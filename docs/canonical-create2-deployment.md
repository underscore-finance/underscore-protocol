# Canonical CREATE2 Deployment

Underscore's cross-chain wallet address family depends on the deterministic
deployment proxy at `0x4e59b44847b379578588920cA78FbF26c0B4956C` (the
"0x4e59 singleton"). Treat its address, runtime, deployment salts, and every
contract's creation bytecode as protocol-level constants.

The helper at `scripts/canonical_create2.py` verifies the singleton and prepares
deployment calldata. It intentionally does not hold keys, sign, or broadcast.

## Required preflight

Run this against every target chain before computing or sending a deployment:

```sh
UNDERSCORE_RPC_URL=https://target-chain.example \
  .venv/bin/python scripts/canonical_create2.py preflight
```

The command queries `eth_getCode` at the exact canonical address and fails
unless all of these match:

- address: `0x4e59b44847b379578588920cA78FbF26c0B4956C`
- runtime length: `69` bytes
- runtime code hash:
  `0x2fa86add0aed31f33a762c9d88e807c475bd51d0f52bd0955754b2608f7e4989`
- exact expected runtime bytes

The expected 69-byte runtime is:

```text
7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffe03601600081602082378035828234f58015156039578182fd5b8082525050506014600cf3
```

An address with missing or mismatched code is a hard stop. Do not send
deployment calldata to it and do not accept an explorer label as evidence.

## Prepare a deployment

Compile once with the repository-pinned Vyper version and settings, retain the
exact creation bytecode, and assign a fixed 32-byte salt. Constructor arguments
are part of creation bytecode for CREATE2 purposes and must be appended exactly
once before running this command.

The V1 salts are `keccak256` of the exact ASCII label bytes (no quotes, prefix,
suffix, whitespace, or null terminator):

| Artifact | ASCII label | Literal bytes32 salt |
| --- | --- | --- |
| UserWallet implementation V1 | `UNDERSCORE_USER_WALLET_IMPL_V1` | `0xda9e0e08155d5e49d144d1878faacbcf25fec5790c5ca4cfea6c03788d80329d` |
| UserWalletConfig implementation V1 | `UNDERSCORE_USER_WALLET_CONFIG_IMPL_V1` | `0xc54fd3bd79f3df3298ee349c311ac2d48d1dd8bdbc6e4c795ec0b851c7321227` |
| Wallet factory V1 | `UNDERSCORE_WALLET_FACTORY_V1` | `0x97049e1342f95e7c1a137d37a08a26977defb40ca4763dd6c6d05cef6bce600a` |

Print these constants from the helper with:

```sh
.venv/bin/python scripts/canonical_create2.py artifact-salts
```

The machine-readable V1 release manifest is
`docs/deployment-manifests/wallet-v1.json`. Its top-level `artifacts` section is
the one cross-chain source of implementation and factory salts, bytecode hashes,
and addresses. A chain entry cannot override those fields; different artifact
bytes require a separately named and versioned address family.

The separate `chains` map is keyed by the decimal `eth_chainId` string. Each
ready entry pins its chain-local UndyHq and approved Hatchery:

```text
"chains": {
  "<decimal-chain-id>": {
    "cutoverStatus": "ready",
    "undyHq": "<checksummed-address>",
    "hatcheryRegistryId": 5,
    "missionControlRegistryId": 2,
    "approvedHatcheryAddress": "<checksummed-address>",
    "approvedHatcheryRuntimeCodehash": "<bytes32>",
    "approvedLegacyWalletTemplateAddress": "<checksummed-address>",
    "approvedLegacyWalletTemplateRuntimeCodehash": "<bytes32>",
    "approvedLegacyConfigTemplateAddress": "<checksummed-address>",
    "approvedLegacyConfigTemplateRuntimeCodehash": "<bytes32>",
    "missionControlTemplateGeneration": "legacy-pair"
  }
}
```

Entries remain explicitly `pending` until implementation and factory bytecode,
the factory's chain-configuration authority, the recovery path, and per-chain
Hatchery and legacy-template artifacts are all frozen. Pending entries
intentionally omit unfrozen artifact, Hatchery, and MissionControl template
addresses and bytecode hashes. Change an artifact or chain to `ready` only after
freezing every required value and completing the recovery/runtime-size release
gates. The generation label is descriptive metadata, not proof of live state;
the cutover preflight verifies the exact live pair independently.

