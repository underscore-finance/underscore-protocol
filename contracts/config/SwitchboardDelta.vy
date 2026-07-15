#        ______   __     __   __   ______  ______   __  __   ______   ______   ______   ______   _____    
#       /\  ___\ /\ \  _ \ \ /\ \ /\__  _\/\  ___\ /\ \_\ \ /\  == \ /\  __ \ /\  __ \ /\  == \ /\  __-.  
#       \ \___  \\ \ \/ ".\ \\ \ \\/_/\ \/\ \ \____\ \  __ \\ \  __< \ \ \/\ \\ \  __ \\ \  __< \ \ \/\ \ 
#        \/\_____\\ \__/".~\_\\ \_\  \ \_\ \ \_____\\ \_\ \_\\ \_____\\ \_____\\ \_\ \_\\ \_\ \_\\ \____- 
#         \/_____/ \/_/   \/_/ \/_/   \/_/  \/_____/ \/_/\/_/ \/_____/ \/_____/ \/_/\/_/ \/_/ /_/ \/____/ 
#                                                      ┓  ┓   
#                                                     ┏┫┏┓┃╋┏┓
#                                                     ┗┻┗ ┗┗┗┻
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# The switchboard config contract for the payments stack (PayProcessor, VendorRegistry, VendorProxy).
# It is registered in the Switchboard registry, so it IS an `isSwitchboardAddr` the payments departments
# trust — every switchboard-gated call to those departments flows through here, which is the single
# caller-authorization layer. Two tiers:
#   • operational (curator/relayer work: createVendor/removeVendor, add/removeDestination, settle/
#     bridge/refund) — governance OR a MissionControl security signer (`canPerformSecurityAction`), run
#     immediately (this is where the server keys act).
#   • config (setSender/setBridge/setVendorTemplate) — governance only, behind the standard timelock
#     (initiate -> executePendingAction after the confirmation block; cancelPendingAction to drop it).

# @version 0.4.3
# pragma optimize codesize

exports: addys.__interface__
exports: gov.__interface__
exports: timeLock.__interface__

initializes: addys
initializes: gov
initializes: timeLock[gov := gov]

import contracts.modules.Addys as addys
import contracts.modules.LocalGov as gov
import contracts.modules.Timelock as timeLock

interface UndyHq:
    def getAddr(_regId: uint256) -> address: view

interface MissionControl:
    def canPerformSecurityAction(_signer: address) -> bool: view

interface PayProcessor:
    def setSender(_account: address, _allowed: bool): nonpayable
    def setBridge(_bridgeAddress: address): nonpayable
    def setCatchAll(_vendor: address): nonpayable
    def settle(_paymentId: bytes32): nonpayable
    def bridge(_amount: uint256): nonpayable
    def refund(_paymentId: bytes32, _amount: uint256): nonpayable
    def pause(_shouldPause: bool): nonpayable
    def isPaused() -> bool: view

interface VendorRegistry:
    def createVendor(_id: String[128]) -> address: nonpayable
    def removeVendor(_vendor: address): nonpayable
    def setVendorTemplate(_template: address): nonpayable
    def pause(_shouldPause: bool): nonpayable
    def isPaused() -> bool: view

interface VendorProxy:
    def addDestination(_dest: address): nonpayable
    def removeDestination(_dest: address): nonpayable

# UndyHq dept ids of the payments departments (not core Addys depts)
VENDOR_REGISTRY_ID: constant(uint256) = 12
PAY_PROCESSOR_ID: constant(uint256) = 13

flag ActionType:
    SET_SENDER
    SET_BRIDGE
    SET_CATCH_ALL
    SET_VENDOR_TEMPLATE
    UNPAUSE

struct PendingSender:
    account: address
    allowed: bool

# pending timelocked config actions
actionType: public(HashMap[uint256, ActionType])
pendingSender: public(HashMap[uint256, PendingSender])
pendingBridge: public(HashMap[uint256, address])
pendingCatchAll: public(HashMap[uint256, address])
pendingVendorTemplate: public(HashMap[uint256, address])

event PendingSenderChange:
    account: indexed(address)
    allowed: bool
    confirmationBlock: uint256
    actionId: uint256

event PendingBridgeChange:
    bridgeAddress: indexed(address)
    confirmationBlock: uint256
    actionId: uint256

event PendingCatchAllChange:
    vendor: indexed(address)
    confirmationBlock: uint256
    actionId: uint256

