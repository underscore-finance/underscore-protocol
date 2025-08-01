# UndyHq Technical Documentation

[📄 View Source Code](../../../contracts/registries/UndyHq.vy)

## Overview

UndyHq is the master registry and governance hub for the Underscore Protocol. It coordinates all critical protocol components and controls minting permissions for the UNDY token. It maintains the authoritative record of protocol contracts while enforcing strict security through two-factor authentication and time-locked changes.

**Core Functions**:
- **Identity Registry**: Maps every protocol contract to a unique, sequentially assigned ID.
- **Two-Factor Minting**: Requires both UndyHq permission AND a department's self-declaration to mint UNDY tokens.
- **Safety Controls**: Features time-locked changes for all critical operations, a global minting circuit breaker, and robust fund recovery mechanisms.

Built with modular governance and registry components, UndyHq prevents unauthorized token creation through a double-verification security model. Its architecture ensures that decentralized components can coordinate safely through a trusted central registry, complete with comprehensive event logging.

## Architecture & Modules

UndyHq is built using a modular architecture that separates concerns and promotes code reusability:

### LocalGov Module
- **Location**: `contracts/modules/LocalGov.vy`
- **Purpose**: Provides core governance functionality with time-locked changes.
- **Documentation**: See [LocalGov Technical Documentation](../modules/LocalGov.md)
- **Key Features**:
  - Governance address management with time-locked transitions.
  - Configurable minimum and maximum timelock periods for security.
  - A two-phase commit pattern for all governance changes.
- **Exported Interface**: All governance functions are exposed via `gov.__interface__`.

### AddressRegistry Module
- **Location**: `contracts/modules/AddressRegistry.vy`
- **Purpose**: Manages the registry of all protocol addresses.
- **Documentation**: See [AddressRegistry Technical Documentation](../modules/AddressRegistry.md)
- **Key Features**:
  - Sequential registry ID assignment (starting from 1).
  - Time-locked address additions, updates, and disabling.
  - Descriptive labels for each registered address.
  - Address lookup by ID or reverse lookup (ID by address).
- **Exported Interface**: All registry functions are exposed via `registry.__interface__`.

### Module Initialization
```vyper
initializes: gov
initializes: registry[gov := gov]
```
This initialization pattern ensures the registry module has access to governance controls while maintaining a clean separation of concerns.

## System Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                           UndyHq Contract                          │
├────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐         ┌──────────────────────────────┐  │
│  │   LocalGov Module   │         │   AddressRegistry Module     │  │
│  │                     │         │                              │  │
│  │ • Governance mgmt   │         │ • Address registration       │  │
│  │ • Timelock control  │         │ • ID assignment (1,2,3...)   │  │
│  │ • Access control    │         │ • Update/disable functions   │  │
│  └─────────────────────┘         └──────────────────────────────┘  │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    HQ Configuration Layer                    │  │
│  │                                                              │  │
│  │  • Minting permissions (canMintUndy)                         │  │
│  │  • Blacklist permissions (canSetTokenBlacklist)              │  │
│  │  • Two-factor authentication with departments                │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Safety Mechanisms                         │  │
│  │                                                              │  │
│  │  • Global minting circuit breaker (mintEnabled)              │  │
│  │  • Fund recovery system (recoverFunds)                       │  │
│  │  • Timelock protection on all changes                        │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                                     │
                     ┌───────────────┴───────────────┐
                     ▼                               ▼
        ┌─────────────────────┐          ┌─────────────────────┐
        │     UNDY Token      │          │     Departments     │
        │ (Set by Governance) │          │                     │
        │                     │          │ ID 1+: Various      │
        └─────────────────────┘          │ • Treasury          │
                                         │ • Credit Engine     │
                                         │ • etc.              │
                                         └─────────────────────┘
```

## Data Structures

### HqConfig Struct
Stores the configuration for each registered address:
```vyper
struct HqConfig:
    description: String[64]        # Human-readable description
    canMintUndy: bool             # Permission to mint Undy tokens
    canSetTokenBlacklist: bool    # Permission to modify the token blacklist
```

### PendingHqConfig Struct
Tracks pending configuration changes during the timelock period:
```vyper
struct PendingHqConfig:
    newHqConfig: HqConfig         # The new configuration to apply
    initiatedBlock: uint256       # Block when the change was initiated
    confirmBlock: uint256         # Block when the change can be confirmed
