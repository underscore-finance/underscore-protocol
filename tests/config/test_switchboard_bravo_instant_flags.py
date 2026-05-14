import boa
import pytest

from config.BluePrint import PARAMS
from conf_utils import filter_logs


ACTIONS = [
    dict(
        method="setCanInstantAddManager",
        target_fixture="high_command",
        getter="canInstantAddManager",
        setter="setCanInstantAddManager",
        pending_getter="pendingCanInstantAddManagerEnable",
        pending_event="PendingEnableWalletCanInstantAddManagerAction",
        set_event="WalletCanInstantAddManagerSet",
        invalid_revert="invalid high command",
    ),
    dict(
        method="setCanInstantAddPayee",
        target_fixture="paymaster",
        getter="canInstantAddPayee",
        setter="setCanInstantAddPayee",
        pending_getter="pendingCanInstantAddPayeeEnable",
        pending_event="PendingEnableWalletCanInstantAddPayeeAction",
        set_event="WalletCanInstantAddPayeeSet",
        invalid_revert="invalid paymaster",
    ),
    dict(
        method="setCanInstantSetGlobalPayeeSettings",
        target_fixture="paymaster",
        getter="canInstantSetGlobalPayeeSettings",
        setter="setCanInstantSetGlobalPayeeSettings",
        pending_getter="pendingCanInstantSetGlobalPayeeSettingsEnable",
        pending_event="PendingEnableWalletCanInstantSetGlobalPayeeSettingsAction",
        set_event="WalletCanInstantSetGlobalPayeeSettingsSet",
        invalid_revert="invalid paymaster",
    ),
    dict(
        method="setCanInstantSetChequeSettings",
        target_fixture="cheque_book",
        getter="canInstantSetChequeSettings",
        setter="setCanInstantSetChequeSettings",
        pending_getter="pendingCanInstantSetChequeSettingsEnable",
        pending_event="PendingEnableWalletCanInstantSetChequeSettingsAction",
        set_event="WalletCanInstantSetChequeSettingsSet",
        invalid_revert="invalid cheque book",
    ),
]


def _target(request, action):
    return request.getfixturevalue(action["target_fixture"])


def _pending(switchboard_bravo, action):
    return getattr(switchboard_bravo, action["pending_getter"])()


def _reset_action(request, switchboard_bravo, governance, action):
    target = _target(request, action)
    pending = _pending(switchboard_bravo, action)
    if pending.actionId != 0 and switchboard_bravo.hasPendingAction(pending.actionId):
        switchboard_bravo.cancelPendingAction(pending.actionId, sender=governance.address)
    if getattr(target, action["getter"])():
        getattr(target, action["setter"])(False, sender=switchboard_bravo.address)
    switchboard_bravo.get_logs()
    target.get_logs()
    return target


def _stage_enable(switchboard_bravo, target, governance, action):
    return getattr(switchboard_bravo, action["method"])(target.address, True, sender=governance.address)


def _execute_after_timelock(switchboard_bravo, aid, governance):
    blocks = switchboard_bravo.getActionConfirmationBlock(aid) - boa.env.evm.patch.block_number
    if blocks > 0:
        boa.env.time_travel(blocks=blocks)
    return switchboard_bravo.executePendingAction(aid, sender=governance.address)


def _deploy_rotated_high_command(undy_hq_deploy, fork):
    return boa.load(
        "contracts/core/walletBackpack/HighCommand.vy",
        undy_hq_deploy,
        PARAMS[fork]["BOSS_MIN_MANAGER_PERIOD"],
        PARAMS[fork]["BOSS_MAX_MANAGER_PERIOD"],
        PARAMS[fork]["BOSS_MIN_ACTIVATION_LENGTH"],
        PARAMS[fork]["BOSS_MAX_ACTIVATION_LENGTH"],
        PARAMS[fork]["BOSS_MAX_START_DELAY"],
        False,
        name="rotated_instant_flag_high_command",
    )


