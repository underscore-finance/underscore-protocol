# HighCommand Technical Documentation

[📄 View Source Code](../../../contracts/core/walletBackpack/HighCommand.vy)

## Overview

HighCommand is the central manager administration module for user wallets in the Underscore Protocol. As a critical wallet backpack item, it provides comprehensive configuration and control over manager permissions, enabling fine-grained access control for delegated wallet management while maintaining security through time-locked operations and multi-tier validation. Managers configured through HighCommand can execute wallet operations via the [AgentWrapper](../agent/AgentWrapper.md) with signature-based authentication.

**Core Features**:
- **Manager Lifecycle Management**: Add, update, and remove managers with time-delayed activation
- **Granular Permission Control**: Configure specific permissions for yield, trading, debt, liquidity, and transfers
- **Limit Enforcement**: USD value limits per transaction, per period, and lifetime
- **Global Settings**: Default configurations that apply to all managers
- **Security Integration**: MissionControl override capabilities for emergency situations

The contract implements sophisticated validation logic ensuring managers cannot exceed owner-defined boundaries, time-locked activation periods preventing immediate access, flexible configuration options for different management scenarios, and comprehensive event logging for audit trails.

## System Architecture Diagram

```
+-------------------------------------------------------------------------+
|                             HighCommand                                 |
+-------------------------------------------------------------------------+
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                    Manager Permission Tiers                       | |
|  |                                                                   | |
|  |  Owner:                                                          | |
|  |    - Full control over all manager settings                      | |
|  |    - Can add/update/remove managers                              | |
|  |    - Sets global defaults                                         | |
|  |                                                                   | |
|  |  Manager:                                                        | |
|  |    - Limited by configured permissions                           | |
|  |    - Subject to USD value limits                                 | |
|  |    - Can only remove themselves                                   | |
|  |                                                                   | |
|  |  Security (MissionControl):                                       | |
|  |    - Can remove managers in emergencies                           | |
|  |    - Override capability for protection                           | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                  Manager Configuration Flow                       | |
|  |                                                                   | |
|  |  1. Owner calls addManager() with settings                        | |
|  |     ├─> Validates all permissions and limits                     | |
|  |     ├─> Sets activation delay (startBlock)                       | |
|  |     └─> Sets expiry (expiryBlock)                                | |
|  |                                                                   | |
|  |  2. After startBlock reached:                                     | |
|  |     └─> Manager can perform allowed actions                      | |
|  |                                                                   | |
|  |  3. Owner can update settings:                                    | |
|  |     ├─> Modify permissions (immediate)                            | |
|  |     └─> Adjust activation length                                  | |
|  |                                                                   | |
|  |  4. Before expiryBlock:                                           | |
|  |     └─> Manager remains active                                    | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                    Permission Categories                          | |
|  |                                                                   | |
|  |  Limits:                    LegoPerms:                            | |
|  |   • maxUsdValuePerTx        • canManageYield                      | |
|  |   • maxUsdValuePerPeriod    • canBuyAndSell                       | |
|  |   • maxUsdValueLifetime     • canManageDebt                       | |
|  |   • maxNumTxsPerPeriod      • canManageLiq                        | |
|  |   • txCooldownBlocks        • canClaimRewards                     | |
|  |   • failOnZeroPrice         • allowedLegos[]                      | |
|  |                                                                   | |
|  |  WhitelistPerms:           TransferPerms:                        | |
|  |   • canAddPending           • canTransfer                         | |
|  |   • canConfirm              • canCreateCheque                     | |
|  |   • canCancel               • canAddPendingPayee                  | |
|  |   • canRemove               • allowedPayees[]                     | |
|  |                                                                   | |
|  |  Other:                                                           | |
|  |   • allowedAssets[]                                               | |
|  |   • canClaimLoot                                                  | |
|  +-------------------------------------------------------------------+ |
+-------------------------------------------------------------------------+
```

## Constants and Immutables

