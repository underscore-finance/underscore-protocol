import pytest
import boa

from conf_utils import filter_logs
from constants import ZERO_ADDRESS


@pytest.fixture(scope="session")
def mock_sentinel():
    return boa.load("contracts/mock/MockSentinel.vy", name="mock_sentinel")


@pytest.fixture(scope="session")  
def mock_sentinel_v2():
    return boa.load("contracts/mock/MockSentinel.vy", name="mock_sentinel_v2")


@pytest.fixture(scope="session")
def mock_high_command():
    return boa.load("contracts/mock/MockRando.vy", name="mock_high_command")


@pytest.fixture(scope="session")
def mock_paymaster():
    return boa.load("contracts/mock/MockRando.vy", name="mock_paymaster")


@pytest.fixture(scope="session")
def mock_migrator():
    return boa.load("contracts/mock/MockRando.vy", name="mock_migrator")


####################
# Add Pending Item #
####################


def test_add_pending_sentinel(wallet_backpack, governance, mock_sentinel):
    # Add pending sentinel
    result = wallet_backpack.addPendingSentinel(mock_sentinel.address, sender=governance.address)
    logs = filter_logs(wallet_backpack, "PendingBackpackItemAdded")
    
    # The function returns bool
    assert result == True

    # Check pending data - pendingUpdates is indexed by BackpackType
    # BackpackType.WALLET_SENTINEL = 1
    pending_data = wallet_backpack.pendingUpdates(1)
    assert pending_data.actionId > 0
    assert pending_data.addr == mock_sentinel.address
    
    # Check event details
    assert len(logs) == 1
    assert logs[0].actionId == pending_data.actionId
    assert logs[0].addr == mock_sentinel.address
    assert logs[0].backpackType == 1  # WALLET_SENTINEL
    assert logs[0].confirmationBlock > 0
    assert logs[0].addedBy == governance.address



def test_add_pending_high_command(wallet_backpack, governance, mock_high_command):
    # Add pending high command
    wallet_backpack.addPendingHighCommand(mock_high_command.address, sender=governance.address)
    logs = filter_logs(wallet_backpack, "PendingBackpackItemAdded")
    
    # Check pending data - BackpackType.WALLET_HIGH_COMMAND = 2
    pending_data = wallet_backpack.pendingUpdates(2)
    assert pending_data.actionId > 0
    assert pending_data.addr == mock_high_command.address
    
    # Check event details
    assert len(logs) == 1
    assert logs[0].actionId == pending_data.actionId
    assert logs[0].addr == mock_high_command.address
    assert logs[0].backpackType == 2  # WALLET_HIGH_COMMAND
    assert logs[0].confirmationBlock > 0
    assert logs[0].addedBy == governance.address


def test_add_pending_paymaster(wallet_backpack, governance, mock_paymaster):
    # Add pending paymaster
    result = wallet_backpack.addPendingPaymaster(mock_paymaster.address, sender=governance.address)
    logs = filter_logs(wallet_backpack, "PendingBackpackItemAdded")
    assert result == True
    
    # Check pending data - BackpackType.WALLET_PAYMASTER = 4 (flag enum)
    pending_data = wallet_backpack.pendingUpdates(4)
    assert pending_data.actionId > 0
    assert pending_data.addr == mock_paymaster.address
    
    # Check event details
    assert len(logs) == 1
    assert logs[0].actionId == pending_data.actionId
    assert logs[0].addr == mock_paymaster.address
    assert logs[0].backpackType == 4  # WALLET_PAYMASTER
    assert logs[0].confirmationBlock > 0
    assert logs[0].addedBy == governance.address


def test_add_pending_migrator(wallet_backpack, governance, mock_migrator):
    # Add pending migrator
    result = wallet_backpack.addPendingMigrator(mock_migrator.address, sender=governance.address)
    logs = filter_logs(wallet_backpack, "PendingBackpackItemAdded")
    assert result == True
    
    # Check pending data - BackpackType.WALLET_MIGRATOR = 8 (flag enum)
    pending_data = wallet_backpack.pendingUpdates(8)
    assert pending_data.actionId > 0
    assert pending_data.addr == mock_migrator.address
    
    # Check event details
    assert len(logs) == 1
    assert logs[0].actionId == pending_data.actionId
    assert logs[0].addr == mock_migrator.address
    assert logs[0].backpackType == 8  # WALLET_MIGRATOR
    assert logs[0].confirmationBlock > 0
    assert logs[0].addedBy == governance.address


