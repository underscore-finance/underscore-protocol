"""
Test manager limits and USD tracking in BossValidator
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
    owner = bob  # bob is the owner
    
    # Advance some blocks to ensure we're not at block 0
    boa.env.time_travel(blocks=100)
    
    return {
        'wallet': user_wallet,
        'wallet_config': wallet_config,
        'boss_validator': boss_validator,
        'owner': owner,
        'manager': alice,
        'non_manager': charlie
    }


# Test USD limit checking and tracking


def test_update_manager_data_on_transaction(setup_contracts, createManagerData,
                                           createManagerLimits):
    """Test that manager data is updated correctly after transactions"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    # Initial data
    initial_data = createManagerData(
        _numTxsInPeriod=2,
        _totalUsdValueInPeriod=500 * EIGHTEEN_DECIMALS,
        _totalNumTxs=10,
        _totalUsdValue=5000 * EIGHTEEN_DECIMALS,
        _lastTxBlock=boa.env.evm.patch.block_number - 100
    )
    
    # Limits
    limits = createManagerLimits(
        _maxUsdValuePerTx=1000 * EIGHTEEN_DECIMALS,
        _maxUsdValuePerPeriod=2000 * EIGHTEEN_DECIMALS,
        _maxUsdValueLifetime=10000 * EIGHTEEN_DECIMALS
    )
    
    global_limits = createManagerLimits()  # No global limits
    
    # Check limits and get updated data
    tx_value = 300 * EIGHTEEN_DECIMALS
    updated_data = boss.checkManagerUsdLimitsAndUpdateData(
        tx_value,
        limits,
        global_limits,
        ONE_DAY_IN_BLOCKS,  # manager period
        initial_data
    )
    
    # Verify updates
    assert updated_data[0] == 3  # numTxsInPeriod incremented
    assert updated_data[1] == 800 * EIGHTEEN_DECIMALS  # totalUsdValueInPeriod updated
    assert updated_data[2] == 11  # totalNumTxs incremented
    assert updated_data[3] == 5300 * EIGHTEEN_DECIMALS  # totalUsdValue updated
    assert updated_data[4] == boa.env.evm.patch.block_number  # lastTxBlock updated


def test_period_reset(setup_contracts, createManagerData, createManagerLimits):
    """Test that period data resets after period ends"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    # First advance enough blocks to ensure we can have an old period
    boa.env.time_travel(blocks=ONE_DAY_IN_BLOCKS * 2)
    
    # Create data from previous period
    old_period_start = boa.env.evm.patch.block_number - (ONE_DAY_IN_BLOCKS + 100)
    data = createManagerData(
        _numTxsInPeriod=10,
        _totalUsdValueInPeriod=1000 * EIGHTEEN_DECIMALS,
        _totalNumTxs=50,
        _totalUsdValue=5000 * EIGHTEEN_DECIMALS,
        _periodStartBlock=old_period_start
    )
    
    limits = createManagerLimits()
    
    # Check limits - should reset period
    tx_value = 100 * EIGHTEEN_DECIMALS
    updated_data = boss.checkManagerUsdLimitsAndUpdateData(
        tx_value,
        limits,
        limits,
        ONE_DAY_IN_BLOCKS,
        data
    )
    
    # Period data should be reset
    assert updated_data[0] == 1  # numTxsInPeriod reset to 1
    assert updated_data[1] == tx_value  # totalUsdValueInPeriod reset to tx_value
    assert updated_data[2] == 51  # totalNumTxs continues incrementing
    assert updated_data[3] == 5100 * EIGHTEEN_DECIMALS  # totalUsdValue continues
    assert updated_data[5] >= boa.env.evm.patch.block_number  # new period start


def test_per_tx_limit(setup_contracts, createManagerData, createManagerLimits):
    """Test per-transaction USD limits"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    data = createManagerData()
    limits = createManagerLimits(
        _maxUsdValuePerTx=1000 * EIGHTEEN_DECIMALS
    )
    
    # Transaction over limit should fail
    with boa.reverts():
        boss.checkManagerUsdLimitsAndUpdateData(
            1001 * EIGHTEEN_DECIMALS,  # Over limit
            limits,
            createManagerLimits(),  # No global limits
            ONE_DAY_IN_BLOCKS,
            data
        )


