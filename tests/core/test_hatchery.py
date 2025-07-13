import pytest
import boa

from contracts.core.userWallet import UserWallet, UserWalletConfig
from contracts.core.agent import AgentWrapper
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS
from conf_utils import filter_logs


######################
# Create User Wallet #
######################


def test_create_user_wallet_with_trial_funds(hatchery, alice, alpha_token, alpha_token_whale, setUserWalletConfig):
    """Test that trial funds get sent to the wallet when configured"""

    # Setup: Configure trial funds
    trial_amount = 10 * EIGHTEEN_DECIMALS
    setUserWalletConfig(
        _trialAsset=alpha_token.address,
        _trialAmount=trial_amount
    )
    
    # Transfer trial funds to hatchery
    alpha_token.transfer(hatchery, trial_amount * 10, sender=alpha_token_whale)
    
    # Create wallet with trial funds enabled (default)
    initial_hatchery_balance = alpha_token.balanceOf(hatchery.address)
    wallet_address = hatchery.createUserWallet(sender=alice)
    
    # Verify trial funds were transferred
    wallet = UserWallet.at(wallet_address)
    assert alpha_token.balanceOf(wallet.address) == trial_amount
    assert alpha_token.balanceOf(hatchery.address) == initial_hatchery_balance - trial_amount

    wallet_config = UserWalletConfig.at(wallet.walletConfig())
    assert wallet_config.trialFundsAsset() == alpha_token.address
    assert wallet_config.trialFundsAmount() == trial_amount


def test_create_user_wallet_without_trial_funds(hatchery, alice, alpha_token, alpha_token_whale, setUserWalletConfig):
    """Test wallet creation without trial funds when disabled"""

    # Setup: Configure trial funds but disable them in creation
    trial_amount = 10 * EIGHTEEN_DECIMALS
    setUserWalletConfig(
        _trialAsset=alpha_token.address,
        _trialAmount=trial_amount
    )
    
    # Transfer trial funds to hatchery
    alpha_token.transfer(hatchery.address, trial_amount * 10, sender=alpha_token_whale)
    
    # Create wallet with trial funds disabled
    initial_hatchery_balance = alpha_token.balanceOf(hatchery.address)
    wallet_address = hatchery.createUserWallet(
        alice,
        ZERO_ADDRESS,
        False,
        sender=alice
    )
    
    # Verify no trial funds were transferred
    wallet = UserWallet.at(wallet_address)
    assert alpha_token.balanceOf(wallet.address) == 0
    assert alpha_token.balanceOf(hatchery.address) == initial_hatchery_balance
    
    # Verify wallet config still has trial funds data
    wallet_config = UserWalletConfig.at(wallet.walletConfig())
    assert wallet_config.trialFundsAsset() == ZERO_ADDRESS
    assert wallet_config.trialFundsAmount() == 0


def test_create_user_wallet_with_ambassador(hatchery, alice, bob, ledger):
    """Test that ambassador is properly set when provided"""

    # First create an ambassador wallet
    ambassador_wallet_addr = hatchery.createUserWallet(sender=alice)
    
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
        False,
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


def test_create_user_wallet_limits(hatchery, alice, setUserWalletConfig):
    """Test limits on how many wallets can be created"""
    # Set max wallets limit
    max_wallets = 5
    setUserWalletConfig(
        _numUserWalletsAllowed=max_wallets
    )
    
    # Create wallets up to the limit
    created_wallets = []
    for i in range(max_wallets - 1):
        wallet = hatchery.createUserWallet(sender=alice)
        created_wallets.append(wallet)
    
    # Verify all wallets were created
    assert len(created_wallets) == max_wallets - 1
    
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


def test_create_user_wallet_events(hatchery, alice, charlie, bob, alpha_token, alpha_token_whale, setUserWalletConfig, ambassador_wallet, setAgentConfig):
    """Test that correct events are emitted during wallet creation"""

    # Setup trial funds
    trial_amount = 10 * EIGHTEEN_DECIMALS
    setUserWalletConfig(
        _trialAsset=alpha_token.address,
        _trialAmount=trial_amount
    )
    alpha_token.transfer(hatchery.address, trial_amount * 10, sender=alpha_token_whale)
    setAgentConfig(
        _startingAgent=charlie
    )

    # Create user wallet and capture events
    wallet_addr = hatchery.createUserWallet(
        alice,
        ambassador_wallet,
        True,
        5,
        sender=bob
    )
    
    # Check for UserWalletCreated event
    event = filter_logs(hatchery, "UserWalletCreated")[0]
    assert event.mainAddr == wallet_addr
    assert event.configAddr == UserWallet.at(wallet_addr).walletConfig()
    assert event.owner == alice
    assert event.agent == charlie
    assert event.ambassador == ambassador_wallet.address
    assert event.creator == bob
    assert event.trialFundsAsset == alpha_token.address
    assert event.trialFundsAmount == trial_amount
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
            True,
            1,
            sender=alice
        )


def test_create_user_wallet_starting_agent_same_as_owner(hatchery, alice, setAgentConfig):
    """Test that wallet creation fails when starting agent is the same as owner"""
    
    # Set starting agent to be alice
    setAgentConfig(
        _startingAgent=alice
    )
    
    # Try to create wallet where owner and starting agent are the same - should fail
    with boa.reverts("starting agent cannot be the owner"):
        hatchery.createUserWallet(
            alice,  # Owner is alice
            ZERO_ADDRESS,
            True,
            1,
            sender=alice  # Starting agent will be alice based on config
        )