def test_add_pending_duplicate_reverts(wallet_backpack, governance, mock_sentinel):
    # Add pending sentinel
    wallet_backpack.addPendingSentinel(mock_sentinel.address, sender=governance.address)
    
    # Try to add any sentinel again while one is pending - should revert
    with boa.reverts("already pending"):
        wallet_backpack.addPendingSentinel(mock_sentinel.address, sender=governance.address)


def test_add_pending_zero_address_reverts(wallet_backpack, governance):
    # Try to add zero address items - should revert with "invalid item"
    with boa.reverts("invalid item"):
        wallet_backpack.addPendingSentinel(ZERO_ADDRESS, sender=governance.address)
    
    with boa.reverts("invalid item"):
        wallet_backpack.addPendingHighCommand(ZERO_ADDRESS, sender=governance.address)
    
    with boa.reverts("invalid item"):
        wallet_backpack.addPendingPaymaster(ZERO_ADDRESS, sender=governance.address)
    
    with boa.reverts("invalid item"):
        wallet_backpack.addPendingMigrator(ZERO_ADDRESS, sender=governance.address)


def test_add_pending_non_governance_reverts(wallet_backpack, alice, mock_sentinel):
    # Try to add pending item from non-governance - should revert with "no perms"
    with boa.reverts("no perms"):
        wallet_backpack.addPendingSentinel(mock_sentinel.address, sender=alice)


def test_add_pending_when_paused_reverts(wallet_backpack, governance, mock_sentinel, switchboard_alpha):
    # Pause the contract - only switchboard can pause
    wallet_backpack.pause(True, sender=switchboard_alpha.address)
    
    # Try to add pending item - should revert with "no perms" because paused
    with boa.reverts("no perms"):
        wallet_backpack.addPendingSentinel(mock_sentinel.address, sender=governance.address)


###################
# Confirm Pending #
###################


def test_confirm_sentinel_success(wallet_backpack, governance, mock_sentinel, ledger):
    # Add pending sentinel
    wallet_backpack.addPendingSentinel(mock_sentinel.address, sender=governance.address)
    pending_data = wallet_backpack.pendingUpdates(1)
    assert pending_data.addr == mock_sentinel.address
    assert pending_data.actionId > 0
    stored_action_id = pending_data.actionId
    
    # go to confirm block
    boa.env.time_travel(blocks=wallet_backpack.actionTimeLock())
    
    # Confirm the sentinel (no address parameter)
    result = wallet_backpack.confirmPendingSentinel(sender=governance.address)
    confirm_logs = filter_logs(wallet_backpack, "BackpackItemConfirmed")
    
    assert result == True
    
    # Check sentinel is set
    assert wallet_backpack.sentinel() == mock_sentinel.address
    
    # Check pending data is cleared
    pending_data = wallet_backpack.pendingUpdates(1)
    assert pending_data.actionId == 0
    
    # Check confirm event details
    assert len(confirm_logs) == 1
    assert confirm_logs[0].backpackType == 1  # WALLET_SENTINEL
    assert confirm_logs[0].addr == mock_sentinel.address
    assert confirm_logs[0].actionId == stored_action_id
    assert confirm_logs[0].confirmedBy == governance.address
    
    assert ledger.isRegisteredBackpackItem(mock_sentinel.address) == True


def test_confirm_high_command_success(wallet_backpack, governance, mock_high_command, ledger):
    # Add and confirm high command
    wallet_backpack.addPendingHighCommand(mock_high_command.address, sender=governance.address)
    
    pending_data = wallet_backpack.pendingUpdates(2)  # WALLET_HIGH_COMMAND = 2
    assert pending_data.addr == mock_high_command.address
    assert pending_data.actionId > 0
    stored_action_id = pending_data.actionId
    
    # go to confirm block
    boa.env.time_travel(blocks=wallet_backpack.actionTimeLock())
    
    wallet_backpack.confirmPendingHighCommand(sender=governance.address)
    confirm_logs = filter_logs(wallet_backpack, "BackpackItemConfirmed")
    
    # Verify
    assert wallet_backpack.highCommand() == mock_high_command.address
    
    # Check pending data is cleared
    pending_data = wallet_backpack.pendingUpdates(2)
    assert pending_data.actionId == 0
    
    # Check confirm event details
    assert len(confirm_logs) == 1
    assert confirm_logs[0].backpackType == 2  # WALLET_HIGH_COMMAND
    assert confirm_logs[0].addr == mock_high_command.address
    assert confirm_logs[0].actionId == stored_action_id
    assert confirm_logs[0].confirmedBy == governance.address
    
    assert ledger.isRegisteredBackpackItem(mock_high_command.address) == True


