#     __   __ ___ _______ ___     ______       ___     _______ _______ _______ 
#    |  | |  |   |       |   |   |      |     |   |   |       |       |       |
#    |  |_|  |   |    ___|   |   |  _    |    |   |   |    ___|    ___|   _   |
#    |       |   |   |___|   |   | | |   |    |   |   |   |___|   | __|  | |  |
#    |_     _|   |    ___|   |___| |_|   |    |   |___|    ___|   ||  |  |_|  |
#      |   | |   |   |___|       |       |    |       |   |___|   |_| |       |
#      |___| |___|_______|_______|______|     |_______|_______|_______|_______|
#                                                                       
#     ╔═════════════════════════════════════╗
#     ║  ** Tokemak **                      ║
#     ║  Integration with Tokemak Protocol. ║
#     ╚═════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

implements: Lego
implements: YieldLego

exports: addys.__interface__
exports: yld.__interface__

initializes: addys
initializes: yld[addys := addys]

from interfaces import LegoPartner as Lego
from interfaces import YieldLego as YieldLego
from interfaces import WalletStructs as ws

import contracts.modules.Addys as addys
import contracts.modules.YieldLegoData as yld

from ethereum.ercs import IERC20Detailed
from ethereum.ercs import IERC20

interface GauntletDepositor:
    def requestRedeem(_vaultToken: address, _vaultTokenAmount: uint256, _minAmountOut: uint256, _solverTip: uint256, _deadline: uint256, _maxPriceAge: uint256, _isFixedPrice: bool): nonpayable
    def requestDeposit(_asset: address, _assetAmount: uint256, _minAmountOut: uint256, _solverTip: uint256, _deadline: uint256, _maxPriceAge: uint256, _isFixedPrice: bool): nonpayable
    def MULTI_DEPOSITOR_VAULT() -> address: view
    def PRICE_FEE_CALCULATOR() -> address: view

interface GauntletCalculator:
    def convertTokenToUnits(_vault: address, _token: address, _tokenAmount: uint256) -> uint256: view
    def convertUnitsToNumeraire(_vault: address, _vaultAmount: uint256) -> uint256: view
    def NUMERAIRE() -> address: view

interface Appraiser:
    def getUsdValue(_asset: address, _amount: uint256, _missionControl: address = empty(address), _legoBook: address = empty(address), _ledger: address = empty(address)) -> uint256: view
    def updatePriceAndGetUsdValue(_asset: address, _amount: uint256, _missionControl: address = empty(address), _legoBook: address = empty(address)) -> uint256: nonpayable

interface Ledger:
    def setVaultToken(_vaultToken: address, _legoId: uint256, _underlyingAsset: address, _decimals: uint256, _isRebasing: bool): nonpayable
    def isRegisteredVaultToken(_vaultToken: address) -> bool: view

interface Registry:
    def getRegId(_addr: address) -> uint256: view

event PendingGauntletDeposit:
    sender: indexed(address)
    asset: indexed(address)
    vaultToken: indexed(address)
    assetAmountDeposited: uint256
    usdValue: uint256
    recipient: address

event PendingGauntletWithdrawal:
    sender: indexed(address)
    vaultToken: indexed(address)
    vaultTokenAmount: uint256
    usdValue: uint256
    asset: indexed(address)
    expectedAssetAmount: uint256
    recipient: address

GAUNTLET_DEPOSITOR: public(immutable(address))
GAUNTLET_CALCULATOR: public(immutable(address))
VAULT_ADDR: public(immutable(address))
USDC_ADDR: public(immutable(address))

MAX_TOKEN_PATH: constant(uint256) = 5


@deploy
def __init__(_undyHq: address, _gauntletDepositor: address):
    addys.__init__(_undyHq)
    yld.__init__(False)

    assert _gauntletDepositor != empty(address) # dev: invalid addr
    GAUNTLET_DEPOSITOR = _gauntletDepositor
    GAUNTLET_CALCULATOR = staticcall GauntletDepositor(_gauntletDepositor).PRICE_FEE_CALCULATOR()
    VAULT_ADDR = staticcall GauntletDepositor(_gauntletDepositor).MULTI_DEPOSITOR_VAULT()
    USDC_ADDR = staticcall GauntletCalculator(GAUNTLET_CALCULATOR).NUMERAIRE() 


