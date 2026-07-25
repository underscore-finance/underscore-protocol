# Incremental Extenders for the Existing User Wallet — Proposal (Claude)

**Status:** **SUPERSEDED as an independent architecture plan**

**Authority notice:** On 2026-07-24, the owner selected
[`simplified-user-wallet-action-architecture-codex.md`](simplified-user-wallet-action-architecture-codex.md)
as the governing architecture for this track. This proposal remains preserved
as independent analysis and provenance. Its useful spike-first sequencing,
family-by-family Lego revision, EIP-170 measurement, and direct-rail
preservation constraints are folded into sections 17–18 of the governing
document. Where the documents conflict, the governing document controls. No
code change is authorized by this file.

**Task framing:** Apply the architectural concepts and learnings from the
Wallets V3 Lean PoC to the *existing* user wallet system
(`contracts/core/userWallet/` + walletBackpack + legos), without the
POC's wholesale replacement of Config, Sentinel, permissioning, fees, or
wallet creation. Migration paths are explicitly out of scope. Gas savings
are explicitly a secondary goal — the primary goal is a smaller, safer,
more extensible change.

**Inputs:** [Lean PoC Architecture](../poc/user-wallet/user-wallet.md) ·
[PoC Results](../poc/user-wallet/POC_RESULTS.md) ·
[Production Design Plan](../poc/user-wallet/production-design-plan.md) ·
current `UserWallet.vy` / `UserWalletConfig.vy` / walletBackpack contracts.

**Revision 2** — after cross-review against the independent Codex proposal
([user-wallet-incremental-extender-proposal-codex.md](../user-wallet-incremental-extender-proposal-codex.md)).
Incorporated: the lego caller-identity constraint (verified in code — it
invalidates this document's earlier "legos change one line" claim and its
`CORE_CONSUMED` transitional mode), typed-facade entry points, the
`preparePayment` special-path requirement, debt staging by effect class,
the LegoBook ID-succession rule, and a spike-first Phase 1a. Rejected (with
reasons, §4a): making the wallet permanently remain the lego caller via
per-action compatibility callbacks.

**Revision 3** — cross-review round 2 convergence: the generic escape
hatch is upgraded from `execute(bytes)` to a **committed-intent
dispatcher** (`executeExtender(route, extenderCalldata, expectedIntent)`),
giving the escape path facade-grade intent binding; one intent vocabulary,
one downstream session architecture (§3). Added the vocabulary-reservation
open question (#6).

---

## 1. Executive summary

The existing `UserWallet.vy` is two things fused into one contract:

1. **A custody core** — asset registry, balances, approvals, fee/loot hooks,
   asset-data accounting, transfer path.
2. **An action catalog** — ~20 hardcoded external functions (yield, debt,
   swap, liquidity, rewards) that each orchestrate one lego call inside an
   identical envelope: *pre-action permission bundle → exact approve → lego
   call → reset approval → post-action limits/fees/accounting*.

The PoC's single most transferable idea is that **the action catalog does not
need to live in the wallet**. Each catalog entry is ~30–60 lines of
orchestration that can move into a shared, stateless, versioned **extender**
contract, while the wallet keeps only a generic **session engine**: it
authorizes the action (via the *existing* Config → ActionDataProvider →
Sentinel path, unchanged), grants one exact bounded approval, lets the pinned
lego consume it, and settles (revoke approval, bound outflow, run the
*existing* post-action fee/limit/accounting hooks).

Concretely, this proposal:

- **Keeps** UserWalletConfig, Sentinel, ActionDataProvider, HighCommand,
  Paymaster, ChequeBook, Kernel, Migrator, LegoBook, all legos, Hatchery,
  fees/loot, freeze/eject, and the transfer/cheque/ETH-WETH paths **as they
  are today**.
- **Adds** to UserWallet a compact session engine imported from the PoC —
  transient phase lock, one capability envelope per session, exact
  session-scoped approvals, settlement bounds — entered through **typed
  facades that keep today's public ABI** (`depositForYield(...)`, etc.),
  with a **committed-intent generic dispatcher**
  (`executeExtender(route, extenderCalldata, expectedIntent)`) as the
  escape hatch for families that ship between template generations. Both
  entries establish the same canonical intent; everything downstream is
  one execution architecture.
- **Requires** a session-aware revision of the legos each routed family
  uses (they currently pull from `msg.sender` and assert wallet-as-caller —
  §4a); revised legos register under new LegoBook IDs and coexist with the
  legacy fleet.
- **Moves** action families out of UserWallet into extenders one at a time —
  starting with **YieldExtender** and **DebtExtender**, exactly the "start
  from the extender system" framing.
- **Replaces** the wallet's one genuinely scary generic mechanism —
  `_setLegoAccessForAction`'s arbitrary-ABI `raw_call` authority grant — with
  the PoC's *named fixed-authority primitive* pattern.
- **Defers** payments/reservations (x402 / reserved transfer) to a later
  phase as a pure addition (a PaymentExtender consuming the same engine), and
  leaves cheques untouched until then.

The result is one wallet template generation per phase, each independently
shippable, each strictly smaller in blast radius than the PoC rewrite, and
each relieving rather than worsening the EIP-170 pressure that is currently
the system's binding constraint (~1.5 KB headroom in UserWallet, ~0.7 KB in
UserWalletConfig).

