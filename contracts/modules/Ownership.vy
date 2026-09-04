#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

interface MissionControl:
    def canPerformSecurityAction(_addr: address) -> bool: view

interface UndyHq:
    def getAddr(_regId: uint256) -> address: view

struct PendingOwnerChange:
    newOwner: address
    initiatedBlock: uint256
    confirmBlock: uint256

struct PendingOwnershipTimeLock:
    newTimeLock: uint256
    initiatedBlock: uint256
    confirmBlock: uint256
    currentOwner: address

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

event PendingOwnershipTimeLockSet:
    newTimeLock: uint256
    initiatedBlock: uint256
    confirmBlock: uint256
    currentOwner: indexed(address)

event PendingOwnershipTimeLockConfirmed:
    oldTimeLock: uint256
    newTimeLock: uint256
    initiatedBlock: uint256
    confirmBlock: uint256
    confirmedBy: indexed(address)

event PendingOwnershipTimeLockCancelled:
    newTimeLock: uint256
    initiatedBlock: uint256
    confirmBlock: uint256
    cancelledBy: indexed(address)

# core
owner: public(address)
ownershipTimeLock: public(uint256)

# pending owner change
pendingOwner: public(PendingOwnerChange)
pendingOwnershipTimeLock: public(PendingOwnershipTimeLock)

UNDY_HQ_FOR_OWNERSHIP: address
MIN_OWNERSHIP_TIMELOCK: public(uint256)
MAX_OWNERSHIP_TIMELOCK: public(uint256)
ownershipInitialized: bool
MISSION_CONTROL_ID: constant(uint256) = 2


@deploy
def __init__(
    _undyHq: address,
    _owner: address,
    _minTimeLock: uint256,
    _maxTimeLock: uint256,
):
    self._initializeOwnership(_undyHq, _owner, _minTimeLock, _maxTimeLock)


@internal
def _initializeOwnership(
    _undyHq: address,
    _owner: address,
    _minTimeLock: uint256,
    _maxTimeLock: uint256,
):
    assert not self.ownershipInitialized # dev: ownership already initialized
    # Keep this as the first storage write. Any future external call added to
    # initialization must observe the guard closed to prevent reentrant init.
    self.ownershipInitialized = True
    assert empty(address) not in [_undyHq, _owner] # dev: invalid addrs
    self.UNDY_HQ_FOR_OWNERSHIP = _undyHq

    # initial ownership
    self.owner = _owner

    # timelock
    assert _minTimeLock != 0 and _minTimeLock < _maxTimeLock # dev: invalid delay
    self.MIN_OWNERSHIP_TIMELOCK = _minTimeLock
    self.MAX_OWNERSHIP_TIMELOCK = _maxTimeLock

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
    missionControl: address = staticcall UndyHq(self.UNDY_HQ_FOR_OWNERSHIP).getAddr(MISSION_CONTROL_ID)
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
    assert _numBlocks >= self.MIN_OWNERSHIP_TIMELOCK and _numBlocks <= self.MAX_OWNERSHIP_TIMELOCK # dev: invalid delay

    currentTimeLock: uint256 = self.ownershipTimeLock
    pending: PendingOwnershipTimeLock = self.pendingOwnershipTimeLock
    hasPending: bool = pending.confirmBlock != 0

    if _numBlocks >= currentTimeLock:
        if _numBlocks == currentTimeLock:
            return

        if hasPending:
            self.pendingOwnershipTimeLock = empty(PendingOwnershipTimeLock)
            log PendingOwnershipTimeLockCancelled(
                newTimeLock = pending.newTimeLock,
                initiatedBlock = pending.initiatedBlock,
                confirmBlock = pending.confirmBlock,
                cancelledBy = msg.sender,
            )

        self.ownershipTimeLock = _numBlocks
        log OwnershipTimeLockSet(numBlocks=_numBlocks)
        return

    assert not hasPending # dev: pending time lock already exists

    confirmBlock: uint256 = block.number + currentTimeLock
    self.pendingOwnershipTimeLock = PendingOwnershipTimeLock(
        newTimeLock = _numBlocks,
        initiatedBlock = block.number,
        confirmBlock = confirmBlock,
        currentOwner = self.owner,
    )
    log PendingOwnershipTimeLockSet(
        newTimeLock = _numBlocks,
        initiatedBlock = block.number,
        confirmBlock = confirmBlock,
        currentOwner = self.owner,
    )


@external
def confirmPendingOwnershipTimeLock():
    assert msg.sender == self.owner # dev: no perms

    pending: PendingOwnershipTimeLock = self.pendingOwnershipTimeLock
    assert pending.confirmBlock != 0 # dev: no pending time lock
    assert block.number >= pending.confirmBlock # dev: time delay not reached
    assert pending.currentOwner == self.owner # dev: owner must match
    assert pending.newTimeLock >= self.MIN_OWNERSHIP_TIMELOCK and pending.newTimeLock <= self.MAX_OWNERSHIP_TIMELOCK # dev: invalid delay

    oldTimeLock: uint256 = self.ownershipTimeLock
    self.ownershipTimeLock = pending.newTimeLock
    self.pendingOwnershipTimeLock = empty(PendingOwnershipTimeLock)
    log OwnershipTimeLockSet(numBlocks=pending.newTimeLock)
    log PendingOwnershipTimeLockConfirmed(
        oldTimeLock = oldTimeLock,
        newTimeLock = pending.newTimeLock,
        initiatedBlock = pending.initiatedBlock,
        confirmBlock = pending.confirmBlock,
        confirmedBy = msg.sender,
    )


@external
def cancelPendingOwnershipTimeLock():
    if msg.sender != self.owner:
        assert self._canPerformSecurityAction(msg.sender) # dev: no perms

    pending: PendingOwnershipTimeLock = self.pendingOwnershipTimeLock
    assert pending.confirmBlock != 0 # dev: no pending time lock
    self.pendingOwnershipTimeLock = empty(PendingOwnershipTimeLock)
    log PendingOwnershipTimeLockCancelled(
        newTimeLock = pending.newTimeLock,
        initiatedBlock = pending.initiatedBlock,
        confirmBlock = pending.confirmBlock,
        cancelledBy = msg.sender,
    )
