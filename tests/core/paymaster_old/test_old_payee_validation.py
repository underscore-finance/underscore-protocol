"""
Test payee validation functions in Paymaster
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
def setup_contracts(setup_wallet, paymaster, alpha_token, bravo_token, bob, alice, charlie, governance):
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
        'payee': alice,
        'payee2': charlie,
        'alpha_token': alpha_token,
        'bravo_token': bravo_token
    }


# Test isValidPayee with whitelisted addresses


def test_is_valid_payee_whitelisted(setup_contracts):
    """Test that whitelisted addresses are always valid payees"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = ctx['payee']
    alpha_token = ctx['alpha_token']
    
    # Add payee to whitelist
    paymaster.addWhitelistAddr(wallet.address, payee, sender=owner)
    
    # Advance time to confirm
    boa.env.time_travel(blocks=wallet_config.timeLock() + 1)
    paymaster.confirmWhitelistAddr(wallet.address, payee, sender=owner)
    
    # Check if payee is valid (any amount should be valid for whitelisted)
    amount = 100 * EIGHTEEN_DECIMALS
    usd_value = 100 * EIGHTEEN_DECIMALS  # Assuming 1:1 for simplicity
    
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    
    assert is_valid
    # Data should be empty for whitelisted addresses
    assert data[0] == 0  # numTxsInPeriod
    assert data[1] == 0  # totalUnitsInPeriod
    assert data[2] == 0  # totalUsdValueInPeriod


def test_is_valid_payee_owner_allowed(setup_contracts, createGlobalPayeeSettings):
    """Test that owner can receive payments when canPayOwner is true"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    owner = ctx['owner']
    alpha_token = ctx['alpha_token']
    
    # Set global settings to allow owner payments
    global_settings = createGlobalPayeeSettings(_canPayOwner=True)
    paymaster.setGlobalPayeeSettings(
        wallet.address,
        global_settings[0],  # defaultPeriodLength
        global_settings[1],  # startDelay
        global_settings[2],  # activationLength
        global_settings[3],  # maxNumTxsPerPeriod
        global_settings[4],  # txCooldownBlocks
        global_settings[5],  # failOnZeroPrice
        global_settings[6],  # usdLimits
        global_settings[7],  # canPayOwner
        sender=owner
    )
    
    # Check if owner is valid payee
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
    # Data should be empty for owner
    assert data[0] == 0


def test_is_valid_payee_owner_not_allowed(setup_contracts, createGlobalPayeeSettings):
    """Test that owner cannot receive payments when canPayOwner is false"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    owner = ctx['owner']
    alpha_token = ctx['alpha_token']
    
    # Set global settings to disallow owner payments
    global_settings = createGlobalPayeeSettings(_canPayOwner=False)
    paymaster.setGlobalPayeeSettings(
        wallet.address,
        global_settings[0],
        global_settings[1],
        global_settings[2],
        global_settings[3],
        global_settings[4],
        global_settings[5],
        global_settings[6],
        False,  # canPayOwner
        sender=owner
    )
    
    # Check if owner is valid payee
    amount = 100 * EIGHTEEN_DECIMALS
    usd_value = 100 * EIGHTEEN_DECIMALS
    
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        owner,
        alpha_token.address,
        amount,
        usd_value
    )
    
    assert not is_valid


# Test registered payee validation


def test_is_valid_payee_registered_active(setup_contracts, createPayeeLimits):
    """Test that active registered payees are validated correctly"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    owner = ctx['owner']
    payee = ctx['payee']
    alpha_token = ctx['alpha_token']
    
    # Add payee with specific settings
    unit_limits = createPayeeLimits(
        _perTxCap=200 * EIGHTEEN_DECIMALS,
        _perPeriodCap=1000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=10000 * EIGHTEEN_DECIMALS
    )
    usd_limits = createPayeeLimits(
        _perTxCap=200 * EIGHTEEN_DECIMALS,
        _perPeriodCap=1000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=10000 * EIGHTEEN_DECIMALS
    )
    
    paymaster.addPayee(
        wallet.address,
        payee,
        False,  # canPull
        ONE_DAY_IN_BLOCKS,  # periodLength
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        False,  # failOnZeroPrice
        alpha_token.address,  # primaryAsset
        False,  # onlyPrimaryAsset
        unit_limits,
        usd_limits,
        sender=owner
    )
    
    # Check payee was added
    wallet_config = ctx['wallet_config']
    assert wallet_config.isRegisteredPayee(payee)
    settings = wallet_config.payeeSettings(payee)
    
    # Advance to when payee is active
    boa.env.time_travel(blocks=settings[0] - boa.env.evm.patch.block_number)
    
    # Check if payee is valid within limits
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
    # Verify data was updated
    assert data[0] == 1  # numTxsInPeriod
    assert data[1] == amount  # totalUnitsInPeriod (since it's primary asset)
    assert data[2] == usd_value  # totalUsdValueInPeriod


def test_is_valid_payee_inactive(setup_contracts, createPayeeLimits):
    """Test that inactive payees (before start or after expiry) are invalid"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    owner = ctx['owner']
    payee = ctx['payee2']
    alpha_token = ctx['alpha_token']
    
    # Add payee with future start block
    unit_limits = createPayeeLimits()
    usd_limits = createPayeeLimits()
    
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
        1000,  # Large start delay
        ONE_YEAR_IN_BLOCKS,
        sender=owner
    )
    
    # Check if payee is valid (should be invalid - not started yet)
    amount = 100 * EIGHTEEN_DECIMALS
    usd_value = 100 * EIGHTEEN_DECIMALS
    
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    
    assert not is_valid


