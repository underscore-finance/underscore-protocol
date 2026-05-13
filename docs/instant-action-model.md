# Instant Action Model

Instant execution is an opt-in bypass for specific wallet actions where the normal pending delay is painful. It is not a global wallet mode.

## Gates

An action can execute instantly only when all three gates pass:

- The protocol flag on the consuming backpack item is enabled.
- The user wallet's matching `instantActionSettings` flag is enabled.
- The caller passes the action's per-call instant bool.

No single gate is enough. A protocol flag alone does not make behavior automatic, a user flag alone does not bypass protocol policy, and a caller bool alone cannot bypass either setting.

## V1 Scope

The supported instant actions are:

- `HighCommand.addManager(..., _shouldStartInstantly=True)`
- `Paymaster.addPayee(..., _shouldStartInstantly=True)`
- `Paymaster.setGlobalPayeeSettings(..., _shouldApplyInstantly=True)` for widening changes
- `ChequeBook.setChequeSettings(..., _shouldApplyInstantly=True)` for widening changes

Whitelist flows remain delay-only because recipient-of-funds risk should not be bypassed by a user-toggleable instant path. Global manager settings also remain delay-only.

## Protocol Flags

Protocol flags live on the consuming backpack item and are managed by `SwitchboardBravo`:

- `HighCommand.canInstantAddManager`
- `Paymaster.canInstantAddPayee`
- `Paymaster.canInstantSetGlobalPayeeSettings`
- `ChequeBook.canInstantSetChequeSettings`

Enabling a protocol flag is governance-only and timelocked through `SwitchboardBravo`. Disabling is immediate for governance or a security actor. Disabling also cancels a matching pending enable for the same target.

`SwitchboardBravo.setCanInstantAddManager(target, bool)` and the sibling setters are the governance entry points. They intentionally share bare names with the backpack-item setters, but have different signatures and selectors because the Switchboard variant takes the backpack-item target.

`SwitchboardBravo` emits wallet-scoped event names so they do not collide with the backpack-item setter events:

- `PendingEnableWalletCanInstantAddManagerAction` / `WalletCanInstantAddManagerSet`
- `PendingEnableWalletCanInstantAddPayeeAction` / `WalletCanInstantAddPayeeSet`
- `PendingEnableWalletCanInstantSetGlobalPayeeSettingsAction` / `WalletCanInstantSetGlobalPayeeSettingsSet`
- `PendingEnableWalletCanInstantSetChequeSettingsAction` / `WalletCanInstantSetChequeSettingsSet`

Pending enables store the target backpack item at staging time. If WalletBackpack rotates a role before execution, cancel and re-stage the enable when the current role target matters.

## User Flags

User flags live on `UserWalletConfig.instantActionSettings`. New wallets inherit `Hatchery.defaultInstantActionSettings`; the cutover default is all true for manager add, payee add, global payee settings, and cheque settings.

Enabling any user flag from false to true stages `pendingInstantActionSettings` behind the wallet time lock. Users can disable flags immediately. Mixed changes apply immediate disables and stage the requested full settings for later confirmation. Cancelling the pending mixed change clears only the pending struct; immediate disables stay active.

Submitting any settings tuple that introduces no new enables clears any outstanding pending instant-settings change. This includes idempotent re-submission of active settings and strict disable-only requests. UIs should not defensively resubmit active or disabled values unless they intend to cancel the outstanding pending enable.

The user wallet instant-setting methods intentionally emit no events, matching the existing `setTimeLock` flow. Operational monitoring should watch the explicit method calls and the Switchboard protocol flag events.

## Migration

Migration copies only active user instant settings. Pending user instant settings block both funds migration and config clone on source and destination wallets. Protocol flags are global rollout state and are not copied.

This migration path assumes both wallets use the current `UserWalletConfig` version. Pending whitelist entries on the source wallet are not migrated; they remain on the source wallet and could still be confirmed there if that wallet continues to be used. Restage and confirm them on the destination wallet to preserve them there.