### Constants
- `LEDGER_ID: uint256 = 1` - Registry ID for Ledger contract
- `MISSION_CONTROL_ID: uint256 = 2` - Registry ID for MissionControl
- `LEGO_BOOK_ID: uint256 = 3` - Registry ID for LegoBook
- `MAX_CONFIG_ASSETS: uint256 = 40` - Maximum allowed assets per manager
- `MAX_CONFIG_LEGOS: uint256 = 25` - Maximum allowed legos per manager
- `MAX_ALLOWED_PAYEES: uint256 = 40` - Maximum allowed payees per manager

### Immutable Variables
- `UNDY_HQ: address` - UndyHq registry address
- `MIN_MANAGER_PERIOD: uint256` - Minimum manager period length
- `MAX_MANAGER_PERIOD: uint256` - Maximum manager period length
- `MAX_START_DELAY: uint256` - Maximum delay before activation
- `MIN_ACTIVATION_LENGTH: uint256` - Minimum active period
- `MAX_ACTIVATION_LENGTH: uint256` - Maximum active period

## Constructor

### `__init__`

Initializes HighCommand with validation bounds for manager configurations.

```vyper
@deploy
def __init__(
    _undyHq: address,
    _minManagerPeriod: uint256,
    _maxManagerPeriod: uint256,
    _minActivationLength: uint256,
    _maxActivationLength: uint256,
    _maxStartDelay: uint256,
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq registry contract address |
| `_minManagerPeriod` | `uint256` | Minimum period length in blocks |
| `_maxManagerPeriod` | `uint256` | Maximum period length in blocks |
| `_minActivationLength` | `uint256` | Minimum activation period |
| `_maxActivationLength` | `uint256` | Maximum activation period |
| `_maxStartDelay` | `uint256` | Maximum start delay in blocks |

#### Access

Called only during deployment

#### Example Usage
```python
high_command = HighCommand.deploy(
    undy_hq.address,
    100,    # Min manager period: 100 blocks
    10000,  # Max manager period: 10000 blocks
    1000,   # Min activation: 1000 blocks
    100000, # Max activation: 100000 blocks
    5000    # Max start delay: 5000 blocks
)
```

## Manager Management Functions

### `addManager`

Adds a new manager with specified permissions and limits.

```vyper
@external
def addManager(
    _userWallet: address,
    _manager: address,
    _limits: wcs.ManagerLimits,
    _legoPerms: wcs.LegoPerms,
    _whitelistPerms: wcs.WhitelistPerms,
    _transferPerms: wcs.TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
    _canClaimLoot: bool,
    _startDelay: uint256 = 0,
    _activationLength: uint256 = 0,
) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet to add manager to |
| `_manager` | `address` | Manager address to add |
| `_limits` | `ManagerLimits` | Transaction and value limits |
| `_legoPerms` | `LegoPerms` | DeFi protocol permissions |
| `_whitelistPerms` | `WhitelistPerms` | Whitelist management permissions |
| `_transferPerms` | `TransferPerms` | Transfer and payee permissions |
| `_allowedAssets` | `DynArray[address, MAX_CONFIG_ASSETS]` | Allowed asset addresses |
| `_canClaimLoot` | `bool` | Can claim protocol rewards |
| `_startDelay` | `uint256` | Blocks before activation (optional) |
| `_activationLength` | `uint256` | Active period length (optional) |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Success status |

#### Access

Only callable by wallet owner

#### Events Emitted

- `ManagerSettingsModified` - Contains user (indexed), manager (indexed), and all configured settings

#### Example Usage
```python
# Define manager limits
limits = ManagerLimits(
    maxUsdValuePerTx=1000 * 10**6,      # $1000 per tx
    maxUsdValuePerPeriod=10000 * 10**6, # $10k per period
    maxUsdValueLifetime=100000 * 10**6, # $100k lifetime
    maxNumTxsPerPeriod=50,
    txCooldownBlocks=10,
    failOnZeroPrice=True
)

# Define lego permissions
lego_perms = LegoPerms(
    canManageYield=True,
    canBuyAndSell=True,
    canManageDebt=False,
    canManageLiq=True,
    canClaimRewards=True,
    allowedLegos=[1, 2, 3]  # Specific lego IDs
)

# Add manager
success = high_command.addManager(
    user_wallet.address,
    manager.address,
    limits,
    lego_perms,
    whitelist_perms,
    transfer_perms,
    [usdc.address, weth.address],  # Allowed assets
    False,  # Cannot claim loot
    100,    # 100 block delay
    10000   # 10000 block activation
)
```

