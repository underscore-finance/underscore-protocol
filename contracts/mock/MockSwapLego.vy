# @version 0.4.3

implements: Lego

exports: addys.__interface__
exports: dld.__interface__

initializes: addys
initializes: dld[addys := addys]

from interfaces import LegoPartner as Lego
from interfaces import WalletStructs as ws

import contracts.modules.Addys as addys
import contracts.modules.DexLegoData as dld

from ethereum.ercs import IERC20
from ethereum.ercs import IERC20Detailed

interface MockToken:
    def mint(_to: address, _value: uint256): nonpayable
    def burn(_value: uint256) -> bool: nonpayable

struct BestPool:
    pool: address
    fee: uint256
    liquidity: uint256
    numCoins: uint256

# mock price config - stores price per token in USD with 18 decimals (e.g., 1 * 10^18 for $1)
price: public(HashMap[address, uint256])

EIGHTEEN_DECIMALS: constant(uint256) = 10 ** 18
MAX_TOKEN_PATH: constant(uint256) = 5
MAX_PROOFS: constant(uint256) = 25


@deploy
def __init__(_undyHq: address):
    # modules
    addys.__init__(_undyHq)
    dld.__init__(False)


@view
@external
def hasCapability(_action: ws.ActionType) -> bool:
    return _action == ws.ActionType.SWAP


@view
@external
def getRegistries() -> DynArray[address, 10]:
    return []


@view
@external
def isYieldLego() -> bool:
    return False


@view
@external
def isDexLego() -> bool:
    return True


# MOCK config


@external
def setPrice(_asset: address, _price: uint256):
    self.price[_asset] = _price


@view
@external
def getPrice(_asset: address, _decimals: uint256) -> uint256:
    return self.price[_asset]


###################
# Swap / Exchange #
###################


@external
def swapTokens(
    _amountIn: uint256,
    _minAmountOut: uint256,
    _tokenPath: DynArray[address, MAX_TOKEN_PATH],
    _poolPath: DynArray[address, MAX_TOKEN_PATH - 1],
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256, uint256):
    assert not dld.isPaused # dev: paused

    assert len(_tokenPath) >= 2 # dev: invalid token path
    tokenIn: address = _tokenPath[0]
    tokenOut: address = _tokenPath[len(_tokenPath) - 1]
    assert tokenIn != tokenOut # dev: same token

    # get actual amount to swap
    amount: uint256 = min(_amountIn, staticcall IERC20(tokenIn).balanceOf(msg.sender))
    assert amount != 0 # dev: nothing to transfer
    assert extcall IERC20(tokenIn).transferFrom(msg.sender, self, amount, default_return_value=True) # dev: transfer failed

    # check prices are set
    assert self.price[tokenIn] != 0 and self.price[tokenOut] != 0 # dev: price not set

    # Step 1: Convert tokenIn amount to USD value
    usdValue: uint256 = self._getUsdValue(tokenIn, amount)

    # Step 2: Convert USD value to tokenOut amount
    amountOut: uint256 = self._getAssetAmount(tokenOut, usdValue)
    assert amountOut >= _minAmountOut # dev: slippage

    # burn input token and mint output token
    extcall MockToken(tokenIn).burn(amount)
    extcall MockToken(tokenOut).mint(_recipient, amountOut)

    # return amounts with USD value
    return amount, amountOut, usdValue


@view
@internal
def _getAssetAmount(_asset: address, _usdValue: uint256) -> uint256:
    if _usdValue == 0 or _asset == empty(address):
        return 0
    price: uint256 = self.price[_asset]
    if price == 0:
        return 0
    decimals: uint256 = convert(staticcall IERC20Detailed(_asset).decimals(), uint256)
    return _usdValue * (10 ** decimals) // price


@view
@internal
def _getUsdValue(_asset: address, _amount: uint256) -> uint256:
    if _amount == 0 or _asset == empty(address):
        return 0
    price: uint256 = self.price[_asset]
    if price == 0:
        return 0
    decimals: uint256 = convert(staticcall IERC20Detailed(_asset).decimals(), uint256)
    return price * _amount // (10 ** decimals)


#####################################
# Stubbed Functions (not used)     #
#####################################


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
def claimIncentives(_user: address, _rewardToken: address, _rewardAmount: uint256, _proofs: DynArray[bytes32, MAX_PROOFS], _miniAddys: ws.MiniAddys = empty(ws.MiniAddys)) -> (uint256, uint256):
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


@view
@external
def getLpToken(_pool: address) -> address:
    return empty(address)


@view
@external
def getPoolForLpToken(_lpToken: address) -> address:
    return empty(address)


@view
@external
def getCoreRouterPool() -> address:
    return empty(address)


@view
@external
def getDeepestLiqPool(_tokenA: address, _tokenB: address) -> BestPool:
    return empty(BestPool)


@view
@external
def getBestSwapAmountOut(_tokenIn: address, _tokenOut: address, _amountIn: uint256) -> (address, uint256):
    return empty(address), 0


@view
@external
def getSwapAmountOut(
    _pool: address,
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256,
) -> uint256:
    return 0


@view
@external
def getBestSwapAmountIn(_tokenIn: address, _tokenOut: address, _amountOut: uint256) -> (address, uint256):
    return empty(address), 0


@view
@external
def getSwapAmountIn(
    _pool: address,
    _tokenIn: address,
    _tokenOut: address,
    _amountOut: uint256,
) -> uint256:
    return 0


@view
@external
def getAddLiqAmountsIn(
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _availAmountA: uint256,
    _availAmountB: uint256,
) -> (uint256, uint256, uint256):
    return 0, 0, 0


@view
@external
def getRemoveLiqAmountsOut(
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _lpAmount: uint256,
) -> (uint256, uint256):
    return 0, 0


@view
@external
def getPriceUnsafe(_pool: address, _targetToken: address, _appraiser: address = empty(address)) -> uint256:
    return 0


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


@view
@external
def getAccessForLego(_user: address, _action: ws.ActionType) -> (address, String[64], uint256):
    return empty(address), empty(String[64]), 0
