# Addys Technical Documentation

[📄 View Source Code](../../../contracts/modules/Addys.vy)

## Overview

Addys is the centralized address resolution module for the Underscore Protocol, functioning as a sophisticated directory service that provides instant access to all protocol contracts. It eliminates redundant address storage across
contracts while maintaining consistency and reducing gas costs through intelligent caching.

**Core Functions**:
- **Protocol Directory**: Unified interface returning all protocol addresses through a single struct
- **Address Validation**: Comprehensive checks for core departments, vaults, and configuration contracts
- **Gas Optimization**: Batch retrieval and caching mechanisms minimize external calls and storage reads

The module uses lazy loading, struct-based batch retrieval, immutable RipeHq reference, and comprehensive helper functions, ensuring efficient and consistent address resolution throughout the protocol.

## Architecture & Design

Addys is designed as a lightweight, inheritable module that other contracts can use to access protocol addresses:

### Core Components
- **UndyHq Integration**: Direct connection to the master registry
- **Address Struct**: Efficient batch retrieval mechanism
- **Validation Logic**: Multi-layer permission checking
- **Helper Functions**: Specific getters for each protocol component

### Module Pattern
```vyper
# Other contracts inherit Addys like this:
initializes: addys
```

This gives the inheriting contract access to all internal functions and the ability to efficiently retrieve protocol addresses.

## System Architecture Diagram

```
+------------------------------------------------------------------------+
|                           Addys Module                                 |
+------------------------------------------------------------------------+
|                                                                        |
|  +------------------------------------------------------------------+  |
|  |                    Address Resolution Flow                       |  |
|  |                                                                  |  |
|  |  1. Contract inherits Addys module                               |  |
|  |     initializes: addys                                           |  |
|  |                                                                  |  |
|  |  2. Calls _getAddys() or specific getter                         |  |
|  |     - Single call returns all addresses                          |  |
|  |     - Or get specific address directly                           |  |
|  |                                                                  |  |
|  |  3. Addys queries UndyHq registry                                |  |
|  |     - Uses constant IDs for each component                       |  |
|  |     - Returns current addresses                                  |  |
|  |                                                                  |  |
|  |  4. Returns structured data                                      |  |
|  |     - Addys struct with all addresses                           |  |
|  |     - Or individual address                                      |  |
|  +------------------------------------------------------------------+  |
|                                                                        |
|  +------------------------------------------------------------------+  |
|  |                     Validation Logic Flow                        |  |
|  |                                                                  |  |
|  |  _isValidUndyAddr(_addr) checks:                                 |  |
|  |                                                                  |  |
|  |  1. Core Department Check                                        |  |
|  |     └─> UndyHq.isValidAddr(_addr)                               |  |
|  |                                                                  |  |
|  |  2. Lego Book Check                                             |  |
|  |     └─> LegoBook.isLegoAddr(_addr)                              |  |
|  |                                                                  |  |
|  |  3. Switchboard Check                                            |  |
|  |     └─> Switchboard.isSwitchboardAddr(_addr)                    |  |
|  |                                                                  |  |
|  |  Returns: True if any check passes                              |  |
|  +------------------------------------------------------------------+  |
+------------------------------------------------------------------------+
                                    |
                                    v
                         +--------------------+
                         |      UndyHq        |
                         | (Master Registry)  |
                         +--------------------+
                                    |
        +---------------------------+---------------------------+
        |                           |                           |
        v                           v                           v
+------------------+    +-------------------+    +------------------+
| Core Contracts   |    | Lego System       |    | Config System    |
| * Undy Token     |    | * LegoBook        |    | * Switchboard    |
| * Hatchery       |    | * Registered      |    | * Registered     |
| * Billing, etc.  |    |   Legos           |    |   Configs        |
+------------------+    +-------------------+    +------------------+
```

## Data Structures

### Addys Struct
Complete protocol address collection:
```vyper
struct Addys:
    hq: address                  # UndyHq master registry
    undyToken: address           # UNDY token
    ledger: address              # Accounting system
    missionControl: address      # Configuration storage
    legoBook: address            # Lego registry
    switchboard: address         # Config access control
    hatchery: address            # User wallet factory
    lootDistributor: address     # Rewards distribution
    appraiser: address           # Asset valuation
    walletBackpack: address      # Wallet backpack registry
    billing: address             # Billing system
```

## State Variables

### Immutable Variables
- `UNDY_HQ_FOR_ADDYS: immutable(address)` - UndyHq registry address

### Constants (Registry IDs)
- `LEDGER_ID: constant(uint256) = 1`
- `MISSION_CONTROL_ID: constant(uint256) = 2`
- `LEGO_BOOK_ID: constant(uint256) = 3`
- `SWITCHBOARD_ID: constant(uint256) = 4`
- `HATCHERY_ID: constant(uint256) = 5`
- `LOOT_DISTRIBUTOR_ID: constant(uint256) = 6`
- `APPRAISER_ID: constant(uint256) = 7`
- `WALLET_BACKPACK_ID: constant(uint256) = 8`
- `BILLING_ID: constant(uint256) = 9`

## Constructor

### `__init__`

Initializes the Addys module with the UndyHq registry address.

