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

from ethereum.ercs import IERC20
from ethereum.ercs import IERC20Detailed

interface ExtraFiPool:
    def redeem(_reserveId: uint256, _eTokenAmount: uint256, _recipient: address, _receiveNativeETH: bool) -> uint256: nonpayable
    def deposit(_reserveId: uint256, _amount: uint256, _onBehalfOf: address, _referralCode: uint16) -> uint256: payable
    def getUnderlyingTokenAddress(_reserveId: uint256) -> address: view
    def totalLiquidityOfReserve(_reserveId: uint256) -> uint256: view
    def totalBorrowsOfReserve(_reserveId: uint256) -> uint256: view
    def exchangeRateOfReserve(_reserveId: uint256) -> uint256: view
    def getETokenAddress(_reserveId: uint256) -> address: view

interface Ledger:
    def setVaultToken(_vaultToken: address, _legoId: uint256, _underlyingAsset: address, _decimals: uint256, _isRebasing: bool): nonpayable
    def isRegisteredVaultToken(_vaultToken: address) -> bool: view
    def isUserWallet(_user: address) -> bool: view

interface Appraiser:
    def getUsdValue(_asset: address, _amount: uint256, _missionControl: address = empty(address), _legoBook: address = empty(address), _ledger: address = empty(address)) -> uint256: view
    def updatePriceAndGetUsdValue(_asset: address, _amount: uint256, _missionControl: address = empty(address), _legoBook: address = empty(address)) -> uint256: nonpayable

interface Registry:
    def getRegId(_addr: address) -> uint256: view
    def isValidAddr(_addr: address) -> bool: view

interface VaultRegistry:
    def isEarnVault(_vaultAddr: address) -> bool: view

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
RIPE_REGISTRY: public(immutable(address))

MAX_MARKETS: constant(uint256) = 50
MAX_ASSETS: constant(uint256) = 25
MAX_TOKEN_PATH: constant(uint256) = 5
MAX_PROOFS: constant(uint256) = 25


@deploy
def __init__(_undyHq: address, _extraFiPool: address, _ripeRegistry: address):
    addys.__init__(_undyHq)
    yld.__init__(False)

    assert _extraFiPool != empty(address) # dev: invalid addr
    EXTRAFI_POOL = _extraFiPool

    assert _ripeRegistry != empty(address) # dev: invalid addrs
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
    return [EXTRAFI_POOL]


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
    return yld.vaultToAsset[_vaultToken].underlyingAsset


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
    reserveId: uint256 = self.vaultTokenToReserveId[_vaultToken]
    if reserveId == 0:
        return 0
    return _vaultTokenAmount * staticcall ExtraFiPool(EXTRAFI_POOL).exchangeRateOfReserve(reserveId) // (10 ** 18)


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

    # safe underlying amount (using cached weighted average from snapshots)
    return _vaultTokenBalance * vaultInfo.lastAveragePricePerShare // (10 ** vaultInfo.decimals)


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
    return staticcall Appraiser(appraiser).getUsdValue(_asset, _amount)


###############
# Other Utils #
###############


# basics


@view
@external
def isRebasing() -> bool:
    return self._isRebasing()


@view
@internal
def _isRebasing() -> bool:
    return False


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
    reserveId: uint256 = self.vaultTokenToReserveId[_vaultToken]
    if reserveId == 0:
        return 0
    return staticcall ExtraFiPool(EXTRAFI_POOL).exchangeRateOfReserve(reserveId) * (10 ** _decimals) // (10 ** 18)


# vault token amount


@view
@external
def getVaultTokenAmount(_asset: address, _assetAmount: uint256, _vaultToken: address) -> uint256:
    reserveId: uint256 = self.vaultTokenToReserveId[_vaultToken]
    if reserveId == 0:
        return 0
    return _assetAmount * (10 ** 18) // staticcall ExtraFiPool(EXTRAFI_POOL).exchangeRateOfReserve(reserveId)


# extras


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
def totalAssets(_vaultToken: address) -> uint256:
    reserveId: uint256 = self.vaultTokenToReserveId[_vaultToken]
    return staticcall ExtraFiPool(EXTRAFI_POOL).totalLiquidityOfReserve(reserveId)


