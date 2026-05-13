#     __   __ ___ _______ ___     ______       ___     _______ _______ _______ 
#    |  | |  |   |       |   |   |      |     |   |   |       |       |       |
#    |  |_|  |   |    ___|   |   |  _    |    |   |   |    ___|    ___|   _   |
#    |       |   |   |___|   |   | | |   |    |   |   |   |___|   | __|  | |  |
#    |_     _|   |    ___|   |___| |_|   |    |   |___|    ___|   ||  |  |_|  |
#      |   | |   |   |___|       |       |    |       |   |___|   |_| |       |
#      |___| |___|_______|_______|______|     |_______|_______|_______|_______|
#                                                                       
#     ╔═════════════════════════════════════╗
#     ║  ** Wasabi Protocol **              ║
#     ║  Integration with Wasabi Protocol.  ║
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
from interfaces import LegoStructs as ls

import contracts.modules.Addys as addys
import contracts.modules.YieldLegoData as yld

from ethereum.ercs import IERC20
from ethereum.ercs import IERC4626
from ethereum.ercs import IERC20Detailed

interface Ledger:
    def setVaultToken(_vaultToken: address, _legoId: uint256, _underlyingAsset: address, _decimals: uint256, _isRebasing: bool): nonpayable
    def isRegisteredVaultToken(_vaultToken: address) -> bool: view
    def isUserWallet(_user: address) -> bool: view

interface Registry:
    def getRegId(_addr: address) -> uint256: view
    def isValidAddr(_addr: address) -> bool: view

interface Appraiser:
    def getUnderlyingUsdValue(_asset: address, _amount: uint256) -> uint256: view

interface VaultRegistry:
    def isEarnVault(_vaultAddr: address) -> bool: view

interface WasabiRegistry:
    def getVault(_asset: address) -> address: view

event WasabiDeposit:
    sender: indexed(address)
    asset: indexed(address)
    vaultToken: indexed(address)
    assetAmountDeposited: uint256
    usdValue: uint256
    vaultTokenAmountReceived: uint256
    recipient: address

event WasabiWithdrawal:
    sender: indexed(address)
    asset: indexed(address)
    vaultToken: indexed(address)
    assetAmountReceived: uint256
    usdValue: uint256
    vaultTokenAmountBurned: uint256
    recipient: address

# wasabi
WASABI_LONG_POOL: public(immutable(address))
WASABI_SHORT_POOL: public(immutable(address))
RIPE_REGISTRY: public(immutable(address))

MAX_TOKEN_PATH: constant(uint256) = 5
MAX_PROOFS: constant(uint256) = 25
HUNDRED_PERCENT: constant(uint256) = 100_00
MIN_WITHDRAWAL_UNITS: constant(uint256) = 10 # 10 whole underlying units; $10 for USDC
WASABI_EMERGENCY_PRICE_PER_SHARE: constant(uint256) = 1_107_017 # 1.107017 USDC per 1e6 Wasabi shares


@deploy
def __init__(_undyHq: address, _wasabiLongPool: address, _wasabiShortPool: address, _ripeRegistry: address):
    addys.__init__(_undyHq)
    yld.__init__(False)

    assert empty(address) not in [_wasabiLongPool, _wasabiShortPool, _ripeRegistry] # dev: invalid addrs
    WASABI_LONG_POOL = _wasabiLongPool
    WASABI_SHORT_POOL = _wasabiShortPool
    RIPE_REGISTRY = _ripeRegistry


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
    return [WASABI_LONG_POOL, WASABI_SHORT_POOL]


@view
@external
def isYieldLego() -> bool:
    return True


@view
@external
def isDexLego() -> bool:
    return False


###################
# Underlying Data #
###################


# underlying asset


@view
@external
def getUnderlyingAsset(_vaultToken: address) -> address:
    return self._getUnderlyingAsset(_vaultToken)


@view
@internal
def _getUnderlyingAsset(_vaultToken: address) -> address:
    asset: address = yld.vaultToAsset[_vaultToken].underlyingAsset
    if asset != empty(address):
        return asset
    return staticcall IERC4626(_vaultToken).asset()


# underlying balances (both true and safe)


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


# underlying amount (true)


@view
@external
def getUnderlyingAmount(_vaultToken: address, _vaultTokenAmount: uint256) -> uint256:
    return self._getUnderlyingAmount(_vaultToken, _vaultTokenAmount)


