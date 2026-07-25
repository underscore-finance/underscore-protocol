# Wallet v3 Permission Research Incorporation Proposal — Codex

**Status:** Proposed decision record for review; not governing architecture,
implementation authorization, or deployment authorization

**Date:** 2026-07-25

**Governing architecture:**
[`simplified-user-wallet-action-architecture-codex.md`](simplified-user-wallet-action-architecture-codex.md)

**Implementation roadmap:**
[`user-wallet-v3-implementation-plan-codex.md`](user-wallet-v3-implementation-plan-codex.md)

**Research syntheses reviewed:**

- [`perms-research-summary-claude.md`](perms-research-summary-claude.md)
- [`perms-research-summary-codex.md`](perms-research-summary-codex.md)

This document decides what I recommend incorporating from those two syntheses,
what I recommend adapting, what should be deferred, and what should be rejected.
It deliberately does not change the governing architecture yet. The permission
decisions below should receive independent review and owner disposition first.

---

## 1. Recommendation in one page

The research validates the governing architecture's central model:

```text
open catalog of immutable action IDs
        +
finite, owner-readable permission categories
        +
existing assets / Legos / recipients / limits
        +
exact transaction-scoped capability
        +
fixed wallet settlement
```

The research does **not** justify a new general policy language, one permission
per payment mechanism, runtime permission declarations by extenders, a cheaper
amount-based validation lane, or a broad rewrite of the existing manager-policy
engine.

My recommended incorporation is:

1. Keep both authorization gates:
   - explicit manager approval of the exact `actionId`; and
   - every categorical permission required by that action.
2. Add one `uint256` routed-permission mask beside the existing manager
   structures in the new Wallet v3 Config. Do not add more booleans to the
   existing `ManagerSettings`, `LegoPerms`, or `TransferPerms` structures.
3. Forward the manager and global routed masks through `PolicyContextV1` and
   check them in the new routed Sentinel entry point. Preserve the existing
   direct-policy ABI and meaning.
4. Use eight initial permission categories, four later categories, and one
   reserved boundary. This is smaller than either synthesis because the exact
   `actionId` gate already provides procedural granularity.
5. Give each immutable `ActionSpec` one exact static permission mask. The
   extender does not declare or narrow permission requirements at runtime.
   Optional variants with different authority use different action IDs.
6. Use one cross-family `POSITION_EXIT` permission for mechanically
   non-expanding actions, rather than separate exit bits for yield, debt, and
   liquidity. Exact action IDs and existing policy sets keep the category
   narrow in practice.
7. Keep payments on the mature direct rails initially. `TRANSFER` means value
   moves now; `PAYMENT_COMMITMENT` means a bounded claim survives.
8. Do not add `ENROLL_PAYEE`, `PAY_NETWORK_FEES`, delegated administration,
   standing allowances, offchain signatures, or cross-chain authority to the
   initial implementation merely because the research discussed them.
9. Treat composite authorization as:

   ```text
   union of required permission bits
   AND
   cumulative application of every relevant limit
   ```

   A swap cannot launder value around an asset, recipient, or value ceiling.
10. Admit new persistent authority only through a separate, typed,
    owner-approved package with inventory, attribution, exposure accounting,
    expiry, and revocation. Phase 1 creates no new persistent external
    authority.

This gives Wallet v3 append-only permission capacity without turning permission
design into the largest change in the system.

---

## 2. How the two syntheses were weighed

Neither synthesis is a vote or an authority document.

### 2.1 What the Claude synthesis does especially well

The Claude synthesis is strongest when it grounds the research in this
repository. Its highest-value contributions are:

- recognizing that permission representation and ABI churn matter more here
  than whether the final count is 13, 16, or 17;
- proposing a parallel Config mask rather than expanding the existing nested
  manager structs;
- identifying the current direct Sentinel fallback as fail-open;
- explaining why a defensive permission needs argument binding and
  wallet-computed postconditions, not merely approved function selectors;
- showing that permission union alone is insufficient for composites when
  limits can be bypassed through an intermediate conversion;
- distinguishing wallet-internal claims from external or offchain rights for
  revocation; and
