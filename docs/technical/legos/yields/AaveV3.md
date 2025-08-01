# AaveV3 Technical Documentation

[📄 View Source Code](../../../../contracts/legos/yield/AaveV3.vy)

## Overview

AaveV3 is a Yield Lego partner that integrates the Underscore Protocol with Aave Protocol V3, the leading decentralized lending and borrowing platform. It provides seamless access to Aave's interest-bearing aTokens, enabling users to earn yield on their deposited assets through Aave's lending pools. The integration handles automatic aToken registration, rebasing token support, and efficient deposit/withdrawal operations while maintaining full compatibility with Aave V3's security model.

**Core Features**:
- **Interest-Bearing Deposits**: Convert assets into aTokens that automatically accrue interest
- **Rebasing Token Support**: Full support for Aave's rebasing aTokens with 1:1 conversion
- **Automatic Registration**: Dynamic discovery and registration of new aToken opportunities
- **Direct Integration**: Efficient integration with Aave V3 Pool for minimal gas costs
- **Comprehensive Tracking**: USD value calculation and yield tracking for all positions

Built with modular architecture using Addys and YieldLegoData modules, AaveV3 provides secure access to one of DeFi's most trusted lending protocols while maintaining the operational standards and security patterns of the Underscore Protocol.

## Architecture & Modules

AaveV3 uses a modular architecture combining address management and yield data handling:

### Addys Module
- **Location**: `contracts/modules/Addys.vy`
- **Purpose**: Provides protocol-wide address lookups and registry access
- **Documentation**: See [Addys Technical Documentation](../../modules/Addys.md)
- **Key Features**:
  - Connection to UndyHq for protocol addresses
  - Access to Appraiser for USD valuations
  - Cached address lookups for gas efficiency

### YieldLegoData Module
- **Location**: `contracts/modules/YieldLegoData.vy`
- **Purpose**: Manages yield protocol data and vault relationships
- **Documentation**: See [YieldLegoData Technical Documentation](../../modules/YieldLegoData.md)
- **Key Features**:
  - Asset to vault token mappings
  - Vault registration and discovery
  - Pause functionality for security

### Module Initialization
```vyper
initializes: addys
initializes: yld[addys := addys]
```

## System Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                         AaveV3 Contract                            │
├────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐         ┌──────────────────────────────┐  │
│  │    Addys Module     │         │   YieldLegoData Module       │  │
│  │                     │         │                              │  │
│  │ • Protocol addrs    │         │ • Asset opportunities        │  │
│  │ • Registry access   │         │ • Vault token mappings       │  │
│  │ • Appraiser access  │         │ • Registration tracking      │  │
│  └─────────────────────┘         └──────────────────────────────┘  │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Core Capabilities                         │  │
│  │                                                              │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │  │
│  │  │  Yield Deposits │  │   Withdrawals   │  │ Token Query │  │  │
│  │  │                 │  │                 │  │             │  │  │
│  │  │ • Supply assets │  │ • Redeem aTokens│  │ • Validate  │  │  │
│  │  │ • Receive      │  │ • Receive assets│  │   aTokens   │  │  │
│  │  │   aTokens      │  │ • Auto-register │  │ • Get asset │  │  │
│  │  │ • 1:1 rebasing │  │ • Max withdrawal│  │ • USD value │  │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                               │
                               v
┌────────────────────────────────────────────────────────────────────┐
│                      Aave V3 Integration                           │
│                                                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │    Aave Pool     │  │  Data Provider   │  │    aTokens      │  │
│  │                  │  │                  │  │                 │  │
│  │ • Supply()       │  │ • Token registry │  │ • Rebasing      │  │
│  │ • Withdraw()     │  │ • Reserve data   │  │ • Interest      │  │
│  │ • Direct calls   │  │ • Debt tracking  │  │ • 1:1 with      │  │
│  │                  │  │                  │  │   underlying    │  │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

## Data Structures

### TokenData Struct
Aave's token information structure:
```vyper
struct TokenData:
    symbol: String[32]      # Token symbol
    tokenAddress: address   # aToken address
```

## State Variables

### Immutable Protocol Addresses
- `AAVE_V3_POOL: public(immutable(address))` - Aave V3 lending pool contract
- `AAVE_V3_ADDRESS_PROVIDER: public(immutable(address))` - Aave V3 address provider

