"""
Test fund migration functionality in Migrator
"""
import pytest
import boa

from contracts.core import Migrator
from contracts.core.userWallet import UserWallet, UserWalletConfig
from constants import EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ONE_YEAR_IN_BLOCKS, ZERO_ADDRESS
from conf_utils import filter_logs


@pytest.fixture(scope="module")
def setup_wallets(setUserWalletConfig, setManagerConfig, setPayeeConfig, hatchery, bob, alice):
    """Setup user wallets for migration testing"""
    # Configure without starting agent for clean wallets
    setManagerConfig(_startingAgent=ZERO_ADDRESS)
    setUserWalletConfig()
    setPayeeConfig()
    
    # Create source wallet
    source_wallet_addr = hatchery.createUserWallet(
        bob,  # owner
        ZERO_ADDRESS,  # ambassador
        False,  # shouldUseTrialFunds
        1,  # groupId
        sender=bob
    )
    
    # Create destination wallet
    dest_wallet_addr = hatchery.createUserWallet(
        bob,  # same owner
        ZERO_ADDRESS,  # ambassador
        False,  # shouldUseTrialFunds
        1,  # groupId
        sender=bob
    )
    
    # Create another destination wallet for testing multiple migrations
    dest_wallet2_addr = hatchery.createUserWallet(
        bob,  # same owner
        ZERO_ADDRESS,  # ambassador
        False,  # shouldUseTrialFunds
        1,  # groupId
        sender=bob
    )
    
    # Create wallet with different owner for negative tests
    alice_wallet_addr = hatchery.createUserWallet(
        alice,  # different owner
        ZERO_ADDRESS,  # ambassador
        False,  # shouldUseTrialFunds
        1,  # groupId
        sender=alice
    )
    
    assert all(addr != ZERO_ADDRESS for addr in [source_wallet_addr, dest_wallet_addr, dest_wallet2_addr, alice_wallet_addr])
    
    return {
        'source_wallet': UserWallet.at(source_wallet_addr),
        'dest_wallet': UserWallet.at(dest_wallet_addr),
        'dest_wallet2': UserWallet.at(dest_wallet2_addr),
        'alice_wallet': UserWallet.at(alice_wallet_addr)
    }


@pytest.fixture(scope="module")
def setup_contracts(setup_wallets, migrator, alpha_token, bravo_token, charlie_token, governance, bob, alice):
    """Setup contracts and fund wallets"""
    wallets = setup_wallets
    source_wallet = wallets['source_wallet']
    dest_wallet = wallets['dest_wallet']
    
    # Get wallet configs
    source_config = UserWalletConfig.at(source_wallet.walletConfig())
    dest_config = UserWalletConfig.at(dest_wallet.walletConfig())
    
    return {
        'source_wallet': source_wallet,
        'dest_wallet': dest_wallet,
        'dest_wallet2': wallets['dest_wallet2'],
        'alice_wallet': wallets['alice_wallet'],
        'source_config': source_config,
        'dest_config': dest_config,
        'migrator': migrator,
        'alpha_token': alpha_token,
        'bravo_token': bravo_token,
        'charlie_token': charlie_token,
        'governance': governance,
        'bob': bob,
        'alice': alice
    }


# Basic fund migration tests


