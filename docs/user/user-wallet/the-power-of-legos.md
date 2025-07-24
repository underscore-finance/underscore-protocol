## The Power of Legos

Legos are standardized protocol integrations that expand your wallet's capabilities without requiring upgrades or migrations. Each Lego undergoes security review and uses common interfaces for consistent behavior.

### Technical Architecture

```
Your Wallet
    ↓
LegoTools (Router)
    ↓
Individual Legos (Protocol Adapters)
    ↓
External DeFi Protocols
```

**Key Properties**:
- Registry-based discovery (LegoBook)
- Standardized interfaces
- Permission-based access control
- Atomic multi-protocol operations

### What This Means for You

**Automatic Protocol Access**: New Lego integrations become available without any action from you. When a new yield protocol launches and gets integrated, your existing wallet can immediately use it.

**Unified Experience**: One wallet address, one interface, access to 20+ protocols. No more juggling different apps or remembering which wallet holds which position.

**Consistent Security**: Every Lego inherits your wallet's security settings:
- Manager permissions apply across all protocols
- USD limits work everywhere
- Time-locks protect all operations

### Real Integration Examples

**Cross-Protocol Yield Farming**:
```
Morning: $50,000 USDC in wallet
AI Manager executes:
1. 40% → Aave (6% APY)
2. 30% → Morpho (7% APY)
3. 30% → Compound (5.5% APY)

Single transaction, $45 gas
Weighted average yield: 6.15%
Extra income vs single protocol: $75/year
```

**Complex DeFi Strategy**:
```
Starting with 10 ETH:
1. Deposit 5 ETH to Aave as collateral
2. Borrow 7,500 USDC against it
3. Swap 2,500 USDC → USDT on Curve
4. Provide USDC/USDT liquidity on Uniswap V3
5. Remaining 3 ETH → stETH via Lido (when available)

Traditional: 8-10 transactions, $200+ gas
Underscore: Could be 2-3 transactions, $100 gas
Time saved: 20 minutes
```

### Growing Ecosystem

**Currently Integrated** (20+ protocols):

**Yield Protocols** (6 integrated):
- Aave V3: $10B+ TVL, 3-8% APY on stables
- Morpho: Optimized rates, often 0.5-1% better than Aave
- Compound V3: USDC focused, 4-6% typical
- Euler: Multi-asset, competitive rates
- Fluid: Innovative lending mechanics
- Moonwell: Multi-chain yields

**DEX Protocols** (8+ integrated):
- Uniswap V2/V3: $3B+ liquidity
- Curve: Stablecoin specialist, minimal slippage
- Aerodrome: Optimism's leading DEX
- Balancer: Multi-asset pools
- Plus 4+ additional DEXs

**Other Protocols**:
- Ripe Finance: Collateralized debt positions
- More integrations monthly

### Technical Constraints

Being transparent about current limitations:

**Per-Transaction Limits**:
- Maximum 5 swap hops
- Up to 10 assets tracked
- 5 Lego protocols per complex operation

**Gas Considerations**:
- Simple operations: $10-30
- Complex strategies: $50-150
- Mainnet only (L2s coming)

**Not Yet Supported**:
- Leveraged/perpetual trading
- Options protocols
- Cross-chain operations
- Some newer experimental protocols

### The Power of Composability

**Today's Example**: 
Your $100,000 portfolio managed through one wallet:
- 40% earning yield across 3 protocols
- 30% providing liquidity on 2 DEXs
- 20% as collateral for borrowing
- 10% liquid for opportunities

**Monthly Operations**:
- 5 rebalances by AI Manager
- 10 reward claims automated
- Gas saved: ~$200 vs manual
- Time saved: 3-4 hours
- Extra yield from optimization: ~$100

**Future Potential**:
As each new Lego is added, your capabilities multiply. When liquid staking Legos arrive, your ETH positions can earn staking rewards without lockups. When RWA Legos launch, you'll access tokenized treasuries. All without moving funds or learning new interfaces.

Your wallet becomes more valuable with time, not obsolete.