# MissionControl Technical Documentation

[📄 View Source Code](../../../contracts/data/MissionControl.vy)

## Overview

MissionControl is the central configuration management contract for the Underscore Protocol. As a Department contract, it stores and manages all protocol-wide settings including wallet creation parameters, fee structures, asset configurations, yield settings, and security controls. It serves as the single source of truth for protocol behavior and limits.

**Core Features**:
- **Global Configuration Management**: Store protocol-wide settings for wallets, agents, managers, payees, and cheques
- **Asset-Specific Settings**: Configure per-asset fees, yield parameters, and integration details
- **Security Controls**: Manage creator whitelists, security signers, and locked addresses
- **Fee Structure**: Define swap fees, rewards fees, and ambassador revenue shares
- **Dynamic Configuration**: Update settings through governance without contract upgrades via [SwitchboardAlpha](../config/SwitchboardAlpha.md) and [SwitchboardBravo](../config/SwitchboardBravo.md)

The contract implements sophisticated configuration patterns including hierarchical settings with defaults and overrides, structured data for complex configurations, granular access control for updates, and view helpers for aggregated configurations.

## System Architecture Diagram

```
+-------------------------------------------------------------------------+
|                            MissionControl                               |
+-------------------------------------------------------------------------+
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                    Configuration Hierarchy                         | |
|  |                                                                   | |
|  |  Global Configs:                                                  | |
|  |    ├─> UserWalletConfig - Default settings for all wallets        | |
|  |    ├─> AgentConfig - Agent creation and defaults                  | |
|  |    ├─> ManagerConfig - Manager periods and activation             | |
|  |    ├─> PayeeConfig - Payee periods and activation                 | |
|  |    └─> ChequeConfig - Cheque limits and timing                    | |
|  |                                                                   | |
|  |  Asset-Specific Configs:                                          | |
|  |    ├─> AssetConfig[asset] - Per-asset overrides                   | |
|  |    ├─> Transaction fees (swap, rewards)                            | |
|  |    ├─> Yield parameters (bonus ratios, fees)                      | |
|  |    └─> Integration details (legoId, decimals)                     | |
|  |                                                                   | |
|  |  Precedence Rules:                                                | |
|  |    1. Asset-specific config (if set)                              | |
|  |    2. Global default config                                       | |
|  |    3. Hard-coded fallback                                         | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                      Security Architecture                         | |
|  |                                                                   | |
|  |  Creator Control:                                                  | |
|  |    • enforceCreatorWhitelist flag per entity type                 | |
|  |    • creatorWhitelist mapping for allowed creators                | |
|  |    • Public creation when whitelist not enforced                  | |
|  |                                                                   | |
|  |  Security Actions:                                                 | |
|  |    • canPerformSecurityAction - Emergency intervention rights      | |
|  |    • isLockedSigner - Prevent specific addresses from actions     | |
|  |    • Switchboard-only updates for all settings                    | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                     Configuration Aggregation                      | |
|  |                                                                   | |
|  |  Helper Functions combine multiple configs:                        | |
|  |                                                                   | |
|  |  getUserWalletCreationConfig:                                     | |
|  |    Merges UserWallet, Manager, Payee, Agent, Cheque configs       | |
|  |                                                                   | |
|  |  getLootDistroConfig:                                             | |
|  |    Combines asset config with global defaults for distribution     | |
|  |                                                                   | |
|  |  getProfitCalcConfig / getAssetUsdValueConfig:                    | |
|  |    Asset config with fallback to global defaults                  | |
|  +-------------------------------------------------------------------+ |
+-------------------------------------------------------------------------+
```

## Module Integration

MissionControl implements the Department interface and integrates:
- `Addys` module for address registry management
- `DeptBasics` module for pause functionality

## Data Structures

### Configuration Structs (from ConfigStructs interface)

**UserWalletConfig**: Global wallet settings including templates, trial funds, time locks, fees, and ambassador revenue shares

**AssetConfig**: Per-asset configuration with protocol integration, decimals, fees, and yield parameters

**TxFees**: Transaction fee structure for swaps and rewards

**AmbassadorRevShare**: Revenue share ratios for different action types

**YieldConfig**: Yield asset parameters including bonus ratios and performance fees

**AgentConfig**: Agent creation settings and templates

**ManagerConfig**: Manager activation periods

**PayeeConfig**: Payee activation periods

**ChequeConfig**: Cheque limits and timing parameters

## State Variables

### Global Configurations
- `userWalletConfig: cs.UserWalletConfig` - Protocol-wide wallet settings
- `agentConfig: cs.AgentConfig` - Agent creation configuration
- `managerConfig: cs.ManagerConfig` - Manager settings
- `payeeConfig: cs.PayeeConfig` - Payee settings
- `chequeConfig: cs.ChequeConfig` - Cheque settings

