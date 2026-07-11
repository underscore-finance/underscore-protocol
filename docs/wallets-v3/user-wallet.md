# User Wallet v3 — Architecture & Spec

**Status:** DRAFT v10 — **self-contained normative spec** (no reliance on prior drafts); PoC steps 1–7 green-lit by external review; provisional freeze (step 8) gated on §16. Changes this revision: core-computed semanticHash binding; purpose-domain general-1271 digests; config-independent proofs for the frozen risk-reducing route; publicly reconstructible PolicyTerms; commitment-bound freeze behavior; complete callback contexts; permanent commitment-mode limitation; PoC registry/timelock simplifications (Mick); restored full text of all sections.

**Scope:** the user wallet stack only — core, config, backpack modules, extenders. Settlement-side payment infrastructure (bridging, batching, off-ramps) is out of scope.

**One-line goal:** rebuild the wallet from the ground up — a permanent-address core users never migrate away from, with everything else attachable, replaceable, and rebuilt fresh.

---

## 1. Build strategy

- **Ground-up rebuild.** Every v3 contract is new; v2 is a requirements reference (§14), never a constraint. Nothing existing is edited — the live stack stays in production. New contracts in `contracts/walletsV3/`, greenfield tests in `tests/walletsV3/`, mock legos/policies.
- **The PoC proves the frozen surface** — and must not accidentally define it. Core ABI/storage freeze only after §16 is demonstrated in skeletal code, including the adversarial suite (§11). Exploratory code is disposable.
- **PoC simplification rules (decided):** *no registry-governance queues and no meaningful waiting* — but core-owned authority transitions (pending owner, pending config destination/hash, pending unfreeze) keep their minimal **permanent state shapes** — proposal argument commitment + owner/config epoch + cancellation/replay protection + executed/cancelled state — instantiated with a **runtime/constructor-set delay of zero** (not a compile-time zero constant, which lets the optimizer strip branches and understate frozen bytecode; adding these fields after storage freeze would invalidate the exercise). Do not build: delay schedules, governance executors, queues, multisigs, production cancellation UX, registry proposal machinery. **No ModuleBook** (config points directly at ParamsModule/Sentinel); **no LegoBook rebuild** (reuse existing v2 registry code in fixtures; append-only versioned ids are a production registration policy); **ExtenderBook minimal but production-shaped where it matters** — deployer-owned and immediate, yet **write-once/content-addressed**: an existing registration id can never change bundle contents, re-registration mints a new id, `bundleHash` is never overwritten, lifecycle is stored apart from immutable metadata, and records carry a stable `familyId` (so attaching Yield v2 auto-DRAINs Yield v1 — not an unrelated extender claiming succession). Its metadata schema and **hot read ABI/storage shape are load-bearing** (the session machine reads them; governance *writes* may differ from production, hot lookups may not). Attachment **epochs + instant detach are kept** — core storage semantics under adversarial test, not hardening. Real timelocks, append-only enforcement, and narrow-only metadata rules belong to the post-freeze audit-oriented build.
- **Deployment assumptions:** Base (Cancun). **EIP-1153 transient storage is mandatory** for all lock/session/capability state — enforced operationally: compiler EVM target fixed to Cancun, deployment chain/factory guard, no persistent-fallback build, cross-transaction state-clearing tests, revert + sequential-session transient tests.

## 2. Why v3

- **Migrations are painful and lossy.** External positions keyed to the wallet address (Ripe collateral/debt, locked RIPE) can't move; config cloning is version-coupled with no on-chain version tag; pending payment refunds keyed to old addresses go stale.
- **Out of code space.** v2 UserWalletConfig sits ~720 bytes under EIP-170; new payment protocols can't bolt onto the monolith.
- **Gas is sponsored and expensive.** v2 production baseline: ~385k tx-equiv (owner→whitelist repeat, cross-block), ~482k payee repeat, ~780k first agent-payee — of which actual token movement is ~10–27k (docs/gas-profiling/).
- **v2 accreted complexity.** Yield tracking, fee capture, points, pricing, and deleverage are woven through every wallet verb; all permanently removed from the wallet.

## 3. Design principles

1. **The wallet address is the user's permanent identity.** The core is small enough to audit exhaustively, then frozen.
2. **One wired operational dependency: config** — plus the core's own **ownership root** (owner + timelocked transfer + `ownerEpoch`), the authority that outranks config. All other targets are dynamically resolved under pinning rules (§5.4).
3. **Mechanics in core, policy behind config.** Core: custody, gates, sessions, approval hygiene, commitments, balance diffs. Policy (valuation, fees, points, limit semantics): config-side, swappable forever. Yield tracking is permanently out of the wallet.
4. **Every new top-level execution frame requires IDLE and acquires its locked phase before the first external call.** Internal wallet effects run only in their designated phase against the active authorization (§5.2). Cleanup never depends on module good behavior.
5. **No arbitrary-target or unbounded wallet-originated calldata execution.** Opaque *typed* calldata routes only to pinned attached extenders; wallet effects are capability-bound; Tier-C uses a frozen template vocabulary (§5.6). Extender→lego interaction is plain typed Vyper.
6. **Funds live only in the wallet.** No module custody beyond metered session windows; deferred payments are reserved commitments; **no signature path can move value without commitment backing** (§5.5a).
7. **Permissions fail closed; trust boundaries are explicit** (§5.3): extenders translate intent; legos are trusted enforcement adapters, audited at core seriousness.

## 4. Component map

```
 users / agents / integrators — always call the one permanent wallet address
                    │
                    ▼  (typed Extender ABIs via selector router)
   ┌───────────────────────────────────────────────┐
   │  USER WALLET (core, frozen)                   │
   │  ownership root · custody · transfer gates ·  │      ┌──────────────────┐
   │  execution lock + phase machine ·             │      │      LEGOS       │
   │  commitments · approvals · EIP-1271 · router  │      │ typed calls from │──▶ external
   └──────────────┬───────────────▲────────────────┘      │ extenders;       │    protocols
                  │ CALL          │ session primitives    │ semantic         │
                  ▼               │ + consumeCapability   │ self-report ────┼──▶ wallet
   ┌──────────────────────────────┴────────────────┐      └─────────────────┘
   │  EXTENDERS (no-custody singletons, swappable) │──────────────▲ typed extcall
   │  Yield · Swap · Debt · Liquidity · Rewards ·  │──────────────┘
   │  Pay-x402 · Pay-MPP · future protocols        │
   └───────────────────────────────────────────────┘
   core's one wired address
                  │
   ┌──────────────▼────────────────────────────────┐      ┌───────────────────────────┐
   │  USER WALLET CONFIG (state + gates,           │◀─────│  BACKPACK MODULES (shared │◀── owner /
   │  replaceable) — permissions · payees ·        │ sender│  stateless singletons)    │    managers
   │  whitelist · pending proposals · hooks        │ gated │  ParamsModule · Sentinel  │
   └──────────────────────┬────────────────────────┘ writes└───────────────────────────┘
                          └─── read hooks delegate decisions ───────▶ Sentinel
```

