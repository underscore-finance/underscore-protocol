## Built-in Security Tools

Your wallet includes four core security components that work together to protect your assets while enabling sophisticated operations. Each tool serves a specific purpose in your security architecture.

### Managers
Delegate specific wallet operations to trusted addresses—whether human operators or AI agents—with granular permission controls and spending limits.

**Technical Implementation**:
- **Time-locked Activation**: 1-7 day security delay before new Managers become active
- **USD-based Limits**: Daily and monthly caps calculated in real-time
- **Action Permissions**: Grant specific abilities (transfer, swap, yield management)
- **Expiry Dates**: Auto-revocation after set period (30-365 days typical)

**AI Agent Integration**: 
Connect automated systems that operate within your safety parameters:

```
Example AI Agent Configuration:
- Daily USD limit: $5,000
- Monthly cap: $50,000
- Allowed actions: Yield deposits/withdrawals, token swaps
- Restricted: Cannot add new Managers or Payees
- Monitoring: 24/7 rate optimization across 10+ protocols
```

**Real Performance Metrics**:
- Typical yield improvement: 1-3% APY through active rebalancing
- Gas savings: 30-50% through batched operations
- Response time: 1-2 blocks after opportunity detection
- Security: Cryptographic signatures for every action

**Manager Templates**:

Conservative (Family Member):
- $500 daily, $2,000 monthly limit
- Transfer permissions only
- 3-day activation delay
- 6-month expiry

Active (Trading Bot):
- $10,000 daily, $100,000 monthly limit  
- Full DeFi permissions
- 1-day activation delay
- 30-day expiry with renewal

### Payees
Pre-approved addresses that can receive funds within defined limits. Unlike Managers, Payees can only receive—they cannot initiate any wallet actions.

**Dual Limit System**:
```
Token Limits              AND    USD Limits
├─ Per Transaction: 1000 USDC    ├─ Per Transaction: $1,000
├─ Per Period: 5000 USDC         ├─ Per Period: $5,000
└─ Lifetime: 50000 USDC          └─ Lifetime: $50,000

Applied Rule: The MORE restrictive limit always applies
```

**Configuration Options**:
- **Activation Delay**: 1-7 days before Payee becomes active
- **Period Length**: 7-30 days typical (customizable)
- **Token Restrictions**: Limit to specific assets (e.g., USDC only)
- **Pull Payments**: Optional ability for Payee to request payment

**Common Use Cases with Numbers**:

Employee Payroll:
- Monthly salary: $5,000 USDC
- Period: 30 days
- Max transactions: 2 per period (bi-weekly)
- Lifetime cap: $60,000 (1 year)

SaaS Subscriptions:
- Monthly limit: $100
- Pull payment: Enabled
- Token: USDC only
- Auto-expiry: 12 months

Contractor Payments:
- Per transaction: $2,500
- Weekly period: $10,000 max
- Cooldown: 24 hours between payments
- Total project cap: $50,000

### Cheques
Time-locked payment commitments that provide flexibility and control over future transfers.

**Automatic Security Delays**:
```
Amount → Delay Applied
< $1,000 → No delay (immediate unlock)
$1,000-$10,000 → 3-day delay
> $10,000 → 7-day delay
Custom delays can override these defaults
```

**Lifecycle Example**:
```
Day 1: Create $5,000 cheque → 3-day delay triggered
Day 4: Cheque unlocks → Recipient can claim
Day 34: Expires if unclaimed → Funds never left wallet
Yield earned during wait: ~$2 at 5% APY
```

**Technical Features**:
- **Max Active Cheques**: 20-50 typical limit
- **Period Limits**: e.g., $50,000/month in new cheques
- **USD Value Lock**: Amount recorded at creation time
- **Manager Creation**: Optional (with permission)

**Use Case Examples**:

Invoice Payment:
- Amount: $3,000 USDC
- Unlock: 3 days (review period)
- Expiry: 30 days (net terms)
- Benefit: Can cancel if work unsatisfactory

Rent Payment:
- Amount: $2,500 USDC
- Created: 25th of month
- Unlocks: 1st of next month
- Pull enabled: Landlord claims when ready

### The Whitelist
Trusted addresses with unlimited transfer permissions—your highest security tier.

**Key Properties**:
- **No Limits**: Bypass all USD caps and restrictions
- **Instant Transfers**: No delays or cooldowns
- **Time-locked Addition**: 3-7 day security delay to add
- **Instant Removal**: Can remove immediately if compromised

**Typical Whitelist**:
```
1. Your hardware wallet
2. Your secondary wallet
3. Company treasury (if business)
4. Emergency backup address
Total addresses: 2-5 maximum recommended
```

**Security Model**:
- Adding requires owner signature + time delay
- Managers cannot be whitelisted
- Whitelist addresses cannot be Payees
- Each address must be explicitly trusted

### Emergency Features

Your wallet includes fail-safe mechanisms for critical situations:

**Wallet Freeze**:
- Instantly stops ALL operations
- Only owner or security team can trigger
- Reversible by owner only
- Use case: Suspected compromise

**Eject Mode**:
- Emergency withdrawal-only mode
- Disables all DeFi operations
- Allows only transfers and ETH/WETH conversion
- Cannot be enabled with trial funds

**NFT Recovery**:
- Retrieve accidentally sent NFTs
- Owner-only function
- Works for any ERC-721 token

**Trial Fund Protection**:
- Special handling for promotional funds
- Auto-clawback if conditions not met
- Prevents gaming of incentive programs