"""
Test global payee settings functionality in Paymaster
"""
import pytest
import boa

from contracts.core import Paymaster
from contracts.core.userWallet import UserWallet, UserWalletConfig
from constants import EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ONE_MONTH_IN_BLOCKS, ONE_YEAR_IN_BLOCKS, ZERO_ADDRESS
from conf_utils import filter_logs


@pytest.fixture(scope="module")
def setup_wallet(setUserWalletConfig, setManagerConfig, setPayeeConfig, hatchery, bob):
    """Setup user wallet with config"""
    setUserWalletConfig()
    setManagerConfig()
    setPayeeConfig()
    
    wallet_addr = hatchery.createUserWallet(sender=bob)
    assert wallet_addr != ZERO_ADDRESS
    return UserWallet.at(wallet_addr)


@pytest.fixture(scope="module")
def setup_contracts(setup_wallet, paymaster, alpha_token, bravo_token, bob, alice, governance):
    """Setup contracts and basic configuration"""
    user_wallet = setup_wallet
    wallet_config_addr = user_wallet.walletConfig()
    wallet_config = UserWalletConfig.at(wallet_config_addr)
    owner = bob
    
    # Fund wallet for testing
    alpha_token.transfer(user_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    bravo_token.transfer(user_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    return {
        'wallet': user_wallet,
        'wallet_config': wallet_config,
        'paymaster': paymaster,
        'owner': owner,
        'non_owner': alice,
        'alpha_token': alpha_token,
        'bravo_token': bravo_token
    }


# Test setting global payee settings


def test_set_global_payee_settings_basic(setup_contracts, createPayeeLimits):
    """Test basic setting of global payee settings"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    
    # Create USD limits
    usd_limits = createPayeeLimits(
        _perTxCap=500 * EIGHTEEN_DECIMALS,
        _perPeriodCap=5000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=50000 * EIGHTEEN_DECIMALS
    )
    
    # Set global settings
    tx = paymaster.setGlobalPayeeSettings(
        wallet.address,
        ONE_DAY_IN_BLOCKS,  # defaultPeriodLength
        100,  # startDelay
        ONE_YEAR_IN_BLOCKS,  # activationLength
        20,  # maxNumTxsPerPeriod
        50,  # txCooldownBlocks
        True,  # failOnZeroPrice
        usd_limits,
        False,  # canPayOwner
        sender=owner
    )
    
    # Check events
    events = filter_logs(paymaster, "GlobalPayeeSettingsModified")
    assert len(events) == 1
    event = events[0]
    assert event.user == wallet.address
    assert event.defaultPeriodLength == ONE_DAY_IN_BLOCKS
    assert event.startDelay == 100
    assert event.activationLength == ONE_YEAR_IN_BLOCKS
    assert event.maxNumTxsPerPeriod == 20
    assert event.txCooldownBlocks == 50
    assert event.failOnZeroPrice == True
    assert event.canPayOwner == False
    assert event.usdPerTxCap == usd_limits[0]
    assert event.usdPerPeriodCap == usd_limits[1]
    assert event.usdLifetimeCap == usd_limits[2]
    
    # Verify settings in UserWalletConfig
    global_settings = wallet_config.globalPayeeSettings()
    assert global_settings[0] == ONE_DAY_IN_BLOCKS  # defaultPeriodLength
    assert global_settings[1] == 100  # startDelay
    assert global_settings[2] == ONE_YEAR_IN_BLOCKS  # activationLength
    assert global_settings[3] == 20  # maxNumTxsPerPeriod
    assert global_settings[4] == 50  # txCooldownBlocks
    assert global_settings[5] == True  # failOnZeroPrice
    assert global_settings[7] == False  # canPayOwner
    
    # Check USD limits
    assert global_settings[6][0] == usd_limits[0]  # perTxCap
    assert global_settings[6][1] == usd_limits[1]  # perPeriodCap
    assert global_settings[6][2] == usd_limits[2]  # lifetimeCap


def test_set_global_payee_settings_permissions(setup_contracts, createPayeeLimits):
    """Test only owner can set global payee settings"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    non_owner = ctx['non_owner']
    
    usd_limits = createPayeeLimits()
    
    # Non-owner cannot set global settings
    with boa.reverts("no perms"):
        paymaster.setGlobalPayeeSettings(
            wallet.address,
            ONE_DAY_IN_BLOCKS,
            100,
            ONE_YEAR_IN_BLOCKS,
            20,
            50,
            True,
            usd_limits,
            False,
            sender=non_owner
        )


def test_global_settings_validation(setup_contracts, createPayeeLimits):
    """Test validation of global payee settings"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    
    usd_limits = createPayeeLimits()
    
    # Test invalid period length (too short)
    min_period = paymaster.MIN_PAYEE_PERIOD()
    
    with boa.reverts("invalid settings"):
        paymaster.setGlobalPayeeSettings(
            wallet.address,
            min_period - 1,  # Too short
            100,
            ONE_YEAR_IN_BLOCKS,
            20,
            50,
            True,
            usd_limits,
            False,
            sender=owner
        )
    
    # Test invalid period length (too long)
    max_period = paymaster.MAX_PAYEE_PERIOD()
    
    with boa.reverts("invalid settings"):
        paymaster.setGlobalPayeeSettings(
            wallet.address,
            max_period + 1,  # Too long
            100,
            ONE_YEAR_IN_BLOCKS,
            20,
            50,
            True,
            usd_limits,
            False,
            sender=owner
        )
    
    # Test invalid activation length (too short)
    min_activation = paymaster.MIN_ACTIVATION_LENGTH()
    
    with boa.reverts("invalid settings"):
        paymaster.setGlobalPayeeSettings(
            wallet.address,
            ONE_DAY_IN_BLOCKS,
            100,
            min_activation - 1,  # Too short
            20,
            50,
            True,
            usd_limits,
            False,
            sender=owner
        )
    
    # Test invalid activation length (too long)
    max_activation = paymaster.MAX_ACTIVATION_LENGTH()
    
    with boa.reverts("invalid settings"):
        paymaster.setGlobalPayeeSettings(
            wallet.address,
            ONE_DAY_IN_BLOCKS,
            100,
            max_activation + 1,  # Too long
            20,
            50,
            True,
            usd_limits,
            False,
            sender=owner
        )
    
    # Test start delay less than timelock
    timelock = wallet_config.timeLock()
    
    with boa.reverts("invalid settings"):
        paymaster.setGlobalPayeeSettings(
            wallet.address,
            ONE_DAY_IN_BLOCKS,
            timelock - 1,  # Less than timelock
            ONE_YEAR_IN_BLOCKS,
            20,
            50,
            True,
            usd_limits,
            False,
            sender=owner
        )
    
    # Test cooldown exceeds period
    with boa.reverts("invalid settings"):
        paymaster.setGlobalPayeeSettings(
            wallet.address,
            ONE_DAY_IN_BLOCKS,
            100,
            ONE_YEAR_IN_BLOCKS,
            20,
            ONE_DAY_IN_BLOCKS + 1,  # Cooldown exceeds period
            True,
            usd_limits,
            False,
            sender=owner
        )
    
    # Test invalid limits
    invalid_limits = createPayeeLimits(
        _perTxCap=200 * EIGHTEEN_DECIMALS,
        _perPeriodCap=100 * EIGHTEEN_DECIMALS  # Less than per-tx
    )
    
    with boa.reverts("invalid settings"):
        paymaster.setGlobalPayeeSettings(
            wallet.address,
            ONE_DAY_IN_BLOCKS,
            100,
            ONE_YEAR_IN_BLOCKS,
            20,
            50,
            True,
            invalid_limits,
            False,
            sender=owner
        )


def test_global_settings_affect_validation(setup_contracts, createPayeeLimits):
    """Test that global settings affect payee validation"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    owner = ctx['owner']
    payee = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    
    # Set restrictive global settings
    usd_limits = createPayeeLimits(
        _perTxCap=100 * EIGHTEEN_DECIMALS,  # Global limit
        _perPeriodCap=500 * EIGHTEEN_DECIMALS
    )
    
    paymaster.setGlobalPayeeSettings(
        wallet.address,
        ONE_DAY_IN_BLOCKS,
        100,
        ONE_YEAR_IN_BLOCKS,
        5,  # Max 5 txs per period globally
        0,
        True,  # failOnZeroPrice
        usd_limits,
        True,
        sender=owner
    )
    
    # Add payee with more permissive settings
    payee_unit_limits = createPayeeLimits(
        _perTxCap=200 * EIGHTEEN_DECIMALS,  # Higher than global
        _perPeriodCap=1000 * EIGHTEEN_DECIMALS
    )
    payee_usd_limits = createPayeeLimits(
        _perTxCap=200 * EIGHTEEN_DECIMALS,
        _perPeriodCap=1000 * EIGHTEEN_DECIMALS
    )
    
    paymaster.addPayee(
        wallet.address,
        payee,
        False,
        ONE_DAY_IN_BLOCKS,
        10,  # More than global max
        0,
        False,  # Don't fail on zero price
        alpha_token.address,
        False,
        payee_unit_limits,
        payee_usd_limits,
        sender=owner
    )
    
    # Test transaction exceeding global USD limit (should fail)
    amount = 150 * EIGHTEEN_DECIMALS
    usd_value = 150 * EIGHTEEN_DECIMALS  # Exceeds global per-tx cap of 100
    
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    
    assert not is_valid  # Should fail due to global limit
    
    # Test zero price transaction (should fail due to global setting)
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        0  # Zero USD value
    )
    
    assert not is_valid  # Should fail due to global failOnZeroPrice


def test_global_default_period_length(setup_contracts, createPayeeLimits):
    """Test that global default period length is used when not specified"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    
    # Set global settings with custom default period
    custom_period = ONE_DAY_IN_BLOCKS  # Valid period
    usd_limits = createPayeeLimits()
    
    paymaster.setGlobalPayeeSettings(
        wallet.address,
        custom_period,  # defaultPeriodLength
        100,
        ONE_YEAR_IN_BLOCKS,
        20,
        0,
        False,
        usd_limits,
        True,
        sender=owner
    )
    
    # Add payee without specifying period length
    unit_limits = createPayeeLimits()
    
    paymaster.addPayee(
        wallet.address,
        payee,
        False,
        0,  # periodLength = 0 means use default
        10,
        0,
        False,
        alpha_token.address,
        False,
        unit_limits,
        usd_limits,
        sender=owner
    )
    
    # Verify default period was used
    settings = wallet_config.payeeSettings(payee)
    assert settings[3] == custom_period


def test_global_canPayOwner_setting(setup_contracts, createPayeeLimits):
    """Test canPayOwner global setting"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    owner = ctx['owner']
    alpha_token = ctx['alpha_token']
    
    # First set to allow owner payments
    usd_limits = createPayeeLimits()
    
    paymaster.setGlobalPayeeSettings(
        wallet.address,
        ONE_DAY_IN_BLOCKS,
        100,
        ONE_YEAR_IN_BLOCKS,
        20,
        0,
        False,
        usd_limits,
        True,  # canPayOwner
        sender=owner
    )
    
    # Verify owner is valid payee
    amount = 100 * EIGHTEEN_DECIMALS
    usd_value = 100 * EIGHTEEN_DECIMALS
    
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        owner,
        alpha_token.address,
        amount,
        usd_value
    )
    
    assert is_valid
    
    # Now disallow owner payments
    paymaster.setGlobalPayeeSettings(
        wallet.address,
        ONE_DAY_IN_BLOCKS,
        100,
        ONE_YEAR_IN_BLOCKS,
        20,
        0,
        False,
        usd_limits,
        False,  # canPayOwner
        sender=owner
    )
    
    # Verify owner is no longer valid payee
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        owner,
        alpha_token.address,
        amount,
        usd_value
    )
    
    assert not is_valid


