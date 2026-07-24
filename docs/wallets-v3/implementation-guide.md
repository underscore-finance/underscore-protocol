# User Wallet v3 — Lean PoC Implementation Guide

**Status:** IMPLEMENTATION-READY v2.4, implementing [Lean PoC Architecture v11.4](user-wallet.md).

This guide builds an experiment, not a production wallet and not an ABI/storage freeze candidate. Produce the smallest credible evidence for the permanent-wallet/extender model.

The architecture document owns the questions, trust boundaries, invariants, and deferred production work. This guide owns the PoC implementation contract, build order, evidence, and measurement method.

“Lean” describes the product surface, not a loose sketch. Section 4 intentionally fixes experimental controls so a fresh implementation agent produces comparable evidence; those choices remain provisional rather than production commitments.

## 1. Scope rules

- Build greenfield PoC code only under `contracts/walletsV3/` and `tests/walletsV3/`.
- Existing v2 code is read-only and may be deployed through the existing test fixtures as a comparison fixture.
- Use repository-pinned Vyper 0.4.3, titanoboa 0.2.7, and py-evm 0.12.1b1. Compile every v3 PoC artifact explicitly for Cancun with gas optimization; do not rely on Vyper's default EVM target. Reuse the existing v2 fixture with its source-declared optimization setting, record its actual compiler settings, and do not edit v2 for benchmark symmetry.
- EIP-1153 transient storage is required. The Base profile imports state and chain context at the pinned block into Boa's local py-evm overlay; it does not execute transactions on Anvil.
- No proxy, `delegatecall`, arbitrary-target executor, opaque protocol-call path, or fallback router.
- Forwarding bounded typed ABI calldata to a pinned extender and registered selector is allowed. An extender may call only its pinned typed Lego interfaces.
- Owner wallet administration is direct and IDLE-only. Do not build freeze, signatures, relayers, timelocks, proposals, or governance wrappers.
- Store attachments directly. Do not build ExtenderBook, LegoBook, ModuleBook, Merkle bundles, or registries.
- Support at most one effect and one capability consumption per session, with a consumed bit rather than a use counter.
- A no-effect session may open and settle without consumption only to prove safe framework overhead. It must leave no approval or persistent economic state.
- Do not add generic callbacks, receiver frameworks, hooks, or general EIP-1271.
- If a mock needs a deferred mechanism, change the mock or record the limitation; do not broaden core preemptively.
- Record material choices, failed assumptions, and scope deviations in `docs/wallets-v3/BUILDLOG.md`.

Allowed writes:

- `contracts/walletsV3/**`
- `tests/walletsV3/**`
- `docs/wallets-v3/BUILDLOG.md`
- `docs/wallets-v3/POC_RESULTS.md`
- `docs/wallets-v3/implementation-guide.md` and `docs/wallets-v3/user-wallet.md` only for an explicitly reviewed scope correction
- Ephemeral benchmark output under `/tmp`; never commit raw run output

No CI workflow edit is part of this PoC. The documented commands are manual acceptance commands unless a later reviewed scope correction adds CI.

## 2. Deliverables and evidence records

The complete PoC produces only:

1. PoC contracts and small shared interfaces/types.
2. Functional and targeted adversarial tests.
3. One gas benchmark file and one manually controlled threshold file.
4. `BUILDLOG.md` containing decisions, surprises, and scope deviations.
5. `POC_RESULTS.md` containing:
   - pass/fail for each of the eight architecture questions;
   - the evidence ids and pytest node ids supporting each answer;
   - gas and bytecode measurements;
   - unresolved security and integration risks;
   - omitted features;
   - a keep/redesign/abandon recommendation;
   - work required before any production specification or audit.

There is no Step-0 package, artifact manifest, candidate id, freeze manifest, canonical-vector suite, sign-off chain, or ratification output.

Use this compact BUILDLOG entry shape:

```text
BL-NNN · date · step/evidence id
Decision or failed assumption:
Reason:
Affected files/evidence:
Scope impact:
```

Use this compact POC_RESULTS question shape:

```text
Q1 · PASS | FAIL | INCONCLUSIVE
Evidence ids:
Test node ids:
Measurements:
Residual risks/limitations:
Disposition:
```

Final gate evidence must come from a clean commit. Dirty-tree measurements are diagnostic and must be labeled as such.

## 3. Planned layout

