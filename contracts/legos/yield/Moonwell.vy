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

interface CompoundV2:
    def redeem(_ctokenAmount: uint256) -> uint256: nonpayable
    def mint(_amount: uint256) -> uint256: nonpayable
    def exchangeRateStored() -> uint256: view
    def totalBorrows() -> uint256: view
    def totalSupply() -> uint256: view
    def underlying() -> address: view

interface Appraiser:
    def getUsdValue(_asset: address, _amount: uint256, _missionControl: address = empty(address), _legoBook: address = empty(address), _ledger: address = empty(address)) -> uint256: view
    def updatePriceAndGetUsdValue(_asset: address, _amount: uint256, _missionControl: address = empty(address), _legoBook: address = empty(address)) -> uint256: nonpayable

interface Ledger:
    def setVaultToken(_vaultToken: address, _legoId: uint256, _underlyingAsset: address, _decimals: uint256, _isRebasing: bool): nonpayable
    def isRegisteredVaultToken(_vaultToken: address) -> bool: view

interface MoonwellComptroller:
    def getAllMarkets() -> DynArray[address, MAX_MARKETS]: view

interface Registry:
    def getRegId(_addr: address) -> uint256: view

interface WethContract:
    def deposit(): payable

event MoonwellDeposit:
    sender: indexed(address)
    asset: indexed(address)
    vaultToken: indexed(address)
    assetAmountDeposited: uint256
    usdValue: uint256
    vaultTokenAmountReceived: uint256
    recipient: address

event MoonwellWithdrawal:
    sender: indexed(address)
    asset: indexed(address)
    vaultToken: indexed(address)
    assetAmountReceived: uint256
    usdValue: uint256
    vaultTokenAmountBurned: uint256
    recipient: address

# moonwell
MOONWELL_COMPTROLLER: public(immutable(address))
WETH: public(immutable(address))

MAX_MARKETS: constant(uint256) = 50
MAX_TOKEN_PATH: constant(uint256) = 5


@deploy
def __init__(
    _undyHq: address,
    _moonwellComptroller: address,
    _weth: address,
):
    addys.__init__(_undyHq)
    yld.__init__(False)

    assert empty(address) not in [_moonwellComptroller, _weth] # dev: invalid addrs
    MOONWELL_COMPTROLLER = _moonwellComptroller
    WETH = _weth


@payable
@external
def __default__():
    pass


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
    return [MOONWELL_COMPTROLLER]


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
    return yld.vaultToAsset[_vaultToken] == _underlyingAsset


#########
# Yield #
#########


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

    # verify vault token (register if necessary)
    vaultToken: address = self._getVaultTokenOnDeposit(_asset, _vaultAddr, miniAddys.ledger, miniAddys.legoBook)

    # pre balances
    preLegoBalance: uint256 = staticcall IERC20(_asset).balanceOf(self)
    preLegoVaultBalance: uint256 = staticcall IERC20(vaultToken).balanceOf(self)

    # transfer deposit asset to this contract
    depositAmount: uint256 = min(_amount, staticcall IERC20(_asset).balanceOf(msg.sender))
    assert depositAmount != 0 # dev: nothing to transfer
    assert extcall IERC20(_asset).transferFrom(msg.sender, self, depositAmount, default_return_value=True) # dev: transfer failed

    # deposit assets into lego partner
    assert extcall CompoundV2(vaultToken).mint(depositAmount) == 0 # dev: could not deposit into moonwell

    # validate received vault tokens, transfer back to user
    vaultTokenAmountReceived: uint256 = staticcall IERC20(vaultToken).balanceOf(self) - preLegoVaultBalance
    assert vaultTokenAmountReceived != 0 # dev: no vault tokens received
    assert extcall IERC20(vaultToken).transfer(_recipient, vaultTokenAmountReceived, default_return_value=True) # dev: transfer failed

    # refund if full deposit didn't get through
    currentLegoBalance: uint256 = staticcall IERC20(_asset).balanceOf(self)
    refundAssetAmount: uint256 = 0
    if currentLegoBalance > preLegoBalance:
        refundAssetAmount = currentLegoBalance - preLegoBalance
        assert extcall IERC20(_asset).transfer(msg.sender, refundAssetAmount, default_return_value=True) # dev: transfer failed
        depositAmount -= refundAssetAmount

    usdValue: uint256 = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(_asset, depositAmount, miniAddys.missionControl, miniAddys.legoBook)
    log MoonwellDeposit(
        sender = msg.sender,
        asset = _asset,
        vaultToken = vaultToken,
        assetAmountDeposited = depositAmount,
        usdValue = usdValue,
        vaultTokenAmountReceived = vaultTokenAmountReceived,
        recipient = _recipient,
    )
    return depositAmount, vaultToken, vaultTokenAmountReceived, usdValue


