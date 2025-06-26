# ActionInstruction Field Mapping Guide

This document provides a clear mapping of how ActionInstruction struct fields are used for each action type in AgentWrapper.vy.

## Field Usage by Action

### Action 0: TRANSFER
- `target`: recipient address
- `asset`: token to transfer
- `amount`: amount to transfer

### Action 1: EARN_DEPOSIT
- `legoId`: protocol ID
- `asset`: asset to deposit
- `target`: vault address
- `amount`: deposit amount

### Action 2: EARN_WITHDRAW  
- `legoId`: protocol ID
- `asset`: vault token
- `amount`: withdraw amount

### Action 3: EARN_REBALANCE ⚠️
- `legoId`: from protocol ID
- `asset`: from vault token
- `amount2`: **to protocol ID (NOT an amount!)** 
- `target`: to vault address
- `amount`: from vault amount

### Action 4: SWAP
- `swapInstructions`: array of swap instructions
- Other fields: unused

### Action 5: MINT_REDEEM
- `legoId`: protocol ID
- `asset`: token in
- `target`: token out
- `amount`: amount in
- `minOut1`: minimum amount out

### Action 6: CONFIRM_MINT_REDEEM
- `legoId`: protocol ID
- `asset`: token in
- `target`: token out

### Action 7: ADD_COLLATERAL
- `legoId`: protocol ID
- `asset`: collateral asset
- `amount`: collateral amount

### Action 8: REMOVE_COLLATERAL
- `legoId`: protocol ID
- `asset`: collateral asset
- `amount`: amount to remove

### Action 9: BORROW
- `legoId`: protocol ID
- `asset`: asset to borrow
- `amount`: borrow amount

### Action 10: REPAY_DEBT
- `legoId`: protocol ID
- `asset`: payment asset
- `amount`: repayment amount

### Action 11: REWARDS
- `legoId`: protocol ID
- `asset`: reward token
- `amount`: reward amount (NOT used as typical amount)

### Action 12: ETH_TO_WETH
- `amount`: ETH amount to convert

### Action 13: WETH_TO_ETH
- `amount`: WETH amount to convert

### Action 14: ADD_LIQ
- `legoId`: protocol ID
- `target`: pool address
- `asset`: token A
- `asset2`: token B
- `amount`: amount A
- `amount2`: amount B
- `minOut1`: min amount A
- `minOut2`: min amount B
- `auxData`: min LP amount (as uint256)

### Action 15: REMOVE_LIQ
- `legoId`: protocol ID
- `target`: pool address
- `asset`: token A
- `asset2`: token B
- `amount`: LP amount to remove
- `minOut1`: min amount A out
- `minOut2`: min amount B out
- `auxData`: LP token address (packed in lower 160 bits)

### Action 16: ADD_LIQ_CONC
- `legoId`: protocol ID
- `target`: NFT address
- `asset`: token A
- `asset2`: token B
- `amount`: amount A
- `amount2`: amount B
- `tickLower`: lower tick
- `tickUpper`: upper tick
- `minOut1`: min amount A
- `minOut2`: min amount B
- `auxData`: pool address (upper 160 bits) + NFT ID (lower 96 bits)

### Action 17: REMOVE_LIQ_CONC
- `legoId`: protocol ID
- `target`: NFT address
- `asset`: token A
- `asset2`: token B
- `amount`: liquidity to remove
- `minOut1`: min amount A out
- `minOut2`: min amount B out
- `auxData`: pool address (upper 160 bits) + NFT ID (lower 96 bits)

## Common Field Patterns

1. **extraAddr, extraVal, extraData**: Protocol-specific parameters used by all actions
2. **usePrevAmountOut**: When true, uses output from previous instruction as amount
3. **amount**: Primary amount field, but meaning varies by action
4. **target**: Multi-purpose field - can be recipient, vault, token out, or pool

## ⚠️ Key Gotchas

1. **Rebalance (Action 3)**: `amount2` is NOT an amount - it's the destination protocol ID
2. **auxData packing**: Actions 15-17 pack multiple values using bit operations
3. **Overloaded fields**: Same field names have different meanings per action
4. **Liquidity Removal Limitation**: When removing liquidity (actions 15 & 17), only tokenA amount is passed forward via `usePrevAmountOut`, even though both tokens are received. Plan batches accordingly.