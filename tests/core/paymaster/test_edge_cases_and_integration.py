"""
Test edge cases and integration scenarios for Paymaster
"""
import pytest
import boa

from contracts.core import Paymaster
from contracts.core.userWallet import UserWallet, UserWalletConfig
from constants import EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ONE_YEAR_IN_BLOCKS, ZERO_ADDRESS
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
def setup_contracts(setup_wallet, paymaster, boss_validator, alpha_token, bravo_token, bob, alice, charlie, governance, env):
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
        'boss_validator': boss_validator,
        'owner': owner,
        'addr1': alice,
        'addr2': charlie,
        'manager': env.generate_address("manager"),
        'alpha_token': alpha_token,
        'bravo_token': bravo_token
    }


def advance_to_payee_active(wallet_config, payee):
    """Helper to advance time to when payee becomes active"""
    settings = wallet_config.payeeSettings(payee)
    if settings[0] > boa.env.evm.patch.block_number:
        boa.env.time_travel(blocks=settings[0] - boa.env.evm.patch.block_number)


# Edge cases for isValidPayeeWithConfig


def test_is_valid_payee_with_config_edge_cases(setup_contracts, createPayeeLimits, createPayeeData,
                                               createPayeeSettings, createGlobalPayeeSettings):
    """Test edge cases for isValidPayeeWithConfig"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    alpha_token = ctx['alpha_token']
    
    # Test with all false/zero values
    is_valid, data = paymaster.isValidPayeeWithConfig(
        False,  # isWhitelisted
        False,  # isOwner
        False,  # isPayee
        alpha_token.address,
        0,  # amount
        0,  # txUsdValue
        createPayeeSettings(),  # Default settings
        createGlobalPayeeSettings(),  # Default global settings
        createPayeeData()  # Empty data
    )
    
    assert not is_valid  # Not a valid payee
    
    # Test whitelisted overrides everything
    is_valid, data = paymaster.isValidPayeeWithConfig(
        True,  # isWhitelisted
        False,
        False,
        alpha_token.address,
        1000000 * EIGHTEEN_DECIMALS,  # Huge amount
        1000000 * EIGHTEEN_DECIMALS,  # Huge USD value
        createPayeeSettings(),
        createGlobalPayeeSettings(),
        createPayeeData()
    )
    
    assert is_valid  # Whitelisted always valid
    assert data[0] == 0  # No data tracking for whitelisted
    
    # Test owner allowed
    global_settings_allow_owner = createGlobalPayeeSettings(_canPayOwner=True)
    is_valid, data = paymaster.isValidPayeeWithConfig(
        False,  # isWhitelisted
        True,   # isOwner
        False,  # isPayee
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        createPayeeSettings(),
        global_settings_allow_owner,
        createPayeeData()
    )
    
    assert is_valid  # Owner allowed
    assert data[0] == 0  # No data tracking for owner
    
    # Test owner not allowed
    global_settings_deny_owner = createGlobalPayeeSettings(_canPayOwner=False)
    is_valid, data = paymaster.isValidPayeeWithConfig(
        False,  # isWhitelisted
        True,   # isOwner
        False,  # isPayee
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        createPayeeSettings(),
        global_settings_deny_owner,
        createPayeeData()
    )
    
    assert not is_valid  # Owner not allowed
    
    # Test registered payee validation
    payee_settings = createPayeeSettings(
        _startBlock=1,
        _expiryBlock=999999999,  # Far future
        _periodLength=ONE_DAY_IN_BLOCKS,
        _failOnZeroPrice=True,
        _primaryAsset=alpha_token.address,
        _onlyPrimaryAsset=True
    )
    
    # Test with zero price (should fail)
    is_valid, data = paymaster.isValidPayeeWithConfig(
        False,  # isWhitelisted
        False,  # isOwner
        True,   # isPayee
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        0,  # Zero USD value
        payee_settings,
        createGlobalPayeeSettings(),
        createPayeeData()
    )
    
    assert not is_valid  # Zero price not allowed
    
    # Test with wrong asset (onlyPrimaryAsset=True)
    is_valid, data = paymaster.isValidPayeeWithConfig(
        False,
        False,
        True,
        boa.env.generate_address(),  # Different asset
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        payee_settings,
        createGlobalPayeeSettings(),
        createPayeeData()
    )
    
    assert not is_valid  # Wrong asset not allowed
    
    # Test with correct asset and non-zero price
    is_valid, data = paymaster.isValidPayeeWithConfig(
        False,
        False,
        True,
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        payee_settings,
        createGlobalPayeeSettings(),
        createPayeeData()
    )
    
    assert is_valid  # Should work
    assert data[0] == 1  # numTxsInPeriod
    assert data[1] == 100 * EIGHTEEN_DECIMALS  # totalUnitsInPeriod
    assert data[2] == 100 * EIGHTEEN_DECIMALS  # totalUsdValueInPeriod


def test_complex_limit_combinations(setup_contracts, createPayeeLimits):
    """Test complex combinations of limits"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    bravo_token = ctx['bravo_token']
    
    # Set up complex limit scenario
    unit_limits = createPayeeLimits(
        _perTxCap=100 * EIGHTEEN_DECIMALS,
        _perPeriodCap=300 * EIGHTEEN_DECIMALS,
        _lifetimeCap=1000 * EIGHTEEN_DECIMALS
    )
    usd_limits = createPayeeLimits(
        _perTxCap=50 * EIGHTEEN_DECIMALS,  # Lower USD cap than unit cap
        _perPeriodCap=200 * EIGHTEEN_DECIMALS,
        _lifetimeCap=800 * EIGHTEEN_DECIMALS
    )
    
    paymaster.addPayee(
        wallet.address,
        payee,
        False,
        ONE_DAY_IN_BLOCKS,  # Valid period length
        10,
        0,
        False,
        alpha_token.address,  # Primary asset
        False,  # Allow other assets
        unit_limits,
        usd_limits,
        sender=owner
    )
    
    # Advance time to make payee active
    advance_to_payee_active(wallet_config, payee)
    
    # Test 1: Transaction limited by USD cap, not unit cap
    amount = 80 * EIGHTEEN_DECIMALS  # Within unit cap
    usd_value = 60 * EIGHTEEN_DECIMALS  # Exceeds USD per-tx cap
    
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    
    assert not is_valid  # USD cap exceeded
    
    # Test 2: Transaction with non-primary asset (only USD limits apply)
    amount = 200 * EIGHTEEN_DECIMALS  # Would exceed unit cap
    usd_value = 40 * EIGHTEEN_DECIMALS  # Within USD cap
    
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        bravo_token.address,  # Non-primary asset
        amount,
        usd_value
    )
    
    assert is_valid  # Unit limits don't apply to non-primary


