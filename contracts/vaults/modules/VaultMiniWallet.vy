#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3
# pragma optimize codesize

from interfaces import YieldLego as YieldLego
from interfaces import Wallet as wi
from interfaces import LegoPartner as Lego
from interfaces import WalletStructs as ws

from ethereum.ercs import IERC20
from ethereum.ercs import IERC20Detailed

interface MissionControl:
    def canPerformSecurityAction(_addr: address) -> bool: view
    def isLockedSigner(_signer: address) -> bool: view

interface Ledger:
    def vaultTokens(_vaultToken: address) -> VaultToken: view

interface Switchboard:
    def isSwitchboardAddr(_addr: address) -> bool: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

struct LocalVaultTokenData:
    legoId: uint256
    isRebasing: bool
    vaultTokenDecimals: uint256
    avgPricePerShare: uint256

struct SnapShotData:
    lastSnapShot: SingleSnapShot
    nextIndex: uint256

struct SingleSnapShot:
    totalSupply: uint256
    pricePerShare: uint256
    lastUpdate: uint256

struct SnapShotPriceConfig:
    minSnapshotDelay: uint256
    maxNumSnapshots: uint256
    maxUpsideDeviation: uint256
    staleTime: uint256

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

event EarnVaultAction:
    op: uint8 
    asset1: indexed(address)
    asset2: indexed(address)
    amount1: uint256
    amount2: uint256
    usdValue: uint256
    legoId: uint256
    signer: indexed(address)

event PricePerShareSnapShotAdded:
    vaultToken: indexed(address)
    totalSupply: uint256
    pricePerShare: uint256

event PriceConfigSet:
    minSnapshotDelay: uint256
    maxNumSnapshots: uint256
    maxUpsideDeviation: uint256
    staleTime: uint256

event RedemptionBufferSet:
    buffer: uint256

event VaultOpsFrozenSet:
    isFrozen: bool
    caller: indexed(address)

event ApprovedVaultTokenSet:
    vaultToken: indexed(address)
    isApproved: bool

event ApprovedYieldLegoSet:
    legoId: indexed(uint256)
    isApproved: bool

# asset data
assetData: public(HashMap[address, LocalVaultTokenData]) # asset -> data
assets: public(HashMap[uint256, address]) # index -> asset
indexOfAsset: public(HashMap[address, uint256]) # asset -> index
numAssets: public(uint256) # num assets

# price snap shot data
snapShotData: public(HashMap[address, SnapShotData]) # asset -> data
snapShots: public(HashMap[address, HashMap[uint256, SingleSnapShot]]) # asset -> index -> snapshot
snapShotPriceConfig: public(SnapShotPriceConfig)

# yield config
isApprovedVaultToken: public(HashMap[address, bool]) # asset -> is approved
isApprovedYieldLego: public(HashMap[uint256, bool]) # lego id -> is approved

# other config
isVaultOpsFrozen: public(bool)
redemptionBuffer: public(uint256)

# managers
managers: public(HashMap[uint256, address]) # index -> manager
indexOfManager: public(HashMap[address, uint256]) # manager -> index
numManagers: public(uint256) # num managers

# constants
ONE_WEEK_SECONDS: constant(uint256) = 60 * 60 * 24 * 7
HUNDRED_PERCENT: constant(uint256) = 100_00 # 100.00%
MAX_SWAP_INSTRUCTIONS: constant(uint256) = 5
MAX_TOKEN_PATH: constant(uint256) = 5
MAX_LEGOS: constant(uint256) = 10
MAX_DEREGISTER_ASSETS: constant(uint256) = 25

# registry ids
LEDGER_ID: constant(uint256) = 1
MISSION_CONTROL_ID: constant(uint256) = 2
LEGO_BOOK_ID: constant(uint256) = 3
SWITCHBOARD_ID: constant(uint256) = 4
APPRAISER_ID: constant(uint256) = 7
VAULT_REGISTRY_ID: constant(uint256) = 10

UNDY_HQ: immutable(address)
VAULT_ASSET: immutable(address)


@deploy
def __init__(
    _undyHq: address,
    _vaultAsset: address,
    _startingAgent: address,
    # price config
    _minSnapshotDelay: uint256,
    _maxNumSnapshots: uint256,
    _maxUpsideDeviation: uint256,
    _staleTime: uint256,
):
    # not using 0 index
    self.numManagers = 1
    self.numAssets = 1

    assert empty(address) not in [_undyHq, _vaultAsset] # dev: inv addr
    UNDY_HQ = _undyHq
    VAULT_ASSET = _vaultAsset

    # initial agent
    if _startingAgent != empty(address):
        self._registerManager(_startingAgent)

    # set price config
    config: SnapShotPriceConfig = SnapShotPriceConfig(
        minSnapshotDelay = _minSnapshotDelay,
        maxNumSnapshots = _maxNumSnapshots,
        maxUpsideDeviation = _maxUpsideDeviation,
        staleTime = _staleTime,
    )
    assert self._isValidPriceConfig(config) # dev: invalid config
    self.snapShotPriceConfig = config

    # set default redemption buffer to 2% (200 basis points)
    self.redemptionBuffer = 2_00


