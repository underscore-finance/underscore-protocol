# Deploy Checklist

## Agent Sender Production Gate

- Confirm every `AgentWrapper` sender in production params is identified by verified ABI, not by probing live contract methods.
- Treat `AgentSenderSpecialAdmin` as a privileged production sender. Before deployment or registration, confirm the ABI is classified as `AgentSenderSpecialAdmin` by `scripts/params/production_params.py`.
- Review every `AgentSenderSpecialAdmin` entry for cheque issuance permissions, wrapper binding, nonce behavior, and signed-hash domain assumptions before adding it to a production `AgentWrapper`.
- Do not deploy, register, or leave enabled any sender reported as `Unknown` in the generated production params output.

## ChequeBook Production Gate

- Verify the deployed wallet config `maxKeyActionTimeLock` is less than or equal to `ChequeBook.MAX_UNLOCK_BLOCKS` and `ChequeBook.MAX_EXPIRY_BLOCKS`. Cheque creation clamps expensive unlock delay and default expiry to the live wallet time lock; if the max time lock exceeds either ChequeBook cap, expensive or default-expiry cheque creation can become uncreatable at max time lock.
- Deploy-time assertion: `maxKeyActionTimeLock <= ChequeBook.MAX_UNLOCK_BLOCKS`.
- Deploy-time assertion: `maxKeyActionTimeLock <= ChequeBook.MAX_EXPIRY_BLOCKS`.

## AgentSender Monitoring

Monitor these AgentSender and ownership signals after deployment:

- `NonceIncremented`
- `OwnershipChangeInitiated`
- `OwnershipChangeConfirmed`
- `OwnershipChangeCancelled`
- `PendingOwnershipTimeLockSet`
- `PendingOwnershipTimeLockConfirmed`
- `PendingOwnershipTimeLockCancelled`
- high-risk `AgentAction` calls, especially cheque creation/payment, whitelist changes, and manager permission changes

## Pending State After Ownership Change

- Pending wallet actions are owner-scoped. If wallet ownership changes while a pending time lock, whitelist entry, cheque settings update, global payee settings update, or migration is outstanding, confirmation should fail on the stored owner check. The new owner should cancel stale pending state and restage the intended action.

## Wallet Creation Config

- Hatchery validates nonzero core setup, wallet/config templates, backpack item addresses, WETH, ETH, and wallet time-lock bounds before deploying a new user wallet.
- Hatchery delegates global manager, starter-agent manager, payee, and cheque default-setting construction and validation to the configured HighCommand, Paymaster, and ChequeBook contracts.

## New-Wallet Defaults

- Hatchery owns only the new-wallet default instant-action settings. These defaults affect only wallets created after the active Hatchery state changes; existing wallets keep their stored settings.
- Starter-agent manager settings are module-owned defaults built by `HighCommand.createStarterAgentSettings(...)`.
- Cheque manager flags are module-owned defaults built by `ChequeBook.createDefaultChequeSettings(...)`.
- Changing starter-agent posture or cheque manager flags is a code/deploy event for the relevant wallet backpack item, not a Hatchery governance configuration change.

## Action Data Provider

- Deploy `ActionDataProvider` before final WalletBackpack setup.
- Stage and confirm `WalletBackpack.addPendingActionDataProvider(provider)` before enabling wallet creation through Hatchery.
- WalletBackpack stores the canonical provider address and governance can rotate it for future wallets.
- Each `UserWalletConfig` captures the provider address as an immutable constructor value. Existing wallets keep their original provider; a provider bug fix for existing wallets requires migration to a new wallet template.
- Action-data reads now cross a read-only provider and make additional staticcalls back into `UserWalletConfig`. Budget extra gas on wallet action paths that call `checkSignerPermissionsAndGetBundle` or `getActionDataBundle`.
- Helper checks moved to `ActionDataProvider` add one additional read-only external call on affected registry/security helper paths. Budget roughly 2,600 gas of extra staticcall/CALL-frame overhead per helper use before calldata/returndata and the original inner lookup.
- Current Boa-measured `UserWalletConfig` blueprint size: `23,830` bytes, leaving `746` bytes under the `24,576` byte EIP-170 gate. Runtime size is `19,960` bytes, under the `23,000` byte soft target.
- Treat the blueprint buffer as exhausted. Any future `UserWalletConfig` growth should include a size check and an extraction plan before merge.
- Hatchery binds each new `UserWalletConfig` by calling `UserWalletConfig.setWallet(wallet)`. The config rejects non-Hatchery callers, so deployment scripts must keep the Hatchery registry entry current before wallet creation.

