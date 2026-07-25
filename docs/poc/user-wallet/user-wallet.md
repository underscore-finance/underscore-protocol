# User Wallet v3 — Lean PoC Architecture

> **Archive notice (2026-07-24):** This is the architecture of the paused
> greenfield proof of concept, not the current Wallet v3 architecture or an
> implementation authorization. See the [archive index](README.md) and the
> [current Wallet v3 documents](../../wallets-v3/README.md).

**Status:** IMPLEMENTATION-READY v11.4, paired with PoC Implementation Guide v2.4.

**Important:** this is an experiment, not a production wallet specification and not an ABI or storage freeze candidate. Its interfaces, storage, encodings, and component boundaries may all change after the results are reviewed.

**Goal:** test whether one non-proxy wallet address can keep custody and protocol identity while replaceable, external, typed extenders add behavior—without `delegatecall` and without migrating user positions.

## 1. Questions the PoC must answer

1. Can one wallet address retain custody and protocol identity across representative Config and extender replacements?
2. Can a Config whose operational authorization calls always revert be replaced without moving funds, positions, attachments, or payment commitments?
3. Can typed extenders be attached and succeeded while remaining unable to exercise general wallet authority?
4. Can the wallet contain both token-spending actions and liability or position actions that allowances cannot constrain?
5. Can one fixed wallet-originated authority call be supported without introducing a generic executor?
6. Can the Base-USDC EIP-3009 external-pull leg and a representative MPP reserved-transfer settlement complete while funds stay in the wallet until the exact authorized pull or settlement?
7. Can an old extender version close its wallet-keyed position after a successor becomes active?
8. Is the resulting direct-transfer path materially cheaper than the equivalent v2 sponsored-wallet path?

Anything not required to answer one of these questions is outside the PoC.

## 2. Deliberate scope boundary

The PoC retains only:

- One `UserWalletV3` with a fixed PoC owner.
- One directly replaceable, wallet-bound `UserWalletConfigV3`.
- Direct, append-only, codehash-pinned extender attachments; no registry.
- A small transient phase lock and at most one effect/capability consumption per session.
- Exact ERC-20 approvals, typed semantic commitments, and relevant postconditions.
- One yield deposit, representative debt actions, and one fixed operator grant/revoke template.
- Two wallet-held payment modes: a Base-USDC EIP-3009 external pull representing the onchain x402 payment leg, and a reserved-transfer model of an MPP (Machine Payments Protocol) metered session.
- Targeted adversarial tests and a compact gas report.

Notably, the PoC has **no wallet freeze or Config-bypassing emergency drain**. Owner administration is admitted only while the wallet is IDLE. If Config is broken, the owner replaces it directly and then uses the ordinary, Config-authorized exit path. Production emergency policy is a separate design problem.

## 3. Components

```text
user / manager
      │
      ▼
┌─────────────────────────────────────────────┐
│ UserWalletV3 — stable per-user address      │
│ custody · Config pointer · routing · phases │
│ approvals · capabilities · reservations     │
└──────────────┬───────────────┬──────────────┘
               │               │
       policy  │               │ typed CALL
               ▼               ▼
┌──────────────────────┐  ┌──────────────────────┐
│ UserWalletConfigV3   │  │ attached extenders   │
│ simple permissions   │  │ yield · debt · pay   │
└──────────────────────┘  └──────────┬───────────┘
                                     │ typed CALL
                                     ▼
                              ┌──────────────┐
                              │ mock Legos   │──▶ vault / debt / token
                              └──────────────┘
```

| Component | PoC responsibility | Holds persistent user funds? |
|---|---|---|
| `UserWalletV3` | Custody, identity, containment, attachment metadata, reservations | Yes |
| `UserWalletConfigV3` | Replaceable owner/manager/recipient/action/amount policy | No |
| Extenders | Translate typed entry points into bounded wallet sessions | No |
| Legos | Trusted protocol adapters for the representative flows | No |
| x402 helper | Derive the pinned token digest and interpret its external-pull state | No |

