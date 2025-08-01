# SwitchboardBravo Technical Documentation

[📄 View Source Code](../../../contracts/config/SwitchboardBravo.vy)

## Overview

SwitchboardBravo is an operational management contract for the Underscore Protocol, focused on administrative and maintenance functions across the ecosystem. It provides immediate access for security-critical operations and time-locked access for fund recovery, loot management, and user wallet maintenance. This contract serves as the operational arm of the switchboard system, complementing SwitchboardAlpha's configuration management with day-to-day operational controls.

**Core Functions**:
- **Emergency Operations**: Immediate pause/unpause capabilities and security response functions
- **Fund Recovery**: Time-locked recovery of tokens and NFTs from protocol contracts
- **Loot Management**: User loot claiming, adjustment, and deposit point management
- **User Wallet Maintenance**: Asset data updates and ejection mode management
- **Trial Fund Management**: Clawback capabilities for trial fund abuse

Built with flexible access controls, SwitchboardBravo provides both immediate security response capabilities and time-locked administrative functions, ensuring protocol operations can continue smoothly while maintaining security and governance oversight.

## Architecture & Modules

SwitchboardBravo uses the same modular architecture as SwitchboardAlpha with specialized operational focus:

### Addys Module
- **Location**: `contracts/modules/Addys.vy`
- **Purpose**: Provides protocol-wide address lookups for operational access
- **Documentation**: See [Addys Technical Documentation](../modules/Addys.md)
- **Key Features**:
  - Connection to UndyHq for protocol addresses
  - Access to LootDistributor, Hatchery, and other operational contracts
  - Cached address lookups for efficient operations
- **Exported Interface**: All address functions are exposed via `addys.__interface__`

### LocalGov Module
- **Location**: `contracts/modules/LocalGov.vy`
- **Purpose**: Provides governance functionality with temporary governance support
- **Documentation**: See [LocalGov Technical Documentation](../modules/LocalGov.md)
- **Key Features**:
  - Links to UndyHq as primary governance authority
  - Supports temporary governance during deployment
  - Permission validation for operational functions
- **Exported Interface**: All governance functions are exposed via `gov.__interface__`

### TimeLock Module
- **Location**: `contracts/modules/Timelock.vy`
- **Purpose**: Provides time-locked action management for sensitive operations
- **Documentation**: See [Timelock Technical Documentation](../modules/Timelock.md)
- **Key Features**:
  - Configurable timelock periods for fund recovery and sensitive operations
  - Action initiation, confirmation, and cancellation
  - Protection against immediate execution of potentially harmful operations
- **Exported Interface**: All timelock functions are exposed via `timeLock.__interface__`

### Module Initialization
```vyper
initializes: addys
initializes: gov
initializes: timeLock[gov := gov]
```
This initialization pattern ensures proper module dependencies and secure operational management.

## System Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                      SwitchboardBravo Contract                     │
├────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐         ┌──────────────────────────────┐  │
│  │    Addys Module     │         │    LocalGov Module           │  │
│  │                     │         │                              │  │
│  │ • Protocol addrs    │         │ • UndyHq governance          │  │
│  │ • Operational       │         │ • Temp governance support    │  │
│  │   contracts         │         │ • Permission validation      │  │
│  └─────────────────────┘         └──────────────────────────────┘  │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                    TimeLock Module                          │  │
│  │                                                             │  │
│  │ • Action initiation for sensitive operations               │  │
│  │ • Configurable timelock periods                            │  │
│  │ • Confirmation and cancellation management                 │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                 Operational Function Categories               │  │
│  │                                                              │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  │ Emergency Ops   │  │ Fund Recovery   │  │ Loot Management │ │
│  │  │ (Immediate)     │  │ (Time-locked)   │  │ (Mixed Access)  │ │
│  │  │                 │  │                 │  │                 │ │
│  │  │ • Pause/unpause │  │ • Recover funds │  │ • Claim loot    │ │
│  │  │   contracts     │  │ • Recover many  │  │ • Adjust loot   │ │
│  │  │ • Security      │  │   funds         │  │ • Deposit       │ │
│  │  │   response      │  │ • Recover NFTs  │  │   points        │ │
│  │  │                 │  │                 │  │ • Deposit       │ │
│  │  │                 │  │                 │  │   rewards       │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│  │                                                              │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  │ Trial Funds     │  │ User Wallet     │  │ Action          │ │
│  │  │ (Lite Access)   │  │ Maintenance     │  │ Execution       │ │
│  │  │                 │  │ (Lite Access)   │  │ (Governance)    │ │
│  │  │ • Clawback      │  │ • Asset data    │  │ • Execute       │ │
│  │  │   trial funds   │  │   updates       │  │   pending       │ │
│  │  │                 │  │ • Ejection mode │  │ • Cancel        │ │
│  │  │                 │  │                 │  │   pending       │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                                     │
                     ┌───────────────┴───────────────┐
                     ▼                               ▼
        ┌─────────────────────┐          ┌─────────────────────┐
        │ Protocol Contracts  │          │    User Operations  │
        │                     │          │                     │
        │ • LootDistributor   │          │ • UserWallets       │
        │ • Hatchery          │          │ • UserWalletConfig  │
        │ • UndyEcoContracts  │          │ • Loot claiming     │
        │ • Department impls  │          │ • Asset maintenance │
        └─────────────────────┘          └─────────────────────┘