# Test limit validations


def test_is_valid_payee_exceeds_per_tx_cap(setup_contracts, createPayeeLimits):
    """Test that transactions exceeding per-tx cap are invalid"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()  # Use fresh address
    alpha_token = ctx['alpha_token']
    
    # Add payee with low per-tx cap
    unit_limits = createPayeeLimits(
        _perTxCap=50 * EIGHTEEN_DECIMALS,
        _perPeriodCap=1000 * EIGHTEEN_DECIMALS
    )
    usd_limits = createPayeeLimits(
        _perTxCap=50 * EIGHTEEN_DECIMALS,
        _perPeriodCap=1000 * EIGHTEEN_DECIMALS
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
    settings = wallet_config.payeeSettings(payee)
    boa.env.time_travel(blocks=settings[0] - boa.env.evm.patch.block_number)
    
    # Try amount exceeding per-tx cap
    amount = 100 * EIGHTEEN_DECIMALS  # Exceeds 50 cap
    usd_value = 100 * EIGHTEEN_DECIMALS
    
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    
    assert not is_valid


def test_is_valid_payee_exceeds_period_cap(setup_contracts, createPayeeLimits, createPayeeData):
    """Test that transactions exceeding period cap are invalid"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()  # Fresh address
    alpha_token = ctx['alpha_token']
    
    # Add payee with period cap
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
    settings = wallet_config.payeeSettings(payee)
    boa.env.time_travel(blocks=settings[0] - boa.env.evm.patch.block_number)
    
    # First transaction within limits
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
    
    # Update payee data in wallet config to simulate first transaction
    wallet_config.checkRecipientLimitsAndUpdateData(
        payee,
        usd_value,
        alpha_token.address,
        amount,
        sender=wallet.address
    )
    
    # Second transaction would exceed period cap
    amount = 60 * EIGHTEEN_DECIMALS  # Total would be 160, exceeds 150 cap
    usd_value = 60 * EIGHTEEN_DECIMALS
    
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    
    assert not is_valid


def test_is_valid_payee_transaction_cooldown(setup_contracts, createPayeeLimits):
    """Test that transactions within cooldown period are invalid"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()  # Fresh address
    alpha_token = ctx['alpha_token']
    
    # Add payee with cooldown
    unit_limits = createPayeeLimits(_perTxCap=100 * EIGHTEEN_DECIMALS)
    usd_limits = createPayeeLimits(_perTxCap=100 * EIGHTEEN_DECIMALS)
    
    paymaster.addPayee(
        wallet.address,
        payee,
        False,
        ONE_DAY_IN_BLOCKS,
        10,
        100,  # 100 block cooldown
        False,
        alpha_token.address,
        False,
        unit_limits,
        usd_limits,
        sender=owner
    )
    
    # Advance to when payee is active (no need to advance past cooldown for first tx)
    settings = wallet_config.payeeSettings(payee)
    boa.env.time_travel(blocks=settings[0] - boa.env.evm.patch.block_number)
    
    # First transaction
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
    
    # Update payee data
    wallet_config.checkRecipientLimitsAndUpdateData(
        payee,
        usd_value,
        alpha_token.address,
        amount,
        sender=wallet.address
    )
    
    # Try another transaction immediately (should fail due to cooldown)
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    
    assert not is_valid
    
    # Advance past cooldown
    boa.env.time_travel(blocks=101)
    
    # Now should be valid
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    
    assert is_valid


def test_is_valid_payee_first_transaction_cooldown_fix(setup_contracts, createPayeeLimits):
    """Test that first transaction with cooldown works immediately (bug fix verification)"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    
    # Add payee with a large cooldown
    unit_limits = createPayeeLimits(_perTxCap=100 * EIGHTEEN_DECIMALS)
    usd_limits = createPayeeLimits(_perTxCap=100 * EIGHTEEN_DECIMALS)
    
    paymaster.addPayee(
        wallet.address,
        payee,
        False,
        ONE_DAY_IN_BLOCKS,
        10,
        1000,  # Very large cooldown (1000 blocks)
        False,
        alpha_token.address,
        False,
        unit_limits,
        usd_limits,
        sender=owner
    )
    
    # Advance only to when payee is active (not past cooldown)
    settings = wallet_config.payeeSettings(payee)
    boa.env.time_travel(blocks=settings[0] - boa.env.evm.patch.block_number)
    
    # First transaction should work immediately despite large cooldown
    amount = 50 * EIGHTEEN_DECIMALS
    usd_value = 50 * EIGHTEEN_DECIMALS
    
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    
    # This should be True - verifies the cooldown bug fix
    assert is_valid
    
    # Update payee data to simulate the first transaction
    wallet_config.checkRecipientLimitsAndUpdateData(
        payee,
        usd_value,
        alpha_token.address,
        amount,
        sender=wallet.address
    )
    
    # Now immediate second transaction should fail (cooldown applies)
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    
    assert not is_valid


