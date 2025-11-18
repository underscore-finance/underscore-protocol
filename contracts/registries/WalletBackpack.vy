#
#     _____  _____  _____  __ ___ _____  _____  _____  __ ___
#    /  _  \/  _  \/     \|  |  //  _  \/  _  \/     \|  |  /
#    |  _  <|  _  ||  |--||  _ < |   __/|  _  ||  |--||  _ < 
#    \_____/\__|__/\_____/|__|__\\__/   \__|__/\_____/|__|__\
#                                                        
#     ╔═════════════════════════════════════════════════════╗
#     ║  ** Wallet Backpack **                              ║
#     ║  Registry for all wallet-related support contracts. ║
#     ╚═════════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

implements: Department

exports: gov.__interface__
exports: addys.__interface__
exports: deptBasics.__interface__
exports: timeLock.__interface__

initializes: gov
initializes: addys
initializes: deptBasics[addys := addys]
initializes: timeLock[gov := gov]

import contracts.modules.LocalGov as gov
import contracts.modules.Addys as addys
import contracts.modules.DeptBasics as deptBasics
import contracts.modules.TimeLock as timeLock
from interfaces import Department

from interfaces import WalletConfigStructs as wcs
from interfaces import WalletStructs as ws

interface Sentinel:
    def canSignerPerformActionWithConfig(_isOwner: bool, _isManager: bool, _data: wcs.ManagerData, _config: wcs.ManagerSettings, _globalConfig: wcs.GlobalManagerSettings, _action: ws.ActionType, _assets: DynArray[address, MAX_ASSETS] = [], _legoIds: DynArray[uint256, MAX_LEGOS] = [], _payee: address = empty(address)) -> bool: view
    def checkManagerLimitsPostTx(_txUsdValue: uint256, _specificLimits: wcs.ManagerLimits, _globalLimits: wcs.ManagerLimits, _managerPeriod: uint256, _data: wcs.ManagerData, _needsVaultApproval: bool, _underlyingAsset: address, _vaultToken: address, _vaultRegistry: address) -> (bool, wcs.ManagerData): view
    def isValidPayeeAndGetData(_isWhitelisted: bool, _isOwner: bool, _isPayee: bool, _asset: address, _amount: uint256, _txUsdValue: uint256, _config: wcs.PayeeSettings, _globalConfig: wcs.GlobalPayeeSettings, _data: wcs.PayeeData) -> (bool, wcs.PayeeData): view
    def isValidChequeAndGetData(_asset: address, _amount: uint256, _txUsdValue: uint256, _cheque: wcs.Cheque, _globalConfig: wcs.ChequeSettings, _chequeData: wcs.ChequeData, _isManager: bool) -> (bool, wcs.ChequeData): view

interface Ledger:
    def isRegisteredBackpackItem(_addr: address) -> bool: view
    def registerBackpackItem(_addr: address): nonpayable

struct PendingBackpackItem:
    actionId: uint256
    addr: address

event PendingBackpackItemAdded:
    backpackType: wcs.BackpackType
    addr: indexed(address)
    actionId: uint256
    confirmationBlock: uint256
    addedBy: indexed(address)

event BackpackItemConfirmed:
    backpackType: wcs.BackpackType
    addr: indexed(address)
    actionId: uint256
    confirmedBy: indexed(address)

event PendingBackpackItemCancelled:
    backpackType: wcs.BackpackType
    addr: indexed(address)
    actionId: uint256
    cancelledBy: indexed(address)

# current implementations
kernel: public(address)
sentinel: public(address)
highCommand: public(address)
paymaster: public(address)
chequeBook: public(address)
migrator: public(address)

# pending changes
pendingUpdates: public(HashMap[wcs.BackpackType, PendingBackpackItem]) # type -> config

MAX_ASSETS: constant(uint256) = 10
MAX_LEGOS: constant(uint256) = 10


@deploy
def __init__(
    _undyHq: address,
    _tempGov: address,
    _minTimeLock: uint256,
    _maxTimeLock: uint256,
):
    gov.__init__(_undyHq, _tempGov, 0, 0, 0)
    addys.__init__(_undyHq)
    deptBasics.__init__(False, False)
    timeLock.__init__(_minTimeLock, _maxTimeLock, 0, _maxTimeLock)


####################
# Add Pending Item #
####################


@external
def addPendingKernel(_addr: address) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return self._addPendingBackpackItem(wcs.BackpackType.WALLET_KERNEL, _addr)


