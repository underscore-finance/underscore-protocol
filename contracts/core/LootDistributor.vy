#     ___                     ___             ___                     ___                           
#    (   )                   (   )           (   )  .-.              (   )                          
#     | |    .--.     .--.    | |_         .-.| |  ( __)     .--.     | |_      ___ .-.      .--.   
#     | |   /    \   /    \  (   __)      /   \ |  (''")   /  _  \   (   __)   (   )   \    /    \  
#     | |  |  .-. ; |  .-. ;  | |        |  .-. |   | |   . .' `. ;   | |       | ' .-. ;  |  .-. ; 
#     | |  | |  | | | |  | |  | | ___    | |  | |   | |   | '   | |   | | ___   |  / (___) | |  | | 
#     | |  | |  | | | |  | |  | |(   )   | |  | |   | |   _\_`.(___)  | |(   )  | |        | |  | | 
#     | |  | |  | | | |  | |  | | | |    | |  | |   | |  (   ). '.    | | | |   | |        | |  | | 
#     | |  | '  | | | '  | |  | ' | |    | '  | |   | |   | |  `\ |   | ' | |   | |        | '  | | 
#     | |  '  `-' / '  `-' /  ' `-' ;    ' `-'  /   | |   ; '._,' '   ' `-' ;   | |        '  `-' / 
#    (___)  `.__.'   `.__.'    `.__.      `.__,'   (___)   '.___.'     `.__.   (___)        `.__.'  
#                                                                                
#     ╔═════════════════════════════════════════════════════════╗
#     ║  ** Loot Distributor **                                 ║
#     ║  Handles all rewards and revenue share functionality.   ║
#     ╚═════════════════════════════════════════════════════════╝
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
from interfaces import YieldLego as YieldLego
from interfaces import WalletStructs as ws
from interfaces import WalletConfigStructs as wcs
import interfaces.ConfigStructs as cs

from ethereum.ercs import IERC20

interface MissionControl:
    def getSwapFee(_tokenIn: address, _tokenOut: address) -> uint256: view
    def getLootDistroConfig(_asset: address) -> LootDistroConfig: view
    def getRewardsFee(_asset: address) -> uint256: view
    def getLootClaimCoolOffPeriod() -> uint256: view
    def getDepositRewardsAsset() -> address: view

interface Ledger:
    def setUserAndGlobalPoints(_user: address, _userData: PointsData, _globalData: PointsData): nonpayable
    def getUserAndGlobalPoints(_user: address) -> (PointsData, PointsData): view
    def ambassadors(_user: address) -> address: view
    def isUserWallet(_user: address) -> bool: view

interface Appraiser:
    def getAssetAmountFromRipe(_asset: address, _usdValue: uint256) -> uint256: view
    def getUnderlyingUsdValue(_asset: address, _amount: uint256) -> uint256: view

interface UserWalletConfig:
    def managerSettings(_manager: address) -> wcs.ManagerSettings: view
    def owner() -> address: view

interface RipeTeller:
    def depositIntoGovVault(_asset: address, _amount: uint256, _lockDuration: uint256, _user: address = msg.sender) -> uint256: nonpayable

interface Registry:
    def getAddr(_regId: uint256) -> address: view

interface UserWallet:
    def walletConfig() -> address: view

interface UndyHq:
    def governance() -> address: view

struct PointsData:
    usdValue: uint256
    depositPoints: uint256
    lastUpdate: uint256

struct LootDistroConfig:
    legoId: uint256
    legoAddr: address
    underlyingAsset: address
    ambassador: address
    ambassadorRevShare: cs.AmbassadorRevShare
    ambassadorBonusRatio: uint256
    bonusRatio: uint256
    bonusAsset: address

struct DepositRewards:
    asset: address
    amount: uint256

event TransactionFeePaid:
    user: indexed(address)
    asset: indexed(address)
    feeAmount: uint256
    action: ws.ActionType

event RevenueTransferredToGov:
    asset: indexed(address)
    amount: uint256
    action: ws.ActionType

event YieldPerformanceFeePaid:
    user: indexed(address)
    asset: indexed(address)
    feeAmount: uint256
    yieldRealized: uint256

