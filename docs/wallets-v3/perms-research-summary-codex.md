# Wallet v3 Permissions Research Synthesis — Codex

**Status:** Supporting architecture synthesis and owner-decision input; not a
replacement for the governing architecture and not implementation
authorization

**Governing architecture:**
[`simplified-user-wallet-action-architecture-codex.md`](simplified-user-wallet-action-architecture-codex.md)

**Implementation roadmap:**
[`user-wallet-v3-implementation-plan-codex.md`](user-wallet-v3-implementation-plan-codex.md)

**Research instrument:**
[`permission-action-taxonomy-research-prompt-codex.md`](permission-action-taxonomy-research-prompt-codex.md)

**Research reviewed:** `codex.md`, `gemini.md`, `claude.md`, and `grok.md` from
`~/Downloads/perms-research/`

**Date:** 2026-07-24

---

## Executive recommendation

The strongest combined design is:

> Keep action identities open, keep authority semantics closed, keep the
> existing policy engine, and require both an explicitly approved `actionId`
> and every categorical permission required by that action.

The research strongly supports the governing architecture's central direction.
New reviewed actions may be registered without recompiling the wallet, but a
registration must not create a new kind of authority, a new persistent right,
an arbitrary external call, a new settlement interpretation, or a new policy
language. Those changes require an explicit wallet-core design and owner
decision.

The recommended permission model has **16 documented authority boundaries**:

- **11 `INITIAL` permissions** needed to express the current wallet's major
  operational families with safer entry/exit and risk-increase/risk-reduction
  splits;
- **4 `LATER` permissions** that should not ship until their tracking,
  revocation, and settlement stories are proven; and
- **1 `RESERVED` permission boundary** for persistent external authority,
  which is named so it cannot be smuggled into an ordinary action but is not
  initially grantable.

`INITIAL` means part of the proposed Wallet v3 authority vocabulary, not that
all 11 permissions ship in the first vertical slice. The implementation
roadmap's action-family gates still control rollout.

The most important split is not between payment brands or protocol families.
It is between:

```text
move or transform value now
```

and:

```text
create a right, obligation, liability, or authority that survives this
transaction
```

The second most important split is between authority that can increase risk and
authority that is mechanically constrained to reduce risk. An agent that may
repay debt or exit a position should not automatically be able to borrow,
remove collateral, or enter a new position.

The permission system cannot determine whether a plausible invoice is genuine,
whether a vendor is overcharging, or whether an AI agent's economic judgment is
correct. A valid grant must therefore be treated as a **maximum-loss envelope**,
not as a guarantee of good behavior. Recipient allowlists, per-recipient
budgets, short expiries, aggregate limits, and dual control for new
counterparties or large exposure changes are the structural mitigations.

The safest brownfield implementation is smaller than a general capability
language:

1. store a permission mask and explicit routed-action set for each manager;
2. bind each immutable `actionId` to one exact required permission mask;
3. retain the existing fixed policy and limit concepts;
4. let a pinned extender prepare one bounded plan;
5. let the wallet create exact, transaction-scoped spend capability;
6. let one pinned, capability-aware Lego consume it once;
7. settle through a wallet-owned fixed mode using wallet-observed amounts; and
8. refuse actions whose authority, price behavior, persistence, or settlement
   cannot be represented safely.

This recommendation deliberately does **not** add a manager permission for
wallet administration, arbitrary recipients, arbitrary calldata, opaque
signatures, unlimited allowances, or sub-delegation.

---

## 1. How the four reports were weighed

The four reports agree more on the security structure than their different
permission names initially suggest. They were not weighted by length alone.
The review considered internal consistency, compatibility with the supplied
threat model, fit with the live Wallet v3 architecture, treatment of persistent
authority, and whether a recommendation actually fails closed.

| Report | Approximate size | Strongest contributions | Material cautions |
|---|---:|---|---|
| Codex | 12,853 words | Most complete effect-based taxonomy; strong pay-now/future-authority split; strong entry/exit and increase/reduce splits; good persistent-right inventory; good two-gate defense | Its typed primitive-plan proposal is broader than the current governing architecture and would need to prove that it does not become a generic effect language; its initial list is aggressive about standing approvals, signatures, and bridging |
| Gemini | 10,186 words | Useful dissent on the cost and operational friction of two gates; good emphasis on persistence, defensive authority, and micropayment economics | The permission-only conclusion would let newly registered actions fall under old categorical grants; manager-routable security administration is contrary to the prompt and current architecture; the proposed gasless fast path bypasses the wallet's heavy policy checks; source quality is mixed |
| Claude | 1,213 words | Concise corroboration of two gates, fixed authority, fail-closed settlement, manipulated-agent risk, and presentation-only presets | It is explicitly a compressed summary rather than the requested full analysis; exact identifiers and several mechanics were not fully worked through; its same-path gas conclusion is not yet supported by measurements from this repo |
| Grok | 10,335 words | Strong first-principles treatment, useful action mapping, good action lifecycle and upgrade reasoning, and clear rejection of mutable bundles | The taxonomy grants several dangerous powers too early, including unrestricted-recipient payment and standing allowance; it merges risk-increasing and defensive debt operations despite arguing that they should split; its amount-based “lite” lane weakens checks at exactly the boundary attackers can aggregate |

### 1.1 Findings that are consistent across the reports

All four reports support the following core conclusions:

- open action identities are compatible with a closed authority vocabulary;
- temporary, exact capability must be distinguished from persistent authority;
- a manager's allowed action repertoire must remain understandable and bounded;
- reviewed extenders and adapters can still be buggy or malicious;
- unknown permission, action, persistence, and settlement values must fail
  closed;
- payment now is materially different from creating a later claim;
- input manipulation of a valid AI agent is not solved by key security;
- value limits do not protect the wallet if missing, stale, zero, or manipulated
  prices weaken the calculation;
- manager ejection does not erase obligations that already exist;
- composites must consume the union of their constituent authority;
- permission bits must be append-only and never reordered or reused; and
- role presets should expand to concrete grants and must not mutate old grants
  when a preset definition changes.

Three reports explicitly keep both the action-ID and permission gates. Gemini
is the sole dissent. The governing architecture and this synthesis keep both
because they answer different questions:

```text
actionId approval       Which exact reviewed procedure may this manager run?
permission mask         What category of wallet power may this manager hold?
limits/configuration    How much, how often, using what assets, integrations,
                        recipients, and risk bounds?
```

The extra action gate is intentional fail-closed friction. When a new action or
implementation is registered, an existing manager must not receive it merely
because it uses a familiar permission.

