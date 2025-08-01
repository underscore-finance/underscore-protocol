# SwitchboardAlpha Technical Documentation

[📄 View Source Code](../../../contracts/config/SwitchboardAlpha.vy)

## Overview

SwitchboardAlpha is a comprehensive configuration management contract for the Underscore Protocol. It provides time-locked configuration changes for user wallets, assets, agents, managers, payees, and security settings. All configuration updates are managed through a secure timelock mechanism that ensures protocol changes are reviewable and reversible before implementation.

**Core Functions**:
- **User Wallet Configuration**: Manages wallet templates, trial funds, creation limits, and operational parameters
- **Asset Configuration**: Handles asset-specific settings including fees, yield parameters, and protocol integrations
- **Agent & Manager Configuration**: Controls agent templates, creation limits, and management parameters
- **Security Management**: Manages security permissions, creator whitelists, and signer locks
- **Time-Locked Changes**: All configuration updates require confirmation after a timelock period

Built with modular architecture, SwitchboardAlpha integrates governance controls, address management, and timelock functionality to ensure that protocol configuration changes are performed safely with appropriate oversight and community review periods.

## Architecture & Modules

SwitchboardAlpha uses a modular architecture combining governance, timelock, and address management:

### Addys Module
- **Location**: `contracts/modules/Addys.vy`
- **Purpose**: Provides protocol-wide address lookups and registry access
- **Documentation**: See [Addys Technical Documentation](../modules/Addys.md)
- **Key Features**:
  - Connection to UndyHq for protocol addresses
  - MissionControl and LegoBook address resolution
  - Cached address lookups for gas efficiency
- **Exported Interface**: All address functions are exposed via `addys.__interface__`

### LocalGov Module
- **Location**: `contracts/modules/LocalGov.vy`
- **Purpose**: Provides governance functionality with temporary governance support
- **Documentation**: See [LocalGov Technical Documentation](../modules/LocalGov.md)
- **Key Features**:
  - Links to UndyHq as primary governance authority
  - Supports temporary governance during deployment
  - No local governance timelock (managed by TimeLock module)
- **Exported Interface**: All governance functions are exposed via `gov.__interface__`

### TimeLock Module
- **Location**: `contracts/modules/Timelock.vy`
- **Purpose**: Provides time-locked action management for configuration changes
- **Documentation**: See [Timelock Technical Documentation](../modules/Timelock.md)
- **Key Features**:
  - Configurable minimum and maximum timelock periods
  - Action initiation, confirmation, and cancellation
  - Protection against immediate malicious configuration changes
- **Exported Interface**: All timelock functions are exposed via `timeLock.__interface__`

### Module Initialization
```vyper
initializes: addys
initializes: gov
initializes: timeLock[gov := gov]
```
This initialization pattern ensures proper module dependencies and secure timelock management for configuration updates.

