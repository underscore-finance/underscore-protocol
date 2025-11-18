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
from interfaces import YieldLego as YieldLego
from ethereum.ercs import IERC4626

interface Ledger:
    def vaultTokens(_vaultToken: address) -> VaultToken: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

interface LevgVault:
    def isLeveragedVault() -> bool: view

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
    isLeveragedVault: bool

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
    vaultAsset: address
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

event IsLeveragedVaultSet:
    vaultAddr: indexed(address)
    isLeveragedVault: bool

event ApprovedVaultTokenSet:
    undyVaultAddr: indexed(address)
    underlyingAsset: indexed(address)
    vaultToken: indexed(address)
    isApproved: bool

event VaultTokenAdded:
    undyVaultAddr: indexed(address)
    underlyingAsset: indexed(address)
    vaultToken: indexed(address)

event VaultTokenRemoved:
    undyVaultAddr: indexed(address)
    underlyingAsset: indexed(address)
    vaultToken: indexed(address)

event AssetVaultTokenAdded:
    asset: indexed(address)
    vaultToken: indexed(address)

event AssetVaultTokenRemoved:
    asset: indexed(address)
    vaultToken: indexed(address)

# config
vaultConfigs: public(HashMap[address, VaultConfig]) # vault addr -> vault config
isApprovedVaultToken: public(HashMap[address, HashMap[address, bool]]) # vault addr -> vault token -> is approved

# iterable approved vault tokens per vault
approvedVaultTokens: public(HashMap[address, HashMap[uint256, address]]) # vault addr -> index -> vault token
indexOfApprovedVaultToken: public(HashMap[address, HashMap[address, uint256]]) # vault addr -> vault token -> index
numApprovedVaultTokens: public(HashMap[address, uint256]) # vault addr -> count

# iterable vault tokens per underlying asset (combined across all vaults)
assetVaultTokens: public(HashMap[address, HashMap[uint256, address]]) # underlying asset -> index -> vault token
indexOfAssetVaultToken: public(HashMap[address, HashMap[address, uint256]]) # underlying asset -> vault token -> index
numAssetVaultTokens: public(HashMap[address, uint256]) # underlying asset -> count
assetVaultTokenRefCount: public(HashMap[address, HashMap[address, uint256]]) # underlying asset -> vault token -> ref count

MAX_VAULT_TOKENS: constant(uint256) = 50
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


# gov access


@view
@internal
def _canPerformAction(_caller: address) -> bool:
    return gov._canGovern(_caller) and not deptBasics.isPaused


# vault helpers


@view
@external
def isEarnVault(_undyVaultAddr: address) -> bool:
    return self._isEarnVault(_undyVaultAddr)


@view
@internal
def _isEarnVault(_undyVaultAddr: address) -> bool:
    return registry._isValidAddr(_undyVaultAddr) or self._hasConfig(_undyVaultAddr)


@view
@external
def isLeveragedVault(_undyVaultAddr: address) -> bool:
    return self.vaultConfigs[_undyVaultAddr].isLeveragedVault


@view
@external
def isBasicEarnVault(_undyVaultAddr: address) -> bool:
    config: VaultConfig = self.vaultConfigs[_undyVaultAddr]
    hasConfig: bool = self._checkConfig(config)
    if not hasConfig:
        return False
    return not config.isLeveragedVault


# has config


@view
@external
def hasConfig(_undyVaultAddr: address) -> bool:
    return self._hasConfig(_undyVaultAddr)


@view
@internal
def _hasConfig(_undyVaultAddr: address) -> bool:
    return self._checkConfig(self.vaultConfigs[_undyVaultAddr])


@view
@internal
def _checkConfig(_config: VaultConfig) -> bool:
    return _config.redemptionBuffer != 0 or _config.minYieldWithdrawAmount != 0 or _config.performanceFee != 0 or _config.defaultTargetVaultToken != empty(address) or _config.shouldAutoDeposit or _config.canDeposit or _config.canWithdraw


############
# Registry #
############


@external
def startAddNewAddressToRegistry(_undyVaultAddr: address, _description: String[64]) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return registry._startAddNewAddressToRegistry(_undyVaultAddr, _description)


