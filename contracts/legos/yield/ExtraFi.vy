#     __   __ ___ _______ ___     ______       ___     _______ _______ _______ 
#    |  | |  |   |       |   |   |      |     |   |   |       |       |       |
#    |  |_|  |   |    ___|   |   |  _    |    |   |   |    ___|    ___|   _   |
#    |       |   |   |___|   |   | | |   |    |   |   |   |___|   | __|  | |  |
#    |_     _|   |    ___|   |___| |_|   |    |   |___|    ___|   ||  |  |_|  |
#      |   | |   |   |___|       |       |    |       |   |___|   |_| |       |
#      |___| |___|_______|_______|______|     |_______|_______|_______|_______|
#                                                                       
#     ╔═════════════════════════════════════════╗
#     ║  ** ExtraFi Lego **                     ║
#     ║  Integration with ExtraFi Protocol.     ║
#     ╚═════════════════════════════════════════╝
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
from interfaces import LegoStructs as ls

import contracts.modules.Addys as addys
import contracts.modules.YieldLegoData as yld

from ethereum.ercs import IERC20Detailed
from ethereum.ercs import IERC20

interface ExtraFiPool:
    def redeem(_reserveId: uint256, _eTokenAmount: uint256, _recipient: address, _receiveNativeETH: bool) -> uint256: nonpayable
    def deposit(_reserveId: uint256, _amount: uint256, _onBehalfOf: address, _referralCode: uint16) -> uint256: payable
    def getUnderlyingTokenAddress(_reserveId: uint256) -> address: view
    def totalLiquidityOfReserve(_reserveId: uint256) -> uint256: view
    def totalBorrowsOfReserve(_reserveId: uint256) -> uint256: view
    def exchangeRateOfReserve(_reserveId: uint256) -> uint256: view
    def getETokenAddress(_reserveId: uint256) -> address: view

interface Appraiser:
    def getUsdValue(_asset: address, _amount: uint256, _missionControl: address = empty(address), _legoBook: address = empty(address), _ledger: address = empty(address)) -> uint256: view
    def updatePriceAndGetUsdValue(_asset: address, _amount: uint256, _missionControl: address = empty(address), _legoBook: address = empty(address)) -> uint256: nonpayable

interface Ledger:
    def setVaultToken(_vaultToken: address, _legoId: uint256, _underlyingAsset: address, _decimals: uint256, _isRebasing: bool): nonpayable
    def isRegisteredVaultToken(_vaultToken: address) -> bool: view

interface Registry:
    def getRegId(_addr: address) -> uint256: view

event ExtraFiDeposit:
    sender: indexed(address)
    asset: indexed(address)
    vaultToken: indexed(address)
    assetAmountDeposited: uint256
    usdValue: uint256
    vaultTokenAmountReceived: uint256
    recipient: address

event ExtraFiWithdrawal:
    sender: indexed(address)
    asset: indexed(address)
    vaultToken: indexed(address)
    assetAmountReceived: uint256
    usdValue: uint256
    vaultTokenAmountBurned: uint256
    recipient: address

vaultTokenToReserveId: public(HashMap[address, uint256]) # vault token -> reserve id

EXTRAFI_POOL: public(immutable(address))

MAX_MARKETS: constant(uint256) = 50
MAX_ASSETS: constant(uint256) = 25
MAX_TOKEN_PATH: constant(uint256) = 5


@deploy
def __init__(_undyHq: address, _extraFiPool: address):
    addys.__init__(_undyHq)
    yld.__init__(False)

    assert _extraFiPool != empty(address) # dev: invalid addr
    EXTRAFI_POOL = _extraFiPool


@view
@external
def hasCapability(_action: ws.ActionType) -> bool:
    return _action in (
        ws.ActionType.EARN_DEPOSIT | 
        ws.ActionType.EARN_WITHDRAW
    )


@view
@external
def getRegistries() -> DynArray[address, 10]:
    return [EXTRAFI_POOL]


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
def isEligibleVaultForTrialFunds(_vaultToken: address, _underlyingAsset: address) -> bool:
    return False


@view
@external
def isEligibleForYieldBonus(_asset: address) -> bool:
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
def canRegisterVaultToken(_asset: address, _vaultToken: address) -> bool:
    # TODO: implement
    return False


#########
# Yield #
#########


# add price snapshot


