## The Cheque Lifecycle

Every Cheque follows a transparent four-stage journey, with clear rules at each step. Understanding this lifecycle helps you use Cheques effectively for different scenarios.

### Stage 1: Creation

When you "write" a Cheque, you're creating a payment promise without moving any funds yet.

**What you specify**:
- Recipient address
- Token and amount
- Unlock time (when it becomes cashable)
- Expiry time (when it becomes void)
- Optional: Pull permission, Manager payment permission

**Real example**: 
Freelancer completes work on Monday. Client creates:
- $5,000 USDC cheque
- Unlocks: Friday (3-day review period)
- Expires: 30 days later (standard terms)
- Pull enabled: Freelancer can claim when ready

### Stage 2: Time-locked (Pending)

The security waiting period before a Cheque can be cashed.

**Duration depends on**:
- Your instant threshold setting
- The cheque amount
- Custom unlock time you set

**Examples**:
- $500 cheque with $1,000 threshold → No delay, immediately active
- $10,000 cheque with $1,000 threshold → 7-day automatic delay
- Any amount with custom future date → Waits until that date

**What happens**: 
- Cheque is visible on-chain
- Recipient sees the commitment
- You can still cancel if needed
- No funds have moved

### Stage 3: Active (Unlocked)

The Cheque is now "live" and can be cashed.

**Payment options**:
1. **Push Payment**: You or your Manager executes the payment
2. **Pull Payment**: Recipient claims it themselves (if enabled)

**Real scenarios**:
- Landlord pulls rent payment on the 1st
- You pay contractor after final approval
- AI Manager pays approved invoices automatically

**Important**: The Cheque stays active until paid or expired. There's no rush if everyone's happy with the timeline.

### Stage 4: Finalized

Every Cheque eventually reaches one of two final states:

#### Successfully Paid
- Funds transfer to recipient
- USD value at payment recorded
- Cheque marked as inactive
- Cannot be paid again

#### Expired
- Expiry block reached without payment
- Cheque becomes void
- Cannot be cashed anymore
- Funds never left your wallet

### Practical Timeline Examples

**Immediate Small Payment**:
- Create: $200 cheque at block 1000
- Active: Immediately (under threshold)
- Paid: Block 1001
- Total time: 2 blocks (≈20 seconds)

**Standard Invoice**:
- Create: $3,000 cheque Monday 9am
- Time-locked: 3 days (review period)
- Active: Thursday 9am
- Expires: 30 days from creation
- Paid: Following Monday (recipient's choice)

**High-Value Transfer**:
- Create: $50,000 cheque
- Time-locked: 7 days (automatic delay)
- Active: Week later
- Owner reviews and pays manually
- Or cancels if something seems wrong

### Why This Lifecycle Matters

Each stage serves a purpose:
- **Creation** establishes commitment without risk
- **Time-lock** provides security and review time
- **Active** period offers payment flexibility
- **Finalization** ensures clean resolution

The beauty is that you maintain control until the moment of payment, while recipients have transparency about when and how they'll be paid. It's the trust of traditional banking with the efficiency of blockchain.