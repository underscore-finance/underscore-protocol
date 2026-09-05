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


def _settings_tuple(settings):
    return (
        settings.canInstantAddManager,
        settings.canInstantAddPayee,
        settings.canInstantSetGlobalPayeeSettings,
        settings.canInstantSetChequeSettings,
    )


def _pending_hatchery_default_tuple(switchboard_bravo):
    return _settings_tuple(switchboard_bravo.pendingHatcheryDefaultInstantSettings().settings)


def _set_hatchery_defaults_and_execute_if_staged(switchboard_bravo, governance, settings):
    assert switchboard_bravo.setHatcheryDefaultInstantActionSettings(*settings, sender=governance.address)
    pending = switchboard_bravo.pendingHatcheryDefaultInstantSettings()
    if pending.actionId != 0:
        assert _execute_after_timelock(switchboard_bravo, pending.actionId, governance)


def _deploy_mock_loot_distributor(name):
    return boa.load("contracts/mock/MockLootDistributor.vy", name=name)


def _deploy_hatchery_like(hatchery, undy_hq, settings, name):
    return boa.load(
        "contracts/core/Hatchery.vy",
        undy_hq,
        hatchery.WETH(),
        hatchery.ETH(),
        settings,
        hatchery.stagingStarterAgentConfig(),
        hatchery.devStarterAgentConfig(),
        hatchery.nonProdCreator(),
        name=name,
    )


def _rotate_hatchery(undy_hq, governance, hatchery):
    assert undy_hq.startAddressUpdateToRegistry(5, hatchery.address, sender=governance.address)
    boa.env.time_travel(blocks=undy_hq.registryChangeTimeLock())
    assert undy_hq.confirmAddressUpdateToRegistry(5, sender=governance.address)


def _rotate_loot_distributor(undy_hq, governance, loot_distributor):
    assert undy_hq.startAddressUpdateToRegistry(6, loot_distributor.address, sender=governance.address)
    boa.env.time_travel(blocks=undy_hq.registryChangeTimeLock())
    assert undy_hq.confirmAddressUpdateToRegistry(6, sender=governance.address)


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


def test_hatchery_starter_agent_config(switchboard_bravo, governance, hatchery, alice, starter_agent):
    assert switchboard_bravo.setHatcheryStarterAgentConfig(
        STARTER_AGENT_TYPE.STAGING,
        starter_agent.address,
        ONE_YEAR_IN_BLOCKS,
        sender=governance.address,
    )

    config = hatchery.stagingStarterAgentConfig()
    logs = filter_logs(switchboard_bravo, "HatcheryStarterAgentConfigSet")
    assert config.startingAgent == starter_agent.address
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


def test_hatchery_default_instant_enable_stages_and_executes(
    switchboard_bravo, governance, hatchery
):
    with boa.env.anchor():
        _set_hatchery_defaults_and_execute_if_staged(switchboard_bravo, governance, (False, False, False, False))

        assert switchboard_bravo.setHatcheryDefaultInstantActionSettings(
            True, False, False, False, sender=governance.address
        )

        pending = switchboard_bravo.pendingHatcheryDefaultInstantSettings()
        aid = pending.actionId
        assert switchboard_bravo.actionType(aid) == BRAVO_ACTION_TYPE.ENABLE_HATCHERY_DEFAULT_INSTANT_SETTINGS
        assert pending.hatchery == hatchery.address
        assert _pending_hatchery_default_tuple(switchboard_bravo) == (True, False, False, False)
        assert instant_action_settings_tuple(hatchery.defaultInstantActionSettings()) == (False, False, False, False)

        assert switchboard_bravo.executePendingAction(aid, sender=governance.address) is False
        assert instant_action_settings_tuple(hatchery.defaultInstantActionSettings()) == (False, False, False, False)

        assert _execute_after_timelock(switchboard_bravo, aid, governance)
        assert instant_action_settings_tuple(hatchery.defaultInstantActionSettings()) == (True, False, False, False)
        assert switchboard_bravo.pendingHatcheryDefaultInstantSettings().actionId == 0


