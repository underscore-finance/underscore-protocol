# Simplified User Wallet Action Architecture — Codex

**Status:** Governing architecture for the incremental user-wallet action track;
not authorized for implementation

**Document authority:** Owner-selected governing architecture as of 2026-07-24.
This selection resolves document precedence only. It does not authorize contract
changes, deployment, migration, or use of funds.

**Goal:** Apply the useful extender, session, capability, and Lego patterns from
the wallet PoC without replacing the existing permission and limits system.

**Migration design:** Out of scope

**History note:** This simplified proposal replaced an earlier untracked Codex
north-star draft. That earlier full text was overwritten before it was committed
and is not recoverable from repository history. Section 19 records the known
architectural dispositions, but it is not a substitute for the lost reasoning.

**Change-control rule from this revision forward:** A future conceptual
replacement must use a new file and mark this document `SUPERSEDED`; it must not
overwrite this file. Material revisions within this direction must append an
entry to section 22. No document authorizes contract changes without an explicit
owner decision.

---

## 1. Executive recommendation

The wallet should be extensible in one deliberately narrow dimension:

> New action identities and reviewed implementations may be registered. New
> kinds of wallet authority may not be registered.

The proposed system keeps:

- the existing `UserWalletConfig`;
- the existing Sentinel and wallet-backpack responsibilities;
- existing manager activation, expiration, limits, cooldowns, allowed assets,
  allowed Legos, swap restrictions, approved-vault rules, payees, cheques,
  whitelists, and owner/security controls;
- the wallet as the custody and accounting boundary;
- the PoC lifecycle of wallet-opened sessions, extender acknowledgement,
  consumer capability consumption, wallet locking, and wallet settlement; and
- capability-aware Legos that pull from the wallet only after consumption.

It adds:

- open-ended `actionId` values;
- one small immutable `ActionSpec` per action ID;
- one codehash-pinned extender per action ID;
- one routed LegoBook address bound to the wallet generation;
- immutable-by-ID Lego succession for routed and position-bearing consumers;
- a closed permission mask selected from a finite reviewed vocabulary;
- explicit action-ID opt-in for delegated managers;
- a bounded extender `prepare` call;
- exact `planBytes` forwarded from extender to Lego;
- exact spend amounts resolved by the wallet and returned when the Lego
  consumes the capability; and
- a small closed set of settlement modes that reuse existing wallet post-action
  machinery.

It does **not** add:

- open-ended permission semantics;
- a policy DSL;
- a standalone ActionCodec contract;
- a generic effect language;
- generic proof classes or verifier plugins in the first version;
- mutable route versions;
- `FOLLOW_RECOMMENDED`;
- generic accounting profiles;
- generic position-family machinery; or
- arbitrary target-and-calldata execution.

The design promise is intentionally bounded:

> A new action can avoid a wallet change only when existing permissions,
> limits, spend primitives, session mechanics, and settlement modes already
> describe it.

That limitation is a security property.

---

## 2. Why simplify

The earlier north-star design made several things independently extensible:

- action identities;
- permission identities;
- implementation routes;
- codecs;
- effect templates;
- authority templates;
- risk templates;
- position-family records;
- proof adapters; and
- accounting profiles.

Each mechanism was individually defensible, but their combinations created a
large specification, more governance surfaces, more hash relationships, and
more ways for implementation details to disagree.

The existing wallet already has a strong policy system. Sentinel currently
groups many specific actions into a few meaningful authorities:

```text
transfer
yield management
buying and selling
debt management
liquidity management
claiming rewards
```

It also already enforces the limits that distinguish safe from unsafe use:

```text
activation and expiry
transaction counts and cooldowns
per-transaction / per-period / lifetime USD limits
allowed assets
allowed Legos
approved yield opportunities
recipient and payee restrictions
swap count and slippage
cheque creation and payment limits
zero-price rules
```

The simpler design treats that system as an asset to reuse, not infrastructure
to replace.

---

## 3. The boundary: open actions, closed authority

| Concept | Extensibility |
|---|---|
| `actionId` | Open-ended registry data |
| Extender implementation | New immutable action registration |
| Lego / consumer implementation | Wallet-bound LegoBook plus its existing reviewed add/confirm process and no in-place repointing for routed or position-bearing IDs |
| Permission categories | Closed wallet/Sentinel vocabulary |
| Limit semantics | Existing closed Sentinel behavior |
| Spend authority | Closed wallet-created primitives |
| Settlement modes | Small closed wallet enum |
| Session phases | Closed wallet enum |
| Security and administration | Existing owner/security-action/system paths only |

A new action may combine existing permissions:

```text
yield.deposit                 → YIELD
yield.rebalance               → YIELD
yield.rebalance-with-swap     → YIELD | TRADE
debt.deleverage               → DEBT | TRADE
claim-and-restake             → REWARDS | STAKING
bridge-and-deposit            → CROSS_CHAIN | YIELD
```

Registration cannot define what `YIELD`, `TRADE`, or another permission means.
It can only select already-supported bits.

Unknown bits fail closed.

---

## 4. What remains unchanged

### 4.1 Direct wallet and payment rails

These paths remain direct and outside the action registry initially:

- `transferFunds`;
- ETH/WETH conversion;
- payee payments and pulls;
- cheques;
- `preparePayment`;
- Billing integration;
- freezing and ejection;
- migration and recovery;
- manager, payee, cheque, and whitelist administration; and
- backpack and security configuration.

The routed engine is not a replacement for every wallet function.

### 4.2 Existing Config data

The existing manager records remain authoritative:

- `ManagerSettings`;
- `GlobalManagerSettings`;
- `ManagerLimits`;
- `LegoPerms`;
- `SwapPerms`;
- `TransferPerms`;
- allowed assets;
- allowed Legos; and
- manager period data.

The only proposed Config addition is a bounded set of routed `actionId` values
explicitly approved for a delegated manager and, if desired, a global manager
ceiling.

The lifecycle check belongs at the Config storage boundary, not only in
HighCommand. `UserWalletConfig` already stores its wallet address. For every
manager action-ID mutation, it should call a read-only wallet getter for that
wallet's bound ActionRegistry, then read lifecycle from that exact registry.
HighCommand remains the owner-facing coordinator, but neither HighCommand nor
Migrator can bypass Config's stored-set rule.

The bounded action-ID array is treated as a set:

- duplicates reject;
- an ID already present in both the stored and proposed sets is retained without
  lifecycle revalidation;
- an ID absent from the stored set but present in the proposed set is an
  addition and must currently be `ENABLED`; and
- an ID may always be removed.

Therefore an unrelated manager edit—such as changing a USD cap—preserves a
retained `EXIT_ONLY` grant. Once that ID is removed, a later transaction treats
it as an addition and cannot restore it while it remains `EXIT_ONLY`. Atomic
reordering is not removal and re-addition because membership, not array
position, defines the comparison.

New managers and migration-applied settings use the same addition validation.
Wallet creation begins with no routed action IDs for the starter manager because
the wallet and its bound registry do not yet exist when the Config constructor
runs; routed grants are added only after `setWallet`.

This adds one explicit Config → wallet getter → ActionRegistry read path, plus
bounded set-difference work. Its ABI, bytecode, and gas belong in Phase 0
measurement.

### 4.3 Existing Sentinel behavior

Sentinel keeps:

- caller classification;
- owner-versus-manager behavior;
- manager activation and expiry;
- transaction count and cooldown checks;
- asset restrictions;
- Lego restrictions;
- current permission booleans;
- USD limits;
- swap counters and slippage;
- approved-vault checks; and
- post-transaction counter updates.

The new routed path should reuse those helpers rather than create a second
policy engine.

#### 4.3.1 The routed path requires an explicit two-stage policy API

The current `checkSignerPermissionsAndGetBundle` interface performs caller,
transaction-count, cooldown, permission, allowed-asset, and allowed-Lego checks
in one call because today's typed wallet functions know their asset and Lego
arguments before authorization.

The routed path does not know the complete asset and Lego sets until the locked
`prepare` call returns. It therefore cannot reuse that ABI unchanged. Version
one needs a small explicit split within the existing
Config → ActionDataProvider → Sentinel path:

1. **Caller and action authorization:** load the existing action-data bundle;
   preserve owner/manager classification, activation and expiry, transaction
   count and cooldown behavior; check the manager's explicit `actionId`; and
   evaluate every required permission bit.
2. **Prepared-policy validation:** after exact prepare decoding, apply the
   existing specific-manager and global allowed-asset and allowed-Lego rules to
   the complete prepared sets.

The exact function names are a Phase 0 ABI decision. The important constraint is
that both stages call the existing Config/Sentinel data and internal policy
helpers. They do not create a second manager record, duplicate counters, or
quietly reinterpret owner behavior. Post-action manager accounting remains one
call after execution.

This is a real interface and bytecode change to `UserWalletConfig`,
`ActionDataProvider`, and Sentinel/backpack—not merely a new wallet wrapper—and
must be measured as such.

`ACTION_DATA_PROVIDER` is immutable in each current `UserWalletConfig`, while
the Config's `sentinel` address is replaceable through the existing backpack
validation path. Version one should use that asymmetry deliberately:

- the immutable ActionDataProvider is a thin, mechanically stable adapter that
  gathers the existing Config data and forwards exact routed-policy inputs;
- the replaceable Sentinel owns the substantive stage-one and stage-two policy
  interpretation;
- direct and routed Sentinel entry points remain separate enough that replacing
  a routed-policy implementation cannot silently reinterpret the untouched
  direct path; and
- bytecode and regression tests cover the Config, ActionDataProvider, and
  Sentinel changes as three distinct risk surfaces.

The thin provider's forwarding ABI is itself an immutable wallet-generation
boundary. Sentinel replaceability does not help when a future policy decision
needs a Config datum or authorization stage that the provider cannot express.
Version one therefore freezes an action-agnostic `PolicyContextV1`, not a
yield-deposit-shaped projection. Phase 0B must define the smallest complete
context that includes:

- wallet, Config, caller, and action identity;
- every field of the current `ws.ActionData`, `wcs.ManagerData`,
  `wcs.ManagerSettings`, and `wcs.GlobalManagerSettings` structures on every
  routed stage, using the same empty/default values current code uses when a
  signer has no manager record, rather than a hand-picked subset for the first
  action;
- an explicit stage discriminator;
- bounded prepared asset and Lego sets for stage two; and
- the wallet-bound registry identities required to interpret those fields.

This is an unconditional field-set guarantee, not a claim that every field
governs every action. The provider forwards the same complete base context at
both stages; Sentinel decides which fields are relevant. The provider only
gathers and forwards these mechanically.

The `V1` suffix identifies the context shape frozen into one wallet/Config/
provider generation. It does not imply an in-place V1-to-V2 upgrade path. A
different context shape requires a reviewed provider, Config, and wallet
generation.

Action-specific classifications use only the fixed typed fields already
admitted by ActionSpec, the replaceable Sentinel, or another already-approved
bounded source. This does not add generic policy parameters, and those
classifications do not become new provider branches.

Version one deliberately does not include an opaque reserved extension blob.
An untyped blob cannot manufacture future Config data that the immutable
provider does not know how to gather, and interpreting it would obscure the
closed-policy boundary. A proposed action may be enabled in a wallet generation
only when all of its caller and prepared-policy requirements fit that
generation's versioned context and two-stage API. Otherwise registration or
enablement fails closed and the proposal returns for a reviewed core/new-wallet-
generation change.

