# Deploy Checklist

## Agent Sender Production Gate

- Confirm every `AgentWrapper` sender in production params is identified by verified ABI, not by probing live contract methods.
- Treat `AgentSenderSpecialAdmin` as a privileged production sender. Before deployment or registration, confirm the ABI is classified as `AgentSenderSpecialAdmin` by `scripts/params/production_params.py`.
- Review every `AgentSenderSpecialAdmin` entry for cheque issuance permissions, wrapper binding, nonce behavior, and signed-hash domain assumptions before adding it to a production `AgentWrapper`.
- Do not deploy, register, or leave enabled any sender reported as `Unknown` in the generated production params output.
