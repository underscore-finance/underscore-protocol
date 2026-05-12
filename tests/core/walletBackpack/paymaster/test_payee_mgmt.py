import pytest
import boa

from constants import EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ZERO_ADDRESS
from conf_utils import filter_logs, fresh_user_wallet, set_user_instant_action_settings
from abi_utils import count_abi_arities


def _set_user_instant_settings(config, owner, settings):
    set_user_instant_action_settings(config, owner, settings)


def _set_protocol_flag(target, switchboard_bravo, getter_name, setter_name, enabled):
    if getattr(target, getter_name)() != enabled:
        getattr(target, setter_name)(enabled, sender=switchboard_bravo.address)


def _add_payee_args(createPayeeLimits):
    return (
        False,
        ONE_DAY_IN_BLOCKS,
        0,
        0,
        False,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        createPayeeLimits(),
    )


def _restrictive_global_payee_settings(config, createPayeeLimits):
    return (
        ONE_DAY_IN_BLOCKS,
        config.timeLock(),
        ONE_DAY_IN_BLOCKS,
        5,
        100,
        True,
        createPayeeLimits(
            _perTxCap=100 * EIGHTEEN_DECIMALS,
            _perPeriodCap=1000 * EIGHTEEN_DECIMALS,
            _lifetimeCap=10000 * EIGHTEEN_DECIMALS,
        ),
        False,
    )


def _widened_global_payee_settings(config, createPayeeLimits):
    # Lower cooldown plus higher limits both widen the current global policy.
    return (
        ONE_DAY_IN_BLOCKS,
        config.timeLock(),
        2 * ONE_DAY_IN_BLOCKS,
        10,
        50,
        False,
        createPayeeLimits(
            _perTxCap=200 * EIGHTEEN_DECIMALS,
            _perPeriodCap=2000 * EIGHTEEN_DECIMALS,
            _lifetimeCap=20000 * EIGHTEEN_DECIMALS,
        ),
        True,
    )


def test_paymaster_abi_selector_counts():
    assert count_abi_arities("scripts/abis/Paymaster.json", "addPayee") == [11, 12, 13, 14]
    assert count_abi_arities("scripts/abis/Paymaster.json", "setGlobalPayeeSettings") == [9, 10]


def test_instant_add_payee_sets_start_block_to_current_and_preserves_activation_length(
    paymaster, switchboard_bravo, hatchery, bob, alice, createPayeeLimits
):
    wallet, config = fresh_user_wallet(hatchery, bob)
    _set_protocol_flag(paymaster, switchboard_bravo, "canInstantAddPayee", "setCanInstantAddPayee", True)
    _set_user_instant_settings(config, bob, (False, True, False, False))
    args = _add_payee_args(createPayeeLimits)

    block_before = boa.env.evm.patch.block_number
    assert paymaster.addPayee(wallet.address, alice, *args, 0, ONE_DAY_IN_BLOCKS, True, sender=bob)

    settings = config.payeeSettings(alice)
    assert settings.startBlock == block_before
    assert settings.expiryBlock - settings.startBlock == ONE_DAY_IN_BLOCKS


def test_delayed_add_payee_still_uses_max_delay(
    paymaster, switchboard_bravo, hatchery, bob, alice, createPayeeLimits
):
    wallet, config = fresh_user_wallet(hatchery, bob)
    _set_protocol_flag(paymaster, switchboard_bravo, "canInstantAddPayee", "setCanInstantAddPayee", True)
    args = _add_payee_args(createPayeeLimits)
    requested_delay = config.timeLock() + 10
    block_before = boa.env.evm.patch.block_number

    assert paymaster.addPayee(wallet.address, alice, *args, requested_delay, ONE_DAY_IN_BLOCKS, False, sender=bob)

    settings = config.payeeSettings(alice)
    assert settings.startBlock == block_before + requested_delay


def test_instant_add_payee_requested_with_nonzero_start_delay_reverts(
    paymaster, switchboard_bravo, hatchery, bob, alice, createPayeeLimits
):
    wallet, config = fresh_user_wallet(hatchery, bob)
    _set_protocol_flag(paymaster, switchboard_bravo, "canInstantAddPayee", "setCanInstantAddPayee", True)
    _set_user_instant_settings(config, bob, (False, True, False, False))
    args = _add_payee_args(createPayeeLimits)

    with boa.reverts("invalid start delay"):
        paymaster.addPayee(wallet.address, alice, *args, 1, ONE_DAY_IN_BLOCKS, True, sender=bob)


@pytest.mark.parametrize(
    "protocol_enabled,user_enabled,request_instant,should_revert,expect_instant",
    [
        (False, False, False, False, False),
        (True, False, True, True, False),
        (False, True, True, True, False),
        (True, True, False, False, False),
        (True, True, True, False, True),
    ],
)
def test_add_payee_instant_gate_matrix(
    paymaster, switchboard_bravo, hatchery, bob, alice, createPayeeLimits,
    protocol_enabled, user_enabled, request_instant, should_revert, expect_instant,
):
    wallet, config = fresh_user_wallet(hatchery, bob)
    _set_protocol_flag(paymaster, switchboard_bravo, "canInstantAddPayee", "setCanInstantAddPayee", protocol_enabled)
    if user_enabled:
        _set_user_instant_settings(config, bob, (False, True, False, False))
    args = _add_payee_args(createPayeeLimits)
    block_before = boa.env.evm.patch.block_number

    if should_revert:
        with boa.reverts("instant disabled"):
            paymaster.addPayee(wallet.address, alice, *args, 0, ONE_DAY_IN_BLOCKS, request_instant, sender=bob)
        return

    assert paymaster.addPayee(wallet.address, alice, *args, 0, ONE_DAY_IN_BLOCKS, request_instant, sender=bob)
    settings = config.payeeSettings(alice)
    if expect_instant:
        assert settings.startBlock == block_before
    else:
        assert settings.startBlock == block_before + config.timeLock()