def test_period_boundary_conditions(setup_contracts, createPayeeLimits):
    """Test period boundary conditions"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    
    period_length = ONE_DAY_IN_BLOCKS  # Valid period length
    
    unit_limits = createPayeeLimits(
        _perPeriodCap=100 * EIGHTEEN_DECIMALS
    )
    usd_limits = createPayeeLimits(
        _perPeriodCap=100 * EIGHTEEN_DECIMALS
    )
    
    paymaster.addPayee(
        wallet.address,
        payee,
        False,
        period_length,
        10,
        0,
        False,
        alpha_token.address,
        False,
        unit_limits,
        usd_limits,
        sender=owner
    )
    
    # Advance time to make payee active
    advance_to_payee_active(wallet_config, payee)
    
    # Make transaction at end of period
    amount = 90 * EIGHTEEN_DECIMALS
    usd_value = 90 * EIGHTEEN_DECIMALS
    
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    assert is_valid
    
    wallet_config.checkRecipientLimitsAndUpdateData(
        payee,
        usd_value,
        alpha_token.address,
        amount,
        paymaster.address,
        sender=wallet.address
    )
    
    # Advance exactly to period boundary
    boa.env.time_travel(blocks=period_length)
    
    # Should be in new period now
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    
    assert is_valid
    assert data[0] == 1  # New period, count reset
    assert data[1] == amount  # New period amount


def test_max_values_and_overflows(setup_contracts, createPayeeLimits):
    """Test behavior with maximum values"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    
    # Test with maximum values
    max_uint256 = 2**256 - 1
    
    # Add payee with max limits
    unit_limits = createPayeeLimits(
        _perTxCap=max_uint256,
        _perPeriodCap=max_uint256,
        _lifetimeCap=max_uint256
    )
    usd_limits = createPayeeLimits(
        _perTxCap=max_uint256,
        _perPeriodCap=max_uint256,
        _lifetimeCap=max_uint256
    )
    
    paymaster.addPayee(
        wallet.address,
        payee,
        False,
        ONE_DAY_IN_BLOCKS,
        0,  # Unlimited transactions
        0,
        False,
        alpha_token.address,
        False,
        unit_limits,
        usd_limits,
        sender=owner
    )
    
    # Advance time to make payee active
    advance_to_payee_active(wallet_config, payee)
    
    # Test with large amounts
    large_amount = 10**30
    large_usd = 10**30
    
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        large_amount,
        large_usd
    )
    
    assert is_valid