def test_create_default_global_payee_settings(setup_contracts):
    """Test createDefaultGlobalPayeeSettings function"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    
    # Create default settings with various inputs
    settings = paymaster.createDefaultGlobalPayeeSettings(
        ONE_DAY_IN_BLOCKS,  # defaultPeriodLength
        100,  # startDelay
        ONE_YEAR_IN_BLOCKS  # activationLength
    )
    
    # Verify defaults
    assert settings[0] == ONE_DAY_IN_BLOCKS  # defaultPeriodLength
    assert settings[1] == 100  # startDelay
    assert settings[2] == ONE_YEAR_IN_BLOCKS  # activationLength
    assert settings[3] == 0  # maxNumTxsPerPeriod (unlimited)
    assert settings[4] == 0  # txCooldownBlocks (no cooldown)
    assert settings[5] == False  # failOnZeroPrice
    assert settings[6][0] == 0  # usdLimits.perTxCap
    assert settings[6][1] == 0  # usdLimits.perPeriodCap
    assert settings[6][2] == 0  # usdLimits.lifetimeCap
    assert settings[7] == True  # canPayOwner
    
    # Test with minimum boundary values
    min_period = paymaster.MIN_PAYEE_PERIOD()
    min_activation = paymaster.MIN_ACTIVATION_LENGTH()
    
    settings_min = paymaster.createDefaultGlobalPayeeSettings(
        min_period,
        0,  # No start delay
        min_activation
    )
    
    assert settings_min[0] == min_period
    assert settings_min[1] == 0
    assert settings_min[2] == min_activation
    assert settings_min[3] == 0  # Still unlimited by default
    assert settings_min[7] == True  # Still allow owner by default
    
    # Test with maximum boundary values
    max_period = paymaster.MAX_PAYEE_PERIOD()
    max_activation = paymaster.MAX_ACTIVATION_LENGTH()
    max_start_delay = paymaster.MAX_START_DELAY()
    
    settings_max = paymaster.createDefaultGlobalPayeeSettings(
        max_period,
        max_start_delay,
        max_activation
    )
    
    assert settings_max[0] == max_period
    assert settings_max[1] == max_start_delay
    assert settings_max[2] == max_activation
    assert settings_max[6][0] == 0  # USD limits still zero
    assert settings_max[6][1] == 0
    assert settings_max[6][2] == 0


def test_global_settings_interaction_with_payees(setup_contracts, createPayeeLimits):
    """Test how global settings interact with individual payee settings"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    alpha_token = ctx['alpha_token']
    
    # Set global settings with transaction limits
    global_usd_limits = createPayeeLimits(
        _perTxCap=100 * EIGHTEEN_DECIMALS,
        _perPeriodCap=300 * EIGHTEEN_DECIMALS
    )
    
    paymaster.setGlobalPayeeSettings(
        wallet.address,
        ONE_DAY_IN_BLOCKS,
        100,
        ONE_YEAR_IN_BLOCKS,
        3,  # Max 3 txs per period globally
        50,  # 50 block cooldown
        False,
        global_usd_limits,
        True,
        sender=owner
    )
    
    # Add payee with different settings
    payee = boa.env.generate_address()
    payee_limits = createPayeeLimits()  # No limits
    
    paymaster.addPayee(
        wallet.address,
        payee,
        False,
        ONE_DAY_IN_BLOCKS,
        10,  # Payee allows 10 txs
        0,  # No cooldown for payee
        False,
        alpha_token.address,
        False,
        payee_limits,
        payee_limits,
        sender=owner
    )
    
    # Advance time to make payee active
    settings = wallet_config.payeeSettings(payee)
    boa.env.time_travel(blocks=settings[0] - boa.env.evm.patch.block_number)
    
    # Make transactions up to global limit
    amount = 50 * EIGHTEEN_DECIMALS
    usd_value = 50 * EIGHTEEN_DECIMALS
    
    # First 3 transactions should work
    for i in range(3):
        is_valid, data = paymaster.isValidPayee(
            wallet.address,
            payee,
            alpha_token.address,
            amount,
            usd_value
        )
        assert is_valid
        
        # Update data
        wallet_config.checkRecipientLimitsAndUpdateData(
            payee,
            usd_value,
            alpha_token.address,
            amount,
            sender=wallet.address
        )
        
        # Advance past cooldown
        boa.env.time_travel(blocks=51)
    
    # 4th transaction should fail (exceeds global max)
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    assert not is_valid  # Global limit exceeded


