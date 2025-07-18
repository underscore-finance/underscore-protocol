import boa
import pytest

from constants import EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ONE_MONTH_IN_BLOCKS
from conf_utils import filter_logs

ONE_WEEK_IN_BLOCKS = ONE_DAY_IN_BLOCKS * 7
ONE_HOUR_IN_BLOCKS = ONE_DAY_IN_BLOCKS // 24


####################
# Cheque Creation #
####################


def test_createCheque_success_and_storage(
    bob, alice, alpha_token, mock_ripe,
    user_wallet, user_wallet_config, cheque_book,
):
    """Test successful cheque creation and verify data is stored correctly"""
    # Setup cheque settings
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
        False,  # canBePulled
        sender=bob
    )
    
    # Set price for the asset
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)  # $1 per token
    
    # Record initial state
    initial_cheques = user_wallet_config.cheques(alice)
    initial_cheque_data = user_wallet_config.chequePeriodData()
    initial_num_active = user_wallet_config.numActiveCheques()
    
    # Create cheque
    amount = 50 * EIGHTEEN_DECIMALS
    unlock_blocks = ONE_DAY_IN_BLOCKS
    expiry_blocks = ONE_WEEK_IN_BLOCKS
    
    tx = cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        unlock_blocks,
        expiry_blocks,
        True,  # canManagerPay
        False,  # canBePulled
        sender=bob
    )
    
    # Verify cheque was stored
    stored_cheque = user_wallet_config.cheques(alice)
    assert stored_cheque.recipient == alice
    assert stored_cheque.asset == alpha_token.address
    assert stored_cheque.amount == amount
    assert stored_cheque.creationBlock == boa.env.evm.patch.block_number
    assert stored_cheque.unlockBlock == boa.env.evm.patch.block_number + unlock_blocks
    assert stored_cheque.expiryBlock == stored_cheque.unlockBlock + expiry_blocks
    assert stored_cheque.usdValueOnCreation == amount  # Since price is $1 per token
    assert stored_cheque.canManagerPay == True
    assert stored_cheque.canBePulled == False
    assert stored_cheque.creator == bob
    assert stored_cheque.active == True
    
    # Verify chequePeriodData was updated
    updated_cheque_data = user_wallet_config.chequePeriodData()
    assert updated_cheque_data.numChequesCreatedInPeriod == initial_cheque_data.numChequesCreatedInPeriod + 1
    assert updated_cheque_data.totalUsdValueCreatedInPeriod == initial_cheque_data.totalUsdValueCreatedInPeriod + amount
    assert updated_cheque_data.totalNumChequesCreated == initial_cheque_data.totalNumChequesCreated + 1
    assert updated_cheque_data.totalUsdValueCreated == initial_cheque_data.totalUsdValueCreated + amount
    assert updated_cheque_data.lastChequeCreatedBlock == boa.env.evm.patch.block_number
    assert updated_cheque_data.periodStartBlock == boa.env.evm.patch.block_number  # First cheque starts the period
    
    # Verify numActiveCheques was incremented
    assert user_wallet_config.numActiveCheques() == initial_num_active + 1


def test_createCheque_event_emission(
    bob, alice, alpha_token, mock_ripe,
    user_wallet, cheque_book,
):
    """Test that ChequeCreated event is emitted with correct data"""
    # Setup - match the working test's pattern exactly
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
        False,  # canBePulled
        sender=bob
    )
    
    # Set price
    mock_ripe.setPrice(alpha_token.address, 2 * EIGHTEEN_DECIMALS)  # $2 per token
    
    # Create cheque and capture events
    amount = 75 * EIGHTEEN_DECIMALS
    unlock_blocks = ONE_DAY_IN_BLOCKS
    expiry_blocks = ONE_WEEK_IN_BLOCKS
    
    tx = cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        unlock_blocks,
        expiry_blocks,
        True,  # canManagerPay
        False,  # canBePulled
        sender=bob
    )
    
    # Verify event
    events = filter_logs(cheque_book, "ChequeCreated")
    assert len(events) == 1
    
    event = events[0]
    assert event.user == user_wallet.address
    assert event.recipient == alice
    assert event.asset == alpha_token.address
    assert event.amount == amount
    assert event.usdValue == amount * 2  # $2 per token
    # Calculate expected values
    expected_unlock = boa.env.evm.patch.block_number + unlock_blocks
    expected_expiry = expected_unlock + expiry_blocks
    assert event.unlockBlock == expected_unlock
    assert event.expiryBlock == expected_expiry
    assert event.canManagerPay == True
    assert event.canBePulled == False
    assert event.creator == bob


