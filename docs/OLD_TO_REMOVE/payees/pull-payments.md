## Pull Payments

Pull payments transform how you handle recurring charges and subscriptions. Instead of remembering to send payments, authorized services can request payment when due—within the strict limits you've set.

### The Game-Changing Difference

**Traditional Subscriptions**: 
* Credit card on file with full access to your bank account
* Cancel by calling customer service during business hours
* Charges can increase without your explicit approval

**Underscore Pull Payments**: 
* Service can only pull what you've authorized
* Cancel instantly with one transaction
* Price increases blocked by your preset limits

### How Pull Payments Work

1. **Service requests payment** when their subscription fee is due
2. **Smart contract checks** your rules and limits
3. **Automatic sourcing** pulls from yield if needed
4. **Payment completes** without any action from you

### The Yield Advantage

Here's where it gets interesting. When a Pull Payee requests payment:

```
Your Wallet Status:
├─ Liquid USDC: $100
└─ Aave USDC: $5,000 (earning 5% APY)

Pull Request: $500 subscription payment
                ↓
System automatically:
1. Takes $100 liquid USDC
2. Withdraws $400 from Aave
3. Sends $500 to payee
4. Leaves $4,600 earning yield

Monthly benefit: $20 extra income from yield on subscription funds
```

**Real Numbers Comparison**:
* Traditional: $6,000 yearly subscriptions sitting idle = $0 earned
* Underscore: Same $6,000 earning 5% until needed = $300 extra per year
* That's a free month of subscriptions from yield alone!

### Security Requirements

Pull payments have strict safety requirements enforced by smart contracts:

### Double Activation Required
```
Global Settings              AND    Specific Payee Settings
canPull: true                       canPull: true
     ↓                                   ↓
     └─────────────┬─────────────────────┘
                   │
            Pull Payments Work

If either is false → Pull payments blocked
```

**Why double activation?** Prevents accidental enablement and gives you two control points

### Mandatory Financial Limits
Pull Payees MUST have at least one type of limit:

| Configuration | Valid? | Why |
|---------------|---------|-----|
| Only USD limits ($50/month) | ✓ | Protected by dollar value |
| Only unit limits (50 USDC/month) | ✓ | Protected by token amount |
| Both USD and unit limits | ✓ | Double protection |
| No limits set | ✗ | System blocks - no unlimited access |

**Example**: Netflix-style service
* Unit limit: 20 USDC per month
* USD limit: $25 per month  
* Result: Protected even if USDC depegs

### Best Practices
* Start with small limits and increase as you build trust
* Use period caps for subscriptions (e.g., $50/month)
* Set lifetime caps for project-based services
* Enable `failOnZeroPrice` for extra protection

### Perfect Use Cases

**Monthly Subscriptions** ($50-500/month typical)
```
Example: Business SaaS Suite
* QuickBooks: $30/month
* Slack: $100/month  
* AWS: $200/month (capped)
* Total: $330/month in subscriptions

Configuration:
* Period: 30 days
* USD limit: $50-200 per service
* Pull enabled individually
* Saves: ~$15/month in yield
```

**Usage-Based Services** (Variable but capped)
```
Example: OpenAI API
* Average use: $50-100/month
* Spike protection: $500 cap
* Period: 30 days
* Cooldown: 25 days
* Only USDC accepted
Result: Never worry about runaway API costs
```

**DAO Contributions** (Supporting ecosystem)
```
Example: Protocol supporter
* Gitcoin: $100/month
* Local DAO: $50/month
* Dev fund: $25/week
* All pull automatically
* Cancel = remove payee
Benefit: "Set and forget" supporting builders
```

### Practical Pull Payment Setups

**Streaming Service Bundle**:
```
Netflix: $20/mo → Pull enabled, 30-day period
Spotify: $15/mo → Pull enabled, 30-day period  
YouTube: $25/mo → Pull enabled, 30-day period
Total: $60/mo earning yield until needed
Annual yield benefit: ~$36
```

**Business Operations**:
```
Payroll service: $500/mo → Pull enabled, strict limits
Accounting: $200/mo → Pull enabled, USDC only
Cloud hosting: $1,000/mo → Pull enabled, $1,500 cap
All funds earn ~5% APY until pulled
Monthly benefit: ~$85 from yield
```

### Quick Setup Checklist

✓ Enable `canPull` in global settings  
✓ Add service as Payee with pull enabled  
✓ Set appropriate period (usually 30 days)  
✓ Configure USD/unit limits  
✓ Set max 1 transaction per period  
✓ Add 25+ day cooldown (prevent double-charge)  
✓ Restrict to stablecoins only  
✓ Enable failOnZeroPrice  

Pull payments combine the convenience of traditional subscriptions with the security and control of self-custody. Your funds work for you until the moment they're needed—earning yield 24/7 while still meeting all payment obligations automatically.