@view
@external
def totalBorrows(_vaultToken: address) -> uint256:
    reserveId: uint256 = self.vaultTokenToReserveId[_vaultToken]
    return staticcall ExtraFiPool(EXTRAFI_POOL).totalBorrowsOfReserve(reserveId)


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
    # no `_reserveId` param can be passed here, so not implemented
    return False


@view
@internal
def _canRegisterVaultToken(_asset: address, _vaultToken: address, _reserveId: uint256) -> bool:
    if empty(address) in [_asset, _vaultToken]:
        return False
    if _reserveId == 0:
        return False
    extraFiPool: address = EXTRAFI_POOL
    if staticcall ExtraFiPool(extraFiPool).getUnderlyingTokenAddress(_reserveId) != _asset:
        return False
    return staticcall ExtraFiPool(extraFiPool).getETokenAddress(_reserveId) == _vaultToken


# register vault token locally


@external
def registerVaultTokenLocally(_asset: address, _vaultAddr: address, _reserveId: uint256) -> ls.VaultTokenInfo:
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert self._canRegisterVaultToken(_asset, _vaultAddr, _reserveId) # dev: cannot register vault token
    assert not yld._isAssetOpportunity(_asset, _vaultAddr) # dev: already registered
    vaultInfo: ls.VaultTokenInfo = self._registerVaultTokenLocally(_asset, _vaultAddr, _reserveId)
    self._registerVaultTokenGlobally(_asset, _vaultAddr, vaultInfo.decimals, addys._getLedgerAddr(), addys._getLegoBookAddr())
    return vaultInfo


@internal
def _registerVaultTokenLocally(_asset: address, _vaultAddr: address, _reserveId: uint256) -> ls.VaultTokenInfo:
    assert extcall IERC20(_asset).approve(EXTRAFI_POOL, max_value(uint256), default_return_value=True) # dev: max approval failed
    assert extcall IERC20(_vaultAddr).approve(EXTRAFI_POOL, max_value(uint256), default_return_value=True) # dev: max approval failed
    self.vaultTokenToReserveId[_vaultAddr] = _reserveId
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
    assert extcall IERC20(_asset).approve(EXTRAFI_POOL, 0, default_return_value=True) # dev: max approval failed
    assert extcall IERC20(_vaultAddr).approve(EXTRAFI_POOL, 0, default_return_value=True) # dev: max approval failed
    yld._removeAssetOpportunity(_asset, _vaultAddr)
    self.vaultTokenToReserveId[_vaultAddr] = 0


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
    assert self._isAllowedToPerformAction(msg.sender) # dev: no perms
    assert not yld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = yld._getMiniAddys(_miniAddys)
    vaultInfo: ls.VaultTokenInfo = yld.vaultToAsset[_vaultAddr]

    # verify asset and vault token are registered
    assert _asset != empty(address) # dev: invalid asset
    assert vaultInfo.underlyingAsset == _asset # dev: asset mismatch
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

    # add price snapshot
    pricePerShare: uint256 = self._getPricePerShare(_vaultAddr, vaultInfo.decimals)
    yld._addPriceSnapshot(_vaultAddr, pricePerShare, vaultInfo.decimals)

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
    assert self._isAllowedToPerformAction(msg.sender) # dev: no perms
    assert not yld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = yld._getMiniAddys(_miniAddys)
    vaultInfo: ls.VaultTokenInfo = yld.vaultToAsset[_vaultToken]

    # verify asset and vault token are registered
    assert vaultInfo.underlyingAsset != empty(address) # dev: invalid asset
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

    usdValue: uint256 = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(vaultInfo.underlyingAsset, assetAmountReceived, miniAddys.missionControl, miniAddys.legoBook)
    log ExtraFiWithdrawal(
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


#########
# Other #
#########


@view
@external
def getAccessForLego(_user: address, _action: ws.ActionType) -> (address, String[64], uint256):
    return empty(address), empty(String[64]), 0


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


@view
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