```

## Data Structures

### ActionType Flag
Defines the types of operational actions available:
```vyper
flag ActionType:
    RECOVER_FUNDS                  # Single token recovery
    RECOVER_FUNDS_MANY            # Multiple token recovery
    RECOVER_NFT                   # NFT recovery
    LOOT_ADJUST                   # Loot adjustment
    RECOVER_DEPOSIT_REWARDS       # Deposit reward recovery
    SET_EJECTION_MODE             # User ejection mode
```

### Action Data Structures

#### PauseAction Struct
```vyper
struct PauseAction:
    contractAddr: address    # Contract to pause/unpause
    shouldPause: bool        # Pause state to set
```

#### RecoverFundsAction Struct
```vyper
struct RecoverFundsAction:
    contractAddr: address    # Contract to recover from
    recipient: address       # Address to receive funds
    asset: address          # Token to recover
```

#### RecoverFundsManyAction Struct
```vyper
struct RecoverFundsManyAction:
    contractAddr: address                           # Contract to recover from
    recipient: address                              # Address to receive funds
    assets: DynArray[address, MAX_RECOVER_ASSETS]   # Tokens to recover
```

#### RecoverNftAction Struct
```vyper
struct RecoverNftAction:
    contractAddr: address    # Contract to recover from
    collection: address      # NFT collection contract
    nftTokenId: uint256     # NFT token ID
    recipient: address       # Address to receive NFT
```

#### LootAdjustAction Struct
```vyper
struct LootAdjustAction:
    user: address           # User whose loot to adjust
    asset: address          # Asset being adjusted
    newClaimable: uint256   # New claimable amount
```

#### RecoverDepositRewardsAction Struct
```vyper
struct RecoverDepositRewardsAction:
    lootAddr: address       # LootDistributor address
    recipient: address      # Address to receive rewards
```

#### AssetDataUpdate Struct
```vyper
struct AssetDataUpdate:
    user: address           # User wallet to update
    legoId: uint256        # Lego protocol ID
    asset: address         # Asset to update
    shouldCheckYield: bool  # Whether to check yield
```

#### AllAssetDataUpdate Struct
```vyper
struct AllAssetDataUpdate:
    user: address           # User wallet to update
    shouldCheckYield: bool  # Whether to check yield
```

#### SetEjectionModeAction Struct
```vyper
struct SetEjectionModeAction:
    user: address          # User to configure
    shouldEject: bool      # Ejection mode state
