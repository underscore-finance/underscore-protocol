# @version 0.4.3

implements: Department

exports: addys.__interface__
exports: deptBasics.__interface__

initializes: addys
initializes: deptBasics[addys := addys]

import contracts.modules.Addys as addys
import contracts.modules.DeptBasics as deptBasics
from interfaces import Department
from interfaces import LegoPartner as Lego

from ethereum.ercs import IERC20Detailed

interface MissionControl:
    def getAssetUsdValueConfig(_asset: address) -> AssetUsdValueConfig: view
    def getProfitCalcConfig(_asset: address) -> ProfitCalcConfig: view

interface RipePriceDesk:
    def getPrice(_asset: address, _shouldRaise: bool = False) -> uint256: view

interface Ledger:
    def isUserWallet(_user: address) -> bool: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

struct LastPrice:
    price: uint256
    lastUpdate: uint256

struct LastPricePerShare:
    underlyingAsset: address
    pricePerShare: uint256
    lastUpdate: uint256

# helpers

struct AssetUsdValueConfig:
    legoId: uint256
    legoAddr: address
    decimals: uint256
    staleBlocks: uint256
    isYieldAsset: bool
    underlyingAsset: address

struct ProfitCalcConfig:
    legoId: uint256
    legoAddr: address
    decimals: uint256
    staleBlocks: uint256
    isYieldAsset: bool
    isRebasing: bool
    underlyingAsset: address
    maxYieldIncrease: uint256
    yieldProfitFee: uint256

# price cache
lastPrice: public(HashMap[address, LastPrice]) # asset -> last price
lastPricePerShare: public(HashMap[address, LastPricePerShare]) # asset -> last price per share

HUNDRED_PERCENT: constant(uint256) = 100_00 # 100.00%
LEDGER_ID: constant(uint256) = 2
MISSION_CONTROL_ID: constant(uint256) = 3
LEGO_BOOK_ID: constant(uint256) = 4

# ripe
RIPE_HQ: immutable(address)
RIPE_PRICE_DESK_ID: constant(uint256) = 7

WETH: public(immutable(address))
ETH: public(immutable(address))


@deploy
def __init__(
    _undyHq: address,
    _ripeHq: address,
    _wethAddr: address,
    _ethAddr: address,
):
    addys.__init__(_undyHq)
    deptBasics.__init__(False, False) # no minting

    assert _ripeHq != empty(address) # dev: invalid ripe hq
    RIPE_HQ = _ripeHq

    WETH = _wethAddr
    ETH = _ethAddr


##################
# Yield Handling #
##################


@external
def calculateYieldProfits(
    _asset: address,
    _currentBalance: uint256,
    _assetBalance: uint256,
    _lastYieldPrice: uint256,
    _missionControl: address,
    _legoBook: address,
) -> (uint256, uint256, uint256):
    assert self._isCallerUserWallet(msg.sender, addys._getUndyHq()) # dev: no perms

    config: ProfitCalcConfig = self._getProfitCalcConfig(_asset, _missionControl, _legoBook)
    if not config.isYieldAsset:
        return 0, 0, 0

    if config.isRebasing:
        return self._handleRebaseYieldAsset(_asset, _currentBalance, _assetBalance, config.maxYieldIncrease, config.yieldProfitFee)
    else:
        return self._handleNormalYieldAsset(_asset, _currentBalance, _assetBalance, _lastYieldPrice, config)


# rebasing assets


@internal
def _handleRebaseYieldAsset(
    _asset: address,
    _currentBalance: uint256,
    _lastBalance: uint256,
    _maxYieldIncrease: uint256,
    _yieldProfitFee: uint256,
) -> (uint256, uint256, uint256):

    # no profits if balance decreased or stayed the same
    if _currentBalance <= _lastBalance:
        return 0, 0, 0
    
    # calculate the actual profit
    uncappedProfit: uint256 = _currentBalance - _lastBalance
    actualProfit: uint256 = uncappedProfit
    
    # apply max yield increase cap if configured
    if _maxYieldIncrease != 0:
        maxAllowedProfit: uint256 = _lastBalance * _maxYieldIncrease // HUNDRED_PERCENT
        actualProfit = min(uncappedProfit, maxAllowedProfit)
    
    # no profits after applying cap
    if actualProfit == 0:
        return 0, 0, 0
    
    return 0, actualProfit, _yieldProfitFee


