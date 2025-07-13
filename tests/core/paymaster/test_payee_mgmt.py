import pytest
import boa

from constants import EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ZERO_ADDRESS
from config.BluePrint import PARAMS


#########################
# Global Payee Settings #
#########################


def test_valid_global_payee_settings(paymaster, user_wallet, createPayeeLimits, fork):
    """Test valid global payee settings with all parameters in range"""
    # Create valid USD limits
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    # All parameters within valid ranges
    assert paymaster.isValidGlobalPayeeSettings(
        user_wallet,
        2 * ONE_DAY_IN_BLOCKS,  # _defaultPeriodLength: Within MIN and MAX
        PARAMS[fork]["PAYMASTER_MAX_START_DELAY"],  # _startDelay: Use max allowed
        ONE_DAY_IN_BLOCKS,  # _activationLength: Within MIN and MAX
        10,  # _maxNumTxsPerPeriod
        100,  # _txCooldownBlocks: Must be <= periodLength
        True,  # _failOnZeroPrice
        usd_limits,  # _usdLimits
        False  # _canPayOwner
    )


def test_valid_global_payee_settings_zero_cooldown(paymaster, user_wallet, createPayeeLimits, fork):
    """Test that zero cooldown is valid"""
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    # Zero cooldown should be valid
    assert paymaster.isValidGlobalPayeeSettings(
        user_wallet,
        2 * ONE_DAY_IN_BLOCKS,  # _defaultPeriodLength: Valid period within MIN/MAX
        PARAMS[fork]["PAYMASTER_MAX_START_DELAY"],  # _startDelay: Valid within MAX_START_DELAY
        ONE_DAY_IN_BLOCKS,  # _activationLength: Valid within MIN/MAX
        10,  # _maxNumTxsPerPeriod
        0,  # _txCooldownBlocks: Zero cooldown
        False,  # _failOnZeroPrice
        usd_limits,  # _usdLimits
        True  # _canPayOwner
    )


def test_invalid_period_length_too_short(paymaster, user_wallet, createPayeeLimits, fork):
    """Test period length below minimum"""
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    
    # Period length below minimum
    assert not paymaster.isValidGlobalPayeeSettings(
        user_wallet,
        PARAMS[fork]["PAYMASTER_MIN_PAYEE_PERIOD"] - 1,  # _defaultPeriodLength: Below minimum
        PARAMS[fork]["PAYMASTER_MAX_START_DELAY"],  # _startDelay
        ONE_DAY_IN_BLOCKS,  # _activationLength
        10,  # _maxNumTxsPerPeriod
        0,  # _txCooldownBlocks
        True,  # _failOnZeroPrice
        usd_limits,  # _usdLimits
        False  # _canPayOwner
    )


def test_invalid_period_length_too_long(paymaster, user_wallet, createPayeeLimits, fork):
    """Test period length above maximum"""
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    
    # Period length above maximum
    assert not paymaster.isValidGlobalPayeeSettings(
        user_wallet,
        PARAMS[fork]["PAYMASTER_MAX_PAYEE_PERIOD"] + 1,  # _defaultPeriodLength: Above maximum
        PARAMS[fork]["PAYMASTER_MAX_START_DELAY"],  # _startDelay
        ONE_DAY_IN_BLOCKS,  # _activationLength
        10,  # _maxNumTxsPerPeriod
        0,  # _txCooldownBlocks
        True,  # _failOnZeroPrice
        usd_limits,  # _usdLimits
        False  # _canPayOwner
    )


def test_invalid_cooldown_exceeds_period(paymaster, user_wallet, createPayeeLimits, fork):
    """Test cooldown cannot exceed period length"""
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    
    period_length = 2 * ONE_DAY_IN_BLOCKS  # Valid period within range
    
    # Cooldown exceeds period length
    assert not paymaster.isValidGlobalPayeeSettings(
        user_wallet,
        period_length,  # _defaultPeriodLength
        PARAMS[fork]["PAYMASTER_MAX_START_DELAY"],  # _startDelay
        ONE_DAY_IN_BLOCKS,  # _activationLength
        10,  # _maxNumTxsPerPeriod
        period_length + 1,  # _txCooldownBlocks: Exceeds period
        True,  # _failOnZeroPrice
        usd_limits,  # _usdLimits
        False  # _canPayOwner
    )