| Component | Deployment | Upgradeable? | Holds funds? | Knows about |
|---|---|---|---|---|
| UserWallet (core) | per-user blueprint | **never** | yes — all of it | its config + its own ownership root |
| UserWalletConfig | per-user blueprint | replaceable/recoverable via core state machine (§6.5) | no | its backpack modules, registries |
| Backpack modules | shared **stateless** singletons | owner opt-in (production: ModuleBook; PoC: direct pointers) | no | config layout; later policy deps |
| Extenders | shared singletons | ExtenderBook + bundle attach; two-level lifecycle (§8) | no | legos, external protocols |
| Legos | shared singletons | governance registry (production: append-only versioned ids); **trusted enforcement adapters** | transient only | one external protocol each |

**Attachment state has one canonical home:** the core stores active attachments — address, codehash, epoch, local lifecycle status, selector routes, **compact content-addressed registration id AND the exact `bundleHash`** (stored at attachment so the frozen risk-reducing route can verify proofs without config, §5.7; a registry must never return different metadata for an attached id). Config stores pending proposals, timelocks, owner policy. Full bundle metadata is never copied per wallet.

## 5. UserWallet core (permanent)

**Ownership root** — owner + timelocked transfer + `ownerEpoch` (bumped on transfer; invalidates pending config/module/attachment proposals). The only unconditional authority when config is unhealthy. Includes the core emergency freeze (§5.7).

**Custody & transfer** — `transferFunds(recipient, asset, amount, ...)`: config validate-and-consume hook (nonpayable — decision and counters atomic; failed transfer reverts counters with the tx), spends `available = max(balance − reserved, 0)` (saturating). Batch variant: shared authentication/context, per-logical-transfer validation and counters. ETH + ERC-20 custody, `__default__` receive, `onERC721Received`.

### 5.1 Execution mechanisms — cumulative, per versioned action tuple

| Mechanism | Protection |
|---|---|
| **A — loss containment** | exact approvals / balance-loss bounds; applies wherever an allowance is involved |
| **B — semantic consumption** | lego consumes a semantic commitment + typed budgets before external effects; applies to *all* protocol interactions (an allowance bounds loss but not vault, output token, minOut, ticks, lock period, recipient) |
| **C — wallet-originated call** | frozen-template CALL from the wallet itself (native value, operator grants, wallet-as-msg.sender); always +B, and +A where applicable |

Vault deposit / swap / add-liquidity = **A+B**; borrow / removeCollateral = **B**; WETH wrap / operator grant = **C+B**. Classification key: `(extender version, actionId/selector, lego version, verb/schema version, dependency policy)` — never per verb name alone.

**Capability schema** (committed at `openSession`, config-approved):

```
Capability { id, legoRef, verbId, schemaId, semanticHash,
             beneficiaryMode, approvedBeneficiary, maxUses }
Budget     { capabilityId, mechanicalClass, semanticKind, resourceId, maxAmount }

mechanicalClass (permanent core enum): SPEND | LIABILITY | ASSET_RELEASE | NFT | NATIVE | AUTHORITY
semanticKind (registered, open-ended):  e.g. keccak256("RIPE_DEBT_INCREASE_V1")
```

- Core understands only the six mechanical classes; new protocol effects register new `semanticKind`s under an existing class — no core change. `setApprovalForAll`-style operations are **AUTHORITY**, not NFT.
- **Core-computed hash binding:** at `openSession` the core itself computes
  `semanticHash = keccak256(domain(chainId, wallet, bundleHash, legoVersion, verbId, schemaId) ‖ canonicalSemanticPayload)`
  from the bounded canonical payload it received — the same payload Sentinel inspects for policy (approved vaults/pools, recipients, minOut, position ids, lock periods). An extender can never show Sentinel a benign payload while committing a different hash: Sentinel, core, and lego all bind to one preimage. **Golden test vectors** shared by extender, lego, Sentinel validator, core, and off-chain tooling define dynamic arrays, defaults, signed ints, token ordering, native representation, NFT ids, MAX_UINT256, partial fills, protocol bytes.
- **Beneficiary is mechanically enforced:** typed `beneficiaryMode`/`approvedBeneficiary` on the capability, and the lego passes `actualBeneficiary` as a **typed consumption argument** (not buried in the hash) — core compares directly.
- **Semantic-only capabilities:** `semanticHash + maxUses` with zero budget leaves is valid when the registered schema declares no quantitative leaf (vote, claim, mode change, lock-duration change, delegation). "Missing mandatory leaves" is schema-specific.
- `consumeCapability(capabilityId, semanticHash, actualBeneficiary, budgetLeaves[])` — session-resolved lego only, hash computed from actual typed args immediately before the effect. Encoding validation (O(n) via canonical ordering/adjacent checks — no nested scans) rejects: duplicate capability ids, duplicate/overlapping budget keys, unknown mechanical classes, wrong schema versions, noncanonical leaf ordering, missing schema-mandatory leaves, consumption overflow.
- **Manifest cardinality maxima** (assets, capabilities, approvals, NFTs, lego calls per session) fixed pre-freeze — they set Vyper bounded types and worst-case gas.

### 5.2 Execution lock + phase machine (transient storage mandated)

```
IDLE → DISPATCHING → ACTIVE → SETTLING → CALLBACK → IDLE      (sessions)
IDLE → DIRECT_EXECUTING → IDLE                                 (transfers/batch)
IDLE → COMMITMENT_SETTLING → IDLE                              (settle/sync/refund/cleanup)
IDLE → ANSWER_CALLBACK → IDLE                                  (non-static answer-only forwards)
```

