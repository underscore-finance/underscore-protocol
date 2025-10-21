#     __                   _____         _     
#    |  |   ___ ___ ___   |_   _|___ ___| |___ 
#    |  |__| -_| . | . |    | | | . | . | |_ -|
#    |_____|___|_  |___|    |_| |___|___|_|___|
#              |___|                           
#
#     ╔═══════════════════════════════════════════╗
#     ║  ** Lego Tools **                         ║
#     ║  Tools for interacting with the legos.    ║
#     ╚═══════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

implements: Department

exports: addys.__interface__
exports: deptBasics.__interface__

initializes: addys
initializes: deptBasics[addys := addys]

from interfaces import LegoPartner
from interfaces import YieldLego
from interfaces import DexLego
from interfaces import Department

import contracts.modules.Addys as addys
import contracts.modules.DeptBasics as deptBasics
from ethereum.ercs import IERC20

interface LegoDexNonStandard:
    def getSwapAmountOut(_pool: address, _tokenIn: address, _tokenOut: address, _amountIn: uint256) -> uint256: nonpayable
    def getSwapAmountIn(_pool: address, _tokenIn: address, _tokenOut: address, _amountOut: uint256) -> uint256: nonpayable
    def getBestSwapAmountIn(_tokenIn: address, _tokenOut: address, _amountOut: uint256) -> (address, uint256): nonpayable
    def getBestSwapAmountOut(_tokenIn: address, _tokenOut: address, _amountIn: uint256) -> (address, uint256): nonpayable

interface Registry:
    def getAddrInfo(_regId: uint256) -> AddressInfo: view
    def isValidRegId(_regId: uint256) -> bool: view
    def getAddr(_regId: uint256) -> address: view
    def numAddrs() -> uint256: view

interface Appraiser:
    def getUsdValue(_asset: address, _amount: uint256) -> uint256: view

struct AddressInfo:
    addr: address
    version: uint256
    lastModified: uint256
    description: String[64]

struct SwapRoute:
    legoId: uint256
    pool: address
    tokenIn: address
    tokenOut: address
    amountIn: uint256
    amountOut: uint256

struct SwapInstruction:
    legoId: uint256
    amountIn: uint256
    minAmountOut: uint256
    tokenPath: DynArray[address, MAX_TOKEN_PATH]
    poolPath: DynArray[address, MAX_TOKEN_PATH - 1]

struct UnderlyingData:
    asset: address
    amount: uint256
    usdValue: uint256
    legoId: uint256
    legoAddr: address
    legoDesc: String[64]

struct VaultTokenInfo:
    legoId: uint256
    vaultToken: address

# key router tokens
ROUTER_TOKENA: public(immutable(address))
ROUTER_TOKENB: public(immutable(address))

# yield lego ids
AAVE_V3_ID: public(immutable(uint256))
COMPOUND_V3_ID: public(immutable(uint256))
EULER_ID: public(immutable(uint256))
FLUID_ID: public(immutable(uint256))
MOONWELL_ID: public(immutable(uint256))
MORPHO_ID: public(immutable(uint256))

# dex lego ids
UNISWAP_V2_ID: public(immutable(uint256))
UNISWAP_V3_ID: public(immutable(uint256))
AERODROME_ID: public(immutable(uint256))
AERODROME_SLIPSTREAM_ID: public(immutable(uint256))
CURVE_ID: public(immutable(uint256))

MAX_VAULTS_FOR_USER: constant(uint256) = 50
MAX_VAULTS: constant(uint256) = 40
MAX_ROUTES: constant(uint256) = 10
MAX_TOKEN_PATH: constant(uint256) = 5
MAX_SWAP_INSTRUCTIONS: constant(uint256) = 5
MAX_LEGOS: constant(uint256) = 10
HUNDRED_PERCENT: constant(uint256) = 100_00 # 100%


@deploy
def __init__(
    _undyHq: address,
    _routerTokenA: address,
    _routerTokenB: address,
    # yield lego ids
    _aaveV3Id: uint256,
    _compoundV3Id: uint256,
    _eulerId: uint256,
    _fluidId: uint256,
    _moonwellId: uint256,
    _morphoId: uint256,
    # dex lego ids
    _uniswapV2Id: uint256,
    _uniswapV3Id: uint256,
    _aerodromeId: uint256,
    _aerodromeSlipstreamId: uint256,
    _curveId: uint256,
):
    addys.__init__(_undyHq)
    deptBasics.__init__(False, False) # no minting

    assert empty(address) not in [_routerTokenA, _routerTokenB] # dev: invalid address
    ROUTER_TOKENA = _routerTokenA
    ROUTER_TOKENB = _routerTokenB

    # yield lego ids
    legoBook: address = addys._getLegoBookAddr()
    assert staticcall Registry(legoBook).isValidRegId(_aaveV3Id) # dev: invalid id
    assert staticcall Registry(legoBook).isValidRegId(_compoundV3Id) # dev: invalid id
    assert staticcall Registry(legoBook).isValidRegId(_eulerId) # dev: invalid id
    assert staticcall Registry(legoBook).isValidRegId(_fluidId) # dev: invalid id
    assert staticcall Registry(legoBook).isValidRegId(_moonwellId) # dev: invalid id
    assert staticcall Registry(legoBook).isValidRegId(_morphoId) # dev: invalid id

    AAVE_V3_ID = _aaveV3Id
    COMPOUND_V3_ID = _compoundV3Id
    EULER_ID = _eulerId
    FLUID_ID = _fluidId
    MOONWELL_ID = _moonwellId
    MORPHO_ID = _morphoId

    # dex lego ids
    assert staticcall Registry(legoBook).isValidRegId(_uniswapV2Id) # dev: invalid id
    assert staticcall Registry(legoBook).isValidRegId(_uniswapV3Id) # dev: invalid id
    assert staticcall Registry(legoBook).isValidRegId(_aerodromeId) # dev: invalid id
    assert staticcall Registry(legoBook).isValidRegId(_aerodromeSlipstreamId) # dev: invalid id
    assert staticcall Registry(legoBook).isValidRegId(_curveId) # dev: invalid id

    UNISWAP_V2_ID = _uniswapV2Id
    UNISWAP_V3_ID = _uniswapV3Id
    AERODROME_ID = _aerodromeId
    AERODROME_SLIPSTREAM_ID = _aerodromeSlipstreamId
    CURVE_ID = _curveId