def test_hatchery_default_pending_enable_uses_staged_hatchery_after_registry_rotation(
    switchboard_bravo, governance, undy_hq, hatchery
):
    with boa.env.anchor():
        _set_hatchery_defaults_and_execute_if_staged(switchboard_bravo, governance, (False, False, False, False))
        rotated_hatchery = _deploy_hatchery_like(
            hatchery,
            undy_hq,
            (False, True, False, False),
            "rotated_hatchery_default_instant",
        )

        assert switchboard_bravo.setHatcheryDefaultInstantActionSettings(
            True, True, True, True, sender=governance.address
        )
        pending = switchboard_bravo.pendingHatcheryDefaultInstantSettings()
        assert pending.hatchery == hatchery.address

        _rotate_hatchery(undy_hq, governance, rotated_hatchery)
        assert _execute_after_timelock(switchboard_bravo, pending.actionId, governance)

        assert instant_action_settings_tuple(hatchery.defaultInstantActionSettings()) == (True, True, True, True)
        assert instant_action_settings_tuple(rotated_hatchery.defaultInstantActionSettings()) == (False, True, False, False)


def test_hatchery_default_pure_disable_applies_immediately(
    switchboard_bravo, governance, hatchery
):
    with boa.env.anchor():
        _set_hatchery_defaults_and_execute_if_staged(switchboard_bravo, governance, (True, True, True, True))

        assert switchboard_bravo.setHatcheryDefaultInstantActionSettings(
            False, True, False, True, sender=governance.address
        )

        assert instant_action_settings_tuple(hatchery.defaultInstantActionSettings()) == (False, True, False, True)
        assert switchboard_bravo.pendingHatcheryDefaultInstantSettings().actionId == 0


def test_hatchery_default_pure_disable_leaves_stale_pending_enable_and_allows_restaging(
    switchboard_bravo, governance, hatchery
):
    with boa.env.anchor():
        _set_hatchery_defaults_and_execute_if_staged(switchboard_bravo, governance, (False, False, False, False))
        assert switchboard_bravo.setHatcheryDefaultInstantActionSettings(
            True, False, False, False, sender=governance.address
        )
        aid = switchboard_bravo.pendingHatcheryDefaultInstantSettings().actionId
        assert aid != 0

        assert switchboard_bravo.setHatcheryDefaultInstantActionSettings(
            False, False, False, False, sender=governance.address
        )

        assert instant_action_settings_tuple(hatchery.defaultInstantActionSettings()) == (False, False, False, False)
        assert not switchboard_bravo.hasPendingAction(aid)
        assert switchboard_bravo.actionType(aid) == 0
        stale_pending = switchboard_bravo.pendingHatcheryDefaultInstantSettings()
        assert stale_pending.actionId == aid
        assert stale_pending.hatchery == hatchery.address
        assert _settings_tuple(stale_pending.settings) == (True, False, False, False)

        assert switchboard_bravo.setHatcheryDefaultInstantActionSettings(
            True, False, False, False, sender=governance.address
        )
        new_pending = switchboard_bravo.pendingHatcheryDefaultInstantSettings()
        assert new_pending.actionId != aid
        assert new_pending.hatchery == hatchery.address
        assert _settings_tuple(new_pending.settings) == (True, False, False, False)
        assert switchboard_bravo.hasPendingAction(new_pending.actionId)


def test_hatchery_default_mixed_change_applies_disables_and_stages_target(
    switchboard_bravo, governance, hatchery
):
    with boa.env.anchor():
        _set_hatchery_defaults_and_execute_if_staged(switchboard_bravo, governance, (True, False, True, False))

        assert switchboard_bravo.setHatcheryDefaultInstantActionSettings(
            False, True, False, True, sender=governance.address
        )

        pending = switchboard_bravo.pendingHatcheryDefaultInstantSettings()
        assert instant_action_settings_tuple(hatchery.defaultInstantActionSettings()) == (False, False, False, False)
        assert _settings_tuple(pending.settings) == (False, True, False, True)

        assert _execute_after_timelock(switchboard_bravo, pending.actionId, governance)
        assert instant_action_settings_tuple(hatchery.defaultInstantActionSettings()) == (False, True, False, True)


def test_new_wallets_during_hatchery_default_pending_window_use_current_defaults(
    switchboard_bravo, governance, hatchery, alice
):
    from contracts.core.userWallet import UserWallet

    with boa.env.anchor():
        _set_hatchery_defaults_and_execute_if_staged(switchboard_bravo, governance, (False, False, False, False))
        assert switchboard_bravo.setHatcheryDefaultInstantActionSettings(
            True, True, True, True, sender=governance.address
        )

        wallet = UserWallet.at(hatchery.createUserWallet(sender=alice))
        config = wallet.walletConfig()

        from contracts.core.userWallet import UserWalletConfig
        wallet_config = UserWalletConfig.at(config)
        assert instant_action_settings_tuple(wallet_config.instantActionSettings()) == (False, False, False, False)
        assert _pending_hatchery_default_tuple(switchboard_bravo) == (True, True, True, True)


