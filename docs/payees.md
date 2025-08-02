---
description: Automated recurring payments to verified addresses while your funds earn yield
---

# Payees: Your Circle of Trust for Automated Payments

Your business checking account holds $500,000. At 0.01% APY, that's $50 a year. Meanwhile, you're paying $35 per wire transfer, 20 times a month. That's $8,400 annually — gone.

Now imagine those same funds earning 5% in DeFi ($25,000/year) while automatically paying your team on schedule. No wires. No manual transfers. No watching the clock on payday. Just verified addresses with preset limits, executing payments while your money keeps working.

**Payees** are your [wallet's](user-wallet.md) trusted contacts — verified once, paid forever. Like speed dial for payments, but with built-in spending limits and automatic execution. Add an employee with a $10,000 monthly cap. A vendor with $50,000 quarterly. Your office rent at exactly $8,500 on the first.

Stop choosing between yield and liquidity. Your money can do both.

## Why Payees Exist

### The Problem with Recurring Crypto Payments

Making regular crypto payments today means choosing between bad options:

- **Manual transfers**: Re-enter addresses, risk typos, waste time every pay period
- **Give full access**: Share private keys or grant unlimited spending permissions
- **Traditional banking**: Pay wire fees, lose DeFi yield, wait for processing

None of these work for businesses or individuals who need reliable, controlled automation.

### The Payee Solution

Payees create a verified recipient list with granular controls:

```
Traditional: Give vendor your credit card → They charge whatever, whenever
Underscore: Add vendor as Payee → $5,000/month limit → Only USDC → Auto-expires quarterly
```

Your funds stay in DeFi earning yield (via protocols like Aave, Morpho, Euler) until the moment of payment. The system automatically withdraws only what's needed, when it's needed. Plus, you earn [rewards](rewards.md) on all your DeFi activity.

**Example Impact**:

- $500k operating funds at 5% APY = $25,000/year earned
- Traditional bank at 0.01% APY = $50/year earned
- Difference: $24,950 additional revenue annually
- Plus: [Protocol rewards](rewards.md) on top of yield

## Payment Validation Hierarchy

The system checks payment recipients in strict order:

1. **[Whitelisted Addresses](whitelist.md)** → Instant, no limits
2. **Owner (You)** → Can self-pay if enabled
3. **Active Payees** → All configured limits apply
4. **Others** → Payment blocked

This hierarchy maximizes flexibility while maintaining security.

## Why Your Circle of Trust is Unbreakable

### Only You Hold the Keys

**Absolute Owner Control**: Only you, as the [wallet owner](user-wallet.md), can add or remove addresses from your Circle of Trust. Not your accountant. Not your manager. Not even your AI assistant. This fundamental rule is enforced by the blockchain itself — it's not a policy that can be bent, it's code that cannot be broken.

### Tamper-Proof by Design

**Immutable Records**: Once you add someone to your Circle of Trust, that record is written to the blockchain permanently. No hacker can secretly change "Alice's Wallet" to point to their own address. The address you saved is the address that stays.

### Managers Can Only Pay Your Trusted Circle

**The Ultimate Safety Net**: When you grant a manager permission to make payments, they can ONLY send funds to addresses already in your Circle of Trust. They cannot add new payees. They cannot modify existing ones. They cannot "accidentally" send your entire treasury to an unknown address. Every payment must go to someone you've already verified and approved.

This isn't just security theater — it's security architecture. Your Circle of Trust creates an impenetrable boundary around your funds.

## Payee Controls & Configuration

You can set comprehensive controls for each payee, ensuring payments happen exactly as intended. These controls protect against overspending, timing errors, and unauthorized changes.

### Financial Limits

#### Dual Protection System

Every payee supports both token amount AND USD value limits:

- **Transaction Limits**: Maximum per single payment (e.g., 1,000 USDC or $1,000)
- **Period Limits**: Maximum per time period (e.g., 5,000 USDC or $5,000/month)
- **Lifetime Limits**: Total cumulative maximum (e.g., 50,000 USDC or $50,000)

The most restrictive limit always applies, protecting against price volatility.

#### Period Configuration

- **Custom Periods**: Set any duration in blocks (e.g., 43,200 blocks ≈ 1 day on Base)
- **Auto-Reset**: Limits refresh each period (unused amounts don't roll over)
- **Common Settings**: Daily, weekly, bi-weekly, monthly, quarterly

### Payment Controls

#### Transaction Restrictions

- **Max Transactions**: Limit payment count per period (e.g., 1 for monthly salary)
- **Cooldown Period**: Minimum time between payments (prevents accidental double-pays)
- **Expiry Date**: Auto-deactivate payees after set time (e.g., contractor end date)

#### Asset Restrictions

Control exactly which tokens each payee can receive:

- **Single Asset**: Lock to one token only (e.g., USDC for salaries)
- **Preferred Asset**: Set default with flexibility for others
- **Any Asset**: Accept all tokens (useful for trading desks)

### Security Features

#### Global Settings (Wallet-Wide)

- **Pull Payment Master Switch**: Enable/disable all pull payments
- **Self-Payment Toggle**: Allow/block payments to yourself
- **Default Limits**: Base settings inherited by new payees

#### Individual Overrides

- **Custom Limits**: Override globals for specific relationships
- **Pull Permission**: Enable per-payee even if globally disabled
- **Asset Whitelist**: Restrict tokens beyond global settings

### System Limits

- **Maximum 40 Payees**: Per wallet capacity
- **Maximum 40 Assets**: Per payee restriction list
- **Fail-Safe Protection**: Blocks payments if price oracles unavailable
- **Keep it enabled**: A broken price feed could otherwise drain your wallet
- **Only disable for**: Pure stablecoin operations where you trust the 1:1 peg

Price oracles are essential services that provide real-world asset prices to the blockchain. By blocking payments when this price data is unavailable, the system prevents potential exploits that could otherwise drain funds during an oracle malfunction.

### Pull Payment Safety

**Hard requirement**: You _cannot_ enable pull payments without setting limits. The system enforces at least one cap (transaction or period) to prevent unlimited access.

## Permission System

### Who Can Add Payees

**Owner**: Full control to add, modify, or remove any payee
**Managers**: Can propose new payees (requires owner approval after delay)
**Others**: No access to modify Circle of Trust

### Who Can Execute Payments

**Owner**: Can pay any active payee within limits
**Managers**: Same payment rights as owner (to active payees only)
**Payees**: Can pull payments if explicitly enabled

### Who Can Remove

**Owner**: Can remove any payee immediately
**Payees**: Can remove themselves (clean exit option)
**Managers**: Cannot remove payees directly

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

> **📋 Manager Proposals Need Your Approval**  
> If a manager proposes a new payee, you'll see a pending request. After the security delay (configurable by you), you must manually confirm to activate the payee. This two-step process prevents unauthorized additions.

## Pull Payments: The Subscription Revolution

Enable Payees to pull payment directly from your wallet, always within your preset limits.

### How It Works

1. Payee initiates withdrawal from your wallet
2. Smart contract validates against all configured limits
3. Funds automatically sourced from yield positions if needed
4. Payment executes immediately if within limits

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

### Employee Payroll Configuration

```
Payee: John Smith - Developer
Limits: $5,000 bi-weekly, USDC only
Schedule: 1st and 15th of each month
Result: Automatic payment from yield-earning funds
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

**What if I overpay by mistake?**
Impossible. Hard limits enforced by smart contracts on the blockchain prevent sending more than configured.

**Do I need separate Payees for each employee?**
Yes. Each payee has individual limits and tracking.

**Can I modify limits after setup?**
Yes. Changes take effect immediately.

## Payees vs Cheques: Which Payment Tool is Right for You?

Understanding when to use Payees versus Cheques ensures you're using the most efficient tool for each situation:

| Feature                 | **Payees**                                                                                              | **[Cheques](cheques.md)**                                                                                                                      |
| ----------------------- | ------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| **Primary Use Case**    | Automated, recurring payments for ongoing relationships                                                 | Flexible, one-time payments that you control until cashed                                                                                      |
| **Payment Frequency**   | Scheduled intervals (weekly, monthly, etc.)                                                             | Single, non-repeating transaction                                                                                                              |
| **Recipient Setup**     | Must add recipient to your "Circle of Trust" first                                                      | No setup needed — send to any address                                                                                                          |
| **Key Benefit**         | Convenience & Automation: Set once, runs automatically                                                  | Control & Flexibility: Create now, cancel anytime before cashed                                                                                |
| **Ideal For**           | • Employee salaries • Rent or subscriptions • Regular vendor payments • Allowances or stipends | • Paying contractors after work approval • Settling one-time invoices • Sending gifts or prizes • Large transfers needing review time |
| **Management**          | Set up once, modify schedule as needed                                                                  | Each cheque managed individually                                                                                                               |
| **How Payment Happens** | Can be executed by owner/manager or pulled by recipient (if enabled)                                    | Can be cashed by owner/manager or pulled by recipient (if enabled)                                                                             |
| **Cancellation**        | Pause or stop entire payment schedule                                                                   | Cancel specific cheque anytime before cashed                                                                                                   |

## The Future of Business Payments

Remember that $500,000 sitting in your checking account earning $50 a year? That's not banking — that's charity to your bank.

With Payees, those same funds earn $25,000 annually. Your team gets paid automatically on schedule. No more Friday afternoon wire transfers. No more $35 fees adding up to thousands. No more manual entry errors sending money to the wrong place.

This is what business banking should have been from the start. Not choosing between yield and liquidity. Not trusting vendors with unlimited access. Not wasting hours on repetitive transfers.

Just verified addresses. Preset limits. Automatic execution. And money that works as hard as you do.

Welcome to payments that finally make sense.

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

- **[Cheques](cheques.md)**: One-time payments with time delays and cancellation ability
- **[Managers](managers.md)**: Learn how to delegate payment tasks to AI or team members
- **[Whitelist](whitelist.md)**: Configure instant, unlimited transfers for your most trusted addresses
- **[User Wallet](user-wallet.md)**: Explore your complete financial command center and all its features

---

_For technical implementation details, see the [technical documentation](technical/)._
