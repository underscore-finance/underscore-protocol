import pytest
import boa

from constants import ZERO_ADDRESS, EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ONE_MONTH_IN_BLOCKS
from contracts.core.userWallet import UserWallet, UserWalletConfig
from conf_utils import filter_logs


########################
# Migration Validation #
########################


# Test successful migration scenario
def test_can_migrate_funds_valid(migrator, user_wallet, hatchery, bob):
    """Test valid migration scenario where all conditions are met"""
    # Create a new wallet for migration (toWallet)
    new_wallet_addr = hatchery.createUserWallet(sender=bob)
    new_wallet = UserWallet.at(new_wallet_addr)
    
    # Should be able to migrate
    assert migrator.canMigrateFundsToNewWallet(user_wallet, new_wallet, bob)


# Test wallet validation failures
def test_cannot_migrate_non_underscore_wallets(migrator, user_wallet, bob, alice):
    """Test that migration fails if either wallet is not an Underscore wallet"""
    # Test with non-underscore fromWallet
    assert not migrator.canMigrateFundsToNewWallet(alice, user_wallet, bob)
    
    # Test with non-underscore toWallet
    assert not migrator.canMigrateFundsToNewWallet(user_wallet, alice, bob)
    
    # Test with both non-underscore
    assert not migrator.canMigrateFundsToNewWallet(alice, alice, bob)


# Test ownership validation
def test_cannot_migrate_if_not_owner(migrator, user_wallet, hatchery, bob, alice):
    """Test that only the owner can initiate migration"""
    # Create new wallet owned by bob
    new_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    
    # Alice (not owner) cannot migrate bob's wallet
    assert not migrator.canMigrateFundsToNewWallet(user_wallet, new_wallet, alice)


def test_cannot_migrate_with_different_owners(migrator, user_wallet, hatchery, bob, alice):
    """Test that fromWallet and toWallet must have the same owner"""
    # Create new wallet owned by alice
    new_wallet = UserWallet.at(hatchery.createUserWallet(sender=alice))
    
    # Cannot migrate between wallets with different owners
    assert not migrator.canMigrateFundsToNewWallet(user_wallet, new_wallet, bob)


# Test trial funds are automatically handled during migration
def test_migrate_with_trial_funds_clawback(migrator, hatchery, bob, alpha_token, alpha_token_whale, setUserWalletConfig, bravo_token, bravo_token_whale, switchboard_alpha):
    """Test that migration automatically claws back trial funds and proceeds"""
    # Configure trial funds
    trial_amount = 10 * EIGHTEEN_DECIMALS
    setUserWalletConfig(
        _trialAsset=alpha_token.address,
        _trialAmount=trial_amount
    )
    
    # Fund hatchery
    alpha_token.transfer(hatchery, trial_amount * 10, sender=alpha_token_whale)
    
    # Create wallet with trial funds
    wallet_with_trial = UserWallet.at(hatchery.createUserWallet(sender=bob))
    wallet_config = UserWalletConfig.at(wallet_with_trial.walletConfig())
    
    # Add another asset to migrate
    bravo_amount = 50 * EIGHTEEN_DECIMALS
    bravo_token.transfer(wallet_with_trial, bravo_amount, sender=bravo_token_whale)
    wallet_config.updateAssetData(0, bravo_token, False, sender=switchboard_alpha.address)
    
    # Create target wallet
    new_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    
    # Verify can migrate (trial funds will be handled automatically)
    assert migrator.canMigrateFundsToNewWallet(wallet_with_trial, new_wallet, bob)
    
    # Record hatchery balance before migration
    hatchery_balance_before = alpha_token.balanceOf(hatchery.address)
    
    # Migrate funds - should automatically claw back trial funds first
    num_migrated = migrator.migrateFunds(wallet_with_trial, new_wallet, sender=bob)
    
    # Verify trial funds were clawed back to hatchery
    assert alpha_token.balanceOf(hatchery.address) == hatchery_balance_before + trial_amount
    
    # Verify trial funds config was cleared
    assert wallet_config.trialFundsAsset() == ZERO_ADDRESS
    assert wallet_config.trialFundsAmount() == 0
    
    # Verify other assets were migrated
    assert num_migrated == 1  # Only bravo token (trial funds were clawed back, not migrated)
    assert bravo_token.balanceOf(wallet_with_trial) == 0
    assert bravo_token.balanceOf(new_wallet) == bravo_amount


