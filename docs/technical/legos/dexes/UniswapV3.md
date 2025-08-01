# UniswapV3 Technical Documentation

[📄 View Source Code](../../../../contracts/legos/dexes/UniswapV3.vy)

## Overview

UniswapV3 is a DEX Lego partner that integrates the Underscore Protocol with Uniswap V3, the revolutionary concentrated liquidity AMM protocol. It provides comprehensive support for token swapping through concentrated liquidity pools and advanced liquidity management with NFT-based positions. The integration enables capital-efficient liquidity provision with custom price ranges, multi-hop swaps with minimal slippage, and full control over liquidity positions through Uniswap's NFT Position Manager.

**Core Features**:
- **Concentrated Liquidity**: Provide liquidity within specific price ranges for maximum capital efficiency
- **NFT Position Management**: Create, increase, and decrease liquidity positions represented as NFTs
- **Multi-Hop Swaps**: Execute complex token swaps through multiple pools with automatic routing
- **Fee Collection**: Automatically collect trading fees when modifying positions
- **Multiple Fee Tiers**: Access pools with 0.01%, 0.05%, 0.3%, and 1% fee tiers

Built with modular architecture using Addys and DexLegoData modules, UniswapV3 provides seamless access to the most capital-efficient DEX protocol while maintaining the security patterns and operational standards of the Underscore Protocol.

## Architecture & Modules

UniswapV3 uses a modular architecture combining address management and DEX data handling:

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
│                        UniswapV3 Contract                          │
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
│  │  │   Token Swaps   │  │ Concentrated Liq │  │  Position   │  │  │
│  │  │                 │  │   Management    │  │  Management │  │  │
│  │  │ • Multi-hop     │  │                 │  │             │  │  │
│  │  │   routing       │  │ • Custom ranges │  │ • NFT based │  │  │
│  │  │ • Callback      │  │ • Capital       │  │ • Fee       │  │  │
│  │  │   pattern       │  │   efficiency    │  │   collection│  │  │
│  │  │ • Slippage      │  │ • Multiple      │  │ • Position  │  │  │
│  │  │   protection    │  │   fee tiers     │  │   tracking  │  │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                               │
                               v
┌────────────────────────────────────────────────────────────────────┐
│                    Uniswap V3 Integration                          │
│                                                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │   V3 Factory     │  │  NFT Position    │  │   V3 Quoter     │  │
│  │                  │  │    Manager       │  │                 │  │
│  │ • Pool creation  │  │ • Mint positions │  │ • Quote swaps   │  │
│  │ • Pool lookup    │  │ • Modify liq     │  │ • Path quotes   │  │
│  │ • Fee tiers      │  │ • Collect fees   │  │ • Price impact  │  │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

## Data Structures

### BestPool Struct
Contains information about the optimal pool for a token pair:
```vyper
struct BestPool:
    pool: address        # Pool contract address
    fee: uint256        # Pool fee rate (normalized to 100_00)
    liquidity: uint256  # Total token balances (pseudo-liquidity)
    numCoins: uint256   # Always 2 for Uniswap V3
```

### PoolSwapData Struct (Transient)
Stores swap data for callback verification:
```vyper
struct PoolSwapData:
    pool: address       # Pool executing the swap
    tokenIn: address    # Input token
    amountIn: uint256   # Input amount
```

### PositionData Struct
NFT position information from Position Manager:
```vyper
struct PositionData:
    nonce: uint96
    operator: address
    token0: address
    token1: address
    fee: uint24
    tickLower: int24
    tickUpper: int24
    liquidity: uint128
    feeGrowthInside0LastX128: uint256
    feeGrowthInside1LastX128: uint256
    tokensOwed0: uint128
    tokensOwed1: uint128
```

### MintParams / IncreaseLiquidityParams / DecreaseLiquidityParams
Parameter structs for position management operations.

## State Variables

### Immutable Protocol Addresses
- `UNIV3_FACTORY: public(immutable(address))` - Uniswap V3 factory contract
- `UNIV3_NFT_MANAGER: public(immutable(address))` - NFT Position Manager contract
- `UNIV3_QUOTER: public(immutable(address))` - Quoter contract for price calculations
- `coreRouterPool: public(address)` - Core routing pool for the protocol