###############
# Yield Legos #
###############


@view
@external
def aaveV3() -> address:
    return staticcall Registry(addys._getLegoBookAddr()).getAddr(AAVE_V3_ID)


@view
@external
def aaveV3Id() -> uint256:
    return AAVE_V3_ID


@view
@external
def compoundV3() -> address:
    return staticcall Registry(addys._getLegoBookAddr()).getAddr(COMPOUND_V3_ID)


@view
@external
def compoundV3Id() -> uint256:
    return COMPOUND_V3_ID


@view
@external
def euler() -> address:
    return staticcall Registry(addys._getLegoBookAddr()).getAddr(EULER_ID)


@view
@external
def eulerId() -> uint256:
    return EULER_ID


@view
@external
def fluid() -> address:
    return staticcall Registry(addys._getLegoBookAddr()).getAddr(FLUID_ID)


@view
@external
def fluidId() -> uint256:
    return FLUID_ID


@view
@external
def moonwell() -> address:
    return staticcall Registry(addys._getLegoBookAddr()).getAddr(MOONWELL_ID)


@view
@external
def moonwellId() -> uint256:
    return MOONWELL_ID


@view
@external
def morpho() -> address:
    return staticcall Registry(addys._getLegoBookAddr()).getAddr(MORPHO_ID)


@view
@external
def morphoId() -> uint256:
    return MORPHO_ID


#############
# DEX Legos #
#############


@view
@external
def uniswapV2() -> address:
    return staticcall Registry(addys._getLegoBookAddr()).getAddr(UNISWAP_V2_ID)


@view
@external
def uniswapV2Id() -> uint256:
    return UNISWAP_V2_ID


@view
@external
def uniswapV3() -> address:
    return staticcall Registry(addys._getLegoBookAddr()).getAddr(UNISWAP_V3_ID)


@view
@external
def uniswapV3Id() -> uint256:
    return UNISWAP_V3_ID


@view
@external
def aerodrome() -> address:
    return staticcall Registry(addys._getLegoBookAddr()).getAddr(AERODROME_ID)


@view
@external
def aerodromeId() -> uint256:
    return AERODROME_ID


@view
@external
def aerodromeSlipstream() -> address:
    return staticcall Registry(addys._getLegoBookAddr()).getAddr(AERODROME_SLIPSTREAM_ID)


@view
@external
def aerodromeSlipstreamId() -> uint256:
    return AERODROME_SLIPSTREAM_ID


@view
@external
def curve() -> address:
    return staticcall Registry(addys._getLegoBookAddr()).getAddr(CURVE_ID)


@view
@external
def curveId() -> uint256:
    return CURVE_ID


#################
# Yield Helpers #
#################


# get underlying asset (given a vault token)


@view
@external
def getUnderlyingAsset(_vaultToken: address, _legoBook: address = empty(address)) -> address:
    if _vaultToken == empty(address):
        return empty(address)

    legoBook: address = _legoBook
    if _legoBook == empty(address):
        legoBook = addys._getLegoBookAddr()

    numLegos: uint256 = staticcall Registry(legoBook).numAddrs()
    if numLegos == 0:
        return empty(address)

    for i: uint256 in range(1, numLegos, bound=max_value(uint256)):
        legoAddr: address = staticcall Registry(legoBook).getAddr(i)
        if not staticcall LegoPartner(legoAddr).isYieldLego():
            continue

        asset: address = staticcall YieldLego(legoAddr).getUnderlyingAsset(_vaultToken)
        if asset != empty(address):
            return asset

    return empty(address)


# get underlying amount (given user and underlying asset)


@view
@external
def getUnderlyingForUser(_user: address, _asset: address, _legoBook: address = empty(address)) -> uint256:
    if empty(address) in [_user, _asset]:
        return 0

    legoBook: address = _legoBook
    if _legoBook == empty(address):
        legoBook = addys._getLegoBookAddr()

    numLegos: uint256 = staticcall Registry(legoBook).numAddrs()
    if numLegos == 0:
        return 0

    totalDeposited: uint256 = 0
    for i: uint256 in range(1, numLegos, bound=max_value(uint256)):
        legoAddr: address = staticcall Registry(legoBook).getAddr(i)
        if not staticcall LegoPartner(legoAddr).isYieldLego():
            continue

        legoVaultTokens: DynArray[address, MAX_VAULTS] = staticcall YieldLego(legoAddr).getAssetOpportunities(_asset)
        if len(legoVaultTokens) == 0:
            continue

        for vaultToken: address in legoVaultTokens:
            if vaultToken == empty(address):
                continue
            vaultTokenBal: uint256 = staticcall IERC20(vaultToken).balanceOf(_user)
            if vaultTokenBal != 0:
                totalDeposited += staticcall YieldLego(legoAddr).getUnderlyingAmount(vaultToken, vaultTokenBal)

    return totalDeposited


# get all vault tokens (given user and underlying asset)


@view
@external
def getVaultTokensForUser(_user: address, _asset: address, _legoBook: address = empty(address)) -> DynArray[VaultTokenInfo, MAX_VAULTS_FOR_USER]:
    if empty(address) in [_user, _asset]:
        return []

    legoBook: address = _legoBook
    if _legoBook == empty(address):
        legoBook = addys._getLegoBookAddr()

    numLegos: uint256 = staticcall Registry(legoBook).numAddrs()
    if numLegos == 0:
        return []

    vaultTokens: DynArray[VaultTokenInfo, MAX_VAULTS_FOR_USER] = []
    for i: uint256 in range(1, numLegos, bound=max_value(uint256)):
        legoAddr: address = staticcall Registry(legoBook).getAddr(i)
        if not staticcall LegoPartner(legoAddr).isYieldLego():
            continue

        legoVaultTokens: DynArray[address, MAX_VAULTS] = staticcall YieldLego(legoAddr).getAssetOpportunities(_asset)
        if len(legoVaultTokens) == 0:
            continue

        for vaultToken: address in legoVaultTokens:
            if vaultToken == empty(address):
                continue
            if staticcall IERC20(vaultToken).balanceOf(_user) != 0:
                vaultTokens.append(VaultTokenInfo(
                    legoId=i,
                    vaultToken=vaultToken
                ))

    return vaultTokens


