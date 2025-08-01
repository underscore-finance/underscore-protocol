# CompoundV3 Technical Documentation

[📄 View Source Code](../../../../contracts/legos/yield/CompoundV3.vy)

## Overview

CompoundV3 is a Yield Lego partner that integrates the Underscore Protocol with Compound Protocol V3 (Compound III), the next-generation lending protocol focused on single-asset borrowing markets. It provides seamless access to Compound's interest-bearing cTokens, enabling users to earn yield through supply and borrow markets. The integration handles automatic Comet token registration, reward claiming, and efficient deposit/withdrawal operations while maintaining full compatibility with Compound V3's security model.

**Core Features**:
- **Interest-Bearing Deposits**: Supply base assets to Comet markets and earn yield
- **Rebasing Token Support**: Full support for Compound's rebasing cTokens with 1:1 conversion
- **Reward Claiming**: Integrated COMP reward claiming across all markets
- **Automatic Registration**: Dynamic discovery and registration of new Comet opportunities
- **Multi-Market Support**: Access all Compound V3 markets through a single interface

Built with modular architecture using Addys and YieldLegoData modules, CompoundV3 provides secure access to Compound's innovative single-collateral lending markets while maintaining the operational standards and security patterns of the Underscore Protocol.

## Architecture & Modules

CompoundV3 uses a modular architecture combining address management and yield data handling:

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
│                       CompoundV3 Contract                          │
├────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐         ┌──────────────────────────────┐  │
│  │    Addys Module     │         │   YieldLegoData Module       │  │
│  │                     │         │                              │  │
│  │ • Protocol addrs    │         │ • Asset opportunities        │  │
│  │ • Registry access   │         │ • Comet token mappings       │  │
│  │ • Appraiser access  │         │ • Registration tracking      │  │
│  └─────────────────────┘         └──────────────────────────────┘  │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Core Capabilities                         │  │
│  │                                                              │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │  │
│  │  │  Yield Deposits │  │   Withdrawals   │  │   Rewards   │  │  │
│  │  │                 │  │                 │  │             │  │  │
│  │  │ • Supply to     │  │ • Withdraw from │  │ • Claim COMP│  │  │
│  │  │   Comet         │  │   Comet         │  │ • Multi-    │  │  │
│  │  │ • Receive       │  │ • Receive base  │  │   market    │  │  │
│  │  │   cTokens       │  │   assets        │  │ • Auto      │  │  │
│  │  │ • 1:1 rebasing │  │ • Max withdrawal│  │   accrual   │  │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                               │
                               v
┌────────────────────────────────────────────────────────────────────┐
│                    Compound V3 Integration                         │
│                                                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │   Comet Markets  │  │  Configurator    │  │ Rewards Module  │  │
│  │                  │  │                  │  │                 │  │
│  │ • supplyTo()     │  │ • Factory lookup │  │ • getRewardOwed │  │
│  │ • withdrawTo()   │  │ • Market valid.  │  │ • claim()       │  │
│  │ • Base tokens    │  │ • Registration   │  │ • COMP tokens   │  │
│  │                  │  │                  │  │                 │  │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

## Data Structures

### RewardOwed Struct
Compound's reward information structure:
```vyper
struct RewardOwed:
    token: address    # Reward token address (COMP)
    owed: uint256    # Amount of rewards owed
```

## State Variables

### Protocol Addresses
- `compoundRewards: public(address)` - Compound rewards contract for COMP claiming
- `COMPOUND_V3_CONFIGURATOR: public(immutable(address))` - Compound V3 configurator contract

### Constants
- `MAX_TOKEN_PATH: constant(uint256) = 5` - Maximum tokens in path (unused)

## Constructor

### `__init__`

Initializes CompoundV3 with Underscore Protocol and Compound V3 connections.

