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
   structures in the new Wallet v3 Config, plus explicit `NONE / SET / ANY`
   codes for asset, Lego, and payee scopes. Do not add more booleans to the
   existing `ManagerSettings`, `LegoPerms`, or `TransferPerms` structures.
3. Forward the manager/global routed masks and scope codes through
   `PolicyContextV1` and check them in the new routed Sentinel entry point.
   Preserve the existing direct-policy ABI and meaning.
4. Use twelve initial vocabulary categories, four later categories, and one
   reserved boundary. “Initial vocabulary” does not mean “enabled in the first
   release”; support is enabled only with a reviewed action-family package.
5. Give each immutable `ActionSpec` one exact static permission mask. The
   extender does not declare or narrow permission requirements at runtime.
   Optional variants with different authority use different action IDs.
6. Use separate `YIELD_EXIT`, `DEBT_REDUCE`, and `LIQUIDITY_EXIT` permissions.
   Reuse common argument-binding, AUTH, and non-expansion proof templates in
   implementation, but do not generalize those distinct owner authorities into
   one permanent bit.
7. Keep payments on the mature direct rails initially. `TRANSFER` means value
   moves now; `PAYMENT_COMMITMENT` means a bounded claim survives.
8. Add `PAY_NETWORK_FEES`, `ENROLL_PAYEE`, and `REVOKE_CLAIMS` as distinct
   durable permissions, but do not make any grantable before its bounded
   package exists. Keep delegated administration, standing allowances,
   offchain signatures, and cross-chain authority out of the initial
   implementation merely because the research discussed them.
9. Treat composite authorization as:

   ```text
   union of required permission bits
   AND
   cumulative application of every relevant limit
   ```

   A swap cannot launder value around an asset, recipient, or value ceiling.
10. Require valid prices by default. Admit price-independent execution only
    through an exact immutable `NATIVE_BOUNDED_RECOVERY` recipe for an eligible
    pure yield/liquidity exit.
11. Admit new persistent authority only through a separate, typed,
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
introduces product capabilities that the current wallet does not need for the
first routed architecture. This proposal adopts the network-fee, bounded
payee-enrollment, and claim-revocation boundaries in the durable vocabulary
without pretending any of those functionalities already exists.

The document also contains two unresolved reversals. This is not an inference
from its source-attribution column: section 4.5 is explicitly titled
“Deliberately not permissions,” and its third table column is “Why I decline.”
Its own recommendations therefore move in opposite directions:

- section 4.2 assigns `PAY_NETWORK_FEES` an initial bit; section 4.5 declines
  gas, relayer, and paymaster fees as a permission and places them under
  `TRANSFER`; section 10.3 then recommends a separate network-fee boundary
  again; and
- section 4.2 assigns `ENROLL_PAYEE` an initial bit; section 4.5 declines
  first-time recipient control as a permission; section 10.3 then recommends
  bounded delegated enrollment again.

Those reversals reinforce the need to apply the split rule consistently rather
than accept the proposed bit table as a unit. They do not make the underlying
concerns frivolous. In particular, a fee recipient may not be enumerable in
the same way as an ordinary payee. The owner therefore selected a distinct
permission while requiring a future relayer/paymaster package to solve that
recipient-binding problem before the bit becomes grantable. The owner also
selected bounded delegated payee enrollment, agreeing with the synthesis's
later considered position while requiring a probationary package before use.

For fairness, the Claude synthesis's later and more deliberate reconciliation
in section 10.3 and Appendix A favors a separate `PAY_NETWORK_FEES` permission
despite the section 4.5 reversal. This proposal now agrees with that considered
boundary while adding explicit parent-mask, action-ID, recipient-binding, cap,
and grantability requirements.

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
debt, and liquidity. I initially recommended merging those exits because the
exact manager `actionId` gate already narrows the procedure. The owner rejected
that generalization: the categorical layer should independently let an owner
grant yield recovery while withholding debt or liquidity authority. This
proposal therefore adopts the family-specific split while continuing to share
implementation proof machinery.

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

Where the syntheses disagree, prefer an owner-readable boundary that reflects a
meaningful product choice. Exact action IDs prevent procedural overbreadth, but
they do not automatically justify merging distinct categories of authority.

### 2.4 Key disagreement matrix

| Topic | Claude synthesis | Codex synthesis | This proposal |
|---|---|---|---|
| Documented boundaries | 17 | 16 | 17: 12 initial, 4 later, 1 reserved |
| Defensive authority | One cross-family `POSITION_EXIT` | Separate strategy, debt, and liquidity exit permissions | Separate `YIELD_EXIT`, `DEBT_REDUCE`, and `LIQUIDITY_EXIT`, each narrowed further by exact action IDs and postconditions |
| Network fees | Reverses between a separate bit (§4.2), rejection as a permission (§4.5), and separate boundary (§10.3) | Fee policy under the parent action | Separate `PAY_NETWORK_FEES` permission, additive to the parent action and ungrantable until its package exists |
| Payee enrollment | Reverses between a separate bit (§4.2), owner configuration (§4.5), and bounded delegated enrollment (§10.3) | Owner-controlled recipient enrollment | Separate `ENROLL_PAYEE`, ungrantable until its probationary enrollment package exists |
| Delegated revocation | Initial defensive permission | Later, after inventory and anti-griefing | Owner-selected `REVOKE_CLAIMS`, ungrantable until inventory, scope, and anti-griefing rules exist |
| Self-custody transforms | Use existing family axis and action IDs | Separate initial transform permission | Explicit action under `TRADE` |
| Action implementation update | Same semantic action ID may receive a versioned implementation | Material code receives a new action ID | New extender receives a new action ID |
| Persistent-effect metadata | Fixed type/flag | Generic closed `persistenceMask` | Existing position/exit fields first; add new metadata only for a concrete new effect |
| Empty policy sets | Prefer explicit `NONE / SET / ANY` | Prefer explicit `NONE / SET / ANY` | Owner-selected `NONE=0 / SET=1 / ANY=2` for Wallet v3 assets, Legos, and payees; legacy direct behavior unchanged |
| Dual control | New two-manager co-signature design | Use for high-risk changes without fixing one mechanism | No new authentication system in Phase 1 |
| Price-free defensive actions | Broad exemption after monotonicity proof | Fail closed or use native-unit bounds | Owner-selected closed `NATIVE_BOUNDED_RECOVERY` recipes only for eligible pure yield/liquidity exits; default remains `PRICE_REQUIRED` |

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
| Missing or invalid prices cannot silently reduce charged value to zero | **ADOPT WITH OWNER DISPOSITION** | Default `PRICE_REQUIRED`; only exact owner-approved `NATIVE_BOUNDED_RECOVERY` recipes may use native limits and distinct accounting |

