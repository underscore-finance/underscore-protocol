#        ______   __     __   __   ______  ______   __  __   ______   ______   ______   ______   _____    
#       /\  ___\ /\ \  _ \ \ /\ \ /\__  _\/\  ___\ /\ \_\ \ /\  == \ /\  __ \ /\  __ \ /\  == \ /\  __-.  
#       \ \___  \\ \ \/ ".\ \\ \ \\/_/\ \/\ \ \____\ \  __ \\ \  __< \ \ \/\ \\ \  __ \\ \  __< \ \ \/\ \ 
#        \/\_____\\ \__/".~\_\\ \_\  \ \_\ \ \_____\\ \_\ \_\\ \_____\\ \_____\\ \_\ \_\\ \_\ \_\\ \____- 
#         \/_____/ \/_/   \/_/ \/_/   \/_/  \/_____/ \/_/\/_/ \/_____/ \/_____/ \/_/\/_/ \/_/ /_/ \/____/ 
#                                                    ┏┓┓     ┓•  
#                                                    ┃ ┣┓┏┓┏┓┃┓┏┓
#                                                    ┗┛┛┗┗┻┛ ┗┗┗ 
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

exports: addys.__interface__
exports: gov.__interface__
exports: timeLock.__interface__

initializes: addys
initializes: gov
initializes: timeLock[gov := gov]

import contracts.modules.Addys as addys
import contracts.modules.LocalGov as gov
import contracts.modules.TimeLock as timeLock

interface VaultRegistry:
    def setApprovedVaultToken(_vaultAddr: address, _vaultToken: address, _isApproved: bool): nonpayable
    def setDefaultTargetVaultToken(_vaultAddr: address, _targetVaultToken: address): nonpayable
    def setMaxDepositAmount(_vaultAddr: address, _maxDepositAmount: uint256): nonpayable
    def setShouldAutoDeposit(_vaultAddr: address, _shouldAutoDeposit: bool): nonpayable
    def isApprovedVaultToken(_vaultAddr: address, _vaultToken: address) -> bool: view
    def setPerformanceFee(_vaultAddr: address, _performanceFee: uint256): nonpayable
    def setMinYieldWithdrawAmount(_vaultAddr: address, _amount: uint256): nonpayable
    def setRedemptionBuffer(_vaultAddr: address, _buffer: uint256): nonpayable
    def setVaultOpsFrozen(_vaultAddr: address, _isFrozen: bool): nonpayable
    def setCanWithdraw(_vaultAddr: address, _canWithdraw: bool): nonpayable
    def setCanDeposit(_vaultAddr: address, _canDeposit: bool): nonpayable
    def isValidPerformanceFee(_performanceFee: uint256) -> bool: view
    def isValidRedemptionBuffer(_buffer: uint256) -> bool: view
    def isValidVaultToken(_vaultToken: address) -> bool: view
    def isEarnVault(_vaultAddr: address) -> bool: view

interface MissionControl:
    def canPerformSecurityAction(_signer: address) -> bool: view

interface YieldLego:
    def setSnapShotPriceConfig(_config: SnapShotPriceConfig): nonpayable
    def isValidPriceConfig(_config: SnapShotPriceConfig) -> bool: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

flag ActionType:
    REDEMPTION_BUFFER
    MIN_YIELD_WITHDRAW_AMOUNT
    SNAPSHOT_PRICE_CONFIG
    APPROVED_VAULT_TOKEN
    PERFORMANCE_FEE
    DEFAULT_TARGET_VAULT_TOKEN
    MAX_DEPOSIT_AMOUNT

struct SnapShotPriceConfig:
    minSnapshotDelay: uint256
    maxNumSnapshots: uint256
    maxUpsideDeviation: uint256
    staleTime: uint256

struct PendingRedemptionBuffer:
    vaultAddr: address
    buffer: uint256

struct PendingMinYieldWithdrawAmount:
    vaultAddr: address
    amount: uint256

struct PendingSnapShotPriceConfig:
    legoId: uint256
    config: SnapShotPriceConfig

