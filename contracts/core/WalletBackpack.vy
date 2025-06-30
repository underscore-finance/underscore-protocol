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

from ethereum.ercs import IERC20
from ethereum.ercs import IERC20Detailed

interface MissionControl:
    def getSwapFeeConfig(_tokenIn: address, _tokenOut: address) -> SwapFeeConfig: view
    def getUnderlyingAssetAndDecimals(_asset: address) -> (address, uint256): view
    def getAssetUsdValueConfig(_asset: address) -> AssetUsdValueConfig: view
    def getProfitCalcConfig(_asset: address) -> ProfitCalcConfig: view
    def getRewardsFeeConfig(_asset: address) -> RewardsFeeConfig: view
    def feeRecipient() -> address: view

interface Ledger:
    def setUserAndGlobalPoints(_user: address, _userData: PointsData, _globalData: PointsData): nonpayable
    def getUserAndGlobalPoints(_user: address) -> (PointsData, PointsData): view
    def getLastTotalUsdValue(_user: address) -> uint256: view
    def isUserWallet(_user: address) -> bool: view

interface UserWallet:
    def updateAssetData(_legoId: uint256, _asset: address, _shouldCheckYield: bool) -> uint256: nonpayable
    def recoverNft(_collection: address, _nftTokenId: uint256, _recipient: address) -> bool: nonpayable
    def assetData(_asset: address) -> WalletAssetData: view
    def assets(_index: uint256) -> address: view
    def walletConfig() -> address: view
    def numAssets() -> uint256: view

interface UserWalletConfig:
    def setEjectionMode(_inEjectMode: bool): nonpayable
    def setFrozen(_isFrozen: bool): nonpayable
    def cancelOwnershipChange(): nonpayable
    def trialFundsAmount() -> uint256: view
    def trialFundsAsset() -> address: view

interface RipePriceDesk:
    def getPrice(_asset: address, _shouldRaise: bool = False) -> uint256: view

interface Switchboard:
    def isSwitchboardAddr(_addr: address) -> bool: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

struct WalletAssetData:
    assetBalance: uint256
    usdValue: uint256
    isYieldAsset: bool
    lastYieldPrice: uint256

struct LastPrice:
    price: uint256
    lastUpdate: uint256

struct LastPricePerShare:
    underlyingAsset: address
    pricePerShare: uint256
    lastUpdate: uint256

struct PointsData:
    usdValue: uint256
    depositPoints: uint256
    lastUpdate: uint256

struct BackpackData:
    legoBook: address
    feeRecipient: address
    lastTotalUsdValue: uint256

# helpers

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

struct AssetUsdValueConfig:
    legoId: uint256
    legoAddr: address
    decimals: uint256
    staleBlocks: uint256
    isYieldAsset: bool
    underlyingAsset: address

struct SwapFeeConfig:
    tokenInIsStablecoin: bool
    tokenOutIsStablecoin: bool
    tokenOutIsConfigured: bool
    tokenOutSwapFee: uint256
    genStableSwapFee: uint256
    genSwapFee: uint256

struct RewardsFeeConfig:
    tokenIsConfigured: bool
    tokenRewardsFee: uint256
    genRewardsFee: uint256

# price cache
lastPrice: public(HashMap[address, LastPrice]) # asset -> last price
lastPricePerShare: public(HashMap[address, LastPricePerShare]) # asset -> last price per share

HUNDRED_PERCENT: constant(uint256) = 100_00 # 100.00%
EIGHTEEN_DECIMALS: constant(uint256) = 10 ** 18
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
def performPostActionTasks(_newUserValue: uint256, _walletConfig: address):
    ledger: address = addys._getLedgerAddr()
    assert staticcall Ledger(ledger).isUserWallet(msg.sender) # dev: not a user wallet

    # check trial funds first
    assert self._doesWalletStillHaveTrialFunds(msg.sender, _walletConfig) # dev: user no longer has trial funds

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


##########################
# Mission Control Config #
##########################


@view
@external
def getSwapFee(_user: address, _tokenIn: address, _tokenOut: address) -> uint256:
    # NOTE: passing in `_user` in case we ever have different fees for different users in future
    config: SwapFeeConfig = staticcall MissionControl(addys._getMissionControlAddr()).getSwapFeeConfig(_tokenIn, _tokenOut)

    # stable swap fee
    if config.tokenInIsStablecoin and config.tokenOutIsStablecoin:
        return config.genStableSwapFee

    # asset swap fee takes precedence over global swap fee
    if config.tokenOutIsConfigured:
        return config.tokenOutSwapFee

    return config.genSwapFee


