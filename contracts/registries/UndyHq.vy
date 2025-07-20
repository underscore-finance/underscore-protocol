#          ___           ___           ___                                  ___           ___     
#         /  /\         /  /\         /  /\          __                    /  /\         /  /\    
#        /  /:/        /  /::|       /  /::\        |  |\                 /  /:/        /  /::\   
#       /  /:/        /  /:|:|      /  /:/\:\       |  |:|               /  /:/        /__/:/\:\  
#      /  /:/        /  /:/|:|__   /  /:/  \:\      |  |:|              /  /::\ ___    \  \:\ \:\ 
#     /__/:/     /\ /__/:/ |:| /\ /__/:/ \__\:|     |__|:|__           /__/:/\:\  /\    \  \:\ \:\
#     \  \:\    /:/ \__\/  |:|/:/ \  \:\ /  /:/     /  /::::\          \__\/  \:\/:/     \  \:\/:/
#      \  \:\  /:/      |  |:/:/   \  \:\  /:/     /  /:/~~~~               \__\::/       \__\::/ 
#       \  \:\/:/       |__|::/     \  \:\/:/     /__/:/                    /  /:/        /  /:/  
#        \  \::/        /__/:/       \__\::/      \__\/                    /__/:/        /__/:/   
#         \__\/         \__\/            ~~                                \__\/         \__\/    
#
#     ╔═══════════════════════════════════════════════════════════════════════════════╗
#     ║  ** Undy Hq **                                                                ║
#     ║  Main address registry for Underscore protocol. Also handles minting config.  ║
#     ╚═══════════════════════════════════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/hightophq/underscore-protocol/blob/master/LICENSE.md
#     Hightop Financial, Inc. (C) 2025                                                           

# @version 0.4.3

exports: gov.__interface__
exports: registry.__interface__

initializes: gov
initializes: registry[gov := gov]

import contracts.modules.LocalGov as gov
import contracts.modules.AddressRegistry as registry

from interfaces import Department
from ethereum.ercs import IERC20

struct HqConfig:
    description: String[64]
    canMintUndy: bool
    canSetTokenBlacklist: bool

struct PendingHqConfig:
    newHqConfig: HqConfig
    initiatedBlock: uint256
    confirmBlock: uint256

event HqConfigChangeInitiated:
    regId: uint256
    description: String[64]
    canMintUndy: bool
    canSetTokenBlacklist: bool
    confirmBlock: uint256

event HqConfigChangeConfirmed:
    regId: uint256
    description: String[64]
    canMintUndy: bool
    canSetTokenBlacklist: bool
    initiatedBlock: uint256
    confirmBlock: uint256

event HqConfigChangeCancelled:
    regId: uint256
    description: String[64]
    canMintUndy: bool
    canSetTokenBlacklist: bool
    initiatedBlock: uint256
    confirmBlock: uint256

event UndyHqFundsRecovered:
    asset: indexed(address)
    recipient: indexed(address)
    balance: uint256

event MintingEnabled:
    isEnabled: bool

# hq config
hqConfig: public(HashMap[uint256, HqConfig]) # reg id -> hq config
pendingHqConfig: public(HashMap[uint256, PendingHqConfig]) # reg id -> pending hq config

# minting circuit breaker
mintEnabled: public(bool)

MAX_RECOVER_ASSETS: constant(uint256) = 20


@deploy
def __init__(
    _undyToken: address,
    _initialGov: address,
    _minGovTimeLock: uint256,
    _maxGovTimeLock: uint256,
    _minRegistryTimeLock: uint256,
    _maxRegistryTimeLock: uint256,
):
    gov.__init__(empty(address), _initialGov, _minGovTimeLock, _maxGovTimeLock, 0)
    registry.__init__(_minRegistryTimeLock, _maxRegistryTimeLock, 0, "UndyHq.vy")

    # undy token
    assert registry._startAddNewAddressToRegistry(_undyToken, "Undy Token") # dev: failed to register undy token
    assert registry._confirmNewAddressToRegistry(_undyToken) == 1 # dev: failed to confirm undy token