@view
@internal
def _getUnderlyingAmount(_vaultToken: address, _vaultTokenAmount: uint256) -> uint256:
    # temp emergency peg: restore live pricing after users exit Wasabi
    # return staticcall IERC4626(_vaultToken).previewRedeem(_vaultTokenAmount)
    vaultTokenDecimals: uint256 = self._getVaultTokenDecimals(_vaultToken)
    return self._getEmergencyPeggedUnderlyingAmount(_vaultToken, _vaultTokenAmount, vaultTokenDecimals)


# underlying amount (safe)


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

    # temp emergency peg: restore cached snapshot pricing after users exit Wasabi
    # return _vaultTokenBalance * vaultInfo.lastAveragePricePerShare // (10 ** vaultInfo.decimals)
    return self._getEmergencyPeggedUnderlyingAmount(_vaultToken, _vaultTokenBalance, vaultInfo.decimals)


# underlying data (combined)


@view
@external
def getUnderlyingData(_vaultToken: address, _vaultTokenAmount: uint256, _appraiser: address = empty(address)) -> (address, uint256, uint256):
    return self._getUnderlyingData(_vaultToken, _vaultTokenAmount, _appraiser)


@view
@internal
def _getUnderlyingData(_vaultToken: address, _vaultTokenAmount: uint256, _appraiser: address) -> (address, uint256, uint256):
    asset: address = self._getUnderlyingAsset(_vaultToken)
    if asset == empty(address):
        return empty(address), 0, 0 # invalid vault token
    underlyingAmount: uint256 = self._getUnderlyingAmount(_vaultToken, _vaultTokenAmount)
    usdValue: uint256 = self._getUsdValue(asset, underlyingAmount, _appraiser)
    return asset, underlyingAmount, usdValue


# usd value


@view
@external
def getUsdValueOfVaultToken(_vaultToken: address, _vaultTokenAmount: uint256, _appraiser: address = empty(address)) -> uint256:
    return self._getUsdValueOfVaultToken(_vaultToken, _vaultTokenAmount, _appraiser)


@view
@internal
def _getUsdValueOfVaultToken(_vaultToken: address, _vaultTokenAmount: uint256, _appraiser: address) -> uint256:
    return self._getUnderlyingData(_vaultToken, _vaultTokenAmount, _appraiser)[2]


@view
@internal
def _getUsdValue(_asset: address, _amount: uint256, _appraiser: address) -> uint256:
    appraiser: address = _appraiser
    if _appraiser == empty(address):
        appraiser = addys._getAppraiserAddr()
    return staticcall Appraiser(appraiser).getUnderlyingUsdValue(_asset, _amount)


###############
# Other Utils #
###############


# basics


@view
@external
def isRebasing() -> bool:
    return self._isRebasing()


@pure
@internal
def _isRebasing() -> bool:
    return False


# emergency peg


@view
@internal
def _getAssetDecimals(_asset: address) -> uint256:
    return convert(staticcall IERC20Detailed(_asset).decimals(), uint256)


@view
@internal
def _getVaultTokenDecimals(_vaultToken: address) -> uint256:
    decimals: uint256 = yld.vaultToAsset[_vaultToken].decimals
    if decimals == 0:
        decimals = convert(staticcall IERC20Detailed(_vaultToken).decimals(), uint256)
    return decimals


@view
@internal
def _getEmergencyPeggedPricePerShare(_vaultToken: address) -> uint256:
    asset: address = self._getUnderlyingAsset(_vaultToken)
    if asset == empty(address):
        return 0
    return WASABI_EMERGENCY_PRICE_PER_SHARE


@view
@internal
def _getEmergencyPeggedUnderlyingAmount(_vaultToken: address, _vaultTokenAmount: uint256, _vaultTokenDecimals: uint256) -> uint256:
    if _vaultTokenAmount == 0 or _vaultTokenDecimals == 0:
        return 0

    pricePerShare: uint256 = self._getEmergencyPeggedPricePerShare(_vaultToken)
    if pricePerShare == 0:
        return 0

    return _vaultTokenAmount * pricePerShare // (10 ** _vaultTokenDecimals)


