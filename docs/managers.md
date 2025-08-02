---
description: Delegate operations to humans or AI within unbreakable boundaries you control
---

# Managers: Delegated Control for Your [Underscore Wallet](user-wallet.md)

Your yield optimizer found a 15% APY opportunity at 3am. By the time you wake up and manually move funds, it's down to 5%. Another $500 in missed gains because you need sleep.

Or your business runs 24/7 but you don't. Vendors need payment at midnight. Opportunities appear on weekends. Your AI trading strategy spots perfect setups while you're in meetings. Every hour of manual control costs real money.

**Managers** let trusted operators — human or AI — work within your exact limits. Your CFO pays invoices up to $10k. Your yield optimizer moves funds between protocols. Your trading bot executes strategies. All within boundaries you set, revocable with one click.

Finally, delegation that doesn't mean giving up control.

## Why Managers Exist

### The Problem with Manual Wallet Management

Running a [wallet](user-wallet.md) solo creates impossible tradeoffs:

- **24/7 Opportunities**: DeFi never sleeps, but you need to
- **Routine Tasks**: Paying vendors, [claiming rewards](rewards.md), rebalancing — repetitive time drains
- **Specialized Knowledge**: Complex strategies require expertise you might not have
- **Emergency Access**: If something happens to you, your funds are locked

Traditional solutions all fail:
- **Shared keys**: One compromised key loses everything
- **Multi-sig**: Slow, requires coordination for every transaction
- **Custody services**: You lose control and pay high fees

### The Manager Solution

Managers enable programmable delegation with precise controls:

- **Limited Permissions**: Grant only specific actions (lend, swap tokens, pay [Payees](payees.md), etc.)
- **Spending Limits**: Hard caps on transaction and period amounts
- **Asset Restrictions**: Limit which tokens managers can touch
- **Instant Revocation**: Remove access with one transaction
- **Time Delays**: Optional cooling periods for sensitive actions

### Your Manager Options

**People You Trust** = Handle specific tasks without full access

- Your spouse can pay bills but can't trade your ETH
- Your business partner can pay vendors but can't touch reserves
- Your accountant can [claim rewards](rewards.md) and rebalance but can't withdraw
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

### Two-Phase Security Checks

Every manager action undergoes automatic validation:

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

Both phases execute atomically within the transaction — if any check fails, the entire action reverts.

## Permissions: What Managers Can Do

Permissions are granular capabilities you grant to managers. You can mix and match these permissions to create the exact operator profile needed — from a CFO who only pays vendors to an AI that manages your entire DeFi strategy. Each permission is independent and can be combined with others.

### Transfer & Payment Operations

| Permission            | Capability                                           | Example Use Case        |
| --------------------- | ---------------------------------------------------- | ----------------------- |
| **General Transfers** | Send assets to [Payees](payees.md), [Whitelist](whitelist.md), or via [Cheques](cheques.md)    | Pay monthly expenses    |
| **Create [Cheques](cheques.md)**    | Schedule one-time payments       | Delayed vendor payments |
| **Propose [Payees](payees.md)**    | Add recurring payment recipients | Onboard new contractors |

### DeFi Operations

| Permission           | Capability                            | Example Use Case                     |
| -------------------- | ------------------------------------- | ------------------------------------ |
| **Buy & Sell**       | Swap tokens, rebalance portfolios     | Maintain 60/40 ETH/USDC ratio        |
| **Manage Yield**     | Deposit/withdraw from yield protocols | Rebalance Morpho/Aave positions      |
| **Manage Debt**      | Handle loans and collateral           | Keep 150% collateralization          |
| **Manage Liquidity** | Provide/remove DEX liquidity          | Optimize Uniswap V3 ranges           |
| **Claim Rewards**    | Harvest protocol incentives           | Collect and reinvest [farming rewards](rewards.md) |

### Administrative Operations

| Permission                 | Capability                    | Example Use Case            |
| -------------------------- | ----------------------------- | --------------------------- |
| **Whitelist Management**   | Add/remove approved addresses | Maintain vendor list        |
| **Claim Protocol Rewards** | Harvest Underscore incentives | Auto-claim [platform rewards](rewards.md) |
| **Claim Loot**             | Collect revenue share         | Maximize [protocol earnings](rewards.md)  |

> **📝 Time Units in Underscore**  
> All time-based settings (delays, cooldowns, periods) are stored in blocks, not wall-clock time. On Base L2 with 2-second blocks:
>
> - 1 hour (1,800 blocks)
> - 1 day (43,200 blocks)
> - 1 week (302,400 blocks)
>
> Examples in this guide assume Base's 2-second block time.

