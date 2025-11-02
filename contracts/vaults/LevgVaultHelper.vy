#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

exports: addys.__interface__
initializes: addys
import contracts.modules.Addys as addys

from ethereum.ercs import IERC20
from ethereum.ercs import IERC4626

interface RipePriceDesk:
    def getAssetAmount(_asset: address, _usdValue: uint256, _shouldRaise: bool = False) -> uint256: view
    def getUsdValue(_asset: address, _amount: uint256, _shouldRaise: bool = False) -> uint256: view

interface YieldLego:
    def getUnderlyingAmount(_vaultToken: address, _vaultTokenAmount: uint256) -> uint256: view
    def canRegisterVaultToken(_asset: address, _vaultToken: address) -> bool: view

interface RipeMissionControl:
    def isSupportedAssetInVault(_vaultId: uint256, _asset: address) -> bool: view
    def getFirstVaultIdForAsset(_asset: address) -> uint256: view

interface RipeRegistry:
    def savingsGreen() -> address: view
    def greenToken() -> address: view

interface RipeDepositVault:
    def getTotalAmountForUser(_user: address, _asset: address) -> uint256: view

interface RipeCreditEngine:
    def getUserDebtAmount(_user: address) -> uint256: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

# ripe addrs
RIPE_REGISTRY: public(immutable(address))
GREEN_TOKEN: public(immutable(address))
SAVINGS_GREEN: public(immutable(address))
USDC: public(immutable(address))

