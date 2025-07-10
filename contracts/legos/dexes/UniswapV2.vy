# @version 0.4.3

implements: Lego
implements: DexLego

exports: addys.__interface__
exports: dld.__interface__

initializes: addys
initializes: dld[addys := addys]

from interfaces import LegoPartner as Lego
from interfaces import DexLego as DexLego
from interfaces import Wallet as wi

import contracts.modules.Addys as addys
import contracts.modules.DexLegoData as dld

from ethereum.ercs import IERC20
from ethereum.ercs import IERC20Detailed

interface IUniswapV2Pair:
    def swap(_amount0Out: uint256, _amount1Out: uint256, _recipient: address, _data: Bytes[256]): nonpayable
    def getReserves() -> (uint112, uint112, uint32): view
    def token0() -> address: view
    def token1() -> address: view

interface Appraiser:
    def getNormalAssetPrice(_asset: address, _missionControl: address = empty(address), _legoBook: address = empty(address), _ledger: address = empty(address)) -> uint256: view
    def updatePriceAndGetUsdValue(_asset: address, _amount: uint256, _missionControl: address = empty(address), _legoBook: address = empty(address)) -> uint256: nonpayable

interface UniV2Router:
    def addLiquidity(_tokenA: address, _tokenB: address, _amountADesired: uint256, _amountBDesired: uint256, _amountAMin: uint256, _amountBMin: uint256, _recipient: address, _deadline: uint256) -> (uint256, uint256, uint256): nonpayable
    def removeLiquidity(_tokenA: address, _tokenB: address, _lpAmount: uint256, _amountAMin: uint256, _amountBMin: uint256, _recipient: address, _deadline: uint256) -> (uint256, uint256): nonpayable

interface UniV2Factory:
    def getPair(_tokenA: address, _tokenB: address) -> address: view

struct BestPool:
    pool: address
    fee: uint256
    liquidity: uint256
    numCoins: uint256

struct Route:
    from_: address
    to: address 
    stable: bool
    factory: address

event UniswapV2Swap:
    sender: indexed(address)
    tokenIn: indexed(address)
    tokenOut: indexed(address)
    amountIn: uint256
    amountOut: uint256
    usdValue: uint256
    numTokens: uint256
    recipient: address

event UniswapV2LiquidityAdded:
    sender: indexed(address)
    tokenA: indexed(address)
    tokenB: indexed(address)
    amountA: uint256
    amountB: uint256
    lpAmountReceived: uint256
    usdValue: uint256
    recipient: address

event UniswapV2LiquidityRemoved:
    sender: address
    pool: indexed(address)
    tokenA: indexed(address)
    tokenB: indexed(address)
    amountA: uint256
    amountB: uint256
    lpToken: address
    lpAmountBurned: uint256
    usdValue: uint256
    recipient: address

# uniswap v2
UNISWAP_V2_FACTORY: public(immutable(address))
UNISWAP_V2_ROUTER: public(immutable(address))
coreRouterPool: public(address)

EIGHTEEN_DECIMALS: constant(uint256) = 10 ** 18
MAX_TOKEN_PATH: constant(uint256) = 5


@deploy
def __init__(
    _undyHq: address,
    _uniswapV2Factory: address,
    _uniswapV2Router: address,
    _coreRouterPool: address,
):
    addys.__init__(_undyHq)
    dld.__init__(False)

    assert empty(address) not in [_uniswapV2Factory, _uniswapV2Router, _coreRouterPool] # dev: invalid addrs
    UNISWAP_V2_FACTORY = _uniswapV2Factory
    UNISWAP_V2_ROUTER = _uniswapV2Router
    self.coreRouterPool = _coreRouterPool


@view
@external
def hasCapability(_action: wi.ActionType) -> bool:
    return _action in (
        wi.ActionType.SWAP |
        wi.ActionType.ADD_LIQ | 
        wi.ActionType.REMOVE_LIQ
    )


@view
@external
def getRegistries() -> DynArray[address, 10]:
    return [UNISWAP_V2_FACTORY, UNISWAP_V2_ROUTER]