```vyper
@deploy
def __init__(_undyHq: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq master registry contract |

#### Returns

*Constructor does not return any values*

#### Access

Called only during module initialization

#### Example Usage
```python
# When deploying a contract that uses Addys
contract = boa.load(
    "contracts/core/Appraiser.vy",
    undy_hq.address  # Passed to Addys module
)
```

## Core Functions

### `getAddys`

Returns all protocol addresses in a single struct.

```vyper
@view
@external
def getAddys() -> Addys:
```

#### Returns

| Type | Description |
|------|-------------|
| `Addys` | Struct containing all protocol addresses |

#### Access

Public view function

#### Example Usage
```python
# Get all protocol addresses
addys = contract.getAddys()
undy_token = addys.undyToken
hatchery = addys.hatchery
```

### `getUndyHq`

Returns the UndyHq registry address.

```vyper
@view
@external
def getUndyHq() -> address:
```

#### Returns

| Type | Description |
|------|-------------|
| `address` | UndyHq registry address |

#### Access

Public view function

## Internal Helper Functions

### `_getAddys`

Internal function to get all addresses with caching support.

```vyper
@view
@internal
def _getAddys(_addys: Addys = empty(Addys)) -> Addys:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addys` | `Addys` | Optional cached addresses |

#### Returns

| Type | Description |
|------|-------------|
| `Addys` | Complete address struct |

#### Usage Pattern
```vyper
# In inheriting contract
def someFunction():
    a: Addys = self._getAddys()
    undy: address = a.undyToken
```

### `_generateAddys`

Creates a fresh Addys struct by querying UndyHq.

```vyper
@view
@internal
def _generateAddys() -> Addys:
```

#### Returns

| Type | Description |
|------|-------------|
| `Addys` | Newly generated address struct |

## Token Address Functions

### `_getUndyToken`

Returns the Undy token address.

```vyper
@view
@internal
def _getUndyToken() -> address:
```

## Validation Functions

### `_isValidUndyAddr`

Comprehensive validation to check if an address is a valid protocol participant.

```vyper
@view
@internal
def _isValidUndyAddr(_addr: address, _hq: address = empty(address)) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | Address to validate |
| `_hq` | `address` | Optional UndyHq address (uses default if empty) |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if valid Undy address |

#### Validation Logic
1. Checks if address is a core department in UndyHq
2. Checks if address is a registered lego in LegoBook
3. Checks if address is a registered config in Switchboard

#### Example Usage
```vyper
# In inheriting contract
if not self._isValidUndyAddr(msg.sender):
    raise "unauthorized"
```

### `_isSwitchboardAddr`

Checks if an address is registered in Switchboard.

```vyper
@view
@internal
def _isSwitchboardAddr(_addr: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | Address to check |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if registered in Switchboard |

### `_isLegoBookAddr`

Checks if an address is registered in LegoBook.

```vyper
@view
@internal
def _isLegoBookAddr(_addr: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | Address to check |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if registered in LegoBook |

## Department-Specific Functions

Each department has a pair of functions for getting its ID and address:

### Ledger Functions
- `_getLedgerId() -> uint256` - Returns LEDGER_ID (1)
- `_getLedgerAddr() -> address` - Returns Ledger address

### Mission Control Functions
- `_getMissionControlId() -> uint256` - Returns MISSION_CONTROL_ID (2)
- `_getMissionControlAddr() -> address` - Returns Mission Control address

### LegoBook Functions
- `_getLegoBookId() -> uint256` - Returns LEGO_BOOK_ID (3)
- `_getLegoBookAddr() -> address` - Returns LegoBook address

### Switchboard Functions
- `_getSwitchboardId() -> uint256` - Returns SWITCHBOARD_ID (4)
- `_getSwitchboardAddr() -> address` - Returns Switchboard address

### Hatchery Functions
- `_getHatcheryId() -> uint256` - Returns HATCHERY_ID (5)
- `_getHatcheryAddr() -> address` - Returns Hatchery address

### LootDistributor Functions
- `_getLootDistributorId() -> uint256` - Returns LOOT_DISTRIBUTOR_ID (6)
- `_getLootDistributorAddr() -> address` - Returns LootDistributor address

### Appraiser Functions
- `_getAppraiserId() -> uint256` - Returns APPRAISER_ID (7)
- `_getAppraiserAddr() -> address` - Returns Appraiser address

### WalletBackpack Functions
- `_getWalletBackpackId() -> uint256` - Returns WALLET_BACKPACK_ID (8)
- `_getWalletBackpackAddr() -> address` - Returns WalletBackpack address

### Billing Functions
- `_getBillingId() -> uint256` - Returns BILLING_ID (9)
- `_getBillingAddr() -> address` - Returns Billing address

## Usage Patterns

### Basic Address Retrieval
```vyper
# Get all addresses at once
a: Addys = self._getAddys()
undy: address = a.undyToken
ledger: address = a.ledger
```

### Individual Address Retrieval
```vyper
# Get specific address directly
mc: address = self._getMissionControlAddr()
```

### Address Validation
```vyper
# Validate caller
assert self._isValidUndyAddr(msg.sender), "unauthorized"
```

### Caching Pattern
```vyper
# Pass cached addresses to avoid redundant lookups
def someFunction(_a: Addys = empty(Addys)):
    a: Addys = self._getAddys(_a)
    # Use addresses from 'a'
```

## Gas Optimization

The Addys module implements several gas optimization strategies:

1. **Batch Retrieval**: Getting all addresses in one struct is more efficient than individual calls
2. **Caching Support**: Functions accept pre-fetched addresses to avoid redundant lookups
3. **Immutable Storage**: UndyHq address stored as immutable reduces SLOAD costs
4. **Constant IDs**: Using constants for registry IDs eliminates storage reads

## Security Considerations

1. **Immutable Registry**: UndyHq address cannot be changed after deployment
2. **Registry Authority**: All addresses come from the authoritative UndyHq registry
3. **Validation Layers**: Multiple validation checks ensure comprehensive coverage
4. **No Direct State**: Module has no mutable state, reducing attack surface

## Testing

Test examples can be found in contracts that utilize the Addys module.