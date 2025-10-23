#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

from interfaces import Wallet as wi
from interfaces import LegoPartner as Lego
from interfaces import WalletStructs as ws

from ethereum.ercs import IERC4626
from ethereum.ercs import IERC20
from ethereum.ercs import IERC20Detailed

interface RipeLego:
    def getUsdValue(_asset: address, _amount: uint256, _shouldRaise: bool = False) -> uint256: view
    def getAssetAmount(_asset: address, _usdValue: uint256, _shouldRaise: bool = False) -> uint256: view
    def getCollateralBalance(_user: address, _asset: address) -> uint256: view
    def getUserDebtAmount(_user: address) -> uint256: view
    def savingsGreen() -> address: view

interface VaultRegistry:
    def getVaultActionDataWithFrozenStatus(_legoId: uint256, _signer: address, _vaultAddr: address) -> (VaultActionData, bool): view
    def getVaultActionDataBundle(_legoId: uint256, _signer: address) -> VaultActionData: view
    def redemptionConfig(_vaultAddr: address) -> (uint256, uint256): view

interface YieldLego:
    def getUnderlyingBalances(_vaultToken: address, _vaultTokenBalance: uint256) -> (uint256, uint256): view
    def getVaultTokenAmount(_asset: address, _assetAmount: uint256, _vaultToken: address) -> uint256: view
    def getUnderlyingAmount(_vaultToken: address, _vaultTokenAmount: uint256) -> uint256: view

interface Switchboard:
    def isSwitchboardAddr(_addr: address) -> bool: view

interface MissionControl:
    def isLockedSigner(_signer: address) -> bool: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

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

event EarnVaultAction:
    op: uint8
    asset1: indexed(address)
    asset2: indexed(address)
    amount1: uint256
    amount2: uint256
    usdValue: uint256
    legoId: uint256
    signer: indexed(address)

event UsdcSlippageAllowedSet:
    slippage: uint256

event GreenSlippageAllowedSet:
    slippage: uint256

vaultToLegoId: public(HashMap[address, uint256])

# main vault tokens
coreVaultToken: public(address) # core collateral - where base asset (WETH/CBBTC/USDC) is deposited (optional)
leverageVaultToken: public(address) # leverage yield - where borrowed GREEN → swapped USDC is deposited

# slippage settings
usdcSlippageAllowed: public(uint256) # basis points (100 = 1%)
greenSlippageAllowed: public(uint256) # basis points (100 = 1%)

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

# ids
RIPE_LEGO_ID: constant(uint256) = 1
LEGO_BOOK_ID: constant(uint256) = 3
SWITCHBOARD_ID: constant(uint256) = 4
VAULT_REGISTRY_ID: constant(uint256) = 10

UNDY_HQ: immutable(address)
UNDERLYING_ASSET: immutable(address)
USDC: immutable(address)
GREEN: immutable(address)
SAVINGS_GREEN: immutable(address)


@deploy
def __init__(
    _undyHq: address,
    _underlyingAsset: address,
    _coreVaultToken: address,
    _leverageVaultToken: address,
    _usdc: address,
    _green: address,
    _savingsGreen: address,
    _startingAgent: address,
):
    # not using 0 index
    self.numManagers = 1

    # main addys
    assert empty(address) not in [_undyHq, _underlyingAsset, _usdc, _green, _leverageVaultToken] # dev: inv addr
    UNDY_HQ = _undyHq
    UNDERLYING_ASSET = _underlyingAsset
    USDC = _usdc
    GREEN = _green
    SAVINGS_GREEN = _savingsGreen

    # main leverage vault token
    assert staticcall IERC4626(_leverageVaultToken).asset() == _usdc # dev: leverage vault token must be USDC
    self.leverageVaultToken = _leverageVaultToken

    # ripe collateral token (optional)
    if _coreVaultToken != empty(address):
        assert staticcall IERC4626(_coreVaultToken).asset() == _underlyingAsset # dev: core vault token must be underlying asset
        self.coreVaultToken = _coreVaultToken

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
    return self._depositForYield(_asset, _vaultAddr, _amount, _extraData, ad)


