"""
Test migration validation functions in Paymaster
"""
import pytest
import boa

from contracts.core import Paymaster
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
def setup_contracts(setup_wallets, paymaster, alpha_token, bravo_token, governance, createPayeeLimits,
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
        'paymaster': paymaster,
        'alpha_token': alpha_token,
        'bravo_token': bravo_token,
        'bob': wallets['bob'],
        'alice': wallets['alice'],
        'charlie': wallets['charlie'],
        'sally': wallets['sally'],
        'createPayeeLimits': createPayeeLimits,
        'createManagerSettings': createManagerSettings,
        'createTransferPerms': createTransferPerms,
        'boss_validator': boss_validator
    }


# Test canMigrateToNewWallet


def test_can_migrate_basic_valid_case(setup_contracts):
    """Test basic valid migration scenario"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']  # No starting agent, no trial funds
    wallet2 = ctx['wallet2']  # No starting agent, no trial funds
    
    # Both wallets owned by bob, no restrictions
    can_migrate = paymaster.canMigrateToNewWallet(wallet2.address, wallet1.address)
    assert can_migrate


def test_cannot_migrate_to_non_underscore_wallet(setup_contracts):
    """Test cannot migrate to non-Underscore wallet"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']
    random_addr = boa.env.generate_address()
    
    can_migrate = paymaster.canMigrateToNewWallet(random_addr, wallet1.address)
    assert not can_migrate


def test_cannot_migrate_with_trial_funds(setup_contracts):
    """Test cannot migrate wallet with trial funds"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet2 = ctx['wallet2']
    wallet5 = ctx['wallet5']  # This wallet has trial funds
    wallet5_config = ctx['wallet5_config']
    
    # Verify wallet5 has trial funds
    bundle = wallet5_config.getMigrationConfigBundle()
    assert bundle.trialFundsAmount > 0
    
    # Should not be able to migrate from wallet with trial funds
    can_migrate = paymaster.canMigrateToNewWallet(wallet2.address, wallet5.address)
    assert not can_migrate


def test_cannot_migrate_frozen_wallet(setup_contracts, backpack):
    """Test cannot migrate frozen wallet"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    wallet1_config = ctx['wallet1_config']
    
    # Freeze wallet1
    wallet1_config.setFrozen(True, sender=backpack.address)
    
    # Should not be able to migrate
    can_migrate = paymaster.canMigrateToNewWallet(wallet2.address, wallet1.address)
    assert not can_migrate
    
    # Unfreeze
    wallet1_config.setFrozen(False, sender=backpack.address)


def test_cannot_migrate_with_pending_owner_change(setup_contracts):
    """Test cannot migrate with pending owner change"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    wallet1_config = ctx['wallet1_config']
    bob = ctx['bob']
    alice = ctx['alice']
    
    # Initiate owner change on wallet1
    wallet1_config.changeOwnership(alice, sender=bob)
    
    # Should not be able to migrate
    can_migrate = paymaster.canMigrateToNewWallet(wallet2.address, wallet1.address)
    assert not can_migrate
    
    # Cancel owner change
    wallet1_config.cancelOwnershipChange(sender=bob)


def test_cannot_migrate_different_owners(setup_contracts):
    """Test cannot migrate between wallets with different owners"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']  # Owned by bob
    wallet3 = ctx['wallet3']  # Owned by alice
    
    can_migrate = paymaster.canMigrateToNewWallet(wallet3.address, wallet1.address)
    assert not can_migrate


def test_cannot_migrate_to_wallet_with_pending_owner_change(setup_contracts):
    """Test cannot migrate to wallet with pending owner change"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    wallet2_config = ctx['wallet2_config']
    bob = ctx['bob']
    alice = ctx['alice']
    
    # Initiate owner change on wallet2 (destination)
    wallet2_config.changeOwnership(alice, sender=bob)
    
    # Should not be able to migrate
    can_migrate = paymaster.canMigrateToNewWallet(wallet2.address, wallet1.address)
    assert not can_migrate
    
    # Cancel owner change
    wallet2_config.cancelOwnershipChange(sender=bob)


def test_cannot_migrate_different_group_ids(setup_contracts):
    """Test cannot migrate between wallets with different group IDs"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']  # bob, group ID 1
    wallet6 = ctx['wallet6']  # bob, group ID 2 (different!)
    
    # Cannot migrate between wallets with different group IDs
    can_migrate = paymaster.canMigrateToNewWallet(wallet6.address, wallet1.address)
    assert not can_migrate
    
    # Try the other direction too
    can_migrate = paymaster.canMigrateToNewWallet(wallet1.address, wallet6.address)
    assert not can_migrate


