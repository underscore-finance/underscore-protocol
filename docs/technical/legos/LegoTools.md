# LegoTools Technical Documentation

[📄 View Source Code](../../../contracts/legos/LegoTools.vy)

## Overview

LegoTools is the unified interface for interacting with all protocol integrations (Legos) in the Underscore Protocol. As a Department contract, it provides discovery and routing services for yield opportunities and decentralized exchanges, abstracting the complexity of multiple protocol integrations behind a simple, consistent API. It serves as the central hub for finding optimal swap routes, managing yield positions, and querying vault tokens across all integrated protocols.

**Core Features**:
- **Yield Protocol Discovery**: Find vault tokens, calculate underlying amounts, and track yield opportunities across multiple protocols
- **DEX Routing Engine**: Intelligent swap routing with multi-hop optimization across various DEX protocols
- **Protocol Abstraction**: Unified interface for Aave, Compound, Euler, Fluid, Moonwell, Morpho, Uniswap, Aerodrome, and Curve
- **Dynamic Integration**: Automatically discovers new Lego partners registered in [LegoBook](../registries/LegoBook.md)
- **Gas-Optimized Routing**: Finds optimal paths considering both price and gas costs

The contract implements sophisticated routing algorithms including single-hop and multi-hop swap optimization, automatic router token bridging (USDC/WETH), yield vault discovery and valuation, protocol-agnostic interfaces, and dynamic slippage management.

## System Architecture Diagram

```
+-------------------------------------------------------------------------+
|                              LegoTools                                  |
+-------------------------------------------------------------------------+
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                     Lego Partner Architecture                      | |
|  |                                                                   | |
|  |  LegoBook Registry:                                               | |
|  |    ├─> Stores all Lego partner addresses                          | |
|  |    ├─> Categorizes as YieldLego or DexLego                        | |
|  |    └─> Dynamic discovery of new integrations                       | |
|  |                                                                   | |
|  |  Yield Legos:                     DEX Legos:                      | |
|  |    • Aave V3                      • Uniswap V2                    | |
|  |    • Compound V3                  • Uniswap V3                    | |
|  |    • Euler                        • Aerodrome                     | |
|  |    • Fluid                        • Aerodrome Slipstream          | |
|  |    • Moonwell                     • Curve                          | |
|  |    • Morpho                                                        | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                      Swap Routing Engine                           | |
|  |                                                                   | |
|  |  Direct Routes:                                                    | |
|  |    tokenA → tokenB (single pool, best price)                       | |
|  |                                                                   | |
|  |  Router Token Routes (USDC/WETH):                                  | |
|  |    tokenA → USDC → tokenB                                          | |
|  |    tokenA → WETH → tokenB                                          | |
|  |    tokenA → USDC → WETH → tokenB                                   | |
|  |                                                                   | |
|  |  Route Selection:                                                  | |
|  |    1. Query all DEX Legos for best rates                          | |
|  |    2. Compare direct vs multi-hop routes                           | |
|  |    3. Account for gas costs and slippage                           | |
|  |    4. Return optimal SwapInstruction array                         | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                      Yield Discovery System                        | |
|  |                                                                   | |
|  |  Vault Token Lookup:                                               | |
|  |    • By underlying asset → find all vault opportunities            | |
|  |    • By vault token → identify protocol and underlying             | |
|  |    • By user → aggregate all yield positions                       | |
|  |                                                                   | |
|  |  Value Calculations:                                               | |
|  |    • Vault tokens → underlying amounts                             | |
|  |    • Underlying amounts → vault tokens                             | |
|  |    • USD valuations via Appraiser integration                      | |
|  +-------------------------------------------------------------------+ |
+-------------------------------------------------------------------------+
```

## Module Integration

LegoTools implements the Department interface and integrates:
- `Addys` module for address registry management
- `DeptBasics` module for pause functionality

## Constants and Immutables

### Router Tokens (Immutable)
- `ROUTER_TOKENA: address` - Primary router token (typically USDC)
- `ROUTER_TOKENB: address` - Secondary router token (typically WETH)

### Yield Lego IDs (Immutable)
- `AAVE_V3_ID: uint256` - Aave V3 protocol ID
- `COMPOUND_V3_ID: uint256` - Compound V3 protocol ID
- `EULER_ID: uint256` - Euler protocol ID
- `FLUID_ID: uint256` - Fluid protocol ID
- `MOONWELL_ID: uint256` - Moonwell protocol ID
- `MORPHO_ID: uint256` - Morpho protocol ID