def test_widening_global_payee_settings_without_instant_creates_pending(
    paymaster, hatchery, bob, createPayeeLimits
):
    wallet, config = fresh_user_wallet(hatchery, bob)
    baseline = _restrictive_global_payee_settings(config, createPayeeLimits)
    assert paymaster.setGlobalPayeeSettings(wallet.address, *baseline, sender=bob)

    widened = _widened_global_payee_settings(config, createPayeeLimits)
    assert paymaster.setGlobalPayeeSettings(wallet.address, *widened, False, sender=bob)

    pending = paymaster.pendingGlobalPayeeSettings(wallet.address)
    assert pending.confirmBlock != 0
    assert pending.settings.canPull is True
    assert config.globalPayeeSettings().canPull is False


def test_widening_global_payee_settings_with_all_gates_applies_immediately(
    paymaster, switchboard_bravo, hatchery, bob, createPayeeLimits
):
    wallet, config = fresh_user_wallet(hatchery, bob)
    baseline = _restrictive_global_payee_settings(config, createPayeeLimits)
    paymaster.setGlobalPayeeSettings(wallet.address, *baseline, sender=bob)
    _set_protocol_flag(
        paymaster,
        switchboard_bravo,
        "canInstantSetGlobalPayeeSettings",
        "setCanInstantSetGlobalPayeeSettings",
        True,
    )
    _set_user_instant_settings(config, bob, (False, False, True, False))
    widened = _widened_global_payee_settings(config, createPayeeLimits)

    assert paymaster.setGlobalPayeeSettings(wallet.address, *widened, True, sender=bob)

    assert paymaster.pendingGlobalPayeeSettings(wallet.address).confirmBlock == 0
    saved = config.globalPayeeSettings()
    assert saved.canPull is True
    assert saved.activationLength == 2 * ONE_DAY_IN_BLOCKS


def test_existing_pending_global_payee_settings_cancelled_when_instant_apply_succeeds(
    paymaster, switchboard_bravo, hatchery, bob, createPayeeLimits
):
    wallet, config = fresh_user_wallet(hatchery, bob)
    baseline = _restrictive_global_payee_settings(config, createPayeeLimits)
    paymaster.setGlobalPayeeSettings(wallet.address, *baseline, sender=bob)
    widened = _widened_global_payee_settings(config, createPayeeLimits)
    paymaster.setGlobalPayeeSettings(wallet.address, *widened, sender=bob)
    pending = paymaster.pendingGlobalPayeeSettings(wallet.address)
    _set_protocol_flag(
        paymaster,
        switchboard_bravo,
        "canInstantSetGlobalPayeeSettings",
        "setCanInstantSetGlobalPayeeSettings",
        True,
    )
    _set_user_instant_settings(config, bob, (False, False, True, False))
    paymaster.get_logs()

    assert paymaster.setGlobalPayeeSettings(wallet.address, *widened, True, sender=bob)

    cancel_event = filter_logs(paymaster, "PendingGlobalPayeeSettingsCancelled")[0]
    assert cancel_event.user == wallet.address
    assert cancel_event.confirmBlock == pending.confirmBlock
    assert paymaster.pendingGlobalPayeeSettings(wallet.address).confirmBlock == 0
    assert config.globalPayeeSettings().canPull is True


def test_should_apply_instantly_on_non_widening_global_payee_settings_ignores_gates(
    paymaster, switchboard_bravo, hatchery, bob, createPayeeLimits
):
    wallet, config = fresh_user_wallet(hatchery, bob)
    _set_protocol_flag(
        paymaster,
        switchboard_bravo,
        "canInstantSetGlobalPayeeSettings",
        "setCanInstantSetGlobalPayeeSettings",
        False,
    )
    baseline = _restrictive_global_payee_settings(config, createPayeeLimits)
    paymaster.setGlobalPayeeSettings(wallet.address, *baseline, sender=bob)
    tighter = list(baseline)
    tighter[4] = 200

    assert paymaster.setGlobalPayeeSettings(wallet.address, *tuple(tighter), True, sender=bob)

    assert paymaster.pendingGlobalPayeeSettings(wallet.address).confirmBlock == 0
    assert config.globalPayeeSettings().txCooldownBlocks == 200


def test_instant_global_payee_settings_requested_but_unavailable_reverts(
    paymaster, switchboard_bravo, hatchery, bob, createPayeeLimits
):
    wallet, config = fresh_user_wallet(hatchery, bob)
    baseline = _restrictive_global_payee_settings(config, createPayeeLimits)
    paymaster.setGlobalPayeeSettings(wallet.address, *baseline, sender=bob)
    _set_protocol_flag(
        paymaster,
        switchboard_bravo,
        "canInstantSetGlobalPayeeSettings",
        "setCanInstantSetGlobalPayeeSettings",
        False,
    )
    _set_user_instant_settings(config, bob, (False, False, True, False))

    with boa.reverts("instant disabled"):
        paymaster.setGlobalPayeeSettings(
            wallet.address,
            *_widened_global_payee_settings(config, createPayeeLimits),
            True,
            sender=bob,
        )


#########################
# Global Payee Settings #
#########################


def test_set_global_payee_settings_updates_pending_and_live_settings(paymaster, user_wallet, user_wallet_config, createPayeeLimits, bob):
    start_delay = user_wallet_config.timeLock()
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS,
    )

    result = paymaster.setGlobalPayeeSettings(
        user_wallet,
        2 * ONE_DAY_IN_BLOCKS,
        start_delay,
        ONE_DAY_IN_BLOCKS,
        10,
        100,
        True,
        usd_limits,
        True,
        sender=bob,
    )

    assert result == True

    pending = paymaster.pendingGlobalPayeeSettings(user_wallet)
    assert pending.settings.defaultPeriodLength == 2 * ONE_DAY_IN_BLOCKS
    assert pending.settings.startDelay == start_delay
    assert pending.settings.activationLength == ONE_DAY_IN_BLOCKS
    assert pending.settings.maxNumTxsPerPeriod == 10
    assert pending.settings.txCooldownBlocks == 100
    assert pending.settings.failOnZeroPrice == True
    assert pending.settings.canPull == True
    assert pending.confirmBlock == boa.env.evm.patch.block_number + user_wallet_config.timeLock()

    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    result = paymaster.confirmPendingGlobalPayeeSettings(user_wallet, sender=bob)

    assert result == True

    saved = user_wallet_config.globalPayeeSettings()
    assert saved.defaultPeriodLength == 2 * ONE_DAY_IN_BLOCKS
    assert saved.startDelay == start_delay
    assert saved.activationLength == ONE_DAY_IN_BLOCKS
    assert saved.maxNumTxsPerPeriod == 10
    assert saved.txCooldownBlocks == 100
    assert saved.failOnZeroPrice == True
    assert saved.canPull == True

    event = filter_logs(paymaster, "GlobalPayeeSettingsModified")[-1]
    assert event.user == user_wallet.address
    assert event.canPull == True