This does not make routed actions retrofittable into an already-deployed wallet.
Existing wallet bytecode has no routed entry point, session kernel, or bound
ActionRegistry/routed-LegoBook getters, and its Config cannot replace the
ActionDataProvider. Routed execution therefore exists only in the new wallet and
Config generation. Migration remains out of scope.

### 4.4 Existing wallet settlement

The wallet keeps:

- yield-profit realization;
- asset registration and deregistration;
- price and USD-value accounting;
- fee ceilings;
- loot and deposit-point updates;
- manager counter updates;
- beneficiary and custody expectations; and
- approval cleanup.

---

## 5. Permission model

### 5.1 Provisional permission vocabulary

The exact future taxonomy is a pending research and owner decision. The
architecture requires a finite set, not this exact list.

The current system already supports:

```text
TRANSFER
YIELD
TRADE
DEBT
LIQUIDITY
REWARDS
```

Likely future candidates to evaluate are:

```text
PAYMENT
PAYMENT_COMMITMENT
STAKING
DERIVATIVES
CROSS_CHAIN
GOVERNANCE
```

These candidates are not free aliases. Existing permissions are represented in
`LegoPerms` and related Config structures, so each new category may require
Config storage/ABI changes plus Sentinel/backpack code. No candidate becomes
supported merely because a spare bit exists in a conceptual mask. Phase 0 must
measure Config and policy-contract size for the exact initial taxonomy and for
the reserved expansion capacity.

The distinction between `PAYMENT` and `PAYMENT_COMMITMENT` is potentially
important:

- `PAYMENT` authorizes a bounded payment now.
- `PAYMENT_COMMITMENT` authorizes creating a future obligation, reservation,
  recurring instruction, cheque, or pull authority.

Payment modes do not automatically need separate permission categories.

### 5.2 When permissions should split

Two actions should require different permissions when at least one is true:

- an owner would reasonably delegate them independently;
- they create materially different financial or custody risk;
- one creates a future obligation or persistent position;
- one exposes a different class of counterparty;
- compromising one should not expose the other;
- their required limits are fundamentally different; or
- one can create liabilities rather than only move existing assets.

Actions should share a permission when their differences are safely expressed
through:

- `actionId`;
- allowed assets;
- allowed Legos;
- approved recipients;
- amount limits;
- slippage;
- cooldowns;
- settlement mode; or
- action-specific typed arguments.

### 5.3 Composite permission checks are cumulative

The routed Sentinel path must check every required bit:

```text
if requiredPermissions contains YIELD:
    require canManageYield

if requiredPermissions contains TRADE:
    require canBuyAndSell

if requiredPermissions contains DEBT:
    require canManageDebt
```

It must not use a mutually exclusive `if / elif` chain for composite masks.

The current fallback behavior for an unrecognized action must not carry into
the routed path. Unknown, empty when prohibited, or unsupported masks return
`False`.

### 5.4 New actions must not silently expand manager grants

Broad permission categories create an important governance question:

```text
manager already has YIELD
governance registers a new YIELD action
```

The manager must not gain that action automatically.

The conservative first design requires:

```text
manager possesses every required permission bit
AND
actionId is explicitly approved in manager Config
AND
actionId is permitted by the global manager ceiling, if configured
```

For routed actions, an empty manager action list means **no routed actions**,
not all actions.

The proposed default, pending owner decision 6, is that an owner with existing
`canOwnerManage` authority may use globally executable actions without a
per-owner action-ID list. This is not yet an approved rule.

This adds one narrow action-ID control without introducing open-ended policy
semantics.

---

## 6. The small ActionRegistry

The first design uses a fixed-width identifier:

```text
actionId: bytes32
```

The recommended derivation is `keccak256` of a canonical, versioned action name,
with the human-readable preimage published in registry events and interfaces.
The identifier width is therefore known when sizing the bounded Config list.

Each action ID has one immutable specification and one separately mutable
lifecycle record:

```text
ActionSpec:
    actionId: bytes32
    extender
    extenderCodehash
    requiredPermissionMask
    settlementMode
    eligibleAtBlock
    opensOrExpandsPosition
    exitActionIds[]

ActionLifecycle:
    state
```

The initial state vocabulary is closed:

```text
PENDING
ENABLED
EXIT_ONLY
DISABLED
```

### 6.1 Meaning of one action ID

An action ID identifies one meaning, argument schema, and extender
implementation.

A material change to that meaning, schema, or extender receives a new action
ID:

```text
yield.rebalance.aave-morpho.v1
yield.rebalance.aave-morpho.v2
```

Human interfaces may group both under “Yield Rebalance,” but the contracts do
not need route-version or recommendation machinery.

The action ID does **not** pin the consumer Lego. Consumer identity is a
separate LegoBook axis governed by section 6.5.

### 6.2 One-way lifecycle and registry powers

Lifecycle transitions are closed and monotonic:

```text
PENDING  → ENABLED | DISABLED
ENABLED  → EXIT_ONLY | DISABLED
EXIT_ONLY → DISABLED
DISABLED → terminal
```

There is no `DISABLED → ENABLED` transition. Re-enabling code after disablement
requires a new action ID and a new review delay.

The registry may:

- append a new immutable `ActionSpec`;
- move it from `PENDING` to `ENABLED` after the fixed review delay;
- move an enabled action to `EXIT_ONLY` when only unwind use should survive;
- move an entry action to `DISABLED`;
- preserve an unwind action as `EXIT_ONLY`;
- disable compromised code;
- atomically disable dependent entry actions before or with the last usable
  exit; and
- mutate only the separate `ActionLifecycle.state` field according to the
  transition graph above.

The registry may not:

- edit an enabled action's extender or codehash;
- change its permission mask;
- change its settlement mode;
- change its argument meaning;
- register unsupported permission bits;
- register arbitrary wallet authority;
- replace the wallet's registry pointer invisibly;
- reverse a lifecycle transition; or
- mutate `eligibleAtBlock` after registration.

Execution checks lifecycle on every routed call:

- `PENDING` and `DISABLED` actions always reject;
- `ENABLED` actions may execute only after every ordinary caller, permission,
  action-ID, policy, session, and limit check passes; and
- `EXIT_ONLY` actions may execute only when
  `opensOrExpandsPosition == False`, with every ordinary check still applying.

`EXIT_ONLY` also closes new delegated entry into the action. A Config may add an
`actionId` to a manager's routed-action list only while the action is
`ENABLED`. Existing manager grants are not erased by the transition and may
continue to unwind under all ordinary permissions and limits. If an existing
grant is removed while the action is `EXIT_ONLY`, it cannot be added back.
Owner behavior remains governed by owner decision 6.

This is the distinct behavioral effect of `EXIT_ONLY`; it is not merely a
display label and it does not bypass manager policy.

The registry rejects an `ENABLED → EXIT_ONLY` transition when
`opensOrExpandsPosition == True`. The boolean is immutable reviewed metadata,
not proof of protocol behavior: activation evidence and differential tests must
also show that the action cannot open or expand the position it is intended to
unwind.

### 6.3 Activation delay

A newly registered action must remain `PENDING` until its immutable
`eligibleAtBlock`, which must encode at least the fixed minimum review delay.

The purpose is review and monitoring, not session drainage: routed sessions are
atomic within one transaction.

Explicit manager action approval remains required after activation. The delay
does not replace owner intent.

### 6.4 ActionRegistry and routed LegoBook binding

The wallet binds both the intended ActionRegistry and the routed LegoBook at
wallet creation. The exact addresses are constructor inputs to the wallet
blueprint generation and are exposed through read-only getters. They are not
looked up from `UndyHq` during routed execution.

This distinction matters in the current codebase:
`ActionDataProvider._getActionDataBundle` resolves `LEGO_BOOK_ID == 3` from
`UndyHq` on each call. That mutable lookup may remain for untouched direct
legacy actions during the incremental transition, but it is not an acceptable
source for routed consumer resolution. Repointing UndyHq slot 3 must not change
the LegoBook used by an already-created wallet's routed actions.

The creation path should therefore:

1. resolve the intended ActionRegistry and LegoBook once under the reviewed
   wallet-generation configuration;
2. pass both addresses into the new wallet constructor;
3. require both to be nonzero contracts;
4. store or compile them as immutable wallet bindings; and
5. have routed preparation, policy resolution, session commitment, and Config
   action-grant validation use the wallet getters for those exact bindings.

Changing either binding requires a new explicitly authorized wallet template or
wallet-generation mechanism. This document does not introduce a mutable
per-wallet setter. A mutable global pointer must not silently replace either
source of truth for existing wallets.

### 6.5 Extender identity and consumer identity are separate

The ActionRegistry pins the extender address and codehash. It does not pin the
consumer address in `ActionSpec`. The extender's prepared result selects a
`consumerLegoId`, and the wallet resolves that ID through its bound routed
LegoBook.

This creates two explicit identity axes:

```text
actionId → immutable extender address and codehash
Lego ID  → reviewed consumer address and codehash
```

The session commits both, so neither can change during one transaction. Across
transactions, the wallet uses its bound routed LegoBook rather than resolving
UndyHq slot 3 again. The no-repoint rule below then makes admitted IDs stable
inside that bound book. Both layers are required: binding the book does not
freeze an ID mapping, and freezing an ID mapping in one book does not help if a
global pointer can silently substitute another book.

The required narrow LegoBook succession rule is:

- once a Lego ID has been admitted to routed execution or has opened, managed,
  or remained necessary to exit a wallet-keyed position, its implementation is
  never repointed in place;
- materially different consumer code is registered under a new Lego ID through
  LegoBook's existing timelocked `startAddNewAddressToRegistry` /
  `confirmNewAddressToRegistry` flow;
- the predecessor ID remains resolvable for every surviving exit action or
  owner recovery path until no wallet position depends on it; and
- manager allowed-Lego policy must explicitly permit the successor ID.

A new consumer implementation therefore always receives a new Lego ID. It
receives a new action ID as well only when the immutable extender or action
schema must change to select or use it. An integration-generic extender that
already permits a new reviewed Lego ID within the same action meaning may keep
its action ID, but the new Lego ID still requires LegoBook review and manager
policy approval.

Phase 0 must decide the smallest enforceable LegoBook change for this no-repoint
rule. A governance convention alone is not sufficient for the immutability
claim. The add/confirm delay already exists; the new contract work is preventing
the existing address-update path from repointing protected IDs and binding the
routed book above UndyHq's mutable registry slot.

---

## 7. Extender preparation replaces the standalone codec

There is no separate ActionCodec contract.

The registered extender owns the typed action schema and exposes a bounded view
function:

```text
prepare(actionData)
    → planBytes
    → consumerLegoId
    → policyLegoIds[]
    → touchedAssets[]
    → SpendRequest[]
    → settlementData
```

This produces one execution plan. The Lego receives and uses those exact
`planBytes`; it does not independently recreate the plan from raw action data.

### 7.1 PreparedAction field definitions

Every returned field has one bounded purpose:

- `planBytes` is the exact bounded byte string decoded by the consumer Lego. It
  includes typed action parameters such as integration targets, minimum
  outputs, rate modes, and destinations.
- `consumerLegoId` is the one ID in the wallet-bound routed LegoBook allowed to
  consume the capability.
  The ActionSpec does not pin this field; the wallet relies on the immutable-ID
  LegoBook succession rule in section 6.5, then resolves and codehash-commits
  the selected consumer for the session.