### 1.2 Where this synthesis does not follow a report majority mechanically

The reports were research inputs, not votes. This synthesis rejects or narrows
several recurring suggestions:

- **Exact transaction-scoped allowance is not a permission.** It is a wallet
  execution primitive activated only inside one approved action and cleared
  atomically.
- **Gas or relayer payment is normally not a standalone permission.** Network
  gas is transaction mechanics. A wallet-funded relayer or paymaster fee is an
  immediate bounded payment governed by the action's fee policy.
- **Administrative security power is not a manager permission.** Freeze,
  ejection, recovery, registry mutation, codehash rebinding, ownership,
  guardian changes, limit enlargement, and permission changes stay on existing
  owner/security/system rails.
- **Unlimited or untracked persistent approvals do not ship as ordinary
  manager authority.**
- **An amount threshold must not choose a weaker validation regime.** Many
  small actions can aggregate into a large loss.
- **A generic typed effect grammar is not an initial requirement.** The current
  architecture can remain safer and smaller by assigning an exact static
  permission mask to each immutable action identity.

The reports' external citations and current-standard claims were not
independently re-verified for this synthesis. Standards work may inform a later
implementation review, but no external precedent overrides the wallet's local
threat model or the current governing document.

---

## 2. The authority model

The permission system should be organized around owner-meaningful authority,
not protocol names, calldata shapes, or every payment mechanism.

### 2.1 Ranked rule for splitting or merging permissions

Apply these tests in order. The first decisive higher-ranked test wins.

1. **Independent delegation:** Would a reasonable business owner grant one
   authority while withholding the other?
2. **Persistence or liability:** Does one create a surviving right,
   obligation, approval, signature, position, or liability that the other does
   not?
3. **Blast radius:** Does compromise or input manipulation cause a materially
   different maximum loss or recovery problem?
4. **Risk direction:** Can one be mechanically constrained to reduce exposure
   while the other can create or increase exposure?
5. **Counterparty and custody:** Does one introduce a new recipient, spender,
   integration, destination chain, or custody boundary?
6. **Limits and revocation:** Do they need different caps, expiry,
   enumeration, cancellation, or emergency handling?
7. **Consent clarity:** Would one plain-language consent sentence conceal a
   meaningful difference?
8. **Mechanics only:** If the difference is merely routing, call sequence,
   encoding, or another bounded execution detail, keep one permission and
   express the difference through `actionId`, configuration, or settlement.

This rule explains why direct payment and x402-style one-time payment can share
one permission, while direct payment and creation of a payee pull cannot. It
also explains why an exact one-action allowance is an execution primitive but
a reusable standing allowance is a separate persistent-authority boundary.

### 2.2 The eight concepts must remain separate

| Concept | Wallet v3 meaning |
|---|---|
| Action identity | One immutable reviewed operation, typed schema, and extender implementation |
| Permission | An owner-facing category of delegated power |
| Policy or limit | A quantitative or contextual restriction on that power |
| Execution mode | A bounded variation that does not create a new authority category |
| Settlement mode | A wallet-owned fixed observation and accounting recipe |
| Temporary capability | Exact authority activated for one session and cleared atomically |
| Persistent authority | A right or obligation that survives transaction completion |
| Administration | Power to alter the wallet's trust, recovery, ownership, registry, permissions, or security state |

Examples of the separation:

- swap slippage is a policy under `SWAP_ASSETS`, not a permission;
- an approved yield opportunity is configuration under `ENTER_STRATEGY`, not a
  new permission;
- `EXACT` versus `UP_TO_WALLET_BALANCE` is a spend mode, not a permission;
- an exact consume-time token approval is a temporary capability, while a
  reusable allowance is persistent external authority;
- a cheque and a reservation are different commitment object types but consume
  the same authority to create a bounded future payment claim;
- asset-only, debt, and yield settlement modes are wallet-internal enforcement
  recipes, not owner-facing permissions; and
- registering an extender or changing a manager limit is administration, not a
  routable financial action.

---

## 3. Recommended permission taxonomy

The identifiers below are recommended conceptual names. Ratifying the exact
names, rollout states, storage representation, and mapping from current Config
fields remains an owner gate.

### 3.1 Count and rollout

```text
INITIAL:   11
LATER:      4
RESERVED:   1
TOTAL:     16
```

`INITIAL` is the vocabulary needed for Wallet v3 parity and the currently
planned action families. It does not mean every permission is implemented or
activated at once.

### 3.2 Initial permissions

#### `PAY_NOW`

**Owner consent:** This manager may send approved assets now to approved
recipients within the limits you set.

It covers direct payment, approved-payee push, one-time merchant payment,
ordinary invoice payment, x402-style one-time payment, payroll batch, and an
outbound refund. It creates no later claim, allowance, order, stream,
reservation, or pull right.

Required policy includes allowed assets, explicit recipient or merchant sets,
per-transaction and aggregate budgets, per-recipient budgets, cooldowns, and
fee caps. A first-time or arbitrary recipient is not implied by this
permission.

#### `CREATE_PAYMENT_COMMITMENT`

**Owner consent:** This manager may create a bounded future payment claim for
an approved recipient under the amount, timing, and expiry rules you set.

It covers creation of payee pulls, cheques, reservations and later capture
rights, recurring payment mandates, subscriptions, and streams. These are
different object types with different limit and cancellation rules, but they
share the same owner-level authority: another party or schedule may move value
later without a fresh manager decision.

The permission does not authorize arbitrary token allowance, marketplace
listing, opaque signature, or unbounded obligation. Every commitment must have
a fixed type, creator attribution, maximum exposure, counterparty, expiry or
termination rule, and revocation semantics.

#### `SWAP_ASSETS`

**Owner consent:** This manager may exchange approved assets through approved
integrations within your size, price, and slippage limits.

It covers immediate spot conversion where outputs return to the wallet or
continue inside one approved atomic composite. It excludes resting orders,
cross-chain intent settlement, persistent signatures, and output to an
unapproved recipient.

The wallet must independently observe the input and output amounts used for
manager limits and slippage checks. A consumer-reported value is not sufficient.

#### `SELF_CUSTODY_TRANSFORM`

**Owner consent:** This manager may convert approved wallet assets between
equivalent self-custodied forms without giving another party a lasting claim.

It covers narrowly reviewed transformations such as ETH/WETH conversion or an
equivalent wrapper mint/redeem where beneficial ownership remains with the
wallet. It excludes market-risk swaps, vault entry, bridge custody, lockup,
slashing exposure, or a third-party claim.