## System Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                      SwitchboardAlpha Contract                     │
├────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐         ┌──────────────────────────────┐  │
│  │    Addys Module     │         │    LocalGov Module           │  │
│  │                     │         │                              │  │
│  │ • Protocol addrs    │         │ • UndyHq governance          │  │
│  │ • MissionControl    │         │ • Temp governance support    │  │
│  │ • LegoBook access   │         │ • Permission validation      │  │
│  └─────────────────────┘         └──────────────────────────────┘  │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                    TimeLock Module                          │  │
│  │                                                             │  │
│  │ • Action initiation with sequential IDs                    │  │
│  │ • Configurable timelock periods                            │  │
│  │ • Confirmation and cancellation management                 │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                Configuration Management Categories            │  │
│  │                                                              │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  │ User Wallet     │  │ Asset Config    │  │ Agent Config    │ │
│  │  │ Configuration   │  │                 │  │                 │ │
│  │  │                 │  │ • Asset settings│  │ • Templates     │ │
│  │  │ • Templates     │  │ • Yield params  │  │ • Creation      │ │
│  │  │ • Trial funds   │  │ • Fee structure │  │   limits        │ │
│  │  │ • Creation      │  │ • Stablecoin    │  │ • Starter agent │ │
│  │  │   limits        │  │   flags         │  │   params        │ │
│  │  │ • Timelock      │  │ • Protocol IDs  │  │                 │ │
│  │  │   bounds        │  │                 │  │                 │ │
│  │  │ • Stale blocks  │  │                 │  │                 │ │
│  │  │ • TX fees       │  │                 │  │                 │ │
│  │  │ • Ambassador    │  │                 │  │                 │ │
│  │  │   rev share     │  │                 │  │                 │ │
│  │  │ • Yield params  │  │                 │  │                 │ │
│  │  │ • Loot params   │  │                 │  │                 │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│  │                                                              │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  │ Manager Config  │  │ Payee Config    │  │ Security        │ │
│  │  │                 │  │                 │  │ Management      │ │
│  │  │ • Period        │  │ • Period        │  │                 │ │
│  │  │ • Activation    │  │ • Activation    │  │ • Security      │ │
│  │  │   length        │  │   length        │  │   actions       │ │
│  │  │                 │  │                 │  │ • Creator       │ │
│  │  │                 │  │                 │  │   whitelist     │ │
│  │  │                 │  │                 │  │ • Locked        │ │
│  │  │                 │  │                 │  │   signers       │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                                     │
                     ┌───────────────┴───────────────┐
                     ▼                               ▼
        ┌─────────────────────┐          ┌─────────────────────┐
        │   MissionControl    │          │    Protocol Users   │
        │                     │          │                     │
        │ • Receives config   │          │ • UserWallets       │
        │   updates           │          │ • Agents            │
        │ • Validates changes │          │ • Managers          │
        │ • Stores settings   │          │ • Protocol assets   │
        │ • Enforces limits   │          │                     │
        └─────────────────────┘          └─────────────────────┘
```

## Data Structures

### ActionType Flag
Defines the types of configuration actions available:
```vyper
flag ActionType:
    USER_WALLET_TEMPLATES          # Wallet and config templates
    TRIAL_FUNDS                    # Trial asset and amount
    WALLET_CREATION_LIMITS         # Wallet count and whitelist enforcement
    KEY_ACTION_TIMELOCK_BOUNDS     # Min/max timelock bounds
    DEFAULT_STALE_BLOCKS           # Default staleness period
    TX_FEES                        # Transaction fee structure
    AMBASSADOR_REV_SHARE           # Ambassador revenue sharing
    DEFAULT_YIELD_PARAMS           # Default yield parameters
    LOOT_PARAMS                    # Loot claiming parameters
    AGENT_TEMPLATE                 # Agent contract template
    AGENT_CREATION_LIMITS          # Agent creation constraints
    STARTER_AGENT_PARAMS           # Starter agent configuration
    MANAGER_CONFIG                 # Manager operation parameters
    PAYEE_CONFIG                   # Payee operation parameters
    CAN_PERFORM_SECURITY_ACTION    # Security action permissions
    ASSET_CONFIG                   # Asset-specific configuration
    IS_STABLECOIN                  # Stablecoin designation
```

### IsAddrAllowed Struct
Simple address permission mapping:
```vyper
struct IsAddrAllowed:
    addr: address        # Address being configured
    isAllowed: bool      # Permission or flag state
```

### PendingAssetConfig Struct
Tracks pending asset configuration changes:
```vyper
struct PendingAssetConfig:
    asset: address           # Asset being configured
    config: AssetConfig      # Complete asset configuration
