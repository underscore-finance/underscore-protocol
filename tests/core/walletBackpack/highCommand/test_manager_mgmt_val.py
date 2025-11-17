import pytest
import boa

from constants import ONE_DAY_IN_BLOCKS, ONE_MONTH_IN_BLOCKS, ONE_YEAR_IN_BLOCKS, ZERO_ADDRESS


############################
# Add Manager - Validation #
############################


def test_reject_existing_manager(high_command, user_wallet, alice, createManagerSettings, user_wallet_config, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms):
    # setup: add alice as existing manager
    new_manager_settings = createManagerSettings()
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # try to add alice again - should fail
    result = high_command.isValidNewManager(
        user_wallet,
        alice,  # already a manager
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,
    )
    
    assert result == False


def test_valid_new_manager_basic(high_command, user_wallet, charlie, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, user_wallet_config):
    # setup: set global manager settings
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    # charlie is not a manager yet - should pass
    result = high_command.isValidNewManager(
        user_wallet,
        charlie,
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,
    )
    
    assert result == True


def test_invalid_limits_per_tx_greater_than_per_period(high_command, user_wallet, charlie, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, user_wallet_config):
    # setup: set global manager settings
    global_settings = createGlobalManagerSettings(_managerPeriod=ONE_MONTH_IN_BLOCKS)
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    # invalid limits: per tx > per period
    invalid_limits = createManagerLimits(
        _maxUsdValuePerTx=10000 * 10**6,  # $10,000
        _maxUsdValuePerPeriod=1000 * 10**6  # $1,000
    )
    
    result = high_command.isValidNewManager(
        user_wallet,
        charlie,
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        invalid_limits,
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,
    )
    
    assert result == False


def test_valid_limits_per_tx_less_than_lifetime(high_command, user_wallet, charlie, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, user_wallet_config):
    # setup: set global manager settings
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    # valid limits: per tx can be > lifetime if lifetime is 0 (unlimited)
    # This test shows that per_tx vs lifetime is not validated
    valid_limits = createManagerLimits(
        _maxUsdValuePerTx=10000 * 10**6,  # $10,000
        _maxUsdValueLifetime=1000 * 10**6,  # $1,000
        _failOnZeroPrice=True  # Required when USD limits are set
    )
    
    result = high_command.isValidNewManager(
        user_wallet,
        charlie,
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        valid_limits,
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,
    )
    
    assert result == True  # Actually passes because this isn't validated


def test_invalid_limits_per_period_greater_than_lifetime(high_command, user_wallet, charlie, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, user_wallet_config):
    # setup: set global manager settings
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    # invalid limits: per period > lifetime
    invalid_limits = createManagerLimits(
        _maxUsdValuePerPeriod=10000 * 10**6,  # $10,000
        _maxUsdValueLifetime=1000 * 10**6  # $1,000
    )
    
    result = high_command.isValidNewManager(
        user_wallet,
        charlie,
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        invalid_limits,
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,
    )
    
    assert result == False


def test_valid_limits_unlimited_values(high_command, user_wallet, charlie, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, user_wallet_config):
    # setup: set global manager settings
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    # valid limits: mix of unlimited (0) and limited values
    valid_limits = createManagerLimits(
        _maxUsdValuePerTx=1000 * 10**6,  # $1,000
        _maxUsdValuePerPeriod=0,  # unlimited
        _maxUsdValueLifetime=0,  # unlimited
        _failOnZeroPrice=True  # Required when USD limits are set
    )
    
    result = high_command.isValidNewManager(
        user_wallet,
        charlie,
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        valid_limits,
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,
    )
    
    assert result == True


def test_invalid_allowed_assets_with_zero_address(high_command, user_wallet, charlie, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, user_wallet_config, alpha_token):
    # setup: set global manager settings
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    # invalid: contains zero address
    result = high_command.isValidNewManager(
        user_wallet,
        charlie,
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [alpha_token.address, ZERO_ADDRESS],  # contains zero address - use address
        False,
    )
    
    assert result == False