def test_createCheque_fails_access_control(
    bob, alice, charlie, alpha_token, mock_ripe,
    user_wallet, cheque_book,
):
    """Test that createCheque fails when caller lacks permission"""
    # Setup
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
        False,  # canManagersCreateCheques - Disable manager creation
        True,  # canManagerPay
        False,  # canBePulled
        sender=bob
    )
    
    # Set price
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
    
    # Charlie (non-owner, non-manager) tries to create cheque
    with boa.reverts("not authorized to create cheques"):
        cheque_book.createCheque(
            user_wallet.address,
            alice,
            alpha_token.address,
            50 * EIGHTEEN_DECIMALS,
            ONE_DAY_IN_BLOCKS,
            ONE_WEEK_IN_BLOCKS,
            True,
            False,
            sender=charlie
        )


def test_createCheque_fails_invalid_inputs(
    bob, alice, alpha_token, mock_ripe,
    user_wallet, cheque_book,
):
    """Test that createCheque fails when inputs are invalid"""
    # Setup
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
        False,  # canBePulled
        sender=bob
    )
    
    # Set price
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
    
    # Try to create cheque with zero amount
    with boa.reverts("invalid cheque"):
        cheque_book.createCheque(
            user_wallet.address,
            alice,
            alpha_token.address,
            0,  # Invalid: zero amount
            ONE_DAY_IN_BLOCKS,
            ONE_WEEK_IN_BLOCKS,
            True,
            False,
            sender=bob
        )


def test_createCheque_replaces_existing_cheque(
    bob, alice, alpha_token, mock_ripe,
    user_wallet, user_wallet_config, cheque_book,
):
    """Test that creating a cheque for existing recipient replaces the old one"""
    # Setup
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
        False,  # canBePulled
        sender=bob
    )
    
    # Set price
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
    
    # Create first cheque
    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        50 * EIGHTEEN_DECIMALS,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,
        False,
        sender=bob
    )
    
    initial_num_active = user_wallet_config.numActiveCheques()
    
    # Create second cheque for same recipient (should replace)
    new_amount = 100 * EIGHTEEN_DECIMALS
    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        new_amount,
        ONE_DAY_IN_BLOCKS,  # Use same unlock period as first
        ONE_WEEK_IN_BLOCKS,  # Use same expiry period as first
        True,  # Keep same canManagerPay as first cheque
        False,
        sender=bob
    )
    
    # Verify cheque was replaced
    stored_cheque = user_wallet_config.cheques(alice)
    assert stored_cheque.amount == new_amount
    assert stored_cheque.canManagerPay == True
    assert stored_cheque.canBePulled == False
    
    # Verify numActiveCheques didn't increase (replacement)
    assert user_wallet_config.numActiveCheques() == initial_num_active


