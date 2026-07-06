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
#     ║  UndyHq dept: proxy factory + registry (dests live in proxies)    ║
#     ╚═══════════════════════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# The verified-service registry for agent payments. Deploys one PaymentProcessorProxy per service
# (a string id like "x402joker.com"), indexes it, and can enable/disable it. ProxyStore is also the
# SOLE CRUD entry point for a proxy's allow-listed destinations: those addresses live inside each proxy
# (self-contained), and ProxyStore forwards add/remove into the proxy after a curator/switchboard
# permission check — the proxy in turn only accepts edits from this store. The PaymentProcessor gates
# x402 settlement on `isProxyEnabled(proxy)` here plus the proxy's own `isAllowed(dest)`. Curators (set
# by the Switchboard) may create proxies and manage them.

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

interface Proxy:
    def addDestination(_dest: address): nonpayable
    def removeDestination(_dest: address): nonpayable

HQ: public(immutable(address))

proxyTemplate: public(address)                                      # blueprint for PaymentProcessorProxy
curators: public(HashMap[address, bool])                           # may create proxies + manage the index

# proxy registry
numProxies: public(uint256)
proxies: public(HashMap[uint256, address])                         # 1-based index -> proxy
indexOfProxy: public(HashMap[address, uint256])                   # proxy -> index (0 = not a proxy)
proxyById: public(HashMap[bytes32, address])                      # keccak(id) -> proxy
isProxyEnabled: public(HashMap[address, bool])                    # proxy -> enabled (PaymentProcessor settlement gate)

event ProxyCreated:
    proxy: indexed(address)
    id: String[128]

event ProxyEnabledSet:
    proxy: indexed(address)
    enabled: bool

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
    self.isProxyEnabled[proxy] = True
    log ProxyCreated(proxy=proxy, id=_id)
    return proxy


@external
def setProxyEnabled(_proxy: address, _enabled: bool):
    # Disable takes a proxy out of settlement (the PaymentProcessor gate) without dropping its registry
    # row or allow-list — re-enabling restores it. This is the "remove it from the index" kill-switch.
    assert self._canManage(msg.sender)  # dev: no perms
    assert self.indexOfProxy[_proxy] != 0  # dev: not a proxy
    self.isProxyEnabled[_proxy] = _enabled
    log ProxyEnabledSet(proxy=_proxy, enabled=_enabled)


#################################################
# destination CRUD (ProxyStore is the only door) #
#################################################


@external
def addDestination(_proxy: address, _dest: address):
    # ProxyStore is the sole CRUD entry point for a proxy's allow-list; the data itself lives in the
    # proxy (self-contained). We gate on curator/switchboard here; the proxy gates on `msg.sender == store`.
    assert self._canManage(msg.sender)  # dev: no perms
    assert self.indexOfProxy[_proxy] != 0  # dev: not a proxy
    extcall Proxy(_proxy).addDestination(_dest)


@external
def removeDestination(_proxy: address, _dest: address):
    assert self._canManage(msg.sender)  # dev: no perms
    assert self.indexOfProxy[_proxy] != 0  # dev: not a proxy
    extcall Proxy(_proxy).removeDestination(_dest)


#########
# views #
#########


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
