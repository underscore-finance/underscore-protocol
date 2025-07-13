import pytest
import boa

from config.BluePrint import PARAMS
from conf_utils import filter_logs
from constants import ZERO_ADDRESS


@pytest.fixture(scope="module")
def mock_ownership(undy_hq, bob, fork):
    return boa.load(
        "contracts/mock/MockOwnership.vy",
        undy_hq,
        bob,
        PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"],
        PARAMS[fork]["UNDY_HQ_MAX_GOV_TIMELOCK"],
        name="mock_ownership",
    )


# deployment tests


def test_ownership_deployment(mock_ownership, bob, fork):
    # Check initial state
    assert mock_ownership.owner() == bob
    assert mock_ownership.ownershipTimeLock() == PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"]
    assert mock_ownership.MIN_OWNERSHIP_TIMELOCK() == PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"]
    assert mock_ownership.MAX_OWNERSHIP_TIMELOCK() == PARAMS[fork]["UNDY_HQ_MAX_GOV_TIMELOCK"]
    
    # Check no pending ownership change
    assert not mock_ownership.hasPendingOwnerChange()

    pending = mock_ownership.pendingOwner()
    assert pending.newOwner == ZERO_ADDRESS
    assert pending.initiatedBlock == 0
    assert pending.confirmBlock == 0


def test_ownership_deployment_invalid_addresses(undy_hq, bob, fork):
    # Invalid undy hq
    with boa.reverts("invalid addrs"):
        boa.load(
            "contracts/mock/MockOwnership.vy",
            ZERO_ADDRESS,  # zero address
            bob,
            PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"],
            PARAMS[fork]["UNDY_HQ_MAX_GOV_TIMELOCK"],
        )
    
    # Invalid owner
    with boa.reverts("invalid addrs"):
        boa.load(
            "contracts/mock/MockOwnership.vy",
            undy_hq,
            ZERO_ADDRESS,  # zero address
            PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"],
            PARAMS[fork]["UNDY_HQ_MAX_GOV_TIMELOCK"],
        )


def test_ownership_deployment_invalid_timelock(undy_hq, bob, fork):
    # Zero min timelock
    with boa.reverts("invalid delay"):
        boa.load(
            "contracts/mock/MockOwnership.vy",
            undy_hq,
            bob,
            0,
            PARAMS[fork]["UNDY_HQ_MAX_GOV_TIMELOCK"],
        )
    
    # Min >= Max
    with boa.reverts("invalid delay"):
        boa.load(
            "contracts/mock/MockOwnership.vy",
            undy_hq,
            bob,
            PARAMS[fork]["UNDY_HQ_MAX_GOV_TIMELOCK"],
            PARAMS[fork]["UNDY_HQ_MAX_GOV_TIMELOCK"],
        )


# ownership change tests


def test_change_ownership_basic(mock_ownership, bob, alice):
    # Initial state
    assert mock_ownership.owner() == bob
    assert not mock_ownership.hasPendingOwnerChange()
    
    # Change ownership
    mock_ownership.changeOwnership(alice, sender=bob)
    
    # Check event
    event_log = filter_logs(mock_ownership, "OwnershipChangeInitiated")[0]
    assert event_log.prevOwner == bob
    assert event_log.newOwner == alice
    assert event_log.confirmBlock == boa.env.evm.patch.block_number + mock_ownership.ownershipTimeLock()
    
    # Check pending state
    assert mock_ownership.hasPendingOwnerChange()

    pending = mock_ownership.pendingOwner()
    assert pending.newOwner == alice
    assert pending.initiatedBlock == boa.env.evm.patch.block_number
    assert pending.confirmBlock == event_log.confirmBlock
    
    # Owner should still be bob until confirmed
    assert mock_ownership.owner() == bob


def test_change_ownership_no_permissions(mock_ownership, alice, charlie):
    # Non-owner cannot change ownership
    with boa.reverts("no perms"):
        mock_ownership.changeOwnership(charlie, sender=alice)


