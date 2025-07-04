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

interface UserWalletConfig:
    def preparePayment(_targetAsset: address, _legoId: uint256, _vaultToken: address, _vaultAmount: uint256 = max_value(uint256)) -> (uint256, uint256): nonpayable
    def setEjectionMode(_inEjectMode: bool): nonpayable
    def removeTrialFunds() -> uint256: nonpayable
    def setFrozen(_isFrozen: bool): nonpayable
    def cancelOwnershipChange(): nonpayable
    def trialFundsAmount() -> uint256: view
    def trialFundsAsset() -> address: view
    def owner() -> address: view

interface UserWallet:
    def updateAssetData(_legoId: uint256, _asset: address, _shouldCheckYield: bool) -> uint256: nonpayable
    def recoverNft(_collection: address, _nftTokenId: uint256, _recipient: address) -> bool: nonpayable
    def assetData(_asset: address) -> WalletAssetData: view
    def assets(_index: uint256) -> address: view
    def walletConfig() -> address: view
    def numAssets() -> uint256: view

interface Ledger:
    def setUserAndGlobalPoints(_user: address, _userData: PointsData, _globalData: PointsData): nonpayable
    def getUserAndGlobalPoints(_user: address) -> (PointsData, PointsData): view
    def getLastTotalUsdValue(_user: address) -> uint256: view
    def isUserWallet(_user: address) -> bool: view

interface MissionControl:
    def getAssetUsdValueConfig(_asset: address) -> AssetUsdValueConfig: view
    def getProfitCalcConfig(_asset: address) -> ProfitCalcConfig: view
    def feeRecipient() -> address: view

interface Appraiser:
    def updateAndGetPricePerShareWithConfig(_asset: address, _legoAddr: address, _staleBlocks: uint256) -> uint256: nonpayable
    def getPricePerShareWithConfig(_asset: address, _legoAddr: address, _staleBlocks: uint256) -> uint256: view

interface Switchboard:
    def isSwitchboardAddr(_addr: address) -> bool: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

struct WalletAssetData:
    assetBalance: uint256
    usdValue: uint256
    isYieldAsset: bool
    lastYieldPrice: uint256

struct PointsData:
    usdValue: uint256
    depositPoints: uint256
    lastUpdate: uint256

struct BackpackData:
    missionControl: address
    legoBook: address
    appraiser: address
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

HUNDRED_PERCENT: constant(uint256) = 100_00 # 100.00%
EIGHTEEN_DECIMALS: constant(uint256) = 10 ** 18

LEDGER_ID: constant(uint256) = 2
MISSION_CONTROL_ID: constant(uint256) = 3
LEGO_BOOK_ID: constant(uint256) = 4
APPRAISER_ID: constant(uint256) = 8

WETH: public(immutable(address))
ETH: public(immutable(address))


@deploy
def __init__(
    _undyHq: address,
    _wethAddr: address,
    _ethAddr: address,
):
    addys.__init__(_undyHq)
    deptBasics.__init__(False, False) # no minting

    WETH = _wethAddr
    ETH = _ethAddr


###################
# Data for Wallet #
###################


@view
@external
def getBackpackData(_user: address) -> BackpackData:
    hq: address = addys._getUndyHq()
    mc: address = staticcall Registry(hq).getAddr(MISSION_CONTROL_ID)
    ledger: address = staticcall Registry(hq).getAddr(LEDGER_ID)

    return BackpackData(
        missionControl = mc,
        legoBook = staticcall Registry(hq).getAddr(LEGO_BOOK_ID),
        appraiser = staticcall Registry(hq).getAddr(APPRAISER_ID),
        feeRecipient = staticcall MissionControl(mc).feeRecipient(),
        lastTotalUsdValue = staticcall Ledger(ledger).getLastTotalUsdValue(_user),
    )


#####################
# Post Action Tasks #
#####################


# post action tasks


