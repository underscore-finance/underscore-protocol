# User Wallet v3 — Architecture & Spec

**Status:** DRAFT for review. High-level plan only — sections expand with full signatures, storage layouts, and flows after the overall shape is approved.

**One-line goal:** a wallet users never migrate again — new protocols and verbs ship as attachable modules, positions and payment routes stay keyed to one permanent address, and every sponsored action costs materially less gas.

---

## 1. Why v3

- **Migrations are painful and lossy.** External positions keyed to the wallet address (Ripe collateral/debt, locked gov-vault RIPE stakes) cannot move — they must be unwound and rebuilt. Config cloning is version-coupled with no on-chain version tag. Pending payment refunds (`op.payer`) go stale.
- **We're out of code space.** UserWalletConfig sits ~720 bytes under EIP-170; UserWallet needs `pragma optimize codesize`. x402/MPP support cannot be bolted onto the v2 monolith.
- **Gas is sponsored and expensive.** Profiling (docs/gas-profiling/) shows a payment costs 335–740k gas of which the actual transfer is ~5–25k. Most overhead is structural (unconditional struct loads, duplicate derivations, unpacked storage) — v3 is a fresh storage layout, so the fixes are free to bake in.

## 2. Design principles

1. **The wallet address is the user's permanent identity.** The core contract is small enough to audit exhaustively, then frozen. Everything else around it is replaceable.
2. **Core implements EVM standards; Extenders implement protocols.** EIP-1271, token receiver hooks, and a selector router live in core (protocol-agnostic). x402 digests, Ripe verbs, DEX routing live in Extenders.
3. **Funds live only in the wallet.** Extenders and legos never custody user assets beyond a metered, single-action approval window. No hub/omnibus contracts holding pooled user funds.
4. **All permissioning stays at the top.** Every action — regardless of which Extender routes it — passes through the same config → Sentinel gate, and every outbound transfer passes the payee/whitelist/cheque gates in core.
5. **Pay for what the action needs, nothing more.** Owner-signed simple transfers must not load manager machinery; whitelist recipients must not load payee machinery; the tx-invariant context is derived once per transaction.

## 3. Component map

```
                    ┌───────────────────────────────────────────────┐
  agents / users ──▶│  EXTENDERS (stateless singletons, swappable)  │
                    │  Yield · Swap · Debt · Liquidity · Rewards    │
                    │  Pay-x402 · Pay-MPP · future protocols        │
                    └───────────────┬───────────────────────────────┘
                                    │ beginAction / grantApproval /
                                    │ settleAction / authorizeHash
                    ┌───────────────▼───────────────┐     ┌──────────────────┐
                    │  USER WALLET (core, frozen)   │────▶│  LEGOS (v2-style) │──▶ external
                    │  custody · transfer gates ·   │◀────│  called by        │    protocols
                    │  action bracket · EIP-1271 ·  │     │  extenders        │
                    │  selector router · asset data │     └──────────────────┘
                    └───────────────┬───────────────┘
                                    │ permission checks / state
                    ┌───────────────▼───────────────┐
                    │  USER WALLET CONFIG (state)   │◀──── backpack items
                    │  managers · payees · whitelist│      (Kernel, HighCommand,
                    │  cheques · attachments ·      │       Paymaster, ChequeBook,
                    │  timelocks                    │       Sentinel, Migrator)
                    └───────────────────────────────┘
```

