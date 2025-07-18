import boa
import pytest

from constants import EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ONE_MONTH_IN_BLOCKS, ZERO_ADDRESS

# Define additional time constants
ONE_WEEK_IN_BLOCKS = ONE_DAY_IN_BLOCKS * 7
ONE_HOUR_IN_BLOCKS = ONE_DAY_IN_BLOCKS // 24


################################
# Cheque Settings - Validation #
################################


def test_isValidChequeSettings_with_valid_settings(
    paymaster
):
    """Test that isValidChequeSettings returns True for valid settings"""
    is_valid = paymaster.isValidChequeSettings(
        10,  # _maxNumActiveCheques
        1000 * EIGHTEEN_DECIMALS,  # _maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # _instantUsdThreshold (must be non-zero)
        5000 * EIGHTEEN_DECIMALS,  # _perPeriodPaidUsdCap
        50,  # _maxNumChequesPaidPerPeriod
        ONE_HOUR_IN_BLOCKS,  # _payCooldownBlocks
        10000 * EIGHTEEN_DECIMALS,  # _perPeriodCreatedUsdCap
        100,  # _maxNumChequesCreatedPerPeriod
        ONE_HOUR_IN_BLOCKS,  # _createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # _periodLength
        ONE_DAY_IN_BLOCKS,  # _expensiveDelayBlocks (required when instant threshold is set)
        ONE_WEEK_IN_BLOCKS,  # _defaultExpiryBlocks
        ONE_DAY_IN_BLOCKS,  # _timeLock
    )
    assert is_valid == True


def test_isValidChequeSettings_with_valid_default_settings(
    paymaster
):
    """Test that isValidChequeSettings returns True for zero values (defaults)"""
    # Zero values should be valid for most fields
    is_valid = paymaster.isValidChequeSettings(
        0,  # _maxNumActiveCheques (0 = unlimited)
        0,  # _maxChequeUsdValue (0 = unlimited)
        100 * EIGHTEEN_DECIMALS,  # _instantUsdThreshold (must be non-zero)
        0,  # _perPeriodPaidUsdCap (0 = unlimited)
        0,  # _maxNumChequesPaidPerPeriod (0 = unlimited)
        0,  # _payCooldownBlocks (0 = no cooldown)
        0,  # _perPeriodCreatedUsdCap (0 = unlimited)
        0,  # _maxNumChequesCreatedPerPeriod (0 = unlimited)
        0,  # _createCooldownBlocks (0 = no cooldown)
        ONE_MONTH_IN_BLOCKS,  # _periodLength (must be valid)
        ONE_DAY_IN_BLOCKS,  # _expensiveDelayBlocks (required when instant threshold is set)
        0,  # _defaultExpiryBlocks (0 = use timelock)
        ONE_DAY_IN_BLOCKS,  # _timeLock
    )
    assert is_valid == True


def test_isValidChequeSettings_fails_with_zero_period_length(
    paymaster
):
    """Test that zero period length is invalid"""
    is_valid = paymaster.isValidChequeSettings(
        0,  # _maxNumActiveCheques
        0,  # _maxChequeUsdValue
        0,  # _instantUsdThreshold
        0,  # _perPeriodPaidUsdCap
        0,  # _maxNumChequesPaidPerPeriod
        0,  # _payCooldownBlocks
        0,  # _perPeriodCreatedUsdCap
        0,  # _maxNumChequesCreatedPerPeriod
        0,  # _createCooldownBlocks
        0,  # _periodLength (INVALID: must be non-zero)
        0,  # _expensiveDelayBlocks
        0,  # _defaultExpiryBlocks
        ONE_DAY_IN_BLOCKS,  # _timeLock
    )
    assert is_valid == False


def test_isValidChequeSettings_fails_with_period_below_minimum(
    paymaster
):
    """Test that period below minimum is invalid"""
    min_period = paymaster.MIN_CHEQUE_PERIOD()
    is_valid = paymaster.isValidChequeSettings(
        0,  # _maxNumActiveCheques
        0,  # _maxChequeUsdValue
        0,  # _instantUsdThreshold
        0,  # _perPeriodPaidUsdCap
        0,  # _maxNumChequesPaidPerPeriod
        0,  # _payCooldownBlocks
        0,  # _perPeriodCreatedUsdCap
        0,  # _maxNumChequesCreatedPerPeriod
        0,  # _createCooldownBlocks
        min_period - 1,  # _periodLength (INVALID: below minimum)
        0,  # _expensiveDelayBlocks
        0,  # _defaultExpiryBlocks
        ONE_DAY_IN_BLOCKS,  # _timeLock
    )
    assert is_valid == False


def test_isValidChequeSettings_fails_with_period_above_maximum(
    paymaster
):
    """Test that period above maximum is invalid"""
    max_period = paymaster.MAX_CHEQUE_PERIOD()
    is_valid = paymaster.isValidChequeSettings(
        0,  # _maxNumActiveCheques
        0,  # _maxChequeUsdValue
        0,  # _instantUsdThreshold
        0,  # _perPeriodPaidUsdCap
        0,  # _maxNumChequesPaidPerPeriod
        0,  # _payCooldownBlocks
        0,  # _perPeriodCreatedUsdCap
        0,  # _maxNumChequesCreatedPerPeriod
        0,  # _createCooldownBlocks
        max_period + 1,  # _periodLength (INVALID: above maximum)
        0,  # _expensiveDelayBlocks
        0,  # _defaultExpiryBlocks
        ONE_DAY_IN_BLOCKS,  # _timeLock
    )
    assert is_valid == False


def test_isValidChequeSettings_succeeds_with_period_at_minimum(
    paymaster
):
    """Test that period at minimum is valid"""
    min_period = paymaster.MIN_CHEQUE_PERIOD()
    is_valid = paymaster.isValidChequeSettings(
        0,  # _maxNumActiveCheques
        0,  # _maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # _instantUsdThreshold (must be non-zero)
        0,  # _perPeriodPaidUsdCap
        0,  # _maxNumChequesPaidPerPeriod
        0,  # _payCooldownBlocks
        0,  # _perPeriodCreatedUsdCap
        0,  # _maxNumChequesCreatedPerPeriod
        0,  # _createCooldownBlocks
        min_period,  # _periodLength (VALID: at minimum)
        ONE_DAY_IN_BLOCKS,  # _expensiveDelayBlocks (required when instant threshold is set)
        0,  # _defaultExpiryBlocks
        ONE_DAY_IN_BLOCKS,  # _timeLock
    )
    assert is_valid == True


def test_isValidChequeSettings_succeeds_with_period_at_maximum(
    paymaster
):
    """Test that period at maximum is valid"""
    max_period = paymaster.MAX_CHEQUE_PERIOD()
    is_valid = paymaster.isValidChequeSettings(
        0,  # _maxNumActiveCheques
        0,  # _maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # _instantUsdThreshold (must be non-zero)
        0,  # _perPeriodPaidUsdCap
        0,  # _maxNumChequesPaidPerPeriod
        0,  # _payCooldownBlocks
        0,  # _perPeriodCreatedUsdCap
        0,  # _maxNumChequesCreatedPerPeriod
        0,  # _createCooldownBlocks
        max_period,  # _periodLength (VALID: at maximum)
        ONE_DAY_IN_BLOCKS,  # _expensiveDelayBlocks (required when instant threshold is set)
        0,  # _defaultExpiryBlocks
        ONE_DAY_IN_BLOCKS,  # _timeLock
    )
    assert is_valid == True


def test_isValidChequeSettings_fails_when_pay_cooldown_exceeds_period(
    paymaster
):
    """Test that pay cooldown cannot exceed period length"""
    period = ONE_WEEK_IN_BLOCKS
    is_valid = paymaster.isValidChequeSettings(
        0,  # _maxNumActiveCheques
        0,  # _maxChequeUsdValue
        0,  # _instantUsdThreshold
        0,  # _perPeriodPaidUsdCap
        0,  # _maxNumChequesPaidPerPeriod
        period + 1,  # _payCooldownBlocks (INVALID: exceeds period)
        0,  # _perPeriodCreatedUsdCap
        0,  # _maxNumChequesCreatedPerPeriod
        0,  # _createCooldownBlocks
        period,  # _periodLength
        0,  # _expensiveDelayBlocks
        0,  # _defaultExpiryBlocks
        ONE_DAY_IN_BLOCKS,  # _timeLock
    )
    assert is_valid == False