@external
def performPostActionTasks(
    _newUserValue: uint256,
    _walletConfig: address,
    _missionControl: address,
    _legoBook: address,
    _appraiser: address,
):
    ledger: address = addys._getLedgerAddr()
    assert staticcall Ledger(ledger).isUserWallet(msg.sender) # dev: not a user wallet

    # check trial funds first
    assert self._doesWalletStillHaveTrialFunds(msg.sender, _walletConfig, _missionControl, _legoBook, _appraiser) # dev: user no longer has trial funds

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
    _appraiser: address,
) -> (uint256, uint256, uint256):
    hq: address = addys._getUndyHq()
    ledger: address = staticcall Registry(hq).getAddr(LEDGER_ID)
    assert staticcall Ledger(ledger).isUserWallet(msg.sender) # dev: no perms

    config: ProfitCalcConfig = self._getProfitCalcConfig(_asset, _missionControl, _legoBook)
    if not config.isYieldAsset:
        return 0, 0, 0

    if config.isRebasing:
        return self._handleRebaseYieldAsset(_asset, _currentBalance, _assetBalance, config.maxYieldIncrease, config.yieldProfitFee)
    else:
        return self._handleNormalYieldAsset(_asset, _currentBalance, _assetBalance, _lastYieldPrice, config, _appraiser)


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
    _appraiser: address,
) -> (uint256, uint256, uint256):
    currentPricePerShare: uint256 = extcall Appraiser(_appraiser).updateAndGetPricePerShareWithConfig(_asset, _config.legoAddr, _config.staleBlocks)

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


###############
# Trial Funds #
###############


# clawback trial funds


@external
def clawBackTrialFunds(_user: address) -> uint256:
    a: addys.Addys = addys._getAddys()
    assert staticcall Ledger(a.ledger).isUserWallet(_user) # dev: not a user wallet
    walletConfig: address = staticcall UserWallet(_user).walletConfig()
    assert staticcall Switchboard(a.switchboard).isSwitchboardAddr(msg.sender) or staticcall UserWalletConfig(walletConfig).owner() == msg.sender # dev: no perms
    return self._clawBackTrialFunds(_user, walletConfig, a.missionControl, a.legoBook, a.appraiser)


@internal
def _clawBackTrialFunds(
    _user: address,
    _walletConfig: address,
    _missionControl: address,
    _legoBook: address,
    _appraiser: address,
) -> uint256:
    trialFundsAmount: uint256 = staticcall UserWalletConfig(_walletConfig).trialFundsAmount()
    trialFundsAsset: address = staticcall UserWalletConfig(_walletConfig).trialFundsAsset()
    if trialFundsAmount == 0 or trialFundsAsset == empty(address):
        return 0

    # add 1% buffer to ensure we recover enough
    targetRecoveryAmount: uint256 = trialFundsAmount * 101_00 // HUNDRED_PERCENT

    # if we already have enough, just remove what we have
    amountRecovered: uint256 = staticcall IERC20(trialFundsAsset).balanceOf(_user)
    if amountRecovered >= targetRecoveryAmount:
        return extcall UserWalletConfig(_walletConfig).removeTrialFunds()

    # find all vault tokens and withdraw from them
    numAssets: uint256 = staticcall UserWallet(_user).numAssets()
    if numAssets != 0:
        for i: uint256 in range(1, numAssets, bound=max_value(uint256)):
            if amountRecovered >= targetRecoveryAmount:
                break

            asset: address = staticcall UserWallet(_user).assets(i)
            if asset == empty(address):
                continue

            data: WalletAssetData = staticcall UserWallet(_user).assetData(asset)
            if not data.isYieldAsset or data.assetBalance == 0:
                continue

            # get underlying details
            config: AssetUsdValueConfig = self._getAssetUsdValueConfig(asset, _missionControl, _legoBook)
            if config.underlyingAsset != trialFundsAsset:
                continue

            # get price per share for this vault token
            pricePerShare: uint256 = staticcall Appraiser(_appraiser).getPricePerShareWithConfig(asset, config.legoAddr, config.staleBlocks)
            if pricePerShare == 0:
                continue

            # calculate how many vault tokens we need to withdraw
            amountStillNeeded: uint256 = targetRecoveryAmount - amountRecovered
            vaultTokensNeeded: uint256 = amountStillNeeded * (10 ** config.decimals) // pricePerShare

            # don't withdraw more than available
            targetAmount: uint256 = min(vaultTokensNeeded, staticcall IERC20(asset).balanceOf(_user))
            if targetAmount == 0:
                continue

            # withdraw vault tokens to get underlying
            underlyingAmount: uint256 = 0
            na: uint256 = 0
            underlyingAmount, na = extcall UserWalletConfig(_walletConfig).preparePayment(config.underlyingAsset, config.legoId, asset, targetAmount)

            # update recovered amount
            amountRecovered += underlyingAmount

    # now remove trial funds
    return extcall UserWalletConfig(_walletConfig).removeTrialFunds()


