# Moonwell Technical Documentation

[📄 View Source Code](../../../../contracts/legos/yield/Moonwell.vy)

## Overview

Moonwell is a Yield Lego partner that integrates the Underscore Protocol with Moonwell Protocol, an open lending and borrowing DeFi protocol built on Base and other networks. It provides seamless access to Moonwell's interest-bearing mTokens, enabling users to earn competitive yields through supply markets. The integration handles automatic mToken registration, non-rebasing token support, reward claiming, and efficient deposit/withdrawal operations while maintaining full compatibility with Moonwell's Compound V2-based architecture.

**Core Features**:
- **Interest-Bearing mTokens**: Non-rebasing tokens that increase in value via exchange rate
- **Multi-Asset Rewards**: Integrated reward claiming across all markets
- **Automatic Registration**: Dynamic discovery and registration of new mToken opportunities
- **ETH/WETH Handling**: Special handling for native ETH deposits and withdrawals
- **Comprehensive Tracking**: USD value calculation and yield tracking for all positions

Built with modular architecture using Addys and YieldLegoData modules, Moonwell provides secure access to cross-chain lending markets while maintaining the operational standards and security patterns of the Underscore Protocol.

## Architecture & Modules

Moonwell uses a modular architecture combining address management and yield data handling:

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
│                       Moonwell Contract                            │
├────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐         ┌──────────────────────────────┐  │
│  │    Addys Module     │         │   YieldLegoData Module       │  │
│  │                     │         │                              │  │
│  │ • Protocol addrs    │         │ • Asset opportunities        │  │
│  │ • Registry access   │         │ • mToken mappings            │  │
│  │ • Appraiser access  │         │ • Registration tracking      │  │
│  └─────────────────────┘         └──────────────────────────────┘  │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Core Capabilities                         │  │
│  │                                                              │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │  │
│  │  │  Yield Deposits │  │   Withdrawals   │  │   Rewards   │  │  │
│  │  │                 │  │                 │  │             │  │  │
│  │  │ • mint() assets │  │ • redeem()      │  │ • Claim     │  │  │
│  │  │ • Receive       │  │   mTokens       │  │   rewards   │  │  │
│  │  │   mTokens       │  │ • ETH handling  │  │ • Multi-    │  │  │
│  │  │ • Exchange rate │  │ • Full withdraw │  │   asset     │  │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                               │
                               v
┌────────────────────────────────────────────────────────────────────┐
│                    Moonwell Integration                            │
│                                                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │   Comptroller    │  │  mToken Markets  │  │ RewardDistributor│  │
│  │                  │  │                  │  │                 │  │
│  │ • getAllMarkets()│  │ • mint/redeem    │  │ • Outstanding   │  │
│  │ • Market registry│  │ • Exchange rate  │  │   rewards       │  │
│  │ • claimReward()  │  │ • Compound V2    │  │ • Multi-token   │  │
│  │                  │  │   interface      │  │   rewards       │  │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

## Data Structures

### RewardWithMToken Struct
Maps mTokens to their reward information:
```vyper
struct RewardWithMToken:
    mToken: address                              # mToken market address
    rewards: DynArray[RewardInfo, MAX_ASSETS]    # Array of reward tokens
```

### RewardInfo Struct
Detailed reward information per token:
```vyper
struct RewardInfo:
    emissionToken: address    # Reward token address
    totalAmount: uint256      # Total claimable amount
    supplySide: uint256       # Supply side rewards
    borrowSide: uint256       # Borrow side rewards
```

## State Variables

### Immutable Protocol Addresses
- `MOONWELL_COMPTROLLER: public(immutable(address))` - Moonwell comptroller contract
- `WETH: public(immutable(address))` - Wrapped ETH contract address

### Constants
- `MAX_MARKETS: constant(uint256) = 50` - Maximum number of markets
- `MAX_ASSETS: constant(uint256) = 25` - Maximum reward assets per market
- `MAX_TOKEN_PATH: constant(uint256) = 5` - Maximum tokens in path (unused)

## Constructor

### `__init__`

