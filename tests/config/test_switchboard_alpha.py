import pytest
import boa
from conf_utils import filter_logs
from constants import ZERO_ADDRESS, CONFIG_ACTION_TYPE, MAX_UINT256


@pytest.fixture(scope="module")
def wallet_template_v2():
    return boa.load_partial("contracts/core/userWallet/UserWallet.vy").deploy_as_blueprint()


@pytest.fixture(scope="module")
def config_template_v2():
    return boa.load_partial("contracts/core/userWallet/UserWalletConfig.vy").deploy_as_blueprint()


@pytest.fixture(scope="module")
def agent_template_v2():
    return boa.load_partial("contracts/core/agent/AgentWrapper.vy").deploy_as_blueprint()


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
    """Test that non-governance addresses cannot set wallet templates"""
    with boa.reverts("no perms"):
        switchboard_alpha.setUserWalletTemplates(
            wallet_template_v2.address,
            config_template_v2.address,
            sender=alice
        )


def test_set_user_wallet_templates_invalid_addresses_revert(switchboard_alpha, governance, wallet_template_v2, alice):
    """Test various invalid address scenarios"""
    # Test with zero addresses
    with boa.reverts("invalid user wallet templates"):
        switchboard_alpha.setUserWalletTemplates(ZERO_ADDRESS, wallet_template_v2.address, sender=governance.address)
    
    with boa.reverts("invalid user wallet templates"):
        switchboard_alpha.setUserWalletTemplates(wallet_template_v2.address, ZERO_ADDRESS, sender=governance.address)
    
    with boa.reverts("invalid user wallet templates"):
        switchboard_alpha.setUserWalletTemplates(ZERO_ADDRESS, ZERO_ADDRESS, sender=governance.address)
    
    # Test with EOA as wallet template
    with boa.reverts("invalid user wallet templates"):
        switchboard_alpha.setUserWalletTemplates(alice, wallet_template_v2.address, sender=governance.address)
    
    # Test with EOA as config template
    with boa.reverts("invalid user wallet templates"):
        switchboard_alpha.setUserWalletTemplates(wallet_template_v2.address, alice, sender=governance.address)
    
    # Test with both EOAs
    with boa.reverts("invalid user wallet templates"):
        switchboard_alpha.setUserWalletTemplates(alice, alice, sender=governance.address)


def test_cancel_pending_wallet_template_update(switchboard_alpha, governance, mission_control, wallet_template_v2, config_template_v2):
    """Test canceling a pending wallet template update"""
    # Get initial config
    initial_config = mission_control.userWalletConfig()
    
    # Initiate template change
    aid = switchboard_alpha.setUserWalletTemplates(
        wallet_template_v2.address,
        config_template_v2.address,
        sender=governance.address
    )
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.USER_WALLET_TEMPLATES
    
    # Cancel the pending action
    result = switchboard_alpha.cancelPendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify action is cleared
    assert switchboard_alpha.actionType(aid) == 0  # empty(ActionType)
    
    # Try to execute canceled action - should fail
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Verify config hasn't changed
    final_config = mission_control.userWalletConfig()
    assert final_config.walletTemplate == initial_config.walletTemplate
    assert final_config.configTemplate == initial_config.configTemplate


def test_cancel_pending_action_non_governance_reverts(switchboard_alpha, governance, alice, wallet_template_v2, config_template_v2):
    """Test that non-governance addresses cannot cancel pending actions"""
    # Create a pending action
    aid = switchboard_alpha.setUserWalletTemplates(
        wallet_template_v2.address,
        config_template_v2.address,
        sender=governance.address
    )
    
    # Try to cancel as non-governance
    with boa.reverts("no perms"):
        switchboard_alpha.cancelPendingAction(aid, sender=alice)


def test_execute_expired_wallet_template_update(switchboard_alpha, governance, mission_control, wallet_template_v2, config_template_v2):
    """Test that expired actions auto-cancel and cannot be executed"""
    # Get initial config
    initial_config = mission_control.userWalletConfig()
    
    # Initiate template change
    aid = switchboard_alpha.setUserWalletTemplates(
        wallet_template_v2.address,
        config_template_v2.address,
        sender=governance.address
    )
    
    # Time travel past expiration (timelock + max timelock)
    max_timelock = switchboard_alpha.maxActionTimeLock()
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock() + max_timelock + 1)
    
    # Try to execute - should auto-cancel and return False
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Verify action is cleared
    assert switchboard_alpha.actionType(aid) == 0  # empty(ActionType)
    
    # Verify config hasn't changed
    final_config = mission_control.userWalletConfig()
    assert final_config.walletTemplate == initial_config.walletTemplate
    assert final_config.configTemplate == initial_config.configTemplate


def test_execute_pending_action_non_governance_reverts(switchboard_alpha, governance, alice, wallet_template_v2, config_template_v2):
    """Test that non-governance addresses cannot execute pending actions"""
    # Create a pending action
    aid = switchboard_alpha.setUserWalletTemplates(
        wallet_template_v2.address,
        config_template_v2.address,
        sender=governance.address
    )
    
    # Time travel to timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    
    # Try to execute as non-governance
    with boa.reverts("no perms"):
        switchboard_alpha.executePendingAction(aid, sender=alice)


def test_multiple_pending_wallet_template_updates(switchboard_alpha, governance, mission_control):
    """Test creating multiple pending updates with different action IDs"""
    # Deploy multiple template sets
    templates1 = boa.load_partial("contracts/core/userWallet/UserWallet.vy").deploy_as_blueprint()
    config1 = boa.load_partial("contracts/core/userWallet/UserWalletConfig.vy").deploy_as_blueprint()
    
    templates2 = boa.load_partial("contracts/core/userWallet/UserWallet.vy").deploy_as_blueprint()
    config2 = boa.load_partial("contracts/core/userWallet/UserWalletConfig.vy").deploy_as_blueprint()
    
    # Create first pending action
    aid1 = switchboard_alpha.setUserWalletTemplates(
        templates1.address,
        config1.address,
        sender=governance.address
    )
    
    # Create second pending action
    aid2 = switchboard_alpha.setUserWalletTemplates(
        templates2.address,
        config2.address,
        sender=governance.address
    )
    
    # Verify different action IDs
    assert aid1 != aid2
    
    # Verify both are pending
    assert switchboard_alpha.actionType(aid1) == CONFIG_ACTION_TYPE.USER_WALLET_TEMPLATES
    assert switchboard_alpha.actionType(aid2) == CONFIG_ACTION_TYPE.USER_WALLET_TEMPLATES
    
    # Verify different pending configs
    pending1 = switchboard_alpha.pendingUserWalletConfig(aid1)
    pending2 = switchboard_alpha.pendingUserWalletConfig(aid2)
    assert pending1.walletTemplate == templates1.address
    assert pending2.walletTemplate == templates2.address
    
    # Execute second action first
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid2, sender=governance.address)
    assert result == True
    
    # Verify config updated to second set
    config = mission_control.userWalletConfig()
    assert config.walletTemplate == templates2.address
    assert config.configTemplate == config2.address
    
    # First action should still be pending
    assert switchboard_alpha.actionType(aid1) == CONFIG_ACTION_TYPE.USER_WALLET_TEMPLATES
    
    # Execute first action
    result = switchboard_alpha.executePendingAction(aid1, sender=governance.address)
    assert result == True
    
    # Verify config updated to first set
    final_config = mission_control.userWalletConfig()
    assert final_config.walletTemplate == templates1.address
    assert final_config.configTemplate == config1.address


################
# Trial Funds  #
################


def test_set_trial_funds_success(switchboard_alpha, governance, mission_control, alpha_token):
    """Test successful trial funds update through full lifecycle"""
    # Get initial config
    initial_config = mission_control.userWalletConfig()
    
    # Step 1: Initiate trial funds change
    trial_amount = 1000 * 10**18  # 1000 tokens
    aid = switchboard_alpha.setTrialFunds(
        alpha_token.address,
        trial_amount,
        sender=governance.address
    )
    
    # Step 2: Verify event was emitted
    logs = filter_logs(switchboard_alpha, "PendingTrialFundsChange")
    assert len(logs) == 1
    assert logs[0].trialAsset == alpha_token.address
    assert logs[0].trialAmount == trial_amount
    assert logs[0].actionId == aid
    expected_confirmation_block = boa.env.evm.patch.block_number + switchboard_alpha.actionTimeLock()
    assert logs[0].confirmationBlock == expected_confirmation_block
    
    # Step 3: Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.TRIAL_FUNDS
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.trialAsset == alpha_token.address
    assert pending_config.trialAmount == trial_amount
    
    # Step 4: Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Step 5: Verify execution event
    exec_logs = filter_logs(switchboard_alpha, "TrialFundsSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].trialAsset == alpha_token.address
    assert exec_logs[0].trialAmount == trial_amount
    
    # Step 6: Verify state changes in MissionControl
    updated_config = mission_control.userWalletConfig()
    assert updated_config.trialAsset == alpha_token.address
    assert updated_config.trialAmount == trial_amount
    
    # Verify other config fields remain unchanged
    assert updated_config.walletTemplate == initial_config.walletTemplate
    assert updated_config.numUserWalletsAllowed == initial_config.numUserWalletsAllowed
    
    # Step 7: Verify action is cleared
    assert switchboard_alpha.actionType(aid) == 0


def test_set_trial_funds_zero_values_allowed(switchboard_alpha, governance, mission_control, alpha_token):
    """Test that zero amount and zero address are allowed for trial funds"""
    # Test with zero amount
    aid = switchboard_alpha.setTrialFunds(
        alpha_token.address,
        0,  # Zero amount
        sender=governance.address
    )
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    config = mission_control.userWalletConfig()
    assert config.trialAsset == alpha_token.address
    assert config.trialAmount == 0
    
    # Test with zero address
    aid2 = switchboard_alpha.setTrialFunds(
        ZERO_ADDRESS,  # Zero address
        100,
        sender=governance.address
    )
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid2, sender=governance.address)
    assert result == True
    
    final_config = mission_control.userWalletConfig()
    assert final_config.trialAsset == ZERO_ADDRESS
    assert final_config.trialAmount == 100


def test_set_trial_funds_non_governance_reverts(switchboard_alpha, alice, alpha_token):
    """Test that non-governance addresses cannot set trial funds"""
    with boa.reverts("no perms"):
        switchboard_alpha.setTrialFunds(
            alpha_token.address,
            1000,
            sender=alice
        )


def test_set_trial_funds_mixed_with_template_updates(switchboard_alpha, governance, mission_control, alpha_token, wallet_template_v2, config_template_v2):
    """Test that trial funds and template updates can coexist as separate actions"""
    # Create pending template update
    aid1 = switchboard_alpha.setUserWalletTemplates(
        wallet_template_v2.address,
        config_template_v2.address,
        sender=governance.address
    )
    
    # Create pending trial funds update
    aid2 = switchboard_alpha.setTrialFunds(
        alpha_token.address,
        2000,
        sender=governance.address
    )
    
    # Verify different action types
    assert switchboard_alpha.actionType(aid1) == CONFIG_ACTION_TYPE.USER_WALLET_TEMPLATES
    assert switchboard_alpha.actionType(aid2) == CONFIG_ACTION_TYPE.TRIAL_FUNDS
    
    # Execute trial funds first
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid2, sender=governance.address)
    assert result == True
    
    # Verify only trial funds changed
    config = mission_control.userWalletConfig()
    assert config.trialAsset == alpha_token.address
    assert config.trialAmount == 2000
    # Templates should be unchanged
    initial_config = mission_control.userWalletConfig()
    assert config.walletTemplate == initial_config.walletTemplate
    
    # Execute template update
    result = switchboard_alpha.executePendingAction(aid1, sender=governance.address)
    assert result == True
    
    # Verify both changes are applied
    final_config = mission_control.userWalletConfig()
    assert final_config.walletTemplate == wallet_template_v2.address
    assert final_config.configTemplate == config_template_v2.address
    assert final_config.trialAsset == alpha_token.address
    assert final_config.trialAmount == 2000


##########################
# Wallet Creation Limits #
##########################


def test_set_wallet_creation_limits_success(switchboard_alpha, governance, mission_control):
    """Test successful wallet creation limits update"""
    # Get initial config
    initial_config = mission_control.userWalletConfig()
    
    # Set new limits
    aid = switchboard_alpha.setWalletCreationLimits(
        5,  # numUserWalletsAllowed
        True,  # enforceCreatorWhitelist
        sender=governance.address
    )
    
    # Verify event
    logs = filter_logs(switchboard_alpha, "PendingWalletCreationLimitsChange")
    assert len(logs) == 1
    assert logs[0].numUserWalletsAllowed == 5
    assert logs[0].enforceCreatorWhitelist == True
    assert logs[0].actionId == aid
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.WALLET_CREATION_LIMITS
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.numUserWalletsAllowed == 5
    assert pending_config.enforceCreatorWhitelist == True
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify execution event
    exec_logs = filter_logs(switchboard_alpha, "WalletCreationLimitsSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].numUserWalletsAllowed == 5
    assert exec_logs[0].enforceCreatorWhitelist == True
    
    # Verify state changes
    updated_config = mission_control.userWalletConfig()
    assert updated_config.numUserWalletsAllowed == 5
    assert updated_config.enforceCreatorWhitelist == True
    
    # Verify other fields unchanged
    assert updated_config.walletTemplate == initial_config.walletTemplate
    assert updated_config.trialAmount == initial_config.trialAmount


def test_set_wallet_creation_limits_extreme_values(switchboard_alpha, governance, mission_control):
    """Test setting extreme but valid values"""
    # Test with 1 wallet allowed
    aid = switchboard_alpha.setWalletCreationLimits(
        1,  # Minimum valid value
        False,
        sender=governance.address
    )
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    config = mission_control.userWalletConfig()
    assert config.numUserWalletsAllowed == 1
    assert config.enforceCreatorWhitelist == False
    
    # Test with very large number
    large_num = 2**256 - 2  # max_value - 1
    aid2 = switchboard_alpha.setWalletCreationLimits(
        large_num,
        True,
        sender=governance.address
    )
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid2, sender=governance.address)
    assert result == True
    
    final_config = mission_control.userWalletConfig()
    assert final_config.numUserWalletsAllowed == large_num
    assert final_config.enforceCreatorWhitelist == True


def test_set_wallet_creation_limits_invalid_values_revert(switchboard_alpha, governance):
    """Test that invalid values are rejected"""
    # Test with 0
    with boa.reverts("invalid num user wallets allowed"):
        switchboard_alpha.setWalletCreationLimits(0, False, sender=governance.address)
    
    # Test with max_value
    with boa.reverts("invalid num user wallets allowed"):
        switchboard_alpha.setWalletCreationLimits(MAX_UINT256, False, sender=governance.address)