def test_pending_global_payee_settings_cancel_and_events(paymaster, user_wallet, user_wallet_config, createPayeeLimits, bob):
    start_delay = user_wallet_config.timeLock()
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)

    assert paymaster.setGlobalPayeeSettings(
        user_wallet,
        2 * ONE_DAY_IN_BLOCKS,
        start_delay,
        ONE_DAY_IN_BLOCKS,
        10,
        100,
        True,
        usd_limits,
        True,
        sender=bob,
    )
    set_event = filter_logs(paymaster, "PendingGlobalPayeeSettingsSet")[0]
    pending = paymaster.pendingGlobalPayeeSettings(user_wallet)
    assert set_event.user == user_wallet.address
    assert set_event.initiatedBy == bob
    assert set_event.confirmBlock == pending.confirmBlock

    assert paymaster.cancelPendingGlobalPayeeSettings(user_wallet, sender=bob)
    cancel_event = filter_logs(paymaster, "PendingGlobalPayeeSettingsCancelled")[0]
    assert paymaster.pendingGlobalPayeeSettings(user_wallet).confirmBlock == 0
    assert cancel_event.user == user_wallet.address
    assert cancel_event.cancelledBy == bob
    assert cancel_event.currentOwner == bob
    assert cancel_event.initiatedBlock == pending.initiatedBlock
    assert cancel_event.confirmBlock == pending.confirmBlock


def test_tightening_global_payee_settings_applies_immediately_and_cancels_pending(
    paymaster, user_wallet, user_wallet_config, createPayeeLimits, bob
):
    start_delay = user_wallet_config.timeLock()
    widening_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    assert paymaster.setGlobalPayeeSettings(
        user_wallet,
        2 * ONE_DAY_IN_BLOCKS,
        start_delay,
        ONE_DAY_IN_BLOCKS,
        10,
        100,
        True,
        widening_limits,
        True,
        sender=bob,
    )
    pending = paymaster.pendingGlobalPayeeSettings(user_wallet)
    assert pending.confirmBlock != 0

    current = user_wallet_config.globalPayeeSettings()
    tightening_limits = createPayeeLimits()
    assert paymaster.setGlobalPayeeSettings(
        user_wallet,
        current.defaultPeriodLength,
        current.startDelay,
        current.activationLength,
        current.maxNumTxsPerPeriod,
        current.txCooldownBlocks,
        True,
        tightening_limits,
        current.canPull,
        sender=bob,
    )

    cancel_event = filter_logs(paymaster, "PendingGlobalPayeeSettingsCancelled")[0]
    assert paymaster.pendingGlobalPayeeSettings(user_wallet).confirmBlock == 0
    saved = user_wallet_config.globalPayeeSettings()
    assert saved.defaultPeriodLength == current.defaultPeriodLength
    assert saved.canPull == current.canPull
    assert saved.maxNumTxsPerPeriod == current.maxNumTxsPerPeriod
    assert saved.failOnZeroPrice == True
    assert cancel_event.user == user_wallet.address
    assert cancel_event.cancelledBy == bob
    assert cancel_event.currentOwner == bob
    assert cancel_event.confirmBlock == pending.confirmBlock


def test_tightening_global_payee_settings_after_owner_change_preserves_pending_owner_in_cancel_event(
    paymaster, user_wallet, user_wallet_config, createPayeeLimits, bob, alice
):
    start_delay = user_wallet_config.timeLock()
    widening_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    assert paymaster.setGlobalPayeeSettings(
        user_wallet,
        2 * ONE_DAY_IN_BLOCKS,
        start_delay,
        ONE_DAY_IN_BLOCKS,
        10,
        100,
        True,
        widening_limits,
        True,
        sender=bob,
    )
    pending = paymaster.pendingGlobalPayeeSettings(user_wallet)
    assert pending.currentOwner == bob

    user_wallet_config.changeOwnership(alice, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.ownershipTimeLock())
    user_wallet_config.confirmOwnershipChange(sender=alice)

    current = user_wallet_config.globalPayeeSettings()
    assert paymaster.setGlobalPayeeSettings(
        user_wallet,
        current.defaultPeriodLength,
        current.startDelay,
        current.activationLength,
        current.maxNumTxsPerPeriod,
        current.txCooldownBlocks,
        True,
        createPayeeLimits(),
        current.canPull,
        sender=alice,
    )

    cancel_event = filter_logs(paymaster, "PendingGlobalPayeeSettingsCancelled")[0]
    assert paymaster.pendingGlobalPayeeSettings(user_wallet).confirmBlock == 0
    assert cancel_event.cancelledBy == alice
    assert cancel_event.currentOwner == bob
    assert cancel_event.confirmBlock == pending.confirmBlock


