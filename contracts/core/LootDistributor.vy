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
from interfaces import Wallet as wi
import interfaces.ConfigStructs as cs

from ethereum.ercs import IERC20
from ethereum.ercs import IERC20Detailed

interface Ledger:
    def setUserAndGlobalPoints(_user: address, _userData: PointsData, _globalData: PointsData): nonpayable
    def getUserAndGlobalPoints(_user: address) -> (PointsData, PointsData): view
    def vaultTokens(_vaultToken: address) -> VaultToken: view
    def ambassadors(_user: address) -> address: view
    def isUserWallet(_user: address) -> bool: view

interface MissionControl:
    def getAmbassadorConfig(_ambassador: address, _asset: address) -> AmbassadorConfig: view
    def getDepositRewardsAsset() -> address: view

interface UserWalletConfig:
    def wallet() -> address: view
    def owner() -> address: view

interface Appraiser:
    def getPricePerShare(_asset: address, _missionControl: address = empty(address), _legoBook: address = empty(address), _ledger: address = empty(address)) -> uint256: view

interface UserWallet:
    def walletConfig() -> address: view

struct PointsData:
    usdValue: uint256
    depositPoints: uint256
    lastUpdate: uint256

struct AmbassadorConfig:
    ambassador: address
    ambassadorRevShare: cs.AmbassadorRevShare
    ambassadorBonusRatio: uint256
    underlyingAsset: address
    decimals: uint256

struct DepositRewards:
    asset: address
    amount: uint256

struct VaultToken:
    legoId: uint256
    underlyingAsset: address
    decimals: uint256
    isRebasing: bool

event LootClaimed:
    user: indexed(address)
    asset: indexed(address)
    amount: uint256

event DepositRewardsAdded:
    asset: indexed(address)
    addedAmount: uint256
    newTotalAmount: uint256
    adder: indexed(address)

event DepositRewardsClaimed:
    user: indexed(address)
    asset: indexed(address)
    userRewards: uint256
    remainingRewards: uint256

event DepositRewardsRecovered:
    asset: indexed(address)
    recipient: indexed(address)
    amount: uint256

# claimable loot
totalClaimableLoot: public(HashMap[address, uint256]) # asset -> amount
claimableLoot: public(HashMap[address, HashMap[address, uint256]]) # ambassador -> asset -> amount

# ambassador claimable loot
claimableAssets: public(HashMap[address, HashMap[uint256, address]]) # ambassador -> index -> asset
indexOfClaimableAsset: public(HashMap[address, HashMap[address, uint256]]) # ambassador -> asset -> index
numClaimableAssets: public(HashMap[address, uint256]) # ambassador -> num assets

# deposit rewards
depositRewards: public(DepositRewards)

HUNDRED_PERCENT: constant(uint256) = 100_00 # 100.00%
EIGHTEEN_DECIMALS: constant(uint256) = 10 ** 18
MAX_DEREGISTER_ASSETS: constant(uint256) = 20


@deploy
def __init__(_undyHq: address):
    addys.__init__(_undyHq)
    deptBasics.__init__(False, False) # no minting


####################
# Protocol Revenue #
####################


# normal fee flow (swaps, rewards)


@external
def addLootFromSwapOrRewards(
    _asset: address,
    _feeAmount: uint256,
    _action: wi.ActionType,
    _missionControl: address = empty(address),
):
    ledger: address = addys._getLedgerAddr()
    assert staticcall Ledger(ledger).isUserWallet(msg.sender) # dev: not a user wallet

    # finalize amount
    feeAmount: uint256 = min(_feeAmount, staticcall IERC20(_asset).balanceOf(msg.sender))
    if feeAmount == 0:
        return
    assert extcall IERC20(_asset).transferFrom(msg.sender, self, feeAmount, default_return_value=True) # dev: transfer failed

    # ambassador rev share
    config: AmbassadorConfig = self._getAmbassadorConfig(msg.sender, _asset, _missionControl, ledger)
    if config.ambassador != empty(address):
        self._handleAmbassadorTxFee(_asset, feeAmount, _action, config)


