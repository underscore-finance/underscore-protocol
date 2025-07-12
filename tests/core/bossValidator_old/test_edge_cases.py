"""
Test edge cases and boundary conditions for BossValidator
"""
import pytest
import boa
from eth_utils import to_checksum_address

from contracts.core.userWallet import UserWallet, UserWalletConfig
from constants import EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ZERO_ADDRESS, ACTION_TYPE
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
    
    return {
        'wallet': user_wallet,
        'wallet_config': wallet_config,
        'boss_validator': boss_validator,
        'owner': owner,
        'manager': alice,
        'manager2': charlie
    }


# Test manager expiry at exact boundaries


def test_manager_expiry_boundary(setup_contracts, createManagerLimits,
                                createLegoPerms, createWhitelistPerms,
                                createTransferPerms):
    """Test manager access around expiry time"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    owner = ctx['owner']
    # Use unique address to avoid conflicts
    manager = to_checksum_address("0x" + "E" * 40)
    
    # Add manager with specific activation length (must be at least 1800 blocks = 1 hour)
    activation_length = 2000
    boss.addManager(
        wallet.address,
        manager,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        0,  # Start immediately
        activation_length,
        sender=owner
    )
    
    # Advance time to ensure manager is active (global settings may add delay)
    boa.env.time_travel(blocks=100)
    assert boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.TRANSFER))
    
    # Advance time past expiry
    boa.env.time_travel(blocks=activation_length + 100)
    
    # Manager should be inactive after expiry
    assert not boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.TRANSFER))


def test_manager_start_exact_boundary(setup_contracts, createManagerLimits,
                                     createLegoPerms, createWhitelistPerms,
                                     createTransferPerms):
    """Test manager access at exact start block boundary"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    owner = ctx['owner']
    # Use unique address to avoid conflicts
    manager = to_checksum_address("0x" + "F" * 40)
    
    # Add manager starting in future
    start_delay = 100
    boss.addManager(
        wallet.address,
        manager,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        start_delay,
        ONE_DAY_IN_BLOCKS,
        sender=owner
    )
    
    # Test before start block
    boa.env.time_travel(blocks=start_delay - 1)
    assert not boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.TRANSFER))
    
    # Test at exact start block
    boa.env.time_travel(blocks=1)
    assert boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.TRANSFER))
    
    # Test after start block
    boa.env.time_travel(blocks=1)
    assert boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.TRANSFER))


# Test period reset boundaries


def test_period_reset_exact_boundary(setup_contracts, createManagerData, 
                                    createManagerLimits):
    """Test period reset at exact block boundary"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    # Advance enough blocks to ensure we can have an old period
    boa.env.time_travel(blocks=ONE_DAY_IN_BLOCKS * 2)
    
    current_block = boa.env.evm.patch.block_number
    period_length = ONE_DAY_IN_BLOCKS
    
    # Create data at exact period boundary
    period_start = current_block - period_length
    data = createManagerData(
        _numTxsInPeriod=10,
        _totalUsdValueInPeriod=1000 * EIGHTEEN_DECIMALS,
        _totalNumTxs=50,
        _totalUsdValue=5000 * EIGHTEEN_DECIMALS,
        _periodStartBlock=period_start
    )
    
    # Transaction at exact period boundary should reset
    limits = createManagerLimits()
    updated_data = boss.checkManagerUsdLimitsAndUpdateData(
        100 * EIGHTEEN_DECIMALS,
        limits,
        limits,
        period_length,
        data
    )
    
    # Period should be reset
    assert updated_data[0] == 1  # numTxsInPeriod reset
    assert updated_data[1] == 100 * EIGHTEEN_DECIMALS  # totalUsdValueInPeriod reset
    assert updated_data[2] == 51  # totalNumTxs incremented
    assert updated_data[3] == 5100 * EIGHTEEN_DECIMALS  # totalUsdValue incremented
    assert updated_data[5] >= current_block  # New period started


def test_period_reset_one_block_before(setup_contracts, createManagerData,
                                      createManagerLimits):
    """Test that period doesn't reset one block before boundary"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    current_block = boa.env.evm.patch.block_number
    period_length = ONE_DAY_IN_BLOCKS
    
    # Create data one block before period end
    # Ensure the period start is positive
    period_start = max(1, current_block - period_length + 1)
    data = createManagerData(
        _numTxsInPeriod=10,
        _totalUsdValueInPeriod=1000 * EIGHTEEN_DECIMALS,
        _periodStartBlock=period_start
    )
    
    # Transaction before period boundary should not reset
    limits = createManagerLimits()
    updated_data = boss.checkManagerUsdLimitsAndUpdateData(
        100 * EIGHTEEN_DECIMALS,
        limits,
        limits,
        period_length,
        data
    )
    
    # Period should NOT be reset
    assert updated_data[0] == 11  # numTxsInPeriod incremented
    assert updated_data[1] == 1100 * EIGHTEEN_DECIMALS  # totalUsdValueInPeriod incremented
    assert updated_data[5] == period_start  # periodStartBlock unchanged