#########
# Yield #
#########


# deposit


@external
def depositForYield(
    _legoId: uint256,
    _asset: address,
    _vaultAddr: address = empty(address),
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, address, uint256, uint256):
    ad: VaultActionData = self._canManagerPerformAction(msg.sender, [_legoId])
    return self._depositForYield(_asset, _vaultAddr, _amount, _extraData, True, ad)


@internal
def _depositForYield(
    _asset: address,
    _vaultAddr: address,
    _amount: uint256,
    _extraData: bytes32,
    _shouldGenerateEvent: bool,
    _ad: VaultActionData,
) -> (uint256, address, uint256, uint256):
    amount: uint256 = self._getAmountAndApprove(_asset, _amount, _ad.legoAddr) # doing approval here

    # deposit for yield
    assetAmount: uint256 = 0
    vaultToken: address = empty(address)
    vaultTokenAmountReceived: uint256 = 0
    txUsdValue: uint256 = 0
    assetAmount, vaultToken, vaultTokenAmountReceived, txUsdValue = extcall Lego(_ad.legoAddr).depositForYield(_asset, amount, _vaultAddr, _extraData, self, self._packMiniAddys(_ad.ledger, _ad.missionControl, _ad.legoBook, _ad.appraiser))
    assert extcall IERC20(_asset).approve(_ad.legoAddr, 0, default_return_value = True) # dev: appr

    # update yield position
    if _asset == VAULT_ASSET:
        assert self.isApprovedYieldLego[_ad.legoId] # dev: not approved lego id
        assert self.isApprovedVaultToken[vaultToken] # dev: not approved vault token
        self._updateYieldPosition(vaultToken, _ad.legoId, _ad.legoAddr)

    if _shouldGenerateEvent:
        log EarnVaultAction(
            op = 10,
            asset1 = _asset,
            asset2 = vaultToken,
            amount1 = assetAmount,
            amount2 = vaultTokenAmountReceived,
            usdValue = txUsdValue,
            legoId = _ad.legoId,
            signer = _ad.signer,
        )
    return assetAmount, vaultToken, vaultTokenAmountReceived, txUsdValue


# withdraw


@external
def withdrawFromYield(
    _legoId: uint256,
    _vaultToken: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _isSpecialTx: bool = False,
) -> (uint256, address, uint256, uint256):
    ad: VaultActionData = self._canManagerPerformAction(msg.sender, [_legoId])
    return self._withdrawFromYield(_vaultToken, _amount, _extraData, True, ad)


@internal
def _withdrawFromYield(
    _vaultToken: address,
    _amount: uint256,
    _extraData: bytes32,
    _shouldGenerateEvent: bool,
    _ad: VaultActionData,
) -> (uint256, address, uint256, uint256):
    assert _vaultToken != empty(address) # dev: invalid vault token
    amount: uint256 = self._getAmountAndApprove(_vaultToken, _amount, empty(address)) # not approving here

    # some vault tokens require max value approval (comp v3)
    assert extcall IERC20(_vaultToken).approve(_ad.legoAddr, max_value(uint256), default_return_value = True) # dev: appr

    # withdraw from yield
    vaultTokenAmountBurned: uint256 = 0
    underlyingAsset: address = empty(address)
    underlyingAmount: uint256 = 0
    txUsdValue: uint256 = 0
    vaultTokenAmountBurned, underlyingAsset, underlyingAmount, txUsdValue = extcall Lego(_ad.legoAddr).withdrawFromYield(_vaultToken, amount, _extraData, self, self._packMiniAddys(_ad.ledger, _ad.missionControl, _ad.legoBook, _ad.appraiser))
    assert extcall IERC20(_vaultToken).approve(_ad.legoAddr, 0, default_return_value = True) # dev: appr

    # update yield position
    if underlyingAsset == VAULT_ASSET:
        self._updateYieldPosition(_vaultToken, _ad.legoId, _ad.legoAddr)

    if _shouldGenerateEvent:
        log EarnVaultAction(
            op = 11,
            asset1 = _vaultToken,
            asset2 = underlyingAsset,
            amount1 = vaultTokenAmountBurned,
            amount2 = underlyingAmount,
            usdValue = txUsdValue,
            legoId = _ad.legoId,
            signer = _ad.signer,
        )
    return vaultTokenAmountBurned, underlyingAsset, underlyingAmount, txUsdValue


# rebalance position


