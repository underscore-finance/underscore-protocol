# Robinhood protocol deployment

Matching the Base `UndyHq` address on Robinhood is an operational convenience,
not a security property. Wallet address parity is a separate, deferred design.

## Address-critical account

The only authorized deployer for this migration is
`0x14051A647C2B647363739ccfD4B008AfEeb8FD8e`. `UndyHq` must be its nonce-5
CREATE and must land at `0x44Cf3c4f000DFD76a35d03298049D37bE688D6F9`.

The deployer EOA must be under exclusive operational control from preflight
until the nonce-5 deployment is confirmed. Do not queue, replace, cancel, or
send any other transaction from it. The migration requires `latest == pending`
before every address-critical transaction and pins the expected nonce again at
the signer boundary. It never retries an ambiguous broadcast automatically.

The expected sequence from a fresh Robinhood account is:

| Nonce | Operation | Result |
| ---: | --- | --- |
| 0 | Deploy `UserWallet` blueprint | `0xAfF6aE05285c543B1Bbb6298d023c613B07817CB` |
| 1 | Deploy `UserWalletConfig` blueprint | `0x5aB75ef37A30736f38F637a9129348AD327EfD08` |
| 2 | Deploy `AgentWrapper` blueprint | `0x0E7064202c4F906Adc4D9F6D3C92470b62F624F1` |
| 3 | Deploy `DefaultsRobinhood` | `0x55eeA103abA26FA85fb1359E2D2e1961d1B46218` |
| 4 | Zero-value self-send | no contract |
| 5 | Deploy `UndyHq` | `0x44Cf3c4f000DFD76a35d03298049D37bE688D6F9` |

Constructor arguments and bytecode do not affect these CREATE addresses. Use
the Robinhood profile and Robinhood-specific values; only deployer and nonce
determine the address.

## Ledger path and signing preflight

Do not translate a wallet UI label such as "account 1" directly into
`--ledger 1`. Common Ethereum wallet software uses three incompatible Ledger
derivation conventions:

| Convention | Path at index `N` |
| --- | --- |
| BIP44 address index (MetaMask default) | `m/44'/60'/0'/0/N` |
| Ledger Live account | `m/44'/60'/N'/0/0` |
| Ledger Legacy (MEW/MyCrypto) | `m/44'/60'/0'/N` |

With the Ledger unlocked and the Ethereum app open, resolve the path before
any signing:

```shell
PYTHONPATH=. .venv/bin/python scripts/ledger_signing_smoke.py --discover-path
```

This is read-only. It derives 15 addresses (all three conventions at `N=0..4`),
prints a table in this form, matches the pinned deployer, and reports its latest
and pending nonces from chain ID 4663 when the Robinhood RPC is available:

```text
Convention             N  Derivation path        Address
BIP44 address index    0  m/44'/60'/0'/0/0       0x...
Ledger Live account    1  m/44'/60'/1'/0/0       0x...
Ledger Legacy          1  m/44'/60'/0'/1         0x...

Pinned deployer match    m/<resolved path> (<convention> N=<index>)
Migration signer flag   --ledger-path "m/<resolved path>"
```

The installed `ledgereth` implementation derives each address with the Ethereum
app's `GET_ADDRESS_NO_CONFIRM` APDU (`P1=0x00`), so it does not request an
address-display confirmation. Discovery does not sign or broadcast. If none of
the 15 rows is
`0x14051A647C2B647363739ccfD4B008AfEeb8FD8e`, stop. Either the connected
device is not the Base deployer or the path is outside the approved scan; both
require a human decision. Do not choose an index by convention or extend the
search during the launch. A nonzero or unavailable live nonce does not prevent
the read-only path result from being printed; it means state must be reconciled
before a deployment resume.

After path discovery passes, prove one real-size contract-creation signature
against a local Anvil fork. In two shells, run:

```shell
anvil --fork-url "$ROBINHOOD_MAINNET_RPC_URL" --chain-id 4663 --port 8545 --silent
```

```shell
PYTHONPATH=. .venv/bin/python scripts/ledger_signing_smoke.py
```

Alternatively, if Anvil is on `PATH`, the second command can manage it:

```shell
PYTHONPATH=. .venv/bin/python scripts/ledger_signing_smoke.py --manage-anvil
```

