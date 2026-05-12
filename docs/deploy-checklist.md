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
- Hatchery delegates manager, payee, and cheque default-setting validation to the configured HighCommand, Paymaster, and ChequeBook contracts. Invalid MissionControl wallet-creation parameters should fail wallet creation before config deployment completes.

## Action Data Provider

- Deploy `ActionDataProvider` before final WalletBackpack setup.
- Stage and confirm `WalletBackpack.addPendingActionDataProvider(provider)` before enabling wallet creation through Hatchery.
- WalletBackpack stores the canonical provider address and governance can rotate it for future wallets.
- Each `UserWalletConfig` captures the provider address as an immutable constructor value. Existing wallets keep their original provider; a provider bug fix for existing wallets requires migration to a new wallet template.
- Action-data reads now cross a read-only provider and make additional staticcalls back into `UserWalletConfig`. Budget extra gas on wallet action paths that call `checkSignerPermissionsAndGetBundle` or `getActionDataBundle`.
- Post-refactor Boa-measured `UserWalletConfig` blueprint size: `23,498` bytes, leaving `1,078` bytes under the `24,576` byte EIP-170 gate.
- Treat that buffer as a budget. Any future `UserWalletConfig` PR expected to add more than roughly `100` bytes should include a size check and an extraction plan if the remaining buffer would fall below `500` bytes.

## Wallet Time Lock Bounds

- Owner-initiated `setTimeLock` and `confirmPendingTimeLock` enforce `MIN_TIMELOCK <= value <= MAX_TIMELOCK` at the wallet-config layer.
- `setTimeLockViaMigrator` clamps copied source values into the destination wallet's `[MIN_TIMELOCK, MAX_TIMELOCK]` range. Cross-creator migrations with divergent bounds may complete with a clamped destination time lock.

## Instant Migration Runbook

- `instantMigrationEnabled` defaults to `false`.
- Set `instantMigrationEnabled` to `true` only during monitored migration windows.
- Setting `instantMigrationEnabled` to `false` still permits timelocked migrations. It only disables the instant bypass path.
- `migrateAll` is the one-call path for tracked ERC20-style funds and config under one pending migration.
- `migrateFunds` and `cloneConfig` are terminal paths. Each clears pending migration after success, so users need a new pending migration for the other half unless instant migration is enabled.
- Loose native ETH is not migrated. Users should wrap or otherwise convert native ETH into a tracked ERC20-style asset before migration if it should move with the wallet.
- Cloned managers and payees are validated for destination role collisions before registration. Legacy source-side cross-role state can cause config clone to revert with `manager collision on clone` or `payee collision on clone`.
- Changing a wallet's configured migrator via `setMigrator` requires no pending migration on that wallet. Complete or cancel in-flight migration state before swapping the migrator.
- Payee and manager period/lifetime counters are not copied. Migration resets those accounting windows on the destination wallet.
- Individual cheques are not migrated. Users must recreate any desired cheques on the destination wallet, and the source cheque ledger remains as historical state.
- Fee-on-transfer or rebasing assets can leave dust or accounting differences because migration transfers the wallet's tracked token balance rather than reconciling post-transfer received amounts.
- A wallet's configured migrator is highly trusted because migrator-facing wallet-config setters apply immediately. Treat migrator upgrades and instant-migration windows as privileged operations.

## Instant Wallet Action Runbook

- Instant wallet actions require all three gates: the consuming backpack item protocol flag, the user wallet `instantActionSettings` flag, and the per-call instant bool.
- The V1 instant actions are `HighCommand.addManager`, `Paymaster.addPayee`, `Paymaster.setGlobalPayeeSettings`, and `ChequeBook.setChequeSettings`.
- Whitelist flows and global manager settings stay delay-only. Do not add rollout steps that enable instant whitelist changes.
- Protocol flags default to `false`. Governance stages enables through `SwitchboardBravo`, waits for the Switchboard timelock, then executes the pending action. Governance or a security actor can disable immediately.
- If a pending protocol enable exists and the flag should not go live, disable the same flag through `SwitchboardBravo`; this cancels the matching pending action and emits the `WalletCanInstant*Set` event with `isEnabled=false`.
- Pending protocol enables store the target backpack item at staging time. If WalletBackpack rotates a role before execution, cancel and re-stage when the current role target matters.
- User instant settings default to all false. Enabling a user flag is timelocked; disabling applies immediately. Cancelling a mixed pending change does not roll back disables that already applied.
- Existing wallets from the old template do not expose `instantActionSettings()`. Delayed paths remain compatible because backpack items read the new selector only when the caller requests instant execution. Old-template-to-new-template migration is out of scope for this runbook.
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