@view
@external
def getRewardsFee(_user: address, _asset: address) -> uint256:
    # NOTE: passing in `_user` in case we ever have different fees for different users in future
    config: RewardsFeeConfig = staticcall MissionControl(addys._getMissionControlAddr()).getRewardsFeeConfig(_asset)
    if config.tokenIsConfigured:
        return config.tokenRewardsFee
    return config.genRewardsFee


##################
# Yield Handling #
##################


@external
def calculateYieldProfits(
    _asset: address,
    _currentBalance: uint256,
    _assetBalance: uint256,
    _lastYieldPrice: uint256,
) -> (uint256, uint256, uint256):
    hq: address = addys._getUndyHq()
    ledger: address = staticcall Registry(hq).getAddr(LEDGER_ID)
    assert staticcall Ledger(ledger).isUserWallet(msg.sender) # dev: no perms

    config: ProfitCalcConfig = self._getProfitCalcConfig(_asset, hq)
    if not config.isYieldAsset:
        return 0, 0, 0

    if config.isRebasing:
        return self._handleRebaseYieldAsset(_asset, config, _currentBalance, _assetBalance)
    else:
        return self._handleNormalYieldAsset(_asset, config, _currentBalance, _assetBalance, _lastYieldPrice, hq)


# rebasing assets


@internal
def _handleRebaseYieldAsset(
    _asset: address,
    _config: ProfitCalcConfig,
    _currentBalance: uint256,
    _lastBalance: uint256,
) -> (uint256, uint256, uint256):

    # no profits if balance decreased or stayed the same
    if _currentBalance <= _lastBalance:
        return 0, 0, 0
    
    # calculate the actual profit
    uncappedProfit: uint256 = _currentBalance - _lastBalance
    actualProfit: uint256 = uncappedProfit
    
    # apply max yield increase cap if configured
    if _config.maxYieldIncrease != 0:
        maxAllowedProfit: uint256 = _lastBalance * _config.maxYieldIncrease // HUNDRED_PERCENT
        actualProfit = min(uncappedProfit, maxAllowedProfit)
    
    # no profits after applying cap
    if actualProfit == 0:
        return 0, 0, 0
    
    return 0, actualProfit, _config.yieldProfitFee


# normal yield assets


@internal
def _handleNormalYieldAsset(
    _asset: address,
    _config: ProfitCalcConfig,
    _currentBalance: uint256,
    _lastBalance: uint256,
    _lastYieldPrice: uint256,
    _hq: address,
) -> (uint256, uint256, uint256):
    currentPricePerShare: uint256 = self._updateAndGetPricePerShare(_asset, _config.legoAddr, _config.staleBlocks, _hq)

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
def _getProfitCalcConfig(_asset: address, _hq: address) -> ProfitCalcConfig:
    missionControl: address = staticcall Registry(_hq).getAddr(MISSION_CONTROL_ID)
    config: ProfitCalcConfig = staticcall MissionControl(missionControl).getProfitCalcConfig(_asset)

    # get lego addr if needed
    if config.legoId != 0 and config.legoAddr == empty(address):
        legoBook: address = staticcall Registry(_hq).getAddr(LEGO_BOOK_ID)
        config.legoAddr = staticcall Registry(legoBook).getAddr(config.legoId)

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
        price = self._getPrice(_asset, hq)

    # yield price
    else:
        pricePerShare: uint256 = self._getPricePerShare(_asset, hq)

        # for yield assets, need to check if it has underlying asset
        if config.underlyingAsset != empty(address):
            underlyingConfig: AssetUsdValueConfig = self._getAssetUsdValueConfig(config.underlyingAsset, hq)
            underlyingPrice: uint256 = self._getPrice(config.underlyingAsset, hq)
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
    ledger: address = staticcall Registry(hq).getAddr(LEDGER_ID)
    assert staticcall Ledger(ledger).isUserWallet(msg.sender) # dev: no perms
    usdValue: uint256 = 0
    na: bool = False
    usdValue, na = self._updatePriceAndGetUsdValue(_asset, _amount, hq)
    return usdValue


@external
def updatePriceAndGetUsdValueAndIsYieldAsset(_asset: address, _amount: uint256) -> (uint256, bool):
    hq: address = addys._getUndyHq()
    ledger: address = staticcall Registry(hq).getAddr(LEDGER_ID)
    assert staticcall Ledger(ledger).isUserWallet(msg.sender) # dev: no perms
    return self._updatePriceAndGetUsdValue(_asset, _amount, hq)


