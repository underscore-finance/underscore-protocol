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
    def initializeVaultConfig(_vaultAddr: address, _canDeposit: bool, _canWithdraw: bool, _maxDepositAmount: uint256, _redemptionBuffer: uint256, _minYieldWithdrawAmount: uint256, _snapShotPriceConfig: SnapShotPriceConfig, _approvedVaultTokens: DynArray[address, 25], _approvedYieldLegos: DynArray[uint256, 25]): nonpayable
    def setApprovedVaultToken(_vaultAddr: address, _vaultToken: address, _isApproved: bool): nonpayable
    def setApprovedYieldLego(_vaultAddr: address, _legoId: uint256, _isApproved: bool): nonpayable
    def setSnapShotPriceConfig(_vaultAddr: address, _config: SnapShotPriceConfig): nonpayable
    def setRedemptionBuffer(_vaultAddr: address, _buffer: uint256): nonpayable
    def setMinYieldWithdrawAmount(_vaultAddr: address, _amount: uint256): nonpayable
    def setVaultOpsFrozen(_vaultAddr: address, _isFrozen: bool): nonpayable
    def setCanWithdraw(_vaultAddr: address, _canWithdraw: bool): nonpayable
    def setCanDeposit(_vaultAddr: address, _canDeposit: bool): nonpayable
    def isValidPriceConfig(_config: SnapShotPriceConfig) -> bool: view
    def isEarnVault(_vaultAddr: address) -> bool: view

interface MissionControl:
    def canPerformSecurityAction(_signer: address) -> bool: view

flag ActionType:
    REDEMPTION_BUFFER
    MIN_YIELD_WITHDRAW_AMOUNT
    SNAPSHOT_PRICE_CONFIG
    APPROVED_VAULT_TOKEN
    APPROVED_YIELD_LEGO
    INITIALIZE_VAULT_CONFIG

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
    vaultAddr: address
    config: SnapShotPriceConfig

struct PendingApprovedVaultToken:
    vaultAddr: address
    vaultToken: address
    isApproved: bool

struct PendingApprovedYieldLego:
    vaultAddr: address
    legoId: uint256
    isApproved: bool

struct PendingInitializeVaultConfig:
    vaultAddr: address
    canDeposit: bool
    canWithdraw: bool
    maxDepositAmount: uint256
    redemptionBuffer: uint256
    minYieldWithdrawAmount: uint256
    snapShotPriceConfig: SnapShotPriceConfig
    approvedVaultTokens: DynArray[address, 25]
    approvedYieldLegos: DynArray[uint256, 25]

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
    vaultAddr: indexed(address)
    minSnapshotDelay: uint256
    maxNumSnapshots: uint256
    maxUpsideDeviation: uint256
    staleTime: uint256
    confirmationBlock: uint256
    actionId: uint256

event SnapShotPriceConfigSet:
    vaultAddr: indexed(address)
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

event PendingApprovedYieldLegoChange:
    vaultAddr: indexed(address)
    legoId: indexed(uint256)
    isApproved: bool
    confirmationBlock: uint256
    actionId: uint256

event ApprovedYieldLegoSet:
    vaultAddr: indexed(address)
    legoId: indexed(uint256)
    isApproved: bool

event PendingInitializeVaultConfigChange:
    vaultAddr: indexed(address)
    canDeposit: bool
    canWithdraw: bool
    maxDepositAmount: uint256
    redemptionBuffer: uint256
    numApprovedVaultTokens: uint256
    numApprovedYieldLegos: uint256
    confirmationBlock: uint256
    actionId: uint256

event VaultConfigInitialized:
    vaultAddr: indexed(address)
    canDeposit: bool
    canWithdraw: bool
    maxDepositAmount: uint256
    redemptionBuffer: uint256

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

# pending config changes
actionType: public(HashMap[uint256, ActionType]) # aid -> type
pendingRedemptionBuffer: public(HashMap[uint256, PendingRedemptionBuffer]) # aid -> config
pendingMinYieldWithdrawAmount: public(HashMap[uint256, PendingMinYieldWithdrawAmount]) # aid -> config
pendingSnapShotPriceConfig: public(HashMap[uint256, PendingSnapShotPriceConfig]) # aid -> config
pendingApprovedVaultToken: public(HashMap[uint256, PendingApprovedVaultToken]) # aid -> config
pendingApprovedYieldLego: public(HashMap[uint256, PendingApprovedYieldLego]) # aid -> config
pendingInitializeVaultConfig: public(HashMap[uint256, PendingInitializeVaultConfig]) # aid -> config


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


##############
# Timelocked #
##############


# redemption buffer