def test_change_ownership_invalid_new_owner(mock_ownership, bob):
    # Cannot change to zero address
    with boa.reverts("invalid new owner"):
        mock_ownership.changeOwnership(ZERO_ADDRESS, sender=bob)
    
    # Cannot change to same owner
    with boa.reverts("invalid new owner"):
        mock_ownership.changeOwnership(bob, sender=bob)


def test_change_ownership_overwrites_pending(mock_ownership, bob, alice, charlie):
    # Start first ownership change
    mock_ownership.changeOwnership(alice, sender=bob)
    
    pending1 = mock_ownership.pendingOwner()
    assert pending1.newOwner == alice
    
    # Start second ownership change (overwrites first)
    mock_ownership.changeOwnership(charlie, sender=bob)
    
    # Check that pending change is overwritten
    pending2 = mock_ownership.pendingOwner()
    assert pending2.newOwner == charlie
    assert pending2.newOwner != pending1.newOwner


# confirm ownership tests


def test_confirm_ownership_change_basic(mock_ownership, bob, alice):
    time_lock = mock_ownership.ownershipTimeLock()
    
    # Change ownership
    mock_ownership.changeOwnership(alice, sender=bob)
    
    pending = mock_ownership.pendingOwner()
    initiated_block = pending.initiatedBlock
    confirm_block = pending.confirmBlock
    
    # Cannot confirm before time lock
    with boa.reverts("time delay not reached"):
        mock_ownership.confirmOwnershipChange(sender=alice)
    
    # Time travel past time lock
    boa.env.time_travel(blocks=time_lock)
    
    # Confirm ownership change
    mock_ownership.confirmOwnershipChange(sender=alice)
    
    # Check event
    event_log = filter_logs(mock_ownership, "OwnershipChangeConfirmed")[0]
    assert event_log.prevOwner == bob
    assert event_log.newOwner == alice
    assert event_log.initiatedBlock == initiated_block
    assert event_log.confirmBlock == confirm_block
    
    # Check state changes
    assert mock_ownership.owner() == alice
    assert not mock_ownership.hasPendingOwnerChange()
    
    # Pending should be cleared
    pending = mock_ownership.pendingOwner()
    assert pending.newOwner == ZERO_ADDRESS
    assert pending.initiatedBlock == 0
    assert pending.confirmBlock == 0


def test_confirm_ownership_no_pending(mock_ownership, alice):
    # Cannot confirm when no pending change
    with boa.reverts("no pending owner"):
        mock_ownership.confirmOwnershipChange(sender=alice)


def test_confirm_ownership_wrong_caller(mock_ownership, bob, alice, charlie):
    # Change ownership
    mock_ownership.changeOwnership(alice, sender=bob)
    
    # Time travel past time lock
    boa.env.time_travel(blocks=mock_ownership.ownershipTimeLock())
    
    # Only new owner can confirm
    with boa.reverts("only new owner can confirm"):
        mock_ownership.confirmOwnershipChange(sender=bob)
    
    with boa.reverts("only new owner can confirm"):
        mock_ownership.confirmOwnershipChange(sender=charlie)


def test_confirm_ownership_exact_time_boundary(mock_ownership, bob, alice):
    time_lock = mock_ownership.ownershipTimeLock()
    
    # Change ownership
    mock_ownership.changeOwnership(alice, sender=bob)
    
    # Time travel to exactly the confirm block
    boa.env.time_travel(blocks=time_lock - 1)
    
    # Should still fail (need >= confirm block)
    with boa.reverts("time delay not reached"):
        mock_ownership.confirmOwnershipChange(sender=alice)
    
    # Travel one more block
    boa.env.time_travel(blocks=1)
    
    # Should now succeed
    mock_ownership.confirmOwnershipChange(sender=alice)
    assert mock_ownership.owner() == alice


# cancel ownership tests


