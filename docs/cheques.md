---
description: One-time payments you can cancel anytime before they're cashed
---

# Digital Cheques: Send Money with Total Control

You send $5,000 USDC to a contractor. Three hours later, you realize it's the wrong address. Your money? Gone forever. No undo button. No customer service. Just an expensive lesson in triple-checking addresses.

Or you're paying a vendor for work they haven't finished yet. With traditional crypto, you either pay upfront and hope, or make them wait and chase you for payment. Neither feels right.

**Digital Cheques** bring the control of paper cheques to crypto — without the paper. Write payments that recipients cash on their schedule. Cancel anytime before they do. Set automatic delays for large amounts. Keep earning yield until the moment of payment in your [wallet](user-wallet.md).

Finally, crypto payments that understand mistakes happen.

## Why Digital Cheques Exist

### The Problem with Instant Crypto Payments

Traditional crypto transfers are irreversible the moment you click send. No grace period. No take-backs. This creates unnecessary risk for legitimate transactions where:

- You need to verify work before releasing payment
- Large amounts require extra security measures
- Payment timing needs to align with business processes
- Mistakes in addresses or amounts must be correctable

### The Digital Cheque Solution

Digital Cheques separate payment authorization from execution:

- **Write Now, Pay Later**: Create a payment commitment that executes on your terms
- **Cancellable Until Cashed**: Maintain control until the moment funds transfer
- **Automatic Security Delays**: Large payments get built-in review periods
- **Yield Preservation**: Funds keep earning in your wallet until payment, plus [protocol rewards](rewards.md)
- **One-Off Simplicity**: No recurring schedules to manage — perfect for single payments

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

## Smart Security Features

### Automatic USD Thresholds

Set a single delay threshold (e.g., $1,000):

- Below: Cheques can be immediate
- Above: Automatic delay applied

> **Note**: Cheques cannot be created for [whitelisted](whitelist.md) addresses. If you trust an address enough to whitelist it, use the [Whitelist feature for instant, unlimited transfers](whitelist.md) — Cheques are for addresses that need payment controls.

Example impact:

- $500 payment → No delay needed
- $5,000 payment → Security delay applied

### Time Controls

- **Expensive Delay**: How long high-value cheques wait (e.g., 3-7 days)
- **Default Expiry**: How long cheques stay active (e.g., 30 days)
- **Custom Timing**: Override per cheque as needed

Time is measured in blocks (on Base L2: ~2 seconds per block, ~43,200 blocks per day).

## Financial Controls

You can set a variety of controls and limits to ensure your Digital Cheques work exactly how you want them to. These controls help you manage risk, prevent mistakes, and maintain oversight of your payment operations. Whether you're an individual managing personal finances or a business handling vendor payments, you can customize these settings to match your specific needs and comfort level.

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
**Pull Payment**: Recipient claims when ready (must be explicitly enabled)

### Who Can Cancel

**Owner**: Any cheque, anytime before payment
**Security**: Emergency cancellation rights only

## Real-World Configurations

### Social Payment

```
Amount: $30 USDC
Unlock: Immediate (under threshold)
Expiry: 7 days
Pull: Enabled
Result: Friend grabs lunch money when convenient
```

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

\*Yield varies with current market rates

## The Recipient Experience

Digital Cheques are designed to be just as simple for recipients as they are secure for senders. Recipients benefit from complete transparency — they can verify a cheque's existence and terms on the blockchain before providing goods or services. Once the security delay (if any) has passed, the recipient can claim their payment at their convenience within the validity period.

This creates a trust-building dynamic: the recipient sees your commitment to pay, while you maintain the ability to cancel if something goes wrong. The blockchain ensures both parties have clear visibility into the payment status at all times, eliminating the uncertainty that often surrounds traditional payment methods.

## Advanced Features

### [Manager](managers.md)-Created Cheques

Let AI or team members create cheques within your rules. Learn about [setting up Managers with cheque permissions](managers.md):

1. [Manager](managers.md) creates cheque from approved invoice
2. Time-lock applies automatically
3. You review during delay period
4. Cancel or let it proceed

