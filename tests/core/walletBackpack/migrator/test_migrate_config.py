import pytest
import boa

from constants import ZERO_ADDRESS, EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ONE_MONTH_IN_BLOCKS
from contracts.core.userWallet import UserWallet, UserWalletConfig
from conf_utils import filter_logs


@pytest.fixture(scope="module")
def prepareAssetForMigration(alpha_token, alpha_token_whale, mock_ripe, switchboard_alpha):
    def prepareAssetForMigration(
        _wallet,
        _asset = alpha_token,
        _amount = 100 * EIGHTEEN_DECIMALS,
        _whale = alpha_token_whale,
        _price=2 * EIGHTEEN_DECIMALS
    ):
        # Set price
        mock_ripe.setPrice(_asset, _price)
        
        # Transfer asset to wallet  
        _asset.transfer(_wallet, _amount, sender=_whale)
        
        # Register asset in wallet
        wallet_config = UserWalletConfig.at(_wallet.walletConfig())
        wallet_config.updateAssetData(
            0,  # _op
            _asset,
            False,  # _shouldCheckYield
            sender=switchboard_alpha.address
        )
        
        return _amount
    
    yield prepareAssetForMigration


###############################
# Migration Config Validation #
###############################


# Test successful config copy scenario
def test_can_copy_config_valid(migrator, user_wallet, hatchery, bob):
    """Test valid config copy scenario where all conditions are met"""
    # Create a new wallet for config copy (toWallet)
    new_wallet_addr = hatchery.createUserWallet(sender=bob)
    new_wallet = UserWallet.at(new_wallet_addr)
    
    # Should be able to copy config
    assert migrator.canCopyWalletConfig(user_wallet, new_wallet, bob)


# Test wallet validation failures
def test_cannot_copy_config_non_underscore_wallets(migrator, user_wallet, bob, alice):
    """Test that config copy fails if either wallet is not an Underscore wallet"""
    # Test with non-underscore fromWallet
    assert not migrator.canCopyWalletConfig(alice, user_wallet, bob)
    
    # Test with non-underscore toWallet
    assert not migrator.canCopyWalletConfig(user_wallet, alice, bob)
    
    # Test with both non-underscore
    assert not migrator.canCopyWalletConfig(alice, alice, bob)


# Test ownership validation
def test_cannot_copy_config_if_not_owner(migrator, user_wallet, hatchery, bob, alice):
    """Test that only the owner of toWallet can initiate config copy"""
    # Create new wallet owned by bob
    new_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    
    # Alice (not owner) cannot copy config to bob's wallet
    assert not migrator.canCopyWalletConfig(user_wallet, new_wallet, alice)


def test_cannot_copy_config_with_different_owners(migrator, user_wallet, hatchery, bob, alice):
    """Test that fromWallet and toWallet must have the same owner"""
    # Create new wallet owned by alice
    new_wallet = UserWallet.at(hatchery.createUserWallet(sender=alice))
    
    # Cannot copy config between wallets with different owners
    assert not migrator.canCopyWalletConfig(user_wallet, new_wallet, alice)


# Test frozen wallet restriction
def test_cannot_copy_config_frozen_wallets(migrator, user_wallet, user_wallet_config, hatchery, bob):
    """Test that frozen wallets cannot have their config copied (either from or to)"""
    # Create new wallet
    new_wallet_addr = hatchery.createUserWallet(sender=bob)
    new_wallet = UserWallet.at(new_wallet_addr)
    new_wallet_config = UserWalletConfig.at(new_wallet.walletConfig())
    
    # Freeze the fromWallet
    user_wallet_config.setFrozen(True, sender=bob)
    assert not migrator.canCopyWalletConfig(user_wallet, new_wallet, bob)
    
    # Unfreeze fromWallet and freeze toWallet
    user_wallet_config.setFrozen(False, sender=bob)
    new_wallet_config.setFrozen(True, sender=bob)
    assert not migrator.canCopyWalletConfig(user_wallet, new_wallet, bob)


