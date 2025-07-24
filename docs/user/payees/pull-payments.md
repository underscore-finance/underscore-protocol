## Pull Payments

Pull payments transform how you handle recurring charges and subscriptions. Instead of remembering to send payments, authorized services can request payment when due—within the strict limits you've set.

### The Game-Changing Difference

**Traditional Subscriptions**: 
- Credit card on file with full access to your bank account
- Cancel by calling customer service during business hours
- Charges can increase without your explicit approval

**Underscore Pull Payments**: 
- Service can only pull what you've authorized
- Cancel instantly with one transaction
- Price increases blocked by your preset limits

### How Pull Payments Work

1. **Service requests payment** when their subscription fee is due
2. **Smart contract checks** your rules and limits
3. **Automatic sourcing** pulls from yield if needed
4. **Payment completes** without any action from you

### The Yield Advantage

Here's where it gets interesting. When a Pull Payee requests payment:

1. **First**: System checks your wallet's liquid balance
2. **If insufficient**: Automatically withdraws from your yield positions (Aave, Compound, etc.)
3. **Result**: Payment succeeds without you keeping idle funds

*Real example*: You have $100 in liquid USDC and $5,000 earning 8% in Aave. When your $500 monthly subscription is due, the system automatically:
- Uses your $100 liquid USDC
- Withdraws $400 from Aave
- Completes the payment
- Your remaining $4,600 keeps earning yield

### Security Requirements

Pull payments have strict safety requirements:

#### Double Activation Required
- Must be enabled in global settings AND for specific Payee
- Prevents accidental authorization

#### Mandatory Limits
- Every Pull Payee MUST have financial limits set
- No unlimited access, ever
- System enforces this—no limits, no pull access

#### Best Practices
* Start with small limits and increase as you build trust
* Use period caps for subscriptions (e.g., $50/month)
* Set lifetime caps for project-based services
* Enable `failOnZeroPrice` for extra protection

### Perfect Use Cases

**Monthly Subscriptions**: SaaS tools, streaming services, protocol fees
- Set monthly period cap matching subscription price
- Service pulls payment on their billing date
- Cancel anytime by removing pull permission

**Usage-Based Services**: Cloud computing, API calls, data services  
- Set reasonable monthly maximum
- Service pulls actual usage amount
- Protected from bill shock by your cap

**DAO Contributions**: Regular donations, membership fees
- Support projects without manual transfers
- Maintain transparency with on-chain limits
- Stop anytime you want

Pull payments combine the convenience of traditional subscriptions with the security and control of self-custody. Your funds work for you until the moment they're needed.