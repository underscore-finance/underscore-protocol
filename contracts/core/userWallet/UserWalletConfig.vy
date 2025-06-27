# @version 0.4.3
# pragma optimize codesize

from interfaces import Wallet as wi
from ethereum.ercs import IERC20

interface Registry:
    def isValidRegId(_regId: uint256) -> bool: view
    def getAddr(_regId: uint256) -> address: view

interface MissionControl:
    def canPerformSecurityAction(_addr: address) -> bool: view

struct ManagerPeriodData:
    txCount: uint256
    volume: uint256
    lastTxBlock: uint256

struct Limits:
    maxVolumePerTx: uint256
    maxVolumePerPeriod: uint256
    maxNumTxsPerPeriod: uint256
    txCooldownBlocks: uint256

struct LegoPerms:
    canManageYield: bool
    canBuyAndSell: bool
    canManageDebt: bool
    canManageLiq: bool
    canClaimRewards: bool
    allowedLegos: DynArray[uint256, MAX_CONFIG_LEGOS]

struct TransferPerms:
    canTransfer: bool
    canCreateCheque: bool
    canAddPendingRecipient: bool
    allowedRecipients: DynArray[address, MAX_CONFIG_RECIPIENTS]

struct ManagerSettings:
    startBlock: uint256
    expiryBlock: uint256
    limits: Limits
    legoPerms: LegoPerms
    transferPerms: TransferPerms
    allowedAssets: DynArray[address, MAX_CONFIG_ASSETS]

struct GlobalManagerSettings:
    managerPeriod: uint256
    startDelay: uint256
    activationLength: uint256
    limits: Limits
    legoPerms: LegoPerms
    transferPerms: TransferPerms
    allowedAssets: DynArray[address, MAX_CONFIG_ASSETS]

struct PendingGlobalManagerSettings:
    config: GlobalManagerSettings
    initiatedBlock: uint256
    confirmBlock: uint256

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
wallet: public(address)
owner: public(address)
pendingOwner: public(PendingOwnerChange)

# managers
managerSettings: public(HashMap[address, ManagerSettings])
managerPeriodData: public(HashMap[address, ManagerPeriodData])

# managers (iterable)
managers: public(HashMap[uint256, address]) # index -> manager
indexOfManager: public(HashMap[address, uint256]) # manager -> index
numManagers: public(uint256) # num managers

# global config
globalManagerSettings: public(GlobalManagerSettings)
pendingGlobalManagerSettings: public(PendingGlobalManagerSettings)

# config
timeLock: public(uint256)
didSetWallet: public(bool)

# TODO: TEMPORARY
initialAgent: public(address)

API_VERSION: constant(String[28]) = "0.1.0"

MAX_CONFIG_ASSETS: constant(uint256) = 40
MAX_CONFIG_LEGOS: constant(uint256) = 25
MAX_CONFIG_ACTIONS: constant(uint256) = 20
MAX_CONFIG_RECIPIENTS: constant(uint256) = 40
MAX_ASSETS: constant(uint256) = 10
MAX_LEGOS: constant(uint256) = 10

# time (blocks)
ONE_DAY_IN_BLOCKS: constant(uint256) = 43_200
ONE_MONTH_IN_BLOCKS: constant(uint256) = ONE_DAY_IN_BLOCKS * 30
ONE_YEAR_IN_BLOCKS: constant(uint256) = ONE_DAY_IN_BLOCKS * 365

# registry ids
MISSION_CONTROL_ID: constant(uint256) = 3
LEGO_BOOK_ID: constant(uint256) = 4
HATCHERY_ID: constant(uint256) = 6

UNDY_HQ: public(immutable(address))
MIN_TIMELOCK: public(immutable(uint256))
MAX_TIMELOCK: public(immutable(uint256))
MIN_MANAGER_PERIOD: public(immutable(uint256))
MAX_MANAGER_PERIOD: public(immutable(uint256))


@deploy
def __init__(
    _undyHq: address,
    _owner: address,
    _initialManager: address,
    _defaultManagerSettings: GlobalManagerSettings,
    _minManagerPeriod: uint256,
    _maxManagerPeriod: uint256,
    _minTimeLock: uint256,
    _maxTimeLock: uint256,
):
    assert empty(address) not in [_undyHq, _owner] # dev: invalid addrs
    UNDY_HQ = _undyHq
    self.owner = _owner

    # TODO: TEMPORARY
    self.initialAgent = _initialManager

    # validate global manager settings
    assert _minManagerPeriod != 0 and _minManagerPeriod < _maxManagerPeriod # dev: invalid manager periods
    MIN_MANAGER_PERIOD = _minManagerPeriod
    MAX_MANAGER_PERIOD = _maxManagerPeriod
    assert self._isValidGlobalManagerTimes(_defaultManagerSettings.managerPeriod, _defaultManagerSettings.startDelay, _defaultManagerSettings.activationLength) # dev: invalid manager periods
    assert self._isValidLimits(_defaultManagerSettings.limits) # dev: invalid limits
    assert self._isValidLegoPerms(_defaultManagerSettings.legoPerms) # dev: invalid lego perms
    assert self._isValidTransferPerms(_defaultManagerSettings.transferPerms) # dev: invalid transfer perms
    assert self._isValidAllowedAssets(_defaultManagerSettings.allowedAssets) # dev: invalid allowed assets
    self.globalManagerSettings = _defaultManagerSettings

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


