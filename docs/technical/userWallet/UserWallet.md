# UserWallet Technical Documentation

[📄 View Source Code](../../../contracts/core/userWallet/UserWallet.vy)

## Overview

UserWallet is the core wallet contract for the Underscore Protocol that manages all user asset interactions, yield farming operations, and transaction functionality. It serves as the primary entry point for users to interact with the protocol's extensive DeFi integrations while maintaining security, flexibility, and comprehensive asset tracking.

**Core Features**:
- **Asset Management**: Handles ETH and ERC20 token transfers with built-in yield tracking and USD value calculations
- **Yield Operations**: Comprehensive yield farming support including deposits, withdrawals, and position rebalancing
- **DeFi Integrations**: Swapping, liquidity provision (standard and concentrated), debt management, and rewards claiming
- **Security Controls**: Permission-based access control through [UserWalletConfig](UserWalletConfig.md), time-locked operations, and trial fund management

The wallet implements sophisticated yield profit tracking for rebasing and non-rebasing assets, automated fee distribution for protocol sustainability, flexible Lego Partner integrations through [LegoTools](../legos/LegoTools.md) for external protocols, and comprehensive event logging for transaction transparency. Management operations can be delegated through the [AgentWrapper](../agent/AgentWrapper.md) system.

## System Architecture Diagram

```
+-------------------------------------------------------------------------+
|                              UserWallet                                 |
+-------------------------------------------------------------------------+
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                       Core Components                             | |
|  |                                                                   | |
|  |  * WalletConfig: Permission management and action validation      | |
|  |  * Asset Registry: Tracks all wallet assets and balances          | |
|  |  * Yield Tracker: Monitors yield profits and price per share      | |
|  |  * Lego Integration: Connects to external DeFi protocols          | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                      Action Categories                            | |
|  |                                                                   | |
|  |  Transfer & Payments:                                             | |
|  |    - transferFunds (normal, cheque, special)                      | |
|  |    - ETH/WETH conversions                                         | |
|  |                                                                   | |
|  |  Yield Management:                                                | |
|  |    - depositForYield / withdrawFromYield                          | |
|  |    - rebalanceYieldPosition                                       | |
|  |    - Automatic yield profit calculation                           | |
|  |                                                                   | |
|  |  Trading & Exchange:                                              | |
|  |    - swapTokens (multi-hop support)                               | |
|  |    - mintOrRedeemAsset / confirmMintOrRedeemAsset                | |
|  |                                                                   | |
|  |  Liquidity Operations:                                            | |
|  |    - addLiquidity / removeLiquidity (standard)                    | |
|  |    - addLiquidityConcentrated / removeLiquidityConcentrated       | |
|  |                                                                   | |
|  |  Debt Management:                                                 | |
|  |    - addCollateral / removeCollateral                             | |
|  |    - borrow / repayDebt                                           | |
|  |                                                                   | |
|  |  Rewards:                                                         | |
|  |    - claimRewards (with automatic fee handling)                   | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                    External Integrations                          | |
|  |                                                                   | |
|  |  * Appraiser: USD value calculations and yield profit tracking    | |
|  |  * LootDistributor: Fee collection and distribution               | |
|  |  * LegoBook: Registry of integrated DeFi protocols                | |
|  |  * Hatchery: Trial fund management                                | |
|  |  * MissionControl: Protocol-wide configuration                    | |
|  +-------------------------------------------------------------------+ |
+-------------------------------------------------------------------------+
```

## Data Structures

### WalletAssetData Struct
Tracks comprehensive data for each asset in the wallet:
```vyper
struct WalletAssetData:
    assetBalance: uint256        # Current balance of the asset
    usdValue: uint256           # USD value of holdings
    isYieldAsset: bool          # Whether asset generates yield
    lastPricePerShare: uint256  # For yield tracking (non-rebasing)
```