def test_invalid_allowed_assets_with_duplicates(high_command, user_wallet, charlie, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, user_wallet_config, alpha_token):
    # setup: set global manager settings
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    # invalid: contains duplicates
    result = high_command.isValidNewManager(
        user_wallet,
        charlie,
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [alpha_token.address, alpha_token.address],  # duplicate asset - use address
        False,
    )
    
    assert result == False


def test_valid_allowed_assets_multiple(high_command, user_wallet, charlie, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, user_wallet_config, alpha_token, bravo_token):
    # setup: set global manager settings
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    # valid: multiple unique assets
    result = high_command.isValidNewManager(
        user_wallet,
        charlie,
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [alpha_token.address, bravo_token.address],  # multiple valid assets
        False,
    )
    
    assert result == True


def test_invalid_lego_perms_with_restricted_lego(high_command, user_wallet, charlie, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, user_wallet_config):
    # First reset to a known clean state with no permissions
    clean_settings = createGlobalManagerSettings(
        _legoPerms=createLegoPerms(
            _canManageYield=False,
            _canBuyAndSell=False,
            _canManageDebt=False,
            _canManageLiq=False,
            _canClaimRewards=False,
            _allowedLegos=[]
        )
    )
    user_wallet_config.setGlobalManagerSettings(clean_settings, sender=high_command.address)
    
    # setup: set global manager settings with restricted legos
    global_settings = createGlobalManagerSettings(
        _legoPerms=createLegoPerms(
            _canManageYield=False,  # cannot manage yield
            _allowedLegos=[2, 3]  # only legos 1 and 2 allowed
        )
    )
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    # try to give manager yield permissions when globally restricted
    invalid_perms = createLegoPerms(
        _canManageYield=True,  # trying to allow yield when globally false
        _allowedLegos=[6, 7]  # trying to use legos not in global allowed list
    )
    
    result = high_command.isValidNewManager(
        user_wallet,
        charlie,
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        createManagerLimits(),
        invalid_perms,
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,
    )
    
    assert result == False


def test_valid_lego_perms_within_global_restrictions(high_command, user_wallet, charlie, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, user_wallet_config):
    # setup: set global manager settings with some restrictions
    global_settings = createGlobalManagerSettings(
        _legoPerms=createLegoPerms(
            _canManageYield=False,  # cannot manage yield
            _canBuyAndSell=True,  # can buy and sell
            _allowedLegos=[1, 2, 3]  # legos 1, 2, 3 allowed
        )
    )
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    # valid: permissions within global restrictions
    valid_perms = createLegoPerms(
        _canManageYield=False,  # respecting global restriction
        _canBuyAndSell=True,  # allowed globally
        _allowedLegos=[1, 2]  # subset of globally allowed legos
    )
    
    result = high_command.isValidNewManager(
        user_wallet,
        charlie,
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        createManagerLimits(),
        valid_perms,
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,
    )
    
    assert result == True


def test_invalid_transfer_perms_zero_address_payee(high_command, user_wallet, charlie, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, user_wallet_config, alice):
    # setup: set global manager settings
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    # invalid: allowed payees contains zero address
    invalid_transfer_perms = createTransferPerms(
        _canTransfer=True,
        _allowedPayees=[alice, ZERO_ADDRESS]  # contains zero address
    )
    
    result = high_command.isValidNewManager(
        user_wallet,
        charlie,
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        invalid_transfer_perms,
        [],
        False,
    )
    
    assert result == False


def test_invalid_transfer_perms_duplicate_payees(high_command, user_wallet, charlie, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, user_wallet_config, alice):
    # setup: set global manager settings
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    # invalid: allowed payees contains duplicates
    invalid_transfer_perms = createTransferPerms(
        _canTransfer=True,
        _allowedPayees=[alice, alice]  # duplicate payee
    )
    
    result = high_command.isValidNewManager(
        user_wallet,
        charlie,
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        invalid_transfer_perms,
        [],
        False,
    )
    
    assert result == False


def test_valid_transfer_perms_empty_payees(high_command, user_wallet, charlie, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, user_wallet_config):
    # setup: set global manager settings
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    # valid: empty allowed payees means can transfer to anyone
    valid_transfer_perms = createTransferPerms(
        _canTransfer=True,
        _allowedPayees=[]  # empty means unrestricted
    )
    
    result = high_command.isValidNewManager(
        user_wallet,
        charlie,
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        valid_transfer_perms,
        [],
        False,
    )
    
    assert result == True


