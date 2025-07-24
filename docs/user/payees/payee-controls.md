## Payee Controls

You have a comprehensive set of controls to define the exact terms of each payment relationship. These settings are enforced by the `Sentinel` contract for every transaction.

### Understanding the Dual Limit System

Underscore provides two ways to set limits, giving you maximum flexibility:
- **Unit Limits**: Based on token amounts (e.g., 1000 USDC)
- **USD Limits**: Based on dollar value (e.g., $5,000 worth of any token)

You can use either or both. This dual system protects you during market volatility—your ETH payments won't accidentally overspend if ETH price spikes.

### Financial Limits

#### Per-Transaction Cap (`perTxCap`)
The maximum amount a Payee can receive in a single transaction.
* *Example*: Set 5000 USDC cap for vendor payments
* *Example*: Set $10,000 USD cap for large invoices
* *Use case*: Prevents accidental overpayment due to input errors

#### Per-Period Cap (`perPeriodCap`)
The total amount a Payee can receive within a recurring time window.
* *Example*: $6,000 per month for employee salary
* *Example*: 500 USDC per week for recurring services
* *How it works*: Resets automatically each period—unused amounts don't roll over

#### Lifetime Cap (`lifetimeCap`)
The cumulative total amount a Payee can ever receive.
* *Example*: $50,000 total for a contractor's project
* *Example*: 10,000 USDC for a limited engagement
* *Security benefit*: Once reached, no more payments possible without your intervention

### Timing & Frequency Controls

#### Period Length (`periodLength`)
Defines your payment cycle in blocks.
* *Example*: 216,000 blocks ≈ 30 days for monthly payments
* *Example*: 50,400 blocks ≈ 7 days for weekly payments
* *Tip*: Periods start from the Payee's first transaction

#### Max Transactions Per Period (`maxNumTxsPerPeriod`)
Limits payment frequency within each period.
* *Example*: 1 transaction per month for salary
* *Example*: 4 transactions per week for flexible contractor
* *Protection*: Prevents payment spam or abuse

#### Transaction Cooldown (`txCooldownBlocks`)
Mandatory waiting period between payments.
* *Example*: 7,200 blocks ≈ 24 hours between payments
* *Example*: 300 blocks ≈ 1 hour for more frequent needs
* *Why it matters*: Gives you time to react if something seems wrong

### Asset Restrictions

#### Primary Asset Settings
Control which tokens can be sent to each Payee.
* **primaryAsset**: Preferred token for this Payee (e.g., USDC address)
* **onlyPrimaryAsset**: If true, blocks all other tokens

*Examples*:
- Salary in USDC only: Set primaryAsset to USDC, enable onlyPrimaryAsset
- Vendor accepting any stablecoin: Leave onlyPrimaryAsset false

### Safety Features

#### Fail on Zero Price (`failOnZeroPrice`)
Critical protection during oracle failures or market anomalies.
* *When enabled*: Blocks transactions if token price reads as $0
* *Why crucial*: Prevents paying 1000 ETH when system thinks ETH = $0
* *Best practice*: Always enable unless you have specific reason not to

This comprehensive control system ensures your automated payments are just as safe—if not safer—than manual transactions.