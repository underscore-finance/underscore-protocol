# ChequeBook Technical Documentation

[📄 View Source Code](../../../contracts/core/walletBackpack/ChequeBook.vy)

## Overview

ChequeBook is the comprehensive cheque management module for user wallets in the Underscore Protocol. As a critical wallet backpack item, it enables wallets to create time-locked payment promises (cheques) with sophisticated controls over amounts, timing, and permissions while maintaining security through USD value thresholds and period-based rate limiting.

**Core Features**:
- **Time-locked Cheques**: Create payment promises with unlock and expiry times
- **USD Value Controls**: Automatic delays for high-value cheques exceeding thresholds
- **Period-based Limits**: Track and limit cheque creation and payment by period
- **Manager Permissions**: Allow managers to create cheques with proper authorization
- **Pull Payment Support**: Enable recipients to pull funds when cheques unlock

The contract implements sophisticated validation ensuring cheques cannot exceed defined limits, automatic time-locking for expensive payments, flexible configuration for different payment scenarios, and comprehensive tracking of cheque creation and payment metrics.

## System Architecture Diagram

```
+-------------------------------------------------------------------------+
|                              ChequeBook                                 |
+-------------------------------------------------------------------------+
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                      Cheque Lifecycle                             | |
|  |                                                                   | |
|  |  1. Creation:                                                     | |
|  |     ├─> Validate creator permissions (owner/manager)             | |
|  |     ├─> Check recipient not whitelisted                          | |
|  |     ├─> Get USD value from Appraiser                             | |
|  |     ├─> Apply limits and cooldowns                               | |
|  |     └─> Set unlock/expiry blocks                                 | |
|  |                                                                   | |
|  |  2. Time-lock Period:                                             | |
|  |     ├─> Standard delay: user-defined unlock blocks               | |
|  |     └─> Expensive delay: auto-applied for high USD values        | |
|  |                                                                   | |
|  |  3. Active Period (after unlock, before expiry):                  | |
|  |     ├─> Owner can pay                                             | |
|  |     ├─> Managers can pay (if permitted)                           | |
|  |     └─> Recipients can pull (if permitted)                        | |
|  |                                                                   | |
|  |  4. Expiration:                                                   | |
|  |     └─> Cheque becomes invalid if not paid                       | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                    Permission Structure                           | |
|  |                                                                   | |
|  |  Creation Permissions:                                            | |
|  |   • Owner: Always can create                                      | |
|  |   • Manager: Requires canCreateCheque + global setting            | |
|  |                                                                   | |
|  |  Payment Permissions:                                             | |
|  |   • canManagerPay: Allows managers to pay this cheque             | |
|  |   • canBePulled: Allows recipient to pull payment                 | |
|  |                                                                   | |
|  |  Cancellation:                                                    | |
|  |   • Owner: Can always cancel                                      | |
|  |   • MissionControl: Emergency cancellation                        | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                      Limit Categories                             | |
|  |                                                                   | |
|  |  Creation Limits:                   Payment Limits:               | |
|  |   • maxNumActiveCheques             • perPeriodPaidUsdCap        | |
|  |   • maxChequeUsdValue               • maxNumChequesPaidPerPeriod  | |
|  |   • perPeriodCreatedUsdCap          • payCooldownBlocks           | |
|  |   • maxNumChequesCreatedPerPeriod                                 | |
|  |   • createCooldownBlocks                                          | |
|  |                                                                   | |
|  |  Timing Controls:                   Asset Controls:               | |
|  |   • instantUsdThreshold             • allowedAssets[]             | |
|  |   • expensiveDelayBlocks                                          | |
|  |   • defaultExpiryBlocks                                           | |
|  |   • periodLength                                                  | |
|  +-------------------------------------------------------------------+ |
+-------------------------------------------------------------------------+
```

## Constants and Immutables

### Constants
- `LEDGER_ID: uint256 = 1` - Registry ID for Ledger contract
- `MISSION_CONTROL_ID: uint256 = 2` - Registry ID for MissionControl
- `APPRAISER_ID: uint256 = 7` - Registry ID for Appraiser
- `MAX_CONFIG_ASSETS: uint256 = 40` - Maximum allowed assets