def test_create_user_wallet_insufficient_trial_funds(hatchery, alice, alpha_token, setUserWalletConfig, alpha_token_whale):
    """Test wallet creation when hatchery has insufficient trial funds"""
    
    # Setup trial funds config
    trial_amount = 10 * EIGHTEEN_DECIMALS
    setUserWalletConfig(
        _trialAsset=alpha_token.address,
        _trialAmount=trial_amount
    )
    
    # Don't fund hatchery or fund with less than required
    # Hatchery balance is 0 or less than trial_amount

    # remove funds from hatchery
    if alpha_token.balanceOf(hatchery.address) != 0:
        alpha_token.transfer(alpha_token_whale, alpha_token.balanceOf(hatchery.address), sender=hatchery.address)

    # Create wallet - should succeed but without trial funds
    wallet_address = hatchery.createUserWallet(sender=alice)
    
    # Verify wallet was created
    wallet = UserWallet.at(wallet_address)
    assert wallet != ZERO_ADDRESS
    
    # Verify no trial funds were sent
    assert alpha_token.balanceOf(wallet.address) == 0
    
    # Verify wallet config shows no trial funds
    wallet_config = UserWalletConfig.at(wallet.walletConfig())
    assert wallet_config.trialFundsAsset() == ZERO_ADDRESS
    assert wallet_config.trialFundsAmount() == 0


def test_create_user_wallet_trial_funds_partial_config(hatchery, alice, alpha_token, setUserWalletConfig):
    """Test wallet creation with incomplete trial funds configuration"""
    
    # Test 1: Asset set but amount is 0
    setUserWalletConfig(
        _trialAsset=alpha_token.address,
        _trialAmount=0
    )
    
    wallet1 = hatchery.createUserWallet(sender=alice)
    wallet1_config = UserWalletConfig.at(UserWallet.at(wallet1).walletConfig())
    
    # Should create wallet without trial funds
    assert alpha_token.balanceOf(wallet1) == 0
    assert wallet1_config.trialFundsAsset() == ZERO_ADDRESS
    assert wallet1_config.trialFundsAmount() == 0
    
    # Test 2: Amount set but asset is ZERO_ADDRESS
    setUserWalletConfig(
        _trialAsset=ZERO_ADDRESS,
        _trialAmount=10 * EIGHTEEN_DECIMALS
    )
    
    wallet2 = hatchery.createUserWallet(sender=alice)
    wallet2_config = UserWalletConfig.at(UserWallet.at(wallet2).walletConfig())
    
    # Should create wallet without trial funds
    assert wallet2_config.trialFundsAsset() == ZERO_ADDRESS
    assert wallet2_config.trialFundsAmount() == 0


################
# Create Agent #
################


def test_create_agent_basic(hatchery, alice, ledger):
    """Test basic agent creation with default parameters"""
    
    initial_count = ledger.numAgents()
    
    # Create agent with defaults (owner=msg.sender, groupId=1)
    agent_address = hatchery.createAgent(sender=alice)
    
    # Verify agent was created
    assert agent_address != ZERO_ADDRESS
    
    # Verify agent is registered in ledger
    assert ledger.isAgent(agent_address) == True
    assert ledger.agents(initial_count) == agent_address
    assert ledger.indexOfAgent(agent_address) == initial_count
    
    # Verify agent count increased
    assert ledger.numAgents() == initial_count + 1


def test_create_agent_custom_owner(hatchery, alice, bob, ledger):
    """Test agent creation with custom owner"""
    
    # Create agent for bob (different from sender)
    agent_address = hatchery.createAgent(bob, sender=alice)
    
    # Verify agent was created
    assert agent_address != ZERO_ADDRESS
    
    # Verify agent is registered in ledger
    assert ledger.isAgent(agent_address) == True
    
    # Verify owner is bob
    assert AgentWrapper.at(agent_address).owner() == bob


def test_create_agent_custom_group_id(hatchery, alice):
    """Test agent creation with custom group ID"""
    
    # Create agent with custom group ID
    group_id = 42
    agent_address = hatchery.createAgent(alice, group_id, sender=alice)
    
    # verify group id
    assert AgentWrapper.at(agent_address).groupId() == group_id


def test_create_agent_permissions(hatchery, alice, bob, charlie, setAgentConfig, mission_control, switchboard_alpha):
    """Test permissions around who can create agents"""
    
    # By default, anyone can create agents
    agent1 = hatchery.createAgent(sender=alice)
    assert agent1 != ZERO_ADDRESS
    
    # Create agent for someone else
    agent2 = hatchery.createAgent(bob, sender=alice)
    assert agent2 != ZERO_ADDRESS
    
    # Restrict agent creation by enabling whitelist
    setAgentConfig(
        _enforceCreatorWhitelist=True
    )
    
    # Add charlie to whitelist
    mission_control.setCreatorWhitelist(charlie, True, sender=switchboard_alpha.address)
    
    # Non-allowed creator should fail
    with boa.reverts("creator not allowed"):
        hatchery.createAgent(sender=bob)
    
    # Allowed creator should succeed
    agent3 = hatchery.createAgent(sender=charlie)
    assert agent3 != ZERO_ADDRESS