# is vault token (given a vault token)


@view
@external
def isVaultToken(_vaultToken: address, _legoBook: address = empty(address)) -> bool:
    if _vaultToken == empty(address):
        return False

    legoBook: address = _legoBook
    if _legoBook == empty(address):
        legoBook = addys._getLegoBookAddr()

    numLegos: uint256 = staticcall Registry(legoBook).numAddrs()
    if numLegos == 0:
        return False

    for i: uint256 in range(1, numLegos, bound=max_value(uint256)):
        legoAddr: address = staticcall Registry(legoBook).getAddr(i)
        if not staticcall LegoPartner(legoAddr).isYieldLego():
            continue

        if staticcall YieldLego(legoAddr).isLegoAsset(_vaultToken):
            return True

    return False


# get vault token amount (given an underlying asset, underlying amount, and vault token)


@view
@external
def getVaultTokenAmount(_asset: address, _assetAmount: uint256, _vaultToken: address, _legoBook: address = empty(address)) -> uint256:
    if _assetAmount == 0 or _asset == empty(address) or _vaultToken == empty(address):
        return 0

    legoBook: address = _legoBook
    if _legoBook == empty(address):
        legoBook = addys._getLegoBookAddr()

    numLegos: uint256 = staticcall Registry(legoBook).numAddrs()
    if numLegos == 0:
        return 0

    for i: uint256 in range(1, numLegos, bound=max_value(uint256)):
        legoAddr: address = staticcall Registry(legoBook).getAddr(i)
        if not staticcall LegoPartner(legoAddr).isYieldLego():
            continue

        vaultTokenAmount: uint256 = staticcall YieldLego(legoAddr).getVaultTokenAmount(_asset, _assetAmount, _vaultToken)
        if vaultTokenAmount != 0:
            return vaultTokenAmount

    return 0


# get lego info (given a vault token)


@view
@external
def getLegoInfoFromVaultToken(_vaultToken: address, _legoBook: address = empty(address)) -> (uint256, address, String[64]):
    if _vaultToken == empty(address):
        return 0, empty(address), ""

    legoBook: address = _legoBook
    if _legoBook == empty(address):
        legoBook = addys._getLegoBookAddr()

    numLegos: uint256 = staticcall Registry(legoBook).numAddrs()
    if numLegos == 0:
        return 0, empty(address), ""

    for i: uint256 in range(1, numLegos, bound=max_value(uint256)):
        legoInfo: AddressInfo = staticcall Registry(legoBook).getAddrInfo(i)
        if not staticcall LegoPartner(legoInfo.addr).isYieldLego():
            continue

        if staticcall YieldLego(legoInfo.addr).isLegoAsset(_vaultToken):
            return i, legoInfo.addr, legoInfo.description

    return 0, empty(address), ""


# get underlying data (given an underlying asset, underlying amount)


@view
@external
def getUnderlyingData(_asset: address, _amount: uint256, _legoBook: address = empty(address)) -> UnderlyingData:
    if _amount == 0 or _asset == empty(address):
        return empty(UnderlyingData)

    legoBook: address = _legoBook
    if _legoBook == empty(address):
        legoBook = addys._getLegoBookAddr()

    numLegos: uint256 = staticcall Registry(legoBook).numAddrs()
    if numLegos == 0:
        return empty(UnderlyingData)

    appraiser: address = addys._getAppraiserAddr()
    for i: uint256 in range(1, numLegos, bound=max_value(uint256)):
        legoInfo: AddressInfo = staticcall Registry(legoBook).getAddrInfo(i)
        if not staticcall LegoPartner(legoInfo.addr).isYieldLego():
            continue

        asset: address = empty(address)
        underlyingAmount: uint256 = 0
        usdValue: uint256 = 0
        asset, underlyingAmount, usdValue = staticcall YieldLego(legoInfo.addr).getUnderlyingData(_asset, _amount, appraiser)
        if asset != empty(address):
            return UnderlyingData(
                asset = asset,
                amount = underlyingAmount,
                usdValue = usdValue,
                legoId = i,
                legoAddr = legoInfo.addr,
                legoDesc = legoInfo.description,
            )

    # fallback to appraiser
    return UnderlyingData(
        asset = _asset,
        amount = _amount,
        usdValue = staticcall Appraiser(appraiser).getUsdValue(_asset, _amount),
        legoId = 0,
        legoAddr = empty(address),
        legoDesc = "",
    )


###############
# Dex Helpers #
###############


# get routes and swap instructions (amountIn as input)


@external
def getRoutesAndSwapInstructionsAmountOut(
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256,
    _slippage: uint256,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS] = [],
) -> DynArray[SwapInstruction, MAX_SWAP_INSTRUCTIONS]:
    routes: DynArray[SwapRoute, MAX_ROUTES] = self._getBestSwapRoutesAmountOut(_tokenIn, _tokenOut, _amountIn, _includeLegoIds)
    return self._prepareSwapInstructionsAmountOut(_slippage, routes)


# get routes and swap instructions (amountOut as input)