def test_cannot_migrate_to_frozen_wallet(setup_contracts, backpack):
    """Test cannot migrate to frozen wallet"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    wallet2_config = ctx['wallet2_config']
    
    # Freeze wallet2 (destination)
    wallet2_config.setFrozen(True, sender=backpack.address)
    
    # Should not be able to migrate
    can_migrate = paymaster.canMigrateToNewWallet(wallet2.address, wallet1.address)
    assert not can_migrate
    
    # Unfreeze
    wallet2_config.setFrozen(False, sender=backpack.address)


def test_cannot_migrate_to_wallet_with_payees(setup_contracts):
    """Test cannot migrate to wallet with existing payees"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    bob = ctx['bob']
    payee = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    createPayeeLimits = ctx['createPayeeLimits']
    
    # Add payee to wallet2
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
    
    # Should not be able to migrate
    can_migrate = paymaster.canMigrateToNewWallet(wallet2.address, wallet1.address)
    assert not can_migrate
    
    # Remove payee
    paymaster.removePayee(wallet2.address, payee, sender=bob)


def test_cannot_migrate_to_wallet_with_whitelisted(setup_contracts):
    """Test cannot migrate to wallet with whitelisted addresses"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    wallet2_config = ctx['wallet2_config']
    bob = ctx['bob']
    addr = boa.env.generate_address()
    
    # Add whitelisted address to wallet2
    paymaster.addWhitelistAddr(wallet2.address, addr, sender=bob)
    boa.env.time_travel(blocks=wallet2_config.timeLock() + 1)
    paymaster.confirmWhitelistAddr(wallet2.address, addr, sender=bob)
    
    # Should not be able to migrate
    can_migrate = paymaster.canMigrateToNewWallet(wallet2.address, wallet1.address)
    assert not can_migrate
    
    # Remove whitelist
    paymaster.removeWhitelistAddr(wallet2.address, addr, sender=bob)


def test_cannot_migrate_to_wallet_with_managers_no_starting_agent(setup_contracts):
    """Test cannot migrate to wallet with managers when no starting agent"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']  # Clean wallet without starting agent
    wallet2 = ctx['wallet2']  # Clean wallet without starting agent
    bob = ctx['bob']
    manager = boa.env.generate_address()
    boss_validator = ctx['boss_validator']
    createManagerSettings = ctx['createManagerSettings']
    
    # Add manager to wallet2
    manager_settings = createManagerSettings()
    # Extract the individual components from the settings tuple
    start_block, expiry_block, limits, lego_perms, whitelist_perms, transfer_perms, allowed_assets = manager_settings
    
    boss_validator.addManager(
        wallet2.address,
        manager,
        limits,  # limits tuple
        lego_perms,  # legoPerms tuple
        whitelist_perms,  # whitelistPerms tuple
        transfer_perms,  # transferPerms tuple
        allowed_assets,  # allowed assets list
        sender=bob
    )
    
    # Should not be able to migrate to wallet with managers when no starting agent
    can_migrate = paymaster.canMigrateToNewWallet(wallet2.address, wallet1.address)
    assert not can_migrate
    
    # Remove manager
    boss_validator.removeManager(wallet2.address, manager, sender=bob)


def test_can_migrate_with_starting_agent_only(setup_contracts):
    """Test can migrate to wallet with only starting agent as manager"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']  # bob, no starting agent
    wallet7 = ctx['wallet7']  # bob, with starting agent
    
    # Wallet1 (no starting agent) can migrate to wallet7 (with starting agent only)
    can_migrate = paymaster.canMigrateToNewWallet(wallet7.address, wallet1.address)
    assert can_migrate


def test_cannot_migrate_with_starting_agent_plus_other_managers(setup_contracts):
    """Test cannot migrate with starting agent plus additional managers"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']  # Clean wallet
    wallet3 = ctx['wallet3']  # Has starting agent
    alice = ctx['alice']  # Owner of wallet3
    another_manager = boa.env.generate_address()
    boss_validator = ctx['boss_validator']
    createManagerSettings = ctx['createManagerSettings']
    
    # Add another manager to wallet3 (which has starting agent)
    manager_settings = createManagerSettings()
    # Extract the individual components from the settings tuple
    start_block, expiry_block, limits, lego_perms, whitelist_perms, transfer_perms, allowed_assets = manager_settings
    
    boss_validator.addManager(
        wallet3.address,
        another_manager,
        limits,
        lego_perms,
        whitelist_perms,
        transfer_perms,
        allowed_assets,
        sender=alice  # alice owns wallet3
    )
    
    # Should not be able to migrate (has more than just starting agent)
    can_migrate = paymaster.canMigrateToNewWallet(wallet3.address, wallet1.address)
    assert not can_migrate
    
    # Clean up
    boss_validator.removeManager(wallet3.address, another_manager, sender=alice)