```

## State Variables

### Public State Variables
- `undyToken: address` - The address of the Undy token contract.
- `mintEnabled: bool` - Global circuit breaker for all minting operations.
- `hqConfig: HashMap[uint256, HqConfig]` - Maps a registry ID to its configuration.
- `pendingHqConfig: HashMap[uint256, PendingHqConfig]` - Maps a registry ID to its pending config changes.

### Constants
- `MAX_RECOVER_ASSETS: uint256 = 20` - Maximum number of assets recoverable in a single transaction.

### Inherited State Variables (from modules)
From [LocalGov](../modules/LocalGov.md):
- `governance: address` - The current governance address.
- `govChangeTimeLock: uint256` - The timelock period for governance changes.

From [AddressRegistry](../modules/AddressRegistry.md):
- `registryChangeTimeLock: uint256` - The timelock period for registry changes.
- Various internal registry mappings for address management.

## Constructor

### `__init__`

Initializes the UndyHq contract with governance and timelock parameters. The UNDY token is not set at deployment and must be configured by governance post-deployment.

```vyper
@deploy
def __init__(
    _initialGov: address,
    _minGovTimeLock: uint256,
    _maxGovTimeLock: uint256,
    _minRegistryTimeLock: uint256,
    _maxRegistryTimeLock: uint256,
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_initialGov` | `address` | The initial governance address |
| `_minGovTimeLock` | `uint256` | The minimum time lock for governance changes, in blocks |
| `_maxGovTimeLock` | `uint256` | The maximum time lock for governance changes, in blocks |
| `_minRegistryTimeLock` | `uint256` | The minimum time lock for registry changes, in blocks |
| `_maxRegistryTimeLock` | `uint256` | The maximum time lock for registry changes, in blocks |

#### Returns

*The constructor does not return any values.*

#### Access

Called only once, during contract deployment.

#### Example Usage
```python
# Deploy UndyHq
undy_hq = boa.load(
    "contracts/registries/UndyHq.vy",
    deployer_address,
    100,   # Min gov timelock (blocks)
    1000,  # Max gov timelock (blocks)
    50,    # Min registry timelock (blocks)
    500    # Max registry timelock (blocks)
)
```

**Example Output**: The contract is deployed. `undyToken` is `ZERO_ADDRESS`, and `mintEnabled` is `False` by default.

## Registry Management Functions

### `startAddNewAddressToRegistry`

Initiates the time-locked process of adding a new address to the registry.

```vyper
@external
def startAddNewAddressToRegistry(_addr: address, _description: String[64]) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | The address to add to the registry. |
| `_description` | `String[64]` | A human-readable description (max 64 characters). |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | `True` if the addition was successfully initiated. |

#### Access

Only callable by the governance address.

#### Events Emitted

- `NewAddressPending` (from [AddressRegistry](../modules/AddressRegistry.md)) - Contains the address, description, and confirmation block.

### `confirmNewAddressToRegistry`

Confirms a pending address addition after the timelock period has passed, assigning it the next available registry ID.

```vyper
@external
def confirmNewAddressToRegistry(_addr: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | The address to confirm. |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | The newly assigned registry ID. |

#### Access

Only callable by the governance address.

#### Events Emitted

- `NewAddressConfirmed` (from [AddressRegistry](../modules/AddressRegistry.md)) - Contains the new registry ID, address, and description.

### `cancelNewAddressToRegistry`

Cancels a pending address addition before it is confirmed.

```vyper
@external
def cancelNewAddressToRegistry(_addr: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | The address whose pending addition should be cancelled. |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | `True` if successfully cancelled. |

#### Access

Only callable by the governance address.

#### Events Emitted

- `NewAddressCancelled` (from [AddressRegistry](../modules/AddressRegistry.md)) - Contains details of the cancelled addition.

---
*The functions `startAddressUpdateToRegistry`, `confirmAddressUpdateToRegistry`, `cancelAddressUpdateToRegistry`, `startAddressDisableInRegistry`, `confirmAddressDisableInRegistry`, and `cancelAddressDisableInRegistry` are also available and function identically to their counterparts in RipeHq, as they are inherited directly from the `AddressRegistry` module. They are all controlled by governance and are subject to the registry timelock.*

### Inherited View Functions

In addition to the governance-controlled functions, `UndyHq` exposes several public view functions from the `AddressRegistry` module for querying registry data:

- `getAddr(_regId: uint256) -> address`: Returns the address for a given registry ID.
- `getRegId(_addr: address) -> uint256`: Returns the registry ID for a given address.
- `getAddrDescription(_regId: uint256) -> String[64]`: Returns the description for a given registry ID.
- `isValidRegId(_regId: uint256) -> bool`: Checks if a registry ID is valid and active.
- `isValidAddr(_addr: address) -> bool`: Checks if an address is registered in the registry.
- `getAddrInfo(_regId: uint256) -> AddressInfo`: Returns complete address information including address, version, lastModified, and description.
- `getNumAddrs() -> uint256`: Returns the total number of registered addresses.
- `getLastAddr() -> address`: Returns the most recently registered address.
- `getLastRegId() -> uint256`: Returns the ID of the most recently registered address.
- `minRegistryTimeLock() -> uint256`: Returns the minimum allowed time-lock period for registry changes.
- `maxRegistryTimeLock() -> uint256`: Returns the maximum allowed time-lock period for registry changes.

These functions provide read-only access to registry data without requiring governance permissions.
---

## HQ Configuration Functions

### `hasPendingHqConfigChange`

Checks if a given registry ID has a pending configuration change.

```vyper
@view
@external
def hasPendingHqConfigChange(_regId: uint256) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_regId` | `uint256` | The registry ID to check. |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | `True` if a configuration change is pending. |

#### Access

Public view function.

### `initiateHqConfigChange`

Starts a time-locked process to update a department's permissions for minting and blacklist management.

```vyper
@external
def initiateHqConfigChange(
    _regId: uint256,
    _canMintUndy: bool,
    _canSetTokenBlacklist: bool,
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_regId` | `uint256` | The registry ID to configure. |
| `_canMintUndy` | `bool` | Whether this address can mint Undy tokens. |
| `_canSetTokenBlacklist` | `bool` | Whether this address can modify the token blacklist. |

#### Returns

*This function does not return any values.*

#### Access

Only callable by the governance address.

#### Events Emitted

- `HqConfigChangeInitiated` - Contains the registry ID, description, new permissions, and confirmation block.

### `confirmHqConfigChange`

Confirms a pending configuration change after the timelock. It performs a final validation to ensure the target contract supports the requested minting permission.

```vyper
@external
def confirmHqConfigChange(_regId: uint256) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_regId` | `uint256` | The registry ID whose configuration change to confirm. |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | `True` if confirmed, `False` if the configuration is invalid (deleting the pending change). |

#### Access

Only callable by the governance address.

#### Events Emitted

- `HqConfigChangeConfirmed` - Contains the registry ID, description, and the applied permissions.

### `cancelHqConfigChange`

Cancels a pending configuration change.

```vyper
@external
def cancelHqConfigChange(_regId: uint256) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_regId` | `uint256` | The registry ID whose configuration change to cancel. |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | `True` if successfully cancelled. |

#### Access

Only callable by the governance address.

#### Events Emitted

- `HqConfigChangeCancelled` - Contains details of the cancelled change, including `regId`, `description`, `canMintUndy`, `canSetTokenBlacklist`, `initiatedBlock`, and `confirmBlock`.

### `isValidHqConfig`

Validates whether a proposed configuration is valid for a given registry ID. Checks that the target contract supports the requested minting capability.

```vyper
@view
@external
def isValidHqConfig(_regId: uint256, _canMintUndy: bool) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_regId` | `uint256` | The registry ID to validate. |
| `_canMintUndy` | `bool` | The proposed Undy minting permission. |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | `True` if the configuration is valid. |

#### Access

Public view function.

## Token Management Functions

### `setUndyToken`

Sets the official Undy token address for the protocol. This can only be done once.

```vyper
@external
def setUndyToken(_token: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_token` | `address` | The address of the UNDY ERC20 token contract. |

#### Returns

*This function does not return any values.*

#### Access

Only callable by the governance address.

#### Events Emitted

- `UndyTokenSet` - Contains the new token address.

### `canMintUndy`

Checks if an address has permission to mint Undy tokens. This requires three conditions to be met: global minting is enabled, the address is registered with `canMintUndy` permission, and the address's contract returns `True` from its own `canMintUndy()` view function.

```vyper
@view
@external
def canMintUndy(_addr: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | The address to check. |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | `True` if the address can mint Undy tokens. |

#### Access

Public view function.

### `canSetTokenBlacklist`

Checks if an address has permission to modify the token blacklist.

```vyper
@view
@external
def canSetTokenBlacklist(_addr: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | The address to check. |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | `True` if the address has permission to set the token blacklist. |

#### Access

Public view function.

## Circuit Breaker Functions

### `setMintingEnabled`

Enables or disables all minting operations across the protocol. This acts as a global emergency circuit breaker.

```vyper
@external
def setMintingEnabled(_shouldEnable: bool):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_shouldEnable` | `bool` | `True` to enable minting, `False` to disable. |

#### Returns

*This function does not return any values.*

#### Access

Only callable by the governance address.

#### Events Emitted

- `MintingEnabled` - Contains the new enabled state (`isEnabled`).

## Recovery Functions

### `recoverFunds`

Recovers the full balance of a single ERC20 token that was accidentally sent to the UndyHq contract.

```vyper
@external
def recoverFunds(_recipient: address, _asset: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_recipient` | `address` | The address to receive the recovered funds. |
| `_asset` | `address` | The token contract address to recover. |

#### Returns

*This function does not return any values.*

#### Access

Only callable by the governance address.

#### Events Emitted

- `UndyHqFundsRecovered` - Contains the asset address, recipient address, and the balance recovered.

### `recoverFundsMany`

Recovers multiple different ERC20 tokens in a single transaction.

```vyper
@external
def recoverFundsMany(_recipient: address, _assets: DynArray[address, MAX_RECOVER_ASSETS]):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_recipient` | `address` | The address to receive all recovered funds. |
| `_assets` | `DynArray[address, MAX_RECOVER_ASSETS]` | A list of token addresses to recover (max 20). |

#### Returns

*This function does not return any values.*

#### Access

Only callable by the governance address.

#### Events Emitted

- `UndyHqFundsRecovered` - One event is emitted for each successfully recovered asset.

## Testing

For comprehensive test examples, see: [`tests/registries/test_undy_hq.py`](../../../tests/registries/test_undy_hq.py)