The full smoke payload is 24,376 bytes, matching the largest Robinhood core
CREATE data: `VaultRegistry`'s 24,248-byte compiler bytecode plus 128 bytes of
constructor arguments. It streams as 95 full 255-byte chunks plus a final
partial chunk. The smoke broadcasts only to local Anvil; the real Robinhood RPC
is used for read-only chain/nonce checks and as the fork source. Unlike
discovery-only mode, the signing path fails closed unless both the latest and
pending live deployer nonces are zero. Do not use
`--toy-payload` as launch approval because it does not exercise this streaming
path.

Expect these device behaviors:

- With blind signing disabled, the Ethereum app rejects every contract
  creation. Enable blind signing before the smoke test.
- Chain ID 4663 is unknown to the Ethereum app, so it presents an
  unknown-network warning on every transaction prompt. Verify the displayed
  chain ID rather than treating the warning as exceptional.
- A roughly 24 KB initcode payload streams for several seconds before the
  device displays anything. This can look like a hang. Do not unplug or lock
  the device while it is streaming; older firmware may fail here even when a
  toy payload signs.

## Running and resuming

Set `ROBINHOOD_MAINNET_RPC_URL`, activate the repository virtual environment,
and select both the Robinhood chain and profile explicitly. The CLI refuses a
Robinhood deployment with the Base profile and validates chain ID 4663 before
examining or consuming a nonce. `MigrationRunner` repeats that check before it
loads any Robinhood migration, so direct runner use and a mislabeled local
`boa` RPC fail before they can write a Robinhood manifest or mutate state.

Rehearse against the pinned Robinhood fork with:

```shell
PYTHONPATH=. .venv/bin/python scripts/migrate.py \
  --fork \
  --safe 0x14051A647C2B647363739ccfD4B008AfEeb8FD8e \
  --chain robinhood-mainnet \
  --blueprint robinhood \
  --environment v1 \
  --start-timestamp 0000 \
  --end-timestamp 0000 \
  --block 54618507 \
  --single
```

For production, paste the exact path emitted by discovery when prompted below,
then use the explicit hardware path. Invoking Robinhood without `--ledger-path`
or `--ledger` now fails closed unless an explicit `DEPLOYER_PRIVATE_KEY` is
present; it never falls back to the public Anvil test key.

```shell
printf '%s' 'Paste resolved Ledger path (m/...): '
IFS= read -r LEDGER_PATH
PYTHONPATH=. .venv/bin/python scripts/migrate.py \
  --ledger-path "$LEDGER_PATH" \
  --chain robinhood-mainnet \
  --blueprint robinhood \
  --environment v1 \
  --start-timestamp 0000 \
  --end-timestamp 0000 \
  --single
```

Fork rehearsals write to a `-fork` history directory and cannot populate the
production history directory. Logs and manifests are not proof of progress.
On every run, the core migration precompiles all sources and reconstructs
progress from the live account nonce plus exact runtime bytecode at every
predicted address. At nonce 6 it additionally verifies the initial `UndyHq`
governance, registry, token, and timelock state.

Do not use positional transaction-log replay on Robinhood. The CLI rejects
`--is-retry` because a serialized return value is not proof that the intended
state exists on chain. Resume the nonce-critical migration by rerunning it with
the explicit `--start-timestamp 0000`; its on-chain state machine authenticates
the live nonce, code, and constructor state before taking any action.

If a broadcast result is ambiguous, stop and inspect both latest and pending
state before rerunning. For a nonce at or below 5, an authentication failure is
reported as requiring manual reconciliation and the migration sends nothing;
do not describe the nonce-5 target as lost merely because automatic resume was
refused. If nonce 5 has been consumed without the exact `UndyHq` deployment,
the target address is unreachable by this deployer.

`MigrationRunner` does not durably distinguish a pre-broadcast signer refusal
from a broadcast or receipt failure: both raise `MigrationError`, and neither
attempt is appended to the migration log or manifest. The live exception and
terminal boundary matter:

- A device rejection, lock, disconnect, or timeout before
  `Transaction signed on Ledger!` originates in `sign_transaction`; Boa has no
  raw transaction to broadcast, so that attempt spent no nonce. Exit the
  process, reconnect and unlock the Ledger, reopen the Ethereum app, verify
  latest/pending nonce and the expected live state, then retry in a fresh CLI
  process. Do not retry in the same Boa environment because its preflight
  simulation may be dirty.
