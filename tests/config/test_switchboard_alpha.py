import pytest
import boa
from conf_utils import filter_logs
from constants import ZERO_ADDRESS, CONFIG_ACTION_TYPE


@pytest.fixture(scope="module")
def wallet_template_v2():
    return boa.load_partial("contracts/core/userWallet/UserWallet.vy").deploy_as_blueprint()


@pytest.fixture(scope="module")
def config_template_v2():
    return boa.load_partial("contracts/core/userWallet/UserWalletConfig.vy").deploy_as_blueprint()


#########################
# User Wallet Templates #
#########################


def test_set_user_wallet_templates_success(switchboard_alpha, governance, mission_control):
    """Test successful wallet template update through full lifecycle"""
    # Deploy new template contracts to use as v2
    user_wallet_template_v2 = boa.load_partial("contracts/core/userWallet/UserWallet.vy").deploy_as_blueprint()
    user_wallet_config_template_v2 = boa.load_partial("contracts/core/userWallet/UserWalletConfig.vy").deploy_as_blueprint()
    
    # Get initial config from MissionControl
    initial_config = mission_control.userWalletConfig()
    initial_wallet_template = initial_config.walletTemplate
    initial_config_template = initial_config.configTemplate
    
    # Step 1: Initiate template change
    aid = switchboard_alpha.setUserWalletTemplates(
        user_wallet_template_v2.address, 
        user_wallet_config_template_v2.address,
        sender=governance.address
    )
    
    # Step 2: Verify event was emitted
    logs = filter_logs(switchboard_alpha, "PendingUserWalletTemplatesChange")
    assert len(logs) == 1
    assert logs[0].walletTemplate == user_wallet_template_v2.address
    assert logs[0].configTemplate == user_wallet_config_template_v2.address
    assert logs[0].actionId == aid
    # Confirmation block should be current block + timelock
    expected_confirmation_block = boa.env.evm.patch.block_number + switchboard_alpha.actionTimeLock()
    assert logs[0].confirmationBlock == expected_confirmation_block
    
    # Step 3: Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.USER_WALLET_TEMPLATES
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.walletTemplate == user_wallet_template_v2.address
    assert pending_config.configTemplate == user_wallet_config_template_v2.address
    
    # Verify the action confirmation block matches what we expect
    assert switchboard_alpha.getActionConfirmationBlock(aid) == expected_confirmation_block
    
    # Step 4: Try to execute before timelock - should fail silently
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Verify no state change
    current_config = mission_control.userWalletConfig()
    assert current_config.walletTemplate == initial_wallet_template
    assert current_config.configTemplate == initial_config_template
    
    # Step 5: Time travel to one block before timelock - should still fail
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock() - 1)
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Travel one more block to reach exact timelock
    boa.env.time_travel(blocks=1)
    
    # Step 6: Now execution should succeed
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Step 7: Verify execution event
    exec_logs = filter_logs(switchboard_alpha, "UserWalletTemplatesSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].walletTemplate == user_wallet_template_v2.address
    assert exec_logs[0].configTemplate == user_wallet_config_template_v2.address
    
    # Step 8: Verify state changes in MissionControl
    updated_config = mission_control.userWalletConfig()
    assert updated_config.walletTemplate == user_wallet_template_v2.address
    assert updated_config.configTemplate == user_wallet_config_template_v2.address
    
    # Verify other config fields remain unchanged
    assert updated_config.trialAmount == initial_config.trialAmount
    assert updated_config.numUserWalletsAllowed == initial_config.numUserWalletsAllowed
    
    # Step 9: Verify action is cleared
    assert switchboard_alpha.actionType(aid) == 0  # empty(ActionType)
    # Note: pendingUserWalletConfig mapping is not cleared after execution


def test_set_user_wallet_templates_non_governance_reverts(switchboard_alpha, alice, wallet_template_v2, config_template_v2):
    """Test that non-governance cannot set wallet templates"""
    
    # Try to set templates as non-governance user
    with boa.reverts("no perms"):
        switchboard_alpha.setUserWalletTemplates(
            wallet_template_v2.address,
            config_template_v2.address,
            sender=alice
        )


def test_set_user_wallet_templates_invalid_addresses_revert(switchboard_alpha, governance, user_wallet_template, user_wallet_config_template, alice, bob):
    """Test that invalid template addresses revert with 'invalid user wallet templates' error"""
    
    # Test 1: Zero address for wallet template
    with boa.reverts("invalid user wallet templates"):
        switchboard_alpha.setUserWalletTemplates(
            ZERO_ADDRESS,
            user_wallet_config_template.address,
            sender=governance.address
        )
    
    # Test 2: Zero address for config template
    with boa.reverts("invalid user wallet templates"):
        switchboard_alpha.setUserWalletTemplates(
            user_wallet_template.address,
            ZERO_ADDRESS,
            sender=governance.address
        )
    
    # Test 3: Both zero addresses
    with boa.reverts("invalid user wallet templates"):
        switchboard_alpha.setUserWalletTemplates(
            ZERO_ADDRESS,
            ZERO_ADDRESS,
            sender=governance.address
        )
    
    # Test 4: EOA address for wallet template (alice is not a contract)
    with boa.reverts("invalid user wallet templates"):
        switchboard_alpha.setUserWalletTemplates(
            alice,
            user_wallet_config_template.address,
            sender=governance.address
        )
    
    # Test 5: EOA address for config template (bob is not a contract)
    with boa.reverts("invalid user wallet templates"):
        switchboard_alpha.setUserWalletTemplates(
            user_wallet_template.address,
            bob,
            sender=governance.address
        )
    
    # Test 6: Both EOA addresses
    with boa.reverts("invalid user wallet templates"):
        switchboard_alpha.setUserWalletTemplates(
            alice,
            bob,
            sender=governance.address
        )


def test_cancel_pending_wallet_template_update(switchboard_alpha, governance, mission_control, wallet_template_v2, config_template_v2):
    """Test canceling a pending wallet template update"""
    
    # Get initial state
    initial_config = mission_control.userWalletConfig()
    
    # Initiate template change
    aid = switchboard_alpha.setUserWalletTemplates(
        wallet_template_v2.address,
        config_template_v2.address,
        sender=governance.address
    )
    
    # Verify pending action exists
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.USER_WALLET_TEMPLATES
    
    # Cancel the action
    result = switchboard_alpha.cancelPendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify action is cleared
    assert switchboard_alpha.actionType(aid) == 0
    # Note: pendingUserWalletConfig mapping is not cleared, only actionType is cleared
    
    # Time travel and try to execute - should fail
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Verify config remains unchanged
    final_config = mission_control.userWalletConfig()
    assert final_config.walletTemplate == initial_config.walletTemplate
    assert final_config.configTemplate == initial_config.configTemplate


def test_cancel_pending_action_non_governance_reverts(switchboard_alpha, governance, alice, wallet_template_v2, config_template_v2):
    """Test that non-governance cannot cancel pending actions"""
    
    # Initiate as governance
    aid = switchboard_alpha.setUserWalletTemplates(
        wallet_template_v2.address,
        config_template_v2.address,
        sender=governance.address
    )
    
    # Try to cancel as non-governance
    with boa.reverts("no perms"):
        switchboard_alpha.cancelPendingAction(aid, sender=alice)


def test_execute_expired_wallet_template_update(switchboard_alpha, governance, mission_control, wallet_template_v2, config_template_v2):
    """Test that expired actions cannot be executed and are automatically cancelled"""
    
    # Initiate template change
    aid = switchboard_alpha.setUserWalletTemplates(
        wallet_template_v2.address,
        config_template_v2.address,
        sender=governance.address
    )
    
    # Verify pending action exists
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.USER_WALLET_TEMPLATES
    
    # Travel to exactly the last valid block (timelock + expiration - 1)
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock() + switchboard_alpha.expiration() - 1)
    
    # Should still be executable at the last valid block
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Create another pending action to test expiration
    aid2 = switchboard_alpha.setUserWalletTemplates(
        wallet_template_v2.address,
        config_template_v2.address,
        sender=governance.address
    )
    
    # Travel past expiration (timelock + expiration)
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock() + switchboard_alpha.expiration())
    
    # Execute should fail silently and cancel the action
    result = switchboard_alpha.executePendingAction(aid2, sender=governance.address)
    assert result == False
    
    # Verify action was cancelled
    assert switchboard_alpha.actionType(aid2) == 0
    # Note: pendingUserWalletConfig mapping is not cleared, only actionType is cleared
    
    # Verify config was updated by first action but not the expired second one
    final_config = mission_control.userWalletConfig()
    assert final_config.walletTemplate == wallet_template_v2.address
    assert final_config.configTemplate == config_template_v2.address


