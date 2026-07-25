# User Wallet v3 — Phase 0 D4a/D2 Foundation

> **Archive notice (2026-07-24):** This file belongs to the paused,
> PoC-derived production track. Its historical decisions are superseded for
> current Wallet v3 work. It is retained as reasoning provenance, not current
> authority or implementation authorization. See the [archive index](README.md)
> and the [current Wallet v3 documents](../../wallets-v3/README.md).

**Status:** REVISED AFTER INITIAL INDEPENDENT CHALLENGE — Package B remains a
candidate to pressure-test, not an accepted baseline

**Phase 0 authority:** The owner explicitly answered “yes I approve” on
2026-07-23 under the [Production Design Plan](production-design-plan.md).

**Roles:** The owner also holds product, operations, and named human
security-review responsibility. The design/implementation analyst prepares the
analysis. The separate reviewer agent provides independent Phase 0 challenge.
Independent external review remains required before audit freeze or production
deployment.

**Code-change scope:** None. This document analyzes authority and recovery
options; it does not authorize contract implementation or an architecture
change.

## 1. Decision being prepared

This work prepares two coupled owner decisions:

- **D4a:** What owner, manager, guardian, pause, emergency, and recovery
  authority must the permanent core represent?
- **D2:** What happens when the immutable core itself has a critical defect,
  and which residual failures are acceptable?

The non-proxy architecture remains the working hypothesis. D2 does not assume a
proxy is desirable. It tests whether the word “permanent” can be used honestly
once critical-defect recovery, wallet-keyed positions, payment commitments, and
future product families are considered.

Any recommendation to add a proxy, `delegatecall`, replaceable core, arbitrary
executor, general callback/signature perimeter, or unbounded emergency call is
an architecture scope-stop requiring a separate owner decision.

## 2. Executive findings

1. **The PoC proves external-component recovery, not arbitrary core recovery.**
   Direct Config replacement and typed extender succession handle important
   Config, extender, and dependency failures without moving custody.
2. **The current PoC core has no production emergency authority.** Its owner is
   immutable. There is no owner rotation, pause, freeze, scoped attachment
   disable, hard revoke, or migration/escape path.
3. **A pause contains only defects whose dangerous paths still honor the pause.**
   It cannot repair a broken transfer, routing, accounting, authorization, or
   compiler/runtime path.
4. **Migration is necessarily partial.** A new address can receive transferable
   tokens, but it cannot automatically inherit the old address's protocol
   positions, EIP-3009 digests, payment commitments, reservations, or identity.
5. **No mechanism provides both absolute immutability and recovery from every
   core defect.** D2 must choose a bounded residual-risk promise, not search for
   a nonexistent perfect escape.
6. **The working recommendation is to retain the non-proxy hypothesis while
   designing a bounded two-role emergency package.** A replaceable core remains
   a REDESIGN comparator, not the default.
7. **The authority/recovery machine is itself unpatchable privileged code.**
   Rotation, veto, pause, epoch, delay, and escape bugs can create unrecoverable
   takeover, denial-of-service, or custody paths. Package B's added containment
   therefore comes with more permanent privileged surface than Package A.
8. **Package B is viable only with meaningful owner/guardian key separation and
   a safe delayed/joint recovery design.** Without those prerequisites, its
   two-role safety argument collapses.
9. **Base delay semantics are part of the authority model.** Timelock safety
   depends on the chosen clock, sequencer availability, L1-origin behavior, and
   an emergency transaction-submission fallback.

## 3. Repository-grounded baseline

### 3.1 Current v3 PoC authority

The current [`UserWalletV3.vy`](../../../contracts/poc/userWallet/UserWalletV3.vy)
contains:

- One immutable `OWNER`.
- One mutable Config pointer.
- Append-only attachment records with automatic `ACTIVE` → `DRAIN_ONLY`
  succession.
- Persistent reservations and terminal commitment state.
- One transient execution phase and one transient capability.

The immutable owner can currently:

- Replace Config while IDLE.
- Attach a strictly newer typed extender.
- Refund the unsettled remainder of a reserved-transfer commitment.

The current owner cannot:

- Rotate ownership.
- Pause or freeze wallet behavior.
- Disable one attachment without adding a valid successor.
- Hard-revoke a broken dependency.
- Invalidate all rail signatures independently of commitment state.
- Move funds through a Config-independent recovery path.
- Migrate commitments, reservations, attachment history, or wallet-keyed
  positions to a successor wallet.

