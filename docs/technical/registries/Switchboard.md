# Switchboard Technical Documentation

[📄 View Source Code](../../../contracts/registries/Switchboard.vy)

## Overview

Switchboard is the configuration registry and access control hub for the Underscore Protocol. It maintains a registry of authorized configuration-related contracts (SwitchboardAlpha, SwitchboardBravo, etc.) while providing unified blacklist management across protocol tokens. As a Department contract, it integrates modular governance and registry components to create a secure, time-locked configuration system.

**Core Functions**:
- **Configuration Registry**: Maintains a list of authorized switchboard contracts with time-locked changes.
- **Blacklist Coordination**: Provides a centralized interface for token blacklist management across multiple tokens.
- **Access Control Gateway**: Validates that only registered switchboard contracts can perform sensitive operations.

Built as a Department implementation, Switchboard enforces strict security through time-locked registry changes and permission validation. It acts as the protocol's configuration authority, ensuring that operational changes are made through authorized channels with appropriate governance oversight.

## Architecture & Modules

Switchboard leverages a modular architecture that combines governance, registry, and department functionality:

### LocalGov Module
- **Location**: `contracts/modules/LocalGov.vy`
- **Purpose**: Provides governance functionality specific to this registry.
- **Documentation**: See [LocalGov Technical Documentation](../modules/LocalGov.md)
- **Key Features**:
  - Links to UndyHq as the ultimate governance authority.
  - No local governance timelock (0 blocks) as changes are managed through registry timelock.
  - Enables governance delegation from UndyHq.
- **Exported Interface**: All governance functions are exposed via `gov.__interface__`.

### AddressRegistry Module
- **Location**: `contracts/modules/AddressRegistry.vy`
- **Purpose**: Manages the registry of authorized switchboard contracts.
- **Documentation**: See [AddressRegistry Technical Documentation](../modules/AddressRegistry.md)
- **Key Features**:
  - Sequential registry ID assignment for switchboard contracts.
  - Time-locked additions, updates, and disabling of addresses.
  - Descriptive labels for each registered switchboard.
  - Validation functions for permission checks.
- **Exported Interface**: All registry functions are exposed via `registry.__interface__`.

### Addys Module
- **Location**: `contracts/modules/Addys.vy`
- **Purpose**: Provides protocol-wide address lookups.
- **Documentation**: See [Addys Technical Documentation](../modules/Addys.md)
- **Key Features**:
  - Connection to UndyHq for protocol addresses.
  - Cached address lookups for gas efficiency.
  - Standardized address validation.
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
This initialization pattern ensures proper module dependencies and access control throughout the contract hierarchy.

## System Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                        Switchboard Contract                        │
├────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐         ┌──────────────────────────────┐  │
│  │   LocalGov Module   │         │   AddressRegistry Module     │  │
│  │                     │         │                              │  │
│  │ • UndyHq governance │         │ • Switchboard registration   │  │
│  │ • Permission checks │         │ • Time-locked changes       │  │
│  │ • No local timelock │         │ • Address validation         │  │
│  └─────────────────────┘         └──────────────────────────────┘  │
│                                                                    │
│  ┌─────────────────────┐         ┌──────────────────────────────┐  │
│  │    Addys Module     │         │    DeptBasics Module         │  │
│  │                     │         │                              │  │
│  │ • Protocol addrs    │         │ • Pause functionality        │  │
│  │ • Address lookups   │         │ • Fund recovery              │  │
│  │ • Cache management  │         │ • No minting (False)         │  │
│  └─────────────────────┘         └──────────────────────────────┘  │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Core Functionality                         │  │
│  │                                                              │  │
│  │  • Registry Management (add/update/disable switchboards)     │  │
│  │  • Blacklist Passthrough (setBlacklist function)             │  │
│  │  • Permission Validation (isSwitchboardAddr)                 │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                                     │
                     ┌───────────────┴───────────────┐
                     ▼                               ▼
        ┌─────────────────────┐          ┌─────────────────────┐
        │ SwitchboardAlpha    │          │ SwitchboardBravo    │
        │ (Config Contract)   │          │ (Config Contract)   │
        │                     │          │                     │
        │ • Specific configs  │          │ • Specific configs  │
        │ • Token management  │          │ • Protocol params   │
        └─────────────────────┘          └─────────────────────┘
                     │                               │
                     ▼                               ▼
        ┌─────────────────────┐          ┌─────────────────────┐
        │   Token Contracts   │          │ Protocol Contracts  │
        │                     │          │                     │
        │ • Receive blacklist │          │ • Read configs      │
        │   updates           │          │ • Apply params      │
        └─────────────────────┘          └─────────────────────┘