```text
contracts/walletsV3/
  UserWalletV3.vy
  UserWalletConfigV3.vy
  interfaces/
    IUserWalletV3.vyi
    IUserWalletConfigV3.vyi
    IWalletExtenderV3.vyi
    IYieldLegoV3.vyi
    IDebtLegoV3.vyi
    IFutureActionLegoV3.vyi
    IOperatorProtocolV3.vyi
    IX402Helper.vyi
  types/
    WalletV3Types.vy
  extenders/
    YieldExtender.vy
    DebtExtender.vy
    PaymentExtender.vy
    FutureActionExtender.vy
  rails/
    X402Helper.vy
  mocks/
    MockYieldLego.vy
    MockDebtLego.vy
    MockFutureActionLego.vy
    MockVault.vy
    MockDebtProtocol.vy
    MockOperatorProtocol.vy
    MockFutureActionProtocol.vy
    MockBrokenConfig.vy
    MockAdversarialConfig.vy
    MockBenchmarkExtender.vy
    MockGasBoundary.vy
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

DebtExtender v1/v2, Debt Lego v1/v2, PaymentExtender v1/v2, and x402 helper v1/v2 are separate deployments of the same listed source unless a failing requirement justifies different source. A successor must use a different extender address and a strictly higher version. Equal runtime codehashes across versions are allowed and expected for same-source redeployment; attachment id, address, and version define version identity.

`tests/walletsV3/conftest.py` may deploy small bounded inline EVM return-data shims for malformed and oversized low-level-call cases that Vyper's typed ABI cannot express. Document each shim next to its bytecode; it is test machinery, not a new wallet component.

Do not add a component merely to resemble an earlier architecture draft. An unplanned addition requires a failing retained requirement and a BUILDLOG entry. The future-action files above are planned evidence, not scope expansion.

## 4. Frozen PoC implementation contract

These choices are fixed for the PoC so implementation results are comparable. They are not production ABI or storage commitments. A change after implementation begins requires a BUILDLOG entry and rerun of all affected evidence.

### 4.1 Trust and compatibility model

| Component | PoC assumption |
|---|---|
| Wallet owner | Trusted root; fixed for the deployment |
| Manager/caller | Untrusted outside Config-authorized fields and caps |
| Config | Owner-selected policy code; may be broken or revert operational calls |
| Extender | May be malicious; core must contain it to the routed, Config-authorized action vocabulary |
| Lego | Trusted typed protocol adapter; address and codehash pinned |
| x402 helper | Trusted narrow digest/state adapter; address and codehash pinned |
| Mock protocol | Representative behavior only unless a test names it adversarial |
| ERC-20 | Standard exact-return token for supported flows; reentrant and malformed tokens are adversarial tests |

The malicious-extender exercise proves policy/effect containment, not calldata-to-request fidelity for malicious extender code. The typed extender translates calldata into the session request and remains reviewed code. A malicious extender may select a different request that the real caller's Config policy still authorizes, but it must not escape that policy, attachment, consumer, target, amount, beneficiary, or effect class.

Fee-on-transfer, rebasing, ERC-777 hooks, and tokens that omit boolean return values are unsupported. Record, do not generalize around, any limitation they expose.

### 4.2 Fixed types and PoC bounds

| Item | PoC choice |
|---|---|
| Attachment id | `uint256`, id 0 is invalid, first id is 1 |
| Family id | `bytes32` |
| Family version | `uint32`, nonzero and strictly increasing |
| Action id | `uint16` |
| Effect class | `uint8`: INVALID=0, SPEND=1, LIABILITY=2, ASSET_RELEASE=3, AUTHORITY=4 |
| Consumer mode | `uint8`: INVALID=0, LEGO=1, CORE=2, NONE=3 |
| Phase | `uint8`: IDLE=0, DIRECT=1, ADMIN=2, DISPATCHING=3, ACTIVE=4, SETTLING=5, COMMITMENT=6 |
| Lifecycle | `uint8`: UNSET=0, ACTIVE=1, DRAIN_ONLY=2 |
| Commitment id / semantic hash | `bytes32` |
| Maximum attachments | 16 |
| Maximum routed selectors per attachment | 8 |
| Maximum DRAIN_ONLY exit selectors per attachment | 4 |
| Maximum typed extender calldata | 1,024 bytes including selector |
| Maximum managers in a Config | 4 |
| Maximum recipients in a Config | 8 |
| Maximum tokens in a Config | 8 |
| Maximum action ids in a Config | 16 |
| Config marker/wallet probe gas | 30,000 per call |
| Config probe return | exactly one 32-byte ABI word |
| EIP-1271 signature argument | bounded to 256 bytes and ignored by the rail-only decision |

The Config interface marker is:

```text
keccak256("underscore.user-wallet-config-v3-poc-v1")
```

The wallet uses bounded static `raw_call` probes for the marker and `wallet()`. Each exact-word probe uses `max_outsize=33`, then requires `len(returndata) == 32` before decoding; `max_outsize=32` would silently truncate an oversized return. A candidate with no code, a wrong marker, wrong wallet, revert, malformed/oversized return, or exhausted probe gas is rejected. The wallet never calls the old Config during replacement. Apply the same 33-byte capture and exact-length check to operational Config authorization and exact-return ERC-20 calls.

All v3 deployment fixtures must use one compiler wrapper that explicitly selects:

```text
Vyper 0.4.3 · optimizer=gas · evm_version=cancun
```

The gas harness asserts and emits those settings. Cancun is the deliberate minimum compiler target because the design requires EIP-1153 but should not depend on Prague-only code generation. Vyper 0.4.3's CLI default and Boa 0.2.7's installed py-evm execution VM are Prague, so the report records compiler target and execution rules separately; an implicit compiler configuration is invalid evidence.

### 4.3 Boot and Config policy

The wallet deploys with a fixed nonzero owner and no Config.

Before the first Config is installed:

- `replaceConfig` and read-only views are the only successful wallet calls.
- Transfer, attachment, routing, session, and commitment calls fail closed.

`UserWalletConfigV3` is constructor-bound immutably to one wallet and has no initializer, fallback, or rebinding function. Its constructor initializes the bounded manager, recipient, token, action, and per-call-cap policy. The PoC Config has no policy mutation API; replacement installs fresh constructor policy. The wallet proves only the candidate's marker and current `wallet()` answer at runtime; absence of mutable rebinding is a property of the reviewed PoC Config source, not something generic bytecode introspection can establish.

Operational methods are:

```text
configInterfaceMarker() -> bytes32
wallet() -> address
authorizeTransfer(realCaller, recipient, token, amount) -> bool
authorizeSession(realCaller, attachmentId, selector, actionEnvelope) -> bool
```

All are views. Wallet requires the two authorization calls to return an exact ABI `True` word. The Config marker and `wallet()` remain readable in `MockBrokenConfig`, while its operational authorization methods always revert.

Config constructor policy uses these bounded records:

```text
TokenPolicy:
  token · maxTransferAmount · maxSessionAmount

ActionPolicy:
  actionId · maxAmount
```

The constructor receives bounded manager and recipient arrays plus bounded `TokenPolicy` and `ActionPolicy` arrays. Duplicates and zero addresses fail. `authorizeTransfer` requires an owner/manager caller, allowed recipient/token, nonzero amount, and the token transfer cap. `authorizeSession` requires an owner/manager caller, allowed action id, allowed nonzero resource token when one exists, action and token session caps, and an allowed beneficiary whenever the beneficiary is neither the wallet nor the envelope's nonzero Lego consumer. A CORE route whose beneficiary is the attachment Lego, such as operator grant/revoke, therefore includes that Lego in the Config recipient allowlist. Both payment modes are CORE routes with a zero consumer, so every merchant/payment destination must also be in that allowlist.

### 4.4 Attachment records and succession

Core receives an attachment request but derives all stored dependency codehashes itself.

The input records are:

```text
RouteSpec:
  selector: bytes4
  actionId: uint16
  effectClass: uint8
  consumerMode: uint8

