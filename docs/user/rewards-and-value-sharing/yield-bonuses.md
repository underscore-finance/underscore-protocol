## Yield Bonuses

Yield Bonuses are additional rewards distributed to users holding eligible yield-bearing assets. These bonuses are configured per asset and distributed automatically when yield is realized through the protocol.

### How Yield Bonuses Work

**Technical Implementation:**
- Bonuses triggered when yield profits are realized
- YieldLego contracts determine eligibility
- Bonus rates configured in MissionControl
- Distribution respects available balance limits

**Bonus Calculation:**
- Based on percentage of yield realized
- Can be paid in three forms:
  1. In-kind (same asset)
  2. Underlying asset
  3. Alternative asset (e.g., protocol tokens)

**Example:**
- You realize $100 in stETH yield
- Bonus rate: 20%
- You receive: $20 bonus (in configured asset)

### Types of Yield Bonus Configurations

**1. Standard User Bonus**
- Configured per asset via `bonusRatio`
- Typical range: 10-30% of yield realized
- Paid from available LootDistributor balance
- Example: 20% bonus on $100 yield = $20 bonus

**2. Ambassador Bonus**
- Additional bonus for ambassadors
- Configured via `ambassadorBonusRatio`
- Stacks with regular user bonus
- Rewards ambassadors for bringing active users

**3. Alternative Asset Bonuses**
- Paid in different token than yield asset
- Requires price oracle for conversion
- Common for partnership promotions
- Example: Earn UNDY tokens for stETH yield

### Bonus Distribution Examples

**In-Kind Bonus (Same Asset):**
- Hold: 100 stETH
- Yield realized: 0.5 stETH  
- Bonus at 20%: 0.1 stETH
- Total received: 0.6 stETH
- Benefit: Compounds automatically

**Underlying Asset Bonus:**
- Hold: Vault token worth 10 ETH
- Yield realized: $200 value
- Bonus: $40 worth of ETH
- Benefit: Liquid ETH without unwrapping

**Alternative Asset Bonus:**
- Hold: $10,000 in yield position
- Yield realized: $100
- Bonus: $20 worth of UNDY tokens
- Conversion: Based on current oracle prices
- Benefit: Accumulate protocol tokens

### Important Bonus Mechanics

**Eligibility Requirements:**
- Asset must be configured for bonuses
- YieldLego must return `isEligibleForYieldBonus = true`
- Sufficient balance in LootDistributor
- Yield must be realized (not just accrued)

**Distribution Priority:**
1. Contract checks available balance
2. Subtracts reserved amounts (other claims)
3. Calculates maximum payable bonus
4. Distributes up to configured percentage

**Limitations:**
- Bonuses paid only from available funds
- No borrowing or minting for bonuses
- If insufficient funds, partial payment
- First-come, first-served basis

### Claiming Yield Bonuses

**How Bonuses Are Distributed:**
- Automatically added to claimable loot
- No separate claim process needed
- Subject to same cooldown as other rewards
- Tracked per asset for transparency

**Monitoring Your Bonuses:**
- Check claimable assets in LootDistributor
- View accumulated amounts per asset
- Track bonus events in transaction history
- Verify calculations on-chain

**Optimization Strategies:**
- Time yield realizations for active bonuses
- Consolidate positions in bonus-eligible assets
- Monitor LootDistributor balance for availability
- Claim during low gas periods

**Key Takeaway**: Yield bonuses provide additional rewards for holding eligible assets, but actual payments depend on configured rates, available funds, and yield realization timing. Always verify current bonus configurations before making investment decisions.