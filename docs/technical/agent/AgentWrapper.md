# AgentWrapper Technical Documentation

[📄 View Source Code](../../../contracts/core/agent/AgentWrapper.vy)

## Overview

AgentWrapper is a secure intermediary contract that enables managers (agents) to perform actions on user wallets through signature-based authentication. It serves as a wrapper around [UserWallet](../userWallet/UserWallet.md) functionality, implementing EIP-712 typed data signatures for secure off-chain authorization while maintaining the same interface as UserWallet for seamless integration. Manager permissions and limits are configured through the [HighCommand](../walletBackpack/HighCommand.md) module.

**Core Features**:
- **Signature-Based Authentication**: All actions require valid EIP-712 signatures from the wallet owner
- **Nonce Management**: Replay attack protection through sequential nonce tracking
- **Batch Operations**: Execute multiple wallet actions in a single transaction with output chaining
- **Complete UserWallet Coverage**: Mirrors all UserWallet functions with signature authentication

The contract enables automated wallet management scenarios where owners can delegate transaction execution to managers without giving up custody, perfect for portfolio management services, automated DeFi strategies, and gasless transaction patterns.

## Architecture & Modules

AgentWrapper inherits critical functionality through modular architecture:

### Ownership Module
- **Location**: `contracts/modules/Ownership.vy`
- **Purpose**: Provides secure ownership management with time-locked transfers
- **Documentation**: See [Ownership Technical Documentation](../modules/Ownership.md)
- **Key Features**:
  - Time-locked ownership transfers for agent wrapper control
  - Security override capabilities via MissionControl
  - Owner controls nonce increments and signature validation
- **Exported Interface**: All ownership functions exposed via `ownership.__interface__`

### Module Initialization
```vyper
initializes: ownership
exports: ownership.__interface__
```

## System Architecture Diagram

```
+-------------------------------------------------------------------------+
|                             AgentWrapper                                |
+-------------------------------------------------------------------------+
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                    Authentication Flow                            | |
|  |                                                                   | |
|  |  1. Manager prepares transaction parameters                       | |
|  |  2. Owner signs message off-chain (EIP-712)                      | |
|  |  3. Manager submits tx with signature to AgentWrapper            | |
|  |  4. AgentWrapper validates:                                       | |
|  |     - Signature authenticity                                      | |
|  |     - Nonce correctness                                           | |
|  |     - Expiration time                                              | |
|  |  5. AgentWrapper calls UserWallet function                       | |
|  |  6. UserWallet validates manager permissions                      | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                     Supported Operations                          | |
|  |                                                                   | |
|  |  Individual Functions:                                             | |
|  |    • transferFunds          • depositForYield                     | |
|  |    • withdrawFromYield      • rebalanceYieldPosition              | |
|  |    • swapTokens             • mintOrRedeemAsset                   | |
|  |    • addCollateral          • removeCollateral                    | |
|  |    • borrow                 • repayDebt                           | |
|  |    • claimRewards           • convertWethToEth/EthToWeth          | |
|  |    • addLiquidity           • removeLiquidity                     | |
|  |    • addLiquidityConc       • removeLiquidityConc                 | |
|  |                                                                   | |
|  |  Batch Operations:                                                | |
|  |    • performBatchActions - Chain multiple operations              | |
|  |    • Output from one action can be input to next                  | |
|  +-------------------------------------------------------------------+ |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                            UserWallet                                   |
|  • Validates manager has permission for the action                      |
|  • Executes the requested operation                                     |
|  • Returns results to AgentWrapper                                      |
+-------------------------------------------------------------------------+
```

## Data Structures

### Signature Struct
Contains signature data for authentication:
```vyper
struct Signature:
    signature: Bytes[65]    # ECDSA signature (r, s, v)
    nonce: uint256         # Sequential nonce for replay protection
    expiration: uint256    # Timestamp when signature expires
```

