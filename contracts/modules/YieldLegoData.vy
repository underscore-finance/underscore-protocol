#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

uses: addys

import contracts.modules.Addys as addys

from interfaces import WalletStructs as ws
from interfaces import LegoStructs as ls
from ethereum.ercs import IERC20
from ethereum.ercs import IERC20Detailed

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

event PricePerShareSnapShotAdded:
    vaultToken: indexed(address)
    totalSupply: uint256
    pricePerShare: uint256

event SnapShotPriceConfigSet:
    minSnapshotDelay: uint256
    maxNumSnapshots: uint256
    maxUpsideDeviation: uint256
    staleTime: uint256

# core
vaultToAsset: public(HashMap[address, ls.VaultTokenInfo]) # vault addr -> data

# asset opportunities
assetOpportunities: public(HashMap[address, HashMap[uint256, address]]) # asset -> index -> vault addr
indexOfAssetOpportunity: public(HashMap[address, HashMap[address, uint256]]) # asset -> vault addr -> index
numAssetOpportunities: public(HashMap[address, uint256]) # asset -> number of opportunities

# lego assets (iterable)
assets: public(HashMap[uint256, address]) # index -> asset
indexOfAsset: public(HashMap[address, uint256]) # asset -> index
numAssets: public(uint256) # num assets

# price snapshots
snapShotData: public(HashMap[address, ls.SnapShotData]) # vault token -> data
snapShots: public(HashMap[address, HashMap[uint256, ls.SingleSnapShot]]) # vault token -> index -> snapshot
snapShotPriceConfig: public(ls.SnapShotPriceConfig) # config

isPaused: public(bool)

MAX_VAULTS: constant(uint256) = 40
MAX_ASSETS: constant(uint256) = 20
MAX_RECOVER_ASSETS: constant(uint256) = 20
ONE_DAY_SECONDS: constant(uint256) = 60 * 60 * 24
ONE_WEEK_SECONDS: constant(uint256) = ONE_DAY_SECONDS * 7
HUNDRED_PERCENT: constant(uint256) = 100_00


@deploy
def __init__(_shouldPause: bool):
    self.isPaused = _shouldPause
    self.numAssets = 1 # not using 0 index

    # default snapshot price config
    self.snapShotPriceConfig = ls.SnapShotPriceConfig(
        minSnapshotDelay = 60 * 10, # 10 minutes
        maxNumSnapshots = 20,
        maxUpsideDeviation = 10_00, # 10%
        staleTime = 3 * ONE_DAY_SECONDS, # 3 days
    )


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
def _addAssetOpportunity(_asset: address, _vaultAddr: address) -> ls.VaultTokenInfo:
    if self.indexOfAssetOpportunity[_asset][_vaultAddr] != 0:
        return self.vaultToAsset[_vaultAddr]

    if empty(address) in [_asset, _vaultAddr]:
        return empty(ls.VaultTokenInfo)

    # add asset opportunity
    aid: uint256 = self.numAssetOpportunities[_asset]
    if aid == 0:
        aid = 1 # not using 0 index
    self.assetOpportunities[_asset][aid] = _vaultAddr
    self.indexOfAssetOpportunity[_asset][_vaultAddr] = aid
    self.numAssetOpportunities[_asset] = aid + 1

    # add mapping
    vaultInfo: ls.VaultTokenInfo = ls.VaultTokenInfo(
        underlyingAsset = _asset,
        decimals = convert(staticcall IERC20Detailed(_vaultAddr).decimals(), uint256),
        lastAveragePricePerShare = 0,
    )
    self.vaultToAsset[_vaultAddr] = vaultInfo

    # add asset
    self._addAsset(_asset)

    log AssetOpportunityAdded(asset=_asset, vaultAddr=_vaultAddr)
    return vaultInfo


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

    self.vaultToAsset[_vaultAddr] = empty(ls.VaultTokenInfo)

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


###################
# Price Snapshots #
###################


# add price snapshot


@internal
def _addPriceSnapshot(_vaultToken: address, _pricePerShare: uint256, _vaultTokenDecimals: uint256) -> bool:
    config: ls.SnapShotPriceConfig = self.snapShotPriceConfig
    if config.maxNumSnapshots == 0:
        return False

    data: ls.SnapShotData = self.snapShotData[_vaultToken]

    # already have snapshot for this time
    if data.lastSnapShot.lastUpdate == block.timestamp:
        return False

    # check if snapshot is too recent
    if data.lastSnapShot.lastUpdate + config.minSnapshotDelay > block.timestamp:
        return False

    # create and store new snapshot
    newSnapshot: ls.SingleSnapShot = self._getLatestSnapshot(_vaultToken, _pricePerShare, _vaultTokenDecimals, data.lastSnapShot, config)
    data.lastSnapShot = newSnapshot
    self.snapShots[_vaultToken][data.nextIndex] = newSnapshot

    # update index
    data.nextIndex += 1
    if data.nextIndex >= config.maxNumSnapshots:
        data.nextIndex = 0

    # save snap shot data
    self.snapShotData[_vaultToken] = data

    # update cached weighted average price per share
    self.vaultToAsset[_vaultToken].lastAveragePricePerShare = self._getWeightedPricePerShare(_vaultToken, _pricePerShare)

    log PricePerShareSnapShotAdded(
        vaultToken = _vaultToken,
        totalSupply = newSnapshot.totalSupply,
        pricePerShare = newSnapshot.pricePerShare,
    )
    return True


