"""
Test update and remove payee functionality in Paymaster
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


@pytest.fixture
def setup_payee(setup_contracts, createPayeeLimits):
    """Setup a payee for testing updates and removals"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    owner = ctx['owner']
    payee = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    
    # Create initial limits
    unit_limits = createPayeeLimits(
        _perTxCap=100 * EIGHTEEN_DECIMALS,
        _perPeriodCap=1000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=10000 * EIGHTEEN_DECIMALS
    )
    usd_limits = createPayeeLimits(
        _perTxCap=100 * EIGHTEEN_DECIMALS,
        _perPeriodCap=1000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=10000 * EIGHTEEN_DECIMALS
    )
    
    # Add payee
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
        0,  # startDelay
        ONE_YEAR_IN_BLOCKS,  # activationLength
        sender=owner
    )
    
    return payee


# Test update payee functionality


def test_update_payee_basic(setup_contracts, setup_payee, createPayeeLimits):
    """Test basic update payee functionality"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    bravo_token = ctx['bravo_token']
    payee = setup_payee
    
    # Get original settings
    original_settings = wallet_config.payeeSettings(payee)
    original_start = original_settings[0]
    original_expiry = original_settings[1]
    
    # Create new limits
    new_unit_limits = createPayeeLimits(
        _perTxCap=200 * EIGHTEEN_DECIMALS,  # Increased
        _perPeriodCap=2000 * EIGHTEEN_DECIMALS,  # Increased
        _lifetimeCap=20000 * EIGHTEEN_DECIMALS  # Increased
    )
    new_usd_limits = createPayeeLimits(
        _perTxCap=200 * EIGHTEEN_DECIMALS,
        _perPeriodCap=2000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=20000 * EIGHTEEN_DECIMALS
    )
    
    # Update payee
    tx = paymaster.updatePayee(
        wallet.address,
        payee,
        True,  # canPull (changed)
        ONE_DAY_IN_BLOCKS,  # periodLength (valid)
        20,  # maxNumTxsPerPeriod (changed)
        10,  # txCooldownBlocks (changed)
        True,  # failOnZeroPrice (changed)
        bravo_token.address,  # primaryAsset (changed)
        True,  # onlyPrimaryAsset (changed)
        new_unit_limits,
        new_usd_limits,
        sender=owner
    )
    
    # Check events
    events = filter_logs(paymaster, "PayeeUpdated")
    assert len(events) == 1
    event = events[0]
    assert event.user == wallet.address
    assert event.payee == payee
    assert event.startBlock == original_start  # Should not change
    assert event.expiryBlock == original_expiry  # Should not change
    assert event.canPull == True
    assert event.periodLength == ONE_DAY_IN_BLOCKS
    assert event.maxNumTxsPerPeriod == 20
    assert event.txCooldownBlocks == 10
    assert event.failOnZeroPrice == True
    assert event.primaryAsset == bravo_token.address
    assert event.onlyPrimaryAsset == True
    assert event.unitPerTxCap == new_unit_limits[0]
    assert event.unitPerPeriodCap == new_unit_limits[1]
    assert event.unitLifetimeCap == new_unit_limits[2]
    
    # Verify settings in UserWalletConfig
    settings = wallet_config.payeeSettings(payee)
    assert settings[0] == original_start  # startBlock preserved
    assert settings[1] == original_expiry  # expiryBlock preserved
    assert settings[2] == True  # canPull
    assert settings[3] == ONE_DAY_IN_BLOCKS  # periodLength
    assert settings[4] == 20  # maxNumTxsPerPeriod
    assert settings[5] == 10  # txCooldownBlocks
    assert settings[6] == True  # failOnZeroPrice
    assert settings[7] == bravo_token.address  # primaryAsset
    assert settings[8] == True  # onlyPrimaryAsset


def test_update_payee_permissions(setup_contracts, setup_payee):
    """Test only owner can update payees"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    alice = ctx['payee']  # Non-owner
    payee = setup_payee
    
    # Non-owner cannot update
    with boa.reverts("no perms"):
        paymaster.updatePayee(
            wallet.address,
            payee,
            False,
            ONE_DAY_IN_BLOCKS,
            10,
            0,
            False,
            ctx['alpha_token'].address,
            False,
            (0, 0, 0),  # unit limits
            (0, 0, 0),  # usd limits
            sender=alice
        )