def test_backpack_constructor_initializes_protocol_instant_flags(undy_hq_deploy, fork):
    high_command = boa.load(
        "contracts/core/walletBackpack/HighCommand.vy",
        undy_hq_deploy,
        PARAMS[fork]["BOSS_MIN_MANAGER_PERIOD"],
        PARAMS[fork]["BOSS_MAX_MANAGER_PERIOD"],
        PARAMS[fork]["BOSS_MIN_ACTIVATION_LENGTH"],
        PARAMS[fork]["BOSS_MAX_ACTIVATION_LENGTH"],
        PARAMS[fork]["BOSS_MAX_START_DELAY"],
        True,
        name="constructor_flag_high_command",
    )
    paymaster = boa.load(
        "contracts/core/walletBackpack/Paymaster.vy",
        undy_hq_deploy,
        PARAMS[fork]["PAYMASTER_MIN_PAYEE_PERIOD"],
        PARAMS[fork]["PAYMASTER_MAX_PAYEE_PERIOD"],
        PARAMS[fork]["PAYMASTER_MIN_ACTIVATION_LENGTH"],
        PARAMS[fork]["PAYMASTER_MAX_ACTIVATION_LENGTH"],
        PARAMS[fork]["PAYMASTER_MAX_START_DELAY"],
        True,
        True,
        name="constructor_flag_paymaster",
    )
    cheque_book = boa.load(
        "contracts/core/walletBackpack/ChequeBook.vy",
        undy_hq_deploy,
        PARAMS[fork]["CHEQUE_MIN_PERIOD"],
        PARAMS[fork]["CHEQUE_MAX_PERIOD"],
        PARAMS[fork]["CHEQUE_MIN_EXPENSIVE_DELAY"],
        PARAMS[fork]["CHEQUE_MAX_UNLOCK_BLOCKS"],
        PARAMS[fork]["CHEQUE_MAX_EXPIRY_BLOCKS"],
        True,
        name="constructor_flag_cheque_book",
    )
    migrator = boa.load(
        "contracts/core/walletBackpack/Migrator.vy",
        undy_hq_deploy,
        False,
        name="constructor_flag_migrator",
    )

    assert high_command.canInstantAddManager() is True
    assert paymaster.canInstantAddPayee() is True
    assert paymaster.canInstantSetGlobalPayeeSettings() is True
    assert cheque_book.canInstantSetChequeSettings() is True
    assert migrator.instantMigrationEnabled() is False


def test_constructor_enabled_protocol_flags_have_no_switchboard_pending_state(switchboard_bravo):
    assert switchboard_bravo.pendingCanInstantAddManagerEnable().actionId == 0
    assert switchboard_bravo.pendingCanInstantAddPayeeEnable().actionId == 0
    assert switchboard_bravo.pendingCanInstantSetGlobalPayeeSettingsEnable().actionId == 0
    assert switchboard_bravo.pendingCanInstantSetChequeSettingsEnable().actionId == 0
    assert switchboard_bravo.pendingInstantMigrationEnable().actionId == 0


@pytest.mark.parametrize("action", ACTIONS)
def test_enabling_constructor_true_protocol_flag_reverts_as_already_enabled(
    request, switchboard_bravo, governance, action
):
    target = _target(request, action)
    getattr(target, action["setter"])(True, sender=switchboard_bravo.address)

    with boa.reverts("already enabled"):
        _stage_enable(switchboard_bravo, target, governance, action)


@pytest.mark.parametrize("action", ACTIONS)
def test_governance_can_stage_protocol_instant_flag_enable(request, switchboard_bravo, governance, action):
    target = _reset_action(request, switchboard_bravo, governance, action)

    aid = _stage_enable(switchboard_bravo, target, governance, action)
    logs = filter_logs(switchboard_bravo, action["pending_event"])

    pending = _pending(switchboard_bravo, action)
    event = logs[0]
    assert aid != 0
    assert pending.actionId == aid
    assert pending.target == target.address
    assert event.target == target.address
    assert event.confirmationBlock == switchboard_bravo.getActionConfirmationBlock(aid)
    assert event.actionId == aid
    assert event.caller == governance.address


@pytest.mark.parametrize("action", ACTIONS)
def test_protocol_instant_flag_execute_before_and_after_timelock(request, switchboard_bravo, governance, action):
    target = _reset_action(request, switchboard_bravo, governance, action)
    aid = _stage_enable(switchboard_bravo, target, governance, action)

    assert switchboard_bravo.executePendingAction(aid, sender=governance.address) is False
    assert getattr(target, action["getter"])() is False
    assert _pending(switchboard_bravo, action).actionId == aid

    assert _execute_after_timelock(switchboard_bravo, aid, governance) is True
    logs = filter_logs(switchboard_bravo, action["set_event"])
    assert getattr(target, action["getter"])() is True
    assert _pending(switchboard_bravo, action).actionId == 0
    event = logs[0]
    assert event.target == target.address
    assert event.isEnabled is True
    assert event.caller == governance.address