# weighted price per share


@view
@external
def getWeightedPricePerShare(_vaultToken: address) -> uint256:
    data: ls.SnapShotData = self.snapShotData[_vaultToken]
    return self._getWeightedPricePerShare(_vaultToken, data.lastSnapShot.pricePerShare)


@view
@internal
def _getWeightedPricePerShare(_vaultToken: address, _lastPricePerShare: uint256) -> uint256:
    config: ls.SnapShotPriceConfig = self.snapShotPriceConfig
    if config.maxNumSnapshots == 0:
        return 0

    # calculate weighted average price using all valid snapshots
    numerator: uint256 = 0
    denominator: uint256 = 0
    for i: uint256 in range(config.maxNumSnapshots, bound=max_value(uint256)):

        snapShot: ls.SingleSnapShot = self.snapShots[_vaultToken][i]
        if snapShot.pricePerShare == 0 or snapShot.totalSupply == 0 or snapShot.lastUpdate == 0:
            continue

        # too stale, skip
        if config.staleTime != 0 and block.timestamp > snapShot.lastUpdate + config.staleTime:
            continue

        numerator += (snapShot.totalSupply * snapShot.pricePerShare)
        denominator += snapShot.totalSupply

    # weighted price per share
    weightedPricePerShare: uint256 = 0
    if numerator != 0:
        weightedPricePerShare = numerator // denominator
    else:
        weightedPricePerShare = _lastPricePerShare

    return weightedPricePerShare


# latest snapshot


@view
@external
def getLatestSnapshot(_vaultToken: address, _pricePerShare: uint256) -> ls.SingleSnapShot:
    data: ls.SnapShotData = self.snapShotData[_vaultToken]
    config: ls.SnapShotPriceConfig = self.snapShotPriceConfig
    vaultTokenDecimals: uint256 = self.vaultToAsset[_vaultToken].decimals
    return self._getLatestSnapshot(_vaultToken, _pricePerShare, vaultTokenDecimals, data.lastSnapShot, config)


@view
@internal
def _getLatestSnapshot(
    _vaultToken: address,
    _pricePerShare: uint256,
    _vaultTokenDecimals: uint256,
    _lastSnapShot: ls.SingleSnapShot,
    _config: ls.SnapShotPriceConfig,
) -> ls.SingleSnapShot:

    # total supply (adjusted)
    totalSupply: uint256 = staticcall IERC20(_vaultToken).totalSupply() // (10 ** _vaultTokenDecimals)

    # throttle upside (extra safety check)
    pricePerShare: uint256 = self._throttleUpside(_pricePerShare, _lastSnapShot.pricePerShare, _config.maxUpsideDeviation)

    return ls.SingleSnapShot(
        totalSupply = totalSupply,
        pricePerShare = pricePerShare,
        lastUpdate = block.timestamp,
    )


@view
@internal
def _throttleUpside(_newValue: uint256, _prevValue: uint256, _maxUpside: uint256) -> uint256:
    if _maxUpside == 0 or _prevValue == 0 or _newValue == 0:
        return _newValue
    maxPricePerShare: uint256 = _prevValue + (_prevValue * _maxUpside // HUNDRED_PERCENT)
    return min(_newValue, maxPricePerShare)


# snapshot price config


@external
def setSnapShotPriceConfig(_config: ls.SnapShotPriceConfig):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert self._isValidPriceConfig(_config) # dev: invalid config
    self.snapShotPriceConfig = _config
    log SnapShotPriceConfigSet(
        minSnapshotDelay=_config.minSnapshotDelay,
        maxNumSnapshots=_config.maxNumSnapshots,
        maxUpsideDeviation=_config.maxUpsideDeviation,
        staleTime=_config.staleTime
    )


@view
@external
def isValidPriceConfig(_config: ls.SnapShotPriceConfig) -> bool:
    return self._isValidPriceConfig(_config)


@view
@internal
def _isValidPriceConfig(_config: ls.SnapShotPriceConfig) -> bool:
    if _config.minSnapshotDelay > ONE_WEEK_SECONDS:
        return False
    if _config.maxNumSnapshots == 0 or _config.maxNumSnapshots > 25:
        return False
    if _config.maxUpsideDeviation > HUNDRED_PERCENT:
        return False
    return _config.staleTime < ONE_WEEK_SECONDS