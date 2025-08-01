# Fluid Technical Documentation

[📄 View Source Code](../../../../contracts/legos/yield/Fluid.vy)

## Overview

Fluid is a Yield Lego partner that integrates the Underscore Protocol with Fluid Protocol, an innovative liquidity layer that optimizes capital efficiency across lending and borrowing markets. It provides seamless access to Fluid's yield-generating fTokens, enabling users to earn competitive yields through dynamic liquidity allocation. The integration handles automatic fToken registration, ERC-4626 standard compliance, and efficient deposit/withdrawal operations while maintaining full compatibility with Fluid's advanced liquidity mechanisms.

**Core Features**:
- **ERC-4626 Vaults**: Full support for standardized yield-bearing fTokens
- **Non-Rebasing Shares**: Share tokens that increase in value rather than quantity
- **Dynamic Discovery**: Automatic registration of new fToken opportunities via resolver
- **Efficient Integration**: Direct integration with Fluid vaults for minimal gas costs
- **Comprehensive Tracking**: USD value calculation and yield tracking for all positions

Built with modular architecture using Addys and YieldLegoData modules, Fluid provides secure access to advanced yield optimization strategies while maintaining the operational standards and security patterns of the Underscore Protocol.

## Architecture & Modules

Fluid uses a modular architecture combining address management and yield data handling:

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
│                         Fluid Contract                             │
├────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐         ┌──────────────────────────────┐  │
│  │    Addys Module     │         │   YieldLegoData Module       │  │
│  │                     │         │                              │  │
│  │ • Protocol addrs    │         │ • Asset opportunities        │  │
│  │ • Registry access   │         │ • fToken mappings            │  │
│  │ • Appraiser access  │         │ • Registration tracking      │  │
│  └─────────────────────┘         └──────────────────────────────┘  │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Core Capabilities                         │  │
│  │                                                              │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │  │
│  │  │  Yield Deposits │  │   Withdrawals   │  │ Token Query │  │  │
│  │  │                 │  │                 │  │             │  │  │
│  │  │ • ERC-4626      │  │ • Redeem shares │  │ • Validate  │  │  │
│  │  │   deposit()     │  │ • Receive assets│  │   fTokens   │  │  │
│  │  │ • Non-rebasing  │  │ • Auto-register │  │ • Get asset │  │  │
│  │  │   shares        │  │ • Full redeem   │  │ • USD value │  │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                               │
                               v
┌────────────────────────────────────────────────────────────────────┐
│                      Fluid Integration                             │
│                                                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │  Lending Resolver│  │    fTokens        │  │ Liquidity Layer │  │
│  │                  │  │                   │  │                 │  │
│  │ • getAllFTokens()│  │ • ERC-4626 vaults │  │ • Dynamic       │  │
│  │ • Token registry │  │ • Share-based     │  │   allocation    │  │
│  │ • Discovery      │  │ • Price per share │  │ • Optimized     │  │
│  │                  │  │                   │  │   yields        │  │
│  └──────────────────┐  └──────────────────┘  └─────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

## Data Structures

Fluid uses standard ERC-4626 interfaces and does not define custom structs.

## State Variables

### Protocol Addresses
- `FLUID_RESOLVER: public(immutable(address))` - Fluid lending resolver contract

### Constants
- `MAX_FTOKENS: constant(uint256) = 50` - Maximum fTokens to query
- `MAX_TOKEN_PATH: constant(uint256) = 5` - Maximum tokens in path (unused)

## Constructor

### `__init__`

Initializes Fluid with Underscore Protocol and Fluid resolver connections.