@pytest.mark.parametrize(
    "widening_dimension",
    [
        "can_pull",
        "cap_increase",
        "cap_to_zero",
        "max_txs_increase",
        "max_txs_to_zero",
        "cooldown_decrease",
        "cooldown_to_zero",
        "period_decrease",
        "start_delay_decrease",
        "activation_increase",
        "fail_on_zero_price_false",
    ],
)
def test_global_payee_settings_each_widening_dimension_is_pending(
    paymaster,
    user_wallet,
    user_wallet_config,
    createGlobalPayeeSettings,
    createPayeeLimits,
    bob,
    widening_dimension,
):
    baseline_limits = createPayeeLimits(
        _perTxCap=100 * EIGHTEEN_DECIMALS,
        _perPeriodCap=1000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=10000 * EIGHTEEN_DECIMALS,
    )
    if widening_dimension == "fail_on_zero_price_false":
        baseline_limits = createPayeeLimits()
    baseline = createGlobalPayeeSettings(
        _defaultPeriodLength=10 * ONE_DAY_IN_BLOCKS,
        _startDelay=2 * ONE_DAY_IN_BLOCKS,
        _activationLength=10 * ONE_DAY_IN_BLOCKS,
        _maxNumTxsPerPeriod=5,
        _txCooldownBlocks=100,
        _failOnZeroPrice=True,
        _usdLimits=baseline_limits,
        _canPull=False,
    )
    user_wallet_config.setGlobalPayeeSettings(baseline, sender=paymaster.address)

    updated_limits = baseline_limits
    default_period_length = 10 * ONE_DAY_IN_BLOCKS
    start_delay = 2 * ONE_DAY_IN_BLOCKS
    activation_length = 10 * ONE_DAY_IN_BLOCKS
    max_num_txs = 5
    cooldown = 100
    fail_on_zero_price = True
    can_pull = False

    if widening_dimension == "can_pull":
        can_pull = True
    elif widening_dimension == "cap_increase":
        updated_limits = createPayeeLimits(
            _perTxCap=200 * EIGHTEEN_DECIMALS,
            _perPeriodCap=1000 * EIGHTEEN_DECIMALS,
            _lifetimeCap=10000 * EIGHTEEN_DECIMALS,
        )
    elif widening_dimension == "cap_to_zero":
        updated_limits = createPayeeLimits(
            _perTxCap=0,
            _perPeriodCap=1000 * EIGHTEEN_DECIMALS,
            _lifetimeCap=10000 * EIGHTEEN_DECIMALS,
        )
    elif widening_dimension == "max_txs_increase":
        max_num_txs = 6
    elif widening_dimension == "max_txs_to_zero":
        max_num_txs = 0
    elif widening_dimension == "cooldown_decrease":
        cooldown = 99
    elif widening_dimension == "cooldown_to_zero":
        cooldown = 0
    elif widening_dimension == "period_decrease":
        default_period_length = 9 * ONE_DAY_IN_BLOCKS
    elif widening_dimension == "start_delay_decrease":
        start_delay = ONE_DAY_IN_BLOCKS
    elif widening_dimension == "activation_increase":
        activation_length = 11 * ONE_DAY_IN_BLOCKS
    elif widening_dimension == "fail_on_zero_price_false":
        fail_on_zero_price = False

    assert paymaster.setGlobalPayeeSettings(
        user_wallet,
        default_period_length,
        start_delay,
        activation_length,
        max_num_txs,
        cooldown,
        fail_on_zero_price,
        updated_limits,
        can_pull,
        sender=bob,
    )
    set_event = filter_logs(paymaster, "PendingGlobalPayeeSettingsSet")[0]
    pending = paymaster.pendingGlobalPayeeSettings(user_wallet)
    assert pending.confirmBlock != 0
    assert pending.settings.canPull == can_pull
    assert set_event.confirmBlock == pending.confirmBlock


#############
# Add Payee #
#############


def test_add_payee_verifies_real_user_wallet(paymaster, createPayeeLimits, alice, bob):
    """Test that addPayee verifies it's a real user wallet"""
    # Try to add payee to a non-wallet address (bob's EOA)
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    # This should fail because bob is not a user wallet
    with boa.reverts("invalid user wallet"):
        paymaster.addPayee(
            bob,  # Not a real user wallet, just an EOA
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
            sender=bob
        )


def test_add_payee_verifies_caller_is_owner(paymaster, user_wallet, createPayeeLimits, alice, charlie):
    """Test that only the owner can add a payee"""
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    # Try to add payee as non-owner (alice)
    with boa.reverts("no perms"):
        paymaster.addPayee(
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
            sender=alice  # Not the owner
        )


def test_add_payee_rejects_owner_as_payee(paymaster, user_wallet, createPayeeLimits, bob):
    """Owner must use a separate wallet if they want to receive payee payments"""
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )

    with boa.reverts("invalid payee settings"):
        paymaster.addPayee(
            user_wallet,
            bob,
            False,
            2 * ONE_DAY_IN_BLOCKS,
            10,
            0,
            True,
            ZERO_ADDRESS,
            False,
            createPayeeLimits(),
            usd_limits,
            sender=bob
        )


def test_add_payee_saves_settings_in_wallet_config(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob, alpha_token):
    """Test that addPayee correctly saves all payee settings in user wallet config"""
    # Set global payee settings to allow canPull
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Create specific limits to verify they're saved correctly
    unit_limits = createPayeeLimits(
        _perTxCap=100,
        _perPeriodCap=1000,
        _lifetimeCap=10000
    )
    usd_limits = createPayeeLimits(
        _perTxCap=2000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=20000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=200000 * EIGHTEEN_DECIMALS
    )

    # Add payee with specific settings
    result = paymaster.addPayee(
        user_wallet,
        alice,  # payee
        True,  # canPull
        3 * ONE_DAY_IN_BLOCKS,  # periodLength
        15,  # maxNumTxsPerPeriod
        500,  # txCooldownBlocks
        True,  # failOnZeroPrice
        alpha_token,  # primaryAsset
        True,  # onlyPrimaryAsset
        unit_limits,  # unitLimits
        usd_limits,  # usdLimits
        sender=bob  # Owner
    )
    
    assert result == True
    
    # Verify the payee was added by checking the index
    assert user_wallet_config.indexOfPayee(alice) != 0

    # Get the payee config bundle to verify all settings
    payee_settings = user_wallet_config.payeeSettings(alice)

    # Verify basic settings
    assert payee_settings.canPull == True
    assert payee_settings.periodLength == 3 * ONE_DAY_IN_BLOCKS
    assert payee_settings.maxNumTxsPerPeriod == 15
    assert payee_settings.txCooldownBlocks == 500
    assert payee_settings.failOnZeroPrice == True
    assert payee_settings.primaryAsset == alpha_token.address
    assert payee_settings.onlyPrimaryAsset == True
    
    # Verify unit limits
    assert payee_settings.unitLimits.perTxCap == 100
    assert payee_settings.unitLimits.perPeriodCap == 1000
    assert payee_settings.unitLimits.lifetimeCap == 10000
    
    # Verify USD limits
    assert payee_settings.usdLimits.perTxCap == 2000 * EIGHTEEN_DECIMALS
    assert payee_settings.usdLimits.perPeriodCap == 20000 * EIGHTEEN_DECIMALS
    assert payee_settings.usdLimits.lifetimeCap == 200000 * EIGHTEEN_DECIMALS
    
    # Also verify the direct public mappings
    # Check that alice is stored at the correct index
    payee_index = user_wallet_config.indexOfPayee(alice)
    assert payee_index > 0  # Should have a non-zero index
    
    # Verify the payee address can be retrieved by index
    assert user_wallet_config.payees(payee_index) == alice
    
    # Verify the number of payees increased
    assert user_wallet_config.numPayees() == 2
    
    # Check the payeeSettings mapping directly
    direct_settings = user_wallet_config.payeeSettings(alice)
    assert direct_settings.canPull == True
    assert direct_settings.periodLength == 3 * ONE_DAY_IN_BLOCKS
    assert direct_settings.maxNumTxsPerPeriod == 15


