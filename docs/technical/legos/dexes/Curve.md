# Curve Technical Documentation

[📄 View Source Code](../../../../contracts/legos/dexes/Curve.vy)

## Overview

Curve is a DEX Lego partner that integrates the Underscore Protocol with Curve Finance, the leading decentralized exchange optimized for stablecoin and similar-value asset swaps. It provides comprehensive support for Curve's diverse pool types including StableSwap NG, Crypto pools, TriCrypto pools, and MetaPools. The integration enables efficient token swapping and liquidity management across Curve's ecosystem while leveraging their sophisticated bonding curves for minimal slippage.

**Core Features**:
- **Multi-Pool Type Support**: Handles StableSwap NG, Two/TriCrypto (NG and legacy), and MetaPools
- **Token Swaps**: Multi-hop swaps with automatic pool routing through Curve's meta registry
- **Liquidity Management**: Add/remove liquidity with support for single-sided withdrawals
- **Pool Discovery**: Automatic selection of deepest liquidity pools using Curve's registry system

Built with modular architecture using Addys and DexLegoData modules, Curve provides seamless access to one of DeFi's most liquid and capital-efficient exchange protocols while maintaining the security patterns and operational standards of the Underscore Protocol.

## Architecture & Modules

Curve uses a modular architecture combining address management and DEX data handling:

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
│                         Curve Contract                             │
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
│  │  │   routing       │  │ • Multi-pool    │  │ • Deepest   │  │  │
│  │  │ • Pool type     │  │   support       │  │   liquidity │  │  │
│  │  │   detection     │  │ • Single-sided  │  │ • Best      │  │  │
│  │  │ • Auto routing  │  │   removal       │  │   rates     │  │  │
│  │  │ • Slippage      │  │ • LP token      │  │ • Pool      │  │  │
│  │  │   protection    │  │   management    │  │   metadata  │  │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                               │
                               v
┌────────────────────────────────────────────────────────────────────┐
│                    Curve Finance Integration                       │
│                                                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │   Meta Registry  │  │  Rate Provider   │  │   Pool Types    │  │
│  │                  │  │                  │  │                 │  │
│  │ • Pool lookup    │  │ • Quote engine   │  │ • StableSwap NG │  │
│  │ • Coin indices   │  │ • Aggregated     │  │ • TwoCrypto NG  │  │
│  │ • LP tokens      │  │   rates          │  │ • TriCrypto NG  │  │
│  │ • Pool metadata  │  │ • Swap quotes    │  │ • TwoCrypto     │  │
│  │ • Registry       │  │ • Amount calc    │  │ • MetaPool      │  │
│  │   handlers       │  │                  │  │ • Crypto (v1)   │  │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

## Data Structures

### PoolType Flag
Identifies the specific Curve pool implementation:
```vyper
flag PoolType:
    STABLESWAP_NG    # Next-gen stable pools
    TWO_CRYPTO_NG    # Next-gen 2-token crypto pools
    TRICRYPTO_NG     # Next-gen 3-token crypto pools
    TWO_CRYPTO       # Legacy 2-token crypto pools
    METAPOOL         # Meta pools (stable + LP token)
    CRYPTO           # Legacy crypto pools
```

### PoolData Struct
Contains essential pool information:
```vyper
struct PoolData:
    pool: address           # Pool contract address
    indexTokenA: uint256    # Index of token A in pool
    indexTokenB: uint256    # Index of token B in pool
    poolType: PoolType      # Pool implementation type
    numCoins: uint256       # Total number of coins in pool
```

### BestPool Struct
Information about the optimal pool for a token pair:
```vyper
struct BestPool:
    pool: address        # Pool contract address
    fee: uint256        # Pool fee rate (normalized to 100_00)
    liquidity: uint256  # Total liquidity (sum of balances)
    numCoins: uint256   # Number of tokens in pool
```

### Quote Struct
Swap quote information from Rate Provider:
```vyper
struct Quote:
    source_token_index: uint256
    dest_token_index: uint256
    is_underlying: bool
    amount_out: uint256
    pool: address
    source_token_pool_balance: uint256
    dest_token_pool_balance: uint256
    pool_type: uint8
```

