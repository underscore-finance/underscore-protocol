# LootDistributor Technical Documentation

[📄 View Source Code](../../../contracts/core/LootDistributor.vy)

## Overview

LootDistributor is the comprehensive rewards and revenue share engine for the Underscore Protocol. As a Department contract, it manages all protocol fee distribution, yield bonuses, ambassador revenue sharing, and deposit rewards, ensuring proper incentive alignment between users, ambassadors, and the protocol while maintaining transparent and secure distribution mechanisms.

**Core Features**:
- **Ambassador Revenue Share**: Automatic distribution of swap, yield, and rewards fees to ambassadors
- **Yield Bonus System**: Performance-based bonuses paid in-kind or alternative assets
- **Deposit Rewards**: Points-based rewards system for protocol deposits
- **Claimable Loot Management**: Secure tracking and distribution of accumulated rewards
- **Fee Routing**: Intelligent fee collection from various protocol activities

The contract implements sophisticated distribution logic including period-based tracking with automatic resets, multi-asset reward accumulation, cooldown periods for claim security, and flexible bonus configurations per asset type.

## System Architecture Diagram

```
+-------------------------------------------------------------------------+
|                            LootDistributor                              |
+-------------------------------------------------------------------------+
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                      Revenue Flow Architecture                     | |
|  |                                                                   | |
|  |  1. Fee Collection:                                               | |
|  |     ├─> Swap fees from trading activities                         | |
|  |     ├─> Yield fees from profit realization                       | |
|  |     └─> Rewards fees from external claims                        | |
|  |                                                                   | |
|  |  2. Ambassador Revenue Share:                                     | |
|  |     ├─> Calculate ambassador's share based on action type        | |
|  |     ├─> Add to claimable loot for ambassador                     | |
|  |     └─> Track by asset for multi-asset support                   | |
|  |                                                                   | |
|  |  3. Yield Bonus Distribution:                                     | |
|  |     ├─> Check eligibility via YieldLego                           | |
|  |     ├─> Calculate bonus amount (in-kind or alt asset)            | |
|  |     ├─> Distribute to user and ambassador                        | |
|  |     └─> Respect available balance limits                         | |
|  |                                                                   | |
|  |  4. Deposit Rewards:                                              | |
|  |     ├─> Track deposit points based on USD value × time           | |
|  |     ├─> Pro-rata distribution when claimed                        | |
|  |     └─> Global tracking for fair distribution                     | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                    Claimable Asset Management                      | |
|  |                                                                   | |
|  |  Registration System:                                              | |
|  |    • Dynamic array of claimable assets per user                   | |
|  |    • Index mapping for O(1) lookups                               | |
|  |    • Automatic deregistration when balance = 0                    | |
|  |                                                                   | |
|  |  Claim Process:                                                   | |
|  |    1. Check cooldown period (if not switchboard)                  | |
|  |    2. Iterate through all claimable assets                        | |
|  |    3. Transfer available balances                                 | |
|  |    4. Update tracking and deregister if empty                     | |
|  |    5. Update last claim timestamp                                 | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                      Points Calculation Logic                      | |
|  |                                                                   | |
|  |  Deposit Points = USD Value × Blocks Held / 10^18                 | |
|  |                                                                   | |
|  |  User Rewards = Total Rewards × User Points / Global Points       | |
|  |                                                                   | |
|  |  Updates trigger on:                                               | |
|  |    • Deposit/withdrawal (value change)                             | |
|  |    • Rewards claim (points reset)                                  | |
|  |    • Manual update calls                                           | |
|  +-------------------------------------------------------------------+ |
+-------------------------------------------------------------------------+
```

## Module Integration

LootDistributor implements the Department interface and integrates:
- `Addys` module for address registry management
- `DeptBasics` module for pause functionality and basic department features

## Constants

- `HUNDRED_PERCENT: uint256 = 100_00` - 100% in basis points (100.00%)
- `EIGHTEEN_DECIMALS: uint256 = 10 ** 18` - Scaling factor for points
- `MAX_DEREGISTER_ASSETS: uint256 = 20` - Maximum assets to deregister per claim

## Constructor

### `__init__`

Initializes LootDistributor with registry integration.

