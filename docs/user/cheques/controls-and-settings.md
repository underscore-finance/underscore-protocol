## Cheque Controls & Settings

As the owner, you can configure comprehensive wallet-wide rules for all Cheques. These settings ensure your payment promises align with your risk tolerance and business needs.

### Understanding Period-Based Limits

Like Payees and Managers, Cheque limits work on a rolling period system:
- Set a period (e.g., 30 days)
- Limits reset automatically each period
- Prevents both runaway spending and creation spam

### Creation Limits

Control how many Cheques can be written:

#### Max Active Cheques (`maxNumActiveCheques`)
Total number of unpaid Cheques allowed at once.
* *Example*: 20 active cheques maximum
* *Use case*: Freelancer managing multiple client invoices
* *Why it matters*: Prevents overcommitment of future funds

#### Max Cheque USD Value (`maxChequeUsdValue`)
Largest single Cheque you can create.
* *Example*: $50,000 maximum per cheque
* *Use case*: Business with typical transactions under this amount
* *Protection*: Prevents accidental creation of enormous cheques

#### Creation Period Controls
Limit Cheque creation within time windows:
* **Per-Period USD Cap**: e.g., $100,000 worth of cheques per month
* **Max Number Per Period**: e.g., 30 cheques per month
* **Creation Cooldown**: e.g., 100 blocks (20 minutes) between cheques

*Real scenario*: Prevents a compromised Manager from creating hundreds of cheques rapidly.

### Payment Limits

Control how Cheques are cashed:

#### Payment Period Controls
Limit how many Cheques can be paid in a period:
* **Per-Period USD Cap**: e.g., $50,000 paid out per week
* **Max Number Per Period**: e.g., 10 cheques cashed per week  
* **Payment Cooldown**: e.g., 50 blocks (10 minutes) between payments

*Why this matters*: Even if you have 50 active cheques, you can control the payment velocity to manage cash flow.

### Timing Controls - Your Safety Net

#### Instant USD Threshold (`instantUsdThreshold`)
The dividing line between instant and delayed cheques.
* *Example*: Set to $1,000
* Below $1,000: Cheques can be immediate
* Above $1,000: Automatic security delay applied
* *Business use*: Routine payments instant, large payments get review time

#### Expensive Delay (`expensiveDelayBlocks`)
How long high-value cheques must wait.
* *Example*: 50,400 blocks ≈ 7 days
* *Example*: 7,200 blocks ≈ 24 hours for faster business
* *Benefit*: Time to catch errors on large payments

#### Default Expiry (`defaultExpiryBlocks`)
How long cheques remain cashable after unlocking.
* *Example*: 216,000 blocks ≈ 30 days (standard invoice terms)
* *Example*: 50,400 blocks ≈ 7 days for time-sensitive payments
* *Note*: Can be overridden per cheque if needed

### Asset Controls

#### Allowed Assets List
Restrict which tokens can be used in cheques.
* *Example*: Only [USDC, USDT, DAI] for stablecoin business
* *Example*: Only [WETH] for ETH-denominated operations
* *Empty list*: Allows any token (use with caution)

### Practical Configuration Examples

**Conservative Personal Wallet**:
- Max 5 active cheques
- $5,000 instant threshold
- 3-day delay for large amounts
- 30-day default expiry
- Only stablecoins allowed

**Active Business Wallet**:
- Max 50 active cheques
- $10,000 instant threshold  
- 24-hour delay for large amounts
- 45-day default expiry (net terms)
- Multiple tokens allowed

**High-Security Treasury**:
- Max 10 active cheques
- $500 instant threshold
- 7-day delay for anything above
- 14-day expiry (short validity)
- Only USDC allowed

### Permission Flags

Control who can do what:
* **canManagersCreateCheques**: Allow Managers to write cheques
* **canManagerPay**: Allow Managers to execute cheque payments
* **canBePulled**: Enable recipients to pull payments themselves

Each setting balances convenience with security, letting you tailor the system to your exact needs.