# AeroClassic Technical Documentation

[📄 View Source Code](../../../../contracts/legos/dexes/AeroClassic.vy)

## Overview

AeroClassic is a DEX Lego partner that integrates the Underscore Protocol with Aerodrome Finance's Classic AMM pools. It provides token swapping and liquidity management capabilities for both stable and volatile pairs, enabling users to interact with Aerodrome's liquidity pools through their UserWallet contracts. The integration supports multi-hop swaps, optimal pool selection, and comprehensive liquidity operations.

**Core Features**:
- **Token Swaps**: Multi-hop swaps through Aerodrome pools with automatic route optimization
- **Liquidity Management**: Add/remove liquidity for both stable and volatile pairs
- **Pool Discovery**: Automatic selection of optimal pools based on liquidity depth
- **Price Queries**: On-chain price discovery through pool reserves

Built with modular architecture using Addys and DexLegoData modules, AeroClassic provides seamless access to Aerodrome's decentralized exchange infrastructure while maintaining the security patterns and operational standards of the Underscore Protocol.

## Architecture & Modules

AeroClassic uses a modular architecture combining address management and DEX data handling:

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
│                       AeroClassic Contract                         │
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
│  │  │   Token Swaps   │  │    Liquidity    │  │    Price    │  │  │
│  │  │                 │  │   Management    │  │   Queries   │  │  │
│  │  │ • Multi-hop     │  │                 │  │             │  │  │
│  │  │   routing       │  │ • Add liquidity │  │ • Pool      │  │  │
│  │  │ • Auto pool     │  │   (stable/vol)  │  │   prices    │  │  │
│  │  │   selection     │  │ • Remove        │  │ • Best      │  │  │
│  │  │ • Slippage      │  │   liquidity     │  │   routes    │  │  │
│  │  │   protection    │  │ • LP token      │  │ • Amount    │  │  │
│  │  │ • Refund        │  │   management    │  │   quotes    │  │  │
│  │  │   handling      │  │                 │  │             │  │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                               │
                               v
┌────────────────────────────────────────────────────────────────────┐
│                    Aerodrome Finance Integration                   │
│                                                                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐   │
│  │     Factory     │  │     Router      │  │   Classic Pools   │  │
│  │                 │  │                 │  │                   │  │
│  │ • Pool lookup   │  │ • Add/remove    │  │ • Stable pairs    │  │
│  │ • Fee queries   │  │   liquidity     │  │ • Volatile pairs  │  │
│  │ • Pool creation │  │ • Quote         │  │ • Token swaps     │  │
│  │                 │  │   functions     │  │ • Reserve queries │  │
│  └─────────────────┘  └─────────────────┘  └──────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
```

## Data Structures

### BestPool Struct
Information about the optimal pool for a token pair:
```vyper
struct BestPool:
    pool: address        # Pool contract address
    fee: uint256        # Pool fee rate
    liquidity: uint256  # Total liquidity (reserve0 + reserve1)
    numCoins: uint256   # Number of tokens (always 2)
```

### Route Struct
Defines a swap route segment for Aerodrome Router:
```vyper
struct Route:
    from_: address      # Input token
    to: address         # Output token
    stable: bool        # Whether to use stable pool
    factory: address    # Factory contract address
