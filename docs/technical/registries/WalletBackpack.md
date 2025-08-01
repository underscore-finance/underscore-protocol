# WalletBackpack Technical Documentation

[📄 View Source Code](../../../contracts/registries/WalletBackpack.vy)

## Overview

WalletBackpack is the centralized registry for all wallet-related support contracts in the Underscore Protocol. It manages the deployment and updates of critical wallet infrastructure components including security validation (Sentinel), execution logic (Kernel), configuration management (HighCommand), payment processing (Paymaster, ChequeBook), and migration tooling (Migrator). As a Department contract, it provides time-locked upgrade mechanisms to ensure secure evolution of the wallet ecosystem.

**Core Functions**:
- **Wallet Infrastructure Registry**: Maintains authoritative addresses for all wallet support contracts.
- **Time-Locked Upgrades**: Provides secure upgrade paths for critical wallet components with governance oversight.
- **Interface Validation**: Ensures new contracts implement required interfaces before deployment.
- **Ledger Integration**: Automatically registers new components with the protocol's Ledger for tracking.

Built with the Department architecture, WalletBackpack combines governance controls with specialized timelock mechanisms for wallet infrastructure management. It ensures that wallet upgrades are performed safely through controlled, reviewable processes that protect user funds and maintain system integrity.

## Architecture & Modules

WalletBackpack uses the Department architecture with specialized TimeLock functionality for wallet infrastructure:

### LocalGov Module
- **Location**: `contracts/modules/LocalGov.vy`
- **Purpose**: Provides governance functionality with temporary governance support.
- **Documentation**: See [LocalGov Technical Documentation](../modules/LocalGov.md)
- **Key Features**:
  - Links to UndyHq as the primary governance authority.
  - Supports temporary governance during initial deployment.
  - No local governance timelock (managed by TimeLock module).
- **Exported Interface**: All governance functions are exposed via `gov.__interface__`.

### Addys Module
- **Location**: `contracts/modules/Addys.vy`
- **Purpose**: Provides protocol-wide address lookups.
- **Documentation**: See [Addys Technical Documentation](../modules/Addys.md)
- **Key Features**:
  - Connection to UndyHq for protocol addresses.
  - Cached address lookups for gas efficiency.
  - Ledger address resolution for component registration.
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

### TimeLock Module
- **Location**: `contracts/modules/Timelock.vy`
- **Purpose**: Provides time-locked action management for wallet upgrades.
- **Documentation**: See [Timelock Technical Documentation](../modules/Timelock.md)
- **Key Features**:
  - Configurable minimum and maximum timelock periods.
  - Action initiation, confirmation, and cancellation.
  - Protection against immediate malicious upgrades.
- **Exported Interface**: All timelock functions are exposed via `timeLock.__interface__`.

### Module Initialization
```vyper
initializes: gov
initializes: addys
initializes: deptBasics[addys := addys]
initializes: timeLock[gov := gov]
```
This initialization pattern ensures proper module dependencies and secure timelock management for wallet infrastructure.