def test_cancel_ownership_by_owner(mock_ownership, bob, alice):
    # Change ownership
    mock_ownership.changeOwnership(alice, sender=bob)
    
    pending = mock_ownership.pendingOwner()
    initiated_block = pending.initiatedBlock
    confirm_block = pending.confirmBlock
    
    # Owner can cancel
    mock_ownership.cancelOwnershipChange(sender=bob)
    
    # Check event
    event_log = filter_logs(mock_ownership, "OwnershipChangeCancelled")[0]
    assert event_log.cancelledOwner == alice
    assert event_log.cancelledBy == bob
    assert event_log.initiatedBlock == initiated_block
    assert event_log.confirmBlock == confirm_block
    
    # Check state
    assert mock_ownership.owner() == bob  # unchanged
    assert not mock_ownership.hasPendingOwnerChange()
    
    # Pending should be cleared
    pending = mock_ownership.pendingOwner()
    assert pending.newOwner == ZERO_ADDRESS
    assert pending.confirmBlock == 0


def test_cancel_ownership_by_security_operator(mock_ownership, bob, alice, charlie, mission_control, switchboard_alpha):
    # Set charlie as security operator
    mission_control.setCanPerformSecurityAction(charlie, True, sender=switchboard_alpha.address)
    
    # Change ownership
    mock_ownership.changeOwnership(alice, sender=bob)
    
    # Security operator can cancel
    mock_ownership.cancelOwnershipChange(sender=charlie)
    
    # Check event shows security operator as canceller
    event_log = filter_logs(mock_ownership, "OwnershipChangeCancelled")[0]
    assert event_log.cancelledOwner == alice
    assert event_log.cancelledBy == charlie


def test_cancel_ownership_no_permissions(mock_ownership, bob, alice, charlie):
    # Change ownership
    mock_ownership.changeOwnership(alice, sender=bob)
    
    # Non-owner, non-security-operator cannot cancel
    with boa.reverts("no perms"):
        mock_ownership.cancelOwnershipChange(sender=charlie)


def test_cancel_ownership_no_pending(mock_ownership, bob):
    # Cannot cancel when no pending change
    with boa.reverts("no pending change"):
        mock_ownership.cancelOwnershipChange(sender=bob)


def test_cancel_ownership_after_confirm(mock_ownership, bob, alice):
    time_lock = mock_ownership.ownershipTimeLock()
    
    # Change and confirm ownership
    mock_ownership.changeOwnership(alice, sender=bob)
    boa.env.time_travel(blocks=time_lock)
    mock_ownership.confirmOwnershipChange(sender=alice)
    
    # Cannot cancel after confirmation
    with boa.reverts("no pending change"):
        mock_ownership.cancelOwnershipChange(sender=alice)


# time lock tests


def test_set_ownership_timelock_basic(mock_ownership, bob, fork):
    min_timelock = PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"]
    max_timelock = PARAMS[fork]["UNDY_HQ_MAX_GOV_TIMELOCK"]
    
    # Set to different valid value
    new_timelock = min_timelock + 100
    mock_ownership.setOwnershipTimeLock(new_timelock, sender=bob)
    
    # Check event
    event_log = filter_logs(mock_ownership, "OwnershipTimeLockSet")[0]
    assert event_log.numBlocks == new_timelock
    
    # Check state
    assert mock_ownership.ownershipTimeLock() == new_timelock
    
    # Set to min
    mock_ownership.setOwnershipTimeLock(min_timelock, sender=bob)
    assert mock_ownership.ownershipTimeLock() == min_timelock
    
    # Set to max
    mock_ownership.setOwnershipTimeLock(max_timelock, sender=bob)
    assert mock_ownership.ownershipTimeLock() == max_timelock


