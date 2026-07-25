# User Wallet v3 — Production Design Plan

> **Archive notice (2026-07-24):** This PoC-derived production track is
> superseded by the separately selected Wallet v3 architecture. Its historical
> approval applied only to that earlier Phase 0 working contract; it does not
> authorize current implementation. See the [archive index](README.md) and the
> [current Wallet v3 documents](../../wallets-v3/README.md).

**Status:** APPROVED as the Phase 0 working contract on 2026-07-23

**Kickoff roles:** The owner also holds product, operations, and named human
security-review responsibility. The design/implementation analyst prepares the
analysis. The separate reviewer agent provides independent Phase 0 challenge.
Independent external review remains required before any audit freeze or
production deployment.

**Owner approval record:** The owner explicitly answered “yes I approve” on
2026-07-23 after reviewing the Phase 0 authorization, reviewer-separation, and
staffing questions.

**PoC baseline:** User Wallet v3 Lean PoC at commit `8febc243b9d7`

**Inputs:**

- [Lean PoC Architecture](user-wallet.md)
- [Lean PoC Implementation Guide](implementation-guide.md)
- [Lean PoC Results](POC_RESULTS.md)
- Independent implementation and evidence reviews completed after the PoC

### Change disclosure after plan convergence

- The D4a↔D2 paragraph in §4.3 was added during reviewer-driven convergence to
  make the recoverability-versus-authority dependency explicit. It was
  disclosed in that revision's owner handoff.
- After owner approval, only the status, kickoff roles, and approval record were
  added before Phase 0 analysis began.
- The first Phase 0 independent challenge then required one roadmap
  clarification: evaluating a bounded successor escape pulls a minimal
  successor-deployment/address-attestation trust design into Phase 0. Production
  factory implementation remains downstream.
- No post-convergence edit authorizes contract implementation, changes the PoC,
  or relaxes an architecture scope-stop.

## 1. Executive decision

The Lean PoC is complete and successful within its stated scope. It supports
continuing with the architecture, but it does not authorize production
deployment or freeze an ABI, storage layout, trust model, or product surface.

The production-design direction is:

- **Keep the architectural trunk:** permanent non-proxy custody, direct
  replaceable wallet-bound Config, append-only typed attachments, pinned
  dependencies, one bounded capability, exact token/effect bounds, named
  fixed-authority primitives, selector-bounded `DRAIN_ONLY`, wallet-held
  reservations, and terminal commitment non-reuse.
- **Redesign the expensive or underspecified branches:** routed-session
  overhead, payment-commitment creation, Lego governance and containment,
  owner/emergency policy, payment liveness, dependency failure, and production
  lifecycle behavior.
- **Do not infer what the PoC did not prove:** production readiness, safe
  arbitrary execution, general signatures or callbacks, full x402/MPP
  compliance, real Ripe/Morpho safety, or a frozen permanent-core interface.

The next step is a production design phase with explicit owner and security
gates. The PoC contracts remain an evidence artifact; they are not incrementally
promoted into production code.

### 1.1 Irreversible launch rule

**No production permanent-core bytecode may hold real user funds until D2 is
resolved and explicitly accepted by the owner and security reviewers.** This
applies to every release shape, including Candidate A's custody/transfer-only
trunk.

D2 must state what happens after a critical immutable-core defect: which
onchain recovery remains possible, whether users must migrate, which wallet-keyed
positions or identity guarantees would be lost, and which irreducible risk is
being accepted. “The core is immutable” is not an answer.

The owner/emergency-authority shape in D4 must be decided early enough to inform
D2 and the permanent-core state map. Disposable local, fork, and testnet
deployments may support design evidence, but they must not be represented as
production candidates or entrusted with real user funds before this gate.

### 1.2 Owner review snapshot

The immediate work is:

1. Define the owner, manager, emergency, and recovery shape that the immutable
   core may need.
2. Resolve the critical-core-defect/evolution posture and its honest limits.
3. Name a provisional first-release composition using actual product needs and
   transaction mix, then ratify or revise it from Phase 0 evidence.
4. Build the adversary matrix, including hostile Legos, sponsor griefing, and
   reservation-locking attacks.
5. Decompose gas and sponsor cost before setting product-derived budgets.
6. Run only the real protocol, rail, and offchain spikes required by the
   proposed first release.

The owner decision surface is:

| Decision | Question |
|---|---|
| D1 | Which composition should graduate as the first release? |
| D2 | What can and cannot happen after a permanent-core defect? |
| D3 | How are Legos contained, approved, monitored, succeeded, and revoked? |
| D4 | What owner/manager/emergency authority exists, and how are keys operated? |
| D5 | Which gas and sponsored-fee budgets are economically acceptable? |
| D6 | Which payment rails and liveness guarantees ship first? |
| D7 | Which token behaviors are supported or rejected? |
| D8 | Which real protocols and protocol authorities ship first? |
| D9 | What is the audit scope and what launch limits apply? |
| D10 | How do relaying, sponsorship, facilitation, indexing, and sync operate safely? |

No decision is silently inherited from the PoC.

### 1.3 Parallel tracks and provisional timeboxes

The numbered phases are evidence-maturity gates, not a requirement that every
workstream finish serially before any narrower workstream advances.

| Track | May advance when | Must not outrun |
|---|---|---|
| Custody trunk | D2, the D4 authority/emergency shape, D5, D7, applicable D10 controls, and the permanent-core future-family exercises are accepted | Permanent-core gate, frozen trunk specification, verification, and narrow audit |
| Protocol integrations | Target protocol is selected under D8 and its D3 trust/containment model is accepted | Per-adapter real-integration, exit, mutation, and audit evidence |
| Payment rails | Rail is selected under D6 and its D10 offchain/sponsor model is accepted | Complete liveness, reservation, griefing, and rail-specific audit evidence |
| Broader governance/operations | Authority and dependency scope is known | D2/D4/D10, incident rehearsal, and launch controls |

A narrow custody track may move toward its own specification and audit while
unselected Lego and payment work continues. It cannot bypass D2 merely because
its surface is small. Likewise, success on the trunk does not graduate an
integration track.

At kickoff, calibrate the planning budgets to actual staffing. If product,
protocol, operations, and security roles are held by one or two people, the
tracks remain logically independent but their calendar execution becomes
partly or fully serial. The timeboxes below are effort budgets for the applicable
release slice, not an assumption that every role is independently staffed.

- **Shared foundation:** 3–5 working days to name a provisional D1 candidate,
  frame the D4 authority/emergency
  shape, the D2 defect cases, D7, D10, and the bounded spike list.
- **Candidate A evidence:** 5–10 working days for permanent-core future-family
  exercises, D2/D4 analysis, the real direct-token path, and applicable
  sponsor/offchain evidence.
- **Candidate B increment:** 5–10 working days for the one selected rail,
  including offchain, liveness, reservation-lock, and sponsor-griefing evidence.
- **Candidate C increment:** 5–10 working days per selected protocol family,
  including real integration, callback, exit, and Lego-containment evidence.
- **Candidate D evidence:** the scoped sum of its A/B/C slices; it does not
  inherit a single global 10-day spike budget.
- **Phase 0 decision package:** 2–3 working days to synthesize evidence and
  record the slice-specific disposition.
- **Narrow production specification:** 5–10 working days after the applicable
  Phase 0/1 gates pass.

These are anti-stall timeboxes, not delivery estimates. Phase 3 implementation,
external-audit scheduling, and launch timing are estimated only after D1 fixes
the release surface and staffing. Each named slice may receive at most one
owner-approved 5-working-day extension for a specific unresolved hypothesis.
When a timebox expires, the result is `PROCEED`, `PROCEED NARROWER`, `REDESIGN`,
or `STOP`—not an unbounded design extension.

### 1.4 Existential stop conditions

Phase 0 should concentrate first on the two findings that can invalidate a
load-bearing architectural premise:

1. **Permanent-core failure:** D2 has no owner- and security-acceptable answer
   for a critical immutable-core defect. This stops the permanent-custody
   architecture; it is not a branch-level optimization problem.
2. **Typed-integration failure:** useful selected protocol actions cannot be
   bounded without an arbitrary executor, unbounded authority, or equivalent
   expansion of the Lego trust boundary. This stops that integration and, if
   the intended product depends on it, the typed-extender product architecture.
   It does not by itself disprove a narrower custody-only trunk.

The primary design lever connecting D4a to D2 is the smallest pause, escape, or
recovery authority placed in the immutable core. Too little may make critical
defects unrecoverable; too much may turn the emergency authority into the
largest custody risk. Phase 0 must resolve that recoverability-versus-authority
trade explicitly rather than treating purity or emergency power as inherently
safer.

## 2. What the PoC established—and what it did not

### 2.1 Evidence classification

Every production decision must label its supporting evidence as one of:

- **Demonstrated:** directly exercised by the PoC's targeted tests or measured
  by its reproducible harness.
- **Modeled:** exercised against a representative mock or deterministic
  fork-time model whose production behavior is not yet established.
- **Assumed:** intentionally inside the trust model or outside the PoC scope.
- **Unresolved:** requires a design decision or new evidence before production.

