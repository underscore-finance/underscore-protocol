#     __   __ ___ _______ ___     ______       ___     _______ _______ _______ 
#    |  | |  |   |       |   |   |      |     |   |   |       |       |       |
#    |  |_|  |   |    ___|   |   |  _    |    |   |   |    ___|    ___|   _   |
#    |       |   |   |___|   |   | | |   |    |   |   |   |___|   | __|  | |  |
#    |_     _|   |    ___|   |___| |_|   |    |   |___|    ___|   ||  |  |_|  |
#      |   | |   |   |___|       |       |    |       |   |___|   |_| |       |
#      |___| |___|_______|_______|______|     |_______|_______|_______|_______|
#                                                                       
#     ╔═════════════════════════════════════════╗
#     ║  ** Moonwell Lego **                    ║
#     ║  Integration with Moonwell Protocol.    ║
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

interface CompoundV2:
    def redeem(_ctokenAmount: uint256) -> uint256: nonpayable
    def mint(_amount: uint256) -> uint256: nonpayable
    def exchangeRateStored() -> uint256: view
    def totalBorrows() -> uint256: view
    def totalSupply() -> uint256: view
    def underlying() -> address: view

interface Ledger:
    def setVaultToken(_vaultToken: address, _legoId: uint256, _underlyingAsset: address, _decimals: uint256, _isRebasing: bool): nonpayable
    def isRegisteredVaultToken(_vaultToken: address) -> bool: view
    def isUserWallet(_user: address) -> bool: view

interface MoonwellComptroller:
    def getAllMarkets() -> DynArray[address, MAX_MARKETS]: view
    def claimReward(_holder: address): nonpayable
    def rewardDistributor() -> address: view

interface Appraiser:
    def getUsdValue(_asset: address, _amount: uint256, _missionControl: address = empty(address), _legoBook: address = empty(address), _ledger: address = empty(address)) -> uint256: view
    def updatePriceAndGetUsdValue(_asset: address, _amount: uint256, _missionControl: address = empty(address), _legoBook: address = empty(address)) -> uint256: nonpayable

interface Registry:
    def getRegId(_addr: address) -> uint256: view
    def isValidAddr(_addr: address) -> bool: view

interface MoonwellRewardDistributor:
    def getOutstandingRewardsForUser(_user: address) -> DynArray[RewardWithMToken, MAX_MARKETS]: view

interface VaultRegistry:
    def isEarnVault(_vaultAddr: address) -> bool: view

interface WethContract:
    def deposit(): payable

struct RewardWithMToken:
    mToken: address
    rewards: DynArray[RewardInfo, MAX_ASSETS]

struct RewardInfo:
    emissionToken: address
    totalAmount: uint256
    supplySide: uint256
    borrowSide: uint256

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
RIPE_REGISTRY: public(immutable(address))

MAX_MARKETS: constant(uint256) = 50
MAX_ASSETS: constant(uint256) = 25
MAX_TOKEN_PATH: constant(uint256) = 5
MAX_PROOFS: constant(uint256) = 25


@deploy
def __init__(
    _undyHq: address,
    _moonwellComptroller: address,
    _weth: address,
    _ripeRegistry: address,
):
    addys.__init__(_undyHq)
    yld.__init__(False)

    assert empty(address) not in [_moonwellComptroller, _weth, _ripeRegistry] # dev: invalid addrs
    MOONWELL_COMPTROLLER = _moonwellComptroller
    WETH = _weth
    RIPE_REGISTRY = _ripeRegistry


@payable
@external
def __default__():
    pass