def test_isValidChequeSettings_fails_when_create_cooldown_exceeds_period(
    paymaster
):
    """Test that create cooldown cannot exceed period length"""
    period = ONE_WEEK_IN_BLOCKS
    is_valid = paymaster.isValidChequeSettings(
        0,  # _maxNumActiveCheques
        0,  # _maxChequeUsdValue
        0,  # _instantUsdThreshold
        0,  # _perPeriodPaidUsdCap
        0,  # _maxNumChequesPaidPerPeriod
        0,  # _payCooldownBlocks
        0,  # _perPeriodCreatedUsdCap
        0,  # _maxNumChequesCreatedPerPeriod
        period + 1,  # _createCooldownBlocks (INVALID: exceeds period)
        period,  # _periodLength
        0,  # _expensiveDelayBlocks
        0,  # _defaultExpiryBlocks
        ONE_DAY_IN_BLOCKS,  # _timeLock
    )
    assert is_valid == False


def test_isValidChequeSettings_succeeds_with_cooldowns_equal_to_period(
    paymaster
):
    """Test that cooldowns equal to period length are valid"""
    period = ONE_WEEK_IN_BLOCKS
    is_valid = paymaster.isValidChequeSettings(
        0,  # _maxNumActiveCheques
        0,  # _maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # _instantUsdThreshold (must be non-zero)
        0,  # _perPeriodPaidUsdCap
        0,  # _maxNumChequesPaidPerPeriod
        period,  # _payCooldownBlocks (VALID: equal to period)
        0,  # _perPeriodCreatedUsdCap
        0,  # _maxNumChequesCreatedPerPeriod
        period,  # _createCooldownBlocks (VALID: equal to period)
        period,  # _periodLength
        ONE_DAY_IN_BLOCKS,  # _expensiveDelayBlocks (required when instant threshold is set)
        0,  # _defaultExpiryBlocks
        ONE_DAY_IN_BLOCKS,  # _timeLock
    )
    assert is_valid == True


def test_isValidChequeSettings_fails_when_period_cap_less_than_max_cheque(
    paymaster
):
    """Test that period USD cap cannot be less than max cheque value"""
    is_valid = paymaster.isValidChequeSettings(
        0,  # _maxNumActiveCheques
        1000 * EIGHTEEN_DECIMALS,  # _maxChequeUsdValue
        0,  # _instantUsdThreshold
        500 * EIGHTEEN_DECIMALS,  # _perPeriodPaidUsdCap (INVALID: less than max cheque)
        0,  # _maxNumChequesPaidPerPeriod
        0,  # _payCooldownBlocks
        0,  # _perPeriodCreatedUsdCap
        0,  # _maxNumChequesCreatedPerPeriod
        0,  # _createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # _periodLength
        0,  # _expensiveDelayBlocks
        0,  # _defaultExpiryBlocks
        ONE_DAY_IN_BLOCKS,  # _timeLock
    )
    assert is_valid == False


def test_isValidChequeSettings_fails_when_created_cap_less_than_max_cheque(
    paymaster
):
    """Test that created USD cap cannot be less than max cheque value"""
    is_valid = paymaster.isValidChequeSettings(
        0,  # _maxNumActiveCheques
        1000 * EIGHTEEN_DECIMALS,  # _maxChequeUsdValue
        0,  # _instantUsdThreshold
        0,  # _perPeriodPaidUsdCap
        0,  # _maxNumChequesPaidPerPeriod
        0,  # _payCooldownBlocks
        500 * EIGHTEEN_DECIMALS,  # _perPeriodCreatedUsdCap (INVALID: less than max cheque)
        0,  # _maxNumChequesCreatedPerPeriod
        0,  # _createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # _periodLength
        0,  # _expensiveDelayBlocks
        0,  # _defaultExpiryBlocks
        ONE_DAY_IN_BLOCKS,  # _timeLock
    )
    assert is_valid == False


def test_isValidChequeSettings_succeeds_when_caps_equal_max_cheque(
    paymaster
):
    """Test that USD caps equal to max cheque value are valid"""
    max_cheque = 1000 * EIGHTEEN_DECIMALS
    is_valid = paymaster.isValidChequeSettings(
        0,  # _maxNumActiveCheques
        max_cheque,  # _maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # _instantUsdThreshold (must be non-zero)
        max_cheque,  # _perPeriodPaidUsdCap (VALID: equal to max cheque)
        0,  # _maxNumChequesPaidPerPeriod
        0,  # _payCooldownBlocks
        max_cheque,  # _perPeriodCreatedUsdCap (VALID: equal to max cheque)
        0,  # _maxNumChequesCreatedPerPeriod
        0,  # _createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # _periodLength
        ONE_DAY_IN_BLOCKS,  # _expensiveDelayBlocks (required when instant threshold is set)
        0,  # _defaultExpiryBlocks
        ONE_DAY_IN_BLOCKS,  # _timeLock
    )
    assert is_valid == True


def test_isValidChequeSettings_succeeds_with_zero_caps_and_max_cheque(
    paymaster
):
    """Test that zero USD caps mean unlimited even with max cheque set"""
    is_valid = paymaster.isValidChequeSettings(
        0,  # _maxNumActiveCheques
        1000 * EIGHTEEN_DECIMALS,  # _maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # _instantUsdThreshold (must be non-zero)
        0,  # _perPeriodPaidUsdCap (VALID: 0 = unlimited)
        0,  # _maxNumChequesPaidPerPeriod
        0,  # _payCooldownBlocks
        0,  # _perPeriodCreatedUsdCap (VALID: 0 = unlimited)
        0,  # _maxNumChequesCreatedPerPeriod
        0,  # _createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # _periodLength
        ONE_DAY_IN_BLOCKS,  # _expensiveDelayBlocks (required when instant threshold is set)
        0,  # _defaultExpiryBlocks
        ONE_DAY_IN_BLOCKS,  # _timeLock
    )
    assert is_valid == True


def test_isValidChequeSettings_fails_with_instant_threshold_but_no_delay(
    paymaster
):
    """Test that instant threshold requires expensive delay blocks"""
    is_valid = paymaster.isValidChequeSettings(
        0,  # _maxNumActiveCheques
        0,  # _maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # _instantUsdThreshold (set)
        0,  # _perPeriodPaidUsdCap
        0,  # _maxNumChequesPaidPerPeriod
        0,  # _payCooldownBlocks
        0,  # _perPeriodCreatedUsdCap
        0,  # _maxNumChequesCreatedPerPeriod
        0,  # _createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # _periodLength
        0,  # _expensiveDelayBlocks (INVALID: must be set when instant threshold is set)
        0,  # _defaultExpiryBlocks
        ONE_DAY_IN_BLOCKS,  # _timeLock
    )
    assert is_valid == False


def test_isValidChequeSettings_succeeds_with_instant_threshold_and_delay(
    paymaster
):
    """Test that instant threshold with delay blocks is valid"""
    min_delay = paymaster.MIN_EXPENSIVE_CHEQUE_DELAY()
    is_valid = paymaster.isValidChequeSettings(
        0,  # _maxNumActiveCheques
        0,  # _maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # _instantUsdThreshold (must be non-zero)
        0,  # _perPeriodPaidUsdCap
        0,  # _maxNumChequesPaidPerPeriod
        0,  # _payCooldownBlocks
        0,  # _perPeriodCreatedUsdCap
        0,  # _maxNumChequesCreatedPerPeriod
        0,  # _createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # _periodLength
        min_delay,  # _expensiveDelayBlocks (VALID: set with instant threshold)
        0,  # _defaultExpiryBlocks
        ONE_DAY_IN_BLOCKS,  # _timeLock
    )
    assert is_valid == True


