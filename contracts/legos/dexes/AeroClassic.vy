#     _____  _____  __  __    ____   _____  _____  _____ 
#    |  _  \/   __\/  \/  \  /  _/  /   __\/   __\/  _  \
#    |  |  ||   __|>-    -<  |  |---|   __||  |_ ||  |  |
#    |_____/\_____/\__/\__/  \_____/\_____/\_____/\_____/
#                                                                       
#     ╔═════════════════════════════════════════╗
#     ║  ** Aero Classic Lego **                ║
#     ║  Integration with Aerodrome Classic.    ║
#     ╚═════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

implements: Lego
implements: DexLego

exports: addys.__interface__
exports: dld.__interface__

initializes: addys
initializes: dld[addys := addys]

from interfaces import LegoPartner as Lego
from interfaces import DexLego as DexLego
from interfaces import WalletStructs as ws

import contracts.modules.Addys as addys
import contracts.modules.DexLegoData as dld

from ethereum.ercs import IERC20
from ethereum.ercs import IERC20Detailed

interface AeroRouter:
    def addLiquidity(_tokenA: address, _tokenB: address, _isStable: bool, _amountADesired: uint256, _amountBDesired: uint256, _amountAMin: uint256, _amountBMin: uint256, _recipient: address, _deadline: uint256) -> (uint256, uint256, uint256): nonpayable
    def removeLiquidity(_tokenA: address, _tokenB: address, _isStable: bool, _lpAmount: uint256, _amountAMin: uint256, _amountBMin: uint256, _recipient: address, _deadline: uint256) -> (uint256, uint256): nonpayable
    def quoteAddLiquidity(_tokenA: address, _tokenB: address, _isStable: bool, _factory: address, _amountADesired: uint256, _amountBDesired: uint256) -> (uint256, uint256, uint256): view
    def swapExactTokensForTokens(_amountIn: uint256, _amountOutMin: uint256, _path: DynArray[Route, 10], _to: address, _deadline: uint256) -> DynArray[uint256, 10]: nonpayable
    def quoteRemoveLiquidity(_tokenA: address, _tokenB: address, _isStable: bool, _factory: address, _liquidity: uint256) -> (uint256, uint256): view

interface AeroClassicPool:
    def swap(_amount0Out: uint256, _amount1Out: uint256, _recipient: address, _data: Bytes[256]): nonpayable
    def getAmountOut(_amountIn: uint256, _tokenIn: address) -> uint256: view
    def getReserves() -> (uint256, uint256, uint256): view
    def tokens() -> (address, address): view
    def stable() -> bool: view

interface Appraiser:
    def getUsdValue(_asset: address, _amount: uint256, _missionControl: address = empty(address), _legoBook: address = empty(address), _ledger: address = empty(address)) -> uint256: view
    def getRipePrice(_asset: address) -> uint256: view

interface AeroFactory:
    def getPool(_tokenA: address, _tokenB: address, _isStable: bool) -> address: view
    def getFee(_pool: address, _isStable: bool) -> uint256: view

interface VaultRegistry:
    def isEarnVault(_vaultAddr: address) -> bool: view

interface Ledger:
    def isUserWallet(_user: address) -> bool: view

interface Registry:
    def isValidAddr(_addr: address) -> bool: view

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

event AerodromeSwap:
    sender: indexed(address)
    tokenIn: indexed(address)
    tokenOut: indexed(address)
    amountIn: uint256
    amountOut: uint256
    usdValue: uint256
    numTokens: uint256
    recipient: address

event AerodromeLiquidityAdded:
    sender: indexed(address)
    tokenA: indexed(address)
    tokenB: indexed(address)
    amountA: uint256
    amountB: uint256
    lpAmountReceived: uint256
    usdValue: uint256
    recipient: address

event AerodromeLiquidityRemoved:
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

# aero
AERODROME_FACTORY: public(immutable(address))
AERODROME_ROUTER: public(immutable(address))
RIPE_REGISTRY: public(immutable(address))