```vyper
@deploy
def __init__(
    _undyHq: address,
    _configurator: address,
    _compRewards: address,
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq contract address for Underscore Protocol |
| `_configurator` | `address` | Compound V3 Configurator contract address |
| `_compRewards` | `address` | Compound rewards contract for COMP claiming |

#### Returns

*Constructor does not return any values*

#### Access

Called only during contract deployment

#### Example Usage
```python
compound_v3_lego = boa.load(
    "contracts/legos/yield/CompoundV3.vy",
    undy_hq.address,
    configurator.address,
    rewards.address
)
```

#### Notes

- Validates configurator address is non-empty
- Stores rewards contract for later claiming
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

Returns the Compound V3 registry addresses.

```vyper
@view
@external
def getRegistries() -> DynArray[address, 10]:
```

#### Returns

| Type | Description |
|------|-------------|
| `DynArray[address, 10]` | Array containing Configurator address |

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
| `bool` | Always True - Compound V3 uses rebasing cTokens |

## Yield Functions

### `depositForYield`

Deposits assets into Compound V3 Comet markets to earn yield.

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
| `_asset` | `address` | Base asset to deposit |
| `_amount` | `uint256` | Amount to deposit |
| `_vaultAddr` | `address` | Comet market address |
| `_extraData` | `bytes32` | Additional data (unused) |
| `_recipient` | `address` | Address to receive cTokens |
| `_miniAddys` | `ws.MiniAddys` | Protocol addresses struct |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Actual amount deposited |
| `address` | Comet token address (same as vault) |
| `uint256` | Amount of cTokens received (1:1 with deposit) |
| `uint256` | USD value of deposit |

#### Access

- Contract must not be paused
- Open to all callers

#### Events Emitted

- `CompoundV3Deposit` - Contains deposit details including asset, Comet token, amounts, and USD value

#### Example Usage
```python
# Deposit USDC to Compound V3
amount_deposited, comet, ctokens_received, usd_value = compound_v3_lego.depositForYield(
    usdc.address,
    1000 * 10**6,  # 1000 USDC
    cusdc_comet.address,  # Comet market
    empty(bytes32),
    user.address
)
```

#### Notes

- Validates asset matches Comet's base token
- Comet tokens are sent directly to recipient
- Refunds any unused deposit amount
- 1:1 conversion between asset and cToken

### `withdrawFromYield`

Withdraws assets from Compound V3 by redeeming cTokens.

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
| `_vaultToken` | `address` | Comet token to redeem |
| `_amount` | `uint256` | Amount of cTokens to redeem |
| `_extraData` | `bytes32` | Additional data (unused) |
| `_recipient` | `address` | Address to receive underlying assets |
| `_miniAddys` | `ws.MiniAddys` | Protocol addresses struct |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Amount of cTokens redeemed |
| `address` | Underlying asset address |
| `uint256` | Amount of assets received |
| `uint256` | USD value of withdrawal |

#### Access

- Contract must not be paused
- Open to all callers

#### Events Emitted

- `CompoundV3Withdrawal` - Contains withdrawal details including asset, Comet token, amounts, and USD value

#### Example Usage
```python
# Withdraw USDC from Compound V3
ctokens_burned, asset, amount_received, usd_value = compound_v3_lego.withdrawFromYield(
    cusdc_comet.address,
    1000 * 10**6,  # 1000 cUSDC
    empty(bytes32),
    user.address
)
```

#### Notes

- Uses max withdrawal to get all available assets
- Automatically registers unknown Comet tokens
- Assets sent directly to recipient
- Refunds any unused cTokens

## Rewards Functions

### `claimRewards`

Claims COMP rewards from Compound V3 markets.

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
| `_user` | `address` | User claiming rewards (must be msg.sender) |
| `_rewardToken` | `address` | COMP token address |
| `_rewardAmount` | `uint256` | Expected amount (unused) |
| `_extraData` | `bytes32` | Specific market address or empty for all |
| `_miniAddys` | `ws.MiniAddys` | Protocol addresses struct |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Amount of COMP rewards received |
| `uint256` | USD value of rewards |

#### Access

- Contract must not be paused
- Caller must be the user claiming

#### Example Usage
```python
# Claim from specific market
market_address = convert(cusdc_comet.address, bytes32)
comp_amount, usd_value = compound_v3_lego.claimRewards(
    user.address,
    comp_token.address,
    0,  # Not used
    market_address,
    sender=user
)

