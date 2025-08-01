# Ownership Technical Documentation

[📄 View Source Code](../../../contracts/modules/Ownership.vy)

## Overview

Ownership is a reusable module that provides secure, time-locked ownership transfer functionality for contracts in the Underscore Protocol. It implements a two-step process with configurable delays to prevent rushed or accidental ownership changes, while also providing emergency override capabilities through the MissionControl security system.

**Core Features**:
- **Time-locked Transfers**: Two-step ownership change process with mandatory waiting period
- **Security Override**: MissionControl authorized addresses can cancel pending transfers
- **Configurable Delays**: Adjustable time-lock periods within defined bounds
- **Inheritance Support**: Designed to be inherited by other contracts via `initializes` and `exports`

The module ensures secure ownership management with protection against common pitfalls like accidental transfers or compromised keys, while maintaining flexibility for legitimate ownership transitions and emergency interventions.

## Ownership Transfer Flow

```
Ownership Transfer Process:
+------------------+      +------------------+      +------------------+
|  Current Owner   |      |   Wait Period    |      |   New Owner      |
|  Initiates       | ---> | (Time-lock)      | ---> |   Confirms       |
|  Transfer        |      |                  |      |   Transfer       |
+------------------+      +------------------+      +------------------+
         |                                                    |
         |                      OR                            |
         v                                                    v
+------------------+                              +------------------+
| Cancel Transfer  |                              | Ownership        |
| (Owner or        |                              | Transferred      |
| MissionControl)  |                              |                  |
+------------------+                              +------------------+

Key Security Features:
* Only current owner can initiate transfers
* New owner must confirm after time-lock expires
* Current owner or security team can cancel pending transfers
* Configurable time-lock periods for flexibility
```

## Data Structures

### PendingOwnerChange Struct
Tracks pending ownership transfer details:
```vyper
struct PendingOwnerChange:
    newOwner: address           # The proposed new owner
    initiatedBlock: uint256     # Block when transfer was initiated
    confirmBlock: uint256       # Block when transfer can be confirmed
```

## State Variables

### Public State Variables
- `owner: address` - Current owner of the contract
- `ownershipTimeLock: uint256` - Current time-lock period in blocks
- `pendingOwner: PendingOwnerChange` - Details of pending ownership change

### Immutable Variables
- `UNDY_HQ_FOR_OWNERSHIP: address` - UndyHq registry address
- `MIN_OWNERSHIP_TIMELOCK: uint256` - Minimum allowed time-lock period
- `MAX_OWNERSHIP_TIMELOCK: uint256` - Maximum allowed time-lock period

### Constants
- `MISSION_CONTROL_ID: uint256 = 2` - Registry ID for MissionControl

## Constructor

### `__init__`

Initializes the Ownership module with initial owner and time-lock parameters.