### DEX Lego IDs (Immutable)
- `UNISWAP_V2_ID: uint256` - Uniswap V2 protocol ID
- `UNISWAP_V3_ID: uint256` - Uniswap V3 protocol ID
- `AERODROME_ID: uint256` - Aerodrome protocol ID
- `AERODROME_SLIPSTREAM_ID: uint256` - Aerodrome concentrated liquidity ID
- `CURVE_ID: uint256` - Curve protocol ID

### Constants
- `MAX_VAULTS_FOR_USER: uint256 = 50` - Maximum vault tokens per user query
- `MAX_VAULTS: uint256 = 40` - Maximum vaults per protocol
- `MAX_ROUTES: uint256 = 10` - Maximum swap routes
- `MAX_TOKEN_PATH: uint256 = 5` - Maximum tokens in swap path
- `MAX_SWAP_INSTRUCTIONS: uint256 = 5` - Maximum swap instructions
- `MAX_LEGOS: uint256 = 10` - Maximum Legos to include
- `HUNDRED_PERCENT: uint256 = 100_00` - 100% in basis points

## Data Structures

### SwapRoute
```vyper
struct SwapRoute:
    legoId: uint256      # Protocol ID for this hop
    pool: address        # Pool address for swap
    tokenIn: address     # Input token
    tokenOut: address    # Output token
    amountIn: uint256    # Input amount
    amountOut: uint256   # Output amount
```

### SwapInstruction
```vyper
struct SwapInstruction:
    legoId: uint256                              # Protocol to execute on
    amountIn: uint256                            # Starting amount
    minAmountOut: uint256                        # Minimum acceptable output
    tokenPath: DynArray[address, MAX_TOKEN_PATH] # Token sequence
    poolPath: DynArray[address, MAX_TOKEN_PATH-1] # Pool sequence
```

### UnderlyingData
```vyper
struct UnderlyingData:
    asset: address       # Underlying asset address
    amount: uint256      # Underlying amount
    usdValue: uint256    # USD value
    legoId: uint256      # Protocol ID
    legoAddr: address    # Protocol address
    legoDesc: String[64] # Protocol description
```

### VaultTokenInfo
```vyper
struct VaultTokenInfo:
    legoId: uint256      # Protocol ID
    vaultToken: address  # Vault token address
```

## Constructor

### `__init__`

Initializes LegoTools with router tokens and protocol IDs.

```vyper
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
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq registry contract |
| `_routerTokenA` | `address` | Primary router token (USDC) |
| `_routerTokenB` | `address` | Secondary router token (WETH) |
| `_aaveV3Id` | `uint256` | Aave V3 registry ID |
| `_compoundV3Id` | `uint256` | Compound V3 registry ID |
| `_eulerId` | `uint256` | Euler registry ID |
| `_fluidId` | `uint256` | Fluid registry ID |
| `_moonwellId` | `uint256` | Moonwell registry ID |
| `_morphoId` | `uint256` | Morpho registry ID |
| `_uniswapV2Id` | `uint256` | Uniswap V2 registry ID |
| `_uniswapV3Id` | `uint256` | Uniswap V3 registry ID |
| `_aerodromeId` | `uint256` | Aerodrome registry ID |
| `_aerodromeSlipstreamId` | `uint256` | Aerodrome Slipstream ID |
| `_curveId` | `uint256` | Curve registry ID |

#### Access

Called only during deployment

#### Notes

- Validates all Lego IDs exist in LegoBook
- Sets immutable protocol references
- Configures router token pair

## Yield Lego Access Functions

### Protocol Address Getters

Functions to retrieve current protocol addresses from LegoBook:

- `aaveV3()` → `address` - Get Aave V3 address
- `compoundV3()` → `address` - Get Compound V3 address
- `euler()` → `address` - Get Euler address
- `fluid()` → `address` - Get Fluid address
- `moonwell()` → `address` - Get Moonwell address
- `morpho()` → `address` - Get Morpho address

### Protocol ID Getters

Functions to retrieve protocol IDs:

- `aaveV3Id()` → `uint256` - Get Aave V3 ID
- `compoundV3Id()` → `uint256` - Get Compound V3 ID
- `eulerId()` → `uint256` - Get Euler ID
- `fluidId()` → `uint256` - Get Fluid ID
- `moonwellId()` → `uint256` - Get Moonwell ID
- `morphoId()` → `uint256` - Get Morpho ID

## DEX Lego Access Functions

### Protocol Address Getters

- `uniswapV2()` → `address` - Get Uniswap V2 address
- `uniswapV3()` → `address` - Get Uniswap V3 address
- `aerodrome()` → `address` - Get Aerodrome address
- `aerodromeSlipstream()` → `address` - Get Aerodrome Slipstream address
- `curve()` → `address` - Get Curve address

### Protocol ID Getters

- `uniswapV2Id()` → `uint256` - Get Uniswap V2 ID
- `uniswapV3Id()` → `uint256` - Get Uniswap V3 ID
- `aerodromeId()` → `uint256` - Get Aerodrome ID
- `aerodromeSlipstreamId()` → `uint256` - Get Aerodrome Slipstream ID
- `curveId()` → `uint256` - Get Curve ID

## Yield Helper Functions

### `getUnderlyingAsset`

Gets the underlying asset for a vault token.

```vyper
@view
@external
def getUnderlyingAsset(_vaultToken: address, _legoBook: address = empty(address)) -> address:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | Vault token to query |
| `_legoBook` | `address` | Optional LegoBook address |

