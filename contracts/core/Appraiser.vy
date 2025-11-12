#     ________   ______   ______   ______    ________    ________  ______   ______   ______       
#    /_______/\ /_____/\ /_____/\ /_____/\  /_______/\  /_______/\/_____/\ /_____/\ /_____/\      
#    \::: _  \ \\:::_ \ \\:::_ \ \\:::_ \ \ \::: _  \ \ \__.::._\/\::::_\/_\::::_\/_\:::_ \ \     
#     \::(_)  \ \\:(_) \ \\:(_) \ \\:(_) ) )_\::(_)  \ \   \::\ \  \:\/___/\\:\/___/\\:(_) ) )_   
#      \:: __  \ \\: ___\/ \: ___\/ \: __ `\ \\:: __  \ \  _\::\ \__\_::._\:\\::___\/_\: __ `\ \  
#       \:.\ \  \ \\ \ \    \ \ \    \ \ `\ \ \\:.\ \  \ \/__\::\__/\ /____\:\\:\____/\\ \ `\ \ \ 
#        \__\/\__\/ \_\/     \_\/     \_\/ \_\/ \__\/\__\/\________\/ \_____\/ \_____\/ \_\/ \_\/ 
#
#     ╔════════════════════════════════════════════════╗
#     ║  ** Appraiser **                               ║
#     ║  Handles price calculations for the protocol.  ║
#     ╚════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

implements: Department

exports: addys.__interface__
exports: deptBasics.__interface__

initializes: addys
initializes: deptBasics[addys := addys]

import contracts.modules.Addys as addys
import contracts.modules.DeptBasics as deptBasics
from interfaces import Department
from interfaces import DexLego as DexLego
from interfaces import YieldLego as YieldLego

from ethereum.ercs import IERC20Detailed

interface RipePriceDesk:
    def getAssetAmount(_asset: address, _usdValue: uint256, _shouldRaise: bool = False) -> uint256: view
    def getUsdValue(_asset: address, _amount: uint256, _shouldRaise: bool = False) -> uint256: view
    def getPrice(_asset: address, _shouldRaise: bool = False) -> uint256: view
    def addPriceSnapshot(_asset: address) -> bool: nonpayable

interface Ledger:
    def isRegisteredBackpackItem(_user: address) -> bool: view
    def vaultTokens(_vaultToken: address) -> VaultToken: view
    def isUserWallet(_user: address) -> bool: view

interface MissionControl:
    def getAssetUsdValueConfig(_asset: address) -> AssetUsdValueConfig: view
    def getProfitCalcConfig(_asset: address) -> ProfitCalcConfig: view

interface VaultRegistry:
    def isEarnVault(_vaultAddr: address) -> bool: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

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

HUNDRED_PERCENT: constant(uint256) = 100_00 # 100.00%

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
    _lastBalance: uint256,
    _lastPricePerShare: uint256,
    _missionControl: address,
    _legoBook: address,
) -> (uint256, uint256, uint256):
    ledger: address = addys._getLedgerAddr() # cannot allow this to be passed in as param
    assert staticcall Ledger(ledger).isUserWallet(msg.sender) # dev: no perms

    # if paused, fail gracefully
    if deptBasics.isPaused:
        return 0, 0, 0

    # get addresses if not provided
    missionControl: address = _missionControl
    if _missionControl == empty(address):
        missionControl = addys._getMissionControlAddr()
    legoBook: address = _legoBook
    if _legoBook == empty(address):
        legoBook = addys._getLegoBookAddr()

    config: ProfitCalcConfig = self._getProfitCalcConfig(_asset, missionControl, legoBook, ledger)
    if not config.isYieldAsset:
        return 0, 0, 0

    if config.isRebasing:
        return self._handleRebaseYieldAsset(_currentBalance, _lastBalance, config.maxYieldIncrease, config.performanceFee)
    else:
        currentPricePerShare: uint256 = staticcall YieldLego(config.legoAddr).getPricePerShare(_asset, config.decimals)
        return self._handleNormalYieldAsset(_currentBalance, _lastBalance, _lastPricePerShare, currentPricePerShare, config)