- **Top-level frames require IDLE; the phase is set before the first external call** (config, Sentinel, extenders, tokens, native recipients, rail adapters, handlers). Internal effects — Tier-C during ACTIVE, fee adjustment during SETTLING, hook during CALLBACK — run only in their designated phase against active authorization.
- **DISPATCHING:** router authenticates the real caller (transient `sessionSigner`), derives `actionId` from the route (never extender-supplied), CALLs the extender with original calldata unchanged. Only the route-bound extender may call `openSession(manifest)`, exactly once; nothing fund-moving works yet; nested router calls, transfers, and commitment ops revert.
- **ACTIVE:** config authorized `(signer, actionId, manifest)`; balances snapshotted; session primitives + consumeCapability only; config/attachment/module mutations prohibited. **Expected receiver hooks during ACTIVE:** only manifest-declared receiver selectors, with expected collection/token id/operator; they cannot open sessions, consume capabilities, approve, or move funds; they return directly to ACTIVE; unexpected receiver callbacks revert; SETTLING/CALLBACK reject them unless explicitly required.
- **SETTLING → CALLBACK (fixed order):** (1) zero every approval granted this session; (2) compute diffs, enforce mechanical postconditions — input loss ≤ manifest max per asset, cumulative budgets respected, resolved targets unchanged, NFT round-trips hold; (3) config settlement policy; (4) apply bounded adjustment; (5) final postconditions incl. fee+outflow ≤ authorized; (6) revoke session authority; (7) CALLBACK: optional `needsAfterSessionHook` — gas- and returndata-capped, reentrancy-locked, best-effort, success/failure logged, routing/outflows still locked; (8) IDLE.
- `isValidSignature` answers only in global IDLE. **Stated limitation:** a protocol cannot verify this wallet's signature during the wallet's own session — permit-style flows inside extender actions are unsupported; any exception would need a session-approved digest capability designed into core.
- Answer-only handlers use STATICCALL where possible; otherwise ANSWER_CALLBACK with gas/returndata caps. Config refuses mutations unless the wallet reports not-busy.
- **Session commitment (transient, complete):** attachmentKey/version · extender address + codehash · attachment epoch · bundleHash · registry lifecycle result/epoch · selector + route-derived actionId · calldata hash · manifest hash · config address + configEpoch · ownerEpoch · signer · session nonce · resolved target/codehash root · capability/schema root · hook flags. Nothing mutable is re-resolved mid-session.
- **bundleHash covers:** extender version/codehash, manifest schema, capability/effect schemas, mechanism set, lego versions, dependency policies, rail adapters, Tier-C template version, hook behavior, exit selectors, required core version, and the signed tier checklist artifact (§17).
- One ACTIVE session at a time; no nesting; **sequential sessions in one tx allowed** (fresh nonce; mutable state — lifecycle, targets, counters, budgets — revalidated per session; only immutable tx context cached).

### 5.3 Trust boundaries (explicit)

1. **User calldata → manifest:** the attached extender translates intent; core containment begins at the config-approved manifest (pinned code, timelocked bundle attach, revocable). Optional later hardening: caller-signed intents checked by Sentinel.
2. **Manifest → effect:** core-enforced (budgets, semantic consumption, postconditions). Semantic parameters are self-reported by **legos — trusted enforcement adapters** under an explicit contract: every public effect path requires `msg.sender == wallet.activeExtender()` for that wallet's live session AND explicit `_user ==` the active wallet; consumption strictly before external effects; outputs/refunds forced to the wallet unless the capability's typed beneficiary says otherwise; no alternate entry point bypasses consumption; persistent operator access unusable through unguarded functions. Legos are audited at core seriousness.
3. **Protocol callbacks into legos — EXPECTING_CALLBACK machine.** Context bound when the active extender initiates: `{wallet, wallet session nonce, active extender, protocol caller, callback selector, capabilityId, semanticHash or callback-data hash, remaining calls}`. Keyed by wallet/session (one shared lego may serve multiple wallets per tx); callback-supplied wallet data can never select the context; cross-wallet/session substitution fails; **nesting prohibited (decided)** — reassessed only if a concrete required integration proves it necessary before freeze; context consumed before callback effects; revert restores counters transactionally; a callback arriving after the initiating lego call returns fails.

### 5.4 Dependency pinning — with the honest qualification

Registration classifies every lego dependency: **immutable target** / **append-only versioned target** / **owner-approved dependency root** / **governance-mutable (disclosed as attachment risk)**. Qualification to the no-forced-code invariant: Underscore-controlled executable dependencies cannot widen without a new owner-approved bundle; **third-party proxies/governance are external risks explicitly accepted at attachment** (a proxy upgrade changes behavior without changing codehash — surfaced in attachment UX/events); parameter-only dependencies move only within committed policy; pause/narrow-only actions may stay governance-controlled. Attached-version metadata can only narrow. Owners attach **bundles**, referenced per wallet by compact immutable id. **Registries are untrusted resolvers:** config resolves a lego address via the registry, but the core verifies it against the attached bundle's lego binding *and* `extcodehash`, commits the exact address/codehash into transient session state, and approvals/consumption accept only that address. Mutating the address behind a registry id after attachment fails closed — no approval granted, replacement lego never called; a new owner-attached bundle is the only acceptance path. (This makes production append-only registration operational policy rather than a hidden core dependency — and it is an adversarial PoC test against the reused v2 registry.)

### 5.5 Commitments (deferred outbound value)

Packed core layout: **target ≤5 words, hard ceiling 6** — compact registry ids for verifier/adapter-root, policy-record id or hash, protocol nonce derived from commitment id, narrow checked amounts/timestamps; exact bit layout demonstrated pre-freeze. **Total system storage reported separately:** `reserved[asset]`, replay tombstone, per-wallet pending-commitment counter, extender metadata, failed-notification retry state — with a total first-touch slot ceiling across core, config, and extender.

Fields: binder + binderEpoch, verifier id, rail-adapter root, asset, originalAmount, remainingLiability, cumulative settled (or hasSettled bit), destination, window, mode, state, policySnapshot (hash), transitionNonce, freezeBehavior.

