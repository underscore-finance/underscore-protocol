# @version 0.4.3

uses: addys

import contracts.modules.Addys as addys

from interfaces import WalletStructs as ws
from ethereum.ercs import IERC20

event AssetOpportunityAdded:
    asset: indexed(address)
    vaultAddr: indexed(address)

event AssetOpportunityRemoved:
    asset: indexed(address)
    vaultAddr: indexed(address)

event LegoPauseModified:
    isPaused: bool

event LegoFundsRecovered:
    asset: indexed(address)
    recipient: indexed(address)
    balance: uint256

# config
isPaused: public(bool)

# asset opportunities
assetOpportunities: public(HashMap[address, HashMap[uint256, address]]) # asset -> index -> vault addr
indexOfAssetOpportunity: public(HashMap[address, HashMap[address, uint256]]) # asset -> vault addr -> index
numAssetOpportunities: public(HashMap[address, uint256]) # asset -> number of opportunities

# mapping
vaultToAsset: public(HashMap[address, address]) # vault addr -> underlying asset

# lego assets (iterable)
assets: public(HashMap[uint256, address]) # index -> asset
indexOfAsset: public(HashMap[address, uint256]) # asset -> index
numAssets: public(uint256) # num assets

MAX_VAULTS: constant(uint256) = 40
MAX_ASSETS: constant(uint256) = 20
MAX_RECOVER_ASSETS: constant(uint256) = 20


@deploy
def __init__(_shouldPause: bool):
    self.isPaused = _shouldPause
    self.numAssets = 1 # not using 0 index


#########
# Views #
#########


# is lego asset


@view
@external
def isLegoAsset(_asset: address) -> bool:
    return self._isLegoAsset(_asset)


@view
@internal
def _isLegoAsset(_asset: address) -> bool:
    return self.indexOfAsset[_asset] != 0


# vault opportunities


@view
@external
def getAssetOpportunities(_asset: address) -> DynArray[address, MAX_VAULTS]:
    numOpportunities: uint256 = self.numAssetOpportunities[_asset]
    if numOpportunities == 0:
        return []
    opportunities: DynArray[address, MAX_VAULTS] = []
    for i: uint256 in range(1, numOpportunities, bound=MAX_VAULTS):
        opportunities.append(self.assetOpportunities[_asset][i])
    return opportunities


# all assets registered


@view
@external
def getAssets() -> DynArray[address, MAX_ASSETS]:
    numAssets: uint256 = self.numAssets
    if numAssets == 0:
        return []
    assets: DynArray[address, MAX_ASSETS] = []
    for i: uint256 in range(1, numAssets, bound=MAX_ASSETS):
        assets.append(self.assets[i])
    return assets


################
# Registration #
################


@view
@external
def isAssetOpportunity(_asset: address, _vaultAddr: address) -> bool:
    return self._isAssetOpportunity(_asset, _vaultAddr)


@view
@internal
def _isAssetOpportunity(_asset: address, _vaultAddr: address) -> bool:
    return self.indexOfAssetOpportunity[_asset][_vaultAddr] != 0


# add asset opportunity


@internal
def _addAssetOpportunity(_asset: address, _vaultAddr: address):
    if self.indexOfAssetOpportunity[_asset][_vaultAddr] != 0:
        return
    if empty(address) in [_asset, _vaultAddr]:
        return

    # add asset opportunity
    aid: uint256 = self.numAssetOpportunities[_asset]
    if aid == 0:
        aid = 1 # not using 0 index
    self.assetOpportunities[_asset][aid] = _vaultAddr
    self.indexOfAssetOpportunity[_asset][_vaultAddr] = aid
    self.numAssetOpportunities[_asset] = aid + 1

    # add mapping
    self.vaultToAsset[_vaultAddr] = _asset

    # add asset
    self._addAsset(_asset)

    log AssetOpportunityAdded(asset=_asset, vaultAddr=_vaultAddr)


# remove asset opportunity


@internal
def _removeAssetOpportunity(_asset: address, _vaultAddr: address):
    numOpportunities: uint256 = self.numAssetOpportunities[_asset]
    if numOpportunities == 0:
        return

    targetIndex: uint256 = self.indexOfAssetOpportunity[_asset][_vaultAddr]
    if targetIndex == 0:
        return

    # update data
    lastIndex: uint256 = numOpportunities - 1
    self.numAssetOpportunities[_asset] = lastIndex
    self.indexOfAssetOpportunity[_asset][_vaultAddr] = 0

    self.vaultToAsset[_vaultAddr] = empty(address)

    # shift to replace the removed one
    if targetIndex != lastIndex:
        lastVaultAddr: address = self.assetOpportunities[_asset][lastIndex]
        self.assetOpportunities[_asset][targetIndex] = lastVaultAddr
        self.indexOfAssetOpportunity[_asset][lastVaultAddr] = targetIndex

    # remove asset
    if lastIndex <= 1:
        self._removeAsset(_asset)

    log AssetOpportunityRemoved(asset=_asset, vaultAddr=_vaultAddr)


# add asset


@internal
def _addAsset(_asset: address):
    if self.indexOfAsset[_asset] != 0:
        return

    aid: uint256 = self.numAssets
    if aid == 0:
        aid = 1 # not using 0 index
    self.assets[aid] = _asset
    self.indexOfAsset[_asset] = aid
    self.numAssets = aid + 1


# remove asset


@internal
def _removeAsset(_asset: address):
    numAssets: uint256 = self.numAssets
    if numAssets == 0:
        return

    targetIndex: uint256 = self.indexOfAsset[_asset]
    if targetIndex == 0:
        return

    # update data
    lastIndex: uint256 = numAssets - 1
    self.numAssets = lastIndex
    self.indexOfAsset[_asset] = 0

    # shift to replace the removed one
    if targetIndex != lastIndex:
        lastAsset: address = self.assets[lastIndex]
        self.assets[targetIndex] = lastAsset
        self.indexOfAsset[lastAsset] = targetIndex


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


# fill mini addys


@view
@internal
def _getMiniAddys(_miniAddys: ws.MiniAddys = empty(ws.MiniAddys)) -> ws.MiniAddys:
    if _miniAddys.ledger != empty(address):
        return _miniAddys
    return ws.MiniAddys(
        ledger = addys._getLedgerAddr(),
        missionControl = addys._getMissionControlAddr(),
        legoBook = addys._getLegoBookAddr(),
        appraiser = addys._getAppraiserAddr(),
    )


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