### `updateManager`

Updates existing manager settings (permissions and limits only).

```vyper
@external
def updateManager(
    _userWallet: address,
    _manager: address,
    _limits: wcs.ManagerLimits,
    _legoPerms: wcs.LegoPerms,
    _whitelistPerms: wcs.WhitelistPerms,
    _transferPerms: wcs.TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
    _canClaimLoot: bool,
) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet address |
| `_manager` | `address` | Manager to update |
| `_limits` | `ManagerLimits` | New transaction limits |
| `_legoPerms` | `LegoPerms` | New DeFi permissions |
| `_whitelistPerms` | `WhitelistPerms` | New whitelist permissions |
| `_transferPerms` | `TransferPerms` | New transfer permissions |
| `_allowedAssets` | `DynArray[address, MAX_CONFIG_ASSETS]` | New allowed assets |
| `_canClaimLoot` | `bool` | New loot claim permission |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Success status |

#### Access

Only callable by wallet owner

#### Events Emitted

- `ManagerSettingsModified` - Contains user (indexed), manager (indexed), and all updated settings

#### Notes

- Cannot update startBlock or expiryBlock with this function
- Use `adjustManagerActivationLength` to modify activation period

### `removeManager`

Removes a manager from the wallet.

```vyper
@external
def removeManager(_userWallet: address, _manager: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet address |
| `_manager` | `address` | Manager to remove |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Success status |

#### Access

- Wallet owner
- The manager themselves
- MissionControl authorized addresses

#### Events Emitted

- `ManagerRemoved` - Contains user (indexed) and manager (indexed)

#### Example Usage
```python
# Owner removes manager
success = high_command.removeManager(
    user_wallet.address,
    manager.address,
    sender=owner
)

# Manager removes themselves
success = high_command.removeManager(
    user_wallet.address,
    manager.address,
    sender=manager
)
```

### `adjustManagerActivationLength`

Adjusts the activation period for an existing manager.

```vyper
@external
def adjustManagerActivationLength(
    _userWallet: address,
    _manager: address,
    _activationLength: uint256,
    _shouldResetStartBlock: bool = False,
) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet address |
| `_manager` | `address` | Manager to adjust |
| `_activationLength` | `uint256` | New activation length |
| `_shouldResetStartBlock` | `bool` | Reset start to current block |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Success status |

#### Access

Only callable by wallet owner

#### Events Emitted

- `ManagerActivationLengthAdjusted` - Contains user (indexed), manager (indexed), activationLength, and didRestart

#### Notes

- Can only be called after manager's startBlock
- Automatically resets if manager has expired
- Useful for extending manager access periods

## Global Settings Functions

### `setGlobalManagerSettings`

Sets default settings for all future managers.

```vyper
@external
def setGlobalManagerSettings(
    _userWallet: address,
    _managerPeriod: uint256,
    _startDelay: uint256,
    _activationLength: uint256,
    _canOwnerManage: bool,
    _limits: wcs.ManagerLimits,
    _legoPerms: wcs.LegoPerms,
    _whitelistPerms: wcs.WhitelistPerms,
    _transferPerms: wcs.TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet address |
| `_managerPeriod` | `uint256` | Period length for limits |
| `_startDelay` | `uint256` | Default activation delay |
| `_activationLength` | `uint256` | Default active period |
| `_canOwnerManage` | `bool` | Can owner act as manager |
| `_limits` | `ManagerLimits` | Default transaction limits |
| `_legoPerms` | `LegoPerms` | Default DeFi permissions |
| `_whitelistPerms` | `WhitelistPerms` | Default whitelist permissions |
| `_transferPerms` | `TransferPerms` | Default transfer permissions |
| `_allowedAssets` | `DynArray[address, MAX_CONFIG_ASSETS]` | Default allowed assets |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Success status |

#### Access

Only callable by wallet owner

#### Events Emitted

- `GlobalManagerSettingsModified` - Contains user (indexed) and all global settings

#### Example Usage
```python
# Set permissive global defaults
success = high_command.setGlobalManagerSettings(
    user_wallet.address,
    1000,   # 1000 block periods
    100,    # 100 block start delay
    50000,  # 50000 block activation
    True,   # Owner can manage
    ManagerLimits(...),
    LegoPerms(canManageYield=True, ...),
    WhitelistPerms(canConfirm=True, ...),
    TransferPerms(canTransfer=True, ...),
    []      # No asset restrictions by default
)
```

## Validation Functions

### `isValidNewManager`

Validates settings for a new manager.

```vyper
@view
@external
def isValidNewManager(
    _userWallet: address,
    _manager: address,
    _startDelay: uint256,
    _activationLength: uint256,
    _limits: wcs.ManagerLimits,
    _legoPerms: wcs.LegoPerms,
    _whitelistPerms: wcs.WhitelistPerms,
    _transferPerms: wcs.TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
    _canClaimLoot: bool,
) -> bool:
```

#### Parameters

Same as `addManager`

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if settings are valid |

#### Access

Public view function

### `validateManagerOnUpdate`

Validates settings for updating an existing manager.

```vyper
@view
@external
def validateManagerOnUpdate(
    _userWallet: address,
    _manager: address,
    _limits: wcs.ManagerLimits,
    _legoPerms: wcs.LegoPerms,
    _whitelistPerms: wcs.WhitelistPerms,
    _transferPerms: wcs.TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
    _canClaimLoot: bool,
) -> bool:
```

#### Parameters

Same as `updateManager`

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if settings are valid |

#### Access

Public view function

### `validateGlobalManagerSettings`

Validates global manager settings.

```vyper
@view
@external
def validateGlobalManagerSettings(
    _userWallet: address,
    _managerPeriod: uint256,
    _startDelay: uint256,
    _activationLength: uint256,
    _canOwnerManage: bool,
    _limits: wcs.ManagerLimits,
    _legoPerms: wcs.LegoPerms,
    _whitelistPerms: wcs.WhitelistPerms,
    _transferPerms: wcs.TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
) -> bool:
```

#### Parameters

Same as `setGlobalManagerSettings`

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if settings are valid |

#### Access

Public view function

## Default Creation Functions

### `createDefaultGlobalManagerSettings`

Creates recommended global manager settings.

```vyper
@view
@external
def createDefaultGlobalManagerSettings(
    _managerPeriod: uint256,
    _minTimeLock: uint256,
    _defaultActivationLength: uint256,
) -> wcs.GlobalManagerSettings:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_managerPeriod` | `uint256` | Period length for limits |
| `_minTimeLock` | `uint256` | Minimum time-lock to use |
| `_defaultActivationLength` | `uint256` | Default activation period |

#### Returns

| Type | Description |
|------|-------------|
| `GlobalManagerSettings` | Populated settings struct |

#### Access

Public view function

#### Notes

Creates "happy path" defaults with:
- `canOwnerManage` = True
- All DeFi permissions enabled
- Whitelist confirm/cancel enabled
- Transfer permissions enabled
- No asset/lego/payee restrictions

### `createStarterAgentSettings`

Creates settings for initial agent/manager.

```vyper
@view
@external
def createStarterAgentSettings(_startingAgentActivationLength: uint256) -> wcs.ManagerSettings:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_startingAgentActivationLength` | `uint256` | Activation period length |

#### Returns

| Type | Description |
|------|-------------|
| `ManagerSettings` | Populated settings struct |

#### Access

Public view function

#### Notes

Creates immediate activation settings with:
- `startBlock` = current block (no delay)
- Full permissions similar to defaults
- `canClaimLoot` = True

## Utility Functions

### `getManagerSettingsBundle`

Retrieves comprehensive data about a manager.

```vyper
@view
@external
def getManagerSettingsBundle(_userWallet: address, _manager: address) -> wcs.ManagerSettingsBundle:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet address |
| `_manager` | `address` | Manager address (empty for global) |

#### Returns

| Type | Description |
|------|-------------|
| `ManagerSettingsBundle` | Bundle containing owner, settings, and state |

#### Access

Public view function

#### Bundle Contents
- `owner` - Wallet owner address
- `isManager` - Whether address is a manager
- `timeLock` - Current wallet time-lock
- `walletConfig` - Config contract address
- `legoBook` - LegoBook registry address
- `globalManagerSettings` - Current global settings

## Internal Validation Logic

### Manager Limits Validation

The contract enforces logical consistency in limits:

1. **Value Hierarchy**: 
   - Per-transaction ≤ Per-period ≤ Lifetime
   - Zero values treated as "unlimited"

2. **Cooldown Validation**:
   - Cooldown cannot exceed period length
   - Prevents locking out managers

3. **Period Bounds**:
   - Must be within MIN/MAX_MANAGER_PERIOD

### Lego Permissions Validation

1. **Permission Consistency**:
   - If allowedLegos specified, must have at least one permission
   - Each lego ID must be valid in LegoBook registry

2. **Duplicate Prevention**:
   - No duplicate lego IDs allowed

### Transfer Permissions Validation

1. **Payee Validation**:
   - All payees must be registered in wallet
   - No duplicate payees allowed

2. **Permission Logic**:
   - Must have canTransfer if allowedPayees specified

### Asset Validation

1. **Address Checks**:
   - No empty addresses
   - No duplicates allowed

2. **Array Limits**:
   - Maximum 40 assets per manager

## Security Considerations

### Time-locked Activation
- Managers cannot act immediately after being added
- Minimum delay enforced by global settings or wallet time-lock
- Provides reaction time for unexpected additions

### Permission Boundaries
- Managers cannot exceed owner-defined limits
- All actions validated through UserWalletConfig
- Granular control over specific protocols and assets

### Emergency Controls
- MissionControl can remove compromised managers
- Managers can remove themselves
- Owner maintains ultimate control

### Validation Layers
1. HighCommand validates configuration consistency
2. UserWalletConfig enforces runtime limits
3. UserWallet performs final action validation

## Common Integration Patterns

### Basic Manager Setup
```python
# 1. Set global defaults
high_command.setGlobalManagerSettings(
    wallet.address,
    period=1000,
    start_delay=100,
    activation=10000,
    can_owner_manage=True,
    limits=default_limits,
    lego_perms=default_lego,
    whitelist_perms=default_whitelist,
    transfer_perms=default_transfer,
    allowed_assets=[]
)

# 2. Add specific manager
high_command.addManager(
    wallet.address,
    portfolio_manager.address,
    limits=custom_limits,
    lego_perms=yield_only_perms,
    whitelist_perms=no_whitelist,
    transfer_perms=no_transfer,
    allowed_assets=[usdc.address],
    can_claim_loot=False
)
```

### Temporary Manager Access
```python
# Add with short activation
high_command.addManager(
    wallet.address,
    temp_manager.address,
    limits=strict_limits,
    lego_perms=limited_perms,
    whitelist_perms=read_only,
    transfer_perms=no_transfer,
    allowed_assets=allowed,
    can_claim_loot=False,
    start_delay=10,      # Quick activation
    activation_length=1000  # Short period
)

# Later extend if needed
high_command.adjustManagerActivationLength(
    wallet.address,
    temp_manager.address,
    activation_length=5000,  # Extend
    should_reset_start=False
)
```

### Emergency Manager Removal
```python
# Security team removes compromised manager
high_command.removeManager(
    wallet.address,
    compromised_manager.address,
    sender=security_admin  # MissionControl authorized
)
```

## Testing

For comprehensive test examples, see: [`tests/core/walletBackpack/highCommand/`](../../../tests/core/walletBackpack/highCommand/)