AttachmentRequest:
  familyId: bytes32
  version: uint32
  extender: address
  lego: address
  authorityTarget: address
  x402Helper: address
  routes: DynArray[RouteSpec, 8]
  exitSelectors: DynArray[bytes4, 4]
```

An attachment stores:

```text
familyId · version · lifecycle
extender address · extender codehash
optional Lego address · Lego codehash
optional fixed authority target · target codehash
optional x402 helper address · helper codehash
selector → actionId/effectClass/consumerMode declarations
exit-selector subset
```

`consumerMode` is one of `LEGO`, `CORE`, or `NONE`. `LEGO` requires the attachment's pinned Lego as consumer. `CORE` requires a zero consumer and can be consumed only by a named narrow core primitive. `NONE` requires a zero consumer and can never be consumed; it exists only for the empty-session measurement.

Rules:

- Every nonzero dependency must have code.
- Selector/action/effect/consumer-mode declarations are unique within the record.
- Exit selectors must be declared selectors.
- A family has at most one ACTIVE attachment.
- A successor has a strictly higher version and different extender address.
- Same runtime codehash as the predecessor is allowed.
- Before installing a successor, core clears every predecessor current route and marks the predecessor DRAIN_ONLY.
- Active selector collisions across families fail.
- DRAIN_ONLY execution admits only that attachment's exit selectors.
- Extender, Lego, fixed authority target, and helper codehashes are checked again at each use.
- Identity/dependency fields never change; lifecycle changes only ACTIVE → DRAIN_ONLY.

For the Debt family, `repayClose` and operator revoke are exit selectors. Borrow, collateral removal, and operator grant cannot open through DRAIN_ONLY.

### 4.5 Dispatch and session state machine

There is no fallback router. The two top-level routing functions are:

```text
execute(typedExtenderCalldata)
executeAttached(attachmentId, typedExtenderCalldata)
```

Both return no opaque data. Tests query typed state after execution.

`execute`:

1. Requires IDLE, an installed Config, calldata length 4..1,024, and a current ACTIVE route for the first four bytes.
2. Enters DISPATCHING before any external call.
3. Records the real caller, Config snapshot, attachment id, selector, calldata hash, mapped action id, and a new session nonce.
4. Rechecks the extender codehash and forwards the unchanged bounded calldata to the pinned extender.

`executeAttached` performs the same setup but requires the supplied attachment to be DRAIN_ONLY and the selector to be one of its registered exits.

The common request/consumption record is:

```text
ActionEnvelope:
  actionId: uint16
  effectClass: uint8
  consumer: address
  target: address
  resource: address
  maxAmount: uint256
  beneficiary: address
  actionDataHash: bytes32
```

The extender's typed function decodes its calldata and calls `openSession(ActionEnvelope)`. Core then:

1. Requires DISPATCHING, the exact routed extender, matching attachment/action/selector, and no prior open for the frame.
2. Rechecks the relevant Lego/authority-target/helper codehashes.
3. Derives the semantic hash from the canonical envelope below.
4. Calls the snapshotted Config's `authorizeSession`.
5. Stores the transient capability and starting balance/reservation data.
6. Grants an approval only for a SPEND capability with a nonzero Lego consumer.
7. Enters ACTIVE.

When the extender returns, core requires that a session was opened, enters SETTLING, clears any Wallet→Lego approval, applies the token-loss bound, clears transient session data, and returns to IDLE.

Only a `NONE` route may return with `consumed == false` as a successful no-effect session: no core primitive/effect ran, any approval is cleared, and no persistent economic state changed. A `LEGO` or `CORE` route must consume its capability before the extender returns or the entire execution reverts. The `v3.session.empty` benchmark measures the `NONE` path through a dedicated `MockBenchmarkExtender` and measurement-only `BENCHMARK_EMPTY` route; adversarial behavior remains isolated in `MaliciousExtender`.

Every stateful top-level path acquires its phase before its first external call:

```text
IDLE → DIRECT → IDLE
IDLE → ADMIN → IDLE
IDLE → DISPATCHING → ACTIVE → SETTLING → IDLE
IDLE → COMMITMENT → IDLE
```

`COMMITMENT` wraps `syncExternalPull`, `expireExternalExact`, `settleReservedTransfer`, and `refundReservedTransfer`. Commitment creation occurs inside ACTIVE and consumes internally.

### 4.6 Capability and semantic hash

The transient capability is:

```text
actionId · effectClass · consumer · target · semanticHash ·
resource · maxAmount · beneficiary · consumed
```

- `consumer` is the pinned Lego for general `consumeCapability`.
- `consumer == empty(address)` denotes a core-consumed or no-effect action and never receives a token approval.
- `target` is the protocol/token/operator-protocol effect target and is never overloaded with consumer identity.

Supported effect classes are `SPEND`, `LIABILITY`, `ASSET_RELEASE`, and `AUTHORITY`.

The canonical outer hash is:

```text
ACTION_DOMAIN = keccak256("underscore.wallet-v3-action-v1")

