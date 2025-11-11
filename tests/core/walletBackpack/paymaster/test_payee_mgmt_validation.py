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
        False,  # _canPayOwner
        True  # _canPull
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
        True,  # _canPayOwner
        True  # _canPull
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
        False,  # _canPayOwner
        True  # _canPull
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
        False,  # _canPayOwner
        True  # _canPull
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
        False,  # _canPayOwner
        True  # _canPull
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
        False,  # _canPayOwner
        True  # _canPull
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
        False,  # _canPayOwner
        True  # _canPull
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
        False,  # _canPayOwner
        True  # _canPull
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
        False,  # _canPayOwner
        True  # _canPull
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
        False,  # _canPayOwner
        True  # _canPull
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
        False,  # _canPayOwner
        True  # _canPull
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
        False,  # _canPayOwner
        True  # _canPull
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
        True,  # _canPayOwner
        True  # _canPull
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
        False,  # _canPayOwner
        True  # _canPull
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


########################
# New Payee Validation #
########################


def test_valid_new_payee_basic(paymaster, user_wallet, createPayeeLimits, alice, fork):
    """Test valid new payee with basic parameters"""
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    # Should be valid
    assert paymaster.isValidNewPayee(
        user_wallet,
        alice,  # payee
        False,  # canPull
        2 * ONE_DAY_IN_BLOCKS,  # periodLength
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        createPayeeLimits(),  # unitLimits
        usd_limits  # usdLimits
    )


def test_invalid_new_payee_zero_address(paymaster, user_wallet, createPayeeLimits):
    """Test invalid new payee with zero address"""
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    
    # Zero address should be invalid
    assert not paymaster.isValidNewPayee(
        user_wallet,
        ZERO_ADDRESS,  # payee is zero address
        False,  # canPull
        2 * ONE_DAY_IN_BLOCKS,  # periodLength
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        createPayeeLimits(),  # unitLimits
        usd_limits  # usdLimits
    )


def test_invalid_new_payee_is_owner(paymaster, user_wallet, createPayeeLimits, bob):
    """Test invalid new payee when payee is owner"""
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    
    # Owner should not be valid as payee
    assert not paymaster.isValidNewPayee(
        user_wallet,
        bob,  # payee is owner
        False,  # canPull
        2 * ONE_DAY_IN_BLOCKS,  # periodLength
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        createPayeeLimits(),  # unitLimits
        usd_limits  # usdLimits
    )


def test_invalid_new_payee_is_wallet(paymaster, user_wallet, createPayeeLimits):
    """Test invalid new payee when payee is wallet address"""
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    
    # Wallet address should not be valid as payee
    assert not paymaster.isValidNewPayee(
        user_wallet,
        user_wallet.address,  # payee is wallet itself
        False,  # canPull
        2 * ONE_DAY_IN_BLOCKS,  # periodLength
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        createPayeeLimits(),  # unitLimits
        usd_limits  # usdLimits
    )


def test_invalid_new_payee_already_exists(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createPayeeSettings, alice):
    """Test invalid new payee when payee already exists"""
    # First add alice as a payee
    new_payee_settings = createPayeeSettings()
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    
    # Should be invalid since alice is already a payee
    assert not paymaster.isValidNewPayee(
        user_wallet,
        alice,  # payee already exists
        False,  # canPull
        2 * ONE_DAY_IN_BLOCKS,  # periodLength
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        createPayeeLimits(),  # unitLimits
        usd_limits  # usdLimits
    )


def test_invalid_new_payee_is_whitelisted(paymaster, user_wallet, user_wallet_config, migrator, createPayeeLimits, alice):
    """Test invalid new payee when payee is already whitelisted"""
    # Add alice to whitelist using the shortcut
    user_wallet_config.addWhitelistAddrViaMigrator(alice, sender=migrator.address)
    
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    
    # Should be invalid since alice is whitelisted
    assert not paymaster.isValidNewPayee(
        user_wallet,
        alice,  # payee is whitelisted
        False,  # canPull
        2 * ONE_DAY_IN_BLOCKS,  # periodLength
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        createPayeeLimits(),  # unitLimits
        usd_limits  # usdLimits
    )


