# AeroSlipstream Technical Documentation

[📄 View Source Code](../../../../contracts/legos/dexes/AeroSlipstream.vy)

## Overview

AeroSlipstream is a DEX Lego partner that integrates the Underscore Protocol with Aerodrome Finance's concentrated liquidity AMM (based on Uniswap V3). It provides advanced token swapping and concentrated liquidity management capabilities, enabling users to create and manage liquidity positions with precise price ranges through NFT-based position tracking. The integration supports multi-hop swaps, optimal tick spacing selection, and sophisticated position management.

**Core Features**:
- **Token Swaps**: Multi-hop swaps through concentrated liquidity pools with callback-based execution
- **Concentrated Liquidity**: NFT-based position management with custom price ranges (ticks)
- **Position Management**: Create new positions or add to existing ones, with automatic fee collection
- **Pool Discovery**: Automatic selection of optimal pools based on liquidity depth across multiple tick spacings

Built with modular architecture using Addys and DexLegoData modules, AeroSlipstream implements the Uniswap V3 callback interface for secure swap execution while maintaining the security patterns and operational standards of the Underscore Protocol.

## Architecture & Modules

AeroSlipstream uses a modular architecture combining address management and DEX data handling:

### Addys Module
- **Location**: `contracts/modules/Addys.vy`
- **Purpose**: Provides protocol-wide address lookups and registry access
- **Documentation**: See [Addys Technical Documentation](../../modules/Addys.md)
- **Key Features**:
  - Connection to UndyHq for protocol addresses
  - Access to Appraiser for USD valuations
  - Switchboard validation for NFT recovery

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
│                     AeroSlipstream Contract                        │
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
│  │  ┌──────────────────┐  ┌────────────────┐  ┌─────────────┐  │  │
│  │  │   Token Swaps    │  │  Concentrated  │  │  Position   │  │  │
│  │  │                  │  │   Liquidity    │  │ Management  │  │  │
│  │  │ • Multi-hop      │  │                │  │             │  │  │
│  │  │   routing        │  │ • NFT-based    │  │ • Fee       │  │  │
│  │  │ • Callback-based │  │   positions    │  │   collection│  │  │
│  │  │   execution      │  │ • Custom price │  │ • Position  │  │  │
│  │  │ • Price limit    │  │   ranges       │  │   increase  │  │  │
│  │  │   protection     │  │ • Multiple     │  │ • NFT       │  │  │
│  │  │ • Transient      │  │   tick spacings│  │   transfer  │  │  │
│  │  │   storage        │  │                │  │             │  │  │
│  │  └──────────────────┘  └────────────────┘  └─────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                               │
                               v
┌────────────────────────────────────────────────────────────────────┐
│                  Aerodrome Slipstream Integration                  │
│                                                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │     Factory      │  │  NFT Position    │  │     Quoter      │  │
│  │                  │  │    Manager       │  │                 │  │
│  │ • Pool lookup    │  │                  │  │ • Quote swaps   │  │
│  │ • Tick spacing   │  │ • Mint positions │  │ • Exact input   │  │
│  │   validation     │  │ • Increase liq   │  │ • Exact output  │  │
│  │                  │  │ • Decrease liq   │  │ • Price impact  │  │
│  │                  │  │ • Collect fees   │  │                 │  │
│  │                  │  │ • Burn positions │  │                 │  │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

## Data Structures

### PoolSwapData Struct (Transient Storage)
Temporary swap data for callback validation:
```vyper
struct PoolSwapData:
    pool: address       # Pool executing the swap
    tokenIn: address    # Input token address
    amountIn: uint256   # Input amount
```

### BestPool Struct
Information about the optimal pool for a token pair:
```vyper
struct BestPool:
    pool: address        # Pool contract address
    fee: uint256        # Pool fee rate (normalized to 100_00)
    liquidity: uint256  # Token balances (comparable to reserves)
    numCoins: uint256   # Number of tokens (always 2)
```

### PositionData Struct
Complete position information from NFT:
```vyper
struct PositionData:
    nonce: uint96
    operator: address
    token0: address
    token1: address
    tickSpacing: uint24
    tickLower: int24
    tickUpper: int24
    liquidity: uint128
    feeGrowthInside0LastX128: uint256
    feeGrowthInside1LastX128: uint256
    tokensOwed0: uint128
    tokensOwed1: uint128
```