def test_isValidChequeSettings_fails_with_expensive_delay_below_minimum(
    paymaster
):
    """Test that expensive delay below minimum is invalid"""
    min_delay = paymaster.MIN_EXPENSIVE_CHEQUE_DELAY()
    is_valid = paymaster.isValidChequeSettings(
        0,  # _maxNumActiveCheques
        0,  # _maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # _instantUsdThreshold (must be non-zero)
        0,  # _perPeriodPaidUsdCap
        0,  # _maxNumChequesPaidPerPeriod
        0,  # _payCooldownBlocks
        0,  # _perPeriodCreatedUsdCap
        0,  # _maxNumChequesCreatedPerPeriod
        0,  # _createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # _periodLength
        min_delay - 1,  # _expensiveDelayBlocks (INVALID: below minimum)
        0,  # _defaultExpiryBlocks
        ONE_DAY_IN_BLOCKS,  # _timeLock
    )
    assert is_valid == False


def test_isValidChequeSettings_fails_with_expensive_delay_above_maximum(
    paymaster
):
    """Test that expensive delay above maximum is invalid"""
    max_unlock = paymaster.MAX_UNLOCK_BLOCKS()
    is_valid = paymaster.isValidChequeSettings(
        0,  # _maxNumActiveCheques
        0,  # _maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # _instantUsdThreshold (must be non-zero)
        0,  # _perPeriodPaidUsdCap
        0,  # _maxNumChequesPaidPerPeriod
        0,  # _payCooldownBlocks
        0,  # _perPeriodCreatedUsdCap
        0,  # _maxNumChequesCreatedPerPeriod
        0,  # _createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # _periodLength
        max_unlock + 1,  # _expensiveDelayBlocks (INVALID: above maximum)
        0,  # _defaultExpiryBlocks
        ONE_DAY_IN_BLOCKS,  # _timeLock
    )
    assert is_valid == False


def test_isValidChequeSettings_succeeds_with_expensive_delay_at_maximum(
    paymaster
):
    """Test that expensive delay at maximum is valid"""
    max_unlock = paymaster.MAX_UNLOCK_BLOCKS()
    is_valid = paymaster.isValidChequeSettings(
        0,  # _maxNumActiveCheques
        0,  # _maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # _instantUsdThreshold (must be non-zero)
        0,  # _perPeriodPaidUsdCap
        0,  # _maxNumChequesPaidPerPeriod
        0,  # _payCooldownBlocks
        0,  # _perPeriodCreatedUsdCap
        0,  # _maxNumChequesCreatedPerPeriod
        0,  # _createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # _periodLength
        max_unlock,  # _expensiveDelayBlocks (VALID: at maximum)
        0,  # _defaultExpiryBlocks
        ONE_DAY_IN_BLOCKS,  # _timeLock
    )
    assert is_valid == True


def test_isValidChequeSettings_fails_with_expiry_exceeding_max(
    paymaster
):
    """Test that expiry blocks cannot exceed MAX_EXPIRY_BLOCKS"""
    max_expiry = paymaster.MAX_EXPIRY_BLOCKS()
    is_valid = paymaster.isValidChequeSettings(
        0,  # _maxNumActiveCheques
        0,  # _maxChequeUsdValue
        0,  # _instantUsdThreshold
        0,  # _perPeriodPaidUsdCap
        0,  # _maxNumChequesPaidPerPeriod
        0,  # _payCooldownBlocks
        0,  # _perPeriodCreatedUsdCap
        0,  # _maxNumChequesCreatedPerPeriod
        0,  # _createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # _periodLength
        0,  # _expensiveDelayBlocks
        max_expiry + 1,  # _defaultExpiryBlocks (INVALID: exceeds max)
        ONE_DAY_IN_BLOCKS,  # _timeLock
    )
    assert is_valid == False


def test_isValidChequeSettings_succeeds_with_expiry_at_max(
    paymaster
):
    """Test that expiry blocks at MAX_EXPIRY_BLOCKS is valid"""
    max_expiry = paymaster.MAX_EXPIRY_BLOCKS()
    min_delay = paymaster.MIN_EXPENSIVE_CHEQUE_DELAY()
    is_valid = paymaster.isValidChequeSettings(
        0,  # _maxNumActiveCheques
        0,  # _maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # _instantUsdThreshold (must be non-zero)
        0,  # _perPeriodPaidUsdCap
        0,  # _maxNumChequesPaidPerPeriod
        0,  # _payCooldownBlocks
        0,  # _perPeriodCreatedUsdCap
        0,  # _maxNumChequesCreatedPerPeriod
        0,  # _createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # _periodLength
        min_delay,  # _expensiveDelayBlocks (required when instant threshold is set)
        max_expiry,  # _defaultExpiryBlocks (VALID: at max)
        ONE_DAY_IN_BLOCKS,  # _timeLock
    )
    assert is_valid == True


def test_isValidChequeSettings_fails_with_expiry_less_than_timelock(
    paymaster
):
    """Test that expiry blocks cannot be less than wallet timelock"""
    # Use a meaningful timelock value for testing
    timelock = ONE_DAY_IN_BLOCKS * 2  # 2 days
    
    is_valid = paymaster.isValidChequeSettings(
        0,  # _maxNumActiveCheques
        0,  # _maxChequeUsdValue
        0,  # _instantUsdThreshold
        0,  # _perPeriodPaidUsdCap
        0,  # _maxNumChequesPaidPerPeriod
        0,  # _payCooldownBlocks
        0,  # _perPeriodCreatedUsdCap
        0,  # _maxNumChequesCreatedPerPeriod
        0,  # _createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # _periodLength
        0,  # _expensiveDelayBlocks
        timelock - 1,  # _defaultExpiryBlocks (INVALID: less than timelock)
        timelock,  # _timeLock
    )
    assert is_valid == False


def test_isValidChequeSettings_with_complex_valid_configuration(
    paymaster
):
    """Test a complex but valid configuration with multiple constraints"""
    min_delay = paymaster.MIN_EXPENSIVE_CHEQUE_DELAY()
    is_valid = paymaster.isValidChequeSettings(
        10,  # _maxNumActiveCheques
        500 * EIGHTEEN_DECIMALS,  # _maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # _instantUsdThreshold (must be non-zero)
        1000 * EIGHTEEN_DECIMALS,  # _perPeriodPaidUsdCap
        50,  # _maxNumChequesPaidPerPeriod
        ONE_HOUR_IN_BLOCKS,  # _payCooldownBlocks
        2000 * EIGHTEEN_DECIMALS,  # _perPeriodCreatedUsdCap
        20,  # _maxNumChequesCreatedPerPeriod
        30 * 60,  # _createCooldownBlocks (30 minutes)
        ONE_WEEK_IN_BLOCKS,  # _periodLength
        min_delay,  # _expensiveDelayBlocks
        ONE_DAY_IN_BLOCKS * 3,  # _defaultExpiryBlocks
        ONE_DAY_IN_BLOCKS,  # _timeLock
    )
    assert is_valid == True


def test_isValidChequeSettings_with_multiple_violations(
    paymaster
):
    """Test that multiple validation violations still return False"""
    is_valid = paymaster.isValidChequeSettings(
        0,  # _maxNumActiveCheques
        1000 * EIGHTEEN_DECIMALS,  # _maxChequeUsdValue
        0,  # _instantUsdThreshold
        500 * EIGHTEEN_DECIMALS,  # _perPeriodPaidUsdCap (INVALID: less than max cheque)
        0,  # _maxNumChequesPaidPerPeriod
        ONE_WEEK_IN_BLOCKS + 1,  # _payCooldownBlocks (INVALID: exceeds period)
        0,  # _perPeriodCreatedUsdCap
        0,  # _maxNumChequesCreatedPerPeriod
        0,  # _createCooldownBlocks
        0,  # _periodLength (INVALID: zero)
        0,  # _expensiveDelayBlocks
        0,  # _defaultExpiryBlocks
        ONE_DAY_IN_BLOCKS,  # _timeLock
    )
    assert is_valid == False


