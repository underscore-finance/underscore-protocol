import pytest
import boa

from constants import WHITELIST_ACTION, ZERO_ADDRESS
from conf_utils import filter_logs


###################################
# Whitelist Management Validation #
###################################


def test_owner_can_manage_all_whitelist_actions(kernel, user_wallet, bob):
    """Test that the owner has permission for all whitelist actions"""
    # Owner should have permission for all actions
    assert kernel.canManageWhitelist(user_wallet, bob, WHITELIST_ACTION.ADD_PENDING)
    assert kernel.canManageWhitelist(user_wallet, bob, WHITELIST_ACTION.CONFIRM_WHITELIST)
    assert kernel.canManageWhitelist(user_wallet, bob, WHITELIST_ACTION.CANCEL_WHITELIST)
    assert kernel.canManageWhitelist(user_wallet, bob, WHITELIST_ACTION.REMOVE_WHITELIST)


def test_manager_whitelist_permissions_individual(createGlobalManagerSettings, createWhitelistPerms, sally, createManagerSettings, kernel, user_wallet, user_wallet_config, alice, high_command):
    """Test manager permissions for individual whitelist actions"""
    # Set global permissions to allow all actions
    global_whitelist_perms = createWhitelistPerms(_canAddPending=True, _canConfirm=True, _canCancel=True, _canRemove=True)
    new_global_manager_settings = createGlobalManagerSettings(_whitelistPerms=global_whitelist_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    # Test canAddPending permission only
    manager_whitelist_perms = createWhitelistPerms(_canAddPending=True, _canConfirm=False, _canCancel=False, _canRemove=False)
    new_manager_settings = createManagerSettings(_whitelistPerms=manager_whitelist_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    assert kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.ADD_PENDING)
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.CONFIRM_WHITELIST)
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.CANCEL_WHITELIST)
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.REMOVE_WHITELIST)
    
    # Test canConfirm permission only
    manager_whitelist_perms = createWhitelistPerms(_canAddPending=False, _canConfirm=True, _canCancel=False, _canRemove=False)
    new_manager_settings = createManagerSettings(_whitelistPerms=manager_whitelist_perms)
    user_wallet_config.addManager(sally, new_manager_settings, sender=high_command.address)
    
    assert not kernel.canManageWhitelist(user_wallet, sally, WHITELIST_ACTION.ADD_PENDING)
    assert kernel.canManageWhitelist(user_wallet, sally, WHITELIST_ACTION.CONFIRM_WHITELIST)
    assert not kernel.canManageWhitelist(user_wallet, sally, WHITELIST_ACTION.CANCEL_WHITELIST)
    assert not kernel.canManageWhitelist(user_wallet, sally, WHITELIST_ACTION.REMOVE_WHITELIST)


def test_manager_whitelist_permissions_multiple(createGlobalManagerSettings, createWhitelistPerms, createManagerSettings, kernel, user_wallet, user_wallet_config, alice, high_command):
    """Test manager with multiple whitelist permissions"""
    whitelist_perms = createWhitelistPerms(_canAddPending=True, _canConfirm=True, _canCancel=True, _canRemove=False)
    new_global_manager_settings = createGlobalManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    new_manager_settings = createManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    assert kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.ADD_PENDING)
    assert kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.CONFIRM_WHITELIST)
    assert kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.CANCEL_WHITELIST)
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.REMOVE_WHITELIST)


