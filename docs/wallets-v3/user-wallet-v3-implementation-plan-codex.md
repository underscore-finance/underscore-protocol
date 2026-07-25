# User Wallet v3 Implementation Plan — Codex

**Status:** Draft implementation roadmap; contract implementation and deployment
remain unauthorized

**Governing architecture:**
[`simplified-user-wallet-action-architecture-codex.md`](simplified-user-wallet-action-architecture-codex.md)

**Purpose:** Convert the governing architecture into bounded, independently
reviewable work packages with explicit dependencies, unchanged surfaces,
evidence, rollback rules, and owner gates.

**Migration design:** Out of scope

**Change-control rule:** This file is append-preserved. A future replacement
must use a new filename, mark this file `SUPERSEDED`, and update the governing
architecture's document map. Material revisions append to section 13. Nothing
in this document authorizes contract edits, production deployment, registry
changes, timelocked governance actions, migration, or use of funds without a
separate owner decision.

---

## 1. Outcome and recommended sequence

The implementation should answer one question at a time:

```text
Can the current wallet trunk create enough room?
    ↓
Can the provisional kernel and Config changes fit with reserves?
    ↓
Can one real yield deposit preserve policy, custody, and accounting?
    ↓
Can the remaining yield family reuse the same primitives?
    ↓
Can named external operator authority replace the generic raw-call bridge?
    ↓
Can debt and other families be added without expanding core authority again?
```

The roadmap is:

```text
0A0  Catalog-strip budget — completed
  ↓
0A   Current-state behavioral and contract baselines
  ↓
0B   Provisional interfaces + compiled skeleton + formal feasibility gate
  ↓
1A   Isolated ActionRegistry candidate
  ↓
1B   Shared/new-generation policy and governance candidates
  ↓
1C   One yield-deposit vertical slice
  ↓
1D   Differential evidence + interface ratification + owner disposition
  ↓
2A   Yield withdrawal
  ↓
2B   Yield rebalance
  ↓
AUTH Named external operator-authority package
  ↓
3A   Add collateral + repay
  ↓
3B   Borrow + remove collateral
  ↓
3C   Deleverage composite
  ↓
4    Swap / liquidity / rewards / other reviewed actions
```

Payments remain a separate owner decision.

No Phase 1 contract is deployed, registered, or activated independently before
Phase 1D. The packages are development and review boundaries, not permission to
ship partial infrastructure.

---

## 2. Controlling scope

### 2.1 What this plan builds

The plan incrementally derives a new wallet generation from the existing user
wallet:

- preserve wallet custody, direct transfers, ETH/WETH conversion, payment and
  security rails, asset accounting, fees, loot, and settlement responsibilities;
- keep existing `UserWalletConfig` policy concepts and existing Sentinel
  semantics;
- remove hardcoded action-family functions from the new wallet template as
  their routed replacements become ready;
- add open-ended action IDs with immutable reviewed implementations;
- add a bounded transient session kernel;
- add capability-aware Legos that pull exact wallet-resolved amounts;
- add only a finite, wallet-recognized authority vocabulary; and
- move action families one at a time behind formal evidence gates.

### 2.2 What this plan does not build

- no in-place upgrade mechanism for deployed wallets;
- no user migration design;
- no arbitrary target-and-calldata executor;
- no policy DSL;
- no open-ended permission registry;
- no generic effect or verifier language;
- no mutable implementation behind an existing action or Lego ID;
- no payment routing without a separate comparison and owner decision;
- no deployment before a reviewed release package exists; and
- no assumption that a stripped-core measurement proves the final kernel fits.

### 2.3 New-generation coexistence

Hatchery creates immutable wallet and Config instances from blueprint templates.
Existing wallet bytecode has no routed entry point, session kernel, or bound
ActionRegistry/routed-LegoBook getters. Its Config also stores
`ACTION_DATA_PROVIDER` as an immutable.

Therefore:

```text
Existing wallets
    continue using the legacy action catalog
    remain unaffected by Wallet v3 development

New Wallet v3 generation
    uses new wallet and Config blueprints
    receives the routed kernel and bound registries
    uses the new thin ActionDataProvider interface
```

