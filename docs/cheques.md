# Cheques: The Safety Net Your Crypto Payments Never Had

**TL;DR:**
- Create cancellable payments with built-in time delays for security
- Perfect for large transfers, contractor payments, or any transaction needing an "undo" button
- Funds stay in your wallet earning yield until the cheque is actually cashed

That sinking feeling when you realize you sent $50,000 to the wrong address. The panic when a contractor cashes your payment before delivering. The wire recall that takes three days and might not work.

**Cheques** fix all of this. They're blockchain-native payments you control until the moment they're cashed — like having an "undo" button for your money.

Write a cheque. Set when it unlocks. Cancel if something goes wrong. Sleep soundly knowing large payments get automatic security delays. This is what payment control actually looks like.

## Core Concept: Payment Promises with Power

Traditional crypto forces instant finality. Traditional banking offers recalls but with bureaucracy. Cheques deliver the best of both:

```
Crypto Transfer: Send $5,000 → Gone forever in 12 seconds
Bank Wire: Send $5,000 → Call to cancel → Maybe works in 3 days
Underscore Cheque: Send $5,000 → Cancel anytime before cashed → Instant
```

### How Cheques Work

1. **Write** the cheque (no funds move yet)
2. **Time-lock** period for security review
3. **Active** window when it can be cashed
4. **Settlement** only when explicitly paid

Your funds earn yield the entire time. The recipient sees the commitment. You keep control.

## The Four-Stage Lifecycle

```
Creation → Time-locked → Active → Finalized
    │          │           │         │
    └──────────┴───────────┴─────────┴─→ Cancel anytime until paid
```

### Creation

Specify recipient, amount, timing, and permissions. We record the cheque's USD value when you create it — this snapshot powers limits, reporting, and automatic delays.

### Time-locked

Security delay before the cheque becomes cashable:

- Automatic for amounts over your threshold
- Custom for future-dated payments
- Funds still earning yield in your wallet

### Active

The cheque can now be cashed by:

- You pushing the payment
- Manager executing it (if permitted)
- Recipient pulling it (if enabled)

### Finalized

Either paid (funds transferred) or expired (becomes void).

## Smart Security Features

### Automatic USD Thresholds

Set a delay threshold (e.g., $1,000):

- Below: Cheques can be immediate
- Above: Automatic delay applied

> **Note**: Cheques cannot be created for [whitelisted addresses](whitelist.md). If you trust an address enough to whitelist it, pay them directly with instant, unlimited transfers — Cheques are for everything else.

Example impact:

- $500 payment → No delay needed
- $5,000 payment → 3-day security review
- $50,000 payment → 7-day extended review

### Time Controls

- **Expensive Delay**: How long high-value cheques wait (e.g., 3-7 days)
- **Default Expiry**: How long cheques stay active (e.g., 30 days)
- **Custom Timing**: Override per cheque as needed

Time is measured in blocks (on Base L2: ~2 seconds per block, ~43,200 blocks per day).

## Financial Controls

### Creation Limits

- **Max Active Cheques**: Total unpaid cheques allowed (e.g., 20)
- **Max Cheque Value**: Largest single cheque (e.g., $50,000)
- **Period Caps**: Monthly creation limits (e.g., $100,000)

### Payment Limits

- **Period Payment Cap**: Maximum cashed per period (e.g., $50,000/week)
- **Payment Cooldown**: Time between payments (e.g., 10 minutes)

### Asset Restrictions

Limit cheques to specific tokens:

- Stablecoins only for conservative operations
- Any token for flexible businesses
- Single asset for simplified accounting

## Permission System

### Who Can Create

**Owner**: Always can create any cheque
**Managers**: Only if globally enabled AND individually permitted

### Payment Options

**Push Payment**: You or manager executes
**Pull Payment**: Recipient claims when ready (requires double-flag activation)

### Who Can Cancel

**Owner**: Any cheque, anytime before payment
**Security**: Emergency cancellation rights only

## Real-World Configurations

### Freelance Invoice

```
Amount: $3,000 USDC
Unlock: 3 days (automatic over $1,000 threshold)
Expiry: 30 days
Pull: Enabled
Result: Client shows commitment, freelancer controls timing
```

### Monthly Rent

```
Amount: $2,500 USDC
Created: 25th of month
Unlock: 1st of next month
Pull: Enabled
Result: Landlord gets paid on time, you keep control
```

### High-Value Contract

```
Amount: $50,000 USDC
Unlock: 7 days (expensive delay)
Expiry: 45 days
Review benefit: Time to verify deliverables
Yield earned: ~$48 during delay
```

## Advanced Features

### Manager-Created Cheques

Let AI or team members ([managers](managers.md)) create cheques within your rules:

1. Manager creates cheque from approved invoice
2. Time-lock applies automatically
3. You review during delay period
4. Cancel or let it proceed

### Smart Fund Sourcing

Like [payees](payees.md), cheques pull from yield when needed:

- Check liquid balance first
- Auto-withdraw from Aave/Compound if needed
- Complete payment in one transaction

## Common Questions

**What if I send the wrong amount?**
Cancel the cheque before it's cashed, create a new one.

**Can recipients see pending cheques?**
Yes, full transparency on-chain from creation.

**Do cancelled cheques cost gas?**
Yes, but minimal on Base L2 and far less than recovering a wrong payment.

**Can I modify a cheque?**
No, but you can cancel and recreate with new terms.

**What happens at expiry?**
Cheque becomes void, cannot be cashed anymore.

**Can I write a cheque to a whitelisted address?**
No — use [Whitelist](whitelist.md) for instant payments. Cheques are for non-whitelisted recipients who need payment controls.

## Quick Setup Guide

For personal use:

- Set $1,000 delay threshold
- 3-day expensive delay
- 30-day default expiry
- 10 max active cheques

For business:

- Set $10,000 delay threshold
- 24-hour expensive delay
- 45-day default expiry
- Allow manager creation

For high security:

- Set $500 delay threshold
- 7-day expensive delay
- Disable pull payments
- Single asset only

## The Bottom Line

Every payment mistake costs money, time, and peace of mind. Cheques eliminate all three problems.

Your funds earn yield until needed. Large payments get automatic review periods. Mistakes become fixable instead of fatal. Recipients see commitments while you maintain control.

For businesses: Save thousands in payment errors and days of reconciliation work.
For individuals: Never lose sleep over a large transfer again.

This isn't just a better payment method — it's payment control that matches the stakes of modern crypto. When moving real money, you deserve a real safety net.

## When to Use What

| Use Case | Choose | Why |
|----------|--------|-----|
| One-off, high-value payment needing review window | **Cheque** | Time-lock + cancel up to payout; global period caps |
| Recurring payments to trusted relationships | **[Payee](payees.md)** | Individual caps, pull-payment safety, "Circle of Trust" |
| Emergency or ultra-trusted transfers | **[Whitelist](whitelist.md)** | Instant, no limits or delays |

## Related Features

- **[Payees](payees.md)**: Recurring payments to pre-approved addresses
- **[Managers](managers.md)**: Delegate cheque creation within spending limits
- **[Whitelist](whitelist.md)**: Instant payments without delays for trusted addresses
- **[User Wallet](user-wallet.md)**: Your control center for all payment types

---

_For technical implementation details, see the [technical documentation](technical/)._