def test_global_whitelist_permissions_override(createGlobalManagerSettings, createWhitelistPerms, createManagerSettings, kernel, user_wallet, user_wallet_config, alice, high_command):
    """Test that both manager and global permissions must be true"""
    # Set global permissions to allow all
    global_whitelist_perms = createWhitelistPerms(_canAddPending=True, _canConfirm=True, _canCancel=True, _canRemove=True)
    new_global_manager_settings = createGlobalManagerSettings(_whitelistPerms=global_whitelist_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    # But manager permissions only allow ADD_PENDING
    manager_whitelist_perms = createWhitelistPerms(_canAddPending=True, _canConfirm=False, _canCancel=False, _canRemove=False)
    new_manager_settings = createManagerSettings(_whitelistPerms=manager_whitelist_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Only ADD_PENDING should be allowed (both global and manager are true)
    assert kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.ADD_PENDING)
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.CONFIRM_WHITELIST)
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.CANCEL_WHITELIST)
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.REMOVE_WHITELIST)


def test_global_permissions_restrict_manager(createGlobalManagerSettings, createWhitelistPerms, createManagerSettings, kernel, user_wallet, user_wallet_config, alice, high_command):
    """Test that global permissions can restrict manager permissions"""
    # Set global permissions to deny all except ADD_PENDING
    global_whitelist_perms = createWhitelistPerms(_canAddPending=True, _canConfirm=False, _canCancel=False, _canRemove=False)
    new_global_manager_settings = createGlobalManagerSettings(_whitelistPerms=global_whitelist_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    # Manager permissions allow all
    manager_whitelist_perms = createWhitelistPerms(_canAddPending=True, _canConfirm=True, _canCancel=True, _canRemove=True)
    new_manager_settings = createManagerSettings(_whitelistPerms=manager_whitelist_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Only ADD_PENDING should be allowed (global restricts the others)
    assert kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.ADD_PENDING)
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.CONFIRM_WHITELIST)
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.CANCEL_WHITELIST)
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.REMOVE_WHITELIST)


def test_non_manager_non_owner_denied(kernel, user_wallet, charlie):
    """Test that non-manager/non-owner users are denied all whitelist actions"""
    assert not kernel.canManageWhitelist(user_wallet, charlie, WHITELIST_ACTION.ADD_PENDING)
    assert not kernel.canManageWhitelist(user_wallet, charlie, WHITELIST_ACTION.CONFIRM_WHITELIST)
    assert not kernel.canManageWhitelist(user_wallet, charlie, WHITELIST_ACTION.CANCEL_WHITELIST)
    assert not kernel.canManageWhitelist(user_wallet, charlie, WHITELIST_ACTION.REMOVE_WHITELIST)


def test_manager_with_all_permissions_false(createGlobalManagerSettings, createWhitelistPerms, createManagerSettings, kernel, user_wallet, user_wallet_config, alice, high_command):
    """Test manager with all whitelist permissions set to false"""
    whitelist_perms = createWhitelistPerms(_canAddPending=False, _canConfirm=False, _canCancel=False, _canRemove=False)
    new_global_manager_settings = createGlobalManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    new_manager_settings = createManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Manager should be denied all actions
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.ADD_PENDING)
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.CONFIRM_WHITELIST)
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.CANCEL_WHITELIST)
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.REMOVE_WHITELIST)


def test_whitelist_management_example(createGlobalManagerSettings, createWhitelistPerms, sally, charlie, bob, createManagerSettings, kernel, user_wallet, user_wallet_config, alice, high_command):

    whitelist_perms = createWhitelistPerms(_canAddPending=True, _canConfirm=False, _canCancel=False, _canRemove=False)

    # set global manager settings
    new_global_manager_settings = createGlobalManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)

    # add manager
    new_manager_settings = createManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)

    # owner can manage
    assert kernel.canManageWhitelist(user_wallet, bob, WHITELIST_ACTION.ADD_PENDING)

    # manager -- allowed
    assert kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.ADD_PENDING)

    # another manager -- not allowed
    whitelist_perms = createWhitelistPerms(_canAddPending=False)
    new_manager_settings = createManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.addManager(sally, new_manager_settings, sender=high_command.address)

    assert not kernel.canManageWhitelist(user_wallet, sally, WHITELIST_ACTION.ADD_PENDING)

    # not manager
    assert not kernel.canManageWhitelist(user_wallet, charlie, WHITELIST_ACTION.ADD_PENDING)