@view
@external
def calculateYieldProfitsNoUpdate(
    _legoId: uint256,
    _asset: address,
    _underlyingAsset: address,
    _currentBalance: uint256,
    _lastBalance: uint256,
    _lastPricePerShare: uint256,
) -> (uint256, uint256, uint256):
    config: ProfitCalcConfig = self._getProfitCalcConfig(_asset, addys._getMissionControlAddr(), addys._getLegoBookAddr(), addys._getLedgerAddr())
    if not config.isYieldAsset:
        return 0, 0, 0

    if config.isRebasing:
        return self._handleRebaseYieldAsset(_currentBalance, _lastBalance, config.maxYieldIncrease, config.performanceFee)
    else:
        currentPricePerShare: uint256 = staticcall YieldLego(config.legoAddr).getPricePerShare(_asset, config.decimals)
        return self._handleNormalYieldAsset(_currentBalance, _lastBalance, _lastPricePerShare, currentPricePerShare, config)
    

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
    if _lastBalance == 0 or _currentBalance <= _lastBalance:
        return 0, 0, 0
    
    # calculate the actual profit
    uncappedProfit: uint256 = _currentBalance - _lastBalance
    actualProfit: uint256 = uncappedProfit
    
    # apply max yield increase cap if configured
    if _maxYieldIncrease != 0:
        maxAllowedProfit: uint256 = _lastBalance * _maxYieldIncrease // HUNDRED_PERCENT
        actualProfit = min(uncappedProfit, maxAllowedProfit)
    
    return 0, actualProfit, _performanceFee


# normal yield assets


@view
@internal
def _handleNormalYieldAsset(
    _currentBalance: uint256,
    _lastBalance: uint256,
    _lastPricePerShare: uint256,
    _currentPricePerShare: uint256,
    _config: ProfitCalcConfig,
) -> (uint256, uint256, uint256):

    # first time saving it, no profits
    if _lastPricePerShare == 0:
        return _currentPricePerShare, 0, 0

    # nothing to do if price decreased or stayed the same
    if _currentPricePerShare == 0 or _currentPricePerShare <= _lastPricePerShare:
        return 0, 0, 0
    
    trackedBalance: uint256 = min(_currentBalance, _lastBalance)

    # calculate underlying amounts
    prevUnderlyingAmount: uint256 = trackedBalance * _lastPricePerShare // (10 ** _config.decimals)
    currentUnderlyingAmount: uint256 = trackedBalance * _currentPricePerShare // (10 ** _config.decimals)
    
    # calculate profit in underlying tokens
    profitInUnderlying: uint256 = currentUnderlyingAmount - prevUnderlyingAmount
    
    # apply max yield increase cap if configured
    if _config.maxYieldIncrease != 0:
        maxProfit: uint256 = prevUnderlyingAmount * _config.maxYieldIncrease // HUNDRED_PERCENT
        profitInUnderlying = min(profitInUnderlying, maxProfit)

    profitInVaultTokens: uint256 = profitInUnderlying * (10 ** _config.decimals) // _currentPricePerShare   
    return _currentPricePerShare, profitInVaultTokens, _config.performanceFee


# last price per share


@view
@external
def lastPricePerShare(_asset: address) -> uint256:
    a: addys.Addys = addys._getAddys()
    config: AssetUsdValueConfig = self._getAssetUsdValueConfig(_asset, a.missionControl, a.legoBook, a.ledger)
    if not config.isYieldAsset or config.legoAddr == empty(address):
        return 0
    return staticcall YieldLego(config.legoAddr).getPricePerShare(_asset, config.decimals)


#############
# USD Value #
#############


@view
@external
def getUsdValue(_asset: address, _amount: uint256, _missionControl: address = empty(address), _legoBook: address = empty(address), _ledger: address = empty(address)) -> uint256:
    return self._getUsdValueAndIsYieldAsset(_asset, _amount, _ledger, _missionControl, _legoBook)[0]


@view
@external
def getUnderlyingUsdValue(_asset: address, _amount: uint256) -> uint256:
    return self._getUnderlyingUsdValueFromRipe(_asset, _amount)[0]


# called from wallet


@external
def updatePriceAndGetUsdValue(
    _asset: address,
    _amount: uint256,
    _missionControl: address = empty(address),
    _legoBook: address = empty(address),
) -> uint256:
    ledger: address = addys._getLedgerAddr() # cannot allow this to be passed in as param
    if not staticcall Ledger(ledger).isUserWallet(msg.sender) and not addys._isValidUndyAddr(msg.sender):
        assert staticcall Ledger(ledger).isRegisteredBackpackItem(msg.sender) # dev: no perms

    # get usd value
    usdValue: uint256 = 0
    na: bool = False
    ripePriceDesk: address = empty(address)
    usdValue, na, ripePriceDesk = self._getUsdValueAndIsYieldAsset(_asset, _amount, ledger, _missionControl, _legoBook)

    # add snapshot to Ripe if earn vault
    if staticcall VaultRegistry(addys._getVaultRegistryAddr()).isEarnVault(_asset):
        self._updateRipeSnapshot(_asset)

    return usdValue