###########################
# Global Manager Settings #
###########################


# set pending global manager settings


@external
def setPendingGlobalManagerSettings(
    _managerPeriod: uint256,
    _startDelay: uint256,
    _activationLength: uint256,
    _limits: Limits,
    _legoPerms: LegoPerms,
    _transferPerms: TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
) -> bool:
    assert msg.sender == self.owner # dev: no perms

     # validation
    assert self._isValidGlobalManagerTimes(_managerPeriod, _startDelay, _activationLength) # dev: invalid manager periods
    assert self._isValidLimits(_limits) # dev: invalid limits
    assert self._isValidLegoPerms(_legoPerms) # dev: invalid lego perms
    assert self._isValidTransferPerms(_transferPerms) # dev: invalid transfer perms
    assert self._isValidAllowedAssets(_allowedAssets) # dev: invalid allowed assets

    config: GlobalManagerSettings = GlobalManagerSettings(
        managerPeriod = _managerPeriod,
        startDelay = _startDelay,
        activationLength = _activationLength,
        limits = _limits,
        legoPerms = _legoPerms,
        transferPerms = _transferPerms,
        allowedAssets = _allowedAssets,
    )

    # put in pending state
    self.pendingGlobalManagerSettings = PendingGlobalManagerSettings(
        config = config,
        initiatedBlock = block.number,
        confirmBlock = block.number + self.timeLock,
    )

    # TODO: add event
    return True


@view
@internal
def _isValidGlobalManagerTimes(_managerPeriod: uint256, _startDelay: uint256, _activationLength: uint256) -> bool:
    if _managerPeriod < MIN_MANAGER_PERIOD or _managerPeriod > MAX_MANAGER_PERIOD:
        return False
    if _startDelay > 3 * ONE_MONTH_IN_BLOCKS:
        return False
    if _activationLength > 5 * ONE_YEAR_IN_BLOCKS:
        return False
    return True


# confirm global manager settings


@external
def confirmPendingGlobalManagerSettings() -> bool:
    assert msg.sender == self.owner # dev: no perms

    data: PendingGlobalManagerSettings = self.pendingGlobalManagerSettings
    assert data.confirmBlock != 0 and block.number >= data.confirmBlock # dev: time delay not reached

    self.globalManagerSettings = data.config
    self.pendingGlobalManagerSettings = empty(PendingGlobalManagerSettings)

    # TODO: add event
    return True


# cancel global manager settings


@external
def cancelPendingGlobalManagerSettings() -> bool:
    assert msg.sender == self.owner # dev: no perms

    data: PendingGlobalManagerSettings = self.pendingGlobalManagerSettings
    assert data.confirmBlock != 0 # dev: no pending change
    self.pendingGlobalManagerSettings = empty(PendingGlobalManagerSettings)

    # TODO: add event
    return True


#############################
# Specific Manager Settings #
#############################


@external
def setManagerSettings(
    _manager: address,
    _limits: Limits,
    _legoPerms: LegoPerms,
    _transferPerms: TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
    _startDelay: uint256 = 0,
    _activationLength: uint256 = 0,
) -> bool:
    assert msg.sender == self.owner # dev: no perms

    # validation
    assert _manager != empty(address) # dev: invalid manager
    assert self._isValidLimits(_limits) # dev: invalid limits
    assert self._isValidLegoPerms(_legoPerms) # dev: invalid lego perms
    assert self._isValidTransferPerms(_transferPerms) # dev: invalid transfer perms
    assert self._isValidAllowedAssets(_allowedAssets) # dev: invalid allowed assets

    # set manager settings
    config: ManagerSettings = ManagerSettings(
        startBlock = 0,
        expiryBlock = 0,
        limits = _limits,
        legoPerms = _legoPerms,
        transferPerms = _transferPerms,
        allowedAssets = _allowedAssets,
    )
    config.startBlock, config.expiryBlock = self._getStartAndExpiryBlocks(_startDelay, _activationLength)
    self.managerSettings[_manager] = config

    # register manager
    if self.indexOfManager[_manager] == 0:
        self._registerManager(_manager)

    # TODO: add event
    return True


