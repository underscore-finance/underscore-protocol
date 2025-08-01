# Euler Technical Documentation

[📄 View Source Code](../../../../contracts/legos/yield/Euler.vy)

## Overview

Euler is a Yield Lego partner that integrates the Underscore Protocol with Euler Protocol, a permissionless lending protocol with advanced risk management features. It provides seamless access to Euler's ERC-4626 vaults, supporting both eVaults (isolated lending markets) and Earn vaults (managed yield strategies). The integration handles automatic vault registration, non-rebasing yield tokens, and efficient deposit/withdrawal operations while maintaining full compatibility with Euler's modular architecture.

**Core Features**:
- **ERC-4626 Standard**: Full support for standard vault operations with non-rebasing shares
- **Dual Vault Support**: Access both eVaults (lending) and Earn vaults (strategies)
- **Reward Claiming**: Integrated reward claiming with operator permissions
- **Minimum TVL Requirements**: Built-in eligibility checks for vault quality ($100k minimum)
- **Price-Per-Share Yield**: Non-rebasing tokens that increase in value over time

Built with modular architecture using Addys and YieldLegoData modules, Euler provides secure access to sophisticated lending markets and yield strategies while maintaining the operational standards and security patterns of the Underscore Protocol.

## Architecture & Modules

Euler uses a modular architecture combining address management and yield data handling:

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
│                         Euler Contract                             │
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
│  │  │  Yield Deposits │  │   Withdrawals   │  │   Rewards   │  │  │
│  │  │                 │  │                 │  │             │  │  │
│  │  │ • ERC-4626      │  │ • Redeem shares │  │ • Claim via │  │  │
│  │  │   deposit()     │  │ • Receive assets│  │   operator  │  │  │
│  │  │ • Non-rebasing  │  │ • Auto-register │  │ • Permission│  │  │
│  │  │   shares        │  │ • Full withdrawal│  │   setup     │  │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                               │
                               v
┌────────────────────────────────────────────────────────────────────┐
│                      Euler Integration                             │
│                                                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │  eVault Factory  │  │  Earn Factory    │  │ Rewards Module  │  │
│  │                  │  │                  │  │                 │  │
│  │ • Lending vaults │  │ • Strategy vaults│  │ • Distributor   │  │
│  │ • isProxy()      │  │ • isValidDeploy()│  │ • Operators     │  │
│  │ • Isolated risk  │  │ • Managed yield  │  │ • Merkle proofs │  │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

## Data Structures

Euler uses standard ERC-4626 interfaces and does not define custom structs.

## State Variables

### Protocol Addresses
- `eulerRewards: public(address)` - Euler rewards distributor contract
- `EULER_EVAULT_FACTORY: public(immutable(address))` - eVault factory for lending markets
- `EULER_EARN_FACTORY: public(immutable(address))` - Earn factory for strategy vaults

### Constants
- `MAX_TOKEN_PATH: constant(uint256) = 5` - Maximum tokens in path (unused)
- `LEGO_ACCESS_ABI: constant(String[64]) = "toggleOperator(address,address)"` - ABI for operator setup

## Constructor

### `__init__`

Initializes Euler with Underscore Protocol and Euler factory connections.

