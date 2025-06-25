# Agent Contract Optimization Guide

## Overview

The optimized Agent contract reduces the ActionInstruction struct from 26 fields to 17 fields, achieving approximately 35% reduction in size. This optimization reduces gas costs for batch operations while maintaining full functionality and compatibility with the Wallet interface.

## Key Changes

### 1. Struct Optimization

**Original Struct (26 fields):**
- Individual fields for every possible parameter across all action types
- Many fields unused for most actions
- Large memory footprint

**Optimized Struct (17 fields):**
```vyper
struct ActionInstruction:
    # Core action data (packed when possible)
    usePrevAmountOut: bool
    action: uint8          # Reduced from full ActionType enum
    legoId: uint16         # Reduced from uint256
    
    # Primary fields (reused based on action type)
    asset: address         # Primary asset/token
    target: address        # Vault/pool/recipient/nftAddr
    amount: uint256        # Primary amount
    
    # Secondary fields (for complex actions)
    asset2: address        # Secondary asset (tokenB, etc)
    amount2: uint256       # Secondary amount
    minOut1: uint256       # Min amount out / minAmountA
    minOut2: uint256       # Min amount out B / minLpAmount
    
    # Tick values (only for concentrated liquidity)
    tickLower: int24
    tickUpper: int24
    
    # Extra params (always available as per Wallet interface)
    extraAddr: address
    extraVal: uint256
    extraData: bytes32
    
    # Additional encoding field for complex actions (not passed to wallet functions)
    auxData: bytes32    # For encoding pool addresses, minLpAmount, etc.
    
    # Swap instructions (only used for SWAP action)
    swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS]
```

### 2. Field Mapping by Action Type

| Action | asset | target | amount | asset2 | amount2 | minOut1 | minOut2 | Special Notes |
|--------|-------|--------|--------|--------|---------|---------|---------|---------------|
| EARN_DEPOSIT | asset | vaultAddr | amount | - | - | - | - | - |
| EARN_WITHDRAW | vaultToken | - | amount | - | - | - | - | - |
| EARN_REBALANCE | fromVaultToken | toVaultAddr | amount | - | toLegoId | - | - | fromLegoId in legoId field |
| SWAP | - | - | - | - | - | - | - | Uses swapInstructions array |
| MINT_REDEEM | tokenIn | tokenOut | amountIn | - | - | minAmountOut | - | - |
| CONFIRM_MINT_REDEEM | tokenIn | tokenOut | - | - | - | - | - | - |
| ADD_COLLATERAL | asset | - | amount | - | - | - | - | - |
| REMOVE_COLLATERAL | asset | - | amount | - | - | - | - | - |
| BORROW | borrowAsset | - | amount | - | - | - | - | - |
| REPAY_DEBT | paymentAsset | - | amount | - | - | - | - | - |
| ADD_LIQ | tokenA | pool | amountA | tokenB | amountB | minAmountA | minAmountB | minLpAmount in auxData |
| ADD_LIQ_CONC | tokenA | nftAddr | amountA | tokenB | amountB | minAmountA | minAmountB | pool+nftTokenId in auxData, uses tickLower/tickUpper |
| REMOVE_LIQ | tokenA | pool | lpAmount | tokenB | - | minAmountA | minAmountB | lpToken in auxData |
| REMOVE_LIQ_CONC | tokenA | nftAddr | liqToRemove | tokenB | - | minAmountA | minAmountB | pool+nftTokenId in auxData |
| TRANSFER | asset | recipient | amount | - | - | - | - | - |
| REWARDS | rewardToken | - | rewardAmount | - | - | - | - | - |
| ETH_TO_WETH | - | - | amount | - | - | - | - | - |
| WETH_TO_ETH | - | - | amount | - | - | - | - | - |

### 3. Special Handling

#### Important: Extra Parameters
The `extraAddr`, `extraVal`, and `extraData` fields are preserved as dedicated fields because they are part of the Wallet interface and are used by nearly all functions. They cannot be reused for other purposes.

#### Liquidity Operations
- **ADD_LIQ**: minLpAmount is encoded as uint256 in auxData
- **ADD_LIQ_CONC**: pool address is encoded in the first 20 bytes of auxData (shifted left by 96 bits), nftTokenId in the last 12 bytes
- **REMOVE_LIQ**: lpToken address is encoded in the last 20 bytes of auxData
- **REMOVE_LIQ_CONC**: pool address is encoded in the first 20 bytes of auxData (shifted left by 96 bits), nftTokenId in the last 12 bytes

#### Rebalance Operation
- fromLegoId is stored in the main legoId field
- toLegoId is stored in amount2 field as uint256

## Migration Instructions

### For Frontend/SDK Integration

1. **Update ActionInstruction Construction:**
```python
# Old way
instruction = {
    'usePrevAmountOut': False,
    'action': ActionType.EARN_DEPOSIT,
    'legoId': 1,
    'asset': token_address,
    'vaultAddr': vault_address,
    'amount': amount,
    'altLegoId': 0,
    'altAsset': ZERO_ADDRESS,
    # ... many unused fields
}

# New way
instruction = {
    'usePrevAmountOut': False,
    'action': 0,  # EARN_DEPOSIT as uint8
    'legoId': 1,
    'asset': token_address,
    'target': vault_address,
    'amount': amount,
    'asset2': ZERO_ADDRESS,
    'amount2': 0,
    'minOut1': 0,
    'minOut2': 0,
    'tickLower': 0,
    'tickUpper': 0,
    'extraAddr': extra_address,
    'extraVal': extra_value,
    'extraData': extra_data,
    'auxData': empty_bytes32,
    'swapInstructions': []
}
```

2. **Update Action Type Encoding:**
- Actions must be encoded as uint8 (0-17) instead of enum values
- See _convertActionType function for mapping

### For Smart Contract Integration

1. **Deploy new Agent contract** with optimized struct
2. **Update any contracts** that interact with Agent to use new struct format
3. **Update signature generation** to use new EIP-712 type hash

## Gas Savings

Estimated savings per batch operation:
- Calldata: ~35% reduction (from 26 to 17 fields)
- Memory operations: ~30% reduction
- Storage operations: Unchanged (no storage changes)

For a typical 5-instruction batch:
- Old: ~150,000 gas
- New: ~105,000 gas
- Savings: ~45,000 gas (30%)

## Backwards Compatibility

The optimized Agent contract is NOT backwards compatible. A migration is required:
1. Deploy new Agent contract
2. Transfer ownership from old to new
3. Update all integrated systems
4. Deprecate old Agent contract

## Security Considerations

1. **Field Reuse**: Ensure correct mapping of fields for each action type
2. **Encoding**: Special care needed for concentrated liquidity operations
3. **Validation**: All existing validation logic is preserved
4. **Signatures**: EIP-712 signatures must be regenerated with new type hash