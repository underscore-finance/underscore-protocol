#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

from interfaces import Wallet as wi
from interfaces import LegoPartner as Lego
from interfaces import WalletStructs as ws

from ethereum.ercs import IERC20

interface LevgVaultHelper:
    def getTotalAssetsForNonUsdcVault(_wallet: address, _underlyingAsset: address, _collateralVaultToken: address, _collateralVaultTokenLegoId: uint256, _leverageVaultToken: address, _leverageVaultTokenLegoId: uint256, _usdc: address = empty(address), _green: address = empty(address), _savingsGreen: address = empty(address), _legoBook: address = empty(address)) -> uint256: view
    def getTotalAssetsForUsdcVault(_wallet: address, _collateralVaultToken: address, _collateralVaultTokenLegoId: uint256, _leverageVaultToken: address, _leverageVaultTokenLegoId: uint256, _usdc: address = empty(address), _green: address = empty(address), _savingsGreen: address = empty(address), _legoBook: address = empty(address)) -> uint256: view
    def getSwappableUsdcAmount(_wallet: address, _amountIn: uint256, _currentBalance: uint256, _leverageVaultToken: address, _leverageVaultTokenLegoId: uint256, _usdc: address = empty(address), _green: address = empty(address), _savingsGreen: address = empty(address), _legoBook: address = empty(address)) -> uint256: view
    def performPostSwapValidation(_tokenIn: address, _tokenInAmount: uint256, _tokenOut: address, _tokenOutAmount: uint256, _usdcSlippageAllowed: uint256, _greenSlippageAllowed: uint256, _usdc: address = empty(address), _green: address = empty(address)) -> bool: view
    def getCollateralBalance(_user: address, _asset: address) -> uint256: view
    def isSupportedRipeAsset(_asset: address) -> bool: view

interface VaultRegistry:
    def getVaultActionDataWithFrozenStatus(_legoId: uint256, _signer: address, _vaultAddr: address) -> (VaultActionData, bool): view
    def getVaultActionDataBundle(_legoId: uint256, _signer: address) -> VaultActionData: view
    def redemptionBuffer(_vaultAddr: address) -> uint256: view

interface YieldLego:
    def getVaultTokenAmount(_asset: address, _assetAmount: uint256, _vaultToken: address) -> uint256: view
    def canRegisterVaultToken(_asset: address, _vaultToken: address) -> bool: view

interface MissionControl:
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
    vaultAsset: address
    signer: address
    legoId: uint256
    legoAddr: address

event LevgVaultAction:
    op: uint8
    asset1: indexed(address)
    asset2: indexed(address)
    amount1: uint256
    amount2: uint256
    usdValue: uint256
    legoId: uint256
    signer: indexed(address)

event CollateralVaultTokenSet:
    collateralVaultToken: indexed(address)

event LeverageVaultTokenSet:
    leverageVaultToken: indexed(address)

event UsdcSlippageAllowedSet:
    slippage: uint256

event GreenSlippageAllowedSet:
    slippage: uint256

event LevgVaultHelperSet:
    levgVaultHelper: indexed(address)

vaultToLegoId: public(HashMap[address, uint256])
levgVaultHelper: public(address)

# vault tokens
collateralVaultToken: public(address) # core collateral - where base asset (WETH/CBBTC/USDC) is deposited (optional)
leverageVaultToken: public(address) # leverage yield - where borrowed GREEN → swapped USDC is deposited

# managers
managers: public(HashMap[uint256, address]) # index -> manager
indexOfManager: public(HashMap[address, uint256]) # manager -> index
numManagers: public(uint256) # num managers

# slippage settings
usdcSlippageAllowed: public(uint256) # basis points (100 = 1%)
greenSlippageAllowed: public(uint256) # basis points (100 = 1%)

