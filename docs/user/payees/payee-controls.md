## Payee Controls

You have a comprehensive set of controls to define the exact terms of each payment relationship. These settings are enforced by the `Sentinel` contract for every transaction.

### Understanding the Dual Limit System

Underscore provides two parallel ways to set limits, giving you maximum flexibility and protection:

```
Unit Limits (Token Amounts)        USD Limits (Dollar Values)
├─ Per Transaction: 1000 USDC      ├─ Per Transaction: $1,000
├─ Per Period: 5000 USDC           ├─ Per Period: $5,000  
└─ Lifetime: 50000 USDC            └─ Lifetime: $50,000

Applied Rule: The MORE RESTRICTIVE limit always wins
```

**Example Scenarios**:
- Sending 1000 USDC when USDC = $1.00 → Both limits allow ✓
- Sending 1000 USDC when USDC = $1.10 → USD limit blocks (would be $1,100) ✗
- Sending 100 ETH when ETH = $2,000 → USD limit blocks (would be $200,000) ✗

This dual system protects you during market volatility—your ETH payments won't accidentally overspend if ETH price spikes.

### Financial Limits

#### Per-Transaction Cap (`perTxCap`)
The maximum amount a Payee can receive in a single transaction.
* *Example*: Set 5000 USDC cap for vendor payments
* *Example*: Set $10,000 USD cap for large invoices
* *Use case*: Prevents accidental overpayment due to input errors

#### Per-Period Cap (`perPeriodCap`)
The total amount a Payee can receive within a recurring time window.

**Visual Example - $10,000 Monthly Limit**:
```
Month 1                    Month 2                    Month 3
[=====$10k limit=====]    [=====$10k limit=====]    [=====$10k limit=====]
Used: $7,000              Used: $10,000             Used: $3,000
Remaining: $3,000         Remaining: $0              Remaining: $7,000
        ↓                         ↓                         ↓
   (doesn't roll over)      (hit the cap)           (fresh start)
```

* *Employee salary*: $6,000 per month, paid in 2 installments
* *Vendor payments*: $20,000 per month, multiple invoices
* *Contractor*: 500 USDC per week for ongoing services

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
Control which tokens can be sent to each Payee—critical for preventing wrong-token mistakes.

* **primaryAsset**: The main token this Payee receives (e.g., USDC address)
* **onlyPrimaryAsset**: If true, ONLY this token can be sent

**Common Configurations**:

| Scenario | primaryAsset | onlyPrimaryAsset | Result |
|----------|--------------|-------------------|---------|
| Salary payments | USDC | true | Can only receive USDC |
| Rent payments | USDC | true | Landlord protected from volatile tokens |
| Trading services | (empty) | false | Can receive any token |
| Stablecoin vendor | USDT | false | Prefers USDT but accepts others |

**Why This Matters**: Prevents sending $5,000 worth of a memecoin when you meant to send USDC

### Safety Features

#### Fail on Zero Price (`failOnZeroPrice`)
Critical protection during oracle failures or market anomalies.
* *When enabled*: Blocks transactions if token price reads as $0
* *Why crucial*: Prevents paying 1000 ETH when system thinks ETH = $0
* *Real example*: If oracle fails and shows ETH = $0, your $5,000 limit wouldn't protect you
* *Best practice*: Always enable unless you have specific reason not to

### Complete Configuration Examples

**Employee Payroll Setup**:
```
Address: 0xEmployee...
Period: 30 days (216,000 blocks)
Unit Limits:
  - Per Tx: 5,000 USDC
  - Per Period: 5,000 USDC
  - Lifetime: 60,000 USDC (1 year)
USD Limits:
  - Per Tx: $5,000
  - Per Period: $5,000
  - Lifetime: $60,000
Timing:
  - Max Txs/Period: 2 (bi-weekly pay)
  - Cooldown: 10 days (prevent double-pay)
Assets:
  - Primary: USDC
  - Only Primary: Yes
  - Fail on Zero: Yes
```

**Vendor Payment Setup**:
```
Address: 0xVendor...
Period: 7 days
Unit Limits: None (0 = unlimited)
USD Limits:
  - Per Tx: $2,000
  - Per Period: $8,000
  - Lifetime: $100,000
Timing:
  - Max Txs/Period: 10
  - Cooldown: 1 hour
Assets:
  - Primary: USDC
  - Only Primary: No (accepts any token)
  - Fail on Zero: Yes
```

**Subscription Service (Pull Payment)**:
```
Address: 0xNetflix...
Period: 30 days
Unit Limits:
  - Per Tx: 20 USDC
  - Per Period: 20 USDC
  - Lifetime: 240 USDC (1 year)
USD Limits:
  - Per Tx: $20
  - Per Period: $20
  - Lifetime: $240
Timing:
  - Max Txs/Period: 1
  - Cooldown: 25 days
Assets:
  - Primary: USDC
  - Only Primary: Yes
  - Fail on Zero: Yes
Pull Payment: Enabled
```

This comprehensive control system ensures your automated payments are just as safe—if not safer—than manual transactions, with every parameter tuned to your specific needs.