def test_invalid_payee_limits_per_tx_exceeds_period(paymaster, user_wallet, createPayeeLimits, fork):
    """Test invalid payee limits where perTxCap exceeds perPeriodCap"""
    # Create invalid limits - perTxCap > perPeriodCap
    usd_limits = createPayeeLimits(
        _perTxCap=10000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=1000 * EIGHTEEN_DECIMALS,  # Less than perTxCap
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    assert not paymaster.isValidGlobalPayeeSettings(
        user_wallet,
        2 * ONE_DAY_IN_BLOCKS,  # _defaultPeriodLength: Valid period within MIN/MAX
        PARAMS[fork]["PAYMASTER_MAX_START_DELAY"],  # _startDelay
        ONE_DAY_IN_BLOCKS,  # _activationLength: Valid within MIN/MAX
        10,  # _maxNumTxsPerPeriod
        100,  # _txCooldownBlocks
        True,  # _failOnZeroPrice
        usd_limits,  # _usdLimits
        False  # _canPayOwner
    )


def test_invalid_payee_limits_period_exceeds_lifetime(paymaster, user_wallet, createPayeeLimits, fork):
    """Test invalid payee limits where perPeriodCap exceeds lifetimeCap"""
    # Create invalid limits - perPeriodCap > lifetimeCap
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=100000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=10000 * EIGHTEEN_DECIMALS  # Less than perPeriodCap
    )
    
    assert not paymaster.isValidGlobalPayeeSettings(
        user_wallet,
        2 * ONE_DAY_IN_BLOCKS,  # _defaultPeriodLength: Valid period within MIN/MAX
        PARAMS[fork]["PAYMASTER_MAX_START_DELAY"],  # _startDelay
        ONE_DAY_IN_BLOCKS,  # _activationLength: Valid within MIN/MAX
        10,  # _maxNumTxsPerPeriod
        100,  # _txCooldownBlocks
        True,  # _failOnZeroPrice
        usd_limits,  # _usdLimits
        False  # _canPayOwner
    )


def test_invalid_activation_length_too_short(paymaster, user_wallet, createPayeeLimits, fork):
    """Test activation length below minimum"""
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    
    # Activation length below minimum
    assert not paymaster.isValidGlobalPayeeSettings(
        user_wallet,
        2 * ONE_DAY_IN_BLOCKS,  # _defaultPeriodLength: Valid period within MIN/MAX
        PARAMS[fork]["PAYMASTER_MAX_START_DELAY"],  # _startDelay
        PARAMS[fork]["PAYMASTER_MIN_ACTIVATION_LENGTH"] - 1,  # _activationLength: Below minimum
        10,  # _maxNumTxsPerPeriod
        100,  # _txCooldownBlocks
        True,  # _failOnZeroPrice
        usd_limits,  # _usdLimits
        False  # _canPayOwner
    )


def test_invalid_activation_length_too_long(paymaster, user_wallet, createPayeeLimits, fork):
    """Test activation length above maximum"""
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    
    # Activation length above maximum
    assert not paymaster.isValidGlobalPayeeSettings(
        user_wallet,
        2 * ONE_DAY_IN_BLOCKS,  # _defaultPeriodLength: Valid period within MIN/MAX
        PARAMS[fork]["PAYMASTER_MAX_START_DELAY"],  # _startDelay
        PARAMS[fork]["PAYMASTER_MAX_ACTIVATION_LENGTH"] + 1,  # _activationLength: Above maximum
        10,  # _maxNumTxsPerPeriod
        100,  # _txCooldownBlocks
        True,  # _failOnZeroPrice
        usd_limits,  # _usdLimits
        False  # _canPayOwner
    )


def test_invalid_start_delay_below_timelock(paymaster, user_wallet, user_wallet_config, createPayeeLimits, fork):
    """Test start delay cannot be below current timelock"""
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    
    timelock = user_wallet_config.timeLock()
    
    # Start delay below timelock
    assert not paymaster.isValidGlobalPayeeSettings(
        user_wallet,
        2 * ONE_DAY_IN_BLOCKS,  # _defaultPeriodLength: Valid period within MIN/MAX
        timelock - 1,  # _startDelay: Below timelock
        ONE_DAY_IN_BLOCKS,  # _activationLength: Valid within MIN/MAX
        10,  # _maxNumTxsPerPeriod
        100,  # _txCooldownBlocks
        True,  # _failOnZeroPrice
        usd_limits,  # _usdLimits
        False  # _canPayOwner
    )