```vyper
@deploy
def __init__(
    _undyHq: address,
    _owner: address,
    _minTimeLock: uint256,
    _maxTimeLock: uint256,
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq registry contract address |
| `_owner` | `address` | Initial owner address |
| `_minTimeLock` | `uint256` | Minimum time-lock blocks allowed |
| `_maxTimeLock` | `uint256` | Maximum time-lock blocks allowed |

#### Returns

*Constructor does not return any values*

#### Access

Called only during deployment by parent contract

#### Example Usage
```python
# Initialize within parent contract
ownership.__init__(
    undy_hq.address,
    deployer.address,
    100,    # Min 100 blocks
    10000   # Max 10000 blocks
)
```

**Example Output**: Module initialized with owner set and time-lock at minimum value

## Ownership Transfer Functions

### `changeOwnership`

Initiates a time-locked ownership transfer to a new address.

```vyper
@external
def changeOwnership(_newOwner: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_newOwner` | `address` | The proposed new owner address |

#### Returns

*Function does not return any values*

#### Access

Only callable by current owner

#### Events Emitted

- `OwnershipChangeInitiated` - Contains previous owner (indexed), new owner (indexed), and confirmation block

#### Example Usage
```python
# Current owner initiates transfer
contract.changeOwnership(
    new_owner.address,
    sender=current_owner.address
)
```

**Example Output**: Emits `OwnershipChangeInitiated` with confirmation block = current block + time-lock

#### Validation
- Caller must be current owner
- New owner cannot be empty address
- New owner cannot be current owner

### `confirmOwnershipChange`

Confirms a pending ownership change after the time-lock period expires.

```vyper
@external
def confirmOwnershipChange():
```

#### Parameters

*Function has no parameters*

#### Returns

*Function does not return any values*

#### Access

Only callable by the pending new owner after time-lock expires

#### Events Emitted

- `OwnershipChangeConfirmed` - Contains previous owner (indexed), new owner (indexed), initiation block, and confirmation block

#### Example Usage
```python
# Wait for time-lock to expire
boa.env.time_travel(blocks=ownership_timelock)

# New owner confirms the transfer
contract.confirmOwnershipChange(sender=new_owner.address)
```

**Example Output**: Ownership transferred, pending data cleared

#### Validation
- Must have pending ownership change
- Time-lock period must have expired
- Caller must be the pending new owner

### `cancelOwnershipChange`

Cancels a pending ownership change.

```vyper
@external
def cancelOwnershipChange():
```

#### Parameters

*Function has no parameters*

#### Returns

*Function does not return any values*

#### Access

Callable by current owner or MissionControl authorized address

#### Events Emitted

- `OwnershipChangeCancelled` - Contains cancelled owner (indexed), cancelled by (indexed), initiation block, and confirmation block

#### Example Usage
```python
# Owner cancels pending change
contract.cancelOwnershipChange(sender=current_owner.address)

# Or security team cancels
contract.cancelOwnershipChange(sender=security_admin.address)
```

**Example Output**: Pending ownership change cleared

#### Validation
- Must have pending ownership change
- Caller must be owner or authorized by MissionControl

## Time-lock Configuration Functions

### `setOwnershipTimeLock`

Updates the ownership change time-lock period.

```vyper
@external
def setOwnershipTimeLock(_numBlocks: uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_numBlocks` | `uint256` | New time-lock period in blocks |

#### Returns

*Function does not return any values*

#### Access

Only callable by current owner

#### Events Emitted

- `OwnershipTimeLockSet` - Contains new time-lock value

#### Example Usage
```python
# Update time-lock to 1000 blocks
contract.setOwnershipTimeLock(1000, sender=owner.address)
```

**Example Output**: Time-lock updated, emits `OwnershipTimeLockSet`

#### Validation
- Caller must be current owner
- New time-lock must be >= MIN_OWNERSHIP_TIMELOCK
- New time-lock must be <= MAX_OWNERSHIP_TIMELOCK

## Query Functions

### `hasPendingOwnerChange`

Checks if there's a pending ownership change.

```vyper
@view
@external
def hasPendingOwnerChange() -> bool:
```

#### Parameters

*Function has no parameters*

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if an ownership change is pending |

#### Access

Public view function

#### Example Usage
```python
has_pending = contract.hasPendingOwnerChange()
# Returns: True if pendingOwner.confirmBlock != 0
```

## Internal Functions

### `_canPerformSecurityAction`

Internal function to check if an address has security permissions via MissionControl.

```vyper
@view
@internal
def _canPerformSecurityAction(_addr: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | Address to check |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if address has security permissions |

#### Logic
1. Retrieves MissionControl address from UndyHq registry
2. Returns false if MissionControl not set
3. Calls MissionControl to check permissions

## Integration Pattern

The Ownership module is designed to be integrated into other contracts using Vyper's module system:

```vyper
# In parent contract
initializes: ownership
exports: ownership.__interface__
import contracts.modules.Ownership as ownership

@deploy
def __init__(...):
    # Initialize ownership module
    ownership.__init__(
        _undyHq,
        _owner,
        _minTimeLock,
        _maxTimeLock
    )
    # Continue with parent initialization
```

This pattern:
1. Initializes the ownership module's storage
2. Exports all ownership functions as part of parent's interface
3. Makes `owner` and other state variables accessible
4. Inherits all events and functionality

## Security Considerations

### Time-lock Protection
- Mandatory waiting period prevents rushed transfers
- Configurable delays allow flexibility based on security needs
- Cannot be bypassed except by cancellation

### Access Control
- Only current owner can initiate transfers
- Only new owner can confirm (prevents griefing)
- Security override via MissionControl for emergencies

### Validation Checks
- Prevents transfer to empty address
- Prevents redundant transfer to current owner
- Ensures time-lock bounds are respected

### Emergency Response
- MissionControl integration allows security team intervention
- Can cancel suspicious or compromised transfers
- Maintains decentralization while providing safety net

## Usage Example

Here's a complete example of ownership transfer:

```python
# 1. Current owner initiates transfer
contract.changeOwnership(
    new_owner.address,
    sender=current_owner.address
)
# Event: OwnershipChangeInitiated

# 2. Wait for time-lock period
current_timelock = contract.ownershipTimeLock()
boa.env.time_travel(blocks=current_timelock)

# 3. New owner confirms
contract.confirmOwnershipChange(
    sender=new_owner.address
)
# Event: OwnershipChangeConfirmed

# Verify ownership changed
assert contract.owner() == new_owner.address
```

## Testing

For comprehensive test examples, see: [`tests/modules/test_ownership.py`](../../../tests/modules/test_ownership.py)