coreRouterPool: public(address)

MAX_TOKEN_PATH: constant(uint256) = 5
EIGHTEEN_DECIMALS: constant(uint256) = 10 ** 18
MAX_PROOFS: constant(uint256) = 25


@deploy
def __init__(
    _undyHq: address,
    _aerodromeFactory: address,
    _aerodromeRouter: address,
    _coreRouterPool: address,
    _ripeRegistry: address,
):
    addys.__init__(_undyHq)
    dld.__init__(False)

    assert empty(address) not in [_aerodromeFactory, _aerodromeRouter, _coreRouterPool, _ripeRegistry] # dev: invalid addrs
    AERODROME_FACTORY = _aerodromeFactory
    AERODROME_ROUTER = _aerodromeRouter
    RIPE_REGISTRY = _ripeRegistry
    self.coreRouterPool = _coreRouterPool


@view
@external
def hasCapability(_action: ws.ActionType) -> bool:
    return _action in (
        ws.ActionType.SWAP |
        ws.ActionType.ADD_LIQ | 
        ws.ActionType.REMOVE_LIQ
    )


@view
@external
def getRegistries() -> DynArray[address, 10]:
    return [AERODROME_FACTORY, AERODROME_ROUTER]


@view
@external
def isYieldLego() -> bool:
    return False


@view
@external
def isDexLego() -> bool:
    return True