def test_createCheque_with_expensive_delay(
    bob, alice, alpha_token, mock_ripe,
    user_wallet, user_wallet_config, cheque_book,
):
    """Test that expensive cheques get proper delay applied"""
    # Setup with instant threshold
    instant_threshold = 100 * EIGHTEEN_DECIMALS
    expensive_delay = ONE_DAY_IN_BLOCKS * 3
    
    cheque_book.setChequeSettings(
        user_wallet.address,
        0,  # maxNumActiveCheques
        0,  # maxChequeUsdValue
        instant_threshold,  # instantUsdThreshold
        0,  # perPeriodPaidUsdCap
        0,  # maxNumChequesPaidPerPeriod
        0,  # payCooldownBlocks
        0,  # perPeriodCreatedUsdCap
        0,  # maxNumChequesCreatedPerPeriod
        0,  # createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # periodLength
        expensive_delay,  # expensiveDelayBlocks
        0,  # defaultExpiryBlocks
        [],  # allowedAssets
        True,  # canManagersCreateCheques
        True,  # canManagerPay
        False,  # canBePulled
        sender=bob
    )
    
    # Set price
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
    
    # Create expensive cheque (above threshold)
    amount = 150 * EIGHTEEN_DECIMALS  # Above threshold
    unlock_blocks = ONE_DAY_IN_BLOCKS  # Less than expensive delay
    
    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        unlock_blocks,
        ONE_WEEK_IN_BLOCKS,
        True,
        False,
        sender=bob
    )
    
    # Verify expensive delay was applied
    stored_cheque = user_wallet_config.cheques(alice)
    expected_unlock = boa.env.evm.patch.block_number + expensive_delay
    assert stored_cheque.unlockBlock == expected_unlock


def test_createCheque_with_cheque_period_data_manipulation(
    bob, alice, charlie, alpha_token, mock_ripe,
    user_wallet, user_wallet_config, cheque_book,
    createChequeData
):
    """Test cheque creation with direct manipulation of chequePeriodData"""
    # Setup
    cheque_book.setChequeSettings(
        user_wallet.address,
        0,  # maxNumActiveCheques
        0,  # maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # instantUsdThreshold
        0,  # perPeriodPaidUsdCap
        0,  # maxNumChequesPaidPerPeriod
        0,  # payCooldownBlocks
        1000 * EIGHTEEN_DECIMALS,  # perPeriodCreatedUsdCap
        5,  # maxNumChequesCreatedPerPeriod
        0,  # createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # periodLength
        ONE_DAY_IN_BLOCKS,  # expensiveDelayBlocks
        0,  # defaultExpiryBlocks
        [],  # allowedAssets
        True,  # canManagersCreateCheques
        True,  # canManagerPay
        False,  # canBePulled
        sender=bob
    )
    
    # Set price
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
    
    # Manipulate chequePeriodData to simulate existing period activity
    existing_cheque_data = createChequeData(
        _numChequesCreatedInPeriod=3,
        _totalUsdValueCreatedInPeriod=500 * EIGHTEEN_DECIMALS,
        _totalNumChequesCreated=10,
        _totalUsdValueCreated=2000 * EIGHTEEN_DECIMALS,
        _periodStartBlock=boa.env.evm.patch.block_number,
    )
    
    # Create a dummy cheque struct for direct call
    dummy_cheque = (
        alice,  # recipient
        alpha_token.address,  # asset
        EIGHTEEN_DECIMALS,  # amount
        boa.env.evm.patch.block_number,  # creationBlock
        boa.env.evm.patch.block_number + ONE_DAY_IN_BLOCKS,  # unlockBlock
        boa.env.evm.patch.block_number + ONE_WEEK_IN_BLOCKS,  # expiryBlock
        EIGHTEEN_DECIMALS,  # usdValueOnCreation
        True,  # canManagerPay
        False,  # canBePulled
        cheque_book.address,  # creator (using cheque_book as authorized sender)
        True,  # active
    )
    
    # Call createCheque directly on user_wallet_config
    user_wallet_config.createCheque(
        alice,
        dummy_cheque,
        existing_cheque_data,
        False,  # not existing cheque
        sender=cheque_book.address
    )
    
    # Now create a real cheque through ChequeBook
    amount = 200 * EIGHTEEN_DECIMALS
    cheque_book.createCheque(
        user_wallet.address,
        charlie,  # Different recipient
        alpha_token.address,
        amount,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,
        False,
        sender=bob
    )
    
    # Verify the period data was properly updated
    final_cheque_data = user_wallet_config.chequePeriodData()
    assert final_cheque_data.numChequesCreatedInPeriod == 4  # 3 + 1
    assert final_cheque_data.totalUsdValueCreatedInPeriod == 700 * EIGHTEEN_DECIMALS  # 500 + 200
    assert final_cheque_data.totalNumChequesCreated == 11  # 10 + 1
    assert final_cheque_data.totalUsdValueCreated == 2200 * EIGHTEEN_DECIMALS  # 2000 + 200