### ActionInstruction Struct
Defines a single action in batch operations:
```vyper
struct ActionInstruction:
    usePrevAmountOut: bool     # Use output from previous instruction
    action: uint8              # Action type code
    legoId: uint16            # Protocol/Lego ID
    asset: address            # Primary asset/token
    target: address           # Target address (varies by action)
    amount: uint256           # Primary amount
    asset2: address           # Secondary asset
    amount2: uint256          # Secondary amount or data (for rebalance operations action 12, this field is used for toLegoId)
    minOut1: uint256          # Minimum output for primary asset
    minOut2: uint256          # Minimum output for secondary asset
    tickLower: int24          # For concentrated liquidity
    tickUpper: int24          # For concentrated liquidity
    extraData: bytes32        # Protocol-specific data (for transfer operations action 1, the least significant bit is used as the isCheque flag)
    auxData: bytes32          # Packed auxiliary data (for removeLiquidity action 31, this holds the lpToken address; for concentrated liquidity actions 32-33, it packs the pool address and nftId)
    swapInstructions: DynArray[SwapInstruction, MAX_SWAP_INSTRUCTIONS]
```

### Action Type Codes
- 1: Transfer funds
- 2: WETH to ETH conversion
- 3: ETH to WETH conversion
- 10: Deposit for yield
- 11: Withdraw from yield
- 12: Rebalance yield position
- 20: Swap tokens
- 21: Mint/redeem asset
- 22: Confirm mint/redeem
- 30: Add liquidity
- 31: Remove liquidity
- 32: Add concentrated liquidity
- 33: Remove concentrated liquidity
- 40: Add collateral
- 41: Remove collateral
- 42: Borrow
- 43: Repay debt
- 50: Claim rewards

## State Variables

### Public State Variables
- `groupId: uint256` - Wallet group identifier
- `currentNonce: uint256` - Current nonce for signature validation

### Constants
- `MAX_INSTRUCTIONS: uint256 = 15` - Maximum batch instructions
- `MAX_SWAP_INSTRUCTIONS: uint256 = 5` - Maximum swap steps
- `MAX_TOKEN_PATH: uint256 = 5` - Maximum swap path length
- `ECRECOVER_PRECOMPILE: address` - Address for signature recovery
- `SIG_PREFIX: bytes32` - EIP-712 signature prefix

### Inherited Variables
From [Ownership module](../modules/Ownership.md):
- `owner: address` - Current owner who can sign transactions
- `ownershipTimeLock: uint256` - Time-lock for ownership changes
- `pendingOwner: PendingOwnerChange` - Pending ownership details

## Constructor

### `__init__`

Initializes the AgentWrapper with ownership settings and group ID.