## System Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                      WalletBackpack Contract                       │
├────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐         ┌──────────────────────────────┐  │
│  │   LocalGov Module   │         │    TimeLock Module           │  │
│  │                     │         │                              │  │
│  │ • UndyHq governance │         │ • Time-locked upgrades       │  │
│  │ • Temp governance   │         │ • Action management          │  │
│  │ • Permission checks │         │ • Confirmation delays        │  │
│  └─────────────────────┘         └──────────────────────────────┘  │
│                                                                    │
│  ┌─────────────────────┐         ┌──────────────────────────────┐  │
│  │    Addys Module     │         │    DeptBasics Module         │  │
│  │                     │         │                              │  │
│  │ • Protocol addrs    │         │ • Pause functionality        │  │
│  │ • Ledger connection │         │ • Fund recovery              │  │
│  │ • Address caching   │         │ • No minting (False)         │  │
│  └─────────────────────┘         └──────────────────────────────┘  │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                  Wallet Infrastructure Registry               │  │
│  │                                                              │  │
│  │  Current Implementations:                                    │  │
│  │    • kernel: Wallet execution logic                         │  │
│  │    • sentinel: Security validation                          │  │
│  │    • highCommand: Configuration management                  │  │
│  │    • paymaster: Payment processing                          │  │
│  │    • chequeBook: Cheque management                          │  │
│  │    • migrator: Wallet migration tools                       │  │
│  │                                                              │  │
│  │  Pending Updates: (time-locked changes)                     │  │
│  │    • pendingUpdates[BackpackType] → PendingBackpackItem     │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                                     │
                     ┌───────────────┴───────────────┐
                     ▼                               ▼
        ┌─────────────────────┐          ┌─────────────────────┐
        │  Wallet Components  │          │      User Wallets   │
        │                     │          │                     │
        │ • Kernel.vy         │          │ • UserWallet.vy     │
        │ • Sentinel.vy       │          │ • UserWalletConfig  │
        │ • HighCommand.vy    │          │ • Individual users  │
        │ • Paymaster.vy      │          │ • Agent integrations│
        │ • ChequeBook.vy     │          │                     │
        │ • Migrator.vy       │          │                     │
        └─────────────────────┘          └─────────────────────┘
                     │                               │
                     ▼                               ▼
        ┌─────────────────────┐          ┌─────────────────────┐
        │   Infrastructure    │          │   User Experience   │
        │                     │          │                     │
        │ • Security rules    │          │ • Safe operations   │
        │ • Payment logic     │          │ • Config management │
        │ • Migration tools   │          │ • Fund protection   │
        └─────────────────────┘          └─────────────────────┘
```

## Data Structures

### BackpackType Enum
Defines the types of wallet infrastructure components:
```vyper
flag BackpackType:
    WALLET_KERNEL          # Execution logic
    WALLET_SENTINEL        # Security validation
    WALLET_HIGH_COMMAND    # Configuration management
    WALLET_PAYMASTER       # Payment processing
    WALLET_CHEQUE_BOOK     # Cheque management
    WALLET_MIGRATOR        # Migration tools
```

### PendingBackpackItem Struct
Tracks pending infrastructure upgrades during timelock:
```vyper
struct PendingBackpackItem:
    actionId: uint256      # TimeLock action identifier
    addr: address          # New contract address
