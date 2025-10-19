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

interface Ledger:
    def vaultTokens(_vaultToken: address) -> VaultToken: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

struct VaultConfig:
    canDeposit: bool
    canWithdraw: bool
    maxDepositAmount: uint256
    isVaultOpsFrozen: bool
    redemptionBuffer: uint256
    minYieldWithdrawAmount: uint256
    performanceFee: uint256
    shouldAutoDeposit: bool
    defaultTargetVaultToken: address

struct VaultToken:
    legoId: uint256
    underlyingAsset: address
    decimals: uint256
    isRebasing: bool

struct VaultActionData:
    ledger: address
    missionControl: address
    legoBook: address
    appraiser: address
    vaultRegistry: address
    signer: address
    legoId: uint256
    legoAddr: address

event CanDepositSet:
    vaultAddr: indexed(address)
    canDeposit: bool

event CanWithdrawSet:
    vaultAddr: indexed(address)
    canWithdraw: bool

event MaxDepositAmountSet:
    vaultAddr: indexed(address)
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

event PerformanceFeeSet:
    vaultAddr: indexed(address)
    performanceFee: uint256

event DefaultTargetVaultTokenSet:
    vaultAddr: indexed(address)
    targetVaultToken: indexed(address)

event ShouldAutoDepositSet:
    vaultAddr: indexed(address)
    shouldAutoDeposit: bool

event ApprovedVaultTokenSet:
    vaultAddr: indexed(address)
    vaultToken: indexed(address)
    isApproved: bool

# config
vaultConfigs: public(HashMap[address, VaultConfig]) # vault addr -> vault config
isApprovedVaultToken: public(HashMap[address, HashMap[address, bool]]) # vault addr -> vault token -> is approved

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


# is earn vault


@view
@external
def isEarnVault(_vaultAddr: address) -> bool:
    return registry._isValidAddr(_vaultAddr)


# gov access


@view
@internal
def _canPerformAction(_caller: address) -> bool:
    return gov._canGovern(_caller) and not deptBasics.isPaused


############
# Registry #
############


@external
def startAddNewAddressToRegistry(_vaultAddr: address, _description: String[64]) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return registry._startAddNewAddressToRegistry(_vaultAddr, _description)


@external
def confirmNewAddressToRegistry(
    _vaultAddr: address,
    _approvedVaultTokens: DynArray[address, 25] = [],
    _maxDepositAmount: uint256 = max_value(uint256),
    _minYieldWithdrawAmount: uint256 = 0,
    _performanceFee: uint256 = 20_00, # 20.00%
    _defaultTargetVaultToken: address = empty(address),
    _shouldAutoDeposit: bool = True,
    _canDeposit: bool = True,
    _canWithdraw: bool = True,
    _isVaultOpsFrozen: bool = False,
    _redemptionBuffer: uint256 = 2_00, # 2.00%
) -> uint256:
    assert self._canPerformAction(msg.sender) # dev: no perms
    regId: uint256 = registry._confirmNewAddressToRegistry(_vaultAddr)
    if regId != 0:
        self._initializeVaultConfig(
            _vaultAddr,
            _maxDepositAmount,
            _minYieldWithdrawAmount,
            _approvedVaultTokens,
            _performanceFee,
            _defaultTargetVaultToken,
            _shouldAutoDeposit,
            _canDeposit,
            _canWithdraw,
            _isVaultOpsFrozen,
            _redemptionBuffer,
        )
    return regId


@external
def cancelNewAddressToRegistry(_vaultAddr: address) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return registry._cancelNewAddressToRegistry(_vaultAddr)


# set vault config


@internal
def _initializeVaultConfig(
    _vaultAddr: address,
    _maxDepositAmount: uint256,
    _minYieldWithdrawAmount: uint256,
    _approvedVaultTokens: DynArray[address, 25],
    _performanceFee: uint256,
    _defaultTargetVaultToken: address,
    _shouldAutoDeposit: bool,
    _canDeposit: bool,
    _canWithdraw: bool,
    _isVaultOpsFrozen: bool,
    _redemptionBuffer: uint256,
):
    assert registry._isValidAddr(_vaultAddr) # dev: invalid vault addr

    # validation
    assert self._isValidRedemptionBuffer(_redemptionBuffer) # dev: invalid redemption buffer
    assert self._isValidPerformanceFee(_performanceFee) # dev: invalid performance fee

    # target token
    if _defaultTargetVaultToken != empty(address):
        assert _defaultTargetVaultToken in _approvedVaultTokens # dev: invalid target vault token

    config: VaultConfig = VaultConfig(
        canDeposit = _canDeposit,
        canWithdraw = _canWithdraw,
        maxDepositAmount = _maxDepositAmount,
        isVaultOpsFrozen = _isVaultOpsFrozen,
        redemptionBuffer = _redemptionBuffer,
        minYieldWithdrawAmount = _minYieldWithdrawAmount,
        performanceFee = _performanceFee,
        shouldAutoDeposit = _shouldAutoDeposit,
        defaultTargetVaultToken = _defaultTargetVaultToken,
    )
    self.vaultConfigs[_vaultAddr] = config

    # approve vault tokens
    for vaultToken: address in _approvedVaultTokens:
        if vaultToken != empty(address):
            self.isApprovedVaultToken[_vaultAddr][vaultToken] = True


