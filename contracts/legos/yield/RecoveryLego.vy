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

from ethereum.ercs import IERC20

interface UndyHq:
    def governance() -> address: view

interface Ledger:
    def isUserWallet(_user: address) -> bool: view

interface UserWallet:
    def walletConfig() -> address: view

interface UserWalletConfig:
    def indexOfManager(_addr: address) -> uint256: view

struct Recovery:
    user: address
    asset: address
    recipient: address

event RecoveryDeposit:
    user: indexed(address)
    asset: indexed(address)
    amount: uint256

event FundsMigrated:
    user: indexed(address)
    asset: indexed(address)
    recipient: indexed(address)
    amount: uint256

MAX_TOKEN_PATH: constant(uint256) = 5
MAX_PROOFS: constant(uint256) = 25
MAX_RECOVERIES: constant(uint256) = 30

AGENT_WRAPPER: constant(address) = 0x8ee401f1E0F4CC0Ed57318AB6dAab1F1Fb59f65f

# user -> asset -> amount
userAssets: public(HashMap[address, HashMap[address, uint256]])


@deploy
def __init__(_undyHq: address):
    assert empty(address) not in [_undyHq] # dev: invalid addrs
    addys.__init__(_undyHq)
    yld.__init__(False)


@view
@internal
def _canMigrate(_caller: address) -> bool:
    return _caller == staticcall UndyHq(addys._getUndyHq()).governance()


@view
@internal
def _isUserWallet(_wallet: address) -> bool:
    ledger: address = addys._getLedgerAddr()
    if ledger == empty(address):
        return False
    return staticcall Ledger(ledger).isUserWallet(_wallet)


#########
# Views #
#########


@view
@external
def hasCapability(_action: ws.ActionType) -> bool:
    return _action == ws.ActionType.EARN_DEPOSIT


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


###################
# Underlying Data #
###################


@view
@external
def getUnderlyingAsset(_vaultToken: address) -> address:
    return empty(address)


@view
@external
def getUnderlyingBalances(_vaultToken: address, _vaultTokenBalance: uint256) -> (uint256, uint256):
    return 0, 0


@view
@external
def getUnderlyingAmount(_vaultToken: address, _vaultTokenAmount: uint256) -> uint256:
    return 0


@view
@external
def getUnderlyingAmountSafe(_vaultToken: address, _vaultTokenBalance: uint256) -> uint256:
    return 0


@view
@external
def getUnderlyingData(_vaultToken: address, _vaultTokenAmount: uint256, _appraiser: address = empty(address)) -> (address, uint256, uint256):
    return empty(address), 0, 0


@view
@external
def getUsdValueOfVaultToken(_vaultToken: address, _vaultTokenAmount: uint256, _appraiser: address = empty(address)) -> uint256:
    return 0


###############
# Other Utils #
###############


@view
@external
def isRebasing() -> bool:
    return False


@view
@external
def getPricePerShare(_vaultToken: address, _decimals: uint256 = 0) -> uint256:
    return 0


@view
@external
def getVaultTokenAmount(_asset: address, _assetAmount: uint256, _vaultToken: address) -> uint256:
    return 0


@view
@external
def canRegisterVaultToken(_asset: address, _vaultToken: address) -> bool:
    return False


@view
@external
def totalAssets(_vaultToken: address) -> uint256:
    return 0


@view
@external
def totalBorrows(_vaultToken: address) -> uint256:
    return 0


@view
@external
def getUtilizationRatio(_vaultToken: address) -> uint256:
    return 0


@view
@external
def getAvailLiquidity(_vaultToken: address) -> uint256:
    return 0


@view
@external
def isEligibleForYieldBonus(_asset: address) -> bool:
    return False


@view
@external
def getWithdrawalFees(_vaultToken: address, _vaultTokenAmount: uint256) -> uint256:
    return 0


#################
# Yield Actions #
#################


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
    assert self._isUserWallet(msg.sender) # dev: not a user wallet
    assert _asset != empty(address) # dev: invalid asset

    depositAmount: uint256 = min(_amount, staticcall IERC20(_asset).balanceOf(msg.sender))
    assert depositAmount != 0 # dev: nothing to transfer
    assert extcall IERC20(_asset).transferFrom(msg.sender, self, depositAmount, default_return_value=True) # dev: transfer failed

    self.userAssets[msg.sender][_asset] += depositAmount

    log RecoveryDeposit(user=msg.sender, asset=_asset, amount=depositAmount)
    return depositAmount, empty(address), 0, 1


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
def migrateFunds(_recoveries: DynArray[Recovery, MAX_RECOVERIES]) -> bool:
    assert self._canMigrate(msg.sender) # dev: no perms

    for r: Recovery in _recoveries:
        if empty(address) in [r.asset, r.recipient]:
            continue

        assert self._isUserWallet(r.recipient) # dev: not a user wallet
        config: address = staticcall UserWallet(r.recipient).walletConfig()
        assert staticcall UserWalletConfig(config).indexOfManager(AGENT_WRAPPER) != 0 # dev: recipient wallet not managed by UndyHq

        recordedAmount: uint256 = self.userAssets[r.user][r.asset]
        if recordedAmount == 0:
            continue

        amount: uint256 = min(recordedAmount, staticcall IERC20(r.asset).balanceOf(self))
        if amount == 0:
            continue

        self.userAssets[r.user][r.asset] = recordedAmount - amount
        assert extcall IERC20(r.asset).transfer(r.recipient, amount, default_return_value=True) # dev: transfer failed
        log FundsMigrated(user=r.user, asset=r.asset, recipient=r.recipient, amount=amount)

    return True


@external
def addPriceSnapshot(_vaultToken: address) -> bool:
    return False


#########
# Other #
#########


@view
@external
def getAccessForLego(_user: address, _action: ws.ActionType) -> (address, String[64], uint256):
    return empty(address), empty(String[64]), 0


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
def claimRewards(
    _user: address,
    _rewardToken: address,
    _rewardAmount: uint256,
    _extraData: bytes32,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    return 0, 0


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
def removeCollateral(
    _asset: address,
    _amount: uint256,
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
