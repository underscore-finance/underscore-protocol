# DeptBasics Technical Documentation

[📄 View Source Code](../../../contracts/modules/DeptBasics.vy)

## Overview

DeptBasics is a foundational module providing essential department-level functionality for Underscore Protocol contracts. It standardizes common operations across all departments including pause mechanisms, token recovery, and minting
capability declarations, ensuring consistency while allowing deployment-time customization.

**Core Capabilities**:
- **Pause Functionality**: Circuit breaker for emergencies, allowing Switchboard-authorized contracts to halt operations
- **Token Recovery**: Secure retrieval of accidentally sent tokens with batch support for efficiency
- **Minting Declarations**: Immutable capability flag for UNDY token minting, supporting UndyHq's permission system

The module implements the Department interface standard, integrates with Addys for validation, and promotes operational consistency across all protocol departments.

## System Architecture Diagram

```
+---------------------------------------------------------------+
|                      DeptBasics Module                        |
+---------------------------------------------------------------+
|                                                               |
|  +----------------------------------------------------------+ |
|  |                   Core Capabilities                      | |
|  |                                                          | |
|  |  1. Pause Management                                     | |
|  |     * isPaused state variable                            | |
|  |     * Toggle via Switchboard-authorized contracts        | |
|  |     * Emits DepartmentPauseModified events               | |
|  |                                                          | |
|  |  2. Token Recovery                                       | |
|  |     * Recover individual tokens                          | |
|  |     * Batch recovery (up to 20 tokens)                   | |
|  |     * Only via Switchboard authorization                 | |
|  |     * Emits DepartmentFundsRecovered events              | |
|  |                                                          | |
|  |  3. Minting Capabilities                                 | |
|  |     * CAN_MINT_UNDY (immutable)                          | |
|  |     * Set once at deployment                             | |
|  |     * Queried by UndyHq for permissions                  | |
|  +----------------------------------------------------------+ |
|                                                               |
|  +----------------------------------------------------------+ |
|  |                 Integration Pattern                      | |
|  |                                                          | |
|  |  Parent Contract                                         | |
|  |  initializes: deptBasics[addys := addys]                 | |
|  |                                                          | |
|  |  deptBasics.__init__(                                    | |
|  |      _shouldPause,    // Initial pause state             | |
|  |      _canMintUndy     // UNDY minting capability         | |
|  |  )                                                       | |
|  +----------------------------------------------------------+ |
+---------------------------------------------------------------+
                              |
                              v
+---------------------------------------------------------------+
|               Department Contract Examples                    |
|                                                               |
|  +------------------+  +------------------+  +--------------+ |
|  | Hatchery         |  | Switchboard      |  | Billing      | |
|  | * UNDY minting   |  | * No minting     |  | * No minting | |
|  | * Can pause      |  | * Can pause      |  | * Can pause  | |
|  +------------------+  +------------------+  +--------------+ |
|                                                               |
|  +------------------+  +------------------+                   |
|  | LootDistributor  |  | Appraiser        |                   |
|  | * No minting     |  | * No minting     |                   |
|  | * Can pause      |  | * Can pause      |                   |
|  +------------------+  +------------------+                   |
+---------------------------------------------------------------+
```

## State Variables

### Public State Variables
- `isPaused: bool` - Current pause state of the department

### Immutable Variables
- `CAN_MINT_UNDY: bool` - Whether this department can mint UNDY tokens

### Constants
- `MAX_RECOVER_ASSETS: uint256 = 20` - Maximum tokens recoverable in batch operation

## Constructor

### `__init__`

Initializes the DeptBasics module with pause state and minting capabilities.

```vyper
@deploy
def __init__(_shouldPause: bool, _canMintUndy: bool):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_shouldPause` | `bool` | Initial pause state for the department |
| `_canMintUndy` | `bool` | Whether department can mint UNDY tokens |

#### Returns

*Constructor does not return any values*

#### Access

Called only during deployment by parent contract

#### Example Usage
```python
# Initialize for a non-minting department (e.g., Billing)
deptBasics.__init__(
    False,  # Not paused initially
    False   # Cannot mint UNDY
)

# Initialize for Hatchery (can mint UNDY)
deptBasics.__init__(
    False,  # Not paused initially
    True    # Can mint UNDY
)
```

