# PR #76 audit — Add x402 + MPP agent payments settlement engine

Working audit doc (task branch `task/payprocessor-audit-wqcsp6`). Owner: Moto (coordination + consolidation).
Peers: Luna (MPP accounting), Toro (x402/EIP-3009/1271), Gina (AgentSenderPay/sig), Leto (Vendor* + tests).

## System model

Agent-payments settlement engine on Base, two rails behind one `PayProcessor.register()`:

- **x402** — processor binds a USDC EIP-3009 authorization and is the EIP-1271 payer
  (`isValidSignature → MAGIC`); merchant's facilitator pulls `transferWithAuthorization(from=processor, to=dest)`.
- **MPP** — processor escrows → `settle()` → `availToBridge` → `bridge()` batches USDC to a
  Switchboard-set bridge address (off-ramps to Tempo). `refund()` returns unsettled escrow.
- `AgentSenderPay` (owner-signed) sources the user's USDC and calls `register`.
- `VendorRegistry`/`VendorProxy` — per-service payee proxies + destination allow-list.
- `SwitchboardDelta` (**added in latest PR rev d7895a5**) — the config+ops gateway registered as the
  payments departments' `isSwitchboardAddr`; every switchboard-gated call flows through it. Two tiers:
  *operational* (security-signer/gov, immediate: createVendor/removeVendor, add/removeDestination,
  settle/bridge/refund, pause) and *config* (gov-only + timelock: setSender/setBridge/setVendorTemplate,
  unpause).

**Systemic property:** the processor is ONE commingled USDC balance across both rails + refunds,
no per-op segregation. Correctness hinges on `balance ≥ Σ(outstanding x402) + pendingTotal + availToBridge`
holding across every path. Everything is Switchboard-gated (single trust root).

---

## Executive summary (consolidated — Moto)

Five-lane review (Moto/Luna/Toro/Gina/Leto) across two PR revs (base + `SwitchboardDelta`). **Two HIGH
findings, both fixed and regression-tested;** one MED and one LOW also fixed; the remainder are LOW/INFO.
No unfixed issue blocks; the two deploy-time guards (T1, T2) are the main items worth doing before
mainnet. **No permissionless fund-theft path was found** — the residual risk is counterparty/
centralization (the Switchboard is the single trust root; MPP escrow has no on-chain guarantee).

Full payments suite: **58 passing** (`--fork local`) on latest PR rev **d7895a5** (31 original + 8 Leto
+ 7 Toro + 3 F1 + 5 F2/F3 + 4 SwitchboardDelta). `SwitchboardDelta` (the trust root) reviewed — see below;
notably its immediate/security-signer tier is confined to **non-redirecting** ops, so a compromised server
key can grief/DoS but **cannot redirect funds** (fund-redirecting config is gov-only + timelocked).