def test_set_wallet_creation_limits_non_governance_reverts(switchboard_alpha, alice):
    """Test that non-governance addresses cannot set wallet creation limits"""
    with boa.reverts("no perms"):
        switchboard_alpha.setWalletCreationLimits(5, True, sender=alice)


def test_set_wallet_creation_limits_mixed_with_other_updates(switchboard_alpha, governance, mission_control):
    """Test that wallet creation limits can be updated alongside other configs"""
    # Set wallet creation limits
    aid1 = switchboard_alpha.setWalletCreationLimits(3, True, sender=governance.address)
    
    # Set trial funds
    aid2 = switchboard_alpha.setTrialFunds(ZERO_ADDRESS, 500, sender=governance.address)
    
    # Execute both
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    
    result1 = switchboard_alpha.executePendingAction(aid1, sender=governance.address)
    assert result1 == True
    
    result2 = switchboard_alpha.executePendingAction(aid2, sender=governance.address)
    assert result2 == True
    
    # Verify both changes applied
    config = mission_control.userWalletConfig()
    assert config.numUserWalletsAllowed == 3
    assert config.enforceCreatorWhitelist == True
    assert config.trialAsset == ZERO_ADDRESS
    assert config.trialAmount == 500


###############################
# Key Action Timelock Bounds  #
###############################


def test_set_key_action_timelock_bounds_success(switchboard_alpha, governance, mission_control):
    """Test successful key action timelock bounds update"""
    # Set new bounds
    min_timelock = 100
    max_timelock = 1000
    
    aid = switchboard_alpha.setKeyActionTimelockBounds(
        min_timelock,
        max_timelock,
        sender=governance.address
    )
    
    # Verify event
    logs = filter_logs(switchboard_alpha, "PendingKeyActionTimelockBoundsChange")
    assert len(logs) == 1
    assert logs[0].minKeyActionTimeLock == min_timelock
    assert logs[0].maxKeyActionTimeLock == max_timelock
    assert logs[0].actionId == aid
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.KEY_ACTION_TIMELOCK_BOUNDS
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.minKeyActionTimeLock == min_timelock
    assert pending_config.maxKeyActionTimeLock == max_timelock
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify execution event
    exec_logs = filter_logs(switchboard_alpha, "KeyActionTimelockBoundsSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].minKeyActionTimeLock == min_timelock
    assert exec_logs[0].maxKeyActionTimeLock == max_timelock
    
    # Verify state changes
    updated_config = mission_control.userWalletConfig()
    assert updated_config.minKeyActionTimeLock == min_timelock
    assert updated_config.maxKeyActionTimeLock == max_timelock


def test_set_key_action_timelock_bounds_invalid_values_revert(switchboard_alpha, governance):
    """Test that invalid bounds are rejected"""
    # Test with zero values
    with boa.reverts("invalid key action timelock bounds"):
        switchboard_alpha.setKeyActionTimelockBounds(0, 1000, sender=governance.address)
    
    with boa.reverts("invalid key action timelock bounds"):
        switchboard_alpha.setKeyActionTimelockBounds(100, 0, sender=governance.address)
    
    # Test with max_value
    max_val = MAX_UINT256
    with boa.reverts("invalid key action timelock bounds"):
        switchboard_alpha.setKeyActionTimelockBounds(max_val, 1000, sender=governance.address)
    
    with boa.reverts("invalid key action timelock bounds"):
        switchboard_alpha.setKeyActionTimelockBounds(100, max_val, sender=governance.address)
    
    # Test with min >= max
    with boa.reverts("invalid key action timelock bounds"):
        switchboard_alpha.setKeyActionTimelockBounds(1000, 1000, sender=governance.address)
    
    with boa.reverts("invalid key action timelock bounds"):
        switchboard_alpha.setKeyActionTimelockBounds(1000, 999, sender=governance.address)


def test_set_key_action_timelock_bounds_non_governance_reverts(switchboard_alpha, alice):
    """Test that non-governance addresses cannot set key action timelock bounds"""
    with boa.reverts("no perms"):
        switchboard_alpha.setKeyActionTimelockBounds(100, 1000, sender=alice)


def test_set_key_action_timelock_bounds_edge_cases(switchboard_alpha, governance, mission_control):
    """Test edge cases for key action timelock bounds"""
    # Test with min = 1, max = 2 (smallest valid range)
    aid = switchboard_alpha.setKeyActionTimelockBounds(1, 2, sender=governance.address)
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    config = mission_control.userWalletConfig()
    assert config.minKeyActionTimeLock == 1
    assert config.maxKeyActionTimeLock == 2
    
    # Test with large valid range
    large_max = 2**256 - 2
    aid2 = switchboard_alpha.setKeyActionTimelockBounds(1, large_max, sender=governance.address)
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid2, sender=governance.address)
    assert result == True
    
    final_config = mission_control.userWalletConfig()
    assert final_config.minKeyActionTimeLock == 1
    assert final_config.maxKeyActionTimeLock == large_max


#########################
# Default Stale Blocks  #
#########################


def test_set_default_stale_blocks_success(switchboard_alpha, governance, mission_control):
    """Test successful default stale blocks update"""
    # Set new value
    stale_blocks = 43200  # ~1 day
    
    aid = switchboard_alpha.setDefaultStaleBlocks(
        stale_blocks,
        sender=governance.address
    )
    
    # Verify event
    logs = filter_logs(switchboard_alpha, "PendingDefaultStaleBlocksChange")
    assert len(logs) == 1
    assert logs[0].defaultStaleBlocks == stale_blocks
    assert logs[0].actionId == aid
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.DEFAULT_STALE_BLOCKS
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.defaultStaleBlocks == stale_blocks
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify execution event
    exec_logs = filter_logs(switchboard_alpha, "DefaultStaleBlocksSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].defaultStaleBlocks == stale_blocks
    
    # Verify state changes
    updated_config = mission_control.userWalletConfig()
    assert updated_config.defaultStaleBlocks == stale_blocks


def test_set_default_stale_blocks_invalid_values_revert(switchboard_alpha, governance):
    """Test that invalid values are rejected"""
    # Test with 0
    with boa.reverts("invalid default stale blocks"):
        switchboard_alpha.setDefaultStaleBlocks(0, sender=governance.address)
    
    # Test with max_value
    with boa.reverts("invalid default stale blocks"):
        switchboard_alpha.setDefaultStaleBlocks(MAX_UINT256, sender=governance.address)


def test_set_default_stale_blocks_non_governance_reverts(switchboard_alpha, alice):
    """Test that non-governance addresses cannot set default stale blocks"""
    with boa.reverts("no perms"):
        switchboard_alpha.setDefaultStaleBlocks(100, sender=alice)


def test_set_default_stale_blocks_edge_cases(switchboard_alpha, governance, mission_control):
    """Test edge cases for default stale blocks"""
    # Test with 1 (minimum valid)
    aid = switchboard_alpha.setDefaultStaleBlocks(1, sender=governance.address)
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    config = mission_control.userWalletConfig()
    assert config.defaultStaleBlocks == 1
    
    # Test with max_value - 1
    large_blocks = 2**256 - 2
    aid2 = switchboard_alpha.setDefaultStaleBlocks(large_blocks, sender=governance.address)
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid2, sender=governance.address)
    assert result == True
    
    final_config = mission_control.userWalletConfig()
    assert final_config.defaultStaleBlocks == large_blocks


###########
# TX Fees #
###########


