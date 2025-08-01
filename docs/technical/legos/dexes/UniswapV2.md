# UniswapV2 Technical Documentation

[📄 View Source Code](../../../../contracts/legos/dexes/UniswapV2.vy)

## Overview

UniswapV2 is a DEX Lego partner that integrates the Underscore Protocol with Uniswap V2, the pioneering automated market maker (AMM) protocol. It provides comprehensive support for token swapping and liquidity management on Uniswap V2's constant product pools. The integration enables multi-hop swaps through various pool paths, efficient liquidity provision with automatic ratio management, and full compatibility with the standard Uniswap V2 router interface.

**Core Features**:
- **Multi-Hop Swaps**: Execute complex token swaps through multiple pools with automatic routing
- **Liquidity Management**: Add and remove liquidity with automatic token ratio calculation
- **Pool Discovery**: Find the best pool for any token pair through the factory contract
- **Price Calculations**: Built-in functions for calculating swap amounts and optimal liquidity ratios
- **Standard AMM Model**: Implements the classic x*y=k constant product formula with 0.3% fee

Built with modular architecture using Addys and DexLegoData modules, UniswapV2 provides seamless access to one of DeFi's most battle-tested and widely-forked AMM protocols while maintaining the security patterns and operational standards of the Underscore Protocol.

## Architecture & Modules

UniswapV2 uses a modular architecture combining address management and DEX data handling:

### Addys Module
- **Location**: `contracts/modules/Addys.vy`
- **Purpose**: Provides protocol-wide address lookups and registry access
- **Documentation**: See [Addys Technical Documentation](../../modules/Addys.md)
- **Key Features**:
  - Connection to UndyHq for protocol addresses
  - Access to Appraiser for USD valuations
  - Cached address lookups for gas efficiency

### DexLegoData Module
- **Location**: `contracts/modules/DexLegoData.vy`
- **Purpose**: Manages DEX-specific data and pause functionality
- **Documentation**: See [DexLegoData Technical Documentation](../../modules/DexLegoData.md)
- **Key Features**:
  - Pause functionality for emergency stops
  - Mini address struct management
  - Foundational DEX data structures

### Module Initialization
```vyper
initializes: addys
initializes: dld[addys := addys]
```

## System Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                        UniswapV2 Contract                          │
├────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐         ┌──────────────────────────────┐  │
│  │    Addys Module     │         │   DexLegoData Module         │  │
│  │                     │         │                              │  │
│  │ • Protocol addrs    │         │ • Pause functionality        │  │
│  │ • Registry access   │         │ • Mini address management    │  │
│  │ • Appraiser access  │         │ • DEX data structures        │  │
│  └─────────────────────┘         └──────────────────────────────┘  │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Core Capabilities                         │  │
│  │                                                              │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │  │
│  │  │   Token Swaps   │  │    Liquidity    │  │  Pool Info  │  │  │
│  │  │                 │  │   Management    │  │    Query    │  │  │
│  │  │ • Multi-hop     │  │                 │  │             │  │  │
│  │  │   routing       │  │ • Add liquidity │  │ • Best pool │  │  │
│  │  │ • Direct swaps  │  │ • Remove liq    │  │ • Reserves  │  │  │
│  │  │ • Slippage      │  │ • Auto ratios   │  │ • Pricing   │  │  │
│  │  │   protection    │  │ • LP tokens     │  │ • Quotes    │  │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                               │
                               v
┌────────────────────────────────────────────────────────────────────┐
│                    Uniswap V2 Integration                          │
│                                                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │   V2 Factory     │  │    V2 Router     │  │   V2 Pairs      │  │
│  │                  │  │                  │  │                 │  │
│  │ • Pair creation  │  │ • Add liquidity  │  │ • Token swaps   │  │
│  │ • Pair lookup    │  │ • Remove liq     │  │ • Reserves      │  │
│  │ • Fee settings   │  │ • Path routing   │  │ • LP tokens     │  │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

## Data Structures

### BestPool Struct
Contains information about the optimal pool for a token pair:
```vyper
struct BestPool:
    pool: address        # Pool contract address
    fee: uint256        # Pool fee rate (30 = 0.3%)
    liquidity: uint256  # Total liquidity (sum of reserves)
    numCoins: uint256   # Always 2 for Uniswap V2
```