# Test frozen wallet restriction
def test_cannot_migrate_frozen_wallets(migrator, user_wallet, user_wallet_config, hatchery, bob):
    """Test that frozen wallets cannot be migrated (either from or to)"""
    # Create new wallet
    new_wallet_addr = hatchery.createUserWallet(sender=bob)
    new_wallet = UserWallet.at(new_wallet_addr)
    new_wallet_config = UserWalletConfig.at(new_wallet.walletConfig())
    
    # Freeze the fromWallet
    user_wallet_config.setFrozen(True, sender=bob)
    assert not migrator.canMigrateFundsToNewWallet(user_wallet, new_wallet, bob)
    
    # Unfreeze fromWallet and freeze toWallet
    user_wallet_config.setFrozen(False, sender=bob)
    new_wallet_config.setFrozen(True, sender=bob)
    assert not migrator.canMigrateFundsToNewWallet(user_wallet, new_wallet, bob)


# Test pending ownership change restriction
def test_cannot_migrate_with_pending_owner_change(migrator, user_wallet, user_wallet_config, hatchery, bob, alice):
    """Test that wallets with pending ownership changes cannot be migrated"""
    # Create new wallet
    new_wallet_addr = hatchery.createUserWallet(sender=bob)
    new_wallet = UserWallet.at(new_wallet_addr)
    new_wallet_config = UserWalletConfig.at(new_wallet.walletConfig())
    
    # Initiate ownership change on fromWallet
    user_wallet_config.changeOwnership(alice, sender=bob)
    assert not migrator.canMigrateFundsToNewWallet(user_wallet, new_wallet, bob)
    
    # Test migrateFunds fails with proper revert
    with boa.reverts("invalid migration"):
        migrator.migrateFunds(user_wallet, new_wallet, sender=bob)
    
    # Cancel ownership change on fromWallet
    user_wallet_config.cancelOwnershipChange(sender=bob)
    
    # Initiate ownership change on toWallet
    new_wallet_config.changeOwnership(alice, sender=bob)
    assert not migrator.canMigrateFundsToNewWallet(user_wallet, new_wallet, bob)
    
    # Test migrateFunds fails with proper revert
    with boa.reverts("invalid migration"):
        migrator.migrateFunds(user_wallet, new_wallet, sender=bob)


# Test group ID restriction
def test_cannot_migrate_different_group_ids(migrator, user_wallet, hatchery, bob):
    """Test that wallets must have the same group ID to migrate"""
    # Create new wallet with different group ID
    new_wallet = UserWallet.at(hatchery.createUserWallet(bob, ZERO_ADDRESS, False, 2, sender=bob))
    
    # Cannot migrate between different group IDs
    assert not migrator.canMigrateFundsToNewWallet(user_wallet, new_wallet, bob)


# Test payee restrictions
def test_cannot_migrate_with_payees(migrator, user_wallet, hatchery, bob, alice, paymaster, createPayeeSettings):
    """Test that toWallet cannot have payees (more than default)"""
    # Create new wallet
    new_wallet_addr = hatchery.createUserWallet(sender=bob)
    new_wallet = UserWallet.at(new_wallet_addr)
    new_wallet_config = UserWalletConfig.at(new_wallet.walletConfig())
    
    # Add a payee to the new wallet
    payee_settings = createPayeeSettings()
    new_wallet_config.addPayee(alice, payee_settings, sender=paymaster.address)
    
    # Cannot migrate to wallet with payees
    assert not migrator.canMigrateFundsToNewWallet(user_wallet, new_wallet, bob)


# Test whitelist restrictions
def test_cannot_migrate_with_whitelisted_addresses(migrator, user_wallet, hatchery, bob, alice):
    """Test that toWallet cannot have whitelisted addresses (more than default)"""
    # Create new wallet
    new_wallet_addr = hatchery.createUserWallet(sender=bob)
    new_wallet = UserWallet.at(new_wallet_addr)
    new_wallet_config = UserWalletConfig.at(new_wallet.walletConfig())
    
    # Add whitelisted address
    new_wallet_config.addWhitelistAddrViaMigrator(alice, sender=migrator.address)
    
    # Cannot migrate to wallet with whitelisted addresses
    assert not migrator.canMigrateFundsToNewWallet(user_wallet, new_wallet, bob)


