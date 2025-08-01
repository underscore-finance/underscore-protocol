# Sentinel Technical Documentation

[📄 View Source Code](../../../contracts/core/walletBackpack/Sentinel.vy)

## Overview

Sentinel is the validation engine for [UserWallet](../userWallet/UserWallet.md) activity in the Underscore Protocol. As a critical wallet backpack item, it enforces comprehensive permission checks, transaction limits, and USD value restrictions for managers, payees, and cheque payments, ensuring all wallet actions comply with configured security policies before and after execution.

**Core Features**:
- **Pre-Action Validation**: Checks permissions before transaction execution
- **Post-Action Validation**: Enforces USD value limits after price calculation
- **Manager Controls**: Period-based limits, asset restrictions, and action permissions
- **Payee Validation**: Whitelisted addresses, registered payees, and payment limits
- **Cheque Verification**: Time-locked payment validation with period controls

The contract implements sophisticated validation logic including period-based tracking with automatic resets, hierarchical permission systems (individual + global), USD value limits at transaction/period/lifetime levels, and granular action-type permissions for DeFi operations.

## System Architecture Diagram

```
+-------------------------------------------------------------------------+
|                                Sentinel                                 |
+-------------------------------------------------------------------------+
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                    Validation Flow Architecture                   | |
|  |                                                                   | |
|  |  Pre-Action Phase:                                                | |
|  |    1. Identity Check → Owner/Manager/Neither                      | |
|  |    2. Permission Check → Action allowed for role                  | |
|  |    3. Asset Check → Asset in allowed list                         | |
|  |    4. Lego Check → Protocol ID allowed                            | |
|  |    5. Payee Check → Recipient in allowed list                     | |
|  |    6. Cooldown Check → Time since last transaction                | |
|  |    7. Count Check → Transactions in current period                | |
|  |                                                                   | |
|  |  Post-Action Phase:                                               | |
|  |    1. USD Calculation → Get transaction value                     | |
|  |    2. Zero Price Check → Handle missing prices                    | |
|  |    3. Tx Limit Check → Single transaction cap                     | |
|  |    4. Period Limit Check → Current period cap                     | |
|  |    5. Lifetime Limit Check → Total lifetime cap                   | |
|  |    6. Data Update → Record transaction metrics                    | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                       Permission Categories                        | |
|  |                                                                   | |
|  |  Action Types:              Mapped Permissions:                   | |
|  |   • TRANSFER               → canTransfer                          | |
|  |   • PAY_CHEQUE             → canTransfer                          | |
|  |   • EARN_DEPOSIT           → canManageYield                       | |
|  |   • EARN_WITHDRAW          → canManageYield                       | |
|  |   • EARN_REBALANCE         → canManageYield                       | |
|  |   • SWAP                   → canBuyAndSell                        | |
|  |   • MINT_REDEEM            → canBuyAndSell                        | |
|  |   • CONFIRM_MINT_REDEEM    → canBuyAndSell                        | |
|  |   • ADD_COLLATERAL         → canManageDebt                        | |
|  |   • REMOVE_COLLATERAL      → canManageDebt                        | |
|  |   • BORROW                 → canManageDebt                        | |
|  |   • REPAY_DEBT             → canManageDebt                        | |
|  |   • ADD_LIQ                → canManageLiq                         | |
|  |   • REMOVE_LIQ             → canManageLiq                         | |
|  |   • ADD_LIQ_CONC           → canManageLiq                         | |
|  |   • REMOVE_LIQ_CONC        → canManageLiq                         | |
|  |   • REWARDS                → canClaimRewards                      | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                      Period-Based Tracking                         | |
|  |                                                                   | |
|  |  Automatic Reset Logic:                                            | |
|  |    • First transaction initializes period                          | |
|  |    • Period expires → counters reset to 0                          | |
|  |    • New period starts at current block                            | |
|  |                                                                   | |
|  |  Tracked Metrics:                                                  | |
|  |    • numTxsInPeriod - Transaction count                            | |
|  |    • totalUsdValueInPeriod - USD value sum                         | |
|  |    • totalUnitsInPeriod - Token units (payees)                    | |
|  |    • lastTxBlock - For cooldown enforcement                        | |
|  +-------------------------------------------------------------------+ |
+-------------------------------------------------------------------------+
```

