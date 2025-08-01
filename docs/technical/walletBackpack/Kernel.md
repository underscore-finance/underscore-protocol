# Kernel Technical Documentation

[📄 View Source Code](../../../contracts/core/walletBackpack/Kernel.vy)

## Overview

Kernel is the whitelist management module for user wallets in the Underscore Protocol. As a critical wallet backpack item, it provides secure, time-locked management of whitelisted addresses, enabling wallets to establish trusted relationships with external contracts and addresses while maintaining security through multi-tier permissions and delayed activation.

**Core Features**:
- **Time-locked Whitelist Operations**: All whitelist additions require time-delay for security
- **Multi-tier Permission System**: Owner, manager, and security roles with different capabilities
- **Two-step Confirmation Process**: Pending whitelist additions require explicit confirmation after time-lock
- **Flexible Permission Configuration**: Granular control over who can add, confirm, cancel, and remove
- **Emergency Override**: MissionControl integration for security interventions

The contract implements sophisticated permission validation ensuring only authorized parties can manage whitelist, time-locked operations preventing immediate additions, comprehensive event logging for audit trails, and integration with the broader wallet security framework.

## System Architecture Diagram

```
+-------------------------------------------------------------------------+
|                                Kernel                                   |
+-------------------------------------------------------------------------+
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                    Whitelist Management Flow                      | |
|  |                                                                   | |
|  |  1. Add Pending Whitelist:                                       | |
|  |     ├─> Validate caller permissions                              | |
|  |     ├─> Check address not already whitelisted/pending            | |
|  |     ├─> Calculate confirmation block (current + timeLock)        | |
|  |     └─> Store pending whitelist entry                            | |
|  |                                                                   | |
|  |  2. Time-lock Period:                                             | |
|  |     └─> Must wait until confirmBlock reached                     | |
|  |                                                                   | |
|  |  3. Confirm Whitelist:                                            | |
|  |     ├─> Validate caller permissions                              | |
|  |     ├─> Check time-lock expired                                  | |
|  |     ├─> Verify owner hasn't changed                              | |
|  |     └─> Add to active whitelist                                  | |
|  |                                                                   | |
|  |  4. Cancel/Remove:                                                | |
|  |     └─> Can cancel pending or remove active entries              | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                      Permission Hierarchy                         | |
|  |                                                                   | |
|  |  Owner:                                                           | |
|  |    - Full control over all whitelist operations                   | |
|  |    - Can add, confirm, cancel, and remove                         | |
|  |    - Bypass manager permission checks                             | |
|  |                                                                   | |
|  |  Manager (with permissions):                                      | |
|  |    - canAddPending: Add addresses to pending whitelist            | |
|  |    - canConfirm: Confirm pending entries after time-lock          | |
|  |    - canCancel: Cancel pending entries                            | |
|  |    - canRemove: Remove active whitelist entries                   | |
|  |    - Subject to both individual and global settings               | |
|  |                                                                   | |
|  |  Security (MissionControl):                                       | |
|  |    - Can cancel pending entries (emergency override)              | |
|  |    - Can remove whitelist entries (security action)               | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                    Whitelist Action Types                         | |
|  |                                                                   | |
|  |  ADD_PENDING:       Add address to pending whitelist              | |
|  |  CONFIRM_WHITELIST: Confirm pending after time-lock               | |
|  |  CANCEL_WHITELIST:  Cancel pending whitelist entry                | |
|  |  REMOVE_WHITELIST:  Remove active whitelist entry                 | |
|  +-------------------------------------------------------------------+ |
+-------------------------------------------------------------------------+
```

## Constants and Immutables

### Constants
- `LEDGER_ID: uint256 = 1` - Registry ID for Ledger contract
- `MISSION_CONTROL_ID: uint256 = 2` - Registry ID for MissionControl

### Immutable Variables
- `UNDY_HQ: address` - UndyHq registry address

## Constructor

### `__init__`

Initializes Kernel with the protocol registry address.