| Sev | ID | Title | Status |
|-----|----|-------|--------|
| HIGH | F1 | Cross-rail refund/settle contamination (mutable-rail inference) | **FIXED + tested** (Moto) |
| HIGH | F2 | Unsigned `_vault` — broadcaster can force a yield withdrawal | **FIXED + tested** (Moto; Gina find) |
| MED  | F3 | No `incrementNonce()` to revoke leaked/stale signatures | **FIXED + tested** (Moto; Gina find) |
| LOW  | F4 | Registered amount was `moved`, not signed `_amount` | **FIXED + tested** (Moto; Gina find) |
| LOW  | F5 | Silent `pendingTotal = 0` clamps masked accounting drift | **FIXED** (Luna) |
| LOW  | F6 | CEI: `register()` external call before `exists` write | Documented — defer to next-rail (Luna) |
| LOW  | T1 | Hardcoded USDC domain assumes native USDC (silent x402 no-settle if wrong token) | **Open** — recommend constructor guard |
| LOW  | T2 | `validAfter`/`validBefore` unvalidated → stuck-but-refundable ops | **Open** — recommend `assert validAfter < validBefore` |
| LOW  | Leto-A | `pullPayment`/Billing path is unused today (future pull-rail) | **RESOLVED** — kept for future-proofing + documented as forward-decl (per @you) |
| INFO | F7 | Shared-pool invariant not queryable on-chain | Recommend `checkInvariant()` view |
| INFO | T3 | Permissionless `isValidSignature`/refund race | By design; **bounded** — only the payload-holder (merchant) can trigger the pull |
| INFO | Leto-B | MPP dest-gate is required-but-unused (off-ramp is `bridgeAddress`) | Note intent |
| INFO | Leto-C | PR body says "17-case suite"; actual is 58 | Update PR body |
| LOW  | SD-1 | A single compromised security signer can immediately DoS payments (pause + removeVendor + removeDestination); recovery is gov-only, unpause timelocked | Disclose — inherent to the ops tier |
| LOW  | SD-2 | MPP escrow can be `settle`d (→ non-refundable) + `bridge`d by a security signer immediately (no timelock); refunds discretionary and foreclosable | Sharpens counterparty risk |
| LOW  | SD-3 | `SwitchboardDelta` must be registered as `isSwitchboardAddr` + MissionControl (dept 2) set, else calls revert / only-gov | Deploy-time invariant |
| INFO | SD-4 | x402 dest allow-list is edited in the immediate (non-timelocked) tier | Acceptable — necessary-but-not-sufficient to move funds |

**Verified-correct (no action):** x402 digest/domain parity vs **live Base USDC** — byte-for-byte match
(Toro, closes the circular-mock coverage gap); Vendor*/registry swap-remove list logic across all edge
cases (Leto); CEI/reentrancy on `refund()` (Toro).

**Recommended fix queue (all LOW/INFO, none applied yet — need a decision):**
1. **T1** — constructor `assert UsdcDomain(_usdc).DOMAIN_SEPARATOR() == self._domainSeparator()` (needs a
   `DOMAIN_SEPARATOR()` on `MockUsdc`). Turns "deploy against the right USDC" into an on-chain invariant.