# Claim from all markets
comp_amount, usd_value = compound_v3_lego.claimRewards(
    user.address,
    comp_token.address,
    0,
    empty(bytes32),
    sender=user
)
```

### `hasClaimableRewards`

Checks if user has claimable COMP rewards.

```vyper
@external
def hasClaimableRewards(_user: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User to check |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if user has claimable rewards |

#### Notes

- Not a view function due to Compound's implementation
- Checks all registered markets

### `setCompRewardsAddr`

Updates the Compound rewards contract address.

```vyper
@external
def setCompRewardsAddr(_addr: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | New rewards contract address |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if successfully updated |

#### Access

Only callable by switchboard addresses

#### Events Emitted

- `CompoundV3RewardsAddrSet` - Contains new rewards address

## Query Functions

### `isVaultToken`

Checks if an address is a valid Comet market.

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
| `bool` | True if valid Comet market |

### `getUnderlyingAsset`

Gets the base token for a Comet market.

```vyper
@view
@external
def getUnderlyingAsset(_vaultToken: address) -> address:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | Comet market address |

#### Returns

| Type | Description |
|------|-------------|
| `address` | Base token address |

### `getUnderlyingAmount`

Converts cToken amount to underlying amount (1:1).

```vyper
@view
@external
def getUnderlyingAmount(_vaultToken: address, _vaultTokenAmount: uint256) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | Comet token address |
| `_vaultTokenAmount` | `uint256` | Amount of cTokens |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Equivalent underlying amount (same value) |

### `getVaultTokenAmount`

Converts asset amount to cToken amount (1:1).

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
| `_vaultToken` | `address` | Comet token to validate |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Equivalent cToken amount (same value) |

### `getUsdValueOfVaultToken`

Gets USD value of cToken holdings.

```vyper
@view
@external
def getUsdValueOfVaultToken(_vaultToken: address, _vaultTokenAmount: uint256, _appraiser: address = empty(address)) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | Comet token address |
| `_vaultTokenAmount` | `uint256` | Amount of cTokens |
| `_appraiser` | `address` | Optional appraiser address |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | USD value of the cTokens |

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

Gets total supply in a Comet market.

```vyper
@view
@external
def totalAssets(_vaultToken: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | Comet market address |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Total supplied to market |

### `totalBorrows`

Gets total borrows from a Comet market.

```vyper
@view
@external
def totalBorrows(_vaultToken: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | Comet market address |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Total borrowed from market |

### `getPricePerShare`

Gets the conversion rate (always 1:1 for Compound V3).

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

Registers a new Comet market opportunity.

```vyper
@external
def addAssetOpportunity(_asset: address, _vaultAddr: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Base token for market |
| `_vaultAddr` | `address` | Comet market address |

#### Access

Only callable by switchboard addresses

#### Notes

- Validates Comet through configurator
- Sets unlimited approval for deposits
- Registers in YieldLegoData

### `removeAssetOpportunity`

Removes a Comet market opportunity.

```vyper
@external
def removeAssetOpportunity(_asset: address, _vaultAddr: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Base token |
| `_vaultAddr` | `address` | Comet market address |

#### Access

Only callable by switchboard addresses

#### Notes

- Revokes approval for the asset
- Removes from YieldLegoData registry

## Internal Functions

### `_getVaultTokenOnDeposit`

Gets and validates Comet market for deposits.

```vyper
@internal
def _getVaultTokenOnDeposit(_asset: address, _vaultAddr: address, _ledger: address, _legoBook: address) -> address:
```

#### Logic

1. Check if Comet already registered
2. Validate through configurator if not
3. Verify base token matches input asset
4. Register if new
5. Update Ledger with vault token info

### `_getAssetOnWithdraw`

Gets base token for withdrawals.

```vyper
@internal
def _getAssetOnWithdraw(_vaultToken: address, _ledger: address, _legoBook: address) -> address:
```

#### Logic

1. Check if asset already mapped
2. Validate Comet through configurator
3. Get base token address
4. Register if new
5. Update Ledger

### `_isValidCometAddr`

Validates Comet market through configurator.

```vyper
@view
@internal
def _isValidCometAddr(_cometAddr: address) -> bool:
```

### `_hasClaimableOrShouldClaim`

Internal rewards logic for checking/claiming.

```vyper
@internal
def _hasClaimableOrShouldClaim(_user: address, _shouldClaim: bool, _compRewardsAddr: address) -> bool:
```

#### Logic

1. Iterate through all registered assets
2. Get Comet market for each asset
3. Check rewards owed for user
4. Either claim or return true if rewards exist

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

CompoundV3 includes placeholder implementations for unsupported functions:

- DEX: `swapTokens()`
- Mint/Redeem: `mintOrRedeemAsset()`, `confirmMintOrRedeemAsset()`
- Lending: `addCollateral()`, `removeCollateral()`, `borrow()`, `repayDebt()`
- Liquidity: `addLiquidity()`, `removeLiquidity()`, `addLiquidityConcentrated()`, `removeLiquidityConcentrated()`
- Other: `getAccessForLego()`, `getPrice()`

All return zero values or empty results.

## Security Considerations

### Market Validation
- All Comet markets verified through configurator
- Base token validation on both deposit and withdrawal
- Factory lookup ensures legitimate markets

### Approval Management
- Unlimited approval set on registration for gas efficiency
- Approvals revoked when opportunities removed
- No approval needed for withdrawals

### Direct Integration
- cTokens sent directly to recipient on deposit
- Assets sent directly to recipient on withdrawal
- Minimizes custody risk

### Rewards Security
- Only user can claim their own rewards
- Rewards contract address updateable by governance
- Automatic accrual on claims

## Integration Patterns

### Deposit Workflow
```python
# 1. Find Comet market for asset
comet = configurator.getComet(asset)

# 2. Deposit through Underscore
amount_in, vault_token, vault_amount, usd = user_wallet.depositForYield(
    COMPOUND_V3_LEGO_ID,
    asset.address,
    deposit_amount,
    comet.address,
    empty(bytes32),
    wallet.address
)

# 3. User receives cTokens directly
assert comet.balanceOf(wallet.address) > 0
```

### Withdrawal Workflow
```python
# 1. User approves cTokens to wallet
comet.approve(user_wallet.address, withdraw_amount)

# 2. Withdraw through Underscore
vault_burned, asset, amount_out, usd = user_wallet.withdrawFromYield(
    COMPOUND_V3_LEGO_ID,
    comet.address,
    withdraw_amount,
    empty(bytes32),
    wallet.address
)

# 3. User receives base assets
assert asset.balanceOf(wallet.address) >= amount_out
```

### Rewards Claiming Pattern
```python
# Check for rewards across all markets
has_rewards = compound_v3_lego.hasClaimableRewards(user.address)

if has_rewards:
    # Claim all rewards
    comp_amount, usd_value = user_wallet.claimRewards(
        COMPOUND_V3_LEGO_ID,
        user.address,
        comp_token.address,
        0,  # Amount not used
        empty(bytes32)  # All markets
    )
    
    # Or claim from specific market
    comp_amount, usd_value = user_wallet.claimRewards(
        COMPOUND_V3_LEGO_ID,
        user.address,
        comp_token.address,
        0,
        convert(comet.address, bytes32)
    )
```

## Special Considerations

### Rebasing Tokens
- cTokens increase in value, not quantity
- User balance stays constant while value grows
- 1:1 conversion maintained at all times
- No yield bonus for rebasing tokens

### Single Asset Markets
- Each Comet market supports only one base asset
- No cross-collateral within a market
- Focused risk management per asset

### Trial Funds
- Eligible for trial funds when asset/vault pair registered
- Validation through `isEligibleVaultForTrialFunds()`

### Gas Optimization
- Direct cToken transfers avoid extra steps
- Unlimited approvals reduce transaction count
- Batch reward claiming across markets

## Testing

For comprehensive test examples, see: [`tests/legos/yields/`](../../../../tests/legos/yields/)