# constants
HUNDRED_PERCENT: constant(uint256) = 100_00 # 100.00%
MAX_SWAP_INSTRUCTIONS: constant(uint256) = 5
MAX_TOKEN_PATH: constant(uint256) = 5
MAX_LEGOS: constant(uint256) = 10

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
    _collateralVaultToken: address,
    _collateralVaultTokenLegoId: uint256,
    _leverageVaultToken: address,
    _leverageVaultTokenLegoId: uint256,
    _usdc: address,
    _green: address,
    _savingsGreen: address,
    _startingAgent: address,
    _levgVaultHelper: address,
):
    # not using 0 index
    self.numManagers = 1

    # main addys
    assert empty(address) not in [_undyHq, _underlyingAsset, _usdc, _green, _leverageVaultToken, _levgVaultHelper] # dev: inv addr
    UNDY_HQ = _undyHq
    UNDERLYING_ASSET = _underlyingAsset
    USDC = _usdc
    GREEN = _green
    SAVINGS_GREEN = _savingsGreen

    self.levgVaultHelper = _levgVaultHelper
    legoBook: address = staticcall Registry(_undyHq).getAddr(LEGO_BOOK_ID)

    # leverage vault token
    legoAddr: address = staticcall Registry(legoBook).getAddr(_leverageVaultTokenLegoId)
    assert staticcall YieldLego(legoAddr).canRegisterVaultToken(_usdc, _leverageVaultToken) # dev: invalid leverage vault token
    self.leverageVaultToken = _leverageVaultToken
    self.vaultToLegoId[_leverageVaultToken] = _leverageVaultTokenLegoId

    # ripe collateral token (optional)
    if _collateralVaultToken != empty(address):
        legoAddr = staticcall Registry(legoBook).getAddr(_collateralVaultTokenLegoId)
        assert staticcall YieldLego(legoAddr).canRegisterVaultToken(_underlyingAsset, _collateralVaultToken) # dev: invalid collateral vault token
        self.collateralVaultToken = _collateralVaultToken
        self.vaultToLegoId[_collateralVaultToken] = _collateralVaultTokenLegoId

    # initial agent
    if _startingAgent != empty(address):
        self._registerManager(_startingAgent)

    # defaults
    self.usdcSlippageAllowed = 1_00 # 1.00%
    self.greenSlippageAllowed = 1_00 # 1.00%


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
    collateralVaultToken: address = self.collateralVaultToken
    legoId: uint256 = self.vaultToLegoId[collateralVaultToken]
    ad: VaultActionData = staticcall VaultRegistry(_vaultRegistry).getVaultActionDataBundle(legoId, _depositor)
    if ad.legoId == 0 or ad.legoAddr == empty(address):
        return 0
    ad.vaultAsset = UNDERLYING_ASSET
    return self._depositForYield(ad.vaultAsset, collateralVaultToken, max_value(uint256), empty(bytes32), ad)[0]


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

    # vault asset can go into collateral vault OR (for USDC vaults) leverage vault
    if _asset == _ad.vaultAsset:
        if _asset == USDC:
            # USDC vault: allow both collateral and leverage vaults
            assert vaultToken in [self.collateralVaultToken, self.leverageVaultToken] # dev: vault token mismatch
        else:
            # Non-USDC vault: only collateral vault
            assert vaultToken == self.collateralVaultToken # dev: vault token mismatch

    # USDC (when NOT vault asset) must go into leverage vault
    elif _asset == USDC:
        assert vaultToken == self.leverageVaultToken # dev: vault token mismatch

    # GREEN must go into savings green
    elif _asset == GREEN:
        assert vaultToken == SAVINGS_GREEN # dev: vault token mismatch

    # first time, need to save lego mapping
    if _ad.legoId != 0 and self.vaultToLegoId[vaultToken] == 0:
        self.vaultToLegoId[vaultToken] = _ad.legoId

    log LevgVaultAction(
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

    log LevgVaultAction(
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

    # key addresses
    usdc: address = USDC
    green: address = GREEN
    savingsGreen: address = SAVINGS_GREEN
    leverageVaultToken: address = self.leverageVaultToken
    levgVaultHelper: address = self.levgVaultHelper

    origAmountIn: uint256 = _instructions[0].amountIn
    currentBalance: uint256 = staticcall IERC20(tokenIn).balanceOf(self)

    # important checks!
    assert tokenIn not in [ad.vaultAsset, self.collateralVaultToken, leverageVaultToken, savingsGreen] # dev: invalid swap asset
    if tokenIn == green:
        assert tokenOut == usdc  # dev: GREEN can only go to USDC
    elif tokenIn == usdc and tokenOut != green:
        assert tokenOut == ad.vaultAsset  # dev: must swap into vault asset
        origAmountIn = staticcall LevgVaultHelper(levgVaultHelper).getSwappableUsdcAmount(
            self,
            origAmountIn,
            currentBalance,
            leverageVaultToken,
            self.vaultToLegoId[leverageVaultToken],
            usdc,
            green,
            savingsGreen,
            ad.legoBook,
        )

    origAmountIn = min(origAmountIn, currentBalance)
    assert origAmountIn != 0  # dev: no amount to swap

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

    # verify green <--> usdc swap is fair (check slippage)
    if tokenIn in [green, usdc] and lastTokenOut in [green, usdc]:
        assert staticcall LevgVaultHelper(levgVaultHelper).performPostSwapValidation(tokenIn, origAmountIn, lastTokenOut, lastTokenOutAmount, self.usdcSlippageAllowed, self.greenSlippageAllowed, usdc, green) # dev: bad slippage

    log LevgVaultAction(
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
    assert _asset in [_ad.vaultAsset, self.leverageVaultToken, self.collateralVaultToken, SAVINGS_GREEN] # dev: invalid collateral

    # add collateral
    amount: uint256 = self._getAmountAndApprove(_asset, _amount, empty(address)) # not approving here
    amountDeposited: uint256 = 0
    txUsdValue: uint256 = 0
    amountDeposited, txUsdValue = extcall Lego(_ad.legoAddr).addCollateral(_asset, amount, _extraData, self, self._packMiniAddys(_ad.ledger, _ad.missionControl, _ad.legoBook, _ad.appraiser))
    assert extcall IERC20(_asset).approve(_ad.legoAddr, 0, default_return_value = True) # dev: appr

    log LevgVaultAction(
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

    log LevgVaultAction(
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
    self._setLegoAccessForAction(ad.legoAddr, ws.ActionType.BORROW)

    # borrow
    borrowAmount: uint256 = 0
    txUsdValue: uint256 = 0
    borrowAmount, txUsdValue = extcall Lego(ad.legoAddr).borrow(_borrowAsset, _amount, _extraData, self, self._packMiniAddys(ad.ledger, ad.missionControl, ad.legoBook, ad.appraiser))

    log LevgVaultAction(
        op = 42,
        asset1 = _borrowAsset,
        asset2 = empty(address),
        amount1 = borrowAmount,
        amount2 = 0,
        usdValue = txUsdValue,
        legoId = ad.legoId,
        signer = ad.signer,
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

    log LevgVaultAction(
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

    log LevgVaultAction(
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


#####################
# Underlying Assets #
#####################


@view
@internal
def _getTotalAssets() -> uint256:
    underlyingAsset: address = UNDERLYING_ASSET
    legoBook: address = staticcall Registry(UNDY_HQ).getAddr(LEGO_BOOK_ID)
    levgVaultHelper: address = self.levgVaultHelper
    collateralVaultToken: address = self.collateralVaultToken
    leverageVaultToken: address = self.leverageVaultToken

    # usdc vault
    usdc: address = USDC
    if underlyingAsset == usdc:
        return staticcall LevgVaultHelper(levgVaultHelper).getTotalAssetsForUsdcVault(
            self,
            collateralVaultToken,
            self.vaultToLegoId[collateralVaultToken],
            leverageVaultToken,
            self.vaultToLegoId[leverageVaultToken],
            usdc,
            GREEN,
            SAVINGS_GREEN,
            legoBook,
        )

    # non-usdc vault (WETH, CBBTC, etc)
    return staticcall LevgVaultHelper(levgVaultHelper).getTotalAssetsForNonUsdcVault(
        self,
        underlyingAsset,
        collateralVaultToken,
        self.vaultToLegoId[collateralVaultToken],
        leverageVaultToken,
        self.vaultToLegoId[leverageVaultToken],
        usdc,
        GREEN,
        SAVINGS_GREEN,
        legoBook,
    )


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

    ripeAd: VaultActionData = staticcall VaultRegistry(_vaultRegistry).getVaultActionDataBundle(RIPE_LEGO_ID, _sender)
    ripeAd.vaultAsset = _asset
    levgVaultHelper: address = self.levgVaultHelper

    # buffer to make sure we pull out enough for redemption
    redemptionBuffer: uint256 = staticcall VaultRegistry(_vaultRegistry).redemptionBuffer(self)
    targetWithdrawAmount: uint256 = _amount * (HUNDRED_PERCENT + redemptionBuffer) // HUNDRED_PERCENT

    # step 1: remove underlying asset from Ripe collateral if needed
    underlyingCollateral: uint256 = staticcall LevgVaultHelper(levgVaultHelper).getCollateralBalance(self, _asset)
    if underlyingCollateral != 0:
        amountStillNeeded: uint256 = targetWithdrawAmount - availAmount
        availAmount += self._removeCollateral(_asset, amountStillNeeded, empty(bytes32), ripeAd)[0]
        if availAmount >= _amount:
            return availAmount

    # collateral vault info
    collAd: VaultActionData = ripeAd
    collateralVaultToken: address = self.collateralVaultToken
    collAd.legoId = self.vaultToLegoId[collateralVaultToken]
    collAd.legoAddr = staticcall Registry(collAd.legoBook).getAddr(collAd.legoId)
    if collAd.legoAddr == empty(address):
        return availAmount

    # step 2: withdraw from idle collateralVaultToken in wallet
    collateralVaultTokenBalance: uint256 = staticcall IERC20(collateralVaultToken).balanceOf(self)
    if collateralVaultTokenBalance != 0:
        amountStillNeeded: uint256 = targetWithdrawAmount - availAmount
        vaultTokenAmountToWithdraw: uint256 = staticcall YieldLego(collAd.legoAddr).getVaultTokenAmount(_asset, amountStillNeeded, collateralVaultToken)
        availAmount += self._withdrawFromYield(collateralVaultToken, vaultTokenAmountToWithdraw, empty(bytes32), collAd)[2]
        if availAmount >= _amount:
            return availAmount

    # step 3: remove collateralVaultToken collateral from Ripe and withdraw
    collateralVaultTokenOnRipe: uint256 = staticcall LevgVaultHelper(levgVaultHelper).getCollateralBalance(self, collateralVaultToken)
    if collateralVaultTokenOnRipe != 0:
        amountStillNeeded: uint256 = targetWithdrawAmount - availAmount
        vaultTokenAmountToWithdraw: uint256 = staticcall YieldLego(collAd.legoAddr).getVaultTokenAmount(_asset, amountStillNeeded, collateralVaultToken)
        vaultTokenAmountToWithdraw = self._removeCollateral(collateralVaultToken, vaultTokenAmountToWithdraw, empty(bytes32), ripeAd)[0]
        availAmount += self._withdrawFromYield(collateralVaultToken, vaultTokenAmountToWithdraw, empty(bytes32), collAd)[2]
        if availAmount >= _amount:
            return availAmount

    # step 4: for USDC vaults, also check leverageVaultToken
    if _asset == USDC:
        leverageVaultToken: address = self.leverageVaultToken
        if leverageVaultToken != empty(address) and availAmount < _amount:
            levgAd: VaultActionData = ripeAd
            levgAd.legoId = self.vaultToLegoId[leverageVaultToken]
            levgAd.legoAddr = staticcall Registry(levgAd.legoBook).getAddr(levgAd.legoId)

            if levgAd.legoAddr != empty(address):
                # step 4a: withdraw from idle leverageVaultToken in wallet
                leverageVaultTokenBalance: uint256 = staticcall IERC20(leverageVaultToken).balanceOf(self)
                if leverageVaultTokenBalance != 0:
                    amountStillNeeded: uint256 = targetWithdrawAmount - availAmount
                    vaultTokenAmountToWithdraw: uint256 = staticcall YieldLego(levgAd.legoAddr).getVaultTokenAmount(_asset, amountStillNeeded, leverageVaultToken)
                    availAmount += self._withdrawFromYield(leverageVaultToken, vaultTokenAmountToWithdraw, empty(bytes32), levgAd)[2]
                    if availAmount >= _amount:
                        return availAmount

                # step 4b: remove leverageVaultToken collateral from Ripe and withdraw
                leverageVaultTokenOnRipe: uint256 = staticcall LevgVaultHelper(levgVaultHelper).getCollateralBalance(self, leverageVaultToken)
                if leverageVaultTokenOnRipe != 0:
                    amountStillNeeded: uint256 = targetWithdrawAmount - availAmount
                    vaultTokenAmountToWithdraw: uint256 = staticcall YieldLego(levgAd.legoAddr).getVaultTokenAmount(_asset, amountStillNeeded, leverageVaultToken)
                    vaultTokenAmountToWithdraw = self._removeCollateral(leverageVaultToken, vaultTokenAmountToWithdraw, empty(bytes32), ripeAd)[0]
                    availAmount += self._withdrawFromYield(leverageVaultToken, vaultTokenAmountToWithdraw, empty(bytes32), levgAd)[2]

    return availAmount


#####################
# Levg Vault Config #
#####################


# collateral vault token


@external
def setCollateralVault(_vaultToken: address, _legoId: uint256):
    assert self._isSwitchboardAddr(msg.sender) # dev: no perms

    oldVaultToken: address = self.collateralVaultToken
    assert _vaultToken != oldVaultToken # dev: no change

    # get required addresses
    ad: VaultActionData = staticcall VaultRegistry(self._getVaultRegistry()).getVaultActionDataBundle(RIPE_LEGO_ID, msg.sender)
    ripeLegoAddr: address = ad.legoAddr

    # validate new collateral vault token
    if _vaultToken != empty(address):
        assert staticcall LevgVaultHelper(ripeLegoAddr).isSupportedRipeAsset(_vaultToken) # dev: not supported asset
        assert _vaultToken != SAVINGS_GREEN # dev: cannot be savings green
        legoAddr: address = staticcall Registry(ad.legoBook).getAddr(_legoId)
        assert staticcall YieldLego(legoAddr).canRegisterVaultToken(UNDERLYING_ASSET, _vaultToken) # dev: invalid collateral vault token
        self.vaultToLegoId[_vaultToken] = _legoId

    # validate old collateral vault token has no balances
    if oldVaultToken != empty(address):
        assert staticcall IERC20(oldVaultToken).balanceOf(self) == 0 # dev: old vault has local balance
        assert staticcall LevgVaultHelper(ripeLegoAddr).getCollateralBalance(self, oldVaultToken) == 0 # dev: old vault has ripe balance
        self.vaultToLegoId[oldVaultToken] = 0

    # update state
    self.collateralVaultToken = _vaultToken
    log CollateralVaultTokenSet(collateralVaultToken = _vaultToken)


# leverage vault token


@external
def setLeverageVault(_vaultToken: address, _legoId: uint256):
    assert self._isSwitchboardAddr(msg.sender) # dev: no perms

    oldVaultToken: address = self.leverageVaultToken
    assert _vaultToken != oldVaultToken # dev: no change

    # get required addresses
    ad: VaultActionData = staticcall VaultRegistry(self._getVaultRegistry()).getVaultActionDataBundle(RIPE_LEGO_ID, msg.sender)
    ripeLegoAddr: address = ad.legoAddr

    # validate new leverage vault token
    assert _vaultToken != empty(address) # dev: invalid vault token
    assert staticcall LevgVaultHelper(ripeLegoAddr).isSupportedRipeAsset(_vaultToken) # dev: not supported asset
    assert _vaultToken != SAVINGS_GREEN # dev: cannot be savings green

    legoAddr: address = staticcall Registry(ad.legoBook).getAddr(_legoId)
    assert staticcall YieldLego(legoAddr).canRegisterVaultToken(USDC, _vaultToken) # dev: invalid leverage vault token
    self.vaultToLegoId[_vaultToken] = _legoId

    # validate old leverage vault token has no balances
    if oldVaultToken != empty(address):
        assert staticcall IERC20(oldVaultToken).balanceOf(self) == 0 # dev: old vault has local balance
        assert staticcall LevgVaultHelper(ripeLegoAddr).getCollateralBalance(self, oldVaultToken) == 0 # dev: old vault has ripe balance
        self.vaultToLegoId[oldVaultToken] = 0

    # update state
    self.leverageVaultToken = _vaultToken
    log LeverageVaultTokenSet(leverageVaultToken = _vaultToken)


# slippage settings (USDC <--> GREEN)


@external
def setUsdcSlippageAllowed(_slippage: uint256):
    assert self._isSwitchboardAddr(msg.sender) # dev: no perms
    assert _slippage <= 10_00 # dev: slippage too high (max 10%)
    self.usdcSlippageAllowed = _slippage
    log UsdcSlippageAllowedSet(slippage=_slippage)


@external
def setGreenSlippageAllowed(_slippage: uint256):
    assert self._isSwitchboardAddr(msg.sender) # dev: no perms
    assert _slippage <= 10_00 # dev: slippage too high (max 10%)
    self.greenSlippageAllowed = _slippage
    log GreenSlippageAllowedSet(slippage=_slippage)


# leverage vault helper


@external
def setLevgVaultHelper(_levgVaultHelper: address):
    assert self._isSwitchboardAddr(msg.sender) # dev: no perms
    assert _levgVaultHelper != empty(address) # dev: invalid lego helper
    self.levgVaultHelper = _levgVaultHelper
    log LevgVaultHelperSet(levgVaultHelper=_levgVaultHelper)


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