- `policyLegoIds[]` is the bounded, deduplicated list of every routed-LegoBook
  integration ID whose use must pass existing Config/Sentinel allowed-Lego
  checks. It includes the consumer and every separately governed integration
  reached by a composite plan. It is policy metadata, not an executable address
  list; the wallet resolves every ID through its bound routed LegoBook.
- `touchedAssets[]` is the bounded, deduplicated set of every wallet-held input
  or output asset whose balance or accounting may change and that the fixed
  settlement mode must inspect or update.
- `SpendRequest[]` is the only request for wallet-created token authority.
  Every spend asset must also appear in `touchedAssets[]`. An empty spend array
  is legal for an action such as borrow, claim, or withdrawal that needs no
  wallet token pull; it does not bypass action, permission, liability, session,
  or settlement checks.
- `settlementData` is bounded ABI data whose schema is selected by the
  wallet-owned `settlementMode`. The wallet exact-decodes it using code compiled
  for that mode. It carries identifiers and fixed-mode configuration only. For
  example, a swap mode may identify its input and output assets, while a yield
  mode may identify the underlying and vault token. It does not supply an
  amount that settlement treats as observed. Every settlement amount comes from
  wallet-recorded pre-execution state, post-execution balance or position
  observation, or another independently verified wallet source. The extender
  cannot define a new settlement schema.

No field is an arbitrary target or arbitrary calldata grant.

Before execution, the wallet sends the deduplicated union of
`SpendRequest.asset` and `touchedAssets[]` through the existing allowed-assets
checks and sends every `policyLegoIds[]` entry through the existing
allowed-Lego checks. The wallet enforces the restrictions for every declared
item. A pinned extender and immutable-by-ID Lego remain trusted to declare the
complete asset and integration set; section 14 states that boundary explicitly
rather than claiming the wallet can infer undeclared protocol semantics.

### 7.2 Bounded call boundary

The wallet calls `prepare` only after entering the locked phase.

The call must be:

- a bounded-gas `staticcall`;
- made to the exact registered address;
- protected by an immediate codehash check;
- limited to bounded calldata and return sizes;
- exactly decoded with no trailing data;
- limited to fixed maximum array counts;
- deterministic from `actionData` and immutable action configuration; and
- forbidden from reading or changing wallet policy.

A malformed or reverting extender may deny its own action. It may not expand
authority.

### 7.3 PreparedAction is fully committed

The wallet commits every field used for policy, authority, execution, or
settlement.

There are no uncommitted side arrays.

Conceptually:

```text
preparedActionHash = keccak256(
    keccak256(actionData),
    planBytes,
    consumerLegoId,
    policyLegoIds,
    touchedAssets,
    spendRequests,
    settlementData
)
```

The wallet independently resolves Lego IDs through its bound routed LegoBook and
checks Config restrictions. The extender cannot invent an executable address.

### 7.4 Typed facades remain offchain convenience

The stable wallet entry point can remain:

```text
executeAction(actionId, actionData, deadline)
```

SDK builders provide typed functions:

```text
buildYieldDeposit(...)
buildYieldRebalance(...)
buildDebtDeleverage(...)
```

The SDK displays:

- the action ID;
- requested assets and amounts;
- selected Lego;
- minimum outputs;
- required permissions; and
- the final transaction data.

The wallet does not require a second caller-supplied effect language or a
duplicate caller plan hash. The caller-supplied `actionData`, its committed
hash, the registered extender, the prepared-action commitment, and the exact
capability form the onchain chain of meaning.

### 7.5 Authentication and relaying

The routed engine does not introduce a new signature or relayer scheme in
version one.

For `executeAction`:

- `msg.sender` is the signer submitted to the existing Config/Sentinel
  authorization path;
- the caller must resolve as the owner or a configured manager;
- an existing `AgentWrapper` may call as the configured manager, preserving the
  current upstream `AgentSender → AgentWrapper → UserWallet` signature, nonce,
  expiry, and approved-sender flow;
- the wallet does not accept a caller-supplied `signer` address;
- the wallet does not recover a signer from `actionData`; and
- `keccak256(actionData)` is committed even though `actionData` is not itself a
  new wallet-level signed object.

The Billing signer shortcut and Config-initiated `_isSpecialTx` paths remain on
their existing direct payment, migration, recovery, and security rails. They
cannot call `executeAction` in version one.

Any future arbitrary relay or wallet-level typed-signature path is a separate
design. At minimum it must bind chain ID, wallet, `actionId`,
`keccak256(actionData)`, deadline, nonce, signer, Config epoch, and replay
domain; define whether Billing or system callers are eligible; and preserve the
same phase, permission, action-ID, and limit checks as a direct call.

---

## 8. Exact spend authority, including “deposit max”

The system needs one familiar relative amount behavior, not a general formula
language.

Each spend request is:

```text
SpendRequest:
    roleId: uint8
    asset
    requestedAmount
    mode = EXACT | UP_TO_WALLET_BALANCE
```

`roleId` is a unique local correlation label within one prepared action. It lets
the consumer map each wallet-resolved spend back to the corresponding input
role in `planBytes` without relying on array order. It is not a permission,
registry identity, or externally reusable authority. The wallet rejects
duplicate role IDs, commits them with the spend requests, and returns the same
labels in `resolvedSpends[]`.

Resolution is closed:

```text
EXACT:
    require balance >= requestedAmount
    resolvedAmount = requestedAmount

UP_TO_WALLET_BALANCE:
    resolvedAmount = min(requestedAmount, available wallet balance)
    require resolvedAmount > 0
```

No relative lower-bound mode exists.

Minimum output, slippage, rate mode, destination, and protocol-specific
parameters remain exact action-specific fields in `planBytes`.

“Available wallet balance” means the wallet's actual liquid token balance
snapshotted while locked, after pre-action bookkeeping and before any session
allowance is activated. Today's `preparePayment` is a completed direct
withdrawal from yield, not a reservation ledger, so it does not create a
separate encumbered amount to subtract. If a future payment reservation system
does encumber liquid funds, its enumerated reserved amount must be subtracted
before `UP_TO_WALLET_BALANCE` resolves; otherwise the architecture must not
claim that reserved funds are protected.

### 8.1 The resolved amount reaches the executor

The wallet records resolved spends in the session before dispatch.

When the pinned Lego calls `consumeCapability`, the wallet returns:

```text
ActivatedCapability:
    sessionId
    actionId
    planHash
    beneficiary = wallet
    resolvedSpends[]
```

The Lego must use `resolvedSpends[]`, not the original requested amount, for
every wallet pull.

This closes the channel that “deposit max” requires:

```text
caller requests up to max
→ wallet snapshots balance while locked
→ wallet resolves an exact amount
→ consume activates the exact allowance
→ Lego receives the same exact amount
→ Lego pulls no more than that amount
```

### 8.2 Authority is linked to the resolved amount

For each resolved spend, the wallet constructs:

```text
EXACT_ERC20_ALLOWANCE(
    asset,
    pinned consumer,
    resolvedAmount
)
```

The allowance is not created during preparation.

It is activated atomically inside successful capability consumption. If
consumption reverts, no allowance exists.

### 8.3 Deliberate compatibility difference

The current `_getAmountAndApprove` behavior always clamps:

```text
amount = min(requestedAmount, currentBalance)
```

Routed `EXACT` is intentionally stricter and reverts when the balance is below
the request. A moved action that must preserve current clamp behavior uses
`UP_TO_WALLET_BALANCE`; it must not use `EXACT` and then treat the resulting
revert as accidental differential-test failure.

### 8.4 Deliberate `txUsdValue` source change

Today many wallet actions accept `txUsdValue` from the Lego's return value and
pass it into `checkManagerLimitsPostTx`. The routed path deliberately does not
trust that value.

Instead, every fixed settlement mode owns a closed valuation recipe that
produces:

```text
policyChargeUsd
fromAssetUsdValue, when a swap check applies
toAssetUsdValue, when a swap check applies
```

The recipe may use only wallet-owned or independently verified observations:

- amounts actually activated and consumed from the session capability ledger;
- post-step-7 wallet balance reconciliation against committed starting
  balances;
- fixed-mode position or debt observations from an already trusted wallet
  accounting source; and
- Appraiser conversion of those observed asset amounts at settlement.

For example:

- a yield deposit charges the actual consumed underlying amount;
- a withdrawal, borrow, or claim charges the independently observed amount
  received by the wallet, unless its fixed mode defines another reviewed
  position or debt observation;
- a swap values the actual consumed input and reconciled output separately; and
- a composite must expose every observation its fixed recipe requires or remain
  inactive for managers.

Balance deltas alone are not assumed sufficient. A token that is both spent and
received may require reconciliation with the capability-consumption ledger, and
a composite that sends borrowed assets directly into another position may
require a fixed debt or position observation. If a mode cannot produce the
required value independently, that routed action cannot use manager USD limits
safely and must not be activated for managers.

The dedicated capability-aware routed Lego interface drops `txUsdValue` from
its return tuple entirely. A routed Lego returns only action-specific execution
results needed by fixed settlement. Untouched direct legacy Lego interfaces
keep their current return tuples until those actions move. If shared adapter
code still computes a legacy USD value for a direct caller, the routed entry
point neither requests nor computes it solely for diagnostics.

Routed manager counters and emitted policy USD values use only the
wallet-derived recipe result. This removes an ambiguous dead return value and
its avoidable routed gas while preserving legacy direct behavior during the
incremental transition.

This is an intentional behavioral and gas difference from the current path. It
adds settlement-side Appraiser work and may produce a different result from a
legacy Lego calculation. Each moved action must declare its exact valuation
recipe and expected difference before differential tests are written.

### 8.5 External protocol operator authority is a separate closed vocabulary

ERC20 allowance is not the only authority used by current integrations. The
legacy wallet asks a Lego for a target, ABI string, and one of three calldata
shapes, then uses an arbitrary `raw_call` to grant that Lego operator access on
an external protocol. Confirmed production examples include:

```text
Ripe:
    setUndyLegoAccess(operator)

Euler rewards:
    toggleOperator(user, operator)
```

The routed system must not preserve the Lego-supplied target-and-ABI mechanism.
It also must not pretend that `EXACT_ERC20_ALLOWANCE` describes persistent
external protocol authority.

Before the first routed action that needs operator access, Phase 0 must inventory
every production Lego/action pair that currently returns a nonempty access
request and define the smallest named authority vocabulary actually required.
Each supported shape must:

- use a wallet-recognized authority kind rather than an arbitrary ABI string;
- bind the exact external target, wallet/user argument shape, operator, and
  enable/disable semantics through reviewed configuration or immutable code;
- bind the operator to a capability-aware, immutable-by-ID Lego;
- fail when the external call reverts;
- validate exact return semantics when the named interface returns data;
- verify resulting operator state when the external protocol exposes a reliable
  view;
- define whether the grant is per-session, immediately revoked, or intentionally
  persistent;
- define the owner and manager rules for creating and removing it;
- emit an auditable grant or revocation event; and
- preserve a usable revocation or exit path during Lego succession.

The current helper's final `assert success` already rejects a reverted call, but
it ignores returned data and does not verify resulting external state. A
non-reverting false return or semantically ineffective call may therefore look
successful. The named replacement must close that gap.

Operator authority complicates succession. If a predecessor Lego remains
necessary for an `EXIT_ONLY` path while a successor uses a new Lego ID, both may
need external protocol access simultaneously. The authority design must support
that reviewed overlap without repointing either Lego ID and must state when the
predecessor's authority can be revoked.

