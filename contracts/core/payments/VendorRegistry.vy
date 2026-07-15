#      _    __               __              ____             _      __            
#     | |  / /__  ____  ____/ /___  _____   / __ \___  ____ _(_)____/ /________  __
#     | | / / _ \/ __ \/ __  / __ \/ ___/  / /_/ / _ \/ __ `/ / ___/ __/ ___/ / / /
#     | |/ /  __/ / / / /_/ / /_/ / /     / _, _/  __/ /_/ / (__  ) /_/ /  / /_/ / 
#     |___/\___/_/ /_/\__,_/\____/_/     /_/ |_|\___/\__, /_/____/\__/_/   \__, /  
#                                                   /____/                /____/   
#
#     ╔═══════════════════════════════════════════════════════════════════╗
#     ║  ** Vendor Registry **                                            ║
#     ║  UndyHq dept: vendor factory + registry (dests live in vendors)   ║
#     ╚═══════════════════════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# The verified-service registry for agent payments. Deploys one VendorProxy per service and
# records it in a simple 1-based registry — each row carries the vendor address plus its human string id
# (e.g. "x402joker.com"), so the id lives on the record (no separate id index). A vendor is "live" while
# it holds a registry slot: the PayProcessor gates settlement on `indexOfVendor(vendor) != 0`, and
# removeVendor takes it back out (there is no separate enabled/disabled flag). The Switchboard may
# create and remove vendors. A vendor's allow-listed destinations are NOT managed here:
# they live inside each vendor (self-contained) and are edited directly on the vendor by the Switchboard.

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

vendorTemplate: public(address)                                     # blueprint for VendorProxy

struct VendorData:
    vendor: address
    id: String[128]

# vendor registry (1-based; count == numVendors - 1). Removal swaps the last row into the freed slot.
numVendors: public(uint256)                                       # next free regId (starts at 1)
vendors: public(HashMap[uint256, VendorData])                      # regId -> record (id lives on the record)
indexOfVendor: public(HashMap[address, uint256])                   # vendor -> regId (0 = not a vendor)

event VendorCreated:
    vendor: indexed(address)
    id: String[128]

event VendorRemoved:
    vendor: indexed(address)

event VendorTemplateSet:
    template: indexed(address)


@deploy
def __init__(_undyHq: address, _vendorTemplate: address):
    addys.__init__(_undyHq)
    deptBasics.__init__(False, False)  # not paused; cannot mint UNDY
    HQ = _undyHq
    self.vendorTemplate = _vendorTemplate
    self.numVendors = 1  # 1-based registry (Underscore list style)


###########
# factory #
###########


@external
def createVendor(_id: String[128]) -> address:
    assert not deptBasics.isPaused  # dev: paused
    assert addys._isSwitchboardAddr(msg.sender)  # dev: no perms
    template: address = self.vendorTemplate
    assert template != empty(address)  # dev: no template
    vendor: address = create_from_blueprint(template, HQ)
    pid: uint256 = self.numVendors
    self.vendors[pid] = VendorData(vendor=vendor, id=_id)
    self.indexOfVendor[vendor] = pid
    self.numVendors = pid + 1
    log VendorCreated(vendor=vendor, id=_id)
    return vendor


@external
def removeVendor(_vendor: address):
    # Remove a vendor from the registry (the "kill switch"): the PayProcessor gates on
    # `indexOfVendor(vendor) != 0`, so a removed vendor can no longer settle. Swap-remove keeps the list
    # dense (mirrors the Underscore whitelist idiom); re-listing a service means a fresh createVendor.
    assert not deptBasics.isPaused  # dev: paused
    assert addys._isSwitchboardAddr(msg.sender)  # dev: no perms
    targetIndex: uint256 = self.indexOfVendor[_vendor]
    assert targetIndex != 0  # dev: not a vendor

    lastIndex: uint256 = self.numVendors - 1
    self.numVendors = lastIndex

    lastData: VendorData = self.vendors[lastIndex]
    self.vendors[targetIndex] = lastData
    self.indexOfVendor[lastData.vendor] = targetIndex
    self.vendors[lastIndex] = empty(VendorData)
    self.indexOfVendor[_vendor] = 0
    log VendorRemoved(vendor=_vendor)


#########
# views #
#########


@view
@external
def isVendor(_vendor: address) -> bool:
    return self.indexOfVendor[_vendor] != 0


@view
@external
def getNumVendors() -> uint256:
    return self.numVendors - 1


#############################
# admin (Switchboard-gated) #
#############################


@external
def setVendorTemplate(_template: address):
    assert addys._isSwitchboardAddr(msg.sender)  # dev: no perms
    self.vendorTemplate = _template
    log VendorTemplateSet(template=_template)