event AmbassadorTxFeePaid:
    asset: indexed(address)
    totalFee: uint256
    ambassadorFeeRatio: uint256
    ambassadorFee: uint256
    ambassador: indexed(address)
    action: ws.ActionType

event YieldBonusPaid:
    bonusAsset: indexed(address)
    bonusAmount: uint256
    bonusRatio: uint256
    yieldRealized: uint256
    recipient: indexed(address)
    isAmbassador: bool

event LootAdjusted:
    user: indexed(address)
    asset: indexed(address)
    newClaimable: uint256

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

event RipeRewardsConfigSet:
    ripeStakeRatio: uint256
    ripeLockDuration: uint256

# claimable loot
lastClaim: public(HashMap[address, uint256]) # user -> last claim block
totalClaimableLoot: public(HashMap[address, uint256]) # asset -> amount
claimableLoot: public(HashMap[address, HashMap[address, uint256]]) # ambassador -> asset -> amount

# ambassador claimable loot
claimableAssets: public(HashMap[address, HashMap[uint256, address]]) # ambassador -> index -> asset
indexOfClaimableAsset: public(HashMap[address, HashMap[address, uint256]]) # ambassador -> asset -> index
numClaimableAssets: public(HashMap[address, uint256]) # ambassador -> num assets

# deposit rewards
depositRewards: public(DepositRewards)
ripeStakeRatio: public(uint256)
ripeLockDuration: public(uint256)

RIPE_TOKEN: public(immutable(address))
RIPE_REGISTRY: public(immutable(address))

HUNDRED_PERCENT: constant(uint256) = 100_00 # 100.00%
EIGHTEEN_DECIMALS: constant(uint256) = 10 ** 18
MAX_DEREGISTER_ASSETS: constant(uint256) = 20
RIPE_TELLER_ID: constant(uint256) = 17


@deploy
def __init__(
    _undyHq: address,
    _ripeToken: address,
    _ripeRegistry: address,
    _ripeStakeRatio: uint256,
    _ripeLockDuration: uint256,
):
    addys.__init__(_undyHq)
    deptBasics.__init__(False, False) # no minting

    assert empty(address) not in [_ripeToken, _ripeRegistry] # dev: invalid addresses
    RIPE_TOKEN = _ripeToken
    RIPE_REGISTRY = _ripeRegistry

    assert _ripeStakeRatio <= HUNDRED_PERCENT # dev: invalid stake ratio
    self.ripeStakeRatio = _ripeStakeRatio
    assert _ripeLockDuration != 0 # dev: invalid lock duration
    self.ripeLockDuration = _ripeLockDuration


#################
# Revenue Flows #
#################


# normal fee flow (swaps, rewards)


@external
def addLootFromSwapOrRewards(
    _asset: address,
    _feeAmount: uint256,
    _action: ws.ActionType,
    _missionControl: address = empty(address),
):
    # if paused, fail gracefully
    if deptBasics.isPaused:
        return

    ledger: address = addys._getLedgerAddr()
    assert staticcall Ledger(ledger).isUserWallet(msg.sender) # dev: not a user wallet

    # finalize amount
    feeAmount: uint256 = min(_feeAmount, staticcall IERC20(_asset).balanceOf(msg.sender))
    if feeAmount == 0:
        return

    assert extcall IERC20(_asset).transferFrom(msg.sender, self, feeAmount, default_return_value=True) # dev: transfer failed
    log TransactionFeePaid(user = msg.sender, asset = _asset, feeAmount = feeAmount, action = _action)

    ambFee: uint256 = 0
    ambassador: address = staticcall Ledger(ledger).ambassadors(msg.sender)
    if ambassador != empty(address):
        missionControl: address = _missionControl if _missionControl != empty(address) else addys._getMissionControlAddr()
        config: LootDistroConfig = staticcall MissionControl(missionControl).getLootDistroConfig(_asset)
        config.ambassador = ambassador
        ambFee = self._handleAmbassadorTxFee(_asset, feeAmount, _action, config)

    # transfer leftover revenue to gov
    leftoverFee: uint256 = feeAmount - min(feeAmount, ambFee)
    if leftoverFee != 0:
        self._transferRevenueToGov(_asset, leftoverFee, _action)


