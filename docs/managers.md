# Managers: The Autonomous Operators of Your Underscore Wallet

You've been doing DeFi wrong. Manually claiming rewards at 3am. Missing arbitrage opportunities while you sleep. Watching yields evaporate because you couldn't rebalance fast enough.

Enter **Managers** — the game-changing delegation system that lets your wallet work as hard as you do. Grant specific permissions to trusted operators, AI agents, or professional services. Set unbreakable spending limits enforced by smart contracts. Revoke access instantly if anything seems off.

This isn't your grandfather's power of attorney. This is programmable, revocable, limited delegation that puts you in complete control while enabling 24/7 optimization.

## Core Concept: Delegation Without Trust

Traditional finance forces an impossible choice: keep full control and miss opportunities, or hand over your keys and pray. Underscore Managers create a third option:

```
Traditional:   Give someone your credit card → Hope they don't max it out
Underscore:    Give someone a virtual card → Hard-coded $1,000 limit → Auto-expires in 30 days
```

### Who Can Be a Manager?

**Human Operators**

- Family members with emergency access
- Business partners handling operations
- Team members paying approved vendors
- Professional traders executing strategies

**AI Agents**

- Yield optimization bots working 24/7
- Rebalancing algorithms maintaining portfolios
- DCA bots executing regular purchases
- Arbitrage hunters capturing opportunities

**Professional Services**

- Registered financial advisors
- Institutional trading desks
- Yield aggregator protocols
- Automated market makers

### The Two-Phase Security Model

Every Manager action passes through two validation phases, ensuring comprehensive protection:

```
Phase 1: Pre-Action Validation        Phase 2: Post-Action Validation
├─ Manager active?                    ├─ Under per-tx USD limit?
├─ Action permitted?                  ├─ Under period USD limit?
├─ Asset allowed?                     ├─ Under lifetime USD limit?
├─ Protocol allowed?                  └─ Update tracking data
└─ Cooldown passed?
```

Both phases execute atomically within the transaction — if any check fails, the entire action reverts.

### Global vs Specific Settings

Underscore employs a dual-layer configuration system where the most restrictive settings always apply:

**Global Manager Settings**

- Master template for all managers in your wallet
- Sets maximum boundaries no manager can exceed
- Includes `canOwnerManage` flag determining if you're subject to limits

**Specific Manager Settings**

- Individual configuration per manager
- Can be more restrictive than global, never less
- Both global AND specific permissions must allow an action

```
Example: Permission Hierarchy
Global: Can trade = Yes, Max per tx = $100k
Manager A: Can trade = Yes, Max per tx = $50k → Limited to $50k
Manager B: Can trade = No, Max per tx = $200k → Cannot trade at all
```

## Permissions: What Managers Can Do

### DeFi Operations

| Permission           | Capability                            | Example Use Case                     |
| -------------------- | ------------------------------------- | ------------------------------------ |
| **Manage Yield**     | Deposit/withdraw from yield protocols | Auto-compound Aave positions daily   |
| **Buy & Sell**       | Swap tokens, rebalance portfolios     | Maintain 60/40 ETH/USDC ratio        |
| **Manage Debt**      | Handle loans and collateral           | Keep 150% collateralization          |
| **Manage Liquidity** | Provide/remove DEX liquidity          | Optimize Uniswap V3 ranges           |
| **Claim Rewards**    | Harvest protocol incentives           | Collect and reinvest farming rewards |

### Transfer & Payment Operations

| Permission            | Capability                       | Example Use Case        |
| --------------------- | -------------------------------- | ----------------------- |
| **General Transfers** | Send assets to any address       | Pay monthly expenses    |
| **Create Cheques**    | Schedule one-time payments       | Delayed vendor payments |
| **Propose Payees**    | Add recurring payment recipients | Onboard new contractors |

### Administrative Operations

| Permission                 | Capability                    | Example Use Case            |
| -------------------------- | ----------------------------- | --------------------------- |
| **Whitelist Management**   | Add/remove approved addresses | Maintain vendor list        |
| **Claim Protocol Rewards** | Harvest Underscore incentives | Auto-claim platform rewards |
| **Claim Loot**             | Collect revenue share         | Maximize protocol earnings  |

