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

| Use Case | Delay | Blocks (Ethereum) | Why |
|----------|-------|-------------------|-----|
| High-value vendor | 7 days | ~50,400 | Maximum security for large payments |
| New employee | 3 days | ~21,600 | Balance of security and onboarding |
| Trusted family | 1 day | ~7,200 | Quick access for emergencies |
| Existing partner | 1 hour | ~300 | Minimal delay for known entities |

*Security benefit*: Cancel if something seems wrong before activation

#### Activation Length (`activationLength`)
How long the Payee remains active before automatic expiry.

| Payee Type | Duration | Use Case |
|------------|----------|----------|
| Full-time employee | 365 days | Annual review cycle |
| Contractor | 90 days | Project duration |
| Subscription service | 30 days | Monthly renewal |
| One-time vendor | 7 days | Single transaction |

*Auto-expiry*: Forces regular review of payment relationships

#### Payee State Flow
```
Added → Pending → Active → Expired/Removed
  │        │         │          │
  └────────┴─────────┴──────────┴─→ Can be removed at any time
           │         │
           │         └─→ Payments allowed
           │
           └─→ Security delay period
```

### Who Can Manage Payees

Clear hierarchy ensures security while enabling flexibility:

```
┌─────────────────────────────────────────────┐
│                   OWNER                     │
│         (Complete Control)                  │
│  • Add Payees directly                      │
│  • Update all settings                      │
│  • Remove instantly                         │
└────────────────┬────────────────────────────┘
                 │
┌────────────────┼────────────────────────────┐
│            MANAGERS                         │
│    (Limited Proposal Rights)                │
│  • Propose new Payees                       │
│  • Cannot modify/remove                     │
│  • Requires owner confirmation              │
└────────────────┬────────────────────────────┘
                 │
┌────────────────┴────────────────────────────┐
│         PAYEE & SECURITY                    │
│      (Self-Service & Emergency)             │
│  • Payee: Self-removal only                │
│  • Security: Emergency removal              │
└─────────────────────────────────────────────┘
```

#### The Owner (You)
* Add new Payees with configurable delay (e.g., 3-day security buffer)
* Update any Payee's settings immediately
* Remove any Payee instantly
* Confirm or reject Manager proposals

#### Managers
* Can propose new Payees through two-tier process
* Creates pending entry with time-lock
* Owner must confirm after delay expires
* Useful for: HR proposing new $5,000/month employee

#### The Payee
* Can remove themselves (self-service offboarding)
* Cannot modify their own limits
* Cannot add other Payees
* Example: Contractor finishing project removes access

#### Security Team (MissionControl)
* Emergency removal rights only
* Cannot add or modify
* Last resort for compromised accounts

### Manager-Proposed Payee Workflow

When a Manager proposes a new Payee:

```
1. Manager Proposes          2. Time-Lock Period         3. Owner Reviews
   "Add vendor for           Wait 3 days                 Check details
    $2k/month supplies"      (security buffer)           Confirm/Cancel
         │                           │                          │
         └───────────────────────────┴──────────────────────────┘
                          Cannot bypass delay
```

**Example Flow**:
- Day 1: HR Manager proposes new contractor ($3,000/month limit)
- Day 1-3: Pending period (owner can review and cancel)
- Day 4: Owner confirms → Contractor becomes active Payee
- Alternative: Owner cancels → Proposal rejected

### Practical Administration Tips

**For Businesses**:
- Set conservative global defaults ($1,000 per tx, $10,000 per month)
- Customize for each relationship (employee: $10k/mo, vendor: $5k/mo)
- Use 7-day delays for vendors handling >$10,000
- Review all Payees quarterly

**For Personal Use**:
- Global limit: $500 per transaction
- Family emergency fund: $5,000 lifetime cap
- Subscription services: $100/month with 30-day periods
- Clean up expired Payees monthly

**Security Best Practices**:
- Minimum 24-hour delay for all new Payees
- Set activation length to force reviews (90-365 days)
- Start with $1,000 limit, increase after trust established
- Name Payees clearly: "John Doe - Contractor - Marketing"

### Troubleshooting Common Issues

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
| "Cannot add Payee" | Address already whitelisted | Check whitelist, remove if needed |
| "Payment to Payee failed" | Payee expired or not yet active | Check activation/expiry dates |
| "Manager can't propose" | Missing permission or inactive | Verify Manager has `canAddPendingPayee` |
| "Pending Payee stuck" | Time-lock not expired | Wait for delay period to complete |
| "Can't remove Payee" | Wrong permission level | Only owner, payee, or security can remove |

### Quick Checks

**Is Payee Active?**
- Current block > startBlock? ✓
- Current block < expiryBlock? ✓
- Both must be true

**Why Did Payment Fail?**
1. Check Payee is active (not expired)
2. Verify within transaction limits
3. Confirm period limits not exceeded
4. Check cooldown period passed
5. Verify correct token if restricted

The administration system balances convenience with security, ensuring you're always in control while automating the routine work.