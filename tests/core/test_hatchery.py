import pytest
import boa

from contracts.core.userWallet import UserWallet, UserWalletConfig
from contracts.core.agent import AgentWrapper
from constants import MAX_UINT256, ONE_YEAR_IN_BLOCKS, STARTER_AGENT_TYPE, ZERO_ADDRESS
from conf_utils import (
    assert_manager_settings_match_template,
    filter_logs,
    instant_action_settings_tuple,
    starter_agent_template_tuple,
)


WALLET_BACKPACK_CORE_ADDR_ARGS = (
    ("kernel", 0),
    ("sentinel", 1),
    ("high_command", 2),
    ("paymaster", 3),
    ("cheque_book", 4),
    ("migrator", 5),
    ("action_data_provider", 6),
)


def wallet_config_for(wallet_addr):
    return UserWalletConfig.at(UserWallet.at(wallet_addr).walletConfig())


def starter_agent_settings(config):
    return config.managerSettings(config.startingAgent())


def deploy_mock_wallet_backpack(
    field,
    arg_index,
    kernel,
    sentinel,
    high_command,
    paymaster,
    cheque_book,
    migrator,
    action_data_provider,
):
    args = [
        kernel.address,
        sentinel.address,
        high_command.address,
        paymaster.address,
        cheque_book.address,
        migrator.address,
        action_data_provider.address,
    ]
    args[arg_index] = ZERO_ADDRESS
    return boa.load(
        "contracts/mock/MockWalletBackpack.vy",
        *args,
        name=f"mock_wallet_backpack_zero_{field}",
    )


######################
# Create User Wallet #
######################


def test_create_user_wallet_basic(hatchery, alice):
    """Test basic wallet creation"""

    # Create wallet
    wallet_address = hatchery.createUserWallet(sender=alice)

    # Verify wallet was created
    wallet = UserWallet.at(wallet_address)
    assert wallet != ZERO_ADDRESS

    # Verify wallet config
    wallet_config = UserWalletConfig.at(wallet.walletConfig())
    assert wallet_config.owner() == alice


def test_fresh_wallet_inherits_hatchery_default_instant_settings(hatchery, alice):
    wallet = UserWallet.at(hatchery.createUserWallet(sender=alice))
    config = UserWalletConfig.at(wallet.walletConfig())

    assert instant_action_settings_tuple(config.instantActionSettings()) == (True, True, True, True)


def test_hatchery_default_update_only_affects_new_wallets(hatchery, switchboard_bravo, governance, alice, bob):
    wallet_a = UserWallet.at(hatchery.createUserWallet(sender=alice))
    config_a = UserWalletConfig.at(wallet_a.walletConfig())

    switchboard_bravo.setHatcheryDefaultInstantActionSettings(False, True, False, True, sender=governance.address)

    wallet_b = UserWallet.at(hatchery.createUserWallet(sender=bob))
    config_b = UserWalletConfig.at(wallet_b.walletConfig())

    assert instant_action_settings_tuple(config_a.instantActionSettings()) == (True, True, True, True)
    assert instant_action_settings_tuple(config_b.instantActionSettings()) == (False, True, False, True)


def test_hatchery_default_instant_action_settings_change_helper(hatchery, switchboard_bravo):
    has_enable, has_immediate_change, immediate = hatchery.getDefaultInstantActionSettingsChange(
        (False, True, False, True)
    )
    assert has_enable is False
    assert has_immediate_change is True
    assert instant_action_settings_tuple(immediate) == (False, True, False, True)

    has_enable, has_immediate_change, immediate = hatchery.getDefaultInstantActionSettingsChange(
        (True, True, True, True)
    )
    assert has_enable is False
    assert has_immediate_change is False
    assert instant_action_settings_tuple(immediate) == (True, True, True, True)

    hatchery.setDefaultInstantActionSettings((True, False, True, False), sender=switchboard_bravo.address)
    has_enable, has_immediate_change, immediate = hatchery.getDefaultInstantActionSettingsChange(
        (False, True, False, True)
    )
    assert has_enable is True
    assert has_immediate_change is True
    assert instant_action_settings_tuple(immediate) == (False, False, False, False)

    hatchery.setDefaultInstantActionSettings((False, False, False, False), sender=switchboard_bravo.address)
    has_enable, has_immediate_change, immediate = hatchery.getDefaultInstantActionSettingsChange(
        (True, False, False, False)
    )
    assert has_enable is True
    assert has_immediate_change is False
    assert instant_action_settings_tuple(immediate) == (False, False, False, False)


