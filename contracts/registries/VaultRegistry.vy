#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

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

interface EarnVault:
    def totalAssets() -> uint256: view
    def asset() -> address: view

interface Appraiser:
    def getUsdValue(_asset: address, _amount: uint256, _missionControl: address = empty(address), _legoBook: address = empty(address), _ledger: address = empty(address)) -> uint256: view

interface Switchboard:
    def isSwitchboardAddr(_addr: address) -> bool: view

interface UndyHq:
    def getAddr(_regId: uint256) -> address: view

event LockedMinVaultValueSet:
    minValue: uint256

hasBeenEarnVault: public(HashMap[address, bool]) # vault addr -> is earn vault
lockedMinVaultValue: public(uint256)

EIGHTEEN_DECIMALS: constant(uint256) = 10 ** 18
SWITCHBOARD_ID: constant(uint256) = 4


@deploy
def __init__(
    _undyHq: address,
    _tempGov: address,
    _minRegistryTimeLock: uint256,
    _maxRegistryTimeLock: uint256,
):
    gov.__init__(_undyHq, _tempGov, 0, 0, 0)
    registry.__init__(_minRegistryTimeLock, _maxRegistryTimeLock, 0, "VaultRegistry.vy")
    addys.__init__(_undyHq)
    deptBasics.__init__(False, False)

    self.lockedMinVaultValue = 100 * EIGHTEEN_DECIMALS


############
# Registry #
############


# new address


@external
def startAddNewAddressToRegistry(_vaultAddr: address, _description: String[64]) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return registry._startAddNewAddressToRegistry(_vaultAddr, _description)


@external
def confirmNewAddressToRegistry(_vaultAddr: address) -> uint256:
    assert self._canPerformAction(msg.sender) # dev: no perms
    regId: uint256 = registry._confirmNewAddressToRegistry(_vaultAddr)
    if regId != 0:
        self.hasBeenEarnVault[_vaultAddr] = True
    return regId


@external
def cancelNewAddressToRegistry(_vaultAddr: address) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return registry._cancelNewAddressToRegistry(_vaultAddr)


# address update


@external
def startAddressUpdateToRegistry(_regId: uint256, _newAddr: address) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    assert self._canReplaceOrDisableVault(_regId) # dev: cannot update vault
    return registry._startAddressUpdateToRegistry(_regId, _newAddr)


@external
def confirmAddressUpdateToRegistry(_regId: uint256) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    assert self._canReplaceOrDisableVault(_regId) # dev: cannot update vault
    isConfirmed: bool = registry._confirmAddressUpdateToRegistry(_regId)
    if isConfirmed:
        vaultAddr: address = registry._getAddr(_regId)
        self.hasBeenEarnVault[vaultAddr] = True
    return isConfirmed


@external
def cancelAddressUpdateToRegistry(_regId: uint256) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return registry._cancelAddressUpdateToRegistry(_regId)


# address disable


@external
def startAddressDisableInRegistry(_regId: uint256) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    assert self._canReplaceOrDisableVault(_regId) # dev: cannot disable vault
    return registry._startAddressDisableInRegistry(_regId)


@external
def confirmAddressDisableInRegistry(_regId: uint256) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    assert self._canReplaceOrDisableVault(_regId) # dev: cannot disable vault
    return registry._confirmAddressDisableInRegistry(_regId)


@external
def cancelAddressDisableInRegistry(_regId: uint256) -> bool:
    assert self._canPerformAction(msg.sender) # dev: no perms
    return registry._cancelAddressDisableInRegistry(_regId)


#############
# Utilities #
#############


# gov access


@view
@internal
def _canPerformAction(_caller: address) -> bool:
    return gov._canGovern(_caller) and not deptBasics.isPaused


# is signer switchboard


@view
@internal
def _isSwitchboardAddr(_signer: address) -> bool:
    switchboard: address = staticcall UndyHq(addys._getUndyHq()).getAddr(SWITCHBOARD_ID)
    if switchboard == empty(address):
        return False
    return staticcall Switchboard(switchboard).isSwitchboardAddr(_signer)


# can replace or disable vault


@view
@internal
def _canReplaceOrDisableVault(_regId: uint256) -> bool:
    vaultAddr: address = registry._getAddr(_regId)
    totalAssets: uint256 = staticcall EarnVault(vaultAddr).totalAssets()
    if totalAssets == 0:
        return True
    asset: address = staticcall EarnVault(vaultAddr).asset()
    usdValue: uint256 = staticcall Appraiser(addys._getAppraiserAddr()).getUsdValue(asset, totalAssets)
    return usdValue != 0 and usdValue < self.lockedMinVaultValue


# locked min vault value


@external
def setLockedMinVaultValue(_minValue: uint256):
    assert self._isSwitchboardAddr(msg.sender) # dev: no perms
    self.lockedMinVaultValue = _minValue
    log LockedMinVaultValueSet(minValue = _minValue)