The existing direct conversion rail may remain outside routing. It still needs
an explicit fail-closed manager authority in the new-generation policy model
rather than relying on today's unknown-action fallback.

#### `ENTER_STRATEGY`

**Owner consent:** This manager may place approved assets into approved yield
or treasury strategies within your exposure limits.

It covers deposits into reviewed vaults, lending-supply positions, and other
non-leveraged strategies that produce a persistent position. Strategy identity,
asset, lockup, exposure, and opportunity approval are policy configuration.

It excludes borrowing, leverage, liquidity provisioning with materially
different risk, slashing-risk staking unless explicitly classified, and any
persistent external spend authority.

#### `EXIT_STRATEGY`

**Owner consent:** This manager may withdraw from approved existing strategies
back to the wallet without opening or enlarging another position.

It covers withdrawal, redemption, and position closure to the wallet. It is
separate from entry because an owner may reasonably authorize an unwind agent
without letting that agent redeploy funds. A rebalance consumes
`EXIT_STRATEGY | ENTER_STRATEGY`, plus `SWAP_ASSETS` if a trade occurs.

It excludes redeposit, third-party payout, new debt, and any new persistent
authority.

#### `INCREASE_DEBT_RISK`

**Owner consent:** This manager may borrow, remove collateral, or otherwise
increase approved debt and liquidation risk within your limits.

It covers opening or increasing borrow positions, removing collateral,
increasing leverage, and refinancing that can increase liability. It requires
protocol, market, collateral, debt-asset, LTV, health-factor, and total debt
limits.

It is intentionally separate from repayment and deleveraging. Larger or novel
uses should require dual control even when the permission exists.

#### `REDUCE_DEBT_RISK`

**Owner consent:** This manager may repay approved debt, add approved collateral,
or close exposure when the wallet can verify that risk did not increase.

It covers repay, collateral top-up, close, and bounded deleverage. The permission
is only safe when the wallet can verify monotonic risk reduction: no higher
debt, no lower required collateral buffer, no value sent to an unapproved
recipient, residual assets returned to the wallet, and no new persistent
authority.

If those properties cannot be independently observed for an integration, the
action must use `INCREASE_DEBT_RISK`, remain owner-only, or stay unsupported.

#### `ENTER_LIQUIDITY_POSITION`

**Owner consent:** This manager may place approved assets into approved
liquidity positions within your exposure and price-range limits.

Liquidity has distinct custody, inventory, impermanent-loss, and tokenized
position risks and should not be hidden inside ordinary yield authority.
Concentrated-liquidity actions also require explicit NFT or position-token
custody accounting.

#### `EXIT_LIQUIDITY_POSITION`

**Owner consent:** This manager may remove approved existing liquidity
positions and return the proceeds to the wallet.

It is separated from entry for the same reason as strategy exit. Fee collection
that does not alter a position may consume `CLAIM_REWARDS`; a remove-and-swap
flow additionally consumes `SWAP_ASSETS`.

#### `CLAIM_REWARDS`

**Owner consent:** This manager may claim approved rewards into the wallet
without sending them elsewhere or creating a new position.

Claiming to the wallet is materially narrower than selling, restaking, or
transferring rewards. Claim-and-restake consumes
`CLAIM_REWARDS | ENTER_STRATEGY`; claim-and-sell consumes
`CLAIM_REWARDS | SWAP_ASSETS`.

### 3.3 Later permissions

#### `REVOKE_PERSISTENT_AUTHORITY`

**Owner consent:** This manager may cancel or reduce tracked future rights but
may not create or enlarge them.

This is a useful defensive permission, but it should be added only after
commitment enumeration and anti-griefing rules are proven. By default, a
manager should revoke only objects it created. Cross-manager revocation should
require explicit owner scope or the existing security-action path. Payroll
streams, legitimate merchant reservations, and other relied-upon obligations
must not be cancellable by an arbitrary hot manager.

#### `BRIDGE_ASSETS`

**Owner consent:** This manager may move approved assets through approved
bridges to approved recipients and destination chains.

It should ship only after source-chain custody, delayed finality, failure,
refund, attribution, and emergency-disable behavior are specified. Destination
execution is separate authority and is not implied.

#### `ISSUE_VALUE_SIGNATURE`

**Owner consent:** This manager may create a tracked, short-lived signature or
order that can move a bounded amount of wallet value later.

Only registered typed schemas with domain separation, wallet and chain binding,
amount and counterparty limits, expiry, nonce or epoch invalidation, and a
wallet-visible commitment record are eligible. Opaque `EIP-1271` approval,
unlogged Permit-style authority, and non-revocable long-lived orders remain
owner-only or unsupported.

#### `GOVERNANCE_ACTION`

**Owner consent:** This manager may cast approved governance votes or
delegations without transferring wallet assets or changing this wallet's own
administration.

Protocol governance can have indirect financial effects, so it should remain
separate and later. Proposal creation, proposal execution, treasury transfer,
or delegation of the wallet's financial control is not implied.

### 3.4 Reserved boundary

#### `CREATE_PERSISTENT_EXTERNAL_AUTHORITY`

**Owner consent:** This manager may create a specifically approved external
spender or operator right that survives the action.

This boundary includes reusable token allowances and persistent integration
operator rights. It is named now so those effects cannot hide inside
`SWAP_ASSETS`, `ENTER_STRATEGY`, or another ordinary permission.

It is **not initially grantable**. Before activation, it would require:

- a finite named authority kind;
- approved asset, target, spender/operator, and maximum amount;
- mandatory expiry where the external system supports it;
- onchain inventory and creator attribution;
- a tested revoke or invalidate path;
- a policy for predecessor/successor overlap during exits;
- explicit owner consent for every supported authority kind; and
- a decision on whether unlimited approval is categorically owner-only.

The recommended default is that unlimited allowances remain owner-only even if
this permission is later activated.

### 3.5 Powers that are not manager permissions

Do not allocate ordinary manager bits for:

- permission or limit enlargement;
- manager creation or grant modification;
- registry mutation or action activation;
- extender or Lego codehash rebinding;
- ownership, guardian, recovery, freeze, ejection, or migration control;
- wallet or backpack replacement;
- arbitrary target and calldata execution;
- unrestricted-recipient payment;
- opaque or untracked signature validation;
- unlimited external approvals;
- sub-delegation or session-key issuance by a manager; or
- a catch-all “manage protocol” or “contract call” permission.

Emergency freeze and ejection remain on the existing security control plane.
Sub-delegation should be unsupported, not merely hidden in a role preset.

### 3.6 Mapping from the current permission model