### CurveRegistries Struct
Registry addresses for different pool types:
```vyper
struct CurveRegistries:
    StableSwapNg: address
    TwoCryptoNg: address
    TricryptoNg: address
    TwoCrypto: address
    MetaPool: address
    RateProvider: address
```

## State Variables

### Immutable Curve Addresses
- `CURVE_META_REGISTRY: public(immutable(address))` - Curve's meta registry contract
- `CURVE_REGISTRIES: public(immutable(CurveRegistries))` - Registry addresses struct

### Constants
- `METAPOOL_FACTORY_ID: constant(uint256) = 3` - Address provider ID
- `TWO_CRYPTO_FACTORY_ID: constant(uint256) = 6` - Address provider ID
- `META_REGISTRY_ID: constant(uint256) = 7` - Address provider ID
- `TRICRYPTO_NG_FACTORY_ID: constant(uint256) = 11` - Address provider ID
- `STABLESWAP_NG_FACTORY_ID: constant(uint256) = 12` - Address provider ID
- `TWO_CRYPTO_NG_FACTORY_ID: constant(uint256) = 13` - Address provider ID
- `RATE_PROVIDER_ID: constant(uint256) = 18` - Address provider ID
- `MAX_POOLS: constant(uint256) = 50` - Maximum pools to check
- `MAX_QUOTES: constant(uint256) = 100` - Maximum quotes to process
- `MAX_TOKEN_PATH: constant(uint256) = 5` - Maximum tokens in swap path

## Constructor

### `__init__`

Initializes Curve with Underscore Protocol and Curve Finance connections.

```vyper
@deploy
def __init__(_undyHq: address, _curveAddressProvider: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq contract address for Underscore Protocol |
| `_curveAddressProvider` | `address` | Curve's address provider contract |

#### Returns

*Constructor does not return any values*

#### Access

Called only during contract deployment

#### Example Usage
```python
curve_lego = boa.load(
    "contracts/legos/dexes/Curve.vy",
    undy_hq.address,
    curve_address_provider.address
)
```

#### Notes

- Fetches all registry addresses from Curve's address provider
- Stores meta registry and specialized registry addresses
- Validates all addresses are non-zero

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

- `SWAP` - Token swapping through Curve pools
- `ADD_LIQ` - Adding liquidity to pools
- `REMOVE_LIQ` - Removing liquidity from pools

### `getRegistries`

Returns the Curve registry addresses.

```vyper
@view
@external
def getRegistries() -> DynArray[address, 10]:
```

#### Returns

| Type | Description |
|------|-------------|
| `DynArray[address, 10]` | Array containing the meta registry address |

## Token Swap Functions

### `swapTokens`

Executes multi-hop token swaps through Curve pools.

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

- `CurveSwap` - Contains swap details including tokens, amounts, USD value, and recipient

#### Example Usage
```python
# Single-hop swap USDC -> USDT
amount_in, amount_out, usd_value = curve_lego.swapTokens(
    1000 * 10**6,  # 1000 USDC
    995 * 10**6,   # Min 995 USDT (0.5% slippage)
    [usdc.address, usdt.address],
    [stable_pool.address],
    user.address
)

