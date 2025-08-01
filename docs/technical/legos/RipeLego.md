# RipeLego Technical Documentation

[📄 View Source Code](../../../contracts/legos/RipeLego.vy)

## Overview

RipeLego is a comprehensive Lego partner integration that connects the Underscore Protocol with the Ripe Protocol ecosystem. It provides both yield generation capabilities through Savings Green tokens and debt management features including collateral deposits, borrowing, and repayment operations. As a dual-purpose Lego, it serves as both a YieldLego for earning yield on Green tokens and a lending protocol interface for debt management.

**Core Functions**:
- **Yield Generation**: Deposit Green tokens into Savings Green for yield farming
- **Debt Management**: Add/remove collateral, borrow, and repay debt on Ripe Protocol
- **Rewards Claiming**: Claim RIPE token rewards from protocol participation
- **Vault Token Management**: ERC-4626 compliant vault operations for Savings Green

Built with modular architecture integrating Addys and YieldLegoData modules, RipeLego provides seamless access to Ripe Protocol's lending and yield farming ecosystem while maintaining the security and operational patterns of the Underscore Protocol.

## Architecture & Modules

RipeLego uses a modular architecture combining address management and yield farming data:

### Addys Module
- **Location**: `contracts/modules/Addys.vy`
- **Purpose**: Provides protocol-wide address lookups and registry access
- **Documentation**: See [Addys Technical Documentation](../modules/Addys.md)
- **Key Features**:
  - Connection to UndyHq for protocol addresses
  - Access to Ledger, Appraiser, and other core contracts
  - Cached address lookups for gas efficiency
- **Exported Interface**: All address functions are exposed via `addys.__interface__`

### YieldLegoData Module
- **Location**: `contracts/modules/YieldLegoData.vy`
- **Purpose**: Manages yield farming data and vault token mappings
- **Documentation**: See [YieldLegoData Technical Documentation](../modules/YieldLegoData.md)
- **Key Features**:
  - Asset to vault token bidirectional mappings
  - Pause functionality for emergency stops
  - Vault opportunity management
- **Exported Interface**: All yield data functions are exposed via `yld.__interface__`

### Module Initialization
```vyper
initializes: addys
initializes: yld[addys := addys]
```
This initialization pattern ensures proper module dependencies and yield farming capabilities.

## System Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                        RipeLego Contract                           │
├────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐         ┌──────────────────────────────┐  │
│  │    Addys Module     │         │    YieldLegoData Module      │  │
│  │                     │         │                              │  │
│  │ • Protocol addrs    │         │ • Vault mappings             │  │
│  │ • Registry access   │         │ • Asset opportunities        │  │
│  │ • Cached lookups    │         │ • Pause functionality        │  │
│  └─────────────────────┘         └──────────────────────────────┘  │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                  Core Capabilities                           │  │
│  │                                                              │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  │ Debt Management │  │ Yield Farming   │  │ Rewards Claiming│ │
│  │  │                 │  │                 │  │                 │ │
│  │  │ • Add collateral│  │ • Green → sGreen│  │ • RIPE tokens   │ │
│  │  │ • Remove        │  │ • sGreen → Green│  │ • Auto-staking  │ │
│  │  │   collateral    │  │ • ERC-4626      │  │ • USD valuation │ │
│  │  │ • Borrow Green/ │  │   compliant     │  │                 │ │
│  │  │   sGreen        │  │ • Yield tracking│  │                 │ │
│  │  │ • Repay debt    │  │                 │  │                 │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│  │                                                              │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  │ Access Control  │  │ Token Support   │  │ Integration     │ │
│  │  │                 │  │                 │  │                 │ │
│  │  │ • User wallet   │  │ • GREEN token   │  │ • RipeTeller    │ │
│  │  │   validation    │  │ • sGREEN token  │  │ • RipeRegistry  │ │
│  │  │ • Ripe protocol │  │ • RIPE rewards  │  │ • Mission       │ │
│  │  │   permissions   │  │ • USD pricing   │  │   Control       │ │
│  │  │ • Recipient     │  │ • Decimals      │  │ • Appraiser     │ │
│  │  │   restrictions  │  │   handling      │  │   integration   │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                               │
                               v
