# User Wallet v3 — Lean PoC Implementation Guide

**Status:** DRAFT v2.1, implementing [Lean PoC Architecture v11.1](user-wallet.md).

This guide builds an experiment, not a production wallet and not an ABI/storage freeze candidate. Produce the smallest credible evidence for the permanent-wallet/extender model.

## 1. Scope rules

- Build greenfield PoC code only under `contracts/walletsV3/` and `tests/walletsV3/`.
- Existing v2 code is read-only and may be deployed as a comparison fixture.
- Use the repository-pinned Vyper 0.4.3, Cancun, and EIP-1153 transient storage.
- No proxy, `delegatecall`, arbitrary-target executor, or opaque protocol-call path.
- Forwarding typed ABI calldata to a pinned extender and registered selector is allowed; that extender may call only its pinned typed Lego interfaces.
- Owner administration is direct and IDLE-only. Do not build freeze, signatures, relayers, timelocks, proposals, or governance wrappers.
- Store attachments directly. Do not build ExtenderBook, LegoBook, ModuleBook, Merkle bundles, or registries.
- Implement one action and one capability per session, with a consumed bit rather than a use counter.
- Do not add generic callbacks, receiver frameworks, hooks, or general EIP-1271.
- If a mock needs a deferred mechanism, change the mock or record the limitation; do not broaden core preemptively.
- Record material choices and failed assumptions in `docs/wallets-v3/BUILDLOG.md`.

Allowed writes:

- `contracts/walletsV3/**`
- `tests/walletsV3/**`
- `docs/wallets-v3/BUILDLOG.md`
- `docs/wallets-v3/POC_RESULTS.md`
- These two documents only for an explicitly reviewed scope correction
- Ephemeral benchmark output under `/tmp` or the CI artifact directory; never commit raw run output

## 2. Deliverables

The complete PoC produces only:

1. PoC contracts and small shared interfaces/types.
2. Functional and targeted adversarial tests.
3. One gas benchmark file and one manually controlled threshold file.
4. `BUILDLOG.md` containing decisions, surprises, and scope deviations.
5. `POC_RESULTS.md` containing:
   - pass/fail for each of the eight architecture questions;
   - gas and bytecode measurements;
   - unresolved security and integration risks;
   - omitted features;
   - a keep/redesign/abandon recommendation;
   - work required before any production specification or audit.

There is no Step-0 package, artifact manifest, candidate id, freeze manifest, canonical-vector suite, sign-off chain, or ratification output.

## 3. Planned layout

```text
contracts/walletsV3/
  UserWalletV3.vy
  UserWalletConfigV3.vy
  interfaces/
    IUserWalletV3.vyi
    IUserWalletConfigV3.vyi
    IWalletExtenderV3.vyi
    IWalletLegoV3.vyi
    IX402Helper.vyi
  types/
    WalletV3Types.vy
  extenders/
    YieldExtender.vy
    DebtExtender.vy
    PaymentExtender.vy
  rails/
    X402Helper.vy
  mocks/
    MockYieldLego.vy
    MockDebtLego.vy
    MockVault.vy
    MockDebtProtocol.vy
    MockOperatorProtocol.vy
    MockBrokenConfig.vy
    MaliciousExtender.vy
    MockReentrantToken.vy
    MockMalformedToken.vy

tests/walletsV3/
  conftest.py
  test_transfer_and_config.py
  test_yield_session.py
  test_debt_and_operator.py
  test_extender_lifecycle.py
  test_x402.py
  test_mpp.py
  test_security.py
  test_future_action.py
  gas/
    test_poc_gas.py
    thresholds.json
```

Do not add a component merely to resemble an earlier architecture draft. An addition requires a failing retained requirement and a `BUILDLOG.md` entry.

## 4. Provisional surface

Names and encodings are implementation choices and are not frozen.

### Core administration