@external
def addPriceSnapshot(_vaultToken: address) -> bool:
    # TODO: implement
    return False


# deposit


@external
def depositForYield(
    _asset: address,
    _amount: uint256,
    _vaultAddr: address,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, address, uint256, uint256):
    assert not yld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = yld._getMiniAddys(_miniAddys)

    # verify asset and vault token are registered
    assert yld.vaultToAsset[_vaultAddr].underlyingAsset == _asset # dev: asset mismatch
    assert _asset != empty(address) # dev: invalid asset
    reserveId: uint256 = self.vaultTokenToReserveId[_vaultAddr]
    assert reserveId != 0 # dev: invalid vault token

    # pre balances
    preLegoBalance: uint256 = staticcall IERC20(_asset).balanceOf(self)

    # transfer deposit asset to this contract
    depositAmount: uint256 = min(_amount, staticcall IERC20(_asset).balanceOf(msg.sender))
    assert depositAmount != 0 # dev: nothing to transfer
    assert extcall IERC20(_asset).transferFrom(msg.sender, self, depositAmount, default_return_value=True) # dev: transfer failed

    # deposit assets into lego partner
    vaultTokenAmountReceived: uint256 = extcall ExtraFiPool(EXTRAFI_POOL).deposit(reserveId, depositAmount, _recipient, 0)
    assert vaultTokenAmountReceived != 0 # dev: no vault tokens received

    # refund if full deposit didn't get through
    currentLegoBalance: uint256 = staticcall IERC20(_asset).balanceOf(self)
    refundAssetAmount: uint256 = 0
    if currentLegoBalance > preLegoBalance:
        refundAssetAmount = currentLegoBalance - preLegoBalance
        assert extcall IERC20(_asset).transfer(msg.sender, refundAssetAmount, default_return_value=True) # dev: transfer failed
        depositAmount -= refundAssetAmount

    usdValue: uint256 = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(_asset, depositAmount, miniAddys.missionControl, miniAddys.legoBook)
    log ExtraFiDeposit(
        sender = msg.sender,
        asset = _asset,
        vaultToken = _vaultAddr,
        assetAmountDeposited = depositAmount,
        usdValue = usdValue,
        vaultTokenAmountReceived = vaultTokenAmountReceived,
        recipient = _recipient,
    )

    # add price snapshot for non-rebasing asset
    vaultTokenDecimals: uint256 = yld.vaultToAsset[_vaultAddr].decimals
    pricePerShare: uint256 = self._getPricePerShare(_vaultAddr, vaultTokenDecimals)
    yld._addPriceSnapshot(_vaultAddr, pricePerShare, vaultTokenDecimals)

    return depositAmount, _vaultAddr, vaultTokenAmountReceived, usdValue


# withdraw


@external
def withdrawFromYield(
    _vaultToken: address,
    _amount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, address, uint256, uint256):
    assert not yld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = yld._getMiniAddys(_miniAddys)

    # verify asset and vault token are registered
    asset: address = yld.vaultToAsset[_vaultToken].underlyingAsset
    assert asset != empty(address) # dev: invalid asset
    reserveId: uint256 = self.vaultTokenToReserveId[_vaultToken]
    assert reserveId != 0 # dev: invalid vault token

    # pre balances
    preLegoVaultBalance: uint256 = staticcall IERC20(_vaultToken).balanceOf(self)

    # transfer vaults tokens to this contract
    vaultTokenAmount: uint256 = min(_amount, staticcall IERC20(_vaultToken).balanceOf(msg.sender))
    assert vaultTokenAmount != 0 # dev: nothing to transfer
    assert extcall IERC20(_vaultToken).transferFrom(msg.sender, self, vaultTokenAmount, default_return_value=True) # dev: transfer failed

    # withdraw assets from lego partner
    assetAmountReceived: uint256 = extcall ExtraFiPool(EXTRAFI_POOL).redeem(reserveId, vaultTokenAmount, _recipient, False)
    assert assetAmountReceived != 0 # dev: no asset amount received

    # refund if full withdrawal didn't happen
    currentLegoVaultBalance: uint256 = staticcall IERC20(_vaultToken).balanceOf(self)
    refundVaultTokenAmount: uint256 = 0
    if currentLegoVaultBalance > preLegoVaultBalance:
        refundVaultTokenAmount = currentLegoVaultBalance - preLegoVaultBalance
        assert extcall IERC20(_vaultToken).transfer(msg.sender, refundVaultTokenAmount, default_return_value=True) # dev: transfer failed
        vaultTokenAmount -= refundVaultTokenAmount

    usdValue: uint256 = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(asset, assetAmountReceived, miniAddys.missionControl, miniAddys.legoBook)
    log ExtraFiWithdrawal(
        sender = msg.sender,
        asset = asset,
        vaultToken = _vaultToken,
        assetAmountReceived = assetAmountReceived,
        usdValue = usdValue,
        vaultTokenAmountBurned = vaultTokenAmount,
        recipient = _recipient,
    )

    # add price snapshot for non-rebasing asset
    vaultTokenDecimals: uint256 = yld.vaultToAsset[_vaultToken].decimals
    pricePerShare: uint256 = self._getPricePerShare(_vaultToken, vaultTokenDecimals)
    yld._addPriceSnapshot(_vaultToken, pricePerShare, vaultTokenDecimals)

    return vaultTokenAmount, asset, assetAmountReceived, usdValue