There is no proxy and no `delegatecall`. Cross-component execution uses ordinary typed `CALL` or `STATICCALL`.

## 4. Minimal `UserWalletV3`

### 4.1 Custody and direct transfer

The PoC custody and transfer surface is ERC-20 only. Native ETH support would add a second transfer and reentrancy model without helping answer the extender questions, so it is deferred.

```text
caller → wallet.transferFunds(recipient, token, amount)
       → Config authorizes
       → wallet checks available balance
       → wallet transfers
```

`available(token) = max(balanceOf(wallet) - reserved(token), 0)`. Every wallet-originated transfer, SPEND approval, and new commitment is bounded by `available(token)`. A SPEND session records its starting balance and reservation, requires a nonzero authorized maximum not exceeding starting availability before calling the Lego, grants that exact maximum, and bounds final token loss by the grant. It therefore cannot consume reserved value even if a used-but-unsynced x402 pull has already made `reserved(token) > balanceOf(wallet)`.

The owner is fixed at deployment. Owner transfer, multisig policy, relayed administration, and account abstraction are deferred.

### 4.2 Direct Config replacement

The owner may replace Config while the wallet is IDLE. The core enters `ADMIN` before making any external validation call. A candidate must:

- Have nonzero code and the expected small interface marker.
- Be constructor-bound immutably to this exact wallet, exposed by `wallet()`.
- Have no public or reusable initializer.

Replacement never calls or requires cooperation from the old Config. The new Config starts with constructor-initialized PoC policy; this experiment does not migrate Config state. Funds, positions, attachment records, reservations, and commitments remain in the wallet.

The wallet can runtime-check the marker and current `wallet()` answer, but it cannot prove by generic bytecode introspection that an arbitrary candidate has no hidden rebinding path. Immutability and absence of an initializer are properties of the reviewed PoC Config source.

This proves the architectural escape from a broken Config. It does not specify production recovery, owner-compromise handling, delays, or state migration.

### 4.3 Direct extender attachment and succession

While IDLE, the owner appends a bounded attachment record:

```text
familyId · version · extender address/codehash · routed selectors ·
Lego address/codehash · declared action/effect/consumer modes · exit selectors ·
optional fixed authority target/codehash · optional x402 helper/codehash
```

Attachment ids and identity/dependency fields are append-only and immutable. The lifecycle field has one permitted transition:

- `ACTIVE`: current routing may open new actions.
- `DRAIN_ONLY`: only its registered position-closing selectors may run.

Attaching a strictly higher family version at a different extender address atomically removes every current route for the prior family version, marks it `DRAIN_ONLY`, then installs the successor. A successor may be a new deployment of the same reviewed source and may therefore have the same runtime codehash; address, attachment id, and version provide version identity. Active selector collisions across families are rejected. There is no manual lifecycle mutation, detach, or HARD_REVOKE.

Normal calls to an old version use its exact attachment id and remain Config-authorized. Extender, Lego, fixed authority target, and helper codehashes are checked again when used. Forwarding typed ABI calldata to a pinned extender and registered selector is allowed; forwarding extender-supplied calldata to an arbitrary target is not.

No ExtenderBook, LegoBook, bundle tree, governance registry, proof system, or timelock is built.

### 4.4 Execution phases

Transient storage provides one wallet-wide execution lock:

```text
IDLE → DIRECT → IDLE
IDLE → DISPATCHING → ACTIVE → SETTLING → IDLE
IDLE → COMMITMENT → IDLE
IDLE → ADMIN → IDLE
```

`IDLE` is phase value zero. Transient storage therefore decodes to IDLE at the start of every top-level transaction, including the merchant transaction—separate from commitment creation—in which USDC makes the nested EIP-1271 callback. Every non-IDLE phase has a nonzero value.