def test_set_tx_fees_success(switchboard_alpha, governance, mission_control):
    """Test successful transaction fees update"""
    # Set new fees
    swap_fee = 30  # 0.3%
    stable_swap_fee = 10  # 0.1%
    rewards_fee = 50  # 0.5%
    
    aid = switchboard_alpha.setTxFees(
        swap_fee,
        stable_swap_fee,
        rewards_fee,
        sender=governance.address
    )
    
    # Verify event
    logs = filter_logs(switchboard_alpha, "PendingTxFeesChange")
    assert len(logs) == 1
    assert logs[0].swapFee == swap_fee
    assert logs[0].stableSwapFee == stable_swap_fee
    assert logs[0].rewardsFee == rewards_fee
    assert logs[0].actionId == aid
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.TX_FEES
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.txFees.swapFee == swap_fee
    assert pending_config.txFees.stableSwapFee == stable_swap_fee
    assert pending_config.txFees.rewardsFee == rewards_fee
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify execution event
    exec_logs = filter_logs(switchboard_alpha, "TxFeesSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].swapFee == swap_fee
    assert exec_logs[0].stableSwapFee == stable_swap_fee
    assert exec_logs[0].rewardsFee == rewards_fee
    
    # Verify state changes
    updated_config = mission_control.userWalletConfig()
    assert updated_config.txFees.swapFee == swap_fee
    assert updated_config.txFees.stableSwapFee == stable_swap_fee
    assert updated_config.txFees.rewardsFee == rewards_fee


def test_set_tx_fees_invalid_values_revert(switchboard_alpha, governance):
    """Test that fees exceeding their specific limits are rejected"""
    # Test swap fee > 5%
    with boa.reverts("invalid tx fees"):
        switchboard_alpha.setTxFees(501, 0, 0, sender=governance.address)
    
    # Test stable swap fee > 2%
    with boa.reverts("invalid tx fees"):
        switchboard_alpha.setTxFees(0, 201, 0, sender=governance.address)
    
    # Test rewards fee > 25%
    with boa.reverts("invalid tx fees"):
        switchboard_alpha.setTxFees(0, 0, 2501, sender=governance.address)
    
    # Test all fees at their max + 1
    with boa.reverts("invalid tx fees"):
        switchboard_alpha.setTxFees(501, 201, 2501, sender=governance.address)


def test_set_tx_fees_zero_values_allowed(switchboard_alpha, governance, mission_control):
    """Test that zero fees are allowed"""
    aid = switchboard_alpha.setTxFees(0, 0, 0, sender=governance.address)
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    config = mission_control.userWalletConfig()
    assert config.txFees.swapFee == 0
    assert config.txFees.stableSwapFee == 0
    assert config.txFees.rewardsFee == 0


def test_set_tx_fees_non_governance_reverts(switchboard_alpha, alice):
    """Test that non-governance addresses cannot set tx fees"""
    with boa.reverts("no perms"):
        switchboard_alpha.setTxFees(30, 10, 50, sender=alice)


def test_set_tx_fees_maximum_allowed_values(switchboard_alpha, governance, mission_control):
    """Test setting fees to their maximum allowed values"""
    # Set each fee to its maximum: swap 5%, stable swap 2%, rewards 25%
    aid = switchboard_alpha.setTxFees(500, 200, 2500, sender=governance.address)
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    config = mission_control.userWalletConfig()
    assert config.txFees.swapFee == 500
    assert config.txFees.stableSwapFee == 200
    assert config.txFees.rewardsFee == 2500


def test_set_tx_fees_edge_cases(switchboard_alpha, governance, mission_control):
    """Test setting fees at their exact limits"""
    # Test swap fee at exactly 5%
    aid = switchboard_alpha.setTxFees(500, 0, 0, sender=governance.address)
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    assert switchboard_alpha.executePendingAction(aid, sender=governance.address) == True
    
    # Test stable swap fee at exactly 2%
    aid = switchboard_alpha.setTxFees(0, 200, 0, sender=governance.address)
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    assert switchboard_alpha.executePendingAction(aid, sender=governance.address) == True
    
    # Test rewards fee at exactly 25%
    aid = switchboard_alpha.setTxFees(0, 0, 2500, sender=governance.address)
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    assert switchboard_alpha.executePendingAction(aid, sender=governance.address) == True
    
    # Verify all fees work at their limits simultaneously
    aid = switchboard_alpha.setTxFees(500, 200, 2500, sender=governance.address)
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    assert switchboard_alpha.executePendingAction(aid, sender=governance.address) == True
    
    config = mission_control.userWalletConfig()
    assert config.txFees.swapFee == 500
    assert config.txFees.stableSwapFee == 200
    assert config.txFees.rewardsFee == 2500


##########################
# Ambassador Rev Share   #
##########################


def test_set_ambassador_rev_share_success(switchboard_alpha, governance, mission_control):
    """Test successful ambassador revenue share update"""
    # Set new ratios
    swap_ratio = 1000  # 10%
    rewards_ratio = 2000  # 20%
    yield_ratio = 1500  # 15%
    
    aid = switchboard_alpha.setAmbassadorRevShare(
        swap_ratio,
        rewards_ratio,
        yield_ratio,
        sender=governance.address
    )
    
    # Verify event
    logs = filter_logs(switchboard_alpha, "PendingAmbassadorRevShareChange")
    assert len(logs) == 1
    assert logs[0].swapRatio == swap_ratio
    assert logs[0].rewardsRatio == rewards_ratio
    assert logs[0].yieldRatio == yield_ratio
    assert logs[0].actionId == aid
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.AMBASSADOR_REV_SHARE
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.ambassadorRevShare.swapRatio == swap_ratio
    assert pending_config.ambassadorRevShare.rewardsRatio == rewards_ratio
    assert pending_config.ambassadorRevShare.yieldRatio == yield_ratio
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify execution event
    exec_logs = filter_logs(switchboard_alpha, "AmbassadorRevShareSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].swapRatio == swap_ratio
    assert exec_logs[0].rewardsRatio == rewards_ratio
    assert exec_logs[0].yieldRatio == yield_ratio
    
    # Verify state changes
    updated_config = mission_control.userWalletConfig()
    assert updated_config.ambassadorRevShare.swapRatio == swap_ratio
    assert updated_config.ambassadorRevShare.rewardsRatio == rewards_ratio
    assert updated_config.ambassadorRevShare.yieldRatio == yield_ratio


def test_set_ambassador_rev_share_invalid_values_revert(switchboard_alpha, governance):
    """Test that ratios exceeding 100% are rejected"""
    # Test swap ratio > 100%
    with boa.reverts("invalid ambassador rev share ratios"):
        switchboard_alpha.setAmbassadorRevShare(10001, 0, 0, sender=governance.address)
    
    # Test rewards ratio > 100%
    with boa.reverts("invalid ambassador rev share ratios"):
        switchboard_alpha.setAmbassadorRevShare(0, 10001, 0, sender=governance.address)
    
    # Test yield ratio > 100%
    with boa.reverts("invalid ambassador rev share ratios"):
        switchboard_alpha.setAmbassadorRevShare(0, 0, 10001, sender=governance.address)


def test_set_ambassador_rev_share_zero_values_allowed(switchboard_alpha, governance, mission_control):
    """Test that zero ratios are allowed"""
    aid = switchboard_alpha.setAmbassadorRevShare(0, 0, 0, sender=governance.address)
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    config = mission_control.userWalletConfig()
    assert config.ambassadorRevShare.swapRatio == 0
    assert config.ambassadorRevShare.rewardsRatio == 0
    assert config.ambassadorRevShare.yieldRatio == 0


def test_set_ambassador_rev_share_non_governance_reverts(switchboard_alpha, alice):
    """Test that non-governance addresses cannot set ambassador rev share"""
    with boa.reverts("no perms"):
        switchboard_alpha.setAmbassadorRevShare(1000, 2000, 1500, sender=alice)


def test_set_ambassador_rev_share_maximum_allowed_values(switchboard_alpha, governance, mission_control):
    """Test setting ratios to exactly 100%"""
    aid = switchboard_alpha.setAmbassadorRevShare(10000, 10000, 10000, sender=governance.address)
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    config = mission_control.userWalletConfig()
    assert config.ambassadorRevShare.swapRatio == 10000
    assert config.ambassadorRevShare.rewardsRatio == 10000
    assert config.ambassadorRevShare.yieldRatio == 10000


def test_set_ambassador_rev_share_mixed_values(switchboard_alpha, governance, mission_control):
    """Test setting different ratios for each type"""
    aid = switchboard_alpha.setAmbassadorRevShare(
        5000,  # 50% swap
        2500,  # 25% rewards
        7500,  # 75% yield
        sender=governance.address
    )
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    config = mission_control.userWalletConfig()
    assert config.ambassadorRevShare.swapRatio == 5000
    assert config.ambassadorRevShare.rewardsRatio == 2500
    assert config.ambassadorRevShare.yieldRatio == 7500


##########################
# Default Yield Params   #
##########################


def test_set_default_yield_params_success(switchboard_alpha, governance, mission_control, alpha_token):
    """Test successful default yield parameters update"""
    # Set new params
    max_increase = 500  # 5% (max is 10%)
    performance_fee = 1000  # 10% (max is 25%)
    ambassador_bonus = 5000  # 50% (max is 100%)
    bonus_ratio = 1500  # 15% (max is 100%)
    alt_bonus_asset = alpha_token.address
    
    aid = switchboard_alpha.setDefaultYieldParams(
        max_increase,
        performance_fee,
        ambassador_bonus,
        bonus_ratio,
        alt_bonus_asset,
        sender=governance.address
    )
    
    # Verify event
    logs = filter_logs(switchboard_alpha, "PendingDefaultYieldParamsChange")
    assert len(logs) == 1
    assert logs[0].defaultYieldMaxIncrease == max_increase
    assert logs[0].defaultYieldPerformanceFee == performance_fee
    assert logs[0].defaultYieldAmbassadorBonusRatio == ambassador_bonus
    assert logs[0].defaultYieldBonusRatio == bonus_ratio
    assert logs[0].defaultYieldAltBonusAsset == alt_bonus_asset
    assert logs[0].actionId == aid
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify execution event
    exec_logs = filter_logs(switchboard_alpha, "DefaultYieldParamsSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].defaultYieldMaxIncrease == max_increase
    assert exec_logs[0].defaultYieldPerformanceFee == performance_fee
    assert exec_logs[0].defaultYieldAmbassadorBonusRatio == ambassador_bonus
    assert exec_logs[0].defaultYieldBonusRatio == bonus_ratio
    assert exec_logs[0].defaultYieldAltBonusAsset == alt_bonus_asset
    
    # Verify state changes
    updated_config = mission_control.userWalletConfig()
    assert updated_config.defaultYieldMaxIncrease == max_increase
    assert updated_config.defaultYieldPerformanceFee == performance_fee
    assert updated_config.defaultYieldAmbassadorBonusRatio == ambassador_bonus
    assert updated_config.defaultYieldBonusRatio == bonus_ratio
    assert updated_config.defaultYieldAltBonusAsset == alt_bonus_asset


def test_set_default_yield_params_invalid_values_revert(switchboard_alpha, governance, alpha_token):
    """Test that percentages exceeding their specific limits are rejected"""
    # Test max increase > 10%
    with boa.reverts("invalid default yield params"):
        switchboard_alpha.setDefaultYieldParams(1001, 0, 0, 0, alpha_token.address, sender=governance.address)
    
    # Test performance fee > 25%
    with boa.reverts("invalid default yield params"):
        switchboard_alpha.setDefaultYieldParams(0, 2501, 0, 0, alpha_token.address, sender=governance.address)
    
    # Test ambassador bonus > 100%
    with boa.reverts("invalid default yield params"):
        switchboard_alpha.setDefaultYieldParams(0, 0, 10001, 0, alpha_token.address, sender=governance.address)
    
    # Test bonus ratio > 100%
    with boa.reverts("invalid default yield params"):
        switchboard_alpha.setDefaultYieldParams(0, 0, 0, 10001, alpha_token.address, sender=governance.address)


def test_set_default_yield_params_zero_values_allowed(switchboard_alpha, governance, mission_control):
    """Test that zero values are allowed for all params"""
    aid = switchboard_alpha.setDefaultYieldParams(
        0, 0, 0, 0, ZERO_ADDRESS,
        sender=governance.address
    )
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    config = mission_control.userWalletConfig()
    assert config.defaultYieldMaxIncrease == 0
    assert config.defaultYieldPerformanceFee == 0
    assert config.defaultYieldAmbassadorBonusRatio == 0
    assert config.defaultYieldBonusRatio == 0
    assert config.defaultYieldAltBonusAsset == ZERO_ADDRESS


def test_set_default_yield_params_non_governance_reverts(switchboard_alpha, alice, alpha_token):
    """Test that non-governance addresses cannot set default yield params"""
    with boa.reverts("no perms"):
        switchboard_alpha.setDefaultYieldParams(
            2000, 1000, 500, 1500, alpha_token.address,
            sender=alice
        )


def test_set_default_yield_params_maximum_allowed_values(switchboard_alpha, governance, mission_control, alpha_token):
    """Test setting all percentages to their maximum allowed values"""
    aid = switchboard_alpha.setDefaultYieldParams(
        1000, 2500, 10000, 10000, alpha_token.address,
        sender=governance.address
    )
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    config = mission_control.userWalletConfig()
    assert config.defaultYieldMaxIncrease == 1000
    assert config.defaultYieldPerformanceFee == 2500
    assert config.defaultYieldAmbassadorBonusRatio == 10000
    assert config.defaultYieldBonusRatio == 10000
    assert config.defaultYieldAltBonusAsset == alpha_token.address


def test_set_default_yield_params_mixed_values(switchboard_alpha, governance, mission_control, alice):
    """Test setting different values including EOA address"""
    aid = switchboard_alpha.setDefaultYieldParams(
        500,   # 5% (max 10%)
        2500,  # 25% (max 25%)
        7500,  # 75% (max 100%)
        3333,  # 33.33% (max 100%)
        alice,  # EOA address allowed
        sender=governance.address
    )
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    config = mission_control.userWalletConfig()
    assert config.defaultYieldMaxIncrease == 500
    assert config.defaultYieldPerformanceFee == 2500
    assert config.defaultYieldAmbassadorBonusRatio == 7500
    assert config.defaultYieldBonusRatio == 3333
    assert config.defaultYieldAltBonusAsset == alice


def test_set_default_yield_params_edge_cases(switchboard_alpha, governance, mission_control, alpha_token):
    """Test setting yield params at their exact limits"""
    # Test max increase at exactly 10%
    aid = switchboard_alpha.setDefaultYieldParams(1000, 0, 0, 0, alpha_token.address, sender=governance.address)
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    assert switchboard_alpha.executePendingAction(aid, sender=governance.address) == True
    
    # Test performance fee at exactly 25%
    aid = switchboard_alpha.setDefaultYieldParams(0, 2500, 0, 0, alpha_token.address, sender=governance.address)
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    assert switchboard_alpha.executePendingAction(aid, sender=governance.address) == True
    
    # Test ambassador bonus at exactly 100%
    aid = switchboard_alpha.setDefaultYieldParams(0, 0, 10000, 0, alpha_token.address, sender=governance.address)
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    assert switchboard_alpha.executePendingAction(aid, sender=governance.address) == True
    
    # Test bonus ratio at exactly 100%
    aid = switchboard_alpha.setDefaultYieldParams(0, 0, 0, 10000, alpha_token.address, sender=governance.address)
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    assert switchboard_alpha.executePendingAction(aid, sender=governance.address) == True
    
    # Verify all params work at their limits simultaneously
    aid = switchboard_alpha.setDefaultYieldParams(1000, 2500, 10000, 10000, alpha_token.address, sender=governance.address)
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    assert switchboard_alpha.executePendingAction(aid, sender=governance.address) == True
    
    config = mission_control.userWalletConfig()
    assert config.defaultYieldMaxIncrease == 1000
    assert config.defaultYieldPerformanceFee == 2500
    assert config.defaultYieldAmbassadorBonusRatio == 10000
    assert config.defaultYieldBonusRatio == 10000
    assert config.defaultYieldAltBonusAsset == alpha_token.address


#################
# Loot Params   #
#################


def test_set_loot_params_success(switchboard_alpha, governance, mission_control, alpha_token):
    """Test successful loot parameters update"""
    # Set new params
    deposit_rewards_asset = alpha_token.address
    cool_off_period = 86400  # ~2 days in blocks
    
    aid = switchboard_alpha.setLootParams(
        deposit_rewards_asset,
        cool_off_period,
        sender=governance.address
    )
    
    # Verify event
    logs = filter_logs(switchboard_alpha, "PendingLootParamsChange")
    assert len(logs) == 1
    assert logs[0].depositRewardsAsset == deposit_rewards_asset
    assert logs[0].lootClaimCoolOffPeriod == cool_off_period
    assert logs[0].actionId == aid
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.LOOT_PARAMS
    pending_config = switchboard_alpha.pendingUserWalletConfig(aid)
    assert pending_config.depositRewardsAsset == deposit_rewards_asset
    assert pending_config.lootClaimCoolOffPeriod == cool_off_period
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify execution event
    exec_logs = filter_logs(switchboard_alpha, "LootParamsSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].depositRewardsAsset == deposit_rewards_asset
    assert exec_logs[0].lootClaimCoolOffPeriod == cool_off_period
    
    # Verify state changes
    updated_config = mission_control.userWalletConfig()
    assert updated_config.depositRewardsAsset == deposit_rewards_asset
    assert updated_config.lootClaimCoolOffPeriod == cool_off_period


def test_set_loot_params_invalid_cool_off_period_revert(switchboard_alpha, governance, alpha_token):
    """Test that invalid cool off periods are rejected"""
    # Test with 0
    with boa.reverts("invalid loot params"):
        switchboard_alpha.setLootParams(alpha_token.address, 0, sender=governance.address)
    
    # Test with max_value
    with boa.reverts("invalid loot params"):
        switchboard_alpha.setLootParams(alpha_token.address, MAX_UINT256, sender=governance.address)


def test_set_loot_params_zero_address_allowed(switchboard_alpha, governance, mission_control):
    """Test that zero address is allowed for depositRewardsAsset"""
    aid = switchboard_alpha.setLootParams(ZERO_ADDRESS, 43200, sender=governance.address)
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    config = mission_control.userWalletConfig()
    assert config.depositRewardsAsset == ZERO_ADDRESS
    assert config.lootClaimCoolOffPeriod == 43200


def test_set_loot_params_non_governance_reverts(switchboard_alpha, alice, alpha_token):
    """Test that non-governance addresses cannot set loot params"""
    with boa.reverts("no perms"):
        switchboard_alpha.setLootParams(alpha_token.address, 86400, sender=alice)


def test_set_loot_params_edge_cases(switchboard_alpha, governance, mission_control, alpha_token):
    """Test edge cases for loot params"""
    # Test with minimum valid cool off period (1)
    aid = switchboard_alpha.setLootParams(alpha_token.address, 1, sender=governance.address)
    
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


#################
# Asset Config  #
#################


def test_set_asset_config_success(switchboard_alpha, governance, mission_control, alpha_token):
    """Test successful asset configuration update"""
    # Set new asset config
    asset = alpha_token.address
    lego_id = 1  # Assuming valid lego ID
    stale_blocks = 100
    swap_fee = 30  # 0.3%
    stable_swap_fee = 10  # 0.1%
    rewards_fee = 50  # 0.5%
    ambassador_swap_ratio = 1000  # 10%
    ambassador_rewards_ratio = 2000  # 20%
    ambassador_yield_ratio = 1500  # 15%
    is_yield_asset = True
    is_rebasing = False
    underlying_asset = ZERO_ADDRESS
    max_yield_increase = 500  # 5%
    performance_fee = 1000  # 10%
    ambassador_bonus_ratio = 5000  # 50%
    bonus_ratio = 3000  # 30%
    alt_bonus_asset = ZERO_ADDRESS
    
    aid = switchboard_alpha.setAssetConfig(
        asset,
        lego_id,
        stale_blocks,
        swap_fee,
        stable_swap_fee,
        rewards_fee,
        ambassador_swap_ratio,
        ambassador_rewards_ratio,
        ambassador_yield_ratio,
        is_yield_asset,
        is_rebasing,
        underlying_asset,
        max_yield_increase,
        performance_fee,
        ambassador_bonus_ratio,
        bonus_ratio,
        alt_bonus_asset,
        sender=governance.address
    )
    
    # Verify event
    logs = filter_logs(switchboard_alpha, "PendingAssetConfigChange")
    assert len(logs) == 1
    assert logs[0].asset == asset
    assert logs[0].legoId == lego_id
    assert logs[0].staleBlocks == stale_blocks
    assert logs[0].txFeesSwapFee == swap_fee
    assert logs[0].txFeesStableSwapFee == stable_swap_fee
    assert logs[0].txFeesRewardsFee == rewards_fee
    assert logs[0].ambassadorRevShareSwapRatio == ambassador_swap_ratio
    assert logs[0].ambassadorRevShareRewardsRatio == ambassador_rewards_ratio
    assert logs[0].ambassadorRevShareYieldRatio == ambassador_yield_ratio
    assert logs[0].isYieldAsset == is_yield_asset
    assert logs[0].isRebasing == is_rebasing
    assert logs[0].underlyingAsset == underlying_asset
    assert logs[0].maxYieldIncrease == max_yield_increase
    assert logs[0].performanceFee == performance_fee
    assert logs[0].ambassadorBonusRatio == ambassador_bonus_ratio
    assert logs[0].bonusRatio == bonus_ratio
    assert logs[0].altBonusAsset == alt_bonus_asset
    assert logs[0].actionId == aid
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    
    # Verify execution event - must use filter_logs immediately after the transaction
    exec_logs = filter_logs(switchboard_alpha, "AssetConfigSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].asset == asset
    assert result == True
    
    # Verify the asset config was saved in MissionControl
    saved_config = mission_control.assetConfig(asset)
    assert saved_config.legoId == lego_id
    assert saved_config.decimals == 18  # Alpha token has 18 decimals
    assert saved_config.staleBlocks == stale_blocks
    
    # Verify tx fees
    assert saved_config.txFees.swapFee == swap_fee
    assert saved_config.txFees.stableSwapFee == stable_swap_fee
    assert saved_config.txFees.rewardsFee == rewards_fee
    
    # Verify ambassador rev share
    assert saved_config.ambassadorRevShare.swapRatio == ambassador_swap_ratio
    assert saved_config.ambassadorRevShare.rewardsRatio == ambassador_rewards_ratio
    assert saved_config.ambassadorRevShare.yieldRatio == ambassador_yield_ratio
    
    # Verify yield config
    assert saved_config.yieldConfig.isYieldAsset == is_yield_asset
    assert saved_config.yieldConfig.isRebasing == is_rebasing
    assert saved_config.yieldConfig.underlyingAsset == underlying_asset
    assert saved_config.yieldConfig.maxYieldIncrease == max_yield_increase
    assert saved_config.yieldConfig.performanceFee == performance_fee
    assert saved_config.yieldConfig.ambassadorBonusRatio == ambassador_bonus_ratio
    assert saved_config.yieldConfig.bonusRatio == bonus_ratio
    assert saved_config.yieldConfig.altBonusAsset == alt_bonus_asset


def test_set_asset_config_invalid_tx_fees_revert(switchboard_alpha, governance, alpha_token):
    """Test that asset config with invalid tx fees is rejected"""
    # Test swap fee > 5%
    with boa.reverts("invalid asset config"):
        switchboard_alpha.setAssetConfig(
            alpha_token.address, 1, 100, 501, 0, 0,  # swap fee too high
            0, 0, 0, False, False, ZERO_ADDRESS,
            0, 0, 0, 0, ZERO_ADDRESS,
            sender=governance.address
        )
    
    # Test stable swap fee > 2%
    with boa.reverts("invalid asset config"):
        switchboard_alpha.setAssetConfig(
            alpha_token.address, 1, 100, 0, 201, 0,  # stable swap fee too high
            0, 0, 0, False, False, ZERO_ADDRESS,
            0, 0, 0, 0, ZERO_ADDRESS,
            sender=governance.address
        )
    
    # Test rewards fee > 25%
    with boa.reverts("invalid asset config"):
        switchboard_alpha.setAssetConfig(
            alpha_token.address, 1, 100, 0, 0, 2501,  # rewards fee too high
            0, 0, 0, False, False, ZERO_ADDRESS,
            0, 0, 0, 0, ZERO_ADDRESS,
            sender=governance.address
        )


def test_set_asset_config_invalid_yield_params_revert(switchboard_alpha, governance, alpha_token):
    """Test that asset config with invalid yield params is rejected"""
    # Test max increase > 10%
    with boa.reverts("invalid asset config"):
        switchboard_alpha.setAssetConfig(
            alpha_token.address, 1, 100, 50, 10, 100,
            1000, 2000, 1500, True, False, ZERO_ADDRESS,
            1001, 0, 0, 0, ZERO_ADDRESS,  # max increase too high
            sender=governance.address
        )
    
    # Test performance fee > 25%
    with boa.reverts("invalid asset config"):
        switchboard_alpha.setAssetConfig(
            alpha_token.address, 1, 100, 50, 10, 100,
            1000, 2000, 1500, True, False, ZERO_ADDRESS,
            500, 2501, 0, 0, ZERO_ADDRESS,  # performance fee too high
            sender=governance.address
        )
    
    # Test ambassador bonus > 100%
    with boa.reverts("invalid asset config"):
        switchboard_alpha.setAssetConfig(
            alpha_token.address, 1, 100, 50, 10, 100,
            1000, 2000, 1500, True, False, ZERO_ADDRESS,
            500, 1000, 10001, 0, ZERO_ADDRESS,  # ambassador bonus too high
            sender=governance.address
        )
    
    # Test bonus ratio > 100%
    with boa.reverts("invalid asset config"):
        switchboard_alpha.setAssetConfig(
            alpha_token.address, 1, 100, 50, 10, 100,
            1000, 2000, 1500, True, False, ZERO_ADDRESS,
            500, 1000, 5000, 10001, ZERO_ADDRESS,  # bonus ratio too high
            sender=governance.address
        )


def test_set_asset_config_invalid_ambassador_rev_share_revert(switchboard_alpha, governance, alpha_token):
    """Test that asset config with invalid ambassador rev share is rejected"""
    # Test swap ratio > 100%
    with boa.reverts("invalid asset config"):
        switchboard_alpha.setAssetConfig(
            alpha_token.address, 1, 100, 50, 10, 100,
            10001, 0, 0, False, False, ZERO_ADDRESS,  # swap ratio too high
            0, 0, 0, 0, ZERO_ADDRESS,
            sender=governance.address
        )
    
    # Test rewards ratio > 100%
    with boa.reverts("invalid asset config"):
        switchboard_alpha.setAssetConfig(
            alpha_token.address, 1, 100, 50, 10, 100,
            0, 10001, 0, False, False, ZERO_ADDRESS,  # rewards ratio too high
            0, 0, 0, 0, ZERO_ADDRESS,
            sender=governance.address
        )
    
    # Test yield ratio > 100%
    with boa.reverts("invalid asset config"):
        switchboard_alpha.setAssetConfig(
            alpha_token.address, 1, 100, 50, 10, 100,
            0, 0, 10001, False, False, ZERO_ADDRESS,  # yield ratio too high
            0, 0, 0, 0, ZERO_ADDRESS,
            sender=governance.address
        )


def test_set_asset_config_invalid_asset_revert(switchboard_alpha, governance):
    """Test that asset config with invalid asset address is rejected"""
    with boa.reverts("invalid asset config"):
        switchboard_alpha.setAssetConfig(
            ZERO_ADDRESS, 1, 100, 50, 10, 100,  # zero address asset
            1000, 2000, 1500, False, False, ZERO_ADDRESS,
            0, 0, 0, 0, ZERO_ADDRESS,
            sender=governance.address
        )


def test_set_asset_config_invalid_stale_blocks_revert(switchboard_alpha, governance, alpha_token):
    """Test that asset config with invalid stale blocks is rejected"""
    # Test stale blocks = 0
    with boa.reverts("invalid asset config"):
        switchboard_alpha.setAssetConfig(
            alpha_token.address, 1, 0, 50, 10, 100,  # stale blocks = 0
            1000, 2000, 1500, False, False, ZERO_ADDRESS,
            0, 0, 0, 0, ZERO_ADDRESS,
            sender=governance.address
        )
    
    # Test stale blocks = max_value(uint256)
    with boa.reverts("invalid asset config"):
        switchboard_alpha.setAssetConfig(
            alpha_token.address, 1, 2**256 - 1, 50, 10, 100,  # stale blocks = max uint256
            1000, 2000, 1500, False, False, ZERO_ADDRESS,
            0, 0, 0, 0, ZERO_ADDRESS,
            sender=governance.address
        )


def test_set_asset_config_non_yield_asset(switchboard_alpha, governance, mission_control, alpha_token):
    """Test setting config for non-yield asset"""
    aid = switchboard_alpha.setAssetConfig(
        alpha_token.address, 1, 100, 50, 10, 100,
        1000, 2000, 1500, False, False, ZERO_ADDRESS,  # is_yield_asset = False
        999, 2499, 9999, 9999, alpha_token.address,  # These should be ignored
        sender=governance.address
    )
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    
    # Verify the yield config is empty when is_yield_asset is False
    exec_logs = filter_logs(switchboard_alpha, "AssetConfigSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].isYieldAsset == False
    assert exec_logs[0].maxYieldIncrease == 0
    assert exec_logs[0].performanceFee == 0
    assert exec_logs[0].ambassadorBonusRatio == 0
    assert exec_logs[0].bonusRatio == 0
    assert exec_logs[0].altBonusAsset == ZERO_ADDRESS
    assert result == True
    
    # Verify the config was saved in MissionControl
    saved_config = mission_control.assetConfig(alpha_token.address)
    assert saved_config.legoId == 1
    assert saved_config.staleBlocks == 100
    assert saved_config.txFees.swapFee == 50
    assert saved_config.txFees.stableSwapFee == 10
    assert saved_config.txFees.rewardsFee == 100
    assert saved_config.ambassadorRevShare.swapRatio == 1000
    assert saved_config.ambassadorRevShare.rewardsRatio == 2000
    assert saved_config.ambassadorRevShare.yieldRatio == 1500
    
    # Verify yield config is not set when is_yield_asset is False
    assert saved_config.yieldConfig.isYieldAsset == False
    assert saved_config.yieldConfig.isRebasing == False
    assert saved_config.yieldConfig.underlyingAsset == ZERO_ADDRESS
    assert saved_config.yieldConfig.maxYieldIncrease == 0
    assert saved_config.yieldConfig.performanceFee == 0
    assert saved_config.yieldConfig.ambassadorBonusRatio == 0
    assert saved_config.yieldConfig.bonusRatio == 0
    assert saved_config.yieldConfig.altBonusAsset == ZERO_ADDRESS


def test_set_asset_config_maximum_allowed_values(switchboard_alpha, governance, mission_control, alpha_token):
    """Test setting all percentages to their maximum allowed values"""
    aid = switchboard_alpha.setAssetConfig(
        alpha_token.address, 1, 100,
        500, 200, 2500,  # Max tx fees: 5%, 2%, 25%
        10000, 10000, 10000,  # Max ambassador rev share: 100% each
        True, False, ZERO_ADDRESS,
        1000, 2500, 10000, 10000, alpha_token.address,  # Max yield params: 10%, 25%, 100%, 100%
        sender=governance.address
    )
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    
    exec_logs = filter_logs(switchboard_alpha, "AssetConfigSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].txFeesSwapFee == 500
    assert exec_logs[0].txFeesStableSwapFee == 200
    assert exec_logs[0].txFeesRewardsFee == 2500
    assert exec_logs[0].ambassadorRevShareSwapRatio == 10000
    assert exec_logs[0].ambassadorRevShareRewardsRatio == 10000
    assert exec_logs[0].ambassadorRevShareYieldRatio == 10000
    assert exec_logs[0].maxYieldIncrease == 1000
    assert exec_logs[0].performanceFee == 2500
    assert exec_logs[0].ambassadorBonusRatio == 10000
    assert exec_logs[0].bonusRatio == 10000
    assert result == True
    
    # Verify all max values were saved in MissionControl
    saved_config = mission_control.assetConfig(alpha_token.address)
    assert saved_config.txFees.swapFee == 500
    assert saved_config.txFees.stableSwapFee == 200
    assert saved_config.txFees.rewardsFee == 2500
    assert saved_config.ambassadorRevShare.swapRatio == 10000
    assert saved_config.ambassadorRevShare.rewardsRatio == 10000
    assert saved_config.ambassadorRevShare.yieldRatio == 10000
    assert saved_config.yieldConfig.maxYieldIncrease == 1000
    assert saved_config.yieldConfig.performanceFee == 2500
    assert saved_config.yieldConfig.ambassadorBonusRatio == 10000
    assert saved_config.yieldConfig.bonusRatio == 10000


def test_set_asset_config_non_governance_reverts(switchboard_alpha, alice, alpha_token):
    """Test that non-governance addresses cannot set asset config"""
    with boa.reverts("no perms"):
        switchboard_alpha.setAssetConfig(
            alpha_token.address, 1, 100, 50, 10, 100,
            1000, 2000, 1500, False, False, ZERO_ADDRESS,
            0, 0, 0, 0, ZERO_ADDRESS,
            sender=alice
        )


def test_set_asset_config_edge_case_stale_blocks(switchboard_alpha, governance, mission_control, alpha_token):
    """Test setting asset config with edge case stale blocks values"""
    # Test with stale blocks = 1 (minimum valid value)
    aid = switchboard_alpha.setAssetConfig(
        alpha_token.address, 1, 1, 50, 10, 100,  # stale blocks = 1
        1000, 2000, 1500, False, False, ZERO_ADDRESS,
        0, 0, 0, 0, ZERO_ADDRESS,
        sender=governance.address
    )
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    
    # Must use filter_logs immediately after the transaction
    exec_logs = filter_logs(switchboard_alpha, "AssetConfigSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].staleBlocks == 1
    assert result == True
    
    # Verify MissionControl saved the minimum stale blocks value
    saved_config = mission_control.assetConfig(alpha_token.address)
    assert saved_config.staleBlocks == 1
    
    # Test with stale blocks = max_value - 1 (maximum valid value)
    aid = switchboard_alpha.setAssetConfig(
        alpha_token.address, 1, 2**256 - 2, 50, 10, 100,  # stale blocks = max - 1
        1000, 2000, 1500, False, False, ZERO_ADDRESS,
        0, 0, 0, 0, ZERO_ADDRESS,
        sender=governance.address
    )
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    
    # Must use filter_logs immediately after the transaction
    exec_logs2 = filter_logs(switchboard_alpha, "AssetConfigSet")
    assert len(exec_logs2) == 1
    assert exec_logs2[0].staleBlocks == 2**256 - 2
    assert result == True
    
    # Verify MissionControl saved the maximum stale blocks value
    saved_config2 = mission_control.assetConfig(alpha_token.address)
    assert saved_config2.staleBlocks == 2**256 - 2


##################
# Is Stablecoin  #
##################


def test_set_is_stablecoin_success(switchboard_alpha, governance, mission_control, alpha_token):
    """Test successful isStablecoin flag update"""
    # Set alpha_token as a stablecoin
    aid = switchboard_alpha.setIsStablecoin(
        alpha_token.address,
        True,
        sender=governance.address
    )
    
    # Verify event
    logs = filter_logs(switchboard_alpha, "PendingIsStablecoinChange")
    assert len(logs) == 1
    assert logs[0].asset == alpha_token.address
    assert logs[0].isStablecoin == True
    assert logs[0].actionId == aid
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.IS_STABLECOIN
    pending_data = switchboard_alpha.pendingAddrToBool(aid)
    assert pending_data.addr == alpha_token.address
    assert pending_data.isAllowed == True
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    
    # Verify execution event - must use filter_logs immediately after the transaction
    exec_logs = filter_logs(switchboard_alpha, "IsStablecoinSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].asset == alpha_token.address
    assert exec_logs[0].isStablecoin == True
    assert result == True
    
    # Verify the stablecoin flag was saved in MissionControl
    assert mission_control.isStablecoin(alpha_token.address) == True
    
    # Verify action is cleared
    assert switchboard_alpha.actionType(aid) == 0


def test_set_is_stablecoin_false(switchboard_alpha, governance, mission_control, alpha_token):
    """Test setting isStablecoin to false"""
    # First set it to true
    aid1 = switchboard_alpha.setIsStablecoin(alpha_token.address, True, sender=governance.address)
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    switchboard_alpha.executePendingAction(aid1, sender=governance.address)
    assert mission_control.isStablecoin(alpha_token.address) == True
    
    # Now set it back to false
    aid2 = switchboard_alpha.setIsStablecoin(
        alpha_token.address,
        False,
        sender=governance.address
    )
    
    # Verify event
    logs = filter_logs(switchboard_alpha, "PendingIsStablecoinChange")
    assert len(logs) == 1
    assert logs[0].asset == alpha_token.address
    assert logs[0].isStablecoin == False
    assert logs[0].actionId == aid2
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid2, sender=governance.address)
    
    # Verify execution event
    exec_logs = filter_logs(switchboard_alpha, "IsStablecoinSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].asset == alpha_token.address
    assert exec_logs[0].isStablecoin == False
    assert result == True
    
    # Verify the stablecoin flag was updated in MissionControl
    assert mission_control.isStablecoin(alpha_token.address) == False


def test_set_is_stablecoin_zero_address(switchboard_alpha, governance, mission_control):
    """Test setting isStablecoin for zero address"""
    # This should be allowed as there's no validation preventing it
    aid = switchboard_alpha.setIsStablecoin(
        ZERO_ADDRESS,
        True,
        sender=governance.address
    )
    
    # Verify it goes through
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify MissionControl stored it
    assert mission_control.isStablecoin(ZERO_ADDRESS) == True


def test_set_is_stablecoin_non_governance_reverts(switchboard_alpha, alice, alpha_token):
    """Test that non-governance addresses cannot set isStablecoin"""
    with boa.reverts("no perms"):
        switchboard_alpha.setIsStablecoin(
            alpha_token.address,
            True,
            sender=alice
        )


def test_set_is_stablecoin_multiple_pending(switchboard_alpha, governance, mission_control, alpha_token, wallet_template_v2):
    """Test multiple pending isStablecoin updates"""
    # Create first pending action
    aid1 = switchboard_alpha.setIsStablecoin(
        alpha_token.address,
        True,
        sender=governance.address
    )
    
    # Create second pending action for different asset
    aid2 = switchboard_alpha.setIsStablecoin(
        wallet_template_v2.address,
        True,
        sender=governance.address
    )
    
    # Verify different action IDs
    assert aid1 != aid2
    
    # Verify both are pending
    assert switchboard_alpha.actionType(aid1) == CONFIG_ACTION_TYPE.IS_STABLECOIN
    assert switchboard_alpha.actionType(aid2) == CONFIG_ACTION_TYPE.IS_STABLECOIN
    
    # Execute second action first
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result2 = switchboard_alpha.executePendingAction(aid2, sender=governance.address)
    assert result2 == True
    assert mission_control.isStablecoin(wallet_template_v2.address) == True
    assert mission_control.isStablecoin(alpha_token.address) == False  # Not yet executed
    
    # Execute first action
    result1 = switchboard_alpha.executePendingAction(aid1, sender=governance.address)
    assert result1 == True
    assert mission_control.isStablecoin(alpha_token.address) == True


def test_cancel_pending_is_stablecoin(switchboard_alpha, governance, mission_control, alpha_token):
    """Test canceling a pending isStablecoin update"""
    # Create pending action
    aid = switchboard_alpha.setIsStablecoin(
        alpha_token.address,
        True,
        sender=governance.address
    )
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.IS_STABLECOIN
    
    # Cancel the pending action
    result = switchboard_alpha.cancelPendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify action is cleared
    assert switchboard_alpha.actionType(aid) == 0
    
    # Try to execute canceled action - should fail
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Verify isStablecoin wasn't set
    assert mission_control.isStablecoin(alpha_token.address) == False


def test_execute_expired_is_stablecoin(switchboard_alpha, governance, mission_control, alpha_token):
    """Test that expired isStablecoin actions auto-cancel"""
    # Create pending action
    aid = switchboard_alpha.setIsStablecoin(
        alpha_token.address,
        True,
        sender=governance.address
    )
    
    # Time travel past expiration
    max_timelock = switchboard_alpha.maxActionTimeLock()
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock() + max_timelock + 1)
    
    # Try to execute - should auto-cancel and return False
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Verify action is cleared
    assert switchboard_alpha.actionType(aid) == 0
    
    # Verify isStablecoin wasn't set
    assert mission_control.isStablecoin(alpha_token.address) == False


def test_set_is_stablecoin_eoa_address(switchboard_alpha, governance, mission_control, alice):
    """Test setting isStablecoin for an EOA address"""
    # This should be allowed as there's no validation preventing it
    aid = switchboard_alpha.setIsStablecoin(
        alice,
        True,
        sender=governance.address
    )
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify MissionControl stored it
    assert mission_control.isStablecoin(alice) == True


##################
# Agent Template #
##################


def test_set_agent_template_success(switchboard_alpha, governance, mission_control, agent_template_v2):
    """Test successful agent template update through full lifecycle"""
    # Get initial config from MissionControl
    initial_config = mission_control.agentConfig()
    initial_agent_template = initial_config.agentTemplate
    
    # Step 1: Initiate template change
    aid = switchboard_alpha.setAgentTemplate(
        agent_template_v2.address,
        sender=governance.address
    )
    
    # Step 2: Verify event was emitted
    logs = filter_logs(switchboard_alpha, "PendingAgentTemplateChange")
    assert len(logs) == 1
    assert logs[0].agentTemplate == agent_template_v2.address
    assert logs[0].actionId == aid
    # Confirmation block should be current block + timelock
    expected_confirmation_block = boa.env.evm.patch.block_number + switchboard_alpha.actionTimeLock()
    assert logs[0].confirmationBlock == expected_confirmation_block
    
    # Step 3: Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.AGENT_TEMPLATE
    pending_config = switchboard_alpha.pendingAgentConfig(aid)
    assert pending_config.agentTemplate == agent_template_v2.address
    
    # Verify the action confirmation block matches what we expect
    assert switchboard_alpha.getActionConfirmationBlock(aid) == expected_confirmation_block
    
    # Step 4: Try to execute before timelock - should fail silently
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Verify no state change
    current_config = mission_control.agentConfig()
    assert current_config.agentTemplate == initial_agent_template
    
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
    exec_logs = filter_logs(switchboard_alpha, "AgentTemplateSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].agentTemplate == agent_template_v2.address
    
    # Step 8: Verify state changes in MissionControl
    updated_config = mission_control.agentConfig()
    assert updated_config.agentTemplate == agent_template_v2.address
    
    # Verify other config fields remain unchanged
    assert updated_config.numAgentsAllowed == initial_config.numAgentsAllowed
    assert updated_config.enforceCreatorWhitelist == initial_config.enforceCreatorWhitelist
    
    # Step 9: Verify action is cleared
    assert switchboard_alpha.actionType(aid) == 0  # empty(ActionType)
    # Note: pendingAgentConfig mapping is not cleared after execution


def test_set_agent_template_non_governance_reverts(switchboard_alpha, alice, agent_template_v2):
    """Test that non-governance addresses cannot set agent template"""
    with boa.reverts("no perms"):
        switchboard_alpha.setAgentTemplate(
            agent_template_v2.address,
            sender=alice
        )


def test_set_agent_template_invalid_addresses_revert(switchboard_alpha, governance, alice):
    """Test various invalid address scenarios"""
    # Test with zero address
    with boa.reverts("invalid agent template"):
        switchboard_alpha.setAgentTemplate(ZERO_ADDRESS, sender=governance.address)
    
    # Test with EOA
    with boa.reverts("invalid agent template"):
        switchboard_alpha.setAgentTemplate(alice, sender=governance.address)


def test_cancel_pending_agent_template_update(switchboard_alpha, governance, mission_control, agent_template_v2):
    """Test canceling a pending agent template update"""
    # Get initial config
    initial_config = mission_control.agentConfig()
    
    # Initiate template change
    aid = switchboard_alpha.setAgentTemplate(
        agent_template_v2.address,
        sender=governance.address
    )
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.AGENT_TEMPLATE
    
    # Cancel the pending action
    result = switchboard_alpha.cancelPendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify action is cleared
    assert switchboard_alpha.actionType(aid) == 0  # empty(ActionType)
    
    # Try to execute canceled action - should fail
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Verify config hasn't changed
    final_config = mission_control.agentConfig()
    assert final_config.agentTemplate == initial_config.agentTemplate


def test_execute_expired_agent_template_update(switchboard_alpha, governance, mission_control, agent_template_v2):
    """Test that expired actions auto-cancel and cannot be executed"""
    # Get initial config
    initial_config = mission_control.agentConfig()
    
    # Initiate template change
    aid = switchboard_alpha.setAgentTemplate(
        agent_template_v2.address,
        sender=governance.address
    )
    
    # Time travel past expiration (timelock + max timelock)
    max_timelock = switchboard_alpha.maxActionTimeLock()
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock() + max_timelock + 1)
    
    # Try to execute - should auto-cancel and return False
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Verify action is cleared
    assert switchboard_alpha.actionType(aid) == 0  # empty(ActionType)
    
    # Verify config hasn't changed
    final_config = mission_control.agentConfig()
    assert final_config.agentTemplate == initial_config.agentTemplate


def test_multiple_pending_agent_template_updates(switchboard_alpha, governance, mission_control):
    """Test creating multiple pending updates with different action IDs"""
    # Deploy multiple template sets
    template1 = boa.load_partial("contracts/core/agent/AgentWrapper.vy").deploy_as_blueprint()
    template2 = boa.load_partial("contracts/core/agent/AgentWrapper.vy").deploy_as_blueprint()
    
    # Create first pending action
    aid1 = switchboard_alpha.setAgentTemplate(
        template1.address,
        sender=governance.address
    )
    
    # Create second pending action
    aid2 = switchboard_alpha.setAgentTemplate(
        template2.address,
        sender=governance.address
    )
    
    # Verify different action IDs
    assert aid1 != aid2
    
    # Verify both are pending
    assert switchboard_alpha.actionType(aid1) == CONFIG_ACTION_TYPE.AGENT_TEMPLATE
    assert switchboard_alpha.actionType(aid2) == CONFIG_ACTION_TYPE.AGENT_TEMPLATE
    
    # Verify different pending configs
    pending1 = switchboard_alpha.pendingAgentConfig(aid1)
    pending2 = switchboard_alpha.pendingAgentConfig(aid2)
    assert pending1.agentTemplate == template1.address
    assert pending2.agentTemplate == template2.address
    
    # Execute second action first
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid2, sender=governance.address)
    assert result == True
    
    # Verify config updated to second template
    config = mission_control.agentConfig()
    assert config.agentTemplate == template2.address
    
    # First action should still be pending
    assert switchboard_alpha.actionType(aid1) == CONFIG_ACTION_TYPE.AGENT_TEMPLATE
    
    # Execute first action
    result = switchboard_alpha.executePendingAction(aid1, sender=governance.address)
    assert result == True
    
    # Verify config updated to first template
    final_config = mission_control.agentConfig()
    assert final_config.agentTemplate == template1.address


def test_set_agent_template_mixed_with_user_wallet_updates(switchboard_alpha, governance, mission_control, agent_template_v2, wallet_template_v2, config_template_v2):
    """Test that agent template and user wallet template updates can coexist as separate actions"""
    # Create pending user wallet template update
    aid1 = switchboard_alpha.setUserWalletTemplates(
        wallet_template_v2.address,
        config_template_v2.address,
        sender=governance.address
    )
    
    # Create pending agent template update
    aid2 = switchboard_alpha.setAgentTemplate(
        agent_template_v2.address,
        sender=governance.address
    )
    
    # Verify different action types
    assert switchboard_alpha.actionType(aid1) == CONFIG_ACTION_TYPE.USER_WALLET_TEMPLATES
    assert switchboard_alpha.actionType(aid2) == CONFIG_ACTION_TYPE.AGENT_TEMPLATE
    
    # Execute agent template first
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid2, sender=governance.address)
    assert result == True
    
    # Verify only agent template changed
    agent_config = mission_control.agentConfig()
    assert agent_config.agentTemplate == agent_template_v2.address
    
    # User wallet templates should be unchanged
    user_config = mission_control.userWalletConfig()
    initial_user_config = mission_control.userWalletConfig()
    assert user_config.walletTemplate == initial_user_config.walletTemplate
    
    # Execute user wallet template update
    result = switchboard_alpha.executePendingAction(aid1, sender=governance.address)
    assert result == True
    
    # Verify both changes are applied
    final_user_config = mission_control.userWalletConfig()
    assert final_user_config.walletTemplate == wallet_template_v2.address
    assert final_user_config.configTemplate == config_template_v2.address
    
    final_agent_config = mission_control.agentConfig()
    assert final_agent_config.agentTemplate == agent_template_v2.address


#########################
# Agent Creation Limits #
#########################


def test_set_agent_creation_limits_success(switchboard_alpha, governance, mission_control):
    """Test successful agent creation limits update"""
    # Get initial config
    initial_config = mission_control.agentConfig()
    
    # Set new limits
    aid = switchboard_alpha.setAgentCreationLimits(
        5,  # numAgentsAllowed
        True,  # enforceCreatorWhitelist
        sender=governance.address
    )
    
    # Verify event
    logs = filter_logs(switchboard_alpha, "PendingAgentCreationLimitsChange")
    assert len(logs) == 1
    assert logs[0].numAgentsAllowed == 5
    assert logs[0].enforceCreatorWhitelist == True
    assert logs[0].actionId == aid
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.AGENT_CREATION_LIMITS
    pending_config = switchboard_alpha.pendingAgentConfig(aid)
    assert pending_config.numAgentsAllowed == 5
    assert pending_config.enforceCreatorWhitelist == True
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify execution event
    exec_logs = filter_logs(switchboard_alpha, "AgentCreationLimitsSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].numAgentsAllowed == 5
    assert exec_logs[0].enforceCreatorWhitelist == True
    
    # Verify state changes
    updated_config = mission_control.agentConfig()
    assert updated_config.numAgentsAllowed == 5
    assert updated_config.enforceCreatorWhitelist == True
    
    # Verify other fields unchanged
    assert updated_config.agentTemplate == initial_config.agentTemplate
    assert updated_config.startingAgent == initial_config.startingAgent


def test_set_agent_creation_limits_extreme_values(switchboard_alpha, governance, mission_control):
    """Test setting extreme but valid values"""
    # Test with 1 agent allowed
    aid = switchboard_alpha.setAgentCreationLimits(
        1,  # Minimum valid value
        False,
        sender=governance.address
    )
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    config = mission_control.agentConfig()
    assert config.numAgentsAllowed == 1
    assert config.enforceCreatorWhitelist == False
    
    # Test with very large number
    large_num = 2**256 - 2  # max_value - 1
    aid2 = switchboard_alpha.setAgentCreationLimits(
        large_num,
        True,
        sender=governance.address
    )
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid2, sender=governance.address)
    assert result == True
    
    final_config = mission_control.agentConfig()
    assert final_config.numAgentsAllowed == large_num
    assert final_config.enforceCreatorWhitelist == True


def test_set_agent_creation_limits_invalid_values_revert(switchboard_alpha, governance):
    """Test that invalid values are rejected"""
    # Test with 0
    with boa.reverts("invalid num agents allowed"):
        switchboard_alpha.setAgentCreationLimits(0, False, sender=governance.address)
    
    # Test with max_value
    with boa.reverts("invalid num agents allowed"):
        switchboard_alpha.setAgentCreationLimits(MAX_UINT256, False, sender=governance.address)


def test_set_agent_creation_limits_non_governance_reverts(switchboard_alpha, alice):
    """Test that non-governance addresses cannot set agent creation limits"""
    with boa.reverts("no perms"):
        switchboard_alpha.setAgentCreationLimits(5, True, sender=alice)


def test_set_agent_creation_limits_mixed_with_template_update(switchboard_alpha, governance, mission_control, agent_template_v2):
    """Test that agent creation limits can be updated alongside agent template"""
    # Set agent creation limits
    aid1 = switchboard_alpha.setAgentCreationLimits(3, True, sender=governance.address)
    
    # Set agent template
    aid2 = switchboard_alpha.setAgentTemplate(agent_template_v2.address, sender=governance.address)
    
    # Execute both
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    
    result1 = switchboard_alpha.executePendingAction(aid1, sender=governance.address)
    assert result1 == True
    
    result2 = switchboard_alpha.executePendingAction(aid2, sender=governance.address)
    assert result2 == True
    
    # Verify both changes applied
    config = mission_control.agentConfig()
    assert config.numAgentsAllowed == 3
    assert config.enforceCreatorWhitelist == True
    assert config.agentTemplate == agent_template_v2.address


########################
# Starter Agent Params #
########################


def test_set_starter_agent_params_success(switchboard_alpha, governance, mission_control, alice):
    """Test successful starter agent params update"""
    # Get initial config
    initial_config = mission_control.agentConfig()
    
    # Set starter agent params
    activation_length = 86400  # ~2 days in blocks
    aid = switchboard_alpha.setStarterAgentParams(
        alice,  # startingAgent
        activation_length,  # startingAgentActivationLength
        sender=governance.address
    )
    
    # Verify event
    logs = filter_logs(switchboard_alpha, "PendingStarterAgentParamsChange")
    assert len(logs) == 1
    assert logs[0].startingAgent == alice
    assert logs[0].startingAgentActivationLength == activation_length
    assert logs[0].actionId == aid
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.STARTER_AGENT_PARAMS
    pending_config = switchboard_alpha.pendingAgentConfig(aid)
    assert pending_config.startingAgent == alice
    assert pending_config.startingAgentActivationLength == activation_length
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify execution event
    exec_logs = filter_logs(switchboard_alpha, "StarterAgentParamsSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].startingAgent == alice
    assert exec_logs[0].startingAgentActivationLength == activation_length
    
    # Verify state changes
    updated_config = mission_control.agentConfig()
    assert updated_config.startingAgent == alice
    assert updated_config.startingAgentActivationLength == activation_length
    
    # Verify other fields unchanged
    assert updated_config.agentTemplate == initial_config.agentTemplate
    assert updated_config.numAgentsAllowed == initial_config.numAgentsAllowed


def test_set_starter_agent_params_disable_starter_agent(switchboard_alpha, governance, mission_control):
    """Test disabling starter agent by setting zero address"""
    # First set a starter agent
    aid1 = switchboard_alpha.setStarterAgentParams(
        boa.env.generate_address(),
        43200,  # ~1 day
        sender=governance.address
    )
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid1, sender=governance.address)
    assert result == True
    
    # Now disable by setting zero address and zero activation length
    aid2 = switchboard_alpha.setStarterAgentParams(
        ZERO_ADDRESS,
        0,
        sender=governance.address
    )
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid2, sender=governance.address)
    assert result == True
    
    # Verify starter agent is disabled
    config = mission_control.agentConfig()
    assert config.startingAgent == ZERO_ADDRESS
    assert config.startingAgentActivationLength == 0


def test_set_starter_agent_params_invalid_combinations_revert(switchboard_alpha, governance, alice):
    """Test that invalid combinations are rejected"""
    # Test with non-zero address but zero activation length
    with boa.reverts("invalid starter agent params"):
        switchboard_alpha.setStarterAgentParams(alice, 0, sender=governance.address)
    
    # Test with zero address but non-zero activation length
    with boa.reverts("invalid starter agent params"):
        switchboard_alpha.setStarterAgentParams(ZERO_ADDRESS, 86400, sender=governance.address)
    
    # Test with max_value activation length
    with boa.reverts("invalid starter agent params"):
        switchboard_alpha.setStarterAgentParams(alice, MAX_UINT256, sender=governance.address)


def test_set_starter_agent_params_non_governance_reverts(switchboard_alpha, alice, bob):
    """Test that non-governance addresses cannot set starter agent params"""
    with boa.reverts("no perms"):
        switchboard_alpha.setStarterAgentParams(bob, 86400, sender=alice)


def test_set_starter_agent_params_edge_cases(switchboard_alpha, governance, mission_control, alice):
    """Test edge cases for starter agent params"""
    # Test with minimum activation length (1)
    aid1 = switchboard_alpha.setStarterAgentParams(alice, 1, sender=governance.address)
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid1, sender=governance.address)
    assert result == True
    
    config = mission_control.agentConfig()
    assert config.startingAgent == alice
    assert config.startingAgentActivationLength == 1
    
    # Test with large activation length (but not max)
    large_length = 2**256 - 2
    aid2 = switchboard_alpha.setStarterAgentParams(
        boa.env.generate_address(),
        large_length,
        sender=governance.address
    )
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid2, sender=governance.address)
    assert result == True
    
    final_config = mission_control.agentConfig()
    assert final_config.startingAgentActivationLength == large_length


def test_set_starter_agent_params_with_contract_address(switchboard_alpha, governance, mission_control, agent_template_v2):
    """Test setting a contract address as starter agent"""
    activation_length = 172800  # ~4 days
    aid = switchboard_alpha.setStarterAgentParams(
        agent_template_v2.address,  # Using a contract address
        activation_length,
        sender=governance.address
    )
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    config = mission_control.agentConfig()
    assert config.startingAgent == agent_template_v2.address
    assert config.startingAgentActivationLength == activation_length


##################
# Manager Config #
##################


def test_set_manager_config_success(switchboard_alpha, governance, mission_control):
    """Test successful manager config update through full lifecycle"""
    # Get initial config
    initial_config = mission_control.managerConfig()
    
    # Set new manager config
    new_manager_period = 86400  # ~2 days in blocks
    new_activation_length = 43200  # ~1 day in blocks
    
    aid = switchboard_alpha.setManagerConfig(
        new_manager_period,
        new_activation_length,
        sender=governance.address
    )
    
    # Verify event was emitted
    logs = filter_logs(switchboard_alpha, "PendingManagerConfigChange")
    assert len(logs) == 1
    assert logs[0].managerPeriod == new_manager_period
    assert logs[0].managerActivationLength == new_activation_length
    assert logs[0].actionId == aid
    expected_confirmation_block = boa.env.evm.patch.block_number + switchboard_alpha.actionTimeLock()
    assert logs[0].confirmationBlock == expected_confirmation_block
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.MANAGER_CONFIG
    pending_config = switchboard_alpha.pendingManagerConfig(aid)
    assert pending_config.managerPeriod == new_manager_period
    assert pending_config.managerActivationLength == new_activation_length
    
    # Try to execute before timelock - should fail
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Verify no state change
    current_config = mission_control.managerConfig()
    assert current_config.managerPeriod == initial_config.managerPeriod
    assert current_config.managerActivationLength == initial_config.managerActivationLength
    
    # Time travel to reach timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    
    # Execute the action
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify execution event
    exec_logs = filter_logs(switchboard_alpha, "ManagerConfigSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].managerPeriod == new_manager_period
    assert exec_logs[0].managerActivationLength == new_activation_length
    
    # Verify state changes in MissionControl
    updated_config = mission_control.managerConfig()
    assert updated_config.managerPeriod == new_manager_period
    assert updated_config.managerActivationLength == new_activation_length
    
    # Verify action is cleared
    assert switchboard_alpha.actionType(aid) == 0


def test_set_manager_config_invalid_params_revert(switchboard_alpha, governance):
    """Test that invalid manager config parameters are rejected"""
    # Test with zero manager period
    with boa.reverts("invalid manager config"):
        switchboard_alpha.setManagerConfig(0, 86400, sender=governance.address)
    
    # Test with zero activation length
    with boa.reverts("invalid manager config"):
        switchboard_alpha.setManagerConfig(86400, 0, sender=governance.address)
    
    # Test with both zero
    with boa.reverts("invalid manager config"):
        switchboard_alpha.setManagerConfig(0, 0, sender=governance.address)
    
    # Test with max_value manager period
    with boa.reverts("invalid manager config"):
        switchboard_alpha.setManagerConfig(MAX_UINT256, 86400, sender=governance.address)
    
    # Test with max_value activation length
    with boa.reverts("invalid manager config"):
        switchboard_alpha.setManagerConfig(86400, MAX_UINT256, sender=governance.address)
    
    # Test with both max_value
    with boa.reverts("invalid manager config"):
        switchboard_alpha.setManagerConfig(MAX_UINT256, MAX_UINT256, sender=governance.address)


def test_set_manager_config_non_governance_reverts(switchboard_alpha, alice):
    """Test that non-governance addresses cannot set manager config"""
    with boa.reverts("no perms"):
        switchboard_alpha.setManagerConfig(86400, 43200, sender=alice)


def test_set_manager_config_edge_cases(switchboard_alpha, governance, mission_control):
    """Test edge cases for manager config"""
    # Test with minimum values (1, 1)
    aid1 = switchboard_alpha.setManagerConfig(1, 1, sender=governance.address)
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid1, sender=governance.address)
    assert result == True
    
    config = mission_control.managerConfig()
    assert config.managerPeriod == 1
    assert config.managerActivationLength == 1
    
    # Test with large values (but not max)
    large_period = 2**256 - 2
    large_activation = 2**256 - 3
    aid2 = switchboard_alpha.setManagerConfig(large_period, large_activation, sender=governance.address)
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid2, sender=governance.address)
    assert result == True
    
    final_config = mission_control.managerConfig()
    assert final_config.managerPeriod == large_period
    assert final_config.managerActivationLength == large_activation


def test_set_manager_config_multiple_pending_actions(switchboard_alpha, governance, mission_control):
    """Test creating multiple pending manager config actions"""
    # Create first pending action
    aid1 = switchboard_alpha.setManagerConfig(100000, 50000, sender=governance.address)
    
    # Create second pending action with different values
    aid2 = switchboard_alpha.setManagerConfig(200000, 100000, sender=governance.address)
    
    # Verify both are stored separately
    pending1 = switchboard_alpha.pendingManagerConfig(aid1)
    pending2 = switchboard_alpha.pendingManagerConfig(aid2)
    
    assert pending1.managerPeriod == 100000
    assert pending1.managerActivationLength == 50000
    assert pending2.managerPeriod == 200000
    assert pending2.managerActivationLength == 100000
    
    # Execute second action first
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid2, sender=governance.address)
    assert result == True
    
    config = mission_control.managerConfig()
    assert config.managerPeriod == 200000
    assert config.managerActivationLength == 100000
    
    # Execute first action
    result = switchboard_alpha.executePendingAction(aid1, sender=governance.address)
    assert result == True
    
    # Verify it overwrites with first action's values
    final_config = mission_control.managerConfig()
    assert final_config.managerPeriod == 100000
    assert final_config.managerActivationLength == 50000


def test_set_manager_config_cancel_pending_action(switchboard_alpha, governance, mission_control):
    """Test canceling a pending manager config action"""
    # Get initial config
    initial_config = mission_control.managerConfig()
    
    # Create pending action
    aid = switchboard_alpha.setManagerConfig(150000, 75000, sender=governance.address)
    
    # Cancel the action
    result = switchboard_alpha.cancelPendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify action is cleared
    assert switchboard_alpha.actionType(aid) == 0
    
    # Try to execute cancelled action after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Verify config remains unchanged
    current_config = mission_control.managerConfig()
    assert current_config.managerPeriod == initial_config.managerPeriod
    assert current_config.managerActivationLength == initial_config.managerActivationLength


################
# Payee Config #
################


def test_set_payee_config_success(switchboard_alpha, governance, mission_control):
    """Test successful payee config update through full lifecycle"""
    # Get initial config
    initial_config = mission_control.payeeConfig()
    
    # Set new payee config
    new_payee_period = 129600  # ~3 days in blocks
    new_activation_length = 64800  # ~1.5 days in blocks
    
    aid = switchboard_alpha.setPayeeConfig(
        new_payee_period,
        new_activation_length,
        sender=governance.address
    )
    
    # Verify event was emitted
    logs = filter_logs(switchboard_alpha, "PendingPayeeConfigChange")
    assert len(logs) == 1
    assert logs[0].payeePeriod == new_payee_period
    assert logs[0].payeeActivationLength == new_activation_length
    assert logs[0].actionId == aid
    expected_confirmation_block = boa.env.evm.patch.block_number + switchboard_alpha.actionTimeLock()
    assert logs[0].confirmationBlock == expected_confirmation_block
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.PAYEE_CONFIG
    pending_config = switchboard_alpha.pendingPayeeConfig(aid)
    assert pending_config.payeePeriod == new_payee_period
    assert pending_config.payeeActivationLength == new_activation_length
    
    # Try to execute before timelock - should fail
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Verify no state change
    current_config = mission_control.payeeConfig()
    assert current_config.payeePeriod == initial_config.payeePeriod
    assert current_config.payeeActivationLength == initial_config.payeeActivationLength
    
    # Time travel to reach timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    
    # Execute the action
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify execution event
    exec_logs = filter_logs(switchboard_alpha, "PayeeConfigSet")
    assert len(exec_logs) == 1
    assert exec_logs[0].payeePeriod == new_payee_period
    assert exec_logs[0].payeeActivationLength == new_activation_length
    
    # Verify state changes in MissionControl
    updated_config = mission_control.payeeConfig()
    assert updated_config.payeePeriod == new_payee_period
    assert updated_config.payeeActivationLength == new_activation_length
    
    # Verify action is cleared
    assert switchboard_alpha.actionType(aid) == 0


def test_set_payee_config_invalid_params_revert(switchboard_alpha, governance):
    """Test that invalid payee config parameters are rejected"""
    # Test with zero payee period
    with boa.reverts("invalid payee config"):
        switchboard_alpha.setPayeeConfig(0, 86400, sender=governance.address)
    
    # Test with zero activation length
    with boa.reverts("invalid payee config"):
        switchboard_alpha.setPayeeConfig(86400, 0, sender=governance.address)
    
    # Test with both zero
    with boa.reverts("invalid payee config"):
        switchboard_alpha.setPayeeConfig(0, 0, sender=governance.address)
    
    # Test with max_value payee period
    with boa.reverts("invalid payee config"):
        switchboard_alpha.setPayeeConfig(MAX_UINT256, 86400, sender=governance.address)
    
    # Test with max_value activation length
    with boa.reverts("invalid payee config"):
        switchboard_alpha.setPayeeConfig(86400, MAX_UINT256, sender=governance.address)
    
    # Test with both max_value
    with boa.reverts("invalid payee config"):
        switchboard_alpha.setPayeeConfig(MAX_UINT256, MAX_UINT256, sender=governance.address)


def test_set_payee_config_non_governance_reverts(switchboard_alpha, alice):
    """Test that non-governance addresses cannot set payee config"""
    with boa.reverts("no perms"):
        switchboard_alpha.setPayeeConfig(129600, 64800, sender=alice)


def test_set_payee_config_edge_cases(switchboard_alpha, governance, mission_control):
    """Test edge cases for payee config"""
    # Test with minimum values (1, 1)
    aid1 = switchboard_alpha.setPayeeConfig(1, 1, sender=governance.address)
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid1, sender=governance.address)
    assert result == True
    
    config = mission_control.payeeConfig()
    assert config.payeePeriod == 1
    assert config.payeeActivationLength == 1
    
    # Test with large values (but not max)
    large_period = 2**256 - 10
    large_activation = 2**256 - 5
    aid2 = switchboard_alpha.setPayeeConfig(large_period, large_activation, sender=governance.address)
    
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid2, sender=governance.address)
    assert result == True
    
    final_config = mission_control.payeeConfig()
    assert final_config.payeePeriod == large_period
    assert final_config.payeeActivationLength == large_activation