### Asset Configurations
- `assetConfig: HashMap[address, cs.AssetConfig]` - Per-asset settings
- `isStablecoin: HashMap[address, bool]` - Stablecoin flags for fee logic

### Security Settings
- `creatorWhitelist: HashMap[address, bool]` - Allowed creators
- `canPerformSecurityAction: HashMap[address, bool]` - Security signers
- `isLockedSigner: HashMap[address, bool]` - Locked addresses

## Constructor

### `__init__`

Initializes MissionControl with optional default configuration.

```vyper
@deploy
def __init__(_undyHq: address, _defaults: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq registry contract address |
| `_defaults` | `address` | Optional defaults contract for initial config |

#### Access

Called only during deployment

#### Example Usage
```python
# Deploy with defaults
mission_control = MissionControl.deploy(
    undy_hq.address,
    defaults_contract.address
)

# Deploy without defaults
mission_control = MissionControl.deploy(
    undy_hq.address,
    ZERO_ADDRESS
)
```

## Global Configuration Functions

### `setUserWalletConfig`

Updates global user wallet configuration.

```vyper
@external
def setUserWalletConfig(_config: cs.UserWalletConfig):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_config` | `UserWalletConfig` | Complete wallet configuration struct |

#### Access

Only callable by switchboard addresses

#### Example Usage
```python
# Update wallet configuration
mission_control.setUserWalletConfig(
    new_wallet_config,
    sender=switchboard
)
```

### `setManagerConfig`

Updates manager configuration.

```vyper
@external
def setManagerConfig(_config: cs.ManagerConfig):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_config` | `ManagerConfig` | Manager settings |

#### Access

Only callable by switchboard addresses

### `setPayeeConfig`

Updates payee configuration.

```vyper
@external
def setPayeeConfig(_config: cs.PayeeConfig):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_config` | `PayeeConfig` | Payee settings |

#### Access

Only callable by switchboard addresses

### `setChequeConfig`

Updates cheque configuration.

```vyper
@external
def setChequeConfig(_config: cs.ChequeConfig):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_config` | `ChequeConfig` | Cheque settings |

#### Access

Only callable by switchboard addresses

### `getUserWalletCreationConfig`

Gets aggregated configuration for wallet creation.

```vyper
@view
@external
def getUserWalletCreationConfig(_creator: address) -> UserWalletCreationConfig:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_creator` | `address` | Address attempting to create wallet |

#### Returns

| Type | Description |
|------|-------------|
| `UserWalletCreationConfig` | Aggregated creation configuration |

#### Access

Public view function

#### Example Usage
```python
# Check creation permissions and settings
config = mission_control.getUserWalletCreationConfig(creator)
if config.isCreatorAllowed:
    # Can create wallet with config parameters
    pass