### Smart Fund Sourcing

Like the automated payment system, cheques intelligently source funds from yield when needed:

- Check liquid balance first
- Auto-withdraw from Aave/Morpho/etc if needed
- Complete payment in one transaction

## Common Questions

**What if I send the wrong amount?**
Cancel the cheque before it's cashed, create a new one.

**Can recipients see pending cheques?**
Yes, full transparency on-chain from creation.

**Can I modify a cheque?**
No, but you can cancel and recreate with new terms.

**Can I write a cheque to a whitelisted address?**
No — use [Whitelist](whitelist.md) for instant payments. Cheques are for non-whitelisted recipients who need payment controls.

**What happens when a cheque expires?**
Just like a void cheque at the bank, expired cheques become invalid automatically. The funds never leave your wallet, so they're immediately available for other uses. No action needed from you.

**Are there limits on cheque amounts or how many I can have?**
Yes, for security. You can set maximum values per cheque and limit total active cheques. These safeguards prevent accidental overcommitment while giving plenty of flexibility for normal use.

**Can my [Manager](managers.md) handle cheques for me?**
Yes, and it's incredibly useful. You can authorize a [Wallet Manager](managers.md) to create and cancel cheques within limits you set. This is perfect for businesses where your CFO handles vendor payments, or individuals who want their financial advisor to help manage large transactions. The beauty is that Managers can only operate within your pre-set boundaries — they can't exceed spending limits or change your security settings. Learn how to set up these secure delegated permissions in our guide on [Managing Your Wallet with Managers](managers.md).

## Cheques vs Payees: Which Payment Tool is Right for You?

Understanding when to use Cheques versus Payees ensures you're using the most efficient tool for each situation:

| Feature                 | **Cheques**                                                                                                                                    | **[Payees](payees.md)**                                                                                 |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| **Primary Use Case**    | Flexible, one-time payments that you control until cashed                                                                                      | Automated, recurring payments for ongoing relationships                                                 |
| **Payment Frequency**   | Single, non-repeating transaction                                                                                                              | Scheduled intervals (weekly, monthly, etc.)                                                             |
| **Recipient Setup**     | No setup needed — send to any address                                                                                                          | Must add recipient to your "Circle of Trust" first                                                      |
| **Key Benefit**         | Control & Flexibility: Create now, cancel anytime before cashed                                                                                | Convenience & Automation: Set once, runs automatically                                                  |
| **Ideal For**           | • Splitting lunch with coworkers • Paying contractors after work approval • Settling one-time invoices • Sending gifts or prizes • Large transfers needing review time | • Employee salaries • Rent or subscriptions • Regular vendor payments • Allowances or stipends |
| **Management**          | Each cheque managed individually                                                                                                               | Set up once, modify schedule as needed                                                                  |
| **How Payment Happens** | Can be cashed by owner/manager or pulled by recipient (if enabled)                                                                             | Can be executed by owner/manager or pulled by recipient (if enabled)                                    |
| **Cancellation**        | Cancel specific cheque anytime before cashed                                                                                                   | Pause or stop entire payment schedule                                                                   |

## The Future of Crypto Payments

Remember that $5,000 you accidentally sent to the wrong address? With Digital Cheques, that's a story that never happens.

Every other payment method forces you to choose: instant but irreversible, or slow but safe. Digital Cheques break the tradeoff. Write payments with the confidence of knowing you can cancel. Let recipients cash on their timeline. Keep your funds earning until the last second. Get automatic protection on large amounts without committees or delays.

This is what crypto payments should have been from the start. Not just moving money, but moving it intelligently.

Stop hoping you got the address right. Start knowing you can fix it if you didn't.

## Related Features

- **[Payees](payees.md)**: Set up automated recurring payments for regular expenses
- **[Managers](managers.md)**: Learn how to delegate payment tasks to AI or team members
- **[Whitelist](whitelist.md)**: Configure instant, unlimited transfers for your most trusted addresses
- **[User Wallet](user-wallet.md)**: Explore your complete financial command center and all its features

---

_For technical implementation details, see the [technical documentation](technical/)._
