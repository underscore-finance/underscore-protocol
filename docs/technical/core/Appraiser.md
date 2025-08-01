# Appraiser Technical Documentation

[📄 View Source Code](../../../contracts/core/Appraiser.vy)

## Overview

Appraiser is the price oracle and valuation engine for the Underscore Protocol. As a Department contract, it provides accurate price calculations for all assets including normal tokens and yield-bearing vaults, handles yield profit calculations with performance fee support, and integrates with multiple price sources for reliability while maintaining an efficient caching mechanism.

**Core Features**:
- **Multi-Source Pricing**: Integrates RipePriceDesk and Lego partners for price feeds
- **Yield Asset Support**: Specialized handling for vault tokens with price-per-share calculations
- **Profit Calculation**: Tracks yield profits for both rebasing and non-rebasing assets
- **Price Caching**: Block-level caching with configurable staleness thresholds
- **USD Valuation**: Comprehensive USD value calculations for portfolio management

The contract implements sophisticated pricing logic including fallback mechanisms for price sources, automatic yield profit detection, performance fee calculations, maximum yield increase caps for security, and efficient state management with caching.

## System Architecture Diagram

```
+-------------------------------------------------------------------------+
|                               Appraiser                                 |
+-------------------------------------------------------------------------+
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                       Price Flow Architecture                      | |
|  |                                                                   | |
|  |  Normal Assets:                                                   | |
|  |    1. Check cache (same block → return cached)                    | |
|  |    2. Check staleness (recent enough → return cached)             | |
|  |    3. Query RipePriceDesk (primary source)                         | |
|  |    4. Fallback to Lego partner (if Ripe fails)                    | |
|  |    5. Update cache and return                                      | |
|  |                                                                   | |
|  |  Yield Assets:                                                     | |
|  |    1. Get price per share from Lego partner                       | |
|  |    2. Fallback to RipePriceDesk if needed                         | |
|  |    3. If has underlying asset:                                    | |
|  |       └─> Price = Underlying Price × Price Per Share              | |
|  |    4. Update cache and notify Ripe for snapshot                   | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                     Yield Profit Calculation                       | |
|  |                                                                   | |
|  |  Rebasing Assets:                                                  | |
|  |    • Profit = Current Balance - Last Balance                      | |
|  |    • Apply max yield increase cap if configured                   | |
|  |    • Return profit amount and performance fee                     | |
|  |                                                                   | |
|  |  Non-Rebasing Vaults:                                              | |
|  |    • Track price per share changes                                | |
|  |    • Calculate profit on tracked balance                          | |
|  |    • Convert to vault tokens for withdrawal                       | |
|  |    • Apply max yield cap and performance fee                      | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                        Caching Strategy                            | |
|  |                                                                   | |
|  |  Cache Levels:                                                    | |
|  |    1. Block-level: Always return cached for same block            | |
|  |    2. Staleness: Return cached if within stale blocks             | |
|  |    3. Update: Fetch new price and update cache                    | |
|  |                                                                   | |
|  |  Cache Storage:                                                    | |
|  |    • lastPrice[asset] → {price, lastUpdate}                       | |
|  |    • lastPricePerShare[asset] → {pricePerShare, lastUpdate}      | |
|  +-------------------------------------------------------------------+ |
+-------------------------------------------------------------------------+
```

## Module Integration

Appraiser implements the Department interface and integrates:
- `Addys` module for address registry management
- `DeptBasics` module for pause functionality

## Constants

- `HUNDRED_PERCENT: uint256 = 100_00` - 100% in basis points
- `RIPE_PRICE_DESK_ID: uint256 = 7` - Registry ID for RipePriceDesk

## Immutable Variables

- `RIPE_HQ: address` - Ripe protocol registry address
- `WETH: address` - Wrapped ETH address
- `ETH: address` - ETH placeholder address

## Constructor

### `__init__`

Initializes Appraiser with registry addresses.