def test_fresh_wallet_default_starter_agent_template_matches_legacy_defaults(hatchery, mission_control, alice):
    block_before = boa.env.evm.patch.block_number
    config = wallet_config_for(hatchery.createUserWallet(sender=alice))
    settings = starter_agent_settings(config)
    wallet_creation_config = mission_control.getUserWalletCreationConfig(alice)

    assert config.startingAgent() != ZERO_ADDRESS
    assert settings.startBlock == block_before
    assert settings.expiryBlock - settings.startBlock == wallet_creation_config.startingAgentActivationLength
    assert_manager_settings_match_template(
        settings,
        starter_agent_template_tuple(startBlock=settings.startBlock, expiryBlock=settings.expiryBlock),
    )


def test_fresh_wallet_default_cheque_flags_are_enabled(hatchery, alice):
    config = wallet_config_for(hatchery.createUserWallet(sender=alice))
    settings = config.chequeSettings()

    assert settings.canManagersCreateCheques is True
    assert settings.canManagerPay is True
    assert settings.canBePulled is True


def test_hatchery_default_instant_setting_access_control(hatchery, switchboard_bravo, alice):
    with boa.reverts("no perms"):
        hatchery.setDefaultInstantActionSettings((False, False, False, False), sender=alice)

    with boa.reverts("no perms"):
        switchboard_bravo.setHatcheryDefaultInstantActionSettings(False, False, False, False, sender=alice)


def test_hatchery_constructor_rejects_whitelisted_non_prod_creator(
    undy_hq,
    weth,
    hatchery,
    mission_control,
    switchboard_alpha,
    alice,
):
    mission_control.setCreatorWhitelist(alice, True, sender=switchboard_alpha.address)

    with boa.reverts("non-prod creator is whitelisted"):
        boa.load(
            "contracts/core/Hatchery.vy",
            undy_hq,
            weth,
            hatchery.ETH(),
            (True, True, True, True),
            (ZERO_ADDRESS, 0),
            (ZERO_ADDRESS, 0),
            alice,
            name="hatchery_bad_non_prod_creator",
        )


@pytest.mark.parametrize("field,arg_index", WALLET_BACKPACK_CORE_ADDR_ARGS)
def test_create_user_wallet_rejects_zero_wallet_backpack_addresses(
    field,
    arg_index,
    hatchery,
    undy_hq,
    governance,
    alice,
    kernel,
    sentinel,
    high_command,
    paymaster,
    cheque_book,
    migrator,
    action_data_provider,
):
    mock_wallet_backpack = deploy_mock_wallet_backpack(
        field,
        arg_index,
        kernel,
        sentinel,
        high_command,
        paymaster,
        cheque_book,
        migrator,
        action_data_provider,
    )
    undy_hq.startAddressUpdateToRegistry(8, mock_wallet_backpack, sender=governance.address)
    boa.env.time_travel(blocks=undy_hq.registryChangeTimeLock())
    assert undy_hq.confirmAddressUpdateToRegistry(8, sender=governance.address)

    with boa.reverts("invalid setup"):
        hatchery.createUserWallet(sender=alice)


@pytest.mark.parametrize("zero_weth", [True, False])
def test_create_user_wallet_rejects_zero_eth_addresses(undy_hq, hatchery, weth, alice, zero_weth):
    bad_hatchery = boa.load(
        "contracts/core/Hatchery.vy",
        undy_hq,
        ZERO_ADDRESS if zero_weth else weth,
        hatchery.ETH() if zero_weth else ZERO_ADDRESS,
        (True, True, True, True),
        (ZERO_ADDRESS, 0),
        (ZERO_ADDRESS, 0),
        ZERO_ADDRESS,
        name=f"hatchery_zero_{'weth' if zero_weth else 'eth'}",
    )

    with boa.reverts("invalid setup"):
        bad_hatchery.createUserWallet(sender=alice)


def test_create_user_wallet_rejects_invalid_templates(hatchery, setUserWalletConfig, alice):
    setUserWalletConfig(_walletTemplate=alice)

    with boa.reverts():
        hatchery.createUserWallet(sender=alice)


def test_create_user_wallet_rejects_invalid_timelock_bounds(hatchery, setUserWalletConfig, alice):
    setUserWalletConfig(_minTimeLock=0, _maxTimeLock=100)

    with boa.reverts("invalid setup"):
        hatchery.createUserWallet(sender=alice)


def test_create_user_wallet_rejects_max_timelock_above_cheque_caps(hatchery, setUserWalletConfig, cheque_book, alice):
    max_supported = min(cheque_book.MAX_UNLOCK_BLOCKS(), cheque_book.MAX_EXPIRY_BLOCKS())
    setUserWalletConfig(_maxTimeLock=max_supported + 1)

    with boa.reverts("invalid setup"):
        hatchery.createUserWallet(sender=alice)