### ActionData Struct
Contains all necessary data for executing wallet actions:
```vyper
struct ActionData:
    signer: address             # Address initiating the action
    billing: address            # Billing address for the wallet
    legoId: uint256            # ID of lego partner (if applicable)
    legoAddr: address          # Address of lego partner contract
    walletConfig: address      # WalletConfig contract address
    appraiser: address         # Appraiser contract address
    lootDistributor: address   # LootDistributor contract address
    ledger: address            # Ledger contract address
    missionControl: address    # MissionControl contract address
    legoBook: address          # LegoBook registry address
    hatchery: address          # Hatchery contract address
    eth: address               # ETH placeholder address
    weth: address              # WETH contract address
    lastTotalUsdValue: uint256 # Previous total USD value
    isFrozen: bool            # Whether wallet is frozen
    inEjectMode: bool         # Emergency withdrawal mode
```

### SwapInstruction Struct
Defines parameters for token swaps:
```vyper
struct SwapInstruction:
    legoId: uint256                              # Lego partner to use
    amountIn: uint256                            # Input amount
    minAmountOut: uint256                        # Minimum output required
    tokenPath: DynArray[address, MAX_TOKEN_PATH]  # Token swap path
    poolPath: DynArray[bytes32, MAX_TOKEN_PATH]   # Pool identifiers
```

## State Variables

### Public State Variables
- `walletConfig: address` - Associated WalletConfig contract
- `assetData: HashMap[address, WalletAssetData]` - Asset data mapping
- `assets: HashMap[uint256, address]` - Index to asset mapping
- `indexOfAsset: HashMap[address, uint256]` - Asset to index mapping
- `numAssets: uint256` - Total number of registered assets

### Transient State Variables
- `checkedYield: HashMap[address, bool]` - Tracks yield checks per transaction

### Immutable Variables
- `WETH: address` - WETH contract address
- `ETH: address` - ETH placeholder address

### Constants
- `HUNDRED_PERCENT: uint256 = 100_00` - 100.00% in basis points
- `MAX_SWAP_INSTRUCTIONS: uint256 = 5` - Maximum swap steps
- `MAX_TOKEN_PATH: uint256 = 5` - Maximum tokens in swap path
- `MAX_ASSETS: uint256 = 10` - Maximum assets per action
- `MAX_LEGOS: uint256 = 10` - Maximum lego partners per action
- `API_VERSION: String[28] = "0.1.0"` - Contract version

## Constructor

### `__init__`

Initializes the UserWallet with essential contract addresses.

```vyper
@deploy
def __init__(
    _wethAddr: address,
    _ethAddr: address,
    _walletConfig: address,
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_wethAddr` | `address` | WETH contract address |
| `_ethAddr` | `address` | ETH placeholder address |
| `_walletConfig` | `address` | WalletConfig contract address |

#### Returns

*Constructor does not return any values*

#### Access

Called only during deployment

#### Example Usage
```python
wallet = UserWallet.deploy(
    weth.address,
    ETH_ADDRESS,
    wallet_config.address
)
```

## Transfer Functions

### `transferFunds`

Transfers funds to a recipient with various modes (normal, cheque, special).

```vyper
@external
def transferFunds(
    _recipient: address,
    _asset: address = empty(address),
    _amount: uint256 = max_value(uint256),
    _isCheque: bool = False,
    _isSpecialTx: bool = False,
) -> (uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_recipient` | `address` | Recipient address |
| `_asset` | `address` | Asset to transfer (empty for ETH) |
| `_amount` | `uint256` | Amount to transfer (max_value for all) |
| `_isCheque` | `bool` | Whether this is a cheque payment |
| `_isSpecialTx` | `bool` | Whether this is a special transaction |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Amount transferred |
| `uint256` | USD value of transfer |

#### Access

External function requiring appropriate permissions

#### Events Emitted

- `WalletAction` - op=1, contains transfer details

#### Example Usage
```python
# Transfer 100 USDC
amount, usd_value = wallet.transferFunds(
    recipient.address,
    usdc.address,
    100 * 10**6,
    sender=user.address
)

# Transfer all ETH
amount, usd_value = wallet.transferFunds(
    recipient.address,
    sender=user.address
)
```

