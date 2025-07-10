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

interface Ledger:
    def vaultTokens(_vaultToken: address) -> VaultToken: view
    def isUserWallet(_user: address) -> bool: view

interface RipePriceDesk:
    def getPrice(_asset: address, _shouldRaise: bool = False) -> uint256: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

struct LastPrice:
    price: uint256
    lastUpdate: uint256

struct LastPricePerShare:
    pricePerShare: uint256
    lastUpdate: uint256

struct VaultToken:
    legoId: uint256
    underlyingAsset: address
    decimals: uint256
    isRebasing: bool

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
    performanceFee: uint256

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
    ledger: address = addys._getLedgerAddr() # cannot allow this to be passed in as param
    assert staticcall Ledger(ledger).isUserWallet(msg.sender) # dev: no perms

    config: ProfitCalcConfig = self._getProfitCalcConfig(_asset, _missionControl, _legoBook, ledger)
    if not config.isYieldAsset:
        return 0, 0, 0

    if config.isRebasing:
        return self._handleRebaseYieldAsset(_currentBalance, _assetBalance, config.maxYieldIncrease, config.performanceFee)
    else:
        currentPricePerShare: uint256 = self._updateAndGetPricePerShare(_asset, config.legoAddr, config.staleBlocks, config.decimals)
        return self._handleNormalYieldAsset(_currentBalance, _assetBalance, _lastYieldPrice, currentPricePerShare, config)


@view
@external
def calculateYieldProfitsNoUpdate(
    _legoId: uint256,
    _asset: address,
    _underlyingAsset: address,
    _currentBalance: uint256,
    _assetBalance: uint256,
    _lastYieldPrice: uint256,
) -> (uint256, uint256, uint256):
    config: ProfitCalcConfig = self._getProfitCalcConfig(_asset, addys._getMissionControlAddr(), addys._getLegoBookAddr(), addys._getLedgerAddr())
    if not config.isYieldAsset:
        return 0, 0, 0

    if config.isRebasing:
        return self._handleRebaseYieldAsset(_currentBalance, _assetBalance, config.maxYieldIncrease, config.performanceFee)
    else:
        currentPricePerShare: uint256 = self._getPricePerShare(_asset, config.legoAddr, config.staleBlocks, config.decimals)
        return self._handleNormalYieldAsset(_currentBalance, _assetBalance, _lastYieldPrice, currentPricePerShare, config)
    

# rebasing assets