def test_create_agent_limits(hatchery, alice, setAgentConfig, ledger):
    """Test limits on how many agents can be created"""
    
    # Get current agent count
    initial_count = ledger.numAgents()
    
    # Set max agents limit (relative to current count)
    max_new_agents = 3
    max_total_agents = initial_count + max_new_agents
    
    setAgentConfig(
        _numAgentsAllowed=max_total_agents
    )
    
    # Create agents up to the limit
    created_agents = []
    for i in range(max_new_agents):
        agent = hatchery.createAgent(sender=alice)
        created_agents.append(agent)
    
    # Verify all agents were created
    assert len(created_agents) == max_new_agents
    assert ledger.numAgents() == max_total_agents
    
    # Try to create one more - should fail
    with boa.reverts("max agents reached"):
        hatchery.createAgent(sender=alice)


def test_create_agent_invalid_owner(hatchery, alice):
    """Test that agent creation fails when owner is ZERO_ADDRESS"""
    
    # Try to create agent with ZERO_ADDRESS as owner - should fail
    with boa.reverts("invalid setup"):
        hatchery.createAgent(
            ZERO_ADDRESS,  # Invalid owner
            sender=alice
        )


def test_create_agent_events(hatchery, alice, bob):
    """Test that correct events are emitted during agent creation"""
    
    # Create agent with specific parameters
    group_id = 7
    agent_addr = hatchery.createAgent(
        bob,
        group_id,
        sender=alice
    )
    
    # Check for AgentCreated event
    event = filter_logs(hatchery, "AgentCreated")[0]
    assert event.agent == agent_addr
    assert event.owner == bob
    assert event.creator == alice
    assert event.groupId == group_id


def test_create_agent_paused(hatchery, alice, switchboard_alpha):
    """Test that agent creation fails when contract is paused"""
    
    # Pause the contract
    hatchery.pause(True, sender=switchboard_alpha.address)
    
    # Try to create agent - should fail
    with boa.reverts("contract paused"):
        hatchery.createAgent(sender=alice)
    
    # Unpause and verify it works again
    hatchery.pause(False, sender=switchboard_alpha.address)
    
    agent = hatchery.createAgent(sender=alice)
    assert agent != ZERO_ADDRESS


def test_create_agent_multiple_creators(hatchery, alice, bob, charlie, ledger):
    """Test multiple agents created by different creators"""
    
    initial_count = ledger.numAgents()
    
    # Different creators create agents
    agent1 = hatchery.createAgent(sender=alice)
    agent2 = hatchery.createAgent(sender=bob)
    agent3 = hatchery.createAgent(sender=charlie)
    
    # Verify all agents were created and registered
    assert ledger.isAgent(agent1) == True
    assert ledger.isAgent(agent2) == True
    assert ledger.isAgent(agent3) == True
    
    # Verify count increased correctly
    assert ledger.numAgents() == initial_count + 3
    
    # Verify they have different addresses
    assert agent1 != agent2
    assert agent2 != agent3
    assert agent1 != agent3


def test_create_agent_time_lock_config(hatchery, alice, setUserWalletConfig):
    """Test agent creation with different time lock configurations"""
    
    # Set specific time lock values
    min_lock = 100
    max_lock = 1000
    
    setUserWalletConfig(
        _minTimeLock=min_lock,
        _maxTimeLock=max_lock
    )
    
    # Create agent
    agent_address = hatchery.createAgent(sender=alice)
    
    # Verify agent was created
    assert agent_address != ZERO_ADDRESS
    
    assert AgentWrapper.at(agent_address).MIN_OWNERSHIP_TIMELOCK() == min_lock
    assert AgentWrapper.at(agent_address).MAX_OWNERSHIP_TIMELOCK() == max_lock


###############
# Trial Funds #
###############


@pytest.fixture(scope="module")
def setupTrialFundsWallet(setUserWalletConfig, hatchery, alice, alpha_token, alpha_token_whale):
    def setupTrialFundsWallet():
        trial_amount = 10 * EIGHTEEN_DECIMALS
        setUserWalletConfig(
            _trialAsset=alpha_token.address,
            _trialAmount=trial_amount
        )
        
        # Transfer trial funds to hatchery
        alpha_token.transfer(hatchery, trial_amount * 10, sender=alpha_token_whale)
        
        # Create wallet with trial funds
        wallet_address = hatchery.createUserWallet(sender=alice)
        return UserWallet.at(wallet_address)

    yield setupTrialFundsWallet


# does wallet have trial funds


def test_does_wallet_still_have_trial_funds_all_in_wallet(hatchery, alpha_token, setupTrialFundsWallet):
    """Test doesWalletStillHaveTrialFunds when all funds are in the wallet"""

    wallet = setupTrialFundsWallet()
    
    # Verify wallet has trial funds
    assert alpha_token.balanceOf(wallet) == 10 * EIGHTEEN_DECIMALS
    
    # Check that wallet still has trial funds
    assert hatchery.doesWalletStillHaveTrialFunds(wallet) == True


def test_does_wallet_still_have_trial_funds_all_in_single_vault(
    hatchery, alice, alpha_token, setupTrialFundsWallet, alpha_token_vault
):
    """Test doesWalletStillHaveTrialFunds when all funds are in a single vault"""

    wallet = setupTrialFundsWallet()
    
    # Owner deposits all trial funds into vault
    wallet.depositForYield(
        1,
        alpha_token.address,
        alpha_token_vault.address,
        sender=alice,
    )
    
    # Verify wallet has no direct alpha tokens but has vault shares
    assert alpha_token.balanceOf(wallet.address) == 0
    assert alpha_token_vault.balanceOf(wallet.address) != 0
    
    # Check that wallet still has trial funds (in the vault)
    assert hatchery.doesWalletStillHaveTrialFunds(wallet.address) == True


