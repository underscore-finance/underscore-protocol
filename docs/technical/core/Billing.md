# Billing Technical Documentation

[📄 View Source Code](../../../contracts/core/Billing.vy)

## Overview

Billing is the pull payment engine for the Underscore Protocol. As a Department contract, it enables authorized payees and cheque recipients to pull payments directly from [UserWallet](../userWallet/UserWallet.md) instances, implementing sophisticated asset discovery and yield withdrawal mechanisms to ensure payment fulfillment while maintaining security through permission validation and amount controls.

**Core Features**:
- **Pull Payment Support**: Enable payees and cheque recipients to pull authorized payments
- **Yield Asset Discovery**: Automatically find and withdraw from yield vaults for payment
- **Asset Management**: Intelligent deregistration of empty assets after payment
- **Permission Validation**: Strict verification of pull payment authorization
- **Buffer Management**: Apply buffers to ensure sufficient withdrawal amounts

The contract implements sophisticated payment logic including multi-source asset aggregation, automatic yield vault unwinding, partial payment support for payees, full payment requirements for cheques, and efficient asset cleanup after transfers.

## System Architecture Diagram

```
+-------------------------------------------------------------------------+
|                                Billing                                  |
+-------------------------------------------------------------------------+
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                    Pull Payment Flow                               | |
|  |                                                                   | |
|  |  1. Validation:                                                   | |
|  |     ├─> Verify caller is authorized payee/cheque recipient        | |
|  |     ├─> Check pull payment permissions in config                  | |
|  |     └─> Ensure wallet is valid user wallet                        | |
|  |                                                                   | |
|  |  2. Asset Discovery:                                               | |
|  |     ├─> Check direct asset balance                                | |
|  |     ├─> If insufficient, search yield vaults                      | |
|  |     └─> Calculate withdrawal amounts with buffer                   | |
|  |                                                                   | |
|  |  3. Yield Withdrawal:                                              | |
|  |     ├─> Find vaults with matching underlying asset                 | |
|  |     ├─> Get price per share from Appraiser                         | |
|  |     ├─> Calculate vault tokens needed                              | |
|  |     └─> Withdraw to underlying asset                               | |
|  |                                                                   | |
|  |  4. Transfer Execution:                                             | |
|  |     ├─> Execute transfer through UserWallet                        | |
|  |     ├─> Payees: Allow partial payments                             | |
|  |     ├─> Cheques: Require full payment                              | |
|  |     └─> Deregister empty assets                                   | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                     Permission Model                               | |
|  |                                                                   | |
|  |  Cheque Recipients:                                                | |
|  |    • ChequeSettings.canBePulled must be true                       | |
|  |    • Individual Cheque.canBePulled must be true                    | |
|  |    • Additional validation in Sentinel                             | |
|  |                                                                   | |
|  |  Payees:                                                           | |
|  |    • GlobalPayeeSettings.canPull must be true                      | |
|  |    • Individual PayeeSettings.canPull must be true                 | |
|  |    • Additional validation in Sentinel                             | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                    Yield Discovery Strategy                        | |
|  |                                                                   | |
|  |  For each registered asset in wallet:                              | |
|  |    1. Check if asset is yield-bearing                              | |
|  |    2. Verify underlying matches payment asset                      | |
|  |    3. Get current price per share                                  | |
|  |    4. Calculate withdrawal amount                                  | |
|  |    5. Add 1% buffer for rounding/fees                              | |
|  |    6. Withdraw and aggregate                                       | |
|  |                                                                   | |
|  |  Optimization:                                                     | |
|  |    • Stop when target amount reached                               | |
|  |    • Batch deregistration of empty assets                          | |
|  |    • Maximum 25 assets deregistered per call                       | |
|  +-------------------------------------------------------------------+ |
+-------------------------------------------------------------------------+
```

## Module Integration

Billing implements the Department interface and integrates:
- `Addys` module for address registry management
- `DeptBasics` module for pause functionality

## Constants

- `HUNDRED_PERCENT: uint256 = 100_00` - 100% in basis points
- `MAX_DEREGISTER_ASSETS: uint256 = 25` - Maximum assets to deregister per payment

## Immutable Variables

- `WETH: address` - Wrapped ETH address
- `ETH: address` - ETH placeholder address

## Constructor

### `__init__`