# Test pending ownership change restriction
def test_cannot_copy_config_with_pending_owner_change(migrator, user_wallet, user_wallet_config, hatchery, bob, alice):
    """Test that wallets with pending ownership changes cannot have config copied"""
    # Create new wallet
    new_wallet_addr = hatchery.createUserWallet(sender=bob)
    new_wallet = UserWallet.at(new_wallet_addr)
    new_wallet_config = UserWalletConfig.at(new_wallet.walletConfig())
    
    # Initiate ownership change on fromWallet
    user_wallet_config.changeOwnership(alice, sender=bob)
    assert not migrator.canCopyWalletConfig(user_wallet, new_wallet, bob)
    
    # Test cloneConfig fails with proper revert
    with boa.reverts("cannot copy config"):
        migrator.cloneConfig(user_wallet, new_wallet, sender=bob)
    
    # Cancel ownership change on fromWallet
    user_wallet_config.cancelOwnershipChange(sender=bob)
    
    # Initiate ownership change on toWallet
    new_wallet_config.changeOwnership(alice, sender=bob)
    assert not migrator.canCopyWalletConfig(user_wallet, new_wallet, bob)
    
    # Test cloneConfig fails with proper revert
    with boa.reverts("cannot copy config"):
        migrator.cloneConfig(user_wallet, new_wallet, sender=bob)


# Test group ID restriction
def test_cannot_copy_config_different_group_ids(migrator, user_wallet, hatchery, bob):
    """Test that wallets must have the same group ID to copy config"""
    # Create new wallet with different group ID
    new_wallet = UserWallet.at(hatchery.createUserWallet(bob, ZERO_ADDRESS, 2, sender=bob))
    
    # Cannot copy config between different group IDs
    assert not migrator.canCopyWalletConfig(user_wallet, new_wallet, bob)


# Test payee restrictions
def test_cannot_copy_config_with_payees(migrator, user_wallet, hatchery, bob, alice, paymaster, createPayeeSettings):
    """Test that toWallet cannot have payees (more than default)"""
    # Create new wallet
    new_wallet_addr = hatchery.createUserWallet(sender=bob)
    new_wallet = UserWallet.at(new_wallet_addr)
    new_wallet_config = UserWalletConfig.at(new_wallet.walletConfig())
    
    # Add a payee to the new wallet
    payee_settings = createPayeeSettings()
    new_wallet_config.addPayee(alice, payee_settings, sender=paymaster.address)
    
    # Cannot copy config to wallet with payees
    assert not migrator.canCopyWalletConfig(user_wallet, new_wallet, bob)


# Test whitelist restrictions
def test_cannot_copy_config_with_whitelisted_addresses(migrator, user_wallet, hatchery, bob, alice):
    """Test that toWallet cannot have whitelisted addresses (more than default)"""
    # Create new wallet
    new_wallet_addr = hatchery.createUserWallet(sender=bob)
    new_wallet = UserWallet.at(new_wallet_addr)
    new_wallet_config = UserWalletConfig.at(new_wallet.walletConfig())
    
    # Add whitelisted address
    new_wallet_config.addWhitelistAddrViaMigrator(alice, sender=migrator.address)
    
    # Cannot copy config to wallet with whitelisted addresses
    assert not migrator.canCopyWalletConfig(user_wallet, new_wallet, bob)


