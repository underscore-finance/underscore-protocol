import pytest
import boa
from conf_utils import filter_logs
from constants import ZERO_ADDRESS


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
    assert switchboard_alpha.actionType(aid) == 1  # USER_WALLET_TEMPLATES
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
    assert switchboard_alpha.actionType(aid) == 1  # USER_WALLET_TEMPLATES
    
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
    assert switchboard_alpha.actionType(aid) == 1  # USER_WALLET_TEMPLATES
    
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