### Immutable Variables
- `UNDY_HQ: address` - UndyHq registry address
- `MIN_CHEQUE_PERIOD: uint256` - Minimum period length
- `MAX_CHEQUE_PERIOD: uint256` - Maximum period length
- `MIN_EXPENSIVE_CHEQUE_DELAY: uint256` - Minimum delay for expensive cheques
- `MAX_UNLOCK_BLOCKS: uint256` - Maximum unlock delay
- `MAX_EXPIRY_BLOCKS: uint256` - Maximum active duration

## Constructor

### `__init__`

Initializes ChequeBook with validation bounds for cheque configurations.

```vyper
@deploy
def __init__(
    _undyHq: address,
    _minChequePeriod: uint256,
    _maxChequePeriod: uint256,
    _minExpensiveChequeDelay: uint256,
    _maxUnlockBlocks: uint256,
    _maxExpiryBlocks: uint256,
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq registry contract address |
| `_minChequePeriod` | `uint256` | Minimum period length in blocks |
| `_maxChequePeriod` | `uint256` | Maximum period length in blocks |
| `_minExpensiveChequeDelay` | `uint256` | Minimum delay for expensive cheques |
| `_maxUnlockBlocks` | `uint256` | Maximum unlock delay allowed |
| `_maxExpiryBlocks` | `uint256` | Maximum active duration allowed |

#### Access

Called only during deployment

#### Example Usage
```python
cheque_book = ChequeBook.deploy(
    undy_hq.address,
    100,    # Min cheque period: 100 blocks
    10000,  # Max cheque period: 10000 blocks
    500,    # Min expensive delay: 500 blocks
    50000,  # Max unlock: 50000 blocks
    100000  # Max expiry: 100000 blocks
)
```

## Cheque Management Functions

### `createCheque`

Creates a new cheque with specified parameters and time-locks.

```vyper
@external
def createCheque(
    _userWallet: address,
    _recipient: address,
    _asset: address,
    _amount: uint256,
    _unlockNumBlocks: uint256,
    _expiryNumBlocks: uint256,
    _canManagerPay: bool,
    _canBePulled: bool,
) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet creating the cheque |
| `_recipient` | `address` | Cheque recipient address |
| `_asset` | `address` | Asset for payment |
| `_amount` | `uint256` | Payment amount |
| `_unlockNumBlocks` | `uint256` | Blocks until cheque unlocks |
| `_expiryNumBlocks` | `uint256` | Blocks from unlock to expiry (0 uses default) |
| `_canManagerPay` | `bool` | Allow managers to pay this cheque |
| `_canBePulled` | `bool` | Allow recipient to pull payment |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Success status |

#### Access

- Wallet owner
- Managers with `canCreateCheque` permission (if enabled globally)

#### Events Emitted

- `ChequeCreated` - Contains user (indexed), recipient (indexed), asset, amount, usdValue, unlockBlock, expiryBlock, canManagerPay, canBePulled, and creator (indexed)

#### Example Usage
```python
# Create a cheque for service payment
success = cheque_book.createCheque(
    user_wallet.address,
    service_provider.address,
    usdc.address,
    1000 * 10**6,     # 1000 USDC
    1000,             # Unlock after 1000 blocks
    10000,            # Active for 10000 blocks after unlock
    True,             # Managers can pay
    False,            # No pull payment
    sender=owner
)

# Create instant small cheque
success = cheque_book.createCheque(
    user_wallet.address,
    vendor.address,
    usdc.address,
    50 * 10**6,       # 50 USDC (below instant threshold)
    0,                # Immediate unlock
    5000,             # Active for 5000 blocks
    False,            # Only owner can pay
    True,             # Recipient can pull
    sender=owner
)
```

#### Notes

- Recipients cannot be whitelisted addresses
- High USD value cheques automatically get additional delay
- Replaces existing cheque for same recipient if one exists
- Subject to period-based creation limits

### `cancelCheque`

Cancels an active cheque.

```vyper
@external
def cancelCheque(_userWallet: address, _recipient: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet address |
| `_recipient` | `address` | Recipient of cheque to cancel |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Success status |

#### Access

- Wallet owner
- MissionControl authorized addresses

#### Events Emitted

- `ChequeCancelled` - Contains user (indexed), recipient (indexed), asset, amount, usdValue, unlockBlock, expiryBlock, canManagerPay, canBePulled, and cancelledBy (indexed)

#### Example Usage
```python
# Owner cancels cheque
success = cheque_book.cancelCheque(
    user_wallet.address,
    recipient.address,
    sender=owner
)