### MintParams Struct
Parameters for creating new positions:
```vyper
struct MintParams:
    token0: address
    token1: address
    tickSpacing: int24
    tickLower: int24
    tickUpper: int24
    amount0Desired: uint256
    amount1Desired: uint256
    amount0Min: uint256
    amount1Min: uint256
    recipient: address
    deadline: uint256
    sqrtPriceX96: uint160
```

## State Variables

### Immutable Aerodrome Addresses
- `AERO_SLIPSTREAM_FACTORY: public(immutable(address))` - Factory contract
- `AERO_SLIPSTREAM_NFT_MANAGER: public(immutable(address))` - NFT position manager
- `AERO_SLIPSTREAM_QUOTER: public(immutable(address))` - Quote calculator

### Public State Variables
- `coreRouterPool: public(address)` - Core routing pool for optimal paths

### Transient State Variables
- `poolSwapData: transient(PoolSwapData)` - Temporary swap data for callbacks

### Constants
- `TICK_SPACING: constant(int24[5]) = [1, 50, 100, 200, 2000]` - Supported tick spacings
- `MIN_SQRT_RATIO_PLUS_ONE: constant(uint160) = 4295128740` - Min sqrt price
- `MAX_SQRT_RATIO_MINUS_ONE: constant(uint160) = 1461446703485210103287273052203988822378723970341` - Max sqrt price
- `TICK_LOWER: constant(int24) = -887272` - Default lower tick
- `TICK_UPPER: constant(int24) = 887272` - Default upper tick
- `UNISWAP_Q96: constant(uint256) = 2 ** 96` - Uniswap's fixed point scaling
- `MAX_TOKEN_PATH: constant(uint256) = 5` - Maximum tokens in swap path

## Constructor

### `__init__`

Initializes AeroSlipstream with Underscore Protocol and Aerodrome connections.