## Yield Management Functions

### `depositForYield`

Deposits assets into yield-generating protocols.

```vyper
@external
def depositForYield(
    _legoId: uint256,
    _asset: address,
    _vaultAddr: address = empty(address),
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, address, uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_legoId` | `uint256` | Lego partner ID for yield protocol |
| `_asset` | `address` | Asset to deposit |
| `_vaultAddr` | `address` | Specific vault address (optional) |
| `_amount` | `uint256` | Amount to deposit |
| `_extraData` | `bytes32` | Protocol-specific data |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Amount of asset deposited |
| `address` | Vault token received |
| `uint256` | Amount of vault tokens received |
| `uint256` | USD value of transaction |

#### Access

External function requiring EARN_DEPOSIT permission

#### Events Emitted

- `WalletAction` - op=10, contains deposit details

#### Example Usage
```python
# Deposit USDC to Aave
asset_amount, vault_token, vault_amount, usd_value = wallet.depositForYield(
    AAVE_LEGO_ID,
    usdc.address,
    amount=1000 * 10**6,
    sender=user.address
)
```

### `withdrawFromYield`

Withdraws assets from yield-generating protocols.

```vyper
@external
def withdrawFromYield(
    _legoId: uint256,
    _vaultToken: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _isSpecialTx: bool = False,
) -> (uint256, address, uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_legoId` | `uint256` | Lego partner ID |
| `_vaultToken` | `address` | Vault token to redeem |
| `_amount` | `uint256` | Amount to withdraw |
| `_extraData` | `bytes32` | Protocol-specific data |
| `_isSpecialTx` | `bool` | Whether this is a special transaction |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Amount of vault tokens burned |
| `address` | Underlying asset received |
| `uint256` | Amount of underlying received |
| `uint256` | USD value of transaction |

#### Access

External function requiring EARN_WITHDRAW permission

#### Events Emitted

- `WalletAction` - op=11, contains withdrawal details

### `rebalanceYieldPosition`

Rebalances between yield positions in a single transaction.

```vyper
@external
def rebalanceYieldPosition(
    _fromLegoId: uint256,
    _fromVaultToken: address,
    _toLegoId: uint256,
    _toVaultAddr: address = empty(address),
    _fromVaultAmount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, address, uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_fromLegoId` | `uint256` | Source lego partner ID |
| `_fromVaultToken` | `address` | Vault token to withdraw from |
| `_toLegoId` | `uint256` | Destination lego partner ID |
| `_toVaultAddr` | `address` | Destination vault address |
| `_fromVaultAmount` | `uint256` | Amount to rebalance |
| `_extraData` | `bytes32` | Protocol-specific data |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Amount of underlying asset moved |
| `address` | New vault token received |
| `uint256` | Amount of new vault tokens |
| `uint256` | USD value of transaction |

#### Access

External function requiring EARN_REBALANCE permission

#### Events Emitted

- `WalletAction` - op=12, contains rebalance details

## Trading Functions

### `swapTokens`

Executes token swaps through multiple protocols.

```vyper
@external
def swapTokens(
    _instructions: DynArray[SwapInstruction, MAX_SWAP_INSTRUCTIONS]
) -> (address, uint256, address, uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_instructions` | `DynArray[SwapInstruction, MAX_SWAP_INSTRUCTIONS]` | Swap instructions |

#### Returns

| Type | Description |
|------|-------------|
| `address` | Input token address |
| `uint256` | Input amount |
| `address` | Output token address |
| `uint256` | Output amount (after fees) |
| `uint256` | USD value of transaction |

#### Access

External function requiring SWAP permission

#### Events Emitted

- `WalletAction` - op=20, contains swap details

#### Example Usage
```python
# Single swap USDC -> ETH
instructions = [{
    'legoId': UNISWAP_LEGO_ID,
    'amountIn': 1000 * 10**6,
    'minAmountOut': 0.3 * 10**18,
    'tokenPath': [usdc.address, weth.address],
    'poolPath': [pool_id]
}]

token_in, amount_in, token_out, amount_out, usd_value = wallet.swapTokens(
    instructions,
    sender=user.address
)
```