- preserving one validation standard rather than creating a low-value
  downgrade lane.

Its broader 17-boundary recommendation should not be adopted wholesale. It
introduces several product capabilities that the current wallet does not need
for the first routed architecture, including delegated payee enrollment,
network-fee authority, and delegated claim revocation.

The document also contains two internal conflicts:

- it recommends `PAY_NETWORK_FEES` as an initial permission, while later
  classifying gas, relayer, and paymaster fees as policy under `TRANSFER`; and
- it recommends `ENROLL_PAYEE` as an initial permission, while later
  classifying first-time recipient control as existing configuration rather
  than a permission.

Those conflicts reinforce the need to apply the split rule consistently rather
than accept the proposed bit table as a unit.

### 2.2 What the Codex synthesis does especially well

The Codex synthesis is more internally conservative and closer to the governing
architecture. Its highest-value contributions are:

- a clear open-actions / closed-authority model;
- a strong pay-now versus surviving-claim boundary;
- exact static permission masks on immutable action IDs;
- separation of temporary capability from persistent authority;
- explicit refusal of manager administration, arbitrary calls, and opaque
  signatures;
- preservation of the existing direct payment rails;
- persistent-authority inventory and manager attribution;
- invalid-price requirements;
- a concrete future-action admission rule; and
- a useful implementation and test sequence.

Its 16-boundary recommendation splits entry and exit independently for yield,
debt, and liquidity. That is defensible in isolation, but it underuses the exact
manager `actionId` gate. If a manager must already be granted the exact yield
withdrawal, debt repayment, or liquidity-removal action, separate categorical
exit bits add permanent taxonomy and UI surface without adding equivalent
security.

The Codex synthesis also proposes a generic `persistenceMask` in `ActionSpec`.
That may become useful later, but the first routed slice already has a closed
position flag, fixed settlement mode, exit IDs, and no new payment, signature,
bridge, or standing-approval object. Adding a generic persistence taxonomy
before those effects exist would freeze speculative metadata.

### 2.3 Combined judgment

Use the Codex synthesis as the conservative authority-model base, the Claude
synthesis for repository-specific implementation constraints and adversarial
corrections, and the existing governing architecture for the session,
capability, settlement, registry, and succession design.

Where the syntheses disagree, choose the smaller rule that still fails closed.

### 2.4 Key disagreement matrix

| Topic | Claude synthesis | Codex synthesis | This proposal |
|---|---|---|---|
| Documented boundaries | 17 | 16 | 13: 8 initial, 4 later, 1 reserved |
| Exit authority | One cross-family `POSITION_EXIT` | Separate strategy, debt, and liquidity exit permissions | One `POSITION_EXIT`, narrowed by exact action IDs and postconditions |
| Network fees | Separate initial bit, but later text also folds them into transfer policy | Fee policy under the parent action | Fee policy; no initial bit |
| Payee enrollment | Separate initial bit, but later text also calls it existing configuration | Owner-controlled recipient enrollment | Keep owner/config-controlled initially |
| Delegated revocation | Initial defensive permission | Later, after inventory and anti-griefing | Later |
| Self-custody transforms | Use existing family axis and action IDs | Separate initial transform permission | Explicit action under `TRADE` |
| Action implementation update | Same semantic action ID may receive a versioned implementation | Material code receives a new action ID | New extender receives a new action ID |
| Persistent-effect metadata | Fixed type/flag | Generic closed `persistenceMask` | Existing position/exit fields first; add new metadata only for a concrete new effect |
| Empty policy sets | Prefer explicit `NONE / SET / ANY` | Prefer explicit `NONE / SET / ANY` | Preserve existing meanings for the first slice; make them explicit in consent and measure a future encoding |
| Dual control | New two-manager co-signature design | Use for high-risk changes without fixing one mechanism | No new authentication system in Phase 1 |
| Price-free defensive actions | Broad exemption after monotonicity proof | Fail closed or use native-unit bounds | Exempt only pure non-converting exits whose native-unit and postcondition proof is independently sufficient |

---

## 3. Conclusions to incorporate without reopening