# Test cheque restrictions
def test_cannot_migrate_with_active_cheques(migrator, hatchery, bob, alice, user_wallet, user_wallet_config, cheque_book, alpha_token, mock_ripe):
    """Test that toWallet cannot have active cheques"""
    ONE_WEEK_IN_BLOCKS = 7 * ONE_DAY_IN_BLOCKS

    # Get timeLock value
    timeLock = user_wallet_config.timeLock()

    # Travel past timelock to allow cheque settings change
    import boa
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

    # Cannot migrate from new wallet to user_wallet (which has active cheques)
    assert not migrator.canMigrateFundsToNewWallet(from_wallet, user_wallet, bob)


# Test manager restrictions - no starting agent
def test_cannot_migrate_with_managers_no_starting_agent(migrator, hatchery, bob, alice, high_command, createManagerSettings, mission_control, switchboard_alpha):
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
    
    # Cannot migrate to wallet with managers when no starting agent
    assert not migrator.canMigrateFundsToNewWallet(from_wallet, new_wallet, bob)


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
    
    # Should be able to migrate with just starting agent
    assert migrator.canMigrateFundsToNewWallet(user_wallet, new_wallet, bob)
    
    # Add another manager
    manager_settings = createManagerSettings()
    new_wallet_config.addManager(alice, manager_settings, sender=high_command.address)
    
    # Cannot migrate with additional managers beyond starting agent
    assert not migrator.canMigrateFundsToNewWallet(user_wallet, new_wallet, bob)


def test_starting_agent_at_correct_index(migrator, user_wallet, hatchery, bob, starter_agent):
    """Test that starting agent must be at index 1 for valid migration"""
    # Create new wallet with starting agent
    new_wallet_addr = hatchery.createUserWallet(sender=bob)
    new_wallet = UserWallet.at(new_wallet_addr)
    new_wallet_config = UserWalletConfig.at(new_wallet.walletConfig())
    
    # Verify starting agent is at index 1 (this is a contract invariant)
    assert new_wallet_config.startingAgent() == starter_agent.address
    assert new_wallet_config.indexOfManager(starter_agent.address) == 1
    
    # Should be valid for migration with starting agent at correct index
    assert migrator.canMigrateFundsToNewWallet(user_wallet, new_wallet, bob)


# Test edge cases
def test_can_migrate_empty_wallets(migrator, hatchery, bob):
    """Test that empty wallets can be migrated"""
    # Create two new empty wallets
    from_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    to_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    
    # Should be able to migrate empty wallets
    assert migrator.canMigrateFundsToNewWallet(from_wallet, to_wallet, bob)


def test_migration_bundle_data(migrator, user_wallet, user_wallet_config, bob):
    """Test getMigrationConfigBundle returns correct data"""
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


#################
# Migrate Funds #
#################


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


def test_migrate_funds_no_assets(migrator, hatchery, bob):
    """Test that migration fails when wallet has no assets to migrate"""
    # Create two wallets
    from_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    to_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    
    # Should fail because from_wallet has no assets (only ETH at index 0)
    with boa.reverts("no assets to migrate"):
        migrator.migrateFunds(from_wallet, to_wallet, sender=bob)


def test_migrate_funds_single_asset(migrator, user_wallet, hatchery, bob, alpha_token, prepareAssetForMigration):
    """Test successful migration of a single asset"""
    # Create target wallet
    to_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    
    # Prepare asset in source wallet
    amount = prepareAssetForMigration(user_wallet, alpha_token, 100 * EIGHTEEN_DECIMALS)
    
    # Verify initial state
    assert alpha_token.balanceOf(user_wallet) == amount
    assert alpha_token.balanceOf(to_wallet) == 0
    
    # Get initial USD value from wallet data
    asset_data = user_wallet.assetData(alpha_token)
    initial_usd_value = asset_data.usdValue
    
    # Migrate funds
    num_migrated = migrator.migrateFunds(user_wallet, to_wallet, sender=bob)
    
    # Verify migration results
    assert num_migrated == 1
    assert alpha_token.balanceOf(user_wallet) == 0
    assert alpha_token.balanceOf(to_wallet) == amount
    
    # Check event
    event = filter_logs(migrator, "FundsMigrated")[0]
    assert event.fromWallet == user_wallet.address
    assert event.toWallet == to_wallet.address
    assert event.numAssetsMigrated == 1
    assert event.totalUsdValue == initial_usd_value