@external
def rebalanceYieldPosition(
    _fromLegoId: uint256,
    _fromVaultToken: address,
    _toLegoId: uint256,
    _toVaultAddr: address = empty(address),
    _fromVaultAmount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, address, uint256, uint256):
    ad: VaultActionData = self._canManagerPerformAction(msg.sender, [_fromLegoId, _toLegoId])

    # withdraw
    vaultTokenAmountBurned: uint256 = 0
    underlyingAsset: address = empty(address)
    underlyingAmount: uint256 = 0
    withdrawTxUsdValue: uint256 = 0
    vaultTokenAmountBurned, underlyingAsset, underlyingAmount, withdrawTxUsdValue = self._withdrawFromYield(_fromVaultToken, _fromVaultAmount, _extraData, False, ad)

    # deposit
    toVaultToken: address = empty(address)
    toVaultTokenAmountReceived: uint256 = 0
    depositTxUsdValue: uint256 = 0
    ad.legoId = _toLegoId
    ad.legoAddr = staticcall Registry(ad.legoBook).getAddr(_toLegoId)
    underlyingAmount, toVaultToken, toVaultTokenAmountReceived, depositTxUsdValue = self._depositForYield(underlyingAsset, _toVaultAddr, underlyingAmount, _extraData, False, ad)

    maxUsdValue: uint256 = max(withdrawTxUsdValue, depositTxUsdValue)
    log EarnVaultAction(
        op = 12,
        asset1 = _fromVaultToken,
        asset2 = toVaultToken,
        amount1 = vaultTokenAmountBurned,
        amount2 = toVaultTokenAmountReceived,
        usdValue = maxUsdValue,
        legoId = ad.legoId,
        signer = ad.signer,
    )
    return underlyingAmount, toVaultToken, toVaultTokenAmountReceived, maxUsdValue


###################
# Swap / Exchange #
###################


@external
def swapTokens(_instructions: DynArray[wi.SwapInstruction, MAX_SWAP_INSTRUCTIONS]) -> (address, uint256, address, uint256, uint256):
    tokenIn: address = empty(address)
    tokenOut: address = empty(address)
    legoIds: DynArray[uint256, MAX_LEGOS] = []
    tokenIn, tokenOut, legoIds = self._validateAndGetSwapInfo(_instructions)

    # important checks!
    assert tokenIn != VAULT_ASSET # dev: cannot swap out of vault asset
    assert self.assetData[tokenIn].legoId == 0 # dev: cannot swap out of vault token
    assert tokenOut == VAULT_ASSET # dev: must swap into vault asset

    # action data bundle
    ad: VaultActionData = self._canManagerPerformAction(msg.sender, legoIds)
    origAmountIn: uint256 = self._getAmountAndApprove(tokenIn, _instructions[0].amountIn, empty(address)) # not approving here

    amountIn: uint256 = origAmountIn
    lastTokenOut: address = empty(address)
    lastTokenOutAmount: uint256 = 0
    maxTxUsdValue: uint256 = 0

    # perform swaps
    for i: wi.SwapInstruction in _instructions:
        if lastTokenOut != empty(address):
            newTokenIn: address = i.tokenPath[0]
            assert lastTokenOut == newTokenIn # dev: path
            amountIn = min(lastTokenOutAmount, staticcall IERC20(newTokenIn).balanceOf(self))
        
        thisTxUsdValue: uint256 = 0
        lastTokenOut, lastTokenOutAmount, thisTxUsdValue = self._performSwapInstruction(amountIn, i, ad)
        maxTxUsdValue = max(maxTxUsdValue, thisTxUsdValue)

    log EarnVaultAction(
        op = 20,
        asset1 = tokenIn,
        asset2 = lastTokenOut,
        amount1 = origAmountIn,
        amount2 = lastTokenOutAmount,
        usdValue = maxTxUsdValue,
        legoId = ad.legoId, # using just the first lego used
        signer = ad.signer,
    )
    return tokenIn, origAmountIn, lastTokenOut, lastTokenOutAmount, maxTxUsdValue


@internal
def _performSwapInstruction(
    _amountIn: uint256,
    _i: wi.SwapInstruction,
    _ad: VaultActionData,
) -> (address, uint256, uint256):
    legoAddr: address = staticcall Registry(_ad.legoBook).getAddr(_i.legoId)
    assert legoAddr != empty(address) # dev: lego

    # tokens
    tokenIn: address = _i.tokenPath[0]
    tokenOut: address = _i.tokenPath[len(_i.tokenPath) - 1]
    tokenInAmount: uint256 = 0
    tokenOutAmount: uint256 = 0
    txUsdValue: uint256 = 0

    assert extcall IERC20(tokenIn).approve(legoAddr, _amountIn, default_return_value = True) # dev: appr
    tokenInAmount, tokenOutAmount, txUsdValue = extcall Lego(legoAddr).swapTokens(_amountIn, _i.minAmountOut, _i.tokenPath, _i.poolPath, self, self._packMiniAddys(_ad.ledger, _ad.missionControl, _ad.legoBook, _ad.appraiser))
    assert extcall IERC20(tokenIn).approve(legoAddr, 0, default_return_value = True) # dev: appr
    return tokenOut, tokenOutAmount, txUsdValue


