---
description: Instant unlimited transfers to your most trusted addresses with time-locked security
---

# Whitelist: Unlimited Trust for Your Most Important Addresses

Your AI trading agent just spotted a massive arbitrage opportunity. You need to move $500,000 from your conservative [Underscore wallet](user-wallet.md) to your aggressive trading [Underscore wallet](user-wallet.md) immediately. But without the whitelist, you'd need to create multiple Cheques with delays or set up Payees with limits. By the time the funds arrive, the opportunity is gone.

Or your DAO needs immediate treasury consolidation. Markets are volatile, opportunities are time-sensitive, and you need to move $2 million between [wallets](user-wallet.md) now — not after security delays, not in chunks to avoid limits.

**The Whitelist** breaks the emergency glass on your own security. Your cold storage wallet. Your corporate treasury for business operations. Your backup wallet for redundancy. These addresses get unlimited transfers — no limits, no delays, no friction.

Your security should protect you from threats, not from yourself.

## Why the Whitelist Exists

### The Problem with Three-Recipient Restrictions

Your [wallet](user-wallet.md) requires every recipient to be either a [Payee](payees.md) (with limits), sent via [Cheque](cheques.md) (with delays), or Whitelisted. This keeps you safe but creates friction:

- **Payees**: Great for recurring payments, but limits restrict large transfers
- **Cheques**: Perfect for one-time payments, but delays kill time-sensitive opportunities
- **Missing option**: What about your own wallets that need instant, unlimited access?

When your AI agent spots arbitrage or your DAO needs treasury consolidation, [Payee](payees.md) limits and [Cheque](cheques.md) delays become profit killers.

### The Whitelist Solution

The Whitelist completes the payment trinity with a special category for absolute trust:

- **Your other [Underscore wallets](user-wallet.md)**: Move millions between your own accounts instantly
- **Hardware wallets**: Secure funds without friction when threats emerge
- **Corporate treasuries**: Enable instant consolidation for business operations
- **Time-locked security**: Additions require waiting period, removals are instant
- **Manager compatible**: Delegate whitelist management without giving away funds

## How the Whitelist Works

### Payment Hierarchy

Your [wallet](user-wallet.md) recognizes three types of payment recipients:

```
[Payees](payees.md) → Recurring payments with configured limits
[Cheques](cheques.md) → One-time payments with delays and cancellation
Whitelist → Instant unlimited transfers
```

Only addresses in one of these three categories can receive payments from your wallet.

### Transaction Flow

```
You initiate transfer
        ↓
Is recipient whitelisted?
        ↓
    ┌───┴───┐
    │       │
   YES      NO
    │       │
    ↓       ↓
Transfer   Is it a Payee or Cheque?
proceeds        ↓
instantly   ┌───┴───┐
            │       │
           YES      NO
            │       │
            ↓       ↓
        Apply limits  Transaction
        and proceed   BLOCKED
```

## Security Features

### Time-Locked Additions

Adding a whitelisted address follows a security delay that you control:

```
Propose → Time-Lock → Confirm → Active
Day 1      Your Choice   Ready    Until Removed
```

**This is your ultimate defense against wallet compromise.**

Every Underscore wallet has an "owner" — the external wallet (EOA or hardware wallet) that has full control. If an attacker compromises this owner wallet, the time-lock gives you a crucial defense window.

Even with full control of your owner wallet, the attacker CANNOT immediately drain your Underscore wallet funds. Here's why:

1. **Attacker tries to whitelist their address** → Enters time-lock period (e.g., 7 days)
2. **You see the pending addition** → You have days to respond, not minutes
3. **You immediately cancel the malicious addition** → Attacker's plan fails
4. **You transfer all funds to your pre-whitelisted cold storage** → Your money is safe

The attacker is forced to reveal their hand while you still have full control. They can't add their address instantly, can't speed up the time-lock, and can't stop you from moving funds to your already-whitelisted addresses.

This time delay transforms a successful attack into a failed attempt, giving you a critical window to protect your assets.

### Configurable Security Delay

The delay period is controlled by your wallet's `timeLock` setting, measured in blocks. You can set any duration that suits your needs — shorter for more convenience, longer for more security.

This same delay applies to all security-critical operations in your wallet, not just whitelist additions.

### Instant Removal

Unlike additions, removing whitelisted addresses takes effect immediately — protecting you when every second counts.

## Permission System

### Owner (You)
Complete authority over all whitelist operations:
- Add, confirm, cancel, remove addresses
- No restrictions on your control
- Override all other permissions
- Direct [rewards](rewards.md) to any whitelisted wallet

### [Managers](managers.md)
Delegated whitelist powers (if granted):
- **Propose**: Suggest new addresses for your approval
- **Confirm**: Complete additions after the security delay
- **Cancel**: Stop pending additions before they activate
- **Remove**: Delete existing whitelisted addresses

Each permission must be explicitly granted — managers only get the whitelist powers you choose to give them.

### Additional Security Features