```

## Constants

### Inherited Constants (from modules)
From [AddressRegistry](../modules/AddressRegistry.md):
- Various internal constants for registry management

From [DeptBasics](../modules/DeptBasics.md):
- `MAX_RECOVER_ASSETS: uint256 = 20` - Maximum assets recoverable in a single transaction

## State Variables

### Inherited State Variables (from modules)
From [LocalGov](../modules/LocalGov.md):
- `governance: address` - Set to UndyHq address
- `govChangeTimeLock: uint256` - Set to 0 (no local timelock)

From [AddressRegistry](../modules/AddressRegistry.md):
- `registryChangeTimeLock: uint256` - The timelock period for registry changes
- Various internal registry mappings for address management

From [Addys](../modules/Addys.md):
- `hq: address` - Reference to UndyHq contract
- Various cached protocol addresses

From [DeptBasics](../modules/DeptBasics.md):
- `isPaused: bool` - Emergency pause state
- `canMintUndy: bool` - Set to False (no minting capability)

## Constructor

### `__init__`

Initializes the Switchboard contract with UndyHq reference and registry timelock parameters.

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
# Deploy Switchboard
switchboard = boa.load(
    "contracts/registries/Switchboard.vy",
    undy_hq.address,
    50,    # Min registry timelock (blocks)
    500    # Max registry timelock (blocks)
)
```

#### Notes

- Initializes LocalGov with UndyHq as governance and 0 timelock
- Sets up AddressRegistry with provided timelock bounds
- Configures DeptBasics with no minting capability
- Links Addys module to UndyHq for protocol addresses

## Permission Validation Functions

### `isSwitchboardAddr`

Checks if an address is registered as a valid switchboard contract.

```vyper
@view
@external
def isSwitchboardAddr(_addr: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | The address to validate |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | `True` if the address is a registered switchboard |

#### Access

Public view function.

#### Example Usage
```python
# Check if address is authorized switchboard
is_valid = switchboard.isSwitchboardAddr(switchboard_alpha.address)
# Returns: True
```

#### Notes

This is the primary function used by other contracts to validate switchboard permissions.

## Registry Management Functions

### `startAddNewAddressToRegistry`

Initiates the time-locked process of adding a new switchboard contract to the registry.

```vyper
@external
def startAddNewAddressToRegistry(_addr: address, _description: String[64]) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | The switchboard contract address to add |
| `_description` | `String[64]` | Human-readable description (max 64 characters) |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | `True` if the addition was successfully initiated |

#### Access

Only callable by addresses that can perform actions (governance or authorized switchboards).

#### Events Emitted

- `NewAddressPending` (from [AddressRegistry](../modules/AddressRegistry.md)) - Contains the address, description, and confirmation block

#### Example Usage
```python
# Start adding a new switchboard
switchboard.startAddNewAddressToRegistry(
    new_switchboard.address,
    "SwitchboardCharlie - Extended Config",
    sender=governance
)
```

### `confirmNewAddressToRegistry`

Confirms a pending address addition after the timelock period has passed.

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

### `cancelNewAddressToRegistry`

Cancels a pending address addition before confirmation.

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

The following functions manage updates to existing registry entries:

- `startAddressUpdateToRegistry(_regId: uint256, _newAddr: address) -> bool`
- `confirmAddressUpdateToRegistry(_regId: uint256) -> bool`
- `cancelAddressUpdateToRegistry(_regId: uint256) -> bool`

### Address Disable Functions

The following functions manage disabling of registry entries:

- `startAddressDisableInRegistry(_regId: uint256) -> bool`
- `confirmAddressDisableInRegistry(_regId: uint256) -> bool`
- `cancelAddressDisableInRegistry(_regId: uint256) -> bool`

All registry management functions follow the same pattern:
1. Require permission via `_canPerformAction`
2. Initiate time-locked change
3. Wait for timelock period
4. Confirm or cancel the change

## Blacklist Management

### `setBlacklist`

Passes blacklist updates from authorized switchboard contracts to token contracts.

```vyper
@external
def setBlacklist(_tokenAddr: address, _addr: address, _shouldBlacklist: bool) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_tokenAddr` | `address` | The token contract to update |
| `_addr` | `address` | The address to blacklist/unblacklist |
| `_shouldBlacklist` | `bool` | `True` to blacklist, `False` to remove |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Always returns `True` on success |

#### Access

Only callable by registered switchboard addresses.

#### Example Usage
```python
# Switchboard contract blacklists an address
switchboard.setBlacklist(
    undy_token.address,
    malicious_addr,
    True,
    sender=switchboard_alpha
)
```

#### Notes

- Acts as a passthrough to token contracts
- Validates caller is a registered switchboard
- Token contract must implement the `setBlacklist` interface

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

The Switchboard exposes all public view functions from the AddressRegistry module:

- `getAddr(_regId: uint256) -> address`: Returns the address for a given registry ID
- `getRegId(_addr: address) -> uint256`: Returns the registry ID for a given address
- `getAddrDescription(_regId: uint256) -> String[64]`: Returns the description for a registry ID
- `isValidRegId(_regId: uint256) -> bool`: Checks if a registry ID is valid and active
- `isValidAddr(_addr: address) -> bool`: Checks if an address is registered
- `getAddrInfo(_regId: uint256) -> AddressInfo`: Returns complete address information
- `getNumAddrs() -> uint256`: Returns the total number of registered addresses
- `getLastAddr() -> address`: Returns the most recently registered address
- `getLastRegId() -> uint256`: Returns the ID of the most recently registered address
- `minRegistryTimeLock() -> uint256`: Returns the minimum timelock period
- `maxRegistryTimeLock() -> uint256`: Returns the maximum timelock period

### From DeptBasics Module

- `isPaused() -> bool`: Returns the current pause state
- `canMintUndy() -> bool`: Always returns `False` (no minting capability)

### From Addys Module

Various protocol address lookup functions for accessing registered contracts.

## Security Considerations

### Access Control
- Registry changes require governance permissions
- Blacklist updates require registered switchboard status
- All actions blocked when contract is paused

### Time-Lock Protection
- All registry changes subject to configurable timelock
- Prevents immediate malicious configuration changes
- Allows time for review and intervention

### Permission Validation
- Double validation: governance AND not paused
- Strict validation of switchboard addresses for blacklist operations
- No direct user access to sensitive functions

## Integration Patterns

### Adding a New Switchboard
```python
# Governance initiates addition
switchboard.startAddNewAddressToRegistry(
    new_config_contract,
    "SwitchboardDelta - New Features"
)

# Wait for timelock...

# Confirm addition
reg_id = switchboard.confirmNewAddressToRegistry(
    new_config_contract
)
```

### Blacklist Management Flow
```python
# From authorized switchboard contract
switchboard.setBlacklist(
    token_address,
    address_to_blacklist,
    True  # blacklist
)
```

### Permission Checking
```python
# Other contracts check if address is switchboard
if switchboard.isSwitchboardAddr(caller):
    # Allow configuration changes
    ...
```

## Common Patterns

### Registry Lifecycle
1. Start addition/update/disable with appropriate function
2. Wait for `registryChangeTimeLock` blocks
3. Confirm or cancel the pending change
4. Check success via view functions

### Emergency Response
```python
# Pause all operations
switchboard.pause(True, sender=governance)

# Recover stuck funds if needed
switchboard.recoverFunds(recipient, token_address)

# Resume after issue resolved
switchboard.pause(False, sender=governance)
```

## Testing

For comprehensive test examples, see: [`tests/config/test_switchboard_alpha.py`](../../../tests/config/test_switchboard_alpha.py)