def test_is_valid_payee_only_primary_asset(setup_contracts, createPayeeLimits):
    """Test that only primary asset is allowed when onlyPrimaryAsset is true"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()  # Fresh address
    alpha_token = ctx['alpha_token']
    bravo_token = ctx['bravo_token']
    
    # Add payee that only accepts alpha token
    unit_limits = createPayeeLimits()
    usd_limits = createPayeeLimits()
    
    paymaster.addPayee(
        wallet.address,
        payee,
        False,
        ONE_DAY_IN_BLOCKS,
        10,
        0,
        False,
        alpha_token.address,  # primaryAsset
        True,  # onlyPrimaryAsset
        unit_limits,
        usd_limits,
        sender=owner
    )
    
    # Advance to when payee is active
    settings = wallet_config.payeeSettings(payee)
    boa.env.time_travel(blocks=settings[0] - boa.env.evm.patch.block_number)
    
    # Test with primary asset (should be valid)
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
    
    # Test with different asset (should be invalid)
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        bravo_token.address,
        amount,
        usd_value
    )
    
    assert not is_valid


def test_is_valid_payee_fail_on_zero_price(setup_contracts, createPayeeLimits):
    """Test that zero price transactions fail when failOnZeroPrice is true"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()  # Fresh address
    alpha_token = ctx['alpha_token']
    
    # Add payee with failOnZeroPrice
    unit_limits = createPayeeLimits()
    usd_limits = createPayeeLimits()
    
    paymaster.addPayee(
        wallet.address,
        payee,
        False,
        ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,  # failOnZeroPrice
        alpha_token.address,
        False,
        unit_limits,
        usd_limits,
        sender=owner
    )
    
    # Advance to when payee is active
    settings = wallet_config.payeeSettings(payee)
    boa.env.time_travel(blocks=settings[0] - boa.env.evm.patch.block_number)
    
    # Test with zero USD value
    amount = 50 * EIGHTEEN_DECIMALS
    usd_value = 0  # Zero price
    
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    
    assert not is_valid
    
    # Test with non-zero USD value
    usd_value = 50 * EIGHTEEN_DECIMALS
    
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    
    assert is_valid