def test_add_payee_emits_event_with_correct_data(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob, alpha_token):
    """Test that addPayee emits PayeeAdded event with all correct data"""
    # Set global payee settings to allow canPull
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Create specific limits
    unit_limits = createPayeeLimits(
        _perTxCap=50,
        _perPeriodCap=500,
        _lifetimeCap=5000
    )
    usd_limits = createPayeeLimits(
        _perTxCap=1500 * EIGHTEEN_DECIMALS,
        _perPeriodCap=15000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=150000 * EIGHTEEN_DECIMALS
    )
    
    # Add payee
    paymaster.addPayee(
        user_wallet,
        alice,  # payee
        True,  # canPull
        4 * ONE_DAY_IN_BLOCKS,  # periodLength
        20,  # maxNumTxsPerPeriod
        1000,  # txCooldownBlocks
        True,  # failOnZeroPrice
        alpha_token,  # primaryAsset
        False,  # onlyPrimaryAsset
        unit_limits,  # unitLimits
        usd_limits,  # usdLimits
        100,  # startDelay
        5000,  # activationLength
        sender=bob  # Owner
    )
    
    # Get the event
    event = filter_logs(paymaster, "PayeeAdded")[0]
    
    # Verify indexed fields
    assert event.user == user_wallet.address
    assert event.payee == alice
    
    # Verify start and expiry blocks
    # The actual block numbers depend on when the payee was added
    # Just verify the difference equals our parameters
    assert event.expiryBlock - event.startBlock == 5000  # activationLength
    
    # Verify all settings
    assert event.canPull == True
    assert event.periodLength == 4 * ONE_DAY_IN_BLOCKS
    assert event.maxNumTxsPerPeriod == 20
    assert event.txCooldownBlocks == 1000
    assert event.failOnZeroPrice == True
    assert event.primaryAsset == alpha_token.address
    assert event.onlyPrimaryAsset == False
    
    # Verify unit limits
    assert event.unitPerTxCap == 50
    assert event.unitPerPeriodCap == 500
    assert event.unitLifetimeCap == 5000
    
    # Verify USD limits
    assert event.usdPerTxCap == 1500 * EIGHTEEN_DECIMALS
    assert event.usdPerPeriodCap == 15000 * EIGHTEEN_DECIMALS
    assert event.usdLifetimeCap == 150000 * EIGHTEEN_DECIMALS


def test_add_payee_reverts_on_invalid_settings(paymaster, user_wallet, createPayeeLimits, alice, bob):
    """Test that addPayee reverts with 'invalid payee settings' when validation fails"""
    # Create invalid limits where perTxCap > perPeriodCap
    invalid_usd_limits = createPayeeLimits(
        _perTxCap=10000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=1000 * EIGHTEEN_DECIMALS,  # Less than perTxCap - invalid!
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    # This should fail validation and revert with "invalid payee settings"
    with boa.reverts("invalid payee settings"):
        paymaster.addPayee(
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
            invalid_usd_limits,  # usdLimits with invalid settings
            sender=bob  # Owner
        )
    

################
# Update Payee #
################


def test_update_payee_requires_registered_payee(paymaster, user_wallet, createPayeeLimits, alice, bob):
    """Test that updatePayee requires the payee to be already registered"""
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    # Try to update a non-existent payee
    with boa.reverts("invalid payee settings"):
        paymaster.updatePayee(
            user_wallet,
            alice,  # Not a registered payee yet
            False,  # canPull
            2 * ONE_DAY_IN_BLOCKS,  # periodLength
            10,  # maxNumTxsPerPeriod
            0,  # txCooldownBlocks
            True,  # failOnZeroPrice
            ZERO_ADDRESS,  # primaryAsset
            False,  # onlyPrimaryAsset
            createPayeeLimits(),  # unitLimits
            usd_limits,  # usdLimits
            sender=bob  # Owner
        )


def test_update_payee_verifies_caller_is_owner(paymaster, user_wallet, createPayeeLimits, alice, bob, charlie):
    """Test that only the owner can update a payee"""
    # First add alice as a payee
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    paymaster.addPayee(
        user_wallet,
        alice,
        False,
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        usd_limits,
        sender=bob
    )
    
    # Try to update as non-owner (charlie)
    with boa.reverts("no perms"):
        paymaster.updatePayee(
            user_wallet,
            alice,
            True,  # canPull (changing)
            2 * ONE_DAY_IN_BLOCKS,
            10,
            0,
            True,
            ZERO_ADDRESS,
            False,
            createPayeeLimits(),
            usd_limits,
            sender=charlie  # Not the owner
        )


def test_update_payee_saves_new_settings(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob, alpha_token, bravo_token):
    """Test that updatePayee correctly saves all new payee settings"""
    # Set global payee settings to allow canPull
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # First add alice as a payee with initial settings
    initial_unit_limits = createPayeeLimits(
        _perTxCap=50,
        _perPeriodCap=500,
        _lifetimeCap=5000
    )
    initial_usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )

    paymaster.addPayee(
        user_wallet,
        alice,
        False,  # canPull
        2 * ONE_DAY_IN_BLOCKS,  # periodLength
        5,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        alpha_token,  # primaryAsset
        False,  # onlyPrimaryAsset
        initial_unit_limits,
        initial_usd_limits,
        sender=bob
    )
    
    # Get the original start/expiry blocks
    original_settings = user_wallet_config.payeeSettings(alice)
    original_start = original_settings.startBlock
    original_expiry = original_settings.expiryBlock
    
    # Now update with new settings
    new_unit_limits = createPayeeLimits(
        _perTxCap=100,
        _perPeriodCap=1000,
        _lifetimeCap=10000
    )
    new_usd_limits = createPayeeLimits(
        _perTxCap=2000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=20000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=200000 * EIGHTEEN_DECIMALS
    )

    result = paymaster.updatePayee(
        user_wallet,
        alice,
        True,  # canPull (changed)
        3 * ONE_DAY_IN_BLOCKS,  # periodLength (changed)
        15,  # maxNumTxsPerPeriod (changed)
        500,  # txCooldownBlocks (changed)
        True,  # failOnZeroPrice (changed)
        bravo_token,  # primaryAsset (changed)
        True,  # onlyPrimaryAsset (changed)
        new_unit_limits,  # unitLimits (changed)
        new_usd_limits,  # usdLimits (changed)
        sender=bob
    )
    
    assert result == True
    
    # Get updated settings
    updated_settings = user_wallet_config.payeeSettings(alice)
    
    # Verify start/expiry blocks are preserved
    assert updated_settings.startBlock == original_start
    assert updated_settings.expiryBlock == original_expiry
    
    # Verify all new settings were saved
    assert updated_settings.canPull == True
    assert updated_settings.periodLength == 3 * ONE_DAY_IN_BLOCKS
    assert updated_settings.maxNumTxsPerPeriod == 15
    assert updated_settings.txCooldownBlocks == 500
    assert updated_settings.failOnZeroPrice == True
    assert updated_settings.primaryAsset == bravo_token.address
    assert updated_settings.onlyPrimaryAsset == True
    
    # Verify unit limits
    assert updated_settings.unitLimits.perTxCap == 100
    assert updated_settings.unitLimits.perPeriodCap == 1000
    assert updated_settings.unitLimits.lifetimeCap == 10000
    
    # Verify USD limits
    assert updated_settings.usdLimits.perTxCap == 2000 * EIGHTEEN_DECIMALS
    assert updated_settings.usdLimits.perPeriodCap == 20000 * EIGHTEEN_DECIMALS
    assert updated_settings.usdLimits.lifetimeCap == 200000 * EIGHTEEN_DECIMALS


