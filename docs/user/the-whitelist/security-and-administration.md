## Security Process & Administration

The Whitelist's power requires equally strong security measures. Every addition follows a careful process designed to prevent both accidents and attacks.

### The Two-Step Security Process

Adding an address to the whitelist is never instant. Here's how it works:

#### Step 1: Propose an Address
Submit the address you want to whitelist. This creates a pending entry and starts the security countdown.

*Example timeline*:
- Monday 2pm: You propose your hardware wallet address
- System records: Block 18,945,000, pending until block 18,995,400

#### Step 2: Mandatory Time-Lock
A security delay prevents immediate additions, giving you time to detect and stop unauthorized attempts.

*Typical delays*:
- **3 days** (25,920 blocks): Common for personal wallets
- **7 days** (60,480 blocks): Often used for high-value wallets
- Your specific delay is set in your wallet configuration

*Security feature*: If the wallet owner changes during this waiting period, all pending whitelist proposals are automatically cancelled. This prevents an attacker who gains temporary control from adding their own addresses.

#### Step 3: Confirm the Addition
After the time-lock expires, you must send a second transaction to complete the whitelisting.

*Example completion*:
- Thursday 2pm: Time-lock expired
- You confirm: Hardware wallet now whitelisted
- Can immediately transfer any amount

### Administration Hierarchy

Clear rules govern who can manage your whitelist:

#### The Owner (You)
Complete control over all whitelist operations:
- Propose new addresses
- Confirm after time-lock
- Cancel pending proposals
- Remove existing addresses
- No restrictions on your authority

#### Managers
Can be granted specific whitelist permissions:
- **canAddPending**: Propose new addresses
- **canConfirm**: Confirm after time-lock expires
- **canCancel**: Cancel pending proposals  
- **canRemove**: Remove whitelisted addresses

*Note*: These follow the dual-permission system—both global and specific manager settings must allow the action.

*Common pattern*: Grant your accountant `canAddPending` but not `canConfirm`, requiring your final approval for all additions.

#### Security Override (MissionControl)
Protocol-level emergency powers (rarely used):
- Cancel suspicious pending proposals
- Remove addresses in security emergencies
- Cannot add new addresses
- Acts as a safety net

### Practical Administration Examples

#### Solo User Setup
- You propose and confirm all addresses
- 3-day time-lock for security
- No manager permissions needed

#### Family Wallet
- You and spouse can both propose
- Either can confirm after delay
- Both can cancel if something seems wrong

#### Business Treasury
- CFO can propose new addresses
- CEO must confirm additions
- Security team can cancel suspicious proposals
- Clear separation of duties

### Security Best Practices

1. **Choose Appropriate Time-Locks**
   - Longer delays for higher-value wallets
   - Shorter (but never instant) for frequently-used operations

2. **Limited Manager Permissions**
   - Don't grant all whitelist permissions to one manager
   - Require owner confirmation for additions

3. **Regular Audits**
   - Review whitelist quarterly
   - Remove addresses no longer needed
   - Document why each address is trusted

4. **Test Before Trusting**
   - Send small amount first
   - Verify you control the address
   - Then whitelist for large transfers

5. **Emergency Planning**
   - Know how to quickly remove addresses
   - Have a process for security incidents
   - Keep whitelist as small as practical

### Common Questions

**Q: Can I speed up the time-lock?**
A: No. The delay is non-skippable for security. Plan additions in advance.

**Q: What if I need emergency access?**
A: That's why you whitelist emergency addresses in advance, during calm times.

**Q: Can removed addresses be re-added?**
A: Yes, but they must go through the full proposal process again.

**Q: How many addresses can I whitelist?**
A: No hard limit, but keep it minimal for security. Most users need 2-5 addresses.

The whitelist security process may seem strict, but it's designed to protect your assets while still enabling the flexibility you need for legitimate operations.