- **Owner Change Protection**: All pending additions cancel if ownership changes
- **No Cheque Creation**: Whitelisted addresses cannot receive Cheques
- **Address Validation**: Cannot whitelist empty addresses, the wallet itself, or config contracts

## Real-World Use Cases

### Multi-Wallet Strategies

**Conservative + Aggressive Split**
- Conservative wallet: Stablecoin yield farming, vendor payments
- Aggressive wallet: AI trading agent, DeFi strategies
- Instant rebalancing: Move millions between strategies as opportunities arise

Whitelist each other for instant capital deployment when your AI spots alpha.

**Security Threat Response**
- Active wallet: Daily operations, exposed to more interactions
- Secure cold storage: Maximum security setup, rarely accessed
- Instant evacuation: Move entire balance when threats emerge

When you suspect compromise or face a wrench attack, every second counts. Whitelist your secure storage to evacuate funds instantly.

### DAO & Corporate Treasury

**Multi-Signature Operations**
- Operations wallet → Main treasury: Daily revenue consolidation
- Treasury → Operations: Instant funding for opportunities
- Emergency moves: React to governance decisions immediately

**Department Management**
- Marketing wallet needs urgent campaign funding
- Development wallet requires immediate contractor payment
- Investment wallet spots time-sensitive opportunity

Whitelist between departments for operational efficiency without compromising security.

### AI Agent Operations

**Automated Strategy Execution**
- AI identifies arbitrage across protocols
- Needs immediate capital from your yield wallet
- Opportunity window: Often under 60 seconds

Without whitelist: Cheque delays or Payee limits kill the trade
With whitelist: Your AI executes at market speed

## Common Questions

**Can I speed up the time-lock?**
No. The delay is absolute for security. Plan additions in advance.

**What if I lose access to a whitelisted address?**
Remove it immediately. A compromised whitelisted address is your highest risk.

**Can removed addresses be re-added?**
Yes, but they go through the full process again.

**What happens if I try to send to an unapproved address?**
The transaction will be blocked before any funds leave your wallet.

**Can a Manager steal my funds?**
No. Managers cannot initiate transfers or withdraw funds. They can only manage your whitelist if you've granted those specific permissions.

**How does the whitelist interact with my daily transfer limits?**
Whitelisted addresses bypass ALL limits — daily, weekly, and lifetime. This is why you should only whitelist addresses you trust completely.

## Whitelist vs Other Payment Methods

Understanding when to use the Whitelist versus other payment tools:

| Feature                 | **Whitelist**                                                          | **[Payees](payees.md)**                                                                                 | **[Cheques](cheques.md)**                                                                                      |
| ----------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| **Primary Use Case**    | Unlimited instant transfers to your most trusted addresses             | Automated, recurring payments for ongoing relationships                                                 | Flexible, one-time payments that you control until cashed                                                      |
| **Payment Limits**      | None — completely unlimited                                            | Customizable per-recipient limits                                                                       | Set per cheque with optional delays                                                                            |
| **Recipient Setup**     | Time-locked addition (i.e. 3-7 days), instant removal                       | Add to Circle of Trust with specific limits                                                             | No setup needed — send to any address                                                                          |
| **Key Benefit**         | Emergency Access: Move millions instantly when needed                  | Convenience & Automation: Set once, runs automatically                                                  | Control & Flexibility: Create now, cancel anytime before cashed                                                |
| **Ideal For**           | • Your hardware wallets • Emergency contacts • Treasury wallets • Business operations | • Employee salaries • Rent or subscriptions • Regular vendor payments • Allowances or stipends | • Paying contractors after work approval • Settling one-time invoices • Sending gifts or prizes • Large transfers needing review time |
| **Risk Level**          | Highest — can drain entire wallet                                      | Medium — limited by configured caps                                                                     | Low — cancellable until cashed                                                                                 |
| **Manager Access**      | Can manage whitelist (if permitted) but bypasses their spending limits | Managers pay within their own limits                                                                    | Managers can create/cancel within rules                                                                        |

## The Future of Trust Without Limits

Remember that AI trading opportunity that needed $500,000 moved in seconds? Or your DAO's urgent treasury consolidation? Without the Whitelist, those moments become missed opportunities and operational nightmares.

Every other security system forces you to choose: protection or accessibility. The Whitelist breaks the tradeoff. Time-locked additions keep attackers out. Instant removal maintains your control. Unlimited transfers mean your money moves at the speed of opportunity.

This is what wallet security should have been from the start. Not choosing between being safe and being functional. Not watching arbitrage windows close while funds sit in transit. Not explaining to your DAO why the treasury consolidation is delayed by security theater.

Stop being prisoner to your own protection. Start having security that knows the difference between a thief and your hardware wallet.

## Related Features

- **[Payees](payees.md)**: Set up automated recurring payments for regular expenses
- **[Cheques](cheques.md)**: One-time payments with time delays and cancellation ability
- **[Managers](managers.md)**: Learn how to delegate payment tasks to AI or team members
- **[User Wallet](user-wallet.md)**: Explore your complete financial command center and all its features

---

_For technical implementation details, see the [technical documentation](technical/)._