def test_migrate_funds_multiple_assets(migrator, user_wallet, hatchery, bob, alpha_token, bravo_token, bravo_token_whale, prepareAssetForMigration):
    """Test migration of multiple assets"""
    # Create target wallet
    to_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    
    # Prepare multiple assets
    alpha_amount = prepareAssetForMigration(user_wallet, alpha_token, 100 * EIGHTEEN_DECIMALS, _price=2 * EIGHTEEN_DECIMALS)
    bravo_amount = prepareAssetForMigration(user_wallet, bravo_token, 50 * EIGHTEEN_DECIMALS, bravo_token_whale, 4 * EIGHTEEN_DECIMALS)
    
    # Calculate expected total USD value
    alpha_usd = 100 * 2 * EIGHTEEN_DECIMALS  # amount * price
    bravo_usd = 50 * 4 * EIGHTEEN_DECIMALS
    expected_total_usd = alpha_usd + bravo_usd
    
    # Migrate funds
    num_migrated = migrator.migrateFunds(user_wallet, to_wallet, sender=bob)
    
    # Verify migration results
    assert num_migrated == 2
    assert alpha_token.balanceOf(user_wallet) == 0
    assert bravo_token.balanceOf(user_wallet) == 0
    assert alpha_token.balanceOf(to_wallet) == alpha_amount
    assert bravo_token.balanceOf(to_wallet) == bravo_amount
    
    # Check event
    event = filter_logs(migrator, "FundsMigrated")[0]
    assert event.numAssetsMigrated == 2
    assert event.totalUsdValue == expected_total_usd


def test_migrate_funds_skip_zero_balance(migrator, user_wallet, hatchery, bob, alpha_token, bravo_token, charlie_token, bravo_token_whale, charlie_token_whale, prepareAssetForMigration):
    """Test that migration skips assets with zero balance"""
    # Create target wallet
    to_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    
    # Prepare assets with different scenarios
    alpha_amount = prepareAssetForMigration(user_wallet, alpha_token, 100 * EIGHTEEN_DECIMALS)

    # Register bravo but don't fund it (zero balance)
    prepareAssetForMigration(user_wallet, bravo_token, 0, bravo_token_whale)

    # Charlie token has 6 decimals
    charlie_amount = prepareAssetForMigration(user_wallet, charlie_token, 75 * 10**6, charlie_token_whale)
    
    # Verify initial state
    assert user_wallet.numAssets() == 3  # ETH + 2 tokens (bravo with 0 balance not counted in assets array)
    assert alpha_token.balanceOf(user_wallet) == alpha_amount
    assert bravo_token.balanceOf(user_wallet) == 0
    assert charlie_token.balanceOf(user_wallet) == charlie_amount
    
    # Migrate funds
    num_migrated = migrator.migrateFunds(user_wallet, to_wallet, sender=bob)
    
    # Should only migrate 2 assets (alpha and charlie, not bravo)
    assert num_migrated == 2
    assert alpha_token.balanceOf(to_wallet) == alpha_amount
    assert bravo_token.balanceOf(to_wallet) == 0
    assert charlie_token.balanceOf(to_wallet) == charlie_amount


def test_migrate_funds_preserves_usd_values(migrator, user_wallet, hatchery, bob, alpha_token, bravo_token, bravo_token_whale, prepareAssetForMigration):
    """Test that USD values from asset data are correctly tracked in event"""
    # Create target wallet
    to_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    
    # Prepare assets with specific prices
    prepareAssetForMigration(user_wallet, alpha_token, 50 * EIGHTEEN_DECIMALS, _price=3 * EIGHTEEN_DECIMALS)
    prepareAssetForMigration(user_wallet, bravo_token, 25 * EIGHTEEN_DECIMALS, bravo_token_whale, 8 * EIGHTEEN_DECIMALS)
    
    # Get USD values from wallet data
    alpha_data = user_wallet.assetData(alpha_token)
    bravo_data = user_wallet.assetData(bravo_token)
    expected_total_usd = alpha_data.usdValue + bravo_data.usdValue
    
    # Migrate funds
    migrator.migrateFunds(user_wallet, to_wallet, sender=bob)
    
    # Check event USD value matches sum of individual asset USD values
    event = filter_logs(migrator, "FundsMigrated")[0]
    assert event.totalUsdValue == expected_total_usd
    assert event.totalUsdValue == (50 * 3 + 25 * 8) * EIGHTEEN_DECIMALS


def test_migrate_funds_validation_revert(migrator, user_wallet, alice):
    """Test that migrateFunds reverts if validation fails"""
    # Try to migrate with invalid parameters (non-wallet address)
    with boa.reverts("invalid migration"):
        migrator.migrateFunds(user_wallet, alice, sender=alice)


