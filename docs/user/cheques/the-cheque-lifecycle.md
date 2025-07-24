## The Cheque Lifecycle

Every Cheque follows a transparent four-stage journey, with clear rules at each step. Understanding this lifecycle helps you use Cheques effectively for different scenarios.

### Lifecycle Visualization

```
Creation → Time-locked → Active → Finalized (Paid/Expired)
   │           │           │           │
   ├───────────┴───────────┴───────────┤
   │     Can Cancel Anytime Until Paid │
   └───────────────────────────────────┘
               │           │
               │           └─→ Payment Period
               │               - Owner can pay
               │               - Manager can pay (if allowed)
               │               - Recipient can pull (if allowed)
               │
               └─→ Security Review Period
                   - Automatic for large amounts
                   - Custom for future dating
```

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

**Duration Formula**:
```
Unlock Time = MAX(
    User-specified delay,
    Automatic expensive delay (if amount > threshold)
)
```

**Real Examples**:
| Cheque Amount | Instant Threshold | User Delay | Actual Delay | Reason |
|---------------|-------------------|------------|--------------|---------|
| $500 | $1,000 | 0 blocks | 0 blocks | Under threshold |
| $2,000 | $1,000 | 0 blocks | 21,600 blocks (3 days) | Auto-delay triggered |
| $500 | $1,000 | 7,200 blocks | 7,200 blocks (1 day) | User preference |
| $10,000 | $5,000 | 3,600 blocks | 50,400 blocks (7 days) | Expensive delay override |

**What happens during time-lock**: 
- Cheque is visible on-chain (transparency)
- Recipient sees the commitment
- USD value locked at creation price
- You can cancel anytime
- No funds have moved
- Funds continue earning yield

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
```
Create: $200 USDC cheque at block 1000
Settings: $1,000 instant threshold
Time-locked: None (under threshold)
Active: Block 1000 (immediate)
Paid: Block 1001 
Total time: 1 block (≈12 seconds)
Yield earned: Negligible
```

**Standard Invoice (Net 30)**:
```
Create: $3,000 USDC cheque Monday 9am (block 100,000)
Settings: $1,000 instant threshold, 3-day expensive delay
Time-locked: 21,600 blocks (auto-triggered)
Active: Thursday 9am (block 121,600)
Expires: Block 316,000 (30 days from creation)
Paid: Following Monday (block 150,000)
Yield earned: ~$2.50 over 8 days at 5% APY
```

**High-Value Contract Payment**:
```
Create: $50,000 USDC cheque (block 200,000)
Settings: $5,000 threshold, 7-day expensive delay
Time-locked: 50,400 blocks (automatic)
Active: Block 250,400 (week later)
Expires: Block 466,400 (30 days after unlock)
Review period benefit: Time to verify deliverables
Yield earned: ~$48 during 7-day delay at 5% APY
```

**Future-Dated Rent Payment**:
```
Create: $2,500 USDC cheque on 25th (block 300,000)
Custom unlock: 6 days (to reach 1st of month)
Time-locked: 43,200 blocks 
Active: 1st of month (block 343,200)
Pull enabled: Landlord claims when convenient
Expiry: 45 days total (standard terms)
```

### Why This Lifecycle Matters

Each stage serves a purpose:
- **Creation** establishes commitment without risk
- **Time-lock** provides security and review time
- **Active** period offers payment flexibility
- **Finalization** ensures clean resolution

The beauty is that you maintain control until the moment of payment, while recipients have transparency about when and how they'll be paid. It's the trust of traditional banking with the efficiency of blockchain.