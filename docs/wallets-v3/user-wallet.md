# User Wallet v3 — Architecture & Spec

**Status:** DRAFT v9 — PoC-ready per external review; freeze-blockers tracked in §16. (v9: purpose-scoped general 1271; capability schema with beneficiary/resource fields + mechanicalClass/semanticKind split; restored session/bundle commitments; corrected lock semantics + transient mandate; honest commitment packing + executable policySnapshot; idempotent transition notifications; lego callback machine; permanent Tier-C/callback limitations; freeze matrix decisions; B-only and C+B PoC coverage. Prior: v8 mechanisms/lock/rails; v7 tiers/phases; v6 manifest/commitments/ownership root; v5 backpack; v4 ground-up rebuild.)

**Scope:** the user wallet stack only — core, config, backpack modules, extenders. Settlement-side payment infrastructure is out of scope.

**One-line goal:** rebuild the wallet from the ground up — a permanent-address core users never migrate away from, everything else attachable, replaceable, rebuilt fresh.

---

## 1. Build strategy

- **Ground-up rebuild.** Every v3 contract is new; v2 is a requirements reference (§14), never a constraint. Nothing existing is edited. New contracts in `contracts/walletsV3/`, greenfield tests, mock legos/policies.
- **The PoC proves the frozen surface** — and must not accidentally define it. Freeze only after §16 is demonstrated, including the adversarial suite. Exploratory code is disposable.
- **Deployment assumptions stated:** Base (Cancun) — EIP-1153 transient storage is mandatory for all lock/session/capability state (a persistent lock would tax every sponsored action with SSTOREs and invalidate the gas gates).

## 2. Why v3

- Migrations are painful and lossy (address-keyed Ripe positions, locked RIPE, version-coupled config, stale refund addresses).
- Out of code space (v2 config ~720 bytes under EIP-170).
- Gas is sponsored and expensive (v2: ~385k owner→whitelist repeat cross-block; ~482k payee; ~780k first agent-payee; token movement ~10–27k).
- v2 accreted complexity — yield tracking, fees, points, pricing, deleverage — all permanently removed from the wallet.

## 3. Design principles

1. **The wallet address is the user's permanent identity.** Core small enough to audit exhaustively, then frozen.
2. **One wired operational dependency (config)** + the core's own **ownership root** (owner, timelocked transfer, `ownerEpoch`), which outranks config. All other targets dynamically resolved under pinning rules (§5.4).
3. **Mechanics in core, policy behind config** — valuation/fees/points/limit semantics are module-side and swappable forever.
4. **Every new top-level execution frame requires IDLE and acquires its locked phase before the first external call.** Internal wallet effects are permitted only in their designated phase, against the active authorization (§5.2). Cleanup never depends on module good behavior.
5. **No arbitrary-target or unbounded wallet-originated calldata execution.** Opaque *typed* calldata routes only to pinned attached extenders; wallet effects are capability-bound; Tier-C uses a frozen template vocabulary (§5.6).
6. **Funds live only in the wallet;** deferred payments are reserved commitments; no signature path can move value without commitment backing (§5.5a).
7. **Permissions fail closed; trust boundaries explicit** (§5.3): extenders translate intent; legos are trusted enforcement adapters audited at core seriousness.

## 4. Component map

*(unchanged from v8.1 — users/agents → wallet router → extenders → legos → protocols; config + stateless ParamsModule/Sentinel behind sender gates; ModuleBook + ExtenderBook registries; append-only versioned lego ids.)*

| Component | Deployment | Upgradeable? | Holds funds? | Knows about |
|---|---|---|---|---|
| UserWallet (core) | per-user blueprint | **never** | yes — all of it | its config + its own ownership root |
| UserWalletConfig | per-user blueprint | replaceable/recoverable (§6) | no | its modules, registries |
| Backpack modules | shared **stateless** singletons | owner opt-in via ModuleBook | no | config layout |
| Extenders | shared singletons | bundle attach; two-level lifecycle (§8) | no | legos, protocols |
| Legos | shared singletons | append-only versioned; **trusted enforcement adapters** | transient only | one protocol each |

Attachment state: core stores active attachments (address, codehash, epoch, local status, selector routes, **compact bundle/registration id** — full bundle metadata is never copied per wallet); config stores pending proposals/timelocks/policy.

## 5. UserWallet core (permanent)

