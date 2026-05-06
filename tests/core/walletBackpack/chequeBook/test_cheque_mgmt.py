import boa
import pytest

from constants import EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ONE_MONTH_IN_BLOCKS, ZERO_ADDRESS
from contracts.core.userWallet import UserWallet, UserWalletConfig
from conf_utils import filter_logs, set_live_cheque_settings

ONE_WEEK_IN_BLOCKS = ONE_DAY_IN_BLOCKS * 7
ONE_HOUR_IN_BLOCKS = ONE_DAY_IN_BLOCKS // 24
CHEQUE_SETTING_FIELDS = (
    "maxNumActiveCheques",
    "maxChequeUsdValue",
    "instantUsdThreshold",
    "perPeriodPaidUsdCap",
    "maxNumChequesPaidPerPeriod",
    "payCooldownBlocks",
    "perPeriodCreatedUsdCap",
    "maxNumChequesCreatedPerPeriod",
    "createCooldownBlocks",
    "periodLength",
    "expensiveDelayBlocks",
    "defaultExpiryBlocks",
    "allowedAssets",
    "canManagersCreateCheques",
    "canManagerPay",
    "canBePulled",
)

def restrictive_cheque_settings(createChequeSettings, **overrides):
    settings = dict(
        _maxNumActiveCheques=2,
        _maxChequeUsdValue=300 * EIGHTEEN_DECIMALS,
        _instantUsdThreshold=25 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_DAY_IN_BLOCKS,
        _expensiveDelayBlocks=2 * ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=ONE_DAY_IN_BLOCKS,
        _canManagersCreateCheques=False,
        _canManagerPay=False,
        _canBePulled=False,
    )
    settings.update(overrides)
    return createChequeSettings(**settings)


def _cheque_setting_value(settings, field):
    value = getattr(settings, field)
    if field == "allowedAssets":
        return list(value)
    return value


def assert_cheque_settings_match(actual, expected):
    for field in CHEQUE_SETTING_FIELDS:
        assert _cheque_setting_value(actual, field) == _cheque_setting_value(expected, field)


def assert_pending_only_changes_field(live_settings, pending_settings, target_field):
    for field in CHEQUE_SETTING_FIELDS:
        if field == target_field:
            continue
        assert _cheque_setting_value(pending_settings, field) == _cheque_setting_value(live_settings, field)


def assert_pending_cheque_settings_empty(cheque_book, user_wallet):
    pending = cheque_book.pendingChequeSettings(user_wallet)
    settings = pending.settings
    assert pending.initiatedBlock == 0
    assert pending.confirmBlock == 0
    assert pending.currentOwner == ZERO_ADDRESS
    assert settings.maxNumActiveCheques == 0
    assert settings.maxChequeUsdValue == 0
    assert settings.instantUsdThreshold == 0
    assert settings.perPeriodPaidUsdCap == 0
    assert settings.maxNumChequesPaidPerPeriod == 0
    assert settings.payCooldownBlocks == 0
    assert settings.perPeriodCreatedUsdCap == 0
    assert settings.maxNumChequesCreatedPerPeriod == 0
    assert settings.createCooldownBlocks == 0
    assert settings.periodLength == 0
    assert settings.expensiveDelayBlocks == 0
    assert settings.defaultExpiryBlocks == 0
    assert list(settings.allowedAssets) == []
    assert settings.canManagersCreateCheques == False
    assert settings.canManagerPay == False
    assert settings.canBePulled == False


def assert_cheque_settings_values(settings, expected):
    assert settings.maxNumActiveCheques == expected["maxNumActiveCheques"]
    assert settings.maxChequeUsdValue == expected["maxChequeUsdValue"]
    assert settings.instantUsdThreshold == expected["instantUsdThreshold"]
    assert settings.perPeriodPaidUsdCap == expected["perPeriodPaidUsdCap"]
    assert settings.maxNumChequesPaidPerPeriod == expected["maxNumChequesPaidPerPeriod"]
    assert settings.payCooldownBlocks == expected["payCooldownBlocks"]
    assert settings.perPeriodCreatedUsdCap == expected["perPeriodCreatedUsdCap"]
    assert settings.maxNumChequesCreatedPerPeriod == expected["maxNumChequesCreatedPerPeriod"]
    assert settings.createCooldownBlocks == expected["createCooldownBlocks"]
    assert settings.periodLength == expected["periodLength"]
    assert settings.expensiveDelayBlocks == expected["expensiveDelayBlocks"]
    assert settings.defaultExpiryBlocks == expected["defaultExpiryBlocks"]
    assert list(settings.allowedAssets) == expected["allowedAssets"]
    assert settings.canManagersCreateCheques == expected["canManagersCreateCheques"]
    assert settings.canManagerPay == expected["canManagerPay"]
    assert settings.canBePulled == expected["canBePulled"]


def set_timelock_clamp_cheque_settings(
    cheque_book,
    user_wallet,
    createChequeSettings,
    *,
    sender,
    instant_threshold=100 * EIGHTEEN_DECIMALS,
    expensive_delay=ONE_DAY_IN_BLOCKS,
    default_expiry=ONE_DAY_IN_BLOCKS,
):
    settings = createChequeSettings(
        _maxNumActiveCheques=0,
        _maxChequeUsdValue=0,
        _instantUsdThreshold=instant_threshold,
        _periodLength=ONE_MONTH_IN_BLOCKS,
        _expensiveDelayBlocks=expensive_delay,
        _defaultExpiryBlocks=default_expiry,
        _canManagersCreateCheques=True,
        _canManagerPay=True,
        _canBePulled=False,
    )
    set_live_cheque_settings(cheque_book, user_wallet.address, *settings, sender=sender)


def assert_single_field_widening_stages_pending(
    bob,
    user_wallet,
    user_wallet_config,
    cheque_book,
    createChequeSettings,
    *,
    target_field,
    baseline_overrides,
    widening_overrides,
    expected_live_value,
    expected_pending_value,
):
    baseline = restrictive_cheque_settings(createChequeSettings, **baseline_overrides)
    set_live_cheque_settings(cheque_book, user_wallet.address, *baseline, sender=bob)
    current = user_wallet_config.chequeSettings()

    widened_overrides = dict(baseline_overrides)
    widened_overrides.update(widening_overrides)
    widened = restrictive_cheque_settings(createChequeSettings, **widened_overrides)
    cheque_book.setChequeSettings(user_wallet.address, *widened, sender=bob)

    live = user_wallet_config.chequeSettings()
    pending = cheque_book.pendingChequeSettings(user_wallet.address)
    assert cheque_book.hasPendingChequeSettings(user_wallet.address)
    assert_cheque_settings_match(live, current)
    assert_pending_only_changes_field(current, pending.settings, target_field)
    assert _cheque_setting_value(live, target_field) == expected_live_value
    assert _cheque_setting_value(pending.settings, target_field) == expected_pending_value

    cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=bob)


def assert_immediate_update_without_pending(
    bob,
    user_wallet,
    user_wallet_config,
    cheque_book,
    createChequeSettings,
    *,
    target_field,
    baseline_overrides,
    update_overrides,
    expected_value,
):
    baseline = restrictive_cheque_settings(createChequeSettings, **baseline_overrides)
    set_live_cheque_settings(cheque_book, user_wallet.address, *baseline, sender=bob)
    cheque_book.get_logs()

    updated_overrides = dict(baseline_overrides)
    updated_overrides.update(update_overrides)
    updated = restrictive_cheque_settings(createChequeSettings, **updated_overrides)
    cheque_book.setChequeSettings(user_wallet.address, *updated, sender=bob)
    logs = cheque_book.get_logs()
    modified_events = [e for e in logs if type(e).__name__ == "ChequeSettingsModified"]
    pending_events = [e for e in logs if type(e).__name__ == "ChequeSettingsPending"]

    live = user_wallet_config.chequeSettings()
    assert _cheque_setting_value(live, target_field) == expected_value
    assert cheque_book.hasPendingChequeSettings(user_wallet.address) == False
    assert_pending_cheque_settings_empty(cheque_book, user_wallet.address)
    assert len(modified_events) == 1
    assert modified_events[0].user == user_wallet.address
    assert len(pending_events) == 0


####################
# Cheque Creation #
####################


