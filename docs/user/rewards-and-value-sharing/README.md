## Understanding Underscore's Rewards System

The Underscore Protocol distributes protocol-generated fees back to users through a transparent, on-chain rewards system. When you use the protocol for swaps, yield generation, or external rewards claiming, a portion of the fees collected are shared with active participants.

### How Rewards Work

The protocol collects fees from value-generating activities and distributes them through the `LootDistributor` smart contract. Your share is determined by your participation level and calculated transparently on-chain.

**Three Types of Rewards**:

**1. Revenue Sharing Through Deposit Points**  
Your share of protocol fees is calculated based on your deposit value and time held. The formula: `Points = USD Value × Blocks Held / 10^18`. Higher balances and longer holding periods result in more points, which determine your percentage of fee distributions.

**2. Ambassador Revenue Share**  
When users you refer generate fees, you receive a percentage (typically 20-30%) of their fee contributions. This creates ongoing revenue sharing between ambassadors and their referrals. The exact percentage varies by fee type.

**3. Yield Bonuses**  
Eligible yield-bearing assets may earn additional bonuses during promotional periods. These bonuses can be paid in the same asset, the underlying asset, or partner tokens. Bonus rates and eligibility are configured per asset and may change.

### Key Features of the Rewards System

**Transparent Distribution**:
* All fees and distributions tracked on-chain
* Share calculation based on verifiable formulas
* Claims subject to cooldown periods (configurable)
* Multiple claim options: individual rewards or batch claiming

**Fee Structure Overview**:
* **Swap fees**: 0.1-0.5% (varies by asset pair)
* **Yield fees**: Up to 25% of profits only (typically 10%)
* **External rewards fees**: Up to 25% of claimed rewards

**Important Notes**:
* Fees are split between users, ambassadors, and protocol operations
* Actual returns depend on protocol activity and your participation level
* Rewards accumulate until claimed (subject to available balances)
* Manager permissions can allow delegated claiming