def test_migrate_funds_caller_not_owner(migrator, user_wallet, hatchery, bob, alice, alpha_token, prepareAssetForMigration):
    """Test that non-owner cannot initiate migration"""
    # Create target wallet owned by bob
    to_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    
    # Prepare asset
    prepareAssetForMigration(user_wallet, alpha_token, 100 * EIGHTEEN_DECIMALS)
    
    # Alice (not owner) tries to migrate bob's wallet
    with boa.reverts("invalid migration"):
        migrator.migrateFunds(user_wallet, to_wallet, sender=alice)


def test_migrate_funds_deregisters_assets_from_source_wallet(migrator, user_wallet, hatchery, bob, alpha_token, bravo_token, bravo_token_whale, prepareAssetForMigration):
    """Test that assets are deregistered from source wallet after migration"""
    # Create target wallet
    to_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    
    # Prepare multiple assets in source wallet
    alpha_amount = prepareAssetForMigration(user_wallet, alpha_token, 100 * EIGHTEEN_DECIMALS)
    bravo_amount = prepareAssetForMigration(user_wallet, bravo_token, 50 * EIGHTEEN_DECIMALS, bravo_token_whale)
    
    # Verify initial state - assets are registered in source wallet
    initial_num_assets = user_wallet.numAssets()
    assert initial_num_assets == 3
    assert user_wallet.indexOfAsset(alpha_token) == 1
    assert user_wallet.indexOfAsset(bravo_token) == 2
    
    # Migrate funds
    num_migrated = migrator.migrateFunds(user_wallet, to_wallet, sender=bob)
    assert num_migrated == 2
    
    # Verify funds were transferred
    assert alpha_token.balanceOf(user_wallet) == 0
    assert bravo_token.balanceOf(user_wallet) == 0
    assert alpha_token.balanceOf(to_wallet) == alpha_amount
    assert bravo_token.balanceOf(to_wallet) == bravo_amount
    
    # With the updated _deregisterAsset that only checks ERC20 balance,
    # assets should be successfully deregistered since their balances are 0
    final_num_assets = user_wallet.numAssets()
    assert final_num_assets == 1  # Only ETH remains
    assert user_wallet.indexOfAsset(alpha_token) == 0  # Asset is deregistered (index 0 means not found)
    assert user_wallet.indexOfAsset(bravo_token) == 0  # Asset is deregistered (index 0 means not found)
    
    # Verify asset array only contains ETH
    assert user_wallet.assets(0) == ZERO_ADDRESS  # ETH placeholder


def test_migrate_funds_with_trial_funds_all_spent(migrator, hatchery, bob, alpha_token, alpha_token_whale, setUserWalletConfig, bravo_token, bravo_token_whale, switchboard_alpha):
    """Test migration fails when all trial funds have been spent"""
    # Configure trial funds
    trial_amount = 10 * EIGHTEEN_DECIMALS
    setUserWalletConfig(
        _trialAsset=alpha_token.address,
        _trialAmount=trial_amount
    )
    
    # Fund hatchery
    alpha_token.transfer(hatchery, trial_amount * 10, sender=alpha_token_whale)
    
    # Create wallet with trial funds
    wallet_with_trial = UserWallet.at(hatchery.createUserWallet(sender=bob))
    wallet_config = UserWalletConfig.at(wallet_with_trial.walletConfig())
    
    # Spend all trial funds
    alpha_token.transfer(bob, trial_amount, sender=wallet_with_trial.address)
    
    # Add another asset to migrate
    bravo_amount = 50 * EIGHTEEN_DECIMALS
    bravo_token.transfer(wallet_with_trial, bravo_amount, sender=bravo_token_whale)
    wallet_config.updateAssetData(0, bravo_token, False, sender=switchboard_alpha.address)
    
    # Create target wallet
    new_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    
    # Migration should fail because all trial funds (100%) remain unrecovered
    # which exceeds acceptable dust threshold (1%)
    with boa.reverts("trial funds could not be removed"):
        migrator.migrateFunds(wallet_with_trial, new_wallet, sender=bob)