# Test cheque restrictions
def test_cannot_copy_config_with_active_cheques(migrator, hatchery, bob, alice, user_wallet, user_wallet_config, cheque_book, alpha_token, mock_ripe):
    """Test that toWallet cannot have active cheques"""
    ONE_WEEK_IN_BLOCKS = 7 * ONE_DAY_IN_BLOCKS

    # Get timeLock value
    timeLock = user_wallet_config.timeLock()

    # Travel past timelock to allow cheque settings change
    boa.env.time_travel(blocks=timeLock + 1)

    # Setup cheque settings
    cheque_book.setChequeSettings(
        user_wallet.address,
        0,  # maxNumActiveCheques
        0,  # maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # instantUsdThreshold
        0,  # perPeriodPaidUsdCap
        0,  # maxNumChequesPaidPerPeriod
        0,  # payCooldownBlocks
        0,  # perPeriodCreatedUsdCap
        0,  # maxNumChequesCreatedPerPeriod
        0,  # createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # periodLength
        ONE_DAY_IN_BLOCKS,  # expensiveDelayBlocks
        0,  # defaultExpiryBlocks
        [],  # allowedAssets
        True,  # canManagersCreateCheques
        True,  # canManagerPay
        False,  # canBePulled
        sender=bob
    )

    # Set price for the asset
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)  # $1 per token

    # Create an active cheque on user_wallet
    amount = 50 * EIGHTEEN_DECIMALS
    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        ONE_DAY_IN_BLOCKS,  # delayBlocks
        ONE_WEEK_IN_BLOCKS,  # expiryBlocks
        True,  # canManagerPay
        False,  # canBePulled
        sender=bob
    )

    # Verify cheque is active
    assert user_wallet_config.numActiveCheques() == 1

    # Create a new source wallet
    from_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))

    # Cannot copy config from new wallet to user_wallet (which has active cheques)
    assert not migrator.canCopyWalletConfig(from_wallet, user_wallet, bob)


# Test manager restrictions - no starting agent
def test_cannot_copy_config_with_managers_no_starting_agent(migrator, hatchery, bob, alice, high_command, createManagerSettings, mission_control, switchboard_alpha):
    """Test that toWallet cannot have managers when there's no starting agent"""
    # Clear starting agent
    mission_control.setStarterAgent(ZERO_ADDRESS, sender=switchboard_alpha.address)
    
    # Create new wallet without starting agent
    new_wallet_addr = hatchery.createUserWallet(sender=bob)
    new_wallet = UserWallet.at(new_wallet_addr)
    new_wallet_config = UserWalletConfig.at(new_wallet.walletConfig())
    
    # Verify no starting agent
    assert new_wallet_config.startingAgent() == ZERO_ADDRESS
    
    # Add a manager
    manager_settings = createManagerSettings()
    new_wallet_config.addManager(alice, manager_settings, sender=high_command.address)
    
    # Create fromWallet
    from_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    
    # Cannot copy config to wallet with managers when no starting agent
    assert not migrator.canCopyWalletConfig(from_wallet, new_wallet, bob)


# Test manager restrictions - with starting agent
def test_manager_restrictions_with_starting_agent(migrator, user_wallet, hatchery, bob, alice, high_command, createManagerSettings, starter_agent):
    """Test manager restrictions when toWallet has a starting agent"""
    # Create new wallet (will have starter_agent as manager)
    new_wallet_addr = hatchery.createUserWallet(sender=bob)
    new_wallet = UserWallet.at(new_wallet_addr)
    new_wallet_config = UserWalletConfig.at(new_wallet.walletConfig())
    
    # Verify starting agent is set and is first manager
    assert new_wallet_config.startingAgent() == starter_agent.address
    assert new_wallet_config.indexOfManager(starter_agent.address) == 1
    assert new_wallet_config.numManagers() == 2  # 0 + starter_agent
    
    # Should be able to copy config with just starting agent
    assert migrator.canCopyWalletConfig(user_wallet, new_wallet, bob)
    
    # Add another manager
    manager_settings = createManagerSettings()
    new_wallet_config.addManager(alice, manager_settings, sender=high_command.address)
    
    # Cannot copy config with additional managers beyond starting agent
    assert not migrator.canCopyWalletConfig(user_wallet, new_wallet, bob)


def test_starting_agent_at_correct_index(migrator, user_wallet, hatchery, bob, starter_agent):
    """Test that starting agent must be at index 1 for valid config copy"""
    # Create new wallet with starting agent
    new_wallet_addr = hatchery.createUserWallet(sender=bob)
    new_wallet = UserWallet.at(new_wallet_addr)
    new_wallet_config = UserWalletConfig.at(new_wallet.walletConfig())
    
    # Verify starting agent is at index 1 (this is a contract invariant)
    assert new_wallet_config.startingAgent() == starter_agent.address
    assert new_wallet_config.indexOfManager(starter_agent.address) == 1
    
    # Should be valid for config copy with starting agent at correct index
    assert migrator.canCopyWalletConfig(user_wallet, new_wallet, bob)


