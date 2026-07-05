#            _            _            _             _            _            _      
#           / /\         /\ \         /\ \     _    /\ \         /\ \         /\ \    
#          / /  \       /  \ \       /  \ \   /\_\ /  \ \____   /  \ \       /  \ \   
#         / / /\ \__   / /\ \ \     / /\ \ \_/ / // /\ \_____\ / /\ \ \     / /\ \ \  
#        / / /\ \___\ / / /\ \_\   / / /\ \___/ // / /\/___  // / /\ \_\   / / /\ \_\ 
#        \ \ \ \/___// /_/_ \/_/  / / /  \/____// / /   / / // /_/_ \/_/  / / /_/ / / 
#         \ \ \     / /____/\    / / /    / / // / /   / / // /____/\    / / /__\/ /  
#     _    \ \ \   / /\____\/   / / /    / / // / /   / / // /\____\/   / / /_____/   
#    /_/\__/ / /  / / /______  / / /    / / / \ \ \__/ / // / /______  / / /\ \ \     
#    \ \/___/ /  / / /_______\/ / /    / / /   \ \___\/ // / /_______\/ / /  \ \ \    
#     \_____\/   \/__________/\/_/     \/_/     \/_____/ \/__________/\/_/    \_\/    
#
#     ╔═══════════════════════════════════════════════════════════════════╗
#     ║  ** Proxy Store **                                                ║
#     ║  UndyHq dept: proxy factory + the verified service/dest index.    ║
#     ╚═══════════════════════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# The verified-service registry for agent payments. Deploys one PaymentProcessorProxy per service
# (a string id like "x402joker.com") and holds the bidirectional allow-list mapping each service's
# proxy to the destination addresses it may settle to — and the reverse (which services a destination
# serves). The PaymentProcessor reads `isAllowed(proxy, dest)` to gate x402 settlement, and the reverse
# index maps a settlement back to its service(s). Curators (set by the Switchboard) manage the index.

# @version 0.4.3
# pragma optimize codesize

implements: Department

exports: addys.__interface__
exports: deptBasics.__interface__

initializes: addys
initializes: deptBasics[addys := addys]

import contracts.modules.Addys as addys
import contracts.modules.DeptBasics as deptBasics
from interfaces import Department

MAX_LIST: constant(uint256) = 100

HQ: public(immutable(address))

proxyTemplate: public(address)                                       # blueprint for PaymentProcessorProxy
curators: public(HashMap[address, bool])                            # may create proxies + manage the index

# proxy registry
numProxies: public(uint256)
proxies: public(HashMap[uint256, address])                          # 1-based index -> proxy
indexOfProxy: public(HashMap[address, uint256])                    # proxy -> index (0 = not a proxy)
proxyById: public(HashMap[bytes32, address])                       # keccak(id) -> proxy

# bidirectional destination index
isAllowed: public(HashMap[address, HashMap[address, bool]])         # proxy -> dest -> allowed (O(1) gate)
# forward: proxy -> [dest, ...]
numDests: public(HashMap[address, uint256])
dests: public(HashMap[address, HashMap[uint256, address]])          # proxy -> idx(1-based) -> dest
indexOfDest: public(HashMap[address, HashMap[address, uint256]])   # proxy -> dest -> idx
# reverse: dest -> [proxy, ...]
numProxiesForDest: public(HashMap[address, uint256])
proxiesForDest: public(HashMap[address, HashMap[uint256, address]]) # dest -> idx(1-based) -> proxy
indexOfProxyForDest: public(HashMap[address, HashMap[address, uint256]])

event ProxyCreated:
    proxy: indexed(address)
    id: String[128]

event DestinationAdded:
    proxy: indexed(address)
    dest: indexed(address)

event DestinationRemoved:
    proxy: indexed(address)
    dest: indexed(address)

event CuratorSet:
    account: indexed(address)
    allowed: bool

event ProxyTemplateSet:
    template: indexed(address)


@deploy
def __init__(_undyHq: address, _proxyTemplate: address):
    addys.__init__(_undyHq)
    deptBasics.__init__(False, False)  # not paused; cannot mint UNDY
    HQ = _undyHq
    self.proxyTemplate = _proxyTemplate


@view
@internal
def _canManage(_addr: address) -> bool:
    return addys._isSwitchboardAddr(_addr) or self.curators[_addr]


###########
# factory #
###########


