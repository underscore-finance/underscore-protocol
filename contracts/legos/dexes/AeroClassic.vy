# @version 0.4.3

implements: Lego

exports: addys.__interface__
exports: legoAssets.__interface__

initializes: addys
initializes: legoAssets[addys := addys]

from interfaces import LegoPartner as Lego
from interfaces import Wallet as wi

import contracts.modules.Addys as addys
import contracts.modules.LegoAssets as legoAssets

from ethereum.ercs import IERC20
from ethereum.ercs import IERC20Detailed


interface AeroRouter:
    def addLiquidity(_tokenA: address, _tokenB: address, _isStable: bool, _amountADesired: uint256, _amountBDesired: uint256, _amountAMin: uint256, _amountBMin: uint256, _recipient: address, _deadline: uint256) -> (uint256, uint256, uint256): nonpayable
    def removeLiquidity(_tokenA: address, _tokenB: address, _isStable: bool, _lpAmount: uint256, _amountAMin: uint256, _amountBMin: uint256, _recipient: address, _deadline: uint256) -> (uint256, uint256): nonpayable
    def quoteAddLiquidity(_tokenA: address, _tokenB: address, _isStable: bool, _factory: address, _amountADesired: uint256, _amountBDesired: uint256) -> (uint256, uint256, uint256): view
    def swapExactTokensForTokens(_amountIn: uint256, _amountOutMin: uint256, _path: DynArray[Route, 7], _to: address, _deadline: uint256) -> DynArray[uint256, 7]: nonpayable
    def quoteRemoveLiquidity(_tokenA: address, _tokenB: address, _isStable: bool, _factory: address, _liquidity: uint256) -> (uint256, uint256): view

interface AeroClassicPool:
    def swap(_amount0Out: uint256, _amount1Out: uint256, _recipient: address, _data: Bytes[256]): nonpayable
    def getAmountOut(_amountIn: uint256, _tokenIn: address) -> uint256: view
    def getReserves() -> (uint256, uint256, uint256): view
    def tokens() -> (address, address): view
    def stable() -> bool: view

interface AeroFactory:
    def getPool(_tokenA: address, _tokenB: address, _isStable: bool) -> address: view
    def getFee(_pool: address, _isStable: bool) -> uint256: view

interface Appraiser:
    def updatePriceAndGetUsdValue(_asset: address, _amount: uint256) -> uint256: nonpayable

struct BestPool:
    pool: address
    fee: uint256
    liquidity: uint256
    numCoins: uint256
    legoId: uint256

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

# aero
AERODROME_FACTORY: public(immutable(address))
AERODROME_ROUTER: public(immutable(address))
coreRouterPool: public(address)

MAX_TOKEN_PATH: constant(uint256) = 5
EIGHTEEN_DECIMALS: constant(uint256) = 10 ** 18


@deploy
def __init__(
    _undyHq: address,
    _aerodromeFactory: address,
    _aerodromeRouter: address,
    _coreRouterPool: address,
):
    addys.__init__(_undyHq)
    legoAssets.__init__(False)

    assert empty(address) not in [_aerodromeFactory, _aerodromeRouter, _coreRouterPool] # dev: invalid addrs
    AERODROME_FACTORY = _aerodromeFactory
    AERODROME_ROUTER = _aerodromeRouter
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
    return [AERODROME_FACTORY, AERODROME_ROUTER]


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
) -> (uint256, uint256, uint256):
    assert not legoAssets.isPaused # dev: paused

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
    assert amountOut >= _minAmountOut # dev: min amount out not met

    # refund if full swap didn't get through
    currentLegoBalance: uint256 = staticcall IERC20(tokenIn).balanceOf(self)
    refundAssetAmount: uint256 = 0
    if currentLegoBalance > preLegoBalance:
        refundAssetAmount = currentLegoBalance - preLegoBalance
        assert extcall IERC20(tokenIn).transfer(msg.sender, refundAssetAmount, default_return_value=True) # dev: transfer failed
        amountIn -= refundAssetAmount

    # get usd values
    appraiser: address = addys._getAppraiserAddr()
    usdValue: uint256 = extcall Appraiser(appraiser).updatePriceAndGetUsdValue(tokenIn, amountIn)
    if usdValue == 0:
        usdValue = extcall Appraiser(appraiser).updatePriceAndGetUsdValue(tokenOut, amountOut)

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
    return amountOut, amountOut, usdValue


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
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
) -> (uint256, uint256, uint256, uint256):
    return 0, 0, 0, 0


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
) -> (uint256, uint256, uint256, bool, uint256):
    return 0, 0, 0, False, 0


@view
@external
def getAccessForLego(_user: address, _action: wi.ActionType) -> (address, String[64], uint256):
    return empty(address), empty(String[64]), 0


@view
@external
def getPricePerShare(_yieldAsset: address) -> uint256:
    return 0


@view
@external
def getPrice(_asset: address) -> uint256:
    return 0