def test_create_user_wallet_rejects_invalid_manager_defaults(hatchery, setManagerConfig, alice):
    setManagerConfig(_managerPeriod=0)

    with boa.reverts("invalid setup"):
        hatchery.createUserWallet(sender=alice)


def test_create_user_wallet_rejects_invalid_payee_defaults(hatchery, mission_control, switchboard_alpha, alice):
    mission_control.setPayeeConfig((0, 15_768_000), sender=switchboard_alpha.address)

    with boa.reverts("invalid setup"):
        hatchery.createUserWallet(sender=alice)


def test_create_user_wallet_rejects_invalid_cheque_defaults(hatchery, mission_control, switchboard_alpha, alice):
    mission_control.setChequeConfig((10, 1_000, 0, 100, 1_000), sender=switchboard_alpha.address)

    with boa.reverts("invalid setup"):
        hatchery.createUserWallet(sender=alice)


def test_create_user_wallet_rejects_user_wallet_starting_agent(hatchery, setAgentConfig, alice, bob):
    existing_wallet = hatchery.createUserWallet(sender=alice)
    setAgentConfig(_startingAgent=existing_wallet)

    with boa.reverts("invalid setup"):
        hatchery.createUserWallet(sender=bob)


def test_create_user_wallet_with_ambassador(hatchery, alice, bob, ledger, mission_control, switchboard_alpha):
    """Test that ambassador is properly set when provided"""

    # First create an ambassador wallet
    ambassador_wallet_addr = hatchery.createUserWallet(sender=alice)

    # Add bob to creator whitelist so they can set an ambassador
    mission_control.setCreatorWhitelist(bob, True, sender=switchboard_alpha.address)

    # Create a user wallet with ambassador
    user_wallet_addr = hatchery.createUserWallet(
        bob,
        ambassador_wallet_addr,
        sender=bob
    )
    
    # Verify ambassador relationship in ledger
    assert ledger.ambassadors(user_wallet_addr) == ambassador_wallet_addr
    
    # Verify ambassador is a valid user wallet
    assert ledger.isUserWallet(ambassador_wallet_addr) == True


def test_create_user_wallet_non_whitelisted_creator_no_ambassador(hatchery, alice, bob, charlie, ledger, mission_control, switchboard_alpha):
    """Test that non-whitelisted creators cannot set ambassadors"""

    # First create an ambassador wallet
    ambassador_wallet_addr = hatchery.createUserWallet(sender=alice)

    # Ensure charlie is NOT on the creator whitelist
    # (by default they shouldn't be, but let's be explicit)
    mission_control.setCreatorWhitelist(charlie, False, sender=switchboard_alpha.address)

    # Create a user wallet with ambassador from non-whitelisted creator
    # The ambassador should be ignored and set to ZERO_ADDRESS
    user_wallet_addr = hatchery.createUserWallet(
        bob,
        ambassador_wallet_addr,
        sender=charlie
    )

    # Verify the wallet was created but ambassador is ZERO_ADDRESS
    assert ledger.isUserWallet(user_wallet_addr) == True
    assert ledger.ambassadors(user_wallet_addr) == ZERO_ADDRESS

    # Verify the ambassador wallet itself is still valid
    assert ledger.isUserWallet(ambassador_wallet_addr) == True


def test_create_user_wallet_ledger_registration(hatchery, alice, ledger):
    """Test that user wallet gets registered with Ledger after creation"""

    initial_count = ledger.numUserWallets()

    # Create wallet
    wallet_address = hatchery.createUserWallet(sender=alice)
    
    # Verify wallet is registered in ledger
    assert ledger.isUserWallet(wallet_address) == True
    assert ledger.userWallets(initial_count) == wallet_address
    assert ledger.indexOfUserWallet(wallet_address) == initial_count

    # Verify wallet count increased
    assert ledger.numUserWallets() == initial_count + 1


def test_user_wallet_config_data(hatchery, alice, setUserWalletConfig):
    """Test that data stored in user wallet and config reflect expected values"""

    # Setup specific configuration
    setUserWalletConfig(
        _minTimeLock=10,
        _maxTimeLock=100,
    )
    
    # Create wallet with specific group ID
    group_id = 42
    wallet_address = hatchery.createUserWallet(
        alice,
        ZERO_ADDRESS,
        group_id,
        sender=alice
    )
    
    # Get wallet and config
    wallet = UserWallet.at(wallet_address)
    wallet_config = UserWalletConfig.at(wallet.walletConfig())
    
    # Verify config data
    assert wallet_config.wallet() == wallet_address
    assert wallet_config.groupId() == group_id
    assert wallet_config.owner() == alice

    assert wallet_config.MIN_TIMELOCK() == 10
    assert wallet_config.MAX_TIMELOCK() == 100