def test_execute_pending_action_non_governance_reverts(switchboard_alpha, governance, alice, wallet_template_v2, config_template_v2):
    """Test that non-governance cannot execute pending actions"""
    
    # Initiate as governance
    aid = switchboard_alpha.setUserWalletTemplates(
        wallet_template_v2.address,
        config_template_v2.address,
        sender=governance.address
    )
    
    # Time travel
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    
    # Try to execute as non-governance
    with boa.reverts("no perms"):
        switchboard_alpha.executePendingAction(aid, sender=alice)


def test_multiple_pending_wallet_template_updates(switchboard_alpha, governance, wallet_template_v2, config_template_v2):
    """Test handling multiple pending updates"""
    # Deploy multiple template versions
    wallet_v3 = boa.load_partial("contracts/core/userWallet/UserWallet.vy").deploy_as_blueprint()
    config_v3 = boa.load_partial("contracts/core/userWallet/UserWalletConfig.vy").deploy_as_blueprint()
    
    # Create first pending update
    aid1 = switchboard_alpha.setUserWalletTemplates(
        wallet_template_v2.address,
        config_template_v2.address,
        sender=governance.address
    )
    
    # Create second pending update
    aid2 = switchboard_alpha.setUserWalletTemplates(
        wallet_v3.address,
        config_v3.address,
        sender=governance.address
    )
    
    # Verify both are pending with different action IDs
    assert aid1 != aid2
    assert switchboard_alpha.actionType(aid1) == 1
    assert switchboard_alpha.actionType(aid2) == 1
    
    # Verify different pending configs
    pending1 = switchboard_alpha.pendingUserWalletConfig(aid1)
    pending2 = switchboard_alpha.pendingUserWalletConfig(aid2)
    
    assert pending1.walletTemplate == wallet_template_v2.address
    assert pending2.walletTemplate == wallet_v3.address


###############
# Trial Funds #
###############


def test_set_trial_funds_success(switchboard_alpha, governance, mission_control, alpha_token):
    """Test successful trial funds update through full lifecycle"""
    # Get initial config from MissionControl
    initial_config = mission_control.userWalletConfig()
    initial_trial_asset = initial_config.trialAsset
    initial_trial_amount = initial_config.trialAmount
    
    # New trial funds values
    new_trial_asset = alpha_token.address
    new_trial_amount = 100 * 10**18  # 100 ALPHA tokens (assuming 18 decimals)
    
    # Step 1: Initiate trial funds change
    aid = switchboard_alpha.setTrialFunds(
        new_trial_asset,
        new_trial_amount,
        sender=governance.address
    )
    
    # Step 2: Verify event was emitted
    logs = filter_logs(switchboard_alpha, "PendingTrialFundsChange")
    assert len(logs) == 1
    assert logs[0].trialAsset == new_trial_asset
    assert logs[0].trialAmount == new_trial_amount
    assert logs[0].actionId == aid
    # Confirmation block should be current block + timelock
    expected_confirmation_block = boa.env.evm.patch.block_number + switchboard_alpha.actionTimeLock()
    assert logs[0].confirmationBlock == expected_confirmation_block
    
    # Step 3: Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.TRIAL_FUNDS
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.trialAsset == new_trial_asset
    assert pending_config.trialAmount == new_trial_amount
    
    # Verify the action confirmation block matches what we expect
    assert switchboard_alpha.getActionConfirmationBlock(aid) == expected_confirmation_block
    
    # Step 4: Try to execute before timelock - should fail silently
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Verify no state change
    current_config = mission_control.userWalletConfig()
    assert current_config.trialAsset == initial_trial_asset
    assert current_config.trialAmount == initial_trial_amount
    
    # Step 5: Time travel to one block before timelock - should still fail
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock() - 1)
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Travel one more block to reach exact timelock
    boa.env.time_travel(blocks=1)
    
    # Step 6: Now execution should succeed
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Step 7: Verify execution event
    exec_logs = filter_logs(switchboard_alpha, "TrialFundsSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].trialAsset == new_trial_asset
    assert exec_logs[0].trialAmount == new_trial_amount
    
    # Step 8: Verify state changes in MissionControl
    updated_config = mission_control.userWalletConfig()
    assert updated_config.trialAsset == new_trial_asset
    assert updated_config.trialAmount == new_trial_amount
    
    # Verify other config fields remain unchanged
    assert updated_config.walletTemplate == initial_config.walletTemplate
    assert updated_config.configTemplate == initial_config.configTemplate
    
    # Step 9: Verify action is cleared
    assert switchboard_alpha.actionType(aid) == 0  # empty(ActionType)
    # Note: pendingUserWalletConfig mapping is not cleared after execution


def test_set_trial_funds_zero_values_allowed(switchboard_alpha, governance, mission_control):
    """Test that zero address and zero amount are allowed for trial funds"""
    # Test with zero address and zero amount - should succeed
    aid = switchboard_alpha.setTrialFunds(
        ZERO_ADDRESS,
        0,
        sender=governance.address
    )
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.TRIAL_FUNDS
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.trialAsset == ZERO_ADDRESS
    assert pending_config.trialAmount == 0
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify state changes
    updated_config = mission_control.userWalletConfig()
    assert updated_config.trialAsset == ZERO_ADDRESS
    assert updated_config.trialAmount == 0


def test_set_trial_funds_non_governance_reverts(switchboard_alpha, alice, alpha_token):
    """Test that non-governance cannot set trial funds"""
    with boa.reverts("no perms"):
        switchboard_alpha.setTrialFunds(
            alpha_token.address,
            100 * 10**18,
            sender=alice
        )


def test_set_trial_funds_mixed_with_template_updates(switchboard_alpha, governance, mission_control, wallet_template_v2, config_template_v2, alpha_token):
    """Test that trial funds and template updates can coexist as separate pending actions"""
    # Create pending template update
    aid1 = switchboard_alpha.setUserWalletTemplates(
        wallet_template_v2.address,
        config_template_v2.address,
        sender=governance.address
    )
    
    # Create pending trial funds update
    aid2 = switchboard_alpha.setTrialFunds(
        alpha_token.address,
        50 * 10**18,  # 50 ALPHA tokens
        sender=governance.address
    )
    
    # Verify both are pending with different action IDs and types
    assert aid1 != aid2
    assert switchboard_alpha.actionType(aid1) == CONFIG_ACTION_TYPE.USER_WALLET_TEMPLATES
    assert switchboard_alpha.actionType(aid2) == CONFIG_ACTION_TYPE.TRIAL_FUNDS
    
    # Time travel and execute trial funds first
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid2, sender=governance.address)
    assert result == True
    
    # Verify trial funds updated but templates not yet
    config = mission_control.userWalletConfig()
    assert config.trialAsset == alpha_token.address
    assert config.trialAmount == 50 * 10**18
    assert config.walletTemplate != wallet_template_v2.address
    
    # Execute template update
    result = switchboard_alpha.executePendingAction(aid1, sender=governance.address)
    assert result == True
    
    # Verify both updates applied
    final_config = mission_control.userWalletConfig()
    assert final_config.walletTemplate == wallet_template_v2.address
    assert final_config.configTemplate == config_template_v2.address
    assert final_config.trialAsset == alpha_token.address
    assert final_config.trialAmount == 50 * 10**18


##########################
# Wallet Creation Limits #
##########################


