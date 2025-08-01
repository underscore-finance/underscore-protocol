# Ledger Technical Documentation

[📄 View Source Code](../../../contracts/data/Ledger.vy)

## Overview

Ledger is the central data storage contract for the Underscore Protocol. As a Department contract, it maintains critical protocol state including user wallet registrations, agent tracking, deposit points for rewards, vault token configurations, and ambassador relationships. It serves as the single source of truth for protocol entities and their relationships.

**Core Features**:
- **User Wallet Registry**: Track all user wallets with indexed access
- **Points System**: Maintain deposit points for rewards distribution
- **Vault Token Registry**: Store configuration for yield-bearing assets
- **Agent Management**: Track autonomous agents with indexed storage
- **Ambassador Tracking**: Maintain referral relationships

The contract implements efficient storage patterns including indexed mappings for O(1) lookups, dual-direction mappings for iteration, structured data storage for complex types, and strict access control for data integrity.

## System Architecture Diagram

```
+-------------------------------------------------------------------------+
|                                Ledger                                   |
+-------------------------------------------------------------------------+
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                       Storage Architecture                         | |
|  |                                                                   | |
|  |  User Wallets (Indexed):                                          | |
|  |    • userWallets[index] → address                                 | |
|  |    • indexOfUserWallet[address] → index                           | |
|  |    • Enables iteration and O(1) lookup                            | |
|  |    • Index starts at 1 (0 = not registered)                       | |
|  |                                                                   | |
|  |  Points System:                                                    | |
|  |    • userPoints[user] → PointsData                                | |
|  |    • globalPoints → PointsData                                    | |
|  |    • Tracks USD value, points, and last update                    | |
|  |                                                                   | |
|  |  Vault Tokens:                                                     | |
|  |    • vaultTokens[address] → VaultToken                            | |
|  |    • Stores protocol ID, underlying, decimals                      | |
|  |    • Identifies rebasing vs non-rebasing                          | |
|  |                                                                   | |
|  |  Agents (Indexed):                                                 | |
|  |    • agents[index] → address                                       | |
|  |    • indexOfAgent[address] → index                                 | |
|  |    • Similar structure to user wallets                            | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                        Access Control                              | |
|  |                                                                   | |
|  |  Hatchery Only:                                                   | |
|  |    • createUserWallet - Register new wallets                      | |
|  |    • createAgent - Register new agents                            | |
|  |                                                                   | |
|  |  LootDistributor Only:                                            | |
|  |    • setUserPoints - Update user points                           | |
|  |    • setGlobalPoints - Update global points                       | |
|  |    • setUserAndGlobalPoints - Atomic update                       | |
|  |                                                                   | |
|  |  LegoBook Only:                                                    | |
|  |    • setVaultToken - Register yield assets                        | |
|  |                                                                   | |
|  |  WalletBackpack Only:                                             | |
|  |    • registerBackpackItem - Mark as valid item                    | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                      Indexing Strategy                             | |
|  |                                                                   | |
|  |  Benefits of 1-based indexing:                                     | |
|  |    • 0 index = not registered (cheap validation)                   | |
|  |    • Supports up to 2^256-1 entities                              | |
|  |    • Efficient iteration from 1 to numEntities                     | |
|  |    • No special handling for first element                         | |
|  |                                                                   | |
|  |  Example: userWallets                                              | |
|  |    • numUserWallets = 1 initially                                  | |
|  |    • First wallet gets index 1                                     | |
|  |    • indexOfUserWallet[unregistered] = 0                           | |
|  +-------------------------------------------------------------------+ |
+-------------------------------------------------------------------------+
```

## Module Integration

Ledger implements the Department interface and integrates:
- `Addys` module for address registry management
- `DeptBasics` module for pause functionality

## Data Structures

### PointsData
```vyper
struct PointsData:
    usdValue: uint256       # Current USD value of deposits
    depositPoints: uint256  # Accumulated points
    lastUpdate: uint256     # Last update block
```