@internal
def _validateAndGetSwapInfo(_instructions: DynArray[wi.SwapInstruction, MAX_SWAP_INSTRUCTIONS]) -> (address, address, DynArray[uint256, MAX_LEGOS]):
    numSwapInstructions: uint256 = len(_instructions)
    assert numSwapInstructions != 0 # dev: swaps

    # lego ids, make sure token paths are valid
    legoIds: DynArray[uint256, MAX_LEGOS] = []
    for i: wi.SwapInstruction in _instructions:
        assert len(i.tokenPath) >= 2 # dev: path
        if i.legoId not in legoIds:
            legoIds.append(i.legoId)

    # finalize tokens
    firstRoutePath: DynArray[address, MAX_TOKEN_PATH] = _instructions[0].tokenPath
    tokenIn: address = firstRoutePath[0]
    tokenOut: address = empty(address)

    if numSwapInstructions == 1:
        tokenOut = firstRoutePath[len(firstRoutePath) - 1]
    else:
        lastRoutePath: DynArray[address, MAX_TOKEN_PATH] = _instructions[numSwapInstructions - 1].tokenPath
        tokenOut = lastRoutePath[len(lastRoutePath) - 1]

    assert empty(address) not in [tokenIn, tokenOut] # dev: path
    return tokenIn, tokenOut, legoIds


#################
# Claim Rewards #
#################


@external
def claimRewards(
    _legoId: uint256,
    _rewardToken: address = empty(address),
    _rewardAmount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256):
    ad: VaultActionData = self._canManagerPerformAction(msg.sender, [_legoId])

    # make sure can access
    self._setLegoAccessForAction(ad.legoAddr, ws.ActionType.REWARDS)

    # claim rewards
    rewardAmount: uint256 = 0
    txUsdValue: uint256 = 0
    rewardAmount, txUsdValue = extcall Lego(ad.legoAddr).claimRewards(self, _rewardToken, _rewardAmount, _extraData, self._packMiniAddys(ad.ledger, ad.missionControl, ad.legoBook, ad.appraiser))

    log EarnVaultAction(
        op = 50,
        asset1 = _rewardToken,
        asset2 = ad.legoAddr,
        amount1 = rewardAmount,
        amount2 = 0,
        usdValue = txUsdValue,
        legoId = ad.legoId,
        signer = ad.signer,
    )
    return rewardAmount, txUsdValue


################
# Total Assets #
################


@view
@external
def getTotalAssets(_shouldGetMax: bool) -> uint256:
    return self._getTotalAssets(_shouldGetMax)


@view
@internal
def _getTotalAssets(_shouldGetMax: bool) -> uint256:
    totalAssets: uint256 = staticcall IERC20(VAULT_ASSET).balanceOf(self)

    # get num assets
    numAssets: uint256 = self.numAssets
    if numAssets == 0:
        return totalAssets

    # iterate over each asset
    legoBook: address = staticcall Registry(UNDY_HQ).getAddr(LEGO_BOOK_ID)
    for i: uint256 in range(1, numAssets, bound=max_value(uint256)):

        # get asset addr
        vaultToken: address = self.assets[i]
        if vaultToken == empty(address):
            continue

        vaultTokenBalance: uint256 = staticcall IERC20(vaultToken).balanceOf(self)
        if vaultTokenBalance == 0:
            continue

        data: LocalVaultTokenData = self.assetData[vaultToken]
        if data.legoId == 0 or data.vaultTokenDecimals == 0:
            continue

        # add to total assets
        if data.isRebasing:
            totalAssets += vaultTokenBalance # TODO: check that decimals match up with underlying asset !!

        else:
            legoAddr: address = staticcall Registry(legoBook).getAddr(data.legoId)
            pricePerShare: uint256 = staticcall Lego(legoAddr).getPricePerShare(vaultToken, data.vaultTokenDecimals)
            trueBalance: uint256 = vaultTokenBalance * pricePerShare // (10 ** data.vaultTokenDecimals)

            if _shouldGetMax:
                totalAssets += trueBalance
            else:
                avgBalance: uint256 = vaultTokenBalance * data.avgPricePerShare // (10 ** data.vaultTokenDecimals)
                totalAssets += min(avgBalance, trueBalance)

    return totalAssets


###################
# Redemption Prep #
###################


