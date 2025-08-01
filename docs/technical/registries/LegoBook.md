# LegoBook Technical Documentation

[📄 View Source Code](../../../contracts/registries/LegoBook.vy)

## Overview

LegoBook is the master registry for all Lego partner contracts (DeFi protocol integrations) in the Underscore Protocol. It maintains the authoritative directory of yield protocols, DEX integrations, and other DeFi building blocks while providing unified access control and configuration management. As a Department contract, it combines governance controls with the registry functionality needed to coordinate protocol integrations safely.

**Core Functions**:
- **Lego Partner Registry**: Maintains a registry of all DeFi protocol integration contracts (Yield Legos, DEX Legos).
- **LegoTools Coordination**: Manages the official [LegoTools](../legos/LegoTools.md) contract address for protocol-wide routing.
- **Integration Validation**: Provides address validation functions for other protocol components.

Built with the same modular architecture as other protocol registries, LegoBook ensures that DeFi integrations are managed through controlled, time-locked processes. It serves as the single source of truth for all protocol integrations, enabling dynamic discovery while maintaining security through governance oversight.

## Architecture & Modules

LegoBook uses the standard Department architecture with specialized functionality for DeFi integrations:

### LocalGov Module
- **Location**: `contracts/modules/LocalGov.vy`
- **Purpose**: Provides governance functionality linked to UndyHq.
- **Documentation**: See [LocalGov Technical Documentation](../modules/LocalGov.md)
- **Key Features**:
  - Links to UndyHq as the ultimate governance authority.
  - No local governance timelock (0 blocks) as changes are managed through registry timelock.
  - Enables governance delegation from UndyHq.
- **Exported Interface**: All governance functions are exposed via `gov.__interface__`.

### AddressRegistry Module
- **Location**: `contracts/modules/AddressRegistry.vy`
- **Purpose**: Manages the registry of Lego partner contracts.
- **Documentation**: See [AddressRegistry Technical Documentation](../modules/AddressRegistry.md)
- **Key Features**:
  - Sequential registry ID assignment for Lego contracts.
  - Time-locked additions, updates, and disabling of addresses.
  - Descriptive labels for each registered integration.
  - Validation functions for permission checks.
- **Exported Interface**: All registry functions are exposed via `registry.__interface__`.

### Addys Module
- **Location**: `contracts/modules/Addys.vy`
- **Purpose**: Provides protocol-wide address lookups.
- **Documentation**: See [Addys Technical Documentation](../modules/Addys.md)
- **Key Features**:
  - Connection to UndyHq for protocol addresses.
  - Cached address lookups including Switchboard validation.
  - Standardized address validation across protocol.
- **Exported Interface**: All address functions are exposed via `addys.__interface__`.

### DeptBasics Module
- **Location**: `contracts/modules/DeptBasics.vy`
- **Purpose**: Implements Department interface requirements.
- **Documentation**: See [DeptBasics Technical Documentation](../modules/DeptBasics.md)
- **Key Features**:
  - Pause functionality for emergency control.
  - Fund recovery mechanisms.
  - No minting capability (configured as `False`).
- **Exported Interface**: All department functions are exposed via `deptBasics.__interface__`.

### Module Initialization
```vyper
initializes: gov
initializes: registry[gov := gov]
initializes: addys
initializes: deptBasics[addys := addys]
```
This initialization pattern ensures proper module dependencies and access control throughout the Lego integration system.

