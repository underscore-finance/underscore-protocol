# UserWalletConfig Byte Budget

## Baseline

- Current Boa-measured `UserWalletConfig` blueprint size: `24,490` bytes.
- EIP-170 blueprint gate: `24,576` bytes.
- Current headroom: `86` bytes.
- PR 2a acceptance gate before PR 2b: `<= 23,800` bytes.
- Required savings before PR 2b: at least `690` bytes from the current baseline.

## Result

- PR 2a measurement before PR 2b: `23,796` bytes, `780` bytes under EIP-170 and `4` bytes under the PR 2a gate.
- Final measurement after PR 2b constructor plumbing, restored Hatchery wallet binding, and Migrator access to `updateManager`: `23,830` bytes, `746` bytes under EIP-170. Runtime size is `19,960` bytes.
- The final measurement is `34` bytes higher than the PR 2a measurement; later PR 2b wiring and small local-struct simplifications offset most of the cost of the restored `setWallet(_wallet)` Hatchery guard and Migrator permission update.
- The PR 2a gate of `23,800` bytes is missed by `30` bytes after restoring the `setWallet(_wallet)` Hatchery authorization guard and allowing Migrator to preserve starter-agent manager settings during config clone. These additions close concrete migration/config risks; the EIP-170 limit remains the hard cap.

## Changes Kept

- Inlined the single-use instant-action comparison helpers into `setInstantActionSettings`.
- Moved registry/security helper resolution to `ActionDataProvider`, adding one read-only provider staticcall on those helper paths.
- Inlined constructor starting-agent registration instead of calling `_registerManager`.
- Removed redundant indexed-set empty checks and unconditionalized last-item swaps for whitelist, manager, and payee removal.
- Removed an unreachable `numAssets == 0` branch in `updateAllAssetData`.
- Simplified internal callback returns where callers already rely on revert-or-continue behavior.
- Removed unnecessary local struct copies in `confirmPendingTimeLock` and `setPendingMigration`.
- Kept wallet/config binding authorized through Hatchery: `UserWalletConfig.setWallet(_wallet)` requires the registered Hatchery and stores the deployed wallet address.
- Allowed the configured Migrator to call `updateManager` so config clone can preserve starter-agent manager fields without changing the destination starter-agent time window.

## Behavioral Notes

- `setWallet(_wallet)` preserves the Hatchery authorization boundary. Unbound configs cannot be claimed by arbitrary callers.
- `setInstantActionSettings(active_settings)` clears any pending instant-settings change because it is a no-enable request. Use this only when the caller intends to cancel pending enables; otherwise avoid defensive resubmission of active values.

## Gas Impact

- `ActionDataProvider` extraction adds an extra read-only external call before the existing inner registry/config checks on `_canSetBackpackItem`, `_canPerformSecurityAction`, `_isValidRegistryAddr`, `_isSwitchboardAddr`, and `isAgentSender`.
- Affected `UserWalletConfig` paths include backpack-item setters, security cancel/freeze paths, `cancelPendingInstantActionSettings`, `preparePayment`, `deregisterAsset`, `setLegoAccessForAction`, `updateAssetData`, `recoverNft`, `setEjectionMode`, and agent-sender checks.
- Expect roughly one additional staticcall/CALL-frame overhead per helper use, on the order of 2,600 gas before calldata/returndata and the original inner call cost. The signer-permission and action-data bundle paths already cross `ActionDataProvider`; they are hit on every wallet action permission check and should be included in wallet-action gas budgets.

## Stop Rule

Measure after each meaningful change. Do not ship additional `UserWalletConfig` growth unless the Boa-measured blueprint size remains under the EIP-170 limit.
