# User Wallet Runtime Byte Budget

## Current Measurement — 2026-09-04

This snapshot uses Vyper `0.4.3` with each contract's checked-in `pragma optimize codesize`. It includes the deterministic-proxy initializer conversion, exact EIP-1167 runtime and CREATE2 deployer guard, and reciprocal same-salt wallet/config authentication. `UserWalletConfig` derives the tuple salt internally, authenticates the hardcoded wallet-implementation counterpart, and stores the salt once. `UserWallet` receives only WETH and the config address, checks the config's reciprocal pointer and salt, proves its own exact proxy runtime and CREATE2 deployer first, then asks that proven direct factory whether the config is its same-salt proxy. The factory predicate derives the expected address from a compile-time config-implementation constant with no mutable override. It does **not** include the pending recovery sweep.

- `UserWallet`: `24,155` runtime bytes, leaving `421` bytes below the `24,576`-byte EIP-170 limit.
- `UserWalletConfig`: `23,739` runtime bytes, leaving `837` bytes below the EIP-170 limit.
- The pending recovery sweep must be followed by a fresh measurement of both implementations. The current headroom is an incomplete-work budget, not spare capacity for unrelated features. Further code-relocation and recovery-sweep prototypes have not landed and are not reflected in these figures.

## Measurement Method

From the repository root, compile each implementation's deployed runtime with the pinned project compiler:

```sh
.venv/bin/vyper -f bytecode_runtime contracts/core/userWallet/UserWallet.vy
.venv/bin/vyper -f bytecode_runtime contracts/core/userWallet/UserWalletConfig.vy
```

For each `0x`-prefixed result, the runtime byte count is `(hex character count - 2) / 2`. Measure `bytecode_runtime`; deployment bytecode and ERC-5202 blueprint artifacts are not substitutes for the EIP-170 runtime check.

## Stale Baseline Correction

The previous version of this document called `19,986` bytes the current `UserWalletConfig` runtime size. That value was stale: immediately before the deterministic-proxy changes, the same Vyper `0.4.3` runtime measurement was already `22,870` bytes. `UserWallet` was `23,032` bytes at that point.

Against those verified pre-change baselines, the current deterministic-proxy state adds `1,123` runtime bytes to `UserWallet` and `869` bytes to `UserWalletConfig`. Earlier `23,796`- and `23,856`-byte measurements described blueprint-era PR artifacts and remain historical optimization context; they must not be used as current implementation-runtime baselines.

## Changes Kept

- Inlined the single-use instant-action comparison helpers into `setInstantActionSettings`.
- Moved registry/security helper resolution to `ActionDataProvider`, adding one read-only provider staticcall on those helper paths.
- Inlined constructor starting-agent registration instead of calling `_registerManager`.
- Removed redundant indexed-set empty checks and unconditionalized last-item swaps for whitelist, manager, and payee removal.
- Removed an unreachable `numAssets == 0` branch in `updateAllAssetData`.
- Simplified internal callback returns where callers already rely on revert-or-continue behavior.
- Removed unnecessary local struct copies in `confirmPendingTimeLock` and `setPendingMigration`.
- Replaced the post-deployment Hatchery `setWallet(_wallet)` binding with atomic one-shot initialization, reciprocal wallet/config validation, and shared write-once `walletSalt` binding.
- Allowed the configured Migrator to call `updateManager` so config clone can preserve starter-agent manager fields without changing the destination starter-agent time window.
- Allowed the configured Migrator to call per-asset `updateAssetData` so funds migration refreshes destination asset accounting after transferred assets arrive.

## Behavioral Notes

- Each implementation locks itself in its constructor. Fresh proxy storage can initialize once, and the CREATE2 guard authenticates the direct deployer and the exact minimal-proxy runtime before accepting configuration.
- `UserWalletConfig` receives its paired wallet and the owner/group/tier tuple during initialization, derives the tuple salt internally, authenticates the config proxy itself, checks the wallet against the same factory/salt and hardcoded wallet implementation, and stores the salt once. It never accepts a caller-supplied salt. `UserWallet` receives only WETH and its config address, requires the config to point back to it, reads the verified `walletSalt`, and authenticates its own exact proxy runtime and CREATE2 deployer before any factory trust call. It then requires that proven direct factory's `isUserWalletConfig(config, salt)` predicate to derive and match the config address from the factory's compile-time config-implementation constant; there is no mutable implementation override.
- `setInstantActionSettings(active_settings)` clears any pending instant-settings change because it is a no-enable request. Use this only when the caller intends to cancel pending enables; otherwise avoid defensive resubmission of active values.
- `ActionDataProvider` is captured in write-once storage during each `UserWalletConfig` initialization. It has no rotation setter, so rotating WalletBackpack's provider only affects future wallets; existing-wallet provider fixes require a wallet/config migration.

## Gas Impact

- `ActionDataProvider` extraction adds an extra read-only external call before the existing inner registry/config checks on `_canSetBackpackItem`, `_canPerformSecurityAction`, `_isValidRegistryAddr`, `_isSwitchboardAddr`, and `isAgentSender`.
- Affected `UserWalletConfig` paths include backpack-item setters, security cancel/freeze paths, `cancelPendingInstantActionSettings`, `preparePayment`, `deregisterAsset`, `setLegoAccessForAction`, `updateAssetData`, `recoverNft`, `setEjectionMode`, and agent-sender checks.
- Funds migration now calls destination `updateAssetData` once per successfully transferred asset. Include that per-asset multiplier in migration gas budgets.
- Expect roughly one additional staticcall/CALL-frame overhead per helper use, on the order of 2,600 gas before calldata/returndata and the original inner call cost. The signer-permission and action-data bundle paths already cross `ActionDataProvider`; they are hit on every wallet action permission check and should be included in wallet-action gas budgets.

## Stop Rule

Measure both implementation runtimes after each meaningful change. Do not ship either contract at or above the `24,576`-byte EIP-170 limit. In particular, do not accept the pending recovery sweep until the final `UserWallet` and `UserWalletConfig` runtimes have been remeasured with the release compiler.