┌────────────────────────────────────────────────────────────────────┐
│                      Ripe Protocol Integration                     │
│                                                                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│  │   RipeTeller    │  │  RipeRegistry   │  │   Savings Green     │ │
│  │                 │  │                 │  │   (ERC-4626)        │ │
│  │ • Collateral    │  │ • Component     │  │                     │ │
│  │   management    │  │   addresses     │  │ • Green → sGreen    │ │
│  │ • Borrowing     │  │ • Token         │  │ • Yield generation  │ │
│  │ • Repayment     │  │   contracts     │  │ • Redemption        │ │
│  │ • Reward        │  │ • Mission       │  │ • Asset conversion  │ │
│  │   claiming      │  │   Control       │  │                     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

## Data Structures

### Ripe Protocol Integration Constants
```vyper
# Component registry IDs for Ripe Protocol
RIPE_MISSION_CONTROL_ID: constant(uint256) = 5
RIPE_LOOTBOX_ID: constant(uint256) = 16
RIPE_TELLER_ID: constant(uint256) = 17

# Access control constants
LEGO_ACCESS_ABI: constant(String[64]) = "setUndyLegoAccess(address)"
MAX_TOKEN_PATH: constant(uint256) = 5
```

## State Variables

### Immutable Ripe Protocol Addresses
- `RIPE_REGISTRY: public(immutable(address))` - Ripe Protocol registry contract
- `RIPE_GREEN_TOKEN: public(immutable(address))` - GREEN token contract address
- `RIPE_SAVINGS_GREEN: public(immutable(address))` - Savings Green vault token address
- `RIPE_TOKEN: public(immutable(address))` - RIPE reward token address

## Constructor

### `__init__`

Initializes RipeLego with Underscore Protocol and Ripe Protocol connections.