**Example Output**: Module initialized with specified capabilities

## Minting Query Functions

### `canMintUndy`

Returns whether this department has UNDY token minting capability.

```vyper
@view
@external
def canMintUndy() -> bool:
```

#### Parameters

*Function has no parameters*

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if department can mint UNDY tokens |

#### Access

Public view function

#### Example Usage
```python
# Check if Hatchery can mint UNDY
can_mint = hatchery.canMintUndy()
# Returns: True

# Check if Billing can mint UNDY
can_mint = billing.canMintUndy()
# Returns: False
```

## Pause Management Functions

### `pause`

Toggles the pause state of the department.

```vyper
@external
def pause(_shouldPause: bool):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_shouldPause` | `bool` | New pause state (must be different from current) |

#### Returns

*Function does not return any values*

#### Access

Only callable by Switchboard-registered contracts

#### Events Emitted

- `DepartmentPauseModified` - Contains the new pause state

#### Example Usage
```python
# Pause a department in emergency
department.pause(
    True,
    sender=switchboard_contract.address  # Must be in Switchboard
)

# Resume operations
department.pause(
    False,
    sender=switchboard_contract.address
)
```

**Example Output**: Department paused/unpaused, emits `DepartmentPauseModified`

## Recovery Functions

### `recoverFunds`

Recovers tokens accidentally sent to the department contract.

```vyper
@external
def recoverFunds(_recipient: address, _asset: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_recipient` | `address` | Address to receive recovered funds |
| `_asset` | `address` | Token contract address to recover |

#### Returns

*Function does not return any values*

#### Access

Only callable by Switchboard-registered contracts

#### Events Emitted

- `DepartmentFundsRecovered` - Contains asset address (indexed), recipient (indexed), and balance recovered

#### Example Usage
```python
# Recover accidentally sent USDC
dept_basics.recoverFunds(
    treasury.address,      # Send to treasury
    usdc_token.address,    # Token to recover
    sender=recovery_mgr.address  # Must be in Switchboard
)
```

**Example Output**: Transfers full token balance, emits `DepartmentFundsRecovered`

### `recoverFundsMany`

Recovers multiple tokens in a single transaction.

```vyper
@external
def recoverFundsMany(_recipient: address, _assets: DynArray[address, MAX_RECOVER_ASSETS]):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_recipient` | `address` | Address to receive all recovered funds |
| `_assets` | `DynArray[address, MAX_RECOVER_ASSETS]` | List of token addresses (max 20) |

#### Returns

*Function does not return any values*

#### Access

Only callable by Switchboard-registered contracts

#### Events Emitted

- `DepartmentFundsRecovered` - One event per recovered asset

#### Example Usage
```python
# Recover multiple tokens at once
tokens = [usdc.address, dai.address, weth.address]
dept_basics.recoverFundsMany(
    treasury.address,
    tokens,
    sender=recovery_mgr.address
)
```

**Example Output**: Transfers all token balances, emits event for each

## Usage Pattern

```python
# Example parent contract implementation
class DepartmentContract:
    # Initialize module
    def __init__(self):
        deptBasics.__init__(
            False,  # Not paused
            True    # Can mint UNDY
        )
    
    # Check pause in operations
    def sensitive_operation(self):
        if deptBasics.isPaused:
            raise "Department is paused"
        # Perform operation
    
    # UndyHq checks minting capability
    def can_mint_check(self):
        # UndyHq calls canMintUndy() as part of
        # permission checking for minting
        return deptBasics.canMintUndy()
```

## Integration with UndyHq

UndyHq uses DeptBasics minting declarations as part of its permission system:

1. **Configuration Check**: UndyHq checks if department has minting permission in HQ config
2. **Capability Check**: UndyHq calls `canMintUndy()` on the department
3. **Both Must Pass**: Minting only allowed if both checks return true

This ensures departments explicitly declare their minting intentions and prevents unauthorized minting even if misconfigured in UndyHq.

## Testing

Test examples can be found in the test suite for contracts that use the DeptBasics module.