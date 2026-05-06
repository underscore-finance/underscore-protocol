# Deploy Checklist

## Agent Sender Production Gate

- Confirm every `AgentWrapper` sender in production params is identified by verified ABI, not by probing live contract methods.
- Treat `AgentSenderSpecialAdmin` as a privileged production sender. Before deployment or registration, confirm the ABI is classified as `AgentSenderSpecialAdmin` by `scripts/params/production_params.py`.
- Review every `AgentSenderSpecialAdmin` entry for cheque issuance permissions, wrapper binding, nonce behavior, and signed-hash domain assumptions before adding it to a production `AgentWrapper`.
- Do not deploy, register, or leave enabled any sender reported as `Unknown` in the generated production params output.

## ChequeBook Production Gate

- Verify the deployed wallet config `maxKeyActionTimeLock` is less than or equal to `ChequeBook.MAX_UNLOCK_BLOCKS` and `ChequeBook.MAX_EXPIRY_BLOCKS`. Cheque creation clamps expensive unlock delay and default expiry to the live wallet time lock; if the max time lock exceeds either ChequeBook cap, expensive or default-expiry cheque creation can become uncreatable at max time lock.