Migration remains outside this plan. Differential tests compare an old-template
wallet and a new-template wallet under equivalent configuration and protocol
state.

---

## 3. Phase 0A0 feasibility evidence

### 3.1 Reproducible measurement

Run:

```bash
python tools/measure_wallet_v3_catalog_strip.py --pretty
```

Measurement source:

```text
Repository commit:
c8d3d002c374ce2cf7038d0e5de4fbd613478d39

Source:
contracts/core/userWallet/UserWallet.vy

Source SHA-256:
4d2ff16cbae6ade5b7d80bc560168c3a2b6584d6e783efc98f610aec30e331c3

Compiler:
Vyper 0.4.3

Optimizer:
codesize source pragma

Explicit EVM target:
prague
```

The implicit Vyper target and explicitly pinned `prague` target produced
byte-for-byte identical baseline runtime code during this measurement.

### 3.2 Results

| Variant | Runtime bytes | EIP-170 headroom | Interpretation |
|---|---:|---:|---|
| Current wallet | 23,032 | 1,544 | Reproduces governing baseline |
| Catalog stripped | 8,461 | 16,115 | Conservative upper bound used by this plan |
| Catalog and legacy operator bridge stripped | 7,591 | 16,985 | Comparator only; does not approve replacement authority |

The catalog-stripped variant removes these external action functions:

```text
depositForYield
withdrawFromYield
rebalanceYieldPosition
swapTokens
mintOrRedeemAsset
confirmMintOrRedeemAsset
addCollateral
removeCollateral
borrow
repayDebt
deleverage
claimIncentives
addLiquidity
removeLiquidity
addLiquidityConcentrated
removeLiquidityConcentrated
```

It also removes these catalog-only internal helpers:

```text
_depositForYield
_withdrawFromYield
_performSwapInstruction
_validateAndGetSwapInfo
_packMiniAddys
```

The scratch source removes the legacy `implements: wi` declaration because that
interface requires the deleted external catalog. This is a measurement-only
adjustment; the Wallet v3 interface must be specified separately.

### 3.3 What the result does and does not prove

It proves:

- the earlier 8,461-byte reviewer result is reproducible;
- removing the catalog can create materially more than the current 1,544 bytes
  of headroom; and
- a session kernel is not automatically ruled out by EIP-170.

It does not prove:

- the final kernel fits;
- Config fits;
- source-retained accounting helpers remain free—unreachable helpers may be
  absent from the stripped runtime until the new kernel calls them;
- the routed flow has acceptable gas;
- the operator bridge can be removed before a replacement exists; or
- any implementation package should proceed.

Phase 0B must compile the provisional skeleton and compare the complete result,
including reviewed bytecode reserves, against this budget.

---

## 4. Cross-cutting implementation decisions

### 4.1 Compiler and phase lock

The existing wallet already uses transient storage and its current runtime emits
`TLOAD`/`TSTORE`. The provisional Wallet v3 phase machine is transient:

```text
IDLE → DISPATCHING → ACTIVE → SETTLING → IDLE
```

Phase 0 must:

- pin Vyper version, optimizer, and EVM target in the Wallet v3 build harness;
- prove the explicit target reproduces the intended current baseline;
- record those settings with every bytecode and gas artifact;
- verify the selected deployment chain supports the emitted opcodes; and
- measure any persistent-storage alternative before considering it.

The default implementation direction is transient unless evidence requires a
different choice.

### 4.2 Thin immutable ActionDataProvider

Each current Config binds `ACTION_DATA_PROVIDER` immutably. Sentinel and
HighCommand are replaceable through existing backpack controls.

The new split is:

```text
UserWalletConfig
    ↓ calls
thin immutable ActionDataProvider
    gathers existing Config data
    forwards exact stage inputs
    ↓ calls
replaceable Sentinel
    stage 1: caller + action + permission
    stage 2: prepared assets + Legos
```

ActionDataProvider must not become the evolving policy engine. Sentinel owns
substantive routed-policy interpretation through distinct entry points, and the
legacy direct entry point retains its existing meaning.

### 4.3 Closed external operator authority

The current wallet accepts a Lego-supplied target, ABI string, and calldata
shape. Confirmed production needs include Ripe's one-argument Undy-Lego access
and Euler rewards' two-argument operator toggle.