### `mintOrRedeemAsset`

Mints or redeems protocol-specific assets (e.g., stETH, rETH).

```vyper
@external
def mintOrRedeemAsset(
    _legoId: uint256,
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256 = max_value(uint256),
    _minAmountOut: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256, bool, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_legoId` | `uint256` | Lego partner ID |
| `_tokenIn` | `address` | Input token |
| `_tokenOut` | `address` | Output token |
| `_amountIn` | `uint256` | Input amount |
| `_minAmountOut` | `uint256` | Minimum output required |
| `_extraData` | `bytes32` | Protocol-specific data |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Input amount used |
| `uint256` | Output amount received |
| `bool` | Whether operation is pending |
| `uint256` | USD value of transaction |

#### Access

External function requiring MINT_REDEEM permission

#### Events Emitted

- `WalletAction` - op=21, contains mint/redeem details

## Liquidity Management Functions

### `addLiquidity`

Adds liquidity to standard AMM pools.

```vyper
@external
def addLiquidity(
    _legoId: uint256,
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _amountA: uint256 = max_value(uint256),
    _amountB: uint256 = max_value(uint256),
    _minAmountA: uint256 = 0,
    _minAmountB: uint256 = 0,
    _minLpAmount: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256, uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_legoId` | `uint256` | Lego partner ID |
| `_pool` | `address` | Pool address |
| `_tokenA` | `address` | First token |
| `_tokenB` | `address` | Second token |
| `_amountA` | `uint256` | Amount of token A |
| `_amountB` | `uint256` | Amount of token B |
| `_minAmountA` | `uint256` | Minimum token A to add |
| `_minAmountB` | `uint256` | Minimum token B to add |
| `_minLpAmount` | `uint256` | Minimum LP tokens to receive |
| `_extraData` | `bytes32` | Protocol-specific data |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | LP tokens received |
| `uint256` | Token A amount added |
| `uint256` | Token B amount added |
| `uint256` | USD value of transaction |

#### Access

External function requiring ADD_LIQ permission

#### Events Emitted

- `WalletAction` - op=30, contains liquidity addition details

### `removeLiquidity`

Removes liquidity from standard AMM pools.

```vyper
@external
def removeLiquidity(
    _legoId: uint256,
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _lpToken: address,
    _lpAmount: uint256 = max_value(uint256),
    _minAmountA: uint256 = 0,
    _minAmountB: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256, uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_legoId` | `uint256` | Lego partner ID |
| `_pool` | `address` | Pool address |
| `_tokenA` | `address` | First token |
| `_tokenB` | `address` | Second token |
| `_lpToken` | `address` | LP token to burn |
| `_lpAmount` | `uint256` | Amount of LP tokens to burn |
| `_minAmountA` | `uint256` | Minimum token A to receive |
| `_minAmountB` | `uint256` | Minimum token B to receive |
| `_extraData` | `bytes32` | Protocol-specific data |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Token A amount received |
| `uint256` | Token B amount received |
| `uint256` | LP tokens burned |
| `uint256` | USD value of transaction |

#### Access

External function requiring REMOVE_LIQ permission

#### Events Emitted

- `WalletAction` - op=31, contains liquidity removal details

#### Example Usage
```python
# Remove liquidity from Uniswap pool
amount_a, amount_b, lp_burned, usd_value = wallet.removeLiquidity(
    UNISWAP_LEGO_ID,
    pool.address,
    token_a.address,
    token_b.address,
    lp_token.address,
    lp_amount=100 * 10**18,
    sender=user.address
)
```

### `addLiquidityConcentrated`

Adds liquidity to concentrated liquidity pools (e.g., Uniswap V3).