@external
def getRoutesAndSwapInstructionsAmountIn(
    _tokenIn: address,
    _tokenOut: address,
    _amountOut: uint256,
    _amountInAvailable: uint256,
    _slippage: uint256,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS] = [],
) -> DynArray[SwapInstruction, MAX_SWAP_INSTRUCTIONS]:
    routes: DynArray[SwapRoute, MAX_ROUTES] = self._getBestSwapRoutesAmountIn(_tokenIn, _tokenOut, _amountOut, _includeLegoIds)
    if len(routes) == 0:
        return []

    # let's re-run the routes with amountIn as input (this is more accurate, for example, Aerodrome doesn't have getAmountIn for stable pools
    amountIn: uint256 = min(_amountInAvailable, routes[0].amountIn)
    routes = self._getBestSwapRoutesAmountOut(_tokenIn, _tokenOut, amountIn, _includeLegoIds)
    return self._prepareSwapInstructionsAmountOut(_slippage, routes)


########################
# Dex: Swap Amount Out #
########################


# prepare swap instructions (amountIn as input)


@external
def prepareSwapInstructionsAmountOut(_slippage: uint256, _routes: DynArray[SwapRoute, MAX_ROUTES]) -> DynArray[SwapInstruction, MAX_SWAP_INSTRUCTIONS]:
    return self._prepareSwapInstructionsAmountOut(_slippage, _routes)


@internal
def _prepareSwapInstructionsAmountOut(_slippage: uint256, _routes: DynArray[SwapRoute, MAX_ROUTES]) -> DynArray[SwapInstruction, MAX_SWAP_INSTRUCTIONS]:
    if len(_routes) == 0:
        return []

    instructions: DynArray[SwapInstruction, MAX_SWAP_INSTRUCTIONS] = []

    # start with first route
    prevRoute: SwapRoute = _routes[0]
    prevInstruction: SwapInstruction = self._createNewInstruction(prevRoute, _slippage)

    # iterate thru swap routes, skip first
    for i: uint256 in range(1, len(_routes), bound=MAX_ROUTES):
        newRoute: SwapRoute = _routes[i]
        assert prevRoute.tokenOut == newRoute.tokenIn # dev: invalid route

        # add to previous instruction
        if prevRoute.legoId == newRoute.legoId:
            prevInstruction.minAmountOut = newRoute.amountOut * (HUNDRED_PERCENT - _slippage) // HUNDRED_PERCENT
            prevInstruction.tokenPath.append(newRoute.tokenOut)
            prevInstruction.poolPath.append(newRoute.pool)
        
        # create new instruction
        else:
            instructions.append(prevInstruction)
            prevInstruction = self._createNewInstruction(newRoute, _slippage)

        # set previous item
        prevRoute = newRoute

    # add last instruction
    instructions.append(prevInstruction)
    return instructions


@view
@internal
def _createNewInstruction(_route: SwapRoute, _slippage: uint256) -> SwapInstruction:
    return SwapInstruction(
        legoId=_route.legoId,
        amountIn=_route.amountIn,
        minAmountOut=_route.amountOut * (HUNDRED_PERCENT - _slippage) // HUNDRED_PERCENT,
        tokenPath=[_route.tokenIn, _route.tokenOut],
        poolPath=[_route.pool],
    )


# best swap routes (amountIn as input)


@external
def getBestSwapRoutesAmountOut(
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS] = [],
) -> DynArray[SwapRoute, MAX_ROUTES]:
    return self._getBestSwapRoutesAmountOut(_tokenIn, _tokenOut, _amountIn, _includeLegoIds)


@internal
def _getBestSwapRoutesAmountOut(
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS],
) -> DynArray[SwapRoute, MAX_ROUTES]:
    if _tokenIn == _tokenOut or _amountIn == 0 or empty(address) in [_tokenIn, _tokenOut]:
        return []

    bestSwapRoutes: DynArray[SwapRoute, MAX_ROUTES] = []

    # required data
    legoBook: address = addys._getLegoBookAddr()
    numLegos: uint256 = staticcall Registry(legoBook).numAddrs()
    routerTokenA: address = ROUTER_TOKENA
    routerTokenB: address = ROUTER_TOKENB

    # direct swap route
    directSwapRoute: SwapRoute = self._getBestSwapAmountOutSinglePool(_tokenIn, _tokenOut, _amountIn, numLegos, legoBook, _includeLegoIds)

    # check with router pools
    withRouterHopAmountOut: uint256 = 0
    withHopRoutes: DynArray[SwapRoute, MAX_ROUTES] = []
    withRouterHopAmountOut, withHopRoutes = self._getBestSwapAmountOutWithRouterPool(routerTokenA, routerTokenB, _tokenIn, _tokenOut, _amountIn, numLegos, legoBook, _includeLegoIds)

    # compare direct swap route with hop routes
    if directSwapRoute.amountOut > withRouterHopAmountOut:
        bestSwapRoutes = [directSwapRoute]

    # update router token pool (if possible)
    elif withRouterHopAmountOut != 0:
        bestSwapRoutes = withHopRoutes

    return bestSwapRoutes


# check various routes via core router pools


@external
def getBestSwapAmountOutWithRouterPool(
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS] = [],
) -> (uint256, DynArray[SwapRoute, MAX_ROUTES]):
    legoBook: address = addys._getLegoBookAddr()
    numLegos: uint256 = staticcall Registry(legoBook).numAddrs()
    return self._getBestSwapAmountOutWithRouterPool(ROUTER_TOKENA, ROUTER_TOKENB, _tokenIn, _tokenOut, _amountIn, numLegos, legoBook, _includeLegoIds)


