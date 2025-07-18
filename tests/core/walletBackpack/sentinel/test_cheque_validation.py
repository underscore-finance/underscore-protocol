import boa
import pytest

from constants import EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ONE_MONTH_IN_BLOCKS, ZERO_ADDRESS

ONE_WEEK_IN_BLOCKS = ONE_DAY_IN_BLOCKS * 7
ONE_HOUR_IN_BLOCKS = ONE_DAY_IN_BLOCKS // 24


#################################################
# isValidChequeAndGetData() - Basic Validation #
#################################################


def test_isValidChequeAndGetData_fails_when_cheque_not_active(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that inactive cheques are rejected"""
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _active=False  # INVALID: cheque is not active
    )
    global_config = createChequeSettings(
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData()
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,  # _asset
        100 * EIGHTEEN_DECIMALS,  # _amount
        100 * EIGHTEEN_DECIMALS,  # _txUsdValue
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    assert is_valid == False


def test_isValidChequeAndGetData_fails_when_before_unlock_block(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that cheques cannot be used before unlock block"""
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _creationBlock=current_block,
        _unlockBlock=current_block + 100,  # Unlocks in future
        _expiryBlock=current_block + 1000,
        _active=True
    )
    global_config = createChequeSettings(
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData()
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    assert is_valid == False


def test_isValidChequeAndGetData_fails_when_after_expiry_block(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that cheques cannot be used after expiry block"""
    # Advance blocks to ensure we have room
    boa.env.time_travel(blocks=200)
    
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _creationBlock=current_block - 100,
        _unlockBlock=current_block - 50,
        _expiryBlock=current_block - 1,  # Already expired
        _active=True
    )
    global_config = createChequeSettings(
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData()
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    assert is_valid == False


def test_isValidChequeAndGetData_succeeds_within_valid_time_window(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that cheques are valid within unlock and expiry window"""
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _creationBlock=current_block,
        _unlockBlock=current_block,  # Already unlocked
        _expiryBlock=current_block + 1000,  # Not expired yet
        _active=True
    )
    global_config = createChequeSettings(
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData()
    
    is_valid, updated_data = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    assert is_valid == True
    # Verify cheque data was updated
    assert updated_data.lastChequePaidBlock == current_block
    assert updated_data.numChequesPaidInPeriod == 1
    assert updated_data.totalUsdValuePaidInPeriod == 100 * EIGHTEEN_DECIMALS


def test_isValidChequeAndGetData_fails_with_zero_recipient(
    sentinel, createCheque, createChequeSettings, createChequeData, alpha_token
):
    """Test that cheques with zero address recipient are rejected"""
    cheque = createCheque(
        _recipient=ZERO_ADDRESS,  # INVALID: zero address
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _active=True
    )
    global_config = createChequeSettings(
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData()
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    assert is_valid == False


def test_isValidChequeAndGetData_fails_with_zero_asset(
    sentinel, createCheque, createChequeSettings, createChequeData, alice
):
    """Test that cheques with zero address asset are rejected"""
    cheque = createCheque(
        _recipient=alice,
        _asset=ZERO_ADDRESS,  # INVALID: zero address
        _amount=100 * EIGHTEEN_DECIMALS,
        _active=True
    )
    global_config = createChequeSettings(
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData()
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        ZERO_ADDRESS,  # Must match cheque asset
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    assert is_valid == False


def test_isValidChequeAndGetData_fails_when_asset_mismatch(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token, bravo_token
):
    """Test that provided asset must match cheque asset"""
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _active=True
    )
    global_config = createChequeSettings(
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData()
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        bravo_token.address,  # INVALID: different asset
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    assert is_valid == False


def test_isValidChequeAndGetData_fails_when_amount_mismatch(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that provided amount must exactly match cheque amount"""
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _active=True
    )
    global_config = createChequeSettings(
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData()
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        99 * EIGHTEEN_DECIMALS,  # INVALID: different amount
        99 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    assert is_valid == False


def test_isValidChequeAndGetData_fails_when_asset_not_allowed(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token, bravo_token
):
    """Test that cheques are rejected when asset is not in allowed list"""
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _active=True
    )
    global_config = createChequeSettings(
        _allowedAssets=[bravo_token.address],  # Only bravo allowed
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData()
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,  # Not in allowed list
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    assert is_valid == False


def test_isValidChequeAndGetData_succeeds_when_asset_allowed(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that cheques are accepted when asset is in allowed list"""
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block,  # Already unlocked
        _active=True
    )
    global_config = createChequeSettings(
        _allowedAssets=[alpha_token.address],  # Alpha is allowed
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData()
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    assert is_valid == True


def test_isValidChequeAndGetData_succeeds_with_empty_allowed_assets(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that empty allowed assets list means all assets are allowed"""
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block,  # Already unlocked
        _active=True
    )
    global_config = createChequeSettings(
        _allowedAssets=[],  # Empty means all allowed
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData()
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    assert is_valid == True


def test_isValidChequeAndGetData_fails_with_zero_usd_value(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that cheques with zero USD value are rejected"""
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _active=True
    )
    global_config = createChequeSettings(
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData()
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        0,  # INVALID: zero USD value
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    assert is_valid == False


def test_isValidChequeAndGetData_fails_when_exceeds_max_cheque_usd_value(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that cheques exceeding max USD value are rejected"""
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _active=True
    )
    global_config = createChequeSettings(
        _maxChequeUsdValue=50 * EIGHTEEN_DECIMALS,  # Max 50 USD
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData()
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,  # INVALID: exceeds max
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    assert is_valid == False


def test_isValidChequeAndGetData_succeeds_at_max_cheque_usd_value(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that cheques at exactly max USD value are accepted"""
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block,  # Already unlocked
        _active=True
    )
    global_config = createChequeSettings(
        _maxChequeUsdValue=100 * EIGHTEEN_DECIMALS,  # Max 100 USD
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData()
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,  # VALID: at max
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    assert is_valid == True


def test_isValidChequeAndGetData_succeeds_with_zero_max_cheque_usd_value(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that zero max USD value means unlimited"""
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block,  # Already unlocked
        _active=True
    )
    global_config = createChequeSettings(
        _maxChequeUsdValue=0,  # Zero means unlimited
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData()
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        1000000 * EIGHTEEN_DECIMALS,  # Very large value, still valid
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    assert is_valid == True


def test_isValidChequeAndGetData_manager_fails_without_global_permission(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that managers cannot pay when globally disabled"""
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _canManagerPay=True,  # Cheque allows manager pay
        _active=True
    )
    global_config = createChequeSettings(
        _canManagerPay=False,  # INVALID: globally disabled
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData()
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        True  # _isManager
    )
    assert is_valid == False


def test_isValidChequeAndGetData_manager_fails_without_cheque_permission(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that managers cannot pay when cheque doesn't allow it"""
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _canManagerPay=False,  # INVALID: cheque doesn't allow
        _active=True
    )
    global_config = createChequeSettings(
        _canManagerPay=True,  # Globally enabled
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData()
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        True  # _isManager
    )
    assert is_valid == False


def test_isValidChequeAndGetData_manager_succeeds_with_both_permissions(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that managers can pay when both permissions are enabled"""
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block,  # Already unlocked
        _canManagerPay=True,  # Cheque allows
        _active=True
    )
    global_config = createChequeSettings(
        _canManagerPay=True,  # Globally enabled
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData()
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        True  # _isManager
    )
    assert is_valid == True


def test_isValidChequeAndGetData_non_manager_ignores_manager_permissions(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that non-managers are not affected by manager permissions"""
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block,  # Already unlocked
        _canManagerPay=False,  # Doesn't matter for non-manager
        _active=True
    )
    global_config = createChequeSettings(
        _canManagerPay=False,  # Doesn't matter for non-manager
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData()
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False  # _isManager (not a manager)
    )
    assert is_valid == True


def test_isValidChequeAndGetData_fails_within_pay_cooldown(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that cheques cannot be paid within cooldown period"""
    # Advance blocks to ensure we can subtract safely
    boa.env.time_travel(blocks=200)
    
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block,  # Already unlocked
        _active=True
    )
    global_config = createChequeSettings(
        _payCooldownBlocks=100,  # 100 blocks cooldown
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData(
        _lastChequePaidBlock=current_block - 50  # Paid 50 blocks ago
    )
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    assert is_valid == False


def test_isValidChequeAndGetData_succeeds_after_pay_cooldown(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that cheques can be paid after cooldown period"""
    # Advance blocks to ensure positive block numbers
    boa.env.time_travel(blocks=200)
    
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block,  # Already unlocked
        _active=True
    )
    global_config = createChequeSettings(
        _payCooldownBlocks=100,  # 100 blocks cooldown
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData(
        _lastChequePaidBlock=current_block - 101  # Paid 101 blocks ago
    )
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    assert is_valid == True


def test_isValidChequeAndGetData_succeeds_with_zero_pay_cooldown(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that zero cooldown means no cooldown"""
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block,  # Already unlocked
        _active=True
    )
    global_config = createChequeSettings(
        _payCooldownBlocks=0,  # No cooldown
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData(
        _lastChequePaidBlock=current_block  # Paid this block
    )
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    assert is_valid == True


def test_isValidChequeAndGetData_fails_when_exceeds_max_cheques_per_period(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that cheques are rejected when period limit is reached"""
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block,  # Already unlocked
        _active=True
    )
    global_config = createChequeSettings(
        _maxNumChequesPaidPerPeriod=5,  # Max 5 per period
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData(
        _numChequesPaidInPeriod=5  # Already at limit
    )
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    assert is_valid == False


def test_isValidChequeAndGetData_succeeds_below_max_cheques_per_period(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that cheques are accepted when below period limit"""
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block,  # Already unlocked
        _active=True
    )
    global_config = createChequeSettings(
        _maxNumChequesPaidPerPeriod=5,  # Max 5 per period
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData(
        _numChequesPaidInPeriod=4  # Below limit
    )
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    assert is_valid == True


def test_isValidChequeAndGetData_succeeds_with_zero_max_cheques_per_period(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that zero max cheques per period means unlimited"""
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block,  # Already unlocked
        _active=True
    )
    global_config = createChequeSettings(
        _maxNumChequesPaidPerPeriod=0,  # Zero means unlimited
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData(
        _numChequesPaidInPeriod=1000  # Very high number
    )
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    assert is_valid == True


def test_isValidChequeAndGetData_fails_when_exceeds_period_usd_cap(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that cheques are rejected when period USD cap would be exceeded"""
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block,  # Already unlocked
        _active=True
    )
    global_config = createChequeSettings(
        _perPeriodPaidUsdCap=500 * EIGHTEEN_DECIMALS,  # Max 500 USD per period
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData(
        _totalUsdValuePaidInPeriod=450 * EIGHTEEN_DECIMALS  # Already 450 USD
    )
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,  # Would exceed cap (450 + 100 > 500)
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    assert is_valid == False


def test_isValidChequeAndGetData_succeeds_at_exactly_period_usd_cap(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that cheques are accepted when exactly at period USD cap"""
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block,  # Already unlocked
        _active=True
    )
    global_config = createChequeSettings(
        _perPeriodPaidUsdCap=500 * EIGHTEEN_DECIMALS,  # Max 500 USD per period
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData(
        _totalUsdValuePaidInPeriod=400 * EIGHTEEN_DECIMALS  # Already 400 USD
    )
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,  # Exactly at cap (400 + 100 = 500)
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    assert is_valid == True


def test_isValidChequeAndGetData_succeeds_with_zero_period_usd_cap(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that zero period USD cap means unlimited"""
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block,  # Already unlocked
        _active=True
    )
    global_config = createChequeSettings(
        _perPeriodPaidUsdCap=0,  # Zero means unlimited
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData(
        _totalUsdValuePaidInPeriod=1000000 * EIGHTEEN_DECIMALS  # Very high amount
    )
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    assert is_valid == True


def test_isValidChequeAndGetData_updates_cheque_data_correctly(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that cheque data is updated correctly when validation passes"""
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block,  # Already unlocked
        _active=True
    )
    global_config = createChequeSettings(
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData(
        _numChequesPaidInPeriod=2,
        _totalUsdValuePaidInPeriod=200 * EIGHTEEN_DECIMALS,
        _totalNumChequesPaid=10,
        _totalUsdValuePaid=1000 * EIGHTEEN_DECIMALS
    )
    
    is_valid, updated_data = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    
    assert is_valid == True
    # Verify all updates
    assert updated_data.lastChequePaidBlock == current_block
    assert updated_data.numChequesPaidInPeriod == 3  # Incremented
    assert updated_data.totalUsdValuePaidInPeriod == 300 * EIGHTEEN_DECIMALS  # Added 100
    assert updated_data.totalNumChequesPaid == 11  # Incremented
    assert updated_data.totalUsdValuePaid == 1100 * EIGHTEEN_DECIMALS  # Added 100


def test_isValidChequeAndGetData_complex_scenario_all_conditions(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test complex scenario with multiple conditions"""
    # Advance blocks for realistic scenario
    boa.env.time_travel(blocks=1000)
    
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _creationBlock=current_block - 500,
        _unlockBlock=current_block - 100,
        _expiryBlock=current_block + 100,
        _canManagerPay=True,
        _active=True
    )
    
    global_config = createChequeSettings(
        _maxNumActiveCheques=10,
        _maxChequeUsdValue=200 * EIGHTEEN_DECIMALS,
        _perPeriodPaidUsdCap=1000 * EIGHTEEN_DECIMALS,
        _maxNumChequesPaidPerPeriod=10,
        _payCooldownBlocks=50,
        _allowedAssets=[alpha_token.address],
        _canManagerPay=True,
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    
    cheque_data = createChequeData(
        _numChequesPaidInPeriod=5,
        _totalUsdValuePaidInPeriod=500 * EIGHTEEN_DECIMALS,
        _lastChequePaidBlock=current_block - 100
    )
    
    # Test as manager
    is_valid, updated_data = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        True  # _isManager
    )
    
    assert is_valid == True
    assert updated_data.numChequesPaidInPeriod == 6
    assert updated_data.totalUsdValuePaidInPeriod == 600 * EIGHTEEN_DECIMALS


def test_isValidChequeAndGetData_edge_case_at_all_limits(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test edge case where all limits are at maximum allowed values"""
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block,  # Already unlocked
        _active=True
    )
    
    global_config = createChequeSettings(
        _maxChequeUsdValue=100 * EIGHTEEN_DECIMALS,  # Exactly at limit
        _perPeriodPaidUsdCap=100 * EIGHTEEN_DECIMALS,  # Exactly at limit
        _maxNumChequesPaidPerPeriod=1,  # Exactly at limit
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    
    cheque_data = createChequeData(
        _numChequesPaidInPeriod=0,  # Will be at limit after this
        _totalUsdValuePaidInPeriod=0  # Will be at limit after this
    )
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    
    assert is_valid == True


def test_isValidChequeAndGetData_multiple_failures(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token, bravo_token
):
    """Test that function fails fast on first validation error"""
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _active=False  # First failure point
    )
    
    global_config = createChequeSettings(
        _allowedAssets=[bravo_token.address],  # Would also fail
        _maxChequeUsdValue=50 * EIGHTEEN_DECIMALS,  # Would also fail
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    
    cheque_data = createChequeData(
        _numChequesPaidInPeriod=100  # Would also fail if limits were set
    )
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False  # _isManager
    )
    
    assert is_valid == False  # Fails on first check (not active)


def test_isValidChequeAndGetData_recipient_equals_zero_address(
    sentinel, createCheque, createChequeSettings, createChequeData, alpha_token
):
    """Test explicit check for recipient being zero address"""
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=ZERO_ADDRESS,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block,
        _active=True
    )
    global_config = createChequeSettings(_periodLength=ONE_MONTH_IN_BLOCKS)
    cheque_data = createChequeData()
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False
    )
    
    assert is_valid == False


def test_isValidChequeAndGetData_asset_equals_zero_address(
    sentinel, createCheque, createChequeSettings, createChequeData, alice
):
    """Test explicit check for asset being zero address"""
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=ZERO_ADDRESS,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block,
        _active=True
    )
    global_config = createChequeSettings(_periodLength=ONE_MONTH_IN_BLOCKS)
    cheque_data = createChequeData()
    
    # Must pass ZERO_ADDRESS as asset to match cheque
    is_valid, _ = sentinel.isValidChequeAndGetData(
        ZERO_ADDRESS,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False
    )
    
    assert is_valid == False


def test_isValidChequeAndGetData_manager_with_only_global_permission_disabled(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test manager when only global permission is disabled (cheque allows)"""
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block,
        _canManagerPay=True,  # Cheque allows
        _active=True
    )
    global_config = createChequeSettings(
        _canManagerPay=False,  # Global disallows
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData()
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        True  # _isManager
    )
    
    # Should fail because BOTH permissions are required
    assert is_valid == False


def test_isValidChequeAndGetData_manager_with_only_cheque_permission_disabled(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test manager when only cheque permission is disabled (global allows)"""
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block,
        _canManagerPay=False,  # Cheque disallows
        _active=True
    )
    global_config = createChequeSettings(
        _canManagerPay=True,  # Global allows
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData()
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        True  # _isManager
    )
    
    # Should fail because BOTH permissions are required
    assert is_valid == False


def test_isValidChequeAndGetData_first_cheque_initializes_period(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that first cheque initializes period start block"""
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block,
        _active=True
    )
    global_config = createChequeSettings(
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    # Explicitly set periodStartBlock to 0 to simulate first cheque
    cheque_data = createChequeData(
        _periodStartBlock=0
    )
    
    is_valid, updated_data = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False
    )
    
    assert is_valid == True
    # Verify period was initialized
    assert updated_data.periodStartBlock == current_block
    assert updated_data.numChequesPaidInPeriod == 1
    assert updated_data.totalUsdValuePaidInPeriod == 100 * EIGHTEEN_DECIMALS


def test_isValidChequeAndGetData_period_reset_after_expiry(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that period data resets when period expires"""
    # Advance blocks to ensure we have room for period calculations
    boa.env.time_travel(blocks=ONE_MONTH_IN_BLOCKS + 1000)
    
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block,
        _active=True
    )
    global_config = createChequeSettings(
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    # Set up data from a previous period that should be reset
    cheque_data = createChequeData(
        _numChequesPaidInPeriod=5,
        _totalUsdValuePaidInPeriod=500 * EIGHTEEN_DECIMALS,
        _numChequesCreatedInPeriod=10,
        _totalUsdValueCreatedInPeriod=1000 * EIGHTEEN_DECIMALS,
        _periodStartBlock=current_block - ONE_MONTH_IN_BLOCKS - 1  # Period has expired
    )
    
    is_valid, updated_data = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False
    )
    
    assert is_valid == True
    # Verify period was reset
    assert updated_data.periodStartBlock == current_block
    assert updated_data.numChequesPaidInPeriod == 1  # Reset to 1 (current cheque)
    assert updated_data.totalUsdValuePaidInPeriod == 100 * EIGHTEEN_DECIMALS  # Reset
    # These should also be reset even though not used in validation
    assert updated_data.numChequesCreatedInPeriod == 0
    assert updated_data.totalUsdValueCreatedInPeriod == 0


def test_isValidChequeAndGetData_zero_period_length_no_reset(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test that zero period length means no period reset"""
    # Advance blocks
    boa.env.time_travel(blocks=10000)
    
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block,
        _active=True
    )
    global_config = createChequeSettings(
        _periodLength=0  # Zero means no period reset
    )
    # Set up old data that would normally trigger reset
    cheque_data = createChequeData(
        _numChequesPaidInPeriod=5,
        _totalUsdValuePaidInPeriod=500 * EIGHTEEN_DECIMALS,
        _periodStartBlock=100  # Very old
    )
    
    is_valid, updated_data = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False
    )
    
    assert is_valid == True
    # Verify NO period reset occurred
    assert updated_data.periodStartBlock == 100  # Unchanged
    assert updated_data.numChequesPaidInPeriod == 6  # Just incremented
    assert updated_data.totalUsdValuePaidInPeriod == 600 * EIGHTEEN_DECIMALS


def test_isValidChequeAndGetData_cooldown_with_zero_last_paid_block(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test cooldown check when no cheque has been paid before (lastChequePaidBlock = 0)"""
    # Advance blocks to ensure current block > cooldown period
    boa.env.time_travel(blocks=200)
    
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block,
        _active=True
    )
    global_config = createChequeSettings(
        _payCooldownBlocks=100,  # Cooldown enabled
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData(
        _lastChequePaidBlock=0  # No previous cheque paid
    )
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False
    )
    
    # Should succeed because lastChequePaidBlock + cooldown = 0 + 100 = 100
    # and current block is now > 100 due to time travel
    assert is_valid == True


def test_isValidChequeAndGetData_expiry_at_exact_current_block(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test cheque that expires at exactly the current block"""
    # Advance blocks
    boa.env.time_travel(blocks=100)
    
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block - 50,
        _expiryBlock=current_block,  # Expires exactly now
        _active=True
    )
    global_config = createChequeSettings(
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    cheque_data = createChequeData()
    
    is_valid, _ = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False
    )
    
    # Should fail because check is >= (expires at current block)
    assert is_valid == False


def test_isValidChequeAndGetData_period_boundary_exact(
    sentinel, createCheque, createChequeSettings, createChequeData, alice, alpha_token
):
    """Test at exact period boundary"""
    # Advance blocks
    boa.env.time_travel(blocks=ONE_MONTH_IN_BLOCKS + 100)
    
    current_block = boa.env.evm.patch.block_number
    cheque = createCheque(
        _recipient=alice,
        _asset=alpha_token.address,
        _amount=100 * EIGHTEEN_DECIMALS,
        _unlockBlock=current_block,
        _active=True
    )
    global_config = createChequeSettings(
        _periodLength=ONE_MONTH_IN_BLOCKS
    )
    # Period ends exactly at current block
    cheque_data = createChequeData(
        _numChequesPaidInPeriod=5,
        _totalUsdValuePaidInPeriod=500 * EIGHTEEN_DECIMALS,
        _periodStartBlock=current_block - ONE_MONTH_IN_BLOCKS  # Exact boundary
    )
    
    is_valid, updated_data = sentinel.isValidChequeAndGetData(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        cheque,
        global_config,
        cheque_data,
        False
    )
    
    assert is_valid == True
    # Should reset because current >= start + period
    assert updated_data.periodStartBlock == current_block
    assert updated_data.numChequesPaidInPeriod == 1
