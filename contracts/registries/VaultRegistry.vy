#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

implements: Department

exports: gov.__interface__
exports: registry.__interface__
exports: addys.__interface__
exports: deptBasics.__interface__

initializes: gov
initializes: registry[gov := gov]
initializes: addys
initializes: deptBasics[addys := addys]

import contracts.modules.LocalGov as gov
import contracts.modules.AddressRegistry as registry
import contracts.modules.Addys as addys
import contracts.modules.DeptBasics as deptBasics

from interfaces import Department

interface EarnVault:
    def updatePerformanceFee(_performanceFee: uint256): nonpayable

interface UndyHq:
    def getAddr(_regId: uint256) -> address: view

struct SnapShotPriceConfig:
    minSnapshotDelay: uint256
    maxNumSnapshots: uint256
    maxUpsideDeviation: uint256
    staleTime: uint256

struct VaultConfig:
    canDeposit: bool
    canWithdraw: bool
    maxDepositAmount: uint256
    isVaultOpsFrozen: bool
    redemptionBuffer: uint256
    minYieldWithdrawAmount: uint256
    targetCollateralizationRatio: uint256
    performanceFee: uint256
    snapShotPriceConfig: SnapShotPriceConfig

event VaultConfigSet:
    vaultAddr: indexed(address)
    canDeposit: bool
    canWithdraw: bool
    maxDepositAmount: uint256

event VaultOpsFrozenSet:
    vaultAddr: indexed(address)
    isFrozen: bool

event RedemptionBufferSet:
    vaultAddr: indexed(address)
    buffer: uint256

event MinYieldWithdrawAmountSet:
    vaultAddr: indexed(address)
    amount: uint256

event TargetCollateralizationRatioSet:
    vaultAddr: indexed(address)
    ratio: uint256

event PerformanceFeeSet:
    vaultAddr: indexed(address)
    performanceFee: uint256

event SnapShotPriceConfigSet:
    vaultAddr: indexed(address)
    minSnapshotDelay: uint256
    maxNumSnapshots: uint256
    maxUpsideDeviation: uint256
    staleTime: uint256

event ApprovedVaultTokenSet:
    vaultAddr: indexed(address)
    vaultToken: indexed(address)
    isApproved: bool

event ApprovedYieldLegoSet:
    vaultAddr: indexed(address)
    legoId: indexed(uint256)
    isApproved: bool

# vault configs
vaultConfigs: public(HashMap[address, VaultConfig]) # vault addr -> vault config
isApprovedVaultToken: public(HashMap[address, HashMap[address, bool]]) # vault addr -> vault token -> is approved
isApprovedYieldLego: public(HashMap[address, HashMap[uint256, bool]]) # vault addr -> lego id -> is approved

ONE_WEEK_SECONDS: constant(uint256) = 60 * 60 * 24 * 7
HUNDRED_PERCENT: constant(uint256) = 100_00


@deploy
def __init__(
    _undyHq: address,
    _tempGov: address,
    _minRegistryTimeLock: uint256,
    _maxRegistryTimeLock: uint256,
):
    gov.__init__(_undyHq, _tempGov, 0, 0, 0)
    registry.__init__(_minRegistryTimeLock, _maxRegistryTimeLock, 0, "VaultRegistry.vy")
    addys.__init__(_undyHq)
    deptBasics.__init__(False, False) # no minting


@view
@external
def isEarnVault(_vaultAddr: address) -> bool:
    return registry._isValidAddr(_vaultAddr)


############
# Registry #
############


@external
def startAddNewAddressToRegistry(_vaultAddr: address, _description: String[64]) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return registry._startAddNewAddressToRegistry(_vaultAddr, _description)


@external
def confirmNewAddressToRegistry(_vaultAddr: address) -> uint256:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return registry._confirmNewAddressToRegistry(_vaultAddr)


@external
def cancelNewAddressToRegistry(_vaultAddr: address) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return registry._cancelNewAddressToRegistry(_vaultAddr)


# gov access


@view
@internal
def _canPerformAction(_caller: address) -> bool:
    return gov._canGovern(_caller) and not deptBasics.isPaused


######################
# Vault Config Views #
######################


@view
@external
def canDeposit(_vaultAddr: address) -> bool:
    return self.vaultConfigs[_vaultAddr].canDeposit