```vyper
@deploy
def __init__(
    _undyHq: address,
    _evaultFactory: address,
    _earnFactory: address,
    _eulerRewardsAddr: address,
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq contract address for Underscore Protocol |
| `_evaultFactory` | `address` | Euler eVault factory contract |
| `_earnFactory` | `address` | Euler Earn factory contract |
| `_eulerRewardsAddr` | `address` | Euler rewards distributor address |

#### Returns

*Constructor does not return any values*

#### Access

Called only during contract deployment

#### Example Usage
```python
euler_lego = boa.load(
    "contracts/legos/yield/Euler.vy",
    undy_hq.address,
    evault_factory.address,
    earn_factory.address,
    rewards_distributor.address
)
```

#### Notes

- Validates factory addresses are non-empty
- Stores rewards address for later claiming
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

Returns the Euler factory addresses.

```vyper
@view
@external
def getRegistries() -> DynArray[address, 10]:
```

#### Returns

| Type | Description |
|------|-------------|
| `DynArray[address, 10]` | Array containing eVault and Earn factory addresses |

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
| `bool` | Always False - Euler uses non-rebasing ERC-4626 shares |

### `getAccessForLego`

Provides access requirements for reward claiming.

```vyper
@view
@external
def getAccessForLego(_user: address, _action: ws.ActionType) -> (address, String[64], uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User to check access for |
| `_action` | `ws.ActionType` | Action type (REWARDS) |

#### Returns

| Type | Description |
|------|-------------|
| `address` | Rewards contract needing operator permission |
| `String[64]` | Function ABI to call ("toggleOperator") |
| `uint256` | Number of parameters (2) |

#### Notes

- Only relevant for REWARDS action
- Returns empty if already has operator permission
- User must call toggleOperator(lego, true) on rewards contract

## Yield Functions

### `depositForYield`

Deposits assets into Euler vaults using ERC-4626 standard.

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
| `_vaultAddr` | `address` | Euler vault address |
| `_extraData` | `bytes32` | Additional data (unused) |
| `_recipient` | `address` | Address to receive vault shares |
| `_miniAddys` | `ws.MiniAddys` | Protocol addresses struct |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Actual amount deposited |
| `address` | Vault token address |
| `uint256` | Amount of vault shares received |
| `uint256` | USD value of deposit |

#### Access

- Contract must not be paused
- Open to all callers

#### Events Emitted

- `EulerDeposit` - Contains deposit details including asset, vault, shares, and USD value

#### Example Usage
```python
# Deposit USDC to Euler vault
amount_deposited, vault, shares_received, usd_value = euler_lego.depositForYield(
    usdc.address,
    1000 * 10**6,  # 1000 USDC
    euler_usdc_vault.address,
    empty(bytes32),
    user.address
)
```

#### Notes

- Uses standard ERC-4626 deposit function
- Vault shares sent directly to recipient
- Refunds any unused deposit amount
- Shares value increases over time (non-rebasing)

### `withdrawFromYield`

Withdraws assets from Euler vaults by redeeming shares.

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
| `_vaultToken` | `address` | Vault shares to redeem |
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

- `EulerWithdrawal` - Contains withdrawal details including asset, vault, amounts, and USD value

#### Example Usage
```python
# Withdraw from Euler vault
shares_burned, asset, amount_received, usd_value = euler_lego.withdrawFromYield(
    euler_usdc_vault.address,
    100 * 10**18,  # 100 shares
    empty(bytes32),
    user.address
)
```

#### Notes

- Uses standard ERC-4626 redeem function
- Assets sent directly to recipient
- Refunds any unused shares
- Amount received depends on current share price

## Rewards Functions

### `claimRewards`

Claims rewards from Euler protocol using merkle proofs.

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
| `_rewardToken` | `address` | Token being claimed |
| `_rewardAmount` | `uint256` | Amount to claim |
| `_extraData` | `bytes32` | Merkle proof for claim |
| `_miniAddys` | `ws.MiniAddys` | Protocol addresses struct |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Amount of rewards received |
| `uint256` | USD value of rewards |

#### Access

- Contract must not be paused
- Caller must be the user claiming
- Requires operator permission setup

#### Example Usage
```python
# First setup operator permission
rewards_distributor.toggleOperator(euler_lego.address, True)

# Then claim rewards with proof
reward_amount, usd_value = euler_lego.claimRewards(
    user.address,
    reward_token.address,
    claim_amount,
    merkle_proof,
    sender=user
)
```

### `hasClaimableRewards`

Checks if user has claimable rewards.

```vyper
@view
@external
def hasClaimableRewards(_user: address) -> bool:
```

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Always False - must be checked off-chain |

#### Notes

- Euler uses merkle proofs that must be computed off-chain
- No on-chain way to check claimable amounts

### `setEulerRewardsAddr`

Updates the Euler rewards distributor address.

```vyper
@external
def setEulerRewardsAddr(_addr: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_addr` | `address` | New rewards distributor address |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if successfully updated |

#### Access

Only callable by switchboard addresses

#### Events Emitted

- `EulerRewardsAddrSet` - Contains new rewards address

## Query Functions

### `isVaultToken`

Checks if an address is a valid Euler vault.

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
| `bool` | True if valid eVault or Earn vault |

### `getUnderlyingAsset`

Gets the underlying asset for a vault.

```vyper
@view
@external
def getUnderlyingAsset(_vaultToken: address) -> address:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | Vault address |

#### Returns

| Type | Description |
|------|-------------|
| `address` | Underlying asset address |

### `getUnderlyingAmount`

Converts vault shares to underlying asset amount.

```vyper
@view
@external
def getUnderlyingAmount(_vaultToken: address, _vaultTokenAmount: uint256) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | Vault token address |
| `_vaultTokenAmount` | `uint256` | Amount of shares |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Equivalent underlying amount |

#### Notes

- Uses ERC-4626 convertToAssets function
- Accounts for current share price

### `getVaultTokenAmount`

Converts asset amount to vault shares.

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
| `_vaultToken` | `address` | Vault to validate |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Equivalent share amount |

#### Notes

- Uses ERC-4626 convertToShares function
- Accounts for current share price

### `getUsdValueOfVaultToken`

Gets USD value of vault share holdings.

```vyper
@view
@external
def getUsdValueOfVaultToken(_vaultToken: address, _vaultTokenAmount: uint256, _appraiser: address = empty(address)) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_vaultToken` | `address` | Vault token address |
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
| `_vaultToken` | `address` | Vault address |

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
| `_vaultToken` | `address` | Vault address |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Total borrowed amount |

#### Notes

- Only applicable to eVaults (lending markets)
- Returns 0 for Earn vaults

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
| `_asset` | `address` | Vault address (not underlying) |
| `_decimals` | `uint256` | Decimal places for share |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Assets per share unit |

#### Notes

- Parameter is vault address, not underlying asset
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
| `_vaultToken` | `address` | Vault to check |
| `_underlyingAsset` | `address` | Expected underlying asset |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if eligible (asset matches and TVL > $100k) |

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
| `_asset` | `address` | Vault address to check |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if vault has > $100k TVL |

#### Notes

- Non-rebasing vaults can receive yield bonus
- Requires minimum $100k in total assets

## Registration Functions

### `addAssetOpportunity`

Registers a new Euler vault opportunity.

```vyper
@external
def addAssetOpportunity(_asset: address, _vaultAddr: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Underlying asset |
| `_vaultAddr` | `address` | Euler vault address |

#### Access

Only callable by switchboard addresses

#### Notes

- Validates vault through factories
- Sets unlimited approval for deposits
- Registers in YieldLegoData

### `removeAssetOpportunity`

Removes an Euler vault opportunity.

```vyper
@external
def removeAssetOpportunity(_asset: address, _vaultAddr: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Underlying asset |
| `_vaultAddr` | `address` | Euler vault address |

#### Access

Only callable by switchboard addresses

#### Notes

- Revokes approval for the asset
- Removes from YieldLegoData registry

## Internal Functions

### `_getVaultTokenOnDeposit`

Gets and validates vault for deposits.

```vyper
@internal
def _getVaultTokenOnDeposit(_asset: address, _vaultAddr: address, _ledger: address, _legoBook: address) -> address:
```

#### Logic

1. Check if vault already registered
2. Validate through factories if not
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
2. Validate vault through factories
3. Get underlying asset via ERC-4626
4. Register if new
5. Update Ledger

### `_isValidEulerVault`

Validates vault through both factories.

```vyper
@view
@internal
def _isValidEulerVault(_vaultToken: address) -> bool:
```

#### Logic

- Checks eVault factory with isProxy()
- Checks Earn factory with isValidDeployment()
- Returns true if either validates

### `_hasSufficientAssets`

Checks if vault meets minimum TVL requirement.

```vyper
@view
@internal
def _hasSufficientAssets(_vaultToken: address, _underlyingAsset: address) -> bool:
```

#### Logic

- Gets asset decimals
- Checks totalAssets() > 100,000 units
- Used for eligibility checks

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

Euler includes placeholder implementations for unsupported functions:

- DEX: `swapTokens()`
- Mint/Redeem: `mintOrRedeemAsset()`, `confirmMintOrRedeemAsset()`
- Lending: `addCollateral()`, `removeCollateral()`, `borrow()`, `repayDebt()`
- Liquidity: `addLiquidity()`, `removeLiquidity()`, `addLiquidityConcentrated()`, `removeLiquidityConcentrated()`
- Other: `getPrice()`

All return zero values or empty results.

## Security Considerations

### Vault Validation
- All vaults verified through official factories
- Dual validation (eVault and Earn)
- Underlying asset verification

### Approval Management
- Unlimited approval set on registration for gas efficiency
- Approvals revoked when opportunities removed
- Standard ERC-4626 security model

### Direct Integration
- Vault shares sent directly to recipient on deposit
- Assets sent directly to recipient on withdrawal
- Minimizes custody risk

### Minimum TVL Requirements
- $100k minimum for trial funds eligibility
- Protects against low-liquidity vaults
- Quality control for yield opportunities

## Integration Patterns

### Deposit Workflow
```python
# 1. Check vault eligibility
is_eligible = euler_lego.isEligibleVaultForTrialFunds(
    vault.address,
    asset.address
)

# 2. Deposit through Underscore
amount_in, vault_token, shares, usd = user_wallet.depositForYield(
    EULER_LEGO_ID,
    asset.address,
    deposit_amount,
    vault.address,
    empty(bytes32),
    wallet.address
)

# 3. User receives non-rebasing shares
assert vault.balanceOf(wallet.address) == shares
```

### Withdrawal Workflow
```python
# 1. Check current share value
share_price = euler_lego.getPricePerShare(vault.address, 18)
expected_assets = shares * share_price // 10**18

# 2. Approve shares to wallet
vault.approve(user_wallet.address, shares)

# 3. Withdraw through Underscore
shares_burned, asset, amount_out, usd = user_wallet.withdrawFromYield(
    EULER_LEGO_ID,
    vault.address,
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
initial_shares = vault.balanceOf(user)
initial_price = euler_lego.getPricePerShare(vault.address, 18)
initial_value = initial_shares * initial_price // 10**18

# ... time passes, yield accrues ...

current_shares = vault.balanceOf(user)  # Same amount
current_price = euler_lego.getPricePerShare(vault.address, 18)
current_value = current_shares * current_price // 10**18

yield_earned = current_value - initial_value
```

### Rewards Claiming Pattern
```python
# 1. Setup operator permission (one-time)
euler_rewards.toggleOperator(euler_lego.address, True)

# 2. Get merkle proof off-chain
proof, amount = get_euler_rewards_proof(user, reward_token)

# 3. Claim through wallet
reward_amount, usd = user_wallet.claimRewards(
    EULER_LEGO_ID,
    user.address,
    reward_token.address,
    amount,
    proof  # As bytes32
)
```

## Special Considerations

### Non-Rebasing Shares
- Share count stays constant
- Value per share increases over time
- Standard ERC-4626 behavior
- Eligible for yield bonus

### Dual Vault System
- eVaults: Isolated lending markets
- Earn vaults: Managed strategies
- Both use same interface
- Different risk profiles

### Operator Permissions
- Required for reward claiming
- One-time setup per user
- Managed through rewards distributor
- Check with getAccessForLego()

### Trial Fund Eligibility
- Requires $100k+ TVL
- Protects protocol funds
- Quality filter for vaults

## Testing

For comprehensive test examples, see: [`tests/legos/yields/`](../../../../tests/legos/yields/)