What we consciously give up (accepted tradeoffs, per the task framing):

- The PoC's −90% transfer gas. The direct transfer path here is *unchanged*,
  so nothing regresses, but nothing improves either.
- The 125-line Config. We keep the full Config/Sentinel policy machine and
  its per-action staticcall costs.
- Direct owner Config replacement. Existing ownership/security/migration
  machinery stays authoritative.

---

## 2. What we keep vs. what we import

| Layer | Today | This proposal | PoC learning applied |
|---|---|---|---|
| Custody & identity | UserWallet holds all assets | Unchanged | Stable custody address (trivially — same contract) |
| Permissioning | Config → ActionDataProvider → Sentinel (`checkSignerPermissionsAndGetBundle`, `checkManagerLimitsPostTx`) | Unchanged; called from the session engine instead of per-action functions | `authorizeSession` maps 1:1 onto the existing pre-action gate |
| Action orchestration | ~20 hardcoded functions in UserWallet | Typed extenders, attached per wallet, routed by selector | Extender pattern, typed CALL, no delegatecall |
| Lego layer | LegoBook + `LegoPartner` interface | Unchanged; legos gain one small `consumeCapability` call before pulling funds | Capability consumption binds actual effect to authorized request |
| Extender governance | n/a | New `ExtenderBook` registry (clone of LegoBook: timelocked, AddressRegistry-based) | PoC deferred ExtenderBook; the production repo already has the exact pattern |
| Attachment lifecycle | n/a | Append-only per-wallet records, codehash-pinned, family-versioned, auto `DRAIN_ONLY` on succession | Demonstrated PoC mechanism, kept per POC_RESULTS |
| Authority grants | `_setLegoAccessForAction` raw_call with lego-supplied ABI string | Named fixed-authority primitive per protocol family | PoC Q5: named primitives, **abandon** generic executor |
| Fees / loot / accounting | `_performPostActionTasks`, `_checkForYieldProfits`, Appraiser, LootDistributor | Unchanged; run at session settlement | Settlement phase is the natural home for post-action hooks |
| Payments | ChequeBook | Unchanged now; later a PaymentExtender adds reservations/x402 alongside cheques | Wallet-held reservations, terminal non-reuse (kept per POC_RESULTS) |
| Reentrancy | `@nonreentrant` per function | Transient phase machine for routed actions; `@nonreentrant` stays on core paths | Phase-before-external-call invariant |

---

## 3. Target architecture

```text
caller (owner / manager / agent)
   │
   ├── transferFunds / cheques / eth↔weth ──────────► unchanged core paths
   │
   └── wallet.execute(typedExtenderCalldata)
          │  selector → attachment (codehash-pinned)
          ▼
   ┌──────────────────────────────────────────────────────┐
   │ UserWallet (custody + session engine)                │
   │  DISPATCHING: record frame (real caller, selector,   │
   │               action, calldata hash, nonce)          │
   │  ──CALL──► Extender (stateless, shared, versioned)   │
   │  ◄─reenter─ openSession(envelope)                    │
   │     · checkSignerPermissionsAndGetBundle (Config →   │
   │       ActionDataProvider → Sentinel — TODAY'S GATE)  │
   │     · frozen / eject checks (today's rules)          │
   │     · grant exact approval to pinned lego            │
   │  Extender ──CALL──► Lego (LegoBook, unchanged role)  │
   │  ◄─reenter─ consumeCapability(actual, txUsdValue,    │
   │             touchedAssets)                           │
   │     · semantic hash must match authorized request    │
   │     · lego pulls funds via the exact approval        │
   │  SETTLING (after extender returns):                  │
   │     · revoke approval, bound net outflow             │
   │     · _performPostActionTasks (fees, loot, asset     │
   │       data, Sentinel post-tx manager limits — TODAY) │
   └──────────────────────────────────────────────────────┘

   ExtenderBook (new registry, LegoBook clone, timelocked)
   WalletBackpack / Sentinel / HighCommand / ... (unchanged)
```

Extenders are **stateless shared singletons** like the backpack contracts —
one deployment serves every wallet. An *attachment* is a small per-wallet
record that enables a (family, version, extender address, codehash, routes)
tuple for that wallet. New wallets get the standard set attached at Hatchery
creation, the same way backpack addresses are wired today.

### Why wallet-entry dispatch (not calling extenders directly)