semanticHash = keccak256(abi_encode(
  ACTION_DOMAIN,
  chain.id,
  wallet,
  attachmentId,
  selector,
  actionId,
  effectClass,
  consumer,
  target,
  resource,
  maxAmount,
  beneficiary,
  actionDataHash,
))
```

The PoC fixture vocabulary and action-data preimages are:

| Id | Action | Effect | Mode | Target / resource / beneficiary | `actionDataHash` preimage |
|---:|---|---|---|---|---|
| 1 | `YIELD_DEPOSIT` | SPEND | LEGO | vault / input token / wallet | `vault, token, amount, wallet` |
| 10 | `DEBT_BORROW` | LIABILITY | LEGO | debt protocol / borrow asset / wallet | `protocol, asset, amount, wallet` |
| 11 | `DEBT_REPAY_CLOSE` | SPEND | LEGO | debt protocol / payment asset / wallet position owner | `protocol, paymentAsset, maxPaymentAmount, wallet` |
| 12 | `DEBT_REMOVE_COLLATERAL` | ASSET_RELEASE | LEGO | debt protocol / collateral asset / wallet | `protocol, asset, amount, wallet` |
| 13 | `DEBT_OPERATOR_GRANT` | AUTHORITY | CORE | operator protocol / zero / Debt Lego | `protocol, lego, True` |
| 14 | `DEBT_OPERATOR_REVOKE` | AUTHORITY | CORE | operator protocol / zero / Debt Lego | `protocol, lego, False` |
| 20 | `PAY_EXTERNAL_EXACT` | SPEND | CORE | pinned USDC / USDC / destination | `commitmentId, token, amount, destination, validAfter, validBefore, nonce, helper, digest` |
| 21 | `PAY_RESERVED_TRANSFER` | SPEND | CORE | token / token / destination | `commitmentId, token, totalAmount, destination, settlementOperator` |
| 30 | `FUTURE_RELEASE_BOND` | ASSET_RELEASE | LEGO | future mock protocol / released asset / wallet | `protocol, asset, amount, wallet` |
| 255 | `BENCHMARK_EMPTY` | LIABILITY | NONE | zero / zero / wallet | `keccak256("empty")` |

Each `actionDataHash` is `keccak256(abi_encode(the listed typed fields))`.

For Lego-consumed actions, the Lego calls `consumeCapability(ActionEnvelope)` with the actual common fields plus its independently derived action-data hash before effect. Core recomputes the outer hash and requires exact equality. For operator and payment actions, core derives both hashes directly from the narrow function's typed arguments and consumes internally.

Before Config authorization, core requires the route-declared action id, effect class, and consumer mode, and every SPEND route requires `maxAmount > 0`. LEGO routes require `consumer == attachment.lego`. CORE and NONE routes require a zero consumer; CORE capabilities may be consumed only by their named narrow primitive, while NONE capabilities cannot be consumed. Operator primitives additionally require their fixed action id, `target == attachment.authorityTarget`, and `beneficiary == attachment.lego`. External-exact and reserved-transfer primitives likewise require their fixed action ids; external exact also requires the attachment helper's immutable token and helper address. No extender-supplied action id, effect class, consumer, authority target, helper, or consumption mode may override the route or attachment.

The vocabulary table fixes PoC fixtures and test encodings; it is not a hardcoded generic-action registry in `UserWalletV3`. Only the named CORE primitives know their action ids. This distinction is what allows Step 5 to add action 30 through a LEGO route without changing core.

`BENCHMARK_EMPTY` uses LIABILITY only as a non-SPEND placeholder so the framework-overhead measurement never performs approval setup. Its NONE consumer mode—not the placeholder effect class—enforces that it cannot consume a capability or produce an effect.

The core does not compare an extender-supplied opaque hash. It compares a core-recomputed hash. The independent test encoder in Step 2 must not import the production hash helper.

### 4.7 Token and approval rules

Supported ERC-20 calls require exactly one 32-byte ABI word and boolean `True` where applicable. Missing, short, oversized, false, or malformed returns fail closed.

For a SPEND capability with a nonzero Lego consumer:

1. Snapshot `startBalance`, `startReserved`, and `startAvailable = max(startBalance - startReserved, 0)`.
2. Require `0 < maxAmount <= startAvailable`; a zero amount or insufficient availability fails before an approval or Lego call.
3. Require the existing Wallet→Lego allowance is zero.
4. Grant exactly `maxAmount`.
5. The Lego consumes before pulling.
6. The Lego may grant only an exact protocol allowance and must clear it before returning.
7. SETTLING clears Wallet→Lego approval before other checks.
8. Require final wallet token loss does not exceed the granted amount.

The core enforces approval cleanup and maximum input loss. Beneficiary delivery is bound in the semantic hash before effect and proved from the mock protocol/token state in tests. Extenders and Legos must retain no user token balance after success.

Reentrant calls encounter a non-IDLE phase and fail. A cleanup failure reverts the complete transaction, including the protocol effect and approval changes.

### 4.8 Payment commitments

PaymentExtender has two typed authorization functions. Creation occurs only during its ACTIVE routed session, requires `0 < amount <= available(token)`, and consumes internally after exact comparison with the authorized action.

#### External exact: Base USDC EIP-3009

This is the onchain external-pull leg used by the x402 experiment. It is not a test of x402 HTTP request/facilitator wire compatibility.

The pinned profile is:

```text
chain id: 8453
Base block: 34,642,981
block hash: 0xcf93c5606c59a6e58a0524e0c46fd79c9cb94c8e876ac4dc5657e5f6af52d662
timestamp: 1,756,075,309
baseFeePerGas: 774,425 wei
USDC: 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
name/version: "USD Coin" / "2"
DOMAIN_SEPARATOR: 0x02fa7265e7c5d81118673727957699e4d68f74cd74b7db77da710fe8a2c7834f
TRANSFER_WITH_AUTHORIZATION_TYPEHASH:
  0x7c7c6cdb67a18743f49ec6fa9b35f50d52ed05cbed4cc592e13b44501c1a2267
```

`tests/conf_env.py::FORKS["base"]["block"]` is the canonical fork pin and `config/BluePrint.py::TOKENS["base"]["USDC"]` is the canonical token address. Changing either requires a reviewed scope correction and produces a new evidence profile.

The Base fixture asserts all values above before testing. It may fund the wallet from `config/BluePrint.py::WHALES["base"]["USDC"]`; funding is setup and is never measured.

The first Base-profile action is a constants preflight. A block hash, timestamp, `baseFeePerGas`, USDC constant, or GasPriceOracle mismatch stops the run. Record it in `BUILDLOG.md` and request a reviewed documentation scope correction; never auto-update, omit, or loosen the assertion.

`X402Helper` is constructor-pinned to that USDC. It derives:

```text
structHash = keccak256(abi_encode(
  USDC.TRANSFER_WITH_AUTHORIZATION_TYPEHASH(),
  wallet,
  destination,
  amount,
  validAfter,
  validBefore,
  nonce,
))