---

## 4. Proposed permission taxonomy

### 4.1 Why twelve initial-vocabulary categories are appropriate

The exact `actionId` gate answers:

```text
Which reviewed procedure may this manager execute?
```

The permission mask answers:

```text
What owner-readable kind of power does that procedure require?
```

Because the first question is already exact, the second vocabulary should avoid
procedural duplication. But it should still split when an owner may reasonably
want to grant one family of reduction while withholding another **even after
exact action selection and existing limits are considered**. The owner selected
that finer control for yield exits, debt reduction, and liquidity exits. The
owner also selected a separate network-fee boundary because it authorizes a
purpose-specific wallet outflow to a recipient class that may not fit ordinary
payee allowlisting. Finally, the owner selected `ENROLL_PAYEE` because expanding
the recipient set is a distinct administrative authority that should never be
hidden inside `TRANSFER`.

### 4.2 Recommended permanent bit assignment

The proposed assignment is new-generation-only. Existing booleans are not
reinterpreted as these bits.

| Bit | Permission | Vocabulary status | First enforcement package | Owner-readable authority |
|---:|---|---|---|---|
| 0 | `TRANSFER` | INITIAL | Existing direct `canTransfer`; future direct-mask compatibility package | Send approved value now to approved recipients within existing payment limits |
| 1 | `PAYMENT_COMMITMENT` | INITIAL | Existing direct `canCreateCheque`; future payment package | Create a typed, bounded future payment claim through a direct wallet rail |
| 2 | `PAY_NETWORK_FEES` | INITIAL | Future bounded network-fee package; ungrantable until then | Pay a bounded relayer, paymaster, or equivalent execution fee for an otherwise authorized parent action |
| 3 | `ENROLL_PAYEE` | INITIAL | Future probationary payee-enrollment package; ungrantable until then | Add a bounded new payee under owner-defined probation, attribution, expiry, and exposure ceilings; no payment authority |
| 4 | `TRADE` | INITIAL | Later routed trade/composite package | Convert approved assets through approved integrations within price and slippage limits |
| 5 | `YIELD` | INITIAL | Phase 1C first routed action | Open or increase an approved non-debt strategy position; no exit authority |
| 6 | `DEBT` | INITIAL | Later debt package, after AUTH when the selected integration/action requires operator authority | Open or increase debt, leverage, or collateral-withdrawal risk |
| 7 | `LIQUIDITY` | INITIAL | Later liquidity package | Open or increase an approved liquidity position |
| 8 | `REWARDS` | INITIAL | Rewards package, after AUTH when an integration requires operator authority | Claim accrued rewards to the wallet without selling, transferring, or redeploying them |
| 9 | `YIELD_EXIT` | INITIAL | First yield-withdrawal package; AUTH first only when the selected integration/action requires operator authority | Withdraw, close, or reduce an approved yield position back to the wallet |
| 10 | `DEBT_REDUCE` | INITIAL | First defensive-debt package; AUTH first when the selected integration/action requires operator authority | Repay or otherwise reduce an existing wallet debt obligation without increasing exposure |
| 11 | `LIQUIDITY_EXIT` | INITIAL | First liquidity-removal package; AUTH first only when the selected integration/action requires operator authority | Remove or reduce an approved liquidity position back to the wallet |
| 12 | `REVOKE_CLAIMS` | LATER | Separate revocation package | Cancel or reduce tracked persistent rights without creating or enlarging them |
| 13 | `CROSS_CHAIN` | LATER | Separate cross-chain package | Create a typed, bounded cross-chain transfer or message |
| 14 | `OFFCHAIN_SIGNATURE` | LATER | Separate signature package | Create a tracked, bounded value-moving signature that may be used later |
| 15 | `GOVERNANCE` | LATER | Separate governance package | Exercise protocol governance without wallet administration or value transfer |
| 16 | `PERSISTENT_EXTERNAL_AUTHORITY` | RESERVED | Not grantable until an owner-approved authority package exists | Create a named standing spender or operator right that survives the action |
| 17–255 | Unassigned | — | Not grantable | Unknown bits reject |

