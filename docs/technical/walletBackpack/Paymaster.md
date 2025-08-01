# Paymaster Technical Documentation

[📄 View Source Code](../../../contracts/core/walletBackpack/Paymaster.vy)

## Overview

Paymaster is the comprehensive payee management module for user wallets in the Underscore Protocol. As a critical wallet backpack item, it provides fine-grained control over payment recipients, enabling wallets to establish trusted payment relationships with configurable limits, time restrictions, and pull payment capabilities while maintaining security through time-locked operations.

**Core Features**:
- **Payee Lifecycle Management**: Add, update, and remove payees with time-delayed activation
- **Flexible Payment Limits**: Configure limits by transaction, period, and lifetime in both USD and token units
- **Pull Payment Support**: Enable payees to pull funds within defined boundaries
- **Two-Tier Addition Process**: Managers can propose payees requiring owner confirmation
- **Asset-Specific Controls**: Restrict payees to specific assets with granular permissions

The contract implements sophisticated validation ensuring payees cannot exceed defined limits, time-locked operations for security, period-based tracking for rate limiting, and comprehensive configuration options for different payment scenarios.

## System Architecture Diagram

```
+-------------------------------------------------------------------------+
|                              Paymaster                                  |
+-------------------------------------------------------------------------+
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                      Payee Permission Tiers                       | |
|  |                                                                   | |
|  |  Owner:                                                          | |
|  |    - Can directly add/update/remove payees                       | |
|  |    - Sets global payee defaults                                  | |
|  |    - Confirms pending payees from managers                       | |
|  |                                                                   | |
|  |  Manager (with permission):                                      | |
|  |    - Can add pending payees (requires owner confirmation)        | |
|  |    - Cannot directly add active payees                           | |
|  |                                                                   | |
|  |  Payee:                                                          | |
|  |    - Can remove themselves                                       | |
|  |    - Can pull payments if enabled                                | |
|  |                                                                   | |
|  |  Security (MissionControl):                                       | |
|  |    - Can remove payees in emergencies                            | |
|  |    - Can cancel pending payees                                   | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                    Payee Configuration Flow                       | |
|  |                                                                   | |
|  |  Direct Addition (Owner):                                         | |
|  |    1. Owner calls addPayee() with settings                       | |
|  |    2. Validates limits and permissions                           | |
|  |    3. Sets activation delay and expiry                           | |
|  |    4. Payee active after startBlock                              | |
|  |                                                                   | |
|  |  Pending Addition (Manager):                                      | |
|  |    1. Manager calls addPendingPayee()                             | |
|  |    2. Creates time-locked pending entry                          | |
|  |    3. Owner confirms after time-lock                             | |
|  |    4. Payee becomes active                                       | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                       Limit Categories                            | |
|  |                                                                   | |
|  |  Unit Limits (Token):         USD Limits:                        | |
|  |   • perTxCap                  • perTxCap                          | |
|  |   • perPeriodCap              • perPeriodCap                      | |
|  |   • lifetimeCap               • lifetimeCap                       | |
|  |                                                                   | |
|  |  Period Controls:             Asset Controls:                     | |
|  |   • periodLength              • primaryAsset                      | |
|  |   • maxNumTxsPerPeriod        • onlyPrimaryAsset                  | |
|  |   • txCooldownBlocks          • failOnZeroPrice                   | |
|  |                                                                   | |
|  |  Pull Payment:                                                    | |
|  |   • canPull - Allows payee to initiate transfers                  | |
|  |   • Requires at least one limit type configured                   | |
|  +-------------------------------------------------------------------+ |
+-------------------------------------------------------------------------+
```

## Constants and Immutables

### Constants
- `LEDGER_ID: uint256 = 1` - Registry ID for Ledger contract
- `MISSION_CONTROL_ID: uint256 = 2` - Registry ID for MissionControl

### Immutable Variables
- `UNDY_HQ: address` - UndyHq registry address
- `MIN_PAYEE_PERIOD: uint256` - Minimum period length for payees
- `MAX_PAYEE_PERIOD: uint256` - Maximum period length for payees
- `MIN_ACTIVATION_LENGTH: uint256` - Minimum active period
- `MAX_ACTIVATION_LENGTH: uint256` - Maximum active period
- `MAX_START_DELAY: uint256` - Maximum delay before activation

## Constructor

### `__init__`

Initializes Paymaster with validation bounds for payee configurations.