```vyper
@external
def addLiquidityConcentrated(
    _legoId: uint256,
    _nftAddr: address,
    _nftTokenId: uint256,
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _amountA: uint256 = max_value(uint256),
    _amountB: uint256 = max_value(uint256),
    _tickLower: int24 = min_value(int24),
    _tickUpper: int24 = max_value(int24),
    _minAmountA: uint256 = 0,
    _minAmountB: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256, uint256, uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_legoId` | `uint256` | Lego partner ID |
| `_nftAddr` | `address` | NFT position manager address |
| `_nftTokenId` | `uint256` | Existing NFT token ID (0 for new) |
| `_pool` | `address` | Pool address |
| `_tokenA` | `address` | First token |
| `_tokenB` | `address` | Second token |
| `_amountA` | `uint256` | Amount of token A |
| `_amountB` | `uint256` | Amount of token B |
| `_tickLower` | `int24` | Lower tick boundary |
| `_tickUpper` | `int24` | Upper tick boundary |
| `_minAmountA` | `uint256` | Minimum token A to add |
| `_minAmountB` | `uint256` | Minimum token B to add |
| `_extraData` | `bytes32` | Protocol-specific data |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Liquidity amount added |
| `uint256` | Token A amount added |
| `uint256` | Token B amount added |
| `uint256` | NFT token ID |
| `uint256` | USD value of transaction |

#### Access

External function requiring ADD_LIQ_CONC permission

#### Events Emitted

- `WalletActionExt` - op=32, contains concentrated liquidity details

### `removeLiquidityConcentrated`

Removes liquidity from concentrated liquidity pools (e.g., Uniswap V3).

```vyper
@external
def removeLiquidityConcentrated(
    _legoId: uint256,
    _nftAddr: address,
    _nftTokenId: uint256,
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _liqToRemove: uint256 = max_value(uint256),
    _minAmountA: uint256 = 0,
    _minAmountB: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256, uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_legoId` | `uint256` | Lego partner ID |
| `_nftAddr` | `address` | NFT position manager address |
| `_nftTokenId` | `uint256` | NFT token ID representing position |
| `_pool` | `address` | Pool address |
| `_tokenA` | `address` | First token |
| `_tokenB` | `address` | Second token |
| `_liqToRemove` | `uint256` | Amount of liquidity to remove |
| `_minAmountA` | `uint256` | Minimum token A to receive |
| `_minAmountB` | `uint256` | Minimum token B to receive |
| `_extraData` | `bytes32` | Protocol-specific data |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Token A amount received |
| `uint256` | Token B amount received |
| `uint256` | Liquidity removed |
| `uint256` | USD value of transaction |

#### Access

External function requiring REMOVE_LIQ_CONC permission

#### Events Emitted

- `WalletActionExt` - op=33, contains concentrated liquidity removal details

#### Example Usage
```python
# Remove liquidity from Uniswap V3 position
amount_a, amount_b, liq_removed, usd_value = wallet.removeLiquidityConcentrated(
    UNISWAP_V3_LEGO_ID,
    nft_manager.address,
    position_nft_id,
    pool.address,
    token_a.address,
    token_b.address,
    liq_to_remove=1000000,
    sender=user.address
)
```

#### Notes

- The NFT is temporarily transferred to the lego partner during the operation
- If the position is fully depleted, the NFT may be burned
- The function validates that the NFT is returned if the position is not depleted

## Debt Management Functions

**Note**: These debt management functions assume there is no vault token involved (i.e., they are designed for protocols like Ripe Protocol). For protocols that use vault tokens to represent debt positions, you should use the `depositForYield` and `withdrawFromYield` functions instead.

### `addCollateral`

Adds collateral to lending protocols.

```vyper
@external
def addCollateral(
    _legoId: uint256,
    _asset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_legoId` | `uint256` | Lego partner ID |
| `_asset` | `address` | Collateral asset |
| `_amount` | `uint256` | Amount to add |
| `_extraData` | `bytes32` | Protocol-specific data |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Amount deposited |
| `uint256` | USD value of transaction |

#### Access

External function requiring ADD_COLLATERAL permission

#### Events Emitted

- `WalletAction` - op=40, contains collateral details