def test_set_payee_config_multiple_pending_actions(switchboard_alpha, governance, mission_control):
    """Test creating multiple pending payee config actions"""
    # Create first pending action
    aid1 = switchboard_alpha.setPayeeConfig(120000, 60000, sender=governance.address)
    
    # Create second pending action with different values
    aid2 = switchboard_alpha.setPayeeConfig(240000, 120000, sender=governance.address)
    
    # Verify both are stored separately
    pending1 = switchboard_alpha.pendingPayeeConfig(aid1)
    pending2 = switchboard_alpha.pendingPayeeConfig(aid2)
    
    assert pending1.payeePeriod == 120000
    assert pending1.payeeActivationLength == 60000
    assert pending2.payeePeriod == 240000
    assert pending2.payeeActivationLength == 120000
    
    # Execute second action first
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid2, sender=governance.address)
    assert result == True
    
    config = mission_control.payeeConfig()
    assert config.payeePeriod == 240000
    assert config.payeeActivationLength == 120000
    
    # Execute first action
    result = switchboard_alpha.executePendingAction(aid1, sender=governance.address)
    assert result == True
    
    # Verify it overwrites with first action's values
    final_config = mission_control.payeeConfig()
    assert final_config.payeePeriod == 120000
    assert final_config.payeeActivationLength == 60000