def test_second_pending_hatchery_default_enable_reverts(switchboard_bravo, governance):
    with boa.env.anchor():
        _set_hatchery_defaults_and_execute_if_staged(switchboard_bravo, governance, (False, False, False, False))
        assert switchboard_bravo.setHatcheryDefaultInstantActionSettings(
            True, False, False, False, sender=governance.address
        )

        with boa.reverts("pending enable exists"):
            switchboard_bravo.setHatcheryDefaultInstantActionSettings(
                False, True, False, False, sender=governance.address
            )


def test_cancel_hatchery_default_pending_enable_leaves_stale_singleton_and_allows_restaging(
    switchboard_bravo, governance, hatchery
):
    with boa.env.anchor():
        _set_hatchery_defaults_and_execute_if_staged(switchboard_bravo, governance, (False, False, False, False))
        assert switchboard_bravo.setHatcheryDefaultInstantActionSettings(
            True, True, True, True, sender=governance.address
        )
        aid = switchboard_bravo.pendingHatcheryDefaultInstantSettings().actionId

        assert switchboard_bravo.cancelPendingAction(aid, sender=governance.address)

        assert instant_action_settings_tuple(hatchery.defaultInstantActionSettings()) == (False, False, False, False)
        assert not switchboard_bravo.hasPendingAction(aid)
        assert switchboard_bravo.actionType(aid) == 0
        stale_pending = switchboard_bravo.pendingHatcheryDefaultInstantSettings()
        assert stale_pending.actionId == aid
        assert stale_pending.hatchery == hatchery.address
        assert _settings_tuple(stale_pending.settings) == (True, True, True, True)

        assert switchboard_bravo.setHatcheryDefaultInstantActionSettings(
            True, False, False, False, sender=governance.address
        )
        new_pending = switchboard_bravo.pendingHatcheryDefaultInstantSettings()
        assert new_pending.actionId != aid
        assert new_pending.hatchery == hatchery.address
        assert _settings_tuple(new_pending.settings) == (True, False, False, False)
        assert switchboard_bravo.hasPendingAction(new_pending.actionId)


def test_loot_adjust_uses_staged_loot_distributor_after_registry_rotation(
    switchboard_bravo, governance, undy_hq, user_wallet, alpha_token
):
    with boa.env.anchor():
        staged_loot = _deploy_mock_loot_distributor("staged_loot_adjust")
        active_loot = _deploy_mock_loot_distributor("active_loot_adjust")
        _rotate_loot_distributor(undy_hq, governance, staged_loot)

        aid = switchboard_bravo.adjustLoot(
            user_wallet.address,
            alpha_token.address,
            123,
            sender=governance.address,
        )
        assert switchboard_bravo.pendingLootAdjustActions(aid).lootDistributor == staged_loot.address

        _rotate_loot_distributor(undy_hq, governance, active_loot)
        assert _execute_after_timelock(switchboard_bravo, aid, governance)

        assert staged_loot.numAdjustCalls() == 1
        assert staged_loot.lastAdjustUser() == user_wallet.address
        assert staged_loot.lastAdjustAsset() == alpha_token.address
        assert staged_loot.lastAdjustClaimable() == 123
        assert active_loot.numAdjustCalls() == 0


def test_set_ejection_mode_uses_staged_loot_distributor_after_registry_rotation(
    switchboard_bravo, governance, undy_hq, user_wallet
):
    with boa.env.anchor():
        staged_loot = _deploy_mock_loot_distributor("staged_loot_ejection")
        active_loot = _deploy_mock_loot_distributor("active_loot_ejection")
        _rotate_loot_distributor(undy_hq, governance, staged_loot)

        aid = switchboard_bravo.setEjectionMode(user_wallet.address, True, sender=governance.address)
        assert switchboard_bravo.pendingSetEjectionModeActions(aid).lootDistributor == staged_loot.address

        _rotate_loot_distributor(undy_hq, governance, active_loot)
        assert _execute_after_timelock(switchboard_bravo, aid, governance)

        assert staged_loot.numEjectionCalls() == 1
        assert staged_loot.lastEjectionUser() == user_wallet.address
        assert active_loot.numEjectionCalls() == 0