If users called extenders directly, the wallet could not authenticate the
original signer — the extender would assert "the caller was X" and Sentinel's
per-manager permissions would rest on extender honesty. Routing through the
wallet keeps `msg.sender` authentication exactly where it is today, at the
wallet boundary.

### Keep the typed public API as facades

The wallet keeps its existing typed entry points (`depositForYield(...)`,
`borrow(...)`, …) as thin **facades**: each packs the capability envelope —
including `actionDataHash` computed *by the wallet from the typed
arguments* — records the frame, and dispatches to the attached family
extender.

For families that ship between wallet-template generations, the generic
entry is a **committed-intent dispatcher** (adopted from cross-review
round 2), not a bare `execute(bytes)`:

```text
executeExtender(route, extenderCalldata, expectedIntent)
```

The caller supplies the canonical intent explicitly; the wallet commits to
it before dispatch, and the extender's `openSession` must match it exactly
— the same binding guarantee the facades provide. The opaque calldata
becomes advisory input for the extender; the committed intent is the
enforcement surface. If calldata and intent disagree, an honest extender's
session mismatches and the call fails closed; a malicious extender is
bounded by the commitment regardless.

**Vocabulary rule:** `expectedIntent` is exactly the canonical envelope
plus the Sentinel inputs — `actionType, assets[], legoIds[], effectClass,
consumerMode, maxAmount, beneficiary, actionDataHash` — never a parallel
schema. A facade and the dispatcher are two ways to *establish* one
`ActionIntent`; there is one session architecture downstream, not two.

The result is three deliberate tiers:

1. **Typed facade** — best UX, ABI stability, differential testing, and
   wallet-computed intent.
2. **Committed generic dispatch** — future extensibility without trusting
   an extender to invent the caller's intent.
3. **No arbitrary execution** — the wallet never becomes a generic
   target-and-calldata executor.