@internal
def _updatePriceAndGetUsdValue(_asset: address, _amount: uint256, _hq: address) -> (uint256, bool):
    config: AssetUsdValueConfig = self._getAssetUsdValueConfig(_asset, _hq)

    # normal price
    price: uint256 = 0
    if not config.isYieldAsset:
        price = self._updateAndGetPrice(_asset, config.legoAddr, config.staleBlocks, _hq)

    # yield price
    else:
        pricePerShare: uint256 = self._updateAndGetPricePerShare(_asset, config.legoAddr, config.staleBlocks, _hq)

        # for yield assets, need to check if it has underlying asset
        if config.underlyingAsset != empty(address):
            underlyingConfig: AssetUsdValueConfig = self._getAssetUsdValueConfig(config.underlyingAsset, _hq)
            underlyingPrice: uint256 = self._updateAndGetPrice(config.underlyingAsset, underlyingConfig.legoAddr, underlyingConfig.staleBlocks, _hq)
            price = underlyingPrice * pricePerShare // (10 ** underlyingConfig.decimals)
        else:
            price = pricePerShare

    # finalize value
    usdValue: uint256 = price * _amount // (10 ** config.decimals)

    return usdValue, config.isYieldAsset


# utils


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


@view
@internal
def _getDecimals(_asset: address) -> uint256:
    if _asset in [WETH, ETH]:
        return 18
    return convert(staticcall IERC20Detailed(_asset).decimals(), uint256)


########################
# Normal Asset - Price #
########################


# get price


@view
@external
def getPrice(_asset: address) -> uint256:
    hq: address = addys._getUndyHq()
    return self._getPrice(_asset, hq)


@view
@internal
def _getPrice(_asset: address, _hq: address) -> uint256:
    config: AssetUsdValueConfig = self._getAssetUsdValueConfig(_asset, _hq)
    data: LastPrice = empty(LastPrice)
    na: bool = False
    data, na = self._getPriceAndDidUpdate(_asset, config.legoAddr, config.staleBlocks, _hq)
    return data.price


