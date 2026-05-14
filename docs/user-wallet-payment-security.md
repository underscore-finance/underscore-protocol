# User Wallet Payment Security

## Recipient Policy

- `allowedPayees` is a universal manager recipient allowlist.
- It applies to manager transfers, manager-created cheques, and cheque payments performed by managers.
- Owner-created cheques paid by a manager still respect that manager's `allowedPayees`.
- An empty `allowedPayees` list means unrestricted.
- Whitelisted recipients bypass `allowedPayees`.
- Allowed recipients do not need to be registered payees. EOAs, ordinary contracts, and registered payees are valid allowed recipients.
- Allowed recipients cannot be the zero address, the owner, the wallet, the wallet config, a same-wallet manager, a privileged Undy/system address, or a registered backpack item.

## Role Separation

- Managers cannot add pending whitelist entries.
- Managers may confirm, cancel, or remove whitelist entries only when granted the relevant whitelist permissions.
- Managers cannot be payees or whitelisted recipients.
- User wallets registered with the protocol's `Ledger` are valid payees but cannot be added as managers or starting agents.
- Payees, whitelisted recipients, and active cheque recipients cannot become managers. Expired but uncleared cheques still reserve the recipient until the cheque is cancelled, cleared, or paid.
- New cheques cannot be created to current managers, payees, whitelisted recipients, privileged Undy/system addresses, or registered backpack items.
- Whitelist registration is now strict: confirming a pending whitelist entry reverts if the address is already whitelisted. If migration or another owner action whitelists the same address during the wait, cancel the stale pending entry and restage if needed.
- Managers can replace only their own active cheques; owners can replace any active cheque. The same-block replacement residual remains deferred, and this branch intentionally does not add a cheque id/version field to the ABI.

## Reserved Fields

- `TransferPerms.canAddPendingPayee` remains in the struct for ABI compatibility, but it is reserved. HighCommand validation rejects manager-settings input that sets it to `true`; legitimate manager paths write `false`.

## Security Boundaries

- `groupId` is caller-chosen metadata, not a security primitive.
- Switchboard has NFT recovery power.
- `preparePayment` is callable by valid Undy addresses.
- The AgentSender signer is not the user wallet owner.
- AgentSender can act only through wrapper manager permissions.
- The AgentSender owner remains privileged for that sender contract: direct owner calls do not require a signature, and owner-only `incrementNonce` can invalidate pending signed payloads for one wallet on that AgentSender.
- AgentSender nonce spaces are per AgentSender contract and per user wallet. They are separate from wallet pending-action state and from other AgentSender contracts registered on the same `AgentWrapper`.
- New wallets ship with instant manager-add, payee-add, global payee-settings, and cheque-settings user flags enabled by the Hatchery default. These paths still require the matching protocol flag and the per-call instant bool.
- New-wallet cheque manager flags default from `ChequeBook.createDefaultChequeSettings`. Changing those defaults is a code/deploy event; existing wallets keep their stored cheque settings.
- Users can opt out by disabling any `instantActionSettings` flag immediately. Re-enabling a disabled flag is timelocked at the wallet-config layer.

## Future Options

- Split `signerEOA` and `adminOwner` for AgentSender administration.
- Add a per-user signature to `AgentWrapper.removeSelfAsManager`. The current risk is automation denial of service, not direct fund loss.