# Multi-hop swap USDC -> WETH -> WBTC
amount_in, amount_out, usd_value = curve_lego.swapTokens(
    1000 * 10**6,
    min_btc_out,
    [usdc.address, weth.address, wbtc.address],
    [tricrypto_pool.address, btc_pool.address],
    user.address
)
```

#### Notes

- Automatically detects pool type and uses appropriate interface
- Handles approvals internally with reset after swap
- Refunds any unused input tokens
- Supports all Curve pool types

## Liquidity Management Functions

### `addLiquidity`

Adds liquidity to Curve pools with automatic pool type detection.

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
| `_minAmountA` | `uint256` | Minimum token A to add (unused) |
| `_minAmountB` | `uint256` | Minimum token B to add (unused) |
| `_minLpAmount` | `uint256` | Minimum LP tokens to receive |
| `_extraData` | `bytes32` | Additional data (unused) |
| `_recipient` | `address` | Address to receive LP tokens |
| `_miniAddys` | `ws.MiniAddys` | Mini address struct |

#### Returns

| Type | Description |
|------|-------------|
| `address` | LP token address |
| `uint256` | LP tokens received |
| `uint256` | Actual amount of token A added |
| `uint256` | Actual amount of token B added |
| `uint256` | USD value of liquidity added |

#### Access

- Contract must not be paused
- Open to all callers

#### Events Emitted

- `CurveLiquidityAdded` - Contains liquidity details including tokens, amounts, LP tokens, and USD value

#### Example Usage
```python
# Add liquidity to USDC/USDT pool
lp_token, lp_amount, amount_a, amount_b, usd_value = curve_lego.addLiquidity(
    stable_pool.address,
    usdc.address,
    usdt.address,
    1000 * 10**6,   # 1000 USDC
    1000 * 10**6,   # 1000 USDT
    0,              # No min for token A
    0,              # No min for token B
    1990 * 10**18,  # Min 1990 LP tokens
    empty(bytes32),
    user.address
)
```

#### Notes

- Supports pools with 2-4 coins (only uses first 2 tokens)
- Automatically detects pool type and uses correct interface
- Handles single-sided deposits (one token can be 0)
- Refunds any unused tokens

### `removeLiquidity`

Removes liquidity from Curve pools with support for single-sided withdrawals.

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
| `_tokenA` | `address` | First token (empty for single-sided) |
| `_tokenB` | `address` | Second token (empty for single-sided) |
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

- `CurveLiquidityRemoved` - Contains removal details including tokens, amounts, LP tokens burned, and USD value

#### Example Usage
```python
# Remove liquidity proportionally
amount_a, amount_b, lp_burned, usd_value = curve_lego.removeLiquidity(
    stable_pool.address,
    usdc.address,
    usdt.address,
    lp_token.address,
    100 * 10**18,    # 100 LP tokens
    99 * 10**6,      # Min 99 USDC
    99 * 10**6,      # Min 99 USDT
    empty(bytes32),
    user.address
)

# Single-sided withdrawal (USDC only)
amount_usdc, _, lp_burned, usd_value = curve_lego.removeLiquidity(
    stable_pool.address,
    usdc.address,
    empty(address),   # Empty = single-sided
    lp_token.address,
    100 * 10**18,
    198 * 10**6,      # Min 198 USDC
    0,
    empty(bytes32),
    user.address
)
```

#### Notes

- Supports balanced and single-sided withdrawals
- Empty address for a token indicates single-sided withdrawal
- Only supports 2-coin pools for balanced withdrawals
- Automatically detects pool type

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

- Checks all pools registered in Curve's meta registry
- Returns pool with highest combined balance of both tokens
- Fee is normalized to 100_00 base (e.g., 4 = 0.04%)

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

#### Notes

- Uses Curve's Rate Provider for accurate quotes
- Considers all available pools and routes

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
| `address` | Best pool address |
| `uint256` | Required input amount (approximate) |

#### Notes

- Uses aggregated rate from Rate Provider
- Returns max_value if output amount is invalid

## Utility Functions

### `getLpToken` / `getPoolForLpToken`

LP token utilities using Curve's meta registry.

```vyper
@view
@external
def getLpToken(_pool: address) -> address:
    return staticcall CurveMetaRegistry(CURVE_META_REGISTRY).get_lp_token(_pool)

@view
@external  
def getPoolForLpToken(_lpToken: address) -> address:
    return staticcall CurveMetaRegistry(CURVE_META_REGISTRY).get_pool_from_lp_token(_lpToken)
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
| `uint256` | Expected LP tokens |

#### Notes

- Calculates amounts to maintain pool ratio
- Uses pool-specific calculation methods

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

- Supports balanced withdrawal estimates for 2-coin pools
- Single-sided withdrawal calculations when one token is empty
- Uses pool-specific calc functions

### `getCoreRouterPool`

Returns the core routing pool address.