@internal
def _getBestSwapAmountOutWithRouterPool(
    _routerTokenA: address,
    _routerTokenB: address,
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256,
    _numLegos: uint256,
    _legoRegistry: address,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS],
) -> (uint256, DynArray[SwapRoute, MAX_ROUTES]):

    # nothing to do, already have router pool to use
    if self._isRouterPool(_tokenIn, _tokenOut, _routerTokenA, _routerTokenB):
        return 0, []

    isMultiHop: bool = False
    finalAmountOut: uint256 = 0
    bestSwapRoutes: DynArray[SwapRoute, MAX_ROUTES] = []
    firstRoute: SwapRoute = empty(SwapRoute)
    secondRoute: SwapRoute = empty(SwapRoute)

    # usdc -> weth -> tokenOut
    if _tokenIn == _routerTokenA:
        firstRoute = self._getSwapAmountOutViaRouterPool(_routerTokenA, _routerTokenB, _amountIn, _numLegos, _legoRegistry, _includeLegoIds)
        if firstRoute.amountOut != 0:
            secondRoute = self._getBestSwapAmountOutSinglePool(_routerTokenB, _tokenOut, firstRoute.amountOut, _numLegos, _legoRegistry, _includeLegoIds)

    # tokenIn -> weth -> usdc
    elif _tokenOut == _routerTokenA:
        firstRoute = self._getBestSwapAmountOutSinglePool(_tokenIn, _routerTokenB, _amountIn, _numLegos, _legoRegistry, _includeLegoIds)
        if firstRoute.amountOut != 0:
            secondRoute = self._getSwapAmountOutViaRouterPool(_routerTokenB, _routerTokenA, firstRoute.amountOut, _numLegos, _legoRegistry, _includeLegoIds)

    # weth -> usdc -> tokenOut
    elif _tokenIn == _routerTokenB:
        firstRoute = self._getSwapAmountOutViaRouterPool(_routerTokenB, _routerTokenA, _amountIn, _numLegos, _legoRegistry, _includeLegoIds)
        if firstRoute.amountOut != 0:
            secondRoute = self._getBestSwapAmountOutSinglePool(_routerTokenA, _tokenOut, firstRoute.amountOut, _numLegos, _legoRegistry, _includeLegoIds)

    # tokenIn -> usdc -> weth
    elif _tokenOut == _routerTokenB:
        firstRoute = self._getBestSwapAmountOutSinglePool(_tokenIn, _routerTokenA, _amountIn, _numLegos, _legoRegistry, _includeLegoIds)
        if firstRoute.amountOut != 0:
            secondRoute = self._getSwapAmountOutViaRouterPool(_routerTokenA, _routerTokenB, firstRoute.amountOut, _numLegos, _legoRegistry, _includeLegoIds)

    # let's try multi hop routes
    else:
        isMultiHop = True

        # router token A as starting point
        viaRouterTokenAAmountOut: uint256 = 0
        viaRouterTokenARoutes: DynArray[SwapRoute, MAX_ROUTES] = []
        viaRouterTokenAAmountOut, viaRouterTokenARoutes = self._checkRouterPoolForMiddleSwapAmountOut(_routerTokenA, _routerTokenB, _tokenIn, _tokenOut, _amountIn, _numLegos, _legoRegistry, _includeLegoIds)

        # router token B as starting point
        viaRouterTokenBAmountOut: uint256 = 0
        viaRouterTokenBRoutes: DynArray[SwapRoute, MAX_ROUTES] = []
        viaRouterTokenBAmountOut, viaRouterTokenBRoutes = self._checkRouterPoolForMiddleSwapAmountOut(_routerTokenB, _routerTokenA, _tokenIn, _tokenOut, _amountIn, _numLegos, _legoRegistry, _includeLegoIds)

        # compare
        if viaRouterTokenAAmountOut > viaRouterTokenBAmountOut:
            finalAmountOut = viaRouterTokenAAmountOut
            bestSwapRoutes = viaRouterTokenARoutes
        elif viaRouterTokenBAmountOut != 0:
            finalAmountOut = viaRouterTokenBAmountOut
            bestSwapRoutes = viaRouterTokenBRoutes

    if not isMultiHop:
        finalAmountOut = secondRoute.amountOut
        bestSwapRoutes = [firstRoute, secondRoute]

    return finalAmountOut, bestSwapRoutes


@internal
def _checkRouterPoolForMiddleSwapAmountOut(
    _firstRouterTokenHop: address,
    _secondRouterTokenHop: address,
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256,
    _numLegos: uint256,
    _legoRegistry: address,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS],
) -> (uint256, DynArray[SwapRoute, MAX_ROUTES]):
    secondHopToTokenOut: SwapRoute = empty(SwapRoute)

    # tokenIn -> first Router Token
    tokenInToFirstHop: SwapRoute = self._getBestSwapAmountOutSinglePool(_tokenIn, _firstRouterTokenHop, _amountIn, _numLegos, _legoRegistry, _includeLegoIds)
    if tokenInToFirstHop.amountOut == 0:
        return 0, []

    # first Router Token -> tokenOut
    firstHopToTokenOut: SwapRoute = self._getBestSwapAmountOutSinglePool(_firstRouterTokenHop, _tokenOut, tokenInToFirstHop.amountOut, _numLegos, _legoRegistry, _includeLegoIds)

    # first Router Token -> second Router Token -- this will always happen in router pools (i.e. usdc <-> weth)
    firstHopToSecondHop: SwapRoute = self._getSwapAmountOutViaRouterPool(_firstRouterTokenHop, _secondRouterTokenHop, tokenInToFirstHop.amountOut, _numLegos, _legoRegistry, _includeLegoIds)

    # second Router Token -> tokenOut
    if firstHopToSecondHop.amountOut != 0:
        secondHopToTokenOut = self._getBestSwapAmountOutSinglePool(_secondRouterTokenHop, _tokenOut, firstHopToSecondHop.amountOut, _numLegos, _legoRegistry, _includeLegoIds)

    # compare routes
    if firstHopToTokenOut.amountOut > secondHopToTokenOut.amountOut:
        return firstHopToTokenOut.amountOut, [tokenInToFirstHop, firstHopToTokenOut]
    elif secondHopToTokenOut.amountOut != 0:
        return secondHopToTokenOut.amountOut, [tokenInToFirstHop, firstHopToSecondHop, secondHopToTokenOut]
    return 0, []


# single pool


@external
def getBestSwapAmountOutSinglePool(
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS] = [],
) -> SwapRoute:
    legoBook: address = addys._getLegoBookAddr()
    numLegos: uint256 = staticcall Registry(legoBook).numAddrs()
    return self._getBestSwapAmountOutSinglePool(_tokenIn, _tokenOut, _amountIn, numLegos, legoBook, _includeLegoIds)