This is an accepted boundary on forward compatibility:

> A new action that needs an unsupported form of external protocol authority
> requires a reviewed wallet-core authority addition. Registration alone cannot
> invent it.

The initial yield-deposit slice requires no such authority. The named authority
package is designed in Phase 0 but implemented only before the first action that
needs it.

---

## 9. Session lifecycle

The useful PoC lifecycle remains, but the production design also needs one
canonical ordering for registry, policy, preparation, spend resolution, and
post-action checks.

### 9.1 Canonical end-to-end flow

Every routed action follows this order:

1. The wallet checks the deadline and requires session phase `IDLE`. It changes
   phase to `DISPATCHING` before its first external registry, Config, Sentinel,
   extender, LegoBook, or other untrusted call.
2. The wallet looks up the immutable `ActionSpec` through its bound
   ActionRegistry, rejects an unknown action, and checks lifecycle eligibility:
   `ENABLED`, or `EXIT_ONLY` with
   `opensOrExpandsPosition == False`. `PENDING` and `DISABLED` reject.
3. The wallet authenticates `msg.sender` through the existing owner/manager
   path using the first routed-policy stage. For a manager, it checks activation
   and expiry, current transaction-count and cooldown state, explicit
   `actionId` opt-in, and every bit in `requiredPermissionMask`. Owner behavior
   follows the unresolved default in section 5.4.
4. The wallet checks the registered extender address and codehash, then makes
   the bounded `staticcall` to `prepare(actionData)`.
5. The wallet exact-decodes the full prepared action, resolves all Lego IDs
   through its bound routed LegoBook, checks the consumer codehash, requires the
   consumer to be included in `policyLegoIds[]`, and validates every array
   relationship and bound. It does not consult the current UndyHq LegoBook slot.
6. The wallet runs the second routed-policy stage for checks that require
   prepared values. Allowed-assets checks use the union of
   `SpendRequest.asset` and `touchedAssets[]`; allowed-Lego checks use
   `policyLegoIds[]`. This stage reuses the existing specific-manager and global
   rules without advancing counters or repeating the stage-3 transaction
   checks. No USD, slippage, approved-vault, period-value, or lifetime-value
   result is invented before execution.
7. While still locked, the wallet performs the applicable existing pre-action
   accounting, including yield-profit realization, and records the
   pre-execution balances or other wallet observations required by the selected
   settlement mode. This accounting may make external Appraiser, token, fee, or
   loot calls and may transfer realized fee tokens. It remains in
   `DISPATCHING`; no active session record, capability, or allowance exists.
   Therefore acknowledgement and consumption both reject even though those
   entry points otherwise use the `DISPATCHING` phase. All stateful wallet
   reentry rejects, and the starting snapshots are recorded after those
   bookkeeping effects so settlement reconciles from post-fee reality.
8. The wallet resolves every `EXACT` or `UP_TO_WALLET_BALANCE` spend after that
   bookkeeping and before any allowance exists. It commits the complete
   prepared action, resolved consumer, observed starting state, and resolved
   spends into one session.
9. The wallet calls the exact extender with `(sessionId, consumerAddress,
   planBytes)`. The extender acknowledges that exact session and plan, then
   calls the supplied consumer with the exact `(sessionId, planBytes)`.
10. The exact Lego consumes the capability once. Consumption changes phase to
    `ACTIVE`, activates only the resolved allowances, and returns the exact
    resolved capability context. The Lego then performs its reviewed one-step
    or multi-step protocol workflow.
11. When execution returns, the wallet changes phase to `SETTLING` and clears
    every wallet-created allowance before making settlement-related external
    calls.
12. The fixed settlement mode computes actual amounts from the capability
    ledger, committed starting observations, and independently observed results.
    Its closed valuation recipe uses Appraiser to produce `policyChargeUsd` and,
    when applicable, separate input/output USD values. The existing post-action
    policy path applies per-transaction, period, and lifetime USD limits,
    approved-vault requirements, swap counts, and slippage to those
    wallet-derived values, then updates manager counters exactly once.
13. The wallet completes asset, yield, fee, loot, deposit-point, and other
    applicable accounting, clears the session, and returns to `IDLE`.

Any failure reverts the entire transaction, including phase changes, allowances,
external protocol effects, policy updates, and accounting.

### 9.2 Phase machine

```text
IDLE
DISPATCHING
ACTIVE
SETTLING
```

Every stateful top-level wallet action requires `IDLE`.

`executeAction` changes phase before its first call to an untrusted external
contract. A revert rolls the phase change back with the transaction.

The existing `UserWallet.vy` already uses transient storage and its current
Vyper 0.4.3 runtime emits `TLOAD`/`TSTORE`. A transient phase variable is
therefore the provisional version-one choice rather than a new EVM-family
dependency. Phase 0 must still:

- pin the Wallet v3 EVM target explicitly instead of inheriting a Vyper default;
- reproduce the current runtime under both the implicit and explicit target and
  require byte-for-byte agreement before adopting the pin;
- compare the transient phase machine with any proposed persistent-storage
  alternative for bytecode and gas;
- verify the selected deployment chain supports the pinned opcodes; and
- record optimizer and target settings with every size and gas result.

Changing optimizer settings for unrelated shared contracts is not implied.
Wallet v3 and every shared contract it changes use an explicit reproducible
release build configuration.

### 9.3 Phase-to-entry-point table

| Entry point | Allowed phase | Caller |
|---|---|---|
| Direct wallet financial actions | `IDLE` | Existing authorized caller |
| `executeAction` | `IDLE` | Owner or configured manager |
| Extender `acknowledgeSession` callback | `DISPATCHING` plus committed active session | Exact registered extender |
| `consumeCapability` | `DISPATCHING` plus committed, acknowledged active session | Exact resolved Lego |
| Stateful wallet callbacks during consumer execution | `ACTIVE` | None; all reject |
| Settlement helpers | `SETTLING` | Wallet internal flow |
| Passive token/NFT receive hooks | Any token-required phase | Inert receipt only |
| Manager/config/security mutations | `IDLE` | Existing authorized system path |

This table lists wallet-observable entry points only. The wallet cannot inspect
an external protocol call's abstract “position in the call stack.” It enforces
execution order through phase, exact caller checks on wallet callbacks,
one-time consumption, and exact allowance activation. Correct construction of
downstream external calls remains part of the pinned Lego trust boundary.

There is deliberately no state-mutating wallet entry point available during
`ACTIVE`. The consumed Lego operates against external protocols using the
already activated bounded authority. Only the inert receiver hooks described
below remain callable when token standards require them.

Passive receive hooks:

- may return the required receiver selector;
- may emit a narrowly scoped receipt event;
- do not write wallet storage;
- do not call external contracts;
- do not change permissions;
- do not open or consume sessions; and
- cannot invoke another top-level wallet action.

Asset registration and other receipt accounting happen through the fixed
settlement flow, not inside a passive hook.

### 9.4 Session commitment

The session commitment binds:

```text
chain ID
wallet
direct caller
actionId
keccak256(actionData)
ActionRegistry address
extender address and codehash
consumer Lego ID, address, and codehash
bound routed LegoBook address
required permission mask
settlement mode
keccak256(planBytes)
preparedActionHash
resolved spend amounts
touched assets
pre-execution wallet observations required by settlement
deadline
wallet session nonce
```

`sessionId` is derived from that commitment and the nonce.

### 9.5 Acknowledgement

The wallet calls the extender with:

```text
sessionId
consumerAddress
planBytes
```

The extender:

- checks the wallet-reported session ID and plan hash;
- calls `acknowledgeSession(sessionId, planHash)` on the wallet;
- waits for that acknowledgement to succeed;
- forwards `(sessionId, planBytes)` to the supplied resolved consumer; and
- never receives custody or a wallet allowance.

The wallet records `acknowledged = True` only when a committed active-session
record already exists and the exact registered extender calls back during
`DISPATCHING` with that session ID and plan hash. Phase alone is insufficient:
the pre-accounting callbacks in step 7 occur in `DISPATCHING` before any session
exists and must not be able to acknowledge.

Acknowledgement does not prove economic correctness and is not an effect
attestation. It proves only that the pinned extender is orchestrating the exact
wallet-opened session and accepted the committed plan before the consumer may
activate authority.

### 9.6 Consumption

The Lego calls:

```text
consumeCapability(sessionId, planHash)
    → ActivatedCapability
```

The wallet requires:

- phase is `DISPATCHING`;
- caller is the exact session consumer;
- session ID and plan hash match;
- the exact registered extender has already acknowledged that session;
- deadline has not passed;
- capability is unused; and
- consumer codehash still matches.

Inside the same call, the wallet:

1. marks the capability consumed;
2. changes phase to `ACTIVE`;
3. activates exact resolved allowances; and
4. returns the exact resolved capability context.

Only after this return can `transferFrom` succeed.

### 9.7 Settlement

After the extender/Lego call returns, the wallet enters `SETTLING`.

The wallet:

- requires successful consumption;
- clears every wallet-created allowance before settlement-related external
  calls;
- runs the fixed settlement mode;
- derives settlement amounts from the capability ledger and wallet-recorded
  observations rather than extender- or Lego-supplied amount claims;
- converts each fixed mode's selected observed amounts through Appraiser to
  produce the policy USD values defined in section 8.4;
- applies post-action USD, approved-vault, swap, and slippage checks to the
  applicable observed results;
- updates manager counters once;
- updates asset records, yield profits, fees, loot, and deposit points as
  applicable;
- requires committed-resource residuals to return to the wallet when the action
  requires it;
- clears all session storage; and
- returns to `IDLE`.

---

## 10. Fixed settlement modes

Settlement behavior remains a closed wallet vocabulary.

An initial set may be:

```text
STANDARD
YIELD_DEPOSIT
YIELD_WITHDRAW
YIELD_REBALANCE
SWAP
DEBT
LIQUIDITY
REWARDS
```

The exact set should be derived from the current `_performPostActionTasks`
branches and the first vertical slice.

An ActionSpec selects one existing mode. Registration cannot add a new mode.

Each mode compiles one valuation recipe into the wallet. The initial mapping
should be no more generic than:

| Mode family | Primary policy-charge observation | Additional required observations |
|---|---|---|
| Standard spend / yield deposit / repay | Actual capability amount consumed for the designated spend role | Resulting asset or position balance when existing accounting needs it |
| Yield withdraw / rewards | Reconciled amount received by the wallet | Source position-token reduction where required |
| Yield rebalance | Reconciled source-position withdrawal plus target-position deposit, linked to the capability ledger | Source reduction, target increase, residual return, yield-profit/accounting updates, and—when `TRADE` applies—independently observed input/output for every counted swap |
| Borrow / collateral change | Independently observed debt, collateral, or wallet-received delta selected by the fixed mode | Liability and approved-position checks |
| Swap | Actual consumed input plus independently reconciled output | Separate Appraiser values for Sentinel slippage |
| Liquidity | Actual consumed token roles and independently observed LP position change | Both sides of the liquidity position |

This is a starting measurement map, not permission for ambiguous net-balance
valuation. Phase 0 must freeze the precise amount formula, Appraiser calls,
zero-price behavior, and event value for each enabled mode. A mode that cannot
independently observe its required basis does not ship for managers.

For a standalone swap, the routed path must preserve today's wallet-observed
input/output valuation, swap counter, and slippage behavior.

