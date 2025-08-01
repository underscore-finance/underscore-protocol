# YieldLegoData Technical Documentation

[📄 View Source Code](../../../contracts/modules/YieldLegoData.vy)

## Overview

YieldLegoData is a specialized data management module for yield protocol integrations (Yield Legos) in the Underscore Protocol. It provides a structured way to track and manage vault opportunities across different underlying assets, maintaining relationships between assets and their corresponding yield vaults while offering efficient data access patterns for discovery and validation.

**Core Features**:
- **Asset Opportunity Tracking**: Maps underlying assets to their available yield vaults
- **Bidirectional Mapping**: Efficient lookups from asset to vaults and vault to asset
- **Indexed Storage**: Iterable data structures for asset and vault discovery
- **Pause Control**: Emergency pause functionality for security
- **Fund Recovery**: Secure mechanism to recover stuck funds

The module implements sophisticated storage patterns including dual-direction mappings for O(1) lookups, indexed arrays for iteration support, automatic asset lifecycle management, and gas-efficient removal operations with array compaction.

## System Architecture Diagram

```
+-------------------------------------------------------------------------+
|                           YieldLegoData                                 |
+-------------------------------------------------------------------------+
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                    Storage Architecture                            | |
|  |                                                                   | |
|  |  Asset Opportunities:                                             | |
|  |    ┌─────────────┐      ┌──────────────────┐                     | |
|  |    │ Asset (USDC)│ ───> │ Vault 1: aUSDC   │                     | |
|  |    │             │      │ Vault 2: cUSDC   │                     | |
|  |    │             │      │ Vault 3: mUSDC   │                     | |
|  |    └─────────────┘      └──────────────────┘                     | |
|  |                                                                   | |
|  |  Bidirectional Mappings:                                          | |
|  |    • assetOpportunities[asset][index] → vault                     | |
|  |    • indexOfAssetOpportunity[asset][vault] → index                | |
|  |    • vaultToAsset[vault] → asset                                  | |
|  |                                                                   | |
|  |  Asset Registry (Indexed):                                        | |
|  |    • assets[index] → asset address                                | |
|  |    • indexOfAsset[asset] → index                                  | |
|  |    • 1-based indexing (0 = not registered)                        | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                    Lifecycle Management                            | |
|  |                                                                   | |
|  |  Asset Addition:                                                   | |
|  |    1. First vault for asset → Register asset                      | |
|  |    2. Add vault to opportunities array                            | |
|  |    3. Update all mappings                                          | |
|  |                                                                   | |
|  |  Asset Removal:                                                    | |
|  |    1. Remove vault from opportunities                             | |
|  |    2. Compact array (move last to removed position)              | |
|  |    3. Last vault removed → Unregister asset                       | |
|  |                                                                   | |
|  |  Automatic Cleanup:                                                | |
|  |    • Assets with no vaults are automatically removed              | |
|  |    • Maintains data consistency and gas efficiency                | |
|  +-------------------------------------------------------------------+ |
+-------------------------------------------------------------------------+
```

## Module Dependencies

YieldLegoData uses the `Addys` module for:
- Address registry access
- Permission validation (switchboard checks)
- Protocol address lookups

## Constants

- `MAX_VAULTS: uint256 = 40` - Maximum vaults per asset
- `MAX_ASSETS: uint256 = 20` - Maximum assets to return in queries
- `MAX_RECOVER_ASSETS: uint256 = 20` - Maximum assets per recovery call

## State Variables

### Configuration
- `isPaused: bool` - Emergency pause state

### Asset Opportunity Storage
- `assetOpportunities: HashMap[address, HashMap[uint256, address]]` - Asset to indexed vault mapping
- `indexOfAssetOpportunity: HashMap[address, HashMap[address, uint256]]` - Asset/vault to index mapping
- `numAssetOpportunities: HashMap[address, uint256]` - Vault count per asset

### Vault Mapping
- `vaultToAsset: HashMap[address, address]` - Vault to underlying asset mapping

### Asset Registry
- `assets: HashMap[uint256, address]` - Indexed asset array
- `indexOfAsset: HashMap[address, uint256]` - Asset to index mapping
- `numAssets: uint256` - Total registered assets + 1

## Constructor

### `__init__`

Initializes the module with pause state.

```vyper
@deploy
def __init__(_shouldPause: bool):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_shouldPause` | `bool` | Initial pause state |

#### Access

Called only during deployment

#### Example Usage
```python
# Deploy with initial pause
yield_data = YieldLegoData.deploy(True)

# Deploy active
yield_data = YieldLegoData.deploy(False)
```

## View Functions

### `isLegoAsset`

Checks if an asset is registered in the system.

```vyper
@view
@external
def isLegoAsset(_asset: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Asset address to check |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if asset has registered vaults |

#### Access

Public view function

#### Example Usage
```python
# Check if USDC has yield opportunities
has_vaults = yield_data.isLegoAsset(usdc.address)
```

### `getAssetOpportunities`

Gets all vault addresses for an asset.

```vyper
@view
@external
def getAssetOpportunities(_asset: address) -> DynArray[address, MAX_VAULTS]:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Underlying asset address |

#### Returns

| Type | Description |
|------|-------------|
| `DynArray[address, MAX_VAULTS]` | Array of vault addresses |

#### Access

Public view function

#### Example Usage
```python
# Get all USDC vault opportunities
usdc_vaults = yield_data.getAssetOpportunities(usdc.address)
# Returns: [aUSDC, cUSDC, mUSDC, ...]
```