### Transient Storage
- `poolSwapData: transient(PoolSwapData)` - Temporary storage for swap callbacks

### Constants
- `FEE_TIERS: constant(uint24[4]) = [100, 500, 3000, 10000]` - Available fee tiers (0.01%, 0.05%, 0.3%, 1%)
- `MIN_SQRT_RATIO_PLUS_ONE: constant(uint160) = 4295128740` - Minimum price bound
- `MAX_SQRT_RATIO_MINUS_ONE: constant(uint160) = 1461446703485210103287273052203988822378723970341` - Maximum price bound
- `TICK_LOWER: constant(int24) = -887272` - Minimum tick
- `TICK_UPPER: constant(int24) = 887272` - Maximum tick
- `MAX_TOKEN_PATH: constant(uint256) = 5` - Maximum tokens in swap path

## Constructor

### `__init__`

Initializes UniswapV3 with Underscore Protocol and Uniswap V3 connections.

```vyper
@deploy
def __init__(
    _undyHq: address,
    _uniswapV3Factory: address,
    _uniNftPositionManager: address,
    _uniV3Quoter: address,
    _coreRouterPool: address,
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq contract address for Underscore Protocol |
| `_uniswapV3Factory` | `address` | Uniswap V3 factory contract |
| `_uniNftPositionManager` | `address` | NFT Position Manager contract |
| `_uniV3Quoter` | `address` | Quoter contract for price calculations |
| `_coreRouterPool` | `address` | Core routing pool address |

#### Returns

*Constructor does not return any values*

#### Access

Called only during contract deployment

#### Example Usage
```python
uniswap_v3_lego = boa.load(
    "contracts/legos/dexes/UniswapV3.vy",
    undy_hq.address,
    uniswap_factory.address,
    position_manager.address,
    quoter.address,
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

- `SWAP` - Token swapping through Uniswap V3 pools
- `ADD_LIQ_CONC` - Adding concentrated liquidity
- `REMOVE_LIQ_CONC` - Removing concentrated liquidity

### `onERC721Received`

Required for receiving NFT positions safely.

```vyper
@view
@external
def onERC721Received(_operator: address, _owner: address, _tokenId: uint256, _data: Bytes[1024]) -> bytes4:
```

#### Notes

- Must return specific selector for ERC721 compliance
- Validates data matches expected format

### `getRegistries`

Returns the Uniswap V3 registry addresses.

```vyper
@view
@external
def getRegistries() -> DynArray[address, 10]:
```

#### Returns

| Type | Description |
|------|-------------|
| `DynArray[address, 10]` | Array containing factory, position manager, and quoter addresses |

## Token Swap Functions

### `swapTokens`

Executes multi-hop token swaps through Uniswap V3 pools.

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

- `UniswapV3Swap` - Contains swap details including tokens, amounts, USD value, and recipient

#### Example Usage
```python
# Single-hop swap USDC -> WETH
amount_in, amount_out, usd_value = uniswap_v3_lego.swapTokens(
    1000 * 10**6,  # 1000 USDC
    0.3 * 10**18,  # Min 0.3 WETH
    [usdc.address, weth.address],
    [usdc_weth_pool.address],
    user.address
)

# Multi-hop swap USDC -> WETH -> DAI
amount_in, amount_out, usd_value = uniswap_v3_lego.swapTokens(
    1000 * 10**6,
    990 * 10**18,  # Min 990 DAI
    [usdc.address, weth.address, dai.address],
    [usdc_weth_pool.address, weth_dai_pool.address],
    user.address
)
```

#### Notes

- Uses callback pattern for token transfers
- Validates each pool through factory
- Refunds any unused input tokens
- Uses transient storage for callback security

### `uniswapV3SwapCallback`

Callback function called by pools during swaps.

```vyper
@external
def uniswapV3SwapCallback(_amount0Delta: int256, _amount1Delta: int256, _data: Bytes[256]):
```

#### Security

- Only callable by the pool stored in transient storage
- Transfers exact input amount to calling pool
- Clears transient storage after transfer

## Concentrated Liquidity Functions

### `addLiquidityConcentrated`

Adds liquidity to a specific price range or increases existing position.

```vyper
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
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_nftTokenId` | `uint256` | Existing position ID (0 to create new) |
| `_pool` | `address` | Pool contract address |
| `_tokenA` | `address` | First token address |
| `_tokenB` | `address` | Second token address |
| `_tickLower` | `int24` | Lower tick bound (min_value for full range) |
| `_tickUpper` | `int24` | Upper tick bound (max_value for full range) |
| `_amountA` | `uint256` | Amount of token A to add |
| `_amountB` | `uint256` | Amount of token B to add |
| `_minAmountA` | `uint256` | Minimum token A to add |
| `_minAmountB` | `uint256` | Minimum token B to add |
| `_extraData` | `bytes32` | Additional data (unused) |
| `_recipient` | `address` | Address to receive NFT |
| `_miniAddys` | `ws.MiniAddys` | Mini address struct |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Liquidity units added |
| `uint256` | Actual amount of token A added |
| `uint256` | Actual amount of token B added |
| `uint256` | NFT token ID (new or existing) |
| `uint256` | USD value of liquidity added |

#### Access

- Contract must not be paused
- Open to all callers

#### Events Emitted

- `UniswapV3LiquidityAdded` - Contains liquidity details including tokens, amounts, NFT ID, and USD value

#### Example Usage
```python
# Create new concentrated position
liquidity, amount_a, amount_b, nft_id, usd = uniswap_v3_lego.addLiquidityConcentrated(
    0,                    # Create new position
    usdc_weth_pool.address,
    usdc.address,
    weth.address,
    -60,                  # Lower tick
    60,                   # Upper tick
    1000 * 10**6,        # 1000 USDC
    0.5 * 10**18,        # 0.5 WETH
    990 * 10**6,         # Min USDC
    0.49 * 10**18,       # Min WETH
    empty(bytes32),
    user.address
)

# Add to existing position
liquidity, amount_a, amount_b, nft_id, usd = uniswap_v3_lego.addLiquidityConcentrated(
    existing_nft_id,      # Existing position
    usdc_weth_pool.address,
    usdc.address,
    weth.address,
    min_value(int24),     # Use existing ticks
    max_value(int24),     # Use existing ticks
    500 * 10**6,          # Add 500 USDC
    0.25 * 10**18,        # Add 0.25 WETH
    490 * 10**6,
    0.24 * 10**18,
    empty(bytes32),
    user.address
)
```

#### Notes

- Creates new NFT position if `_nftTokenId` is 0
- Increases existing position if NFT ID provided
- Automatically collects fees on existing positions
- Handles token ordering internally
- Refunds unused tokens

### `removeLiquidityConcentrated`

Removes liquidity from concentrated position and collects fees.

```vyper
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
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_nftTokenId` | `uint256` | NFT position ID |
| `_pool` | `address` | Pool contract address |
| `_tokenA` | `address` | First token address |
| `_tokenB` | `address` | Second token address |
| `_liqToRemove` | `uint256` | Liquidity units to remove |
| `_minAmountA` | `uint256` | Minimum token A to receive |
| `_minAmountB` | `uint256` | Minimum token B to receive |
| `_extraData` | `bytes32` | Additional data (unused) |
| `_recipient` | `address` | Address to receive tokens and NFT |
| `_miniAddys` | `ws.MiniAddys` | Mini address struct |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Amount of token A received |
| `uint256` | Amount of token B received |
| `uint256` | Liquidity units removed |
| `bool` | True if position fully closed |
| `uint256` | USD value of liquidity removed |

#### Access

- Contract must not be paused
- NFT must be owned by contract
- Open to all callers

#### Events Emitted

- `UniswapV3LiquidityRemoved` - Contains removal details including tokens, amounts, liquidity removed, and USD value

#### Example Usage
```python
# Remove partial liquidity
amount_a, amount_b, liq_removed, is_closed, usd = uniswap_v3_lego.removeLiquidityConcentrated(
    nft_id,
    usdc_weth_pool.address,
    usdc.address,
    weth.address,
    liquidity // 2,      # Remove half
    490 * 10**6,         # Min USDC
    0.24 * 10**18,       # Min WETH
    empty(bytes32),
    user.address
)

# Remove all liquidity
amount_a, amount_b, liq_removed, is_closed, usd = uniswap_v3_lego.removeLiquidityConcentrated(
    nft_id,
    usdc_weth_pool.address,
    usdc.address,
    weth.address,
    max_value(uint256),  # Remove all
    980 * 10**6,
    0.48 * 10**18,
    empty(bytes32),
    user.address
)
```

#### Notes

- Automatically collects all fees
- Burns NFT if position fully depleted
- Returns NFT to recipient if liquidity remains
- Handles token ordering internally

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

- Checks all fee tiers (0.01%, 0.05%, 0.3%, 1%)
- Returns pool with highest active liquidity
- Liquidity field contains token balances (not true liquidity)

### `getBestSwapAmountOut`

Finds the best pool and calculates output for a swap.

```vyper
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

- Not a view function due to Quoter limitations
- Uses deepest liquidity pool
- Includes price impact in calculation

### `getBestSwapAmountIn`

Calculates required input for desired output.

```vyper
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

- Not a view function due to Quoter limitations
- Returns max_value if output amount invalid

## Utility Functions

### `getLpToken` / `getPoolForLpToken`

LP token utilities (V3 uses NFTs, not LP tokens).

```vyper
@view
@external
def getLpToken(_pool: address) -> address:
    return empty(address)  # No LP tokens in V3

@view
@external  
def getPoolForLpToken(_lpToken: address) -> address:
    return empty(address)  # No LP tokens in V3
```

### `getAddLiqAmountsIn`

Calculates optimal amounts for adding liquidity at current price.

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
| `uint256` | Always 0 (liquidity calculation not included) |

#### Notes

- Calculates for full range position
- Uses current pool price (sqrtPriceX96)

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

- Estimates based on current price
- Actual amounts depend on position's tick range

### `getCoreRouterPool`

Returns the core routing pool address.

```vyper
@view
@external
def getCoreRouterPool() -> address:
    return self.coreRouterPool
```

### `getPriceUnsafe`

Gets token price using pool's current tick and external price feed.

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
- Uses sqrtPriceX96 for accurate pricing
- Adjusts for decimal differences

## NFT Recovery Function

### `recoverNft`

Recovers stuck NFT positions (admin only).

```vyper
@external
def recoverNft(_collection: address, _nftTokenId: uint256, _recipient: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_collection` | `address` | NFT collection address |
| `_nftTokenId` | `uint256` | NFT token ID |
| `_recipient` | `address` | Address to receive NFT |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if recovered successfully |

#### Access

Only callable by switchboard addresses

#### Events Emitted

- `UniswapV3NftRecovered` - Contains collection, token ID, and recipient

## Internal Functions

### `_swapTokensInPool`

Executes a single swap within a pool using callbacks.

```vyper
@internal
def _swapTokensInPool(
    _pool: address,
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256,
    _recipient: address,
    _uniswapV3Factory: address,
) -> uint256:
```

#### Security

- Stores swap data in transient storage
- Validates pool through factory
- Callback verifies caller is expected pool

### `_getDeepestLiqPool`

Finds pool with highest liquidity across all fee tiers.

```vyper
@view
@internal
def _getDeepestLiqPool(_tokenA: address, _tokenB: address) -> (address, uint24):
```

### `_getSqrtPriceX96`

Gets current pool price in Uniswap's sqrt format.

```vyper
@view
@internal
def _getSqrtPriceX96(_pool: address) -> uint256:
```

### `_getTicks`

Converts special tick values to actual tick bounds.

```vyper
@view
@internal
def _getTicks(_pool: address, _tickLower: int24, _tickUpper: int24) -> (int24, int24):
```

#### Notes

- `min_value(int24)` converts to minimum valid tick
- `max_value(int24)` converts to maximum valid tick
- Aligns ticks to pool's tick spacing

### `_mintNewPosition`

Creates new NFT position in Position Manager.

```vyper
@internal
def _mintNewPosition(...) -> (uint256, uint128, uint256, uint256):
```

### `_increaseExistingPosition`

Adds liquidity to existing NFT position.

```vyper
@internal
def _increaseExistingPosition(...) -> (uint128, uint256, uint256):
```

### `_collectFees`

Collects accumulated fees from a position.

```vyper
@internal
def _collectFees(...) -> (uint256, uint256):
```

### `_getUsdValue`

Calculates total USD value for two tokens.

```vyper
@internal
def _getUsdValue(...) -> uint256:
```

## Unimplemented Functions

UniswapV3 includes placeholder implementations for unsupported functions:

- Yield: `depositForYield()`, `withdrawFromYield()`
- Mint/Redeem: `mintOrRedeemAsset()`, `confirmMintOrRedeemAsset()`
- Lending: `addCollateral()`, `removeCollateral()`, `borrow()`, `repayDebt()`
- Rewards: `claimRewards()`
- Standard Liquidity: `addLiquidity()`, `removeLiquidity()` (V3 uses concentrated versions)
- Other: `getAccessForLego()`, `getPricePerShare()`, `getPrice()`

All return zero values or empty results.

## Security Considerations

### Callback Security
- Uses transient storage to verify callback caller
- Only pools can call swap callback
- Clears transient storage after use

### NFT Handling
- Implements `onERC721Received` for safe transfers
- Validates NFT ownership before operations
- Burns NFTs when positions are closed

### Pool Validation
- All pools verified through factory
- Fee tier must be valid (0.01%, 0.05%, 0.3%, 1%)
- Token validation before operations

### Price Bounds
- Uses Uniswap's min/max sqrt price ratios
- Prevents manipulation through extreme prices
- Tick bounds enforced by protocol

## Integration Patterns

### Swap Workflow
```python
# 1. Find best pool and get quote
pool, expected_out = uniswap_v3_lego.getBestSwapAmountOut(
    token_in.address,
    token_out.address,
    swap_amount
)

# 2. Execute swap with slippage protection
amount_in, amount_out, usd_value = user_wallet.swapTokens([{
    'legoId': UNISWAP_V3_LEGO_ID,
    'amountIn': swap_amount,
    'minAmountOut': int(expected_out * 0.995),  # 0.5% slippage
    'tokenPath': [token_in.address, token_out.address],
    'poolPath': [pool]
}])
```

### Concentrated Liquidity Workflow
```python
# 1. Calculate optimal amounts for range
amount_a, amount_b, _ = uniswap_v3_lego.getAddLiqAmountsIn(
    pool.address,
    token_a.address,
    token_b.address,
    available_a,
    available_b
)

# 2. Create concentrated position
liquidity, actual_a, actual_b, nft_id, usd = user_wallet.addLiquidityConcentrated(
    UNISWAP_V3_LEGO_ID,
    0,  # New position
    pool.address,
    token_a.address,
    token_b.address,
    -600,   # Lower tick (~5% below current)
    600,    # Upper tick (~5% above current)
    amount_a,
    amount_b,
    int(amount_a * 0.99),
    int(amount_b * 0.99),
    user.address
)

# 3. Later, add to existing position
liquidity2, actual_a2, actual_b2, same_nft, usd2 = user_wallet.addLiquidityConcentrated(
    UNISWAP_V3_LEGO_ID,
    nft_id,  # Existing position
    pool.address,
    token_a.address,
    token_b.address,
    min_value(int24),  # Use existing range
    max_value(int24),  # Use existing range
    more_a,
    more_b,
    min_a,
    min_b,
    user.address
)

# 4. Remove liquidity and collect fees
out_a, out_b, liq_removed, is_closed, usd = user_wallet.removeLiquidityConcentrated(
    UNISWAP_V3_LEGO_ID,
    nft_id,
    pool.address,
    token_a.address,
    token_b.address,
    liquidity_to_remove,
    min_out_a,
    min_out_b,
    user.address
)
```

### Full Range Position Pattern
```python
# Create full range position (similar to V2)
liquidity, a, b, nft_id, usd = user_wallet.addLiquidityConcentrated(
    UNISWAP_V3_LEGO_ID,
    0,
    pool.address,
    token_a.address,
    token_b.address,
    min_value(int24),  # Full range lower
    max_value(int24),  # Full range upper
    amount_a,
    amount_b,
    min_a,
    min_b,
    user.address
)
```

## Testing

For comprehensive test examples, see: [`tests/legos/dexes/`](../../../../tests/legos/dexes/)