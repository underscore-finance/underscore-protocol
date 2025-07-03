"""
Test manager operations in BossValidator
"""
import pytest
import boa

from contracts.core.userWallet import UserWallet, UserWalletConfig
from constants import EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ZERO_ADDRESS
from conf_utils import filter_logs


@pytest.fixture(scope="module")
def setup_wallet(setUserWalletConfig, setManagerConfig, hatchery, bob):
    """Setup user wallet with config"""
    setUserWalletConfig()
    setManagerConfig()
    
    wallet_addr = hatchery.createUserWallet(sender=bob)
    assert wallet_addr != ZERO_ADDRESS
    return UserWallet.at(wallet_addr)


@pytest.fixture(scope="module") 
def setup_contracts(setup_wallet, boss_validator, alice, bob, charlie):
    """Setup contracts and basic configuration"""
    user_wallet = setup_wallet
    wallet_config_addr = user_wallet.walletConfig()
    wallet_config = UserWalletConfig.at(wallet_config_addr)
    owner = bob
    
    # Advance some blocks
    boa.env.time_travel(blocks=100)
    
    return {
        'wallet': user_wallet,
        'wallet_config': wallet_config,
        'boss_validator': boss_validator,
        'owner': owner,
        'manager': alice,
        'manager2': charlie
    }


# Test adding managers


def test_add_manager_basic(setup_contracts, createManagerLimits, createLegoPerms,
                          createWhitelistPerms, createTransferPerms):
    """Test adding a manager through BossValidator"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    manager = ctx['manager']
    
    # Create manager settings
    limits = createManagerLimits()
    lego_perms = createLegoPerms()
    whitelist_perms = createWhitelistPerms()
    transfer_perms = createTransferPerms()
    
    # Add manager
    boss.addManager(
        wallet.address,
        manager,
        limits,
        lego_perms,
        whitelist_perms,
        transfer_perms,
        [],  # No asset restrictions
        sender=owner
    )
    
    # Get events from BossValidator (not wallet_config)
    events = filter_logs(boss, "ManagerSettingsModified")
    
    # Verify manager was added
    assert wallet_config.isManager(manager)
    assert len(events) == 1
    assert events[0].manager == manager
    assert events[0].user == wallet.address


def test_add_manager_with_delays(setup_contracts, createManagerLimits, createLegoPerms,
                               createWhitelistPerms, createTransferPerms):
    """Test adding a manager with start and expiry blocks"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    manager = ctx['manager2']
    
    current_block = boa.env.evm.patch.block_number
    start_delay = 100
    activation_length = 10000
    
    # Add manager with specific timing (using delay and length, not absolute blocks)
    boss.addManager(
        wallet.address,
        manager,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        start_delay,  # blocks from now to start
        activation_length,  # how long manager is active
        sender=owner
    )
    
    # Check settings
    settings = wallet_config.managerSettings(manager)
    # Start block should be current + delay
    assert settings[0] >= current_block + start_delay
    # Expiry block should be start + activation_length
    assert settings[1] == settings[0] + activation_length


def test_add_manager_validation_fails(setup_contracts, createManagerLimits, createLegoPerms,
                                    createWhitelistPerms, createTransferPerms):
    """Test that invalid manager settings are rejected"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    owner = ctx['owner']
    manager = ctx['manager']
    
    # Invalid limits (per-tx > per-period)
    invalid_limits = createManagerLimits(
        _maxUsdValuePerTx=1000 * EIGHTEEN_DECIMALS,
        _maxUsdValuePerPeriod=100 * EIGHTEEN_DECIMALS
    )
    
    # Should revert
    with boa.reverts():
        boss.addManager(
            wallet.address,
            manager,
            invalid_limits,
            createLegoPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            sender=owner
        )


# Test updating managers


def test_update_manager_basic(setup_contracts, createManagerLimits, createLegoPerms,
                            createWhitelistPerms, createTransferPerms, sally):
    """Test updating an existing manager"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    manager = sally  # Use sally for this test
    
    # First add manager
    boss.addManager(
        wallet.address,
        manager,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        sender=owner
    )
    
    # Update with new limits
    new_limits = createManagerLimits(
        _maxUsdValuePerTx=500 * EIGHTEEN_DECIMALS
    )
    
    boss.updateManager(
        wallet.address,
        manager,
        new_limits,
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        sender=owner
    )
    
    # Get events from BossValidator right after the update
    events = filter_logs(boss, "ManagerSettingsModified")
    
    # Verify update event
    assert len(events) == 1
    assert events[0].manager == manager
    settings = wallet_config.managerSettings(manager)
    assert settings[2][0] == 500 * EIGHTEEN_DECIMALS  # maxUsdValuePerTx


def test_update_manager_not_exist(setup_contracts, createManagerLimits, createLegoPerms,
                                 createWhitelistPerms, createTransferPerms):
    """Test updating a non-existent manager fails"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    owner = ctx['owner']
    manager = ctx['manager']
    
    # Try to update non-existent manager
    with boa.reverts():
        boss.updateManager(
            wallet.address,
            manager,
            createManagerLimits(),
            createLegoPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            sender=owner
        )


# Test removing managers


def test_remove_manager(setup_contracts, createManagerLimits, createLegoPerms,
                       createWhitelistPerms, createTransferPerms):
    """Test removing a manager"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    manager = ctx['manager']
    
    # First add manager
    boss.addManager(
        wallet.address,
        manager,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        sender=owner
    )
    
    assert wallet_config.isManager(manager)
    
    # Remove manager
    boss.removeManager(wallet.address, manager, sender=owner)
    
    # Get events
    events = filter_logs(boss, "ManagerRemoved")
    
    # Verify removal
    assert not wallet_config.isManager(manager)
    assert len(events) == 1
    assert events[0].user == wallet.address
    assert events[0].manager == manager