## Controls: Security Boundaries

While permissions define what actions managers can take, controls set the boundaries within which they operate. These limits ensure that even trusted managers can't exceed your risk tolerance or drain your wallet through mistakes or malicious behavior. Every manager action must pass through these security checkpoints.

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
- Configurable delay period set by you (e.g., 1 hour, 1 day, 1 week)
- Time to verify additions and cancel if suspicious
- Protects against rushed or malicious manager additions

**Activation Length**

- Set Manager expiration periods
- Auto-revoke after: 30 days (trial), 90 days (quarterly), 365 days (annual)
- No action needed — permissions end automatically

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

## Real-World Examples

### Yield Optimization

**Setup**: $100k in stablecoins with YieldMaxAI Agent

**Permissions**:
- Assets: Stablecoins only (USDC, USDT, DAI)
- Protocols: Aave, Morpho, Euler only
- Limits: $20k per transaction, 6-hour cooldown

**Results**:
- Captured 5.2% Morpho rate at 3am
- Moved to 6.1% Euler promotional rate
- Auto-claimed $312 in missed [rewards/incentives](rewards.md)
- Additional yield: $3,000 annually

### Business Operations

**Setup**: Global crypto company with 30+ contractors and vendors, CFO as manager

**Permissions**:
- Recipients: Pre-approved contractor and vendor addresses only
- Limits: $2,500 per payment, $25,000 weekly
- Cooldown: 1 hour between payments
- Assets: USDC only

**Results**:
- CFO handles vendor payments independently
- Eliminated $1,750/month in wire fees
- Owner freed from payment operations
- Investment funds remain untouchable

### Family Office Trading

**Setup**: 5 professional traders as individual managers

**Permissions per trader**:
- Assets: ETH, BTC, stablecoins
- Protocols: Major DEXes only
- Limits: $100k per trade, $500k daily cap per trader
- Duration: Quarterly contracts, 3-day activation delay

**Results**:
- Risk distributed across multiple traders
- No single trader can exceed loss limits
- Each trader's P&L tracked separately
- Underperformers removed at quarter end

### Debt Management AI

**Setup**: Ripe Protocol Debt Manager AI Agent

**Permissions**:
- Manage Debt: Repay loans, add collateral
- Manage Yield: Withdraw from Aave/Morpho for repayments
- Limits: $50k per transaction, $200k daily

**Results**:
- Maintains 150% collateralization ratio 24/7
- Auto-withdraws yield to repay when needed
- Added $15k collateral during market volatility
- Prevented liquidation during 20% market drop

### Teen Trading Education

**Setup**: 16-year-old son learning DeFi with monthly allowance

**Permissions**:
- Buy & Sell: Can swap between major tokens
- Manage Yield: Can deposit to Aave/Morpho/Euler only
- Assets: Limited to ETH, USDC, and top 10 tokens
- Limits: $100 per transaction, $500 monthly cap
- Cooldown: 30 minutes between trades
- Duration: 6-month trial period

**Results**:
- Son learns DeFi with real money, real stakes
- Losses capped at affordable education cost
- Can't access family's main holdings
- Built experience before accessing own wallet at 18

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

## Common Questions

**Can managers add other managers?**
No. Only the wallet owner can add new managers. This prevents permission escalation attacks.

**What happens when a manager expires?**
They automatically lose all permissions. No action needed from you.

**Can I change limits without removing the manager?**
Yes. You can modify permissions, limits, and allowed assets/protocols anytime.

**Do unused period limits roll over?**
No. Each period starts fresh with the full limit. Use it or lose it.

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

## The Future of Wallet Operations

Remember that 15% APY opportunity you missed at 3am? The vendor payments that disrupted your weekend? The specialized strategies locked behind $10M minimums?

Those problems end with Managers.

Your yield optimizer now captures overnight opportunities within your risk limits. Your CFO handles invoices without touching your reserves. Your AI trading agent executes institutional strategies on your behalf. All operating within unbreakable boundaries you control.

This is what wallet management should have been from the start. Not choosing between security and opportunity. Not missing gains because you need sleep. Not paying premiums for strategies that should be accessible to everyone.

Stop letting your wallet run on manual mode. The right operators, with the right permissions, executing the right strategies — that's how winning portfolios are built in DeFi.


_For technical implementation details, see the [technical documentation](technical/)._