### `getAssets`

Gets all registered assets.

```vyper
@view
@external
def getAssets() -> DynArray[address, MAX_ASSETS]:
```

#### Returns

| Type | Description |
|------|-------------|
| `DynArray[address, MAX_ASSETS]` | Array of asset addresses |

#### Access

Public view function

### `isAssetOpportunity`

Checks if a vault is registered for an asset.

```vyper
@view
@external
def isAssetOpportunity(_asset: address, _vaultAddr: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Underlying asset |
| `_vaultAddr` | `address` | Vault address |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if vault is registered for asset |

#### Access

Public view function

### `getNumLegoAssets`

Gets the actual number of registered assets.

```vyper
@view
@external
def getNumLegoAssets() -> uint256:
```

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Number of registered assets |

#### Access

Public view function

#### Notes

Returns `numAssets - 1` due to 1-based indexing

## Internal Registration Functions

### `_addAssetOpportunity`

Registers a vault opportunity for an asset.

```vyper
@internal
def _addAssetOpportunity(_asset: address, _vaultAddr: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Underlying asset |
| `_vaultAddr` | `address` | Vault to register |

#### Events Emitted

- `AssetOpportunityAdded` - Contains asset (indexed) and vaultAddr (indexed)

#### Logic Flow

1. Check if already registered (skip if yes)
2. Validate addresses not empty
3. Add to opportunities array
4. Update index mapping
5. Set vault to asset mapping
6. Register asset if first vault

### `_removeAssetOpportunity`

Removes a vault opportunity from an asset.

```vyper
@internal
def _removeAssetOpportunity(_asset: address, _vaultAddr: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Underlying asset |
| `_vaultAddr` | `address` | Vault to remove |

#### Events Emitted

- `AssetOpportunityRemoved` - Contains asset (indexed) and vaultAddr (indexed)

#### Logic Flow

1. Check if registered (skip if not)
2. Get vault index
3. Move last vault to removed position
4. Update mappings
5. Remove asset if last vault

## Administrative Functions

### `pause`

Toggle emergency pause state.

```vyper
@external
def pause(_shouldPause: bool):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_shouldPause` | `bool` | New pause state |

#### Access

Only callable by switchboard addresses

#### Events Emitted

- `LegoPauseModified` - Contains isPaused state

#### Example Usage
```python
# Pause the module
yield_data.pause(True, sender=switchboard)

# Resume operations
yield_data.pause(False, sender=switchboard)
```

### `recoverFunds`

Recovers stuck tokens from the contract.

```vyper
@external
def recoverFunds(_recipient: address, _asset: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_recipient` | `address` | Address to receive funds |
| `_asset` | `address` | Token to recover |

#### Access

Only callable by switchboard addresses

#### Events Emitted

- `LegoFundsRecovered` - Contains asset (indexed), recipient (indexed), and balance

### `recoverFundsMany`

Recovers multiple tokens in one transaction.

```vyper
@external
def recoverFundsMany(_recipient: address, _assets: DynArray[address, MAX_RECOVER_ASSETS]):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_recipient` | `address` | Address to receive funds |
| `_assets` | `DynArray[address, MAX_RECOVER_ASSETS]` | Tokens to recover |

#### Access

Only callable by switchboard addresses

## Internal Helper Functions

### `_getMiniAddys`

Gets or fills MiniAddys struct for protocol addresses.

```vyper
@view
@internal
def _getMiniAddys(_miniAddys: ws.MiniAddys = empty(ws.MiniAddys)) -> ws.MiniAddys:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_miniAddys` | `MiniAddys` | Optional pre-filled addresses |

#### Returns

| Type | Description |
|------|-------------|
| `MiniAddys` | Filled address struct |

## Storage Patterns

### 1-Based Indexing

All indexed arrays use 1-based indexing where:
- Index 0 indicates "not registered"
- Valid indices start at 1
- Simplifies existence checks

### Array Compaction

When removing elements:
1. Move last element to removed position
2. Update index mapping for moved element
3. Decrement count
4. Maintains O(1) removal complexity

### Automatic Lifecycle

Assets are automatically:
- Added when first vault registered
- Removed when last vault unregistered
- Ensures clean state management

## Security Considerations

### Access Control
- Only switchboard can pause/unpause
- Only switchboard can recover funds
- Internal functions for registration (used by Lego contracts)

### State Validation
- Empty address checks
- Duplicate registration prevention
- Array bounds enforcement

### Emergency Controls
- Pause mechanism for security incidents
- Fund recovery for stuck tokens
- No user funds at risk (data only)

## Integration Patterns

### Vault Registration (from Yield Lego)
```python
# In yield protocol integration
def addAssetOpportunity(_asset: address, _vault: address):
    # Permission checks
    assert msg.sender == authorized
    
    # Register vault
    self._addAssetOpportunity(_asset, _vault)
```

### Vault Discovery
```python
# Find all vaults for an asset
vaults = yield_data.getAssetOpportunities(usdc.address)

# Check specific vault
is_valid = yield_data.isAssetOpportunity(
    usdc.address,
    aave_usdc_vault
)
```

### Asset Iteration
```python
# Get all assets with vaults
assets = yield_data.getAssets()

# Process each asset
for asset in assets:
    vaults = yield_data.getAssetOpportunities(asset)
    # Process vaults
```

## Testing

For comprehensive test examples, see: [`tests/modules/`](../../../tests/modules/)