def test_global_settings_multiple_updates(setup_contracts, createPayeeLimits):
    """Test multiple updates to global settings"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    
    # Initial settings
    initial_limits = createPayeeLimits(_perTxCap=100 * EIGHTEEN_DECIMALS)
    
    paymaster.setGlobalPayeeSettings(
        wallet.address,
        ONE_DAY_IN_BLOCKS,
        100,
        ONE_YEAR_IN_BLOCKS,
        10,
        0,
        False,
        initial_limits,
        True,
        sender=owner
    )
    
    # Update to more restrictive settings
    restrictive_limits = createPayeeLimits(
        _perTxCap=50 * EIGHTEEN_DECIMALS,
        _perPeriodCap=200 * EIGHTEEN_DECIMALS,
        _lifetimeCap=1000 * EIGHTEEN_DECIMALS
    )
    
    paymaster.setGlobalPayeeSettings(
        wallet.address,
        ONE_DAY_IN_BLOCKS,  # Valid period
        200,  # Longer delay
        ONE_MONTH_IN_BLOCKS,  # Shorter activation
        5,  # Fewer txs
        100,  # Add cooldown
        True,  # Fail on zero price
        restrictive_limits,
        False,  # Disallow owner
        sender=owner
    )
    
    # Verify all changes applied
    settings = wallet_config.globalPayeeSettings()
    assert settings[0] == ONE_DAY_IN_BLOCKS
    assert settings[1] == 200
    assert settings[2] == ONE_MONTH_IN_BLOCKS
    assert settings[3] == 5
    assert settings[4] == 100
    assert settings[5] == True
    assert settings[6][0] == 50 * EIGHTEEN_DECIMALS
    assert settings[6][1] == 200 * EIGHTEEN_DECIMALS
    assert settings[6][2] == 1000 * EIGHTEEN_DECIMALS
    assert settings[7] == False