# asset verification


@internal
def _getVaultTokenOnDeposit(_asset: address, _vaultAddr: address, _ledger: address, _legoBook: address) -> address:
    asset: address = yld.vaultToAsset[_vaultAddr]
    isRegistered: bool = True

    # not yet registered, call moonwell directly to get asset
    if asset == empty(address) and self._isValidCToken(_vaultAddr):
        asset = staticcall CompoundV2(_vaultAddr).underlying()
        isRegistered = False

    assert asset != empty(address) # dev: invalid asset
    assert asset == _asset # dev: asset mismatch

    # register if necessary
    if not isRegistered:
        self._registerAsset(asset, _vaultAddr)
        self._updateLedgerVaultToken(asset, _vaultAddr, _ledger, _legoBook)

    return _vaultAddr


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

    # verify asset (register if necessary)
    asset: address = self._getAssetOnWithdraw(_vaultToken, miniAddys.ledger, miniAddys.legoBook)

    # pre balances
    preLegoBalance: uint256 = staticcall IERC20(asset).balanceOf(self)
    preLegoVaultBalance: uint256 = staticcall IERC20(_vaultToken).balanceOf(self)

    # transfer vaults tokens to this contract
    vaultTokenAmount: uint256 = min(_amount, staticcall IERC20(_vaultToken).balanceOf(msg.sender))
    assert vaultTokenAmount != 0 # dev: nothing to transfer
    assert extcall IERC20(_vaultToken).transferFrom(msg.sender, self, vaultTokenAmount, default_return_value=True) # dev: transfer failed

    # withdraw assets from lego partner
    assert extcall CompoundV2(_vaultToken).redeem(max_value(uint256)) == 0 # dev: could not withdraw from moonwell

    # when withdrawing weth, they give eth
    if asset == WETH:
        extcall WethContract(WETH).deposit(value=self.balance)

    # validate received asset , transfer back to user
    assetAmountReceived: uint256 = staticcall IERC20(asset).balanceOf(self) - preLegoBalance
    assert assetAmountReceived != 0 # dev: no asset amount received
    assert extcall IERC20(asset).transfer(_recipient, assetAmountReceived, default_return_value=True) # dev: transfer failed

    # refund if full withdrawal didn't happen
    currentLegoVaultBalance: uint256 = staticcall IERC20(_vaultToken).balanceOf(self)
    refundVaultTokenAmount: uint256 = 0
    if currentLegoVaultBalance > preLegoVaultBalance:
        refundVaultTokenAmount = currentLegoVaultBalance - preLegoVaultBalance
        assert extcall IERC20(_vaultToken).transfer(msg.sender, refundVaultTokenAmount, default_return_value=True) # dev: transfer failed
        vaultTokenAmount -= refundVaultTokenAmount

    usdValue: uint256 = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(asset, assetAmountReceived, miniAddys.missionControl, miniAddys.legoBook)
    log MoonwellWithdrawal(
        sender = msg.sender,
        asset = asset,
        vaultToken = _vaultToken,
        assetAmountReceived = assetAmountReceived,
        usdValue = usdValue,
        vaultTokenAmountBurned = vaultTokenAmount,
        recipient = _recipient,
    )
    return vaultTokenAmount, asset, assetAmountReceived, usdValue