def test_create_user_wallet_permissions(hatchery, alice, bob, charlie, setUserWalletConfig, mission_control, switchboard_alpha):
    """Test permissions around who can create wallets"""

    # By default, anyone can create wallets
    wallet1 = hatchery.createUserWallet(sender=alice)
    assert UserWalletConfig.at(UserWallet.at(wallet1).walletConfig()).owner() == alice
    
    # Create wallet for someone else
    wallet2 = hatchery.createUserWallet(bob, sender=alice)
    assert UserWalletConfig.at(UserWallet.at(wallet2).walletConfig()).owner() == bob
    
    # Restrict wallet creation by enabling whitelist
    setUserWalletConfig(
        _enforceCreatorWhitelist=True
    )
    # Add charlie to whitelist
    mission_control.setCreatorWhitelist(charlie, True, sender=switchboard_alpha.address)
    
    # Non-allowed creator should fail
    with boa.reverts("creator not allowed"):
        hatchery.createUserWallet(sender=bob)
    
    # Allowed creator should succeed
    wallet3 = hatchery.createUserWallet(sender=charlie)
    assert UserWalletConfig.at(UserWallet.at(wallet3).walletConfig()).owner() == charlie


def test_create_user_wallet_limits(hatchery, alice, setUserWalletConfig, ledger):
    """Test limits on how many wallets can be created"""
    # Get current number of wallets
    current_wallet_count = ledger.numUserWallets()
    
    # Set max wallets limit to current + 5 more
    max_wallets = current_wallet_count + 5
    setUserWalletConfig(
        _numUserWalletsAllowed=max_wallets
    )
    
    # Create wallets up to the limit (we can create 5 more)
    created_wallets = []
    for i in range(5):
        wallet = hatchery.createUserWallet(sender=alice)
        created_wallets.append(wallet)
    
    # Verify all wallets were created
    assert len(created_wallets) == 5
    assert ledger.numUserWallets() == max_wallets
    
    # Try to create one more - should fail
    with boa.reverts("max user wallets reached"):
        hatchery.createUserWallet(sender=alice)


def test_create_user_wallet_invalid_ambassador(hatchery, alice, bob, ledger):
    """Test that invalid ambassador addresses are rejected"""

    # Try to use a non-wallet address as ambassador
    user_wallet_addr = hatchery.createUserWallet(
        alice,
        bob,  # bob is an EOA, not a wallet
        sender=alice
    )

    # will fail gracefully
    assert ledger.ambassadors(user_wallet_addr) == ZERO_ADDRESS


def test_create_user_wallet_events(hatchery, alice, starter_agent_2, bob, ambassador_wallet, setAgentConfig, mission_control, switchboard_alpha):
    """Test that correct events are emitted during wallet creation"""

    # Setup agent config
    setAgentConfig(
        _startingAgent=starter_agent_2.address
    )

    # Add bob to creator whitelist so they can set an ambassador
    mission_control.setCreatorWhitelist(bob, True, sender=switchboard_alpha.address)

    # Create user wallet and capture events
    wallet_addr = hatchery.createUserWallet(
        alice,
        ambassador_wallet,
        5,
        sender=bob
    )

    # Check for UserWalletCreated event
    event = filter_logs(hatchery, "UserWalletCreated")[0]
    assert event.mainAddr == wallet_addr
    assert event.configAddr == UserWallet.at(wallet_addr).walletConfig()
    assert event.owner == alice
    assert event.agent == starter_agent_2.address
    assert event.ambassador == ambassador_wallet.address
    assert event.creator == bob
    assert event.groupId == 5
    

def test_create_user_wallet_paused(hatchery, alice, switchboard_alpha):
    """Test that wallet creation fails when contract is paused"""

    # Pause the contract
    hatchery.pause(True, sender=switchboard_alpha.address)
    
    # Try to create wallet - should fail
    with boa.reverts("contract paused"):
        hatchery.createUserWallet(sender=alice)
    
    # Unpause and verify it works again
    hatchery.pause(False, sender=switchboard_alpha.address)

    wallet = hatchery.createUserWallet(sender=alice)
    assert UserWalletConfig.at(UserWallet.at(wallet).walletConfig()).owner() == alice


def test_create_user_wallet_invalid_owner(hatchery, alice):
    """Test that wallet creation fails when owner is ZERO_ADDRESS"""
    
    # Try to create wallet with ZERO_ADDRESS as owner - should fail
    with boa.reverts("invalid setup"):
        hatchery.createUserWallet(
            ZERO_ADDRESS,  # Invalid owner
            ZERO_ADDRESS,
            1,
            sender=alice
        )