- Every stateful top-level action requires IDLE and sets its phase before its first external call.
- The router records the real caller, attachment, selector, typed-calldata hash, action id, authorized request, Config snapshot, and session nonce.
- Only the routed extender may open that exact session.
- Only the session's pinned Lego may call the general `consumeCapability` primitive. Named CORE primitives consume internally after verifying the active routed extender.
- SETTLING clears the session approval before checking balances and beneficiaries.
- Only a `NONE` route may return without consuming the capability. This is a safe no-effect session used to measure framework overhead; it leaves no approval or persistent economic state. A `LEGO` or `CORE` route must consume before the extender returns or the entire execution reverts.
- No nested sessions, generic receiver callbacks, after-session hooks, or answer-handler framework exists.
- Rail-only `isValidSignature` is a bounded static answer and requires the wallet to be IDLE.

### 4.5 One action capability

The PoC deliberately supports at most one effect and one capability consumption per session. A transient `consumed` bit prevents reuse.

| Mechanism | What it demonstrates | PoC example |
|---|---|---|
| A — token-loss bound | Exact approval plus maximum wallet balance loss | vault deposit |
| B — semantic/effect bound | Actual target, asset, amount, beneficiary, and effect match the authorized request | borrow / remove collateral |
| C — fixed wallet call | Core constructs one bounded call that must originate from the wallet | operator grant/revoke |

A flow may require more than one mechanism; the yield deposit uses A+B. Core derives the semantic hash from a domain-separated common envelope and an action-specific data hash. The Lego supplies the actual common fields and action-data hash before the external effect; the wallet recomputes and compares the semantic hash with the authorized request. Core settlement checks approval cleanup and the maximum input-token loss. Direct beneficiary delivery is bound before effect and proved from the mock protocol's resulting state; the PoC does not add a generic callback/postcondition framework.

Each route declares an action id, effect class, and one bounded consumer mode:
Lego-consumed, named-core-consumed, or measurement-only no-effect. Generic
Lego-consumed actions are not hardcoded into a core action registry. Named core
primitives remain action-specific. This permits the future-action test to add a
new Lego-consumed action without changing the wallet core.

The C example is a narrow wallet entry point. Grant is callable only by the active routed DebtExtender. Revoke is callable by that active route or by the exact Config-authorized `DRAIN_ONLY` revoke selector for the attachment that granted the authority. Core validates and consumes the capability internally, then constructs the call granting or revoking one pinned Debt Lego on one pinned mock protocol. Every Lego entry point capable of using that authority still requires the exact wallet/attachment's active session and capability consumption. The template does not accept arbitrary targets, operators, or calldata. Multi-action sessions, schema registries, generalized templates, and production action vocabulary are deferred.

### 4.6 Wallet-held payment commitments

Commitment creation is an `ACTIVE`-phase wallet entry point. Only the routed PaymentExtender may call it. Core validates every economic field against the authorized request, requires `0 < amount <= available(token)`, and consumes the capability internally before creating the commitment. Commitment ids, external-exact digests, and external-authorization nonces are permanently non-reusable within the PoC deployment.

Two modes are implemented:

1. `EXTERNAL_EXACT` — x402/Base USDC:
   - Stores exact digest, token, amount, destination, validity window, and the attachment-pinned x402 helper.
   - Reserves the exact amount in the wallet.
   - Rail-only EIP-1271 returns MAGIC only for that live exact commitment.
   - The exact USDC pull moves funds to the merchant before core sync. Until sync, the unchanged reservation conservatively reduces the wallet's other spending capacity.
   - Anyone may then call sync; the helper's address and codehash are rechecked and it verifies that exact authorization was used.
   - Expiry releases funds only after the helper proves the authorization can no longer be used. A used-but-unsynced authorization cannot be expired as unused.

2. `RESERVED_TRANSFER` — representative MPP metered-session settlement:
   - Stores token, total amount, destination, and settlement operator.
   - Core—not a helper—requires `msg.sender == settlementOperator` for partial settlement.
   - Only the wallet owner may refund the unsettled remainder.
   - The stored destination cannot be changed.

