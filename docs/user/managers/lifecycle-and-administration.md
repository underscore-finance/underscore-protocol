## Lifecycle & Administration

### Lifecycle Management

Managers follow a carefully designed lifecycle that balances security with flexibility:

#### Time-locked Activation
When a Manager is added, a `startDelay` enforces a waiting period before their permissions become active.
* *Example*: 7-day delay (50,400 blocks) for high-value managers
* *Example*: 24-hour delay (7,200 blocks) for trusted family members
* *Why it matters*: Gives you time to verify the addition and cancel if something seems wrong

#### Activation & Expiry
You set an `activationLength` that determines the duration of the Manager's term.
* *Example*: 30 days (216,000 blocks) for a trial period with a new AI service
* *Example*: 365 days (2,628,000 blocks) for a trusted business partner
* *After expiry*: The Manager automatically loses all permissions—no action needed

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

#### Who Can Do What

**The Owner (You)**: 
* Add new Managers with custom permissions
* Update any Manager's settings and limits
* Remove any Manager instantly
* Extend activation periods
* *Your power is absolute—you always have the final say*

**The Manager**: 
* Can only remove themselves (self-revocation)
* Cannot modify their own permissions
* Cannot add other Managers
* *This prevents compromised Managers from expanding their access*

**Security (MissionControl)**: 
* Can remove Managers in emergencies
* Acts as a safety net if malicious behavior is detected
* Cannot add Managers or change permissions
* *Think of this as the protocol's emergency brake*

#### The Starter Agent

New wallets can come with a **Starter Agent** that has **immediate activation** (no start delay).
* *Purpose*: Helps new users explore wallet capabilities right away
* *Limited permissions*: Usually restricted to basic operations
* *Removable*: You can remove it anytime once you're comfortable
* *Example use*: A demo agent that shows you how yield optimization works