```vyper
@deploy
def __init__(
    _undyHq: address,
    _aeroFactory: address,
    _aeroNftPositionManager: address,
    _aeroQuoter: address,
    _coreRouterPool: address,
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq contract address |
| `_aeroFactory` | `address` | Slipstream factory contract |
| `_aeroNftPositionManager` | `address` | NFT position manager contract |
| `_aeroQuoter` | `address` | Price quoter contract |
| `_coreRouterPool` | `address` | Core pool for routing |

#### Returns

*Constructor does not return any values*

#### Access

Called only during contract deployment

## Capability Functions

### `hasCapability`

Indicates which action types this Lego supports.

```vyper
@view
@external
def hasCapability(_action: ws.ActionType) -> bool:
```

#### Supported Actions

- `SWAP` - Token swapping through concentrated liquidity pools
- `ADD_LIQ_CONC` - Adding concentrated liquidity
- `REMOVE_LIQ_CONC` - Removing concentrated liquidity

### `onERC721Received`

Handles safe NFT transfers to the contract.

```vyper
@view
@external
def onERC721Received(_operator: address, _owner: address, _tokenId: uint256, _data: Bytes[1024]) -> bytes4:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_operator` | `address` | Address performing the transfer |
| `_owner` | `address` | Previous owner |
| `_tokenId` | `uint256` | NFT token ID |
| `_data` | `Bytes[1024]` | Must be "UE721" for Underscore transfers |

#### Returns

| Type | Description |
|------|-------------|
| `bytes4` | ERC721 receiver selector |

## Token Swap Functions

### `swapTokens`

Executes multi-hop token swaps through concentrated liquidity pools.

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

- `AeroSlipStreamSwap` - Contains swap details including tokens, amounts, USD value, and recipient

#### Example Usage
```python
# Single-hop swap USDC -> WETH
amount_in, amount_out, usd_value = aero_slipstream.swapTokens(
    1000 * 10**6,  # 1000 USDC
    0.3 * 10**18,  # Min 0.3 WETH
    [usdc.address, weth.address],
    [usdc_weth_pool.address],
    user.address
)
```

### `uniswapV3SwapCallback`

Callback function called by pools during swaps.

```vyper
@external
def uniswapV3SwapCallback(_amount0Delta: int256, _amount1Delta: int256, _data: Bytes[256]):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_amount0Delta` | `int256` | Token0 amount change |
| `_amount1Delta` | `int256` | Token1 amount change |
| `_data` | `Bytes[256]` | Callback data (unused) |

#### Access

- Only callable by the pool stored in transient storage
- Validates caller is the expected pool

## Concentrated Liquidity Functions

### `addLiquidityConcentrated`

Adds liquidity to concentrated liquidity pools with custom price ranges.

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
| `_nftTokenId` | `uint256` | Existing NFT ID (0 for new position) |
| `_pool` | `address` | Pool contract address |
| `_tokenA` | `address` | First token address |
| `_tokenB` | `address` | Second token address |
| `_tickLower` | `int24` | Lower price tick (min_value for full range) |
| `_tickUpper` | `int24` | Upper price tick (max_value for full range) |
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
| `uint256` | Liquidity amount added |
| `uint256` | Actual amount of token A added |
| `uint256` | Actual amount of token B added |
| `uint256` | NFT token ID |
| `uint256` | USD value of liquidity added |

#### Access

- Contract must not be paused
- Open to all callers

#### Events Emitted

- `AeroSlipStreamLiquidityAdded` - Contains liquidity details including tokens, amounts, NFT ID, and USD value

#### Example Usage
```python
# Create new concentrated liquidity position
liquidity, amount_a, amount_b, nft_id, usd_value = aero_slipstream.addLiquidityConcentrated(
    0,  # New position
    pool.address,
    usdc.address,
    weth.address,
    -60000,  # Lower tick
    60000,   # Upper tick
    1000 * 10**6,   # 1000 USDC
    0.5 * 10**18,   # 0.5 WETH
    950 * 10**6,    # Min USDC
    0.45 * 10**18,  # Min WETH
    empty(bytes32),
    user.address
)
```

### `removeLiquidityConcentrated`

Removes liquidity from concentrated liquidity positions.

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
| `_liqToRemove` | `uint256` | Amount of liquidity to remove |
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
| `uint256` | Liquidity amount removed |
| `bool` | Whether position was fully depleted and NFT burned |
| `uint256` | USD value of liquidity removed |

#### Access

- Contract must not be paused
- NFT must be owned by this contract

#### Events Emitted

- `AeroSlipStreamLiquidityRemoved` - Contains removal details including tokens, amounts, NFT ID, and USD value

#### Notes

- Automatically collects any accrued fees
- Burns NFT if position is fully depleted
- Transfers NFT back to recipient if position remains

## Pool Query Functions

### `getDeepestLiqPool`

Finds the pool with highest liquidity across all tick spacings.

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

- Checks all 5 tick spacings: [1, 50, 100, 200, 2000]
- Returns pool with highest active liquidity
- Liquidity field contains token balances (not actual liquidity)

### `getBestSwapAmountOut`

Finds the best pool and calculates output for a swap.

```vyper
@external
def getBestSwapAmountOut(_tokenIn: address, _tokenOut: address, _amountIn: uint256) -> (address, uint256):
```

**Note**: This is an external function (not view) due to Quoter requirements.

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

Calculates required input for desired output.

```vyper
@external
def getBestSwapAmountIn(_tokenIn: address, _tokenOut: address, _amountOut: uint256) -> (address, uint256):
```

**Note**: This is an external function (not view) due to Quoter requirements.

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

## Utility Functions

### `getLpToken` / `getPoolForLpToken`

LP token utilities (returns empty for concentrated liquidity).

```vyper
@view
@external
def getLpToken(_pool: address) -> address:
    # No LP tokens for concentrated liquidity
    return empty(address)

@view
@external  
def getPoolForLpToken(_lpToken: address) -> address:
    # No LP tokens for concentrated liquidity
    return empty(address)
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
| `uint256` | Always 0 (placeholder) |

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

### `getPriceUnsafe`

Gets price from pool using sqrt price.

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

### `recoverNft`

Recovers NFT positions sent to the contract.

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
| `bool` | Success status |

#### Access

- Only callable by Switchboard authorized addresses

#### Events Emitted

- `AeroSlipStreamNftRecovered` - Contains collection, NFT ID, and recipient

## Internal Functions

### `_swapTokensInPool`

Executes swap in a specific pool with callback.

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
3. Stores swap data in transient storage
4. Executes swap with appropriate price limits
5. Returns actual output amount