| Claim | Classification | Production interpretation |
|---|---|---|
| One wallet address retains custody through Config replacement and extender succession | Demonstrated with representative assets and positions | Keep the stable-custody model; validate storage and real integrations before freezing it |
| A broken operational Config can be replaced without its cooperation | Demonstrated | Keep direct IDLE-only replacement; design compromised-owner and emergency policy |
| A malicious typed extender is contained by pinned routing and field/effect checks | Demonstrated, including mutation-sensitive adversarial evidence | Keep narrow typed primitives and their load-bearing checks |
| A malicious or buggy Lego is contained | Assumed false by the PoC trust model | First-class production threat-model problem |
| Old extenders can close wallet-keyed positions after succession | Demonstrated against representative debt mocks | Validate per real protocol and define stuck-position policy |
| Direct transfer is materially cheaper than v2 | Demonstrated as an architecture-overhead comparison | The relative result is strong; the absolute 51,337 figure is not a real USDC-proxy transfer claim |
| Base USDC EIP-3009 external exact pull works | Demonstrated against pinned Base state in a Boa overlay | Add live/fork compatibility and full rail lifecycle evidence |
| x402 sponsored fee is production cost evidence | Modeled | Re-price using production transaction construction and current product assumptions |
| Reserved-transfer settlement semantics work | Modeled | Not evidence of MPP wire-protocol compliance |
| Representative yield/debt behavior is safe | Modeled only by representative mocks | Select actual target protocols under D8, then require real integration and adversarial callback evidence |
| Fixed owner, reviewed Config, Legos, and payment helper are safe | Assumed | Requires a production authority, provenance, and incident-response design |
| The Base v2 comparator is reproducible | Demonstrated with the owner-approved BL-010 Boa overlay shim | Keep the result; revisit the shim when Boa or the fixture changes |

Passing Q1–Q8 means the architecture hypotheses passed the contracted PoC
evidence. It does not mean every production adversary or integration has been
covered.

### 2.2 Current economic evidence

| Scenario | PoC result | Current disposition |
|---|---:|---|
| Direct v3 transfer | 51,337 tx-equivalent gas | Keep |
| Paired v2 transfer | 511,975 tx-equivalent gas | Comparator |
| Empty routed session | 117,497 tx-equivalent gas | Profile and redesign |
| Direct yield control | 123,126 tx-equivalent gas | Control |
| Routed minimal yield | 292,025 tx-equivalent gas | Profile and redesign |
| x402 authorization | 543,981 tx-equivalent gas | Redesign creation path |
| x402 sync | 67,410 tx-equivalent gas | Accept only as PoC evidence |
| Reserved-transfer authorization | 352,399 tx-equivalent gas | Redesign creation path |
| Reserved partial settlement | 93,491 tx-equivalent gas | Accept only as PoC evidence |
| Reserved refund | 51,787 tx-equivalent gas | Accept only as PoC evidence |

The PoC's 60,000 empty-session target was provisional, not a product
requirement. Production targets must be derived from expected transaction mix,
sponsorship policy, Base fee/L1 data scenarios, and user value. Cost work begins
with decomposition, not optimization.

## 3. Non-negotiable design guardrails

These are the validated properties that production design should preserve unless
the owner explicitly reopens the architecture:

1. The wallet remains the persistent custodian and protocol identity.
2. No `delegatecall`, arbitrary target/calldata executor, or generalized wallet
   authority is introduced.
3. Extender routing remains typed, selector-bounded, attachment-specific, and
   dependency/codehash-pinned.
4. Every stateful frame acquires its execution phase before an external call.
5. Every economic effect is bounded by exact token loss, a typed semantic
   commitment, a named fixed-authority primitive, or an explicitly reviewed
   combination.
6. A LEGO or CORE route cannot settle successfully without consuming its one
   capability; capability reuse and nested sessions remain impossible.
7. Exact approvals are cleared before successful settlement, and reservations
   cannot be consumed by unrelated wallet actions.
8. Old-version behavior remains limited to exact reviewed exits.
9. Payment commitments cannot exceed, replay, or resurrect reserved authority.
10. Gas optimization may not remove or weaken a security check merely to meet a
    target. Any replacement mechanism must first establish equivalent evidence,
    including an adversarial or mutation-sensitive regression.

The PoC's `NONE` consumer path exists only to measure framework overhead. Phase
0 must decide whether it has any production use. The default production posture
is to omit measurement-only callable surface.

### Architecture scope-stop

Stop and request owner architecture review before implementing any proposal
that:

- Adds a proxy, `delegatecall`, arbitrary executor, general callback/signature
  perimeter, or unbounded target/calldata path.