@internal
def _prepareRedemption(_amount: uint256, _sender: address) -> uint256:
    vaultAsset: address = VAULT_ASSET
    ad: VaultActionData = self._getVaultActionDataBundle(0, _sender)

    withdrawnAmount: uint256 = staticcall IERC20(vaultAsset).balanceOf(self)
    if withdrawnAmount >= _amount:
        return withdrawnAmount

    # buffer to make sure we pull out enough for redemption
    bufferMultiplier: uint256 = HUNDRED_PERCENT + self.redemptionBuffer
    targetWithdrawAmount: uint256 = _amount * bufferMultiplier // HUNDRED_PERCENT
    assetsToDeregister: DynArray[address, MAX_DEREGISTER_ASSETS] = []

    numAssets: uint256 = self.numAssets
    if numAssets == 0:
        return withdrawnAmount

    for i: uint256 in range(1, numAssets, bound=max_value(uint256)):
        if withdrawnAmount >= targetWithdrawAmount:
            break

        vaultToken: address = self.assets[i]
        if vaultToken == empty(address):
            continue

        vaultTokenBalance: uint256 = staticcall IERC20(vaultToken).balanceOf(self)
        if vaultTokenBalance == 0:
            continue

        data: LocalVaultTokenData = self.assetData[vaultToken]
        if data.legoId == 0 or data.vaultTokenDecimals == 0:
            continue

        ad.legoId = data.legoId
        ad.legoAddr = staticcall Registry(ad.legoBook).getAddr(data.legoId)

        # get price per share
        pricePerShare: uint256 = 0
        if data.isRebasing:
            pricePerShare = 10 ** data.vaultTokenDecimals
        else:
            pricePerShare = staticcall Lego(ad.legoAddr).getPricePerShare(vaultToken, data.vaultTokenDecimals)

        # calculate how many vault tokens we need to withdraw
        amountStillNeeded: uint256 = targetWithdrawAmount - withdrawnAmount
        vaultTokensNeeded: uint256 = amountStillNeeded * (10 ** data.vaultTokenDecimals) // pricePerShare

        # withdraw from yield opportunity
        na1: uint256 = 0
        na2: address = empty(address)
        underlyingAmount: uint256 = 0
        na3: uint256 = 0
        na1, na2, underlyingAmount, na3 = self._withdrawFromYield(vaultToken, vaultTokensNeeded, empty(bytes32), True, ad)

        # add to withdrawn amount
        withdrawnAmount += underlyingAmount

        # add to deregister list
        if vaultTokensNeeded > vaultTokenBalance and len(assetsToDeregister) < MAX_DEREGISTER_ASSETS:
            assetsToDeregister.append(vaultToken)

    # deregister vault positions
    for asset: address in assetsToDeregister:
        self._deregisterYieldPosition(asset)

    return withdrawnAmount


###################
# Yield Positions #
###################


# update yield position


@external
def updateYieldPosition(_vaultToken: address):
    assert self._isSwitchboardAddr(msg.sender) # dev: no perms
    legoId: uint256 = 0
    legoAddr: address = empty(address)
    legoId, legoAddr = self._getLegoDataFromVaultToken(_vaultToken)
    if legoId != 0 and legoAddr != empty(address):
        self._updateYieldPosition(_vaultToken, legoId, legoAddr)


@internal
def _updateYieldPosition(_vaultToken: address, _legoId: uint256, _legoAddr: address):
    if _vaultToken == empty(address):
        return

    # no balance, deregister asset
    currentBalance: uint256 = staticcall IERC20(_vaultToken).balanceOf(self)
    if currentBalance == 0:
        self._deregisterYieldPosition(_vaultToken)
        return

    data: LocalVaultTokenData = self.assetData[_vaultToken]
    needsSave: bool = False

    # first time, need to save data
    if data.legoId == 0:
        data.legoId = _legoId
        data.isRebasing = staticcall YieldLego(_legoAddr).isRebasing()
        data.vaultTokenDecimals = convert(staticcall IERC20Detailed(_vaultToken).decimals(), uint256)
        needsSave = True

    # non-rebase assets use weighted average share prices
    if not data.isRebasing:
        config: SnapShotPriceConfig = self.snapShotPriceConfig
        self._addPriceSnapshot(_vaultToken, _legoAddr, data.vaultTokenDecimals, config)
        data.avgPricePerShare = self._getWeightedPricePerShare(_vaultToken, config)
        if data.avgPricePerShare != 0:
            needsSave = True

    # save data
    if needsSave:
        self.assetData[_vaultToken] = data

    # register asset (if necessary)
    if self.indexOfAsset[_vaultToken] == 0:
        self._registerYieldPosition(_vaultToken)


# register yield position


@internal
def _registerYieldPosition(_vaultToken: address):
    aid: uint256 = self.numAssets
    self.assets[aid] = _vaultToken
    self.indexOfAsset[_vaultToken] = aid
    self.numAssets = aid + 1


# deregister yield position


@internal
def _deregisterYieldPosition(_vaultToken: address) -> bool:
    numAssets: uint256 = self.numAssets
    if numAssets == 1:
        return False

    targetIndex: uint256 = self.indexOfAsset[_vaultToken]
    if targetIndex == 0:
        return False

    # update data
    lastIndex: uint256 = numAssets - 1
    self.numAssets = lastIndex
    self.indexOfAsset[_vaultToken] = 0

    # get last item, replace the removed item
    if targetIndex != lastIndex:
        lastItem: address = self.assets[lastIndex]
        self.assets[targetIndex] = lastItem
        self.indexOfAsset[lastItem] = targetIndex

    return True


