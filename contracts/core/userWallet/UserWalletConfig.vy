# @version 0.4.3

from interfaces import LegoPartner as Lego
from ethereum.ercs import IERC20

interface MissionControl:
    def canPerformSecurityAction(_addr: address) -> bool: view

interface Registry:
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

event TimeLockSet:
    numBlocks: uint256

# core
owner: public(address)
wallet: public(address)

# config
timeLock: public(uint256) # num blocks!
pendingOwner: public(PendingOwnerChange)
didSetWallet: public(bool)

API_VERSION: constant(String[28]) = "0.1.0"
MAX_ASSETS: constant(uint256) = 10
MAX_LEGOS: constant(uint256) = 10

# registry ids
MISSION_CONTROL_ID: constant(uint256) = 3
HATCHERY_ID: constant(uint256) = 6

UNDY_HQ: public(immutable(address))
MIN_TIMELOCK: public(immutable(uint256))
MAX_TIMELOCK: public(immutable(uint256))


@deploy
def __init__(
    _undyHq: address,
    _owner: address,
    _initialManager: address,
    _minTimeLock: uint256,
    _maxTimeLock: uint256,
):
    assert empty(address) not in [_undyHq, _owner] # dev: invalid addrs
    UNDY_HQ = _undyHq
    self.owner = _owner

    # TODO:
    # handle `_initialManager`

    # time lock
    assert _minTimeLock < _maxTimeLock # dev: invalid delay
    MIN_TIMELOCK = _minTimeLock
    MAX_TIMELOCK = _maxTimeLock
    self.timeLock = _minTimeLock


@external
def setWallet(_wallet: address) -> bool:
    assert not self.didSetWallet # dev: wallet already set
    assert _wallet != empty(address) # dev: invalid wallet
    assert msg.sender == staticcall Registry(UNDY_HQ).getAddr(HATCHERY_ID) # dev: no perms
    self.wallet = _wallet
    self.didSetWallet = True
    return True


@pure
@external
def apiVersion() -> String[28]:
    return API_VERSION


#############
# Ownership #
#############


@external
def changeOwnership(_newOwner: address):
    currentOwner: address = self.owner
    assert msg.sender == currentOwner # dev: no perms
    assert _newOwner not in [empty(address), currentOwner] # dev: invalid new owner

    confirmBlock: uint256 = block.number + self.timeLock
    self.pendingOwner = PendingOwnerChange(
        newOwner = _newOwner,
        initiatedBlock = block.number,
        confirmBlock = confirmBlock,
    )
    log OwnershipChangeInitiated(prevOwner=currentOwner, newOwner=_newOwner, confirmBlock=confirmBlock)


@external
def confirmOwnershipChange():
    data: PendingOwnerChange = self.pendingOwner
    assert data.newOwner != empty(address) # dev: no pending owner
    assert data.confirmBlock != 0 and block.number >= data.confirmBlock # dev: time delay not reached
    assert msg.sender == data.newOwner # dev: only new owner can confirm

    prevOwner: address = self.owner
    self.owner = data.newOwner
    self.pendingOwner = empty(PendingOwnerChange)
    log OwnershipChangeConfirmed(prevOwner=prevOwner, newOwner=data.newOwner, initiatedBlock=data.initiatedBlock, confirmBlock=data.confirmBlock)


@external
def cancelOwnershipChange():
    if msg.sender != self.owner:
        missionControl: address = staticcall Registry(UNDY_HQ).getAddr(MISSION_CONTROL_ID)
        assert staticcall MissionControl(missionControl).canPerformSecurityAction(msg.sender) # dev: no perms

    data: PendingOwnerChange = self.pendingOwner
    assert data.confirmBlock != 0 # dev: no pending change
    self.pendingOwner = empty(PendingOwnerChange)
    log OwnershipChangeCancelled(cancelledOwner=data.newOwner, cancelledBy=msg.sender, initiatedBlock=data.initiatedBlock, confirmBlock=data.confirmBlock)


# utils


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


# time lock


@external
def setTimeLock(_numBlocks: uint256):
    assert msg.sender == self.owner # dev: no perms
    assert _numBlocks >= MIN_TIMELOCK and _numBlocks <= MAX_TIMELOCK # dev: invalid delay
    self.timeLock = _numBlocks
    log TimeLockSet(numBlocks=_numBlocks)


#########
# TO DO #
#########


@view
@external
def canTransferToRecipient(_recipient: address) -> bool:
    return True


@view
@external
def canAccessWallet(
    _signer: address,
    _action: Lego.ActionType,
    _assets: DynArray[address, MAX_ASSETS],
    _legoIds: DynArray[uint256, MAX_LEGOS],
) -> bool:
    return True