@view
@internal
def _handleRebaseYieldAsset(
    _currentBalance: uint256,
    _lastBalance: uint256,
    _maxYieldIncrease: uint256,
    _performanceFee: uint256,
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
    
    return 0, actualProfit, _performanceFee


# normal yield assets


@view
@internal
def _handleNormalYieldAsset(
    _currentBalance: uint256,
    _lastBalance: uint256,
    _lastYieldPrice: uint256,
    _currentPricePerShare: uint256,
    _config: ProfitCalcConfig,
) -> (uint256, uint256, uint256):

    # first time saving it, no profits
    if _lastYieldPrice == 0:
        return _currentPricePerShare, 0, 0

    # nothing to do if price hasn't changed or increased
    if _currentPricePerShare == 0 or _currentPricePerShare <= _lastYieldPrice:
        return 0, 0, 0
    
    # calculate underlying amounts
    trackedBalance: uint256 = min(_currentBalance, _lastBalance)
    prevUnderlyingAmount: uint256 = trackedBalance * _lastYieldPrice // (10 ** _config.decimals)
    currentUnderlyingAmount: uint256 = trackedBalance * _currentPricePerShare // (10 ** _config.decimals)
    
    # apply max yield increase cap if configured (in underlying terms)
    if _config.maxYieldIncrease != 0:
        maxAllowedUnderlying: uint256 = prevUnderlyingAmount + (prevUnderlyingAmount * _config.maxYieldIncrease // HUNDRED_PERCENT)
        currentUnderlyingAmount = min(currentUnderlyingAmount, maxAllowedUnderlying)

    # calculate profit in underlying tokens
    profitInUnderlying: uint256 = currentUnderlyingAmount - prevUnderlyingAmount
    profitInVaultTokens: uint256 = profitInUnderlying * (10 ** _config.decimals) // _currentPricePerShare
    
    return _currentPricePerShare, profitInVaultTokens, _config.performanceFee


# utils


@view
@internal
def _getProfitCalcConfig(
    _asset: address,
    _missionControl: address,
    _legoBook: address,
    _ledger: address,
) -> ProfitCalcConfig:
    config: ProfitCalcConfig = staticcall MissionControl(_missionControl).getProfitCalcConfig(_asset)

    # if no specific config, fallback to vault token registration
    if config.decimals == 0:
        vaultToken: VaultToken = staticcall Ledger(_ledger).vaultTokens(_asset)
        if vaultToken.underlyingAsset != empty(address):
            config.legoId = vaultToken.legoId
            config.decimals = vaultToken.decimals
            config.isYieldAsset = True
            config.isRebasing = vaultToken.isRebasing
            config.underlyingAsset = vaultToken.underlyingAsset

    # get lego addr if needed
    if config.legoId != 0 and config.legoAddr == empty(address):
        config.legoAddr = staticcall Registry(_legoBook).getAddr(config.legoId)

    # get decimals if needed
    if config.isYieldAsset and config.decimals == 0:
        config.decimals = self._getDecimals(_asset)

    return config


######################
# Prices - USD Value #
######################


# get usd value


@view
@external
def getUsdValue(
    _asset: address,
    _amount: uint256,
    _missionControl: address = empty(address),
    _legoBook: address = empty(address),
    _ledger: address = empty(address),
) -> uint256:

    # get addresses if not provided
    missionControl: address = _missionControl
    if _missionControl == empty(address):
        missionControl = addys._getMissionControlAddr()
    legoBook: address = _legoBook
    if _legoBook == empty(address):
        legoBook = addys._getLegoBookAddr()
    ledger: address = _ledger
    if _ledger == empty(address):
        ledger = addys._getLedgerAddr()

    # config
    config: AssetUsdValueConfig = self._getAssetUsdValueConfig(_asset, missionControl, legoBook, ledger)

    # normal price
    price: uint256 = 0
    if not config.isYieldAsset:
        price = self._getNormalAssetPrice(_asset, config.legoAddr, config.staleBlocks, config.decimals)

    # yield price
    else:
        pricePerShare: uint256 = self._getPricePerShare(_asset, config.legoAddr, config.staleBlocks, config.decimals)

        # for yield assets, need to check if it has underlying asset
        if config.underlyingAsset != empty(address):
            underlyingConfig: AssetUsdValueConfig = self._getAssetUsdValueConfig(config.underlyingAsset, missionControl, legoBook, ledger)
            underlyingPrice: uint256 = self._getNormalAssetPrice(config.underlyingAsset, underlyingConfig.legoAddr, underlyingConfig.staleBlocks, underlyingConfig.decimals)
            price = underlyingPrice * pricePerShare // (10 ** underlyingConfig.decimals)
        else:
            price = pricePerShare

    usdValue: uint256 = price * _amount // (10 ** config.decimals)
    return usdValue


# update prices (and get usd value)


@external
def updatePriceAndGetUsdValue(
    _asset: address,
    _amount: uint256,
    _missionControl: address = empty(address),
    _legoBook: address = empty(address),
) -> uint256:
    ledger: address = addys._getLedgerAddr() # cannot allow this to be passed in as param
    if not staticcall Ledger(ledger).isUserWallet(msg.sender):
        assert addys._isValidUndyAddr(msg.sender) # dev: no perms

    usdValue: uint256 = 0
    na: bool = False
    usdValue, na = self._updatePriceAndGetUsdValue(_asset, _amount, _missionControl, _legoBook, ledger)
    return usdValue


@external
def updatePriceAndGetUsdValueAndIsYieldAsset(
    _asset: address,
    _amount: uint256,
    _missionControl: address = empty(address),
    _legoBook: address = empty(address),
) -> (uint256, bool):
    ledger: address = addys._getLedgerAddr() # cannot allow this to be passed in as param
    if not staticcall Ledger(ledger).isUserWallet(msg.sender):
        assert addys._isValidUndyAddr(msg.sender) # dev: no perms
    return self._updatePriceAndGetUsdValue(_asset, _amount, _missionControl, _legoBook, ledger)


@internal
def _updatePriceAndGetUsdValue(
    _asset: address,
    _amount: uint256,
    _missionControl: address,
    _legoBook: address,
    _ledger: address,
) -> (uint256, bool):

    # get addresses if not provided
    missionControl: address = _missionControl
    if _missionControl == empty(address):
        missionControl = addys._getMissionControlAddr()
    legoBook: address = _legoBook
    if _legoBook == empty(address):
        legoBook = addys._getLegoBookAddr()
    ledger: address = _ledger
    if _ledger == empty(address):
        ledger = addys._getLedgerAddr()

    # config
    config: AssetUsdValueConfig = self._getAssetUsdValueConfig(_asset, missionControl, legoBook, ledger)

    # normal price
    price: uint256 = 0
    if not config.isYieldAsset:
        price = self._updateAndGetNormalAssetPrice(_asset, config.legoAddr, config.staleBlocks, config.decimals)

    # yield price
    else:
        pricePerShare: uint256 = self._updateAndGetPricePerShare(_asset, config.legoAddr, config.staleBlocks, config.decimals)

        # for yield assets, need to check if it has underlying asset
        if config.underlyingAsset != empty(address):
            underlyingConfig: AssetUsdValueConfig = self._getAssetUsdValueConfig(config.underlyingAsset, missionControl, legoBook, ledger)
            underlyingPrice: uint256 = self._updateAndGetNormalAssetPrice(config.underlyingAsset, underlyingConfig.legoAddr, underlyingConfig.staleBlocks, underlyingConfig.decimals)
            price = underlyingPrice * pricePerShare // (10 ** underlyingConfig.decimals)
        else:
            price = pricePerShare

    usdValue: uint256 = price * _amount // (10 ** config.decimals)
    return usdValue, config.isYieldAsset


########################
# Normal Asset - Price #
########################


# get price


@view
@external
def getNormalAssetPrice(
    _asset: address,
    _missionControl: address = empty(address),
    _legoBook: address = empty(address),
    _ledger: address = empty(address),
) -> uint256:

    # get addresses if not provided
    missionControl: address = _missionControl
    if _missionControl == empty(address):
        missionControl = addys._getMissionControlAddr()
    legoBook: address = _legoBook
    if _legoBook == empty(address):
        legoBook = addys._getLegoBookAddr()
    ledger: address = _ledger
    if _ledger == empty(address):
        ledger = addys._getLedgerAddr()

    config: AssetUsdValueConfig = self._getAssetUsdValueConfig(_asset, missionControl, legoBook, ledger)
    if config.isYieldAsset:
        return 0 # cannot get yield price here
    return self._getNormalAssetPrice(_asset, config.legoAddr, config.staleBlocks, config.decimals)


@view
@internal
def _getNormalAssetPrice(
    _asset: address,
    _legoAddr: address,
    _staleBlocks: uint256,
    _decimals: uint256,
) -> uint256:
    data: LastPrice = empty(LastPrice)
    na: bool = False
    data, na = self._getNormalAssetPriceAndDidUpdate(_asset, _legoAddr, _staleBlocks, _decimals)
    return data.price


@view
@internal
def _getNormalAssetPriceAndDidUpdate(
    _asset: address,
    _legoAddr: address,
    _staleBlocks: uint256,
    _decimals: uint256,
) -> (LastPrice, bool):
    data: LastPrice = self.lastPrice[_asset]

    # same block, return cached price
    if data.lastUpdate == block.number:
        return data, False

    # check if recent price is good enough
    if _staleBlocks != 0 and data.lastUpdate != 0:
        if data.lastUpdate + _staleBlocks > block.number:
            return data, False

    prevPrice: uint256 = data.price

    # first, check with Ripe
    data.price = self._getRipePrice(_asset)

    # back up plan, check with Lego
    if data.price == 0 and _legoAddr != empty(address):
        data.price = staticcall Lego(_legoAddr).getPrice(_asset, _decimals)

    # check if changed
    didPriceChange: bool = False
    if data.price != prevPrice:
        didPriceChange = True

    data.lastUpdate = block.number
    return data, didPriceChange


# update and get price


@external
def updateAndGetNormalAssetPrice(
    _asset: address,
    _missionControl: address = empty(address),
    _legoBook: address = empty(address),
) -> uint256:
    ledger: address = addys._getLedgerAddr() # cannot allow this to be passed in as param
    if not staticcall Ledger(ledger).isUserWallet(msg.sender):
        assert addys._isValidUndyAddr(msg.sender) # dev: no perms

    # get addresses if not provided
    missionControl: address = _missionControl
    if _missionControl == empty(address):
        missionControl = addys._getMissionControlAddr()
    legoBook: address = _legoBook
    if _legoBook == empty(address):
        legoBook = addys._getLegoBookAddr()

    config: AssetUsdValueConfig = self._getAssetUsdValueConfig(_asset, missionControl, legoBook, ledger)
    if config.isYieldAsset:
        return 0 # cannot get yield price here
    return self._updateAndGetNormalAssetPrice(_asset, config.legoAddr, config.staleBlocks, config.decimals)


@internal
def _updateAndGetNormalAssetPrice(
    _asset: address,
    _legoAddr: address,
    _staleBlocks: uint256,
    _decimals: uint256,
) -> uint256:
    data: LastPrice = empty(LastPrice)
    didPriceChange: bool = False
    data, didPriceChange = self._getNormalAssetPriceAndDidUpdate(_asset, _legoAddr, _staleBlocks, _decimals)
    if didPriceChange:
        self.lastPrice[_asset] = data
    return data.price


#################################
# Yield Asset - Price Per Share #
#################################


# get price per share


@view
@external
def getPricePerShare(
    _asset: address,
    _missionControl: address = empty(address),
    _legoBook: address = empty(address),
    _ledger: address = empty(address),
) -> uint256:

    # get addresses if not provided
    missionControl: address = _missionControl
    if _missionControl == empty(address):
        missionControl = addys._getMissionControlAddr()
    legoBook: address = _legoBook
    if _legoBook == empty(address):
        legoBook = addys._getLegoBookAddr()
    ledger: address = _ledger
    if _ledger == empty(address):
        ledger = addys._getLedgerAddr()

    config: AssetUsdValueConfig = self._getAssetUsdValueConfig(_asset, missionControl, legoBook, ledger)
    return self._getPricePerShare(_asset, config.legoAddr, config.staleBlocks, config.decimals)


@view
@external
def getPricePerShareWithConfig(
    _asset: address,
    _legoAddr: address,
    _staleBlocks: uint256,
    _decimals: uint256,
) -> uint256:
    return self._getPricePerShare(_asset, _legoAddr, _staleBlocks, _decimals)


@view
@internal
def _getPricePerShare(
    _asset: address,
    _legoAddr: address,
    _staleBlocks: uint256,
    _decimals: uint256,
) -> uint256:
    data: LastPricePerShare = empty(LastPricePerShare)
    na: bool = False
    data, na = self._getPricePerShareAndDidUpdate(_asset, _legoAddr, _staleBlocks, _decimals)
    return data.pricePerShare


@view
@internal
def _getPricePerShareAndDidUpdate(
    _asset: address,
    _legoAddr: address,
    _staleBlocks: uint256,
    _decimals: uint256,
) -> (LastPricePerShare, bool):
    data: LastPricePerShare = self.lastPricePerShare[_asset]

    # same block, return cached pricePerShare
    if data.lastUpdate == block.number:
        return data, False

    # check if recent pricePerShare is good enough
    if _staleBlocks != 0 and data.lastUpdate != 0:
        if data.lastUpdate + _staleBlocks > block.number:
            return data, False

    prevPricePerShare: uint256 = data.pricePerShare

    # first, check with Lego
    if _legoAddr != empty(address):
        decimals: uint256 = self._getDecimals(_asset)
        data.pricePerShare = staticcall Lego(_legoAddr).getPricePerShare(_asset, decimals)
    
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
def updateAndGetPricePerShare(
    _asset: address,
    _missionControl: address = empty(address),
    _legoBook: address = empty(address),
) -> uint256:
    ledger: address = addys._getLedgerAddr() # cannot allow this to be passed in as param
    if not staticcall Ledger(ledger).isUserWallet(msg.sender):
        assert addys._isValidUndyAddr(msg.sender) # dev: no perms

    # get addresses if not provided
    missionControl: address = _missionControl
    if _missionControl == empty(address):
        missionControl = addys._getMissionControlAddr()
    legoBook: address = _legoBook
    if _legoBook == empty(address):
        legoBook = addys._getLegoBookAddr()

    config: AssetUsdValueConfig = self._getAssetUsdValueConfig(_asset, missionControl, legoBook, ledger)
    if not config.isYieldAsset:
        return 0 # cannot get normal price here
    return self._updateAndGetPricePerShare(_asset, config.legoAddr, config.staleBlocks, config.decimals)


@internal
def _updateAndGetPricePerShare(
    _asset: address,
    _legoAddr: address,
    _staleBlocks: uint256,
    _decimals: uint256,
) -> uint256:
    data: LastPricePerShare = empty(LastPricePerShare)
    didPriceChange: bool = False
    data, didPriceChange = self._getPricePerShareAndDidUpdate(_asset, _legoAddr, _staleBlocks, _decimals)
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
    return self._getAssetUsdValueConfig(_asset, addys._getMissionControlAddr(), addys._getLegoBookAddr(), addys._getLedgerAddr())


@view
@internal
def _getAssetUsdValueConfig(
    _asset: address,
    _missionControl: address,
    _legoBook: address,
    _ledger: address,
) -> AssetUsdValueConfig:
    config: AssetUsdValueConfig = staticcall MissionControl(_missionControl).getAssetUsdValueConfig(_asset)

    # if no specific config, fallback to vault token registration
    if config.decimals == 0:
        vaultToken: VaultToken = staticcall Ledger(_ledger).vaultTokens(_asset)
        if vaultToken.underlyingAsset != empty(address):
            config.legoId = vaultToken.legoId
            config.decimals = vaultToken.decimals
            config.isYieldAsset = True
            config.underlyingAsset = vaultToken.underlyingAsset

    # get lego addr if needed
    if config.legoId != 0 and config.legoAddr == empty(address):
        config.legoAddr = staticcall Registry(_legoBook).getAddr(config.legoId)

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