## Controls: Security Boundaries

### Financial Limits

**Per-Transaction Limits**

- Maximum USD value for any single transaction
- Example: $5,000 cap prevents large one-time losses

**Period-Based Limits**

- Total USD value allowed within recurring time windows
- Periods reset automatically (daily, weekly, monthly)
- Example: $10,000 per week for trading operations

```
Week 1: Use $7k of $10k limit → Week 2: Fresh $10k limit
Unused amounts don't roll over — each period starts clean
```

**Lifetime Limits**

- Cumulative USD cap over Manager's entire tenure
- Example: $500,000 total for year-long AI service

### Operational Controls

**Transaction Cooldown**

- Mandatory waiting period between transactions
- Measured in blocks (e.g., 1,800 blocks ≈ 1 hour)
- Prevents rapid-fire mistakes or attacks

**Asset Restrictions**

- Limit Manager to specific tokens (e.g., only stablecoins)
- Granular control over what can be touched
- Maximum 40 different assets per manager

**Protocol Restrictions (Legos)**

- Restrict to specific DeFi protocols by ID
- Each protocol ("Lego") registered in LegoBook
- Example: Only allow Aave and Compound interactions
- Maximum 25 different protocols per manager

**Payee Restrictions**

- Limit transfers to pre-approved addresses only
- Perfect for business operations with known vendors
- Maximum 40 approved [payees](payees.md) per manager

**Fail on Zero Price**

- Safety feature blocking transactions when asset price is $0
- Prevents trading during oracle failures
- Protects against manipulation when prices unavailable

### Time-Based Security

**Activation Delay**

- New Managers wait before permissions activate
- Configurable: 1 hour (emergency) to 7 days (high-value)
- Time to verify additions and cancel if suspicious

**Activation Length**

- Set Manager expiration periods
- Auto-revoke after: 30 days (trial), 90 days (quarterly), 365 days (annual)
- No action needed — permissions end automatically

## Real-World Configurations

### The Conservative Yield Farmer

```
Manager: YieldMaxAI Bot
Permissions: Manage Yield, Claim Rewards
Assets: USDC, USDT, DAI only
Protocols: Aave, Compound, Yearn
Limits: $20k/tx, $100k/month, $1M lifetime
Cooldown: 6 hours between moves
Activation: 7-day delay, 180-day duration
Result: +3-5% APY through optimization
```

### The Business Operations Manager

```
Manager: Trusted CFO
Permissions: Transfers only
Assets: USDC only
[Payees](payees.md): 10 verified vendor addresses
Limits: $2.5k/tx, $25k/week
Cooldown: 1 hour minimum
Activation: 24-hour delay, 90-day duration
Result: Streamlined payments without treasury access
```

### The Emergency Access System

```
Manager: Family Member
Permissions: Transfers only
Assets: USDC only
Limits: $10k lifetime cap
Cooldown: None (emergency use)
Activation: 1-hour delay
Result: Quick help without compromising savings
```

### The Professional Trading Desk

```
Manager: InstitutionalTradingCo
Permissions: Buy & Sell, Manage Liquidity
Assets: ETH, WBTC, USDC, USDT
Protocols: Uniswap, Curve, Balancer
Limits: $50k/tx, $500k/week, $10M lifetime
Cooldown: 10 minutes
Activation: 3-day delay, 365-day duration
Result: Institutional strategies in personal wallet
```

## Lifecycle Management

### Manager States

```
Added → Waiting → Active → Expired
  │        │         │        │
  └────────┴─────────┴────────┴─→ Removable anytime
           │         │
           │         └─→ Extendable (resets expiry)
           │
           └─→ Cancellable before activation
```

### Administrative Hierarchy

**You (The Owner)**

- Add, update, remove any Manager
- Modify all settings and limits
- Extend activation periods
- Ultimate control always

**The Manager**

- Can only remove themselves
- Cannot modify permissions
- Cannot add other Managers
- Prevents permission escalation

**Protocol Security (MissionControl)**

- Emergency Manager removal only
- Cannot add or modify
- Last-resort safety net