def test_invalid_start_delay_exceeds_max(paymaster, user_wallet, createPayeeLimits, fork):
    """Test start delay cannot exceed maximum"""
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    
    # Start delay exceeds maximum
    assert not paymaster.isValidGlobalPayeeSettings(
        user_wallet,
        2 * ONE_DAY_IN_BLOCKS,  # _defaultPeriodLength: Valid period within MIN/MAX
        PARAMS[fork]["PAYMASTER_MAX_START_DELAY"] + 1,  # _startDelay: Above maximum
        ONE_DAY_IN_BLOCKS,  # _activationLength: Valid within MIN/MAX
        10,  # _maxNumTxsPerPeriod
        100,  # _txCooldownBlocks
        True,  # _failOnZeroPrice
        usd_limits,  # _usdLimits
        False  # _canPayOwner
    )


def test_valid_limits_with_zero_values(paymaster, user_wallet, createPayeeLimits, fork):
    """Test that zero values in limits are treated as unlimited"""
    # Create limits with some zero values (unlimited)
    usd_limits = createPayeeLimits(
        _perTxCap=0,  # Unlimited per tx
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=0  # Unlimited lifetime
    )
    
    # Should be valid - zeros mean unlimited
    assert paymaster.isValidGlobalPayeeSettings(
        user_wallet,
        2 * ONE_DAY_IN_BLOCKS,  # _defaultPeriodLength: Valid period within MIN/MAX
        PARAMS[fork]["PAYMASTER_MAX_START_DELAY"],  # _startDelay
        ONE_DAY_IN_BLOCKS,  # _activationLength: Valid within MIN/MAX
        10,  # _maxNumTxsPerPeriod
        100,  # _txCooldownBlocks
        True,  # _failOnZeroPrice
        usd_limits,  # _usdLimits
        False  # _canPayOwner
    )


def test_valid_at_boundaries(paymaster, user_wallet, user_wallet_config, createPayeeLimits, fork):
    """Test valid settings at exact boundaries"""
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    
    timelock = user_wallet_config.timeLock()
    
    # Test at minimum boundaries
    assert paymaster.isValidGlobalPayeeSettings(
        user_wallet,
        PARAMS[fork]["PAYMASTER_MIN_PAYEE_PERIOD"],  # _defaultPeriodLength: At minimum
        timelock,  # _startDelay: At minimum (timelock)
        PARAMS[fork]["PAYMASTER_MIN_ACTIVATION_LENGTH"],  # _activationLength: At minimum
        1,  # _maxNumTxsPerPeriod
        0,  # _txCooldownBlocks
        False,  # _failOnZeroPrice
        usd_limits,  # _usdLimits
        True  # _canPayOwner
    )
    
    # Test at maximum boundaries
    assert paymaster.isValidGlobalPayeeSettings(
        user_wallet,
        PARAMS[fork]["PAYMASTER_MAX_PAYEE_PERIOD"],  # _defaultPeriodLength: At maximum
        PARAMS[fork]["PAYMASTER_MAX_START_DELAY"],  # _startDelay: At maximum
        PARAMS[fork]["PAYMASTER_MAX_ACTIVATION_LENGTH"],  # _activationLength: At maximum
        1000,  # _maxNumTxsPerPeriod
        PARAMS[fork]["PAYMASTER_MAX_PAYEE_PERIOD"],  # _txCooldownBlocks: At period length
        True,  # _failOnZeroPrice
        usd_limits,  # _usdLimits
        False  # _canPayOwner
    )


#########################
# Can Add Pending Payee #
#########################


def test_owner_cannot_add_pending_payee(paymaster, user_wallet, bob, charlie):
    """Test that owner cannot add pending payee (they add directly)"""
    # Owner should return False for canAddPendingPayee
    assert not paymaster.canAddPendingPayee(user_wallet, charlie, bob)