**Modes — permanently only two.** Future streaming/recurring/partial-external rails must map onto these or are unsupported; a rail adapter cannot add a core state machine (limitation stated alongside Tier-C):

- **EXTERNAL_EXACT** (x402/EIP-3009): exact-amount digest — full pull, full revoke, or expiry only; **no partial reservation release while the digest is valid**.
- **RESERVED_TRANSFER** (MPP-style): `settleReservedTransfer(id, amount)` transfers to the **stored** destination (never caller-supplied); `refundReserved(id, amount)` releases reservation back to this wallet's available balance — **no token transfer**; state + reservation updated before the external transfer, under the lock; refunds never restore consumed limits; terminal state: SETTLED if any settlement occurred and liability is zero, REVOKED only if fully refunded with none (cumulative-settled tracking makes this unambiguous).

**PolicyTerms — executable and publicly reconstructible:** core stores the hash; the complete canonical preimage is **emitted at authorization** (event/calldata) with a fixed maximum byte length (counted in L1-data benchmarks); settlement callers supply the preimage; core verifies and enforces — a future maintenance caller reconstructs terms solely from chain data even if config and extender are dead. Differently-encoded but semantically similar preimages reject. **Failed-fee model (decided): accounting-only.** Merchant-pull finalization and reservation release never revert or stall on a fee — a failed fee transfer releases the fee reservation, emits an unpaid-fee event, and never creates a core liability. If guaranteed fee collection is ever required, it gets its own explicitly-reserved, bounded mechanism designed at that time — not ambiguous headroom.

**Notifications — idempotent, cumulative, retryable:** every commitment transition (settle, refund, cancel, expire, cleanup — not just x402 sync) notifies policy **non-bubbling**, identified by `keccak256(commitmentId, transitionNonce)`; payload is cumulative `{originalAmount, cumulativeSettled, cumulativeRefunded, remainingLiability, terminalState, transitionNonce, policySnapshot}`; config applies only strictly newer nonces and derives deltas from its last accepted state. **A permissionless retry path exists for terminal transitions** whose initial notification failed (there may be no later transition to catch up on). Retries can never reapply fees, double-consume limits, or apply stale transitions. Synchronous session `onSettle` still bubbles (atomic revert is correct there).

**Authority matrix (per rail adapter registration):** x402 sync — permissionless with conclusive on-token evidence; MPP settlement — binder/operator per adapter proof (never assumed-safe permissionless); refunds — defined owner/operator authority; expiry — permissionless strictly after the underlying authorization can no longer settle (validBefore boundary semantics tested inclusive/exclusive); cancel + `cleanupInvalidBinder` — check external-pull evidence first, including pulls that landed before HARD_REVOKE but weren't synced.

**Adapter liveness — bounded, stated precisely:** a pre-approved compatible adapter set/root is committed at authorization; before expiry, failure of every committed adapter may delay sync/cancel/cleanup (accepted); governance cannot insert new adapters (evidence fabrication); after expiry, reservation release requires no adapter; if a real pull occurred but adapters failed until expiry, funds release safely and settlement classification reconciles from token events.

**Freeze behavior is commitment-bound, never config-dependent:** fixed per mode (or per-commitment `freezeBehavior` set at authorization): existing EXTERNAL_EXACT merchant commitments survive freeze unless explicitly HARD_REVOKED; new authorizations fail; sync + expiry remain available; RESERVED_TRANSFER follows its registered maintenance rules. Never incidental.

### 5.5a EIP-1271 — two strictly separated perimeters

**Rail-backed (commitment) validation:** MAGIC iff an ACTIVE, unexpired commitment matches the hash, binder attached at recorded epoch, wallet globally IDLE. Caller-binding to the verifier = Base-fork test decision (facilitator preflight may come from arbitrary callers). **If a hash is or ever was a commitment digest, rail state decides — terminal digests never fall through to the general path.**

**General-signature path (reserved, ships disabled) — mechanically purpose-scoped:** an envelope label is not enough (an owner-signed raw EIP-3009 digest labeled "authentication" is still a signed value-moving digest). The owner signs a **purpose-wrapped digest**:

```
generalAuthDigest = keccak256(GENERAL_AUTH_DOMAIN, chainId, wallet, ownerEpoch,
                              purposeId, validatorId, nonce, deadline, originalHash)
```

so raw EIP-3009/Permit2/order digests can never be relabeled. **Wrapping alone is not sufficient** — a verifier asking about `originalHash` doesn't care that the owner signed a wrapper around it; if the wallet answers MAGIC, value still moves. The binding defense is **schema recomputation**: the envelope carries a bounded canonical purpose payload (e.g. the authentication message); the purpose validator parses it, verifies it conforms to the registered schema, **recomputes `originalHash` from the payload itself**, and only then checks the purpose-wrapped owner signature. A raw EIP-3009/Permit2/order digest can never satisfy this — no valid authentication payload hashes to it. For caller-independent authentication modes, schema validation is the primary safety boundary. Default-deny policy per `GeneralValidationPolicy {purposeId, validatorId/codehash, allowedVerifierOrCallerMode, messageSchema, enabled}`, owner-timelocked. Validator calls are STATICCALL, gas- and returndata-capped, fail closed on unknown versions/malformed returndata/revert. Always fails during emergency freeze, recovery, and every non-IDLE phase. **Value-moving verifiers (tokens, Permit2, settlement conduits) can never be satisfied here — value movement requires the commitment path, no exceptions.** Nonce/deadline bind the message but are *not* consumed at validation (EIP-1271 is view-only — never described as one-time without a separate state-changing step; replay is otherwise the consuming protocol's responsibility). Initial enablement, if any: an explicit **authentication purpose only**. If value-moving general signatures are ever enabled, they are first added to invariant 2 as an explicit seventh class. Adversarial tests — **both** must fail: (a) owner signed the raw EIP-3009 digest, attacker labels it AUTHENTICATION; (b) owner signed a well-formed GENERAL_AUTH wrapper whose inner `originalHash` is an EIP-3009 digest — the important case, blocked only by schema recomputation.

### 5.6 Tier-C templates & router — permanent limitations

