## Administration & Advanced Features

Cheques offer powerful features beyond basic payments, enabling sophisticated payment workflows while maintaining security.

### Advanced Payment Features

### Pull Payments (`canBePulled`)
Transform Cheques into claimable payments that recipients control.

**Double-Flag Requirement**:
```
Global Setting            AND    Individual Cheque
canBePulled: true               canBePulled: true
       ↓                              ↓
       └──────────┬───────────────────┘
                  │
           Pull Payment Works
```

**How it works**:
- You create a Cheque with pull permission
- Recipient sees it's ready on their schedule
- They claim payment when convenient
- No more "the check is in the mail" excuses

**Perfect for**:
- Freelancers who want control over payment timing
- Landlords collecting rent ($2,500/month)
- Services that batch process payments
- Anyone who prefers to pull rather than wait

Real example: 
A contractor completes work and receives a pull-enabled Cheque for $5,000:
- Claim immediately if they need funds
- Wait until month-end for tax purposes  
- Batch multiple client payments together
- Funds earn 5% APY until claimed (~$20/month)

### Manager Payments (`canManagerPay`)
Delegate payment execution without giving full access.

**Use cases**:
- AI agents paying approved invoices
- Accounting team executing payroll cheques
- Automated systems processing routine payments

**How it's secure**:
- Managers can only pay existing cheques
- They cannot create new ones (unless separately authorized)
- They cannot modify amounts or recipients
- Perfect separation of duties

### Smart Fund Sourcing

Like Payees, Cheques intelligently source funds when needed:

1. **Check liquid balance** in your wallet
2. **Auto-withdraw from yield** if needed (Aave, Compound, etc.)
3. **Complete payment** seamlessly

Example: You have a $10,000 cheque to pay but only $2,000 liquid. The system automatically:
- Uses your $2,000 liquid funds
- Withdraws $8,000 from your yield positions
- Completes the payment in one transaction

### Administration Hierarchy

Clear rules about who can do what:

### Creating Cheques
**The Owner (You)**: 
- Always can create cheques
- No restrictions on amounts or settings
- Full control over all parameters

**Managers**: 
- Can create IF you enable `canManagersCreateCheques`
- Subject to the same wallet limits as you
- Perfect for delegated invoice processing

**Manager Permission Requirements**:
```
Two Conditions Must Be True:
1. Global: canManagersCreateCheques = true
2. Manager: transferPerms.canCreateCheque = true
                    ↓
           Both Required for Creation
```

**Why double permission?**: 
- Global flag: Master switch for the feature
- Per-manager flag: Individual authorization
- Prevents accidental permissions
- Maximum security for fund control

### Cancelling Cheques
**The Owner**: 
- Can cancel any cheque before it's paid
- No questions asked
- Immediate effect

**Security (MissionControl)**: 
- Emergency cancellation rights
- Protects against detected threats
- Rarely used safety net

**Recipients/Managers**: 
- Cannot cancel cheques
- Ensures payment commitments are reliable

### Practical Administration Patterns

**Solo Business Owner**:
- Create all cheques yourself
- Enable pull for trusted vendors
- Keep manager creation disabled

**Small Team**:
- You create large/important cheques
- Bookkeeper (Manager) creates routine ones
- AI agent pays approved cheques
- All within your set limits

**Automated Operations**:
- AI Manager creates cheques from invoices
- You review during time-lock period
- Another Manager or AI executes payments
- Full audit trail maintained

### Manager Cheque Creation Workflow

When a Manager creates a cheque, here's the complete flow:

```
1. Manager Attempts Creation     2. Permission Check           3. Validation
   "Create $5,000 cheque"       Global: ✓ Managers allowed    Amount: Within limits?
          │                     Manager: ✓ Has permission     Period: Under cap?
          │                              │                     Active: < max cheques?
          └──────────────────────────────┴─────────────────────┘
                                        │
                              4. Time-Lock Applied
                              $5,000 > $1,000 threshold
                              → 3-day automatic delay
                                        │
                              5. Cheque Created
                              Visible on-chain
                              Owner can review/cancel
```

### The Power of Combining Features

**Scenario**: Automated invoice processing
1. Invoice arrives → AI Manager creates cheque
2. Time delay for large amounts → You review
3. Approval → Cheque becomes active
4. Vendor pulls payment → No action needed
5. Funds sourced from yield → Maximum efficiency

**Real Numbers**:
- Invoice amount: $8,000
- Automatic delay: 3 days (exceeds $1,000 threshold)
- Yield earned during delay: ~$3.30
- Total time saved: 30 minutes per invoice
- Monthly volume: 20 invoices = 10 hours saved

### Security Best Practices

1. **Start Conservative**: Enable features as you need them
2. **Use Time Delays**: Especially for manager-created cheques  
3. **Regular Reviews**: Check active cheques periodically
4. **Clear Policies**: Document when managers should create/pay cheques
5. **Audit Trail**: All actions are recorded on-chain

These advanced features make Cheques more than just payments—they're building blocks for sophisticated financial operations that run themselves while you sleep.