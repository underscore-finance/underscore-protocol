#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3
# pragma optimize codesize

from interfaces import Wallet as wi
from interfaces import LegoPartner as Lego
from interfaces import WalletStructs as ws

from ethereum.ercs import IERC20

interface LevgVaultHelper:
    def getTotalAssetsForNonUsdcVault(_wallet: address, _underlyingAsset: address, _collateralVaultToken: address, _collateralVaultTokenLegoId: uint256, _collateralVaultTokenRipeVaultId: uint256, _leverageVaultToken: address, _leverageVaultTokenLegoId: uint256, _leverageVaultTokenRipeVaultId: uint256, _shouldGetMax: bool = True, _usdc: address = empty(address), _green: address = empty(address), _savingsGreen: address = empty(address), _legoBook: address = empty(address)) -> uint256: view
    def getTotalAssetsForUsdcVault(_wallet: address, _collateralVaultToken: address, _collateralVaultTokenLegoId: uint256, _collateralVaultTokenRipeVaultId: uint256, _leverageVaultToken: address, _leverageVaultTokenLegoId: uint256, _leverageVaultTokenRipeVaultId: uint256, _shouldGetMax: bool = True, _usdc: address = empty(address), _green: address = empty(address), _savingsGreen: address = empty(address), _legoBook: address = empty(address)) -> uint256: view
    def getSwappableUsdcAmount(_wallet: address, _amountIn: uint256, _currentBalance: uint256, _leverageVaultToken: address, _leverageVaultTokenLegoId: uint256, _leverageVaultTokenRipeVaultId: uint256, _usdc: address = empty(address), _green: address = empty(address), _savingsGreen: address = empty(address), _legoBook: address = empty(address)) -> uint256: view
    def getMaxBorrowAmount(_wallet: address, _underlyingAsset: address, _collateralVaultToken: address, _collateralVaultTokenLegoId: uint256, _collateralVaultTokenRipeVaultId: uint256, _netUserCapital: uint256, _maxDebtRatio: uint256, _isUsdcVault: bool, _legoBook: address = empty(address)) -> uint256: view
    def performPostSwapValidation(_tokenIn: address, _tokenInAmount: uint256, _tokenOut: address, _tokenOutAmount: uint256, _usdcSlippageAllowed: uint256, _greenSlippageAllowed: uint256, _usdc: address = empty(address), _green: address = empty(address)) -> bool: view
    def getCollateralBalance(_user: address, _asset: address, _ripeVaultId: uint256, _vaultBook: address = empty(address)) -> uint256: view
    def isValidVaultToken(_underlyingAsset: address, _vaultToken: address, _ripeVaultId: uint256, _legoId: uint256) -> bool: view
    def getVaultBookAndDeleverage() -> (address, address): view

interface VaultRegistry:
    def getVaultActionDataWithFrozenStatus(_legoId: uint256, _signer: address, _vaultAddr: address) -> (VaultActionData, bool): view
    def getVaultActionDataBundle(_legoId: uint256, _signer: address) -> VaultActionData: view
    def redemptionBuffer(_vaultAddr: address) -> uint256: view

interface RipeDeleverage:
    def deleverageForWithdrawal(_user: address, _vaultId: uint256, _asset: address, _amount: uint256) -> bool: nonpayable

interface YieldLego:
    def getVaultTokenAmount(_asset: address, _assetAmount: uint256, _vaultToken: address) -> uint256: view

interface MissionControl:
    def isLockedSigner(_signer: address) -> bool: view

interface Switchboard:
    def isSwitchboardAddr(_addr: address) -> bool: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

interface UndyHq:
    def governance() -> address: view

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

struct RipeAsset:
    vaultToken: address
    ripeVaultId: uint256

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
    legoId: uint256
    ripeVaultId: uint256

event LeverageVaultTokenSet:
    leverageVaultToken: indexed(address)
    legoId: uint256
    ripeVaultId: uint256

event UsdcSlippageAllowedSet:
    slippage: uint256

event GreenSlippageAllowedSet:
    slippage: uint256

event LevgVaultHelperSet:
    levgVaultHelper: indexed(address)

event MaxDebtRatioSet:
    maxDebtRatio: uint256

vaultToLegoId: public(HashMap[address, uint256])
levgVaultHelper: public(address)