@external
def addPendingSentinel(_addr: address) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return self._addPendingBackpackItem(wcs.BackpackType.WALLET_SENTINEL, _addr)


@external
def addPendingHighCommand(_addr: address) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return self._addPendingBackpackItem(wcs.BackpackType.WALLET_HIGH_COMMAND, _addr)


@external
def addPendingPaymaster(_addr: address) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return self._addPendingBackpackItem(wcs.BackpackType.WALLET_PAYMASTER, _addr)


@external
def addPendingChequeBook(_addr: address) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return self._addPendingBackpackItem(wcs.BackpackType.WALLET_CHEQUE_BOOK, _addr)


@external
def addPendingMigrator(_addr: address) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return self._addPendingBackpackItem(wcs.BackpackType.WALLET_MIGRATOR, _addr)


# add item


@internal
def _addPendingBackpackItem(_backpackType: wcs.BackpackType, _addr: address) -> bool:
    assert self.pendingUpdates[_backpackType].actionId == 0 # dev: already pending
    assert self._canAddBackpackItem(_backpackType, _addr) # dev: invalid item

    aid: uint256 = timeLock._initiateAction()
    self.pendingUpdates[_backpackType] = PendingBackpackItem(actionId=aid, addr=_addr)

    log PendingBackpackItemAdded(
        backpackType=_backpackType,
        addr=_addr,
        actionId=aid,
        confirmationBlock=timeLock._getActionConfirmationBlock(aid),
        addedBy=msg.sender,
    )
    return True


# validation


@view
@external
def canAddBackpackItem(_backpackType: wcs.BackpackType, _addr: address) -> bool:
    return self._canAddBackpackItem(_backpackType, _addr)


@view
@internal
def _canAddBackpackItem(_backpackType: wcs.BackpackType, _addr: address) -> bool:
    if _backpackType == wcs.BackpackType.WALLET_KERNEL:
        return self._isValidAddr(_addr, self.kernel)
    if _backpackType == wcs.BackpackType.WALLET_SENTINEL:
        return self._isValidSentinel(_addr)
    elif _backpackType == wcs.BackpackType.WALLET_HIGH_COMMAND:
        return self._isValidAddr(_addr, self.highCommand)
    elif _backpackType == wcs.BackpackType.WALLET_PAYMASTER:
        return self._isValidAddr(_addr, self.paymaster)
    elif _backpackType == wcs.BackpackType.WALLET_CHEQUE_BOOK:
        return self._isValidAddr(_addr, self.chequeBook)
    elif _backpackType == wcs.BackpackType.WALLET_MIGRATOR:
        return self._isValidAddr(_addr, self.migrator)
    return False


@view
@internal
def _isValidSentinel(_addr: address) -> bool:
    if not self._isValidAddr(_addr, self.sentinel):
        return False

    # make sure has all the important interfaces
    isValid: bool = staticcall Sentinel(_addr).canSignerPerformActionWithConfig(
        False,
        False,
        empty(wcs.ManagerData),
        empty(wcs.ManagerSettings),
        empty(wcs.GlobalManagerSettings),
        ws.ActionType.EARN_DEPOSIT,
        [],
        [],
        empty(address),
    )

    payeeData: wcs.PayeeData = empty(wcs.PayeeData)
    isValid, payeeData = staticcall Sentinel(_addr).isValidPayeeAndGetData(
        False,
        False,
        False,
        empty(address),
        0,
        0,
        empty(wcs.PayeeSettings),
        empty(wcs.GlobalPayeeSettings),
        empty(wcs.PayeeData),
    )

    managerData: wcs.ManagerData = empty(wcs.ManagerData)
    isValid, managerData = staticcall Sentinel(_addr).checkManagerLimitsPostTx(
        0,
        empty(wcs.ManagerLimits),
        empty(wcs.ManagerLimits),
        0,
        empty(wcs.ManagerData),
        False,
        empty(address),
        empty(address),
        empty(address),
    )

    chequeData: wcs.ChequeData = empty(wcs.ChequeData)
    isValid, chequeData = staticcall Sentinel(_addr).isValidChequeAndGetData(
        empty(address),
        0,
        0,
        empty(wcs.Cheque),
        empty(wcs.ChequeSettings),
        empty(wcs.ChequeData),
        False,
    )
    return True


@view
@internal
def _isValidAddr(_addr: address, _prevAddr: address) -> bool:
    if not _addr.is_contract or _addr == empty(address):
        return False
    return _addr != _prevAddr


########################
# Confirm Pending Item #
########################


