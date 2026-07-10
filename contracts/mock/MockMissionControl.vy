# @version 0.4.3
# Minimal MissionControl stand-in for the SwitchboardDelta tests: a settable set of "security signers"
# that `canPerformSecurityAction` recognizes.

securitySigners: public(HashMap[address, bool])

@external
def setSecuritySigner(_addr: address, _ok: bool):
    self.securitySigners[_addr] = _ok

@view
@external
def canPerformSecurityAction(_signer: address) -> bool:
    return self.securitySigners[_signer]