def test_migrate_funds_single_asset(setup_contracts, backpack):
    """Test migrating a single asset between wallets"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    source_wallet = ctx['source_wallet']
    dest_wallet = ctx['dest_wallet']
    source_config = ctx['source_config']
    bob = ctx['bob']
    alpha_token = ctx['alpha_token']
    governance = ctx['governance']
    
    # Transfer tokens to source wallet
    alpha_token.transfer(source_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Register asset in source wallet
    source_config.updateAssetData(
        0,  # legoId
        alpha_token.address,
        False,  # shouldCheckYield
        sender=backpack.address
    )
    
    # Verify initial state
    assert alpha_token.balanceOf(source_wallet.address) == 1000 * EIGHTEEN_DECIMALS
    assert alpha_token.balanceOf(dest_wallet.address) == 0
    assert source_wallet.numAssets() >= 1
    
    # Migrate funds
    num_migrated = migrator.migrateFunds(source_wallet.address, dest_wallet.address, sender=bob)
    assert num_migrated == 1
    
    # Check event
    events = filter_logs(migrator, "FundsMigrated")
    assert len(events) == 1
    event = events[0]
    assert event.fromWallet == source_wallet.address
    assert event.toWallet == dest_wallet.address
    assert event.numAssetsMigrated == 1
    
    # Verify final state
    assert alpha_token.balanceOf(source_wallet.address) == 0
    assert alpha_token.balanceOf(dest_wallet.address) == 1000 * EIGHTEEN_DECIMALS
    
    # Verify migration flag
    bundle = source_config.getMigrationConfigBundle()
    assert bundle.didMigrateFunds


def test_migrate_funds_multiple_assets(setup_contracts, backpack):
    """Test migrating multiple assets"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    source_wallet = ctx['source_wallet']
    dest_wallet2 = ctx['dest_wallet2']  # Use different dest to avoid conflict
    bob = ctx['bob']
    alpha_token = ctx['alpha_token']
    bravo_token = ctx['bravo_token']
    charlie_token = ctx['charlie_token']
    governance = ctx['governance']
    
    # Transfer multiple tokens to source wallet
    alpha_token.transfer(source_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    bravo_token.transfer(source_wallet.address, 2000 * EIGHTEEN_DECIMALS, sender=governance.address)
    charlie_token.transfer(source_wallet.address, 3000 * 10**6, sender=governance.address)  # Charlie has 6 decimals
    
    # Register all assets
    source_config = UserWalletConfig.at(source_wallet.walletConfig())
    for token in [alpha_token, bravo_token, charlie_token]:
        source_config.updateAssetData(0, token.address, False, sender=backpack.address)
    
    # Verify initial state
    assert source_wallet.numAssets() >= 3
    
    # Migrate all funds
    num_migrated = migrator.migrateFunds(source_wallet.address, dest_wallet2.address, sender=bob)
    assert num_migrated == 3
    
    # Verify all balances transferred
    assert alpha_token.balanceOf(source_wallet.address) == 0
    assert bravo_token.balanceOf(source_wallet.address) == 0
    assert charlie_token.balanceOf(source_wallet.address) == 0
    
    assert alpha_token.balanceOf(dest_wallet2.address) == 1000 * EIGHTEEN_DECIMALS
    assert bravo_token.balanceOf(dest_wallet2.address) == 2000 * EIGHTEEN_DECIMALS
    assert charlie_token.balanceOf(dest_wallet2.address) == 3000 * 10**6  # Charlie has 6 decimals


def test_migrate_funds_with_zero_balance_assets(setup_contracts, hatchery, backpack):
    """Test migration skips assets with zero balance"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    # Create fresh wallets for this test
    # Use hatchery from fixture
    source_addr = hatchery.createUserWallet(ctx['bob'], ZERO_ADDRESS, False, 1, sender=ctx['bob'])
    dest_addr = hatchery.createUserWallet(ctx['bob'], ZERO_ADDRESS, False, 1, sender=ctx['bob'])
    source_wallet = UserWallet.at(source_addr)
    dest_wallet = UserWallet.at(dest_addr)
    
    bob = ctx['bob']
    alpha_token = ctx['alpha_token']
    bravo_token = ctx['bravo_token']
    governance = ctx['governance']
    
    # Transfer only alpha token
    alpha_token.transfer(source_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Register both assets but only alpha has balance
    source_config = UserWalletConfig.at(source_wallet.walletConfig())
    source_config.updateAssetData(0, alpha_token.address, False, sender=backpack.address)
    source_config.updateAssetData(0, bravo_token.address, False, sender=backpack.address)
    
    # Migrate funds
    num_migrated = migrator.migrateFunds(source_wallet.address, dest_wallet.address, sender=bob)
    assert num_migrated == 1  # Only alpha token migrated
    
    # Verify only alpha was transferred
    assert alpha_token.balanceOf(dest_wallet.address) == 1000 * EIGHTEEN_DECIMALS
    assert bravo_token.balanceOf(dest_wallet.address) == 0


def test_migrate_funds_empty_wallet(setup_contracts, hatchery):
    """Test migrating from wallet with no assets"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    # Create fresh wallets for this test
    # Use hatchery from fixture
    source_addr = hatchery.createUserWallet(ctx['bob'], ZERO_ADDRESS, False, 1, sender=ctx['bob'])
    dest_addr = hatchery.createUserWallet(ctx['bob'], ZERO_ADDRESS, False, 1, sender=ctx['bob'])
    source_wallet = UserWallet.at(source_addr)
    source_config = UserWalletConfig.at(source_wallet.walletConfig())
    
    bob = ctx['bob']
    
    # Don't register any assets - wallet should have numAssets = 0
    assert source_wallet.numAssets() == 0
    
    # Migration should succeed but migrate nothing
    num_migrated = migrator.migrateFunds(source_wallet.address, dest_addr, sender=bob)
    assert num_migrated == 0
    
    # Flag should still be set
    bundle = source_config.getMigrationConfigBundle()
    assert bundle.didMigrateFunds


# Validation tests


def test_cannot_migrate_funds_twice(setup_contracts, hatchery, backpack):
    """Test that funds cannot be migrated twice"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    bob = ctx['bob']
    alpha_token = ctx['alpha_token']
    governance = ctx['governance']
    
    # Create fresh wallets
    source_addr = hatchery.createUserWallet(bob, ZERO_ADDRESS, False, 1, sender=bob)
    dest1_addr = hatchery.createUserWallet(bob, ZERO_ADDRESS, False, 1, sender=bob)
    dest2_addr = hatchery.createUserWallet(bob, ZERO_ADDRESS, False, 1, sender=bob)
    
    source_wallet = UserWallet.at(source_addr)
    source_config = UserWalletConfig.at(source_wallet.walletConfig())
    
    # Setup source with funds
    alpha_token.transfer(source_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    source_config.updateAssetData(0, alpha_token.address, False, sender=backpack.address)
    
    # First migration should succeed
    num_migrated = migrator.migrateFunds(source_wallet.address, dest1_addr, sender=bob)
    assert num_migrated == 1
    
    # Verify flag is set
    bundle = source_config.getMigrationConfigBundle()
    assert bundle.didMigrateFunds
    
    # Second migration should fail
    with boa.reverts("cannot migrate to new wallet"):
        migrator.migrateFunds(source_wallet.address, dest2_addr, sender=bob)


def test_cannot_migrate_funds_different_owner(setup_contracts):
    """Test cannot migrate funds between wallets with different owners"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    source_wallet = ctx['source_wallet']
    alice_wallet = ctx['alice_wallet']
    bob = ctx['bob']
    
    # Bob cannot migrate to Alice's wallet
    with boa.reverts("cannot migrate to new wallet"):
        migrator.migrateFunds(source_wallet.address, alice_wallet.address, sender=bob)


def test_cannot_migrate_funds_non_owner(setup_contracts):
    """Test non-owner cannot migrate funds"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    source_wallet = ctx['source_wallet']
    dest_wallet = ctx['dest_wallet']
    alice = ctx['alice']  # Not the owner
    
    # Alice cannot migrate Bob's wallet
    with boa.reverts("cannot migrate to new wallet"):
        migrator.migrateFunds(source_wallet.address, dest_wallet.address, sender=alice)


def test_migrate_funds_with_trial_funds(setup_contracts, setUserWalletConfig, setManagerConfig, setPayeeConfig, hatchery):
    """Test cannot migrate wallet with trial funds"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    bob = ctx['bob']
    alpha_token = ctx['alpha_token']
    
    # Configure and create wallet with trial funds
    setManagerConfig()  # Use default starting agent
    setUserWalletConfig()
    setPayeeConfig()
    
    # Fund hatchery for trial funds
    alpha_token.transfer(hatchery.address, 1000 * EIGHTEEN_DECIMALS, sender=ctx['governance'].address)
    
    # Create wallet with trial funds
    trial_wallet_addr = hatchery.createUserWallet(
        bob,
        ZERO_ADDRESS,
        True,  # shouldUseTrialFunds = True
        1,
        sender=bob
    )
    
    # Create destination wallet
    dest_addr = hatchery.createUserWallet(bob, ZERO_ADDRESS, False, 1, sender=bob)
    
    # Should not be able to migrate
    with boa.reverts("cannot migrate to new wallet"):
        migrator.migrateFunds(trial_wallet_addr, dest_addr, sender=bob)


def test_migrate_funds_frozen_wallet(setup_contracts, backpack, hatchery):
    """Test cannot migrate from frozen wallet"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    bob = ctx['bob']
    
    # Create fresh wallets
    source_addr = hatchery.createUserWallet(bob, ZERO_ADDRESS, False, 1, sender=bob)
    dest_addr = hatchery.createUserWallet(bob, ZERO_ADDRESS, False, 1, sender=bob)
    
    source_wallet = UserWallet.at(source_addr)
    source_config = UserWalletConfig.at(source_wallet.walletConfig())
    
    # Freeze source wallet
    source_config.setFrozen(True, sender=backpack.address)
    
    # Should not be able to migrate
    with boa.reverts("cannot migrate to new wallet"):
        migrator.migrateFunds(source_addr, dest_addr, sender=bob)
    
    # Unfreeze
    source_config.setFrozen(False, sender=backpack.address)


# Edge cases


def test_migrate_funds_unregistered_assets(setup_contracts, hatchery, backpack):
    """Test that unregistered assets with balance are not migrated"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    bob = ctx['bob']
    alpha_token = ctx['alpha_token']
    bravo_token = ctx['bravo_token']
    governance = ctx['governance']
    
    # Create fresh wallets
    source_addr = hatchery.createUserWallet(bob, ZERO_ADDRESS, False, 1, sender=bob)
    dest_addr = hatchery.createUserWallet(bob, ZERO_ADDRESS, False, 1, sender=bob)
    
    source_wallet = UserWallet.at(source_addr)
    source_config = UserWalletConfig.at(source_wallet.walletConfig())
    
    # Transfer both tokens but only register alpha
    alpha_token.transfer(source_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    bravo_token.transfer(source_wallet.address, 500 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Only register alpha token
    source_config.updateAssetData(0, alpha_token.address, False, sender=backpack.address)
    
    # Migrate funds
    num_migrated = migrator.migrateFunds(source_addr, dest_addr, sender=bob)
    assert num_migrated == 1  # Only registered alpha token
    
    # Verify only registered asset was migrated
    assert alpha_token.balanceOf(dest_addr) == 1000 * EIGHTEEN_DECIMALS
    assert bravo_token.balanceOf(dest_addr) == 0
    assert bravo_token.balanceOf(source_addr) == 500 * EIGHTEEN_DECIMALS  # Still in source


def test_migrate_funds_max_amount_transfer(setup_contracts, hatchery, backpack):
    """Test that max_value(uint256) transfers entire balance"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    bob = ctx['bob']
    alpha_token = ctx['alpha_token']
    governance = ctx['governance']
    
    # Create fresh wallets
    source_addr = hatchery.createUserWallet(bob, ZERO_ADDRESS, False, 1, sender=bob)
    dest_addr = hatchery.createUserWallet(bob, ZERO_ADDRESS, False, 1, sender=bob)
    
    source_wallet = UserWallet.at(source_addr)
    source_config = UserWalletConfig.at(source_wallet.walletConfig())
    
    # Transfer odd amount to test max transfer
    transfer_amount = 1234567890123456789  # Not a round number
    alpha_token.transfer(source_wallet.address, transfer_amount, sender=governance.address)
    
    # Register asset
    source_config.updateAssetData(0, alpha_token.address, False, sender=backpack.address)
    
    # Migrate with max_value should transfer entire balance
    migrator.migrateFunds(source_addr, dest_addr, sender=bob)
    
    # Verify exact transfer - CRITICAL: no funds left behind
    assert alpha_token.balanceOf(source_addr) == 0
    assert alpha_token.balanceOf(dest_addr) == transfer_amount


def test_migrate_funds_complete_balance_transfer(setup_contracts, hatchery, backpack):
    """CRITICAL: Test that migration transfers exactly 100% of balance with no funds left behind"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    bob = ctx['bob']
    alpha_token = ctx['alpha_token']
    governance = ctx['governance']
    
    # Create fresh wallets
    source_addr = hatchery.createUserWallet(bob, ZERO_ADDRESS, False, 1, sender=bob)
    dest_addr = hatchery.createUserWallet(bob, ZERO_ADDRESS, False, 1, sender=bob)
    
    source_wallet = UserWallet.at(source_addr)
    source_config = UserWalletConfig.at(source_wallet.walletConfig())
    
    # Transfer a specific amount and verify exact balances
    exact_amount = 123456789012345678901234  # Specific large amount
    alpha_token.transfer(source_wallet.address, exact_amount, sender=governance.address)
    source_config.updateAssetData(0, alpha_token.address, False, sender=backpack.address)
    
    # Record pre-migration balances
    pre_source_balance = alpha_token.balanceOf(source_wallet.address)
    pre_dest_balance = alpha_token.balanceOf(dest_addr)
    
    # Migrate funds
    num_migrated = migrator.migrateFunds(source_wallet.address, dest_addr, sender=bob)
    assert num_migrated == 1
    
    # CRITICAL VERIFICATION: Exact balance transfer
    post_source_balance = alpha_token.balanceOf(source_wallet.address)
    post_dest_balance = alpha_token.balanceOf(dest_addr)
    
    # Source must be completely emptied
    assert post_source_balance == 0, f"Source still has {post_source_balance} tokens - migration incomplete"
    
    # Destination must receive exactly what source had
    transferred_amount = post_dest_balance - pre_dest_balance
    assert transferred_amount == pre_source_balance, f"Expected {pre_source_balance}, got {transferred_amount}"
    assert post_dest_balance == pre_dest_balance + exact_amount