def test_create_user_wallet_starting_agent_same_as_owner(hatchery, alice, setAgentConfig, starter_agent):
    """Test that wallet creation fails when starting agent is the same as owner"""
    
    # Set starting agent to be alice
    setAgentConfig(
        _startingAgent=starter_agent.address
    )
    
    # Try to create wallet where owner and starting agent are the same - should fail
    with boa.reverts("starting agent cannot be the owner"):
        hatchery.createUserWallet(
            starter_agent.address,  # Owner matches the configured starting agent
            ZERO_ADDRESS,
            1,
            sender=alice
        )


#########################
# Starter Agent Configs #
#########################


def test_create_user_wallet_old_three_arg_call_still_uses_prod(hatchery, alice, bob, starter_agent):
    wallet_addr = hatchery.createUserWallet(alice, ZERO_ADDRESS, 7, sender=bob)
    wallet_config = UserWalletConfig.at(UserWallet.at(wallet_addr).walletConfig())

    assert wallet_config.owner() == alice
    assert wallet_config.groupId() == 7
    assert wallet_config.startingAgent() == starter_agent.address


def test_create_user_wallet_prod_uses_mission_control_starter(hatchery, alice, setAgentConfig, starter_agent_2):
    setAgentConfig(_startingAgent=starter_agent_2.address)

    wallet_addr = hatchery.createUserWallet(
        alice,
        ZERO_ADDRESS,
        1,
        STARTER_AGENT_TYPE.PROD,
        sender=alice,
    )
    wallet_config = UserWalletConfig.at(UserWallet.at(wallet_addr).walletConfig())

    assert wallet_config.startingAgent() == starter_agent_2.address


def test_non_prod_starter_configs_create_distinct_wallets(hatchery, switchboard_alpha, starter_agent, starter_agent_2, charlie, sally):
    hatchery.setStarterAgentConfig(
        STARTER_AGENT_TYPE.STAGING,
        starter_agent.address,
        ONE_YEAR_IN_BLOCKS,
        sender=switchboard_alpha.address,
    )
    hatchery.setStarterAgentConfig(
        STARTER_AGENT_TYPE.DEV,
        starter_agent_2.address,
        ONE_YEAR_IN_BLOCKS,
        sender=switchboard_alpha.address,
    )
    hatchery.setNonProdCreator(charlie, sender=switchboard_alpha.address)

    staging_wallet = hatchery.createUserWallet(sally, ZERO_ADDRESS, 1, STARTER_AGENT_TYPE.STAGING, sender=charlie)
    dev_wallet = hatchery.createUserWallet(sally, ZERO_ADDRESS, 2, STARTER_AGENT_TYPE.DEV, sender=charlie)

    staging_config = hatchery.stagingStarterAgentConfig()
    dev_config = hatchery.devStarterAgentConfig()
    assert staging_config.startingAgent == starter_agent.address
    assert dev_config.startingAgent == starter_agent_2.address
    assert UserWalletConfig.at(UserWallet.at(staging_wallet).walletConfig()).startingAgent() == starter_agent.address
    assert UserWalletConfig.at(UserWallet.at(dev_wallet).walletConfig()).startingAgent() == starter_agent_2.address