# vault tokens
collateralAsset: public(RipeAsset) # core collateral - where base asset (WETH/CBBTC/USDC) is deposited (optional)
leverageAsset: public(RipeAsset) # leverage yield - where borrowed GREEN → swapped USDC is deposited

# managers
managers: public(HashMap[uint256, address]) # index -> manager
indexOfManager: public(HashMap[address, uint256]) # manager -> index
numManagers: public(uint256) # num managers

# slippage settings
usdcSlippageAllowed: public(uint256) # basis points (100 = 1%)
greenSlippageAllowed: public(uint256) # basis points (100 = 1%)

# leverage limits
maxDebtRatio: public(uint256) # max debt as % of capital, basis points (7000 = 70%)
netUserCapital: public(uint256) # tracks user deposits - withdrawals (for USDC vaults)

# constants
HUNDRED_PERCENT: constant(uint256) = 100_00 # 100.00%
MAX_SWAP_INSTRUCTIONS: constant(uint256) = 5
MAX_TOKEN_PATH: constant(uint256) = 5
MAX_LEGOS: constant(uint256) = 10
MAX_PROOFS: constant(uint256) = 25

# ids
RIPE_LEGO_ID: constant(uint256) = 1
LEGO_BOOK_ID: constant(uint256) = 3
SWITCHBOARD_ID: constant(uint256) = 4
VAULT_REGISTRY_ID: constant(uint256) = 10

UNDY_HQ: immutable(address)
UNDERLYING_ASSET: immutable(address)
USDC: public(immutable(address))
GREEN: immutable(address)
SAVINGS_GREEN: immutable(address)