# Security team cancels suspicious cheque
success = cheque_book.cancelCheque(
    user_wallet.address,
    suspicious_recipient.address,
    sender=security_admin
)
```

## Cheque Settings Functions

### `setChequeSettings`

Configures global cheque settings for a wallet.

```vyper
@external
def setChequeSettings(
    _userWallet: address,
    _maxNumActiveCheques: uint256,
    _maxChequeUsdValue: uint256,
    _instantUsdThreshold: uint256,
    _perPeriodPaidUsdCap: uint256,
    _maxNumChequesPaidPerPeriod: uint256,
    _payCooldownBlocks: uint256,
    _perPeriodCreatedUsdCap: uint256,
    _maxNumChequesCreatedPerPeriod: uint256,
    _createCooldownBlocks: uint256,
    _periodLength: uint256,
    _expensiveDelayBlocks: uint256,
    _defaultExpiryBlocks: uint256,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
    _canManagersCreateCheques: bool,
    _canManagerPay: bool,
    _canBePulled: bool,
) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet address |
| `_maxNumActiveCheques` | `uint256` | Maximum concurrent active cheques |
| `_maxChequeUsdValue` | `uint256` | Maximum USD value per cheque |
| `_instantUsdThreshold` | `uint256` | USD value requiring delay |
| `_perPeriodPaidUsdCap` | `uint256` | USD payment cap per period |
| `_maxNumChequesPaidPerPeriod` | `uint256` | Max cheques paid per period |
| `_payCooldownBlocks` | `uint256` | Cooldown between payments |
| `_perPeriodCreatedUsdCap` | `uint256` | USD creation cap per period |
| `_maxNumChequesCreatedPerPeriod` | `uint256` | Max cheques created per period |
| `_createCooldownBlocks` | `uint256` | Cooldown between creations |
| `_periodLength` | `uint256` | Period length for limits |
| `_expensiveDelayBlocks` | `uint256` | Delay for expensive cheques |
| `_defaultExpiryBlocks` | `uint256` | Default expiry duration |
| `_allowedAssets` | `DynArray[address, MAX_CONFIG_ASSETS]` | Allowed payment assets |
| `_canManagersCreateCheques` | `bool` | Allow managers to create |
| `_canManagerPay` | `bool` | Allow manager payments globally |
| `_canBePulled` | `bool` | Allow pull payments globally |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Success status |

#### Access

Only callable by wallet owner

#### Events Emitted

- `ChequeSettingsModified` - Contains user (indexed) and all settings parameters

#### Example Usage
```python
# Conservative settings for personal wallet
success = cheque_book.setChequeSettings(
    user_wallet.address,
    maxNumActiveCheques=10,
    maxChequeUsdValue=1000 * 10**6,      # $1000 max
    instantUsdThreshold=100 * 10**6,     # $100 threshold
    perPeriodPaidUsdCap=5000 * 10**6,    # $5000/period paid
    maxNumChequesPaidPerPeriod=20,
    payCooldownBlocks=50,
    perPeriodCreatedUsdCap=10000 * 10**6, # $10000/period created
    maxNumChequesCreatedPerPeriod=50,
    createCooldownBlocks=10,
    periodLength=1000,                    # 1000 block periods
    expensiveDelayBlocks=500,             # 500 block delay
    defaultExpiryBlocks=10000,            # 10000 block expiry
    allowedAssets=[usdc.address, dai.address],
    canManagersCreateCheques=False,
    canManagerPay=True,
    canBePulled=False
)

# Business wallet with manager permissions
success = cheque_book.setChequeSettings(
    business_wallet.address,
    maxNumActiveCheques=100,
    maxChequeUsdValue=10000 * 10**6,
    instantUsdThreshold=500 * 10**6,
    perPeriodPaidUsdCap=0,                # No limit
    maxNumChequesPaidPerPeriod=0,
    payCooldownBlocks=0,
    perPeriodCreatedUsdCap=0,
    maxNumChequesCreatedPerPeriod=0,
    createCooldownBlocks=0,
    periodLength=10000,
    expensiveDelayBlocks=1000,
    defaultExpiryBlocks=50000,
    allowedAssets=[],                     # Any asset
    canManagersCreateCheques=True,
    canManagerPay=True,
    canBePulled=True
)
```

## Validation Functions

### `canCreateCheque`

Checks if an address can create cheques.