- Once `Transaction signed on Ledger!` appears, any later transport or receipt
  failure is potentially post-broadcast. Stop and preserve the terminal output.
  Reconcile the transaction hash if one was printed, receipt, latest/pending
  nonce, exact runtime code, manifest, registry IDs, pending registry action,
  and WalletBackpack configuration as applicable. Never blindly rerun an
  ambiguous post-HQ CREATE: a mined deployment whose response was lost may have
  consumed the nonce without recording its address.

On a pristine deployer, plan for **66 physical confirmations through `0011`**:
25 CREATEs, 26 registry stage/confirm writes, 14 WalletBackpack child writes,
and the nonce-4 alignment self-send. About 25 prompts are blind-signed contract
creations, and several stream more than 90 chunks. `1000` adds 11 writes, for
**77 confirmations in the intended full run**. As currently checked in,
Robinhood governance and its codehash are intentionally unapproved, so `1000`
fails closed before its first prompt; 77 applies only after that release blocker
is resolved. This is a long session: disable device auto-lock if policy permits,
keep the cable stable, and have the stop/reconcile procedure ready.

Robinhood explorer verification is intentionally skipped until an authoritative
endpoint is configured. RPC logs redact credentials, path tokens, and query
parameters.

Rewards, bonus rewards, starter agents, creators, and security signers are
fail-closed in `DefaultsRobinhood`. They require separate governance approval;
the initial migration does not deploy integration Legos, vaults, price
configuration, or earn vaults.

## Post-HQ sequence

Nonce alignment ends after `UndyHq` is deployed. Every later address is resolved
through a registry, so do not apply padding, fixed-nonce signing, or address
parity requirements to migrations `0001` and later. Normal dependency ordering
still matters, and every migration verifies the exact existing registry prefix
before its first transaction.

Any post-HQ address map produced by the Boa fork test is a fork-only artifact,
not a production prediction. Boa's in-process calls consume no deployer nonce;
live registration stage/confirm calls do. Base's committed manifest makes the
difference concrete: `MissionControl` is the deployer's nonce-9 CREATE at
`0x910FE9484540fa21B092eE04a478A30A6B342006`, while the Robinhood Boa fork
assigns that same nonce-derived address to `Switchboard`. Only nonce-5
`UndyHq` is an intentional production parity guarantee; do not extrapolate
later production addresses from the fork literals.

Do not use `migration_history/base-mainnet/v1/current-manifest.json` as evidence
of live Base parity: that generation stopped in November 2025. The checked-in
`v1.1/current-manifest.json` matches live Base through HQ ID 11; live IDs 12 and
13 are later payments work on a separate branch and are out of this release.
Robinhood authenticates its own manifest continuity against pinned
source-derived runtime hashes and live constructor state; this runbook does not
claim byte-for-byte or registry-tail equivalence with current Base.

The intended initial sequence is:

| Migration | Deployment and registration |
| --- | --- |
| `0001` | `Ledger` at UndyHq ID 1 |
| `0002` | `MissionControl` using `DefaultsRobinhood`, at ID 2 |
| `0003` | empty core `LegoBook` registry at ID 3; no Legos or `LegoTools` |
| `0004` | `Switchboard` at ID 4; Alpha and Bravo at Switchboard IDs 1 and 2 |
| `0005` | original CREATE-based `Hatchery` at ID 5, using the nonce-0/1 wallet blueprints |
| `0006` | `LootDistributor` at ID 6, pinned to the live RH Ripe registry and RIPE token |
| `0007` | `Appraiser` at ID 7, pinned to the live RH Ripe registry |
| `0008` | `WalletBackpack` at ID 8, with Kernel, Sentinel, HighCommand, Paymaster, ChequeBook, Migrator, and ActionDataProvider wired |
| `0009` | `Billing` at ID 9 |
| `0010` | empty `VaultRegistry` at ID 10; no earn vaults or vault configuration |
| `0011` | empty `Helpers` registry at ID 11; no `LegoTools` or `LevgVaultTools` |
| `1000` | lock setup-time registries/actions, grant Switchboard the ID-4 token-blacklist permission, and hand UndyHq to the approved RH governance contract |

SwitchboardCharlie is deliberately absent. Its current entry points administer
vaults, vault allowlists, and Lego/yield configuration; nothing in the initial
no-vault core path resolves Switchboard child ID 3. Register it later, before
vault support, through the timelocked Switchboard registry.