def test_set_wallet_creation_limits_success(switchboard_alpha, governance, mission_control):
    """Test successful wallet creation limits update through full lifecycle"""
    # Get initial config from MissionControl
    initial_config = mission_control.userWalletConfig()
    initial_num_wallets_allowed = initial_config.numUserWalletsAllowed
    initial_enforce_whitelist = initial_config.enforceCreatorWhitelist
    
    # New wallet creation limits values
    new_num_wallets_allowed = 100
    new_enforce_whitelist = True
    
    # Step 1: Initiate wallet creation limits change
    aid = switchboard_alpha.setWalletCreationLimits(
        new_num_wallets_allowed,
        new_enforce_whitelist,
        sender=governance.address
    )
    
    # Step 2: Verify event was emitted
    logs = filter_logs(switchboard_alpha, "PendingWalletCreationLimitsChange")
    assert len(logs) == 1
    assert logs[0].numUserWalletsAllowed == new_num_wallets_allowed
    assert logs[0].enforceCreatorWhitelist == new_enforce_whitelist
    assert logs[0].actionId == aid
    # Confirmation block should be current block + timelock
    expected_confirmation_block = boa.env.evm.patch.block_number + switchboard_alpha.actionTimeLock()
    assert logs[0].confirmationBlock == expected_confirmation_block
    
    # Step 3: Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.WALLET_CREATION_LIMITS
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.numUserWalletsAllowed == new_num_wallets_allowed
    assert pending_config.enforceCreatorWhitelist == new_enforce_whitelist
    
    # Verify the action confirmation block matches what we expect
    assert switchboard_alpha.getActionConfirmationBlock(aid) == expected_confirmation_block
    
    # Step 4: Try to execute before timelock - should fail silently
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Verify no state change
    current_config = mission_control.userWalletConfig()
    assert current_config.numUserWalletsAllowed == initial_num_wallets_allowed
    assert current_config.enforceCreatorWhitelist == initial_enforce_whitelist
    
    # Step 5: Time travel to one block before timelock - should still fail
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock() - 1)
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Travel one more block to reach exact timelock
    boa.env.time_travel(blocks=1)
    
    # Step 6: Now execution should succeed
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Step 7: Verify execution event
    exec_logs = filter_logs(switchboard_alpha, "WalletCreationLimitsSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].numUserWalletsAllowed == new_num_wallets_allowed
    assert exec_logs[0].enforceCreatorWhitelist == new_enforce_whitelist
    
    # Step 8: Verify state changes in MissionControl
    updated_config = mission_control.userWalletConfig()
    assert updated_config.numUserWalletsAllowed == new_num_wallets_allowed
    assert updated_config.enforceCreatorWhitelist == new_enforce_whitelist
    
    # Verify other config fields remain unchanged
    assert updated_config.walletTemplate == initial_config.walletTemplate
    assert updated_config.configTemplate == initial_config.configTemplate
    assert updated_config.trialAsset == initial_config.trialAsset
    assert updated_config.trialAmount == initial_config.trialAmount
    
    # Step 9: Verify action is cleared
    assert switchboard_alpha.actionType(aid) == 0  # empty(ActionType)
    # Note: pendingUserWalletConfig mapping is not cleared after execution


def test_set_wallet_creation_limits_extreme_values(switchboard_alpha, governance, mission_control):
    """Test that large (but not max) values are allowed for wallet creation limits"""
    # Test with large value (max uint256 - 1) and false
    large_value = 2**256 - 2  # max uint256 - 1
    aid = switchboard_alpha.setWalletCreationLimits(
        large_value,
        False,
        sender=governance.address
    )
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.WALLET_CREATION_LIMITS
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.numUserWalletsAllowed == large_value
    assert pending_config.enforceCreatorWhitelist == False
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify state changes
    updated_config = mission_control.userWalletConfig()
    assert updated_config.numUserWalletsAllowed == large_value
    assert updated_config.enforceCreatorWhitelist == False


def test_set_wallet_creation_limits_invalid_values_revert(switchboard_alpha, governance):
    """Test that invalid values (0 and max_value) revert"""
    # Test with 0 - should revert
    with boa.reverts("invalid num user wallets allowed"):
        switchboard_alpha.setWalletCreationLimits(
            0,
            True,
            sender=governance.address
        )
    
    # Test with max_value(uint256) - should revert
    with boa.reverts("invalid num user wallets allowed"):
        switchboard_alpha.setWalletCreationLimits(
            2**256 - 1,  # max uint256
            False,
            sender=governance.address
        )


def test_set_wallet_creation_limits_non_governance_reverts(switchboard_alpha, alice):
    """Test that non-governance cannot set wallet creation limits"""
    with boa.reverts("no perms"):
        switchboard_alpha.setWalletCreationLimits(
            100,
            True,
            sender=alice
        )


def test_set_wallet_creation_limits_mixed_with_other_updates(switchboard_alpha, governance, mission_control, wallet_template_v2, config_template_v2, alpha_token):
    """Test that wallet creation limits can coexist with other pending actions"""
    # Create pending template update
    aid1 = switchboard_alpha.setUserWalletTemplates(
        wallet_template_v2.address,
        config_template_v2.address,
        sender=governance.address
    )
    
    # Create pending trial funds update
    aid2 = switchboard_alpha.setTrialFunds(
        alpha_token.address,
        25 * 10**18,
        sender=governance.address
    )
    
    # Create pending wallet creation limits update
    aid3 = switchboard_alpha.setWalletCreationLimits(
        50,
        True,
        sender=governance.address
    )
    
    # Verify all are pending with different action IDs and types
    assert aid1 != aid2 != aid3
    assert switchboard_alpha.actionType(aid1) == CONFIG_ACTION_TYPE.USER_WALLET_TEMPLATES
    assert switchboard_alpha.actionType(aid2) == CONFIG_ACTION_TYPE.TRIAL_FUNDS
    assert switchboard_alpha.actionType(aid3) == CONFIG_ACTION_TYPE.WALLET_CREATION_LIMITS
    
    # Time travel and execute wallet creation limits first
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid3, sender=governance.address)
    assert result == True
    
    # Verify only wallet creation limits updated
    config = mission_control.userWalletConfig()
    assert config.numUserWalletsAllowed == 50
    assert config.enforceCreatorWhitelist == True
    assert config.walletTemplate != wallet_template_v2.address
    assert config.trialAsset != alpha_token.address
    
    # Execute other updates
    assert switchboard_alpha.executePendingAction(aid1, sender=governance.address) == True
    assert switchboard_alpha.executePendingAction(aid2, sender=governance.address) == True
    
    # Verify all updates applied
    final_config = mission_control.userWalletConfig()
    assert final_config.walletTemplate == wallet_template_v2.address
    assert final_config.configTemplate == config_template_v2.address
    assert final_config.trialAsset == alpha_token.address
    assert final_config.trialAmount == 25 * 10**18
    assert final_config.numUserWalletsAllowed == 50
    assert final_config.enforceCreatorWhitelist == True


##############################
# Key Action Timelock Bounds #
##############################


