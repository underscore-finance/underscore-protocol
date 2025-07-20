#     Underscore Protocol License: https://github.com/hightophq/underscore-protocol/blob/master/LICENSE.md
#     Hightop Financial, Inc. (C) 2025

# @version 0.4.3

interface MissionControl:
    def canPerformSecurityAction(_addr: address) -> bool: view

interface UndyHq:
    def getAddr(_regId: uint256) -> address: view

struct PendingOwnerChange:
    newOwner: address
    initiatedBlock: uint256
    confirmBlock: uint256

event OwnershipChangeInitiated:
    prevOwner: indexed(address)
    newOwner: indexed(address)
    confirmBlock: uint256

event OwnershipChangeConfirmed:
    prevOwner: indexed(address)
    newOwner: indexed(address)
    initiatedBlock: uint256
    confirmBlock: uint256

event OwnershipChangeCancelled:
    cancelledOwner: indexed(address)
    cancelledBy: indexed(address)
    initiatedBlock: uint256
    confirmBlock: uint256

event OwnershipTimeLockSet:
    numBlocks: uint256

# core
owner: public(address)
ownershipTimeLock: public(uint256)

# pending owner change
pendingOwner: public(PendingOwnerChange)

UNDY_HQ_FOR_OWNERSHIP: immutable(address)
MIN_OWNERSHIP_TIMELOCK: public(immutable(uint256))
MAX_OWNERSHIP_TIMELOCK: public(immutable(uint256))
MISSION_CONTROL_ID: constant(uint256) = 3


@deploy
def __init__(
    _undyHq: address,
    _owner: address,
    _minTimeLock: uint256,
    _maxTimeLock: uint256,
):
    assert empty(address) not in [_undyHq, _owner] # dev: invalid addrs
    UNDY_HQ_FOR_OWNERSHIP = _undyHq

    # initial ownership
    self.owner = _owner

    # timelock
    assert _minTimeLock != 0 and _minTimeLock < _maxTimeLock # dev: invalid delay
    MIN_OWNERSHIP_TIMELOCK = _minTimeLock
    MAX_OWNERSHIP_TIMELOCK = _maxTimeLock

    self.ownershipTimeLock = _minTimeLock


#############
# Ownership #
#############


# change ownership


@external
def changeOwnership(_newOwner: address):
    currentOwner: address = self.owner
    assert msg.sender == currentOwner # dev: no perms
    assert _newOwner not in [empty(address), currentOwner] # dev: invalid new owner

    confirmBlock: uint256 = block.number + self.ownershipTimeLock
    self.pendingOwner = PendingOwnerChange(
        newOwner = _newOwner,
        initiatedBlock = block.number,
        confirmBlock = confirmBlock,
    )
    log OwnershipChangeInitiated(prevOwner = currentOwner, newOwner = _newOwner, confirmBlock = confirmBlock)


# confirm ownership change


@external
def confirmOwnershipChange():
    data: PendingOwnerChange = self.pendingOwner
    assert data.newOwner != empty(address) # dev: no pending owner
    assert data.confirmBlock != 0 and block.number >= data.confirmBlock # dev: time delay not reached
    assert msg.sender == data.newOwner # dev: only new owner can confirm

    prevOwner: address = self.owner
    self.owner = data.newOwner
    self.pendingOwner = empty(PendingOwnerChange)
    log OwnershipChangeConfirmed(prevOwner = prevOwner, newOwner = data.newOwner, initiatedBlock = data.initiatedBlock, confirmBlock = data.confirmBlock)


# cancel ownership change


@external
def cancelOwnershipChange():
    if msg.sender != self.owner:
        assert self._canPerformSecurityAction(msg.sender) # dev: no perms

    data: PendingOwnerChange = self.pendingOwner
    assert data.confirmBlock != 0 # dev: no pending change
    self.pendingOwner = empty(PendingOwnerChange)
    log OwnershipChangeCancelled(cancelledOwner = data.newOwner, cancelledBy = msg.sender, initiatedBlock = data.initiatedBlock, confirmBlock = data.confirmBlock)


@view
@internal
def _canPerformSecurityAction(_addr: address) -> bool:
    missionControl: address = staticcall UndyHq(UNDY_HQ_FOR_OWNERSHIP).getAddr(MISSION_CONTROL_ID)
    if missionControl == empty(address):
        return False
    return staticcall MissionControl(missionControl).canPerformSecurityAction(_addr)


#############
# Utilities #
#############


@view
@external
def hasPendingOwnerChange() -> bool:
    return self._hasPendingOwnerChange()


@view
@internal
def _hasPendingOwnerChange() -> bool:
    return self.pendingOwner.confirmBlock != 0


#############
# Time Lock #
#############


@external
def setOwnershipTimeLock(_numBlocks: uint256):
    assert msg.sender == self.owner # dev: no perms
    assert _numBlocks >= MIN_OWNERSHIP_TIMELOCK and _numBlocks <= MAX_OWNERSHIP_TIMELOCK # dev: invalid delay
    self.ownershipTimeLock = _numBlocks
    log OwnershipTimeLockSet(numBlocks=_numBlocks)