| Current concept | Recommended Wallet v3 authority |
|---|---|
| `TransferPerms.canTransfer` | `PAY_NOW` |
| `TransferPerms.canCreateCheque` | `CREATE_PAYMENT_COMMITMENT` |
| `LegoPerms.canManageYield` | split into `ENTER_STRATEGY` and `EXIT_STRATEGY` |
| `LegoPerms.canBuyAndSell` | `SWAP_ASSETS`; self-custody equivalence transforms split out |
| `LegoPerms.canManageDebt` | split into `INCREASE_DEBT_RISK` and `REDUCE_DEBT_RISK` |
| `LegoPerms.canManageLiq` | split into `ENTER_LIQUIDITY_POSITION` and `EXIT_LIQUIDITY_POSITION` |
| `LegoPerms.canClaimRewards` | `CLAIM_REWARDS` |
| `onlyApprovedYieldOpps` | strategy configuration, not permission |
| `SwapPerms.maxSlippage` and swap counters | policy under `SWAP_ASSETS` |
| allowed assets, Legos, payees | policy sets intersecting every applicable permission |
| cheque limits | object-specific policy under `CREATE_PAYMENT_COMMITMENT` |
| `failOnZeroPrice` | must not allow an invalid price to weaken a Wallet v3 value limit |

This mapping is a conceptual target. Phase 0 must measure the bytecode, ABI,
storage, deployment, and configuration impact before choosing a packed mask,
booleans, or a staged compatibility representation.

---

## 4. Grant model for many managers

The stored grant should be concrete:

```text
manager
permissionMask
explicitRoutedActionIds
managerPolicy
expiry
activation
suspension/ejection state
managerEpoch
```

The effective authority is the intersection of:

```text
wallet/global ceiling
AND manager grant
AND action registry specification
AND action lifecycle
AND action-specific policy
AND current wallet security state
```

### 4.1 Presets are presentation only

Product-defined presets such as “Payroll Agent,” “Yield Exit Agent,” or
“Treasury Rebalancer” are useful, but they must expand before owner approval
into:

- exact permission bits;
- exact action IDs;
- exact assets, integrations, recipients, and position types;
- exact budgets and expiry; and
- any dual-control threshold.

The wallet stores the expansion, not a mutable preset identifier. Updating a
preset later does not change an existing grant. The owner must explicitly
approve the new expansion.

### 4.2 Empty must not ambiguously mean “everything”

The current policy structures often use an empty allowed-assets, allowed-Legos,
or allowed-payees array as an unrestricted set. For a new high-value,
multi-agent wallet, this is too easy to misconfigure.

Wallet v3 should distinguish explicitly:

```text
NONE
EXPLICIT_SET
ANY
```

`ANY` should be a separately displayed high-risk owner choice, never an
accidental consequence of an empty array. The governing architecture already
requires an empty routed-action set to mean no routed actions. The same
fail-closed clarity should be evaluated for assets, Legos, recipients, and
integration classes in the new-generation Config.

### 4.3 Owner-facing consent should display maximum authority

The approval screen should show:

- plain-language permission descriptions;
- every action ID being granted;
- assets and counterparties;
- per-action, per-period, and lifetime value ceilings;
- maximum outstanding future commitments;
- maximum strategy, debt, and liquidity exposure;
- expiry and revocation behavior;
- whether any effect survives manager ejection; and
- the largest plausible loss if the manager exercises the entire grant.

That last item is important. The policy engine cannot tell whether an allowed
invoice is economically legitimate. Owners should approve the full envelope
they are willing to lose under key compromise or input manipulation.

---

## 5. Two-gate enforcement and action registration

### 5.1 Keep both gates

For a routed manager action:

```text
require manager is active and not suspended/ejected
require action lifecycle is ENABLED or valid EXIT_ONLY
require actionId is in the manager's explicit set
require actionId is inside any global manager ceiling
require manager permissionMask contains ActionSpec.requiredPermissionMask
require global permissionMask contains ActionSpec.requiredPermissionMask
require all policy and limit checks
```

Product governance may register a new action, but it cannot add that action to
a manager's Config or turn on a permission bit. The owner retains the final
grant decision.

### 5.2 Use an exact static permission mask per action

The initial `ActionSpec.requiredPermissionMask` should be the exact permission
union for that immutable action identity, not a self-declared value returned by
the extender.

If one apparent action sometimes requires materially different authority:

- give the variants distinct action IDs; or
- require the full union on every invocation.

For example:

```text
yield.rebalance.no-swap.v1
    EXIT_STRATEGY | ENTER_STRATEGY

yield.rebalance.with-swap.v1
    EXIT_STRATEGY | ENTER_STRATEGY | SWAP_ASSETS
```

This is safer than letting a buggy or malicious extender say that the current
invocation does not require `SWAP_ASSETS`. Open action IDs make this split
affordable, and the explicit manager action set keeps it understandable.

A bounded plan may still select amounts, assets, approved integrations,
minimum outputs, and other typed arguments. It must not determine the meaning
of the permission bits.

### 5.3 Recommended ActionSpec additions

The governing architecture already proposes:

```text
actionId
extender
extenderCodehash
requiredPermissionMask
settlementMode
eligibleAtBlock
opensOrExpandsPosition
exitActionIds[]
```

Before any routed action may create surviving authority, add a fixed
wallet-recognized persistence mask:

```text
persistenceMask:
    NONE = 0
    POSITION
    PAYMENT_COMMITMENT
    EXTERNAL_AUTHORITY
    VALUE_SIGNATURE
    BRIDGE_MESSAGE
```

This does not need to be a generic effect language. It is a closed lifecycle
and audit bitmask that forces the correct inventory, attribution, exit, and
revocation paths when an action has more than one persistent effect. Unknown
bits fail closed.

Any named external operator authority should also be immutably bound through a
reviewed authority-profile ID or equivalent fixed record. An extender must
never supply an arbitrary target, ABI string, or authority lifetime.

### 5.4 Execution flow

```text
manager calls executeAction(actionId, actionData, deadline)
    ↓
wallet locks before the first untrusted call
    ↓
wallet loads immutable ActionSpec and verifies extender codehash
    ↓
Config/Sentinel checks caller, action gate, exact permission mask, and policy
    ↓
pinned extender performs bounded static prepare
    ↓
wallet validates declared assets, Legos, recipients, spends, and fixed mode
    ↓
wallet resolves exact spend amounts and commits the complete session
    ↓
one pinned capability-aware Lego consumes once
    ↓
wallet activates only exact consume-time authority
    ↓
Lego performs the reviewed protocol sequence
    ↓
wallet independently observes the fixed settlement facts
    ↓
limits/counters commit once, authority clears, session clears
```