# check if it remains


@view
@external
def doesWalletStillHaveTrialFunds(_user: address) -> bool:
    a: addys.Addys = addys._getAddys()
    walletConfig: address = staticcall UserWallet(_user).walletConfig()
    return self._doesWalletStillHaveTrialFunds(_user, walletConfig, a.missionControl, a.legoBook, a.appraiser)


@view
@internal
def _doesWalletStillHaveTrialFunds(
    _user: address,
    _walletConfig: address,
    _missionControl: address,
    _legoBook: address,
    _appraiser: address,
) -> bool:
    trialFundsAmount: uint256 = staticcall UserWalletConfig(_walletConfig).trialFundsAmount()
    trialFundsAsset: address = staticcall UserWalletConfig(_walletConfig).trialFundsAsset()
    if trialFundsAmount == 0 or trialFundsAsset == empty(address):
        return True

    amount: uint256 = staticcall IERC20(trialFundsAsset).balanceOf(_user)
    if amount >= trialFundsAmount:
        return True

    numAssets: uint256 = staticcall UserWallet(_user).numAssets()
    if numAssets == 0:
        return False

    for i: uint256 in range(1, numAssets, bound=max_value(uint256)):
        if amount >= trialFundsAmount:
            return True

        asset: address = staticcall UserWallet(_user).assets(i)
        if asset == empty(address):
            continue

        data: WalletAssetData = staticcall UserWallet(_user).assetData(asset)
        if not data.isYieldAsset:
            continue

        # get underlying details
        config: AssetUsdValueConfig = self._getAssetUsdValueConfig(asset, _missionControl, _legoBook)
        if config.underlyingAsset != trialFundsAsset:
            continue

        # get current balance of vault token
        vaultBalance: uint256 = staticcall IERC20(asset).balanceOf(_user)
        if vaultBalance == 0:
            continue

        # get price per share for this vault token
        pricePerShare: uint256 = staticcall Appraiser(_appraiser).getPricePerShareWithConfig(asset, config.legoAddr, config.staleBlocks)
        if pricePerShare == 0:
            continue

        # calculate underlying amount
        underlyingAmount: uint256 = vaultBalance * pricePerShare // (10 ** config.decimals)
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


##############
# Eject Mode #
##############


@external
def setEjectionMode(_user: address, _shouldEject: bool):
    a: addys.Addys = addys._getAddys()
    assert staticcall Switchboard(a.switchboard).isSwitchboardAddr(msg.sender) # dev: no perms
    assert staticcall Ledger(a.ledger).isUserWallet(_user) # dev: not a user wallet

    walletConfig: address = staticcall UserWallet(_user).walletConfig()
    if _shouldEject:
        self._updateDepositPoints(_user, 0, a.ledger) # update deposit points, new usd value is zero

    extcall UserWalletConfig(walletConfig).setEjectionMode(_shouldEject)


#########
# Utils #
#########


# get asset usd value config


@view
@external
def getAssetUsdValueConfig(_asset: address) -> AssetUsdValueConfig:
    a: addys.Addys = addys._getAddys()
    return self._getAssetUsdValueConfig(_asset, a.missionControl, a.legoBook)


@view
@internal
def _getAssetUsdValueConfig(_asset: address, _missionControl: address, _legoBook: address) -> AssetUsdValueConfig:
    config: AssetUsdValueConfig = staticcall MissionControl(_missionControl).getAssetUsdValueConfig(_asset)

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