def test_invalid_new_payee_has_active_cheque(
    paymaster, user_wallet, user_wallet_config, bob, alice, alpha_token,
    createPayeeLimits, cheque_book, mock_ripe
):
    """Test cross-validation: payee cannot be added if they have an active cheque"""
    # First, set up cheque settings
    ONE_MONTH_IN_BLOCKS = 30 * ONE_DAY_IN_BLOCKS
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
        True,  # canBePulled
        sender=bob
    )

    # Set price for the asset
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)

    # Create a cheque for alice
    ONE_WEEK_IN_BLOCKS = ONE_DAY_IN_BLOCKS * 7
    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        50 * EIGHTEEN_DECIMALS,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,
        True,
        sender=bob
    )

    # Verify alice has an active cheque
    cheque = user_wallet_config.cheques(alice)
    assert cheque[10] == True  # active flag

    # Now try to add alice as a payee - should fail
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)

    assert not paymaster.isValidNewPayee(
        user_wallet,
        alice,  # payee has active cheque (INVALID)
        False,  # canPull
        2 * ONE_DAY_IN_BLOCKS,  # periodLength
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        createPayeeLimits(),  # unitLimits
        usd_limits  # usdLimits
    )


def test_valid_new_payee_after_cheque_cancelled(
    paymaster, user_wallet, user_wallet_config, bob, alice, alpha_token,
    createPayeeLimits, cheque_book, mock_ripe
):
    """Test edge case: payee CAN be added after their cheque is cancelled/inactive"""
    # First, set up cheque settings
    ONE_MONTH_IN_BLOCKS = 30 * ONE_DAY_IN_BLOCKS
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
        True,  # canBePulled
        sender=bob
    )

    # Set price for the asset
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)

    # Create a cheque for alice
    ONE_WEEK_IN_BLOCKS = ONE_DAY_IN_BLOCKS * 7
    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        50 * EIGHTEEN_DECIMALS,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,
        True,
        sender=bob
    )

    # Verify alice has an active cheque
    cheque = user_wallet_config.cheques(alice)
    assert cheque[10] == True  # active flag

    # Cancel the cheque
    cheque_book.cancelCheque(user_wallet.address, alice, sender=bob)

    # Verify cheque is now inactive
    cheque_after = user_wallet_config.cheques(alice)
    assert cheque_after[10] == False  # active flag should be False

    # Now adding alice as a payee should succeed (cheque is inactive)
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)

    assert paymaster.isValidNewPayee(
        user_wallet,
        alice,  # payee no longer has active cheque (VALID)
        False,  # canPull
        2 * ONE_DAY_IN_BLOCKS,  # periodLength
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        createPayeeLimits(),  # unitLimits
        usd_limits  # usdLimits
    )


def test_invalid_new_payee_period_too_short(paymaster, user_wallet, createPayeeLimits, alice, fork):
    """Test invalid new payee with period length too short"""
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    
    # Period length below minimum
    assert not paymaster.isValidNewPayee(
        user_wallet,
        alice,  # payee
        False,  # canPull
        PARAMS[fork]["PAYMASTER_MIN_PAYEE_PERIOD"] - 1,  # periodLength too short
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        createPayeeLimits(),  # unitLimits
        usd_limits  # usdLimits
    )


def test_invalid_new_payee_period_too_long(paymaster, user_wallet, createPayeeLimits, alice, fork):
    """Test invalid new payee with period length too long"""
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    
    # Period length above maximum
    assert not paymaster.isValidNewPayee(
        user_wallet,
        alice,  # payee
        False,  # canPull
        PARAMS[fork]["PAYMASTER_MAX_PAYEE_PERIOD"] + 1,  # periodLength too long
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        createPayeeLimits(),  # unitLimits
        usd_limits  # usdLimits
    )


def test_invalid_new_payee_cooldown_exceeds_period(paymaster, user_wallet, createPayeeLimits, alice):
    """Test invalid new payee with cooldown exceeding period"""
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    
    period_length = 2 * ONE_DAY_IN_BLOCKS
    
    # Cooldown exceeds period length
    assert not paymaster.isValidNewPayee(
        user_wallet,
        alice,  # payee
        False,  # canPull
        period_length,  # periodLength
        10,  # maxNumTxsPerPeriod
        period_length + 1,  # txCooldownBlocks exceeds period
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        createPayeeLimits(),  # unitLimits
        usd_limits  # usdLimits
    )