@view
@internal
def _getMinWithdrawalAmount(_vaultToken: address) -> uint256:
    asset: address = self._getUnderlyingAsset(_vaultToken)
    if asset == empty(address):
        return 0
    return MIN_WITHDRAWAL_UNITS * 10 ** self._getAssetDecimals(asset)


# price per share


@view
@external
def getPricePerShare(_vaultToken: address, _decimals: uint256 = 0) -> uint256:
    decimals: uint256 = _decimals
    if decimals == 0:
        decimals = yld.vaultToAsset[_vaultToken].decimals
    if decimals == 0:
        decimals = convert(staticcall IERC20Detailed(_vaultToken).decimals(), uint256)
    return self._getPricePerShare(_vaultToken, decimals)


@view
@internal
def _getPricePerShare(_vaultToken: address, _decimals: uint256) -> uint256:
    # temp emergency peg: restore live PPS after users exit Wasabi
    # return staticcall IERC4626(_vaultToken).previewRedeem(10 ** _decimals)
    return self._getEmergencyPeggedPricePerShare(_vaultToken)


# vault token amount


@view
@external
def getVaultTokenAmount(_asset: address, _assetAmount: uint256, _vaultToken: address) -> uint256:
    # actual withdrawal sizing stays live
    return staticcall IERC4626(_vaultToken).convertToShares(_assetAmount)


# total assets


@view
@external
def totalAssets(_vaultToken: address) -> uint256:
    return self._totalAssets(_vaultToken)


@view
@internal
def _totalAssets(_vaultToken: address) -> uint256:
    # temp emergency peg: restore live total assets after users exit Wasabi
    # return staticcall IERC4626(_vaultToken).totalAssets()
    vaultTokenDecimals: uint256 = self._getVaultTokenDecimals(_vaultToken)
    return self._getEmergencyPeggedUnderlyingAmount(_vaultToken, staticcall IERC20(_vaultToken).totalSupply(), vaultTokenDecimals)


# total borrows


@view
@external
def totalBorrows(_vaultToken: address) -> uint256:
    return self._totalBorrows(_vaultToken)


@view
@internal
def _totalBorrows(_vaultToken: address) -> uint256:
    # totalBorrows = totalAssets - available liquidity (underlying balance in vault)
    totalAssets: uint256 = self._totalAssets(_vaultToken)
    availLiquidity: uint256 = self._getAvailLiquidity(_vaultToken)
    if totalAssets <= availLiquidity:
        return 0
    return totalAssets - availLiquidity


# avail liquidity


@view
@external
def getAvailLiquidity(_vaultToken: address) -> uint256:
    return self._getAvailLiquidity(_vaultToken)


@view
@internal
def _getAvailLiquidity(_vaultToken: address) -> uint256:
    # available liquidity = underlying tokens actually held in the vault
    asset: address = staticcall IERC4626(_vaultToken).asset()
    return staticcall IERC20(asset).balanceOf(_vaultToken)


# utilization


@view
@external
def getUtilizationRatio(_vaultToken: address) -> uint256:
    totalAssets: uint256 = self._totalAssets(_vaultToken)
    if totalAssets == 0:
        return 0
    totalBorrows: uint256 = self._totalBorrows(_vaultToken)
    return totalBorrows * HUNDRED_PERCENT // totalAssets


# extras


@view
@external
def isEligibleForYieldBonus(_asset: address) -> bool:
    return False


@view
@external
def getWithdrawalFees(_vaultToken: address, _vaultTokenAmount: uint256) -> uint256:
    return 0


################
# Registration #
################


# can vault be registered


@view
@external
def canRegisterVaultToken(_asset: address, _vaultToken: address) -> bool:
    return self._canRegisterVaultToken(_asset, _vaultToken)


@view
@internal
def _canRegisterVaultToken(_asset: address, _vaultToken: address) -> bool:
    if empty(address) in [_asset, _vaultToken]:
        return False
    if staticcall IERC4626(_vaultToken).asset() != _asset:
        return False
    return staticcall WasabiRegistry(WASABI_LONG_POOL).getVault(_asset) == _vaultToken or staticcall WasabiRegistry(WASABI_SHORT_POOL).getVault(_asset) == _vaultToken


# register vault token locally