###########################
# Whitelist - Add Pending #
###########################


def test_add_pending_whitelist_success(kernel, user_wallet, user_wallet_config, bob, charlie):
    """Test successful pending whitelist creation"""
    # Add pending whitelist as owner
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Verify pending whitelist data was saved
    pending = user_wallet_config.pendingWhitelist(charlie)
    assert pending.initiatedBlock == boa.env.evm.patch.block_number
    assert pending.confirmBlock == boa.env.evm.patch.block_number + user_wallet_config.timeLock()
    assert pending.currentOwner == bob
    
    # Verify event emission
    log = filter_logs(kernel, "WhitelistAddrPending")[0]
    assert log.user == user_wallet.address
    assert log.addr == charlie
    assert log.confirmBlock == pending.confirmBlock
    assert log.addedBy == bob


def test_add_pending_whitelist_with_timelock(kernel, user_wallet, user_wallet_config, bob, alice):
    """Test pending whitelist respects timelock"""
    timelock = user_wallet_config.timeLock()
    initial_block = boa.env.evm.patch.block_number
    
    # Add pending whitelist
    kernel.addPendingWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Verify confirmBlock is set correctly with timelock
    pending = user_wallet_config.pendingWhitelist(alice)
    assert pending.confirmBlock == initial_block + timelock


def test_add_pending_whitelist_invalid_addresses(kernel, user_wallet, user_wallet_config, bob):
    """Test invalid address validation"""
    # Cannot add zero address
    with boa.reverts("invalid addr"):
        kernel.addPendingWhitelistAddr(user_wallet, ZERO_ADDRESS, sender=bob)
    
    # Cannot add the wallet itself
    with boa.reverts("invalid addr"):
        kernel.addPendingWhitelistAddr(user_wallet, user_wallet, sender=bob)
    
    # Cannot add the owner
    with boa.reverts("invalid addr"):
        kernel.addPendingWhitelistAddr(user_wallet, bob, sender=bob)
    
    # Cannot add the wallet config
    with boa.reverts("invalid addr"):
        kernel.addPendingWhitelistAddr(user_wallet, user_wallet_config.address, sender=bob)


def test_add_pending_whitelist_already_pending(kernel, user_wallet, bob, charlie):
    """Test cannot add duplicate pending whitelist"""
    # Add pending whitelist first time
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Try to add same address again
    with boa.reverts("pending whitelist already exists"):
        kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)


def test_add_pending_whitelist_already_whitelisted(kernel, user_wallet, user_wallet_config, bob, alice):
    """Test cannot add pending for already whitelisted address"""
    # First add alice to whitelist (pending -> confirm)
    kernel.addPendingWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Advance blocks to pass timelock
    boa.env.time_travel(blocks=user_wallet_config.timeLock())

    # Confirm the whitelist
    kernel.confirmWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Verify alice is whitelisted
    assert user_wallet_config.indexOfWhitelist(alice) != 0
    
    # Try to add pending whitelist for already whitelisted address
    with boa.reverts("already whitelisted"):
        kernel.addPendingWhitelistAddr(user_wallet, alice, sender=bob)


def test_add_pending_whitelist_invalid_user_wallet(kernel, bob, alice):
    """Test validation of user wallet"""
    # Try with random address that's not a user wallet
    with boa.reverts("invalid user wallet"):
        kernel.addPendingWhitelistAddr(alice, bob, sender=bob)


def test_add_pending_whitelist_by_manager(createGlobalManagerSettings, createWhitelistPerms, createManagerSettings, kernel, user_wallet, user_wallet_config, alice, charlie, high_command):
    """Test manager can add pending whitelist with proper permissions"""
    # Setup manager with add pending permission
    whitelist_perms = createWhitelistPerms(_canAddPending=True, _canConfirm=False, _canCancel=False, _canRemove=False)
    new_global_manager_settings = createGlobalManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    new_manager_settings = createManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Manager adds pending whitelist
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=alice)
    
    # Verify event shows manager as addedBy
    log = filter_logs(kernel, "WhitelistAddrPending")[0]
    assert log.addedBy == alice