def test_invalid_new_payee_pull_without_limits(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice):
    """Test invalid new payee with pull enabled but no limits"""
    # Set global payee settings with canPull=True to test the limits requirement
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Create limits with all zeros (no limits)
    unit_limits = createPayeeLimits(_perTxCap=0, _perPeriodCap=0, _lifetimeCap=0)
    usd_limits = createPayeeLimits(_perTxCap=0, _perPeriodCap=0, _lifetimeCap=0)
    
    # Pull payee must have at least one limit
    assert not paymaster.isValidNewPayee(
        user_wallet,
        alice,  # payee
        True,  # canPull enabled
        2 * ONE_DAY_IN_BLOCKS,  # periodLength
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        unit_limits,  # unitLimits (all zeros)
        usd_limits  # usdLimits (all zeros)
    )


def test_valid_new_payee_pull_with_unit_limits(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice):
    """Test valid new payee with pull enabled and unit limits"""
    # Set global payee settings with canPull=True
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Create unit limits only
    unit_limits = createPayeeLimits(_perTxCap=100, _perPeriodCap=1000, _lifetimeCap=10000)
    usd_limits = createPayeeLimits(_perTxCap=0, _perPeriodCap=0, _lifetimeCap=0)
    
    # Should be valid with unit limits
    assert paymaster.isValidNewPayee(
        user_wallet,
        alice,  # payee
        True,  # canPull enabled
        2 * ONE_DAY_IN_BLOCKS,  # periodLength
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        unit_limits,  # unitLimits
        usd_limits  # usdLimits (all zeros)
    )


def test_valid_new_payee_pull_with_usd_limits(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice):
    """Test valid new payee with pull enabled and USD limits"""
    # Set global payee settings with canPull=True
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Create USD limits only
    unit_limits = createPayeeLimits(_perTxCap=0, _perPeriodCap=0, _lifetimeCap=0)
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS, _perPeriodCap=10000 * EIGHTEEN_DECIMALS, _lifetimeCap=0)
    
    # Should be valid with USD limits
    assert paymaster.isValidNewPayee(
        user_wallet,
        alice,  # payee
        True,  # canPull enabled
        2 * ONE_DAY_IN_BLOCKS,  # periodLength
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        unit_limits,  # unitLimits (all zeros)
        usd_limits  # usdLimits
    )


def test_invalid_new_payee_only_primary_asset_without_asset(paymaster, user_wallet, createPayeeLimits, alice):
    """Test invalid new payee with onlyPrimaryAsset but no primaryAsset"""
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    
    # onlyPrimaryAsset=true but primaryAsset is zero address
    assert not paymaster.isValidNewPayee(
        user_wallet,
        alice,  # payee
        False,  # canPull
        2 * ONE_DAY_IN_BLOCKS,  # periodLength
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset is zero
        True,  # onlyPrimaryAsset is true
        createPayeeLimits(),  # unitLimits
        usd_limits  # usdLimits
    )


def test_valid_new_payee_with_primary_asset(paymaster, user_wallet, createPayeeLimits, alice, alpha_token):
    """Test valid new payee with primary asset"""
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    
    # Should be valid with proper primary asset
    assert paymaster.isValidNewPayee(
        user_wallet,
        alice,  # payee
        False,  # canPull
        2 * ONE_DAY_IN_BLOCKS,  # periodLength
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        alpha_token.address,  # primaryAsset
        True,  # onlyPrimaryAsset
        createPayeeLimits(),  # unitLimits
        usd_limits  # usdLimits
    )


def test_new_payee_uses_global_default_period_length(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, fork):
    """Test that period length 0 uses global default"""
    # Set global payee settings with default period length
    global_settings = createGlobalPayeeSettings(_defaultPeriodLength=3 * ONE_DAY_IN_BLOCKS)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    
    # Should be valid using global default period length
    assert paymaster.isValidNewPayee(
        user_wallet,
        alice,  # payee
        False,  # canPull
        0,  # periodLength = 0 means use global default
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        createPayeeLimits(),  # unitLimits
        usd_limits  # usdLimits
    )