`UserWalletFactory.vy` temporarily declares
`WALLET_FACTORY_ADMIN = 0x0000000000000000000000000000000000000000`.
That zero address is a deliberately fail-closed development placeholder, not a
deployable configuration. The shared manifest records the same value under
`artifacts.walletFactory.admin`. While it remains in either source or manifest,
every artifact in this family must remain `pending`: the manifest drift gate
rejects a ready artifact, and both fixed-salt deployment preparation and the
Hatchery cutover command stop before any RPC call or transaction payload. Replace
the one source literal and manifest value together with the human-approved final
admin; a missing, duplicated, computed, malformed, or mismatched declaration is
also a hard stop.

```sh
UNDERSCORE_RPC_URL=https://target-chain.example \
  .venv/bin/python scripts/canonical_create2.py prepare \
  --salt 0xda9e0e08155d5e49d144d1878faacbcf25fec5790c5ca4cfea6c03788d80329d \
  --initcode-file ./out/UserWallet.creation.hex
```

The JSON output contains:

- the singleton address and verified runtime hash
- normalized salt, initcode length, and initcode hash
- the predicted deployed address
- a zero-value transaction object with `to` and raw `data`

For any of the three fixed V1 artifact salts, `prepare` also loads `--manifest`
(the shared V1 manifest by default) and requires the factory admin release gate
to be final. The selected artifact must also be `ready`, and the supplied
initcode length, hash, salt, and predicted address must match its shared manifest
entry. This prevents both preparing any V1 deployment while the zero admin
placeholder remains and later replaying stale placeholder-compiled factory
bytecode after the source admin changes. Arbitrary salts remain available for
unrelated CREATE2 operations and do not represent a blessed V1 artifact.

The singleton has no ABI selector. Its calldata is exactly:

```text
salt (32 bytes) || initcode (remaining bytes)
```

Submit the emitted transaction through the approved operations signer or
multisig workflow. Before signing, independently compare the salt, initcode
hash, predicted address, and transaction data with the release manifest. After
mining, fetch code at the predicted address and compare its runtime code hash
with the manifest. A CREATE2 collision reverts; if code already exists, accept
it only when the expected runtime hash matches exactly.

For the wallet system, deploy the UserWallet implementation first. Compile
UserWalletConfig with that exact fixed UserWallet implementation address for
its counterpart check, deploy UserWalletConfig, then compile and deploy the
factory directly, not through a proxy, with both fixed implementation addresses
and runtime code hashes. The current factory's
`isUserWalletConfig(config, salt)` predicate must derive the expected config
proxy from a true compile-time config-implementation constant in that immutable
runtime, not a storage value populated or rotated after deployment. Preserve
the exact deployment payloads so future chains replay bytes rather than
rebuilding from source.

## Atomic wallet-pair deployment invariant

The deterministic factory is the only valid deployer of this wallet generation.
It must be direct immutable code at the canonical address, never a proxy or an
initializable implementation-address registry. Its exact runtime and
`isUserWalletConfig(config, salt)` predicate are part of the release manifest;
the predicate must derive from the factory's compile-time config-implementation
constant and expose no mutable override. Its normal creation entry point must
authenticate the caller as the current Hatchery at registry ID `5` in the
factory's pinned chain-local UndyHq. Never accept a caller-supplied registry or
Hatchery address as that authorization root.

The implementations contain no chain-varying immutables. Their one-shot proxy
initializers write UserWallet WETH; UserWalletConfig UndyHq, WETH, ETH,
ActionDataProvider, and min/max time locks; and Ownership UndyHq plus min/max
ownership time locks into proxy storage. ActionDataProvider has no
post-initialization setter and remains non-rotatable for an existing wallet.
The implementation constructors lock their own storage and cannot initialize
as user wallets.

For each owner/group/tier tuple, the factory must execute this sequence in one
transaction:

1. Derive `walletSalt = keccak256(abi.encode(owner, groupId,
   starterAgentTier))`.
2. Create the UserWalletConfig proxy and UserWallet proxy with that same salt
   and Vyper 0.4.3's exact 54-byte minimal-proxy initcode. Both proxies must
   exist before initialization begins.
3. Initialize UserWalletConfig first. It derives the tuple salt internally,
   authenticates its own exact 45-byte runtime and factory CREATE2 namespace,
   checks the wallet address against the same factory and salt with the
   hardcoded UserWallet implementation, and stores the wallet pointer and salt
   once.
