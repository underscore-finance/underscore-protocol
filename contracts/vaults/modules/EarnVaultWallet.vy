#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3
# pragma optimize codesize

from interfaces import YieldLego as YieldLego
from interfaces import Wallet as wi
from interfaces import LegoPartner as Lego
from interfaces import WalletStructs as ws

from ethereum.ercs import IERC20
from ethereum.ercs import IERC20Detailed

interface VaultRegistry:
    def getVaultActionDataWithFrozenStatus(_legoId: uint256, _signer: address, _vaultAddr: address) -> (VaultActionData, bool): view
    def getLegoAndSnapshotConfig(_vaultToken: address, _vaultAddr: address) -> (address, SnapShotPriceConfig): view
    def getVaultActionDataBundle(_legoId: uint256, _signer: address) -> VaultActionData: view
    def checkVaultApprovals(_vaultAddr: address, _vaultToken: address) -> bool: view
    def getLegoDataFromVaultToken(_vaultToken: address) -> (uint256, address): view
    def snapShotPriceConfig(_vaultAddr: address) -> SnapShotPriceConfig: view
    def redemptionConfig(_vaultAddr: address) -> (uint256, uint256): view
    def getPerformanceFee(_vaultAddr: address) -> uint256: view

interface Switchboard:
    def isSwitchboardAddr(_addr: address) -> bool: view

interface MissionControl:
    def isLockedSigner(_signer: address) -> bool: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

interface UndyHq:
    def governance() -> address: view

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

event PerformanceFeesClaimed:
    pendingFees: uint256

# yield tracking
lastUnderlyingBal: public(uint256)
pendingYieldRealized: public(uint256)

# asset data
assetData: public(HashMap[address, LocalVaultTokenData]) # asset -> data
assets: public(HashMap[uint256, address]) # index -> asset
indexOfAsset: public(HashMap[address, uint256]) # asset -> index
numAssets: public(uint256) # num assets

# price snap shot data
snapShotData: public(HashMap[address, SnapShotData]) # asset -> data
snapShots: public(HashMap[address, HashMap[uint256, SingleSnapShot]]) # asset -> index -> snapshot

# managers
managers: public(HashMap[uint256, address]) # index -> manager
indexOfManager: public(HashMap[address, uint256]) # manager -> index
numManagers: public(uint256) # num managers

# constants
HUNDRED_PERCENT: constant(uint256) = 100_00 # 100.00%
MAX_SWAP_INSTRUCTIONS: constant(uint256) = 5
MAX_TOKEN_PATH: constant(uint256) = 5
MAX_LEGOS: constant(uint256) = 10
MAX_DEREGISTER_ASSETS: constant(uint256) = 25

# registry ids
LEGO_BOOK_ID: constant(uint256) = 3
SWITCHBOARD_ID: constant(uint256) = 4
VAULT_REGISTRY_ID: constant(uint256) = 10

UNDY_HQ: immutable(address)
VAULT_ASSET: immutable(address)