# Test edge cases
def test_can_copy_config_empty_wallets(migrator, hatchery, bob):
    """Test that config can be copied between empty wallets"""
    # Create two new empty wallets
    from_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    to_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    
    # Should be able to copy config between empty wallets
    assert migrator.canCopyWalletConfig(from_wallet, to_wallet, bob)


def test_migration_bundle_data_for_config(migrator, user_wallet, user_wallet_config, bob):
    """Test getMigrationConfigBundle returns correct data for config validation"""
    # Get migration config bundle
    bundle = migrator.getMigrationConfigBundle(user_wallet)
    
    # Verify bundle data matches wallet config
    assert bundle.owner == bob
    assert bundle.isFrozen == user_wallet_config.isFrozen()
    assert bundle.numPayees == user_wallet_config.numPayees()
    assert bundle.numWhitelisted == user_wallet_config.numWhitelisted()
    assert bundle.numManagers == user_wallet_config.numManagers()
    assert bundle.startingAgent == user_wallet_config.startingAgent()
    assert bundle.hasPendingOwnerChange == user_wallet_config.hasPendingOwnerChange()
    assert bundle.groupId == user_wallet_config.groupId()
    
    # Verify starting agent index
    if bundle.startingAgent != ZERO_ADDRESS:
        assert bundle.startingAgentIndex == user_wallet_config.indexOfManager(bundle.startingAgent)


# Additional test specific to config copy - no trial funds restriction
def test_config_copy_validation_caller_validation(migrator, hatchery, bob, alice):
    """Test that caller must be owner of toWallet to initiate config copy"""
    # Create two wallets owned by bob
    from_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    to_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    
    # Bob (owner) can initiate config copy
    assert migrator.canCopyWalletConfig(from_wallet, to_wallet, bob)
    
    # Alice (not owner) cannot initiate config copy
    assert not migrator.canCopyWalletConfig(from_wallet, to_wallet, alice)


################
# Clone Config #
################


def test_clone_config_validation_revert(migrator, user_wallet, alice):
    """Test that cloneConfig reverts with proper message if validation fails"""
    # Try to clone config with invalid parameters (non-wallet address)
    with boa.reverts("cannot copy config"):
        migrator.cloneConfig(user_wallet, alice, sender=alice)


def test_clone_config_empty_wallets(migrator, hatchery, bob):
    """Test cloning config between empty wallets"""
    # Create two empty wallets
    from_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    to_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    
    # Clone config
    result = migrator.cloneConfig(from_wallet, to_wallet, sender=bob)
    assert result is True
    
    # Check event
    event = filter_logs(migrator, "ConfigCloned")[0]
    assert event.fromWallet == from_wallet.address
    assert event.toWallet == to_wallet.address
    assert event.numManagersCopied == 0
    assert event.numPayeesCopied == 0
    assert event.numWhitelistCopied == 0


def test_clone_config_with_managers(migrator, hatchery, bob, alice, charlie, high_command, createManagerSettings):
    """Test cloning config with managers (excluding starting agent)"""
    # Create source wallet with managers
    from_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    from_config = UserWalletConfig.at(from_wallet.walletConfig())
    
    # Move forward in blocks to ensure meaningful startBlock values
    boa.env.time_travel(blocks=10)
    
    # Add managers to source wallet
    manager_settings1 = createManagerSettings()
    from_config.addManager(alice, manager_settings1, sender=high_command.address)
    
    # Move forward more blocks
    boa.env.time_travel(blocks=5)
    
    manager_settings2 = createManagerSettings()
    from_config.addManager(charlie, manager_settings2, sender=high_command.address)
    
    # Create target wallet
    to_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    to_config = UserWalletConfig.at(to_wallet.walletConfig())
    
    # Get starting agent (should be skipped during copy)
    starting_agent = from_config.startingAgent()
    
    # Clone config
    result = migrator.cloneConfig(from_wallet, to_wallet, sender=bob)
    assert result is True
    
    # Verify managers were copied (excluding starting agent)
    assert to_config.numManagers() == 4  # 0 + starting_agent + alice + charlie
    
    # Verify specific manager settings
    copied_alice_settings = to_config.managerSettings(alice)
    copied_charlie_settings = to_config.managerSettings(charlie)
    assert copied_alice_settings[0] == manager_settings1[0]  # startBlock
    assert copied_charlie_settings[0] == manager_settings2[0]  # startBlock
    
    # Verify starting agent was NOT copied again
    assert to_config.managers(1) == starting_agent  # Starting agent already at index 1
    
    # Check event
    event = filter_logs(migrator, "ConfigCloned")[0]
    assert event.numManagersCopied == 2  # alice and charlie, not starting agent