@internal
def _getBestSwapAmountOutSinglePool(
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256,
    _numLegos: uint256,
    _legoRegistry: address,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS],
) -> SwapRoute:

    bestRoute: SwapRoute = SwapRoute(
        legoId=0,
        pool=empty(address),
        tokenIn=_tokenIn,
        tokenOut=_tokenOut,
        amountIn=_amountIn,
        amountOut=0,
    )

    if _numLegos == 0:
        return bestRoute

    shouldCheckLegoIds: bool = len(_includeLegoIds) != 0
    for i: uint256 in range(1, _numLegos, bound=max_value(uint256)):

        # skip if we should check lego ids and it's not in the list
        if shouldCheckLegoIds and i not in _includeLegoIds:
            continue

        # get lego addr
        legoAddr: address = staticcall Registry(_legoRegistry).getAddr(i)
        if not staticcall LegoPartner(legoAddr).isDexLego():
            continue

        pool: address = empty(address)
        amountOut: uint256 = 0
        if i in [UNISWAP_V3_ID, AERODROME_SLIPSTREAM_ID]:
            pool, amountOut = extcall LegoDexNonStandard(legoAddr).getBestSwapAmountOut(_tokenIn, _tokenOut, _amountIn)
        else:
            pool, amountOut = staticcall DexLego(legoAddr).getBestSwapAmountOut(_tokenIn, _tokenOut, _amountIn)

        # compare best
        if pool != empty(address) and amountOut > bestRoute.amountOut:
            bestRoute.pool = pool
            bestRoute.amountOut = amountOut
            bestRoute.legoId = i

    return bestRoute


# router pool only


@external
def getSwapAmountOutViaRouterPool(
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS] = [],
) -> SwapRoute:
    legoBook: address = addys._getLegoBookAddr()
    numLegos: uint256 = staticcall Registry(legoBook).numAddrs()
    return self._getSwapAmountOutViaRouterPool(_tokenIn, _tokenOut, _amountIn, numLegos, legoBook, _includeLegoIds)


@internal
def _getSwapAmountOutViaRouterPool(
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256,
    _numLegos: uint256,
    _legoRegistry: address,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS],
) -> SwapRoute:

    # NOTE: _tokenIn and _tokenOut need to be ROUTER_TOKENA/ROUTER_TOKENB -- in the `getCoreRouterPool()` pool

    bestRoute: SwapRoute = SwapRoute(
        legoId=0,
        pool=empty(address),
        tokenIn=_tokenIn,
        tokenOut=_tokenOut,
        amountIn=_amountIn,
        amountOut=0,
    )

    if _numLegos == 0:
        return bestRoute

    shouldCheckLegoIds: bool = len(_includeLegoIds) != 0
    for i: uint256 in range(1, _numLegos, bound=max_value(uint256)):

        # skip if we should check lego ids and it's not in the list
        if shouldCheckLegoIds and i not in _includeLegoIds:
            continue

        # get lego addr
        legoAddr: address = staticcall Registry(_legoRegistry).getAddr(i)
        if not staticcall LegoPartner(legoAddr).isDexLego():
            continue

        pool: address = staticcall DexLego(legoAddr).getCoreRouterPool()
        if pool == empty(address):
            continue
        
        amountOut: uint256 = 0
        if i in [UNISWAP_V3_ID, AERODROME_SLIPSTREAM_ID]:
            amountOut = extcall LegoDexNonStandard(legoAddr).getSwapAmountOut(pool, _tokenIn, _tokenOut, _amountIn)
        else:
            amountOut = staticcall DexLego(legoAddr).getSwapAmountOut(pool, _tokenIn, _tokenOut, _amountIn)
        
        # compare best
        if amountOut > bestRoute.amountOut:
            bestRoute.pool = pool
            bestRoute.amountOut = amountOut
            bestRoute.legoId = i

    return bestRoute


#######################
# Dex: Swap Amount In #
#######################


# best swap routes (amountOut as input)


@external
def getBestSwapRoutesAmountIn(
    _tokenIn: address,
    _tokenOut: address,
    _amountOut: uint256,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS] = [],
) -> DynArray[SwapRoute, MAX_ROUTES]:
    return self._getBestSwapRoutesAmountIn(_tokenIn, _tokenOut, _amountOut, _includeLegoIds)


@internal
def _getBestSwapRoutesAmountIn(
    _tokenIn: address,
    _tokenOut: address,
    _amountOut: uint256,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS],
) -> DynArray[SwapRoute, MAX_ROUTES]:
    if _tokenIn == _tokenOut or _amountOut == 0 or empty(address) in [_tokenIn, _tokenOut]:
        return []

    bestSwapRoutes: DynArray[SwapRoute, MAX_ROUTES] = []

    # required data
    legoBook: address = addys._getLegoBookAddr()
    numLegos: uint256 = staticcall Registry(legoBook).numAddrs()
    routerTokenA: address = ROUTER_TOKENA
    routerTokenB: address = ROUTER_TOKENB

    # direct swap route
    directSwapRoute: SwapRoute = self._getBestSwapAmountInSinglePool(_tokenIn, _tokenOut, _amountOut, numLegos, legoBook, _includeLegoIds)

    # check with router pools
    withRouterHopAmountIn: uint256 = 0
    withHopRoutes: DynArray[SwapRoute, MAX_ROUTES] = []
    withRouterHopAmountIn, withHopRoutes = self._getBestSwapAmountInWithRouterPool(routerTokenA, routerTokenB, _tokenIn, _tokenOut, _amountOut, numLegos, legoBook, _includeLegoIds)

    # compare direct swap route with hop routes
    if directSwapRoute.amountIn < withRouterHopAmountIn:
        bestSwapRoutes = [directSwapRoute]

    # update router token pool (if possible)
    elif withRouterHopAmountIn != max_value(uint256):
        bestSwapRoutes = withHopRoutes

    return bestSwapRoutes


# check various routes via core router pools