### 5.5 What the wallet can and cannot guarantee

The research often says that the wallet must be the “final arbiter.” That is the
right target, but the claim must be precise.

The wallet can enforce:

- caller, manager, permission, action, asset, integration, and recipient gates;
- exact code identities;
- exact capability amount and spender;
- one consumption;
- fixed settlement and wallet-observed amounts;
- cleanup and phase safety;
- no arbitrary target/calldata grant by registration; and
- no unknown authority or settlement semantics.

The wallet cannot generally prove how a reviewed Lego used every token after it
pulled the exact capability, infer undeclared protocol semantics from opaque
calldata, or decide whether an economically plausible trade was wise. The
extender and Lego therefore remain a pinned, reviewed trust boundary.

The honest residual-risk statement is:

> A malicious approved consumer must be unable to exceed the wallet-issued
> capability or create an unsupported persistent authority, but it may still
> misuse the exact amount the wallet validly released to it.

This is why per-action and aggregate limits remain load-bearing even after
codehash pinning and review.

---

## 6. Payments

### 6.1 Keep the mature direct rails initially

The existing wallet already has specialized direct behavior for:

- transfer;
- approved payees;
- payee pulls;
- cheques;
- Billing;
- payment preparation;
- payment-asset selection;
- recipient limits;
- cheque delays and expiry; and
- payment-specific counters.

The research does not justify moving those paths through the extender engine
merely for architectural uniformity. The initial recommendation remains:

> Preserve payment rails directly and apply the new authority semantics there.
> Route a payment mechanism only if a separate comparison proves a real product
> or safety advantage.

The direct rail is also the right economical path for one-time machine
payments. It can avoid registry/extender/session overhead without skipping the
manager lifecycle, permission, recipient, value, frequency, or price rules.

### 6.2 Pay now versus future payment authority

`PAY_NOW` includes:

- direct transfer now;
- approved-payee push;
- one-time approved merchant payment;
- ordinary invoice payment to an approved recipient;
- one-time x402-style payment;
- immediate payroll or batch disbursement; and
- outbound refund under a constrained recipient rule.

`CREATE_PAYMENT_COMMITMENT` includes:

- approved payee pull;
- cheque creation;
- reservation and capture;
- bounded recurring payment;
- subscription mandate;
- stream; and
- any future recipient claim.

The boundary is whether another party or schedule has an independent right
after the creating transaction completes.

### 6.3 Mechanism-specific rules stay in policy and object schemas

Sharing one permission does not make the mechanisms identical.

- A cheque has one recipient, maximum amount, unlock, expiry, and redemption
  rule.
- A reservation has an original amount, remaining amount, merchant, capture
  window, partial-capture policy, and release rule.
- A pull has payee, asset, per-pull, frequency, period, lifetime, and expiry
  bounds.
- A recurring payment has schedule, initiator, amount, missed-period, and
  cancellation rules.
- A stream has accrual, earned-but-unclaimed value, cancellation, and final
  settlement rules.

Those differences belong in fixed object types and limits. Registration cannot
invent a new commitment type. A new type requires a core review.

### 6.4 Recipient enrollment is a separate control

`PAY_NOW` must not mean “pay anyone.” New recipient or merchant enrollment
should remain owner-controlled or dual-controlled. A first-time recipient
payment can be handled by:

1. owner approves the recipient and its limits;
2. manager pays under `PAY_NOW`; or
3. owner executes a one-off payment directly.

This is one of the best defenses against both compromised keys and manipulated
AI agents. A separate hot-manager `PAY_ANYONE` permission is not recommended.

### 6.5 Reservations must affect available balance

If a future reservation system encumbers liquid value, the wallet's
`UP_TO_WALLET_BALANCE` resolution must subtract the reserved amount. Until the
wallet has an enumerated reserved-balance ledger, it must not claim that
reserved funds are protected from another manager action.

The earlier PoC's `RESERVED_TRANSFER` idea is only a wallet-side
reservation/partial-settlement primitive. It must not be described as a
complete machine-payment or MPP protocol.

---

## 7. Persistent authority, signatures, and administration

### 7.1 Temporary allowance

An exact allowance used inside one approved action is:

```text
derived from wallet-observed and policy-bounded amount
activated only during successful capability consumption
granted only to the committed consumer
consumed once
cleared before successful settlement completes
reverted with the entire transaction on failure
```

It is not a standalone owner permission and must not survive.

### 7.2 Persistent allowances and operator rights

Standing allowances and integration operator rights survive the action and can
remain exploitable after manager ejection. They therefore cannot hide inside
ordinary swap, yield, debt, liquidity, or rewards permissions.

The safest v1 choices are:

- use exact transaction-scoped authority wherever possible;
- add only named external operator shapes required by a confirmed production
  integration;
- make those shapes temporary when the external protocol permits it;
- keep persistent grants owner-only until inventory and revocation are proven;
  and
- never copy the legacy Lego-supplied target/ABI/calldata helper into routed
  execution.

### 7.3 Offchain signatures

The wallet must assume that a signature handed to another party may be filled
later, after manager revocation, and possibly when the wallet's state has
changed.

Delegated value signatures should be unsupported until every admitted schema
provides:

- exact typed meaning;
- domain, chain, wallet, signer, action, and nonce binding;
- fixed maximum value and counterparty;
- short expiry;
- partial-fill accounting where relevant;
- wallet-visible creation record;
- manager attribution;
- nonce or epoch invalidation that the settlement contract actually checks;
  and
- owner emergency invalidation.

If an external protocol does not permit reliable inventory and invalidation,
the signature is owner-only or unsupported. `EIP-1271` compatibility alone is
not a revocation model.

### 7.4 Persistent-authority ledger

Every surviving authority or obligation created by the wallet should have a
wallet-native reference:

```text
commitmentId
creatorManager
creatorEpoch
actionId or direct-rail type
permission
persistenceMask and subtype
asset
counterparty or spender
maximum remaining exposure
creation block
expiry
external reference
revocation method
status
```

The owner must be able to enumerate active items by type and, where practical,
by creating manager. An append-only numeric ID plus active-status mapping and
paginated per-manager indexes is safer than an unbounded loop during ejection.

Ejection should increment the manager epoch and stop new wallet-checked actions
immediately. It should not attempt an unbounded synchronous loop over every
allowance, stream, or signature. A separate incident response can revoke
tracked external rights in bounded batches while owner/security paths remain
available.

