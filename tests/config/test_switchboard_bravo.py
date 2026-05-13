import boa

from conf_utils import filter_logs, instant_action_settings_tuple
from constants import BRAVO_ACTION_TYPE, ONE_YEAR_IN_BLOCKS, STARTER_AGENT_TYPE, ZERO_ADDRESS


def _execute_after_timelock(switchboard_bravo, aid, governance):
    blocks = switchboard_bravo.getActionConfirmationBlock(aid) - boa.env.evm.patch.block_number
    if blocks > 0:
        boa.env.time_travel(blocks=blocks)
    return switchboard_bravo.executePendingAction(aid, sender=governance.address)


def _enable_security_actor(switchboard_bravo, governance, signer):
    aid = switchboard_bravo.setCanPerformSecurityAction(signer, True, sender=governance.address)
    assert _execute_after_timelock(switchboard_bravo, aid, governance)
    return aid


def test_security_action_enable_stages_and_executes(switchboard_bravo, governance, alice, mission_control):
    assert not mission_control.canPerformSecurityAction(alice)

    aid = switchboard_bravo.setCanPerformSecurityAction(alice, True, sender=governance.address)

    logs = filter_logs(switchboard_bravo, "PendingCanPerformSecurityAction")
    assert switchboard_bravo.actionType(aid) == BRAVO_ACTION_TYPE.CAN_PERFORM_SECURITY_ACTION
    pending = switchboard_bravo.pendingAddrToBool(aid)
    assert pending.addr == alice
    assert pending.isAllowed is True
    assert logs[0].signer == alice
    assert logs[0].canPerform is True
    assert logs[0].actionId == aid

    assert switchboard_bravo.executePendingAction(aid, sender=governance.address) is False
    assert not mission_control.canPerformSecurityAction(alice)

    assert _execute_after_timelock(switchboard_bravo, aid, governance)
    exec_logs = filter_logs(switchboard_bravo, "CanPerformSecurityAction")
    assert exec_logs[0].signer == alice
    assert exec_logs[0].canPerform is True
    assert mission_control.canPerformSecurityAction(alice)
    assert switchboard_bravo.actionType(aid) == 0


def test_security_action_disable_is_immediate(switchboard_bravo, governance, bob, mission_control):
    _enable_security_actor(switchboard_bravo, governance, bob)
    assert mission_control.canPerformSecurityAction(bob)

    aid = switchboard_bravo.setCanPerformSecurityAction(bob, False, sender=governance.address)

    logs = filter_logs(switchboard_bravo, "CanPerformSecurityAction")
    assert aid == 0
    assert logs[-1].signer == bob
    assert logs[-1].canPerform is False
    assert not mission_control.canPerformSecurityAction(bob)


def test_set_ripe_rewards_config_success(switchboard_bravo, governance, mission_control):
    new_stake_ratio = 75_00
    new_duration = 50400
    original_config = mission_control.ripeRewardsConfig()

    aid = switchboard_bravo.setRipeRewardsConfig(new_stake_ratio, new_duration, sender=governance.address)

    logs = filter_logs(switchboard_bravo, "PendingRipeRewardsConfigChange")
    assert switchboard_bravo.actionType(aid) == BRAVO_ACTION_TYPE.RIPE_REWARDS_CONFIG
    assert logs[0].ripeStakeRatio == new_stake_ratio
    assert logs[0].ripeLockDuration == new_duration
    assert logs[0].actionId == aid
    pending = switchboard_bravo.pendingRipeRewardsConfig(aid)
    assert pending.stakeRatio == new_stake_ratio
    assert pending.lockDuration == new_duration

    ripe_config = mission_control.ripeRewardsConfig()
    assert ripe_config[0] == original_config[0]
    assert ripe_config[1] == original_config[1]

    assert _execute_after_timelock(switchboard_bravo, aid, governance)

    logs = filter_logs(switchboard_bravo, "RipeRewardsConfigSet")
    assert logs[0].ripeStakeRatio == new_stake_ratio
    assert logs[0].ripeLockDuration == new_duration

    ripe_config = mission_control.ripeRewardsConfig()
    assert ripe_config[0] == new_stake_ratio
    assert ripe_config[1] == new_duration
    assert switchboard_bravo.actionType(aid) == 0


def test_set_ripe_rewards_config_different_values(switchboard_bravo, governance, mission_control):
    configs = [
        (90_00, 7200),
        (50_00, 216000),
        (0, 1),
        (100_00, 2628000),
    ]

    for stake_ratio, duration in configs:
        aid = switchboard_bravo.setRipeRewardsConfig(stake_ratio, duration, sender=governance.address)
        assert _execute_after_timelock(switchboard_bravo, aid, governance)

        ripe_config = mission_control.ripeRewardsConfig()
        assert ripe_config[0] == stake_ratio
        assert ripe_config[1] == duration


def test_set_ripe_rewards_config_non_governance_reverts(switchboard_bravo, alice, mission_control):
    current_config = mission_control.ripeRewardsConfig()

    with boa.reverts("no perms"):
        switchboard_bravo.setRipeRewardsConfig(85_00, 50400, sender=alice)

    ripe_config = mission_control.ripeRewardsConfig()
    assert ripe_config[0] == current_config[0]
    assert ripe_config[1] == current_config[1]


def test_set_ripe_rewards_config_invalid_values_revert(switchboard_bravo, governance):
    with boa.reverts("invalid ripe rewards config"):
        switchboard_bravo.setRipeRewardsConfig(100_01, 1000, sender=governance.address)

    with boa.reverts("invalid ripe rewards config"):
        switchboard_bravo.setRipeRewardsConfig(50_00, 0, sender=governance.address)