def test_non_prod_starter_config_overwrite_and_clear_all_envs(
    hatchery,
    switchboard_alpha,
    starter_agent,
    starter_agent_2,
    charlie,
    sally,
):
    hatchery.setNonProdCreator(charlie, sender=switchboard_alpha.address)

    staging_default_wallet = hatchery.createUserWallet(sally, ZERO_ADDRESS, 1, STARTER_AGENT_TYPE.STAGING, sender=charlie)
    dev_default_wallet = hatchery.createUserWallet(sally, ZERO_ADDRESS, 2, STARTER_AGENT_TYPE.DEV, sender=charlie)
    assert UserWalletConfig.at(UserWallet.at(staging_default_wallet).walletConfig()).startingAgent() == hatchery.WETH()
    assert UserWalletConfig.at(UserWallet.at(dev_default_wallet).walletConfig()).startingAgent() == hatchery.WETH()

    hatchery.setStarterAgentConfig(
        STARTER_AGENT_TYPE.STAGING,
        starter_agent.address,
        ONE_YEAR_IN_BLOCKS,
        sender=switchboard_alpha.address,
    )
    hatchery.setStarterAgentConfig(
        STARTER_AGENT_TYPE.STAGING,
        starter_agent_2.address,
        ONE_YEAR_IN_BLOCKS,
        sender=switchboard_alpha.address,
    )
    staging_config = hatchery.stagingStarterAgentConfig()
    assert staging_config.startingAgent == starter_agent_2.address
    staging_wallet = hatchery.createUserWallet(sally, ZERO_ADDRESS, 1, STARTER_AGENT_TYPE.STAGING, sender=charlie)
    assert UserWalletConfig.at(UserWallet.at(staging_wallet).walletConfig()).startingAgent() == starter_agent_2.address

    hatchery.setStarterAgentConfig(
        STARTER_AGENT_TYPE.DEV,
        starter_agent_2.address,
        ONE_YEAR_IN_BLOCKS,
        sender=switchboard_alpha.address,
    )
    hatchery.setStarterAgentConfig(
        STARTER_AGENT_TYPE.DEV,
        starter_agent.address,
        ONE_YEAR_IN_BLOCKS,
        sender=switchboard_alpha.address,
    )
    dev_config = hatchery.devStarterAgentConfig()
    assert dev_config.startingAgent == starter_agent.address
    dev_wallet = hatchery.createUserWallet(sally, ZERO_ADDRESS, 2, STARTER_AGENT_TYPE.DEV, sender=charlie)
    assert UserWalletConfig.at(UserWallet.at(dev_wallet).walletConfig()).startingAgent() == starter_agent.address

    hatchery.setStarterAgentConfig(STARTER_AGENT_TYPE.STAGING, ZERO_ADDRESS, 0, sender=switchboard_alpha.address)
    hatchery.setStarterAgentConfig(STARTER_AGENT_TYPE.DEV, ZERO_ADDRESS, 0, sender=switchboard_alpha.address)
    with boa.reverts("starter agent not set"):
        hatchery.createUserWallet(sally, ZERO_ADDRESS, 3, STARTER_AGENT_TYPE.STAGING, sender=charlie)
    with boa.reverts("starter agent not set"):
        hatchery.createUserWallet(sally, ZERO_ADDRESS, 3, STARTER_AGENT_TYPE.DEV, sender=charlie)


def test_non_prod_creation_requires_non_prod_creator(hatchery, switchboard_alpha, alice, starter_agent, charlie):
    hatchery.setStarterAgentConfig(
        STARTER_AGENT_TYPE.STAGING,
        starter_agent.address,
        ONE_YEAR_IN_BLOCKS,
        sender=switchboard_alpha.address,
    )
    hatchery.setNonProdCreator(charlie, sender=switchboard_alpha.address)

    with boa.reverts("no perms"):
        hatchery.createUserWallet(alice, ZERO_ADDRESS, 1, STARTER_AGENT_TYPE.STAGING, sender=alice)

    wallet_addr = hatchery.createUserWallet(alice, ZERO_ADDRESS, 1, STARTER_AGENT_TYPE.STAGING, sender=charlie)
    assert UserWalletConfig.at(UserWallet.at(wallet_addr).walletConfig()).startingAgent() == starter_agent.address


def test_non_prod_creator_can_create_when_creator_whitelist_is_enforced(
    hatchery,
    switchboard_alpha,
    setUserWalletConfig,
    alice,
    starter_agent,
    charlie,
):
    setUserWalletConfig(_enforceCreatorWhitelist=True)
    hatchery.setStarterAgentConfig(
        STARTER_AGENT_TYPE.DEV,
        starter_agent.address,
        ONE_YEAR_IN_BLOCKS,
        sender=switchboard_alpha.address,
    )
    hatchery.setNonProdCreator(charlie, sender=switchboard_alpha.address)

    wallet_addr = hatchery.createUserWallet(alice, ZERO_ADDRESS, 1, STARTER_AGENT_TYPE.DEV, sender=charlie)
    assert UserWalletConfig.at(UserWallet.at(wallet_addr).walletConfig()).startingAgent() == starter_agent.address


def test_non_prod_creator_cannot_create_prod(hatchery, switchboard_alpha, alice, charlie):
    hatchery.setNonProdCreator(charlie, sender=switchboard_alpha.address)

    with boa.reverts("non-prod creator cannot create prod"):
        hatchery.createUserWallet(alice, ZERO_ADDRESS, 1, STARTER_AGENT_TYPE.PROD, sender=charlie)


def test_non_prod_creator_must_not_be_creator_whitelisted(
    hatchery,
    switchboard_alpha,
    mission_control,
    governance,
    alice,
    starter_agent,
    charlie,
):
    mission_control.setCreatorWhitelist(charlie, True, sender=switchboard_alpha.address)

    with boa.reverts("non-prod creator is whitelisted"):
        hatchery.setNonProdCreator(charlie, sender=switchboard_alpha.address)

    mission_control.setCreatorWhitelist(charlie, False, sender=switchboard_alpha.address)
    hatchery.setStarterAgentConfig(
        STARTER_AGENT_TYPE.STAGING,
        starter_agent.address,
        ONE_YEAR_IN_BLOCKS,
        sender=switchboard_alpha.address,
    )
    hatchery.setNonProdCreator(charlie, sender=switchboard_alpha.address)
    mission_control.setCreatorWhitelist(charlie, True, sender=switchboard_alpha.address)

    with boa.reverts("non-prod creator is whitelisted"):
        hatchery.createUserWallet(alice, ZERO_ADDRESS, 1, STARTER_AGENT_TYPE.STAGING, sender=charlie)