event PendingVendorTemplateChange:
    template: indexed(address)
    confirmationBlock: uint256
    actionId: uint256

event SenderSet:
    account: indexed(address)
    allowed: bool

event BridgeSet:
    bridgeAddress: indexed(address)

event CatchAllSet:
    vendor: indexed(address)

event VendorTemplateSet:
    template: indexed(address)

event PaymentsPauseSet:
    paused: bool

event PendingUnpause:
    confirmationBlock: uint256
    actionId: uint256

event PaymentsActionCancelled:
    actionId: uint256


@deploy
def __init__(
    _undyHq: address,
    _tempGov: address,
    _minConfigTimeLock: uint256,
    _maxConfigTimeLock: uint256,
):
    addys.__init__(_undyHq)
    gov.__init__(_undyHq, _tempGov, 0, 0, 0)
    timeLock.__init__(_minConfigTimeLock, _maxConfigTimeLock, 0, _maxConfigTimeLock)


##################
# access control #
##################


@view
@internal
def _canOperate(_caller: address) -> bool:
    # governance is superuser; otherwise a MissionControl security signer (the server keys)
    if gov._canGovern(_caller):
        return True
    return staticcall MissionControl(addys._getMissionControlAddr()).canPerformSecurityAction(_caller)


@view
@internal
def _payProcessor() -> address:
    return staticcall UndyHq(addys._getUndyHq()).getAddr(PAY_PROCESSOR_ID)


@view
@internal
def _vendorRegistry() -> address:
    return staticcall UndyHq(addys._getUndyHq()).getAddr(VENDOR_REGISTRY_ID)


###############################
# operational (security-gated) #
###############################

# The departments emit their own events (VendorCreated, DestinationAdded, Settled, Bridged, Refunded, …),
# so these pass-throughs stay lean.


@external
def createVendor(_id: String[128]) -> address:
    assert self._canOperate(msg.sender)  # dev: no perms
    return extcall VendorRegistry(self._vendorRegistry()).createVendor(_id)


@external
def removeVendor(_vendor: address):
    assert self._canOperate(msg.sender)  # dev: no perms
    extcall VendorRegistry(self._vendorRegistry()).removeVendor(_vendor)


@external
def addDestination(_vendor: address, _dest: address):
    assert self._canOperate(msg.sender)  # dev: no perms
    extcall VendorProxy(_vendor).addDestination(_dest)


@external
def removeDestination(_vendor: address, _dest: address):
    assert self._canOperate(msg.sender)  # dev: no perms
    extcall VendorProxy(_vendor).removeDestination(_dest)


@external
def settle(_paymentId: bytes32):
    assert self._canOperate(msg.sender)  # dev: no perms
    extcall PayProcessor(self._payProcessor()).settle(_paymentId)


@external
def bridge(_amount: uint256):
    assert self._canOperate(msg.sender)  # dev: no perms
    extcall PayProcessor(self._payProcessor()).bridge(_amount)


@external
def refund(_paymentId: bytes32, _amount: uint256):
    assert self._canOperate(msg.sender)  # dev: no perms
    extcall PayProcessor(self._payProcessor()).refund(_paymentId, _amount)


###################
# pause / unpause #
###################


@external
def setPaused(_shouldPause: bool) -> uint256:
    # Disable is an immediate security response (governance or a security signer). Enable (unpause) is
    # governance-only and timelocked. Pauses/unpauses both payments departments (PayProcessor +
    # VendorRegistry) together — which is what freezes createVendor/removeVendor and register/settle/
    # bridge/refund (each department asserts `not isPaused`).
    if _shouldPause:
        assert self._canOperate(msg.sender)  # dev: no perms
        self._setDeptsPaused(True)
        log PaymentsPauseSet(paused=True)
        return 0

    assert gov._canGovern(msg.sender)  # dev: no perms
    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.UNPAUSE
    log PendingUnpause(confirmationBlock=timeLock._getActionConfirmationBlock(aid), actionId=aid)
    return aid


@internal
def _setDeptsPaused(_shouldPause: bool):
    # DeptBasics.pause reverts on a no-op, so only flip a department whose state actually differs.
    payProcessor: address = self._payProcessor()
    vendorRegistry: address = self._vendorRegistry()
    if staticcall PayProcessor(payProcessor).isPaused() != _shouldPause:
        extcall PayProcessor(payProcessor).pause(_shouldPause)
    if staticcall VendorRegistry(vendorRegistry).isPaused() != _shouldPause:
        extcall VendorRegistry(vendorRegistry).pause(_shouldPause)