2. **T2** — `assert validAfter < validBefore` in the x402 branch of `register()`.
3. **Leto-A** — ✅ decided (per @you): **kept** for future-proofing; documented as an intentional,
   not-yet-wired forward-decl (needs real-Billing integration tests before it's used).
4. **F6 / F7** — CEI pre-write in `register()` and the `checkInvariant()` view (defense-in-depth).

## Findings

### [HIGH] F1 — Cross-rail refund/settle contamination — FIXED + VERIFIED

`PayProcessor` infers the rail from the **mutable** `opDigest[paymentId] != 0`. A **partial** x402
`refund()` unbinds the digest and sets `opDigest → empty` (PayProcessor.vy:288-289) while refunding
only part. The op is then indistinguishable from MPP:

- `settle()` (`assert opDigest == empty`, PayProcessor.vy:249) now **accepts the x402 op** and moves
  its remainder into `availToBridge`; `bridge()` off-ramps it. The payer's refundable remainder is
  **permanently lost** (later `refund` reverts "already settled"). Breaks the "x402 settles only via
  the facilitator" and "availToBridge = settled-MPP-only" invariants.
- `refund()`'s MPP `else` branch (PayProcessor.vy:290-296) runs for the x402 op and corrupts the
  unrelated `pendingTotal` MPP escrow counter.

Also violates the documented "revoke-or-refund (never both)" invariant.

**Fix applied (Moto), `PayProcessor.vy`:**
- Added an immutable `protocolId: uint8` to `Operation`, set at register to the raw `_protocolId` — the
  discriminant stores the **rail**, not a boolean, so it's future-proof for additional rails (per @you).
- `settle()` now gates on `assert op.protocolId == RAIL_MPP` (explicit MPP-only) instead of the mutable
  `opDigest == empty`.
- `refund()` branches on `op.protocolId == RAIL_X402` (not `opDigest`), and the x402 branch enforces an
  all-or-nothing refund (`assert _amount == op.amount - op.refunded`) so no half-bound op can ever exist.

**Verification:** `tests/core/payments/test_poc_crossrail.py` — 3 regression tests (partial x402 refund
blocked; x402 op never settleable even post-refund; x402 refund leaves MPP `pendingTotal` untouched).
Full suite **34 passed** (`--fork local`); the 31 pre-existing tests are unaffected (new struct field
appended, so positional indices [0]-[7] are preserved).

**Severity note:** Switchboard-gated (not a permissionless drain), but reachable by a *non-malicious*
operator sequence (partial-refund a disputed x402 charge, then a routine MPP settle sweep picks up the
now-MPP-looking op). The contract should enforce its invariants regardless of operator discipline.

**Residual for Luna's sweep:** with F1 fixed, the `else: pendingTotal = 0` clamps in `settle()` (:257)
and `refund()` (:298-300) are now provably unreachable on any legit path — consider hardening them to
`assert pendingTotal >= amount` so a future accounting drift reverts instead of being silently absorbed.

### [HIGH] F2 — `AgentSenderPay` lets broadcasters change the vault withdrawal that was not signed

`AgentSenderPay.pay()` authenticates a hash of the payment fields, but omits `_vault` from both the
runtime hash and `getPayHash()` (AgentSenderPay.vy:108-111, 203-208). `_vault` is then used as a live
behavioral input in `_sourceAndSend()` to call `withdrawFromYield()` before the payment transfer
(AgentSenderPay.vy:126-136).

Impact: any broadcaster holding a valid payment signature can submit the same signed payment with an
arbitrary non-empty `VaultSource`. If this sender has the expected yield-withdraw permissions, the
broadcaster can unwind the user's USDC yield position (including `max_value(uint256)`), then consume the
payment nonce with the fixed payment. The extra funds remain in the wallet, but the broadcaster still
gets an unsigned asset-management action: forced liquidation of yield exposure, potential exit costs,
reward loss, and operational surprise.

**FIXED + VERIFIED (Moto; Gina's finding), `AgentSenderPay.vy`:**
- `_vault` is now encoded into the signed hash in both `pay()` and `getPayHash()` (added as a trailing
  defaulted param on `getPayHash`, so existing NO_VAULT call sites are unchanged).
- `_sourceAndSend()` rejects a partial `VaultSource` (`assert (legoId != 0) == (vaultToken != empty)`)
  so a malformed config can neither silently skip a signed withdrawal nor slip an unsigned one through.
- Regression tests (`tests/core/payments/test_sender_sig_regression.py`): injecting a vault onto a
  NO_VAULT signature → `invalid signer`; a signed vault is accepted; a partial vault → `partial vault config`.

### [MED] F3 — `AgentSenderPay` cannot revoke leaked or stale payment signatures

The new sender has `currentNonce` replay protection and consumes the nonce only when a non-owner signed
payment succeeds (AgentSenderPay.vy:156-164), but it does not expose the owner-only `incrementNonce()`
escape hatch that the existing senders provide (e.g. AgentSenderGeneric.vy:839-849 and
AgentSenderSpecial.vy:576-586).

Impact: once a payment signature is handed to a broadcaster, the owner cannot cancel it on-chain except
by waiting for expiration or racing to consume the nonce with another payment. The tests sign with
`FAR_FUTURE`, which demonstrates the risk if production signatures are long-lived or leaked.

**FIXED + VERIFIED (Moto; Gina's finding), `AgentSenderPay.vy`:** added owner-only
`incrementNonce(_userWallet)` (mirrors AgentSenderGeneric/Special; uses the existing 2-field
`NonceIncremented` event). Regression tests: an owner nonce-bump kills a pre-signed nonce-0 payment
(`invalid nonce`), and a non-owner call reverts (`no perms`).

### [LOW] F4 — Registered payment amount should be the signed amount, not `moved`

`_amount` is signed, but `pay()` registers `moved` and emits `moved` (AgentSenderPay.vy:108-115), while
`_sourceAndSend()` only checks `moved >= _amount` (AgentSenderPay.vy:138-147). With the canonical
`AgentWrapper`, this is not currently an overcharge: `UserWallet.transferFunds()` caps the transfer at
`min(_amount, balance)` and cheque payment requires the exact cheque amount, so the assertion forces
`moved == _amount` in practice.

The contract should still encode that invariant directly. If a future/misconfigured wrapper ever returns
or transfers more than requested, the processor will record and settle an amount the owner did not sign.

**FIXED (Moto; Gina's finding), `AgentSenderPay.vy`:** `_sourceAndSend()` now asserts `moved == _amount`,
so the amount recorded/settled by the processor provably equals the amount the owner signed (a wrapper
that ever returned more now reverts instead of over-charging). Covered by the end-to-end payment tests
(canonical mock returns exactly `_amount`).

## Cross-cutting risk (underwriter view — Moto)

- **Counterparty risk (MPP):** once MPP funds are escrowed they sit in the processor and are moved by
  the Switchboard to a Switchboard-set off-ramp address. Users have **no on-chain guarantee** — refunds
  and settlement are fully discretionary. This is trust/counterparty risk, not smart-contract-enforced.
- **x402 refunds race settlement — but the trigger set is bounded (corrected per Toro's T3):** I
  originally said "anyone" can force settlement. Not so: `validAfter`/`validBefore` are **not** emitted
  on-chain (only amount/dest/digest/nonce are), so only a party holding the full x402 payload — the
  merchant/facilitator — can actually form the `transferWithAuthorization` pull. Settlement is still
  permissionless *given the payload*, so a pending refund is inherently a race the merchant can win;
  guaranteed refunds, if a product requirement, must be enforced off-chain (settlement hold).
- **Deploy-time correctness:** the hardcoded USDC EIP-712 domain was **verified correct** against live
  Base native USDC (Toro — byte-for-byte). Residual is purely a deploy-config risk (wrong token address)
  → see T1 (recommend a constructor guard).

---

## Luna's sweep — MPP accounting & shared-pool invariant

### [LOW] F5 — Silent `pendingTotal = 0` clamping masked accounting corruption — FIXED

**Location (before fix):** `settle():255-258` and `refund() MPP branch:297-300`.

Both paths used `if pendingTotal >= amount: ... else: pendingTotal = 0`. With the rail now
immutable (`protocolId`), the `else` branch is provably dead on all correct paths. Keeping it meant a
future bug (a new refund path that forgets to decrement, an out-of-order call) would silently
continue with a broken counter instead of reverting and alerting operators.

**Fix applied:** replaced both `if/else` patterns with plain subtraction. Vyper's default safe
arithmetic reverts on underflow — no explicit assert needed:
```vyper
self.pendingTotal -= amount    # settle() — was: if >= amount: ... else: = 0
self.pendingTotal -= _amount   # refund() MPP branch — same pattern
```

**Verification:** 49/49 tests pass; no underflow is triggered by any test path.

---

### [LOW] F6 — CEI pattern violated in `register()`: external call before state write (no fix needed now)

**Location:** `PayProcessor.vy:168-172`.

`assert not self.operations[_paymentId].exists` is checked before line 168, but
`self.operations[_paymentId]` (which sets `exists = True`) is written at line 172 — **after** the
external call to `VendorProxy.transferToProcessor` (line 168). If that external call reentered
`register()` with the same `_paymentId`, the exists guard would pass again.

**Exploitability:** none currently. `VendorProxy.transferToProcessor` is a Switchboard-deployed
blueprint that only does a USDC `transfer` — no hooks, no callbacks. USDC itself has no transfer
hooks. Cannot be reached by a non-Switchboard actor.

**Recommendation before next rail:** move `self.operations[_paymentId] = Operation(..., exists=True, ...)`
to before the `extcall` line. If the call reverts the whole transaction reverts, so the pre-write is safe.

---

### [INFO] F7 — Shared-pool invariant not queryable on-chain

The contract's balance should always satisfy `balanceOf(self) >= pendingTotal + availToBridge`.
There is no on-chain view to expose or assert this. Off-chain monitoring cannot distinguish a
healthy pool from a silently drifted one without computing it externally.

**Recommendation:** add a view:
```vyper
@view
@external
def checkInvariant() -> bool:
    return staticcall IERC20(USDC).balanceOf(self) >= self.pendingTotal + self.availToBridge
```
Switchboard health checks should call this after every settle/bridge/refund batch.

---

## Luna's summary

| ID | Title | Sev | Status |
|----|-------|-----|--------|
| F1 | Cross-rail rail contamination | HIGH | Fixed (Moto), regression-tested |
| F5 | Silent `pendingTotal = 0` clamping | LOW | Fixed by Luna (plain subtraction, 49 tests pass) |
| F6 | CEI violation in `register()` | LOW | Documented — no fix needed until new rails added |
| F7 | Shared-pool invariant not queryable | INFO | Documented |

---

## Leto's lane — VendorRegistry / VendorProxy + test coverage

### [LOW] Leto-A — `VendorProxy.pullPayment` + Billing wiring is unreachable dead code
`pullPayment` (VendorProxy.vy:114-124) is gated `msg.sender == _processor()`, but the PayProcessor never
calls it (nothing anywhere calls `.pullPayment(`). Unreachable in this PR, yet it drags in the `Billing`
interface, `BILLING_ID`, `MockBilling.vy`, and 2 tests that only exercise the mock's echo (false
coverage). It's an unused external **fund-moving** entrypoint; if ever wired it flips the trust model
(pull-from-wallet, a stronger grant than the PR's push model).

**Resolution (per @you): KEPT for future-proofing.** `pullPayment` (+ `Billing` iface, `BILLING_ID`,
`MockBilling.vy`) is retained and now carries an explicit `INTENTIONAL FORWARD-DECLARATION` comment in
`VendorProxy.vy` documenting that (a) no PayProcessor flow calls it today, (b) the live rails PUSH not
pull, and (c) it has **no integration coverage against real Billing authorization yet — must be tested
before it is wired.** This preserves the future pull-rail while making its unfinished/unguarded status
unmistakable to the next reader.

### [INFO] Leto-B — MPP dest-gate is required-but-unused
`register()` gates both rails on `VendorProxy(_vendor).isAllowed(_dest)` (PayProcessor.vy:166), but the
MPP branch never uses `_dest` (MPP off-ramps to the switchboard-set `bridgeAddress`). Every MPP payment
must still carry *some* allow-listed dest with zero effect on fund flow. Intended (per
`test_register_mpp_gates_dest`), but worth a one-line comment; an MPP-only vendor still needs ≥1 dest.

### [INFO] Leto-C — PR body test count stale ("17-case suite"; actual is 54).

### Positive — Vendor* list accounting is provably correct
Both swap-remove impls (`removeVendor`, `removeDestination`) are correct across every edge case, incl.
the self-referential last-element write (`indexOf[last]=target` then `indexOf[removed]=0` on the same
address → 0). No off-by-one, no ghost-liveness after removal, no index collision on re-create;
`numVendors`/`numDests` can't underflow (the `!= 0` index assert implies count ≥ 2 before the decrement).
+8 gap-filling tests added to `test_payments.py` (middle/last-index swap-remove, `transferToProcessor`
guards + max default, `recoverFundsMany`, no-template revert, template perms).

## Toro's lane — x402 / EIP-3009 / EIP-712 / EIP-1271

Full detail in `AUDIT-PR76-toro.md`. Headline: **digest/domain math verified correct two ways**
(spec-reference parity test over 4 value/window combos incl. `value=2²⁵⁶-1`; live Base-mainnet read —
native USDC `0x8335…2913` `DOMAIN_SEPARATOR()` matches byte-for-byte). New `test_x402_digest_parity.py`
(7 tests) closes the circular-mock coverage gap (MockUsdc has no `transferWithAuthorization`, so the PR
only ever tested `isValidSignature` against a digest the processor made itself).

- **[LOW] T1** — hardcoded domain assumes native USDC; point `_usdc` at bridged USDbC and x402 silently
  never settles. Guard: constructor `assert UsdcDomain(_usdc).DOMAIN_SEPARATOR() == self._domainSeparator()`.
- **[LOW] T2** — `validAfter`/`validBefore` unvalidated → stuck-but-refundable ops. `assert validAfter < validBefore`.
- **[reinforces F1]** partial x402 refund is the x402-side root cause — already closed by F1's
  all-or-nothing `assert _amount == op.amount - op.refunded`.
- **[INFO] T3** — permissionless settle / refund race, bounded (params not emitted → merchant-only trigger);
  `authorized[digest]` not cleared on pull is safe (USDC nonce blocks re-pull); CEI on `refund()` verified safe.

## SwitchboardDelta — trust-root gateway (Moto, added rev d7895a5)

`contracts/config/SwitchboardDelta.vy` (334L) is the single caller-authorization layer in front of every
switchboard-gated call to the payments departments. Reviewed in full; **4 SwitchboardDelta tests pass**
(operate-gating, dept routing, config timelock, pause) within the 58-case suite.

**Positive — the tiering is well-designed (the key result):** the *immediate* tier (governance **or** a
MissionControl security signer — the server keys — via `_canOperate`) is confined to **non-redirecting**
operations: `settle` (→ availToBridge), `bridge` (→ the *already-set*, timelocked `bridgeAddress`),
`refund` (→ the recorded `op.payer`), vendor/destination admin, and pause. Every action that could
**redirect funds** — `setSender` (who may move user USDC), `setBridge` (where MPP lands),
`setVendorTemplate` — is *governance-only + timelocked* (`initiate → executePendingAction` after the
confirmation block; `cancelPendingAction`). **Net: a compromised server/security key can grief or DoS,
but cannot steal** — it can't redirect the bridge, add a sender, or swap the template. That containment
is the right call and worth crediting.

- **[LOW · availability] SD-1** — the flip side of the immediate tier: one compromised security signer
  can freeze the whole stack (`setPaused(True)` pauses both depts) and/or `removeVendor` (the kill switch)
  / `removeDestination` at will, with no timelock. Recovery is gov-only and **unpause is timelocked**, so
  an incident's recovery is deliberately slow. Availability depends on security-signer key hygiene.
- **[LOW · counterparty] SD-2** — MPP escrow is `settle`d (making it non-refundable) and `bridge`d to the
  off-ramp by a security signer **immediately, no timelock**; refunds are discretionary and can be
  *foreclosed* by settling first. Concretely, this is the counterparty exposure: once bridged, funds are
  off-chain (Tempo) and users have no on-chain recourse.
- **[LOW · deploy-time] SD-3** — for any of this to work, `SwitchboardDelta` must be registered as an
  `isSwitchboardAddr` the payments depts trust, and MissionControl (dept 2) must be set (else the
  security-signer branch of `_canOperate` reverts — fail-closed to gov-only). Both are deploy invariants,
  not code bugs.
- **[INFO] SD-4** — the x402 destination allow-list is edited in the immediate (non-timelocked) tier.
  Acceptable: adding a dest is necessary-but-not-sufficient to move funds (still needs a timelocked
  `setSender` **and** an owner-signed user payment to that dest), so it isn't a redirection primitive.
- **[INFO] SD-5** — `executePendingAction` relies on `Timelock._confirmAction` being single-use plus the
  `actionType[_aid]` clear to prevent re-execution / action-type confusion; a stale/cleared `_aid` that
  reached dispatch would no-op safely. Optional defense-in-depth: `assert actionType[_aid] != empty(...)`.
  (Optional: a second adversarial pass on the execute/timelock path — cheap insurance on the trust root.)
- **[minor] VendorRegistry pause** (also new): `createVendor` **and** `removeVendor` now assert
  `not isPaused`. Gating the *kill switch* behind pause is a slight asymmetry, but harmless — a paused
  PayProcessor already can't settle, so a still-listed vendor can't do anything while paused.

## Lane status — ALL COMPLETE

- **Moto** — ✅ coordination + F1 fixed/tested + F2/F3/F4 implemented/tested + consolidation.
- **Luna** — ✅ MPP sweep: F5 fixed, F6/F7 documented; reviewed & confirmed F1.
- **Toro** — ✅ x402 lane: digest/domain verified correct; T1/T2/T3 documented.
- **Gina** — ✅ sender/sig lane: found F2/F3/F4 (now fixed).
- **Leto** — ✅ Vendor*/tests: list logic proven; Leto-A/B/C; +8 tests.

## Future work: MPP settlement verification (SD-2 mitigation)

Forward-looking design (not built). Closes the counterparty gap in SD-2: MPP escrow is `settle`d
(non-refundable) and `bridge`d to an off-chain Tempo omnibus by a security signer with **no on-chain proof
the merchant was paid**. Goal: give Base an on-chain signal that a `paymentId` settled on Tempo.

**Two hard constraints (why cheap trustless verification is impossible):**
1. **Cross-chain opacity** — Base can't know Tempo state without a message/proof carrying its own security.
   A bare server signature is *accountability, not verification*.
2. **Omnibus pooling** — funds are pooled before settlement, so the `paymentId → merchant` link is off-chain
   by construction. Per-payment verification needs per-payment (or merkle-committed) Tempo settlement, not
   an omnibus sweep.

**Key enabler (Toro's audit):** `operations[paymentId]` is never deleted and survives `bridge()`, so a
later confirmation can cross-check `amount`/`merchantRef` against the stored op post-bridge. The mechanism
is **purely additive** — no money-path refactor.

**Additive contract shape:**
- New op fields `confirmed: bool`, `confirmDeadline: uint256` (set at settle/bridge).
- `confirmSettlement(paymentId, amount, merchantRef, tempoRef, proof: Bytes[...])`: load op; require
  exists + settled + not confirmed; cross-check `amount == op.amount - op.refunded` and
  `merchantRef == op.merchantRef`; verify `proof` per the trust tier; set `confirmed=True`; emit
  `SettlementConfirmed`.
- Enforcement: past `confirmDeadline` without confirmation → trip the existing `pause()` circuit-breaker
  and/or slash an operator bond; unconfirmed batches halt further bridging.

**Trust tiers (pick per Tempo capabilities):**
- **A. Operator-attested + bond + pause** — `proof` = operator sig. Accountability only; economic security
  via bond + auto-freeze. No new identity. *Works today.*
- **B. Merchant co-signed** — real teeth **only if the merchant self-enrolls their key** (else the operator
  sets the "merchant" key and self-attests). MPP has no on-chain merchant identity today, so this needs a
  new enrollment path (merchant-controlled key on the vendor record). Note: `merchantRef` is an unvalidated,
  operator-chosen `bytes32` (PayProcessor.vy:171), so cross-checking it alone proves nothing about the payee.
- **C. Chainlink CCIP** — `proof` = a CCIP message verified via `ccipReceive()` as originating from the
  allow-listed Tempo settlement contract; trust = CCIP DON + RMN. **Requires (i) a Tempo↔Base CCIP lane and
  (ii) the Tempo contract emitting the message ATOMICALLY in the tx that pays the merchant** (else CCIP
  faithfully delivers a false claim). Sidesteps the identity-anchor problem — strongest path.

**Open decisions before build:** (1) trust tier (A now, C when a Tempo lane exists); (2) does Tempo settle
per-paymentId or omnibus?; (3) merchant-key enrollment self-sovereign vs operator-set?; (4) bond mechanics
+ deadline tolerance (must survive transient CCIP delay, not auto-slash on a hiccup); (5) does `confirmed`
gate further `bridge()`, or is it advisory + monitored off-chain?

**Recommendation:** ship **tier A** as the near-term accountability layer (additive, no new identity, works
regardless of Tempo), and make `confirmSettlement`'s `proof` an opaque `Bytes` blob so the verification tier
can be swapped to CCIP later without touching the op lifecycle. Be explicit in-product that pure-omnibus
payments are *unverified by design*.