struct PendingApprovedVaultToken:
    vaultAddr: address
    vaultToken: address
    isApproved: bool

struct PendingPerformanceFee:
    vaultAddr: address
    performanceFee: uint256

struct PendingDefaultTargetVaultToken:
    vaultAddr: address
    targetVaultToken: address

struct PendingMaxDepositAmount:
    vaultAddr: address
    maxDepositAmount: uint256

event PendingRedemptionBufferChange:
    vaultAddr: indexed(address)
    buffer: uint256
    confirmationBlock: uint256
    actionId: uint256

event RedemptionBufferSet:
    vaultAddr: indexed(address)
    buffer: uint256

event PendingMinYieldWithdrawAmountChange:
    vaultAddr: indexed(address)
    amount: uint256
    confirmationBlock: uint256
    actionId: uint256

event MinYieldWithdrawAmountSet:
    vaultAddr: indexed(address)
    amount: uint256

event PendingSnapShotPriceConfigChange:
    legoId: indexed(uint256)
    minSnapshotDelay: uint256
    maxNumSnapshots: uint256
    maxUpsideDeviation: uint256
    staleTime: uint256
    confirmationBlock: uint256
    actionId: uint256

event SnapShotPriceConfigSet:
    legoId: indexed(uint256)
    legoAddr: indexed(address)
    minSnapshotDelay: uint256
    maxNumSnapshots: uint256
    maxUpsideDeviation: uint256
    staleTime: uint256

event PendingApprovedVaultTokenChange:
    vaultAddr: indexed(address)
    vaultToken: indexed(address)
    isApproved: bool
    confirmationBlock: uint256
    actionId: uint256

event ApprovedVaultTokenSet:
    vaultAddr: indexed(address)
    vaultToken: indexed(address)
    isApproved: bool

event PendingPerformanceFeeChange:
    vaultAddr: indexed(address)
    performanceFee: uint256
    confirmationBlock: uint256
    actionId: uint256

event PerformanceFeeSet:
    vaultAddr: indexed(address)
    performanceFee: uint256

event PendingDefaultTargetVaultTokenChange:
    vaultAddr: indexed(address)
    targetVaultToken: indexed(address)
    confirmationBlock: uint256
    actionId: uint256

event DefaultTargetVaultTokenSet:
    vaultAddr: indexed(address)
    targetVaultToken: indexed(address)

event PendingMaxDepositAmountChange:
    vaultAddr: indexed(address)
    maxDepositAmount: uint256
    confirmationBlock: uint256
    actionId: uint256

event MaxDepositAmountSet:
    vaultAddr: indexed(address)
    maxDepositAmount: uint256

event CanDepositSet:
    vaultAddr: indexed(address)
    canDeposit: bool
    caller: indexed(address)

event CanWithdrawSet:
    vaultAddr: indexed(address)
    canWithdraw: bool
    caller: indexed(address)

event VaultOpsFrozenSet:
    vaultAddr: indexed(address)
    isFrozen: bool
    caller: indexed(address)

event ShouldAutoDepositSet:
    vaultAddr: indexed(address)
    shouldAutoDeposit: bool
    caller: indexed(address)

# pending config changes
actionType: public(HashMap[uint256, ActionType]) # aid -> type
pendingRedemptionBuffer: public(HashMap[uint256, PendingRedemptionBuffer]) # aid -> config
pendingMinYieldWithdrawAmount: public(HashMap[uint256, PendingMinYieldWithdrawAmount]) # aid -> config
pendingSnapShotPriceConfig: public(HashMap[uint256, PendingSnapShotPriceConfig]) # aid -> config
pendingApprovedVaultToken: public(HashMap[uint256, PendingApprovedVaultToken]) # aid -> config
pendingPerformanceFee: public(HashMap[uint256, PendingPerformanceFee]) # aid -> config
pendingDefaultTargetVaultToken: public(HashMap[uint256, PendingDefaultTargetVaultToken]) # aid -> config
pendingMaxDepositAmount: public(HashMap[uint256, PendingMaxDepositAmount]) # aid -> config


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


# access control