def test_isValidChequeSettings_boundary_test_all_at_maximum(
    paymaster
):
    """Test settings with all values at their maximum allowed"""
    max_period = paymaster.MAX_CHEQUE_PERIOD()
    max_unlock = paymaster.MAX_UNLOCK_BLOCKS()
    max_expiry = paymaster.MAX_EXPIRY_BLOCKS()
    
    is_valid = paymaster.isValidChequeSettings(
        0,  # _maxNumActiveCheques
        0,  # _maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # _instantUsdThreshold (must be non-zero)
        0,  # _perPeriodPaidUsdCap
        0,  # _maxNumChequesPaidPerPeriod
        max_period,  # _payCooldownBlocks (equal to period is allowed)
        0,  # _perPeriodCreatedUsdCap
        0,  # _maxNumChequesCreatedPerPeriod
        max_period,  # _createCooldownBlocks (equal to period is allowed)
        max_period,  # _periodLength
        max_unlock,  # _expensiveDelayBlocks (required when instant threshold is set)
        max_expiry,  # _defaultExpiryBlocks
        ONE_DAY_IN_BLOCKS,  # _timeLock
    )
    assert is_valid == True


def test_isValidChequeSettings_boundary_test_all_at_minimum(
    paymaster
):
    """Test settings with all values at their minimum allowed (except zeros)"""
    min_period = paymaster.MIN_CHEQUE_PERIOD()
    min_delay = paymaster.MIN_EXPENSIVE_CHEQUE_DELAY()
    
    is_valid = paymaster.isValidChequeSettings(
        0,  # _maxNumActiveCheques
        0,  # _maxChequeUsdValue
        1,  # _instantUsdThreshold (smallest non-zero value)
        0,  # _perPeriodPaidUsdCap
        0,  # _maxNumChequesPaidPerPeriod
        0,  # _payCooldownBlocks (zero is allowed)
        0,  # _perPeriodCreatedUsdCap
        0,  # _maxNumChequesCreatedPerPeriod
        0,  # _createCooldownBlocks (zero is allowed)
        min_period,  # _periodLength
        min_delay,  # _expensiveDelayBlocks
        min_delay,  # _defaultExpiryBlocks (using min_delay as a reasonable minimum)
        ONE_DAY_IN_BLOCKS,  # _timeLock
    )
    assert is_valid == True


################################
# Cheque Creation - Validation #
################################


def test_isValidNewCheque_fails_when_recipient_is_whitelisted(
    paymaster, user_wallet, user_wallet_config, bob, alice, alpha_token, createChequeSettings, createChequeData
):
    """Test that cheques cannot be created to whitelisted addresses"""
    cheque_settings = createChequeSettings(
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_MONTH_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
    )
    cheque_data = createChequeData()
    
    is_valid = paymaster.isValidNewCheque(
        user_wallet.address,  # _wallet
        user_wallet_config.address,  # _walletConfig
        bob,  # _owner
        True,  # _isRecipientOnWhitelist (INVALID: whitelisted)
        cheque_settings,  # _chequeSettings
        cheque_data,  # _chequeData
        False,  # _isExistingCheque
        0,  # _numActiveCheques
        ONE_DAY_IN_BLOCKS,  # _timeLock
        alice,  # _recipient (doesn't matter, whitelisted check comes first)
        alpha_token.address,  # _asset
        100 * EIGHTEEN_DECIMALS,  # _amount
        ONE_DAY_IN_BLOCKS,  # _unlockNumBlocks
        ONE_WEEK_IN_BLOCKS,  # _expiryNumBlocks
        True,  # _canManagerPay
        False,  # _canBePulled
        bob,  # _creator
        100 * EIGHTEEN_DECIMALS,  # _usdValue
    )
    assert is_valid == False


def test_isValidNewCheque_fails_when_recipient_is_zero_address(
    paymaster, user_wallet, user_wallet_config, bob, alpha_token, createChequeSettings, createChequeData
):
    """Test that cheques cannot be created to zero address"""
    cheque_settings = createChequeSettings(
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_MONTH_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
    )
    cheque_data = createChequeData()
    
    is_valid = paymaster.isValidNewCheque(
        user_wallet.address,  # _wallet
        user_wallet_config.address,  # _walletConfig
        bob,  # _owner
        False,  # _isRecipientOnWhitelist
        cheque_settings,  # _chequeSettings
        cheque_data,  # _chequeData
        False,  # _isExistingCheque
        0,  # _numActiveCheques
        ONE_DAY_IN_BLOCKS,  # _timeLock
        ZERO_ADDRESS,  # _recipient (INVALID: zero address)
        alpha_token.address,  # _asset
        100 * EIGHTEEN_DECIMALS,  # _amount
        ONE_DAY_IN_BLOCKS,  # _unlockNumBlocks
        ONE_WEEK_IN_BLOCKS,  # _expiryNumBlocks
        True,  # _canManagerPay
        False,  # _canBePulled
        bob,  # _creator
        100 * EIGHTEEN_DECIMALS,  # _usdValue
    )
    assert is_valid == False


def test_isValidNewCheque_fails_when_recipient_is_wallet(
    paymaster, user_wallet, user_wallet_config, bob, alpha_token, createChequeSettings, createChequeData
):
    """Test that cheques cannot be created to the wallet itself"""
    cheque_settings = createChequeSettings(
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_MONTH_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
    )
    cheque_data = createChequeData()
    
    is_valid = paymaster.isValidNewCheque(
        user_wallet.address,  # _wallet
        user_wallet_config.address,  # _walletConfig
        bob,  # _owner
        False,  # _isRecipientOnWhitelist
        cheque_settings,  # _chequeSettings
        cheque_data,  # _chequeData
        False,  # _isExistingCheque
        0,  # _numActiveCheques
        ONE_DAY_IN_BLOCKS,  # _timeLock
        user_wallet.address,  # _recipient (INVALID: same as wallet)
        alpha_token.address,  # _asset
        100 * EIGHTEEN_DECIMALS,  # _amount
        ONE_DAY_IN_BLOCKS,  # _unlockNumBlocks
        ONE_WEEK_IN_BLOCKS,  # _expiryNumBlocks
        True,  # _canManagerPay
        False,  # _canBePulled
        bob,  # _creator
        100 * EIGHTEEN_DECIMALS,  # _usdValue
    )
    assert is_valid == False


def test_isValidNewCheque_fails_when_recipient_is_wallet_config(
    paymaster, user_wallet, user_wallet_config, bob, alpha_token, createChequeSettings, createChequeData
):
    """Test that cheques cannot be created to the wallet config contract"""
    cheque_settings = createChequeSettings(
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_MONTH_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
    )
    cheque_data = createChequeData()
    
    is_valid = paymaster.isValidNewCheque(
        user_wallet.address,  # _wallet
        user_wallet_config.address,  # _walletConfig
        bob,  # _owner
        False,  # _isRecipientOnWhitelist
        cheque_settings,  # _chequeSettings
        cheque_data,  # _chequeData
        False,  # _isExistingCheque
        0,  # _numActiveCheques
        ONE_DAY_IN_BLOCKS,  # _timeLock
        user_wallet_config.address,  # _recipient (INVALID: same as wallet config)
        alpha_token.address,  # _asset
        100 * EIGHTEEN_DECIMALS,  # _amount
        ONE_DAY_IN_BLOCKS,  # _unlockNumBlocks
        ONE_WEEK_IN_BLOCKS,  # _expiryNumBlocks
        True,  # _canManagerPay
        False,  # _canBePulled
        bob,  # _creator
        100 * EIGHTEEN_DECIMALS,  # _usdValue
    )
    assert is_valid == False