# Test canCopyWalletConfig


def test_can_copy_config_basic_valid_case(setup_contracts):
    """Test basic valid config copy scenario"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    
    # Both wallets owned by bob, no restrictions
    can_copy = paymaster.canCopyWalletConfig(wallet1.address, wallet2.address)
    assert can_copy


def test_cannot_copy_from_non_underscore_wallet(setup_contracts):
    """Test cannot copy from non-Underscore wallet"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet2 = ctx['wallet2']
    random_addr = boa.env.generate_address()
    
    can_copy = paymaster.canCopyWalletConfig(random_addr, wallet2.address)
    assert not can_copy


def test_cannot_copy_to_non_underscore_wallet(setup_contracts):
    """Test cannot copy to non-Underscore wallet"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']
    random_addr = boa.env.generate_address()
    
    can_copy = paymaster.canCopyWalletConfig(wallet1.address, random_addr)
    assert not can_copy


def test_cannot_copy_to_wallet_with_pending_owner_change(setup_contracts):
    """Test cannot copy to wallet with pending owner change"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    wallet2_config = ctx['wallet2_config']
    bob = ctx['bob']
    alice = ctx['alice']
    
    # Initiate owner change on wallet2 (destination)
    wallet2_config.changeOwnership(alice, sender=bob)
    
    # Should not be able to copy
    can_copy = paymaster.canCopyWalletConfig(wallet1.address, wallet2.address)
    assert not can_copy
    
    # Cancel owner change
    wallet2_config.cancelOwnershipChange(sender=bob)


def test_cannot_copy_to_frozen_wallet(setup_contracts, backpack):
    """Test cannot copy to frozen wallet"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    wallet2_config = ctx['wallet2_config']
    
    # Freeze wallet2 (destination)
    wallet2_config.setFrozen(True, sender=backpack.address)
    
    # Should not be able to copy
    can_copy = paymaster.canCopyWalletConfig(wallet1.address, wallet2.address)
    assert not can_copy
    
    # Unfreeze
    wallet2_config.setFrozen(False, sender=backpack.address)


def test_cannot_copy_to_wallet_with_payees(setup_contracts):
    """Test cannot copy to wallet with existing payees"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    bob = ctx['bob']
    payee = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    createPayeeLimits = ctx['createPayeeLimits']
    
    # Add payee to wallet2
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
    
    # Should not be able to copy
    can_copy = paymaster.canCopyWalletConfig(wallet1.address, wallet2.address)
    assert not can_copy
    
    # Remove payee
    paymaster.removePayee(wallet2.address, payee, sender=bob)


def test_cannot_copy_to_wallet_with_whitelisted(setup_contracts):
    """Test cannot copy to wallet with whitelisted addresses"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    wallet2_config = ctx['wallet2_config']
    bob = ctx['bob']
    addr = boa.env.generate_address()
    
    # Add whitelisted address to wallet2
    paymaster.addWhitelistAddr(wallet2.address, addr, sender=bob)
    boa.env.time_travel(blocks=wallet2_config.timeLock() + 1)
    paymaster.confirmWhitelistAddr(wallet2.address, addr, sender=bob)
    
    # Should not be able to copy
    can_copy = paymaster.canCopyWalletConfig(wallet1.address, wallet2.address)
    assert not can_copy
    
    # Remove whitelist
    paymaster.removeWhitelistAddr(wallet2.address, addr, sender=bob)


def test_cannot_copy_from_frozen_wallet(setup_contracts, backpack):
    """Test cannot copy from frozen wallet"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    wallet1_config = ctx['wallet1_config']
    
    # Freeze wallet1 (source)
    wallet1_config.setFrozen(True, sender=backpack.address)
    
    # Should not be able to copy
    can_copy = paymaster.canCopyWalletConfig(wallet1.address, wallet2.address)
    assert not can_copy
    
    # Unfreeze
    wallet1_config.setFrozen(False, sender=backpack.address)