@view
@external
def hasCapability(_action: ws.ActionType) -> bool:
    return _action in (
        ws.ActionType.EARN_DEPOSIT | 
        ws.ActionType.EARN_WITHDRAW |
        ws.ActionType.REWARDS
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
    return _vaultTokenAmount * staticcall CompoundV2(_vaultToken).exchangeRateStored() // (10 ** 18)


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
    return (10 ** _decimals) * staticcall CompoundV2(_vaultToken).exchangeRateStored() // (10 ** 18)


# vault token amount


@view
@external
def getVaultTokenAmount(_asset: address, _assetAmount: uint256, _vaultToken: address) -> uint256:
    return _assetAmount * (10 ** 18) // staticcall CompoundV2(_vaultToken).exchangeRateStored()


# extras


@view
@external
def isEligibleForYieldBonus(_asset: address) -> bool:
    return False


@view
@external
def totalAssets(_vaultToken: address) -> uint256:
    return staticcall CompoundV2(_vaultToken).totalSupply() * staticcall CompoundV2(_vaultToken).exchangeRateStored() // (10 ** 18)


@view
@external
def totalBorrows(_vaultToken: address) -> uint256:
    return staticcall CompoundV2(_vaultToken).totalBorrows()


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
    if staticcall CompoundV2(_vaultToken).underlying() != _asset:
        return False
    compMarkets: DynArray[address, MAX_MARKETS] = staticcall MoonwellComptroller(MOONWELL_COMPTROLLER).getAllMarkets()
    return _vaultToken in compMarkets


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
    assert self._isAllowedToPerformAction(msg.sender) # dev: no perms
    assert not yld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = yld._getMiniAddys(_miniAddys)
    vaultInfo: ls.VaultTokenInfo = self._getVaultInfoOnDeposit(_asset, _vaultAddr, miniAddys.ledger, miniAddys.legoBook)

    # pre balances
    preLegoVaultBalance: uint256 = staticcall IERC20(_vaultAddr).balanceOf(self)
    preLegoBalance: uint256 = staticcall IERC20(_asset).balanceOf(self)

    # transfer deposit asset to this contract
    depositAmount: uint256 = min(_amount, staticcall IERC20(_asset).balanceOf(msg.sender))
    assert depositAmount != 0 # dev: nothing to transfer
    assert extcall IERC20(_asset).transferFrom(msg.sender, self, depositAmount, default_return_value=True) # dev: transfer failed

    # deposit assets into lego partner
    assert extcall CompoundV2(_vaultAddr).mint(depositAmount) == 0 # dev: could not deposit into moonwell

    # validate received vault tokens, transfer back to user
    vaultTokenAmountReceived: uint256 = staticcall IERC20(_vaultAddr).balanceOf(self) - preLegoVaultBalance
    assert vaultTokenAmountReceived != 0 # dev: no vault tokens received
    assert extcall IERC20(_vaultAddr).transfer(_recipient, vaultTokenAmountReceived, default_return_value=True) # dev: transfer failed

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

    # pre balances
    preLegoBalance: uint256 = staticcall IERC20(vaultInfo.underlyingAsset).balanceOf(self)
    preLegoVaultBalance: uint256 = staticcall IERC20(_vaultToken).balanceOf(self)

    # transfer vaults tokens to this contract
    vaultTokenAmount: uint256 = min(_amount, staticcall IERC20(_vaultToken).balanceOf(msg.sender))
    assert vaultTokenAmount != 0 # dev: nothing to transfer
    assert extcall IERC20(_vaultToken).transferFrom(msg.sender, self, vaultTokenAmount, default_return_value=True) # dev: transfer failed

    # withdraw assets from lego partner
    assert extcall CompoundV2(_vaultToken).redeem(max_value(uint256)) == 0 # dev: could not withdraw from moonwell

    # when withdrawing weth, they give eth
    if vaultInfo.underlyingAsset == WETH:
        extcall WethContract(WETH).deposit(value=self.balance)

    # validate received asset , transfer back to user
    assetAmountReceived: uint256 = staticcall IERC20(vaultInfo.underlyingAsset).balanceOf(self) - preLegoBalance
    assert assetAmountReceived != 0 # dev: no asset amount received
    assert extcall IERC20(vaultInfo.underlyingAsset).transfer(_recipient, assetAmountReceived, default_return_value=True) # dev: transfer failed

    # refund if full withdrawal didn't happen
    currentLegoVaultBalance: uint256 = staticcall IERC20(_vaultToken).balanceOf(self)
    refundVaultTokenAmount: uint256 = 0
    if currentLegoVaultBalance > preLegoVaultBalance:
        refundVaultTokenAmount = currentLegoVaultBalance - preLegoVaultBalance
        assert extcall IERC20(_vaultToken).transfer(msg.sender, refundVaultTokenAmount, default_return_value=True) # dev: transfer failed
        vaultTokenAmount -= refundVaultTokenAmount

    usdValue: uint256 = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(vaultInfo.underlyingAsset, assetAmountReceived, miniAddys.missionControl, miniAddys.legoBook)
    log MoonwellWithdrawal(
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
        asset: address = staticcall CompoundV2(_vaultAddr).underlying()
        assert self._canRegisterVaultToken(asset, _vaultAddr) # dev: cannot register vault token
        vaultInfo = self._registerVaultTokenLocally(asset, _vaultAddr)
        self._registerVaultTokenGlobally(asset, _vaultAddr, vaultInfo.decimals, _ledger, _legoBook)
    return vaultInfo


#################
# Claim Rewards #
#################


@external
def claimIncentives(
    _user: address,
    _rewardToken: address,
    _rewardAmount: uint256,
    _proofs: DynArray[bytes32, MAX_PROOFS],
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    assert self._isAllowedToPerformAction(msg.sender) # dev: no perms
    return self._claimIncentives(_user, _rewardToken, _rewardAmount, _miniAddys)


@external
def claimRewards(
    _user: address,
    _rewardToken: address,
    _rewardAmount: uint256,
    _extraData: bytes32,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    assert self._isAllowedToPerformAction(msg.sender) # dev: no perms
    return self._claimIncentives(_user, _rewardToken, _rewardAmount, _miniAddys)


@internal
def _claimIncentives(
    _user: address,
    _rewardToken: address,
    _rewardAmount: uint256,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    assert not yld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = yld._getMiniAddys(_miniAddys)
    preBalance: uint256 = staticcall IERC20(_rewardToken).balanceOf(_user)

    # claim rewards
    extcall MoonwellComptroller(MOONWELL_COMPTROLLER).claimReward(_user)
    rewardAmount: uint256 = staticcall IERC20(_rewardToken).balanceOf(_user) - preBalance
    assert rewardAmount != 0 # dev: no rewards received

    usdValue: uint256 = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(_rewardToken, rewardAmount, miniAddys.missionControl, miniAddys.legoBook)
    return rewardAmount, usdValue


# has claimable rewards


@view
@external
def hasClaimableRewards(_user: address) -> bool:
    rewardDistributor: address = staticcall MoonwellComptroller(MOONWELL_COMPTROLLER).rewardDistributor()
    rewardsWithMToken: DynArray[RewardWithMToken, MAX_MARKETS] = staticcall MoonwellRewardDistributor(rewardDistributor).getOutstandingRewardsForUser(_user)
    for i: uint256 in range(len(rewardsWithMToken), bound=MAX_MARKETS):
        rewardsInfo: DynArray[RewardInfo, MAX_ASSETS] = rewardsWithMToken[i].rewards
        for j: uint256 in range(len(rewardsInfo), bound=MAX_ASSETS):
            if rewardsInfo[j].totalAmount > 0:
                return True
    return False


#########
# Other #
#########


@view
@external
def getAccessForLego(_user: address, _action: ws.ActionType) -> (address, String[64], uint256):
    return empty(address), empty(String[64]), 0


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