def test_clone_config_with_payees(migrator, hatchery, bob, alice, charlie, paymaster, createPayeeSettings):
    """Test cloning config with payees"""
    # Create source wallet with payees
    from_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    from_config = UserWalletConfig.at(from_wallet.walletConfig())
    
    # Move forward in blocks to ensure meaningful startBlock values
    boa.env.time_travel(blocks=8)
    
    # Add payees to source wallet
    payee_settings1 = createPayeeSettings()
    from_config.addPayee(alice, payee_settings1, sender=paymaster.address)
    
    # Move forward more blocks
    boa.env.time_travel(blocks=3)
    
    payee_settings2 = createPayeeSettings()
    from_config.addPayee(charlie, payee_settings2, sender=paymaster.address)
    
    # Create target wallet
    to_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    to_config = UserWalletConfig.at(to_wallet.walletConfig())
    
    # Clone config
    result = migrator.cloneConfig(from_wallet, to_wallet, sender=bob)
    assert result is True
    
    # Verify payees were copied
    assert to_config.numPayees() == 3  # 0 + alice + charlie
    
    # Verify specific payee settings
    copied_alice_settings = to_config.payeeSettings(alice)
    copied_charlie_settings = to_config.payeeSettings(charlie)
    assert copied_alice_settings[0] == payee_settings1[0]  # startBlock
    assert copied_charlie_settings[0] == payee_settings2[0]  # startBlock
    
    # Check event
    event = filter_logs(migrator, "ConfigCloned")[0]
    assert event.numPayeesCopied == 2


def test_clone_config_with_whitelist(migrator, hatchery, bob, alice, charlie):
    """Test cloning config with whitelisted addresses"""
    # Create source wallet with whitelisted addresses
    from_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    from_config = UserWalletConfig.at(from_wallet.walletConfig())
    
    # Add whitelisted addresses to source wallet
    from_config.addWhitelistAddrViaMigrator(alice, sender=migrator.address)
    from_config.addWhitelistAddrViaMigrator(charlie, sender=migrator.address)
    
    # Create target wallet
    to_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    to_config = UserWalletConfig.at(to_wallet.walletConfig())
    
    # Clone config
    result = migrator.cloneConfig(from_wallet, to_wallet, sender=bob)
    assert result is True
    
    # Verify whitelist addresses were copied
    assert to_config.numWhitelisted() == 3  # 0 + alice + charlie
    assert to_config.whitelistAddr(1) == alice
    assert to_config.whitelistAddr(2) == charlie
    
    # Check event
    event = filter_logs(migrator, "ConfigCloned")[0]
    assert event.numWhitelistCopied == 2