######################
# Basic Vault Config #
######################


@external
def setCanDeposit(_vaultAddr: address, _canDeposit: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert registry._isValidAddr(_vaultAddr) # dev: invalid vault addr

    config: VaultConfig = self.vaultConfigs[_vaultAddr]
    config.canDeposit = _canDeposit
    self.vaultConfigs[_vaultAddr] = config
    log CanDepositSet(vaultAddr=_vaultAddr, canDeposit=_canDeposit)


@external
def setCanWithdraw(_vaultAddr: address, _canWithdraw: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert registry._isValidAddr(_vaultAddr) # dev: invalid vault addr

    config: VaultConfig = self.vaultConfigs[_vaultAddr]
    config.canWithdraw = _canWithdraw
    self.vaultConfigs[_vaultAddr] = config
    log CanWithdrawSet(vaultAddr=_vaultAddr, canWithdraw=_canWithdraw)


@external
def setMaxDepositAmount(_vaultAddr: address, _maxDepositAmount: uint256):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert registry._isValidAddr(_vaultAddr) # dev: invalid vault addr

    config: VaultConfig = self.vaultConfigs[_vaultAddr]
    config.maxDepositAmount = _maxDepositAmount
    self.vaultConfigs[_vaultAddr] = config
    log MaxDepositAmountSet(vaultAddr=_vaultAddr, maxDepositAmount=_maxDepositAmount)


@external
def setVaultOpsFrozen(_vaultAddr: address, _isFrozen: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert registry._isValidAddr(_vaultAddr) # dev: invalid vault addr

    config: VaultConfig = self.vaultConfigs[_vaultAddr]
    config.isVaultOpsFrozen = _isFrozen
    self.vaultConfigs[_vaultAddr] = config
    log VaultOpsFrozenSet(vaultAddr=_vaultAddr, isFrozen=_isFrozen)


@external
def setShouldAutoDeposit(_vaultAddr: address, _shouldAutoDeposit: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert registry._isValidAddr(_vaultAddr) # dev: invalid vault addr

    config: VaultConfig = self.vaultConfigs[_vaultAddr]
    config.shouldAutoDeposit = _shouldAutoDeposit
    self.vaultConfigs[_vaultAddr] = config
    log ShouldAutoDepositSet(vaultAddr=_vaultAddr, shouldAutoDeposit=_shouldAutoDeposit)


@external
def setMinYieldWithdrawAmount(_vaultAddr: address, _amount: uint256):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert registry._isValidAddr(_vaultAddr) # dev: invalid vault addr

    config: VaultConfig = self.vaultConfigs[_vaultAddr]
    config.minYieldWithdrawAmount = _amount
    self.vaultConfigs[_vaultAddr] = config
    log MinYieldWithdrawAmountSet(vaultAddr=_vaultAddr, amount=_amount)


############################
# Approved Yield Positions #
############################


@external
def setApprovedVaultToken(_vaultAddr: address, _vaultToken: address, _isApproved: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert registry._isValidAddr(_vaultAddr) # dev: invalid vault addr
    assert self._isValidVaultToken(_vaultToken) # dev: invalid vault token

    self.isApprovedVaultToken[_vaultAddr][_vaultToken] = _isApproved
    log ApprovedVaultTokenSet(vaultAddr=_vaultAddr, vaultToken=_vaultToken, isApproved=_isApproved)


@view
@external
def isValidVaultToken(_vaultToken: address) -> bool:
    return self._isValidVaultToken(_vaultToken)


@view
@internal
def _isValidVaultToken(_vaultToken: address) -> bool:
    return _vaultToken != empty(address)


######################
# Target Vault Token #
######################


@external
def setDefaultTargetVaultToken(_vaultAddr: address, _targetVaultToken: address):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert registry._isValidAddr(_vaultAddr) # dev: invalid vault addr
    assert self._isValidDefaultTargetVaultToken(_vaultAddr, _targetVaultToken) # dev: invalid default target vault token

    config: VaultConfig = self.vaultConfigs[_vaultAddr]
    config.defaultTargetVaultToken = _targetVaultToken
    self.vaultConfigs[_vaultAddr] = config
    log DefaultTargetVaultTokenSet(vaultAddr=_vaultAddr, targetVaultToken=_targetVaultToken)


@view
@external
def isValidDefaultTargetVaultToken(_vaultAddr: address, _targetVaultToken: address) -> bool:
    return self._isValidDefaultTargetVaultToken(_vaultAddr, _targetVaultToken)


@view
@internal
def _isValidDefaultTargetVaultToken(_vaultAddr: address, _targetVaultToken: address) -> bool:
    if _targetVaultToken == empty(address):
        return True
    return self.isApprovedVaultToken[_vaultAddr][_targetVaultToken]


###################
# Performance Fee #
###################


@external
def setPerformanceFee(_vaultAddr: address, _performanceFee: uint256):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert registry._isValidAddr(_vaultAddr) # dev: invalid vault addr
    assert self._isValidPerformanceFee(_performanceFee) # dev: invalid performance fee

    config: VaultConfig = self.vaultConfigs[_vaultAddr]
    config.performanceFee = _performanceFee
    self.vaultConfigs[_vaultAddr] = config
    log PerformanceFeeSet(vaultAddr=_vaultAddr, performanceFee=_performanceFee)


@view
@external
def isValidPerformanceFee(_performanceFee: uint256) -> bool:
    return self._isValidPerformanceFee(_performanceFee)


@view
@internal
def _isValidPerformanceFee(_performanceFee: uint256) -> bool:
    return _performanceFee <= HUNDRED_PERCENT


#####################
# Redemption Buffer #
#####################


@external
def setRedemptionBuffer(_vaultAddr: address, _buffer: uint256):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert registry._isValidAddr(_vaultAddr) # dev: invalid vault addr
    assert self._isValidRedemptionBuffer(_buffer) # dev: invalid redemption buffer

    config: VaultConfig = self.vaultConfigs[_vaultAddr]
    config.redemptionBuffer = _buffer
    self.vaultConfigs[_vaultAddr] = config
    log RedemptionBufferSet(vaultAddr=_vaultAddr, buffer=_buffer)


@view
@external
def isValidRedemptionBuffer(_buffer: uint256) -> bool:
    return self._isValidRedemptionBuffer(_buffer)


@view
@internal
def _isValidRedemptionBuffer(_buffer: uint256) -> bool:
    return _buffer <= 10_00


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
def getPerformanceFee(_vaultAddr: address) -> uint256:
    return self.vaultConfigs[_vaultAddr].performanceFee


@view
@external
def getDefaultTargetVaultToken(_vaultAddr: address) -> address:
    return self.vaultConfigs[_vaultAddr].defaultTargetVaultToken


@view
@external
def shouldAutoDeposit(_vaultAddr: address) -> bool:
    return self.vaultConfigs[_vaultAddr].shouldAutoDeposit


@view
@external
def isApprovedVaultTokenByAddr(_vaultAddr: address, _vaultToken: address) -> bool:
    return self.isApprovedVaultToken[_vaultAddr][_vaultToken]


@view
@external
def checkVaultApprovals(_vaultAddr: address, _vaultToken: address) -> bool:
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


@view
@external
def getVaultActionDataBundle(_legoId: uint256, _signer: address) -> VaultActionData:
    return self._getVaultActionDataBundle(_legoId, _signer)


@view
@internal
def _getVaultActionDataBundle(_legoId: uint256, _signer: address) -> VaultActionData:
    a: addys.Addys = addys._getAddys()

    legoAddr: address = empty(address)
    if _legoId != 0:
        legoAddr = staticcall Registry(a.legoBook).getAddr(_legoId)

    return VaultActionData(
        ledger = a.ledger,
        missionControl = a.missionControl,
        legoBook = a.legoBook,
        appraiser = a.appraiser,
        vaultRegistry = self,
        signer = _signer,
        legoId = _legoId,
        legoAddr = legoAddr,
    )


@view
@external
def getVaultActionDataWithFrozenStatus(_legoId: uint256, _signer: address, _vaultAddr: address) -> (VaultActionData, bool):
    return self._getVaultActionDataBundle(_legoId, _signer), self.vaultConfigs[_vaultAddr].isVaultOpsFrozen


@view
@external
def getLegoDataFromVaultToken(_vaultToken: address) -> (uint256, address):
    return self._getLegoDataFromVaultToken(_vaultToken)


@view
@internal
def _getLegoDataFromVaultToken(_vaultToken: address) -> (uint256, address):
    a: addys.Addys = addys._getAddys()
    data: VaultToken = staticcall Ledger(a.ledger).vaultTokens(_vaultToken)
    if data.legoId == 0:
        return 0, empty(address)
    return data.legoId, staticcall Registry(a.legoBook).getAddr(data.legoId)


@view
@external
def getLegoAddrFromVaultToken(_vaultToken: address) -> address:
    return self._getLegoDataFromVaultToken(_vaultToken)[1]


@view
@external
def getDepositConfig(_vaultAddr: address) -> (bool, uint256, bool, address):
    config: VaultConfig = self.vaultConfigs[_vaultAddr]
    return config.canDeposit, config.maxDepositAmount, config.shouldAutoDeposit, config.defaultTargetVaultToken


