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

For production, provide the matching deployer key through
`DEPLOYER_PRIVATE_KEY` and run:

```shell
PYTHONPATH=. .venv/bin/python scripts/migrate.py \
  --account DEPLOYER \
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
| `1000` | lock setup-time registries/actions, grant Switchboard the ID-4 token-blacklist permission, and hand UndyHq to the approved RH governance contract |

SwitchboardCharlie is deliberately absent. Its current entry points administer
vaults, vault allowlists, and Lego/yield configuration; nothing in the initial
no-vault core path resolves Switchboard child ID 3. Register it later, before
vault support, through the timelocked Switchboard registry.

Run the post-HQ sequence only after every release blocker below is resolved:

```shell
PYTHONPATH=. .venv/bin/python scripts/migrate.py \
  --account DEPLOYER \
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
update, or disable actions in UndyHq, Switchboard, and LegoBook. AddressRegistry
does not expose an enumerable pending-action list, so exact address prefixes and
empty known action IDs cannot prove the absence of every pending registry write.
Treat this event scan as a mandatory manual precondition before the irreversible
timelock and governance handoff.

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
- HQ ID 10 is intentionally absent because vault deployment is out of scope.
  This is not operationally neutral: both Appraiser update entry points
  unconditionally call `VaultRegistry(getAddr(10)).isBasicEarnVault`, so ordinary
  priced wallet transfer/wrap/cheque paths revert while ID 10 is zero. An empty
  VaultRegistry needs no EarnVault, but deploying it is a scope decision and is
  not done by these migrations. It must be registered and locked before any
  future Lego; otherwise Sentinel's zero-registry guard can bypass the
  only-approved-yield-opportunity check.

Until governance and the ID-10 decision are resolved, migrations `0000` through
`0009` form a deployable prefix but `1000` cannot complete the irreversible
handoff. Do not describe that prefix as a working wallet protocol.