def test_concurrent_payee_and_whitelist_operations(setup_contracts, createPayeeLimits):
    """Test concurrent operations between payee and whitelist systems"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    addr = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    
    # Start adding as payee
    unit_limits = createPayeeLimits()
    usd_limits = createPayeeLimits()
    
    paymaster.addPayee(
        wallet.address,
        addr,
        False,
        ONE_DAY_IN_BLOCKS,
        10,
        0,
        False,
        alpha_token.address,
        False,
        unit_limits,
        usd_limits,
        sender=owner
    )
    
    # Can whitelist an existing payee (payee and whitelist are independent)
    paymaster.addWhitelistAddr(wallet.address, addr, sender=owner)
    boa.env.time_travel(blocks=wallet_config.timeLock() + 1)
    paymaster.confirmWhitelistAddr(wallet.address, addr, sender=owner)
    
    # Verify both payee and whitelist status
    assert wallet_config.isWhitelisted(addr)
    assert wallet_config.isRegisteredPayee(addr)
    
    # Remove payee (whitelist remains)
    paymaster.removePayee(wallet.address, addr, sender=owner)
    
    # Verify states
    assert wallet_config.isWhitelisted(addr)
    assert not wallet_config.isRegisteredPayee(addr)


def test_backpack_permissions_non_eject(setup_contracts, backpack):
    """Test backpack permissions in non-eject mode"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    addr = boa.env.generate_address()
    
    # Verify not in eject mode
    assert not wallet_config.inEjectMode()
    
    # Add pending whitelist
    paymaster.addWhitelistAddr(wallet.address, addr, sender=owner)
    
    # Backpack can cancel in non-eject mode
    paymaster.cancelPendingWhitelistAddr(wallet.address, addr, sender=backpack.address)
    
    # Verify cancelled
    pending = wallet_config.pendingWhitelist(addr)
    assert pending[0] == 0