Initializes Billing with registry and token addresses.

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
billing = Billing.deploy(
    undy_hq.address,
    weth.address,
    "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"  # ETH placeholder
)
```

## Cheque Payment Functions

### `pullPaymentAsCheque`

Allows cheque recipients to pull authorized payments.

```vyper
@external
def pullPaymentAsCheque(_userWallet: address, _paymentAsset: address, _paymentAmount: uint256) -> (uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet to pull payment from |
| `_paymentAsset` | `address` | Asset to receive as payment |
| `_paymentAmount` | `uint256` | Amount to pull (must be exact) |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Amount actually transferred |
| `uint256` | USD value of transfer |

#### Access

Caller must be authorized cheque recipient

#### Events Emitted

- `ChequePaymentPulled` - Contains asset (indexed), amount, usdValue, chequeRecipient (indexed), and userWallet (indexed)

#### Example Usage
```python
# Cheque recipient pulls payment
amount, usd_value = billing.pullPaymentAsCheque(
    user_wallet.address,
    usdc.address,
    cheque_amount,
    sender=recipient
)
```

#### Notes

- Requires full payment amount (no partial payments)
- Automatically withdraws from yield vaults if needed
- Fails if insufficient funds available
- Deregisters empty assets after payment

### `canPullPaymentAsCheque`

Checks if a recipient can pull payment as cheque.

```vyper
@view
@external
def canPullPaymentAsCheque(_userWallet: address, _chequeRecipient: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet to check |
| `_chequeRecipient` | `address` | Potential cheque recipient |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if recipient can pull payment |

#### Access

Public view function

#### Example Usage
```python
# Check before attempting pull
if billing.canPullPaymentAsCheque(wallet, recipient):
    amount, value = billing.pullPaymentAsCheque(
        wallet,
        asset,
        amount
    )
```

## Payee Payment Functions

### `pullPaymentAsPayee`

Allows authorized payees to pull payments.

```vyper
@external
def pullPaymentAsPayee(_userWallet: address, _paymentAsset: address, _paymentAmount: uint256) -> (uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet to pull payment from |
| `_paymentAsset` | `address` | Asset to receive as payment |
| `_paymentAmount` | `uint256` | Requested amount (partial allowed) |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Amount actually transferred |
| `uint256` | USD value of transfer |

#### Access

Caller must be authorized payee

#### Events Emitted

- `PayeePaymentPulled` - Contains asset (indexed), amount, usdValue, payee (indexed), and userWallet (indexed)

#### Example Usage
```python
# Payee pulls available payment
amount, usd_value = billing.pullPaymentAsPayee(
    user_wallet.address,
    dai.address,
    requested_amount,
    sender=payee
)

# Amount may be less than requested if insufficient funds
print(f"Received {amount} (${usd_value})")
```

#### Notes

- Allows partial payments if full amount unavailable
- Automatically withdraws from yield vaults
- Deregisters empty assets after payment

### `canPullPaymentAsPayee`

Checks if a payee can pull payment.

```vyper
@view
@external
def canPullPaymentAsPayee(_userWallet: address, _payee: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User wallet to check |
| `_payee` | `address` | Potential payee |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if payee can pull payment |

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

## Internal Payment Logic

### Pull Payment Process

1. **Direct Balance Check**: First checks if wallet has sufficient direct balance
2. **Yield Discovery**: If insufficient, searches for yield vaults with matching underlying
3. **Withdrawal Calculation**: Calculates vault tokens needed with 1% buffer
4. **Asset Transfer**: Executes transfer through UserWallet contract
5. **Cleanup**: Deregisters assets with zero balance

### Yield Withdrawal Strategy

```
Target Amount = Requested Amount × 101% (1% buffer)

For each yield asset:
  If underlying matches payment asset:
    Vault Tokens Needed = Target / Price Per Share
    Withdraw and aggregate
    Stop if target reached
```

### Permission Validation

**Cheque Recipients**:
- Global `ChequeSettings.canBePulled` must be true
- Individual `Cheque.canBePulled` must be true
- Additional validation occurs in Sentinel

**Payees**:
- Global `GlobalPayeeSettings.canPull` must be true
- Individual `PayeeSettings.canPull` must be true
- Additional validation occurs in Sentinel

## Security Considerations

### Access Control
- Strict validation of caller permissions
- User wallet verification through Ledger
- Configuration checks before payment

### Payment Security
- Cheques require exact payment amounts
- Payees allow partial payments for flexibility
- 1% buffer ensures sufficient withdrawals
- Automatic asset deregistration prevents dust

### State Management
- Nonreentrant guards on payment functions
- Proper ordering of operations
- Clean state after transfers

## Common Integration Patterns

### Cheque Pull Payment
```python
# Recipient checks and pulls cheque payment
if billing.canPullPaymentAsCheque(wallet, recipient.address):
    try:
        amount, usd_value = billing.pullPaymentAsCheque(
            wallet,
            payment_asset,
            cheque_amount,
            sender=recipient
        )
        print(f"Received ${usd_value} cheque payment")
    except:
        print("Insufficient funds for cheque")
```

### Payee Pull Payment
```python
# Payee pulls available funds
if billing.canPullPaymentAsPayee(wallet, payee.address):
    # Request full amount but accept partial
    amount, usd_value = billing.pullPaymentAsPayee(
        wallet,
        payment_asset,
        requested_amount,
        sender=payee
    )
    
    if amount < requested_amount:
        print(f"Partial payment: {amount} of {requested_amount}")
```

### Yield-Aware Payment
```python
# Check if payment will require yield withdrawal
wallet_balance = token.balanceOf(wallet)
if wallet_balance < payment_amount:
    # Billing will automatically find and withdraw from vaults
    amount, value = billing.pullPaymentAsPayee(
        wallet,
        token.address,
        payment_amount
    )
    # Vaults were unwound to fulfill payment
```

### Asset Configuration Check
```python
# Get asset details for payment planning
config = billing.getAssetUsdValueConfig(asset)

if config.isYieldAsset:
    print(f"Yield asset with underlying: {config.underlyingAsset}")
else:
    print(f"Normal asset with {config.decimals} decimals")
```

## Testing

For comprehensive test examples, see: [`tests/core/test_billing.py`](../../../tests/core/test_billing.py)