# yield profit flow


@external
def addLootFromYieldProfit(
    _asset: address,
    _feeAmount: uint256,
    _yieldRealized: uint256,
    _missionControl: address = empty(address),
    _appraiser: address = empty(address),
    _legoBook: address = empty(address),
):
    # if paused, fail gracefully
    if deptBasics.isPaused:
        return

    ledger: address = addys._getLedgerAddr()
    assert staticcall Ledger(ledger).isUserWallet(msg.sender) # dev: not a user wallet
    log YieldPerformanceFeePaid(user = msg.sender, asset = _asset, feeAmount = _feeAmount, yieldRealized = _yieldRealized)

    ambassador: address = staticcall Ledger(ledger).ambassadors(msg.sender)
    missionControl: address = _missionControl if _missionControl != empty(address) else addys._getMissionControlAddr()
    config: LootDistroConfig = staticcall MissionControl(missionControl).getLootDistroConfig(_asset)
    config.ambassador = ambassador
    
    # handle fee (this may be 0) -- no need to `transferFrom` in this case, it's already in this contract
    ambFee: uint256 = 0
    if _feeAmount != 0 and ambassador != empty(address):
        ambFee = self._handleAmbassadorTxFee(_asset, _feeAmount, empty(ws.ActionType), config)

    # transfer leftover revenue to gov
    leftoverFee: uint256 = _feeAmount - min(_feeAmount, ambFee)
    if leftoverFee != 0:
        self._transferRevenueToGov(_asset, leftoverFee, ws.ActionType.EARN_WITHDRAW)

    # yield bonus -- must be eligible
    if config.legoAddr != empty(address) and staticcall YieldLego(config.legoAddr).isEligibleForYieldBonus(_asset):
        self._handleYieldBonus(msg.sender, _asset, _yieldRealized, config, _appraiser)


# ambassador rev share (transaction fees)


