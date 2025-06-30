# @version 0.4.3

uses: addys

import contracts.modules.Addys as addys
from ethereum.ercs import IERC20

event LegoPauseModified:
    isPaused: bool

event LegoFundsRecovered:
    asset: indexed(address)
    recipient: indexed(address)
    balance: uint256

# config
isPaused: public(bool)

# lego assets (iterable)
assets: public(HashMap[uint256, address]) # index -> asset
indexOfAsset: public(HashMap[address, uint256]) # asset -> index
numAssets: public(uint256) # num assets

MAX_RECOVER_ASSETS: constant(uint256) = 20


@deploy
def __init__(_shouldPause: bool):
    self.isPaused = _shouldPause
    self.numAssets = 1 # not using 0 index


################
# Registration #
################


# is lego asset


@view
@external
def isLegoAsset(_asset: address) -> bool:
    return self.indexOfAsset[_asset] != 0


# register lego asset


@internal
def _registerLegoAsset(_asset: address):
    if self.indexOfAsset[_asset] != 0:
        return

    aid: uint256 = self.numAssets
    self.assets[aid] = _asset
    self.indexOfAsset[_asset] = aid
    self.numAssets = aid + 1


# deregister lego asset


@external
def deregisterLegoAsset(_asset: address) -> bool:
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms

    numAssets: uint256 = self.numAssets
    if numAssets == 0:
        return False

    targetIndex: uint256 = self.indexOfAsset[_asset]
    if targetIndex == 0:
        return False

    # update data
    lastIndex: uint256 = numAssets - 1
    self.numAssets = lastIndex
    self.indexOfAsset[_asset] = 0

    # get last item, replace the removed item
    if targetIndex != lastIndex:
        lastItem: address = self.assets[lastIndex]
        self.assets[targetIndex] = lastItem
        self.indexOfAsset[lastItem] = targetIndex

    return True


# num lego assets (true number, use `numAssets` for iteration)


@view
@external
def getNumLegoAssets() -> uint256:
    return self._getNumLegoAssets()


@view
@internal
def _getNumLegoAssets() -> uint256:
    numAssets: uint256 = self.numAssets
    if numAssets == 0:
        return 0
    return numAssets - 1


###########
# General #
###########


# activate


@external
def pause(_shouldPause: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert _shouldPause != self.isPaused # dev: no change
    self.isPaused = _shouldPause
    log LegoPauseModified(isPaused=_shouldPause)


# recover funds


@external
def recoverFunds(_recipient: address, _asset: address):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    self._recoverFunds(_recipient, _asset)


@external
def recoverFundsMany(_recipient: address, _assets: DynArray[address, MAX_RECOVER_ASSETS]):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    for a: address in _assets:
        self._recoverFunds(_recipient, a)


@internal
def _recoverFunds(_recipient: address, _asset: address):
    assert empty(address) not in [_recipient, _asset] # dev: invalid recipient or asset
    balance: uint256 = staticcall IERC20(_asset).balanceOf(self)
    assert balance != 0 # dev: nothing to recover

    assert extcall IERC20(_asset).transfer(_recipient, balance, default_return_value=True) # dev: recovery failed
    log LegoFundsRecovered(asset=_asset, recipient=_recipient, balance=balance)