For a composite containing `TRADE`, permission alone is insufficient. Before
that action can be activated for managers, a concrete wallet-verifiable path
must provide the actual input and output amounts needed by the existing
Sentinel slippage check for every counted swap. A value merely reported by the
extender or Lego is not independent evidence, and correct use of `minOut` does
not by itself satisfy the existing Sentinel check.

Possible implementations may use wallet-observable intermediate custody,
independently checked balance deltas, or another bounded mechanism proven by the
vertical slice. This document does not preselect one. If the required evidence
cannot be produced safely, the manager-routed composite action must remain
inactive. It may not silently downgrade to reviewed-code trust.

Unknown settlement modes fail closed.

### 10.1 No generic verifier in version one

The first simplified version should not include a generic verifier registry.

Protocol-specific correctness remains enforced by:

- exact action-specific plan fields;
- reviewed and pinned extender/Lego code;
- exact spend authority;
- protocol return validation;
- wallet balance and ownership checks already used by that action family; and
- the fixed settlement mode.

If a concrete action later proves that a protocol-specific before/after adapter
is necessary, that is a separate reviewed addition.

Any future verifier must use:

- immediate codehash checks before both pre and post calls;
- bounded-gas `staticcall`;
- bounded calldata and return data;
- exact decoding;
- the same address and codehash before and after; and
- output that can reject settlement but cannot expand authority.

---

## 11. Rebalance and deleverage

Both can remain one action.

The requirement is one consumer and one capability consumption, not one
protocol call.

### 11.1 Yield rebalance

```text
actionId:
    yield.rebalance.aave-morpho.v1

permissions:
    YIELD
    + TRADE only if the plan permits a swap

consumer:
    one reviewed composite Lego

execution:
    consume once
    → withdraw source position
    → optionally swap
    → deposit target position
    → return residual committed assets

settlement:
    YIELD_REBALANCE
    + wallet-verifiable trade observations before manager activation
```

`YIELD_REBALANCE` is a new closed wallet-core settlement mode. It is not
registry data and cannot be created by an ActionSpec. Its fixed recipe
reconciles the source-position reduction, target-position increase, capability
consumption, residual asset return, and existing yield/accounting updates. When
the plan permits a swap, the same mode must also provide independently observed
per-swap inputs and outputs for the existing Sentinel checks; otherwise that
manager route remains inactive.

### 11.2 Debt deleverage

```text
actionId:
    debt.deleverage.aave-v1

permissions:
    DEBT | TRADE

consumer:
    one reviewed deleverage Lego

execution:
    consume once
    → release bounded collateral
    → exchange if required
    → repay debt
    → return residual committed assets

settlement:
    fixed debt path plus wallet-verifiable trade counters/slippage
```

The extender does not call internal wallet functions to create nested actions.
The Lego performs the multi-step protocol workflow inside one wallet session.

These examples establish that a composite may be one action. They do not waive
the manager activation gate in section 10. Until wallet-verifiable trade
evidence exists, the swap-containing variants are not manager-routable.

---

## 12. Payments

Payment rails remain direct initially because the existing wallet already has
specialized and mature behavior:

- approved payees;
- payee pull permissions;
- unit and USD limits;
- cheque creation and payment;
- cheque unlock and expiry;
- allowed payment assets;
- per-period counters and cooldowns; and
- Billing and special-payment preparation.

The permission research should distinguish:

```text
make a bounded payment now
```

from:

```text
create a future payment commitment or pull authority
```

Possible payment modes include:

```text
direct transfer
approved-payee push
approved-payee pull
cheque
invoice
reservation and capture
recurring subscription
stream
x402 machine payment
refund
```

These modes do not automatically require separate permission IDs. Recipient
configuration, amount limits, time bounds, and pull-versus-push rules may
express the differences.

No payment mode moves into the routed engine without a separate comparison
against the existing direct rail.

---

## 13. Action activation, upgrades, and exits

### 13.1 New action meaning, schema, or extender means new action ID

The first design does not support mutable versions under one action ID.

This removes:

- route pinning;
- route preferences;
- recommended-route changes;
- wildcard version behavior;
- succession races; and
- per-wallet version resolution.

A new extender implementation, action schema, or action meaning receives a new
immutable action ID and requires explicit manager action approval.

Consumer Legos use the separate rule in section 6.5: new consumer code always
receives a new Lego ID. It also requires a new action ID only when the immutable
extender or action schema must change to use that consumer.

### 13.2 Emergency disabling

Registry governance may disable a compromised action immediately.

Because sessions are atomic, there are no cross-transaction sessions to drain.

Persistent positions are different: their unwind actions must survive.
Moving an action to `EXIT_ONLY` preserves only a non-expanding unwind path; it
does not preserve ordinary entry behavior or bypass any wallet-level grant.
Config refuses new manager action-ID grants for an `EXIT_ONLY` action while
honoring grants that already existed before the transition.

### 13.3 Entry and exit pairs

An action that opens or expands a persistent position must name at least one
reviewed exit action ID.

Onchain activation checks:

- every exit action exists;
- at least one exit action is `ENABLED` or `EXIT_ONLY`;
- every exit action has `opensOrExpandsPosition == False`;
- exit IDs are immutable fields of the entry `ActionSpec`; and
- the registry records the reverse dependency needed for atomic entry
  disablement.

Required review evidence before governance activates the entry:

- tests cover entry followed by exit;
- the reference wallet configuration demonstrates that the owner can invoke the
  exit;
- operational documentation identifies the resulting external position; and
- emergency procedures identify the usable exit or owner-only recovery path.

When entry or exit depends on a consumer Lego, the evidence must also identify
that Lego ID. LegoBook may not repoint it while any wallet-keyed position or
exit dependency survives. A successor Lego receives a new ID, while the
predecessor remains resolvable for the recorded exit path.

The last three items are review and release gates; the ActionRegistry cannot
prove them from per-wallet state at registration.

If the last usable exit is disabled:

- the registry transaction must first or atomically move every dependent entry
  action to `DISABLED`; or
- a separately reviewed owner-only recovery path must remain.

This is intentionally smaller than a generic position-family framework.

---

## 14. Trust model

The simplified system does not pretend to make arbitrary protocol code
trustless.

### 14.1 Wallet-enforced guarantees

The wallet enforces:

- caller and manager authorization;
- explicit manager action opt-in;
- existing recipient and value limits;
- allowed-assets checks for every declared spend asset and touched wallet
  asset;
- allowed-Lego checks for every declared policy Lego ID;
- exact action and extender identity from ActionRegistry;
- exact consumer Lego ID, address, and codehash resolved from the wallet-bound
  routed LegoBook for the session;
- exact plan and prepared-context commitment;
- one session and one capability consumption;
- exact resolved token allowances;
- no consumer pull above the resolved allowance;
- wallet locking;
- fixed settlement behavior;
- authority cleanup; and
- session cleanup.

### 14.2 Reviewed-code trust

The registered extender and Lego remain trusted for:

- correct action-specific decoding;
- complete declaration of every policy-relevant wallet asset and integration
  used by the action;
- correct protocol call construction;
- correct use of minimum outputs and slippage fields;
- correct use of the pulled resolved amount in downstream protocol calls;
- safe intermediate-hop behavior;
- correct handling of protocol callbacks;
- returning residual assets; and
- protocol-specific semantic correctness not observed by the wallet.

Extender codehash pinning makes extender trust explicit and immutable for one
action ID. Consumer trust is pinned independently by Lego ID: the wallet
commits the resolved consumer address and codehash for each session, while the
wallet's immutable routed-LegoBook binding plus that book's no-repoint rule make
the ID stable across transactions. The ActionRegistry does not make the
consumer immutable.

The distinction is important: the wallet can cap how much the Lego pulls, but
it cannot generally prove how the Lego used every pulled token inside an
external protocol or infer an undeclared output or intermediate integration from
opaque protocol calldata. The wallet therefore enforces asset and Lego policy
over the complete declared set, while declaration completeness remains pinned
reviewed-code trust in version one. Likewise, the Lego is trusted to place
committed minimum outputs into protocol calls, while manager-facing Sentinel
slippage enforcement still requires the independent wallet-verifiable
observations described in section 10.

### 14.3 Policy-price trust

The routed wallet owns the amount observations used by each fixed settlement
recipe, but it still trusts Appraiser and its configured price sources to
convert those amounts into correct USD values. Moving manager limits away from
Lego-returned `txUsdValue` removes consumer-controlled valuation; it does not
make price conversion trustless.

This trust is policy-critical because an incorrect price can weaken a
per-transaction, period, or lifetime manager cap, while an unavailable price can
block an otherwise valid action. Routed settlement must preserve the existing
manager-selected `failOnZeroPrice` behavior and the existing system's freshness
rules. It must not silently reinterpret zero, missing, or stale data as a usable
price. Phase 0 must document, per settlement mode, which Appraiser entry point
and price source are used, when a price is considered stale or unavailable, and
whether the existing policy rejects or permits that condition.

The security claim is therefore:

- observed token, position, and debt amounts come from the wallet-owned fixed
  recipe;
- USD conversion comes from the trusted Appraiser path;
- configured zero/stale-price behavior remains explicit and testable; and
- an extender or Lego cannot substitute its own USD value.

### 14.4 Governance trust

Governance can:

- register reviewed new action IDs after delay;
- activate them;
- disable compromised IDs; and
- maintain the approved Lego registry;
- register successor consumer code under a new Lego ID; and
- retain predecessor Lego IDs while routed or wallet-keyed positions still
  need them for exits.

Governance cannot silently grant a manager the new action because delegated
manager use requires explicit Config approval.

Governance also cannot repoint a routed or position-bearing Lego ID to new code,
and an UndyHq LegoBook-slot update cannot replace the routed book bound to an
existing wallet. Those restrictions require both the wallet binding and a
LegoBook enforcement change; they are not merely social promises.

---

## 15. Security invariants