@external
def confirmNewAddressToRegistry(
    _undyVaultAddr: address,
    _isLeveragedVault: bool = False,
    _approvedVaultTokens: DynArray[address, MAX_VAULT_TOKENS] = [],
    _maxDepositAmount: uint256 = max_value(uint256),
    _minYieldWithdrawAmount: uint256 = 0,
    _performanceFee: uint256 = 20_00, # 20.00%
    _defaultTargetVaultToken: address = empty(address),
    _shouldAutoDeposit: bool = True,
    _canDeposit: bool = False,
    _canWithdraw: bool = True,
    _isVaultOpsFrozen: bool = False,
    _redemptionBuffer: uint256 = 2_00, # 2.00%
) -> uint256:
    assert self._canPerformAction(msg.sender) # dev: no perms
    regId: uint256 = registry._confirmNewAddressToRegistry(_undyVaultAddr)
    if regId != 0:
        self._initializeVaultConfig(
            _undyVaultAddr,
            _isLeveragedVault,
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
def cancelNewAddressToRegistry(_undyVaultAddr: address) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return registry._cancelNewAddressToRegistry(_undyVaultAddr)


# set vault config


@internal
def _initializeVaultConfig(
    _undyVaultAddr: address,
    _isLeveragedVault: bool,
    _maxDepositAmount: uint256,
    _minYieldWithdrawAmount: uint256,
    _approvedVaultTokens: DynArray[address, MAX_VAULT_TOKENS],
    _performanceFee: uint256,
    _defaultTargetVaultToken: address,
    _shouldAutoDeposit: bool,
    _canDeposit: bool,
    _canWithdraw: bool,
    _isVaultOpsFrozen: bool,
    _redemptionBuffer: uint256,
):
    assert registry._isValidAddr(_undyVaultAddr) # dev: invalid vault addr

    # validation
    assert self._isValidRedemptionBuffer(_redemptionBuffer) # dev: invalid redemption buffer
    assert self._isValidPerformanceFee(_performanceFee) # dev: invalid performance fee

    # validate leveraged vault
    if _isLeveragedVault:
        assert staticcall LevgVault(_undyVaultAddr).isLeveragedVault() # dev: invalid leveraged vault

    # underlying asset
    underlyingAsset: address = staticcall IERC4626(_undyVaultAddr).asset()
    assert underlyingAsset != empty(address) # dev: invalid underlying asset

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
        isLeveragedVault = _isLeveragedVault,
    )
    self.vaultConfigs[_undyVaultAddr] = config

    # approve vault tokens
    if len(_approvedVaultTokens) != 0:
        for vaultToken: address in _approvedVaultTokens:
            if vaultToken != empty(address):
                self.isApprovedVaultToken[_undyVaultAddr][vaultToken] = True
                self._addApprovedVaultToken(_undyVaultAddr, underlyingAsset, vaultToken)


#################
# Vault Disable #
#################


@external
def startAddressDisableInRegistry(_regId: uint256) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    assert self._canDisableVault(_regId) # dev: cannot disable vault
    return registry._startAddressDisableInRegistry(_regId)


@external
def confirmAddressDisableInRegistry(_regId: uint256) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    assert self._canDisableVault(_regId) # dev: cannot disable vault
    return registry._confirmAddressDisableInRegistry(_regId)


@external
def cancelAddressDisableInRegistry(_regId: uint256) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return registry._cancelAddressDisableInRegistry(_regId)


# validation


@view
@internal
def _canDisableVault(_regId: uint256) -> bool:
    vaultAddr: address = registry._getAddr(_regId)
    return self._hasConfig(vaultAddr)


######################
# Basic Vault Config #
######################