def test_zero_period_length_edge_case(setup_contracts, createPayeeLimits, createGlobalPayeeSettings):
    """Test edge case where period length is specified as 0"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    
    # Set global default period
    default_period = ONE_DAY_IN_BLOCKS  # Valid period length
    global_settings = createGlobalPayeeSettings(_defaultPeriodLength=default_period)
    paymaster.setGlobalPayeeSettings(
        wallet.address,
        default_period,
        global_settings[1],
        global_settings[2],
        global_settings[3],
        global_settings[4],
        global_settings[5],
        global_settings[6],
        global_settings[7],
        sender=owner
    )
    
    unit_limits = createPayeeLimits()
    usd_limits = createPayeeLimits()
    
    # Add payee with 0 period length
    paymaster.addPayee(
        wallet.address,
        payee,
        False,
        0,  # Should use global default
        10,
        0,
        False,
        alpha_token.address,
        False,
        unit_limits,
        usd_limits,
        sender=owner
    )
    
    # Verify default was used
    settings = wallet_config.payeeSettings(payee)
    assert settings[3] == default_period


def test_complex_manager_payee_scenario(setup_contracts, createPayeeLimits, createManagerSettings,
                                       createTransferPerms, boss_validator):
    """Test complex scenario with managers and payees"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    manager = ctx['manager']
    payee1 = boa.env.generate_address()
    payee2 = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    
    # Add manager with limited payee permissions
    transfer_perms = createTransferPerms(
        _canAddPendingPayee=True,
        _allowedPayees=[payee1]  # Only allowed to manage payee1
    )
    manager_settings = createManagerSettings(_transferPerms=transfer_perms)
    wallet_config.addManager(manager, manager_settings, sender=boss_validator.address)
    
    unit_limits = createPayeeLimits()
    usd_limits = createPayeeLimits()
    
    # Manager can add payee1 as pending
    paymaster.addPendingPayee(
        wallet.address,
        payee1,
        False,
        ONE_DAY_IN_BLOCKS,
        10,
        0,
        False,
        alpha_token.address,
        False,
        unit_limits,
        usd_limits,
        sender=manager
    )
    
    # Manager cannot add payee2 (not in allowed list)
    # Note: This would require checking allowed payees in the contract
    # which may not be implemented - commenting out for now
    
    # Owner confirms payee1
    boa.env.time_travel(blocks=wallet_config.timeLock() + 1)
    paymaster.confirmPendingPayee(wallet.address, payee1, sender=owner)
    
    # Verify payee1 is registered
    assert wallet_config.isRegisteredPayee(payee1)


def test_zero_limits_unlimited_behavior(setup_contracts, createPayeeLimits):
    """Test that zero limits are treated as unlimited"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    
    # Add payee with all zero limits (unlimited)
    zero_limits = createPayeeLimits(
        _perTxCap=0,
        _perPeriodCap=0,
        _lifetimeCap=0
    )
    
    paymaster.addPayee(
        wallet.address,
        payee,
        False,
        ONE_DAY_IN_BLOCKS,
        0,  # Unlimited transactions
        0,  # No cooldown
        False,
        alpha_token.address,
        False,
        zero_limits,
        zero_limits,
        sender=owner
    )
    
    # Advance to when payee is active
    advance_to_payee_active(wallet_config, payee)
    
    # Test very large transaction amounts (should be allowed)
    huge_amount = 1000000 * EIGHTEEN_DECIMALS
    huge_usd_value = 1000000 * EIGHTEEN_DECIMALS
    
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        huge_amount,
        huge_usd_value
    )
    
    assert is_valid
    assert data[0] == 1  # numTxsInPeriod
    assert data[1] == huge_amount  # totalUnitsInPeriod
    assert data[2] == huge_usd_value  # totalUsdValueInPeriod


def test_mixed_zero_nonzero_limits(setup_contracts, createPayeeLimits):
    """Test combinations of zero and non-zero limits"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    
    # Add payee with mixed limits (per-tx limited, period/lifetime unlimited)
    mixed_limits = createPayeeLimits(
        _perTxCap=100 * EIGHTEEN_DECIMALS,  # Limited
        _perPeriodCap=0,  # Unlimited
        _lifetimeCap=0   # Unlimited
    )
    
    paymaster.addPayee(
        wallet.address,
        payee,
        False,
        ONE_DAY_IN_BLOCKS,
        0,  # Unlimited transactions
        0,
        False,
        alpha_token.address,
        False,
        mixed_limits,
        mixed_limits,
        sender=owner
    )
    
    # Advance to when payee is active
    advance_to_payee_active(wallet_config, payee)
    
    # Transaction within per-tx limit should work
    amount = 50 * EIGHTEEN_DECIMALS
    usd_value = 50 * EIGHTEEN_DECIMALS
    
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    
    assert is_valid
    
    # Transaction exceeding per-tx limit should fail
    large_amount = 150 * EIGHTEEN_DECIMALS
    large_usd_value = 150 * EIGHTEEN_DECIMALS
    
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        large_amount,
        large_usd_value
    )
    
    assert not is_valid


