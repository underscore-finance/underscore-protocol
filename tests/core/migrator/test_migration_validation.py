"""
Test migration validation functions in Migrator
"""
import pytest
import boa

from contracts.core import Migrator
from contracts.core.userWallet import UserWallet, UserWalletConfig
from constants import EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ONE_YEAR_IN_BLOCKS, ZERO_ADDRESS
from conf_utils import filter_logs


@pytest.fixture(scope="module")
def setup_wallets(setUserWalletConfig, setManagerConfig, setPayeeConfig, hatchery, bob, alice, charlie, sally, alpha_token, governance):
    """Setup multiple user wallets for testing migration"""
    # First set manager config without starting agent for clean wallets
    setManagerConfig(_startingAgent=ZERO_ADDRESS)
    setUserWalletConfig()
    setPayeeConfig()
    
    # Fund hatchery for trial funds
    alpha_token.transfer(hatchery.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Create wallets for different scenarios
    # 1. Clean wallets (no starting agent, no trial funds)
    wallet1_addr = hatchery.createUserWallet(
        bob,  # Owner
        ZERO_ADDRESS,  # Ambassador
        False,  # shouldUseTrialFunds = False
        1,  # groupId = 1
        sender=bob
    )
    wallet2_addr = hatchery.createUserWallet(
        bob,  # Same owner
        ZERO_ADDRESS,  # Ambassador
        False,  # shouldUseTrialFunds = False
        1,  # groupId = 1
        sender=bob
    )
    
    # 2. Create wallet for bob with different group ID
    wallet6_addr = hatchery.createUserWallet(
        bob,  # Same owner as wallet1/2
        ZERO_ADDRESS,  # Ambassador
        False,  # shouldUseTrialFunds = False
        2,  # groupId = 2 (different!)
        sender=bob
    )
    
    # Now set manager config with starting agent for wallets that need it
    setManagerConfig()  # This will use default starting agent
    
    # 3. Wallets with starting agents
    wallet3_addr = hatchery.createUserWallet(sender=alice)  # Different owner, has starting agent
    wallet4_addr = hatchery.createUserWallet(sender=charlie)  # Another different owner, has starting agent
    
    # 4. Create wallet for bob with starting agent (same owner as wallet1/2)
    wallet7_addr = hatchery.createUserWallet(
        bob,  # Same owner as wallet1/2
        ZERO_ADDRESS,  # Ambassador
        False,  # shouldUseTrialFunds = False
        1,  # groupId = 1
        sender=bob
    )
    
    # 5. Create wallet with trial funds for bob (for testing copy config)
    wallet8_addr = hatchery.createUserWallet(
        bob,  # Same owner as wallet1/2
        ZERO_ADDRESS,  # Ambassador
        True,  # shouldUseTrialFunds = True
        1,  # groupId = 1
        sender=bob
    )
    
    # 6. Original wallet with trial funds for sally
    wallet5_addr = hatchery.createUserWallet(
        sally,  # Owner
        ZERO_ADDRESS,  # Ambassador
        True,  # shouldUseTrialFunds
        1,  # groupId = 1
        sender=sally
    )
    
    assert all(addr != ZERO_ADDRESS for addr in [wallet1_addr, wallet2_addr, wallet3_addr, 
                                                  wallet4_addr, wallet5_addr, wallet6_addr, 
                                                  wallet7_addr, wallet8_addr])
    
    return {
        'wallet1': UserWallet.at(wallet1_addr),  # bob, no starting agent, group 1
        'wallet2': UserWallet.at(wallet2_addr),  # bob, no starting agent, group 1
        'wallet3': UserWallet.at(wallet3_addr),  # alice, has starting agent, group 1
        'wallet4': UserWallet.at(wallet4_addr),  # charlie, has starting agent, group 1
        'wallet5': UserWallet.at(wallet5_addr),  # sally, has trial funds and starting agent, group 1
        'wallet6': UserWallet.at(wallet6_addr),  # bob, no starting agent, group 2 (different!)
        'wallet7': UserWallet.at(wallet7_addr),  # bob, has starting agent, group 1
        'wallet8': UserWallet.at(wallet8_addr),  # bob, has trial funds and starting agent, group 1
        'bob': bob,
        'alice': alice,
        'charlie': charlie,
        'sally': sally
    }


@pytest.fixture(scope="module")
def setup_contracts(setup_wallets, migrator, paymaster, alpha_token, bravo_token, governance, switchboard_alpha, createPayeeLimits,
                   createManagerSettings, createTransferPerms, boss_validator):
    """Setup contracts and configurations"""
    wallets = setup_wallets
    
    # Fund wallets for testing (except wallet5 which has trial funds)
    for wallet_key in ['wallet1', 'wallet2', 'wallet3', 'wallet4']:
        wallet = wallets[wallet_key]
        alpha_token.transfer(wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
        bravo_token.transfer(wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Get wallet configs
    wallet1_config = UserWalletConfig.at(wallets['wallet1'].walletConfig())
    wallet2_config = UserWalletConfig.at(wallets['wallet2'].walletConfig())
    wallet3_config = UserWalletConfig.at(wallets['wallet3'].walletConfig())
    wallet4_config = UserWalletConfig.at(wallets['wallet4'].walletConfig())
    wallet5_config = UserWalletConfig.at(wallets['wallet5'].walletConfig())
    wallet6_config = UserWalletConfig.at(wallets['wallet6'].walletConfig())
    wallet7_config = UserWalletConfig.at(wallets['wallet7'].walletConfig())
    wallet8_config = UserWalletConfig.at(wallets['wallet8'].walletConfig())
    
    return {
        'wallet1': wallets['wallet1'],
        'wallet2': wallets['wallet2'],
        'wallet3': wallets['wallet3'],
        'wallet4': wallets['wallet4'],
        'wallet5': wallets['wallet5'],
        'wallet6': wallets['wallet6'],  # bob, different group
        'wallet7': wallets['wallet7'],  # bob, with starting agent
        'wallet8': wallets['wallet8'],  # bob, with trial funds
        'wallet1_config': wallet1_config,
        'wallet2_config': wallet2_config,
        'wallet3_config': wallet3_config,
        'wallet4_config': wallet4_config,
        'wallet5_config': wallet5_config,
        'wallet6_config': wallet6_config,
        'wallet7_config': wallet7_config,
        'wallet8_config': wallet8_config,
        'migrator': migrator,
        'paymaster': paymaster,
        'alpha_token': alpha_token,
        'bravo_token': bravo_token,
        'bob': wallets['bob'],
        'alice': wallets['alice'],
        'charlie': wallets['charlie'],
        'sally': wallets['sally'],
        'governance': governance,
        'switchboard_alpha': switchboard_alpha,
        'createPayeeLimits': createPayeeLimits,
        'createManagerSettings': createManagerSettings,
        'createTransferPerms': createTransferPerms,
        'boss_validator': boss_validator
    }


# Test canMigrateToNewWallet


def test_can_migrate_basic_valid_case(setup_contracts):
    """Test basic valid migration scenario"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    wallet1 = ctx['wallet1']  # No starting agent, no trial funds
    wallet2 = ctx['wallet2']  # No starting agent, no trial funds
    bob = ctx['bob']
    
    can_migrate = migrator.canMigrateFundsToNewWallet(wallet1.address, wallet2.address, bob)
    assert can_migrate


def test_cannot_migrate_to_non_underscore_wallet(setup_contracts):
    """Test cannot migrate to non-Underscore wallet"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    wallet1 = ctx['wallet1']
    bob = ctx['bob']
    random_addr = boa.env.generate_address()
    
    can_migrate = migrator.canMigrateFundsToNewWallet(wallet1.address, random_addr, bob)
    assert not can_migrate


def test_cannot_migrate_with_trial_funds(setup_contracts):
    """Test cannot migrate wallet with trial funds"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    wallet5 = ctx['wallet5']  # Has trial funds
    wallet1 = ctx['wallet1']
    sally = ctx['sally']
    
    can_migrate = migrator.canMigrateFundsToNewWallet(wallet5.address, wallet1.address, sally)
    assert not can_migrate


def test_cannot_migrate_frozen_wallet(setup_contracts, switchboard_alpha):
    """Test cannot migrate from frozen wallet"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    wallet1_config = ctx['wallet1_config']
    bob = ctx['bob']
    
    # Freeze wallet1
    wallet1_config.setFrozen(True, sender=switchboard_alpha.address)
    
    can_migrate = migrator.canMigrateFundsToNewWallet(wallet1.address, wallet2.address, bob)
    assert not can_migrate
    
    # Unfreeze for other tests
    wallet1_config.setFrozen(False, sender=switchboard_alpha.address)


def test_cannot_migrate_with_pending_owner_change(setup_contracts):
    """Test cannot migrate from wallet with pending owner change"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    wallet1_config = ctx['wallet1_config']
    bob = ctx['bob']
    
    # Initiate owner change
    new_owner = boa.env.generate_address()
    wallet1_config.changeOwnership(new_owner, sender=bob)
    
    can_migrate = migrator.canMigrateFundsToNewWallet(wallet1.address, wallet2.address, bob)
    assert not can_migrate
    
    # Cancel for other tests
    wallet1_config.cancelOwnershipChange(sender=bob)


def test_cannot_migrate_different_owners(setup_contracts):
    """Test cannot migrate between wallets with different owners"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    wallet1 = ctx['wallet1']  # Bob's wallet
    wallet3 = ctx['wallet3']  # Alice's wallet
    bob = ctx['bob']
    
    can_migrate = migrator.canMigrateFundsToNewWallet(wallet1.address, wallet3.address, bob)
    assert not can_migrate


def test_cannot_migrate_to_wallet_with_pending_owner_change(setup_contracts):
    """Test cannot migrate to wallet with pending owner change"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    wallet2_config = ctx['wallet2_config']
    bob = ctx['bob']
    
    # Initiate owner change on destination
    new_owner = boa.env.generate_address()
    wallet2_config.changeOwnership(new_owner, sender=bob)
    
    can_migrate = migrator.canMigrateFundsToNewWallet(wallet1.address, wallet2.address, bob)
    assert not can_migrate
    
    # Cancel for other tests
    wallet2_config.cancelOwnershipChange(sender=bob)


def test_cannot_migrate_different_group_ids(setup_contracts):
    """Test cannot migrate between wallets with different group IDs"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    wallet1 = ctx['wallet1']  # Group 1
    wallet6 = ctx['wallet6']  # Group 2
    bob = ctx['bob']
    
    can_migrate = migrator.canMigrateFundsToNewWallet(wallet1.address, wallet6.address, bob)
    assert not can_migrate


def test_cannot_migrate_to_frozen_wallet(setup_contracts, switchboard_alpha):
    """Test cannot migrate to frozen wallet"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    wallet2_config = ctx['wallet2_config']
    bob = ctx['bob']
    
    # Freeze destination wallet
    wallet2_config.setFrozen(True, sender=switchboard_alpha.address)
    
    can_migrate = migrator.canMigrateFundsToNewWallet(wallet1.address, wallet2.address, bob)
    assert not can_migrate
    
    # Unfreeze for other tests
    wallet2_config.setFrozen(False, sender=switchboard_alpha.address)


def test_cannot_migrate_to_wallet_with_payees(setup_contracts):
    """Test cannot migrate to wallet that has payees"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    bob = ctx['bob']
    alpha_token = ctx['alpha_token']
    createPayeeLimits = ctx['createPayeeLimits']
    
    # Add payee to destination wallet
    payee = boa.env.generate_address()
    unit_limits = createPayeeLimits()
    usd_limits = createPayeeLimits()
    
    paymaster.addPayee(
        wallet2.address,
        payee,
        False,
        ONE_DAY_IN_BLOCKS,
        10,
        0,
        False,
        alpha_token.address,
        False,
        unit_limits,
        usd_limits,
        sender=bob
    )
    
    can_migrate = migrator.canMigrateFundsToNewWallet(wallet1.address, wallet2.address, bob)
    assert not can_migrate
    
    # Clean up
    paymaster.removePayee(wallet2.address, payee, sender=bob)


def test_cannot_migrate_to_wallet_with_whitelisted(setup_contracts):
    """Test cannot migrate to wallet that has whitelisted addresses"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    wallet2_config = ctx['wallet2_config']
    bob = ctx['bob']
    
    # Add whitelisted address to destination
    addr = boa.env.generate_address()
    paymaster.addWhitelistAddr(wallet2.address, addr, sender=bob)
    boa.env.time_travel(blocks=wallet2_config.timeLock() + 1)
    paymaster.confirmWhitelistAddr(wallet2.address, addr, sender=bob)
    
    can_migrate = migrator.canMigrateFundsToNewWallet(wallet1.address, wallet2.address, bob)
    assert not can_migrate
    
    # Clean up
    paymaster.removeWhitelistAddr(wallet2.address, addr, sender=bob)


def test_cannot_migrate_to_wallet_with_managers_no_starting_agent(setup_contracts):
    """Test cannot migrate to wallet with managers but no starting agent"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    boss_validator = ctx['boss_validator']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    bob = ctx['bob']
    createManagerSettings = ctx['createManagerSettings']
    
    # Add manager to destination (which has no starting agent)
    manager = boa.env.generate_address()
    manager_settings = createManagerSettings()
    start_block, expiry_block, limits, lego_perms, whitelist_perms, transfer_perms, allowed_assets = manager_settings
    
    boss_validator.addManager(
        wallet2.address,
        manager,
        limits,
        lego_perms,
        whitelist_perms,
        transfer_perms,
        allowed_assets,
        sender=bob
    )
    
    can_migrate = migrator.canMigrateFundsToNewWallet(wallet1.address, wallet2.address, bob)
    assert not can_migrate
    
    # Clean up
    boss_validator.removeManager(wallet2.address, manager, sender=bob)


def test_can_migrate_with_starting_agent_only(setup_contracts):
    """Test can migrate to wallet with only starting agent"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    wallet1 = ctx['wallet1']  # No starting agent
    wallet7 = ctx['wallet7']  # Has starting agent
    bob = ctx['bob']
    
    can_migrate = migrator.canMigrateFundsToNewWallet(wallet1.address, wallet7.address, bob)
    assert can_migrate


def test_cannot_migrate_with_starting_agent_plus_other_managers(setup_contracts):
    """Test cannot migrate to wallet with starting agent plus other managers"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    boss_validator = ctx['boss_validator']
    wallet1 = ctx['wallet1']
    wallet7 = ctx['wallet7']  # Has starting agent
    bob = ctx['bob']
    createManagerSettings = ctx['createManagerSettings']
    
    # Add additional manager to wallet7 (which already has starting agent)
    manager = boa.env.generate_address()
    manager_settings = createManagerSettings()
    start_block, expiry_block, limits, lego_perms, whitelist_perms, transfer_perms, allowed_assets = manager_settings
    
    boss_validator.addManager(
        wallet7.address,
        manager,
        limits,
        lego_perms,
        whitelist_perms,
        transfer_perms,
        allowed_assets,
        sender=bob
    )
    
    can_migrate = migrator.canMigrateFundsToNewWallet(wallet1.address, wallet7.address, bob)
    assert not can_migrate
    
    # Clean up
    boss_validator.removeManager(wallet7.address, manager, sender=bob)


# Test canCopyWalletConfig


def test_can_copy_config_basic_valid_case(setup_contracts):
    """Test basic valid config copy scenario"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    bob = ctx['bob']
    
    can_copy = migrator.canCopyWalletConfig(wallet1.address, wallet2.address, bob)
    assert can_copy


def test_cannot_copy_from_non_underscore_wallet(setup_contracts):
    """Test cannot copy config from non-Underscore wallet"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    wallet2 = ctx['wallet2']
    bob = ctx['bob']
    random_addr = boa.env.generate_address()
    
    can_copy = migrator.canCopyWalletConfig(random_addr, wallet2.address, bob)
    assert not can_copy


def test_cannot_copy_to_non_underscore_wallet(setup_contracts):
    """Test cannot copy config to non-Underscore wallet"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    wallet1 = ctx['wallet1']
    bob = ctx['bob']
    random_addr = boa.env.generate_address()
    
    can_copy = migrator.canCopyWalletConfig(wallet1.address, random_addr, bob)
    assert not can_copy


def test_cannot_copy_to_wallet_with_pending_owner_change(setup_contracts):
    """Test cannot copy to wallet with pending owner change"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    wallet2_config = ctx['wallet2_config']
    bob = ctx['bob']
    
    # Initiate owner change on destination
    new_owner = boa.env.generate_address()
    wallet2_config.changeOwnership(new_owner, sender=bob)
    
    can_copy = migrator.canCopyWalletConfig(wallet1.address, wallet2.address, bob)
    assert not can_copy
    
    # Cancel for other tests
    wallet2_config.cancelOwnershipChange(sender=bob)


def test_cannot_copy_to_frozen_wallet(setup_contracts, switchboard_alpha):
    """Test cannot copy to frozen wallet"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    wallet2_config = ctx['wallet2_config']
    bob = ctx['bob']
    
    # Freeze destination
    wallet2_config.setFrozen(True, sender=switchboard_alpha.address)
    
    can_copy = migrator.canCopyWalletConfig(wallet1.address, wallet2.address, bob)
    assert not can_copy
    
    # Unfreeze
    wallet2_config.setFrozen(False, sender=switchboard_alpha.address)


def test_cannot_copy_to_wallet_with_payees(setup_contracts):
    """Test cannot copy to wallet that already has payees"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    bob = ctx['bob']
    alpha_token = ctx['alpha_token']
    createPayeeLimits = ctx['createPayeeLimits']
    
    # Add payee to destination
    payee = boa.env.generate_address()
    unit_limits = createPayeeLimits()
    usd_limits = createPayeeLimits()
    
    paymaster.addPayee(
        wallet2.address,
        payee,
        False,
        ONE_DAY_IN_BLOCKS,
        10,
        0,
        False,
        alpha_token.address,
        False,
        unit_limits,
        usd_limits,
        sender=bob
    )
    
    can_copy = migrator.canCopyWalletConfig(wallet1.address, wallet2.address, bob)
    assert not can_copy
    
    # Clean up
    paymaster.removePayee(wallet2.address, payee, sender=bob)


def test_cannot_copy_to_wallet_with_whitelisted(setup_contracts):
    """Test cannot copy to wallet with whitelisted addresses"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    wallet2_config = ctx['wallet2_config']
    bob = ctx['bob']
    
    # Add whitelisted address to destination
    addr = boa.env.generate_address()
    paymaster.addWhitelistAddr(wallet2.address, addr, sender=bob)
    boa.env.time_travel(blocks=wallet2_config.timeLock() + 1)
    paymaster.confirmWhitelistAddr(wallet2.address, addr, sender=bob)
    
    can_copy = migrator.canCopyWalletConfig(wallet1.address, wallet2.address, bob)
    assert not can_copy
    
    # Clean up
    paymaster.removeWhitelistAddr(wallet2.address, addr, sender=bob)


def test_cannot_copy_from_frozen_wallet(setup_contracts, switchboard_alpha):
    """Test cannot copy from frozen wallet"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    wallet1_config = ctx['wallet1_config']
    bob = ctx['bob']
    
    # Freeze source
    wallet1_config.setFrozen(True, sender=switchboard_alpha.address)
    
    can_copy = migrator.canCopyWalletConfig(wallet1.address, wallet2.address, bob)
    assert not can_copy
    
    # Unfreeze
    wallet1_config.setFrozen(False, sender=switchboard_alpha.address)


def test_cannot_copy_different_owners(setup_contracts):
    """Test cannot copy between wallets with different owners"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    wallet1 = ctx['wallet1']  # Bob's wallet
    wallet3 = ctx['wallet3']  # Alice's wallet
    bob = ctx['bob']
    
    can_copy = migrator.canCopyWalletConfig(wallet1.address, wallet3.address, bob)
    assert not can_copy


def test_cannot_copy_different_group_ids(setup_contracts):
    """Test cannot copy between wallets with different group IDs"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    wallet1 = ctx['wallet1']  # Group 1
    wallet6 = ctx['wallet6']  # Group 2
    bob = ctx['bob']
    
    can_copy = migrator.canCopyWalletConfig(wallet1.address, wallet6.address, bob)
    assert not can_copy


def test_cannot_copy_from_wallet_with_pending_owner_change(setup_contracts):
    """Test cannot copy from wallet with pending owner change"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    wallet1_config = ctx['wallet1_config']
    bob = ctx['bob']
    
    # Initiate owner change on source
    new_owner = boa.env.generate_address()
    wallet1_config.changeOwnership(new_owner, sender=bob)
    
    can_copy = migrator.canCopyWalletConfig(wallet1.address, wallet2.address, bob)
    assert not can_copy
    
    # Cancel
    wallet1_config.cancelOwnershipChange(sender=bob)


def test_can_copy_with_managers_and_starting_agent(setup_contracts):
    """Test can copy to wallet with only starting agent"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    wallet1 = ctx['wallet1']
    wallet7 = ctx['wallet7']  # Has starting agent
    bob = ctx['bob']
    
    can_copy = migrator.canCopyWalletConfig(wallet1.address, wallet7.address, bob)
    assert can_copy


def test_cannot_copy_after_already_migrated_settings(setup_contracts):
    """Test cannot copy config from wallet that already migrated settings"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    wallet1_config = ctx['wallet1_config']
    bob = ctx['bob']
    alpha_token = ctx['alpha_token']
    createPayeeLimits = ctx['createPayeeLimits']
    
    # Add some config to wallet1
    payee = boa.env.generate_address()
    unit_limits = createPayeeLimits()
    usd_limits = createPayeeLimits()
    
    paymaster.addPayee(
        wallet1.address,
        payee,
        False,
        ONE_DAY_IN_BLOCKS,
        10,
        0,
        False,
        alpha_token.address,
        False,
        unit_limits,
        usd_limits,
        sender=bob
    )
    
    # Perform migration
    migrator.cloneConfig(wallet1.address, wallet2.address, sender=bob)
    
    # Verify flag is set
    bundle = wallet1_config.getMigrationConfigBundle()
    assert bundle.didMigrateSettings
    
    # Try to copy again - should fail
    wallet7 = ctx['wallet7']
    can_copy = migrator.canCopyWalletConfig(wallet1.address, wallet7.address, bob)
    assert not can_copy
    
    # Clean up
    paymaster.removePayee(wallet1.address, payee, sender=bob)
    paymaster.removePayee(wallet2.address, payee, sender=bob)


def test_cannot_migrate_from_eoa_address(setup_contracts):
    """Test migration validation fails for EOA addresses"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    wallet2 = ctx['wallet2']
    bob = ctx['bob']
    eoa_address = boa.env.generate_address()
    
    can_migrate = migrator.canMigrateFundsToNewWallet(eoa_address, wallet2.address, bob)
    assert not can_migrate


def test_cannot_migrate_to_eoa_address(setup_contracts):
    """Test migration validation fails when destination is EOA"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    wallet1 = ctx['wallet1']
    bob = ctx['bob']
    eoa_address = boa.env.generate_address()
    
    can_migrate = migrator.canMigrateFundsToNewWallet(wallet1.address, eoa_address, bob)
    assert not can_migrate


def test_cannot_copy_config_with_non_contract_addresses(setup_contracts):
    """Test config copy validation fails for non-contract addresses"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    bob = ctx['bob']
    eoa_address1 = boa.env.generate_address()
    eoa_address2 = boa.env.generate_address()
    
    can_copy = migrator.canCopyWalletConfig(eoa_address1, eoa_address2, bob)
    assert not can_copy


def test_cannot_migrate_non_existent_caller(setup_contracts):
    """Test migration validation with non-existent caller"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    random_caller = boa.env.generate_address()
    
    # Random caller is not the owner
    can_migrate = migrator.canMigrateFundsToNewWallet(wallet1.address, wallet2.address, random_caller)
    assert not can_migrate
    
    can_copy = migrator.canCopyWalletConfig(wallet1.address, wallet2.address, random_caller)
    assert not can_copy


# Note: Fund migration implementation tests are in test_migrate_funds.py
# Config cloning implementation tests are in test_clone_config.py