# UserWalletConfig Technical Documentation

[📄 View Source Code](../../../contracts/core/userWallet/UserWalletConfig.vy)

## Overview

UserWalletConfig is the comprehensive configuration and access control contract for UserWallet instances in the Underscore Protocol. It manages all permission-based operations, user roles (managers, payees, whitelist), transaction limits, and security features while providing a flexible framework for wallet governance and backpack module integration.

**Core Features**:
- **Multi-tier Permission System**: Hierarchical access control with owner, managers, payees, and whitelisted addresses
- **Transaction Limits**: Configurable USD value and frequency limits for managers and payees with per-period tracking  
- **Cheque Management**: Full cheque lifecycle management with creation, validation, and payment controls
- **Security Controls**: Wallet freezing, ejection mode, time-locked operations, and trial fund management

The contract implements sophisticated period-based tracking for rate limiting, flexible configuration for different user types, integration with the wallet backpack module system, and comprehensive validation through the [Sentinel](../walletBackpack/Sentinel.md) contract for all operations. Managers are administered through [HighCommand](../walletBackpack/HighCommand.md), payees through [Paymaster](../walletBackpack/Paymaster.md), and cheques through [ChequeBook](../walletBackpack/ChequeBook.md). Pull payments are processed via the [Billing](../core/Billing.md) engine.

## Architecture & Modules

UserWalletConfig inherits critical functionality through a modular architecture:

### Ownership Module
- **Location**: `contracts/modules/Ownership.vy`
- **Purpose**: Provides secure ownership management with time-locked transfers
- **Documentation**: See [Ownership Technical Documentation](../modules/Ownership.md)
- **Key Features**:
  - Time-locked ownership transfers with two-step confirmation
  - Security override capabilities via MissionControl
  - Configurable time-lock periods within defined bounds
- **Exported Interface**: All ownership functions are exposed via `ownership.__interface__`

### Module Initialization
```vyper
initializes: ownership
exports: ownership.__interface__
```
This initialization pattern ensures UserWalletConfig inherits complete ownership management functionality while maintaining clean separation of concerns.

## System Architecture Diagram

```
+-------------------------------------------------------------------------+
|                           UserWalletConfig                              |
+-------------------------------------------------------------------------+
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                      User Role Management                         | |
|  |                                                                   | |
|  |  Owner:                                                          | |
|  |    - Full control over wallet and configuration                  | |
|  |    - Can manage all other roles                                  | |
|  |                                                                   | |
|  |  Managers:                                                       | |
|  |    - Limited transaction permissions                             | |
|  |    - USD value and frequency limits                              | |
|  |    - Specific action permissions (yield, swap, etc.)             | |
|  |                                                                   | |
|  |  Payees:                                                         | |
|  |    - Can receive funds with limits                               | |
|  |    - Period-based caps and cooldowns                             | |
|  |    - Optional pull payment capability                            | |
|  |                                                                   | |
|  |  Whitelist:                                                      | |
|  |    - Unrestricted fund recipients                                | |
|  |    - Bypass payee validation                                      | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                    Permission Validation Flow                      | |
|  |                                                                   | |
|  |  1. checkSignerPermissionsAndGetBundle                            | |
|  |     ├─> Verify signer role (owner/manager)                       | |
|  |     ├─> Check signer not locked                                  | |
|  |     ├─> Validate action permissions via Sentinel                 | |
|  |     └─> Return ActionData bundle                                 | |
|  |                                                                   | |
|  |  2. checkRecipientLimitsAndUpdateData                            | |
|  |     ├─> Check if whitelisted (bypass limits)                     | |
|  |     ├─> Validate payee limits via Sentinel                       | |
|  |     └─> Update period tracking data                              | |
|  |                                                                   | |
|  |  3. validateCheque                                               | |
|  |     ├─> Verify cheque details                                    | |
|  |     ├─> Check period limits                                      | |
|  |     └─> Update cheque tracking                                   | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                     Backpack Module System                        | |
|  |                                                                   | |
|  |  * Kernel: Whitelist management                                  | |
|  |  * Sentinel: Permission validation engine                        | |
|  |  * HighCommand: Manager administration                           | |
|  |  * Paymaster: Payee management                                   | |
|  |  * ChequeBook: Cheque operations                                 | |
|  |  * Migrator: Wallet migration utilities                          | |
|  +-------------------------------------------------------------------+ |
+-------------------------------------------------------------------------+
```