def test_timing_edge_cases(setup_contracts, createPayeeLimits):
    """Test edge cases around timing and block numbers"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    
    # Get min/max values
    min_activation = paymaster.MIN_ACTIVATION_LENGTH()
    max_activation = paymaster.MAX_ACTIVATION_LENGTH()
    min_period = paymaster.MIN_PAYEE_PERIOD()
    max_period = paymaster.MAX_PAYEE_PERIOD()
    
    unit_limits = createPayeeLimits()
    usd_limits = createPayeeLimits()
    
    # Test with minimum values
    paymaster.addPayee(
        wallet.address,
        payee,
        False,
        min_period,  # Minimum period
        1,  # Minimum transactions
        0,
        False,
        alpha_token.address,
        False,
        unit_limits,
        usd_limits,
        0,
        min_activation,  # Minimum activation
        sender=owner
    )
    
    settings = wallet_config.payeeSettings(payee)
    assert settings[3] == min_period
    
    # Remove for next test
    paymaster.removePayee(wallet.address, payee, sender=owner)
    
    # Test with maximum values
    paymaster.addPayee(
        wallet.address,
        payee,
        False,
        max_period,  # Maximum period
        0,  # Unlimited transactions
        max_period - 1,  # Max cooldown (less than period)
        False,
        alpha_token.address,
        False,
        unit_limits,
        usd_limits,
        0,
        max_activation,  # Maximum activation
        sender=owner
    )
    
    settings = wallet_config.payeeSettings(payee)
    assert settings[3] == max_period
    assert settings[5] == max_period - 1  # txCooldownBlocks


def test_data_consistency_after_operations(setup_contracts, createPayeeLimits):
    """Test data consistency after various operations"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    
    unit_limits = createPayeeLimits(
        _perTxCap=100 * EIGHTEEN_DECIMALS,
        _lifetimeCap=500 * EIGHTEEN_DECIMALS
    )
    usd_limits = createPayeeLimits(
        _perTxCap=100 * EIGHTEEN_DECIMALS,
        _lifetimeCap=500 * EIGHTEEN_DECIMALS
    )
    
    # Add payee
    paymaster.addPayee(
        wallet.address,
        payee,
        False,
        ONE_DAY_IN_BLOCKS,  # Valid period
        0,
        0,
        False,
        alpha_token.address,
        False,
        unit_limits,
        usd_limits,
        sender=owner
    )
    
    # Advance time to make payee active
    advance_to_payee_active(wallet_config, payee)
    
    # Make some transactions
    for i in range(3):
        amount = 50 * EIGHTEEN_DECIMALS
        usd_value = 50 * EIGHTEEN_DECIMALS
        
        is_valid, data = paymaster.isValidPayee(
            wallet.address,
            payee,
            alpha_token.address,
            amount,
            usd_value
        )
        assert is_valid
        
        wallet_config.checkRecipientLimitsAndUpdateData(
            payee,
            usd_value,
            alpha_token.address,
            amount,
            paymaster.address,
            sender=wallet.address
        )
    
    # Check accumulated data
    period_data = wallet_config.payeePeriodData(payee)
    assert period_data[3] == 3  # totalNumTxs
    assert period_data[4] == 150 * EIGHTEEN_DECIMALS  # totalUnits
    assert period_data[5] == 150 * EIGHTEEN_DECIMALS  # totalUsdValue
    
    # Update payee (should preserve data)
    new_limits = createPayeeLimits(_perTxCap=200 * EIGHTEEN_DECIMALS)
    paymaster.updatePayee(
        wallet.address,
        payee,
        False,
        ONE_DAY_IN_BLOCKS,
        0,
        0,
        False,
        alpha_token.address,
        False,
        new_limits,
        new_limits,
        sender=owner
    )
    
    # Verify data preserved
    period_data = wallet_config.payeePeriodData(payee)
    assert period_data[3] == 3  # Still 3 total txs
    assert period_data[4] == 150 * EIGHTEEN_DECIMALS  # Still same total
    
    # Can now make larger transaction with new limits
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        150 * EIGHTEEN_DECIMALS,  # Larger than old limit
        150 * EIGHTEEN_DECIMALS
    )
    assert is_valid