```vyper
@deploy
def __init__(
    _undyHq: address,
    _ripeHq: address,
    _wethAddr: address,
    _ethAddr: address,
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq registry contract address |
| `_ripeHq` | `address` | RipeHq registry contract address |
| `_wethAddr` | `address` | WETH token address |
| `_ethAddr` | `address` | ETH placeholder address |

#### Access

Called only during deployment

#### Example Usage
```python
appraiser = Appraiser.deploy(
    undy_hq.address,
    ripe_hq.address,
    weth.address,
    "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
)
```

## Yield Handling Functions

### `calculateYieldProfits`

Calculates yield profits for a position with state updates.

```vyper
@external
def calculateYieldProfits(
    _asset: address,
    _currentBalance: uint256,
    _lastBalance: uint256,
    _lastPricePerShare: uint256,
    _missionControl: address,
    _legoBook: address,
) -> (uint256, uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Yield asset address |
| `_currentBalance` | `uint256` | Current balance of asset |
| `_lastBalance` | `uint256` | Previous balance of asset |
| `_lastPricePerShare` | `uint256` | Previous price per share |
| `_missionControl` | `address` | MissionControl address (optional) |
| `_legoBook` | `address` | LegoBook address (optional) |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | New price per share (0 for rebasing) |
| `uint256` | Profit amount in asset tokens |
| `uint256` | Performance fee percentage |

#### Access

Can only be called by user wallets

#### Example Usage
```python
# Calculate yield profits for vault position
new_pps, profit, fee = appraiser.calculateYieldProfits(
    vault_token.address,
    current_balance,
    last_balance,
    last_price_per_share,
    mission_control.address,
    lego_book.address
)
```

#### Notes

- Fails gracefully if paused
- Returns (0, 0, 0) for non-yield assets
- Handles both rebasing and non-rebasing assets
- Updates price per share cache

### `calculateYieldProfitsNoUpdate`

Calculates yield profits without updating state (view function).

```vyper
@view
@external
def calculateYieldProfitsNoUpdate(
    _legoId: uint256,
    _asset: address,
    _underlyingAsset: address,
    _currentBalance: uint256,
    _lastBalance: uint256,
    _lastPricePerShare: uint256,
) -> (uint256, uint256, uint256):
```

#### Parameters

Similar to `calculateYieldProfits` but includes `_legoId` and `_underlyingAsset`

#### Returns

Same as `calculateYieldProfits`

#### Access

Public view function

## High-Level Price Functions

### `getUsdValue`

Gets USD value for an asset amount.

```vyper
@view
@external
def getUsdValue(
    _asset: address,
    _amount: uint256,
    _missionControl: address = empty(address),
    _legoBook: address = empty(address),
    _ledger: address = empty(address),
) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Asset address |
| `_amount` | `uint256` | Amount of asset |
| `_missionControl` | `address` | Optional MissionControl |
| `_legoBook` | `address` | Optional LegoBook |
| `_ledger` | `address` | Optional Ledger |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | USD value of the amount |

#### Access

Public view function

#### Example Usage
```python
# Get USD value of 1000 USDC
usd_value = appraiser.getUsdValue(
    usdc.address,
    1000 * 10**6
)
```

### `getPrice`

Gets price for an asset.

```vyper
@view
@external
def getPrice(
    _asset: address,
    _missionControl: address = empty(address),
    _legoBook: address = empty(address),
    _ledger: address = empty(address),
) -> uint256:
```

#### Parameters

Same as `getUsdValue` except no `_amount`

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Price per unit with asset decimals |

#### Access

Public view function

### `updatePriceAndGetUsdValue`

Updates price cache and returns USD value.

```vyper
@external
def updatePriceAndGetUsdValue(
    _asset: address,
    _amount: uint256,
    _missionControl: address = empty(address),
    _legoBook: address = empty(address),
) -> uint256:
```

#### Parameters

Same as `getUsdValue`

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | USD value of the amount |

#### Access

- User wallets
- Valid Undy addresses
- Registered backpack items

#### Notes

- Updates price cache
- Fails gracefully if paused
- Enforces permission checks

### `updatePriceAndGetUsdValueAndIsYieldAsset`

Updates price and returns USD value with yield asset flag.

```vyper
@external
def updatePriceAndGetUsdValueAndIsYieldAsset(
    _asset: address,
    _amount: uint256,
    _missionControl: address = empty(address),
    _legoBook: address = empty(address),
) -> (uint256, bool):
```

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | USD value |
| `bool` | Whether asset is yield-bearing |

#### Access

- User wallets
- Valid Undy addresses

## Normal Asset Price Functions

### `getNormalAssetPrice`

Gets price for non-yield assets.

```vyper
@view
@external
def getNormalAssetPrice(
    _asset: address,
    _missionControl: address = empty(address),
    _legoBook: address = empty(address),
    _ledger: address = empty(address),
) -> uint256:
```

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Asset price (0 for yield assets) |

#### Access

Public view function

### `updateAndGetNormalAssetPrice`

Updates and gets price for normal assets.

```vyper
@external
def updateAndGetNormalAssetPrice(
    _asset: address,
    _missionControl: address = empty(address),
    _legoBook: address = empty(address),
) -> uint256:
```

#### Access

- User wallets
- Valid Undy addresses

## Yield Asset Price Functions

### `getPricePerShare`

Gets price per share for yield assets.

```vyper
@view
@external
def getPricePerShare(
    _asset: address,
    _missionControl: address = empty(address),
    _legoBook: address = empty(address),
    _ledger: address = empty(address),
) -> uint256:
```

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Price per share with asset decimals |

#### Access

Public view function

### `getPricePerShareWithConfig`

Gets price per share with explicit configuration.

```vyper
@view
@external
def getPricePerShareWithConfig(
    _asset: address,
    _legoAddr: address,
    _staleBlocks: uint256,
    _decimals: uint256,
) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Asset address |
| `_legoAddr` | `address` | Lego partner address |
| `_staleBlocks` | `uint256` | Cache staleness threshold |
| `_decimals` | `uint256` | Asset decimals |

#### Access

Public view function

### `updateAndGetPricePerShare`

Updates and gets price per share.

```vyper
@external
def updateAndGetPricePerShare(
    _asset: address,
    _missionControl: address = empty(address),
    _legoBook: address = empty(address),
) -> uint256:
```

#### Access

- User wallets
- Valid Undy addresses

#### Notes

- Updates cache
- Notifies Ripe for snapshot update

## Ripe Integration Functions

### `getRipePrice`

Gets price from RipePriceDesk.

```vyper
@view
@external
def getRipePrice(_asset: address) -> uint256:
```

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Price from Ripe (0 if unavailable) |

#### Access

Public view function

## Configuration Functions

### `getProfitCalcConfig`

Gets profit calculation configuration.

```vyper
@view
@external
def getProfitCalcConfig(_asset: address) -> ProfitCalcConfig:
```

#### Returns

`ProfitCalcConfig` struct containing:
- `legoId` - Protocol integration ID
- `legoAddr` - Protocol address
- `decimals` - Asset decimals
- `staleBlocks` - Cache threshold
- `isYieldAsset` - Yield asset flag
- `isRebasing` - Rebasing flag
- `underlyingAsset` - Underlying for vaults
- `maxYieldIncrease` - Yield cap percentage
- `performanceFee` - Fee percentage

#### Access

Public view function

### `getAssetUsdValueConfig`

Gets asset USD value configuration.

```vyper
@view
@external
def getAssetUsdValueConfig(_asset: address) -> AssetUsdValueConfig:
```

#### Returns

`AssetUsdValueConfig` struct containing:
- `legoId` - Protocol integration ID
- `legoAddr` - Protocol address
- `decimals` - Asset decimals
- `staleBlocks` - Cache threshold
- `isYieldAsset` - Yield asset flag
- `underlyingAsset` - Underlying asset

#### Access

Public view function

## Internal Pricing Logic

### Price Source Priority

**Normal Assets**:
1. RipePriceDesk (primary)
2. Lego partner (fallback)

**Yield Assets**:
1. Lego partner (primary)
2. RipePriceDesk (fallback)

### Yield Profit Calculation

**Rebasing Assets**:
```
Profit = Current Balance - Last Balance
If max cap: Profit = min(Profit, Last Balance × Max Yield %)
```

**Non-Rebasing Vaults**:
```
Tracked Balance = min(Current Balance, Last Balance)
Profit (underlying) = Tracked × (Current PPS - Last PPS) / Decimals
If max cap: Apply same logic
Convert back to vault tokens for withdrawal
```

### Caching Strategy

1. **Same Block**: Always return cached price
2. **Staleness Check**: If within `staleBlocks`, return cached
3. **Update**: Fetch new price and update cache

## Security Considerations

### Access Control
- User wallet validation for state-changing functions
- Backpack item permissions for pricing updates
- Valid Undy address checks

### Price Manipulation Protection
- Block-level caching prevents same-block manipulation
- Staleness thresholds for efficient updates
- Multiple price sources with fallback

### Yield Security
- Maximum yield increase caps
- Performance fee deduction
- Tracked balance for dilution protection

### Pause Protection
- Graceful failure when paused
- Critical functions return safe defaults
- No reverts that could block operations

## Common Integration Patterns

### Basic Price Queries
```python
# Get current price
price = appraiser.getPrice(token.address)

# Get USD value
usd_value = appraiser.getUsdValue(
    token.address,
    amount
)
```

### Yield Profit Tracking
```python
# Track yield profits
new_pps, profit, fee = appraiser.calculateYieldProfits(
    vault.address,
    current_balance,
    last_balance,
    last_pps,
    mission_control,
    lego_book
)

# Calculate fee amount
fee_amount = profit * fee / 10000
```

### Price Updates for Valuation
```python
# Update and get USD value
usd_value = appraiser.updatePriceAndGetUsdValue(
    asset.address,
    balance
)

# Check if yield asset
usd_value, is_yield = appraiser.updatePriceAndGetUsdValueAndIsYieldAsset(
    asset.address,
    balance
)
```

### Configuration Queries
```python
# Get asset config
config = appraiser.getAssetUsdValueConfig(asset)

if config.isYieldAsset:
    # Handle as vault
    pps = appraiser.getPricePerShare(asset)
else:
    # Handle as normal token
    price = appraiser.getNormalAssetPrice(asset)
```

### Price Source Fallback
```python
# Try Ripe first
ripe_price = appraiser.getRipePrice(asset)

if ripe_price == 0:
    # Use full pricing logic with fallbacks
    price = appraiser.getPrice(asset)
```

## Testing

For comprehensive test examples, see: [`tests/core/test_appraiser.py`](../../../tests/core/test_appraiser.py)