#######################
# Whitelist - Confirm #
#######################


def test_confirm_whitelist_success(kernel, user_wallet, user_wallet_config, bob, charlie):
    """Test successful whitelist confirmation after timelock"""
    # Add pending whitelist
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Get pending whitelist data before confirmation
    pending = user_wallet_config.pendingWhitelist(charlie)
    initiated_block = pending.initiatedBlock
    confirm_block = pending.confirmBlock
    
    # Advance blocks to pass timelock
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    
    # Confirm the whitelist
    kernel.confirmWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Verify address is now whitelisted
    assert user_wallet_config.indexOfWhitelist(charlie) != 0
    
    # Verify pending whitelist is cleared
    pending_after = user_wallet_config.pendingWhitelist(charlie)
    assert pending_after.initiatedBlock == 0
    assert pending_after.confirmBlock == 0
    
    # Verify event emission
    log = filter_logs(kernel, "WhitelistAddrConfirmed")[0]
    assert log.user == user_wallet.address
    assert log.addr == charlie
    assert log.initiatedBlock == initiated_block
    assert log.confirmBlock == confirm_block
    assert log.confirmedBy == bob


def test_confirm_whitelist_timelock_not_reached(kernel, user_wallet, user_wallet_config, bob, alice):
    """Test cannot confirm before timelock expires"""
    # Add pending whitelist
    kernel.addPendingWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Try to confirm immediately (without advancing blocks)
    with boa.reverts("time delay not reached"):
        kernel.confirmWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Advance blocks but not enough to pass timelock
    boa.env.time_travel(blocks=user_wallet_config.timeLock() - 1)
    
    # Should still fail
    with boa.reverts("time delay not reached"):
        kernel.confirmWhitelistAddr(user_wallet, alice, sender=bob)


def test_confirm_whitelist_exactly_at_timelock(kernel, user_wallet, user_wallet_config, bob, alice):
    """Test can confirm exactly when timelock expires"""
    # Add pending whitelist
    kernel.addPendingWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Advance exactly to the confirm block
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    
    # Should succeed
    kernel.confirmWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Verify whitelisted
    assert user_wallet_config.indexOfWhitelist(alice) != 0


def test_confirm_whitelist_no_pending(kernel, user_wallet, bob, charlie):
    """Test cannot confirm non-existent pending whitelist"""
    # Try to confirm without adding pending first
    with boa.reverts("no pending whitelist"):
        kernel.confirmWhitelistAddr(user_wallet, charlie, sender=bob)


def test_confirm_whitelist_owner_changed(kernel, user_wallet, user_wallet_config, bob, alice, charlie):
    """Test cannot confirm if owner changed after pending was created"""
    # Add pending whitelist as current owner (bob)
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Transfer ownership to alice
    user_wallet_config.changeOwnership(alice, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.ownershipTimeLock())
    user_wallet_config.confirmOwnershipChange(sender=alice)

    boa.env.time_travel(blocks=user_wallet_config.timeLock())

    # Try to confirm - should fail because owner changed
    with boa.reverts("owner must match"):
        kernel.confirmWhitelistAddr(user_wallet, charlie, sender=alice)


def test_confirm_whitelist_invalid_user_wallet(kernel, bob, alice):
    """Test validation of user wallet"""
    # Try with random address that's not a user wallet
    with boa.reverts("invalid user wallet"):
        kernel.confirmWhitelistAddr(alice, bob, sender=bob)


