#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3
# pragma optimize codesize

from interfaces import Wallet as wi
from interfaces import LegoPartner as Lego
from interfaces import WalletStructs as ws

from ethereum.ercs import IERC20
from ethereum.ercs import IERC20Detailed
from ethereum.ercs import IERC4626

interface RipeLego:
    def getAssetAmount(_asset: address, _usdValue: uint256, _shouldRaise: bool = False) -> uint256: view
    def getMaxWithdrawableForAsset(_user: address, _asset: address) -> uint256: view
    def prepareGreenToUsdcSwap(_greenAmount: uint256) -> wi.SwapInstruction: view
    def prepareUsdcToGreenSwap(_usdcAmount: uint256) -> wi.SwapInstruction: view
    def getCollateralBalance(_user: address, _asset: address) -> uint256: view
    def getCollateralValue(_user: address) -> uint256: view
    def getUserDebtAmount(_user: address) -> uint256: view
    def RIPE_GREEN_TOKEN() -> address: view

interface VaultRegistry:
    def targetCollateralizationRatio(_vaultAddr: address) -> uint256: view
    def redemptionConfig(_vaultAddr: address) -> (uint256, uint256): view
    def isVaultOpsFrozen(_vaultAddr: address) -> bool: view

interface MissionControl:
    def canPerformSecurityAction(_addr: address) -> bool: view
    def isLockedSigner(_signer: address) -> bool: view

interface Switchboard:
    def isSwitchboardAddr(_addr: address) -> bool: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

struct VaultActionData:
    ledger: address
    missionControl: address
    legoBook: address
    appraiser: address
    vaultRegistry: address
    signer: address
    legoId: uint256
    legoAddr: address

event LeverageVaultAction:
    op: uint8 
    asset1: indexed(address)
    asset2: indexed(address)
    amount1: uint256
    amount2: uint256
    usdValue: uint256
    legoId: uint256
    signer: indexed(address)

# managers
managers: public(HashMap[uint256, address]) # index -> manager
indexOfManager: public(HashMap[address, uint256]) # manager -> index
numManagers: public(uint256) # num managers

# constants
RIPE_LEGO_ID: constant(uint256) = 1
MAX_SWAP_INSTRUCTIONS: constant(uint256) = 5
MAX_TOKEN_PATH: constant(uint256) = 5
MAX_LEGOS: constant(uint256) = 10
MAX_DELEVERAGE_ITERATIONS: constant(uint256) = 10
DEFAULT_TARGET_COLLATERALIZATION: constant(uint256) = 200_00  # 200%
HUNDRED_PERCENT: constant(uint256) = 100_00

# registry ids
LEDGER_ID: constant(uint256) = 1
MISSION_CONTROL_ID: constant(uint256) = 2
LEGO_BOOK_ID: constant(uint256) = 3
SWITCHBOARD_ID: constant(uint256) = 4
APPRAISER_ID: constant(uint256) = 7
VAULT_REGISTRY_ID: constant(uint256) = 10

UNDY_HQ: immutable(address)
UNDERLYING_ASSET: immutable(address)
YIELD_VAULT_ASSET: immutable(address)
YIELD_VAULT_DECIMALS: immutable(uint256)
YIELD_VAULT_LEGO_ID: immutable(uint256)
GREEN_TOKEN: immutable(address)