**The template vocabulary freezes with the core.** Per template: id/version, selector + target source, argument types/order, core-forced fields, capability fields, native value/gas behavior, returndata handling, reservation interaction, reentrancy phase, required mechanical budgets, emergency reversal. `setApprovalForAll` is an **AUTHORITY** operation binding the exact operator/lego version, with core-accessible emergency revocation. A future call shape outside the vocabulary is unsupported by this core unless the operation is redesigned so a lego becomes the caller — a registry cannot teach frozen core a new template. PoC proves one independently-chosen fitting shape **and** one intentionally-unsupported shape that must reject — plus registration-time rejection (not just runtime revert) for protocols requiring privileged wallet callbacks, in-session EIP-1271, unsupported templates, or beyond-maxima cardinalities.

**Privileged wallet callbacks are permanently unsupported:** they must terminate at a lego (§5.3's machine); protocols requiring the wallet itself to perform a privileged callback are out of scope for this core, permanently. No disabled permit mechanism is reserved.

Router: fail-closed dispatch; action selectors → attached CURRENT extenders; answer-only handlers cannot move funds or open sessions; `executeAttached(attachmentKey, calldata)` — keyed to the exact attached version, any attached non-current version, core parses the selector and enforces the registration-pinned exit/refund/sync capability set. Unknown selectors revert; core selectors can't be shadowed.

### 5.7 Emergency freeze + recovery

- **Freeze:** owner, or a security signer attested by a *healthy* config, freezes immediately. **Unfreeze: owner only, timelocked.**
- While frozen: general 1271 always fails; commitment behavior per the commitment-bound rules (§5.5); MPP maintenance (sync/cancel/expire/cleanup) stays enabled; new sessions, transfers, authorizations blocked except the risk-reducing set.
- **Risk-reducing route — config-independent by construction:** owner-only access to registration-pinned risk-reducing selectors (debt repayment, collateral top-up, DRAIN exits, operator revocation, commitment maintenance) that works when config is broken. Mechanism: core stores `registrationId + bundleHash` at attachment (§4); the caller supplies proofs — exact attachment version/epoch, selector/actionId, risk-reducing classification, extender/lego target + codehash, schema + mechanism set, exit capability — which core verifies against the stored `bundleHash`. The route then runs the **same A/B/C mechanics, semantic consumption, budgets, reservations, lock, and postconditions as a normal session — only config policy authorization is bypassed.** The proof system is permanent core behavior, so `bundleHash` is a **proof-friendly root over canonical leaves** (attachment/version/epoch, selector/actionId, risk-reducing classification, mechanism set, extender/lego address + codehash, semantic schema, exit capability, beneficiary restrictions, dependency roots) with defined encoding, ordering, duplicate handling, and maximum proof depth — **the same leaves used by normal attachment/session authorization**, never a separate emergency metadata language. And because a security signer may have frozen the wallet precisely because the *owner* is compromised: every risk-reducing action must **mechanically force value to the wallet or a pinned protocol destination** — a selector is never risk-reducing merely because metadata labels it so.
- Both MIGRATE and RECOVER_FRESH increment `configEpoch`. Eject semantics, operator/NFT recovery under freeze, and the full risk-reducing actionId matrix are §16 deliverables.

**Explicitly NOT in core, permanently:** pricing, yield tracking, fee logic (beyond the bounded `onSettle` adjustment), points, WETH wrap, deleverage, lego interfaces, USD-denominated anything.

## 6. UserWalletConfig — state + gates, policy-free

Per-wallet **policy/configuration state** container (core keeps its own: ownership, attachments, commitments, epochs, lifecycle) and hook dispatcher. Policy-free but structurally strict — config permanently enforces: sender gates matched to module capability, nonzero/compatible addresses, packed-width bounds, enumeration consistency, timelock floors on security-root changes, no config/attachment mutation while the wallet reports busy, module↔config version compatibility.

1. **Hooks the core calls:** `validateAndConsumeTransfer(signer, recipient, asset, amount)` — nonpayable, decision + counter consumption atomic; `authorizeSession(signer, actionId, manifest)` + target resolution **in one config traversal**, returning resolved targets + hook bitmap; `onSettle(report) → bounded adjustment`. The core passes an authenticated authority class — config never calls back to re-read owner. Payloads always carry `(asset, amount)` so pricing slots in module-side later with no core or hook-ABI change.
2. **Limits are amount-denominated for now — by decision.** Per-asset caps, per-period counters, allowlists. USD limits return as a Sentinel upgrade. Amount caps are not equivalent security for volatile/differently-scaled assets — revisit before production.
3. **Config is the ONLY home for per-wallet policy state:** managers (allowlist + per-manager caps/assets/actions), whitelist + payees (timelocked adds, instant removes), **all** pending/timelocked proposals (params, global settings, module + attachment changes — v2's pendings in Paymaster/ChequeBook end here), module pointers, packed storage, `version()` tag. Ownership lives in core.
4. **Writes are sender-gated to backpack modules;** config never validates lifecycle policy itself. Module-pointer succession (including ParamsModule replacing itself) is authorized by the core ownership root, timelocked.
5. **Replacement/recovery — core-enforced, two modes:**
   - **MIGRATE:** initiate → timelock → freeze source writes → chunked copy → activation commits to `{sourceConfig, sourceStateEpoch, destinationConfig, destinationCodehash/schemaHash, completeness root, expected counts}` and rejects if source state changed → re-point + `configEpoch++`.
   - **RECOVER_FRESH:** for a config that cannot participate in freezing/export — longer timelock, runs under the core emergency freeze (a compromised config must not be able to drain during the delay), installs a conservative empty config, deliberately abandons inaccessible policy state, preserves core funds/commitments/attachments/owner/epochs, `configEpoch++`.
   - Security-signer powers flow through config and exist only while config is healthy; the core owner is the sole unconditional authority.

Action ids are plain `uint256`; unknown ids revert; new action classes ship as module upgrades — owner opt-in, never a core change.

## 7. Backpack modules

The v2 pattern kept — state in config behind sender gates, logic in shared owner-swappable singletons — without the six-contract split. Production: registered in a **ModuleBook** separate from ExtenderBook (different trust directions: modules interpret canonical config state; extenders orchestrate funds/positions). PoC: no ModuleBook — config points directly at modules.

- **Strictly stateless.** Zero per-wallet state in modules — a deliberate break from v2 (Paymaster/ChequeBook pendings move to config).
- **Write path:** owner/manager → module (validates request, enforces timelocks/bounds) → config's sender-gated setter. **Read path:** config hooks delegate decisions to Sentinel.
- **PoC shape:** **ParamsModule** (whitelist/manager/payee/attachment-proposal lifecycle) + **Sentinel** (signer perms, transfer gates, amount caps, session authorization — where pricing/USD limits later land). Split further only if size demands.
- **Later phases:** cheque-like commitments, richer payee policy, fee/points policy, accounting adapters (§13). The v2 Migrator's successor is the config-replacement copier.

## 8. Extenders

Shared, immutable, **no-custody** singletons in the **ExtenderBook**, attached per-wallet by the owner as **bundles**. Typed Vyper throughout.

- **Registration metadata:** pinned codehash (no proxies behind attachments), id + version, required core version, state-schema version, capability declaration (action tuples with mechanism sets, lego types, whether value may leave), exit/refund/sync capability set for `executeAttached`, bound lego versions/codehashes + dependency classifications, rail adapters, hook flags, and the signed tier checklist artifact — all folded into `bundleHash`. Metadata for an attached version is immutable except permission-narrowing lifecycle changes.
- **Two-level lifecycle — effective permission is the most restrictive of:** registry `ACTIVE / DRAIN_ONLY / CLOSED` (governance) × wallet-local `CURRENT / DRAIN_ONLY / DETACHED` (owner). Attaching v2 of an extender auto-DRAINs v1 locally (still reachable via `executeAttached`); detach = **HARD_REVOKE** (instant, epoch bump, voids that wallet's pending commitments; cleanup via `cleanupInvalidBinder` with pull-evidence checks). Routine deprecation uses DRAIN_ONLY, not detach. **CLOSED is an operational/governance status, never an on-chain proof** — commitments are distributed per-wallet; DRAIN_ONLY may last indefinitely; per-wallet closure is provable locally; external-position closure is never inferred from payment commitments.
- **State rule:** core commitment state is canonical for value/liability; extender storage is **supplemental and reconcilable** (permissionless reconciliation path); core finalization never depends on extender callbacks. Opt-in `needsAfterSessionHook` for synchronous local settlement state — capped, best-effort.
- **State classification:** external canonical (Ripe positions, vault shares — keyed to the permanent wallet address, survive by construction) · reconstructible cache · supplemental payment metadata.
- **Planned set:** YieldExtender, SwapExtender, DebtExtender (Ripe positions never migrate — the address is permanent), LiquidityExtender, RewardsExtender, WethExtender (Tier-C), PayExtender-x402, PayExtender-MPP.
- **Lego-side (rebuilt to fit v3):** pull from explicit `_user`; enforce the §5.3 adapter contract (caller guards, consumption-before-effects, EXPECTING_CALLBACK, forced beneficiaries).

## 9. Transaction flows (abbreviated)

**Yield deposit (agent):**
```
agent → wallet [YieldExtender.depositForYield ABI]
  DISPATCHING: authenticate → transient signer · route-derived actionId · CALL extender
  extender → wallet.openSession(manifest + canonical payloads)   # core computes semanticHashes,
                                                                 # config/Sentinel authorize; snapshot; → ACTIVE
  extender → wallet.grantApproval(asset, amt, legoRef)           # exact, manifest-budgeted
  extender → Lego.depositForYield(asset, amt, vault, wallet)     # typed extcall
      lego → wallet.consumeCapability(capId, semanticHash, wallet, budgets)   # semantic consumption
  extender returns → SETTLING: approvals zeroed · postconditions · policy · adjustment → CALLBACK → IDLE
```

**x402 payment:**
```
agent → wallet [PayExtender402.pay ABI]
  session opens (config gates USDC, amt, dest) · rail validator proves digest ↔ approved terms
  extender → wallet.authorizeCommitment(EXTERNAL_EXACT, digest, USDC, amt, dest, adapterRoot, window,
                                        policyTerms)             # reserves; PolicyTerms preimage emitted
  ... later: facilitator → USDC.transferWithAuthorization(from=wallet, to=dest, ...)
             USDC → wallet.isValidSignature(digest) → MAGIC (wallet IDLE) → funds move wallet→merchant
             anyone → wallet.syncExternalPull(id, policyTermsPreimage)   # adapter verifies evidence;
                                                                 # finalize; non-bubbling notification
```

**Simple transfer (owner):** DIRECT_EXECUTING — no router, no session. Ownership-root/manager fast path, config validate-and-consume, transfer, event. Highest-volume path, cheapest by construction.

## 10. PoC scope

| In the PoC | Deferred (module-side / later phase — never a core change) |
|---|---|
| Core: ownership root + emergency freeze + risk-reducing route (bundle-proof mechanism), custody, transfers + batch, execution lock + phase machine, capabilities (core-computed hashes, typed beneficiary, semantic-only), commitments (both modes, full API, authority matrix, PolicyTerms reconstruction, notification retry, rail adapters), EIP-1271 (rail + purpose-domain general envelope, disabled; fork test), router + executeAttached, config-pointer recovery authority | Pricing / USD limits (Sentinel upgrade) |
| Thin config (state + structural gates) + ParamsModule + Sentinel (direct pointers, no ModuleBook) | Yield tracking & fee capture (permanently out of the wallet; onSettle bounds fully exercised in PoC) |
| Extenders per §11 vs mock legos + forked Base USDC | Deposit points / loot (module-side) |
| Minimal ExtenderBook (deployer-owned; load-bearing metadata schema only) | Cheque-like commitments, richer payee policy, accounting adapters |
| Reused v2 registry code for lego resolution (no LegoBook rebuild) | Config replacement copier; ModuleBook; production registry hardening |
| Greenfield tests + gas benchmark with component gates from day one; adversarial suite | Cutover tooling; Ripe `transferPosition`; agent-stack integration |

## 11. PoC build order

1. **Minimal direct transfer** + config/Sentinel — hot-path budget first.
2. **YieldExtender + mock lego** — A+B: phase machine, manifest, core-computed hashes, budgets, postconditions, epilogue; empirical direct-vs-mediated cost comparison.
3. **Mock debt lego (borrow / removeCollateral)** — B-only, no-allowance liability actions: semantic enforcement where approvals protect nothing.
4. **Tier-C templates** — C+B: WETH/native template, operator grant + emergency revoke, NFT/AUTHORITY template if retained; the fitting + intentionally-rejected mock-future-protocol pair; registration-time incompatibility rejections.
5. **PayExtender-x402 on forked Base USDC** — EXTERNAL_EXACT, sync + PolicyTerms preimage reconstruction (with config/extender reads disabled), 1271 caller-binding decision, non-bubbling notification + permissionless terminal retry.
6. **Mock MPP flow** — partial settle/refund with cumulative-settled tracking, authority matrix, transition-nonce idempotency, onSettle bounds/failure, reserved-fee failure semantics.
7. **Adversarial suite:** extender — signer spoofing, manifest inflation vs calldata, payload-vs-hash mismatch (must be impossible by construction), semantic violations (removeCollateral MAX vs approved 1), repeated grants, wrong lego/verb, nested sessions, phase-transition reentrancy everywhere, return-without-settle, DISPATCHING abuse, mid-session direct-lego calls, mid-session external-pull attempts (IDLE-only 1271); general-1271 — owner-signed raw EIP-3009 relabeled AUTHENTICATION must fail; terminal-digest fall-through must fail; lego-within-scope — self-report consistency, beneficiary violations, unguarded entries, EXPECTING_CALLBACK cross-wallet/session substitution + late callbacks; commitments — cancel-vs-pull races, pre-revoke-pull cleanup, digest/nonce reuse, epoch resurrection, reverting-policy stranding, notification replay/stale nonces; freeze matrix — every risk-reducing path works via bundle proofs with config disabled; hooks — success/revert/exhaustion.
8. **Future-compat exercise:** add a new extender/lego/schema with a new `semanticKind` under an existing mechanical class + a new Sentinel schema validator + a semantic-only capability — **zero core changes**. Then provisional freeze; audit-oriented build.

## 12. Gas strategy

v3 removes the v2 hot-path machinery (~209k bundle assembly, double pricing, sync points) and adds measured costs: config pointer, `reserved` reads, config→Sentinel chain, lock/phase transitions, consumeCapability, commitment storage.

**Hot-path gates:** owner→whitelist repeat < **~190k** must-have, **125–150k** stretch (amount-cap profile; minimal-PoC vs future-policy profiles reported separately — an amount-only PoC is *not* feature-equivalent to v2 pricing/points behavior).

**Component gates (pre-freeze; exact numbers set during PoC, ceilings then enforced in CI):** router + empty session < ~60k (contents defined: authenticate, route, openSession round-trip, empty snapshot, epilogue); realistic minimal session (one input, one output, one lego, one approval/reset, one consumeCapability, snapshots, zero adjustment) — **acceptance ceiling, not just a report**; consumeCapability warm base + per-budget-leaf marginal targets (< ~5k base), first vs repeat benchmarked; one-item vs maximum-cardinality manifests (maxima fixed pre-freeze); commitment core struct ≤4–5 words target / 6 hard (adapter-root-as-compact-id decision resolves which) + total first-touch slot ceiling across core/config/extender incl. pending counter; PolicyTerms max byte length + its calldata/L1 cost; fixed gas/returndata caps for handlers, hooks, notifications, general validators; 1271 benchmarks (rail hit, disabled-general miss, enabled-general validation, adversarial calldata); attachment storage ceilings (slots per attachment/selector/bundle-id); DRAIN routing; second sequential session; every rail lifecycle (consider batch sync/finalize); duplicate validation O(n); **deployment ceilings: core ≤16KB hard, config runtime + combined core+config ceilings set pre-freeze**; optimizer-mode comparison; **a defined v2-vs-v3 sponsored-UserOperation improvement requirement measured under identical EntryPoint/account/paymaster/bundler/Base conditions with production USDC**.

**PoC measurement honesty:** runtime reads must be production-shaped — the meaningful measurements are transfer, config→Sentinel validation, router/session framework, capability consumption, bundle/lifecycle lookup, lego resolution, commitment lifecycles, EIP-1271, and callback machinery. Deployment, installation, attachment-proposal, registration, and timelock-flow gas are **PoC-only numbers, reported as such**.

Design rules: ownership-root fast path (single packed slot before any struct); one config traversal for authorize+resolve; hook bitmap skips no-op onSettle; manifest bounded + deduplicated before snapshots; immutable tx context cached once — mutable state revalidated per sequential session; packed hot structs everywhere; whitelist early-outs preserved; no minimal proxies; CI regression gates from day one.

## 13. Accounting (off the hot path, by design)

The hot path never regains synchronous pricing/points. "What does this user own" — wallet balances, reservations/commitments, Ripe collateral/debt, locked RIPE, vault shares, LP/NFT positions, pending payment ops, DRAIN_ONLY extender state — is served by **read-only accounting adapters** identified in ExtenderBook metadata, composed by indexers. **No core asset registry** (resolved): it would miss unsolicited transfers and external positions, cost first-touch SSTOREs, and a permanent wallet doesn't need it for migration. Events + indexing are canonical for enumeration.

## 14. Requirements inventory (v2 behavior → v3 disposition)

| v2 behavior | v3 disposition |
|---|---|
| Owner / managers / security roles | **redesigned** — ownership root + ownerEpoch in core; managers in config/Sentinel; security signers config-dependent; owner unconditional |
| Whitelist / payees + limits | **redesigned** — amount-denominated first; USD via Sentinel upgrade |
| Cheques | **redesigned, deferred** — reborn as commitments/policy module |
| Freeze / eject | **redesigned** — core emergency freeze + risk-reducing route + matrix (pre-freeze) |
| Trial-fund clawback | **redesigned, deferred** — cutover-phase decision |
| Billing pulls | **redesigned, deferred** — commitment/policy flow |
| Agent wrappers / session keys | **preserved** — target the wallet address with extender ABIs; consolidation deferred until payment extenders exist |
| NFT recovery | **preserved** — core primitive, owner-gated, lock-respecting |
| Ripe operator grants | **preserved** — Tier-C AUTHORITY template, full grant/revoke/emergency-revoke lifecycle |
| Yield tracking / price-per-share | **intentionally removed** from the wallet |
| Swap/yield/rewards fees | **deferred** — onSettle adjustment fully specified + exercised pre-freeze; policy module later |
| Deposit points / loot | **deferred** — module-side if ever |
| Wallet-to-wallet migration | **intentionally removed** — permanence + config replacement/recovery |
| Asset registry / USD accounting | **removed from core** — accounting adapters + indexing (§13) |

## 15. Security invariants

1. Every fund- or position-affecting action executes in a wallet-owned frame with the real caller authenticated. (Module→config configuration writes are the intentional exception and move no value.)
2. **Wallet-authorized outflow authority or new principal liability is initiated only via:** (1) config-authorized direct transfer; (2) capability-bound session execution (cumulative mechanisms per registered tuple); (3) rail-bound deferred pull against an ACTIVE commitment; (4) atomic reserved settlement/refund; (5) persistent operator grants (Tier-C AUTHORITY templates, emergency-revocable); (6) enumerated emergency/cutover primitives (defined pre-freeze). **General-signature validation can never authorize value movement** — if that ever changes it is added here as an explicit seventh class first. Asynchronous protocol effects (interest, liquidations, rebases) are handled by accounting, not prevented.
3. Every new top-level frame requires IDLE and takes its phase before any external call; internal effects only in designated phases; `isValidSignature` answers only in IDLE; all lock/session/capability state is transient (EIP-1153).
4. Committed value is reserved; `available` saturates; limits consumed at authorization, never twice; EXTERNAL_EXACT never partially releases under a valid digest; refunds don't restore limits; terminal states unambiguous; notifications idempotent per transition nonce with permissionless terminal retry.
5. Approvals exact, manifest-budgeted, session-scoped, zeroed before any settlement hook.
6. Parameter-sensitive effects require semantic consumption with core-computed payload↔hash binding, typed beneficiary, and per-mechanical-class budgets; unknown classes/kinds/schemas/envelope versions revert.
7. Trust boundaries per §5.3; legos audited at core seriousness; lego callbacks only through fully-namespaced EXPECTING_CALLBACK contexts; dependency pinning per §5.4 with the third-party-risk qualification.
8. Fail closed everywhere.
9. Detach = HARD_REVOKE with evidence-checked cleanup; DRAIN_ONLY preserves exits via exact-version `executeAttached`; CLOSED is operational, never an on-chain proof.
10. No delegatecall; no arbitrary-target or unbounded wallet-originated calldata; Tier-C vocabulary, the two commitment modes, and the privileged-callback exclusion are permanent, stated limitations.
11. Governance can never force or widen code on an existing wallet (append-only registries, narrow-only attached metadata, bundle re-attach for any widening); third-party proxy risk is disclosed and owner-accepted at attachment.
12. Ownership root outranks config; freeze/unfreeze per §5.7 with the config-independent risk-reducing route; recovery exists for every config failure mode; commitment maintenance and PolicyTerms enforcement survive config/extender/policy failure.

## 16. Pre-freeze vs post-freeze

**Pre-freeze (the PoC must prove):** closure of the emergency/cutover category — either expressed entirely through already-enumerated transfer/Tier-C/commitment/recovery primitives, or every additional core method named with exact bounds (invariant 2 is not exhaustive while a category is open-ended); the canonical bundle-proof leaf schema shared by normal and frozen routes; phase machine incl. ANSWER_CALLBACK + ACTIVE receiver exceptions + transient mandate; capability/budget encodings — core-computed semanticHash domain + golden vectors, typed beneficiary chain, semantic-only capabilities, O(n) validation, manifest maxima; complete session/bundle commitment lists; lego adapter contract incl. fully-bound EXPECTING_CALLBACK contexts + nesting rules; dependency classifications + bundle attachment; commitment bit layout (≤6 words) + PolicyTerms public reconstruction + max size + reserved-fee failure semantics + cumulative-settled tracking + transition-nonce idempotency + permissionless terminal retry + adapter-root liveness fallback + boundary semantics + commitment-bound freeze behavior; purpose-domain general-1271 envelope (disabled but validated, relabel attack rejected); rail authority matrix; Tier-C frozen template table (incl. AUTHORITY/`setApprovalForAll`) + fitting/rejecting mocks + registration-time incompatibility rejection; permanent two-mode + privileged-callback limitations; freeze/recovery matrix incl. bundle-proof risk-reducing route; both recovery modes; new-semanticKind/no-core-change future-compat exercise; exact numeric gas/storage/bytecode gates (§12); lean two-step sign-off with the checklist artifact committed into bundleHash (max loss/liability, required caller, mechanical classes + semantic kinds, beneficiaries/resources, persistent authority, dependencies + admins, callback behavior, freeze/DRAIN behavior, adversarial tests, residual trust — the reviewer approves the artifact, not a tier label).

**Post-freeze:** config-replacement copier; ModuleBook + production registry hardening (real timelocks, append-only + narrow-only enforcement); payee/cheque policy modules; pricing/USD Sentinel; fee/points policy; accounting adapters; agent-stack integration; cutover tooling; ERC-1155 receiver (routed through the ACTIVE-receiver authorization model); benchmark expansion.

## 17. Decisions & remaining open questions

**Resolved:**
- General-1271 reserved path **IN**, mechanically purpose-scoped per §5.5a; initial enablement (if any) = authentication only.
- Tier sign-off: **lean two-step** — builder proposes schema + mechanisms + adversarial tests; one independent technical reviewer approves the checklist artifact; timelocked registration + owner attach do the rest. No committees.
- PoC registries: **ExtenderBook only** (minimal, schema load-bearing); no ModuleBook; reuse v2 LegoBook code. Production keeps separate ModuleBook/ExtenderBook.
- PoC timelocks: **runtime-zero delays with permanent pending-state shapes retained** (pending owner / config destination / unfreeze — the fields must exist before storage freeze); epochs + instant detach kept. Production attach timelock: **configurable registry/config minimum — never hardcoded into immutable core.**
- Failed external-pull fees: **accounting-only** (§5.5). Nested lego callbacks: **prohibited** (§5.3). ExtenderBook records: **write-once/content-addressed with `familyId`** (§1). Registries: **untrusted resolvers** — core verifies against bundle bindings + codehash (§5.4).

**Open (small confirms):**
1. **Manager model for PoC:** flat allowlist + per-asset caps + action classes + period counters — confirm.
2. **Contracts location** `contracts/walletsV3/` — confirm.