- Deploy with a fixed owner and no Config.
- `replaceConfig(newConfig)` — owner-only, IDLE → ADMIN; validates nonzero code, interface marker, and immutable `config.wallet() == self` using bounded static calls. Config has no initializer.
- `attachExtender(record)` — owner-only, IDLE → ADMIN; append-only metadata. A family successor atomically clears the predecessor's routes and marks it `DRAIN_ONLY`.
- No `freeze`, `unfreeze`, manual `setDrainOnly`, detach, or emergency path.

### Custody and routing

- `transferFunds(recipient, token, amount)` for ERC-20 only.
- `availableBalance(token)`.
- Current selector routing to an `ACTIVE` attachment.
- `executeAttached(attachmentId, typedExtenderCalldata)` for exact Config-authorized `DRAIN_ONLY` exits.

### Session primitives

- `openSession(request)` — exact routed extender only.
- Exact Wallet→Lego approval grant, always bounded by the session-start `availableBalance(token)`; settlement bounds token loss by that grant.
- `consumeCapability(actualSemanticFields...)` — pinned Lego only and before effect.
- One active-Extender-only operator grant/revoke entry point; core validates and consumes internally, then constructs the call granting only the pinned Debt Lego authority on the pinned mock protocol.

The single capability contains only the fields required by the examples:

```text
actionId · effectClass · Lego/target · semanticHash ·
resource · maxAmount · beneficiary · consumed
```

Supported `effectClass` values are `SPEND`, `LIABILITY`, `ASSET_RELEASE`, and `AUTHORITY`.

### Payment commitments

- Create `EXTERNAL_EXACT` or `RESERVED_TRANSFER` only through an active-Extender-only wallet entry point; core matches the authorized request, requires `amount <= availableBalance(token)`, and consumes internally.
- Rail-only `isValidSignature` for a live exact x402 digest.
- `syncExternalPull` and `expireExternalExact` through the attachment-pinned x402 helper.
- `settleReservedTransfer` checks the stored operator directly; `refundReservedTransfer` is owner-only.
- Core views for commitment state and `reserved(token)`.
- Terminal ids/digests cannot be reauthorized.

No MPP helper, generalized rail interface, Config settlement callback, fee, policy snapshot, notification, or extender reconciliation is implemented.

## 5. Build sequence

### Step 1 — custody, Config replacement, and transfer gas

Build:

- Fixed owner and direct IDLE-only Config installation/replacement.
- Constructor-bound Config with owner/manager recognition, recipient/token/action allowlists, and per-call caps.
- Direct ERC-20 transfer and `availableBalance`.
- Minimal transient phases: IDLE, DIRECT, ADMIN.

Required evidence:

- Owner, allowed manager, and unauthorized caller cases.
- Wrong-wallet Config and initializer/rebind attempts fail.
- Failed Config or token calls roll back cleanly.
- A current Config whose authorization/policy calls all revert can still be replaced; its immutable `wallet()` and interface-marker views remain readable.
- Replacement starts with fresh policy state and never moves wallet assets.
- Paired v2/v3 initialized, independent-transaction, cross-block ERC-20 transfer benchmark.

Exit: functional tests pass; v3 transfer is below 190,000 tx-equivalent gas and cheaper than paired v2.

### Step 2 — attachments, one session, and yield

Build:

- Append-only attachment metadata, codehash checks, collision rejection, and current-family routing.
- DISPATCHING → ACTIVE → SETTLING phases.
- One consumed capability, exact approval, cleanup, and input-loss/beneficiary postconditions.
- `YieldExtender`, `MockYieldLego`, and one-deposit `MockVault`.

Required evidence:

- Only the routed extender opens the exact authorized session.
- Only the pinned Lego consumes the capability, once.
- Capability binds vault, token, amount, and wallet beneficiary.
- Lego consumes before pulling.
- Vault shares mint directly to the wallet.
- All allowances clear; Lego/extender retain no token balance.
- Active-family selector collisions fail.
- Empty-session and minimal-yield gas are measured.
- A small inline test proves that the core-derived authorization matches the Lego-reported actual fields, using one independent test encoder as a cross-check; no canonical vector artifact is created.