@external
def registerVaultTokenLocally(_asset: address, _vaultAddr: address) -> ls.VaultTokenInfo:
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert self._canRegisterVaultToken(_asset, _vaultAddr) # dev: cannot register vault token
    assert not yld._isAssetOpportunity(_asset, _vaultAddr) # dev: already registered
    vaultInfo: ls.VaultTokenInfo = self._registerVaultTokenLocally(_asset, _vaultAddr)
    self._registerVaultTokenGlobally(_asset, _vaultAddr, vaultInfo.decimals, addys._getLedgerAddr(), addys._getLegoBookAddr())
    return vaultInfo


@internal
def _registerVaultTokenLocally(_asset: address, _vaultAddr: address) -> ls.VaultTokenInfo:
    assert extcall IERC20(_asset).approve(_vaultAddr, max_value(uint256), default_return_value=True) # dev: max approval failed
    vaultInfo: ls.VaultTokenInfo = yld._addAssetOpportunity(_asset, _vaultAddr)
    assert vaultInfo.decimals != 0 # dev: invalid vault token
    return vaultInfo


# remove vault token locally


@external
def deregisterVaultTokenLocally(_asset: address, _vaultAddr: address):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert yld._isAssetOpportunity(_asset, _vaultAddr) # dev: already registered
    self._deregisterVaultTokenLocally(_asset, _vaultAddr)


@internal
def _deregisterVaultTokenLocally(_asset: address, _vaultAddr: address):
    assert extcall IERC20(_asset).approve(_vaultAddr, 0, default_return_value=True) # dev: max approval failed
    yld._removeAssetOpportunity(_asset, _vaultAddr)


# ledger registration


@internal
def _registerVaultTokenGlobally(_underlyingAsset: address, _vaultToken: address, _decimals: uint256, _ledger: address, _legoBook: address):
    if not staticcall Ledger(_ledger).isRegisteredVaultToken(_vaultToken):
        legoId: uint256 = staticcall Registry(_legoBook).getRegId(self)
        extcall Ledger(_ledger).setVaultToken(_vaultToken, legoId, _underlyingAsset, _decimals, self._isRebasing())


#################
# Yield Actions #
#################


# access control


@view
@internal
def _isAllowedToPerformAction(_caller: address) -> bool:
    # NOTE: important to not trust `_miniAddys` here, that's why getting ledger and vault registry from addys
    if staticcall VaultRegistry(addys._getVaultRegistryAddr()).isEarnVault(_caller):
        return True
    if staticcall Ledger(addys._getLedgerAddr()).isUserWallet(_caller):
        return True
    return staticcall Registry(RIPE_REGISTRY).isValidAddr(_caller) # Ripe Endaoment is allowed


# add price snapshot


@external
def addPriceSnapshot(_vaultToken: address) -> bool:
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    vaultInfo: ls.VaultTokenInfo = yld.vaultToAsset[_vaultToken]
    assert vaultInfo.decimals != 0 # dev: not registered
    pricePerShare: uint256 = self._getPricePerShare(_vaultToken, vaultInfo.decimals)
    return yld._addPriceSnapshot(_vaultToken, pricePerShare, vaultInfo.decimals)


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
    raise "not allowing deposits right now"


# vault info on deposit


@internal
def _getVaultInfoOnDeposit(_asset: address, _vaultAddr: address, _ledger: address, _legoBook: address) -> ls.VaultTokenInfo:
    vaultInfo: ls.VaultTokenInfo = yld.vaultToAsset[_vaultAddr]
    if vaultInfo.decimals == 0:
        assert self._canRegisterVaultToken(_asset, _vaultAddr) # dev: cannot register vault token
        vaultInfo = self._registerVaultTokenLocally(_asset, _vaultAddr)
        self._registerVaultTokenGlobally(_asset, _vaultAddr, vaultInfo.decimals, _ledger, _legoBook)
    else:
        assert vaultInfo.underlyingAsset == _asset # dev: asset mismatch
    return vaultInfo


# withdraw