@view
@internal
def _hasPermsToFreeze(_caller: address, _shouldFreeze: bool) -> bool:
    if gov._canGovern(_caller):
        return True
    if _shouldFreeze:
        return staticcall MissionControl(addys._getMissionControlAddr()).canPerformSecurityAction(_caller)
    return False


#####################
# Immediate Actions #
#####################


# can deposit


@external
def setCanDeposit(_vaultAddr: address, _canDeposit: bool):
    assert self._hasPermsToFreeze(msg.sender, not _canDeposit) # dev: no perms
    extcall VaultRegistry(addys._getVaultRegistryAddr()).setCanDeposit(_vaultAddr, _canDeposit)
    log CanDepositSet(vaultAddr=_vaultAddr, canDeposit=_canDeposit, caller=msg.sender)


# can withdraw


@external
def setCanWithdraw(_vaultAddr: address, _canWithdraw: bool):
    assert self._hasPermsToFreeze(msg.sender, not _canWithdraw) # dev: no perms
    extcall VaultRegistry(addys._getVaultRegistryAddr()).setCanWithdraw(_vaultAddr, _canWithdraw)
    log CanWithdrawSet(vaultAddr=_vaultAddr, canWithdraw=_canWithdraw, caller=msg.sender)


# vault ops frozen


@external
def setVaultOpsFrozen(_vaultAddr: address, _isFrozen: bool):
    assert self._hasPermsToFreeze(msg.sender, _isFrozen) # dev: no perms
    extcall VaultRegistry(addys._getVaultRegistryAddr()).setVaultOpsFrozen(_vaultAddr, _isFrozen)
    log VaultOpsFrozenSet(vaultAddr=_vaultAddr, isFrozen=_isFrozen, caller=msg.sender)


# should auto deposit


@external
def setShouldAutoDeposit(_vaultAddr: address, _shouldAutoDeposit: bool):
    assert self._hasPermsToFreeze(msg.sender, not _shouldAutoDeposit) # dev: no perms
    extcall VaultRegistry(addys._getVaultRegistryAddr()).setShouldAutoDeposit(_vaultAddr, _shouldAutoDeposit)
    log ShouldAutoDepositSet(vaultAddr=_vaultAddr, shouldAutoDeposit=_shouldAutoDeposit, caller=msg.sender)


##############
# Timelocked #
##############


# redemption buffer


