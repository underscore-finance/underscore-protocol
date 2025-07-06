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

from ethereum.ercs import IERC20
from ethereum.ercs import IERC20Detailed

interface Ledger:
    def ambassadors(_user: address) -> address: view
    def isUserWallet(_user: address) -> bool: view

interface MissionControl:
    def getAmbassadorConfig(_ambassador: address, _asset: address, _isYieldProfit: bool) -> AmbassadorConfig: view

interface Appraiser:
    def getPricePerShare(_asset: address) -> uint256: view

interface UserWallet:
    def walletConfig() -> address: view

interface UserWalletConfig:
    def owner() -> address: view

struct AmbassadorConfig:
    ambassador: address
    ambassadorFeeRatio: AmbassadorFees
    ambassadorBonusRatio: uint256
    underlyingAsset: address
    decimals: uint256

struct AmbassadorFees:
    swapFee: uint256
    rewardsFee: uint256
    yieldProfitFee: uint256

event LootClaimed:
    user: indexed(address)
    asset: indexed(address)
    amount: uint256

# claimable loot
totalClaimableLoot: public(HashMap[address, uint256]) # asset -> amount
claimableLoot: public(HashMap[address, HashMap[address, uint256]]) # ambassador -> asset -> amount

# ambassador claimable loot
claimableAssets: public(HashMap[address, HashMap[uint256, address]]) # ambassador -> index -> asset
indexOfClaimableAsset: public(HashMap[address, HashMap[address, uint256]]) # ambassador -> asset -> index
numClaimableAssets: public(HashMap[address, uint256]) # ambassador -> num assets

HUNDRED_PERCENT: constant(uint256) = 100_00 # 100.00%


@deploy
def __init__(_undyHq: address):
    addys.__init__(_undyHq)
    deptBasics.__init__(False, False) # no minting


####################
# Transaction Fees #
####################


# normal fee flow (swaps, rewards)


@external
def addLootFromSwapOrRewards(_asset: address, _feeAmount: uint256, _action: wi.ActionType):
    ledger: address = addys._getLedgerAddr()
    assert staticcall Ledger(ledger).isUserWallet(msg.sender) # dev: not a user wallet

    # finalize amount
    feeAmount: uint256 = min(_feeAmount, staticcall IERC20(_asset).balanceOf(msg.sender))
    if feeAmount == 0:
        return
    assert extcall IERC20(_asset).transferFrom(msg.sender, self, feeAmount, default_return_value=True) # dev: transfer failed

    config: AmbassadorConfig = self._getAmbassadorConfig(msg.sender, _asset, False, ledger)
    if config.ambassador != empty(address):
        self._handleTransactionFeeForAmbassador(_asset, feeAmount, _action, config)


# yield profit flow


@external
def addLootFromYieldProfit(_asset: address, _feeAmount: uint256, _totalYieldAmount: uint256):
    ledger: address = addys._getLedgerAddr()
    assert staticcall Ledger(ledger).isUserWallet(msg.sender) # dev: not a user wallet

    config: AmbassadorConfig = self._getAmbassadorConfig(msg.sender, _asset, True, ledger)
    if config.ambassador == empty(address):
        return
    
    # handle fee (this may be 0) -- no need to `transferFrom` in this case, it's already in this contract
    if _feeAmount != 0:
        self._handleTransactionFeeForAmbassador(_asset, _feeAmount, empty(wi.ActionType), config)

    # handle yield ambassador bonus
    if config.ambassadorBonusRatio != 0 and config.underlyingAsset != empty(address):
        self._handleYieldAmbassadorBonus(_asset, _totalYieldAmount, config)


# transaction fees


@internal
def _handleTransactionFeeForAmbassador(
    _asset: address,
    _feeAmount: uint256,
    _action: wi.ActionType,
    _config: AmbassadorConfig,
):
    feeRatio: uint256 = _config.ambassadorFeeRatio.yieldProfitFee
    if _action == wi.ActionType.SWAP:
        feeRatio = _config.ambassadorFeeRatio.swapFee
    elif _action == wi.ActionType.REWARDS:
        feeRatio = _config.ambassadorFeeRatio.rewardsFee

    # finalize fee
    ambassadorRatio: uint256 = min(feeRatio, HUNDRED_PERCENT)
    fee: uint256 = min(_feeAmount * ambassadorRatio // HUNDRED_PERCENT, staticcall IERC20(_asset).balanceOf(self))
    if fee != 0:
        self._addClaimableLootToAmbassador(_config.ambassador, _asset, fee)


# get ambassador config


@view
@internal
def _getAmbassadorConfig(
    _wallet: address,
    _asset: address,
    _isYieldProfit: bool,
    _ledger: address,
) -> AmbassadorConfig:
    ambassador: address = staticcall Ledger(_ledger).ambassadors(_wallet)
    if ambassador == empty(address):
        return empty(AmbassadorConfig)
    return staticcall MissionControl(addys._getMissionControlAddr()).getAmbassadorConfig(ambassador, _asset, _isYieldProfit)
    

####################
# Ambassador Bonus #
####################


@internal
def _handleYieldAmbassadorBonus(
    _asset: address,
    _totalYieldAmount: uint256,
    _config: AmbassadorConfig,
):
    bonusRatio: uint256 = min(_config.ambassadorBonusRatio, HUNDRED_PERCENT)
    bonusAmount: uint256 = _totalYieldAmount * bonusRatio // HUNDRED_PERCENT

    pricePerShare: uint256 = staticcall Appraiser(addys._getAppraiserAddr()).getPricePerShare(_asset)
    if pricePerShare == 0:
        return

    decimals: uint256 = _config.decimals
    if decimals == 0:
        decimals = convert(staticcall IERC20Detailed(_asset).decimals(), uint256)

    # how much is available for bonus
    availableForBonus: uint256 = 0
    currentBalance: uint256 = staticcall IERC20(_config.underlyingAsset).balanceOf(self)
    totalClaimable: uint256 = self.totalClaimableLoot[_config.underlyingAsset]
    if currentBalance > totalClaimable:
        availableForBonus = currentBalance - totalClaimable

    underlyingAmount: uint256 = min(bonusAmount * pricePerShare // (10 ** decimals), availableForBonus)
    if underlyingAmount != 0:
        self._addClaimableLootToAmbassador(_config.ambassador, _config.underlyingAsset, underlyingAmount)


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
    if numAssets == 0:
        return 0

    assetsClaimed: uint256 = 0

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

        log LootClaimed(
            user = _user,
            asset = asset,
            amount = transferAmount
        )
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