def test_manager_can_add_pending_payee_with_permission(createGlobalManagerSettings, createTransferPerms, createManagerSettings, paymaster, user_wallet, user_wallet_config, alice, charlie, high_command):
    """Test manager with canAddPendingPayee permission"""
    # Set global permissions to allow adding pending payees
    global_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_global_manager_settings = createGlobalManagerSettings(_transferPerms=global_transfer_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    # Add manager with permission to add pending payees
    manager_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_manager_settings = createManagerSettings(_transferPerms=manager_transfer_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Manager should be able to add pending payee
    assert paymaster.canAddPendingPayee(user_wallet, charlie, alice)


def test_manager_cannot_add_pending_payee_without_permission(createGlobalManagerSettings, createTransferPerms, createManagerSettings, paymaster, user_wallet, user_wallet_config, alice, charlie, high_command):
    """Test manager without canAddPendingPayee permission"""
    # Set global permissions to allow adding pending payees
    global_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_global_manager_settings = createGlobalManagerSettings(_transferPerms=global_transfer_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    # Add manager WITHOUT permission to add pending payees
    manager_transfer_perms = createTransferPerms(_canAddPendingPayee=False)
    new_manager_settings = createManagerSettings(_transferPerms=manager_transfer_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Manager should NOT be able to add pending payee
    assert not paymaster.canAddPendingPayee(user_wallet, charlie, alice)


def test_global_permissions_restrict_manager_add_pending_payee(createGlobalManagerSettings, createTransferPerms, createManagerSettings, paymaster, user_wallet, user_wallet_config, alice, charlie, high_command):
    """Test that global permissions can restrict manager from adding pending payees"""
    # Set global permissions to DENY adding pending payees
    global_transfer_perms = createTransferPerms(_canAddPendingPayee=False)
    new_global_manager_settings = createGlobalManagerSettings(_transferPerms=global_transfer_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    # Add manager with permission to add pending payees
    manager_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_manager_settings = createManagerSettings(_transferPerms=manager_transfer_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Manager should NOT be able to add pending payee (global restricts)
    assert not paymaster.canAddPendingPayee(user_wallet, charlie, alice)


def test_non_manager_cannot_add_pending_payee(paymaster, user_wallet, alice, charlie):
    """Test that non-manager cannot add pending payee"""
    # Non-manager should not be able to add pending payee
    assert not paymaster.canAddPendingPayee(user_wallet, charlie, alice)


def test_inactive_manager_cannot_add_pending_payee(createGlobalManagerSettings, createTransferPerms, createManagerSettings, paymaster, user_wallet, user_wallet_config, alice, charlie, high_command):
    """Test that inactive manager cannot add pending payee"""
    # This test verifies that a manager set up to start in the future cannot perform actions
    # We'll do this by adding a manager with a very high start block
    
    # Set global permissions to allow adding pending payees
    global_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_global_manager_settings = createGlobalManagerSettings(_transferPerms=global_transfer_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    # Add manager with permission but starts in far future
    manager_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_manager_settings = createManagerSettings(
        _transferPerms=manager_transfer_perms,
        _startBlock=999999999  # Starts in far future
    )
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Manager should NOT be able to add pending payee (not active yet)
    assert not paymaster.canAddPendingPayee(user_wallet, charlie, alice)


def test_expired_manager_cannot_add_pending_payee(createGlobalManagerSettings, createTransferPerms, createManagerSettings, paymaster, user_wallet, user_wallet_config, alice, charlie, high_command):
    """Test that expired manager cannot add pending payee"""
    # Set global permissions to allow adding pending payees
    global_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_global_manager_settings = createGlobalManagerSettings(_transferPerms=global_transfer_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    # Add manager with permission that will expire soon
    current_block = boa.env.evm.patch.block_number
    manager_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_manager_settings = createManagerSettings(
        _transferPerms=manager_transfer_perms,
        _expiryBlock=current_block + 10  # Will expire in 10 blocks
    )
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Time travel past expiry
    boa.env.time_travel(blocks=20)
    
    # Manager should NOT be able to add pending payee (expired)
    assert not paymaster.canAddPendingPayee(user_wallet, charlie, alice)


def test_cannot_add_pending_payee_if_already_pending(createGlobalManagerSettings, createTransferPerms, createManagerSettings, createPayeeLimits, paymaster, user_wallet, user_wallet_config, alice, charlie, high_command):
    """Test that cannot add pending payee if already pending"""
    # Set global permissions to allow adding pending payees
    global_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_global_manager_settings = createGlobalManagerSettings(_transferPerms=global_transfer_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    # Add manager with permission to add pending payees
    manager_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_manager_settings = createManagerSettings(_transferPerms=manager_transfer_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # First, add a pending payee
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    paymaster.addPendingPayee(
        user_wallet,
        charlie,  # payee
        False,  # canPull
        2 * ONE_DAY_IN_BLOCKS,  # periodLength
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        createPayeeLimits(),  # unitLimits
        usd_limits,  # usdLimits
        sender=alice
    )
    
    # Now manager should NOT be able to add pending payee again
    assert not paymaster.canAddPendingPayee(user_wallet, charlie, alice)