def test_staged_protocol_flag_enable_uses_original_target_after_wallet_backpack_rotation(
    request,
    switchboard_bravo,
    governance,
    undy_hq,
    undy_hq_deploy,
    fork,
    wallet_backpack,
    action_data_provider,
):
    with boa.env.anchor():
        action = ACTIONS[0]
        target = _reset_action(request, switchboard_bravo, governance, action)
        aid = _stage_enable(switchboard_bravo, target, governance, action)

        rotated_high_command = _deploy_rotated_high_command(undy_hq_deploy, fork)
        rotated_wallet_backpack = boa.load(
            "contracts/mock/MockWalletBackpack.vy",
            wallet_backpack.kernel(),
            wallet_backpack.sentinel(),
            rotated_high_command.address,
            wallet_backpack.paymaster(),
            wallet_backpack.chequeBook(),
            wallet_backpack.migrator(),
            action_data_provider.address,
            name="rotated_instant_flag_wallet_backpack",
        )
        assert undy_hq.startAddressUpdateToRegistry(8, rotated_wallet_backpack.address, sender=governance.address)
        boa.env.time_travel(blocks=undy_hq.registryChangeTimeLock())
        assert undy_hq.confirmAddressUpdateToRegistry(8, sender=governance.address)

        assert _execute_after_timelock(switchboard_bravo, aid, governance)

        assert target.canInstantAddManager() is True
        assert rotated_high_command.canInstantAddManager() is False


@pytest.mark.parametrize("action", ACTIONS)
def test_security_actor_can_disable_protocol_instant_flag_immediately(
    request, switchboard_bravo, governance, mission_control, alice, action
):
    target = _reset_action(request, switchboard_bravo, governance, action)
    aid = _stage_enable(switchboard_bravo, target, governance, action)
    assert _execute_after_timelock(switchboard_bravo, aid, governance)
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_bravo.address)
    switchboard_bravo.get_logs()

    assert getattr(switchboard_bravo, action["method"])(target.address, False, sender=alice) == 0

    assert getattr(target, action["getter"])() is False
    event = filter_logs(switchboard_bravo, action["set_event"])[0]
    assert event.target == target.address
    assert event.isEnabled is False
    assert event.caller == alice


@pytest.mark.parametrize("action", ACTIONS)
def test_security_actor_can_disable_protocol_instant_flag_when_already_disabled(
    request, switchboard_bravo, governance, mission_control, alice, action
):
    target = _reset_action(request, switchboard_bravo, governance, action)
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_bravo.address)
    switchboard_bravo.get_logs()

    assert getattr(switchboard_bravo, action["method"])(target.address, False, sender=alice) == 0
    logs = filter_logs(switchboard_bravo, action["set_event"])

    assert getattr(target, action["getter"])() is False
    assert _pending(switchboard_bravo, action).actionId == 0
    event = logs[0]
    assert event.target == target.address
    assert event.isEnabled is False
    assert event.caller == alice


@pytest.mark.parametrize("action", ACTIONS)
def test_disabling_protocol_instant_flag_cancels_matching_pending_enable(
    request, switchboard_bravo, governance, mission_control, alice, action
):
    target = _reset_action(request, switchboard_bravo, governance, action)
    aid = _stage_enable(switchboard_bravo, target, governance, action)
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_bravo.address)

    assert getattr(switchboard_bravo, action["method"])(target.address, False, sender=alice) == 0

    assert _pending(switchboard_bravo, action).actionId == 0
    assert not switchboard_bravo.hasPendingAction(aid)
    assert switchboard_bravo.executePendingAction(aid, sender=governance.address) is False
    assert getattr(target, action["getter"])() is False


@pytest.mark.parametrize("action", ACTIONS)
def test_duplicate_protocol_instant_flag_pending_enable_reverts(request, switchboard_bravo, governance, action):
    target = _reset_action(request, switchboard_bravo, governance, action)
    aid = _stage_enable(switchboard_bravo, target, governance, action)
    assert _pending(switchboard_bravo, action).actionId == aid

    with boa.reverts("pending enable exists"):
        _stage_enable(switchboard_bravo, target, governance, action)


@pytest.mark.parametrize("action", ACTIONS)
def test_cancel_pending_action_cancels_protocol_instant_flag_action_and_allows_restaging(
    request, switchboard_bravo, governance, action
):
    target = _reset_action(request, switchboard_bravo, governance, action)
    aid = _stage_enable(switchboard_bravo, target, governance, action)

    assert switchboard_bravo.cancelPendingAction(aid, sender=governance.address)

    assert not switchboard_bravo.hasPendingAction(aid)
    assert getattr(target, action["getter"])() is False
    assert _pending(switchboard_bravo, action).actionId == 0

    new_aid = _stage_enable(switchboard_bravo, target, governance, action)
    assert new_aid != aid
    assert _pending(switchboard_bravo, action).actionId == new_aid
    assert switchboard_bravo.hasPendingAction(new_aid)


@pytest.mark.parametrize("action", ACTIONS)
def test_protocol_instant_flag_rejects_unregistered_backpack_target(
    request, switchboard_bravo, governance, alice, action
):
    _reset_action(request, switchboard_bravo, governance, action)

    with boa.reverts(action["invalid_revert"]):
        getattr(switchboard_bravo, action["method"])(alice, True, sender=governance.address)

    with boa.reverts(action["invalid_revert"]):
        getattr(switchboard_bravo, action["method"])(alice, False, sender=governance.address)
