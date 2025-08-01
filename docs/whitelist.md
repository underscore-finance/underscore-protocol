# Whitelist: Unlimited Trust for Your Most Important Addresses

**TL;DR:**
- Grant unlimited, instant transfer access to your most trusted addresses
- Perfect for hardware wallets, emergency contacts, or treasury management
- Time-locked addition process ensures security while instant removal provides control

Your hardware wallet holding $1 million. Your spouse who needs emergency access. Your business treasury requiring daily sweeps. Some addresses deserve unlimited trust — and the Whitelist delivers exactly that.

No more being blocked by your own security limits when moving funds between your wallets. No more panic during emergencies because daily limits prevent helping family. The **Whitelist** is your wallet's VIP list — addresses that bypass all restrictions for instant, unlimited transfers.

## Core Concept: Trust Without Limits

The Whitelist creates a clear hierarchy in your wallet:

```
Regular Recipients → Subject to all limits and controls
Whitelisted Addresses → Instant unlimited transfers
```

It's like the difference between a visitor pass and executive access — whitelisted addresses have the keys to the kingdom.

## The Two-Step Security Process

Adding an address requires deliberate action and patience:

```
Propose → Time-Lock → Confirm → Active
Day 1      3-7 days    Day 4+    Forever
```

This delay is your safety net. Even if someone compromises your wallet, they can't immediately drain it to their address.

### Time-Lock Examples
- Personal wallet (<$100k): 3 days (129,600 blocks)
- High-value wallet (>$100k): 7 days (302,400 blocks)
- Business treasury: Custom based on risk tolerance

## Permission Hierarchy

### The Owner (You)
Complete authority over all whitelist operations:
- Add, confirm, cancel, remove addresses
- No restrictions on your control
- Override all other permissions

### [Managers](managers.md)
Delegated whitelist powers (if granted):
- `canAddPending`: Propose new addresses
- `canConfirm`: Complete additions after delay
- `canCancel`: Stop pending additions
- `canRemove`: Delete existing entries

Dual-permission system: Both individual AND global settings must allow the action.

### Security Override
MissionControl can:
- Cancel suspicious pending additions
- Remove addresses in emergencies
- Cannot add new addresses (safety only)

## Security Features

### Owner Change Protection
If wallet ownership changes during the pending period, ALL pending whitelist proposals automatically cancel. This prevents attackers from completing their own additions.

### Address Validation
Cannot whitelist:
- Empty addresses
- The wallet itself
- Current owner address
- Configuration contracts

### No Cheque Creation
Whitelisted addresses cannot receive Cheques — they already have unlimited access.

## Real-World Use Cases

### Personal Finance

**Multi-Wallet Security**
- Hot wallet: $5k-50k daily operations
- Hardware wallet: $100k-1M cold storage
- Multi-sig vault: $1M+ ultimate security

Whitelist your cold storage to instantly secure funds during market crashes or security concerns.

**Emergency Family Access**
Whitelist trusted family for:
- Medical emergency funding
- Crisis situations requiring immediate help
- Peace of mind knowing they're covered

### Business Operations

**Treasury Management**
- Operations → Treasury: Daily $200k revenue sweeps
- Treasury → Payroll: Monthly $500k+ transfers
- Treasury → Investments: Deploy millions instantly

Save 10+ hours monthly by eliminating transfer limits between company wallets.

**Multi-Entity Operations**
- Subsidiary transfers
- Department allocations
- Joint venture funding

### Trading & Investment

**High-Frequency Trading**
- Deploy $250k during flash crashes
- Secure profits instantly
- Rebalance between strategies

Without whitelist: Miss opportunities due to $25k daily limits
With whitelist: Act in seconds with any amount

## What NOT to Whitelist

❌ **Exchange deposit addresses** - Can change without notice
❌ **Service providers** - Use Payees with limits instead
❌ **New acquaintances** - No matter how trustworthy
❌ **Smart contracts** - Unless thoroughly audited
❌ **Temporary needs** - Use Cheques for one-time transfers

Remember: Whitelisted addresses can drain your entire wallet instantly.

## Best Practices

1. **Minimal List**: Only addresses you absolutely trust
2. **Document Everything**: Record why each address is whitelisted
3. **Regular Audits**: Review quarterly, remove unnecessary entries
4. **Test First**: Send $10 before trusting with millions
5. **Plan Ahead**: Add addresses during calm periods, not crises

## Quick Setup Guide

### For Personal Use
1. Whitelist your hardware wallet
2. Add spouse/family emergency contact
3. Use 3-day time-lock
4. Document in secure location

### For Business
1. Whitelist treasury wallets
2. Add operational wallets
3. Use 7-day time-lock for high-value
4. Implement dual-control (propose/confirm split)

### For Traders
1. Whitelist main trading wallets
2. Add cold storage for profits
3. Balance speed vs security in delay choice
4. Keep exchange addresses OFF the list

## Common Questions

**Can I speed up the time-lock?**
No. The delay is absolute for security. Plan additions in advance.

**What if I lose access to a whitelisted address?**
Remove it immediately. A compromised whitelisted address is your highest risk.

**How many addresses should I whitelist?**
Most users need 2-5. Keep it minimal for security.

**Can removed addresses be re-added?**
Yes, but they go through the full process again.

## Integration with Other Features

- **[Managers](managers.md)**: Have limits; whitelisted addresses don't
- **[Payees](payees.md)**: Pull payments within bounds; whitelist is unlimited push
- **[Cheques](cheques.md)**: Controlled scheduled payments; whitelist is instant unlimited

## The Bottom Line

The Whitelist solves a fundamental problem: how to maintain strong security while enabling legitimate large transfers. It's the difference between being protected by your limits and being trapped by them.

For personal users: Move millions between your wallets instantly while keeping hackers at bay.
For businesses: Eliminate treasury friction while maintaining audit trails.
For everyone: Emergency access when it matters most.

Your money, your addresses, your control — with no artificial limits standing in the way.

## Related Features

- **[Managers](managers.md)**: Delegate whitelist management permissions
- **[Payees](payees.md)**: Recurring payments with spending limits
- **[Cheques](cheques.md)**: One-time payments with time delays
- **[User Wallet](user-wallet.md)**: Configure all security settings

---

_For technical implementation details, see the [technical documentation](technical/)._