```

## Agent Configuration Functions

### `setAgentConfig`

Updates agent configuration.

```vyper
@external
def setAgentConfig(_config: cs.AgentConfig):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_config` | `AgentConfig` | Agent configuration struct |

#### Access

Only callable by switchboard addresses

### `setStarterAgent`

Updates the default starting agent.

```vyper
@external
def setStarterAgent(_agent: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_agent` | `address` | Default agent address |

#### Access

Only callable by switchboard addresses

### `getAgentCreationConfig`

Gets aggregated configuration for agent creation.

```vyper
@view
@external
def getAgentCreationConfig(_creator: address) -> AgentCreationConfig:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_creator` | `address` | Address attempting to create agent |

#### Returns

| Type | Description |
|------|-------------|
| `AgentCreationConfig` | Aggregated agent creation config |

#### Access

Public view function

## Asset Configuration Functions

### `setAssetConfig`

Sets configuration for a specific asset.

```vyper
@external
def setAssetConfig(_asset: address, _config: cs.AssetConfig):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Asset address to configure |
| `_config` | `AssetConfig` | Asset configuration struct |

#### Access

Only callable by switchboard addresses

#### Example Usage
```python
# Configure yield vault
vault_config = AssetConfig(
    legoId=5,
    decimals=18,
    staleBlocks=50,
    txFees=TxFees(...),
    ambassadorRevShare=AmbassadorRevShare(...),
    yieldConfig=YieldConfig(
        isYieldAsset=True,
        isRebasing=False,
        underlyingAsset=usdc.address,
        maxYieldIncrease=50_00,  # 50%
        performanceFee=10_00,    # 10%
        ...
    )
)
mission_control.setAssetConfig(vault.address, vault_config)
```

### `setIsStablecoin`

Marks an asset as a stablecoin.

```vyper
@external
def setIsStablecoin(_asset: address, _isStablecoin: bool):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Asset address |
| `_isStablecoin` | `bool` | Whether asset is stablecoin |

#### Access

Only callable by switchboard addresses

### `getProfitCalcConfig`

Gets profit calculation configuration for an asset.

```vyper
@view
@external
def getProfitCalcConfig(_asset: address) -> ProfitCalcConfig:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Asset to get config for |

#### Returns

| Type | Description |
|------|-------------|
| `ProfitCalcConfig` | Profit calculation parameters |

#### Access

Public view function

### `getAssetUsdValueConfig`

Gets USD value calculation configuration.

```vyper
@view
@external
def getAssetUsdValueConfig(_asset: address) -> AssetUsdValueConfig:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Asset to get config for |

#### Returns

| Type | Description |
|------|-------------|
| `AssetUsdValueConfig` | USD value calculation parameters |

#### Access

Public view function

## Fee Functions

### `getSwapFee`

Gets swap fee for a token pair.

```vyper
@view
@external
def getSwapFee(_tokenIn: address, _tokenOut: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_tokenIn` | `address` | Input token |
| `_tokenOut` | `address` | Output token |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Swap fee in basis points |

#### Access

Public view function

#### Fee Logic
1. If both tokens are stablecoins: use `stableSwapFee`
2. If output token has asset config: use asset-specific swap fee
3. Otherwise: use global default swap fee

### `getRewardsFee`

Gets rewards claiming fee for an asset.

```vyper
@view
@external
def getRewardsFee(_asset: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Reward asset |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Rewards fee in basis points |

#### Access

Public view function

## Security Functions

### `setCanPerformSecurityAction`

Grants or revokes security action permissions.

```vyper
@external
def setCanPerformSecurityAction(_signer: address, _canPerform: bool):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_signer` | `address` | Address to configure |
| `_canPerform` | `bool` | Whether can perform security actions |

#### Access

Only callable by switchboard addresses

### `setCreatorWhitelist`

Adds or removes addresses from creator whitelist.

```vyper
@external
def setCreatorWhitelist(_creator: address, _isWhitelisted: bool):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_creator` | `address` | Creator address |
| `_isWhitelisted` | `bool` | Whether whitelisted |

#### Access

Only callable by switchboard addresses

### `setLockedSigner`

Locks or unlocks a signer address.

```vyper
@external
def setLockedSigner(_signer: address, _isLocked: bool):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_signer` | `address` | Signer address |
| `_isLocked` | `bool` | Whether locked |

#### Access

Only callable by switchboard addresses

## Additional View Functions

### `getLootDistroConfig`

Gets loot distribution configuration for an asset.

```vyper
@view
@external
def getLootDistroConfig(_asset: address) -> LootDistroConfig:
```

### `getDepositRewardsAsset`

Gets the configured deposit rewards asset.

```vyper
@view
@external
def getDepositRewardsAsset() -> address:
```

### `getLootClaimCoolOffPeriod`

Gets the loot claim cooldown period.

```vyper
@view
@external
def getLootClaimCoolOffPeriod() -> uint256:
```

## Configuration Patterns

### Asset Configuration with Defaults
```python
# Check asset-specific config
config = mission_control.getAssetUsdValueConfig(asset)

if config.decimals == 0:
    # No asset-specific config, using defaults
    print("Using global defaults")
else:
    # Asset has custom configuration
    print(f"Using custom config with {config.decimals} decimals")
```

### Fee Calculation Pattern
```python
# Get appropriate fee for swap
fee = mission_control.getSwapFee(token_in, token_out)

# Apply fee to swap amount
fee_amount = swap_amount * fee / 10000
net_amount = swap_amount - fee_amount
```

### Security Check Pattern
```python
# Check if address can perform security action
if mission_control.canPerformSecurityAction(caller):
    # Allow emergency intervention
    perform_security_action()

# Check if signer is locked
if mission_control.isLockedSigner(signer):
    raise Exception("Signer is locked")
```

### Creator Validation Pattern
```python
# Get creation config
config = mission_control.getUserWalletCreationConfig(creator)

if config.isCreatorAllowed:
    # Check other limits
    if config.numUserWalletsAllowed > 0:
        # Global limit enforced
        pass
else:
    raise Exception("Creator not whitelisted")
```

## Security Considerations

### Access Control
- All configuration updates restricted to switchboard
- No direct user access to modify settings
- Department-based permission system

### Configuration Safety
- Structured data prevents partial updates
- Validation in consuming contracts
- Pause protection on all setters

### Defaults and Fallbacks
- Global defaults for unset values
- Zero checks for missing configs
- Graceful degradation patterns

## Testing

For comprehensive test examples, see: [`tests/core/data/test_mission_control.py`](../../../tests/core/data/test_mission_control.py)