def test_update_nonexistent_payee(setup_contracts, createPayeeLimits):
    """Test cannot update payee that doesn't exist"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    owner = ctx['owner']
    nonexistent_payee = boa.env.generate_address()
    
    unit_limits = createPayeeLimits()
    usd_limits = createPayeeLimits()
    
    with boa.reverts("payee not found"):
        paymaster.updatePayee(
            wallet.address,
            nonexistent_payee,
            False,
            ONE_DAY_IN_BLOCKS,
            10,
            0,
            False,
            ctx['alpha_token'].address,
            False,
            unit_limits,
            usd_limits,
            sender=owner
        )


def test_update_payee_validation_errors(setup_contracts, setup_payee, createPayeeLimits):
    """Test validation errors when updating payee"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    owner = ctx['owner']
    payee = setup_payee
    
    # Test invalid period length
    unit_limits = createPayeeLimits()
    usd_limits = createPayeeLimits()
    
    min_period = paymaster.MIN_PAYEE_PERIOD()
    
    with boa.reverts("invalid settings"):
        paymaster.updatePayee(
            wallet.address,
            payee,
            False,
            min_period - 1,  # Too short
            10,
            0,
            False,
            ctx['alpha_token'].address,
            False,
            unit_limits,
            usd_limits,
            sender=owner
        )
    
    # Test invalid cooldown
    with boa.reverts("invalid settings"):
        paymaster.updatePayee(
            wallet.address,
            payee,
            False,
            ONE_DAY_IN_BLOCKS,
            10,
            ONE_DAY_IN_BLOCKS + 1,  # Cooldown exceeds period
            False,
            ctx['alpha_token'].address,
            False,
            unit_limits,
            usd_limits,
            sender=owner
        )
    
    # Test pull payee without limits
    empty_limits = createPayeeLimits()  # All zeros
    
    with boa.reverts("invalid settings"):
        paymaster.updatePayee(
            wallet.address,
            payee,
            True,  # canPull
            ONE_DAY_IN_BLOCKS,
            10,
            0,
            False,
            ctx['alpha_token'].address,
            False,
            empty_limits,  # No limits
            empty_limits,
            sender=owner
        )


def test_update_preserves_timing(setup_contracts, createPayeeLimits):
    """Test that update preserves start and expiry blocks"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    
    # Add payee with specific timing
    unit_limits = createPayeeLimits()
    usd_limits = createPayeeLimits()
    
    start_delay = 100
    activation_length = 5000
    
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
        start_delay,
        activation_length,
        sender=owner
    )
    
    # Get original timing
    settings = wallet_config.payeeSettings(payee)
    original_start = settings[0]
    original_expiry = settings[1]
    
    # Update payee
    # For pull payee, need non-zero limits
    pull_limits = createPayeeLimits(_perTxCap=100 * EIGHTEEN_DECIMALS)
    paymaster.updatePayee(
        wallet.address,
        payee,
        True,  # Change to pull
        ONE_DAY_IN_BLOCKS + 100,  # Change period
        5,  # Change max txs
        0,
        False,
        alpha_token.address,
        False,
        pull_limits,
        pull_limits,
        sender=owner
    )
    
    # Verify timing preserved
    updated_settings = wallet_config.payeeSettings(payee)
    assert updated_settings[0] == original_start
    assert updated_settings[1] == original_expiry


# Test remove payee functionality


def test_remove_payee_basic(setup_contracts, setup_payee):
    """Test basic remove payee functionality"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = setup_payee
    
    # Verify payee exists
    assert wallet_config.isRegisteredPayee(payee)
    
    # Remove payee
    tx = paymaster.removePayee(wallet.address, payee, sender=owner)
    
    # Check events
    events = filter_logs(paymaster, "PayeeRemoved")
    assert len(events) == 1
    assert events[0].user == wallet.address
    assert events[0].payee == payee
    
    # Verify payee removed from UserWalletConfig
    assert not wallet_config.isRegisteredPayee(payee)
    
    # Verify settings cleared
    settings = wallet_config.payeeSettings(payee)
    assert settings[0] == 0  # All fields should be zero
    assert settings[1] == 0
    assert settings[2] == False
    
    # Verify data cleared
    data = wallet_config.payeePeriodData(payee)
    assert data[0] == 0  # All fields should be zero
    assert data[1] == 0
    assert data[2] == 0