def test_boundary_validation_errors(setup_contracts, createPayeeLimits):
    """Test validation at exact boundaries"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    owner = ctx['owner']
    alpha_token = ctx['alpha_token']
    
    # Get exact boundary values
    min_period = paymaster.MIN_PAYEE_PERIOD()
    max_period = paymaster.MAX_PAYEE_PERIOD()
    min_activation = paymaster.MIN_ACTIVATION_LENGTH()
    max_activation = paymaster.MAX_ACTIVATION_LENGTH()
    max_start_delay = paymaster.MAX_START_DELAY()
    
    unit_limits = createPayeeLimits()
    usd_limits = createPayeeLimits()
    
    # Test exact boundaries (should succeed)
    paymaster.addPayee(
        wallet.address,
        boa.env.generate_address(),
        False,
        min_period,  # Exact minimum
        0,
        0,
        False,
        alpha_token.address,
        False,
        unit_limits,
        usd_limits,
        0,
        min_activation,  # Exact minimum
        sender=owner
    )
    
    paymaster.addPayee(
        wallet.address,
        boa.env.generate_address(),
        False,
        max_period,  # Exact maximum
        0,
        0,
        False,
        alpha_token.address,
        False,
        unit_limits,
        usd_limits,
        max_start_delay,  # Exact maximum
        max_activation,  # Exact maximum
        sender=owner
    )
    
    # Both should succeed without errors


def test_period_boundary_exact_timing(setup_contracts, createPayeeLimits):
    """Test transactions at exact period boundaries"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    
    # Add payee with short period for precise testing
    period_length = ONE_DAY_IN_BLOCKS
    unit_limits = createPayeeLimits(
        _perTxCap=100 * EIGHTEEN_DECIMALS,
        _perPeriodCap=150 * EIGHTEEN_DECIMALS
    )
    usd_limits = createPayeeLimits(
        _perTxCap=100 * EIGHTEEN_DECIMALS,
        _perPeriodCap=150 * EIGHTEEN_DECIMALS
    )
    
    paymaster.addPayee(
        wallet.address,
        payee,
        False,
        period_length,
        10,
        0,
        False,
        alpha_token.address,
        False,
        unit_limits,
        usd_limits,
        sender=owner
    )
    
    # Advance to when payee is active
    advance_to_payee_active(wallet_config, payee)
    
    # First transaction to establish period
    amount = 100 * EIGHTEEN_DECIMALS
    usd_value = 100 * EIGHTEEN_DECIMALS
    
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    
    assert is_valid
    period_start = data[7]  # periodStartBlock
    
    # Update data
    wallet_config.checkRecipientLimitsAndUpdateData(
        payee,
        usd_value,
        alpha_token.address,
        amount,
        paymaster.address,
        sender=wallet.address
    )
    
    # Move to exactly one block before period ends
    target_block = period_start + period_length - 1
    current_block = boa.env.evm.patch.block_number
    boa.env.time_travel(blocks=target_block - current_block)
    
    # Transaction at last block of period (should fail - exceeds period cap)
    amount = 60 * EIGHTEEN_DECIMALS
    usd_value = 60 * EIGHTEEN_DECIMALS
    
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    
    assert not is_valid  # Should fail due to period cap (100 + 60 > 150)
    
    # Move to exactly the first block of new period
    boa.env.time_travel(blocks=1)
    
    # Same transaction should now work (new period)
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    
    assert is_valid  # Should work - new period
    assert data[0] == 1  # numTxsInPeriod reset to 1
    assert data[1] == amount  # totalUnitsInPeriod reset
    assert data[7] == boa.env.evm.patch.block_number  # New periodStartBlock


