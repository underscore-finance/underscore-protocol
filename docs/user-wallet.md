---
description: One wallet unifying 20+ DeFi protocols with automated payments and secure delegation
---

# User Wallet: Your DeFi Command Center

You're managing $100K+ across 5 protocols, but you're still copying addresses, approving tokens one by one, and checking rates manually like it's 2020.

The constant tab switching. The missed yield opportunities while you sleep. The anxiety every time you paste an address. The hours lost to manual operations that should take seconds.

**Underscore** unifies your entire DeFi experience into one powerful smart wallet. Direct access to 20+ protocols. Managers that optimize yields 24/7. Payment systems that actually work. Security that protects without restricting.

Finally, professional-grade DeFi tools without the complexity.

## Core Architecture

Underscore is a smart wallet system built on Base L2 that provides four key components:

1. **Unified Protocol Access**: Direct integration with 20+ DeFi protocols through standardized adapters
2. **Delegation System**: Managers who can execute strategies within defined boundaries
3. **Payment Rails**: Automated payment systems for recurring transfers and one-time payments
4. **Security Layers**: Time-locks, whitelists, and granular permissions protecting every operation

## Security Architecture

The wallet implements a hierarchical permission system:

```
OWNER → Full control, can modify all settings
  │
  ├── WHITELIST → Unlimited transfer access to trusted addresses
  │
  ├── MANAGERS → Delegated operators with specific permissions and limits
  │
  └── PAYEES → Pre-approved recipients with configured payment limits
```

**Access Control**:

- **Owner**: Complete control over wallet configuration and funds
- **Whitelist**: Time-locked additions, instant removal, unlimited transfers
- **Managers**: Can only execute permitted actions within spending limits
- **Payees**: Can only receive payments up to configured amounts
- **Others**: No access - all transfers and actions blocked

This architecture ensures that every transaction must pass through appropriate security checks before execution.

## Protocol Integration: The Lego System

Underscore connects to DeFi protocols through standardized adapters called "Legos". Each Lego provides a consistent interface for protocol-specific operations, enabling atomic multi-protocol transactions with optimized gas usage. New protocols integrate seamlessly through the Lego Book registry — your wallet gains new capabilities automatically without upgrades.

### Yield & Lending Protocols

**Integrated protocols**: Morpho, Moonwell, Aave, Euler, Fluid, Compound

**Capabilities**:

- Deposit assets to earn yield
- Withdraw funds with automatic unwinding
- Track yields and calculate profits
- Claim protocol rewards
- Rebalance between protocols

### Trading & DEX Integration

**Integrated DEXs**: Aerodrome, Uniswap, Curve

**Capabilities**:

- Swap tokens with smart routing (up to 5 hops)
- Add/remove liquidity with automatic ratio calculation
- Support for both standard (uni v2) and concentrated liquidity (uni v3+)
- Manage NFT positions and adjust ranges

### Debt Management

**Integrated protocols**: Ripe Protocol

**Capabilities**:

- Deposit any supported asset as collateral
- Borrow against collateral in GREEN or yield-bearing sGREEN
- Repay debt with any accepted token
- Earn and claim RIPE rewards

### Asset Transformations

**Capabilities**:

- ETH ↔ WETH conversion with zero slippage
- Mint and redeem receipt tokens (like stETH)
- Handle delayed redemptions
- Automatic format conversion for protocol requirements

### Rewards & Incentives

**Capabilities**:

- Batch claim rewards across all protocols in one transaction
- Auto-compound rewards into productive positions
- Track lifetime earnings across protocols

## Batch Operations: Multiple Actions, One Transaction

Underscore's architecture allows complex multi-step operations to execute atomically in a single transaction. This provides significant gas savings and eliminates the risk of partial execution.

### Examples of Batch Operations

**Yield Rebalancing**:

```
1. Withdraw from Aave (lower yield)
2. Deposit to Morpho (higher yield)
3. Claim rewards from both protocols
4. Convert rewards to productive assets
→ All in one transaction
```

**Complex Position Entry**:

```
1. Deposit collateral to Ripe Protocol
2. Borrow against collateral
3. Provide borrowed funds as liquidity
4. Stake LP tokens for additional yield
→ Complete strategy in one click
```

**Portfolio Rebalancing**:

```
1. Remove liquidity from multiple pools
2. Swap assets to target allocations
3. Re-deploy into new positions
4. Claim and reinvest all [rewards](rewards.md)
→ Entire rebalance atomically
```

## Core Features

### [Managers](managers.md): Delegated Operations

Managers are authorized operators — human or AI — who execute actions within your defined boundaries. They can trade, optimize yields, and manage payments, but cannot withdraw to external addresses or exceed your limits.

**Use cases**:

- 24/7 yield optimization by AI agents
- CFO handling vendor and contractor payments
- Professional traders managing portions of portfolio
- Automated debt position management
- Family members with emergency access