def test_remove_non_existent_manager(setup_contracts):
    """Test removing a non-existent manager fails"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    owner = ctx['owner']
    manager = ctx['manager']
    
    # Try to remove non-existent manager
    with boa.reverts():
        boss.removeManager(wallet.address, manager, sender=owner)


# Test manager activation length adjustment


def test_adjust_activation_length(setup_contracts, createManagerLimits, createLegoPerms,
                                createWhitelistPerms, createTransferPerms):
    """Test adjusting manager activation length"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    
    # Generate a unique address for this test to avoid conflicts
    import boa
    manager = boa.env.generate_address("test_adjust_manager")
    
    # Add manager with initial activation length
    initial_length = 1800  # Minimum activation length
    boss.addManager(
        wallet.address,
        manager,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        0,  # no start delay
        initial_length,  # initial activation length
        sender=owner
    )
    
    # Get initial settings
    initial_settings = wallet_config.managerSettings(manager)
    initial_start = initial_settings[0]
    
    # Advance time to ensure manager is active
    current_block = boa.env.evm.patch.block_number
    if current_block < initial_start:
        blocks_to_advance = initial_start - current_block + 1
        boa.env.time_travel(blocks=blocks_to_advance)
    
    # Adjust activation length
    new_length = 2000
    boss.adjustManagerActivationLength(
        wallet.address,
        manager,
        new_length,
        False,  # Don't restart
        sender=owner
    )
    
    # Get events
    events = filter_logs(boss, "ManagerActivationLengthAdjusted")
    
    # Verify adjustment
    assert len(events) == 1
    assert events[0].manager == manager
    assert events[0].activationLength == new_length
    assert events[0].didRestart == False
    
    # Verify expiry was updated
    updated_settings = wallet_config.managerSettings(manager)
    assert updated_settings[0] == initial_start  # Start unchanged
    assert updated_settings[1] == initial_start + new_length  # New expiry


def test_adjust_activation_length_with_restart(setup_contracts, createManagerLimits,
                                             createLegoPerms, createWhitelistPerms,
                                             createTransferPerms):
    """Test adjusting manager activation length with restart"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    
    # Generate a unique address for this test to avoid conflicts
    import boa
    manager = boa.env.generate_address("test_restart_manager")
    
    # Add manager
    boss.addManager(
        wallet.address,
        manager,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        sender=owner
    )
    
    # Get initial settings and advance time to ensure manager is active
    initial_settings = wallet_config.managerSettings(manager)
    initial_start = initial_settings[0]
    current_block = boa.env.evm.patch.block_number
    if current_block < initial_start:
        blocks_to_advance = initial_start - current_block + 1
        boa.env.time_travel(blocks=blocks_to_advance)
    
    # Adjust with restart
    new_length = 3000
    boss.adjustManagerActivationLength(
        wallet.address,
        manager,
        new_length,
        True,  # Restart
        sender=owner
    )
    
    # Get events
    events = filter_logs(boss, "ManagerActivationLengthAdjusted")
    
    # Verify restart
    settings = wallet_config.managerSettings(manager)
    current_block = boa.env.evm.patch.block_number
    assert settings[0] == current_block  # Start block reset
    assert settings[1] == current_block + new_length  # New expiry
    assert events[0].didRestart == True


# Test authorization checks


def test_only_owner_can_add_manager(setup_contracts, createManagerLimits, createLegoPerms,
                                   createWhitelistPerms, createTransferPerms, alice):
    """Test that only owner can add managers"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    manager = ctx['manager']
    
    # Non-owner tries to add manager
    with boa.reverts():
        boss.addManager(
            wallet.address,
            manager,
            createManagerLimits(),
            createLegoPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            sender=alice  # Not the owner
        )


def test_only_owner_can_remove_manager(setup_contracts, createManagerLimits, createLegoPerms,
                                      createWhitelistPerms, createTransferPerms, alice):
    """Test that only owner can remove managers"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    owner = ctx['owner']
    manager = ctx['manager']
    
    # Add manager as owner
    boss.addManager(
        wallet.address,
        manager,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        sender=owner
    )
    
    # Non-owner tries to remove
    with boa.reverts():
        boss.removeManager(wallet.address, manager, sender=alice)


# Test complex scenarios


def test_multiple_managers(setup_contracts, createManagerLimits, createLegoPerms,
                         createWhitelistPerms, createTransferPerms, alice, charlie):
    """Test adding multiple managers with different permissions"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    
    # Add first manager with full permissions
    boss.addManager(
        wallet.address,
        alice,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        sender=owner
    )
    
    # Add second manager with restricted permissions
    restricted_lego = createLegoPerms(
        _canManageYield=False,
        _canManageDebt=False
    )
    restricted_transfer = createTransferPerms(
        _canTransfer=False
    )
    
    boss.addManager(
        wallet.address,
        charlie,
        createManagerLimits(),
        restricted_lego,
        createWhitelistPerms(),
        restricted_transfer,
        [],
        sender=owner
    )
    
    # Verify both are managers
    assert wallet_config.isManager(alice)
    assert wallet_config.isManager(charlie)
    
    # Verify different permissions
    alice_settings = wallet_config.managerSettings(alice)
    charlie_settings = wallet_config.managerSettings(charlie)
    
    # Alice has full lego permissions
    assert alice_settings[3][0] == True  # canManageYield
    assert alice_settings[3][2] == True  # canManageDebt
    
    # Charlie has restricted permissions
    assert charlie_settings[3][0] == False  # canManageYield
    assert charlie_settings[3][2] == False  # canManageDebt