The replacement is not implemented during the yield-deposit slice. Phase 0
designs it, and the `AUTH` package implements it before the first requiring debt
or rewards action.

Each admitted authority shape must bind:

- named authority kind;
- reviewed external target;
- exact user/wallet and operator arguments;
- exact enable/disable semantics;
- exact capability-aware Lego ID and codehash;
- return-value validation;
- observable resulting state when available;
- temporary or persistent lifetime;
- revocation and emergency behavior; and
- predecessor/successor behavior while an exit dependency survives.

Unsupported external authority requires a wallet-core change. Action
registration cannot invent a new authority shape.

### 4.4 No partial production rollout

The default rollback model is source-level:

```text
Package fails before 1D
    → revert the unshipped candidate changes
    → deploy nothing
    → register nothing
    → leave current wallets and shared infrastructure unchanged
```

Any proposal to deploy a dormant registry or shared LegoBook change before 1D
requires a separate owner authorization and its own rollback plan.

---

## 5. Work-package contract

Every package must contain:

1. **Entry evidence:** exact prerequisite commit, decisions, and passing gates.
2. **Question answered:** one falsifiable reason the package exists.
3. **Changed surfaces:** exact contracts, interfaces, storage, ABI, and tests.
4. **Untouched surfaces:** explicit scope boundaries.
5. **Fund and authority flow:** before, during, and after the action.
6. **Security invariants:** governing invariant numbers tested by the package.
7. **Measurements:** runtime, creation size, gas, calldata, and shared-contract
   impact where applicable.
8. **Rollback:** what is reverted, retained, or deliberately left dormant.
9. **Evidence record:** commands, outputs, artifact hashes, and expected
   differences.
10. **Disposition:** `PROCEED`, `PROCEED NARROWER`, `REDESIGN`, or `STOP`.

### 5.1 Risk classes

| Class | Meaning | Examples |
|---|---|---|
| Isolated | No existing production caller depends on the new artifact | ActionRegistry before wiring |
| New-generation-only | Address/code is fixed into newly created Wallet v3 instances | Wallet blueprint, Config blueprint, ActionDataProvider |
| Replaceable per wallet | Existing governance path can select a new implementation for a wallet | Sentinel, HighCommand |
| Shared governance | Change affects registry behavior used by multiple wallet generations | LegoBook no-repoint rule |
| Integration-specific | New reviewed extender or Lego ID | Yield Extender, capability-aware Yield Lego |

Risk classification does not authorize deployment. It determines review depth,
regression scope, and rollback evidence.

### 5.2 Gate record

Each formal gate appends:

```text
Gate:
Commit:
Evidence paths:
Changed contracts:
Unchanged paths verified:
Implementer:
Independent reviewer:
Owner:
Disposition:
Conditions:
Deferred questions:
```

The implementer prepares the evidence. An independent reviewer checks it. The
owner selects the final disposition when an owner gate is named.

---

## 6. Phase 0 packages

### 6.1 Package 0A0 — Catalog-strip budget

**Status:** Complete.

**Question:** Can removal of the hardcoded action catalog create plausible
kernel headroom?

**Result:** The source transformation reproduced an 8,461-byte runtime with
16,115 bytes of EIP-170 headroom.

**Disposition:** Measurement only. The formal disposition waits for 0B's
compiled provisional skeleton.

**Rollback:** None; production source was not transformed.

### 6.2 Package 0A — Current-state baseline

**Question:** What exact behavior and cost must the first routed deposit preserve
or deliberately change?

**Changed surfaces:** Tests, measurement helpers, and documentation only.

**Required evidence:**

- current UserWallet, UserWalletConfig, ActionDataProvider, Sentinel,
  HighCommand, LegoBook, selected Yield Lego, and Hatchery sizes;
- current deployment/blueprint creation sizes and gas;
- old yield-deposit owner and manager flows;
- exact asset and approval movement;
- manager count, cooldown, asset, Lego, and USD-limit behavior;
- fee, loot, asset-registration, yield-profit, and deposit-point behavior;
- events and returned values;
- legacy Lego-returned `txUsdValue`;
- Appraiser behavior for normal, zero, missing, and stale prices;
- calldata and Base L1 data cost;
- direct transfer, ETH/WETH, payment, and security-rail baselines;
- current operator-authority inventory by Lego and action;
- current compiler default, explicit target, optimizer, and opcode evidence; and
- deployment-artifact and governance-delay inventory.

