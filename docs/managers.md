# Managers: The Autonomous Operators of Your Underscore Wallet

**TL;DR:**
- Let AI or trusted people operate your wallet within strict limits you control
- Automate yield optimization and DeFi strategies that work 24/7
- Set up once, revoke instantly, sleep soundly knowing your rules are enforced by code

You've been doing DeFi wrong. Manually claiming rewards at 3am. Missing arbitrage opportunities while you sleep. Watching yields evaporate because you couldn't rebalance fast enough.

Enter **Managers** — the game-changing delegation system that lets your wallet work as hard as you do. Grant specific permissions to trusted operators, AI agents, or professional services. Set unbreakable spending limits enforced by smart contracts. Revoke access instantly if anything seems off.

This isn't your grandfather's power of attorney. This is programmable, revocable, limited delegation that puts you in complete control while enabling 24/7 optimization.

## What Managers Do For You

**💰 Make Money While You Sleep**

- AI managers optimize yields 24/7 across multiple protocols
- Capture arbitrage opportunities in milliseconds
- Auto-compound rewards you'd otherwise miss
- Average users gain 2-5% extra APY

**⏰ Save Time on Routine Tasks**

- Automate weekly DCA purchases at optimal prices
- Let your CFO handle vendor payments independently
- Auto-rebalance portfolios to maintain target allocations
- Reclaim 10+ hours monthly from manual operations

**🔒 Stay Secure with Granular Control**

- Set exact spending limits enforced by smart contracts
- Restrict managers to specific tokens and protocols
- Revoke access instantly if anything seems wrong
- Time delays prevent rushed or malicious actions

**🎯 Access Professional Strategies**

- Use institutional-grade trading algorithms
- Benefit from strategies requiring 24/7 monitoring
- Pay performance fees only on profits
- No minimum investment requirements

## Stop Choosing Between Control and Growth

Every crypto holder faces the same dilemma:

- **Keep full control** = Miss opportunities, waste time on manual tasks
- **Share your keys** = Risk losing everything

Managers eliminate this impossible choice:

**Old Way**: Give your accountant your seed phrase and pray
**Manager Way**: Give your accountant permission to pay invoices up to $5k/month. Nothing more.

**Old Way**: Stay up until 3am to catch the best yield rates
**Manager Way**: Your AI manager rebalances automatically within your set limits

**Old Way**: Your spouse can't help if something happens to you
**Manager Way**: Your spouse has emergency access that activates only when needed

### Your Manager Options

**People You Trust** = Handle specific tasks without full access

- Your spouse can pay bills but can't trade your ETH
- Your business partner can handle vendors but can't touch reserves
- Your accountant can view transactions but can't move funds
- Your trader friend can swap tokens but only up to set limits

**AI That Never Sleeps** = Capture opportunities 24/7

- Yield optimizers that move funds to the best rates automatically
- Rebalancing bots that maintain your 60/40 portfolio split
- DCA bots that buy $100 of ETH every Monday at optimal prices
- Arbitrage bots that profit from price differences while you sleep

**Professional Services** = Institutional strategies for everyone

- Get hedge fund returns without the $10M minimum
- Access quant strategies previously exclusive to banks
- Let proven traders work within your risk limits
- Benefit from AI models trained on billions in trades

### Your Protection Never Sleeps

Every manager action faces a gauntlet of automatic checks:

**Before Any Action**:
✓ Is this manager still active?
✓ Can they perform this specific action?
✓ Can they touch this particular asset?
✓ Are they using an approved protocol?
✓ Has enough time passed since their last action?

**After The Action**:
✓ Did they stay under their per-transaction limit?
✓ Are they still within their daily/weekly/monthly budget?
✓ Have they exceeded their total lifetime allowance?

If any check fails, the transaction stops cold. No exceptions, no overrides, no "just this once." Your rules are enforced by code, not promises.

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

### Transfer & Payment Operations

| Permission            | Capability                       | Example Use Case        |
| --------------------- | -------------------------------- | ----------------------- |
| **General Transfers** | Send assets to any address       | Pay monthly expenses    |
| **Create Cheques**    | Schedule one-time payments       | Delayed vendor payments |
| **Propose Payees**    | Add recurring payment recipients | Onboard new contractors |

### DeFi Operations

| Permission           | Capability                            | Example Use Case                     |
| -------------------- | ------------------------------------- | ------------------------------------ |
| **Buy & Sell**       | Swap tokens, rebalance portfolios     | Maintain 60/40 ETH/USDC ratio        |
| **Manage Yield**     | Deposit/withdraw from yield protocols | Auto-compound Aave positions daily   |
| **Manage Debt**      | Handle loans and collateral           | Keep 150% collateralization          |
| **Manage Liquidity** | Provide/remove DEX liquidity          | Optimize Uniswap V3 ranges           |
| **Claim Rewards**    | Harvest protocol incentives           | Collect and reinvest farming rewards |

### Administrative Operations

| Permission                 | Capability                    | Example Use Case            |
| -------------------------- | ----------------------------- | --------------------------- |
| **Whitelist Management**   | Add/remove approved addresses | Maintain vendor list        |
| **Claim Protocol Rewards** | Harvest Underscore incentives | Auto-claim platform rewards |
| **Claim Loot**             | Collect revenue share         | Maximize protocol earnings  |

> **📝 Time Units in Underscore**  
> All time-based settings (delays, cooldowns, periods) are stored in blocks, not wall-clock time. On Base L2 with 2-second blocks:
>
> - 1 hour (1,800 blocks)
> - 1 day (43,200 blocks)
> - 1 week (302,400 blocks)
>
> Examples in this guide assume Base's 2-second block time.