#################
# Claim Rewards #
#################


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
    return False


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
    return yld.vaultToAsset[_vaultToken].underlyingAsset != empty(address)


@view
@external
def getUnderlyingAsset(_vaultToken: address) -> address:
    return self._getUnderlyingAsset(_vaultToken)


@view
@internal
def _getUnderlyingAsset(_vaultToken: address) -> address:
    return yld.vaultToAsset[_vaultToken].underlyingAsset


# underlying amount


@view
@external
def getUnderlyingAmount(_vaultToken: address, _vaultTokenAmount: uint256) -> uint256:
    if yld.vaultToAsset[_vaultToken].underlyingAsset == empty(address) or _vaultTokenAmount == 0:
        return 0 # invalid vault token or amount
    return self._getUnderlyingAmount(_vaultToken, _vaultTokenAmount)


@view
@internal
def _getUnderlyingAmount(_vaultToken: address, _vaultTokenAmount: uint256) -> uint256:
    reserveId: uint256 = self.vaultTokenToReserveId[_vaultToken]
    return _vaultTokenAmount * staticcall ExtraFiPool(EXTRAFI_POOL).exchangeRateOfReserve(reserveId) // (10 ** 18)


@view
@external
def getVaultTokenAmount(_asset: address, _assetAmount: uint256, _vaultToken: address) -> uint256:
    if empty(address) in [_asset, _vaultToken] or _assetAmount == 0:
        return 0 # bad inputs
    if self._getUnderlyingAsset(_vaultToken) != _asset:
        return 0 # invalid vault token or asset
    reserveId: uint256 = self.vaultTokenToReserveId[_vaultToken]
    return _assetAmount * (10 ** 18) // staticcall ExtraFiPool(EXTRAFI_POOL).exchangeRateOfReserve(reserveId)


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
    reserveId: uint256 = self.vaultTokenToReserveId[_vaultToken]
    return staticcall ExtraFiPool(EXTRAFI_POOL).totalLiquidityOfReserve(reserveId)


@view
@external
def totalBorrows(_vaultToken: address) -> uint256:
    if not self._isVaultToken(_vaultToken):
        return 0 # invalid vault token
    reserveId: uint256 = self.vaultTokenToReserveId[_vaultToken]
    return staticcall ExtraFiPool(EXTRAFI_POOL).totalBorrowsOfReserve(reserveId)


# price per share


@view
@external
def getPricePerShare(_asset: address, _decimals: uint256) -> uint256:
    return self._getPricePerShare(_asset, _decimals)


@view
@internal
def _getPricePerShare(_asset: address, _decimals: uint256) -> uint256:
    reserveId: uint256 = self.vaultTokenToReserveId[_asset]
    if reserveId == 0:
        return 0
    return staticcall ExtraFiPool(EXTRAFI_POOL).exchangeRateOfReserve(reserveId) * (10 ** _decimals) // (10 ** 18)


# underlying balances (true and safe)


@view
@external
def getUnderlyingBalances(_vaultToken: address, _vaultTokenBalance: uint256) -> (uint256, uint256):
    if _vaultTokenBalance == 0:
        return 0, 0

    trueUnderlying: uint256 = self._getUnderlyingAmount(_vaultToken, _vaultTokenBalance)
    safeUnderlying: uint256 = self._getUnderlyingAmountSafe(_vaultToken, _vaultTokenBalance)
    if safeUnderlying == 0:
        safeUnderlying = trueUnderlying

    return trueUnderlying, min(trueUnderlying, safeUnderlying)