| Component | Deployment | Upgradeable? | Holds funds? | Holds state? |
|---|---|---|---|---|
| UserWallet (core) | per-user blueprint | **never** (that's the point) | yes — all of it | asset registry, attachments, authorized hashes |
| UserWalletConfig | per-user blueprint | re-pointable (timelocked; see §5) | no | all user settings |
| Extenders | shared singletons | swap anytime (registry + attach) | no | protocol bookkeeping only, keyed by wallet |
| Backpack items | shared singletons | owner opt-in per wallet (as today) | no | none (logic only) |
| Legos | shared singletons | governance registry (as today) | transient only | none |

## 4. UserWallet core (permanent)

The complete external surface. Everything here is protocol-agnostic; the bet is that this list never grows.

**Custody & transfer**
- `transferFunds(recipient, asset, amount, ...)` — the *only* way value leaves at rest. Runs payee/whitelist/cheque gates via config/Sentinel. Includes a native batch variant (one permission bundle, N transfers — profiling measured −27–30% for batches of 2).
- `__default__` (receive) + `onERC721Received`.

**Action bracket** (callable only by attached Extenders; one open action per tx, tracked in transient storage)
- `beginAction(signer, action, assets[], legoIds[]) -> ActionData` — runs the full signer permission path once, snapshots declared asset balances, caches the bundle in transient storage.
- `grantApproval(asset, amount, legoId) -> amount` — exact approval; target resolved from LegoBook by the core, never supplied by the caller.
- `settleAction(assets[], usdValue)` — zeroes every approval granted this action, balance-diffs declared assets, realizes yield, pays fees, updates asset registry + deposit points, runs manager post-tx limits **from the cached bundle** (no re-reads).

**Outbound authorization** (deferred payments — x402/EIP-3009, future signature-based rails)
- `authorizeHash(hash, expiry)` — attached-Extender-only, inside an open action whose outbound gate (payee checks on dest/asset/amount) passed. Core stores `(binderExtender, expiry)`.
- `revokeHash(hash)` — binder, owner, or security action.
- `isValidSignature(hash, sig) -> bytes4` — EIP-1271. MAGIC iff hash is stored, unexpired, **and its binder is still attached**. Core never interprets hashes; detaching an Extender instantly voids everything it bound.

**Forward compatibility**
- Selector router in `__default__`: unknown selector → `selector -> handler` lookup (owner-set via config, registry-validated) → plain `call`/`staticcall` forward with original caller appended. Handlers answer; they cannot move funds. Core selectors cannot be shadowed. This is how the wallet exposes interfaces that don't exist yet (flash-loan callbacks, new receiver hooks, future payment standards) without a core change.
- `setLegoAccessForAction` — the existing constrained operator-grant raw_call (e.g. Ripe `setUndyLegoAccess`), unchanged. The wallet remains the on-record owner of external positions forever.

**Wiring**
- `attachments` mapping (Extender set + selector handlers) — mutated only by config, which enforces owner intent, timelock, and ExtenderBook registration.
- `walletConfig` pointer — **re-pointable** via a heavily-guarded, timelocked flow (see §5). This is the escape hatch that makes config evolution non-migratory.
- Special paths that must survive: trial-funds clawback, `preparePayment`/Billing pulls, eject mode, freeze.

## 5. UserWalletConfig

Same role as v2 — the per-wallet state container — with four changes:

1. **New packed storage layout.** Hot structs hand-packed (profiling: `PayeeData` 8→3 slots, `ManagerData` 7→3, `Cheque` 11→5, `ChequeData` 11→4, points 6→2–4). Halves recurring writes and first-touch 20k/slot cliffs.
2. **Owner fast path is a layout concern.** `canOwnerManage` + frozen/eject flags packed into one slot read first; the three manager-struct getters (measured 130k cold on every v2 owner action) are only touched when the signer is actually a manager.
3. **ActionDataProvider becomes swappable** (it is `immutable` in v2 — a documented migration-forcing landmine). Same owner-opt-in rules as backpack items.
4. **Extender attachment lifecycle** lives here: `attachExtender` (timelocked, must be ExtenderBook-registered), `detachExtender` (instant — kill switch, also usable by security signers), selector-handler management with the same rules.
5. **Config replacement without wallet migration:** owner initiates → timelock → new config (governance-registered template) is deployed, state copied by the Migrator, core re-pointed. Funds, positions, address, attachments never move. This retires the "same-version config clone" constraint; add `version()` tags to both contracts regardless.

Action types become plain `uint256` at the core/config boundary (not a compile-time flag) so new action classes ship via a Sentinel upgrade, never a core change.

## 6. Extenders

**Definition:** stateless singleton logic modules, registered in an **ExtenderBook** (LegoBook-style timelocked governance registry), attached per-wallet by the owner. They are to UserWallet what backpack items are to UserWalletConfig — trusted registered code that relays the real signer and calls privileged, sender-gated functions.

**What an Extender does:** owns the typed user-facing ABI for a domain, validates protocol-specific inputs, orchestrates legos with plain typed `extcall`s (no raw_call), and does its bookkeeping in its own storage keyed by wallet address. Because the wallet address is permanent, that bookkeeping survives everything.

**What an Extender cannot do:** hold funds; receive approvals; move value except through the core's gated primitives; act on a wallet it isn't attached to; bypass Sentinel (the signer it relays goes through the same checks as v2).

**Initial set (maps 1:1 to v2 wallet verb groups):**

| Extender | Absorbs from v2 | Notes |
|---|---|---|
| YieldExtender | depositForYield / withdrawFromYield / rebalance | |
| SwapExtender | swapTokens / mintOrRedeem / confirmMintOrRedeem | swap-fee logic moves with it; fee *enforcement* stays in core settle |
| DebtExtender | addCollateral / removeCollateral / borrow / repay / deleverage | Ripe positions stay keyed to the wallet address — nothing to migrate, ever |
| LiquidityExtender | add/removeLiquidity (+ concentrated) | NFT round-trip checks come along |
| RewardsExtender | claimIncentives | |
| PayExtender-x402 | replaces the PayProcessor hub | binds EIP-3009 digests with `from = wallet` via `authorizeHash`; facilitator pulls wallet → merchant directly; refund-before-pull = revoke. No pooled funds, no commingling |
| PayExtender-MPP | replaces MPP escrow | wallet *is* the escrow: register = record op (nothing moves), settle = gated transfer to bridge address, refund = cancel. Residual: per-transfer bridge minimums may require per-wallet op batching |
| WethExtender | convertEthToWeth / convertWethToEth | candidate to keep in core if cheap enough — open question |

**Lego-side changes required (one-time, we own all legos):** legos pull from the explicit `_user` instead of `msg.sender`, and caller guards like Ripe's `assert msg.sender == _recipient` relax to "recipient or an attached Extender of recipient." External protocols see no difference — the lego is still what calls them, and operator grants are still wallet→protocol.

## 7. Backpack items

Largely unchanged in role; all get the packed-layout treatment.

- **Kernel / HighCommand / Paymaster / ChequeBook** — same responsibilities against the new config layout. ChequeBook adds the instant-cheque short-circuit (create-and-pay without persisting the 11-slot record; profiling: saves ~300–400k of the ~973k atomic flow).
- **Sentinel** — same validation role; consumes `uint256` action ids (unknown ids → a default extension-action permission class with USD limits); owner path reduced to the packed fast-path slot.
- **Migrator** — shrinks to: v2→v3 cutover tool + config-replacement copier (§5.5). Steady-state wallet-to-wallet migration stops being a product feature.
- **ActionDataProvider** — assembles the bundle once per tx into the core's transient cache; loses the per-helper back-call chatter (v2: ~14 staticcalls, 16 registry `getAddr`s per action).

## 8. Transaction flows (abbreviated)

**Yield deposit (agent):**
```
agent → YieldExtender.depositForYield(wallet, legoId, asset, vault, amt)
  → wallet.beginAction(agent, EARN_DEPOSIT, [asset], [legoId])   # perms, snapshot, bundle→transient
  → wallet.grantApproval(asset, amt, legoId)                     # exact, LegoBook-resolved
  → Lego.depositForYield(asset, amt, vault, wallet, ...)         # typed extcall; shares minted to wallet
  → wallet.settleAction([asset, vaultToken], usd)                # approvals zeroed, diffs, fees, limits
```

**x402 payment (no hub):**
```
agent → PayExtender402.pay(wallet, vendor, amt, dest, paymentId, window)
  → wallet.beginAction(...)                        # payee/cheque gates run on dest+amt
  → extender builds EIP-3009 digest (from = wallet)
  → wallet.authorizeHash(digest, validBefore)      # + op recorded in extender storage
  ... later: facilitator → USDC.transferWithAuthorization(from=wallet, to=dest, ...)
             USDC → wallet.isValidSignature(digest) → MAGIC → funds move wallet→merchant
```

**Simple transfer (owner):** stays entirely in core — `wallet.transferFunds(...)`, no Extender hop, owner fast-path permission read, whitelist early-out. This is the highest-volume path and is designed to be the cheapest.

## 9. Gas strategy (baked into the design, not bolted on)

From docs/gas-profiling/ (measured on v2; the v2 transfer is 335–740k with ~5–25k of actual transfer):

| Rule | Source finding | v3 mechanism |
|---|---|---|
| Owner actions never load manager structs | 130k cold wasted per owner action (R1, both reports) | packed fast-path slot read before any struct getter |
| Derive the bundle once per tx | pre/post double-derivation; batch 2nd action −120k (R14) | `beginAction` caches to transient; `settleAction` and batched actions reuse |
| Pack every hot struct | Vyper = 1 slot/field; first-touch cliffs of 100–236k (R10) | new layout: PayeeData 8→3, ManagerData 7→3, Cheque 11→5, ChequeData 11→4, points packed |
| Price once per action | 2 Appraiser round-trips + 2×`isBasicEarnVault` (26.9k) per transfer (R2/R8) | Appraiser returns unit price + yield flag once; core computes both values; O(1) vault classification |
| Trust resolved addresses | Ledger resolved 4–6×, 16 `getAddr`/action (R3) | bundle addresses passed down; callee trust = registered-wallet check already in place |
| Points accrual off the hot path | 20–99k per action, unconditional (R15) | skip when value unchanged; evaluate lazy checkpoint (open question) |
| Batch natively | −27–30% measured for 2 actions (R4/R7) | core batch transfer + one bracket for multi-step Extender actions |
| Cheap paths stay cheap | whitelist ~3k vs payee 80–236k (R9) | whitelist early-outs preserved; product favors whitelisting; instant-cheque short-circuit |
| No minimal proxies | +2.6k/call forever to save one-time deploy (both reports §8.5) | keep full blueprint deploys; core is small so deploy cost drops anyway |

The Extender hop itself costs one call frame (~2.6k) — noise against the structural savings above. Net expectation: the common sponsored paths land well under half of today's cost; re-measure per combination rather than summing (per the reports' warning). Fix the exact-full-ETH deregister revert (§9 of both reports) in the v3 core from day one.