```vyper
@view
@external
def canCreateCheque(
    _isCreatorOwner: bool,
    _isCreatorManager: bool,
    _canManagersCreateCheques: bool,
    _managerSettings: wcs.ManagerSettings,
) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_isCreatorOwner` | `bool` | Is creator the owner |
| `_isCreatorManager` | `bool` | Is creator a manager |
| `_canManagersCreateCheques` | `bool` | Global manager permission |
| `_managerSettings` | `ManagerSettings` | Manager's settings |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if can create cheques |

#### Access

Public view function

### `isValidNewCheque`

Validates new cheque parameters.

```vyper
@view
@external
def isValidNewCheque(
    _wallet: address,
    _walletConfig: address,
    _owner: address,
    _isRecipientOnWhitelist: bool,
    _chequeSettings: wcs.ChequeSettings,
    _chequeData: wcs.ChequeData,
    _isExistingCheque: bool,
    _numActiveCheques: uint256,
    _timeLock: uint256,
    _recipient: address,
    _asset: address,
    _amount: uint256,
    _unlockNumBlocks: uint256,
    _expiryNumBlocks: uint256,
    _canManagerPay: bool,
    _canBePulled: bool,
    _creator: address,
    _usdValue: uint256,
) -> bool:
```

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if cheque parameters are valid |

#### Access

Public view function

### `isValidChequeSettings`

Validates cheque settings configuration.

```vyper
@view
@external
def isValidChequeSettings(
    _maxNumActiveCheques: uint256,
    _maxChequeUsdValue: uint256,
    _instantUsdThreshold: uint256,
    _perPeriodPaidUsdCap: uint256,
    _maxNumChequesPaidPerPeriod: uint256,
    _payCooldownBlocks: uint256,
    _perPeriodCreatedUsdCap: uint256,
    _maxNumChequesCreatedPerPeriod: uint256,
    _createCooldownBlocks: uint256,
    _periodLength: uint256,
    _expensiveDelayBlocks: uint256,
    _defaultExpiryBlocks: uint256,
    _timeLock: uint256,
) -> bool:
```

#### Parameters

Same as `setChequeSettings` plus `_timeLock`

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if settings are valid |

#### Access

Public view function

## Utility Functions

### `getChequeConfig`

Retrieves comprehensive cheque configuration data.