def test_update_payee_emits_event_with_correct_data(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob, alpha_token):
    """Test that updatePayee emits PayeeUpdated event with all correct data"""
    # Set global payee settings to allow canPull
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # First add alice as a payee
    paymaster.addPayee(
        user_wallet,
        alice,
        False,
        2 * ONE_DAY_IN_BLOCKS,
        5,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS),
        sender=bob
    )
    
    # Update the payee with new settings
    unit_limits = createPayeeLimits(
        _perTxCap=75,
        _perPeriodCap=750,
        _lifetimeCap=7500
    )
    usd_limits = createPayeeLimits(
        _perTxCap=1750 * EIGHTEEN_DECIMALS,
        _perPeriodCap=17500 * EIGHTEEN_DECIMALS,
        _lifetimeCap=175000 * EIGHTEEN_DECIMALS
    )

    paymaster.updatePayee(
        user_wallet,
        alice,
        True,  # canPull
        4 * ONE_DAY_IN_BLOCKS,  # periodLength
        25,  # maxNumTxsPerPeriod
        1500,  # txCooldownBlocks
        True,  # failOnZeroPrice
        alpha_token,  # primaryAsset
        True,  # onlyPrimaryAsset
        unit_limits,
        usd_limits,
        sender=bob
    )
    
    # Get the event
    event = filter_logs(paymaster, "PayeeUpdated")[0]
    
    # Verify indexed fields
    assert event.user == user_wallet.address
    assert event.payee == alice
    
    # Verify all settings
    assert event.canPull == True
    assert event.periodLength == 4 * ONE_DAY_IN_BLOCKS
    assert event.maxNumTxsPerPeriod == 25
    assert event.txCooldownBlocks == 1500
    assert event.failOnZeroPrice == True
    assert event.primaryAsset == alpha_token.address
    assert event.onlyPrimaryAsset == True
    
    # Verify unit limits
    assert event.unitPerTxCap == 75
    assert event.unitPerPeriodCap == 750
    assert event.unitLifetimeCap == 7500
    
    # Verify USD limits
    assert event.usdPerTxCap == 1750 * EIGHTEEN_DECIMALS
    assert event.usdPerPeriodCap == 17500 * EIGHTEEN_DECIMALS
    assert event.usdLifetimeCap == 175000 * EIGHTEEN_DECIMALS


def test_update_payee_reverts_on_invalid_settings(paymaster, user_wallet, createPayeeLimits, alice, bob):
    """Test that updatePayee reverts with 'invalid payee settings' when validation fails"""
    # First add alice as a valid payee
    paymaster.addPayee(
        user_wallet,
        alice,
        False,
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS),
        sender=bob
    )
    
    # Try to update with invalid limits (perTxCap > perPeriodCap)
    invalid_usd_limits = createPayeeLimits(
        _perTxCap=10000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=1000 * EIGHTEEN_DECIMALS,  # Less than perTxCap - invalid!
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    with boa.reverts("invalid payee settings"):
        paymaster.updatePayee(
            user_wallet,
            alice,
            False,
            2 * ONE_DAY_IN_BLOCKS,
            10,
            0,
            True,
            ZERO_ADDRESS,
            False,
            createPayeeLimits(),
            invalid_usd_limits,
            sender=bob
        )


def test_update_payee_preserves_start_expiry_blocks(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob):
    """Test that updatePayee preserves original start and expiry blocks"""
    # Set global payee settings to allow canPull
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Add payee with specific start delay and activation length
    paymaster.addPayee(
        user_wallet,
        alice,
        False,
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS),
        100,  # startDelay
        5000,  # activationLength
        sender=bob
    )

    # Get original blocks
    original_settings = user_wallet_config.payeeSettings(alice)
    original_start = original_settings.startBlock
    original_expiry = original_settings.expiryBlock

    # Time travel forward
    boa.env.time_travel(blocks=1000)

    # Update the payee
    paymaster.updatePayee(
        user_wallet,
        alice,
        True,  # Change some settings
        3 * ONE_DAY_IN_BLOCKS,
        20,
        100,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        createPayeeLimits(_perTxCap=2000 * EIGHTEEN_DECIMALS),
        sender=bob
    )

    # Verify blocks are preserved
    updated_settings = user_wallet_config.payeeSettings(alice)
    assert updated_settings.startBlock == original_start
    assert updated_settings.expiryBlock == original_expiry