def test_confirm_paymaster_success(wallet_backpack, governance, mock_paymaster, ledger):
    # Add pending paymaster
    wallet_backpack.addPendingPaymaster(mock_paymaster.address, sender=governance.address)
    
    pending_data = wallet_backpack.pendingUpdates(4)  # WALLET_PAYMASTER = 4
    assert pending_data.addr == mock_paymaster.address
    assert pending_data.actionId > 0
    stored_action_id = pending_data.actionId
    
    # go to confirm block
    boa.env.time_travel(blocks=wallet_backpack.actionTimeLock())
    
    # Confirm the paymaster
    result = wallet_backpack.confirmPendingPaymaster(sender=governance.address)
    confirm_logs = filter_logs(wallet_backpack, "BackpackItemConfirmed")
    
    assert result == True
    
    # Check paymaster is set
    assert wallet_backpack.paymaster() == mock_paymaster.address
    
    # Check pending data is cleared
    pending_data = wallet_backpack.pendingUpdates(4)
    assert pending_data.actionId == 0
    
    # Check confirm event details
    assert len(confirm_logs) == 1
    assert confirm_logs[0].backpackType == 4  # WALLET_PAYMASTER
    assert confirm_logs[0].addr == mock_paymaster.address
    assert confirm_logs[0].actionId == stored_action_id
    assert confirm_logs[0].confirmedBy == governance.address
    
    assert ledger.isRegisteredBackpackItem(mock_paymaster.address) == True


def test_confirm_migrator_success(wallet_backpack, governance, mock_migrator, ledger):
    # Add pending migrator
    wallet_backpack.addPendingMigrator(mock_migrator.address, sender=governance.address)
    
    pending_data = wallet_backpack.pendingUpdates(8)  # WALLET_MIGRATOR = 8
    assert pending_data.addr == mock_migrator.address
    assert pending_data.actionId > 0
    stored_action_id = pending_data.actionId
    
    # go to confirm block
    boa.env.time_travel(blocks=wallet_backpack.actionTimeLock())
    
    # Confirm the migrator
    result = wallet_backpack.confirmPendingMigrator(sender=governance.address)
    confirm_logs = filter_logs(wallet_backpack, "BackpackItemConfirmed")
    
    assert result == True
    
    # Check migrator is set
    assert wallet_backpack.migrator() == mock_migrator.address
    
    # Check pending data is cleared
    pending_data = wallet_backpack.pendingUpdates(8)
    assert pending_data.actionId == 0
    
    # Check confirm event details
    assert len(confirm_logs) == 1
    assert confirm_logs[0].backpackType == 8  # WALLET_MIGRATOR
    assert confirm_logs[0].addr == mock_migrator.address
    assert confirm_logs[0].actionId == stored_action_id
    assert confirm_logs[0].confirmedBy == governance.address
    
    assert ledger.isRegisteredBackpackItem(mock_migrator.address) == True


def test_confirm_before_timelock_reverts(wallet_backpack, governance, mock_sentinel):
    # Add pending sentinel
    wallet_backpack.addPendingSentinel(mock_sentinel.address, sender=governance.address)
    
    # Try to confirm immediately - should revert
    with boa.reverts("time lock not reached"):
        wallet_backpack.confirmPendingSentinel(sender=governance.address)


def test_confirm_non_pending_reverts(wallet_backpack, governance):
    # Try to confirm non-existing pending action
    with boa.reverts("no pending item"):
        wallet_backpack.confirmPendingSentinel(sender=governance.address)


def test_confirm_wrong_type_reverts(wallet_backpack, governance, mock_sentinel):
    # Add pending sentinel
    wallet_backpack.addPendingSentinel(mock_sentinel.address, sender=governance.address)
    
    # Travel past timelock
    boa.env.time_travel(blocks=wallet_backpack.actionTimeLock())
    
    # Try to confirm as wrong type - should revert with "no pending item"
    with boa.reverts("no pending item"):
        wallet_backpack.confirmPendingHighCommand(sender=governance.address)