```vyper
@view
@external
def getChequeConfig(_userWallet: address, _creator: address, _recipient: address) -> wcs.ChequeManagementBundle:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet address |
| `_creator` | `address` | Cheque creator address |
| `_recipient` | `address` | Cheque recipient address |

#### Returns

| Type | Description |
|------|-------------|
| `ChequeManagementBundle` | Bundle containing configuration and state |

#### Access

Public view function

#### Bundle Contents
- `wallet` - User wallet address
- `walletConfig` - Config contract address
- `owner` - Wallet owner address
- `isRecipientOnWhitelist` - Whether recipient is whitelisted
- `isCreatorManager` - Whether creator is a manager
- `managerSettings` - Creator's manager settings
- `chequeSettings` - Global cheque settings
- `chequeData` - Period tracking data
- `isExistingCheque` - Whether cheque exists for recipient
- `numActiveCheques` - Current active cheque count
- `timeLock` - Wallet time-lock setting

### `createDefaultChequeSettings`

Creates recommended default cheque settings.

```vyper
@view
@external
def createDefaultChequeSettings(
    _maxNumActiveCheques: uint256,
    _instantUsdThreshold: uint256,
    _periodLength: uint256,
    _expensiveDelayBlocks: uint256,
    _defaultExpiryBlocks: uint256,
) -> wcs.ChequeSettings:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_maxNumActiveCheques` | `uint256` | Maximum active cheques |
| `_instantUsdThreshold` | `uint256` | Threshold for delays |
| `_periodLength` | `uint256` | Period for tracking |
| `_expensiveDelayBlocks` | `uint256` | Delay for expensive |
| `_defaultExpiryBlocks` | `uint256` | Default expiry |

#### Returns

| Type | Description |
|------|-------------|
| `ChequeSettings` | Populated settings struct |

#### Access

Public view function

#### Notes

Creates conservative defaults with:
- No USD caps (unlimited)
- No cooldowns
- No creation/payment limits per period
- Empty allowed assets (any asset)
- `canManagersCreateCheques` = False
- `canManagerPay` = True
- `canBePulled` = False

## Internal Validation Logic

### USD Value Thresholds

The contract implements automatic delays for expensive cheques:

1. **Instant Threshold Check**:
   - If cheque USD value > `instantUsdThreshold`
   - Additional delay applied automatically

2. **Delay Calculation**:
   - Uses `expensiveDelayBlocks` if set
   - Falls back to wallet `timeLock` if not set
   - Applied as minimum unlock time

### Period-based Tracking

The contract maintains period-based metrics:

1. **Period Reset**:
   - Tracks start block of current period
   - Resets counters when period expires
   - Separate tracking for creation and payment

2. **Tracked Metrics**:
   - Number of cheques created/paid
   - Total USD value created/paid
   - Last creation/payment block

### Validation Rules

1. **Recipient Validation**:
   - Cannot be whitelisted address
   - Cannot be wallet/owner/config
   - Must be valid address

2. **Asset Validation**:
   - Must be in allowed assets (if restricted)
   - Cannot be zero address
   - Amount must be non-zero

3. **Timing Validation**:
   - Unlock blocks ≤ MAX_UNLOCK_BLOCKS
   - Active duration ≤ MAX_EXPIRY_BLOCKS
   - Cooldowns ≤ period length

4. **Permission Validation**:
   - Global settings override individual
   - Manager must be active
   - Proper permission flags required

## Security Considerations

### Time-lock Protection
- Expensive cheques get automatic delays
- Minimum delays enforced by configuration
- Cannot bypass USD threshold delays

### Creation Controls
- Managers need explicit permission
- Subject to cooldowns between creations
- Period-based limits prevent spam

### Payment Security
- Only authorized parties can pay
- Pull payments require explicit permission
- Expired cheques become invalid

### Emergency Controls
- Owner can always cancel cheques
- MissionControl override capability
- No funds locked during cheque period

## Common Integration Patterns

### Basic Cheque Creation
```python
# 1. Configure settings
cheque_book.setChequeSettings(
    wallet.address,
    maxNumActiveCheques=20,
    maxChequeUsdValue=5000 * 10**6,
    instantUsdThreshold=200 * 10**6,
    perPeriodPaidUsdCap=0,
    maxNumChequesPaidPerPeriod=0,
    payCooldownBlocks=0,
    perPeriodCreatedUsdCap=25000 * 10**6,
    maxNumChequesCreatedPerPeriod=100,
    createCooldownBlocks=10,
    periodLength=5000,
    expensiveDelayBlocks=1000,
    defaultExpiryBlocks=20000,
    allowedAssets=[usdc.address, dai.address],
    canManagersCreateCheques=False,
    canManagerPay=True,
    canBePulled=False
)

# 2. Create standard cheque
cheque_book.createCheque(
    wallet.address,
    merchant.address,
    usdc.address,
    150 * 10**6,    # 150 USDC
    100,            # 100 block delay
    0,              # Use default expiry
    True,           # Managers can pay
    False           # No pull
)
```

### Automated Payment System
```python
# Configure for automated payments
cheque_book.setChequeSettings(
    wallet.address,
    maxNumActiveCheques=50,
    maxChequeUsdValue=1000 * 10**6,
    instantUsdThreshold=100 * 10**6,
    perPeriodPaidUsdCap=10000 * 10**6,
    maxNumChequesPaidPerPeriod=200,
    payCooldownBlocks=5,
    perPeriodCreatedUsdCap=50000 * 10**6,
    maxNumChequesCreatedPerPeriod=500,
    createCooldownBlocks=0,
    periodLength=10000,
    expensiveDelayBlocks=500,
    defaultExpiryBlocks=50000,
    allowedAssets=[],
    canManagersCreateCheques=True,
    canManagerPay=True,
    canBePulled=True
)

# Manager creates pull-enabled cheque
cheque_book.createCheque(
    wallet.address,
    subscription.address,
    usdc.address,
    30 * 10**6,     # 30 USDC monthly
    0,              # Immediate
    30*24*60*4,     # ~30 days active
    False,          # Only owner pays
    True,           # Recipient can pull
    sender=manager
)
```

### High-value Payment with Delay
```python
# Create high-value cheque (auto-delayed)
cheque_book.createCheque(
    wallet.address,
    contractor.address,
    usdc.address,
    50000 * 10**6,  # $50k (above threshold)
    1000,           # User delay: 1000 blocks
    100000,         # Long expiry
    False,          # Owner only
    False,          # No pull
    sender=owner
)
# Actual unlock = max(1000, expensiveDelayBlocks)
```

## Testing

For comprehensive test examples, see: [`tests/core/walletBackpack/chequeBook/`](../../../tests/core/walletBackpack/chequeBook/)