These conclusions are sufficiently supported and already align with the
governing design.

| Conclusion | Disposition | Incorporation |
|---|---|---|
| Action IDs may grow; authority meanings remain finite | **ADOPT** | Keep open registry and closed permission vocabulary |
| Exact action-ID approval and categorical permissions answer different questions | **ADOPT** | Require both for every routed manager action |
| A new action must not enter an existing manager grant automatically | **ADOPT** | Empty action set means none; additions require owner-authorized Config update |
| Extenders cannot choose their required permissions | **ADOPT** | `ActionSpec.requiredPermissionMask` is immutable and static |
| Exact temporary allowance is not a permission | **ADOPT** | Keep it as session capability machinery |
| Settlement mode is not a permission | **ADOPT** | Keep the wallet-owned closed settlement vocabulary |
| Manager administration is not ordinary operational authority | **ADOPT** | Preserve owner/security/system control plane |
| Permission bits are append-only and never reused | **ADOPT WITH STRONGER RULE** | Meanings are immutable; deprecate rather than reinterpret a bit |
| Presets are presentation only | **ADOPT** | Expand to bits, action IDs, limits, and counterparties before owner approval |
| Unknown actions, bits, stages, modes, or persistent effects fail closed | **ADOPT** | Add explicit tests at each relevant boundary |
| Amount alone must not select a weaker validation path | **ADOPT** | Keep direct and routed paths different by function, not value threshold |
| Payments remain direct initially | **ADOPT** | Research refines permission meaning without forcing routing |
| Persistent effects require attribution and enumeration | **ADOPT FOR NEW EFFECTS** | No new persistent type ships without its lifecycle package |
| Same-chain composites are atomic or separate actions | **ADOPT** | No caught security-critical partial failure |
| Missing or invalid prices cannot silently reduce charged value to zero | **ADOPT** | Define fixed failure or independent native-unit bounds per recipe |

---

## 4. Proposed permission taxonomy

### 4.1 Why eight initial categories are enough

The exact `actionId` gate answers:

```text
Which reviewed procedure may this manager execute?
```

The permission mask answers:

```text
What owner-readable kind of power does that procedure require?
```

Because the first question is already exact, the second vocabulary should stay
coarse. Categorical permissions should split only when the owner should be able
to grant one class while withholding the other **even after exact action
selection and existing limits are considered**.

### 4.2 Recommended permanent bit assignment

The proposed assignment is new-generation-only. Existing booleans are not
reinterpreted as these bits.

| Bit | Permission | State | Owner-readable authority |
|---:|---|---|---|
| 0 | `TRANSFER` | INITIAL | Send approved value now to approved recipients within existing payment limits |
| 1 | `PAYMENT_COMMITMENT` | INITIAL | Create a typed, bounded future payment claim through a direct wallet rail |
| 2 | `TRADE` | INITIAL | Convert approved assets through approved integrations within price and slippage limits |
| 3 | `YIELD` | INITIAL | Open or increase an approved non-debt strategy position |
| 4 | `DEBT` | INITIAL | Open or increase debt, leverage, or collateral-withdrawal risk |
| 5 | `LIQUIDITY` | INITIAL | Open or increase an approved liquidity position |
| 6 | `REWARDS` | INITIAL | Claim accrued rewards to the wallet without selling, transferring, or redeploying them |
| 7 | `POSITION_EXIT` | INITIAL | Close or reduce an existing position under wallet-verified non-expansion rules |
| 8 | `REVOKE_CLAIMS` | LATER | Cancel or reduce tracked persistent rights without creating or enlarging them |
| 9 | `CROSS_CHAIN` | LATER | Create a typed, bounded cross-chain transfer or message |
| 10 | `OFFCHAIN_SIGNATURE` | LATER | Create a tracked, bounded value-moving signature that may be used later |
| 11 | `GOVERNANCE` | LATER | Exercise protocol governance without wallet administration or value transfer |
| 12 | `PERSISTENT_EXTERNAL_AUTHORITY` | RESERVED | Create a named standing spender or operator right that survives the action |
| 13–255 | Unassigned | — | Unknown bits reject |

