# Hatchery Technical Documentation

[📄 View Source Code](../../../contracts/core/Hatchery.vy)

## Overview

Hatchery is the wallet and agent creation factory for the Underscore Protocol. As a Department contract, it manages the deployment of new user wallets and agent contracts with configurable templates, default settings, and trial fund distribution, serving as the entry point for new users joining the protocol ecosystem.

**Core Features**:
- **User Wallet Creation**: Deploy wallet and configuration contracts with customizable settings
- **Agent Creation**: Deploy autonomous agent contracts for programmatic wallet management
- **Trial Fund Management**: Distribute and recover trial funds for new users
- **Template System**: Flexible blueprint-based deployment for upgradeable patterns
- **Default Configuration**: Automatic setup of manager, payee, and cheque settings

The contract implements sophisticated creation logic including ambassador referral tracking, group-based organization, configurable time-locks and limits, trial fund recovery mechanisms, and permission-based creation controls.

## System Architecture Diagram

```
+-------------------------------------------------------------------------+
|                                Hatchery                                 |
+-------------------------------------------------------------------------+
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                    Wallet Creation Flow                           | |
|  |                                                                   | |
|  |  1. Validation:                                                   | |
|  |     ├─> Check creator permissions                                 | |
|  |     ├─> Verify template addresses                                | |
|  |     ├─> Ensure owner ≠ starting agent                            | |
|  |     └─> Check global wallet limits                               | |
|  |                                                                   | |
|  |  2. Configuration Setup:                                          | |
|  |     ├─> Create default manager settings                           | |
|  |     ├─> Create default payee settings                             | |
|  |     ├─> Create default cheque settings                            | |
|  |     └─> Setup starting agent (if configured)                      | |
|  |                                                                   | |
|  |  3. Contract Deployment:                                          | |
|  |     ├─> Deploy UserWalletConfig from template                     | |
|  |     ├─> Deploy UserWallet from template                           | |
|  |     ├─> Link wallet to configuration                              | |
|  |     └─> Register in Ledger                                       | |
|  |                                                                   | |
|  |  4. Post-Creation:                                                | |
|  |     ├─> Transfer trial funds (if applicable)                      | |
|  |     └─> Set ambassador relationship                               | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                     Trial Fund Management                          | |
|  |                                                                   | |
|  |  Distribution:                                                     | |
|  |    • Check balance availability                                   | |
|  |    • Transfer after wallet creation                               | |
|  |    • Track in wallet configuration                                | |
|  |                                                                   | |
|  |  Recovery Process:                                                | |
|  |    1. Check direct balance                                        | |
|  |    2. Search yield vaults with matching underlying                | |
|  |    3. Withdraw from vaults to recover funds                       | |
|  |    4. Remove trial fund tracking                                  | |
|  |    5. Deregister empty assets                                     | |
|  |                                                                   | |
|  |  Validation:                                                      | |
|  |    • 99% threshold for "still has funds"                          | |
|  |    • 101% target for recovery (1% buffer)                         | |
|  |    • Eligible vault verification                                  | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                      Permission Structure                          | |
|  |                                                                   | |
|  |  Creation Permissions:                                             | |
|  |    • Switchboard: Always allowed                                  | |
|  |    • Public: If isCreatorAllowed = true                           | |
|  |    • Limits: numUserWalletsAllowed / numAgentsAllowed             | |
|  |                                                                   | |
|  |  Trial Fund Clawback:                                             | |
|  |    • Owner: Can recover own funds                                 | |
|  |    • Security: MissionControl authorized                          | |
|  |    • Switchboard: Administrative access                           | |
|  |    • Backpack Items: Registered modules                           | |
|  +-------------------------------------------------------------------+ |
+-------------------------------------------------------------------------+
```

## Module Integration

Hatchery implements the Department interface and integrates:
- `Addys` module for address registry management
- `DeptBasics` module for pause functionality

## Constants

- `HUNDRED_PERCENT: uint256 = 100_00` - 100% in basis points
- `MAX_DEREGISTER_ASSETS: uint256 = 25` - Maximum assets to deregister during recovery

## Immutable Variables

- `WETH: address` - Wrapped ETH address
- `ETH: address` - ETH placeholder address

## Constructor

### `__init__`

Initializes Hatchery with registry and token addresses.