**Ownership root** — owner + timelocked transfer + `ownerEpoch` (bumped on transfer; invalidates pending proposals). Includes the core emergency freeze (§5.7). The only unconditional authority when config is unhealthy.

**Custody & transfer** — `transferFunds`: config validate-and-consume (nonpayable, atomic), spends `available = max(balance − reserved, 0)`; batch = shared auth, per-transfer validation. ETH + ERC-20, `__default__`, `onERC721Received`.

### 5.1 Execution mechanisms — cumulative, per versioned action tuple

| Mechanism | Protection |
|---|---|
| **A — loss containment** | exact approvals / balance-loss bounds, wherever an allowance is involved |
| **B — semantic consumption** | lego consumes a semantic commitment + typed budgets before effects — applies to *all* protocol interactions |
| **C — wallet-originated call** | frozen-template CALL (native value, operator grants, wallet-as-msg.sender); always +B, +A where applicable |

Vault deposit / swap / add-liquidity = A+B; borrow / removeCollateral = B; WETH wrap / operator grant = C+B. Classification key: `(extender version, actionId/selector, lego version, verb/schema version, dependency policy)`.

**Capability schema** (committed at `openSession`, config-approved; exact encodings are PoC deliverables, the shape is not):

```
Capability { id, legoRef, verbId, schemaId, semanticHash,
             beneficiaryMode, approvedBeneficiary, maxUses }
Budget     { capabilityId, mechanicalClass, semanticKind, resourceId, maxAmount }

mechanicalClass (permanent core enum): SPEND | LIABILITY | ASSET_RELEASE | NFT | NATIVE | AUTHORITY
semanticKind (registered, open-ended):  e.g. keccak256("RIPE_DEBT_INCREASE_V1")
```

Core understands only the six mechanical classes — new protocol effects register new `semanticKind`s under an existing class with **no core change**. The manifest carries a **bounded canonical semantic payload** (schema-validated) so Sentinel can police policy-relevant fields — approved vaults/pools, recipients, minOut, position ids, lock periods — while the core only commits to the canonical hash. Beneficiary is a **typed field** (`beneficiaryMode` + `approvedBeneficiary`), mechanically enforced by core — never inferred from a hash.

`consumeCapability(capabilityId, semanticHash, budgetLeaves[])` — session-resolved lego only; hash computed from actual typed args (domain-separated by lego version + verb + schema) immediately before the effect. Encoding validation rejects: duplicate capability ids, duplicate/overlapping budget keys, unknown mechanical classes, wrong schema versions, noncanonical leaf ordering, missing mandatory leaves, consumption overflow. **Manifest cardinality maxima fixed pre-freeze.**

### 5.2 Execution lock + phase machine (transient storage mandated)

```
IDLE → DISPATCHING → ACTIVE → SETTLING → CALLBACK → IDLE      (sessions)
IDLE → DIRECT_EXECUTING → IDLE                                 (transfers/batch)
IDLE → COMMITMENT_SETTLING → IDLE                              (settle/sync/refund/cleanup)
IDLE → ANSWER_CALLBACK → IDLE                                  (non-static answer-only forwards)
```

- **Top-level frames require IDLE; the phase is set before the first external call** (config, Sentinel, extenders, tokens, native recipients, rail adapters, handlers). Internal effects (Tier-C during ACTIVE, fee adjustment during SETTLING, hook during CALLBACK) run only in their designated phase against active authorization.
- Answer-only handlers use STATICCALL where possible; otherwise ANSWER_CALLBACK with gas/returndata caps.
- `isValidSignature` answers only in global IDLE (prevents mid-session external pulls). **Stated limitation:** a protocol cannot verify this wallet's signature during the wallet's own session — permit-style flows inside extender actions are unsupported; any future exception requires a session-approved digest capability designed into core, not a Sentinel change.
- Config refuses mutations unless the wallet reports not-busy.
- **Session commitment (transient, complete list — restored):** attachmentKey/version · extender address + codehash · attachment epoch · **bundleHash** · registry lifecycle result/epoch · selector + route-derived actionId · calldata hash · manifest hash · config address + configEpoch · ownerEpoch · signer · session nonce · resolved target/codehash root · capability/schema root · hook flags. Nothing mutable is re-resolved mid-session.
- **bundleHash covers:** extender version/codehash, manifest schema, capability/effect schemas, mechanism set, lego versions, dependency policies, rail adapters, Tier-C template version, hook behavior, exit selectors, required core version — plus the signed tier checklist (§17).
- SETTLING→CALLBACK ordering as v8 (approvals zeroed first; postconditions; policy; bounded adjustment; final postconditions; authority revoked; capped best-effort hook; IDLE). One active session; sequential sessions with fresh nonce; mutable state revalidated per session.