# Test USD limit enforcement boundaries


def test_usd_limit_exact_boundary(setup_contracts, createManagerData,
                                  createManagerLimits):
    """Test USD limits at exact boundary values"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    # Test per-transaction limit at exact boundary
    tx_limit = 1000 * EIGHTEEN_DECIMALS
    limits = createManagerLimits(
        _maxUsdValuePerTx=tx_limit
    )
    
    data = createManagerData()
    
    # Transaction at exact limit should succeed
    updated_data = boss.checkManagerUsdLimitsAndUpdateData(
        tx_limit,  # Exactly at limit
        limits,
        createManagerLimits(),
        ONE_DAY_IN_BLOCKS,
        data
    )
    assert updated_data[1] == tx_limit
    
    # Transaction exceeding limit by 1 wei should fail
    with boa.reverts("usd value limit exceeded"):
        boss.checkManagerUsdLimitsAndUpdateData(
            tx_limit + 1,  # 1 wei over limit
            limits,
            createManagerLimits(),
            ONE_DAY_IN_BLOCKS,
            data
        )


def test_usd_period_limit_accumulation(setup_contracts, createManagerData,
                                      createManagerLimits):
    """Test USD period limit with accumulated transactions"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    period_limit = 1000 * EIGHTEEN_DECIMALS
    limits = createManagerLimits(
        _maxUsdValuePerPeriod=period_limit
    )
    
    # Start with some accumulated value
    data = createManagerData(
        _totalUsdValueInPeriod=900 * EIGHTEEN_DECIMALS,
        _periodStartBlock=boa.env.evm.patch.block_number
    )
    
    # Transaction that brings us to exact limit should succeed
    updated_data = boss.checkManagerUsdLimitsAndUpdateData(
        100 * EIGHTEEN_DECIMALS,  # Total will be exactly 1000
        limits,
        createManagerLimits(),
        ONE_DAY_IN_BLOCKS,
        data
    )
    assert updated_data[1] == period_limit
    
    # Next transaction should fail
    with boa.reverts("usd value limit exceeded"):
        boss.checkManagerUsdLimitsAndUpdateData(
            1,  # Even 1 wei over should fail
            limits,
            createManagerLimits(),
            ONE_DAY_IN_BLOCKS,
            updated_data
        )


# Test global vs specific limit interactions


def test_global_limits_override_at_boundaries(setup_contracts, createManagerData,
                                             createManagerLimits):
    """Test that global limits override specific limits at exact boundaries"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    # Specific limits are generous
    specific_limits = createManagerLimits(
        _maxUsdValuePerTx=1000 * EIGHTEEN_DECIMALS
    )
    
    # Global limits are restrictive
    global_limits = createManagerLimits(
        _maxUsdValuePerTx=100 * EIGHTEEN_DECIMALS
    )
    
    data = createManagerData()
    
    # Transaction at global limit should succeed
    updated_data = boss.checkManagerUsdLimitsAndUpdateData(
        100 * EIGHTEEN_DECIMALS,  # At global limit
        specific_limits,
        global_limits,
        ONE_DAY_IN_BLOCKS,
        data
    )
    assert updated_data[1] == 100 * EIGHTEEN_DECIMALS
    
    # Transaction exceeding global limit should fail even if within specific limit
    with boa.reverts("usd value limit exceeded"):
        boss.checkManagerUsdLimitsAndUpdateData(
            101 * EIGHTEEN_DECIMALS,  # Over global, under specific
            specific_limits,
            global_limits,
            ONE_DAY_IN_BLOCKS,
            data
        )


# Test zero value edge cases


def test_zero_usd_transaction(setup_contracts, createManagerData,
                              createManagerLimits):
    """Test handling of zero USD value transactions"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    limits = createManagerLimits(
        _maxUsdValuePerTx=1000 * EIGHTEEN_DECIMALS
    )
    
    data = createManagerData(
        _numTxsInPeriod=5,
        _totalUsdValueInPeriod=500 * EIGHTEEN_DECIMALS,
        _totalNumTxs=5,  # Set initial total to match period count
        _totalUsdValue=500 * EIGHTEEN_DECIMALS  # Set initial total to match period value
    )
    
    # Zero value transaction should still increment counters
    updated_data = boss.checkManagerUsdLimitsAndUpdateData(
        0,  # Zero USD value
        limits,
        createManagerLimits(),
        ONE_DAY_IN_BLOCKS,
        data
    )
    
    # Counters should increment but USD value stays same
    assert updated_data[0] == 6  # numTxsInPeriod incremented
    assert updated_data[1] == 500 * EIGHTEEN_DECIMALS  # totalUsdValueInPeriod unchanged
    assert updated_data[2] == 6  # totalNumTxs incremented
    assert updated_data[3] == 500 * EIGHTEEN_DECIMALS  # totalUsdValue unchanged
    assert updated_data[4] == boa.env.evm.patch.block_number  # lastTxBlock updated


