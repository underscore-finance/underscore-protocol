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

from interfaces import LegoStructs as ls
from ethereum.ercs import IERC4626

interface VaultRegistry:
    def setApprovedVaultTokens(_vaultAddr: address, _vaultTokens: DynArray[address, MAX_VAULT_TOKENS], _isApproved: bool, _shouldMaxWithdraw: bool): nonpayable
    def setApprovedVaultToken(_vaultAddr: address, _vaultToken: address, _isApproved: bool, _shouldMaxWithdraw: bool): nonpayable
    def setDefaultTargetVaultToken(_vaultAddr: address, _targetVaultToken: address): nonpayable
    def setMaxDepositAmount(_vaultAddr: address, _maxDepositAmount: uint256): nonpayable
    def setShouldAutoDeposit(_vaultAddr: address, _shouldAutoDeposit: bool): nonpayable
    def setIsLeveragedVault(_vaultAddr: address, _isLeveragedVault: bool): nonpayable
    def isApprovedVaultToken(_vaultAddr: address, _vaultToken: address) -> bool: view
    def setPerformanceFee(_vaultAddr: address, _performanceFee: uint256): nonpayable
    def setMinYieldWithdrawAmount(_vaultAddr: address, _amount: uint256): nonpayable
    def setRedemptionBuffer(_vaultAddr: address, _buffer: uint256): nonpayable
    def setVaultOpsFrozen(_vaultAddr: address, _isFrozen: bool): nonpayable
    def setCanWithdraw(_vaultAddr: address, _canWithdraw: bool): nonpayable
    def setCanDeposit(_vaultAddr: address, _canDeposit: bool): nonpayable
    def isValidPerformanceFee(_performanceFee: uint256) -> bool: view
    def isValidRedemptionBuffer(_buffer: uint256) -> bool: view
    def isEarnVault(_vaultAddr: address) -> bool: view

interface LevgVault:
    def setCollateralVault(_vaultToken: address, _legoId: uint256, _ripeVaultId: uint256, _shouldMaxWithdraw: bool): nonpayable
    def setLeverageVault(_vaultToken: address, _legoId: uint256, _ripeVaultId: uint256, _shouldMaxWithdraw: bool): nonpayable
    def setSlippagesAllowed(_usdcSlippage: uint256, _greenSlippage: uint256): nonpayable
    def setLevgVaultHelper(_levgVaultHelper: address): nonpayable
    def updateYieldPosition(_vaultToken: address): nonpayable
    def claimPerformanceFees() -> uint256: nonpayable
    def removeManager(_manager: address): nonpayable
    def setMaxDebtRatio(_ratio: uint256): nonpayable
    def addManager(_manager: address): nonpayable
    def levgVaultHelper() -> address: view
    def USDC() -> address: view

interface YieldLego:
    def deregisterVaultTokenLocally(_asset: address, _vaultToken: address): nonpayable
    def registerVaultTokenLocally(_asset: address, _vaultToken: address): nonpayable
    def canRegisterVaultToken(_asset: address, _vaultToken: address) -> bool: view
    def setSnapShotPriceConfig(_config: ls.SnapShotPriceConfig): nonpayable
    def isValidPriceConfig(_config: ls.SnapShotPriceConfig) -> bool: view
    def addPriceSnapshot(_vaultToken: address) -> bool: nonpayable
    def setMorphoRewardsAddr(_rewardsAddr: address): nonpayable
    def setEulerRewardsAddr(_rewardsAddr: address): nonpayable
    def setCompRewardsAddr(_rewardsAddr: address): nonpayable

interface LevgVaultHelper:
    def isValidVaultToken(_underlyingAsset: address, _vaultToken: address, _ripeVaultId: uint256, _legoId: uint256) -> bool: view

interface MissionControl:
    def canPerformSecurityAction(_signer: address) -> bool: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

interface EarnVault:
    def sweepLeftovers() -> uint256: nonpayable

flag ActionType:
    REDEMPTION_BUFFER
    MIN_YIELD_WITHDRAW_AMOUNT
    SNAPSHOT_PRICE_CONFIG
    APPROVED_VAULT_TOKEN
    APPROVED_VAULT_TOKENS
    PERFORMANCE_FEE
    DEFAULT_TARGET_VAULT_TOKEN
    MAX_DEPOSIT_AMOUNT
    IS_LEVERAGED_VAULT
    COLLATERAL_VAULT
    LEVERAGE_VAULT
    SLIPPAGES
    LEVG_VAULT_HELPER
    MAX_DEBT_RATIO
    ADD_MANAGER
    REMOVE_MANAGER
    REGISTER_VAULT_TOKEN_ON_LEGO
    SET_MORPHO_REWARDS_ADDR
    SET_EULER_REWARDS_ADDR
    SET_COMP_REWARDS_ADDR

struct PendingRedemptionBuffer:
    vaultAddr: address
    buffer: uint256

