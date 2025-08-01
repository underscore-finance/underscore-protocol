# Morpho Technical Documentation

[📄 View Source Code](../../../../contracts/legos/yield/Morpho.vy)

## Overview

Morpho is a Yield Lego partner that integrates the Underscore Protocol with Morpho Protocol, a revolutionary peer-to-peer layer built on top of lending pools that enables improved rates for both suppliers and borrowers. It provides seamless access to Morpho's MetaMorpho vaults, which are ERC-4626 compliant vaults that optimize yield across multiple lending markets. The integration handles automatic vault registration, non-rebasing token support, reward claiming, and efficient deposit/withdrawal operations while maintaining full compatibility with Morpho's advanced matching engine.

**Core Features**:
- **ERC-4626 MetaMorpho Vaults**: Full support for standardized yield-bearing vault tokens
- **Non-Rebasing Shares**: Share tokens that increase in value rather than quantity
- **Dual Factory Support**: Compatible with both current and legacy MetaMorpho factories
- **Minimum TVL Requirements**: Built-in eligibility checks for vault quality ($100k minimum)
- **Rewards Integration**: Merkle proof-based reward claiming system

Built with modular architecture using Addys and YieldLegoData modules, Morpho provides secure access to optimized peer-to-peer lending while maintaining the operational standards and security patterns of the Underscore Protocol.

## Architecture & Modules

Morpho uses a modular architecture combining address management and yield data handling:

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
│                         Morpho Contract                            │
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
│  │  │ • ERC-4626      │  │ • Redeem shares │  │ • Merkle    │  │  │
│  │  │   deposit()     │  │ • Receive assets│  │   proofs    │  │  │
│  │  │ • Non-rebasing  │  │ • Auto-register │  │ • Claim     │  │  │
│  │  │   shares        │  │ • Full redeem   │  │   rewards   │  │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                               │
                               v
┌────────────────────────────────────────────────────────────────────┐
│                      Morpho Integration                            │
│                                                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │ MetaMorpho Factory│  │ MetaMorpho Vaults│  │    Rewards      │  │
│  │                  │  │                  │  │   Distributor   │  │
│  │ • isMetaMorpho() │  │ • ERC-4626       │  │                 │  │
│  │ • Current factory│  │ • Multi-market   │  │ • Merkle proofs │  │
│  │ • Legacy factory │  │ • Optimized yield│  │ • claim()       │  │
│  │                  │  │ • P2P matching   │  │ • Token rewards │  │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

## Data Structures

Morpho uses standard ERC-4626 interfaces and does not define custom structs.

## State Variables

### Protocol Addresses
- `morphoRewards: public(address)` - Morpho rewards distributor contract
- `MORPHO_FACTORY: public(immutable(address))` - Current MetaMorpho factory contract
- `MORPHO_FACTORY_LEGACY: public(immutable(address))` - Legacy MetaMorpho factory contract

### Constants
- `MAX_TOKEN_PATH: constant(uint256) = 5` - Maximum tokens in path (unused)

## Constructor

### `__init__`

Initializes Morpho with Underscore Protocol and Morpho factory connections.

