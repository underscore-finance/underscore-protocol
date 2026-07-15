# @version 0.4.3
# Minimal UndyHq + Switchboard stand-in for the payments tests: resolves dept ids (2=MissionControl,
# 4=switchboard, 12=VendorRegistry, 13=PayProcessor), answers isSwitchboardAddr for a settable set,
# and — for SwitchboardDelta's LocalGov — exposes governance + gov-change timelock bounds.

addrs: public(HashMap[uint256, address])
switchers: public(HashMap[address, bool])
govAddr: public(address)

@external
def setAddr(_id: uint256, _addr: address):
    self.addrs[_id] = _addr

@external
def setSwitcher(_addr: address, _ok: bool):
    self.switchers[_addr] = _ok

@external
def setGov(_addr: address):
    self.govAddr = _addr

@view
@external
def getAddr(_id: uint256) -> address:
    return self.addrs[_id]

@view
@external
def isValidAddr(_addr: address) -> bool:
    return _addr != empty(address)

@view
@external
def isSwitchboardAddr(_addr: address) -> bool:
    return self.switchers[_addr]

@view
@external
def undyToken() -> address:
    return empty(address)

# LocalGov support (SwitchboardDelta)

@view
@external
def governance() -> address:
    return self.govAddr

@view
@external
def minGovChangeTimeLock() -> uint256:
    return 1

@view
@external
def maxGovChangeTimeLock() -> uint256:
    return 1_000_000