```vyper
@deploy
def __init__(
    _undyHq: address,
    _fluidResolver: address,
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq contract address for Underscore Protocol |
| `_fluidResolver` | `address` | Fluid Lending Resolver contract address |

#### Returns

*Constructor does not return any values*

#### Access

Called only during contract deployment

#### Example Usage
```python
fluid_lego = boa.load(
    "contracts/legos/yield/Fluid.vy",
    undy_hq.address,
    fluid_resolver.address
)
```

#### Notes

- Validates resolver address is non-empty
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

Returns the Fluid registry addresses.

```vyper
@view
@external
def getRegistries() -> DynArray[address, 10]:
```

#### Returns

| Type | Description |
|------|-------------|
| `DynArray[address, 10]` | Array containing Fluid Resolver address |

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
| `bool` | Always False - Fluid uses non-rebasing share tokens |

## Yield Functions

### `depositForYield`

Deposits assets into Fluid vaults using ERC-4626 standard.

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
| `_vaultAddr` | `address` | Fluid fToken vault address |
| `_extraData` | `bytes32` | Additional data (unused) |
| `_recipient` | `address` | Address to receive fToken shares |
| `_miniAddys` | `ws.MiniAddys` | Protocol addresses struct |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Actual amount deposited |
| `address` | fToken vault address |
| `uint256` | Amount of fToken shares received |
| `uint256` | USD value of deposit |

#### Access

- Contract must not be paused
- Open to all callers

#### Events Emitted

- `FluidDeposit` - Contains deposit details including asset, fToken, shares, and USD value

#### Example Usage
```python
# Deposit USDC to Fluid vault
amount_deposited, ftoken, shares_received, usd_value = fluid_lego.depositForYield(
    usdc.address,
    1000 * 10**6,  # 1000 USDC
    fusdc.address,  # fUSDC vault
    empty(bytes32),
    user.address
)
```

#### Notes

- Uses standard ERC-4626 deposit function
- fToken shares sent directly to recipient
- Refunds any unused deposit amount
- Shares value increases over time (non-rebasing)

### `withdrawFromYield`

Withdraws assets from Fluid vaults by redeeming fToken shares.

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
| `_vaultToken` | `address` | fToken shares to redeem |
| `_amount` | `uint256` | Amount of shares to redeem |
| `_extraData` | `bytes32` | Additional data (unused) |
| `_recipient` | `address` | Address to receive underlying assets |
| `_miniAddys` | `ws.MiniAddys` | Protocol addresses struct |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Amount of shares redeemed |
| `address` | Underlying asset address |
| `uint256` | Amount of assets received |
| `uint256` | USD value of withdrawal |

#### Access

- Contract must not be paused
- Open to all callers

#### Events Emitted

- `FluidWithdrawal` - Contains withdrawal details including asset, fToken, amounts, and USD value

#### Example Usage
```python
# Withdraw from Fluid vault
shares_burned, asset, amount_received, usd_value = fluid_lego.withdrawFromYield(
    fusdc.address,
    100 * 10**18,  # 100 fUSDC shares
    empty(bytes32),
    user.address
)
```

#### Notes

- Uses standard ERC-4626 redeem function
- Assets sent directly to recipient
- Refunds any unused shares
- Amount received depends on current share price

## Query Functions

### `isVaultToken`

Checks if an address is a valid fToken.

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
| `bool` | True if valid fToken |

### `getUnderlyingAsset`

Gets the underlying asset for an fToken.

```vyper
@view
@external
def getUnderlyingAsset(_vaultToken: address) -> address:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | fToken address |

#### Returns

| Type | Description |
|------|-------------|
| `address` | Underlying asset address |

### `getUnderlyingAmount`

Converts fToken shares to underlying asset amount.

```vyper
@view
@external
def getUnderlyingAmount(_vaultToken: address, _vaultTokenAmount: uint256) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | fToken address |
| `_vaultTokenAmount` | `uint256` | Amount of shares |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Equivalent underlying amount |

#### Notes

- Uses ERC-4626 convertToAssets function
- Accounts for current share price

### `getVaultTokenAmount`

Converts asset amount to fToken shares.

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
| `_vaultToken` | `address` | fToken to validate |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Equivalent share amount |

#### Notes

- Uses ERC-4626 convertToShares function
- Accounts for current share price

### `getUsdValueOfVaultToken`

Gets USD value of fToken share holdings.

```vyper
@view
@external
def getUsdValueOfVaultToken(_vaultToken: address, _vaultTokenAmount: uint256, _appraiser: address = empty(address)) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | fToken address |
| `_vaultTokenAmount` | `uint256` | Amount of shares |
| `_appraiser` | `address` | Optional appraiser address |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | USD value of the shares |

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
| `uint256` | Underlying amount |
| `uint256` | USD value |

### `totalAssets`

Gets total assets in a vault.