def test_migrate_funds_with_trial_funds_partial_spent(migrator, hatchery, bob, alpha_token, alpha_token_whale, setUserWalletConfig, bravo_token, bravo_token_whale, switchboard_alpha):
    """Test migration fails when too many trial funds have been spent"""
    # Configure trial funds
    trial_amount = 10 * EIGHTEEN_DECIMALS
    setUserWalletConfig(
        _trialAsset=alpha_token.address,
        _trialAmount=trial_amount
    )
    
    # Fund hatchery
    alpha_token.transfer(hatchery, trial_amount * 10, sender=alpha_token_whale)
    
    # Create wallet with trial funds
    wallet_with_trial = UserWallet.at(hatchery.createUserWallet(sender=bob))
    wallet_config = UserWalletConfig.at(wallet_with_trial.walletConfig())
    
    # Spend part of trial funds (3 units), leaving 7 units
    alpha_token.transfer(bob, 3 * EIGHTEEN_DECIMALS, sender=wallet_with_trial.address)
    
    # Add another asset to migrate
    bravo_amount = 50 * EIGHTEEN_DECIMALS
    bravo_token.transfer(wallet_with_trial, bravo_amount, sender=bravo_token_whale)
    wallet_config.updateAssetData(0, bravo_token, False, sender=switchboard_alpha.address)
    
    # Create target wallet
    new_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    
    # Migration should fail because after clawback, 3 units (30%) remain unrecovered
    # which exceeds acceptable dust threshold (1%)
    with boa.reverts("trial funds could not be removed"):
        migrator.migrateFunds(wallet_with_trial, new_wallet, sender=bob)


def test_migrate_funds_with_trial_funds_partial_spent_within_dust(migrator, hatchery, bob, alpha_token, alpha_token_whale, setUserWalletConfig, bravo_token, bravo_token_whale, switchboard_alpha):
    """Test successful migration when only a small amount of trial funds were spent"""
    # Configure trial funds
    trial_amount = 10 * EIGHTEEN_DECIMALS
    setUserWalletConfig(
        _trialAsset=alpha_token.address,
        _trialAmount=trial_amount
    )
    
    # Fund hatchery
    alpha_token.transfer(hatchery, trial_amount * 10, sender=alpha_token_whale)
    
    # Create wallet with trial funds
    wallet_with_trial = UserWallet.at(hatchery.createUserWallet(sender=bob))
    wallet_config = UserWalletConfig.at(wallet_with_trial.walletConfig())
    
    # Spend only 0.08 units, leaving 9.92 units available for clawback
    # After clawback, only 0.08 units (0.8%) will remain unrecovered - within 1% threshold
    alpha_token.transfer(bob, 8 * 10**16, sender=wallet_with_trial.address)
    
    # Add another asset to migrate
    bravo_amount = 50 * EIGHTEEN_DECIMALS
    bravo_token.transfer(wallet_with_trial, bravo_amount, sender=bravo_token_whale)
    wallet_config.updateAssetData(0, bravo_token, False, sender=switchboard_alpha.address)
    
    # Create target wallet
    new_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    
    # Record hatchery balance before migration
    hatchery_balance_before = alpha_token.balanceOf(hatchery.address)
    
    # Migrate funds - should succeed because only 0.8% remains unrecovered after clawback
    num_migrated = migrator.migrateFunds(wallet_with_trial, new_wallet, sender=bob)
    
    # Verify most trial funds were clawed back (9.92 units)
    assert alpha_token.balanceOf(hatchery.address) == hatchery_balance_before + trial_amount - 8 * 10**16
    
    # Verify trial funds config shows small remaining unrecovered amount (0.08 units = 0.8%)
    assert wallet_config.trialFundsAsset() == alpha_token.address
    assert wallet_config.trialFundsAmount() == 8 * 10**16
    
    # Verify other assets were migrated
    assert num_migrated == 1  # Only bravo token
    assert bravo_token.balanceOf(wallet_with_trial) == 0
    assert bravo_token.balanceOf(new_wallet) == bravo_amount