```vyper
@deploy
def __init__(
    _undyHq: address,
    _ripeRegistry: address,
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq contract address for Underscore Protocol |
| `_ripeRegistry` | `address` | Ripe Protocol registry contract address |

#### Returns

*The constructor does not return any values.*

#### Access

Called only once during contract deployment.

#### Example Usage
```python
# Deploy RipeLego
ripe_lego = boa.load(
    "contracts/legos/RipeLego.vy",
    undy_hq.address,
    ripe_registry.address
)
```

#### Notes

- Initializes Addys module with UndyHq connection
- Initializes YieldLegoData module with non-rebasing configuration
- Validates and stores Ripe Protocol component addresses
- Automatically fetches Green, Savings Green, and RIPE token addresses

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

- `EARN_DEPOSIT` - Depositing for yield (Green → Savings Green)
- `EARN_WITHDRAW` - Withdrawing from yield (Savings Green → Green)
- `ADD_COLLATERAL` - Adding collateral to Ripe Protocol
- `REMOVE_COLLATERAL` - Removing collateral from Ripe Protocol
- `BORROW` - Borrowing Green/Savings Green tokens
- `REPAY_DEBT` - Repaying borrowed amounts
- `REWARDS` - Claiming RIPE token rewards

#### Example Usage
```python
# Check if RipeLego supports borrowing
can_borrow = ripe_lego.hasCapability(ActionType.BORROW)
# Returns: True
```

### `getRegistries`

Returns the Ripe Protocol registry address.

```vyper
@view
@external
def getRegistries() -> DynArray[address, 10]:
```

#### Returns

| Type | Description |
|------|-------------|
| `DynArray[address, 10]` | Array containing the Ripe registry address |

### `getAccessForLego`

Determines access requirements for Ripe Protocol operations.

```vyper
@view
@external
def getAccessForLego(_user: address, _action: ws.ActionType) -> (address, String[64], uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User address to check access for |
| `_action` | `ws.ActionType` | Action type being performed |

#### Returns

| Type | Description |
|------|-------------|
| `address` | Contract address for access setup (empty if access exists) |
| `String[64]` | Function signature for access setup (empty if access exists) |
| `uint256` | Value parameter for access call (0 if access exists) |

#### Access Logic

- **Has Access**: Returns empty values if user already has Ripe Protocol access
- **Needs Access**: Returns RipeTeller address and `setUndyLegoAccess(address)` function signature

### `isYieldLego` / `isDexLego`

Identifies the Lego type capabilities.

```vyper
@view
@external
def isYieldLego() -> bool:  # Returns True

@view
@external
def isDexLego() -> bool:    # Returns False
```

## Debt Management Functions

### `addCollateral`

Deposits assets as collateral into Ripe Protocol.

```vyper
@external
def addCollateral(
    _asset: address,
    _amount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Asset to deposit as collateral |
| `_amount` | `uint256` | Amount to deposit |
| `_extraData` | `bytes32` | Optional vault ID (converted from bytes32) |
| `_recipient` | `address` | Address to receive collateral credit (must be caller) |
| `_miniAddys` | `ws.MiniAddys` | Mini address struct for protocol integration |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Actual amount deposited |
| `uint256` | USD value of deposited amount |

#### Access

- Only user wallets can call this function
- Recipient must be the calling address

#### Events Emitted

- `RipeCollateralDeposit` - Contains asset, amount, vault ID, USD value, and recipient information: `log RipeCollateralDeposit(sender=msg.sender, asset=_asset, assetAmountDeposited=depositAmount, vaultId=vaultId, usdValue=usdValue, recipient=_recipient)`

#### Example Usage
```python
# Add USDC as collateral
amount_deposited, usd_value = user_wallet.addCollateral(
    usdc.address,
    1000 * 10**6,  # 1000 USDC
    convert(1, bytes32),  # Vault ID 1
    user_wallet.address,
    mini_addys
)
```

#### Notes

- Automatically handles token transfers and approvals
- Refunds any undeposited amounts
- Updates prices through Appraiser integration
- Supports vault-specific deposits via extraData

### `removeCollateral`

Withdraws collateral from Ripe Protocol.

```vyper
@external
def removeCollateral(
    _asset: address,
    _amount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Asset to withdraw |
| `_amount` | `uint256` | Amount to withdraw |
| `_extraData` | `bytes32` | Optional vault ID (converted from bytes32) |
| `_recipient` | `address` | Address to receive withdrawn assets (must be caller) |
| `_miniAddys` | `ws.MiniAddys` | Mini address struct for protocol integration |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Actual amount withdrawn |
| `uint256` | USD value of withdrawn amount |

#### Access

- Only user wallets can call this function
- Recipient must be the calling address

#### Events Emitted

- `RipeCollateralWithdrawal` - Contains asset, amount, vault ID, USD value, and recipient information: `log RipeCollateralWithdrawal(sender=msg.sender, asset=_asset, assetAmountReceived=amountRemoved, vaultId=vaultId, usdValue=usdValue, recipient=_recipient)`

#### Example Usage
```python
# Remove USDC collateral
amount_withdrawn, usd_value = user_wallet.removeCollateral(
    usdc.address,
    500 * 10**6,  # 500 USDC
    convert(1, bytes32),  # Vault ID 1
    user_wallet.address,
    mini_addys
)
```

### `borrow`

Borrows Green or Savings Green tokens from Ripe Protocol.

```vyper
@external
def borrow(
    _borrowAsset: address,
    _amount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_borrowAsset` | `address` | Asset to borrow (GREEN or Savings GREEN) |
| `_amount` | `uint256` | Amount to borrow |
| `_extraData` | `bytes32` | Additional data (unused in current implementation) |
| `_recipient` | `address` | Address to receive borrowed tokens (must be caller) |
| `_miniAddys` | `ws.MiniAddys` | Mini address struct for protocol integration |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Actual amount borrowed |
| `uint256` | USD value of borrowed amount |

#### Access

- Only user wallets can call this function
- Recipient must be the calling address

#### Validation

- Borrow asset must be either GREEN token or Savings GREEN token
- Automatically determines if user wants Savings Green based on asset choice

#### Events Emitted

- `RipeBorrow` - Contains asset, amount, USD value, and recipient information: `log RipeBorrow(sender=msg.sender, asset=_borrowAsset, assetAmountBorrowed=borrowAmount, usdValue=usdValue, recipient=_recipient)`

#### Example Usage
```python
# Borrow Savings Green tokens
amount_borrowed, usd_value = user_wallet.borrow(
    savings_green.address,
    1000 * 10**18,  # 1000 sGREEN
    empty(bytes32),
    user_wallet.address,
    mini_addys
)
```

### `repayDebt`

Repays borrowed amounts to Ripe Protocol.

```vyper
@external
def repayDebt(
    _paymentAsset: address,
    _paymentAmount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_paymentAsset` | `address` | Asset used for repayment (GREEN or Savings GREEN) |
| `_paymentAmount` | `uint256` | Amount to repay |
| `_extraData` | `bytes32` | Additional data (unused in current implementation) |
| `_recipient` | `address` | Address credited with repayment (must be caller) |
| `_miniAddys` | `ws.MiniAddys` | Mini address struct for protocol integration |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Actual amount repaid |
| `uint256` | USD value of repaid amount |

#### Access

- Only user wallets can call this function
- Recipient must be the calling address

#### Events Emitted

- `RipeRepay` - Contains asset, amount, USD value, and recipient information: `log RipeRepay(sender=msg.sender, asset=_paymentAsset, assetAmountRepaid=paymentAmount, usdValue=usdValue, recipient=_recipient)`

#### Example Usage
```python
# Repay debt with Green tokens
amount_repaid, usd_value = user_wallet.repayDebt(
    green_token.address,
    500 * 10**18,  # 500 GREEN
    empty(bytes32),
    user_wallet.address,
    mini_addys
)
```

#### Notes

- Automatically handles token transfers and approvals
- Refunds any unused payment tokens
- Supports both Green and Savings Green for repayment
- Enables refund of Savings Green if applicable

## Rewards Management

### `claimRewards`

Claims RIPE token rewards from protocol participation.

```vyper
@external
def claimRewards(
    _user: address,
    _rewardToken: address,
    _rewardAmount: uint256,
    _extraData: bytes32,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User address to claim rewards for (must be caller) |
| `_rewardToken` | `address` | Reward token address (must be RIPE token) |
| `_rewardAmount` | `uint256` | Amount parameter (unused - claims all available) |
| `_extraData` | `bytes32` | Additional data (unused in current implementation) |
| `_miniAddys` | `ws.MiniAddys` | Mini address struct for protocol integration |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Total RIPE tokens claimed |
| `uint256` | USD value of claimed rewards |

#### Access

- Caller must be the user address (no user wallet restriction for Endaoment compatibility)
- Reward token must be RIPE token

#### Events Emitted

- `RipeClaimRewards` - Contains reward asset, amount claimed, USD value, and recipient information: `log RipeClaimRewards(sender=msg.sender, asset=_rewardToken, ripeClaimed=totalRipe, usdValue=usdValue, recipient=_user)`

#### Example Usage
```python
# Claim RIPE rewards
ripe_claimed, usd_value = ripe_lego.claimRewards(
    user.address,
    ripe_token.address,
    0,  # Amount ignored - claims all
    empty(bytes32),
    mini_addys
)
```

#### Notes

- Automatically stakes claimed RIPE tokens
- Compatible with Ripe's Endaoment system
- Claims all available rewards regardless of amount parameter

## Yield Farming Functions

### `depositForYield`

Deposits Green tokens into Savings Green for yield generation.

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
| `_asset` | `address` | Asset to deposit (must be GREEN token) |
| `_amount` | `uint256` | Amount to deposit |
| `_vaultAddr` | `address` | Vault address (must be Savings GREEN) |
| `_extraData` | `bytes32` | Additional data (unused in current implementation) |
| `_recipient` | `address` | Address to receive vault tokens |
| `_miniAddys` | `ws.MiniAddys` | Mini address struct for protocol integration |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Actual amount deposited |
| `address` | Vault token address (Savings GREEN) |
| `uint256` | Vault tokens received |
| `uint256` | USD value of deposited amount |

#### Access

Open to all callers (no user wallet restriction).

#### Validation

- Asset must be GREEN token
- Vault address must be Savings GREEN token
- Automatically registers vault token if not already registered

#### Events Emitted

- `RipeSavingsGreenDeposit` - Contains asset, vault token, amounts, USD value, and recipient information: `log RipeSavingsGreenDeposit(sender=msg.sender, asset=_asset, vaultToken=vaultToken, assetAmountDeposited=depositAmount, usdValue=usdValue, vaultTokenAmountReceived=vaultTokenAmountReceived, recipient=_recipient)`

#### Example Usage
```python
# Deposit Green tokens for yield
amount_deposited, vault_token, vault_amount, usd_value = ripe_lego.depositForYield(
    green_token.address,
    1000 * 10**18,  # 1000 GREEN
    savings_green.address,
    empty(bytes32),
    user.address,
    mini_addys
)
```

### `withdrawFromYield`

Withdraws Green tokens from Savings Green vault.

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
| `_vaultToken` | `address` | Vault token to redeem (must be Savings GREEN) |
| `_amount` | `uint256` | Vault token amount to redeem |
| `_extraData` | `bytes32` | Additional data (unused in current implementation) |
| `_recipient` | `address` | Address to receive underlying assets |
| `_miniAddys` | `ws.MiniAddys` | Mini address struct for protocol integration |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Vault tokens burned |
| `address` | Underlying asset address (GREEN token) |
| `uint256` | Underlying assets received |
| `uint256` | USD value of withdrawn amount |

#### Access

Open to all callers (no user wallet restriction).

#### Events Emitted

- `RipeSavingsGreenWithdrawal` - Contains asset, vault token, amounts, USD value, and recipient information: `log RipeSavingsGreenWithdrawal(sender=msg.sender, asset=asset, vaultToken=_vaultToken, assetAmountReceived=assetAmountReceived, usdValue=usdValue, vaultTokenAmountBurned=vaultTokenAmount, recipient=_recipient)`

#### Example Usage
```python
# Withdraw Green tokens from yield
vault_burned, asset, amount_received, usd_value = ripe_lego.withdrawFromYield(
    savings_green.address,
    500 * 10**18,  # 500 sGREEN
    empty(bytes32),
    user.address,
    mini_addys
)
```

## Vault Token Query Functions

### `isVaultToken`

Checks if an address is a supported vault token.

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
| `bool` | True if address is Savings GREEN token |

### `getUnderlyingAsset`

Gets the underlying asset for a vault token.

```vyper
@view
@external
def getUnderlyingAsset(_vaultToken: address) -> address:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | Vault token address |

#### Returns

| Type | Description |
|------|-------------|
| `address` | Underlying asset address (GREEN token if valid vault) |

### `getUnderlyingAmount`

Converts vault token amount to underlying asset amount.

```vyper
@view
@external
def getUnderlyingAmount(_vaultToken: address, _vaultTokenAmount: uint256) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | Vault token address |
| `_vaultTokenAmount` | `uint256` | Vault token amount |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Equivalent underlying asset amount |

### `getVaultTokenAmount`

Converts underlying asset amount to vault token amount.

```vyper
@view
@external
def getVaultTokenAmount(_asset: address, _assetAmount: uint256, _vaultToken: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Underlying asset address |
| `_assetAmount` | `uint256` | Asset amount |
| `_vaultToken` | `address` | Vault token address |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Equivalent vault token amount |

### `getUsdValueOfVaultToken`

Gets USD value of vault token amount.

```vyper
@view
@external
def getUsdValueOfVaultToken(_vaultToken: address, _vaultTokenAmount: uint256, _appraiser: address = empty(address)) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | Vault token address |
| `_vaultTokenAmount` | `uint256` | Vault token amount |
| `_appraiser` | `address` | Appraiser contract address (optional) |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | USD value of vault token amount |

### `getUnderlyingData`

Gets comprehensive underlying asset data for vault tokens.

```vyper
@view
@external
def getUnderlyingData(_vaultToken: address, _vaultTokenAmount: uint256, _appraiser: address = empty(address)) -> (address, uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | Vault token address |
| `_vaultTokenAmount` | `uint256` | Vault token amount |
| `_appraiser` | `address` | Appraiser contract address (optional) |

#### Returns

| Type | Description |
|------|-------------|
| `address` | Underlying asset address |
| `uint256` | Underlying asset amount |
| `uint256` | USD value |

## Vault Information Functions

### `totalAssets`

Gets total assets managed by a vault.

```vyper
@view
@external
def totalAssets(_vaultToken: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | Vault token address |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Total underlying assets in vault |

### `totalBorrows`

Gets total borrowed amounts for a vault (placeholder implementation).

```vyper
@view
@external
def totalBorrows(_vaultToken: address) -> uint256:
```

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Always returns 0 (placeholder for future implementation) |

### `getPricePerShare`

Gets the price per share for vault tokens.

```vyper
@view
@external
def getPricePerShare(_asset: address, _decimals: uint256) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Vault token address |
| `_decimals` | `uint256` | Token decimals |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Assets per unit of vault token |

## Configuration Functions

### `isRebasing`

Indicates whether vault tokens are rebasing.

```vyper
@view
@external
def isRebasing() -> bool:
```

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Always returns False (Savings GREEN is not rebasing) |

### `isEligibleVaultForTrialFunds`

Checks vault eligibility for trial funds.

```vyper
@view
@external
def isEligibleVaultForTrialFunds(_vaultToken: address, _underlyingAsset: address) -> bool:
```

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Always returns False (not eligible for trial funds) |

### `isEligibleForYieldBonus`

Checks asset eligibility for yield bonuses.

```vyper
@view
@external
def isEligibleForYieldBonus(_asset: address) -> bool:
```

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Always returns False (RIPE rewards replace yield bonuses) |

## Asset Registration Functions

### `addAssetOpportunity` / `removeAssetOpportunity`

Placeholder functions for asset opportunity management.

```vyper
@external
def addAssetOpportunity(_asset: address, _vaultAddr: address):
    pass

@external
def removeAssetOpportunity(_asset: address, _vaultAddr: address):
    pass
```

#### Notes

- Currently implemented as pass-through functions
- Asset registration handled automatically during operations

## Unimplemented Functions

RipeLego includes placeholder implementations for DEX-related functions that are not supported:

- `swapTokens()` - Returns (0, 0, 0)
- `mintOrRedeemAsset()` - Returns (0, 0, False, 0)
- `confirmMintOrRedeemAsset()` - Returns (0, 0)
- `addLiquidity()` - Returns (empty(address), 0, 0, 0, 0)
- `removeLiquidity()` - Returns (0, 0, 0, 0)
- `addLiquidityConcentrated()` - Returns (0, 0, 0, 0, 0)
- `removeLiquidityConcentrated()` - Returns (0, 0, 0, False, 0)
- `getPrice()` - Returns 0

## Security Considerations

### Access Control
- User wallet validation for debt management operations
- Recipient address validation (must match caller for sensitive operations)
- Ripe Protocol permission integration

### Token Handling
- Automatic approval management with reset after operations
- Balance tracking for refund calculations
- ERC-20 transfer safety with default return value handling

### Integration Safety
- Automatic vault token registration in Ledger
- Price updates through Appraiser integration
- Pause functionality through YieldLegoData module

## Integration Patterns

### Debt Management Workflow
```python
# 1. Add collateral
amount_deposited, usd_value = user_wallet.addCollateral(
    collateral_asset.address,
    deposit_amount,
    vault_id_bytes,
    user_wallet.address,
    mini_addys
)

# 2. Borrow against collateral
borrowed_amount, borrow_usd_value = user_wallet.borrow(
    green_token.address,
    borrow_amount,
    empty(bytes32),
    user_wallet.address,
    mini_addys
)

# 3. Repay debt when ready
repaid_amount, repay_usd_value = user_wallet.repayDebt(
    green_token.address,
    repayment_amount,
    empty(bytes32),
    user_wallet.address,
    mini_addys
)

# 4. Remove collateral
withdrawn_amount, withdraw_usd_value = user_wallet.removeCollateral(
    collateral_asset.address,
    withdrawal_amount,
    vault_id_bytes,
    user_wallet.address,
    mini_addys
)
```

### Yield Farming Workflow
```python
# 1. Deposit Green tokens for yield
deposited, vault_token, vault_amount, usd_value = ripe_lego.depositForYield(
    green_token.address,
    deposit_amount,
    savings_green.address,
    empty(bytes32),
    user.address,
    mini_addys
)

# 2. Let yield accumulate over time...

# 3. Claim RIPE rewards periodically
ripe_claimed, reward_usd_value = ripe_lego.claimRewards(
    user.address,
    ripe_token.address,
    0,  # Claims all available
    empty(bytes32),
    mini_addys
)

# 4. Withdraw when desired
vault_burned, asset, amount_received, withdraw_usd_value = ripe_lego.withdrawFromYield(
    savings_green.address,
    withdrawal_vault_amount,
    empty(bytes32),
    user.address,
    mini_addys
)
```

### Access Setup Pattern
```python
# Check if user needs Ripe Protocol access
contract_addr, function_sig, value = ripe_lego.getAccessForLego(
    user.address, 
    ActionType.BORROW
)

if contract_addr != empty(address):
    # User needs to call setUndyLegoAccess on RipeTeller
    ripe_teller.setUndyLegoAccess(user.address)
```

## Testing

For comprehensive test examples, see: [`tests/legos/`](../../../tests/legos/)