Exit: functional/security tests pass. Empty-session cost is compared with the 60,000 review target and yield cost receives a preliminary accept/redesign disposition; neither blocks later evidence collection.

### Step 3 — debt, fixed operator authority, and old-version exit

Build:

- `DebtExtender`, `MockDebtLego`, `MockDebtProtocol`, and `MockOperatorProtocol`.
- Semantic borrow, repay/close, and remove-collateral capabilities.
- One core-constructed operator grant/revoke template.
- Automatic `DRAIN_ONLY` succession and exact-version normal exit.

Required evidence:

- `removeCollateral(MAX)` fails when only one unit is authorized.
- Borrowed/released assets go directly to the wallet.
- Operator grant/revoke can target only the pinned protocol and Debt Lego; arbitrary target/operator/calldata fails.
- Direct use of that operator outside a session, use by the wrong extender, and every alternate authority-using Lego path fail without capability consumption.
- Revocation still succeeds through an authorized session after Config replacement.
- Open a v1 wallet-keyed position.
- Install a Config whose authorization/policy calls always revert, replace it directly with a fresh working Config, then attach v2.
- Verify every v1 current route was removed and opening through v1 fails.
- Close the old position through v1's exact Config-authorized exit while wallet address and protocol owner remain unchanged.

Exit: all position-survival, version-succession, exit, and authority tests pass.

### Step 4 — x402 and MPP

Build:

- `PaymentExtender` and narrow `X402Helper`.
- `reserved(token)` accounting and both commitment modes.
- Rail-only EIP-1271.
- External-pull sync/expiry; direct-caller MPP partial settlement and owner refund.
- Non-reusable commitment ids/digests and terminal tombstones or records.

Required evidence:

- Commitment creation fails outside ACTIVE, from the wrong extender, or when any request field differs from the consumed capability.
- On pinned Base, real USDC `transferWithAuthorization` pulls only the exact live commitment.
- Unknown, wrong-field, not-yet-valid, expired, or terminal digests never return MAGIC.
- A successful but unsynced pull cannot later be expired as unused; sync reaches the correct terminal state.
- Terminal x402 digest reauthorization fails.
- MPP settlement requires the stored operator, uses the stored destination, and cannot over-settle.
- An unauthorized caller cannot settle or refund; only owner may refund the remainder; neither terminal transition replays.
- Reserved funds cannot be transferred, granted as a session approval, spent by yield/debt actions, or committed twice; reserve the full balance and test both yield deposit and debt repayment attempts.
- Create commitments, replace Config and attach PaymentExtender v2, then actually sync x402 and settle/refund MPP successfully.

Exit: payment tests pass and each measured lifecycle receives a preliminary accept/redesign disposition.

### Step 5 — targeted attacks, future action, and findings

Required attacks:

- Wrong extender, wrong Lego, wrong semantic hash, wrong beneficiary, excessive amount, and capability reuse.
- Nested session and reentrant ERC-20 behavior.
- Malicious extender attempts a primitive without an open session.
- Approval cleanup failure and malformed ERC-20 return behavior.
- Transfer attempts against reserved funds.
- x402 replay and expiry-boundary cases.
- MPP unauthorized caller, over-settlement, and refund replay.
- Old-version current-route access and active-family selector collision.

Future-compatibility exercise:

- Add one new mock action using an existing effect class without modifying the core action engine.

Exit:

- Targeted tests pass.
- Core runtime size is measured against the 16,384-byte review target.
- `POC_RESULTS.md` records explicit pass/fail and accept/redesign decisions.

## 6. Gas method

Required scenarios:

| Scenario | Profile | Result role |
|---|---|---|
| `v2.transfer.repeat` / `v3.transfer.repeat` | pinned Base | `gate`: v3 `<190k` and cheaper than paired v2 |
| `v2.transfer.repeat` / `v3.transfer.repeat` | local | `diagnostic` only |
| `v3.session.empty` | local | `review`: compare with `<60k` target |
| `control.yield.protocol_direct` / `v3.session.yield_minimal` | local | `review` |
| `v3.x402.authorize` / `v3.x402.sync` | pinned Base only | `review` |
| `v3.mpp.authorize` / `partial_settle` / `refund` | local | `review` |

The harness runs only scenarios valid for the selected profile; in particular, it never substitutes a local mock for the Base x402 result. Every emitted result labels itself `gate`, `review`, or `diagnostic`. Pinned Base is authoritative for the transfer gate and sponsored-fee reporting.

Debt/operator actions require functional and security tests but no PoC gas gate.

Commands to support:

```text
python -m pytest --fork=local --ignore=tests/walletsV3/gas tests/walletsV3/ -q
python -m pytest --fork=base tests/walletsV3/test_x402.py -q
python -m pytest -p no:xdist --fork=local tests/walletsV3/gas/test_poc_gas.py -q -s --gas-output=/tmp/wallet-v3-poc-local.json
python -m pytest -p no:xdist --fork=base tests/walletsV3/gas/test_poc_gas.py -q -s --gas-output=/tmp/wallet-v3-poc-base.json
```

For non-creation transactions without access lists:

```text
intrinsic = 21_000 + 4 * zero_calldata_bytes + 16 * nonzero_calldata_bytes
pre_refund = gross_execution + intrinsic
applied_refund = min(raw_refund, floor(pre_refund / 5))
tx_equivalent = pre_refund - applied_refund
```

Each result records:

- Scenario id and semantic success assertions.
- Source commit/dirty flag.
- Vyper version, optimizer, EVM target, and fork chain/block.
- Caller, entry point, token, amount, and initialized/cold-state description.
- Gross execution, raw/applied refund, intrinsic, and tx-equivalent gas.
- Raw calldata or its hash plus zero/nonzero byte counts.
- For Base: effective L2 gas price, measured L1 fee, and total sponsored fee in wei.
- Absolute/percentage delta for paired comparisons.
- Feature-parity note: lean v3 Config intentionally omits v2 production policy work.

`thresholds.json` contains only the direct-transfer hard ceiling. The relational “cheaper than paired v2” assertion uses the same run's paired result. No benchmark or CI job may create, overwrite, widen, or approve its own threshold. Raw JSON remains in `/tmp` or CI artifacts; the reviewed summary goes in `POC_RESULTS.md`.

## 7. Explicit non-goals

Do not build:

- Wallet freeze/unfreeze or any Config-bypassing emergency path.
- Production ABI/storage freeze, migration tools, factory, deployment system, or cutover plan.
- Native ETH transfer, owner transfer, multisig/AA, relayed signatures, session keys, or UserOperation benchmarks.
- Security signers, timelocks, proposals, governance, ExtenderBook, LegoBook, or ModuleBook.
- General EIP-1271, generic callbacks, receiver frameworks, or after-session hooks.
- HARD_REVOKE/detach, registry CLOSED, cleanup machinery, or Merkle emergency routes.
- Config state migration, recovery state machines, candidate lifecycle, or cross-Config accounting.
- Policy snapshots, fees, settlement callbacks, notifications, retry checkpoints, pricing, points, or yield tracking.
- NFTs, swaps, liquidity, rewards, or generalized wallet-call vocabulary.
- Real Ripe/Morpho integration; representative mocks suffice.
- Candidate ids, artifact manifests, schema suites, freeze generators, sign-off files, or ratification.
- Exhaustive audit testing; Step 5 is a focused attack suite.

## 8. Scope-stop rule

If an addition does not directly answer one of the eight architecture questions, do not build it. Record it as deferred in `POC_RESULTS.md`.

The PoC is complete when it produces a credible answer, not when it resembles a production wallet.