@deploy
def __init__(
    _undyHq: address,
    _asset: address,
    _yieldVaultAsset: address,
    _yieldVaultLegoId: uint256,
    _startingAgent: address,
):
    # not using 0 index
    self.numManagers = 1

    assert empty(address) not in [_undyHq, _asset, _yieldVaultAsset] # dev: inv addr
    UNDY_HQ = _undyHq
    UNDERLYING_ASSET = _asset
    YIELD_VAULT_ASSET = _yieldVaultAsset
    YIELD_VAULT_DECIMALS = convert(staticcall IERC20Detailed(_yieldVaultAsset).decimals(), uint256)
    YIELD_VAULT_LEGO_ID = _yieldVaultLegoId

    # get GREEN token from RipeLego
    legoBook: address = staticcall Registry(_undyHq).getAddr(LEGO_BOOK_ID)
    ripeLego: address = staticcall Registry(legoBook).getAddr(RIPE_LEGO_ID)
    GREEN_TOKEN = staticcall RipeLego(ripeLego).RIPE_GREEN_TOKEN()

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

    # update yield position (single position only)
    if _asset == UNDERLYING_ASSET:
        assert _vaultAddr == YIELD_VAULT_ASSET # dev: vault addr mismatch

    if _shouldGenerateEvent:
        log LeverageVaultAction(
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

    if _shouldGenerateEvent:
        log LeverageVaultAction(
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
    assert tokenIn not in [UNDERLYING_ASSET, YIELD_VAULT_ASSET] # dev: invalid swap in token
    assert tokenOut == UNDERLYING_ASSET # dev: must swap into vault asset

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

    log LeverageVaultAction(
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


@internal
def _deleverageSwap(_instruction: wi.SwapInstruction, _ad: VaultActionData) -> (address, uint256, address, uint256):
    tokenIn: address = _instruction.tokenPath[0]
    amountIn: uint256 = self._getAmountAndApprove(tokenIn, _instruction.amountIn, empty(address)) # not approving here

    tokenOut: address = empty(address)
    tokenOutAmount: uint256 = 0
    na: uint256 = 0
    tokenOut, tokenOutAmount, na = self._performSwapInstruction(amountIn, _instruction, _ad)
    return tokenIn, amountIn, tokenOut, tokenOutAmount


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

    log LeverageVaultAction(
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


###################
# Debt Management #
###################


# NOTE: these functions assume there is no receipt token after deposit (i.e. Ripe Protocol)
# You can also use `depositForYield` and `withdrawFromYield` if a vault token is involved


# add collateral


@external
def addCollateral(
    _legoId: uint256,
    _asset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256):
    ad: VaultActionData = self._canManagerPerformAction(msg.sender, [_legoId])
    return self._addCollateral(ad, _asset, _amount, _extraData)


@internal
def _addCollateral(
    _ad: VaultActionData,
    _asset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256):
    assert _ad.legoId == RIPE_LEGO_ID # dev: invalid lego id
    assert _asset == YIELD_VAULT_ASSET # dev: asset mismatch

    # some vault tokens require max value approval (comp v3)
    assert extcall IERC20(_asset).approve(_ad.legoAddr, max_value(uint256), default_return_value = True) # dev: appr

    # add collateral
    amount: uint256 = self._getAmountAndApprove(_asset, _amount, empty(address)) # not approving here
    amountDeposited: uint256 = 0
    txUsdValue: uint256 = 0
    amountDeposited, txUsdValue = extcall Lego(_ad.legoAddr).addCollateral(_asset, amount, _extraData, self, self._packMiniAddys(_ad.ledger, _ad.missionControl, _ad.legoBook, _ad.appraiser))
    assert extcall IERC20(_asset).approve(_ad.legoAddr, 0, default_return_value = True) # dev: appr

    log LeverageVaultAction(
        op = 40,
        asset1 = _asset,
        asset2 = empty(address),
        amount1 = amountDeposited,
        amount2 = 0,
        usdValue = txUsdValue,
        legoId = _ad.legoId,
        signer = _ad.signer,
    )
    return amountDeposited, txUsdValue


# remove collateral


@external
def removeCollateral(
    _legoId: uint256,
    _asset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256):
    ad: VaultActionData = self._canManagerPerformAction(msg.sender, [_legoId])
    return self._removeCollateral(ad, _asset, _amount, _extraData)


@internal
def _removeCollateral(
    _ad: VaultActionData,
    _asset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256):
    assert _ad.legoId == RIPE_LEGO_ID # dev: invalid lego id
    assert _asset == YIELD_VAULT_ASSET # dev: asset mismatch

    # remove collateral
    amountRemoved: uint256 = 0
    txUsdValue: uint256 = 0
    amountRemoved, txUsdValue = extcall Lego(_ad.legoAddr).removeCollateral(_asset, _amount, _extraData, self, self._packMiniAddys(_ad.ledger, _ad.missionControl, _ad.legoBook, _ad.appraiser))

    log LeverageVaultAction(
        op = 41,
        asset1 = _asset,
        asset2 = empty(address),
        amount1 = amountRemoved,
        amount2 = 0,
        usdValue = txUsdValue,
        legoId = _ad.legoId,
        signer = _ad.signer,
    )
    return amountRemoved, txUsdValue


# borrow


@external
def borrow(
    _legoId: uint256,
    _borrowAsset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256):
    ad: VaultActionData = self._canManagerPerformAction(msg.sender, [_legoId])
    return self._borrow(ad, _borrowAsset, _amount, _extraData)


@internal
def _borrow(
    _ad: VaultActionData,
    _borrowAsset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256):
    borrowAmount: uint256 = 0
    txUsdValue: uint256 = 0
    borrowAmount, txUsdValue = extcall Lego(_ad.legoAddr).borrow(_borrowAsset, _amount, _extraData, self, self._packMiniAddys(_ad.ledger, _ad.missionControl, _ad.legoBook, _ad.appraiser))

    log LeverageVaultAction(
        op = 42,
        asset1 = _borrowAsset,
        asset2 = empty(address),
        amount1 = borrowAmount,
        amount2 = 0,
        usdValue = txUsdValue,
        legoId = _ad.legoId,
        signer = _ad.signer,
    )
    return borrowAmount, txUsdValue


# repay debt


@external
def repayDebt(
    _legoId: uint256,
    _paymentAsset: address,
    _paymentAmount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256):
    ad: VaultActionData = self._canManagerPerformAction(msg.sender, [_legoId])
    return self._repayDebt(ad, _paymentAsset, _paymentAmount, _extraData)


@internal
def _repayDebt(
    _ad: VaultActionData,
    _paymentAsset: address,
    _paymentAmount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256):
    amount: uint256 = self._getAmountAndApprove(_paymentAsset, _paymentAmount, _ad.legoAddr) # doing approval here
    repaidAmount: uint256 = 0
    txUsdValue: uint256 = 0
    repaidAmount, txUsdValue = extcall Lego(_ad.legoAddr).repayDebt(_paymentAsset, amount, _extraData, self, self._packMiniAddys(_ad.ledger, _ad.missionControl, _ad.legoBook, _ad.appraiser))
    assert extcall IERC20(_paymentAsset).approve(_ad.legoAddr, 0, default_return_value = True) # dev: appr

    log LeverageVaultAction(
        op = 43,
        asset1 = _paymentAsset,
        asset2 = empty(address),
        amount1 = repaidAmount,
        amount2 = 0,
        usdValue = txUsdValue,
        legoId = _ad.legoId,
        signer = _ad.signer,
    )
    return repaidAmount, txUsdValue


################
# Total Assets #
################


@view
@external
def getTotalAssets() -> uint256:
    return self._getTotalAssets()


@view
@internal
def _getTotalAssets() -> uint256:
    vaultToken: address = YIELD_VAULT_ASSET
    underlyingAsset: address = UNDERLYING_ASSET

    # 1. loose underlying asset balance
    totalAssets: uint256 = staticcall IERC20(underlyingAsset).balanceOf(self)

    # 2. vault tokens in wallet
    vaultTokenBalance: uint256 = staticcall IERC20(vaultToken).balanceOf(self)

    # 3. collateral position (vault tokens deposited as collateral)
    legoBook: address = staticcall Registry(UNDY_HQ).getAddr(LEGO_BOOK_ID)
    legoAddr: address = staticcall Registry(legoBook).getAddr(RIPE_LEGO_ID)
    vaultTokenBalance += staticcall RipeLego(legoAddr).getCollateralBalance(self, vaultToken)

    # calculate total assets
    if vaultTokenBalance != 0:
        totalAssets += staticcall IERC4626(vaultToken).convertToAssets(vaultTokenBalance)

    # NOTE: GREEN is treated as $1 in Ripe, so we don't need to normalize anything
    debtAmount: uint256 = staticcall RipeLego(legoAddr).getUserDebtAmount(self)
    if debtAmount != 0:
        underlyingDebtAmount: uint256 = staticcall RipeLego(legoAddr).getAssetAmount(underlyingAsset, debtAmount, True)
        assert underlyingDebtAmount != 0 # dev: invalid debt amount
        totalAssets -= min(underlyingDebtAmount, totalAssets)

    return totalAssets


###################
# Redemption Prep #
###################


@view
@internal
def _calculateDebtRepayment(
    _collateralValue: uint256,
    _debtAmount: uint256,
    _withdrawnCollateral: uint256,
    _targetRatio: uint256,
) -> uint256:
    # After withdrawing collateral, calculate how much debt to repay
    # to maintain target collateralization ratio

    # Convert withdrawn collateral to USD value
    withdrawnValue: uint256 = staticcall IERC4626(YIELD_VAULT_ASSET).convertToAssets(_withdrawnCollateral)
    newCollateralValue: uint256 = _collateralValue - withdrawnValue

    # Target: newCollateralValue / newDebt = targetRatio
    # newDebt = newCollateralValue * HUNDRED_PERCENT / targetRatio
    targetDebt: uint256 = newCollateralValue * HUNDRED_PERCENT // _targetRatio

    if _debtAmount <= targetDebt:
        return 0  # already at or below target

    return _debtAmount - targetDebt


@internal
def _prepareRedemption(_amount: uint256, _sender: address, _vaultRegistry: address) -> uint256:
    underlyingAsset: address = UNDERLYING_ASSET
    yieldVaultAsset: address = YIELD_VAULT_ASSET
    greenToken: address = GREEN_TOKEN

    withdrawnAmount: uint256 = staticcall IERC20(underlyingAsset).balanceOf(self)
    if withdrawnAmount >= _amount:
        return _amount

    # get redemption config (buffer and min withdraw amount)
    redemptionBuffer: uint256 = 0
    minWithdrawAmount: uint256 = 0
    redemptionBuffer, minWithdrawAmount = staticcall VaultRegistry(_vaultRegistry).redemptionConfig(self)

    # buffer to make sure we pull out enough for redemption
    bufferMultiplier: uint256 = HUNDRED_PERCENT + redemptionBuffer
    targetWithdrawAmount: uint256 = _amount * bufferMultiplier // HUNDRED_PERCENT

    # addrs
    ripeAd: VaultActionData = self._getVaultActionDataBundle(RIPE_LEGO_ID, _sender)
    yieldAd: VaultActionData = ripeAd
    yieldAd.legoAddr = staticcall Registry(ripeAd.legoBook).getAddr(YIELD_VAULT_LEGO_ID)
    yieldAd.legoId = YIELD_VAULT_LEGO_ID

    # withdraw from yield vault -- if applicable
    vaultTokenBalance: uint256 = staticcall IERC20(yieldVaultAsset).balanceOf(self)
    if vaultTokenBalance != 0:
        amountStillNeeded: uint256 = targetWithdrawAmount - withdrawnAmount
        pricePerShare: uint256 = staticcall IERC4626(yieldVaultAsset).convertToAssets(10 ** YIELD_VAULT_DECIMALS)
        vaultTokensNeeded: uint256 = amountStillNeeded * (10 ** YIELD_VAULT_DECIMALS) // pricePerShare

        # withdraw from yield opportunity
        na1: uint256 = 0
        na2: address = empty(address)
        underlyingAmount: uint256 = 0
        na3: uint256 = 0
        if vaultTokensNeeded != 0:
            na1, na2, underlyingAmount, na3 = self._withdrawFromYield(yieldVaultAsset, vaultTokensNeeded, empty(bytes32), True, yieldAd)

        # add to withdrawn amount
        withdrawnAmount += underlyingAmount
        if withdrawnAmount >= _amount:
            return _amount







    # Get target collateralization ratio from registry
    targetRatio: uint256 = staticcall VaultRegistry(_vaultRegistry).targetCollateralizationRatio(self)
    if targetRatio == 0:
        targetRatio = DEFAULT_TARGET_COLLATERALIZATION  # fallback to 200%

    # De-leverage loop - MUST get the full amount
    for i: uint256 in range(MAX_DELEVERAGE_ITERATIONS):
        freedAmount: uint256 = staticcall IERC20(underlyingAsset).balanceOf(self)

        # Success: we have enough
        if freedAmount >= _amount:
            return _amount

        # Get current position
        collateralValue: uint256 = staticcall RipeLego(ripeAd.legoAddr).getCollateralValue(self)
        debtAmount: uint256 = staticcall RipeLego(ripeAd.legoAddr).getUserDebtAmount(self)

        # Check if position is fully unwound
        if collateralValue == 0 and debtAmount == 0:
            # This should never happen - means vault is insolvent
            # But we've extracted everything possible
            assert False  # dev: insufficient liquidity

        # Calculate withdrawal maintaining target ratio
        maxWithdrawable: uint256 = staticcall RipeLego(ripeAd.legoAddr).getMaxWithdrawableForAsset(self, yieldVaultAsset)

        # # If we can't withdraw anything, position is at liquidation risk
        # # We need to repay debt first without withdrawing
        # if maxWithdrawable == 0:
        #     # Emergency: repay debt with whatever underlying we have
        #     underlyingBalance: uint256 = staticcall IERC20(underlyingAsset).balanceOf(self)
        #     if underlyingBalance > 0:
        #         extcall self.repayDebt(RIPE_LEGO_ID, underlyingAsset, underlyingBalance, empty(bytes32))
        #         continue
        #     else:
        #         assert False  # dev: cannot deleverage

        # Step 1: Remove max collateral
        self._removeCollateral(yieldAd, yieldVaultAsset, maxWithdrawable, empty(bytes32))

        # Step 2: Withdraw from yield vault to get underlying asset
        self._withdrawFromYield(yieldVaultAsset, max_value(uint256), empty(bytes32), False, yieldAd)

        # Step 3: Calculate how much debt to repay to maintain target ratio
        newDebtToRepay: uint256 = self._calculateDebtRepayment(
            collateralValue,
            debtAmount,
            maxWithdrawable,
            targetRatio,
        )

        if newDebtToRepay > 0:
            # Swap underlying (USDC) → GREEN to get GREEN for debt repayment
            underlyingBalance: uint256 = staticcall IERC20(underlyingAsset).balanceOf(self)

            # Only swap what we need for debt repayment (keep rest for redemption)
            amountToSwap: uint256 = min(newDebtToRepay, underlyingBalance)

            if amountToSwap > 0:
                swapInstruction: wi.SwapInstruction = staticcall RipeLego(ripeAd.legoAddr).prepareUsdcToGreenSwap(amountToSwap)
                self._deleverageSwap(swapInstruction, ripeAd)

                # Repay GREEN debt with GREEN we just swapped
                greenBalance: uint256 = staticcall IERC20(greenToken).balanceOf(self)
                if greenBalance > 0:
                    self._repayDebt(ripeAd, greenToken, greenBalance, empty(bytes32))

    # If we exit the loop without returning, we hit max iterations
    # This should never happen with proper target ratio
    assert False  # dev: max deleverage iterations reached
    return 0


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
    isVaultOpsFrozen: bool = staticcall VaultRegistry(self._getVaultRegistry()).isVaultOpsFrozen(self)
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