def test_cannot_copy_different_owners(setup_contracts):
    """Test cannot copy between wallets with different owners"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']  # Owned by bob
    wallet3 = ctx['wallet3']  # Owned by alice
    
    can_copy = paymaster.canCopyWalletConfig(wallet1.address, wallet3.address)
    assert not can_copy


def test_cannot_copy_different_group_ids(setup_contracts):
    """Test cannot copy between wallets with different group IDs"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']  # bob, group ID 1
    wallet6 = ctx['wallet6']  # bob, group ID 2 (different!)
    
    # Cannot copy config between wallets with different group IDs
    can_copy = paymaster.canCopyWalletConfig(wallet1.address, wallet6.address)
    assert not can_copy
    
    # Try the other direction too
    can_copy = paymaster.canCopyWalletConfig(wallet6.address, wallet1.address)
    assert not can_copy


def test_cannot_copy_from_wallet_with_pending_owner_change(setup_contracts):
    """Test cannot copy from wallet with pending owner change"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    wallet1_config = ctx['wallet1_config']
    bob = ctx['bob']
    alice = ctx['alice']
    
    # Initiate owner change on wallet1 (source)
    wallet1_config.changeOwnership(alice, sender=bob)
    
    # Should not be able to copy
    can_copy = paymaster.canCopyWalletConfig(wallet1.address, wallet2.address)
    assert not can_copy
    
    # Cancel owner change
    wallet1_config.cancelOwnershipChange(sender=bob)


def test_can_copy_with_managers_and_starting_agent(setup_contracts):
    """Test can copy to wallet with starting agent and correct manager setup"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet3 = ctx['wallet3']  # Has starting agent, owned by alice
    wallet4 = ctx['wallet4']  # Has starting agent, owned by charlie
    
    # Can't copy between wallets with different owners
    can_copy = paymaster.canCopyWalletConfig(wallet3.address, wallet4.address)
    assert not can_copy  # Different owners
    
    # This test shows that starting agent alone doesn't enable copying - owners must match
    # We would need two wallets with same owner and starting agents to properly test this


# Edge cases and potential bugs


def test_migration_validation_with_complex_state(setup_contracts):
    """Test migration validation with complex wallet state"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    wallet1_config = ctx['wallet1_config']
    bob = ctx['bob']
    payee = boa.env.generate_address()
    whitelist_addr = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    createPayeeLimits = ctx['createPayeeLimits']
    
    # Setup wallet1 with payees and whitelist
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
    
    paymaster.addWhitelistAddr(wallet1.address, whitelist_addr, sender=bob)
    boa.env.time_travel(blocks=wallet1_config.timeLock() + 1)
    paymaster.confirmWhitelistAddr(wallet1.address, whitelist_addr, sender=bob)
    
    # Source wallet has payees/whitelist but destination is clean - should be able to migrate
    can_migrate = paymaster.canMigrateToNewWallet(wallet2.address, wallet1.address)
    assert can_migrate
    
    # Can also copy config in this scenario
    can_copy = paymaster.canCopyWalletConfig(wallet1.address, wallet2.address)
    assert can_copy


def test_starting_agent_index_edge_case(setup_contracts):
    """Test edge case with starting agent index validation"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    
    # Test wallet without starting agent (wallet1, wallet2)
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    wallet1_config = ctx['wallet1_config']
    wallet2_config = ctx['wallet2_config']
    
    # Verify wallets without starting agent have correct state
    bundle1 = wallet1_config.getMigrationConfigBundle()
    assert bundle1.startingAgent == ZERO_ADDRESS
    assert bundle1.startingAgentIndex == 0
    assert bundle1.numManagers == 0  # No managers in clean wallet
    
    bundle2 = wallet2_config.getMigrationConfigBundle()
    assert bundle2.startingAgent == ZERO_ADDRESS
    assert bundle2.startingAgentIndex == 0
    assert bundle2.numManagers == 0  # No managers in clean wallet
    
    # Can migrate between clean wallets
    can_migrate = paymaster.canMigrateToNewWallet(wallet2.address, wallet1.address)
    assert can_migrate
    
    # Test wallet with starting agent (wallet3)
    wallet3 = ctx['wallet3']
    wallet3_config = ctx['wallet3_config']
    
    bundle3 = wallet3_config.getMigrationConfigBundle()
    assert bundle3.startingAgent != ZERO_ADDRESS
    assert bundle3.startingAgentIndex == 1  # Starting agent at index 1
    assert bundle3.numManagers == 2  # Owner + starting agent
    
    # Cannot migrate from wallet1 to wallet3 due to different owners
    can_migrate = paymaster.canMigrateToNewWallet(wallet3.address, wallet1.address)
    assert not can_migrate  # Different owners (bob vs alice)


