#     __   __ ___ _______ ___     ______       ___     _______ _______ _______ 
#    |  | |  |   |       |   |   |      |     |   |   |       |       |       |
#    |  |_|  |   |    ___|   |   |  _    |    |   |   |    ___|    ___|   _   |
#    |       |   |   |___|   |   | | |   |    |   |   |   |___|   | __|  | |  |
#    |_     _|   |    ___|   |___| |_|   |    |   |___|    ___|   ||  |  |_|  |
#      |   | |   |   |___|       |       |    |       |   |___|   |_| |       |
#      |___| |___|_______|_______|______|     |_______|_______|_______|_______|
#                                                                       
#     ╔═══════════════════════════════════╗
#     ║  ** Sky Psm **                    ║
#     ║  Integration with Sky Protocol.   ║
#     ╚═══════════════════════════════════╝
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

interface SkyPsm:
    def swapExactIn(_assetIn: address, _assetOut: address, _amountIn: uint256, _minAmountOut: uint256, _receiver: address, _referralCode: uint256) -> uint256: nonpayable
    def previewSwapExactIn(_assetIn: address, _assetOut: address, _amountIn: uint256) -> uint256: view
    def convertToAssets(_asset: address, _numShares: uint256) -> uint256: view
    def convertToShares(_asset: address, _amount: uint256) -> uint256: view
    def totalAssets() -> uint256: view
    def susds() -> address: view
    def usds() -> address: view

interface Appraiser:
    def getUsdValue(_asset: address, _amount: uint256, _missionControl: address = empty(address), _legoBook: address = empty(address), _ledger: address = empty(address)) -> uint256: view
    def updatePriceAndGetUsdValue(_asset: address, _amount: uint256, _missionControl: address = empty(address), _legoBook: address = empty(address)) -> uint256: nonpayable

interface Ledger:
    def setVaultToken(_vaultToken: address, _legoId: uint256, _underlyingAsset: address, _decimals: uint256, _isRebasing: bool): nonpayable
    def isRegisteredVaultToken(_vaultToken: address) -> bool: view

interface Registry:
    def getRegId(_addr: address) -> uint256: view

event SkyPsmDeposit:
    sender: indexed(address)
    asset: indexed(address)
    vaultToken: indexed(address)
    assetAmountDeposited: uint256
    usdValue: uint256
    vaultTokenAmountReceived: uint256
    recipient: address

event SkyPsmWithdrawal:
    sender: indexed(address)
    asset: indexed(address)
    vaultToken: indexed(address)
    assetAmountReceived: uint256
    usdValue: uint256
    vaultTokenAmountBurned: uint256
    recipient: address

event SlippageSet:
    slippage: uint256

slippage: public(uint256)

MAX_TOKEN_PATH: constant(uint256) = 5
HUNDRED_PERCENT: constant(uint256) = 100_00 # 100.00%

SKY_PSM: public(immutable(address))
USDS: public(immutable(address))
SUSDS: public(immutable(address))