def test_set_payee_config_cancel_pending_action(switchboard_alpha, governance, mission_control):
    """Test canceling a pending payee config action"""
    # Get initial config
    initial_config = mission_control.payeeConfig()
    
    # Create pending action
    aid = switchboard_alpha.setPayeeConfig(180000, 90000, sender=governance.address)
    
    # Cancel the action
    result = switchboard_alpha.cancelPendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify action is cleared
    assert switchboard_alpha.actionType(aid) == 0
    
    # Try to execute cancelled action after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Verify config remains unchanged
    current_config = mission_control.payeeConfig()
    assert current_config.payeePeriod == initial_config.payeePeriod
    assert current_config.payeeActivationLength == initial_config.payeeActivationLength


def test_set_payee_config_different_from_manager_config(switchboard_alpha, governance, mission_control):
    """Test that payee config is independent from manager config"""
    # Set manager config
    manager_aid = switchboard_alpha.setManagerConfig(100000, 50000, sender=governance.address)
    
    # Set payee config with different values
    payee_aid = switchboard_alpha.setPayeeConfig(200000, 100000, sender=governance.address)
    
    # Execute both
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    assert switchboard_alpha.executePendingAction(manager_aid, sender=governance.address) == True
    assert switchboard_alpha.executePendingAction(payee_aid, sender=governance.address) == True
    
    # Verify they have different values
    manager_config = mission_control.managerConfig()
    payee_config = mission_control.payeeConfig()
    
    assert manager_config.managerPeriod == 100000
    assert manager_config.managerActivationLength == 50000
    assert payee_config.payeePeriod == 200000
    assert payee_config.payeeActivationLength == 100000