def test_per_period_limit(setup_contracts, createManagerData, createManagerLimits):
    """Test per-period USD limits"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    # Already used most of period limit
    data = createManagerData(
        _totalUsdValueInPeriod=1900 * EIGHTEEN_DECIMALS,
        _periodStartBlock=boa.env.evm.patch.block_number
    )
    
    limits = createManagerLimits(
        _maxUsdValuePerPeriod=2000 * EIGHTEEN_DECIMALS
    )
    
    # Transaction that would exceed period limit
    with boa.reverts():
        boss.checkManagerUsdLimitsAndUpdateData(
            200 * EIGHTEEN_DECIMALS,  # Would exceed period limit
            limits,
            createManagerLimits(),
            ONE_DAY_IN_BLOCKS,
            data
        )


def test_lifetime_limit(setup_contracts, createManagerData, createManagerLimits):
    """Test lifetime USD limits"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    # Already used most of lifetime limit
    data = createManagerData(
        _totalUsdValue=9900 * EIGHTEEN_DECIMALS
    )
    
    limits = createManagerLimits(
        _maxUsdValueLifetime=10000 * EIGHTEEN_DECIMALS
    )
    
    # Transaction that would exceed lifetime limit
    with boa.reverts():
        boss.checkManagerUsdLimitsAndUpdateData(
            200 * EIGHTEEN_DECIMALS,  # Would exceed lifetime limit
            limits,
            createManagerLimits(),
            ONE_DAY_IN_BLOCKS,
            data
        )


def test_global_limits_override(setup_contracts, createManagerData, createManagerLimits):
    """Test that global limits can be more restrictive than specific limits"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    data = createManagerData()
    
    # Specific limits are generous
    specific_limits = createManagerLimits(
        _maxUsdValuePerTx=1000 * EIGHTEEN_DECIMALS
    )
    
    # Global limits are restrictive
    global_limits = createManagerLimits(
        _maxUsdValuePerTx=500 * EIGHTEEN_DECIMALS
    )
    
    # Should fail on global limit even though specific limit passes
    with boa.reverts():
        boss.checkManagerUsdLimitsAndUpdateData(
            600 * EIGHTEEN_DECIMALS,  # Within specific, over global
            specific_limits,
            global_limits,
            ONE_DAY_IN_BLOCKS,
            data
        )


def test_zero_means_unlimited(setup_contracts, createManagerData, createManagerLimits):
    """Test that zero values mean unlimited"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    data = createManagerData()
    
    # All limits set to 0 (unlimited)
    limits = createManagerLimits()  # All default to 0
    
    # Very large transaction should pass
    updated_data = boss.checkManagerUsdLimitsAndUpdateData(
        1_000_000 * EIGHTEEN_DECIMALS,
        limits,
        limits,
        ONE_DAY_IN_BLOCKS,
        data
    )
    
    assert updated_data[3] == 1_000_000 * EIGHTEEN_DECIMALS


# Test transaction count and cooldown limits


def test_max_txs_per_period(setup_contracts, createManagerData, createManagerLimits):
    """Test that checkManagerUsdLimitsAndUpdateData tracks transaction count but doesn't enforce limits"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    # Already at what would be a max transaction limit
    data = createManagerData(
        _numTxsInPeriod=10,
        _totalNumTxs=10,  # Lifetime count should match period count for this test
        _periodStartBlock=boa.env.evm.patch.block_number
    )
    
    limits = createManagerLimits(
        _maxNumTxsPerPeriod=10  # This limit is NOT enforced by checkManagerUsdLimitsAndUpdateData
    )
    
    # checkManagerUsdLimitsAndUpdateData only checks USD limits, not transaction count
    # It will increment the counter but not enforce the limit
    updated_data = boss.checkManagerUsdLimitsAndUpdateData(
        100 * EIGHTEEN_DECIMALS,
        limits,
        createManagerLimits(),
        ONE_DAY_IN_BLOCKS,
        data
    )
    
    # Verify transaction counter is incremented even though it exceeds maxNumTxsPerPeriod
    assert updated_data[0] == 11  # numTxsInPeriod incremented to 11
    assert updated_data[1] == 100 * EIGHTEEN_DECIMALS  # totalUsdValueInPeriod
    assert updated_data[2] == 11  # totalNumTxs should also be 11 if it started at 10
    assert updated_data[4] == boa.env.evm.patch.block_number  # lastTxBlock updated


def test_tx_cooldown(setup_contracts, createManagerData, createManagerLimits):
    """Test that checkManagerUsdLimitsAndUpdateData updates lastTxBlock but doesn't enforce cooldown"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    current_block = boa.env.evm.patch.block_number
    
    # Recent transaction (only 10 blocks ago)
    data = createManagerData(
        _lastTxBlock=current_block - 10,
        _numTxsInPeriod=5,
        _totalNumTxs=20
    )
    
    limits = createManagerLimits(
        _txCooldownBlocks=100  # This cooldown is NOT enforced by checkManagerUsdLimitsAndUpdateData
    )
    
    # checkManagerUsdLimitsAndUpdateData only checks USD limits, not cooldown
    # It will update lastTxBlock but not enforce the cooldown period
    updated_data = boss.checkManagerUsdLimitsAndUpdateData(
        100 * EIGHTEEN_DECIMALS,
        limits,
        createManagerLimits(),
        ONE_DAY_IN_BLOCKS,
        data
    )
    
    # Verify lastTxBlock is updated even though cooldown period hasn't passed
    assert updated_data[4] == current_block  # lastTxBlock updated to current block
    assert updated_data[0] == 6  # numTxsInPeriod incremented
    assert updated_data[2] == 21  # totalNumTxs incremented