```

## State Variables

### Immutable Aerodrome Addresses
- `AERODROME_FACTORY: public(immutable(address))` - Aerodrome factory contract
- `AERODROME_ROUTER: public(immutable(address))` - Aerodrome router contract

### Public State Variables
- `coreRouterPool: public(address)` - Core routing pool for optimal paths

### Constants
- `MAX_TOKEN_PATH: constant(uint256) = 5` - Maximum tokens in swap path
- `EIGHTEEN_DECIMALS: constant(uint256) = 10 ** 18` - Decimal precision constant

## Constructor

### `__init__`

Initializes AeroClassic with Underscore Protocol and Aerodrome connections.

```vyper
@deploy
def __init__(
    _undyHq: address,
    _aerodromeFactory: address,
    _aerodromeRouter: address,
    _coreRouterPool: address,
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq contract address for Underscore Protocol |
| `_aerodromeFactory` | `address` | Aerodrome factory contract address |
| `_aerodromeRouter` | `address` | Aerodrome router contract address |
| `_coreRouterPool` | `address` | Core pool for routing optimization |

#### Returns

*Constructor does not return any values*

#### Access

Called only during contract deployment

#### Example Usage
```python
aero_classic = boa.load(
    "contracts/legos/dexes/AeroClassic.vy",
    undy_hq.address,
    aero_factory.address,
    aero_router.address,
    core_pool.address
)
```

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

- `SWAP` - Token swapping through Aerodrome pools
- `ADD_LIQ` - Adding liquidity to pools
- `REMOVE_LIQ` - Removing liquidity from pools

### `getRegistries`

Returns the Aerodrome registry addresses.

```vyper
@view
@external
def getRegistries() -> DynArray[address, 10]:
```

#### Returns

| Type | Description |
|------|-------------|
| `DynArray[address, 10]` | Array containing factory and router addresses |

### `isYieldLego` / `isDexLego`

Identifies the Lego type capabilities.

```vyper
@view
@external
def isYieldLego() -> bool:  # Returns False

@view
@external
def isDexLego() -> bool:    # Returns True
```

## Token Swap Functions

### `swapTokens`

Executes multi-hop token swaps through Aerodrome pools.

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

- `AerodromeSwap` - Contains swap details including tokens, amounts, USD value, and recipient

#### Example Usage
```python
# Single-hop swap USDC -> WETH
amount_in, amount_out, usd_value = aero_classic.swapTokens(
    1000 * 10**6,  # 1000 USDC
    0.3 * 10**18,  # Min 0.3 WETH
    [usdc.address, weth.address],
    [usdc_weth_pool.address],
    user.address
)

# Multi-hop swap USDC -> WETH -> TOKEN
amount_in, amount_out, usd_value = aero_classic.swapTokens(
    1000 * 10**6,
    min_token_out,
    [usdc.address, weth.address, token.address],
    [usdc_weth_pool.address, weth_token_pool.address],
    user.address
)
```

#### Notes

- Automatically refunds unused input tokens
- Validates pool authenticity through factory
- Handles both stable and volatile pools
- Updates prices through Appraiser integration

## Liquidity Management Functions

### `addLiquidity`

Adds liquidity to Aerodrome Classic pools.

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
| `_minLpAmount` | `uint256` | Minimum LP tokens to receive |
| `_extraData` | `bytes32` | Additional data (unused) |
| `_recipient` | `address` | Address to receive LP tokens |
| `_miniAddys` | `ws.MiniAddys` | Mini address struct |

#### Returns

| Type | Description |
|------|-------------|
| `address` | Pool address (LP token address) |
| `uint256` | LP tokens received |
| `uint256` | Actual amount of token A added |
| `uint256` | Actual amount of token B added |
| `uint256` | USD value of liquidity added |

#### Access

- Contract must not be paused
- Open to all callers

#### Events Emitted

- `AerodromeLiquidityAdded` - Contains liquidity details including tokens, amounts, LP tokens, and USD value

#### Example Usage
```python
# Add liquidity to USDC/WETH pool
pool, lp_amount, amount_a, amount_b, usd_value = aero_classic.addLiquidity(
    usdc_weth_pool.address,
    usdc.address,
    weth.address,
    1000 * 10**6,    # 1000 USDC
    0.5 * 10**18,     # 0.5 WETH
    950 * 10**6,      # Min 950 USDC
    0.45 * 10**18,    # Min 0.45 WETH
    0,                # No min LP requirement
    empty(bytes32),
    user.address
)
```

### `removeLiquidity`

Removes liquidity from Aerodrome Classic pools.

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
| `_lpToken` | `address` | LP token address (same as pool) |
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

- `AerodromeLiquidityRemoved` - Contains removal details including tokens, amounts, LP tokens burned, and USD value

## Pool Query Functions

### `getDeepestLiqPool`

Finds the pool with highest liquidity for a token pair.

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
| `BestPool` | Struct containing best pool info or empty if no pools exist |

#### Notes

- Compares both stable and volatile pools
- Returns pool with highest total reserves
- Includes fee information from factory

### `getBestSwapAmountOut`

Finds the best pool and calculates output for a swap.

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
| `address` | Best pool address |
| `uint256` | Expected output amount |

### `getBestSwapAmountIn`

Calculates required input for desired output (volatile pools only).

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
| `address` | Best pool address |
| `uint256` | Required input amount |

#### Notes

- Currently only supports volatile pools
- Returns max_value(uint256) for stable pools

## Utility Functions

### `getLpToken` / `getPoolForLpToken`

LP token utilities for Aerodrome pools.

```vyper
@view
@external
def getLpToken(_pool: address) -> address:
    # In Aerodrome Classic, LP token IS the pool
    return _pool

@view
@external  
def getPoolForLpToken(_lpToken: address) -> address:
    # In Aerodrome Classic, pool IS the LP token
    return _lpToken
```

### `getCoreRouterPool`

Returns the core routing pool address.

```vyper
@view
@external
def getCoreRouterPool() -> address:
```

### `getAddLiqAmountsIn`

Quotes required amounts for adding liquidity.

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

### `getRemoveLiqAmountsOut`

Quotes output amounts for removing liquidity.

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

### `getPriceUnsafe`

Gets price from pool reserves (volatile pools only).

```vyper
@view
@external
def getPriceUnsafe(_pool: address, _targetToken: address, _appraiser: address = empty(address)) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_pool` | `address` | Pool address |
| `_targetToken` | `address` | Token to get price for |
| `_appraiser` | `address` | Appraiser address (optional) |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Price in 18 decimals |

#### Notes

- Uses reserve ratios and known prices
- Adjusts for token decimal differences
- Returns 0 for stable pools (not implemented)

## Internal Functions

### `_swapTokensInPool`

Internal function to execute swap in a specific pool.

```vyper
@internal
def _swapTokensInPool(
    _pool: address,
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256,
    _recipient: address,
    _aeroFactory: address,
) -> uint256:
```

#### Logic
1. Validates tokens are in the pool
2. Verifies pool authenticity via factory
3. Calculates expected output
4. Executes swap with correct amounts
5. Returns actual output amount

### `_getUsdValue`

Calculates combined USD value for liquidity operations.

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

### `_getAmountInForVolatilePools`

Calculates required input for volatile pools using constant product formula.

```vyper
@internal
def _getAmountInForVolatilePools(_pool: address, _zeroForOne: bool, _amountOut: uint256) -> uint256:
```

## Unimplemented Functions

AeroClassic includes placeholder implementations for non-DEX functions:

- Yield operations: `depositForYield()`, `withdrawFromYield()`
- Asset minting: `mintOrRedeemAsset()`, `confirmMintOrRedeemAsset()`
- Debt management: `addCollateral()`, `removeCollateral()`, `borrow()`, `repayDebt()`
- Rewards: `claimRewards()`
- Concentrated liquidity: `addLiquidityConcentrated()`, `removeLiquidityConcentrated()`
- Other: `getAccessForLego()`, `getPricePerShare()`, `getPrice()`

All return zero values or empty results.

## Security Considerations

### Access Control
- Pause functionality through DexLegoData module
- No special permissions required for operations
- All functions validate inputs and pool authenticity

### Token Handling
- Automatic approval management with reset after operations
- Balance tracking for refund calculations
- Safe transfer handling with default return values

### Pool Validation
- All pools verified through factory before interaction
- Token pair validation for liquidity operations
- Slippage protection through minimum amounts

## Integration Patterns

### Swap Workflow
```python
# 1. Find best pool for swap
pool, expected_out = aero_classic.getBestSwapAmountOut(
    token_in.address,
    token_out.address,
    swap_amount
)

# 2. Execute swap with slippage protection
amount_in, amount_out, usd_value = user_wallet.swapTokens([{
    'legoId': AERO_CLASSIC_LEGO_ID,
    'amountIn': swap_amount,
    'minAmountOut': int(expected_out * 0.97),  # 3% slippage
    'tokenPath': [token_in.address, token_out.address],
    'poolPath': [pool]
}])
```

### Liquidity Workflow
```python
# 1. Quote required amounts
amount_a, amount_b, lp_expected = aero_classic.getAddLiqAmountsIn(
    pool.address,
    token_a.address,
    token_b.address,
    available_a,
    available_b
)

# 2. Add liquidity
pool, lp_received, actual_a, actual_b, usd = user_wallet.addLiquidity(
    AERO_CLASSIC_LEGO_ID,
    pool.address,
    token_a.address,
    token_b.address,
    amount_a,
    amount_b,
    int(amount_a * 0.95),  # 5% slippage
    int(amount_b * 0.95),
    0  # No LP minimum
)

# 3. Remove liquidity later
amount_a_out, amount_b_out = aero_classic.getRemoveLiqAmountsOut(
    pool.address,
    token_a.address,
    token_b.address,
    lp_amount
)
```

## Testing

For comprehensive test examples, see: [`tests/legos/dexes/test_aero_classic.py`](../../../../tests/legos/dexes/test_aero_classic.py)