## Cheque Controls & Settings

As the owner, you can configure comprehensive wallet-wide rules for all Cheques. These settings ensure your payment promises align with your risk tolerance and business needs.

### Understanding Period-Based Limits

Like Payees and Managers, Cheque limits work on a rolling period system:
- Set a period (e.g., 30 days = 216,000 blocks on Ethereum)
- Limits reset automatically each period
- Prevents both runaway spending and creation spam
- Creation and payment periods tracked independently

**Block Time Reference**:
- 1 hour ≈ 300 blocks
- 1 day ≈ 7,200 blocks
- 1 week ≈ 50,400 blocks
- 30 days ≈ 216,000 blocks

### Creation Limits

Control how many Cheques can be written:

### Max Active Cheques (`maxNumActiveCheques`)
Total number of unpaid Cheques allowed at once.
* Example: 20 active cheques maximum
* Use case: Freelancer managing multiple client invoices
* Why it matters: Prevents overcommitment of future funds

### Max Cheque USD Value (`maxChequeUsdValue`)
Largest single Cheque you can create.
* Example: $50,000 maximum per cheque
* Use case: Business with typical transactions under this amount
* Protection: Prevents accidental creation of enormous cheques

### Creation Period Controls
Limit Cheque creation within time windows:
* **Per-Period USD Cap**: e.g., $100,000 worth of cheques per month
* **Max Number Per Period**: e.g., 30 cheques per month
* **Creation Cooldown**: e.g., 100 blocks (20 minutes) between cheques

Real scenario: Prevents a compromised Manager from creating hundreds of cheques rapidly.

### Payment Limits

Control how Cheques are cashed:

### Payment Period Controls
Limit how many Cheques can be paid in a period:
* **Per-Period USD Cap**: e.g., $50,000 paid out per week
* **Max Number Per Period**: e.g., 10 cheques cashed per week  
* **Payment Cooldown**: e.g., 50 blocks (10 minutes) between payments

Why this matters: Even if you have 50 active cheques, you can control the payment velocity to manage cash flow.

### Timing Controls - Your Safety Net

### Instant USD Threshold (`instantUsdThreshold`)
The dividing line between instant and delayed cheques.
* Example: Set to $1,000
* Below $1,000: Cheques can be immediate
* Above $1,000: Automatic security delay applied
* Business use: Routine payments instant, large payments get review time

### Expensive Delay (`expensiveDelayBlocks`)
How long high-value cheques must wait.
* Example: 50,400 blocks ≈ 7 days
* Example: 7,200 blocks ≈ 24 hours for faster business
* Benefit: Time to catch errors on large payments

### Default Expiry (`defaultExpiryBlocks`)
How long cheques remain cashable after unlocking.
* Example: 216,000 blocks ≈ 30 days (standard invoice terms)
* Example: 50,400 blocks ≈ 7 days for time-sensitive payments
* Note: Can be overridden per cheque if needed

### Asset Controls

### Allowed Assets List
Restrict which tokens can be used in cheques.
* Example: Only [USDC, USDT, DAI] for stablecoin business
* Example: Only [WETH] for ETH-denominated operations
* Empty list: Allows any token (use with caution)

**Security Warning**: An empty allowed assets list means:
- Any token can be used, including volatile ones
- Potential for scam token cheques
- Best practice: Always specify trusted tokens

### Technical Constraints

The protocol enforces these validation rules:

### Timing Constraints
- **Cooldowns cannot exceed period length**: If period = 30 days, cooldown must be < 30 days
- **Minimum expensive delay**: Set by protocol deployment
- **Maximum unlock delay**: Cannot exceed protocol maximum
- **Maximum active duration**: Expiry - unlock cannot exceed limit

### Expiry Fallback Logic
```
if custom expiry provided → use it
else if default expiry set → use default
else → use wallet timeLock setting
```

### USD Cap Consistency
- Per-cheque cap cannot exceed period caps
- If maxChequeUsdValue = $10,000 and perPeriodCreatedUsdCap = $50,000
- You can create at most 5 maximum-value cheques per period

### Practical Configuration Examples

**Conservative Personal Wallet**:
```
maxNumActiveCheques: 5
maxChequeUsdValue: $10,000
instantUsdThreshold: $1,000
perPeriodCreatedUsdCap: $25,000
periodLength: 216,000 (30 days)
expensiveDelayBlocks: 21,600 (3 days)
defaultExpiryBlocks: 216,000 (30 days)
allowedAssets: [USDC, USDT, DAI]
```

**Active Business Wallet**:
```
maxNumActiveCheques: 50
maxChequeUsdValue: $100,000
instantUsdThreshold: $10,000
perPeriodCreatedUsdCap: $500,000
maxNumChequesCreatedPerPeriod: 200
periodLength: 216,000 (30 days)
expensiveDelayBlocks: 7,200 (24 hours)
defaultExpiryBlocks: 324,000 (45 days)
allowedAssets: [USDC, USDT, DAI, WETH]
canManagersCreateCheques: true
```

**High-Security Treasury**:
```
maxNumActiveCheques: 10
maxChequeUsdValue: $50,000
instantUsdThreshold: $500
perPeriodPaidUsdCap: $100,000
maxNumChequesPaidPerPeriod: 20
periodLength: 50,400 (7 days)
expensiveDelayBlocks: 50,400 (7 days)
defaultExpiryBlocks: 100,800 (14 days)
createCooldownBlocks: 300 (1 hour)
allowedAssets: [USDC]
canManagersCreateCheques: false
canBePulled: false
```

### Permission Flags

Control who can do what:
* **canManagersCreateCheques**: Allow Managers to write cheques
* **canManagerPay**: Allow Managers to execute cheque payments
* **canBePulled**: Enable recipients to pull payments themselves

Each setting balances convenience with security, letting you tailor the system to your exact needs.

### Troubleshooting Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "Cannot create cheque" | Hit active cheque limit | Check maxNumActiveCheques |
| "Cheque creation failed" | Exceeded period USD cap | Wait for period reset or increase cap |
| "Manager cannot create" | Missing permission | Check both global and manager flags |
| "Invalid cheque amount" | Exceeds maxChequeUsdValue | Reduce amount or increase limit |
| "Cooldown not met" | Too soon after last cheque | Wait for cooldown blocks |
| "Period cap exceeded" | Too many/much this period | Wait for automatic reset |
| "Asset not allowed" | Token not in allowed list | Add token or use approved one |
| "Cheque expired" | Past expiry block | Create new cheque |
| "Cannot pull payment" | Pull not enabled | Check both global and cheque flags |