###################
# Price Snapshots #
###################


# get weighted price


@view
@external
def getWeightedPrice(_vaultToken: address) -> uint256:
    return self._getWeightedPricePerShare(_vaultToken, self.snapShotPriceConfig)


@view
@internal
def _getWeightedPricePerShare(_vaultToken: address, _config: SnapShotPriceConfig) -> uint256:
    if _config.maxNumSnapshots == 0:
        return 0

    # calculate weighted average price using all valid snapshots
    numerator: uint256 = 0
    denominator: uint256 = 0
    for i: uint256 in range(_config.maxNumSnapshots, bound=max_value(uint256)):

        snapShot: SingleSnapShot = self.snapShots[_vaultToken][i]
        if snapShot.pricePerShare == 0 or snapShot.totalSupply == 0 or snapShot.lastUpdate == 0:
            continue

        # too stale, skip
        if _config.staleTime != 0 and block.timestamp > snapShot.lastUpdate + _config.staleTime:
            continue

        numerator += (snapShot.totalSupply * snapShot.pricePerShare)
        denominator += snapShot.totalSupply

    # weighted price per share
    weightedPricePerShare: uint256 = 0
    if numerator != 0:
        weightedPricePerShare = numerator // denominator
    else:
        data: SnapShotData = self.snapShotData[_vaultToken]
        weightedPricePerShare = data.lastSnapShot.pricePerShare

    return weightedPricePerShare


# add price snapshot


@external 
def addPriceSnapshot(_vaultToken: address) -> bool:
    assert self._isSwitchboardAddr(msg.sender) # dev: no perms
    legoAddr: address = self._getLegoAddrFromVaultToken(_vaultToken)
    if legoAddr == empty(address):
        return False
    vaultTokenDecimals: uint256 = convert(staticcall IERC20Detailed(_vaultToken).decimals(), uint256)
    return self._addPriceSnapshot(_vaultToken, legoAddr, vaultTokenDecimals, self.snapShotPriceConfig)


@internal 
def _addPriceSnapshot(
    _vaultToken: address,
    _legoAddr: address,
    _vaultTokenDecimals: uint256,
    _config: SnapShotPriceConfig,
) -> bool:
    data: SnapShotData = self.snapShotData[_vaultToken]

    # already have snapshot for this time
    if data.lastSnapShot.lastUpdate == block.timestamp:
        return False

    # check if snapshot is too recent
    if data.lastSnapShot.lastUpdate + _config.minSnapshotDelay > block.timestamp:
        return False

    # create and store new snapshot
    newSnapshot: SingleSnapShot = self._getLatestSnapshot(_vaultToken, _legoAddr, _vaultTokenDecimals, data.lastSnapShot, _config)
    data.lastSnapShot = newSnapshot
    self.snapShots[_vaultToken][data.nextIndex] = newSnapshot

    # update index
    data.nextIndex += 1
    if data.nextIndex >= _config.maxNumSnapshots:
        data.nextIndex = 0

    # save snap shot data
    self.snapShotData[_vaultToken] = data

    log PricePerShareSnapShotAdded(
        vaultToken = _vaultToken,
        totalSupply = newSnapshot.totalSupply,
        pricePerShare = newSnapshot.pricePerShare,
    )
    return True


# latest snapshot


@view
@external
def getLatestSnapshot(_vaultToken: address) -> SingleSnapShot:
    legoAddr: address = self._getLegoAddrFromVaultToken(_vaultToken)
    if legoAddr == empty(address):
        return empty(SingleSnapShot)
    vaultTokenDecimals: uint256 = convert(staticcall IERC20Detailed(_vaultToken).decimals(), uint256)
    data: SnapShotData = self.snapShotData[_vaultToken]
    return self._getLatestSnapshot(_vaultToken, legoAddr, vaultTokenDecimals, data.lastSnapShot, self.snapShotPriceConfig)


@view
@internal
def _getLatestSnapshot(
    _vaultToken: address,
    _legoAddr: address,
    _vaultTokenDecimals: uint256,
    _lastSnapShot: SingleSnapShot,
    _config: SnapShotPriceConfig,
) -> SingleSnapShot:

    # total supply (adjusted)
    totalSupply: uint256 = staticcall IERC20(_vaultToken).totalSupply() // (10 ** _vaultTokenDecimals)

    # get current price per share
    pricePerShare: uint256 = staticcall Lego(_legoAddr).getPricePerShare(_vaultToken, _vaultTokenDecimals)

    # throttle upside (extra safety check)
    pricePerShare = self._throttleUpside(pricePerShare, _lastSnapShot.pricePerShare, _config.maxUpsideDeviation)

    return SingleSnapShot(
        totalSupply = totalSupply,
        pricePerShare = pricePerShare,
        lastUpdate = block.timestamp,
    )


