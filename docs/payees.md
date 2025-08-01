# Payees: Automated Payment Relationships That Actually Work

**TL;DR:**

- Replace wire transfers with automated crypto payments that earn yield until needed
- Set hard limits per payee: monthly caps for vendors, weekly limits for employees, etc.
- Save thousands in fees while gaining hours back every month

Stop losing $400 monthly because your payroll sits in a checking account earning nothing. Stop paying $50 wire fees. Stop missing payments while traveling. Stop worrying about sending too much by accident.

**Payees** are pre-approved payment recipients with smart contract-enforced limits. Think automatic bill pay, but you keep earning yield until the moment of payment, you can cancel instantly, and you control every parameter.

This is what happens when you redesign payments from first principles. Your money works harder, your operations run smoother, and you sleep better.

## Core Concept: Controlled Payment Relationships

Traditional payments force bad choices: manual processing (time-consuming) or full access (risky). Payees create a better way:

```
Traditional: Give vendor your credit card → They charge whatever, whenever
Underscore: Add vendor as Payee → $5,000/month limit → Only USDC → Auto-expires quarterly
```

### The Yield Advantage

Your payment funds earn yield until needed:

```
Traditional Business Account:
$100,000 payroll fund → 0.01% APY → $10/year

Underscore with Payees:
$100,000 in Aave → 5% APY → $5,000/year
Automatic withdrawal only when payments due
```

**Real impact**: A business with $500k in operating funds earns ~$25,000 annually instead of $50.

## Payment Validation Hierarchy

The system checks payment recipients in strict order:

1. **[Whitelisted Addresses](whitelist.md)** → Instant, no limits
2. **Owner (You)** → Can self-pay if enabled
3. **Active Payees** → All configured limits apply
4. **Others** → Payment blocked

This hierarchy maximizes flexibility while maintaining security.

## Two-Layer Control System

### Global Payee Settings

Wallet-wide defaults affecting all payees:

- Default period length (e.g., 30 days)
- Base transaction and period limits
- `canPayOwner`: Self-payment toggle (default: enabled)
- `canPull`: Master switch for pull payments (default: disabled for security)

### Specific Payee Settings

Individual overrides for each relationship:

- Custom limits tailored to each payee
- Specific period lengths
- Asset restrictions
- Pull payment permissions

The most restrictive setting always wins.

## Financial Controls

### Dual Limit System

Payees support both token amount AND USD value limits:

```
Token Limits:              USD Limits:
├─ Per Tx: 1000 USDC      ├─ Per Tx: $1,000
├─ Per Period: 5000 USDC  ├─ Per Period: $5,000
└─ Lifetime: 50000 USDC   └─ Lifetime: $50,000

Applied: MOST RESTRICTIVE wins
```

**Why both?** Protects against price volatility. Your 10 ETH payment won't accidentally send $40,000 if ETH spikes.

### Period-Based Limits

Limits reset automatically each period:

```
Month 1: Use $7k of $10k → Month 2: Fresh $10k (unused doesn't roll)
```

Common configurations:

- Daily: ~43,200 blocks
- Weekly: ~302,400 blocks
- Monthly: ~1,296,000 blocks
- Quarterly: ~3,888,000 blocks

### Transaction Controls

- **Max Transactions**: Limit payment frequency (e.g., 1/month for salary)
- **Cooldown Period**: Minimum time between payments (prevents double-pays)
- **Fail on Zero Price**: Blocks payments if price oracles fail

## Asset Restrictions

Control exactly what tokens each payee can receive:

| Setting                      | Effect               | Use Case            |
| ---------------------------- | -------------------- | ------------------- |
| Primary Asset + Only Primary | Single token only    | Salary in USDC only |
| Primary Asset + Any          | Preference indicated | Vendor prefers USDT |
| No Restrictions              | Accept anything      | Trading services    |

## System Limits & Safety Features

### Maximum Counts

- **40 payees per wallet**: Need more? Spin up another wallet or remove inactive payees
- **40 assets per payee**: More than enough for any payment relationship
- **25 protocols per manager**: If a manager proposes payees

### Fail on Zero Price Protection

This critical safety feature blocks transactions when asset prices are unavailable:

- **Why it matters**: Prevents unlimited token transfers during oracle failures
- **Keep it enabled**: A broken price feed could otherwise drain your wallet
- **Only disable for**: Pure stablecoin operations where you trust the 1:1 peg

### Pull Payment Safety

**Hard requirement**: You _cannot_ enable pull payments without setting limits. The system enforces at least one cap (transaction or period) to prevent unlimited access.

## Lifecycle Management

### Activation Flow

```
Added → Pending → Active → Expired/Removed
         (delay)   (working)
```

### Typical Activation & Expiry Combinations