RIPE_MISSION_CONTROL_ID: constant(uint256) = 5
RIPE_PRICE_DESK_ID: constant(uint256) = 7
RIPE_VAULT_BOOK_ID: constant(uint256) = 8
RIPE_CREDIT_ENGINE_ID: constant(uint256) = 13

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

    # usdc balance
    usdcAmount: uint256 = _currentBalance

    # usdc on ripe protocol
    ripeMc: address = staticcall Registry(ripeHq).getAddr(RIPE_MISSION_CONTROL_ID)
    ripeVaultBook: address = staticcall Registry(ripeHq).getAddr(RIPE_VAULT_BOOK_ID)
    if _leverageVaultTokenRipeVaultId != 0:
        ripeDepositAddr: address = staticcall Registry(ripeVaultBook).getAddr(_leverageVaultTokenRipeVaultId)
        usdcAmount += self._getCollateralBalance(_wallet, usdc, ripeDepositAddr)

    # usdc via leverage vault
    usdcAmount += self._getUnderlyingForVaultToken(_wallet, _leverageVaultToken, _leverageVaultTokenLegoId, _leverageVaultTokenRipeVaultId, legoBook, ripeMc, ripeVaultBook) # 6 decimals

    # get USD value
    ripePriceDesk: address = staticcall Registry(ripeHq).getAddr(RIPE_PRICE_DESK_ID)
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
    usdcAmount: uint256 = self._getUnderlyingAmountForLevgVault(
        _wallet,
        usdc,
        _collateralVaultToken,
        _collateralVaultTokenLegoId,
        _collateralVaultTokenRipeVaultId,
        _leverageVaultToken,
        _leverageVaultTokenLegoId,
        _leverageVaultTokenRipeVaultId,
        True,
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
    underlyingAmount: uint256 = self._getUnderlyingAmountForLevgVault(
        _wallet,
        _underlyingAsset,
        _collateralVaultToken,
        _collateralVaultTokenLegoId,
        _collateralVaultTokenRipeVaultId,
        _leverageVaultToken,
        _leverageVaultTokenLegoId,
        _leverageVaultTokenRipeVaultId,
        False, # !
        legoBook,
        ripeMc,
        ripeVaultBook,
    )

    # phase 2: get USDC (wallet + leverage vault)
    usdcAmount: uint256 = staticcall IERC20(usdc).balanceOf(_wallet)
    usdcAmount += self._getUnderlyingForVaultToken(_wallet, _leverageVaultToken, _leverageVaultTokenLegoId, _leverageVaultTokenRipeVaultId, legoBook, ripeMc, ripeVaultBook)
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
    ripeVaultId: uint256 = staticcall RipeMissionControl(_ripeMissionControl).getFirstVaultIdForAsset(_savingsGreen)
    if ripeVaultId != 0:
        ripeDepositAddr: address = staticcall Registry(_ripeVaultBook).getAddr(ripeVaultId)
        savingsGreenAmount += self._getCollateralBalance(_wallet, _savingsGreen, ripeDepositAddr)

    # calc underlying amount
    if savingsGreenAmount != 0:
        greenAmount += self._getUnderlyingAmount(_savingsGreen, savingsGreenAmount)

    return greenAmount


# underlying amount for leverage vault


@view
@internal
def _getUnderlyingAmountForLevgVault(
    _wallet: address,
    _underlyingAsset: address,
    _collateralVaultToken: address,
    _collateralVaultTokenLegoId: uint256,
    _collateralVaultTokenRipeVaultId: uint256,
    _leverageVaultToken: address,
    _leverageVaultTokenLegoId: uint256,
    _leverageVaultTokenRipeVaultId: uint256,
    _haveSameUnderlyingAsset: bool,
    _legoBook: address,
    _ripeMissionControl: address,
    _ripeVaultBook: address,
) -> uint256:
    underlyingAmount: uint256 = staticcall IERC20(_underlyingAsset).balanceOf(_wallet)

    # check if underlying asset is in a ripe vault
    if _collateralVaultTokenRipeVaultId != 0:
        ripeDepositAddr: address = staticcall Registry(_ripeVaultBook).getAddr(_collateralVaultTokenRipeVaultId)
        underlyingAmount += self._getCollateralBalance(_wallet, _underlyingAsset, ripeDepositAddr)

    # collateral vault amount
    underlyingAmount += self._getUnderlyingForVaultToken(_wallet, _collateralVaultToken, _collateralVaultTokenLegoId, _collateralVaultTokenRipeVaultId, _legoBook, _ripeMissionControl, _ripeVaultBook)

    # leverage vault amount
    if _haveSameUnderlyingAsset and _collateralVaultToken != _leverageVaultToken:
        underlyingAmount += self._getUnderlyingForVaultToken(_wallet, _leverageVaultToken, _leverageVaultTokenLegoId, _leverageVaultTokenRipeVaultId, _legoBook, _ripeMissionControl, _ripeVaultBook)

    return underlyingAmount


# underlying amount for vault token


@view
@internal
def _getUnderlyingForVaultToken(
    _wallet: address,
    _vaultToken: address,
    _vaultTokenLegoId: uint256,
    _ripeVaultId: uint256,
    _legoBook: address,
    _ripeMissionControl: address,
    _ripeVaultBook: address,
) -> uint256:
    if _vaultToken == empty(address):
        return 0

    vaultTokenAmount: uint256 = staticcall IERC20(_vaultToken).balanceOf(_wallet)

    if _ripeVaultId != 0:
        ripeDepositAddr: address = staticcall Registry(_ripeVaultBook).getAddr(_ripeVaultId)
        vaultTokenAmount += self._getCollateralBalance(_wallet, _vaultToken, ripeDepositAddr)

    if vaultTokenAmount == 0:
        return 0

    # calc underlying amount
    underlyingAmount: uint256 = 0
    legoAddr: address = staticcall Registry(_legoBook).getAddr(_vaultTokenLegoId)
    if legoAddr != empty(address):
        underlyingAmount = staticcall YieldLego(legoAddr).getUnderlyingAmount(_vaultToken, vaultTokenAmount)
    
    return underlyingAmount


# collateral balance


@view
@external
def getCollateralBalance(_user: address, _asset: address, _ripeVaultId: uint256) -> uint256:
    ripeHq: address = RIPE_REGISTRY
    mc: address = staticcall Registry(ripeHq).getAddr(RIPE_MISSION_CONTROL_ID)
    ripeVaultId: uint256 = _ripeVaultId
    if ripeVaultId == 0:
        ripeVaultId = staticcall RipeMissionControl(mc).getFirstVaultIdForAsset(_asset)
    vaultBook: address = staticcall Registry(ripeHq).getAddr(RIPE_VAULT_BOOK_ID)
    vaultAddr: address = staticcall Registry(vaultBook).getAddr(ripeVaultId)
    return self._getCollateralBalance(_user, _asset, vaultAddr)


@view
@internal
def _getCollateralBalance(_user: address, _asset: address, _vaultAddr: address) -> uint256:
    return staticcall RipeDepositVault(_vaultAddr).getTotalAmountForUser(_user, _asset)


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