@external
def getBestSwapAmountInWithRouterPool(
    _tokenIn: address,
    _tokenOut: address,
    _amountOut: uint256,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS] = [],
) -> (uint256, DynArray[SwapRoute, MAX_ROUTES]):
    legoBook: address = addys._getLegoBookAddr()
    numLegos: uint256 = staticcall Registry(legoBook).numAddrs()
    return self._getBestSwapAmountInWithRouterPool(ROUTER_TOKENA, ROUTER_TOKENB, _tokenIn, _tokenOut, _amountOut, numLegos, legoBook, _includeLegoIds)


@internal
def _getBestSwapAmountInWithRouterPool(
    _routerTokenA: address,
    _routerTokenB: address,
    _tokenIn: address,
    _tokenOut: address,
    _amountOut: uint256,
    _numLegos: uint256,
    _legoRegistry: address,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS],
) -> (uint256, DynArray[SwapRoute, MAX_ROUTES]):

    # nothing to do, already have router pool to use
    if self._isRouterPool(_tokenIn, _tokenOut, _routerTokenA, _routerTokenB):
        return max_value(uint256), []

    isMultiHop: bool = False
    finalAmountIn: uint256 = max_value(uint256)
    bestSwapRoutes: DynArray[SwapRoute, MAX_ROUTES] = []
    firstRoute: SwapRoute = empty(SwapRoute)
    secondRoute: SwapRoute = empty(SwapRoute)

    # usdc -> weth -> tokenOut
    if _tokenIn == _routerTokenA:
        secondRoute = self._getBestSwapAmountInSinglePool(_routerTokenB, _tokenOut, _amountOut, _numLegos, _legoRegistry, _includeLegoIds)
        if secondRoute.amountIn != max_value(uint256):
            firstRoute = self._getSwapAmountInViaRouterPool(_routerTokenA, _routerTokenB, secondRoute.amountIn, _numLegos, _legoRegistry, _includeLegoIds)

    # tokenIn -> weth -> usdc
    elif _tokenOut == _routerTokenA:
        secondRoute = self._getSwapAmountInViaRouterPool(_routerTokenB, _routerTokenA, _amountOut, _numLegos, _legoRegistry, _includeLegoIds)
        if secondRoute.amountIn != max_value(uint256):
            firstRoute = self._getBestSwapAmountInSinglePool(_tokenIn, _routerTokenB, secondRoute.amountIn, _numLegos, _legoRegistry, _includeLegoIds)

    # weth -> usdc -> tokenOut
    elif _tokenIn == _routerTokenB:
        secondRoute = self._getBestSwapAmountInSinglePool(_routerTokenA, _tokenOut, _amountOut, _numLegos, _legoRegistry, _includeLegoIds)
        if secondRoute.amountIn != max_value(uint256):
            firstRoute = self._getSwapAmountInViaRouterPool(_routerTokenB, _routerTokenA, secondRoute.amountIn, _numLegos, _legoRegistry, _includeLegoIds)

    # tokenIn -> usdc -> weth
    elif _tokenOut == _routerTokenB:
        secondRoute = self._getSwapAmountInViaRouterPool(_routerTokenA, _routerTokenB, _amountOut, _numLegos, _legoRegistry, _includeLegoIds)
        if secondRoute.amountIn != max_value(uint256):
            firstRoute = self._getBestSwapAmountInSinglePool(_tokenIn, _routerTokenA, secondRoute.amountIn, _numLegos, _legoRegistry, _includeLegoIds)

    # let's try multi hop routes
    else:
        isMultiHop = True

        # router token A as starting point
        viaRouterTokenAAmountIn: uint256 = 0
        viaRouterTokenARoutes: DynArray[SwapRoute, MAX_ROUTES] = []
        viaRouterTokenAAmountIn, viaRouterTokenARoutes = self._checkRouterPoolForMiddleSwapAmountIn(_routerTokenA, _routerTokenB, _tokenIn, _tokenOut, _amountOut, _numLegos, _legoRegistry, _includeLegoIds)

        # router token B as starting point
        viaRouterTokenBAmountIn: uint256 = 0
        viaRouterTokenBRoutes: DynArray[SwapRoute, MAX_ROUTES] = []
        viaRouterTokenBAmountIn, viaRouterTokenBRoutes = self._checkRouterPoolForMiddleSwapAmountIn(_routerTokenB, _routerTokenA, _tokenIn, _tokenOut, _amountOut, _numLegos, _legoRegistry, _includeLegoIds)

        # compare
        if viaRouterTokenAAmountIn < viaRouterTokenBAmountIn:
            finalAmountIn = viaRouterTokenAAmountIn
            bestSwapRoutes = viaRouterTokenARoutes
        elif viaRouterTokenBAmountIn != max_value(uint256):
            finalAmountIn = viaRouterTokenBAmountIn
            bestSwapRoutes = viaRouterTokenBRoutes

    if not isMultiHop:
        finalAmountIn = firstRoute.amountIn
        bestSwapRoutes = [firstRoute, secondRoute]

    return finalAmountIn, bestSwapRoutes


@internal
def _checkRouterPoolForMiddleSwapAmountIn(
    _firstRouterToken: address,
    _secondRouterToken: address,
    _tokenIn: address,
    _tokenOut: address,
    _amountOut: uint256,
    _numLegos: uint256,
    _legoRegistry: address,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS],
) -> (uint256, DynArray[SwapRoute, MAX_ROUTES]):
    tokenInToFirstHop: SwapRoute = empty(SwapRoute)
    tokenInToFirstHop.amountIn = max_value(uint256)

    # second Router Token -> tokenOut
    secondHopToTokenOut: SwapRoute = self._getBestSwapAmountInSinglePool(_secondRouterToken, _tokenOut, _amountOut, _numLegos, _legoRegistry, _includeLegoIds)
    if secondHopToTokenOut.amountIn == max_value(uint256):
        return max_value(uint256), []

    # tokenIn -> second Router Token
    tokenInToSecondHop: SwapRoute = self._getBestSwapAmountInSinglePool(_tokenIn, _secondRouterToken, secondHopToTokenOut.amountIn, _numLegos, _legoRegistry, _includeLegoIds)

    # first Router Token -> second Router Token -- this will always happen in router pools (i.e. usdc <-> weth)
    firstHopToSecondHop: SwapRoute = self._getSwapAmountInViaRouterPool(_firstRouterToken, _secondRouterToken, secondHopToTokenOut.amountIn, _numLegos, _legoRegistry, _includeLegoIds)

    # tokenIn -> first Router Token
    if firstHopToSecondHop.amountIn != max_value(uint256):
        tokenInToFirstHop = self._getBestSwapAmountInSinglePool(_tokenIn, _firstRouterToken, firstHopToSecondHop.amountIn, _numLegos, _legoRegistry, _includeLegoIds)

    # compare routes
    if tokenInToSecondHop.amountIn < tokenInToFirstHop.amountIn:
        return tokenInToSecondHop.amountIn, [tokenInToSecondHop, secondHopToTokenOut]
    elif tokenInToFirstHop.amountIn != max_value(uint256):
        return tokenInToFirstHop.amountIn, [tokenInToFirstHop, firstHopToSecondHop, secondHopToTokenOut]
    return max_value(uint256), []


