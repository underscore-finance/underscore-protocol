# Deploy Checklist

## Agent Sender Production Gate

- Confirm every `AgentWrapper` sender in production params is identified by verified ABI, not by probing live contract methods.
- Treat `AgentSenderSpecialAdmin` as a privileged production sender. Before deployment or registration, confirm the ABI is classified as `AgentSenderSpecialAdmin` by `scripts/params/production_params.py`.
- Review every `AgentSenderSpecialAdmin` entry for cheque issuance permissions, wrapper binding, nonce behavior, and signed-hash domain assumptions before adding it to a production `AgentWrapper`.
- The AgentSender owner can call sender methods directly without a signature and can increment per-wallet nonces. Keep the owner key operationally separate from user wallet ownership, and treat `currentNonce[userWallet]` as scoped to each AgentSender contract.
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

- Normal wallet creation starts at the registered Hatchery. Hatchery validates nonzero core setup, backpack item addresses, WETH, ETH, wallet time-lock bounds, creator policy, and starter-agent tier before calling the deterministic wallet factory.
- Hatchery delegates global manager, starter-agent manager, payee, and cheque default-setting construction and validation to the configured HighCommand, Paymaster, and ChequeBook contracts.
- The deterministic factory, not MissionControl's legacy `walletTemplate` or `configTemplate`, selects the fixed `UserWallet` and `UserWalletConfig` implementations. Leave the MissionControl template fields on a matched legacy pair and treat them as deprecated after cutover.
- Before enabling creation, verify the factory's pinned chain-local UndyHq and confirm UndyHq registry ID `5` resolves to the exact approved Hatchery. The normal factory path must reject every caller other than that current registered Hatchery.
- The normal Hatchery path continues to enforce `MissionControl.numUserWalletsAllowed` against the chain-local Ledger. Do not silently move or remove that check as part of the deterministic deployment cutover.
- `nonProdCreator` must not also be present in `MissionControl.creatorWhitelist`. If both controls drift together, the non-prod creation lane and production creator policy conflict; deployment scripts should assert the intended creator posture before unpausing Hatchery.

## Deterministic Wallet Pair Invariants

- The wallet salt is `keccak256(abi.encode(owner, groupId, starterAgentTier))`. It contains exactly three 32-byte ABI words and does not include the creator.
- Chain-varying values are absent from implementation immutables. Factory-only initialization writes UserWallet WETH; UserWalletConfig UndyHq, WETH, ETH, ActionDataProvider, and min/max time locks; and Ownership UndyHq plus min/max ownership time locks into one-shot storage. The shared implementation bytecode must remain identical across chains.
- The factory creates the config proxy and wallet proxy with the same salt and Vyper 0.4.3's 54-byte minimal-proxy initcode. Their addresses differ because each initcode embeds a different implementation.
- The canonical factory must be deployed directly as immutable code, never through a proxy. In the current design its `isUserWalletConfig(config, salt)` predicate derives the expected address from a true compile-time config-implementation constant in that runtime, with no setter, mutable override, or one-shot implementation-initialization path. Verify the exact factory runtime before trusting the predicate.
- Both proxies must be created before either is exposed. Initialize `UserWalletConfig` before `UserWallet`; wallet initialization reads the completed config's reciprocal wallet pointer and verified salt.
- `UserWalletConfig` derives the tuple salt internally, authenticates its own exact EIP-1167 runtime and CREATE2 factory namespace, verifies `_wallet` is code-bearing, and checks `_wallet` is the same-salt CREATE2 proxy for the hardcoded wallet implementation. It then stores the salt and wallet pointer once.
- `UserWallet` receives only WETH and the config address. It requires a code-bearing config whose `wallet()` points back to it and reads `walletSalt()` from that config. It first authenticates its own exact runtime and CREATE2 deployer, then staticcalls that proven direct factory's `isUserWalletConfig(config, salt)` predicate to authenticate the config as the factory's same-salt proxy.
- The factory must perform both CREATE2 deployments and both one-shot initializations atomically, with no path that leaves an uninitialized proxy behind. Any failed validation must revert the entire transaction, including both deployments.
- There is no `UserWalletConfig.setWallet` step. Deployment scripts, interfaces, and monitoring must not call or wait for that removed entry point.

## Recovery Creation Invariants