```text
S1   Every stateful top-level wallet action requires phase IDLE.
S2   executeAction locks the wallet before its first untrusted external call.
S3   Unknown action IDs, lifecycle states, permission bits, settlement modes, and phases fail closed.
S4   A manager needs every required permission bit.
S5   A manager also needs explicit actionId approval.
S6   New registry entries never expand existing manager action approvals.
S7   An ActionSpec is immutable after registration; only separate lifecycle state moves one-way.
S8   A material action meaning, schema, or extender change receives a new actionId.
S9   The extender address and codehash match the ActionSpec immediately before use.
S10  Extender preparation is a bounded staticcall with exact decoding.
S11  Every policy, authority, execution, and settlement input is session-committed.
S12  The wallet resolves routed consumer addresses only through its bound routed LegoBook.
S13  The extender never receives custody or token allowance.
S14  The Lego is the only capability consumer.
S15  A capability is consumed at most once.
S16  Wallet-created token authority activates only inside successful consumption.
S17  Activated allowance equals the wallet-resolved spend amount.
S18  consumeCapability returns the same resolved amount to the Lego.
S19  The wallet never authorizes a consumer pull above the resolved spend amount.
S20  EXACT spend requires the requested balance; UP_TO_WALLET_BALANCE clamps once.
S21  Relative lower bounds and arbitrary amount formulas do not exist.
S22  The session binds exact planBytes and prepared context.
S23  Direct wallet actions cannot reenter during a routed session.
S24  Passive receiver hooks cannot open, consume, or mutate a session.
S25  The exact extender acknowledges the wallet-opened session before consumption.
S26  Composite actions use one consumer and one capability consumption.
S27  A manager trade composite requires TRADE and wallet-verifiable swap evidence.
S28  Settlement clears every wallet-created allowance.
S29  Settlement updates manager counters once.
S30  Successful settlement clears the session and returns phase to IDLE.
S31  An action opening a position has a surviving owner exit or recovery path.
S32  Direct payment and security rails remain outside routing unless separately approved.
S33  Registry governance cannot replace the wallet's registry pointer invisibly.
S34  Any future verifier is pinned, bounded, static, exact-decoded, and non-authorizing.
S35  Routed authentication uses msg.sender as owner/manager; Billing and special paths stay direct.
S36  The session commits keccak256(actionData).
S37  DISABLED is terminal; reactivation requires a new actionId and review delay.
S38  PENDING and DISABLED actions never execute; only ENABLED or valid EXIT_ONLY actions can dispatch.
S39  EXIT_ONLY never executes an action marked as opening or expanding a position.
S40  Every spend asset also appears in the touched-asset set.
S41  Allowed-assets checks cover every spend asset and touched wallet asset; allowed-Lego checks cover every policy Lego ID.
S42  Settlement never treats an amount supplied by the extender or Lego as a wallet observation.
S43  A zero-spend action still consumes one capability and passes every non-spend authorization and settlement check.
S44  New consumer code receives a new Lego ID; routed or position-bearing Lego IDs are never repointed in place.
S45  A predecessor Lego ID remains resolvable while any wallet-keyed position or exit path depends on it.
S46  Config cannot add or restore a manager action-ID grant while that action is EXIT_ONLY.
S47  Routed policy USD values come only from a fixed wallet-owned valuation recipe and Appraiser over independently observed amounts.
S48  ACTIVE exposes no state-mutating wallet entry point; only inert token-standard receipt hooks may respond.
S49  Repointing UndyHq's LegoBook slot cannot change an existing wallet's routed LegoBook.
S50  acknowledgeSession requires a committed active-session record; DISPATCHING phase alone is insufficient.
S51  Config validates only action-ID set additions against ENABLED: retained EXIT_ONLY grants survive unrelated edits, but removed grants cannot be restored.
S52  The routed Lego ABI does not return txUsdValue; legacy direct Lego returns cannot enter routed policy.
S53  No routed operator grant accepts a Lego-supplied target, ABI string, or arbitrary calldata.
S54  Every supported external operator grant uses a named wallet-recognized shape and a reviewed target/operator binding.
S55  Operator-grant return semantics and resulting external state are verified whenever the named protocol interface permits it.
S56  A predecessor required for EXIT_ONLY may retain reviewed operator authority until its last dependent position can exit; succession never repoints its Lego ID.
S57  The immutable ActionDataProvider remains a thin adapter; replaceable Sentinel entry points own routed policy interpretation.
S58  Wallet v3 compilation pins compiler version, optimizer, and EVM target for every release measurement.
S59  PolicyContextV1 is versioned and action-agnostic; the immutable ActionDataProvider has no per-action policy branches or opaque extension semantics.
S60  An action cannot be enabled when its caller or prepared-policy requirements cannot be expressed by the wallet generation's bound policy context and stages.
```

---

## 16. Required tests

### 16.1 ActionRegistry tests

- reject duplicate action IDs;
- reject unsupported permission bits;
- reject unsupported settlement modes;
- reject zero or non-contract extenders;
- reject codehash mismatch;
- enforce minimum pending delay;
- prevent mutation of every immutable `ActionSpec` field;
- allow only the closed one-way lifecycle transitions;
- prove `DISABLED` cannot return to `ENABLED` or `EXIT_ONLY`;
- prove `eligibleAtBlock` cannot change;
- reject execution while `PENDING` or `DISABLED`;
- allow `EXIT_ONLY` execution only when
  `opensOrExpandsPosition == False`;
- reject an `ENABLED → EXIT_ONLY` transition for an action marked as opening or
  expanding a position;
- require a new action ID for a new extender, schema, or action meaning;
- reject position entry without a usable exit; and
- disable every dependent entry atomically when its last exit disappears; and
- prove the wallet-bound registry getter cannot be changed through a mutable
  global pointer.

### 16.2 LegoBook and binding tests

- reject in-place repointing of every routed or position-bearing Lego ID;
- require materially different consumer code to use a new Lego ID;
- prove new IDs use LegoBook's existing timelocked add/confirm flow;
- preserve the predecessor ID while an entry/exit dependency survives; and
- prove that the session rejects a consumer whose resolved codehash changes;
- prove the wallet constructor rejects a zero or non-contract routed LegoBook;
- prove routed resolution uses the wallet-bound book rather than the current
  UndyHq slot 3;
- repoint UndyHq slot 3 in a fixture and prove an existing wallet's routed
  consumer resolution is unchanged; and
- prove changing the routed book requires a new explicitly authorized wallet
  template or wallet-generation path.

### 16.3 Permission tests

- owner behavior matches existing `canOwnerManage`;
- manager without action-ID approval fails;
- manager with action approval but missing one permission bit fails;
- composite masks require every bit;
- unknown bits fail;
- global and manager limits both apply;
- allowed-assets checks receive every spend asset and touched wallet asset;
- allowed-Lego checks receive every policy Lego ID;
- omission of a declared spend asset from `touchedAssets[]` fails;
- a newly registered action is not automatically granted;
- Config may add a manager grant while an action is `ENABLED`;
- Config may not add or restore a manager grant after it becomes `EXIT_ONLY`;
- an existing grant continues to authorize a valid non-expanding exit under all
  ordinary permissions and limits;
- changing an unrelated manager field preserves a retained `EXIT_ONLY` grant;
- reordering or resubmitting the same action-ID set is not treated as a new
  grant;
- removing an `EXIT_ONLY` grant succeeds, while adding it in a later update
  fails;
- the Config storage boundary applies identical addition checks to HighCommand
  and Migrator callers;
- a starter manager begins with no routed action IDs and can receive them only
  after the wallet binding exists;
- the stage-3 routed authorization path and stage-6 prepared-policy path both
  preserve specific-manager and global policy behavior without double-counting;
  and
- existing direct permission behavior remains unchanged.

### 16.4 Authentication tests

- direct owner and configured-manager callers preserve existing authorization;
- an existing AgentWrapper is evaluated as the configured manager;
- an arbitrary relayer cannot nominate another signer;
- Billing cannot enter `executeAction`;
- Config special-transaction callers cannot enter `executeAction`;
- action-data hash mismatch changes the session ID and fails acknowledgement or
  consumption;
- nonce and deadline bind the session; and
- any future relay path has separate replay-domain and signature tests before
  activation.

### 16.5 Phase and reentrancy tests

- every top-level financial action fails outside `IDLE`;
- no state-mutating wallet callback is callable during `ACTIVE`;
- phase changes before extender preparation;
- extender preparation cannot reenter;
- extender acknowledgement fails from the wrong caller or phase;
- consumption before acknowledgement fails;
- the extender receives the resolved consumer address and forwards the exact
  `(sessionId, planBytes)` pair to that consumer;
- capability consumption fails from the wrong caller or phase;
- consumption cannot repeat;
- direct transfers, payment preparation, and config mutation cannot nest;
- passive ETH/ERC20/ERC721/ERC1155 receipt cannot start an action;
- passive receipt hooks do not write wallet storage or perform external calls;
- step-7 yield, fee, token, and Appraiser callbacks cannot acknowledge a
  session, consume a capability, or reenter a top-level wallet action before the
  active-session record is committed, even though phase is `DISPATCHING`;
- every revert returns the wallet to its pre-transaction phase through atomic
  rollback.

### 16.6 Spend and capability tests

- exact spend succeeds with sufficient balance;
- exact spend fails with insufficient balance;
- a parity action that previously clamped uses `UP_TO_WALLET_BALANCE`;
- up-to-balance spend clamps exactly once;
- zero resolved amount fails;
- an action with no wallet token pull may use an empty spend array but still
  requires one successful capability consumption;
- the allowance is zero before consumption;
- consumption activates the exact resolved allowance;
- the returned capability contains the same amount;
- every resolved spend preserves its unique `roleId`;
- duplicate spend role IDs fail;
- a Lego cannot pull before consumption;
- a Lego cannot pull more than the resolved amount;
- allowance is zero after settlement; and
- plan hash or session ID mismatch fails.

### 16.7 Settlement tests

- each fixed mode matches its declared legacy-parity behavior and expected
  routed differences;
- `YIELD_REBALANCE` reconciles source reduction, target increase, capability
  consumption, residuals, and existing yield/accounting updates;
- swap-containing `YIELD_REBALANCE` also supplies independently observed
  per-swap input/output values or remains inactive for managers;
- manager counters update once;
- a trade-containing composite cannot activate for managers without
  wallet-verifiable actual input/output observations;
- untrusted extender- or Lego-reported swap values do not satisfy the
  manager-slippage requirement;
- an enabled trade composite updates swap counters and slippage checks from the
  verified observations;
- yield deposit/withdraw accounting preserves current asset, fee, loot, and
  deposit-point behavior apart from declared valuation-source differences;
- touched assets are updated correctly;
- an extender- or Lego-reported amount cannot substitute for a required wallet
  balance snapshot, delta, or other independent observation;
- each fixed mode derives `policyChargeUsd` from its specified capability,
  balance, position, or debt observations and Appraiser;
- the routed Lego ABI has no `txUsdValue` return and no legacy-return adapter
  value can affect manager limits, counters, or policy events;
- zero, missing, and stale prices preserve the existing fail-closed behavior
  selected by manager policy;
- mixed spend-and-receive use of the same asset reconciles gross capability
  consumption rather than relying on an ambiguous net balance delta;
- committed residual resources return when required;
- fees remain under wallet hard ceilings;
- loot and deposit points preserve parity; and
- unknown settlement mode fails.

### 16.8 Differential tests

For each moved action, compare old and routed paths for:

- caller authorization;
- allowed assets and Legos;
- limits and counters;
- token flows;
- protocol position results;
- fees and accounting;
- events;
- approval cleanup;
- failure behavior; and
- gas.

Expected differences must be declared before asserting parity. In particular,
`EXACT` insufficient-balance reversion is deliberate; an action that needs
today's clamp behavior must select `UP_TO_WALLET_BALANCE`.

The routed policy-value source is also deliberately different. Differential
fixtures must compare the legacy Lego-returned `txUsdValue` with the routed
wallet-derived `policyChargeUsd`, explain every expected difference, and assert
that the capability-aware routed ABI returns no `txUsdValue` and routed manager
counters and emitted policy values use only the wallet-derived result.

### 16.9 External operator-authority tests

Before activating any routed action that needs external protocol operator
access:

- inventory every current production Lego/action pair that requests access and
  map it to a named supported authority shape or explicitly unsupported case;
- reject arbitrary targets, selectors, ABI strings, calldata, users, and
  operators;
- reject an authority request for a consumer other than the session's
  immutable-by-ID Lego;
- revert when the external grant call reverts;
- reject a non-reverting false return when the named interface returns a boolean;
- verify the resulting operator state when the protocol exposes a reliable view;
- prove the exact temporary or persistent lifecycle selected for that authority;
- test explicit revocation and emergency disablement;
- preserve predecessor authority when required for `EXIT_ONLY`;
- permit reviewed predecessor/successor overlap without repointing either ID;
- revoke predecessor authority only after no recorded exit dependency remains;
  and
- prove the initial yield-deposit route creates no external operator grant.

---

## 17. Feasibility and measurement

The design is not implementation-ready until a real vertical slice proves:

- wallet runtime size with catalog functions removed and session code added;
- Config size after the bounded action-ID list;
- Config size after the exact initial permission representation and each
  proposed expansion category;
- Config and HighCommand size plus add/update gas for the bounded action-ID
  set-difference and Config → wallet getter → ActionRegistry lifecycle check;
- UserWalletConfig, ActionDataProvider, and Sentinel/backpack size after the
  two-stage routed-policy API;
- wallet constructor/runtime size and creation gas after adding bound
  ActionRegistry and routed-LegoBook addresses and read-only getters;
- LegoBook size and governance cost after the enforceable no-repoint succession
  rule, including confirmation that existing add/confirm delay is reused;
- proof that changing UndyHq slot 3 does not change an existing wallet's routed
  resolution, with any direct-legacy behavior difference documented;
- ActionRegistry runtime size at its maximum bounded record shape;
- first extender runtime size, including its typed plan decoder;
- Base transaction gas;
- calldata and L1 data cost;
- direct transfer/payment gas parity;
- exact `prepare` gas and output bounds;
- exact per-mode Appraiser call count and gas for wallet-derived
  `policyChargeUsd`, including zero/stale-price paths;
- exact Appraiser trust/failure behavior for zero, missing, and stale prices in
  each initial mode;
- differential counter and event effects from replacing Lego-returned
  `txUsdValue`;
- explicit maxima for `planBytes`, `policyLegoIds[]`, `touchedAssets[]`,
  `SpendRequest[]`, `exitActionIds[]`, and per-manager action IDs; and
- end-to-end deposit-max behavior.

The current documented baselines are:

```text
UserWallet runtime:          23,032 / 24,576 bytes
UserWallet runtime headroom:  1,544 bytes

UserWalletConfig blueprint:  23,856 / 24,576 bytes
Config blueprint headroom:       720 bytes
```

These exact figures are reproduction targets, not permission to spend all
remaining bytes. Phase 0 must reproduce them in the pinned compiler and harness,
set an explicit safety reserve below each hard limit, and measure the complete
release shape after every meaningful change. The final kernel budget is not the
current 1,544-byte wallet headroom because routed actions are intended to remove
existing action-catalog code in the same template generation.

The current Sentinel interfaces use maximums of ten assets and ten Lego IDs.
Those values are compatibility hypotheses for the first spike, not automatically
the final routed maxima. Phase 0 should start at no more than those existing
ceilings, measure the session-storage, calldata, decoding, and gas costs, and
lower each bound when the first action family does not need it. No implementation
begins with an unnamed or effectively unbounded array.

The catalog-strip feasibility result has now been reproduced from checkout
`c8d3d002c374ce2cf7038d0e5de4fbd613478d39`; the measured wallet source was
last modified at `9c959ac449a7f37c9287cd014c76d08b83aa5935` and is identified
independently by its source hash. The measurement uses Vyper 0.4.3, code-size
optimization, and an explicit `prague` EVM target:

This Wallet v3 build identity is intentionally separate from the archived PoC
identity in `docs/poc/user-wallet/`, which pins Vyper 0.4.3 with
`optimizer=gas` and `evm_version=cancun`. The PoC remains historical evidence;
its target must not be “harmonized” with Wallet v3 because doing so would change
the bytecode and invalidate its hash-pinned evidence identity.

```text
Current runtime:                         23,032 bytes
Catalog-stripped runtime:                 8,461 bytes
Catalog-stripped EIP-170 headroom:       16,115 bytes

Catalog + legacy operator bridge stripped:
                                            7,591 bytes
EIP-170 headroom:                         16,985 bytes
```

Run:

```bash
python tools/measure_wallet_v3_catalog_strip.py --pretty
```

The tool separately records the current repository commit and the source file's
last-modified commit, plus the source hash, exact removed external and internal
functions, scratch-only legacy-interface adjustment, implicit-versus-pinned
target match, creation/runtime hashes, and both comparator variants. The
8,461-byte result reproduces the earlier reviewer figure.

This is an upper bound on available room, not an implementation disposition.
The compiler may omit source-retained shared helpers while they are unreachable;
the routed kernel will make some of them reachable again. Phase 0B must compile
a provisional kernel and compare the complete result plus a reviewed safety
reserve against this budget before issuing `PROCEED`, `PROCEED NARROWER`,
`REDESIGN`, or `STOP`.

### 17.1 First vertical slice

Use one real yield deposit:

```text
require IDLE and enter DISPATCHING
→ ActionRegistry lookup and ENABLED lifecycle check
→ routed stage-1 caller, action, permission, count, and cooldown checks
→ locked bounded extender prepare
→ exact decode and resolution through the wallet-bound routed LegoBook
→ routed stage-2 declared asset/Lego checks
→ existing pre-action accounting and starting-balance snapshots
→ UP_TO_WALLET_BALANCE resolution
→ wallet-opened session
→ extender acknowledgement using the wallet-resolved consumer
→ capability-aware Yield Lego consumption
→ exact allowance activation
→ protocol deposit
→ allowance cleanup
→ fixed-recipe Appraiser valuation and post-action limit checks
→ accounting and policy events using wallet-derived policyChargeUsd
→ cleanup
```

This is the yield-specific instance of section 9.1, not an alternative flow.
This single slice should answer:

- whether the kernel fits;
- whether Config/Sentinel changes remain small;
- whether the Config addition-only lifecycle validation and wallet registry
  getter remain small and preserve unrelated manager updates;
- whether the session adds acceptable gas;
- whether deposit-max parity works;
- whether exact consume-time authority works;
- whether the two-stage Sentinel/Config API remains smaller and clearer than a
  parallel policy path;
- whether the fixed yield-deposit valuation recipe reproduces or deliberately
  improves current manager-counter semantics at acceptable cost; and
- whether the architecture is easier to audit than the previous proposal.

---

## 18. Incremental implementation sequence

This sequence incorporates the useful incremental constraints from both
superseded proposals: retain the existing wallet as the architectural trunk;
preserve direct payment and security rails; revise Legos family by family;
start with a deposit-only vertical slice; reproduce EIP-170 bytecode baselines;
measure gas and Config/Sentinel size rather than estimating; and require every
phase to remain independently reviewable. Where either prior proposal conflicts
with this document's action IDs, closed permission vocabulary, bound registries,
session ordering, Config grant semantics, or fixed settlement modes, this
governing document controls.

### Phase 0A0 — Catalog-strip feasibility budget

This measurement is complete and reproducible through
`tools/measure_wallet_v3_catalog_strip.py`. It produces the 8,461-byte
catalog-stripped upper bound described in section 17. It does not issue an
implementation disposition by itself.

### Phase 0A — Complete current-state baseline

- capture the exact compiler, optimizer, EVM target, source, runtime, and
  creation evidence for every contract the vertical slice may change;
- record direct transfer/payment parity baselines;
- record legacy yield-deposit calls, fund movement, events, manager counters,
  `txUsdValue`, fee/loot/deposit-point effects, gas, calldata, and zero/missing/
  stale-price behavior;
- inventory every production Lego/action pair that currently requests external
  operator authority;
- classify each prospective artifact as isolated, new-generation-only,
  replaceable per wallet, or shared live governance infrastructure; and
- record the deployment and governance mechanism for each artifact without
  authorizing deployment.

### Phase 0B — Provisional design and first formal gate

- complete the independent permission-taxonomy research;
- decide the initial supported permission mask and manager action-ID bound;
- set every prepared-action and session array/byte bound;
- derive the first settlement modes and wallet-owned valuation recipes from
  current code;
- map legacy Lego-returned `txUsdValue` behavior to expected routed
  `policyChargeUsd` differences;
- provisionally define the capability-aware routed Lego ABI without a
  `txUsdValue` return;
- provisionally define `ActionSpec`, `PreparedAction`,
  `ActivatedCapability`, the phase-to-entry-point table, and the transient phase
  representation;
- pin the release compiler/optimizer/EVM target;
- keep ActionDataProvider mechanically thin and place routed policy
  interpretation in replaceable Sentinel entry points;
- design, but do not yet implement, the smallest named external operator-
  authority vocabulary;
- define the Config storage-boundary set-difference check;
- define the LegoBook no-repoint succession rule using the existing
  add/confirm delay;
- compile a provisional kernel/interface skeleton; and
- compare the complete candidate plus explicit wallet and Config safety reserves
  against the Phase 0A0 budget.

The recorded result is one of `PROCEED`, `PROCEED NARROWER`, `REDESIGN`, or
`STOP`. Interfaces remain provisional until Phase 1D; Phase 1C may propose
evidence-backed amendments, which Phase 1D must either ratify or reject.

### Phase 1A — Isolated registry candidate

- implement and test ActionRegistry without wiring it into production contracts;
- measure its maximum bounded record shape; and
- retain it only if the Phase 1D vertical slice ratifies the architecture.

### Phase 1B — Shared and new-generation infrastructure candidate

Treat the changed surfaces as separate risk classes:

1. **New-generation-only:** `UserWalletConfig` action-ID storage and its
   immutable thin ActionDataProvider interface.
2. **Replaceable per wallet:** routed Sentinel policy entry points and
   HighCommand coordination.
3. **Shared governance infrastructure:** the enforceable LegoBook no-repoint
   rule for routed and position-bearing IDs.

Add the wallet's bound ActionRegistry and routed-LegoBook constructor inputs and
getters, Config addition-only lifecycle validation, and the exact two-stage
policy API. Measure and review each risk class separately.

### Phase 1C — One yield-deposit vertical slice

- add the smallest complete transient session kernel;
- add one bounded Yield Extender;
- update one Yield Lego to consume exactly one capability;
- move one yield-deposit action behind one action ID;
- use `UP_TO_WALLET_BALANCE` for legacy deposit-max parity;
- derive `policyChargeUsd` through the fixed wallet recipe; and
- keep every unrelated direct rail and action unchanged.

### Phase 1D — Evidence, ratification, and release boundary

- run differential, signer, permission, malicious-component, phase, spend,
  settlement, bytecode, gas, calldata, and Base-fork evidence;
- compare every declared behavior difference;
- ratify or amend the provisional interfaces;
- record the exact commit, evidence paths, implementer, independent reviewer,
  owner, and disposition; and
- choose `PROCEED`, `PROCEED NARROWER`, `REDESIGN`, or `STOP`.

No Phase 1 contract is deployed, registered, or activated independently before
this gate. Until a separate deployment authorization exists, rollback means
reverting the unshipped candidate changes rather than leaving dormant Config
fields, registries, or LegoBook restrictions in production.

### Phase 2 — Complete yield family

- add withdrawal first and repeat the action-level evidence gate;
- add `YIELD_REBALANCE` only after its fixed settlement recipe is ratified;
- keep manager swap-containing rebalance inactive until wallet-verifiable trade
  observations exist; and
- preserve direct payment and security rails.

### Named operator-authority package — Before the first requiring action

Implement only the production authority shapes approved in Phase 0B. This
package must replace, not wrap, the arbitrary target-and-ABI mechanism and must
pass the section 16.9 tests before debt or rewards actions that depend on it.

### Phase 3 — Debt family

- add collateral and repay actions first;
- add borrow and remove-collateral after their observed settlement recipes pass;
- add one deleverage composite last;
- require every cumulative permission bit and named operator authority; and
- repeat the formal disposition gate after each bounded subphase.

### Phase 4 — Additional reviewed actions