def test_remove_payee_permissions(setup_contracts, setup_payee):
    """Test only owner can remove payees"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    alice = ctx['payee']  # Non-owner
    payee = setup_payee
    
    # Non-owner cannot remove
    with boa.reverts("no perms"):
        paymaster.removePayee(wallet.address, payee, sender=alice)


def test_remove_nonexistent_payee(setup_contracts):
    """Test cannot remove payee that doesn't exist"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    owner = ctx['owner']
    nonexistent_payee = boa.env.generate_address()
    
    with boa.reverts("payee not found"):
        paymaster.removePayee(wallet.address, nonexistent_payee, sender=owner)


def test_remove_payee_with_pending_data(setup_contracts, setup_payee):
    """Test removing payee clears all associated data"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    alpha_token = ctx['alpha_token']
    payee = setup_payee
    
    # First make a transaction to populate payee data
    amount = 50 * EIGHTEEN_DECIMALS
    usd_value = 50 * EIGHTEEN_DECIMALS
    
    # Advance time to make payee active
    settings = wallet_config.payeeSettings(payee)
    boa.env.time_travel(blocks=settings[0] - boa.env.evm.patch.block_number)
    
    # Validate payee to populate data
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        payee,
        alpha_token.address,
        amount,
        usd_value
    )
    assert is_valid
    
    # Update data in wallet config
    wallet_config.checkRecipientLimitsAndUpdateData(
        payee,
        usd_value,
        alpha_token.address,
        amount,
        paymaster.address,
        sender=wallet.address
    )
    
    # Verify data exists
    period_data = wallet_config.payeePeriodData(payee)
    assert period_data[0] > 0  # numTxsInPeriod
    assert period_data[1] > 0  # totalUnitsInPeriod
    assert period_data[2] > 0  # totalUsdValueInPeriod
    
    # Remove payee
    paymaster.removePayee(wallet.address, payee, sender=owner)
    
    # Verify all data cleared
    period_data = wallet_config.payeePeriodData(payee)
    assert period_data[0] == 0
    assert period_data[1] == 0
    assert period_data[2] == 0
    assert period_data[3] == 0
    assert period_data[4] == 0
    assert period_data[5] == 0
    assert period_data[6] == 0
    assert period_data[7] == 0


def test_remove_then_readd_payee(setup_contracts, createPayeeLimits):
    """Test that removed payee can be added again"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    
    unit_limits = createPayeeLimits()
    usd_limits = createPayeeLimits()
    
    # Add payee
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
    
    # Remove payee
    paymaster.removePayee(wallet.address, payee, sender=owner)
    
    # Verify removed
    assert not wallet_config.isRegisteredPayee(payee)
    
    # Add again with different settings
    new_unit_limits = createPayeeLimits(_perTxCap=200 * EIGHTEEN_DECIMALS)
    
    paymaster.addPayee(
        wallet.address,
        payee,
        True,  # Different settings
        ONE_DAY_IN_BLOCKS + 100,  # Different period
        5,
        0,
        False,
        alpha_token.address,
        False,
        new_unit_limits,
        usd_limits,
        sender=owner
    )
    
    # Verify added with new settings
    assert wallet_config.isRegisteredPayee(payee)
    settings = wallet_config.payeeSettings(payee)
    assert settings[2] == True  # canPull
    assert settings[3] == ONE_DAY_IN_BLOCKS + 100  # periodLength