def test_isValidNewCheque_fails_when_recipient_is_owner(
    paymaster, user_wallet, user_wallet_config, bob, alpha_token, createChequeSettings, createChequeData
):
    """Test that cheques cannot be created to the owner"""
    cheque_settings = createChequeSettings(
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_MONTH_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
    )
    cheque_data = createChequeData()
    
    is_valid = paymaster.isValidNewCheque(
        user_wallet.address,  # _wallet
        user_wallet_config.address,  # _walletConfig
        bob,  # _owner
        False,  # _isRecipientOnWhitelist
        cheque_settings,  # _chequeSettings
        cheque_data,  # _chequeData
        False,  # _isExistingCheque
        0,  # _numActiveCheques
        ONE_DAY_IN_BLOCKS,  # _timeLock
        bob,  # _recipient (INVALID: same as owner)
        alpha_token.address,  # _asset
        100 * EIGHTEEN_DECIMALS,  # _amount
        ONE_DAY_IN_BLOCKS,  # _unlockNumBlocks
        ONE_WEEK_IN_BLOCKS,  # _expiryNumBlocks
        True,  # _canManagerPay
        False,  # _canBePulled
        bob,  # _creator
        100 * EIGHTEEN_DECIMALS,  # _usdValue
    )
    assert is_valid == False


def test_isValidNewCheque_succeeds_with_valid_recipient(
    paymaster, user_wallet, user_wallet_config, bob, alice, alpha_token, createChequeSettings, createChequeData
):
    """Test that cheques can be created to valid recipients"""
    cheque_settings = createChequeSettings(
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_MONTH_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
    )
    cheque_data = createChequeData()
    
    is_valid = paymaster.isValidNewCheque(
        user_wallet.address,  # _wallet
        user_wallet_config.address,  # _walletConfig
        bob,  # _owner
        False,  # _isRecipientOnWhitelist
        cheque_settings,  # _chequeSettings
        cheque_data,  # _chequeData
        False,  # _isExistingCheque
        0,  # _numActiveCheques
        ONE_DAY_IN_BLOCKS,  # _timeLock
        alice,  # _recipient (VALID: different address)
        alpha_token.address,  # _asset
        100 * EIGHTEEN_DECIMALS,  # _amount
        ONE_DAY_IN_BLOCKS,  # _unlockNumBlocks
        ONE_WEEK_IN_BLOCKS,  # _expiryNumBlocks
        True,  # _canManagerPay
        False,  # _canBePulled
        bob,  # _creator
        100 * EIGHTEEN_DECIMALS,  # _usdValue
    )
    assert is_valid == True


def test_isValidNewCheque_fails_with_zero_address_asset(
    paymaster, user_wallet, user_wallet_config, bob, alice, createChequeSettings, createChequeData
):
    """Test that cheques cannot be created with zero address as asset"""
    cheque_settings = createChequeSettings(
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_MONTH_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
    )
    cheque_data = createChequeData()
    
    is_valid = paymaster.isValidNewCheque(
        user_wallet.address,  # _wallet
        user_wallet_config.address,  # _walletConfig
        bob,  # _owner
        False,  # _isRecipientOnWhitelist
        cheque_settings,  # _chequeSettings
        cheque_data,  # _chequeData
        False,  # _isExistingCheque
        0,  # _numActiveCheques
        ONE_DAY_IN_BLOCKS,  # _timeLock
        alice,  # _recipient
        ZERO_ADDRESS,  # _asset (INVALID: zero address)
        100 * EIGHTEEN_DECIMALS,  # _amount
        ONE_DAY_IN_BLOCKS,  # _unlockNumBlocks
        ONE_WEEK_IN_BLOCKS,  # _expiryNumBlocks
        True,  # _canManagerPay
        False,  # _canBePulled
        bob,  # _creator
        100 * EIGHTEEN_DECIMALS,  # _usdValue
    )
    assert is_valid == False


def test_isValidNewCheque_fails_with_zero_amount(
    paymaster, user_wallet, user_wallet_config, bob, alice, alpha_token, createChequeSettings, createChequeData
):
    """Test that cheques cannot be created with zero amount"""
    cheque_settings = createChequeSettings(
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_MONTH_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
    )
    cheque_data = createChequeData()
    
    is_valid = paymaster.isValidNewCheque(
        user_wallet.address,  # _wallet
        user_wallet_config.address,  # _walletConfig
        bob,  # _owner
        False,  # _isRecipientOnWhitelist
        cheque_settings,  # _chequeSettings
        cheque_data,  # _chequeData
        False,  # _isExistingCheque
        0,  # _numActiveCheques
        ONE_DAY_IN_BLOCKS,  # _timeLock
        alice,  # _recipient
        alpha_token.address,  # _asset
        0,  # _amount (INVALID: zero)
        ONE_DAY_IN_BLOCKS,  # _unlockNumBlocks
        ONE_WEEK_IN_BLOCKS,  # _expiryNumBlocks
        True,  # _canManagerPay
        False,  # _canBePulled
        bob,  # _creator
        100 * EIGHTEEN_DECIMALS,  # _usdValue
    )
    assert is_valid == False


def test_isValidNewCheque_fails_when_asset_not_in_allowed_list(
    paymaster, user_wallet, user_wallet_config, bob, alice, alpha_token, bravo_token, createChequeSettings, createChequeData
):
    """Test that cheques cannot be created with assets not in allowed list"""
    cheque_settings = createChequeSettings(
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_MONTH_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _allowedAssets=[alpha_token.address],  # Only allow one specific asset
    )
    cheque_data = createChequeData()
    
    is_valid = paymaster.isValidNewCheque(
        user_wallet.address,  # _wallet
        user_wallet_config.address,  # _walletConfig
        bob,  # _owner
        False,  # _isRecipientOnWhitelist
        cheque_settings,  # _chequeSettings
        cheque_data,  # _chequeData
        False,  # _isExistingCheque
        0,  # _numActiveCheques
        ONE_DAY_IN_BLOCKS,  # _timeLock
        alice,  # _recipient
        bravo_token.address,  # _asset (INVALID: not in allowed list)
        100 * EIGHTEEN_DECIMALS,  # _amount
        ONE_DAY_IN_BLOCKS,  # _unlockNumBlocks
        ONE_WEEK_IN_BLOCKS,  # _expiryNumBlocks
        True,  # _canManagerPay
        False,  # _canBePulled
        bob,  # _creator
        100 * EIGHTEEN_DECIMALS,  # _usdValue
    )
    assert is_valid == False


def test_isValidNewCheque_succeeds_when_asset_in_allowed_list(
    paymaster, user_wallet, user_wallet_config, bob, alice, alpha_token, createChequeSettings, createChequeData
):
    """Test that cheques can be created with assets in allowed list"""
    cheque_settings = createChequeSettings(
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_MONTH_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _allowedAssets=[alpha_token.address],  # Allow this specific asset
    )
    cheque_data = createChequeData()
    
    is_valid = paymaster.isValidNewCheque(
        user_wallet.address,  # _wallet
        user_wallet_config.address,  # _walletConfig
        bob,  # _owner
        False,  # _isRecipientOnWhitelist
        cheque_settings,  # _chequeSettings
        cheque_data,  # _chequeData
        False,  # _isExistingCheque
        0,  # _numActiveCheques
        ONE_DAY_IN_BLOCKS,  # _timeLock
        alice,  # _recipient
        alpha_token.address,  # _asset (VALID: in allowed list)
        100 * EIGHTEEN_DECIMALS,  # _amount
        ONE_DAY_IN_BLOCKS,  # _unlockNumBlocks
        ONE_WEEK_IN_BLOCKS,  # _expiryNumBlocks
        True,  # _canManagerPay
        False,  # _canBePulled
        bob,  # _creator
        100 * EIGHTEEN_DECIMALS,  # _usdValue
    )
    assert is_valid == True


def test_isValidNewCheque_succeeds_when_allowed_assets_empty(
    paymaster, user_wallet, user_wallet_config, bob, alice, alpha_token, createChequeSettings, createChequeData
):
    """Test that any asset is allowed when allowedAssets is empty"""
    cheque_settings = createChequeSettings(
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_MONTH_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _allowedAssets=[],  # Empty list means all assets allowed
    )
    cheque_data = createChequeData()
    
    is_valid = paymaster.isValidNewCheque(
        user_wallet.address,  # _wallet
        user_wallet_config.address,  # _walletConfig
        bob,  # _owner
        False,  # _isRecipientOnWhitelist
        cheque_settings,  # _chequeSettings
        cheque_data,  # _chequeData
        False,  # _isExistingCheque
        0,  # _numActiveCheques
        ONE_DAY_IN_BLOCKS,  # _timeLock
        alice,  # _recipient
        alpha_token.address,  # _asset (VALID: any asset allowed when list is empty)
        100 * EIGHTEEN_DECIMALS,  # _amount
        ONE_DAY_IN_BLOCKS,  # _unlockNumBlocks
        ONE_WEEK_IN_BLOCKS,  # _expiryNumBlocks
        True,  # _canManagerPay
        False,  # _canBePulled
        bob,  # _creator
        100 * EIGHTEEN_DECIMALS,  # _usdValue
    )
    assert is_valid == True