`INITIAL` means part of the initial durable vocabulary. It does not mean every
permission is implemented or activated in Phase 1.

Support still grows action family by action family. The first routed
`SUPPORTED_PERMISSION_MASK` may contain only `YIELD`. A bit becomes grantable
for routed execution only when a concrete action package, settlement recipe,
policy mapping, and tests are authorized. Unimplemented initial, later, and
reserved bits reject rather than existing as inert grants.

### 4.3 Mapping from the current wallet

| Current concept | Wallet v3 routed meaning |
|---|---|
| `TransferPerms.canTransfer` | `TRANSFER` |
| `TransferPerms.canCreateCheque` | `PAYMENT_COMMITMENT` |
| `LegoPerms.canBuyAndSell` | `TRADE` |
| `LegoPerms.canManageYield` | `YIELD` for entry/increase; `POSITION_EXIT` for withdrawal |
| `LegoPerms.canManageDebt` | `DEBT` for borrow/remove collateral; `POSITION_EXIT` for repay/add collateral/close |
| `LegoPerms.canManageLiq` | `LIQUIDITY` for entry/increase; `POSITION_EXIT` for removal |
| `LegoPerms.canClaimRewards` | `REWARDS` |
| Approved assets, Legos, payees, opportunities, slippage, counts, cooldowns, and value limits | Existing policy and limits, not new permission bits |

The existing direct path can retain its current boolean meaning during the
incremental build. The routed path uses the new mask. Any later decision to
make the new-generation direct rails consume the mask is a separate
compatibility package; until then `TRANSFER` and `PAYMENT_COMMITMENT` describe
the durable taxonomy while their current direct enforcement remains
`canTransfer` and `canCreateCheque`. No Config should store two independently
editable representations of the same live authority.

### 4.4 Deliberately not initial permissions

#### Payee enrollment

Adding or broadening a recipient is authority administration. Keep it on the
existing owner/payee-configuration rail initially.

If product evidence later requires manager-assisted enrollment, design a
separate probation-class object with attribution, expiry, a lifetime cap, and
owner-configured ceilings. Do not pre-allocate an initial bit for an unbuilt
product.

#### Network, relayer, and paymaster fees

Ordinary transaction gas is not wallet permission. A wallet-funded relayer or
paymaster charge is a bounded fee attached to a parent action. Enforce a named
recipient/profile and absolute or proportional fee cap. It does not need an
independent permission unless owners later need to delegate fee payment while
withholding the parent action, which is not a current requirement.

#### Self-custody transforms

ETH/WETH and other reviewed equivalent-form transformations use explicit
action IDs and the existing `TRADE` authority rather than a new categorical bit.
This is intentionally conservative: possessing `TRADE` alone grants no action,
because exact action-ID approval is still required.

The current direct Sentinel fallback must not be treated as the specification
for this behavior.

#### Standing allowance

A standing allowance is one subtype of the reserved
`PERSISTENT_EXTERNAL_AUTHORITY` boundary. Exact transaction-scoped allowance
remains capability machinery. Unlimited allowance remains owner-only.

#### Sub-delegation and manager administration

These are unsupported or owner/security control-plane powers, not dormant
operational permissions. Reserving bits for them would suggest an accepted
delegation model that has not been designed.

#### Staking and derivatives

These remain named future candidates, not pre-approved bits. Apply the split
rule when a concrete action and settlement recipe exist. Slashing exposure,
continuous funding, options obligations, or liquidation behavior may justify
new categories later.

---

## 5. Routed permission representation

### 5.1 Do not expand the existing manager structs

The existing structures are used across Config, Sentinel, HighCommand,
ChequeBook, Migrator, Kernel, and ActionDataProvider. Adding more nested
booleans would create the exact broad ABI and bytecode churn this incremental
track is trying to avoid.

The proposed new-generation Config stores routed permissions separately:

```text
managerRoutedPermissionMask[manager] -> uint256
globalRoutedPermissionMask          -> uint256
allowedRoutedActionIds[manager]     -> bounded set of bytes32
globalAllowedRoutedActionIds        -> optional bounded ceiling
```