def test_update_after_data_accumulation(setup_contracts, setup_payee, createPayeeLimits):
    """Test that updating payee preserves accumulated data"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    alpha_token = ctx['alpha_token']
    payee = setup_payee
    
    # Advance time to make payee active first
    settings = wallet_config.payeeSettings(payee)
    boa.env.time_travel(blocks=settings[0] - boa.env.evm.patch.block_number)
    
    # Make transactions to accumulate data
    amount = 50 * EIGHTEEN_DECIMALS
    usd_value = 50 * EIGHTEEN_DECIMALS
    
    # First transaction
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
        paymaster.address,
        sender=wallet.address
    )
    
    # Get current data
    period_data_before = wallet_config.payeePeriodData(payee)
    total_txs_before = period_data_before[3]
    total_units_before = period_data_before[4]
    total_usd_before = period_data_before[5]
    
    # Update payee settings
    new_limits = createPayeeLimits(_perTxCap=300 * EIGHTEEN_DECIMALS)
    
    paymaster.updatePayee(
        wallet.address,
        payee,
        False,
        ONE_DAY_IN_BLOCKS,
        20,  # Increased max txs
        0,
        False,
        alpha_token.address,
        False,
        new_limits,
        new_limits,
        sender=owner
    )
    
    # Verify data preserved
    period_data_after = wallet_config.payeePeriodData(payee)
    assert period_data_after[3] == total_txs_before  # totalNumTxs
    assert period_data_after[4] == total_units_before  # totalUnits
    assert period_data_after[5] == total_usd_before  # totalUsdValue


def test_batch_operations(setup_contracts, createPayeeLimits):
    """Test multiple payee operations in sequence"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    alpha_token = ctx['alpha_token']
    
    # Create multiple payees
    payees = [boa.env.generate_address() for _ in range(3)]
    
    unit_limits = createPayeeLimits()
    usd_limits = createPayeeLimits()
    
    # Add all payees
    for i, payee in enumerate(payees):
        paymaster.addPayee(
            wallet.address,
            payee,
            False,
            ONE_DAY_IN_BLOCKS,
            10 + i,  # Different max txs
            0,
            False,
            alpha_token.address,
            False,
            unit_limits,
            usd_limits,
            sender=owner
        )
    
    # Verify all added
    for payee in payees:
        assert wallet_config.isRegisteredPayee(payee)
    
    # Update middle payee
    # For pull payee, need non-zero limits
    pull_limits = createPayeeLimits(_perTxCap=100 * EIGHTEEN_DECIMALS)
    paymaster.updatePayee(
        wallet.address,
        payees[1],
        True,  # Change to pull
        ONE_DAY_IN_BLOCKS,
        15,
        0,
        False,
        alpha_token.address,
        False,
        pull_limits,
        pull_limits,
        sender=owner
    )
    
    # Remove first payee
    paymaster.removePayee(wallet.address, payees[0], sender=owner)
    
    # Verify states
    assert not wallet_config.isRegisteredPayee(payees[0])  # Removed
    assert wallet_config.isRegisteredPayee(payees[1])  # Still exists
    assert wallet_config.isRegisteredPayee(payees[2])  # Still exists
    
    # Verify updated settings
    settings = wallet_config.payeeSettings(payees[1])
    assert settings[2] == True  # canPull
    assert settings[3] == ONE_DAY_IN_BLOCKS  # periodLength


def test_backpack_can_remove_payee(setup_contracts, createPayeeLimits, backpack):
    """Test that Backpack can remove payees in non-eject mode"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    
    # Add payee first
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
        sender=owner
    )
    
    # Verify payee exists
    assert wallet_config.isRegisteredPayee(payee)
    
    # Backpack removes payee
    tx = paymaster.removePayee(wallet.address, payee, sender=backpack.address)
    
    # Check event
    events = filter_logs(paymaster, "PayeeRemoved")
    assert len(events) == 1
    assert events[0].user == wallet.address
    assert events[0].payee == payee
    
    # Verify payee removed
    assert not wallet_config.isRegisteredPayee(payee)


def test_payee_can_remove_themselves(setup_contracts, createPayeeLimits):
    """Test that payees can remove themselves"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = ctx['payee']
    alpha_token = ctx['alpha_token']
    
    # Add payee first
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
        sender=owner
    )
    
    # Verify payee exists
    assert wallet_config.isRegisteredPayee(payee)
    
    # Payee removes themselves
    tx = paymaster.removePayee(wallet.address, payee, sender=payee)
    
    # Check event
    events = filter_logs(paymaster, "PayeeRemoved")
    assert len(events) == 1
    assert events[0].user == wallet.address
    assert events[0].payee == payee
    
    # Verify payee removed
    assert not wallet_config.isRegisteredPayee(payee)


def test_non_authorized_cannot_remove_payee(setup_contracts, createPayeeLimits):
    """Test that non-authorized addresses cannot remove payees"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    payee = boa.env.generate_address()
    random_addr = boa.env.generate_address()  # Random unauthorized address
    alpha_token = ctx['alpha_token']
    
    # Add payee first
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
        sender=owner
    )
    
    # Random address cannot remove payee
    with boa.reverts("no perms"):
        paymaster.removePayee(wallet.address, payee, sender=random_addr)