### `removeCollateral`

Removes collateral from lending protocols.

```vyper
@external
def removeCollateral(
    _legoId: uint256,
    _asset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_legoId` | `uint256` | Lego partner ID |
| `_asset` | `address` | Collateral asset to remove |
| `_amount` | `uint256` | Amount to remove |
| `_extraData` | `bytes32` | Protocol-specific data |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Amount removed |
| `uint256` | USD value of transaction |

#### Access

External function requiring REMOVE_COLLATERAL permission

#### Events Emitted

- `WalletAction` - op=41, contains collateral removal details

#### Example Usage
```python
# Remove ETH collateral from lending protocol
amount_removed, usd_value = wallet.removeCollateral(
    LENDING_LEGO_ID,
    weth.address,
    amount=1 * 10**18,  # 1 ETH
    sender=user.address
)
```

### `borrow`

Borrows assets from lending protocols.

```vyper
@external
def borrow(
    _legoId: uint256,
    _borrowAsset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_legoId` | `uint256` | Lego partner ID |
| `_borrowAsset` | `address` | Asset to borrow |
| `_amount` | `uint256` | Amount to borrow |
| `_extraData` | `bytes32` | Protocol-specific data |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Amount borrowed |
| `uint256` | USD value of transaction |

#### Access

External function requiring BORROW permission

#### Events Emitted

- `WalletAction` - op=42, contains borrow details

### `repayDebt`

Repays borrowed assets.

```vyper
@external
def repayDebt(
    _legoId: uint256,
    _paymentAsset: address,
    _paymentAmount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_legoId` | `uint256` | Lego partner ID |
| `_paymentAsset` | `address` | Asset to repay with |
| `_paymentAmount` | `uint256` | Amount to repay |
| `_extraData` | `bytes32` | Protocol-specific data |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Amount repaid |
| `uint256` | USD value of transaction |

#### Access

External function requiring REPAY_DEBT permission

#### Events Emitted

- `WalletAction` - op=43, contains repayment details

## Rewards Functions

### `claimRewards`

Claims rewards from protocols with automatic fee handling.

```vyper
@external
def claimRewards(
    _legoId: uint256,
    _rewardToken: address = empty(address),
    _rewardAmount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_legoId` | `uint256` | Lego partner ID |
| `_rewardToken` | `address` | Expected reward token |
| `_rewardAmount` | `uint256` | Expected amount |
| `_extraData` | `bytes32` | Protocol-specific data |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Reward amount (after fees) |
| `uint256` | USD value of transaction |

#### Access

External function requiring REWARDS permission

#### Events Emitted

- `WalletAction` - op=50, contains reward details

## ETH/WETH Conversion Functions

### `convertWethToEth`

Unwraps WETH to ETH.

```vyper
@external
def convertWethToEth(_amount: uint256 = max_value(uint256)) -> (uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_amount` | `uint256` | Amount to unwrap |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Amount converted |
| `uint256` | USD value |

#### Access

External function requiring WETH_TO_ETH permission

#### Events Emitted

- `WalletAction` - op=2, contains conversion details

### `convertEthToWeth`

Wraps ETH to WETH.

```vyper
@payable
@external
def convertEthToWeth(_amount: uint256 = max_value(uint256)) -> (uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_amount` | `uint256` | Amount to wrap |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Amount converted |
| `uint256` | USD value |

#### Access

External function requiring ETH_TO_WETH permission

#### Events Emitted

- `WalletAction` - op=3, contains conversion details

## Asset Management Functions

### `updateAssetData`

Updates asset tracking data (called by WalletConfig).

```vyper
@external
def updateAssetData(
    _legoId: uint256,
    _asset: address,
    _shouldCheckYield: bool,
    _prevTotalUsdValue: uint256,
    _ad: ActionData = empty(ActionData),
) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_legoId` | `uint256` | Lego ID for action data |
| `_asset` | `address` | Asset to update |
| `_shouldCheckYield` | `bool` | Whether to check for yield profits |
| `_prevTotalUsdValue` | `uint256` | Previous total USD value |
| `_ad` | `ActionData` | Pre-populated action data |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | New total USD value |