```vyper
@deploy
def __init__(
    _undyHq: address,
    _owner: address,
    _groupId: uint256,
    _minTimeLock: uint256,
    _maxTimeLock: uint256,
):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq registry address |
| `_owner` | `address` | Initial owner who can sign |
| `_groupId` | `uint256` | Wallet group identifier |
| `_minTimeLock` | `uint256` | Minimum ownership time-lock |
| `_maxTimeLock` | `uint256` | Maximum ownership time-lock |

#### Access

Called only during deployment

## Transfer Functions

### `transferFunds`

Transfers funds from user wallet with signature authentication.

```vyper
@external
def transferFunds(
    _userWallet: address,
    _recipient: address,
    _asset: address = empty(address),
    _amount: uint256 = max_value(uint256),
    _isCheque: bool = False,
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User's wallet address |
| `_recipient` | `address` | Transfer recipient |
| `_asset` | `address` | Asset to transfer (empty for ETH) |
| `_amount` | `uint256` | Amount to transfer |
| `_isCheque` | `bool` | Whether this is a cheque payment |
| `_sig` | `Signature` | Owner's signature |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Amount transferred |
| `uint256` | USD value of transfer |

#### Authentication

Requires valid signature from wallet owner containing hash of all parameters

#### Example Usage
```python
# Owner signs transfer off-chain
message_hash = keccak256(encode(
    1,  # action type
    user_wallet,
    recipient,
    token,
    amount,
    nonce,
    expiration
))
signature = owner.sign(message_hash)

# Manager executes transfer
amount, usd_value = agent_wrapper.transferFunds(
    user_wallet,
    recipient,
    token,
    amount,
    False,
    Signature(signature, nonce, expiration),
    sender=manager
)
```

## Yield Management Functions

### `depositForYield`

Deposits assets into yield protocols with signature.

```vyper
@external
def depositForYield(
    _userWallet: address,
    _legoId: uint256,
    _asset: address,
    _vaultAddr: address = empty(address),
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, address, uint256, uint256):
```

Similar signature authentication pattern as transferFunds.

### `withdrawFromYield`

Withdraws assets from yield protocols.

```vyper
@external
def withdrawFromYield(
    _userWallet: address,
    _legoId: uint256,
    _vaultToken: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, address, uint256, uint256):
```

### `rebalanceYieldPosition`

Rebalances between yield positions.

```vyper
@external
def rebalanceYieldPosition(
    _userWallet: address,
    _fromLegoId: uint256,
    _fromVaultToken: address,
    _toLegoId: uint256,
    _toVaultAddr: address = empty(address),
    _fromVaultAmount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, address, uint256, uint256):
```

## Trading Functions

### `swapTokens`

Executes token swaps through integrated protocols.

```vyper
@external
def swapTokens(
    _userWallet: address,
    _swapInstructions: DynArray[SwapInstruction, MAX_SWAP_INSTRUCTIONS],
    _sig: Signature = empty(Signature),
) -> (address, uint256, address, uint256, uint256):
```

### `mintOrRedeemAsset`

Mints or redeems protocol-specific assets.

```vyper
@external
def mintOrRedeemAsset(
    _userWallet: address,
    _legoId: uint256,
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256 = max_value(uint256),
    _minAmountOut: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256, bool, uint256):
```

### `confirmMintOrRedeemAsset`

Confirms pending mint/redeem operations.

```vyper
@external
def confirmMintOrRedeemAsset(
    _userWallet: address,
    _legoId: uint256,
    _tokenIn: address,
    _tokenOut: address,
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
```

## Debt Management Functions

### `addCollateral`

Adds collateral to lending protocols.

```vyper
@external
def addCollateral(
    _userWallet: address,
    _legoId: uint256,
    _asset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
```

### `removeCollateral`

Removes collateral from lending protocols.

```vyper
@external
def removeCollateral(
    _userWallet: address,
    _legoId: uint256,
    _asset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
```

### `borrow`

Borrows assets from lending protocols.

```vyper
@external
def borrow(
    _userWallet: address,
    _legoId: uint256,
    _borrowAsset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
```

### `repayDebt`

Repays borrowed assets.

```vyper
@external
def repayDebt(
    _userWallet: address,
    _legoId: uint256,
    _paymentAsset: address,
    _paymentAmount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
```

## Rewards and Utility Functions

### `claimRewards`

Claims rewards from protocols.

```vyper
@external
def claimRewards(
    _userWallet: address,
    _legoId: uint256,
    _rewardToken: address = empty(address),
    _rewardAmount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
```

### `convertWethToEth`

Unwraps WETH to ETH.

```vyper
@external
def convertWethToEth(
    _userWallet: address,
    _amount: uint256 = max_value(uint256),
    _sig: Signature = empty(Signature)
) -> (uint256, uint256):
```

### `convertEthToWeth`

Wraps ETH to WETH.

```vyper
@external
def convertEthToWeth(
    _userWallet: address,
    _amount: uint256 = max_value(uint256),
    _sig: Signature = empty(Signature)
) -> (uint256, uint256):
```

## Liquidity Management Functions

### `addLiquidity`

Adds liquidity to AMM pools.

```vyper
@external
def addLiquidity(
    _userWallet: address,
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
    _sig: Signature = empty(Signature),
) -> (uint256, uint256, uint256, uint256):
```

### `removeLiquidity`

Removes liquidity from AMM pools.

```vyper
@external
def removeLiquidity(
    _userWallet: address,
    _legoId: uint256,
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _lpToken: address,
    _lpAmount: uint256 = max_value(uint256),
    _minAmountA: uint256 = 0,
    _minAmountB: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256, uint256, uint256):
```

### `addLiquidityConcentrated`

Adds liquidity to concentrated liquidity pools.

```vyper
@external
def addLiquidityConcentrated(
    _userWallet: address,
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
    _sig: Signature = empty(Signature),
) -> (uint256, uint256, uint256, uint256, uint256):
```

### `removeLiquidityConcentrated`

Removes liquidity from concentrated liquidity pools.

```vyper
@external
def removeLiquidityConcentrated(
    _userWallet: address,
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
    _sig: Signature = empty(Signature),
) -> (uint256, uint256, uint256, uint256):
```

## Batch Operations

### `performBatchActions`

Executes multiple actions in sequence with output chaining.

```vyper
@external
def performBatchActions(
    _userWallet: address,
    _instructions: DynArray[ActionInstruction, MAX_INSTRUCTIONS],
    _sig: Signature = empty(Signature),
) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | User's wallet address |
| `_instructions` | `DynArray[ActionInstruction, MAX_INSTRUCTIONS]` | Array of actions |
| `_sig` | `Signature` | Owner's signature |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Success status |

#### Features

- Execute up to 15 actions in one transaction
- Output from one action can be input to the next
- All actions must succeed or entire batch reverts
- Single signature covers all operations

#### Example Usage
```python
# Create batch instructions
instructions = [
    # Withdraw from yield
    ActionInstruction(
        action=11,  # withdraw
        legoId=aave_id,
        asset=aUSDC,
        amount=1000e6
    ),
    # Swap USDC to ETH (using previous output)
    ActionInstruction(
        usePrevAmountOut=True,
        action=20,  # swap
        swapInstructions=[...]
    ),
    # Wrap ETH to WETH (using previous output)
    ActionInstruction(
        usePrevAmountOut=True,
        action=3  # eth to weth
    )
]

# Owner signs batch
message_hash = keccak256(encode(
    user_wallet,
    instructions,
    nonce,
    expiration
))

# Manager executes batch
success = agent_wrapper.performBatchActions(
    user_wallet,
    instructions,
    Signature(signature, nonce, expiration),
    sender=manager
)
```

## Authentication Functions

### `incrementNonce`

Manually increments the nonce (invalidates current signatures).

```vyper
@external
def incrementNonce():
```

#### Access

Only callable by owner

#### Events Emitted

- `NonceIncremented` - Contains old and new nonce values

### `getNonce`

Returns the current nonce value.

```vyper
@view
@external
def getNonce() -> uint256:
```

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Current nonce |

#### Access

Public view function

## Internal Mechanisms

### Signature Validation

The contract implements EIP-712 typed data signatures:

1. **Message Hashing**: Each function creates a unique hash of all parameters
2. **Domain Separator**: The EIP-712 digest is created using a domain separator with the name hardcoded to 'UnderscoreAgent', the contract's chainId, and its own address
3. **Signature Components**: Extracts r, s, v from 65-byte signature
4. **Recovery**: Uses ecrecover precompile to get signer address
5. **Validation**: Ensures signer is the wallet owner

### Nonce Management

- Sequential nonce prevents replay attacks
- Each successful transaction increments nonce
- Owner can manually increment to invalidate signatures
- Nonce must match exactly (no gaps allowed)

### Expiration Handling

- Signatures include expiration timestamp
- Checked before expensive operations
- Prevents DoS from invalid signatures
- Owner controls validity period

### Batch Execution Flow

1. Validate single signature for entire batch
2. Execute instructions sequentially
3. Pass output amounts between actions
4. Revert entire batch on any failure
5. Return success status

## Security Considerations

### Authentication Security
- EIP-712 prevents signature replay across contracts/chains
- Sequential nonce prevents replay attacks
- Expiration limits signature lifetime
- Only wallet owner can create valid signatures

### Permission Model
- AgentWrapper only authenticates the signer
- UserWallet still validates manager permissions
- Double-layer security: signature + permissions
- Owner maintains ultimate control

### Signature Safety
- S-value validation prevents malleability
- V-value normalization for compatibility
- Zero address checks on recovery
- Domain separator prevents cross-contract replay

### Batch Operation Safety
- Atomic execution (all or nothing)
- Output validation between actions
- Gas limit considerations for large batches
- Clear action type validation

## Usage Patterns

### Gasless Transactions
Owners sign operations off-chain, managers pay gas:
1. Owner signs desired operations
2. Manager submits with their gas
3. UserWallet validates manager permissions
4. Operations execute on owner's behalf

### Automated Portfolio Management
Managers execute pre-approved strategies:
1. Owner signs batch operations with conditions
2. Manager monitors markets
3. When conditions met, manager executes
4. Strategies execute atomically

### Emergency Response
Quick action with owner approval:
1. Manager detects issue requiring action
2. Owner signs emergency operations
3. Manager executes immediately
4. Time-sensitive operations complete

## Testing

For comprehensive test examples, see: [`tests/core/agent/`](../../../tests/core/agent/)