@external
def createProxy(_id: String[128]) -> address:
    assert self._canManage(msg.sender)  # dev: no perms
    template: address = self.proxyTemplate
    assert template != empty(address)  # dev: no template
    idHash: bytes32 = keccak256(_id)
    assert self.proxyById[idHash] == empty(address)  # dev: id taken
    proxy: address = create_from_blueprint(template, HQ, _id)
    pid: uint256 = self.numProxies + 1
    self.proxies[pid] = proxy
    self.indexOfProxy[proxy] = pid
    self.numProxies = pid
    self.proxyById[idHash] = proxy
    log ProxyCreated(proxy=proxy, id=_id)
    return proxy


#####################################
# destination index (bidirectional) #
#####################################


@external
def addDestination(_proxy: address, _dest: address):
    assert self._canManage(msg.sender)  # dev: no perms
    assert self.indexOfProxy[_proxy] != 0  # dev: not a proxy
    assert _dest != empty(address)  # dev: zero dest
    if self.isAllowed[_proxy][_dest]:
        return
    self.isAllowed[_proxy][_dest] = True
    # forward: proxy -> dest
    fidx: uint256 = self.numDests[_proxy] + 1
    self.dests[_proxy][fidx] = _dest
    self.indexOfDest[_proxy][_dest] = fidx
    self.numDests[_proxy] = fidx
    # reverse: dest -> proxy
    ridx: uint256 = self.numProxiesForDest[_dest] + 1
    self.proxiesForDest[_dest][ridx] = _proxy
    self.indexOfProxyForDest[_dest][_proxy] = ridx
    self.numProxiesForDest[_dest] = ridx
    log DestinationAdded(proxy=_proxy, dest=_dest)


@external
def removeDestination(_proxy: address, _dest: address):
    assert self._canManage(msg.sender)  # dev: no perms
    assert self.isAllowed[_proxy][_dest]  # dev: not allowed
    self.isAllowed[_proxy][_dest] = False
    self._removeForward(_proxy, _dest)
    self._removeReverse(_dest, _proxy)
    log DestinationRemoved(proxy=_proxy, dest=_dest)


@internal
def _removeForward(_proxy: address, _dest: address):
    idx: uint256 = self.indexOfDest[_proxy][_dest]
    last: uint256 = self.numDests[_proxy]
    if idx != last:
        moved: address = self.dests[_proxy][last]
        self.dests[_proxy][idx] = moved
        self.indexOfDest[_proxy][moved] = idx
    self.dests[_proxy][last] = empty(address)
    self.indexOfDest[_proxy][_dest] = 0
    self.numDests[_proxy] = last - 1


@internal
def _removeReverse(_dest: address, _proxy: address):
    idx: uint256 = self.indexOfProxyForDest[_dest][_proxy]
    last: uint256 = self.numProxiesForDest[_dest]
    if idx != last:
        moved: address = self.proxiesForDest[_dest][last]
        self.proxiesForDest[_dest][idx] = moved
        self.indexOfProxyForDest[_dest][moved] = idx
    self.proxiesForDest[_dest][last] = empty(address)
    self.indexOfProxyForDest[_dest][_proxy] = 0
    self.numProxiesForDest[_dest] = last - 1


#########
# views #
#########


@view
@external
def getProxyDestinations(_proxy: address) -> DynArray[address, MAX_LIST]:
    out: DynArray[address, MAX_LIST] = []
    n: uint256 = self.numDests[_proxy]
    for i: uint256 in range(1, MAX_LIST + 1):
        if i > n:
            break
        out.append(self.dests[_proxy][i])
    return out


@view
@external
def getDestinationProxies(_dest: address) -> DynArray[address, MAX_LIST]:
    out: DynArray[address, MAX_LIST] = []
    n: uint256 = self.numProxiesForDest[_dest]
    for i: uint256 in range(1, MAX_LIST + 1):
        if i > n:
            break
        out.append(self.proxiesForDest[_dest][i])
    return out


@view
@external
def getProxyById(_id: String[128]) -> address:
    return self.proxyById[keccak256(_id)]


#############################
# admin (Switchboard-gated) #
#############################


@external
def setCurator(_account: address, _allowed: bool):
    assert addys._isSwitchboardAddr(msg.sender)  # dev: no perms
    self.curators[_account] = _allowed
    log CuratorSet(account=_account, allowed=_allowed)


@external
def setProxyTemplate(_template: address):
    assert addys._isSwitchboardAddr(msg.sender)  # dev: no perms
    self.proxyTemplate = _template
    log ProxyTemplateSet(template=_template)
