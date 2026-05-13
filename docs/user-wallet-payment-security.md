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
- Payees, whitelisted recipients, and active unexpired cheque recipients cannot become managers.
- New cheques cannot be created to current managers, payees, whitelisted recipients, privileged Undy/system addresses, or registered backpack items.
- Whitelist registration is now strict: confirming a pending whitelist entry reverts if the address is already whitelisted. If migration or another owner action whitelists the same address during the wait, cancel the stale pending entry and restage if needed.

## Reserved Fields

- `TransferPerms.canAddPendingPayee` remains in the struct for ABI compatibility, but it is reserved. HighCommand validation rejects manager-settings input that sets it to `true`; legitimate manager paths write `false`.

## Security Boundaries

- `groupId` is caller-chosen metadata, not a security primitive.
- Switchboard has NFT recovery power.
- `preparePayment` is callable by valid Undy addresses.
- The AgentSender signer is not the user wallet owner.
- AgentSender can act only through wrapper manager permissions.
- New wallets ship with instant manager-add, payee-add, global payee-settings, and cheque-settings user flags enabled by the Hatchery default. These paths still require the matching protocol flag and the per-call instant bool.
- Users can opt out by disabling any `instantActionSettings` flag immediately. Re-enabling a disabled flag is timelocked at the wallet-config layer.

## Future Options

- Split `signerEOA` and `adminOwner` for AgentSender administration.
- Add a per-user signature to `AgentWrapper.removeSelfAsManager`. The current risk is automation denial of service, not direct fund loss.