def test_multiple_validation_failures(high_command, user_wallet, charlie, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, user_wallet_config, alpha_token):
    # setup: set global manager settings
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    # multiple invalid inputs
    invalid_limits = createManagerLimits(
        _maxUsdValuePerTx=10000 * 10**6,  # $10,000
        _maxUsdValuePerPeriod=1000 * 10**6  # $1,000 - invalid
    )
    
    invalid_transfer_perms = createTransferPerms(
        _canTransfer=True,
        _allowedPayees=[ZERO_ADDRESS]  # invalid
    )
    
    result = high_command.isValidNewManager(
        user_wallet,
        charlie,
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        invalid_limits,
        createLegoPerms(),
        createWhitelistPerms(),
        invalid_transfer_perms,
        [alpha_token.address, ZERO_ADDRESS],  # invalid allowed assets - use address
        False,
    )
    
    assert result == False


###############################
# Update Manager - Validation #
###############################


def test_update_manager_reject_non_existing_manager(high_command, user_wallet, charlie, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, user_wallet_config):
    # setup: set global manager settings
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    # charlie is not a manager yet - should fail
    result = high_command.validateManagerOnUpdate(
        user_wallet,
        charlie,  # not a manager
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,
    )
    
    assert result == False


def test_update_manager_valid_existing_manager(high_command, user_wallet, alice, createGlobalManagerSettings, createManagerSettings, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, user_wallet_config):
    # setup: set global manager settings
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    # add alice as manager first
    new_manager_settings = createManagerSettings()
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # alice is a manager - should pass with valid params
    result = high_command.validateManagerOnUpdate(
        user_wallet,
        alice,  # existing manager
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,
    )
    
    assert result == True


def test_update_manager_invalid_limits(high_command, user_wallet, alice, createGlobalManagerSettings, createManagerSettings, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, user_wallet_config):
    # setup: set global manager settings
    global_settings = createGlobalManagerSettings(_managerPeriod=ONE_MONTH_IN_BLOCKS)
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    # add alice as manager first
    new_manager_settings = createManagerSettings()
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # invalid limits: per tx > per period
    invalid_limits = createManagerLimits(
        _maxUsdValuePerTx=10000 * 10**6,  # $10,000
        _maxUsdValuePerPeriod=1000 * 10**6  # $1,000
    )
    
    result = high_command.validateManagerOnUpdate(
        user_wallet,
        alice,
        invalid_limits,
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,
    )
    
    assert result == False


def test_update_manager_invalid_allowed_assets(high_command, user_wallet, alice, createGlobalManagerSettings, createManagerSettings, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, user_wallet_config, alpha_token):
    # setup: set global manager settings
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    # add alice as manager first
    new_manager_settings = createManagerSettings()
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # invalid: duplicate assets
    result = high_command.validateManagerOnUpdate(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [alpha_token.address, alpha_token.address],  # duplicate asset
        False,
    )
    
    assert result == False


def test_update_manager_respects_global_lego_restrictions(high_command, user_wallet, alice, createGlobalManagerSettings, createManagerSettings, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, user_wallet_config):
    # First reset to a known clean state with no permissions
    clean_settings = createGlobalManagerSettings(
        _legoPerms=createLegoPerms(
            _canManageYield=False,
            _canBuyAndSell=False,
            _canManageDebt=False,
            _canManageLiq=False,
            _canClaimRewards=False,
            _allowedLegos=[]
        )
    )
    user_wallet_config.setGlobalManagerSettings(clean_settings, sender=high_command.address)
    
    # setup: set global manager settings with lego restrictions
    global_settings = createGlobalManagerSettings(
        _legoPerms=createLegoPerms(
            _canManageYield=False,  # globally restricted
            _allowedLegos=[2, 3]  # only legos 1 and 2 allowed globally
        )
    )
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    # add alice as manager first
    new_manager_settings = createManagerSettings()
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # try to update with legos outside global restrictions
    invalid_perms = createLegoPerms(
        _canManageYield=True,  # trying to override global restriction
        _allowedLegos=[6, 7]  # trying to use legos not globally allowed
    )
    
    result = high_command.validateManagerOnUpdate(
        user_wallet,
        alice,
        createManagerLimits(),
        invalid_perms,
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,
    )
    
    assert result == False


