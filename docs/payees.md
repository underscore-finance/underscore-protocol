# Payees: Your Circle of Trust for Automated Payments

**TL;DR:**

- Build your personal "Circle of Trust" — a safe list of verified payment addresses
- Set individual limits for each recipient: monthly caps for vendors, weekly for employees
- Your funds earn yield until payment while saving thousands in wire fees

Tired of triple-checking crypto addresses? Losing sleep over that large payment you just sent? Watching your payroll earn nothing in a checking account?

**Payees** transform scary crypto payments into confident, automated transactions. Like saving contacts in your phone, you verify an address once and pay with peace of mind forever. Add your employees, vendors, and regular recipients to your Circle of Trust. Set their individual limits. Then relax knowing every payment is protected from typos, overspending, and mistakes.

This is payment security that actually makes sense — your trusted addresses, your rules, your peace of mind.

## Your Circle of Trust: Safe, Smart, Automated

Think of Payees as your wallet's trusted contacts list. Just like you save phone numbers to avoid misdialing, you save payment addresses to avoid costly mistakes:

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

This yield is generated through established DeFi lending protocols like Aave, Morpho, Euler, where your funds are supplied to liquidity pools and earn a share of the interest paid by borrowers — all while maintaining instant access for payments.

**Real impact**: A business with $500k in operating funds earns ~$25,000 annually instead of $50.

## Payment Validation Hierarchy

The system checks payment recipients in strict order:

1. **[Whitelisted Addresses](whitelist.md)** → Instant, no limits
2. **Owner (You)** → Can self-pay if enabled
3. **Active Payees** → All configured limits apply
4. **Others** → Payment blocked

This hierarchy maximizes flexibility while maintaining security.

## Why Your Circle of Trust is Unbreakable

### Only You Hold the Keys

**Absolute Owner Control**: Only you, as the wallet owner, can add or remove addresses from your Circle of Trust. Not your accountant. Not your manager. Not even your AI assistant. This fundamental rule is enforced by the blockchain itself — it's not a policy that can be bent, it's code that cannot be broken.

### Tamper-Proof by Design

**Immutable Records**: Once you add someone to your Circle of Trust, that record is written to the blockchain permanently. No hacker can secretly change "Alice's Wallet" to point to their own address. The address you saved is the address that stays.

### Managers Can Only Pay Your Trusted Circle

**The Ultimate Safety Net**: When you grant a manager permission to make payments, they can ONLY send funds to addresses already in your Circle of Trust. They cannot add new payees. They cannot modify existing ones. They cannot "accidentally" send your entire treasury to an unknown address. Every payment must go to someone you've already verified and approved.

This isn't just security theater — it's security architecture. Your Circle of Trust creates an impenetrable boundary around your funds.

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

Common configurations (on Base L2):

- Daily: ~24 hours (43,200 blocks)
- Weekly: ~7 days (302,400 blocks)
- Monthly: ~30 days (1,296,000 blocks)
- Quarterly: ~90 days (3,888,000 blocks)

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

- **40 Payees per wallet**: Need more? Spin up another wallet or remove inactive Payees
- **40 assets per payee**: More than enough for any payment relationship
- **25 protocols per manager**: If a manager proposes Payees

### Fail on Zero Price Protection

This critical safety feature blocks transactions when asset prices are unavailable:

- **Why it matters**: Prevents unlimited token transfers during oracle failures
- **Keep it enabled**: A broken price feed could otherwise drain your wallet
- **Only disable for**: Pure stablecoin operations where you trust the 1:1 peg

Price oracles are essential services that provide real-world asset prices to the blockchain. By blocking payments when this price data is unavailable, the system prevents potential exploits that could otherwise drain funds during an oracle malfunction.

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

**[Managers](managers.md)** — Your Trusted Operators

- Can make payments to anyone in your Circle of Trust
- Can suggest new Payees (requires your approval)
- Cannot modify your Circle of Trust directly
- Perfect for delegating routine payments while maintaining control

**Payees**

- Can remove themselves
- Enables clean exits

**Security (MissionControl)**

- Emergency removal only
- Protocol safety net

> **📋 Manager Proposals Need Your Approval**  
> If a manager proposes a new payee, you'll see a pending request in your dashboard. After the security delay (typically 2-3 hours), you must manually confirm to activate the payee. This two-step process prevents unauthorized additions.

## Pull Payments: The Subscription Revolution

Enable Payees to request payment when due, always within your limits.

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

**Safety**: Pull Payees MUST have limits. No unlimited access allowed.

## Real-World Configurations

### Transform Your Payroll

**Before**: Logging into your bank, paying $35 wire fees, losing 3 days of yield
**After**: John gets paid automatically on the 1st and 15th, your funds earn until payment

```
Payee: John Smith - Developer
Your Benefit: Save $70/month in wire fees + earn yield
Protection: Can only receive his set salary amount
Convenience: Payments happen while you sleep
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

**Can Payees see my balance?**
No. They can only receive what you've authorized.

**What if I overpay by mistake?**
Impossible. Hard limits prevent sending more than configured.

**Do I need separate Payees for each employee?**
Yes. Each payee has individual limits and tracking.

**Can I modify limits after setup?**
Yes. Changes take effect immediately.

## Quick Setup Checklist

For employees:

- ✓ Monthly period (~30 days)
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

## The Perfect Partnership: Managers + Payees

**Your Circle of Trust** (Payees) defines WHO can receive payments.
**Your Operators** ([Managers](managers.md)) handle the routine work of making those payments.

Together, they create unbreakable security:

- You verify payment addresses once (adding them as Payees)
- Your manager handles daily operations (paying only those Payees)
- You maintain ultimate control (only you can modify the Circle of Trust)

This separation of powers means you can delegate work without delegating trust. Your CFO can pay all your vendors without being able to add their cousin as a new "vendor." Your AI can optimize payments without being able to drain your wallet to an unknown address.

**Learn more**: See how [Managers](managers.md) can automate your payment workflows.

## Related Features

- **[Managers](managers.md)**: Grant payee management permissions to trusted operators
- **[Cheques](cheques.md)**: One-time payments with time delays and cancellation ability
- **[Whitelist](whitelist.md)**: Unlimited payment access for your most trusted addresses
- **[User Wallet](user-wallet.md)**: Your command center for all payment configurations

---

_For technical implementation details, see the [technical documentation](technical/)._
