# Permission System for Wallet v3 — Research Synthesis

**Status:** Synthesis of four independent research reports, reconciled against the
code that actually exists. This is analysis and recommendation. It is not an
architecture decision and does not authorize contract changes. The governing
architecture remains
[`simplified-user-wallet-action-architecture-codex.md`](simplified-user-wallet-action-architecture-codex.md);
where this document disagrees with it, that is flagged explicitly and left as an
owner decision.

**Inputs:** four responses to
[`permission-action-taxonomy-research-prompt-codex.md`](permission-action-taxonomy-research-prompt-codex.md),
run independently against the same prompt (~34,600 words total), plus direct
verification against `contracts/` at commit `fdb3bad`.

---

## 0. The one-page version

Four models were asked the same question with no access to this codebase. They
converged much more than they diverged, and the convergence is worth more than any
individual recommendation.

**What all four independently concluded:**

1. The **open-actions / closed-authority** hypothesis survives. Action identities may
   be open-ended; authority semantics may not.
2. The single load-bearing boundary in the whole design is **"does any right survive
   this action?"** — not payment mechanism, not asset class, not protocol. (Their exact
   phrasing has a hole in it; see [§2.2](#22-the-persistence-test-is-the-primary-boundary--but-state-it-carefully).)
3. **Exposure-reducing authority must be separately delegable from exposure-increasing
   authority**, so that the exit path survives an incident that disables entry.
4. **Presets/bundles must expand to concrete permissions at grant time** and must never
   retroactively mutate an existing grant.
5. **Bit positions are permanent and append-only.** Reordering silently rewrites every
   stored grant.
6. Every persistent obligation must be **attributed to the manager that created it** and
   **enumerable by the owner**, or revocation is not possible.
7. The **manipulated-but-uncompromised AI agent** is the threat no permission taxonomy
   solves. All four say so plainly. This is the most important honest finding in the
   corpus.

**What I recommend on top of that:** a **17-permission taxonomy (11 INITIAL, 4 LATER,
2 RESERVED)** that keeps this repo's existing family axis and adds four genuinely new
initial bits — `POSITION_EXIT` (the defensive cross-cut), `REVOKE_CLAIMS` (the kill-switch),
`ENROLL_PAYEE` (which closes a leak all four reports miss) and `PAY_NETWORK_FEES`. Keep
**both** gates (per-manager `actionId` allowlist *and* categorical permissions), with the
registry's permission requirement **EXACT** rather than a floor or a ceiling. Do **not**
build a second cheap validation lane.

**Five findings that go beyond what any of the four reports says**, in rough order of value:

1. **The reports argue the bitmask on gas; here the binding constraint is bytecode.**
   `HighCommand` has 867 bytes of headroom and `ManagerSettings` ripples through eight
   files, so adding a permission today costs an ABI migration. That makes the mask far more
   urgent than any report realized — and the permission *count* far less important.
   [§9.1](#91-permissions-are-booleans-and-that-is-the-expensive-part)
2. **"Composite privilege equals the union of its permissions" is false.** All four assert
   it; none argues it. It holds for permissions and fails for limits, and the counterexample
   costs two allowed actions. The correct rule is *union of permissions **and** intersection
   of limits*. [§8.4](#84-composite-partial-failure)
3. **Approving a first-time payment and enrolling a payee must be two decisions.** If one
   owner approval also enrols the address, a one-shot has silently become standing authority
   for every payment-capable agent. No report asks the question.
   [§7](#7-payments-where-pay-now-ends)
4. **The defensive permission is unsafe as all four specify it.** Selector allowlists do not
   constrain `receiver` or `onBehalfOf`; withdrawing collateral is not defensive. The
   invariant has to be a wallet-computed risk metric plus argument binding.
   [§8.3](#83-the-defensive-permission-leaks-at-the-parameter-not-the-selector)
5. **The fail-open default is not hypothetical, it is live.** `Sentinel.vy:201-202` returns
   `True` for any unmatched action type. Two lines, highest value-to-cost item in the
   document. [§9.2](#92-the-fail-open-fallback)

---

## 1. The four reports, and how much to trust each

| | codex | gemini | grok | claude |
|---|---|---|---|---|
| Length | ~12,850 w | ~10,190 w | ~10,340 w | **~1,210 w** |
| Completeness | full 17 sections | full 17 sections | full 17 sections | **exec summary only** |
| Web research | yes | yes | **no** | yes |
| Permission count | 15 (12/2/1) | 12 | 14 (11/2/1) | ~14 (8/4/2) |
| Two-gate verdict | KEEP_BOTH | **PERMISSION_ONLY** | KEEP_BOTH | KEEP_BOTH |
| Fixed taxonomy sufficient | conditional | yes | yes | conditional |
| Expression layer | bounded | none | none | bounded |
| Cheap micropayment lane | yes (bounded grammar) | yes (**bypasses the wallet**) | yes (dust threshold) | **no** |
| Self-declared confidence | medium | high | high | medium |

**codex** is the strongest report. It is the only one that mechanizes its own
recommendation into a bounded grammar of thirteen named execution primitives, the only one
that reasons carefully about composite partial failure, and the only one whose section 15
disagreement is a real disagreement rather than a restated tradeoff. Its weakness is that
its central claim — that the wallet independently re-derives what the extender declared —
is asserted rather than specified, and its gas figures are invented.

**grok** is the most internally disciplined. Its ranked split/merge procedure is actually
run, its fail-closed enumeration is the most complete, and its "extender declaration may
only further restrict, never enlarge" is the crispest single formulation of the extender
trust boundary in the corpus. It did no web research and says so. Its notable original
contribution is splitting payments to *approved* recipients from payments to *arbitrary*
recipients as two permissions rather than one permission plus a list.

**gemini** is the most confident and the least reliable. It is the sole dissenter on the
two-gate question, and its argument for collapsing the gates is an *availability* argument
(a registry upgrade changes the `actionId` and the agent breaks until the owner updates the
allowlist) escalated into a *security* claim. It never engages the actual counterargument.
Its recommended micropayment fast path routes sub-dollar payments through an EIP-3009
signature "bypassing the wallet's heavy on-chain caveat evaluation entirely" — which voids
the entire policy engine for exactly the transaction class its own Scenario 2 shows being
manipulated. Several citations do not survive inspection. **It also contains the two best
individual observations in the corpus** — see [§8](#8-the-hard-problems-answered-honestly).
Read it for the specific findings; do not adopt its architecture.

**claude** never produced its deliverable. Its tooling failed and it emitted a compressed
executive summary with `SECTIONS_SHORTENED_OR_OMITTED: 1,2,...,17`. What survives is
conclusions without derivations. Its conclusions happen to agree with the majority on every
structural question, which is mild corroboration and nothing more. Its one distinctive
position — refuse to fork a cheap validation path, because a cheap lane is a downgrade
attack surface — is, I think, correct, and I adopt it for a different and better reason
than the one it gives.

> A note on reading agreement. Four models agreeing is weaker evidence than it feels,
> because they share training data and read the same prompt. Where I rely on agreement
> below, I have tried to state the falsifier alongside it.

---

## 2. The convergent core

These survived all four reports **and** my own scrutiny. Each is stated with the one thing
that would falsify it.

### 2.1 Open actions, closed authority

New action identities and reviewed implementations may be registered freely. New *kinds*
of wallet authority may not. Registration selects from an existing vocabulary; it cannot
define what a permission means.

*Falsifier:* if a materially important new action class repeatedly cannot be expressed as a
union of existing permissions without either over-granting or forcing everything owner-only.
codex offers the sharpest version of this test: **if the wallet needs more than one or two
new core permissions per year to support mainstream treasury workflows, the split rule was
wrong.**

### 2.2 The persistence test is the primary boundary — but state it carefully

All four reports reach the same boundary and three of them state it in a form that has a
hole. The common formulation is: an action is "pay now" if and only if no counterparty holds
any surviving right **when the transaction ends**.

That is mechanical and checkable, and it cuts across payment mechanism exactly as intended:
a direct transfer, an approved-payee payment, a merchant payment and a payroll batch are all
the same authority; a cheque, a pull right, a reservation, a recurring schedule and a stream
are all a different authority.

**The hole is signature-emitting payments.** For an action whose output is a signed
authorization rather than an on-chain effect, there is no transaction, so an
end-of-transaction test silently returns "no surviving claim" for what is in fact a bearer
instrument. Three reports classify x402 machine payments as pay-now with no persistent
effect; that is right for the variant where the wallet settles on-chain and wrong for the
variant where an agent signs an EIP-3009 authorization that a facilitator redeems later.

**Use this formulation instead:**

> An action is **pay now** if and only if, at the end of the **authorization event**, no
> counterparty holds anything the wallet cannot **unilaterally extinguish**.

That version classifies both x402 variants correctly, and it also explains why an in-flight
bridge message is not pay-now even though nobody holds a claim against the wallet — the
wallet cannot extinguish it.

*Falsifier:* an authority the wallet can unilaterally extinguish that is nonetheless as
dangerous as one it cannot. None found.

### 2.3 Defensive authority must be separately delegable

Repaying debt, adding collateral to an existing position, withdrawing to the wallet,
closing a position, and revoking an outstanding claim are authority that **only reduces
exposure**. All four reports independently carved this out, under four different names.

The argument that persuades me is codex's, and it is not the obvious one. It is not that
defensive actions are safe enough to delegate cheaply. It is that **the exit path must
survive the incident that disables the entry path.** A wallet frozen with open debt and no
route to repay it is a wallet that gets liquidated during its own incident response.

*Falsifier:* a "defensive" action that extracts value. These exist and are the reason this
permission needs parameter-level enforcement, not selector-level — see
[§8.3](#83-the-defensive-permission-leaks-at-the-parameter-not-the-selector).

### 2.4 Extenders declare; the wallet constrains

A reviewed extender may be buggy or hostile. It may propose a plan. It may never widen
authority. grok's formulation is the one to adopt verbatim: an extender declaration
**may only further restrict, never enlarge** the permission set registered for that
`actionId`. Monotone restriction is trivially checkable and removes the entire class of
"the extender lied about its own effects" attacks.

*Falsifier:* none found. This is the most robust conclusion in the corpus. Note that the
governing architecture already implements exactly this shape (`ActionSpec.requiredPermissionMask`
plus a committed `PreparedAction`), which is worth saying plainly: **on the single point
where all four reports are vaguest, this repo is already ahead of the research.**

### 2.5 Bit positions are permanent

New permissions take the next free bit. Deprecated permissions are retired and never
reused. Reordering is forbidden. The safety property is clean: adding a permission at an
unassigned bit is always safe because every existing grant has that bit at zero and
therefore fails closed. No agent silently acquires authority.

One refinement on the usual phrasing. "Bit meaning is fixed" is slightly too strong; the
right rule is **meaning may narrow, never widen.** Narrowing a bit retroactively removes
authority owners were granted, which is safe. Widening one silently enlarges every stored
grant, which is the catastrophe. The live candidate is already visible: if slashing-bearing
restaking is later excluded from `YIELD`, that is a narrowing and it is fine.

*Falsifier:* none. This is not really a research finding, it is a correctness requirement,
and all four state it because it is easy to get wrong.

### 2.6 Presets expand at grant time and never mutate

Owners may be offered role presets ("Payroll Agent", "Yield Rebalancer"). The wallet must
store only the **expanded** permission set, never a preset identifier. Redefining a preset
later must not change any grant already made. All four reports say this; gemini reaches it
through hash-binding, the others through presentation-only expansion — same effect.

The reason is precise: a wallet-enforced bundle whose definition can change is a hidden
catch-all permission with a friendly name, which is exactly the thing the taxonomy exists
to eliminate.

*Falsifier:* none. Adopt as stated.

### 2.7 Value-denominated limits are only as strong as the price feed

A limit denominated in USD is not a limit; it is a limit *multiplied by an oracle*. Missing,
zero, and stale prices must fail closed. gemini quantifies it best: a flash-loan crashing an
asset from $100 to $0.01 in-block turns a $5,000 per-transaction cap into a $10,000,000
loss — a 10,000× bypass with every rule satisfied.

The specific arithmetic footgun claude names is worth writing on the wall: a USD limit
evaluating a zero price yields zero value, and **zero value passes every check**. Fail
closed means "block or treat as maximum value", never "allow because it appears to be
worth nothing".

**With one exception all four get backwards: monotonicity-verified defensive actions must be
price-EXEMPT.** If the oracle degrades during a market crash — precisely when it will — and
`POSITION_EXIT` is value-limited, the wallet cannot repay debt at the exact moment repaying
debt is the only thing that matters. codex argues forcefully elsewhere that defensive paths
must survive an incident and never connects the two sections. An action whose postcondition
proves the wallet's risk did not worsen does not need a price to be safe.

*Falsifier:* none. See [§9.3](#93-the-price-gap-is-real-and-narrower-than-it-looks) for
what this actually means here, which is narrower than the reports assume but still real.

### 2.8 Attribution and enumeration are prerequisites for revocation

Every persistent authority — allowance, pull right, cheque, stream, reservation, signed
order, bridge message, debt position — must record the manager that created it, and the
owner must be able to enumerate all outstanding claims filtered by manager, type, or
counterparty. Without this, "eject the compromised agent" does not tell you what the agent
left behind.

codex draws the correct hard conclusion, and it is the most under-appreciated recommendation
in all four reports: **do not permit delegated authority the wallet cannot later list and
invalidate.** Where a protocol supports nonce invalidation or order cancellation, use it and
track it. Where it does not, the action is owner-only. This is a product constraint, not
just an architecture one — it means saying no to some integrations.

*Falsifier:* if the set of integrations you must support to have a viable product is mostly
composed of unenumerable authority forms. Then the constraint has to bend and the residual
risk has to be accepted explicitly rather than designed away.

---

## 3. The mental model: five questions in a fixed order

The most useful thing to take from this research is not a permission list. It is an
ordering. Almost every wallet permission bug in the wild is a system that asked these
questions in the wrong order, or forgot one.

| # | Question | Answered by | Fails closed when |
|---|---|---|---|
| 1 | **Is this code allowed to run at all?** | Action registry — `actionId` bound to a reviewed extender and codehash, delayed activation, monotonic lifecycle | unknown or unregistered `actionId`; codehash mismatch; state not `ENABLED` |
| 2 | **Is *this agent* allowed to invoke *this procedure*?** | Per-manager `actionId` allowlist + global ceiling | empty list means **no** routed actions, not all |
| 3 | **Does this agent hold the *kinds of power* this action needs?** | Permission mask, checked **cumulatively** over the union | any required bit unset; any unknown bit set |
| 4 | **Is this specific instance inside bounds?** | Limits engine — value, period, lifetime, count, cooldown, asset, lego, recipient, slippage, price sanity | missing/zero/stale price; recipient not allowed; limit exceeded |
| 5 | **What survives this transaction, and who owns it?** | Settlement mode + persistent-obligation ledger | unknown settlement mode; persistent effect created without the matching permission *and* without a registry declaration |

Question 5 is the one the industry keeps forgetting, and it is the one that determines
whether revocation is possible at all. A design that answers 1–4 perfectly and skips 5
produces a wallet that can block a bad action and cannot undo a good one that turned bad.

Two properties of this ordering matter:

- **Questions 2 and 3 are not redundant.** Gate 2 answers *"which reviewed procedures may
  this agent invoke?"* Gate 3 answers *"what kinds of power does this agent hold?"* See
  [§6.1](#61-why-both-gates--the-one-real-disagreement).
- **Question 4 must be cumulative, not first-match.** A composite requiring `YIELD | TRADE`
  must satisfy both. This is the specific failure mode that turns composition into privilege
  escalation.

---

## 4. Recommended taxonomy

**17 permissions: 11 INITIAL, 4 LATER, 2 RESERVED.**

### 4.0 The ranked split rule

All four reports offer a ranked rule and all four rank differently. Use this one:

| Rank | Criterion | Why here |
|---|---|---|
| 1 | **Persistence** — does a right survive the authorization event? | The only criterion that is a function of the action's typed effects alone |
| 2 | **Revocability class** — can the wallet unilaterally extinguish it, and at what cost? O(1) internal / O(n) external / irrevocable | Justifies splitting standing allowances from wallet-internal claims without appealing to mechanism |
| 3 | **Directionality** — can this only reduce exposure, or can it increase it? | The defensive split |
| 4 | **Owner delegability** | Tiebreak only, among effects equal on 1–3 |
| 5 | **Blast radius** | Decides default presets and default limits — **never** bit allocation |
| 6 | **Execution mechanics, routing, settlement plumbing** | Never a reason to split. Unanimous across all four reports |

**Persistence wins on conflict, and the reason is mechanical rather than a matter of taste.**
Blast radius is a function of the limit configuration, which is per-grant and owner-mutable;
owner delegability is a function of survey data that drifts. A compile-time-fixed,
append-only bitmask cannot have a rank-1 criterion that depends on mutable per-grant
configuration, or the same two authorities merge under one customer's limits and split under
another's. Rank 2 is not in any report and is what makes the allowance-versus-claim split
principled rather than mechanical.

The organizing rule is deliberate and differs slightly from every one of the four reports:
**keep this repo's existing family axis** (which subsystem and counterparty class) **and add
exactly one orthogonal directional split** (does this increase exposure or reduce it) **plus
one persistence split** (does value leave now, or does a claim survive).

The reports that reorganize entirely around direction (codex) or around risk class (grok's
Sketch B) are defensible in the abstract and expensive here — see
[§9](#9-what-this-means-for-the-code-that-exists). Fighting the existing `LegoPerms` layout
costs bytecode in contracts that do not have bytecode to spare.

### 4.1 Bit assignment

Permanent, append-only, meaning may narrow but never widen. Assigned in this order so that
the payment family, which will be extended first, sits together.

| Bit | ID | State | Bit | ID | State |
|---:|---|---|---:|---|---|
| 0 | `TRANSFER` | INITIAL | 9 | `POSITION_EXIT` | INITIAL |
| 1 | `PAY_NETWORK_FEES` | INITIAL | 10 | `REVOKE_CLAIMS` | INITIAL |
| 2 | `ENROLL_PAYEE` | INITIAL | 11 | `CROSS_CHAIN` | LATER |
| 3 | `PAYMENT_COMMITMENT` | INITIAL | 12 | `STANDING_ALLOWANCE` | LATER |
| 4 | `TRADE` | INITIAL | 13 | `OFFCHAIN_SIGNATURE` | LATER |
| 5 | `YIELD` | INITIAL | 14 | `GOVERNANCE` | LATER |
| 6 | `DEBT` | INITIAL | 15 | `SUB_DELEGATE` | RESERVED |
| 7 | `LIQUIDITY` | INITIAL | 16 | `MANAGER_ADMIN` | RESERVED |
| 8 | `REWARDS` | INITIAL | 17–255 | *unassigned* | — |

Bit permanence starts clean here, which is worth noting: today's authority is booleans in
nested structs rather than bits, and routed execution is new-generation-only, so nothing
needs remapping. This is the one moment where the assignment is free.

### 4.2 INITIAL — required for the initial system

```text
PERMISSION: TRANSFER
OWNER CONSENT: This agent may send money out of the wallet now, to recipients you
  have approved, within the limits you set.
PRECISE AUTHORITY: Immediate value transfer that leaves no surviving claim, allowance,
  signature, schedule or reservation once the transaction ends.
EXAMPLE ACTIONS: approved-payee payment, merchant payment, payroll batch, one-time
  x402-style machine payment, relayer or paymaster fee payment.
EXPLICIT EXCLUSIONS: any future claim; standing approvals; off-chain signatures;
  enrolling a new recipient; network/relayer/paymaster fees.
LIMITS: recipient allowlist, per-recipient per-tx / per-period / **lifetime** caps,
  per-tx / per-period / lifetime USD caps, asset allowlist, cooldowns.
MAPS TO TODAY: TransferPerms.canTransfer — unchanged.
ROLLOUT: INITIAL
```

```text
PERMISSION: PAY_NETWORK_FEES
OWNER CONSENT: This agent may pay the network, relayer and paymaster fees needed to
  carry out its other work.
PRECISE AUTHORITY: Fee payment to a builder, relayer or paymaster, capped as a
  proportion of the linked parent action.
EXPLICIT EXCLUSIONS: any payment not linked to a parent action; standalone value
  transfer.
LIMITS: fee-ratio cap relative to parent action value; mandatory parent-action linkage.
MAPS TO TODAY: NEW (folded into canTransfer today).
ROLLOUT: INITIAL
WHY SEPARATE: this is a 2-2 split across the reports where neither side engages the
  other, and the deciding argument is one neither side makes. A fee must go to a party
  that NO recipient allowlist can contain — a block builder, a relayer, a paymaster. If
  TRANSFER has to carry that carve-out, its own consent sentence ("recipients you have
  already approved") becomes false, and the natural exfiltration channel — overpaying a
  paymaster you control — now lives inside the most widely granted bit in the system.
```

```text
PERMISSION: ENROLL_PAYEE
OWNER CONSENT: This agent may add a new payment destination, which this and other agents
  may then pay.
PRECISE AUTHORITY: Creation of a probation-class recipient enrollment — attributed to the
  creating manager, expiring, carrying its own per-recipient lifetime cap and its own
  revocation handle.
EXPLICIT EXCLUSIONS: raising a probation cap; enrolling a contract as a spender; making
  the payment itself.
LIMITS: probation duration, probation lifetime cap, cooldown before a cap may rise, count
  of open probation enrollments.
MAPS TO TODAY: NEW (payee administration is owner-side today).
ROLLOUT: INITIAL
WHY SEPARATE: all four reports miss the leak this closes, and it is the sharpest single
  finding of the whole exercise. codex and gemini route first-time payments to
  owner-only; grok gives them a permission with tighter limits. None of them asks
  **whether approving a first payment also enrols the address.** If it does, one owner
  decision has created standing payability exercisable by every TRANSFER holder forever —
  a one-shot silently converting into persistent authority, which is exactly the boundary
  the taxonomy exists to defend. And owner-only will be routed around in practice by
  pre-approving a wide recipient class, which is strictly worse than a bounded delegable
  form. The delegable object is **enrollment into probation**, not unrestricted payment.
```

```text
PERMISSION: PAYMENT_COMMITMENT
OWNER CONSENT: This agent may set up a payment that someone can claim from the wallet
  later.
PRECISE AUTHORITY: Creation of a bounded, revocable, expiring future claim on wallet
  funds — cheque, payee pull, reservation, recurring schedule, or stream — in favour
  of a specific payee.
EXAMPLE ACTIONS: issue a cheque; authorize a payee pull; create a bounded recurring
  payment; reserve value for later merchant capture.
EXPLICIT EXCLUSIONS: immediate payment; token allowances; off-chain signatures;
  any claim without an expiry.
LIMITS: allowed claim types, approved payees, maximum total outstanding exposure,
  expiry ceiling, frequency bounds, partial-capture rules, revocability rules.
MAPS TO TODAY: TransferPerms.canCreateCheque — generalized from cheques to any claim.
ROLLOUT: INITIAL
WHY SEPARATE: this is the boundary from §2.2, and it is the one boundary that is never
  crossed inside a single permission. A claim survives manager ejection; a payment
  does not.
```

```text
PERMISSION: TRADE
OWNER CONSENT: This agent may exchange one approved asset for another through approved
  venues, within your slippage limits, with proceeds returning to the wallet.
PRECISE AUTHORITY: Spot conversion of approved assets via approved Legos. No latent
  right except the resulting balance.
EXPLICIT EXCLUSIONS: sending proceeds to a third party; standing approvals; resting
  or off-chain orders that settle later; bridging.
LIMITS: lego allowlist, asset-pair allowlist, max slippage, swap count per period,
  per-trade and per-period caps, price sanity.
MAPS TO TODAY: LegoPerms.canBuyAndSell — unchanged.
ROLLOUT: INITIAL
```

```text
PERMISSION: YIELD
OWNER CONSENT: This agent may move approved assets from the wallet into approved yield
  opportunities.
PRECISE AUTHORITY: ENTRY ONLY — deposit into a reviewed yield/vault/lending-supply
  position that leaves the wallet holding a protocol position.
EXPLICIT EXCLUSIONS: withdrawal and exit (those are POSITION_EXIT); borrowing;
  leverage; slashing-bearing staking unless separately approved.
LIMITS: approved-opportunity gating (onlyApprovedYieldOpps), exposure caps per
  opportunity and overall, lock-up awareness.
MAPS TO TODAY: LegoPerms.canManageYield — narrowed to entry.
ROLLOUT: INITIAL
```

```text
PERMISSION: DEBT
OWNER CONSENT: This agent may borrow against the wallet's assets, which increases the
  wallet's financial risk.
PRECISE AUTHORITY: EXPOSURE-INCREASING ONLY — borrow, remove collateral, increase
  leverage.
EXPLICIT EXCLUSIONS: repaying debt and adding collateral (those are POSITION_EXIT);
  moving borrowed funds out of the wallet (that is TRANSFER).
LIMITS: LTV / health-factor floor, approved lending Legos, debt-asset caps.
MAPS TO TODAY: LegoPerms.canManageDebt — narrowed to the exposure-increasing half.
ROLLOUT: INITIAL
```

```text
PERMISSION: LIQUIDITY
OWNER CONSENT: This agent may provide the wallet's assets as liquidity in approved pools.
PRECISE AUTHORITY: ENTRY ONLY — add liquidity, including concentrated positions.
EXPLICIT EXCLUSIONS: removal (POSITION_EXIT); swaps (TRADE).
LIMITS: approved pools, exposure caps, range constraints for concentrated positions.
MAPS TO TODAY: LegoPerms.canManageLiq — narrowed to entry.
ROLLOUT: INITIAL
```

```text
PERMISSION: REWARDS
OWNER CONSENT: This agent may claim rewards and incentives the wallet has already earned.
PRECISE AUTHORITY: Claim accrued incentives to the wallet.
EXPLICIT EXCLUSIONS: restaking or redepositing the proceeds (that additionally needs
  YIELD); selling them (TRADE).
MAPS TO TODAY: LegoPerms.canClaimRewards — unchanged.
ROLLOUT: INITIAL
```

```text
PERMISSION: POSITION_EXIT
OWNER CONSENT: This agent may only bring money back to the wallet and reduce risk — it
  can close positions, withdraw, repay debt and top up collateral, but it can never send
  money out of the wallet or take on new risk.
PRECISE AUTHORITY: Strictly exposure-reducing operations across every family —
  withdraw from yield, remove liquidity, repay debt, add collateral to a position the
  wallet ALREADY HOLDS, close a position.
  ALL PROCEEDS MUST SETTLE TO THE WALLET.
EXPLICIT EXCLUSIONS: any transfer to a third party; opening any new position; seeding
  collateral for a position that does not yet exist; REMOVING collateral; any new
  obligation.
LIMITS: must reference an existing wallet position; destination parameter checked to be
  the wallet; slippage bounds on any conversion leg; health-factor must not decrease.
MAPS TO TODAY: NEW — carved out of canManageYield / canManageDebt / canManageLiq.
ROLLOUT: INITIAL — conditional on the four enforcements in §8.3 shipping with it
WHY SEPARATE: all four reports derived this independently. It is what lets most agents in
  a fleet be structurally incapable of losing money, and what keeps the wallet able to
  unwind during an incident that has disabled entry.
```

> **Removing collateral is not defensive**, and two of the four reports get this wrong by
> listing `withdraw` among the defensive operations. Withdrawing collateral from a lending
> position *lowers* the health factor. An agent holding only a defensive permission that
> included it could walk a position to the liquidation threshold having invoked nothing but
> allowed operations. Removing collateral belongs with `DEBT`, which is where this taxonomy
> puts it.

```text
PERMISSION: REVOKE_CLAIMS
OWNER CONSENT: This agent may cancel payment rights, allowances and orders the wallet
  previously created. It can never create one.
PRECISE AUTHORITY: Revocation, cancellation, reduction, expiry-shortening or
  spend-to-zero of wallet-tracked persistent obligations and approvals.
EXAMPLE ACTIONS: cancel a stream; revoke a pull right; void an unredeemed cheque;
  release an unspent reservation; reduce or zero an allowance; invalidate a signed order
  where the protocol supports it.
EXPLICIT EXCLUSIONS: creating or enlarging any right; recipient substitution; shortening
  expiry in a way that increases exposure; any administrative change.
LIMITS: object-type allowlist; by default only objects created by the same manager or an
  approved creator class (anti-griefing); owner may always cancel.
MAPS TO TODAY: NEW.
ROLLOUT: INITIAL
WHY SEPARATE: codex alone proposed this and it is right. Revocation is intrinsically
  defensive and must stay routable when creation authority has been withdrawn — that is
  the whole point of a kill-switch. Folding it into the permission that created the
  obligation (grok, gemini) means the only agent that can cancel a runaway stream is one
  that can also create streams, which is precisely the agent you have just stopped
  trusting. It also lets an owner run a recovery agent that holds this bit and nothing
  else.
```

Four INITIAL bits are new: `POSITION_EXIT`, `REVOKE_CLAIMS`, `PAY_NETWORK_FEES` and
`ENROLL_PAYEE`. The other seven are existing booleans, renamed or narrowed.

> **A note on the count.** Reading the four reports first suggests 12–15 permissions.
> Working the split rule honestly through the leaks the reports themselves surface — the
> enrollment leak, the fee-recipient carve-out, the revocation kill-switch — lands at 17.
> That is *more* than any single report recommends and it is the right answer, because in
> this codebase (§9.1) the marginal cost of a bit under a mask is essentially zero, while
> the cost of a missing boundary is a permission whose consent sentence is false.

### 4.3 LATER — likely useful, not initially required

| Bit | ID | Why not now |
|---|---|---|
| 11 | `CROSS_CHAIN` | Bridge finality and liveness risk is its own class, and an in-flight message is authority the wallet cannot unilaterally extinguish. No routed bridge action exists yet. |
| 12 | `STANDING_ALLOWANCE` | An approval that survives the transaction. Today the wallet never leaves one standing — `_resetApproval` always runs — so the bit would gate nothing. Add it the day that changes, not before. |
| 13 | `OFFCHAIN_SIGNATURE` | EIP-1271, Permit2, gasless orders, marketplace listings, and the signature-emitting variant of x402. Do not ship until the nonce/epoch invalidation and on-chain-commitment story is built, per §2.8. |
| 14 | `GOVERNANCE` | Unanimous LATER across all four reports. Low extraction risk, genuinely separable, no urgency. |

**On unlimited allowances.** Three reports give `type(uint256).max` its own permission or
route it owner-only; codex keeps one permission on the persistence line. Codex has the
boundary right and the implementation wrong. Keep one permission — but do not therefore
treat unlimited as an ordinary limit value. `uint256.max` is **not a quantity, it is a
category change**: it removes the limits engine's ability to bound loss, and it breaks the
outstanding-exposure ledger, which can no longer sum. So: one permission, plus a hard wallet
invariant that no delegated grant may ever set an approval ceiling to `uint256.max`.
Unlimited approval is owner-only by invariant, not by permission bit.

### 4.4 RESERVED — named to keep the boundary reviewed, granting nothing

| Bit | ID | Meaning |
|---|---|---|
| 15 | `SUB_DELEGATE` | Unanimous RESERVED. Named so that sub-delegation can never appear as a "mode" of something else. |
| 16 | `MANAGER_ADMIN` | Tighten-only administration of *other* managers — suspend, eject, reduce limits. Never loosen, never self. Named so nobody smuggles administration into an operational bit. |

Reserving costs nothing and buys a real property: `STANDING_ALLOWANCE` existing as a named
RESERVED/LATER concept prevents an unlimited approval being smuggled in as a large
*parameter* of an ordinary one, and `SUB_DELEGATE` existing prevents delegation appearing as
an execution mode.

### 4.5 Deliberately *not* permissions

| Candidate | Who proposed it | Why I decline |
|---|---|---|
| Exact temporary allowance | gemini, grok, claude | It is an execution primitive the wallet already issues and reclaims (`_getAmountAndApprove` / `_resetApproval`). It has no independent existence to delegate, and making it delegable invites the mistake of granting it standing. codex agrees. |
| First-time / arbitrary recipient | grok (`PAYMENT_UNRESTRICTED_RECIPIENT`) | A real and well-argued boundary, but this repo already expresses it as configuration — `allowedPayees`, the whitelist, `PayeeLimits`. Keep it a limit. Do not spend a bit and a storage migration on something the engine already does. |
| Gas / relayer / paymaster fees | grok, claude | A payment to a fee recipient. Bound it with a fee-ratio cap under `TRANSFER`. |
| Wallet security configuration | gemini (as INITIAL and delegable) | Owner-only, never routable. Making this a delegable operational permission is the clearest single error in the corpus. |
| Settlement / accounting mode | the research prompt itself | An internal effect label, not an owner-facing grant. codex and claude both say so, and the governing architecture already treats it as a closed enum. Agreed — see [§10.1](#101-the-prompts-eight-concepts-are-not-eight-concepts). |

### 4.6 Named future candidates

Not reserved — reserving implies a completed review — but flagged so the split rule is
applied consistently when they arrive:

- **`STAKING` / restaking with slashing exposure.** Today this is `YIELD` plus a
  slashing-exposure limit. It earns its own bit when owners want to delegate ordinary yield
  entry while withholding slashing-risk entry, which they eventually will. codex reaches the
  same conclusion in its future-compatibility section.
- **`DERIVATIVES` (perps, options).** Continuous funding liability and contingent
  liquidation exposure are not expressible as `DEBT` plus limits. This is the strongest
  candidate for a genuinely new permission plus a new settlement behaviour.

Both were listed as candidates in the governing architecture's provisional vocabulary. This
synthesis agrees they are real and agrees they are not initial.

---

## 5. The grant model

**Owners grant individual permissions.** Presets exist in the interface, expand to a
concrete mask plus concrete `actionId`s plus concrete limits before the owner signs, and the
wallet stores only the expansion.

Requirements, all four reports agreeing:

- Presets are **defined and versioned by product governance**, not by managers.
- The owner **inspects the expanded set** before approving and may customize it.
- Changing a preset definition later **never** mutates an existing grant. Only an explicit
  owner re-grant does.
- The wallet checks **only expanded primitives**. There is no code path where a preset
  identifier is an input to an authorization decision.

This is what stops a convenience bundle from becoming a hidden catch-all. It is also what
makes the taxonomy scale to dozens of agents without pushing operators toward granting
everything: the operator interacts with four or five role names, and the wallet enforces
fourteen bits.

**The honest cost:** this does not remove the per-agent grant transaction. With dozens of
agents and a slow business multisig, each new action still requires the owner to extend
each relevant manager's `actionId` list. gemini is right that this is a real operational
cost. It is wrong that the cost justifies removing the gate — see next section.

---

## 6. Enforcement architecture

### 6.1 Why both gates — the one real disagreement

Three reports say keep both. gemini says collapse to permissions only. This is the single
substantive fork in the corpus, so it deserves a decision rather than a summary.

**gemini's argument:** the `actionId` allowlist is redundant with permissions-plus-caveats;
it causes breakage when a registry upgrade changes an `actionId`; it costs gas.

**Why it does not hold — three reasons, strongest first.**

*It does not actually remove a gate.* gemini's own recommended registry record binds
`actionId` to "a bitmask of maximum allowable permissions", and its Scenario 3 defense
against a malicious extender appending `approve(attacker, max)` depends entirely on that
ceiling. gemini has not collapsed two gates into one; it has moved one gate from per-manager
to system-wide. System-wide-only is **strictly weaker**, because it cannot express "agent A
may run this action, agent B may not" — which is the entire point of having a fleet of
narrow agents.

*Its breakage premise is not required by the design it criticizes.* The argument assumes a
router upgrade necessarily mints a new `actionId`. codex explicitly denies this: a new
implementation gets a new identity only when its effective authority surface, allowed
primitive set, or settlement behaviour materially changes. See
[§6.3](#63-identity-versus-implementation) — separating the two removes the objection
entirely.

*The gas point is trivial* — one extra storage read against gemini's own claimed
25,000–40,000 gas of overhead.

And it never answers the actual argument for the gate, which is a property rather than a
preference:

> **The `actionId` allowlist is what makes new-action registration fail closed.**
> Register a new `YIELD` action into an open-ended registry, and with permissions alone
> every manager already holding `YIELD` acquires it the instant it is enabled — silently,
> with no owner action. With the allowlist, the new action reaches nobody until an owner
> explicitly adds it.

That is not redundancy. It is the entire fail-closed property of an open-ended registry, and
it is the reason the design can afford to let the action set be open in the first place.
The two gates answer different questions and neither answer implies the other. The governing
architecture already requires all three of manager bits, explicit `actionId` approval, and
the global ceiling, with an empty list meaning "no routed actions". That decision was right.

**Where gemini's concern should be honoured instead:** the operational cost is real, and the
mitigation is the **global manager ceiling** the architecture already sketches. Approve an
`actionId` once at the ceiling; per-manager opt-in then becomes a cheap edit over a small
approved set rather than a fresh owner deliberation per agent. That preserves fail-closed
while making the common case affordable. The friction that remains is on *action
registration*, which is already a deliberate, delayed, reviewed event — there, the friction
is the feature.

### 6.2 The registry record

Merging the four proposals, with fields all of them agree on marked ✓:

| Field | Purpose | Consensus |
|---|---|---|
| `actionId` | Stable identity — **semantic**, not implementation | ✓ 4/4 |
| `extender` + `extenderCodehash` + `version` | Implementation binding | ✓ 4/4 |
| `requiredPermissionMask` | The permission requirement — **EXACT**, see below | ✓ 4/4 (semantics disputed) |
| `allowedCapabilityMask` | Ceiling on the execution primitives this action may use | codex, grok |
| `persistentEffect` (type + flag) | Whether this action may create a surviving claim, and of what type | ✓ 4/4 |
| `settlementMode` | From a small closed enum | codex, grok |
| `lifecycleState` | `PENDING → ENABLED → EXIT_ONLY → DISABLED`, monotonic, `DISABLED` terminal | governing arch |

**`requiredPermissionMask` must be EXACT, not a floor and not a ceiling.** All four reports
describe this field in one line and each means something different by it, which produces
three different contracts from the same sentence. This needs deciding before the registry is
written:

- **Ceiling-only** (gemini) is an under-enforcement bug. If the per-invocation derived
  requirement is a strict subset of the ceiling and the derivation misses an effect, the
  manager passes holding fewer bits than the action actually consumed. The mask silently
  grants rather than constrains.
- **Floor-only** (codex) over-grants: every invocation pays for the worst case, so an agent
  needs `TRADE` to run a rebalance that did not swap.
- **EXACT** collapses both failure modes. The action declares precisely what it requires;
  the manager must hold precisely that; anything the invocation would consume beyond it
  reverts.

The companion rule, which is grok's and is the crispest formulation in the corpus:

> The registry fixes the requirement at registration. The extender's declaration may
> **only further restrict, never enlarge** it. The wallet authorizes the intersection of
> what the manager holds, what the registry fixed, and what the extender declared.

This matters more than it looks, because it is the one place where the governing
architecture is honest about a limit the reports paper over: the wallet **cannot** generally
prove how a Lego used every pulled token inside an external protocol, nor infer an
undeclared output from opaque calldata. Declaration completeness remains pinned to reviewed-code
trust. A fixed mask plus narrowing-only declaration is safe under that admission; a
wallet-derived requirement is not, because deriving requirements from a plan you cannot fully
verify is a trust claim wearing a verification costume.

`EXIT_ONLY` as a lifecycle state deserves emphasis. It is the mechanism that makes §2.3
operational: an action family can be disabled for entry while remaining available for
unwind. This is in the governing architecture already and none of the four reports proposed
anything as clean.

### 6.3 Identity versus implementation

All four reports bind `actionId` to a codehash, so that any code change is an identity
change, so that every manager must be re-granted. That is what makes gemini's operational
objection bite, and the fix is to split the two:

- The registry entry keyed by `actionId` carries the **reviewed semantics** — permission
  requirement, allowed-capability mask, persistence and settlement flags.
- It separately carries a **versioned implementation binding** — extender address and
  codehash.

A version bump that leaves every semantic field **bit-identical** is a version bump: the
manager keeps its grant, and governance still reviews the code under the existing delayed
process. A change to any semantic field is a **new `actionId`**, and every manager must be
re-granted, because the thing the owner approved has changed.

This preserves the fail-closed property exactly where it matters, and removes the
re-granting churn exactly where it does not. It is a better answer than any of the four
reports gives, and it dissolves gemini's dissent rather than merely rebutting it.

### 6.4 Fail-closed rules

Every one of these must revert, not default:

| Condition | Required behaviour |
|---|---|
| Unknown or unregistered `actionId` | revert |
| `actionId` not on the manager's allowlist | revert |
| Manager `actionId` list empty | **no routed actions** — never "all" |
| Extender codehash mismatch | revert |
| Lifecycle state not `ENABLED` (or not `EXIT_ONLY` for an exit action) | revert |
| Any required permission bit unset | revert |
| Any **unknown** permission bit set in the requirement | revert |
| Unknown settlement mode | revert |
| Persistent effect created without both the permission **and** the registry declaration | revert |
| Missing, zero, or stale price on a value-governed action | revert |
| Extender declaration attempting to **enlarge** the registered set | revert |
| Unrecognized action type on the direct path | **revert** — see [§9.2](#92-the-fail-open-fallback) |

### 6.5 One validation lane, not two

Three of four reports recommend a cheap path for micropayments. I recommend against it, and
the reason available here is stronger than the reason claude gave.

The reports argued this on **gas**: full validation costs tens of thousands of gas, which is
uneconomic for a sub-dollar payment. gemini therefore proposes routing micropayments through
an EIP-3009 signature that bypasses the policy engine entirely — which means the wallet's
limits, recipient allowlists and permission mask do not apply to the exact transaction class
its own Scenario 2 demonstrates being manipulated. That is not an optimization, it is a hole.
codex's version is much safer (a cheap lane bounded by a hard grammar: no persistence, no
external protocol call, no signature emission) and it names the right risk — classification
pressure, teams pushing more actions into the cheap lane over time.

But in this codebase the argument changes shape. **The binding constraint is not gas, it is
bytecode.** A second validation lane is a second code path in `Sentinel` and a second set of
entry points, spent from contracts that have 867 and 1,544 bytes of headroom. A cheap lane
costs the scarcest resource in the system to save the one that is least scarce, and it adds
a downgrade-attack surface for free. One lane.

If micropayment economics later prove genuinely blocking, the right answer is not a second
policy path but **aggregation** — settle many machine payments against one bounded claim
created once under `PAYMENT_COMMITMENT` — which stays inside the taxonomy and inside one
validation path.

---

## 7. Payments: where "pay now" ends

Applying the persistence test from §2.2 mechanically:

| Flow | Permission | Persistent effect |
|---|---|---|
| Direct / approved-payee payment | `TRANSFER` | none |
| Merchant payment | `TRANSFER` | none |
| Payroll / batch disbursement | `TRANSFER` | none |
| Invoice payment | `TRANSFER` | none |
| Gas / relayer / paymaster fee | `PAY_NETWORK_FEES` | none |
| x402 machine payment, **wallet settles on-chain** | `TRANSFER` | none |
| x402 machine payment, **agent signs an EIP-3009 authorization** | `OFFCHAIN_SIGNATURE` (LATER) | **a bearer instrument** until redeemed or expired |
| Cheque issuance | `PAYMENT_COMMITMENT` | recipient-specific claim until expiry |
| Payee pull authorization | `PAYMENT_COMMITMENT` | revocable pull right |
| Reservation for later capture | `PAYMENT_COMMITMENT` | encumbered value until expiry |
| Recurring payment / subscription | `PAYMENT_COMMITMENT` | bounded schedule |
| Stream | `PAYMENT_COMMITMENT` | accruing obligation |
| Cancel / revoke an outstanding claim | `REVOKE_CLAIMS` | removes one |
| Refund **received** | none | none — see below |

The two x402 rows are the practical payoff of restating the persistence test in §2.2. Three
of the four reports collapse them into one row and classify both as pay-now with no
persistent effect. They are not the same authority, and treating them as one means the
signature variant ships under the permission with the loosest limits and no revocation
story at all.

**A note on first-time recipients.** codex and gemini make paying a never-seen address
owner-only; grok gives it a separate delegable permission with tighter limits. grok is right
that a delegable form must exist — but all four miss the actual leak, which is worth stating
because it is subtle and expensive: **none of them says whether owner approval of a
first-time payment also enrols that address in the allowlist.** If it does, a one-time owner
decision has created standing authority exercisable by every `TRANSFER` holder forever. A
pay-now action has quietly become persistent authority — exactly the boundary the whole
taxonomy is built on. Approval of a payment and enrolment of a payee must be two separate
owner decisions, which is what `ENROLL_PAYEE` (§4.2) exists to make explicit.

Three further findings worth pulling out:

**Refunds require no authority at all.** gemini's smallest observation and one of its
best: refunds route back to wallet custody and consume zero manager permission. The wallet
must never require a permission to be made whole. It follows that inbound value needs no
gate — and that any design where receiving requires authorization has a bug.

**What ejection does to outstanding authority — two axes, not one.** All four reports treat
this as a single question and get a single answer, and each answer is half right. Two
distinctions actually matter:

*Axis 1 — reliance obligation or unilateral capability?* A cheque, a payee pull, a merchant
reservation and a contractor stream are **reliance obligations**: a counterparty has adjusted
its behaviour on the strength of the claim. The liability does not vanish because the agent
that created it was ejected, and auto-cancelling would be a griefing weapon against honest
payees — halt payroll by getting an agent ejected. An ERC-20 allowance and an unfilled
off-chain order are **unilateral capabilities**: nobody has relied on them, and nobody is
harmed by their removal. gemini's Scenario 5 is the concrete case — minutes before
revocation the agent grants a large approval to a dormant attacker contract, the owner
ejects, and three days later the attacker calls `transferFrom`.

*Axis 2 — routine ejection or ejection for cause?* This is the distinction none of the four
draws, and it is the one that decides the hard case. Run gemini's Scenario 5 again with a
payee pull instead of an `approve()` and gemini's rules preserve the attack: the pull is a
"reliance obligation", so it survives, and the attacker collects. Object class alone is not
sufficient when the reason for ejection is suspected compromise.

**The rule:**

| | Routine ejection (expiry, rotation, offboarding) | Ejection for cause (suspected compromise) |
|---|---|---|
| Unilateral capabilities (allowances, unfilled orders) | swept | swept |
| Reliance obligations (cheques, pulls, reservations, streams) | survive under their own terms; owner may cancel | **frozen pending owner review**, not destroyed |

Freezing rather than cancelling on the for-cause path preserves the honest payee's claim
while denying the attacker the window, and it puts the decision where it belongs — with the
owner, who can release each obligation after checking it.

> One caveat on the sweep, which gemini misses: iterating an unbounded
> `active_allowances_by_manager` list and zeroing each entry is a per-entry storage write
> plus an external call. A manager anticipating investigation can create thousands of dust
> allowances so the ejection routine runs out of gas. **The sweep must be bounded and
> resumable, or ejection itself becomes the denial-of-service.** Ejection must also
> succeed unconditionally even when the sweep has not finished — stopping the key must
> never depend on finishing the cleanup.

---

## 8. The hard problems, answered honestly

### 8.1 The manipulated but uncompromised agent

This is the threat the whole corpus agrees it cannot solve, and the agreement is worth
taking seriously rather than reading past. No key is stolen. No limit is exceeded. Every
action is individually plausible and individually permitted. A malicious invoice, a poisoned
feed, or a crafted retrieval result induces a real agent to exercise real authority.

What the taxonomy **does** constrain: magnitude (value limits), destination (recipient
allowlists), duration (expiry ceilings on claims), and *category* — an agent without
`PAYMENT_COMMITMENT` cannot be talked into creating a stream no matter how convincing the
document, and an agent without `OFFCHAIN_SIGNATURE` cannot be talked into signing an order
that fills later.

What it does **not** constrain: whether an otherwise-permitted payment was a good idea.
That is not a limitation of this design, it is a limitation of authorization systems
generally.

Three structural defenses actually work, and only these three, because off-chain monitoring
is excluded by assumption:

1. **Destination constraint.** Manipulation almost always needs value to reach an
   attacker-controlled address. Narrow recipient allowlists plus **per-recipient lifetime
   caps that never reset** are the highest-leverage control available. Per-period caps alone
   only bound the rate; lifetime caps bound the loss.
2. **Reduce the number of agents holding extractive authority at all.** This is the
   under-stated payoff of `POSITION_EXIT` and it reframes the defensive split from elegance
   into economics. If most of a fleet holds only exit/reduce/claim/vote-class permissions,
   manipulating those agents cannot lose money. The taxonomy's contribution to this threat
   is not that it constrains a manipulated agent — it is that it lets most agents be
   structurally un-manipulable-for-profit.
3. **Dual control on the actions that matter.** Input manipulation is a *single-agent*
   failure. The only structural on-chain defense is to require a second, independently-sourced
   principal for the decisions that matter — adding a payee, raising a limit, paying a
   first-time recipient, exceeding a threshold. The attacker must then manipulate two agents
   whose inputs do not share a source. The research prompt notes dual control is "practical
   rather than exotic" for business users; this threat model is the reason it should be
   treated as a primary control rather than a compliance nicety.

**Residual risk after all three: material and permanent.** An agent with `TRANSFER` to
approved vendors, manipulated by a plausible invoice, will pay an approved vendor. Loss is
bounded by the configured envelope, not by the agent's judgment. Recovery is forward-looking
only.

### 8.2 The fully compliant compromised manager

The same ceiling from a different direction. codex's version is the sharpest: an
accounts-payable agent with a $7,500 per-transaction cap, $40,000 daily, $250,000 lifetime,
paying an already-approved cloud vendor whose address the attacker now controls. Payments of
$1,900, $2,300, $3,100 across days. Every action compliant. **Maximum loss is the lifetime
cap — $250,000 — with no rule broken.**

The honest statement is that limits are the only thing bounding this, so limits set for
operational convenience are the actual security boundary, not the taxonomy. The named
mitigations are per-recipient lifetime caps, tighter merchant classes, spend-purpose
sublimits, and an owner-flow (not agent-flow) for adding or expanding a payee class.

### 8.3 The defensive permission leaks at the parameter, not the selector

This is the permission all four reports agree on and none of them makes safe. The
recommended enforcement is a selector allowlist — restrict calls to `repay()`,
`addCollateral()`, `withdraw()`. That is not sufficient, in four distinct ways:

1. **The destination is a parameter, not a selector.** ERC-4626's signature is
   `withdraw(assets, receiver, owner)`, and Aave-style `repay` takes `onBehalfOf`. Both pass
   a selector allowlist and both pay a third party. This is gemini's own best observation
   and it invalidates gemini's own proposal.
2. **Removing collateral is not defensive.** It lowers the health factor. Two reports list
   it among defensive operations; an agent holding only that permission could walk a
   position to the liquidation threshold using nothing but allowed calls. It belongs in
   `DEBT`.
3. **Value destruction is invisible to monotonicity checks.** codex identifies this and no
   one resolves it: an agent can repay debt by selling collateral into a thin or manipulated
   pool. Debt goes down, the destination is the wallet, every stated invariant holds, and
   value is gone.
4. **Repeated "defensive" churn is a griefing vector.** Nothing in the invariants bounds how
   often an agent may unwind and re-enter, and each cycle pays spread and fees.

And the sharpest instance of (1), which no report catches: Aave-style
`repay(asset, amount, rateMode, onBehalfOf)` lets an agent **repay a third party's debt with
wallet funds**. The wallet's own debt principal is unchanged, the destination is a lending
pool rather than an attacker address, and every monotonicity invariant any report proposes
is satisfied. Value simply leaves.

**The correct invariant is none of the three the reports propose.** Not a selector allowlist
(gemini), not a debt-principal comparison (codex), not "total exposure metrics" (grok), but:

> a **non-worsening, wallet-computed risk metric** measured before and after the whole
> action, **plus argument-level binding** (`onBehalfOf == wallet`, `receiver == wallet`,
> `beneficiary == wallet`), **plus a bound on value destroyed** on any conversion leg.

That costs one extra protocol read and one comparison, it is adapter-agnostic, and it is the
only formulation that survives a hostile adapter. **So `POSITION_EXIT` is INITIAL conditional
on those three enforcements plus a cooldown on exit frequency**, and it should not ship
without them.

This is the concrete form of "the wallet is the final arbiter", and it is the one place in
the whole design where that principle has to be an actual parameter check rather than a
design intention.

### 8.4 Composite partial failure

The consensus rule — a composite may never create privilege greater than the union of its
component permissions — is asserted by all four reports and argued by none. **It is also
false, and the counterexample is cheap.**

> An agent holds `TRADE` (venue-allowlisted, proceeds must return to the wallet — so it
> looks non-extractive) and `TRANSFER` (USDC only, $10k/day, approved vendor). It swaps
> 100 WETH to USDC: fully compliant, proceeds land in the wallet. It then pays the vendor
> in USDC: fully compliant. **The WETH asset restriction never binds, because WETH never
> leaves as WETH.** The union of the two permissions is described as "swap within
> approved venues" plus "pay approved vendors in USDC". The effective authority is
> *drain any swappable asset in the treasury, at $10k/day*.

The union rule holds for *permissions* and fails for *limits*. Asset allowlists,
counterparty restrictions and value caps are attached to the leg where they were written,
and a composite re-routes value around them. codex names swap-as-laundering when discussing
`SWAP_ASSETS` and never returns to it in its composites section; the other three do not
raise it.

**The correct rule is: union of permissions AND intersection of limits.** Concretely:

- asset allowlists bind the **inputs of every leg**, not just the terminal output;
- the value counter charges the **maximum notional touched at any leg**, not the net;
- a composite consumes every constituent permission's counters and cooldowns.

The second reason the consensus rule is insufficient: **intermediate states belong to
neither permission.** A composite whose legs cannot be atomic leaves the wallet in a state
no single permission contemplates.

The workable rules:

1. Same-chain composites are **atomic or they are separate actions**. There is no third
   option. The EVM gives atomicity for free on a single chain; the only way to get partial
   completion is for an adapter to swallow a revert in a `try`/`catch`, which is precisely
   the mechanism that lets a hostile adapter externalize intermediate state. **An adapter
   that catches a revert to continue a composite is the bug**, not a design choice — and it
   is worth an explicit invariant test rather than a convention.
2. Non-atomic legs — bridging above all — are **never hidden inside a single action**, even
   when the product markets them as one user intent. codex is right to refuse this.
3. Counters, cooldowns and limits advance **only on successful final commit**, and only for
   effects that actually occurred.
4. Temporary capabilities are issued immediately before use and cleared regardless of
   outcome.
5. Where partial completion is genuinely unavoidable, the wallet records an intermediate
   state object and permits **only defensive follow-up actions** until it resolves.

### 8.5 Enumerating outstanding authority

No report has a complete answer and one should not be claimed. There are three classes with
three different costs, and separating them is what makes the problem tractable:

**Class 1 — wallet-internal objects** (cheques, pulls, reservations, streams, payee
enrollments). These are **O(1) revocable by bumping a per-manager epoch**, because the
wallet is itself the enforcer: every object records the epoch it was created under, and
validity is checked against the manager's current epoch. One storage write invalidates
everything one manager ever created, with zero effect on the other twenty-nine agents. No
report proposes this and it is mechanically available today.

**Class 2 — external on-chain rights** (ERC-20 allowances, Permit2 `AllowanceTransfer`).
These are genuinely O(n) and gemini is right that a sweep is required. But its mechanism is
unshippable: an unbounded loop inside the ejection transaction exceeds block gas, and if a
failed sweep means a failed ejection, then an attacker with allowance authority spams dust
allowances and achieves **denial of ejection**. The fix is to decouple them —
**ejection is O(1) and always succeeds**, and the sweep is exposed separately as a
**paginated, permissionless** "revoke the next N allowances created by manager X" that any
keeper may call. Stopping the key must never depend on finishing the cleanup.

**Class 3 — off-chain and cross-chain commitments.** The residual. codex's admission-control
doctrine is the only position that does not enforce policy over a knowingly incomplete set:
**do not permit delegated authority the wallet cannot later list and invalidate** —
registered schema, typed, expiry-bounded, epoch-revocable, ledgered at creation. Where a
protocol cannot support that, the action is owner-only or the integration is declined.

Combining classes 1 and 3 gives an answer codex has all the parts of and never assembles:
**namespace ERC-1271 validation by manager epoch.** gemini's blunt global nonce rotation —
which destroys every legitimate in-flight order from every agent — becomes surgical. This is
complete for signatures the wallet validates. **It is not complete for signatures a third
party validates without reading wallet state, and there is no answer at all for in-flight
bridge messages.** That is why both `OFFCHAIN_SIGNATURE` and `CROSS_CHAIN` are `LATER`.

> **One hole nobody catches.** Every report says counters advance only on successful commit,
> which is right for on-chain execution. For a *signature-emitted* payment there is no
> commit — so budget would be consumed at settlement, and a manipulated agent can sign N
> authorizations against a single period cap and let the attacker settle all N. **Budget
> must be encumbered at issuance and released on expiry**, not charged at settlement.

### 8.6 The most dangerous combination

Three of four reports independently name the same pair — persistent-claim creation together
with off-chain signing (`PAYMENT_COMMITMENT` + `OFFCHAIN_SIGNATURE` in this taxonomy) — and
gemini gives the reason that makes it more than an additive-risk observation:

> The danger is not additive authority. It is **invisibility**. Neither permission alone
> produces a claim that is both delayed and unobservable; together they do.

Both are `LATER` here. Neither should reach the same manager without dual control.

---

## 9. What this means for the code that exists

This is the section the four reports could not write. Everything below was verified directly
against the repository at `fdb3bad`.

### 9.1 Permissions are booleans, and that is the expensive part

Today authority is five booleans in
[`LegoPerms`](../../interfaces/WalletConfigStructs.vyi) (`canManageYield`, `canBuyAndSell`,
`canManageDebt`, `canManageLiq`, `canClaimRewards`), two in `TransferPerms` (`canTransfer`,
`canCreateCheque`), three in `WhitelistPerms`, plus `canClaimLoot`, `onlyApprovedYieldOpps`
and `canOwnerManage`. There is no mask. The only bitmask in the system is `ActionType`,
which identifies the *action*, not the authority.

All four reports recommend a bitmask and all four justify it on gas — one storage read
instead of several. That justification is weak; a few cold reads is not what makes or breaks
this design. **The real argument is bytecode and ABI churn**, and it is much stronger.

`ManagerSettings` — which contains `LegoPerms` — is referenced across eight production
files: 55 times in `HighCommand.vy`, 14 in `UserWalletConfig.vy`, 13 in `Migrator.vy`, 11 in
`ChequeBook.vy`, 7 in `Sentinel.vy`, 7 in the interface, 5 in `Kernel.vy`, 4 in
`ActionDataProvider.vy`.

Measured headroom against EIP-170:

| Contract | Runtime | Headroom |
|---|---:|---:|
| `HighCommand.vy` | 23,709 | **867** |
| `UserWallet.vy` | 23,032 | **1,544** |
| `UserWalletConfig.vy` | (creation 23,958) | **~618** |
| `Sentinel.vy` | 13,315 | 11,261 |

So today, adding one permission category means a new struct field, a storage and ABI change
rippling through eight files, new validation code in `HighCommand`, and a new branch in
`Sentinel` — in contracts with under 1 KB of headroom between them. With a `uint256` mask,
adding permission #9 costs **zero** layout change and **zero** ABI churn, and the check
stays `mask & required == required`.

**Width: use a full `uint256`.** codex and gemini say 256 bits; grok says 64 or 128 would
do. Use 256, on a repo-specific ground none of them could give: the only bitmask in this
system today is `ws.ActionType`, a Vyper `flag`, and Vyper flags are `uint256`-backed and
cap at 256 members. More decisively, a `uint128` field inside `ManagerSettings` occupies a
full storage slot anyway unless it is hand-packed against an adjacent field of matching
size — and `ManagerSettings` is five nested perm structs plus two `DynArray`s, with no
`uint128` neighbour to pair with. The narrower field saves nothing and forecloses future
room for no benefit.

**Where to put it — and it should not be a struct field.** Because `ManagerSettings` is what
ripples, do not add the mask to it. Store it as a **parallel `(wallet, manager) → uint256`
mapping in Config**, leaving `ManagerSettings` untouched and the four dependent ABIs
unchanged. And host the routed permission check in **`Sentinel`** (11,261 bytes free), not
`HighCommand` (867 bytes free) — `HighCommand` holds `addManager`, `updateManager`,
`setGlobalManagerSettings` and every `_validate*` helper, and it is the tightest unbudgeted
contract in the system. This is the highest-leverage repo-grounded implementation decision
in this document and no report could have reached it.

**Consequence for this synthesis:** the taxonomy's *representation* matters far more than
its *size*. All four reports spent their effort arguing about whether the right count is 12,
14 or 15. In this codebase that argument is nearly irrelevant and the representation
question — which none of them raised — is the highest-leverage decision available. The
governing architecture is right to insist that "no candidate becomes supported merely
because a spare bit exists in a conceptual mask"; the point here is that converting to a
mask is what *makes* the later bits cheap, and it should therefore happen before the
taxonomy is finalized rather than after.

### 9.2 The fail-open fallback

[`Sentinel.vy:188-202`](../../contracts/core/walletBackpack/Sentinel.vy) is the entire
action→permission mapping:

```text
if   _txAction in (TRANSFER | PAY_CHEQUE):                          return canTransfer
elif _txAction in (EARN_DEPOSIT | EARN_WITHDRAW | EARN_REBALANCE):  return canManageYield
elif _txAction in (SWAP | MINT_REDEEM | CONFIRM_MINT_REDEEM):       return canBuyAndSell
elif _txAction in (ADD_COLLATERAL | REMOVE_COLLATERAL | BORROW | REPAY_DEBT):
                                                                    return canManageDebt
elif _txAction in (ADD_LIQ | REMOVE_LIQ | ADD_LIQ_CONC | REMOVE_LIQ_CONC):
                                                                    return canManageLiq
elif _txAction == REWARDS:                                          return canClaimRewards
else:                                                               return True   # <-- open
```

Three observations:

1. **`else: return True` is fail-open.** Any action type not enumerated is permitted by
   default. The enumerated set is nearly complete today, so the live exposure is
   `ETH_TO_WETH` / `WETH_TO_ETH` — wrap and unwrap are currently permissionless for any
   active manager. That is defensible on its merits (codex independently argues
   self-custody transforms are materially safer than swaps and belong on the hot path), but
   it is reached by fallback rather than by decision. The governing architecture forbids
   carrying this into the routed path; it does not require fixing the direct path. It is a
   two-line change and it is worth making, because a fail-open default is the exact
   anti-pattern claude flags in its precedent review.
2. **`BORROW` and `REPAY_DEBT` share `canManageDebt`.** All four reports independently say
   exposure-increasing and exposure-reducing authority must split, and the implementation
   plan already splits the *code* — package 3A is "add collateral + repay", 3B is "borrow +
   remove collateral". The permission split is the missing half of a decision already made.
3. **The chain is `if/elif`, first-match-wins.** Correct today, because `_txAction` carries
   exactly one flag. It becomes a privilege-escalation bug the moment a routed composite
   passes a multi-bit mask: `EARN_REBALANCE | SWAP` would return on `canManageYield` and
   never test `canBuyAndSell`. The governing architecture calls this out; it is worth
   restating because it is the concrete local form of the "composition must not exceed the
   union" rule that all four reports assert abstractly.

### 9.3 The price gap is real, and narrower than it looks

The only price guard on the limits path is `_txUsdValue == 0 and failOnZeroPrice`, at three
scopes ([`Sentinel.vy:345`](../../contracts/core/walletBackpack/Sentinel.vy), `:525`, `:565`).
It is **zero-price only** and it is **opt-in**.

Staleness handling does exist, but not here: `SnapShotPriceConfig.staleTime` governs yield
vault price-per-share snapshots at the Lego layer, defaulting to one day
([`YieldLegoData.vy:422`](../../contracts/modules/YieldLegoData.vy)). That protects yield
accounting. It does not gate the USD valuation that enforces `maxUsdValuePerTx`.

So the accurate statement of the gap — narrower than the reports assume, and still real — is:
**there is no staleness gate on the valuation that gates manager limits, and the zero-price
gate that does exist can be configured off.** Given §2.7, `failOnZeroPrice` should not be a
per-manager option at all; it should be an invariant with no off switch, and it should grow
a maximum-age check.

### 9.4 The hardest primitive already exists

Worth stating plainly because it is good news that the reports could not know.
[`UserWallet.vy:1322`](../../contracts/core/userWallet/UserWallet.vy) `_getAmountAndApprove`
grants an approval clamped to `min(_amount, balanceOf(self))` — exact, never open-ended — and
`_resetApproval` at `:1334` zeroes it after the external call. The "exact temporary
capability, cleared atomically" primitive that all four reports call essential, and that is
hardest to retrofit, is already built and already used on the main paths.

One place to watch, and it is a note rather than a finding: `:313` and `:544` grant
`max_value(uint256)` for vault tokens that require it (the comment cites Compound v3), reset
immediately after. It is bounded by transaction atomicity and the reset on the success path,
and it is the only point in the wallet where an unbounded allowance exists even momentarily.
It is exactly the shape of gemini's Scenario 5 and codex's malicious-adapter scenario, and
it is worth an explicit invariant test rather than an assumption.

### 9.5 What the code already gets right

- `canCreateCheque` separate from `canTransfer` is the pay-now / create-future-claim split
  from §2.2, already shipped — for exactly one mechanism. Generalizing it to
  `PAYMENT_COMMITMENT` is a smaller change than it appears, because the boundary already
  exists and has a working precedent.
- `onlyApprovedYieldOpps` sits inside `LegoPerms` as a *modifier*, not a permission — which
  is precisely where all four reports say it belongs. Same for slippage in `SwapPerms` and
  the cheque caps in `ChequeSettings`. **claude's recommendation to redesign these
  action-specific controls into generic mode-scoped limits is the one majority
  recommendation I would decline**: they are already in the policy layer, they already work,
  and the redesign spends scarce bytecode to buy conceptual tidiness.
- `ChequeSettings` is the best template in the codebase for every future persistent-object
  schema — it already carries attribution, expiry, per-period create *and* pay caps,
  cooldowns, and a value-triggered delay (`expensiveDelayBlocks`). Model streams, pulls and
  reservations **on** it rather than dissolving it into generic subtypes.

One genuine defect among those controls, which no report could see. The approved-yield-opportunity
gate — `onlyApprovedYieldOpps` → `VaultRegistry.isApprovedVaultTokenForAsset` — lives in
`_checkManagerLimitsPostTx` at
[`Sentinel.vy:305-307`](../../contracts/core/walletBackpack/Sentinel.vy). **Entry authority
for a strategy is therefore validated after the deposit has already executed.** Same-chain
atomicity makes this safe today: the check reverts and the deposit unwinds. It stops being
safe for any action whose external effect a revert cannot undo — a lock-up, a bridge, a
message another system acts on — which is precisely the direction the routed action set is
heading. Entry authority belongs in the pre-action path.
- `PayeeLimits` already carries `perTxCap`, `perPeriodCap` **and** `lifetimeCap`. The
  per-recipient lifetime cap that §8.1 identifies as the single highest-leverage control
  against both the manipulated agent and the compliant compromise is **already implemented**.
  The recommendation is not to build it; it is to make it non-optional by default.

### 9.6 Two prerequisites that gate everything above

Neither is about permissions, and both must land before any of this matters.

**Codehash binding has nothing underneath it yet.** Every one of the four reports rests on
binding an `actionId` to a reviewed implementation by codehash. But `LegoBook` delegates to
[`AddressRegistry.vy:239`](../../contracts/modules/AddressRegistry.vy), which allows an
in-place `regId → newAddr` update after a timelock, with **no per-ID protection flag**;
`UndyHq` permits the same for the LegoBook slot. Until no-repoint protection exists, every
codehash-binding claim in all four reports is a social promise rather than an enforced
invariant. The governing architecture requires this (invariants S44/S49) and concedes it
needs new code.

**Lego caller identity.** Legos pull funds with `transferFrom(msg.sender, ...)`, and
`RipeLego` additionally asserts `msg.sender == _recipient` for collateral, borrow and repay.
A `wallet → extender → unmodified lego` call graph therefore cannot work at all. This is
already known and already has an owner disposition (session-aware Lego revision under new
LegoBook IDs, 2026-07-24). It is noted here because the permission model assumes a routed
path that does not yet exist.

---

## 10. Where I disagree

### 10.1 The prompt's eight concepts are not eight concepts

The research prompt asked all four models to separate action identity, permission, policy,
execution mode, settlement mode, temporary capability, persistent authority, and
administrative authority. Applying that decomposition to the answers:

- **Doing real work:** action identity, permission, policy/limit, persistent authority,
  administrative authority. These are genuinely independent and conflating any pair produces
  a known bug class.
- **Not a peer of the others:** *settlement/accounting mode*. codex and claude both reach
  this and they are right — it is an internal effect label used to derive checks and
  postconditions, not something an owner grants. If a finance operator has to understand
  "asset-only vs debt vs persistent-position accounting" to approve a grant, an
  implementation taxonomy has leaked onto the consent surface.
- **Not a peer, for a different reason:** *temporary capability*. It is not a category of
  authority at all; it is the mechanism by which an authorized action is executed safely.
  Three of four reports gave it a permission bit and this codebase shows why that is wrong —
  the wallet issues and reclaims it internally, and it has no independent existence to
  delegate. Elevating it invites the error of granting it standing.
- **Genuinely ambiguous:** *execution mode*. The prompt hoped a mode would never create a new
  category of authority. That boundary mostly holds, with one real exception the reports
  found: **batching**. An agent with `TRANSFER` and a $100 per-transaction cap that may batch
  a hundred $99 transfers has escaped its per-transaction limit through a mode. Modes must be
  constrained by aggregate limits, or batching becomes an authority.

So: six real concepts, not eight — and one of the six, *administrative authority*, is not a
permission at all but a different control plane, which is why it gets no operational bit in
§4.

**And one thing all four get wrong together, by omission.** Every report treats
sub-delegation as absent from the initial system because no agent can mint a manager, and
parks it on a RESERVED bit. But a payee pull hands transfer initiative to a party the wallet
does not control. A resting signed order is a bearer capability. A standing allowance to a
contract that has its own spenders is transitive delegation. **`PAYMENT_COMMITMENT`,
`ENROLL_PAYEE`, `STANDING_ALLOWANCE` and `OFFCHAIN_SIGNATURE` *are* the sub-delegation
permissions**, and naming them that way forces the questions that matter — depth,
attenuation, enumeration, revocation — onto four permissions that actually ship, instead of
deferring them to a reserved bit nobody implements.

### 10.2 Where all four are too convenient

**"A composite creates no privilege greater than the union of its permissions."** Every
report asserts this and none argues it. It is a necessary condition presented as a
sufficient one. It says nothing about pairs that are more dangerous together, and nothing
about intermediate states that belong to neither permission. Treat it as a floor.

**The gas figures are invented.** codex's "low tens of thousands", gemini's "25,000–40,000"
with only ~4,200 itemized and a "$0.10–$0.80" band citing no gas price, no token price and
no chain, grok's promise of order-of-magnitude analysis followed by no numbers at all. None
of these should inform a decision. The good news is that in this codebase they do not need
to, because the binding constraint is bytecode and that **is** measured — reproducibly, by
`tools/measure_wallet_v3_catalog_strip.py`.

**The load-bearing mechanism is the least specified part of every report.** All four rest on
the wallet independently constraining what the extender declared. codex gets closest with a
thirteen-primitive grammar; grok gets closest to a checkable rule with monotone restriction.
None of them specifies how a wallet verifies the *true effects* of an arbitrary registered
adapter. That this repo's governing architecture already commits to a concrete shape here —
committed `PreparedAction`, exact spend authority tied to the resolved amount, fixed
settlement modes — means the local design is ahead of the research on exactly the point
where the research is weakest. That is worth knowing before treating any of these reports as
more authoritative than the existing architecture.

### 10.3 Where I disagree with the majority

- **On the cheap validation lane** (3 of 4 in favour): no. §6.5.
- **On redesigning the existing semantic controls** (claude, echoed by codex): no. §9.5.
  They already live in the policy layer and already work.
- **On giving exact temporary allowances a permission bit** (3 of 4 in favour): no. §4.5.
- **On making `MANAGE_ALLOWANCE`-style authority INITIAL** (grok, gemini): no. The wallet
  currently leaves no standing approvals, so there is nothing for the bit to gate. Ship the
  bit when the behaviour exists.
- **On "composite privilege = union of permissions"** (4 of 4): no — it is false for limits,
  and cheaply so. §8.4. This is the one unanimous claim in the corpus that I think is simply
  wrong rather than merely under-argued.
- **On folding network fees into general payment** (codex, gemini): no. §4.2. A fee recipient
  is by construction un-allowlistable, so folding it in makes the consent sentence of the
  most widely granted permission false.
- **On routing first-time recipients to owner-only** (codex, gemini): no. §4.2. It is safer
  per decision and will be routed around by pre-approving a wide recipient class, which is
  strictly worse. The delegable object is bounded enrollment.

And two places where I side with a **minority of one**, which is worth flagging because a
1-of-4 vote deserves more scrutiny than a 4-of-4:

- **A standalone revocation permission** (codex alone). Folding revocation into the
  permission that created the obligation means the only agent able to cancel a runaway
  stream is one that can also create streams — precisely the agent you have just stopped
  trusting. §4.2.
- **Refusing the cheap validation lane** (claude alone). Right conclusion; here the
  decisive reason is bytecode rather than the downgrade surface claude names. §6.5.

---

## 11. Sequenced recommendation

Mapped onto the phases the implementation plan already defines. Nothing here authorizes
work; it is a proposed ordering within an already-approved sequence.

**Decide before any code is written** — these are expensive to change later:

1. **Representation: mask or booleans**, and **where the mask lives** — a parallel
   `(wallet, manager) → uint256` mapping in Config rather than a `ManagerSettings` field,
   with the routed check hosted in `Sentinel` not `HighCommand`. §9.1. This determines the
   cost of every subsequent permission and should be settled in Phase 0B alongside the size
   measurement, not deferred until the taxonomy is final.
2. **Bit assignment**, permanent, with the rule stated as *meaning may narrow, never widen*.
   §2.5.
3. **`requiredPermissionMask` is EXACT**, not a floor and not a ceiling. §6.2. Three readings
   of one field description produce three different contracts and one of them is an
   under-enforcement bug. Fix before `ActionRegistry` exists.
4. **`actionId` keyed on reviewed semantics, not codehash.** §6.3. A version bump that leaves
   the semantic fields bit-identical keeps every grant; any semantic change mints a new id.
   Check this against invariant S51 (a removed `EXIT_ONLY` id can never return to a manager)
   before committing — under set-difference grant semantics a mis-sequenced upgrade is not
   merely slow to repair, it is unrepairable for that manager.
5. **Which `persistenceType` values exist in v1.** Register types for objects the system can
   actually create — today that is `none / allowance / cheque / enrollment`. Adding
   `pull / stream / bridge / signature` before those objects exist is metadata that drifts.

**Cheap given what exists** (small, well-scoped, high value):

6. Close the fail-open fallback on the direct path. Two lines, in the contract with the most
   headroom. §9.2. **This is the highest value-to-cost item in the document** — and while it
   stands, a routed permission mask is bypassable through the direct path.
7. Move the approved-yield-opportunity gate from `_checkManagerLimitsPostTx` into the
   pre-action path. §9.5.
8. Make `failOnZeroPrice` non-optional and add a maximum-age check to the valuation used for
   limits — with defensive actions exempt. §2.7, §9.3.
9. Make per-recipient `lifetimeCap` non-optional by default. It is already implemented.
   §8.1, §9.5.
10. Add an invariant test that no allowance survives any wallet action, including on the
    `max_value` compatibility path, and that no adapter catches a revert internally. §8.4,
    §9.4.
11. Re-derive the `UserWalletConfig` blueprint baseline — the governing doc states 23,856
    creation bytes, measurement gives 23,958, and Phase 0A demands reproduction.

**Genuine new build**, in dependency order:

12. *The two prerequisites in §9.6* — no-repoint protection, and Lego caller identity.
    Without the first, every codehash-binding claim in this document is a social promise.
13. Permission mask storage; `ActionRegistry` and lifecycle; the two-stage Sentinel API;
    cumulative composite checking (`if`, never `elif`) with **intersection-of-limits**
    accounting on gross flow. §8.4.
14. Per-manager `actionId` allowlist plus the global ceiling, enforced at the Config storage
    boundary. §6.1.
15. Payments: `TRANSFER`, `PAY_NETWORK_FEES`, `ENROLL_PAYEE` with the probation class.
16. `POSITION_EXIT` with its risk-metric postcondition and argument binding (§8.3) —
    aligning with the plan's existing 3A-before-3B ordering; `REVOKE_CLAIMS` with
    anti-griefing scoping.
17. The persistent-obligation ledger with per-manager attribution **and manager epochs**;
    `PAYMENT_COMMITMENT` generalized from `canCreateCheque`; paginated permissionless
    allowance sweep with O(1) ejection. §7, §8.5.
18. `STANDING_ALLOWANCE` with the no-`uint256.max` invariant, then `OFFCHAIN_SIGNATURE` with
    schema registry, epoch-namespaced 1271 validation, domain-separator allowlist and
    issuance-time budget encumbrance. **Neither ships before item 17.**
19. `CROSS_CHAIN`, `GOVERNANCE`.

**And build a gas harness before accepting any cost argument.** The repo has
`tools/measure_wallet_v3_catalog_strip.py` for bytecode and nothing for gas. Three
architectural forks in the source reports rest on numbers nobody computed. §10.2.

---

## 12. Open decisions for the owner

These are product judgments, not security analysis. Each has a recommendation, but the call
is not mine.

| # | Decision | Options | Recommendation |
|---|---|---|---|
| 1 | Permission representation | keep booleans / convert to `uint256` mask | **Convert.** §9.1. It is the difference between future permissions costing an ABI migration and costing nothing. |
| 2 | Initial permission count | 8 / 11 / 13 / 15 | **11 INITIAL**, with 4 LATER and 2 RESERVED named but unshipped. Much less important than #1. |
| 2b | Registry permission-mask semantics | floor / ceiling / **exact** | **Exact.** §6.2. Must be settled before `ActionRegistry` is written — the three readings produce different contracts from the same one-line field description. |
| 2c | `actionId` bound to codehash? | yes / semantics and implementation split | **Split them.** §6.3. This is what makes the second gate affordable at fleet scale. |
| 3 | Where the `actionId` gate lives | per-manager only / global ceiling + per-manager | **Both.** The ceiling is what makes the per-manager step affordable at fleet scale. §6.1. |
| 4 | Dual-control **shape** | owner multisig (hours–days) / **two-manager co-signature with disjoint input channels** (~1 block) / none | **Build the second.** §8.1. Owner multisig is procedural in effect on any hot path, so on a machine-speed agent it is not a control at all. Two agents whose inputs come from unrelated sources is the only version of dual control compatible with the threat and the latency budget. No report proposes it. Cost: doubles agent infrastructure. |
| 5 | Micropayment economics | one lane / cheap lane / aggregate under a claim | **One lane now**, aggregation if economics prove blocking — and only revisit with a measured number. §6.5. If a cheap lane is ever built, eligibility must be a **derived predicate evaluated every time, never a flag stored on the actionId or manager** — a stored flag is exactly what makes downgrade possible. |
| 6 | Off-chain signatures | ship with `OFFCHAIN_SIGNATURE` / defer until enumeration exists / never delegate | **Defer.** §8.5. Shipping the permission before the revocation machinery creates authority the owner cannot inventory. |
| 7 | Ejection semantics | one verb, obligations always survive / **two verbs — for-cause freezes, for-convenience preserves** | **Two verbs.** §7. One verb has no defence at all against the insider who creates a claim minutes before revocation. The cost of two is that a false-positive incident freezes real payroll, bounded by auto-expiry and owner triage. |
| 8 | First-time recipients | owner-only / **delegable probation-class enrollment** | **Probation class** (§4.2 `ENROLL_PAYEE`), with owner-only available as a per-wallet setting. Owner-only is safer per decision and will be routed around by pre-approving a wide recipient class — strictly worse in practice. |
| 9 | Do reservations encumber spendable balance? | record-only / **encumber** | **Encumber, with a per-manager cap on total outstanding encumbrance.** Nobody in the corpus answers this. If a reservation only records a claim, a `TRANSFER` agent spends the balance out from under a merchant and the reservation is an over-commitment. If it locks without a cap, an agent holding only `PAYMENT_COMMITMENT` freezes the treasury with large reservations to approved merchants — availability extraction with zero value moved. The cap makes the freeze bounded and the over-commitment impossible. |
| 10 | Price policy ownership | — | Somebody must own a staleness bound, a deviation band, a feed-quorum rule, the designation of the price-free class, and the depeg fallback. All four reports state the principle; none gives a threshold. **Recommend token-denominated caps as the fallback, and defensive actions exempt.** §2.7. |
| 11 | Keep `LIQUIDITY` as its own bit? | keep / merge into `YIELD` + `POSITION_EXIT` | **Keep** — but note this overrules the ranked rule in §4.0, which says market-risk flavour is a rank-5 concern and cannot decide bit allocation. The justification is brownfield continuity: `canManageLiq` exists today, removing it is a migration with no security benefit. If you disagree, overrule the rule explicitly rather than making a quiet exception, because the same pressure recurs for every risk-flavoured variant. |
| 12 | Integrations whose authority cannot be enumerated | support with residual risk accepted / owner-only / decline | **Owner-only**, escalating to decline. §2.8. This is a product constraint with revenue consequences and is the sharpest genuine fork in this list. |

---

## Appendix A — Authority-boundary map across the four reports

Synonyms normalized. "Verdict" is my call, not a vote count.

| Boundary | codex | gemini | grok | claude | Verdict |
|---|---|---|---|---|---|
| Pay now, approved recipient | `PAY_NOW` | `TRANSFER_FUNDS` | `PAYMENT_DIRECT` | `PAY_DIRECT` | 4/4 → `TRANSFER` |
| First-time / arbitrary recipient | OWNER_ONLY | OWNER_ONLY | `PAYMENT_UNRESTRICTED_RECIPIENT` | limit | **All four wrong** → `ENROLL_PAYEE` (probation class). The delegable object is enrollment, not payment |
| Create future claim | `CREATE_PAYMENT_AUTHORITY` | `MANAGE_PULL_PAYMENT` | `CREATE_PERSISTENT_PAYMENT` | `CREATE_PULL_AUTHORITY` | 4/4 → `PAYMENT_COMMITMENT` |
| Revoke future claim | `REVOKE_FUTURE_AUTHORITY` | folded | folded | folded | **codex right, 1/4** → `REVOKE_CLAIMS`, own INITIAL bit |
| Exact temp allowance | primitive | `MANAGE_ALLOWANCES` | `MANAGE_ALLOWANCE` | `GRANT_EXACT_ALLOWANCE` | codex right → not a permission |
| Standing / unlimited allowance | `GRANT_PERSISTENT_ALLOWANCE` | owner-only | `GRANT_STANDING_ALLOWANCE` | `GRANT_UNLIMITED_ALLOWANCE` | 4/4 separate → `STANDING_ALLOWANCE`, LATER |
| Off-chain signature | `SIGN_OFFCHAIN_VALUE_AUTHORITY` | `ISSUE_OFFCHAIN_SIGNATURE` | `SIGN_OFFCHAIN` | `CREATE_OFFCHAIN_ORDER` | 4/4 → `OFFCHAIN_SIGNATURE`, LATER |
| Spot swap | `SWAP_ASSETS` | `EXECUTE_SWAP` | `SWAP` | `SWAP_WITHIN_INTEGRATION` | 4/4 → `TRADE` (exists) |
| Self-custody transform | `SELF_CUSTODY_ASSET_TRANSFORM` | — | — | — | Real; today reached by fail-open fallback |
| Enter yield | `DEPOSIT_TO_STRATEGY` | `MANAGE_YIELD_POSITION` | `YIELD_MANAGE` | `MANAGE_YIELD_POSITION` | codex's split wins → `YIELD` = entry |
| Exit yield | `EXIT_STRATEGY` | merged | merged | merged | → `POSITION_EXIT` |
| Borrow / increase exposure | `INCREASE_EXPOSURE` | `MANAGE_DEBT_POSITION` | `COLLATERAL_AND_DEBT` | — | 4/4 higher tier → `DEBT` |
| Reduce exposure | `REDUCE_EXPOSURE` | `DEFENSIVE_REDUCE_EXPOSURE` | `DEFENSIVE_REDUCE` | `MANAGE_DEBT_DEFENSIVE` | **4/4 independently** → `POSITION_EXIT` |
| Bridge | INITIAL | RESERVED | INITIAL | LATER | 4/4 separate → `CROSS_CHAIN`, LATER |
| Governance | LATER | LATER | LATER | LATER | 4/4 unanimous → LATER |
| Gas / relayer / paymaster fees | folded | mode | `GAS_SPEND` | `PAY_FEES` | Split 2–2 → **carve out** as `PAY_NETWORK_FEES`; the recipient can never be on an allowlist |
| Sub-delegation | RESERVED | RESERVED | RESERVED | RESERVED | 4/4 unanimous → RESERVED |
| Liquidity | in strategy | in yield | in yield | `MANAGE_LIQUIDITY` | exists here → `LIQUIDITY` |
| Rewards | in exit | in yield | in yield | folded | exists here → `REWARDS` |
| Security config | owner-only | `CONFIGURE_WALLET_SECURITY` INITIAL | `ADMIN_MANAGER` RESERVED | owner-only | gemini wrong → owner-only; `MANAGER_ADMIN` RESERVED |

## Appendix B — What each report contributed that no other did

**codex** — the thirteen-primitive execution grammar; the end-of-transaction test stated
mechanically; defensive monotonicity as a ranked criterion producing three permissions that
must survive an incident; the refusal to make bridge-and-deposit one action; the hard rule
against delegated authority the wallet cannot list and invalidate; a stated falsification
test for its own design.

**grok** — monotone restriction ("the extender declaration may only further restrict, never
enlarge"), the crispest formulation of the extender boundary in the corpus; the
approved-versus-arbitrary recipient split; the griefing argument for why ejection must not
auto-cancel obligations; the double condition on composite persistence (permission **and**
registry declaration).

**gemini** — the 10,000× oracle bypass, quantified; the ERC-4626 `withdraw(assets, receiver,
owner)` observation that defeats selector-level defensive enforcement; refunds requiring no
authority; the allowance-granted-before-ejection sequence; the invisibility framing of the
dangerous pair.

**claude** — the refusal to fork a cheap validation lane; per-recipient lifetime caps as the
named answer to compliant compromise; fail-open defaults identified as *the* anti-pattern;
the escalation threshold stated in advance (if per-manager enumeration of all outstanding
authority proves infeasible, escalate to a bounded expression layer).