## Controls: Security Boundaries

### Financial Limits

**Per-Transaction Limits**

- Maximum USD value for any single transaction
- Example: $5,000 cap prevents large one-time losses

**Period-Based Limits**

- Total USD value allowed within recurring time windows
- Period length set via `managerPeriod` in global settings (e.g., 1 day = 43,200 blocks)
- Periods reset automatically when the current period ends
- Example: $10,000 per day for trading operations

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
- Measured in blocks (e.g., 1 hour = 1,800 blocks on Base)
- Prevents rapid-fire mistakes or attacks

**Asset Restrictions**

- Limit Manager to specific tokens (e.g., only stablecoins)
- Granular control over what can be touched
- Maximum 40 different assets per manager

**Protocol Restrictions (Legos)**

- Restrict to specific DeFi protocols by ID
- Each protocol (["Lego"](user-wallet.md#the-lego-system) = standardized integration, e.g., Aave, Curve) registered in LegoBook
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
- Configurable up to your wallet's maximum (about 2 hours 48 minutes = 5,000 blocks on Base)
- Time to verify additions and cancel if suspicious
- Protects against rushed or malicious manager additions

**Activation Length**

- Set Manager expiration periods
- Auto-revoke after: 30 days (trial), 90 days (quarterly), 365 days (annual)
- No action needed — permissions end automatically

## How to Set Up Your First Manager

### The Journey from Zero to Automated

**1. Choose Your Manager Period**  
Decide how often spending limits reset — daily, weekly, or monthly. This becomes your default for all managers through global settings. Think of it like a credit card billing cycle.

**2. Add Your Manager**  
Provide their address and two key timeframes:

- **Security Delay**: How long to wait before they’re active (up to your wallet's maximum, typically 2-3 hours)
- **Active Period**: How long they can operate (30 days for trials, 90+ days for trusted services)

**3. Set Permissions and Limits**  
Pick what they can do from the permissions menu:

- Which actions (trade, yield, transfer, etc.)
- Which assets they can touch
- Which protocols they can use
- Maximum amounts per transaction, per period, and lifetime

**4. Monitor Performance**  
Check anytime to see:

- How much they’ve spent vs. their limits
- Transaction history and patterns
- Days remaining in their active period

Your wallet provides detailed manager statistics through the dashboard or by querying current usage data.

**5. Adjust or Remove**  
Based on performance:

- Extend their active period if they’re doing well
- Increase limits for proven performers
- Remove instantly if anything seems wrong

### What to Expect

**During Setup**: Small gas fee to configure (similar to approving a token)

**While Active**: Each manager transaction costs normal DeFi gas — no extra overhead

**For Monitoring**: Checking balances and history is free

**If Problems Arise**: Removal is instant and costs minimal gas

## Real People, Real Results

### Sarah's Passive Income Machine

**The Situation**: Sarah holds $100k in stablecoins but barely earns 2% because she can't monitor rates 24/7.

**The Solution**: She added YieldMaxAI as a manager with these limits:

- Can only touch her stablecoins (USDC, USDT, DAI)
- Can only use trusted protocols (Aave, Compound)
- Maximum $20k per transaction
- Must wait 6 hours between moves

**The Result**: Her AI manager:

- Moved funds to Compound when rates hit 5.2% at 3am
- Shifted to Aave during a 6.1% promotional period
- Auto-claimed $312 in rewards she would have missed
- **Generated an extra $3,000 annually** with zero effort

### David's Distributed Company

**The Situation**: David runs a DAO with 50 contributors. He was drowning in payment requests and wire transfers cost $35 each.

**The Solution**: He made his CFO a manager with strict boundaries:

- Can only send USDC to pre-approved vendor addresses
- Maximum $2,500 per payment
- Maximum $25,000 per week total
- 1 hour cooldown between payments

**The Result**:

- CFO handles all routine payments independently
- **Saved $1,750/month** in wire fees
- **Freed up 10 hours/week** of David's time
- Zero access to investment funds or treasury reserves

### Maria's Safety Net

**The Situation**: Maria travels frequently and worries about her family accessing funds if something happens.

**The Solution**: She made her brother an emergency manager:

- Can only transfer USDC
- Lifetime limit of $10,000
- No cooldown (for true emergencies)
- Activates after just 1 hour

**The Result**:

- Brother can help in genuine emergencies
- Can't touch her ETH or other investments
- **Peace of mind** without compromising security
- Already helped once when Maria lost her phone abroad

### Alex's Institutional Edge

**The Situation**: Alex wanted access to sophisticated trading strategies but didn't have $10M for a hedge fund minimum.

**The Solution**: He connected TradingDeskPro as a manager:

- Can trade ETH, BTC, and stablecoins
- Can use major DEXes (Uniswap, Curve)
- Maximum $50k per trade
- 10-minute cooldown between trades
- Annual contract with 3-day security delay

**The Result**:

- Access to arbitrage strategies previously exclusive to institutions
- **Earned 18% last quarter** through automated trading
- Pays only 20% performance fee vs 2-and-20 hedge fund structure
- Can revoke access instantly if strategies underperform

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

> **💸 Fee Considerations**  
> Manager transactions still incur:
>
> - Normal gas fees (paid by transaction sender - you or the service)
> - Protocol fees on swaps/yields (0.1-0.5%)
> - These fees contribute to your rewards
>
> Professional services may cover gas costs as part of their offering.

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