def test_migrate_funds_with_trial_funds_in_vault(migrator, hatchery, bob, alice, alpha_token, alpha_token_whale, setUserWalletConfig, alpha_token_vault, bravo_token, bravo_token_whale, switchboard_alpha):
    """Test migration when trial funds are in yield vault"""
    # Configure trial funds
    trial_amount = 10 * EIGHTEEN_DECIMALS
    setUserWalletConfig(
        _trialAsset=alpha_token.address,
        _trialAmount=trial_amount
    )
    
    # Fund hatchery
    alpha_token.transfer(hatchery, trial_amount * 10, sender=alpha_token_whale)
    
    # Create wallet with trial funds
    wallet_with_trial = UserWallet.at(hatchery.createUserWallet(sender=bob))
    wallet_config = UserWalletConfig.at(wallet_with_trial.walletConfig())
    
    # Deposit all trial funds into vault
    wallet_with_trial.depositForYield(
        2,  # legoId for mock_yield_lego
        alpha_token.address,
        alpha_token_vault.address,
        sender=bob,
    )
    
    # Add another asset to migrate
    bravo_amount = 50 * EIGHTEEN_DECIMALS
    bravo_token.transfer(wallet_with_trial, bravo_amount, sender=bravo_token_whale)
    wallet_config.updateAssetData(0, bravo_token, False, sender=switchboard_alpha.address)
    
    # Create target wallet
    new_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    
    # Record hatchery balance before migration
    hatchery_balance_before = alpha_token.balanceOf(hatchery.address)
    
    # Migrate funds - should claw back trial funds from vault
    num_migrated = migrator.migrateFunds(wallet_with_trial, new_wallet, sender=bob)
    
    # Verify trial funds were clawed back from vault
    assert alpha_token.balanceOf(hatchery.address) == hatchery_balance_before + trial_amount
    assert alpha_token_vault.balanceOf(wallet_with_trial) == 0
    
    # Verify trial funds config was cleared
    assert wallet_config.trialFundsAsset() == ZERO_ADDRESS
    assert wallet_config.trialFundsAmount() == 0
    
    # Verify other assets were migrated
    assert num_migrated == 1  # Only bravo token
    assert bravo_token.balanceOf(wallet_with_trial) == 0
    assert bravo_token.balanceOf(new_wallet) == bravo_amount


def test_migrate_funds_with_acceptable_dust(migrator, hatchery, bob, alpha_token, alpha_token_whale, setUserWalletConfig, bravo_token, bravo_token_whale, switchboard_alpha):
    """Test migration succeeds when nearly all trial funds can be recovered"""
    # Configure trial funds
    trial_amount = 10 * EIGHTEEN_DECIMALS
    setUserWalletConfig(
        _trialAsset=alpha_token.address,
        _trialAmount=trial_amount
    )
    
    # Fund hatchery
    alpha_token.transfer(hatchery, trial_amount * 10, sender=alpha_token_whale)
    
    # Create wallet with trial funds
    wallet_with_trial = UserWallet.at(hatchery.createUserWallet(sender=bob))
    wallet_config = UserWalletConfig.at(wallet_with_trial.walletConfig())
    
    # Spend a tiny amount, leaving 9.95 units (99.5% recoverable)
    # After clawback, only 0.05 units (0.5%) will remain unrecovered - within 1% threshold
    alpha_token.transfer(bob, 5 * 10**16, sender=wallet_with_trial.address)  # Spend 0.05 units
    
    # Add another asset to migrate
    bravo_amount = 50 * EIGHTEEN_DECIMALS
    bravo_token.transfer(wallet_with_trial, bravo_amount, sender=bravo_token_whale)
    wallet_config.updateAssetData(0, bravo_token, False, sender=switchboard_alpha.address)
    
    # Create target wallet
    new_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    
    # Record hatchery balance before migration
    hatchery_balance_before = alpha_token.balanceOf(hatchery.address)
    
    # Migrate funds - should succeed because after clawback only 0.5% remains unrecovered
    num_migrated = migrator.migrateFunds(wallet_with_trial, new_wallet, sender=bob)
    
    # Verify most trial funds were clawed back (9.95 units)
    assert alpha_token.balanceOf(hatchery.address) == hatchery_balance_before + trial_amount - 5 * 10**16
    
    # Verify trial funds config shows small remaining unrecovered amount (0.05 units = 0.5%)
    assert wallet_config.trialFundsAsset() == alpha_token.address
    assert wallet_config.trialFundsAmount() == 5 * 10**16  # 0.05 units unrecovered
    
    # Verify other assets were migrated
    assert num_migrated == 1  # Only bravo token
    assert bravo_token.balanceOf(wallet_with_trial) == 0
    assert bravo_token.balanceOf(new_wallet) == bravo_amount