- Recovery uses the same owner/group/tier salt and canonical factory address even when it initializes with no starter agent and no managers. Removing the starter agent does not change the tier committed into the address.
- Recovery must bypass the normal `Ledger.numUserWallets()` / `MissionControl.numUserWalletsAllowed` gate. Legacy wallet counts can legitimately differ across chains; applying a chain-local count cap could strand funds at an already published counterfactual address.
- Keep the existing normal-creation cap behavior unchanged for this release. Separately review whether that cap should count deterministic-generation wallets only, and document any future semantic change before implementing it.
- Do not approve the V1 release while one-wallet-per-owner/group/tier remains an unresolved product decision. The current Migrator requires a distinct destination with the same current owner and group ID, so an unchanged production owner cannot migrate between two V1 wallets in the same factory family. Record the accepted behavior against the [one-wallet-per-tuple migration gate](canonical-create2-deployment.md#one-wallet-per-tuple-and-migration-release-gate).
- Ledger has no wallet-generation marker. APIs and deployment inventories must distinguish legacy CREATE wallets externally and must never advertise a legacy address as a cross-chain identity; only deterministic-generation addresses have the recovery guarantee.
- Treat recovery as incomplete until the owner-authorized sweep path and its final runtime-size checks are implemented and tested. Do not advertise an unsupported chain as recoverable based only on address prediction.

## Mixed-Generation Prohibition

- Existing legacy wallets remain on their already deployed wallet/config bytecode and do not need conversion for the deterministic cutover.
- Never combine a deterministic implementation with a legacy blueprint counterpart, and never register either deterministic implementation as a MissionControl wallet template.
- Keep the two legacy MissionControl template fields as a matched pair. Do not update one field independently, even while the old Hatchery is paused.
- New creation must flow exclusively through the new Hatchery and canonical deterministic factory after registry cutover. The old Hatchery must remain paused; do not run legacy and deterministic creation paths concurrently.

## New-Wallet Defaults

- Hatchery owns only the new-wallet default instant-action settings. These defaults affect only wallets created after the active Hatchery state changes; existing wallets keep their stored settings.
- Starter-agent manager settings are module-owned defaults built by `HighCommand.createStarterAgentSettings(...)`.
- Cheque manager flags are module-owned defaults built by `ChequeBook.createDefaultChequeSettings(...)`.
- Changing starter-agent posture or cheque manager flags is a code/deploy event for the relevant wallet backpack item, not a Hatchery governance configuration change.

## Action Data Provider

- Deploy `ActionDataProvider` before final WalletBackpack setup.
- Stage and confirm `WalletBackpack.addPendingActionDataProvider(provider)` before enabling wallet creation through Hatchery.
- WalletBackpack stores the canonical provider address and governance can rotate it for future wallets.
- Each `UserWalletConfig` captures the provider address in write-once storage during atomic initialization. There is no post-initialization provider setter: existing wallets keep their original provider, and a provider bug fix for an existing V1 wallet with an unchanged identity requires migration to a pair from a new versioned factory family. V1 cannot create a second wallet for the same `(initial owner, groupId, tier)` tuple.
- Action-data reads now cross a read-only provider and make additional staticcalls back into `UserWalletConfig`. Budget extra gas on wallet action paths that call `checkSignerPermissionsAndGetBundle` or `getActionDataBundle`.
- Helper checks moved to `ActionDataProvider` add one additional read-only external call on affected registry/security helper paths. Budget roughly 2,600 gas of extra staticcall/CALL-frame overhead per helper use before calldata/returndata and the original inner lookup.
- `ActionDataProvider.isAgentSender` is a deployed-contract helper. It intentionally returns `false` for an empty starter agent, EOAs, and contracts still in construction where `EXTCODESIZE` is zero. Non-empty starter agents are validated as contracts when configured; contracts with a bad or reverting `isSender(address)` implementation still revert through the normal staticcall path.
- As of 2026-09-04, the implementation runtimes are `24,155` bytes for `UserWallet` (`421` bytes of EIP-170 headroom) and `23,739` bytes for `UserWalletConfig` (`837` bytes of headroom). This snapshot includes deterministic-proxy initializers, exact CREATE2/minimal-proxy self-authentication before factory trust, the immutable factory predicate for reciprocal same-salt counterpart authentication, and write-once config salt binding; it precedes the pending recovery sweep. Further code-relocation and recovery-sweep prototypes have not landed and are excluded from these figures. The former `19,986`-byte `UserWalletConfig` runtime figure was stale; see [the runtime byte-budget note](user-wallet-config-byte-budget.md).
- Treat both implementation buffers as constrained. Remeasure both runtimes after the recovery sweep and after any later growth; include an extraction plan before merge if either approaches the `24,576`-byte EIP-170 limit.

## SwitchboardAlpha Size

- Current Boa-measured `SwitchboardAlpha` runtime size: `22,381` bytes, leaving `2,195` bytes under the `24,576` byte EIP-170 gate.
- Treat future wrapper/event additions as size-sensitive. A few more similar governance wrappers in one PR should include an explicit size measurement before merge.
- Optional MissionControl override arguments must be contract addresses. Use `empty(address)` for the currently registered MissionControl.
- SwitchboardAlpha actions that accept a MissionControl override store the resolved MissionControl at staging time and execute against that staged address. Registry rotation before execution does not retarget the action; cancel and restage if the current MissionControl should be used.

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
- This migration path assumes required registry dependencies are registered, including `LootDistributor`.
- Both source and destination wallets must have the same configured `migrator` address. Standalone `migrateFunds` and config clone both reject destination configs that do not trust the active migrator.
- Loose native ETH is intentionally not migrated by `migrateFunds` or `migrateAll`. Operators should not treat migration as a full wallet drain; users must wrap, withdraw, or otherwise convert native ETH into a tracked ERC20-style asset before migration if it should move with the wallet.
- Cloned managers and payees are validated for destination role collisions before registration. Source-side cross-role state can cause config clone to revert with `manager collision on clone` or `payee collision on clone`. The source starting agent is not copied as a new manager; when source and destination share that starter-agent address, `cloneConfig` copies the source starter-agent manager fields while preserving the destination starter-agent time fields.
- Changing a wallet's configured migrator via `setMigrator` requires no pending migration on that wallet. Complete or cancel in-flight migration state before swapping the migrator.
- Pending global payee settings block migration on both source and destination wallets.
- Pending whitelist entries on the source wallet are not migrated. They remain on the source wallet and could still be confirmed there if the source wallet continues to be used. To preserve them on the destination wallet, restage and confirm them there.
- Config cloning emits paired events: `UserWalletConfig.MigrationConfigApplied` from the destination config log address with the source config address and applied time lock, and `Migrator.ConfigCloned` on the migrator with source/destination wallet addresses and copied counts.
- The destination config event intentionally omits a settings hash: computing one inside `UserWalletConfig` consumes constrained EIP-170 implementation-runtime headroom, and a migrator-supplied hash would not be independently trustworthy.
- Funds migration deregisters up to 25 migrated assets from the source wallet. If more than 25 assets move in one transaction, excess assets are transferred but remain tracked on the source wallet with zero balance; clean them up with later `deregisterAsset` calls if desired.
- Funds migration refreshes destination asset accounting once per successfully transferred asset. Gas scales with the number of migrated assets, and duplicate destination asset entries are not added.
- Payee and manager period/lifetime counters are not copied. Migration resets those accounting windows on the destination wallet.
- Config clone copies all currently indexed managers, payees, and whitelist entries in one transaction. There is no per-wallet manager/payee cap and no partial config-clone entry point in this release, so gas scales with those list sizes. Operators should preflight high-cardinality wallets and migrate them only in a monitored window; wallets with unusually many managers/payees may need a future batched clone path before they are practically migratable.
- Individual cheques are not migrated. Users must recreate any desired cheques on the destination wallet, and the source cheque ledger remains as historical state.
- Active user instant-action settings are copied directly during config migration. This is accepted migration behavior; pending user instant settings still block migration on both wallets.
- Fee-on-transfer or rebasing assets can leave dust or accounting differences because migration transfers the wallet's tracked token balance rather than reconciling post-transfer received amounts.
- A wallet's configured migrator is highly trusted because migrator-facing wallet-config settings apply immediately. Treat migrator upgrades and instant-migration windows as privileged operations.

## Instant Wallet Action Runbook

- Instant wallet actions require all three gates: the consuming backpack item protocol flag, the user wallet `instantActionSettings` flag, and the per-call instant bool.
- The V1 instant actions are `HighCommand.addManager`, `Paymaster.addPayee`, `Paymaster.setGlobalPayeeSettings`, and `ChequeBook.setChequeSettings`.
- Whitelist flows and global manager settings stay delay-only. Do not add rollout steps that enable instant whitelist changes.
- Protocol flags are deployment-configurable constructor values on new backpack items. The cutover values are all true except `Migrator.instantMigrationEnabled`, which stays false. This release intentionally cuts over the protocol flags and new-wallet Hatchery defaults together; the per-call instant bool remains the final opt-in gate on each action. Governance can still stage enables through `SwitchboardBravo`, wait for the Switchboard timelock, then execute the pending action. Governance or a security actor can disable immediately.
- If a pending protocol enable exists and the flag should not go live, disable the same flag through `SwitchboardBravo`; this cancels the matching pending action and emits the `WalletCanInstant*Set` event with `isEnabled=false`.
- Pending protocol enables store the target backpack item at staging time. If WalletBackpack rotates a role before execution, cancel and re-stage when the current role target matters.
- Pending Bravo actions also execute against staged external targets where a role can rotate, including the staged `LootDistributor` for loot adjustment and ejection-mode updates. If the registry role rotated during the pending window, monitor the executed target as a stale-target signal and cancel/restage when needed.
- User instant settings default from `Hatchery.defaultInstantActionSettings`; the cutover default is all true and is intended to become active at the same time as the matching protocol flags. Enabling a disabled user flag is timelocked; disabling applies immediately. Cancelling a mixed pending change does not roll back disables that already applied.
- Hatchery default instant settings are managed through `SwitchboardBravo`. Any false-to-true default transition is Bravo-timelocked against the staged Hatchery address, pure disables apply immediately, and wallets created during a pending window inherit the current confirmed Hatchery defaults.
- Hatchery's setter remains gated to registered Switchboard addresses. Do not run concurrent Hatchery-default changes through multiple Switchboards; cancel/restage if the operational target changes.

## Deterministic Wallet and Instant Defaults Cutover

- Deploy and byte-verify the fixed `UserWallet` implementation, `UserWalletConfig` implementation, and factory through the canonical CREATE2 singleton before changing live registry state. The factory must contain the exact approved implementation addresses and runtime code hashes.
- The deterministic implementations are not blueprints. Do not stage or execute `SwitchboardAlpha.setUserWalletTemplates` for them; leave MissionControl's legacy wallet/config template fields unchanged as a matched legacy pair.
- Deploy and verify the new Hatchery with the intended default instant settings, staging/dev starter-agent configuration, non-prod creator, and deterministic factory integration. Do not reuse an older Hatchery deployment script or constructor layout.
- Verify the factory's one-shot chain configuration is complete and points at the intended UndyHq. Confirm that its normal creation authorization resolves Hatchery from registry ID `5` rather than trusting a caller-supplied registry or Hatchery address.
- Query live `WalletBackpack`, `SwitchboardAlpha`, `SwitchboardBravo`, and `UndyHq` timelocks before cutover. Stage the Hatchery registry update and any intended backpack/protocol-flag changes, but no deterministic implementation template update.
- Do not plan a staged protocol-flag-vs-Hatchery-default rollout for this cutover. The accepted release plan is simultaneous protocol flags plus all-true new-wallet defaults, with per-call instant bools controlling actual use.
- Pause the old Hatchery before executing the ID `5` registry update. Keep it paused permanently after the deterministic path goes live; running both creation generations concurrently is prohibited.
- Execute the Hatchery registry update, then run the manifest-backed exact-address/runtime cutover preflight in [Canonical CREATE2 Deployment](canonical-create2-deployment.md). A wrong factory, implementation, Hatchery, pinned UndyHq, or registry pointer is a hard stop.
- Enable or unpause the new Hatchery only after preflight passes. Create a canary wallet through Hatchery and verify the expected wallet/config CREATE2 addresses, 45-byte proxy runtimes, reciprocal pointers, shared salt, owner/group/tier, WETH, ActionDataProvider, time-lock bounds, starter-agent state, and Ledger registration.
- Spot-check the canary wallet's `instantActionSettings` and confirm the factory transaction emitted/recorded both members of the pair without any intermediate uninitialized deployment.
- `SwitchboardBravo.HatcheryDefaultInstantActionSettingsSet` and `Hatchery.HatcheryDefaultInstantActionSettingsSet` share an event name but have different fields. Off-chain consumers should disambiguate by emitter address.
- A creation-path rollback changes the UndyHq Hatchery registry entry; it never points MissionControl templates at deterministic implementations. Deterministic wallets already created remain on their immutable proxy targets and cannot be rolled back by registry changes.
- Backpack-item rollback is a separate `WalletBackpack` staged rotation back to old HighCommand, Paymaster, ChequeBook, or Migrator items.
- User wallet instant-setting methods intentionally emit no events, matching `setTimeLock`. Monitor explicit calls plus the Switchboard protocol flag events listed in [Instant Action Model](instant-action-model.md).

## ABI / SDK Hard Cutover

- Regenerate the `Hatchery`, deterministic factory, `UserWallet`, and `UserWalletConfig` ABIs from the final sources. Remove every deployment-script or interface call to `UserWalletConfig.setWallet`; that entry point no longer exists.
- Wallet/config initializers are factory plumbing, not public operational APIs. No script, EOA, Hatchery, or SDK should deploy a proxy and initialize it later; Hatchery makes one factory call and the factory completes the pair atomically.
- Pending-payee compatibility fields were removed from the current struct layouts. Do not encode `TransferPerms.canAddPendingPayee`, `WhitelistPerms.canAddPending`, or `GlobalPayeeSettings.canPayOwner` in new calls.
- This is a hard ABI cutover, not a rolling-compatible change. Off-chain encoders that still use the old struct layouts will revert against the new HighCommand and Paymaster contracts because their calldata tuple layouts no longer match.
- Regenerate ABIs and SDKs before cutover, and update or redeploy every downstream caller that builds manager/payee-settings calldata, including dapps, multisig UIs, scripts, bots, and custom integrations.
- Do not rotate new backpack items into production while any supported caller is still encoding the old struct layouts.

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