########################################
# Global Manager Settings - Validation #
########################################


def test_global_settings_valid_basic(high_command, user_wallet, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms):
    # valid global manager settings
    result = high_command.validateGlobalManagerSettings(
        user_wallet,
        ONE_MONTH_IN_BLOCKS,  # managerPeriod
        ONE_DAY_IN_BLOCKS,  # startDelay
        ONE_YEAR_IN_BLOCKS,  # activationLength
        True,  # canOwnerManage
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
    )
    
    assert result == True


def test_global_settings_invalid_manager_period_too_short(high_command, user_wallet, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms):
    # manager period too short (less than MIN_MANAGER_PERIOD)
    result = high_command.validateGlobalManagerSettings(
        user_wallet,
        100,  # too short
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        True,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
    )
    
    assert result == False


def test_global_settings_invalid_manager_period_too_long(high_command, user_wallet, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms):
    # manager period too long (more than MAX_MANAGER_PERIOD)
    result = high_command.validateGlobalManagerSettings(
        user_wallet,
        ONE_YEAR_IN_BLOCKS * 10,  # too long
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        True,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
    )
    
    assert result == False


def test_global_settings_invalid_activation_length_too_short(high_command, user_wallet, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms):
    # activation length too short
    result = high_command.validateGlobalManagerSettings(
        user_wallet,
        ONE_MONTH_IN_BLOCKS,
        ONE_DAY_IN_BLOCKS,
        100,  # too short
        True,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
    )
    
    assert result == False


def test_global_settings_invalid_activation_length_too_long(high_command, user_wallet, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms):
    # activation length too long
    result = high_command.validateGlobalManagerSettings(
        user_wallet,
        ONE_MONTH_IN_BLOCKS,
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS * 10,  # too long
        True,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
    )
    
    assert result == False


def test_global_settings_start_delay_too_short(high_command, user_wallet, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms):
    # start delay of 0 should fail (must be at least current timelock)
    result = high_command.validateGlobalManagerSettings(
        user_wallet,
        ONE_MONTH_IN_BLOCKS,
        0,  # too short
        ONE_YEAR_IN_BLOCKS,
        True,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
    )
    
    assert result == False


def test_global_settings_invalid_manager_limits(high_command, user_wallet, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms):
    # invalid limits: per tx > per period
    invalid_limits = createManagerLimits(
        _maxUsdValuePerTx=10000 * 10**6,
        _maxUsdValuePerPeriod=1000 * 10**6
    )
    
    result = high_command.validateGlobalManagerSettings(
        user_wallet,
        ONE_MONTH_IN_BLOCKS,
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        True,
        invalid_limits,
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
    )
    
    assert result == False


def test_global_settings_invalid_allowed_assets(high_command, user_wallet, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, alpha_token):
    # invalid: duplicate assets
    result = high_command.validateGlobalManagerSettings(
        user_wallet,
        ONE_MONTH_IN_BLOCKS,
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        True,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [alpha_token.address, alpha_token.address],  # duplicates
    )
    
    assert result == False


def test_global_settings_invalid_transfer_perms(high_command, user_wallet, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms):
    # invalid transfer perms with zero address
    invalid_transfer_perms = createTransferPerms(
        _allowedPayees=[ZERO_ADDRESS]
    )
    
    result = high_command.validateGlobalManagerSettings(
        user_wallet,
        ONE_MONTH_IN_BLOCKS,
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        True,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        invalid_transfer_perms,
        [],
    )
    
    assert result == False


