# Deploy Checklist

## Agent Sender Production Gate

- Confirm every `AgentWrapper` sender in production params is identified by verified ABI, not by probing live contract methods.
- Treat `AgentSenderSpecialAdmin` as a privileged production sender. Before deployment or registration, confirm the ABI is classified as `AgentSenderSpecialAdmin` by `scripts/params/production_params.py`.
- Review every `AgentSenderSpecialAdmin` entry for cheque issuance permissions, wrapper binding, nonce behavior, and signed-hash domain assumptions before adding it to a production `AgentWrapper`.
- Do not deploy, register, or leave enabled any sender reported as `Unknown` in the generated production params output.

## ChequeBook Production Gate

- Verify the deployed wallet config `maxKeyActionTimeLock` is less than or equal to `ChequeBook.MAX_UNLOCK_BLOCKS` and `ChequeBook.MAX_EXPIRY_BLOCKS`. Cheque creation clamps expensive unlock delay and default expiry to the live wallet time lock; if the max time lock exceeds either ChequeBook cap, expensive or default-expiry cheque creation can become uncreatable at max time lock.

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