# normal yield assets


@internal
def _handleNormalYieldAsset(
    _asset: address,
    _currentBalance: uint256,
    _lastBalance: uint256,
    _lastYieldPrice: uint256,
    _config: ProfitCalcConfig,
) -> (uint256, uint256, uint256):
    currentPricePerShare: uint256 = self._updateAndGetPricePerShare(_asset, _config.legoAddr, _config.staleBlocks)

    # first time saving it, no profits
    if _lastYieldPrice == 0:
        return currentPricePerShare, 0, 0

    # nothing to do if price hasn't changed or increased
    if currentPricePerShare == 0 or currentPricePerShare <= _lastYieldPrice:
        return 0, 0, 0
    
    # calculate underlying amounts
    trackedBalance: uint256 = min(_currentBalance, _lastBalance)
    prevUnderlyingAmount: uint256 = trackedBalance * _lastYieldPrice // (10 ** _config.decimals)
    currentUnderlyingAmount: uint256 = trackedBalance * currentPricePerShare // (10 ** _config.decimals)
    
    # apply max yield increase cap if configured (in underlying terms)
    if _config.maxYieldIncrease != 0:
        maxAllowedUnderlying: uint256 = prevUnderlyingAmount + (prevUnderlyingAmount * _config.maxYieldIncrease // HUNDRED_PERCENT)
        currentUnderlyingAmount = min(currentUnderlyingAmount, maxAllowedUnderlying)

    # calculate profit in underlying tokens
    profitInUnderlying: uint256 = currentUnderlyingAmount - prevUnderlyingAmount
    profitInVaultTokens: uint256 = profitInUnderlying * (10 ** _config.decimals) // currentPricePerShare
    
    return currentPricePerShare, profitInVaultTokens, _config.yieldProfitFee


# utils


@view
@internal
def _getProfitCalcConfig(_asset: address, _missionControl: address, _legoBook: address) -> ProfitCalcConfig:
    config: ProfitCalcConfig = staticcall MissionControl(_missionControl).getProfitCalcConfig(_asset)

    # get lego addr if needed
    if config.legoId != 0 and config.legoAddr == empty(address):
        config.legoAddr = staticcall Registry(_legoBook).getAddr(config.legoId)

    # get decimals if needed
    if config.decimals == 0:
        config.decimals = self._getDecimals(_asset)

    return config


######################
# Prices - USD Value #
######################


# get usd value


@view
@external
def getUsdValue(_asset: address, _amount: uint256) -> uint256:
    hq: address = addys._getUndyHq()
    config: AssetUsdValueConfig = self._getAssetUsdValueConfig(_asset, hq)

    # normal price
    price: uint256 = 0
    if not config.isYieldAsset:
        price = self._getNormalAssetPrice(_asset, config.legoAddr, config.staleBlocks)

    # yield price
    else:
        pricePerShare: uint256 = self._getPricePerShare(_asset, config.legoAddr, config.staleBlocks)

        # for yield assets, need to check if it has underlying asset
        if config.underlyingAsset != empty(address):
            underlyingConfig: AssetUsdValueConfig = self._getAssetUsdValueConfig(config.underlyingAsset, hq)
            underlyingPrice: uint256 = self._getNormalAssetPrice(config.underlyingAsset, underlyingConfig.legoAddr, underlyingConfig.staleBlocks)
            price = underlyingPrice * pricePerShare // (10 ** underlyingConfig.decimals)
        else:
            price = pricePerShare

    # finalize value
    usdValue: uint256 = price * _amount // (10 ** config.decimals)

    return usdValue


# update prices (and get usd value)


@external
def updatePriceAndGetUsdValue(_asset: address, _amount: uint256) -> uint256:
    hq: address = addys._getUndyHq()
    if not self._isCallerUserWallet(msg.sender, hq):
        assert addys._isValidUndyAddr(msg.sender, hq) # dev: no perms
    usdValue: uint256 = 0
    na: bool = False
    usdValue, na = self._updatePriceAndGetUsdValue(_asset, _amount, hq)
    return usdValue


@external
def updatePriceAndGetUsdValueAndIsYieldAsset(_asset: address, _amount: uint256) -> (uint256, bool):
    hq: address = addys._getUndyHq()
    if not self._isCallerUserWallet(msg.sender, hq):
        assert addys._isValidUndyAddr(msg.sender, hq) # dev: no perms
    return self._updatePriceAndGetUsdValue(_asset, _amount, hq)


@internal
def _updatePriceAndGetUsdValue(_asset: address, _amount: uint256, _hq: address) -> (uint256, bool):
    config: AssetUsdValueConfig = self._getAssetUsdValueConfig(_asset, _hq)

    # normal price
    price: uint256 = 0
    if not config.isYieldAsset:
        price = self._updateAndGetNormalAssetPrice(_asset, config.legoAddr, config.staleBlocks)

    # yield price
    else:
        pricePerShare: uint256 = self._updateAndGetPricePerShare(_asset, config.legoAddr, config.staleBlocks)

        # for yield assets, need to check if it has underlying asset
        if config.underlyingAsset != empty(address):
            underlyingConfig: AssetUsdValueConfig = self._getAssetUsdValueConfig(config.underlyingAsset, _hq)
            underlyingPrice: uint256 = self._updateAndGetNormalAssetPrice(config.underlyingAsset, underlyingConfig.legoAddr, underlyingConfig.staleBlocks)
            price = underlyingPrice * pricePerShare // (10 ** underlyingConfig.decimals)
        else:
            price = pricePerShare

    # finalize value
    usdValue: uint256 = price * _amount // (10 ** config.decimals)

    return usdValue, config.isYieldAsset


########################
# Normal Asset - Price #
########################


# get price


@view
@external
def getNormalAssetPrice(_asset: address) -> uint256:
    hq: address = addys._getUndyHq()
    config: AssetUsdValueConfig = self._getAssetUsdValueConfig(_asset, hq)
    if config.isYieldAsset:
        return 0
    return self._getNormalAssetPrice(_asset, config.legoAddr, config.staleBlocks)


@view
@internal
def _getNormalAssetPrice(
    _asset: address,
    _legoAddr: address,
    _staleBlocks: uint256,
) -> uint256:
    data: LastPrice = empty(LastPrice)
    na: bool = False
    data, na = self._getNormalAssetPriceAndDidUpdate(_asset, _legoAddr, _staleBlocks)
    return data.price


@view
@internal
def _getNormalAssetPriceAndDidUpdate(
    _asset: address,
    _legoAddr: address,
    _staleBlocks: uint256,
) -> (LastPrice, bool):
    data: LastPrice = self.lastPrice[_asset]

    # same block, return cached price
    if data.lastUpdate == block.number:
        return data, False

    # check if recent price is good enough
    if _staleBlocks != 0 and data.lastUpdate + _staleBlocks > block.number:
        return data, False

    prevPrice: uint256 = data.price

    # first, check with Lego
    if _legoAddr != empty(address):
        data.price = staticcall Lego(_legoAddr).getPrice(_asset)

    # back up plan, check with Ripe
    if data.price == 0:
        data.price = self._getRipePrice(_asset)

    # check if changed
    didPriceChange: bool = False
    if data.price != prevPrice:
        didPriceChange = True

    data.lastUpdate = block.number
    return data, didPriceChange


# update and get price


@external
def updateAndGetNormalAssetPrice(_asset: address) -> uint256:
    hq: address = addys._getUndyHq()
    if not self._isCallerUserWallet(msg.sender, hq):
        assert addys._isValidUndyAddr(msg.sender, hq) # dev: no perms
    config: AssetUsdValueConfig = self._getAssetUsdValueConfig(_asset, hq)
    if config.isYieldAsset:
        return 0
    return self._updateAndGetNormalAssetPrice(_asset, config.legoAddr, config.staleBlocks)


@internal
def _updateAndGetNormalAssetPrice(
    _asset: address,
    _legoAddr: address,
    _staleBlocks: uint256,
) -> uint256:
    data: LastPrice = empty(LastPrice)
    didPriceChange: bool = False
    data, didPriceChange = self._getNormalAssetPriceAndDidUpdate(_asset, _legoAddr, _staleBlocks)
    if didPriceChange:
        self.lastPrice[_asset] = data
    return data.price


#################################
# Yield Asset - Price Per Share #
#################################


# get price per share


@view
@external
def getPricePerShare(_asset: address) -> uint256:
    hq: address = addys._getUndyHq()
    config: AssetUsdValueConfig = self._getAssetUsdValueConfig(_asset, hq)
    if not config.isYieldAsset:
        return 0
    return self._getPricePerShare(_asset, config.legoAddr, config.staleBlocks)


@view
@external
def getPricePerShareWithConfig(
    _asset: address,
    _legoAddr: address,
    _staleBlocks: uint256,
) -> uint256:
    return self._getPricePerShare(_asset, _legoAddr, _staleBlocks)


@view
@internal
def _getPricePerShare(
    _asset: address,
    _legoAddr: address,
    _staleBlocks: uint256,
) -> uint256:
    data: LastPricePerShare = empty(LastPricePerShare)
    na: bool = False
    data, na = self._getPricePerShareAndDidUpdate(_asset, _legoAddr, _staleBlocks)
    return data.pricePerShare


@view
@internal
def _getPricePerShareAndDidUpdate(
    _asset: address,
    _legoAddr: address,
    _staleBlocks: uint256,
) -> (LastPricePerShare, bool):
    data: LastPricePerShare = self.lastPricePerShare[_asset]

    # same block, return cached pricePerShare
    if data.lastUpdate == block.number:
        return data, False

    # check if recent pricePerShare is good enough
    if _staleBlocks != 0 and data.lastUpdate + _staleBlocks > block.number:
        return data, False

    prevPricePerShare: uint256 = data.pricePerShare

    # first, check with Lego
    if _legoAddr != empty(address):
        data.pricePerShare = staticcall Lego(_legoAddr).getPricePerShare(_asset)
    
    # back up plan, check with Ripe
    if data.pricePerShare == 0:
        data.pricePerShare = self._getRipePrice(_asset)

    # check if changed
    didPriceChange: bool = False
    if data.pricePerShare != prevPricePerShare:
        didPriceChange = True

    data.lastUpdate = block.number
    return data, didPriceChange


# update and get price per share


@external
def updateAndGetPricePerShare(_asset: address) -> uint256:
    hq: address = addys._getUndyHq()
    if not self._isCallerUserWallet(msg.sender, hq):
        assert addys._isValidUndyAddr(msg.sender, hq) # dev: no perms
    config: AssetUsdValueConfig = self._getAssetUsdValueConfig(_asset, hq)
    if not config.isYieldAsset:
        return 0
    return self._updateAndGetPricePerShare(_asset, config.legoAddr, config.staleBlocks)


@internal
def _updateAndGetPricePerShare(
    _asset: address,
    _legoAddr: address,
    _staleBlocks: uint256,
) -> uint256:
    data: LastPricePerShare = empty(LastPricePerShare)
    didPriceChange: bool = False
    data, didPriceChange = self._getPricePerShareAndDidUpdate(_asset, _legoAddr, _staleBlocks)
    if didPriceChange:
        self.lastPricePerShare[_asset] = data
    return data.pricePerShare


####################
# Ripe Integration #
####################


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


#########
# Utils #
#########


# get asset usd value config


@view
@external
def getAssetUsdValueConfig(_asset: address) -> AssetUsdValueConfig:
    hq: address = addys._getUndyHq()
    return self._getAssetUsdValueConfig(_asset, hq)


@view
@internal
def _getAssetUsdValueConfig(_asset: address, _hq: address) -> AssetUsdValueConfig:
    missionControl: address = staticcall Registry(_hq).getAddr(MISSION_CONTROL_ID)
    config: AssetUsdValueConfig = staticcall MissionControl(missionControl).getAssetUsdValueConfig(_asset)

    # get lego addr if needed
    if config.legoId != 0 and config.legoAddr == empty(address):
        legoBook: address = staticcall Registry(_hq).getAddr(LEGO_BOOK_ID)
        config.legoAddr = staticcall Registry(legoBook).getAddr(config.legoId)

    # get decimals if needed
    if config.decimals == 0:
        config.decimals = self._getDecimals(_asset)

    return config


# get decimals


@view
@internal
def _getDecimals(_asset: address) -> uint256:
    if _asset in [WETH, ETH]:
        return 18
    return convert(staticcall IERC20Detailed(_asset).decimals(), uint256)


# is user wallet


@view
@external
def isCallerUserWallet(_caller: address) -> bool:
    hq: address = addys._getUndyHq()
    return self._isCallerUserWallet(_caller, hq)


@view
@internal
def _isCallerUserWallet(_caller: address, _hq: address) -> bool:
    ledger: address = staticcall Registry(_hq).getAddr(LEDGER_ID)
    return staticcall Ledger(ledger).isUserWallet(_caller)