def test_clone_config_comprehensive(migrator, hatchery, bob, alice, charlie, high_command, paymaster, createManagerSettings, createPayeeSettings):
    """Test cloning config with all types of settings"""
    # Create source wallet with comprehensive config
    from_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    from_config = UserWalletConfig.at(from_wallet.walletConfig())
    
    # Move forward in blocks to ensure meaningful startBlock values
    boa.env.time_travel(blocks=12)
    
    # Add managers
    manager_settings = createManagerSettings()
    from_config.addManager(alice, manager_settings, sender=high_command.address)
    
    # Move forward more blocks
    boa.env.time_travel(blocks=6)
    
    # Add payees
    payee_settings = createPayeeSettings()
    from_config.addPayee(charlie, payee_settings, sender=paymaster.address)
    
    # Add whitelist
    from_config.addWhitelistAddrViaMigrator(alice, sender=migrator.address)
    
    # Create target wallet
    to_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    to_config = UserWalletConfig.at(to_wallet.walletConfig())
    
    # Store initial counts
    initial_managers = to_config.numManagers()
    initial_payees = to_config.numPayees()
    initial_whitelist = to_config.numWhitelisted()
    
    # Clone config
    result = migrator.cloneConfig(from_wallet, to_wallet, sender=bob)
    assert result is True
    
    # Verify all settings were copied
    assert to_config.numManagers() == initial_managers + 1  # +alice
    assert to_config.numPayees() == initial_payees + 1     # +charlie
    assert to_config.numWhitelisted() == initial_whitelist + 1  # +alice
    
    # Verify settings are correct
    assert to_config.managerSettings(alice)[0] == manager_settings[0]  # startBlock
    assert to_config.payeeSettings(charlie)[0] == payee_settings[0]  # startBlock
    assert to_config.whitelistAddr(1) == alice
    
    # Check comprehensive event
    event = filter_logs(migrator, "ConfigCloned")[0]
    assert event.fromWallet == from_wallet.address
    assert event.toWallet == to_wallet.address
    assert event.numManagersCopied == 1
    assert event.numPayeesCopied == 1
    assert event.numWhitelistCopied == 1


def test_clone_config_global_settings(migrator, hatchery, bob, high_command, paymaster, createGlobalManagerSettings, createGlobalPayeeSettings, alpha_token, bravo_token):
    """Test that global settings are copied correctly"""
    # Create source wallet and configure global settings
    from_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    from_config = UserWalletConfig.at(from_wallet.walletConfig())
    
    # Create custom global manager settings with unique values
    global_manager_settings = createGlobalManagerSettings(
        _managerPeriod=100,  # unique value
        _startDelay=50,      # unique value 
        _activationLength=200,  # unique value
        _canOwnerManage=False,  # different from default
        _allowedAssets=[alpha_token.address, bravo_token.address]
    )
    from_config.setGlobalManagerSettings(global_manager_settings, sender=high_command.address)
    
    # Create custom global payee settings with unique values
    global_payee_settings = createGlobalPayeeSettings(
        _defaultPeriodLength=150,  # unique value
        _startDelay=75,            # unique value
        _activationLength=300,     # unique value
        _maxNumTxsPerPeriod=25,    # unique value
        _txCooldownBlocks=10,      # unique value
        _failOnZeroPrice=True,     # different from default
        _canPayOwner=False         # different from default
    )
    from_config.setGlobalPayeeSettings(global_payee_settings, sender=paymaster.address)
    
    # Create target wallet
    to_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    to_config = UserWalletConfig.at(to_wallet.walletConfig())
    
    # Clone config
    result = migrator.cloneConfig(from_wallet, to_wallet, sender=bob)
    assert result is True
    
    # Verify global manager settings were copied
    copied_global_manager = to_config.globalManagerSettings()
    assert copied_global_manager.managerPeriod == 100
    assert copied_global_manager.startDelay == 50
    assert copied_global_manager.activationLength == 200
    assert copied_global_manager.canOwnerManage == False
    assert len(copied_global_manager.allowedAssets) == 2
    assert alpha_token.address in copied_global_manager.allowedAssets
    assert bravo_token.address in copied_global_manager.allowedAssets
    
    # Verify global payee settings were copied
    copied_global_payee = to_config.globalPayeeSettings()
    assert copied_global_payee.defaultPeriodLength == 150
    assert copied_global_payee.startDelay == 75
    assert copied_global_payee.activationLength == 300
    assert copied_global_payee.maxNumTxsPerPeriod == 25
    assert copied_global_payee.txCooldownBlocks == 10
    assert copied_global_payee.failOnZeroPrice == True
    assert copied_global_payee.canPayOwner == False


