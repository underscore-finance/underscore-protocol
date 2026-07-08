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

# The verified-service registry for agent payments. Deploys one PaymentProcessorProxy per service and
# records it in a simple 1-based registry — each row carries the proxy address plus its human string id
# (e.g. "x402joker.com"), so the id lives on the record (no separate id index). A proxy is "live" while
# it holds a registry slot: the PaymentProcessor gates settlement on `indexOfProxy(proxy) != 0`, and
# removeProxy takes it back out (there is no separate enabled/disabled flag). Curators (set by the
# Switchboard) may create and remove proxies. A proxy's allow-listed destinations are NOT managed here:
# they live inside each proxy (self-contained) and are edited directly on the proxy by the Switchboard.

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

HQ: public(immutable(address))

proxyTemplate: public(address)                                     # blueprint for PaymentProcessorProxy
curators: public(HashMap[address, bool])                          # may create + remove proxies

struct ProxyData:
    proxy: address
    id: String[128]

# proxy registry (1-based; count == numProxies - 1). Removal swaps the last row into the freed slot.
numProxies: public(uint256)                                       # next free regId (starts at 1)
proxies: public(HashMap[uint256, ProxyData])                      # regId -> record (id lives on the record)
indexOfProxy: public(HashMap[address, uint256])                   # proxy -> regId (0 = not a proxy)

event ProxyCreated:
    proxy: indexed(address)
    id: String[128]

event ProxyRemoved:
    proxy: indexed(address)

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
    self.numProxies = 1  # 1-based registry (Underscore list style)


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
    proxy: address = create_from_blueprint(template, HQ, _id)
    pid: uint256 = self.numProxies
    self.proxies[pid] = ProxyData(proxy=proxy, id=_id)
    self.indexOfProxy[proxy] = pid
    self.numProxies = pid + 1
    log ProxyCreated(proxy=proxy, id=_id)
    return proxy


@external
def removeProxy(_proxy: address):
    # Remove a proxy from the registry (the "kill switch"): the PaymentProcessor gates on
    # `indexOfProxy(proxy) != 0`, so a removed proxy can no longer settle. Swap-remove keeps the list
    # dense (mirrors the Underscore whitelist idiom); re-listing a service means a fresh createProxy.
    assert self._canManage(msg.sender)  # dev: no perms
    targetIndex: uint256 = self.indexOfProxy[_proxy]
    assert targetIndex != 0  # dev: not a proxy

    lastIndex: uint256 = self.numProxies - 1
    self.numProxies = lastIndex

    lastData: ProxyData = self.proxies[lastIndex]
    self.proxies[targetIndex] = lastData
    self.indexOfProxy[lastData.proxy] = targetIndex
    self.proxies[lastIndex] = empty(ProxyData)
    self.indexOfProxy[_proxy] = 0
    log ProxyRemoved(proxy=_proxy)


#########
# views #
#########


@view
@external
def isProxy(_proxy: address) -> bool:
    return self.indexOfProxy[_proxy] != 0


@view
@external
def getNumProxies() -> uint256:
    return self.numProxies - 1


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