```vyper
@deploy
def __init__(_undyHq: address, _wethAddr: address, _ethAddr: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq registry contract address |
| `_wethAddr` | `address` | WETH token address |
| `_ethAddr` | `address` | ETH placeholder address |

#### Access

Called only during deployment

#### Example Usage
```python
hatchery = Hatchery.deploy(
    undy_hq.address,
    weth.address,
    "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"  # ETH placeholder
)
```

## Wallet Creation Functions

### `createUserWallet`

Creates a new user wallet with configuration.

```vyper
@external
def createUserWallet(
    _owner: address = msg.sender,
    _ambassador: address = empty(address),
    _shouldUseTrialFunds: bool = True,
    _groupId: uint256 = 1,
) -> address:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_owner` | `address` | Wallet owner address (defaults to sender) |
| `_ambassador` | `address` | Ambassador wallet for referral |
| `_shouldUseTrialFunds` | `bool` | Whether to distribute trial funds |
| `_groupId` | `uint256` | Group identifier for organization |

#### Returns

| Type | Description |
|------|-------------|
| `address` | Deployed wallet address |

#### Access

- Public (if `isCreatorAllowed` in config)
- Switchboard addresses

#### Events Emitted

- `UserWalletCreated` - Contains mainAddr (indexed), configAddr (indexed), owner (indexed), agent, ambassador, creator, trialFundsAsset, trialFundsAmount, and groupId

#### Example Usage
```python
# Create wallet with defaults
wallet = hatchery.createUserWallet(
    sender=user
)

# Create with specific settings
wallet = hatchery.createUserWallet(
    _owner=user.address,
    _ambassador=referrer_wallet.address,
    _shouldUseTrialFunds=True,
    _groupId=5,
    sender=creator
)
```

#### Notes

- Deploys both UserWallet and UserWalletConfig contracts
- Sets up default manager, payee, and cheque settings
- Configures starting agent if specified
- Transfers trial funds after creation
- Owner cannot be the starting agent

### `createAgent`

Creates a new agent contract.

```vyper
@external
def createAgent(_owner: address = msg.sender, _groupId: uint256 = 1) -> address:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_owner` | `address` | Agent owner address (defaults to sender) |
| `_groupId` | `uint256` | Group identifier |

#### Returns

| Type | Description |
|------|-------------|
| `address` | Deployed agent address |

#### Access

- Public (if `isCreatorAllowed` in config)
- Switchboard addresses

#### Events Emitted

- `AgentCreated` - Contains agent (indexed), owner (indexed), creator (indexed), and groupId

#### Example Usage
```python
# Create agent for self
agent = hatchery.createAgent(
    sender=user
)