# yield profit flow


@external
def addLootFromYieldProfit(
    _asset: address,
    _feeAmount: uint256,
    _totalYieldAmount: uint256,
    _missionControl: address = empty(address),
    _appraiser: address = empty(address),
):
    ledger: address = addys._getLedgerAddr()
    assert staticcall Ledger(ledger).isUserWallet(msg.sender) # dev: not a user wallet

    config: AmbassadorConfig = self._getAmbassadorConfig(msg.sender, _asset, _missionControl, ledger)
    if config.ambassador == empty(address):
        return
    
    # handle fee (this may be 0) -- no need to `transferFrom` in this case, it's already in this contract
    if _feeAmount != 0:
        self._handleAmbassadorTxFee(_asset, _feeAmount, empty(wi.ActionType), config)

    # ambassador yield bonus
    if config.ambassadorBonusRatio != 0 and config.underlyingAsset != empty(address):
        self._handleAmbassadorYieldBonus(_asset, _totalYieldAmount, config, _missionControl, _appraiser, ledger)


#######################
# Ambassadors Rewards #
#######################


# rev share (transaction fees)


@internal
def _handleAmbassadorTxFee(
    _asset: address,
    _feeAmount: uint256,
    _action: wi.ActionType,
    _config: AmbassadorConfig,
):
    feeRatio: uint256 = _config.ambassadorRevShare.yieldRatio
    if _action == wi.ActionType.SWAP:
        feeRatio = _config.ambassadorRevShare.swapRatio
    elif _action == wi.ActionType.REWARDS:
        feeRatio = _config.ambassadorRevShare.rewardsRatio

    # finalize fee
    ambassadorRatio: uint256 = min(feeRatio, HUNDRED_PERCENT)
    fee: uint256 = min(_feeAmount * ambassadorRatio // HUNDRED_PERCENT, staticcall IERC20(_asset).balanceOf(self))
    if fee != 0:
        self._addClaimableLootToAmbassador(_config.ambassador, _asset, fee)


# yield bonus


@internal
def _handleAmbassadorYieldBonus(
    _asset: address,
    _totalYieldAmount: uint256,
    _config: AmbassadorConfig,
    _missionControl: address,
    _appraiser: address,
    _ledger: address,
):
    bonusRatio: uint256 = min(_config.ambassadorBonusRatio, HUNDRED_PERCENT)
    bonusAmount: uint256 = _totalYieldAmount * bonusRatio // HUNDRED_PERCENT

    # get addys (if necessary)
    missionControl: address = _missionControl
    if _missionControl == empty(address):
        missionControl = addys._getMissionControlAddr()
    appraiser: address = _appraiser
    if _appraiser == empty(address):
        appraiser = addys._getAppraiserAddr()

    pricePerShare: uint256 = staticcall Appraiser(appraiser).getPricePerShare(_asset, missionControl, empty(address), _ledger)
    if pricePerShare == 0:
        return

    # how much is available for bonus
    availableForBonus: uint256 = 0
    currentBalance: uint256 = staticcall IERC20(_config.underlyingAsset).balanceOf(self)
    totalClaimable: uint256 = self.totalClaimableLoot[_config.underlyingAsset]
    if currentBalance > totalClaimable:
        availableForBonus = currentBalance - totalClaimable

    underlyingAmount: uint256 = min(bonusAmount * pricePerShare // (10 ** _config.decimals), availableForBonus)
    if underlyingAmount != 0:
        self._addClaimableLootToAmbassador(_config.ambassador, _config.underlyingAsset, underlyingAmount)


# get ambassador config


@view
@external
def getAmbassadorConfig(_wallet: address, _asset: address) -> AmbassadorConfig:
    return self._getAmbassadorConfig(_wallet, _asset, addys._getMissionControlAddr(), addys._getLedgerAddr())


@view
@internal
def _getAmbassadorConfig(
    _wallet: address,
    _asset: address,
    _missionControl: address,
    _ledger: address,
) -> AmbassadorConfig:
    ambassador: address = staticcall Ledger(_ledger).ambassadors(_wallet)
    if ambassador == empty(address):
        return empty(AmbassadorConfig)

    # get mission control (if necessary)
    missionControl: address = _missionControl
    if _missionControl == empty(address):
        missionControl = addys._getMissionControlAddr()

    # config
    config: AmbassadorConfig = staticcall MissionControl(missionControl).getAmbassadorConfig(ambassador, _asset)

    # if no specific config, fallback to vault token registration
    if config.decimals == 0:
        vaultToken: VaultToken = staticcall Ledger(_ledger).vaultTokens(_asset)
        if vaultToken.underlyingAsset != empty(address):
            config.decimals = vaultToken.decimals
            config.underlyingAsset = vaultToken.underlyingAsset

    # get decimals if needed
    if config.decimals == 0:
        config.decimals = convert(staticcall IERC20Detailed(_asset).decimals(), uint256)

    return config


##############
# Claim Loot #
##############


@external
def claimLoot(_user: address) -> uint256:
    a: addys.Addys = addys._getAddys()
    assert staticcall Ledger(a.ledger).isUserWallet(_user) # dev: not a user wallet

    # permission check
    walletConfig: address = staticcall UserWallet(_user).walletConfig()
    owner: address = staticcall UserWalletConfig(walletConfig).owner()
    if msg.sender != owner:
        assert addys._isSwitchboardAddr(msg.sender) # dev: no perms

    # nothing to do here
    numAssets: uint256 = self.numClaimableAssets[_user]
    assert numAssets != 0 # dev: no claimable assets

    assetsClaimed: uint256 = 0
    assetsToDeregister: DynArray[address, MAX_DEREGISTER_ASSETS] = []

    # iterate through all claimable assets for user
    for i: uint256 in range(1, numAssets, bound=max_value(uint256)):
        asset: address = self.claimableAssets[_user][i]
        if asset == empty(address):
            continue

        claimableAmount: uint256 = self.claimableLoot[_user][asset]
        if claimableAmount == 0:
            continue

        # check contract has enough balance
        transferAmount: uint256 = min(claimableAmount, staticcall IERC20(asset).balanceOf(self))
        if transferAmount == 0:
            continue

        # transfer to user
        assert extcall IERC20(asset).transfer(_user, transferAmount, default_return_value=True) # dev: xfer fail

        # update tracking
        self.totalClaimableLoot[asset] -= transferAmount
        self.claimableLoot[_user][asset] -= transferAmount
        assetsClaimed += 1

        # add to deregister list
        if claimableAmount == transferAmount and len(assetsToDeregister) < MAX_DEREGISTER_ASSETS:
            assetsToDeregister.append(asset)

        log LootClaimed(
            user = _user,
            asset = asset,
            amount = transferAmount
        )

    # deregister assets
    if len(assetsToDeregister) != 0:
        for asset: address in assetsToDeregister:
            self._deregisterClaimableAssetForAmbassador(_user, asset)

    assert assetsClaimed != 0 # dev: no assets claimed
    return assetsClaimed


# claimable assets


@view
@external
def getTotalClaimableAssets(_user: address) -> uint256:
    numAssets: uint256 = self.numClaimableAssets[_user]
    if numAssets == 0:
        return 0

    totalAssets: uint256 = 0
    for i: uint256 in range(1, numAssets, bound=max_value(uint256)):
        asset: address = self.claimableAssets[_user][i]
        if asset == empty(address):
            continue
            
        claimableAmount: uint256 = min(self.claimableLoot[_user][asset], staticcall IERC20(asset).balanceOf(self))
        if claimableAmount != 0:
            totalAssets += 1
    
    return totalAssets


#####################
# Loot Registration #
#####################


# add loot to ambassador


@internal
def _addClaimableLootToAmbassador(_ambassador: address, _asset: address, _amount: uint256):
    self.totalClaimableLoot[_asset] += _amount
    self.claimableLoot[_ambassador][_asset] += _amount
    self._registerClaimableAssetForAmbassador(_ambassador, _asset)


# register claimable asset


@internal
def _registerClaimableAssetForAmbassador(_ambassador: address, _asset: address):
    if self.indexOfClaimableAsset[_ambassador][_asset] != 0:
        return

    aid: uint256 = self.numClaimableAssets[_ambassador]
    if aid == 0:
        aid = 1 # not using 0 index
    self.claimableAssets[_ambassador][aid] = _asset
    self.indexOfClaimableAsset[_ambassador][_asset] = aid
    self.numClaimableAssets[_ambassador] = aid + 1


# deregister asset


@internal
def _deregisterClaimableAssetForAmbassador(_ambassador: address, _asset: address) -> bool:
    numAssets: uint256 = self.numClaimableAssets[_ambassador]
    if numAssets == 0:
        return False

    targetIndex: uint256 = self.indexOfClaimableAsset[_ambassador][_asset]
    if targetIndex == 0:
        return False

    # update data
    lastIndex: uint256 = numAssets - 1
    self.numClaimableAssets[_ambassador] = lastIndex
    self.indexOfClaimableAsset[_ambassador][_asset] = 0

    # get last item, replace the removed item
    if targetIndex != lastIndex:
        lastItem: address = self.claimableAssets[_ambassador][lastIndex]
        self.claimableAssets[_ambassador][targetIndex] = lastItem
        self.indexOfClaimableAsset[_ambassador][lastItem] = targetIndex

    return True


##################
# Deposit Points #
##################


# update points


@external
def updateDepositPoints(_user: address):
    a: addys.Addys = addys._getAddys()
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    self._updateDepositPoints(_user, 0, False, a.ledger)


@external
def updateDepositPointsWithNewValue(_user: address, _newUsdValue: uint256):
    ledger: address = addys._getLedgerAddr()
    if not staticcall Ledger(ledger).isUserWallet(msg.sender):
        assert self._isValidWalletConfig(_user, msg.sender, ledger) # dev: invalid config
    self._updateDepositPoints(_user, _newUsdValue, True, ledger)


@internal
def _updateDepositPoints(
    _user: address,
    _newUsdValue: uint256,
    _didUsdValueChange: bool,
    _ledger: address,
):
    userPoints: PointsData = empty(PointsData)
    globalPoints: PointsData = empty(PointsData)
    userPoints, globalPoints = staticcall Ledger(_ledger).getUserAndGlobalPoints(_user)

    prevUserValue: uint256 = userPoints.usdValue

    # update user data
    userPoints.depositPoints += self._getLatestDepositPoints(prevUserValue, userPoints.lastUpdate)
    userPoints.lastUpdate = block.number
    if _didUsdValueChange:
        userPoints.usdValue = _newUsdValue
    
    # update global data
    globalPoints.depositPoints += self._getLatestDepositPoints(globalPoints.usdValue, globalPoints.lastUpdate)
    globalPoints.lastUpdate = block.number
    if _didUsdValueChange:
        globalPoints.usdValue -= prevUserValue
        globalPoints.usdValue += _newUsdValue

    # save data
    extcall Ledger(_ledger).setUserAndGlobalPoints(_user, userPoints, globalPoints)


# latest points


@view
@external
def getLatestDepositPoints(_usdValue: uint256, _lastUpdate: uint256) -> uint256:
    return self._getLatestDepositPoints(_usdValue, _lastUpdate)


@view
@internal
def _getLatestDepositPoints(_usdValue: uint256, _lastUpdate: uint256) -> uint256:
    if _usdValue == 0 or _lastUpdate == 0 or block.number <= _lastUpdate:
        return 0
    points: uint256 = _usdValue * (block.number - _lastUpdate)
    return points // EIGHTEEN_DECIMALS


# validate wallet config


@view
@external
def isValidWalletConfig(_wallet: address, _caller: address) -> bool:
    return self._isValidWalletConfig(_wallet, _caller, addys._getLedgerAddr())


@view
@internal
def _isValidWalletConfig(_wallet: address, _caller: address, _ledger: address) -> bool:
    if not staticcall Ledger(_ledger).isUserWallet(_wallet):
        return False
    walletConfig: address = staticcall UserWallet(_wallet).walletConfig()
    return walletConfig == _caller


###################
# Deposit Rewards #
###################


# claim deposit rewards


@external
def claimDepositRewards(_user: address) -> uint256:
    a: addys.Addys = addys._getAddys()
    assert staticcall Ledger(a.ledger).isUserWallet(_user) # dev: not a user wallet

    # cannot claim if this is not current loot distributor, likely migrated to new loot distributor
    assert a.lootDistributor == self # dev: not current loot distributor

    # permission check - same as claimLoot
    walletConfig: address = staticcall UserWallet(_user).walletConfig()
    owner: address = staticcall UserWalletConfig(walletConfig).owner()
    if msg.sender != owner:
        assert addys._isSwitchboardAddr(msg.sender) # dev: no perms

    # update deposit points first
    self._updateDepositPoints(_user, 0, False, a.ledger)
    userPoints: PointsData = empty(PointsData)
    globalPoints: PointsData = empty(PointsData)
    userPoints, globalPoints = staticcall Ledger(a.ledger).getUserAndGlobalPoints(_user)
    assert globalPoints.depositPoints != 0 # dev: no points

    # check if there is anything available for rewards
    data: DepositRewards = self.depositRewards
    assert data.asset != empty(address) # dev: nothing to claim
    availableRewards: uint256 = min(data.amount, staticcall IERC20(data.asset).balanceOf(self))

    # calculate user's share, transfer to user
    userRewards: uint256 = availableRewards * userPoints.depositPoints // globalPoints.depositPoints
    assert userRewards != 0 # dev: nothing to claim
    assert extcall IERC20(data.asset).transfer(_user, userRewards, default_return_value=True) # dev: xfer fail

    # save rewards data
    data.amount -= userRewards
    self.depositRewards = data

    # save / update points
    globalPoints.depositPoints -= userPoints.depositPoints
    userPoints.depositPoints = 0
    extcall Ledger(a.ledger).setUserAndGlobalPoints(_user, userPoints, globalPoints)

    log DepositRewardsClaimed(
        user = _user,
        asset = data.asset,
        userRewards = userRewards,
        remainingRewards = data.amount,
    )
    return userRewards


# add rewards


@external
def addDepositRewards(_asset: address, _amount: uint256):
    a: addys.Addys = addys._getAddys()
    depositRewardsAsset: address = staticcall MissionControl(a.missionControl).getDepositRewardsAsset() # dev: invalid asset
    assert depositRewardsAsset == _asset # dev: invalid asset

    data: DepositRewards = self.depositRewards
    if data.asset != empty(address) and data.amount != 0:
        # NOTE: if changing the rewards asset, need to recover the previous asset first (zero out the amount)
        assert data.asset == depositRewardsAsset # dev: invalid asset

    # finalize amount
    amount: uint256 = min(_amount, staticcall IERC20(depositRewardsAsset).balanceOf(msg.sender))
    assert amount != 0 # dev: nothing to add
    assert extcall IERC20(depositRewardsAsset).transferFrom(msg.sender, self, amount, default_return_value=True) # dev: transfer failed

    # update data
    data.asset = depositRewardsAsset
    data.amount += amount
    self.depositRewards = data

    log DepositRewardsAdded(asset = depositRewardsAsset, addedAmount = amount, newTotalAmount = data.amount, adder = msg.sender)


# recover deposit rewards


@external
def recoverDepositRewards(_recipient: address):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms

    data: DepositRewards = self.depositRewards
    assert data.asset != empty(address) # dev: nothing to claim
    amount: uint256 = min(data.amount, staticcall IERC20(data.asset).balanceOf(self))
    assert amount != 0 # dev: nothing to recover
    assert extcall IERC20(data.asset).transfer(_recipient, amount, default_return_value=True) # dev: recovery failed

    self.depositRewards = empty(DepositRewards)
    log DepositRewardsRecovered(asset=data.asset, recipient=_recipient, amount=amount)