############
# Registry #
############


# new address


@external
def startAddNewAddressToRegistry(_addr: address, _description: String[64]) -> bool:
    assert msg.sender == gov.governance # dev: no perms
    return registry._startAddNewAddressToRegistry(_addr, _description)


@external
def confirmNewAddressToRegistry(_addr: address) -> uint256:
    assert msg.sender == gov.governance # dev: no perms
    return registry._confirmNewAddressToRegistry(_addr)


@external
def cancelNewAddressToRegistry(_addr: address) -> bool:
    assert msg.sender == gov.governance # dev: no perms
    return registry._cancelNewAddressToRegistry(_addr)


# address update


@external
def startAddressUpdateToRegistry(_regId: uint256, _newAddr: address) -> bool:
    assert msg.sender == gov.governance # dev: no perms
    return registry._startAddressUpdateToRegistry(_regId, _newAddr)


@external
def confirmAddressUpdateToRegistry(_regId: uint256) -> bool:
    assert msg.sender == gov.governance # dev: no perms
    return registry._confirmAddressUpdateToRegistry(_regId)


@external
def cancelAddressUpdateToRegistry(_regId: uint256) -> bool:
    assert msg.sender == gov.governance # dev: no perms
    return registry._cancelAddressUpdateToRegistry(_regId)


# address disable


@external
def startAddressDisableInRegistry(_regId: uint256) -> bool:
    assert not self._isUndyToken(_regId) # dev: cannot disable token

    assert msg.sender == gov.governance # dev: no perms
    return registry._startAddressDisableInRegistry(_regId)


@external
def confirmAddressDisableInRegistry(_regId: uint256) -> bool:
    assert msg.sender == gov.governance # dev: no perms
    return registry._confirmAddressDisableInRegistry(_regId)


@external
def cancelAddressDisableInRegistry(_regId: uint256) -> bool:
    assert msg.sender == gov.governance # dev: no perms
    return registry._cancelAddressDisableInRegistry(_regId)


#############
# Hq Config #
#############


@view
@external
def hasPendingHqConfigChange(_regId: uint256) -> bool:
    return self.pendingHqConfig[_regId].confirmBlock != 0


# start hq config change


@external
def initiateHqConfigChange(
    _regId: uint256,
    _canMintUndy: bool,
    _canSetTokenBlacklist: bool,
):
    assert msg.sender == gov.governance # dev: no perms

    assert self._isValidHqConfig(_regId, _canMintUndy) # dev: invalid hq config
    hqConfig: HqConfig = HqConfig(
        description= registry._getAddrDescription(_regId),
        canMintUndy= _canMintUndy,
        canSetTokenBlacklist= _canSetTokenBlacklist,
    )

    # set pending hq config
    confirmBlock: uint256 = block.number + registry.registryChangeTimeLock
    self.pendingHqConfig[_regId] = PendingHqConfig(
        newHqConfig= hqConfig,
        initiatedBlock= block.number,
        confirmBlock= confirmBlock,
    )
    log HqConfigChangeInitiated(
        regId=_regId,
        description=hqConfig.description,
        canMintUndy=_canMintUndy,
        canSetTokenBlacklist=_canSetTokenBlacklist,
        confirmBlock=confirmBlock,
    )


# confirm hq config change


@external
def confirmHqConfigChange(_regId: uint256) -> bool:
    assert msg.sender == gov.governance # dev: no perms

    data: PendingHqConfig = self.pendingHqConfig[_regId]
    assert data.confirmBlock != 0 and block.number >= data.confirmBlock # dev: time lock not reached

    # invalid hq config
    newConfig: HqConfig = data.newHqConfig
    if not self._isValidHqConfig(_regId, newConfig.canMintUndy):
        self.pendingHqConfig[_regId] = empty(PendingHqConfig)
        return False

    # set hq config
    self.hqConfig[_regId] = newConfig
    self.pendingHqConfig[_regId] = empty(PendingHqConfig)

    log HqConfigChangeConfirmed(
        regId=_regId,
        description=newConfig.description,
        canMintUndy=newConfig.canMintUndy,
        canSetTokenBlacklist=newConfig.canSetTokenBlacklist,
        initiatedBlock=data.initiatedBlock,
        confirmBlock=data.confirmBlock,
    )
    return True