def test_confirm_whitelist_by_manager(createGlobalManagerSettings, createWhitelistPerms, createManagerSettings, kernel, user_wallet, user_wallet_config, alice, charlie, bob, high_command):
    """Test manager can confirm whitelist with proper permissions"""
    # Setup manager with confirm permission
    whitelist_perms = createWhitelistPerms(_canAddPending=False, _canConfirm=True, _canCancel=False, _canRemove=False)
    new_global_manager_settings = createGlobalManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    new_manager_settings = createManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Owner adds pending whitelist
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Advance blocks to pass timelock
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    
    # Manager confirms the whitelist
    kernel.confirmWhitelistAddr(user_wallet, charlie, sender=alice)
    
    # Verify event shows manager as confirmedBy
    log = filter_logs(kernel, "WhitelistAddrConfirmed")[0]
    assert log.confirmedBy == alice
    
    # Verify whitelisted
    assert user_wallet_config.indexOfWhitelist(charlie) != 0


def test_confirm_whitelist_already_confirmed(kernel, user_wallet, user_wallet_config, bob, alice):
    """Test cannot confirm already confirmed whitelist"""
    # Add and confirm whitelist
    kernel.addPendingWhitelistAddr(user_wallet, alice, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    kernel.confirmWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Try to confirm again
    with boa.reverts("no pending whitelist"):
        kernel.confirmWhitelistAddr(user_wallet, alice, sender=bob)


######################
# Whitelist - Cancel #
######################


def test_cancel_pending_whitelist_success(kernel, user_wallet, user_wallet_config, bob, charlie):
    """Test successful pending whitelist cancellation by owner"""
    # Add pending whitelist
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Get pending whitelist data before cancellation
    pending = user_wallet_config.pendingWhitelist(charlie)
    initiated_block = pending.initiatedBlock
    confirm_block = pending.confirmBlock
    
    # Cancel the pending whitelist
    kernel.cancelPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Verify pending whitelist is cleared
    pending_after = user_wallet_config.pendingWhitelist(charlie)
    assert pending_after.initiatedBlock == 0
    assert pending_after.confirmBlock == 0
    assert pending_after.currentOwner == ZERO_ADDRESS
    
    # Verify address is not whitelisted
    assert user_wallet_config.indexOfWhitelist(charlie) == 0
    
    # Verify event emission
    log = filter_logs(kernel, "WhitelistAddrCancelled")[0]
    assert log.user == user_wallet.address
    assert log.addr == charlie
    assert log.initiatedBlock == initiated_block
    assert log.confirmBlock == confirm_block
    assert log.cancelledBy == bob


def test_cancel_pending_whitelist_no_pending(kernel, user_wallet, bob, charlie):
    """Test cannot cancel non-existent pending whitelist"""
    # Try to cancel without adding pending first
    with boa.reverts("no pending whitelist"):
        kernel.cancelPendingWhitelistAddr(user_wallet, charlie, sender=bob)


def test_cancel_pending_whitelist_after_timelock(kernel, user_wallet, user_wallet_config, bob, alice):
    """Test can cancel even after timelock expires"""
    # Add pending whitelist
    kernel.addPendingWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Advance blocks past timelock
    boa.env.time_travel(blocks=user_wallet_config.timeLock() + 10)
    
    # Should still be able to cancel
    kernel.cancelPendingWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Verify cancelled
    pending = user_wallet_config.pendingWhitelist(alice)
    assert pending.initiatedBlock == 0


def test_cancel_pending_whitelist_invalid_user_wallet(kernel, bob, alice):
    """Test validation of user wallet"""
    # Try with random address that's not a user wallet
    with boa.reverts("invalid user wallet"):
        kernel.cancelPendingWhitelistAddr(alice, bob, sender=bob)


def test_cancel_pending_whitelist_by_manager(createGlobalManagerSettings, createWhitelistPerms, createManagerSettings, kernel, user_wallet, user_wallet_config, alice, charlie, bob, high_command):
    """Test manager can cancel pending whitelist with proper permissions"""
    # Setup manager with cancel permission
    whitelist_perms = createWhitelistPerms(_canAddPending=False, _canConfirm=False, _canCancel=True, _canRemove=False)
    new_global_manager_settings = createGlobalManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    new_manager_settings = createManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Owner adds pending whitelist
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Manager cancels the pending whitelist
    kernel.cancelPendingWhitelistAddr(user_wallet, charlie, sender=alice)
    
    # Verify event shows manager as cancelledBy
    log = filter_logs(kernel, "WhitelistAddrCancelled")[0]
    assert log.cancelledBy == alice
    
    # Verify cancelled
    pending = user_wallet_config.pendingWhitelist(charlie)
    assert pending.initiatedBlock == 0


def test_cancel_pending_whitelist_by_security_action(kernel, user_wallet, user_wallet_config, bob, charlie, alice, mission_control, switchboard_alpha):
    """Test security action permission can cancel pending whitelist"""
    # Set alice as security operator
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)
    
    # Add pending whitelist
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Alice doesn't have cancel permission but has security action permission
    # This should work via security action fallback
    kernel.cancelPendingWhitelistAddr(user_wallet, charlie, sender=alice)
    
    # Verify cancelled
    pending = user_wallet_config.pendingWhitelist(charlie)
    assert pending.initiatedBlock == 0
    
    # Verify event shows alice as cancelledBy
    log = filter_logs(kernel, "WhitelistAddrCancelled")[0]
    assert log.cancelledBy == alice