## Constants

- `MAX_CONFIG_ASSETS: uint256 = 40` - Maximum allowed assets per configuration
- `MAX_ASSETS: uint256 = 10` - Maximum assets per transaction
- `MAX_LEGOS: uint256 = 10` - Maximum protocol IDs per transaction

## Constructor

### `__init__`

Initializes Sentinel as a stateless validation contract.

```vyper
@deploy
def __init__():
    pass
```

#### Access

Called only during deployment

#### Notes

Sentinel is designed as a pure validation contract with no storage

## Manager Validation Functions

### Pre-Action Validation

#### `canSignerPerformAction`

Validates if a signer can perform a specific action.

```vyper
@view
@external
def canSignerPerformAction(
    _user: address,
    _signer: address,
    _action: ws.ActionType,
    _assets: DynArray[address, MAX_ASSETS] = [],
    _legoIds: DynArray[uint256, MAX_LEGOS] = [],
    _txRecipient: address = empty(address),
) -> bool:
```

##### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User wallet address |
| `_signer` | `address` | Address attempting action |
| `_action` | `ActionType` | Type of action to perform |
| `_assets` | `DynArray[address, MAX_ASSETS]` | Assets involved in transaction |
| `_legoIds` | `DynArray[uint256, MAX_LEGOS]` | Protocol IDs being used |
| `_txRecipient` | `address` | Transaction recipient if applicable |

##### Returns

| Type | Description |
|------|-------------|
| `bool` | True if action is allowed |

##### Access

Public view function

##### Example Usage
```python
# Check if manager can perform swap
can_swap = sentinel.canSignerPerformAction(
    user_wallet.address,
    manager.address,
    ActionType.SWAP,
    [usdc.address, weth.address],
    [uniswap_id],
    empty_address
)

# Check if manager can transfer to payee
can_transfer = sentinel.canSignerPerformAction(
    user_wallet.address,
    manager.address,
    ActionType.TRANSFER,
    [usdc.address],
    [],
    payee.address
)
```

#### `canSignerPerformActionWithConfig`

Validates action with pre-fetched configuration data.

```vyper
@view
@external
def canSignerPerformActionWithConfig(
    _isOwner: bool,
    _isManager: bool,
    _managerData: wcs.ManagerData,
    _config: wcs.ManagerSettings,
    _globalConfig: wcs.GlobalManagerSettings,
    _action: ws.ActionType,
    _assets: DynArray[address, MAX_ASSETS] = [],
    _legoIds: DynArray[uint256, MAX_LEGOS] = [],
    _txRecipient: address = empty(address),
) -> bool:
```

##### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_isOwner` | `bool` | Whether signer is owner |
| `_isManager` | `bool` | Whether signer is manager |
| `_managerData` | `ManagerData` | Manager's period data |
| `_config` | `ManagerSettings` | Manager's settings |
| `_globalConfig` | `GlobalManagerSettings` | Global settings |
| `_action` | `ActionType` | Action type |
| `_assets` | `DynArray[address, MAX_ASSETS]` | Assets involved |
| `_legoIds` | `DynArray[uint256, MAX_LEGOS]` | Protocol IDs |
| `_txRecipient` | `address` | Recipient address |

##### Returns

| Type | Description |
|------|-------------|
| `bool` | True if action is allowed |

##### Access

Public view function

### Post-Action Validation

#### `checkManagerUsdLimits`

Validates USD value limits after transaction.

```vyper
@view
@external
def checkManagerUsdLimits(
    _user: address,
    _manager: address,
    _txUsdValue: uint256,
) -> bool:
```

##### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User wallet address |
| `_manager` | `address` | Manager address |
| `_txUsdValue` | `uint256` | Transaction USD value |

##### Returns

| Type | Description |
|------|-------------|
| `bool` | True if within limits |

##### Access

Public view function

#### `checkManagerUsdLimitsAndUpdateData`

Validates limits and returns updated tracking data.

```vyper
@view
@external
def checkManagerUsdLimitsAndUpdateData(
    _txUsdValue: uint256,
    _specificLimits: wcs.ManagerLimits,
    _globalLimits: wcs.ManagerLimits,
    _managerPeriod: uint256,
    _managerData: wcs.ManagerData,
) -> (bool, wcs.ManagerData):
```

##### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_txUsdValue` | `uint256` | Transaction USD value |
| `_specificLimits` | `ManagerLimits` | Manager's limits |
| `_globalLimits` | `ManagerLimits` | Global limits |
| `_managerPeriod` | `uint256` | Period length |
| `_managerData` | `ManagerData` | Current tracking data |

##### Returns

| Type | Description |
|------|-------------|
| `bool` | Whether transaction is valid |
| `ManagerData` | Updated tracking data |

##### Access

Public view function

##### Example Usage
```python
# Check and update manager data
valid, new_data = sentinel.checkManagerUsdLimitsAndUpdateData(
    tx_usd_value=1000 * 10**6,  # $1000
    specific_limits=manager_limits,
    global_limits=global_limits,
    manager_period=1000,
    manager_data=current_data
)

if valid:
    # Save new_data to storage
    save_manager_data(manager, new_data)
```

## Payee Validation Functions

### `isValidPayee`

Validates if a recipient can receive payment.

```vyper
@view
@external
def isValidPayee(
    _user: address,
    _recipient: address,
    _asset: address,
    _amount: uint256,
    _txUsdValue: uint256,
) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User wallet address |
| `_recipient` | `address` | Payment recipient |
| `_asset` | `address` | Asset being sent |
| `_amount` | `uint256` | Token amount |
| `_txUsdValue` | `uint256` | USD value |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if payment allowed |

#### Access

Public view function

### `isValidPayeeAndGetData`

Validates payee and returns updated tracking data.

```vyper
@view
@external
def isValidPayeeAndGetData(
    _isWhitelisted: bool,
    _isOwner: bool,
    _isPayee: bool,
    _asset: address,
    _amount: uint256,
    _txUsdValue: uint256,
    _config: wcs.PayeeSettings,
    _globalConfig: wcs.GlobalPayeeSettings,
    _payeeData: wcs.PayeeData,
) -> (bool, wcs.PayeeData):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_isWhitelisted` | `bool` | Is recipient whitelisted |
| `_isOwner` | `bool` | Is recipient the owner |
| `_isPayee` | `bool` | Is registered payee |
| `_asset` | `address` | Asset address |
| `_amount` | `uint256` | Token amount |
| `_txUsdValue` | `uint256` | USD value |
| `_config` | `PayeeSettings` | Payee settings |
| `_globalConfig` | `GlobalPayeeSettings` | Global settings |
| `_payeeData` | `PayeeData` | Current tracking data |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Whether payment is valid |
| `PayeeData` | Updated tracking data |

#### Access

Public view function

#### Example Usage
```python
# Validate and update payee data
valid, new_data = sentinel.isValidPayeeAndGetData(
    is_whitelisted=False,
    is_owner=False,
    is_payee=True,
    asset=usdc.address,
    amount=100 * 10**6,
    tx_usd_value=100 * 10**6,
    config=payee_settings,
    global_config=global_settings,
    payee_data=current_data
)
```

## Cheque Validation Functions

### `isValidChequeAndGetData`

Validates cheque payment and returns updated tracking data.

```vyper
@view
@external
def isValidChequeAndGetData(
    _asset: address,
    _amount: uint256,
    _txUsdValue: uint256,
    _cheque: wcs.Cheque,
    _globalConfig: wcs.ChequeSettings,
    _chequeData: wcs.ChequeData,
    _isManager: bool,
) -> (bool, wcs.ChequeData):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Payment asset |
| `_amount` | `uint256` | Payment amount |
| `_txUsdValue` | `uint256` | USD value |
| `_cheque` | `Cheque` | Cheque details |
| `_globalConfig` | `ChequeSettings` | Global settings |
| `_chequeData` | `ChequeData` | Current tracking data |
| `_isManager` | `bool` | Is payer a manager |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Whether payment is valid |
| `ChequeData` | Updated tracking data |

#### Access

Public view function

#### Validation Checks

1. **Cheque Status**: Must be active
2. **Time Window**: Between unlock and expiry blocks
3. **Asset Match**: Payment asset must match cheque
4. **Amount Match**: Payment amount must equal cheque amount
5. **Manager Permission**: If manager, must have permission
6. **Period Limits**: Cooldowns and count limits
7. **USD Caps**: Period and maximum value limits