def test_non_prod_creator_zero_blocks_non_prod_only(hatchery, switchboard_alpha, alice, starter_agent, charlie):
    hatchery.setStarterAgentConfig(
        STARTER_AGENT_TYPE.STAGING,
        starter_agent.address,
        ONE_YEAR_IN_BLOCKS,
        sender=switchboard_alpha.address,
    )

    with boa.reverts("no perms"):
        hatchery.createUserWallet(alice, ZERO_ADDRESS, 1, STARTER_AGENT_TYPE.STAGING, sender=charlie)

    hatchery.setNonProdCreator(charlie, sender=switchboard_alpha.address)
    assert hatchery.createUserWallet(alice, ZERO_ADDRESS, 1, STARTER_AGENT_TYPE.STAGING, sender=charlie) != ZERO_ADDRESS

    hatchery.setNonProdCreator(ZERO_ADDRESS, sender=switchboard_alpha.address)
    with boa.reverts("no perms"):
        hatchery.createUserWallet(alice, ZERO_ADDRESS, 1, STARTER_AGENT_TYPE.STAGING, sender=charlie)
    assert hatchery.createUserWallet(sender=alice) != ZERO_ADDRESS


def test_selecting_unset_or_cleared_non_prod_reverts(hatchery, switchboard_alpha, alice, starter_agent, charlie):
    hatchery.setNonProdCreator(charlie, sender=switchboard_alpha.address)
    hatchery.setStarterAgentConfig(
        STARTER_AGENT_TYPE.STAGING,
        ZERO_ADDRESS,
        0,
        sender=switchboard_alpha.address,
    )

    with boa.reverts("starter agent not set"):
        hatchery.createUserWallet(alice, ZERO_ADDRESS, 1, STARTER_AGENT_TYPE.STAGING, sender=charlie)

    hatchery.setStarterAgentConfig(
        STARTER_AGENT_TYPE.STAGING,
        starter_agent.address,
        ONE_YEAR_IN_BLOCKS,
        sender=switchboard_alpha.address,
    )
    assert hatchery.createUserWallet(alice, ZERO_ADDRESS, 1, STARTER_AGENT_TYPE.STAGING, sender=charlie) != ZERO_ADDRESS

    hatchery.setStarterAgentConfig(
        STARTER_AGENT_TYPE.STAGING,
        ZERO_ADDRESS,
        0,
        sender=switchboard_alpha.address,
    )
    with boa.reverts("starter agent not set"):
        hatchery.createUserWallet(alice, ZERO_ADDRESS, 1, STARTER_AGENT_TYPE.STAGING, sender=charlie)


def test_set_starter_agent_config_validation(hatchery, switchboard_alpha, alice):
    with boa.reverts("invalid starter agent params"):
        hatchery.setStarterAgentConfig(STARTER_AGENT_TYPE.STAGING, alice, 0, sender=switchboard_alpha.address)

    with boa.reverts("invalid starter agent params"):
        hatchery.setStarterAgentConfig(STARTER_AGENT_TYPE.STAGING, ZERO_ADDRESS, ONE_YEAR_IN_BLOCKS, sender=switchboard_alpha.address)

    with boa.reverts("invalid starter agent params"):
        hatchery.setStarterAgentConfig(STARTER_AGENT_TYPE.STAGING, alice, MAX_UINT256, sender=switchboard_alpha.address)

    with boa.reverts("invalid starter agent params"):
        hatchery.setStarterAgentConfig(STARTER_AGENT_TYPE.STAGING, alice, ONE_YEAR_IN_BLOCKS, sender=switchboard_alpha.address)

    with boa.reverts("prod owned by mission control"):
        hatchery.setStarterAgentConfig(STARTER_AGENT_TYPE.PROD, alice, ONE_YEAR_IN_BLOCKS, sender=switchboard_alpha.address)


def test_hatchery_setters_require_switchboard(hatchery, alice, bob):
    with boa.reverts("no perms"):
        hatchery.setStarterAgentConfig(STARTER_AGENT_TYPE.STAGING, bob, ONE_YEAR_IN_BLOCKS, sender=alice)

    with boa.reverts("no perms"):
        hatchery.setNonProdCreator(bob, sender=alice)