- Makes the permanent core replaceable or gives an external component direct
  access to its storage.
- Weakens a pinned dependency, semantic/effect binding, phase transition,
  capability-consumption rule, exact approval, reservation, or terminal-state
  invariant.
- Expands the trust placed in an owner, manager, Config, extender, Lego, helper,
  settlement operator, token, or protocol without recording that change in the
  threat model.
- Freezes an ABI or storage scheme before the permanent-core evolution gate has
  passed.
- Treats modeled or assumed evidence as demonstrated production behavior.

## 4. Phase 0 — decisions before production implementation

Phase 0 changes no production contract. It produces the evidence and decisions
that determine whether the architecture should proceed unchanged, proceed with
a narrower initial release, be redesigned, or stop.

### 4.1 First-release composition decision

At the foundation kickoff, name one **provisional working candidate** to scope
the bounded evidence spikes. At the Phase 0 exit, D1 ratifies or revises that
candidate from the resulting evidence. The provisional choice is not launch
approval.

Evaluate at least these first-release compositions rather than assuming an
all-or-nothing launch:

| Candidate | First-release surface | Principal tradeoff |
|---|---|---|
| A — custody trunk | Permanent wallet, Config replacement, direct ERC-20 transfer | Smallest audit surface, but the immutable trunk may strand early users if later families require a different core |
| B — trunk plus one payment rail | Candidate A plus one fully specified payment lifecycle | Earlier payment value; adds liveness and rail trust |
| C — trunk plus one protocol family | Candidate A plus either yield or debt and exact exits | Proves real protocol identity; adds Lego and callback risk |
| D — combined first release | Selected transfer, payment, yield, debt, and succession slices | Broad utility; largest first audit and governance surface |

The comparison must include product need, expected call mix, sponsor economics,
audit scope, operational controls, migration constraints, and failure blast
radius. The owner selects the initial release only after the other Phase 0
deliverables make these costs explicit.

Candidate A may graduate only if the exact proposed trunk core has passed the
§4.4 future-family exercises for the next plausible payment and protocol
families. If those exercises require different immutable bytecode, Candidate A
is not a safe shortcut: redesign the trunk before launch or explicitly narrow
the product's permanence promise under D2.

D1 chooses the first release composition, not the wallet's permanent feature
ceiling. Later rails and protocol families graduate as separately gated slices
under the same D2 core, unless their evidence reopens the core premise.

### 4.2 Production adversary and trust model

Create a component-by-component adversary matrix covering:

- Malicious or compromised owner.
- Malicious, compromised, or policy-confused manager.
- Broken, malicious, or reentrant Config.
- Malicious extender.
- Malicious or buggy Lego.
- Mutated or unavailable dependency at a pinned address.
- Malicious payment helper, facilitator, merchant, or settlement operator.
- Reentrant, non-standard, fee-on-transfer, rebasing, hook-enabled, or
  non-returning token.
- Reentrant or behavior-changing external protocol.
- Stale, censored, delayed, or permanently unavailable sync/cancellation path.
- Sponsor/paymaster griefing through repeated costly valid requests, deliberate
  late reverts, inflated gas limits/calldata, or queue exhaustion.
- Merchant, facilitator, helper, or observer behavior that induces or prolongs
  a reservation to lock a victim's otherwise available balance.
- Compromised or unavailable relayer, sponsor, facilitator, indexer/sync bot,
  transaction builder, signing frontend, factory, or deployment system where
  that component is included in the selected release.

For each actor/component, record:

1. Authority available before compromise.
2. Assets or state reachable.
3. Invariants enforced independently by core.
4. Residual trust that cannot be removed.
5. Prevention, detection, containment, and recovery controls.
6. Upgrade/succession behavior and maximum blast radius.

#### Lego problem statement

Lego trust is a headline architecture question. A Lego mediates protocol
authority and is likely to be both a high-value target and a frequently changed
component. Phase 0 must compare:

- Governance-only trust: reviewed codehash manifests, approval policy,
  timelocks, monitoring, and emergency response.
- Stronger core containment: action-specific primitives, bounded approvals,
  typed effect hashes, beneficiary checks, before/after state checks, and
  protocol-specific limits.
- Split responsibility: a small generic containment envelope plus independently
  reviewed protocol adapters.
- A narrower product surface that avoids integrations that cannot be bounded
  without general authority.

The goal is not to claim that arbitrary Lego behavior can be made safe. The goal
is to state exactly what remains trusted, minimize that trust, and make approval
and recovery proportional to its authority.

### 4.3 Owner, manager, emergency, and recovery shape