### Route Struct
Defines a swap route between tokens:
```vyper
struct Route:
    from_: address      # Input token
    to: address         # Output token
    stable: bool        # Not used in V2
    factory: address    # Factory address
```

## State Variables

### Immutable Protocol Addresses
- `UNISWAP_V2_FACTORY: public(immutable(address))` - Uniswap V2 factory contract
- `UNISWAP_V2_ROUTER: public(immutable(address))` - Uniswap V2 router contract
- `coreRouterPool: public(address)` - Core routing pool for the protocol

### Constants
- `EIGHTEEN_DECIMALS: constant(uint256) = 10 ** 18` - Decimal normalization
- `MAX_TOKEN_PATH: constant(uint256) = 5` - Maximum tokens in swap path

## Constructor

### `__init__`

Initializes UniswapV2 with Underscore Protocol and Uniswap V2 connections.

```vyper
@deploy
def __init__(
    _undyHq: address,
    _uniswapV2Factory: address,
    _uniswapV2Router: address,
    _coreRouterPool: address,
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq contract address for Underscore Protocol |
| `_uniswapV2Factory` | `address` | Uniswap V2 factory contract |
| `_uniswapV2Router` | `address` | Uniswap V2 router contract |
| `_coreRouterPool` | `address` | Core routing pool address |

#### Returns

*Constructor does not return any values*

#### Access

Called only during contract deployment

#### Example Usage
```python
uniswap_v2_lego = boa.load(
    "contracts/legos/dexes/UniswapV2.vy",
    undy_hq.address,
    uniswap_factory.address,
    uniswap_router.address,
    core_pool.address
)
```

#### Notes

- Validates all addresses are non-empty
- Initializes modules without pausing

## Capability Functions

### `hasCapability`

Indicates which action types this Lego supports.

```vyper
@view
@external
def hasCapability(_action: ws.ActionType) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_action` | `ws.ActionType` | The action type to check |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if the action is supported |

#### Supported Actions

- `SWAP` - Token swapping through Uniswap V2 pools
- `ADD_LIQ` - Adding liquidity to pools
- `REMOVE_LIQ` - Removing liquidity from pools

### `getRegistries`

Returns the Uniswap V2 registry addresses.

```vyper
@view
@external
def getRegistries() -> DynArray[address, 10]:
```

#### Returns

| Type | Description |
|------|-------------|
| `DynArray[address, 10]` | Array containing factory and router addresses |

## Token Swap Functions

### `swapTokens`

Executes multi-hop token swaps through Uniswap V2 pools.

```vyper
@external
def swapTokens(
    _amountIn: uint256,
    _minAmountOut: uint256,
    _tokenPath: DynArray[address, MAX_TOKEN_PATH],
    _poolPath: DynArray[address, MAX_TOKEN_PATH - 1],
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_amountIn` | `uint256` | Amount of input token to swap |
| `_minAmountOut` | `uint256` | Minimum output amount required |
| `_tokenPath` | `DynArray[address, MAX_TOKEN_PATH]` | Ordered array of tokens in swap path |
| `_poolPath` | `DynArray[address, MAX_TOKEN_PATH - 1]` | Ordered array of pools to use |
| `_recipient` | `address` | Address to receive output tokens |
| `_miniAddys` | `ws.MiniAddys` | Mini address struct for protocol integration |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Actual input amount used |
| `uint256` | Output amount received |
| `uint256` | USD value of transaction |

#### Access

- Contract must not be paused
- Open to all callers

#### Events Emitted

- `UniswapV2Swap` - Contains swap details including tokens, amounts, USD value, and recipient

#### Example Usage
```python
# Single-hop swap USDC -> WETH
amount_in, amount_out, usd_value = uniswap_v2_lego.swapTokens(
    1000 * 10**6,  # 1000 USDC
    0.3 * 10**18,  # Min 0.3 WETH
    [usdc.address, weth.address],
    [usdc_weth_pool.address],
    user.address
)

# Multi-hop swap USDC -> WETH -> DAI
amount_in, amount_out, usd_value = uniswap_v2_lego.swapTokens(
    1000 * 10**6,
    990 * 10**18,  # Min 990 DAI
    [usdc.address, weth.address, dai.address],
    [usdc_weth_pool.address, weth_dai_pool.address],
    user.address
)
```

#### Notes

- Transfers tokens directly to pools for gas efficiency
- Validates each pool is a legitimate Uniswap V2 pair
- Refunds any unused input tokens
- Calculates USD value from input or output token

## Liquidity Management Functions

### `addLiquidity`

Adds liquidity to Uniswap V2 pools with automatic ratio calculation.

```vyper
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
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_pool` | `address` | Pool contract address |
| `_tokenA` | `address` | First token address |
| `_tokenB` | `address` | Second token address |
| `_amountA` | `uint256` | Amount of token A to add |
| `_amountB` | `uint256` | Amount of token B to add |
| `_minAmountA` | `uint256` | Minimum token A to add |
| `_minAmountB` | `uint256` | Minimum token B to add |
| `_minLpAmount` | `uint256` | Minimum LP tokens to receive (unused) |
| `_extraData` | `bytes32` | Additional data (unused) |
| `_recipient` | `address` | Address to receive LP tokens |
| `_miniAddys` | `ws.MiniAddys` | Mini address struct |

#### Returns

| Type | Description |
|------|-------------|
| `address` | LP token address (same as pool) |
| `uint256` | LP tokens received |
| `uint256` | Actual amount of token A added |
| `uint256` | Actual amount of token B added |
| `uint256` | USD value of liquidity added |

#### Access

- Contract must not be paused
- Open to all callers

#### Events Emitted

- `UniswapV2LiquidityAdded` - Contains liquidity details including tokens, amounts, LP tokens, and USD value

#### Example Usage
```python
# Add liquidity to USDC/WETH pool
lp_token, lp_amount, amount_a, amount_b, usd_value = uniswap_v2_lego.addLiquidity(
    usdc_weth_pool.address,
    usdc.address,
    weth.address,
    1000 * 10**6,   # 1000 USDC
    0.5 * 10**18,   # 0.5 WETH
    990 * 10**6,    # Min 990 USDC
    0.49 * 10**18,  # Min 0.49 WETH
    0,              # No min LP (handled by router)
    empty(bytes32),
    user.address
)
```

#### Notes

- Uses Uniswap V2 router for optimal liquidity addition
- Automatically handles token ratio adjustments
- Refunds any unused tokens
- LP token address equals pool address in V2

### `removeLiquidity`

Removes liquidity from Uniswap V2 pools.

```vyper
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
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_pool` | `address` | Pool contract address |
| `_tokenA` | `address` | First token address |
| `_tokenB` | `address` | Second token address |
| `_lpToken` | `address` | LP token address |
| `_lpAmount` | `uint256` | Amount of LP tokens to burn |
| `_minAmountA` | `uint256` | Minimum token A to receive |
| `_minAmountB` | `uint256` | Minimum token B to receive |
| `_extraData` | `bytes32` | Additional data (unused) |
| `_recipient` | `address` | Address to receive tokens |
| `_miniAddys` | `ws.MiniAddys` | Mini address struct |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Amount of token A received |
| `uint256` | Amount of token B received |
| `uint256` | LP tokens burned |
| `uint256` | USD value of liquidity removed |

#### Access

- Contract must not be paused
- Open to all callers

#### Events Emitted

- `UniswapV2LiquidityRemoved` - Contains removal details including tokens, amounts, LP tokens burned, and USD value

#### Example Usage
```python
# Remove liquidity
amount_a, amount_b, lp_burned, usd_value = uniswap_v2_lego.removeLiquidity(
    usdc_weth_pool.address,
    usdc.address,
    weth.address,
    usdc_weth_pool.address,  # LP token = pool in V2
    100 * 10**18,            # 100 LP tokens
    990 * 10**6,             # Min 990 USDC
    0.49 * 10**18,           # Min 0.49 WETH
    empty(bytes32),
    user.address
)
```

#### Notes

- Always removes liquidity proportionally
- No single-sided removal in V2
- Uses router for safe removal with slippage protection

## Pool Query Functions

### `getDeepestLiqPool`

Finds the pool for a token pair (only one pool per pair in V2).

```vyper
@view
@external
def getDeepestLiqPool(_tokenA: address, _tokenB: address) -> BestPool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_tokenA` | `address` | First token address |
| `_tokenB` | `address` | Second token address |

#### Returns

| Type | Description |
|------|-------------|
| `BestPool` | Struct containing pool info or empty if no pool exists |

#### Notes

- Returns the single pool for the pair (V2 has one pool per pair)
- Fee is always 30 (0.3% in basis points)
- Liquidity is sum of both reserves

### `getBestSwapAmountOut`

Calculates output amount for a swap.

```vyper
@view
@external
def getBestSwapAmountOut(_tokenIn: address, _tokenOut: address, _amountIn: uint256) -> (address, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_tokenIn` | `address` | Input token address |
| `_tokenOut` | `address` | Output token address |
| `_amountIn` | `uint256` | Input amount |

#### Returns

| Type | Description |
|------|-------------|
| `address` | Pool address |
| `uint256` | Expected output amount |

#### Notes

- Uses constant product formula with 0.3% fee
- Returns zero if no pool exists

### `getBestSwapAmountIn`

Calculates required input for desired output.

```vyper
@view
@external
def getBestSwapAmountIn(_tokenIn: address, _tokenOut: address, _amountOut: uint256) -> (address, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_tokenIn` | `address` | Input token address |
| `_tokenOut` | `address` | Output token address |
| `_amountOut` | `uint256` | Desired output amount |

#### Returns

| Type | Description |
|------|-------------|
| `address` | Pool address |
| `uint256` | Required input amount |

#### Notes

- Calculates using inverse of output formula
- Returns max_value if output exceeds reserves

## Utility Functions

### `getLpToken` / `getPoolForLpToken`

Pool and LP token utilities (in V2, they're the same).

```vyper
@view
@external
def getLpToken(_pool: address) -> address:
    return _pool  # LP token is the pool

@view
@external  
def getPoolForLpToken(_lpToken: address) -> address:
    return _lpToken  # Pool is the LP token
```

### `getAddLiqAmountsIn`

Calculates optimal amounts for adding liquidity.

```vyper
@view
@external
def getAddLiqAmountsIn(
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _availAmountA: uint256,
    _availAmountB: uint256,
) -> (uint256, uint256, uint256):
```

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Optimal amount of token A |
| `uint256` | Optimal amount of token B |
| `uint256` | Always 0 (LP calculation not included) |

#### Notes

- Calculates amounts to maintain pool ratio
- Uses quote function to determine optimal split

### `getRemoveLiqAmountsOut`

Estimates output amounts for removing liquidity.

```vyper
@view
@external
def getRemoveLiqAmountsOut(
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _lpAmount: uint256,
) -> (uint256, uint256):
```

#### Notes

- Calculates proportional share based on LP tokens
- Always returns both tokens (no single-sided removal)

### `getCoreRouterPool`

Returns the core routing pool address.

```vyper
@view
@external
def getCoreRouterPool() -> address:
    return self.coreRouterPool
```

### `getPriceUnsafe`

Gets token price using pool reserves and external price feed.

```vyper
@view
@external
def getPriceUnsafe(_pool: address, _targetToken: address, _appraiser: address = empty(address)) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_pool` | `address` | Pool to get price from |
| `_targetToken` | `address` | Token to price |
| `_appraiser` | `address` | Optional appraiser address |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Token price in 18 decimals |

#### Notes

- Requires price feed for the other token in pair
- Adjusts for decimal differences between tokens
- Returns 0 if no price feed available

## Internal Functions

### `_swapTokensInPool`

Executes a single swap within a pool.

```vyper
@internal
def _swapTokensInPool(
    _pool: address,
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256,
    _recipient: address,
    _uniswapV2Factory: address,
) -> uint256:
```

#### Logic

1. Validates tokens are in the pool
2. Verifies pool through factory
3. Calculates output amount
4. Executes low-level swap call

### `_getAmountOut`

Calculates output using constant product formula.

```vyper
@view
@internal
def _getAmountOut(
    _pool: address,
    _zeroForOne: bool,
    _amountIn: uint256,
) -> uint256:
```

#### Formula

```
amountOut = (amountIn * 997 * reserveOut) / ((reserveIn * 1000) + (amountIn * 997))
```

### `_getAmountIn`

Calculates required input for desired output.

```vyper
@view
@internal
def _getAmountIn(_pool: address, _zeroForOne: bool, _amountOut: uint256) -> uint256:
```

#### Formula

```
amountIn = ((reserveIn * amountOut * 1000) / ((reserveOut - amountOut) * 997)) + 1
```

### `_getReserves`

Gets pool reserves in correct order.

```vyper
@view
@internal
def _getReserves(_pool: address, _isTokenAZeroIndex: bool) -> (uint256, uint256):
```

### `_quote`

Calculates proportional amount for liquidity.

```vyper
@view
@internal
def _quote(_amountA: uint256, _reserveA: uint256, _reserveB: uint256) -> uint256:
    return (_amountA * _reserveB) // _reserveA
```

### `_getUsdValue`

Calculates total USD value for two tokens.

```vyper
@internal
def _getUsdValue(
    _tokenA: address,
    _amountA: uint256,
    _tokenB: address,
    _amountB: uint256,
    _miniAddys: ws.MiniAddys,
) -> uint256:
```

## Unimplemented Functions

UniswapV2 includes placeholder implementations for unsupported functions:

- Yield: `depositForYield()`, `withdrawFromYield()`
- Mint/Redeem: `mintOrRedeemAsset()`, `confirmMintOrRedeemAsset()`
- Lending: `addCollateral()`, `removeCollateral()`, `borrow()`, `repayDebt()`
- Rewards: `claimRewards()`
- Concentrated Liquidity: `addLiquidityConcentrated()`, `removeLiquidityConcentrated()`
- Other: `getAccessForLego()`, `getPricePerShare()`, `getPrice()`

All return zero values or empty results.

## Security Considerations

### Pool Validation
- All pools verified through factory lookup
- Token order validation before swaps
- Prevents interactions with fake pools

### Token Handling
- Direct transfers to pools (no approval needed for swaps)
- Approval management for liquidity operations
- Automatic approval reset after operations
- Refund mechanism for unused tokens

### Slippage Protection
- Minimum output amounts enforced on swaps
- Minimum token amounts on liquidity operations
- Router handles optimal liquidity ratios

## Integration Patterns

### Swap Workflow
```python
# 1. Find pool and calculate output
pool, expected_out = uniswap_v2_lego.getBestSwapAmountOut(
    token_in.address,
    token_out.address,
    swap_amount
)

# 2. Execute swap with slippage protection
amount_in, amount_out, usd_value = user_wallet.swapTokens([{
    'legoId': UNISWAP_V2_LEGO_ID,
    'amountIn': swap_amount,
    'minAmountOut': int(expected_out * 0.995),  # 0.5% slippage
    'tokenPath': [token_in.address, token_out.address],
    'poolPath': [pool]
}])
```

### Liquidity Workflow
```python
# 1. Get optimal amounts for current pool ratio
amount_a, amount_b, _ = uniswap_v2_lego.getAddLiqAmountsIn(
    pool.address,
    token_a.address,
    token_b.address,
    available_a,
    available_b
)

# 2. Add liquidity
lp_token, lp_received, actual_a, actual_b, usd = user_wallet.addLiquidity(
    UNISWAP_V2_LEGO_ID,
    pool.address,
    token_a.address,
    token_b.address,
    amount_a,
    amount_b,
    int(amount_a * 0.99),    # 1% slippage
    int(amount_b * 0.99),    # 1% slippage
    0  # Router handles min LP
)

# 3. Check removal amounts
out_a, out_b = uniswap_v2_lego.getRemoveLiqAmountsOut(
    pool.address,
    token_a.address,
    token_b.address,
    lp_amount
)

# 4. Remove liquidity
amount_a_out, amount_b_out, lp_burned, usd = user_wallet.removeLiquidity(
    UNISWAP_V2_LEGO_ID,
    pool.address,
    token_a.address,
    token_b.address,
    pool.address,  # LP token = pool
    lp_amount,
    int(out_a * 0.99),  # 1% slippage
    int(out_b * 0.99)
)
```

### Multi-Hop Swap Pattern
```python
# Complex route: USDC -> WETH -> WBTC -> DAI
token_path = [usdc.address, weth.address, wbtc.address, dai.address]
pool_path = [usdc_weth_pool, weth_wbtc_pool, wbtc_dai_pool]

# Calculate minimum output through the path
# (In production, calculate based on each hop)
min_output = calculate_multi_hop_output(token_path, pool_path, input_amount)

# Execute multi-hop swap
amount_in, amount_out, usd_value = user_wallet.swapTokens([{
    'legoId': UNISWAP_V2_LEGO_ID,
    'amountIn': input_amount,
    'minAmountOut': int(min_output * 0.97),  # 3% total slippage
    'tokenPath': token_path,
    'poolPath': pool_path
}])
```

## Testing

For comprehensive test examples, see: [`tests/legos/dexes/`](../../../../tests/legos/dexes/)