### 7.5 Administration remains a separate control plane

The owner is a business multisig, so routine owner actions do not need a second
manager permission. Additional delay or notice remains warranted for changes
that alter future trust:

- registry addition and action activation;
- extender or consumer succession;
- wallet template or backpack replacement;
- persistent external authority-kind addition;
- recovery and ownership changes; and
- permission taxonomy extension.

Immediate defensive actions should not wait:

- freeze;
- manager suspension or ejection;
- action disablement;
- disablement of a compromised integration; and
- owner/security revocation of dangerous tracked authority.

Managers must never be able to enlarge their own grant, add another manager,
change global ceilings, change code, or sub-delegate.

---

## 8. Policy and limits

### 8.1 Limits intersect; they do not substitute for one another

The effective limit should be the minimum of every applicable ceiling:

```text
wallet/global manager ceiling
manager-wide ceiling
permission-specific ceiling
action-specific ceiling
asset ceiling
recipient/merchant ceiling
integration/strategy ceiling
persistent-exposure ceiling
```

The existing manager-wide per-transaction, per-period, lifetime, count, and
cooldown controls remain useful. The smallest high-value additions are:

- per-recipient period and lifetime budgets for `PAY_NOW`;
- total outstanding commitment exposure for
  `CREATE_PAYMENT_COMMITMENT`;
- per-strategy and total strategy exposure for `ENTER_STRATEGY`;
- debt principal, LTV, and health-factor floors;
- liquidity-position exposure and price-range rules;
- per-action and per-permission budgets where the current manager-wide bucket
  is too coarse; and
- fee ratio and absolute fee ceilings.

No general onchain policy DSL is recommended. Add fixed, reviewed limit
semantics only when a permission or object type requires them.

### 8.2 Invalid price behavior

A missing, stale, zero, unsupported, or obviously invalid price must never turn
a USD-denominated cap into a zero-value or unlimited action.

For Wallet v3 manager actions, use one of:

1. reject the action;
2. apply a conservative maximum valuation; or
3. allow it only when a separately configured native-unit cap independently
   bounds the loss.

Preserving a legacy `failOnZeroPrice = False` setting without an independent
unit bound is not acceptable for a new routed value limit. The exact change
needs an owner decision because it can deliberately differ from legacy direct
behavior.

### 8.3 Input manipulation

No permission taxonomy can prove invoice truth or agent intent. Structural
controls that still help are:

- fixed recipients and merchants;
- owner-controlled recipient enrollment;
- vendor-specific budgets;
- separate machine-payment budgets;
- short manager expiry;
- action-specific grants;
- dual control for first-time recipients, large transfers, new debt, and large
  position entry;
- defensive-only agents for exit and debt reduction; and
- optional invoice or purpose commitments when the owner can define them
  without trusting the same manipulated agent.

Monitoring and anomaly detection are useful, but they are detection and
response tools, not the enforcement boundary.

---

## 9. Composite actions and partial failure

One `actionId` may represent an atomic multi-call workflow. Its static permission
mask is the union of every authority it may consume.

| Composite | Required permissions | Important rule |
|---|---|---|
| Yield rebalance without swap | `EXIT_STRATEGY \| ENTER_STRATEGY` | Source exit and target entry settle together |
| Yield rebalance with swap | `EXIT_STRATEGY \| SWAP_ASSETS \| ENTER_STRATEGY` | Wallet must observe each counted swap |
| Deleverage using collateral conversion | `REDUCE_DEBT_RISK \| SWAP_ASSETS` | Debt must not increase; residuals return to wallet |
| Claim and restake | `CLAIM_REWARDS \| ENTER_STRATEGY` | Claim alone must not imply restake |
| Bridge and deposit | source `BRIDGE_ASSETS`, destination `ENTER_STRATEGY` | Two asynchronous authorities; do not pretend they are one atomic source-chain action |
| Withdraw and pay | `EXIT_STRATEGY \| PAY_NOW` | Recipient checks still apply after withdrawal |
| Refinance across integrations | commonly `REDUCE_DEBT_RISK \| INCREASE_DEBT_RISK \| SWAP_ASSETS` | High-risk; use dual control or owner-only until measured |
| Unwind liquidity and repay | `EXIT_LIQUIDITY_POSITION \| REDUCE_DEBT_RISK`, plus `SWAP_ASSETS` if needed | Position output, swap, and debt reduction all need observation |

### 9.1 Atomic EVM failure

Inside one EVM transaction, a propagated revert rolls back token transfers,
allowances, wallet counters, and external-contract state changed by the same
transaction. The wallet should not catch and normalize a failed security-
critical leg as success.

The dangerous cases are:

- a low-level call reports failure and the adapter ignores it;
- the adapter intentionally permits partial success;
- settlement relies on an extender-reported amount;
- an external signature, order, bridge message, or persistent object was
  intentionally created for later use; or
- the workflow crosses transactions or chains.

For ordinary atomic composites:

- counters and cooldowns commit only after successful wallet settlement;
- the wallet charges the fixed, independently observed policy value once;
- every temporary allowance clears;
- no partial action success is returned; and
- failure of step 2 or 3 reverts the whole transaction.

Asynchronous bridge, order, stream, or pull flows are not atomic composites and
must use persistent-object lifecycle rules.

---

## 10. Revocation, upgrades, and exits

### 10.1 Manager revocation

Immediate suspension or ejection stops:

- new direct manager actions;
- new routed actions;
- new commitment creation;
- new wallet-validated signatures; and
- use of the old manager epoch.

It does not erase:

- already paid funds;
- active payee pulls, cheques, reservations, schedules, or streams;
- standing external allowances or operator rights;
- signatures already given to third parties;
- open debt or strategy positions;
- bridge messages already sent; or
- legally or economically earned claims.

The owner interface should present these surviving items as an incident
checklist, not imply that “manager removed” means “all effects gone.”

### 10.2 Entry and exit

Every action that opens or expands a persistent position must identify at least
one usable exit or owner recovery path before activation.

The governing lifecycle remains sound:

```text
PENDING → ENABLED | DISABLED
ENABLED → EXIT_ONLY | DISABLED
EXIT_ONLY → DISABLED
DISABLED → terminal
```

`EXIT_ONLY` must never bypass ordinary permission, action-ID, policy, or limit
checks. It preserves a non-expanding path and blocks new grants.

### 10.3 Code and taxonomy upgrades

- A material action meaning, schema, or extender change receives a new
  `actionId`.