@view
@internal
def _isAllowedToPerformAction(_caller: address) -> bool:
    if staticcall VaultRegistry(addys._getVaultRegistryAddr()).isEarnVault(_caller):
        return True
    if staticcall Ledger(addys._getLedgerAddr()).isUserWallet(_caller):
        return True
    return staticcall Registry(RIPE_REGISTRY).isValidAddr(_caller)


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
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256, uint256):
    assert not dld.isPaused # dev: paused
    assert self._isAllowedToPerformAction(msg.sender) # dev: no perms
    miniAddys: ws.MiniAddys = dld._getMiniAddys(_miniAddys)

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

    # adjust min amount out
    minAmountOut: uint256 = _minAmountOut
    if amountIn < _amountIn and _amountIn != max_value(uint256):
        minAmountOut = _minAmountOut * amountIn // _amountIn

    # transfer initial amount to first pool
    assert extcall IERC20(tokenIn).transfer(_poolPath[0], amountIn, default_return_value=True) # dev: transfer failed

    # iterate through swap routes
    tempAmountIn: uint256 = amountIn
    aeroFactory: address = AERODROME_FACTORY
    for i: uint256 in range(numTokens - 1, bound=MAX_TOKEN_PATH):
        tempTokenIn: address = _tokenPath[i]
        tempTokenOut: address = _tokenPath[i + 1]
        tempPool: address = _poolPath[i]

        # transfer to next pool (or to recipient if last swap)
        recipient: address = _recipient
        if i < numTokens - 2:
            recipient = _poolPath[i + 1]

        # swap
        tempAmountIn = self._swapTokensInPool(tempPool, tempTokenIn, tempTokenOut, tempAmountIn, recipient, aeroFactory)

    # final amount
    amountOut: uint256 = tempAmountIn
    assert amountOut >= minAmountOut # dev: min amount out not met

    # refund if full swap didn't get through
    currentLegoBalance: uint256 = staticcall IERC20(tokenIn).balanceOf(self)
    refundAssetAmount: uint256 = 0
    if currentLegoBalance > preLegoBalance:
        refundAssetAmount = currentLegoBalance - preLegoBalance
        assert extcall IERC20(tokenIn).transfer(msg.sender, refundAssetAmount, default_return_value=True) # dev: transfer failed
        amountIn -= refundAssetAmount

    # get usd values
    usdValue: uint256 = staticcall Appraiser(miniAddys.appraiser).getUsdValue(tokenIn, amountIn, miniAddys.missionControl, miniAddys.legoBook, miniAddys.ledger)
    if usdValue == 0:
        usdValue = staticcall Appraiser(miniAddys.appraiser).getUsdValue(tokenOut, amountOut, miniAddys.missionControl, miniAddys.legoBook, miniAddys.ledger)

    log AerodromeSwap(
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
    _aeroFactory: address,
) -> uint256:
    token0: address = empty(address)
    token1: address = empty(address)
    token0, token1 = staticcall AeroClassicPool(_pool).tokens()

    tokens: address[2] = [token0, token1]
    assert _tokenIn in tokens # dev: invalid tokenIn
    assert _tokenOut in tokens # dev: invalid tokenOut
    assert _tokenIn != _tokenOut # dev: invalid tokens

    # verify actual aerodrome pool
    assert staticcall AeroFactory(_aeroFactory).getPool(_tokenIn, _tokenOut, staticcall AeroClassicPool(_pool).stable()) == _pool # dev: invalid pool

    zeroForOne: bool = _tokenIn == token0
    amountOut: uint256 = staticcall AeroClassicPool(_pool).getAmountOut(_amountIn, _tokenIn)
    assert amountOut != 0 # dev: no tokens swapped

    # put in correct order
    amount0Out: uint256 = amountOut
    amount1Out: uint256 = 0
    if zeroForOne:
        amount0Out = 0
        amount1Out = amountOut

    extcall AeroClassicPool(_pool).swap(amount0Out, amount1Out, _recipient, b"")
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
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (address, uint256, uint256, uint256, uint256):
    assert not dld.isPaused # dev: paused
    assert self._isAllowedToPerformAction(msg.sender) # dev: no perms
    miniAddys: ws.MiniAddys = dld._getMiniAddys(_miniAddys)

    # validate tokens
    token0: address = empty(address)
    token1: address = empty(address)
    token0, token1 = staticcall AeroClassicPool(_pool).tokens()

    tokens: address[2] = [token0, token1]
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
    router: address = AERODROME_ROUTER
    assert extcall IERC20(_tokenA).approve(router, liqAmountA, default_return_value=True) # dev: approval failed
    assert extcall IERC20(_tokenB).approve(router, liqAmountB, default_return_value=True) # dev: approval failed

    # add liquidity
    lpAmountReceived: uint256 = 0
    liqAmountA, liqAmountB, lpAmountReceived = extcall AeroRouter(router).addLiquidity(
        _tokenA,
        _tokenB,
        staticcall AeroClassicPool(_pool).stable(),
        liqAmountA,
        liqAmountB,
        _minAmountA,
        _minAmountB,
        _recipient,
        block.timestamp,
    )
    assert lpAmountReceived != 0 # dev: no liquidity added
    if _minLpAmount != 0:
        assert lpAmountReceived >= _minLpAmount # dev: insufficient liquidity added

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
    log AerodromeLiquidityAdded(
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
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256, uint256, uint256):
    assert not dld.isPaused # dev: paused
    assert self._isAllowedToPerformAction(msg.sender) # dev: no perms
    miniAddys: ws.MiniAddys = dld._getMiniAddys(_miniAddys)

    # validate tokens
    token0: address = empty(address)
    token1: address = empty(address)
    token0, token1 = staticcall AeroClassicPool(_pool).tokens()

    tokens: address[2] = [token0, token1]
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
    router: address = AERODROME_ROUTER
    assert extcall IERC20(_lpToken).approve(router, lpAmount, default_return_value=True) # dev: approval failed

    # remove liquidity
    amountA: uint256 = 0
    amountB: uint256 = 0
    amountA, amountB = extcall AeroRouter(router).removeLiquidity(
        _tokenA,
        _tokenB,
        staticcall AeroClassicPool(_pool).stable(),
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
    log AerodromeLiquidityRemoved(
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
    _miniAddys: ws.MiniAddys,
) -> uint256:

    usdValueA: uint256 = 0
    if _amountA != 0:
        usdValueA = staticcall Appraiser(_miniAddys.appraiser).getUsdValue(_tokenA, _amountA, _miniAddys.missionControl, _miniAddys.legoBook, _miniAddys.ledger)

    usdValueB: uint256 = 0
    if _amountB != 0:
        usdValueB = staticcall Appraiser(_miniAddys.appraiser).getUsdValue(_tokenB, _amountB, _miniAddys.missionControl, _miniAddys.legoBook, _miniAddys.ledger)

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
    factory: address = AERODROME_FACTORY
    reserve0: uint256 = 0
    reserve1: uint256 = 0
    na: uint256 = 0

    # get pool options
    stablePool: address = staticcall AeroFactory(factory).getPool(_tokenA, _tokenB, True)
    volatilePool: address = staticcall AeroFactory(factory).getPool(_tokenA, _tokenB, False)

    # no pools found
    if stablePool == empty(address) and volatilePool == empty(address):
        return empty(BestPool)

    # stable pool
    stableLiquidity: uint256 = 0
    if stablePool != empty(address):
        reserve0, reserve1, na = staticcall AeroClassicPool(stablePool).getReserves()
        stableLiquidity = reserve0 + reserve1

    # volatile pool
    volatileLiquidity: uint256 = 0
    if volatilePool != empty(address):
        reserve0, reserve1, na = staticcall AeroClassicPool(volatilePool).getReserves()
        volatileLiquidity = reserve0 + reserve1

    # best pool determined by liquidity
    bestPoolAddr: address = stablePool
    bestLiquidity: uint256 = stableLiquidity
    isStable: bool = True
    if volatileLiquidity > stableLiquidity:
        bestPoolAddr = volatilePool
        bestLiquidity = volatileLiquidity
        isStable = False

    return BestPool(
        pool=bestPoolAddr,
        fee=staticcall AeroFactory(factory).getFee(bestPoolAddr, isStable),
        liquidity=bestLiquidity,
        numCoins=2,
    )


@view
@external
def getBestSwapAmountOut(_tokenIn: address, _tokenOut: address, _amountIn: uint256) -> (address, uint256):
    factory: address = AERODROME_FACTORY
    stablePool: address = staticcall AeroFactory(factory).getPool(_tokenIn, _tokenOut, True)
    volatilePool: address = staticcall AeroFactory(factory).getPool(_tokenIn, _tokenOut, False)
    if stablePool == empty(address) and volatilePool == empty(address):
        return empty(address), 0

    # stable pool
    stableAmountOut: uint256 = 0
    if stablePool != empty(address):
        stableAmountOut = staticcall AeroClassicPool(stablePool).getAmountOut(_amountIn, _tokenIn)

    # volatile pool
    volatileAmountOut: uint256 = 0
    if volatilePool != empty(address):
        volatileAmountOut = staticcall AeroClassicPool(volatilePool).getAmountOut(_amountIn, _tokenIn)

    if stableAmountOut == 0 and volatileAmountOut == 0:
        return empty(address), 0

    pool: address = stablePool
    amountOut: uint256 = stableAmountOut
    if volatileAmountOut > stableAmountOut:
        pool = volatilePool
        amountOut = volatileAmountOut

    return pool, amountOut


@view
@external
def getSwapAmountOut(
    _pool: address,
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256,
) -> uint256:
    return staticcall AeroClassicPool(_pool).getAmountOut(_amountIn, _tokenIn)


@view
@external
def getBestSwapAmountIn(_tokenIn: address, _tokenOut: address, _amountOut: uint256) -> (address, uint256):
    # TODO: implement stable pools
    pool: address = staticcall AeroFactory(AERODROME_FACTORY).getPool(_tokenIn, _tokenOut, False)
    if pool == empty(address):
        return empty(address), max_value(uint256)

    token0: address = empty(address)
    token1: address = empty(address)
    token0, token1 = staticcall AeroClassicPool(pool).tokens()
    return pool, self._getAmountInForVolatilePools(pool, token0 == _tokenIn, _amountOut)


@view
@external
def getSwapAmountIn(
    _pool: address,
    _tokenIn: address,
    _tokenOut: address,
    _amountOut: uint256,
) -> uint256:
    if not staticcall AeroClassicPool(_pool).stable():
        token0: address = empty(address)
        token1: address = empty(address)
        token0, token1 = staticcall AeroClassicPool(_pool).tokens()
        return self._getAmountInForVolatilePools(_pool, token0 == _tokenIn, _amountOut)
    else:
        return max_value(uint256) # TODO: implement stable pools


@view
@external
def getAddLiqAmountsIn(
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _availAmountA: uint256,
    _availAmountB: uint256,
) -> (uint256, uint256, uint256):
    return staticcall AeroRouter(AERODROME_ROUTER).quoteAddLiquidity(_tokenA, _tokenB, staticcall AeroClassicPool(_pool).stable(), AERODROME_FACTORY, _availAmountA, _availAmountB)


@view
@external
def getRemoveLiqAmountsOut(
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _lpAmount: uint256,
) -> (uint256, uint256):
    return staticcall AeroRouter(AERODROME_ROUTER).quoteRemoveLiquidity(_tokenA, _tokenB, staticcall AeroClassicPool(_pool).stable(), AERODROME_FACTORY, _lpAmount)


@view
@external
def getPrice(_asset: address, _decimals: uint256) -> uint256:
    return 0 # TODO: implement price


@view
@external
def getPriceUnsafe(_pool: address, _targetToken: address, _appraiser: address = empty(address)) -> uint256:
    if not staticcall AeroClassicPool(_pool).stable():
        return self._getPriceUnsafeVolatilePool(_pool, _targetToken, _appraiser)
    else:
        return 0 # TODO: implement stable pools


# internal utils


@view
@internal
def _getPriceUnsafeVolatilePool(_pool: address, _targetToken: address, _appraiser: address) -> uint256:
    token0: address = empty(address)
    token1: address = empty(address)
    token0, token1 = staticcall AeroClassicPool(_pool).tokens()

    # appraiser
    appraiser: address = _appraiser
    if _appraiser == empty(address):
        appraiser = addys._getAppraiserAddr()

    # alt price
    altPrice: uint256 = 0
    if _targetToken == token0:
        altPrice = staticcall Appraiser(appraiser).getRipePrice(token1)
    else:
        altPrice = staticcall Appraiser(appraiser).getRipePrice(token0)

    # return early if no alt price
    if altPrice == 0:
        return 0

    # reserves
    reserve0: uint256 = 0
    reserve1: uint256 = 0
    na: uint256 = 0
    reserve0, reserve1, na = staticcall AeroClassicPool(_pool).getReserves()

    # avoid division by zero
    if reserve0 == 0 or reserve1 == 0:
        return 0  

    # price of token0 in token1
    priceZeroToOne: uint256 = reserve1 * EIGHTEEN_DECIMALS // reserve0

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


@view
@internal
def _getAmountInForVolatilePools(_pool: address, _zeroForOne: bool, _amountOut: uint256) -> uint256:
    if _amountOut == 0 or _amountOut == max_value(uint256):
        return max_value(uint256)

    reserve0: uint256 = 0
    reserve1: uint256 = 0
    na: uint256 = 0
    reserve0, reserve1, na = staticcall AeroClassicPool(_pool).getReserves()
    if reserve0 == 0 or reserve1 == 0:
        return max_value(uint256)

    # determine which token is which
    reserveIn: uint256 = reserve0
    reserveOut: uint256 = reserve1
    if not _zeroForOne:
        reserveIn = reserve1
        reserveOut = reserve0

    # prevent division by zero: if _amountOut == reserveOut,
    if _amountOut >= reserveOut:
        return max_value(uint256)

    fee: uint256 = staticcall AeroFactory(AERODROME_FACTORY).getFee(_pool, False)
    numerator: uint256 = reserveIn * _amountOut * 100_00
    denominator: uint256 = (reserveOut - _amountOut) * (100_00 - fee)
    return (numerator // denominator) + 1


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