@external
def withdrawFromYield(
    _vaultToken: address,
    _amount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, address, uint256, uint256):
    assert self._isAllowedToPerformAction(msg.sender) # dev: no perms
    assert not yld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = yld._getMiniAddys(_miniAddys)
    vaultInfo: ls.VaultTokenInfo = self._getVaultInfoOnWithdrawal(_vaultToken, miniAddys.ledger, miniAddys.legoBook)

    # skip withdrawal if liquidity is too low, but still refresh price snapshot
    availLiquidity: uint256 = self._getAvailLiquidity(_vaultToken)
    if availLiquidity <= self._getMinWithdrawalAmount(_vaultToken):
        pricePerShare: uint256 = self._getPricePerShare(_vaultToken, vaultInfo.decimals)
        yld._addPriceSnapshot(_vaultToken, pricePerShare, vaultInfo.decimals)
        return 0, vaultInfo.underlyingAsset, 0, 0

    # pre balances
    preLegoVaultBalance: uint256 = staticcall IERC20(_vaultToken).balanceOf(self)

    # transfer vaults tokens to this contract
    vaultTokenAmount: uint256 = min(_amount, staticcall IERC20(_vaultToken).balanceOf(msg.sender))
    assert vaultTokenAmount != 0 # dev: nothing to transfer
    assert extcall IERC20(_vaultToken).transferFrom(msg.sender, self, vaultTokenAmount, default_return_value=True) # dev: transfer failed

    assetAmountReceived: uint256 = 0
    redeemVaultTokenAmount: uint256 = min(vaultTokenAmount, staticcall IERC4626(_vaultToken).convertToShares(availLiquidity))
    if redeemVaultTokenAmount != 0:

        # withdraw assets from lego partner
        assetAmountReceived = extcall IERC4626(_vaultToken).redeem(redeemVaultTokenAmount, _recipient, self)
        assert assetAmountReceived != 0 # dev: no asset amount received

    # refund if full withdrawal didn't happen
    currentLegoVaultBalance: uint256 = staticcall IERC20(_vaultToken).balanceOf(self)
    refundVaultTokenAmount: uint256 = 0
    if currentLegoVaultBalance > preLegoVaultBalance:
        refundVaultTokenAmount = currentLegoVaultBalance - preLegoVaultBalance
        assert extcall IERC20(_vaultToken).transfer(msg.sender, refundVaultTokenAmount, default_return_value=True) # dev: transfer failed
        vaultTokenAmount -= refundVaultTokenAmount

    usdValue: uint256 = 0
    if assetAmountReceived != 0:
        usdValue = staticcall Appraiser(miniAddys.appraiser).getUnderlyingUsdValue(vaultInfo.underlyingAsset, assetAmountReceived)

    log WasabiWithdrawal(
        sender = msg.sender,
        asset = vaultInfo.underlyingAsset,
        vaultToken = _vaultToken,
        assetAmountReceived = assetAmountReceived,
        usdValue = usdValue,
        vaultTokenAmountBurned = vaultTokenAmount,
        recipient = _recipient,
    )

    # add price snapshot
    pricePerShare: uint256 = self._getPricePerShare(_vaultToken, vaultInfo.decimals)
    yld._addPriceSnapshot(_vaultToken, pricePerShare, vaultInfo.decimals)

    return vaultTokenAmount, vaultInfo.underlyingAsset, assetAmountReceived, usdValue


# vault info on withdrawal


@internal
def _getVaultInfoOnWithdrawal(_vaultAddr: address, _ledger: address, _legoBook: address) -> ls.VaultTokenInfo:
    vaultInfo: ls.VaultTokenInfo = yld.vaultToAsset[_vaultAddr]
    if vaultInfo.decimals == 0:
        asset: address = staticcall IERC4626(_vaultAddr).asset()
        assert self._canRegisterVaultToken(asset, _vaultAddr) # dev: cannot register vault token
        vaultInfo = self._registerVaultTokenLocally(asset, _vaultAddr)
        self._registerVaultTokenGlobally(asset, _vaultAddr, vaultInfo.decimals, _ledger, _legoBook)
    return vaultInfo


#########
# Other #
#########


@view
@external
def getAccessForLego(_user: address, _action: ws.ActionType) -> (address, String[64], uint256):
    return empty(address), empty(String[64]), 0


@pure
@external
def claimRewards(
    _user: address,
    _rewardToken: address,
    _rewardAmount: uint256,
    _extraData: bytes32,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    # backwards compatibility
    return 0, 0


@external
def claimIncentives(
    _user: address,
    _rewardToken: address,
    _rewardAmount: uint256,
    _proofs: DynArray[bytes32, MAX_PROOFS],
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    return 0, 0


@pure
@external
def hasClaimableRewards(_user: address) -> bool:
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
