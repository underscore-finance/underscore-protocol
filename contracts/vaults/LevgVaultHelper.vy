#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

exports: addys.__interface__
initializes: addys
import contracts.modules.Addys as addys

from ethereum.ercs import IERC20
from ethereum.ercs import IERC4626

interface LevgVault:
    def vaultToLegoId(_vaultToken: address) -> uint256: view
    def collateralAsset() -> RipeAsset: view
    def leverageAsset() -> RipeAsset: view
    def netUserCapital() -> uint256: view
    def maxDebtRatio() -> uint256: view

interface YieldLego:
    def getUnderlyingAmountSafe(_vaultToken: address, _vaultTokenBalance: uint256) -> uint256: view
    def getUnderlyingAmount(_vaultToken: address, _vaultTokenAmount: uint256) -> uint256: view
    def canRegisterVaultToken(_asset: address, _vaultToken: address) -> bool: view

interface RipePriceDesk:
    def getAssetAmount(_asset: address, _usdValue: uint256, _shouldRaise: bool = False) -> uint256: view
    def getUsdValue(_asset: address, _amount: uint256, _shouldRaise: bool = False) -> uint256: view

interface RipeMissionControl:
    def isSupportedAssetInVault(_vaultId: uint256, _asset: address) -> bool: view
    def getFirstVaultIdForAsset(_asset: address) -> uint256: view

interface RipeCreditEngine:
    def getMaxBorrowAmount(_user: address) -> uint256: view
    def getUserDebtAmount(_user: address) -> uint256: view

interface RipeRegistry:
    def savingsGreen() -> address: view
    def greenToken() -> address: view

interface RipeDepositVault:
    def getTotalAmountForUser(_user: address, _asset: address) -> uint256: view

interface Ledger:
    def vaultTokens(_vaultToken: address) -> VaultToken: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

struct VaultToken:
    legoId: uint256
    underlyingAsset: address
    decimals: uint256
    isRebasing: bool

struct RipeAsset:
    vaultToken: address
    ripeVaultId: uint256

# ripe addrs
RIPE_REGISTRY: public(immutable(address))
GREEN_TOKEN: public(immutable(address))
SAVINGS_GREEN: public(immutable(address))
USDC: public(immutable(address))

RIPE_MISSION_CONTROL_ID: constant(uint256) = 5
RIPE_PRICE_DESK_ID: constant(uint256) = 7
RIPE_VAULT_BOOK_ID: constant(uint256) = 8
RIPE_CREDIT_ENGINE_ID: constant(uint256) = 13
RIPE_DELEVERAGE_ID: constant(uint256) = 18
STAB_POOL_ID: constant(uint256) = 1

HUNDRED_PERCENT: constant(uint256) = 100_00  # 100.00%


@deploy
def __init__(_undyHq: address, _ripeRegistry: address, _usdc: address):
    addys.__init__(_undyHq)

    assert _ripeRegistry != empty(address) # dev: invalid ripe registry
    RIPE_REGISTRY = _ripeRegistry
    GREEN_TOKEN = staticcall RipeRegistry(RIPE_REGISTRY).greenToken()
    SAVINGS_GREEN = staticcall RipeRegistry(RIPE_REGISTRY).savingsGreen()

    assert _usdc != empty(address) # dev: invalid usdc
    USDC = _usdc


###################
# Leverage Vaults #
###################


# pre swap validation


@view
@external
def getSwappableUsdcAmount(
    _wallet: address,
    _amountIn: uint256,
    _currentBalance: uint256,
    _leverageVaultToken: address,
    _leverageVaultTokenLegoId: uint256,
    _leverageVaultTokenRipeVaultId: uint256,
    _usdc: address = empty(address),
    _green: address = empty(address),
    _savingsGreen: address = empty(address),
    _legoBook: address = empty(address),
) -> uint256:
    # resolve addresses
    ripeHq: address = self._getRipeHq()
    ripeVaultBook: address = self._getRipeVaultBook(empty(address), ripeHq)
    ripeMissionControl: address = self._getRipeMissionControl(empty(address), ripeHq)
    legoBook: address = _legoBook if _legoBook != empty(address) else addys._getLegoBookAddr()
    creditEngine: address = self._getRipeCreditEngine(empty(address), ripeHq)
    ripePriceDesk: address = self._getRipePriceDesk(empty(address), ripeHq)

    swappableAmount: uint256 = self._getSwappableUsdcAmount(_wallet, _leverageVaultToken, _leverageVaultTokenRipeVaultId, _usdc, _green, _savingsGreen, legoBook, ripeVaultBook, ripeMissionControl, creditEngine, ripePriceDesk)
    return min(swappableAmount, _amountIn)