**Untouched:**

- no contract ABI or storage change;
- no deployment;
- no registry or timelock action;
- no migration design.

**Stop condition:** Any baseline that cannot be reproduced or explained blocks
the dependent 0B decision. It does not get replaced by an estimate.

**Exit:** Evidence is complete, reproducible, and reviewed.

### 6.3 Package 0B — Provisional design and compiled skeleton

**Question:** Can a narrowly bounded session architecture and required shared
interfaces fit with explicit safety reserves?

**Inputs:**

- completed 0A evidence;
- permission-taxonomy research;
- initial owner decisions from section 11;
- governing architecture revision named by commit.

**Provisional definitions:**

- `ActionSpec`;
- action lifecycle;
- `PreparedAction`;
- `SpendRequest`;
- `ActivatedCapability`;
- transient phase representation;
- session commitment;
- extender `prepare` and acknowledgement interfaces;
- capability-aware Yield Lego ABI;
- Config action-ID set representation;
- ActionDataProvider stage-one/stage-two forwarding ABI;
- Sentinel routed-policy entry points;
- LegoBook protected-ID rule;
- first fixed settlement recipe; and
- named operator-authority design, without implementation.

**Compiled candidates:**

- wallet skeleton with bound ActionRegistry/routed-LegoBook getters and phase
  kernel;
- Config skeleton with bounded action IDs;
- thin ActionDataProvider interface;
- Sentinel routed entry points;
- HighCommand coordination shape;
- ActionRegistry maximum record shape; and
- LegoBook protected-ID change.

**Required comparison:**

```text
complete candidate runtime
+ reviewed wallet safety reserve
≤ 24,576 bytes

complete Config blueprint/runtime
+ reviewed Config safety reserve
≤ applicable creation/runtime limits
```

The owner selects the reserve before the gate; the implementation does not use
all measured headroom by default.

**Permitted amendment:** Interfaces are provisional. Phase 1C may propose a
minimal evidence-backed change. Phase 1D must record and ratify it; silent drift
is not allowed.

**Gate:** `PROCEED`, `PROCEED NARROWER`, `REDESIGN`, or `STOP`.

**Rollback:** Discard the skeleton and retain only the evidence when the
disposition is `REDESIGN` or `STOP`.

---

## 7. Phase 1 packages

### 7.1 Package 1A — Isolated ActionRegistry

**Question:** Can action identity, immutable implementation binding, and one-way
lifecycle remain small and independently auditable?

**Candidate files:**

```text
contracts/walletsV3/ActionRegistry.vy
interfaces/WalletV3ActionRegistry.vyi
tests/walletsV3/actionRegistry/
```

Final names are frozen in 0B.

**Changes:**

- bounded immutable `ActionSpec`;
- action ID uniqueness;
- pinned extender/codehash;
- permission mask and settlement mode validation;
- pending delay;
- `ENABLED`, `EXIT_ONLY`, and terminal `DISABLED`;
- immutable entry/exit relationships; and
- read-only resolution.

**Untouched:**

- current UserWallet and Config;
- Sentinel and ActionDataProvider;
- LegoBook;
- Hatchery and MissionControl;
- production registries.

**Evidence:**

- full section 16.1 test set;
- maximum-size runtime and governance gas;
- malicious registration and lifecycle tests; and
- no storage or call dependency on current wallets.

**Rollback:** Delete/revert the unshipped isolated candidate if Phase 1D does not
ratify the architecture.

### 7.2 Package 1B1 — New-generation Config and thin ActionDataProvider

**Question:** Can explicit manager action IDs and two-stage forwarding fit
without creating a second policy engine?

**Risk class:** New-generation-only.

**Changes:**

- Wallet v3 Config blueprint derived from current `UserWalletConfig`;
- bounded action-ID set per manager;
- duplicate rejection;
- addition-only lifecycle validation through the wallet's bound registry getter;
- retained `EXIT_ONLY` behavior;
- starter manager begins with no routed action IDs;
- immutable thin ActionDataProvider with stage-one/stage-two forwarding; and
- exact Wallet v3 Config/ActionDataProvider interfaces.