def test_set_key_action_timelock_bounds_success(switchboard_alpha, governance, mission_control):
    """Test successful key action timelock bounds update through full lifecycle"""
    # Get initial config from MissionControl
    initial_config = mission_control.userWalletConfig()
    initial_min_timelock = initial_config.minKeyActionTimeLock
    initial_max_timelock = initial_config.maxKeyActionTimeLock
    
    # New timelock bounds values (e.g., 1 hour to 1 week in blocks)
    new_min_timelock = 3600  # ~1 hour in blocks
    new_max_timelock = 604800  # ~1 week in blocks
    
    # Step 1: Initiate key action timelock bounds change
    aid = switchboard_alpha.setKeyActionTimelockBounds(
        new_min_timelock,
        new_max_timelock,
        sender=governance.address
    )
    
    # Step 2: Verify event was emitted
    logs = filter_logs(switchboard_alpha, "PendingKeyActionTimelockBoundsChange")
    assert len(logs) == 1
    assert logs[0].minKeyActionTimeLock == new_min_timelock
    assert logs[0].maxKeyActionTimeLock == new_max_timelock
    assert logs[0].actionId == aid
    # Confirmation block should be current block + timelock
    expected_confirmation_block = boa.env.evm.patch.block_number + switchboard_alpha.actionTimeLock()
    assert logs[0].confirmationBlock == expected_confirmation_block
    
    # Step 3: Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.KEY_ACTION_TIMELOCK_BOUNDS
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.minKeyActionTimeLock == new_min_timelock
    assert pending_config.maxKeyActionTimeLock == new_max_timelock
    
    # Verify the action confirmation block matches what we expect
    assert switchboard_alpha.getActionConfirmationBlock(aid) == expected_confirmation_block
    
    # Step 4: Try to execute before timelock - should fail silently
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Verify no state change
    current_config = mission_control.userWalletConfig()
    assert current_config.minKeyActionTimeLock == initial_min_timelock
    assert current_config.maxKeyActionTimeLock == initial_max_timelock
    
    # Step 5: Time travel to one block before timelock - should still fail
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock() - 1)
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Travel one more block to reach exact timelock
    boa.env.time_travel(blocks=1)
    
    # Step 6: Now execution should succeed
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Step 7: Verify execution event
    exec_logs = filter_logs(switchboard_alpha, "KeyActionTimelockBoundsSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].minKeyActionTimeLock == new_min_timelock
    assert exec_logs[0].maxKeyActionTimeLock == new_max_timelock
    
    # Step 8: Verify state changes in MissionControl
    updated_config = mission_control.userWalletConfig()
    assert updated_config.minKeyActionTimeLock == new_min_timelock
    assert updated_config.maxKeyActionTimeLock == new_max_timelock
    
    # Verify other config fields remain unchanged
    assert updated_config.walletTemplate == initial_config.walletTemplate
    assert updated_config.configTemplate == initial_config.configTemplate
    assert updated_config.trialAsset == initial_config.trialAsset
    assert updated_config.trialAmount == initial_config.trialAmount
    
    # Step 9: Verify action is cleared
    assert switchboard_alpha.actionType(aid) == 0  # empty(ActionType)
    # Note: pendingUserWalletConfig mapping is not cleared after execution


def test_set_key_action_timelock_bounds_invalid_values_revert(switchboard_alpha, governance):
    """Test that invalid values revert with proper error message"""
    # Test 1: min = 0
    with boa.reverts("invalid key action timelock bounds"):
        switchboard_alpha.setKeyActionTimelockBounds(
            0,
            1000,
            sender=governance.address
        )
    
    # Test 2: max = 0
    with boa.reverts("invalid key action timelock bounds"):
        switchboard_alpha.setKeyActionTimelockBounds(
            1000,
            0,
            sender=governance.address
        )
    
    # Test 3: min = max_value(uint256)
    with boa.reverts("invalid key action timelock bounds"):
        switchboard_alpha.setKeyActionTimelockBounds(
            2**256 - 1,
            1000,
            sender=governance.address
        )
    
    # Test 4: max = max_value(uint256)
    with boa.reverts("invalid key action timelock bounds"):
        switchboard_alpha.setKeyActionTimelockBounds(
            1000,
            2**256 - 1,
            sender=governance.address
        )
    
    # Test 5: min >= max
    with boa.reverts("invalid key action timelock bounds"):
        switchboard_alpha.setKeyActionTimelockBounds(
            1000,
            1000,  # min == max
            sender=governance.address
        )
    
    # Test 6: min > max
    with boa.reverts("invalid key action timelock bounds"):
        switchboard_alpha.setKeyActionTimelockBounds(
            2000,
            1000,  # min > max
            sender=governance.address
        )


def test_set_key_action_timelock_bounds_non_governance_reverts(switchboard_alpha, alice):
    """Test that non-governance cannot set key action timelock bounds"""
    with boa.reverts("no perms"):
        switchboard_alpha.setKeyActionTimelockBounds(
            3600,
            604800,
            sender=alice
        )


def test_set_key_action_timelock_bounds_edge_cases(switchboard_alpha, governance, mission_control):
    """Test edge cases for key action timelock bounds"""
    # Test with min = 1 and max = 2 (smallest valid range)
    aid = switchboard_alpha.setKeyActionTimelockBounds(
        1,
        2,
        sender=governance.address
    )
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.KEY_ACTION_TIMELOCK_BOUNDS
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.minKeyActionTimeLock == 1
    assert pending_config.maxKeyActionTimeLock == 2
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify state changes
    updated_config = mission_control.userWalletConfig()
    assert updated_config.minKeyActionTimeLock == 1
    assert updated_config.maxKeyActionTimeLock == 2
    
    # Test with large values (but not max)
    large_min = 2**255
    large_max = 2**256 - 2
    aid2 = switchboard_alpha.setKeyActionTimelockBounds(
        large_min,
        large_max,
        sender=governance.address
    )
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid2, sender=governance.address)
    assert result == True
    
    # Verify state changes
    final_config = mission_control.userWalletConfig()
    assert final_config.minKeyActionTimeLock == large_min
    assert final_config.maxKeyActionTimeLock == large_max


########################
# Default Stale Blocks #
########################


def test_set_default_stale_blocks_success(switchboard_alpha, governance, mission_control):
    """Test successful default stale blocks update through full lifecycle"""
    # Get initial config from MissionControl
    initial_config = mission_control.userWalletConfig()
    initial_stale_blocks = initial_config.defaultStaleBlocks
    
    # New default stale blocks value (e.g., 6 hours in blocks)
    new_stale_blocks = 21600  # ~6 hours in blocks
    
    # Step 1: Initiate default stale blocks change
    aid = switchboard_alpha.setDefaultStaleBlocks(
        new_stale_blocks,
        sender=governance.address
    )
    
    # Step 2: Verify event was emitted
    logs = filter_logs(switchboard_alpha, "PendingDefaultStaleBlocksChange")
    assert len(logs) == 1
    assert logs[0].defaultStaleBlocks == new_stale_blocks
    assert logs[0].actionId == aid
    # Confirmation block should be current block + timelock
    expected_confirmation_block = boa.env.evm.patch.block_number + switchboard_alpha.actionTimeLock()
    assert logs[0].confirmationBlock == expected_confirmation_block
    
    # Step 3: Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.DEFAULT_STALE_BLOCKS
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.defaultStaleBlocks == new_stale_blocks
    
    # Verify the action confirmation block matches what we expect
    assert switchboard_alpha.getActionConfirmationBlock(aid) == expected_confirmation_block
    
    # Step 4: Try to execute before timelock - should fail silently
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Verify no state change
    current_config = mission_control.userWalletConfig()
    assert current_config.defaultStaleBlocks == initial_stale_blocks
    
    # Step 5: Time travel to one block before timelock - should still fail
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock() - 1)
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Travel one more block to reach exact timelock
    boa.env.time_travel(blocks=1)
    
    # Step 6: Now execution should succeed
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Step 7: Verify execution event
    exec_logs = filter_logs(switchboard_alpha, "DefaultStaleBlocksSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].defaultStaleBlocks == new_stale_blocks
    
    # Step 8: Verify state changes in MissionControl
    updated_config = mission_control.userWalletConfig()
    assert updated_config.defaultStaleBlocks == new_stale_blocks
    
    # Verify other config fields remain unchanged
    assert updated_config.walletTemplate == initial_config.walletTemplate
    assert updated_config.configTemplate == initial_config.configTemplate
    assert updated_config.trialAsset == initial_config.trialAsset
    assert updated_config.trialAmount == initial_config.trialAmount
    assert updated_config.numUserWalletsAllowed == initial_config.numUserWalletsAllowed
    assert updated_config.minKeyActionTimeLock == initial_config.minKeyActionTimeLock
    assert updated_config.maxKeyActionTimeLock == initial_config.maxKeyActionTimeLock
    
    # Step 9: Verify action is cleared
    assert switchboard_alpha.actionType(aid) == 0  # empty(ActionType)
    # Note: pendingUserWalletConfig mapping is not cleared after execution


def test_set_default_stale_blocks_invalid_values_revert(switchboard_alpha, governance):
    """Test that invalid values revert with proper error message"""
    # Test 1: defaultStaleBlocks = 0
    with boa.reverts("invalid default stale blocks"):
        switchboard_alpha.setDefaultStaleBlocks(
            0,
            sender=governance.address
        )
    
    # Test 2: defaultStaleBlocks = max_value(uint256)
    with boa.reverts("invalid default stale blocks"):
        switchboard_alpha.setDefaultStaleBlocks(
            2**256 - 1,
            sender=governance.address
        )


def test_set_default_stale_blocks_non_governance_reverts(switchboard_alpha, alice):
    """Test that non-governance cannot set default stale blocks"""
    with boa.reverts("no perms"):
        switchboard_alpha.setDefaultStaleBlocks(
            21600,
            sender=alice
        )


def test_set_default_stale_blocks_edge_cases(switchboard_alpha, governance, mission_control):
    """Test edge cases for default stale blocks"""
    # Test with minimum valid value (1)
    aid = switchboard_alpha.setDefaultStaleBlocks(
        1,
        sender=governance.address
    )
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.DEFAULT_STALE_BLOCKS
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.defaultStaleBlocks == 1
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify state changes
    updated_config = mission_control.userWalletConfig()
    assert updated_config.defaultStaleBlocks == 1
    
    # Test with large value (but not max)
    large_value = 2**256 - 2
    aid2 = switchboard_alpha.setDefaultStaleBlocks(
        large_value,
        sender=governance.address
    )
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid2, sender=governance.address)
    assert result == True
    
    # Verify state changes
    final_config = mission_control.userWalletConfig()
    assert final_config.defaultStaleBlocks == large_value