## 10. Migration story

- **One final v2→v3 migration** per user: move token balances (incl. receipt tokens), clone config into the new layout, re-establish attachments. Ripe debt / locked-stake wallets (<10 today): either a Ripe-side, Migrator-gated `transferPosition` (preferred — moves collateral/debt/lock timers intact; we control Ripe) or concierge unwind.
- **After v3:** there is no wallet migration. New protocol = new Extender. New validation logic = new Sentinel/backpack item. New config layout = config replacement behind the permanent core. New inbound interface = selector handler.

## 11. Security invariants

1. Value at rest leaves only via `transferFunds` (payee/whitelist/cheque gated) or a facilitator pull against a hash bound through those same gates.
2. Approvals are exact, action-scoped, and zeroed at settle; targets only ever resolve from LegoBook.
3. Every action's signer passes the identical config→Sentinel path regardless of entry point.
4. Extenders/handlers are doubly gated: governance registration (timelocked) AND owner attachment (timelocked on, instant off). Detach voids the Extender's pending hash authorizations atomically.
5. No delegatecall anywhere. Handlers are `call`-forwarded answerers with no custody and no privileged wallet access.
6. Governance can never force code onto an existing wallet (unchanged from v2 backpack sovereignty).

## 12. Open questions (for review)

1. **Naming:** "Extender" vs "Extension"; "ExtenderBook" vs folding registration into LegoBook with a type flag.
2. **WETH wrap/unwrap:** keep in core (tiny, high-frequency) or first Extender?
3. **Attach timelock length** — same as wallet timelock, or a shorter dedicated one? Should security signers be able to detach (kill switch) as specced?
4. **MPP without the hub:** accept per-wallet batching latency against bridge minimums, or keep a slim staging pool as a transitional MPP-only component?
5. **x402 v1 sequencing:** ship the existing hub branch first and treat it as scaffolding, or hold x402 for v3 Extenders?
6. **Deposit points:** how lazy can accrual get without breaking loot fairness? (Biggest remaining unconditional per-action cost.)
7. **Agent stack:** AgentWrapper/senders point at Extender ABIs in v3 — fold the payments sender (AgentSenderPay) into PayExtenders, or keep the sender layer as-is?
8. **Config replacement guardrails:** what's copied automatically vs re-established manually (managers yes; pending cheques?), and does replacement require a fresh global registry template check only, or per-field validation like today's Migrator?