################
# Remove Payee #
################


def test_remove_payee_by_owner(paymaster, user_wallet, user_wallet_config, createPayeeLimits, alice, bob):
    """Test that the owner can remove a payee"""
    # First add alice as a payee
    paymaster.addPayee(
        user_wallet,
        alice,
        False,
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS),
        sender=bob
    )
    
    # Verify alice is a payee
    assert user_wallet_config.indexOfPayee(alice) != 0
    
    # Remove alice as the owner
    result = paymaster.removePayee(user_wallet, alice, sender=bob)
    assert result == True
    
    # Verify alice is no longer a payee
    assert user_wallet_config.indexOfPayee(alice) == 0


def test_remove_payee_by_payee_self(paymaster, user_wallet, user_wallet_config, createPayeeLimits, alice, bob):
    """Test that a payee can remove themselves"""
    # First add alice as a payee
    paymaster.addPayee(
        user_wallet,
        alice,
        False,
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS),
        sender=bob
    )
    
    # Verify alice is a payee
    assert user_wallet_config.indexOfPayee(alice) != 0
    
    # Alice removes herself
    result = paymaster.removePayee(user_wallet, alice, sender=alice)
    assert result == True
    
    # Verify alice is no longer a payee
    assert user_wallet_config.indexOfPayee(alice) == 0


def test_remove_payee_by_security_admin(paymaster, user_wallet, user_wallet_config, createPayeeLimits, alice, bob, charlie, mission_control, switchboard_alpha):
    """Test that security admin can remove a payee"""
    # Set charlie as security operator
    mission_control.setCanPerformSecurityAction(charlie, True, sender=switchboard_alpha.address)
    
    # First add alice as a payee
    paymaster.addPayee(
        user_wallet,
        alice,
        False,
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS),
        sender=bob
    )
    
    # Verify alice is a payee
    assert user_wallet_config.indexOfPayee(alice) != 0
    
    # Remove alice as security admin (charlie)
    result = paymaster.removePayee(user_wallet, alice, sender=charlie)
    assert result == True
    
    # Verify alice is no longer a payee
    assert user_wallet_config.indexOfPayee(alice) == 0


def test_remove_payee_unauthorized(paymaster, user_wallet, createPayeeLimits, alice, bob, charlie):
    """Test that unauthorized users cannot remove a payee"""
    # First add alice as a payee
    paymaster.addPayee(
        user_wallet,
        alice,
        False,
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS),
        sender=bob
    )
    
    # Try to remove alice as charlie (not owner, not payee, not security admin)
    with boa.reverts("no perms"):
        paymaster.removePayee(user_wallet, alice, sender=charlie)


def test_remove_payee_not_found(paymaster, user_wallet, alice, bob):
    """Test that removing a non-existent payee fails"""
    # Try to remove alice who is not a payee
    with boa.reverts("payee not found"):
        paymaster.removePayee(user_wallet, alice, sender=bob)


def test_remove_payee_invalid_wallet(paymaster, alice, bob):
    """Test that removing from invalid wallet fails"""
    # Try to remove from bob's address (not a user wallet)
    with boa.reverts("invalid user wallet"):
        paymaster.removePayee(bob, alice, sender=bob)


def test_remove_payee_emits_event(paymaster, user_wallet, createPayeeLimits, alice, bob):
    """Test that removePayee emits PayeeRemoved event with correct data"""
    # First add alice as a payee
    paymaster.addPayee(
        user_wallet,
        alice,
        False,
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS),
        sender=bob
    )
    
    # Remove alice
    paymaster.removePayee(user_wallet, alice, sender=bob)
    
    # Get the event
    event = filter_logs(paymaster, "PayeeRemoved")[0]
    
    # Verify event data
    assert event.user == user_wallet.address
    assert event.payee == alice
    assert event.removedBy == bob


def test_remove_payee_clears_all_data(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob, charlie):
    """Test that removing a payee clears all their data"""
    # Set global payee settings to allow canPull
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Add alice as a payee with specific settings
    paymaster.addPayee(
        user_wallet,
        alice,
        True,
        3 * ONE_DAY_IN_BLOCKS,
        15,
        500,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(_perTxCap=100),
        createPayeeLimits(_perTxCap=2000 * EIGHTEEN_DECIMALS),
        sender=bob
    )
    
    # Also add charlie to verify numPayees changes correctly
    paymaster.addPayee(
        user_wallet,
        charlie,
        False,
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS),
        sender=bob
    )

    # Record initial state
    initial_num_payees = user_wallet_config.numPayees()
    alice_index = user_wallet_config.indexOfPayee(alice)
    
    # Remove alice
    paymaster.removePayee(user_wallet, alice, sender=bob)
    
    # Verify alice's data is cleared
    assert user_wallet_config.indexOfPayee(alice) == 0
    
    # Verify the payee count decreased
    assert user_wallet_config.numPayees() == initial_num_payees - 1
    
    # Verify alice's index is no longer mapped to alice
    assert user_wallet_config.payees(alice_index) != alice
    
    # Verify alice's settings are cleared (default values)
    settings = user_wallet_config.payeeSettings(alice)
    assert settings.startBlock == 0
    assert settings.expiryBlock == 0
    assert settings.canPull == False
    assert settings.periodLength == 0


def test_remove_payee_allows_re_adding(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob):
    """Test that a removed payee can be added again"""
    # Set global payee settings to allow canPull
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Add alice as a payee
    paymaster.addPayee(
        user_wallet,
        alice,
        False,
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS),
        sender=bob
    )

    # Remove alice
    paymaster.removePayee(user_wallet, alice, sender=bob)

    # Verify alice is removed
    assert user_wallet_config.indexOfPayee(alice) == 0

    # Add alice again with different settings
    result = paymaster.addPayee(
        user_wallet,
        alice,
        True,  # Different settings
        3 * ONE_DAY_IN_BLOCKS,
        20,
        100,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        createPayeeLimits(_perTxCap=2000 * EIGHTEEN_DECIMALS),
        sender=bob
    )

    assert result == True
    
    # Verify alice is added again
    assert user_wallet_config.indexOfPayee(alice) != 0
    
    # Verify new settings
    settings = user_wallet_config.payeeSettings(alice)
    assert settings.canPull == True
    assert settings.periodLength == 3 * ONE_DAY_IN_BLOCKS
    assert settings.maxNumTxsPerPeriod == 20


