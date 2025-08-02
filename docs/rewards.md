---
description: Earn revenue share from protocol fees with no lock-ups or complex tokenomics
---

# Rewards: Real Revenue Share from Real DeFi Activity

You just paid $50 in swap fees. Another protocol pocketed 100% of it. Your $25K position earned the protocol $2,500 in yield fees this year. You got nothing back. Meanwhile, professional trading firms negotiate revenue share deals worth millions. Regular users are excluded from these deals.

**Underscore** shares actual protocol revenue with users and ambassadors. Swap fees, yield fees, rewards fees — up to 50% flows directly back to participants. Direct fee sharing in the assets you already use, plus additional rewards and bonuses.

Finally, a protocol that treats you like a partner, not exit liquidity.

## How Revenue Sharing Works

Underscore collects fees on value-generating activities and distributes them through the LootDistributor:

```
User Activity → Protocol Fee → Distribution:
                              ├── Ambassador Revenue Share (50% default)
                              ├── Yield Bonuses (if configured)
                              └── Deposit Rewards Pool
```

The math is transparent. The distribution is automatic. The claiming is permissionless.

_Note: All percentages shown are defaults and examples. Actual rates are configurable by the protocol._

## Ambassador Earnings: Two Revenue Streams

Ambassadors earn when their referred users generate value:

### 1. Revenue Share on All Fees

**Automatic percentage of every fee generated** (default 50%, configurable):

| User Activity       | Protocol Fee | Ambassador Gets 50% | Example                     |
| ------------------- | ------------ | ------------------- | --------------------------- |
| $10,000 swap        | 0.25% = $25  | $12.50              | User swaps tokens           |
| $1,000 yield profit | 10% = $100   | $50                 | User realizes gains         |
| $200 rewards claim  | 10% = $20    | $10                 | User claims MORPHO/WELL/etc |

### 2. Yield Bonuses (Only on Yield Profits)

**Additional rewards when users realize yield profits** (not on swaps or reward claims):

- 25% bonus on top of the yield profit amount (typical example, varies by asset)
- Can be yield asset, underlying, or alternative tokens (configurable by protocol)
- Requires: eligible yield position and available distributor balance
- Distributed first-come, first-served when balance is limited

**Example**: User realizes $1,000 in yield profit

- User keeps their $1,000 profit
- Ambassador gets $250 bonus (25% of profit amount)
- This is IN ADDITION to the $50 revenue share from fees

**Example Ambassador Income**:

Assuming each user generates $50/month in total protocol fees:

- Protocol collects: $50 in fees
- Ambassador receives: $25 (50% revenue share)

**Network Growth Projections**:
| Users in Network | Monthly Revenue Share | Annual Revenue Share |
|------------------|----------------------|---------------------|
| 5 users | $125 | $1,500 |
| 10 users | $250 | $3,000 |
| 20 users | $500 | $6,000 |
| 50 users | $1,250 | $15,000 |

_Plus potential yield bonuses when users realize profits (calculated separately based on actual yield performance)_

## User Earnings: Two Reward Mechanisms

Users earn through participation and performance:

### 1. Yield Bonuses (Only on Yield Profits)

**Direct bonus on your realized yield profits** (not on swaps or rewards):

- 25% extra on top of your yield profit (typical example, configurable)
- Paid automatically when claiming yield
- Only applies to yield strategies, not trading or reward claims
- Requires: eligible yield position and available distributor balance
- Example: Realize $1,000 yield profit → Get $250 bonus

### 2. Deposit Points System

**Share of protocol-wide rewards based on holdings**:

```
Points = (USD Value × Blocks Held)
Your Share = Your Points / Total Global Points
```

**How it works**:

1. Hold assets in your [wallet](user-wallet.md)
2. Accumulate points over time
3. Protocol adds rewards to pool
4. Claim your proportional share

**Example calculation**:

- Hold $10,000 for 2 weeks = 60.48 points
- Total protocol points = 3,024
- Your share = 2%
- $5,000 rewards added to pool → You claim $100

## Fee Structure

### What Gets Collected

_All fees are configurable. Examples below show typical defaults._

| Activity | Fee Range       | Applied To      | Example                  |
| -------- | --------------- | --------------- | ------------------------ |
| Yield    | 10% (default)   | Profits only    | $1,000 profit → $100 fee |
| Swaps    | 0.25% (default) | Trade amount    | $10,000 trade → $25 fee  |
| Rewards  | 10% (default)   | External claims | $200 claim → $20 fee     |

### Where Fees Go

All fees flow through transparent distribution:

- **Ambassador share**: 50% to referrer (default, configurable)
- **Yield bonuses**: If eligible and available
- **Deposit pool**: For points-based distribution
- **Protocol**: Remaining for operations

## Common Questions

**Q: When can I claim?**
A: Immediately after fees generate, subject to cooldown. [Managers](managers.md) can claim on your behalf if authorized.

**Q: Can rewards be lost?**
A: No, they accumulate until claimed (limited by contract balance).

**Q: How do points work?**
A: Points = deposit value × time. More deposits + longer holding = more points.

**Q: What's the cooldown?**
A: Configured cooldown period, preventing spam while allowing regular claims.

**Q: Do bonuses always pay out?**
A: Only if distributor has sufficient balance. First-come, first-served.

## The Bottom Line

Traditional protocols keep 100% of the fees you generate. Underscore shares real revenue from real activity.

**For Ambassadors**: Build a network, earn 50% of all fees forever (default rate). Five active users = $2,700/year. Scale from there.

**For Users**: Your deposits earn points. Your yields earn bonuses. Your activity generates returns.

Transparent fee sharing that rewards participation. Use DeFi, get paid. Refer users, get paid more. Rewards come in various forms — the assets you're already using, protocol tokens, or other valuable assets.

This is how DeFi should work — where protocols and users succeed together.

---

## Next Steps

- **[Deploy Your Wallet](user-wallet.md)**: Start earning rewards immediately
- **[Become an Ambassador](user-wallet.md)**: Build a network and earn revenue share
- **[Add Managers](managers.md)**: Automate reward claiming
- **[Set Up Whitelist](whitelist.md)**: Direct rewards to any trusted wallet

---

_For technical implementation details, see the [LootDistributor contract documentation](technical/)._