@view
@external
def canWithdraw(_vaultAddr: address) -> bool:
    return self.vaultConfigs[_vaultAddr].canWithdraw


@view
@external
def maxDepositAmount(_vaultAddr: address) -> uint256:
    return self.vaultConfigs[_vaultAddr].maxDepositAmount


@view
@external
def isVaultOpsFrozen(_vaultAddr: address) -> bool:
    return self.vaultConfigs[_vaultAddr].isVaultOpsFrozen


@view
@external
def redemptionBuffer(_vaultAddr: address) -> uint256:
    return self.vaultConfigs[_vaultAddr].redemptionBuffer


@view
@external
def minYieldWithdrawAmount(_vaultAddr: address) -> uint256:
    return self.vaultConfigs[_vaultAddr].minYieldWithdrawAmount


@view
@external
def redemptionConfig(_vaultAddr: address) -> (uint256, uint256):
    config: VaultConfig = self.vaultConfigs[_vaultAddr]
    return config.redemptionBuffer, config.minYieldWithdrawAmount


@view
@external
def targetCollateralizationRatio(_vaultAddr: address) -> uint256:
    return self.vaultConfigs[_vaultAddr].targetCollateralizationRatio


@view
@external
def getPerformanceFee(_vaultAddr: address) -> uint256:
    return self.vaultConfigs[_vaultAddr].performanceFee


@view
@external
def snapShotPriceConfig(_vaultAddr: address) -> SnapShotPriceConfig:
    return self.vaultConfigs[_vaultAddr].snapShotPriceConfig


@view
@external
def isApprovedVaultTokenByAddr(_vaultAddr: address, _vaultToken: address) -> bool:
    return self.isApprovedVaultToken[_vaultAddr][_vaultToken]


@view
@external
def isApprovedYieldLegoByAddr(_vaultAddr: address, _legoId: uint256) -> bool:
    return self.isApprovedYieldLego[_vaultAddr][_legoId]


@view
@external
def checkVaultApprovals(_vaultAddr: address, _legoId: uint256, _vaultToken: address) -> bool:
    if not self.isApprovedYieldLego[_vaultAddr][_legoId]:
        return False
    return self.isApprovedVaultToken[_vaultAddr][_vaultToken]


@view
@external
def getVaultConfig(_regId: uint256) -> VaultConfig:
    vaultAddr: address = registry._getAddr(_regId)
    return self.vaultConfigs[vaultAddr]


@view
@external
def getVaultConfigByAddr(_vaultAddr: address) -> VaultConfig:
    return self.vaultConfigs[_vaultAddr]


################
# Vault Config #
################