## Data Structures

### ManagerSettings Struct
Configuration for manager permissions and limits:
```vyper
struct ManagerSettings:
    startBlock: uint256              # When manager becomes active
    expiryBlock: uint256            # When manager expires
    limits: ManagerLimits           # USD value and tx limits
    legoPerms: LegoPerms           # DeFi protocol permissions
    whitelistPerms: WhitelistPerms  # Whitelist management permissions
    transferPerms: TransferPerms    # Transfer and payee permissions
    allowedAssets: DynArray[address, MAX_CONFIG_ASSETS]  # Allowed tokens
    canClaimLoot: bool             # Can claim protocol rewards
```

### PayeeSettings Struct
Configuration for payee limits and restrictions:
```vyper
struct PayeeSettings:
    startBlock: uint256             # When payee becomes active
    expiryBlock: uint256           # When payee expires
    canPull: bool                  # Can pull payments
    periodLength: uint256          # Period for limits (blocks)
    maxNumTxsPerPeriod: uint256    # Max transactions per period
    txCooldownBlocks: uint256      # Cooldown between transactions
    failOnZeroPrice: bool          # Fail if asset has no price
    primaryAsset: address          # Primary payment asset
    onlyPrimaryAsset: bool         # Restrict to primary asset only
    unitLimits: PayeeLimits        # Token amount limits
    usdLimits: PayeeLimits         # USD value limits
```

### Cheque Struct
Represents a payment cheque:
```vyper
struct Cheque:
    recipient: address              # Cheque recipient
    asset: address                 # Payment asset
    amount: uint256                # Payment amount
    creationBlock: uint256         # When created
    unlockBlock: uint256           # When becomes payable
    expiryBlock: uint256           # When expires
    usdValueOnCreation: uint256    # USD value at creation
    canManagerPay: bool            # Can managers pay this cheque
    canBePulled: bool              # Can be pulled by recipient
    creator: address               # Who created the cheque
    active: bool                   # Is cheque active
```

### ActionData Struct
Bundle of addresses and state for action validation:
```vyper
struct ActionData:
    ledger: address                # Ledger contract
    missionControl: address        # Security control contract
    legoBook: address             # DeFi protocol registry
    hatchery: address             # Trial fund manager
    lootDistributor: address      # Fee distributor
    appraiser: address            # Price oracle
    billing: address              # Billing contract
    wallet: address               # User wallet
    walletConfig: address         # This config contract
    walletOwner: address          # Wallet owner
    inEjectMode: bool            # Emergency withdrawal mode
    isFrozen: bool               # Wallet frozen state
    lastTotalUsdValue: uint256   # Previous USD value
    signer: address              # Transaction signer
    isManager: bool              # Is signer a manager
    legoId: uint256              # DeFi protocol ID
    legoAddr: address            # DeFi protocol address
    eth: address                 # ETH placeholder
    weth: address                # WETH address
```

## State Variables

### Core State
- `wallet: address` - Associated UserWallet contract
- `kernel: address` - Whitelist management module
- `sentinel: address` - Permission validation module
- `highCommand: address` - Manager administration module
- `paymaster: address` - Payee management module
- `chequeBook: address` - Cheque operations module
- `migrator: address` - Migration utilities module

### Trial Funds
- `trialFundsAsset: address` - Trial fund token
- `trialFundsAmount: uint256` - Trial fund amount

### Manager Registry
- `managerSettings: HashMap[address, ManagerSettings]` - Manager configurations
- `managerPeriodData: HashMap[address, ManagerData]` - Manager tracking data
- `managers: HashMap[uint256, address]` - Index to manager mapping
- `indexOfManager: HashMap[address, uint256]` - Manager to index mapping
- `numManagers: uint256` - Total managers count

### Payee Registry
- `payeeSettings: HashMap[address, PayeeSettings]` - Payee configurations
- `payeePeriodData: HashMap[address, PayeeData]` - Payee tracking data
- `payees: HashMap[uint256, address]` - Index to payee mapping
- `indexOfPayee: HashMap[address, uint256]` - Payee to index mapping
- `numPayees: uint256` - Total payees count
- `pendingPayees: HashMap[address, PendingPayee]` - Time-locked payee additions