##############################
# Can Perform Security Action #
##############################


def test_set_can_perform_security_action_enable_success(switchboard_alpha, governance, alice, mission_control):
    """Test successfully enabling security action permissions for an address"""
    # Verify alice doesn't have permission initially
    assert mission_control.canPerformSecurityAction(alice) == False
    
    # Enable security action for alice
    aid = switchboard_alpha.setCanPerformSecurityAction(
        alice,  # signer
        True,   # canPerform
        sender=governance.address
    )
    
    # Verify event was emitted
    logs = filter_logs(switchboard_alpha, "PendingCanPerformSecurityAction")
    assert len(logs) == 1
    assert logs[0].signer == alice
    assert logs[0].canPerform == True
    assert logs[0].actionId == aid
    expected_confirmation_block = boa.env.evm.patch.block_number + switchboard_alpha.actionTimeLock()
    assert logs[0].confirmationBlock == expected_confirmation_block
    
    # Verify pending state
    assert switchboard_alpha.actionType(aid) == CONFIG_ACTION_TYPE.CAN_PERFORM_SECURITY_ACTION
    pending_data = switchboard_alpha.pendingAddrToBool(aid)
    assert pending_data.addr == alice
    assert pending_data.isAllowed == True
    
    # Try to execute before timelock - should fail
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Verify no state change yet
    assert mission_control.canPerformSecurityAction(alice) == False
    
    # Time travel to reach timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    
    # Execute the action
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify execution event
    exec_logs = filter_logs(switchboard_alpha, "CanPerformSecurityAction")
    assert len(exec_logs) == 1
    assert exec_logs[0].signer == alice
    assert exec_logs[0].canPerform == True
    
    # Verify the change was saved in MissionControl
    assert mission_control.canPerformSecurityAction(alice) == True
    
    # Verify action is cleared
    assert switchboard_alpha.actionType(aid) == 0