@view
@external
def hasCapability(_action: ws.ActionType) -> bool:
    return _action == ws.ActionType.MINT_REDEEM


@view
@external
def getRegistries() -> DynArray[address, 10]:
    return []


@view
@external
def isYieldLego() -> bool:
    return True


@view
@external
def isDexLego() -> bool:
    return False


@view
@external
def isRebasing() -> bool:
    return self._isRebasing()


@view
@internal
def _isRebasing() -> bool:
    return False


@view
@external
def isEligibleVaultForTrialFunds(_vaultToken: address, _underlyingAsset: address) -> bool:
    return yld.vaultToAsset[_vaultToken] == _underlyingAsset


@view
@external
def isEligibleForYieldBonus(_asset: address) -> bool:
    return yld.vaultToAsset[_asset] != empty(address)


#########
# Yield #
#########


@external
def mintOrRedeemAsset(
    _tokenIn: address,
    _tokenOut: address,
    _tokenInAmount: uint256,
    _minAmountOut: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256, bool, uint256):
    assert not yld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = yld._getMiniAddys(_miniAddys)

    # validate inputs
    assert _tokenIn != _tokenOut # dev: invalid token
    asset: address = USDC_ADDR
    assert asset in [_tokenIn, _tokenOut] # dev: invalid asset
    vaultAddr: address = VAULT_ADDR
    assert vaultAddr in [_tokenIn, _tokenOut] # dev: invalid vault

    # make sure registered
    if yld.vaultToAsset[vaultAddr] == empty(address):
        self._registerAsset(asset, vaultAddr)
        self._updateLedgerVaultToken(asset, vaultAddr, miniAddys.ledger, miniAddys.legoBook)

    # mint vault token
    if _tokenIn == asset:
        return self._mintVaultToken(asset, _tokenInAmount, vaultAddr, _minAmountOut, _extraData, _recipient, miniAddys, msg.sender)

    # redeem vault token
    else:
        return self._redeemVaultToken(vaultAddr, _tokenInAmount, asset, _minAmountOut, _extraData, _recipient, miniAddys, msg.sender)


# deposit


@internal
def _mintVaultToken(
    _asset: address,
    _amount: uint256,
    _vaultAddr: address,
    _minAmountOut: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys,
    _sender: address,
) -> (uint256, uint256, bool, uint256):

    # pre balances
    preLegoBalance: uint256 = staticcall IERC20(_asset).balanceOf(self)

    # transfer deposit asset to this contract
    depositAmount: uint256 = min(_amount, staticcall IERC20(_asset).balanceOf(_sender))
    assert depositAmount != 0 # dev: nothing to transfer
    assert extcall IERC20(_asset).transferFrom(_sender, self, depositAmount, default_return_value=True) # dev: transfer failed

    # deposit assets into lego partner
    extcall GauntletDepositor(GAUNTLET_DEPOSITOR).requestDeposit(
        _asset,
        depositAmount,
        _minAmountOut,
        0,
        block.timestamp + 600,
        864000,
        False,
    )

    # refund if full deposit didn't get through
    currentLegoBalance: uint256 = staticcall IERC20(_asset).balanceOf(self)
    refundAssetAmount: uint256 = 0
    if currentLegoBalance > preLegoBalance:
        refundAssetAmount = currentLegoBalance - preLegoBalance
        assert extcall IERC20(_asset).transfer(_sender, refundAssetAmount, default_return_value=True) # dev: transfer failed
        depositAmount -= refundAssetAmount

    usdValue: uint256 = extcall Appraiser(_miniAddys.appraiser).updatePriceAndGetUsdValue(_asset, depositAmount, _miniAddys.missionControl, _miniAddys.legoBook)
    log PendingGauntletDeposit(
        sender = _sender,
        asset = _asset,
        vaultToken = _vaultAddr,
        assetAmountDeposited = depositAmount,
        usdValue = usdValue,
        recipient = _recipient,
    )
    return depositAmount, 0, True, usdValue