#### Returns

| Type | Description |
|------|-------------|
| `address` | Underlying asset address (empty if not found) |

#### Access

Public view function

#### Example Usage
```python
# Get underlying for vault token
underlying = lego_tools.getUnderlyingAsset(aave_usdc_vault)
# Returns: USDC address
```

### `getUnderlyingForUser`

Gets total underlying amount across all vaults for a user.

```vyper
@view
@external
def getUnderlyingForUser(_user: address, _asset: address, _legoBook: address = empty(address)) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User address |
| `_asset` | `address` | Underlying asset to aggregate |
| `_legoBook` | `address` | Optional LegoBook address |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Total underlying amount across all vaults |

#### Access

Public view function

#### Example Usage
```python
# Get total USDC deposited across all vaults
total_usdc = lego_tools.getUnderlyingForUser(
    user.address,
    usdc.address
)
```

### `getVaultTokensForUser`

Gets all vault tokens held by a user for a specific underlying asset.

```vyper
@view
@external
def getVaultTokensForUser(_user: address, _asset: address, _legoBook: address = empty(address)) -> DynArray[VaultTokenInfo, MAX_VAULTS_FOR_USER]:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User address |
| `_asset` | `address` | Underlying asset |
| `_legoBook` | `address` | Optional LegoBook address |

#### Returns

| Type | Description |
|------|-------------|
| `DynArray[VaultTokenInfo, MAX_VAULTS_FOR_USER]` | Array of vault tokens with protocol IDs |

#### Access

Public view function

### `isVaultToken`

Checks if an address is a recognized vault token.

```vyper
@view
@external
def isVaultToken(_vaultToken: address, _legoBook: address = empty(address)) -> bool:
```

### `getVaultTokenAmount`

Calculates vault tokens needed for a given underlying amount.

```vyper
@view
@external
def getVaultTokenAmount(_asset: address, _assetAmount: uint256, _vaultToken: address, _legoBook: address = empty(address)) -> uint256:
```

### `getUnderlyingData`

Gets comprehensive data about underlying value.

```vyper
@view
@external
def getUnderlyingData(_asset: address, _amount: uint256, _legoBook: address = empty(address)) -> UnderlyingData:
```

### `getLegoInfoFromVaultToken`

Gets detailed protocol information for a vault token.