@external
def setCanDeposit(_vaultAddr: address, _canDeposit: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert registry._isValidAddr(_vaultAddr) # dev: invalid vault addr
    config: VaultConfig = self.vaultConfigs[_vaultAddr]
    assert _canDeposit != config.canDeposit # dev: nothing to change
    config.canDeposit = _canDeposit
    self.vaultConfigs[_vaultAddr] = config
    log VaultConfigSet(vaultAddr=_vaultAddr, canDeposit=config.canDeposit, canWithdraw=config.canWithdraw, maxDepositAmount=config.maxDepositAmount)


@external
def setCanWithdraw(_vaultAddr: address, _canWithdraw: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert registry._isValidAddr(_vaultAddr) # dev: invalid vault addr
    config: VaultConfig = self.vaultConfigs[_vaultAddr]
    assert _canWithdraw != config.canWithdraw # dev: nothing to change
    config.canWithdraw = _canWithdraw
    self.vaultConfigs[_vaultAddr] = config
    log VaultConfigSet(vaultAddr=_vaultAddr, canDeposit=config.canDeposit, canWithdraw=config.canWithdraw, maxDepositAmount=config.maxDepositAmount)


@external
def setMaxDepositAmount(_vaultAddr: address, _maxDepositAmount: uint256):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert registry._isValidAddr(_vaultAddr) # dev: invalid vault addr
    config: VaultConfig = self.vaultConfigs[_vaultAddr]
    assert _maxDepositAmount != config.maxDepositAmount # dev: nothing to change
    config.maxDepositAmount = _maxDepositAmount
    self.vaultConfigs[_vaultAddr] = config
    log VaultConfigSet(vaultAddr=_vaultAddr, canDeposit=config.canDeposit, canWithdraw=config.canWithdraw, maxDepositAmount=config.maxDepositAmount)


@external
def setVaultOpsFrozen(_vaultAddr: address, _isFrozen: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert registry._isValidAddr(_vaultAddr) # dev: invalid vault addr
    config: VaultConfig = self.vaultConfigs[_vaultAddr]
    assert _isFrozen != config.isVaultOpsFrozen # dev: nothing to change
    config.isVaultOpsFrozen = _isFrozen
    self.vaultConfigs[_vaultAddr] = config
    log VaultOpsFrozenSet(vaultAddr=_vaultAddr, isFrozen=_isFrozen)


@external
def setRedemptionBuffer(_vaultAddr: address, _buffer: uint256):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert registry._isValidAddr(_vaultAddr) # dev: invalid vault addr
    assert _buffer <= 10_00 # dev: buffer too high (max 10%)
    config: VaultConfig = self.vaultConfigs[_vaultAddr]
    config.redemptionBuffer = _buffer
    self.vaultConfigs[_vaultAddr] = config
    log RedemptionBufferSet(vaultAddr=_vaultAddr, buffer=_buffer)


@external
def setMinYieldWithdrawAmount(_vaultAddr: address, _amount: uint256):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert registry._isValidAddr(_vaultAddr) # dev: invalid vault addr
    config: VaultConfig = self.vaultConfigs[_vaultAddr]
    config.minYieldWithdrawAmount = _amount
    self.vaultConfigs[_vaultAddr] = config
    log MinYieldWithdrawAmountSet(vaultAddr=_vaultAddr, amount=_amount)


@external
def setTargetCollateralizationRatio(_vaultAddr: address, _ratio: uint256):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert registry._isValidAddr(_vaultAddr) # dev: invalid vault addr
    assert _ratio >= 100_00 # dev: ratio must be >= 100%
    assert _ratio <= 500_00 # dev: ratio too high (max 500%)
    config: VaultConfig = self.vaultConfigs[_vaultAddr]
    config.targetCollateralizationRatio = _ratio
    self.vaultConfigs[_vaultAddr] = config
    log TargetCollateralizationRatioSet(vaultAddr=_vaultAddr, ratio=_ratio)


@external
def setPerformanceFee(_vaultAddr: address, _performanceFee: uint256):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert registry._isValidAddr(_vaultAddr) # dev: invalid vault addr
    assert _performanceFee <= HUNDRED_PERCENT # dev: performance fee too high (max 100%)
    config: VaultConfig = self.vaultConfigs[_vaultAddr]
    config.performanceFee = _performanceFee
    self.vaultConfigs[_vaultAddr] = config
    extcall EarnVault(_vaultAddr).updatePerformanceFee(_performanceFee)
    log PerformanceFeeSet(vaultAddr=_vaultAddr, performanceFee=_performanceFee)


@external
def setSnapShotPriceConfig(_vaultAddr: address, _config: SnapShotPriceConfig):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert registry._isValidAddr(_vaultAddr) # dev: invalid vault addr
    assert self._isValidPriceConfig(_config) # dev: invalid config
    vaultConfig: VaultConfig = self.vaultConfigs[_vaultAddr]
    vaultConfig.snapShotPriceConfig = _config
    self.vaultConfigs[_vaultAddr] = vaultConfig
    log SnapShotPriceConfigSet(vaultAddr=_vaultAddr, minSnapshotDelay=_config.minSnapshotDelay, maxNumSnapshots=_config.maxNumSnapshots, maxUpsideDeviation=_config.maxUpsideDeviation, staleTime=_config.staleTime)


@external
def setApprovedVaultToken(_vaultAddr: address, _vaultToken: address, _isApproved: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert registry._isValidAddr(_vaultAddr) # dev: invalid vault addr
    assert _vaultToken != empty(address) # dev: invalid vault token
    assert _isApproved != self.isApprovedVaultToken[_vaultAddr][_vaultToken] # dev: nothing to change
    self.isApprovedVaultToken[_vaultAddr][_vaultToken] = _isApproved
    log ApprovedVaultTokenSet(vaultAddr=_vaultAddr, vaultToken=_vaultToken, isApproved=_isApproved)


@external
def setApprovedYieldLego(_vaultAddr: address, _legoId: uint256, _isApproved: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert registry._isValidAddr(_vaultAddr) # dev: invalid vault addr
    assert _legoId != 0 # dev: invalid lego id
    assert _isApproved != self.isApprovedYieldLego[_vaultAddr][_legoId] # dev: nothing to change
    self.isApprovedYieldLego[_vaultAddr][_legoId] = _isApproved
    log ApprovedYieldLegoSet(vaultAddr=_vaultAddr, legoId=_legoId, isApproved=_isApproved)


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
    _targetCollateralizationRatio: uint256 = 0,
    _performanceFee: uint256 = 20_00, # 20.00%
):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms

    # validation
    assert registry._isValidAddr(_vaultAddr) or registry.pendingNewAddr[_vaultAddr].confirmBlock != 0 # dev: invalid vault addr
    assert self._isValidPriceConfig(_snapShotPriceConfig) # dev: invalid price config
    assert _redemptionBuffer <= 10_00 # dev: buffer too high (max 10%)
    assert _performanceFee <= HUNDRED_PERCENT # dev: performance fee too high (max 100%)
    if _targetCollateralizationRatio != 0:
        assert _targetCollateralizationRatio >= 100_00 # dev: ratio must be >= 100%
        assert _targetCollateralizationRatio <= 500_00 # dev: ratio too high (max 500%)

    # set main vault config
    config: VaultConfig = VaultConfig(
        canDeposit = _canDeposit,
        canWithdraw = _canWithdraw,
        maxDepositAmount = _maxDepositAmount,
        isVaultOpsFrozen = False,
        redemptionBuffer = _redemptionBuffer,
        minYieldWithdrawAmount = _minYieldWithdrawAmount,
        targetCollateralizationRatio = _targetCollateralizationRatio,
        performanceFee = _performanceFee,
        snapShotPriceConfig = _snapShotPriceConfig,
    )
    self.vaultConfigs[_vaultAddr] = config

    # approve vault tokens
    for vaultToken: address in _approvedVaultTokens:
        if vaultToken != empty(address):
            self.isApprovedVaultToken[_vaultAddr][vaultToken] = True
            log ApprovedVaultTokenSet(vaultAddr=_vaultAddr, vaultToken=vaultToken, isApproved=True)

    # approve yield legos
    for legoId: uint256 in _approvedYieldLegos:
        if legoId != 0:
            self.isApprovedYieldLego[_vaultAddr][legoId] = True
            log ApprovedYieldLegoSet(vaultAddr=_vaultAddr, legoId=legoId, isApproved=True)

    # log config events
    log VaultConfigSet(vaultAddr=_vaultAddr, canDeposit=_canDeposit, canWithdraw=_canWithdraw, maxDepositAmount=_maxDepositAmount)
    log RedemptionBufferSet(vaultAddr=_vaultAddr, buffer=_redemptionBuffer)
    log MinYieldWithdrawAmountSet(vaultAddr=_vaultAddr, amount=_minYieldWithdrawAmount)
    if _targetCollateralizationRatio != 0:
        log TargetCollateralizationRatioSet(vaultAddr=_vaultAddr, ratio=_targetCollateralizationRatio)
    if _performanceFee != 0:
        log PerformanceFeeSet(vaultAddr=_vaultAddr, performanceFee=_performanceFee)
    log SnapShotPriceConfigSet(vaultAddr=_vaultAddr, minSnapshotDelay=_snapShotPriceConfig.minSnapshotDelay, maxNumSnapshots=_snapShotPriceConfig.maxNumSnapshots, maxUpsideDeviation=_snapShotPriceConfig.maxUpsideDeviation, staleTime=_snapShotPriceConfig.staleTime)


# validation on snap shot price config


@view
@external
def isValidPriceConfig(_config: SnapShotPriceConfig) -> bool:
    return self._isValidPriceConfig(_config)


@view
@internal
def _isValidPriceConfig(_config: SnapShotPriceConfig) -> bool:
    if _config.minSnapshotDelay > ONE_WEEK_SECONDS:
        return False
    if _config.maxNumSnapshots == 0 or _config.maxNumSnapshots > 25:
        return False
    if _config.maxUpsideDeviation > HUNDRED_PERCENT:
        return False
    return _config.staleTime < ONE_WEEK_SECONDS