# withdraw


@internal
def _redeemVaultToken(
    _vaultToken: address,
    _vaultTokenAmount: uint256,
    _asset: address,
    _minAmountOut: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys,
    _sender: address,
) -> (uint256, uint256, bool, uint256):

    # pre balances
    preLegoBalance: uint256 = staticcall IERC20(_vaultToken).balanceOf(self)

    # transfer vault token to this contract
    vaultTokenAmount: uint256 = min(_vaultTokenAmount, staticcall IERC20(_vaultToken).balanceOf(_sender))
    assert vaultTokenAmount != 0 # dev: nothing to transfer
    assert extcall IERC20(_vaultToken).transferFrom(_sender, self, vaultTokenAmount, default_return_value=True) # dev: transfer failed

    # get before redeem
    underlyingAmount: uint256 = self._getUnderlyingAmount(_vaultToken, vaultTokenAmount)

    # pending redeem
    extcall GauntletDepositor(GAUNTLET_DEPOSITOR).requestRedeem(
        _asset,
        vaultTokenAmount,
        _minAmountOut,
        0,
        block.timestamp + 600,
        864000,
        False,
    )

    # refund if full redeem didn't get through
    currentLegoBalance: uint256 = staticcall IERC20(_vaultToken).balanceOf(self)
    refundAssetAmount: uint256 = 0
    if currentLegoBalance > preLegoBalance:
        refundAssetAmount = currentLegoBalance - preLegoBalance
        assert extcall IERC20(_vaultToken).transfer(_sender, refundAssetAmount, default_return_value=True) # dev: transfer failed
        vaultTokenAmount -= refundAssetAmount

    usdValue: uint256 = extcall Appraiser(_miniAddys.appraiser).updatePriceAndGetUsdValue(_asset, underlyingAmount, _miniAddys.missionControl, _miniAddys.legoBook)
    log PendingGauntletWithdrawal(
        sender = _sender,
        vaultToken = _vaultToken,
        vaultTokenAmount = vaultTokenAmount,
        usdValue = usdValue,
        asset = _asset,
        expectedAssetAmount = underlyingAmount,
        recipient = _recipient,
    )
    return vaultTokenAmount, 0, True, usdValue


#############
# Utilities #
#############


# underlying asset


@view
@external
def isVaultToken(_vaultToken: address) -> bool:
    return self._isVaultToken(_vaultToken)


@view
@internal
def _isVaultToken(_vaultToken: address) -> bool:
    if yld.vaultToAsset[_vaultToken] != empty(address):
        return True
    return self._isValidGauntletVault(_vaultToken)


@view
@external
def isValidGauntletVault(_vaultToken: address) -> bool:
    return self._isValidGauntletVault(_vaultToken)


@view
@internal
def _isValidGauntletVault(_vaultToken: address) -> bool:
    return VAULT_ADDR == _vaultToken


@view
@external
def getUnderlyingAsset(_vaultToken: address) -> address:
    return self._getUnderlyingAsset(_vaultToken)


@view
@internal
def _getUnderlyingAsset(_vaultToken: address) -> address:
    asset: address = yld.vaultToAsset[_vaultToken]
    if asset == empty(address) and self._isValidGauntletVault(_vaultToken):
        asset = USDC_ADDR
    return asset


# underlying amount


@view
@external
def getUnderlyingAmount(_vaultToken: address, _vaultTokenAmount: uint256) -> uint256:
    if not self._isVaultToken(_vaultToken) or _vaultTokenAmount == 0:
        return 0 # invalid vault token or amount
    return self._getUnderlyingAmount(_vaultToken, _vaultTokenAmount)


@view
@internal
def _getUnderlyingAmount(_vaultToken: address, _vaultTokenAmount: uint256) -> uint256:
    return staticcall GauntletCalculator(GAUNTLET_CALCULATOR).convertUnitsToNumeraire(_vaultToken, _vaultTokenAmount)


