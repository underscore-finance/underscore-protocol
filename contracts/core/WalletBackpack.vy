# @version 0.4.3

implements: Department

exports: addys.__interface__
exports: deptBasics.__interface__

initializes: addys
initializes: deptBasics[addys := addys]

import contracts.modules.Addys as addys
import contracts.modules.DeptBasics as deptBasics
from interfaces import Department

interface MissionControl:
    def getSwapFee(_user: address, _tokenIn: address, _tokenOut: address) -> uint256: view
    def isYieldAssetAndGetDecimals(_asset: address) -> (bool, uint256): view
    def getRewardsFee(_user: address, _asset: address) -> uint256: view
    def yieldAssetConfig(_asset: address) -> YieldAssetConfig: view
    def feeRecipient() -> address: view

interface Ledger:
    def setUserAndGlobalPoints(_user: address, _userData: PointsData, _globalData: PointsData): nonpayable
    def getUserAndGlobalPoints(_user: address) -> (PointsData, PointsData): view
    def getLastTotalUsdValue(_user: address) -> uint256: view
    def isUserWallet(_user: address) -> bool: view

interface UserWallet:
    def updateAssetData(_legoId: uint256, _asset: address, _shouldCheckYield: bool) -> uint256: nonpayable

interface RipePriceDesk:
    def getPrice(_asset: address, _shouldRaise: bool = False) -> uint256: view

interface Switchboard:
    def isSwitchboardAddr(_addr: address) -> bool: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

struct YieldAssetConfig:
    legoId: uint256
    isRebasing: bool
    underlyingAsset: address
    maxYieldIncrease: uint256
    yieldProfitFee: uint256

struct PointsData:
    usdValue: uint256
    depositPoints: uint256
    lastUpdate: uint256

struct BackpackData:
    legoBook: address
    feeRecipient: address
    lastTotalUsdValue: uint256

struct LastPrice:
    price: uint256
    lastUpdate: uint256

# price cache
lastPrice: public(HashMap[address, LastPrice]) # asset -> last price

EIGHTEEN_DECIMALS: constant(uint256) = 10 ** 18
LEDGER_ID: constant(uint256) = 2
MISSION_CONTROL_ID: constant(uint256) = 3
LEGO_BOOK_ID: constant(uint256) = 4

# ripe
RIPE_HQ: immutable(address)
RIPE_PRICE_DESK_ID: constant(uint256) = 7


@deploy
def __init__(_undyHq: address, _ripeHq: address):
    addys.__init__(_undyHq)
    deptBasics.__init__(False, False) # no minting

    assert _ripeHq != empty(address) # dev: invalid ripe hq
    RIPE_HQ = _ripeHq


##############
# Main Addys #
##############


@view
@external
def getBackpackData(_userWallet: address) -> BackpackData:
    hq: address = addys._getUndyHq()
    mc: address = staticcall Registry(hq).getAddr(MISSION_CONTROL_ID)
    ledger: address = staticcall Registry(hq).getAddr(LEDGER_ID)

    return BackpackData(
        legoBook = staticcall Registry(hq).getAddr(LEGO_BOOK_ID),
        feeRecipient = staticcall MissionControl(mc).feeRecipient(),
        lastTotalUsdValue = staticcall Ledger(ledger).getLastTotalUsdValue(_userWallet),
    )


#####################
# Post Action Tasks #
#####################


# post action tasks


@external
def performPostActionTasks(_newUserValue: uint256):
    ledger: address = addys._getLedgerAddr()
    assert staticcall Ledger(ledger).isUserWallet(msg.sender) # dev: not a user wallet

    # check trial funds first
    assert self._doesWalletStillHaveTrialFunds(msg.sender) # dev: user no longer has trial funds

    # update points
    self._updateDepositPoints(msg.sender, _newUserValue, ledger)


# deposit points


@internal
def _updateDepositPoints(_user: address, _newUserValue: uint256, _ledger: address):
    userPoints: PointsData = empty(PointsData)
    globalPoints: PointsData = empty(PointsData)
    userPoints, globalPoints = staticcall Ledger(_ledger).getUserAndGlobalPoints(_user)

    # update user data
    prevUserValue: uint256 = userPoints.usdValue
    userPoints.depositPoints += self._getLatestDepositPoints(prevUserValue, userPoints.lastUpdate)
    userPoints.usdValue = _newUserValue
    userPoints.lastUpdate = block.number
    
    # update global data
    globalPoints.depositPoints += self._getLatestDepositPoints(globalPoints.usdValue, globalPoints.lastUpdate)
    globalPoints.usdValue -= prevUserValue
    globalPoints.usdValue += _newUserValue
    globalPoints.lastUpdate = block.number

    # save data
    extcall Ledger(_ledger).setUserAndGlobalPoints(_user, userPoints, globalPoints)


# latest points


@view
@internal
def _getLatestDepositPoints(_usdValue: uint256, _lastUpdate: uint256) -> uint256:
    if _usdValue == 0 or _lastUpdate == 0 or block.number <= _lastUpdate:
        return 0
    points: uint256 = _usdValue * (block.number - _lastUpdate)
    return points // EIGHTEEN_DECIMALS