@internal
def _onReceiveVaultFunds(_depositor: address, _vaultRegistry: address) -> uint256:
    coreVaultToken: address = self.coreVaultToken
    legoId: uint256 = self.vaultToLegoId[coreVaultToken]
    ad: VaultActionData = staticcall VaultRegistry(_vaultRegistry).getVaultActionDataBundle(legoId, _depositor)
    if ad.legoId == 0 or ad.legoAddr == empty(address):
        return 0
    ad.vaultAsset = UNDERLYING_ASSET
    return self._depositForYield(ad.vaultAsset, coreVaultToken, max_value(uint256), empty(bytes32), ad)[0]


@internal
def _depositForYield(
    _asset: address,
    _vaultAddr: address,
    _amount: uint256,
    _extraData: bytes32,
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
    assert _vaultAddr == vaultToken # dev: vault token mismatch

    # vault asset must go into core vault
    if _asset == UNDERLYING_ASSET:
        assert vaultToken == self.coreVaultToken # dev: vault token mismatch

    # USDC must go into leverage vault
    elif _asset == USDC:
        assert vaultToken == self.leverageVaultToken # dev: vault token mismatch

    # GREEN must go into savings green
    elif _asset == GREEN:
        ripeLegoAddr: address = staticcall Registry(_ad.legoBook).getAddr(RIPE_LEGO_ID)
        assert vaultToken == staticcall RipeLego(ripeLegoAddr).savingsGreen() # dev: vault token mismatch

    # first time, need to save lego mapping
    if _ad.legoId != 0:
        self.vaultToLegoId[vaultToken] = _ad.legoId

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
    return self._withdrawFromYield(_vaultToken, _amount, _extraData, ad)


@internal
def _withdrawFromYield(
    _vaultToken: address,
    _amount: uint256,
    _extraData: bytes32,
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
    ad: VaultActionData = self._canManagerPerformAction(msg.sender, legoIds)

    # important checks!
    leverageVaultToken: address = self.leverageVaultToken
    savingsGreen: address = SAVINGS_GREEN
    assert tokenIn not in [ad.vaultAsset, self.coreVaultToken, leverageVaultToken, savingsGreen] # dev: invalid swap asset

    # pre swap validation
    green: address = GREEN
    usdc: address = USDC
    origAmountIn: uint256 = self._preSwapValidation(tokenIn, _instructions[0].amountIn, tokenOut, ad.vaultAsset, green, savingsGreen, usdc, leverageVaultToken, ad.legoBook)

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

    # post swap validation
    self._postSwapValidation(tokenIn, origAmountIn, lastTokenOut, lastTokenOutAmount, green, usdc, ad.legoBook)

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
    assert tokenIn != tokenOut # dev: same token
    return tokenIn, tokenOut, legoIds


# swap validation (GREEN/USDC)


@view
@internal
def _preSwapValidation(
    _tokenIn: address,
    _amountIn: uint256,
    _tokenOut: address,
    _vaultAsset: address,
    _green: address,
    _savingsGreen: address,
    _usdc: address,
    _leverageVaultToken: address,
    _legoBook: address,
) -> uint256:
    currentBalance: uint256 = staticcall IERC20(_usdc).balanceOf(self)

    amountIn: uint256 = _amountIn
    if _tokenIn == _green:
        assert _tokenOut == _usdc # dev: GREEN can only go to USDC
    elif _tokenIn == _usdc and _tokenOut != _green:
        assert _tokenOut == _vaultAsset # dev: must swap into vault asset
        amountIn = self._getSwappableUsdcAmount(_usdc, _amountIn, currentBalance, _leverageVaultToken, _green, _savingsGreen, _legoBook)

    finalAmount: uint256 = min(amountIn, currentBalance)
    assert finalAmount != 0 # dev: no amount to swap
    return finalAmount


@view
@internal
def _getSwappableUsdcAmount(
    _usdc: address,
    _amountIn: uint256,
    _currentBalance: uint256,
    _leverageVaultToken: address,
    _green: address,
    _savingsGreen: address,
    _legoBook: address,
) -> uint256:
    ripeLegoAddr: address = staticcall Registry(_legoBook).getAddr(RIPE_LEGO_ID)
    userDebtAmount: uint256 = staticcall RipeLego(ripeLegoAddr).getUserDebtAmount(self) # 18 decimals
    if userDebtAmount == 0:
        return _amountIn

    # usdc balance
    usdcAmount: uint256 = _currentBalance
    usdcAmount += self._getUnderlyingAmount(_leverageVaultToken, _legoBook, ripeLegoAddr) # 6 decimals
    usdcValue: uint256 = staticcall RipeLego(ripeLegoAddr).getUsdValue(_usdc, usdcAmount, True) # 18 decimals

    # green amount
    greenSurplusAmount: uint256 = self._getTotalGreenAmount(_green, _savingsGreen, ripeLegoAddr)
    positiveValue: uint256 = greenSurplusAmount + usdcValue # treat green as $1 USD (most conservative, in this case)

    # compare usd values
    if userDebtAmount > positiveValue:
        return 0

    availUsdcAmount: uint256 = staticcall RipeLego(ripeLegoAddr).getAssetAmount(_usdc, positiveValue - userDebtAmount, True) # 6 decimals
    return min(availUsdcAmount, _amountIn)


@view
@internal
def _postSwapValidation(
    _tokenIn: address,
    _tokenInAmount: uint256,
    _tokenOut: address,
    _tokenOutAmount: uint256,
    _green: address,
    _usdc: address,
    _legoBook: address,
):
    # GREEN -> USDC swap validation
    if _tokenIn == _green and _tokenOut == _usdc:
        slippage: uint256 = self.usdcSlippageAllowed

        # Get USD value of USDC received (18 decimals)
        ripeLegoAddr: address = staticcall Registry(_legoBook).getAddr(RIPE_LEGO_ID)
        usdcValue: uint256 = staticcall RipeLego(ripeLegoAddr).getUsdValue(_usdc, _tokenOutAmount, True)

        # Minimum expected: greenAmount * (10000 - slippage) / 10000
        # GREEN is 18 decimals and treated as $1 USD, so greenAmount = USD value
        minExpected: uint256 = _tokenInAmount * (HUNDRED_PERCENT - slippage) // HUNDRED_PERCENT
        assert usdcValue >= minExpected # dev: too much slippage

    # USDC -> GREEN swap validation
    elif _tokenIn == _usdc and _tokenOut == _green:
        slippage: uint256 = self.greenSlippageAllowed

        # Get USD value of USDC sent (18 decimals)
        ripeLegoAddr: address = staticcall Registry(_legoBook).getAddr(RIPE_LEGO_ID)
        usdcValue: uint256 = staticcall RipeLego(ripeLegoAddr).getUsdValue(_usdc, _tokenInAmount, True)

        # Minimum expected: usdcValue * (10000 - slippage) / 10000
        minExpected: uint256 = usdcValue * (HUNDRED_PERCENT - slippage) // HUNDRED_PERCENT
        assert _tokenOutAmount >= minExpected # dev: too much slippage


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


###################
# Debt Management #
###################


# add collateral


@external
def addCollateral(
    _legoId: uint256,
    _asset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256):
    ad: VaultActionData = self._canManagerPerformAction(msg.sender, [_legoId])
    return self._addCollateral(_asset, _amount, _extraData, ad)


@internal
def _addCollateral(
    _asset: address,
    _amount: uint256,
    _extraData: bytes32,
    _ad: VaultActionData,
) -> (uint256, uint256):
    self._setLegoAccessForAction(_ad.legoAddr, ws.ActionType.ADD_COLLATERAL)
    assert extcall IERC20(_asset).approve(_ad.legoAddr, max_value(uint256), default_return_value = True) # dev: appr

    # validate collateral + lego id
    assert _ad.legoId == RIPE_LEGO_ID # dev: invalid lego id
    assert _asset in [UNDERLYING_ASSET, self.leverageVaultToken, self.coreVaultToken, staticcall RipeLego(_ad.legoAddr).savingsGreen()] # dev: invalid collateral

    # add collateral
    amount: uint256 = self._getAmountAndApprove(_asset, _amount, empty(address)) # not approving here
    amountDeposited: uint256 = 0
    txUsdValue: uint256 = 0
    amountDeposited, txUsdValue = extcall Lego(_ad.legoAddr).addCollateral(_asset, amount, _extraData, self, self._packMiniAddys(_ad.ledger, _ad.missionControl, _ad.legoBook, _ad.appraiser))
    assert extcall IERC20(_asset).approve(_ad.legoAddr, 0, default_return_value = True) # dev: appr

    log EarnVaultAction(
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
    return self._removeCollateral(_asset, _amount, _extraData, ad)


@internal
def _removeCollateral(
    _asset: address,
    _amount: uint256,
    _extraData: bytes32,
    _ad: VaultActionData,
) -> (uint256, uint256):
    self._setLegoAccessForAction(_ad.legoAddr, ws.ActionType.REMOVE_COLLATERAL)

    # remove collateral
    amountRemoved: uint256 = 0
    txUsdValue: uint256 = 0
    amountRemoved, txUsdValue = extcall Lego(_ad.legoAddr).removeCollateral(_asset, _amount, _extraData, self, self._packMiniAddys(_ad.ledger, _ad.missionControl, _ad.legoBook, _ad.appraiser))

    log EarnVaultAction(
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
    return self._borrow(_borrowAsset, _amount, _extraData, ad)


@internal
def _borrow(
    _borrowAsset: address,
    _amount: uint256,
    _extraData: bytes32,
    _ad: VaultActionData,
) -> (uint256, uint256):
    self._setLegoAccessForAction(_ad.legoAddr, ws.ActionType.BORROW)

    # borrow
    borrowAmount: uint256 = 0
    txUsdValue: uint256 = 0
    borrowAmount, txUsdValue = extcall Lego(_ad.legoAddr).borrow(_borrowAsset, _amount, _extraData, self, self._packMiniAddys(_ad.ledger, _ad.missionControl, _ad.legoBook, _ad.appraiser))

    log EarnVaultAction(
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
    return self._repayDebt(_paymentAsset, _paymentAmount, _extraData, ad)


@internal
def _repayDebt(
    _paymentAsset: address,
    _paymentAmount: uint256,
    _extraData: bytes32,
    _ad: VaultActionData,
) -> (uint256, uint256):
    self._setLegoAccessForAction(_ad.legoAddr, ws.ActionType.REPAY_DEBT)

    # repay debt
    amount: uint256 = self._getAmountAndApprove(_paymentAsset, _paymentAmount, _ad.legoAddr) # doing approval here
    repaidAmount: uint256 = 0
    txUsdValue: uint256 = 0
    repaidAmount, txUsdValue = extcall Lego(_ad.legoAddr).repayDebt(_paymentAsset, amount, _extraData, self, self._packMiniAddys(_ad.ledger, _ad.missionControl, _ad.legoBook, _ad.appraiser))
    assert extcall IERC20(_paymentAsset).approve(_ad.legoAddr, 0, default_return_value = True) # dev: appr

    log EarnVaultAction(
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


#####################
# Underlying Assets #
#####################


@view
@internal
def _getTotalAssets() -> uint256:
    legoBook: address = staticcall Registry(UNDY_HQ).getAddr(LEGO_BOOK_ID)
    ripeLegoAddr: address = staticcall Registry(legoBook).getAddr(RIPE_LEGO_ID)
    underlyingAsset: address = UNDERLYING_ASSET

    # usdc vault
    usdc: address = USDC
    if underlyingAsset == usdc:
        return self._getTotalAssetsForUsdcVault(usdc, GREEN, SAVINGS_GREEN, legoBook, ripeLegoAddr)

    # TODO: implement

    return 0



@view
@internal
def _getTotalAssetsForUsdcVault(_usdc: address, _green: address, _savingsGreen: address, _legoBook: address, _ripeLegoAddr: address) -> uint256:
    usdcAmount: uint256 = staticcall IERC20(_usdc).balanceOf(self)

    # leverage vault amount
    leverageVaultToken: address = self.leverageVaultToken
    usdcAmount += self._getUnderlyingAmount(leverageVaultToken, _legoBook, _ripeLegoAddr)

    # core vault amount
    coreVaultToken: address = self.coreVaultToken
    if coreVaultToken != empty(address) and coreVaultToken != leverageVaultToken:
        usdcAmount += self._getUnderlyingAmount(coreVaultToken, _legoBook, _ripeLegoAddr)

    # green amounts
    userDebtAmount: uint256 = staticcall RipeLego(_ripeLegoAddr).getUserDebtAmount(self) # 18 decimals
    greenSurplusAmount: uint256 = self._getTotalGreenAmount(_green, _savingsGreen, _ripeLegoAddr)

    # adjust usdc values based on green situation
    if userDebtAmount > greenSurplusAmount:
        userDebtAmount -= greenSurplusAmount # treat green as $1 USD (most conservative, in this case)
        usdcAmount -= min(usdcAmount, userDebtAmount // (10 ** 12)) # normalize to 6 decimals
    elif greenSurplusAmount > userDebtAmount:
        extraGreen: uint256 = greenSurplusAmount - userDebtAmount
        usdValueOfGreen: uint256 = min(staticcall RipeLego(_ripeLegoAddr).getUsdValue(_green, extraGreen, True), extraGreen) # both 18 decimals
        usdcAmount += staticcall RipeLego(_ripeLegoAddr).getAssetAmount(_usdc, usdValueOfGreen, True)

    return usdcAmount


@view
@internal
def _getUnderlyingAmount(
    _vaultToken: address,
    _legoBook: address,
    _ripeLegoAddr: address,
) -> uint256:
    if _vaultToken == empty(address):
        return 0

    # ripe collateral balance or idle in vault
    vaultTokenAmount: uint256 = staticcall RipeLego(_ripeLegoAddr).getCollateralBalance(self, _vaultToken)
    vaultTokenAmount += staticcall IERC20(_vaultToken).balanceOf(self)
    if vaultTokenAmount == 0:
        return 0

    # calc underlying amount
    underlyingAmount: uint256 = 0
    legoId: uint256 = self.vaultToLegoId[_vaultToken]
    legoAddr: address = staticcall Registry(_legoBook).getAddr(legoId)
    if legoAddr != empty(address):
        underlyingAmount = staticcall YieldLego(legoAddr).getUnderlyingAmount(_vaultToken, vaultTokenAmount)
    
    return underlyingAmount


@view
@internal
def _getTotalGreenAmount(_green: address, _savingsGreen: address, _ripeLegoAddr: address) -> uint256:
    greenAmount: uint256 = staticcall IERC20(_green).balanceOf(self)

    # calc savings green
    savingsGreenAmount: uint256 = staticcall RipeLego(_ripeLegoAddr).getCollateralBalance(self, _savingsGreen)
    savingsGreenAmount += staticcall IERC20(_savingsGreen).balanceOf(self)
    if savingsGreenAmount != 0:
        greenAmount += staticcall YieldLego(_ripeLegoAddr).getUnderlyingAmount(_savingsGreen, savingsGreenAmount)

    return greenAmount


###################
# Redemption Prep #
###################


@internal
def _prepareRedemption(
    _asset: address,
    _amount: uint256,
    _sender: address,
    _vaultRegistry: address,
) -> uint256:
    availAmount: uint256 = staticcall IERC20(_asset).balanceOf(self)
    if availAmount >= _amount:
        return availAmount

    # get redemption config (buffer and min withdraw amount)
    redemptionBuffer: uint256 = 0
    minWithdrawAmount: uint256 = 0
    redemptionBuffer, minWithdrawAmount = staticcall VaultRegistry(_vaultRegistry).redemptionConfig(self)

    # buffer to make sure we pull out enough for redemption
    bufferMultiplier: uint256 = HUNDRED_PERCENT + redemptionBuffer
    targetWithdrawAmount: uint256 = _amount * bufferMultiplier // HUNDRED_PERCENT

    withdrawnAmount: uint256 = 0
    ad: VaultActionData = staticcall VaultRegistry(_vaultRegistry).getVaultActionDataBundle(0, _sender)
    ad.vaultAsset = _asset

    # TODO: implement
    # if vault token, calc vault token amount to withdraw from Ripe (with buffer), then withdraw from yield opportunity
    # if not vault token, withdraw from Ripe

    return availAmount


###############
# Core Vaults #
###############


@external
def setCoreVaults(_vaultToken: address, _isCore: bool):
    assert self._isSwitchboardAddr(msg.sender) # dev: no perms
    assert _vaultToken != empty(address) # dev: invalid vault token

    # TODO: implement


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
    ad.vaultAsset = UNDERLYING_ASSET

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


#####################
# Slippage Settings #
#####################


@external
def setUsdcSlippageAllowed(_slippage: uint256):
    assert self._isSwitchboardAddr(msg.sender) # dev: no perms
    assert _slippage <= HUNDRED_PERCENT # dev: slippage too high
    self.usdcSlippageAllowed = _slippage
    log UsdcSlippageAllowedSet(slippage = _slippage)


@external
def setGreenSlippageAllowed(_slippage: uint256):
    assert self._isSwitchboardAddr(msg.sender) # dev: no perms
    assert _slippage <= HUNDRED_PERCENT # dev: slippage too high
    self.greenSlippageAllowed = _slippage
    log GreenSlippageAllowedSet(slippage = _slippage)


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