@view
@external
def isYieldLego() -> bool:
    return False


@view
@external
def isDexLego() -> bool:
    return True


#########
# Swaps #
#########


@external
def swapTokens(
    _amountIn: uint256,
    _minAmountOut: uint256,
    _tokenPath: DynArray[address, MAX_TOKEN_PATH],
    _poolPath: DynArray[address, MAX_TOKEN_PATH - 1],
    _recipient: address,
    _miniAddys: Lego.MiniAddys = empty(Lego.MiniAddys),
) -> (uint256, uint256, uint256):
    assert not dld.isPaused # dev: paused
    miniAddys: Lego.MiniAddys = dld._getMiniAddys(_miniAddys)

    # validate inputs
    numTokens: uint256 = len(_tokenPath)
    numPools: uint256 = len(_poolPath)
    assert numTokens >= 2 # dev: invalid path
    assert numPools == numTokens - 1 # dev: invalid path

    # get first token and last token
    tokenIn: address = _tokenPath[0]
    tokenOut: address = _tokenPath[numTokens - 1]

    # pre balances
    preLegoBalance: uint256 = staticcall IERC20(tokenIn).balanceOf(self)

    # transfer deposit asset to this contract
    amountIn: uint256 = min(_amountIn, staticcall IERC20(tokenIn).balanceOf(msg.sender))
    assert amountIn != 0 # dev: nothing to transfer
    assert extcall IERC20(tokenIn).transferFrom(msg.sender, self, amountIn, default_return_value=True) # dev: transfer failed

    # transfer initial amount to first pool
    assert extcall IERC20(tokenIn).transfer(_poolPath[0], amountIn, default_return_value=True) # dev: transfer failed

    # iterate through swap routes
    tempAmountIn: uint256 = amountIn
    uniswapV2Factory: address = UNISWAP_V2_FACTORY
    for i: uint256 in range(numTokens - 1, bound=MAX_TOKEN_PATH):
        tempTokenIn: address = _tokenPath[i]
        tempTokenOut: address = _tokenPath[i + 1]
        tempPool: address = _poolPath[i]

        # transfer to next pool (or to recipient if last swap)
        recipient: address = _recipient
        if i < numTokens - 2:
            recipient = _poolPath[i + 1]

        # swap
        tempAmountIn = self._swapTokensInPool(tempPool, tempTokenIn, tempTokenOut, tempAmountIn, recipient, uniswapV2Factory)

    # final amount
    amountOut: uint256 = tempAmountIn
    assert amountOut >= _minAmountOut # dev: min amount out not met

    # refund if full swap didn't get through
    currentLegoBalance: uint256 = staticcall IERC20(tokenIn).balanceOf(self)
    refundAssetAmount: uint256 = 0
    if currentLegoBalance > preLegoBalance:
        refundAssetAmount = currentLegoBalance - preLegoBalance
        assert extcall IERC20(tokenIn).transfer(msg.sender, refundAssetAmount, default_return_value=True) # dev: transfer failed
        amountIn -= refundAssetAmount

    # get usd values
    usdValue: uint256 = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(tokenIn, amountIn, miniAddys.missionControl, miniAddys.legoBook)
    if usdValue == 0:
        usdValue = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(tokenOut, amountOut, miniAddys.missionControl, miniAddys.legoBook)

    log UniswapV2Swap(
        sender = msg.sender,
        tokenIn = tokenIn,
        tokenOut = tokenOut,
        amountIn = amountIn,
        amountOut = amountOut,
        usdValue = usdValue,
        numTokens = numTokens,
        recipient = _recipient,
    )
    return amountIn, amountOut, usdValue


# swap in pool