def test_createCheque_period_reset(
    bob, alice, charlie, alpha_token, mock_ripe,
    user_wallet, user_wallet_config, cheque_book,
    createChequeData
):
    """Test that period data resets after period expires"""
    # Setup with short period for testing
    period_length = ONE_DAY_IN_BLOCKS  # Minimum allowed period
    
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
        period_length,  # periodLength
        ONE_DAY_IN_BLOCKS,  # expensiveDelayBlocks
        0,  # defaultExpiryBlocks
        [],  # allowedAssets
        True,  # canManagersCreateCheques
        True,  # canManagerPay
        False,  # canBePulled
        sender=bob
    )
    
    # Set price
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
    
    # Set up initial period data with a past period
    initial_cheque_data = createChequeData(
        _numChequesCreatedInPeriod=5,
        _totalUsdValueCreatedInPeriod=500 * EIGHTEEN_DECIMALS,
        _totalNumChequesCreated=20,
        _totalUsdValueCreated=2000 * EIGHTEEN_DECIMALS,
        _periodStartBlock=boa.env.evm.patch.block_number,  # Current period
    )
    
    # Create dummy cheque to set initial data
    dummy_cheque = (
        alice,  # recipient
        alpha_token.address,  # asset
        EIGHTEEN_DECIMALS,  # amount
        boa.env.evm.patch.block_number,  # creationBlock
        boa.env.evm.patch.block_number + ONE_DAY_IN_BLOCKS,  # unlockBlock
        boa.env.evm.patch.block_number + ONE_WEEK_IN_BLOCKS,  # expiryBlock
        EIGHTEEN_DECIMALS,  # usdValueOnCreation
        True,  # canManagerPay
        False,  # canBePulled
        cheque_book.address,  # creator
        True,  # active
    )
    
    user_wallet_config.createCheque(
        alice,
        dummy_cheque,
        initial_cheque_data,
        False,
        sender=cheque_book.address
    )
    
    # Advance past the period
    boa.env.time_travel(blocks=period_length + 20)
    
    # Create new cheque (should trigger period reset)
    amount = 100 * EIGHTEEN_DECIMALS
    cheque_book.createCheque(
        user_wallet.address,
        charlie,  # Different recipient
        alpha_token.address,
        amount,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,
        False,
        sender=bob
    )
    
    # Verify period was reset
    final_cheque_data = user_wallet_config.chequePeriodData()
    assert final_cheque_data.numChequesCreatedInPeriod == 1  # Reset to 1
    assert final_cheque_data.totalUsdValueCreatedInPeriod == amount  # Reset to new amount
    assert final_cheque_data.totalNumChequesCreated == 21  # Cumulative: 20 + 1
    assert final_cheque_data.totalUsdValueCreated == 2100 * EIGHTEEN_DECIMALS  # Cumulative: 2000 + 100
    assert final_cheque_data.periodStartBlock == boa.env.evm.patch.block_number  # New period start


def test_createCheque_fails_invalid_inputs(
    bob, alice, alpha_token, mock_ripe,
    user_wallet, cheque_book,
):
    """Test that createCheque fails when inputs are invalid"""
    # Setup
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
        False,  # canBePulled
        sender=bob
    )
    
    # Set price
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
    
    # Try to create cheque with zero amount
    with boa.reverts("invalid cheque"):
        cheque_book.createCheque(
            user_wallet.address,
            alice,
            alpha_token.address,
            0,  # Invalid: zero amount
            ONE_DAY_IN_BLOCKS,
            ONE_WEEK_IN_BLOCKS,
            True,
            False,
            sender=bob
        )


