#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

#     ╔════════════════════════════════════════════════════════╗
#     ║  ** LevgVaultTools (Frontend) **                      ║
#     ║  Convenience functions for frontend / web app usage    ║
#     ╚════════════════════════════════════════════════════════╝

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

interface RipeCreditEngine:
    def getMaxBorrowAmount(_user: address) -> uint256: view
    def getUserDebtAmount(_user: address) -> uint256: view
    def getBorrowRate(_user: address) -> uint256: view

interface RipePriceDesk:
    def getAssetAmount(_asset: address, _usdValue: uint256, _shouldRaise: bool = False) -> uint256: view
    def getUsdValue(_asset: address, _amount: uint256, _shouldRaise: bool = False) -> uint256: view

interface YieldLego:
    def getUnderlyingAmountSafe(_vaultToken: address, _vaultTokenBalance: uint256) -> uint256: view
    def getUnderlyingAmount(_vaultToken: address, _vaultTokenAmount: uint256) -> uint256: view

interface RipeRegistry:
    def savingsGreen() -> address: view
    def greenToken() -> address: view

interface RipeDepositVault:
    def getTotalAmountForUser(_user: address, _asset: address) -> uint256: view

interface RipeMissionControl:
    def getFirstVaultIdForAsset(_asset: address) -> uint256: view

interface Ledger:
    def vaultTokens(_vaultToken: address) -> VaultToken: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

interface RipeEndaomentPsm:
    def getAvailableUsdc() -> uint256: view

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
RIPE_ENDAOMENT_PSM_ID: constant(uint256) = 22
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


####################
# Total Underlying #
####################


@view
@external
def getTotalUnderlyingAmount(
    _levgVault: address,
    _isCollateralAsset: bool,
    _shouldGetMax: bool,
    _legoBook: address = empty(address),
    _ripeVaultBook: address = empty(address),
    _ripeMissionControl: address = empty(address),
    _ripeHq: address = empty(address),
) -> uint256:
    vaultToken: address = empty(address)
    ripeVaultId: uint256 = 0
    vaultToken, ripeVaultId = self._getVaultTokenData(_levgVault, _isCollateralAsset)
    if vaultToken == empty(address):
        return 0

    ripeHq: address = self._getRipeHq(_ripeHq)
    ripeVaultBook: address = self._getRipeVaultBook(_ripeVaultBook, ripeHq)
    ripeMissionControl: address = self._getRipeMissionControl(_ripeMissionControl, ripeHq)
    legoBook: address = _legoBook if _legoBook != empty(address) else addys._getLegoBookAddr()

    return self._getTotalUnderlyingAmount(_levgVault, vaultToken, _isCollateralAsset, _shouldGetMax, ripeVaultId, legoBook, ripeVaultBook, ripeMissionControl)


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


####################
# Amount for Asset #
####################


@view
@external
def getAmountForAsset(
    _levgVault: address,
    _asset: address,
    _ripeVaultId: uint256 = 0,
    _ripeVaultBook: address = empty(address),
    _ripeMissionControl: address = empty(address),
    _ripeHq: address = empty(address),
) -> uint256:
    ripeHq: address = self._getRipeHq(_ripeHq)
    ripeVaultBook: address = self._getRipeVaultBook(_ripeVaultBook, ripeHq)
    ripeMissionControl: address = self._getRipeMissionControl(_ripeMissionControl, ripeHq)
    return self._getAmountForAsset(_levgVault, _asset, _ripeVaultId, ripeVaultBook, ripeMissionControl)


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


###############################
# Underlying from Vault Token #
###############################