#### Access

Only callable by WalletConfig

### `deregisterAsset`

Removes an asset from tracking when balance is zero.

```vyper
@external
def deregisterAsset(_asset: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_asset` | `address` | Asset to deregister |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Success status |

#### Access

Only callable by WalletConfig

## Utility Functions

### `recoverNft`

Recovers NFTs sent to the wallet.

```vyper
@external
def recoverNft(_collection: address, _nftTokenId: uint256, _recipient: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_collection` | `address` | NFT collection address |
| `_nftTokenId` | `uint256` | Token ID |
| `_recipient` | `address` | Recipient address |

#### Access

Only callable by WalletConfig

### `setLegoAccessForAction`

Sets protocol-specific permissions for lego partners.

```vyper
@external
def setLegoAccessForAction(_legoAddr: address, _action: ActionType) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_legoAddr` | `address` | Lego partner address |
| `_action` | `ActionType` | Action type requiring access |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Success status |

#### Access

Only callable by WalletConfig

### `onERC721Received`

Handles safe NFT transfers to the wallet.

```vyper
@view
@external
def onERC721Received(
    _operator: address,
    _owner: address,
    _tokenId: uint256,
    _data: Bytes[1024]
) -> bytes4:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_operator` | `address` | Address performing the transfer |
| `_owner` | `address` | Previous owner |
| `_tokenId` | `uint256` | NFT token ID |
| `_data` | `Bytes[1024]` | Additional data |

#### Returns

| Type | Description |
|------|-------------|
| `bytes4` | ERC721 receiver selector |

#### Access

Public view function

### `apiVersion`

Returns the contract version.

```vyper
@pure
@external
def apiVersion() -> String[28]:
```

#### Returns

| Type | Description |
|------|-------------|
| `String[28]` | Version string ("0.1.0") |

#### Access

Public pure function

## Internal Mechanisms

### Yield Profit Tracking

The wallet automatically tracks yield profits for both rebasing and non-rebasing yield assets:

1. **Non-rebasing assets**: Tracks `lastPricePerShare` to calculate profits
2. **Rebasing assets**: Compares current balance to stored balance
3. **Automatic fee collection**: Yield profits trigger fee payments to LootDistributor
4. **Per-transaction tracking**: Uses transient storage to avoid duplicate checks

### Permission System

All actions require permission checks through WalletConfig:

1. **Signer validation**: Ensures caller has permission for the action
2. **Asset validation**: Checks if assets are allowed for the action
3. **Limit enforcement**: Validates transaction limits for managers/recipients
4. **Special transactions**: WalletConfig can perform trusted operations

### Asset Registration

The wallet maintains an efficient asset registry:

1. **Automatic registration**: Assets are registered on first interaction
2. **Balance tracking**: Stores balance and USD value for each asset
3. **Deregistration**: Assets with zero balance can be removed
4. **Index mapping**: Bidirectional mapping for efficient lookups

### Fee Handling

The protocol collects fees on specific operations:

1. **Yield fees**: Up to 25% on yield profits
2. **Swap fees**: Configurable per user/asset pair (max 5%)
3. **Rewards fees**: Configurable per user/asset (max 25%)
4. **Automatic collection**: Fees are transferred during operations

## Security Considerations

### Access Control
- All functions check permissions through WalletConfig
- Special transactions limited to WalletConfig only
- Manager limits enforced for non-billing signers

### Reentrancy Protection
- State changes occur before external calls
- Approvals are reset after each operation

### Asset Safety
- Maximum approval limits for each operation
- Automatic approval cleanup after use
- Balance checks before operations
- Slippage protection through minimum amounts

### Emergency Features
- Eject mode for emergency withdrawals
- Wallet freezing capability
- Trial fund clawback mechanism
- NFT recovery function

## Testing

For comprehensive test examples, see: [`tests/core/userWallet/`](../../../tests/core/userWallet/)