- New consumer code receives a new Lego ID.
- Existing managers do not receive either automatically.
- Permission bits are permanent, append-only, and never reordered or reused.
- Deprecation leaves the old bit reserved and unset for new grants.
- A taxonomy version may be stored for audit and UI, but it must not reinterpret
  old bits.
- Product preset versions never mutate an existing onchain expansion.

Pure bug-fix rebinding under the same action identity is not recommended for the
initial system. A new identity plus explicit opt-in is easier to audit and
fails closed.

---

## 11. Adversarial conclusions

| Threat | Maximum loss or failure | Structural controls | Residual risk |
|---|---|---|---|
| Compromised manager uses only allowed actions | Up to the full aggregate grant envelope, potentially accumulated over days | action ID set, permission mask, recipient set, per-recipient and aggregate limits, short expiry | An approved recipient can still receive economically illegitimate payments |
| Uncompromised AI agent is manipulated | Same as the valid grant for the manipulated sequence | fixed recipients, narrow action set, separate defensive agents, dual control for high-risk transitions | Taxonomy cannot determine business truth |
| Buggy or malicious extender/Lego | At most exact wallet-issued capability plus any separately approved persistent authority | codehash pinning, exact capability, named target/authority, fixed settlement, postconditions | Consumer may misuse the exact amount validly released |
| Missing/stale/zero/manipulated price | Limit bypass or denial of service | fail closed or independent unit caps, source freshness, wallet-owned valuation | Oracle corruption can still block actions or misvalue within accepted bounds |
| Ejection with outstanding commitments | Later pulls, fills, captures, debt, or bridge completion | persistence ledger, creator attribution, manager epoch, bounded revocation workflows, owner exits | Some external rights may be irrevocable; those should not be delegated |
| Composite failure | Stranded position or latent authority if failure is caught or asynchronous | propagated revert, one consumption, fixed settlement, cleanup, no partial-success semantics | Cross-chain and offchain flows remain asynchronous by nature |

The broadest initial permission is `CREATE_PAYMENT_COMMITMENT`, because it can
create many kinds of future claims. It must therefore be constrained by an
allowed object-type set and a total outstanding-exposure cap.

The most dangerous ordinary combination is:

```text
INCREASE_DEBT_RISK | SWAP_ASSETS | PAY_NOW
```

It can create liability, transform borrowed assets, and move value to a
recipient. It should rarely be granted to one hot agent and should use dual
control at material thresholds.

The most operationally harmless-looking dangerous action is a signature,
allowance, or operator approval that moves no funds during the creating
transaction. The absence of an immediate balance change is not evidence of low
risk.

---

## 12. Gas and transaction-value spread

The reports correctly identify the tension between sub-dollar machine payments
and large treasury actions, but the safe answer is not to select security
checks based only on transaction value.

Use two **functionally distinct paths**:

1. **Narrow direct path:** immediate payment or self-custody conversion with no
   external protocol call graph and no persistent effect.
2. **General routed path:** strategies, swaps, debt, liquidity, rewards, and
   composites using registry, extender, session, capability, consumer, and
   fixed settlement.

Both paths retain the same core manager lifecycle, permission, asset, recipient,
aggregate-limit, and invalid-price rules. The direct path is cheaper because it
does less, not because the amount is below a “dust” threshold.

Reject these shortcuts:

- bypassing the wallet with an external-token signature fast path;
- skipping recipient or aggregate checks for small amounts;
- treating short expiry as sufficient replay protection;
- relying on anomaly detection instead of enforcement; or
- assuming L2 gas makes rich validation negligible without measurement.

Phase 0 and each vertical slice should measure:

- wallet and Config runtime/creation size;
- cold and warm storage reads;
- successful and reverting gas for the exact action;
- calldata size;
- direct-path versus routed-path delta;
- price lookup and settlement cost;
- persistent-object storage cost; and
- worst-case batch or composite cost.

No report's rough gas number is decision-grade for this repository.

---

## 13. Recommended implementation sequence

This sequence is intended to refine, not replace, the existing implementation
roadmap.

### Phase A — Ratify the authority decision record

Before changing contracts, the owner decides:

- exact permission names and rollout states;
- whether the entry/exit and increase/reduce splits above are accepted;
- explicit-set versus `ANY` semantics for assets, Legos, and recipients;
- the initial manager and global permission-mask representation;
- whether permission-specific budgets are required in v1;
- invalid-price behavior for new routed actions; and
- whether `REVOKE_PERSISTENT_AUTHORITY` remains later or enters the initial
  vocabulary.

Output: an append-preserved decision record referenced by the governing
architecture and implementation plan.

### Phase B — Compile the fail-closed skeleton

Implement and measure only the common authority substrate:

- manager and global permission masks;
- bounded explicit manager action-ID set;
- empty action set means none;
- cumulative bit checks;
- unknown bits reject;
- unknown actions and settlement modes reject;
- immutable exact permission mask in `ActionSpec`;
- action lifecycle checks; and
- no manager administration or sub-delegation path.

Do not activate production actions.

### Phase C — Yield entry vertical slice

Use `ENTER_STRATEGY` only:

- one immutable action ID;
- one pinned extender;
- one capability-aware Lego;
- exact spend;
- approved asset, Lego, and opportunity;
- fixed `YIELD_DEPOSIT` settlement;
- wallet-observed policy value;
- no persistent external operator authority; and
- owner exit evidence before activation.

### Phase D — Yield exit and rebalance

Add `EXIT_STRATEGY`, then prove:

- exit without entry authority;
- `EXIT_ONLY` lifecycle;
- no-swap rebalance uses `EXIT_STRATEGY | ENTER_STRATEGY`;
- swap rebalance uses the additional `SWAP_ASSETS` bit;
- wallet-observed swap evidence; and
- atomic failure and cleanup.

### Phase E — Named external authority

Inventory confirmed integration needs. Add only named temporary authority
shapes. Any persistent shape remains owner-only until the persistent-authority
ledger and revocation package pass.

### Phase F — Debt by risk direction

Implement `REDUCE_DEBT_RISK` first for repay and collateral top-up. Then add
`INCREASE_DEBT_RISK` for borrow and collateral removal. Prove monotonicity for
the defensive class and require owner/dual control where it cannot be proven.

### Phase G — Liquidity and rewards

Add entry and exit independently. Concentrated liquidity requires explicit NFT
custody and settlement evidence. Claim-only actions use `CLAIM_REWARDS`;
restake or swap composites require the additional bits.

### Phase H — Separate payment decision