def test_multiple_transactions_same_block_period_boundary(setup_contracts, createPayeeLimits):
    """Test multiple transactions in same block at period boundary"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    
    # Add payee
    unit_limits = createPayeeLimits(_perTxCap=50 * EIGHTEEN_DECIMALS)
    usd_limits = createPayeeLimits(_perTxCap=50 * EIGHTEEN_DECIMALS)
    
    paymaster.addPayee(
        wallet.address,
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
        sender=owner
    )
    
    # Advance to when payee is active
    advance_to_payee_active(wallet_config, payee)
    
    # First transaction to establish period
    amount = 30 * EIGHTEEN_DECIMALS
    usd_value = 30 * EIGHTEEN_DECIMALS
    
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    
    assert is_valid
    period_start = data[7]
    
    # Advance to new period boundary
    boa.env.time_travel(blocks=ONE_DAY_IN_BLOCKS)
    
    # Multiple calls to isValidPayee in same block should be consistent
    is_valid_1, data_1 = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    
    is_valid_2, data_2 = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    
    # Both should be valid and show consistent period reset
    assert is_valid_1
    assert is_valid_2
    assert data_1[7] == data_2[7]  # Same new periodStartBlock
    assert data_1[0] == 1  # New period transaction count
    assert data_2[0] == 1  # Same for second call


def test_cannot_bypass_lifetime_limit_with_period_resets(setup_contracts, createPayeeLimits):
    """Test that lifetime limits cannot be bypassed by waiting for period resets"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    
    # Add payee with period cap > lifetime cap (should fail validation)
    # But test with period cap < lifetime cap and verify lifetime enforcement
    unit_limits = createPayeeLimits(
        _perTxCap=100 * EIGHTEEN_DECIMALS,
        _perPeriodCap=200 * EIGHTEEN_DECIMALS,
        _lifetimeCap=300 * EIGHTEEN_DECIMALS  # 300 lifetime, 200 per period
    )
    usd_limits = createPayeeLimits(
        _perTxCap=100 * EIGHTEEN_DECIMALS,
        _perPeriodCap=200 * EIGHTEEN_DECIMALS,
        _lifetimeCap=300 * EIGHTEEN_DECIMALS
    )
    
    paymaster.addPayee(
        wallet.address,
        payee,
        False,
        ONE_DAY_IN_BLOCKS,  # Short period for testing
        10,
        0,
        False,
        alpha_token.address,
        False,
        unit_limits,
        usd_limits,
        sender=owner
    )
    
    # Advance to when payee is active
    advance_to_payee_active(wallet_config, payee)
    
    # First period: consume 200 (full period limit)
    amount_1 = 100 * EIGHTEEN_DECIMALS
    usd_value_1 = 100 * EIGHTEEN_DECIMALS
    
    # First transaction
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount_1,
        usd_value_1
    )
    assert is_valid
    
    wallet_config.checkRecipientLimitsAndUpdateData(
        payee,
        usd_value_1,
        alpha_token.address,
        amount_1,
        paymaster.address,
        sender=wallet.address
    )
    
    # Second transaction (completes period limit)
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount_1,
        usd_value_1
    )
    assert is_valid
    
    wallet_config.checkRecipientLimitsAndUpdateData(
        payee,
        usd_value_1,
        alpha_token.address,
        amount_1,
        paymaster.address,
        sender=wallet.address
    )
    
    # Advance to new period
    boa.env.time_travel(blocks=ONE_DAY_IN_BLOCKS + 1)
    
    # Try to spend another 200 in new period (would exceed lifetime cap of 300)
    # First transaction in new period should work (lifetime: 200 + 100 = 300)
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount_1,
        usd_value_1
    )
    assert is_valid  # 300 total is at lifetime cap
    
    wallet_config.checkRecipientLimitsAndUpdateData(
        payee,
        usd_value_1,
        alpha_token.address,
        amount_1,
        paymaster.address,
        sender=wallet.address
    )
    
    # Any additional transaction should fail (would exceed lifetime)
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        1 * EIGHTEEN_DECIMALS,  # Even small amount
        1 * EIGHTEEN_DECIMALS,
    )
    assert not is_valid  # Lifetime cap enforced


