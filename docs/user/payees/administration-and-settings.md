## Administration & Settings

Managing Payees is straightforward yet powerful, with multiple layers of control to ensure security.

### The Two-Layer Settings System

#### 1. Global Payee Settings
Your wallet-wide defaults that apply to all Payees. Think of these as your master controls:

* **Default period length**: Standard payment cycle (e.g., 30 days)
* **Default limits**: Baseline caps for all new Payees
* **canPayOwner**: Whether you can pay yourself without setup
* **canPull**: Master switch for pull payment functionality

*Example setup for a business*:
- Default period: 30 days (monthly)
- Default per-transaction cap: $5,000
- canPayOwner: Enabled (for moving funds between your wallets)
- canPull: Enabled (for subscriptions)

#### 2. Specific Payee Settings
Custom rules for each individual Payee that override defaults:

* **Individual limits**: Tailored to each relationship
* **Custom periods**: Weekly for contractors, monthly for employees
* **Asset restrictions**: USDC only for some, any token for others

*Example*: Your default limit is $5,000, but you set your landlord's limit to $10,000 for rent payments.

### Lifecycle Management

Payees follow a secure activation process:

#### Start Delay (`startDelay`)
Time buffer before a new Payee becomes active.
* *Example*: 3-day delay (25,920 blocks) for new vendors
* *Example*: 24-hour delay (7,200 blocks) for trusted contacts
* *Security benefit*: Gives you time to cancel if something seems wrong

#### Activation Length (`activationLength`)
How long the Payee remains active.
* *Example*: 365 days for ongoing employees
* *Example*: 90 days for project-based contractors
* *Auto-expiry*: Payee automatically deactivates after this period

### Who Can Manage Payees

Clear hierarchy ensures security while enabling flexibility:

#### The Owner (You)
* Add new Payees instantly (subject to start delay)
* Update any Payee's settings
* Remove any Payee immediately
* No restrictions on your control

#### Managers
* Can propose new Payees (requires your approval)
* Cannot modify existing Payees
* Cannot remove Payees
* Useful for: HR managers proposing new employees

#### The Payee
* Can remove themselves (self-service offboarding)
* Cannot modify their own limits
* Cannot add other Payees
* Respectful exit option

#### Security Team
* Emergency removal rights only
* Cannot add or modify
* Extra safety net for protocol security

### Practical Administration Tips

**For Businesses**:
- Set conservative global defaults
- Customize limits for each vendor/employee
- Use longer start delays for high-value Payees
- Review and update quarterly

**For Personal Use**:
- Keep global limits reasonable
- Use shorter activation periods for trials
- Enable pull only for trusted services
- Regular cleanup of unused Payees

**Security Best Practices**:
- Always use start delays (no instant activation)
- Set expiry dates to force regular reviews
- Start with small limits, increase over time
- Document Payee purposes for future reference

The administration system balances convenience with security, ensuring you're always in control while automating the routine work.