struct PendingMinYieldWithdrawAmount:
    vaultAddr: address
    amount: uint256

struct PendingSnapShotPriceConfig:
    legoId: uint256
    config: ls.SnapShotPriceConfig

struct PendingApprovedVaultToken:
    vaultAddr: address
    vaultToken: address
    isApproved: bool
    shouldMaxWithdraw: bool

struct PendingApprovedVaultTokens:
    vaultAddr: address
    vaultTokens: DynArray[address, MAX_VAULT_TOKENS]
    isApproved: bool
    shouldMaxWithdraw: bool

struct PendingPerformanceFee:
    vaultAddr: address
    performanceFee: uint256

struct PendingDefaultTargetVaultToken:
    vaultAddr: address
    targetVaultToken: address

struct PendingMaxDepositAmount:
    vaultAddr: address
    maxDepositAmount: uint256

struct PendingIsLeveragedVault:
    vaultAddr: address
    isLeveragedVault: bool

struct PendingCollateralVault:
    vaultAddr: address
    vaultToken: address
    ripeVaultId: uint256
    legoId: uint256
    shouldMaxWithdraw: bool

struct PendingLeverageVault:
    vaultAddr: address
    vaultToken: address
    legoId: uint256
    ripeVaultId: uint256
    shouldMaxWithdraw: bool

struct PendingSlippages:
    vaultAddr: address
    usdcSlippage: uint256
    greenSlippage: uint256

struct PendingLevgVaultHelper:
    vaultAddr: address
    levgVaultHelper: address

struct PendingMaxDebtRatio:
    vaultAddr: address
    ratio: uint256

struct PendingAddManager:
    vaultAddr: address
    manager: address

struct PendingRemoveManager:
    vaultAddr: address
    manager: address

struct PendingRegisterVaultTokenOnLego:
    legoId: uint256
    asset: address
    vaultToken: address

struct PendingMorphoRewardsAddr:
    legoId: uint256
    rewardsAddr: address

struct PendingEulerRewardsAddr:
    legoId: uint256
    rewardsAddr: address

struct PendingCompRewardsAddr:
    legoId: uint256
    rewardsAddr: address

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

event PendingApprovedVaultTokensChange:
    vaultAddr: indexed(address)
    numTokens: uint256
    isApproved: bool
    confirmationBlock: uint256
    actionId: uint256

event ApprovedVaultTokensSet:
    vaultAddr: indexed(address)
    numTokens: uint256
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

event PendingIsLeveragedVaultChange:
    vaultAddr: indexed(address)
    isLeveragedVault: bool
    confirmationBlock: uint256
    actionId: uint256

event IsLeveragedVaultSet:
    vaultAddr: indexed(address)
    isLeveragedVault: bool

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

event PendingCollateralVaultChange:
    vaultAddr: indexed(address)
    vaultToken: indexed(address)
    ripeVaultId: uint256
    legoId: uint256
    shouldMaxWithdraw: bool
    confirmationBlock: uint256
    actionId: uint256

event CollateralVaultSet:
    vaultAddr: indexed(address)
    vaultToken: indexed(address)
    ripeVaultId: uint256
    legoId: uint256

event PendingLeverageVaultChange:
    vaultAddr: indexed(address)
    vaultToken: indexed(address)
    legoId: uint256
    ripeVaultId: uint256
    shouldMaxWithdraw: bool
    confirmationBlock: uint256
    actionId: uint256

event LeverageVaultSet:
    vaultAddr: indexed(address)
    vaultToken: indexed(address)
    legoId: uint256
    ripeVaultId: uint256

event PendingSlippagesChange:
    vaultAddr: indexed(address)
    usdcSlippage: uint256
    greenSlippage: uint256
    confirmationBlock: uint256
    actionId: uint256

event SlippagesSet:
    vaultAddr: indexed(address)
    usdcSlippage: uint256
    greenSlippage: uint256

event PendingLevgVaultHelperChange:
    vaultAddr: indexed(address)
    levgVaultHelper: indexed(address)
    confirmationBlock: uint256
    actionId: uint256

event LevgVaultHelperSet:
    vaultAddr: indexed(address)
    levgVaultHelper: indexed(address)

event PendingMaxDebtRatioChange:
    vaultAddr: indexed(address)
    ratio: uint256
    confirmationBlock: uint256
    actionId: uint256

event MaxDebtRatioSet:
    vaultAddr: indexed(address)
    ratio: uint256

event PendingAddManagerChange:
    vaultAddr: indexed(address)
    manager: indexed(address)
    confirmationBlock: uint256
    actionId: uint256

event ManagerAdded:
    vaultAddr: indexed(address)
    manager: indexed(address)

event PendingRemoveManagerChange:
    vaultAddr: indexed(address)
    manager: indexed(address)
    confirmationBlock: uint256
    actionId: uint256

