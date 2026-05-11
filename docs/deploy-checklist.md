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

## Instant Migration Runbook

- `instantMigrationEnabled` defaults to `false`.
- Set `instantMigrationEnabled` to `true` only during monitored migration windows.
- Setting `instantMigrationEnabled` to `false` still permits timelocked migrations. It only disables the instant bypass path.
- `migrateAll` is the one-call path for tracked ERC20-style funds and config under one pending migration.
- `migrateFunds` and `cloneConfig` are terminal paths. Each clears pending migration after success, so users need a new pending migration for the other half unless instant migration is enabled.
- Loose native ETH is not migrated. Users should wrap or otherwise convert native ETH into a tracked ERC20-style asset before migration if it should move with the wallet.
- Payee and manager period/lifetime counters are not copied. Migration resets those accounting windows on the destination wallet.
- Individual cheques are not migrated. Users must recreate any desired cheques on the destination wallet, and the source cheque ledger remains as historical state.
- Fee-on-transfer or rebasing assets can leave dust or accounting differences because migration transfers the wallet's tracked token balance rather than reconciling post-transfer received amounts.
- Complete or cancel pending migration state before changing a wallet's configured migrator address; changing the migrator while a migration is pending can orphan that pending state operationally.
- A wallet's configured migrator is highly trusted because migrator-facing wallet-config setters apply immediately. Treat migrator upgrades and instant-migration windows as privileged operations.

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
