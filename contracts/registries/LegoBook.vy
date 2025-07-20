#          ___       ___           ___           ___                ___           ___           ___           ___     
#         /\__\     /\  \         /\  \         /\  \              /\  \         /\  \         /\  \         /\__\    
#        /:/  /    /::\  \       /::\  \       /::\  \            /::\  \       /::\  \       /::\  \       /:/  /    
#       /:/  /    /:/\:\  \     /:/\:\  \     /:/\:\  \          /:/\:\  \     /:/\:\  \     /:/\:\  \     /:/__/     
#      /:/  /    /::\~\:\  \   /:/  \:\  \   /:/  \:\  \        /::\~\:\__\   /:/  \:\  \   /:/  \:\  \   /::\__\____ 
#     /:/__/    /:/\:\ \:\__\ /:/__/_\:\__\ /:/__/ \:\__\      /:/\:\ \:|__| /:/__/ \:\__\ /:/__/ \:\__\ /:/\:::::\__\
#     \:\  \    \:\~\:\ \/__/ \:\  /\ \/__/ \:\  \ /:/  /      \:\~\:\/:/  / \:\  \ /:/  / \:\  \ /:/  / \/_|:|~~|~   
#      \:\  \    \:\ \:\__\    \:\ \:\__\    \:\  /:/  /        \:\ \::/  /   \:\  /:/  /   \:\  /:/  /     |:|  |    
#       \:\  \    \:\ \/__/     \:\/:/  /     \:\/:/  /          \:\/:/  /     \:\/:/  /     \:\/:/  /      |:|  |    
#        \:\__\    \:\__\        \::/  /       \::/  /            \::/__/       \::/  /       \::/  /       |:|  |    
#         \/__/     \/__/         \/__/         \/__/              ~~            \/__/         \/__/         \|__|    
#
#     ╔════════════════════════════════════════════════════════════════════════════════╗
#     ║  ** Lego Book **                                                               ║
#     ║  Address registry for Legos (DeFi integrations -- yield protocols, DEXs, etc). ║
#     ╚════════════════════════════════════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/hightophq/underscore-protocol/blob/master/LICENSE.md
#     Hightop Financial, Inc. (C) 2025                                                           

# @version 0.4.3

implements: Department

exports: gov.__interface__
exports: registry.__interface__
exports: addys.__interface__
exports: deptBasics.__interface__

initializes: gov
initializes: registry[gov := gov]
initializes: addys
initializes: deptBasics[addys := addys]

import contracts.modules.LocalGov as gov
import contracts.modules.AddressRegistry as registry
import contracts.modules.Addys as addys
import contracts.modules.DeptBasics as deptBasics

from interfaces import LegoPartner as Lego
from interfaces import Department

event LegoToolsSet:
    addr: indexed(address)

legoTools: public(address)


@deploy
def __init__(
    _undyHq: address,
    _minRegistryTimeLock: uint256,
    _maxRegistryTimeLock: uint256,
):
    gov.__init__(_undyHq, empty(address), 0, 0, 0)
    registry.__init__(_minRegistryTimeLock, _maxRegistryTimeLock, 0, "LegoBook.vy")
    addys.__init__(_undyHq)
    deptBasics.__init__(False, False)


@view
@external
def isLegoAddr(_addr: address) -> bool:
    return registry._isValidAddr(_addr)


############
# Registry #
############


# new address


@external
def startAddNewAddressToRegistry(_addr: address, _description: String[64]) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return registry._startAddNewAddressToRegistry(_addr, _description)


@external
def confirmNewAddressToRegistry(_addr: address) -> uint256:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return registry._confirmNewAddressToRegistry(_addr)


@external
def cancelNewAddressToRegistry(_addr: address) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return registry._cancelNewAddressToRegistry(_addr)


# address update


@external
def startAddressUpdateToRegistry(_regId: uint256, _newAddr: address) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return registry._startAddressUpdateToRegistry(_regId, _newAddr)


@external
def confirmAddressUpdateToRegistry(_regId: uint256) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return registry._confirmAddressUpdateToRegistry(_regId)


@external
def cancelAddressUpdateToRegistry(_regId: uint256) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return registry._cancelAddressUpdateToRegistry(_regId)


# address disable


@external
def startAddressDisableInRegistry(_regId: uint256) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return registry._startAddressDisableInRegistry(_regId)


@external
def confirmAddressDisableInRegistry(_regId: uint256) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return registry._confirmAddressDisableInRegistry(_regId)


@external
def cancelAddressDisableInRegistry(_regId: uint256) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return registry._cancelAddressDisableInRegistry(_regId)


##############
# Lego Tools #
##############


@external
def setLegoTools(_addr: address) -> bool:
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    if not self._isValidLegoTools(_addr):
        return False
    self.legoTools = _addr
    log LegoToolsSet(addr = _addr)
    return True


@view
@external 
def isValidLegoTools(_addr: address) -> bool:
    return self._isValidLegoTools(_addr)


@view
@internal 
def _isValidLegoTools(_addr: address) -> bool:
    if not _addr.is_contract or _addr == empty(address):
        return False
    return _addr != self.legoTools


#############
# Utilities #
#############


@view
@internal
def _canPerformAction(_caller: address) -> bool:
    return gov._canGovern(_caller) and not deptBasics.isPaused