```vyper
@deploy
def __init__(
    _undyHq: address,
    _minPayeePeriod: uint256,
    _maxPayeePeriod: uint256,
    _minActivationLength: uint256,
    _maxActivationLength: uint256,
    _maxStartDelay: uint256,
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq registry contract address |
| `_minPayeePeriod` | `uint256` | Minimum period length in blocks |
| `_maxPayeePeriod` | `uint256` | Maximum period length in blocks |
| `_minActivationLength` | `uint256` | Minimum activation period |
| `_maxActivationLength` | `uint256` | Maximum activation period |
| `_maxStartDelay` | `uint256` | Maximum start delay in blocks |

#### Access

Called only during deployment

#### Example Usage
```python
paymaster = Paymaster.deploy(
    undy_hq.address,
    100,    # Min payee period: 100 blocks
    10000,  # Max payee period: 10000 blocks
    1000,   # Min activation: 1000 blocks
    100000, # Max activation: 100000 blocks
    5000    # Max start delay: 5000 blocks
)
```

## Global Settings Functions

### `setGlobalPayeeSettings`

Sets default settings for all payees in a wallet.

```vyper
@external
def setGlobalPayeeSettings(
    _userWallet: address,
    _defaultPeriodLength: uint256,
    _startDelay: uint256,
    _activationLength: uint256,
    _maxNumTxsPerPeriod: uint256,
    _txCooldownBlocks: uint256,
    _failOnZeroPrice: bool,
    _usdLimits: wcs.PayeeLimits,
    _canPayOwner: bool,
    _canPull: bool,
) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet address |
| `_defaultPeriodLength` | `uint256` | Default period for limits |
| `_startDelay` | `uint256` | Default activation delay |
| `_activationLength` | `uint256` | Default active period |
| `_maxNumTxsPerPeriod` | `uint256` | Max transactions per period |
| `_txCooldownBlocks` | `uint256` | Blocks between transactions |
| `_failOnZeroPrice` | `bool` | Fail if asset has no price |
| `_usdLimits` | `PayeeLimits` | Default USD value limits |
| `_canPayOwner` | `bool` | Allow payments to owner |
| `_canPull` | `bool` | Enable pull payments globally |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Success status |

#### Access

Only callable by wallet owner

#### Events Emitted

- `GlobalPayeeSettingsModified` - Contains user (indexed) and all global settings

#### Example Usage
```python
# Set conservative global defaults
usd_limits = PayeeLimits(
    perTxCap=100 * 10**6,      # $100 per tx
    perPeriodCap=1000 * 10**6, # $1k per period
    lifetimeCap=10000 * 10**6  # $10k lifetime
)

success = paymaster.setGlobalPayeeSettings(
    user_wallet.address,
    1000,   # 1000 block periods
    100,    # 100 block start delay
    50000,  # 50000 block activation
    10,     # Max 10 txs per period
    50,     # 50 block cooldown
    True,   # Fail on zero price
    usd_limits,
    False,  # Cannot pay owner
    False   # No pull payments by default
)
```

## Payee Management Functions

### `addPayee`

Adds a new payee with specified limits and permissions.

```vyper
@external
def addPayee(
    _userWallet: address,
    _payee: address,
    _canPull: bool,
    _periodLength: uint256,
    _maxNumTxsPerPeriod: uint256,
    _txCooldownBlocks: uint256,
    _failOnZeroPrice: bool,
    _primaryAsset: address,
    _onlyPrimaryAsset: bool,
    _unitLimits: wcs.PayeeLimits,
    _usdLimits: wcs.PayeeLimits,
    _startDelay: uint256 = 0,
    _activationLength: uint256 = 0,
) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet address |
| `_payee` | `address` | Payee address to add |
| `_canPull` | `bool` | Enable pull payments |
| `_periodLength` | `uint256` | Period for limit tracking |
| `_maxNumTxsPerPeriod` | `uint256` | Max transactions per period |
| `_txCooldownBlocks` | `uint256` | Cooldown between payments |
| `_failOnZeroPrice` | `bool` | Fail if asset has no price |
| `_primaryAsset` | `address` | Primary payment asset |
| `_onlyPrimaryAsset` | `bool` | Restrict to primary asset only |
| `_unitLimits` | `PayeeLimits` | Token amount limits |
| `_usdLimits` | `PayeeLimits` | USD value limits |
| `_startDelay` | `uint256` | Blocks before activation (optional) |
| `_activationLength` | `uint256` | Active period (optional) |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Success status |

#### Access

Only callable by wallet owner

#### Events Emitted

- `PayeeAdded` - Contains user (indexed), payee (indexed), and all configured settings

#### Example Usage
```python
# Add a service provider as payee
unit_limits = PayeeLimits(
    perTxCap=1000 * 10**6,      # 1000 USDC per tx
    perPeriodCap=5000 * 10**6,  # 5000 USDC per period
    lifetimeCap=50000 * 10**6   # 50000 USDC lifetime
)