Initializes Moonwell with Underscore Protocol and Moonwell connections.

```vyper
@deploy
def __init__(
    _undyHq: address,
    _moonwellComptroller: address,
    _weth: address,
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq contract address for Underscore Protocol |
| `_moonwellComptroller` | `address` | Moonwell Comptroller contract address |
| `_weth` | `address` | Wrapped ETH contract address |

#### Returns

*Constructor does not return any values*

#### Access

Called only during contract deployment

#### Example Usage
```python
moonwell_lego = boa.load(
    "contracts/legos/yield/Moonwell.vy",
    undy_hq.address,
    comptroller.address,
    weth.address
)
```

#### Notes

- Validates all addresses are non-empty
- Initializes modules without pausing
- Sets up ETH handling capability

## Special Functions

### `__default__`

Allows contract to receive ETH for WETH conversions.

```vyper
@payable
@external
def __default__():
    pass
```

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

Returns the Moonwell registry addresses.

```vyper
@view
@external
def getRegistries() -> DynArray[address, 10]:
```

#### Returns

| Type | Description |
|------|-------------|
| `DynArray[address, 10]` | Array containing Moonwell Comptroller address |

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
| `bool` | Always False - Moonwell uses non-rebasing mTokens |

## Yield Functions

### `depositForYield`

Deposits assets into Moonwell markets to earn yield.

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
| `_vaultAddr` | `address` | mToken market address |
| `_extraData` | `bytes32` | Additional data (unused) |
| `_recipient` | `address` | Address to receive mTokens |
| `_miniAddys` | `ws.MiniAddys` | Protocol addresses struct |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Actual amount deposited |
| `address` | mToken address |
| `uint256` | Amount of mTokens received |
| `uint256` | USD value of deposit |

#### Access

- Contract must not be paused
- Open to all callers

#### Events Emitted

- `MoonwellDeposit` - Contains deposit details including asset, mToken, amounts, and USD value

#### Example Usage
```python
# Deposit USDC to Moonwell
amount_deposited, mtoken, mtokens_received, usd_value = moonwell_lego.depositForYield(
    usdc.address,
    1000 * 10**6,  # 1000 USDC
    musdc.address,  # mUSDC market
    empty(bytes32),
    user.address
)
```

#### Notes

- Uses Compound V2 mint function
- mTokens transferred to recipient after minting
- Refunds any unused deposit amount
- Exchange rate determines mToken amount

### `withdrawFromYield`

Withdraws assets from Moonwell by redeeming mTokens.

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
| `_vaultToken` | `address` | mToken to redeem |
| `_amount` | `uint256` | Amount of mTokens to redeem |
| `_extraData` | `bytes32` | Additional data (unused) |
| `_recipient` | `address` | Address to receive underlying assets |
| `_miniAddys` | `ws.MiniAddys` | Protocol addresses struct |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Amount of mTokens redeemed |
| `address` | Underlying asset address |
| `uint256` | Amount of assets received |
| `uint256` | USD value of withdrawal |

#### Access

- Contract must not be paused
- Open to all callers

#### Events Emitted

- `MoonwellWithdrawal` - Contains withdrawal details including asset, mToken, amounts, and USD value

#### Example Usage
```python
# Withdraw USDC from Moonwell
mtokens_burned, asset, amount_received, usd_value = moonwell_lego.withdrawFromYield(
    musdc.address,
    1000 * 10**8,  # 1000 mUSDC (8 decimals)
    empty(bytes32),
    user.address
)
```

#### Notes

- Uses max redemption to get all available assets
- Special handling for WETH - converts ETH to WETH
- Assets transferred to recipient after redemption
- Refunds any unused mTokens

## Rewards Functions

### `claimRewards`

Claims rewards from Moonwell markets.

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
| `_rewardToken` | `address` | Expected reward token |
| `_rewardAmount` | `uint256` | Expected amount (unused) |
| `_extraData` | `bytes32` | Additional data (unused) |
| `_miniAddys` | `ws.MiniAddys` | Protocol addresses struct |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Amount of rewards received |
| `uint256` | USD value of rewards |

#### Access

- Contract must not be paused
- Caller must be the user claiming

#### Example Usage
```python
# Claim rewards from all markets
reward_amount, usd_value = moonwell_lego.claimRewards(
    user.address,
    well_token.address,
    0,  # Not used
    empty(bytes32),
    sender=user
)
```

### `hasClaimableRewards`

Checks if user has claimable rewards across markets.

```vyper
@view
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
| `bool` | True if user has any claimable rewards |