## SwitchboardAlpha Size

- Current Boa-measured `SwitchboardAlpha` runtime size: `22,939` bytes, leaving `1,637` bytes under the `24,576` byte EIP-170 gate.
- Treat future wrapper/event additions as size-sensitive. A few more similar governance wrappers in one PR should include an explicit size measurement before merge.
- Optional MissionControl override arguments must be contract addresses. Use `empty(address)` for the currently registered MissionControl.

## Wallet Time Lock Bounds

- Owner-initiated `setTimeLock` and `confirmPendingTimeLock` enforce `MIN_TIMELOCK <= value <= MAX_TIMELOCK` at the wallet-config layer.
- `applyMigratedConfigSettings` clamps copied source time-lock values into the destination wallet's `[MIN_TIMELOCK, MAX_TIMELOCK]` range. Cross-creator migrations with divergent bounds may complete with a clamped destination time lock.

## Instant Migration Runbook

- `instantMigrationEnabled` defaults to `false`.
- Set `instantMigrationEnabled` to `true` only during monitored migration windows.
- Setting `instantMigrationEnabled` to `false` still permits timelocked migrations. It only disables the instant bypass path.
- `migrateAll` is the one-call path for tracked ERC20-style funds and config under one pending migration.
- `migrateFunds` and `cloneConfig` are terminal paths. Each clears pending migration after success, so users need a new pending migration for the other half unless instant migration is enabled.
- This migration path assumes both wallets use the current `UserWalletConfig` version.
- Both source and destination wallets must have the same configured `migrator` address; otherwise destination-side config apply reverts with `no perms`.
- Loose native ETH is not migrated. Users should wrap or otherwise convert native ETH into a tracked ERC20-style asset before migration if it should move with the wallet.
- Cloned managers and payees are validated for destination role collisions before registration. Source-side cross-role state can cause config clone to revert with `manager collision on clone` or `payee collision on clone`. The source starting agent is not copied as a new manager; when source and destination share that starter-agent address, `cloneConfig` copies the source starter-agent manager fields while preserving the destination starter-agent time fields.
- Changing a wallet's configured migrator via `setMigrator` requires no pending migration on that wallet. Complete or cancel in-flight migration state before swapping the migrator.
- Pending global payee settings block migration on both source and destination wallets.
- Pending whitelist entries on the source wallet are not migrated. They remain on the source wallet and could still be confirmed there if the source wallet continues to be used. To preserve them on the destination wallet, restage and confirm them there.
- Config cloning emits paired events: `UserWalletConfig.MigrationConfigApplied` from the destination config log address with the source config address and applied time lock, and `Migrator.ConfigCloned` on the migrator with source/destination wallet addresses and copied counts.
- The destination config event intentionally omits a settings hash: computing one inside `UserWalletConfig` exceeds the deploy-blueprint size limit, and a migrator-supplied hash would not be independently trustworthy.
- Funds migration deregisters up to 25 migrated assets from the source wallet. If more than 25 assets move in one transaction, excess assets are transferred but remain tracked on the source wallet with zero balance; clean them up with later `deregisterAsset` calls if desired.
- Payee and manager period/lifetime counters are not copied. Migration resets those accounting windows on the destination wallet.
- Individual cheques are not migrated. Users must recreate any desired cheques on the destination wallet, and the source cheque ledger remains as historical state.
- Fee-on-transfer or rebasing assets can leave dust or accounting differences because migration transfers the wallet's tracked token balance rather than reconciling post-transfer received amounts.
- A wallet's configured migrator is highly trusted because migrator-facing wallet-config settings apply immediately. Treat migrator upgrades and instant-migration windows as privileged operations.