def test_createCheque_fails_validation_checks(
    bob, alice, alpha_token,
    user_wallet, cheque_book,
):
    """Test that createCheque fails when validation checks fail"""
    # Setup
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
        False,  # canBePulled
        sender=bob
    )
    
    # Don't set price for alpha_token (zero USD value)
    
    # Try to create cheque with asset that has no price
    with boa.reverts("invalid cheque"):
        cheque_book.createCheque(
            user_wallet.address,
            alice,
            alpha_token.address,
            50 * EIGHTEEN_DECIMALS,
            ONE_DAY_IN_BLOCKS,
            ONE_WEEK_IN_BLOCKS,
            True,
            False,
            sender=bob
        )


def test_createCheque_expiry_calculation_paths(
    bob, alice, charlie, alpha_token, mock_ripe,
    user_wallet, user_wallet_config, cheque_book,
):
    """Test different expiry calculation paths (explicit, default, time lock fallback)"""
    time_lock = user_wallet_config.timeLock()
    
    # Test 1: Explicit expiry
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
        0,  # defaultExpiryBlocks - No default
        [],  # allowedAssets
        True,  # canManagersCreateCheques
        True,  # canManagerPay
        False,  # canBePulled
        sender=bob
    )
    
    # Set price
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
    
    # Create cheque with explicit expiry
    unlock_blocks = ONE_DAY_IN_BLOCKS
    expiry_blocks = ONE_DAY_IN_BLOCKS * 3
    
    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        50 * EIGHTEEN_DECIMALS,
        unlock_blocks,
        expiry_blocks,  # Explicit expiry
        True,
        False,
        sender=bob
    )
    
    # Verify explicit expiry was used
    stored_cheque = user_wallet_config.cheques(alice)
    expected_unlock = boa.env.evm.patch.block_number + unlock_blocks
    expected_expiry = expected_unlock + expiry_blocks
    assert stored_cheque.expiryBlock == expected_expiry
    
    # Test 2: Default expiry
    default_expiry = ONE_DAY_IN_BLOCKS * 2
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
        default_expiry,  # defaultExpiryBlocks
        [],  # allowedAssets
        True,  # canManagersCreateCheques
        True,  # canManagerPay
        False,  # canBePulled
        sender=bob
    )
    
    # Create cheque with 0 expiry (should use default)
    cheque_book.createCheque(
        user_wallet.address,
        charlie,  # Use charlie as second recipient
        alpha_token.address,
        50 * EIGHTEEN_DECIMALS,
        unlock_blocks,
        0,  # No explicit expiry, should use default
        True,
        False,
        sender=bob
    )
    
    # Verify default expiry was used
    stored_cheque = user_wallet_config.cheques(charlie)
    expected_unlock = boa.env.evm.patch.block_number + unlock_blocks
    expected_expiry = expected_unlock + default_expiry
    assert stored_cheque.expiryBlock == expected_expiry
    
    # Test 3: Time lock fallback (no explicit, no default)
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
        0,  # defaultExpiryBlocks - No default
        [],  # allowedAssets
        True,  # canManagersCreateCheques
        True,  # canManagerPay
        False,  # canBePulled
        sender=bob
    )
    
    # Create cheque with 0 expiry (should use time lock)
    # Use alice again but replace the old cheque
    cheque_book.createCheque(
        user_wallet.address,
        alice,  # Replace alice's cheque
        alpha_token.address,
        50 * EIGHTEEN_DECIMALS,
        unlock_blocks,
        0,  # No explicit expiry, no default, should use time lock
        True,
        False,
        sender=bob
    )
    
    # Verify time lock was used for expiry
    stored_cheque = user_wallet_config.cheques(alice)
    expected_unlock = boa.env.evm.patch.block_number + unlock_blocks
    expected_expiry = expected_unlock + time_lock
    assert stored_cheque.expiryBlock == expected_expiry