The exact encoding and bounds remain Phase 0B measurement outputs.

### 5.2 Fixed checks

For a manager-routed action:

```text
required = ActionSpec.requiredPermissionMask

require required != 0
require required & ~SUPPORTED_PERMISSION_MASK == 0
require managerMask & required == required
require globalMask & required == required
require actionId in manager allowed-action set
require actionId in global ceiling, if configured
```

The first registered action may use only one bit. The mask representation still
ships early because it prevents every later permission from becoming a struct
and ABI migration.

### 5.3 `PolicyContextV1`

In addition to the field-complete existing action-data and manager-policy
structures already required by the governing architecture, `PolicyContextV1`
must carry:

- the manager routed-permission mask;
- the global routed-permission mask;
- the supported-mask constant or generation identity needed to interpret
  them; and
- the exact action ID and immutable required mask.

Those fields are fixed before the provider/Config generation is compiled. The
provider gathers and forwards them mechanically. Sentinel interprets them.

### 5.4 Keep the direct and routed meanings separate

The new routed Sentinel entry point uses cumulative mask checks. The current
direct entry point continues to receive existing structs and `ActionType`.

This avoids a flag-day rewrite of:

- current direct wallet actions;
- current manager Config storage;
- ChequeBook;
- Migrator;
- Kernel;
- existing struct-bearing HighCommand settings interfaces; and
- existing deployed wallet behavior.

HighCommand may still need one narrow Wallet v3 coordination entry point for
routed masks and action IDs. Phase 0B must measure that exact addition rather
than expanding every existing settings call.

The direct `else: return True` fallback is a real fail-open behavior, but fixing
it changes current authorization semantics. Treat it as a separately reviewed
legacy hardening candidate. Wallet v3 routed authorization always rejects an
unknown action or mask. Its production disposition must be explicit before a
Wallet v3 release; documenting it is not acceptance of the fallback.

---

## 6. Static action permission semantics

### 6.1 The registry is the only permission source

`ActionSpec.requiredPermissionMask` is the exact static union required by that
action ID.

The extender does not:

- supply the mask;
- choose among permission variants;
- remove a permission for the current invocation; or
- enlarge the mask.

If optional behavior changes the required authority, use separate action IDs:

```text
yield.rebalance.no-swap.v1
    POSITION_EXIT | YIELD

yield.rebalance.with-swap.v1
    POSITION_EXIT | YIELD | TRADE
```

This is easier to audit than a second runtime permission declaration and makes
the owner-facing action grant exact.

### 6.2 One action ID still pins one implementation

Keep the governing rule:

```text
one action meaning
one argument schema
one extender address and codehash
one required permission mask
one settlement mode
```

A new extender implementation receives a new action ID, even if governance
believes the semantics are equivalent.

The Claude synthesis's semantic-ID / mutable-implementation split reduces
re-granting friction, but it creates a new governance burden: proving that a
code change is semantically identical to every existing grant. Wallet v3 does
not need that complexity initially. Re-granting after a reviewed code change is
intentional fail-closed friction.

### 6.3 No generic persistence mask in the first registry

Version one already has:

- `opensOrExpandsPosition`;
- immutable exit action IDs;
- a closed settlement mode;
- a named operator-authority package; and
- direct typed payment objects outside routing.

That is enough for the first routed families. Do not add a generic
`persistenceMask` until a concrete routed action needs a second persistent
effect that those fields cannot express.

At that point, the architecture returns for review rather than assigning
speculative meaning to reserved metadata.

---

## 7. Limits, composites, and defensive authority

### 7.1 Composite actions

Permission union is necessary but not sufficient.

For every composite:

- the static mask contains every constituent permission;
- every spend asset and touched wallet asset enters the existing allowed-asset
  checks;
- every policy integration enters the existing allowed-Lego checks;
- recipient checks apply to the final beneficiary;
- the wallet charges its fixed policy meter from the gross wallet value
  released or the stricter recipe-specific basis, not merely the terminal
  output asset;
- every applicable global, manager, action, recipient, strategy, and future
  permission-specific ceiling applies cumulatively;