### Constants
- `MAX_ATOKENS: constant(uint256) = 40` - Maximum aTokens to query
- `MAX_TOKEN_PATH: constant(uint256) = 5` - Maximum tokens in path (unused)

## Constructor

### `__init__`

Initializes AaveV3 with Underscore Protocol and Aave V3 connections.

```vyper
@deploy
def __init__(
    _undyHq: address,
    _aaveV3: address,
    _addressProvider: address,
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq contract address for Underscore Protocol |
| `_aaveV3` | `address` | Aave V3 Pool contract address |
| `_addressProvider` | `address` | Aave V3 Address Provider contract |

#### Returns

*Constructor does not return any values*

#### Access

Called only during contract deployment

#### Example Usage
```python
aave_v3_lego = boa.load(
    "contracts/legos/yield/AaveV3.vy",
    undy_hq.address,
    aave_pool.address,
    aave_provider.address
)
```

#### Notes

- Validates all addresses are non-empty
- Initializes modules without pausing

## Capability Functions

### `hasCapability`

Indicates which action types this Lego supports.

```vyper
@view
@external
def hasCapability(_action: ws.ActionType) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_action` | `ws.ActionType` | The action type to check |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if the action is supported |

#### Supported Actions

- `EARN_DEPOSIT` - Deposit assets to earn yield
- `EARN_WITHDRAW` - Withdraw assets from yield

### `getRegistries`

Returns the Aave V3 registry addresses.

```vyper
@view
@external
def getRegistries() -> DynArray[address, 10]:
```

#### Returns

| Type | Description |
|------|-------------|
| `DynArray[address, 10]` | Array containing Aave Pool and Address Provider |

### `isRebasing`

Indicates if this protocol uses rebasing tokens.

```vyper
@view
@external
def isRebasing() -> bool:
```

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Always True - Aave V3 uses rebasing aTokens |

## Yield Functions

### `depositForYield`

Deposits assets into Aave V3 to earn yield.

```vyper
@external
def depositForYield(
    _asset: address,
    _amount: uint256,
    _vaultAddr: address,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, address, uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Asset to deposit |
| `_amount` | `uint256` | Amount to deposit |
| `_vaultAddr` | `address` | Expected aToken address (optional validation) |
| `_extraData` | `bytes32` | Additional data (unused) |
| `_recipient` | `address` | Address to receive aTokens |
| `_miniAddys` | `ws.MiniAddys` | Protocol addresses struct |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Actual amount deposited |
| `address` | aToken address received |
| `uint256` | Amount of aTokens received (1:1 with deposit) |
| `uint256` | USD value of deposit |

#### Access

- Contract must not be paused
- Open to all callers

#### Events Emitted

- `AaveV3Deposit` - Contains deposit details including asset, aToken, amounts, and USD value

#### Example Usage
```python
# Deposit USDC to Aave V3
amount_deposited, atoken, atokens_received, usd_value = aave_v3_lego.depositForYield(
    usdc.address,
    1000 * 10**6,  # 1000 USDC
    aUsdc.address,  # Optional validation
    empty(bytes32),
    user.address
)
```

#### Notes

- Automatically registers new aToken opportunities
- aTokens are sent directly to recipient
- Refunds any unused deposit amount
- 1:1 conversion between asset and aToken

### `withdrawFromYield`

Withdraws assets from Aave V3 by redeeming aTokens.

```vyper
@external
def withdrawFromYield(
    _vaultToken: address,
    _amount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, address, uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | aToken to redeem |
| `_amount` | `uint256` | Amount of aTokens to redeem |
| `_extraData` | `bytes32` | Additional data (unused) |
| `_recipient` | `address` | Address to receive underlying assets |
| `_miniAddys` | `ws.MiniAddys` | Protocol addresses struct |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Amount of aTokens redeemed |
| `address` | Underlying asset address |
| `uint256` | Amount of assets received |
| `uint256` | USD value of withdrawal |

#### Access

- Contract must not be paused
- Open to all callers

#### Events Emitted

- `AaveV3Withdrawal` - Contains withdrawal details including asset, aToken, amounts, and USD value

#### Example Usage
```python
# Withdraw USDC from Aave V3
atokens_burned, asset, amount_received, usd_value = aave_v3_lego.withdrawFromYield(
    aUsdc.address,
    1000 * 10**6,  # 1000 aUSDC
    empty(bytes32),
    user.address
)
```

#### Notes

- Uses max withdrawal to get all available assets
- Automatically registers unknown aTokens
- Assets sent directly to recipient
- Refunds any unused aTokens

## Query Functions

### `isVaultToken`

Checks if an address is a valid aToken.

```vyper
@view
@external
def isVaultToken(_vaultToken: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | Address to check |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if valid aToken |

### `getUnderlyingAsset`

Gets the underlying asset for an aToken.

```vyper
@view
@external
def getUnderlyingAsset(_vaultToken: address) -> address:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | aToken address |

#### Returns

| Type | Description |
|------|-------------|
| `address` | Underlying asset address |

### `getUnderlyingAmount`

Converts aToken amount to underlying amount (1:1).

```vyper
@view
@external
def getUnderlyingAmount(_vaultToken: address, _vaultTokenAmount: uint256) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | aToken address |
| `_vaultTokenAmount` | `uint256` | Amount of aTokens |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Equivalent underlying amount (same value) |

### `getVaultTokenAmount`

Converts asset amount to aToken amount (1:1).

```vyper
@view
@external
def getVaultTokenAmount(_asset: address, _assetAmount: uint256, _vaultToken: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Underlying asset |
| `_assetAmount` | `uint256` | Asset amount |
| `_vaultToken` | `address` | aToken to validate |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Equivalent aToken amount (same value) |

### `getUsdValueOfVaultToken`

Gets USD value of aToken holdings.

```vyper
@view
@external
def getUsdValueOfVaultToken(_vaultToken: address, _vaultTokenAmount: uint256, _appraiser: address = empty(address)) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | aToken address |
| `_vaultTokenAmount` | `uint256` | Amount of aTokens |
| `_appraiser` | `address` | Optional appraiser address |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | USD value of the aTokens |

### `getUnderlyingData`

Gets complete underlying asset information.

```vyper
@view
@external
def getUnderlyingData(_vaultToken: address, _vaultTokenAmount: uint256, _appraiser: address = empty(address)) -> (address, uint256, uint256):
```

#### Returns

| Type | Description |
|------|-------------|
| `address` | Underlying asset address |
| `uint256` | Underlying amount (1:1) |
| `uint256` | USD value |

### `totalAssets`

Gets total supply of an aToken.

```vyper
@view
@external
def totalAssets(_vaultToken: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | aToken address |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Total aToken supply |

### `totalBorrows`

Gets total debt for an asset in Aave.

```vyper
@view
@external
def totalBorrows(_vaultToken: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | aToken address |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Total borrowed amount of underlying asset |

### `getPricePerShare`

Gets the conversion rate (always 1:1 for Aave).

```vyper
@view
@external
def getPricePerShare(_asset: address, _decimals: uint256) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Asset address (unused) |
| `_decimals` | `uint256` | Decimal places |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Always 10^decimals (1:1 rate) |

## Registration Functions

### `addAssetOpportunity`

Registers a new aToken opportunity.

```vyper
@external
def addAssetOpportunity(_asset: address, _vaultAddr: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Underlying asset |
| `_vaultAddr` | `address` | aToken address |

#### Access

Only callable by switchboard addresses

#### Notes

- Validates aToken through Aave's registry
- Sets unlimited approval for deposits
- Registers in YieldLegoData

### `removeAssetOpportunity`

Removes an aToken opportunity.

```vyper
@external
def removeAssetOpportunity(_asset: address, _vaultAddr: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Underlying asset |
| `_vaultAddr` | `address` | aToken address |

#### Access

Only callable by switchboard addresses

#### Notes

- Revokes approval for the asset
- Removes from YieldLegoData registry

## Internal Functions

### `_getVaultTokenOnDeposit`

Gets and validates aToken for deposits.

```vyper
@internal
def _getVaultTokenOnDeposit(_asset: address, _vaultAddr: address, _ledger: address, _legoBook: address) -> address:
```

#### Logic

1. Check if aToken already registered
2. Query Aave if not registered
3. Validate input matches discovered aToken
4. Register if new
5. Update Ledger with vault token info

### `_getAssetOnWithdraw`

Gets underlying asset for withdrawals.

```vyper
@internal
def _getAssetOnWithdraw(_vaultToken: address, _ledger: address, _legoBook: address) -> address:
```

#### Logic

1. Check if asset already mapped
2. Validate aToken through Aave
3. Get underlying asset address
4. Register if new
5. Update Ledger

### `_isValidAToken`

Validates aToken through Aave's registry.

```vyper
@view
@internal
def _isValidAToken(_aToken: address, _dataProvider: address) -> bool:
```

### `_getAaveVaultToken`

Gets aToken address for an asset.

```vyper
@view
@internal
def _getAaveVaultToken(_asset: address, _dataProvider: address) -> address:
```

### `_updateLedgerVaultToken`

Registers vault token with protocol Ledger.

```vyper
@internal
def _updateLedgerVaultToken(
    _underlyingAsset: address,
    _vaultToken: address,
    _ledger: address,
    _legoBook: address,
):
```

## Unimplemented Functions

AaveV3 includes placeholder implementations for unsupported functions:

- DEX: `swapTokens()`
- Mint/Redeem: `mintOrRedeemAsset()`, `confirmMintOrRedeemAsset()`
- Lending: `addCollateral()`, `removeCollateral()`, `borrow()`, `repayDebt()`
- Rewards: `claimRewards()`
- Liquidity: `addLiquidity()`, `removeLiquidity()`, `addLiquidityConcentrated()`, `removeLiquidityConcentrated()`
- Other: `getAccessForLego()`, `getPrice()`

All return zero values or empty results.

## Security Considerations

### Token Validation
- All aTokens verified through Aave's Data Provider
- Underlying assets validated on both deposit and withdrawal
- Automatic registration only for verified tokens

### Approval Management
- Unlimited approval set on registration for gas efficiency
- Approvals revoked when opportunities removed
- No approval needed for withdrawals

### Direct Integration
- aTokens sent directly to recipient on deposit
- Assets sent directly to recipient on withdrawal
- Minimizes custody risk

## Integration Patterns

### Deposit Workflow
```python
# 1. Check if asset has aToken
atoken = aave_data_provider.getReserveTokensAddresses(asset)[0]

# 2. Deposit through Underscore
amount_in, vault_token, vault_amount, usd = user_wallet.depositForYield(
    AAVE_V3_LEGO_ID,
    asset.address,
    deposit_amount,
    atoken,  # Optional validation
    empty(bytes32),
    wallet.address
)

# 3. User receives aTokens directly
assert atoken.balanceOf(wallet.address) > 0
```

### Withdrawal Workflow
```python
# 1. User approves aTokens to wallet
atoken.approve(user_wallet.address, withdraw_amount)

# 2. Withdraw through Underscore
vault_burned, asset, amount_out, usd = user_wallet.withdrawFromYield(
    AAVE_V3_LEGO_ID,
    atoken.address,
    withdraw_amount,
    empty(bytes32),
    wallet.address
)

# 3. User receives underlying assets
assert asset.balanceOf(wallet.address) >= amount_out
```

### Yield Tracking Pattern
```python
# Track yield earned over time
initial_balance = atoken.balanceOf(user)
initial_value = aave_v3_lego.getUsdValueOfVaultToken(
    atoken.address,
    initial_balance
)

# ... time passes, interest accrues ...

current_balance = atoken.balanceOf(user)  # Same as initial (rebasing)
current_value = aave_v3_lego.getUsdValueOfVaultToken(
    atoken.address,
    current_balance
)

yield_earned_usd = current_value - initial_value
```

## Special Considerations

### Rebasing Tokens
- aTokens increase in value, not quantity
- User balance stays constant while value grows
- 1:1 conversion maintained at all times
- No yield bonus for rebasing tokens

### Trial Funds
- Eligible for trial funds when asset/vault pair registered
- Validation through `isEligibleVaultForTrialFunds()`

### Gas Optimization
- Direct aToken transfers avoid extra steps
- Unlimited approvals reduce transaction count
- Automatic registration saves manual setup

## Testing

For comprehensive test examples, see: [`tests/legos/yields/`](../../../../tests/legos/yields/)