The MPP branch tests wallet reservation and cumulative partial-settlement mechanics only. It does not implement or claim compliance with MPP HTTP challenges, credentials, receipts, or a production payment-method specification.

Settlement records the new state and reservation before transferring tokens; token failure reverts both. Refund is only a state transition that releases the unsettled reservation back into the wallet's available balance. Terminal commitments retain enough state to prevent replay or resurrection. Reserved value is excluded from transfers and new commitments.

Commitments remain usable across Config replacement, PaymentExtender succession, `DRAIN_ONLY`, and unrelated failed sessions. No general EIP-1271, fee policy, notification callback, settlement hook, policy snapshot, or adapter registry is included.

## 5. Minimal `UserWalletConfigV3`

Config contains only:

- Its immutable wallet binding.
- Owner and manager recognition.
- Recipient allowlist.
- Allowed tokens and action ids.
- Simple per-call amount caps.
- `authorizeTransfer(...)` and `authorizeSession(...)`.

The wallet itself and a nonzero Lego consumer are beneficiary exemptions. CORE payment actions have a zero consumer, so their merchant/payment destinations must be Config-allowlisted recipients.

There are no modules, payees, period counters, pricing/USD conversion, points, fees, proposal state, or settlement callback.

## 6. Extenders and Legos

The PoC builds three representative extenders plus one future-compatibility extender:

- `YieldExtender`: one mock ERC-4626-like deposit.
- `DebtExtender`: representative borrow, repay/close, and remove-collateral actions plus the fixed operator template.
- `PaymentExtender`: Base-USDC external-exact and representative MPP reserved-transfer authorization entry points.
- `FutureActionExtender`: one late-added mock asset-release action that must not modify the core action engine.

A separate test-only benchmark extender opens the NONE-consumer empty session; it is not part of the representative behavior surface or the malicious-extender fixture.

Extenders are shared typed contracts. They hold no persistent user funds or allowances, have no general wallet authority, and must open the routed, Config-authorized session before using a primitive. The malicious-extender exercise proves policy/effect containment, not that malicious extender code preserves the caller's intended argument values: attaching and reviewing the typed extender remains a trust decision.

Legos are trusted protocol-specific enforcement adapters for the PoC. Each Lego:

- Requires the active wallet/extender pair.
- Consumes the capability using its actual typed arguments before the effect.
- Pulls only an authorized amount through an exact approval.
- Uses an exact protocol approval and clears it.
- Sends shares, borrowed assets, refunds, and released collateral directly to the wallet.

The PoC tests containment of a malicious extender. A registered malicious Lego is outside the trust model because a Lego already mediates protocol authority; production Lego review and governance are deferred. Protocol callback machinery is also deferred.

## 7. Representative flows

### Direct transfer

```text
owner/manager → wallet → Config authorization → available-balance check → token recipient
```

### Yield deposit

```text
caller → wallet router → YieldExtender → open authorized session
       → wallet exact approval → Yield Lego consumes A+B capability
       → mock vault mints shares directly to wallet
       → approval cleared and input-loss/beneficiary postconditions checked
```

### Debt and extender succession

```text
DebtExtender v1 opens a wallet-keyed mock debt position
→ owner installs a Config whose authorization calls always revert
→ owner replaces it directly with a fresh working Config
→ owner attaches DebtExtender v2; v1 becomes DRAIN_ONLY
→ repay/close through v1's exact Config-authorized exit route
→ wallet address and protocol position owner never change
```

### Base USDC external exact (x402 onchain leg)

```text
PaymentExtender authorizes EXTERNAL_EXACT commitment
→ wallet reserves USDC
→ merchant/facilitator calls USDC transferWithAuthorization
→ USDC asks wallet.isValidSignature
→ pull succeeds
→ permissionless sync verifies use and clears the reservation
```

### Representative MPP reserved transfer

```text
PaymentExtender authorizes RESERVED_TRANSFER
→ wallet reserves tokens
→ stored operator settles one or more partial amounts to the stored destination
→ owner refunds any remaining reservation
```