`INITIAL` means part of the initial durable vocabulary. The separate
“First enforcement package” column states when the authority first becomes
live. It does not mean every permission is implemented or activated in
Phase 1.

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
| No current manager equivalent | `PAY_NETWORK_FEES`; assigned in the durable vocabulary but ungrantable until its package exists |
| Owner-side payee configuration | `ENROLL_PAYEE`; future bounded manager enrollment, ungrantable until its probationary package exists |
| `LegoPerms.canBuyAndSell` | `TRADE` |
| `LegoPerms.canManageYield` | `YIELD` for entry/increase; `YIELD_EXIT` for withdrawal |
| `LegoPerms.canManageDebt` | `DEBT` for borrow/remove collateral; `DEBT_REDUCE` for a qualifying repay, collateral top-up, or close |
| `LegoPerms.canManageLiq` | `LIQUIDITY` for entry/increase; `LIQUIDITY_EXIT` for removal |
| `LegoPerms.canClaimRewards` | `REWARDS` |
| Approved assets, Legos, payees, opportunities, slippage, counts, cooldowns, and value limits | Existing policy and limits, not new permission bits |

The Claude synthesis uses one `POSITION_EXIT`; the Codex synthesis recommends
separate family exits. The owner selected the finer model. The permanent
permission vocabulary therefore distinguishes recovery-shaped yield and
liquidity exits from obligation-reduction debt spends. Common proof machinery
may still be shared without sharing authority.

The existing direct path can retain its current boolean meaning during the
incremental build. The routed path uses the new mask. Any later decision to
make the new-generation direct rails consume the mask is a separate
compatibility package; until then `TRANSFER` and `PAYMENT_COMMITMENT` describe
the durable taxonomy while their current direct enforcement remains
`canTransfer` and `canCreateCheque`. No Config should store two independently
editable representations of the same live authority.

Owner-facing consent for `YIELD` must say explicitly that it grants entry or
increase only. A yield withdrawal requires `YIELD_EXIT`. A default UI
preset may pair the two, but the underlying authorities remain separately
grantable so an owner may intentionally permit entry while retaining exclusive
recovery authority.

### 4.4 `PAY_NETWORK_FEES` is additive, never standalone

Ordinary transaction gas paid by the transaction sender is not wallet
permission. A wallet-funded relayer, paymaster, or equivalent execution charge
requires `PAY_NETWORK_FEES` in addition to every permission required by the
parent action:

```text
authorized fee-paying action
    parent action's exact static permission mask
    |
    PAY_NETWORK_FEES
```

`PAY_NETWORK_FEES` alone cannot move value, select a parent action, or authorize
a general transfer. If fee payment is optional, the fee-paying and non-fee
variants use distinct action IDs because their static permission masks differ.

The future package must enforce a named fee mechanism/profile, an absolute
and/or proportional fee cap, and exact binding for a dynamic or
non-enumerable recipient. An ordinary payee allowlist must not be assumed
sufficient. The bit remains outside `SUPPORTED_PERMISSION_MASK` and is not
grantable until that complete package is reviewed and authorized.

### 4.5 `ENROLL_PAYEE` is enrollment, never payment

Adding a recipient expands where later value may flow, so it receives a
separate permission rather than hiding inside `TRANSFER`.

`ENROLL_PAYEE` authorizes only a typed probationary enrollment action. It does
not authorize a payment, and it cannot:

- pay the new recipient;
- convert a probationary payee into an unrestricted or owner-trusted payee;
- enlarge or reset an existing payee's exposure;
- alter another manager's enrollment;
- bypass recipient, asset, cooldown, transaction-count, or value limits; or
- create an enrollment outside owner-configured ceilings.

The future package must bind:

- the exact enrollment action ID;
- manager and manager-epoch attribution;
- recipient identity and any allowed recipient class;
- creation time and expiry;
- per-payment, rolling, and lifetime exposure ceilings;
- the maximum number of active probationary payees;
- owner suspension and removal;
- manager-ejection behavior; and
- bounded enumeration and status visibility.

Paying an enrolled recipient remains a separate action requiring `TRANSFER`,
the exact payment action ID, the probationary payee's remaining limits, and all
ordinary policy checks. `ENROLL_PAYEE` remains outside
`SUPPORTED_PERMISSION_MASK` until this complete lifecycle package is reviewed
and authorized.

### 4.6 `REVOKE_CLAIMS` is reduction-only

`REVOKE_CLAIMS` allows a separately authorized manager to cancel or reduce a
tracked surviving claim without holding the permission that created it. It
cannot:

- create a claim;
- increase its face value or remaining exposure;
- extend its expiry or exercise window;
- change its asset, beneficiary, spender, or recipient;
- turn a revocable object into an irrevocable one; or
- act on an unknown, unenumerated, or externally unverifiable authority type.

Every revocation action requires an exact action ID and must bind the claim ID,
claim type, manager/epoch attribution, beneficiary, pre-action exposure,
requested reduction, and wallet-observed post-action exposure. Security-
critical partial failure is not caught; the entire same-chain revocation
reverts atomically.

The owner selects a bounded revocation-source set for each revoker:

```text
(revokerManager, revokerEpoch)
    -> allowed (sourceManager, sourceEpoch) pairs
```

The revoker may act only on claims attributed to those exact source pairs.
Owner-, security-, or system-created claims are never reachable through
delegated revocation. An empty source set means none, not any. Only the owner
may add or remove source pairs; neither the revoker nor a source manager may
expand the scope. Epoch binding prevents an ejected and later re-added address
from inheriting stale revocation authority.

The package must also define cancellation notice, reliance versus unilateral-
right semantics, cancellation fees, frequency limits, manager-ejection
behavior, and bounded source-set storage. Until the inventory and anti-griefing
package is ratified, `REVOKE_CLAIMS` remains outside
`SUPPORTED_PERMISSION_MASK` and is not grantable.

