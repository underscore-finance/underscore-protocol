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
    def getUserWalletAssetConfig(_asset: address) -> WalletAssetConfig: view
    def getRewardsFee(_user: address, _asset: address) -> uint256: view
    def getSwapFee(_user: address, _asset: address) -> uint256: view
    def feeRecipient() -> address: view

interface Ledger:
    def setUserWalletData(_user: address, _data: UserWalletData): nonpayable
    def userWalletData(_user: address) -> UserWalletData: view
    def getLastTotalUsdValue(_user: address) -> uint256: view
    def isUserWallet(_user: address) -> bool: view

interface UserWallet:
    def updateAssetData(_asset: address, _shouldCheckYield: bool, _lastTotalUsdValue: uint256, _feeRecipient: address) -> uint256: nonpayable

interface RipePriceDesk:
    def getPrice(_asset: address, _shouldRaise: bool = False) -> uint256: view

interface Switchboard:
    def isSwitchboardAddr(_addr: address) -> bool: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

interface LegoBook:
    def isLegoAddr(_addr: address) -> bool: view

struct UserWalletData:
    usdValue: uint256
    depositPoints: uint256
    lastUpdate: uint256
    ambassador: address

struct WalletAssetConfig:
    hasConfig: bool
    isYieldAsset: bool
    isRebasing: bool
    maxYieldIncrease: uint256
    yieldProfitFee: uint256
    decimals: uint256
    stalePriceNumBlocks: uint256

struct BackpackData:
    legoBook: address
    feeRecipient: address
    lastTotalUsdValue: uint256

struct LastPrice:
    price: uint256
    lastUpdate: uint256

# price cache
lastPrice: public(HashMap[address, LastPrice]) # asset -> last price

LEDGER_ID: constant(uint256) = 2
MISSION_CONTROL_ID: constant(uint256) = 3
LEGO_BOOK_ID: constant(uint256) = 4

RIPE_PRICE_DESK_ID: constant(uint256) = 7
RIPE_HQ: immutable(address)


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


##################
# Deposit Points #
##################


# user deposit points


@external
def updateUserDepositPoints() -> uint256:
    ledger: address = addys._getLedgerAddr()
    assert staticcall Ledger(ledger).isUserWallet(msg.sender) # dev: not a user wallet
    return self._updateUserDepositPoints(msg.sender, ledger)


@internal
def _updateUserDepositPoints(_user: address, _ledger: address) -> uint256:
    data: UserWalletData = staticcall Ledger(_ledger).userWalletData(_user)

    # nothing to do here -- `lastUpdate` will be saved in `_performPostActionTasks`
    if data.usdValue == 0 or data.lastUpdate == 0 or block.number <= data.lastUpdate:
        return data.usdValue

    newDepositPoints: uint256 = data.usdValue * (block.number - data.lastUpdate)
    data.depositPoints += newDepositPoints
    data.lastUpdate = block.number
    extcall Ledger(_ledger).setUserWalletData(_user, data)

    return data.usdValue


# update global deposit points


@external
def updateGlobalDepositPoints(_prevTotalUsdValue: uint256, _newTotalUsdValue: uint256):
    ledger: address = addys._getLedgerAddr()
    assert staticcall Ledger(ledger).isUserWallet(msg.sender) # dev: not a user wallet
    self._updateGlobalDepositPoints(_prevTotalUsdValue, _newTotalUsdValue, ledger)


@internal
def _updateGlobalDepositPoints(_prevTotalUsdValue: uint256, _newTotalUsdValue: uint256, _ledger: address):
    # need `totalUsdValue` for global points
    # TODO: implement this -- only call if prevUsdValue != _newUsdValue
    pass


# update points + trial funds


@external
def performPostActionTasks(_prevTotalUsdValue: uint256, _newTotalUsdValue: uint256):
    ledger: address = addys._getLedgerAddr()
    assert staticcall Ledger(ledger).isUserWallet(msg.sender) # dev: not a user wallet

    # check trial funds
    assert self._doesWalletStillHaveTrialFunds(msg.sender) # dev: user no longer has trial funds

    # update global points
    self._updateGlobalDepositPoints(_prevTotalUsdValue, _newTotalUsdValue, ledger)


################
# Update Asset #
################


@external
def updateAssetInWallet(_userWallet: address, _asset: address, _shouldCheckYield: bool):
    a: addys.Addys = addys._getAddys()
    assert staticcall Switchboard(a.switchboard).isSwitchboardAddr(msg.sender) # dev: no perms

    # first, update user deposit points
    prevTotalUsdValue: uint256 = self._updateUserDepositPoints(msg.sender, a.ledger)

    # update asset data in user wallet
    feeRecipient: address = staticcall MissionControl(a.missionControl).feeRecipient()
    newTotalUsdValue: uint256 = extcall UserWallet(_userWallet).updateAssetData(_asset, _shouldCheckYield, prevTotalUsdValue, feeRecipient)

    # then, update global deposit points
    self._updateGlobalDepositPoints(prevTotalUsdValue, newTotalUsdValue, a.ledger)


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
def getUserWalletAssetConfig(_asset: address) -> WalletAssetConfig:
    return staticcall MissionControl(addys._getMissionControlAddr()).getUserWalletAssetConfig(_asset)


@view
@external
def getRewardsFee(_user: address, _asset: address) -> uint256:
    return staticcall MissionControl(addys._getMissionControlAddr()).getRewardsFee(_user, _asset)


@view
@external
def getSwapFee(_user: address, _asset: address) -> uint256:
    return staticcall MissionControl(addys._getMissionControlAddr()).getSwapFee(_user, _asset)


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
def _getPrice(_asset: address, _isYieldAsset: bool, _staleBlocks: uint256) -> (LastPrice, bool):
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
def updateAndGetPriceFromWallet(
    _asset: address,
    _isYieldAsset: bool,
    _staleBlocks: uint256,
) -> uint256:
    assert staticcall Ledger(addys._getLedgerAddr()).isUserWallet(msg.sender) # dev: no perms

    if _asset == empty(address):
        return 0

    # get latest price
    data: LastPrice = empty(LastPrice)
    didPriceChange: bool = False
    data, didPriceChange = self._getPrice(_asset, _isYieldAsset, _staleBlocks)

    # only save if price changed
    if didPriceChange:
        self.lastPrice[_asset] = data

    return data.price


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