def test_confirm_expired_reverts(wallet_backpack, governance, mock_sentinel):
    # Add pending sentinel
    wallet_backpack.addPendingSentinel(mock_sentinel.address, sender=governance.address)
    
    # Travel past expiration (confirmBlock + expiration)
    boa.env.time_travel(blocks=wallet_backpack.actionTimeLock() + wallet_backpack.expiration() + 1)
    
    # Try to confirm - should revert with time lock not reached (TimeLock returns False on expiration)
    with boa.reverts("time lock not reached"):
        wallet_backpack.confirmPendingSentinel(sender=governance.address)


##################
# Cancel Pending #
##################


def test_cancel_pending_success(wallet_backpack, governance, mock_sentinel):
    # Add pending sentinel
    wallet_backpack.addPendingSentinel(mock_sentinel.address, sender=governance.address)
    
    # Store the action ID before canceling
    pending_data = wallet_backpack.pendingUpdates(1)
    stored_action_id = pending_data.actionId
    
    # Cancel it
    result = wallet_backpack.cancelPendingSentinel(sender=governance.address)
    cancel_logs = filter_logs(wallet_backpack, "PendingBackpackItemCancelled")
    assert result == True
    
    # Check pending data is cleared
    pending_data = wallet_backpack.pendingUpdates(1)
    assert pending_data.actionId == 0
    
    # Check cancel event details
    assert len(cancel_logs) == 1
    assert cancel_logs[0].backpackType == 1  # WALLET_SENTINEL
    assert cancel_logs[0].addr == mock_sentinel.address
    assert cancel_logs[0].actionId == stored_action_id
    assert cancel_logs[0].cancelledBy == governance.address


def test_cancel_non_existing_reverts(wallet_backpack, governance):
    # Try to cancel non-existing pending action
    with boa.reverts("cannot cancel action"):
        wallet_backpack.cancelPendingSentinel(sender=governance.address)


def test_cancel_non_governance_reverts(wallet_backpack, governance, alice, mock_sentinel):
    # Add pending sentinel
    wallet_backpack.addPendingSentinel(mock_sentinel.address, sender=governance.address)
    
    # Try to cancel from non-governance
    with boa.reverts("no perms"):
        wallet_backpack.cancelPendingSentinel(sender=alice)


####################
# Validation Tests #
####################


def test_validate_sentinel_interface(wallet_backpack, governance, alice):
    # Try to add a non-sentinel contract (using alice as a regular address)
    with boa.reverts("invalid item"):
        wallet_backpack.addPendingSentinel(alice, sender=governance.address)


def test_validate_duplicate_sentinel(wallet_backpack, governance, mock_sentinel):
    # First confirm a sentinel
    wallet_backpack.addPendingSentinel(mock_sentinel.address, sender=governance.address)
    boa.env.time_travel(blocks=wallet_backpack.actionTimeLock())
    wallet_backpack.confirmPendingSentinel(sender=governance.address)
    
    # Try to add the same sentinel again
    with boa.reverts("invalid item"):
        wallet_backpack.addPendingSentinel(mock_sentinel.address, sender=governance.address)


def test_validate_duplicate_high_command(wallet_backpack, governance, mock_high_command):
    # Confirm high command
    wallet_backpack.addPendingHighCommand(mock_high_command.address, sender=governance.address)
    boa.env.time_travel(blocks=wallet_backpack.actionTimeLock())
    wallet_backpack.confirmPendingHighCommand(sender=governance.address)
    
    # Try to add the same high command again
    with boa.reverts("invalid item"):
        wallet_backpack.addPendingHighCommand(mock_high_command.address, sender=governance.address)


def test_validate_duplicate_paymaster(wallet_backpack, governance, mock_paymaster):
    # Confirm paymaster
    wallet_backpack.addPendingPaymaster(mock_paymaster.address, sender=governance.address)
    boa.env.time_travel(blocks=wallet_backpack.actionTimeLock())
    wallet_backpack.confirmPendingPaymaster(sender=governance.address)
    
    # Try to add the same paymaster again
    with boa.reverts("invalid item"):
        wallet_backpack.addPendingPaymaster(mock_paymaster.address, sender=governance.address)