### VaultToken
```vyper
struct VaultToken:
    legoId: uint256         # Protocol integration ID
    underlyingAsset: address # Underlying asset address
    decimals: uint256       # Token decimals
    isRebasing: bool        # Whether vault is rebasing
```

## State Variables

### Points Storage
- `userPoints: HashMap[address, PointsData]` - User deposit points data
- `globalPoints: PointsData` - Global points accumulator

### User Wallet Storage
- `userWallets: HashMap[uint256, address]` - Index to wallet mapping
- `indexOfUserWallet: HashMap[address, uint256]` - Wallet to index mapping
- `numUserWallets: uint256` - Total wallets + 1

### Ambassador Storage
- `ambassadors: HashMap[address, address]` - User to ambassador mapping

### Agent Storage
- `agents: HashMap[uint256, address]` - Index to agent mapping
- `indexOfAgent: HashMap[address, uint256]` - Agent to index mapping
- `numAgents: uint256` - Total agents + 1

### Vault Token Storage
- `vaultTokens: HashMap[address, VaultToken]` - Vault token configurations

### Backpack Item Storage
- `isRegisteredBackpackItem: HashMap[address, bool]` - Valid backpack items

## Constructor

### `__init__`

Initializes Ledger with registry integration.

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
ledger = Ledger.deploy(
    undy_hq.address
)
```

#### Notes

- Initializes numUserWallets and numAgents to 1
- Sets up Department module integration
- No minting capability enabled

## User Wallet Functions

### `createUserWallet`

Registers a new user wallet in the protocol.

```vyper
@external
def createUserWallet(_user: address, _ambassador: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User wallet address to register |
| `_ambassador` | `address` | Ambassador wallet (optional) |

#### Access

Only callable by Hatchery contract

#### Example Usage
```python
# Called by Hatchery during wallet creation
ledger.createUserWallet(
    new_wallet_address,
    ambassador_wallet_address
)
```

#### Notes

- Assigns next sequential index
- Sets ambassador if provided
- Fails if paused

### `getNumUserWallets`

Gets the total number of registered user wallets.

```vyper
@view
@external
def getNumUserWallets() -> uint256:
```

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Number of registered wallets |

#### Access

Public view function

#### Example Usage
```python
# Get total wallet count
total_wallets = ledger.getNumUserWallets()
print(f"Protocol has {total_wallets} user wallets")
```

### `isUserWallet`

Checks if an address is a registered user wallet.

```vyper
@view
@external
def isUserWallet(_user: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | Address to check |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if registered user wallet |

#### Access

Public view function

#### Example Usage
```python
# Validate user wallet
if ledger.isUserWallet(address):
    # Proceed with wallet operations
    pass
```

## Deposit Points Functions

### `setUserPoints`

Updates deposit points for a user.

```vyper
@external
def setUserPoints(_user: address, _data: PointsData):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User address |
| `_data` | `PointsData` | Points data to set |

#### Access

Only callable by LootDistributor

### `setGlobalPoints`

Updates global deposit points.

```vyper
@external
def setGlobalPoints(_data: PointsData):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_data` | `PointsData` | Global points data |

#### Access

Only callable by LootDistributor

### `setUserAndGlobalPoints`

Atomically updates both user and global points.

```vyper
@external
def setUserAndGlobalPoints(_user: address, _userData: PointsData, _globalData: PointsData):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User address |
| `_userData` | `PointsData` | User points data |
| `_globalData` | `PointsData` | Global points data |

#### Access

Only callable by LootDistributor

#### Example Usage
```python
# Atomic update from LootDistributor
ledger.setUserAndGlobalPoints(
    user_address,
    user_points_data,
    global_points_data
)
```

### `getLastTotalUsdValue`

Gets the last recorded USD value for a user.

```vyper
@view
@external
def getLastTotalUsdValue(_user: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User address |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Last total USD value |

#### Access

Public view function

### `getUserAndGlobalPoints`

Gets both user and global points data.

```vyper
@view
@external
def getUserAndGlobalPoints(_user: address) -> (PointsData, PointsData):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User address |

#### Returns

| Type | Description |
|------|-------------|
| `PointsData` | User points data |
| `PointsData` | Global points data |

#### Access

Public view function

## Vault Token Functions

### `isRegisteredVaultToken`

Checks if an address is a registered vault token.

```vyper
@view
@external
def isRegisteredVaultToken(_vaultToken: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | Token address to check |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if registered vault token |

#### Access

Public view function

### `setVaultToken`

Registers or updates a vault token configuration.

```vyper
@external
def setVaultToken(
    _vaultToken: address,
    _legoId: uint256,
    _underlyingAsset: address,
    _decimals: uint256,
    _isRebasing: bool,
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | Vault token address |
| `_legoId` | `uint256` | Protocol integration ID |
| `_underlyingAsset` | `address` | Underlying asset address |
| `_decimals` | `uint256` | Token decimals |
| `_isRebasing` | `bool` | Whether vault is rebasing |

#### Access

Only callable by LegoBook

#### Example Usage
```python
# Register new vault token
ledger.setVaultToken(
    vault_token.address,
    lego_id,
    underlying.address,
    18,
    False  # non-rebasing
)
```

## Backpack Item Functions

### `registerBackpackItem`

Registers an address as a valid backpack item.

```vyper
@external
def registerBackpackItem(_addr: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | Backpack item address |

#### Access

Only callable by WalletBackpack

## Agent Functions

### `createAgent`

Registers a new agent in the protocol.

```vyper
@external
def createAgent(_agent: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_agent` | `address` | Agent address to register |

#### Access

Only callable by Hatchery

### `getNumAgents`

Gets the total number of registered agents.

```vyper
@view
@external
def getNumAgents() -> uint256:
```

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Number of registered agents |

#### Access

Public view function

### `isAgent`

Checks if an address is a registered agent.

```vyper
@view
@external
def isAgent(_agent: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_agent` | `address` | Address to check |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if registered agent |

#### Access

Public view function

## Security Considerations

### Access Control
- Strict function-level permissions
- Only authorized contracts can modify state
- Department-based access control

### Data Integrity
- Indexed storage prevents duplicates
- Atomic updates for related data
- Pause protection on all write functions

### Storage Efficiency
- Dual mappings for O(1) operations
- Structured data for complex types
- Efficient iteration patterns

## Common Integration Patterns

### Wallet Registration Check
```python
# Before wallet operations
if not ledger.isUserWallet(wallet_address):
    raise Exception("Not a registered wallet")

# Get wallet by index
wallet_count = ledger.getNumUserWallets()
for i in range(1, wallet_count + 1):
    wallet = ledger.userWallets(i)
    # Process wallet
```

### Points Management
```python
# Get current points state
user_points, global_points = ledger.getUserAndGlobalPoints(user)

# Calculate new points
new_user_points = calculate_points(user_points)
new_global_points = calculate_global(global_points)

# Update atomically (from LootDistributor)
ledger.setUserAndGlobalPoints(
    user,
    new_user_points,
    new_global_points
)
```

### Vault Token Verification
```python
# Check if token is yield-bearing
if ledger.isRegisteredVaultToken(token):
    vault_info = ledger.vaultTokens(token)
    if vault_info.isRebasing:
        # Handle rebasing vault
        pass
    else:
        # Handle non-rebasing vault
        pass
```

### Ambassador Tracking
```python
# Get user's ambassador
ambassador = ledger.ambassadors(user_wallet)
if ambassador != ZERO_ADDRESS:
    # Calculate ambassador rewards
    pass
```

## Testing

For comprehensive test examples, see: [`tests/core/data/test_ledger.py`](../../../tests/core/data/test_ledger.py)