################
# Update Asset #
################


@external
def updateAssetInWallet(_legoId: uint256, _user: address, _asset: address, _shouldCheckYield: bool):
    a: addys.Addys = addys._getAddys()
    assert staticcall Switchboard(a.switchboard).isSwitchboardAddr(msg.sender) # dev: no perms

    assert _asset != empty(address) # dev: invalid asset
    newUserValue: uint256 = extcall UserWallet(_user).updateAssetData(_legoId, _asset, _shouldCheckYield)
    self._updateDepositPoints(_user, newUserValue, a.ledger)


###############
# Trial Funds #
###############


@view
@external
def doesWalletStillHaveTrialFunds(_user: address) -> bool:
    return self._doesWalletStillHaveTrialFunds(_user)


@view
@internal
def _doesWalletStillHaveTrialFunds(_user: address) -> bool:
    # TODO: implement this
    return True


##########################
# Mission Control Config #
##########################


@view
@external
def getSwapFee(_user: address, _tokenIn: address, _tokenOut: address) -> uint256:
    return staticcall MissionControl(addys._getMissionControlAddr()).getSwapFee(_user, _tokenIn, _tokenOut)


@view
@external
def getRewardsFee(_user: address, _asset: address) -> uint256:
    return staticcall MissionControl(addys._getMissionControlAddr()).getRewardsFee(_user, _asset)


@view
@external
def getYieldAssetConfig(_asset: address, _legoId: uint256, _underlyingAsset: address) -> YieldAssetConfig:
    mc: address = addys._getMissionControlAddr()
    yieldAssetConfig: YieldAssetConfig = staticcall MissionControl(mc).yieldAssetConfig(_asset)

    # TODO: if no config, check if any lego defaults (all Aave v3 will be rebasing for example).
    # check underlying for stablecoin, maybe make max increase lower 
    # use default maxYieldIncrease, and yieldProfitFee if no specific asset config

    return yieldAssetConfig


@view
@external
def isYieldAssetAndGetDecimals(_asset: address) -> (bool, uint256):
    return staticcall MissionControl(addys._getMissionControlAddr()).isYieldAssetAndGetDecimals(_asset)


#################
# Price Support #
#################


# get price


@view
@external
def getPrice(_asset: address, _isYieldAsset: bool, _staleBlocks: uint256) -> uint256:
    data: LastPrice = empty(LastPrice)
    na: bool = False
    data, na = self._getPrice(_asset, _isYieldAsset, _staleBlocks)
    return data.price


@view
@internal
def _getPrice(_asset: address, _isYieldAsset: bool, _staleBlocks: uint256 = 0) -> (LastPrice, bool):
    data: LastPrice = self.lastPrice[_asset]

    # same block, return cached price
    if data.lastUpdate == block.number:
        return data, False

    prevPrice: uint256 = data.price

    # yield assets handled slightly differently
    if _isYieldAsset:
        data.price = self._getYieldAssetPrice(_asset)

    # normal assets
    else:

        # TODO: get stale blocks from asset config

        # check if recent price is good enough
        if _staleBlocks != 0 and data.lastUpdate + _staleBlocks > block.number:
            return data, False

        # get price from Ripe
        data.price = self._getRipePrice(_asset)

    # check if price changed
    didPriceChange: bool = False
    if data.price != prevPrice:
        didPriceChange = True

    data.lastUpdate = block.number
    return data, didPriceChange


@view
@internal
def _getYieldAssetPrice(_asset: address) -> uint256:
    # TODO: get CURRENT price per share from Lego, instead of snapshot/weighted ripe price
    return self._getRipePrice(_asset)


# update price


@external
def updateAndGetUsdValue(
    _asset: address,
    _amount: uint256,
    _decimals: uint256,
    _isYieldAsset: bool,
    _legoAddr: address,
) -> uint256:
    assert staticcall Ledger(addys._getLedgerAddr()).isUserWallet(msg.sender) # dev: no perms

    if _asset == empty(address):
        return 0

    # get latest price
    data: LastPrice = empty(LastPrice)
    didPriceChange: bool = False
    data, didPriceChange = self._getPrice(_asset, _isYieldAsset)

    # only save if price changed
    if didPriceChange:
        self.lastPrice[_asset] = data

    # TODO: might need to use legoAddr for some prices

    return data.price * _amount // (10 ** _decimals)


@external
def updateAndGetPricePerShare(_asset: address, _legoAddr: address) -> uint256:
    # TODO: implement this
    return 0


# ripe integration 


@view
@external
def getRipePrice(_asset: address) -> uint256:
    return self._getRipePrice(_asset)


@view
@internal
def _getRipePrice(_asset: address) -> uint256:
    ripePriceDesk: address = staticcall Registry(RIPE_HQ).getAddr(RIPE_PRICE_DESK_ID)
    if ripePriceDesk == empty(address):
        return 0
    return staticcall RipePriceDesk(ripePriceDesk).getPrice(_asset, False)