D4 has two parts:

- **D4a — authority shape:** decide in early Phase 0 which owner/manager roles,
  multisig or account-abstraction controls, pause/freeze powers, Config
  replacement powers, recovery actions, delays, and limits the permanent core
  must represent.
- **D4b — operational readiness:** before audit freeze and launch, complete
  signer selection, hardware/key ceremonies, quorum and rotation procedures,
  monitoring, incident roles, rehearsals, and compromised-key response.

D4a precedes finalization of D2 and the permanent-core state map. The design must
distinguish:

- Controls that must exist in immutable core bytecode.
- Replaceable policy that may live in Config.
- Operational protections that do not create onchain authority.
- Actions available during each non-IDLE phase or a broken Config.
- Actions that can move value, disable behavior, replace dependencies, or only
  prevent new exposure.

Because signer onboarding, hardware procurement, and operational rehearsals can
have long lead times, D4b work begins in Phase 0 even though its completion gates
the audit freeze rather than the initial design exercises.

The minimal pause, escape, or recovery authority selected in D4a is the primary
tool available to make D2 tolerable. D2 cannot be accepted before reviewers have
tested both sides of that choice: unrecoverable immutable defects versus
compromise of the emergency authority itself.

If D2 evaluates a bounded successor escape, Phase 0 must also define the minimum
successor-deployment and address-attestation model needed to validate the
destination. That analysis must include factory/verifier compromise and
versioning risk. It does not authorize building the production factory early.

An emergency mechanism is not automatically safe merely because it is intended
for emergencies. For each power, record its compromise blast radius, delay,
quorum, user visibility, and whether it violates the stable-custody or
wallet-keyed-identity promise.

### 4.4 Permanent-core and storage-evolution design

The core is non-proxy and cannot be upgraded in place. Its evolution story is
therefore more restrictive than ordinary upgradeable-contract storage
compatibility and must be designed early.

Do not finalize the state map until D4a establishes which emergency and
authority state must exist in the immutable core.

Produce a permanent-core state map that classifies every field as:

- Immutable identity or authority root.
- Append-only/versioned record.
- Replaceable external-policy reference.
- Transient execution state.
- Derivable state that should not be stored.
- Product state that must remain outside the permanent core.

Then answer:

- Which future behaviors can be added through typed external components without
  changing core code?
- Which future behaviors require a core entry point or persistent schema that
  cannot be added later?
- Can commitment, attachment, and action records support versioned encodings
  without ambiguous interpretation or unbounded legacy logic?
- How are deprecated records drained, made terminal, or proven irrelevant?
- What happens if the immutable core itself has a critical defect?
- Is a new-wallet migration compatible with the product's promise of permanent
  custody and protocol identity? If not, what residual core risk is being
  accepted?
- Which views, events, and integration interfaces must be stable, and which may
  remain versioned?

Required exercises:

- Add at least two plausible future action families without changing the
  candidate core.
- Model one future payment-state version and one deprecated dependency.
- Model a critical-core-defect scenario and document the limits of recovery.
- Estimate worst-case storage growth and gas for long-lived attachment and
  commitment history.

Do not freeze the core ABI or storage layout in Phase 0. First determine whether
the permanent-core premise survives these exercises.

### 4.5 Product-derived gas and fee budgets

Before optimizing:

1. Define expected frequency for direct transfer, routed actions, commitment
   creation, settlement, sync, refund, and exit.
2. Define who pays each transaction and the permitted sponsor cost per user
   action.
3. Model relevant Base fee and L1-data scenarios.
4. Determine whether authorization and settlement can be amortized across
   product value or multiple effects.
5. Derive review and hard-stop budgets for each selected-release path.
6. Define sponsor loss limits for reverted, duplicated, or adversarially
   expensive transactions, not only successful user actions.

Then profile the current PoC paths into:

- Config calls and bounded return handling.
- Attachment and codehash verification.
- Phase and transient capability setup/cleanup.
- Calldata hashing and semantic binding.
- Persistent storage reads and writes.
- Token approvals/transfers.
- Protocol/Lego calls.
- Commitment and terminal-state storage.
- Transaction intrinsic and modeled L1 data cost.

Every proposed optimization must identify:

- The measured cost center it removes or reduces.
- The invariant currently served by that work.
- The replacement security argument, if any.
- Before/after semantic and adversarial tests.
- Before/after gas under the same measurement boundary.

The profiling should explicitly decide whether the production design needs an
empty `NONE` session at all. A measurement artifact is not a product feature.

### 4.6 Real integrations and security design—interleaved