@deploy
def __init__(
    _undyHq: address,
    _vaultAsset: address,
    _startingAgent: address,
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
    return self._depositForYield(_legoId, _asset, _vaultAddr, _amount, _extraData, self._getUnderlyingAndUpdatePendingYield(), True, ad)


@internal
def _onReceiveVaultFunds(
    _vaultAddr: address,
    _depositor: address,
    _vaultRegistry: address,
) -> uint256:
    legoId: uint256 = self.assetData[_vaultAddr].legoId
    ad: VaultActionData = staticcall VaultRegistry(_vaultRegistry).getVaultActionDataBundle(legoId, _depositor)
    if ad.legoId == 0 or ad.legoAddr == empty(address):
        return 0
    return self._depositForYield(ad.legoId, VAULT_ASSET, _vaultAddr, max_value(uint256), empty(bytes32), 0, False, ad)[0]


@internal
def _depositForYield(
    _legoId: uint256,
    _asset: address,
    _vaultAddr: address,
    _amount: uint256,
    _extraData: bytes32,
    _currentUnderlying: uint256,
    _shouldSaveUnderlying: bool,
    _ad: VaultActionData,
) -> (uint256, address, uint256, uint256):
    amount: uint256 = self._getAmountAndApprove(_asset, _amount, _ad.legoAddr) # doing approval here
    currentUnderlying: uint256 = _currentUnderlying

    # deposit for yield
    assetAmount: uint256 = 0
    vaultToken: address = empty(address)
    vaultTokenAmountReceived: uint256 = 0
    txUsdValue: uint256 = 0
    assetAmount, vaultToken, vaultTokenAmountReceived, txUsdValue = extcall Lego(_ad.legoAddr).depositForYield(_asset, amount, _vaultAddr, _extraData, self, self._packMiniAddys(_ad.ledger, _ad.missionControl, _ad.legoBook, _ad.appraiser))
    assert extcall IERC20(_asset).approve(_ad.legoAddr, 0, default_return_value = True) # dev: appr

    # update yield position
    if _asset == VAULT_ASSET:
        assert _vaultAddr == vaultToken # dev: vault token mismatch
        assert staticcall VaultRegistry(_ad.vaultRegistry).checkVaultApprovals(self, vaultToken) # dev: lego or vault token not approved
        self._updateYieldPosition(vaultToken, _ad.legoId, _ad.legoAddr, _ad.vaultRegistry)
        currentUnderlying += assetAmount

    # save underlying balance
    if _shouldSaveUnderlying:
        self.lastUnderlyingBal = currentUnderlying

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
    return self._withdrawFromYield(_vaultToken, _amount, _extraData, self._getUnderlyingAndUpdatePendingYield(), True, ad)


@internal
def _withdrawFromYield(
    _vaultToken: address,
    _amount: uint256,
    _extraData: bytes32,
    _currentUnderlying: uint256,
    _shouldSaveUnderlying: bool,
    _ad: VaultActionData,
) -> (uint256, address, uint256, uint256):
    assert _vaultToken != empty(address) # dev: invalid vault token
    amount: uint256 = self._getAmountAndApprove(_vaultToken, _amount, empty(address)) # not approving here
    currentUnderlying: uint256 = _currentUnderlying

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
        self._updateYieldPosition(_vaultToken, _ad.legoId, _ad.legoAddr, _ad.vaultRegistry)
        currentUnderlying -= min(currentUnderlying, underlyingAmount)

    if _shouldSaveUnderlying:
        self.lastUnderlyingBal = currentUnderlying

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
    vaultAsset: address = VAULT_ASSET
    assert tokenIn != vaultAsset # dev: cannot swap out of vault asset
    assert self.assetData[tokenIn].legoId == 0 # dev: cannot swap out of vault token
    assert tokenOut == vaultAsset # dev: must swap into vault asset

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


#############################
# Overall Yield Calculation #
#############################


# calculate yield realized


@view
@internal
def _calcNewYieldAndGetUnderlying(_currentUnderlying: uint256 = 0) -> (uint256, uint256):
    currentUnderlying: uint256 = _currentUnderlying
    if currentUnderlying == 0:
        currentUnderlying = self._getUnderlyingYieldBalances()[0]

    newYield: uint256 = 0
    lastUnderlyingBal: uint256 = self.lastUnderlyingBal
    if lastUnderlyingBal != 0 and currentUnderlying > lastUnderlyingBal:
        newYield = currentUnderlying - lastUnderlyingBal

    return currentUnderlying, newYield


# update pending yield realized


@internal
def _getUnderlyingAndUpdatePendingYield() -> uint256:
    currentUnderlying: uint256 = 0
    newYield: uint256 = 0
    currentUnderlying, newYield = self._calcNewYieldAndGetUnderlying()
    self.pendingYieldRealized += newYield
    return currentUnderlying


# claim performance fees


@external
def claimPerformanceFees() -> uint256:
    governance: address = staticcall UndyHq(UNDY_HQ).governance()
    assert self._isSwitchboardAddr(msg.sender) or governance == msg.sender # dev: no perms

    vaultRegistry: address = self._getVaultRegistry()
    currentUnderlying: uint256 = self._getUnderlyingAndUpdatePendingYield()
    pendingFees: uint256 = self.pendingYieldRealized * self._getPerformanceFeeRatio(vaultRegistry) // HUNDRED_PERCENT

    # make withdrawals from yield positions
    availAmount: uint256 = 0
    withdrawnAmount: uint256 = 0
    availAmount, withdrawnAmount = self._prepareRedemption(pendingFees, empty(address), governance, vaultRegistry)
    assert availAmount >= pendingFees # dev: insufficient funds

    # transfer pending fees to governance
    assert extcall IERC20(VAULT_ASSET).transfer(governance, pendingFees, default_return_value=True) # dev: withdrawal failed

    # update data
    self.pendingYieldRealized = 0
    self.lastUnderlyingBal = currentUnderlying - min(currentUnderlying, withdrawnAmount)

    log PerformanceFeesClaimed(pendingFees=pendingFees)
    return pendingFees


# claimable performance fees


@view
@external
def getClaimablePerformanceFees() -> uint256:
    newYield: uint256 = self._calcNewYieldAndGetUnderlying()[1]
    return (self.pendingYieldRealized + newYield) * self._getPerformanceFeeRatio(self._getVaultRegistry()) // HUNDRED_PERCENT


# get performance fee %


@view
@internal
def _getPerformanceFeeRatio(_vaultRegistry: address) -> uint256:
    return staticcall VaultRegistry(_vaultRegistry).getPerformanceFee(self)


#####################
# Underlying Assets #
#####################


@view
@internal
def _getUnderlyingYieldBalances() -> (uint256, uint256, address):
    numAssets: uint256 = self.numAssets
    if numAssets == 0:
        return 0, 0, empty(address)

    maxTotalAssets: uint256 = 0
    safeTotalAssets: uint256 = 0
    maxBalance: uint256 = 0
    maxBalVaultToken: address = empty(address)

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
        underlyingBalance: uint256 = 0
        if data.isRebasing:
            underlyingBalance = vaultTokenBalance # TODO: check that decimals match up with underlying asset !!
            safeTotalAssets += vaultTokenBalance

        else:
            legoAddr: address = staticcall Registry(legoBook).getAddr(data.legoId)

            # max possible balance
            pricePerShare: uint256 = staticcall Lego(legoAddr).getPricePerShare(vaultToken, data.vaultTokenDecimals)
            underlyingBalance = vaultTokenBalance * pricePerShare // (10 ** data.vaultTokenDecimals)

            # safe balance
            avgBalance: uint256 = vaultTokenBalance * data.avgPricePerShare // (10 ** data.vaultTokenDecimals)
            safeTotalAssets += min(avgBalance, underlyingBalance)

        maxTotalAssets += underlyingBalance

        # save max balance / token
        if underlyingBalance > maxBalance:
            maxBalance = underlyingBalance
            maxBalVaultToken = vaultToken

    return maxTotalAssets, safeTotalAssets, maxBalVaultToken


###################
# Redemption Prep #
###################


@internal
def _prepareRedemption(
    _amount: uint256,
    _maxBalVaultToken: address,
    _sender: address,
    _vaultRegistry: address,
) -> (uint256, uint256):
    availAmount: uint256 = staticcall IERC20(VAULT_ASSET).balanceOf(self)
    if availAmount >= _amount:
        return availAmount, 0

    # get redemption config (buffer and min withdraw amount)
    redemptionBuffer: uint256 = 0
    minWithdrawAmount: uint256 = 0
    redemptionBuffer, minWithdrawAmount = staticcall VaultRegistry(_vaultRegistry).redemptionConfig(self)

    # buffer to make sure we pull out enough for redemption
    bufferMultiplier: uint256 = HUNDRED_PERCENT + redemptionBuffer
    targetWithdrawAmount: uint256 = _amount * bufferMultiplier // HUNDRED_PERCENT

    withdrawnAmount: uint256 = 0
    ad: VaultActionData = staticcall VaultRegistry(_vaultRegistry).getVaultActionDataBundle(0, _sender)
    assetsToDeregister: DynArray[address, MAX_DEREGISTER_ASSETS] = []

    # first withdraw from biggest yield position
    if _maxBalVaultToken != empty(address):
        underlyingAmount: uint256 = 0
        needsDeregister: bool = False
        underlyingAmount, needsDeregister = self._withdrawDuringRedemption(_maxBalVaultToken, targetWithdrawAmount, availAmount, minWithdrawAmount, 0, ad)
        availAmount += underlyingAmount
        withdrawnAmount += underlyingAmount
        if needsDeregister:
            assetsToDeregister.append(_maxBalVaultToken)

    # next, iterate thru each yield position (order it is saved)
    if availAmount < targetWithdrawAmount:
        numAssets: uint256 = self.numAssets
        if numAssets != 0:
            for i: uint256 in range(1, numAssets, bound=max_value(uint256)):
                if availAmount >= targetWithdrawAmount:
                    break

                vaultToken: address = self.assets[i]
                if _maxBalVaultToken != empty(address) and vaultToken == _maxBalVaultToken:
                    continue

                # withdraw from yield opportunity
                underlyingAmount: uint256 = 0
                needsDeregister: bool = False
                underlyingAmount, needsDeregister = self._withdrawDuringRedemption(vaultToken, targetWithdrawAmount, availAmount, minWithdrawAmount, len(assetsToDeregister), ad)
                availAmount += underlyingAmount
                withdrawnAmount += underlyingAmount

                # add to deregister list
                if needsDeregister and vaultToken not in assetsToDeregister:
                    assetsToDeregister.append(vaultToken)

    # deregister vault positions
    for asset: address in assetsToDeregister:
        self._deregisterYieldPosition(asset)

    return availAmount, withdrawnAmount


@internal
def _withdrawDuringRedemption(
    _vaultToken: address,
    _targetWithdrawAmount: uint256,
    _availAmount: uint256,
    _minWithdrawAmount: uint256,
    _numDeregisterAssets: uint256,
    _ad: VaultActionData,
) -> (uint256, bool):
    if _vaultToken == empty(address):
        return 0, False

    vaultTokenBalance: uint256 = staticcall IERC20(_vaultToken).balanceOf(self)
    if vaultTokenBalance == 0:
        return 0, _numDeregisterAssets < MAX_DEREGISTER_ASSETS # need to deregister

    data: LocalVaultTokenData = self.assetData[_vaultToken]
    if data.legoId == 0 or data.vaultTokenDecimals == 0:
        return 0, False

    ad: VaultActionData = _ad
    ad.legoId = data.legoId
    ad.legoAddr = staticcall Registry(ad.legoBook).getAddr(data.legoId)

    # get price per share
    pricePerShare: uint256 = 0
    if data.isRebasing:
        pricePerShare = 10 ** data.vaultTokenDecimals
    else:
        pricePerShare = staticcall Lego(ad.legoAddr).getPricePerShare(_vaultToken, data.vaultTokenDecimals)

    # calculate how many vault tokens we need to withdraw
    amountStillNeeded: uint256 = _targetWithdrawAmount - _availAmount

    # skip if amount still needed is below minimum (dust protection)
    if _minWithdrawAmount != 0 and amountStillNeeded < _minWithdrawAmount:
        return 0, False

    # skip if vault tokens needed rounds to 0 (dust)
    vaultTokensNeeded: uint256 = amountStillNeeded * (10 ** data.vaultTokenDecimals) // pricePerShare
    if vaultTokensNeeded == 0:
        return 0, False

    # withdraw from yield opportunity
    underlyingAmount: uint256 = self._withdrawFromYield(_vaultToken, vaultTokensNeeded, empty(bytes32), 0, False, ad)[2]

    # add to deregister list
    needsDeregister: bool = False
    if vaultTokensNeeded >= vaultTokenBalance and staticcall IERC20(_vaultToken).balanceOf(self) == 0 and _numDeregisterAssets < MAX_DEREGISTER_ASSETS:
        needsDeregister = True

    return underlyingAmount, needsDeregister


###################
# Yield Positions #
###################


# update yield position


@external
def updateYieldPosition(_vaultToken: address):
    assert self._isSwitchboardAddr(msg.sender) # dev: no perms
    vaultRegistry: address = self._getVaultRegistry()
    legoId: uint256 = 0
    legoAddr: address = empty(address)
    legoId, legoAddr = staticcall VaultRegistry(vaultRegistry).getLegoDataFromVaultToken(_vaultToken)
    if legoId != 0 and legoAddr != empty(address):
        self._updateYieldPosition(_vaultToken, legoId, legoAddr, vaultRegistry)


@internal
def _updateYieldPosition(
    _vaultToken: address,
    _legoId: uint256,
    _legoAddr: address,
    _vaultRegistry: address,
):
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
        snapConfig: SnapShotPriceConfig = staticcall VaultRegistry(_vaultRegistry).snapShotPriceConfig(self)
        self._addPriceSnapshot(_vaultToken, _legoAddr, data.vaultTokenDecimals, snapConfig)
        data.avgPricePerShare = self._getWeightedPricePerShare(_vaultToken, snapConfig)
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
    config: SnapShotPriceConfig = staticcall VaultRegistry(self._getVaultRegistry()).snapShotPriceConfig(self)
    return self._getWeightedPricePerShare(_vaultToken, config)


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
    legoAddr: address = empty(address)
    config: SnapShotPriceConfig = empty(SnapShotPriceConfig)
    legoAddr, config = staticcall VaultRegistry(self._getVaultRegistry()).getLegoAndSnapshotConfig(_vaultToken, self)
    if legoAddr == empty(address):
        return False
    vaultTokenDecimals: uint256 = convert(staticcall IERC20Detailed(_vaultToken).decimals(), uint256)
    return self._addPriceSnapshot(_vaultToken, legoAddr, vaultTokenDecimals, config)


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
    legoAddr: address = empty(address)
    config: SnapShotPriceConfig = empty(SnapShotPriceConfig)
    legoAddr, config = staticcall VaultRegistry(self._getVaultRegistry()).getLegoAndSnapshotConfig(_vaultToken, self)
    if legoAddr == empty(address):
        return empty(SingleSnapShot)
    vaultTokenDecimals: uint256 = convert(staticcall IERC20Detailed(_vaultToken).decimals(), uint256)
    data: SnapShotData = self.snapShotData[_vaultToken]
    return self._getLatestSnapshot(_vaultToken, legoAddr, vaultTokenDecimals, data.lastSnapShot, config)


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

    # main data for this transaction - get action data and frozen status in single call
    legoId: uint256 = 0
    if len(_legoIds) != 0:
        legoId = _legoIds[0]

    vaultRegistry: address = self._getVaultRegistry()
    ad: VaultActionData = empty(VaultActionData)
    isVaultOpsFrozen: bool = False
    ad, isVaultOpsFrozen = staticcall VaultRegistry(vaultRegistry).getVaultActionDataWithFrozenStatus(legoId, _signer, self)

    # cannot perform any actions if vault is frozen
    assert not isVaultOpsFrozen # dev: frozen vault

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


#############
# Utilities #
#############


# get vault registry


@view
@internal
def _getVaultRegistry() -> address:
    return staticcall Registry(UNDY_HQ).getAddr(VAULT_REGISTRY_ID)


# is signer switchboard


@view
@internal
def _isSwitchboardAddr(_signer: address) -> bool:
    switchboard: address = staticcall Registry(UNDY_HQ).getAddr(SWITCHBOARD_ID)
    if switchboard == empty(address):
        return False
    return staticcall Switchboard(switchboard).isSwitchboardAddr(_signer)


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