4. Initialize UserWallet with only WETH and the config address. It requires the
   config to point back to it and reads the verified config salt. It first
   authenticates its own exact proxy runtime and CREATE2 deployer, then
   staticcalls that proven direct factory's `isUserWalletConfig(config, salt)`
   predicate to authenticate the config as the factory's same-salt proxy. The
   predicate derives from the factory's compile-time config-implementation
   constant and has no mutable override.
5. Only after both initializers succeed may Hatchery update Ledger and emit the
   completed wallet-creation result.

There is no `UserWalletConfig.setWallet` call and no supported two-transaction
deployment flow. The factory must expose no path that creates one or both
proxies without completing both initializers. Any failed check must revert the
whole transaction, including both CREATE2 operations.

Never mix generations. Existing legacy wallet/config pairs continue running on
their already deployed code, but neither deterministic implementation may be
registered as a MissionControl blueprint or paired with a legacy counterpart.
Keep MissionControl's legacy `walletTemplate` and `configTemplate` values as a
matched pair and deprecated after the new Hatchery cutover.

## Recovery-mode invariants

Recovery must use the same canonical factory, owner, group ID, and explicit
starter-agent tier as normal creation. A recovery deployment with no starter
agent and no managers still commits the original tier into the salt; using a
different or zero tier produces a different address and cannot recover the
published wallet.

The recovery entry point must not enforce the normal
`MissionControl.numUserWalletsAllowed` limit against
`Ledger.numUserWallets()`. Legacy wallet counts can differ between chains, and
a chain-local count must never prevent deployment at an already funded
counterfactual address. Normal Hatchery creation continues to enforce the
existing cap for this release. Separately review whether the cap should count
only deterministic-generation wallets, but do not change that behavior as part
of recovery implementation without an explicit governance decision.

Do not mark a chain recoverable until the owner-authorized recovery deployment
and sweep path is implemented, the no-agent/no-manager configuration is tested,
and the final implementation runtimes remain below EIP-170. Address prediction
and availability of the canonical singleton alone are insufficient.

As of 2026-09-04, before the recovery sweep is integrated, the checked-in
implementation runtimes are `24,155` bytes for UserWallet (`421` bytes of
EIP-170 headroom) and `23,739` bytes for UserWalletConfig (`837` bytes of
headroom). Further code-relocation and recovery-sweep prototypes have not landed
and are not part of this address-family snapshot. Remeasure both implementations
after integrating recovery;
[User Wallet Runtime Byte Budget](user-wallet-config-byte-budget.md) records the
measurement method and current baseline.

The implementation hashes in the V1 manifest use `boa.load_partial` with the
listed source paths relative to the repository root. This detail is consensus
critical for CREATE2: invoking Vyper through a different input path can change
deployment metadata and therefore the creation-bytecode hash even when the
runtime bytecode is identical. The manifest drift test recompiles through that
exact entrypoint, but operations should deploy archived, manifest-matched bytes
rather than rely on a future recompile.

The exact compiler build is `Vyper 0.4.3+commit.bff19ea2`, recorded in the
manifest as `compiler.longVersion`. `requirements.txt` pins the `0.4.3` release,
and the manifest test separately checks the installed build's long version.
Vyper's 54-byte `create_minimal_proxy_to` initcode is a compiler-codegen detail,
not a language or EIP-1167 guarantee. Compile the implementations and factory
with this same build.

Before publishing any wallet address, run an end-to-end integration using the
final production factory bytecode: create both proxies through its actual
`create_minimal_proxy_to` path, independently predict both addresses from the
recorded 54-byte initcode, verify the deployed 45-byte runtimes embed the
approved implementations, and complete initialization. A unit test of the
standalone predictor is not sufficient for this release gate.

V1 address families are immortal once published. Never reuse a V1 salt for
changed creation bytecode. Every future implementation version requires new,
distinct implementation salts and its own versioned factory with a distinct
factory salt. Preserve every prior version's bytecode and manifest: each prior
factory must remain deployable through its original deterministic deployer on
every future supported chain so wallets in every published address family stay
recoverable. Deploying or registering a newer factory does not retire an older
family.

## One-wallet-per-tuple and migration release gate

The V1 factory makes `(initial owner, groupId, starterAgentTier)` unique within
the factory family. That is a product behavior change, not merely an address
derivation detail: the legacy Hatchery could create an unlimited number of
wallets for the same owner with the default group ID. Do not mark V1 ready until
the human has explicitly accepted this behavior or approved a different
identity design.