def test_isValidNewCheque_fails_when_can_be_pulled_not_allowed_globally(
    paymaster, user_wallet, user_wallet_config, bob, alice, alpha_token, createChequeSettings, createChequeData
):
    """Test that cheques cannot be pullable when not allowed globally"""
    cheque_settings = createChequeSettings(
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_MONTH_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _canBePulled=False,  # Globally disable pullable cheques
    )
    cheque_data = createChequeData()
    
    is_valid = paymaster.isValidNewCheque(
        user_wallet.address,  # _wallet
        user_wallet_config.address,  # _walletConfig
        bob,  # _owner
        False,  # _isRecipientOnWhitelist
        cheque_settings,  # _chequeSettings
        cheque_data,  # _chequeData
        False,  # _isExistingCheque
        0,  # _numActiveCheques
        ONE_DAY_IN_BLOCKS,  # _timeLock
        alice,  # _recipient
        alpha_token.address,  # _asset
        100 * EIGHTEEN_DECIMALS,  # _amount
        ONE_DAY_IN_BLOCKS,  # _unlockNumBlocks
        ONE_WEEK_IN_BLOCKS,  # _expiryNumBlocks
        True,  # _canManagerPay
        True,  # _canBePulled (INVALID: globally disabled)
        bob,  # _creator
        100 * EIGHTEEN_DECIMALS,  # _usdValue
    )
    assert is_valid == False


def test_isValidNewCheque_fails_when_manager_pay_not_allowed_globally(
    paymaster, user_wallet, user_wallet_config, bob, alice, alpha_token, createChequeSettings, createChequeData
):
    """Test that cheques cannot be manager payable when not allowed globally"""
    cheque_settings = createChequeSettings(
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_MONTH_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _canManagerPay=False,  # Globally disable manager pay
    )
    cheque_data = createChequeData()
    
    is_valid = paymaster.isValidNewCheque(
        user_wallet.address,  # _wallet
        user_wallet_config.address,  # _walletConfig
        bob,  # _owner
        False,  # _isRecipientOnWhitelist
        cheque_settings,  # _chequeSettings
        cheque_data,  # _chequeData
        False,  # _isExistingCheque
        0,  # _numActiveCheques
        ONE_DAY_IN_BLOCKS,  # _timeLock
        alice,  # _recipient
        alpha_token.address,  # _asset
        100 * EIGHTEEN_DECIMALS,  # _amount
        ONE_DAY_IN_BLOCKS,  # _unlockNumBlocks
        ONE_WEEK_IN_BLOCKS,  # _expiryNumBlocks
        True,  # _canManagerPay (INVALID: globally disabled)
        False,  # _canBePulled
        bob,  # _creator
        100 * EIGHTEEN_DECIMALS,  # _usdValue
    )
    assert is_valid == False


def test_isValidNewCheque_succeeds_with_restrictive_cheque_permissions(
    paymaster, user_wallet, user_wallet_config, bob, alice, alpha_token, createChequeSettings, createChequeData
):
    """Test that cheques can be created with specific permissions matching global settings"""
    cheque_settings = createChequeSettings(
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_MONTH_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _canBePulled=False,  # Disable pullable cheques
        _canManagerPay=False,  # Disable manager pay
    )
    cheque_data = createChequeData()
    
    is_valid = paymaster.isValidNewCheque(
        user_wallet.address,  # _wallet
        user_wallet_config.address,  # _walletConfig
        bob,  # _owner
        False,  # _isRecipientOnWhitelist
        cheque_settings,  # _chequeSettings
        cheque_data,  # _chequeData
        False,  # _isExistingCheque
        0,  # _numActiveCheques
        ONE_DAY_IN_BLOCKS,  # _timeLock
        alice,  # _recipient
        alpha_token.address,  # _asset
        100 * EIGHTEEN_DECIMALS,  # _amount
        ONE_DAY_IN_BLOCKS,  # _unlockNumBlocks
        ONE_WEEK_IN_BLOCKS,  # _expiryNumBlocks
        False,  # _canManagerPay (VALID: matches global)
        False,  # _canBePulled (VALID: matches global)
        bob,  # _creator
        100 * EIGHTEEN_DECIMALS,  # _usdValue
    )
    assert is_valid == True


def test_isValidNewCheque_fails_when_exceeds_max_active_cheques(
    paymaster, user_wallet, user_wallet_config, bob, alice, alpha_token, createChequeSettings, createChequeData
):
    """Test that new cheques cannot exceed max active cheques limit"""
    cheque_settings = createChequeSettings(
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_MONTH_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _maxNumActiveCheques=5,  # Limit to 5 active cheques
    )
    cheque_data = createChequeData()
    
    is_valid = paymaster.isValidNewCheque(
        user_wallet.address,  # _wallet
        user_wallet_config.address,  # _walletConfig
        bob,  # _owner
        False,  # _isRecipientOnWhitelist
        cheque_settings,  # _chequeSettings
        cheque_data,  # _chequeData
        False,  # _isExistingCheque (new cheque)
        5,  # _numActiveCheques (INVALID: already at limit)
        ONE_DAY_IN_BLOCKS,  # _timeLock
        alice,  # _recipient
        alpha_token.address,  # _asset
        100 * EIGHTEEN_DECIMALS,  # _amount
        ONE_DAY_IN_BLOCKS,  # _unlockNumBlocks
        ONE_WEEK_IN_BLOCKS,  # _expiryNumBlocks
        True,  # _canManagerPay
        False,  # _canBePulled
        bob,  # _creator
        100 * EIGHTEEN_DECIMALS,  # _usdValue
    )
    assert is_valid == False


def test_isValidNewCheque_succeeds_when_replacing_existing_cheque(
    paymaster, user_wallet, user_wallet_config, bob, alice, alpha_token, createChequeSettings, createChequeData
):
    """Test that replacing existing cheques doesn't count against limit"""
    cheque_settings = createChequeSettings(
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_MONTH_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _maxNumActiveCheques=5,  # Limit to 5 active cheques
    )
    cheque_data = createChequeData()
    
    is_valid = paymaster.isValidNewCheque(
        user_wallet.address,  # _wallet
        user_wallet_config.address,  # _walletConfig
        bob,  # _owner
        False,  # _isRecipientOnWhitelist
        cheque_settings,  # _chequeSettings
        cheque_data,  # _chequeData
        True,  # _isExistingCheque (VALID: replacing, not new)
        5,  # _numActiveCheques (at limit, but replacing)
        ONE_DAY_IN_BLOCKS,  # _timeLock
        alice,  # _recipient
        alpha_token.address,  # _asset
        100 * EIGHTEEN_DECIMALS,  # _amount
        ONE_DAY_IN_BLOCKS,  # _unlockNumBlocks
        ONE_WEEK_IN_BLOCKS,  # _expiryNumBlocks
        True,  # _canManagerPay
        False,  # _canBePulled
        bob,  # _creator
        100 * EIGHTEEN_DECIMALS,  # _usdValue
    )
    assert is_valid == True