### Whitelist Registry
- `whitelistAddr: HashMap[uint256, address]` - Index to whitelist mapping
- `indexOfWhitelist: HashMap[address, uint256]` - Whitelist to index mapping
- `numWhitelisted: uint256` - Total whitelisted count
- `pendingWhitelist: HashMap[address, PendingWhitelist]` - Time-locked additions

### Cheque System
- `cheques: HashMap[address, Cheque]` - Active cheques by recipient
- `chequeSettings: ChequeSettings` - Global cheque configuration
- `chequePeriodData: ChequeData` - Period tracking for cheques
- `numActiveCheques: uint256` - Count of active cheques

### Global Configuration
- `globalManagerSettings: GlobalManagerSettings` - Default manager settings
- `globalPayeeSettings: GlobalPayeeSettings` - Default payee settings
- `timeLock: uint256` - Time-lock period for changes
- `isFrozen: bool` - Wallet frozen state
- `inEjectMode: bool` - Emergency mode state
- `groupId: uint256` - Wallet group identifier
- `startingAgent: address` - Initial manager address
- `didSetWallet: bool` - Wallet set flag

### Immutable Variables
- `UNDY_HQ: address` - UndyHq registry address
- `WETH: address` - WETH token address
- `ETH: address` - ETH placeholder address
- `MIN_TIMELOCK: uint256` - Minimum time-lock period
- `MAX_TIMELOCK: uint256` - Maximum time-lock period

### Constants
- `API_VERSION: String[28] = "0.1.0"` - Contract version
- `MAX_ASSETS: uint256 = 10` - Maximum assets per action
- `MAX_LEGOS: uint256 = 10` - Maximum legos per action
- Registry IDs for various protocol contracts

## Constructor

### `__init__`

Initializes the wallet configuration with all necessary settings and modules.