@internal
def _swapTokensInPool(
    _pool: address,
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256,
    _recipient: address,
    _uniswapV2Factory: address,
) -> uint256:
    tokens: address[2] = [staticcall IUniswapV2Pair(_pool).token0(), staticcall IUniswapV2Pair(_pool).token1()]
    assert _tokenIn in tokens # dev: invalid tokenIn
    assert _tokenOut in tokens # dev: invalid tokenOut
    assert _tokenIn != _tokenOut # dev: invalid tokens

    # verify actual uniswap v2 pool
    assert staticcall UniV2Factory(_uniswapV2Factory).getPair(_tokenIn, _tokenOut) == _pool # dev: invalid pool

    zeroForOne: bool = _tokenIn == tokens[0]
    amountOut: uint256 = self._getAmountOut(_pool, zeroForOne, _amountIn)
    assert amountOut != 0 # dev: no tokens swapped

    # put in correct order
    amount0Out: uint256 = amountOut
    amount1Out: uint256 = 0
    if zeroForOne:
        amount0Out = 0
        amount1Out = amountOut

    # perform swap
    extcall IUniswapV2Pair(_pool).swap(amount0Out, amount1Out, _recipient, b"")
    return amountOut


#############
# Liquidity #
#############


# add liquidity


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
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: Lego.MiniAddys = empty(Lego.MiniAddys),
) -> (address, uint256, uint256, uint256, uint256):
    assert not dld.isPaused # dev: paused
    miniAddys: Lego.MiniAddys = dld._getMiniAddys(_miniAddys)

    # validate tokens
    tokens: address[2] = [staticcall IUniswapV2Pair(_pool).token0(), staticcall IUniswapV2Pair(_pool).token1()]
    assert _tokenA in tokens # dev: invalid tokenA
    assert _tokenB in tokens # dev: invalid tokenB
    assert _tokenA != _tokenB # dev: invalid tokens

    # pre balances
    preLegoBalanceA: uint256 = staticcall IERC20(_tokenA).balanceOf(self)
    preLegoBalanceB: uint256 = staticcall IERC20(_tokenB).balanceOf(self)

    # token a
    liqAmountA: uint256 = min(_amountA, staticcall IERC20(_tokenA).balanceOf(msg.sender))
    assert liqAmountA != 0 # dev: nothing to transfer
    assert extcall IERC20(_tokenA).transferFrom(msg.sender, self, liqAmountA, default_return_value=True) # dev: transfer failed

    # token b
    liqAmountB: uint256 = min(_amountB, staticcall IERC20(_tokenB).balanceOf(msg.sender))
    assert liqAmountB != 0 # dev: nothing to transfer
    assert extcall IERC20(_tokenB).transferFrom(msg.sender, self, liqAmountB, default_return_value=True) # dev: transfer failed

    # approvals
    router: address = UNISWAP_V2_ROUTER
    assert extcall IERC20(_tokenA).approve(router, liqAmountA, default_return_value=True) # dev: approval failed
    assert extcall IERC20(_tokenB).approve(router, liqAmountB, default_return_value=True) # dev: approval failed

    # add liquidity
    lpAmountReceived: uint256 = 0
    liqAmountA, liqAmountB, lpAmountReceived = extcall UniV2Router(router).addLiquidity(
        _tokenA,
        _tokenB,
        liqAmountA,
        liqAmountB,
        _minAmountA,
        _minAmountB,
        _recipient,
        block.timestamp,
    )
    assert lpAmountReceived != 0 # dev: no liquidity added

    # reset approvals
    assert extcall IERC20(_tokenA).approve(router, 0, default_return_value=True) # dev: approval failed
    assert extcall IERC20(_tokenB).approve(router, 0, default_return_value=True) # dev: approval failed

    # refund if full liquidity was not added
    currentLegoBalanceA: uint256 = staticcall IERC20(_tokenA).balanceOf(self)
    refundAssetAmountA: uint256 = 0
    if currentLegoBalanceA > preLegoBalanceA:
        refundAssetAmountA = currentLegoBalanceA - preLegoBalanceA
        assert extcall IERC20(_tokenA).transfer(msg.sender, refundAssetAmountA, default_return_value=True) # dev: transfer failed

    currentLegoBalanceB: uint256 = staticcall IERC20(_tokenB).balanceOf(self)
    refundAssetAmountB: uint256 = 0
    if currentLegoBalanceB > preLegoBalanceB:
        refundAssetAmountB = currentLegoBalanceB - preLegoBalanceB
        assert extcall IERC20(_tokenB).transfer(msg.sender, refundAssetAmountB, default_return_value=True) # dev: transfer failed

    usdValue: uint256 = self._getUsdValue(_tokenA, liqAmountA, _tokenB, liqAmountB, miniAddys)
    log UniswapV2LiquidityAdded(
        sender = msg.sender,
        tokenA = _tokenA,
        tokenB = _tokenB,
        amountA = liqAmountA,
        amountB = liqAmountB,
        lpAmountReceived = lpAmountReceived,
        usdValue = usdValue,
        recipient = _recipient,
    )
    return _pool, lpAmountReceived, liqAmountA, liqAmountB, usdValue