@internal
def _handleAmbassadorTxFee(
    _asset: address,
    _feeAmount: uint256,
    _action: ws.ActionType,
    _config: LootDistroConfig,
) -> uint256:
    feeRatio: uint256 = _config.ambassadorRevShare.yieldRatio
    if _action == ws.ActionType.SWAP:
        feeRatio = _config.ambassadorRevShare.swapRatio
    elif _action == ws.ActionType.REWARDS:
        feeRatio = _config.ambassadorRevShare.rewardsRatio

    # finalize fee
    ambassadorRatio: uint256 = min(feeRatio, HUNDRED_PERCENT)
    fee: uint256 = min(_feeAmount * ambassadorRatio // HUNDRED_PERCENT, staticcall IERC20(_asset).balanceOf(self))
    if fee != 0:
        self._addClaimableLootToUser(_config.ambassador, _asset, fee)
        log AmbassadorTxFeePaid(asset = _asset, totalFee = _feeAmount, ambassadorFeeRatio = feeRatio, ambassadorFee = fee, ambassador = _config.ambassador, action = _action)
    return fee


# transfer revenue to gov


@internal
def _transferRevenueToGov(_asset: address, _amount: uint256, _action: ws.ActionType):
    amount: uint256 = min(_amount, staticcall IERC20(_asset).balanceOf(self))
    if amount == 0:
        return
    governance: address = staticcall UndyHq(addys._getUndyHq()).governance()
    if governance == empty(address):
        return
    assert extcall IERC20(_asset).transfer(governance, amount, default_return_value=True) # dev: transfer failed
    log RevenueTransferredToGov(asset = _asset, amount = amount, action = _action)


###############
# Yield Bonus #
###############


@internal
def _handleYieldBonus(
    _user: address,
    _asset: address,
    _yieldRealized: uint256,
    _config: LootDistroConfig,
    _appraiser: address,
):
    # early return if no bonusAsset (RIPE token) configured
    if empty(address) in [_config.bonusAsset, _asset] or _yieldRealized == 0:
        return

    # get addys (if necessary)
    appraiser: address = _appraiser
    if _appraiser == empty(address):
        appraiser = addys._getAppraiserAddr()

    # convert yield realized to USD value
    usdValue: uint256 = 0
    if _config.underlyingAsset != empty(address):
        underlyingAmount: uint256 = staticcall YieldLego(_config.legoAddr).getUnderlyingAmount(_asset, _yieldRealized)
        usdValue = staticcall Appraiser(appraiser).getUnderlyingUsdValue(_config.underlyingAsset, underlyingAmount)
    else:
        usdValue = staticcall Appraiser(appraiser).getUnderlyingUsdValue(_asset, _yieldRealized)
    if usdValue == 0:
        return

    # convert USD value to RIPE token amount
    bonusAsset: address = _config.bonusAsset # RIPE token
    bonusAssetYieldRealized: uint256 = staticcall Appraiser(appraiser).getAssetAmountFromRipe(bonusAsset, usdValue)

    # no bonus to distribute
    currentBalance: uint256 = staticcall IERC20(bonusAsset).balanceOf(self)
    if bonusAssetYieldRealized == 0 or currentBalance == 0:
        return

    # check deposit rewards asset
    reservedForDepositRewards: uint256 = 0
    depositRewards: DepositRewards = self.depositRewards
    if bonusAsset == depositRewards.asset:
        reservedForDepositRewards = depositRewards.amount

    # user bonus
    if _config.bonusRatio != 0:
        self._handleSpecificYieldBonus(False, bonusAsset, bonusAssetYieldRealized, _config.bonusRatio, _user, currentBalance, reservedForDepositRewards)

    # ambassador bonus
    if _config.ambassador != empty(address) and _config.ambassadorBonusRatio != 0:
        self._handleSpecificYieldBonus(True, bonusAsset, bonusAssetYieldRealized, _config.ambassadorBonusRatio, _config.ambassador, currentBalance, reservedForDepositRewards)


# handle specific yield bonus


@internal
def _handleSpecificYieldBonus(
    _isAmbassador: bool,
    _bonusAsset: address,
    _bonusAssetYieldRealized: uint256,
    _bonusRatio: uint256,
    _recipient: address,
    _currentBalance: uint256,
    _reservedForDepositRewards: uint256,
) -> uint256:
    bonusAmount: uint256 = min(_bonusAssetYieldRealized * _bonusRatio // HUNDRED_PERCENT, _bonusAssetYieldRealized)

    # check what's available for bonus
    availableForBonus: uint256 = 0
    unavailableAmount: uint256 = self.totalClaimableLoot[_bonusAsset] + _reservedForDepositRewards
    if _currentBalance > unavailableAmount:
        availableForBonus = _currentBalance - unavailableAmount

    bonusAmount = min(bonusAmount, availableForBonus)
    if bonusAmount != 0:
        self._addClaimableLootToUser(_recipient, _bonusAsset, bonusAmount)
        log YieldBonusPaid(bonusAsset = _bonusAsset, bonusAmount = bonusAmount, bonusRatio = _bonusRatio, yieldRealized = _bonusAssetYieldRealized, recipient = _recipient, isAmbassador = _isAmbassador)

    return bonusAmount


################################
# Claim Rev Share / Bonus Loot #
################################


@external
def claimRevShareAndBonusLoot(_user: address) -> uint256:
    a: addys.Addys = addys._getAddys()
    assert not deptBasics.isPaused # dev: contract paused

    # permission check
    assert self._validateCanClaimLoot(_user, msg.sender, a.ledger, a.missionControl) # dev: no perms

    # ripe params
    ripeTeller: address = staticcall Registry(RIPE_REGISTRY).getAddr(RIPE_TELLER_ID)
    ripeLockDuration: uint256 = self.ripeLockDuration
    ripeStakeRatio: uint256 = self.ripeStakeRatio

    # claim rev share and bonus loot
    assetsClaimed: uint256 = self._claimRevShareAndBonusLoot(_user, ripeStakeRatio, ripeLockDuration, ripeTeller)
    assert assetsClaimed != 0 # dev: no assets claimed

    self.lastClaim[_user] = block.number
    return assetsClaimed


@internal
def _claimRevShareAndBonusLoot(
    _user: address,
    _ripeStakeRatio: uint256,
    _ripeLockDuration: uint256,
    _ripeTeller: address,
) -> uint256:
    numAssets: uint256 = self.numClaimableAssets[_user]
    if numAssets == 0:
        return 0

    assetsClaimed: uint256 = 0
    assetsToDeregister: DynArray[address, MAX_DEREGISTER_ASSETS] = []

    # iterate through all claimable assets for user
    for i: uint256 in range(1, numAssets, bound=max_value(uint256)):
        asset: address = self.claimableAssets[_user][i]
        if asset == empty(address):
            continue

        didClaim: bool = False
        shouldDeregister: bool = False
        didClaim, shouldDeregister = self._claimLootForAsset(_user, asset, _ripeStakeRatio, _ripeLockDuration, _ripeTeller)
        if didClaim:
            assetsClaimed += 1

        # add to deregister list
        if shouldDeregister and len(assetsToDeregister) < MAX_DEREGISTER_ASSETS:
            assetsToDeregister.append(asset)

    # deregister assets
    if len(assetsToDeregister) != 0:
        for asset: address in assetsToDeregister:
            self._deregisterClaimableAssetForUser(_user, asset)

    return assetsClaimed


# specific asset claim


@internal
def _claimLootForAsset(
    _user: address,
    _asset: address,
    _ripeStakeRatio: uint256,
    _ripeLockDuration: uint256,
    _ripeTeller: address,
) -> (bool, bool):
    claimableAmount: uint256 = self.claimableLoot[_user][_asset]
    if claimableAmount == 0:
        return False, True

    # check contract has enough balance
    transferAmount: uint256 = min(claimableAmount, staticcall IERC20(_asset).balanceOf(self))
    if transferAmount == 0:
        return False, False

    # transfer to user
    if _ripeTeller != empty(address) and _asset == RIPE_TOKEN:
        self._handleRipeRewards(_user, transferAmount, _ripeStakeRatio, _ripeLockDuration, _asset, _ripeTeller)
    else:
        assert extcall IERC20(_asset).transfer(_user, transferAmount, default_return_value=True) # dev: xfer fail

    # update tracking
    self.totalClaimableLoot[_asset] -= transferAmount
    self.claimableLoot[_user][_asset] -= transferAmount

    log LootClaimed(
        user = _user,
        asset = _asset,
        amount = transferAmount,
    )
    return True, claimableAmount == transferAmount


@view
@external
def getClaimableLootForAsset(_user: address, _asset: address) -> uint256:
    claimableAmount: uint256 = self.claimableLoot[_user][_asset]
    return min(claimableAmount, staticcall IERC20(_asset).balanceOf(self))


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


# adjust loot (cheaters!)


@external
def adjustLoot(_user: address, _asset: address, _newClaimable: uint256) -> bool:
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert not deptBasics.isPaused # dev: contract paused

    # invalid inputs
    if empty(address) in [_user, _asset]:
        return False

    # can only adjust down (not up)
    claimableAmount: uint256 = self.claimableLoot[_user][_asset]
    if claimableAmount == 0 or _newClaimable >= claimableAmount:
        return False
    
    # update claimable loot for user
    self.claimableLoot[_user][_asset] = _newClaimable

    # update total claimable loot
    totalClaimableLoot: uint256 = self.totalClaimableLoot[_asset]
    totalClaimableLoot -= claimableAmount
    totalClaimableLoot += _newClaimable
    self.totalClaimableLoot[_asset] = totalClaimableLoot

    # deregister asset if necessary
    if _newClaimable == 0:
        self._deregisterClaimableAssetForUser(_user, _asset)

    log LootAdjusted(user = _user, asset = _asset, newClaimable = _newClaimable)
    return True


#####################
# Loot Registration #
#####################


# add loot to user


@internal
def _addClaimableLootToUser(_user: address, _asset: address, _amount: uint256):
    self.totalClaimableLoot[_asset] += _amount
    self.claimableLoot[_user][_asset] += _amount
    self._registerClaimableAssetForUser(_user, _asset)


# register claimable asset


@internal
def _registerClaimableAssetForUser(_user: address, _asset: address):
    if self.indexOfClaimableAsset[_user][_asset] != 0:
        return

    aid: uint256 = self.numClaimableAssets[_user]
    if aid == 0:
        aid = 1 # not using 0 index
    self.claimableAssets[_user][aid] = _asset
    self.indexOfClaimableAsset[_user][_asset] = aid
    self.numClaimableAssets[_user] = aid + 1


# deregister asset


@internal
def _deregisterClaimableAssetForUser(_user: address, _asset: address) -> bool:
    numAssets: uint256 = self.numClaimableAssets[_user]
    if numAssets == 0:
        return False

    targetIndex: uint256 = self.indexOfClaimableAsset[_user][_asset]
    if targetIndex == 0:
        return False

    # update data
    lastIndex: uint256 = numAssets - 1
    self.numClaimableAssets[_user] = lastIndex
    self.indexOfClaimableAsset[_user][_asset] = 0

    # get last item, replace the removed item
    if targetIndex != lastIndex:
        lastItem: address = self.claimableAssets[_user][lastIndex]
        self.claimableAssets[_user][targetIndex] = lastItem
        self.indexOfClaimableAsset[_user][lastItem] = targetIndex

    return True


##################
# Deposit Points #
##################


# update points


@external
def updateDepositPoints(_user: address):
    a: addys.Addys = addys._getAddys()
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert not deptBasics.isPaused # dev: contract paused
    self._updateDepositPoints(_user, 0, False, a.ledger)


@external
def updateDepositPointsWithNewValue(_user: address, _newUsdValue: uint256):
    ledger: address = addys._getLedgerAddr()
    if not staticcall Ledger(ledger).isUserWallet(msg.sender):
        assert self._isValidWalletConfig(_user, msg.sender, ledger) # dev: invalid config

    # if paused, fail gracefully
    if deptBasics.isPaused:
        return

    self._updateDepositPoints(_user, _newUsdValue, True, ledger)


@external
def updateDepositPointsOnEjection(_user: address):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    if deptBasics.isPaused:
        return
    self._updateDepositPoints(_user, 0, True, addys._getLedgerAddr())


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
    assert not deptBasics.isPaused # dev: contract paused
    a: addys.Addys = addys._getAddys()

    # cannot claim if this is not current loot distributor, likely migrated to new loot distributor
    assert a.lootDistributor == self # dev: not current loot distributor

    # permission check
    assert self._validateCanClaimLoot(_user, msg.sender, a.ledger, a.missionControl) # dev: no perms

    # ripe params
    ripeTeller: address = staticcall Registry(RIPE_REGISTRY).getAddr(RIPE_TELLER_ID)
    ripeLockDuration: uint256 = self.ripeLockDuration
    ripeStakeRatio: uint256 = self.ripeStakeRatio

    # claim rewards
    userRewards: uint256 = self._claimDepositRewards(_user, ripeStakeRatio, ripeLockDuration, ripeTeller, a.ledger)
    assert userRewards != 0 # dev: nothing to claim

    self.lastClaim[_user] = block.number
    return userRewards


@internal
def _claimDepositRewards(
    _user: address,
    _ripeStakeRatio: uint256,
    _ripeLockDuration: uint256,
    _ripeTeller: address,
    _ledger: address,
) -> uint256:
    self._updateDepositPoints(_user, 0, False, _ledger)

    # get user and global points
    userPoints: PointsData = empty(PointsData)
    globalPoints: PointsData = empty(PointsData)
    userPoints, globalPoints = staticcall Ledger(_ledger).getUserAndGlobalPoints(_user)
    if userPoints.depositPoints == 0 or globalPoints.depositPoints == 0:
        return 0

    # check if there is anything available for rewards
    data: DepositRewards = self.depositRewards
    if data.asset == empty(address) or data.amount == 0:
        return 0

    # calculate user's share, transfer to user
    availableRewards: uint256 = min(data.amount, staticcall IERC20(data.asset).balanceOf(self))
    userRewards: uint256 = availableRewards * userPoints.depositPoints // globalPoints.depositPoints
    if userRewards == 0:
        return 0

    # transfer to user
    if _ripeTeller != empty(address) and data.asset == RIPE_TOKEN:
        self._handleRipeRewards(_user, userRewards, _ripeStakeRatio, _ripeLockDuration, data.asset, _ripeTeller)
    else:
        assert extcall IERC20(data.asset).transfer(_user, userRewards, default_return_value=True) # dev: xfer fail

    # save rewards data
    data.amount -= userRewards
    self.depositRewards = data

    # save / update points
    globalPoints.depositPoints -= userPoints.depositPoints
    userPoints.depositPoints = 0
    extcall Ledger(_ledger).setUserAndGlobalPoints(_user, userPoints, globalPoints)

    log DepositRewardsClaimed(
        user = _user,
        asset = data.asset,
        userRewards = userRewards,
        remainingRewards = data.amount,
    )
    return userRewards


@view
@external
def getClaimableDepositRewards(_user: address) -> uint256:
    userPoints: PointsData = empty(PointsData)
    globalPoints: PointsData = empty(PointsData)
    userPoints, globalPoints = staticcall Ledger(addys._getLedgerAddr()).getUserAndGlobalPoints(_user)

    # get latest points
    userPoints.depositPoints += self._getLatestDepositPoints(userPoints.usdValue, userPoints.lastUpdate)
    globalPoints.depositPoints += self._getLatestDepositPoints(globalPoints.usdValue, globalPoints.lastUpdate)
    if userPoints.depositPoints == 0 or globalPoints.depositPoints == 0:
        return 0

    # check if there is anything available for rewards
    data: DepositRewards = self.depositRewards
    if data.asset == empty(address) or data.amount == 0:
        return 0

    # calculate user's share
    availableRewards: uint256 = min(data.amount, staticcall IERC20(data.asset).balanceOf(self))
    userRewards: uint256 = availableRewards * userPoints.depositPoints // globalPoints.depositPoints
    return userRewards


# add rewards


@external
def addDepositRewards(_asset: address, _amount: uint256):
    assert not deptBasics.isPaused # dev: contract paused
    a: addys.Addys = addys._getAddys()
    depositRewardsAsset: address = staticcall MissionControl(a.missionControl).getDepositRewardsAsset() # dev: invalid asset
    assert depositRewardsAsset == _asset # dev: invalid asset

    data: DepositRewards = self.depositRewards
    if data.asset != empty(address) and data.amount != 0:
        # NOTE: if changing the rewards asset, need to recover the previous asset first (zero out the amount)
        assert data.asset == depositRewardsAsset # dev: asset mismatch

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
    assert not deptBasics.isPaused # dev: contract paused
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms

    data: DepositRewards = self.depositRewards
    assert data.asset != empty(address) # dev: nothing to recover
    amount: uint256 = min(data.amount, staticcall IERC20(data.asset).balanceOf(self))
    if amount != 0:
        assert extcall IERC20(data.asset).transfer(_recipient, amount, default_return_value=True) # dev: recovery failed

    self.depositRewards = empty(DepositRewards)
    log DepositRewardsRecovered(asset=data.asset, recipient=_recipient, amount=amount)


# handle ripe rewards


@internal
def _handleRipeRewards(
    _user: address,
    _amount: uint256,
    _ripeStakeRatio: uint256,
    _ripeLockDuration: uint256,
    _ripeToken: address,
    _ripeTeller: address,
):
    # just transfer to user
    if _ripeStakeRatio == 0:
        assert extcall IERC20(_ripeToken).transfer(_user, _amount, default_return_value=True) # dev: xfer fail
        return

    # finalize amounts
    amountToStake: uint256 = min(_amount * _ripeStakeRatio // HUNDRED_PERCENT, _amount)
    amountToSend: uint256 = _amount - amountToStake

    # stake ripe tokens
    if amountToStake != 0:
        assert extcall IERC20(_ripeToken).approve(_ripeTeller, amountToStake, default_return_value=True) # dev: ripe approval failed
        extcall RipeTeller(_ripeTeller).depositIntoGovVault(_ripeToken, amountToStake, _ripeLockDuration, _user)
        assert extcall IERC20(_ripeToken).approve(_ripeTeller, 0, default_return_value=True) # dev: ripe approval failed

    # transfer ripe to user
    if amountToSend != 0:
        amount: uint256 = min(amountToSend, staticcall IERC20(_ripeToken).balanceOf(self))
        assert extcall IERC20(_ripeToken).transfer(_user, amount, default_return_value=True) # dev: ripe transfer failed


####################
# Transaction Fees #
####################


@view
@external
def getSwapFee(_user: address, _tokenIn: address, _tokenOut: address, _missionControl: address = empty(address)) -> uint256:
    # NOTE: passing in `_user` in case we ever have different fees for different users in future

    missionControl: address = _missionControl
    if _missionControl == empty(address):
        missionControl = addys._getMissionControlAddr()

    return staticcall MissionControl(missionControl).getSwapFee(_tokenIn, _tokenOut)


@view
@external
def getRewardsFee(_user: address, _asset: address, _missionControl: address = empty(address)) -> uint256:
    # NOTE: passing in `_user` in case we ever have different fees for different users in future

    missionControl: address = _missionControl
    if _missionControl == empty(address):
        missionControl = addys._getMissionControlAddr()

    return staticcall MissionControl(missionControl).getRewardsFee(_asset)


#############
# Utilities #
#############


# claim ALL loot (both rev share and deposit rewards)


@external
def claimAllLoot(_user: address) -> bool:
    assert not deptBasics.isPaused # dev: contract paused
    a: addys.Addys = addys._getAddys()

    # permission check
    assert self._validateCanClaimLoot(_user, msg.sender, a.ledger, a.missionControl) # dev: no perms

    # ripe params
    ripeTeller: address = staticcall Registry(RIPE_REGISTRY).getAddr(RIPE_TELLER_ID)
    ripeLockDuration: uint256 = self.ripeLockDuration
    ripeStakeRatio: uint256 = self.ripeStakeRatio

    # claim rev share and bonus loot
    numAssetsClaimed: uint256 = self._claimRevShareAndBonusLoot(_user, ripeStakeRatio, ripeLockDuration, ripeTeller)

    # can only claim rewards if this is current loot distributor
    if a.lootDistributor == self:
        userRewards: uint256 = self._claimDepositRewards(_user, ripeStakeRatio, ripeLockDuration, ripeTeller, a.ledger)
        if userRewards != 0:
            numAssetsClaimed += 1

    # only save last claim block if there was something claimed
    if numAssetsClaimed != 0:
        self.lastClaim[_user] = block.number

    return numAssetsClaimed != 0


# validation


@view
@external
def validateCanClaimLoot(_user: address, _caller: address) -> bool:
    a: addys.Addys = addys._getAddys()
    return self._validateCanClaimLoot(_user, _caller, a.ledger, a.missionControl)


@view
@internal
def _validateCanClaimLoot(_user: address, _caller: address, _ledger: address, _missionControl: address) -> bool:
    if not staticcall Ledger(_ledger).isUserWallet(_user):
        return False

    # cool off period
    isSwitchboard: bool = addys._isSwitchboardAddr(_caller)
    if not isSwitchboard:
        lastClaimBlock: uint256 = self.lastClaim[_user]
        coolOffPeriod: uint256 = staticcall MissionControl(_missionControl).getLootClaimCoolOffPeriod()
        if lastClaimBlock != 0 and coolOffPeriod != 0:
            if lastClaimBlock + coolOffPeriod > block.number:
                return False

    # lego check
    if addys._isLegoBookAddr(_caller):
        return True

    # permission check
    walletConfig: address = staticcall UserWallet(_user).walletConfig()
    if _caller == staticcall UserWalletConfig(walletConfig).owner():
        return True

    # manager check
    config: wcs.ManagerSettings = staticcall UserWalletConfig(walletConfig).managerSettings(_caller)
    if config.canClaimLoot:
        return True

    return isSwitchboard


# set ripe rewards config


@external
def setRipeRewardsConfig(_ripeStakeRatio: uint256, _ripeLockDuration: uint256):
    assert not deptBasics.isPaused # dev: contract paused
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert _ripeStakeRatio <= HUNDRED_PERCENT # dev: invalid stake ratio
    assert _ripeLockDuration > 0 # dev: invalid lock duration
    self.ripeStakeRatio = _ripeStakeRatio
    self.ripeLockDuration = _ripeLockDuration
    log RipeRewardsConfigSet(ripeStakeRatio=_ripeStakeRatio, ripeLockDuration=_ripeLockDuration)