@view
@external
def getUnderlyingAmountForVaultToken(
    _levgVault: address,
    _isCollateralAsset: bool,
    _shouldGetMax: bool,
    _legoBook: address = empty(address),
    _ripeVaultBook: address = empty(address),
    _ripeMissionControl: address = empty(address),
    _ripeHq: address = empty(address),
) -> uint256:
    vaultToken: address = empty(address)
    ripeVaultId: uint256 = 0
    vaultToken, ripeVaultId = self._getVaultTokenData(_levgVault, _isCollateralAsset)
    if vaultToken == empty(address):
        return 0

    ripeHq: address = self._getRipeHq(_ripeHq)
    ripeVaultBook: address = self._getRipeVaultBook(_ripeVaultBook, ripeHq)
    ripeMissionControl: address = self._getRipeMissionControl(_ripeMissionControl, ripeHq)
    legoBook: address = _legoBook if _legoBook != empty(address) else addys._getLegoBookAddr()

    return self._getUnderlyingAmountForVaultToken(_levgVault, vaultToken, _shouldGetMax, ripeVaultId, legoBook, ripeVaultBook, ripeMissionControl)


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


###################
# Ripe Collateral #
###################


@view
@external
def getRipeCollateralBalance(
    _levgVault: address,
    _asset: address,
    _ripeVaultId: uint256 = 0,
    _ripeVaultBook: address = empty(address),
    _ripeMissionControl: address = empty(address),
    _ripeHq: address = empty(address),
) -> uint256:
    ripeHq: address = self._getRipeHq(_ripeHq)
    ripeVaultBook: address = self._getRipeVaultBook(_ripeVaultBook, ripeHq)
    ripeMissionControl: address = self._getRipeMissionControl(_ripeMissionControl, ripeHq)
    return self._getRipeCollateralBalance(_levgVault, _asset, _ripeVaultId, ripeVaultBook, ripeMissionControl)


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


#################
# GREEN Helpers #
#################


@view
@external
def getUnderlyingGreenAmount(
    _levgVault: address,
    _green: address = empty(address),
    _savingsGreen: address = empty(address),
    _ripeVaultBook: address = empty(address),
    _ripeMissionControl: address = empty(address),
    _ripeHq: address = empty(address),
) -> uint256:
    ripeHq: address = self._getRipeHq(_ripeHq)
    ripeVaultBook: address = self._getRipeVaultBook(_ripeVaultBook, ripeHq)
    ripeMissionControl: address = self._getRipeMissionControl(_ripeMissionControl, ripeHq)
    return self._getUnderlyingGreenAmount(_levgVault, _green, _savingsGreen, ripeVaultBook, ripeMissionControl)


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


################
# Swap Helpers #
################


@view
@external
def getSwappableUsdcAmount(
    _levgVault: address,
    _leverageVaultToken: address = empty(address),
    _leverageVaultTokenRipeVaultId: uint256 = 0,
    _usdc: address = empty(address),
    _green: address = empty(address),
    _savingsGreen: address = empty(address),
    _legoBook: address = empty(address),
    _ripeVaultBook: address = empty(address),
    _ripeMissionControl: address = empty(address),
    _ripeHq: address = empty(address),
) -> uint256:
    # resolve addresses
    ripeHq: address = self._getRipeHq(_ripeHq)
    ripeVaultBook: address = self._getRipeVaultBook(_ripeVaultBook, ripeHq)
    ripeMissionControl: address = self._getRipeMissionControl(_ripeMissionControl, ripeHq)
    legoBook: address = _legoBook if _legoBook != empty(address) else addys._getLegoBookAddr()
    creditEngine: address = self._getRipeCreditEngine(empty(address), ripeHq)
    ripePriceDesk: address = self._getRipePriceDesk(empty(address), ripeHq)

    return self._getSwappableUsdcAmount(_levgVault, _leverageVaultToken, _leverageVaultTokenRipeVaultId, _usdc, _green, _savingsGreen, legoBook, ripeVaultBook, ripeMissionControl, creditEngine, ripePriceDesk)


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


##################
# Borrow Helpers #
##################


@view
@external
def getBorrowRate(_levgVault: address, _ripeHq: address = empty(address)) -> uint256:
    ripeHq: address = self._getRipeHq(_ripeHq)
    creditEngine: address = self._getRipeCreditEngine(empty(address), ripeHq)
    return staticcall RipeCreditEngine(creditEngine).getBorrowRate(_levgVault)