It also conflicts with the current Migrator for an unchanged production owner.
Migrator requires two distinct Ledger-registered wallets whose **current**
owners and group IDs match. Once the V1 production tuple for an owner and group
has created one wallet, the factory cannot create a second same-tier
destination, and using the existing wallet as its own destination is rejected.
Therefore a V1-to-V1 production migration for the same unchanged initial-owner
identity inside one factory family is strictly impossible, not merely limited
to one successful migration.

A legacy Base wallet has one fresh V1 deterministic counterpart available when
the two wallets have the same current owner and group ID: the legacy CREATE
address did not consume the V1 factory tuple. This is an address-availability
limit, not a one-shot flag in Migrator; eligible existing pairs may stage and
execute migrations again. If that V1 wallet later needs a second fresh wallet
for the same unchanged identity, however, there is no second V1 production
destination. A later versioned factory family could provide a new address, but
V1 alone cannot. Changing group ID makes Migrator reject the pair; using a
STAGING or DEV tier requires the privileged non-production creation lane and
changes starter-agent semantics, so it is not a valid production fallback.

The salt records the initial owner, while Migrator compares current owners.
Consequently, two distinct V1 wallets created under different initial-owner
namespaces can become migratable after their ownership converges. For example,
V1 PROD `(A, G)` can transfer ownership to B and then migrate to V1 PROD
`(B, G)`. This changes custody, requires the full ownership-change flow, and is
not equivalent to obtaining a second wallet for the same unchanged identity
(and may be unavailable to contract owners). Do not describe the broader
same-tier or same-factory case as cryptographically impossible.

The existing Hatchery tests expose five concrete consequences and must remain
visible until this decision is made:

- `test_create_user_wallet_limits` creates five production wallets for one
  owner at default group `1` to reach the global creation cap. V1 permits at
  most the first tuple; a global cap test would need distinct identities.
- `test_create_user_wallet_paused` only exercises pause/unpause, but its one
  post-unpause Alice/group-1/PROD creation collides with the session ambassador
  fixture using that tuple. V1 makes formerly harmless shared default identities
  collection-order dependent unless the product defines which call owns them.
- `test_create_user_wallet_prod_uses_mission_control_starter` makes one
  otherwise-valid Alice/group-1/PROD creation after changing the global starter
  agent, but that tuple is already occupied by the session ambassador. It can no
  longer use the default identity to observe the new configuration.
- `test_non_prod_starter_config_overwrite_and_clear_all_envs` similarly creates
  STAGING and DEV wallets before and after changing their defaults. An already
  consumed non-production tuple cannot be recreated with the replacement
  starter agent.
- `test_non_prod_creator_zero_blocks_non_prod_only` proves STAGING and PROD are
  separate authorization lanes, but its final Alice/group-1/PROD creation
  collides with the session ambassador. The authorization property remains,
  while that occupied default tuple can no longer demonstrate it.

This is pervasive in the migration suite, not five isolated tests. A static
audit found same-family duplicate production identities in 37 of 39
creation-bearing `test_migrate_funds.py` tests and 53 of 57
`test_migrate_config.py` tests (90 of 96 total). All four creation-bearing
SwitchboardBravo migration tests collide under V1: two successful-migration
wrappers and two negative authorization tests fail before reaching their
intended assertions. Replacing groups would make Migrator reject; replacing
PROD with STAGING/DEV would conceal the production incompatibility rather than
test it.

## Atomic Hatchery cutover gate

This is a fund-safety release blocker: the new zero-argument implementation
sources and the Hatchery cutover must ship as one coordinated protocol release.
Publishing implementation and factory code in advance is harmless, but they
must not become wallet-creation templates while the old Hatchery is active.

Never register `UserWallet.vy` or `UserWalletConfig.vy` from this release as
MissionControl blueprints. Their zero-argument constructors deliberately lock
the implementation instance, while Switchboard's template validation checks
only nonzero addresses and contract code—not generation compatibility.

The silent dead-wallet combination is a **new UserWallet template plus a legacy
UserWalletConfig template under the old Hatchery**. The old Hatchery appends
legacy constructor arguments, but a zero-argument constructor ignores them;
the resulting wallet is locked and unusable even though creation and the legacy
config's `setWallet` call succeed. Funding it is an irrecoverable loss. Using
both new templates under the old Hatchery is also invalid, but fails loudly
because the old Hatchery calls the removed `setWallet` entry point. Never rely
on that revert as deployment validation.