def test_migrate_funds_fails_with_too_much_trial_funds_remaining(migrator, hatchery, bob, alpha_token, alpha_token_whale, setUserWalletConfig, bravo_token, bravo_token_whale, switchboard_alpha):
    """Test migration fails when too much trial funds remain after clawback attempt"""
    # Configure trial funds
    trial_amount = 10 * EIGHTEEN_DECIMALS
    setUserWalletConfig(
        _trialAsset=alpha_token.address,
        _trialAmount=trial_amount
    )
    
    # Fund hatchery
    alpha_token.transfer(hatchery, trial_amount * 10, sender=alpha_token_whale)
    
    # Create wallet with trial funds
    wallet_with_trial = UserWallet.at(hatchery.createUserWallet(sender=bob))
    wallet_config = UserWalletConfig.at(wallet_with_trial.walletConfig())
    
    # Spend some trial funds, leaving 8.5 units (after clawback, 1.5 units unrecovered = 15% > 1% threshold)
    alpha_token.transfer(bob, 15 * 10**17, sender=wallet_with_trial.address)  # Spend 1.5 units
    
    # Add another asset to ensure we pass the "no assets to migrate" check
    bravo_amount = 50 * EIGHTEEN_DECIMALS
    bravo_token.transfer(wallet_with_trial, bravo_amount, sender=bravo_token_whale)
    wallet_config.updateAssetData(0, bravo_token, False, sender=switchboard_alpha.address)
    
    # Create target wallet
    new_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    
    # Migration should fail because after clawback 1.5 units (15%) remain unrecovered
    with boa.reverts("trial funds could not be removed"):
        migrator.migrateFunds(wallet_with_trial, new_wallet, sender=bob)


def test_migrate_funds_no_trial_funds_configured(migrator, hatchery, bob, alpha_token, alpha_token_whale, setUserWalletConfig, switchboard_alpha):
    """Test migration works normally when no trial funds are configured"""
    # Configure with no trial funds
    setUserWalletConfig(
        _trialAsset=ZERO_ADDRESS,
        _trialAmount=0
    )
    
    # Create wallet without trial funds
    wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    wallet_config = UserWalletConfig.at(wallet.walletConfig())
    
    # Add asset to migrate
    amount = 100 * EIGHTEEN_DECIMALS
    alpha_token.transfer(wallet, amount, sender=alpha_token_whale)
    wallet_config.updateAssetData(0, alpha_token, False, sender=switchboard_alpha.address)
    
    # Create target wallet
    new_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    
    # Record hatchery balance before migration
    hatchery_balance_before = alpha_token.balanceOf(hatchery.address)
    
    # Migrate funds - no trial funds to handle
    num_migrated = migrator.migrateFunds(wallet, new_wallet, sender=bob)
    
    # Verify no funds went to hatchery
    assert alpha_token.balanceOf(hatchery.address) == hatchery_balance_before
    
    # Verify normal migration occurred
    assert num_migrated == 1
    assert alpha_token.balanceOf(wallet) == 0
    assert alpha_token.balanceOf(new_wallet) == amount


def test_migrate_funds_trial_funds_already_cleared(migrator, hatchery, bob, charlie_token, charlie_token_whale, setUserWalletConfig, switchboard_alpha, bravo_token, bravo_token_whale, alpha_token, alpha_token_whale):
    """Test migration when trial funds were already clawed back previously"""
    # Configure trial funds with alpha token
    trial_amount = 10 * EIGHTEEN_DECIMALS
    setUserWalletConfig(
        _trialAsset=alpha_token.address,
        _trialAmount=trial_amount
    )
    
    # Fund hatchery
    alpha_token.transfer(hatchery, trial_amount * 10, sender=alpha_token_whale)
    
    # Create wallet with trial funds
    wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    wallet_config = UserWalletConfig.at(wallet.walletConfig())
    
    # Manually claw back trial funds first
    hatchery.clawBackTrialFunds(wallet.address, sender=bob)
    
    # Verify trial funds were cleared
    assert wallet_config.trialFundsAsset() == ZERO_ADDRESS
    assert wallet_config.trialFundsAmount() == 0
    
    # Add different assets to migrate (not the trial funds asset)
    charlie_amount = 50 * 10**6  # Charlie has 6 decimals
    bravo_amount = 30 * EIGHTEEN_DECIMALS
    charlie_token.transfer(wallet, charlie_amount, sender=charlie_token_whale)
    bravo_token.transfer(wallet, bravo_amount, sender=bravo_token_whale)
    wallet_config.updateAssetData(0, charlie_token, False, sender=switchboard_alpha.address)
    wallet_config.updateAssetData(0, bravo_token, False, sender=switchboard_alpha.address)
    
    # Create target wallet
    new_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    
    # Migrate funds - should work normally since trial funds already cleared
    num_migrated = migrator.migrateFunds(wallet, new_wallet, sender=bob)
    
    # Verify migration succeeded
    assert num_migrated == 2
    assert charlie_token.balanceOf(wallet) == 0
    assert bravo_token.balanceOf(wallet) == 0
    assert charlie_token.balanceOf(new_wallet) == charlie_amount
    assert bravo_token.balanceOf(new_wallet) == bravo_amount
    