**Untouched:**

- payee, cheque, whitelist, ownership, freezing, ejection, payment, and security
  semantics;
- existing deployed Configs and their immutable providers;
- Sentinel policy meaning.

**Evidence:**

- Config runtime/blueprint size after each field and method group;
- HighCommand call and update gas;
- retained/removed/re-added/reordered action-ID tests;
- new manager, starter manager, and migration-caller boundary tests without
  designing migration;
- direct Config regression suite; and
- proof that ActionDataProvider contains forwarding/data assembly rather than
  new policy decisions.

**Rollback:** Revert both candidate blueprints/interfaces. Nothing is deployed.

### 7.3 Package 1B2 — Replaceable Sentinel and HighCommand entry points

**Question:** Can routed policy reuse current data and helpers while preserving
direct behavior?

**Risk class:** Replaceable per wallet.

**Changes:**

- Sentinel stage one: caller, action ID, count/cooldown, activation/expiry, and
  cumulative permission mask;
- Sentinel stage two: prepared asset and Lego sets;
- HighCommand coordination for bounded manager action IDs;
- separate direct and routed entry points; and
- fail-closed unknown bits.

**Untouched:**

- existing direct Sentinel entry-point meaning;
- existing counters and post-action update timing;
- payment/payee/cheque policy;
- production backpack registrations.

**Evidence:**

- old direct suite passes unchanged;
- stage-one and stage-two tests prove no duplicate counting;
- specific and global manager restrictions both apply;
- unknown action/permission data fails;
- replaceability path is tested but not exercised in production; and
- runtime/gas impact is recorded separately for Sentinel and HighCommand.

**Rollback:** Revert the unregistered candidate implementations.

### 7.4 Package 1B3 — Shared LegoBook protection

**Question:** Can routed and position-bearing Lego IDs be made non-repointable
without breaking current registry use?

**Risk class:** Shared governance.

**Changes:**

- protected-ID state or equivalent smallest enforceable rule;
- existing add/confirm delay reused for successor IDs;
- in-place update rejected for protected IDs;
- predecessor remains resolvable for surviving exits; and
- wallet-bound routed book cannot be substituted through UndyHq slot 3.

**Untouched:**

- existing unprotected registry behavior unless the owner selects a broader
  rule;
- production Lego mappings;
- no ID is protected or registered during development.

**Evidence:**

- section 16.2 tests;
- full current LegoBook regression suite;
- governance gas and bytecode;
- current-v2 lookup compatibility; and
- predecessor/successor exit fixture.

**Rollback:** Revert the unshipped shared-contract change. This package may not
be deployed early merely because other Phase 1 code is ready.

### 7.5 Package 1C — Yield-deposit vertical slice

**Question:** Does one real action validate the complete architecture at
acceptable complexity and cost?

**Changes:**

- new Wallet v3 blueprint derived from the current wallet trunk;
- hardcoded catalog removed from that new template;
- bound ActionRegistry and routed-LegoBook constructor inputs/getters;
- transient phase/session kernel;
- one immutable yield-deposit action ID;
- one bounded Yield Extender;
- one capability-aware Yield Lego under a new Lego ID;
- `UP_TO_WALLET_BALANCE` deposit-max behavior;
- exact allowance activation only during consumption;
- fixed yield-deposit settlement and Appraiser valuation; and
- Wallet v3 tests and differential fixtures.

**Exact call and fund flow:**

```text
Caller
  → Wallet v3 locks
  → ActionRegistry resolution
  → Config / thin ActionDataProvider / Sentinel stage 1
  → bounded Yield Extender prepare
  → wallet-bound LegoBook resolution
  → Sentinel stage 2
  → current pre-action accounting
  → wallet resolves exact USDC spend
  → wallet commits session
  → extender acknowledges
  → exact Yield Lego consumes
  → wallet activates exact allowance
  → Yield Lego pulls USDC and deposits
  → position token returns to wallet
  → wallet clears allowance
  → wallet observes result and Appraises policy value
  → current post-action accounting and limits
  → session clears
```

**Authority flow:**