@view
@external
def getDebtAmount(_levgVault: address, _ripeHq: address = empty(address)) -> uint256:
    ripeHq: address = self._getRipeHq(_ripeHq)
    creditEngine: address = self._getRipeCreditEngine(empty(address), ripeHq)
    return staticcall RipeCreditEngine(creditEngine).getUserDebtAmount(_levgVault)


@view
@external
def getAvailableUsdcFromEndaomentPsm(_ripeHq: address = empty(address)) -> uint256:
    ripeHq: address = self._getRipeHq(_ripeHq)
    endaomentPsm: address = staticcall Registry(ripeHq).getAddr(RIPE_ENDAOMENT_PSM_ID)
    return staticcall RipeEndaomentPsm(endaomentPsm).getAvailableUsdc()


# true max borrow amount


@view
@external
def getTrueMaxBorrowAmount(_levgVault: address, _ripeHq: address = empty(address)) -> uint256:
    # resolve addresses
    ripeHq: address = self._getRipeHq(_ripeHq)
    ripeVaultBook: address = self._getRipeVaultBook(empty(address), ripeHq)
    ripeMissionControl: address = self._getRipeMissionControl(empty(address), ripeHq)
    legoBook: address = addys._getLegoBookAddr()
    ripePriceDesk: address = self._getRipePriceDesk(empty(address), ripeHq)
    creditEngine: address = self._getRipeCreditEngine(empty(address), ripeHq)

    maxDebtRatioLimit: uint256 = self._getMaxBorrowAmountByMaxDebtRatio(_levgVault, empty(address), empty(address), 0, empty(address), 0, 0, legoBook, ripeVaultBook, ripeMissionControl, ripePriceDesk, creditEngine)
    maxBorrowAmount: uint256 = self._getMaxBorrowAmountByRipeLtv(_levgVault, creditEngine)
    return min(maxDebtRatioLimit, maxBorrowAmount)


# Max Debt Ratio


@view
@external
def getMaxBorrowAmountByMaxDebtRatio(
    _levgVault: address,
    _underlyingAsset: address = empty(address),
    _collateralVaultToken: address = empty(address),
    _collateralVaultTokenRipeVaultId: uint256 = 0,
    _leverageVaultToken: address = empty(address),
    _netUserCapital: uint256 = 0,
    _maxDebtRatio: uint256 = 0,
    _legoBook: address = empty(address),
    _ripeVaultBook: address = empty(address),
    _ripeMissionControl: address = empty(address),
    _ripeHq: address = empty(address),
) -> uint256:
    # resolve addresses
    ripeHq: address = self._getRipeHq(_ripeHq)
    ripeVaultBook: address = self._getRipeVaultBook(_ripeVaultBook, ripeHq)
    ripeMissionControl: address = self._getRipeMissionControl(_ripeMissionControl, ripeHq)
    legoBook: address = _legoBook if _legoBook != empty(address) else addys._getLegoBookAddr()
    ripePriceDesk: address = self._getRipePriceDesk(empty(address), ripeHq)
    creditEngine: address = self._getRipeCreditEngine(empty(address), ripeHq)

    return self._getMaxBorrowAmountByMaxDebtRatio(_levgVault, _underlyingAsset, _collateralVaultToken, _collateralVaultTokenRipeVaultId, _leverageVaultToken, _netUserCapital, _maxDebtRatio, legoBook, ripeVaultBook, ripeMissionControl, ripePriceDesk, creditEngine)


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

    # current debt amount (in GREEN, 18 decimals, treated as $1 USD)
    currentDebt: uint256 = staticcall RipeCreditEngine(_creditEngine).getUserDebtAmount(_levgVault)

    # user's GREEN can offset debt (GREEN is 18 decimals, treated as $1 USD)
    greenAmount: uint256 = self._getUnderlyingGreenAmount(_levgVault, empty(address), empty(address), _ripeVaultBook, _ripeMissionControl)
    remainingDebt: uint256 = 0
    if currentDebt > greenAmount:
        remainingDebt = currentDebt - greenAmount

    # max allowed debt (in USD)
    maxAllowedDebt: uint256 = underlyingUsdValue * maxDebtRatio // HUNDRED_PERCENT
    if remainingDebt >= maxAllowedDebt:
        return 0

    return maxAllowedDebt - remainingDebt