@view
@external
def getVaultTokenAmount(_asset: address, _assetAmount: uint256, _vaultToken: address) -> uint256:
    if empty(address) in [_asset, _vaultToken] or _assetAmount == 0:
        return 0 # bad inputs
    if self._getUnderlyingAsset(_vaultToken) != _asset:
        return 0 # invalid vault token or asset
    return staticcall GauntletCalculator(GAUNTLET_CALCULATOR).convertTokenToUnits(_vaultToken, _asset, _assetAmount)


# usd value


@view
@external
def getUsdValueOfVaultToken(_vaultToken: address, _vaultTokenAmount: uint256, _appraiser: address = empty(address)) -> uint256:
    return self._getUsdValueOfVaultToken(_vaultToken, _vaultTokenAmount, _appraiser)


@view
@internal
def _getUsdValueOfVaultToken(_vaultToken: address, _vaultTokenAmount: uint256, _appraiser: address) -> uint256:
    asset: address = empty(address)
    underlyingAmount: uint256 = 0
    usdValue: uint256 = 0
    asset, underlyingAmount, usdValue = self._getUnderlyingData(_vaultToken, _vaultTokenAmount, _appraiser)
    return usdValue


# all underlying data together


@view
@external
def getUnderlyingData(_vaultToken: address, _vaultTokenAmount: uint256, _appraiser: address = empty(address)) -> (address, uint256, uint256):
    return self._getUnderlyingData(_vaultToken, _vaultTokenAmount, _appraiser)


@view
@internal
def _getUnderlyingData(_vaultToken: address, _vaultTokenAmount: uint256, _appraiser: address) -> (address, uint256, uint256):
    if _vaultTokenAmount == 0 or _vaultToken == empty(address):
        return empty(address), 0, 0 # bad inputs
    asset: address = self._getUnderlyingAsset(_vaultToken)
    if asset == empty(address):
        return empty(address), 0, 0 # invalid vault token
    underlyingAmount: uint256 = self._getUnderlyingAmount(_vaultToken, _vaultTokenAmount)
    usdValue: uint256 = self._getUsdValue(asset, underlyingAmount, _appraiser)
    return asset, underlyingAmount, usdValue


@view
@internal
def _getUsdValue(_asset: address, _amount: uint256, _appraiser: address) -> uint256:
    appraiser: address = _appraiser
    if _appraiser == empty(address):
        appraiser = addys._getAppraiserAddr()
    return staticcall Appraiser(appraiser).getUsdValue(_asset, _amount)


# other


@view
@external
def totalAssets(_vaultToken: address) -> uint256:
    if not self._isVaultToken(_vaultToken):
        return 0 # invalid vault token
    totalSupply: uint256 = staticcall IERC20(_vaultToken).totalSupply()
    return staticcall GauntletCalculator(GAUNTLET_CALCULATOR).convertUnitsToNumeraire(_vaultToken, totalSupply)


@view
@external
def totalBorrows(_vaultToken: address) -> uint256:
    return 0


# price per share


@view
@external
def getPricePerShare(_asset: address, _decimals: uint256) -> uint256:
    return staticcall GauntletCalculator(GAUNTLET_CALCULATOR).convertUnitsToNumeraire(_asset, 10 ** _decimals)


################
# Registration #
################


@external
def addAssetOpportunity(_asset: address, _vaultAddr: address):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert self._isValidAssetOpportunity(_asset, _vaultAddr) # dev: invalid asset or vault
    assert not yld._isAssetOpportunity(_asset, _vaultAddr) # dev: already registered
    self._registerAsset(_asset, _vaultAddr)


@internal
def _registerAsset(_asset: address, _vaultAddr: address):
    assert extcall IERC20(_asset).approve(GAUNTLET_DEPOSITOR, max_value(uint256), default_return_value=True) # dev: max approval failed
    assert extcall IERC20(_vaultAddr).approve(GAUNTLET_DEPOSITOR, max_value(uint256), default_return_value=True) # dev: max approval failed
    yld._addAssetOpportunity(_asset, _vaultAddr)