def test_set_ownership_timelock_no_permissions(mock_ownership, alice, fork):
    # Non-owner cannot set timelock
    with boa.reverts("no perms"):
        mock_ownership.setOwnershipTimeLock(PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"], sender=alice)


def test_set_ownership_timelock_invalid_values(mock_ownership, bob, fork):
    min_timelock = PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"]
    max_timelock = PARAMS[fork]["UNDY_HQ_MAX_GOV_TIMELOCK"]
    
    # Below minimum
    with boa.reverts("invalid delay"):
        mock_ownership.setOwnershipTimeLock(min_timelock - 1, sender=bob)
    
    # Above maximum
    with boa.reverts("invalid delay"):
        mock_ownership.setOwnershipTimeLock(max_timelock + 1, sender=bob)


def test_ownership_change_uses_current_timelock(mock_ownership, bob, alice, fork):
    min_timelock = PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"]
    
    # Change timelock to longer duration
    new_timelock = min_timelock + 500
    mock_ownership.setOwnershipTimeLock(new_timelock, sender=bob)
    
    # Start ownership change
    mock_ownership.changeOwnership(alice, sender=bob)
    
    # Should use the new timelock
    pending = mock_ownership.pendingOwner()
    expected_confirm_block = boa.env.evm.patch.block_number + new_timelock
    assert pending.confirmBlock == expected_confirm_block


# complex scenarios


def test_ownership_transfer_chain(mock_ownership, bob, alice, charlie):
    time_lock = mock_ownership.ownershipTimeLock()
    
    # Bob -> Alice
    mock_ownership.changeOwnership(alice, sender=bob)
    boa.env.time_travel(blocks=time_lock)
    mock_ownership.confirmOwnershipChange(sender=alice)
    
    assert mock_ownership.owner() == alice
    
    # Alice -> Charlie
    mock_ownership.changeOwnership(charlie, sender=alice)
    boa.env.time_travel(blocks=time_lock)
    mock_ownership.confirmOwnershipChange(sender=charlie)
    
    assert mock_ownership.owner() == charlie
    
    # Charlie -> Bob (complete the circle)
    mock_ownership.changeOwnership(bob, sender=charlie)
    boa.env.time_travel(blocks=time_lock)
    mock_ownership.confirmOwnershipChange(sender=bob)
    
    assert mock_ownership.owner() == bob


def test_ownership_change_with_timelock_modification(mock_ownership, bob, alice, fork):
    min_timelock = PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"]
    
    # Start ownership change with current timelock
    mock_ownership.changeOwnership(alice, sender=bob)
    
    original_confirm_block = mock_ownership.pendingOwner().confirmBlock
    
    # Change timelock (should not affect pending change)
    new_timelock = min_timelock + 200
    mock_ownership.setOwnershipTimeLock(new_timelock, sender=bob)
    
    # Pending change should still use original timelock
    assert mock_ownership.pendingOwner().confirmBlock == original_confirm_block
    
    # Wait for original timelock and confirm
    boa.env.time_travel(blocks=min_timelock)
    mock_ownership.confirmOwnershipChange(sender=alice)
    
    assert mock_ownership.owner() == alice


def test_multiple_ownership_change_attempts(mock_ownership, bob, alice, charlie, sally):
    # Start first change
    mock_ownership.changeOwnership(alice, sender=bob)
    first_confirm_block = mock_ownership.pendingOwner().confirmBlock
    
    # Advance some blocks but not enough
    boa.env.time_travel(blocks=50)
    
    # Start second change (overwrites first)
    mock_ownership.changeOwnership(charlie, sender=bob)
    second_confirm_block = mock_ownership.pendingOwner().confirmBlock
    
    # Should be different confirm blocks
    assert second_confirm_block != first_confirm_block
    assert mock_ownership.pendingOwner().newOwner == charlie
    
    # Start third change (overwrites second)
    mock_ownership.changeOwnership(sally, sender=bob)
    
    # Should now be sally as pending owner
    assert mock_ownership.pendingOwner().newOwner == sally


def test_ownership_change_edge_cases(mock_ownership, bob, alice, charlie):
    time_lock = mock_ownership.ownershipTimeLock()
    
    # Start ownership change to alice
    mock_ownership.changeOwnership(alice, sender=bob)
    
    # Overwrite with change to charlie before confirming
    mock_ownership.changeOwnership(charlie, sender=bob)
    
    # Wait and try to confirm as alice (should fail)
    boa.env.time_travel(blocks=time_lock)
    with boa.reverts("only new owner can confirm"):
        mock_ownership.confirmOwnershipChange(sender=alice)
    
    # Confirm as charlie (the actual pending owner)
    mock_ownership.confirmOwnershipChange(sender=charlie)
    
    # Owner should be charlie, not alice
    assert mock_ownership.owner() == charlie


def test_ownership_operations_after_transfer(mock_ownership, bob, alice):
    time_lock = mock_ownership.ownershipTimeLock()
    
    # Transfer ownership to alice
    mock_ownership.changeOwnership(alice, sender=bob)
    boa.env.time_travel(blocks=time_lock)
    mock_ownership.confirmOwnershipChange(sender=alice)
    
    # Bob should no longer have permissions
    with boa.reverts("no perms"):
        mock_ownership.changeOwnership(bob, sender=bob)
    
    with boa.reverts("no perms"):
        mock_ownership.setOwnershipTimeLock(time_lock + 100, sender=bob)
    
    # Alice should have permissions
    mock_ownership.changeOwnership(bob, sender=alice)
    mock_ownership.setOwnershipTimeLock(time_lock + 100, sender=alice)


# utility function tests


def test_has_pending_owner_change_utility(mock_ownership, bob, alice):
    # Initially no pending change
    assert not mock_ownership.hasPendingOwnerChange()
    
    # After starting change
    mock_ownership.changeOwnership(alice, sender=bob)
    assert mock_ownership.hasPendingOwnerChange()
    
    # After cancelling
    mock_ownership.cancelOwnershipChange(sender=bob)
    assert not mock_ownership.hasPendingOwnerChange()
    
    # After starting and confirming
    mock_ownership.changeOwnership(alice, sender=bob)
    assert mock_ownership.hasPendingOwnerChange()
    
    boa.env.time_travel(blocks=mock_ownership.ownershipTimeLock())
    mock_ownership.confirmOwnershipChange(sender=alice)
    assert not mock_ownership.hasPendingOwnerChange()


# integration tests


def test_ownership_with_different_timelocks(mock_ownership, bob, alice, fork):
    min_timelock = PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"]
    max_timelock = PARAMS[fork]["UNDY_HQ_MAX_GOV_TIMELOCK"]
    
    # Test with minimum timelock
    mock_ownership.setOwnershipTimeLock(min_timelock, sender=bob)
    mock_ownership.changeOwnership(alice, sender=bob)
    
    boa.env.time_travel(blocks=min_timelock)
    mock_ownership.confirmOwnershipChange(sender=alice)
    assert mock_ownership.owner() == alice
    
    # Test with maximum timelock
    mock_ownership.setOwnershipTimeLock(max_timelock, sender=alice)
    mock_ownership.changeOwnership(bob, sender=alice)
    
    boa.env.time_travel(blocks=max_timelock)
    mock_ownership.confirmOwnershipChange(sender=bob)
    assert mock_ownership.owner() == bob


def test_ownership_state_consistency(mock_ownership, bob, alice):
    # Verify initial consistency
    assert mock_ownership.owner() == bob
    assert not mock_ownership.hasPendingOwnerChange()
    
    pending = mock_ownership.pendingOwner()
    assert pending.newOwner == ZERO_ADDRESS
    assert pending.initiatedBlock == 0
    assert pending.confirmBlock == 0
    
    # Start ownership change and verify consistency
    mock_ownership.changeOwnership(alice, sender=bob)
    
    assert mock_ownership.owner() == bob  # unchanged until confirmed
    assert mock_ownership.hasPendingOwnerChange()
    
    pending = mock_ownership.pendingOwner()
    assert pending.newOwner == alice
    assert pending.initiatedBlock == boa.env.evm.patch.block_number
    assert pending.confirmBlock > boa.env.evm.patch.block_number
    
    # Cancel and verify consistency
    mock_ownership.cancelOwnershipChange(sender=bob)
    
    assert mock_ownership.owner() == bob
    assert not mock_ownership.hasPendingOwnerChange()
    
    pending = mock_ownership.pendingOwner()
    assert pending.newOwner == ZERO_ADDRESS
    assert pending.initiatedBlock == 0
    assert pending.confirmBlock == 0


# event testing


def test_all_events_emitted_correctly(mock_ownership, bob, alice, fork):
    time_lock = mock_ownership.ownershipTimeLock()
    
    # Test OwnershipChangeInitiated event
    mock_ownership.changeOwnership(alice, sender=bob)
    
    initiated_log = filter_logs(mock_ownership, "OwnershipChangeInitiated")[0]
    assert initiated_log.prevOwner == bob
    assert initiated_log.newOwner == alice
    assert initiated_log.confirmBlock == boa.env.evm.patch.block_number + time_lock
    
    # Test OwnershipChangeCancelled event
    pending = mock_ownership.pendingOwner()
    mock_ownership.cancelOwnershipChange(sender=bob)
    
    cancelled_log = filter_logs(mock_ownership, "OwnershipChangeCancelled")[0]
    assert cancelled_log.cancelledOwner == alice
    assert cancelled_log.cancelledBy == bob
    assert cancelled_log.initiatedBlock == pending.initiatedBlock
    assert cancelled_log.confirmBlock == pending.confirmBlock
    
    # Test OwnershipChangeConfirmed event
    mock_ownership.changeOwnership(alice, sender=bob)
    pending = mock_ownership.pendingOwner()
    boa.env.time_travel(blocks=time_lock)
    mock_ownership.confirmOwnershipChange(sender=alice)
    
    confirmed_log = filter_logs(mock_ownership, "OwnershipChangeConfirmed")[0]
    assert confirmed_log.prevOwner == bob
    assert confirmed_log.newOwner == alice
    assert confirmed_log.initiatedBlock == pending.initiatedBlock
    assert confirmed_log.confirmBlock == pending.confirmBlock
    
    # Test OwnershipTimeLockSet event
    new_timelock = PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"] + 100
    mock_ownership.setOwnershipTimeLock(new_timelock, sender=alice)
    
    timelock_log = filter_logs(mock_ownership, "OwnershipTimeLockSet")[0]
    assert timelock_log.numBlocks == new_timelock


# error message tests


def test_error_message_consistency(mock_ownership, bob, alice):
    # Test all error messages are as expected
    
    # changeOwnership errors
    with boa.reverts("no perms"):
        mock_ownership.changeOwnership(alice, sender=alice)
    
    with boa.reverts("invalid new owner"):
        mock_ownership.changeOwnership(ZERO_ADDRESS, sender=bob)
    
    with boa.reverts("invalid new owner"):
        mock_ownership.changeOwnership(bob, sender=bob)
    
    # confirmOwnershipChange errors
    with boa.reverts("no pending owner"):
        mock_ownership.confirmOwnershipChange(sender=alice)
    
    mock_ownership.changeOwnership(alice, sender=bob)
    
    with boa.reverts("time delay not reached"):
        mock_ownership.confirmOwnershipChange(sender=alice)
    
    # Time travel to pass the time lock
    boa.env.time_travel(blocks=mock_ownership.ownershipTimeLock())
    
    with boa.reverts("only new owner can confirm"):
        mock_ownership.confirmOwnershipChange(sender=bob)
    
    # cancelOwnershipChange errors
    mock_ownership.cancelOwnershipChange(sender=bob)  # clear pending
    
    with boa.reverts("no pending change"):
        mock_ownership.cancelOwnershipChange(sender=bob)
    
    # setOwnershipTimeLock errors
    with boa.reverts("no perms"):
        mock_ownership.setOwnershipTimeLock(1000, sender=alice)