- a trade cannot transform an otherwise disallowed source asset into an
  allowed payment asset to evade the intended value ceiling; and
- counters and cooldowns commit only after complete successful settlement.

Phase 0B must define the exact charge basis for each initial composite. It must
not introduce a general limit DSL.

### 7.2 `POSITION_EXIT`

`POSITION_EXIT` is deliberately cross-family. The exact action-ID gate and
existing allowed asset/Lego/position rules determine which exit procedures the
manager may use.

An action may require only `POSITION_EXIT` when the wallet can prove:

- it references a position owned by the wallet;
- every `receiver`, `beneficiary`, `owner`, and `onBehalfOf` parameter is bound
  to the wallet where applicable;
- no debt or liquidation risk increases;
- no required collateral buffer decreases;
- no new position, obligation, signature, approval, recipient right, or other
  persistent authority is created;
- all proceeds and residual assets return to the wallet;
- any conversion leg has its own `TRADE` permission and independently enforced
  slippage/value controls; and
- frequency and fee/value-destruction bounds prevent defensive churn from
  becoming a griefing path.

If the wallet cannot prove those properties for an integration, the action:

- requires the risk-increasing family bit as well;
- remains owner-only; or
- is unsupported.

Removing collateral is not a defensive action. It requires `DEBT`.

### 7.3 Price behavior

Missing, zero, stale, unsupported, or invalid price data must never make a
charged action look free.

The fixed settlement recipe chooses one of:

1. reject without a valid price;
2. enforce a conservative valuation; or
3. enforce an independent native-unit ceiling that still bounds loss.

A pure, non-converting exit may be price-independent only when wallet-observed
postconditions and native-unit bounds prove that it cannot extract value or
increase risk. A deleverage action containing a trade is not categorically
price-exempt merely because debt decreases.

The exact rule is an owner decision per first settlement recipe, informed by
Phase 0A evidence.

### 7.4 Existing empty-set semantics

For routed action IDs:

```text
empty == no routed actions
```

For existing allowed assets, Legos, and payees, the current policy often treats
an empty list as unrestricted. Reversing that meaning inside the first slice
would be a broader policy-engine change.

The incremental recommendation is:

- preserve current onchain semantics for the first candidate;
- display empty-as-unrestricted explicitly in every owner-facing Config
  expansion and test fixture; and
- measure an explicit `NONE / SET / ANY` representation in Phase 0B without
  making it a prerequisite for the yield-deposit slice.

No implementation may silently assume empty means the same thing across action
IDs and existing policy sets.

---

## 8. Persistent effects and payments

### 8.1 Phase 1 creates no new persistent external authority

The first yield deposit creates a wallet-owned position represented through the
fixed yield settlement and entry/exit metadata. It does not create:

- a standing token allowance;
- an offchain signature;
- a bridge message;
- a third-party pull;
- a new payee;
- a stream or subscription; or
- a reusable external operator right.

The named operator-authority package remains separate and adds only confirmed,
fixed call shapes.

### 8.2 Direct payment semantics

Keep the existing specialized payment paths initially:

```text
TRANSFER
    value moves now
    no new surviving claim

PAYMENT_COMMITMENT
    a typed bounded claim may be exercised later
```

A cheque, payee pull, reservation, recurring schedule, and stream may share the
same owner-facing permission while retaining distinct object schemas, limits,
expiry, and cancellation behavior.

No new commitment type is created merely by registering an extender.

### 8.3 Future persistent-authority package

Before a new persistent type becomes manager-authorized, require:

- fixed object or authority type;
- manager and manager-epoch attribution;
- asset, counterparty, spender, and maximum remaining exposure;
- creation time and expiry;
- wallet-visible status;
- bounded enumeration;
- O(1) manager suspension or ejection;
- bounded or paginated external cleanup where necessary;
- owner emergency action;
- reliance-versus-unilateral-right semantics; and
- tests proving no untracked or unknown type can be created.

The exact routine-versus-for-cause ejection semantics proposed by the Claude
synthesis are a valuable future design input, but they affect payroll,
merchant, and legal reliance behavior. They belong in the payment/persistence
package, not in Phase 1.