@external
def setRedemptionBuffer(_vaultAddr: address, _buffer: uint256) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    assert staticcall VaultRegistry(addys._getVaultRegistryAddr()).isEarnVault(_vaultAddr) # dev: invalid vault addr
    assert _buffer <= 10_00 # dev: buffer too high (max 10%)

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
def setSnapShotPriceConfig(_vaultAddr: address, _config: SnapShotPriceConfig) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms

    # validation
    vr: address = addys._getVaultRegistryAddr()
    assert staticcall VaultRegistry(vr).isEarnVault(_vaultAddr) # dev: invalid vault addr
    assert staticcall VaultRegistry(vr).isValidPriceConfig(_config) # dev: invalid price config

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.SNAPSHOT_PRICE_CONFIG
    self.pendingSnapShotPriceConfig[aid] = PendingSnapShotPriceConfig(
        vaultAddr=_vaultAddr,
        config=_config
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingSnapShotPriceConfigChange(
        vaultAddr=_vaultAddr,
        minSnapshotDelay=_config.minSnapshotDelay,
        maxNumSnapshots=_config.maxNumSnapshots,
        maxUpsideDeviation=_config.maxUpsideDeviation,
        staleTime=_config.staleTime,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


# approved vault token


@external
def setApprovedVaultToken(_vaultAddr: address, _vaultToken: address, _isApproved: bool) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    assert staticcall VaultRegistry(addys._getVaultRegistryAddr()).isEarnVault(_vaultAddr) # dev: invalid vault addr
    assert _vaultToken != empty(address) # dev: invalid vault token

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


# approved yield lego


@external
def setApprovedYieldLego(_vaultAddr: address, _legoId: uint256, _isApproved: bool) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    assert staticcall VaultRegistry(addys._getVaultRegistryAddr()).isEarnVault(_vaultAddr) # dev: invalid vault addr
    assert _legoId != 0 # dev: invalid lego id

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.APPROVED_YIELD_LEGO
    self.pendingApprovedYieldLego[aid] = PendingApprovedYieldLego(
        vaultAddr=_vaultAddr,
        legoId=_legoId,
        isApproved=_isApproved
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingApprovedYieldLegoChange(
        vaultAddr=_vaultAddr,
        legoId=_legoId,
        isApproved=_isApproved,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


# initialize vault config


@external
def initializeVaultConfig(
    _vaultAddr: address,
    _canDeposit: bool,
    _canWithdraw: bool,
    _maxDepositAmount: uint256,
    _redemptionBuffer: uint256,
    _minYieldWithdrawAmount: uint256,
    _snapShotPriceConfig: SnapShotPriceConfig,
    _approvedVaultTokens: DynArray[address, 25] = [],
    _approvedYieldLegos: DynArray[uint256, 25] = [],
) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    assert _vaultAddr != empty(address) # dev: invalid vault addr
    assert _redemptionBuffer <= 10_00 # dev: buffer too high (max 10%)

    # validate config via VaultRegistry
    vr: address = addys._getVaultRegistryAddr()
    assert staticcall VaultRegistry(vr).isValidPriceConfig(_snapShotPriceConfig) # dev: invalid price config

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.INITIALIZE_VAULT_CONFIG
    self.pendingInitializeVaultConfig[aid] = PendingInitializeVaultConfig(
        vaultAddr=_vaultAddr,
        canDeposit=_canDeposit,
        canWithdraw=_canWithdraw,
        maxDepositAmount=_maxDepositAmount,
        redemptionBuffer=_redemptionBuffer,
        minYieldWithdrawAmount=_minYieldWithdrawAmount,
        snapShotPriceConfig=_snapShotPriceConfig,
        approvedVaultTokens=_approvedVaultTokens,
        approvedYieldLegos=_approvedYieldLegos,
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingInitializeVaultConfigChange(
        vaultAddr=_vaultAddr,
        canDeposit=_canDeposit,
        canWithdraw=_canWithdraw,
        maxDepositAmount=_maxDepositAmount,
        redemptionBuffer=_redemptionBuffer,
        numApprovedVaultTokens=len(_approvedVaultTokens),
        numApprovedYieldLegos=len(_approvedYieldLegos),
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
        extcall VaultRegistry(vr).setSnapShotPriceConfig(p.vaultAddr, p.config)
        log SnapShotPriceConfigSet(
            vaultAddr=p.vaultAddr,
            minSnapshotDelay=p.config.minSnapshotDelay,
            maxNumSnapshots=p.config.maxNumSnapshots,
            maxUpsideDeviation=p.config.maxUpsideDeviation,
            staleTime=p.config.staleTime
        )

    elif actionType == ActionType.APPROVED_VAULT_TOKEN:
        p: PendingApprovedVaultToken = self.pendingApprovedVaultToken[_aid]
        extcall VaultRegistry(vr).setApprovedVaultToken(p.vaultAddr, p.vaultToken, p.isApproved)
        log ApprovedVaultTokenSet(vaultAddr=p.vaultAddr, vaultToken=p.vaultToken, isApproved=p.isApproved)

    elif actionType == ActionType.APPROVED_YIELD_LEGO:
        p: PendingApprovedYieldLego = self.pendingApprovedYieldLego[_aid]
        extcall VaultRegistry(vr).setApprovedYieldLego(p.vaultAddr, p.legoId, p.isApproved)
        log ApprovedYieldLegoSet(vaultAddr=p.vaultAddr, legoId=p.legoId, isApproved=p.isApproved)

    elif actionType == ActionType.INITIALIZE_VAULT_CONFIG:
        p: PendingInitializeVaultConfig = self.pendingInitializeVaultConfig[_aid]
        extcall VaultRegistry(vr).initializeVaultConfig(
            p.vaultAddr,
            p.canDeposit,
            p.canWithdraw,
            p.maxDepositAmount,
            p.redemptionBuffer,
            p.minYieldWithdrawAmount,
            p.snapShotPriceConfig,
            p.approvedVaultTokens,
            p.approvedYieldLegos,
        )
        log VaultConfigInitialized(
            vaultAddr=p.vaultAddr,
            canDeposit=p.canDeposit,
            canWithdraw=p.canWithdraw,
            maxDepositAmount=p.maxDepositAmount,
            redemptionBuffer=p.redemptionBuffer
        )

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