##############################
# config (governance + timelock) #
##############################


@external
def setSender(_account: address, _allowed: bool) -> uint256:
    assert gov._canGovern(msg.sender)  # dev: no perms
    assert _account != empty(address)  # dev: invalid account
    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.SET_SENDER
    self.pendingSender[aid] = PendingSender(account=_account, allowed=_allowed)
    log PendingSenderChange(account=_account, allowed=_allowed, confirmationBlock=timeLock._getActionConfirmationBlock(aid), actionId=aid)
    return aid


@external
def setBridge(_bridgeAddress: address) -> uint256:
    assert gov._canGovern(msg.sender)  # dev: no perms
    assert _bridgeAddress != empty(address)  # dev: invalid bridge address
    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.SET_BRIDGE
    self.pendingBridge[aid] = _bridgeAddress
    log PendingBridgeChange(bridgeAddress=_bridgeAddress, confirmationBlock=timeLock._getActionConfirmationBlock(aid), actionId=aid)
    return aid


@external
def setCatchAll(_vendor: address) -> uint256:
    # The single catch-all vendor (PayProcessor skips its per-dest allow-list). MUST be the dedicated
    # catch-all VendorProxy, never a curated vendor — that vendor would go allow-any. Governance-only,
    # behind the standard config timelock.
    assert gov._canGovern(msg.sender)  # dev: no perms
    assert _vendor != empty(address) and _vendor.is_contract  # dev: invalid catch-all vendor
    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.SET_CATCH_ALL
    self.pendingCatchAll[aid] = _vendor
    log PendingCatchAllChange(vendor=_vendor, confirmationBlock=timeLock._getActionConfirmationBlock(aid), actionId=aid)
    return aid


@external
def setVendorTemplate(_template: address) -> uint256:
    assert gov._canGovern(msg.sender)  # dev: no perms
    assert _template != empty(address) and _template.is_contract  # dev: invalid template
    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.SET_VENDOR_TEMPLATE
    self.pendingVendorTemplate[aid] = _template
    log PendingVendorTemplateChange(template=_template, confirmationBlock=timeLock._getActionConfirmationBlock(aid), actionId=aid)
    return aid


@external
def executePendingAction(_aid: uint256) -> bool:
    assert gov._canGovern(msg.sender)  # dev: no perms

    # timelock gate: not confirmable yet -> false (drop it if it has expired)
    if not timeLock._confirmAction(_aid):
        if timeLock._isExpired(_aid):
            self._clearPending(_aid)
        return False

    at: ActionType = self.actionType[_aid]
    if at == ActionType.SET_SENDER:
        p: PendingSender = self.pendingSender[_aid]
        extcall PayProcessor(self._payProcessor()).setSender(p.account, p.allowed)
        log SenderSet(account=p.account, allowed=p.allowed)
    elif at == ActionType.SET_BRIDGE:
        addr: address = self.pendingBridge[_aid]
        extcall PayProcessor(self._payProcessor()).setBridge(addr)
        log BridgeSet(bridgeAddress=addr)
    elif at == ActionType.SET_CATCH_ALL:
        catchAllVendor: address = self.pendingCatchAll[_aid]
        extcall PayProcessor(self._payProcessor()).setCatchAll(catchAllVendor)
        log CatchAllSet(vendor=catchAllVendor)
    elif at == ActionType.SET_VENDOR_TEMPLATE:
        template: address = self.pendingVendorTemplate[_aid]
        extcall VendorRegistry(self._vendorRegistry()).setVendorTemplate(template)
        log VendorTemplateSet(template=template)
    elif at == ActionType.UNPAUSE:
        self._setDeptsPaused(False)
        log PaymentsPauseSet(paused=False)

    self._clearPending(_aid)
    return True


@external
def cancelPendingAction(_aid: uint256) -> bool:
    assert gov._canGovern(msg.sender)  # dev: no perms
    assert timeLock._cancelAction(_aid)  # dev: cannot cancel action
    self._clearPending(_aid)
    log PaymentsActionCancelled(actionId=_aid)
    return True


@internal
def _clearPending(_aid: uint256):
    self.actionType[_aid] = empty(ActionType)
    self.pendingSender[_aid] = empty(PendingSender)
    self.pendingBridge[_aid] = empty(address)
    self.pendingCatchAll[_aid] = empty(address)
    self.pendingVendorTemplate[_aid] = empty(address)