@deploy
def __init__(
    _undyHq: address,
    _underlyingAsset: address,
    _collateralVaultToken: address,
    _collateralVaultTokenLegoId: uint256,
    _collateralVaultTokenRipeVaultId: uint256,
    _leverageVaultToken: address,
    _leverageVaultTokenLegoId: uint256,
    _leverageVaultTokenRipeVaultId: uint256,
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

    # set levg vault helper
    self.levgVaultHelper = _levgVaultHelper

    # leverage vault token
    assert staticcall LevgVaultHelper(_levgVaultHelper).isValidVaultToken(_usdc, _leverageVaultToken, _leverageVaultTokenRipeVaultId, _leverageVaultTokenLegoId) # dev: invalid leverage vault token
    self.leverageAsset = RipeAsset(vaultToken=_leverageVaultToken, ripeVaultId=_leverageVaultTokenRipeVaultId)
    self.vaultToLegoId[_leverageVaultToken] = _leverageVaultTokenLegoId

    # ripe collateral token (optional)
    if _collateralVaultToken != empty(address):
        assert staticcall LevgVaultHelper(_levgVaultHelper).isValidVaultToken(_underlyingAsset, _collateralVaultToken, _collateralVaultTokenRipeVaultId, _collateralVaultTokenLegoId) # dev: invalid collateral vault token
        self.collateralAsset = RipeAsset(vaultToken=_collateralVaultToken, ripeVaultId=_collateralVaultTokenRipeVaultId)
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
    collData: RipeAsset = self.collateralAsset
    legoId: uint256 = self.vaultToLegoId[collData.vaultToken]
    ad: VaultActionData = staticcall VaultRegistry(_vaultRegistry).getVaultActionDataBundle(legoId, _depositor)
    if ad.legoId == 0 or ad.legoAddr == empty(address):
        return 0
    ad.vaultAsset = UNDERLYING_ASSET
    return self._depositForYield(ad.vaultAsset, collData.vaultToken, max_value(uint256), empty(bytes32), ad)[0]


@internal
def _depositForYield(
    _asset: address,
    _vaultAddr: address,
    _amount: uint256,
    _extraData: bytes32,
    _ad: VaultActionData,
) -> (uint256, address, uint256, uint256):
    amount: uint256 = self._getAmountAndApprove(_asset, _amount, _ad.legoAddr) # doing approval here

    # no re-depositing / re-staking
    assert self.vaultToLegoId[_asset] == 0 # dev: cannot re-deposit vault tokens

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
            assert vaultToken in [self.collateralAsset.vaultToken, self.leverageAsset.vaultToken] # dev: vault token mismatch
        else:
            # Non-USDC vault: only collateral vault
            assert vaultToken == self.collateralAsset.vaultToken # dev: vault token mismatch

    # USDC (when NOT vault asset) must go into leverage vault
    elif _asset == USDC:
        assert vaultToken == self.leverageAsset.vaultToken # dev: vault token mismatch

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
    levgData: RipeAsset = self.leverageAsset
    levgVaultHelper: address = self.levgVaultHelper

    origAmountIn: uint256 = _instructions[0].amountIn
    currentBalance: uint256 = staticcall IERC20(tokenIn).balanceOf(self)

    # important checks!
    assert tokenIn not in [ad.vaultAsset, self.collateralAsset.vaultToken, levgData.vaultToken, savingsGreen] # dev: invalid swap asset
    if tokenIn == green:
        assert tokenOut == usdc  # dev: GREEN can only go to USDC
    elif tokenIn == usdc and tokenOut != green:
        assert tokenOut == ad.vaultAsset  # dev: must swap into vault asset
        origAmountIn = staticcall LevgVaultHelper(levgVaultHelper).getSwappableUsdcAmount(
            self,
            origAmountIn,
            currentBalance,
            levgData.vaultToken,
            self.vaultToLegoId[levgData.vaultToken],
            levgData.ripeVaultId,
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

    assert lastTokenOutAmount != 0 # dev: no output amount
    assert lastTokenOut == tokenOut # dev: must swap into token out

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
    return self._addCollateral(_asset, _amount, _extraData, 0, ad)


@internal
def _addCollateral(
    _asset: address,
    _amount: uint256,
    _extraData: bytes32,
    _ripeVaultId: uint256,
    _ad: VaultActionData,
) -> (uint256, uint256):
    self._setLegoAccessForAction(_ad.legoAddr, ws.ActionType.ADD_COLLATERAL)
    assert extcall IERC20(_asset).approve(_ad.legoAddr, max_value(uint256), default_return_value = True) # dev: appr

    # validate collateral + lego id
    assert _ad.legoId == RIPE_LEGO_ID # dev: invalid lego id
    assert _asset in [_ad.vaultAsset, self.leverageAsset.vaultToken, self.collateralAsset.vaultToken, SAVINGS_GREEN] # dev: invalid collateral

    # encode ripeVaultId into extraData for RipeLego
    extraData: bytes32 = _extraData
    if _ripeVaultId != 0:
        extraData = convert(_ripeVaultId, bytes32)

    # add collateral
    amount: uint256 = self._getAmountAndApprove(_asset, _amount, empty(address)) # not approving here
    amountDeposited: uint256 = 0
    txUsdValue: uint256 = 0
    amountDeposited, txUsdValue = extcall Lego(_ad.legoAddr).addCollateral(_asset, amount, extraData, self, self._packMiniAddys(_ad.ledger, _ad.missionControl, _ad.legoBook, _ad.appraiser))
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
    return self._removeCollateral(_asset, _amount, _extraData, 0, ad)


@internal
def _removeCollateral(
    _asset: address,
    _amount: uint256,
    _extraData: bytes32,
    _ripeVaultId: uint256,
    _ad: VaultActionData,
) -> (uint256, uint256):
    self._setLegoAccessForAction(_ad.legoAddr, ws.ActionType.REMOVE_COLLATERAL)

    # encode ripeVaultId into extraData for RipeLego
    extraData: bytes32 = _extraData
    if _ripeVaultId != 0:
        extraData = convert(_ripeVaultId, bytes32)

    # remove collateral
    amountRemoved: uint256 = 0
    txUsdValue: uint256 = 0
    amountRemoved, txUsdValue = extcall Lego(_ad.legoAddr).removeCollateral(_asset, _amount, extraData, self, self._packMiniAddys(_ad.ledger, _ad.missionControl, _ad.legoBook, _ad.appraiser))

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

    assert ad.legoId == RIPE_LEGO_ID # dev: invalid lego id
    assert _borrowAsset in [GREEN, SAVINGS_GREEN] # dev: invalid borrow asset

    amount: uint256 = _amount

    # check maxDebtRatio if configured
    maxDebtRatio: uint256 = self.maxDebtRatio
    if maxDebtRatio != 0:
        collData: RipeAsset = self.collateralAsset
        maxBorrowableAmount: uint256 = staticcall LevgVaultHelper(self.levgVaultHelper).getMaxBorrowAmount(
            self,
            ad.vaultAsset,
            collData.vaultToken,
            self.vaultToLegoId[collData.vaultToken],
            collData.ripeVaultId,
            self.netUserCapital,
            maxDebtRatio,
            ad.vaultAsset == USDC,
            ad.legoBook,
        )
        amount = min(amount, maxBorrowableAmount)

    assert amount != 0 # dev: no amount to borrow

    # borrow
    borrowAmount: uint256 = 0
    txUsdValue: uint256 = 0
    borrowAmount, txUsdValue = extcall Lego(ad.legoAddr).borrow(_borrowAsset, amount, _extraData, self, self._packMiniAddys(ad.ledger, ad.missionControl, ad.legoBook, ad.appraiser))

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


####################
# Claim Incentives #
####################


@external
def claimIncentives(
    _legoId: uint256,
    _rewardToken: address = empty(address),
    _rewardAmount: uint256 = max_value(uint256),
    _proofs: DynArray[bytes32, MAX_PROOFS] = [],
) -> (uint256, uint256):
    ad: VaultActionData = self._canManagerPerformAction(msg.sender, [_legoId])

    # make sure can access
    self._setLegoAccessForAction(ad.legoAddr, ws.ActionType.REWARDS)

    # claim rewards
    rewardAmount: uint256 = 0
    txUsdValue: uint256 = 0
    rewardAmount, txUsdValue = extcall Lego(ad.legoAddr).claimIncentives(self, _rewardToken, _rewardAmount, _proofs, self._packMiniAddys(ad.ledger, ad.missionControl, ad.legoBook, ad.appraiser))

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
def _getTotalAssets(_shouldGetMax: bool) -> uint256:
    underlyingAsset: address = UNDERLYING_ASSET
    legoBook: address = staticcall Registry(UNDY_HQ).getAddr(LEGO_BOOK_ID)
    levgVaultHelper: address = self.levgVaultHelper
    collData: RipeAsset = self.collateralAsset
    levgData: RipeAsset = self.leverageAsset

    # usdc vault
    usdc: address = USDC
    if underlyingAsset == usdc:
        return staticcall LevgVaultHelper(levgVaultHelper).getTotalAssetsForUsdcVault(
            self,
            collData.vaultToken,
            self.vaultToLegoId[collData.vaultToken],
            collData.ripeVaultId,
            levgData.vaultToken,
            self.vaultToLegoId[levgData.vaultToken],
            levgData.ripeVaultId,
            _shouldGetMax,
            usdc,
            GREEN,
            SAVINGS_GREEN,
            legoBook,
        )

    # non-usdc vault (WETH, CBBTC, etc)
    return staticcall LevgVaultHelper(levgVaultHelper).getTotalAssetsForNonUsdcVault(
        self,
        underlyingAsset,
        collData.vaultToken,
        self.vaultToLegoId[collData.vaultToken],
        collData.ripeVaultId,
        levgData.vaultToken,
        self.vaultToLegoId[levgData.vaultToken],
        levgData.ripeVaultId,
        _shouldGetMax,
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
    ripeVaultBook: address = empty(address)
    ripeDeleverage: address = empty(address)
    ripeVaultBook, ripeDeleverage = staticcall LevgVaultHelper(levgVaultHelper).getVaultBookAndDeleverage()

    # buffer to make sure we pull out enough for redemption
    redemptionBuffer: uint256 = staticcall VaultRegistry(_vaultRegistry).redemptionBuffer(self)
    targetWithdrawAmount: uint256 = _amount * (HUNDRED_PERCENT + redemptionBuffer) // HUNDRED_PERCENT
    specificWithdrawAmount: uint256 = 0

    # step 1: remove underlying asset from Ripe collateral if needed
    amountStillNeeded: uint256 = targetWithdrawAmount - availAmount
    underlyingCollateral: uint256 = staticcall LevgVaultHelper(levgVaultHelper).getCollateralBalance(self, _asset, 0, ripeVaultBook)
    if underlyingCollateral != 0:
        specificWithdrawAmount = min(amountStillNeeded, underlyingCollateral)
        extcall RipeDeleverage(ripeDeleverage).deleverageForWithdrawal(self, 0, _asset, specificWithdrawAmount)
        availAmount += self._removeCollateral(_asset, specificWithdrawAmount, empty(bytes32), 0, ripeAd)[0]
        if availAmount >= _amount:
            return availAmount

    # collateral vault info
    collAd: VaultActionData = ripeAd
    collData: RipeAsset = self.collateralAsset
    collAd.legoId = self.vaultToLegoId[collData.vaultToken]
    collAd.legoAddr = staticcall Registry(collAd.legoBook).getAddr(collAd.legoId)
    if collAd.legoAddr == empty(address):
        return availAmount

    # step 2: withdraw from idle collateralVaultToken in wallet
    availAmount = self._withdrawVaultTokenForRedemption(
        _asset,
        collData.vaultToken,
        targetWithdrawAmount,
        availAmount,
        0,
        True,
        collAd,
        ripeAd,
        levgVaultHelper,
        ripeVaultBook,
        ripeDeleverage
    )
    if availAmount >= _amount:
        return availAmount

    # step 3: remove collateralVaultToken collateral from Ripe and withdraw
    availAmount = self._withdrawVaultTokenForRedemption(
        _asset,
        collData.vaultToken,
        targetWithdrawAmount,
        availAmount,
        collData.ripeVaultId,
        False,
        collAd,
        ripeAd,
        levgVaultHelper,
        ripeVaultBook,
        ripeDeleverage
    )
    if availAmount >= _amount:
        return availAmount

    # step 4: for USDC vaults, also check leverageVaultToken
    if _asset == USDC and availAmount < _amount:
        levgData: RipeAsset = self.leverageAsset
        if levgData.vaultToken == empty(address) or levgData.vaultToken == collData.vaultToken:
            return availAmount

        levgAd: VaultActionData = ripeAd
        levgAd.legoId = self.vaultToLegoId[levgData.vaultToken]
        levgAd.legoAddr = staticcall Registry(levgAd.legoBook).getAddr(levgAd.legoId)
        if levgAd.legoAddr == empty(address):
            return availAmount

        # step 4a: withdraw from idle leverageVaultToken in wallet
        availAmount = self._withdrawVaultTokenForRedemption(
            _asset,
            levgData.vaultToken,
            targetWithdrawAmount,
            availAmount,
            0,
            True,
            levgAd,
            ripeAd,
            levgVaultHelper,
            ripeVaultBook,
            ripeDeleverage
        )
        if availAmount >= _amount:
            return availAmount

        # step 4b: remove leverageVaultToken collateral from Ripe and withdraw
        availAmount = self._withdrawVaultTokenForRedemption(
            _asset,
            levgData.vaultToken,
            targetWithdrawAmount,
            availAmount,
            levgData.ripeVaultId,
            False,
            levgAd,
            ripeAd,
            levgVaultHelper,
            ripeVaultBook,
            ripeDeleverage
        )

    return availAmount


# withdraw for redemption


@internal
def _withdrawVaultTokenForRedemption(
    _underlyingAsset: address,
    _vaultToken: address,
    _targetWithdrawAmount: uint256,
    _availAmount: uint256,
    _ripeVaultId: uint256,
    _fromWallet: bool,
    _actionData: VaultActionData,
    _ripeActionData: VaultActionData,
    _levgVaultHelper: address,
    _ripeVaultBook: address,
    _ripeDeleverage: address,
) -> uint256:
    balance: uint256 = 0
    if _fromWallet:
        balance = staticcall IERC20(_vaultToken).balanceOf(self)
    else:
        balance = staticcall LevgVaultHelper(_levgVaultHelper).getCollateralBalance(self, _vaultToken, _ripeVaultId, _ripeVaultBook)
    if balance == 0:
        return _availAmount

    # calc amount to withdraw
    amountStillNeeded: uint256 = _targetWithdrawAmount - _availAmount
    vaultTokenAmountToWithdraw: uint256 = staticcall YieldLego(_actionData.legoAddr).getVaultTokenAmount(_underlyingAsset, amountStillNeeded, _vaultToken)
    actualVaultTokenAmount: uint256 = vaultTokenAmountToWithdraw

    # ripe withdrawals, cap at available balance and handle deleverage
    if not _fromWallet:
        actualVaultTokenAmount = min(vaultTokenAmountToWithdraw, balance)

        # deleverage before removing collateral
        extcall RipeDeleverage(_ripeDeleverage).deleverageForWithdrawal(self, _ripeVaultId, _vaultToken, actualVaultTokenAmount)

        # remove collateral and get actual amount removed
        actualVaultTokenAmount = self._removeCollateral(_vaultToken, actualVaultTokenAmount, empty(bytes32), _ripeVaultId, _ripeActionData)[0]

    # withdraw from yield protocol to get underlying asset
    return _availAmount + self._withdrawFromYield(_vaultToken, actualVaultTokenAmount, empty(bytes32), _actionData)[2]


#####################
# Levg Vault Config #
#####################


# collateral vault token


@external
def setCollateralVault(_vaultToken: address, _ripeVaultId: uint256, _legoId: uint256):
    assert self._isSwitchboardAddr(msg.sender) # dev: no perms
    levgVaultHelper: address = self.levgVaultHelper
    oldCollData: RipeAsset = self.collateralAsset

    # validate new collateral vault token
    if _vaultToken != empty(address):
        assert staticcall LevgVaultHelper(levgVaultHelper).isValidVaultToken(UNDERLYING_ASSET, _vaultToken, _ripeVaultId, _legoId) # dev: invalid collateral vault token
        self.vaultToLegoId[_vaultToken] = _legoId

    # validate old collateral vault token has no balances
    if oldCollData.vaultToken != empty(address):
        assert staticcall LevgVaultHelper(levgVaultHelper).getCollateralBalance(self, oldCollData.vaultToken, oldCollData.ripeVaultId) == 0 # dev: old vault has ripe balance
        if oldCollData.vaultToken != _vaultToken:
            assert staticcall IERC20(oldCollData.vaultToken).balanceOf(self) == 0 # dev: old vault has local balance

    # update state
    self.collateralAsset = RipeAsset(vaultToken=_vaultToken, ripeVaultId=_ripeVaultId)
    log CollateralVaultTokenSet(collateralVaultToken = _vaultToken, legoId = _legoId, ripeVaultId = _ripeVaultId)


# leverage vault token


@external
def setLeverageVault(_vaultToken: address, _legoId: uint256, _ripeVaultId: uint256):
    assert self._isSwitchboardAddr(msg.sender) # dev: no perms
    levgVaultHelper: address = self.levgVaultHelper
    oldCollData: RipeAsset = self.leverageAsset

    assert staticcall LevgVaultHelper(levgVaultHelper).isValidVaultToken(USDC, _vaultToken, _ripeVaultId, _legoId) # dev: invalid leverage vault token
    self.vaultToLegoId[_vaultToken] = _legoId

    # validate old leverage vault token has no balances
    assert staticcall LevgVaultHelper(levgVaultHelper).getCollateralBalance(self, oldCollData.vaultToken, oldCollData.ripeVaultId) == 0 # dev: old vault has ripe balance
    if oldCollData.vaultToken != _vaultToken:
        assert staticcall IERC20(oldCollData.vaultToken).balanceOf(self) == 0 # dev: old vault has local balance

    # update state
    self.leverageAsset = RipeAsset(vaultToken=_vaultToken, ripeVaultId=_ripeVaultId)
    log LeverageVaultTokenSet(leverageVaultToken = _vaultToken, legoId = _legoId, ripeVaultId = _ripeVaultId)


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


# max debt ratio


@external
def setMaxDebtRatio(_ratio: uint256):
    assert self._isSwitchboardAddr(msg.sender) # dev: no perms
    assert _ratio <= HUNDRED_PERCENT # dev: ratio too high (max 100%)
    self.maxDebtRatio = _ratio
    log MaxDebtRatioSet(maxDebtRatio=_ratio)


####################
# Manager Settings #
####################


# can manage


@internal
def _canManagerPerformAction(_signer: address, _legoIds: DynArray[uint256, MAX_LEGOS]) -> VaultActionData:
    vaultRegistry: address = self._getVaultRegistry()
    if msg.sender != vaultRegistry:
        assert self.indexOfManager[_signer] != 0 # dev: not manager

    # main data for this transaction - get action data and frozen status in single call
    legoId: uint256 = 0
    if len(_legoIds) != 0:
        legoId = _legoIds[0]

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


# governance


@view
@internal
def _getGovernanceAddr() -> address:
    return staticcall UndyHq(UNDY_HQ).governance()


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

    # ripe protocol is only one that needs this in leverage vault
    assert numInputs == 1 # dev: invalid number of inputs
    success, response = raw_call(
        targetAddr,
        concat(
            method_abi,
            convert(_legoAddr, bytes32),
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