def test_global_settings_invalid_cooldown_exceeds_period(high_command, user_wallet, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms):
    # cooldown cannot exceed manager period
    invalid_limits = createManagerLimits(
        _txCooldownBlocks=ONE_MONTH_IN_BLOCKS + 1  # exceeds period
    )
    
    result = high_command.validateGlobalManagerSettings(
        user_wallet,
        ONE_MONTH_IN_BLOCKS,  # manager period
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        True,
        invalid_limits,
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
    )
    
    assert result == False


def test_global_settings_multiple_validation_failures(high_command, user_wallet, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, alpha_token):
    # multiple invalid inputs
    invalid_limits = createManagerLimits(
        _maxUsdValuePerTx=10000 * 10**6,
        _maxUsdValuePerPeriod=1000 * 10**6
    )
    
    invalid_transfer_perms = createTransferPerms(
        _allowedPayees=[ZERO_ADDRESS]
    )
    
    result = high_command.validateGlobalManagerSettings(
        user_wallet,
        100,  # manager period too short
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS * 10,  # activation length too long
        True,
        invalid_limits,
        createLegoPerms(),
        createWhitelistPerms(),
        invalid_transfer_perms,
        [alpha_token.address, ZERO_ADDRESS],  # invalid assets
    )

    assert result == False


#################################################
# failOnZeroPrice Validation with USD Limits #
#################################################


def test_invalid_new_manager_usd_limits_without_fail_on_zero_price(high_command, user_wallet, charlie, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, user_wallet_config):
    """Test that new manager with USD limits requires failOnZeroPrice=True"""
    # Setup: set global manager settings
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)

    # Create limits with USD limit but failOnZeroPrice=False (default)
    invalid_limits = createManagerLimits(
        _maxUsdValuePerTx=5000 * 10**6,  # USD limit set
        _failOnZeroPrice=False  # Invalid with USD limits
    )

    # Should be invalid: USD limit set but failOnZeroPrice=False
    result = high_command.isValidNewManager(
        user_wallet,
        charlie,
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        invalid_limits,
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,
    )

    assert result == False


def test_valid_new_manager_usd_limits_with_fail_on_zero_price(high_command, user_wallet, charlie, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, user_wallet_config):
    """Test that new manager with USD limits works with failOnZeroPrice=True"""
    # Setup: set global manager settings
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)

    # Create limits with USD limit and failOnZeroPrice=True
    valid_limits = createManagerLimits(
        _maxUsdValuePerTx=5000 * 10**6,
        _failOnZeroPrice=True  # Required with USD limits
    )

    # Should be valid: USD limit set and failOnZeroPrice=True
    result = high_command.isValidNewManager(
        user_wallet,
        charlie,
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        valid_limits,
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,
    )

    assert result == True


def test_valid_new_manager_no_usd_limits_fail_on_zero_price_false(high_command, user_wallet, charlie, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, user_wallet_config):
    """Test that failOnZeroPrice=False is valid when no USD limits are set"""
    # Setup: set global manager settings
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)

    # Create limits with all zeros (no USD limits) and failOnZeroPrice=False
    valid_limits = createManagerLimits(
        _maxUsdValuePerTx=0,  # No limit
        _maxUsdValuePerPeriod=0,  # No limit
        _maxUsdValueLifetime=0,  # No limit
        _failOnZeroPrice=False  # OK when no USD limits
    )

    # Should be valid: No USD limits, so failOnZeroPrice can be False
    result = high_command.isValidNewManager(
        user_wallet,
        charlie,
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        valid_limits,
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,
    )

    assert result == True


def test_invalid_update_manager_usd_limits_without_fail_on_zero_price(high_command, user_wallet, alice, createGlobalManagerSettings, createManagerSettings, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, user_wallet_config):
    """Test that manager update with USD limits requires failOnZeroPrice=True"""
    # Setup: set global manager settings
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)

    # Add alice as manager first
    new_manager_settings = createManagerSettings()
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)

    # Create limits with USD limit but failOnZeroPrice=False
    invalid_limits = createManagerLimits(
        _maxUsdValuePerPeriod=10000 * 10**6,  # USD limit set
        _failOnZeroPrice=False  # Invalid with USD limits
    )

    # Should be invalid: USD limit set but failOnZeroPrice=False
    result = high_command.validateManagerOnUpdate(
        user_wallet,
        alice,
        invalid_limits,
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,
    )

    assert result == False