@external
def setRedemptionBuffer(_vaultAddr: address, _buffer: uint256) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    vr: address = addys._getVaultRegistryAddr()
    assert staticcall VaultRegistry(vr).isEarnVault(_vaultAddr) # dev: invalid vault addr
    assert staticcall VaultRegistry(vr).isValidRedemptionBuffer(_buffer) # dev: invalid redemption buffer

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.REDEMPTION_BUFFER
    self.pendingRedemptionBuffer[aid] = PendingRedemptionBuffer(
        vaultAddr=_vaultAddr,
        buffer=_buffer
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingRedemptionBufferChange(
        vaultAddr=_vaultAddr,
        buffer=_buffer,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


# min yield withdraw amount


@external
def setMinYieldWithdrawAmount(_vaultAddr: address, _amount: uint256) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    assert staticcall VaultRegistry(addys._getVaultRegistryAddr()).isEarnVault(_vaultAddr) # dev: invalid vault addr

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.MIN_YIELD_WITHDRAW_AMOUNT
    self.pendingMinYieldWithdrawAmount[aid] = PendingMinYieldWithdrawAmount(
        vaultAddr=_vaultAddr,
        amount=_amount
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingMinYieldWithdrawAmountChange(
        vaultAddr=_vaultAddr,
        amount=_amount,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


# snapshot price config


@external
def setSnapShotPriceConfig(
    _legoId: uint256,
    _minSnapshotDelay: uint256,
    _maxNumSnapshots: uint256,
    _maxUpsideDeviation: uint256,
    _staleTime: uint256,
) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms

    # validation - get lego address from lego book
    legoBook: address = addys._getLegoBookAddr()
    legoAddr: address = staticcall Registry(legoBook).getAddr(_legoId)
    assert legoAddr != empty(address) # dev: invalid lego id

    config: SnapShotPriceConfig = SnapShotPriceConfig(
        minSnapshotDelay=_minSnapshotDelay,
        maxNumSnapshots=_maxNumSnapshots,
        maxUpsideDeviation=_maxUpsideDeviation,
        staleTime=_staleTime,
    )
    assert staticcall YieldLego(legoAddr).isValidPriceConfig(config) # dev: invalid price config

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.SNAPSHOT_PRICE_CONFIG
    self.pendingSnapShotPriceConfig[aid] = PendingSnapShotPriceConfig(
        legoId=_legoId,
        config=config
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingSnapShotPriceConfigChange(
        legoId=_legoId,
        minSnapshotDelay=config.minSnapshotDelay,
        maxNumSnapshots=config.maxNumSnapshots,
        maxUpsideDeviation=config.maxUpsideDeviation,
        staleTime=config.staleTime,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


# approved vault token


@external
def setApprovedVaultToken(_vaultAddr: address, _vaultToken: address, _isApproved: bool) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    vr: address = addys._getVaultRegistryAddr()
    assert staticcall VaultRegistry(vr).isEarnVault(_vaultAddr) # dev: invalid vault addr
    assert staticcall VaultRegistry(vr).isValidVaultToken(_vaultToken) # dev: invalid vault token

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.APPROVED_VAULT_TOKEN
    self.pendingApprovedVaultToken[aid] = PendingApprovedVaultToken(
        vaultAddr=_vaultAddr,
        vaultToken=_vaultToken,
        isApproved=_isApproved
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingApprovedVaultTokenChange(
        vaultAddr=_vaultAddr,
        vaultToken=_vaultToken,
        isApproved=_isApproved,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


# performance fee


@external
def setPerformanceFee(_vaultAddr: address, _performanceFee: uint256) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    vr: address = addys._getVaultRegistryAddr()
    assert staticcall VaultRegistry(vr).isEarnVault(_vaultAddr) # dev: invalid vault addr
    assert staticcall VaultRegistry(vr).isValidPerformanceFee(_performanceFee) # dev: invalid performance fee

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.PERFORMANCE_FEE
    self.pendingPerformanceFee[aid] = PendingPerformanceFee(
        vaultAddr=_vaultAddr,
        performanceFee=_performanceFee
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingPerformanceFeeChange(
        vaultAddr=_vaultAddr,
        performanceFee=_performanceFee,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


# default target vault token


@external
def setDefaultTargetVaultToken(_vaultAddr: address, _targetVaultToken: address) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    vr: address = addys._getVaultRegistryAddr()
    assert staticcall VaultRegistry(vr).isEarnVault(_vaultAddr) # dev: invalid vault addr
    assert not staticcall VaultRegistry(vr).isApprovedVaultToken(_vaultAddr, _targetVaultToken) # dev: vault token already approved

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.DEFAULT_TARGET_VAULT_TOKEN
    self.pendingDefaultTargetVaultToken[aid] = PendingDefaultTargetVaultToken(
        vaultAddr=_vaultAddr,
        targetVaultToken=_targetVaultToken
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingDefaultTargetVaultTokenChange(
        vaultAddr=_vaultAddr,
        targetVaultToken=_targetVaultToken,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


# max deposit amount


@external
def setMaxDepositAmount(_vaultAddr: address, _maxDepositAmount: uint256) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    vr: address = addys._getVaultRegistryAddr()
    assert staticcall VaultRegistry(vr).isEarnVault(_vaultAddr) # dev: invalid vault addr

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.MAX_DEPOSIT_AMOUNT
    self.pendingMaxDepositAmount[aid] = PendingMaxDepositAmount(
        vaultAddr=_vaultAddr,
        maxDepositAmount=_maxDepositAmount
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingMaxDepositAmountChange(
        vaultAddr=_vaultAddr,
        maxDepositAmount=_maxDepositAmount,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


#############
# Execution #
#############


@external
def executePendingAction(_aid: uint256) -> bool:
    assert gov._canGovern(msg.sender) # dev: no perms

    # check time lock
    if not timeLock._confirmAction(_aid):
        if timeLock._isExpired(_aid):
            self._cancelPendingAction(_aid)
        return False

    actionType: ActionType = self.actionType[_aid]
    vr: address = addys._getVaultRegistryAddr()

    if actionType == ActionType.REDEMPTION_BUFFER:
        p: PendingRedemptionBuffer = self.pendingRedemptionBuffer[_aid]
        extcall VaultRegistry(vr).setRedemptionBuffer(p.vaultAddr, p.buffer)
        log RedemptionBufferSet(vaultAddr=p.vaultAddr, buffer=p.buffer)

    elif actionType == ActionType.MIN_YIELD_WITHDRAW_AMOUNT:
        p: PendingMinYieldWithdrawAmount = self.pendingMinYieldWithdrawAmount[_aid]
        extcall VaultRegistry(vr).setMinYieldWithdrawAmount(p.vaultAddr, p.amount)
        log MinYieldWithdrawAmountSet(vaultAddr=p.vaultAddr, amount=p.amount)

    elif actionType == ActionType.SNAPSHOT_PRICE_CONFIG:
        p: PendingSnapShotPriceConfig = self.pendingSnapShotPriceConfig[_aid]
        # get lego address from lego book
        legoBook: address = addys._getLegoBookAddr()
        legoAddr: address = staticcall Registry(legoBook).getAddr(p.legoId)
        # set config on the lego
        extcall YieldLego(legoAddr).setSnapShotPriceConfig(p.config)
        log SnapShotPriceConfigSet(
            legoId=p.legoId,
            legoAddr=legoAddr,
            minSnapshotDelay=p.config.minSnapshotDelay,
            maxNumSnapshots=p.config.maxNumSnapshots,
            maxUpsideDeviation=p.config.maxUpsideDeviation,
            staleTime=p.config.staleTime
        )

    elif actionType == ActionType.APPROVED_VAULT_TOKEN:
        p: PendingApprovedVaultToken = self.pendingApprovedVaultToken[_aid]
        extcall VaultRegistry(vr).setApprovedVaultToken(p.vaultAddr, p.vaultToken, p.isApproved)
        log ApprovedVaultTokenSet(vaultAddr=p.vaultAddr, vaultToken=p.vaultToken, isApproved=p.isApproved)

    elif actionType == ActionType.PERFORMANCE_FEE:
        p: PendingPerformanceFee = self.pendingPerformanceFee[_aid]
        extcall VaultRegistry(vr).setPerformanceFee(p.vaultAddr, p.performanceFee)
        log PerformanceFeeSet(vaultAddr=p.vaultAddr, performanceFee=p.performanceFee)

    elif actionType == ActionType.DEFAULT_TARGET_VAULT_TOKEN:
        p: PendingDefaultTargetVaultToken = self.pendingDefaultTargetVaultToken[_aid]
        extcall VaultRegistry(vr).setDefaultTargetVaultToken(p.vaultAddr, p.targetVaultToken)
        log DefaultTargetVaultTokenSet(vaultAddr=p.vaultAddr, targetVaultToken=p.targetVaultToken)

    elif actionType == ActionType.MAX_DEPOSIT_AMOUNT:
        p: PendingMaxDepositAmount = self.pendingMaxDepositAmount[_aid]
        extcall VaultRegistry(vr).setMaxDepositAmount(p.vaultAddr, p.maxDepositAmount)
        log MaxDepositAmountSet(vaultAddr=p.vaultAddr, maxDepositAmount=p.maxDepositAmount)

    self.actionType[_aid] = empty(ActionType)
    return True


# cancel action


@external
def cancelPendingAction(_aid: uint256) -> bool:
    assert gov._canGovern(msg.sender) # dev: no perms
    self._cancelPendingAction(_aid)
    return True


@internal
def _cancelPendingAction(_aid: uint256):
    assert timeLock._cancelAction(_aid) # dev: cannot cancel action
    self.actionType[_aid] = empty(ActionType)