## 8. PoC invariants

1. Persistent user funds and protocol positions remain owned by the wallet, never an extender.
2. No proxy, `delegatecall`, or arbitrary target/calldata executor exists.
3. Every stateful top-level wallet frame acquires a phase before any external call.
4. Only the routed extender and pinned Lego may use the active session.
5. The single capability is consumed at most once and matches the actual effect fields.
6. Token approvals are exact, session-scoped, and cleared before success; no-effect sessions also clear any approval.
7. Reserved payment value is unavailable to direct transfers, session approvals/spends, and new commitments; wallet-originated settlement cannot consume the reserved portion.
8. Payment settlement cannot exceed, replay, or resurrect a commitment.
9. Config replacement and extender succession never change wallet-owned economic state.
10. Old-version exits remain selector-bounded, codehash-pinned, and Config-authorized.

## 9. Measurements

The PoC measures only architecture-relevant costs:

- Paired v2/v3 initialized, independent-transaction, cross-block owner-to-whitelist ERC-20 transfer in the pinned-Base-state Boa profile. Hard v3 criterion: below 190,000 modeled tx-equivalent gas and cheaper than paired v2.
- Empty routed session. Initial review target: below 60,000 tx-equivalent gas.
- Minimal yield deposit compared with direct mock-protocol cost.
- Base-USDC external-exact authorization and sync.
- Representative MPP reserved-transfer authorization, partial settlement, and refund.
- Core runtime size. Initial review target: below 16,384 bytes.

Only the transfer threshold is a hard PoC gate. All other measurements receive an explicit accept/redesign disposition in `POC_RESULTS.md`; they do not create production baselines.

## 10. Success criteria

The PoC succeeds only if:

- All representative flows and targeted attacks pass.
- A wrong-wallet Config is rejected, while the current Config may revert on every operational authorization call and still be replaced.
- Yield shares and the debt position remain keyed to the same wallet across Config/extender replacement.
- The v1 route cannot open positions after v2 is attached, but its exact exit can close the old position.
- The EIP-3009 external-pull and representative MPP values stay wallet-held until the exact authorized pull/settlement; external-pull reservation accounting remains conservative until sync.
- A new mock action can use the existing action engine without changing the core.
- Direct-transfer gas meets its hard criterion and every other measurement has an explicit disposition.
- `POC_RESULTS.md` recommends which ideas to keep, redesign, or abandon.

Passing the PoC does not authorize deployment or freeze any interface.

## 11. Explicitly deferred

- Wallet freeze/unfreeze, Config-bypassing emergency drains, security signers, and emergency owner policy.
- Production ABI/storage freeze, upgrade guarantees, migration tooling, factories, and cutover plans.
- Owner transfer, multisig, account abstraction, relayed administration, and session keys.
- Timelocks, proposal/confirmation machinery, and governance registries.
- ExtenderBook, LegoBook, ModuleBook, bundle proofs, and dependency-governance policy.
- Config state copying, `MIGRATE`, `RECOVER_FRESH`, recovery handshakes, and notification checkpoints.
- General EIP-1271, answer handlers, receiver hooks, and protocol callbacks. A narrow ERC-165 declaration for the rail-only EIP-1271 function is permitted.
- Fees, policy snapshots, pricing, USD limits, period accounting, points, and yield tracking.
- Native ETH, NFTs, swaps, liquidity, rewards, and generalized wallet-call templates.
- Detach/HARD_REVOKE and proof of no remaining external position; PoC attachments retain their exact exit routes.
- Production payment cancellation policy, multiple rail adapters, and retryable notifications.
- Real Morpho/Ripe integration; representative mocks plus real Base USDC are sufficient for the experiment.
- ERC-4337/UserOperation benchmarking.
- Candidate manifests, freeze artifacts, ratification, golden-vector packages, and exhaustive audit matrices.

## Implementation handoff

The build sequence, tests, repository layout, and measurement method are in the [Lean PoC Implementation Guide](implementation-guide.md).