### `_mintNewPosition`

Creates a new concentrated liquidity position.

```vyper
@internal
def _mintNewPosition(...) -> (uint256, uint128, uint256, uint256):
```

### `_increaseExistingPosition`

Adds liquidity to an existing NFT position.

```vyper
@internal
def _increaseExistingPosition(...) -> (uint128, uint256, uint256):
```

### `_collectFees`

Collects accrued fees from a position.

```vyper
@internal
def _collectFees(...) -> (uint256, uint256):
```

### `_getTicks`

Normalizes tick values to valid tick spacing.

```vyper
@view
@internal
def _getTicks(_tickSpacing: int24, _tickLower: int24, _tickUpper: int24) -> (int24, int24):
```

### `_getDeepestLiqPool`

Internal pool discovery across tick spacings.

```vyper
@view
@internal
def _getDeepestLiqPool(_tokenA: address, _tokenB: address) -> (address, int24):
```

### `_getSqrtPriceX96`

Gets current sqrt price from pool slot0.

```vyper
@view
@internal
def _getSqrtPriceX96(_pool: address) -> uint256:
```

## Unimplemented Functions

AeroSlipstream includes placeholder implementations for non-concentrated liquidity functions:

- Yield operations: `depositForYield()`, `withdrawFromYield()`
- Asset minting: `mintOrRedeemAsset()`, `confirmMintOrRedeemAsset()`
- Debt management: `addCollateral()`, `removeCollateral()`, `borrow()`, `repayDebt()`
- Rewards: `claimRewards()`
- Standard liquidity: `addLiquidity()`, `removeLiquidity()`
- Other: `getAccessForLego()`, `getPricePerShare()`, `getPrice()`

All return zero values or empty results.

## Security Considerations

### Callback Security
- Validates callback caller matches expected pool
- Uses transient storage to prevent reentrancy
- Clears transient data after callback completion

### NFT Handling
- Validates NFT ownership before operations
- Safe transfer implementation with data validation
- Automatic fee collection before NFT transfers

### Price Protection
- Uses appropriate sqrt price limits for swaps
- Slippage protection through minimum amounts
- Tick spacing validation for positions

## Integration Patterns

### Swap Workflow
```python
# 1. Get quote for best pool
pool, expected_out = aero_slipstream.getBestSwapAmountOut(
    token_in.address,
    token_out.address,
    swap_amount
)

# 2. Execute swap
amount_in, amount_out, usd_value = user_wallet.swapTokens([{
    'legoId': AERO_SLIPSTREAM_LEGO_ID,
    'amountIn': swap_amount,
    'minAmountOut': int(expected_out * 0.97),  # 3% slippage
    'tokenPath': [token_in.address, token_out.address],
    'poolPath': [pool]
}])
```

### Concentrated Liquidity Workflow
```python
# 1. Create new position with custom range
liquidity, amount_a, amount_b, nft_id, usd = user_wallet.addLiquidityConcentrated(
    AERO_SLIPSTREAM_LEGO_ID,
    0,  # New position
    pool.address,
    token_a.address,
    token_b.address,
    -60000,  # Lower tick
    60000,   # Upper tick
    amount_a,
    amount_b,
    min_a,
    min_b
)

# 2. Add to existing position later
liquidity2, actual_a, actual_b, same_nft_id, usd2 = user_wallet.addLiquidityConcentrated(
    AERO_SLIPSTREAM_LEGO_ID,
    nft_id,  # Existing NFT
    pool.address,
    token_a.address,
    token_b.address,
    0,  # Ignored for existing
    0,  # Ignored for existing
    more_amount_a,
    more_amount_b,
    min_a,
    min_b
)

# 3. Remove liquidity and collect fees
amount_a_out, amount_b_out, liq_removed, depleted, usd3 = user_wallet.removeLiquidityConcentrated(
    AERO_SLIPSTREAM_LEGO_ID,
    nft_id,
    pool.address,
    token_a.address,
    token_b.address,
    liquidity_to_remove,
    min_out_a,
    min_out_b
)
```

## Testing

For comprehensive test examples, see: [`tests/legos/dexes/test_aero_slipstream.py`](../../../../tests/legos/dexes/test_aero_slipstream.py)