### 5.3 Trust boundaries

1. **Calldata → manifest:** extender translates intent; containment begins at the config-approved manifest (pinned, timelocked bundle attach, revocable). Optional later: caller-signed intents.
2. **Manifest → effect:** core-enforced (budgets, semantic consumption, postconditions). Legos are trusted enforcement adapters under an explicit contract: every effect path requires `msg.sender == wallet.activeExtender()` and `_user ==` active wallet; consumption strictly before effects; outputs forced to the wallet unless the capability's beneficiary field says otherwise; no bypass entry points; operator access unusable through unguarded functions. **Protocol callbacks into legos get their own machine:** the lego enters `EXPECTING_CALLBACK(protocol, selector, wallet, semanticHash, maxCalls)` when the active extender initiates, accepts exactly the expected callback, consumes only pre-authorized capability/budget state, and clears the context transactionally — namespaced per wallet (one shared lego may serve multiple wallets per tx).

### 5.4 Dependency pinning — with the honest qualification

Registration classifies each lego dependency: immutable / append-only versioned / owner-approved root / **governance-mutable (disclosed)**. The no-forced-code invariant is qualified precisely: Underscore-controlled executable dependencies cannot widen without a new owner-approved bundle; **third-party proxies/governance are external risks explicitly accepted at attachment** (a proxy upgrade changes behavior without changing codehash — surfaced in attachment UX/events); parameter-only dependencies move only within committed policy; pause/narrow-only actions may stay governance-controlled. Attached-version metadata can only narrow. Owners attach **bundles** (referenced per wallet by compact id).

### 5.5 Commitments (deferred outbound value)

Packed layout target **≤5 words, hard ceiling 6** — achieved via compact registry ids (verifier/adapter), a policy-record id or hash, derived protocol nonce (from commitment id), narrow checked amounts/timestamps; exact bit layout demonstrated pre-freeze. **Total system storage reported separately:** `reserved[asset]`, replay tombstone, per-wallet pending-commitment counter, extender metadata, failed-notification retry state.

Fields: binder + binderEpoch, verifier id, rail-adapter root, asset, originalAmount, remainingLiability, **cumulative settled (or hasSettled bit)** — settle 5 then refund 5 must resolve terminal state unambiguously (SETTLED if any settlement occurred and liability is zero; REVOKED only if fully refunded with none) — destination, window, mode, state, **policySnapshot hash**, **transitionNonce**.