# validation / utils


@view
@internal
def _getStartAndExpiryBlocks(_startDelay: uint256, _activationLength: uint256) -> (uint256, uint256):
    config: GlobalManagerSettings = self.globalManagerSettings

    startDelay: uint256 = max(_startDelay, config.startDelay)
    activationLength: uint256 = config.activationLength
    if _activationLength != 0:
        activationLength = min(activationLength, _activationLength)

    assert self._isValidGlobalManagerTimes(config.managerPeriod, startDelay, activationLength) # dev: invalid manager periods

    startBlock: uint256 = block.number + startDelay
    expiryBlock: uint256 = startBlock + activationLength
    return startBlock, expiryBlock


@view
@internal
def _isValidLimits(_limits: Limits) -> bool:
    # Note: 0 values are treated as "unlimited" throughout this validation
    
    # only validate if both values are non-zero (not unlimited)
    if _limits.maxVolumePerTx != 0 and _limits.maxVolumePerPeriod != 0:
        if _limits.maxVolumePerTx > _limits.maxVolumePerPeriod:
            return False

    # cooldown cannot exceed period length (unless cooldown is 0 = no cooldown)
    if _limits.txCooldownBlocks != 0 and _limits.txCooldownBlocks > self.globalManagerSettings.managerPeriod:
        return False

    return True


@view
@internal
def _isValidLegoPerms(_legoPerms: LegoPerms) -> bool:
    if len(_legoPerms.allowedLegos) == 0:
        return True

    canDoAnything: bool = _legoPerms.canManageYield or _legoPerms.canBuyAndSell or _legoPerms.canManageDebt or _legoPerms.canManageLiq or _legoPerms.canClaimRewards

    # _allowedLegos should be empty if there are no permissions
    if not canDoAnything:
        return False

    legoBook: address = staticcall Registry(UNDY_HQ).getAddr(LEGO_BOOK_ID)
    if legoBook == empty(address):
        return False

    checkedLegos: DynArray[uint256, MAX_CONFIG_LEGOS] = []
    for i: uint256 in _legoPerms.allowedLegos:
        if not staticcall Registry(legoBook).isValidRegId(i):
            return False

        # duplicates are not allowed
        if i in checkedLegos:
            return False
        checkedLegos.append(i)

    return True


@view
@internal
def _isValidTransferPerms(_transferPerms: TransferPerms) -> bool:
    if len(_transferPerms.allowedRecipients) == 0:
        return True

    canDoAnything: bool = _transferPerms.canTransfer or _transferPerms.canCreateCheque or _transferPerms.canAddPendingRecipient

    # _allowedRecipients should be empty if there are no permissions
    if not canDoAnything:
        return False

    checkedRecipients: DynArray[address, MAX_CONFIG_RECIPIENTS] = []
    for i: address in _transferPerms.allowedRecipients:
        if i == empty(address):
            return False

        # check if recipient is valid
        if not self._isValidRecipient(i):
            return False

        # duplicates are not allowed
        if i in checkedRecipients:
            return False
        checkedRecipients.append(i)

    return True


@view
@internal
def _isValidAllowedAssets(_allowedAssets: DynArray[address, MAX_CONFIG_ASSETS]) -> bool:
    if len(_allowedAssets) == 0:
        return True

    checkedAssets: DynArray[address, MAX_CONFIG_ASSETS] = []
    for i: address in _allowedAssets:
        if i == empty(address):
            return False

        # duplicates are not allowed
        if i in checkedAssets:
            return False
        checkedAssets.append(i)

    return True


# register/deregister manager


@internal
def _registerManager(_manager: address):
    mid: uint256 = self.numManagers
    if mid == 0:
        mid = 1 # not using 0 index
    self.managers[mid] = _manager
    self.indexOfManager[_manager] = mid
    self.numManagers = mid + 1


@internal
def _deregisterManager(_manager: address) -> bool:
    numManagers: uint256 = self.numManagers
    if numManagers == 0:
        return False

    targetIndex: uint256 = self.indexOfManager[_manager]
    if targetIndex == 0:
        return False

    # update data
    lastIndex: uint256 = numManagers - 1
    self.numManagers = lastIndex
    self.indexOfManager[_manager] = 0

    # get last item, replace the removed item
    if targetIndex != lastIndex:
        lastItem: address = self.managers[lastIndex]
        self.managers[targetIndex] = lastItem
        self.indexOfManager[lastItem] = targetIndex

    return True


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
    _action: wi.ActionType,
    _assets: DynArray[address, MAX_ASSETS],
    _legoIds: DynArray[uint256, MAX_LEGOS],
) -> bool:
    return _signer == self.initialAgent


@view
@internal
def _isValidRecipient(_recipient: address) -> bool:

    # TODO: hook this up

    return True