def test_set_can_perform_security_action_disable_success(switchboard_alpha, governance, bob, mission_control):
    """Test successfully disabling security action permissions for an address - applies immediately"""
    # First enable security action for bob
    aid1 = switchboard_alpha.setCanPerformSecurityAction(bob, True, sender=governance.address)
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    assert switchboard_alpha.executePendingAction(aid1, sender=governance.address) == True
    assert mission_control.canPerformSecurityAction(bob) == True
    
    # Now disable security action for bob - this should apply immediately
    aid2 = switchboard_alpha.setCanPerformSecurityAction(
        bob,    # signer
        False,  # canPerform
        sender=governance.address
    )
    
    # When disabling, the change should be applied immediately
    # Verify execution event was emitted immediately
    exec_logs = filter_logs(switchboard_alpha, "CanPerformSecurityAction")
    assert exec_logs[-1].signer == bob
    assert exec_logs[-1].canPerform == False
    
    # Verify the change was immediately saved in MissionControl
    assert mission_control.canPerformSecurityAction(bob) == False
    
    # There should be no pending action since it was applied immediately
    assert switchboard_alpha.actionType(aid2) == 0


def test_set_can_perform_security_action_non_governance_reverts(switchboard_alpha, alice, bob):
    """Test that non-governance addresses cannot set security action permissions"""
    with boa.reverts("no perms"):
        switchboard_alpha.setCanPerformSecurityAction(bob, True, sender=alice)


def test_set_can_perform_security_action_zero_address(switchboard_alpha, governance):
    """Test setting security action permissions for zero address"""
    # Should allow zero address (useful for disabling all non-specified addresses)
    aid = switchboard_alpha.setCanPerformSecurityAction(
        ZERO_ADDRESS,  # signer
        True,          # canPerform
        sender=governance.address
    )
    
    # Verify it was accepted
    pending_data = switchboard_alpha.pendingAddrToBool(aid)
    assert pending_data.addr == ZERO_ADDRESS
    assert pending_data.isAllowed == True
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify execution event
    exec_logs = filter_logs(switchboard_alpha, "CanPerformSecurityAction")
    assert len(exec_logs) == 1
    assert exec_logs[0].signer == ZERO_ADDRESS
    assert exec_logs[0].canPerform == True


def test_set_can_perform_security_action_multiple_addresses(switchboard_alpha, governance, alice, bob, charlie, mission_control):
    """Test setting security action permissions for multiple addresses"""
    # First enable bob so we can test disabling
    aid_enable = switchboard_alpha.setCanPerformSecurityAction(bob, True, sender=governance.address)
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    switchboard_alpha.executePendingAction(aid_enable, sender=governance.address)
    assert mission_control.canPerformSecurityAction(bob) == True
    
    # Create pending action for alice (enable)
    aid1 = switchboard_alpha.setCanPerformSecurityAction(alice, True, sender=governance.address)
    
    # Bob's disable action should apply immediately
    aid2 = switchboard_alpha.setCanPerformSecurityAction(bob, False, sender=governance.address)
    # Check logs immediately after the transaction
    exec_logs_bob = filter_logs(switchboard_alpha, "CanPerformSecurityAction")
    assert len(exec_logs_bob) == 1
    assert exec_logs_bob[0].signer == bob
    assert exec_logs_bob[0].canPerform == False
    
    # Create pending action for charlie (enable)
    aid3 = switchboard_alpha.setCanPerformSecurityAction(charlie, True, sender=governance.address)
    
    # Verify bob's change was applied immediately
    assert mission_control.canPerformSecurityAction(bob) == False
    
    # Verify alice and charlie still have pending actions
    pending1 = switchboard_alpha.pendingAddrToBool(aid1)
    pending3 = switchboard_alpha.pendingAddrToBool(aid3)
    
    assert pending1.addr == alice
    assert pending1.isAllowed == True
    assert pending3.addr == charlie
    assert pending3.isAllowed == True
    
    # Bob's action should not be pending (applied immediately)
    assert switchboard_alpha.actionType(aid2) == 0
    
    # Execute remaining pending actions after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    
    # Execute alice's action
    result1 = switchboard_alpha.executePendingAction(aid1, sender=governance.address)
    assert result1 == True
    assert mission_control.canPerformSecurityAction(alice) == True
    
    # Execute charlie's action
    result3 = switchboard_alpha.executePendingAction(aid3, sender=governance.address)
    assert result3 == True
    assert mission_control.canPerformSecurityAction(charlie) == True


def test_set_can_perform_security_action_same_address_overwrite(switchboard_alpha, governance, alice, mission_control):
    """Test that multiple pending actions for same address can be created"""
    # Create first pending action (enable)
    aid1 = switchboard_alpha.setCanPerformSecurityAction(alice, True, sender=governance.address)
    
    # Create second action (disable) for same address - this applies immediately
    aid2 = switchboard_alpha.setCanPerformSecurityAction(alice, False, sender=governance.address)
    
    # Verify the disable was applied immediately
    assert mission_control.canPerformSecurityAction(alice) == False
    exec_logs = filter_logs(switchboard_alpha, "CanPerformSecurityAction")
    assert exec_logs[-1].signer == alice
    assert exec_logs[-1].canPerform == False
    
    # The first pending action should still exist
    pending1 = switchboard_alpha.pendingAddrToBool(aid1)
    assert pending1.addr == alice
    assert pending1.isAllowed == True
    
    # The second action should not be pending (applied immediately)
    assert switchboard_alpha.actionType(aid2) == 0
    
    # Execute first action after timelock (will overwrite the immediate disable)
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid1, sender=governance.address)
    assert result == True
    
    # Verify alice now has canPerform = True
    assert mission_control.canPerformSecurityAction(alice) == True
    exec_logs = filter_logs(switchboard_alpha, "CanPerformSecurityAction")
    assert exec_logs[-1].signer == alice
    assert exec_logs[-1].canPerform == True


def test_set_can_perform_security_action_cancel_pending(switchboard_alpha, governance, alice):
    """Test canceling a pending security action permission change"""
    # Create pending action
    aid = switchboard_alpha.setCanPerformSecurityAction(alice, True, sender=governance.address)
    
    # Cancel the action
    result = switchboard_alpha.cancelPendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify action is cleared
    assert switchboard_alpha.actionType(aid) == 0
    
    # Try to execute cancelled action after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == False
    
    # Verify no execution event was emitted
    exec_logs = filter_logs(switchboard_alpha, "CanPerformSecurityAction")
    assert len(exec_logs) == 0


def test_set_can_perform_security_action_contract_addresses(switchboard_alpha, governance, wallet_template_v2):
    """Test setting security action permissions for contract addresses"""
    # Should allow setting permissions for contract addresses
    aid = switchboard_alpha.setCanPerformSecurityAction(
        wallet_template_v2.address,  # contract address
        True,                        # canPerform
        sender=governance.address
    )
    
    # Verify it was accepted
    pending_data = switchboard_alpha.pendingAddrToBool(aid)
    assert pending_data.addr == wallet_template_v2.address
    assert pending_data.isAllowed == True
    
    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    result = switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert result == True
    
    # Verify execution event
    exec_logs = filter_logs(switchboard_alpha, "CanPerformSecurityAction")
    assert len(exec_logs) == 1
    assert exec_logs[0].signer == wallet_template_v2.address
    assert exec_logs[0].canPerform == True


#######################
# Creator Whitelist   #
#######################


def test_set_creator_whitelist_enable_by_governance_success(switchboard_alpha, governance, alice, mission_control):
    """Test that governance can enable creator whitelist"""
    # Verify alice is not whitelisted initially
    assert mission_control.creatorWhitelist(alice) == False
    
    # Enable creator whitelist for alice
    switchboard_alpha.setCreatorWhitelist(alice, True, sender=governance.address)
    
    # Verify event was emitted
    logs = filter_logs(switchboard_alpha, "CreatorWhitelistSet")
    assert len(logs) == 1
    assert logs[0].creator == alice
    assert logs[0].isWhitelisted == True
    assert logs[0].caller == governance.address
    
    # Verify the change was saved in MissionControl
    assert mission_control.creatorWhitelist(alice) == True


def test_set_creator_whitelist_disable_by_governance_success(switchboard_alpha, governance, bob, mission_control):
    """Test that governance can disable creator whitelist"""
    # First enable creator whitelist for bob
    switchboard_alpha.setCreatorWhitelist(bob, True, sender=governance.address)
    assert mission_control.creatorWhitelist(bob) == True
    
    # Then disable it
    switchboard_alpha.setCreatorWhitelist(bob, False, sender=governance.address)
    
    # Verify event was emitted
    logs = filter_logs(switchboard_alpha, "CreatorWhitelistSet")
    assert len(logs) == 1  # Only the last event
    assert logs[0].creator == bob
    assert logs[0].isWhitelisted == False
    assert logs[0].caller == governance.address
    
    # Verify the change was saved in MissionControl
    assert mission_control.creatorWhitelist(bob) == False