event ManagerRemoved:
    vaultAddr: indexed(address)
    manager: indexed(address)

event PriceSnapshotAdded:
    legoId: indexed(uint256)
    legoAddr: indexed(address)
    vaultToken: indexed(address)
    success: bool
    caller: address

event YieldPositionUpdated:
    vaultAddr: indexed(address)
    vaultToken: indexed(address)
    caller: address

event PerformanceFeesClaimed:
    vaultAddr: indexed(address)
    amount: uint256
    caller: address

event PendingRegisterVaultTokenOnLegoChange:
    legoId: indexed(uint256)
    asset: indexed(address)
    vaultToken: indexed(address)
    confirmationBlock: uint256
    actionId: uint256

event VaultTokenRegisteredOnLego:
    legoId: indexed(uint256)
    legoAddr: indexed(address)
    asset: indexed(address)
    vaultToken: address

event VaultTokenDeregisteredOnLego:
    legoId: indexed(uint256)
    legoAddr: indexed(address)
    asset: indexed(address)
    vaultToken: address
    caller: address

event PendingMorphoRewardsAddrChange:
    legoId: indexed(uint256)
    rewardsAddr: indexed(address)
    confirmationBlock: uint256
    actionId: uint256

event MorphoRewardsAddrSet:
    legoId: indexed(uint256)
    legoAddr: indexed(address)
    rewardsAddr: indexed(address)

event PendingEulerRewardsAddrChange:
    legoId: indexed(uint256)
    rewardsAddr: indexed(address)
    confirmationBlock: uint256
    actionId: uint256

event EulerRewardsAddrSet:
    legoId: indexed(uint256)
    legoAddr: indexed(address)
    rewardsAddr: indexed(address)

event PendingCompRewardsAddrChange:
    legoId: indexed(uint256)
    rewardsAddr: indexed(address)
    confirmationBlock: uint256
    actionId: uint256

event CompRewardsAddrSet:
    legoId: indexed(uint256)
    legoAddr: indexed(address)
    rewardsAddr: indexed(address)

event LeftoversSwept:
    vaultAddr: indexed(address)
    amount: uint256
    caller: address

# pending config changes
actionType: public(HashMap[uint256, ActionType]) # aid -> type
pendingRedemptionBuffer: public(HashMap[uint256, PendingRedemptionBuffer]) # aid -> config
pendingMinYieldWithdrawAmount: public(HashMap[uint256, PendingMinYieldWithdrawAmount]) # aid -> config
pendingSnapShotPriceConfig: public(HashMap[uint256, PendingSnapShotPriceConfig]) # aid -> config
pendingApprovedVaultToken: public(HashMap[uint256, PendingApprovedVaultToken]) # aid -> config
pendingApprovedVaultTokens: public(HashMap[uint256, PendingApprovedVaultTokens]) # aid -> config
pendingPerformanceFee: public(HashMap[uint256, PendingPerformanceFee]) # aid -> config
pendingDefaultTargetVaultToken: public(HashMap[uint256, PendingDefaultTargetVaultToken]) # aid -> config
pendingMaxDepositAmount: public(HashMap[uint256, PendingMaxDepositAmount]) # aid -> config
pendingIsLeveragedVault: public(HashMap[uint256, PendingIsLeveragedVault]) # aid -> config
pendingCollateralVault: public(HashMap[uint256, PendingCollateralVault]) # aid -> config
pendingLeverageVault: public(HashMap[uint256, PendingLeverageVault]) # aid -> config
pendingSlippages: public(HashMap[uint256, PendingSlippages]) # aid -> config
pendingLevgVaultHelper: public(HashMap[uint256, PendingLevgVaultHelper]) # aid -> config
pendingMaxDebtRatio: public(HashMap[uint256, PendingMaxDebtRatio]) # aid -> config
pendingAddManager: public(HashMap[uint256, PendingAddManager]) # aid -> config
pendingRemoveManager: public(HashMap[uint256, PendingRemoveManager]) # aid -> config
pendingRegisterVaultTokenOnLego: public(HashMap[uint256, PendingRegisterVaultTokenOnLego]) # aid -> config
pendingMorphoRewardsAddr: public(HashMap[uint256, PendingMorphoRewardsAddr]) # aid -> config
pendingEulerRewardsAddr: public(HashMap[uint256, PendingEulerRewardsAddr]) # aid -> config
pendingCompRewardsAddr: public(HashMap[uint256, PendingCompRewardsAddr]) # aid -> config

MAX_VAULT_TOKENS: constant(uint256) = 50


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
def _hasPermission(_caller: address, _isLiteAction: bool) -> bool:
    if gov._canGovern(_caller):
        return True
    if _isLiteAction:
        return staticcall MissionControl(addys._getMissionControlAddr()).canPerformSecurityAction(_caller)
    return False


#####################
# Immediate Actions #
#####################


# can deposit


