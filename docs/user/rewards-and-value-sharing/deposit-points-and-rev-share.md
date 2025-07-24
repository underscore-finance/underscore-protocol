## Deposit Points and Revenue Sharing

Deposit Points determine your share of protocol-generated fees. The system tracks your deposit value over time and calculates your proportional share of rewards based on a transparent formula.

### How Deposit Points Work

Deposit Points measure your contribution to the protocol over time. They are not tokens but rather an accounting mechanism used to calculate your share of fee distributions.

**The Formula:**
```
Points = (USD Value of Deposits × Blocks Held) / 10^18
```

This means both your deposit value AND how long you hold assets matter for determining your rewards share.

#### Calculating Your Share

**Example Calculation:**
- You deposit: $10,000
- You hold for: 100,000 blocks (~2 weeks on Ethereum)
- Your points: (10,000 × 100,000) / 10^18 = 0.001 points

Your reward share = Your Points / Total Global Points

**Practical Example:**
- Your points: 1,000
- Global points: 100,000
- Your share: 1%
- If protocol collects $5,000 in fees
- Your claimable amount: $50

**Important**: Your percentage changes as others deposit/withdraw and as time passes.

#### Points Accumulation Over Time

**How Time Affects Points:**
- Points accumulate each block you hold assets
- Longer holding periods = more points
- Points continue growing until you claim deposit rewards
- After claiming deposit rewards, your points reset to zero

**Note**: Regular fee claims don't reset points - only deposit reward claims do.

### Two Types of Distributions

**1. Revenue Share (Claimable Loot):**
- Accumulates from swap, yield, and reward fees
- Can be claimed anytime (with cooldown)
- Doesn't affect your deposit points
- Multiple assets can accumulate

**2. Deposit Rewards:**
- Special reward pool funded separately
- Distributed based on deposit points
- Claiming resets your points to zero
- Typically single asset (e.g., UNDY token)

**Claiming Process:**
- Both types subject to cooldown periods
- Can claim all assets in one transaction
- Managers with permission can claim for you
- Gas-efficient batch claiming available

#### How Ambassador Rewards Integrate

Ambassador rewards are separate from deposit points:
- Direct fee share (not points-based)
- Percentage varies by fee type (20-30%)
- Accumulates as claimable loot
- Doesn't require deposits to earn

**Example Flow:**
- Your referral swaps $10,000 (pays $10 fee)
- You receive 30% = $3 as claimable loot
- They receive points for remaining 70%
- Both can claim when ready

### Monitoring Your Rewards

**Key Metrics to Track:**
- Current deposit points balance
- Points as % of global total
- USD value of deposits
- Last update block
- Claimable assets and amounts
- Cooldown status

**Understanding Cooldowns:**
- Prevents reward manipulation
- Typical period: 100-1000 blocks
- Owners can claim anytime
- Managers subject to cooldown

**Optimization Tips:**
- Claim when gas is low
- Batch multiple assets together
- Monitor points percentage changes
- Track earnings vs fees paid

The system ensures fair distribution through transparent on-chain calculations. Your rewards are always verifiable and claimable based on your actual contribution to the protocol.