@view
@internal
def _throttleUpside(_newValue: uint256, _prevValue: uint256, _maxUpside: uint256) -> uint256:
    if _maxUpside == 0 or _prevValue == 0 or _newValue == 0:
        return _newValue
    maxPricePerShare: uint256 = _prevValue + (_prevValue * _maxUpside // HUNDRED_PERCENT)
    return min(_newValue, maxPricePerShare)


####################
# Manager Settings #
####################


# can manage


@internal
def _canManagerPerformAction(_signer: address, _legoIds: DynArray[uint256, MAX_LEGOS]) -> VaultActionData:
    assert self.indexOfManager[_signer] != 0 # dev: not manager

    # main data for this transaction
    legoId: uint256 = 0
    if len(_legoIds) != 0:
        legoId = _legoIds[0]
    ad: VaultActionData = self._getVaultActionDataBundle(legoId, _signer)

    # cannot perform any actions if vault is frozen
    assert not self.isVaultOpsFrozen # dev: frozen vault

    # make sure manager is not locked
    assert not staticcall MissionControl(ad.missionControl).isLockedSigner(_signer) # dev: manager is locked

    return ad


# add manager


@external
def addManager(_manager: address):
    assert self._isSwitchboardAddr(msg.sender) # dev: no perms
    self._registerManager(_manager)


# register manager


@internal
def _registerManager(_manager: address):
    if self.indexOfManager[_manager] != 0:
        return
    mid: uint256 = self.numManagers
    self.managers[mid] = _manager
    self.indexOfManager[_manager] = mid
    self.numManagers = mid + 1


# remove manager


@external
def removeManager(_manager: address):
    assert self._isSwitchboardAddr(msg.sender) # dev: no perms

    numManagers: uint256 = self.numManagers
    if numManagers == 1:
        return

    targetIndex: uint256 = self.indexOfManager[_manager]
    if targetIndex == 0:
        return

    # update data
    lastIndex: uint256 = numManagers - 1
    self.numManagers = lastIndex
    self.indexOfManager[_manager] = 0

    # get last item, replace the removed item
    if targetIndex != lastIndex:
        lastItem: address = self.managers[lastIndex]
        self.managers[targetIndex] = lastItem
        self.indexOfManager[lastItem] = targetIndex


# freeze vault ops


@external
def setVaultOpsFrozen(_isFrozen: bool):
    if not self._isSwitchboardAddr(msg.sender):
        assert self._canPerformSecurityAction(msg.sender) and _isFrozen # dev: no perms
    assert _isFrozen != self.isVaultOpsFrozen # dev: nothing to change
    self.isVaultOpsFrozen = _isFrozen
    log VaultOpsFrozenSet(isFrozen=_isFrozen, caller=msg.sender)


###########################
# Approved Legos / Vaults #
###########################


@external
def setApprovedVaultToken(_vaultToken: address, _isApproved: bool):
    assert self._isSwitchboardAddr(msg.sender) # dev: no perms
    assert _vaultToken != empty(address) # dev: invalid vault token
    assert _isApproved != self.isApprovedVaultToken[_vaultToken] # dev: nothing to change
    self.isApprovedVaultToken[_vaultToken] = _isApproved
    log ApprovedVaultTokenSet(vaultToken=_vaultToken, isApproved=_isApproved)


@external
def setApprovedYieldLego(_legoId: uint256, _isApproved: bool):
    assert self._isSwitchboardAddr(msg.sender) # dev: no perms
    assert _legoId != 0 # dev: invalid lego id
    assert _isApproved != self.isApprovedYieldLego[_legoId] # dev: nothing to change
    self.isApprovedYieldLego[_legoId] = _isApproved
    log ApprovedYieldLegoSet(legoId=_legoId, isApproved=_isApproved)


################
# Price Config #
################


@external
def setPriceConfig(_config: SnapShotPriceConfig):
    assert self._isSwitchboardAddr(msg.sender) # dev: no perms
    assert self._isValidPriceConfig(_config) # dev: invalid config

    self.snapShotPriceConfig = _config
    log PriceConfigSet(minSnapshotDelay = _config.minSnapshotDelay, maxNumSnapshots = _config.maxNumSnapshots, maxUpsideDeviation = _config.maxUpsideDeviation, staleTime = _config.staleTime)


# validation


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


#####################
# Redemption Buffer #
#####################


@external
def setRedemptionBuffer(_buffer: uint256):
    assert self._isSwitchboardAddr(msg.sender) # dev: no perms
    assert _buffer <= 10_00 # dev: buffer too high (max 10%)
    self.redemptionBuffer = _buffer
    log RedemptionBufferSet(buffer = _buffer)


#############
# Utilities #
#############


# is signer switchboard


@view
@internal
def _isSwitchboardAddr(_signer: address) -> bool:
    switchboard: address = staticcall Registry(UNDY_HQ).getAddr(SWITCHBOARD_ID)
    if switchboard == empty(address):
        return False
    return staticcall Switchboard(switchboard).isSwitchboardAddr(_signer)


# can perform security action


@view
@internal
def _canPerformSecurityAction(_addr: address) -> bool:
    missionControl: address = staticcall Registry(UNDY_HQ).getAddr(MISSION_CONTROL_ID)
    if missionControl == empty(address):
        return False
    return staticcall MissionControl(missionControl).canPerformSecurityAction(_addr)


# approve


@internal
def _getAmountAndApprove(_token: address, _amount: uint256, _legoAddr: address) -> uint256:
    amount: uint256 = min(_amount, staticcall IERC20(_token).balanceOf(self))
    assert amount != 0 # dev: no balance for _token
    if _legoAddr != empty(address):
        assert extcall IERC20(_token).approve(_legoAddr, amount, default_return_value = True) # dev: appr
    return amount


# lego access


@internal
def _setLegoAccessForAction(_legoAddr: address, _action: ws.ActionType) -> bool:
    if _legoAddr == empty(address):
        return False

    targetAddr: address = empty(address)
    accessAbi: String[64] = empty(String[64])
    numInputs: uint256 = 0
    targetAddr, accessAbi, numInputs = staticcall Lego(_legoAddr).getAccessForLego(self, _action)

    # nothing to do here
    if targetAddr == empty(address):
        return False

    method_abi: bytes4 = convert(slice(keccak256(accessAbi), 0, 4), bytes4)
    success: bool = False
    response: Bytes[32] = b""

    # assumes input is: lego addr (operator)
    if numInputs == 1:
        success, response = raw_call(
            targetAddr,
            concat(
                method_abi,
                convert(_legoAddr, bytes32),
            ),
            revert_on_failure = False,
            max_outsize = 32,
        )
    
    # assumes input (and order) is: user (self), lego addr (operator)
    elif numInputs == 2:
        success, response = raw_call(
            targetAddr,
            concat(
                method_abi,
                convert(self, bytes32),
                convert(_legoAddr, bytes32),
            ),
            revert_on_failure = False,
            max_outsize = 32,
        )

    # assumes input (and order) is: user (self), lego addr (operator), allowed bool
    elif numInputs == 3:
        success, response = raw_call(
            targetAddr,
            concat(
                method_abi,
                convert(self, bytes32),
                convert(_legoAddr, bytes32),
                convert(True, bytes32),
            ),
            revert_on_failure = False,
            max_outsize = 32,
        )

    assert success # dev: failed to set operator
    return True


# mini addys


@view
@internal
def _packMiniAddys(
    _ledger: address,
    _missionControl: address,
    _legoBook: address,
    _appraiser: address,
) -> ws.MiniAddys:
    return ws.MiniAddys(
        ledger = _ledger,
        missionControl = _missionControl,
        legoBook = _legoBook,
        appraiser = _appraiser,
    )


# action data bundle


@view
@external
def getVaultActionDataBundle(_legoId: uint256, _signer: address) -> VaultActionData:
    return self._getVaultActionDataBundle(_legoId, _signer)


@view
@internal
def _getVaultActionDataBundle(_legoId: uint256, _signer: address) -> VaultActionData:
    hq: address = UNDY_HQ

    # lego details
    legoBook: address = staticcall Registry(hq).getAddr(LEGO_BOOK_ID)
    legoAddr: address = empty(address)
    if _legoId != 0 and legoBook != empty(address):
        legoAddr = staticcall Registry(legoBook).getAddr(_legoId)

    return VaultActionData(
        ledger = staticcall Registry(hq).getAddr(LEDGER_ID),
        missionControl = staticcall Registry(hq).getAddr(MISSION_CONTROL_ID),
        legoBook = legoBook,
        appraiser = staticcall Registry(hq).getAddr(APPRAISER_ID),
        vaultRegistry = staticcall Registry(hq).getAddr(VAULT_REGISTRY_ID),
        signer = _signer,
        legoId = _legoId,
        legoAddr = legoAddr,
    )


# get lego data from vault token


@view
@internal
def _getLegoDataFromVaultToken(_vaultToken: address) -> (uint256, address):
    unyHq: address = UNDY_HQ
    ledger: address = staticcall Registry(unyHq).getAddr(LEDGER_ID)
    if ledger == empty(address):
        return 0, empty(address)
    data: VaultToken = staticcall Ledger(ledger).vaultTokens(_vaultToken)
    if data.legoId == 0:
        return 0, empty(address)
    legoBook: address = staticcall Registry(unyHq).getAddr(LEGO_BOOK_ID)
    if legoBook == empty(address):
        return 0, empty(address)
    return data.legoId, staticcall Registry(legoBook).getAddr(data.legoId)


@view
@internal
def _getLegoAddrFromVaultToken(_vaultToken: address) -> address:
    na: uint256 = 0
    legoAddr: address = empty(address)
    na, legoAddr = self._getLegoDataFromVaultToken(_vaultToken)
    return legoAddr