- swaps;
- liquidity;
- rewards, after any required operator-authority package;
- staking, if the permission taxonomy approves it; and
- other actions that fit existing authority and settlement modes.

Payments remain a separate owner decision and are not bundled into these phases.

---

## 19. Explicitly abandoned complexity

The simplified proposal abandons these earlier recommendations:

| Earlier recommendation | Simplified decision |
|---|---|
| Open-ended permission IDs | Finite reviewed permission mask |
| Generic ID-keyed policy records | Existing Config fields and Sentinel semantics |
| Standalone ActionCodec | Extender-owned bounded `prepare` |
| Caller effect array/hash | Caller action-data hash plus prepared-action commitment |
| Generic effect constraints | Fixed session/spend invariants and settlement modes |
| Relative bound language | Exact or up-to-wallet-balance spend only |
| Generic execution-risk templates | Cumulative permission mask |
| Generic position-family registry | Entry/exit action pairing |
| Generic verifier registry | Deferred until a concrete need exists |
| Stable action with mutable routes | New action meaning/schema/extender gets a new action ID; new consumer code gets a new Lego ID |
| `FOLLOW_RECOMMENDED` | Removed |
| Accounting profile registry | Closed wallet settlement enum |
| Arbitrary policy extensibility | Core change required for new semantics |

---

## 20. Remaining owner decisions before implementation

The document-authority decision is complete: this proposal governs and the two
incremental proposals are superseded as independent plans. The remaining
implementation decisions are:

1. What is the final permission taxonomy?
2. Which permissions are implemented initially versus reserved?
3. Are manager action IDs stored per manager only, or also under a global
   manager ceiling?
4. What bounded maximum number of `bytes32` action IDs is acceptable in Config?
5. Should owners bypass action-ID approval when `canOwnerManage` is enabled?
6. What is the minimum review delay before a new action ID becomes `ENABLED`?
7. Which settlement modes are truly required by the first three action
   families?
8. Should action IDs include implementation/version semantics as recommended,
   or should stable semantic IDs be revisited later?
9. What entry/exit relationship is required for the first persistent-position
   action?
10. Do any first-phase actions genuinely require a protocol-specific verifier?
11. What wallet-verifiable trade-observation mechanism, if any, is acceptable
    for manager-routed composites?
12. When, if ever, should payment modes enter the routed system?
13. Does version one accept pinned reviewed-code trust for completeness of the
    declared policy asset and Lego sets, while the wallet enforces every
    declared item, or is wallet-derived completeness required despite the added
    typed-decoding or effect-model complexity?
14. Does the enforceable LegoBook no-repoint rule apply to every Lego ID, or to
    the recommended minimum of routed and wallet-position-bearing IDs?
15. Are the fixed wallet-derived `policyChargeUsd` recipes—and their deliberate
    counter, event, and gas differences from Lego-returned `txUsdValue`—accepted
    for each first-phase action?
16. Which confirmed production external-operator shapes belong in the first
    named authority package, and which integrations remain unsupported?
17. For each named operator authority, is access temporary, immediately revoked,
    or intentionally persistent, and what objective condition permits final
    revocation?
18. Is the provisional transient phase representation accepted after pinned-
    target bytecode and gas measurement?
19. What explicit wallet and Config bytecode safety reserves control the Phase
    0B and Phase 1D dispositions?
20. Is new-generation-only routed execution accepted as the implementation and
    coexistence boundary, with migration remaining outside this plan?

None of these decisions should be hidden inside the first extender
implementation.

---

## 21. Final architecture

```text
Existing UserWallet
    custody
    direct rails
    existing msg.sender owner/manager authentication
    bound ActionRegistry + routed LegoBook
    read-only binding getters for Config and inspection
    transient phase lock under a pinned EVM target
    session commitment
    exact consume-time allowances
    closed named external-operator authority, when separately approved
    fixed settlement

Existing UserWalletConfig
    existing manager settings and limits
    + bounded explicit routed action IDs
    + set-addition lifecycle validation through wallet-bound ActionRegistry
    retained EXIT_ONLY IDs survive unrelated edits; removed IDs cannot return

Thin immutable ActionDataProvider
    mechanically gathers Config data
    forwards exact stage-1 and stage-2 inputs
    does not own evolving routed policy semantics

Replaceable Sentinel / backpack
    existing checks
    + routed stage-1 caller/action/permission evaluation
    + routed stage-2 prepared asset/Lego evaluation
    + fail-closed unknown bits

Small ActionRegistry
    immutable bytes32 actionId and ActionSpec
    pinned extender
    fixed permission mask
    fixed settlement mode
    separate PENDING / ENABLED / EXIT_ONLY / DISABLED lifecycle
    entry/exit relationship

Pinned extender
    typed action interpretation
    bounded static preparation
    exact planBytes
    acknowledgement before consumption
    receives wallet-resolved consumer
    forwards sessionId + planBytes to that consumer
    no custody

Capability-aware Lego
    resolved only through the wallet-bound routed LegoBook
    immutable implementation per routed or position-bearing Lego ID
    successor code receives a new Lego ID
    consumes once
    receives exact resolved amounts
    routed ABI returns no txUsdValue
    performs one or multiple protocol calls
    returns outputs and residual committed assets

Named operator-authority package
    no Lego-supplied target, ABI string, or arbitrary calldata
    only approved production call shapes
    verified return/state semantics where supported
    explicit temporary or persistent lifecycle
    predecessor/successor overlap only for reviewed exits

Manager trade composites
    inactive until wallet-verifiable per-swap evidence exists

Fixed wallet settlement recipe
    capability consumption + balance/position/debt observations
    trusted Appraiser conversion with explicit zero/stale-price behavior
    wallet-derived policyChargeUsd

External protocols
```

The simplified design retains the PoC's strongest execution patterns while
accepting that permission semantics, wallet authority, and settlement behavior
should not be infinitely extensible.

---

## 22. Document governance and revision history

### 22.1 Current document map

| Document | Role | Authority |
|---|---|---|
| `simplified-user-wallet-action-architecture-codex.md` | Governing architecture for this track | **Governing; implementation still requires separate owner authorization** |
| `user-wallet-v3-implementation-plan-codex.md` | Measured work-package roadmap derived from this architecture | Draft implementation plan; contract changes and deployment require separate owner authorization |
| `ideal-wallet-action-architecture-codex.md` | Legacy filename pointer to the governing document | Pointer only; not independently authoritative |
| `incremental-extenders-proposal-claude.md` | Preserved independent analysis and provenance | **SUPERSEDED as a plan; useful sequencing and measurement constraints folded into sections 17–18** |
| `user-wallet-incremental-extender-proposal-codex.md` | Preserved earlier Codex incremental proposal | **SUPERSEDED as a plan** |
| `permission-action-taxonomy-research-prompt-codex.md` | Research instrument | Not an architecture proposal |
| `perms-research-summary-claude.md` | Independent synthesis of the permission-taxonomy research | Supporting analysis and recommendations only; not governing |
| `perms-research-summary-codex.md` | Codex synthesis of the permission-taxonomy research | Supporting analysis and owner-decision input only; not governing |
| `permission-research-incorporation-proposal-codex.md` | Proposed disposition of the two permission-research syntheses | Proposed decision record; non-governing pending independent review and owner disposition |
| `docs/poc/user-wallet/` | Archived PoC contracts, results, visual explanations, and superseded PoC-derived production track | Evidence and background only; PoC is on hold |

An implementation may claim conformance to “the plan” only by naming this
governing file and revision. Document selection does not authorize Phase 0,
contract edits, deployment, migration, or live transactions.

### 22.2 Revision log

| Date | Revision | Disposition |
|---|---|---|
| 2026-07-24 | Earlier 2,268-line Codex north-star draft | Overwritten while untracked; unavailable in git; known rejected mechanisms summarized in section 19 |
| 2026-07-24 | Simplified 1,305-line replacement | Introduced closed permissions, explicit manager action IDs, bounded preparation, exact consume-time authority, and fixed settlement |
| 2026-07-24 | Reviewer-hardening revision | Renamed file; added authentication, `bytes32` action IDs, defined prepared fields, one-way lifecycle, acknowledgement-before-consumption, action-data commitment, exact/clamp compatibility, trade-evidence gate, enforceable exit transitions, and expanded feasibility measurements |
| 2026-07-24 | Canonical-flow and lifecycle revision | Added the complete pre/post policy sequence; renamed the executable lifecycle state to `ENABLED`; defined `EXIT_ONLY`, zero-spend, passive-hook, asset-declaration, observed-settlement, resolved-consumer, and explicit byte/array measurement rules |
| 2026-07-24 | Consumer-identity and valuation revision (1,998 lines) | Clarified independent action/extender and Lego/consumer identity axes; required no-repoint Lego succession; defined wallet-derived `policyChargeUsd`; gave `EXIT_ONLY` a no-new-manager-grants effect; exposed the two-stage routed policy API; and defined spend-role, `ACTIVE`, and pre-accounting behavior |
| 2026-07-24 | Binding, grant-delta, and composite-settlement revision (2,159 lines) | Bound routed LegoBook and ActionRegistry per wallet; defined Config addition-only lifecycle checks; added `YIELD_REBALANCE`; made Appraiser trust explicit; removed routed `txUsdValue`; required an active session before acknowledgement; reused LegoBook's add/confirm delay; and separated ActionRegistry and LegoBook tests |
| 2026-07-24 | Owner authority selection and preservation revision (2,174 lines) | Owner selected this file as the governing architecture; superseded the two incremental proposals as independent plans; recorded their folded sequencing and measurement contributions; and authorized a docs-only preservation commit without authorizing implementation |
| 2026-07-24 | PoC namespace separation | Moved the paused experiment into `docs/poc/user-wallet/`, `contracts/poc/userWallet/`, and `tests/poc/userWallet/`; reserved the Wallet v3 contract and test paths for the new architecture; and preserved historical PoC names and evidence identities |
| 2026-07-24 | Separation review correction | Moved the earlier Codex proposal into this directory; corrected stale archived runtime evidence; disclosed archive path, node-ID, and source-hash rewrites; and documented fork/gas reproduction and path-history constraints |
| 2026-07-24 | Implementation-readiness clarification | Reproduced the 8,461-byte catalog-stripped feasibility bound; made ActionDataProvider a thin immutable adapter to replaceable Sentinel policy; specified transient-lock build pinning; added a closed named external-operator authority boundary; made routed execution explicitly new-generation-only; and split Phase 0/1 into measurement, provisional design, isolated/shared candidates, one yield slice, and a formal no-deployment-before-ratification gate |
| 2026-07-25 | Implementation-plan traceability revision | Defined the bounded, versioned, action-agnostic `PolicyContextV1` boundary; rejected opaque provider-extension semantics; required unsupported policy inputs to fail before action enablement; added S59–S60; distinguished Wallet v3's Prague build from the archived PoC's Cancun evidence identity; and aligned package/invariant traceability with the implementation roadmap |
| 2026-07-25 | Context-schema and research-provenance clarification | Made `PolicyContextV1` field-complete for the current action-data and manager-policy structures at both routed stages; clarified that `V1` names a frozen wallet-generation schema rather than an in-place upgrade path; and registered both permission-research syntheses as non-governing inputs |
| 2026-07-25 | Permission-proposal provenance registration | Registered the non-governing permission-research incorporation proposal for review; this map entry does not adopt its taxonomy or authorize implementation |

Future material revisions append a row here. A future replacement uses a new
file and marks this document `SUPERSEDED` in its header rather than rewriting
its history.