def test_new_payee_custom_start_delay_and_activation_length(paymaster, user_wallet, createPayeeLimits, alice, fork):
    """Test new payee with custom start delay and activation length"""
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    
    # Should be valid with custom start delay and activation length
    assert paymaster.isValidNewPayee(
        user_wallet,
        alice,  # payee
        False,  # canPull
        2 * ONE_DAY_IN_BLOCKS,  # periodLength
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        createPayeeLimits(),  # unitLimits
        usd_limits,  # usdLimits
        PARAMS[fork]["PAYMASTER_MAX_START_DELAY"],  # startDelay
        2 * ONE_DAY_IN_BLOCKS  # activationLength
    )


###########################
# Update Payee Validation #
###########################


def test_valid_payee_update_basic(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createPayeeSettings, createGlobalPayeeSettings, alice):
    """Test valid payee update with basic parameters"""
    # Set global payee settings with canPull=True to allow the update
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # First add an existing payee
    initial_settings = createPayeeSettings(
        _canPull=False,
        _periodLength=2 * ONE_DAY_IN_BLOCKS,
        _maxNumTxsPerPeriod=5,
        _txCooldownBlocks=0,
        _failOnZeroPrice=True,
        _primaryAsset=ZERO_ADDRESS,
        _onlyPrimaryAsset=False,
        _unitLimits=createPayeeLimits(),
        _usdLimits=createPayeeLimits(_perTxCap=500 * EIGHTEEN_DECIMALS)
    )
    user_wallet_config.addPayee(alice, initial_settings, sender=paymaster.address)
    
    # Update with new valid parameters
    new_usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    assert paymaster.isValidPayeeUpdate(
        user_wallet,
        alice,  # payee
        True,  # canPull (changed)
        3 * ONE_DAY_IN_BLOCKS,  # periodLength (changed)
        10,  # maxNumTxsPerPeriod (changed)
        100,  # txCooldownBlocks (changed)
        False,  # failOnZeroPrice (changed)
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        createPayeeLimits(),  # unitLimits
        new_usd_limits  # usdLimits (changed)
    )


def test_invalid_payee_update_not_registered(paymaster, user_wallet, createPayeeLimits, alice):
    """Test update fails if payee is not registered"""
    # Alice is not a registered payee
    assert not paymaster.isValidPayeeUpdate(
        user_wallet,
        alice,  # payee (not registered)
        False,  # canPull
        2 * ONE_DAY_IN_BLOCKS,  # periodLength
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        createPayeeLimits(),  # unitLimits
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)  # usdLimits
    )


def test_invalid_payee_update_period_too_short(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createPayeeSettings, alice, fork):
    """Test update fails with period length below minimum"""
    # First add an existing payee
    initial_settings = createPayeeSettings()
    user_wallet_config.addPayee(alice, initial_settings, sender=paymaster.address)
    
    # Try to update with invalid period length
    assert not paymaster.isValidPayeeUpdate(
        user_wallet,
        alice,  # payee
        False,  # canPull
        PARAMS[fork]["PAYMASTER_MIN_PAYEE_PERIOD"] - 1,  # periodLength (too short)
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        createPayeeLimits(),  # unitLimits
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)  # usdLimits
    )


def test_invalid_payee_update_period_too_long(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createPayeeSettings, alice, fork):
    """Test update fails with period length above maximum"""
    # First add an existing payee
    initial_settings = createPayeeSettings()
    user_wallet_config.addPayee(alice, initial_settings, sender=paymaster.address)
    
    # Try to update with invalid period length
    assert not paymaster.isValidPayeeUpdate(
        user_wallet,
        alice,  # payee
        False,  # canPull
        PARAMS[fork]["PAYMASTER_MAX_PAYEE_PERIOD"] + 1,  # periodLength (too long)
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        createPayeeLimits(),  # unitLimits
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)  # usdLimits
    )