- **Modes:** EXTERNAL_EXACT (x402: full pull / full revoke / expiry only; no partial release under a valid digest) · RESERVED_TRANSFER (MPP: `settleReservedTransfer(id, amount)` transfers to the **stored** destination; `refundReserved(id, amount)` **releases reservation back to this wallet's available balance — no token transfer**; state + reservation updated before external transfer, under the lock; refunds never restore consumed limits).
- **policySnapshot — executable, model chosen:** core stores the hash; settlement callers supply the bounded `PolicyTerms` preimage; core verifies and enforces — works even if config is broken. Fees on externally-completed pulls: reserved at authorization if applicable, otherwise **best-effort/accounting-only** — sync never reverts for an unavailable fee.
- **Idempotent, retryable notification:** every commitment transition (settle, refund, cancel, expire, cleanup — not just x402 sync) notifies policy **non-bubbling**, identified by `keccak256(commitmentId, transitionNonce)`; core tracks monotonic nonce + cumulative totals, config records latest applied — a later successful notification catches policy up; retries can never reapply fees, double-consume limits, or apply stale transitions. (Synchronous session `onSettle` still bubbles — atomic revert is correct there.)
- **Authority matrix (per rail adapter registration):** x402 sync permissionless with conclusive on-token evidence; MPP settlement per adapter proof (never assumed-safe permissionless); refunds per defined authority; expiry permissionless after deadline; cancel/`cleanupInvalidBinder` check external-pull evidence first (including pre-HARD_REVOKE pulls).
- **Adapter liveness:** a pre-approved compatible adapter set/root is committed at authorization; after the commitment window passes, **expiry releases the reservation without adapter cooperation** (timeout fallback). Governance can never substitute an adapter that fabricates evidence (append-only + authorization-bound root).

### 5.5a EIP-1271 — two strictly separated perimeters

**Rail-backed (commitment) validation:** MAGIC iff an ACTIVE, unexpired commitment matches the hash, binder attached at recorded epoch, wallet globally IDLE. Caller-binding to verifier = Base-fork test decision. Terminal (revoked/expired/settled) rail digests **never fall through to the general path**; commitment lookup takes precedence.

**General-signature path (reserved, ships disabled) — purpose-scoped, not generic:** a versioned signature envelope `{validationMode, purposeId, validatorId, ownerEpoch, nonce, deadline, signature}` validated by owner-timelocked, purpose-scoped validators via config/Sentinel. Hard rules: **value-moving verifiers (tokens, Permit2, settlement conduits) can never be satisfied here — value movement requires the commitment/reservation path, no exceptions** (otherwise an owner-signed EIP-3009 digest would bypass reservations entirely); fails closed on unknown versions, malformed returndata, or validator revert; always fails during emergency freeze, recovery, and every non-IDLE phase; binds chain, wallet, ownerEpoch, nonce, deadline. Initial enablement, if any: an explicit **authentication purpose only** (sign-in-with-wallet). Order-signing is potentially value-moving and gets its own purpose review — and if value-moving general signatures are ever enabled, they become a **seventh outflow-authority class** added to invariant 2 explicitly.

### 5.6 Tier-C templates & router — permanent limitations, stated plainly

**The template vocabulary is frozen with the core.** Each template freezes: id + schema, target/selector source, argument order + core-forced fields, native value + gas behavior, returndata handling, reservation treatment, required semantic capability, reversal/emergency behavior, NFT approve vs `setApprovalForAll` restrictions. A future call shape outside the vocabulary is **unsupported by this core** unless the operation is redesigned so a lego becomes the caller — a registry cannot teach frozen core a new template. The PoC proves one independently-chosen fitting shape *and* one intentionally-unsupported shape that must reject.

**Privileged wallet callbacks are permanently unsupported:** privileged protocol callbacks must terminate at a lego (via §5.3's EXPECTING_CALLBACK machine); protocols requiring the *wallet itself* to perform a privileged callback are out of scope for this core, permanently. (No disabled permit mechanism is reserved — a speculative callback surface without a concrete protocol requirement is worse than the limitation.)

Router: fail-closed; `executeAttached(attachmentKey, calldata)` keyed to the exact attached version, restricted to registration-pinned exit/refund/sync capabilities.

### 5.7 Emergency freeze + recovery matrix (decisions)

- **Freeze:** owner, or a security signer attested by a *healthy* config, freezes immediately. **Unfreeze: owner only, timelocked.**
- While frozen: general 1271 always fails; existing rail commitments either explicitly survive (sync/expiry continue) or are explicitly HARD_REVOKED — never incidentally; MPP maintenance (sync, cancel, expire, cleanup) stays enabled; new sessions, transfers, and authorizations blocked except the risk-reducing set.
- **Risk-reducing liveness route:** frozen exits must not wait on RECOVER_FRESH's long timelock — the core provides an **owner-only route to registration-pinned risk-reducing selectors** (debt repayment, collateral top-up, DRAIN exits, operator revocation, commitment maintenance) that functions even when config is broken. Scope: exactly the registration-pinned exit capability set, nothing else.
- Both MIGRATE and RECOVER_FRESH increment `configEpoch`. Eject semantics, operator/NFT recovery under freeze, and the full matrix (which actionIds are risk-reducing) are the §16 deliverable.

**Explicitly NOT in core, permanently:** pricing, yield tracking, fee logic (beyond the bounded adjustment), points, WETH wrap, deleverage, lego interfaces, USD-anything.

## 6. UserWalletConfig — state + gates, policy-free

*(Structure as v8.1; deltas only.)* Hooks: `validateAndConsumeTransfer`; `authorizeSession` + target resolution in one traversal (returns targets + hook bitmap); `onSettle(report) → bounded adjustment`; core passes an authenticated authority class (config never calls back to re-read owner). All per-wallet **policy** state lives here (core keeps ownership, attachments, commitments, epochs, lifecycle). Amount-denominated limits for now; USD returns as a Sentinel upgrade. Writes sender-gated to stateless modules; module succession via ownership root. Replacement/recovery: **MIGRATE** (freeze → chunked copy → committed identities/schema/counts → reject-if-changed → `configEpoch++`) and **RECOVER_FRESH** (longer timelock, under core emergency freeze; conservative empty config; abandons inaccessible policy state; preserves funds/commitments/attachments/owner/epochs; `configEpoch++`).

## 7. Backpack modules

*(As v8.1.)* Stateless ParamsModule + Sentinel in ModuleBook; state in config behind sender gates; later: payee/cheque policy, fee/points policy, accounting adapters; Migrator's successor = the replacement copier.

## 8. Extenders

*(As v8.1, plus:)* registration metadata includes the **tier checklist artifact** (§17) inside `bundleHash`; CLOSED is operational, never an on-chain proof; per-wallet closure locally provable; core commitment state canonical, extender storage supplemental/reconcilable; attaching v2 auto-DRAINs v1 locally; detach = HARD_REVOKE with evidence-checked cleanup.

## 9. Flows

*(As v8.1 — yield A+B with EXPECTING_CALLBACK if the protocol calls back; x402 EXTERNAL_EXACT with IDLE-only 1271 + preimage-verified policy terms at sync; owner transfer via DIRECT_EXECUTING.)*

## 10. PoC scope

*(As v8.1, plus:)* purpose-scoped general-1271 envelope (disabled path, validated shape); policySnapshot preimage flow; transition-nonce notification; lego EXPECTING_CALLBACK machine; owner-only risk-reducing route under freeze.

## 11. PoC build order

1. **Minimal direct transfer** + config/Sentinel — hot-path budget first.
2. **YieldExtender + mock lego** — A+B: phase machine, manifest, budgets, semantic consumption, postconditions, epilogue; direct-vs-mediated cost comparison.
3. **Mock debt lego (borrow / removeCollateral)** — **B-only, no-allowance liability actions**: semantic-hash enforcement where approval budgets protect nothing; the verbs that caused the central architecture correction get first-class coverage.
4. **Tier-C templates** — **C+B**: WETH/native-value template, operator grant + emergency revoke, NFT template if retained; plus the fitting/unsupported mock-future-protocol pair.
5. **PayExtender-x402 on forked Base USDC** — EXTERNAL_EXACT, sync + preimage policy terms, 1271 caller-binding decision, non-bubbling notification.
6. **Mock MPP flow** — partial settle/refund with cumulative-settled tracking, authority matrix, transition-nonce retry/idempotency, onSettle bounds/failure.
7. **Adversarial suite** — as v8.1, plus: general-1271 bypass attempts (owner-signed EIP-3009 through the general path must fail), terminal-digest fall-through, mid-session lego-callback abuse (EXPECTING_CALLBACK), settle-then-refund terminal states, notification replay/stale-transition attempts, frozen-state matrix (each risk-reducing path works; everything else blocked).
8. Freeze provisional selectors/storage; audit-oriented build.

## 12. Gas strategy

*(v8.1 gates retained: <~190k must-have / 125–150k stretch hot path; router+empty session <~60k with contents defined; core bytecode ≤16KB; full ERC-4337 sponsored envelope.)* Additions:

- **Transient storage mandated** for lock/session/capability state (deployment assumption, §1).
- consumeCapability: warm **base** target + **per-budget-leaf marginal** target; first vs repeated use benchmarked.
- One-item vs maximum-cardinality manifests; **realistic minimal session gets an acceptance ceiling, not just a report**.
- Attachment storage budget (slots per attachment/selector/bundle-id); bundle metadata never copied per wallet.
- Commitment cost includes the pending-commitment counter; **6-word hard ceiling / 5-word target** with demonstrated bit layout.
- Fixed gas/returndata caps for extender hooks and policy notifications; benchmark disabled/success/revert/exhausted hooks.
- 1271 benchmarks: rail hit, disabled-general miss, enabled-general validation, adversarial calldata.
- Config runtime + combined core+config deployment ceilings; optimizer-mode comparison (`codesize` vs `gas`).
- **A defined, measurable v2-vs-v3 sponsored-UserOperation improvement requirement** (not just L2 execution).
- Standing disclaimer: amount-only PoC ≠ feature-equivalent to v2 pricing/points behavior.

## 13. Accounting

*(As v8.1 — no core asset registry; events + indexing canonical; read-only adapters per ExtenderBook metadata.)*

## 14. Requirements inventory

*(As v8.1 table — unchanged dispositions.)*

## 15. Security invariants

1. Every fund- or position-affecting action executes in a wallet-owned frame with the real caller authenticated.
2. **Wallet-authorized outflow authority or new principal liability is initiated only via:** (1) config-authorized direct transfer; (2) capability-bound session execution (cumulative mechanisms per registered tuple); (3) rail-bound deferred pull against an ACTIVE commitment; (4) atomic reserved settlement/refund; (5) persistent operator grants (Tier-C templates, emergency-revocable); (6) enumerated emergency/cutover primitives. General-signature validation can never authorize value movement — if that ever changes, it is added here as an explicit seventh class first. Asynchronous protocol effects (interest, liquidations, rebases) are handled by accounting, not prevented.
3. Every new top-level frame requires IDLE and takes its phase before any external call; internal effects only in designated phases; `isValidSignature` answers only in IDLE; lock/session state is transient.
4. Committed value is reserved; `available` saturates; limits consumed at authorization, never twice; EXTERNAL_EXACT never partially releases under a valid digest; refunds don't restore limits; terminal states unambiguous (cumulative settled tracked); notifications idempotent per transition nonce.
5. Approvals exact, manifest-budgeted, session-scoped, zeroed before settlement hooks.
6. Parameter-sensitive effects require semantic consumption with typed beneficiary/resource fields; budgets per mechanical class; unknown classes/kinds/schemas revert.
7. Trust boundaries per §5.3; legos audited at core seriousness; lego callbacks only through EXPECTING_CALLBACK contexts; dependency pinning per §5.4 with the third-party-risk qualification stated.
8. Fail closed everywhere: unknown selectors, ids, capabilities, envelope versions, validator errors.
9. Detach = HARD_REVOKE with evidence-checked cleanup; DRAIN_ONLY preserves exits via exact-version `executeAttached`; CLOSED is operational.
10. No delegatecall; no arbitrary-target or unbounded wallet-originated calldata; Tier-C vocabulary and privileged-callback exclusion are permanent, stated limitations.
11. Governance can never force or widen code on an existing wallet (append-only registries, narrow-only metadata, bundle re-attach for any widening); third-party proxy risk is disclosed and owner-accepted at attachment.
12. Ownership root outranks config; freeze/unfreeze per §5.7 with the owner-only risk-reducing route; recovery paths exist for every config failure mode; commitment maintenance survives config/extender/policy failure.

## 16. Pre-freeze vs post-freeze

**Pre-freeze (PoC must prove):** phase machine incl. ANSWER_CALLBACK + transient mandate; capability/budget encodings (beneficiary fields, mechanical classes, semantic kinds, rejection rules) + canonical payload for Sentinel + manifest maxima; complete session/bundle commitment lists; lego adapter contract incl. EXPECTING_CALLBACK; dependency qualification; commitment bit layout (≤6 words) + policySnapshot preimage flow + cumulative-settled tracking + transition-nonce idempotency + adapter-root liveness fallback; purpose-scoped general-1271 envelope (disabled but validated); rail authority matrix; Tier-C frozen vocabulary + fitting/rejecting mock proofs; permanent callback exclusion; freeze/recovery matrix incl. owner-only risk-reducing route + commitment survival rules; both recovery modes; component gas/storage/bytecode gates incl. acceptance ceilings; lean two-step sign-off with the **checklist artifact committed into bundleHash** (max loss/liability, required caller, classes/kinds, beneficiaries, persistent authority, dependencies + admins, callback behavior, freeze/DRAIN behavior, adversarial tests, residual trust — the reviewer approves the artifact, not a tier label).

**Post-freeze:** replacement copier; payee/cheque policy; pricing/USD Sentinel; fee/points policy; accounting adapters; agent-stack integration; cutover tooling; ERC-1155 receiver; benchmark expansion.

## 17. Decisions & remaining open questions

**Resolved:** general-1271 reserved path IN — **purpose-scoped per §5.5a** (initial enablement, if any: authentication only). Tier sign-off: lean two-step (builder proposes schema + mechanisms + adversarial tests → one independent technical reviewer approves the **checklist artifact**; timelocked registration + owner attach do the rest).

**Open:**
1. **Attach timelock minimum.**
2. **Manager model for PoC** (flat allowlist + caps + classes + period counters) — confirm.
3. **Contracts location** (`contracts/walletsV3/`), registry split — confirm.