###########
# TX Fees #
###########


def test_set_tx_fees_success(switchboard_alpha, governance, mission_control):
    """Test successful tx fees update through full lifecycle"""
    # Get initial config from MissionControl
    initial_config = mission_control.userWalletConfig()
    initial_swap_fee = initial_config.txFees.swapFee
    initial_stable_swap_fee = initial_config.txFees.stableSwapFee
    initial_rewards_fee = initial_config.txFees.rewardsFee
    
    # New tx fees values (in basis points - 100 = 1%)
    new_swap_fee = 30  # 0.3%
    new_stable_swap_fee = 10  # 0.1%
    new_rewards_fee = 50  # 0.5%
    
    # Step 1: Initiate tx fees change
    aid = switchboard_alpha.setTxFees(
        new_swap_fee,
        new_stable_swap_fee,
        new_rewards_fee,
        sender=governance.address
    )
    
    # Step 2: Verify event was emitted
    logs = filter_logs(switchboard_alpha, "PendingTxFeesChange")
    assert len(logs) == 1
    assert logs[0].swapFee == new_swap_fee
    assert logs[0].stableSwapFee == new_stable_swap_fee
    assert logs[0].rewardsFee == new_rewards_fee
    assert logs[0].actionId == aid
    # Confirmation block should be current block + timelock
    expected_confirmation_block = boa.env.evm.patch.block_number + switchboard_alpha.actionTimeLock()
    assert logs[0].confirmationBlock == expected_confirmation_block
    
    # Step 3: Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.TX_FEES
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.txFees.swapFee == new_swap_fee
    assert pending_config.txFees.stableSwapFee == new_stable_swap_fee
    assert pending_config.txFees.rewardsFee == new_rewards_fee
    
    # Verify the action confirmation block matches what we expect
    assert switchboard_alpha.getActionConfirmationBlock(aid) == expected_confirmation_block
    
    # Step 4: Try to execute before timelock - should fail silently
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Verify no state change
    current_config = mission_control.userWalletConfig()
    assert current_config.txFees.swapFee == initial_swap_fee
    assert current_config.txFees.stableSwapFee == initial_stable_swap_fee
    assert current_config.txFees.rewardsFee == initial_rewards_fee
    
    # Step 5: Time travel to one block before timelock - should still fail
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock() - 1)
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Travel one more block to reach exact timelock
    boa.env.time_travel(blocks=1)
    
    # Step 6: Now execution should succeed
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Step 7: Verify execution event
    exec_logs = filter_logs(switchboard_alpha, "TxFeesSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].swapFee == new_swap_fee
    assert exec_logs[0].stableSwapFee == new_stable_swap_fee
    assert exec_logs[0].rewardsFee == new_rewards_fee
    
    # Step 8: Verify state changes in MissionControl
    updated_config = mission_control.userWalletConfig()
    assert updated_config.txFees.swapFee == new_swap_fee
    assert updated_config.txFees.stableSwapFee == new_stable_swap_fee
    assert updated_config.txFees.rewardsFee == new_rewards_fee
    
    # Verify other config fields remain unchanged
    assert updated_config.walletTemplate == initial_config.walletTemplate
    assert updated_config.configTemplate == initial_config.configTemplate
    assert updated_config.trialAsset == initial_config.trialAsset
    assert updated_config.trialAmount == initial_config.trialAmount
    
    # Step 9: Verify action is cleared
    assert switchboard_alpha.actionType(aid) == 0  # empty(ActionType)
    # Note: pendingUserWalletConfig mapping is not cleared after execution


def test_set_tx_fees_invalid_values_revert(switchboard_alpha, governance):
    """Test that invalid values (above 100%) revert with proper error message"""
    # Test 1: swapFee > 100%
    with boa.reverts("invalid tx fees"):
        switchboard_alpha.setTxFees(
            10001,  # > 100%
            100,
            100,
            sender=governance.address
        )
    
    # Test 2: stableSwapFee > 100%
    with boa.reverts("invalid tx fees"):
        switchboard_alpha.setTxFees(
            100,
            10001,  # > 100%
            100,
            sender=governance.address
        )
    
    # Test 3: rewardsFee > 100%
    with boa.reverts("invalid tx fees"):
        switchboard_alpha.setTxFees(
            100,
            100,
            10001,  # > 100%
            sender=governance.address
        )
    
    # Test 4: All fees > 100%
    with boa.reverts("invalid tx fees"):
        switchboard_alpha.setTxFees(
            20000,  # 200%
            15000,  # 150%
            25000,  # 250%
            sender=governance.address
        )


def test_set_tx_fees_zero_values_allowed(switchboard_alpha, governance, mission_control):
    """Test that zero fee values are allowed"""
    # Set all fees to 0
    aid = switchboard_alpha.setTxFees(
        0,
        0,
        0,
        sender=governance.address
    )
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.TX_FEES
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.txFees.swapFee == 0
    assert pending_config.txFees.stableSwapFee == 0
    assert pending_config.txFees.rewardsFee == 0
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify state changes
    updated_config = mission_control.userWalletConfig()
    assert updated_config.txFees.swapFee == 0
    assert updated_config.txFees.stableSwapFee == 0
    assert updated_config.txFees.rewardsFee == 0


def test_set_tx_fees_non_governance_reverts(switchboard_alpha, alice):
    """Test that non-governance cannot set tx fees"""
    with boa.reverts("no perms"):
        switchboard_alpha.setTxFees(
            30,
            10,
            50,
            sender=alice
        )


def test_set_tx_fees_maximum_allowed_values(switchboard_alpha, governance, mission_control):
    """Test maximum allowed fee values (100% = 10000 basis points)"""
    # Set all fees to maximum allowed (100%)
    aid = switchboard_alpha.setTxFees(
        10000,  # 100%
        10000,  # 100%
        10000,  # 100%
        sender=governance.address
    )
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.TX_FEES
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.txFees.swapFee == 10000
    assert pending_config.txFees.stableSwapFee == 10000
    assert pending_config.txFees.rewardsFee == 10000
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify state changes
    updated_config = mission_control.userWalletConfig()
    assert updated_config.txFees.swapFee == 10000
    assert updated_config.txFees.stableSwapFee == 10000
    assert updated_config.txFees.rewardsFee == 10000


########################
# Ambassador Rev Share #
########################


def test_set_ambassador_rev_share_success(switchboard_alpha, governance, mission_control):
    """Test successful ambassador rev share update through full lifecycle"""
    # Get initial config from MissionControl
    initial_config = mission_control.userWalletConfig()
    initial_swap_ratio = initial_config.ambassadorRevShare.swapRatio
    initial_rewards_ratio = initial_config.ambassadorRevShare.rewardsRatio
    initial_yield_ratio = initial_config.ambassadorRevShare.yieldRatio
    
    # New ambassador rev share values (in basis points - 100 = 1%)
    new_swap_ratio = 500  # 5%
    new_rewards_ratio = 1000  # 10%
    new_yield_ratio = 750  # 7.5%
    
    # Step 1: Initiate ambassador rev share change
    aid = switchboard_alpha.setAmbassadorRevShare(
        new_swap_ratio,
        new_rewards_ratio,
        new_yield_ratio,
        sender=governance.address
    )
    
    # Step 2: Verify event was emitted
    logs = filter_logs(switchboard_alpha, "PendingAmbassadorRevShareChange")
    assert len(logs) == 1
    assert logs[0].swapRatio == new_swap_ratio
    assert logs[0].rewardsRatio == new_rewards_ratio
    assert logs[0].yieldRatio == new_yield_ratio
    assert logs[0].actionId == aid
    # Confirmation block should be current block + timelock
    expected_confirmation_block = boa.env.evm.patch.block_number + switchboard_alpha.actionTimeLock()
    assert logs[0].confirmationBlock == expected_confirmation_block
    
    # Step 3: Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.AMBASSADOR_REV_SHARE
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.ambassadorRevShare.swapRatio == new_swap_ratio
    assert pending_config.ambassadorRevShare.rewardsRatio == new_rewards_ratio
    assert pending_config.ambassadorRevShare.yieldRatio == new_yield_ratio
    
    # Verify the action confirmation block matches what we expect
    assert switchboard_alpha.getActionConfirmationBlock(aid) == expected_confirmation_block
    
    # Step 4: Try to execute before timelock - should fail silently
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Verify no state change
    current_config = mission_control.userWalletConfig()
    assert current_config.ambassadorRevShare.swapRatio == initial_swap_ratio
    assert current_config.ambassadorRevShare.rewardsRatio == initial_rewards_ratio
    assert current_config.ambassadorRevShare.yieldRatio == initial_yield_ratio
    
    # Step 5: Time travel to one block before timelock - should still fail
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock() - 1)
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Travel one more block to reach exact timelock
    boa.env.time_travel(blocks=1)
    
    # Step 6: Now execution should succeed
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Step 7: Verify execution event
    exec_logs = filter_logs(switchboard_alpha, "AmbassadorRevShareSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].swapRatio == new_swap_ratio
    assert exec_logs[0].rewardsRatio == new_rewards_ratio
    assert exec_logs[0].yieldRatio == new_yield_ratio
    
    # Step 8: Verify state changes in MissionControl
    updated_config = mission_control.userWalletConfig()
    assert updated_config.ambassadorRevShare.swapRatio == new_swap_ratio
    assert updated_config.ambassadorRevShare.rewardsRatio == new_rewards_ratio
    assert updated_config.ambassadorRevShare.yieldRatio == new_yield_ratio
    
    # Verify other config fields remain unchanged
    assert updated_config.walletTemplate == initial_config.walletTemplate
    assert updated_config.configTemplate == initial_config.configTemplate
    assert updated_config.trialAsset == initial_config.trialAsset
    assert updated_config.trialAmount == initial_config.trialAmount
    assert updated_config.txFees.swapFee == initial_config.txFees.swapFee
    
    # Step 9: Verify action is cleared
    assert switchboard_alpha.actionType(aid) == 0  # empty(ActionType)
    # Note: pendingUserWalletConfig mapping is not cleared after execution


def test_set_ambassador_rev_share_invalid_values_revert(switchboard_alpha, governance):
    """Test that invalid values (above 100%) revert with proper error message"""
    # Test 1: swapRatio > 100%
    with boa.reverts("invalid ambassador rev share ratios"):
        switchboard_alpha.setAmbassadorRevShare(
            10001,  # > 100%
            100,
            100,
            sender=governance.address
        )
    
    # Test 2: rewardsRatio > 100%
    with boa.reverts("invalid ambassador rev share ratios"):
        switchboard_alpha.setAmbassadorRevShare(
            100,
            10001,  # > 100%
            100,
            sender=governance.address
        )
    
    # Test 3: yieldRatio > 100%
    with boa.reverts("invalid ambassador rev share ratios"):
        switchboard_alpha.setAmbassadorRevShare(
            100,
            100,
            10001,  # > 100%
            sender=governance.address
        )
    
    # Test 4: All ratios > 100%
    with boa.reverts("invalid ambassador rev share ratios"):
        switchboard_alpha.setAmbassadorRevShare(
            20000,  # 200%
            15000,  # 150%
            25000,  # 250%
            sender=governance.address
        )


def test_set_ambassador_rev_share_zero_values_allowed(switchboard_alpha, governance, mission_control):
    """Test that zero ratio values are allowed"""
    # Set all ratios to 0
    aid = switchboard_alpha.setAmbassadorRevShare(
        0,
        0,
        0,
        sender=governance.address
    )
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.AMBASSADOR_REV_SHARE
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.ambassadorRevShare.swapRatio == 0
    assert pending_config.ambassadorRevShare.rewardsRatio == 0
    assert pending_config.ambassadorRevShare.yieldRatio == 0
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify state changes
    updated_config = mission_control.userWalletConfig()
    assert updated_config.ambassadorRevShare.swapRatio == 0
    assert updated_config.ambassadorRevShare.rewardsRatio == 0
    assert updated_config.ambassadorRevShare.yieldRatio == 0


def test_set_ambassador_rev_share_non_governance_reverts(switchboard_alpha, alice):
    """Test that non-governance cannot set ambassador rev share"""
    with boa.reverts("no perms"):
        switchboard_alpha.setAmbassadorRevShare(
            500,
            1000,
            750,
            sender=alice
        )


def test_set_ambassador_rev_share_maximum_allowed_values(switchboard_alpha, governance, mission_control):
    """Test maximum allowed ratio values (100% = 10000 basis points)"""
    # Set all ratios to maximum allowed (100%)
    aid = switchboard_alpha.setAmbassadorRevShare(
        10000,  # 100%
        10000,  # 100%
        10000,  # 100%
        sender=governance.address
    )
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.AMBASSADOR_REV_SHARE
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.ambassadorRevShare.swapRatio == 10000
    assert pending_config.ambassadorRevShare.rewardsRatio == 10000
    assert pending_config.ambassadorRevShare.yieldRatio == 10000
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify state changes
    updated_config = mission_control.userWalletConfig()
    assert updated_config.ambassadorRevShare.swapRatio == 10000
    assert updated_config.ambassadorRevShare.rewardsRatio == 10000
    assert updated_config.ambassadorRevShare.yieldRatio == 10000


def test_set_ambassador_rev_share_mixed_values(switchboard_alpha, governance, mission_control):
    """Test setting different values for each ratio"""
    # Set different values for each ratio
    aid = switchboard_alpha.setAmbassadorRevShare(
        0,      # 0% swap ratio
        5000,   # 50% rewards ratio
        10000,  # 100% yield ratio
        sender=governance.address
    )
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.AMBASSADOR_REV_SHARE
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.ambassadorRevShare.swapRatio == 0
    assert pending_config.ambassadorRevShare.rewardsRatio == 5000
    assert pending_config.ambassadorRevShare.yieldRatio == 10000
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify state changes
    updated_config = mission_control.userWalletConfig()
    assert updated_config.ambassadorRevShare.swapRatio == 0
    assert updated_config.ambassadorRevShare.rewardsRatio == 5000
    assert updated_config.ambassadorRevShare.yieldRatio == 10000


########################
# Default Yield Params #
########################


def test_set_default_yield_params_success(switchboard_alpha, governance, mission_control, alice):
    """Test successful default yield params update through full lifecycle"""
    # Get initial config from MissionControl
    initial_config = mission_control.userWalletConfig()
    initial_max_increase = initial_config.defaultYieldMaxIncrease
    initial_performance_fee = initial_config.defaultYieldPerformanceFee
    initial_ambassador_bonus_ratio = initial_config.defaultYieldAmbassadorBonusRatio
    initial_bonus_ratio = initial_config.defaultYieldBonusRatio
    initial_alt_bonus_asset = initial_config.defaultYieldAltBonusAsset
    
    # New default yield params values
    new_max_increase = 1000  # 10%
    new_performance_fee = 2000  # 20%
    new_ambassador_bonus_ratio = 500  # 5%
    new_bonus_ratio = 1500  # 15%
    new_alt_bonus_asset = alice  # Using alice address as alt bonus asset
    
    # Step 1: Initiate default yield params change
    aid = switchboard_alpha.setDefaultYieldParams(
        new_max_increase,
        new_performance_fee,
        new_ambassador_bonus_ratio,
        new_bonus_ratio,
        new_alt_bonus_asset,
        sender=governance.address
    )
    
    # Step 2: Verify event was emitted
    logs = filter_logs(switchboard_alpha, "PendingDefaultYieldParamsChange")
    assert len(logs) == 1
    assert logs[0].defaultYieldMaxIncrease == new_max_increase
    assert logs[0].defaultYieldPerformanceFee == new_performance_fee
    assert logs[0].defaultYieldAmbassadorBonusRatio == new_ambassador_bonus_ratio
    assert logs[0].defaultYieldBonusRatio == new_bonus_ratio
    assert logs[0].defaultYieldAltBonusAsset == new_alt_bonus_asset
    assert logs[0].actionId == aid
    # Confirmation block should be current block + timelock
    expected_confirmation_block = boa.env.evm.patch.block_number + switchboard_alpha.actionTimeLock()
    assert logs[0].confirmationBlock == expected_confirmation_block
    
    # Step 3: Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.DEFAULT_YIELD_PARAMS
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.defaultYieldMaxIncrease == new_max_increase
    assert pending_config.defaultYieldPerformanceFee == new_performance_fee
    assert pending_config.defaultYieldAmbassadorBonusRatio == new_ambassador_bonus_ratio
    assert pending_config.defaultYieldBonusRatio == new_bonus_ratio
    assert pending_config.defaultYieldAltBonusAsset == new_alt_bonus_asset
    
    # Verify the action confirmation block matches what we expect
    assert switchboard_alpha.getActionConfirmationBlock(aid) == expected_confirmation_block
    
    # Step 4: Try to execute before timelock - should fail silently
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Verify no state change
    current_config = mission_control.userWalletConfig()
    assert current_config.defaultYieldMaxIncrease == initial_max_increase
    assert current_config.defaultYieldPerformanceFee == initial_performance_fee
    assert current_config.defaultYieldAmbassadorBonusRatio == initial_ambassador_bonus_ratio
    assert current_config.defaultYieldBonusRatio == initial_bonus_ratio
    assert current_config.defaultYieldAltBonusAsset == initial_alt_bonus_asset
    
    # Step 5: Time travel to one block before timelock - should still fail
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock() - 1)
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Travel one more block to reach exact timelock
    boa.env.time_travel(blocks=1)
    
    # Step 6: Now execution should succeed
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Step 7: Verify execution event
    exec_logs = filter_logs(switchboard_alpha, "DefaultYieldParamsSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].defaultYieldMaxIncrease == new_max_increase
    assert exec_logs[0].defaultYieldPerformanceFee == new_performance_fee
    assert exec_logs[0].defaultYieldAmbassadorBonusRatio == new_ambassador_bonus_ratio
    assert exec_logs[0].defaultYieldBonusRatio == new_bonus_ratio
    assert exec_logs[0].defaultYieldAltBonusAsset == new_alt_bonus_asset
    
    # Step 8: Verify state changes in MissionControl
    updated_config = mission_control.userWalletConfig()
    assert updated_config.defaultYieldMaxIncrease == new_max_increase
    assert updated_config.defaultYieldPerformanceFee == new_performance_fee
    assert updated_config.defaultYieldAmbassadorBonusRatio == new_ambassador_bonus_ratio
    assert updated_config.defaultYieldBonusRatio == new_bonus_ratio
    assert updated_config.defaultYieldAltBonusAsset == new_alt_bonus_asset
    
    # Verify other config fields remain unchanged
    assert updated_config.walletTemplate == initial_config.walletTemplate
    assert updated_config.configTemplate == initial_config.configTemplate
    assert updated_config.trialAsset == initial_config.trialAsset
    assert updated_config.trialAmount == initial_config.trialAmount
    
    # Step 9: Verify action is cleared
    assert switchboard_alpha.actionType(aid) == 0  # empty(ActionType)
    # Note: pendingUserWalletConfig mapping is not cleared after execution


def test_set_default_yield_params_invalid_values_revert(switchboard_alpha, governance, alice):
    """Test that invalid values (above 100%) revert with proper error message"""
    # Test 1: defaultYieldMaxIncrease > 100%
    with boa.reverts("invalid default yield params"):
        switchboard_alpha.setDefaultYieldParams(
            10001,  # > 100%
            1000,
            1000,
            1000,
            alice,
            sender=governance.address
        )
    
    # Test 2: defaultYieldPerformanceFee > 100%
    with boa.reverts("invalid default yield params"):
        switchboard_alpha.setDefaultYieldParams(
            1000,
            10001,  # > 100%
            1000,
            1000,
            alice,
            sender=governance.address
        )
    
    # Test 3: defaultYieldAmbassadorBonusRatio > 100%
    with boa.reverts("invalid default yield params"):
        switchboard_alpha.setDefaultYieldParams(
            1000,
            1000,
            10001,  # > 100%
            1000,
            alice,
            sender=governance.address
        )
    
    # Test 4: defaultYieldBonusRatio > 100%
    with boa.reverts("invalid default yield params"):
        switchboard_alpha.setDefaultYieldParams(
            1000,
            1000,
            1000,
            10001,  # > 100%
            alice,
            sender=governance.address
        )
    
    # Test 5: All percentage params > 100%
    with boa.reverts("invalid default yield params"):
        switchboard_alpha.setDefaultYieldParams(
            20000,  # 200%
            15000,  # 150%
            25000,  # 250%
            30000,  # 300%
            alice,
            sender=governance.address
        )


def test_set_default_yield_params_zero_values_allowed(switchboard_alpha, governance, mission_control):
    """Test that zero values are allowed for all params"""
    # Set all params to 0/ZERO_ADDRESS
    aid = switchboard_alpha.setDefaultYieldParams(
        0,
        0,
        0,
        0,
        ZERO_ADDRESS,
        sender=governance.address
    )
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.DEFAULT_YIELD_PARAMS
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.defaultYieldMaxIncrease == 0
    assert pending_config.defaultYieldPerformanceFee == 0
    assert pending_config.defaultYieldAmbassadorBonusRatio == 0
    assert pending_config.defaultYieldBonusRatio == 0
    assert pending_config.defaultYieldAltBonusAsset == ZERO_ADDRESS
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify state changes
    updated_config = mission_control.userWalletConfig()
    assert updated_config.defaultYieldMaxIncrease == 0
    assert updated_config.defaultYieldPerformanceFee == 0
    assert updated_config.defaultYieldAmbassadorBonusRatio == 0
    assert updated_config.defaultYieldBonusRatio == 0
    assert updated_config.defaultYieldAltBonusAsset == ZERO_ADDRESS


def test_set_default_yield_params_non_governance_reverts(switchboard_alpha, alice):
    """Test that non-governance cannot set default yield params"""
    with boa.reverts("no perms"):
        switchboard_alpha.setDefaultYieldParams(
            1000,
            2000,
            500,
            1500,
            alice,
            sender=alice
        )


def test_set_default_yield_params_maximum_allowed_values(switchboard_alpha, governance, mission_control, alpha_token):
    """Test maximum allowed percentage values (100% = 10000 basis points)"""
    # Set all percentage params to maximum allowed (100%)
    aid = switchboard_alpha.setDefaultYieldParams(
        10000,  # 100%
        10000,  # 100%
        10000,  # 100%
        10000,  # 100%
        alpha_token.address,  # Use a valid token address
        sender=governance.address
    )
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.DEFAULT_YIELD_PARAMS
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.defaultYieldMaxIncrease == 10000
    assert pending_config.defaultYieldPerformanceFee == 10000
    assert pending_config.defaultYieldAmbassadorBonusRatio == 10000
    assert pending_config.defaultYieldBonusRatio == 10000
    assert pending_config.defaultYieldAltBonusAsset == alpha_token.address
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify state changes
    updated_config = mission_control.userWalletConfig()
    assert updated_config.defaultYieldMaxIncrease == 10000
    assert updated_config.defaultYieldPerformanceFee == 10000
    assert updated_config.defaultYieldAmbassadorBonusRatio == 10000
    assert updated_config.defaultYieldBonusRatio == 10000
    assert updated_config.defaultYieldAltBonusAsset == alpha_token.address


def test_set_default_yield_params_mixed_values(switchboard_alpha, governance, mission_control, alice, bob):
    """Test setting different values for each param"""
    # Set different values for each param
    aid = switchboard_alpha.setDefaultYieldParams(
        0,      # 0% max increase
        5000,   # 50% performance fee
        10000,  # 100% ambassador bonus ratio
        2500,   # 25% bonus ratio
        bob,    # bob address as alt bonus asset
        sender=governance.address
    )
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.DEFAULT_YIELD_PARAMS
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.defaultYieldMaxIncrease == 0
    assert pending_config.defaultYieldPerformanceFee == 5000
    assert pending_config.defaultYieldAmbassadorBonusRatio == 10000
    assert pending_config.defaultYieldBonusRatio == 2500
    assert pending_config.defaultYieldAltBonusAsset == bob
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify state changes
    updated_config = mission_control.userWalletConfig()
    assert updated_config.defaultYieldMaxIncrease == 0
    assert updated_config.defaultYieldPerformanceFee == 5000
    assert updated_config.defaultYieldAmbassadorBonusRatio == 10000
    assert updated_config.defaultYieldBonusRatio == 2500
    assert updated_config.defaultYieldAltBonusAsset == bob


################
# Loot Params  #
################


def test_set_loot_params_success(switchboard_alpha, governance, mission_control, alpha_token):
    """Test successful loot params update through full lifecycle"""
    # Get initial config from MissionControl
    initial_config = mission_control.userWalletConfig()
    initial_deposit_rewards_asset = initial_config.depositRewardsAsset
    initial_loot_claim_cool_off_period = initial_config.lootClaimCoolOffPeriod
    
    # New loot params values
    new_deposit_rewards_asset = alpha_token.address
    new_loot_claim_cool_off_period = 86400  # ~1 day in blocks
    
    # Step 1: Initiate loot params change
    aid = switchboard_alpha.setLootParams(
        new_deposit_rewards_asset,
        new_loot_claim_cool_off_period,
        sender=governance.address
    )
    
    # Step 2: Verify event was emitted
    logs = filter_logs(switchboard_alpha, "PendingLootParamsChange")
    assert len(logs) == 1
    assert logs[0].depositRewardsAsset == new_deposit_rewards_asset
    assert logs[0].lootClaimCoolOffPeriod == new_loot_claim_cool_off_period
    assert logs[0].actionId == aid
    # Confirmation block should be current block + timelock
    expected_confirmation_block = boa.env.evm.patch.block_number + switchboard_alpha.actionTimeLock()
    assert logs[0].confirmationBlock == expected_confirmation_block
    
    # Step 3: Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.LOOT_PARAMS
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.depositRewardsAsset == new_deposit_rewards_asset
    assert pending_config.lootClaimCoolOffPeriod == new_loot_claim_cool_off_period
    
    # Verify the action confirmation block matches what we expect
    assert switchboard_alpha.getActionConfirmationBlock(aid) == expected_confirmation_block
    
    # Step 4: Try to execute before timelock - should fail silently
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Verify no state change
    current_config = mission_control.userWalletConfig()
    assert current_config.depositRewardsAsset == initial_deposit_rewards_asset
    assert current_config.lootClaimCoolOffPeriod == initial_loot_claim_cool_off_period
    
    # Step 5: Time travel to one block before timelock - should still fail
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock() - 1)
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Travel one more block to reach exact timelock
    boa.env.time_travel(blocks=1)
    
    # Step 6: Now execution should succeed
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Step 7: Verify execution event
    exec_logs = filter_logs(switchboard_alpha, "LootParamsSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].depositRewardsAsset == new_deposit_rewards_asset
    assert exec_logs[0].lootClaimCoolOffPeriod == new_loot_claim_cool_off_period
    
    # Step 8: Verify state changes in MissionControl
    updated_config = mission_control.userWalletConfig()
    assert updated_config.depositRewardsAsset == new_deposit_rewards_asset
    assert updated_config.lootClaimCoolOffPeriod == new_loot_claim_cool_off_period
    
    # Verify other config fields remain unchanged
    assert updated_config.walletTemplate == initial_config.walletTemplate
    assert updated_config.configTemplate == initial_config.configTemplate
    assert updated_config.trialAsset == initial_config.trialAsset
    assert updated_config.trialAmount == initial_config.trialAmount
    assert updated_config.numUserWalletsAllowed == initial_config.numUserWalletsAllowed
    
    # Step 9: Verify action is cleared
    assert switchboard_alpha.actionType(aid) == 0  # empty(ActionType)
    # Note: pendingUserWalletConfig mapping is not cleared after execution


def test_set_loot_params_invalid_cool_off_period_revert(switchboard_alpha, governance, alice):
    """Test that invalid cool off period values revert with proper error message"""
    # Test 1: lootClaimCoolOffPeriod = 0
    with boa.reverts("invalid loot params"):
        switchboard_alpha.setLootParams(
            alice,
            0,
            sender=governance.address
        )
    
    # Test 2: lootClaimCoolOffPeriod = max_value(uint256)
    with boa.reverts("invalid loot params"):
        switchboard_alpha.setLootParams(
            alice,
            2**256 - 1,
            sender=governance.address
        )


def test_set_loot_params_zero_address_allowed(switchboard_alpha, governance, mission_control):
    """Test that zero address is allowed for depositRewardsAsset"""
    # Set depositRewardsAsset to ZERO_ADDRESS with valid cool off period
    aid = switchboard_alpha.setLootParams(
        ZERO_ADDRESS,
        43200,  # ~12 hours in blocks
        sender=governance.address
    )
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.LOOT_PARAMS
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.depositRewardsAsset == ZERO_ADDRESS
    assert pending_config.lootClaimCoolOffPeriod == 43200
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify state changes
    updated_config = mission_control.userWalletConfig()
    assert updated_config.depositRewardsAsset == ZERO_ADDRESS
    assert updated_config.lootClaimCoolOffPeriod == 43200


def test_set_loot_params_non_governance_reverts(switchboard_alpha, alice):
    """Test that non-governance cannot set loot params"""
    with boa.reverts("no perms"):
        switchboard_alpha.setLootParams(
            alice,
            86400,
            sender=alice
        )


def test_set_loot_params_edge_cases(switchboard_alpha, governance, mission_control, alpha_token):
    """Test edge cases for loot params"""
    # Test with minimum valid cool off period (1)
    aid = switchboard_alpha.setLootParams(
        alpha_token.address,
        1,
        sender=governance.address
    )
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.LOOT_PARAMS
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.depositRewardsAsset == alpha_token.address
    assert pending_config.lootClaimCoolOffPeriod == 1
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify state changes
    updated_config = mission_control.userWalletConfig()
    assert updated_config.depositRewardsAsset == alpha_token.address
    assert updated_config.lootClaimCoolOffPeriod == 1
    
    # Test with large cool off period (but not max)
    large_cool_off = 2**256 - 2
    aid2 = switchboard_alpha.setLootParams(
        ZERO_ADDRESS,
        large_cool_off,
        sender=governance.address
    )
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid2, sender=governance.address)
    assert result == True
    
    # Verify state changes
    final_config = mission_control.userWalletConfig()
    assert final_config.depositRewardsAsset == ZERO_ADDRESS
    assert final_config.lootClaimCoolOffPeriod == large_cool_off


def test_set_loot_params_different_assets(switchboard_alpha, governance, mission_control, alice, bob, alpha_token):
    """Test setting different types of addresses for depositRewardsAsset"""
    # Test with EOA address
    aid = switchboard_alpha.setLootParams(
        alice,  # EOA address
        604800,  # ~1 week in blocks
        sender=governance.address
    )
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify state changes
    config = mission_control.userWalletConfig()
    assert config.depositRewardsAsset == alice
    assert config.lootClaimCoolOffPeriod == 604800
    
    # Test with contract address
    aid2 = switchboard_alpha.setLootParams(
        alpha_token.address,  # Contract address
        172800,  # ~2 days in blocks
        sender=governance.address
    )
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid2, sender=governance.address)
    assert result == True
    
    # Verify state changes
    final_config = mission_control.userWalletConfig()
    assert final_config.depositRewardsAsset == alpha_token.address
    assert final_config.lootClaimCoolOffPeriod == 172800