def test_clone_config_starting_agent_exclusion(migrator, hatchery, bob, alice, charlie, high_command, createManagerSettings, starter_agent):
    """Test that starting agent from source wallet is properly excluded during copy"""
    # Create source wallet with starting agent and other managers
    from_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    from_config = UserWalletConfig.at(from_wallet.walletConfig())
    
    # Verify starting agent exists
    assert from_config.startingAgent() == starter_agent.address
    
    # Move forward in blocks to ensure meaningful startBlock values
    boa.env.time_travel(blocks=15)
    
    # Add other managers
    manager_settings1 = createManagerSettings()
    from_config.addManager(alice, manager_settings1, sender=high_command.address)
    
    # Move forward more blocks
    boa.env.time_travel(blocks=4)
    
    manager_settings2 = createManagerSettings()
    from_config.addManager(charlie, manager_settings2, sender=high_command.address)
    
    # Create target wallet (will have its own starting agent)
    to_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    to_config = UserWalletConfig.at(to_wallet.walletConfig())
    
    # Verify target has starting agent
    assert to_config.startingAgent() == starter_agent.address
    
    # Clone config
    result = migrator.cloneConfig(from_wallet, to_wallet, sender=bob)
    assert result is True
    
    # Verify starting agent wasn't duplicated
    # Target should have: starting_agent + alice + charlie = 3 total managers
    assert to_config.numManagers() == 4  # 0 + starting_agent + alice + charlie
    
    # Verify starting agent is still at index 1
    assert to_config.managers(1) == starter_agent.address
    
    # Verify copied manager settings
    assert to_config.managerSettings(alice)[0] == manager_settings1[0]  # startBlock
    assert to_config.managerSettings(charlie)[0] == manager_settings2[0]  # startBlock
    
    # Check event shows only non-starting-agent managers were copied
    event = filter_logs(migrator, "ConfigCloned")[0]
    assert event.numManagersCopied == 2  # alice and charlie, not starting agent


############################
# Migrate - Funds & Config #
############################


def test_migrate_all_funds_and_config(migrator, hatchery, bob, alice, high_command, createManagerSettings, alpha_token, prepareAssetForMigration):
    """Test migrateAll successfully migrates both funds and config"""
    # Create source wallet with both funds and config
    from_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    from_config = UserWalletConfig.at(from_wallet.walletConfig())
    
    # Add funds to source wallet
    prepareAssetForMigration(from_wallet, alpha_token, 100 * 10**18)
    
    # Move forward in blocks and add config
    boa.env.time_travel(blocks=10)
    manager_settings = createManagerSettings()
    from_config.addManager(alice, manager_settings, sender=high_command.address)
    
    # Create target wallet
    to_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    to_config = UserWalletConfig.at(to_wallet.walletConfig())
    
    # Verify initial state
    assert alpha_token.balanceOf(from_wallet) == 100 * 10**18
    assert alpha_token.balanceOf(to_wallet) == 0
    assert to_config.numManagers() == 2  # 0 + starting_agent
    
    # Migrate all
    num_funds_migrated, did_migrate_config = migrator.migrateAll(from_wallet, to_wallet, sender=bob)
    
    # Verify funds were migrated
    assert num_funds_migrated == 1
    assert alpha_token.balanceOf(from_wallet) == 0
    assert alpha_token.balanceOf(to_wallet) == 100 * 10**18
    
    # Verify config was migrated
    assert did_migrate_config == True
    assert to_config.numManagers() == 3  # 0 + starting_agent + alice
    assert to_config.managerSettings(alice)[0] == manager_settings[0]  # startBlock
    
    # Verify both events were emitted
    funds_events = filter_logs(migrator, "FundsMigrated")
    config_events = filter_logs(migrator, "ConfigCloned")
    assert len(funds_events) == 1
    assert len(config_events) == 1
    assert funds_events[0].numAssetsMigrated == 1
    assert config_events[0].numManagersCopied == 1