def test_cancel_pending_whitelist_no_permission(kernel, user_wallet, bob, charlie, alice):
    """Test cannot cancel without proper permissions"""
    # Add pending whitelist
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Alice has no permissions
    with boa.reverts("no perms"):
        kernel.cancelPendingWhitelistAddr(user_wallet, charlie, sender=alice)


def test_cancel_then_add_again(kernel, user_wallet, user_wallet_config, bob, charlie):
    """Test can add pending whitelist again after cancellation"""
    # Add pending whitelist
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Cancel it
    kernel.cancelPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Should be able to add again
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Verify new pending exists
    pending = user_wallet_config.pendingWhitelist(charlie)
    assert pending.initiatedBlock != 0
    assert pending.confirmBlock != 0


def test_cancel_pending_whitelist_already_confirmed(kernel, user_wallet, user_wallet_config, bob, alice):
    """Test cannot cancel after confirmation"""
    # Add and confirm whitelist
    kernel.addPendingWhitelistAddr(user_wallet, alice, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    kernel.confirmWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Try to cancel - should fail because no pending exists anymore
    with boa.reverts("no pending whitelist"):
        kernel.cancelPendingWhitelistAddr(user_wallet, alice, sender=bob)


######################
# Whitelist - Remove #
######################


def test_remove_whitelist_success(kernel, user_wallet, user_wallet_config, bob, charlie):
    """Test successful whitelist removal by owner"""
    # First add and confirm whitelist
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    kernel.confirmWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Verify whitelisted
    assert user_wallet_config.indexOfWhitelist(charlie) != 0
    
    # Remove from whitelist
    kernel.removeWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Verify no longer whitelisted
    assert user_wallet_config.indexOfWhitelist(charlie) == 0
    
    # Verify event emission
    log = filter_logs(kernel, "WhitelistAddrRemoved")[0]
    assert log.user == user_wallet.address
    assert log.addr == charlie
    assert log.removedBy == bob


def test_remove_whitelist_not_whitelisted(kernel, user_wallet, bob, charlie):
    """Test cannot remove non-whitelisted address"""
    # Try to remove without whitelisting first
    with boa.reverts("not whitelisted"):
        kernel.removeWhitelistAddr(user_wallet, charlie, sender=bob)


def test_remove_whitelist_after_removal(kernel, user_wallet, user_wallet_config, bob, alice):
    """Test cannot remove already removed address"""
    # Add, confirm, and remove
    kernel.addPendingWhitelistAddr(user_wallet, alice, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    kernel.confirmWhitelistAddr(user_wallet, alice, sender=bob)
    kernel.removeWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Try to remove again
    with boa.reverts("not whitelisted"):
        kernel.removeWhitelistAddr(user_wallet, alice, sender=bob)


def test_remove_whitelist_invalid_user_wallet(kernel, bob, alice):
    """Test validation of user wallet"""
    # Try with random address that's not a user wallet
    with boa.reverts("invalid user wallet"):
        kernel.removeWhitelistAddr(alice, bob, sender=bob)


def test_remove_whitelist_by_manager(createGlobalManagerSettings, createWhitelistPerms, createManagerSettings, kernel, user_wallet, user_wallet_config, alice, charlie, bob, high_command):
    """Test manager can remove whitelist with proper permissions"""
    # Setup manager with remove permission
    whitelist_perms = createWhitelistPerms(_canAddPending=False, _canConfirm=False, _canCancel=False, _canRemove=True)
    new_global_manager_settings = createGlobalManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    new_manager_settings = createManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Owner adds and confirms whitelist
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    kernel.confirmWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Manager removes from whitelist
    kernel.removeWhitelistAddr(user_wallet, charlie, sender=alice)
    
    # Verify event shows manager as removedBy
    log = filter_logs(kernel, "WhitelistAddrRemoved")[0]
    assert log.removedBy == alice
    
    # Verify removed
    assert user_wallet_config.indexOfWhitelist(charlie) == 0


def test_remove_whitelist_by_security_action(kernel, user_wallet, user_wallet_config, bob, charlie, alice, mission_control, switchboard_alpha):
    """Test security action permission can remove whitelist"""
    # Set alice as security operator
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)
    
    # Owner adds and confirms whitelist
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    kernel.confirmWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Alice doesn't have remove permission but has security action permission
    # This should work via security action fallback
    kernel.removeWhitelistAddr(user_wallet, charlie, sender=alice)
    
    # Verify removed
    assert user_wallet_config.indexOfWhitelist(charlie) == 0
    
    # Verify event shows alice as removedBy
    log = filter_logs(kernel, "WhitelistAddrRemoved")[0]
    assert log.removedBy == alice


def test_remove_whitelist_no_permission(kernel, user_wallet, user_wallet_config, bob, charlie, alice):
    """Test cannot remove without proper permissions"""
    # Add and confirm whitelist as owner
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    kernel.confirmWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Alice has no permissions
    with boa.reverts("no perms"):
        kernel.removeWhitelistAddr(user_wallet, charlie, sender=alice)


def test_remove_then_add_again(kernel, user_wallet, user_wallet_config, bob, charlie):
    """Test can add to whitelist again after removal"""
    # Add, confirm, and remove
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    kernel.confirmWhitelistAddr(user_wallet, charlie, sender=bob)
    kernel.removeWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Should be able to add again
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Verify new pending exists
    pending = user_wallet_config.pendingWhitelist(charlie)
    assert pending.initiatedBlock != 0
    assert pending.confirmBlock != 0
    
    # Confirm again
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    kernel.confirmWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Verify whitelisted again
    assert user_wallet_config.indexOfWhitelist(charlie) != 0


def test_remove_whitelist_pending_exists(kernel, user_wallet, user_wallet_config, bob, alice):
    """Test pending whitelist is independent of confirmed whitelist"""
    # Add and confirm alice to whitelist
    kernel.addPendingWhitelistAddr(user_wallet, alice, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    kernel.confirmWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Add pending for alice again (should fail)
    with boa.reverts("already whitelisted"):
        kernel.addPendingWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Remove alice from whitelist
    kernel.removeWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Now can add pending again
    kernel.addPendingWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Verify pending exists
    pending = user_wallet_config.pendingWhitelist(alice)
    assert pending.initiatedBlock != 0