#############################
# canPull Validation Tests  #
#############################


def test_payee_cannot_have_canpull_when_global_is_false(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob):
    """Test that payee cannot have canPull=True when global canPull=False"""
    # Set global payee settings with canPull=False (default)
    global_settings = createGlobalPayeeSettings(_canPull=False)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Create valid limits
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    # Try to add payee with canPull=True (should fail)
    with boa.reverts("invalid payee settings"):
        paymaster.addPayee(
            user_wallet,
            alice,
            True,  # canPull - not allowed when global is False
            2 * ONE_DAY_IN_BLOCKS,
            10,
            0,
            True,
            ZERO_ADDRESS,
            False,
            createPayeeLimits(),
            usd_limits,
            sender=bob
        )


def test_payee_can_have_canpull_false_when_global_is_false(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob):
    """Test that payee can have canPull=False when global canPull=False"""
    # Set global payee settings with canPull=False
    global_settings = createGlobalPayeeSettings(_canPull=False)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Create valid limits
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    # Add payee with canPull=False (should succeed)
    result = paymaster.addPayee(
        user_wallet,
        alice,
        False,  # canPull=False is always allowed
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        usd_limits,
        sender=bob
    )
    
    assert result == True
    assert user_wallet_config.payeeSettings(alice).canPull == False


def test_payee_can_have_canpull_true_when_global_is_true(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob):
    """Test that payee can have canPull=True when global canPull=True"""
    # Set global payee settings with canPull=True
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Create valid limits
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    # Add payee with canPull=True (should succeed)
    result = paymaster.addPayee(
        user_wallet,
        alice,
        True,  # canPull=True allowed when global is True
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        usd_limits,
        sender=bob
    )
    
    assert result == True
    assert user_wallet_config.payeeSettings(alice).canPull == True


def test_payee_can_have_canpull_false_when_global_is_true(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob):
    """Test that payee can have canPull=False even when global canPull=True"""
    # Set global payee settings with canPull=True
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Create valid limits
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    # Add payee with canPull=False (should succeed)
    result = paymaster.addPayee(
        user_wallet,
        alice,
        False,  # canPull=False is always allowed
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        usd_limits,
        sender=bob
    )
    
    assert result == True
    assert user_wallet_config.payeeSettings(alice).canPull == False


def test_pull_payee_must_have_limits(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob):
    """Test that pull payees (canPull=True) must have at least one type of limit"""
    # Set global payee settings with canPull=True
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Try to add pull payee with no limits (all zeros)
    with boa.reverts("invalid payee settings"):
        paymaster.addPayee(
            user_wallet,
            alice,
            True,  # canPull=True
            2 * ONE_DAY_IN_BLOCKS,
            10,
            0,
            True,
            ZERO_ADDRESS,
            False,
            createPayeeLimits(),  # All zero limits
            createPayeeLimits(),  # All zero limits
            sender=bob
        )


def test_pull_payee_with_unit_limits_only(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob):
    """Test that pull payees can have only unit limits"""
    # Set global payee settings with canPull=True
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Create unit limits only
    unit_limits = createPayeeLimits(
        _perTxCap=100,
        _perPeriodCap=1000,
        _lifetimeCap=10000
    )
    
    # Add pull payee with unit limits only (should succeed)
    result = paymaster.addPayee(
        user_wallet,
        alice,
        True,  # canPull=True
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        unit_limits,  # Has unit limits
        createPayeeLimits(),  # No USD limits
        sender=bob
    )
    
    assert result == True
    assert user_wallet_config.payeeSettings(alice).canPull == True


def test_pull_payee_with_usd_limits_only(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob):
    """Test that pull payees can have only USD limits"""
    # Set global payee settings with canPull=True
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Create USD limits only
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    # Add pull payee with USD limits only (should succeed)
    result = paymaster.addPayee(
        user_wallet,
        alice,
        True,  # canPull=True
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),  # No unit limits
        usd_limits,  # Has USD limits
        sender=bob
    )
    
    assert result == True
    assert user_wallet_config.payeeSettings(alice).canPull == True


def test_update_payee_cannot_enable_canpull_when_global_is_false(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob):
    """Test that updating a payee cannot set canPull=True when global canPull=False"""
    # Set global payee settings with canPull=False
    global_settings = createGlobalPayeeSettings(_canPull=False)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # First add alice as a payee with canPull=False
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    paymaster.addPayee(
        user_wallet,
        alice,
        False,  # canPull=False
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        usd_limits,
        sender=bob
    )
    
    # Try to update to canPull=True (should fail)
    with boa.reverts("invalid payee settings"):
        paymaster.updatePayee(
            user_wallet,
            alice,
            True,  # Try to enable canPull
            2 * ONE_DAY_IN_BLOCKS,
            10,
            0,
            True,
            ZERO_ADDRESS,
            False,
            createPayeeLimits(),
            usd_limits,
            sender=bob
        )


def test_changing_global_canpull_does_not_affect_existing_payees(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob):
    """Test that changing global canPull setting doesn't affect existing payees"""
    # Set global payee settings with canPull=True
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Add payee with canPull=True
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    paymaster.addPayee(
        user_wallet,
        alice,
        True,  # canPull=True
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(_perTxCap=100),  # Has limits
        usd_limits,
        sender=bob
    )
    
    # Verify payee has canPull=True
    assert user_wallet_config.payeeSettings(alice).canPull == True
    
    # Now change global settings to canPull=False
    global_settings = createGlobalPayeeSettings(_canPull=False)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Existing payee should still have canPull=True
    assert user_wallet_config.payeeSettings(alice).canPull == True

    # But we can't add new payees with canPull=True
    with boa.reverts("invalid payee settings"):
        paymaster.addPayee(
            user_wallet,
            bob,  # Different payee
            True,  # canPull=True not allowed anymore
            2 * ONE_DAY_IN_BLOCKS,
            10,
            0,
            True,
            ZERO_ADDRESS,
            False,
            createPayeeLimits(_perTxCap=100),
            usd_limits,
            sender=bob
        )