#################
# Cancel Cheque #
#################


def test_cancelCheque_success_by_owner(
    bob, alice, alpha_token, mock_ripe,
    user_wallet, user_wallet_config, cheque_book
):
    """Test successful cheque cancellation by owner"""
    # Setup
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
        False,  # canBePulled
        sender=bob
    )
    
    # Set price
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
    
    # Create a cheque first
    amount = 50 * EIGHTEEN_DECIMALS
    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,
        False,
        sender=bob
    )
    
    # Verify cheque exists and is active
    cheque_before = user_wallet_config.cheques(alice)
    assert cheque_before.active == True
    
    # Cancel the cheque
    tx = cheque_book.cancelCheque(
        user_wallet.address,
        alice,
        sender=bob  # Owner canceling
    )
    
    # Verify cheque was cancelled
    cheque_after = user_wallet_config.cheques(alice)
    assert cheque_after.active == False
    
    # Verify ChequeCancelled event was emitted
    events = filter_logs(cheque_book, "ChequeCancelled")
    assert len(events) == 1
    
    event = events[0]
    assert event.user == user_wallet.address
    assert event.recipient == alice
    assert event.asset == alpha_token.address
    assert event.amount == amount
    assert event.usdValue == amount  # Price is $1 per token
    assert event.unlockBlock == cheque_before.unlockBlock
    assert event.expiryBlock == cheque_before.expiryBlock
    assert event.canManagerPay == True
    assert event.canBePulled == False
    assert event.cancelledBy == bob


def test_cancelCheque_fails_non_owner_without_security_perms(
    bob, alice, charlie, alpha_token, mock_ripe,
    user_wallet, cheque_book
):
    """Test that non-owner without security permissions cannot cancel cheque"""
    # Setup
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
        False,  # canBePulled
        sender=bob
    )
    
    # Set price
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
    
    # Create a cheque first
    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        50 * EIGHTEEN_DECIMALS,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,
        False,
        sender=bob
    )
    
    # Try to cancel as non-owner without security permissions
    with boa.reverts("no perms"):
        cheque_book.cancelCheque(
            user_wallet.address,
            alice,
            sender=charlie  # Non-owner, no security perms
        )


def test_cancelCheque_fails_invalid_user_wallet(
    bob, alice, user_wallet, cheque_book
):
    """Test that cancel fails with invalid user wallet"""
    # Try to cancel with invalid user wallet
    invalid_wallet = boa.env.generate_address()
    with boa.reverts("invalid user wallet"):
        cheque_book.cancelCheque(
            invalid_wallet,
            alice,
            sender=bob
        )


def test_cancelCheque_fails_no_active_cheque(
    bob, alice, user_wallet, cheque_book
):
    """Test that cancel fails when no active cheque exists for recipient"""
    # Setup
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
        False,  # canBePulled
        sender=bob
    )
    
    # Try to cancel non-existent cheque
    with boa.reverts("no active cheque"):
        cheque_book.cancelCheque(
            user_wallet.address,
            alice,  # No cheque exists for alice
            sender=bob
        )


def test_cancelCheque_fails_already_cancelled(
    bob, alice, alpha_token, mock_ripe,
    user_wallet, cheque_book
):
    """Test that cancel fails when cheque is already cancelled"""
    # Setup
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
        False,  # canBePulled
        sender=bob
    )
    
    # Set price
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
    
    # Create a cheque first
    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        50 * EIGHTEEN_DECIMALS,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,
        False,
        sender=bob
    )
    
    # Cancel the cheque once
    cheque_book.cancelCheque(
        user_wallet.address,
        alice,
        sender=bob
    )
    
    # Try to cancel again (should fail)
    with boa.reverts("no active cheque"):
        cheque_book.cancelCheque(
            user_wallet.address,
            alice,
            sender=bob
        )