def test_zero_limit_means_unlimited(setup_contracts, createManagerData,
                                   createManagerLimits):
    """Test that zero limits are treated as unlimited"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    # All limits set to zero (unlimited)
    limits = createManagerLimits(
        _maxUsdValuePerTx=0,
        _maxUsdValuePerPeriod=0,
        _maxUsdValueLifetime=0
    )
    
    data = createManagerData()
    
    # Very large transaction should succeed with zero limits
    huge_amount = 1_000_000 * EIGHTEEN_DECIMALS
    updated_data = boss.checkManagerUsdLimitsAndUpdateData(
        huge_amount,
        limits,
        createManagerLimits(),  # Global limits also zero
        ONE_DAY_IN_BLOCKS,
        data
    )
    
    assert updated_data[1] == huge_amount
    assert updated_data[3] == huge_amount


# Test overflow protection


def test_usd_accumulation_overflow_protection(setup_contracts, createManagerData,
                                             createManagerLimits):
    """Test that USD accumulation handles large values safely"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    # Start with very large accumulated values
    large_value = 2**255 - EIGHTEEN_DECIMALS * 1000  # Close to max uint256/2
    data = createManagerData(
        _totalUsdValueInPeriod=large_value,
        _totalUsdValue=large_value,
        _periodStartBlock=boa.env.evm.patch.block_number
    )
    
    limits = createManagerLimits()  # No limits
    
    # Adding more should still work without overflow
    add_value = EIGHTEEN_DECIMALS * 100
    updated_data = boss.checkManagerUsdLimitsAndUpdateData(
        add_value,
        limits,
        limits,
        ONE_DAY_IN_BLOCKS,
        data
    )
    
    assert updated_data[1] == large_value + add_value
    assert updated_data[3] == large_value + add_value


# Test manager removal edge cases


def test_remove_manager_with_pending_data(setup_contracts, createManagerLimits,
                                         createLegoPerms, createWhitelistPerms,
                                         createTransferPerms):
    """Test removing manager who has accumulated transaction data"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    # Use unique address to avoid conflicts
    manager = to_checksum_address("0x" + "D" * 40)
    
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
    
    # Ensure manager is active
    settings = wallet_config.managerSettings(manager)
    if boa.env.evm.patch.block_number < settings[0]:
        boa.env.time_travel(blocks=settings[0] - boa.env.evm.patch.block_number + 1)
    
    # Verify manager can act
    assert boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.TRANSFER))
    
    # Remove manager
    boss.removeManager(wallet.address, manager, sender=owner)
    
    # Verify manager cannot act anymore
    assert not boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.TRANSFER))
    assert not wallet_config.isManager(manager)


# Test concurrent manager scenarios


def test_multiple_managers_same_block(setup_contracts, createManagerLimits,
                                     createLegoPerms, createWhitelistPerms,
                                     createTransferPerms):
    """Test multiple managers added in same block"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    
    # Use unique addresses to avoid conflicts
    manager1 = to_checksum_address("0x" + "A" * 40)
    manager2 = to_checksum_address("0x" + "B" * 40)
    
    # Add two managers in same block
    boss.addManager(
        wallet.address,
        manager1,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        sender=owner
    )
    
    boss.addManager(
        wallet.address,
        manager2,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        sender=owner
    )
    
    # Both should be managers
    assert wallet_config.isManager(manager1)
    assert wallet_config.isManager(manager2)
    
    # Both should have same start block
    settings1 = wallet_config.managerSettings(manager1)
    settings2 = wallet_config.managerSettings(manager2)
    assert settings1[0] == settings2[0]  # Same start block