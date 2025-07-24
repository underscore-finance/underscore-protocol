## How Protocol Fees Generate Rewards

Underscore collects fees on value-generating actions: swaps, yield profits, and external reward claims. These fees are distributed among users, ambassadors, and protocol operations through the LootDistributor contract.

### Fee Structure Details

**1. Yield Fees: Variable by Asset (Typically 10%, Max 25%)**
- Applied only to realized profits, never principal
- Example: $10,000 stETH position earns $42 profit
- Fee at 10%: $4.20
- You keep: $37.80
- Fee enters reward pool for distribution

**Important**: Yield fees are configurable per asset and capped at 25% maximum by the smart contract.

**2. Swap Fees: 0.1-0.5% Per Trade**
- Standard swaps: 0.1% (capped at 0.5%)
- Stablecoin swaps: May have different rates
- Example: $5,000 USDC → ETH swap at 0.1% = $5 fee
- Fees are configurable per asset pair

**Trading Example:**
Consider a trader with $50,000 monthly volume:
- Fees paid at 0.1%: $50
- If they hold 2% of total deposit points
- And protocol collects $5,000 total monthly fees
- Their share: $100 (2% of $5,000)
- Net benefit: $50

*Note: Actual returns depend on total protocol fees and your points percentage*

**3. External Rewards Fees: Up to 25% (Typically 10%)**
- Applied when claiming rewards from external protocols
- Example: Claim $200 CRV rewards
- Fee at 10%: $20
- You keep: $180
- Maximum fee capped at 25% by contract

### Fee Distribution Model

**How Fees Are Distributed:**
- User revenue share: Based on deposit points
- Ambassador share: 20-30% of referred user fees
- Protocol operations: Remaining percentage

The exact distribution varies by fee type and is configured in the MissionControl contract.

### Example Calculation

**Monthly Activity Scenario:**
- Wallet Balance: $25,000 in yield positions
- Yield earned: $104 (5% APY)
- Swaps performed: $10,000 volume
- External rewards claimed: $50

**Fees Generated:**
- Yield fee (10%): $10.40
- Swap fees (0.1%): $10
- Rewards fee (10%): $5
- Total fees paid: $25.40

**Potential Returns:**
If the user holds 2.5% of total deposit points and the protocol collects $2,000 in total monthly fees:
- User's share: $50 (2.5% of $2,000)
- Net position: $50 earned - $25.40 paid = $24.60 profit

*Returns scale with protocol activity and your share of deposit points*

### Ambassador Revenue Share Ratios

Ambassadors receive different percentages based on fee type:
- **Swap fees**: Typically 30% to ambassador
- **Yield fees**: Typically 30% to ambassador  
- **Rewards fees**: Typically 20% to ambassador

These ratios are configured in the smart contract and may vary. The remaining fees go to the general reward pool and protocol operations.

### Understanding Your Returns

**Key Factors Affecting Rewards:**
1. Your deposit value and holding time (determines points)
2. Total protocol fee generation
3. Number of participants sharing rewards
4. Your ambassador referrals (if any)

**Claiming Rewards:**
- Rewards accumulate until claimed
- Subject to cooldown periods between claims
- Can claim all rewards in one transaction
- Manager permissions enable delegated claiming

Actual returns vary based on protocol usage and participation. The smart contract ensures transparent, verifiable distribution of all collected fees.