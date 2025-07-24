## Core DeFi Capabilities

Your wallet connects to DeFi protocols through standardized integrations called Legos. Each operation is optimized for gas efficiency and includes automatic profit tracking.

### How Your Wallet Tracks Yield

The wallet implements sophisticated yield tracking that works automatically:

**For Standard Yield Assets** (like aUSDC from Aave):
```
1. Deposit 10,000 USDC → Receive aUSDC
2. Wallet records price-per-share: 1.05
3. Month later, price-per-share: 1.08
4. Yield earned: (1.08/1.05 - 1) × 10,000 = 285.71 USDC
5. Protocol fee on profit: ~1-2% (2.86-5.71 USDC)
6. Net yield: 280-283 USDC
```

**For Rebasing Assets** (balance increases):
* Automatic detection of balance changes
* Yield calculated on every interaction
* No manual tracking needed

### Earning Yield

**Deposit & Withdraw Operations**:
```
Traditional Method:
1. Approve token: $8 gas
2. Deposit to protocol: $25 gas
3. Track position manually
Total: $33 gas + manual tracking

Underscore Wallet:
1. Single transaction: $28 gas
2. Automatic yield tracking
3. Position registered in wallet
Savings: ~15% gas + automated accounting
```

**Rebalance Positions** (Aave → Morpho example):
```
Traditional: 
- Withdraw from Aave: $30
- Approve Morpho: $8
- Deposit to Morpho: $25
- Total: $63 gas, 3 transactions

Underscore: 
- Single rebalance: $38 gas
- Savings: 40% gas, 1 transaction
- Yield profits calculated automatically
```

**Supported Protocols**: Aave V3, Morpho, Compound V3, Euler, Fluid, Moonwell
**Asset Limit**: Track up to 10 yield positions simultaneously

### Trading & Swapping

**Token Swap Capabilities**:
* Maximum 5 hops in a single transaction
* Automatic routing through multiple DEXs
* Swap fee: 0-5% cap (configurable)
* Supports Uniswap V2/V3, Aerodrome, Curve, and more

**Complex Swap Example**:
```
Swap 10,000 USDC → ETH → wstETH:
1. USDC → ETH via Uniswap V3
2. ETH → wstETH via Curve
Gas cost: $35 (vs $50+ if done separately)
Execution: Single transaction
```

**Liquidity Provision**:
```
Standard LP (Uniswap V2 style):
* Add liquidity: $40 gas
* Remove liquidity: $35 gas
* Auto-calculation of impermanent loss

Concentrated LP (Uniswap V3):
* Mint position: $120 gas
* Add to position: $80 gas
* NFT position tracking included
* Range adjustment capabilities
```

**DEX Integrations**: 10+ protocols including Uniswap, Curve, Balancer, Aerodrome

### Asset Management

**ETH/WETH Conversion**:
* Gas cost: ~$3-5
* No slippage or fees
* Instant execution
* Automatic balance updates

**NFT Management**:
* ERC-721 support
* Safe transfer implementation
* Recovery function for mistakes
* No storage limits

**Mint & Redeem Operations**:
```
Example: DAI → sDAI (Savings DAI)
* Mint sDAI: $15 gas
* Current rate: 5% APY
* Redeem anytime: $12 gas
* No lock-up periods
```

### Borrowing & Debt Management

**Collateral Operations**:
```
Example Setup:
* Deposit 10 ETH as collateral
* Borrow up to 5,000 USDC (50% LTV)
* Health factor monitoring: 1.5+
* Liquidation protection alerts
```

**Gas Costs**:
* Add collateral: $40
* Borrow assets: $60
* Repay debt: $35
* Remove collateral: $40

**Integrated Protocols**: Ripe Finance, with more coming

### Managing Rewards

**Automated Reward Claiming**:
```
Manual Process:
* Check each protocol: 10 min
* Claim rewards: $20 gas × 5 protocols
* Total: $100 gas + 30 min time

With AI Manager:
* Auto-monitors all positions
* Claims when gas-efficient
* Bundles multiple claims: $40 total
* Savings: 60% gas + 100% time
```

**Fee Structure**: 
* Reward claiming fee: 2-5% of rewards
* Applied only on successful claims
* No fee if no rewards available

### Gas Optimization Summary

| Operation | Traditional | Underscore | Savings |
|-----------|------------|------------|---------|
| Yield Rebalance | 3 txns, $63 | 1 txn, $38 | 40% |
| Complex Swap | 2-3 txns, $50+ | 1 txn, $35 | 30% |
| Reward Claims | 5 txns, $100 | 1 txn, $40 | 60% |
| LP Management | 2 txns, $48 | 1 txn, $40 | 17% |