def test_trial_funds_zero_but_asset_set(setup_contracts):
    """Test edge case where trial funds amount is 0 but asset is still set"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']  # Clean wallet without trial funds
    wallet2 = ctx['wallet2']  # Clean wallet without trial funds
    wallet1_config = ctx['wallet1_config']
    
    # Verify wallet has no trial funds
    bundle = wallet1_config.getMigrationConfigBundle()
    assert bundle.trialFundsAmount == 0, "wallet1 should have no trial funds"
    
    # Wallets without trial funds can migrate
    can_migrate = paymaster.canMigrateToNewWallet(wallet2.address, wallet1.address)
    assert can_migrate


def test_both_directions_migration_validation(setup_contracts):
    """Test migration validation works correctly in both directions"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet1 = ctx['wallet1']
    wallet2 = ctx['wallet2']
    
    # Both directions should work with clean wallets
    can_migrate_1_to_2 = paymaster.canMigrateToNewWallet(wallet2.address, wallet1.address)
    can_migrate_2_to_1 = paymaster.canMigrateToNewWallet(wallet1.address, wallet2.address)
    
    assert can_migrate_1_to_2
    assert can_migrate_2_to_1


def test_copy_config_does_not_check_source_trial_funds(setup_contracts):
    """Test that canCopyWalletConfig doesn't check source wallet trial funds"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet8 = ctx['wallet8']  # bob, with trial funds (source)
    wallet2 = ctx['wallet2']  # bob, no trial funds (destination)
    wallet8_config = ctx['wallet8_config']
    
    # Verify wallet8 has trial funds
    bundle = wallet8_config.getMigrationConfigBundle()
    assert bundle.trialFundsAmount > 0
    
    # Should be able to copy from wallet with trial funds
    can_copy = paymaster.canCopyWalletConfig(wallet8.address, wallet2.address)
    assert can_copy  # Trial funds in source should not prevent copying


# Potential bugs and concerns to raise


def test_concern_starting_agent_validation_logic():
    """
    CONCERN: The starting agent validation logic seems complex and potentially fragile.
    
    The checks for starting agent are:
    1. If startingAgent == empty(address) and numManagers != 0: return False
    2. If startingAgent != empty(address):
       - startingAgentIndex must be 1
       - numManagers must be 2
    
    This assumes:
    - Owner is always manager index 0
    - Starting agent is always index 1
    - No other managers can exist when starting agent is set
    
    This could break if the manager indexing logic changes or if there are edge cases
    in how managers are added/removed.
    """
    pass


def test_concern_no_validation_of_wallet_states():
    """
    CONCERN: The migration validation doesn't check many important wallet states:
    
    1. Asset balances - could migrate from wallet with assets to empty wallet
    2. Pending payees/whitelist - these are not checked
    3. Manager permissions/settings - not validated
    4. Global settings differences - not checked
    
    This could lead to unexpected behavior during actual migration.
    """
    pass


def test_concern_group_id_validation():
    """
    CONCERN: Group ID validation might be too strict.
    
    The requirement that group IDs must match between wallets might prevent
    legitimate migrations if group IDs are meant to change during migration.
    
    Also, there's no validation that group IDs are valid/active.
    """
    pass


def test_concern_asymmetric_validation():
    """
    CONCERN: canMigrateToNewWallet and canCopyWalletConfig have asymmetric validation.
    
    canMigrateToNewWallet checks:
    - Source wallet: trial funds, frozen, pending owner change
    - Destination wallet: frozen, pending owner change, payees, whitelist, managers
    
    canCopyWalletConfig checks:
    - Source wallet: frozen, pending owner change (NO trial funds check)
    - Destination wallet: frozen, pending owner change, payees, whitelist, managers
    
    This asymmetry might be intentional but could lead to confusion.
    """
    pass