#### Notes

- Queries reward distributor for outstanding rewards
- Checks all markets and reward tokens
- Returns true if any rewards available

## Query Functions

### `isVaultToken`

Checks if an address is a valid mToken.

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
| `bool` | True if valid mToken market |

### `getUnderlyingAsset`

Gets the underlying asset for an mToken.

```vyper
@view
@external
def getUnderlyingAsset(_vaultToken: address) -> address:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | mToken address |

#### Returns

| Type | Description |
|------|-------------|
| `address` | Underlying asset address |

### `getUnderlyingAmount`

Converts mToken amount to underlying amount using exchange rate.

```vyper
@view
@external
def getUnderlyingAmount(_vaultToken: address, _vaultTokenAmount: uint256) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | mToken address |
| `_vaultTokenAmount` | `uint256` | Amount of mTokens |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Equivalent underlying amount |

#### Notes

- Uses stored exchange rate
- Accounts for interest accrual

### `getVaultTokenAmount`

Converts asset amount to mToken amount.

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
| `_vaultToken` | `address` | mToken to validate |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Equivalent mToken amount |

### `getUsdValueOfVaultToken`

Gets USD value of mToken holdings.

```vyper
@view
@external
def getUsdValueOfVaultToken(_vaultToken: address, _vaultTokenAmount: uint256, _appraiser: address = empty(address)) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | mToken address |
| `_vaultTokenAmount` | `uint256` | Amount of mTokens |
| `_appraiser` | `address` | Optional appraiser address |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | USD value of the mTokens |

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

Gets total supplied assets in a market.

```vyper
@view
@external
def totalAssets(_vaultToken: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | mToken market address |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Total assets supplied to market |

### `totalBorrows`

Gets total borrowed assets from a market.

```vyper
@view
@external
def totalBorrows(_vaultToken: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | mToken market address |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Total assets borrowed from market |

### `getPricePerShare`

Gets the exchange rate for mTokens.

```vyper
@view
@external
def getPricePerShare(_asset: address, _decimals: uint256) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | mToken address (not underlying) |
| `_decimals` | `uint256` | Decimal places for rate |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Exchange rate adjusted for decimals |

#### Notes

- Parameter is mToken address, not underlying
- Returns underlying per mToken unit

## Registration Functions

### `addAssetOpportunity`

Registers a new mToken opportunity.

```vyper
@external
def addAssetOpportunity(_asset: address, _vaultAddr: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Underlying asset |
| `_vaultAddr` | `address` | mToken market address |

#### Access

Only callable by switchboard addresses

#### Notes

- Validates mToken through comptroller
- Sets unlimited approval for deposits
- Registers in YieldLegoData

### `removeAssetOpportunity`

Removes an mToken opportunity.

```vyper
@external
def removeAssetOpportunity(_asset: address, _vaultAddr: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Underlying asset |
| `_vaultAddr` | `address` | mToken market address |

#### Access

Only callable by switchboard addresses

#### Notes

- Revokes approval for the asset
- Removes from YieldLegoData registry

## Internal Functions

### `_getVaultTokenOnDeposit`

Gets and validates mToken for deposits.

```vyper
@internal
def _getVaultTokenOnDeposit(_asset: address, _vaultAddr: address, _ledger: address, _legoBook: address) -> address:
```

#### Logic

1. Check if mToken already registered
2. Validate through comptroller if not
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
2. Validate mToken through comptroller
3. Get underlying asset address
4. Register if new
5. Update Ledger

### `_isValidCToken`

Validates mToken through comptroller.

```vyper
@view
@internal
def _isValidCToken(_cToken: address) -> bool:
```

#### Logic

- Queries comptroller for all markets
- Returns true if address in market list

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

Moonwell includes placeholder implementations for unsupported functions:

- DEX: `swapTokens()`
- Mint/Redeem: `mintOrRedeemAsset()`, `confirmMintOrRedeemAsset()`
- Lending: `addCollateral()`, `removeCollateral()`, `borrow()`, `repayDebt()`
- Liquidity: `addLiquidity()`, `removeLiquidity()`, `addLiquidityConcentrated()`, `removeLiquidityConcentrated()`
- Other: `getAccessForLego()`, `getPrice()`

All return zero values or empty results.

## Security Considerations

### Market Validation
- All mTokens verified through comptroller
- Underlying asset verification on both deposit and withdrawal
- Market registry prevents unauthorized tokens

### Approval Management
- Unlimited approval set on registration for gas efficiency
- Approvals revoked when opportunities removed
- Standard Compound V2 security model

### ETH Handling
- Contract can receive ETH via default function
- Automatic WETH conversion on withdrawal
- Prevents ETH being stuck in contract

### Direct Integration
- mTokens sent directly to recipient after minting
- Assets sent directly to recipient on withdrawal
- Minimizes custody risk

## Integration Patterns

### Deposit Workflow
```python
# 1. Check if market is valid
is_valid = moonwell_lego.isVaultToken(mtoken.address)

# 2. Deposit through Underscore
amount_in, vault_token, mtokens, usd = user_wallet.depositForYield(
    MOONWELL_LEGO_ID,
    asset.address,
    deposit_amount,
    mtoken.address,
    empty(bytes32),
    wallet.address
)

# 3. User receives non-rebasing mTokens
assert mtoken.balanceOf(wallet.address) == mtokens
```

### Withdrawal Workflow
```python
# 1. Check current exchange rate
rate = moonwell_lego.getPricePerShare(mtoken.address, 18)
expected_assets = mtokens * rate // 10**18

# 2. Approve mTokens to wallet
mtoken.approve(user_wallet.address, mtokens)

# 3. Withdraw through Underscore
mtokens_burned, asset, amount_out, usd = user_wallet.withdrawFromYield(
    MOONWELL_LEGO_ID,
    mtoken.address,
    mtokens,
    empty(bytes32),
    wallet.address
)

# 4. User receives underlying assets
assert asset.balanceOf(wallet.address) >= expected_assets
```

### Yield Tracking Pattern
```python
# Track yield earned over time
initial_mtokens = mtoken.balanceOf(user)
initial_rate = moonwell_lego.getPricePerShare(mtoken.address, 18)
initial_value = initial_mtokens * initial_rate // 10**18

# ... time passes, interest accrues ...

current_mtokens = mtoken.balanceOf(user)  # Same amount
current_rate = moonwell_lego.getPricePerShare(mtoken.address, 18)
current_value = current_mtokens * current_rate // 10**18

yield_earned = current_value - initial_value
```

### Rewards Claiming Pattern
```python
# Check for rewards
has_rewards = moonwell_lego.hasClaimableRewards(user.address)

if has_rewards:
    # Claim all rewards across markets
    reward_amount, usd_value = user_wallet.claimRewards(
        MOONWELL_LEGO_ID,
        user.address,
        reward_token.address,
        0,  # Amount not used
        empty(bytes32)
    )
```

## Special Considerations

### Non-Rebasing mTokens
- mToken count stays constant
- Value increases via exchange rate
- Similar to Compound V2 cTokens
- Eligible for yield bonus

### Multi-Asset Rewards
- Multiple reward tokens per market
- Supply and borrow side rewards
- Automatic claiming across all markets
- Reward distributor tracks balances

### ETH/WETH Conversion
- mWETH redeems to ETH
- Contract wraps ETH to WETH
- Seamless user experience
- No ETH stuck in contract

### Cross-Chain Support
- Moonwell operates on multiple chains
- Same interface across deployments
- Consistent behavior

## Testing

For comprehensive test examples, see: [`tests/legos/yields/`](../../../../tests/legos/yields/)