```

## State Variables

### Pending Action Storage
- `actionType: HashMap[uint256, ActionType]` - Maps action ID to operation type
- `pendingPauseActions: HashMap[uint256, PauseAction]` - Pending pause operations
- `pendingRecoverFundsActions: HashMap[uint256, RecoverFundsAction]` - Pending fund recovery
- `pendingRecoverFundsManyActions: HashMap[uint256, RecoverFundsManyAction]` - Pending multi-fund recovery
- `pendingRecoverNftActions: HashMap[uint256, RecoverNftAction]` - Pending NFT recovery
- `pendingLootAdjustActions: HashMap[uint256, LootAdjustAction]` - Pending loot adjustments
- `pendingRecoverDepositRewardsActions: HashMap[uint256, RecoverDepositRewardsAction]` - Pending reward recovery
- `pendingSetEjectionModeActions: HashMap[uint256, SetEjectionModeAction]` - Pending ejection mode changes

### Constants
- `MAX_RECOVER_ASSETS: uint256 = 20` - Maximum assets per recovery operation
- `MAX_USERS: uint256 = 50` - Maximum users per batch operation

## Constructor

### `__init__`

Initializes SwitchboardBravo with governance and timelock parameters.

```vyper
@deploy
def __init__(
    _undyHq: address,
    _tempGov: address,
    _minConfigTimeLock: uint256,
    _maxConfigTimeLock: uint256,
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq contract address for governance |
| `_tempGov` | `address` | Temporary governance address for setup |
| `_minConfigTimeLock` | `uint256` | Minimum timelock period for operations (blocks) |
| `_maxConfigTimeLock` | `uint256` | Maximum timelock period for operations (blocks) |

#### Returns

*The constructor does not return any values.*

#### Access

Called only once during contract deployment.

#### Example Usage
```python
# Deploy SwitchboardBravo
switchboard_bravo = boa.load(
    "contracts/config/SwitchboardBravo.vy",
    undy_hq.address,
    temp_gov.address,
    100,   # Min config timelock (blocks)
    1000   # Max config timelock (blocks)
)
```

## Emergency Operations

### `pause`

Immediately pauses or unpauses a protocol contract for security response.

```vyper
@external
def pause(_contractAddr: address, _shouldPause: bool) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_contractAddr` | `address` | Contract to pause/unpause |
| `_shouldPause` | `bool` | `True` to pause, `False` to unpause |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Always returns `True` on success |

#### Access

- **Pausing**: Governance OR security operators
- **Unpausing**: Governance only

#### Events Emitted

- `PauseExecuted` - Contains contract address and pause state

#### Example Usage
```python
# Emergency pause of a contract
switchboard_bravo.pause(
    problematic_contract.address,
    True,  # Pause
    sender=security_operator
)

# Resume operations (governance only)
switchboard_bravo.pause(
    problematic_contract.address,
    False,  # Unpause
    sender=governance
)
```

#### Notes

- Immediate execution (no timelock)
- Security operators can pause but not unpause
- Uses the reverse permission logic for security

## Fund Recovery Functions

### `recoverFunds`

Initiates time-locked recovery of a single token from a protocol contract.

```vyper
@external
def recoverFunds(_contractAddr: address, _recipient: address, _asset: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_contractAddr` | `address` | Contract to recover funds from |
| `_recipient` | `address` | Address to receive recovered funds |
| `_asset` | `address` | Token contract to recover |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Action ID for tracking the pending recovery |

#### Access

Only callable by governance addresses.

#### Events Emitted

- `PendingRecoverFundsAction` - Contains recovery details and confirmation block

#### Example Usage
```python
# Recover stuck USDC from a contract
action_id = switchboard_bravo.recoverFunds(
    stuck_contract.address,
    treasury.address,
    usdc.address,
    sender=governance
)
```

### `recoverFundsMany`

Initiates time-locked recovery of multiple tokens from a protocol contract.

```vyper
@external
def recoverFundsMany(_contractAddr: address, _recipient: address, _assets: DynArray[address, MAX_RECOVER_ASSETS]) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_contractAddr` | `address` | Contract to recover funds from |
| `_recipient` | `address` | Address to receive all recovered funds |
| `_assets` | `DynArray[address, MAX_RECOVER_ASSETS]` | Array of token contracts to recover (max 20) |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Action ID for tracking |

#### Events Emitted

- `PendingRecoverFundsManyAction` - Contains recovery details and asset count

#### Example Usage
```python
# Recover multiple tokens at once
tokens_to_recover = [usdc.address, dai.address, weth.address]
action_id = switchboard_bravo.recoverFundsMany(
    stuck_contract.address,
    treasury.address,
    tokens_to_recover,
    sender=governance
)
```

### `recoverNft`

Initiates time-locked recovery of an NFT from a protocol contract.

```vyper
@external
def recoverNft(_addr: address, _collection: address, _nftTokenId: uint256, _recipient: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | Contract to recover NFT from |
| `_collection` | `address` | NFT collection contract |
| `_nftTokenId` | `uint256` | NFT token ID to recover |
| `_recipient` | `address` | Address to receive the NFT |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Action ID for tracking |

#### Events Emitted

- `PendingRecoverNftAction` - Contains NFT recovery details

## Trial Fund Management

### `clawBackTrialFunds`

Immediately claws back trial funds from users (typically for abuse prevention).

```vyper
@external
def clawBackTrialFunds(_users: DynArray[address, MAX_USERS]) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_users` | `DynArray[address, MAX_USERS]` | Array of user addresses (max 50) |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Always returns `True` on success |

#### Access

Governance OR security operators (lite access).

#### Events Emitted

- `ClawbackTrialFundsExecuted` - Contains number of users processed

#### Example Usage
```python
# Clawback trial funds from abusive users
abusive_users = [user1.address, user2.address, user3.address]
switchboard_bravo.clawBackTrialFunds(
    abusive_users,
    sender=security_operator
)
```

#### Notes

- Immediate execution (no timelock)
- Only processes valid user wallets
- Skips invalid addresses silently

## Loot Management Functions

### `claimLootForUser`

Claims all available loot for a specific user.

```vyper
@external
def claimLootForUser(_user: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User address to claim loot for |

#### Access

Governance OR security operators (lite access).

#### Events Emitted

- `LootClaimedForUser` - Contains user and caller information

### `claimLootForManyUsers`

Claims loot for multiple users in a single transaction.

```vyper
@external
def claimLootForManyUsers(_users: DynArray[address, MAX_USERS]):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_users` | `DynArray[address, MAX_USERS]` | Array of user addresses (max 50) |

#### Events Emitted

- `LootClaimedForManyUsers` - Contains user count and caller information

### `adjustLoot`

Initiates time-locked adjustment of a user's loot balance.

```vyper
@external
def adjustLoot(_user: address, _asset: address, _newClaimable: uint256) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User whose loot to adjust |
| `_asset` | `address` | Asset being adjusted |
| `_newClaimable` | `uint256` | New claimable amount |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Action ID for tracking |

#### Access

Only callable by governance addresses.

#### Events Emitted

- `PendingLootAdjustAction` - Contains adjustment details

#### Example Usage
```python
# Adjust user's USDC loot
action_id = switchboard_bravo.adjustLoot(
    user.address,
    usdc.address,
    1000 * 10**6,  # 1000 USDC
    sender=governance
)
```

### `recoverDepositRewards`

Initiates time-locked recovery of deposit rewards from LootDistributor.

```vyper
@external
def recoverDepositRewards(_lootAddr: address, _recipient: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_lootAddr` | `address` | LootDistributor contract address |
| `_recipient` | `address` | Address to receive rewards |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Action ID for tracking |

#### Access

Only callable by governance addresses.

### `updateDepositPoints`

Updates deposit points for multiple users.

```vyper
@external
def updateDepositPoints(_users: DynArray[address, MAX_USERS]):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_users` | `DynArray[address, MAX_USERS]` | Array of user addresses (max 50) |

#### Access

Governance OR security operators (lite access).

#### Events Emitted

- `DepositPointsUpdated` - Contains user count and caller information

## User Wallet Maintenance Functions

### `updateAssetData`

Updates asset data for specific user wallets.

```vyper
@external
def updateAssetData(_bundles: DynArray[AssetDataUpdate, MAX_USERS]):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_bundles` | `DynArray[AssetDataUpdate, MAX_USERS]` | Array of asset update specifications |

#### Access

Governance OR security operators (lite access).

#### Events Emitted

- `AssetDataUpdated` - Contains number of users updated and caller

#### Example Usage
```python
# Update asset data for multiple users
updates = [
    AssetDataUpdate(
        user=user1.address,
        legoId=1,
        asset=usdc.address,
        shouldCheckYield=True
    ),
    AssetDataUpdate(
        user=user2.address,
        legoId=2,
        asset=dai.address,
        shouldCheckYield=False
    )
]
switchboard_bravo.updateAssetData(updates, sender=governance)
```

### `updateAllAssetData`

Updates all asset data for specified user wallets.

```vyper
@external
def updateAllAssetData(_bundles: DynArray[AllAssetDataUpdate, MAX_USERS]):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_bundles` | `DynArray[AllAssetDataUpdate, MAX_USERS]` | Array of full update specifications |

#### Access

Governance OR security operators (lite access).

#### Events Emitted

- `AllAssetDataUpdated` - Contains number of users updated and caller

### `setEjectionMode`

Initiates time-locked setting of ejection mode for a user wallet.

```vyper
@external
def setEjectionMode(_user: address, _shouldEject: bool) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User wallet to configure |
| `_shouldEject` | `bool` | Whether to enable ejection mode |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Action ID for tracking |

#### Access

Only callable by governance addresses.

#### Events Emitted

- `PendingSetEjectionModeAction` - Contains user and ejection mode details

#### Notes

- Time-locked operation for security
- Automatically updates deposit points on execution

## Action Execution Functions

### `executePendingAction`

Executes a time-locked operation after confirmation period.

```vyper
@external
def executePendingAction(_aid: uint256) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_aid` | `uint256` | Action ID to execute |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | `True` if successfully executed, `False` if failed |

#### Access

Only callable by governance addresses.

#### Logic Flow

1. Validate timelock confirmation
2. If expired, automatically cancel action
3. Route to appropriate execution handler based on action type:
   - **RECOVER_FUNDS**: Execute single token recovery
   - **RECOVER_FUNDS_MANY**: Execute multi-token recovery
   - **RECOVER_NFT**: Execute NFT recovery
   - **LOOT_ADJUST**: Adjust user loot balance
   - **RECOVER_DEPOSIT_REWARDS**: Recover deposit rewards
   - **SET_EJECTION_MODE**: Set ejection mode and update deposit points
4. Emit appropriate execution event
5. Clean up pending action data

#### Example Usage
```python
# Execute pending action after timelock
success = switchboard_bravo.executePendingAction(
    action_id,
    sender=governance
)
```

### `cancelPendingAction`

Cancels a pending operation before execution.

```vyper
@external
def cancelPendingAction(_aid: uint256) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_aid` | `uint256` | Action ID to cancel |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | `True` if successfully cancelled |

#### Access

Only callable by governance addresses.

## Internal Helper Functions

### `_hasPerms`

Determines access permissions based on operation type.

```vyper
@view
@internal
def _hasPerms(_caller: address, _isLiteAccess: bool) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_caller` | `address` | Address attempting the operation |
| `_isLiteAccess` | `bool` | Whether operation allows lite access |

#### Logic

- **Governance**: Always has full access
- **Security operators**: Has access only to lite access operations
- **Others**: No access

#### Lite Access Operations
Functions that allow security operators:
- `clawBackTrialFunds()`
- `claimLootForUser()` / `claimLootForManyUsers()`
- `updateDepositPoints()`
- `updateAssetData()` / `updateAllAssetData()`

## Security Considerations

### Access Control Levels
1. **Governance Only**: Fund recovery, loot adjustment, ejection mode
2. **Lite Access**: Trial funds, loot claiming, maintenance operations
3. **Immediate vs Time-locked**: Emergency operations vs sensitive operations

### Emergency Response
- Immediate pause capabilities for security incidents
- Security operators can disable but not enable operations
- Trial fund clawback for abuse prevention

### Time-Lock Protection
- All fund recovery operations require timelock confirmation
- Loot adjustments protected against immediate manipulation
- User ejection mode changes require governance review

## Integration Patterns

### Emergency Response Workflow
```python
# Security incident detected
# 1. Immediate pause
switchboard_bravo.pause(
    affected_contract.address,
    True,  # Pause
    sender=security_operator
)

# 2. Clawback trial funds if needed
switchboard_bravo.clawBackTrialFunds(
    affected_users,
    sender=security_operator
)

# 3. After resolution, governance unpauses
switchboard_bravo.pause(
    affected_contract.address,
    False,  # Unpause
    sender=governance
)
```

### Fund Recovery Process
```python
# 1. Initiate recovery
action_id = switchboard_bravo.recoverFunds(
    contract_with_stuck_funds.address,
    treasury.address,
    stuck_token.address,
    sender=governance
)

# 2. Wait for timelock period...

# 3. Execute recovery
success = switchboard_bravo.executePendingAction(
    action_id,
    sender=governance
)
```

### Maintenance Operations
```python
# Batch loot claiming
users_needing_claims = [user1, user2, user3]
switchboard_bravo.claimLootForManyUsers(
    users_needing_claims,
    sender=security_operator
)

# Asset data maintenance
asset_updates = [
    AssetDataUpdate(user1, lego_id, asset, True),
    AssetDataUpdate(user2, lego_id, asset, False)
]
switchboard_bravo.updateAssetData(
    asset_updates,
    sender=security_operator
)
```

## Common Patterns

### Security Operator Workflow
```python
# Daily maintenance tasks (lite access)
switchboard_bravo.claimLootForManyUsers(users_list)
switchboard_bravo.updateDepositPoints(users_list)
switchboard_bravo.updateAssetData(asset_updates)

# Emergency response (lite access)
switchboard_bravo.pause(contract, True)  # Can pause
switchboard_bravo.clawBackTrialFunds(abusive_users)
```

### Governance Workflow
```python
# Full operational control
# Time-locked operations
fund_recovery_id = switchboard_bravo.recoverFunds(...)
loot_adjust_id = switchboard_bravo.adjustLoot(...)

# Immediate operations
switchboard_bravo.pause(contract, False)  # Can unpause
switchboard_bravo.updateAssetData(updates)
```

## Testing

For comprehensive test examples, see: [`tests/config/`](../../../tests/config/)