def test_is_valid_payee_period_reset(setup_contracts, createPayeeLimits):
    """Test that period data resets after period length"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()  # Fresh address
    alpha_token = ctx['alpha_token']
    
    # Add payee with short period
    period_length = ONE_DAY_IN_BLOCKS  # Valid period length
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
    settings = wallet_config.payeeSettings(payee)
    boa.env.time_travel(blocks=settings[0] - boa.env.evm.patch.block_number)
    
    # First transaction
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
    assert data[0] == 1  # numTxsInPeriod
    assert data[1] == amount  # totalUnitsInPeriod
    
    # Update payee data
    wallet_config.checkRecipientLimitsAndUpdateData(
        payee,
        usd_value,
        alpha_token.address,
        amount,
        sender=wallet.address
    )
    
    # Second transaction in same period (would exceed cap)
    amount = 60 * EIGHTEEN_DECIMALS
    usd_value = 60 * EIGHTEEN_DECIMALS
    
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    
    assert not is_valid
    
    # Advance past period
    boa.env.time_travel(blocks=period_length + 1)
    
    # Now should be valid again (new period)
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    
    assert is_valid
    assert data[0] == 1  # numTxsInPeriod (reset)
    assert data[1] == amount  # totalUnitsInPeriod (reset)


def test_is_valid_payee_max_transactions_per_period(setup_contracts, createPayeeLimits):
    """Test that max transactions per period limit is enforced"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()  # Fresh address
    alpha_token = ctx['alpha_token']
    
    # Add payee with max 2 txs per period
    unit_limits = createPayeeLimits()
    usd_limits = createPayeeLimits()
    
    paymaster.addPayee(
        wallet.address,
        payee,
        False,
        ONE_DAY_IN_BLOCKS,
        2,  # maxNumTxsPerPeriod
        0,
        False,
        alpha_token.address,
        False,
        unit_limits,
        usd_limits,
        sender=owner
    )
    
    # Advance to when payee is active
    settings = wallet_config.payeeSettings(payee)
    boa.env.time_travel(blocks=settings[0] - boa.env.evm.patch.block_number)
    
    # First transaction
    amount = 10 * EIGHTEEN_DECIMALS
    usd_value = 10 * EIGHTEEN_DECIMALS
    
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
    
    # Second transaction
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
    
    # Third transaction (should fail - exceeds max)
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    assert not is_valid


def test_is_valid_payee_lifetime_cap(setup_contracts, createPayeeLimits):
    """Test that lifetime cap is enforced"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()  # Fresh address
    alpha_token = ctx['alpha_token']
    
    # Add payee with lifetime cap
    unit_limits = createPayeeLimits(
        _perTxCap=100 * EIGHTEEN_DECIMALS,
        _lifetimeCap=150 * EIGHTEEN_DECIMALS
    )
    usd_limits = createPayeeLimits(
        _perTxCap=100 * EIGHTEEN_DECIMALS,
        _lifetimeCap=150 * EIGHTEEN_DECIMALS
    )
    
    paymaster.addPayee(
        wallet.address,
        payee,
        False,
        ONE_DAY_IN_BLOCKS,  # Valid period for testing
        0,  # Unlimited txs per period
        0,
        False,
        alpha_token.address,
        False,
        unit_limits,
        usd_limits,
        sender=owner
    )
    
    # Advance to when payee is active
    settings = wallet_config.payeeSettings(payee)
    boa.env.time_travel(blocks=settings[0] - boa.env.evm.patch.block_number)
    
    # First transaction
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
    
    # Update data
    wallet_config.checkRecipientLimitsAndUpdateData(
        payee,
        usd_value,
        alpha_token.address,
        amount,
        sender=wallet.address
    )
    
    # Advance to new period
    boa.env.time_travel(blocks=ONE_DAY_IN_BLOCKS + 1)
    
    # Second transaction (would exceed lifetime cap)
    amount = 60 * EIGHTEEN_DECIMALS
    usd_value = 60 * EIGHTEEN_DECIMALS
    
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    assert not is_valid


def test_is_valid_payee_non_primary_asset_units(setup_contracts, createPayeeLimits):
    """Test that unit limits only apply to primary asset"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()  # Fresh address
    alpha_token = ctx['alpha_token']
    bravo_token = ctx['bravo_token']
    
    # Add payee with unit limits on alpha token
    unit_limits = createPayeeLimits(
        _perTxCap=50 * EIGHTEEN_DECIMALS  # Low unit cap
    )
    usd_limits = createPayeeLimits(
        _perTxCap=200 * EIGHTEEN_DECIMALS  # High USD cap
    )
    
    paymaster.addPayee(
        wallet.address,
        payee,
        False,
        ONE_DAY_IN_BLOCKS,
        10,
        0,
        False,
        alpha_token.address,  # primaryAsset
        False,  # Allow other assets
        unit_limits,
        usd_limits,
        sender=owner
    )
    
    # Advance to when payee is active
    settings = wallet_config.payeeSettings(payee)
    boa.env.time_travel(blocks=settings[0] - boa.env.evm.patch.block_number)
    
    # Test with beta token (non-primary) - should ignore unit limits
    amount = 100 * EIGHTEEN_DECIMALS  # Exceeds unit cap
    usd_value = 100 * EIGHTEEN_DECIMALS  # Within USD cap
    
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        bravo_token.address,
        amount,
        usd_value
    )
    
    assert is_valid  # Should be valid because unit limits don't apply
    assert data[1] == 0  # totalUnitsInPeriod should not be updated for non-primary
    
    # Test with alpha token (primary) - should enforce unit limits
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    
    assert not is_valid  # Should fail due to unit cap