@external
def setCanDeposit(_vaultAddr: address, _canDeposit: bool):
    assert self._hasPermission(msg.sender, not _canDeposit) # dev: no perms
    extcall VaultRegistry(addys._getVaultRegistryAddr()).setCanDeposit(_vaultAddr, _canDeposit)
    log CanDepositSet(vaultAddr=_vaultAddr, canDeposit=_canDeposit, caller=msg.sender)


# can withdraw


@external
def setCanWithdraw(_vaultAddr: address, _canWithdraw: bool):
    assert self._hasPermission(msg.sender, not _canWithdraw) # dev: no perms
    extcall VaultRegistry(addys._getVaultRegistryAddr()).setCanWithdraw(_vaultAddr, _canWithdraw)
    log CanWithdrawSet(vaultAddr=_vaultAddr, canWithdraw=_canWithdraw, caller=msg.sender)


# vault ops frozen


@external
def setVaultOpsFrozen(_vaultAddr: address, _isFrozen: bool):
    assert self._hasPermission(msg.sender, _isFrozen) # dev: no perms
    extcall VaultRegistry(addys._getVaultRegistryAddr()).setVaultOpsFrozen(_vaultAddr, _isFrozen)
    log VaultOpsFrozenSet(vaultAddr=_vaultAddr, isFrozen=_isFrozen, caller=msg.sender)


# should auto deposit


@external
def setShouldAutoDeposit(_vaultAddr: address, _shouldAutoDeposit: bool):
    assert self._hasPermission(msg.sender, not _shouldAutoDeposit) # dev: no perms
    extcall VaultRegistry(addys._getVaultRegistryAddr()).setShouldAutoDeposit(_vaultAddr, _shouldAutoDeposit)
    log ShouldAutoDepositSet(vaultAddr=_vaultAddr, shouldAutoDeposit=_shouldAutoDeposit, caller=msg.sender)


# add price snapshot


@external
def addPriceSnapshot(_legoId: uint256, _vaultToken: address) -> bool:
    assert self._hasPermission(msg.sender, True) # dev: no perms

    # get lego address from lego book
    legoAddr: address = staticcall Registry(addys._getLegoBookAddr()).getAddr(_legoId)
    assert legoAddr != empty(address) # dev: invalid lego id

    # call addPriceSnapshot on the lego
    result: bool = extcall YieldLego(legoAddr).addPriceSnapshot(_vaultToken)

    log PriceSnapshotAdded(legoId=_legoId, legoAddr=legoAddr, vaultToken=_vaultToken, success=result, caller=msg.sender)
    return result


# deregister vault token on lego


@external
def deregisterVaultTokenOnLego(_legoId: uint256, _asset: address, _vaultToken: address) -> uint256:
    assert self._hasPermission(msg.sender, True) # dev: no perms
    assert _asset != empty(address) # dev: invalid asset
    assert _vaultToken != empty(address) # dev: invalid vault token

    # get lego address from lego book
    legoAddr: address = staticcall Registry(addys._getLegoBookAddr()).getAddr(_legoId)
    assert legoAddr != empty(address) # dev: invalid lego id

    # execute immediately (no timelock for emergency vault token removals)
    extcall YieldLego(legoAddr).deregisterVaultTokenLocally(_asset, _vaultToken)

    log VaultTokenDeregisteredOnLego(legoId=_legoId, legoAddr=legoAddr, asset=_asset, vaultToken=_vaultToken, caller=msg.sender)
    return 0


# update yield position


@external
def updateYieldPosition(_vaultAddr: address, _vaultToken: address):
    assert self._hasPermission(msg.sender, True) # dev: no perms

    vr: address = addys._getVaultRegistryAddr()
    assert staticcall VaultRegistry(vr).isEarnVault(_vaultAddr) # dev: invalid vault addr

    # call updateYieldPosition on the vault
    extcall LevgVault(_vaultAddr).updateYieldPosition(_vaultToken)

    log YieldPositionUpdated(vaultAddr=_vaultAddr, vaultToken=_vaultToken, caller=msg.sender)


# claim performance fees


@external
def claimPerformanceFees(_vaultAddr: address) -> uint256:
    assert self._hasPermission(msg.sender, True) # dev: no perms

    vr: address = addys._getVaultRegistryAddr()
    assert staticcall VaultRegistry(vr).isEarnVault(_vaultAddr) # dev: invalid vault addr

    # call claimPerformanceFees on the vault
    amount: uint256 = extcall LevgVault(_vaultAddr).claimPerformanceFees()

    log PerformanceFeesClaimed(vaultAddr=_vaultAddr, amount=amount, caller=msg.sender)
    return amount


# sweep leftovers


