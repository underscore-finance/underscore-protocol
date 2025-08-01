# Rewards: Get Paid for Using DeFi the Right Way

Every protocol promises rewards. Most deliver complexity, vesting schedules, and tokens you'll never use. Underscore does it differently — you get real value sharing from actual protocol revenue, paid in assets you already hold.

No governance tokens. No staking requirements. No lock-ups. Just transparent fee sharing that rewards active users and those who grow the ecosystem. This is DeFi alignment done right.

## Core Concept: Real Revenue, Real Rewards

Underscore collects fees only on value-generating activities and shares them with participants:

```
Protocol Fees Collected → LootDistributor → You (based on participation)
```

The more you use the protocol, the more you earn. The more users you bring, the more you earn. Simple, transparent, sustainable.

## Three Ways to Earn

### 1. Deposit Points: Your Share of Protocol Revenue

Hold assets in your wallet, earn points over time, claim your share of fees.

**The Formula**:
```
Points = (USD Value × Blocks Held) / 10^18
Your Share = Your Points / Total Global Points
```

**Example**: 
- Hold $10,000 for 2 weeks (~604,800 blocks)
- Earn proportional share of all protocol fees
- Larger deposits + longer holding = bigger share

Points accumulate until you claim deposit rewards (then reset to zero).

### 2. Ambassador Revenue: Earn from Your Network

When users you refer generate fees, you automatically receive 20-30% of those fees.

**Revenue Split by Fee Type**:
- Swap fees: ~30% to ambassador
- Yield fees: ~30% to ambassador  
- Rewards fees: ~20% to ambassador

**Realistic Examples**:
- 5 active users × $50 monthly fees each = $75/month to you
- 20 mixed users averaging $30 fees = $180/month passive income
- Scale with protocol growth, not token speculation

Relationships are permanent on-chain. Earn as long as your referrals stay active.

### 3. Yield Bonuses: Extra Rewards on Profits

Eligible yield positions can earn bonus rewards when profits are realized.

**How Bonuses Work**:
- Configured per asset (typically 10-30% of yield)
- Paid in-kind, underlying, or alternative assets
- Subject to available balance in distributor
- Automatic distribution with yield claims

**Example**: Realize $100 in stETH yield → Get $20 bonus in stETH

## Fee Structure: What You Pay, What You Earn

### Fees Collected

**Yield Fees**
- Typically 10% of profits (max 25%)
- Only on gains, never principal
- Example: $100 profit → $10 fee → distributed to users

**Swap Fees**
- 0.1-0.5% per trade (varies by pair)
- Example: $10,000 swap → $10-50 fee → shared with participants

**Rewards Fees**
- Up to 25% on external protocol claims
- Example: Claim $200 CRV → $20 fee → into reward pool

### Your Net Position

The key question: Do you earn more than you pay?

**Active User Example**:
- Monthly activity: $25,000 yielding 5% APY
- Fees paid: ~$25 on yield and swaps
- If holding 2% of deposit points: Earn $50 share
- Net profit: $25/month ($300/year)

Returns scale with:
- Your deposit size and holding time
- Total protocol activity
- Number of active referrals

## How Distribution Works

### Claiming Your Rewards

1. **Check Claimable Assets**: View all accumulated rewards
2. **Respect Cooldowns**: Typically 100-1,000 blocks between claims
3. **Batch Claims**: Get all assets in one transaction
4. **Manager Support**: [Managers](managers.md) can claim if permitted

### Two Types of Claims

**Revenue Share (Claimable Loot)**
- Accumulates from all fee types
- Claim anytime (with cooldown)
- Doesn't affect deposit points
- Multiple assets possible

**Deposit Rewards**
- Special distributions (like UNDY tokens)
- Based on points share
- Claiming resets points to zero
- Usually single asset

### Tracking Your Earnings

Monitor these metrics:
- Current deposit points
- Points as % of global total
- Claimable assets and amounts
- Ambassador referral activity
- Cooldown status

## Building Ambassador Income

### Quality Over Quantity

**Target High-Value Users**:
- Active traders (generate swap fees)
- Yield farmers (consistent yield fees)
- Long-term holders (stable point generation)
- Protocol enthusiasts (understand [all features](user-wallet.md))

**Realistic Growth**:
- Start with 5-10 quality referrals
- Help them succeed in the protocol
- Let compound effects build over time
- Focus on sustainable relationships

### Example Ambassador Scenarios

**Small Network** (5 users, $10k each):
- Monthly fees per user: ~$40
- Your 30% share: $12 per user
- Total monthly: $60
- Annual passive: $720

**Growth Network** (20 active users):
- Average fees: $30/user/month
- Your share: $9 per user
- Total monthly: $180
- Annual passive: $2,160

**Scaled Network** (50+ users):
- Mixed activity levels
- $15 average fees per user
- Monthly earnings: $225+
- Annual passive: $2,700+

## Yield Bonus Mechanics

### Eligibility Requirements
- Asset must be configured for bonuses
- Yield must be realized (not just accrued)
- Sufficient balance in distributor
- First-come, first-served distribution

### Bonus Types

**In-Kind**: Same asset as yield (compounds naturally)
**Underlying**: Base asset of yield position
**Alternative**: Different token (often UNDY)

### Distribution Priority
1. Check available balance
2. Calculate maximum payable
3. Distribute up to configured %
4. Add to claimable loot

## Common Questions

**When do rewards become claimable?**
Immediately as fees are generated, subject to cooldowns.

**Can I lose accumulated rewards?**
No, they're yours until claimed (subject to contract balance).

**Do small deposits earn anything?**
Yes, but returns scale with deposit size and protocol activity.

**How often should I claim?**
When gas costs make sense relative to rewards amount.

**Can rewards run out?**
Only bonus rewards depend on distributor balance. Fee shares come directly from activity.

## The Bottom Line

Underscore's reward system aligns everyone's interests: users earn from participation, ambassadors earn from growth, and the protocol thrives from activity.

No token gymnastics. No unsustainable yields. Just transparent revenue sharing from real DeFi usage. The more value the protocol creates, the more participants earn.

Your rewards grow with your participation and the ecosystem's success. Start earning by using DeFi through Underscore — where every transaction contributes to your returns.

## Related Features

- **[User Wallet](user-wallet.md)**: Deploy your wallet to start earning
- **[Managers](managers.md)**: Automate reward claiming with AI
- **[Payees](payees.md)**: Receive ambassador rewards automatically
- **[Whitelist](whitelist.md)**: Instant access to your earned rewards

---

_For technical implementation details, see the [technical documentation](technical/)._