## Advanced Integration: Professional AI Services

The most powerful Manager implementations come from professional services that provide sophisticated strategies:

### How Professional Services Work

1. **Service Registration**: AI company deploys their AgentWrapper contract
2. **You Add as Manager**: Grant their contract specific permissions
3. **Atomic Execution**: Service executes complex strategies in single transactions
4. **Gas Abstraction**: Many services pay gas fees for you
5. **Performance Tracking**: Real-time reporting and analytics

### The Starter Agent

New wallets can include a pre-configured "Starter Agent" with:

- **Immediate Activation**: No waiting period (0 block delay)
- **Limited Permissions**: Basic operations to explore features
- **Educational Purpose**: Learn how managers work risk-free
- **Easy Removal**: Delete anytime once comfortable
- **Example**: Demo yield optimizer showing 2-3% APY gains

### Example: Institutional Yield Optimizer

```
Your Setup:
- Portfolio: $250,000 in stablecoins
- Manager: ProfessionalYieldAI
- Permissions: Manage Yield, Claim Rewards
- Limits: $50k/tx, $500k/month
- Allowed Protocols: Aave, Compound, Morpho, Yearn

What Happens:
1. AI monitors 20+ yield sources every block
2. Spots Morpho at 12% vs Aave's 8%
3. Executes: Withdraw Aave → Deposit Morpho (atomic)
4. Auto-harvests and compounds every 8 hours
5. Sends weekly performance reports

Results:
- Base yield: 8% = $20,000/year
- Optimized: 11% = $27,500/year
- Extra profit: $7,500/year
- Your effort: Zero
```

## Security Best Practices

### Start Conservative

- Test new Managers with small limits
- Use short activation periods initially
- Increase limits after proving reliability

### Layer Your Defenses

- Combine multiple restrictions (assets + protocols + payees)
- Use cooldowns to slow potential attacks
- Set period limits well below lifetime limits

### Monitor Actively

- Check Manager activity regularly
- Set up alerts for large transactions
- Review and adjust permissions quarterly

### Emergency Procedures

1. **Immediate**: Call removeManager() — instant revocation
2. **If Unable**: MissionControl can emergency remove
3. **Prevention**: Conservative limits and short activations

## Common Questions

**Can managers add other managers?**
No. Only the wallet owner can add new managers. This prevents permission escalation attacks.

**What happens when a manager expires?**
They automatically lose all permissions. No action needed from you.

**Can I change limits without removing the manager?**
Yes. Use updateManager to modify permissions, limits, and allowed assets/protocols anytime.

**Do unused period limits roll over?**
No. Each period starts fresh with the full limit. Use it or lose it.

**Can managers see my full portfolio?**
Managers can only interact with assets you've specifically allowed them to access.

## Working with Other Features

### Managers and Payees
- Managers can transfer to approved [payees](payees.md) within their limits
- Add payee restrictions to limit manager transfers to known addresses
- Perfect for accounts payable roles with vendor payment access

### Managers and Cheques
- Managers can create [cheques](cheques.md) within their spending limits
- Cheque amounts count against manager's daily/period/lifetime caps
- Time delays on cheques add extra security layer

### Managers and Whitelist
- Managers cannot modify the [whitelist](whitelist.md)
- Whitelisted addresses bypass all manager restrictions
- Use whitelist for emergency access, managers for daily operations

### Managers and Rewards
- Managers can claim [rewards](rewards.md) if given permission
- Cannot change reward settings or ambassador codes
- Useful for automated reward compounding strategies

## The Bottom Line

Stop choosing between control and automation. Managers let you have both.

Grant specific permissions. Set unbreakable limits. Revoke instantly. Sleep soundly knowing your portfolio is optimizing 24/7 within boundaries you control.

Whether it's a family member who needs emergency access, an AI that never sleeps, or a professional service with institutional strategies — Managers transform your static wallet into a dynamic financial command center.

The future of DeFi isn't about choosing the right protocol. It's about having the right operators executing the right strategies at the right time. With Managers, that future is here.

---

_For technical implementation details, see the [technical documentation](technical/)._