```vyper
@view
@external
def getLegoInfoFromVaultToken(_vaultToken: address, _legoBook: address = empty(address)) -> (uint256, address, String[64]):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | Vault token to query |
| `_legoBook` | `address` | Optional LegoBook address |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Protocol ID (0 if not found) |
| `address` | Protocol address |
| `String[64]` | Protocol description |

#### Access

Public view function

#### Example Usage
```python
# Get detailed info about a vault
lego_id, lego_addr, description = lego_tools.getLegoInfoFromVaultToken(
    aave_usdc_vault.address
)
# Returns: (2, 0xAaveV3..., "Aave V3 Yield Protocol")
```

#### Notes

- Includes human-readable protocol description
- Useful for UI display and debugging

## DEX Routing Functions

### `getRoutesAndSwapInstructionsAmountOut`

Gets optimal swap routes when specifying input amount.

```vyper
@external
def getRoutesAndSwapInstructionsAmountOut(
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256,
    _slippage: uint256,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS] = [],
) -> DynArray[SwapInstruction, MAX_SWAP_INSTRUCTIONS]:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_tokenIn` | `address` | Input token |
| `_tokenOut` | `address` | Output token |
| `_amountIn` | `uint256` | Amount to swap |
| `_slippage` | `uint256` | Slippage tolerance in basis points |
| `_includeLegoIds` | `DynArray[uint256, MAX_LEGOS]` | Limit to specific protocols |

#### Returns

| Type | Description |
|------|-------------|
| `DynArray[SwapInstruction, MAX_SWAP_INSTRUCTIONS]` | Optimized swap instructions |

#### Access

External function

#### Example Usage
```python
# Get swap route for 1000 USDC to WETH with 0.5% slippage
instructions = lego_tools.getRoutesAndSwapInstructionsAmountOut(
    usdc.address,
    weth.address,
    1000 * 10**6,
    50,  # 0.5%
    []   # Check all protocols
)
```

### `getRoutesAndSwapInstructionsAmountIn`

Gets optimal swap routes when specifying output amount.

```vyper
@external
def getRoutesAndSwapInstructionsAmountIn(
    _tokenIn: address,
    _tokenOut: address,
    _amountOut: uint256,
    _amountInAvailable: uint256,
    _slippage: uint256,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS] = [],
) -> DynArray[SwapInstruction, MAX_SWAP_INSTRUCTIONS]:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_tokenIn` | `address` | Input token |
| `_tokenOut` | `address` | Output token |
| `_amountOut` | `uint256` | Desired output amount |
| `_amountInAvailable` | `uint256` | Maximum input available |
| `_slippage` | `uint256` | Slippage tolerance |
| `_includeLegoIds` | `DynArray[uint256, MAX_LEGOS]` | Protocol filter |

#### Returns

| Type | Description |
|------|-------------|
| `DynArray[SwapInstruction, MAX_SWAP_INSTRUCTIONS]` | Optimized swap instructions |

#### Access

External function

### `getBestSwapRoutesAmountOut`

Gets best swap routes without formatting as instructions.

```vyper
@external
def getBestSwapRoutesAmountOut(
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS] = [],
) -> DynArray[SwapRoute, MAX_ROUTES]:
```

### `getBestSwapAmountOutSinglePool`

Finds best single pool for swap.

```vyper
@external
def getBestSwapAmountOutSinglePool(
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS] = [],
) -> SwapRoute:
```

### `prepareSwapInstructionsAmountOut`

Formats pre-computed routes into swap instructions with slippage.

```vyper
@external
def prepareSwapInstructionsAmountOut(_slippage: uint256, _routes: DynArray[SwapRoute, MAX_ROUTES]) -> DynArray[SwapInstruction, MAX_SWAP_INSTRUCTIONS]:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_slippage` | `uint256` | Slippage tolerance in basis points |
| `_routes` | `DynArray[SwapRoute, MAX_ROUTES]` | Pre-computed swap routes |

#### Returns

| Type | Description |
|------|-------------|
| `DynArray[SwapInstruction, MAX_SWAP_INSTRUCTIONS]` | Formatted swap instructions |

#### Access

External function

#### Example Usage
```python
# Get routes first
routes = lego_tools.getBestSwapRoutesAmountOut(
    token_in, token_out, amount
)