# Ripe LTV


@view
@external
def getMaxBorrowAmountByRipeLtv(
    _levgVault: address,
    _creditEngine: address = empty(address),
    _ripeHq: address = empty(address),
) -> uint256:
    ripeHq: address = self._getRipeHq(_ripeHq)
    creditEngine: address = self._getRipeCreditEngine(_creditEngine, ripeHq)
    return self._getMaxBorrowAmountByRipeLtv(_levgVault, creditEngine)


@view
@internal
def _getMaxBorrowAmountByRipeLtv(
    _levgVault: address,
    _creditEngine: address,
) -> uint256:
    return staticcall RipeCreditEngine(_creditEngine).getMaxBorrowAmount(_levgVault)


################
# Combinations #
################


# vault token amounts


@view
@external
def getVaultTokenAmounts(
    _levgVault: address,
    _isCollateralAsset: bool,
    _ripeVaultBook: address = empty(address),
    _ripeMissionControl: address = empty(address),
    _ripeHq: address = empty(address),
) -> (uint256, uint256):
    vaultToken: address = empty(address)
    ripeVaultId: uint256 = 0
    vaultToken, ripeVaultId = self._getVaultTokenData(_levgVault, _isCollateralAsset)
    if vaultToken == empty(address) or ripeVaultId == 0:
        return 0, 0

    # resolve ripe addresses
    ripeHq: address = self._getRipeHq(_ripeHq)
    ripeVaultBook: address = self._getRipeVaultBook(_ripeVaultBook, ripeHq)
    ripeMissionControl: address = self._getRipeMissionControl(_ripeMissionControl, ripeHq)

    # 1. vault token in wallet
    vaultTokenInWallet: uint256 = staticcall IERC20(vaultToken).balanceOf(_levgVault)

    # 2. vault token in Ripe
    vaultTokenInRipe: uint256 = self._getRipeCollateralBalance(_levgVault, vaultToken, ripeVaultId, ripeVaultBook, ripeMissionControl)

    return vaultTokenInWallet, vaultTokenInRipe


# underlying amounts


@view
@external
def getUnderlyingAmounts(
    _levgVault: address,
    _isCollateralAsset: bool,
    _shouldGetMax: bool,
    _legoBook: address = empty(address),
    _ripeVaultBook: address = empty(address),
    _ripeMissionControl: address = empty(address),
    _ripeHq: address = empty(address),
) -> (uint256, uint256, uint256, uint256):
    vaultToken: address = empty(address)
    ripeVaultId: uint256 = 0
    vaultToken, ripeVaultId = self._getVaultTokenData(_levgVault, _isCollateralAsset)
    if vaultToken == empty(address) or ripeVaultId == 0:
        return 0, 0, 0, 0

    ripeHq: address = self._getRipeHq(_ripeHq)
    ripeVaultBook: address = self._getRipeVaultBook(_ripeVaultBook, ripeHq)
    ripeMissionControl: address = self._getRipeMissionControl(_ripeMissionControl, ripeHq)
    legoBook: address = _legoBook if _legoBook != empty(address) else addys._getLegoBookAddr()

    return self._getUnderlyingAmounts(_levgVault, vaultToken, ripeVaultId, _shouldGetMax, legoBook, ripeVaultBook, ripeMissionControl)