@external
def updatePriceAndGetUsdValueAndIsYieldAsset(
    _asset: address,
    _amount: uint256,
    _missionControl: address = empty(address),
    _legoBook: address = empty(address),
) -> (uint256, bool):
    ledger: address = addys._getLedgerAddr() # cannot allow this to be passed in as param
    if not staticcall Ledger(ledger).isUserWallet(msg.sender) and not addys._isValidUndyAddr(msg.sender):
        assert staticcall Ledger(ledger).isRegisteredBackpackItem(msg.sender) # dev: no perms

    # get usd value
    usdValue: uint256 = 0
    isYieldAsset: bool = False
    ripePriceDesk: address = empty(address)
    usdValue, isYieldAsset, ripePriceDesk = self._getUsdValueAndIsYieldAsset(_asset, _amount, ledger, _missionControl, _legoBook)

    # add snapshot to Ripe if earn vault
    if staticcall VaultRegistry(addys._getVaultRegistryAddr()).isEarnVault(_asset):
        self._updateRipeSnapshot(_asset)

    return usdValue, isYieldAsset


# usd value


@view
@internal
def _getUsdValueAndIsYieldAsset(
    _asset: address,
    _amount: uint256,
    _ledger: address,
    _missionControl: address,
    _legoBook: address,
) -> (uint256, bool, address):

    # get addresses if not provided
    ledger: address = _ledger
    if _ledger == empty(address):
        ledger = addys._getLedgerAddr()
    missionControl: address = _missionControl
    if _missionControl == empty(address):
        missionControl = addys._getMissionControlAddr()
    legoBook: address = _legoBook
    if _legoBook == empty(address):
        legoBook = addys._getLegoBookAddr()

    # get config
    config: AssetUsdValueConfig = self._getAssetUsdValueConfig(_asset, missionControl, legoBook, ledger)

    # get usd value
    usdValue: uint256 = 0
    ripePriceDesk: address = empty(address)
    if config.isYieldAsset and empty(address) not in [config.legoAddr, config.underlyingAsset]:
        underlyingAmount: uint256 = staticcall YieldLego(config.legoAddr).getUnderlyingAmount(_asset, _amount)
        usdValue, ripePriceDesk = self._getUnderlyingUsdValueFromRipe(config.underlyingAsset, underlyingAmount)
    else:
        usdValue, ripePriceDesk = self._getUnderlyingUsdValueFromRipe(_asset, _amount)

    return usdValue, config.isYieldAsset, ripePriceDesk


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


@internal
def _updateRipeSnapshot(_asset: address):
    ripePriceDesk: address = staticcall Registry(RIPE_HQ).getAddr(RIPE_PRICE_DESK_ID)
    if ripePriceDesk == empty(address):
        return
    extcall RipePriceDesk(ripePriceDesk).addPriceSnapshot(_asset)


@view
@internal
def _getUnderlyingUsdValueFromRipe(_asset: address, _amount: uint256) -> (uint256, address):
    ripePriceDesk: address = staticcall Registry(RIPE_HQ).getAddr(RIPE_PRICE_DESK_ID)
    if ripePriceDesk == empty(address):
        return 0, empty(address)
    usdValue: uint256 = staticcall RipePriceDesk(ripePriceDesk).getUsdValue(_asset, _amount, False)
    return usdValue, ripePriceDesk


@view
@external
def getAssetAmountFromRipe(_asset: address, _usdValue: uint256) -> uint256:
    ripePriceDesk: address = staticcall Registry(RIPE_HQ).getAddr(RIPE_PRICE_DESK_ID)
    if ripePriceDesk == empty(address):
        return 0
    return staticcall RipePriceDesk(ripePriceDesk).getAssetAmount(_asset, _usdValue, False)


#########
# Utils #
#########


# get profit calc config


@view
@external
def getProfitCalcConfig(_asset: address) -> ProfitCalcConfig:
    a: addys.Addys = addys._getAddys()
    return self._getProfitCalcConfig(_asset, a.missionControl, a.legoBook, a.ledger)


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


# get asset usd value config


@view
@external
def getAssetUsdValueConfig(_asset: address) -> AssetUsdValueConfig:
    a: addys.Addys = addys._getAddys()
    return self._getAssetUsdValueConfig(_asset, a.missionControl, a.legoBook, a.ledger)


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