usd_limits = PayeeLimits(
    perTxCap=1000 * 10**6,      # $1000 per tx
    perPeriodCap=5000 * 10**6,  # $5000 per period
    lifetimeCap=50000 * 10**6   # $50000 lifetime
)

success = paymaster.addPayee(
    user_wallet.address,
    service_provider.address,
    True,           # Can pull payments
    1000,           # 1000 block periods
    5,              # Max 5 txs per period
    100,            # 100 block cooldown
    True,           # Fail on zero price
    usdc.address,   # Primary asset is USDC
    True,           # Only USDC allowed
    unit_limits,
    usd_limits,
    0,              # No additional delay
    100000          # 100000 block activation
)
```

### `updatePayee`

Updates existing payee settings (limits and permissions only).

```vyper
@external
def updatePayee(
    _userWallet: address,
    _payee: address,
    _canPull: bool,
    _periodLength: uint256,
    _maxNumTxsPerPeriod: uint256,
    _txCooldownBlocks: uint256,
    _failOnZeroPrice: bool,
    _primaryAsset: address,
    _onlyPrimaryAsset: bool,
    _unitLimits: wcs.PayeeLimits,
    _usdLimits: wcs.PayeeLimits,
) -> bool:
```

#### Parameters

Same as `addPayee` except no `_startDelay` or `_activationLength`

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Success status |

#### Access

Only callable by wallet owner

#### Events Emitted

- `PayeeUpdated` - Contains user (indexed), payee (indexed), and all updated settings

#### Notes

- Cannot update startBlock or expiryBlock
- Preserves existing activation period

### `removePayee`

Removes a payee from the wallet.

```vyper
@external
def removePayee(_userWallet: address, _payee: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet address |
| `_payee` | `address` | Payee to remove |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Success status |

#### Access

- Wallet owner
- The payee themselves
- MissionControl authorized addresses

#### Events Emitted

- `PayeeRemoved` - Contains user (indexed), payee (indexed), and removedBy (indexed)

#### Example Usage
```python
# Owner removes payee
success = paymaster.removePayee(
    user_wallet.address,
    payee.address,
    sender=owner
)

# Payee removes themselves
success = paymaster.removePayee(
    user_wallet.address,
    payee.address,
    sender=payee
)
```

## Pending Payee Functions

### `addPendingPayee`

Allows managers to propose payees requiring owner confirmation.

```vyper
@external
def addPendingPayee(
    _userWallet: address,
    _payee: address,
    _canPull: bool,
    _periodLength: uint256,
    _maxNumTxsPerPeriod: uint256,
    _txCooldownBlocks: uint256,
    _failOnZeroPrice: bool,
    _primaryAsset: address,
    _onlyPrimaryAsset: bool,
    _unitLimits: wcs.PayeeLimits,
    _usdLimits: wcs.PayeeLimits,
    _startDelay: uint256 = 0,
    _activationLength: uint256 = 0,
) -> bool:
```

#### Parameters

Same as `addPayee`

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Success status |

#### Access

Managers with `canAddPendingPayee` permission

#### Events Emitted

- `PayeePending` - Contains user (indexed), payee (indexed), confirmBlock, addedBy (indexed), and all settings

#### Example Usage
```python
# Manager proposes a new payee
success = paymaster.addPendingPayee(
    user_wallet.address,
    vendor.address,
    False,          # No pull payments
    1000,           # 1000 block periods
    10,             # Max 10 txs per period
    0,              # No cooldown
    False,          # Don't fail on zero price
    empty_address,  # No primary asset
    False,          # Any asset allowed
    empty_limits,   # No unit limits
    usd_limits,     # USD limits only
    sender=manager
)
```

### `confirmPendingPayee`

Owner confirms a pending payee after time-lock.

```vyper
@external
def confirmPendingPayee(_userWallet: address, _payee: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet address |
| `_payee` | `address` | Pending payee to confirm |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Success status |

#### Access

Only callable by wallet owner after time-lock expires

#### Events Emitted

- `PayeePendingConfirmed` - Contains user (indexed), payee (indexed), initiatedBlock, confirmBlock, and confirmedBy (indexed)

#### Example Usage
```python
# Wait for time-lock
boa.env.time_travel(blocks=timelock)

# Owner confirms pending payee
success = paymaster.confirmPendingPayee(
    user_wallet.address,
    vendor.address,
    sender=owner
)
```

### `cancelPendingPayee`

Cancels a pending payee addition.

```vyper
@external
def cancelPendingPayee(_userWallet: address, _payee: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet address |
| `_payee` | `address` | Pending payee to cancel |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Success status |

#### Access

- Wallet owner
- The pending payee
- MissionControl authorized addresses

#### Events Emitted

- `PayeePendingCancelled` - Contains user (indexed), payee (indexed), initiatedBlock, confirmBlock, and cancelledBy (indexed)

## Validation Functions

### `isValidNewPayee`

Validates settings for a new payee.

```vyper
@view
@external
def isValidNewPayee(
    _userWallet: address,
    _payee: address,
    _canPull: bool,
    _periodLength: uint256,
    _maxNumTxsPerPeriod: uint256,
    _txCooldownBlocks: uint256,
    _failOnZeroPrice: bool,
    _primaryAsset: address,
    _onlyPrimaryAsset: bool,
    _unitLimits: wcs.PayeeLimits,
    _usdLimits: wcs.PayeeLimits,
    _startDelay: uint256 = 0,
    _activationLength: uint256 = 0,
) -> bool:
```

#### Parameters

Same as `addPayee`

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if settings are valid |

#### Access

Public view function

### `isValidPayeeUpdate`

Validates settings for updating an existing payee.

```vyper
@view
@external
def isValidPayeeUpdate(
    _userWallet: address,
    _payee: address,
    _canPull: bool,
    _periodLength: uint256,
    _maxNumTxsPerPeriod: uint256,
    _txCooldownBlocks: uint256,
    _failOnZeroPrice: bool,
    _primaryAsset: address,
    _onlyPrimaryAsset: bool,
    _unitLimits: wcs.PayeeLimits,
    _usdLimits: wcs.PayeeLimits,
) -> bool:
```

#### Parameters

Same as `updatePayee`

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if settings are valid |

#### Access

Public view function

### `canAddPendingPayee`

Checks if a caller can add a pending payee.

```vyper
@view
@external
def canAddPendingPayee(_userWallet: address, _payee: address, _caller: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet address |
| `_payee` | `address` | Proposed payee address |
| `_caller` | `address` | Address attempting to add |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if caller can add pending payee |

#### Access

Public view function

### `isValidGlobalPayeeSettings`

Validates global payee settings.

```vyper
@view
@external
def isValidGlobalPayeeSettings(
    _userWallet: address,
    _defaultPeriodLength: uint256,
    _startDelay: uint256,
    _activationLength: uint256,
    _maxNumTxsPerPeriod: uint256,
    _txCooldownBlocks: uint256,
    _failOnZeroPrice: bool,
    _usdLimits: wcs.PayeeLimits,
    _canPayOwner: bool,
    _canPull: bool,
) -> bool:
```

#### Parameters

Same as `setGlobalPayeeSettings`

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if settings are valid |

#### Access

Public view function

## Utility Functions

### `getPayeeConfig`

Retrieves comprehensive data about a payee.

```vyper
@view
@external
def getPayeeConfig(_userWallet: address, _payee: address) -> wcs.PayeeManagementBundle:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet address |
| `_payee` | `address` | Payee address |

#### Returns

| Type | Description |
|------|-------------|
| `PayeeManagementBundle` | Bundle containing configuration and state |

#### Access

Public view function

#### Bundle Contents
- `owner` - Wallet owner address
- `wallet` - User wallet address
- `isRegisteredPayee` - Whether address is a payee
- `isWhitelisted` - Whether address is whitelisted
- `payeeSettings` - Current payee settings
- `globalPayeeSettings` - Global settings
- `timeLock` - Current wallet time-lock
- `walletConfig` - Config contract address

### `createDefaultGlobalPayeeSettings`

Creates recommended global payee settings.

```vyper
@view
@external
def createDefaultGlobalPayeeSettings(
    _defaultPeriodLength: uint256,
    _startDelay: uint256,
    _activationLength: uint256,
) -> wcs.GlobalPayeeSettings:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_defaultPeriodLength` | `uint256` | Default period length |
| `_startDelay` | `uint256` | Default start delay |
| `_activationLength` | `uint256` | Default activation period |

#### Returns

| Type | Description |
|------|-------------|
| `GlobalPayeeSettings` | Populated settings struct |

#### Access

Public view function

#### Notes

Creates conservative defaults with:
- No transaction limits
- No cooldowns
- USD limits empty (no restrictions)
- `canPayOwner` = True
- `canPull` = False
- `failOnZeroPrice` = False

## Internal Validation Logic

### Payee Limits Validation

The contract enforces logical consistency:

1. **Value Hierarchy**:
   - Per-transaction ≤ Per-period ≤ Lifetime
   - Zero values treated as "unlimited"
   - Applies to both unit and USD limits

2. **Pull Payment Requirements**:
   - Must have at least one limit type (unit or USD)
   - Global setting must allow pull payments
   - Prevents unlimited pull access

### Period and Timing Validation

1. **Period Length**:
   - Must be within MIN/MAX_PAYEE_PERIOD
   - Cooldown cannot exceed period length

2. **Activation Timing**:
   - Start delay ≥ wallet time-lock
   - Start delay ≤ MAX_START_DELAY
   - Activation length within bounds

### Asset Controls Validation

1. **Primary Asset Logic**:
   - If `onlyPrimaryAsset` = true, must specify asset
   - Empty address allowed if not restricted

2. **Exclusion Rules**:
   - Cannot add wallet owner as payee
   - Cannot add wallet or config contracts
   - Cannot add already whitelisted addresses

## Security Considerations

### Time-locked Operations
- Direct additions by owner have configurable delay
- Manager additions require owner confirmation after time-lock
- Provides reaction time for unexpected additions

### Limit Enforcement
- Multiple layers of limits (tx, period, lifetime)
- Both token amount and USD value restrictions
- Period-based tracking prevents rapid draining

### Permission Hierarchy
- Only owner can directly add/update payees
- Managers can only propose (pending payees)
- Payees can remove themselves
- MissionControl override for emergencies

### Pull Payment Security
- Requires explicit enablement
- Must have defined limits
- Subject to same validation as push payments
- Can be disabled globally

## Common Integration Patterns

### Basic Payee Setup
```python
# 1. Set global defaults
paymaster.setGlobalPayeeSettings(
    wallet.address,
    default_period=1000,
    start_delay=100,
    activation_length=50000,
    max_txs=10,
    cooldown=0,
    fail_on_zero=False,
    usd_limits=PayeeLimits(0, 0, 0),
    can_pay_owner=True,
    can_pull=False
)

# 2. Add specific payee
paymaster.addPayee(
    wallet.address,
    merchant.address,
    can_pull=False,
    period_length=1000,
    max_txs=5,
    cooldown=100,
    fail_on_zero=True,
    primary_asset=usdc.address,
    only_primary=True,
    unit_limits=PayeeLimits(100e6, 500e6, 5000e6),
    usd_limits=PayeeLimits(100e6, 500e6, 5000e6)
)
```

### Pull Payment Configuration
```python
# Add subscription service with pull capability
paymaster.addPayee(
    wallet.address,
    subscription.address,
    can_pull=True,              # Enable pull
    period_length=30*24*60*4,   # ~30 days
    max_txs=1,                  # Once per period
    cooldown=0,
    fail_on_zero=True,
    primary_asset=usdc.address,
    only_primary=True,
    unit_limits=PayeeLimits(
        perTxCap=10 * 10**6,    # 10 USDC
        perPeriodCap=10 * 10**6,
        lifetimeCap=120 * 10**6 # 1 year
    ),
    usd_limits=PayeeLimits(
        perTxCap=10 * 10**6,
        perPeriodCap=10 * 10**6,
        lifetimeCap=120 * 10**6
    )
)
```

### Manager-Proposed Payee Flow
```python
# 1. Manager proposes payee
paymaster.addPendingPayee(
    wallet.address,
    new_vendor.address,
    can_pull=False,
    period_length=1000,
    max_txs=10,
    cooldown=0,
    fail_on_zero=False,
    primary_asset=empty_address,
    only_primary=False,
    unit_limits=empty_limits,
    usd_limits=usd_only_limits,
    sender=manager
)

# 2. Wait for time-lock
boa.env.time_travel(blocks=timelock)

# 3. Owner confirms
paymaster.confirmPendingPayee(
    wallet.address,
    new_vendor.address,
    sender=owner
)
```

## Testing

For comprehensive test examples, see: [`tests/core/walletBackpack/paymaster/`](../../../tests/core/walletBackpack/paymaster/)