```text
Before consume: no allowance, no operator grant
During consume: exact ERC20 allowance to exact pinned Lego
After execution: allowance zero
```

The initial slice creates no external protocol operator grant.

**Untouched:**

- direct transfer and ETH/WETH functions;
- payment, cheque, payee, Billing, freeze, eject, migration, and recovery paths;
- legacy deployed wallets;
- debt, swap, liquidity, rewards, and payment routing;
- operator-authority implementation.

**Evidence:**

- all governing section 16 tests applicable to the slice;
- old/new differential behavior;
- owner, manager, AgentWrapper, unauthorized caller matrix;
- manager action-ID and permission matrix;
- malicious registry, extender, Lego, token, Config, and callback matrix;
- exact deposit-max and allowance lifecycle;
- event, fee, loot, asset, yield, and deposit-point effects;
- normal/zero/missing/stale Appraiser behavior;
- runtime, creation size, deployment gas, transaction gas, calldata, and L1 data
  cost;
- direct-rail regression/parity; and
- Base-fork execution under the documented harness.

**Rollback:** Revert all Phase 1 candidate changes. No production component has
been deployed or registered.

### 7.6 Package 1D — Ratification gate

**Question:** Is the vertical slice sufficiently safe, understandable, bounded,
and economical to become the trunk for additional actions?

**Required record:**

- exact commit and source hashes;
- all changed contracts and interfaces;
- all intentionally untouched surfaces;
- compiled settings;
- wallet/Config/shared-contract reserves;
- differential evidence and every expected difference;
- gas and calldata results;
- open security assumptions;
- interface amendments since 0B;
- rollback confirmation;
- independent review; and
- owner disposition.

**Dispositions:**

- `PROCEED`: ratify interfaces and begin Phase 2A.
- `PROCEED NARROWER`: retain the trunk but remove named unready surface area.
- `REDESIGN`: preserve evidence and revise a load-bearing mechanism.
- `STOP`: do not use the routed architecture as the new wallet trunk.

Only a separate authorization after this gate may start production deployment
planning.

---

## 8. Expansion packages

### 8.1 Phase 2A — Yield withdrawal

Add withdrawal as a separate action ID and fixed settlement recipe.

Required proof:

- correct vault-token authorization and amount handling;
- underlying returns directly to the wallet;
- depletion and asset-deregistration parity;
- fee and yield-profit parity;
- no operator grant;
- exact owner/manager permission behavior; and
- independent action-level disposition.

### 8.2 Phase 2B — Yield rebalance

Treat rebalance as one wallet action and one capability consumption. The
reviewed Lego may perform multiple protocol calls.

Required proof:

- source position reduction;
- target position increase;
- committed residual return;
- fixed `YIELD_REBALANCE` settlement;
- predecessor exit availability;
- cumulative `YIELD | TRADE` when a swap exists; and
- manager activation withheld until wallet-verifiable per-swap observations
  satisfy existing counters and slippage policy.

### 8.3 AUTH — Named external operator authority

**Entry:** Phase 0 inventory and owner-selected authority shapes.

**Question:** Can required protocol operator access replace the generic
target-and-ABI raw call without creating arbitrary authority?

**Changes:**

- one or more named, finite authority shapes;
- reviewed target/operator binding;
- exact return/state validation;
- grant/revoke events;
- temporary or persistent lifecycle;
- emergency revocation;
- predecessor/successor overlap for reviewed exits; and
- removal of the routed path's dependency on the legacy generic helper.

**Not automatically supported:** The legacy helper's three generic calldata
branches are not copied wholesale. Only confirmed production shapes approved in
Phase 0 are implemented.

**Gate:** Full governing section 16.9 evidence plus `PROCEED`,
`PROCEED NARROWER`, `REDESIGN`, or `STOP`.

### 8.4 Phase 3A — Add collateral and repay

Move the lower-risk debt spend actions first.

Required proof:

- named operator authority where the protocol requires it;
- exact collateral/debt token spend;
- wallet-observed position/debt result;
- fixed debt settlement;
- approved collateral and Lego rules;
- owner exit path; and
- no borrow or collateral removal hidden inside the action.

### 8.5 Phase 3B — Borrow and remove collateral