# cancel hq config change


@external
def cancelHqConfigChange(_regId: uint256) -> bool:
    assert msg.sender == gov.governance # dev: no perms

    data: PendingHqConfig = self.pendingHqConfig[_regId]
    assert data.confirmBlock != 0 # dev: no pending change

    self.pendingHqConfig[_regId] = empty(PendingHqConfig)
    log HqConfigChangeCancelled(
        regId=_regId,
        description=data.newHqConfig.description,
        canMintUndy=data.newHqConfig.canMintUndy,
        canSetTokenBlacklist=data.newHqConfig.canSetTokenBlacklist,
        initiatedBlock=data.initiatedBlock,
        confirmBlock=data.confirmBlock
    )
    return True


# validation


@external
def isValidHqConfig(_regId: uint256, _canMintUndy: bool) -> bool:
    return self._isValidHqConfig(_regId, _canMintUndy)


@internal
def _isValidHqConfig(_regId: uint256, _canMintUndy: bool) -> bool:

    # tokens cannot mint, cannot set their own blacklist, cannot modify mission control
    if self._isUndyToken(_regId):
        return False

    # invalid reg id
    if not registry._isValidRegId(_regId):
        return False

    # no addr
    addr: address = registry._getAddr(_regId)
    if addr == empty(address):
        return False

    if _canMintUndy and not staticcall Department(addr).canMintUndy():
        return False

    return True


@view
@internal
def _isUndyToken(_regId: uint256) -> bool:
    return _regId == 1


##########
# Tokens #
##########


@view
@external
def undyToken() -> address:
    return registry._getAddr(1)


@view
@external
def canMintUndy(_addr: address) -> bool:
    if not self.mintEnabled:
        return False
    if _addr == empty(address):
        return False
    regId: uint256 = registry._getRegId(_addr)
    if regId == 0 or not self.hqConfig[regId].canMintUndy:
        return False
    return staticcall Department(_addr).canMintUndy()


@view
@external
def canSetTokenBlacklist(_addr: address) -> bool:
    if _addr == empty(address):
        return False
    regId: uint256 = registry._getRegId(_addr)
    if regId == 0:
        return False
    return self.hqConfig[regId].canSetTokenBlacklist


###########################
# Minting Circuit Breaker #
###########################


@external
def setMintingEnabled(_shouldEnable: bool):
    assert msg.sender == gov.governance # dev: no perms
    assert self.mintEnabled != _shouldEnable # dev: already set

    self.mintEnabled = _shouldEnable
    log MintingEnabled(isEnabled=_shouldEnable)


############
# Recovery #
############


@external
def recoverFunds(_recipient: address, _asset: address):
    assert msg.sender == gov.governance # dev: no perms
    self._recoverFunds(_recipient, _asset)


@external
def recoverFundsMany(_recipient: address, _assets: DynArray[address, MAX_RECOVER_ASSETS]):
    assert msg.sender == gov.governance # dev: no perms
    for a: address in _assets:
        self._recoverFunds(_recipient, a)


@internal
def _recoverFunds(_recipient: address, _asset: address):
    assert empty(address) not in [_recipient, _asset] # dev: invalid recipient or asset
    balance: uint256 = staticcall IERC20(_asset).balanceOf(self)
    assert balance != 0 # dev: nothing to recover

    assert extcall IERC20(_asset).transfer(_recipient, balance, default_return_value=True) # dev: recovery failed
    log UndyHqFundsRecovered(asset=_asset, recipient=_recipient, balance=balance)