Use this activation order:

1. Deploy and verify the two implementations and the factory without changing
   MissionControl template fields or the live Hatchery registry entry.
2. Complete and verify the factory's one-shot chain configuration. Its pinned
   UndyHq must be the manifest value, its implementation addresses and runtime
   code hashes must match the frozen artifacts, and its normal entry point must
   resolve the authorized Hatchery through UndyHq registry ID `5`.
3. Freeze, deploy, and verify the new Hatchery. In `chains["<chainId>"]`, pin the
   UndyHq, set `cutoverStatus` to `ready`, record the exact approved Hatchery
   address and runtime code hash, and record the two approved legacy
   MissionControl template addresses and their deployed runtime code hashes.
   Retain `missionControlTemplateGeneration: "legacy-pair"` as an operator-facing
   label, but never treat it as evidence. Never use a placeholder.
4. Pause the old Hatchery, then complete the governed UndyHq registry cutover so
   ID `5` resolves to the new Hatchery. Do not leave both creation generations
   live concurrently.
5. Run the exact-hash gate:

   ```sh
   UNDERSCORE_RPC_URL=https://target-chain.example \
     .venv/bin/python scripts/canonical_create2.py cutover-preflight \
     --manifest docs/deployment-manifests/wallet-v1.json
   ```

6. Enable wallet creation through the new release only after the command reports
   `status: ok`. The command reads `eth_chainId`, selects only that chain's entry,
   and uses its pinned UndyHq. It resolves Hatchery at registry ID `5`, resolves
   MissionControl at registry ID `2`, then calls MissionControl's public
   `userWalletConfig()` getter. The first two ABI words must be the manifest-pinned
   legacy `walletTemplate` and `configTemplate` addresses, and `eth_getCode` for
   both must match their manifest-pinned runtime hashes. A missing or pending
   chain, missing approval, decode failure, zero or changed registry pointer,
   either template address mismatch, absent code, or any runtime hash mismatch is
   a hard stop. A manifest generation label cannot override a live mismatch.

The cutover preflight is a point-in-time **off-chain** gate. Operations must run
it immediately before activation and prevent governance drift afterwards. It
proves the registry and template state only at the instant it runs; it is not a
standing on-chain guarantee.

7. Create a canary through Hatchery and independently verify both predicted
   proxy addresses, both exact 45-byte runtimes, the reciprocal wallet/config
   pointers, the shared stored salt, initialized flags, owner/group/tier-derived
   identity, chain-local dependencies, starter-agent state, and Ledger entry.
   The transaction must contain the factory's config-first then wallet
   initialization sequence and leave no uninitialized proxy on any failure.

The new Hatchery no longer consumes MissionControl's `walletTemplate` and
`configTemplate` values for creation, although preserved validation may still
read them as nonzero. Leave both fields unchanged and mark them deprecated at
cutover. The cutover gate deliberately rejects a mixed live pair even if the
manifest still says `legacy-pair`; any governance template-registration workflow
must run this gate before activation. Any later cleanup must happen only after
the new Hatchery registry cutover passes the exact-hash gate.

## Cross-chain onboarding constraints

Ledger does not record whether a wallet came from the legacy CREATE path or a
deterministic factory generation. Only deterministic-generation wallets may be
published or described as cross-chain identities. A legacy Base wallet address
cannot be reproduced by the new factory on another chain; directing a user to
fund that legacy address elsewhere can strand the funds permanently. Until an
on-chain generation marker exists, every API and deployment inventory must
carry this distinction outside Ledger and fail closed when it is unknown.

Reject onboarding any chain that shares **both** its `chainId` and AgentSender
contract address with an already supported chain. That duplicate pair collapses
the intended cross-chain signature-domain separation.

AgentSender authentication is ECDSA-only and does not support ERC-1271 contract
signatures. An undeployed contract owner therefore cannot authorize recovery on
a chain where the owner contract has no code. Treat recovery for that owner and
chain as unsupported unless a separately reviewed authorization design is added.

## Wallet salt encoding

The wallet salt is fixed by the protocol:

```text
keccak256(abi.encode(owner, groupId, starterAgentTier))
```

The preimage is exactly 96 bytes: three left-padded 32-byte ABI words in this
order:

```text
word 0: address owner (12 zero bytes || 20-byte address)
word 1: uint256 groupId
word 2: uint256 starterAgentTier (PROD=1, STAGING=2, DEV=4)
```

The creator is not part of this salt. Do not use `abi.encodePacked`, concatenate
the 20-byte owner directly, encode the tier as a one-byte enum, or substitute a
zero-based tier index. Each produces a different wallet address.
The helper rejects all tier values outside the currently reachable Vyper flag
values `{1, 2, 4}` rather than publishing an unusable counterfactual address.

The helper exposes both the 96-byte preimage and its hash for cross-language
verification:

```sh
.venv/bin/python scripts/canonical_create2.py predict-vyper-wallet \
  --factory 0x0000000000000000000000000000000000000001 \
  --implementation 0x0000000000000000000000000000000000000002 \
  --owner 0x0000000000000000000000000000000000000003 \
  --group-id 1 \
  --starter-agent-tier 1
```

## Vyper minimal-proxy prediction

Vyper 0.4.3's `create_minimal_proxy_to` uses 54 bytes of CREATE2 initcode:

```text
602d3d8160093d39f3363d3d373d3d3d363d73
|| implementation (20 bytes)
|| 5af43d82803e903d91602b57fd5bf3
```

Predict a wallet proxy with:

```sh
.venv/bin/python scripts/canonical_create2.py predict-vyper-clone \
  --factory 0x0000000000000000000000000000000000000001 \
  --implementation 0x0000000000000000000000000000000000000002 \
  --salt 0x0000000000000000000000000000000000000000000000000000000000000003
```

The frequently copied OpenZeppelin creation sequence starts with
`3d602d80600a3d3981f3` and produces 55-byte initcode. Both variants deploy the
same 45-byte EIP-1167 runtime, but their initcode hashes—and therefore their
CREATE2 addresses—differ. Do not use an OpenZeppelin clone prediction helper
for proxies created by Vyper 0.4.3.

The address formula in both cases is:

```text
last20(keccak256(0xff || deployer || salt || keccak256(initcode)))
```

## Bootstrapping the 0x4e59 singleton

The canonical singleton itself was deployed using a pre-signed, replayable
legacy transaction from the one-time signer
`0x3fAB184622Dc19b6109349B94811493BF2a45362`. The transaction uses nonce zero,
an unprotected pre-EIP-155 signature, and a fixed gas price of 100 gwei. Those
bytes cannot be changed without changing the recovered signer and therefore the
CREATE address.

That bootstrap is not universally available. It is permanently impossible if
nonce zero has already been mined for that signer on the target chain. It is
also impossible if the chain rejects unprotected legacy/pre-EIP-155
transactions or cannot execute the fixed 100-gwei transaction under its fee
rules. Incompatible opcode behavior or different code already occupying the
target address are also hard stops.

Use the upstream
[Arachnid deterministic-deployment-proxy repository](https://github.com/Arachnid/deterministic-deployment-proxy)
as the source for the signer, raw bootstrap transaction, and funding procedure.
Confirm chain compatibility and query the signer's mined and pending nonce
before funding or broadcasting. In particular, a mined failing transaction
consumes nonce zero without installing the singleton, permanently preventing
the canonical deployment on that chain.

Use this ordered fallback runbook; never silently substitute addresses:

1. Ask the chain operator for a genesis or system predeploy of the exact 69-byte
   runtime at the exact canonical `0x4e59b44847b379578588920cA78FbF26c0B4956C`
   address. This preserves the canonical address family. Run the required
   preflight and proceed only if it passes exactly.
2. If that is impossible, and only before publishing any addresses for the new
   family, select and pin a chain-supported deterministic deployer address,
   runtime, and code hash. Allocate a new fixed-salt manifest; regenerate every
   implementation, factory, and wallet address; give the family a distinct
   name; and require every participating future chain to support that exact
   deployer.
3. Mark every chain that lacks the original deployer family as unsupported for
   recovery of existing addresses. Never present the new-family address as an
   alias or substitute for an original-family wallet.

Step 2 creates a **different address family**. CREATE2 commits to the deployer
address, so the same salt and initcode through any deployer other than the
canonical `0x4e59b44847b379578588920cA78FbF26c0B4956C` produces a different
implementation address, factory address, and ultimately different user-wallet
addresses. It cannot deploy contracts at already published 0x4e59-derived
addresses and cannot recover funds sent to those counterfactual addresses.