def test_any_registered_switchboard_can_set_hatchery_non_prod_controls(
    hatchery,
    switchboard_bravo,
    starter_agent,
    bob,
):
    hatchery.setStarterAgentConfig(
        STARTER_AGENT_TYPE.STAGING,
        starter_agent.address,
        ONE_YEAR_IN_BLOCKS,
        sender=switchboard_bravo.address,
    )
    hatchery.setNonProdCreator(bob, sender=switchboard_bravo.address)

    config = hatchery.stagingStarterAgentConfig()
    assert config.startingAgent == starter_agent.address
    assert config.startingAgentActivationLength == ONE_YEAR_IN_BLOCKS
    assert hatchery.nonProdCreator() == bob


def test_hatchery_setters_work_while_paused(hatchery, switchboard_alpha, alice, starter_agent):
    hatchery.pause(True, sender=switchboard_alpha.address)

    hatchery.setStarterAgentConfig(STARTER_AGENT_TYPE.STAGING, starter_agent.address, ONE_YEAR_IN_BLOCKS, sender=switchboard_alpha.address)
    hatchery.setNonProdCreator(alice, sender=switchboard_alpha.address)

    config = hatchery.stagingStarterAgentConfig()
    assert config.startingAgent == starter_agent.address
    assert config.startingAgentActivationLength == ONE_YEAR_IN_BLOCKS
    assert hatchery.nonProdCreator() == alice

    with boa.reverts("contract paused"):
        hatchery.createUserWallet(sender=alice)

    hatchery.pause(False, sender=switchboard_alpha.address)


def test_non_prod_owner_collision_reverts(hatchery, switchboard_alpha, starter_agent, charlie):
    hatchery.setStarterAgentConfig(
        STARTER_AGENT_TYPE.STAGING,
        starter_agent.address,
        ONE_YEAR_IN_BLOCKS,
        sender=switchboard_alpha.address,
    )
    hatchery.setNonProdCreator(charlie, sender=switchboard_alpha.address)

    with boa.reverts("starting agent cannot be the owner"):
        hatchery.createUserWallet(starter_agent.address, ZERO_ADDRESS, 1, STARTER_AGENT_TYPE.STAGING, sender=charlie)


def test_non_prod_privileged_starter_fails_at_creation(hatchery, switchboard_alpha, alice, charlie, high_command):
    hatchery.setStarterAgentConfig(
        STARTER_AGENT_TYPE.DEV,
        high_command.address,
        ONE_YEAR_IN_BLOCKS,
        sender=switchboard_alpha.address,
    )
    hatchery.setNonProdCreator(charlie, sender=switchboard_alpha.address)

    with boa.reverts("invalid setup"):
        hatchery.createUserWallet(alice, ZERO_ADDRESS, 1, STARTER_AGENT_TYPE.DEV, sender=charlie)


def test_starter_agent_config_events(hatchery, switchboard_alpha, starter_agent, bob):
    hatchery.setStarterAgentConfig(
        STARTER_AGENT_TYPE.STAGING,
        starter_agent.address,
        ONE_YEAR_IN_BLOCKS,
        sender=switchboard_alpha.address,
    )
    config_event = filter_logs(hatchery, "StarterAgentConfigSet")[-1]
    assert config_event.starterAgentType == STARTER_AGENT_TYPE.STAGING
    assert config_event.startingAgent == starter_agent.address
    assert config_event.startingAgentActivationLength == ONE_YEAR_IN_BLOCKS

    hatchery.setNonProdCreator(bob, sender=switchboard_alpha.address)
    creator_event = filter_logs(hatchery, "NonProdCreatorSet")[-1]
    assert creator_event.nonProdCreator == bob


def test_malformed_starter_agent_type_reverts(hatchery, switchboard_alpha, alice, bob, charlie):
    hatchery.setNonProdCreator(charlie, sender=switchboard_alpha.address)

    with boa.reverts("invalid starter agent type"):
        hatchery.setStarterAgentConfig(0, bob, ONE_YEAR_IN_BLOCKS, sender=switchboard_alpha.address)

    with boa.reverts("invalid starter agent type"):
        hatchery.setStarterAgentConfig(
            STARTER_AGENT_TYPE.PROD | STARTER_AGENT_TYPE.STAGING,
            bob,
            ONE_YEAR_IN_BLOCKS,
            sender=switchboard_alpha.address,
        )

    with boa.reverts("invalid starter agent type"):
        hatchery.createUserWallet(alice, ZERO_ADDRESS, 1, 0, sender=charlie)

    with boa.reverts("invalid starter agent type"):
        hatchery.createUserWallet(
            alice,
            ZERO_ADDRESS,
            1,
            STARTER_AGENT_TYPE.STAGING | STARTER_AGENT_TYPE.DEV,
            sender=charlie,
        )