These expand wallet exposure and therefore require stronger observed-settlement
and limits evidence.

Required proof:

- debt/collateral changes independently observed;
- borrowed assets return to the wallet;
- collateral remains within current policy;
- manager limits charge wallet-derived value;
- usable repay and exit actions remain; and
- no unsupported authority shape is introduced.

### 8.6 Phase 3C — Deleverage

One action ID may represent the reviewed multi-step workflow:

```text
release collateral
→ optional exchange
→ repay debt
→ return residual assets
```

Required proof:

- one consumer and one capability consumption;
- cumulative `DEBT | TRADE` when exchange occurs;
- wallet-verifiable per-swap observations for manager execution;
- fixed debt settlement across all steps;
- atomic rollback; and
- a simpler direct owner-only route if manager trade evidence remains
  unavailable.

### 8.7 Phase 4 — Additional families

Candidate order:

1. simple swaps with wallet-observed input/output;
2. non-concentrated liquidity;
3. concentrated liquidity and NFT custody;
4. rewards after any required operator authority;
5. staking only if the permission taxonomy approves it; and
6. other actions that fit existing permission, authority, and settlement
   vocabularies.

Every new action:

- gets a new immutable action ID when meaning, schema, or extender changes;
- gets a new Lego ID when consumer code changes;
- requires explicit manager opt-in;
- reuses existing authority and settlement primitives or stops for a core
  design change; and
- repeats the bounded action-level evidence gate.

### 8.8 Separate payment decision

Existing direct payment, payee, cheque, Billing, and `preparePayment` paths stay
unchanged. No payment action enters routing until a separate document compares:

- current direct behavior and gas;
- required authorization lifetime;
- cancellation and liveness;
- reserved versus liquid balance semantics;
- owner, manager, payee, and Billing roles; and
- whether routing improves the product enough to justify new complexity.

---

## 9. Deployment and governance inventory

This inventory makes operational cost visible. It does not authorize any
deployment.

| Artifact or change | Risk/reach | Intended selection path |
|---|---|---|
| Wallet v3 blueprint | New-generation-only | MissionControl wallet template after Switchboard review |
| Wallet v3 Config blueprint | New-generation-only | MissionControl Config template after Switchboard review |
| ActionRegistry | New isolated registry, later bound per wallet | Wallet-generation configuration |
| Routed LegoBook binding | Immutable per Wallet v3 instance | Wallet constructor |
| Thin ActionDataProvider | Immutable per Config | WalletBackpack value copied by Hatchery at creation |
| Routed Sentinel | Replaceable per Config | WalletBackpack default for new wallets; existing setter only if separately authorized |
| HighCommand update | Replaceable/shared coordinator | WalletBackpack default and existing validation path |
| LegoBook protected-ID rule | Shared governance infrastructure | New reviewed LegoBook deployment or approved upgrade path |
| Yield Extender | New immutable action implementation | ActionRegistry pending/enable lifecycle |
| Capability-aware Yield Lego | New integration implementation | New timelocked LegoBook ID |
| MissionControl template values | Affects future wallet creation | SwitchboardAlpha timelocked template update |
| WalletBackpack component values | Affects future Config creation | Existing registry governance |

Before a release plan exists, Phase 0A records:

- exact artifact count;
- constructor dependencies;
- deployment ordering;
- applicable timelocks;
- registry confirmations;
- rollback before activation;
- emergency disablement after activation; and
- which changes affect only future wallets versus selectable existing backpack
  components.

---

## 10. Verification and evidence model

### 10.1 Local correctness

- compile every candidate under the pinned settings;
- run the complete existing user-wallet suite;
- run the complete Wallet v3 suite;
- run direct-rail regression tests;
- run source/document link and formatting checks; and
- record exact skipped or deselected tests.

### 10.2 Differential parity

For each moved action compare:

- callers;
- permissions;
- assets and Legos;
- fund flow;
- protocol position;
- fees and accounting;
- manager counters;
- events;
- failure behavior;
- approval cleanup;
- return values;
- gas and calldata; and
- deliberate valuation-source differences.

Expected differences are written before the test assertion.

### 10.3 Adversarial matrix