@view
@internal
def _getUnderlyingAmounts(
    _levgVault: address,
    _vaultToken: address,
    _ripeVaultId: uint256,
    _shouldGetMax: bool,
    _legoBook: address,
    _ripeVaultBook: address,
    _ripeMissionControl: address,
) -> (uint256, uint256, uint256, uint256):
    if _vaultToken == empty(address) or _ripeVaultId == 0:
        return 0, 0, 0, 0

    # 1. underlying asset in wallet
    underlyingAsset: address = staticcall IERC4626(_levgVault).asset()
    underlyingInWallet: uint256 = staticcall IERC20(underlyingAsset).balanceOf(_levgVault)

    # 2. vault token in wallet -> converted to underlying via lego
    vaultTokenInWallet: uint256 = staticcall IERC20(_vaultToken).balanceOf(_levgVault)
    vaultTokenInWalletConverted: uint256 = self._getUnderlyingAmountWithVaultTokenAmount(_levgVault, _vaultToken, vaultTokenInWallet, _shouldGetMax, 0, _legoBook)

    # 3. underlying asset deposited in Ripe Protocol (raw)
    underlyingInRipe: uint256 = self._getRipeCollateralBalance(_levgVault, underlyingAsset, 0, _ripeVaultBook, _ripeMissionControl)

    # 4. vault token in Ripe -> converted to underlying via lego
    vaultTokenInRipe: uint256 = self._getRipeCollateralBalance(_levgVault, _vaultToken, _ripeVaultId, _ripeVaultBook, _ripeMissionControl)
    vaultTokenInRipeConverted: uint256 = self._getUnderlyingAmountWithVaultTokenAmount(_levgVault, _vaultToken, vaultTokenInRipe, _shouldGetMax, 0, _legoBook)

    return underlyingInWallet, vaultTokenInWalletConverted, underlyingInRipe, vaultTokenInRipeConverted


# green amounts


@view
@external
def getGreenAmounts(
    _levgVault: address,
    _green: address = empty(address),
    _savingsGreen: address = empty(address),
    _ripeVaultBook: address = empty(address),
    _ripeMissionControl: address = empty(address),
    _ripeHq: address = empty(address),
) -> (uint256, uint256, uint256, uint256):
    # resolve ripe addresses
    ripeHq: address = self._getRipeHq(_ripeHq)
    ripeVaultBook: address = self._getRipeVaultBook(_ripeVaultBook, ripeHq)
    ripeMissionControl: address = self._getRipeMissionControl(_ripeMissionControl, ripeHq)

    # 1. user debt in Ripe Protocol (denominated in GREEN)
    creditEngine: address = self._getRipeCreditEngine(empty(address), ripeHq)
    userDebt: uint256 = staticcall RipeCreditEngine(creditEngine).getUserDebtAmount(_levgVault)

    # 2. GREEN in wallet
    green: address = _green if _green != empty(address) else GREEN_TOKEN
    greenInWallet: uint256 = staticcall IERC20(green).balanceOf(_levgVault)

    # 3. sGREEN in wallet -> converted to GREEN
    savingsGreen: address = _savingsGreen if _savingsGreen != empty(address) else SAVINGS_GREEN
    sGreenInWalletConverted: uint256 = 0
    sGreenInWallet: uint256 = staticcall IERC20(savingsGreen).balanceOf(_levgVault)
    if sGreenInWallet != 0:
        sGreenInWalletConverted = staticcall IERC4626(savingsGreen).previewRedeem(sGreenInWallet)

    # 4. sGREEN in Ripe -> converted to GREEN
    sGreenInRipeConverted: uint256 = 0
    sGreenInRipe: uint256 = self._getRipeCollateralBalance(_levgVault, savingsGreen, STAB_POOL_ID, ripeVaultBook, ripeMissionControl)
    if sGreenInRipe != 0:
        sGreenInRipeConverted = staticcall IERC4626(savingsGreen).previewRedeem(sGreenInRipe)

    return userDebt, greenInWallet, sGreenInWalletConverted, sGreenInRipeConverted


#############
# Utilities #
#############


# get lego id


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


# get vault token data


@view
@internal
def _getVaultTokenData(_levgVault: address, _isCollateralAsset: bool) -> (address, uint256):
    assetData: RipeAsset = empty(RipeAsset)
    if _isCollateralAsset:
        assetData = staticcall LevgVault(_levgVault).collateralAsset()
    else:
        assetData = staticcall LevgVault(_levgVault).leverageAsset()
    return assetData.vaultToken, assetData.ripeVaultId


# ripe addrs


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


@view
@internal
def _getRipeHq(_ripeHq: address = empty(address)) -> address:
    if _ripeHq != empty(address):
        return _ripeHq
    return RIPE_REGISTRY