| Use Case                 | Activation Delay | Auto-Expiry | Why This Combo                                        |
| ------------------------ | ---------------- | ----------- | ----------------------------------------------------- |
| **New Vendor**           | 7 days           | 90 days     | High security for new relationships; quarterly review |
| **Regular Employee**     | 3 days           | 365 days    | Moderate security; annual contract cycle              |
| **Trusted Family**       | 1 day            | Never       | Quick access for emergencies; permanent relationship  |
| **Subscription Service** | 2 hours          | 30 days     | Fast setup; monthly renewal matches billing           |

### Administrative Hierarchy

**Owner (You)**

- Direct add/update/remove
- Confirm manager proposals
- Full control always

**[Managers](managers.md)**

- Propose new payees only
- Requires owner confirmation
- Cannot modify/remove

**Payees**

- Can remove themselves
- Enables clean exits

**Security (MissionControl)**

- Emergency removal only
- Protocol safety net

> **📋 Manager Proposals Need Your Approval**  
> If a manager proposes a new payee, you'll see a pending request in your dashboard. After the security delay (typically 2-3 hours), you must manually confirm to activate the payee. This two-step process prevents unauthorized additions.

## Pull Payments: The Subscription Revolution

Enable payees to request payment when due, always within your limits.

### How It Works

1. Service requests payment amount
2. Smart contract validates against limits
3. Funds pulled from yield if needed (like [cheques](cheques.md))
4. Payment completes automatically

### Double Activation Required

```
Global: canPull = true  AND  Payee: canPull = true
                ↓
        Pull payments enabled
```

### Real Numbers

Traditional subscriptions:

- $500/month sitting idle = $0 earned

With pull payments:

- $500/month earning 5% = $25/year extra
- $6,000 annual subscriptions = $300/year bonus

**Safety**: Pull payees MUST have limits. No unlimited access allowed.

## Real-World Configurations

### Small Business Payroll

```
Employee: John Smith - Developer
Period: 30 days
Limits: $10k/month, $10k/transaction
Transactions: 2 per month (bi-weekly)
Cooldown: 10 days
Asset: USDC only
Result: Automated payroll, funds earn yield until payday
```

### Vendor Management

```
Vendor: SupplyCo
Period: 7 days
Limits: $2k/tx, $8k/week, $100k lifetime
Cooldown: 1 hour
Asset: Any stablecoin
Result: Flexible payments within boundaries
```

### Family Support

```
Payee: College Daughter
Period: 30 days
Limits: $2k/month split across 2 payments
Asset: USDC only
Activation: 1 day delay
Result: Automated allowance, adjustable anytime
```

### SaaS Subscriptions

```
Service: Analytics Platform
Pull Enabled: Yes
Period: 30 days
Limits: $149/month, 1 transaction
Cooldown: 25 days
Asset: USDC only
Result: Never miss payment, earn yield on float
```

## Common Questions

**What happens at expiry?**
Payees automatically deactivate. Payments blocked until you renew.

**Can payees see my balance?**
No. They can only receive what you've authorized.

**What if I overpay by mistake?**
Impossible. Hard limits prevent sending more than configured.

**Do I need separate payees for each employee?**
Yes. Each payee has individual limits and tracking.

**Can I modify limits after setup?**
Yes. Changes take effect immediately.

## Quick Setup Checklist

For employees:

- ✓ Monthly period (1,296,000 blocks)
- ✓ Salary amount as period cap
- ✓ 1-2 transactions per period
- ✓ 10+ day cooldown
- ✓ USDC only
- ✓ 3-day activation delay

For subscriptions:

- ✓ Enable pull payments (both layers)
- ✓ Monthly period matching billing
- ✓ Exact amount as caps
- ✓ 1 transaction per period
- ✓ 25+ day cooldown
- ✓ Stablecoin only

## The Bottom Line

Every dollar sitting in a business checking account is a dollar not earning yield. Every manual payment is time wasted. Every wire fee is money burned.

Payees fix all three problems simultaneously. Your funds earn until needed. Payments execute automatically within your rules. Minimal gas costs replace expensive wire fees.

For a typical small business: Save $10,000+ annually in fees and lost yield. Reclaim 10 hours monthly from payment processing. Sleep knowing payments can't exceed your limits.

Stop choosing between convenience and control. With Payees, you get both. Plus yield that pays for your Netflix subscription 10 times over.

## Related Features

- **[Managers](managers.md)**: Grant payee management permissions to trusted operators
- **[Cheques](cheques.md)**: One-time payments with time delays and cancellation ability
- **[Whitelist](whitelist.md)**: Unlimited payment access for your most trusted addresses
- **[User Wallet](user-wallet.md)**: Your command center for all payment configurations

---

_For technical implementation details, see the [technical documentation](technical/)._