def test_does_wallet_still_have_trial_funds_split_across_vaults(
    hatchery, alice, alpha_token, setupTrialFundsWallet,
    alpha_token_vault, alpha_token_vault_2, alpha_token_vault_3
):
    """Test doesWalletStillHaveTrialFunds when funds are split across multiple vaults"""

    wallet = setupTrialFundsWallet()
    
    # Split funds across vaults (3, 3, 3 units each, keep 1 in wallet)
    # Total deposited: 9 units, remaining in wallet: 1 unit
    
    # Deposit 3 units into vault 1
    wallet.depositForYield(
        1,  # legoId for mock_yield_lego
        alpha_token.address,
        alpha_token_vault.address,
        3 * EIGHTEEN_DECIMALS,
        sender=alice,
    )
    
    # Deposit 3 units into vault 2
    wallet.depositForYield(
        1,  # legoId for mock_yield_lego
        alpha_token.address,
        alpha_token_vault_2.address,
        3 * EIGHTEEN_DECIMALS,
        sender=alice,
    )
    
    # Deposit 3 units into vault 3
    wallet.depositForYield(
        1,  # legoId for mock_yield_lego
        alpha_token.address,
        alpha_token_vault_3.address,
        3 * EIGHTEEN_DECIMALS,
        sender=alice,
    )
    
    # Verify balances
    assert alpha_token.balanceOf(wallet) == EIGHTEEN_DECIMALS  # 1 unit left
    assert alpha_token_vault.balanceOf(wallet) > 0
    assert alpha_token_vault_2.balanceOf(wallet) > 0
    assert alpha_token_vault_3.balanceOf(wallet) > 0
    
    # Check that wallet still has trial funds (split across vaults + wallet)
    assert hatchery.doesWalletStillHaveTrialFunds(wallet) == True


