# Agent Payments: x402 + MPP Settlement Engine

The agent-payments settlement engine lets an Underscore agent pay a verified service (a "vendor") in
USDC on Base, over two rails behind one entry point. It settles either directly to the merchant (**x402**)
or to an off-chain **Tempo** omnibus in batches (**MPP**).

## Architecture

| Contract | UndyHq dept | Role |
|----------|-------------|------|
| `PayProcessor` | 13 | Settlement hub: pulls funds from the vendor, records the `Operation`, runs the rail (x402 EIP-1271 payer / MPP escrow → bridge). |
| `AgentSenderPay` | — (an AgentSender) | Owner-signed orchestrator: sources the user's USDC and calls `PayProcessor.vy:register`. |
| `VendorRegistry` | 12 | Factory + registry of `VendorProxy` service payees. |
| `VendorProxy` | — (per vendor) | Per-service payee that transiently holds funds and owns a destination allow-list. |
| `SwitchboardDelta` | — (a Switchboard) | Config + ops gateway — the single caller-authorization layer for every switchboard-gated call. |

**End-to-end flow.** `AgentSenderPay.vy:pay` authenticates the owner's signature, sources the payment
(optionally withdrawing from an earn vault first) and pushes the user's USDC into the service
`VendorProxy`, then calls `PayProcessor.vy:register`. `register` gates on
`VendorRegistry.vy:isVendor` (`indexOfVendor(vendor) != 0`) and `VendorProxy.vy:isAllowed`, pulls the USDC
out of the vendor, records an immutable `Operation` (incl. `protocolId` and `dest`), and routes by
`protocolId`:

- **MPP (1):** escrow the amount; then (switchboard) `settle()` → `availToBridge` → `bridge()` off-ramps a
  batch to the Tempo omnibus.
- **x402 (2):** bind an EIP-3009 authorization; the merchant's facilitator pulls the funds from the
  processor via `transferWithAuthorization`.