def test_cancelCheque_event_contains_correct_data(
    bob, alice, alpha_token, mock_ripe,
    user_wallet, user_wallet_config, cheque_book
):
    """Test that ChequeCancelled event contains all correct data"""
    # Setup
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
        False,  # canBePulled
        sender=bob
    )
    
    # Set price to $2 per token
    mock_ripe.setPrice(alpha_token.address, 2 * EIGHTEEN_DECIMALS)
    
    # Create a cheque with specific parameters
    amount = 75 * EIGHTEEN_DECIMALS
    unlock_blocks = ONE_DAY_IN_BLOCKS * 2
    expiry_blocks = ONE_WEEK_IN_BLOCKS
    
    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        unlock_blocks,
        expiry_blocks,
        True,  # canManagerPay
        False,  # canBePulled
        sender=bob
    )
    
    # Get the created cheque data
    created_cheque = user_wallet_config.cheques(alice)
    
    # Cancel the cheque
    tx = cheque_book.cancelCheque(
        user_wallet.address,
        alice,
        sender=bob
    )
    
    # Verify event data
    events = filter_logs(cheque_book, "ChequeCancelled")
    assert len(events) == 1
    
    event = events[0]
    assert event.user == user_wallet.address
    assert event.recipient == alice
    assert event.asset == alpha_token.address
    assert event.amount == amount
    assert event.usdValue == amount * 2  # $2 per token
    assert event.unlockBlock == created_cheque.unlockBlock
    assert event.expiryBlock == created_cheque.expiryBlock
    assert event.canManagerPay == True
    assert event.canBePulled == False
    assert event.cancelledBy == bob


def test_cancelCheque_multiple_cheques_cancel_specific(
    bob, alice, charlie, alpha_token, mock_ripe,
    user_wallet, user_wallet_config, cheque_book
):
    """Test canceling a specific cheque when multiple exist"""
    # Setup
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
        False,  # canBePulled
        sender=bob
    )
    
    # Set price
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
    
    # Create cheques for both alice and charlie
    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        50 * EIGHTEEN_DECIMALS,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,
        False,
        sender=bob
    )
    
    cheque_book.createCheque(
        user_wallet.address,
        charlie,
        alpha_token.address,
        75 * EIGHTEEN_DECIMALS,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,
        False,
        sender=bob
    )
    
    # Verify both cheques exist
    alice_cheque_before = user_wallet_config.cheques(alice)
    charlie_cheque_before = user_wallet_config.cheques(charlie)
    assert alice_cheque_before.active == True
    assert charlie_cheque_before.active == True
    
    # Cancel only alice's cheque
    cheque_book.cancelCheque(
        user_wallet.address,
        alice,
        sender=bob
    )
    
    # Verify alice's cheque is cancelled but charlie's is still active
    alice_cheque_after = user_wallet_config.cheques(alice)
    charlie_cheque_after = user_wallet_config.cheques(charlie)
    assert alice_cheque_after.active == False
    assert charlie_cheque_after.active == True
    
    # Verify only one ChequeCancelled event
    events = filter_logs(cheque_book, "ChequeCancelled")
    assert len(events) == 1
    assert events[0].recipient == alice


def test_cancelCheque_function_returns_true(
    bob, alice, alpha_token, mock_ripe,
    user_wallet, cheque_book
):
    """Test that cancelCheque function returns True on success"""
    # Setup
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
        False,  # canBePulled
        sender=bob
    )
    
    # Set price
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
    
    # Create a cheque
    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        50 * EIGHTEEN_DECIMALS,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,
        False,
        sender=bob
    )
    
    # Cancel the cheque and verify return value
    result = cheque_book.cancelCheque(
        user_wallet.address,
        alice,
        sender=bob
    )
    
    # Function should return True
    assert result == True