## System Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                         LegoBook Contract                          │
├────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐         ┌──────────────────────────────┐  │
│  │   LocalGov Module   │         │   AddressRegistry Module     │  │
│  │                     │         │                              │  │
│  │ • UndyHq governance │         │ • Lego partner registration  │  │
│  │ • Permission checks │         │ • Time-locked changes       │  │
│  │ • No local timelock │         │ • Integration validation     │  │
│  └─────────────────────┘         └──────────────────────────────┘  │
│                                                                    │
│  ┌─────────────────────┐         ┌──────────────────────────────┐  │
│  │    Addys Module     │         │    DeptBasics Module         │  │
│  │                     │         │                              │  │
│  │ • Protocol addrs    │         │ • Pause functionality        │  │
│  │ • Switchboard check │         │ • Fund recovery              │  │
│  │ • Cache management  │         │ • No minting (False)         │  │
│  └─────────────────────┘         └──────────────────────────────┘  │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Core Lego Management                       │  │
│  │                                                              │  │
│  │  • Registry Management (add/update/disable Legos)            │  │
│  │  • LegoTools Address Management (setLegoTools)               │  │
│  │  • Validation Functions (isLegoAddr, isValidLegoTools)       │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                                     │
                     ┌───────────────┴───────────────┐
                     ▼                               ▼
        ┌─────────────────────┐          ┌─────────────────────┐
        │   Yield Legos       │          │    DEX Legos        │
        │                     │          │                     │
        │ • AaveV3Lego        │          │ • UniswapV2Lego     │
        │ • CompoundV3Lego    │          │ • UniswapV3Lego     │
        │ • EulerLego         │          │ • AerodromeLego     │
        │ • FluidLego         │          │ • CurveLego         │
        │ • MoonwellLego      │          │ • etc...            │
        │ • MorphoLego        │          │                     │
        └─────────────────────┘          └─────────────────────┘
                     │                               │
                     ▼                               ▼
        ┌─────────────────────┐          ┌─────────────────────┐
        │  Yield Protocols    │          │   DEX Protocols     │
        │                     │          │                     │
        │ • Vault management  │          │ • Pool discovery    │
        │ • Interest earning  │          │ • Token swapping    │
        │ • Asset wrapping    │          │ • Liquidity mgmt    │
        └─────────────────────┘          └─────────────────────┘