### 4.7 Deliberately not initial permissions

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
managerPolicyScopeCodes[manager]    -> asset / Lego / payee ScopeCode
globalPolicyScopeCodes              -> asset / Lego / payee ScopeCode
```

The exact packing and bounds remain Phase 0B measurement outputs. The semantic
codes are fixed by §7.4 and cannot be reinterpreted to save storage.

### 5.2 Fixed checks

At every Config path that creates or updates a routed grant:

```text
require newManagerMask & ~SUPPORTED_PERMISSION_MASK == 0
require newGlobalMask & ~SUPPORTED_PERMISSION_MASK == 0
```

The check occurs when the authority is stored, not only when it is exercised.
Otherwise an unsupported bit can exist as dormant pre-granted authority and
silently become live when a later release expands `SUPPORTED_PERMISSION_MASK`.

For every manager-routed execution:

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
- the manager and global asset, Lego, and payee scope codes, paired with the
  existing bounded policy-set data; and
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

The direct `else: return True` fallback in
[`Sentinel.vy`](../../contracts/core/walletBackpack/Sentinel.vy) is a real
fail-open behavior, but fixing it requires an explicit legacy disposition
because the presently reachable fallthroughs include the direct ETH/WETH
transforms. Treat it as an immediate, independent hardening workstream rather
than waiting for the Wallet v3 release. The owner has classified wrapping and
unwrapping as exchanges and selected `canBuyAndSell` for both known transforms.
The final unknown-action default becomes `False`.

This disposition authorizes the product semantics in the decision record; it
does not by itself authorize a contract edit or deployment. The legacy
hardening package still needs explicit implementation authorization plus direct
regression tests for every current `ActionType`. Wallet v3 routed authorization
always rejects an unknown action or mask.

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
    YIELD_EXIT | YIELD

yield.rebalance.with-swap.v1
    YIELD_EXIT | YIELD | TRADE
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

## 7. Limits, composites, and reduction authority

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

### 7.2 Family-specific exit and reduction permissions

The owner selected three permanent authorities:

```text
YIELD_EXIT
DEBT_REDUCE
LIQUIDITY_EXIT
```

They may share proof helpers, argument-binding patterns, and AUTH machinery, but
they do not grant one another. The exact action-ID gate narrows each family
further.

#### `YIELD_EXIT` and `LIQUIDITY_EXIT`

These are recovery-shaped permissions. The wallet may withdraw or remove an
existing wallet-owned position only when:

- the action references an existing position in the matching family;
- every `receiver`, `beneficiary`, `owner`, and `onBehalfOf` parameter is bound
  to the wallet where applicable;
- all proceeds and residual assets return to the wallet; and
- no new or enlarged position is hidden inside the exit.

`YIELD_EXIT` cannot remove liquidity, and `LIQUIDITY_EXIT` cannot withdraw a
yield position, even if the manager holds an exact action ID from the other
family.

#### `DEBT_REDUCE`

This is an obligation-reduction spend permission. The wallet may spend an exact
allowed asset to reduce an existing wallet-owned obligation only when:

- the destination is the pinned protocol integration, not an arbitrary
  recipient;
- the wallet is the bound debtor, beneficiary, or `onBehalfOf` account;
- the spend is bounded by the wallet's current outstanding obligation and all
  applicable manager/global limits;
- wallet-computed postconditions prove that debt, risk, or liquidation
  exposure improves; and
- no third party receives an independent benefit.

Repayment and collateral top-up qualify only through this proof. Adding
collateral to create a fresh position, enlarge exposure, or fund an unbound
account is not `DEBT_REDUCE`; it requires `DEBT` or remains unsupported.

#### Shared implementation rules

Every family-specific exit or reduction also requires:

- an existing wallet-owned position or obligation in the matching family;
- no new position, obligation, signature, recipient right, surviving approval,
  operator right, or other persistent authority created by the family
  exit/reduction permission alone;
- the ordinary exact transaction-scoped ERC20 capability to be cleaned during
  settlement;
- any required external operator access to use an exact named AUTH shape that
  is either created and removed transactionally under its separately approved
  lifecycle or already established, inventoried, and approved for continued
  use;
- a separate `TRADE` permission and independently enforced slippage/value
  controls for any conversion leg; and
- frequency and fee/value-destruction bounds that prevent exit or reduction
  churn from becoming a griefing path.

If neither an approved transaction-scoped AUTH shape nor the required tracked
pre-established state is available, the action rejects. It cannot invoke the
legacy generic target-and-ABI helper or silently create a new persistent right.
Any future manager operation that creates persistent operator authority needs a
distinct action ID and the separately ratified persistent-authority boundary;
none of the three family permissions is sufficient.

AUTH remains integration/action specific. An exit that requires no operator
access does not wait for unrelated AUTH work. In contrast, the current
[`RipeLego.vy`](../../contracts/legos/RipeLego.vy) returns its one-argument
`setUndyLegoAccess(address)` request whenever access is absent without branching
on the action. Its repayment and collateral-top-up actions therefore cannot
become routed `DEBT_REDUCE` actions until that Ripe authority shape and
lifecycle have passed AUTH.

If the wallet cannot prove the applicable family-specific rules, the action:

- requires the corresponding entry/risk-increasing family bit as well;
- remains owner-only; or
- is unsupported.

Removing collateral is not a reduction action. It requires `DEBT`.

### 7.3 Price behavior

Missing, zero, stale, unsupported, or invalid price data must never make a
charged action look free.

Each compiled settlement recipe has one closed price code:

```text
PRICE_REQUIRED          = 0
NATIVE_BOUNDED_RECOVERY = 1
```

`PRICE_REQUIRED` is the default. Missing, zero, stale, unsupported, or invalid
price data rejects.

The owner selected `NATIVE_BOUNDED_RECOVERY` only for specifically reviewed
recovery recipes. Eligibility requires all of the following:

- the action is a pure `YIELD_EXIT` or `LIQUIDITY_EXIT`;
- no `TRADE`, `TRANSFER`, `PAY_NETWORK_FEES`, `PAYMENT_COMMITMENT`, or
  risk-increasing permission is present;
- no conversion, bridge, third-party payment, debt spend, or new persistent
  effect occurs;
- every receiver, beneficiary, and residual destination is wallet-bound;
- manager/global action- and asset-specific native-unit ceilings apply;
- wallet-observed source-position reduction and returned-asset deltas prove the
  fixed recovery postconditions;
- same-asset minimum-return and frequency/fee-destruction rules bound bad
  execution and griefing; and
- settlement and events use the explicit native-bounded recipe rather than
  recording a zero USD value as if valuation succeeded.

Changing an existing action from `PRICE_REQUIRED` to
`NATIVE_BOUNDED_RECOVERY`, or the reverse, changes its meaning and requires a
new action ID. The extender cannot select the price code at runtime.

`DEBT_REDUCE`, deleverage, swaps, fee-paying variants, and any action whose
proof depends on USD valuation remain `PRICE_REQUIRED` unless a later owner
decision approves a different exact recipe. If any eligibility proof is
missing, the recovery action rejects.

### 7.4 Explicit Wallet v3 scope codes

Wallet v3 does not infer authority from an empty asset, Lego, or payee list.
Each manager and global policy set carries a closed scope code:

```text
NONE = 0
SET  = 1
ANY  = 2
```

The rules are fixed:

- `NONE` requires an empty list and admits nothing;
- `SET` requires a nonempty bounded list and admits only exact members;
- `ANY` requires an empty list and deliberately admits any member at that
  policy dimension;
- unknown codes reject;
- transitions clear or populate the associated list atomically; and
- manager and global scopes apply cumulatively, so one `ANY` never overrides
  the other layer's `NONE` or `SET`.

Requiring empty lists for `NONE` and `ANY` prevents hidden stale entries from
becoming live after a mode change. Owner-facing Config expansion and events
must display the code and exact `SET` members.

Routed action IDs deliberately do not use these codes:

```text
empty action-ID set == no routed actions
no ANY action-ID mode
```

This preserves the rule that a newly registered action never enters an existing
manager grant automatically.

Existing deployed-wallet direct behavior remains unchanged. Phase 0B must
compile and measure the new Wallet v3 Config, provider, `PolicyContextV1`, and
Sentinel representation before implementation proceeds.

---

## 8. Persistent effects and payments

### 8.1 Phase 1 creates no new delegated authority or administrative object

The first yield deposit creates a wallet-owned position represented through the
fixed yield settlement and entry/exit metadata. The owner selected a hard
Phase 1 boundary: it does not create or activate:

- a standing token allowance;
- an offchain signature;
- a bridge message;
- a third-party pull;
- a new payee;
- delegated claim-revocation scope;
- a new payment-commitment type;
- a stream or subscription; or
- a reusable external operator right.

`ENROLL_PAYEE`, `REVOKE_CLAIMS`, `PAY_NETWORK_FEES`, `CROSS_CHAIN`,
`OFFCHAIN_SIGNATURE`, and `PERSISTENT_EXTERNAL_AUTHORITY` remain outside the
Phase 1 `SUPPORTED_PERMISSION_MASK`. Assignment in the durable vocabulary does
not make a bit grantable. After the core Phase 1 action is integrated and
ratified, each deferred capability still requires its own owner-approved
package and evidence gate.

The named operator-authority package remains separate and adds only confirmed,
fixed call shapes.

No categorical action permission bypasses that boundary. This applies to
`DEBT`, `DEBT_REDUCE`, `YIELD_EXIT`, `LIQUIDITY_EXIT`, and `REWARDS`, not only
to risk-increasing actions. The current Ripe integration requests
`setUndyLegoAccess(address)` without branching on the debt action, while
[`Euler.vy`](../../contracts/legos/yield/Euler.vy) exposes a
`toggleOperator` setup call for rewards. A manager's action-permission bit alone
must never create either authority.

A concrete action becomes enabled only after the named AUTH package has
classified the integration/action pair and supplied its required operator
lifecycle. A permission may then use a transaction-scoped named AUTH shape or
an approved, tracked existing right as §7.2 defines. If authority survives the
transaction, its inventory, attribution, suspension, and cleanup semantics
require the reserved persistent-authority boundary or an equally explicit
owner-approved design.

AUTH is an implementation and authority-lifecycle package, not another
owner-facing action permission. Completing AUTH never grants a manager the
dependent financial action: the exact `actionId`, every required categorical
bit, existing policy, and limits still apply independently.

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

`ENROLL_PAYEE` creates a surviving wallet-internal recipient configuration, not
an external spender/operator right and not a payment claim. Its own permission
and lifecycle gate that effect; it does not consume
`PERSISTENT_EXTERNAL_AUTHORITY` or `PAYMENT_COMMITMENT`. The package must still
satisfy every applicable inventory, attribution, expiry, suspension, ejection,
and bounded-enumeration rule below.

`REVOKE_CLAIMS` is the distinct reduction authority for tracked surviving
claims. It does not require the claim-creation permission, because forcing the
same compromised manager authority to cancel what it created would defeat the
separation. The owner-designated, epoch-bound source set supplies the exact
cross-manager scope; anti-griefing and revocability rules still apply per claim
type.

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

### 9.0 Immediate independent legacy hardening decision

Do not wait for the Wallet v3 release to disposition Sentinel's direct
unknown-action fallback. Open a separately authorized, narrowly scoped legacy
hardening package:

1. enumerate every current `ActionType` and its intended direct permission;
2. add explicit ETH-to-WETH and WETH-to-ETH branches that require
   `canBuyAndSell`, as selected by the owner;
3. change the unknown default to `False`;
4. add positive and negative regression tests for every current action type,
   including both transforms with and without `canBuyAndSell` and an unknown or
   future value; and
5. request separate authorization before editing or deploying the legacy
   contract.

This workstream is independent of the Wallet v3 routed implementation and does
not authorize a contract edit in this documentation task. The product question
is closed: both transforms are exchanges and require `canBuyAndSell`.

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
- compile and measure manager/global asset, Lego, and payee scope-code storage;
- include both masks, the exact required mask, and all six manager/global scope
  codes in `PolicyContextV1`;
- keep existing manager structs and direct policy entry points unchanged;
- measure Config, provider, Sentinel, and HighCommand size and gas;
- define the supported-mask constant and unknown-bit failure;
- define the exact initial action mask;
- define the first composite charge bases;
- compile and measure the closed price codes plus manager/global native-unit
  recovery ceilings and distinct accounting/event behavior;
- define the shared recovery-exit and obligation-reduction proof templates,
  while preserving separate permission checks for `YIELD_EXIT`,
  `DEBT_REDUCE`, and `LIQUIDITY_EXIT`;
  and
- record `PROCEED`, `PROCEED NARROWER`, `REDESIGN`, or `STOP`.

### 9.3 Phase 1A — ActionRegistry

Add tests that:

- the exact static required mask is immutable;
- a required zero mask rejects;
- unknown bits reject;
- different permission variants use different action IDs;
- a new extender uses a new action ID;
- each action's compiled settlement recipe fixes its price code, and changing
  that code requires a new action ID;
- a new action never expands an existing manager grant; and
- no generic persistence or runtime permission field exists.

### 9.4 Phase 1B1 — Config and ActionDataProvider

Implement and measure:

- the bounded manager action-ID set;
- the parallel routed manager mask;
- the routed global mask;
- manager/global asset, Lego, and payee scope codes with structural validation
  (`NONE`/`ANY` require empty; `SET` requires nonempty);
- duplicate and unknown-bit rejection at every grant create/update path;
- rejection of manager/global masks outside `SUPPORTED_PERMISSION_MASK`, so
  dormant pre-granted bits cannot activate in a later release;
- action-ID addition checks;
- full `PolicyContextV1` forwarding; and
- unchanged legacy manager structs and direct provider behavior.

### 9.5 Phase 1B2 — Sentinel and HighCommand

Implement and measure:

- cumulative manager/global routed-mask checks;
- cumulative manager/global scope-code and exact-`SET` membership checks;
- exact action-ID gate coordination;
- unknown-bit, unknown-scope-code, and unsupported-action failure;
- separate direct and routed entry points;
- no first-match `if / elif` behavior for masks; and
- no new generic policy evaluator.

The direct fallback is handled by the independent §9.0 workstream. It is not
silently changed through the routed entry point or deferred merely because
Wallet v3 is not yet released.

### 9.6 Phase 1C — first yield-deposit slice

The first action requires only:

```text
YIELD
```

It proves:

- exact action-ID approval;
- manager and global mask checks;
- explicit manager/global asset and Lego scope-code checks plus existing
  opportunity policy;
- approved opportunity is checked before capability activation on the routed
  path even though the current direct path can safely revert after an atomic
  deposit;
- exact capability;
- fixed yield settlement;
- valid price behavior;
- allowance cleanup; and
- no new persistent external authority.

### 9.7 Later action-family packages

- Inventory required operator access per integration/action pair before enabling
  any later family action. A nonempty requirement must pass AUTH first; an
  action that needs no external operator access does not wait for unrelated
  AUTH work.
- Yield withdrawal uses `YIELD_EXIT`; an exact eligible no-conversion variant
  may use `NATIVE_BOUNDED_RECOVERY`.
- Yield rebalance uses `YIELD_EXIT | YIELD`, plus `TRADE` when applicable.
- Debt repayment and collateral top-up use `DEBT_REDUCE` only when they
  bind an existing wallet obligation and the action-specific postcondition
  proof passes; a fresh or expanding collateral position requires `DEBT`.
  Ripe variants also wait for the approved one-argument Ripe AUTH shape.
- Borrow and collateral removal use `DEBT`.
- Liquidity removal uses `LIQUIDITY_EXIT`; an exact eligible no-conversion
  variant may use `NATIVE_BOUNDED_RECOVERY`.
- Claim-only uses `REWARDS`, but any integration-required operator setup must
  first pass the AUTH/persistent-authority package; claim-and-sell adds
  `TRADE`; claim-and-redeposit adds `YIELD`.
- Any future wallet-funded fee variant adds `PAY_NETWORK_FEES` to its parent
  mask, uses a distinct action ID from the non-fee variant, and remains
  ungrantable until the bounded fee package is approved.
- Any future manager payee-enrollment action requires `ENROLL_PAYEE`, creates
  only the typed probationary object, and remains ungrantable until its complete
  lifecycle package is approved. Payment to that payee remains separate and
  requires `TRANSFER`.
- Any future claim-revocation action requires `REVOKE_CLAIMS`, can only reduce
  a typed inventoried claim from an owner-designated, epoch-bound source
  manager, and remains ungrantable until reliance and anti-griefing rules are
  approved.
- Payments map `TRANSFER` and `PAYMENT_COMMITMENT` onto direct rails before any
  routing comparison.
- Later and reserved bits require their own owner-approved packages.

---

## 10. Proposed governing-document changes after approval

If this decision record is approved, update the governing architecture in one
focused revision:

1. Replace section 5.1's provisional list with the approved bit table.
2. Add the parallel routed-mask and explicit asset/Lego/payee scope-code
   representation plus the direct/routed compatibility boundary.
3. State that `ActionSpec.requiredPermissionMask` is exact and solely
   registry-defined.
4. Add the separate `YIELD_EXIT`, `DEBT_REDUCE`, and `LIQUIDITY_EXIT`
   permissions, their shared proof templates, family-specific fund-flow rules,
   and integration/action-specific AUTH prerequisites.
5. Strengthen composite policy from permission union to permission union plus
   cumulative limits.
6. Add the closed `PRICE_REQUIRED` and `NATIVE_BOUNDED_RECOVERY` recipe codes,
   exact eligibility rules, native ceilings, distinct accounting/events, and
   new-action-ID requirement for a code change.
7. State that permission meanings and bit positions are immutable and never
   reused.
8. Add mask and manager/global scope-code fields to the `PolicyContextV1`
   definition.
9. Record the rejected initial categories, the additive
   `PAY_NETWORK_FEES` boundary, the non-paying `ENROLL_PAYEE` boundary, and
   the reduction-only `REVOKE_CLAIMS` boundary, plus future package boundaries.
10. Add governing invariants and map each new invariant to implementation
    packages and tests.

Update the implementation roadmap in the same revision:

1. replace the generic Phase 0B permission decision with this exact decision
   record and its disposition;
2. add Phase 0A permission and price baselines;
3. add mask and scope-code measurements and fields to Packages 0B, 1B1, and
   1B2;
4. set the first yield action's exact mask;
5. add the family-specific exit/reduction permission, proof, and
   integration-specific AUTH gates before withdrawals, liquidity removal, or
   defensive debt;
6. add price-code, native-recovery-limit, and no-zero-USD-accounting evidence;
7. add composite charge-basis evidence;
8. keep payment/persistence and dual control in separate future packages; and
9. extend invariant traceability and drift tests.

The website should be updated only after the governing Markdown changes. Until
then, this proposal remains a review input rather than presented architecture.

---

## 11. Owner decisions

The research narrows the permission problem to these decisions.

| # | Decision | Recommendation |
|---:|---|---|
| P1 | Durable taxonomy | Approve twelve initial-vocabulary, four later, and one reserved boundary; activate them only through reviewed enforcement packages |
| P2 | Representation | Use parallel `uint256` manager/global routed masks in the new Config; do not expand existing manager structs |
| P3 | Family-specific reduction authority | **OWNER SELECTED 2026-07-25:** use separate `YIELD_EXIT`, `DEBT_REDUCE`, and `LIQUIDITY_EXIT` permissions; reuse proof/AUTH machinery without generalizing the grants |
| P4 | Action permission semantics | One immutable exact static mask per action ID; no runtime extender permission declaration |
| P5 | Direct-path fallback | **OWNER SELECTED 2026-07-25:** ETH/WETH transforms require `canBuyAndSell`; the unknown default fails closed; implementation and deployment remain separately gated |
| P6 | Empty policy sets | **OWNER SELECTED 2026-07-25:** Wallet v3 uses `NONE=0`, `SET=1`, and `ANY=2` for manager/global asset, Lego, and payee scopes; action IDs remain exact-only; legacy direct behavior is unchanged |
| P7 | Price-independent exits | **OWNER SELECTED 2026-07-25:** allow exact `NATIVE_BOUNDED_RECOVERY` recipes only for eligible pure no-conversion `YIELD_EXIT`/`LIQUIDITY_EXIT` actions; default remains `PRICE_REQUIRED` |
| P8 | First persistent additions | **OWNER SELECTED 2026-07-25:** Phase 1 creates only the expected wallet-owned yield position; keep `ENROLL_PAYEE`, `REVOKE_CLAIMS`, network fees, standing authority, signatures, bridges, and new commitment types ungrantable until later packages |
| P9 | Network-fee authority | **OWNER SELECTED 2026-07-25:** use separate `PAY_NETWORK_FEES`, additive to the parent action and ungrantable until a bounded fee package exists |
| P10 | Payee enrollment | **OWNER SELECTED 2026-07-25:** use separate `ENROLL_PAYEE`; it creates only bounded probationary enrollment and is ungrantable until its lifecycle package exists |
| P11 | Claim revocation | **OWNER SELECTED 2026-07-25:** include separate reduction-only `REVOKE_CLAIMS`; keep it ungrantable until typed claim inventory, reliance, and anti-griefing rules exist |
| P12 | Revocation scope | **OWNER SELECTED 2026-07-25:** each revoker receives a bounded owner-designated set of source-manager/epoch pairs; owner/system claims remain unreachable |

P3, P5–P12 are owner-selected. P4 preserves an already governing
action-identity rule. P1–P2 remain open decisions this research most directly
informs.

---

## 12. Reviewer checklist

The independent reviewer should answer:

1. Does the twelve-permission initial vocabulary omit an authority that cannot
   be represented safely by action ID plus existing policy?
2. Do `YIELD_EXIT`, `DEBT_REDUCE`, and `LIQUIDITY_EXIT` give meaningful
   family-specific owner control without duplicating procedural action IDs?
3. Does keeping self-custody transforms under `TRADE` create unacceptable
   owner-consent ambiguity?
4. Does `ENROLL_PAYEE` remain strictly non-paying, probationary, attributable,
   expiring, exposure-bounded, and separately removable?
5. Do the parallel mask and scope codes avoid unacceptable ABI/bytecode churn
   once exact Config/provider/Sentinel interfaces are sketched?
6. Are any mask or manager/global scope-code fields missing from
   `PolicyContextV1`?
7. Is the composite gross-charge rule precise enough to prevent swap-mediated
   limit laundering without a general effect language?
8. Are the family-specific exit/reduction postconditions wallet-observable for
   the first yield, debt, and liquidity integrations?
9. Does rejecting a generic `persistenceMask` leave any first-phase effect
   unclassified?
10. Are every deferred payment, enrollment, revocation, network-fee,
    persistence, signature, bridge, and dual-control package absent from the
    Phase 1 supported mask and separated behind its own evidence gate?
11. Do any recommendations accidentally change current direct-wallet behavior?
12. Which owner decisions must be settled before Phase 0B rather than at a
    later family gate?
13. Does every Config create/update path reject manager and global masks outside
    the current `SUPPORTED_PERMISSION_MASK`, preventing dormant future grants?
14. Does each proposed rewards integration/action pair require a named AUTH
    shape or tracked persistent operator right, and is that prerequisite
    complete before `REWARDS` becomes grantable?
15. Does owner-facing `YIELD` consent make clear that exit requires the separate
    `YIELD_EXIT` authority?
16. Does each proposed yield-exit, debt-reduction, or liquidity-exit
    integration/action pair require a named AUTH shape, and if so is that
    prerequisite complete before that family permission becomes grantable?
17. Does every fee-paying action require both its complete parent mask and
    `PAY_NETWORK_FEES`, use a distinct action ID, bind the fee mechanism and
    recipient, and enforce absolute/proportional caps?
18. Does every payment to a manager-enrolled payee independently require
    `TRANSFER`, the exact payment action ID, ordinary recipient policy, and the
    payee's remaining probationary limits?
19. Does `REVOKE_CLAIMS` only reduce a typed inventoried claim, preserve
    beneficiary and asset identity, fail atomically, and require the exact
    owner-designated revoker/source manager epochs plus anti-griefing rules?
20. Do `NONE`, `SET`, and `ANY` validate their list shapes, combine manager and
    global scopes cumulatively, reject unknown codes, and remain unavailable
    for routed action-ID grants?
21. Does every `NATIVE_BOUNDED_RECOVERY` action use an immutable eligible
    no-conversion yield/liquidity-exit recipe, enforce native ceilings and
    wallet-observed recovery postconditions, avoid zero-USD accounting, and
    receive a new action ID if its price code changes?

The reviewer should verify claims against the live contracts and the governing
architecture, not treat either research synthesis as authority.

---

## 13. Revision log

| Date | Revision | Effect |
|---|---|---|
| 2026-07-25 | Initial proposal | Synthesized the two permission-research reports into a smaller, non-governing recommendation |
| 2026-07-25 | Reviewer-feedback revision | Renamed `POSITION_EXIT` to `POSITION_REDUCE`; separated recovery and obligation-reduction fund flows; added grant-time supported-mask checks, reward/AUTH sequencing, explicit one-way `YIELD` consent, an immediate independent Sentinel hardening workstream, clearer vocabulary-versus-enforcement status, and document provenance |
| 2026-07-25 | Re-review AUTH and fast-path clarification | Added integration/action-specific AUTH prerequisites for `DEBT` and `POSITION_REDUCE`; distinguished transaction-scoped versus pre-established named operator authority; documented Ripe's dependency; made the behavior-preserving Sentinel fix the recommended independent fast path; and stated the Claude synthesis's considered network-fee position fairly |
| 2026-07-25 | Owner disposition P5 | Owner classified ETH/WETH wrapping and unwrapping as exchanges requiring `canBuyAndSell`; unknown direct actions fail closed; contract implementation and deployment remain separately gated |
| 2026-07-25 | Owner disposition P3 | Replaced the proposed cross-family `POSITION_REDUCE` bit with separate `YIELD_EXIT`, `DEBT_REDUCE`, and `LIQUIDITY_EXIT` permissions; retained shared proof and AUTH machinery while keeping the owner grants distinct |
| 2026-07-25 | Owner disposition P9 | Added `PAY_NETWORK_FEES` as a separate durable permission that is additive to the parent action and ungrantable until recipient binding and fee caps are implemented |
| 2026-07-25 | Owner disposition P10 | Added `ENROLL_PAYEE` as a separate durable non-payment permission for attributable, expiring, exposure-bounded probationary enrollment; left it ungrantable until its lifecycle package exists |
| 2026-07-25 | Owner disposition P11 | Confirmed separate reduction-only `REVOKE_CLAIMS`; left it ungrantable until typed inventory, attribution scope, reliance, cancellation-cost, and anti-griefing rules are approved |
| 2026-07-25 | Owner disposition P12 | Scoped delegated claim revocation to bounded owner-designated source-manager/epoch pairs per revoker/epoch; excluded owner, security, and system claims and stale authority after manager re-addition |
| 2026-07-25 | Owner disposition P6 | Selected explicit Wallet v3 scope codes `NONE=0`, `SET=1`, and `ANY=2` for manager/global assets, Legos, and payees; kept routed action IDs exact-only and legacy direct semantics unchanged |
| 2026-07-25 | Owner disposition P7 | Selected exact immutable `NATIVE_BOUNDED_RECOVERY` recipes for eligible pure no-conversion `YIELD_EXIT` and `LIQUIDITY_EXIT` actions; retained `PRICE_REQUIRED` as the default and prohibited zero-USD fallback accounting |
| 2026-07-25 | Owner disposition P8 | Kept Phase 1 limited to the core routed architecture and expected wallet-owned yield position; left enrollment, revocation, network fees, standing authority, signatures, bridges, and new commitment types ungrantable until separate later packages |