# remove liquidity


@external
def removeLiquidity(
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _lpToken: address,
    _lpAmount: uint256,
    _minAmountA: uint256,
    _minAmountB: uint256,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: Lego.MiniAddys = empty(Lego.MiniAddys),
) -> (uint256, uint256, uint256, uint256):
    assert not dld.isPaused # dev: paused
    miniAddys: Lego.MiniAddys = dld._getMiniAddys(_miniAddys)

    # validate tokens
    tokens: address[2] = [staticcall IUniswapV2Pair(_pool).token0(), staticcall IUniswapV2Pair(_pool).token1()]
    assert _tokenA in tokens # dev: invalid tokenA
    assert _tokenB in tokens # dev: invalid tokenB
    assert _tokenA != _tokenB # dev: invalid tokens

    # pre balance
    preLegoBalance: uint256 = staticcall IERC20(_lpToken).balanceOf(self)

    # lp token
    lpAmount: uint256 = min(_lpAmount, staticcall IERC20(_lpToken).balanceOf(msg.sender))
    assert lpAmount != 0 # dev: nothing to transfer
    assert extcall IERC20(_lpToken).transferFrom(msg.sender, self, lpAmount, default_return_value=True) # dev: transfer failed

    # approvals
    router: address = UNISWAP_V2_ROUTER
    assert extcall IERC20(_lpToken).approve(router, lpAmount, default_return_value=True) # dev: approval failed

    # remove liquidity
    amountA: uint256 = 0
    amountB: uint256 = 0
    amountA, amountB = extcall UniV2Router(router).removeLiquidity(
        _tokenA,
        _tokenB,
        lpAmount,
        _minAmountA,
        _minAmountB,
        _recipient,
        block.timestamp,
    )
    assert amountA != 0 # dev: no amountA removed
    assert amountB != 0 # dev: no amountB removed

    # reset approvals
    assert extcall IERC20(_lpToken).approve(router, 0, default_return_value=True) # dev: approval failed

    # refund if full liquidity was not removed
    currentLegoBalance: uint256 = staticcall IERC20(_lpToken).balanceOf(self)
    refundedLpAmount: uint256 = 0
    if currentLegoBalance > preLegoBalance:
        refundedLpAmount = currentLegoBalance - preLegoBalance
        assert extcall IERC20(_lpToken).transfer(msg.sender, refundedLpAmount, default_return_value=True) # dev: transfer failed
        lpAmount -= refundedLpAmount

    usdValue: uint256 = self._getUsdValue(_tokenA, amountA, _tokenB, amountB, miniAddys)
    log UniswapV2LiquidityRemoved(
        sender = msg.sender,
        pool = _pool,
        tokenA = _tokenA,
        tokenB = _tokenB,
        amountA = amountA,
        amountB = amountB,
        lpToken = _lpToken,
        lpAmountBurned = lpAmount,
        usdValue = usdValue,
        recipient = _recipient,
    )
    return amountA, amountB, lpAmount, usdValue


# get usd value on liquidity actions


