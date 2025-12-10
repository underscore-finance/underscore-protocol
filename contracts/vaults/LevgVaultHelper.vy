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
    def asset() -> address: view
    def USDC() -> address: view

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
    def getUserDebtAmount(_user: address) -> uint256: view
    def getBorrowRate(_user: address) -> uint256: view

interface RipeRegistry:
    def savingsGreen() -> address: view
    def greenToken() -> address: view

interface RipeDepositVault:
    def getTotalAmountForUser(_user: address, _asset: address) -> uint256: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

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
    usdc: address = _usdc if _usdc != empty(address) else USDC
    green: address = _green if _green != empty(address) else GREEN_TOKEN
    savingsGreen: address = _savingsGreen if _savingsGreen != empty(address) else SAVINGS_GREEN
    legoBook: address = _legoBook if _legoBook != empty(address) else addys._getLegoBookAddr()

    # user debt amount
    ripeHq: address = RIPE_REGISTRY
    creditEngine: address = staticcall Registry(ripeHq).getAddr(RIPE_CREDIT_ENGINE_ID)
    userDebtAmount: uint256 = self._getUserDebtAmount(_wallet, creditEngine) # 18 decimals
    if userDebtAmount == 0:
        return _amountIn

    # more ripe addrs
    ripeMc: address = staticcall Registry(ripeHq).getAddr(RIPE_MISSION_CONTROL_ID)
    ripeVaultBook: address = staticcall Registry(ripeHq).getAddr(RIPE_VAULT_BOOK_ID)
    ripePriceDesk: address = staticcall Registry(ripeHq).getAddr(RIPE_PRICE_DESK_ID)

    # usdc balance (in wallet, naked on ripe, via leverage vault)
    usdcAmount: uint256 = _currentBalance
    usdcAmount += self._getCollateralBalanceNoRipeVaultId(_wallet, usdc, ripeMc, ripeVaultBook)
    usdcAmount += self._getUnderlyingForVaultToken(
        _wallet,
        _leverageVaultToken,
        _leverageVaultTokenLegoId,
        _leverageVaultTokenRipeVaultId,
        False, # safe underlying amount
        legoBook,
        ripeVaultBook,
    )

    # convert to USD value
    usdcValue: uint256 = self._getUsdValue(usdc, usdcAmount, True, ripePriceDesk) # 18 decimals

    # green amount
    greenSurplusAmount: uint256 = self._getUnderlyingGreenAmount(_wallet, green, savingsGreen, ripeMc, ripeVaultBook)
    positiveValue: uint256 = greenSurplusAmount + usdcValue # treat green as $1 USD (most conservative, in this case)

    # compare usd values
    if userDebtAmount > positiveValue:
        return 0

    # calc asset amount
    availUsdcAmount: uint256 = self._getAssetAmount(usdc, positiveValue - userDebtAmount, True, ripePriceDesk) # 6 decimals
    return min(availUsdcAmount, _amountIn)


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
    if _maxDebtRatio == 0:
        return max_value(uint256)

    legoBook: address = _legoBook if _legoBook != empty(address) else addys._getLegoBookAddr()

    # ripe addresses
    ripeHq: address = RIPE_REGISTRY
    ripeMc: address = staticcall Registry(ripeHq).getAddr(RIPE_MISSION_CONTROL_ID)
    ripeVaultBook: address = staticcall Registry(ripeHq).getAddr(RIPE_VAULT_BOOK_ID)
    priceDesk: address = staticcall Registry(ripeHq).getAddr(RIPE_PRICE_DESK_ID)
    creditEngine: address = staticcall Registry(ripeHq).getAddr(RIPE_CREDIT_ENGINE_ID)

    # NOTE: for usdc vaults, there may not be a clear distinction between collateral and leverage vaults
    # so using netUserCapital as the underlying asset amount for extra safety

    # get underlying asset amount
    underlyingAmount: uint256 = 0
    if _isUsdcVault:
        underlyingAmount = _netUserCapital
    else:
        underlyingAmount = self._getTotalUnderlying(
            _wallet,
            _underlyingAsset,
            _collateralVaultToken,
            _collateralVaultTokenLegoId,
            _collateralVaultTokenRipeVaultId,
            empty(address),
            0,
            0,
            False, # !
            False, # safe underlying amount
            legoBook,
            ripeMc,
            ripeVaultBook,
        )

    # convert to USD value
    underlyingUsdValue: uint256 = self._getUsdValue(_underlyingAsset, underlyingAmount, True, priceDesk)

    # current debt amount (in GREEN, 18 decimals, treated as $1 USD)
    currentDebt: uint256 = self._getUserDebtAmount(_wallet, creditEngine)

    # max allowed debt (in USD)
    maxAllowedDebt: uint256 = underlyingUsdValue * _maxDebtRatio // HUNDRED_PERCENT
    if currentDebt >= maxAllowedDebt:
        return 0

    return maxAllowedDebt - currentDebt


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
        usdcValue: uint256 = self._getUsdValue(usdc, _tokenOutAmount, True, ripePriceDesk)

        # Minimum expected: greenAmount * (10000 - slippage) / 10000
        # GREEN is 18 decimals and treated as $1 USD, so greenAmount = USD value
        minExpected: uint256 = _tokenInAmount * (HUNDRED_PERCENT - _usdcSlippageAllowed) // HUNDRED_PERCENT
        return usdcValue >= minExpected

    # USDC -> GREEN swap validation
    elif _tokenIn == usdc and _tokenOut == green:

        # Get USD value of USDC sent (18 decimals)
        ripePriceDesk: address = staticcall Registry(RIPE_REGISTRY).getAddr(RIPE_PRICE_DESK_ID)
        usdcValue: uint256 = self._getUsdValue(usdc, _tokenInAmount, True, ripePriceDesk)

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
    savingsGreen: address = _savingsGreen if _savingsGreen != empty(address) else SAVINGS_GREEN
    legoBook: address = _legoBook if _legoBook != empty(address) else addys._getLegoBookAddr()

    # ripe addresses
    ripeHq: address = RIPE_REGISTRY
    ripeMc: address = staticcall Registry(ripeHq).getAddr(RIPE_MISSION_CONTROL_ID)
    ripeVaultBook: address = staticcall Registry(ripeHq).getAddr(RIPE_VAULT_BOOK_ID)
    creditEngine: address = staticcall Registry(ripeHq).getAddr(RIPE_CREDIT_ENGINE_ID)

    # usdc amount
    usdcAmount: uint256 = self._getTotalUnderlying(
        _wallet,
        usdc,
        _collateralVaultToken,
        _collateralVaultTokenLegoId,
        _collateralVaultTokenRipeVaultId,
        _leverageVaultToken,
        _leverageVaultTokenLegoId,
        _leverageVaultTokenRipeVaultId,
        True,
        _shouldGetMax,
        legoBook,
        ripeMc,
        ripeVaultBook,
    )

    # green amounts
    userDebtAmount: uint256 = self._getUserDebtAmount(_wallet, creditEngine) # 18 decimals
    greenSurplusAmount: uint256 = self._getUnderlyingGreenAmount(_wallet, green, savingsGreen, ripeMc, ripeVaultBook)

    # adjust usdc values based on green situation
    if userDebtAmount > greenSurplusAmount:
        userDebtAmount -= greenSurplusAmount # treat green as $1 USD (most conservative, in this case)
        usdcAmount -= min(usdcAmount, userDebtAmount // (10 ** 12)) # normalize to 6 decimals

    elif greenSurplusAmount > userDebtAmount:
        ripePriceDesk: address = staticcall Registry(ripeHq).getAddr(RIPE_PRICE_DESK_ID)
        extraGreen: uint256 = greenSurplusAmount - userDebtAmount
        usdValueOfGreen: uint256 = min(self._getUsdValue(green, extraGreen, True, ripePriceDesk), extraGreen) # both 18 decimals
        usdcAmount += self._getAssetAmount(usdc, usdValueOfGreen, True, ripePriceDesk)

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
    savingsGreen: address = _savingsGreen if _savingsGreen != empty(address) else SAVINGS_GREEN
    legoBook: address = _legoBook if _legoBook != empty(address) else addys._getLegoBookAddr()

    # ripe addresses
    ripeHq: address = RIPE_REGISTRY
    ripeMc: address = staticcall Registry(ripeHq).getAddr(RIPE_MISSION_CONTROL_ID)
    ripeVaultBook: address = staticcall Registry(ripeHq).getAddr(RIPE_VAULT_BOOK_ID)
    creditEngine: address = staticcall Registry(ripeHq).getAddr(RIPE_CREDIT_ENGINE_ID)
    ripePriceDesk: address = staticcall Registry(ripeHq).getAddr(RIPE_PRICE_DESK_ID)

    # phase 1: get underlying asset amount (WETH/CBBTC/etc)
    underlyingAmount: uint256 = self._getTotalUnderlying(
        _wallet,
        _underlyingAsset,
        _collateralVaultToken,
        _collateralVaultTokenLegoId,
        _collateralVaultTokenRipeVaultId,
        _leverageVaultToken,
        _leverageVaultTokenLegoId,
        _leverageVaultTokenRipeVaultId,
        False, # !
        _shouldGetMax,
        legoBook,
        ripeMc,
        ripeVaultBook,
    )

    # phase 2: get USDC (wallet + naked on ripe + leverage vault)
    usdcAmount: uint256 = staticcall IERC20(usdc).balanceOf(_wallet)
    usdcAmount += self._getCollateralBalanceNoRipeVaultId(_wallet, usdc, ripeMc, ripeVaultBook)
    usdcAmount += self._getUnderlyingForVaultToken(_wallet, _leverageVaultToken, _leverageVaultTokenLegoId, _leverageVaultTokenRipeVaultId, _shouldGetMax, legoBook, ripeVaultBook)
    usdcValue: uint256 = self._getUsdValue(usdc, usdcAmount, True, ripePriceDesk) # 18 decimals

    # phase 3: calculate GREEN position
    userDebtAmount: uint256 = self._getUserDebtAmount(_wallet, creditEngine) # 18 decimals
    greenSurplusAmount: uint256 = self._getUnderlyingGreenAmount(_wallet, green, savingsGreen, ripeMc, ripeVaultBook)

    # phase 4: convert (USDC +/- GREEN) to underlying asset and add/subtract
    if userDebtAmount > greenSurplusAmount:

        # net debt scenario: we owe GREEN
        netDebt: uint256 = userDebtAmount - greenSurplusAmount # 18 decimals, treat GREEN as $1 USD (most conservative, in this case)

        # USDC covers debt with surplus
        if usdcValue > netDebt:
            netPositiveValue: uint256 = usdcValue - netDebt
            underlyingAmount += self._getAssetAmount(_underlyingAsset, netPositiveValue, True, ripePriceDesk)

        # debt exceeds USDC value - leverage vault is underwater
        else:
            netNegativeValue: uint256 = netDebt - usdcValue
            underlyingToSubtract: uint256 = self._getAssetAmount(_underlyingAsset, netNegativeValue, True, ripePriceDesk)
            underlyingAmount -= min(underlyingAmount, underlyingToSubtract)

    else:
        extraGreen: uint256 = greenSurplusAmount - userDebtAmount # net surplus scenario: we have extra GREEN (or zero)
        greenValue: uint256 = min(self._getUsdValue(green, extraGreen, True, ripePriceDesk), extraGreen) # both 18 decimals
        totalPositiveValue: uint256 = usdcValue + greenValue
        underlyingAmount += self._getAssetAmount(_underlyingAsset, totalPositiveValue, True, ripePriceDesk)

    return underlyingAmount


# underlying green amount


@view
@internal
def _getUnderlyingGreenAmount(
    _wallet: address,
    _green: address,
    _savingsGreen: address,
    _ripeMissionControl: address,
    _ripeVaultBook: address,
) -> uint256:
    greenAmount: uint256 = staticcall IERC20(_green).balanceOf(_wallet)

    # savings green balance
    savingsGreenAmount: uint256= staticcall IERC20(_savingsGreen).balanceOf(_wallet)

    # savings green on ripe protocol
    savingsGreenAmount += self._getCollateralBalanceNoRipeVaultId(_wallet, _savingsGreen, _ripeMissionControl, _ripeVaultBook)

    # calc underlying amount
    if savingsGreenAmount != 0:
        greenAmount += self._getUnderlyingAmount(_savingsGreen, savingsGreenAmount)

    return greenAmount


# underlying amount


@view
@internal
def _getTotalUnderlying(
    _wallet: address,
    _underlyingAsset: address,
    _collateralVaultToken: address,
    _collateralVaultTokenLegoId: uint256,
    _collateralVaultTokenRipeVaultId: uint256,
    _leverageVaultToken: address,
    _leverageVaultTokenLegoId: uint256,
    _leverageVaultTokenRipeVaultId: uint256,
    _haveSameUnderlyingAsset: bool,
    _shouldGetMax: bool,
    _legoBook: address,
    _ripeMissionControl: address,
    _ripeVaultBook: address,
) -> uint256:
    underlyingAmount: uint256 = staticcall IERC20(_underlyingAsset).balanceOf(_wallet)

    # check if underlying asset is on ripe protocol
    underlyingAmount += self._getCollateralBalanceNoRipeVaultId(_wallet, _underlyingAsset, _ripeMissionControl, _ripeVaultBook)

    # collateral vault amount
    underlyingAmount += self._getUnderlyingForVaultToken(_wallet, _collateralVaultToken, _collateralVaultTokenLegoId, _collateralVaultTokenRipeVaultId, _shouldGetMax, _legoBook, _ripeVaultBook)

    # leverage vault amount
    if _haveSameUnderlyingAsset and _collateralVaultToken != _leverageVaultToken:
        underlyingAmount += self._getUnderlyingForVaultToken(_wallet, _leverageVaultToken, _leverageVaultTokenLegoId, _leverageVaultTokenRipeVaultId, _shouldGetMax, _legoBook, _ripeVaultBook)

    return underlyingAmount


# underlying amount for vault token


@view
@internal
def _getUnderlyingForVaultToken(
    _wallet: address,
    _vaultToken: address,
    _vaultTokenLegoId: uint256,
    _ripeVaultId: uint256,
    _shouldGetMax: bool,
    _legoBook: address,
    _ripeVaultBook: address,
) -> uint256:
    if _vaultToken == empty(address):
        return 0

    # vault token local balance
    vaultTokenAmount: uint256 = staticcall IERC20(_vaultToken).balanceOf(_wallet)

    # vault token on ripe protocol
    if _ripeVaultId != 0:
        ripeDepositAddr: address = staticcall Registry(_ripeVaultBook).getAddr(_ripeVaultId)
        if ripeDepositAddr != empty(address):
            vaultTokenAmount += self._getCollateralBalance(_wallet, _vaultToken, ripeDepositAddr)

    if vaultTokenAmount == 0:
        return 0

    # calc underlying amount
    underlyingAmount: uint256 = 0
    legoAddr: address = staticcall Registry(_legoBook).getAddr(_vaultTokenLegoId)
    if legoAddr != empty(address):
        if _shouldGetMax:
            underlyingAmount = staticcall YieldLego(legoAddr).getUnderlyingAmount(_vaultToken, vaultTokenAmount)
        else:
            underlyingAmount = staticcall YieldLego(legoAddr).getUnderlyingAmountSafe(_vaultToken, vaultTokenAmount)
    
    return underlyingAmount


# collateral balance


@view
@external
def getCollateralBalance(_user: address, _asset: address, _ripeVaultId: uint256, _vaultBook: address = empty(address)) -> uint256:
    ripeHq: address = empty(address)

    ripeVaultId: uint256 = _ripeVaultId
    if ripeVaultId == 0:
        ripeHq = RIPE_REGISTRY
        mc: address = staticcall Registry(ripeHq).getAddr(RIPE_MISSION_CONTROL_ID)
        ripeVaultId = staticcall RipeMissionControl(mc).getFirstVaultIdForAsset(_asset)

    vaultBook: address = _vaultBook
    if _vaultBook == empty(address):
        ripeHq = ripeHq if ripeHq != empty(address) else RIPE_REGISTRY
        vaultBook = staticcall Registry(ripeHq).getAddr(RIPE_VAULT_BOOK_ID)

    vaultAddr: address = staticcall Registry(vaultBook).getAddr(ripeVaultId)
    if vaultAddr == empty(address):
        return 0

    return self._getCollateralBalance(_user, _asset, vaultAddr)


@view
@internal
def _getCollateralBalance(_user: address, _asset: address, _vaultAddr: address) -> uint256:
    return staticcall RipeDepositVault(_vaultAddr).getTotalAmountForUser(_user, _asset)


# collateral balance no ripe vault id


@view
@internal
def _getCollateralBalanceNoRipeVaultId(_user: address, _asset: address, _ripeMc: address, _ripeVaultBook: address) -> uint256:
    underlyingRipeId: uint256 = staticcall RipeMissionControl(_ripeMc).getFirstVaultIdForAsset(_asset)
    if underlyingRipeId == 0:
        return 0
    ripeDepositAddr: address = staticcall Registry(_ripeVaultBook).getAddr(underlyingRipeId)
    if ripeDepositAddr == empty(address):
        return 0
    return self._getCollateralBalance(_user, _asset, ripeDepositAddr)


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


# user debt amount


@view
@internal
def _getUserDebtAmount(_user: address, _creditEngine: address) -> uint256:
    return staticcall RipeCreditEngine(_creditEngine).getUserDebtAmount(_user)


# price related


@view
@internal
def _getAssetAmount(_asset: address, _usdValue: uint256, _shouldRaise: bool, _ripePriceDesk: address) -> uint256:
    return staticcall RipePriceDesk(_ripePriceDesk).getAssetAmount(_asset, _usdValue, _shouldRaise)


@view
@internal
def _getUsdValue(_asset: address, _amount: uint256, _shouldRaise: bool, _ripePriceDesk: address) -> uint256:
    return staticcall RipePriceDesk(_ripePriceDesk).getUsdValue(_asset, _amount, _shouldRaise)


# underlying amount (true)


@view
@internal
def _getUnderlyingAmount(_vaultToken: address, _vaultTokenAmount: uint256) -> uint256:
    return staticcall IERC4626(_vaultToken).convertToAssets(_vaultTokenAmount)


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


####################
# Helper Functions #
####################


@view
@external
def getBorrowRate(_levgVault: address) -> uint256:
    creditEngine: address = staticcall Registry(RIPE_REGISTRY).getAddr(RIPE_CREDIT_ENGINE_ID)
    return staticcall RipeCreditEngine(creditEngine).getBorrowRate(_levgVault)


@view
@external
def getDebtAmount(_levgVault: address) -> uint256:
    creditEngine: address = staticcall Registry(RIPE_REGISTRY).getAddr(RIPE_CREDIT_ENGINE_ID)
    return staticcall RipeCreditEngine(creditEngine).getUserDebtAmount(_levgVault)


# vault token amounts


@view
@external
def getVaultTokenAmounts(_levgVault: address, _isCollateralAsset: bool) -> (uint256, uint256):
    assetData: RipeAsset = empty(RipeAsset)
    if _isCollateralAsset:
        assetData = staticcall LevgVault(_levgVault).collateralAsset()
    else:
        assetData = staticcall LevgVault(_levgVault).leverageAsset()

    vaultToken: address = assetData.vaultToken
    ripeVaultId: uint256 = assetData.ripeVaultId

    # 1. vault token in wallet
    vaultTokenInWallet: uint256 = 0
    if vaultToken != empty(address):
        vaultTokenInWallet = staticcall IERC20(vaultToken).balanceOf(_levgVault)

    # 2. vault token in Ripe
    vaultTokenInRipe: uint256 = 0
    if vaultToken != empty(address) and ripeVaultId != 0:
        ripeVaultBook: address = staticcall Registry(RIPE_REGISTRY).getAddr(RIPE_VAULT_BOOK_ID)
        ripeDepositAddr: address = staticcall Registry(ripeVaultBook).getAddr(ripeVaultId)
        if ripeDepositAddr != empty(address):
            vaultTokenInRipe = self._getCollateralBalance(_levgVault, vaultToken, ripeDepositAddr)

    return vaultTokenInWallet, vaultTokenInRipe


# underlying amounts


@view
@external
def getUnderlyingAmounts(_levgVault: address, _isCollateralAsset: bool) -> (uint256, uint256, uint256, uint256):
    underlyingAsset: address = empty(address)
    assetData: RipeAsset = empty(RipeAsset)
    if _isCollateralAsset:
        underlyingAsset = staticcall LevgVault(_levgVault).asset()
        assetData = staticcall LevgVault(_levgVault).collateralAsset()
    else:
        underlyingAsset = staticcall LevgVault(_levgVault).USDC()
        assetData = staticcall LevgVault(_levgVault).leverageAsset()

    vaultToken: address = assetData.vaultToken
    ripeVaultId: uint256 = assetData.ripeVaultId
    legoBook: address = addys._getLegoBookAddr()

    # 1. underlying asset in wallet
    underlyingInWallet: uint256 = staticcall IERC20(underlyingAsset).balanceOf(_levgVault)

    # 2. vault token in wallet -> converted to underlying via lego
    vaultTokenInWalletConverted: uint256 = 0
    if vaultToken != empty(address):
        vaultTokenInWallet: uint256 = staticcall IERC20(vaultToken).balanceOf(_levgVault)
        if vaultTokenInWallet != 0:
            legoId: uint256 = staticcall LevgVault(_levgVault).vaultToLegoId(vaultToken)
            legoAddr: address = staticcall Registry(legoBook).getAddr(legoId)
            if legoAddr != empty(address):
                vaultTokenInWalletConverted = staticcall YieldLego(legoAddr).getUnderlyingAmount(vaultToken, vaultTokenInWallet)

    # ripe addresses
    ripeHq: address = RIPE_REGISTRY
    ripeMc: address = staticcall Registry(ripeHq).getAddr(RIPE_MISSION_CONTROL_ID)
    ripeVaultBook: address = staticcall Registry(ripeHq).getAddr(RIPE_VAULT_BOOK_ID)

    # 3. underlying asset deposited in Ripe Protocol (raw)
    underlyingInRipe: uint256 = self._getCollateralBalanceNoRipeVaultId(_levgVault, underlyingAsset, ripeMc, ripeVaultBook)

    # 4. vault token in Ripe -> converted to underlying via lego
    vaultTokenInRipeConverted: uint256 = 0
    if vaultToken != empty(address) and ripeVaultId != 0:
        ripeDepositAddr: address = staticcall Registry(ripeVaultBook).getAddr(ripeVaultId)
        if ripeDepositAddr != empty(address):
            vaultTokenInRipe: uint256 = self._getCollateralBalance(_levgVault, vaultToken, ripeDepositAddr)
            if vaultTokenInRipe != 0:
                legoId: uint256 = staticcall LevgVault(_levgVault).vaultToLegoId(vaultToken)
                legoAddr: address = staticcall Registry(legoBook).getAddr(legoId)
                if legoAddr != empty(address):
                    vaultTokenInRipeConverted = staticcall YieldLego(legoAddr).getUnderlyingAmount(vaultToken, vaultTokenInRipe)

    return underlyingInWallet, vaultTokenInWalletConverted, underlyingInRipe, vaultTokenInRipeConverted


# green amounts


@view
@external
def getGreenAmounts(_levgVault: address) -> (uint256, uint256, uint256, uint256):
    ripeHq: address = RIPE_REGISTRY
    ripeMc: address = staticcall Registry(ripeHq).getAddr(RIPE_MISSION_CONTROL_ID)
    ripeVaultBook: address = staticcall Registry(ripeHq).getAddr(RIPE_VAULT_BOOK_ID)
    creditEngine: address = staticcall Registry(ripeHq).getAddr(RIPE_CREDIT_ENGINE_ID)

    # 1. user debt in Ripe Protocol (denominated in GREEN)
    userDebt: uint256 = self._getUserDebtAmount(_levgVault, creditEngine)

    # 2. GREEN in wallet
    greenInWallet: uint256 = staticcall IERC20(GREEN_TOKEN).balanceOf(_levgVault)

    # 3. sGREEN in wallet -> converted to GREEN
    savingsGreen: address = SAVINGS_GREEN
    sGreenInWalletConverted: uint256 = 0
    sGreenInWallet: uint256 = staticcall IERC20(savingsGreen).balanceOf(_levgVault)
    if sGreenInWallet != 0:
        sGreenInWalletConverted = self._getUnderlyingAmount(savingsGreen, sGreenInWallet)

    # 4. sGREEN in Ripe -> converted to GREEN
    sGreenInRipeConverted: uint256 = 0
    sGreenInRipe: uint256 = self._getCollateralBalanceNoRipeVaultId(_levgVault, savingsGreen, ripeMc, ripeVaultBook)
    if sGreenInRipe != 0:
        sGreenInRipeConverted = self._getUnderlyingAmount(savingsGreen, sGreenInRipe)

    return userDebt, greenInWallet, sGreenInWalletConverted, sGreenInRipeConverted