@external
def removeAssetOpportunity(_asset: address, _vaultAddr: address):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert extcall IERC20(_asset).approve(GAUNTLET_DEPOSITOR, 0, default_return_value=True) # dev: max approval failed
    assert extcall IERC20(_vaultAddr).approve(GAUNTLET_DEPOSITOR, 0, default_return_value=True) # dev: max approval failed
    yld._removeAssetOpportunity(_asset, _vaultAddr)


# validation


@view
@internal
def isValidAssetOpportunity(_asset: address, _vaultAddr: address) -> bool:
    return self._isValidAssetOpportunity(_asset, _vaultAddr)


@view
@internal
def _isValidAssetOpportunity(_asset: address, _vaultAddr: address) -> bool:
    return self._isValidGauntletVault(_vaultAddr) and _asset == USDC_ADDR


# update ledger registration


@internal
def _updateLedgerVaultToken(
    _underlyingAsset: address,
    _vaultToken: address,
    _ledger: address,
    _legoBook: address,
):
    if empty(address) in [_underlyingAsset, _vaultToken]:
        return

    if not staticcall Ledger(_ledger).isRegisteredVaultToken(_vaultToken):
        legoId: uint256 = staticcall Registry(_legoBook).getRegId(self)
        decimals: uint256 = convert(staticcall IERC20Detailed(_vaultToken).decimals(), uint256)
        extcall Ledger(_ledger).setVaultToken(_vaultToken, legoId, _underlyingAsset, decimals, self._isRebasing())


#########
# Other #
#########


@external
def depositForYield(
    _asset: address,
    _amount: uint256,
    _vaultAddr: address,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, address, uint256, uint256):
    return 0, empty(address), 0, 0


@external
def withdrawFromYield(
    _vaultToken: address,
    _amount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, address, uint256, uint256):
    return 0, empty(address), 0, 0


@external
def claimRewards(
    _user: address,
    _rewardToken: address,
    _rewardAmount: uint256,
    _extraData: bytes32,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    return 0, 0


@view
@external
def hasClaimableRewards(_user: address) -> bool:
    # as far as we can tell, this must be done offchain
    return False


@external
def swapTokens(
    _amountIn: uint256,
    _minAmountOut: uint256,
    _tokenPath: DynArray[address, MAX_TOKEN_PATH],
    _poolPath: DynArray[address, MAX_TOKEN_PATH - 1],
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256, uint256):
    return 0, 0, 0


@external
def confirmMintOrRedeemAsset(
    _tokenIn: address,
    _tokenOut: address,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    return 0, 0


@external
def addCollateral(
    _asset: address,
    _amount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    return 0, 0


@external
def removeCollateral(
    _asset: address,
    _amount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    return 0, 0


@external
def borrow(
    _borrowAsset: address,
    _amount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    return 0, 0


@external
def repayDebt(
    _paymentAsset: address,
    _paymentAmount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    return 0, 0


@external
def addLiquidity(
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _amountA: uint256,
    _amountB: uint256,
    _minAmountA: uint256,
    _minAmountB: uint256,
    _minLpAmount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (address, uint256, uint256, uint256, uint256):
    return empty(address), 0, 0, 0, 0


@external
def removeLiquidity(
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _lpToken: address,
    _lpAmount: uint256,
    _minAmountA: uint256,
    _minAmountB: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256, uint256, uint256):
    return 0, 0, 0, 0


@external
def addLiquidityConcentrated(
    _nftTokenId: uint256,
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _tickLower: int24,
    _tickUpper: int24,
    _amountA: uint256,
    _amountB: uint256,
    _minAmountA: uint256,
    _minAmountB: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256, uint256, uint256, uint256):
    return 0, 0, 0, 0, 0


@external
def removeLiquidityConcentrated(
    _nftTokenId: uint256,
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _liqToRemove: uint256,
    _minAmountA: uint256,
    _minAmountB: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256, uint256, bool, uint256):
    return 0, 0, 0, False, 0


@view
@external
def getAccessForLego(_user: address, _action: ws.ActionType) -> (address, String[64], uint256):
    return empty(address), empty(String[64]), 0


@view
@external
def getPrice(_asset: address, _decimals: uint256) -> uint256:
    return 0