def test_invalid_payee_update_cooldown_exceeds_period(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createPayeeSettings, alice):
    """Test update fails when cooldown exceeds period length"""
    # First add an existing payee
    initial_settings = createPayeeSettings()
    user_wallet_config.addPayee(alice, initial_settings, sender=paymaster.address)
    
    period_length = 2 * ONE_DAY_IN_BLOCKS
    
    # Try to update with cooldown > period
    assert not paymaster.isValidPayeeUpdate(
        user_wallet,
        alice,  # payee
        False,  # canPull
        period_length,  # periodLength
        10,  # maxNumTxsPerPeriod
        period_length + 1,  # txCooldownBlocks (exceeds period)
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        createPayeeLimits(),  # unitLimits
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)  # usdLimits
    )


def test_valid_payee_update_cooldown_equals_period(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createPayeeSettings, alice):
    """Test update succeeds when cooldown equals period length"""
    # First add an existing payee
    initial_settings = createPayeeSettings()
    user_wallet_config.addPayee(alice, initial_settings, sender=paymaster.address)
    
    period_length = 2 * ONE_DAY_IN_BLOCKS
    
    # Should be valid when cooldown = period
    assert paymaster.isValidPayeeUpdate(
        user_wallet,
        alice,  # payee
        False,  # canPull
        period_length,  # periodLength
        10,  # maxNumTxsPerPeriod
        period_length,  # txCooldownBlocks (equals period)
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        createPayeeLimits(),  # unitLimits
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)  # usdLimits
    )


def test_invalid_payee_update_pull_without_limits(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createPayeeSettings, createGlobalPayeeSettings, alice):
    """Test update fails for pull payee without limits"""
    # Set global payee settings with canPull=True to test the limits requirement
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # First add an existing payee
    initial_settings = createPayeeSettings()
    user_wallet_config.addPayee(alice, initial_settings, sender=paymaster.address)
    
    # Try to update as pull payee with no limits
    assert not paymaster.isValidPayeeUpdate(
        user_wallet,
        alice,  # payee
        True,  # canPull (requires limits)
        2 * ONE_DAY_IN_BLOCKS,  # periodLength
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        createPayeeLimits(),  # unitLimits (no limits)
        createPayeeLimits()  # usdLimits (no limits)
    )


def test_valid_payee_update_pull_with_unit_limits(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createPayeeSettings, createGlobalPayeeSettings, alice, alpha_token):
    """Test update succeeds for pull payee with unit limits"""
    # Set global payee settings with canPull=True
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # First add an existing payee
    initial_settings = createPayeeSettings()
    user_wallet_config.addPayee(alice, initial_settings, sender=paymaster.address)
    
    # Update as pull payee with unit limits
    unit_limits = createPayeeLimits(
        _perTxCap=10,
        _perPeriodCap=100,
        _lifetimeCap=1000
    )
    
    assert paymaster.isValidPayeeUpdate(
        user_wallet,
        alice,  # payee
        True,  # canPull
        2 * ONE_DAY_IN_BLOCKS,  # periodLength
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        alpha_token,  # primaryAsset (required for unit limits)
        True,  # onlyPrimaryAsset
        unit_limits,  # unitLimits
        createPayeeLimits()  # usdLimits
    )


def test_valid_payee_update_pull_with_usd_limits(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createPayeeSettings, createGlobalPayeeSettings, alice):
    """Test update succeeds for pull payee with USD limits"""
    # Set global payee settings with canPull=True
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # First add an existing payee
    initial_settings = createPayeeSettings()
    user_wallet_config.addPayee(alice, initial_settings, sender=paymaster.address)
    
    # Update as pull payee with USD limits
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    assert paymaster.isValidPayeeUpdate(
        user_wallet,
        alice,  # payee
        True,  # canPull
        2 * ONE_DAY_IN_BLOCKS,  # periodLength
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        createPayeeLimits(),  # unitLimits
        usd_limits  # usdLimits
    )