```vyper
@view
@external
def totalAssets(_vaultToken: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | fToken address |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Total assets under management |

### `totalBorrows`

Gets total borrows from a vault.

```vyper
@view
@external
def totalBorrows(_vaultToken: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | fToken address |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Always 0 (TODO: implementation pending) |

### `getPricePerShare`

Gets the current share price.

```vyper
@view
@external
def getPricePerShare(_asset: address, _decimals: uint256) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | fToken address (not underlying) |
| `_decimals` | `uint256` | Decimal places for share |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Assets per share unit |

#### Notes

- Parameter is fToken address, not underlying asset
- Uses ERC-4626 convertToAssets

## Eligibility Functions

### `isEligibleVaultForTrialFunds`

Checks if vault meets requirements for trial funds.

```vyper
@view
@external
def isEligibleVaultForTrialFunds(_vaultToken: address, _underlyingAsset: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | fToken to check |
| `_underlyingAsset` | `address` | Expected underlying asset |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if registered and asset matches |

### `isEligibleForYieldBonus`

Checks if vault qualifies for yield bonus.

```vyper
@view
@external
def isEligibleForYieldBonus(_asset: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | fToken address to check |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if registered fToken |

#### Notes

- Non-rebasing vaults can receive yield bonus
- Returns true for any registered fToken

## Registration Functions

### `addAssetOpportunity`

Registers a new fToken opportunity.

```vyper
@external
def addAssetOpportunity(_asset: address, _vaultAddr: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Underlying asset |
| `_vaultAddr` | `address` | fToken vault address |

#### Access

Only callable by switchboard addresses

#### Notes

- Validates fToken through resolver
- Sets unlimited approval for deposits
- Registers in YieldLegoData

### `removeAssetOpportunity`

Removes an fToken opportunity.

```vyper
@external
def removeAssetOpportunity(_asset: address, _vaultAddr: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Underlying asset |
| `_vaultAddr` | `address` | fToken vault address |

#### Access

Only callable by switchboard addresses

#### Notes

- Revokes approval for the asset
- Removes from YieldLegoData registry

## Internal Functions

### `_getVaultTokenOnDeposit`

Gets and validates fToken for deposits.

```vyper
@internal
def _getVaultTokenOnDeposit(_asset: address, _vaultAddr: address, _ledger: address, _legoBook: address) -> address:
```

#### Logic

1. Check if fToken already registered
2. Validate through resolver if not
3. Verify underlying asset matches
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
2. Validate fToken through resolver
3. Get underlying asset via ERC-4626
4. Register if new
5. Update Ledger

### `_isValidFToken`

Validates fToken through Fluid resolver.

```vyper
@view
@internal
def _isValidFToken(_fToken: address) -> bool:
```

#### Logic

- Queries resolver for all fTokens
- Returns true if address in list

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

Fluid includes placeholder implementations for unsupported functions:

- DEX: `swapTokens()`
- Mint/Redeem: `mintOrRedeemAsset()`, `confirmMintOrRedeemAsset()`
- Lending: `addCollateral()`, `removeCollateral()`, `borrow()`, `repayDebt()`
- Rewards: `claimRewards()`
- Liquidity: `addLiquidity()`, `removeLiquidity()`, `addLiquidityConcentrated()`, `removeLiquidityConcentrated()`
- Other: `getAccessForLego()`, `getPrice()`

All return zero values or empty results.

## Security Considerations

### Vault Validation
- All fTokens verified through official resolver
- Underlying asset verification on both deposit and withdrawal
- Dynamic discovery prevents unauthorized vaults

### Approval Management
- Unlimited approval set on registration for gas efficiency
- Approvals revoked when opportunities removed
- Standard ERC-4626 security model

### Direct Integration
- fToken shares sent directly to recipient on deposit
- Assets sent directly to recipient on withdrawal
- Minimizes custody risk

## Integration Patterns

### Deposit Workflow
```python
# 1. Check fToken is valid
is_valid = fluid_lego.isVaultToken(ftoken.address)

# 2. Deposit through Underscore
amount_in, vault_token, shares, usd = user_wallet.depositForYield(
    FLUID_LEGO_ID,
    asset.address,
    deposit_amount,
    ftoken.address,
    empty(bytes32),
    wallet.address
)

# 3. User receives non-rebasing shares
assert ftoken.balanceOf(wallet.address) == shares
```

### Withdrawal Workflow
```python
# 1. Check current share value
share_price = fluid_lego.getPricePerShare(ftoken.address, 18)
expected_assets = shares * share_price // 10**18

# 2. Approve shares to wallet
ftoken.approve(user_wallet.address, shares)

# 3. Withdraw through Underscore
shares_burned, asset, amount_out, usd = user_wallet.withdrawFromYield(
    FLUID_LEGO_ID,
    ftoken.address,
    shares,
    empty(bytes32),
    wallet.address
)

# 4. User receives underlying assets
assert asset.balanceOf(wallet.address) >= expected_assets
```

### Yield Tracking Pattern
```python
# Track yield earned over time
initial_shares = ftoken.balanceOf(user)
initial_price = fluid_lego.getPricePerShare(ftoken.address, 18)
initial_value = initial_shares * initial_price // 10**18

# ... time passes, yield accrues ...

current_shares = ftoken.balanceOf(user)  # Same amount
current_price = fluid_lego.getPricePerShare(ftoken.address, 18)
current_value = current_shares * current_price // 10**18

yield_earned = current_value - initial_value
```

## Special Considerations

### Non-Rebasing Shares
- Share count stays constant
- Value per share increases over time
- Standard ERC-4626 behavior
- Eligible for yield bonus

### Dynamic Liquidity
- Fluid optimizes yields across markets
- Automatic rebalancing for best returns
- No user intervention required

### Resolver-Based Discovery
- All fTokens validated through resolver
- Dynamic registration as new vaults launch
- Permissionless integration

### Trial Fund Eligibility
- Any registered fToken eligible
- No minimum TVL requirements
- Relies on Fluid's own risk management

## Testing

For comprehensive test examples, see: [`tests/legos/yields/`](../../../../tests/legos/yields/)