Real-integration spikes and the threat model run together. Integration behavior
feeds the security model, and security questions determine which failure modes
the spikes must exercise.

For each candidate production protocol or rail:

1. Document exact contracts, deployed versions, chains, selectors, callbacks,
   token flows, authorities, and upgrade controls.
2. Implement the smallest disposable typed spike needed to observe real
   behavior; do not treat it as production code.
3. Exercise success, revert, partial completion, callback/reentrancy, dependency
   mutation/upgrade, stale data, and exit behavior.
4. Identify every field and postcondition the wallet can independently bind.
5. Identify what remains trusted in the Lego/protocol/helper.
6. Feed the findings back into the adversary matrix and permanent-core needs.

Candidate integration subjects, to be confirmed rather than inherited from the
PoC:

- Ripe wallet-keyed position open, modification, and exact exit, **if selected
  under D8**.
- Morpho authority, position, collateral, and callback behavior, **if selected
  under D8**.
- Real Base USDC proxy transfer and EIP-3009 lifecycle.
- The selected x402 facilitator/HTTP lifecycle, if x402 is in the first release.
- The selected MPP credential/receipt/wire lifecycle, if MPP is in the first
  release.

Ripe and Morpho are PoC-derived candidates, not committed production targets.
D8 must confirm or replace them from current product requirements.

### 4.7 Payment liveness and terminal-state design

For every selected rail, specify a complete state machine covering:

- Authorization creation and uniqueness.
- Available/reserved balance accounting.
- External use before local observation.
- Permissionless and privileged synchronization.
- Expiry boundaries.
- Cancellation and proof of non-use.
- Partial settlement.
- Refund/release.
- Helper/operator failure or replacement.
- Notification failure and retry.
- Replay, resurrection, and cross-version behavior.
- Config, extender, helper, and owner succession during each live state.

Every state must have an explicit answer to:

- Who can advance it?
- What if that party disappears or is malicious?
- What value remains unavailable while it is stuck?
- What proof is required to release value safely?
- Which terminal state prevents reuse forever?

Include adversarial liveness cases where a third party intentionally creates,
uses, withholds evidence for, or prolongs a commitment to lock the victim's
balance. Bound the maximum lockable amount, duration, sponsor cost, and recovery
dependency.

### 4.8 Offchain, relayer, and sponsor architecture

Treat the operational transaction path as part of the security architecture,
not merely a gas payer. For every first-release flow, identify:

- Who constructs, signs, submits, retries, replaces, and observes a transaction.
- Whether the user can self-submit or recover when the relayer/facilitator is
  unavailable.
- How the sponsor authenticates intent and enforces per-wallet, per-action,
  per-merchant, and system-wide budgets.
- Gas-price, calldata-size, execution-gas, retry, and fee ceilings.
- Replay/idempotency behavior across relayers, chains, and replacement
  transactions.
- Who pays for reverts and how repeated valid-but-wasteful requests are bounded.
- How the x402 facilitator, indexer, or sync bot proves and advances external
  payment state.
- Queue, nonce, censorship, and dependency-failure behavior.
- Funding, replenishment, circuit breakers, monitoring, and incident response
  for sponsor accounts or paymasters.

Required adversarial evidence includes repeated expensive requests, late
reverts, duplicate submissions, deliberately stale observations, unavailable
sync infrastructure, induced reservations, fee spikes, and exhausted sponsor
budgets. D10 records which controls are protocol-enforced, sponsor-enforced, or
operationally trusted.

## 5. Phase 0 exit gate

Phase 0 passes only when all of the following are reviewed:

- D1 first-release composition ratified or revised from the provisional working
  candidate.
- Approved adversary/trust matrix with Lego trust called out explicitly.
- D4a owner/manager/emergency authority shape.
- Credible permanent-core state/evolution strategy and explicit D2
  critical-defect disposition.
- Product-derived gas budgets and a decomposed baseline.
- Approved D10 relayer/sponsor/offchain architecture for every applicable
  first-release path.
- Real-integration findings for every component proposed for the first release.
- Complete payment liveness/state model for every proposed first-release rail.
- Explicit supported-token policy.
- Recorded architecture deviations, assumptions, and unresolved risks.

### Permanent-core safety gate

D2 is a standalone, universal launch gate. Before any production permanent core
is deployed for real user funds, the owner and security reviewers must sign off
on:

- The exact critical-defect cases considered.
- Which preventive, pause, escape, migration, or recovery mechanisms remain
  possible after each defect.
- Which funds, reservations, commitments, positions, or wallet-keyed identities
  may become stuck or require migration.
- Whether migration violates the product's permanence promise.
- The maximum value and user population permitted under the residual risk.
- The user-facing claim that can be made honestly about permanence and recovery.