# vault token verification


@internal
def _getAssetOnWithdraw(_vaultToken: address, _ledger: address, _legoBook: address) -> address:
    asset: address = yld.vaultToAsset[_vaultToken]
    isRegistered: bool = True

    # not yet registered, call moonwell directly to get asset
    if asset == empty(address) and self._isValidCToken(_vaultToken):
        asset = staticcall CompoundV2(_vaultToken).underlying()
        isRegistered = False

    assert asset != empty(address) # dev: invalid asset

    # register if necessary
    if not isRegistered:
        self._registerAsset(asset, _vaultToken)
        self._updateLedgerVaultToken(asset, _vaultToken, _ledger, _legoBook)

    return asset


#############
# Utilities #
#############


@view
@external
def isRebasing() -> bool:
    return self._isRebasing()


@view
@internal
def _isRebasing() -> bool:
    return False


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
    return self._isValidCToken(_vaultToken)


@view
@internal
def _isValidCToken(_cToken: address) -> bool:
    compMarkets: DynArray[address, MAX_MARKETS] = staticcall MoonwellComptroller(MOONWELL_COMPTROLLER).getAllMarkets()
    return _cToken in compMarkets


@view
@external
def getUnderlyingAsset(_vaultToken: address) -> address:
    return self._getUnderlyingAsset(_vaultToken)


@view
@internal
def _getUnderlyingAsset(_vaultToken: address) -> address:
    asset: address = yld.vaultToAsset[_vaultToken]
    if asset == empty(address) and self._isValidCToken(_vaultToken):
        asset = staticcall CompoundV2(_vaultToken).underlying()
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
    return _vaultTokenAmount * staticcall CompoundV2(_vaultToken).exchangeRateStored() // (10 ** 18)


@view
@external
def getVaultTokenAmount(_asset: address, _assetAmount: uint256, _vaultToken: address) -> uint256:
    if empty(address) in [_asset, _vaultToken] or _assetAmount == 0:
        return 0 # bad inputs
    if self._getUnderlyingAsset(_vaultToken) != _asset:
        return 0 # invalid vault token or asset
    return _assetAmount * (10 ** 18) // staticcall CompoundV2(_vaultToken).exchangeRateStored()


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
    return staticcall CompoundV2(_vaultToken).totalSupply() * staticcall CompoundV2(_vaultToken).exchangeRateStored() // (10 ** 18)


@view
@external
def totalBorrows(_vaultToken: address) -> uint256:
    if not self._isVaultToken(_vaultToken):
        return 0 # invalid vault token
    return staticcall CompoundV2(_vaultToken).totalBorrows()


# price per share


@view
@external
def getPricePerShare(_asset: address, _decimals: uint256) -> uint256:
    return 0


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
    assert extcall IERC20(_asset).approve(_vaultAddr, max_value(uint256), default_return_value=True) # dev: max approval failed
    yld._addAssetOpportunity(_asset, _vaultAddr)


@external
def removeAssetOpportunity(_asset: address, _vaultAddr: address):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert extcall IERC20(_asset).approve(_vaultAddr, 0, default_return_value=True) # dev: max approval failed
    yld._removeAssetOpportunity(_asset, _vaultAddr)


# validation


@view
@internal
def isValidAssetOpportunity(_asset: address, _vaultAddr: address) -> bool:
    return self._isValidAssetOpportunity(_asset, _vaultAddr)


@view
@internal
def _isValidAssetOpportunity(_asset: address, _vaultAddr: address) -> bool:
    return self._isValidCToken(_vaultAddr) and staticcall CompoundV2(_vaultAddr).underlying() == _asset


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
def claimRewards(
    _user: address,
    _rewardToken: address,
    _rewardAmount: uint256,
    _extraData: bytes32,
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