USDC is the only settlement asset. Every settle/bridge/refund and all vendor/destination admin is gated
through `SwitchboardDelta` — see [Trust & security model](#trust--security-model).

## x402 rail (EIP-3009 `exact` scheme)

The x402 rail settles a payment **directly to the merchant's own address** with no protocol-held escrow
beyond the moment of the pull. The `PayProcessor` acts as the on-chain **payer**: it authorizes a USDC
EIP-3009 `TransferWithAuthorization` and answers as an EIP-1271 smart-contract signer, so the merchant's
x402 **facilitator** pulls the funds itself. USDC (FiatTokenV2_2) is both the asset and the signature
verifier.

### Flow

1. `PayProcessor.vy:register` (with `_protocolId = RAIL_X402`) runs the common gate — vendor registered,
   `_dest` on the vendor allow-list, USDC pulled from the VendorProxy into the processor — then decodes
   `(validAfter, validBefore)` from `_extraData` (`abi_encode(uint256,uint256)`), asserts
   `validAfter < validBefore`, computes the EIP-3009 digest, sets `authorized[digest] = True`, records the
   op (incl. immutable `protocolId` and `dest`), and returns the digest.
2. The facilitator submits `transferWithAuthorization(from=processor, to=dest, value, validAfter,
   validBefore, nonce, sig)` to USDC.
3. USDC recomputes the digest from those params and calls `PayProcessor.vy:isValidSignature`, which
   returns `MAGIC` (`0x1626ba7e`) iff `authorized[digest]`. The `sig` bytes are **ignored** — the funded,
   dest-gated registration *is* the authorization. USDC then moves `value` USDC processor → dest and
   consumes the nonce.

### Digest binding & nonce

- Digest is built by `PayProcessor.vy:_x402Digest` / `_domainSeparator` over USDC's own EIP-712 domain:
  `name = "USD Coin"`, `version = "2"`, dynamic `chainId`, `verifyingContract = USDC`, and the standard
  `TransferWithAuthorization` typehash.
- **Nonce is `keccak256(paymentId)`** — one paymentId ⇒ one nonce ⇒ one pull. This binds the EIP-3009
  authorization 1:1 to the operation and reuses the same correlation key everywhere.
- Off-chain helpers for the facilitator: `PayProcessor.vy:getX402Digest` and `PayProcessor.vy:x402Nonce`.

### Hardcoded-USDC-domain requirement (deploy guard)

The domain `name`/`version` are compile-time constants, so the processor's digest must byte-for-byte equal
what the deployed USDC computes or **x402 silently never settles** (the processor authorizes digests no
facilitator can ever satisfy; funds sit until refunded, with no revert to warn you). `PayProcessor.vy:__init__`
enforces this at deploy: `assert UsdcAuth(_usdc).DOMAIN_SEPARATOR() == self._domainSeparator()`. A wrong
token — e.g. bridged **USDbC**, whose `name()` is `"USD Base Coin"` — reverts the deploy. Verified match
against Base native USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`.

### Refund (all-or-nothing)

EIP-3009 authorizations cannot be partially un-bound, so an x402 refund via `PayProcessor.vy:refund` must
clear the whole op: `assert _amount == op.amount - op.refunded`. It first checks
`USDC.authorizationState(processor, nonce)` and reverts if the merchant already pulled; otherwise it
revokes by clearing `authorized[digest]` and `opDigest[paymentId]` before returning the USDC to the payer.

### Security properties & nuances

- **No redirection.** `dest` is bound into the digest, so settlement can only ever pay the allow-listed
  destination — a caller cannot retarget funds.
- **No replay.** USDC's per-`from` nonce blocks a second pull of the same authorization.
- **Rail is immutable.** `settle`/`refund` branch on `Operation.protocolId`, never on the mutable
  `opDigest` — an x402 op can never be mistaken for MPP.
- **Settlement is permissionless but safe.** `isValidSignature` ignores the signature, so anyone holding
  the full params can trigger the pull — but only ever *toward the bound dest*, i.e. accelerating the
  intended payment. The one residual is that a pending refund is a race against the pull.
  `validAfter`/`validBefore` are **not** emitted on-chain (only `amount`/`dest`/`digest`/`nonce` via
  `OperationRegistered` / `X402Authorized`), so in practice only the party holding the x402 payload (the
  merchant/facilitator) can form the call — matching EIP-3009 semantics. If guaranteed refunds are
  required they must be enforced off-chain (a settlement hold with the facilitator); the chain cannot
  prevent an authorized pull.

## MPP rail — escrow, settle, bridge, refund

### What it does

MPP (Machine Payments Protocol) is the Tempo off-ramp rail. Funds are escrowed on Base and bridged in
batches to a Switchboard-set Bridge liquidation address, which off-ramps the pooled USDC to Tempo. There
is **no per-payment on-chain guarantee** that the merchant received the funds; settlement is fully
operator-controlled (see [Trust & security model](#trust--security-model)).

### Lifecycle

```
register()  →  [pendingTotal]  →  settle()  →  [availToBridge]  →  bridge()  →  Bridge
                                    ↓ (pre-settle only)
                                  refund()  →  payer
```

**`PayProcessor.vy:register` (MPP path)**
- Caller must be a registered sender (`senders[msg.sender]`).
- USDC is pulled from the VendorProxy into the processor (`VendorProxy.vy:transferToProcessor`).
- An `Operation` record is created with `protocolId = RAIL_MPP` (immutable — never re-derived from the
  mutable `opDigest`).
- `pendingTotal += amount` — the op enters the refundable escrow counter.
- Returns `empty(bytes32)`.

**`PayProcessor.vy:settle`**
- Switchboard-only. Finalises one MPP op.
- Guards: `op.exists`, `op.protocolId == RAIL_MPP` (x402 ops are blocked here), `not op.settled`.
- Computes `amount = op.amount - op.refunded` (net after any prior partial refunds).
- `pendingTotal -= amount`, `availToBridge += amount`. No USDC leaves the contract.
- Sets `op.settled = True` — op is now non-refundable.

**`PayProcessor.vy:bridge`**
- Switchboard-only. Batch-transfers up to `availToBridge` to the configured `bridgeAddress`.
- `bridgeAddress` is a Switchboard-set liquidation address (the Bridge company); cannot be redirected by
  any other caller.
- Batched off-chain to clear the Bridge company's per-transfer minimum.

**`PayProcessor.vy:refund` (MPP path)**
- Switchboard-only. MPP branch entered when `op.protocolId == RAIL_MPP`.
- Guard: `not op.settled` — settled ops cannot be refunded.
- Partial refunds are allowed: `_amount <= op.amount - op.refunded`.
- `pendingTotal -= _amount`. Vyper's safe arithmetic reverts on underflow; any divergence between the
  counter and reality surfaces as a revert, not a silent clamp.
- USDC transferred back to `op.payer` (the UserWallet).

### Accounting — shared-pool invariant

The processor holds **one commingled USDC balance** across both rails. The invariant that must hold at all
times:

```
balanceOf(processor) >= pendingTotal + availToBridge
```

- `pendingTotal` — sum of all registered-but-not-yet-settled MPP op amounts minus amounts already
  refunded. Represents **refundable escrow**.
- `availToBridge` — sum of settled-but-not-yet-bridged MPP op net amounts. **Non-refundable**.
- x402 funds occupy the implicit remainder (`balance − pendingTotal − availToBridge`).

Every operation preserves this invariant:

| Operation | `balance` | `pendingTotal` | `availToBridge` |
|---|---|---|---|
| `register` (MPP) | +amount | +amount | — |
| `register` (x402) | +amount | — | — |
| `settle` (MPP) | — | −net | +net |
| `bridge` | −amount | — | −amount |
| `refund` (MPP) | −amount | −amount | — |
| `refund` (x402) | −amount | — | — |
| x402 EIP-3009 pull | −amount | — | — |

There is no per-op USDC segregation. An under-funded processor (e.g. due to a balance bug) surfaces at
`bridge()` or `refund()` as a transfer revert.

### Key operational rules

- **Settle before bridge.** Only amounts in `availToBridge` can be bridged. The Switchboard must call
  `settle()` for each op before including its amount in a `bridge()` call.
- **Refund before settle.** Once `op.settled = True`, `refund()` reverts `"already settled"`. Partial
  refunds reduce the net that `settle()` will later move into `availToBridge`.
- **`bridgeAddress` is mandatory.** `bridge()` reverts `"bridge not configured"` if unset. Configure via
  `setBridge()` (Switchboard / timelock-gated) before the first settle cycle.
- **Dual sender registration required.** A sender must be both in `PayProcessor.senders` (`setSender`) AND
  registered in the `AgentWrapper` (`addSender`). See [AgentSenderPay](#agentsenderpay).

### Events & monitoring

| Event | Emitted by | Key fields |
|---|---|---|
| `OperationRegistered` | `register()` | `paymentId, payer, vendor, amount, rail=1` |
| `Settled` | `settle()` | `paymentId, amount` |
| `Bridged` | `bridge()` | `recipient, amount` |
| `Refunded` | `refund()` | `paymentId, payer, amount` |

- Watch `Settled → Bridged` lag for unconfirmed batches.
- `balanceOf(processor) >= pendingTotal + availToBridge` should hold after every block — alert if it does
  not.

## AgentSenderPay

`AgentSenderPay.vy` is the payments-specific agent sender. It does not custody funds or choose settlement
behavior directly. It authenticates the agent operator's payment instruction, sources exactly the signed
USDC amount from the user's wallet, pushes that USDC to the vendor, then calls `PayProcessor.vy:register`.

### Authorization model

`AgentSenderPay.vy:pay` supports the same owner-signed, any-broadcaster pattern as the other Underscore
agent senders:

- If `msg.sender` is the sender owner, the call is direct admin execution and the signature fields must be
  empty.
- Otherwise, the broadcaster supplies an owner signature over the payment payload.
- `AgentSenderPay.vy:_authenticateAccess` checks expiration, checks the per-user nonce, verifies the
  EIP-712-style digest, and increments the nonce after a valid signed call.
- `AgentSenderPay.vy:incrementNonce` is owner-only and bumps `currentNonce[userWallet]` to invalidate
  leaked or stale signed payments for that user wallet on this sender.

Nonces are scoped to `(AgentSenderPay, userWallet)` — independent from wallet pending-action state and from
other agent sender contracts registered on the same wrapper.

### Signed payload

`AgentSenderPay.vy:getPayHash` and `AgentSenderPay.vy:pay` hash the same payload: `protocolId`,
`agentWrapper`, `userWallet`, `vendor`, `amount`, `dest`, `paymentId`, `merchantRef`, `isCheque`,
rail-specific `extraData`, `vault`, `self`, `USDC`, `nonce`, `expiration`.

The domain separator is `UnderscoreAgent` with `chain.id` and `verifyingContract = self`. Including `self`
and `USDC` makes the signature specific to this sender and asset. Including `vault` is required because the
vault source controls an optional yield withdrawal before payment — it must not be broadcaster-injectable.

### Payment flow

`AgentSenderPay.vy:pay` runs three steps: authenticate (`_authenticateAccess`), source and send funds
(`_sourceAndSend`), then register (`PayProcessor.vy:register`).

`_sourceAndSend` first validates the optional `VaultSource`. A partial vault config is rejected: either
both `legoId` and `vaultToken` are set, or neither. When a vault is set, the sender calls
`AgentWrapper.vy:withdrawFromYield` and requires the withdrawn underlying asset to be USDC. Then payment is
pushed to the vendor through the wrapper:

- `isCheque = false`: `AgentWrapper.vy:transferFunds` pays the vendor as a normal approved-payee path.
- `isCheque = true`: `AgentWrapper.vy:createAndPayCheque` creates and pays a cheque atomically for a
  one-off / non-payee vendor.

The returned `moved` amount **must equal** the signed `amount` — over-moving would register more than the
operator signed; under-moving would underfund the vendor before registration.

### Registration & security notes

`AgentSenderPay` must be registered in two independent places before production use (dual-registration):

- `PayProcessor.vy:setSender` authorizes it to call `register`.
- `AgentWrapper.vy:addSender` authorizes it to move that wrapper's user funds.

The `PayProcessor` constructor can seed the processor-side allowlist at genesis, but it cannot register the
sender on each `AgentWrapper` — that is a separate switchboard-gated cutover step.

A broadcaster can choose *when* to submit a valid signed payment before expiration, but cannot change any
signed field. `AgentSenderPay` intentionally records and forwards the caller-supplied `agentWrapper` to the
processor for auditability/attribution only — processor authorization depends on `msg.sender` being an
allowed sender, never on the wrapper address.

## VendorRegistry / VendorProxy

Per-service payee infrastructure. Every verified service (a merchant / agent counterparty) gets its own
**VendorProxy** contract, minted and tracked by the **VendorRegistry**. The proxy is the address a
UserWallet authorizes as a Payee, and the only place a service's allowed payout destinations live.

### VendorRegistry — the verified-service registry (UndyHq dept 12)

Switchboard-managed factory + registry.

- `VendorRegistry.vy:createVendor` (Switchboard-only) deploys one VendorProxy from the blueprint
  (`vendorTemplate`) and records it in a 1-based registry row `{vendor, id}`. The human id (e.g.
  `"x402joker.com"`) lives on the record — there is no separate id index.
- **Liveness = registry membership.** A vendor is "live" iff `indexOfVendor(vendor) != 0`
  (`VendorRegistry.vy:isVendor`). There is **no enabled/disabled flag.** `PayProcessor.vy:register`
  refuses any vendor that is not live, so this gate applies to both rails.
- `VendorRegistry.vy:removeVendor` (Switchboard-only) is the **kill-switch** — it drops the registry row,
  so the vendor can no longer settle on either rail. Re-listing a service means a fresh `createVendor`.
- `VendorRegistry.vy:setVendorTemplate` (Switchboard-only) swaps the blueprint used for future vendors.

Both the registry and each proxy's allow-list use Underscore's 1-based dense swap-remove idiom (count
starts at 1, index 0 = absent; removal swaps the last row into the freed slot).

### VendorProxy — per-service payee (self-contained)

A minimal per-service contract. Holds funds only transiently and owns its own destination allow-list.

- **Fund flow (push-then-pull).** AgentSenderPay pushes the user's USDC into the proxy; then `PayProcessor`
  pulls it out via `VendorProxy.vy:transferToProcessor` (default `amount` sweeps the full balance) to
  settle. **Processor-only** (`assert msg.sender == _processor()`).
- **Destination allow-list.** `VendorProxy.vy:addDestination` / `removeDestination` (**Switchboard-only**)
  manage a per-vendor set; `isAllowed(dest)` is the O(1) gate `PayProcessor.vy:register` reads before
  binding an x402 payment. `addDestination` is idempotent, and the list is self-contained per vendor.
  - **MPP caveat:** `register` gates *both* rails on `isAllowed(_dest)`, but the MPP branch never uses
    `_dest` — MPP off-ramps to the Switchboard-set `bridgeAddress`, not the dest. So an MPP payment must
    still carry *some* allow-listed dest, and that dest does **not** bind where funds go. (`dest` is still
    recorded on the `Operation` for audit + future settlement confirmation.)
- **Recovery.** `VendorProxy.vy:recoverFunds` / `recoverFundsMany` (Switchboard-only) sweep stray funds
  parked on the proxy (e.g. a push with no matching `register`). `recoverFundsMany` reverts the whole batch
  if any listed asset has a zero balance.
- **`VendorProxy.vy:pullPayment` — forward-declaration, unreachable today.** A processor-only entry point
  reserved for a *future* Billing-driven pull rail (the vendor acting as a registered Payee/cheque-recipient
  that pulls from the wallet). No PayProcessor flow calls it in this release; it carries an explicit in-code
  `INTENTIONAL FORWARD-DECLARATION` comment and has **no integration coverage against real Billing yet — it
  must be tested before it is wired.**

**Trust:** every VendorProxy mutation (create, remove, allow-list edits, recovery) is Switchboard-gated;
the proxy is a minimal blueprint with no user-extensible hooks and no callbacks.

## Trust & security model

Everything sensitive routes through **`SwitchboardDelta`**, the single contract registered as the payments
departments' `isSwitchboardAddr`. It splits authority into two tiers:

- **Operational (immediate)** — governance *or* a MissionControl security signer (the server keys):
  `createVendor`/`removeVendor`, `addDestination`/`removeDestination`, `settle`, `bridge`, `refund`, and
  `pause`. No timelock.
- **Config (governance + timelock)** — `setSender`, `setBridge`, `setVendorTemplate`, and `unpause`:
  `initiate → executePendingAction` after the confirmation block; `cancelPendingAction` drops a pending one.

**Blast radius of a compromised server key.** The immediate tier is deliberately confined to
**non-redirecting** operations: `bridge` only sends to the *already-set* `bridgeAddress`, `refund` only
returns to the recorded `op.payer`, `settle` only moves escrow to `availToBridge`. Every action that could
**redirect funds** — who may pull user funds (`setSender`), where MPP lands (`setBridge`), the vendor
blueprint (`setVendorTemplate`) — is timelocked + governance-only. So a compromised security signer can
**grief / DoS** (pause the stack, remove vendors, drop destinations) but **cannot redirect funds**.
Recovery is governance-only and unpause is timelocked.

**Shared pool.** The processor holds one commingled USDC balance across both rails + refunds; correctness
rests on the invariant in [MPP rail](#mpp-rail--escrow-settle-bridge-refund) (`balanceOf ≥ pendingTotal +
availToBridge`). The rail is read from the immutable `Operation.protocolId`, so a refund can't reclassify
an op across rails.

**Counterparty risk (MPP).** Once MPP escrow is `settle`d + `bridge`d it is off-chain on Tempo with
**no on-chain guarantee** — refunds and settlement are discretionary. This is trust / counterparty risk,
not smart-contract-enforced. See [Limitations & future work](#limitations--future-work).

## Deploy & config

**Constructor (genesis).** `PayProcessor(_undyHq, _usdc, _initialBridge, _initialSender)`:

- asserts `_usdc.DOMAIN_SEPARATOR() == self._domainSeparator()` — deploying against the wrong token (e.g.
  bridged USDbC) **reverts** rather than silently shipping a dead x402 rail;
- optionally seeds the initial `bridgeAddress` and first `sender` (pass `empty` to skip). This is the one
  trusted-at-genesis write; post-deploy changes go through the timelocked switchboard.

**Registration requirements.**

- Register `VendorRegistry` at UndyHq dept **12** and `PayProcessor` at dept **13**.
- `SwitchboardDelta` must be registered as a Switchboard addr the payments depts trust, and MissionControl
  (dept 2) must be set — otherwise the security-signer path fails closed to governance-only.
- **Dual-registration for a sender:** an `AgentSenderPay` must be allow-listed on **both** sides —
  `PayProcessor.vy:setSender` *and* `AgentWrapper.vy:addSender`. Seeding `_initialSender` covers only the
  processor side; the wrapper side is per-wrapper.
- Set `bridgeAddress` (the Bridge company liquidation address) before any `bridge()`.

See `docs/deploy-checklist.md` for the broader sender / cheque production gates.

## Limitations & future work

**MPP settlement is not on-chain-verifiable.** MPP escrow is settled (non-refundable) and bridged to
an off-chain Tempo omnibus with no on-chain proof the merchant was paid; the omnibus pools funds before
settlement, so the `paymentId → merchant` link is off-chain by construction. Two hard limits: cross-chain
opacity (a bare server signature is *accountability, not verification*) and the omnibus (per-payment proof
needs per-payment Tempo settlement, not a pooled sweep).

**Proposed mitigation** (design, not built). An additive `confirmSettlement(paymentId, …, proof)` on the
processor — `operations[paymentId]` survives `bridge()`, so it can cross-check `amount` / `merchantRef` /
`dest` against the stored op — with a `confirmDeadline` that trips `pause()` if a batch goes unconfirmed.
Trust tiers, swappable via an opaque `proof`:

- **A. operator-attested + bond + pause** — accountability, works today, no new identity;
- **B. merchant co-signed** — real teeth only if the merchant self-enrolls their key;
- **C. Chainlink CCIP** — a message verified via `ccipReceive()`, emitted *atomically* with the Tempo
  payout; needs a Tempo↔Base lane. Strongest.

Full design in `AUDIT-PR76.md`.