@external
def confirmPendingKernel() -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return self._confirmBackpackItem(wcs.BackpackType.WALLET_KERNEL, msg.sender)


@external
def confirmPendingSentinel() -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return self._confirmBackpackItem(wcs.BackpackType.WALLET_SENTINEL, msg.sender)


@external
def confirmPendingHighCommand() -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return self._confirmBackpackItem(wcs.BackpackType.WALLET_HIGH_COMMAND, msg.sender)


@external
def confirmPendingPaymaster() -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return self._confirmBackpackItem(wcs.BackpackType.WALLET_PAYMASTER, msg.sender)


@external
def confirmPendingChequeBook() -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return self._confirmBackpackItem(wcs.BackpackType.WALLET_CHEQUE_BOOK, msg.sender)


@external
def confirmPendingMigrator() -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return self._confirmBackpackItem(wcs.BackpackType.WALLET_MIGRATOR, msg.sender)


# confirm new item


@internal
def _confirmBackpackItem(_backpackType: wcs.BackpackType, _caller: address) -> bool:
    d: PendingBackpackItem = self.pendingUpdates[_backpackType]
    assert d.addr != empty(address) # dev: no pending item

    # validate again
    if not self._canAddBackpackItem(_backpackType, d.addr):
        self._cancelPendingBackpackItem(_backpackType, _caller)
        return False

    # check time lock
    assert timeLock._confirmAction(d.actionId) # dev: time lock not reached

    # zero out pending item
    self.pendingUpdates[_backpackType] = empty(PendingBackpackItem)
    self._setBackpackItem(_backpackType, d.addr)

    log BackpackItemConfirmed(
        backpackType=_backpackType,
        addr=d.addr,
        actionId=d.actionId,
        confirmedBy=_caller,
    )
    return True


@internal
def _setBackpackItem(_backpackType: wcs.BackpackType, _addr: address):
    if _backpackType == wcs.BackpackType.WALLET_KERNEL:
        self.kernel = _addr
    elif _backpackType == wcs.BackpackType.WALLET_SENTINEL:
        self.sentinel = _addr
    elif _backpackType == wcs.BackpackType.WALLET_HIGH_COMMAND:
        self.highCommand = _addr
    elif _backpackType == wcs.BackpackType.WALLET_PAYMASTER:
        self.paymaster = _addr
    elif _backpackType == wcs.BackpackType.WALLET_CHEQUE_BOOK:
        self.chequeBook = _addr
    elif _backpackType == wcs.BackpackType.WALLET_MIGRATOR:
        self.migrator = _addr

    # register in ledger
    extcall Ledger(addys._getLedgerAddr()).registerBackpackItem(_addr)


#######################
# Cancel Pending Item #
#######################


@external
def cancelPendingKernel() -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return self._cancelPendingBackpackItem(wcs.BackpackType.WALLET_KERNEL, msg.sender)


@external
def cancelPendingSentinel() -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return self._cancelPendingBackpackItem(wcs.BackpackType.WALLET_SENTINEL, msg.sender)


@external
def cancelPendingHighCommand() -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return self._cancelPendingBackpackItem(wcs.BackpackType.WALLET_HIGH_COMMAND, msg.sender)


@external
def cancelPendingPaymaster() -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return self._cancelPendingBackpackItem(wcs.BackpackType.WALLET_PAYMASTER, msg.sender)


@external
def cancelPendingChequeBook() -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return self._cancelPendingBackpackItem(wcs.BackpackType.WALLET_CHEQUE_BOOK, msg.sender)


@external
def cancelPendingMigrator() -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return self._cancelPendingBackpackItem(wcs.BackpackType.WALLET_MIGRATOR, msg.sender)


# cancel pending item


@internal
def _cancelPendingBackpackItem(_backpackType: wcs.BackpackType, _caller: address) -> bool:
    d: PendingBackpackItem = self.pendingUpdates[_backpackType]

    assert timeLock._cancelAction(d.actionId) # dev: cannot cancel action
    self.pendingUpdates[_backpackType] = empty(PendingBackpackItem)

    log PendingBackpackItemCancelled(
        backpackType=_backpackType,
        addr=d.addr,
        actionId=d.actionId,
        cancelledBy=_caller,
    )
    return True


#############
# Utilities #
#############


@view
@internal
def _canPerformAction(_caller: address) -> bool:
    return gov._canGovern(_caller) and not deptBasics.isPaused


@view
@external
def isRegisteredBackpackItem(_addr: address) -> bool:
    return staticcall Ledger(addys._getLedgerAddr()).isRegisteredBackpackItem(_addr)