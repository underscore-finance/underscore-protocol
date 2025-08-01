# Digital Cheques: Send Money with Total Control

**TL;DR:**
- Write a payment now, let them cash it later — just like a real cheque
- Cancel anytime before it's cashed if plans change
- Built-in security delays for large amounts protect you from mistakes
- Your funds keep earning yield until the moment of payment

Remember writing a physical cheque? You fill in the amount, sign it, hand it over — but the money doesn't leave your account until they actually cash it. And if something goes wrong, you can call your bank to stop payment.

**Digital Cheques** bring this familiar control to crypto. Write a blockchain cheque that your recipient can cash when they're ready. Changed your mind? Cancel it with one click. Made a mistake? You have time to fix it. This is the safety net crypto payments have been missing.

## Why Use a Digital Cheque?

- **Total Control**: Changed your mind? Cancel a cheque anytime before it's cashed, giving you complete peace of mind
- **Unmatched Security**: Our secure process protects you from common attacks, ensuring your money only goes where you intend
- **Ultimate Flexibility**: Pay anyone, anytime. Create a cheque now to be cashed by the recipient when they're ready
- **Cost-Effective**: Designed to be efficient, keeping your network fees as low as possible
- **Earning While Waiting**: Your funds stay invested and earning yield until the cheque is actually cashed

## How Digital Cheques Work

Just like a physical cheque, the process is simple and familiar:

```
   You Write & Sign         Recipient Holds         One of Two Outcomes
        📝                      💳                      ✅ or ❌
         │                       │                         │
         ├──────────────────────►├────────────────────────┤
         │                       │                         │
    Create cheque           Pending State            Cashed (funds sent)
    (no funds moved)     (you can still cancel)        OR
                                                    Cancelled (you stopped it)
```

### The Power of the Pending State

While your cheque is pending:
- **Your funds stay in your wallet** earning yield
- **You maintain complete control** with the ability to cancel
- **The recipient sees the commitment** on the blockchain
- **Security delays protect large payments** automatically

This is the key difference from instant crypto transfers — you get time to think, verify, and if needed, change your mind.

## The Four-Stage Lifecycle

```
Creation → Time-locked → Active → Finalized
    │          │           │         │
    └──────────┴───────────┴─────────┴─→ Cancel anytime until paid
```

### Writing (Creation)

Just like filling out a paper cheque, you specify the recipient and amount. We record the USD value at this moment — think of it as writing today's date on the cheque. No money moves yet; you've just made a promise to pay.

### Dating (Time-locked)

Remember post-dated cheques? Our security delays work the same way:

- Large amounts get automatic "post-dating" for your protection
- You can set custom dates for future payments
- Your money stays in your account earning interest, just like at the bank

### Ready to Cash (Active)

The cheque is now valid and can be cashed by:

- You deciding to process it immediately
- Your [authorized assistant (Manager)](managers.md) handling it
- The recipient depositing it themselves (if you enabled this)

### Cleared or Void (Finalized)

Just like a physical cheque, it ends up either:
- **Cleared**: Money successfully transferred to recipient
- **Void**: Expired uncashed or cancelled by you

## Your Security is Our Priority

Every Digital Cheque you write is protected by a state-of-the-art security process. When a cheque is cashed, our system follows a strict procedure that makes it impossible for attackers to drain your funds:

### The "Update-First" Security Method

```
Step 1: Update our records     Step 2: Transfer funds
     "Mark as cashed"           "Send the money"
           ✓                           💸
           │                           │
           └──────────────────────────►│
                                       │
        This happens FIRST        Only THEN this happens
```

**Why this matters**: In the crypto world, there's a well-known attack where malicious actors try to cash the same payment multiple times before the system realizes it. Our "update-first" method makes this impossible — once we mark a cheque as cashed in Step 1, any attempt to cash it again will fail immediately. This protection works automatically on every single cheque, keeping your funds safe without you having to think about it.

## Smart Security Features

### Automatic USD Thresholds

Set a delay threshold (e.g., $1,000):

- Below: Cheques can be immediate
- Above: Automatic delay applied

