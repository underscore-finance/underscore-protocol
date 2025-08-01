# DexLegoData Technical Documentation

[📄 View Source Code](../../../contracts/modules/DexLegoData.vy)

## Overview

DexLegoData is a streamlined data management module for DEX protocol integrations (DEX Legos) in the Underscore Protocol. It provides essential shared functionality for all DEX integrations including pause control, fund recovery, and address management while maintaining a minimal footprint compared to its yield counterpart.

**Core Features**:
- **Pause Control**: Emergency pause functionality for security incidents
- **Fund Recovery**: Secure mechanism to recover stuck tokens
- **Address Management**: Integration with protocol address registry
- **Lego ID Storage**: Protocol identification for registry lookups
- **Minimal State**: Lightweight design focused on essential functions

The module serves as a foundation for DEX integrations, providing common administrative functions while allowing each DEX Lego to implement its own specific pool and routing logic.

## System Architecture Diagram

```
+-------------------------------------------------------------------------+
|                            DexLegoData                                  |
+-------------------------------------------------------------------------+
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                      Module Architecture                           | |
|  |                                                                   | |
|  |  State Variables:                                                  | |
|  |    • legoId: Protocol identifier in LegoBook                       | |
|  |    • isPaused: Emergency pause state                              | |
|  |                                                                   | |
|  |  Core Functions:                                                   | |
|  |    ├─> pause(): Toggle emergency pause                             | |
|  |    ├─> recoverFunds(): Recover single token                        | |
|  |    └─> recoverFundsMany(): Batch token recovery                    | |
|  |                                                                   | |
|  |  Integration:                                                       | |
|  |    • Uses Addys module for permissions                             | |
|  |    • Provides MiniAddys helper for addresses                       | |
|  |    • Switchboard-only administration                               | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                    Comparison with YieldLegoData                   | |
|  |                                                                   | |
|  |  DexLegoData (Minimal):          YieldLegoData (Complex):         | |
|  |    • No asset tracking            • Asset opportunity arrays       | |
|  |    • No vault mappings            • Vault-to-asset mappings        | |
|  |    • Simple state                 • Indexed storage patterns       | |
|  |    • Basic admin functions        • Full lifecycle management      | |
|  |                                                                   | |
|  |  Rationale: DEX pools are discovered through factory contracts     | |
|  |  and graph queries, not stored in the Lego itself                  | |
|  +-------------------------------------------------------------------+ |
+-------------------------------------------------------------------------+
```

## Module Dependencies

DexLegoData uses the `Addys` module for:
- Address registry access
- Permission validation (switchboard checks)
- Protocol address lookups

## Constants

- `MAX_RECOVER_ASSETS: uint256 = 20` - Maximum assets per recovery call

## State Variables

### Configuration
- `legoId: uint256` - Protocol identifier in LegoBook registry
- `isPaused: bool` - Emergency pause state

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
# Deploy paused for initial setup
dex_data = DexLegoData.deploy(True)

# Deploy active
dex_data = DexLegoData.deploy(False)
```

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
# Emergency pause
dex_data.pause(True, sender=switchboard)

# Resume after issue resolved
dex_data.pause(False, sender=switchboard)
```

#### Notes

- Requires state change (cannot set to current state)
- Used by DEX Legos to halt operations during security incidents

### `recoverFunds`

Recovers stuck tokens from the contract.

```vyper
@external
def recoverFunds(_recipient: address, _asset: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_recipient` | `address` | Address to receive recovered funds |
| `_asset` | `address` | Token address to recover |

#### Access

Only callable by switchboard addresses

#### Events Emitted

- `LegoFundsRecovered` - Contains asset (indexed), recipient (indexed), and balance

#### Example Usage
```python
# Recover stuck USDC
dex_data.recoverFunds(
    treasury.address,
    usdc.address,
    sender=switchboard
)
```

#### Notes

- Validates recipient and asset not empty
- Requires non-zero balance
- Transfers entire balance

### `recoverFundsMany`

Batch recovery of multiple tokens.

```vyper
@external
def recoverFundsMany(_recipient: address, _assets: DynArray[address, MAX_RECOVER_ASSETS]):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_recipient` | `address` | Address to receive all funds |
| `_assets` | `DynArray[address, MAX_RECOVER_ASSETS]` | Array of tokens to recover |

#### Access

Only callable by switchboard addresses

#### Events Emitted

- `LegoFundsRecovered` - Emitted for each recovered asset

#### Example Usage
```python
# Recover multiple tokens at once
tokens = [usdc.address, dai.address, weth.address]
dex_data.recoverFundsMany(
    treasury.address,
    tokens,
    sender=switchboard
)
```

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
| `MiniAddys` | Filled address struct with ledger, missionControl, legoBook, appraiser |

#### Usage

Used by DEX Legos to get protocol addresses when not provided by caller.

### `_recoverFunds`

Internal function for fund recovery logic.

```vyper
@internal
def _recoverFunds(_recipient: address, _asset: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_recipient` | `address` | Recipient address |
| `_asset` | `address` | Asset to recover |

#### Logic

1. Validate addresses not empty
2. Check balance > 0
3. Transfer full balance
4. Emit recovery event

## Key Differences from YieldLegoData

### State Management
- **DexLegoData**: Minimal state (pause + legoId only)
- **YieldLegoData**: Complex state with asset/vault tracking

### Storage Patterns
- **DexLegoData**: No indexed storage needed
- **YieldLegoData**: Sophisticated indexed arrays and mappings

### Use Case
- **DexLegoData**: DEX pools discovered via factories/events
- **YieldLegoData**: Vaults must be explicitly registered

### Functions
- **DexLegoData**: Only admin functions (pause/recover)
- **YieldLegoData**: Full CRUD for asset opportunities

## Security Considerations

### Access Control
- All administrative functions restricted to switchboard
- No user-facing functions
- Cannot be called by regular users or contracts

### State Safety
- Pause state prevents duplicate setting
- Fund recovery validates balances
- Address validation prevents empty transfers

### Emergency Response
- Quick pause mechanism for incidents
- Batch recovery for efficient cleanup
- No user funds at risk (admin only)

## Integration Patterns

### DEX Lego Implementation
```python
# In a DEX Lego contract
contract UniswapV2Lego:
    uses: DexLegoData
    
    def swap(...):
        # Check pause state
        assert not self.isPaused
        
        # Perform swap logic
        ...
```

### Emergency Response
```python
# Incident detected
dex_lego.pause(True, sender=switchboard)

# After resolution
dex_lego.pause(False, sender=switchboard)

# Recover any stuck funds
dex_lego.recoverFunds(treasury, token)
```

### Address Helper Usage
```python
# In DEX Lego function
def someFunction(_miniAddys: MiniAddys = empty):
    addrs = self._getMiniAddys(_miniAddys)
    # Use addrs.ledger, addrs.appraiser, etc.
```

## Common Patterns

### Pause Check Pattern
```python
# At start of user-facing functions
assert not self.isPaused  # dev: paused
```

### Batch Recovery Pattern
```python
# Recover all known tokens
stuck_tokens = [
    token1.address,
    token2.address,
    token3.address
]
dex_data.recoverFundsMany(
    recovery_address,
    stuck_tokens
)
```

### Address Resolution Pattern
```python
# Get protocol addresses when needed
mini_addys = self._getMiniAddys()
ledger = mini_addys.ledger
appraiser = mini_addys.appraiser
```

## Testing

For comprehensive test examples, see: [`tests/modules/`](../../../tests/modules/)