This costs a small per-action stub (signature + envelope pack + dispatch —
far smaller than today's full orchestration bodies) and buys three things:

1. **Unchanged ABI** for SDKs, agents, and — critically — differential
   parity testing against the current wallet.
2. **Firsthand intent binding.** Because the wallet derives the semantic
   hash from arguments the caller handed it directly, a malicious extender
   cannot substitute vault/asset/amount/beneficiary at all — it can only
   refuse to proceed (a liveness risk, not a custody risk). This is
   *stronger than the PoC*, whose recorded residual risk was precisely that
   an extender could choose a different still-policy-authorized request.
   With the committed-intent dispatcher, the same guarantee extends to the
   escape-hatch path (the caller, not the extender, supplies the intent).
   Preconditions for the "liveness-only" claim, which the engine must
   enforce and tests must mutation-check: exact commitment matching, only
   the pinned consumer may consume, approval/session cleanup cannot be
   bypassed, and the capability vocabulary fully describes the dangerous
   effects — for LIABILITY actions that last condition is met only
   together with the protocol-specific position postconditions (§10).
3. **Sentinel inputs stay truthful on every path.** The pre-action gate
   needs typed inputs (ActionType, assets, legoIds); facades produce them
   firsthand and the dispatcher takes them from the caller's committed
   intent — never from extender claims.

**Pattern uniformity rule (owner preference, 2026-07-24):** every routed
action — single-step or multi-step — follows the identical POC session
pattern: the extender opens the session, the consumer consumes the
capability, the wallet settles. A possible optimization (facade opens
single-step sessions itself, skipping one re-entry) is deliberately NOT
part of the design; it would give single- and multi-step flows different
session shapes. Revisit only if Phase 1a gas measurements make the
re-entry cost material, and then as a uniform change, not a special case.

---

## 4. Anatomy of one routed action (yield deposit, before/after)

**Today** (`depositForYield`, UserWallet.vy L229):

```text
1. _performPreActionTasks(msg.sender, EARN_DEPOSIT, ...)   # Config→ADP→Sentinel
2. _getAmountAndApprove(asset, amount, legoAddr)           # exact approve
3. extcall Lego.depositForYield(..., self, miniAddys)      # lego pulls, returns txUsdValue
4. _resetApproval
5. _performPostActionTasks([asset, vaultToken], txUsdValue) # limits, fees, asset data
6. _logWalletAction(op=10, ...)
```

**After** (route `YieldExtender.deposit` selector, attachment #1):

```text
1. wallet.depositForYield(legoId, vault, asset, amount, extraData)
      # typed facade: phase IDLE→DISPATCHING; frame records real caller and
      # the envelope (actionDataHash computed by the wallet from typed args);
      # dependency codehashes verified
2. CALL YieldExtender.deposit(wallet, legoId, vault, asset, amount, extraData)
3.   extender → wallet.openSession(envelope{   # must equal the facade-recorded
                                               # intent exactly — same session
                                               # pattern for every routed action
         actionType: EARN_DEPOSIT,   # existing ws.ActionType, so Sentinel is unchanged
         consumer:   legoAddr,       # resolved via LegoBook, pinned for the session
         resource:   asset, maxAmount: amount,
         beneficiary: wallet, actionDataHash: keccak(vault, asset, amount, extra)})
       · wallet runs today's pre-action gate with frame.realCaller
       · wallet grants exact approval(legoAddr, amount)      # phase → ACTIVE
4.   extender → Lego.depositForYield(...)
5.     lego → wallet.consumeCapability(actualEnvelope, txUsdValue,
                                        touched=[asset, vaultToken])
       · semantic hash of actuals must equal authorized hash
       · lego then transferFrom()s the approved amount, deposits, sends
         vault tokens to the wallet
6. extender returns → wallet SETTLING:
       · approve(legoAddr, 0); net outflow ≤ maxAmount; allowance == 0
       · _performPostActionTasks(touched, txUsdValue, ...)   # UNCHANGED code
       · _logWalletAction(...) from route metadata
       · phase → IDLE
```

Everything Sentinel/Config/fees/loot do today happens at the same two points
(pre-gate, post-settle) with the same structs. The only new trust surface is
the extender itself — which is codehash-pinned per wallet and
registry-governed globally (§7).

### 4a. The lego caller-identity constraint (load-bearing)

Current legos assume the wallet is their **direct caller**. Verified in
code: deposit paths pull via `transferFrom(msg.sender, ...)`
([AaveV3.vy:494](../../contracts/legos/yield/AaveV3.vy),
[RipeLego.vy:560](../../contracts/legos/RipeLego.vy)), and Ripe's
collateral/borrow/repay additionally assert `msg.sender == _recipient`
(RipeLego.vy:785, :880, :920) on top of
`_isAllowedToPerformAction(msg.sender)`. A `wallet → extender → unmodified
lego` call therefore fails outright: the lego sees the extender as
`msg.sender`, looks for the extender's funds, and trips Ripe's caller
checks. (Credit: this was independently identified by the Codex
cross-review; an earlier revision of this document wrongly claimed legos
needed only a one-line change, and proposed a `CORE_CONSUMED` transitional
mode that does not work — the `msg.sender` pull fails regardless of who
consumes the capability.)

This proposal's call graph therefore requires a **session-aware lego
revision** — mechanical, but a hard prerequisite for routing a family:

- pull funds from the explicit wallet parameter (`_recipient`) instead of
  `msg.sender`;
- replace caller-identity asserts with one
  `wallet.consumeCapability(actual, ...)` call, which simultaneously
  *authenticates* (only the active session's pinned lego may consume,
  only while the wallet's frame is ACTIVE, only for the pinned wallet) and
  *binds* the actual effect fields to the authorized envelope;
- deliver outputs directly to the wallet, as today.

*Owner decision 2026-07-24: updating the legos to the session-aware
interface is approved — this constraint is resolved in favor of the
revision path below, and §4b's callback design remains only a per-family
fallback.*

Scope honesty and why this is still incremental:

- The change is repetitive across lego action functions but can be
  centralized in the shared lego modules; it does not alter what any lego
  does to its protocol.
- **No deployed wallet or serving lego is touched.** Revised legos register
  under **new LegoBook IDs**; legacy legos keep serving legacy wallets; new
  wallet templates route only to session-aware IDs. Since migration is out
  of scope, the two fleets coexist indefinitely.
- The revision can land family-by-family (yield legos for Phase 1, debt
  legos with it, dex/liquidity legos by Phase 3) — it does not need to be
  one big-bang lego release.

### 4b. The rejected alternative: wallet stays the lego caller

The Codex cross-review proposes keeping legos 100% unchanged by having the
extender coordinate **typed callbacks into the wallet**
(`extensionYieldDeposit(...)` etc.), so the wallet remains the lego's
`msg.sender`. This genuinely works, and its containment story is excellent
(the wallet executes only pre-bound typed calls). This proposal adopts its
binding idea via facades (§3) but rejects it as the *target* call graph,
for three reasons:

1. **It doesn't extract anything for single-step actions.** The
   approve/lego-call/result code moves from today's function bodies into
   per-action wallet callbacks — same contract, plus frame machinery, plus
   facades. UserWallet likely *grows*, against a 1,544-byte budget; the
   Codex document's own stop-condition acknowledges this risk. Deposit,
   borrow, repay, addCollateral — most of the catalog — gain a round-trip
   with no relocation of logic.
2. **Extensibility stays gated on the wallet.** New action *compositions*
   ship as extenders, but any new action *shape* (new lego call signature)
   still needs a new wallet callback — a new template generation. The
   PoC's demonstrated future-family result (new action, zero core change)
   is lost.
3. **It converges here anyway.** The Codex proposal itself sketches a
   "later session-aware lego interface" as the eventual end state. If
   that's the destination, building the per-action callback layer first
   means building — and later retiring — a second complete compatibility
   surface, which is the complexity its own stop-condition warns about.

Where the callback approach is clearly right is *when a family's legos
cannot be revised yet*. If Phase 1's lego revision proves more expensive
than estimated, a facade-driven callback for that family alone is the
fallback — per family, not as the architecture.

---

## 5. The capability envelope, adapted

The PoC's `ActionEnvelope` maps onto existing concepts almost field-for-field:

| PoC field | Incremental version | Notes |
|---|---|---|
| `actionId: uint16` | `actionType: ws.ActionType` | Reuse the existing flag so Sentinel's permission mapping (`canManageYield`, `canManageDebt`, …) works with **zero** Sentinel changes in Phase 1 |
| `effectClass` | keep (SPEND / LIABILITY / ASSET_RELEASE / AUTHORITY) | New concept worth importing: it's what lets borrow/remove-collateral be bounded semantically instead of by allowance |
| `consumer` | lego address resolved from LegoBook by `legoId` | Pinned per session; Sentinel's `allowedLegos` check still applies |
| `resource` / `maxAmount` | asset + amount | Same as today's `_getAmountAndApprove` inputs |
| `beneficiary` | recipient constraint | Wallet-or-consumer for yield/debt; payee-checked via existing Paymaster/whitelist rules for anything outbound |
| `actionDataHash` | keccak of the action-specific args, computed by the typed facade from firsthand arguments | The binding that today simply doesn't exist — currently a lego is trusted to do what the wallet function implied. Facade-side computation also removes extender argument-substitution risk entirely for the standard catalog |

Sentinel's known footgun — the `ActionType → permission` `if/elif` that
falls through to `return True` for unknown types — should be fixed in the
same change that introduces routes: unknown action types **fail closed**.
That is a two-line Sentinel change and is exactly the kind of
mutation-sensitive check the production plan requires.

---

## 6. Where the bytes go (EIP-170 accounting)

Current documented figures: UserWallet runtime 23,032 B (~1.5 KB headroom),
UserWalletConfig 23,856 B init (~0.7 KB under the deploy gate). Neither can
absorb a session engine as a pure addition — the engine must *displace*
moved-out action families in the same template generation.

Rough budget (to be validated by compilation gates, per repo practice):

| Change | Direction | Estimate |
|---|---|---|
| Session engine (dispatch, openSession, consumeCapability, settle, attachment storage + views) | + | ~4–6 KB (PoC's whole core incl. transfer/config/payments was 12 KB; the engine subset is well under half) |
| Typed facades for routed families (§3) | + | ~0.5–1 KB (stubs: signature + envelope pack + dispatch) |
| Remove yield family (3 fns + branches) | − | ~2–2.5 KB |
| Remove debt family (5 fns incl. deleverage + `_setLegoAccessForAction` raw_call machinery) | − | ~2.5–3 KB |
| Remove swap + liquidity + rewards (Phase 3) | − | ~4–5 KB |

So **Phase 1 must move yield and debt together** to pay for the engine —
which is precisely the starting point requested. By Phase 3 the wallet
should sit several KB below the limit for the first time, ending the
optimizer-pragma tightrope documented in the gas-profiling notes.

Two structural rules keep the pressure off permanently:

1. **Attachment admin logic lives outside the wallet.** A new stateless
   backpack-style singleton (`ExtenderHub`, timelock-governed like the other
   backpack items) validates attach/succession requests and writes records
   through one narrow wallet setter — the same pattern as
   `updateAssetData`/`deregisterAsset` being config-gated today. The wallet
   carries only storage, the gated setter, and the runtime checks.
2. **UserWalletConfig is not touched at all** in Phases 1–3. Route→permission
   mapping rides on the existing ActionType; no new config structs.

`# pragma optimize codesize` and CI bytecode gates stay mandatory for every
phase.

---

## 7. Attachment, governance, and succession

Imported PoC mechanics, adjusted to the production registry world:

- **ExtenderBook** (new, boring): a `Department` wrapping `AddressRegistry`,
  identical in shape to LegoBook — timelocked add/confirm, `isExtenderAddr`.
  Global review/governance gate for extender code, exactly the trust level
  legos already receive.
- **Per-wallet attachment record** (stored in UserWallet):
  `familyId · version · extender address + codehash · routes
  (selector → actionType, effectClass, consumerMode, legoId?) ·
  exit selectors · lifecycle (ACTIVE | DRAIN_ONLY)`.
- **Attach/succession rules** (verbatim from the PoC — all demonstrated):
  append-only records; version strictly increases within a family;
  attaching a successor atomically unpublishes the predecessor's selectors
  and marks it `DRAIN_ONLY`; drain-only attachments accept only their
  registered exit selectors via `executeAttached`; codehashes are re-checked
  at every dispatch and every privileged re-entry; selector collisions
  across active families are rejected.
- **Who attaches:** owner action, subject to the existing security-action
  framework (freeze blocks it; the same `_canPerformSecurityAction` /
  timelock conventions the backpack setters use today). Candidate extenders
  must be ExtenderBook-registered — this is *stronger* than the PoC (which
  had owner-attest only) and consistent with how the system already treats
  legos. Hatchery attaches the default set at wallet creation.
- **LegoBook succession rule** (adopted from the Codex cross-review): once
  a lego ID has opened or managed wallet-keyed positions, never replace
  that ID's address in place. Register successors under new IDs and retain
  the old ID for exits. This preserves the meaning of existing
  `allowedLegos` lists, keeps an exact old adapter available for
  drain-only exits, and is also what lets session-aware legos (§4a)
  coexist with legacy ones.
- **DRAIN_ONLY is the upgrade story for action logic.** Today, changing yield
  behavior means a new wallet template + Migrator. With attachments, it means
  registering YieldExtender v2 and attaching it — the wallet address,
  positions, and config never move. This is the PoC's Q1/Q7 result applied
  where it actually pays off.

---

## 8. Phased plan

Each phase = one wallet-template generation, shippable and testable alone.
No phase requires migrating existing wallets (out of scope by task framing);
new templates simply apply to newly created wallets.

### Phase 1a — deposit-only spike (development gate, not a release)

Before committing to the full Phase 1 template generation, build the
narrowest falsifiable slice: the `depositForYield` facade + frame + one
`YieldExtender.deposit` + one session-aware revised yield lego (new
LegoBook ID), with:

- differential parity vs. the current wallet on the same fork state
  (balances, shares, asset data, manager counters, points, events, return
  tuples);
- the malicious-extender matrix (wrong lego, wrong args, double-consume,
  no-consume, out-of-frame calls, reentry attempts, drain-only misuse);
- proof that the frame composes with the existing `@nonreentrant` guards
  without weakening them;
- honest bytecode and gas deltas.

**Stop condition:** if the engine + facade machinery cannot pay for itself
in bytes once yield + debt are removed, or requires weakening reentrancy or
caller authentication, halt and fall back to the per-family callback
alternative (§4b) before building further.

### Phase 1 — Session engine + Yield & Debt extenders

- Add engine to UserWallet: typed facades, `executeExtender` /
  `executeAttached` (committed-intent escape hatch + drain exits),
  transient frame + capability,
  `openSession`, `consumeCapability`, settlement, attachment storage +
  gated setter. Requires the cancun EVM target for transient storage
  (flag: v2 currently compiles with the implicit target; Base supports
  cancun — confirm toolchain and re-run size/gas gates).
- Deploy `ExtenderHub` singleton + `ExtenderBook` registry.
- Build `YieldExtender` (deposit / withdraw / rebalance) and `DebtExtender`,
  staging debt internally by effect class (adopted from the cross-review):
  `addCollateral` / `repayDebt` first (spend-bounded — the approval is a
  real bound), then `borrow` / `removeCollateral` (semantically bounded —
  require protocol-specific before/after position checks against real
  Ripe state, not just envelope hashes), `deleverage` last (specialized
  multi-asset Ripe flow with subset-return invariants; it stays in the
  wallet until its differential matrix is complete).
- **Preserve the Config-initiated special path:** `preparePayment` drives
  `withdrawFromYield` with `_isSpecialTx` (config-gated, bypassing normal
  permissions). The routed family must keep an equivalent core-authorized
  path — simplest is a retained config-gated core withdrawal primitive
  rather than routing special txs through the extender. Missing this
  would silently break payment pulls.
- Revise yield + debt legos to the session-aware interface (§4a), register
  under new LegoBook IDs.
- Remove the corresponding legacy function bodies from UserWallet.
- Sentinel: unknown-ActionType fail-closed fix (+ mutation test).
- Fees/loot/asset-data/manager-limit behavior must be **byte-identical** in
  outcomes: golden tests comparing old function path vs. routed path on the
  same fork state.

### Phase 2 — Named authority primitives

- Replace `_setLegoAccessForAction`'s lego-supplied-ABI `raw_call` with named
  fixed-authority primitives (`setProtocolOperator`-style, one per protocol
  family that needs it — Ripe first). Grant callable only by the active
  routed DebtExtender session; revoke also callable via the drain-only exit
  route. This retires the closest thing the current wallet has to an
  arbitrary executor, applying the PoC's strongest security verdict (Q5:
  keep named primitives, abandon generic authority).

### Phase 3 — Swap, Liquidity, Rewards extenders

- Move `swapTokens`, `mintOrRedeemAsset`(+confirm), the four liquidity
  functions, and `claimIncentives` into three extenders.
- UserWallet is now: custody, transfer path, cheque payment hook, ETH/WETH,
  session engine, asset-data/fee hooks, NFT recovery. Several KB of
  headroom; the action catalog is fully externalized.
- Multi-step envelopes: swaps with `MAX_SWAP_INSTRUCTIONS` legs either run as
  one SPEND envelope bounded by (tokenIn, amountIn, minAmountOut in
  actionDataHash) — recommended — or the engine grows multi-capability
  sessions (not recommended; the PoC deliberately kept one capability per
  session and that simplicity is load-bearing).

### Phase 4 — PaymentExtender + reservations (optional, additive)

- Import wallet-held reservations, `EXTERNAL_EXACT` (x402/EIP-3009) and
  `RESERVED_TRANSFER` commitments, rail-only ERC-1271, permissionless sync.
- Pure addition: no existing path changes; cheques continue working and can
  later be re-expressed as commitments if ever desired.
- Gate on the production plan's D6/D10 decisions (rails, liveness, sponsor
  model) — the PoC itself marked commitment-creation cost REDESIGN.

### Phase 5 — Cleanups enabled by the new shape

- Retire per-family branches in `_performPostActionTasks` (e.g. the
  EARN_DEPOSIT/EARN_REBALANCE vault-token special case) in favor of
  extender-declared touched-asset roles.
- Evaluate whether Migrator/HighCommand size pressure can be relieved by the
  same displacement pattern.

---

## 9. Gas expectations (honest version)

- **Direct transfers: unchanged.** The PoC's headline −90% came from
  deleting Config/Sentinel/fee machinery; we are keeping it, so we don't get
  it. Nothing regresses either.
- **Routed actions: modest overhead vs. today.** Added costs per action: one
  extra CALL hop into the extender (+ calldata), ~15–25 transient
  stores/loads, 2–4 `extcodehash` checks, two keccaks for semantic binding.
  Ballpark +10–25k gas on actions that already cost 300k–800k through
  Config/Sentinel/Appraiser — low single-digit percent. The PoC's scary
  117k "empty session" number is not comparable: most of it was Config
  probing and framework setup that here *replaces* (not duplicates) the
  existing pre/post machinery.
- Per repo practice: paired before/after profiles at equivalent initialized
  state for each family in each phase, with review budgets set from the
  measurements — no optimization-by-vibes, and no check removed to hit a
  number (production-plan guardrail 10).

---

## 10. Security analysis

**Strictly better than today:**

- *Semantic binding where none exists.* Today a lego is trusted to perform
  the action the wallet function implied; nothing binds the lego call's
  actual (vault, asset, amount, beneficiary) to what was authorized beyond
  the approval amount. The envelope + `consumeCapability` hash check adds
  exact binding, with LIABILITY/ASSET_RELEASE classes covering effects that
  allowances cannot bound (borrow, remove-collateral) — the PoC's Q4 result.
  For LIABILITY effects specifically, hashes alone are not enough: the
  routed debt actions additionally require protocol-specific before/after
  position checks (e.g. Ripe debt delta ≤ authorized amount), or the
  residual is explicitly recorded as lego/protocol trust.
- *Facade-side intent binding.* Because typed facades compute the semantic
  hash from firsthand caller arguments, extender argument-substitution —
  the PoC's own recorded residual risk — is eliminated for the standard
  catalog; a malicious extender degrades to a liveness risk there.
- *Settlement bounds.* Net-outflow ≤ maxAmount, forced approval revocation,
  residual-allowance == 0 — mechanical invariants the current per-function
  code approximates by convention.
- *Named authority primitives replace the arbitrary-ABI access grant* (§8
  Phase 2). This is the largest single risk reduction in the proposal.
- *Codehash pinning + fail-closed unknown actions.*

**Unchanged (deliberately):**

- Config/Sentinel policy strength, manager/payee/cheque semantics, freeze,
  eject mode, ownership, security actions, migration machinery.
- Lego trust model — legos remain trusted adapters governed by LegoBook.
  (The envelope narrows what a *buggy* lego can do; a malicious registered
  lego remains a governance problem, as both today and the PoC concluded.)

**New surface to review:**

- The session engine itself (dispatch, transient state, re-entry points) —
  small, but it is core custody code; it needs the full adversarial test
  battery the PoC already wrote (hostile extender, hostile config probe,
  malformed ERC-20, nested-dispatch rollback, stale-session reuse), most of
  which ports directly.
- Extenders are trusted to preserve caller intent among policy-authorized
  requests (PoC residual risk, unchanged in kind from today's manager/agent
  trust — Sentinel limits still bound the damage).
- Opaque `execute(bytes)` calldata means route metadata (not the function
  selector namespace of the wallet) defines what's callable — the
  attach-time route validation and Sentinel fail-closed change carry that
  weight.

---

## 11. Extensibility: what "adding an action family" becomes

Today (per the current codebase): touch `ws.ActionType`, `LegoPartner.vyi`
plus ~15 legos, UserWallet (new function + op code + envelope wiring +
eject-mode list), Sentinel's if/elif, possibly config structs → all inside
two contracts with < 1.5 KB headroom.

After Phase 3: deploy a new extender + lego, register both in their books,
attach. The wallet core changes **only** if the family needs a genuinely new
effect class or a new named authority primitive — the PoC's
FutureActionExtender demonstrated exactly this (new Lego-consumed action,
zero core change). New ActionType members still need a Sentinel permission
branch — one stateless singleton with headroom, instead of five contracts.

---

## 12. Open questions for the owner

1. **Cancun/transient dependency** — confirm moving wallet templates to
   `evm_version=cancun`. Fallback: storage-slot phase lock (works, costs
   ~5k/action more and loses the free per-tx reset).
2. **Session-aware lego revision scope** — *DECIDED 2026-07-24: the owner
   approved updating the legos for the new structure.* Phase 1 proceeds
   with revised yield and debt legos under new LegoBook IDs (§4a), with
   legacy and session-aware fleets coexisting. Remaining sub-decision:
   whether the revision lands as a shared-module refactor across all legos
   or family-by-family (recommended: family-by-family, matching the phase
   sequence).
3. **Attachment authority** — owner-only with security-action override (my
   default above), or timelocked like whitelist additions?
4. **Existing-wallet story** — out of scope here by instruction, but the
   phase boundaries were chosen so Migrator-based adoption remains possible
   later; worth a one-page follow-up when this direction firms up.
5. **Does Phase 4 (payments) ride this track or the POC-derived production
   track?** The reservation/commitment design is wallet-core state; deciding
   early avoids designing the engine's storage twice.
6. **Vocabulary reservation** (from cross-review round 2). The
   committed-intent dispatcher extends existing vocabulary to new
   families, but a genuinely new *effect class* or a new stored manager
   permission still requires a template/Config-struct change. Partial
   relief: Sentinel is a replaceable backpack singleton, so new permission
   *logic* over existing structs can ship without template changes; new
   stored fields cannot. Decide in Phase 1 how much headroom to bake in —
   reserved effect-class values, action-id ranges per family, and whether
   `ManagerSettings`/`LegoPerms` get spare generic capability bits now
   while the structs are already being touched by nothing (i.e., weigh
   against the Config byte budget).

---

## Appendix A — Disposition of every UserWallet external function

| Function | Disposition | Phase |
|---|---|---|
| `transferFunds` (incl. special-tx path for Migrator/Billing) | stays in core, unchanged | — |
| `convertWethToEth` / `convertEthToWeth` | stays in core | — |
| `depositForYield` / `withdrawFromYield` / `rebalanceYieldPosition` | → YieldExtender | 1 |
| `addCollateral` / `removeCollateral` / `borrow` / `repayDebt` / `deleverage` | → DebtExtender | 1 |
| `setLegoAccessForAction` + `_setLegoAccessForAction` raw_call | → named authority primitive | 2 |
| `swapTokens` / `mintOrRedeemAsset` / `confirmMintOrRedeemAsset` | → SwapExtender | 3 |
| `addLiquidity` / `removeLiquidity` / `addLiquidityConcentrated` / `removeLiquidityConcentrated` | → LiquidityExtender | 3 |
| `claimIncentives` | → RewardsExtender | 3 |
| `updateAssetData` / `deregisterAsset` / `recoverNft` (config-gated hooks) | stay in core | — |
| `onERC721Received` / `__default__` | stay in core | — |
| `_performPreActionTasks` / `_performPostActionTasks` / `_checkForYieldProfits` / fee payers / `_updateAssetData` | stay in core; invoked from openSession/settlement | 1 |
| *(new)* `execute` / `executeAttached` / `openSession` / `consumeCapability` / attachment setter + views | added to core | 1 |

## Appendix B — PoC learnings scorecard for this proposal

| PoC KEEP verdict | Applied here? |
|---|---|
| Stable non-proxy custody address | Yes (trivially — same wallet contract) |
| Direct replaceable Config | **No** — existing Config/ownership machinery kept (accepted divergence) |
| Append-only codehash-pinned typed attachments | Yes (§7) |
| Selector-bounded DRAIN_ONLY succession | Yes (§7) |
| One transient capability per session | Yes (§5) |
| Exact approvals + semantic/effect bounds | Yes (§4, §5) |
| Named fixed-authority primitives, no generic executor | Yes — and it *removes* an existing generic mechanism (§8 Phase 2) |
| Wallet-held reservations, terminal commitment non-reuse | Deferred to Phase 4 |
| PoC REDESIGN verdicts (session overhead, payment creation cost) | Session overhead largely moot here (engine replaces, not duplicates, existing machinery); payment cost gated behind Phase 4 decisions |
| PoC ABANDON verdicts (arbitrary executor, general signatures, production-readiness claims) | Respected — nothing here relies on them |