def test_createCheque_success_and_storage(
    bob, alice, alpha_token, mock_ripe,
    user_wallet, user_wallet_config, cheque_book,
):
    """Test successful cheque creation and verify data is stored correctly"""
    # Setup cheque settings
    set_live_cheque_settings(cheque_book,
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
    set_live_cheque_settings(cheque_book,
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
    set_live_cheque_settings(cheque_book,
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


##############################
# Cheque Settings Timelock   #
##############################


def test_setChequeSettings_tightening_applies_immediately(
    bob, alpha_token, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    """Tightening-only cheque settings should update live state immediately"""
    settings = createChequeSettings(
        _maxNumActiveCheques=1,
        _maxChequeUsdValue=200 * EIGHTEEN_DECIMALS,
        _instantUsdThreshold=50 * EIGHTEEN_DECIMALS,
        _perPeriodPaidUsdCap=400 * EIGHTEEN_DECIMALS,
        _maxNumChequesPaidPerPeriod=2,
        _payCooldownBlocks=ONE_HOUR_IN_BLOCKS,
        _perPeriodCreatedUsdCap=400 * EIGHTEEN_DECIMALS,
        _maxNumChequesCreatedPerPeriod=2,
        _createCooldownBlocks=ONE_HOUR_IN_BLOCKS,
        _periodLength=ONE_DAY_IN_BLOCKS,
        _expensiveDelayBlocks=2 * ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=ONE_DAY_IN_BLOCKS,
        _allowedAssets=[alpha_token.address],
        _canManagersCreateCheques=False,
        _canManagerPay=False,
        _canBePulled=False,
    )

    cheque_book.setChequeSettings(user_wallet.address, *settings, sender=bob)

    live = user_wallet_config.chequeSettings()
    pending = cheque_book.pendingChequeSettingsMeta(user_wallet.address)
    assert live.maxNumActiveCheques == 1
    assert live.maxChequeUsdValue == 200 * EIGHTEEN_DECIMALS
    assert live.instantUsdThreshold == 50 * EIGHTEEN_DECIMALS
    assert live.periodLength == ONE_DAY_IN_BLOCKS
    assert live.canManagersCreateCheques == False
    assert live.canManagerPay == False
    assert live.canBePulled == False
    assert pending[1] == 0


def test_setChequeSettings_identical_resubmission_applies_immediately(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    """Resubmitting the live settings should remain immediate and should not stage pending state"""
    settings = restrictive_cheque_settings(createChequeSettings)
    set_live_cheque_settings(cheque_book, user_wallet.address, *settings, sender=bob)

    cheque_book.setChequeSettings(user_wallet.address, *settings, sender=bob)

    live = user_wallet_config.chequeSettings()
    assert live.maxNumActiveCheques == 2
    assert live.maxChequeUsdValue == 300 * EIGHTEEN_DECIMALS
    assert live.instantUsdThreshold == 25 * EIGHTEEN_DECIMALS
    assert live.periodLength == ONE_DAY_IN_BLOCKS
    assert not cheque_book.hasPendingChequeSettings(user_wallet.address)


def test_setChequeSettings_widening_creates_pending_only(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    """Widening-only cheque settings should stage pending state and leave live unchanged"""
    set_live_cheque_settings(
        cheque_book,
        user_wallet.address,
        *createChequeSettings(
            _maxNumActiveCheques=2,
            _maxChequeUsdValue=300 * EIGHTEEN_DECIMALS,
            _instantUsdThreshold=25 * EIGHTEEN_DECIMALS,
            _periodLength=ONE_DAY_IN_BLOCKS,
            _expensiveDelayBlocks=2 * ONE_DAY_IN_BLOCKS,
            _defaultExpiryBlocks=ONE_DAY_IN_BLOCKS,
            _canManagersCreateCheques=False,
            _canManagerPay=False,
            _canBePulled=False,
        ),
        sender=bob,
    )
    current = user_wallet_config.chequeSettings()
    settings = createChequeSettings(
        _maxNumActiveCheques=0,
        _instantUsdThreshold=current.instantUsdThreshold,
        _periodLength=current.periodLength,
        _expensiveDelayBlocks=current.expensiveDelayBlocks,
        _defaultExpiryBlocks=current.defaultExpiryBlocks,
        _canManagersCreateCheques=current.canManagersCreateCheques,
        _canManagerPay=current.canManagerPay,
        _canBePulled=current.canBePulled,
    )

    cheque_book.setChequeSettings(user_wallet.address, *settings, sender=bob)
    pending_event = filter_logs(cheque_book, "ChequeSettingsPending")[-1]

    live = user_wallet_config.chequeSettings()
    pending = cheque_book.pendingChequeSettingsMeta(user_wallet.address)
    assert live.maxNumActiveCheques == current.maxNumActiveCheques
    assert pending_event.maxNumActiveCheques == 0
    assert cheque_book.hasPendingChequeSettings(user_wallet.address)
    assert pending[0] != 0
    assert pending[1] == pending[0] + user_wallet_config.timeLock()
    assert pending[2] == bob

    cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=bob)
    assert not cheque_book.hasPendingChequeSettings(user_wallet.address)


def test_pendingChequeSettings_public_getter_returns_full_pending_config(
    bob, alpha_token, bravo_token, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    """The public pending settings getter should expose the full staged config"""
    baseline = restrictive_cheque_settings(
        createChequeSettings,
        _allowedAssets=[alpha_token.address],
    )
    set_live_cheque_settings(cheque_book, user_wallet.address, *baseline, sender=bob)

    staged = createChequeSettings(
        _maxNumActiveCheques=0,
        _maxChequeUsdValue=0,
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _perPeriodPaidUsdCap=0,
        _maxNumChequesPaidPerPeriod=0,
        _payCooldownBlocks=0,
        _perPeriodCreatedUsdCap=0,
        _maxNumChequesCreatedPerPeriod=0,
        _createCooldownBlocks=0,
        _periodLength=ONE_DAY_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=2 * ONE_DAY_IN_BLOCKS,
        _allowedAssets=[alpha_token.address, bravo_token.address],
        _canManagersCreateCheques=True,
        _canManagerPay=True,
        _canBePulled=True,
    )
    cheque_book.setChequeSettings(user_wallet.address, *staged, sender=bob)

    pending = cheque_book.pendingChequeSettings(user_wallet.address)
    assert pending.currentOwner == bob
    assert pending.confirmBlock == pending.initiatedBlock + user_wallet_config.timeLock()

    expected_settings = {
        "maxNumActiveCheques": 0,
        "maxChequeUsdValue": 0,
        "instantUsdThreshold": 100 * EIGHTEEN_DECIMALS,
        "perPeriodPaidUsdCap": 0,
        "maxNumChequesPaidPerPeriod": 0,
        "payCooldownBlocks": 0,
        "perPeriodCreatedUsdCap": 0,
        "maxNumChequesCreatedPerPeriod": 0,
        "createCooldownBlocks": 0,
        "periodLength": ONE_DAY_IN_BLOCKS,
        "expensiveDelayBlocks": ONE_DAY_IN_BLOCKS,
        "defaultExpiryBlocks": 2 * ONE_DAY_IN_BLOCKS,
        "allowedAssets": [alpha_token.address, bravo_token.address],
        "canManagersCreateCheques": True,
        "canManagerPay": True,
        "canBePulled": True,
    }
    assert_cheque_settings_values(pending.settings, expected_settings)

    cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=bob)


def test_pendingChequeSettings_public_getter_no_pending_returns_zero_empty(
    user_wallet, cheque_book
):
    """The public pending settings getter should return the empty struct when nothing is pending"""
    assert cheque_book.hasPendingChequeSettings(user_wallet.address) == False
    assert_pending_cheque_settings_empty(cheque_book, user_wallet.address)


def test_pendingChequeSettings_public_getter_after_cancel_returns_zero_empty(
    bob, user_wallet, cheque_book, createChequeSettings
):
    """Cancelling pending settings should clear the public pending settings getter"""
    baseline = restrictive_cheque_settings(createChequeSettings)
    set_live_cheque_settings(cheque_book, user_wallet.address, *baseline, sender=bob)
    staged = restrictive_cheque_settings(
        createChequeSettings,
        _maxNumActiveCheques=0,
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=2 * ONE_DAY_IN_BLOCKS,
    )
    cheque_book.setChequeSettings(user_wallet.address, *staged, sender=bob)
    cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=bob)

    assert cheque_book.hasPendingChequeSettings(user_wallet.address) == False
    assert_pending_cheque_settings_empty(cheque_book, user_wallet.address)


def test_pendingChequeSettings_public_getter_after_confirm_returns_zero_empty(
    bob, user_wallet, cheque_book, createChequeSettings
):
    """Confirming pending settings should clear the public pending settings getter"""
    baseline = restrictive_cheque_settings(createChequeSettings)
    set_live_cheque_settings(cheque_book, user_wallet.address, *baseline, sender=bob)
    staged = restrictive_cheque_settings(
        createChequeSettings,
        _maxNumActiveCheques=0,
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=2 * ONE_DAY_IN_BLOCKS,
    )
    cheque_book.setChequeSettings(user_wallet.address, *staged, sender=bob)
    pending = cheque_book.pendingChequeSettings(user_wallet.address)
    boa.env.time_travel(blocks=pending.confirmBlock - boa.env.evm.patch.block_number)
    cheque_book.confirmPendingChequeSettings(user_wallet.address, sender=bob)

    assert cheque_book.hasPendingChequeSettings(user_wallet.address) == False
    assert_pending_cheque_settings_empty(cheque_book, user_wallet.address)


def test_pendingChequeSettings_public_getter_tightening_clears_pending(
    bob, alpha_token, user_wallet, cheque_book, createChequeSettings
):
    """A live tightening should apply immediately and clear the public pending getter"""
    baseline = restrictive_cheque_settings(createChequeSettings)
    set_live_cheque_settings(cheque_book, user_wallet.address, *baseline, sender=bob)
    staged = restrictive_cheque_settings(
        createChequeSettings,
        _maxNumActiveCheques=0,
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=2 * ONE_DAY_IN_BLOCKS,
    )
    cheque_book.setChequeSettings(user_wallet.address, *staged, sender=bob)

    tightening = createChequeSettings(
        _maxNumActiveCheques=1,
        _maxChequeUsdValue=150 * EIGHTEEN_DECIMALS,
        _instantUsdThreshold=10 * EIGHTEEN_DECIMALS,
        _perPeriodPaidUsdCap=250 * EIGHTEEN_DECIMALS,
        _maxNumChequesPaidPerPeriod=2,
        _payCooldownBlocks=ONE_HOUR_IN_BLOCKS,
        _perPeriodCreatedUsdCap=250 * EIGHTEEN_DECIMALS,
        _maxNumChequesCreatedPerPeriod=2,
        _createCooldownBlocks=ONE_HOUR_IN_BLOCKS,
        _periodLength=ONE_DAY_IN_BLOCKS,
        _expensiveDelayBlocks=2 * ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=ONE_DAY_IN_BLOCKS,
        _allowedAssets=[alpha_token.address],
        _canManagersCreateCheques=False,
        _canManagerPay=False,
        _canBePulled=False,
    )
    cheque_book.setChequeSettings(user_wallet.address, *tightening, sender=bob)

    assert cheque_book.hasPendingChequeSettings(user_wallet.address) == False
    assert_pending_cheque_settings_empty(cheque_book, user_wallet.address)


def test_setChequeSettings_allowedAssets_additional_asset_becomes_pending(
    bob, alpha_token, bravo_token, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    """Adding a newly allowed asset should be classified as widening"""
    baseline = restrictive_cheque_settings(createChequeSettings, _allowedAssets=[alpha_token.address])
    set_live_cheque_settings(cheque_book, user_wallet.address, *baseline, sender=bob)

    widened = restrictive_cheque_settings(
        createChequeSettings,
        _allowedAssets=[alpha_token.address, bravo_token.address],
    )
    cheque_book.setChequeSettings(user_wallet.address, *widened, sender=bob)

    live = user_wallet_config.chequeSettings()
    assert list(live.allowedAssets) == [alpha_token.address]
    assert cheque_book.hasPendingChequeSettings(user_wallet.address)

    cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=bob)


def test_setChequeSettings_allowedAssets_removal_applies_immediately(
    bob, alpha_token, bravo_token, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    """Removing an allowed asset is tightening and should apply immediately"""
    baseline = restrictive_cheque_settings(
        createChequeSettings,
        _allowedAssets=[alpha_token.address, bravo_token.address],
    )
    set_live_cheque_settings(cheque_book, user_wallet.address, *baseline, sender=bob)

    tightened = restrictive_cheque_settings(createChequeSettings, _allowedAssets=[alpha_token.address])
    cheque_book.setChequeSettings(user_wallet.address, *tightened, sender=bob)

    live = user_wallet_config.chequeSettings()
    assert list(live.allowedAssets) == [alpha_token.address]
    assert not cheque_book.hasPendingChequeSettings(user_wallet.address)


def test_setChequeSettings_allowedAssets_empty_list_becomes_pending(
    bob, alpha_token, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    """Going from a specific allowlist to empty-all-assets should be classified as widening"""
    baseline = restrictive_cheque_settings(createChequeSettings, _allowedAssets=[alpha_token.address])
    set_live_cheque_settings(cheque_book, user_wallet.address, *baseline, sender=bob)

    widened = restrictive_cheque_settings(createChequeSettings, _allowedAssets=[])
    cheque_book.setChequeSettings(user_wallet.address, *widened, sender=bob)

    live = user_wallet_config.chequeSettings()
    assert list(live.allowedAssets) == [alpha_token.address]
    assert cheque_book.hasPendingChequeSettings(user_wallet.address)

    cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=bob)


def test_setChequeSettings_second_widening_reverts_while_pending_exists(
    bob, user_wallet, cheque_book, createChequeSettings
):
    """A second widening cannot be staged while another widening is already pending"""
    set_live_cheque_settings(
        cheque_book,
        user_wallet.address,
        *createChequeSettings(
            _maxNumActiveCheques=2,
            _maxChequeUsdValue=300 * EIGHTEEN_DECIMALS,
            _instantUsdThreshold=25 * EIGHTEEN_DECIMALS,
            _periodLength=ONE_DAY_IN_BLOCKS,
            _expensiveDelayBlocks=2 * ONE_DAY_IN_BLOCKS,
            _defaultExpiryBlocks=ONE_DAY_IN_BLOCKS,
            _canManagersCreateCheques=False,
            _canManagerPay=False,
            _canBePulled=False,
        ),
        sender=bob,
    )

    first_widening = createChequeSettings(
        _maxNumActiveCheques=0,
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_DAY_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=2 * ONE_DAY_IN_BLOCKS,
        _canManagersCreateCheques=False,
        _canManagerPay=False,
        _canBePulled=False,
    )
    cheque_book.setChequeSettings(user_wallet.address, *first_widening, sender=bob)
    assert cheque_book.hasPendingChequeSettings(user_wallet.address)

    second_widening = createChequeSettings(
        _maxNumActiveCheques=0,
        _maxChequeUsdValue=0,
        _instantUsdThreshold=150 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_DAY_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=2 * ONE_DAY_IN_BLOCKS,
        _canManagersCreateCheques=False,
        _canManagerPay=True,
        _canBePulled=False,
    )
    with boa.reverts("pending cheque settings already exist"):
        cheque_book.setChequeSettings(user_wallet.address, *second_widening, sender=bob)

    cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=bob)


def test_setChequeSettings_defaultExpiry_timelock_equivalent_applies_immediately(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    """Switching between 0 and an explicit timeLock-equivalent expiry should not stage pending"""
    time_lock = user_wallet_config.timeLock()
    baseline = createChequeSettings(
        _maxNumActiveCheques=2,
        _maxChequeUsdValue=300 * EIGHTEEN_DECIMALS,
        _instantUsdThreshold=25 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_DAY_IN_BLOCKS,
        _expensiveDelayBlocks=2 * ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=0,
        _canManagersCreateCheques=False,
        _canManagerPay=False,
        _canBePulled=False,
    )
    set_live_cheque_settings(cheque_book, user_wallet.address, *baseline, sender=bob)

    equivalent = createChequeSettings(
        _maxNumActiveCheques=2,
        _maxChequeUsdValue=300 * EIGHTEEN_DECIMALS,
        _instantUsdThreshold=25 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_DAY_IN_BLOCKS,
        _expensiveDelayBlocks=2 * ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=time_lock,
        _canManagersCreateCheques=False,
        _canManagerPay=False,
        _canBePulled=False,
    )
    cheque_book.setChequeSettings(user_wallet.address, *equivalent, sender=bob)

    live = user_wallet_config.chequeSettings()
    assert live.defaultExpiryBlocks == time_lock
    assert not cheque_book.hasPendingChequeSettings(user_wallet.address)


def test_setChequeSettings_mixed_update_becomes_pending(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    """Mixed tighten+widen updates should still be staged as pending"""
    set_live_cheque_settings(
        cheque_book,
        user_wallet.address,
        *createChequeSettings(
            _maxNumActiveCheques=2,
            _maxChequeUsdValue=300 * EIGHTEEN_DECIMALS,
            _instantUsdThreshold=25 * EIGHTEEN_DECIMALS,
            _periodLength=ONE_DAY_IN_BLOCKS,
            _expensiveDelayBlocks=2 * ONE_DAY_IN_BLOCKS,
            _defaultExpiryBlocks=ONE_DAY_IN_BLOCKS,
            _canManagersCreateCheques=False,
            _canManagerPay=False,
            _canBePulled=False,
        ),
        sender=bob,
    )

    mixed_settings = createChequeSettings(
        _maxNumActiveCheques=0,
        _maxChequeUsdValue=200 * EIGHTEEN_DECIMALS,
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_DAY_IN_BLOCKS,
        _expensiveDelayBlocks=2 * ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=ONE_DAY_IN_BLOCKS,
        _canManagersCreateCheques=False,
        _canManagerPay=False,
        _canBePulled=False,
    )
    current = user_wallet_config.chequeSettings()

    cheque_book.setChequeSettings(user_wallet.address, *mixed_settings, sender=bob)
    pending_event = filter_logs(cheque_book, "ChequeSettingsPending")[-1]

    live = user_wallet_config.chequeSettings()
    assert live.maxNumActiveCheques == current.maxNumActiveCheques
    assert live.maxChequeUsdValue == current.maxChequeUsdValue
    assert pending_event.maxNumActiveCheques == 0
    assert pending_event.maxChequeUsdValue == 200 * EIGHTEEN_DECIMALS

    cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=bob)


def test_setChequeSettings_periodLength_change_always_becomes_pending(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    """Changing periodLength should stage pending settings even if the other fields tighten"""
    baseline = restrictive_cheque_settings(createChequeSettings)
    set_live_cheque_settings(cheque_book, user_wallet.address, *baseline, sender=bob)

    changed_period = restrictive_cheque_settings(
        createChequeSettings,
        _maxNumActiveCheques=1,
        _maxChequeUsdValue=150 * EIGHTEEN_DECIMALS,
        _instantUsdThreshold=10 * EIGHTEEN_DECIMALS,
        _periodLength=2 * ONE_DAY_IN_BLOCKS,
    )
    cheque_book.setChequeSettings(user_wallet.address, *changed_period, sender=bob)

    live = user_wallet_config.chequeSettings()
    assert live.maxNumActiveCheques == 2
    assert live.periodLength == ONE_DAY_IN_BLOCKS
    assert cheque_book.hasPendingChequeSettings(user_wallet.address)

    cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=bob)


def test_confirmPendingChequeSettings_before_timelock_reverts(
    bob, user_wallet, cheque_book, createChequeSettings
):
    """Pending cheque settings cannot be confirmed before their timelock"""
    set_live_cheque_settings(
        cheque_book,
        user_wallet.address,
        *createChequeSettings(
            _maxNumActiveCheques=2,
            _maxChequeUsdValue=300 * EIGHTEEN_DECIMALS,
            _instantUsdThreshold=25 * EIGHTEEN_DECIMALS,
            _periodLength=ONE_DAY_IN_BLOCKS,
            _expensiveDelayBlocks=2 * ONE_DAY_IN_BLOCKS,
            _defaultExpiryBlocks=ONE_DAY_IN_BLOCKS,
            _canManagersCreateCheques=False,
            _canManagerPay=False,
            _canBePulled=False,
        ),
        sender=bob,
    )
    staged = createChequeSettings(
        _maxNumActiveCheques=0,
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_DAY_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=2 * ONE_DAY_IN_BLOCKS,
    )
    cheque_book.setChequeSettings(user_wallet.address, *staged, sender=bob)

    with boa.reverts("time delay not reached"):
        cheque_book.confirmPendingChequeSettings(user_wallet.address, sender=bob)

    cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=bob)


def test_confirmPendingChequeSettings_at_exact_confirm_block_succeeds(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    """Confirmation should succeed exactly at confirmBlock"""
    baseline = restrictive_cheque_settings(createChequeSettings)
    set_live_cheque_settings(cheque_book, user_wallet.address, *baseline, sender=bob)

    staged = restrictive_cheque_settings(
        createChequeSettings,
        _maxNumActiveCheques=0,
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=2 * ONE_DAY_IN_BLOCKS,
    )
    cheque_book.setChequeSettings(user_wallet.address, *staged, sender=bob)

    pending = cheque_book.pendingChequeSettingsMeta(user_wallet.address)
    blocks_to_wait = pending[1] - boa.env.evm.patch.block_number
    boa.env.time_travel(blocks=blocks_to_wait - 1)
    with boa.reverts("time delay not reached"):
        cheque_book.confirmPendingChequeSettings(user_wallet.address, sender=bob)

    boa.env.time_travel(blocks=1)
    cheque_book.confirmPendingChequeSettings(user_wallet.address, sender=bob)

    live = user_wallet_config.chequeSettings()
    assert live.maxNumActiveCheques == 0
    assert not cheque_book.hasPendingChequeSettings(user_wallet.address)


def test_confirmPendingChequeSettings_non_owner_reverts(
    bob, alice, mission_control, switchboard_alpha, user_wallet, cheque_book, createChequeSettings
):
    """Only the wallet owner can confirm pending cheque settings"""
    set_live_cheque_settings(
        cheque_book,
        user_wallet.address,
        *createChequeSettings(
            _maxNumActiveCheques=2,
            _maxChequeUsdValue=300 * EIGHTEEN_DECIMALS,
            _instantUsdThreshold=25 * EIGHTEEN_DECIMALS,
            _periodLength=ONE_DAY_IN_BLOCKS,
            _expensiveDelayBlocks=2 * ONE_DAY_IN_BLOCKS,
            _defaultExpiryBlocks=ONE_DAY_IN_BLOCKS,
            _canManagersCreateCheques=False,
            _canManagerPay=False,
            _canBePulled=False,
        ),
        sender=bob,
    )
    staged = createChequeSettings(
        _maxNumActiveCheques=0,
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_DAY_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=2 * ONE_DAY_IN_BLOCKS,
    )
    cheque_book.setChequeSettings(user_wallet.address, *staged, sender=bob)

    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)
    pending = cheque_book.pendingChequeSettingsMeta(user_wallet.address)
    boa.env.time_travel(blocks=pending[1] - boa.env.evm.patch.block_number)

    with boa.reverts("no perms"):
        cheque_book.confirmPendingChequeSettings(user_wallet.address, sender=alice)

    cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=bob)


def test_confirmPendingChequeSettings_after_timelock_updates_live(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    """Confirming a matured pending widening should update live state"""
    set_live_cheque_settings(
        cheque_book,
        user_wallet.address,
        *createChequeSettings(
            _maxNumActiveCheques=2,
            _maxChequeUsdValue=300 * EIGHTEEN_DECIMALS,
            _instantUsdThreshold=25 * EIGHTEEN_DECIMALS,
            _periodLength=ONE_DAY_IN_BLOCKS,
            _expensiveDelayBlocks=2 * ONE_DAY_IN_BLOCKS,
            _defaultExpiryBlocks=ONE_DAY_IN_BLOCKS,
            _canManagersCreateCheques=False,
            _canManagerPay=False,
            _canBePulled=False,
        ),
        sender=bob,
    )
    staged = createChequeSettings(
        _maxNumActiveCheques=0,
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_DAY_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=2 * ONE_DAY_IN_BLOCKS,
    )
    cheque_book.setChequeSettings(user_wallet.address, *staged, sender=bob)

    pending = cheque_book.pendingChequeSettingsMeta(user_wallet.address)
    boa.env.time_travel(blocks=pending[1] - boa.env.evm.patch.block_number)
    cheque_book.confirmPendingChequeSettings(user_wallet.address, sender=bob)
    logs = cheque_book.get_logs()
    modified_event = [e for e in logs if type(e).__name__ == "ChequeSettingsModified"][-1]
    confirmed_event = [e for e in logs if type(e).__name__ == "ChequeSettingsPendingConfirmed"][-1]

    live = user_wallet_config.chequeSettings()
    pending_after = cheque_book.pendingChequeSettingsMeta(user_wallet.address)
    assert live.maxNumActiveCheques == 0
    assert pending_after[1] == 0
    assert not cheque_book.hasPendingChequeSettings(user_wallet.address)
    assert modified_event.user == user_wallet.address
    assert modified_event.maxNumActiveCheques == 0
    assert confirmed_event.user == user_wallet.address
    assert confirmed_event.initiatedBlock == pending[0]
    assert confirmed_event.confirmBlock == pending[1]


def test_cancelPendingChequeSettings_clears_pending(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    """Cancelling pending cheque settings should leave live config unchanged"""
    set_live_cheque_settings(
        cheque_book,
        user_wallet.address,
        *createChequeSettings(
            _maxNumActiveCheques=2,
            _maxChequeUsdValue=300 * EIGHTEEN_DECIMALS,
            _instantUsdThreshold=25 * EIGHTEEN_DECIMALS,
            _periodLength=ONE_DAY_IN_BLOCKS,
            _expensiveDelayBlocks=2 * ONE_DAY_IN_BLOCKS,
            _defaultExpiryBlocks=ONE_DAY_IN_BLOCKS,
            _canManagersCreateCheques=False,
            _canManagerPay=False,
            _canBePulled=False,
        ),
        sender=bob,
    )
    current = user_wallet_config.chequeSettings()
    staged = createChequeSettings(
        _maxNumActiveCheques=0,
        _instantUsdThreshold=current.instantUsdThreshold,
        _periodLength=current.periodLength,
        _expensiveDelayBlocks=current.expensiveDelayBlocks,
        _defaultExpiryBlocks=current.defaultExpiryBlocks,
        _canManagersCreateCheques=current.canManagersCreateCheques,
        _canManagerPay=current.canManagerPay,
        _canBePulled=current.canBePulled,
    )
    cheque_book.setChequeSettings(user_wallet.address, *staged, sender=bob)

    cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=bob)

    live = user_wallet_config.chequeSettings()
    pending = cheque_book.pendingChequeSettingsMeta(user_wallet.address)
    assert live.maxNumActiveCheques == current.maxNumActiveCheques
    assert pending[1] == 0
    assert not cheque_book.hasPendingChequeSettings(user_wallet.address)


def test_cancelPendingChequeSettings_after_timelock_elapsed_still_cancels(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    """Owners can still cancel a pending widening after confirmBlock has passed"""
    baseline = restrictive_cheque_settings(createChequeSettings)
    set_live_cheque_settings(cheque_book, user_wallet.address, *baseline, sender=bob)

    staged = restrictive_cheque_settings(
        createChequeSettings,
        _maxNumActiveCheques=0,
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=2 * ONE_DAY_IN_BLOCKS,
    )
    cheque_book.setChequeSettings(user_wallet.address, *staged, sender=bob)

    pending = cheque_book.pendingChequeSettingsMeta(user_wallet.address)
    boa.env.time_travel(blocks=pending[1] - boa.env.evm.patch.block_number)
    cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=bob)

    live = user_wallet_config.chequeSettings()
    assert live.maxNumActiveCheques == 2
    assert not cheque_book.hasPendingChequeSettings(user_wallet.address)


def test_cancelPendingChequeSettings_security_action_can_cancel(
    bob, charlie, mission_control, switchboard_alpha, user_wallet, cheque_book, createChequeSettings
):
    """Security action callers can cancel staged pending cheque settings"""
    set_live_cheque_settings(
        cheque_book,
        user_wallet.address,
        *createChequeSettings(
            _maxNumActiveCheques=2,
            _maxChequeUsdValue=300 * EIGHTEEN_DECIMALS,
            _instantUsdThreshold=25 * EIGHTEEN_DECIMALS,
            _periodLength=ONE_DAY_IN_BLOCKS,
            _expensiveDelayBlocks=2 * ONE_DAY_IN_BLOCKS,
            _defaultExpiryBlocks=ONE_DAY_IN_BLOCKS,
            _canManagersCreateCheques=False,
            _canManagerPay=False,
            _canBePulled=False,
        ),
        sender=bob,
    )
    staged = createChequeSettings(
        _maxNumActiveCheques=0,
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_DAY_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=2 * ONE_DAY_IN_BLOCKS,
    )
    cheque_book.setChequeSettings(user_wallet.address, *staged, sender=bob)

    mission_control.setCanPerformSecurityAction(charlie, True, sender=switchboard_alpha.address)
    cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=charlie)

    assert not cheque_book.hasPendingChequeSettings(user_wallet.address)


def test_cancelPendingChequeSettings_non_owner_non_security_reverts(
    bob, alice, user_wallet, cheque_book, createChequeSettings
):
    """Random non-owner callers without security permission cannot cancel pending cheque settings"""
    baseline = restrictive_cheque_settings(createChequeSettings)
    set_live_cheque_settings(cheque_book, user_wallet.address, *baseline, sender=bob)

    widening = restrictive_cheque_settings(
        createChequeSettings,
        _maxNumActiveCheques=0,
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=2 * ONE_DAY_IN_BLOCKS,
    )
    cheque_book.setChequeSettings(user_wallet.address, *widening, sender=bob)

    with boa.reverts("no perms"):
        cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=alice)

    cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=bob)


def test_confirmPendingChequeSettings_owner_change_invalidates_confirm(
    bob, alice, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    """Pending cheque settings should be invalidated if the wallet owner changes"""
    set_live_cheque_settings(
        cheque_book,
        user_wallet.address,
        *createChequeSettings(
            _maxNumActiveCheques=2,
            _maxChequeUsdValue=300 * EIGHTEEN_DECIMALS,
            _instantUsdThreshold=25 * EIGHTEEN_DECIMALS,
            _periodLength=ONE_DAY_IN_BLOCKS,
            _expensiveDelayBlocks=2 * ONE_DAY_IN_BLOCKS,
            _defaultExpiryBlocks=ONE_DAY_IN_BLOCKS,
            _canManagersCreateCheques=False,
            _canManagerPay=False,
            _canBePulled=False,
        ),
        sender=bob,
    )
    staged = createChequeSettings(
        _maxNumActiveCheques=0,
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_DAY_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=2 * ONE_DAY_IN_BLOCKS,
    )
    cheque_book.setChequeSettings(user_wallet.address, *staged, sender=bob)

    pending = cheque_book.pendingChequeSettingsMeta(user_wallet.address)
    user_wallet_config.changeOwnership(alice, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.ownershipTimeLock())
    user_wallet_config.confirmOwnershipChange(sender=alice)
    boa.env.time_travel(blocks=pending[1] - boa.env.evm.patch.block_number)

    with boa.reverts("owner must match"):
        cheque_book.confirmPendingChequeSettings(user_wallet.address, sender=alice)

    cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=alice)


def test_confirmPendingChequeSettings_reverts_if_time_lock_increase_makes_settings_invalid(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    """Increasing the wallet time lock can make staged cheque settings unconfirmable"""
    current_time_lock = user_wallet_config.timeLock()
    staged_delay = max(current_time_lock, cheque_book.MIN_EXPENSIVE_CHEQUE_DELAY())
    assert staged_delay < user_wallet_config.MAX_TIMELOCK()
    baseline = restrictive_cheque_settings(
        createChequeSettings,
        _expensiveDelayBlocks=staged_delay,
        _defaultExpiryBlocks=staged_delay,
    )
    set_live_cheque_settings(cheque_book, user_wallet.address, *baseline, sender=bob)

    widening = restrictive_cheque_settings(
        createChequeSettings,
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _expensiveDelayBlocks=staged_delay,
        _defaultExpiryBlocks=staged_delay,
    )
    cheque_book.setChequeSettings(user_wallet.address, *widening, sender=bob)

    user_wallet_config.setTimeLock(user_wallet_config.MAX_TIMELOCK(), sender=bob)
    pending = cheque_book.pendingChequeSettingsMeta(user_wallet.address)
    boa.env.time_travel(blocks=pending[1] - boa.env.evm.patch.block_number)

    with boa.reverts("invalid cheque settings"):
        cheque_book.confirmPendingChequeSettings(user_wallet.address, sender=bob)

    cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=bob)


def test_setChequeSettings_tightening_while_pending_clears_pending(
    bob, alpha_token, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    """A tightening update should apply live immediately and clear any staged widening"""
    set_live_cheque_settings(
        cheque_book,
        user_wallet.address,
        *createChequeSettings(
            _maxNumActiveCheques=2,
            _maxChequeUsdValue=300 * EIGHTEEN_DECIMALS,
            _instantUsdThreshold=25 * EIGHTEEN_DECIMALS,
            _periodLength=ONE_DAY_IN_BLOCKS,
            _expensiveDelayBlocks=2 * ONE_DAY_IN_BLOCKS,
            _defaultExpiryBlocks=ONE_DAY_IN_BLOCKS,
            _canManagersCreateCheques=False,
            _canManagerPay=False,
            _canBePulled=False,
        ),
        sender=bob,
    )
    widening = createChequeSettings(
        _maxNumActiveCheques=0,
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_DAY_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=2 * ONE_DAY_IN_BLOCKS,
    )
    cheque_book.setChequeSettings(user_wallet.address, *widening, sender=bob)

    tightening = createChequeSettings(
        _maxNumActiveCheques=1,
        _maxChequeUsdValue=150 * EIGHTEEN_DECIMALS,
        _instantUsdThreshold=10 * EIGHTEEN_DECIMALS,
        _perPeriodPaidUsdCap=250 * EIGHTEEN_DECIMALS,
        _maxNumChequesPaidPerPeriod=2,
        _payCooldownBlocks=ONE_HOUR_IN_BLOCKS,
        _perPeriodCreatedUsdCap=250 * EIGHTEEN_DECIMALS,
        _maxNumChequesCreatedPerPeriod=2,
        _createCooldownBlocks=ONE_HOUR_IN_BLOCKS,
        _periodLength=ONE_DAY_IN_BLOCKS,
        _expensiveDelayBlocks=2 * ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=ONE_DAY_IN_BLOCKS,
        _allowedAssets=[alpha_token.address],
        _canManagersCreateCheques=False,
        _canManagerPay=False,
        _canBePulled=False,
    )
    cheque_book.setChequeSettings(user_wallet.address, *tightening, sender=bob)
    logs = cheque_book.get_logs()
    cancel_event = [e for e in logs if type(e).__name__ == "ChequeSettingsPendingCancelled"][-1]

    live = user_wallet_config.chequeSettings()
    pending_after = cheque_book.pendingChequeSettingsMeta(user_wallet.address)
    assert live.maxNumActiveCheques == 1
    assert live.maxChequeUsdValue == 150 * EIGHTEEN_DECIMALS
    assert live.canBePulled == False
    assert pending_after[1] == 0
    assert cancel_event.user == user_wallet.address
    assert cancel_event.cancelledBy == bob


def test_setChequeSettings_bool_widening_becomes_pending(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    """Changing canManagerPay from false to true should stage pending settings"""
    baseline = restrictive_cheque_settings(createChequeSettings, _canManagerPay=False)
    set_live_cheque_settings(cheque_book, user_wallet.address, *baseline, sender=bob)

    widening = restrictive_cheque_settings(createChequeSettings, _canManagerPay=True)
    cheque_book.setChequeSettings(user_wallet.address, *widening, sender=bob)

    live = user_wallet_config.chequeSettings()
    assert live.canManagerPay == False
    assert cheque_book.hasPendingChequeSettings(user_wallet.address)

    cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=bob)


def test_setChequeSettings_cooldown_widening_to_zero_becomes_pending(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    """Removing a non-zero cooldown should count as widening"""
    baseline = restrictive_cheque_settings(createChequeSettings, _payCooldownBlocks=ONE_HOUR_IN_BLOCKS)
    set_live_cheque_settings(cheque_book, user_wallet.address, *baseline, sender=bob)

    widening = restrictive_cheque_settings(createChequeSettings, _payCooldownBlocks=0)
    cheque_book.setChequeSettings(user_wallet.address, *widening, sender=bob)

    live = user_wallet_config.chequeSettings()
    assert live.payCooldownBlocks == ONE_HOUR_IN_BLOCKS
    assert cheque_book.hasPendingChequeSettings(user_wallet.address)

    cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=bob)


def test_setChequeSettings_maxChequeUsdValue_single_field_widening_stages_pending(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    assert_single_field_widening_stages_pending(
        bob,
        user_wallet,
        user_wallet_config,
        cheque_book,
        createChequeSettings,
        target_field="maxChequeUsdValue",
        baseline_overrides={},
        widening_overrides={"_maxChequeUsdValue": 400 * EIGHTEEN_DECIMALS},
        expected_live_value=300 * EIGHTEEN_DECIMALS,
        expected_pending_value=400 * EIGHTEEN_DECIMALS,
    )


def test_setChequeSettings_perPeriodPaidUsdCap_single_field_widening_stages_pending(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    assert_single_field_widening_stages_pending(
        bob,
        user_wallet,
        user_wallet_config,
        cheque_book,
        createChequeSettings,
        target_field="perPeriodPaidUsdCap",
        baseline_overrides={"_perPeriodPaidUsdCap": 400 * EIGHTEEN_DECIMALS},
        widening_overrides={"_perPeriodPaidUsdCap": 600 * EIGHTEEN_DECIMALS},
        expected_live_value=400 * EIGHTEEN_DECIMALS,
        expected_pending_value=600 * EIGHTEEN_DECIMALS,
    )


def test_setChequeSettings_maxNumChequesPaidPerPeriod_single_field_widening_stages_pending(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    assert_single_field_widening_stages_pending(
        bob,
        user_wallet,
        user_wallet_config,
        cheque_book,
        createChequeSettings,
        target_field="maxNumChequesPaidPerPeriod",
        baseline_overrides={"_maxNumChequesPaidPerPeriod": 2},
        widening_overrides={"_maxNumChequesPaidPerPeriod": 3},
        expected_live_value=2,
        expected_pending_value=3,
    )


def test_setChequeSettings_perPeriodCreatedUsdCap_single_field_widening_stages_pending(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    assert_single_field_widening_stages_pending(
        bob,
        user_wallet,
        user_wallet_config,
        cheque_book,
        createChequeSettings,
        target_field="perPeriodCreatedUsdCap",
        baseline_overrides={"_perPeriodCreatedUsdCap": 400 * EIGHTEEN_DECIMALS},
        widening_overrides={"_perPeriodCreatedUsdCap": 600 * EIGHTEEN_DECIMALS},
        expected_live_value=400 * EIGHTEEN_DECIMALS,
        expected_pending_value=600 * EIGHTEEN_DECIMALS,
    )


def test_setChequeSettings_maxNumChequesCreatedPerPeriod_single_field_widening_stages_pending(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    assert_single_field_widening_stages_pending(
        bob,
        user_wallet,
        user_wallet_config,
        cheque_book,
        createChequeSettings,
        target_field="maxNumChequesCreatedPerPeriod",
        baseline_overrides={"_maxNumChequesCreatedPerPeriod": 2},
        widening_overrides={"_maxNumChequesCreatedPerPeriod": 3},
        expected_live_value=2,
        expected_pending_value=3,
    )


def test_setChequeSettings_createCooldownBlocks_single_field_widening_stages_pending(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    assert_single_field_widening_stages_pending(
        bob,
        user_wallet,
        user_wallet_config,
        cheque_book,
        createChequeSettings,
        target_field="createCooldownBlocks",
        baseline_overrides={"_createCooldownBlocks": 2 * ONE_HOUR_IN_BLOCKS},
        widening_overrides={"_createCooldownBlocks": ONE_HOUR_IN_BLOCKS},
        expected_live_value=2 * ONE_HOUR_IN_BLOCKS,
        expected_pending_value=ONE_HOUR_IN_BLOCKS,
    )


def test_setChequeSettings_canManagersCreateCheques_single_field_widening_stages_pending(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    assert_single_field_widening_stages_pending(
        bob,
        user_wallet,
        user_wallet_config,
        cheque_book,
        createChequeSettings,
        target_field="canManagersCreateCheques",
        baseline_overrides={"_canManagersCreateCheques": False},
        widening_overrides={"_canManagersCreateCheques": True},
        expected_live_value=False,
        expected_pending_value=True,
    )


def test_setChequeSettings_canBePulled_single_field_widening_stages_pending(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    assert_single_field_widening_stages_pending(
        bob,
        user_wallet,
        user_wallet_config,
        cheque_book,
        createChequeSettings,
        target_field="canBePulled",
        baseline_overrides={"_canBePulled": False},
        widening_overrides={"_canBePulled": True},
        expected_live_value=False,
        expected_pending_value=True,
    )


def test_setChequeSettings_expensiveDelayBlocks_single_field_widening_stages_pending(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    assert_single_field_widening_stages_pending(
        bob,
        user_wallet,
        user_wallet_config,
        cheque_book,
        createChequeSettings,
        target_field="expensiveDelayBlocks",
        baseline_overrides={
            "_expensiveDelayBlocks": 3 * ONE_DAY_IN_BLOCKS,
            "_defaultExpiryBlocks": 2 * ONE_DAY_IN_BLOCKS,
        },
        widening_overrides={"_expensiveDelayBlocks": 2 * ONE_DAY_IN_BLOCKS},
        expected_live_value=3 * ONE_DAY_IN_BLOCKS,
        expected_pending_value=2 * ONE_DAY_IN_BLOCKS,
    )


def test_setChequeSettings_defaultExpiryBlocks_single_field_widening_stages_pending(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    assert_single_field_widening_stages_pending(
        bob,
        user_wallet,
        user_wallet_config,
        cheque_book,
        createChequeSettings,
        target_field="defaultExpiryBlocks",
        baseline_overrides={
            "_expensiveDelayBlocks": 2 * ONE_DAY_IN_BLOCKS,
            "_defaultExpiryBlocks": 2 * ONE_DAY_IN_BLOCKS,
        },
        widening_overrides={"_defaultExpiryBlocks": 3 * ONE_DAY_IN_BLOCKS},
        expected_live_value=2 * ONE_DAY_IN_BLOCKS,
        expected_pending_value=3 * ONE_DAY_IN_BLOCKS,
    )


def test_setChequeSettings_cap_tightening_applies_immediately_no_pending_event(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    assert_immediate_update_without_pending(
        bob,
        user_wallet,
        user_wallet_config,
        cheque_book,
        createChequeSettings,
        target_field="maxChequeUsdValue",
        baseline_overrides={},
        update_overrides={"_maxChequeUsdValue": 200 * EIGHTEEN_DECIMALS},
        expected_value=200 * EIGHTEEN_DECIMALS,
    )


def test_setChequeSettings_cooldown_tightening_applies_immediately_no_pending_event(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    assert_immediate_update_without_pending(
        bob,
        user_wallet,
        user_wallet_config,
        cheque_book,
        createChequeSettings,
        target_field="payCooldownBlocks",
        baseline_overrides={"_payCooldownBlocks": ONE_HOUR_IN_BLOCKS},
        update_overrides={"_payCooldownBlocks": 2 * ONE_HOUR_IN_BLOCKS},
        expected_value=2 * ONE_HOUR_IN_BLOCKS,
    )


def test_setChequeSettings_fallback_cooldown_tightening_applies_immediately_no_pending_event(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    assert_immediate_update_without_pending(
        bob,
        user_wallet,
        user_wallet_config,
        cheque_book,
        createChequeSettings,
        target_field="expensiveDelayBlocks",
        baseline_overrides={
            "_expensiveDelayBlocks": ONE_DAY_IN_BLOCKS,
            "_defaultExpiryBlocks": 2 * ONE_DAY_IN_BLOCKS,
        },
        update_overrides={"_expensiveDelayBlocks": 2 * ONE_DAY_IN_BLOCKS},
        expected_value=2 * ONE_DAY_IN_BLOCKS,
    )


def test_setChequeSettings_fallback_expiry_tightening_applies_immediately_no_pending_event(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    assert_immediate_update_without_pending(
        bob,
        user_wallet,
        user_wallet_config,
        cheque_book,
        createChequeSettings,
        target_field="defaultExpiryBlocks",
        baseline_overrides={
            "_expensiveDelayBlocks": 2 * ONE_DAY_IN_BLOCKS,
            "_defaultExpiryBlocks": 2 * ONE_DAY_IN_BLOCKS,
        },
        update_overrides={"_defaultExpiryBlocks": ONE_DAY_IN_BLOCKS},
        expected_value=ONE_DAY_IN_BLOCKS,
    )


def test_setChequeSettings_widening_emits_pending_event_payload(
    bob, alpha_token, bravo_token, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    baseline = restrictive_cheque_settings(
        createChequeSettings,
        _allowedAssets=[alpha_token.address],
    )
    set_live_cheque_settings(cheque_book, user_wallet.address, *baseline, sender=bob)

    staged = createChequeSettings(
        _maxNumActiveCheques=0,
        _maxChequeUsdValue=0,
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _perPeriodPaidUsdCap=0,
        _maxNumChequesPaidPerPeriod=0,
        _payCooldownBlocks=0,
        _perPeriodCreatedUsdCap=0,
        _maxNumChequesCreatedPerPeriod=0,
        _createCooldownBlocks=0,
        _periodLength=ONE_DAY_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=2 * ONE_DAY_IN_BLOCKS,
        _allowedAssets=[alpha_token.address, bravo_token.address],
        _canManagersCreateCheques=True,
        _canManagerPay=True,
        _canBePulled=True,
    )
    cheque_book.get_logs()
    cheque_book.setChequeSettings(user_wallet.address, *staged, sender=bob)
    logs = cheque_book.get_logs()
    pending_events = [e for e in logs if type(e).__name__ == "ChequeSettingsPending"]
    modified_events = [e for e in logs if type(e).__name__ == "ChequeSettingsModified"]
    pending = cheque_book.pendingChequeSettings(user_wallet.address)

    assert len(pending_events) == 1
    assert len(modified_events) == 0
    event = pending_events[0]
    assert event.user == user_wallet.address
    assert event.initiatedBy == bob
    assert event.confirmBlock == pending.confirmBlock
    assert event.confirmBlock == pending.initiatedBlock + user_wallet_config.timeLock()
    assert event.maxNumActiveCheques == 0
    assert event.maxChequeUsdValue == 0
    assert event.instantUsdThreshold == 100 * EIGHTEEN_DECIMALS
    assert event.perPeriodPaidUsdCap == 0
    assert event.maxNumChequesPaidPerPeriod == 0
    assert event.payCooldownBlocks == 0
    assert event.perPeriodCreatedUsdCap == 0
    assert event.maxNumChequesCreatedPerPeriod == 0
    assert event.createCooldownBlocks == 0
    assert event.periodLength == ONE_DAY_IN_BLOCKS
    assert event.expensiveDelayBlocks == ONE_DAY_IN_BLOCKS
    assert event.defaultExpiryBlocks == 2 * ONE_DAY_IN_BLOCKS
    assert event.canManagersCreateCheques == True
    assert event.canManagerPay == True
    assert event.canBePulled == True
    # The event stays lightweight; full pending storage includes allowedAssets.
    assert list(pending.settings.allowedAssets) == [alpha_token.address, bravo_token.address]

    cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=bob)


def test_setChequeSettings_reverts_when_instantUsdThreshold_zero(
    bob, user_wallet, cheque_book, createChequeSettings
):
    # Keep every other field valid so only _isValidInstantThreshold fails.
    settings = createChequeSettings(
        _maxNumActiveCheques=2,
        _maxChequeUsdValue=300 * EIGHTEEN_DECIMALS,
        _instantUsdThreshold=0,
        _perPeriodPaidUsdCap=400 * EIGHTEEN_DECIMALS,
        _maxNumChequesPaidPerPeriod=2,
        _payCooldownBlocks=ONE_HOUR_IN_BLOCKS,
        _perPeriodCreatedUsdCap=400 * EIGHTEEN_DECIMALS,
        _maxNumChequesCreatedPerPeriod=2,
        _createCooldownBlocks=ONE_HOUR_IN_BLOCKS,
        _periodLength=ONE_DAY_IN_BLOCKS,
        _expensiveDelayBlocks=2 * ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=ONE_DAY_IN_BLOCKS,
        _canManagersCreateCheques=False,
        _canManagerPay=False,
        _canBePulled=False,
    )

    with boa.reverts("invalid cheque settings"):
        cheque_book.setChequeSettings(user_wallet.address, *settings, sender=bob)


def test_cancelPendingChequeSettings_then_restage_uses_fresh_blocks(
    bob, user_wallet, cheque_book, createChequeSettings
):
    baseline = restrictive_cheque_settings(createChequeSettings)
    set_live_cheque_settings(cheque_book, user_wallet.address, *baseline, sender=bob)
    staged = restrictive_cheque_settings(
        createChequeSettings,
        _maxNumActiveCheques=0,
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=2 * ONE_DAY_IN_BLOCKS,
    )

    cheque_book.setChequeSettings(user_wallet.address, *staged, sender=bob)
    first_pending = cheque_book.pendingChequeSettings(user_wallet.address)
    first_initiated_block = first_pending.initiatedBlock
    first_confirm_block = first_pending.confirmBlock
    cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=bob)

    # Boa keeps txs in the same block unless the test explicitly advances time.
    boa.env.time_travel(blocks=1)
    cheque_book.setChequeSettings(user_wallet.address, *staged, sender=bob)
    second_pending = cheque_book.pendingChequeSettings(user_wallet.address)

    assert second_pending.initiatedBlock > first_initiated_block
    assert second_pending.confirmBlock > first_confirm_block
    assert second_pending.initiatedBlock - first_initiated_block == 1
    assert second_pending.confirmBlock - first_confirm_block == 1

    cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=bob)


def test_cancelPendingChequeSettings_new_owner_can_cancel_stale_pending(
    bob, alice, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    baseline = restrictive_cheque_settings(createChequeSettings)
    set_live_cheque_settings(cheque_book, user_wallet.address, *baseline, sender=bob)
    staged = restrictive_cheque_settings(
        createChequeSettings,
        _maxNumActiveCheques=0,
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=2 * ONE_DAY_IN_BLOCKS,
    )
    cheque_book.setChequeSettings(user_wallet.address, *staged, sender=bob)

    user_wallet_config.changeOwnership(alice, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.ownershipTimeLock())
    user_wallet_config.confirmOwnershipChange(sender=alice)
    cheque_book.get_logs()

    cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=alice)
    logs = cheque_book.get_logs()
    cancel_events = [e for e in logs if type(e).__name__ == "ChequeSettingsPendingCancelled"]

    assert cheque_book.hasPendingChequeSettings(user_wallet.address) == False
    assert_pending_cheque_settings_empty(cheque_book, user_wallet.address)
    assert len(cancel_events) == 1
    assert cancel_events[0].user == user_wallet.address
    assert cancel_events[0].cancelledBy == alice


def test_pending_cheque_settings_are_isolated_per_wallet(
    bob, hatchery, user_wallet, cheque_book, createChequeSettings
):
    """Pending cheque settings for one wallet should not affect another wallet"""
    new_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))

    baseline = restrictive_cheque_settings(createChequeSettings)
    set_live_cheque_settings(cheque_book, user_wallet.address, *baseline, sender=bob)
    set_live_cheque_settings(cheque_book, new_wallet.address, *baseline, sender=bob)

    first_widening = restrictive_cheque_settings(
        createChequeSettings,
        _maxNumActiveCheques=0,
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=2 * ONE_DAY_IN_BLOCKS,
    )
    second_widening = restrictive_cheque_settings(
        createChequeSettings,
        _canManagerPay=True,
    )
    cheque_book.setChequeSettings(user_wallet.address, *first_widening, sender=bob)
    cheque_book.setChequeSettings(new_wallet.address, *second_widening, sender=bob)

    pending_first = cheque_book.pendingChequeSettingsMeta(user_wallet.address)
    pending_second = cheque_book.pendingChequeSettingsMeta(new_wallet.address)
    blocks_to_wait = pending_first[1] - boa.env.evm.patch.block_number
    if blocks_to_wait > 0:
        boa.env.time_travel(blocks=blocks_to_wait)

    cheque_book.confirmPendingChequeSettings(user_wallet.address, sender=bob)

    assert not cheque_book.hasPendingChequeSettings(user_wallet.address)
    assert cheque_book.hasPendingChequeSettings(new_wallet.address)
    assert pending_second[1] == cheque_book.pendingChequeSettingsMeta(new_wallet.address)[1]

    cheque_book.cancelPendingChequeSettings(new_wallet.address, sender=bob)


def test_confirmPendingChequeSettings_after_time_lock_decrease_still_succeeds(
    bob, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    """Cheque settings confirmed after a lower live time lock should still use their original confirmBlock"""
    user_wallet_config.setTimeLock(user_wallet_config.MAX_TIMELOCK(), sender=bob)
    current_time_lock = user_wallet_config.timeLock()

    baseline = restrictive_cheque_settings(
        createChequeSettings,
        _expensiveDelayBlocks=current_time_lock,
        _defaultExpiryBlocks=current_time_lock,
    )
    set_live_cheque_settings(cheque_book, user_wallet.address, *baseline, sender=bob)

    widening = restrictive_cheque_settings(
        createChequeSettings,
        _maxNumActiveCheques=0,
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _expensiveDelayBlocks=current_time_lock,
        _defaultExpiryBlocks=current_time_lock,
    )
    cheque_book.setChequeSettings(user_wallet.address, *widening, sender=bob)

    user_wallet_config.setTimeLock(user_wallet_config.MIN_TIMELOCK(), sender=bob)
    time_lock_pending = user_wallet_config.pendingTimeLock()

    boa.env.time_travel(blocks=time_lock_pending.confirmBlock - boa.env.evm.patch.block_number)
    user_wallet_config.confirmPendingTimeLock(sender=bob)
    cheque_book.confirmPendingChequeSettings(user_wallet.address, sender=bob)

    live = UserWalletConfig.at(user_wallet.walletConfig()).chequeSettings()
    assert user_wallet_config.timeLock() == user_wallet_config.MIN_TIMELOCK()
    assert live.maxNumActiveCheques == 0
    assert not cheque_book.hasPendingChequeSettings(user_wallet.address)


def test_pending_higher_instantUsdThreshold_does_not_affect_cheque_creation_before_confirm(
    bob, alpha_token, mock_ripe, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    """Pending wider thresholds must not change cheque creation behavior before confirmation"""
    baseline = createChequeSettings(
        _maxNumActiveCheques=1,
        _maxChequeUsdValue=500 * EIGHTEEN_DECIMALS,
        _instantUsdThreshold=10 * EIGHTEEN_DECIMALS,
        _perPeriodPaidUsdCap=800 * EIGHTEEN_DECIMALS,
        _maxNumChequesPaidPerPeriod=2,
        _payCooldownBlocks=ONE_HOUR_IN_BLOCKS,
        _perPeriodCreatedUsdCap=800 * EIGHTEEN_DECIMALS,
        _maxNumChequesCreatedPerPeriod=2,
        _createCooldownBlocks=ONE_HOUR_IN_BLOCKS,
        _periodLength=ONE_MONTH_IN_BLOCKS,
        _expensiveDelayBlocks=3 * ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=2 * ONE_DAY_IN_BLOCKS,
        _canManagersCreateCheques=False,
        _canManagerPay=False,
        _canBePulled=False,
    )
    set_live_cheque_settings(cheque_book, user_wallet.address, *baseline, sender=bob)

    widened = createChequeSettings(
        _maxNumActiveCheques=1,
        _maxChequeUsdValue=500 * EIGHTEEN_DECIMALS,
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _perPeriodPaidUsdCap=800 * EIGHTEEN_DECIMALS,
        _maxNumChequesPaidPerPeriod=2,
        _payCooldownBlocks=ONE_HOUR_IN_BLOCKS,
        _perPeriodCreatedUsdCap=800 * EIGHTEEN_DECIMALS,
        _maxNumChequesCreatedPerPeriod=2,
        _createCooldownBlocks=ONE_HOUR_IN_BLOCKS,
        _periodLength=ONE_MONTH_IN_BLOCKS,
        _expensiveDelayBlocks=3 * ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=2 * ONE_DAY_IN_BLOCKS,
        _canManagersCreateCheques=False,
        _canManagerPay=False,
        _canBePulled=False,
    )
    cheque_book.setChequeSettings(user_wallet.address, *widened, sender=bob)

    recipient = boa.env.generate_address()
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
    cheque_book.createCheque(
        user_wallet.address,
        recipient,
        alpha_token.address,
        50 * EIGHTEEN_DECIMALS,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        False,
        False,
        sender=bob,
    )

    stored = user_wallet_config.cheques(recipient)
    assert stored.unlockBlock == boa.env.evm.patch.block_number + (3 * ONE_DAY_IN_BLOCKS)

    cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=bob)


def test_confirmed_higher_instantUsdThreshold_updates_new_cheque_unlocks(
    bob, alpha_token, mock_ripe, user_wallet, user_wallet_config, cheque_book, createChequeSettings
):
    """After confirmation, wider thresholds should affect newly-created cheques"""
    baseline = createChequeSettings(
        _maxNumActiveCheques=1,
        _maxChequeUsdValue=500 * EIGHTEEN_DECIMALS,
        _instantUsdThreshold=10 * EIGHTEEN_DECIMALS,
        _perPeriodPaidUsdCap=800 * EIGHTEEN_DECIMALS,
        _maxNumChequesPaidPerPeriod=2,
        _payCooldownBlocks=ONE_HOUR_IN_BLOCKS,
        _perPeriodCreatedUsdCap=800 * EIGHTEEN_DECIMALS,
        _maxNumChequesCreatedPerPeriod=2,
        _createCooldownBlocks=ONE_HOUR_IN_BLOCKS,
        _periodLength=ONE_MONTH_IN_BLOCKS,
        _expensiveDelayBlocks=3 * ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=2 * ONE_DAY_IN_BLOCKS,
        _canManagersCreateCheques=False,
        _canManagerPay=False,
        _canBePulled=False,
    )
    set_live_cheque_settings(cheque_book, user_wallet.address, *baseline, sender=bob)

    widened = createChequeSettings(
        _maxNumActiveCheques=1,
        _maxChequeUsdValue=500 * EIGHTEEN_DECIMALS,
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _perPeriodPaidUsdCap=800 * EIGHTEEN_DECIMALS,
        _maxNumChequesPaidPerPeriod=2,
        _payCooldownBlocks=ONE_HOUR_IN_BLOCKS,
        _perPeriodCreatedUsdCap=800 * EIGHTEEN_DECIMALS,
        _maxNumChequesCreatedPerPeriod=2,
        _createCooldownBlocks=ONE_HOUR_IN_BLOCKS,
        _periodLength=ONE_MONTH_IN_BLOCKS,
        _expensiveDelayBlocks=3 * ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=2 * ONE_DAY_IN_BLOCKS,
        _canManagersCreateCheques=False,
        _canManagerPay=False,
        _canBePulled=False,
    )
    cheque_book.setChequeSettings(user_wallet.address, *widened, sender=bob)

    pending = cheque_book.pendingChequeSettingsMeta(user_wallet.address)
    boa.env.time_travel(blocks=pending[1] - boa.env.evm.patch.block_number)
    cheque_book.confirmPendingChequeSettings(user_wallet.address, sender=bob)

    recipient = boa.env.generate_address()
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
    cheque_book.createCheque(
        user_wallet.address,
        recipient,
        alpha_token.address,
        50 * EIGHTEEN_DECIMALS,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        False,
        False,
        sender=bob,
    )

    stored = user_wallet_config.cheques(recipient)
    assert stored.unlockBlock == boa.env.evm.patch.block_number + ONE_DAY_IN_BLOCKS


def test_createCheque_manager_respects_global_manager_canCreateCheque(
    bob, alice, charlie, alpha_token, mock_ripe,
    user_wallet, user_wallet_config, cheque_book, high_command,
    createGlobalManagerSettings, createManagerSettings, createTransferPerms,
):
    """Test that manager cheque creation respects global manager transfer permissions"""
    global_settings = createGlobalManagerSettings(
        _transferPerms=createTransferPerms(
            _canTransfer=True,
            _canCreateCheque=False,
            _canAddPendingPayee=True,
            _allowedPayees=[],
        ),
    )
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)

    manager_settings = createManagerSettings(
        _transferPerms=createTransferPerms(
            _canTransfer=True,
            _canCreateCheque=True,
            _canAddPendingPayee=True,
            _allowedPayees=[],
        ),
    )
    user_wallet_config.addManager(alice, manager_settings, sender=high_command.address)

    set_live_cheque_settings(cheque_book,
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

    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)

    with boa.reverts("not authorized to create cheques"):
        cheque_book.createCheque(
            user_wallet.address,
            charlie,
            alpha_token.address,
            50 * EIGHTEEN_DECIMALS,
            ONE_DAY_IN_BLOCKS,
            ONE_WEEK_IN_BLOCKS,
            True,
            False,
            sender=alice
        )


def test_createCheque_manager_respects_manager_allowed_assets(
    bob, alice, charlie, alpha_token, bravo_token, mock_ripe,
    user_wallet, user_wallet_config, cheque_book, high_command,
    createManagerSettings, createTransferPerms,
):
    manager_settings = createManagerSettings(
        _transferPerms=createTransferPerms(
            _canTransfer=True,
            _canCreateCheque=True,
            _canAddPendingPayee=True,
            _allowedPayees=[],
        ),
        _allowedAssets=[bravo_token.address],
    )
    user_wallet_config.addManager(alice, manager_settings, sender=high_command.address)

    set_live_cheque_settings(cheque_book,
        user_wallet.address,
        0,
        0,
        100 * EIGHTEEN_DECIMALS,
        0,
        0,
        0,
        0,
        0,
        0,
        ONE_MONTH_IN_BLOCKS,
        ONE_DAY_IN_BLOCKS,
        0,
        [],
        True,
        True,
        False,
        sender=bob
    )

    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)

    with boa.reverts("not authorized to create cheques"):
        cheque_book.createCheque(
            user_wallet.address,
            charlie,
            alpha_token.address,
            50 * EIGHTEEN_DECIMALS,
            ONE_DAY_IN_BLOCKS,
            ONE_WEEK_IN_BLOCKS,
            True,
            False,
            sender=alice
        )


def test_createCheque_manager_respects_global_manager_allowed_assets(
    bob, alice, charlie, alpha_token, bravo_token, mock_ripe,
    user_wallet, user_wallet_config, cheque_book, high_command,
    createGlobalManagerSettings, createManagerSettings, createTransferPerms,
):
    global_settings = createGlobalManagerSettings(
        _transferPerms=createTransferPerms(
            _canTransfer=True,
            _canCreateCheque=True,
            _canAddPendingPayee=True,
            _allowedPayees=[],
        ),
        _allowedAssets=[bravo_token.address],
    )
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)

    manager_settings = createManagerSettings(
        _transferPerms=createTransferPerms(
            _canTransfer=True,
            _canCreateCheque=True,
            _canAddPendingPayee=True,
            _allowedPayees=[],
        ),
    )
    user_wallet_config.addManager(alice, manager_settings, sender=high_command.address)

    set_live_cheque_settings(cheque_book,
        user_wallet.address,
        0,
        0,
        100 * EIGHTEEN_DECIMALS,
        0,
        0,
        0,
        0,
        0,
        0,
        ONE_MONTH_IN_BLOCKS,
        ONE_DAY_IN_BLOCKS,
        0,
        [],
        True,
        True,
        False,
        sender=bob
    )

    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)

    with boa.reverts("not authorized to create cheques"):
        cheque_book.createCheque(
            user_wallet.address,
            charlie,
            alpha_token.address,
            50 * EIGHTEEN_DECIMALS,
            ONE_DAY_IN_BLOCKS,
            ONE_WEEK_IN_BLOCKS,
            True,
            False,
            sender=alice
        )


def test_createCheque_manager_succeeds_when_manager_and_global_assets_allow_asset(
    bob, alice, charlie, alpha_token, bravo_token, mock_ripe,
    user_wallet, user_wallet_config, cheque_book, high_command,
    createGlobalManagerSettings, createManagerSettings, createTransferPerms,
):
    global_settings = createGlobalManagerSettings(
        _transferPerms=createTransferPerms(
            _canTransfer=True,
            _canCreateCheque=True,
            _canAddPendingPayee=True,
            _allowedPayees=[],
        ),
        _allowedAssets=[alpha_token.address, bravo_token.address],
    )
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)

    manager_settings = createManagerSettings(
        _transferPerms=createTransferPerms(
            _canTransfer=True,
            _canCreateCheque=True,
            _canAddPendingPayee=True,
            _allowedPayees=[],
        ),
        _allowedAssets=[alpha_token.address],
    )
    user_wallet_config.addManager(alice, manager_settings, sender=high_command.address)

    set_live_cheque_settings(cheque_book,
        user_wallet.address,
        0,
        0,
        100 * EIGHTEEN_DECIMALS,
        0,
        0,
        0,
        0,
        0,
        0,
        ONE_MONTH_IN_BLOCKS,
        ONE_DAY_IN_BLOCKS,
        0,
        [],
        True,
        True,
        False,
        sender=bob
    )

    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)

    cheque_book.createCheque(
        user_wallet.address,
        charlie,
        alpha_token.address,
        50 * EIGHTEEN_DECIMALS,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,
        False,
        sender=alice
    )

    stored_cheque = user_wallet_config.cheques(charlie)
    assert stored_cheque.active == True
    assert stored_cheque.asset == alpha_token.address


def test_createCheque_owner_ignores_manager_asset_allowlists(
    bob, alice, charlie, alpha_token, bravo_token, mock_ripe,
    user_wallet, user_wallet_config, cheque_book, high_command,
    createGlobalManagerSettings, createManagerSettings, createTransferPerms,
):
    global_settings = createGlobalManagerSettings(
        _transferPerms=createTransferPerms(
            _canTransfer=True,
            _canCreateCheque=True,
            _canAddPendingPayee=True,
            _allowedPayees=[],
        ),
        _allowedAssets=[bravo_token.address],
    )
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)

    manager_settings = createManagerSettings(
        _transferPerms=createTransferPerms(
            _canTransfer=True,
            _canCreateCheque=True,
            _canAddPendingPayee=True,
            _allowedPayees=[],
        ),
        _allowedAssets=[bravo_token.address],
    )
    user_wallet_config.addManager(alice, manager_settings, sender=high_command.address)

    set_live_cheque_settings(cheque_book,
        user_wallet.address,
        0,
        0,
        100 * EIGHTEEN_DECIMALS,
        0,
        0,
        0,
        0,
        0,
        0,
        ONE_MONTH_IN_BLOCKS,
        ONE_DAY_IN_BLOCKS,
        0,
        [],
        True,
        True,
        False,
        sender=bob
    )

    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)

    cheque_book.createCheque(
        user_wallet.address,
        charlie,
        alpha_token.address,
        50 * EIGHTEEN_DECIMALS,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,
        False,
        sender=bob
    )

    stored_cheque = user_wallet_config.cheques(charlie)
    assert stored_cheque.active == True
    assert stored_cheque.asset == alpha_token.address


def test_createCheque_fails_invalid_inputs(
    bob, alice, alpha_token, mock_ripe,
    user_wallet, cheque_book,
):
    """Test that createCheque fails when inputs are invalid"""
    # Setup
    set_live_cheque_settings(cheque_book,
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
    set_live_cheque_settings(cheque_book,
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
    
    set_live_cheque_settings(cheque_book,
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


def test_createCheque_expensive_delay_clamps_to_live_time_lock(
    bob, alice, alpha_token, mock_ripe,
    user_wallet, user_wallet_config, cheque_book, createChequeSettings,
):
    set_timelock_clamp_cheque_settings(
        cheque_book,
        user_wallet,
        createChequeSettings,
        sender=bob,
        instant_threshold=10 * EIGHTEEN_DECIMALS,
        expensive_delay=ONE_DAY_IN_BLOCKS,
        default_expiry=ONE_WEEK_IN_BLOCKS,
    )
    user_wallet_config.setTimeLock(user_wallet_config.MAX_TIMELOCK(), sender=bob)
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)

    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        50 * EIGHTEEN_DECIMALS,
        0,
        ONE_WEEK_IN_BLOCKS,
        True,
        False,
        sender=bob,
    )

    cheque = user_wallet_config.cheques(alice)
    assert cheque.unlockBlock == cheque.creationBlock + user_wallet_config.timeLock()


def test_createCheque_default_expiry_clamps_to_live_time_lock(
    bob, alice, alpha_token, mock_ripe,
    user_wallet, user_wallet_config, cheque_book, createChequeSettings,
):
    set_timelock_clamp_cheque_settings(
        cheque_book,
        user_wallet,
        createChequeSettings,
        sender=bob,
        instant_threshold=100 * EIGHTEEN_DECIMALS,
        expensive_delay=ONE_DAY_IN_BLOCKS,
        default_expiry=ONE_DAY_IN_BLOCKS,
    )
    user_wallet_config.setTimeLock(user_wallet_config.MAX_TIMELOCK(), sender=bob)
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)

    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        50 * EIGHTEEN_DECIMALS,
        0,
        0,
        True,
        False,
        sender=bob,
    )

    cheque = user_wallet_config.cheques(alice)
    assert cheque.expiryBlock == cheque.unlockBlock + user_wallet_config.timeLock()


def test_createCheque_explicit_expiry_remains_unclamped_by_time_lock(
    bob, alice, alpha_token, mock_ripe,
    user_wallet, user_wallet_config, cheque_book, createChequeSettings,
):
    set_timelock_clamp_cheque_settings(
        cheque_book,
        user_wallet,
        createChequeSettings,
        sender=bob,
        instant_threshold=100 * EIGHTEEN_DECIMALS,
        expensive_delay=ONE_DAY_IN_BLOCKS,
        default_expiry=ONE_DAY_IN_BLOCKS,
    )
    user_wallet_config.setTimeLock(user_wallet_config.MAX_TIMELOCK(), sender=bob)
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
    explicit_expiry_blocks = ONE_DAY_IN_BLOCKS

    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        50 * EIGHTEEN_DECIMALS,
        0,
        explicit_expiry_blocks,
        True,
        False,
        sender=bob,
    )

    cheque = user_wallet_config.cheques(alice)
    assert cheque.expiryBlock == cheque.unlockBlock + explicit_expiry_blocks
    assert cheque.expiryBlock < cheque.unlockBlock + user_wallet_config.timeLock()


def test_createCheque_max_time_lock_clamps_and_creates_successfully(
    bob, alice, alpha_token, mock_ripe,
    user_wallet, user_wallet_config, cheque_book, createChequeSettings,
):
    set_timelock_clamp_cheque_settings(
        cheque_book,
        user_wallet,
        createChequeSettings,
        sender=bob,
        instant_threshold=10 * EIGHTEEN_DECIMALS,
        expensive_delay=ONE_DAY_IN_BLOCKS,
        default_expiry=ONE_DAY_IN_BLOCKS,
    )
    user_wallet_config.setTimeLock(user_wallet_config.MAX_TIMELOCK(), sender=bob)
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)

    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        50 * EIGHTEEN_DECIMALS,
        0,
        0,
        True,
        False,
        sender=bob,
    )

    cheque = user_wallet_config.cheques(alice)
    assert cheque.active
    assert cheque.unlockBlock == cheque.creationBlock + user_wallet_config.timeLock()
    assert cheque.expiryBlock == cheque.unlockBlock + user_wallet_config.timeLock()


def test_createCheque_with_cheque_period_data_manipulation(
    bob, alice, charlie, alpha_token, mock_ripe,
    user_wallet, user_wallet_config, cheque_book,
    createChequeData
):
    """Test cheque creation with direct manipulation of chequePeriodData"""
    # Setup
    set_live_cheque_settings(cheque_book,
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
    
    set_live_cheque_settings(cheque_book,
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
    set_live_cheque_settings(cheque_book,
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
    set_live_cheque_settings(cheque_book,
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


def test_createCheque_rejects_owner_as_recipient(
    bob, alpha_token, mock_ripe,
    user_wallet, cheque_book,
):
    """Owner must use a separate wallet if they want to receive cheque funds"""
    set_live_cheque_settings(cheque_book,
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

    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)

    with boa.reverts("invalid cheque"):
        cheque_book.createCheque(
            user_wallet.address,
            bob,
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
    set_live_cheque_settings(cheque_book,
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
    set_live_cheque_settings(cheque_book,
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
    set_live_cheque_settings(cheque_book,
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
    set_live_cheque_settings(cheque_book,
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
    set_live_cheque_settings(cheque_book,
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
    set_live_cheque_settings(cheque_book,
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
    set_live_cheque_settings(cheque_book,
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
    set_live_cheque_settings(cheque_book,
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
    set_live_cheque_settings(cheque_book,
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
    set_live_cheque_settings(cheque_book,
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