Candidate A does not receive an exception and must also pass the §4.4
future-family exercises with its exact proposed immutable core. If D2 has no
acceptable answer, the disposition is `REDESIGN` or `STOP`, not “ship the simple
version first.”

At the gate, choose exactly one disposition:

- **PROCEED:** the architecture and selected release are viable.
- **PROCEED NARROWER:** retain the trunk but remove unready integrations or
  rails from the first release.
- **REDESIGN:** a load-bearing premise needs new design and PoC evidence.
- **STOP:** the immutable-core, trust, integration, or economic model is not
  viable.

This is an owner and security checkpoint applied per release slice. No
production implementation for that slice starts before its disposition is
recorded. A narrower approved slice may advance while other integration or
payment slices remain in Phase 0/1.

## 6. Phase 1 — focused design and prototype evidence

After Phase 0 approval, run bounded workstreams for the selected release:

1. **Core/evolution candidate:** smallest permanent core and versioned state
   model satisfying the approved future-change exercises.
2. **Authority and governance:** owner/manager model, adapter approval and
   provenance, delays, emergency controls, and incident response.
3. **Cost redesign:** optimize only identified non-load-bearing costs or replace
   a security mechanism with an equivalently evidenced design.
4. **Real integration adapters:** typed Legos and extenders with explicit trust
   and postconditions.
5. **Payment rails:** complete lifecycle prototypes for selected rails.
6. **Offchain/sponsor path:** relayer, sponsorship, facilitator, indexing, sync,
   griefing limits, and operational failure behavior.
7. **Deployment and observability:** deterministic construction, dependency
   manifests, events, monitors, and failure alerts.

Each prototype must have a written hypothesis, threat assumptions, acceptance
criteria, exact tests, reproducible gas method, and a keep/redesign/abandon
result. Throwaway prototypes stay clearly separated from the production
candidate.

### Phase 1 exit gate

- Every first-release flow works against its real target integration.
- Every privileged call and external effect maps to the approved threat model.
- Gas meets the product-derived hard budgets or receives an owner-approved
  product/economic exception.
- The permanent core survives the future-evolution exercises.
- No selected flow requires an arbitrary executor or unbounded authority.
- Remaining trust and emergency limitations are acceptable to the owner and
  security reviewers.

## 7. Phase 2 — production specification

Write a production specification before writing the production implementation.
It must freeze:

- Selected release surface and explicit non-goals.
- Component trust boundaries and authority matrix.
- Core invariants, state machine, storage schema, ABI, events, and versioning.
- Config and owner/manager policy.
- Attachment, code provenance, succession, drain, revoke, and incident policy.
- Action-by-action Lego/Extender semantics and postconditions.
- Payment rail state machines and liveness guarantees.
- Relayer, sponsor/paymaster, facilitator, indexer/sync, transaction-building,
  fee-budget, and offchain failure/recovery behavior.
- Supported tokens and explicit rejection behavior.
- Reentrancy and callback policy.
- Gas and fee gates.
- Factory/deployment, address derivation, initialization, and migration/cutover.
- Monitoring, alerting, pause/freeze/recovery, and operator runbooks.
- Test, formal-verification, and audit evidence matrix.

The specification must distinguish protocol-enforced safety from governance
trust and operational mitigation. A prose promise is not a substitute for a
contract invariant.

### Phase 2 exit gate

Owner, product, protocol engineering, and security reviewers approve the same
frozen specification. Any later architecture or trust-boundary change reopens
the affected Phase 0/1 evidence and the specification review.

## 8. Phase 3 — production candidate

Implement the frozen specification in a clean production path. Do not
progressively rename or deploy the PoC contracts.

Recommended build order:

1. Permanent-core types, storage, and state-machine skeleton.
2. Boot, ownership/authority, Config replacement, and emergency controls.
3. Direct custody/transfer path and available-balance accounting.
4. Attachment provenance, routing, capability containment, and succession.
5. One real action family end to end.
6. Each additional action family independently.
7. Each selected payment rail independently.
8. Selected relayer/sponsor/facilitator/indexer path and griefing controls.
9. Factory/deployment/migration and operational tooling.
10. Monitoring and incident-response integration.

Every step must include positive, negative, adversarial, invariant, gas, and
upgrade/succession evidence before the next authority surface is added.

When a load-bearing check is introduced, the same change must add and verify a
test that fails when that check is removed or inverted. This may be a focused
manual mutation or an automated mutation tool, but it is evidence produced when
the check is written—not deferred until pre-audit hardening.

## 9. Phase 4 — verification and independent review