```

## State Variables

### LegoBook-Specific State
- `legoTools: address` - The official LegoTools contract address for routing

### Inherited State Variables (from modules)
From [LocalGov](../modules/LocalGov.md):
- `governance: address` - Set to UndyHq address
- `govChangeTimeLock: uint256` - Set to 0 (no local timelock)

From [AddressRegistry](../modules/AddressRegistry.md):
- `registryChangeTimeLock: uint256` - The timelock period for registry changes
- Various internal registry mappings for Lego address management

From [Addys](../modules/Addys.md):
- `hq: address` - Reference to UndyHq contract
- Various cached protocol addresses

From [DeptBasics](../modules/DeptBasics.md):
- `isPaused: bool` - Emergency pause state
- `canMintUndy: bool` - Set to False (no minting capability)

## Constructor

### `__init__`

Initializes the LegoBook contract with UndyHq reference and registry timelock parameters.

```vyper
@deploy
def __init__(
    _undyHq: address,
    _minRegistryTimeLock: uint256,
    _maxRegistryTimeLock: uint256,
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | The UndyHq contract address for governance |
| `_minRegistryTimeLock` | `uint256` | Minimum timelock for registry changes (blocks) |
| `_maxRegistryTimeLock` | `uint256` | Maximum timelock for registry changes (blocks) |

#### Returns

*The constructor does not return any values.*

#### Access

Called only once during contract deployment.

#### Example Usage
```python
# Deploy LegoBook
lego_book = boa.load(
    "contracts/registries/LegoBook.vy",
    undy_hq.address,
    50,    # Min registry timelock (blocks)
    500    # Max registry timelock (blocks)
)
```

#### Notes

- Initializes LocalGov with UndyHq as governance and 0 timelock
- Sets up AddressRegistry with provided timelock bounds for Lego management
- Configures DeptBasics with no minting capability
- Links Addys module to UndyHq for protocol addresses
- `legoTools` starts as `empty(address)` and must be set post-deployment

## Lego Validation Functions

### `isLegoAddr`

Checks if an address is registered as a valid Lego partner contract.

```vyper
@view
@external
def isLegoAddr(_addr: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | The address to validate |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | `True` if the address is a registered Lego |

#### Access

Public view function.

#### Example Usage
```python
# Check if address is registered Lego
is_lego = lego_book.isLegoAddr(aave_v3_lego.address)
# Returns: True

# Check unknown address
is_lego = lego_book.isLegoAddr(random_contract.address)
# Returns: False
```

#### Notes

This is the primary function used by LegoTools and other contracts to validate Lego partner addresses.

## Registry Management Functions

### `startAddNewAddressToRegistry`

Initiates the time-locked process of adding a new Lego partner contract to the registry.

```vyper
@external
def startAddNewAddressToRegistry(_addr: address, _description: String[64]) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | The Lego contract address to add |
| `_description` | `String[64]` | Human-readable description (max 64 characters) |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | `True` if the addition was successfully initiated |

#### Access

Only callable by addresses that can perform actions (governance or when not paused).

#### Events Emitted

- `NewAddressPending` (from [AddressRegistry](../modules/AddressRegistry.md)) - Contains the address, description, and confirmation block

#### Example Usage
```python
# Start adding a new Lego integration
lego_book.startAddNewAddressToRegistry(
    new_lego_contract.address,
    "Custom Yield Protocol Integration",
    sender=governance
)
```

### `confirmNewAddressToRegistry`

Confirms a pending Lego addition after the timelock period has passed.

```vyper
@external
def confirmNewAddressToRegistry(_addr: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | The address to confirm |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | The newly assigned registry ID |

#### Access

Only callable by addresses that can perform actions.

#### Events Emitted

- `NewAddressConfirmed` (from [AddressRegistry](../modules/AddressRegistry.md)) - Contains the new registry ID, address, and description

#### Example Usage
```python
# Confirm addition after timelock
reg_id = lego_book.confirmNewAddressToRegistry(
    new_lego_contract.address,
    sender=governance
)
print(f"New Lego registered with ID: {reg_id}")
```

### `cancelNewAddressToRegistry`

Cancels a pending Lego addition before confirmation.

```vyper
@external
def cancelNewAddressToRegistry(_addr: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | The address whose pending addition to cancel |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | `True` if successfully cancelled |

#### Access

Only callable by addresses that can perform actions.

#### Events Emitted

- `NewAddressCancelled` (from [AddressRegistry](../modules/AddressRegistry.md)) - Contains details of the cancelled addition

### Address Update Functions

The following functions manage updates to existing Lego registry entries:

- `startAddressUpdateToRegistry(_regId: uint256, _newAddr: address) -> bool`
- `confirmAddressUpdateToRegistry(_regId: uint256) -> bool` 
- `cancelAddressUpdateToRegistry(_regId: uint256) -> bool`

### Address Disable Functions

The following functions manage disabling of Lego registry entries:

- `startAddressDisableInRegistry(_regId: uint256) -> bool`
- `confirmAddressDisableInRegistry(_regId: uint256) -> bool`
- `cancelAddressDisableInRegistry(_regId: uint256) -> bool`

All registry management functions follow the same pattern:
1. Require permission via `_canPerformAction`
2. Initiate time-locked change
3. Wait for timelock period
4. Confirm or cancel the change

## LegoTools Management

### `setLegoTools`

Sets the official LegoTools contract address for the protocol.

```vyper
@external
def setLegoTools(_addr: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | The LegoTools contract address to set |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | `True` if successfully set, `False` if validation fails |

#### Access

Only callable by Switchboard addresses (via `addys._isSwitchboardAddr`).

#### Events Emitted

- `LegoToolsSet` - Contains the new LegoTools address: `log LegoToolsSet(addr=_addr)`

#### Example Usage
```python
# Set new LegoTools contract
success = lego_book.setLegoTools(
    new_lego_tools.address,
    sender=switchboard_alpha
)
```

#### Notes

- Validates the address using `_isValidLegoTools`
- Returns `False` without reverting if validation fails
- Can only be called by registered switchboard contracts

### `isValidLegoTools`

Validates whether an address can be set as the LegoTools contract.

```vyper
@view
@external
def isValidLegoTools(_addr: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | The address to validate |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | `True` if the address is valid for LegoTools |

#### Access

Public view function.

#### Example Usage
```python
# Check if address can be set as LegoTools
can_set = lego_book.isValidLegoTools(potential_lego_tools.address)
```

### `_isValidLegoTools`

Internal validation logic for LegoTools addresses.

```vyper
@view
@internal
def _isValidLegoTools(_addr: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | The address to validate |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | `True` if valid |

#### Validation Logic

Returns `True` if:
1. Address is not empty (`address(0)`)
2. Address is a contract (has code)
3. Address is different from current `legoTools`

## Internal Utilities

### `_canPerformAction`

Determines if a caller has permission to perform registry management actions.

```vyper
@view
@internal
def _canPerformAction(_caller: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_caller` | `address` | The address attempting the action |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | `True` if caller can govern and contract is not paused |

#### Logic

Returns `True` if:
1. Caller has governance permissions (from LocalGov)
2. AND contract is not paused (from DeptBasics)

## Inherited View Functions

### From AddressRegistry Module

LegoBook exposes all public view functions from the AddressRegistry module:

- `getAddr(_regId: uint256) -> address`: Returns the Lego address for a given registry ID
- `getRegId(_addr: address) -> uint256`: Returns the registry ID for a given Lego address
- `getAddrDescription(_regId: uint256) -> String[64]`: Returns the description for a registry ID
- `isValidRegId(_regId: uint256) -> bool`: Checks if a registry ID is valid and active
- `isValidAddr(_addr: address) -> bool`: Checks if a Lego address is registered
- `getAddrInfo(_regId: uint256) -> AddressInfo`: Returns complete Lego information
- `getNumAddrs() -> uint256`: Returns the total number of registered Legos
- `getLastAddr() -> address`: Returns the most recently registered Lego
- `getLastRegId() -> uint256`: Returns the ID of the most recently registered Lego
- `minRegistryTimeLock() -> uint256`: Returns the minimum timelock period
- `maxRegistryTimeLock() -> uint256`: Returns the maximum timelock period

### From DeptBasics Module

- `isPaused() -> bool`: Returns the current pause state
- `canMintUndy() -> bool`: Always returns `False` (no minting capability)

### From Addys Module

Various protocol address lookup functions for accessing registered contracts.

## Lego Partner Interface

All registered Lego contracts must implement the `LegoPartner` interface, which includes:

### Core Operations
- `swapTokens()` - Token swapping functionality
- `depositForYield()` - Yield farming deposits
- `withdrawFromYield()` - Yield farming withdrawals
- `addLiquidity()` / `removeLiquidity()` - Liquidity management
- `borrow()` / `repayDebt()` - Lending protocol operations

### Metadata Functions
- `isYieldLego()` - Returns `True` for yield protocol integrations
- `isDexLego()` - Returns `True` for DEX integrations
- `hasCapability()` - Returns supported action types
- `getRegistries()` - Returns required registry addresses

### Department Interface
- `isPaused()` - Pause state checking
- `pause()` - Emergency pause functionality
- `recoverFunds()` - Fund recovery mechanisms

## Security Considerations

### Access Control
- Registry changes require governance permissions
- LegoTools updates require Switchboard permissions  
- All actions blocked when contract is paused

### Time-Lock Protection
- All registry changes subject to configurable timelock
- Prevents immediate malicious Lego additions
- Allows time for community review

### Validation Mechanisms
- LegoTools address validation prevents invalid contracts
- Lego contract validation ensures proper interface implementation
- No direct user access to sensitive functions

## Integration Patterns

### Adding a New Lego Partner
```python
# Governance initiates addition
lego_book.startAddNewAddressToRegistry(
    new_lego_contract.address,
    "Morpho Blue Yield Integration"
)

# Wait for timelock...

# Confirm addition
reg_id = lego_book.confirmNewAddressToRegistry(
    new_lego_contract.address
)

# Register in LegoTools for discovery
lego_tools.updateLegoRegistry()
```

### Updating LegoTools
```python
# Deploy new LegoTools
new_lego_tools = deploy_lego_tools()

# Update via Switchboard
lego_book.setLegoTools(
    new_lego_tools.address,
    sender=switchboard_alpha
)
```

### Lego Discovery
```python
# Check if address is valid Lego
if lego_book.isLegoAddr(potential_lego):
    # Use in routing
    routes = lego_tools.getSwapRoutes(...)
    
# Get all registered Legos
num_legos = lego_book.getNumAddrs()
for i in range(1, num_legos + 1):
    lego_addr = lego_book.getAddr(i)
    description = lego_book.getAddrDescription(i)
```

### Protocol Coordination
```python
# LegoTools queries LegoBook for valid partners
def get_available_legos():
    legos = []
    for reg_id in range(1, lego_book.getNumAddrs() + 1):
        if lego_book.isValidRegId(reg_id):
            lego_addr = lego_book.getAddr(reg_id)
            if lego_book.isLegoAddr(lego_addr):
                legos.append(lego_addr)
    return legos
```

## Common Patterns

### Registry Lifecycle for Legos
1. Develop and deploy new Lego contract implementing `LegoPartner` interface
2. Start addition with appropriate description
3. Wait for `registryChangeTimeLock` blocks
4. Confirm addition to receive registry ID
5. Lego becomes discoverable by LegoTools and other components

### Emergency Response
```python
# Pause all Lego operations
lego_book.pause(True, sender=governance)

# Disable specific problematic Lego
lego_book.startAddressDisableInRegistry(problematic_lego_id)
# ... wait for timelock ...
lego_book.confirmAddressDisableInRegistry(problematic_lego_id)

# Resume after issue resolved
lego_book.pause(False, sender=governance)
```

### Protocol Upgrades
```python
# Deploy new version of existing Lego
new_lego_v2 = deploy_upgraded_lego()

# Update registry entry
lego_book.startAddressUpdateToRegistry(
    existing_lego_id,
    new_lego_v2.address
)
# ... timelock and confirm ...
```

## Testing

For comprehensive test examples, see integration tests in: [`tests/legos/`](../../../tests/legos/) and [`tests/registries/`](../../../tests/registries/)