```vyper
@deploy
def __init__(_undyHq: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq registry contract address |

#### Access

Called only during deployment

#### Example Usage
```python
kernel = Kernel.deploy(
    undy_hq.address
)
```

## Whitelist Management Functions

### `addPendingWhitelistAddr`

Initiates a time-locked whitelist addition for an address.

```vyper
@external
def addPendingWhitelistAddr(_userWallet: address, _whitelistAddr: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet address |
| `_whitelistAddr` | `address` | Address to add to whitelist |

#### Access

- Wallet owner
- Managers with `canAddPending` permission

#### Events Emitted

- `WhitelistAddrPending` - Contains user (indexed), addr (indexed), confirmBlock, and addedBy (indexed)

#### Example Usage
```python
# Owner adds pending whitelist
kernel.addPendingWhitelistAddr(
    user_wallet.address,
    trusted_contract.address,
    sender=owner
)

# Manager adds pending whitelist
kernel.addPendingWhitelistAddr(
    user_wallet.address,
    service_provider.address,
    sender=manager  # Must have canAddPending permission
)
```

#### Notes

- Cannot whitelist: empty address, wallet, owner, or walletConfig
- Address must not already be whitelisted or pending
- Confirmation block = current block + wallet timeLock

### `confirmWhitelistAddr`

Confirms a pending whitelist entry after time-lock expiry.

```vyper
@external
def confirmWhitelistAddr(_userWallet: address, _whitelistAddr: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet address |
| `_whitelistAddr` | `address` | Pending address to confirm |

#### Access

- Wallet owner
- Managers with `canConfirm` permission

#### Events Emitted

- `WhitelistAddrConfirmed` - Contains user (indexed), addr (indexed), initiatedBlock, confirmBlock, and confirmedBy (indexed)

#### Example Usage
```python
# Wait for time-lock to expire
boa.env.time_travel(blocks=timelock)

# Confirm the pending whitelist
kernel.confirmWhitelistAddr(
    user_wallet.address,
    trusted_contract.address,
    sender=owner
)
```

#### Notes

- Must have pending whitelist entry
- Current block must be >= confirmBlock
- Owner must not have changed since initiation

### `cancelPendingWhitelistAddr`

Cancels a pending whitelist entry.

```vyper
@external
def cancelPendingWhitelistAddr(_userWallet: address, _whitelistAddr: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet address |
| `_whitelistAddr` | `address` | Pending address to cancel |

#### Access

- Wallet owner
- Managers with `canCancel` permission
- MissionControl authorized addresses

#### Events Emitted

- `WhitelistAddrCancelled` - Contains user (indexed), addr (indexed), initiatedBlock, confirmBlock, and cancelledBy (indexed)

#### Example Usage
```python
# Owner cancels pending whitelist
kernel.cancelPendingWhitelistAddr(
    user_wallet.address,
    untrusted_address.address,
    sender=owner
)

# Security team cancels suspicious pending entry
kernel.cancelPendingWhitelistAddr(
    user_wallet.address,
    suspicious_address.address,
    sender=security_admin  # MissionControl authorized
)
```

### `removeWhitelistAddr`

Removes an active whitelist entry.

```vyper
@external
def removeWhitelistAddr(_userWallet: address, _whitelistAddr: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet address |
| `_whitelistAddr` | `address` | Whitelisted address to remove |

#### Access

- Wallet owner
- Managers with `canRemove` permission
- MissionControl authorized addresses

#### Events Emitted

- `WhitelistAddrRemoved` - Contains user (indexed), addr (indexed), and removedBy (indexed)

#### Example Usage
```python
# Owner removes whitelisted address
kernel.removeWhitelistAddr(
    user_wallet.address,
    old_contract.address,
    sender=owner
)

# Manager removes with permission
kernel.removeWhitelistAddr(
    user_wallet.address,
    deprecated_service.address,
    sender=manager  # Must have canRemove permission
)
```

#### Notes

- Address must be currently whitelisted
- Removal is immediate (no time-lock)

## Permission Validation Functions

### `canManageWhitelist`

Checks if a caller can perform a specific whitelist action.

```vyper
@view
@external
def canManageWhitelist(
    _userWallet: address,
    _caller: address,
    _action: wcs.WhitelistAction,
) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet address |
| `_caller` | `address` | Address to check permissions for |
| `_action` | `WhitelistAction` | Action type to validate |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if caller can perform the action |

#### Access

Public view function

#### Example Usage
```python
# Check if manager can add pending
can_add = kernel.canManageWhitelist(
    user_wallet.address,
    manager.address,
    WhitelistAction.ADD_PENDING
)

# Check if manager can confirm
can_confirm = kernel.canManageWhitelist(
    user_wallet.address,
    manager.address,
    WhitelistAction.CONFIRM_WHITELIST
)
```

## Utility Functions

### `getWhitelistConfig`

Retrieves comprehensive whitelist configuration and state.

```vyper
@view
@external
def getWhitelistConfig(_userWallet: address, _whitelistAddr: address, _caller: address) -> wcs.WhitelistConfigBundle:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet address |
| `_whitelistAddr` | `address` | Address to check whitelist status |
| `_caller` | `address` | Caller address for permission check |

#### Returns

| Type | Description |
|------|-------------|
| `WhitelistConfigBundle` | Bundle containing configuration and state |

#### Access

Public view function

#### Bundle Contents
- `owner` - Wallet owner address
- `wallet` - User wallet address
- `isWhitelisted` - Whether address is whitelisted
- `pendingWhitelist` - Pending whitelist data if exists
- `timeLock` - Current wallet time-lock setting
- `walletConfig` - Config contract address
- `isManager` - Whether caller is a manager
- `isOwner` - Whether caller is the owner
- `whitelistPerms` - Caller's whitelist permissions
- `globalWhitelistPerms` - Global whitelist permissions

#### Example Usage
```python
# Get whitelist status and permissions
config = kernel.getWhitelistConfig(
    user_wallet.address,
    target_address.address,
    manager.address
)

if config.isWhitelisted:
    print("Address is whitelisted")
elif config.pendingWhitelist.initiatedBlock > 0:
    print(f"Pending until block {config.pendingWhitelist.confirmBlock}")
```

## Internal Permission Logic

### Permission Evaluation

The contract uses a two-tier permission system:

1. **Owner Privileges**:
   - Always has full control
   - Can perform any whitelist action
   - Bypasses all permission checks

2. **Manager Permissions**:
   - Must be an active manager
   - Requires both individual AND global permission
   - Each action type has specific permission flag

### Permission Matrix

| Action | Individual Permission | Global Permission | Description |
|--------|---------------------|-------------------|-------------|
| ADD_PENDING | canAddPending | canAddPending | Add to pending whitelist |
| CONFIRM_WHITELIST | canConfirm | canConfirm | Confirm after time-lock |
| CANCEL_WHITELIST | canCancel | canCancel | Cancel pending entry |
| REMOVE_WHITELIST | canRemove | canRemove | Remove active entry |

### Security Override

MissionControl authorized addresses can:
- Cancel pending whitelist entries
- Remove active whitelist entries
- Bypass normal permission checks

## Security Considerations

### Time-lock Protection
- All whitelist additions require time-delay
- Prevents immediate malicious additions
- Time-lock duration set by wallet configuration
- Owner changes invalidate pending entries

### Permission Layers
1. Individual manager permissions
2. Global manager settings
3. MissionControl override
4. Owner ultimate control

### Validation Rules
- Cannot whitelist system addresses (wallet, owner, config)
- Cannot have duplicate pending entries
- Must verify owner consistency on confirmation
- Empty address validation

### Emergency Controls
- MissionControl can intervene for security
- Pending entries can be cancelled
- Active entries can be removed
- No funds at risk during pending period

## Common Integration Patterns

### Basic Whitelist Addition
```python
# 1. Add to pending whitelist
kernel.addPendingWhitelistAddr(
    wallet.address,
    defi_protocol.address,
    sender=owner
)

# 2. Wait for time-lock
boa.env.time_travel(blocks=timelock)

# 3. Confirm whitelist
kernel.confirmWhitelistAddr(
    wallet.address,
    defi_protocol.address,
    sender=owner
)
```

### Manager-Initiated Whitelist
```python
# 1. Manager adds pending (requires permission)
kernel.addPendingWhitelistAddr(
    wallet.address,
    new_integration.address,
    sender=manager
)

# 2. Owner confirms after review and time-lock
boa.env.time_travel(blocks=timelock)
kernel.confirmWhitelistAddr(
    wallet.address,
    new_integration.address,
    sender=owner
)
```

### Emergency Removal
```python
# Security team removes compromised contract
kernel.removeWhitelistAddr(
    wallet.address,
    compromised_contract.address,
    sender=security_admin  # MissionControl authorized
)
```

### Permission Check Before Action
```python
# Check if action is allowed
if kernel.canManageWhitelist(
    wallet.address,
    manager.address,
    WhitelistAction.ADD_PENDING
):
    kernel.addPendingWhitelistAddr(
        wallet.address,
        target.address,
        sender=manager
    )
```

## Testing

For comprehensive test examples, see: [`tests/core/walletBackpack/kernel/`](../../../tests/core/walletBackpack/kernel/)