@internal
def _getUsdValue(
    _tokenA: address,
    _amountA: uint256,
    _tokenB: address,
    _amountB: uint256,
    _miniAddys: Lego.MiniAddys,
) -> uint256:

    usdValueA: uint256 = 0
    if _amountA != 0:
        usdValueA = extcall Appraiser(_miniAddys.appraiser).updatePriceAndGetUsdValue(_tokenA, _amountA, _miniAddys.missionControl, _miniAddys.legoBook)

    usdValueB: uint256 = 0
    if _amountB != 0:
        usdValueB = extcall Appraiser(_miniAddys.appraiser).updatePriceAndGetUsdValue(_tokenB, _amountB, _miniAddys.missionControl, _miniAddys.legoBook)

    return usdValueA + usdValueB


#############
# Utilities #
#############


@view
@external
def getLpToken(_pool: address) -> address:
    # in uniswap v2, the lp token is the pool address
    return _pool


@view
@external
def getPoolForLpToken(_lpToken: address) -> address:
    # in uniswap v2, the pool is the lp token address
    return _lpToken


@view
@external
def getCoreRouterPool() -> address:
    return self.coreRouterPool


@view
@external
def getDeepestLiqPool(_tokenA: address, _tokenB: address) -> BestPool:
    pool: address = staticcall UniV2Factory(UNISWAP_V2_FACTORY).getPair(_tokenA, _tokenB)
    if pool == empty(address):
        return empty(BestPool)

    # get reserves
    reserve0: uint112 = 0
    reserve1: uint112 = 0
    na: uint32 = 0
    reserve0, reserve1, na = staticcall IUniswapV2Pair(pool).getReserves()

    return BestPool(
        pool=pool,
        fee=30, # 0.3%, denominator is 100_00
        liquidity=convert(reserve0 + reserve1, uint256),
        numCoins=2,
    )


@view
@external
def getBestSwapAmountOut(_tokenIn: address, _tokenOut: address, _amountIn: uint256) -> (address, uint256):
    pool: address = staticcall UniV2Factory(UNISWAP_V2_FACTORY).getPair(_tokenIn, _tokenOut)
    if pool == empty(address):
        return empty(address), 0
    token0: address = staticcall IUniswapV2Pair(pool).token0()
    return pool, self._getAmountOut(pool, _tokenIn == token0, _amountIn)


@view
@external
def getSwapAmountOut(
    _pool: address,
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256,
) -> uint256:
    token0: address = staticcall IUniswapV2Pair(_pool).token0()
    return self._getAmountOut(_pool, _tokenIn == token0, _amountIn)


@view
@external
def getBestSwapAmountIn(_tokenIn: address, _tokenOut: address, _amountOut: uint256) -> (address, uint256):
    pool: address = staticcall UniV2Factory(UNISWAP_V2_FACTORY).getPair(_tokenIn, _tokenOut)
    if pool == empty(address):
        return empty(address), 0
    token0: address = staticcall IUniswapV2Pair(pool).token0()
    return pool, self._getAmountIn(pool, _tokenIn == token0, _amountOut)


@view
@external
def getSwapAmountIn(
    _pool: address,
    _tokenIn: address,
    _tokenOut: address,
    _amountOut: uint256,
) -> uint256:
    token0: address = staticcall IUniswapV2Pair(_pool).token0()
    return self._getAmountIn(_pool, _tokenIn == token0, _amountOut)


@view
@external
def getAddLiqAmountsIn(
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _availAmountA: uint256,
    _availAmountB: uint256,
) -> (uint256, uint256, uint256):
    token0: address = staticcall IUniswapV2Pair(_pool).token0()

    reserveA: uint256 = 0
    reserveB: uint256 = 0
    reserveA, reserveB = self._getReserves(_pool, _tokenA == token0)

    # insufficient liquidity
    if reserveA == 0 or reserveB == 0:
        return 0, 0, 0

    # calculate optimal amounts
    amountA: uint256 = _availAmountA
    amountB: uint256 = self._quote(_availAmountA, reserveA, reserveB)
    if amountB > _availAmountB:
        maybeAmountA: uint256 = self._quote(_availAmountB, reserveB, reserveA)
        if maybeAmountA <= _availAmountA:
            amountA = maybeAmountA
            amountB = _availAmountB
    return amountA, amountB, 0