def test_valid_payee_update_primary_asset_not_only(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createPayeeSettings, alice, alpha_token):
    """Test update succeeds with primary asset and onlyPrimaryAsset false"""
    # First add an existing payee
    initial_settings = createPayeeSettings()
    user_wallet_config.addPayee(alice, initial_settings, sender=paymaster.address)
    
    # Should succeed - primary asset can be set without onlyPrimaryAsset
    assert paymaster.isValidPayeeUpdate(
        user_wallet,
        alice,  # payee
        False,  # canPull
        2 * ONE_DAY_IN_BLOCKS,  # periodLength
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        alpha_token,  # primaryAsset (non-zero)
        False,  # onlyPrimaryAsset (can be false)
        createPayeeLimits(),  # unitLimits
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)  # usdLimits
    )


def test_invalid_payee_update_only_primary_without_asset(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createPayeeSettings, alice):
    """Test update fails with onlyPrimaryAsset but no primary asset"""
    # First add an existing payee
    initial_settings = createPayeeSettings()
    user_wallet_config.addPayee(alice, initial_settings, sender=paymaster.address)
    
    # Should fail - onlyPrimaryAsset requires primary asset
    assert not paymaster.isValidPayeeUpdate(
        user_wallet,
        alice,  # payee
        False,  # canPull
        2 * ONE_DAY_IN_BLOCKS,  # periodLength
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset (zero)
        True,  # onlyPrimaryAsset (requires non-zero asset)
        createPayeeLimits(),  # unitLimits
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)  # usdLimits
    )


def test_valid_payee_update_change_all_parameters(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createPayeeSettings, createGlobalPayeeSettings, alice, alpha_token, bravo_token, fork):
    """Test update succeeds when changing all parameters"""
    # Set global payee settings with canPull=True to allow the update
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # First add an existing payee with specific settings
    initial_settings = createPayeeSettings(
        _canPull=False,
        _periodLength=PARAMS[fork]["PAYMASTER_MIN_PAYEE_PERIOD"],
        _maxNumTxsPerPeriod=1,
        _txCooldownBlocks=0,
        _failOnZeroPrice=False,
        _primaryAsset=alpha_token,
        _onlyPrimaryAsset=True,
        _unitLimits=createPayeeLimits(_perTxCap=1),
        _usdLimits=createPayeeLimits()
    )
    user_wallet_config.addPayee(alice, initial_settings, sender=paymaster.address)
    
    # Update with completely different parameters
    new_unit_limits = createPayeeLimits(
        _perTxCap=100,
        _perPeriodCap=1000,
        _lifetimeCap=10000
    )
    new_usd_limits = createPayeeLimits(
        _perTxCap=5000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=50000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=500000 * EIGHTEEN_DECIMALS
    )
    
    assert paymaster.isValidPayeeUpdate(
        user_wallet,
        alice,  # payee
        True,  # canPull (changed to true)
        PARAMS[fork]["PAYMASTER_MAX_PAYEE_PERIOD"],  # periodLength (changed to max)
        100,  # maxNumTxsPerPeriod (changed)
        ONE_DAY_IN_BLOCKS,  # txCooldownBlocks (changed)
        True,  # failOnZeroPrice (changed to true)
        bravo_token,  # primaryAsset (changed token)
        True,  # onlyPrimaryAsset
        new_unit_limits,  # unitLimits (changed)
        new_usd_limits  # usdLimits (changed)
    )


def test_payee_update_maintains_original_start_expiry(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createPayeeSettings, alice):
    """Test that payee update maintains original start/expiry blocks"""
    # Add payee with specific start/expiry
    current_block = boa.env.evm.patch.block_number
    initial_settings = createPayeeSettings(
        _startBlock=current_block + 100,
        _expiryBlock=current_block + 10000
    )
    user_wallet_config.addPayee(alice, initial_settings, sender=paymaster.address)
    
    # Update should be valid regardless of original start/expiry
    assert paymaster.isValidPayeeUpdate(
        user_wallet,
        alice,  # payee
        False,  # canPull
        3 * ONE_DAY_IN_BLOCKS,  # periodLength (changed)
        20,  # maxNumTxsPerPeriod (changed)
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        createPayeeLimits(),  # unitLimits
        createPayeeLimits(_perTxCap=2000 * EIGHTEEN_DECIMALS)  # usdLimits
    )