Map the new `PAY_NOW` and `CREATE_PAYMENT_COMMITMENT` semantics onto the mature
direct rails first. Compare routing only after direct behavior, gas,
reservation accounting, cancellation, and Billing roles are fully specified.

### Phase I — Later and reserved authority

Bridge, value signatures, governance, delegated revocation, and persistent
external authority each need a separate owner-approved package. None should
arrive as incidental metadata on an ordinary action.

---

## 14. Verification requirements

The existing governing architecture's security invariants and test plan remain
authoritative. The permission research adds these explicit cases.

### 14.1 Permission and grant tests

- every initial permission has an owner-facing consent string;
- manager with action ID but missing one bit fails;
- manager with bits but missing action ID fails;
- a new action never expands an old grant;
- global and manager masks intersect;
- composite masks require every bit;
- unknown and deprecated bits fail;
- empty action list means none;
- explicit `ANY` policy, if supported, cannot be confused with empty;
- presentation-preset changes do not mutate existing grants; and
- owner/security paths cannot be reached through manager permissions.

### 14.2 Authority-direction tests

- `EXIT_STRATEGY` cannot deposit;
- `REDUCE_DEBT_RISK` cannot increase debt, remove required collateral, send
  residuals away, or leave a persistent approval;
- `EXIT_LIQUIDITY_POSITION` cannot create or enlarge a position;
- `CLAIM_REWARDS` cannot sell, restake, or transfer rewards;
- `SELF_CUSTODY_TRANSFORM` cannot invoke a market-risk route; and
- `PAY_NOW` cannot create a future claim.

### 14.3 Persistent-effect tests

- every commitment is attributed to manager and epoch;
- total outstanding exposure is bounded;
- ejection stops creation but preserves object state;
- owner can enumerate and act on active objects;
- revocation is bounded and cannot loop over an unbounded set;
- revocation cannot enlarge or redirect authority;
- opaque and unsupported signature schemas reject;
- persistent external authority rejects while the reserved permission is
  inactive; and
- a commitment type unknown to the wallet rejects.

### 14.4 Price and manipulated-agent tests

- missing, stale, zero, or unsupported prices cannot weaken a value cap;
- unit-cap fallback, if allowed, is independently enforced;
- many individually small payments hit aggregate and per-recipient limits;
- an allowed but malicious invoice can consume only the approved recipient
  budget;
- new-recipient payment requires the owner-controlled enrollment path; and
- machine-payment frequency cannot bypass lifetime exposure.

### 14.5 Composite and failure tests

- each named composite uses the exact static union mask;
- optional-swap and no-swap variants cannot under-declare permissions;
- step failure propagates a revert;
- no low-level false return is accepted as success;
- counters commit only on successful final settlement;
- all temporary authority clears;
- bridge/destination behavior is tested as asynchronous, not atomic; and
- a consumer cannot create a persistent effect under a zero
  `persistenceMask`.

---

## 15. Owner decisions this research narrows but does not make

1. Ratify or revise the 16-boundary taxonomy and exact identifiers.
2. Decide whether `REVOKE_PERSISTENT_AUTHORITY` is initially delegated or kept
   on owner/security rails until a later package.
3. Decide whether new-generation empty asset, Lego, and recipient sets fail
   closed or preserve legacy wildcard semantics.
4. Decide the Config representation: one packed mask, staged booleans, or a
   compatibility bridge, based on compiled evidence.
5. Decide whether owner-routed actions bypass manager action-ID grants while
   still obeying registry lifecycle, fixed settlement, and session safety.
6. Decide the per-manager action-ID bound and optional global action ceiling.
7. Decide which permission-specific budgets are required for the first release.
8. Decide the exact stale, missing, and zero price policy for each settlement
   mode.
9. Decide whether a fixed `persistenceMask` joins `ActionSpec` before the first
   position action or only before the first non-position persistent effect.
10. Decide whether persistent external operator authority is ever acceptable
    for a manager and, if so, under which named shapes.
11. Decide whether unlimited allowance is categorically owner-only.
12. Decide when, if ever, payment mechanisms should enter routed execution.

These decisions should be explicit architecture revisions or decision records,
not implicit choices made by the first implementation agent.

---

## 16. Ideas explicitly rejected for Wallet v3 v1

- **Permission-only routing:** registering a new action would enlarge old
  categorical grants.
- **Action-ID-only routing:** owners would have to infer authority from an
  ever-growing procedural catalog, and common invariants would lack an
  independent enforcement layer.
- **Mutable action implementations:** code changes would silently change what
  existing grants mean.
- **Generic arbitrary-call permission:** it collapses all wallet authority into
  calldata review.
- **Extender-selected required permissions:** a malicious extender could
  under-declare.
- **Turing-complete or open-ended policy DSL:** too large an audit, governance,
  and gas surface for the first system.
- **Manager-routable wallet administration:** operational agents must not alter
  their own security boundary.
- **Manager-routable arbitrary recipients:** input manipulation turns it into a
  direct extraction path.
- **Standing or unlimited allowance as an initial ordinary permission:** it
  creates delayed drain authority that survives ejection.
- **Untracked offchain signatures:** the owner cannot enumerate or reliably
  revoke them.
- **Amount-based weak “dust lane”:** repeated small actions aggregate and become
  the bypass.
- **Automatic cancellation of every obligation on manager ejection:**
  legitimate counterparties may have earned or relied on those claims, and
  unbounded cancellation can fail or be used for griefing.
- **Mutable role bundles:** a product preset must never become a hidden
  catch-all after approval.
- **One permission per payment mechanism:** object types and policy can preserve
  important differences without forcing owners to manage a sprawling
  mechanism taxonomy.

---

## 17. Final plan

The permission system should be understood as a small, durable control plane
around an open catalog of immutable actions:

```text
Owner grants:
    exact authority categories
    + exact action identities
    + exact limits and counterparties
    + an expiry

Wallet enforces:
    active manager
    + both gates
    + fixed policy
    + exact temporary capability
    + fixed settlement
    + cleanup and attribution

Reviewed extender and Lego provide:
    action-specific interpretation and protocol execution
    inside the wallet's hard authority ceiling

Persistent effects require:
    explicit permission boundary
    + fixed object type
    + inventory
    + attribution
    + expiry/revocation/exit

Anything else:
    owner-only, delayed for a new core review, or unsupported
```

The architecture succeeds if a new action can reuse these fixed boundaries
without changing what any existing manager grant means. It should stop and
require a core review when a new action needs a new kind of recipient power,
persistent authority, liability, settlement observation, cross-domain effect,
or administrative control.

That stop condition is not a failure of extensibility. It is the main security
property of Wallet v3.
