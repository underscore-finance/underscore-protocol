# User Wallet Payment Security

## Recipient Policy

- `allowedPayees` is a universal manager recipient allowlist.
- It applies to manager transfers, manager-created cheques, and cheque payments performed by managers.
- Owner-created cheques paid by a manager still respect that manager's `allowedPayees`.
- An empty `allowedPayees` list means unrestricted.
- Whitelisted recipients bypass `allowedPayees`.

## Role Separation

- Managers cannot add pending whitelist entries.
- Managers may confirm, cancel, or remove whitelist entries only when granted the relevant whitelist permissions.
- Managers cannot be payees or whitelisted recipients.
- Payees and whitelisted recipients cannot become managers.
- Cheque recipients cannot be managers, payees, whitelisted recipients, privileged Undy/system addresses, or registered backpack items.

## Security Boundaries

- `groupId` is caller-chosen metadata, not a security primitive.
- Switchboard has NFT recovery power.
- `preparePayment` is callable by valid Undy addresses.
- The AgentSender signer is not the user wallet owner.
- AgentSender can act only through wrapper manager permissions.

## Future Options

- Split `signerEOA` and `adminOwner` for AgentSender administration.
- Add a per-user signature to `AgentWrapper.removeSelfAsManager`. The current risk is automation denial of service, not direct fund loss.