Before audit:

- Unit and integration tests cover all specified state transitions.
- Stateful property tests exercise phases, capabilities, reservations,
  commitments, and lifecycle succession.
- Fuzzing covers malformed calldata, boundary amounts/times, route collisions,
  replay, reentrancy, and dependency changes.
- Continuous mutation evidence for every load-bearing check is complete and
  reproducible; Phase 4 audits that record rather than creating it for the first
  time.
- Fork tests cover every real dependency and supported chain.
- Differential/reference tests cover payment digests and protocol accounting
  where a canonical implementation exists.
- Compiler, EVM target, runtime size, storage layout, and gas reports are pinned
  and reproducible.
- A manual invariant-to-code-to-test traceability matrix is complete.
- Deployment and emergency runbooks are rehearsed.

Then freeze the audit commit and obtain independent security review. Feature or
trust-boundary changes during remediation reopen the affected specification and
evidence rather than being folded silently into audit fixes.

## 10. Phase 5 — rollout

Roll out the smallest approved surface with:

- Deterministic deployment and verified source.
- Dependency/codehash manifests.
- Conservative initial value and rate limits.
- Canary users or accounts.
- Live monitoring of phases, failed actions, approvals, reservations,
  commitment age, sync delay, sponsor spend/revert rate, relayer backlog,
  reservation-lock duration, adapter changes, and emergency actions.
- Documented stop, freeze, drain, and user-communication procedures.
- Predefined criteria for increasing limits or enabling another adapter/rail.

Broader action families and payment rails graduate separately. Success of the
direct-transfer trunk does not automatically authorize routed protocol actions,
and success of one Lego does not authorize another.

## 11. Decision register

These decisions require explicit review before their dependent work proceeds:

| Id | Decision | Owner | Required before |
|---|---|---|---|
| D1 | First-release composition A/B/C/D, ratified or revised from the provisional working candidate | Product owner | Phase 0 exit; graduation also requires D2 and applicable slice gates |
| D2 | Permanent-core defect and evolution posture | Owner + security | Core specification and any production deployment holding real user funds |
| D3 | Lego trust, containment, provenance, and succession model | Owner + security | Real adapter implementation |
| D4 | Owner, manager, multisig/AA, emergency, and recovery model | Owner + security | D4a before D2/state-map freeze; D4b before audit freeze |
| D5 | Product-derived gas and sponsored-fee budgets | Product + engineering | Cost optimization acceptance |
| D6 | First-release payment rails and liveness guarantees | Product + security | Payment specification |
| D7 | Supported token classes and rejection policy | Product + security | Token integration |
| D8 | First-release real protocols and allowed authority | Product + protocol engineering | Adapter specification |
| D9 | Audit scope and launch limits | Owner + security | Audit freeze |
| D10 | Relayer, sponsor, facilitator, indexer/sync, and offchain failure/economic model | Product + operations + security | Sponsored/offchain specification and launch |

## 12. Evidence and process rules

- Preserve the Lean PoC and its results as a historical evidence baseline.
- Record modeled, real, assumed, and unresolved evidence separately.
- Define acceptance criteria before implementing a prototype or optimization.
- Keep gas baselines and thresholds read-only from the code being measured.
- Compare alternatives at equivalent initialized state and transaction
  boundaries.
- Preserve exact source commit, dependency versions, chain/block state,
  compiler/EVM settings, and semantic postconditions with every result.
- Maintain an append-only decision/build log for production design and
  implementation.
- Never rewrite a failed result into a passing narrative; append the superseding
  evidence and explain the change.
- Add mutation-sensitive evidence in the same change as every load-bearing
  security check and preserve the mutation result in the evidence record.
- Stop at owner/security gates rather than resolving product, authority, or
  trust expansions unilaterally.

## 13. Immediate next work

The next bounded work package is **Phase 0 decision foundation**, not production
contract implementation:

1. Name a provisional D1 working candidate from current product requirements and
   transaction mix; this scopes evidence but does not authorize launch.
2. Define D4a's owner/manager/emergency authority shape.
3. Build the D2 critical-defect cases and permanent-core state/evolution map,
   including the exact Candidate A future-family gate if A is provisional.
4. Build the adversary/trust matrix, led by malicious/broken Lego behavior,
   sponsor griefing, reservation locking, and compromised authority.
5. Decompose gas/sponsor cost and select only the real protocol, payment, and
   offchain spikes required by the candidate release.
6. Return to the owner with the slice-specific Phase 0 disposition and D1–D10
   decisions.

Until that gate is passed, no PoC interface, storage layout, gas target, or
trusted adapter assumption becomes a production commitment.