`LegoTools` is also deferred rather than deployed empty. Its constructor fixes
two router tokens and eleven LegoBook IDs as immutables and rejects an empty
LegoBook, so deploying it before the RH Lego set is approved would permanently
encode placeholder routing data. Deploy and register it under Helpers only with
the later Lego rollout; `LevgVaultTools` remains part of the deferred vault set.

Run the post-HQ sequence only after every release blocker below is resolved:

```shell
PYTHONPATH=. .venv/bin/python scripts/migrate.py \
  --ledger-path "$LEDGER_PATH" \
  --chain robinhood-mainnet \
  --blueprint robinhood \
  --environment v1 \
  --start-timestamp 0001 \
  --end-timestamp 1000
```

Robinhood requires an explicit start timestamp and rejects `--is-retry`.
Positional log strings are not evidence of live registry or setup state. Every
non-idempotent transaction is sent once; after any ambiguous RPC result, stop
and reconcile the manifest, live pending state, confirmed registry IDs, and
configured backpack items before continuing.

For an interrupted post-HQ deployment, the migration must authenticate an
existing candidate against runtime bytes materialized from the pinned source,
compiler, and constructor arguments before it adopts or registers that
address. A runtime hash copied from the mutable migration manifest is only a
consistency check; it is not an independent release trust root. Freeze the
sources and compiler before production, and never use a handful of public
getters as a substitute for exact runtime authentication plus constructor-state
validation.

`AddressRegistry.pendingNewAddr` is keyed by candidate address and the contract
does not enumerate every pending candidate. If both the deployment manifest
and the candidate address are lost after an ambiguous registration start, do
not deploy another candidate. Recover the address from transaction receipts or
registry events and reconcile that exact pending entry first; otherwise an
unknown pending write can survive until governance handoff.

Immediately before `1000`, scan registry events for unresolved pending add,
update, or disable actions in UndyHq, Switchboard, LegoBook, VaultRegistry, and
Helpers. AddressRegistry does not expose an enumerable pending-action list, so
exact address prefixes and empty known action IDs cannot prove the absence of
every pending registry write. Treat this event scan as a mandatory manual
precondition before the irreversible timelock and governance handoff.

Also scan every `SwitchboardBravo.LockedSignerSet` event since MissionControl
deployment, collect each signer address that ever appeared, and require
`MissionControl.isLockedSigner(signer) == false` for all of them immediately
before handoff. The signer-lock mapping is not enumerable and this write does
not advance Bravo's action ID, so runtime, action-ID, and constructor-state
checks cannot prove that it is empty without event-derived keys.

## Release blockers and intentionally absent values

- Wallet-level deterministic deployment is deferred to a separate release.
  Migration `0005` deploys the original seven-argument Hatchery, whose CREATE
  flow consumes the original `UserWallet` and `UserWalletConfig` blueprints
  recorded by `DefaultsRobinhood`. Its runtime and WETH dependency are pinned
  independently before deployment; no wallet-factory artifact is part of this
  Robinhood release.
- No RH governance contract is approved in the profile. Migration `1000` fails
  before any lock or state change until both a nonzero contract address and its
  exact runtime codehash are supplied. Do not copy Base governance: that address
  has no code on RH. If the selected governance is a Safe or another proxy, the
  release approval must additionally pin and preflight its implementation,
  owners, threshold, guard, enabled modules, and fallback handler; proxy runtime
  code alone does not authenticate those storage-backed controls.
- `DefaultsRobinhood` intentionally has no starter agent, creator, or security
  signer. Finish setup does not invent them. Wallet creation remains fail-closed
  until governance approves and installs the operational identities.
- HQ ID 10 is an empty, locked `VaultRegistry`. Both Appraiser update entry
  points unconditionally call `VaultRegistry(getAddr(10)).isBasicEarnVault`, so
  registering the empty department keeps ordinary non-earn-asset pricing paths
  operational without pulling earn vaults into this release. No vault address,
  vault token, allowlist, or yield configuration is installed. SwitchboardCharlie
  remains deferred until that separately approved vault/Lego rollout.
- HQ ID 11 is an empty, locked `Helpers` registry. `LegoTools` and
  `LevgVaultTools` are not deployed or registered in this core release.

Until governance is resolved, migrations `0000` through `0011` form a deployable
prefix but `1000` cannot complete the irreversible handoff. Do not describe that
prefix as a working wallet protocol.