```vyper
@deploy
def __init__(
    _undyHq: address,
    _owner: address,
    _groupId: uint256,
    _trialFundsAsset: address,
    _trialFundsAmount: uint256,
    _globalManagerSettings: GlobalManagerSettings,
    _globalPayeeSettings: GlobalPayeeSettings,
    _chequeSettings: ChequeSettings,
    _startingAgent: address,
    _starterAgentSettings: ManagerSettings,
    _kernel: address,
    _sentinel: address,
    _highCommand: address,
    _paymaster: address,
    _chequeBook: address,
    _migrator: address,
    _wethAddr: address,
    _ethAddr: address,
    _minTimeLock: uint256,
    _maxTimeLock: uint256,
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq registry contract |
| `_owner` | `address` | Initial wallet owner |
| `_groupId` | `uint256` | Wallet group identifier |
| `_trialFundsAsset` | `address` | Trial fund token address |
| `_trialFundsAmount` | `uint256` | Trial fund amount |
| `_globalManagerSettings` | `GlobalManagerSettings` | Default manager settings |
| `_globalPayeeSettings` | `GlobalPayeeSettings` | Default payee settings |
| `_chequeSettings` | `ChequeSettings` | Cheque system settings |
| `_startingAgent` | `address` | Initial manager address |
| `_starterAgentSettings` | `ManagerSettings` | Initial manager config |
| `_kernel` | `address` | Whitelist module |
| `_sentinel` | `address` | Permission module |
| `_highCommand` | `address` | Manager module |
| `_paymaster` | `address` | Payee module |
| `_chequeBook` | `address` | Cheque module |
| `_migrator` | `address` | Migration module |
| `_wethAddr` | `address` | WETH address |
| `_ethAddr` | `address` | ETH placeholder |
| `_minTimeLock` | `uint256` | Minimum time-lock |
| `_maxTimeLock` | `uint256` | Maximum time-lock |

#### Access

Called only during deployment

## Initialization Functions

### `setWallet`

One-time function to set the associated UserWallet address.

```vyper
@external
def setWallet(_wallet: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_wallet` | `address` | UserWallet contract address |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Success status |

#### Access

Only callable by Hatchery contract, one-time use

## Permission Validation Functions

### `checkSignerPermissionsAndGetBundle`

Validates signer permissions and returns action data bundle.

```vyper
@view
@external
def checkSignerPermissionsAndGetBundle(
    _signer: address,
    _action: ActionType,
    _assets: DynArray[address, MAX_ASSETS] = [],
    _legoIds: DynArray[uint256, MAX_LEGOS] = [],
    _transferRecipient: address = empty(address),
) -> ActionData:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_signer` | `address` | Address attempting the action |
| `_action` | `ActionType` | Type of action being performed |
| `_assets` | `DynArray[address, MAX_ASSETS]` | Assets involved in action |
| `_legoIds` | `DynArray[uint256, MAX_LEGOS]` | DeFi protocol IDs |
| `_transferRecipient` | `address` | Transfer recipient (if applicable) |

#### Returns

| Type | Description |
|------|-------------|
| `ActionData` | Bundle of addresses and state for the action |

#### Access

View function called by UserWallet

#### Example Usage
```python
# UserWallet calls this before executing an action
action_data = wallet_config.checkSignerPermissionsAndGetBundle(
    user.address,
    ActionType.SWAP,
    [token_a.address, token_b.address],
    [uniswap_lego_id]
)
```

### `checkManagerUsdLimitsAndUpdateData`

Validates manager USD limits and updates tracking data.

```vyper
@external
def checkManagerUsdLimitsAndUpdateData(_manager: address, _txUsdValue: uint256) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_manager` | `address` | Manager address |
| `_txUsdValue` | `uint256` | USD value of transaction |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Success status |

#### Access

Only callable by UserWallet

### `checkRecipientLimitsAndUpdateData`

Validates recipient (payee) limits and updates tracking.

```vyper
@external
def checkRecipientLimitsAndUpdateData(
    _recipient: address,
    _txUsdValue: uint256,
    _asset: address,
    _amount: uint256,
) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_recipient` | `address` | Payment recipient |
| `_txUsdValue` | `uint256` | USD value of payment |
| `_asset` | `address` | Asset being sent |
| `_amount` | `uint256` | Amount being sent |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Success status |

#### Access

Only callable by UserWallet

### `validateCheque`

Validates cheque payment and updates tracking.

```vyper
@external
def validateCheque(
    _recipient: address,
    _asset: address,
    _amount: uint256,
    _txUsdValue: uint256,
    _signer: address,
) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_recipient` | `address` | Cheque recipient |
| `_asset` | `address` | Payment asset |
| `_amount` | `uint256` | Payment amount |
| `_txUsdValue` | `uint256` | USD value |
| `_signer` | `address` | Transaction signer |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Success status |

#### Access

Only callable by UserWallet

## Whitelist Management Functions

### `addPendingWhitelistAddr`

Initiates time-locked whitelist addition.

```vyper
@external
def addPendingWhitelistAddr(_addr: address, _pending: PendingWhitelist):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | Address to whitelist |
| `_pending` | `PendingWhitelist` | Pending whitelist data |

#### Access

Only callable by Kernel module

### `confirmWhitelistAddr`

Confirms pending whitelist addition after time-lock.

```vyper
@external
def confirmWhitelistAddr(_addr: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | Address to confirm |

#### Access

Only callable by Kernel module

### `cancelPendingWhitelistAddr`

Cancels pending whitelist addition.

```vyper
@external
def cancelPendingWhitelistAddr(_addr: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | Address to cancel |

#### Access

Only callable by Kernel module

### `removeWhitelistAddr`

Removes address from whitelist.

```vyper
@external
def removeWhitelistAddr(_addr: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | Address to remove |

#### Access

Only callable by Kernel module

### `addWhitelistAddrViaMigrator`

Adds address to whitelist during migration (no time-lock).

```vyper
@external
def addWhitelistAddrViaMigrator(_addr: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | Address to whitelist |

#### Access

Only callable by Migrator module

## Manager Management Functions

### `addManager`

Adds a new manager with configuration.

```vyper
@external
def addManager(_manager: address, _config: ManagerSettings):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_manager` | `address` | Manager address |
| `_config` | `ManagerSettings` | Manager configuration |

#### Access

Only callable by HighCommand or Migrator

### `updateManager`

Updates existing manager configuration.

```vyper
@external
def updateManager(_manager: address, _config: ManagerSettings):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_manager` | `address` | Manager address |
| `_config` | `ManagerSettings` | New configuration |

#### Access

Only callable by HighCommand

### `removeManager`

Removes a manager and clears their data.

```vyper
@external
def removeManager(_manager: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_manager` | `address` | Manager to remove |

#### Access

Only callable by HighCommand

### `setGlobalManagerSettings`

Updates global manager settings.

```vyper
@external
def setGlobalManagerSettings(_config: GlobalManagerSettings):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_config` | `GlobalManagerSettings` | New global settings |

#### Access

Only callable by HighCommand or Migrator

## Payee Management Functions

### `addPayee`

Adds a new payee with configuration.

```vyper
@external
def addPayee(_payee: address, _config: PayeeSettings):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_payee` | `address` | Payee address |
| `_config` | `PayeeSettings` | Payee configuration |

#### Access

Only callable by Paymaster or Migrator

### `updatePayee`

Updates existing payee configuration.

```vyper
@external
def updatePayee(_payee: address, _config: PayeeSettings):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_payee` | `address` | Payee address |
| `_config` | `PayeeSettings` | New configuration |

#### Access

Only callable by Paymaster

### `removePayee`

Removes a payee and clears their data.

```vyper
@external
def removePayee(_payee: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_payee` | `address` | Payee to remove |

#### Access

Only callable by Paymaster

### `setGlobalPayeeSettings`

Updates global payee settings.

```vyper
@external
def setGlobalPayeeSettings(_config: GlobalPayeeSettings):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_config` | `GlobalPayeeSettings` | New global settings |

#### Access

Only callable by Paymaster or Migrator

### Pending Payee Functions

Functions for time-locked payee additions:

- `addPendingPayee` - Initiates payee addition
- `confirmPendingPayee` - Confirms after time-lock
- `cancelPendingPayee` - Cancels pending addition

All accessible only by Paymaster module.

## Cheque Management Functions

### `createCheque`

Creates a new cheque or updates existing one.

```vyper
@external
def createCheque(
    _recipient: address,
    _cheque: Cheque,
    _chequeData: ChequeData,
    _isExistingCheque: bool,
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_recipient` | `address` | Cheque recipient |
| `_cheque` | `Cheque` | Cheque details |
| `_chequeData` | `ChequeData` | Updated tracking data |
| `_isExistingCheque` | `bool` | Whether updating existing |

#### Access

Only callable by ChequeBook module

### `cancelCheque`

Cancels an active cheque.

```vyper
@external
def cancelCheque(_recipient: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_recipient` | `address` | Cheque recipient |

#### Access

Only callable by ChequeBook module

### `setChequeSettings`

Updates global cheque settings.

```vyper
@external
def setChequeSettings(_config: ChequeSettings):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_config` | `ChequeSettings` | New cheque settings |

#### Access

Only callable by ChequeBook module

## Wallet Tool Functions

### `updateAssetData`

Updates single asset data with yield checking.

```vyper
@external
def updateAssetData(_legoId: uint256, _asset: address, _shouldCheckYield: bool) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_legoId` | `uint256` | Lego ID for action data |
| `_asset` | `address` | Asset to update |
| `_shouldCheckYield` | `bool` | Check for yield profits |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | New total USD value |

#### Access

Security action permission or Switchboard

### `updateAllAssetData`

Updates all wallet assets with yield checking.

```vyper
@external
def updateAllAssetData(_shouldCheckYield: bool) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_shouldCheckYield` | `bool` | Check for yield profits |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | New total USD value |

#### Access

Security action permission or Switchboard

### `removeTrialFunds`

Removes trial funds from wallet.

```vyper
@external
def removeTrialFunds() -> uint256:
```

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Amount removed |

#### Access

Only callable by Hatchery

### `getTrialFundsInfo`

Returns trial funds information.

```vyper
@view
@external
def getTrialFundsInfo() -> (address, uint256):
```

#### Returns

| Type | Description |
|------|-------------|
| `address` | Trial fund asset |
| `uint256` | Trial fund amount |

#### Access

Public view function

### `migrateFunds`

Migrates funds to another wallet.

```vyper
@external
def migrateFunds(_toWallet: address, _asset: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_toWallet` | `address` | Destination wallet |
| `_asset` | `address` | Asset to migrate |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Amount migrated |

#### Access

Only callable by Migrator

### `preparePayment`

Prepares payment by withdrawing from yield.

```vyper
@external
def preparePayment(
    _targetAsset: address,
    _legoId: uint256,
    _vaultToken: address,
    _vaultAmount: uint256 = max_value(uint256),
) -> (uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_targetAsset` | `address` | Expected underlying asset |
| `_legoId` | `uint256` | Lego protocol ID |
| `_vaultToken` | `address` | Vault token to withdraw |
| `_vaultAmount` | `uint256` | Amount to withdraw |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Underlying amount received |
| `uint256` | USD value |

#### Access

Only callable by registered UndyHq contracts

### `deregisterAsset`

Removes asset from wallet tracking.

```vyper
@external
def deregisterAsset(_asset: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Asset to deregister |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Success status |

#### Access

Migrator or registered UndyHq contracts

### `recoverNft`

Recovers NFT from wallet.

```vyper
@external
def recoverNft(_collection: address, _nftTokenId: uint256, _recipient: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_collection` | `address` | NFT collection |
| `_nftTokenId` | `uint256` | Token ID |
| `_recipient` | `address` | Recovery recipient |

#### Access

Owner or Switchboard

#### Events Emitted

- `NftRecovered` - Contains collection, token ID, and recipient

## Ownership and Governance Functions

**Note**: UserWalletConfig inherits and exports the complete [Ownership module](../modules/Ownership.md) interface, providing time-locked ownership transfer functionality. These functions are critical for managing control of the wallet configuration. For detailed information about the ownership transfer process and security considerations, refer to the [Ownership Technical Documentation](../modules/Ownership.md).

### `changeOwnership`

Initiates a time-locked ownership transfer.

```vyper
@external
def changeOwnership(_newOwner: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_newOwner` | `address` | The new owner address |

#### Access

Only callable by current owner

#### Events Emitted

- `OwnershipChangeInitiated` - Contains previous owner (indexed), new owner (indexed), and confirmation block

#### Example Usage
```python
# Current owner initiates transfer
wallet_config.changeOwnership(
    new_owner.address,
    sender=current_owner.address
)
```

### `confirmOwnershipChange`

Confirms a pending ownership change after time-lock expires.

```vyper
@external
def confirmOwnershipChange():
```

#### Parameters

*Function has no parameters*

#### Access

Only callable by the pending new owner after time-lock

#### Events Emitted

- `OwnershipChangeConfirmed` - Contains previous owner (indexed), new owner (indexed), initiation block, and confirmation block

#### Example Usage
```python
# Wait for time-lock
boa.env.time_travel(blocks=ownership_timelock)

# New owner confirms
wallet_config.confirmOwnershipChange(sender=new_owner.address)
```

### `cancelOwnershipChange`

Cancels a pending ownership change.

```vyper
@external
def cancelOwnershipChange():
```

#### Parameters

*Function has no parameters*

#### Access

Callable by current owner or security action authorized address

#### Events Emitted

- `OwnershipChangeCancelled` - Contains cancelled owner (indexed), cancelled by (indexed), initiation block, and confirmation block

#### Example Usage
```python
# Owner cancels pending change
wallet_config.cancelOwnershipChange(sender=current_owner.address)
```

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

#### Access

Only callable by current owner

#### Events Emitted

- `OwnershipTimeLockSet` - Contains new time-lock value

#### Example Usage
```python
# Update time-lock to 1000 blocks
wallet_config.setOwnershipTimeLock(
    1000,
    sender=owner.address
)
```

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
|------|------|-------------|
| `bool` | True if an ownership change is pending |

#### Access

Public view function

#### Example Usage
```python
has_pending = wallet_config.hasPendingOwnerChange()
# Returns: True if pendingOwner.confirmBlock != 0
```

### Ownership State Variables

The following state variables are inherited from the [Ownership module](../modules/Ownership.md):

- `owner: address` - Current owner of the wallet configuration
- `ownershipTimeLock: uint256` - Time-lock period for ownership changes
- `pendingOwner: PendingOwnerChange` - Details of pending ownership change
- `MIN_OWNERSHIP_TIMELOCK: uint256` - Minimum allowed time-lock
- `MAX_OWNERSHIP_TIMELOCK: uint256` - Maximum allowed time-lock

## Security Functions

### `setFrozen`

Freezes or unfreezes the wallet.

```vyper
@external
def setFrozen(_isFrozen: bool):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_isFrozen` | `bool` | Freeze state |

#### Access

Owner or security action permission

#### Events Emitted

- `FrozenSet` - Contains freeze state and caller

### `setEjectionMode`

Enables or disables ejection mode for emergency withdrawals.

```vyper
@external
def setEjectionMode(_shouldEject: bool):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_shouldEject` | `bool` | Ejection mode state |

#### Access

Only callable by Switchboard

#### Events Emitted

- `EjectionModeSet` - Contains ejection mode state

### `setLegoAccessForAction`

Sets protocol-specific permissions for lego partners.

```vyper
@external
def setLegoAccessForAction(_legoId: uint256, _action: ActionType) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_legoId` | `uint256` | Lego protocol ID |
| `_action` | `ActionType` | Action type |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Success status |

#### Access

Owner or registered UndyHq contracts

## Backpack Module Management

Functions to update wallet backpack modules:

- `setKernel` - Updates whitelist management module
- `setSentinel` - Updates permission validation module
- `setHighCommand` - Updates manager administration module
- `setPaymaster` - Updates payee management module
- `setChequeBook` - Updates cheque operations module
- `setMigrator` - Updates migration utilities module

All functions follow the same pattern:

```vyper
@external
def set[ModuleName](_[moduleName]: address):
```

#### Access

Only callable by owner with valid backpack item registered in Ledger

## Utility Functions

### `getActionDataBundle`

Returns complete action data bundle for validation.

```vyper
@view
@external
def getActionDataBundle(_legoId: uint256, _signer: address) -> ActionData:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_legoId` | `uint256` | Lego protocol ID |
| `_signer` | `address` | Transaction signer |

#### Returns

| Type | Description |
|------|-------------|
| `ActionData` | Complete action data bundle |

#### Access

Public view function

### `apiVersion`

Returns the contract version.

```vyper
@pure
@external
def apiVersion() -> String[28]:
```

#### Returns

| Type | Description |
|------|-------------|
| `String[28]` | Version string ("0.1.0") |

#### Access

Public pure function

## Internal Mechanisms

### Permission Validation Flow

1. **Signer Validation**: Checks if signer is owner, manager, or billing contract
2. **Lock Check**: Ensures signer is not locked by MissionControl
3. **Whitelist Bypass**: Whitelisted recipients bypass payee validation
4. **Sentinel Validation**: Complex permission logic delegated to Sentinel contract
5. **Period Tracking**: Updates period-based limits and cooldowns

### Registry Management

The contract maintains efficient registries for managers, payees, and whitelist:

1. **Bidirectional Mapping**: Index-to-address and address-to-index mappings
2. **Non-zero Indexing**: Starts at 1 to use 0 as "not registered" indicator
3. **Efficient Removal**: Last item swapped with removed item to maintain continuity
4. **Data Cleanup**: Settings and tracking data cleared on removal

### Trial Fund System

1. **Initial Funding**: Set during deployment for new wallets
2. **Tracking**: Maintains asset and amount
3. **Clawback**: Hatchery can remove trial funds
4. **Protection**: Cannot enter ejection mode with trial funds

### Backpack Module Integration

1. **Modular Design**: Each aspect managed by specialized contract
2. **Access Control**: Only owner can update modules
3. **Validation**: New modules must be registered in Ledger
4. **Separation of Concerns**: Clean interfaces between modules

## Security Considerations

### Access Control Hierarchy
- Owner has full control over configuration
- Managers have limited, configurable permissions
- Backpack modules have specific, limited access
- Registry contracts (UndyHq) have security permissions

### Time-lock Protection
- Configurable delays for sensitive operations
- Prevents rushed changes to critical settings
- Two-step process for additions (initiate → confirm)

### Limit Enforcement
- USD value caps prevent large unauthorized transfers
- Period-based tracking prevents rapid draining
- Transaction cooldowns prevent spam
- Separate limits for managers and payees

### Emergency Features
- Wallet freezing stops all operations
- Ejection mode allows emergency withdrawals
- Trial fund clawback for unused funds
- NFT recovery for stuck assets

## Testing

For comprehensive test examples, see: [`tests/core/userWallet/`](../../../tests/core/userWallet/)