@view
@external
def getRemoveLiqAmountsOut(
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _lpAmount: uint256,
) -> (uint256, uint256):
    token0: address = staticcall IUniswapV2Pair(_pool).token0()

    reserveA: uint256 = 0
    reserveB: uint256 = 0
    reserveA, reserveB = self._getReserves(_pool, _tokenA == token0)

    # insufficient liquidity
    if reserveA == 0 or reserveB == 0:
        return max_value(uint256), max_value(uint256)

    # calculate expected amounts out
    totalSupply: uint256 = staticcall IERC20(_pool).totalSupply()
    expectedAmountA: uint256 = _lpAmount * reserveA // totalSupply
    expectedAmountB: uint256 = _lpAmount * reserveB // totalSupply
    return expectedAmountA, expectedAmountB


@view
@external
def getPrice(_asset: address, _decimals: uint256) -> uint256:
    return 0 # TODO: implement price


@view
@external
def getPriceUnsafe(_pool: address, _targetToken: address, _appraiser: address = empty(address)) -> uint256:
    token0: address = staticcall IUniswapV2Pair(_pool).token0()
    token1: address = staticcall IUniswapV2Pair(_pool).token1()

    # appraiser
    appraiser: address = _appraiser
    if _appraiser == empty(address):
        appraiser = addys._getAppraiserAddr()

    # alt price
    altPrice: uint256 = 0
    if _targetToken == token0:
        altPrice = staticcall Appraiser(appraiser).getNormalAssetPrice(token1)
    else:
        altPrice = staticcall Appraiser(appraiser).getNormalAssetPrice(token0)

    # return early if no alt price
    if altPrice == 0:
        return 0

    # reserves
    reserve0: uint112 = 0
    reserve1: uint112 = 0
    na: uint32 = 0
    reserve0, reserve1, na = staticcall IUniswapV2Pair(_pool).getReserves()

    # avoid division by zero
    if reserve0 == 0 or reserve1 == 0:
        return 0  

    # price of token0 in token1
    priceZeroToOne: uint256 = convert(reserve1, uint256) * EIGHTEEN_DECIMALS // convert(reserve0, uint256)

    # adjust for decimals: price should be in 18 decimals
    decimals0: uint256 = convert(staticcall IERC20Detailed(token0).decimals(), uint256)
    decimals1: uint256 = convert(staticcall IERC20Detailed(token1).decimals(), uint256)
    if decimals0 > decimals1:
        scaleFactor: uint256 = 10 ** (decimals0 - decimals1)
        priceZeroToOne = priceZeroToOne * scaleFactor
    elif decimals1 > decimals0:
        scaleFactor: uint256 = 10 ** (decimals1 - decimals0)
        priceZeroToOne = priceZeroToOne // scaleFactor

    # if _targetToken is token1, make price inverse
    priceToOther: uint256 = priceZeroToOne
    if _targetToken == token1:
        priceToOther = EIGHTEEN_DECIMALS * EIGHTEEN_DECIMALS // priceZeroToOne

    return altPrice * priceToOther // EIGHTEEN_DECIMALS


# internal utils


@view
@internal
def _quote(_amountA: uint256, _reserveA: uint256, _reserveB: uint256) -> uint256:
    return (_amountA * _reserveB) // _reserveA


@view
@internal
def _getReserves(_pool: address, _isTokenAZeroIndex: bool) -> (uint256, uint256):
    reserve0: uint112 = 0
    reserve1: uint112 = 0
    na: uint32 = 0
    reserve0, reserve1, na = staticcall IUniswapV2Pair(_pool).getReserves()

    # determine which token is which
    reserveA: uint256 = convert(reserve0, uint256)
    reserveB: uint256 = convert(reserve1, uint256)
    if not _isTokenAZeroIndex:
        reserveA = convert(reserve1, uint256)
        reserveB = convert(reserve0, uint256)

    return reserveA, reserveB