def test_does_wallet_still_have_trial_funds_below_threshold(
    hatchery, alice, alpha_token, alpha_token_whale, setupTrialFundsWallet,
):
    """Test doesWalletStillHaveTrialFunds when funds fall below 99% threshold"""

    wallet = setupTrialFundsWallet()
    trial_amount = 10 * EIGHTEEN_DECIMALS
    
    # Transfer out more than 1% to fall below threshold (transfer out 2%)
    amount_to_transfer = trial_amount * 2 // 100  # 2% of trial amount
    alpha_token.transfer(alice, amount_to_transfer, sender=wallet.address)
    
    # Verify wallet has less than 99% of trial funds
    remaining = alpha_token.balanceOf(wallet)
    assert remaining < (trial_amount * 99 // 100)
    
    # Check that wallet no longer has sufficient trial funds
    assert hatchery.doesWalletStillHaveTrialFunds(wallet) == False
    
    # Test edge case: exactly at 99% threshold
    # First, send back some funds to get exactly to 99%
    target_balance = trial_amount * 99 // 100
    current_balance = alpha_token.balanceOf(wallet)
    needed = target_balance - current_balance
    
    alpha_token.transfer(wallet.address, needed, sender=alpha_token_whale)
    assert alpha_token.balanceOf(wallet) == target_balance
    
    # Should return True at exactly 99%
    assert hatchery.doesWalletStillHaveTrialFunds(wallet) == True


def test_does_wallet_still_have_trial_funds_mixed_scenario(
    hatchery, alice, alpha_token, setupTrialFundsWallet,
    alpha_token_vault, alpha_token_vault_2
):
    """Test complex scenario with funds in wallet, vaults, and some spent"""

    wallet = setupTrialFundsWallet()
    
    # Scenario: 4 units in wallet, 3 units in vault1, 2 units in vault2, 1 unit spent
    # Total remaining: 9 units (90% of original)
    
    # Deposit 3 units into vault 1
    wallet.depositForYield(
        1,  # legoId for mock_yield_lego
        alpha_token.address,
        alpha_token_vault.address,
        3 * EIGHTEEN_DECIMALS,
        sender=alice,
    )
    
    # Deposit 2 units into vault 2
    wallet.depositForYield(
        1,  # legoId for mock_yield_lego
        alpha_token.address,
        alpha_token_vault_2.address,
        2 * EIGHTEEN_DECIMALS,
        sender=alice,
    )

    # Spend 1 unit
    alpha_token.transfer(alice, EIGHTEEN_DECIMALS, sender=wallet.address)
    
    # Should have 4 units left in wallet
    assert alpha_token.balanceOf(wallet) == 4 * EIGHTEEN_DECIMALS
    
    # Total is 90%, which is below 99% threshold
    assert hatchery.doesWalletStillHaveTrialFunds(wallet) == False


def test_does_wallet_still_have_trial_funds_vault_gains_yield(
    hatchery, alice, alpha_token, alpha_token_whale, setupTrialFundsWallet,
    alpha_token_vault
):
    """Test when vault gains yield, increasing share price"""

    wallet = setupTrialFundsWallet()
    
    # Deposit 8 units into vault, keep 2 in wallet
    wallet.depositForYield(
        1,  # legoId for mock_yield_lego
        alpha_token.address,
        alpha_token_vault.address,
        8 * EIGHTEEN_DECIMALS,
        sender=alice,
    )
    
    # Spend 2 units from wallet (now have 8 units in vault only = 80%)
    alpha_token.transfer(alice, 2 * EIGHTEEN_DECIMALS, sender=wallet.address)
    assert hatchery.doesWalletStillHaveTrialFunds(wallet) == False
    
    # Simulate yield generation: add 2 units to vault
    # This increases vault value by 25% (8 units -> 10 units)
    # Share price goes from 1:1 to 1.25:1
    boa.env.time_travel(seconds=3600)  # Move forward 1 hour
    alpha_token.transfer(alpha_token_vault.address, 2 * EIGHTEEN_DECIMALS, sender=alpha_token_whale)
    
    # Now wallet has 0 direct + 10 in vault = 100% of trial funds
    # Should return True again
    assert hatchery.doesWalletStillHaveTrialFunds(wallet) == True


def test_does_wallet_still_have_trial_funds_vault_loses_value(
    hatchery, alice, alpha_token, alpha_token_whale, setupTrialFundsWallet,
    alpha_token_vault
):
    """Test when vault loses value, decreasing share price"""

    wallet = setupTrialFundsWallet()
    
    # Deposit all 10 units into vault
    wallet.depositForYield(
        1,  # legoId for mock_yield_lego
        alpha_token.address,
        alpha_token_vault.address,
        10 * EIGHTEEN_DECIMALS,
        sender=alice,
    )
    
    # Initially should have 100% of trial funds
    assert hatchery.doesWalletStillHaveTrialFunds(wallet) == True
    
    # Simulate loss: remove 1 unit from vault
    # This reduces vault from 10 units to 9 units (10% loss)
    # Share price goes from 1:1 to 0.9:1
    boa.env.time_travel(seconds=3600)  # Move forward 1 hour
    alpha_token.transfer(alpha_token_whale, 1 * EIGHTEEN_DECIMALS, sender=alpha_token_vault.address)
    
    # Now wallet has shares worth only 90% of trial funds (9 units)
    # Should return False (below 99% threshold)
    assert hatchery.doesWalletStillHaveTrialFunds(wallet) == False


# clawback trial funds


def test_claw_back_trial_funds_all_in_wallet(hatchery, alice, alpha_token, setupTrialFundsWallet):
    """Test clawing back trial funds when all funds are in the wallet"""
    
    wallet = setupTrialFundsWallet()
    wallet_config = UserWalletConfig.at(wallet.walletConfig())
    
    # Verify initial state
    assert alpha_token.balanceOf(wallet.address) == 10 * EIGHTEEN_DECIMALS
    assert wallet_config.trialFundsAsset() == alpha_token.address
    assert wallet_config.trialFundsAmount() == 10 * EIGHTEEN_DECIMALS
    
    # Record hatchery balance before clawback
    hatchery_balance_before = alpha_token.balanceOf(hatchery.address)
    
    # Claw back trial funds (alice is the owner)
    amount_recovered = hatchery.clawBackTrialFunds(wallet.address, sender=alice)
    
    # Verify funds were transferred to hatchery
    assert amount_recovered == 10 * EIGHTEEN_DECIMALS
    assert alpha_token.balanceOf(wallet.address) == 0
    assert alpha_token.balanceOf(hatchery.address) == hatchery_balance_before + 10 * EIGHTEEN_DECIMALS
    
    # Verify trial funds config was cleared
    assert wallet_config.trialFundsAsset() == ZERO_ADDRESS
    assert wallet_config.trialFundsAmount() == 0


def test_claw_back_trial_funds_all_in_single_vault(
    hatchery, alice, alpha_token, setupTrialFundsWallet, alpha_token_vault
):
    """Test clawing back trial funds when all funds are in a single vault"""
    
    wallet = setupTrialFundsWallet()
    wallet_config = UserWalletConfig.at(wallet.walletConfig())
    
    # Deposit all funds into vault
    wallet.depositForYield(
        1,  # legoId for mock_yield_lego
        alpha_token.address,
        alpha_token_vault.address,
        sender=alice,
    )
    
    # Verify initial state
    assert alpha_token.balanceOf(wallet.address) == 0
    assert alpha_token_vault.balanceOf(wallet.address) > 0
    
    # Record hatchery balance before clawback
    hatchery_balance_before = alpha_token.balanceOf(hatchery.address)
    
    # Claw back trial funds
    amount_recovered = hatchery.clawBackTrialFunds(wallet.address, sender=alice)
    
    # Verify funds were transferred to hatchery
    assert amount_recovered == 10 * EIGHTEEN_DECIMALS
    assert alpha_token.balanceOf(hatchery.address) == hatchery_balance_before + 10 * EIGHTEEN_DECIMALS
    
    # Verify vault shares were withdrawn
    assert alpha_token_vault.balanceOf(wallet.address) == 0
    
    # Verify trial funds config was cleared
    assert wallet_config.trialFundsAsset() == ZERO_ADDRESS
    assert wallet_config.trialFundsAmount() == 0


def test_claw_back_trial_funds_split_across_vaults(
    hatchery, alice, alpha_token, setupTrialFundsWallet,
    alpha_token_vault, alpha_token_vault_2, alpha_token_vault_3
):
    """Test clawing back trial funds when funds are split across multiple vaults"""
    
    wallet = setupTrialFundsWallet()
    wallet_config = UserWalletConfig.at(wallet.walletConfig())
    
    # Split funds across vaults (3, 3, 3 units each, keep 1 in wallet)
    wallet.depositForYield(
        1,  # legoId for mock_yield_lego
        alpha_token.address,
        alpha_token_vault.address,
        3 * EIGHTEEN_DECIMALS,
        sender=alice,
    )
    
    wallet.depositForYield(
        1,  # legoId for mock_yield_lego
        alpha_token.address,
        alpha_token_vault_2.address,
        3 * EIGHTEEN_DECIMALS,
        sender=alice,
    )
    
    wallet.depositForYield(
        1,  # legoId for mock_yield_lego
        alpha_token.address,
        alpha_token_vault_3.address,
        3 * EIGHTEEN_DECIMALS,
        sender=alice,
    )
    
    # Verify initial state
    assert alpha_token.balanceOf(wallet.address) == 1 * EIGHTEEN_DECIMALS
    assert alpha_token_vault.balanceOf(wallet.address) > 0
    assert alpha_token_vault_2.balanceOf(wallet.address) > 0
    assert alpha_token_vault_3.balanceOf(wallet.address) > 0
    
    # Record hatchery balance before clawback
    hatchery_balance_before = alpha_token.balanceOf(hatchery.address)
    
    # Claw back trial funds
    amount_recovered = hatchery.clawBackTrialFunds(wallet.address, sender=alice)
    
    # Verify funds were transferred to hatchery
    assert amount_recovered == 10 * EIGHTEEN_DECIMALS
    assert alpha_token.balanceOf(hatchery.address) == hatchery_balance_before + 10 * EIGHTEEN_DECIMALS
    
    # Verify all funds were withdrawn (wallet should be empty)
    assert alpha_token.balanceOf(wallet.address) == 0
    assert alpha_token_vault.balanceOf(wallet.address) == 0
    assert alpha_token_vault_2.balanceOf(wallet.address) == 0
    assert alpha_token_vault_3.balanceOf(wallet.address) == 0
    
    # Verify trial funds config was cleared
    assert wallet_config.trialFundsAsset() == ZERO_ADDRESS
    assert wallet_config.trialFundsAmount() == 0


def test_claw_back_trial_funds_partial_spent(
    hatchery, alice, alpha_token, setupTrialFundsWallet
):
    """Test clawing back trial funds when some have been spent"""
    
    wallet = setupTrialFundsWallet()
    wallet_config = UserWalletConfig.at(wallet.walletConfig())
    
    # Spend 2 units
    alpha_token.transfer(alice, 2 * EIGHTEEN_DECIMALS, sender=wallet.address)
    
    # Verify initial state
    assert alpha_token.balanceOf(wallet.address) == 8 * EIGHTEEN_DECIMALS
    
    # Record hatchery balance before clawback
    hatchery_balance_before = alpha_token.balanceOf(hatchery.address)
    
    # Claw back trial funds (only 8 units available)
    amount_recovered = hatchery.clawBackTrialFunds(wallet.address, sender=alice)
    
    # Verify only available funds were transferred
    assert amount_recovered == 8 * EIGHTEEN_DECIMALS
    assert alpha_token.balanceOf(wallet.address) == 0
    assert alpha_token.balanceOf(hatchery.address) == hatchery_balance_before + 8 * EIGHTEEN_DECIMALS
    
    # Verify trial funds config was updated (not fully cleared since not all recovered)
    assert wallet_config.trialFundsAsset() == alpha_token.address
    assert wallet_config.trialFundsAmount() == 2 * EIGHTEEN_DECIMALS  # 10 - 8 = 2 remaining


def test_claw_back_trial_funds_with_vault_yield(
    hatchery, alice, alpha_token, alpha_token_whale, setupTrialFundsWallet,
    alpha_token_vault
):
    """Test clawing back trial funds when vault has generated yield"""
    
    wallet = setupTrialFundsWallet()
    wallet_config = UserWalletConfig.at(wallet.walletConfig())
    
    # Deposit all funds into vault
    wallet.depositForYield(
        1,  # legoId for mock_yield_lego
        alpha_token.address,
        alpha_token_vault.address,
        sender=alice,
    )
    
    # Simulate yield generation: add 2 units to vault (20% yield)
    boa.env.time_travel(seconds=3600)
    alpha_token.transfer(alpha_token_vault.address, 2 * EIGHTEEN_DECIMALS, sender=alpha_token_whale)
    
    # Record balances before clawback
    hatchery_balance_before = alpha_token.balanceOf(hatchery.address)
    vault_shares_before = alpha_token_vault.balanceOf(wallet.address)
    
    # Claw back trial funds
    amount_recovered = hatchery.clawBackTrialFunds(wallet.address, sender=alice)
    
    # Verify only the trial amount was recovered (not the yield)
    assert amount_recovered == 10 * EIGHTEEN_DECIMALS
    assert alpha_token.balanceOf(hatchery.address) == hatchery_balance_before + 10 * EIGHTEEN_DECIMALS
    
    # Verify some vault shares remain (the yield portion)
    assert alpha_token_vault.balanceOf(wallet.address) > 0
    assert alpha_token_vault.balanceOf(wallet.address) < vault_shares_before
    
    # Verify trial funds config was cleared
    assert wallet_config.trialFundsAsset() == ZERO_ADDRESS
    assert wallet_config.trialFundsAmount() == 0


def test_claw_back_trial_funds_permissions(
    hatchery, alice, bob, alpha_token, setupTrialFundsWallet, switchboard_alpha
):
    """Test permission requirements for clawing back trial funds"""
    
    wallet = setupTrialFundsWallet()
    
    # Bob (non-owner) should not be able to claw back
    with boa.reverts("no perms"):
        hatchery.clawBackTrialFunds(wallet.address, sender=bob)
    
    # Alice (owner) should be able to claw back
    amount_recovered = hatchery.clawBackTrialFunds(wallet.address, sender=alice)
    assert amount_recovered == 10 * EIGHTEEN_DECIMALS
    
    # Create another wallet for switchboard test
    wallet2 = setupTrialFundsWallet()
    
    # Switchboard should be able to claw back without being owner
    amount_recovered2 = hatchery.clawBackTrialFunds(wallet2.address, sender=switchboard_alpha.address)
    assert amount_recovered2 == 10 * EIGHTEEN_DECIMALS


def test_claw_back_trial_funds_already_clawed_back(
    hatchery, alice, setupTrialFundsWallet
):
    """Test that clawing back already clawed back funds returns 0"""
    
    wallet = setupTrialFundsWallet()
    wallet_config = UserWalletConfig.at(wallet.walletConfig())
    
    # First clawback
    amount_recovered = hatchery.clawBackTrialFunds(wallet.address, sender=alice)
    assert amount_recovered == 10 * EIGHTEEN_DECIMALS
    
    # Verify trial funds config was cleared
    assert wallet_config.trialFundsAsset() == ZERO_ADDRESS
    assert wallet_config.trialFundsAmount() == 0
    
    # Second clawback should return 0
    amount_recovered2 = hatchery.clawBackTrialFunds(wallet.address, sender=alice)
    assert amount_recovered2 == 0


def test_claw_back_trial_funds_vault_loses_value(
    hatchery, alice, alpha_token, alpha_token_whale, setupTrialFundsWallet,
    alpha_token_vault
):
    """Test clawing back when vault has lost value"""
    
    wallet = setupTrialFundsWallet()
    wallet_config = UserWalletConfig.at(wallet.walletConfig())
    
    # Deposit all funds into vault
    wallet.depositForYield(
        1,  # legoId for mock_yield_lego
        alpha_token.address,
        alpha_token_vault.address,
        sender=alice,
    )
    
    # Simulate loss: remove 3 units from vault (30% loss)
    boa.env.time_travel(seconds=3600)
    alpha_token.transfer(alpha_token_whale, 3 * EIGHTEEN_DECIMALS, sender=alpha_token_vault.address)
    
    # Record hatchery balance before clawback
    hatchery_balance_before = alpha_token.balanceOf(hatchery.address)
    
    # Claw back trial funds (only 7 units available due to loss)
    amount_recovered = hatchery.clawBackTrialFunds(wallet.address, sender=alice)
    
    # Verify only available funds were recovered
    assert amount_recovered == 7 * EIGHTEEN_DECIMALS
    assert alpha_token.balanceOf(wallet.address) == 0
    assert alpha_token_vault.balanceOf(wallet.address) == 0
    assert alpha_token.balanceOf(hatchery.address) == hatchery_balance_before + 7 * EIGHTEEN_DECIMALS
    
    # Verify trial funds config shows remaining unrecovered amount
    assert wallet_config.trialFundsAsset() == alpha_token.address
    assert wallet_config.trialFundsAmount() == 3 * EIGHTEEN_DECIMALS  # 10 - 7 = 3 remaining


def test_claw_back_trial_funds_invalid_wallet(hatchery, alice, bob):
    """Test clawing back from non-wallet address reverts"""
    
    # Try to claw back from a regular address (not a wallet)
    with boa.reverts("not a user wallet"):
        hatchery.clawBackTrialFunds(bob, sender=alice)
    
    # Try to claw back from zero address
    with boa.reverts("not a user wallet"):
        hatchery.clawBackTrialFunds(ZERO_ADDRESS, sender=alice)


def test_claw_back_trial_funds_wallet_without_trial_funds(
    hatchery, alice, setUserWalletConfig
):
    """Test clawing back from wallet created without trial funds"""
    
    # Create wallet without trial funds
    setUserWalletConfig(
        _trialAsset=ZERO_ADDRESS,
        _trialAmount=0
    )
    
    wallet_address = hatchery.createUserWallet(sender=alice)
    
    # Clawback should return 0
    amount_recovered = hatchery.clawBackTrialFunds(wallet_address, sender=alice)
    assert amount_recovered == 0


def test_claw_back_trial_funds_rounding_edge_case(
    hatchery, alice, alpha_token, alpha_token_whale, setupTrialFundsWallet,
    alpha_token_vault
):
    """Test the 101% recovery buffer for rounding errors"""
    
    wallet = setupTrialFundsWallet()
    wallet_config = UserWalletConfig.at(wallet.walletConfig())
    
    # Deposit 99% into vault, keep 1% in wallet
    wallet.depositForYield(
        1,  # legoId for mock_yield_lego
        alpha_token.address,
        alpha_token_vault.address,
        int(9.9 * EIGHTEEN_DECIMALS),  # 99% of 10 units
        sender=alice,
    )
    
    # Add tiny amount to vault to simulate rounding benefit
    # This makes the vault have slightly more than deposited
    boa.env.time_travel(seconds=3600)
    alpha_token.transfer(alpha_token_vault.address, 10**15, sender=alpha_token_whale)  # 0.001 units

    # Claw back should recover exactly trial amount (10 units)
    amount_recovered = hatchery.clawBackTrialFunds(wallet.address, sender=alice)
    
    # Should recover exactly the trial amount
    assert amount_recovered == 10 * EIGHTEEN_DECIMALS
    assert wallet_config.trialFundsAsset() == ZERO_ADDRESS
    assert wallet_config.trialFundsAmount() == 0


def test_claw_back_trial_funds_many_vaults_gas_usage(
    hatchery, alice, alpha_token, alpha_token_whale, setUserWalletConfig,
    alpha_token_vault, alpha_token_vault_2, alpha_token_vault_3
):
    """Test clawback with many vault positions to check gas usage"""
    
    # Setup with larger trial amount for splitting
    trial_amount = 20 * EIGHTEEN_DECIMALS
    setUserWalletConfig(
        _trialAsset=alpha_token.address,
        _trialAmount=trial_amount
    )
    
    # Transfer trial funds to hatchery
    alpha_token.transfer(hatchery, trial_amount * 10, sender=alpha_token_whale)
    
    # Create wallet
    wallet_address = hatchery.createUserWallet(sender=alice)
    wallet = UserWallet.at(wallet_address)
    
    # Split funds across multiple vaults in small amounts
    # This tests the iteration through assets in clawback
    vaults = [alpha_token_vault, alpha_token_vault_2, alpha_token_vault_3]
    amount_per_deposit = 2 * EIGHTEEN_DECIMALS
    
    for i in range(9):  # 9 deposits of 2 units each = 18 units
        vault = vaults[i % 3]
        wallet.depositForYield(
            1,  # legoId for mock_yield_lego
            alpha_token.address,
            vault.address,
            amount_per_deposit,
            sender=alice,
        )
    
    # Should have 2 units left in wallet
    assert alpha_token.balanceOf(wallet.address) == 2 * EIGHTEEN_DECIMALS
    
    # Claw back - this will need to withdraw from multiple vault positions
    amount_recovered = hatchery.clawBackTrialFunds(wallet.address, sender=alice)
    
    # Verify all funds recovered
    assert amount_recovered == trial_amount
    assert alpha_token.balanceOf(wallet.address) == 0
    for vault in vaults:
        assert vault.balanceOf(wallet.address) == 0


def test_claw_back_trial_funds_wallet_frozen_state(
    hatchery, alice, mission_control, charlie, alpha_token, setupTrialFundsWallet, switchboard_alpha
):
    """Test clawback when wallet is in frozen state"""

    mission_control.setCanPerformSecurityAction(charlie, True, sender=switchboard_alpha.address)

    wallet = setupTrialFundsWallet()
    wallet_config = UserWalletConfig.at(wallet.walletConfig())
    
    # Freeze the wallet
    wallet_config.setFrozen(True, sender=charlie)
    assert wallet_config.isFrozen() == True
    
    # Clawback should still work when frozen
    amount_recovered = hatchery.clawBackTrialFunds(wallet.address, sender=alice)
    
    # Verify funds were recovered despite frozen state
    assert amount_recovered == 10 * EIGHTEEN_DECIMALS
    assert alpha_token.balanceOf(wallet.address) == 0
    assert wallet_config.trialFundsAsset() == ZERO_ADDRESS
    assert wallet_config.trialFundsAmount() == 0


def test_claw_back_trial_funds_partial_vault_withdrawal(
    hatchery, alice, alpha_token, setupTrialFundsWallet, alpha_token_vault
):
    """Test clawback when it needs exact partial withdrawal from vault"""
    
    wallet = setupTrialFundsWallet()
    wallet_config = UserWalletConfig.at(wallet.walletConfig())
    
    # Keep 3 units in wallet, deposit 7 units
    wallet.depositForYield(
        1,  # legoId for mock_yield_lego
        alpha_token.address,
        alpha_token_vault.address,
        7 * EIGHTEEN_DECIMALS,
        sender=alice,
    )
    
    # Spend 2 units from wallet (leaving 1 unit + 7 in vault = 8 total)
    alpha_token.transfer(alice, 2 * EIGHTEEN_DECIMALS, sender=wallet.address)
    
    # Claw back (needs to withdraw exact amount from vault)
    amount_recovered = hatchery.clawBackTrialFunds(wallet.address, sender=alice)
    
    # Should recover 8 units (all available)
    assert amount_recovered == 8 * EIGHTEEN_DECIMALS
    assert alpha_token.balanceOf(wallet.address) == 0
    assert alpha_token_vault.balanceOf(wallet.address) == 0
    
    # Config should show 2 units unrecovered
    assert wallet_config.trialFundsAsset() == alpha_token.address
    assert wallet_config.trialFundsAmount() == 2 * EIGHTEEN_DECIMALS


# doesWalletStillHaveTrialFunds with vault eligibility tests


def test_does_wallet_still_have_trial_funds_with_eligible_vault(
    hatchery, alice, alpha_token, mock_yield_lego, setupTrialFundsWallet, alpha_token_vault
):
    """Test doesWalletStillHaveTrialFunds when funds are in an eligible vault (sufficient liquidity)"""
    
    wallet = setupTrialFundsWallet()
       
    # Deposit all trial funds into the eligible vault
    wallet.depositForYield(
        1,  # legoId for mock_yield_lego
        alpha_token.address,
        alpha_token_vault.address,
        10 * EIGHTEEN_DECIMALS,
        sender=alice,
    )
    
    # Verify wallet has no direct alpha tokens but has vault shares
    assert alpha_token.balanceOf(wallet.address) == 0
    assert alpha_token_vault.balanceOf(wallet.address) > 0

    # Set vault as eligible (has sufficient liquidity)
    # after deposit, vault has 10 tokens
    mock_yield_lego.setMinTotalAssets(9 * EIGHTEEN_DECIMALS)

    # Should return True because vault is eligible (has sufficient liquidity)
    assert hatchery.doesWalletStillHaveTrialFunds(wallet.address) == True

    # Set vault as ineligible (has insufficient liquidity)
    # after deposit, vault has 10 tokens
    mock_yield_lego.setMinTotalAssets(11 * EIGHTEEN_DECIMALS)
    assert hatchery.doesWalletStillHaveTrialFunds(wallet.address) == False