### 8.4 No new dual-control system in Phase 1

The manipulated-agent threat is real, but a two-manager co-signature system
would add a new authentication, replay, liveness, attribution, and recovery
model. It is not an incremental permission change.

For the first architecture:

- owner multisig remains the control for grant creation, new recipients, limit
  enlargement, and high-risk configuration;
- exact action IDs, short grants, recipients, and existing limits bound hot
  managers; and
- a future dual-control design requires a separate owner-approved proposal.

---

## 9. Incorporation into the implementation roadmap

### 9.1 Phase 0A — add evidence, not contract behavior

Extend the current-state baseline to record:

- exact existing direct permission mapping, including the unknown-action
  fallback;
- `canCreateCheque` versus `canTransfer`;
- entry and exit sharing under current yield, debt, and liquidity booleans;
- empty allowed-assets, allowed-Legos, and allowed-payees behavior;
- zero, missing, stale, and invalid price behavior;
- exact temporary allowance and cleanup behavior;
- current manager-ejection effects on cheques, payees, and external approvals;
  and
- successful and reverting gas for the current permission path.

This evidence does not change production authorization.

### 9.2 Phase 0B — ratify and compile the permission substrate

Before the first implementation disposition:

- owner approves or amends this taxonomy;
- compile the parallel manager/global `uint256` routed masks;
- compile the bounded manager action-ID set;
- include both masks and the exact required mask in `PolicyContextV1`;
- keep existing manager structs and direct policy entry points unchanged;
- measure Config, provider, Sentinel, and HighCommand size and gas;
- define the supported-mask constant and unknown-bit failure;
- define the exact initial action mask;
- define the first composite charge bases;
- define the `POSITION_EXIT` proof template, without implementing an exit yet;
  and
- record `PROCEED`, `PROCEED NARROWER`, `REDESIGN`, or `STOP`.

### 9.3 Phase 1A — ActionRegistry

Add tests that:

- the exact static required mask is immutable;
- a required zero mask rejects;
- unknown bits reject;
- different permission variants use different action IDs;
- a new extender uses a new action ID;
- a new action never expands an existing manager grant; and
- no generic persistence or runtime permission field exists.

### 9.4 Phase 1B1 — Config and ActionDataProvider

Implement and measure:

- the bounded manager action-ID set;
- the parallel routed manager mask;
- the routed global mask;
- duplicate and unknown-bit rejection;
- action-ID addition checks;
- full `PolicyContextV1` forwarding; and
- unchanged legacy manager structs and direct provider behavior.

### 9.5 Phase 1B2 — Sentinel and HighCommand

Implement and measure:

- cumulative manager/global routed-mask checks;
- exact action-ID gate coordination;
- unknown-bit and unsupported-action failure;
- separate direct and routed entry points;
- no first-match `if / elif` behavior for masks; and
- no new generic policy evaluator.

The current direct fail-open fallback receives a separate disposition. It is
not silently changed through the routed entry point.

### 9.6 Phase 1C — first yield-deposit slice

The first action requires only:

```text
YIELD
```

It proves:

- exact action-ID approval;
- manager and global mask checks;
- existing allowed asset/Lego/opportunity policy;
- approved opportunity is checked before capability activation on the routed
  path even though the current direct path can safely revert after an atomic
  deposit;
- exact capability;
- fixed yield settlement;
- valid price behavior;
- allowance cleanup; and
- no new persistent external authority.

### 9.7 Later action-family packages

- Yield withdrawal uses `POSITION_EXIT`.
- Yield rebalance uses `POSITION_EXIT | YIELD`, plus `TRADE` when applicable.
- Debt repayment and collateral top-up use `POSITION_EXIT` only after the
  action-specific postcondition proof passes.
- Borrow and collateral removal use `DEBT`.
- Liquidity removal uses `POSITION_EXIT`.
- Claim-only uses `REWARDS`; claim-and-sell adds `TRADE`; claim-and-redeposit
  adds `YIELD`.
- Payments map `TRANSFER` and `PAYMENT_COMMITMENT` onto direct rails before any
  routing comparison.