- malicious extender output;
- malicious or repointed Lego;
- malicious token callbacks;
- wrong codehash;
- wrong session, action, plan, caller, or deadline;
- repeated consumption;
- omitted asset or Lego;
- unapproved permission bit;
- nested direct action;
- callback during pre-accounting, `ACTIVE`, or settlement;
- operator grant to wrong target/user/operator;
- non-reverting false authority result; and
- predecessor/successor exit conflicts.

### 10.4 Size and gas

Record after every meaningful change:

- runtime bytes;
- creation/blueprint bytes;
- safety reserve remaining;
- deployment gas;
- action execution gas;
- calldata bytes;
- Base L1 data cost;
- Appraiser call count;
- Config/HighCommand manager-update gas; and
- ActionRegistry/LegoBook governance gas.

### 10.5 Fork evidence

Use the repository's documented Boa/py-evm Base harness. Do not substitute an
Anvil receipt assumption. Record pinned block, fee conditions, token/protocol
addresses, Appraiser inputs, and any calibration mismatch as an evidence stop.

---

## 11. Owner decision register

### Required for the Phase 0B gate

1. Initial implemented and reserved permission bits.
2. Per-manager action-ID maximum and any global ceiling.
3. Owner action-ID bypass behavior under `canOwnerManage`.
4. ActionRegistry review delay.
5. Action-ID implementation/version semantics.
6. Initial `PreparedAction` and session bounds.
7. Wallet and Config bytecode safety reserves.
8. First yield-deposit settlement and valuation recipe.
9. Pinned compiler optimizer and EVM target.
10. Acceptance of new-generation-only routed execution with migration excluded.
11. Whether declared prepared sets rely on pinned-code completeness or require
    additional wallet-derived proof.
12. Minimum LegoBook protected-ID scope.

### Required before yield rebalance

13. `YIELD_REBALANCE` fixed recipe.
14. Owner-only versus manager availability when a swap exists.
15. Acceptable wallet-verifiable trade observations.

### Required before AUTH and debt

16. Initial named operator-authority shapes.
17. Temporary versus persistent authority per shape.
18. Required return and external-state verification.
19. Revocation and emergency behavior.
20. Predecessor/successor simultaneous-authority rule.
21. First debt settlement recipes and entry/exit relationships.

### Deferred

22. Payment routing.
23. New permission bits not required by an approved action.
24. Protocol-specific verifiers.
25. Arbitrary relay or wallet-level typed signatures.
26. Migration.

No deferred decision is silently answered by implementation.

---

## 12. Working file map

The exact candidate source map is frozen in Phase 0B. The expected shape is:

```text
contracts/walletsV3/
    UserWallet.vy
    UserWalletConfig.vy
    ActionDataProvider.vy
    ActionRegistry.vy
    types/
    extenders/

contracts/core/walletBackpack/
    Sentinel.vy              # routed entry points, direct behavior retained
    HighCommand.vy           # action-ID coordination

contracts/registries/
    LegoBook.vy              # protected-ID enforcement

contracts/legos/
    ...                      # capability-aware implementations under new IDs

interfaces/
    ...                      # exact Wallet v3, registry, extender, capability ABIs

tests/walletsV3/
    measurement/
    actionRegistry/
    config/
    policy/
    session/
    yield/
    authority/
    differential/
    gas/
```

The existing `contracts/core/userWallet/` and its tests remain the legacy
comparison authority. Wallet v3 may derive code from them, but does not rename or
silently rewrite the legacy source out from under differential tests.

---

## 13. Document governance and revision log

### 13.1 Authority

This implementation plan is subordinate to the governing architecture. If they
conflict, implementation stops until the documents are reconciled and reviewed.
The visual website is explanatory and never overrides either Markdown document.

### 13.2 Revision log

| Date | Revision | Disposition |
|---|---|---|
| 2026-07-24 | Initial implementation roadmap | Added the reproduced catalog-strip budget; new-generation coexistence; thin immutable ActionDataProvider boundary; named operator-authority package; 0A/0B/1A/1B/1C/1D decomposition; no-partial-deployment rule; yield/debt expansion packages; artifact inventory; verification model; rollback rules; owner decisions; and uniform formal dispositions |

Future material revisions append a row. A replacement marks this file
`SUPERSEDED` rather than overwriting its history.