def test_migrate_all_both_succeed(migrator, hatchery, bob, alpha_token, prepareAssetForMigration):
    """Test migrateAll when both funds and config migration succeed"""
    # Create fresh wallets
    from_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    to_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    
    # Add funds to source
    prepareAssetForMigration(from_wallet, alpha_token, 75 * EIGHTEEN_DECIMALS)
    
    # Both should succeed since both wallets are fresh and compatible
    num_funds_migrated, did_migrate_config = migrator.migrateAll(from_wallet, to_wallet, sender=bob)
    
    # Both should succeed
    assert num_funds_migrated == 1
    assert did_migrate_config == True
    assert alpha_token.balanceOf(to_wallet) == 75 * EIGHTEEN_DECIMALS


def test_migrate_all_config_only(migrator, hatchery, bob, alice, high_command, createManagerSettings):
    """Test migrateAll when only config can be migrated (no funds to migrate)"""
    # Create source wallet with config but no funds
    from_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    from_config = UserWalletConfig.at(from_wallet.walletConfig())
    
    # Move forward in blocks and add config
    boa.env.time_travel(blocks=8)
    manager_settings = createManagerSettings()
    from_config.addManager(alice, manager_settings, sender=high_command.address)
    
    # Create target wallet
    to_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    to_config = UserWalletConfig.at(to_wallet.walletConfig())
    
    # Verify source wallet has no assets to migrate (only ETH at index 0)
    assert from_wallet.numAssets() == 1
    
    # Migrate all
    num_funds_migrated, did_migrate_config = migrator.migrateAll(from_wallet, to_wallet, sender=bob)
    
    # Verify only config was migrated
    assert num_funds_migrated == 0
    assert did_migrate_config == True
    assert to_config.numManagers() == 3  # 0 + starting_agent + alice
    
    # Verify only config event was emitted
    funds_events = filter_logs(migrator, "FundsMigrated")
    config_events = filter_logs(migrator, "ConfigCloned")
    assert len(funds_events) == 0
    assert len(config_events) == 1
    assert config_events[0].numManagersCopied == 1


def test_migrate_all_nothing_to_migrate(migrator, hatchery, bob):
    """Test migrateAll fails when neither funds nor config can be migrated"""
    # Create two empty wallets with different group IDs (blocks config migration)
    from_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    to_wallet = UserWallet.at(hatchery.createUserWallet(bob, ZERO_ADDRESS, 2, sender=bob))
    
    # Verify no assets to migrate and config migration blocked by different group IDs
    assert from_wallet.numAssets() == 1  # Only ETH
    assert not migrator.canCopyWalletConfig(from_wallet, to_wallet, bob)
    
    # migrateAll should fail
    with boa.reverts("no funds or config to migrate"):
        migrator.migrateAll(from_wallet, to_wallet, sender=bob)


def test_migrate_all_partial_funds_migration(migrator, hatchery, bob, alice, high_command, createManagerSettings, alpha_token, bravo_token, alpha_token_whale, bravo_token_whale, prepareAssetForMigration):
    """Test migrateAll with multiple assets where some have zero balance"""
    # Create source wallet
    from_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    from_config = UserWalletConfig.at(from_wallet.walletConfig())
    
    # Add one asset with balance and one with zero balance
    prepareAssetForMigration(from_wallet, alpha_token, 75 * 10**18, alpha_token_whale)
    prepareAssetForMigration(from_wallet, bravo_token, 0, bravo_token_whale)  # Zero balance
    
    # Add config
    boa.env.time_travel(blocks=5)
    manager_settings = createManagerSettings()
    from_config.addManager(alice, manager_settings, sender=high_command.address)
    
    # Create target wallet
    to_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    
    # Migrate all
    num_funds_migrated, did_migrate_config = migrator.migrateAll(from_wallet, to_wallet, sender=bob)
    
    # Verify results
    assert num_funds_migrated == 1  # Only alpha_token migrated (bravo had zero balance)
    assert did_migrate_config == True
    assert alpha_token.balanceOf(to_wallet) == 75 * 10**18
    assert bravo_token.balanceOf(to_wallet) == 0
    
    # Verify events
    funds_events = filter_logs(migrator, "FundsMigrated")
    config_events = filter_logs(migrator, "ConfigCloned")
    assert len(funds_events) == 1
    assert len(config_events) == 1
    assert funds_events[0].numAssetsMigrated == 1  # Only one asset actually migrated