Permissionless or non-owner recovery currently includes:

- Synchronizing a used external-exact commitment.
- Expiring an unused external-exact commitment only after helper proof.
- Settling a reserved transfer only by its stored settlement operator.
- Executing Config-authorized exact `DRAIN_ONLY` exits.

### 3.2 What the PoC already handles well

| Failure | Existing mechanism | Evidence posture |
|---|---|---|
| Operational Config always reverts | Owner directly replaces Config without old-Config cooperation | Demonstrated |
| Extender version is superseded | New version becomes current; predecessor becomes selector-bounded `DRAIN_ONLY` | Demonstrated with mocks |
| Same-address dependency bytecode changes | Runtime codehash check rejects use | Demonstrated |
| External payment was used but not observed | Permissionless sync reconciles after helper proof | Demonstrated for Base USDC overlay |
| Unused external payment expires | Permissionless expiry releases only after helper proves non-use | Demonstrated |
| Reserved-transfer operator disappears | Owner refund releases unsettled reservation | Demonstrated in representative model |

These mechanisms depend on the immutable core continuing to execute correctly.
They do not solve a defect in the core path that implements them.

### 3.3 Relevant v2 precedent—not a production default

The repository's v2 system includes:

- Mutable, two-step timelocked ownership with new-owner acceptance.
- Security-authorized cancellation of pending ownership changes.
- Owner/security freeze controls.
- Governance-controlled ejection mode.
- Delayed or governance-enabled wallet-to-wallet migration.

Those mechanisms are useful evidence about operational needs, but v2 relies on
broader registries, Config machinery, Switchboard authority, asset enumeration,
and migration components. Phase 0 must not copy them wholesale into the smaller
v3 core.

## 4. Terms and limits

- **Prevention:** Reduce the probability that a defect or compromise is
  reachable.
- **Containment:** Stop new exposure after a defect or compromise is detected.
- **Recovery:** Restore safe operation at the same address without violating
  established obligations.
- **Migration:** Move whatever state or assets are transferable to a new
  address. Migration is not same-address recovery.
- **Pause:** A persistent restriction on selected entry points. A pause is only
  reliable when the defect does not bypass or break its check.
- **Escape:** A narrow emergency path that can move specified assets or authority
  without relying on the normal Config/action path.

An escape function is itself permanent privileged attack surface. Calling it
“emergency” does not make it safer.

## 5. D4a authority requirements

Any production candidate should explicitly answer:

1. Who owns ordinary administration?
2. Can ownership rotate if the owner account or signer set must change?
3. Who can pause new risk?
4. Can a compromised owner immediately undo the pause?
5. Who can cancel a malicious pending owner, guardian, Config, attachment, or
   unpause change?
6. Which actions remain possible while paused?
7. Can any emergency role move assets or grant protocol authority?
8. How is a lost or compromised guardian replaced?
9. What delay applies to authority-increasing changes?
10. Which events and offchain monitors make every authority change observable?
11. Are owner and guardian keys independently custodied in practice?
12. Which Base time source and transaction-submission fallback enforce each
    delay?

### 5.1 Monotonic emergency-role principle

The safer default is that a guardian may immediately reduce authority but never
increase it:

- May pause new risk.
- May cancel pending authority-increasing changes.
- May veto or delay unpause.
- May request a scoped dependency disable.
- Cannot transfer assets.
- Cannot attach an extender or Lego.
- Cannot replace Config.
- Cannot grant protocol authority.
- Cannot unpause alone.
- Cannot select a migration destination alone.

This turns guardian compromise primarily into a denial-of-service risk rather
than a direct custody-loss risk.

### 5.2 Pause scope that must be specified

A production pause cannot be one unexplained boolean. At minimum, the
specification must classify:

- New direct transfers.
- Owner- or manager-initiated transfers authorized through Config.
- New active-route sessions.
- New attachments and successors.
- New external-exact or reserved-transfer commitments.
- Rail `isValidSignature` answers.
- Existing reserved-transfer settlement.
- External-exact sync and expiry.
- Reserved-transfer refund.
- Config replacement.
- Pending owner/guardian operations.
- `DRAIN_ONLY` position exits.

A conservative starting posture is:

- Pause new transfers, active sessions, commitments, attachments, rail
  signatures, settlements, and value-moving exits.
- Permit accounting-only external sync, proof-backed unused expiry, reserved
  refund, and tightly controlled Config replacement.