# Create agent for another user
agent = hatchery.createAgent(
    _owner=user.address,
    _groupId=10,
    sender=creator
)
```

## Trial Fund Functions

### `clawBackTrialFunds`

Recovers trial funds from a user wallet.

```vyper
@external
def clawBackTrialFunds(_user: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User wallet to recover funds from |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Amount of trial funds recovered |

#### Access

- Wallet owner
- MissionControl authorized addresses
- Switchboard addresses
- Registered backpack items

#### Example Usage
```python
# Recover trial funds before migration
amount_recovered = hatchery.clawBackTrialFunds(
    user_wallet.address,
    sender=owner
)
```

#### Recovery Process

1. **Direct Recovery**: If wallet has sufficient balance, remove directly
2. **Vault Search**: Find yield vaults with trial asset as underlying
3. **Withdrawal**: Calculate and withdraw needed vault tokens
4. **Cleanup**: Remove trial fund tracking and deregister empty assets

### `doesWalletStillHaveTrialFunds`

Checks if wallet still has trial funds.

```vyper
@view
@external
def doesWalletStillHaveTrialFunds(_user: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User wallet to check |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if wallet still has ≥99% of trial funds |

#### Access

Public view function

#### Example Usage
```python
# Check before allowing certain operations
if hatchery.doesWalletStillHaveTrialFunds(wallet):
    print("Cannot perform operation with trial funds")
```

### `doesWalletStillHaveTrialFundsWithAddys`

Checks trial funds with custom registry addresses.

```vyper
@view
@external
def doesWalletStillHaveTrialFundsWithAddys(
    _user: address,
    _walletConfig: address,
    _missionControl: address,
    _legoBook: address,
    _appraiser: address,
    _ledger: address,
) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User wallet address |
| `_walletConfig` | `address` | Wallet configuration address |
| `_missionControl` | `address` | MissionControl address |
| `_legoBook` | `address` | LegoBook address |
| `_appraiser` | `address` | Appraiser address |
| `_ledger` | `address` | Ledger address |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if wallet still has trial funds |

#### Access

Public view function

### `canClawbackTrialFunds`

Checks if caller can clawback trial funds.

```vyper
@view
@external
def canClawbackTrialFunds(_user: address, _caller: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User wallet with trial funds |
| `_caller` | `address` | Address attempting clawback |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if caller has permission |

#### Access

Public view function

## Utility Functions

### `getAssetUsdValueConfig`

Gets asset configuration for USD value calculations.

```vyper
@view
@external
def getAssetUsdValueConfig(_asset: address) -> AssetUsdValueConfig:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Asset to get configuration for |

#### Returns

| Type | Description |
|------|-------------|
| `AssetUsdValueConfig` | Asset configuration struct |

#### Access

Public view function

#### Returned Struct Contents
- `legoId` - Protocol integration ID
- `legoAddr` - Protocol integration address
- `decimals` - Asset decimals
- `staleBlocks` - Price staleness threshold
- `isYieldAsset` - Whether asset is yield-bearing
- `underlyingAsset` - Underlying asset for vaults

## Configuration Structures

### UserWalletCreationConfig

Configuration for wallet creation:
- `numUserWalletsAllowed` - Global wallet limit (0 = unlimited)
- `isCreatorAllowed` - Whether public creation allowed
- `walletTemplate` - UserWallet blueprint address
- `configTemplate` - UserWalletConfig blueprint address
- `startingAgent` - Default agent for new wallets
- `startingAgentActivationLength` - Agent active period
- `managerPeriod` - Manager tracking period
- `managerActivationLength` - Manager active period
- `payeePeriod` - Payee tracking period
- `payeeActivationLength` - Payee active period
- `chequeMaxNumActiveCheques` - Maximum active cheques
- `chequeInstantUsdThreshold` - Instant payment threshold
- `chequePeriodLength` - Cheque tracking period
- `chequeExpensiveDelayBlocks` - Delay for high-value cheques
- `chequeDefaultExpiryBlocks` - Default cheque expiry
- `trialAsset` - Trial fund token address
- `trialAmount` - Trial fund amount
- `minKeyActionTimeLock` - Minimum time-lock
- `maxKeyActionTimeLock` - Maximum time-lock

### AgentCreationConfig

Configuration for agent creation:
- `agentTemplate` - Agent blueprint address
- `numAgentsAllowed` - Global agent limit (0 = unlimited)
- `isCreatorAllowed` - Whether public creation allowed
- `minTimeLock` - Minimum agent time-lock
- `maxTimeLock` - Maximum agent time-lock

## Security Considerations

### Creation Controls
- Template validation prevents empty addresses
- Global limits prevent spam
- Starting agent cannot be owner
- Group IDs for organizational boundaries

### Trial Fund Security
- 99% threshold allows for rounding errors
- 101% recovery target ensures complete removal
- Multiple recovery methods for various scenarios
- Automatic asset deregistration

### Permission Hierarchy
- Switchboard has administrative access
- Public creation configurable per deployment
- Owner controls over their own funds
- Security override via MissionControl

### Template System
- Blueprint-based deployment for consistency
- Immutable templates after deployment
- Configuration separation from implementation

## Common Integration Patterns

### Basic Wallet Creation
```python
# Simple wallet creation
wallet = hatchery.createUserWallet()

# With ambassador referral
wallet = hatchery.createUserWallet(
    _ambassador=referrer_wallet.address
)
```

### Wallet Creation with Custom Settings
```python
# Create wallet for another user
wallet = hatchery.createUserWallet(
    _owner=new_user.address,
    _ambassador=referrer.address,
    _shouldUseTrialFunds=True,
    _groupId=organization_id
)

# Get wallet configuration
config_addr = get_wallet_config(wallet)
```

### Agent Creation and Setup
```python
# Create agent
agent = hatchery.createAgent(
    _owner=user.address,
    _groupId=group_id
)

# Add agent as manager to wallet
high_command.addManager(
    wallet,
    agent,
    manager_settings
)
```

### Trial Fund Management
```python
# Check trial funds before operations
if not hatchery.doesWalletStillHaveTrialFunds(wallet):
    # User has used trial funds, allow advanced features
    enable_advanced_features(wallet)
else:
    # Still has trial funds
    print("Please use trial funds first")

# Recover trial funds if needed
if hatchery.canClawbackTrialFunds(wallet, caller):
    amount = hatchery.clawBackTrialFunds(wallet)
    print(f"Recovered {amount} trial funds")
```

### Pre-Creation Validation
```python
# Get creation config
config = mission_control.getUserWalletCreationConfig(creator)

# Check if can create
if config.isCreatorAllowed:
    # Check global limit
    current_wallets = ledger.numUserWallets()
    if config.numUserWalletsAllowed == 0 or current_wallets < config.numUserWalletsAllowed:
        # Can create wallet
        wallet = hatchery.createUserWallet()
```

## Testing

For comprehensive test examples, see: [`tests/core/test_hatchery.py`](../../../tests/core/test_hatchery.py)