def test_validate_duplicate_migrator(wallet_backpack, governance, mock_migrator):
    # Confirm migrator
    wallet_backpack.addPendingMigrator(mock_migrator.address, sender=governance.address)
    boa.env.time_travel(blocks=wallet_backpack.actionTimeLock())
    wallet_backpack.confirmPendingMigrator(sender=governance.address)
    
    # Try to add the same migrator again
    with boa.reverts("invalid item"):
        wallet_backpack.addPendingMigrator(mock_migrator.address, sender=governance.address)


#####################
# Integration Tests #
#####################


def test_full_backpack_setup(wallet_backpack, governance, mock_sentinel, mock_high_command, mock_paymaster, mock_migrator, ledger):
    # Add all pending items
    wallet_backpack.addPendingSentinel(mock_sentinel.address, sender=governance.address)
    wallet_backpack.addPendingHighCommand(mock_high_command.address, sender=governance.address)
    wallet_backpack.addPendingPaymaster(mock_paymaster.address, sender=governance.address)
    wallet_backpack.addPendingMigrator(mock_migrator.address, sender=governance.address)
    
    # Travel past time lock (all items have same timelock)
    boa.env.time_travel(blocks=wallet_backpack.actionTimeLock())
    
    # Confirm all items
    wallet_backpack.confirmPendingSentinel(sender=governance.address)
    wallet_backpack.confirmPendingHighCommand(sender=governance.address)
    wallet_backpack.confirmPendingPaymaster(sender=governance.address)
    wallet_backpack.confirmPendingMigrator(sender=governance.address)
    
    # Verify all are set
    assert wallet_backpack.sentinel() == mock_sentinel.address
    assert wallet_backpack.highCommand() == mock_high_command.address
    assert wallet_backpack.paymaster() == mock_paymaster.address
    assert wallet_backpack.migrator() == mock_migrator.address
    
    # Verify all are registered in Ledger
    assert ledger.isRegisteredBackpackItem(mock_sentinel.address)
    assert ledger.isRegisteredBackpackItem(mock_high_command.address)
    assert ledger.isRegisteredBackpackItem(mock_paymaster.address)
    assert ledger.isRegisteredBackpackItem(mock_migrator.address)


def test_update_existing_item(wallet_backpack, governance, mock_sentinel, mock_sentinel_v2, ledger):
    # Setup initial sentinel
    wallet_backpack.addPendingSentinel(mock_sentinel.address, sender=governance.address)
    boa.env.time_travel(blocks=wallet_backpack.actionTimeLock())
    wallet_backpack.confirmPendingSentinel(sender=governance.address)
    
    # Update to new sentinel
    wallet_backpack.addPendingSentinel(mock_sentinel_v2.address, sender=governance.address)
    boa.env.time_travel(blocks=wallet_backpack.actionTimeLock())
    wallet_backpack.confirmPendingSentinel(sender=governance.address)
    
    # Verify update
    assert wallet_backpack.sentinel() == mock_sentinel_v2.address
    assert ledger.isRegisteredBackpackItem(mock_sentinel_v2.address)


##############
# Edge Cases #
##############


def test_multiple_pending_different_types(wallet_backpack, governance, mock_sentinel, mock_high_command):
    # Add multiple pending items of different types
    wallet_backpack.addPendingSentinel(mock_sentinel.address, sender=governance.address)
    wallet_backpack.addPendingHighCommand(mock_high_command.address, sender=governance.address)
    
    # Verify both are pending
    sentinel_pending = wallet_backpack.pendingUpdates(1)  # WALLET_SENTINEL
    high_command_pending = wallet_backpack.pendingUpdates(2)  # WALLET_HIGH_COMMAND
    
    assert sentinel_pending.actionId > 0
    assert high_command_pending.actionId > 0
    assert sentinel_pending.addr == mock_sentinel.address
    assert high_command_pending.addr == mock_high_command.address


def test_time_lock_boundaries(wallet_backpack, governance, mock_sentinel):
    # Add pending item
    wallet_backpack.addPendingSentinel(mock_sentinel.address, sender=governance.address)
    
    # Travel to one block before the timelock is reached
    boa.env.time_travel(blocks=wallet_backpack.actionTimeLock() - 1)
    
    # Should still revert
    with boa.reverts("time lock not reached"):
        wallet_backpack.confirmPendingSentinel(sender=governance.address)
    
    # Travel one more block to reach exactly the timelock
    boa.env.time_travel(blocks=1)
    
    # Now should succeed
    wallet_backpack.confirmPendingSentinel(sender=governance.address)