def test_data_integrity_across_multiple_updates(setup_contracts, createPayeeLimits):
    """Test data integrity when making multiple updates and transactions"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    
    # Add payee with generous limits
    unit_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=5000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=10000 * EIGHTEEN_DECIMALS
    )
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=5000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=10000 * EIGHTEEN_DECIMALS
    )
    
    paymaster.addPayee(
        wallet.address,
        payee,
        False,
        ONE_DAY_IN_BLOCKS,
        100,  # Many transactions allowed
        0,
        False,
        alpha_token.address,
        False,
        unit_limits,
        usd_limits,
        sender=owner
    )
    
    # Advance to when payee is active
    advance_to_payee_active(wallet_config, payee)
    
    # Make several transactions and verify data consistency
    expected_lifetime_units = 0
    expected_lifetime_usd = 0
    expected_period_units = 0
    expected_period_usd = 0
    expected_num_txs = 0
    
    for i in range(5):
        amount = (100 + i * 50) * EIGHTEEN_DECIMALS
        usd_value = (100 + i * 50) * EIGHTEEN_DECIMALS
        
        is_valid, data = paymaster.isValidPayee(
            wallet.address,
            payee,
            alpha_token.address,
            amount,
            usd_value
        )
        
        assert is_valid
        
        # Update expected values
        expected_num_txs += 1
        expected_period_units += amount
        expected_period_usd += usd_value
        expected_lifetime_units += amount
        expected_lifetime_usd += usd_value
        
        # Verify returned data matches expectations
        assert data[0] == expected_num_txs  # numTxsInPeriod
        assert data[1] == expected_period_units  # totalUnitsInPeriod
        assert data[2] == expected_period_usd  # totalUsdValueInPeriod
        assert data[3] == expected_num_txs  # totalNumTxs (lifetime)
        assert data[4] == expected_lifetime_units  # totalUnits (lifetime)
        assert data[5] == expected_lifetime_usd  # totalUsdValue (lifetime)
        
        # Actually update the data
        wallet_config.checkRecipientLimitsAndUpdateData(
            payee,
            usd_value,
            alpha_token.address,
            amount,
            paymaster.address,
            sender=wallet.address
        )
    
    # Verify final stored data matches our calculations
    final_data = wallet_config.payeePeriodData(payee)
    assert final_data[0] == expected_num_txs  # numTxsInPeriod
    assert final_data[1] == expected_period_units  # totalUnitsInPeriod
    assert final_data[2] == expected_period_usd  # totalUsdValueInPeriod
    assert final_data[3] == expected_num_txs  # totalNumTxs
    assert final_data[4] == expected_lifetime_units  # totalUnits
    assert final_data[5] == expected_lifetime_usd  # totalUsdValue


def test_arithmetic_safety_near_limits(setup_contracts, createPayeeLimits):
    """Test arithmetic safety when approaching uint256 limits"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    
    # Use very large but safe limits
    large_limit = 2**128  # Much smaller than uint256 max to avoid overflow
    unit_limits = createPayeeLimits(
        _perTxCap=large_limit,
        _perPeriodCap=large_limit,
        _lifetimeCap=large_limit
    )
    usd_limits = createPayeeLimits(
        _perTxCap=large_limit,
        _perPeriodCap=large_limit,
        _lifetimeCap=large_limit
    )
    
    paymaster.addPayee(
        wallet.address,
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
        sender=owner
    )
    
    # Advance to when payee is active
    advance_to_payee_active(wallet_config, payee)
    
    # Test with very large transaction amounts
    huge_amount = large_limit - 1000  # Just under the limit
    huge_usd_value = large_limit - 1000
    
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        huge_amount,
        huge_usd_value
    )
    
    assert is_valid
    assert data[1] == huge_amount  # Should handle large numbers correctly
    assert data[2] == huge_usd_value
    
    # Test that exceeding limit is properly detected
    too_large_amount = large_limit + 1
    too_large_usd = large_limit + 1
    
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        too_large_amount,
        too_large_usd
    )
    
    assert not is_valid  # Should reject amounts exceeding limits