def test_set_ripe_rewards_config_execute_before_timelock_fails(switchboard_bravo, governance, mission_control):
    original_config = mission_control.ripeRewardsConfig()

    aid = switchboard_bravo.setRipeRewardsConfig(75_00, 50400, sender=governance.address)

    assert switchboard_bravo.executePendingAction(aid, sender=governance.address) is False

    ripe_config = mission_control.ripeRewardsConfig()
    assert ripe_config[0] == original_config[0]
    assert ripe_config[1] == original_config[1]
    assert switchboard_bravo.actionType(aid) == BRAVO_ACTION_TYPE.RIPE_REWARDS_CONFIG


def test_creator_whitelist_governance_and_security_actor_paths(
    switchboard_bravo, governance, alice, bob, mission_control
):
    switchboard_bravo.setCreatorWhitelist(alice, True, sender=governance.address)
    assert mission_control.creatorWhitelist(alice)

    _enable_security_actor(switchboard_bravo, governance, bob)
    switchboard_bravo.setCreatorWhitelist(alice, False, sender=bob)

    logs = filter_logs(switchboard_bravo, "CreatorWhitelistSet")
    assert logs[-1].creator == alice
    assert logs[-1].isWhitelisted is False
    assert logs[-1].caller == bob
    assert not mission_control.creatorWhitelist(alice)

    with boa.reverts("no perms"):
        switchboard_bravo.setCreatorWhitelist(alice, True, sender=bob)

    with boa.reverts("invalid creator"):
        switchboard_bravo.setCreatorWhitelist(ZERO_ADDRESS, True, sender=governance.address)


def test_locked_signer_governance_and_security_actor_paths(
    switchboard_bravo, governance, alice, bob, mission_control
):
    switchboard_bravo.setLockedSigner(alice, True, sender=governance.address)
    assert mission_control.isLockedSigner(alice)

    _enable_security_actor(switchboard_bravo, governance, bob)
    switchboard_bravo.setLockedSigner(alice, False, sender=bob)

    logs = filter_logs(switchboard_bravo, "LockedSignerSet")
    assert logs[-1].signer == alice
    assert logs[-1].isLocked is False
    assert logs[-1].caller == bob
    assert not mission_control.isLockedSigner(alice)

    with boa.reverts("no perms"):
        switchboard_bravo.setLockedSigner(alice, True, sender=bob)

    with boa.reverts("invalid creator"):
        switchboard_bravo.setLockedSigner(ZERO_ADDRESS, True, sender=governance.address)


def test_hatchery_starter_agent_config(switchboard_bravo, governance, hatchery, alice):
    assert switchboard_bravo.setHatcheryStarterAgentConfig(
        STARTER_AGENT_TYPE.STAGING,
        alice,
        ONE_YEAR_IN_BLOCKS,
        sender=governance.address,
    )

    config = hatchery.stagingStarterAgentConfig()
    logs = filter_logs(switchboard_bravo, "HatcheryStarterAgentConfigSet")
    assert config.startingAgent == alice
    assert config.startingAgentActivationLength == ONE_YEAR_IN_BLOCKS
    assert logs[-1].hatchery == hatchery.address
    assert logs[-1].starterAgentType == STARTER_AGENT_TYPE.STAGING

    with boa.reverts("no perms"):
        switchboard_bravo.setHatcheryStarterAgentConfig(
            STARTER_AGENT_TYPE.STAGING,
            alice,
            ONE_YEAR_IN_BLOCKS,
            sender=alice,
        )

    with boa.reverts("prod owned by mission control"):
        switchboard_bravo.setHatcheryStarterAgentConfig(
            STARTER_AGENT_TYPE.PROD,
            alice,
            ONE_YEAR_IN_BLOCKS,
            sender=governance.address,
        )


def test_hatchery_non_prod_creator(switchboard_bravo, governance, hatchery, alice, bob, mission_control):
    assert switchboard_bravo.setHatcheryNonProdCreator(alice, sender=governance.address)
    logs = filter_logs(switchboard_bravo, "HatcheryNonProdCreatorSet")
    assert hatchery.nonProdCreator() == alice
    assert logs[-1].hatchery == hatchery.address
    assert logs[-1].nonProdCreator == alice

    mission_control.setCreatorWhitelist(bob, True, sender=switchboard_bravo.address)
    with boa.reverts("non-prod creator is whitelisted"):
        switchboard_bravo.setHatcheryNonProdCreator(bob, sender=governance.address)

    with boa.reverts("no perms"):
        switchboard_bravo.setHatcheryNonProdCreator(bob, sender=alice)


def test_hatchery_default_instant_action_settings(switchboard_bravo, governance, hatchery, alice):
    assert switchboard_bravo.setHatcheryDefaultInstantActionSettings(
        False,
        True,
        False,
        True,
        sender=governance.address,
    )

    logs = filter_logs(switchboard_bravo, "HatcheryDefaultInstantActionSettingsSet")
    assert instant_action_settings_tuple(hatchery.defaultInstantActionSettings()) == (False, True, False, True)
    assert logs[-1].hatchery == hatchery.address
    assert logs[-1].canInstantAddManager is False
    assert logs[-1].canInstantAddPayee is True
    assert logs[-1].canInstantSetGlobalPayeeSettings is False
    assert logs[-1].canInstantSetChequeSettings is True

    with boa.reverts("no perms"):
        switchboard_bravo.setHatcheryDefaultInstantActionSettings(
            True,
            True,
            True,
            True,
            sender=alice,
        )