@view
@internal
def _getPriceAndDidUpdate(
    _asset: address,
    _legoAddr: address,
    _staleBlocks: uint256,
    _hq: address,
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
def updateAndGetPrice(_asset: address) -> uint256:
    hq: address = addys._getUndyHq()
    ledger: address = staticcall Registry(hq).getAddr(LEDGER_ID)
    assert staticcall Ledger(ledger).isUserWallet(msg.sender) # dev: no perms
    config: AssetUsdValueConfig = self._getAssetUsdValueConfig(_asset, hq)
    return self._updateAndGetPrice(_asset, config.legoAddr, config.staleBlocks, hq)


@internal
def _updateAndGetPrice(
    _asset: address,
    _legoAddr: address,
    _staleBlocks: uint256,
    _hq: address,
) -> uint256:
    data: LastPrice = empty(LastPrice)
    didPriceChange: bool = False
    data, didPriceChange = self._getPriceAndDidUpdate(_asset, _legoAddr, _staleBlocks, _hq)
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
    return self._getPricePerShare(_asset, hq)


@view
@internal
def _getPricePerShare(_asset: address, _hq: address) -> uint256:
    config: AssetUsdValueConfig = self._getAssetUsdValueConfig(_asset, _hq)
    data: LastPricePerShare = empty(LastPricePerShare)
    na: bool = False
    data, na = self._getPricePerShareAndDidUpdate(_asset, config.legoAddr, config.staleBlocks, _hq)
    return data.pricePerShare


@view
@internal
def _getPricePerShareAndDidUpdate(
    _asset: address,
    _legoAddr: address,
    _staleBlocks: uint256,
    _hq: address,
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
def updateAndGetPricePerShare(
    _asset: address,
    _legoAddr: address,
    _staleBlocks: uint256,
) -> uint256:
    hq: address = addys._getUndyHq()
    ledger: address = staticcall Registry(hq).getAddr(LEDGER_ID)
    assert staticcall Ledger(ledger).isUserWallet(msg.sender) # dev: no perms
    config: AssetUsdValueConfig = self._getAssetUsdValueConfig(_asset, hq)
    return self._updateAndGetPricePerShare(_asset, config.legoAddr, config.staleBlocks, hq)


@internal
def _updateAndGetPricePerShare(
    _asset: address,
    _legoAddr: address,
    _staleBlocks: uint256,
    _hq: address,
) -> uint256:
    data: LastPricePerShare = empty(LastPricePerShare)
    didPriceChange: bool = False
    data, didPriceChange = self._getPricePerShareAndDidUpdate(_asset, _legoAddr, _staleBlocks, _hq)
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


###############
# Trial Funds #
###############


@view
@external
def doesWalletStillHaveTrialFunds(_user: address) -> bool:
    walletConfig: address = staticcall UserWallet(_user).walletConfig()
    return self._doesWalletStillHaveTrialFunds(_user, walletConfig)


@view
@internal
def _doesWalletStillHaveTrialFunds(_user: address, _walletConfig: address) -> bool:
    trialFundsAmount: uint256 = staticcall UserWalletConfig(_walletConfig).trialFundsAmount()
    if trialFundsAmount == 0:
        return True
    
    trialFundsAsset: address = staticcall UserWalletConfig(_walletConfig).trialFundsAsset()
    if trialFundsAsset == empty(address):
        return True
    
    amount: uint256 = staticcall IERC20(trialFundsAsset).balanceOf(_user)
    if amount >= trialFundsAmount:
        return True

    hq: address = addys._getUndyHq()
    missionControl: address = staticcall Registry(hq).getAddr(MISSION_CONTROL_ID)

    numAssets: uint256 = staticcall UserWallet(_walletConfig).numAssets()
    if numAssets == 0:
        return False

    for i: uint256 in range(1, numAssets, bound=max_value(uint256)):
        if amount >= trialFundsAmount:
            return True

        asset: address = staticcall UserWallet(_walletConfig).assets(i)
        if asset == empty(address):
            continue

        data: WalletAssetData = staticcall UserWallet(_walletConfig).assetData(asset)
        if not data.isYieldAsset or data.usdValue == 0:
            continue

        # get underlying details
        underlyingAsset: address = empty(address)
        underlyingDecimals: uint256 = 0
        underlyingAsset, underlyingDecimals = staticcall MissionControl(missionControl).getUnderlyingAssetAndDecimals(asset)
        if underlyingAsset != trialFundsAsset:
            continue
        
        underlyingPrice: uint256 = self._getPrice(underlyingAsset, hq)
        if underlyingPrice == 0:
            continue

        # get decimals if needed
        if underlyingDecimals == 0:
            underlyingDecimals = self._getDecimals(underlyingAsset)

        underlyingAmount: uint256 = data.usdValue * (10 ** underlyingDecimals) // underlyingPrice
        amount += underlyingAmount

    return amount >= trialFundsAmount


##################
# Config / Admin #
##################


@external
def updateAssetInWallet(_legoId: uint256, _user: address, _asset: address, _shouldCheckYield: bool):
    a: addys.Addys = addys._getAddys()
    assert staticcall Switchboard(a.switchboard).isSwitchboardAddr(msg.sender) # dev: no perms

    assert _asset != empty(address) # dev: invalid asset
    newUserValue: uint256 = extcall UserWallet(_user).updateAssetData(_legoId, _asset, _shouldCheckYield)
    self._updateDepositPoints(_user, newUserValue, a.ledger)


@external
def cancelOwnershipChange(_user: address):
    assert staticcall Switchboard(addys._getSwitchboardAddr()).isSwitchboardAddr(msg.sender) # dev: no perms
    walletConfig: address = staticcall UserWallet(_user).walletConfig()
    extcall UserWalletConfig(walletConfig).cancelOwnershipChange()


@external
def setEjectionMode(_user: address, _inEjectMode: bool):
    assert staticcall Switchboard(addys._getSwitchboardAddr()).isSwitchboardAddr(msg.sender) # dev: no perms
    walletConfig: address = staticcall UserWallet(_user).walletConfig()
    extcall UserWalletConfig(walletConfig).setEjectionMode(_inEjectMode)


@external
def setFrozen(_user: address, _isFrozen: bool):
    assert staticcall Switchboard(addys._getSwitchboardAddr()).isSwitchboardAddr(msg.sender) # dev: no perms
    walletConfig: address = staticcall UserWallet(_user).walletConfig()
    extcall UserWalletConfig(walletConfig).setFrozen(_isFrozen)


@external
def recoverNft(_user: address,_collection: address, _nftTokenId: uint256, _recipient: address) -> bool:
    a: addys.Addys = addys._getAddys()
    assert staticcall Switchboard(a.switchboard).isSwitchboardAddr(msg.sender) # dev: no perms
    assert staticcall Ledger(a.ledger).isUserWallet(_user) # dev: no perms
    return extcall UserWallet(_user).recoverNft(_collection, _nftTokenId, _recipient)