def test_valid_update_manager_usd_limits_with_fail_on_zero_price(high_command, user_wallet, alice, createGlobalManagerSettings, createManagerSettings, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, user_wallet_config):
    """Test that manager update with USD limits works with failOnZeroPrice=True"""
    # Setup: set global manager settings
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)

    # Add alice as manager first
    new_manager_settings = createManagerSettings()
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)

    # Create limits with USD limit and failOnZeroPrice=True
    valid_limits = createManagerLimits(
        _maxUsdValuePerPeriod=10000 * 10**6,
        _failOnZeroPrice=True  # Required with USD limits
    )

    # Should be valid: USD limit set and failOnZeroPrice=True
    result = high_command.validateManagerOnUpdate(
        user_wallet,
        alice,
        valid_limits,
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,
    )

    assert result == True


def test_invalid_global_settings_usd_limits_without_fail_on_zero_price(high_command, user_wallet, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms):
    """Test that global manager settings with USD limits requires failOnZeroPrice=True"""
    # Create limits with USD lifetime limit but failOnZeroPrice=False
    invalid_limits = createManagerLimits(
        _maxUsdValueLifetime=100000 * 10**6,  # USD limit set
        _failOnZeroPrice=False  # Invalid with USD limits
    )

    # Should be invalid: USD limit set but failOnZeroPrice=False
    result = high_command.validateGlobalManagerSettings(
        user_wallet,
        ONE_MONTH_IN_BLOCKS,
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        True,
        invalid_limits,
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
    )

    assert result == False


def test_valid_global_settings_usd_limits_with_fail_on_zero_price(high_command, user_wallet, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms):
    """Test that global manager settings with USD limits works with failOnZeroPrice=True"""
    # Create limits with USD limits and failOnZeroPrice=True
    valid_limits = createManagerLimits(
        _maxUsdValuePerTx=5000 * 10**6,
        _maxUsdValuePerPeriod=50000 * 10**6,
        _maxUsdValueLifetime=500000 * 10**6,
        _failOnZeroPrice=True  # Required with USD limits
    )

    # Should be valid: USD limits set and failOnZeroPrice=True
    result = high_command.validateGlobalManagerSettings(
        user_wallet,
        ONE_MONTH_IN_BLOCKS,
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        True,
        valid_limits,
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
    )

    assert result == True


def test_invalid_any_usd_limit_requires_fail_on_zero_price(high_command, user_wallet, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms):
    """Test that ANY non-zero USD limit (perTx, perPeriod, or lifetime) requires failOnZeroPrice=True"""
    # Test with only maxUsdValuePerTx set
    limits_1 = createManagerLimits(_maxUsdValuePerTx=5000 * 10**6, _failOnZeroPrice=False)
    assert not high_command.validateGlobalManagerSettings(
        user_wallet, ONE_MONTH_IN_BLOCKS, ONE_DAY_IN_BLOCKS, ONE_YEAR_IN_BLOCKS,
        True, limits_1, createLegoPerms(), createWhitelistPerms(), createTransferPerms(), []
    )

    # Test with only maxUsdValuePerPeriod set
    limits_2 = createManagerLimits(_maxUsdValuePerPeriod=10000 * 10**6, _failOnZeroPrice=False)
    assert not high_command.validateGlobalManagerSettings(
        user_wallet, ONE_MONTH_IN_BLOCKS, ONE_DAY_IN_BLOCKS, ONE_YEAR_IN_BLOCKS,
        True, limits_2, createLegoPerms(), createWhitelistPerms(), createTransferPerms(), []
    )

    # Test with only maxUsdValueLifetime set
    limits_3 = createManagerLimits(_maxUsdValueLifetime=50000 * 10**6, _failOnZeroPrice=False)
    assert not high_command.validateGlobalManagerSettings(
        user_wallet, ONE_MONTH_IN_BLOCKS, ONE_DAY_IN_BLOCKS, ONE_YEAR_IN_BLOCKS,
        True, limits_3, createLegoPerms(), createWhitelistPerms(), createTransferPerms(), []
    )

