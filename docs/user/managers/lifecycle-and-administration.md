## Lifecycle & Administration

### Lifecycle Management

Managers follow a carefully designed lifecycle that balances security with flexibility:

#### Time-locked Activation
When a Manager is added, a `startDelay` enforces a waiting period before their permissions become active.

| Use Case | Delay Period | Blocks (Ethereum) | Why |
|----------|--------------|-------------------|-----|
| High-value Manager | 7 days | ~50,400 | Maximum security for large portfolios |
| Trusted Family | 24 hours | ~7,200 | Balance of security and accessibility |
| Emergency Access | 1 hour | ~300 | Quick response for urgent situations |
| Professional Service | 3 days | ~21,600 | Time to verify credentials |

*Why it matters*: Gives you time to verify the addition and cancel if suspicious

#### Activation & Expiry
You set an `activationLength` that determines the duration of the Manager's term.

| Manager Type | Duration | Blocks | Use Case |
|--------------|----------|--------|----------|
| Trial Period | 30 days | ~216,000 | Test new AI services |
| Quarterly Review | 90 days | ~648,000 | Business operations |
| Annual Partner | 365 days | ~2,628,000 | Long-term relationships |
| Emergency Access | 7 days | ~50,400 | Temporary assistance |

*After expiry*: The Manager automatically loses all permissions—no action needed

#### Manager State Transitions

```
    Added → Waiting → Active → Expired
      │        │         │        │
      └────────┴─────────┴────────┴─→ Can be Removed at any time
               │         │
               │         └─→ Can be Extended (resets expiry)
               │
               └─→ Can be Cancelled before activation
```

#### Adjusting Activation Length
As the owner, you can extend a Manager's term at any time with the `adjustManagerActivationLength` function.
* *Use case*: Extend a performing AI agent's term before it expires
* *Use case*: Give a family member emergency access for another month

#### Updating Settings
You can update a Manager's permissions and limits at any time. However, the `updateManager` function cannot change the original `startBlock` or `expiryBlock`.
* *Example*: Increase spending limits for a Manager who's proven trustworthy
* *Example*: Add new permissions as your needs evolve
* *Example*: Restrict permissions if you notice concerning behavior

### Manager Administration

The protocol has a clear **Permission Hierarchy** for managing your Managers.

```
┌─────────────────────────────────────────────┐
│                   OWNER                     │
│         (Complete Control)                  │
│  • Add/Update/Remove any Manager           │
│  • Modify all settings & limits            │
│  • Extend activation periods               │
└────────────────┬────────────────────────────┘
                 │
┌────────────────┼────────────────────────────┐
│             MANAGER                         │
│        (Limited Control)                    │
│  • Self-removal only                       │
│  • Cannot modify permissions               │
│  • Cannot add other Managers               │
└────────────────┬────────────────────────────┘
                 │
┌────────────────┴────────────────────────────┐
│         MISSIONCONTROL                      │
│      (Emergency Override)                   │
│  • Remove Managers only                    │
│  • Cannot add or modify                    │
└─────────────────────────────────────────────┘
```

#### Who Can Do What

**The Owner (You)**: 
* Add new Managers with custom permissions
* Update any Manager's settings and limits
* Remove any Manager instantly
* Extend activation periods
* Your power is absolute—you always have the final say

**The Manager**: 
* Can only remove themselves (self-revocation)
* Cannot modify their own permissions
* Cannot add other Managers
* This prevents compromised Managers from expanding their access

**Security (MissionControl)**: 
* Can remove Managers in emergencies
* Acts as a safety net if malicious behavior is detected
* Cannot add Managers or change permissions
* Think of this as the protocol's emergency brake

#### The Starter Agent

New wallets can come with a **Starter Agent** that has **immediate activation** (no start delay).
* *Purpose*: Helps new users explore wallet capabilities right away
* *Limited permissions*: Usually restricted to basic operations
* *Removable*: You can remove it anytime once you're comfortable
* *Example use*: A demo agent that shows you how yield optimization works

### Troubleshooting Common Issues

#### "Why isn't my Manager working?"

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
| Manager can't execute actions | Still in waiting period | Check `startBlock` - wait for activation |
| Actions suddenly stop working | Manager expired | Extend activation length or add new Manager |
| Transaction fails with "no perms" | Missing specific permission | Review and update Manager permissions |
| USD limit errors | Exceeded period/lifetime caps | Wait for period reset or increase limits |

#### Quick Diagnostic Checklist

1. **Check Manager Status**
   - Is current block > startBlock? (Manager active)
   - Is current block < expiryBlock? (Not expired)
   
2. **Verify Permissions**
   - Does Manager have the specific action permission?
   - Is the asset in their allowedAssets list?
   - Is the protocol/lego in their allowedLegos list?

3. **Review Limits**
   - Transaction value within per-tx limit?
   - Period USD cap not exceeded?
   - Sufficient cooldown since last transaction?

4. **Global Settings**
   - Is `canOwnerManage` enabled if you're the owner?
   - Do global settings allow this action type?

#### Emergency Actions

If you suspect compromised Manager activity:
1. **Immediate**: Call `removeManager()` - instant revocation
2. **If unable**: MissionControl can emergency remove
3. **Prevention**: Set conservative limits and short activation periods for new Managers