# max borrow amount


@view
@external
def getMaxBorrowAmount(
    _wallet: address,
    _underlyingAsset: address,
    _collateralVaultToken: address,
    _collateralVaultTokenLegoId: uint256,
    _collateralVaultTokenRipeVaultId: uint256,
    _netUserCapital: uint256,
    _maxDebtRatio: uint256,
    _isUsdcVault: bool,
    _legoBook: address = empty(address),
) -> uint256:
    # resolve addresses
    ripeHq: address = self._getRipeHq()
    ripeVaultBook: address = self._getRipeVaultBook(empty(address), ripeHq)
    ripeMissionControl: address = self._getRipeMissionControl(empty(address), ripeHq)
    ripePriceDesk: address = self._getRipePriceDesk(empty(address), ripeHq)
    creditEngine: address = self._getRipeCreditEngine(empty(address), ripeHq)
    legoBook: address = _legoBook if _legoBook != empty(address) else addys._getLegoBookAddr()

    leverageAsset: RipeAsset = staticcall LevgVault(_wallet).leverageAsset()
    maxDebtRatioLimit: uint256 = self._getMaxBorrowAmountByMaxDebtRatio(_wallet, _underlyingAsset, _collateralVaultToken, _collateralVaultTokenRipeVaultId, leverageAsset.vaultToken, _netUserCapital, _maxDebtRatio, legoBook, ripeVaultBook, ripeMissionControl, ripePriceDesk, creditEngine)
    maxBorrowAmount: uint256 = self._getMaxBorrowAmountByRipeLtv(_wallet, creditEngine)
    return min(maxDebtRatioLimit, maxBorrowAmount)


# post swap validation


@view
@external
def performPostSwapValidation(
    _tokenIn: address,
    _tokenInAmount: uint256,
    _tokenOut: address,
    _tokenOutAmount: uint256,
    _usdcSlippageAllowed: uint256,
    _greenSlippageAllowed: uint256,
    _usdc: address = empty(address),
    _green: address = empty(address),
) -> bool:
    usdc: address = _usdc if _usdc != empty(address) else USDC
    green: address = _green if _green != empty(address) else GREEN_TOKEN

    # GREEN -> USDC swap validation
    if _tokenIn == green and _tokenOut == usdc:

        # Get USD value of USDC received (18 decimals)
        ripePriceDesk: address = staticcall Registry(RIPE_REGISTRY).getAddr(RIPE_PRICE_DESK_ID)
        usdcValue: uint256 = staticcall RipePriceDesk(ripePriceDesk).getUsdValue(usdc, _tokenOutAmount, True)

        # Minimum expected: greenAmount * (10000 - slippage) / 10000
        # GREEN is 18 decimals and treated as $1 USD, so greenAmount = USD value
        minExpected: uint256 = _tokenInAmount * (HUNDRED_PERCENT - _usdcSlippageAllowed) // HUNDRED_PERCENT
        return usdcValue >= minExpected

    # USDC -> GREEN swap validation
    elif _tokenIn == usdc and _tokenOut == green:

        # Get USD value of USDC sent (18 decimals)
        ripePriceDesk: address = staticcall Registry(RIPE_REGISTRY).getAddr(RIPE_PRICE_DESK_ID)
        usdcValue: uint256 = staticcall RipePriceDesk(ripePriceDesk).getUsdValue(usdc, _tokenInAmount, True)

        # Minimum expected: usdcValue * (10000 - slippage) / 10000
        minExpected: uint256 = usdcValue * (HUNDRED_PERCENT - _greenSlippageAllowed) // HUNDRED_PERCENT
        return _tokenOutAmount >= minExpected

    return True