@external
def sweepLeftovers(_vaultAddr: address) -> uint256:
    assert self._hasPermission(msg.sender, True) # dev: no perms

    vr: address = addys._getVaultRegistryAddr()
    assert staticcall VaultRegistry(vr).isEarnVault(_vaultAddr) # dev: invalid vault addr

    amount: uint256 = extcall EarnVault(_vaultAddr).sweepLeftovers()
    log LeftoversSwept(vaultAddr=_vaultAddr, amount=amount, caller=msg.sender)
    return amount


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

    config: ls.SnapShotPriceConfig = ls.SnapShotPriceConfig(
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
def setApprovedVaultToken(_undyVaultAddr: address, _vaultToken: address, _isApproved: bool, _shouldMaxWithdraw: bool) -> uint256:
    assert self._hasPermission(msg.sender, not _isApproved) # dev: no perms

    vr: address = addys._getVaultRegistryAddr()
    assert staticcall VaultRegistry(vr).isEarnVault(_undyVaultAddr) # dev: invalid vault addr
    assert _vaultToken != empty(address) # dev: invalid vault token

    # if disapproving, execute immediately (no timelock for emergency removals)
    if not _isApproved:
        extcall VaultRegistry(vr).setApprovedVaultToken(_undyVaultAddr, _vaultToken, _isApproved, _shouldMaxWithdraw)
        log ApprovedVaultTokenSet(vaultAddr=_undyVaultAddr, vaultToken=_vaultToken, isApproved=_isApproved)
        return 0

    # if approving, use timelock
    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.APPROVED_VAULT_TOKEN
    self.pendingApprovedVaultToken[aid] = PendingApprovedVaultToken(
        vaultAddr=_undyVaultAddr,
        vaultToken=_vaultToken,
        isApproved=_isApproved,
        shouldMaxWithdraw=_shouldMaxWithdraw
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingApprovedVaultTokenChange(
        vaultAddr=_undyVaultAddr,
        vaultToken=_vaultToken,
        isApproved=_isApproved,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


@external
def setApprovedVaultTokens(_undyVaultAddr: address, _vaultTokens: DynArray[address, MAX_VAULT_TOKENS], _isApproved: bool, _shouldMaxWithdraw: bool) -> uint256:
    assert self._hasPermission(msg.sender, not _isApproved) # dev: no perms

    vr: address = addys._getVaultRegistryAddr()
    assert staticcall VaultRegistry(vr).isEarnVault(_undyVaultAddr) # dev: invalid vault addr

    # validate all vault tokens
    assert empty(address) not in _vaultTokens # dev: invalid vault tokens
    assert len(_vaultTokens) != 0 # dev: no vault tokens

    # if disapproving, execute immediately (no timelock for emergency removals)
    if not _isApproved:
        extcall VaultRegistry(vr).setApprovedVaultTokens(_undyVaultAddr, _vaultTokens, _isApproved, _shouldMaxWithdraw)
        log ApprovedVaultTokensSet(vaultAddr=_undyVaultAddr, numTokens=len(_vaultTokens), isApproved=_isApproved)
        return 0

    # if approving, use timelock
    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.APPROVED_VAULT_TOKENS
    self.pendingApprovedVaultTokens[aid] = PendingApprovedVaultTokens(
        vaultAddr=_undyVaultAddr,
        vaultTokens=_vaultTokens,
        isApproved=_isApproved,
        shouldMaxWithdraw=_shouldMaxWithdraw
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingApprovedVaultTokensChange(
        vaultAddr=_undyVaultAddr,
        numTokens=len(_vaultTokens),
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


# is leveraged vault


@external
def setIsLeveragedVault(_vaultAddr: address, _isLeveragedVault: bool) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    vr: address = addys._getVaultRegistryAddr()
    assert staticcall VaultRegistry(vr).isEarnVault(_vaultAddr) # dev: invalid vault addr

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.IS_LEVERAGED_VAULT
    self.pendingIsLeveragedVault[aid] = PendingIsLeveragedVault(
        vaultAddr=_vaultAddr,
        isLeveragedVault=_isLeveragedVault
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingIsLeveragedVaultChange(
        vaultAddr=_vaultAddr,
        isLeveragedVault=_isLeveragedVault,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


# collateral vault


@external
def setCollateralVault(_vaultAddr: address, _vaultToken: address, _legoId: uint256, _ripeVaultId: uint256, _shouldMaxWithdraw: bool) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    vr: address = addys._getVaultRegistryAddr()
    assert staticcall VaultRegistry(vr).isEarnVault(_vaultAddr) # dev: invalid vault addr

    # validate vault token if not empty
    if _vaultToken != empty(address):
        helper: address = staticcall LevgVault(_vaultAddr).levgVaultHelper()
        underlyingAsset: address = staticcall IERC4626(_vaultAddr).asset()
        assert staticcall LevgVaultHelper(helper).isValidVaultToken(underlyingAsset, _vaultToken, _ripeVaultId, _legoId) # dev: invalid collateral vault token

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.COLLATERAL_VAULT
    self.pendingCollateralVault[aid] = PendingCollateralVault(
        vaultAddr=_vaultAddr,
        vaultToken=_vaultToken,
        ripeVaultId=_ripeVaultId,
        legoId=_legoId,
        shouldMaxWithdraw=_shouldMaxWithdraw
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingCollateralVaultChange(
        vaultAddr=_vaultAddr,
        vaultToken=_vaultToken,
        ripeVaultId=_ripeVaultId,
        legoId=_legoId,
        shouldMaxWithdraw=_shouldMaxWithdraw,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


# leverage vault


@external
def setLeverageVault(_vaultAddr: address, _vaultToken: address, _legoId: uint256, _ripeVaultId: uint256, _shouldMaxWithdraw: bool) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    vr: address = addys._getVaultRegistryAddr()
    assert staticcall VaultRegistry(addys._getVaultRegistryAddr()).isEarnVault(_vaultAddr) # dev: invalid vault addr

    # validate vault token
    helper: address = staticcall LevgVault(_vaultAddr).levgVaultHelper()
    usdc: address = staticcall LevgVault(_vaultAddr).USDC()
    assert staticcall LevgVaultHelper(helper).isValidVaultToken(usdc, _vaultToken, _ripeVaultId, _legoId) # dev: invalid leverage vault token

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.LEVERAGE_VAULT
    self.pendingLeverageVault[aid] = PendingLeverageVault(
        vaultAddr=_vaultAddr,
        vaultToken=_vaultToken,
        legoId=_legoId,
        ripeVaultId=_ripeVaultId,
        shouldMaxWithdraw=_shouldMaxWithdraw
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingLeverageVaultChange(
        vaultAddr=_vaultAddr,
        vaultToken=_vaultToken,
        legoId=_legoId,
        ripeVaultId=_ripeVaultId,
        shouldMaxWithdraw=_shouldMaxWithdraw,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


# slippages


@external
def setSlippagesAllowed(_vaultAddr: address, _usdcSlippage: uint256, _greenSlippage: uint256) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    assert staticcall VaultRegistry(addys._getVaultRegistryAddr()).isEarnVault(_vaultAddr) # dev: invalid vault addr
    assert _usdcSlippage <= 10_00 # dev: usdc slippage too high (max 10%)
    assert _greenSlippage <= 10_00 # dev: green slippage too high (max 10%)

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.SLIPPAGES
    self.pendingSlippages[aid] = PendingSlippages(
        vaultAddr=_vaultAddr,
        usdcSlippage=_usdcSlippage,
        greenSlippage=_greenSlippage
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingSlippagesChange(
        vaultAddr=_vaultAddr,
        usdcSlippage=_usdcSlippage,
        greenSlippage=_greenSlippage,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


# levg vault helper


@external
def setLevgVaultHelper(_vaultAddr: address, _levgVaultHelper: address) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    assert staticcall VaultRegistry(addys._getVaultRegistryAddr()).isEarnVault(_vaultAddr) # dev: invalid vault addr
    assert _levgVaultHelper != empty(address) # dev: invalid helper address

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.LEVG_VAULT_HELPER
    self.pendingLevgVaultHelper[aid] = PendingLevgVaultHelper(
        vaultAddr=_vaultAddr,
        levgVaultHelper=_levgVaultHelper
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingLevgVaultHelperChange(
        vaultAddr=_vaultAddr,
        levgVaultHelper=_levgVaultHelper,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


# max debt ratio


@external
def setMaxDebtRatio(_vaultAddr: address, _ratio: uint256) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    assert staticcall VaultRegistry(addys._getVaultRegistryAddr()).isEarnVault(_vaultAddr) # dev: invalid vault addr
    assert _ratio <= 100_00 # dev: ratio too high (max 100%)

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.MAX_DEBT_RATIO
    self.pendingMaxDebtRatio[aid] = PendingMaxDebtRatio(
        vaultAddr=_vaultAddr,
        ratio=_ratio
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingMaxDebtRatioChange(
        vaultAddr=_vaultAddr,
        ratio=_ratio,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


# add manager


@external
def addVaultManager(_vaultAddr: address, _manager: address) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    assert staticcall VaultRegistry(addys._getVaultRegistryAddr()).isEarnVault(_vaultAddr) # dev: invalid vault addr

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.ADD_MANAGER
    self.pendingAddManager[aid] = PendingAddManager(
        vaultAddr=_vaultAddr,
        manager=_manager
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingAddManagerChange(
        vaultAddr=_vaultAddr,
        manager=_manager,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


# remove manager


@external
def removeVaultManager(_vaultAddr: address, _manager: address) -> uint256:
    assert self._hasPermission(msg.sender, True) # dev: no perms
    assert staticcall VaultRegistry(addys._getVaultRegistryAddr()).isEarnVault(_vaultAddr) # dev: invalid vault addr

    # execute immediately (no timelock for emergency manager removals)
    extcall LevgVault(_vaultAddr).removeManager(_manager)
    log ManagerRemoved(vaultAddr=_vaultAddr, manager=_manager)
    return 0


# register vault token on lego


@external
def registerVaultTokenOnLego(_legoId: uint256, _asset: address, _vaultToken: address) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    assert _asset != empty(address) # dev: invalid asset
    assert _vaultToken != empty(address) # dev: invalid vault token

    # get lego address from lego book
    legoBook: address = addys._getLegoBookAddr()
    legoAddr: address = staticcall Registry(legoBook).getAddr(_legoId)
    assert legoAddr != empty(address) # dev: invalid lego id

    # validate that the vault token can be registered
    assert staticcall YieldLego(legoAddr).canRegisterVaultToken(_asset, _vaultToken) # dev: cannot register vault token

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.REGISTER_VAULT_TOKEN_ON_LEGO
    self.pendingRegisterVaultTokenOnLego[aid] = PendingRegisterVaultTokenOnLego(
        legoId=_legoId,
        asset=_asset,
        vaultToken=_vaultToken
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingRegisterVaultTokenOnLegoChange(
        legoId=_legoId,
        asset=_asset,
        vaultToken=_vaultToken,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


# set morpho rewards address


@external
def setMorphoRewardsAddr(_legoId: uint256, _rewardsAddr: address) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms

    # get lego address from lego book
    legoBook: address = addys._getLegoBookAddr()
    legoAddr: address = staticcall Registry(legoBook).getAddr(_legoId)
    assert legoAddr != empty(address) # dev: invalid lego id

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.SET_MORPHO_REWARDS_ADDR
    self.pendingMorphoRewardsAddr[aid] = PendingMorphoRewardsAddr(
        legoId=_legoId,
        rewardsAddr=_rewardsAddr
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingMorphoRewardsAddrChange(
        legoId=_legoId,
        rewardsAddr=_rewardsAddr,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


# set euler rewards address


@external
def setEulerRewardsAddr(_legoId: uint256, _rewardsAddr: address) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms

    # get lego address from lego book
    legoBook: address = addys._getLegoBookAddr()
    legoAddr: address = staticcall Registry(legoBook).getAddr(_legoId)
    assert legoAddr != empty(address) # dev: invalid lego id

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.SET_EULER_REWARDS_ADDR
    self.pendingEulerRewardsAddr[aid] = PendingEulerRewardsAddr(
        legoId=_legoId,
        rewardsAddr=_rewardsAddr
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingEulerRewardsAddrChange(
        legoId=_legoId,
        rewardsAddr=_rewardsAddr,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


# set compound rewards address


@external
def setCompRewardsAddr(_legoId: uint256, _rewardsAddr: address) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms

    # get lego address from lego book
    legoBook: address = addys._getLegoBookAddr()
    legoAddr: address = staticcall Registry(legoBook).getAddr(_legoId)
    assert legoAddr != empty(address) # dev: invalid lego id

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.SET_COMP_REWARDS_ADDR
    self.pendingCompRewardsAddr[aid] = PendingCompRewardsAddr(
        legoId=_legoId,
        rewardsAddr=_rewardsAddr
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingCompRewardsAddrChange(
        legoId=_legoId,
        rewardsAddr=_rewardsAddr,
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
        extcall VaultRegistry(vr).setApprovedVaultToken(p.vaultAddr, p.vaultToken, p.isApproved, p.shouldMaxWithdraw)
        log ApprovedVaultTokenSet(vaultAddr=p.vaultAddr, vaultToken=p.vaultToken, isApproved=p.isApproved)

    elif actionType == ActionType.APPROVED_VAULT_TOKENS:
        p: PendingApprovedVaultTokens = self.pendingApprovedVaultTokens[_aid]
        extcall VaultRegistry(vr).setApprovedVaultTokens(p.vaultAddr, p.vaultTokens, p.isApproved, p.shouldMaxWithdraw)
        log ApprovedVaultTokensSet(vaultAddr=p.vaultAddr, numTokens=len(p.vaultTokens), isApproved=p.isApproved)

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

    elif actionType == ActionType.IS_LEVERAGED_VAULT:
        p: PendingIsLeveragedVault = self.pendingIsLeveragedVault[_aid]
        extcall VaultRegistry(vr).setIsLeveragedVault(p.vaultAddr, p.isLeveragedVault)
        log IsLeveragedVaultSet(vaultAddr=p.vaultAddr, isLeveragedVault=p.isLeveragedVault)

    elif actionType == ActionType.COLLATERAL_VAULT:
        p: PendingCollateralVault = self.pendingCollateralVault[_aid]
        extcall LevgVault(p.vaultAddr).setCollateralVault(p.vaultToken, p.legoId, p.ripeVaultId, p.shouldMaxWithdraw)
        log CollateralVaultSet(vaultAddr=p.vaultAddr, vaultToken=p.vaultToken, ripeVaultId=p.ripeVaultId, legoId=p.legoId)

    elif actionType == ActionType.LEVERAGE_VAULT:
        p: PendingLeverageVault = self.pendingLeverageVault[_aid]
        extcall LevgVault(p.vaultAddr).setLeverageVault(p.vaultToken, p.legoId, p.ripeVaultId, p.shouldMaxWithdraw)
        log LeverageVaultSet(vaultAddr=p.vaultAddr, vaultToken=p.vaultToken, legoId=p.legoId, ripeVaultId=p.ripeVaultId)

    elif actionType == ActionType.SLIPPAGES:
        p: PendingSlippages = self.pendingSlippages[_aid]
        extcall LevgVault(p.vaultAddr).setSlippagesAllowed(p.usdcSlippage, p.greenSlippage)
        log SlippagesSet(vaultAddr=p.vaultAddr, usdcSlippage=p.usdcSlippage, greenSlippage=p.greenSlippage)

    elif actionType == ActionType.LEVG_VAULT_HELPER:
        p: PendingLevgVaultHelper = self.pendingLevgVaultHelper[_aid]
        extcall LevgVault(p.vaultAddr).setLevgVaultHelper(p.levgVaultHelper)
        log LevgVaultHelperSet(vaultAddr=p.vaultAddr, levgVaultHelper=p.levgVaultHelper)

    elif actionType == ActionType.MAX_DEBT_RATIO:
        p: PendingMaxDebtRatio = self.pendingMaxDebtRatio[_aid]
        extcall LevgVault(p.vaultAddr).setMaxDebtRatio(p.ratio)
        log MaxDebtRatioSet(vaultAddr=p.vaultAddr, ratio=p.ratio)

    elif actionType == ActionType.ADD_MANAGER:
        p: PendingAddManager = self.pendingAddManager[_aid]
        extcall LevgVault(p.vaultAddr).addManager(p.manager)
        log ManagerAdded(vaultAddr=p.vaultAddr, manager=p.manager)

    elif actionType == ActionType.REMOVE_MANAGER:
        p: PendingRemoveManager = self.pendingRemoveManager[_aid]
        extcall LevgVault(p.vaultAddr).removeManager(p.manager)
        log ManagerRemoved(vaultAddr=p.vaultAddr, manager=p.manager)

    elif actionType == ActionType.REGISTER_VAULT_TOKEN_ON_LEGO:
        p: PendingRegisterVaultTokenOnLego = self.pendingRegisterVaultTokenOnLego[_aid]
        # get lego address from lego book
        legoBook: address = addys._getLegoBookAddr()
        legoAddr: address = staticcall Registry(legoBook).getAddr(p.legoId)
        # register vault token on the lego
        extcall YieldLego(legoAddr).registerVaultTokenLocally(p.asset, p.vaultToken)
        log VaultTokenRegisteredOnLego(legoId=p.legoId, legoAddr=legoAddr, asset=p.asset, vaultToken=p.vaultToken)

    elif actionType == ActionType.SET_MORPHO_REWARDS_ADDR:
        p: PendingMorphoRewardsAddr = self.pendingMorphoRewardsAddr[_aid]
        # get lego address from lego book
        legoBook: address = addys._getLegoBookAddr()
        legoAddr: address = staticcall Registry(legoBook).getAddr(p.legoId)
        # set rewards address on the lego
        extcall YieldLego(legoAddr).setMorphoRewardsAddr(p.rewardsAddr)
        log MorphoRewardsAddrSet(legoId=p.legoId, legoAddr=legoAddr, rewardsAddr=p.rewardsAddr)

    elif actionType == ActionType.SET_EULER_REWARDS_ADDR:
        p: PendingEulerRewardsAddr = self.pendingEulerRewardsAddr[_aid]
        # get lego address from lego book
        legoBook: address = addys._getLegoBookAddr()
        legoAddr: address = staticcall Registry(legoBook).getAddr(p.legoId)
        # set rewards address on the lego
        extcall YieldLego(legoAddr).setEulerRewardsAddr(p.rewardsAddr)
        log EulerRewardsAddrSet(legoId=p.legoId, legoAddr=legoAddr, rewardsAddr=p.rewardsAddr)

    elif actionType == ActionType.SET_COMP_REWARDS_ADDR:
        p: PendingCompRewardsAddr = self.pendingCompRewardsAddr[_aid]
        # get lego address from lego book
        legoBook: address = addys._getLegoBookAddr()
        legoAddr: address = staticcall Registry(legoBook).getAddr(p.legoId)
        # set rewards address on the lego
        extcall YieldLego(legoAddr).setCompRewardsAddr(p.rewardsAddr)
        log CompRewardsAddrSet(legoId=p.legoId, legoAddr=legoAddr, rewardsAddr=p.rewardsAddr)

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