> **Note**: Cheques cannot be created for whitelisted addresses. If you trust an address enough to whitelist it, use the [Whitelist feature for instant, unlimited transfers](whitelist.md) — Cheques are for addresses that need payment controls.

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
Yield earned: ~$48 during delay*
```

*Yield varies with current market rates

## For the Recipient: How to Cash a Digital Cheque

When someone sends you a Digital Cheque, the process is as simple as depositing a paper cheque:

### What Recipients See
1. **Notification**: They can see the pending cheque on the blockchain with all details (amount, sender, when it becomes cashable)
2. **Waiting Period**: If there's a security delay, they see exactly when they can cash it
3. **Cashing Process**: Once active, they simply click "Cash Cheque" in their wallet interface
4. **Instant Receipt**: Funds arrive in their wallet immediately upon cashing

### The Recipient's Advantages
- **Transparency**: They can verify the cheque exists before providing goods/services
- **Flexibility**: They choose when to cash it (within the validity period)
- **Certainty**: Once created, they know the funds are committed
- **Simplicity**: No complex processes — just one click to receive payment

This simplicity for recipients means you can confidently use Digital Cheques knowing you're not creating complexity for the people you pay.

## Advanced Features

### Manager-Created Cheques

Let AI or team members create cheques within your rules. Learn about [setting up Managers with cheque permissions](managers.md):

1. Manager creates cheque from approved invoice
2. Time-lock applies automatically
3. You review during delay period
4. Cancel or let it proceed

### Smart Fund Sourcing

Like the automated payment system, cheques intelligently source funds from yield when needed:

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

**Can I write a cheque to a whitelisted address?**
No — use [Whitelist](whitelist.md) for instant payments. Cheques are for non-whitelisted recipients who need payment controls.

**What happens when a cheque expires?**
Just like a void cheque at the bank, expired cheques become invalid automatically. The funds never leave your wallet, so they're immediately available for other uses. No action needed from you.

**Are there limits on cheque amounts or how many I can have?**
Yes, for security. You can set maximum values per cheque and limit total active cheques (typically 20-50). These safeguards prevent accidental overcommitment while giving plenty of flexibility for normal use.

**What are network fees (gas)?**
Think of network fees as digital postage stamps. Just like you need a stamp to send a letter through the postal system, you need a small fee to send a transaction through the blockchain network. This fee pays the decentralized computers that verify and secure your transaction. On Base L2, these "stamps" cost just a few cents, and our efficient design keeps them as low as possible.

**Can my Manager handle cheques for me?**
Yes, and it's incredibly useful. You can authorize a Wallet Manager to create and cancel cheques within limits you set. This is perfect for businesses where your CFO handles vendor payments, or individuals who want their financial advisor to help manage large transactions. The beauty is that Managers can only operate within your pre-set boundaries — they can't exceed spending limits or change your security settings. Learn how to set up these secure delegated permissions in our guide on [Managing Your Wallet with Managers](managers.md).

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

## Cheques vs Payees: Which Payment Tool is Right for You?

Understanding when to use Cheques versus Payees ensures you're using the most efficient tool for each situation:

| Feature | **Cheques** | **[Payees](payees.md)** |
|---------|-------------|----------|
| **Primary Use Case** | Flexible, one-time payments that you control until cashed | Automated, recurring payments for ongoing relationships |
| **Payment Frequency** | Single, non-repeating transaction | Scheduled intervals (weekly, monthly, etc.) |
| **Recipient Setup** | No setup needed — send to any address | Must add recipient to your "Circle of Trust" first |
| **Key Benefit** | Control & Flexibility: Create now, cancel anytime before cashed | Convenience & Automation: Set once, runs automatically |
| **Ideal For** | • Paying contractors after work approval<br>• Settling one-time invoices<br>• Sending gifts or prizes<br>• Large transfers needing review time | • Employee salaries<br>• Rent or subscriptions<br>• Regular vendor payments<br>• Allowances or stipends |
| **Management** | Each cheque managed individually | Set up once, modify schedule as needed |
| **How Payment Happens** | Recipient must actively cash the cheque | Automatic on schedule (or recipient can pull) |
| **Cancellation** | Cancel specific cheque anytime before cashed | Pause or stop entire payment schedule |

### Quick Decision Guide

**Choose Cheques when:**
- You need to pay someone just once
- You want time to review before payment completes
- The amount or timing might change
- You're not sure you'll pay this person again

**Choose Payees when:**
- You pay the same person/company regularly
- You want "set and forget" automation
- You have established trust with the recipient
- You need consistent, predictable payments

## Related Features

- **[Payees](payees.md)**: Set up automated recurring payments for regular expenses
- **[Managers](managers.md)**: Learn how to delegate payment tasks to AI or team members
- **[Whitelist](whitelist.md)**: Configure instant, unlimited transfers for your most trusted addresses
- **[User Wallet](user-wallet.md)**: Explore your complete financial command center and all its features

---

_For technical implementation details, see the [technical documentation](technical/)._