```vyper
@view
@external
def getCoreRouterPool() -> address:
    return empty(address)  # Not used for Curve
```

## Internal Pool Management

### `_getPoolData`

Retrieves comprehensive pool information.

```vyper
@view
@internal
def _getPoolData(_pool: address, _tokenA: address, _tokenB: address, _metaRegistry: address) -> PoolData:
```

#### Logic
1. Validates pool is registered in meta registry
2. Gets coin list and finds token indices
3. Determines pool type from registry handlers
4. Counts total coins in pool

### `_getPoolType`

Determines pool implementation type.

```vyper
@view
@internal
def _getPoolType(_pool: address, _metaRegistry: address) -> PoolType:
```

#### Pool Type Detection
- Checks registry handlers to identify base registry
- Maps registry address to pool type enum
- Defaults to CRYPTO for unknown registries

### Pool-Specific Internal Functions

The contract includes specialized internal functions for each pool type:

- **StableSwap NG**: `_addLiquidityStableNg`, `_removeLiquidityStableNg`
- **TwoCrypto NG**: `_addLiquidityTwoCryptoNg`, `_removeLiquidityTwoCryptoNg`
- **TwoCrypto**: `_addLiquidityTwoCrypto`, `_removeLiquidityTwoCrypto`
- **TriCrypto**: `_addLiquidityTricrypto`, `_removeLiquidityTricrypto`
- **MetaPool**: `_addLiquidityMetaPool`, `_removeLiquidityMetaPool`

Each handles the specific interface requirements of its pool type.

## Unimplemented Functions

Curve includes placeholder implementations for unsupported functions:

- Other: `getAccessForLego()`, `getPricePerShare()`, `getPrice()`, `getPriceUnsafe()`

All return zero values or empty results.

## Security Considerations

### Pool Validation
- All pools verified through meta registry
- Token indices validated before operations
- Pool type detection prevents interface mismatches

### Token Handling
- Automatic approval management with reset after operations
- Balance tracking for refund calculations
- Safe transfer handling with default return values

### Slippage Protection
- Minimum output amounts enforced on swaps
- Minimum LP tokens on liquidity addition
- Per-token minimums on liquidity removal

## Integration Patterns

### Swap Workflow
```python
# 1. Find best pool and get quote
pool, expected_out = curve_lego.getBestSwapAmountOut(
    token_in.address,
    token_out.address,
    swap_amount
)

# 2. Execute swap with slippage protection
amount_in, amount_out, usd_value = user_wallet.swapTokens([{
    'legoId': CURVE_LEGO_ID,
    'amountIn': swap_amount,
    'minAmountOut': int(expected_out * 0.995),  # 0.5% slippage
    'tokenPath': [token_in.address, token_out.address],
    'poolPath': [pool]
}])
```

### Liquidity Workflow
```python
# 1. Get optimal amounts for current pool ratio
amount_a, amount_b, expected_lp = curve_lego.getAddLiqAmountsIn(
    pool.address,
    token_a.address,
    token_b.address,
    available_a,
    available_b
)

# 2. Add liquidity
lp_token, lp_received, actual_a, actual_b, usd = user_wallet.addLiquidity(
    CURVE_LEGO_ID,
    pool.address,
    token_a.address,
    token_b.address,
    amount_a,
    amount_b,
    0,  # No min A
    0,  # No min B
    int(expected_lp * 0.99)  # 1% slippage on LP
)

# 3. Check removal amounts
out_a, out_b = curve_lego.getRemoveLiqAmountsOut(
    pool.address,
    token_a.address,
    token_b.address,
    lp_amount
)

# 4. Remove liquidity
amount_a_out, amount_b_out, lp_burned, usd = user_wallet.removeLiquidity(
    CURVE_LEGO_ID,
    pool.address,
    token_a.address,
    token_b.address,
    lp_token,
    lp_amount,
    int(out_a * 0.99),  # 1% slippage
    int(out_b * 0.99)
)
```

## Testing

For comprehensive test examples, see: [`tests/legos/dexes/test_curve.py`](../../../../tests/legos/dexes/test_curve.py)