def test_isValidNewCheque_succeeds_with_zero_max_active_cheques(
    paymaster, user_wallet, user_wallet_config, bob, alice, alpha_token, createChequeSettings, createChequeData
):
    """Test that zero max active cheques means unlimited"""
    cheque_settings = createChequeSettings(
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_MONTH_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _maxNumActiveCheques=0,  # Zero means unlimited
    )
    cheque_data = createChequeData()
    
    is_valid = paymaster.isValidNewCheque(
        user_wallet.address,  # _wallet
        user_wallet_config.address,  # _walletConfig
        bob,  # _owner
        False,  # _isRecipientOnWhitelist
        cheque_settings,  # _chequeSettings
        cheque_data,  # _chequeData
        False,  # _isExistingCheque
        1000,  # _numActiveCheques (VALID: no limit)
        ONE_DAY_IN_BLOCKS,  # _timeLock
        alice,  # _recipient
        alpha_token.address,  # _asset
        100 * EIGHTEEN_DECIMALS,  # _amount
        ONE_DAY_IN_BLOCKS,  # _unlockNumBlocks
        ONE_WEEK_IN_BLOCKS,  # _expiryNumBlocks
        True,  # _canManagerPay
        False,  # _canBePulled
        bob,  # _creator
        100 * EIGHTEEN_DECIMALS,  # _usdValue
    )
    assert is_valid == True


def test_isValidNewCheque_fails_when_within_create_cooldown(
    paymaster, user_wallet, user_wallet_config, bob, alice, alpha_token, createChequeSettings, createChequeData
):
    """Test that cheques cannot be created within cooldown period"""
    # Advance blocks first to ensure we have a positive block number
    boa.env.time_travel(blocks=200)
    
    cheque_settings = createChequeSettings(
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_MONTH_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _createCooldownBlocks=100,  # 100 blocks cooldown
    )
    cheque_data = createChequeData(
        _lastChequeCreatedBlock=boa.env.evm.patch.block_number - 50  # Created 50 blocks ago (within cooldown)
    )
    
    is_valid = paymaster.isValidNewCheque(
        user_wallet.address,  # _wallet
        user_wallet_config.address,  # _walletConfig
        bob,  # _owner
        False,  # _isRecipientOnWhitelist
        cheque_settings,  # _chequeSettings
        cheque_data,  # _chequeData
        False,  # _isExistingCheque
        0,  # _numActiveCheques
        ONE_DAY_IN_BLOCKS,  # _timeLock
        alice,  # _recipient
        alpha_token.address,  # _asset
        100 * EIGHTEEN_DECIMALS,  # _amount
        ONE_DAY_IN_BLOCKS,  # _unlockNumBlocks
        ONE_WEEK_IN_BLOCKS,  # _expiryNumBlocks
        True,  # _canManagerPay
        False,  # _canBePulled
        bob,  # _creator
        100 * EIGHTEEN_DECIMALS,  # _usdValue
    )
    assert is_valid == False


def test_isValidNewCheque_succeeds_after_create_cooldown(
    paymaster, user_wallet, user_wallet_config, bob, alice, alpha_token, createChequeSettings, createChequeData
):
    """Test that cheques can be created after cooldown period"""
    # Advance blocks first to ensure we have a positive block number
    boa.env.time_travel(blocks=200)
    
    cheque_settings = createChequeSettings(
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_MONTH_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _createCooldownBlocks=100,  # 100 blocks cooldown
    )
    cheque_data = createChequeData(
        _lastChequeCreatedBlock=boa.env.evm.patch.block_number - 101  # Created 101 blocks ago (after cooldown)
    )
    
    is_valid = paymaster.isValidNewCheque(
        user_wallet.address,  # _wallet
        user_wallet_config.address,  # _walletConfig
        bob,  # _owner
        False,  # _isRecipientOnWhitelist
        cheque_settings,  # _chequeSettings
        cheque_data,  # _chequeData
        False,  # _isExistingCheque
        0,  # _numActiveCheques
        ONE_DAY_IN_BLOCKS,  # _timeLock
        alice,  # _recipient
        alpha_token.address,  # _asset
        100 * EIGHTEEN_DECIMALS,  # _amount
        ONE_DAY_IN_BLOCKS,  # _unlockNumBlocks
        ONE_WEEK_IN_BLOCKS,  # _expiryNumBlocks
        True,  # _canManagerPay
        False,  # _canBePulled
        bob,  # _creator
        100 * EIGHTEEN_DECIMALS,  # _usdValue
    )
    assert is_valid == True


def test_isValidNewCheque_succeeds_with_zero_create_cooldown(
    paymaster, user_wallet, user_wallet_config, bob, alice, alpha_token, createChequeSettings, createChequeData
):
    """Test that zero cooldown means no cooldown"""
    cheque_settings = createChequeSettings(
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_MONTH_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _createCooldownBlocks=0,  # No cooldown
    )
    cheque_data = createChequeData(
        _lastChequeCreatedBlock=boa.env.evm.patch.block_number  # Created this block
    )
    
    is_valid = paymaster.isValidNewCheque(
        user_wallet.address,  # _wallet
        user_wallet_config.address,  # _walletConfig
        bob,  # _owner
        False,  # _isRecipientOnWhitelist
        cheque_settings,  # _chequeSettings
        cheque_data,  # _chequeData
        False,  # _isExistingCheque
        0,  # _numActiveCheques
        ONE_DAY_IN_BLOCKS,  # _timeLock
        alice,  # _recipient
        alpha_token.address,  # _asset
        100 * EIGHTEEN_DECIMALS,  # _amount
        ONE_DAY_IN_BLOCKS,  # _unlockNumBlocks
        ONE_WEEK_IN_BLOCKS,  # _expiryNumBlocks
        True,  # _canManagerPay
        False,  # _canBePulled
        bob,  # _creator
        100 * EIGHTEEN_DECIMALS,  # _usdValue
    )
    assert is_valid == True


####################################
# Cheque Creation - Access Control #
####################################


def test_canCreateCheque_owner_can_always_create(
    paymaster, createManagerSettings
):
    """Test that owner can always create cheques regardless of settings"""
    # Even with restrictive manager settings, owner should be able to create
    manager_settings = createManagerSettings(
        _startBlock=boa.env.evm.patch.block_number + 1000,  # Not started yet
        _expiryBlock=0,
        _transferPerms=(False, False, False, [])  # All permissions disabled
    )
    
    can_create = paymaster.canCreateCheque(
        True,   # _isCreatorOwner
        False,  # _isCreatorManager
        False,  # _canManagersCreateCheques (globally disabled)
        manager_settings
    )
    assert can_create == True


def test_canCreateCheque_non_owner_non_manager_cannot_create(
    paymaster, createManagerSettings
):
    """Test that non-owner non-manager cannot create cheques"""
    manager_settings = createManagerSettings()
    
    can_create = paymaster.canCreateCheque(
        False,  # _isCreatorOwner
        False,  # _isCreatorManager
        True,   # _canManagersCreateCheques
        manager_settings
    )
    assert can_create == False


def test_canCreateCheque_manager_cannot_create_when_globally_disabled(
    paymaster, createManagerSettings
):
    """Test that managers cannot create cheques when globally disabled"""
    manager_settings = createManagerSettings(
        _transferPerms=(True, True, True, [])  # All permissions enabled
    )
    
    can_create = paymaster.canCreateCheque(
        False,  # _isCreatorOwner
        True,   # _isCreatorManager
        False,  # _canManagersCreateCheques (globally disabled)
        manager_settings
    )
    assert can_create == False


def test_canCreateCheque_manager_cannot_create_without_permission(
    paymaster, createManagerSettings, createTransferPerms
):
    """Test that managers need specific permission to create cheques"""
    transfer_perms = createTransferPerms(
        _canTransfer=True,
        _canCreateCheque=False,  # No cheque creation permission
        _canAddPendingPayee=True,
        _allowedPayees=[]
    )
    
    manager_settings = createManagerSettings(
        _transferPerms=transfer_perms
    )
    
    can_create = paymaster.canCreateCheque(
        False,  # _isCreatorOwner
        True,   # _isCreatorManager
        True,   # _canManagersCreateCheques (globally enabled)
        manager_settings
    )
    assert can_create == False