```vyper
@deploy
def __init__(_undyHq: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq registry contract address |

#### Access

Called only during deployment

#### Example Usage
```python
loot_distributor = LootDistributor.deploy(
    undy_hq.address
)
```

## Revenue Flow Functions

### `addLootFromSwapOrRewards`

Collects fees from swap or rewards actions and distributes to ambassador.

```vyper
@external
def addLootFromSwapOrRewards(
    _asset: address,
    _feeAmount: uint256,
    _action: ws.ActionType,
    _missionControl: address = empty(address),
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Fee asset address |
| `_feeAmount` | `uint256` | Fee amount to collect |
| `_action` | `ActionType` | Type of action (SWAP or REWARDS) |
| `_missionControl` | `address` | Optional MissionControl address |

#### Access

Can only be called by user wallets

#### Events Emitted

- `TxFeePaid` - Contains asset (indexed), totalFee, ambassadorFeeRatio, ambassadorFee, ambassador (indexed), and action

#### Example Usage
```python
# From UserWallet during swap
loot_distributor.addLootFromSwapOrRewards(
    usdc.address,
    swap_fee_amount,
    ActionType.SWAP,
    mission_control.address
)

# From UserWallet during rewards claim
loot_distributor.addLootFromSwapOrRewards(
    reward_asset.address,
    rewards_fee,
    ActionType.REWARDS
)
```

#### Notes

- Fails gracefully if paused
- Transfers fee from caller (must be approved)
- Ambassador revenue share calculated based on action type
- No distribution if user has no ambassador

### `addLootFromYieldProfit`

Handles yield profit distribution including fees and bonuses.

```vyper
@external
def addLootFromYieldProfit(
    _asset: address,
    _feeAmount: uint256,
    _yieldRealized: uint256,
    _missionControl: address = empty(address),
    _appraiser: address = empty(address),
    _legoBook: address = empty(address),
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Yield asset address |
| `_feeAmount` | `uint256` | Fee amount (may be 0) |
| `_yieldRealized` | `uint256` | Total yield realized |
| `_missionControl` | `address` | Optional MissionControl |
| `_appraiser` | `address` | Optional Appraiser |
| `_legoBook` | `address` | Optional LegoBook |

#### Access

Can only be called by user wallets

#### Events Emitted

- `TxFeePaid` - If fee amount > 0 and ambassador exists
- `YieldBonusPaid` - For each bonus distribution (user and/or ambassador)

#### Example Usage
```python
# From UserWallet after yield harvest
loot_distributor.addLootFromYieldProfit(
    vault_token.address,
    yield_fee,          # Protocol fee
    total_yield,        # Total yield amount
    mission_control.address,
    appraiser.address,
    lego_book.address
)
```

#### Notes

- Fee already transferred to contract (no transferFrom)
- Checks eligibility for yield bonus via YieldLego
- Distributes bonus to user and/or ambassador based on ratios
- Supports in-kind, underlying asset, or alternative asset bonuses

## Claim Functions

### `claimRevShareAndBonusLoot`

Claims accumulated revenue share and bonus rewards.

```vyper
@external
def claimRevShareAndBonusLoot(_user: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User address to claim for |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Number of assets claimed |

#### Access

- User (wallet owner)
- Managers with `canClaimLoot` permission
- Switchboard addresses

#### Events Emitted

- `LootClaimed` - For each asset claimed, contains user (indexed), asset (indexed), and amount

#### Example Usage
```python
# User claims their rewards
num_claimed = loot_distributor.claimRevShareAndBonusLoot(
    user_wallet.address,
    sender=user
)

print(f"Claimed {num_claimed} different assets")
```

#### Notes

- Enforces cooldown period (except for switchboard)
- Automatically deregisters assets with zero balance
- Updates last claim timestamp
- Claims all available assets in one transaction

### `claimDepositRewards`

Claims accumulated deposit rewards based on points.

```vyper
@external
def claimDepositRewards(_user: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User address to claim for |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Amount of rewards claimed |

#### Access

Same as `claimRevShareAndBonusLoot`

#### Events Emitted

- `DepositRewardsClaimed` - Contains user (indexed), asset (indexed), userRewards, and remainingRewards

#### Example Usage
```python
# Claim deposit rewards
rewards_amount = loot_distributor.claimDepositRewards(
    user_wallet.address,
    sender=user
)
```

#### Notes

- Must be current LootDistributor (not migrated)
- Updates deposit points before calculation
- Pro-rata distribution based on points share
- Resets user points to 0 after claim

### `claimAllLoot`

Claims both revenue share/bonuses and deposit rewards.

```vyper
@external
def claimAllLoot(_user: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User address to claim for |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if any rewards were claimed |

#### Access

Same as other claim functions

#### Events Emitted

Combines events from both claim types

#### Example Usage
```python
# Claim everything in one transaction
success = loot_distributor.claimAllLoot(
    user_wallet.address,
    sender=user
)
```

## Deposit Points Functions

### `updateDepositPoints`

Updates deposit points for a user (switchboard only).

```vyper
@external
def updateDepositPoints(_user: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User to update points for |

#### Access

Only callable by switchboard addresses

### `updateDepositPointsWithNewValue`

Updates points with a new USD value.

```vyper
@external
def updateDepositPointsWithNewValue(_user: address, _newUsdValue: uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User to update |
| `_newUsdValue` | `uint256` | New total USD value |

#### Access

- User wallets
- Valid wallet configurations

#### Example Usage
```python
# Update after deposit/withdrawal
loot_distributor.updateDepositPointsWithNewValue(
    user_wallet.address,
    new_total_usd_value,
    sender=wallet_config
)
```

### `updateDepositPointsOnEjection`

Updates deposit points when a user wallet is ejected.

```vyper
@external
def updateDepositPointsOnEjection(_user: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User wallet being ejected |

#### Access

Only callable by switchboard addresses

#### Example Usage
```python
# Called during wallet ejection process
loot_distributor.updateDepositPointsOnEjection(
    ejected_wallet.address,
    sender=switchboard
)
```

#### Notes

- Fails gracefully if paused
- Sets USD value to 0 while preserving accumulated points
- Used specifically during wallet ejection scenarios

### `getLatestDepositPoints`

Calculates accumulated points since last update.

```vyper
@view
@external
def getLatestDepositPoints(_usdValue: uint256, _lastUpdate: uint256) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_usdValue` | `uint256` | USD value held |
| `_lastUpdate` | `uint256` | Last update block |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Accumulated points |

#### Access

Public view function

#### Example Usage
```python
# Calculate points for a position
points = loot_distributor.getLatestDepositPoints(
    usd_value=10000 * 10**18,  # $10,000
    last_update=last_update_block
)
```

#### Notes

- Returns 0 if USD value is 0 or last update is 0
- Formula: (USD Value × Blocks Elapsed) / 10^18
- Used internally for all points calculations

## Deposit Rewards Management

### `addDepositRewards`

Adds rewards to the deposit rewards pool.

```vyper
@external
def addDepositRewards(_asset: address, _amount: uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Reward asset (must match configured) |
| `_amount` | `uint256` | Amount to add |

#### Access

Anyone can add rewards

#### Events Emitted

- `DepositRewardsAdded` - Contains asset (indexed), addedAmount, newTotalAmount, and adder (indexed)

#### Example Usage
```python
# Protocol adds rewards
loot_distributor.addDepositRewards(
    undy_token.address,
    reward_amount,
    sender=treasury
)
```

### `recoverDepositRewards`

Recovers deposit rewards (emergency function).

```vyper
@external
def recoverDepositRewards(_recipient: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_recipient` | `address` | Address to receive recovered rewards |

#### Access

Only callable by switchboard addresses

#### Events Emitted

- `DepositRewardsRecovered` - Contains asset (indexed), recipient (indexed), and amount

## Administrative Functions

### `adjustLoot`

Adjusts claimable loot for a user (security function).

```vyper
@external
def adjustLoot(_user: address, _asset: address, _newClaimable: uint256) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User to adjust |
| `_asset` | `address` | Asset to adjust |
| `_newClaimable` | `uint256` | New claimable amount |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Success status |

#### Access

Only callable by switchboard addresses

#### Events Emitted

- `LootAdjusted` - Contains user (indexed), asset (indexed), and newClaimable

#### Notes

- Can only adjust down, not up
- Deregisters asset if set to 0
- Used for security/anti-fraud purposes

## View Functions

### `getTotalClaimableAssets`

Gets count of claimable assets for a user.

```vyper
@view
@external
def getTotalClaimableAssets(_user: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_user` | `address` | User to check |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Number of assets with claimable balance |

### `getSwapFee`

Gets swap fee for a token pair.

```vyper
@view
@external
def getSwapFee(_user: address, _tokenIn: address, _tokenOut: address, _missionControl: address = empty(address)) -> uint256:
```

### `getRewardsFee`

Gets rewards fee for an asset.

```vyper
@view
@external
def getRewardsFee(_user: address, _asset: address, _missionControl: address = empty(address)) -> uint256:
```

### `validateCanClaimLoot`

Checks if caller can claim loot for user.

```vyper
@view
@external
def validateCanClaimLoot(_user: address, _caller: address) -> bool:
```

### `isValidWalletConfig`

Validates if a caller is the wallet configuration for a user wallet.

```vyper
@view
@external
def isValidWalletConfig(_wallet: address, _caller: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_wallet` | `address` | User wallet address |
| `_caller` | `address` | Address to validate as wallet config |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if caller is the valid wallet config |

#### Access

Public view function

#### Example Usage
```python
# Check if caller is valid config
is_valid = loot_distributor.isValidWalletConfig(
    user_wallet.address,
    potential_config.address
)
```

#### Notes

- Used for permission validation
- Checks if wallet is registered in Ledger
- Verifies caller matches wallet's config address

### `getLootDistroConfig`

Gets complete distribution configuration for an asset.

```vyper
@view
@external
def getLootDistroConfig(_wallet: address, _asset: address, _shouldGetLegoInfo: bool = False) -> LootDistroConfig:
```

## Internal Distribution Logic

### Ambassador Revenue Share

Revenue share ratios vary by action type:
- **Swap fees**: Uses `ambassadorRevShare.swapRatio`
- **Yield fees**: Uses `ambassadorRevShare.yieldRatio`
- **Rewards fees**: Uses `ambassadorRevShare.rewardsRatio`

### Yield Bonus Distribution

Bonus calculation follows priority:
1. **Alternative asset**: If configured, converts to alt asset using prices
2. **Underlying asset**: If vault token, converts using price per share
3. **In-kind**: Same asset as yield

Distribution ratios:
- User bonus: `bonusRatio` percentage of yield
- Ambassador bonus: `ambassadorBonusRatio` percentage of yield

### Points Calculation

Deposit points formula:
```
Points = USD Value × (Current Block - Last Update) / 10^18
```

User rewards calculation:
```
User Rewards = Total Rewards × User Points / Global Points
```

## Security Considerations

### Access Control
- User wallet validation for fee collection
- Manager permissions for claims
- Switchboard privileges for admin functions
- Cooldown periods for claim security

### Value Protection
- Balance checks before transfers
- Reserved amount tracking for deposit rewards
- Minimum transfer validation
- Graceful failure on pause

### State Management
- Atomic updates for points
- Proper deregistration of empty assets
- Global tracking for fair distribution
- Period-based cooldowns

## Common Integration Patterns

### Fee Collection Flow
```python
# In UserWallet after swap
fee_amount = calculate_swap_fee(amount)
if fee_amount > 0:
    # Approve LootDistributor
    token.approve(loot_distributor, fee_amount)
    
    # Send fee
    loot_distributor.addLootFromSwapOrRewards(
        token.address,
        fee_amount,
        ActionType.SWAP
    )
```

### Yield Distribution Flow
```python
# In UserWallet after yield harvest
yield_profit = calculate_yield_profit()
fee = yield_profit * fee_ratio / 10000

# Transfer fee to LootDistributor first
if fee > 0:
    token.transfer(loot_distributor, fee)

# Notify about yield
loot_distributor.addLootFromYieldProfit(
    vault_token.address,
    fee,
    yield_profit,
    mission_control,
    appraiser,
    lego_book
)
```

### Claim Pattern
```python
# Check if can claim
if loot_distributor.validateCanClaimLoot(user, caller):
    # Get claimable count
    num_assets = loot_distributor.getTotalClaimableAssets(user)
    
    if num_assets > 0:
        # Claim everything
        success = loot_distributor.claimAllLoot(user)
```

### Points Update Pattern
```python
# On deposit/withdrawal
new_usd_value = calculate_portfolio_value()
loot_distributor.updateDepositPointsWithNewValue(
    user_wallet,
    new_usd_value
)

# On user ejection
loot_distributor.updateDepositPointsOnEjection(user_wallet)
```

## Testing

For comprehensive test examples, see: [`tests/core/test_loot_distributor.py`](../../../tests/core/test_loot_distributor.py)