@deploy
def __init__(_undyHq: address, _skyPsm: address):
    addys.__init__(_undyHq)
    yld.__init__(False)

    self.slippage = 50 # 0.50%

    assert _skyPsm != empty(address) # dev: invalid addrs
    SKY_PSM = _skyPsm
    USDS = staticcall SkyPsm(_skyPsm).usds()
    SUSDS = staticcall SkyPsm(_skyPsm).susds()


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

    # transfer deposit asset to this contract
    depositAmount: uint256 = min(_amount, staticcall IERC20(_asset).balanceOf(msg.sender))
    assert depositAmount != 0 # dev: nothing to transfer
    assert extcall IERC20(_asset).transferFrom(msg.sender, self, depositAmount, default_return_value=True) # dev: transfer failed

    # deposit assets into lego partner
    skyPsm: address = SKY_PSM
    expectedVaultTokenAmount: uint256 = staticcall SkyPsm(skyPsm).previewSwapExactIn(_asset, vaultToken, depositAmount)
    minAmountOut: uint256 = expectedVaultTokenAmount * (HUNDRED_PERCENT - self.slippage) // HUNDRED_PERCENT
    vaultTokenAmountReceived: uint256 = extcall SkyPsm(skyPsm).swapExactIn(_asset, vaultToken, depositAmount, minAmountOut, _recipient, 0)
    assert vaultTokenAmountReceived != 0 # dev: no vault tokens received

    # refund if full deposit didn't get through
    currentLegoBalance: uint256 = staticcall IERC20(_asset).balanceOf(self)
    refundAssetAmount: uint256 = 0
    if currentLegoBalance > preLegoBalance:
        refundAssetAmount = currentLegoBalance - preLegoBalance
        assert extcall IERC20(_asset).transfer(msg.sender, refundAssetAmount, default_return_value=True) # dev: transfer failed
        depositAmount -= refundAssetAmount

    usdValue: uint256 = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(_asset, depositAmount, miniAddys.missionControl, miniAddys.legoBook)
    log SkyPsmDeposit(
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

    # not yet registered, call sky psm directly to get usds
    if asset == empty(address) and self._isValidSkyVault(_vaultAddr):
        asset = USDS
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
    preLegoVaultBalance: uint256 = staticcall IERC20(_vaultToken).balanceOf(self)

    # transfer vaults tokens to this contract
    vaultTokenAmount: uint256 = min(_amount, staticcall IERC20(_vaultToken).balanceOf(msg.sender))
    assert vaultTokenAmount != 0 # dev: nothing to transfer
    assert extcall IERC20(_vaultToken).transferFrom(msg.sender, self, vaultTokenAmount, default_return_value=True) # dev: transfer failed

    # withdraw assets from lego partner
    skyPsm: address = SKY_PSM
    expectedAssetAmount: uint256 = staticcall SkyPsm(skyPsm).previewSwapExactIn(_vaultToken, asset, vaultTokenAmount)
    minAmountOut: uint256 = expectedAssetAmount * (HUNDRED_PERCENT - self.slippage) // HUNDRED_PERCENT
    assetAmountReceived: uint256 = extcall SkyPsm(skyPsm).swapExactIn(_vaultToken, asset, vaultTokenAmount, minAmountOut, _recipient, 0)
    assert assetAmountReceived != 0 # dev: no asset amount received

    # refund if full withdrawal didn't happen
    currentLegoVaultBalance: uint256 = staticcall IERC20(_vaultToken).balanceOf(self)
    refundVaultTokenAmount: uint256 = 0
    if currentLegoVaultBalance > preLegoVaultBalance:
        refundVaultTokenAmount = currentLegoVaultBalance - preLegoVaultBalance
        assert extcall IERC20(_vaultToken).transfer(msg.sender, refundVaultTokenAmount, default_return_value=True) # dev: transfer failed
        vaultTokenAmount -= refundVaultTokenAmount

    usdValue: uint256 = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(asset, assetAmountReceived, miniAddys.missionControl, miniAddys.legoBook)
    log SkyPsmWithdrawal(
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

    # not yet registered, call sky psm directly to get usds
    if asset == empty(address) and self._isValidSkyVault(_vaultToken):
        asset = USDS
        isRegistered = False

    assert asset != empty(address) # dev: invalid asset

    # register if necessary
    if not isRegistered:
        self._registerAsset(asset, _vaultToken)
        self._updateLedgerVaultToken(asset, _vaultToken, _ledger, _legoBook)

    return asset


# set slippage


@external
def setSlippage(_slippage: uint256) -> bool:
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert _slippage != 0 and _slippage < HUNDRED_PERCENT # dev: invalid slippage
    self.slippage = _slippage
    log SlippageSet(slippage=_slippage)
    return True


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
    # as far as we can tell, this must be done offchain
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
    if yld.vaultToAsset[_vaultToken] != empty(address):
        return True
    return self._isValidSkyVault(_vaultToken)


@view
@external
def isValidSkyVault(_vaultToken: address) -> bool:
    return self._isValidSkyVault(_vaultToken)


@view
@internal
def _isValidSkyVault(_vaultToken: address) -> bool:
    return _vaultToken == SUSDS


@view
@external
def getUnderlyingAsset(_vaultToken: address) -> address:
    return self._getUnderlyingAsset(_vaultToken)


@view
@internal
def _getUnderlyingAsset(_vaultToken: address) -> address:
    asset: address = yld.vaultToAsset[_vaultToken]
    if asset == empty(address) and self._isValidSkyVault(_vaultToken):
        asset = USDS
    return asset


# underlying amount


@view
@external
def getUnderlyingAmount(_vaultToken: address, _vaultTokenAmount: uint256) -> uint256:
    asset: address = self._getUnderlyingAsset(_vaultToken)
    if asset == empty(address) or _vaultTokenAmount == 0:
        return 0 # invalid asset or amount
    return self._getUnderlyingAmount(asset, _vaultTokenAmount)


@view
@internal
def _getUnderlyingAmount(_asset: address, _vaultTokenAmount: uint256) -> uint256:
    return staticcall SkyPsm(SKY_PSM).convertToAssets(_asset, _vaultTokenAmount)


@view
@external
def getVaultTokenAmount(_asset: address, _assetAmount: uint256, _vaultToken: address) -> uint256:
    if empty(address) in [_asset, _vaultToken] or _assetAmount == 0:
        return 0 # bad inputs
    if self._getUnderlyingAsset(_vaultToken) != _asset:
        return 0 # invalid vault token or asset
    return staticcall SkyPsm(SKY_PSM).convertToShares(_asset, _assetAmount)


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
    underlyingAmount: uint256 = self._getUnderlyingAmount(asset, _vaultTokenAmount)
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
    return staticcall SkyPsm(SKY_PSM).totalAssets()


@view
@external
def totalBorrows(_vaultToken: address) -> uint256:
    return 0


# price per share


@view
@external
def getPricePerShare(_asset: address, _decimals: uint256) -> uint256:
    if _asset != SUSDS:
        return 0
    return staticcall SkyPsm(SKY_PSM).convertToAssets(USDS, 10 ** _decimals)


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
    skyPsm: address = SKY_PSM
    assert extcall IERC20(_asset).approve(skyPsm, max_value(uint256), default_return_value=True) # dev: max approval failed
    assert extcall IERC20(_vaultAddr).approve(skyPsm, max_value(uint256), default_return_value=True) # dev: max approval failed
    yld._addAssetOpportunity(_asset, _vaultAddr)


@external
def removeAssetOpportunity(_asset: address, _vaultAddr: address):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    skyPsm: address = SKY_PSM
    assert extcall IERC20(_asset).approve(skyPsm, 0, default_return_value=True) # dev: max approval failed
    assert extcall IERC20(_vaultAddr).approve(skyPsm, 0, default_return_value=True) # dev: max approval failed
    yld._removeAssetOpportunity(_asset, _vaultAddr)


# validation


@view
@internal
def isValidAssetOpportunity(_asset: address, _vaultAddr: address) -> bool:
    return self._isValidAssetOpportunity(_asset, _vaultAddr)


@view
@internal
def _isValidAssetOpportunity(_asset: address, _vaultAddr: address) -> bool:
    return self._isValidSkyVault(_vaultAddr) and USDS == _asset


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