- Later and reserved bits require their own owner-approved packages.

---

## 10. Proposed governing-document changes after approval

If this decision record is approved, update the governing architecture in one
focused revision:

1. Replace section 5.1's provisional list with the approved bit table.
2. Add the parallel routed-mask representation and direct/routed compatibility
   boundary.
3. State that `ActionSpec.requiredPermissionMask` is exact and solely
   registry-defined.
4. Add `POSITION_EXIT`'s required wallet-verifiable conditions.
5. Strengthen composite policy from permission union to permission union plus
   cumulative limits.
6. Add the price-independent exit boundary.
7. State that permission meanings and bit positions are immutable and never
   reused.
8. Add mask fields to the `PolicyContextV1` definition.
9. Record the rejected initial categories and future package boundaries.
10. Add governing invariants and map each new invariant to implementation
    packages and tests.

Update the implementation roadmap in the same revision:

1. replace the generic Phase 0B permission decision with this exact decision
   record and its disposition;
2. add Phase 0A permission and price baselines;
3. add mask measurements and fields to Packages 0B, 1B1, and 1B2;
4. set the first yield action's exact mask;
5. add the `POSITION_EXIT` proof gate before withdrawals or defensive debt;
6. add composite charge-basis evidence;
7. keep payment/persistence and dual control in separate future packages; and
8. extend invariant traceability and drift tests.

The website should be updated only after the governing Markdown changes. Until
then, this proposal remains a review input rather than presented architecture.

---

## 11. Owner decisions

The research narrows the permission problem to these decisions.

| # | Decision | Recommendation |
|---:|---|---|
| P1 | Initial taxonomy | Approve eight initial, four later, and one reserved boundary |
| P2 | Representation | Use parallel `uint256` manager/global routed masks in the new Config; do not expand existing manager structs |
| P3 | Exit authority | Use one cross-family `POSITION_EXIT`, gated by exact action IDs and wallet-verifiable non-expansion |
| P4 | Action permission semantics | One immutable exact static mask per action ID; no runtime extender permission declaration |
| P5 | Direct-path fallback | Review as a separate legacy hardening change and resolve its production disposition before release; routed unknown actions always fail |
| P6 | Existing empty policy sets | Preserve current semantics for the first slice, make wildcard meaning explicit, and measure an explicit scope representation |
| P7 | Price-independent exits | Permit only pure, non-converting, native-bounded exits with wallet-proven non-extraction and non-expansion |
| P8 | First persistent additions | Keep payee enrollment, delegated revocation, standing authority, signatures, bridges, and new commitment types out of Phase 1 |

P4 preserves an already governing action-identity rule. P1–P3 and P5–P8 are
the decisions this research most directly informs.

---

## 12. Reviewer checklist

The independent reviewer should answer:

1. Does the eight-permission initial vocabulary omit an authority that cannot
   be represented safely by action ID plus existing policy?
2. Is a cross-family `POSITION_EXIT` too broad even with exact action-ID,
   asset, Lego, recipient, and action-specific postcondition checks?
3. Does keeping self-custody transforms under `TRADE` create unacceptable
   owner-consent ambiguity?
4. Is keeping payee enrollment owner-side the safer incremental choice, or
   would it predictably force operators to over-broaden payee sets?
5. Does the parallel mask actually avoid the claimed ABI churn once exact
   Config/provider/Sentinel interfaces are sketched?
6. Are any mask fields missing from `PolicyContextV1`?
7. Is the composite gross-charge rule precise enough to prevent swap-mediated
   limit laundering without a general effect language?
8. Are the `POSITION_EXIT` postconditions wallet-observable for the first yield
   and debt integrations?
9. Does rejecting a generic `persistenceMask` leave any first-phase effect
   unclassified?
10. Are the deferred payment, persistence, and dual-control packages separated
    at the right boundaries?
11. Do any recommendations accidentally change current direct-wallet behavior?
12. Which owner decisions must be settled before Phase 0B rather than at a
    later family gate?

The reviewer should verify claims against the live contracts and the governing
architecture, not treat either research synthesis as authority.