```vyper
@deploy
def __init__(
    _undyHq: address,
    _morphoFactory: address,
    _morphoFactoryLegacy: address,
    _morphoRewardsAddr: address,
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq contract address for Underscore Protocol |
| `_morphoFactory` | `address` | Current MetaMorpho factory contract address |
| `_morphoFactoryLegacy` | `address` | Legacy MetaMorpho factory contract address |
| `_morphoRewardsAddr` | `address` | Morpho rewards distributor address |

#### Returns

*Constructor does not return any values*

#### Access

Called only during contract deployment

#### Example Usage
```python
morpho_lego = boa.load(
    "contracts/legos/yield/Morpho.vy",
    undy_hq.address,
    morpho_factory.address,
    morpho_factory_legacy.address,
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

Returns the Morpho factory addresses.

```vyper
@view
@external
def getRegistries() -> DynArray[address, 10]:
```

#### Returns

| Type | Description |
|------|-------------|
| `DynArray[address, 10]` | Array containing both MetaMorpho factory addresses |

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
| `bool` | Always False - Morpho uses non-rebasing ERC-4626 shares |

## Yield Functions

### `depositForYield`

Deposits assets into MetaMorpho vaults using ERC-4626 standard.

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
| `_vaultAddr` | `address` | MetaMorpho vault address |
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

- `MorphoDeposit` - Contains deposit details including asset, vault, shares, and USD value

#### Example Usage
```python
# Deposit USDC to MetaMorpho vault
amount_deposited, vault_token, shares_received, usd_value = morpho_lego.depositForYield(
    usdc.address,
    1000 * 10**6,  # 1000 USDC
    metamorpho_usdc_vault.address,
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

Withdraws assets from MetaMorpho vaults by redeeming shares.

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

- `MorphoWithdrawal` - Contains withdrawal details including asset, vault, amounts, and USD value

#### Example Usage
```python
# Withdraw from MetaMorpho vault
shares_burned, asset, amount_received, usd_value = morpho_lego.withdrawFromYield(
    metamorpho_usdc_vault.address,
    100 * 10**18,  # 100 vault shares
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

Claims rewards from Morpho protocol using merkle proofs.

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
- Requires valid merkle proof

#### Example Usage
```python
# Claim rewards with proof
reward_amount, usd_value = morpho_lego.claimRewards(
    user.address,
    morpho_token.address,
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

- Morpho uses merkle proofs that must be computed off-chain
- No on-chain way to check claimable amounts

### `setMorphoRewardsAddr`

Updates the Morpho rewards distributor address.

```vyper
@external
def setMorphoRewardsAddr(_addr: address) -> bool:
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

- `MorphoRewardsAddrSet` - Contains new rewards address

## Query Functions

### `isVaultToken`

Checks if an address is a valid MetaMorpho vault.

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
| `bool` | True if valid MetaMorpho vault |

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

Registers a new MetaMorpho vault opportunity.

```vyper
@external
def addAssetOpportunity(_asset: address, _vaultAddr: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Underlying asset |
| `_vaultAddr` | `address` | MetaMorpho vault address |

#### Access

Only callable by switchboard addresses

#### Notes

- Validates vault through factories
- Sets unlimited approval for deposits
- Registers in YieldLegoData

### `removeAssetOpportunity`

Removes a MetaMorpho vault opportunity.

```vyper
@external
def removeAssetOpportunity(_asset: address, _vaultAddr: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Underlying asset |
| `_vaultAddr` | `address` | MetaMorpho vault address |

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

### `_isValidMorphoVault`

Validates vault through both factories.

```vyper
@view
@internal
def _isValidMorphoVault(_vaultToken: address) -> bool:
```

#### Logic

- Checks current factory with isMetaMorpho()
- Checks legacy factory with isMetaMorpho()
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

Morpho includes placeholder implementations for unsupported functions:

- DEX: `swapTokens()`
- Mint/Redeem: `mintOrRedeemAsset()`, `confirmMintOrRedeemAsset()`
- Lending: `addCollateral()`, `removeCollateral()`, `borrow()`, `repayDebt()`
- Liquidity: `addLiquidity()`, `removeLiquidity()`, `addLiquidityConcentrated()`, `removeLiquidityConcentrated()`
- Other: `getAccessForLego()`, `getPrice()`

All return zero values or empty results.

## Security Considerations

### Vault Validation
- All vaults verified through official factories
- Dual factory support for backward compatibility
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
is_eligible = morpho_lego.isEligibleVaultForTrialFunds(
    vault.address,
    asset.address
)

# 2. Deposit through Underscore
amount_in, vault_token, shares, usd = user_wallet.depositForYield(
    MORPHO_LEGO_ID,
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
share_price = morpho_lego.getPricePerShare(vault.address, 18)
expected_assets = shares * share_price // 10**18

# 2. Approve shares to wallet
vault.approve(user_wallet.address, shares)

# 3. Withdraw through Underscore
shares_burned, asset, amount_out, usd = user_wallet.withdrawFromYield(
    MORPHO_LEGO_ID,
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
initial_price = morpho_lego.getPricePerShare(vault.address, 18)
initial_value = initial_shares * initial_price // 10**18

# ... time passes, yield accrues ...

current_shares = vault.balanceOf(user)  # Same amount
current_price = morpho_lego.getPricePerShare(vault.address, 18)
current_value = current_shares * current_price // 10**18

yield_earned = current_value - initial_value
```

### Rewards Claiming Pattern
```python
# Get merkle proof off-chain
proof, amount = get_morpho_rewards_proof(user, reward_token)

# Claim through wallet
reward_amount, usd = user_wallet.claimRewards(
    MORPHO_LEGO_ID,
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

### MetaMorpho Vaults
- Aggregate yield across multiple markets
- Automated rebalancing for optimal rates
- Risk-adjusted allocations
- Professional curator management

### P2P Matching
- Morpho's core innovation
- Better rates than standard pools
- Fallback to pool rates when needed
- Transparent rate discovery

### Trial Fund Eligibility
- Requires $100k+ TVL
- Protects protocol funds
- Quality filter for vaults

## Testing

For comprehensive test examples, see: [`tests/legos/yields/`](../../../../tests/legos/yields/)