@view
@internal
def _getAmountOut(
    _pool: address,
    _zeroForOne: bool,
    _amountIn: uint256,
) -> uint256:
    if _amountIn == 0:
        return 0

    # get reserves
    reserveIn: uint256 = 0
    reserveOut: uint256 = 0
    reserveIn, reserveOut = self._getReserves(_pool, _zeroForOne)
    if reserveIn == 0 or reserveOut == 0:
        return 0

    # calculate amount out
    amountInWithFee: uint256 = _amountIn * 997 # 1000 - 3 (0.3% fee)
    numerator: uint256 = amountInWithFee * reserveOut
    denominator: uint256 = (reserveIn * 1000) + amountInWithFee
    return numerator // denominator


@view
@internal
def _getAmountIn(_pool: address, _zeroForOne: bool, _amountOut: uint256) -> uint256:
    if _amountOut == 0 or _amountOut == max_value(uint256):
        return max_value(uint256)

    reserveIn: uint256 = 0
    reserveOut: uint256 = 0
    reserveIn, reserveOut = self._getReserves(_pool, _zeroForOne)
    if reserveIn == 0 or reserveOut == 0:
        return max_value(uint256)

    if _amountOut > reserveOut:
        return max_value(uint256)

    numerator: uint256 = reserveIn * _amountOut * 1000
    denominator: uint256 = (reserveOut - _amountOut) * 997
    return (numerator // denominator) + 1


#########
# Other #
#########


@external
def depositForYield(
    _asset: address,
    _amount: uint256,
    _vaultAddr: address,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: Lego.MiniAddys = empty(Lego.MiniAddys),
) -> (uint256, address, uint256, uint256):
    return 0, empty(address), 0, 0


@external
def withdrawFromYield(
    _vaultToken: address,
    _amount: uint256,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: Lego.MiniAddys = empty(Lego.MiniAddys),
) -> (uint256, address, uint256, uint256):
    return 0, empty(address), 0, 0


@external
def mintOrRedeemAsset(
    _tokenIn: address,
    _tokenOut: address,
    _tokenInAmount: uint256,
    _minAmountOut: uint256,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: Lego.MiniAddys = empty(Lego.MiniAddys),
) -> (uint256, uint256, bool, uint256):
    return 0, 0, False, 0
    

@external
def confirmMintOrRedeemAsset(
    _tokenIn: address,
    _tokenOut: address,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: Lego.MiniAddys = empty(Lego.MiniAddys),
) -> (uint256, uint256):
    return 0, 0


@external
def addCollateral(
    _asset: address,
    _amount: uint256,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: Lego.MiniAddys = empty(Lego.MiniAddys),
) -> (uint256, uint256):
    return 0, 0


@external
def removeCollateral(
    _asset: address,
    _amount: uint256,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: Lego.MiniAddys = empty(Lego.MiniAddys),
) -> (uint256, uint256):
    return 0, 0


@external
def borrow(
    _borrowAsset: address,
    _amount: uint256,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: Lego.MiniAddys = empty(Lego.MiniAddys),
) -> (uint256, uint256):
    return 0, 0


@external
def repayDebt(
    _paymentAsset: address,
    _paymentAmount: uint256,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: Lego.MiniAddys = empty(Lego.MiniAddys),
) -> (uint256, uint256):
    return 0, 0


@external
def claimRewards(
    _user: address,
    _rewardToken: address,
    _rewardAmount: uint256,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _miniAddys: Lego.MiniAddys = empty(Lego.MiniAddys),
) -> (uint256, uint256):
    return 0, 0

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
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: Lego.MiniAddys = empty(Lego.MiniAddys),
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
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: Lego.MiniAddys = empty(Lego.MiniAddys),
) -> (uint256, uint256, uint256, bool, uint256):
    return 0, 0, 0, False, 0



@view
@external
def getAccessForLego(_user: address, _action: wi.ActionType) -> (address, String[64], uint256):
    return empty(address), empty(String[64]), 0


@view
@external
def getPricePerShare(_asset: address, _decimals: uint256) -> uint256:
    return 0