## Internal Validation Logic

### Manager Permission Mapping

The contract maps action types to specific permissions:

| Action Category | Action Types | Required Permission |
|----------------|--------------|-------------------|
| Transfers | TRANSFER, PAY_CHEQUE | canTransfer |
| Yield | EARN_DEPOSIT, EARN_WITHDRAW, EARN_REBALANCE | canManageYield |
| Trading | SWAP, MINT_REDEEM, CONFIRM_MINT_REDEEM | canBuyAndSell |
| Debt | ADD_COLLATERAL, REMOVE_COLLATERAL, BORROW, REPAY_DEBT | canManageDebt |
| Liquidity | ADD_LIQ, REMOVE_LIQ, ADD_LIQ_CONC, REMOVE_LIQ_CONC | canManageLiq |
| Rewards | REWARDS | canClaimRewards |

### Period Management

All tracking uses automatic period resets:

```python
# Period initialization (first transaction)
if data.periodStartBlock == 0:
    data.periodStartBlock = block.number

# Period expiration check
elif block.number >= data.periodStartBlock + period_length:
    # Reset counters
    data.numTxsInPeriod = 0
    data.totalUsdValueInPeriod = 0
    data.periodStartBlock = block.number
```

### Limit Hierarchy

Limits are checked at multiple levels:

1. **Transaction Limits**:
   - Max transactions per period
   - Cooldown between transactions

2. **USD Value Limits**:
   - Per transaction cap
   - Per period cap
   - Lifetime cap

3. **Unit Limits** (Payees only):
   - Token amount limits for primary asset
   - Same hierarchy as USD limits

## Security Considerations

### Permission Layering
- Owner bypass with `canOwnerManage` flag
- Manager permissions checked at individual and global level
- Most restrictive setting wins

### Zero Price Handling
- `failOnZeroPrice` flag prevents transactions with unknown value
- Critical for preventing limit bypass
- Configurable per manager/payee

### Cooldown Enforcement
- Prevents rapid transaction spam
- Checked using `lastTxBlock + cooldown > current`
- Applies to managers, payees, and cheques

### Recipient Validation
- Whitelisted addresses bypass payee checks
- Owner payments controlled by `canPayOwner`
- Allowed payee lists for managers

### Time Window Security
- Manager active period validation
- Payee activation windows
- Cheque unlock/expiry enforcement

## Common Integration Patterns

### Manager Action Validation
```python
# Pre-action check
if sentinel.canSignerPerformAction(
    wallet, manager, ActionType.SWAP, 
    [token_a, token_b], [dex_id]
):
    # Execute swap
    usd_value = execute_swap(...)
    
    # Post-action validation
    if sentinel.checkManagerUsdLimits(
        wallet, manager, usd_value
    ):
        # Success - update storage
        finalize_transaction()
```

### Payee Payment Flow
```python
# Check if can pay
if sentinel.isValidPayee(
    wallet, recipient, asset, amount, usd_value
):
    # Execute transfer
    transfer_tokens(recipient, asset, amount)
else:
    # Check why failed
    config = get_payee_config(recipient)
    if config.isWhitelisted:
        # Should not fail for whitelisted
        revert("Unexpected failure")
```

### Cheque Payment Validation
```python
# Fetch cheque and settings
cheque = get_cheque(recipient)
settings = get_cheque_settings()
data = get_cheque_data()

# Validate payment
valid, new_data = sentinel.isValidChequeAndGetData(
    asset, amount, usd_value,
    cheque, settings, data,
    is_manager=True
)

if valid:
    # Pay cheque and update data
    pay_cheque(cheque)
    save_cheque_data(new_data)
```

### Period Reset Handling
```python
# Manager data updates automatically
manager_data = get_manager_data(manager)
period = get_manager_period()

# Sentinel handles reset internally
valid, updated = sentinel.checkManagerUsdLimitsAndUpdateData(
    usd_value, limits, global_limits,
    period, manager_data
)

# Save updated data with reset applied
save_manager_data(manager, updated)
```

## Testing

For comprehensive test examples, see: [`tests/core/walletBackpack/sentinel/`](../../../tests/core/walletBackpack/sentinel/)