# Format with custom slippage
instructions = lego_tools.prepareSwapInstructionsAmountOut(
    100,    # 1% slippage
    routes
)
```

#### Notes

- Consolidates sequential swaps on same protocol
- Applies slippage to minimum output amounts
- Useful for custom routing strategies

### `getBestSwapAmountOutWithRouterPool`

Finds optimal multi-hop routes using router tokens.

```vyper
@external
def getBestSwapAmountOutWithRouterPool(
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS] = [],
) -> (uint256, DynArray[SwapRoute, MAX_ROUTES]):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_tokenIn` | `address` | Input token |
| `_tokenOut` | `address` | Output token |
| `_amountIn` | `uint256` | Amount to swap |
| `_includeLegoIds` | `DynArray[uint256, MAX_LEGOS]` | Protocol filter |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Best output amount achievable |
| `DynArray[SwapRoute, MAX_ROUTES]` | Optimal route sequence |

#### Access

External function

#### Example Usage
```python
# Find best route through USDC/WETH
amount_out, routes = lego_tools.getBestSwapAmountOutWithRouterPool(
    dai.address,
    link.address,
    1000 * 10**18
)
```

#### Notes

- Explores paths through USDC and WETH
- Returns (0, []) if direct route is better
- Handles 2-hop and 3-hop routes automatically

### `getSwapAmountOutViaRouterPool`

Gets swap rate specifically between router tokens.

```vyper
@external
def getSwapAmountOutViaRouterPool(
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS] = [],
) -> SwapRoute:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_tokenIn` | `address` | Router token A or B |
| `_tokenOut` | `address` | Router token B or A |
| `_amountIn` | `uint256` | Amount to swap |
| `_includeLegoIds` | `DynArray[uint256, MAX_LEGOS]` | Protocol filter |

#### Returns

| Type | Description |
|------|-------------|
| `SwapRoute` | Best route for router token swap |

#### Access

External function

#### Example Usage
```python
# Get best USDC → WETH route
route = lego_tools.getSwapAmountOutViaRouterPool(
    usdc.address,
    weth.address,
    10000 * 10**6  # 10,000 USDC
)
```

#### Notes

- Only works for router token pairs (USDC/WETH)
- Queries getCoreRouterPool() from each DEX
- Essential for multi-hop routing

## Routing Algorithm

### Direct Route Discovery

1. **Single Pool Search**: Query all DEX Legos for direct pools
2. **Price Comparison**: Select pool with best output amount
3. **Gas Optimization**: Consider gas costs for different protocols

### Multi-Hop Routing

Router tokens (USDC/WETH) enable efficient multi-hop swaps:

1. **Two-Hop Routes**:
   - `Token → USDC → Token`
   - `Token → WETH → Token`

2. **Three-Hop Routes**:
   - `Token → USDC → WETH → Token`
   - `Token → WETH → USDC → Token`

3. **Route Selection**:
   - Compare all possible paths
   - Account for price impact and fees
   - Select optimal route considering total output

### SwapInstruction Generation

Routes are consolidated into instructions:
- Sequential swaps on same protocol merge into one instruction
- Protocol changes create new instructions
- Slippage applied to final output of each instruction

## DEX Routing Functions - Amount In

These functions calculate the required input amount for a desired output amount, useful for exact output swaps.

### `getRoutesAndSwapInstructionsAmountIn`

Gets optimal swap routes when specifying desired output amount.

```vyper
@external
def getRoutesAndSwapInstructionsAmountIn(
    _tokenIn: address,
    _tokenOut: address,
    _amountOut: uint256,
    _amountInAvailable: uint256,
    _slippage: uint256,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS] = [],
) -> DynArray[SwapInstruction, MAX_SWAP_INSTRUCTIONS]:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_tokenIn` | `address` | Input token |
| `_tokenOut` | `address` | Output token |
| `_amountOut` | `uint256` | Desired output amount |
| `_amountInAvailable` | `uint256` | Maximum input available |
| `_slippage` | `uint256` | Slippage tolerance in basis points |
| `_includeLegoIds` | `DynArray[uint256, MAX_LEGOS]` | Protocol filter |

#### Returns

| Type | Description |
|------|-------------|
| `DynArray[SwapInstruction, MAX_SWAP_INSTRUCTIONS]` | Optimized swap instructions |

#### Access

External function

#### Example Usage
```python
# Want exactly 1 WETH, have up to 2000 USDC
instructions = lego_tools.getRoutesAndSwapInstructionsAmountIn(
    usdc.address,
    weth.address,
    1 * 10**18,      # Want 1 WETH
    2000 * 10**6,    # Have 2000 USDC max
    50               # 0.5% slippage
)
```

#### Notes

- Calculates minimum input needed for exact output
- Re-runs with amount-out logic for accuracy
- Handles protocols without exact amount-in support

### `getBestSwapRoutesAmountIn`

Gets best swap routes for exact output without formatting.

```vyper
@external
def getBestSwapRoutesAmountIn(
    _tokenIn: address,
    _tokenOut: address,
    _amountOut: uint256,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS] = [],
) -> DynArray[SwapRoute, MAX_ROUTES]:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_tokenIn` | `address` | Input token |
| `_tokenOut` | `address` | Output token |
| `_amountOut` | `uint256` | Desired output amount |
| `_includeLegoIds` | `DynArray[uint256, MAX_LEGOS]` | Protocol filter |

#### Returns

| Type | Description |
|------|-------------|
| `DynArray[SwapRoute, MAX_ROUTES]` | Optimal routes for exact output |

#### Access

External function

### `getBestSwapAmountInSinglePool`

Finds best single pool for exact output swap.

```vyper
@external
def getBestSwapAmountInSinglePool(
    _tokenIn: address,
    _tokenOut: address,
    _amountOut: uint256,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS] = [],
) -> SwapRoute:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_tokenIn` | `address` | Input token |
| `_tokenOut` | `address` | Output token |
| `_amountOut` | `uint256` | Desired output amount |
| `_includeLegoIds` | `DynArray[uint256, MAX_LEGOS]` | Protocol filter |

#### Returns

| Type | Description |
|------|-------------|
| `SwapRoute` | Best route with minimum input required |

#### Access

External function

#### Example Usage
```python
# Find minimum USDC needed for 1 WETH
route = lego_tools.getBestSwapAmountInSinglePool(
    usdc.address,
    weth.address,
    1 * 10**18  # Want exactly 1 WETH
)
print(f"Need {route.amountIn} USDC")
```

### `getBestSwapAmountInWithRouterPool`

Finds optimal multi-hop routes for exact output using router tokens.

```vyper
@external
def getBestSwapAmountInWithRouterPool(
    _tokenIn: address,
    _tokenOut: address,
    _amountOut: uint256,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS] = [],
) -> (uint256, DynArray[SwapRoute, MAX_ROUTES]):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_tokenIn` | `address` | Input token |
| `_tokenOut` | `address` | Output token |
| `_amountOut` | `uint256` | Desired output amount |
| `_includeLegoIds` | `DynArray[uint256, MAX_LEGOS]` | Protocol filter |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Minimum input amount required |
| `DynArray[SwapRoute, MAX_ROUTES]` | Optimal route sequence |

#### Access

External function

#### Notes

- Returns `max_value(uint256)` for amount if no route found
- Explores all router token paths
- Selects route requiring minimum input

### `getSwapAmountInViaRouterPool`

Gets minimum input for exact output swap between router tokens.

```vyper
@external
def getSwapAmountInViaRouterPool(
    _tokenIn: address,
    _tokenOut: address,
    _amountOut: uint256,
    _includeLegoIds: DynArray[uint256, MAX_LEGOS] = [],
) -> SwapRoute:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_tokenIn` | `address` | Router token A or B |
| `_tokenOut` | `address` | Router token B or A |
| `_amountOut` | `uint256` | Desired output amount |
| `_includeLegoIds` | `DynArray[uint256, MAX_LEGOS]` | Protocol filter |

#### Returns

| Type | Description |
|------|-------------|
| `SwapRoute` | Route with minimum input for exact output |

#### Access

External function

#### Example Usage
```python
# How much USDC needed for exactly 1 WETH?
route = lego_tools.getSwapAmountInViaRouterPool(
    usdc.address,
    weth.address,
    1 * 10**18
)
print(f"Need {route.amountIn} USDC for 1 WETH")
```

## Security Considerations

### Access Control
- Read-only for most query functions
- State changes restricted to Department interface
- Protocol discovery through secure LegoBook registry

### Routing Security
- Slippage protection on all swaps
- Maximum path length limits
- Validated pool addresses from registered Legos

### Integration Safety
- Dynamic protocol discovery prevents hardcoded risks
- Fallback handling for failed protocol queries
- Gas limits through bounded loops

## Common Integration Patterns

### Yield Position Discovery
```python
# Find all vaults for USDC
vault_tokens = lego_tools.getVaultTokensForUser(
    user.address,
    usdc.address
)

# Get total underlying value
total_usdc = lego_tools.getUnderlyingForUser(
    user.address,
    usdc.address
)
```

### Optimal Swap Execution
```python
# Get swap instructions
instructions = lego_tools.getRoutesAndSwapInstructionsAmountOut(
    token_in,
    token_out,
    amount,
    slippage
)

# Execute through UserWallet
for instruction in instructions:
    wallet.swapTokens(instruction)
```

### Vault Token Identification
```python
# Check if token is vault
if lego_tools.isVaultToken(token):
    # Get protocol info
    lego_id, lego_addr, description = lego_tools.getLegoInfoFromVaultToken(token)
    
    # Get underlying
    underlying = lego_tools.getUnderlyingAsset(token)
```

### Multi-Protocol Yield Aggregation
```python
# Get all USDC vaults for user
vaults = lego_tools.getVaultTokensForUser(user, usdc)

# Calculate total value
total_value = 0
for vault_info in vaults:
    balance = vault_token.balanceOf(user)
    underlying = yield_lego.getUnderlyingAmount(
        vault_info.vaultToken,
        balance
    )
    total_value += underlying
```

## Testing

For comprehensive test examples, see: [`tests/legos/`](../../../tests/legos/)