[→ Learn more about Managers](managers.md)

### [Payees](payees.md): Your Circle of Trust

Payees form your verified payment network — addresses that can only receive what you've pre-approved. Your funds earn yield until payment time, then transfer automatically. Only you can add addresses to this circle.

**Use cases**:

- Employee salaries paid from yield-earning funds
- Automated vendor and contractor payments
- Subscription services with pull payment capability
- Family allowances with monthly limits

[→ Learn more about Payees](payees.md)

### [Cheques](cheques.md): Digital Cheques with Control

Digital cheques bring the control of paper cheques to crypto — write payments that recipients cash on their schedule, cancel anytime before they do. Large amounts get automatic security delays. Your funds keep earning yield until payment.

**Use cases**:

- Contractor payments you can cancel if work isn't delivered
- Large transfers with built-in review time
- Social payments like splitting lunch ($30 to a friend)
- One-time vendor invoices with payment flexibility
- Any payment where you need an "undo" option

[→ Learn more about Cheques](cheques.md)

### [Whitelist](whitelist.md): Unlimited Trust

The whitelist breaks the emergency glass on your security — addresses that get unlimited transfers with no delays or limits. Time-locked additions protect against compromise, while instant removal maintains control.

**Use cases**:

- Hardware wallet for emergency fund access
- Corporate treasury requiring immediate consolidation
- Multi-wallet strategies for risk distribution
- Gnosis Safe for recovery if you lose access

[→ Learn more about Whitelist](whitelist.md)

## Architecture Comparison

| Traditional Multi-Wallet Setup      | Underscore Smart Wallet        |
| ----------------------------------- | ------------------------------ |
| Multiple interfaces and logins      | Single unified interface       |
| Manual token approvals per protocol | Pre-configured protocol access |
| External transfers between wallets  | Internal routing, no transfers |
| Manual yield tracking               | Automatic profit calculation   |
| Limited automation options          | Full delegation capabilities   |
| Separate security per wallet        | Unified security model         |

## Frequently Asked Questions

### 🔐 **Security & Control**

**Is this a self-custody wallet?**  
Yes, absolutely. You maintain complete control of your private keys and assets. Underscore provides the smart contract infrastructure, but only you can authorize transactions.

**What happens if Underscore disappears?**  
Your funds remain safe and accessible. The smart contracts are immutable and don't depend on Underscore's servers. You could interact with your wallet directly through BaseScan or any other interface.

**Can managers or automated strategies steal my funds?**  
No. Managers operate within strict, code-enforced boundaries. They can only perform the specific actions you've authorized, with the limits you've set. You can revoke access instantly at any time.

**How do I recover access if I lose my keys?**  
Use your whitelisted addresses (like your hardware wallet or Gnosis Safe) to recover funds. If you lose access to your owner wallet but still have manager access, managers can transfer funds to your whitelisted addresses - providing a recovery path even when the primary wallet is lost.

### 💰 **Costs & Fees**

**What are the fees?**

- **Swap fees**: Small percentage on token swaps (configurable by protocol)
- **Rewards fees**: Small percentage when claiming protocol rewards (configurable by protocol)
- **Yield fees**: Small percentage of profits when earning yield (configurable by protocol)
- **Revenue sharing**: Up to 50% of fees go back to users and ambassadors through [rewards](rewards.md)
- **No fees on**: Transfers, idle funds, deposits, debt operations, liquidity provision, or ETH/WETH wrapping
- **Full transparency**: Exact fee percentages shown before every transaction

### Technical Setup

**Which blockchain is this on?**  
Underscore runs on Base L2, providing Ethereum's security with significantly lower transaction costs.

**Can I use this with my existing wallet?**  
Yes. You deploy your Underscore smart wallet using your existing wallet (like MetaMask), which then acts as the owner key.

**What protocols can I access?**  
20+ protocols including Aave, Morpho, Compound (lending), Ripe Protocol (borrowing), Uniswap, Curve, Aerodrome (trading), and more. New protocols integrate automatically through the Lego system.

**What if Base L2 has issues?**  
Base inherits Ethereum's security model. In the unlikely event of L2 issues, established procedures exist for withdrawing assets to Ethereum mainnet. Your funds remain under your control.

---

## Your Move

Right now, while you're reading this, yields are compounding. Opportunities are emerging. Strategies are executing.

Just not yours.

Every day you delay is another day of:

- Manual approvals eating your time
- Missed yields while you sleep
- Anxiety about security
- Opportunities slipping through your fingers

Stop juggling wallets. Stop missing opportunities. Stop letting manual operations eat your time.

Your DeFi operations deserve professional tools. Deploy your Underscore wallet and take control of your financial future.

---

_One wallet. Every protocol. Total control._