def test_canCreateCheque_manager_can_create_with_permission(
    paymaster, createManagerSettings, createTransferPerms
):
    """Test that managers can create cheques with proper permissions"""
    transfer_perms = createTransferPerms(
        _canTransfer=True,
        _canCreateCheque=True,  # Has cheque creation permission
        _canAddPendingPayee=True,
        _allowedPayees=[]
    )
    
    manager_settings = createManagerSettings(
        _transferPerms=transfer_perms
    )
    
    can_create = paymaster.canCreateCheque(
        False,  # _isCreatorOwner
        True,   # _isCreatorManager
        True,   # _canManagersCreateCheques (globally enabled)
        manager_settings
    )
    assert can_create == True


def test_canCreateCheque_manager_cannot_create_before_start_block(
    paymaster, createManagerSettings, createTransferPerms
):
    """Test that managers cannot create cheques before their start block"""
    transfer_perms = createTransferPerms(
        _canCreateCheque=True
    )
    
    manager_settings = createManagerSettings(
        _startBlock=boa.env.evm.patch.block_number + 100,  # Starts in future
        _transferPerms=transfer_perms
    )
    
    can_create = paymaster.canCreateCheque(
        False,  # _isCreatorOwner
        True,   # _isCreatorManager
        True,   # _canManagersCreateCheques
        manager_settings
    )
    assert can_create == False


def test_canCreateCheque_manager_can_create_after_start_block(
    paymaster, createManagerSettings, createTransferPerms
):
    """Test that managers can create cheques after their start block"""
    # Advance blocks first
    boa.env.time_travel(blocks=200)
    
    transfer_perms = createTransferPerms(
        _canCreateCheque=True
    )
    
    # Set start block in the past
    start_block = boa.env.evm.patch.block_number - 100
    manager_settings = createManagerSettings(
        _startBlock=start_block,
        _transferPerms=transfer_perms
    )
    
    can_create = paymaster.canCreateCheque(
        False,  # _isCreatorOwner
        True,   # _isCreatorManager
        True,   # _canManagersCreateCheques
        manager_settings
    )
    assert can_create == True


def test_canCreateCheque_manager_cannot_create_after_expiry(
    paymaster, createManagerSettings, createTransferPerms
):
    """Test that managers cannot create cheques after expiry block"""
    # Advance blocks first to ensure we have room
    boa.env.time_travel(blocks=10)
    
    transfer_perms = createTransferPerms(
        _canCreateCheque=True
    )
    
    # Set expiry block in the past
    expiry_block = boa.env.evm.patch.block_number - 1
    manager_settings = createManagerSettings(
        _startBlock=0,  # Already started
        _expiryBlock=expiry_block,  # Already expired
        _transferPerms=transfer_perms
    )
    
    can_create = paymaster.canCreateCheque(
        False,  # _isCreatorOwner
        True,   # _isCreatorManager
        True,   # _canManagersCreateCheques
        manager_settings
    )
    assert can_create == False


def test_canCreateCheque_manager_can_create_before_expiry(
    paymaster, createManagerSettings, createTransferPerms
):
    """Test that managers can create cheques before expiry block"""
    transfer_perms = createTransferPerms(
        _canCreateCheque=True
    )
    
    # Set expiry block in the future
    expiry_block = boa.env.evm.patch.block_number + 100
    manager_settings = createManagerSettings(
        _startBlock=0,  # Already started
        _expiryBlock=expiry_block,  # Not expired yet
        _transferPerms=transfer_perms
    )
    
    can_create = paymaster.canCreateCheque(
        False,  # _isCreatorOwner
        True,   # _isCreatorManager
        True,   # _canManagersCreateCheques
        manager_settings
    )
    assert can_create == True


def test_canCreateCheque_manager_can_create_with_zero_expiry(
    paymaster, createManagerSettings, createTransferPerms
):
    """Test that zero expiry means no expiry for managers"""
    transfer_perms = createTransferPerms(
        _canCreateCheque=True
    )
    
    manager_settings = createManagerSettings(
        _startBlock=0,
        _expiryBlock=0,  # Zero means no expiry
        _transferPerms=transfer_perms
    )
    
    can_create = paymaster.canCreateCheque(
        False,  # _isCreatorOwner
        True,   # _isCreatorManager
        True,   # _canManagersCreateCheques
        manager_settings
    )
    assert can_create == True


def test_canCreateCheque_manager_at_exact_expiry_block(
    paymaster, createManagerSettings, createTransferPerms
):
    """Test that managers cannot create at exact expiry block"""
    transfer_perms = createTransferPerms(
        _canCreateCheque=True
    )
    
    # Set expiry block to current block
    expiry_block = boa.env.evm.patch.block_number
    manager_settings = createManagerSettings(
        _startBlock=0,
        _expiryBlock=expiry_block,  # Expires at current block
        _transferPerms=transfer_perms
    )
    
    can_create = paymaster.canCreateCheque(
        False,  # _isCreatorOwner
        True,   # _isCreatorManager
        True,   # _canManagersCreateCheques
        manager_settings
    )
    assert can_create == False


def test_canCreateCheque_manager_at_exact_start_block(
    paymaster, createManagerSettings, createTransferPerms
):
    """Test that managers can create at exact start block"""
    transfer_perms = createTransferPerms(
        _canCreateCheque=True
    )
    
    # Set start block to current block
    start_block = boa.env.evm.patch.block_number
    manager_settings = createManagerSettings(
        _startBlock=start_block,  # Starts at current block
        _expiryBlock=0,
        _transferPerms=transfer_perms
    )
    
    can_create = paymaster.canCreateCheque(
        False,  # _isCreatorOwner
        True,   # _isCreatorManager
        True,   # _canManagersCreateCheques
        manager_settings
    )
    assert can_create == True


def test_canCreateCheque_complex_scenario_all_conditions_met(
    paymaster, createManagerSettings, createTransferPerms
):
    """Test complex scenario where all conditions are met for manager"""
    # Advance blocks to have room for past/future tests
    boa.env.time_travel(blocks=1000)
    
    transfer_perms = createTransferPerms(
        _canTransfer=True,
        _canCreateCheque=True,
        _canAddPendingPayee=True,
        _allowedPayees=[]
    )
    
    manager_settings = createManagerSettings(
        _startBlock=boa.env.evm.patch.block_number - 100,  # Started 100 blocks ago
        _expiryBlock=boa.env.evm.patch.block_number + 100,  # Expires in 100 blocks
        _transferPerms=transfer_perms
    )
    
    can_create = paymaster.canCreateCheque(
        False,  # _isCreatorOwner
        True,   # _isCreatorManager
        True,   # _canManagersCreateCheques
        manager_settings
    )
    assert can_create == True


def test_canCreateCheque_complex_scenario_one_condition_fails(
    paymaster, createManagerSettings, createTransferPerms
):
    """Test that failing any single condition prevents cheque creation"""
    # Test 1: All good except global setting
    transfer_perms = createTransferPerms(_canCreateCheque=True)
    manager_settings = createManagerSettings(
        _startBlock=0,
        _expiryBlock=0,
        _transferPerms=transfer_perms
    )
    
    can_create = paymaster.canCreateCheque(
        False,  # _isCreatorOwner
        True,   # _isCreatorManager
        False,  # _canManagersCreateCheques (FAIL: globally disabled)
        manager_settings
    )
    assert can_create == False
    
    # Test 2: All good except permission
    transfer_perms = createTransferPerms(_canCreateCheque=False)  # FAIL: no permission
    manager_settings = createManagerSettings(
        _startBlock=0,
        _expiryBlock=0,
        _transferPerms=transfer_perms
    )
    
    can_create = paymaster.canCreateCheque(
        False,  # _isCreatorOwner
        True,   # _isCreatorManager
        True,   # _canManagersCreateCheques
        manager_settings
    )
    assert can_create == False
    
    # Test 3: All good except timing
    transfer_perms = createTransferPerms(_canCreateCheque=True)
    manager_settings = createManagerSettings(
        _startBlock=boa.env.evm.patch.block_number + 1,  # FAIL: not started
        _expiryBlock=0,
        _transferPerms=transfer_perms
    )
    
    can_create = paymaster.canCreateCheque(
        False,  # _isCreatorOwner
        True,   # _isCreatorManager
        True,   # _canManagersCreateCheques
        manager_settings
    )
    assert can_create == False