# usdc vault


@view
@external
def getTotalAssetsForUsdcVault(
    _wallet: address,
    _collateralVaultToken: address,
    _collateralVaultTokenLegoId: uint256,
    _collateralVaultTokenRipeVaultId: uint256,
    _leverageVaultToken: address,
    _leverageVaultTokenLegoId: uint256,
    _leverageVaultTokenRipeVaultId: uint256,
    _shouldGetMax: bool = True,
    _usdc: address = empty(address),
    _green: address = empty(address),
    _savingsGreen: address = empty(address),
    _legoBook: address = empty(address),
) -> uint256:
    usdc: address = _usdc if _usdc != empty(address) else USDC
    green: address = _green if _green != empty(address) else GREEN_TOKEN
    legoBook: address = _legoBook if _legoBook != empty(address) else addys._getLegoBookAddr()

    # resolve ripe addresses
    ripeHq: address = self._getRipeHq()
    ripeVaultBook: address = self._getRipeVaultBook(empty(address), ripeHq)
    ripeMissionControl: address = self._getRipeMissionControl(empty(address), ripeHq)
    creditEngine: address = self._getRipeCreditEngine(empty(address), ripeHq)

    # usdc amount: wallet + naked ripe + collateral vault
    usdcAmount: uint256 = self._getTotalUnderlyingAmount(_wallet, _collateralVaultToken, True, _shouldGetMax, _collateralVaultTokenRipeVaultId, legoBook, ripeVaultBook, ripeMissionControl)

    # add leverage vault amount if different from collateral vault
    if _collateralVaultToken != _leverageVaultToken:
        usdcAmount += self._getUnderlyingAmountForVaultToken(_wallet, _leverageVaultToken, _shouldGetMax, _leverageVaultTokenRipeVaultId, legoBook, ripeVaultBook, ripeMissionControl)

    # green amounts
    userDebtAmount: uint256 = staticcall RipeCreditEngine(creditEngine).getUserDebtAmount(_wallet) # 18 decimals
    greenSurplusAmount: uint256 = self._getUnderlyingGreenAmount(_wallet, green, _savingsGreen, ripeVaultBook, ripeMissionControl)

    # adjust usdc values based on green situation
    if userDebtAmount > greenSurplusAmount:
        userDebtAmount -= greenSurplusAmount # treat green as $1 USD (most conservative, in this case)
        usdcAmount -= min(usdcAmount, userDebtAmount // (10 ** 12)) # normalize to 6 decimals

    elif greenSurplusAmount > userDebtAmount:
        ripePriceDesk: address = self._getRipePriceDesk(empty(address), ripeHq)
        extraGreen: uint256 = greenSurplusAmount - userDebtAmount
        usdValueOfGreen: uint256 = min(staticcall RipePriceDesk(ripePriceDesk).getUsdValue(green, extraGreen, True), extraGreen) # both 18 decimals
        usdcAmount += staticcall RipePriceDesk(ripePriceDesk).getAssetAmount(usdc, usdValueOfGreen, True)

    return usdcAmount


# non-usdc vault


@view
@external
def getTotalAssetsForNonUsdcVault(
    _wallet: address,
    _underlyingAsset: address,
    _collateralVaultToken: address,
    _collateralVaultTokenLegoId: uint256,
    _collateralVaultTokenRipeVaultId: uint256,
    _leverageVaultToken: address,
    _leverageVaultTokenLegoId: uint256,
    _leverageVaultTokenRipeVaultId: uint256,
    _shouldGetMax: bool = True,
    _usdc: address = empty(address),
    _green: address = empty(address),
    _savingsGreen: address = empty(address),
    _legoBook: address = empty(address),
) -> uint256:
    usdc: address = _usdc if _usdc != empty(address) else USDC
    green: address = _green if _green != empty(address) else GREEN_TOKEN
    legoBook: address = _legoBook if _legoBook != empty(address) else addys._getLegoBookAddr()

    # resolve ripe addresses
    ripeHq: address = self._getRipeHq()
    ripeVaultBook: address = self._getRipeVaultBook(empty(address), ripeHq)
    ripeMissionControl: address = self._getRipeMissionControl(empty(address), ripeHq)
    creditEngine: address = self._getRipeCreditEngine(empty(address), ripeHq)
    ripePriceDesk: address = self._getRipePriceDesk(empty(address), ripeHq)

    # phase 1: get underlying asset amount (WETH/CBBTC/etc) - from wallet + naked ripe + collateral vault
    underlyingAmount: uint256 = self._getTotalUnderlyingAmount(_wallet, _collateralVaultToken, True, _shouldGetMax, _collateralVaultTokenRipeVaultId, legoBook, ripeVaultBook, ripeMissionControl)

    # phase 2: get USDC (wallet + naked on ripe + leverage vault)
    usdcAmount: uint256 = self._getTotalUnderlyingAmount(_wallet, _leverageVaultToken, False, _shouldGetMax, _leverageVaultTokenRipeVaultId, legoBook, ripeVaultBook, ripeMissionControl)
    usdcValue: uint256 = staticcall RipePriceDesk(ripePriceDesk).getUsdValue(usdc, usdcAmount, True) # 18 decimals

    # phase 3: calculate GREEN position
    userDebtAmount: uint256 = staticcall RipeCreditEngine(creditEngine).getUserDebtAmount(_wallet) # 18 decimals
    greenSurplusAmount: uint256 = self._getUnderlyingGreenAmount(_wallet, green, _savingsGreen, ripeVaultBook, ripeMissionControl)

    # phase 4: convert (USDC +/- GREEN) to underlying asset and add/subtract
    if userDebtAmount > greenSurplusAmount:

        # net debt scenario: we owe GREEN
        netDebt: uint256 = userDebtAmount - greenSurplusAmount # 18 decimals, treat GREEN as $1 USD (most conservative, in this case)

        # USDC covers debt with surplus
        if usdcValue > netDebt:
            netPositiveValue: uint256 = usdcValue - netDebt
            underlyingAmount += staticcall RipePriceDesk(ripePriceDesk).getAssetAmount(_underlyingAsset, netPositiveValue, True)

        # debt exceeds USDC value - leverage vault is underwater
        else:
            netNegativeValue: uint256 = netDebt - usdcValue
            underlyingToSubtract: uint256 = staticcall RipePriceDesk(ripePriceDesk).getAssetAmount(_underlyingAsset, netNegativeValue, True)
            underlyingAmount -= min(underlyingAmount, underlyingToSubtract)

    else:
        extraGreen: uint256 = greenSurplusAmount - userDebtAmount # net surplus scenario: we have extra GREEN (or zero)
        greenValue: uint256 = min(staticcall RipePriceDesk(ripePriceDesk).getUsdValue(green, extraGreen, True), extraGreen) # both 18 decimals
        totalPositiveValue: uint256 = usdcValue + greenValue
        underlyingAmount += staticcall RipePriceDesk(ripePriceDesk).getAssetAmount(_underlyingAsset, totalPositiveValue, True)

    return underlyingAmount


# collateral balance


@view
@external
def getCollateralBalance(_user: address, _asset: address, _ripeVaultId: uint256, _vaultBook: address = empty(address)) -> uint256:
    ripeHq: address = self._getRipeHq()
    ripeVaultBook: address = self._getRipeVaultBook(_vaultBook, ripeHq)
    ripeMissionControl: address = self._getRipeMissionControl(empty(address), ripeHq)
    return self._getRipeCollateralBalance(_user, _asset, _ripeVaultId, ripeVaultBook, ripeMissionControl)


# supported asset


@view
@external
def isSupportedAssetInVault(_vaultId: uint256, _asset: address) -> bool:
    return self._isSupportedAssetInVault(_vaultId, _asset)


@view
@internal
def _isSupportedAssetInVault(_vaultId: uint256, _asset: address) -> bool:
    mc: address = staticcall Registry(RIPE_REGISTRY).getAddr(RIPE_MISSION_CONTROL_ID)
    return staticcall RipeMissionControl(mc).isSupportedAssetInVault(_vaultId, _asset)


# get addrs


@view
@external
def getVaultBookAndDeleverage() -> (address, address):
    ripeHq: address = RIPE_REGISTRY
    vaultBook: address = staticcall Registry(ripeHq).getAddr(RIPE_VAULT_BOOK_ID)
    deleverage: address = staticcall Registry(ripeHq).getAddr(RIPE_DELEVERAGE_ID)
    return vaultBook, deleverage


# validate vault token


@view
@external
def isValidVaultToken(_underlyingAsset: address, _vaultToken: address, _ripeVaultId: uint256, _legoId: uint256) -> bool:
    if empty(address) in [_underlyingAsset, _vaultToken]:
        return False

    if 0 in [_ripeVaultId, _legoId]:
        return False

    # check lego id
    legoAddr: address = staticcall Registry(addys._getLegoBookAddr()).getAddr(_legoId)
    if not staticcall YieldLego(legoAddr).canRegisterVaultToken(_underlyingAsset, _vaultToken):
        return False

    # check ripe collateral asset
    return self._isSupportedAssetInVault(_ripeVaultId, _vaultToken)


#####################
# Core Internal Fns #
#####################


# Everything below here is the exact same as in LevgVaultTools.vy


@view
@internal
def _getVaultTokenData(_levgVault: address, _isCollateralAsset: bool) -> (address, uint256):
    assetData: RipeAsset = empty(RipeAsset)
    if _isCollateralAsset:
        assetData = staticcall LevgVault(_levgVault).collateralAsset()
    else:
        assetData = staticcall LevgVault(_levgVault).leverageAsset()
    return assetData.vaultToken, assetData.ripeVaultId


@view
@internal
def _getLegoIdForVaultToken(_levgVault: address, _vaultToken: address, _undyVaultTokenLegoId: uint256 = 0) -> uint256:
    if _undyVaultTokenLegoId != 0:
        return _undyVaultTokenLegoId

    legoId: uint256 = staticcall LevgVault(_levgVault).vaultToLegoId(_vaultToken)
    if legoId != 0:
        return legoId

    data: VaultToken = staticcall Ledger(addys._getLedgerAddr()).vaultTokens(_vaultToken)
    return data.legoId


@view
@internal
def _getRipeCollateralBalance(
    _levgVault: address,
    _asset: address,
    _ripeVaultId: uint256,
    _ripeVaultBook: address,
    _ripeMissionControl: address,
) -> uint256:
    ripeVaultId: uint256 = _ripeVaultId

    # get ripe vault id (if necessary)
    if ripeVaultId == 0:
        ripeVaultId = staticcall RipeMissionControl(_ripeMissionControl).getFirstVaultIdForAsset(_asset)

    # no ripe vault id found
    if ripeVaultId == 0:
        return 0

    # get ripe vault deposit address
    ripeVaultAddr: address = staticcall Registry(_ripeVaultBook).getAddr(ripeVaultId)
    if ripeVaultAddr == empty(address):
        return 0

    # get total amount for user
    return staticcall RipeDepositVault(ripeVaultAddr).getTotalAmountForUser(_levgVault, _asset)


@view
@internal
def _getAmountForAsset(
    _levgVault: address,
    _asset: address,
    _ripeVaultId: uint256,
    _ripeVaultBook: address,
    _ripeMissionControl: address,
) -> uint256:
    if _asset == empty(address):
        return 0

    # asset in wallet
    amount: uint256 = staticcall IERC20(_asset).balanceOf(_levgVault)

    # asset on Ripe
    amount += self._getRipeCollateralBalance(_levgVault, _asset, _ripeVaultId, _ripeVaultBook, _ripeMissionControl)

    return amount


@view
@internal
def _getUnderlyingAmountWithVaultTokenAmount(
    _levgVault: address,
    _vaultToken: address,
    _vaultTokenAmount: uint256,
    _shouldGetMax: bool,
    _undyVaultTokenLegoId: uint256,
    _legoBook: address,
) -> uint256:
    # get lego id (if necessary)
    legoId: uint256 = self._getLegoIdForVaultToken(_levgVault, _vaultToken, _undyVaultTokenLegoId)
    if legoId == 0:
        return 0

    # underscore lego address
    legoAddr: address = staticcall Registry(_legoBook).getAddr(legoId)
    if legoAddr == empty(address):
        return 0

    # calc underlying amount
    underlyingAmount: uint256 = 0
    if _shouldGetMax:
        underlyingAmount = staticcall YieldLego(legoAddr).getUnderlyingAmount(_vaultToken, _vaultTokenAmount)
    else:
        underlyingAmount = staticcall YieldLego(legoAddr).getUnderlyingAmountSafe(_vaultToken, _vaultTokenAmount)

    return underlyingAmount


@view
@internal
def _getUnderlyingAmountForVaultToken(
    _levgVault: address,
    _vaultToken: address,
    _shouldGetMax: bool,
    _ripeVaultId: uint256,
    _legoBook: address,
    _ripeVaultBook: address,
    _ripeMissionControl: address,
) -> uint256:
    if _vaultToken == empty(address):
        return 0

    # get vault token amount (in wallet and on ripe)
    vaultTokenAmount: uint256 = self._getAmountForAsset(_levgVault, _vaultToken, _ripeVaultId, _ripeVaultBook, _ripeMissionControl)
    if vaultTokenAmount == 0:
        return 0

    # get underlying amount with vault token amount
    return self._getUnderlyingAmountWithVaultTokenAmount(_levgVault, _vaultToken, vaultTokenAmount, _shouldGetMax, 0, _legoBook)


@view
@internal
def _getTotalUnderlyingAmount(
    _levgVault: address,
    _vaultToken: address,
    _isCollateralAsset: bool,
    _shouldGetMax: bool,
    _ripeVaultId: uint256,
    _legoBook: address,
    _ripeVaultBook: address,
    _ripeMissionControl: address,
) -> uint256:
    underlyingAsset: address = staticcall IERC4626(_levgVault).asset() if _isCollateralAsset else USDC
    underlyingNaked: uint256 = self._getAmountForAsset(_levgVault, underlyingAsset, 0, _ripeVaultBook, _ripeMissionControl)
    underlyingFromVault: uint256 = self._getUnderlyingAmountForVaultToken(_levgVault, _vaultToken, _shouldGetMax, _ripeVaultId, _legoBook, _ripeVaultBook, _ripeMissionControl)
    return underlyingNaked + underlyingFromVault


@view
@internal
def _getUnderlyingGreenAmount(
    _levgVault: address,
    _green: address,
    _savingsGreen: address,
    _ripeVaultBook: address,
    _ripeMissionControl: address,
) -> uint256:
    green: address = _green if _green != empty(address) else GREEN_TOKEN
    greenAmount: uint256 = staticcall IERC20(green).balanceOf(_levgVault)

    # savings green balance (in wallet and on ripe)
    savingsGreen: address = _savingsGreen if _savingsGreen != empty(address) else SAVINGS_GREEN
    savingsGreenAmount: uint256 = self._getAmountForAsset(_levgVault, savingsGreen, STAB_POOL_ID, _ripeVaultBook, _ripeMissionControl)

    # calc underlying amount
    if savingsGreenAmount != 0:
        greenAmount += staticcall IERC4626(savingsGreen).previewRedeem(savingsGreenAmount)

    return greenAmount


@view
@internal
def _getMaxBorrowAmountByMaxDebtRatio(
    _levgVault: address,
    _underlyingAsset: address,
    _collateralVaultToken: address,
    _collateralVaultTokenRipeVaultId: uint256,
    _leverageVaultToken: address,
    _netUserCapital: uint256,
    _maxDebtRatio: uint256,
    _legoBook: address,
    _ripeVaultBook: address,
    _ripeMissionControl: address,
    _ripePriceDesk: address,
    _creditEngine: address,
) -> uint256:
    # get max debt ratio (if necessary) -- check early to avoid expensive calculations
    maxDebtRatio: uint256 = _maxDebtRatio if _maxDebtRatio != 0 else staticcall LevgVault(_levgVault).maxDebtRatio()
    if maxDebtRatio == 0:
        return max_value(uint256)

    # get leverage vault token (if necessary)
    leverageVaultToken: address = _leverageVaultToken
    if leverageVaultToken == empty(address):
        levgData: RipeAsset = staticcall LevgVault(_levgVault).leverageAsset()
        leverageVaultToken = levgData.vaultToken

    collateralVaultToken: address = _collateralVaultToken
    collateralVaultTokenRipeVaultId: uint256 = _collateralVaultTokenRipeVaultId
    if collateralVaultToken == empty(address) or collateralVaultTokenRipeVaultId == 0:
        levgData: RipeAsset = staticcall LevgVault(_levgVault).collateralAsset()
        collateralVaultToken = levgData.vaultToken
        collateralVaultTokenRipeVaultId = levgData.ripeVaultId

    # for usdc leverage vaults, use netUserCapital only (otherwise can't distinguish user capital from leveraged positions)
    underlyingAmount: uint256 = 0
    if collateralVaultToken == leverageVaultToken:
        underlyingAmount = _netUserCapital if _netUserCapital != 0 else staticcall LevgVault(_levgVault).netUserCapital()

    # typical leverage vault
    else:
        underlyingAmount = self._getTotalUnderlyingAmount(
            _levgVault,
            collateralVaultToken,
            True, # is collateral asset
            False, # conservative, safe underlying amount
            collateralVaultTokenRipeVaultId,
            _legoBook,
            _ripeVaultBook,
            _ripeMissionControl,
        )

    # get underlying asset (if necessary)
    underlyingAsset: address = _underlyingAsset if _underlyingAsset != empty(address) else staticcall IERC4626(_levgVault).asset()

    # convert to USD value
    underlyingUsdValue: uint256 = staticcall RipePriceDesk(_ripePriceDesk).getUsdValue(underlyingAsset, underlyingAmount, True)

    # remaining debt after GREEN offset (GREEN is 18 decimals, treated as $1 USD)
    remainingDebt: uint256 = self._getNetUserDebt(_levgVault, _creditEngine, _ripeVaultBook, _ripeMissionControl)

    # max allowed debt (in USD)
    maxAllowedDebt: uint256 = underlyingUsdValue * maxDebtRatio // HUNDRED_PERCENT
    if remainingDebt >= maxAllowedDebt:
        return 0

    return maxAllowedDebt - remainingDebt


@view
@internal
def _getMaxBorrowAmountByRipeLtv(
    _levgVault: address,
    _creditEngine: address,
) -> uint256:
    return staticcall RipeCreditEngine(_creditEngine).getMaxBorrowAmount(_levgVault)


@view
@internal
def _getNetUserDebt(
    _levgVault: address,
    _creditEngine: address,
    _ripeVaultBook: address,
    _ripeMissionControl: address,
) -> uint256:
    # get user debt in GREEN (18 decimals)
    userDebt: uint256 = staticcall RipeCreditEngine(_creditEngine).getUserDebtAmount(_levgVault)

    # get underlying GREEN amount (in wallet and from sGREEN)
    greenSurplus: uint256 = self._getUnderlyingGreenAmount(_levgVault, empty(address), empty(address), _ripeVaultBook, _ripeMissionControl)

    # if GREEN >= debt, return 0 (no net debt exists)
    if greenSurplus >= userDebt:
        return 0

    return userDebt - greenSurplus


@view
@internal
def _getSwappableUsdcAmount(
    _levgVault: address,
    _leverageVaultToken: address,
    _leverageVaultTokenRipeVaultId: uint256,
    _usdc: address,
    _green: address,
    _savingsGreen: address,
    _legoBook: address,
    _ripeVaultBook: address,
    _ripeMissionControl: address,
    _creditEngine: address,
    _ripePriceDesk: address,
) -> uint256:
    usdc: address = _usdc if _usdc != empty(address) else USDC

    # core underlying asset must be different from USDC
    if staticcall IERC4626(_levgVault).asset() == usdc:
        return 0

    # get leverage vault token data (if necessary)
    leverageVaultToken: address = _leverageVaultToken
    leverageVaultTokenRipeVaultId: uint256 = _leverageVaultTokenRipeVaultId
    if leverageVaultToken == empty(address) or leverageVaultTokenRipeVaultId == 0:
        levgData: RipeAsset = staticcall LevgVault(_levgVault).leverageAsset()
        leverageVaultToken = levgData.vaultToken
        leverageVaultTokenRipeVaultId = levgData.ripeVaultId

    # leverage vault token must be USDC
    if staticcall IERC4626(leverageVaultToken).asset() != usdc:
        return 0

    # total usdc amount (in wallet, naked on ripe, via vault token)
    usdcAmount: uint256 = self._getTotalUnderlyingAmount(_levgVault, leverageVaultToken, False, False, leverageVaultTokenRipeVaultId, _legoBook, _ripeVaultBook, _ripeMissionControl)

    # user debt amount
    userDebtAmount: uint256 = staticcall RipeCreditEngine(_creditEngine).getUserDebtAmount(_levgVault) # 18 decimals
    if userDebtAmount == 0:
        return usdcAmount

    # convert to USD value
    usdcValue: uint256 = staticcall RipePriceDesk(_ripePriceDesk).getUsdValue(usdc, usdcAmount, False) # 18 decimals

    # green amount (treat as $1 USD to offset debt)
    greenSurplusAmount: uint256 = self._getUnderlyingGreenAmount(_levgVault, _green, _savingsGreen, _ripeVaultBook, _ripeMissionControl)

    # if GREEN covers all debt, all USDC is swappable
    if greenSurplusAmount >= userDebtAmount:
        return usdcAmount

    # remaining debt must come from USDC
    remainingDebt: uint256 = userDebtAmount - greenSurplusAmount
    if remainingDebt >= usdcValue:
        return 0

    return staticcall RipePriceDesk(_ripePriceDesk).getAssetAmount(usdc, usdcValue - remainingDebt, True)


#####################
# Address Resolvers #
#####################


@view
@internal
def _getRipeHq(_ripeHq: address = empty(address)) -> address:
    if _ripeHq != empty(address):
        return _ripeHq
    return RIPE_REGISTRY


@view
@internal
def _getRipeVaultBook(_ripeVaultBook: address = empty(address), _ripeHq: address = empty(address)) -> address:
    if _ripeVaultBook != empty(address):
        return _ripeVaultBook
    ripeHq: address = self._getRipeHq(_ripeHq)
    return staticcall Registry(ripeHq).getAddr(RIPE_VAULT_BOOK_ID)


@view
@internal
def _getRipeMissionControl(_ripeMissionControl: address = empty(address), _ripeHq: address = empty(address)) -> address:
    if _ripeMissionControl != empty(address):
        return _ripeMissionControl
    ripeHq: address = self._getRipeHq(_ripeHq)
    return staticcall Registry(ripeHq).getAddr(RIPE_MISSION_CONTROL_ID)


@view
@internal
def _getRipeCreditEngine(_ripeCreditEngine: address = empty(address), _ripeHq: address = empty(address)) -> address:
    if _ripeCreditEngine != empty(address):
        return _ripeCreditEngine
    ripeHq: address = self._getRipeHq(_ripeHq)
    return staticcall Registry(ripeHq).getAddr(RIPE_CREDIT_ENGINE_ID)


@view
@internal
def _getRipePriceDesk(_ripePriceDesk: address = empty(address), _ripeHq: address = empty(address)) -> address:
    if _ripePriceDesk != empty(address):
        return _ripePriceDesk
    ripeHq: address = self._getRipeHq(_ripeHq)
    return staticcall Registry(ripeHq).getAddr(RIPE_PRICE_DESK_ID)