# single pool


@external
def getBestSwapAmountInSinglePool(
    _tokenIn: address,
    _tokenOut: address,
    _amountOut: uint256,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS] = [],
) -> SwapRoute:
    legoBook: address = addys._getLegoBookAddr()
    numLegos: uint256 = staticcall Registry(legoBook).numAddrs()
    return self._getBestSwapAmountInSinglePool(_tokenIn, _tokenOut, _amountOut, numLegos, legoBook, _includeLegoIds)


@internal
def _getBestSwapAmountInSinglePool(
    _tokenIn: address,
    _tokenOut: address,
    _amountOut: uint256,
    _numLegos: uint256,
    _legoRegistry: address,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS],
) -> SwapRoute:

    bestRoute: SwapRoute = SwapRoute(
        legoId=0,
        pool=empty(address),
        tokenIn=_tokenIn,
        tokenOut=_tokenOut,
        amountIn=max_value(uint256),
        amountOut=_amountOut,
    )

    if _numLegos == 0:
        return bestRoute

    shouldCheckLegoIds: bool = len(_includeLegoIds) != 0
    for i: uint256 in range(1, _numLegos, bound=max_value(uint256)):

        # skip if we should check lego ids and it's not in the list
        if shouldCheckLegoIds and i not in _includeLegoIds:
            continue

        # get lego addr
        legoAddr: address = staticcall Registry(_legoRegistry).getAddr(i)
        if not staticcall LegoPartner(legoAddr).isDexLego():
            continue

        pool: address = empty(address)
        amountIn: uint256 = max_value(uint256)
        if i in [UNISWAP_V3_ID, AERODROME_SLIPSTREAM_ID]:
            pool, amountIn = extcall LegoDexNonStandard(legoAddr).getBestSwapAmountIn(_tokenIn, _tokenOut, _amountOut)
        else:
            pool, amountIn = staticcall DexLego(legoAddr).getBestSwapAmountIn(_tokenIn, _tokenOut, _amountOut)

        # compare best
        if pool != empty(address) and amountIn != 0 and amountIn < bestRoute.amountIn:
            bestRoute.pool = pool
            bestRoute.amountIn = amountIn
            bestRoute.legoId = i

    return bestRoute


# router pool only


@external
def getSwapAmountInViaRouterPool(
    _tokenIn: address,
    _tokenOut: address,
    _amountOut: uint256,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS] = [],
) -> SwapRoute:
    legoBook: address = addys._getLegoBookAddr()
    numLegos: uint256 = staticcall Registry(legoBook).numAddrs()
    return self._getSwapAmountInViaRouterPool(_tokenIn, _tokenOut, _amountOut, numLegos, legoBook, _includeLegoIds)


@internal
def _getSwapAmountInViaRouterPool(
    _tokenIn: address,
    _tokenOut: address,
    _amountOut: uint256,
    _numLegos: uint256,
    _legoRegistry: address,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS],
) -> SwapRoute:

    # NOTE: _tokenIn and _tokenOut need to be ROUTER_TOKENA/ROUTER_TOKENB -- in the `getCoreRouterPool()` pool

    bestRoute: SwapRoute = SwapRoute(
        legoId=0,
        pool=empty(address),
        tokenIn=_tokenIn,
        tokenOut=_tokenOut,
        amountIn=max_value(uint256),
        amountOut=_amountOut,
    )

    if _numLegos == 0:
        return bestRoute

    shouldCheckLegoIds: bool = len(_includeLegoIds) != 0
    for i: uint256 in range(1, _numLegos, bound=max_value(uint256)):

        # skip if we should check lego ids and it's not in the list
        if shouldCheckLegoIds and i not in _includeLegoIds:
            continue

        # get lego addr
        legoAddr: address = staticcall Registry(_legoRegistry).getAddr(i)
        if not staticcall LegoPartner(legoAddr).isDexLego():
            continue

        # get router pool
        pool: address = staticcall DexLego(legoAddr).getCoreRouterPool()
        if pool == empty(address):
            continue
        
        amountIn: uint256 = max_value(uint256)
        if i in [UNISWAP_V3_ID, AERODROME_SLIPSTREAM_ID]:
            amountIn = extcall LegoDexNonStandard(legoAddr).getSwapAmountIn(pool, _tokenIn, _tokenOut, _amountOut)
        else:
            amountIn = staticcall DexLego(legoAddr).getSwapAmountIn(pool, _tokenIn, _tokenOut, _amountOut)
        
        # compare best
        if amountIn != 0 and amountIn < bestRoute.amountIn:
            bestRoute.pool = pool
            bestRoute.amountIn = amountIn
            bestRoute.legoId = i

    return bestRoute


@view
@internal
def _isRouterPool(_tokenIn: address, _tokenOut: address, _routerTokenA: address, _routerTokenB: address) -> bool:
    return _tokenIn in [_routerTokenA, _routerTokenB] and _tokenOut in [_routerTokenA, _routerTokenB]