## Instant Wallet Action Runbook

- Instant wallet actions require all three gates: the consuming backpack item protocol flag, the user wallet `instantActionSettings` flag, and the per-call instant bool.
- The V1 instant actions are `HighCommand.addManager`, `Paymaster.addPayee`, `Paymaster.setGlobalPayeeSettings`, and `ChequeBook.setChequeSettings`.
- Whitelist flows and global manager settings stay delay-only. Do not add rollout steps that enable instant whitelist changes.
- Protocol flags are deployment-configurable constructor values on new backpack items. The cutover values are all true except `Migrator.instantMigrationEnabled`, which stays false. Governance can still stage enables through `SwitchboardBravo`, wait for the Switchboard timelock, then execute the pending action. Governance or a security actor can disable immediately.
- If a pending protocol enable exists and the flag should not go live, disable the same flag through `SwitchboardBravo`; this cancels the matching pending action and emits the `WalletCanInstant*Set` event with `isEnabled=false`.
- Pending protocol enables store the target backpack item at staging time. If WalletBackpack rotates a role before execution, cancel and re-stage when the current role target matters.
- User instant settings default from `Hatchery.defaultInstantActionSettings`; the cutover default is all true. Enabling a disabled user flag is timelocked; disabling applies immediately. Cancelling a mixed pending change does not roll back disables that already applied.

## Instant Defaults Cutover

- No migration files were updated in this scope.
- Deployment must separately redeploy the `UserWalletConfig` blueprint and stage/execute `SwitchboardAlpha.setUserWalletTemplates`.
- Query live `WalletBackpack`, `SwitchboardAlpha`, and `UndyHq` timelocks before cutover.
- Stage the template update and the Hatchery registry update.
- Do not reuse older Hatchery deploy scripts without updating constructor args. The active Hatchery constructor requires default instant settings, staging/dev starter-agent config, and non-prod creator.
- Pause the old Hatchery before executing the template update. Do not skip this pause step.
- Execute the template update.
- Execute the Hatchery registry update.
- Verify the new Hatchery is unpaused.
- Spot-check a new wallet's `instantActionSettings`.
- `SwitchboardAlpha.HatcheryDefaultInstantActionSettingsSet` and `Hatchery.HatcheryDefaultInstantActionSettingsSet` share an event name but have different fields. Off-chain consumers should disambiguate by emitter address.
- Rollback must reverse both the config template and Hatchery registry, not only Hatchery.
- Backpack-item rollback is a separate `WalletBackpack` staged rotation back to old HighCommand, Paymaster, ChequeBook, or Migrator items.
- User wallet instant-setting methods intentionally emit no events, matching `setTimeLock`. Monitor explicit calls plus the Switchboard protocol flag events listed in [Instant Action Model](instant-action-model.md).

## Manager Settings Constraints

- `TransferPerms.canAddPendingPayee` must be `false`. The field remains in the struct for ABI compatibility, but manager-settings inputs with `true` are rejected by HighCommand validation.

## Pending Payee Removal Preflight

This branch intentionally removes the pending-payee lifecycle from the Paymaster ABI while retaining `Paymaster.vy` for direct payee management (`addPayee`, `updatePayee`, `removePayee`, `setGlobalPayeeSettings`, and `createDefaultGlobalPayeeSettings`).

Before merge or deployment, confirm whether any live wallet has populated legacy `pendingPayees` state. This implementation does not require the implementation agent to gather the evidence, but the deployment owner must record:

- block number used for the audit
- wallet inventory source
- query/RPC method used
- total wallets checked
- total wallets with populated pending-payee state
- handling path if any nonzero pending-payee state exists

If any live pending-payee state exists, do not deploy until the handling path is documented and approved.
