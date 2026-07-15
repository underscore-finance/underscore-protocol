# PR #76 audit — Toro's lane: x402 / EIP-3009 / EIP-712 / EIP-1271

Scope: the `x402 exact` scheme in `PayProcessor.vy` — digest construction, the
EIP-1271 payer path (`isValidSignature`), nonce derivation, and refund/revoke
correctness. Artifacts: `tests/core/payments/test_x402_digest_parity.py` (new).

## Headline: the digest math is CORRECT and interoperates with real Base USDC

The rail hinges on one invariant: the digest the processor pre-computes at
`register()` and stores in `authorized[digest]` must byte-for-byte equal the
digest real USDC (FiatTokenV2) recomputes before calling
`isValidSignature(digest, sig)`. Verified two independent ways:

1. **Spec-reference parity test** — reconstructed the EIP-712 digest from raw
   keccak/abi per EIP-3009 and asserted equality with `getX402Digest(...)` over
   4 value/window combos incl. `value = 2**256-1` and tight windows. PASS.
   Also pins `x402Nonce == keccak256(paymentId)` and that a 1-bit-flipped digest
   is NOT honored (`isValidSignature → FAIL`).
2. **Live Base-mainnet read** (via public RPC `mainnet.base.org`): native USDC
   `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` reports `name()=="USD Coin"`,
   `version()=="2"`, and its on-chain `DOMAIN_SEPARATOR()` equals the domain the
   contract hardcodes (`keccak("USD Coin")`, `keccak("2")`, chainId 8453, USDC).
   EXACT MATCH: `02fa7265…7834f`.

⇒ The "USDC domain-match / x402 liveness" open item is **resolved: correct.**
Typehashes, field order, `from=self`, `\x19\x01` prefix, and nonce derivation
all check out. The critical caveat is purely deploy-time (below).

### Coverage gap this exposes (the reason it was worth verifying)
`MockUsdc` has **no `transferWithAuthorization`**, so the existing suite only
ever asks `isValidSignature` about a digest the processor itself produced
(circular). Nothing in the PR proved parity with real USDC — a wrong
domain/typehash/field-order would have shipped silently and x402 would never
settle on mainnet. `test_x402_digest_parity.py` closes that gap and will fail CI
on any future encoding drift.

## Findings

### [LOW · deploy-time] Hardcoded domain assumes the native-USDC address
`_NAME_HASH`/`_VERSION_HASH` are compile-time constants for `"USD Coin"`/`"2"`.
If `_usdc` is ever pointed at bridged **USDbC** (`name() == "USD Base Coin"`) or
any non-Circle token, the domain mismatches and x402 **silently never settles** —
`register()` still pulls USDC into the processor and authorizes a digest that no
facilitator can ever satisfy; funds sit until a `refund()`. No revert warns you.

**Recommended hardening (cheap, enforced):** assert the token's own domain at
construction so a wrong address fails the deploy loudly:
```vyper
interface UsdcDomain:
    def DOMAIN_SEPARATOR() -> bytes32: view
# in __init__, after USDC is set:
assert staticcall UsdcDomain(_usdc).DOMAIN_SEPARATOR() == self._domainSeparator()  # dev: usdc domain mismatch
```
FiatTokenV2_2 exposes `DOMAIN_SEPARATOR()` (confirmed live above). Cost: the
mock must add a matching `DOMAIN_SEPARATOR()`; minor. Turns "deploy carefully"
into an on-chain invariant.

### [reinforces F1 · x402 root cause] Partial x402 refund is semantically invalid
EIP-3009 authorizations are all-or-nothing — the facilitator pulls the full
`value` or nothing; there is no partial pull. So `refund(paymentId, _amount)`
with `_amount < outstanding` on an x402 op is meaningless: it revokes the
**entire** digest (merchant can now pull none of it) yet returns only part to the
payer, stranding the remainder — and, by clearing `opDigest`, triggers Moto's F1
cross-rail contamination (the op then looks like MPP to `settle()`/`refund()`).

**x402 side of the fix** (complements Luna's immutable-rail change): force x402
refunds to be all-or-nothing —
`assert _amount == op.amount - op.refunded  # dev: x402 refund must be full`
— so the digest and the returned amount can never disagree.

### [LOW] `validAfter`/`validBefore` unvalidated at `register()`
Decoded from `_extraData` and passed straight into the digest with no check. An
already-expired (`validBefore <= now`) or inverted (`validAfter >= validBefore`)
window yields an op USDC will always reject → funds stuck in the processor until
a refund. Not a loss (refundable), but a silent operator footgun.
**Fix:** `assert validAfter < validBefore` (and optionally
`assert validBefore > block.timestamp`) in the x402 branch. Operator-controlled
+ Switchboard-gated, hence LOW.

### [LOW · informational] `isValidSignature` is permissionless / ignores `_signature`; refund is a race
By design the funded, dest-gated registration IS the authorization, so MAGIC is
returned for any authorized digest regardless of caller/signature. Safe on the
two axes that matter: **redirection** (dest is bound into the digest — funds can
only reach the allow-listed dest) and **replay** (USDC's per-`from` nonce blocks
the second pull). Residual: settlement is a public action, so a pending refund is
inherently a race against a pull. Mitigating nuance — `validAfter`/`validBefore`
are **not emitted on-chain** (only amount/dest/digest/nonce are via
`OperationRegistered`/`X402Authorized`), so only a party holding the full x402
payload (the merchant/facilitator) can actually form the pull; a random observer
cannot. Net: "the merchant can pull anytime before a refund lands," which matches
EIP-3009 semantics. If guaranteed refunds are a product requirement they must be
enforced off-chain (settlement hold with the facilitator) — not expressible here.

### [informational] `authorized[digest]` is never cleared on a successful pull
The processor gets no callback from USDC at settle, so a spent digest keeps
returning MAGIC. Not exploitable — USDC's `authorizationState[self][nonce]`
blocks the second pull, and `refund()` correctly consults it to detect a
completed pull. Reliance is already documented in the contract. No action.

### [verified safe] CEI / reentrancy on `refund()`
All state (`authorized`, `opDigest`, `refunded`, `pendingTotal`) is written
before the final `transfer(op.payer, …)`. Standard USDC transfer has no recipient
hook so reentrancy isn't reachable; and `refunded` is persisted pre-transfer, so
the `_amount <= op.amount - op.refunded` guard can't be beaten even if it were.
Correct.

## Suggested severities for consolidation
- Digest/domain correctness: **verified OK** (was flagged as a liveness risk).
- Deploy-time domain guard: **LOW** (recommend the constructor assert).
- x402 partial-refund: fold into **F1 (HIGH)** as the x402-side root cause + fix.
- `validAfter/Before` validation: **LOW**.
- Permissionless settle / refund race: **LOW/informational** (Moto already noted;
  I add the params-not-emitted bound on who can trigger it).