@external
def setCanDeposit(_undyVaultAddr: address, _canDeposit: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert self._hasConfig(_undyVaultAddr) # dev: invalid vault addr

    config: VaultConfig = self.vaultConfigs[_undyVaultAddr]
    config.canDeposit = _canDeposit
    self.vaultConfigs[_undyVaultAddr] = config
    log CanDepositSet(vaultAddr=_undyVaultAddr, canDeposit=_canDeposit)


@external
def setCanWithdraw(_undyVaultAddr: address, _canWithdraw: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert self._hasConfig(_undyVaultAddr) # dev: invalid vault addr

    config: VaultConfig = self.vaultConfigs[_undyVaultAddr]
    config.canWithdraw = _canWithdraw
    self.vaultConfigs[_undyVaultAddr] = config
    log CanWithdrawSet(vaultAddr=_undyVaultAddr, canWithdraw=_canWithdraw)


@external
def setMaxDepositAmount(_undyVaultAddr: address, _maxDepositAmount: uint256):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert self._hasConfig(_undyVaultAddr) # dev: invalid vault addr

    config: VaultConfig = self.vaultConfigs[_undyVaultAddr]
    config.maxDepositAmount = _maxDepositAmount
    self.vaultConfigs[_undyVaultAddr] = config
    log MaxDepositAmountSet(vaultAddr=_undyVaultAddr, maxDepositAmount=_maxDepositAmount)


@external
def setVaultOpsFrozen(_undyVaultAddr: address, _isFrozen: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert self._hasConfig(_undyVaultAddr) # dev: invalid vault addr

    config: VaultConfig = self.vaultConfigs[_undyVaultAddr]
    config.isVaultOpsFrozen = _isFrozen
    self.vaultConfigs[_undyVaultAddr] = config
    log VaultOpsFrozenSet(vaultAddr=_undyVaultAddr, isFrozen=_isFrozen)


@external
def setShouldAutoDeposit(_undyVaultAddr: address, _shouldAutoDeposit: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert self._hasConfig(_undyVaultAddr) # dev: invalid vault addr

    config: VaultConfig = self.vaultConfigs[_undyVaultAddr]
    config.shouldAutoDeposit = _shouldAutoDeposit
    self.vaultConfigs[_undyVaultAddr] = config
    log ShouldAutoDepositSet(vaultAddr=_undyVaultAddr, shouldAutoDeposit=_shouldAutoDeposit)


@external
def setMinYieldWithdrawAmount(_undyVaultAddr: address, _amount: uint256):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert self._hasConfig(_undyVaultAddr) # dev: invalid vault addr

    config: VaultConfig = self.vaultConfigs[_undyVaultAddr]
    config.minYieldWithdrawAmount = _amount
    self.vaultConfigs[_undyVaultAddr] = config
    log MinYieldWithdrawAmountSet(vaultAddr=_undyVaultAddr, amount=_amount)


@external
def setIsLeveragedVault(_undyVaultAddr: address, _isLeveragedVault: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert self._hasConfig(_undyVaultAddr) # dev: invalid vault addr

    # validate leveraged vault
    if _isLeveragedVault:
        assert staticcall LevgVault(_undyVaultAddr).isLeveragedVault() # dev: invalid leveraged vault

    config: VaultConfig = self.vaultConfigs[_undyVaultAddr]
    config.isLeveragedVault = _isLeveragedVault
    self.vaultConfigs[_undyVaultAddr] = config
    log IsLeveragedVaultSet(vaultAddr=_undyVaultAddr, isLeveragedVault=_isLeveragedVault)


######################
# Target Vault Token #
######################


@external
def setDefaultTargetVaultToken(_undyVaultAddr: address, _targetVaultToken: address):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert self._hasConfig(_undyVaultAddr) # dev: invalid vault addr
    assert self._isValidDefaultTargetVaultToken(_undyVaultAddr, _targetVaultToken) # dev: invalid default target vault token

    config: VaultConfig = self.vaultConfigs[_undyVaultAddr]
    config.defaultTargetVaultToken = _targetVaultToken
    self.vaultConfigs[_undyVaultAddr] = config
    log DefaultTargetVaultTokenSet(vaultAddr=_undyVaultAddr, targetVaultToken=_targetVaultToken)


@view
@external
def isValidDefaultTargetVaultToken(_undyVaultAddr: address, _targetVaultToken: address) -> bool:
    return self._isValidDefaultTargetVaultToken(_undyVaultAddr, _targetVaultToken)


@view
@internal
def _isValidDefaultTargetVaultToken(_undyVaultAddr: address, _targetVaultToken: address) -> bool:
    if _targetVaultToken == empty(address):
        return True
    return self.isApprovedVaultToken[_undyVaultAddr][_targetVaultToken]


###################
# Performance Fee #
###################


@external
def setPerformanceFee(_undyVaultAddr: address, _performanceFee: uint256):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert self._hasConfig(_undyVaultAddr) # dev: invalid vault addr
    assert self._isValidPerformanceFee(_performanceFee) # dev: invalid performance fee

    config: VaultConfig = self.vaultConfigs[_undyVaultAddr]
    config.performanceFee = _performanceFee
    self.vaultConfigs[_undyVaultAddr] = config
    log PerformanceFeeSet(vaultAddr=_undyVaultAddr, performanceFee=_performanceFee)


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
def setRedemptionBuffer(_undyVaultAddr: address, _buffer: uint256):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert self._hasConfig(_undyVaultAddr) # dev: invalid vault addr
    assert self._isValidRedemptionBuffer(_buffer) # dev: invalid redemption buffer

    config: VaultConfig = self.vaultConfigs[_undyVaultAddr]
    config.redemptionBuffer = _buffer
    self.vaultConfigs[_undyVaultAddr] = config
    log RedemptionBufferSet(vaultAddr=_undyVaultAddr, buffer=_buffer)


@view
@external
def isValidRedemptionBuffer(_buffer: uint256) -> bool:
    return self._isValidRedemptionBuffer(_buffer)


@view
@internal
def _isValidRedemptionBuffer(_buffer: uint256) -> bool:
    return _buffer <= 10_00


############################
# Approved Yield Positions #
############################


@external
def setApprovedVaultToken(_undyVaultAddr: address, _vaultToken: address, _isApproved: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    self._setApprovedVaultToken(_undyVaultAddr, _vaultToken, _isApproved)


@external
def setApprovedVaultTokens(_undyVaultAddr: address, _vaultTokens: DynArray[address, MAX_VAULT_TOKENS], _isApproved: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    for vaultToken: address in _vaultTokens:
        self._setApprovedVaultToken(_undyVaultAddr, vaultToken, _isApproved)


# set approved


@internal
def _setApprovedVaultToken(_undyVaultAddr: address, _vaultToken: address, _isApproved: bool):
    assert self._hasConfig(_undyVaultAddr) # dev: invalid vault addr

    underlyingAsset: address = staticcall IERC4626(_undyVaultAddr).asset()
    assert empty(address) not in [_undyVaultAddr, underlyingAsset, _vaultToken] # dev: invalid params

    # set approval status
    self.isApprovedVaultToken[_undyVaultAddr][_vaultToken] = _isApproved

    # update iterable lists
    if _isApproved:
        self._addApprovedVaultToken(_undyVaultAddr, underlyingAsset, _vaultToken)
    else:
        self._removeApprovedVaultToken(_undyVaultAddr, underlyingAsset, _vaultToken)

    log ApprovedVaultTokenSet(undyVaultAddr=_undyVaultAddr, underlyingAsset=underlyingAsset, vaultToken=_vaultToken, isApproved=_isApproved)


# vault management


@internal
def _addApprovedVaultToken(
    _undyVaultAddr: address,
    _underlyingAsset: address,
    _vaultToken: address,
):
    if self.indexOfApprovedVaultToken[_undyVaultAddr][_vaultToken] != 0:
        return # already exists

    if empty(address) in [_undyVaultAddr, _underlyingAsset, _vaultToken]:
        return # invalid params

    # add to per-vault list
    vaultIndex: uint256 = self.numApprovedVaultTokens[_undyVaultAddr]
    if vaultIndex == 0:
        vaultIndex = 1 # not using 0 index

    self.approvedVaultTokens[_undyVaultAddr][vaultIndex] = _vaultToken
    self.indexOfApprovedVaultToken[_undyVaultAddr][_vaultToken] = vaultIndex
    self.numApprovedVaultTokens[_undyVaultAddr] = vaultIndex + 1
    log VaultTokenAdded(undyVaultAddr=_undyVaultAddr, underlyingAsset=_underlyingAsset, vaultToken=_vaultToken)

    # add to per-asset list (if not already there)
    if self.indexOfAssetVaultToken[_underlyingAsset][_vaultToken] == 0:
        assetIndex: uint256 = self.numAssetVaultTokens[_underlyingAsset]
        if assetIndex == 0:
            assetIndex = 1 # not using 0 index

        self.assetVaultTokens[_underlyingAsset][assetIndex] = _vaultToken
        self.indexOfAssetVaultToken[_underlyingAsset][_vaultToken] = assetIndex
        self.numAssetVaultTokens[_underlyingAsset] = assetIndex + 1
        log AssetVaultTokenAdded(asset=_underlyingAsset, vaultToken=_vaultToken)

    # increment reference count
    self.assetVaultTokenRefCount[_underlyingAsset][_vaultToken] += 1


@internal
def _removeApprovedVaultToken(
    _undyVaultAddr: address,
    _underlyingAsset: address,
    _vaultToken: address,
):
    targetIndex: uint256 = self.indexOfApprovedVaultToken[_undyVaultAddr][_vaultToken]
    if targetIndex == 0:
        return # not in list

    if empty(address) in [_undyVaultAddr, _underlyingAsset, _vaultToken]:
        return # invalid params

    # remove from per-vault list using swap-and-pop
    numTokens: uint256 = self.numApprovedVaultTokens[_undyVaultAddr]
    if numTokens == 0:
        return

    lastIndex: uint256 = numTokens - 1
    self.numApprovedVaultTokens[_undyVaultAddr] = lastIndex
    self.indexOfApprovedVaultToken[_undyVaultAddr][_vaultToken] = 0

    # swap and pop: replace removed item with last item
    if targetIndex != lastIndex:
        lastVaultToken: address = self.approvedVaultTokens[_undyVaultAddr][lastIndex]
        self.approvedVaultTokens[_undyVaultAddr][targetIndex] = lastVaultToken
        self.indexOfApprovedVaultToken[_undyVaultAddr][lastVaultToken] = targetIndex

    log VaultTokenRemoved(undyVaultAddr=_undyVaultAddr, underlyingAsset=_underlyingAsset, vaultToken=_vaultToken)

    # decrement reference count and remove from asset list if needed
    refCount: uint256 = self.assetVaultTokenRefCount[_underlyingAsset][_vaultToken]
    if refCount == 0:
        return # already removed

    refCount -= 1
    self.assetVaultTokenRefCount[_underlyingAsset][_vaultToken] = refCount

    # only remove from asset list when no vaults are using it
    if refCount != 0:
        return

    assetTargetIndex: uint256 = self.indexOfAssetVaultToken[_underlyingAsset][_vaultToken]
    if assetTargetIndex == 0:
        return

    numAssetTokens: uint256 = self.numAssetVaultTokens[_underlyingAsset]
    if numAssetTokens == 0:
        return # already removed

    lastAssetIndex: uint256 = numAssetTokens - 1
    self.numAssetVaultTokens[_underlyingAsset] = lastAssetIndex
    self.indexOfAssetVaultToken[_underlyingAsset][_vaultToken] = 0

    # swap and pop for asset list
    if assetTargetIndex != lastAssetIndex:
        lastAssetVaultToken: address = self.assetVaultTokens[_underlyingAsset][lastAssetIndex]
        self.assetVaultTokens[_underlyingAsset][assetTargetIndex] = lastAssetVaultToken
        self.indexOfAssetVaultToken[_underlyingAsset][lastAssetVaultToken] = assetTargetIndex

    log AssetVaultTokenRemoved(asset=_underlyingAsset, vaultToken=_vaultToken)


# vault token getters


@view
@external
def getApprovedVaultTokens(_undyVaultAddr: address) -> DynArray[address, MAX_VAULT_TOKENS]:
    numTokens: uint256 = self.numApprovedVaultTokens[_undyVaultAddr]
    if numTokens == 0:
        return []

    tokens: DynArray[address, MAX_VAULT_TOKENS] = []
    for i: uint256 in range(1, numTokens, bound=MAX_VAULT_TOKENS):
        vaultToken: address = self.approvedVaultTokens[_undyVaultAddr][i]
        if vaultToken != empty(address) and vaultToken not in tokens:
            tokens.append(vaultToken)
    return tokens


@view
@external
def getAssetVaultTokens(_asset: address) -> DynArray[address, MAX_VAULT_TOKENS]:
    numTokens: uint256 = self.numAssetVaultTokens[_asset]
    if numTokens == 0:
        return []

    tokens: DynArray[address, MAX_VAULT_TOKENS] = []
    for i: uint256 in range(1, numTokens, bound=MAX_VAULT_TOKENS):
        vaultToken: address = self.assetVaultTokens[_asset][i]
        if vaultToken != empty(address) and vaultToken not in tokens:
            tokens.append(vaultToken)
    return tokens


@view
@external
def getNumApprovedVaultTokens(_undyVaultAddr: address) -> uint256:
    numTokens: uint256 = self.numApprovedVaultTokens[_undyVaultAddr]
    if numTokens == 0:
        return 0
    return numTokens - 1


@view
@external
def getNumAssetVaultTokens(_asset: address) -> uint256:
    numTokens: uint256 = self.numAssetVaultTokens[_asset]
    if numTokens == 0:
        return 0
    return numTokens - 1


@view
@external
def isApprovedVaultTokenForAsset(_underlyingAsset: address, _vaultToken: address) -> bool:
    isRegisteredUnderlyingVault: bool = self.indexOfAssetVaultToken[_underlyingAsset][_vaultToken] != 0
    if isRegisteredUnderlyingVault:
        return True
    
    # underscore vault
    isEarnVault: bool = self._isEarnVault(_vaultToken)
    if isEarnVault:
        return True

    # ripe lego -- GREEN / SAVINGS GREEN
    ripeLegoAddr: address = staticcall Registry(addys._getLegoBookAddr()).getAddr(1) # Ripe Lego
    return staticcall YieldLego(ripeLegoAddr).canRegisterVaultToken(_underlyingAsset, _vaultToken)


######################
# Vault Config Views #
######################


@view
@external
def canDeposit(_undyVaultAddr: address) -> bool:
    return self.vaultConfigs[_undyVaultAddr].canDeposit


@view
@external
def canWithdraw(_undyVaultAddr: address) -> bool:
    return self.vaultConfigs[_undyVaultAddr].canWithdraw


@view
@external
def maxDepositAmount(_undyVaultAddr: address) -> uint256:
    return self.vaultConfigs[_undyVaultAddr].maxDepositAmount


@view
@external
def isVaultOpsFrozen(_undyVaultAddr: address) -> bool:
    return self.vaultConfigs[_undyVaultAddr].isVaultOpsFrozen


@view
@external
def redemptionBuffer(_undyVaultAddr: address) -> uint256:
    return self.vaultConfigs[_undyVaultAddr].redemptionBuffer


@view
@external
def minYieldWithdrawAmount(_undyVaultAddr: address) -> uint256:
    return self.vaultConfigs[_undyVaultAddr].minYieldWithdrawAmount


@view
@external
def redemptionConfig(_undyVaultAddr: address) -> (uint256, uint256):
    config: VaultConfig = self.vaultConfigs[_undyVaultAddr]
    return config.redemptionBuffer, config.minYieldWithdrawAmount


@view
@external
def getPerformanceFee(_undyVaultAddr: address) -> uint256:
    return self.vaultConfigs[_undyVaultAddr].performanceFee


@view
@external
def getDefaultTargetVaultToken(_undyVaultAddr: address) -> address:
    return self.vaultConfigs[_undyVaultAddr].defaultTargetVaultToken


@view
@external
def shouldAutoDeposit(_undyVaultAddr: address) -> bool:
    return self.vaultConfigs[_undyVaultAddr].shouldAutoDeposit


@view
@external
def isApprovedVaultTokenByAddr(_undyVaultAddr: address, _vaultToken: address) -> bool:
    return self.isApprovedVaultToken[_undyVaultAddr][_vaultToken]


@view
@external
def checkVaultApprovals(_undyVaultAddr: address, _vaultToken: address) -> bool:
    return self.isApprovedVaultToken[_undyVaultAddr][_vaultToken]


@view
@external
def getVaultConfig(_regId: uint256) -> VaultConfig:
    vaultAddr: address = registry._getAddr(_regId)
    return self.vaultConfigs[vaultAddr]


@view
@external
def getVaultConfigByAddr(_undyVaultAddr: address) -> VaultConfig:
    return self.vaultConfigs[_undyVaultAddr]


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
        vaultAsset = empty(address),
        signer = _signer,
        legoId = _legoId,
        legoAddr = legoAddr,
    )


@view
@external
def getVaultActionDataWithFrozenStatus(_legoId: uint256, _signer: address, _undyVaultAddr: address) -> (VaultActionData, bool):
    return self._getVaultActionDataBundle(_legoId, _signer), self.vaultConfigs[_undyVaultAddr].isVaultOpsFrozen


@view
@external
def getLegoDataFromVaultToken(_vaultToken: address) -> (uint256, address):
    return self._getLegoDataFromVaultToken(_vaultToken)


@view
@internal
def _getLegoDataFromVaultToken(_vaultToken: address) -> (uint256, address):
    data: VaultToken = staticcall Ledger(addys._getLedgerAddr()).vaultTokens(_vaultToken)
    if data.legoId == 0:
        return 0, empty(address)
    return data.legoId, staticcall Registry(addys._getLegoBookAddr()).getAddr(data.legoId)


@view
@external
def getLegoAddrFromVaultToken(_vaultToken: address) -> address:
    return self._getLegoDataFromVaultToken(_vaultToken)[1]


@view
@external
def getDepositConfig(_undyVaultAddr: address) -> (bool, uint256, bool, address):
    config: VaultConfig = self.vaultConfigs[_undyVaultAddr]
    return config.canDeposit, config.maxDepositAmount, config.shouldAutoDeposit, config.defaultTargetVaultToken