def test_fail_on_zero_price(setup_contracts, createManagerData, createManagerLimits):
    """Test failOnZeroPrice setting"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    data = createManagerData()
    
    # With failOnZeroPrice = true
    limits = createManagerLimits(_failOnZeroPrice=True)
    
    # Zero value transaction should fail
    with boa.reverts():
        boss.checkManagerUsdLimitsAndUpdateData(
            0,  # Zero USD value
            limits,
            createManagerLimits(),
            ONE_DAY_IN_BLOCKS,
            data
        )
    
    # With failOnZeroPrice = false
    limits_no_fail = createManagerLimits(_failOnZeroPrice=False)
    
    # Zero value transaction should pass
    updated_data = boss.checkManagerUsdLimitsAndUpdateData(
        0,
        limits_no_fail,
        createManagerLimits(),
        ONE_DAY_IN_BLOCKS,
        data
    )
    
    assert updated_data[0] == 1  # Transaction counted


# Test validation of limit configurations


def test_validate_manager_limits(setup_contracts, createManagerLimits,
                                createManagerSettings):
    """Test _validateManagerLimits function"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    # Valid limits
    valid_limits = createManagerLimits(
        _maxUsdValuePerTx=100 * EIGHTEEN_DECIMALS,
        _maxUsdValuePerPeriod=1000 * EIGHTEEN_DECIMALS,
        _maxUsdValueLifetime=10000 * EIGHTEEN_DECIMALS,
        _txCooldownBlocks=100
    )
    
    # Test via validateSpecificManagerSettings
    settings = createManagerSettings(_limits=valid_limits)
    assert boss.validateSpecificManagerSettings(
        settings,
        ONE_DAY_IN_BLOCKS,
        False,  # not in eject mode
        ZERO_ADDRESS,  # lego book
        ctx['wallet_config'].address
    )
    
    # Invalid: per-tx > per-period
    invalid_limits1 = createManagerLimits(
        _maxUsdValuePerTx=1000 * EIGHTEEN_DECIMALS,
        _maxUsdValuePerPeriod=100 * EIGHTEEN_DECIMALS
    )
    
    settings_invalid1 = createManagerSettings(_limits=invalid_limits1)
    assert not boss.validateSpecificManagerSettings(
        settings_invalid1,
        ONE_DAY_IN_BLOCKS,
        False,
        ZERO_ADDRESS,
        ctx['wallet_config'].address
    )
    
    # Invalid: per-period > lifetime
    invalid_limits2 = createManagerLimits(
        _maxUsdValuePerPeriod=1000 * EIGHTEEN_DECIMALS,
        _maxUsdValueLifetime=100 * EIGHTEEN_DECIMALS
    )
    
    settings_invalid2 = createManagerSettings(_limits=invalid_limits2)
    assert not boss.validateSpecificManagerSettings(
        settings_invalid2,
        ONE_DAY_IN_BLOCKS,
        False,
        ZERO_ADDRESS,
        ctx['wallet_config'].address
    )
    
    # Invalid: cooldown > period
    invalid_limits3 = createManagerLimits(
        _txCooldownBlocks=ONE_DAY_IN_BLOCKS + 1
    )
    
    settings_invalid3 = createManagerSettings(_limits=invalid_limits3)
    assert not boss.validateSpecificManagerSettings(
        settings_invalid3,
        ONE_DAY_IN_BLOCKS,
        False,
        ZERO_ADDRESS,
        ctx['wallet_config'].address
    )