@view
@external
def getUnderlyingAmountSafe(_vaultToken: address, _vaultTokenBalance: uint256) -> uint256:
    return self._getUnderlyingAmountSafe(_vaultToken, _vaultTokenBalance)


@view
@internal
def _getUnderlyingAmountSafe(_vaultToken: address, _vaultTokenBalance: uint256) -> uint256:
    vaultInfo: ls.VaultTokenInfo = yld.vaultToAsset[_vaultToken]
    if vaultInfo.decimals == 0:
        return 0 # not registered

    # safe underlying amount (using cached weighted average from snapshots)
    return _vaultTokenBalance * vaultInfo.lastAveragePricePerShare // (10 ** vaultInfo.decimals)


################
# Registration #
################


@external
def addAssetOpportunityWithReserveId(_asset: address, _vaultAddr: address, _reserveId: uint256):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert self._isValidAssetOpportunity(_asset, _vaultAddr, _reserveId) # dev: invalid asset or vault
    assert not yld._isAssetOpportunity(_asset, _vaultAddr) # dev: already registered
    self._registerAsset(_asset, _vaultAddr, _reserveId)


@internal
def _registerAsset(_asset: address, _vaultAddr: address, _reserveId: uint256):
    assert extcall IERC20(_asset).approve(EXTRAFI_POOL, max_value(uint256), default_return_value=True) # dev: max approval failed
    assert extcall IERC20(_vaultAddr).approve(EXTRAFI_POOL, max_value(uint256), default_return_value=True) # dev: max approval failed
    yld._addAssetOpportunity(_asset, _vaultAddr)
    self.vaultTokenToReserveId[_vaultAddr] = _reserveId
    self._updateLedgerVaultToken(_asset, _vaultAddr)


@external
def removeAssetOpportunity(_asset: address, _vaultAddr: address):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert extcall IERC20(_asset).approve(EXTRAFI_POOL, 0, default_return_value=True) # dev: max approval failed
    assert extcall IERC20(_vaultAddr).approve(EXTRAFI_POOL, 0, default_return_value=True) # dev: max approval failed
    yld._removeAssetOpportunity(_asset, _vaultAddr)
    self.vaultTokenToReserveId[_vaultAddr] = 0


# validation


@view
@internal
def isValidAssetOpportunity(_asset: address, _vaultAddr: address, _reserveId: uint256) -> bool:
    return self._isValidAssetOpportunity(_asset, _vaultAddr, _reserveId)


@view
@internal
def _isValidAssetOpportunity(_asset: address, _vaultAddr: address, _reserveId: uint256) -> bool:
    if empty(address) in [_asset, _vaultAddr]:
        return False
    if _reserveId == 0:
        return False
    extraFiPool: address = EXTRAFI_POOL
    underlyingToken: address = staticcall ExtraFiPool(extraFiPool).getUnderlyingTokenAddress(_reserveId)
    if _asset != underlyingToken:
        return False
    eToken: address = staticcall ExtraFiPool(extraFiPool).getETokenAddress(_reserveId)
    return _vaultAddr == eToken


# update ledger registration


@internal
def _updateLedgerVaultToken(_underlyingAsset: address, _vaultToken: address):
    if empty(address) in [_underlyingAsset, _vaultToken]:
        return

    ledger: address = addys._getLedgerAddr()
    if not staticcall Ledger(ledger).isRegisteredVaultToken(_vaultToken):
        legoId: uint256 = staticcall Registry(addys._getLegoBookAddr()).getRegId(self)
        decimals: uint256 = convert(staticcall IERC20Detailed(_vaultToken).decimals(), uint256)
        extcall Ledger(ledger).setVaultToken(_vaultToken, legoId, _underlyingAsset, decimals, self._isRebasing())


#########
# Other #
#########


@external
def addAssetOpportunity(_asset: address, _vaultAddr: address):
    pass


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
def mintOrRedeemAsset(
    _tokenIn: address,
    _tokenOut: address,
    _tokenInAmount: uint256,
    _minAmountOut: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256, bool, uint256):
    return 0, 0, False, 0
    

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