def test_set_creator_whitelist_disable_by_security_user_success(switchboard_alpha, governance, alice, bob, mission_control):
    """Test that a user with canPerformSecurityAction can disable creator whitelist"""
    # First, give alice security action permissions
    aid = switchboard_alpha.setCanPerformSecurityAction(alice, True, sender=governance.address)
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    switchboard_alpha.executePendingAction(aid, sender=governance.address)
    
    # Verify alice has security permissions
    assert mission_control.canPerformSecurityAction(alice) == True
    
    # Enable creator whitelist for bob (by governance)
    switchboard_alpha.setCreatorWhitelist(bob, True, sender=governance.address)
    assert mission_control.creatorWhitelist(bob) == True
    
    # Now alice (with security permissions) can disable it
    switchboard_alpha.setCreatorWhitelist(bob, False, sender=alice)
    
    # Verify event was emitted
    logs = filter_logs(switchboard_alpha, "CreatorWhitelistSet")
    assert len(logs) == 1
    assert logs[0].creator == bob
    assert logs[0].isWhitelisted == False
    assert logs[0].caller == alice
    
    # Verify the change was saved in MissionControl
    assert mission_control.creatorWhitelist(bob) == False


def test_set_creator_whitelist_enable_by_security_user_reverts(switchboard_alpha, governance, alice, bob):
    """Test that a user with canPerformSecurityAction cannot enable creator whitelist"""
    # First, give alice security action permissions
    aid = switchboard_alpha.setCanPerformSecurityAction(alice, True, sender=governance.address)
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    switchboard_alpha.executePendingAction(aid, sender=governance.address)
    
    # Alice should not be able to enable creator whitelist
    with boa.reverts("no perms"):
        switchboard_alpha.setCreatorWhitelist(bob, True, sender=alice)


def test_set_creator_whitelist_no_perms_reverts(switchboard_alpha, alice, bob):
    """Test that users without permissions cannot set creator whitelist"""
    # Alice has no special permissions
    with boa.reverts("no perms"):
        switchboard_alpha.setCreatorWhitelist(bob, True, sender=alice)
    
    with boa.reverts("no perms"):
        switchboard_alpha.setCreatorWhitelist(bob, False, sender=alice)


def test_set_creator_whitelist_zero_address_reverts(switchboard_alpha, governance):
    """Test that zero address cannot be whitelisted"""
    with boa.reverts("invalid creator"):
        switchboard_alpha.setCreatorWhitelist(ZERO_ADDRESS, True, sender=governance.address)
    
    with boa.reverts("invalid creator"):
        switchboard_alpha.setCreatorWhitelist(ZERO_ADDRESS, False, sender=governance.address)


def test_set_creator_whitelist_multiple_creators(switchboard_alpha, governance, alice, bob, charlie, mission_control):
    """Test setting whitelist for multiple creators"""
    # Enable whitelist for multiple creators
    switchboard_alpha.setCreatorWhitelist(alice, True, sender=governance.address)
    logs1 = filter_logs(switchboard_alpha, "CreatorWhitelistSet")
    assert logs1[0].creator == alice
    assert logs1[0].isWhitelisted == True
    assert mission_control.creatorWhitelist(alice) == True
    
    switchboard_alpha.setCreatorWhitelist(bob, True, sender=governance.address)
    logs2 = filter_logs(switchboard_alpha, "CreatorWhitelistSet")
    assert logs2[0].creator == bob
    assert logs2[0].isWhitelisted == True
    assert mission_control.creatorWhitelist(bob) == True
    
    switchboard_alpha.setCreatorWhitelist(charlie, False, sender=governance.address)
    logs3 = filter_logs(switchboard_alpha, "CreatorWhitelistSet")
    assert logs3[0].creator == charlie
    assert logs3[0].isWhitelisted == False
    assert mission_control.creatorWhitelist(charlie) == False


def test_set_creator_whitelist_contract_address(switchboard_alpha, governance, wallet_template_v2):
    """Test whitelisting a contract address as creator"""
    # Should allow whitelisting contract addresses
    switchboard_alpha.setCreatorWhitelist(wallet_template_v2.address, True, sender=governance.address)
    
    # Verify event was emitted
    logs = filter_logs(switchboard_alpha, "CreatorWhitelistSet")
    assert len(logs) == 1
    assert logs[0].creator == wallet_template_v2.address
    assert logs[0].isWhitelisted == True
    assert logs[0].caller == governance.address


###################
# Locked Signer   #
###################


def test_set_locked_signer_lock_by_governance_success(switchboard_alpha, governance, alice, mission_control):
    """Test that governance can lock a signer"""
    # Verify alice is not locked initially
    assert mission_control.isLockedSigner(alice) == False
    
    # Lock alice as a signer
    switchboard_alpha.setLockedSigner(alice, True, sender=governance.address)
    
    # Verify event was emitted
    logs = filter_logs(switchboard_alpha, "LockedSignerSet")
    assert len(logs) == 1
    assert logs[0].signer == alice
    assert logs[0].isLocked == True
    assert logs[0].caller == governance.address
    
    # Verify the change was saved in MissionControl
    assert mission_control.isLockedSigner(alice) == True


def test_set_locked_signer_unlock_by_governance_success(switchboard_alpha, governance, bob, mission_control):
    """Test that governance can unlock a signer"""
    # First lock bob
    switchboard_alpha.setLockedSigner(bob, True, sender=governance.address)
    assert mission_control.isLockedSigner(bob) == True
    
    # Then unlock
    switchboard_alpha.setLockedSigner(bob, False, sender=governance.address)
    
    # Verify event was emitted
    logs = filter_logs(switchboard_alpha, "LockedSignerSet")
    assert len(logs) == 1  # Only the last event
    assert logs[0].signer == bob
    assert logs[0].isLocked == False
    assert logs[0].caller == governance.address
    
    # Verify the change was saved in MissionControl
    assert mission_control.isLockedSigner(bob) == False


def test_set_locked_signer_unlock_by_security_user_success(switchboard_alpha, governance, alice, bob, mission_control):
    """Test that a user with canPerformSecurityAction can unlock a signer"""
    # First, give alice security action permissions
    aid = switchboard_alpha.setCanPerformSecurityAction(alice, True, sender=governance.address)
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    switchboard_alpha.executePendingAction(aid, sender=governance.address)
    
    # Verify alice has security permissions
    assert mission_control.canPerformSecurityAction(alice) == True
    
    # Lock bob (by governance)
    switchboard_alpha.setLockedSigner(bob, True, sender=governance.address)
    assert mission_control.isLockedSigner(bob) == True
    
    # Now alice (with security permissions) can unlock
    switchboard_alpha.setLockedSigner(bob, False, sender=alice)
    
    # Verify event was emitted
    logs = filter_logs(switchboard_alpha, "LockedSignerSet")
    assert len(logs) == 1
    assert logs[0].signer == bob
    assert logs[0].isLocked == False
    assert logs[0].caller == alice
    
    # Verify the change was saved in MissionControl
    assert mission_control.isLockedSigner(bob) == False


def test_set_locked_signer_lock_by_security_user_reverts(switchboard_alpha, governance, alice, bob):
    """Test that a user with canPerformSecurityAction cannot lock a signer"""
    # First, give alice security action permissions
    aid = switchboard_alpha.setCanPerformSecurityAction(alice, True, sender=governance.address)
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    switchboard_alpha.executePendingAction(aid, sender=governance.address)
    
    # Alice should not be able to lock a signer
    with boa.reverts("no perms"):
        switchboard_alpha.setLockedSigner(bob, True, sender=alice)


def test_set_locked_signer_no_perms_reverts(switchboard_alpha, alice, bob):
    """Test that users without permissions cannot set locked signer"""
    # Alice has no special permissions
    with boa.reverts("no perms"):
        switchboard_alpha.setLockedSigner(bob, True, sender=alice)
    
    with boa.reverts("no perms"):
        switchboard_alpha.setLockedSigner(bob, False, sender=alice)


def test_set_locked_signer_zero_address_reverts(switchboard_alpha, governance):
    """Test that zero address cannot be locked"""
    with boa.reverts("invalid creator"):
        switchboard_alpha.setLockedSigner(ZERO_ADDRESS, True, sender=governance.address)
    
    with boa.reverts("invalid creator"):
        switchboard_alpha.setLockedSigner(ZERO_ADDRESS, False, sender=governance.address)


def test_set_locked_signer_multiple_signers(switchboard_alpha, governance, alice, bob, charlie, mission_control):
    """Test locking/unlocking multiple signers"""
    # Lock alice
    switchboard_alpha.setLockedSigner(alice, True, sender=governance.address)
    logs1 = filter_logs(switchboard_alpha, "LockedSignerSet")
    assert logs1[0].signer == alice
    assert logs1[0].isLocked == True
    assert mission_control.isLockedSigner(alice) == True
    
    # Lock bob
    switchboard_alpha.setLockedSigner(bob, True, sender=governance.address)
    logs2 = filter_logs(switchboard_alpha, "LockedSignerSet")
    assert logs2[0].signer == bob
    assert logs2[0].isLocked == True
    assert mission_control.isLockedSigner(bob) == True
    
    # Unlock charlie (who wasn't locked)
    switchboard_alpha.setLockedSigner(charlie, False, sender=governance.address)
    logs3 = filter_logs(switchboard_alpha, "LockedSignerSet")
    assert logs3[0].signer == charlie
    assert logs3[0].isLocked == False
    assert mission_control.isLockedSigner(charlie) == False


def test_set_locked_signer_contract_address(switchboard_alpha, governance, wallet_template_v2):
    """Test locking a contract address as signer"""
    # Should allow locking contract addresses
    switchboard_alpha.setLockedSigner(wallet_template_v2.address, True, sender=governance.address)
    
    # Verify event was emitted
    logs = filter_logs(switchboard_alpha, "LockedSignerSet")
    assert len(logs) == 1
    assert logs[0].signer == wallet_template_v2.address
    assert logs[0].isLocked == True
    assert logs[0].caller == governance.address


def test_creator_whitelist_and_locked_signer_interaction(switchboard_alpha, governance, alice, bob, mission_control):
    """Test that creator whitelist and locked signer can be used together"""
    # Give bob security permissions
    aid = switchboard_alpha.setCanPerformSecurityAction(bob, True, sender=governance.address)
    boa.env.time_travel(blocks=switchboard_alpha.actionTimeLock())
    switchboard_alpha.executePendingAction(aid, sender=governance.address)
    assert mission_control.canPerformSecurityAction(bob) == True
    
    # Governance enables creator whitelist and locks signer for alice
    switchboard_alpha.setCreatorWhitelist(alice, True, sender=governance.address)
    logs1 = filter_logs(switchboard_alpha, "CreatorWhitelistSet")
    assert logs1[0].creator == alice
    assert logs1[0].isWhitelisted == True
    assert mission_control.creatorWhitelist(alice) == True
    
    switchboard_alpha.setLockedSigner(alice, True, sender=governance.address)
    logs2 = filter_logs(switchboard_alpha, "LockedSignerSet")
    assert logs2[0].signer == alice
    assert logs2[0].isLocked == True
    assert mission_control.isLockedSigner(alice) == True
    
    # Bob (with security permissions) can disable both
    switchboard_alpha.setCreatorWhitelist(alice, False, sender=bob)
    logs3 = filter_logs(switchboard_alpha, "CreatorWhitelistSet")
    assert logs3[0].creator == alice
    assert logs3[0].isWhitelisted == False
    assert logs3[0].caller == bob
    assert mission_control.creatorWhitelist(alice) == False
    
    switchboard_alpha.setLockedSigner(alice, False, sender=bob)
    logs4 = filter_logs(switchboard_alpha, "LockedSignerSet")
    assert logs4[0].signer == alice
    assert logs4[0].isLocked == False
    assert logs4[0].caller == bob
    assert mission_control.isLockedSigner(alice) == False


######################
# Ripe Lock Duration #
######################


def test_set_ripe_lock_duration_success(switchboard_alpha, governance, loot_distributor):
    """Test successful setting of ripe lock duration"""
    # Set new ripe lock duration (e.g., 50,400 blocks ~ 7 days on Ethereum)
    new_duration = 50400  # blocks
    
    # Call setRipeLockDuration as governance
    switchboard_alpha.setRipeLockDuration(new_duration, sender=governance.address)
    
    # Verify event was emitted
    logs = filter_logs(switchboard_alpha, "RipeLockDurationSetFromSwitchboard")
    assert len(logs) == 1
    assert logs[0].ripeLockDuration == new_duration
    
    # Verify the value was set in LootDistributor
    assert loot_distributor.ripeLockDuration() == new_duration


def test_set_ripe_lock_duration_different_values(switchboard_alpha, governance, loot_distributor):
    """Test setting different ripe lock duration values in blocks"""
    # Test with ~1 day (7200 blocks at 12s/block)
    duration_1_day = 7200
    switchboard_alpha.setRipeLockDuration(duration_1_day, sender=governance.address)
    assert loot_distributor.ripeLockDuration() == duration_1_day
    
    # Test with ~30 days (216,000 blocks)
    duration_30_days = 216000
    switchboard_alpha.setRipeLockDuration(duration_30_days, sender=governance.address)
    assert loot_distributor.ripeLockDuration() == duration_30_days
    
    # Test with 0 (immediate unlock)
    duration_zero = 0
    switchboard_alpha.setRipeLockDuration(duration_zero, sender=governance.address)
    assert loot_distributor.ripeLockDuration() == duration_zero
    
    # Test with ~1 year (2,628,000 blocks)
    duration_1_year = 2628000
    switchboard_alpha.setRipeLockDuration(duration_1_year, sender=governance.address)
    assert loot_distributor.ripeLockDuration() == duration_1_year


def test_set_ripe_lock_duration_non_governance_reverts(switchboard_alpha, alice, loot_distributor):
    """Test that non-governance addresses cannot set ripe lock duration"""
    new_duration = 50400  # blocks (~7 days)
    
    # Store the current duration before the failed attempt
    current_duration = loot_distributor.ripeLockDuration()
    
    with boa.reverts():
        switchboard_alpha.setRipeLockDuration(new_duration, sender=alice)
    
    # Verify the value was not changed
    assert loot_distributor.ripeLockDuration() == current_duration  # Should remain at previous value


def test_set_ripe_lock_duration_multiple_updates(switchboard_alpha, governance, loot_distributor):
    """Test multiple consecutive updates to ripe lock duration in blocks"""
    durations = [100, 500, 1000, 7200, 50400]  # Various block counts
    
    for duration in durations:
        switchboard_alpha.setRipeLockDuration(duration, sender=governance.address)
        assert loot_distributor.ripeLockDuration() == duration
        
        # Verify each update emits an event
        logs = filter_logs(switchboard_alpha, "RipeLockDurationSetFromSwitchboard")
        assert logs[-1].ripeLockDuration == duration