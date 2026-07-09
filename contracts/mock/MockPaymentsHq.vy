# @version 0.4.3
# Minimal UndyHq + Switchboard stand-in for the payments tests: resolves dept ids (4=switchboard,
# 12=VendorRegistry, 13=PayProcessor) and answers isSwitchboardAddr for a settable admin set.

addrs: public(HashMap[uint256, address])
switchers: public(HashMap[address, bool])

@external
def setAddr(_id: uint256, _addr: address):
    self.addrs[_id] = _addr

@external
def setSwitcher(_addr: address, _ok: bool):
    self.switchers[_addr] = _ok

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