digest = keccak256(concat(
  0x1901,
  USDC.DOMAIN_SEPARATOR(),
  structHash,
))
```

The PoC calls the bytes-signature overload:

```text
transferWithAuthorization(
  from,
  to,
  value,
  validAfter,
  validBefore,
  nonce,
  signature,
)
```

USDC requires `block.timestamp > validAfter` and `block.timestamp < validBefore`. Wallet validity mirrors those strict boundaries.

Rail-only `isValidSignature(digest, signature)`:

- Is a static/view answer and requires wallet phase IDLE.
- Requires `msg.sender == commitment.token`.
- Returns `0x1626ba7e` only for the exact live digest within the strict time window.
- Ignores the bounded signature bytes; the stored commitment is the authorization.
- Returns a non-magic value for every other case.

Narrow ERC-165 support returns true for the ERC-165 and ERC-1271 interface ids and false for `0xffffffff`; it does not widen the signature perimeter.

The commitment stores id, digest, token, amount, destination, validity, nonce, helper address/codehash, and state. Commitment id, digest, and external-authorization nonce are permanently non-reusable. Creation also requires USDC `authorizationState(wallet, nonce) == False`.

- Permissionless sync requires `authorizationState(wallet, nonce) == True`, marks the commitment used/terminal, then releases the reservation.
- Permissionless expiry requires `block.timestamp >= validBefore` and authorization state false.
- A true state cannot be expired as unused and must sync.
- The wallet never returns MAGIC for the EIP-3009 cancellation digest, so external cancellation cannot create an ambiguous true state in this PoC.
- Helper codehash is rechecked on creation, sync, and expiry.

#### Reserved transfer: representative MPP settlement

MPP means Machine Payments Protocol. This branch models a metered session's reserved balance and cumulative partial settlement only. It does not implement or claim compliance with MPP HTTP challenges, credentials, receipts, signatures, or a production payment-method specification.

The commitment stores id, token, total, remaining, destination, settlement operator, and state.

- Only the stored operator may partially settle.
- State and reservation update before token transfer; token failure reverts both.
- Settlement always uses the stored destination and cannot exceed remaining.
- Only the owner may refund the remaining reservation.
- Refund releases availability and transfers no token.
- Terminal ids cannot be reauthorized or replayed.

Every wallet-originated transfer, approval, action, and new commitment uses:

```text
available(token) = max(balanceOf(wallet) - reserved(token), 0)
```

An external pull may make `reserved > balance` until sync. That is intentionally conservative.

## 5. Provisional external surface

Names are fixed for the PoC tests but remain non-production.

### Administration and views

```text
owner()
config()
phase()
replaceConfig(newConfig)
attachExtender(attachmentRequest)
attachment(attachmentId)
currentRoute(selector)
availableBalance(token)
reserved(token)
commitment(commitmentId)
```

`replaceConfig` and `attachExtender` are owner-only and enter ADMIN before external validation. `attachExtender` requires a Config already installed.

### Custody and routing

```text
transferFunds(recipient, token, amount)
execute(typedExtenderCalldata)
executeAttached(attachmentId, typedExtenderCalldata)
```

### Session primitives

```text
openSession(request)
consumeCapability(actualEnvelope)
setDebtOperator(enabled, actualEnvelope)
createExternalExact(fields, actualEnvelope)
createReservedTransfer(fields, actualEnvelope)
```

Grant is ACTIVE-only. Revoke is admitted from the ACTIVE route or the exact Config-authorized DRAIN_ONLY revoke route.

### Payment lifecycle

```text
isValidSignature(digest, signature)
supportsInterface(interfaceId)
syncExternalPull(commitmentId)
expireExternalExact(commitmentId)
settleReservedTransfer(commitmentId, amount)
refundReservedTransfer(commitmentId)
```

No generalized rail interface, Config settlement callback, fee, policy snapshot, notification, or extender reconciliation is implemented.

## 6. Architecture-question traceability

| Question | Primary steps | Required evidence |
|---|---|---|
| Q1 stable custody/identity across replacements | 1, 3, 4 | S1-E5, S3-E6, S3-E7, S4-E8 |
| Q2 escape from broken Config | 1, 3 | S1-E3, S1-E5, S3-E6 |
| Q3 contained typed extender succession | 2, 3, 5 | S2-E1..E6, S3-E6, S5-E1..E4 |
| Q4 allowance and non-allowance effects | 2, 3 | S2-E3..E5, S3-E1..E4 |
| Q5 fixed wallet-originated authority | 3 | S3-E3..E5, S3-E7 |
| Q6 external-exact and metered reserved payments | 4, 5 | S4-E1..E9, S5-E5..E7 |
| Q7 old version closes wallet-keyed position | 3 | S3-E6, S3-E7 |
| Q8 materially cheaper direct transfer | 1, gas | S1-E6 and `v2/v3.transfer.repeat` gate |

`POC_RESULTS.md` uses Q1..Q8 as its top-level rows and cites these evidence ids plus exact pytest node ids.

## 7. Build sequence

### Step 1 — custody, Config replacement, and transfer gas

Build:

- Fixed owner, fail-closed pre-Config state, and direct IDLE-only Config installation/replacement.
- Constructor-bound Config with bounded owner/manager recognition, recipient/token/action allowlists, and per-call caps.
- Direct ERC-20 transfer and `availableBalance`.
- Transient phases IDLE, DIRECT, and ADMIN.
- Explicit compiler wrapper and settings assertion.
- `MockGasBoundary` and the local-versus-fork transaction-boundary calibration.

Required evidence:

- **S1-E1:** owner, allowed manager, and unauthorized caller transfer cases.
- **S1-E2:** before Config, only replacement and views succeed; a fresh transaction reports phase IDLE with numeric value zero; transfer, attachment, routing, session, and commitment paths fail.
- **S1-E3:** wrong-wallet, wrong-marker, no-code, reverting, malformed-return, oversized-return, and gas-exhausting candidates are rejected; the reviewed `UserWalletConfigV3` exposes no successful initializer or rebinding path.
- **S1-E4:** Config/token failure and reentrancy roll back cleanly; balances, reservation, Config pointer, and phase behavior are correct.
- **S1-E5:** a current Config whose operational calls all revert can be replaced; marker and wallet views remain readable; replacement starts fresh policy and moves no wallet asset.
- **S1-E6:** the local-versus-fork transaction-boundary calibration passes, then the paired v2/v3 initialized, independent-transaction, cross-block owner-to-allowed-recipient ERC-20 transfer benchmark runs using the existing v2 fixtures.

Exit: functional tests pass; the final clean-commit pinned-Base-state model has v3 transfer below 190,000 tx-equivalent gas and cheaper than paired v2.

### Step 2 — attachments, one session, and yield

Build:

- Bounded append-only attachment metadata, core-derived codehashes, collision rejection, and current-family routing.
- `execute`, `executeAttached`, and DISPATCHING → ACTIVE → SETTLING.
- One transient capability, exact approval, cleanup, and token-loss settlement.
- `YieldExtender`, `MockYieldLego`, and one-deposit `MockVault`.
- Dedicated `MockBenchmarkExtender` with one measurement-only empty-session entry.

Required evidence:

- **S2-E1:** only the wallet-routed extender opens once for the mapped attachment/selector/action; direct extender calls, wrong attachment, wrong selector/action, and nested dispatch fail.
- **S2-E2:** only the pinned consumer consumes once; an unconsumed no-effect session succeeds with no approval or persistent economic change.
- **S2-E3:** capability binds attachment, selector, action, effect, Lego consumer, vault target, token, amount, and wallet beneficiary; cross-action/domain collisions fail.
- **S2-E4:** zero SPEND amount and insufficient availability fail before approval or Lego entry; otherwise the Lego consumes before pulling, approval is exact, begins at zero, clears before success, and final loss cannot exceed the grant.
- **S2-E5:** shares mint directly to the wallet; Lego/extender retain no token or allowance.
- **S2-E6:** invalid bounds, duplicate or invalid route declarations, invalid effect/consumer modes, invalid exit subsets, no-code dependencies, dependency codehash mismatch, active-family selector collisions, and non-increasing successor versions fail.
- **S2-E7:** empty-session and minimal-yield gas are measured with correct transaction boundaries.
- **S2-E8:** one independent inline test encoder reproduces the yield semantic hash without importing production hashing code.

Exit: functional/security tests pass. Empty-session cost is compared with the 60,000 review target and yield cost receives a preliminary accept/redesign disposition; neither blocks later evidence collection.

### Step 3 — debt, fixed operator authority, and old-version exit

Build:

- `DebtExtender`, `MockDebtLego`, `MockDebtProtocol`, and `MockOperatorProtocol`.
- Semantic borrow, repay/close, and remove-collateral actions.
- Core-constructed operator grant/revoke template.
- Automatic DRAIN_ONLY succession and exact-version exit.
- Separate v1/v2 deployments of the same Debt source.

Required evidence:

- **S3-E1:** `removeCollateral(MAX)` fails when only one unit is authorized; wrong effect/action/resource hashes fail.
- **S3-E2:** borrowed and released assets go directly to the wallet; Lego/extender retain none.
- **S3-E3:** grant/revoke can target only the attachment-pinned mock protocol and Debt Lego; arbitrary target/operator/calldata fails.
- **S3-E4:** direct operator use outside a session, wrong extender, wrong attachment, and every alternate authority-using Lego path fail without capability consumption.
- **S3-E5:** revocation succeeds through an authorized ACTIVE session after Config replacement.
- **S3-E6:** open a v1 wallet-keyed position; install a broken operational Config; replace it directly; attach a higher-version v2 at a different address; verify every v1 current route is gone and new v1 actions fail.
- **S3-E7:** close the old position and revoke its operator through v1's exact Config-authorized DRAIN_ONLY exits while wallet address and protocol owner remain unchanged.

Exit: all position-survival, version-succession, exit, and authority tests pass.

### Step 4 — external-exact and representative MPP payments

Build:

- `PaymentExtender`, narrow `X402Helper`, and separate v1/v2 deployments.
- `reserved(token)` accounting and both commitment modes.
- Config-allowlisted merchant/payment destinations for both CORE payment routes.
- Rail-only EIP-1271 plus narrow ERC-165.
- COMMITMENT-phase sync, expiry, partial settlement, and owner refund.
- Non-reusable commitment ids/digests and terminal records.

Required evidence:

- **S4-E1:** commitment creation fails outside ACTIVE, from the wrong extender/attachment, for a zero amount or non-allowlisted payment destination, or when any authorized field differs from the core-derived commitment.
- **S4-E2:** in the pinned-Base-state profile, real USDC's bytes-signature `transferWithAuthorization` pulls only the exact live commitment.
- **S4-E3:** wrong caller, unknown/wrong-field digest, malformed or oversized signature argument, non-IDLE wallet, equality at `validAfter`, equality at `validBefore`, expired, and terminal cases never return MAGIC.
- **S4-E4:** successful unsynced pull cannot expire as unused; permissionless sync reaches the correct terminal state; an unused expired authorization releases only at/after `validBefore`; cancellation digest is never authorized.
- **S4-E5:** terminal external-exact ids/digests/nonces and terminal reserved-transfer ids cannot be reauthorized.
- **S4-E6:** reserved-transfer settlement requires the stored operator, uses the stored destination, cannot over-settle, updates state before transfer, and resists reentrancy; only owner may refund and refund transfers no token.
- **S4-E7:** reserved funds cannot be transferred, approved, spent by yield/debt actions, or committed twice; reserve the full balance and test yield deposit and debt repayment.
- **S4-E8:** create both commitments, replace Config, attach PaymentExtender/helper v2, then sync through the stored v1 helper and settle/refund successfully.
- **S4-E9:** helper codehash mismatch, token failure, malformed token return, and failed lifecycle calls preserve commitment/reservation state.

Exit: payment tests pass and each measured lifecycle receives a preliminary accept/redesign disposition. Results call the branches “Base USDC EIP-3009 external exact” and “representative MPP reserved transfer,” not full protocol implementations.

### Step 5 — targeted attacks, future action, and findings

Required evidence:

- **S5-E1:** wrong extender, attachment, Lego, selector, action, effect class, target, resource, semantic hash, beneficiary, and excessive amount fail.
- **S5-E2:** capability reuse, cross-action replay, nested session, and stale-session attempts fail.
- **S5-E3:** malicious extender attempts each primitive without an open session and cannot exercise general wallet authority.
- **S5-E4:** reentrant ERC-20, Config, and commitment behavior fail closed; approval cleanup failure and malformed ERC-20 returns revert cleanly.
- **S5-E5:** reserved-fund transfer/spend attempts, external-exact replay, and validity boundaries fail.
- **S5-E6:** reserved-transfer unauthorized caller, over-settlement, terminal-id reauthorization, and refund replay fail.
- **S5-E7:** old-version current-route use, non-exit DRAIN_ONLY use, active-family collision, and dependency codehash mutation fail.
- **S5-E8:** after recording the Step-4 core source and runtime bytecode hashes, add `FUTURE_RELEASE_BOND` using ASSET_RELEASE through only the planned FutureAction extender/Lego/protocol, Config fixture, and tests; do not modify `UserWalletV3.vy`, shared types, shared interfaces, or existing extenders/Legos, and prove both recorded core hashes remain unchanged.
- **S5-E9:** measure core runtime bytecode compiled with the gate settings.

Exit:

- Targeted tests pass.
- Core runtime size is compared with the 16,384-byte review target.
- `POC_RESULTS.md` records Q1..Q8 pass/fail/inconclusive and all accept/redesign decisions.

## 8. Gas and fee method

### 8.1 Required scenarios

| Scenario | Profile | Result role |
|---|---|---|
| `v2.transfer.repeat` / `v3.transfer.repeat` | pinned Base state / Boa | `gate`: v3 `<190k` and cheaper than paired v2 |
| `v2.transfer.repeat` / `v3.transfer.repeat` | local | `diagnostic` only |
| `v3.session.empty` | local | `review`: compare with `<60k` target |
| `control.yield.protocol_direct` / `v3.session.yield_minimal` | local | `review` |
| `v3.x402.authorize` / `v3.x402.sync` | pinned Base state / Boa only | `review` |
| `v3.mpp.authorize` / `partial_settle` / `refund` | local | `review` |

Debt/operator actions require functional and security tests but no PoC gas gate.

The pinned-Base-state gas profile requires:

```text
WEB3_ALCHEMY_API_KEY
ETHERSCAN_API_KEY
anvil on PATH
```

The repository imports `ETHERSCAN_API_KEY` for every pytest profile; a placeholder is sufficient for tests that do not fetch verified contracts. Base fork evidence requires working Base RPC credentials.

The harness fails fast if a prerequisite, chain id, fork block, USDC address, compiler setting, py-evm VM, or expected USDC/GasPriceOracle selector or view is wrong.

### 8.2 Transaction boundaries

For every Boa measurement, including the pinned-Base-state profile, reuse the transaction-boundary methodology in `tests/gas_profiling/test_transfer_gas_profile.py`:

- Run gas tests standalone and never under xdist.
- Lock prior storage as previous-transaction state.
- Clear warm account/slot journals and transient storage.
- Prewarm only transaction-origin, transaction-target, and fork-valid precompiles.
- Advance a block before each cross-block repeat.
- Preserve setup/measurement order explicitly.

Do not copy only the arithmetic and omit the Boa journal reset. A result without independent-transaction behavior is invalid.

In the repository harness, Anvil serves state at the pinned Base block and `boa.fork(anvil_uri)` imports that state into a local `Env`. Existing v2 fixtures, v3 deployments, and measured calls live only in Boa's py-evm overlay. They are not Anvil transactions and produce no RPC receipt. The Base-state profile must therefore read gross execution, refund, and calldata from the isolated top-level Boa computation and derive the authoritative gate value with §8.3.

Before accepting the first Base result, run a transaction-boundary calibration with `MockGasBoundary` under both local and Base-state profiles. After the same setup and boundary sequence, require the chain-independent gross/refund observations to match: an initialized nonzero slot cleared in a new transaction has a 4,800 raw refund, a later zero-to-nonzero write is priced as a clean-slot write rather than a same-transaction dirty write, only transaction-origin, transaction-target, and fork-valid precompiles begin warm, and no storage slot begins warm. If the forked account database cannot support the journal reset reliably, the Base gate fails; record the incompatibility in `BUILDLOG.md` and request a reviewed narrow harness correction rather than weakening isolation.

Keep setup unmeasured, create an explicit transaction boundary before each paired call, and advance one block before the measured cross-block repeat. The harness asserts and records Boa's installed Prague VM. A separate `NetworkEnv`/web3 deployment-and-receipt harness is outside this PoC because it could not reuse the required v2 fixture stack. Any later receipt experiment is optional cross-check evidence only and requires a reviewed scope correction; it cannot replace or silently redefine this gate.

The v2 comparator reuses the repository's existing v2 session fixtures and matches:

```text
owner caller · already-allowed recipient · same ERC-20 and amount ·
initialized steady state · independent transaction · next block
```

The report notes that the lean v3 Config intentionally omits v2 production policy work.

### 8.3 Tx-equivalent gas

For modeled/local non-creation type-2 transactions with no access list:

```text
tokens = zero_calldata_bytes + 4 * nonzero_calldata_bytes
standard_intrinsic = 21_000 + 4 * tokens
pre_refund = gross_execution + standard_intrinsic
applied_refund = min(raw_refund, floor(pre_refund / 5))
standard_total = pre_refund - applied_refund
eip7623_floor = 21_000 + 10 * tokens
tx_equivalent = max(standard_total, eip7623_floor)
minimum_executable_gas_limit = max(pre_refund, eip7623_floor)
```

This retains EIP-3529's refund cap and explicitly applies the EIP-7623 calldata floor used by the post-Isthmus pinned-Base-state profile. Boa's call-level computation does not include transaction intrinsic gas or produce a receipt, so `tx_equivalent` from this formula is the authoritative pinned-Base-state gate metric. Refunds are applied only after execution and cannot make execution fit within a smaller gas limit; EIP-7623 independently requires reserving its floor. The serialized fee envelope therefore uses `minimum_executable_gas_limit`, not post-refund `tx_equivalent`, as its gas limit. The local profile uses the same calculation as diagnostic evidence. Both profiles report the py-evm execution VM and whether the EIP-7623 floor bound.

### 8.4 Base fee model

Gas is the hard gate; sponsored fee is review evidence.

For each Base scenario, construct and record one deterministic, fully serialized type-2 transaction envelope:

```text
chainId=8453 · nonce=0 · maxPriorityFeePerGas=0 ·
maxFeePerGas=pinned block base fee · gasLimit=minimum_executable_gas_limit ·
to=measured entry contract · value=0 · data=exact calldata ·
accessList=[] · deterministic nonzero signature fields
```

Read and assert the block hash, timestamp, and `baseFeePerGas` values pinned in §4.8 through the upstream RPC; do not use Boa's synthetic overlay block for the fee input. With zero priority fee and `maxFeePerGas` equal to that value, it is also the modeled effective L2 gas price.

Use Base GasPriceOracle `0x420000000000000000000000000000000000000F`:

- `getL1Fee(serializedTransaction)` for the modeled L1 data fee.
- `getOperatorFee(tx_equivalent)` for the operator fee; record zero rather than omitting it.

At Base block 34,642,981, `getOperatorFee(uint256)` exists and `getOperatorFee(190000)` returns zero. The harness repeats that preflight and fails if the selector disappears or the pinned result changes.

Report:

```text
modeledL2Fee = tx_equivalent * effectiveL2GasPrice
modeledSponsoredFee = modeledL2Fee + modeledL1Fee + operatorFee
```

This is a deterministic fork-time model, not an observed production receipt. Label it `modeled`, never `measured`.

### 8.5 Result schema and thresholds

Each result records:

- Scenario id, role, and semantic success assertions.
- Source commit and dirty flag.
- Vyper/titanoboa/py-evm versions, optimizer, compilation target, execution VM, and execution mode.
- Fork chain id/block/timestamp, upstream `baseFeePerGas`, and canonical token/dependency addresses.
- Caller, entry point, token, amount, and initialized/cold-state description.
- Calldata token counts, standard intrinsic, pre-refund gas, EIP-7623 floor, minimum executable gas limit, and tx-equivalent gas.
- Gross execution and raw/applied refund from the isolated Boa computation.
- For Base: `executionMode=boa-pyevm-overlay`, the pinned upstream state block, and an explicit `receipt=not-applicable` marker.
- Raw calldata or hash.
- For Base: deterministic serialized transaction or hash, gas price, modeled L1 fee, operator fee, and modeled total sponsored fee.
- Absolute/percentage delta for paired comparisons.
- Feature-parity note.

`thresholds.json` has this fixed shape:

```json
{
  "schemaVersion": 1,
  "scenario": "v3.transfer.repeat",
  "profile": "base",
  "metric": "tx_equivalent",
  "max": 190000
}
```

The relational “cheaper than paired v2” assertion uses the same run's paired result. No benchmark or command may create, overwrite, widen, or approve its own threshold. Raw JSON remains in `/tmp`; the reviewed summary goes in `POC_RESULTS.md`.

No receipt hash or receipt `gasUsed` is expected from this harness. If a separately reviewed network-mode cross-check is ever added, store it under a distinct optional field and never substitute it for `tx_equivalent`.

### 8.6 Commands to support

Use environment variables instead of adding a repository-global pytest CLI option:

```text
python -m pytest --fork=local --ignore=tests/walletsV3/gas tests/walletsV3/ -q
python -m pytest --fork=base tests/walletsV3/test_x402.py -q
GAS_PROFILE=1 WALLET_V3_GAS_OUTPUT=/tmp/wallet-v3-poc-local.json python -m pytest --fork=local tests/walletsV3/gas/test_poc_gas.py -q -s
GAS_PROFILE=1 WALLET_V3_GAS_OUTPUT=/tmp/wallet-v3-poc-base.json python -m pytest --fork=base tests/walletsV3/gas/test_poc_gas.py -q -s
```

The gas module skips unless `GAS_PROFILE=1`, requires exactly its own collected gas tests, and writes only to the absolute `/tmp` path provided by `WALLET_V3_GAS_OUTPUT`.

## 9. Final validation

Run serially:

```text
python -m pytest --fork=local --ignore=tests/walletsV3/gas tests/walletsV3/ -q
python -m pytest --fork=base tests/walletsV3/test_x402.py -q
GAS_PROFILE=1 WALLET_V3_GAS_OUTPUT=/tmp/wallet-v3-poc-local.json python -m pytest --fork=local tests/walletsV3/gas/test_poc_gas.py -q -s
GAS_PROFILE=1 WALLET_V3_GAS_OUTPUT=/tmp/wallet-v3-poc-base.json python -m pytest --fork=base tests/walletsV3/gas/test_poc_gas.py -q -s
python -m pytest --fork=local -ra
```

The final full local suite is a regression check, not new PoC scope. Do not run the standalone gas module in the same pytest process as other tests.

Before declaring completion:

- `git diff --check` passes.
- All planned files exist and no unplanned files lack a BUILDLOG justification.
- Every evidence id has at least one exact pytest node id or an explicit FAIL/INCONCLUSIVE explanation.
- Q1..Q8 each have a disposition.
- Final gate evidence is from a clean commit.
- Raw benchmark output is not committed.

## 10. Explicit non-goals

The canonical deferred-feature list is [Architecture §11](user-wallet.md#11-explicitly-deferred).

Guide-specific prohibitions:

- Do not add a factory, deployment system, migration tool, proxy, registry, generalized executor, generalized signature perimeter, callback framework, or production rail adapter.
- Do not add a real Ripe/Morpho, x402 HTTP/facilitator, or MPP wire-protocol integration.
- Do not add a CI workflow or modify existing v2 source/tests for the comparison.
- Do not turn benchmark outputs, provisional types, or helper encodings into freeze artifacts.
- Do not expand the future-action exercise beyond proving one existing effect class without core changes.

## 11. Scope-stop rule

If an addition does not directly answer one of Q1..Q8 or satisfy a named evidence id, do not build it. Record it as deferred in `POC_RESULTS.md`.

If a named evidence item cannot pass without a proxy, arbitrary executor, general callback/signature perimeter, production governance mechanism, or unplanned trust expansion, stop that step. Record the failure and request architecture review rather than widening core.

The PoC is complete when it produces a credible answer, not when it resembles a production wallet.