```

## State Variables

### Pending Configuration Storage
- `actionType: HashMap[uint256, ActionType]` - Maps action ID to configuration type
- `pendingUserWalletConfig: HashMap[uint256, UserWalletConfig]` - Pending wallet configurations
- `pendingAssetConfig: HashMap[uint256, PendingAssetConfig]` - Pending asset configurations
- `pendingAgentConfig: HashMap[uint256, AgentConfig]` - Pending agent configurations
- `pendingManagerConfig: HashMap[uint256, ManagerConfig]` - Pending manager configurations
- `pendingPayeeConfig: HashMap[uint256, PayeeConfig]` - Pending payee configurations
- `pendingAddrToBool: HashMap[uint256, IsAddrAllowed]` - Pending address permission changes

### Constants
- `HUNDRED_PERCENT: uint256 = 100_00` - 100% in basis points

## Constructor

### `__init__`

Initializes SwitchboardAlpha with governance and timelock parameters.

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
| `_minConfigTimeLock` | `uint256` | Minimum timelock period for config changes (blocks) |
| `_maxConfigTimeLock` | `uint256` | Maximum timelock period for config changes (blocks) |

#### Returns

*The constructor does not return any values.*

#### Access

Called only once during contract deployment.

#### Example Usage
```python
# Deploy SwitchboardAlpha
switchboard_alpha = boa.load(
    "contracts/config/SwitchboardAlpha.vy",
    undy_hq.address,
    temp_gov.address,
    100,   # Min config timelock (blocks)
    1000   # Max config timelock (blocks)
)
```

#### Notes

- Initializes Addys with UndyHq connection
- Sets up LocalGov with both primary and temporary governance
- Configures TimeLock with default expiration equal to max timelock

## User Wallet Configuration Functions

### `setUserWalletTemplates`

Initiates time-locked update of wallet and configuration templates.

```vyper
@external
def setUserWalletTemplates(_walletTemplate: address, _configTemplate: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_walletTemplate` | `address` | New UserWallet template contract |
| `_configTemplate` | `address` | New UserWalletConfig template contract |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Action ID for tracking the pending change |

#### Access

Only callable by governance addresses.

#### Events Emitted

- `PendingUserWalletTemplatesChange` - Contains templates and confirmation details

#### Example Usage
```python
# Update wallet templates
action_id = switchboard_alpha.setUserWalletTemplates(
    new_wallet_template.address,
    new_config_template.address,
    sender=governance
)
```

### `setTrialFunds`

Configures trial funding for new wallet users.

```vyper
@external
def setTrialFunds(_trialAsset: address, _trialAmount: uint256) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_trialAsset` | `address` | Asset to provide as trial funds |
| `_trialAmount` | `uint256` | Amount of trial funds to provide |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Action ID for tracking |

#### Events Emitted

- `PendingTrialFundsChange` - Contains asset, amount, and confirmation details

### `setWalletCreationLimits`

Sets limits on wallet creation and creator whitelist enforcement.

```vyper
@external
def setWalletCreationLimits(_numUserWalletsAllowed: uint256, _enforceCreatorWhitelist: bool) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_numUserWalletsAllowed` | `uint256` | Maximum number of wallets allowed |
| `_enforceCreatorWhitelist` | `bool` | Whether to enforce creator whitelist |

#### Events Emitted

- `PendingWalletCreationLimitsChange` - Contains limits and confirmation details

### `setKeyActionTimelockBounds`

Configures timelock bounds for critical wallet actions.

```vyper
@external
def setKeyActionTimelockBounds(_minKeyActionTimeLock: uint256, _maxKeyActionTimeLock: uint256) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_minKeyActionTimeLock` | `uint256` | Minimum timelock for key actions (blocks) |
| `_maxKeyActionTimeLock` | `uint256` | Maximum timelock for key actions (blocks) |

#### Notes

- Minimum must be less than maximum
- Neither can be 0 or max_value(uint256)

### `setDefaultStaleBlocks`

Sets the default staleness period for price data.

```vyper
@external
def setDefaultStaleBlocks(_defaultStaleBlocks: uint256) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_defaultStaleBlocks` | `uint256` | Number of blocks before price data is stale |

### `setTxFees`

Configures transaction fee structure.

```vyper
@external
def setTxFees(_swapFee: uint256, _stableSwapFee: uint256, _rewardsFee: uint256) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_swapFee` | `uint256` | Fee for regular swaps (max 5%) |
| `_stableSwapFee` | `uint256` | Fee for stablecoin swaps (max 2%) |
| `_rewardsFee` | `uint256` | Fee for reward distributions (max 25%) |

#### Validation

- Swap fee capped at 5%
- Stable swap fee capped at 2%
- Rewards fee capped at 25%

### `setAmbassadorRevShare`

Configures ambassador revenue sharing ratios.

```vyper
@external
def setAmbassadorRevShare(_swapRatio: uint256, _rewardsRatio: uint256, _yieldRatio: uint256) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_swapRatio` | `uint256` | Ambassador share of swap fees (max 100%) |
| `_rewardsRatio` | `uint256` | Ambassador share of reward fees (max 100%) |
| `_yieldRatio` | `uint256` | Ambassador share of yield fees (max 100%) |

### `setDefaultYieldParams`

Configures default yield farming parameters.

```vyper
@external
def setDefaultYieldParams(
    _defaultYieldMaxIncrease: uint256,
    _defaultYieldPerformanceFee: uint256,
    _defaultYieldAmbassadorBonusRatio: uint256,
    _defaultYieldBonusRatio: uint256,
    _defaultYieldAltBonusAsset: address
) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_defaultYieldMaxIncrease` | `uint256` | Max yield increase threshold (max 10%) |
| `_defaultYieldPerformanceFee` | `uint256` | Performance fee rate (max 25%) |
| `_defaultYieldAmbassadorBonusRatio` | `uint256` | Ambassador bonus ratio (max 100%) |
| `_defaultYieldBonusRatio` | `uint256` | General bonus ratio (max 100%) |
| `_defaultYieldAltBonusAsset` | `address` | Alternative bonus asset |

### `setLootParams`

Configures loot distribution parameters.

```vyper
@external
def setLootParams(_depositRewardsAsset: address, _lootClaimCoolOffPeriod: uint256) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_depositRewardsAsset` | `address` | Asset used for deposit rewards |
| `_lootClaimCoolOffPeriod` | `uint256` | Cooldown period between loot claims |

## Asset Configuration Functions

### `setAssetConfig`

Configures comprehensive asset-specific settings.

```vyper
@external
def setAssetConfig(
    _asset: address,
    _legoId: uint256,
    _staleBlocks: uint256,
    _txFeesSwapFee: uint256,
    _txFeesStableSwapFee: uint256,
    _txFeesRewardsFee: uint256,
    _ambassadorRevShareSwapRatio: uint256,
    _ambassadorRevShareRewardsRatio: uint256,
    _ambassadorRevShareYieldRatio: uint256,
    _isYieldAsset: bool,
    _isRebasing: bool,
    _underlyingAsset: address,
    _maxYieldIncrease: uint256,
    _performanceFee: uint256,
    _ambassadorBonusRatio: uint256,
    _bonusRatio: uint256,
    _altBonusAsset: address
) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Asset being configured |
| `_legoId` | `uint256` | Associated Lego protocol ID |
| `_staleBlocks` | `uint256` | Staleness threshold for this asset |
| `_txFeesSwapFee` | `uint256` | Asset-specific swap fee |
| `_txFeesStableSwapFee` | `uint256` | Asset-specific stable swap fee |
| `_txFeesRewardsFee` | `uint256` | Asset-specific rewards fee |
| `_ambassadorRevShareSwapRatio` | `uint256` | Ambassador swap fee share |
| `_ambassadorRevShareRewardsRatio` | `uint256` | Ambassador rewards fee share |
| `_ambassadorRevShareYieldRatio` | `uint256` | Ambassador yield fee share |
| `_isYieldAsset` | `bool` | Whether asset generates yield |
| `_isRebasing` | `bool` | Whether asset is rebasing |
| `_underlyingAsset` | `address` | Underlying asset (for vault tokens) |
| `_maxYieldIncrease` | `uint256` | Maximum yield increase threshold |
| `_performanceFee` | `uint256` | Yield performance fee |
| `_ambassadorBonusRatio` | `uint256` | Ambassador yield bonus ratio |
| `_bonusRatio` | `uint256` | General yield bonus ratio |
| `_altBonusAsset` | `address` | Alternative bonus asset |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Action ID for tracking |

#### Access

Only callable by governance addresses.

#### Events Emitted

- `PendingAssetConfigChange` - Contains all asset configuration parameters

#### Example Usage
```python
# Configure USDC asset
action_id = switchboard_alpha.setAssetConfig(
    usdc.address,           # asset
    1,                      # legoId
    100,                    # staleBlocks
    30,                     # swapFee (0.3%)
    10,                     # stableSwapFee (0.1%)
    500,                    # rewardsFee (5%)
    5000,                   # ambassadorSwapRatio (50%)
    3000,                   # ambassadorRewardsRatio (30%)
    2000,                   # ambassadorYieldRatio (20%)
    False,                  # isYieldAsset
    False,                  # isRebasing
    ZERO_ADDRESS,           # underlyingAsset
    0,                      # maxYieldIncrease
    0,                      # performanceFee
    0,                      # ambassadorBonusRatio
    0,                      # bonusRatio
    ZERO_ADDRESS,           # altBonusAsset
    sender=governance
)
```

#### Validation

- Asset must not be empty address
- Lego ID must be valid in LegoBook
- Fee parameters must be within allowed ranges
- Yield parameters validated if `_isYieldAsset` is true

### `setIsStablecoin`

Designates an asset as a stablecoin.

```vyper
@external
def setIsStablecoin(_asset: address, _isStablecoin: bool) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Asset to configure |
| `_isStablecoin` | `bool` | Whether asset is a stablecoin |

#### Events Emitted

- `PendingIsStablecoinChange` - Contains asset, flag, and confirmation details

## Agent Configuration Functions

### `setAgentTemplate`

Sets the template contract for new agents.

```vyper
@external
def setAgentTemplate(_agentTemplate: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_agentTemplate` | `address` | New agent template contract |

#### Validation

- Template must not be empty address
- Template must be a contract

### `setAgentCreationLimits`

Configures agent creation constraints.

```vyper
@external
def setAgentCreationLimits(_numAgentsAllowed: uint256, _enforceCreatorWhitelist: bool) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_numAgentsAllowed` | `uint256` | Maximum number of agents allowed |
| `_enforceCreatorWhitelist` | `bool` | Whether to enforce creator whitelist |

### `setStarterAgentParams`

Configures starting agent parameters.

```vyper
@external
def setStarterAgentParams(_startingAgent: address, _startingAgentActivationLength: uint256) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_startingAgent` | `address` | Default starting agent (can be empty) |
| `_startingAgentActivationLength` | `uint256` | Activation period length |

#### Validation Logic

- If starting agent is set, activation length must be non-zero
- If starting agent is empty, activation length must be zero
- Activation length cannot be max_value(uint256)

## Manager and Payee Configuration Functions

### `setManagerConfig`

Configures manager operation parameters.

```vyper
@external
def setManagerConfig(_managerPeriod: uint256, _managerActivationLength: uint256) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_managerPeriod` | `uint256` | Manager operation period length |
| `_managerActivationLength` | `uint256` | Manager activation period |

#### Validation

- Both parameters must be non-zero and not max_value(uint256)

### `setPayeeConfig`

Configures payee operation parameters.

```vyper
@external
def setPayeeConfig(_payeePeriod: uint256, _payeeActivationLength: uint256) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_payeePeriod` | `uint256` | Payee operation period length |
| `_payeeActivationLength` | `uint256` | Payee activation period |

## Security Management Functions

### `setCanPerformSecurityAction`

Manages security action permissions with immediate removal capability.

```vyper
@external
def setCanPerformSecurityAction(_signer: address, _canPerform: bool) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_signer` | `address` | Address to configure |
| `_canPerform` | `bool` | Whether address can perform security actions |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Action ID (0 if immediate removal) |

#### Access

Only callable by governance addresses.

#### Special Behavior

- **Granting permissions**: Requires timelock confirmation
- **Removing permissions**: Applied immediately for security

#### Example Usage
```python
# Grant security permissions (time-locked)
action_id = switchboard_alpha.setCanPerformSecurityAction(
    security_operator.address,
    True,
    sender=governance
)

# Remove security permissions (immediate)
switchboard_alpha.setCanPerformSecurityAction(
    compromised_operator.address,
    False,
    sender=governance
)  # Returns 0, applied immediately
```

### `setCreatorWhitelist`

Manages creator whitelist with flexible access control.

```vyper
@external
def setCreatorWhitelist(_creator: address, _isWhitelisted: bool):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_creator` | `address` | Creator address to configure |
| `_isWhitelisted` | `bool` | Whitelist status |

#### Access

- **Adding to whitelist**: Governance only
- **Removing from whitelist**: Governance OR addresses with security action permissions

#### Events Emitted

- `CreatorWhitelistSet` - Contains creator, status, and caller information

### `setLockedSigner`

Manages signer lock status.

```vyper
@external
def setLockedSigner(_signer: address, _isLocked: bool):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_signer` | `address` | Signer address to configure |
| `_isLocked` | `bool` | Lock status |

#### Access

- **Locking signers**: Governance OR addresses with security action permissions
- **Unlocking signers**: Governance only

#### Events Emitted

- `LockedSignerSet` - Contains signer, status, and caller information

## Action Execution Functions

### `executePendingAction`

Executes a time-locked configuration change after confirmation period.

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
3. Route to appropriate execution handler based on action type
4. Update MissionControl with new configuration
5. Emit appropriate confirmation event
6. Clean up pending action data

#### Example Usage
```python
# Execute pending action after timelock
success = switchboard_alpha.executePendingAction(
    action_id,
    sender=governance
)
```

### `cancelPendingAction`

Cancels a pending configuration change.

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

### `_hasPermsToEnable`

Determines permission for enable/disable operations.

```vyper
@view
@internal
def _hasPermsToEnable(_caller: address, _shouldEnable: bool) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_caller` | `address` | Address attempting the action |
| `_shouldEnable` | `bool` | Whether operation is enabling or disabling |

#### Logic

- **Governance**: Can always enable or disable
- **Security operators**: Can only disable (for security)
- **Others**: No permissions

### Validation Functions

Multiple internal validation functions ensure configuration integrity:

- `_areValidUserWalletTemplates()` - Validates wallet template contracts
- `_isValidNumUserWalletsAllowed()` - Validates wallet count limits
- `_areValidKeyActionTimelockBounds()` - Validates timelock bounds
- `_isValidStaleBlocks()` - Validates staleness periods
- `_areValidTxFees()` - Validates transaction fees
- `_areValidAmbassadorRevShareRatios()` - Validates revenue sharing
- `_areValidYieldParams()` - Validates yield parameters
- `_areValidLootParams()` - Validates loot parameters
- `_isValidAssetConfig()` - Comprehensive asset validation
- `_isValidAgentTemplate()` - Validates agent templates
- `_areValidStarterAgentParams()` - Validates starter agent configuration

## Security Considerations

### Time-Lock Protection
- All configuration changes require timelock confirmation
- Prevents immediate malicious configuration updates
- Allows community review and intervention

### Granular Access Control
- Governance has full control over all configurations
- Security operators can only disable/remove permissions
- Immediate removal for security-critical permissions

### Validation Boundaries
- All parameters validated against reasonable bounds
- Fee caps prevent excessive charges
- Timelock bounds prevent unusable configurations

### Integration Safety
- Validates Lego IDs against LegoBook registry
- Ensures contract addresses for templates
- Comprehensive parameter validation

## Integration Patterns

### Configuration Update Process
```python
# 1. Initiate configuration change
action_id = switchboard_alpha.setTxFees(
    30,    # 0.3% swap fee
    10,    # 0.1% stable swap fee
    500,   # 5% rewards fee
    sender=governance
)

# 2. Wait for timelock period...

# 3. Execute after confirmation block
success = switchboard_alpha.executePendingAction(
    action_id,
    sender=governance
)
```

### Emergency Security Response
```python
# Immediate removal of compromised operator
switchboard_alpha.setCanPerformSecurityAction(
    compromised_operator,
    False,  # Remove immediately
    sender=governance
)

# Lock compromised signer
switchboard_alpha.setLockedSigner(
    compromised_signer,
    True,
    sender=security_operator
)
```

### Asset Onboarding
```python
# Configure new asset for protocol
action_id = switchboard_alpha.setAssetConfig(
    new_asset.address,
    lego_id,
    stale_blocks,
    # ... all configuration parameters
    sender=governance
)

# Designate as stablecoin if applicable
stablecoin_action = switchboard_alpha.setIsStablecoin(
    new_asset.address,
    True,
    sender=governance
)
```

## Testing

For comprehensive test examples, see: [`tests/config/test_switchboard_alpha.py`](../../../tests/config/test_switchboard_alpha.py)