- Re-enable a reviewed exit or settlement path only through a separately
  authorized recovery decision.

This is a working posture, not a frozen state machine. Real payment and protocol
obligations may require narrower pause domains.

### 5.3 Owner/guardian key-separation precondition

Package B's two-role argument depends on real custody separation:

| Custody level | What it protects | What it does not protect | Package B interpretation |
|---|---|---|---|
| Same key or seed | Nothing meaningful | Any key compromise defeats both roles | Invalid; guardian is security theater |
| Same human, distinct keys and hardware | One device, key, or signing-path compromise | Human compromise, coercion, phishing across both roles, shared process failure | Limited defense-in-depth only |
| Different human quorums, distinct hardware, and separate procedures | Many single-person, single-device, and process failures | Collusion, correlated organizational compromise | Required for the full two-role safety claim |

The current Phase 0 owner/reviewer staffing does not automatically determine
production key custody. But Package B cannot be adopted on its advertised safety
case until the owner confirms that independent human/quorum custody is
operationally staffable. If it is not, the package must be downgraded, redesigned,
or limited to a low-cap pilot with an explicit correlated-compromise assumption.

### 5.4 Base clock and emergency-submission decision

Base normally seals L2 blocks on a short cadence, but inclusion can be delayed,
and ordinary L2 submission depends on sequencer availability. The OP Stack
derivation rules constrain L2 timestamps relative to the L1 origin and a
configured maximum sequencer drift; they do not make the L2 timestamp an
independent wall clock. See the official
[Base transaction documentation](https://docs.base.org/base-chain/network-information/troubleshooting-transactions)
and [OP Stack derivation specification](https://specs.optimism.io/protocol/derivation.html).

The Base/OP Stack exposes L1 context through the
[`L1Block` predeploy](https://specs.optimism.io/protocol/predeploys.html), but
that state is observed from L2 and advances through L2 derivation. It does not
make a wallet callable during an L2 outage. L1 deposits can provide an alternate
submission path when the sequencer is down, but contract callers are subject to
L1→L2 address aliasing and the operational delay/cost of the deposit path. See
the official [Base deposit specification](https://docs.base.org/base-chain/specs/protocol/bridging/deposits).

Phase 0 must compare:

- L2 `block.timestamp` with a safety margin larger than the reviewed sequencer
  drift bound.
- L2 `block.number`, which measures produced blocks rather than wall time and
  stalls when block production stalls.
- L1-origin number/time read from `L1Block`, which adds a predeploy/protocol
  dependency and may lag.
- A hybrid: L2 timestamp for ordinary operations, L1-origin confirmation for
  high-impact recovery, plus an L1-deposit emergency-pause submission path.

The review must pin the actual Base chain parameters at specification freeze,
model downtime and reorg/finality behavior, and verify how an owner or guardian
controller can use the fallback path. No timelock duration is accepted before
this decision.

## 6. D4a authority packages

### Package A — immutable owner only

**Shape**

- Immutable owner address, expected to be a multisig or account-abstraction
  controller.
- Owner retains Config replacement and attachment administration.
- No independent guardian, pause, or recovery authority.

**Advantages**

- Smallest permanent core and authority surface.
- No guardian denial-of-service or emergency-drain risk.
- Closest to the successful PoC.

**Failure limits**

- Lost or broken owner controller permanently disables administration.
- Compromised owner can change all owner-controlled policy before outside
  containment.
- No response to a dangerous core, extender, Lego, helper, or protocol path
  except ordinary succession and Config policy.
- Does not provide a credible D2 answer for high-value production custody.

**Preliminary disposition:** Do not select as the production default.

### Package B — bounded owner plus monotonic guardian

**Shape**

- Production owner is a multisig or account-abstraction controller.
- Core supports delayed two-step owner rotation with new-owner acceptance.
- A separate guardian/security controller may immediately pause new risk and
  cancel pending authority-increasing changes.
- Owner and guardian use independently custodied controllers; distinct keys
  held by one person provide only a weaker, explicitly disclosed variant.
- Guardian cannot move funds, grant authority, attach dependencies, replace
  Config, or unpause alone.
- Owner may propose unpause or guardian rotation; a delay and guardian veto
  protect against a compromised owner. A reviewed joint path may permit faster
  recovery.
- Config replacement remains possible under a security pause, but the new
  Config cannot create economic effects until the relevant pause is cleared.
- No generic emergency asset drain.

**Advantages**

- Contains many owner, Config, attachment, Lego, rail, and offchain incidents.
- Makes guardian compromise primarily a liveness problem.
- Keeps ordinary policy replaceable outside the core.
- Adds less custody authority than a migration/drain role.

**Failure limits**

- The owner/guardian/pause/veto/rotation state machine is additional
  unpatchable privileged code.
- Pause cannot repair arbitrary core defects.
- Lost owner and guardian combinations may still make the wallet inoperable.
- Directly address-keyed positions remain at the old wallet.
- Does not independently recover liquid tokens if normal transfer paths break.

**Preliminary disposition:** Recommended only as the D4a candidate to
pressure-test, provided independent key custody is staffable and the delayed/
joint fast path threat-models cleanly. It is not an accepted baseline.

### Package C — Package B plus bounded successor escape

**Shape**

- Includes Package B.
- Adds a delayed, owner-plus-guardian recovery path to a prevalidated successor
  wallet.
- Destination must be a factory-attested wallet for the same accepted owner and
  chain.
- Recovery is token-specific and cannot invoke arbitrary target/calldata.
- Live commitments, reservations, authorities, and known positions either block
  recovery or require an explicit, proven terminal/exit process.
- The guardian cannot choose the destination or execute recovery alone.

**Advantages**

- May recover supported liquid assets if the ordinary transfer/Config path is
  broken but the escape path still works.
- Gives D2 a concrete partial migration mechanism.
- Uses stronger authorization than ordinary owner-controlled transfer policy.

**Failure limits**

- Requires a minimal successor factory/address-attestation architecture before
  its D2 value can be evaluated.
- Makes that factory/verifier and its versioning policy new recovery trust.
- Adds a permanent asset-movement path and destination-validation surface.
- Cannot preserve the old wallet address.
- Cannot generically migrate wallet-keyed external positions.
- Cannot move address-bound EIP-3009 authorizations or commitments safely.
- Cannot help if the compiler/runtime/core defect also breaks the escape path.
- “Available balance” may be unreliable if reservation accounting is the
  defect.

**Preliminary disposition:** Provisional and blocked on a minimal
factory/address-attestation trust design. After that prerequisite, adversarially
spike it as a D2 option; do not accept or implement until its exact bounds
outperform Package B's residual risk.

### Package D — replaceable or proxy core

**Shape**

- Proxy, `delegatecall`, replaceable execution implementation, or equivalent
  same-address code authority.

**Advantages**

- Can patch same-address logic and potentially preserve wallet-keyed identity.

**Failure limits**

- Makes upgrade authority a direct custody root.
- Reintroduces storage-layout, initialization, implementation, governance, and
  upgrade-compromise risks.
- Weakens the PoC's strongest simplification.
- Does not automatically solve malicious upgrades or compromised governance.

**Preliminary disposition:** Scope-stop REDESIGN comparator only. Do not build
without a separate owner architecture decision.

### 6.1 Package comparison

| Property | A | B | C | D |
|---|---:|---:|---:|---:|
| No proxy/delegatecall | Yes | Yes | Yes | No |
| Independent incident pause | No | Yes | Yes | Depends |
| Guardian can directly move funds | No | No | Joint bounded path only | Upgrade authority may gain equivalent power |
| Same-address core patch | No | No | No | Yes |
| Liquid-token escape if normal path breaks | No | No | Partial | Potentially |
| Preserves wallet-keyed positions automatically | Yes while core works | Yes while core works | No after migration | Potentially, with upgrade risk |
| New unpatchable authority/recovery state machine | Minimal | Owner/guardian/pause/veto/rotation | B plus joint escape/destination validation | Upgrade/governance machine |
| Requires independent owner/guardian key custody | No guardian | Yes for full claim | Yes | Governance-dependent |
| New permanent privileged surface | Lowest | Moderate | High | Highest |
| Current working posture | Reject for high-value production | Pressure-test if prerequisites hold | Provisional; attestation design first | Scope-stop |

## 7. D2 critical-defect matrix

| Defect or incident | Package B containment | Same-address recovery | Package C contribution | Residual result |
|---|---|---|---|---|
| Config operational calls always revert | Owner replaces Config while paused | Yes, already demonstrated | None needed | Keep non-proxy |
| Config authorizes unsafe requests | Guardian pauses; owner replaces Config | Yes if core checks and pause work | None needed | Governance/monitoring risk |
| Extender or Lego is malicious/buggy | Pause active routes; succeed/disable dependency after review | Often, if typed successor/exit works | Liquid assets only if core routes are unusable | Positions may remain stuck |
| Helper/facilitator/indexer fails | Pause new rail authority; permit safe sync/expiry/refund | Sometimes, under rail proof rules | Does not migrate address-bound commitment | Liveness and reserved-value risk |
| Rail signature path authorizes an invalid digest | Global rail pause must force invalid answer | Only if pause check remains reliable | Cannot revoke a signature already accepted externally | Potential payment loss |
| Direct transfer authorization/bounds are bypassed | Guardian pause if dangerous path honors pause | No generic repair | Joint escape may move remaining supported tokens | Exploited value is unrecoverable |
| Session/capability/phase bug permits general authority | Guardian pause if every affected entry point honors pause | No generic repair | Partial liquid-token migration only | Protocol authority/positions may be exposed |
| Persistent reservation accounting locks available funds | Pause new commitments | Only through a separately correct commitment repair | Escape cannot trust broken `available` without an independent rule | May require migration or accepted lock |
| Core settlement/refund/expiry path is broken | Pause affected rail | No, unless another exact terminal path exists | Cannot transfer address-bound authorization state | Commitment may remain stuck forever |
| Attachment history/limit/schema cannot express future family | No incident action; detect before launch | No code addition possible | New wallet supports new core but breaks permanence | Candidate core fails future-family gate |
| Owner controller is lost or broken | Guardian can pause but not administer | Only if owner rotation can be safely completed without old owner | Joint recovery may move supported tokens if designed for this case | Strong recovery role may become custody root |
| Owner controller is compromised | Guardian pauses and cancels pending changes | Rotate after delay if safe path exists | Joint escape blocked without guardian | DoS remains possible |
| Guardian is compromised | Guardian may cause pause/DoS only | Owner uses delayed rotation/unpause path | No unilateral migration | Liveness cost, not direct theft |
| Both owner and guardian are compromised | No trusted onchain authority remains | None | Joint path becomes attacker path | Custody loss; operational key security is critical |
| Owner/guardian/pause/veto/epoch logic is defective | The authority machine itself may not contain the defect | No patch; a forged confirmation or broken delay may take over or brick the wallet | Escape state can turn the defect into a direct drain | Package B/C add unpatchable privileged defect classes absent from A |
| Token/protocol changes behavior or upgrades | Pause affected action/rail | Successor or exact exit if protocol permits | Liquid tokens may migrate; positions may not | External governance risk |
| Compiler, EVM, or shared low-level-call defect affects core | Cannot assume pause works | None can be assumed | Cannot assume escape works | Immutable-core existential risk |
| Unsupported ERC-20/NFT/native asset is sent to wallet | No effect unless supported recovery exists | No generic recovery in PoC | A bounded token escape may help only supported interfaces | Unsupported assets may be permanently stuck |
| Gas repricing makes a critical path unexecutable | Pause does not restore executability | None without a cheaper prebuilt path | Escape helps only if cheaper and still executable | Liveness risk |

## 8. What migration cannot promise

Even a well-designed Package C cannot claim whole-wallet migration:

- The destination has a different address.
- Protocol positions keyed to the old wallet remain there unless the protocol
  exposes an exact transfer or exit.
- `DRAIN_ONLY` exits still depend on old-core routing and protocol behavior.
- External-exact digests bind the old wallet address.
- Live commitments and terminal non-reuse maps remain in old storage.
- Reservations cannot be copied safely without reproducing external-use state.
- Attachment history and old-version exit authority remain in the old core.
- Events and indexer history split across addresses.
- A user-facing “permanent wallet address” claim becomes conditional.

The honest Package C claim would be: “A jointly authorized emergency path may
move specifically supported liquid assets to a verified successor.” It is not
“the wallet upgrades without migration.”

## 9. Non-proxy decision test

Continue with a non-proxy production candidate only if all are true:

1. The core is small enough for exhaustive manual and automated review.
2. D4a provides acceptable incident containment without creating a larger
   custody root.
3. The exact core passes future payment and protocol-family exercises.
4. Critical functions have continuous mutation-sensitive evidence.
5. External positions have exact reviewed exit or explicit stuck-position
   policy.
6. Payment rails have bounded liveness and reservation behavior.
7. The owner accepts that arbitrary core/compiler/EVM defects may still require
   partial migration or leave state stranded.
8. Launch caps and monitoring bound the blast radius while operational evidence
   accumulates.

If these fail, the correct result is `REDESIGN` or `STOP`. Phase 0 must not
quietly add generic authority to preserve the original recommendation.

## 10. Preliminary recommendation

Pressure-test **Package B** as the D4a working candidate only if production
owner/guardian key independence is staffable:

- Mutable, two-step delayed owner rotation with new-owner acceptance.
- Production owner is a multisig or account-abstraction controller.
- Separate guardian with immediate pause/cancel/veto authority only.
- No unilateral guardian value movement or authority grant.
- Delayed owner unpause/guardian rotation, with an optional jointly authorized
  faster path whose clean threat model is a condition of selecting B.
- Config replacement remains available during pause, but economic activity
  remains paused.
- No generic drain or arbitrary call.

In parallel, define Package C's minimum successor-deployment/address-attestation
model. Only then spike its bounded successor escape as a D2 comparison. It must
prove that its recovery value exceeds the attack surface it adds. Keep
**Package D** behind the architecture scope-stop.

This recommendation is intentionally not a final decision. The owner must choose
the acceptable recovery tier after independent challenge.

### 10.1 Internal adversarial challenge

Package B remains the working candidate after an initial hostile review, but it
has unresolved design tensions:

| Challenge | Consequence | Required design response |
|---|---|---|
| Compromised guardian repeatedly pauses | Indefinite denial of service | Owner needs a slow, observable guardian-rotation/unpause path that a guardian can delay but not veto forever |
| Compromised owner queues guardian rotation and unpause | Guardian containment may be bypassed after delay | Guardian must cancel or extend suspicious changes while users/operations have time to respond |
| Owner and guardian collude or are both compromised | Full administrative trust is lost | No onchain role design solves this; independent key custody and launch caps remain mandatory |
| Pause omits one value-moving entry point or rail signature | Exploit survives emergency response | Centralize pause-domain enforcement and require removal/inversion mutation evidence for every gated path |
| Pause blocks a necessary debt exit or payment settlement | Liquidation, breach, or stuck obligation | Define the smallest number of pause domains and exact, separately authorized recovery actions |
| Owner controller contract fails | Wallet administration may be permanently lost | Two-step core owner rotation helps only if initiation remains possible; lost-owner recovery would expand guardian authority |
| Guardian can immediately unpause or move assets | Guardian compromise becomes direct custody risk | Preserve monotonic guardian authority; no unilateral unpause or value movement |
| Rotation/veto/epoch logic accepts a stale or forged confirmation | Permanent takeover or bricking | Treat the authority machine as a primary audit/formal-verification target with continuous mutation evidence |
| Owner and guardian keys share custody or operators | One compromise defeats both roles | Package B cannot claim independent containment without separate human/quorum custody |
| Base clock/submission path is unavailable or manipulated within protocol bounds | Pause, veto, or recovery arrives late or matures unexpectedly | Select and test the clock plus an L1-deposit emergency-submission fallback |

There is no perfect lost-guardian rule. An absolute guardian veto makes
compromise or key loss a permanent denial of service; an owner-only delayed
override lets a compromised owner eventually defeat the guardian. The working
direction is a long, observable owner override plus a shorter joint recovery
path, with launch caps and monitoring covering the delay. This must be reviewed
against realistic incident-response time.

Package C has a narrower useful claim than “recovery”:

| Challenge | Consequence |
|---|---|
| Reservation/accounting is the defective state | The escape cannot safely rely on `available` or `reserved` |
| Factory/verifier accepts the wrong successor | The recovery path becomes a drain |
| Live address-bound payment or protocol state exists | Moving tokens may violate obligations or strand positions |
| The low-level token-call/compiler path is defective | The escape may fail with the normal path |
| Owner and guardian are both compromised | The delayed joint path eventually drains supported assets |
| Only some assets implement the supported transfer interface | “Whole wallet” recovery is impossible |

Package C should proceed only as a spike for **supported liquid-token escape
under a narrow defect set**. It must not be used to soften D2's disclosure of
unrecoverable positions, commitments, identity, or arbitrary core failures.

## 11. Owner decisions to prepare

### D4a-0 — production key independence

Choose the production assumption:

1. Same key/seed for owner and guardian — Package B is invalid.
2. Same human with separate hardware/keys — limited defense-in-depth; no full
   two-role claim.
3. Independent human quorums with separate hardware/procedures — full Package B
   working assumption.

**Required before adopting B:** Confirm option 3 is staffable, or explicitly
select a weaker package/claim and lower launch limits.

### D4a-1 — authority package

- A: Immutable owner only.
- B: Bounded owner rotation plus monotonic guardian.
- C: Package B plus a jointly authorized bounded successor escape.
- D: Reopen replaceable/proxy core architecture.

**Working recommendation:** Pressure-test B only if D4a-0 and D4a-3 can be
satisfied; keep C provisional until D2-C0.

### D4a-2 — pause semantics

Decide whether the working pause posture should:

- Stop all value-moving paths by default.
- Permit accounting-only sync, proof-backed expiry, and reservation release.
- Require a separate reviewed authorization to re-enable one exact exit or
  settlement while globally paused.

**Working recommendation:** Yes to all three.

### D4a-3 — Base delay and emergency-submission source

Select and test:

- L2 timestamp.
- L2 block number.
- L1-origin reference through `L1Block`.
- A hybrid with an L1-deposit pause fallback.

**Working recommendation:** Pressure-test the hybrid for high-impact recovery
and a simpler L2 timestamp for ordinary pending operations. Do not freeze either
until Base parameters, downtime, reorg/finality, caller aliasing, and controller
compatibility are verified.

### D2-1 — acceptable residual promise

Choose which statement the production design should attempt to make:

1. **Containment only:** no emergency asset escape; arbitrary core defects may
   permanently strand assets/state.
2. **Partial liquid-asset escape:** jointly authorized migration of explicitly
   supported tokens to a verified successor, without promising position,
   commitment, or identity migration.
3. **Same-address patchability:** reopen proxy/replaceable-core design and its
   governance risks.

**Working recommendation:** Evaluate statement 2 against statement 1; do not
select statement 3 without evidence that the non-proxy residual is unacceptable.

### D2-C0 — successor attestation prerequisite

Before Package C can be evaluated, define:

- How a successor wallet is deployed or recognized.
- How same-owner intent is proved.
- Which factory/verifier/codehash/version is trusted.
- How factory/verifier compromise or replacement is contained.
- How an L1/L2 or chain mismatch is rejected.

This is Phase 0 trust design only, not authorization to build the factory.

## 12. Preliminary permanent-state impact

This is a state-design inventory, not a proposed storage layout.

### 12.1 Existing state to preserve or reconsider

| State category | Current PoC state | Phase 0 question |
|---|---|---|
| Authority root | Immutable `OWNER` | Replace with mutable two-step owner, or keep an immutable external controller? |
| Policy pointer | Mutable `config` | Which marker/interface versions may future Configs use? |
| Attachments/routes | Append-only records, current-route mappings, maximum 16 attachments | Is the bound viable for a permanent wallet, and is scoped disable/hard revoke required? |
| Commitments | Mode/state/amount/destination/operator/digest/time/helper fields | Can future rail versions coexist without ambiguous interpretation? |
| Replay protection | Permanently used commitment ids, digests, and nonces | What is the lifetime/storage-growth bound? |
| Reservation accounting | Per-token reserved amount | How is a broken or stuck reservation handled without unsafe reset authority? |
| Execution | Transient phase/frame/capability | Which emergency paths are legal during pause and active execution? |

### 12.2 Package B state candidates

Package B would likely require bounded persistent state for:

- Current owner/controller.
- Current guardian/security controller.
- Security pause domain or bitmask.
- The selected delay clock and units, unless they are immutable protocol
  constants.
- Pending owner change with candidate, initiation, executable time/block, and
  new-owner acceptance.
- Pending guardian change with equivalent delay and cancellation rules.
- Pending unpause with initiation, executable time/block, and veto/cancel state.
- Authority-change nonce or epoch to prevent stale confirmations.
- If an L1-deposit emergency path is selected, an explicitly validated L1
  controller identity whose aliased L2 caller is the only alternate emergency
  caller.

Every field creates permanent interpretation and liveness requirements. Phase 0
must decide whether delays use timestamps or blocks, how L2 sequencing affects
them, whether any L1-origin or aliased-caller dependency is acceptable, and how
pending operations are invalidated after owner/guardian changes.

### 12.3 Package C additional state candidates

Package C would additionally require:

- Proposed successor wallet and its attestation evidence.
- Recovery initiation and executable time/block.
- Independent owner and guardian confirmations or a joint authorization record.
- Recovery epoch and cancellation/terminal state.
- Per-token recovery replay protection.
- Destination factory/verifier identity and codehash or a versioned validation
  mechanism.

A token-specific escape can check `reserved[token] == 0`, but the core cannot
prove from that fact that no external position or address-bound obligation
exists. Adding a global “safe to migrate” boolean would merely move that trust
problem into whichever authority sets it.

### 12.4 State-minimization rule

Do not add a persistent field merely because it makes an emergency workflow
convenient. Each field must identify:

- The failure it contains or recovers.
- Who may change it.
- How compromise is bounded.
- How it is cancelled, superseded, or made terminal.
- What happens if it is stuck forever.
- How future versions interpret it without changing core code.

## 13. Future-family exercises for the immutable core

These are design probes for the future production candidate, not requests to add
features to the PoC.

### 13.1 Exact-input swap with minimum output

**Desired effect**

- Spend at most an exact input-token amount.
- Receive at least a minimum output-token amount directly in the wallet.
- Bind router/protocol, input token, output token, recipient, amount, minimum
  output, and deadline.

**Pressure on the PoC model**

- The existing one-resource envelope and settlement check bound maximum input
  loss but do not independently enforce minimum output-token gain.
- Relying on the Lego alone to enforce minimum output leaves the highest-value
  semantic postcondition inside the trusted adapter.
- A production candidate may need a second observed resource/postcondition or a
  narrow swap-specific core primitive.

**Gate**

If swaps are a plausible near-term family, Candidate A cannot freeze the
existing one-resource core without resolving this pressure.

### 13.2 Multi-asset liquidity or atomic debt-rebalance action

**Desired effect**

- Approve or spend more than one asset.
- Produce one or more assets/positions.
- Preserve atomic minimum/maximum bounds across the combined action.

**Pressure on the PoC model**

- The PoC deliberately allows one effect and one capability consumption.
- Multiple independent sessions lose atomicity and may leave intermediate
  economic exposure.
- Generalizing to arbitrary batches would recreate the executor problem.

**Gate**

The product must either exclude these actions, define a small finite set of
typed multi-asset primitives, or redesign the capability model before freezing
the permanent core.

### 13.3 Future payment state with cancellation and retry

**Desired effect**

- Versioned payment rail.
- Retryable notification or synchronization.
- Explicit cancellation proof.
- Partial use followed by terminal settlement/refund.
- Helper succession while a commitment remains live.

**Pressure on the PoC model**

- `CommitmentView` has one fixed schema shared by two PoC modes.
- Core functions and state constants hardcode both payment lifecycles.
- A future rail cannot add fields or transitions to immutable bytecode.
- Externalizing all rail state may weaken wallet-held reservation and replay
  guarantees.

**Gate**

The production candidate needs either a deliberately versioned generic
commitment envelope with bounded rail adapters, a finite frozen first-release
rail set, or a narrower product promise. “Add another mode later” is not valid
for immutable code without a predesigned interpretation path.

### 13.4 Initial result

The PoC core is not a production freeze candidate—as its own contract documents
already state. The exercises do not reject non-proxy custody; they identify
which narrow future semantics must be anticipated or explicitly excluded before
the production core can become permanent.

## 14. Next evidence

Before asking the owner to finalize D4a/D2:

1. Resolve D4a-0 by confirming whether independent production owner and
   guardian human/quorum custody is operationally staffable.
2. Threat-model Package B's delayed and joint fast paths for stale or forged
   confirmation, replay, veto griefing, unsafe unpause, key loss, and correlated
   owner/guardian compromise. Treat the authority machine as a primary formal,
   invariant, and mutation-testing target.
3. Select and test the Base delay clock and emergency-submission model,
   including sequencer downtime, maximum sequencer drift, L1-origin lag,
   reorg/finality behavior, L1-to-L2 caller aliasing, and controller
   compatibility.
4. Define the minimum successor deployment/address-attestation trust model
   before treating Package C as an evaluable recovery option.
5. Continue the independent challenge of Packages B and C for destination
   substitution, live commitments, broken reservation accounting, and stuck
   positions.
6. Determine whether the first-release working candidate needs Ripe, Morpho,
   x402, MPP, or only the custody trunk; none are assumed.
7. Refine the state candidates and future-family exercises from that evidence.
8. Return the narrowed alternatives, unresolved risks, and reviewer findings to
   the owner for explicit selection.