```

## State Variables

### Current Infrastructure Components
- `kernel: address` - Current wallet execution logic contract
- `sentinel: address` - Current security validation contract
- `highCommand: address` - Current configuration management contract
- `paymaster: address` - Current payment processing contract
- `chequeBook: address` - Current cheque management contract
- `migrator: address` - Current migration tools contract

### Pending Changes
- `pendingUpdates: HashMap[BackpackType, PendingBackpackItem]` - Maps component type to pending upgrade

### Constants
- `MAX_ASSETS: uint256 = 10` - Maximum assets for validation
- `MAX_LEGOS: uint256 = 10` - Maximum Legos for validation

### Inherited State Variables (from modules)
From [LocalGov](../modules/LocalGov.md):
- `governance: address` - Set to UndyHq address
- `tempGovernance: address` - Temporary governance during setup

From [Timelock](../modules/Timelock.md):
- `minTimeLock: uint256` - Minimum timelock period
- `maxTimeLock: uint256` - Maximum timelock period
- Various action tracking variables

From [DeptBasics](../modules/DeptBasics.md):
- `isPaused: bool` - Emergency pause state
- `canMintUndy: bool` - Set to False (no minting capability)

## Constructor

### `__init__`

Initializes the WalletBackpack with governance, temporary governance, and timelock parameters.

```vyper
@deploy
def __init__(
    _undyHq: address,
    _tempGov: address,
    _minTimeLock: uint256,
    _maxTimeLock: uint256,
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | The UndyHq contract address for primary governance |
| `_tempGov` | `address` | Temporary governance address for initial setup |
| `_minTimeLock` | `uint256` | Minimum timelock period for upgrades (blocks) |
| `_maxTimeLock` | `uint256` | Maximum timelock period for upgrades (blocks) |

#### Returns

*The constructor does not return any values.*

#### Access

Called only once during contract deployment.

#### Example Usage
```python
# Deploy WalletBackpack
backpack = boa.load(
    "contracts/registries/WalletBackpack.vy",
    undy_hq.address,
    temp_gov.address,
    100,   # Min timelock (blocks)
    1000   # Max timelock (blocks)
)
```

#### Notes

- All wallet infrastructure components start as `empty(address)`
- Components must be added through time-locked upgrade process
- TimeLock is initialized with max timelock as default

## Infrastructure Management Functions

### Add Pending Component Functions

These functions initiate time-locked upgrades for each wallet infrastructure component:

#### `addPendingKernel`

Initiates upgrade of the wallet execution logic contract.

```vyper
@external
def addPendingKernel(_addr: address) -> bool:
```

#### `addPendingSentinel`

Initiates upgrade of the security validation contract.

```vyper
@external
def addPendingSentinel(_addr: address) -> bool:
```

#### `addPendingHighCommand`

Initiates upgrade of the configuration management contract.

```vyper
@external
def addPendingHighCommand(_addr: address) -> bool:
```

#### `addPendingPaymaster`

Initiates upgrade of the payment processing contract.

```vyper
@external
def addPendingPaymaster(_addr: address) -> bool:
```

#### `addPendingChequeBook`

Initiates upgrade of the cheque management contract.

```vyper
@external
def addPendingChequeBook(_addr: address) -> bool:
```

#### `addPendingMigrator`

Initiates upgrade of the migration tools contract.

```vyper
@external
def addPendingMigrator(_addr: address) -> bool:
```

#### Common Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | The new contract address to set |

#### Common Returns

| Type | Description |
|------|-------------|
| `bool` | `True` if successfully initiated |

#### Common Access

Only callable by addresses that can perform actions (governance and not paused).

#### Common Events Emitted

- `PendingBackpackItemAdded` - Contains component type, address, action ID, confirmation block, and initiator: `log PendingBackpackItemAdded(backpackType=_backpackType, addr=_addr, actionId=actionId, confirmationBlock=confirmationBlock, addedBy=msg.sender)`

#### Example Usage
```python
# Initiate Kernel upgrade
backpack.addPendingKernel(
    new_kernel.address,
    sender=governance
)
```

### Confirm Pending Component Functions

These functions confirm time-locked upgrades after the timelock period:

#### `confirmPendingKernel`
#### `confirmPendingSentinel`
#### `confirmPendingHighCommand`
#### `confirmPendingPaymaster`
#### `confirmPendingChequeBook`
#### `confirmPendingMigrator`

```vyper
@external
def confirmPendingKernel() -> bool:
# ... similar signature for all confirm functions
```

#### Common Returns

| Type | Description |
|------|-------------|
| `bool` | `True` if successfully confirmed, `False` if validation fails |

#### Common Access

Only callable by addresses that can perform actions.

#### Common Events Emitted

- `BackpackItemConfirmed` - Contains component type, address, action ID, and confirmer: `log BackpackItemConfirmed(backpackType=_backpackType, addr=pendingAddr, actionId=pendingUpdate.actionId, confirmedBy=_caller)`

#### Example Usage
```python
# Confirm Kernel upgrade after timelock
success = backpack.confirmPendingKernel(sender=governance)
```

#### Notes

- Re-validates the contract before confirmation
- Automatically cancels if validation fails
- Registers new component with Ledger upon success

### Cancel Pending Component Functions

These functions cancel pending upgrades before confirmation:

#### `cancelPendingKernel`
#### `cancelPendingSentinel`
#### `cancelPendingHighCommand`
#### `cancelPendingPaymaster`
#### `cancelPendingChequeBook`
#### `cancelPendingMigrator`

```vyper
@external
def cancelPendingKernel() -> bool:
# ... similar signature for all cancel functions
```

#### Common Returns

| Type | Description |
|------|-------------|
| `bool` | `True` if successfully cancelled |

#### Common Access

Only callable by addresses that can perform actions.

#### Common Events Emitted

- `PendingBackpackItemCancelled` - Contains component type, address, action ID, and canceller: `log PendingBackpackItemCancelled(backpackType=_backpackType, addr=pendingAddr, actionId=pendingUpdate.actionId, cancelledBy=_caller)`

## Validation Functions

### `canAddBackpackItem`

Validates whether an address can be set for a specific component type.

```vyper
@view
@external
def canAddBackpackItem(_backpackType: BackpackType, _addr: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_backpackType` | `BackpackType` | The component type to validate |
| `_addr` | `address` | The address to validate |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | `True` if the address is valid for the component type |

#### Access

Public view function.

#### Example Usage
```python
# Check if address is valid for Sentinel
can_add = backpack.canAddBackpackItem(
    BackpackType.WALLET_SENTINEL,
    new_sentinel.address
)
```

### `isRegisteredBackpackItem`

Checks if an address is registered as a backpack component in the Ledger.

```vyper
@view
@external
def isRegisteredBackpackItem(_addr: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | The address to check |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | `True` if registered in Ledger |

#### Access

Public view function.

## Internal Functions

### `_addPendingBackpackItem`

Internal logic for initiating component upgrades.

```vyper
@internal
def _addPendingBackpackItem(_backpackType: BackpackType, _addr: address) -> bool:
```

#### Logic Flow

1. Check no pending upgrade exists for component type
2. Validate the new address
3. Initiate TimeLock action
4. Store pending update details
5. Emit event with confirmation block

### `_canAddBackpackItem`

Internal validation logic for component addresses.

```vyper
@view
@internal
def _canAddBackpackItem(_backpackType: BackpackType, _addr: address) -> bool:
```

#### Validation Logic

- **WALLET_KERNEL, WALLET_HIGH_COMMAND, WALLET_PAYMASTER, WALLET_CHEQUE_BOOK, WALLET_MIGRATOR**: Basic address validation (contract, not empty, different from current)
- **WALLET_SENTINEL**: Enhanced validation including interface compliance checks

### `_isValidSentinel`

Specialized validation for Sentinel contracts.

```vyper
@view
@internal
def _isValidSentinel(_addr: address) -> bool:
```

#### Validation Process

1. Basic address validation
2. Interface compliance checks:
   - `canSignerPerformActionWithConfig()` - Manager permission validation
   - `isValidPayeeAndGetData()` - Payee validation logic
   - `checkManagerUsdLimitsAndUpdateData()` - Manager limit checking
   - `isValidChequeAndGetData()` - Cheque validation logic

### `_confirmBackpackItem`

Internal logic for confirming component upgrades.

```vyper
@internal
def _confirmBackpackItem(_backpackType: BackpackType, _caller: address) -> bool:
```

#### Logic Flow

1. Retrieve pending upgrade details
2. Re-validate the address (cancel if invalid)
3. Confirm TimeLock action
4. Clear pending update
5. Set new component address
6. Register with Ledger
7. Emit confirmation event

### `_setBackpackItem`

Internal function to update component addresses.

```vyper
@internal
def _setBackpackItem(_backpackType: BackpackType, _addr: address):
```

#### Operations

1. Update appropriate state variable
2. Register new component with Ledger via `registerBackpackItem()`

### `_cancelPendingBackpackItem`

Internal logic for cancelling pending upgrades.

```vyper
@internal
def _cancelPendingBackpackItem(_backpackType: BackpackType, _caller: address) -> bool:
```

### `_canPerformAction`

Permission validation for infrastructure management.

```vyper
@view
@internal
def _canPerformAction(_caller: address) -> bool:
```

#### Logic

Returns `True` if:
1. Caller has governance permissions (from LocalGov)
2. AND contract is not paused (from DeptBasics)

### `_isValidAddr`

Basic address validation for component contracts.

```vyper
@view
@internal
def _isValidAddr(_addr: address, _prevAddr: address) -> bool:
```

#### Validation Criteria

Returns `True` if:
1. Address is a contract (has code)
2. Address is not empty
3. Address is different from previous/current address

## Interface Requirements

### Sentinel Interface
All Sentinel contracts must implement:
- `canSignerPerformActionWithConfig()` - Manager action validation
- `isValidPayeeAndGetData()` - Payee validation and data management
- `checkManagerUsdLimitsAndUpdateData()` - Manager limit enforcement
- `isValidChequeAndGetData()` - Cheque validation and processing

### Ledger Integration
All confirmed components are automatically registered with the Ledger via:
- `registerBackpackItem(_addr: address)` - Marks component as protocol infrastructure

## Security Considerations

### Time-Lock Protection
- All infrastructure upgrades require timelock confirmation
- Prevents immediate malicious contract replacements
- Allows community review of proposed changes

### Interface Validation
- Sentinel contracts undergo comprehensive interface testing
- Ensures critical wallet security functions are properly implemented
- Prevents deployment of incomplete implementations

### Access Control
- All management functions require governance permissions
- Operations blocked when contract is paused
- No direct user access to infrastructure upgrades

### Re-validation on Confirmation
- Contracts are re-validated at confirmation time
- Automatically cancels if validation fails
- Protects against race conditions or contract changes

## Integration Patterns

### Infrastructure Upgrade Process
```python
# 1. Deploy new component
new_sentinel = deploy_new_sentinel()

# 2. Validate before initiating
can_add = backpack.canAddBackpackItem(
    BackpackType.WALLET_SENTINEL,
    new_sentinel.address
)

# 3. Initiate upgrade
backpack.addPendingSentinel(
    new_sentinel.address,
    sender=governance
)

# 4. Wait for timelock period...

# 5. Confirm upgrade
success = backpack.confirmPendingSentinel(sender=governance)
```

### Emergency Response
```python
# Pause all operations
backpack.pause(True, sender=governance)

# Cancel problematic pending upgrade
backpack.cancelPendingSentinel(sender=governance)

# Resume after resolution
backpack.pause(False, sender=governance)
```

### Component Discovery
```python
# Get current infrastructure addresses
kernel_addr = backpack.kernel()
sentinel_addr = backpack.sentinel()
high_command_addr = backpack.highCommand()
paymaster_addr = backpack.paymaster()
cheque_book_addr = backpack.chequeBook()
migrator_addr = backpack.migrator()

# Check if addresses are registered
for addr in [kernel_addr, sentinel_addr, ...]:
    if addr != ZERO_ADDRESS:
        is_registered = backpack.isRegisteredBackpackItem(addr)
```

### Wallet Component Coordination
```python
# UserWallet queries backpack for infrastructure
class UserWallet:
    def get_infrastructure(self):
        backpack = get_wallet_backpack()
        return {
            'kernel': backpack.kernel(),
            'sentinel': backpack.sentinel(),
            'high_command': backpack.highCommand(),
            'paymaster': backpack.paymaster(),
            'cheque_book': backpack.chequeBook(),
            'migrator': backpack.migrator()
        }
```

## Common Patterns

### Upgrade Lifecycle
1. **Development**: Create new component implementing required interfaces
2. **Validation**: Test `canAddBackpackItem()` before initiating
3. **Initiation**: Call appropriate `addPending*()` function
4. **Review Period**: Wait for timelock confirmation block
5. **Confirmation**: Call corresponding `confirmPending*()` function
6. **Deployment**: Component automatically registered with Ledger

### Rollback Process
```python
# If new component has issues, deploy fixed version
fixed_component = deploy_fixed_component()

# Initiate upgrade to fixed version
backpack.addPendingKernel(
    fixed_component.address,
    sender=governance
)
```

### Batch Component Updates
```python
# Coordinate multiple component upgrades
components = [
    (BackpackType.WALLET_KERNEL, new_kernel),
    (BackpackType.WALLET_SENTINEL, new_sentinel),
    (BackpackType.WALLET_PAYMASTER, new_paymaster)
]

# Initiate all upgrades
for component_type, address in components:
    if component_type == BackpackType.WALLET_KERNEL:
        backpack.addPendingKernel(address)
    elif component_type == BackpackType.WALLET_SENTINEL:
        backpack.addPendingSentinel(address)
    # ... etc

# Confirm all after timelock (in separate transaction(s))
```

## Testing

For comprehensive test examples, see: [`tests/registries/`](../../../tests/registries/) and wallet component tests in [`tests/core/walletBackpack/`](../../../tests/core/walletBackpack/)