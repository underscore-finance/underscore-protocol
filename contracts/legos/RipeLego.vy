#         _____   ____     _____       ______          ____            ______        _____           _____    
#     ___|\    \ |    |___|\    \  ___|\     \        |    |       ___|\     \   ___|\    \     ____|\    \   
#    |    |\    \|    |    |\    \|     \     \       |    |      |     \     \ /    /\    \   /     /\    \  
#    |    | |    |    |    | |    |     ,_____/|      |    |      |     ,_____/|    |  |____| /     /  \    \ 
#    |    |/____/|    |    |/____/|     \--'\_|/      |    |  ____|     \--'\_|/    |    ____|     |    |    |
#    |    |\    \|    |    ||    ||     /___/|        |    | |    |     /___/| |    |   |    |     |    |    |
#    |    | |    |    |    ||____|/     \____|\       |    | |    |     \____|\|    |   |_,  |\     \  /    /|
#    |____| |____|____|____|      |____ '     /|      |____|/____/|____ '     /|\ ___\___/  /| \_____\/____/ |
#    |    | |    |    |    |      |    /_____/ |      |    |     ||    /_____/ | |   /____ / |\ |    ||    | /
#    |____| |____|____|____|      |____|     | /      |____|_____|/____|     | /\|___|    | /  \|____||____|/ 
#      \(     )/   \(   \(          \( |_____|/         \(    )/    \( |_____|/   \( |____|/      \(    )/    
#       '     '     '    '           '    )/             '    '      '    )/       '   )/          '    '     
#                                         '                               '            '                      
#     ╔═════════════════════════════════════════╗
#     ║  ** Ripe Lego **                        ║
#     ║  Integration with Ripe Protocol.        ║
#     ╚═════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

implements: Lego
implements: YieldLego

exports: addys.__interface__
exports: yld.__interface__

initializes: addys
initializes: yld[addys := addys]

from interfaces import LegoPartner as Lego
from interfaces import YieldLego as YieldLego
from interfaces import WalletStructs as ws

import contracts.modules.Addys as addys
import contracts.modules.YieldLegoData as yld

from ethereum.ercs import IERC20Detailed
from ethereum.ercs import IERC20
from ethereum.ercs import IERC4626

interface RipeTeller:
    def repay(_paymentAmount: uint256 = max_value(uint256), _user: address = msg.sender, _isPaymentSavingsGreen: bool = False, _shouldRefundSavingsGreen: bool = True) -> bool: nonpayable
    def withdraw(_asset: address, _amount: uint256 = max_value(uint256), _user: address = msg.sender, _vaultAddr: address = empty(address), _vaultId: uint256 = 0) -> uint256: nonpayable
    def deposit(_asset: address, _amount: uint256 = max_value(uint256), _user: address = msg.sender, _vaultAddr: address = empty(address), _vaultId: uint256 = 0) -> uint256: nonpayable
    def depositIntoGovVault(_asset: address, _amount: uint256, _lockDuration: uint256, _user: address = msg.sender) -> uint256: nonpayable
    def borrow(_greenAmount: uint256 = max_value(uint256), _user: address = msg.sender, _wantsSavingsGreen: bool = True, _shouldEnterStabPool: bool = False) -> uint256: nonpayable
    def claimLoot(_user: address = msg.sender, _shouldStake: bool = True) -> uint256: nonpayable

interface RipeRegistry:
    def getAddr(_regId: uint256) -> address: view
    def savingsGreen() -> address: view
    def greenToken() -> address: view
    def ripeToken() -> address: view

interface Ledger:
    def setVaultToken(_vaultToken: address, _legoId: uint256, _underlyingAsset: address, _decimals: uint256, _isRebasing: bool): nonpayable
    def isRegisteredVaultToken(_vaultToken: address) -> bool: view
    def isUserWallet(_user: address) -> bool: view

interface Appraiser:
    def getUsdValue(_asset: address, _amount: uint256, _missionControl: address = empty(address), _legoBook: address = empty(address), _ledger: address = empty(address)) -> uint256: view
    def updatePriceAndGetUsdValue(_asset: address, _amount: uint256, _missionControl: address = empty(address), _legoBook: address = empty(address)) -> uint256: nonpayable

interface RipeMissionControl:
    def doesUndyLegoHaveAccess(_wallet: address, _legoAddr: address) -> bool: view

interface UndyRegistry:
    def getRegId(_addr: address) -> uint256: view

event RipeCollateralDeposit:
    sender: indexed(address)
    asset: indexed(address)
    assetAmountDeposited: uint256
    vaultIdOrLock: uint256
    usdValue: uint256
    recipient: address

event RipeCollateralWithdrawal:
    sender: indexed(address)
    asset: indexed(address)
    assetAmountReceived: uint256
    vaultId: uint256
    usdValue: uint256
    recipient: address

event RipeBorrow:
    sender: indexed(address)
    asset: indexed(address)
    assetAmountBorrowed: uint256
    usdValue: uint256
    recipient: address

event RipeRepay:
    sender: indexed(address)
    asset: indexed(address)
    assetAmountRepaid: uint256
    usdValue: uint256
    recipient: address

event RipeClaimRewards:
    sender: indexed(address)
    asset: indexed(address)
    ripeClaimed: uint256
    usdValue: uint256
    recipient: address

event RipeSavingsGreenDeposit:
    sender: indexed(address)
    asset: indexed(address)
    vaultToken: indexed(address)
    assetAmountDeposited: uint256
    usdValue: uint256
    vaultTokenAmountReceived: uint256
    recipient: address

event RipeSavingsGreenWithdrawal:
    sender: indexed(address)
    asset: indexed(address)
    vaultToken: indexed(address)
    assetAmountReceived: uint256
    usdValue: uint256
    vaultTokenAmountBurned: uint256
    recipient: address

# ripe addrs
RIPE_REGISTRY: public(immutable(address))
RIPE_GREEN_TOKEN: public(immutable(address))
RIPE_SAVINGS_GREEN: public(immutable(address))
RIPE_TOKEN: public(immutable(address))

RIPE_MISSION_CONTROL_ID: constant(uint256) = 5
RIPE_LOOTBOX_ID: constant(uint256) = 16
RIPE_TELLER_ID: constant(uint256) = 17

LEGO_ACCESS_ABI: constant(String[64]) = "setUndyLegoAccess(address)"
MAX_TOKEN_PATH: constant(uint256) = 5


@deploy
def __init__(
    _undyHq: address,
    _ripeRegistry: address,
):
    addys.__init__(_undyHq)
    yld.__init__(False)

    assert _ripeRegistry != empty(address) # dev: invalid ripe registry
    RIPE_REGISTRY = _ripeRegistry
    RIPE_GREEN_TOKEN = staticcall RipeRegistry(RIPE_REGISTRY).greenToken()
    RIPE_SAVINGS_GREEN = staticcall RipeRegistry(RIPE_REGISTRY).savingsGreen()
    RIPE_TOKEN = staticcall RipeRegistry(RIPE_REGISTRY).ripeToken()


@view
@external
def hasCapability(_action: ws.ActionType) -> bool:
    return _action in (
        ws.ActionType.EARN_DEPOSIT | 
        ws.ActionType.EARN_WITHDRAW |
        ws.ActionType.ADD_COLLATERAL |
        ws.ActionType.REMOVE_COLLATERAL |
        ws.ActionType.BORROW |
        ws.ActionType.REPAY_DEBT |
        ws.ActionType.REWARDS
    )


@view
@external
def getRegistries() -> DynArray[address, 10]:
    return [RIPE_REGISTRY]


@view
@external
def getAccessForLego(_user: address, _action: ws.ActionType) -> (address, String[64], uint256):
    ripeHq: address = RIPE_REGISTRY

    mc: address = staticcall RipeRegistry(ripeHq).getAddr(RIPE_MISSION_CONTROL_ID)
    if staticcall RipeMissionControl(mc).doesUndyLegoHaveAccess(_user, self):
        return empty(address), empty(String[64]), 0

    else:
        teller: address = staticcall RipeRegistry(ripeHq).getAddr(RIPE_TELLER_ID)
        return teller, LEGO_ACCESS_ABI, 1


@view
@external
def isYieldLego() -> bool:
    return True # Savings Green


@view
@external
def isDexLego() -> bool:
    return False


###################
# Debt Management #
###################


# add collateral on Ripe


@external
def addCollateral(
    _asset: address,
    _amount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    assert not yld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = yld._getMiniAddys(_miniAddys)

    # only allowing user wallets to do this
    assert self._isUserWallet(msg.sender) # dev: not a user wallet
    assert msg.sender == _recipient # dev: recipient must be caller

    # pre balances
    preLegoBalance: uint256 = staticcall IERC20(_asset).balanceOf(self)

    # transfer deposit asset to this contract
    depositAmount: uint256 = min(_amount, staticcall IERC20(_asset).balanceOf(msg.sender))
    assert depositAmount != 0 # dev: nothing to transfer
    assert extcall IERC20(_asset).transferFrom(msg.sender, self, depositAmount, default_return_value=True) # dev: transfer failed

    vaultIdOrLock: uint256 = 0
    if _extraData != empty(bytes32):
        vaultIdOrLock = convert(_extraData, uint256)

    # deposit into Ripe Protocol
    teller: address = self._getRipeTellerAndApprove(_asset)
    if _asset == RIPE_TOKEN:
        depositAmount = extcall RipeTeller(teller).depositIntoGovVault(_asset, depositAmount, vaultIdOrLock, _recipient)
    else:
        depositAmount = extcall RipeTeller(teller).deposit(_asset, depositAmount, _recipient, empty(address), vaultIdOrLock)
    self._resetTellerApproval(_asset, teller)

    # refund if full deposit didn't get through
    currentLegoBalance: uint256 = staticcall IERC20(_asset).balanceOf(self)
    refundAssetAmount: uint256 = 0
    if currentLegoBalance > preLegoBalance:
        refundAssetAmount = currentLegoBalance - preLegoBalance
        assert extcall IERC20(_asset).transfer(msg.sender, refundAssetAmount, default_return_value=True) # dev: transfer failed

    usdValue: uint256 = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(_asset, depositAmount, miniAddys.missionControl, miniAddys.legoBook)
    log RipeCollateralDeposit(
        sender = msg.sender,
        asset = _asset,
        assetAmountDeposited = depositAmount,
        vaultIdOrLock = vaultIdOrLock,
        usdValue = usdValue,
        recipient = _recipient,
    )
    return depositAmount, usdValue


# remove collateral on ripe


@external
def removeCollateral(
    _asset: address,
    _amount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    assert not yld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = yld._getMiniAddys(_miniAddys)

    # only allowing user wallets to do this
    assert self._isUserWallet(msg.sender) # dev: not a user wallet
    assert msg.sender == _recipient # dev: recipient must be caller

    vaultId: uint256 = 0
    if _extraData != empty(bytes32):
        vaultId = convert(_extraData, uint256)

    # withdraw from Ripe Protocol
    teller: address = staticcall RipeRegistry(RIPE_REGISTRY).getAddr(RIPE_TELLER_ID)
    amountRemoved: uint256 = extcall RipeTeller(teller).withdraw(_asset, _amount, _recipient, empty(address), vaultId)
    assert amountRemoved != 0 # dev: no asset amount received

    usdValue: uint256 = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(_asset, amountRemoved, miniAddys.missionControl, miniAddys.legoBook)
    log RipeCollateralWithdrawal(
        sender = msg.sender,
        asset = _asset,
        assetAmountReceived = amountRemoved,
        vaultId = vaultId,
        usdValue = usdValue,
        recipient = _recipient,
    )
    return amountRemoved, usdValue


# borrow


@external
def borrow(
    _borrowAsset: address,
    _amount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    assert not yld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = yld._getMiniAddys(_miniAddys)

    # only allowing user wallets to do this
    assert self._isUserWallet(msg.sender) # dev: not a user wallet
    assert msg.sender == _recipient # dev: recipient must be caller

    assert _borrowAsset in [RIPE_GREEN_TOKEN, RIPE_SAVINGS_GREEN] # dev: invalid borrow asset
    wantsSavingsGreen: bool = _borrowAsset == RIPE_SAVINGS_GREEN

    # borrow from Ripe
    teller: address = staticcall RipeRegistry(RIPE_REGISTRY).getAddr(RIPE_TELLER_ID)
    borrowAmount: uint256 = extcall RipeTeller(teller).borrow(_amount, _recipient, wantsSavingsGreen, False)
    assert borrowAmount != 0 # dev: no borrow amount received

    usdValue: uint256 = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(_borrowAsset, borrowAmount, miniAddys.missionControl, miniAddys.legoBook)
    log RipeBorrow(
        sender = msg.sender,
        asset = _borrowAsset,
        assetAmountBorrowed = borrowAmount,
        usdValue = usdValue,
        recipient = _recipient,
    )
    return borrowAmount, usdValue


# repay debt


@external
def repayDebt(
    _paymentAsset: address,
    _paymentAmount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    assert not yld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = yld._getMiniAddys(_miniAddys)

    # only allowing user wallets to do this
    assert self._isUserWallet(msg.sender) # dev: not a user wallet
    assert msg.sender == _recipient # dev: recipient must be caller

    assert _paymentAsset in [RIPE_GREEN_TOKEN, RIPE_SAVINGS_GREEN] # dev: invalid payment asset
    isPaymentSavingsGreen: bool = _paymentAsset == RIPE_SAVINGS_GREEN

    # pre balances
    preLegoBalance: uint256 = staticcall IERC20(_paymentAsset).balanceOf(self)

    # transfer deposit asset to this contract
    paymentAmount: uint256 = min(_paymentAmount, staticcall IERC20(_paymentAsset).balanceOf(msg.sender))
    assert paymentAmount != 0 # dev: nothing to transfer
    assert extcall IERC20(_paymentAsset).transferFrom(msg.sender, self, paymentAmount, default_return_value=True) # dev: transfer failed

    # deposit into Ripe Protocol
    teller: address = self._getRipeTellerAndApprove(_paymentAsset)
    extcall RipeTeller(teller).repay(paymentAmount, _recipient, isPaymentSavingsGreen, True)
    self._resetTellerApproval(_paymentAsset, teller)

    # refund if full deposit didn't get through
    currentLegoBalance: uint256 = staticcall IERC20(_paymentAsset).balanceOf(self)
    refundAssetAmount: uint256 = 0
    if currentLegoBalance > preLegoBalance:
        refundAssetAmount = currentLegoBalance - preLegoBalance
        assert extcall IERC20(_paymentAsset).transfer(msg.sender, refundAssetAmount, default_return_value=True) # dev: transfer failed

    usdValue: uint256 = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(_paymentAsset, paymentAmount, miniAddys.missionControl, miniAddys.legoBook)
    log RipeRepay(
        sender = msg.sender,
        asset = _paymentAsset,
        assetAmountRepaid = paymentAmount,
        usdValue = usdValue,
        recipient = _recipient,
    )
    return paymentAmount, usdValue


# shared utils


@internal
def _getRipeTellerAndApprove(_asset: address) -> address:
    teller: address = staticcall RipeRegistry(RIPE_REGISTRY).getAddr(RIPE_TELLER_ID)
    # some vault tokens require max value approval (comp v3)
    assert extcall IERC20(_asset).approve(teller, max_value(uint256), default_return_value = True) # dev: appr
    return teller


@internal
def _resetTellerApproval(_asset: address, _teller: address):
    if _teller != empty(address):
        assert extcall IERC20(_asset).approve(_teller, 0, default_return_value = True) # dev: approval failed


@view
@internal
def _isUserWallet(_user: address) -> bool:
    return staticcall Ledger(addys._getLedgerAddr()).isUserWallet(_user)


#################
# Claim Rewards #
#################


@external
def claimRewards(
    _user: address,
    _rewardToken: address,
    _rewardAmount: uint256,
    _extraData: bytes32,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    assert not yld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = yld._getMiniAddys(_miniAddys)

    # NOTE: not checking isUserWallet -- Ripe's Endaoment needs to be able to call this
    assert msg.sender == _user # dev: recipient must be caller

    assert _rewardToken == RIPE_TOKEN # dev: invalid reward token

    teller: address = staticcall RipeRegistry(RIPE_REGISTRY).getAddr(RIPE_TELLER_ID)
    totalRipe: uint256 = extcall RipeTeller(teller).claimLoot(_user, True)
    assert totalRipe != 0 # dev: no ripe tokens received

    usdValue: uint256 = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(_rewardToken, totalRipe, miniAddys.missionControl, miniAddys.legoBook)
    log RipeClaimRewards(
        sender = msg.sender,
        asset = _rewardToken,
        ripeClaimed = totalRipe,
        usdValue = usdValue,
        recipient = _user,
    )
    return 0, usdValue


#################
# Savings Green #
#################


# deposit


@external
def depositForYield(
    _asset: address,
    _amount: uint256,
    _vaultAddr: address,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, address, uint256, uint256):
    assert not yld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = yld._getMiniAddys(_miniAddys)

    # verify vault token (register if necessary)
    vaultToken: address = self._getVaultTokenOnDeposit(_asset, _vaultAddr, miniAddys.ledger, miniAddys.legoBook)

    # pre balances
    preLegoBalance: uint256 = staticcall IERC20(_asset).balanceOf(self)

    # transfer deposit asset to this contract
    depositAmount: uint256 = min(_amount, staticcall IERC20(_asset).balanceOf(msg.sender))
    assert depositAmount != 0 # dev: nothing to transfer
    assert extcall IERC20(_asset).transferFrom(msg.sender, self, depositAmount, default_return_value=True) # dev: transfer failed

    # deposit assets into lego partner
    vaultTokenAmountReceived: uint256 = extcall IERC4626(vaultToken).deposit(depositAmount, _recipient)
    assert vaultTokenAmountReceived != 0 # dev: no vault tokens received

    # refund if full deposit didn't get through
    currentLegoBalance: uint256 = staticcall IERC20(_asset).balanceOf(self)
    refundAssetAmount: uint256 = 0
    if currentLegoBalance > preLegoBalance:
        refundAssetAmount = currentLegoBalance - preLegoBalance
        assert extcall IERC20(_asset).transfer(msg.sender, refundAssetAmount, default_return_value=True) # dev: transfer failed
        depositAmount -= refundAssetAmount

    usdValue: uint256 = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(_asset, depositAmount, miniAddys.missionControl, miniAddys.legoBook)
    log RipeSavingsGreenDeposit(
        sender = msg.sender,
        asset = _asset,
        vaultToken = vaultToken,
        assetAmountDeposited = depositAmount,
        usdValue = usdValue,
        vaultTokenAmountReceived = vaultTokenAmountReceived,
        recipient = _recipient,
    )
    return depositAmount, vaultToken, vaultTokenAmountReceived, usdValue


# validate green / sgreen tokens


@internal
def _getVaultTokenOnDeposit(_asset: address, _vaultAddr: address, _ledger: address, _legoBook: address) -> address:
    assert _vaultAddr == RIPE_SAVINGS_GREEN # dev: must be savings green
    assert _asset == RIPE_GREEN_TOKEN # dev: must be green token

    # register if necessary
    if yld.vaultToAsset[_vaultAddr] == empty(address):
        self._registerAsset(_asset, _vaultAddr)
        self._updateLedgerVaultToken(_asset, _vaultAddr, _ledger, _legoBook)

    return _vaultAddr


# withdraw


@external
def withdrawFromYield(
    _vaultToken: address,
    _amount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, address, uint256, uint256):
    assert not yld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = yld._getMiniAddys(_miniAddys)

    # verify asset (register if necessary)
    asset: address = self._getAssetOnWithdraw(_vaultToken, miniAddys.ledger, miniAddys.legoBook)

    # pre balances
    preLegoVaultBalance: uint256 = staticcall IERC20(_vaultToken).balanceOf(self)

    # transfer vaults tokens to this contract
    vaultTokenAmount: uint256 = min(_amount, staticcall IERC20(_vaultToken).balanceOf(msg.sender))
    assert vaultTokenAmount != 0 # dev: nothing to transfer
    assert extcall IERC20(_vaultToken).transferFrom(msg.sender, self, vaultTokenAmount, default_return_value=True) # dev: transfer failed

    # withdraw assets from lego partner
    assetAmountReceived: uint256 = extcall IERC4626(_vaultToken).redeem(vaultTokenAmount, _recipient, self)
    assert assetAmountReceived != 0 # dev: no asset amount received

    # refund if full withdrawal didn't happen
    currentLegoVaultBalance: uint256 = staticcall IERC20(_vaultToken).balanceOf(self)
    refundVaultTokenAmount: uint256 = 0
    if currentLegoVaultBalance > preLegoVaultBalance:
        refundVaultTokenAmount = currentLegoVaultBalance - preLegoVaultBalance
        assert extcall IERC20(_vaultToken).transfer(msg.sender, refundVaultTokenAmount, default_return_value=True) # dev: transfer failed
        vaultTokenAmount -= refundVaultTokenAmount

    usdValue: uint256 = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(asset, assetAmountReceived, miniAddys.missionControl, miniAddys.legoBook)
    log RipeSavingsGreenWithdrawal(
        sender = msg.sender,
        asset = asset,
        vaultToken = _vaultToken,
        assetAmountReceived = assetAmountReceived,
        usdValue = usdValue,
        vaultTokenAmountBurned = vaultTokenAmount,
        recipient = _recipient,
    )
    return vaultTokenAmount, asset, assetAmountReceived, usdValue


# vault token verification


@internal
def _getAssetOnWithdraw(_vaultToken: address, _ledger: address, _legoBook: address) -> address:
    assert _vaultToken == RIPE_SAVINGS_GREEN # dev: must be savings green
    asset: address = RIPE_GREEN_TOKEN

    # register if necessary
    if yld.vaultToAsset[_vaultToken] == empty(address):
        self._registerAsset(asset, _vaultToken)
        self._updateLedgerVaultToken(asset, _vaultToken, _ledger, _legoBook)

    return asset


#######################
# Savings Green Utils #
#######################


@view
@external
def isRebasing() -> bool:
    return self._isRebasing()


@view
@internal
def _isRebasing() -> bool:
    return False


@view
@external
def isEligibleVaultForTrialFunds(_vaultToken: address, _underlyingAsset: address) -> bool:
    return False


@view
@external
def isEligibleForYieldBonus(_asset: address) -> bool:
    # likely already giving away RIPE tokens, not allowing sGREEN to have bonus
    return False


# underlying asset


@view
@external
def isVaultToken(_vaultToken: address) -> bool:
    return self._isVaultToken(_vaultToken)


@view
@internal
def _isVaultToken(_vaultToken: address) -> bool:
    return _vaultToken == RIPE_SAVINGS_GREEN


@view
@external
def getUnderlyingAsset(_vaultToken: address) -> address:
    return self._getUnderlyingAsset(_vaultToken)


@view
@internal
def _getUnderlyingAsset(_vaultToken: address) -> address:
    if _vaultToken != RIPE_SAVINGS_GREEN:
        return empty(address)
    return RIPE_GREEN_TOKEN


# underlying amount


@view
@external
def getUnderlyingAmount(_vaultToken: address, _vaultTokenAmount: uint256) -> uint256:
    if not self._isVaultToken(_vaultToken) or _vaultTokenAmount == 0:
        return 0 # invalid vault token or amount
    return self._getUnderlyingAmount(_vaultToken, _vaultTokenAmount)


@view
@internal
def _getUnderlyingAmount(_vaultToken: address, _vaultTokenAmount: uint256) -> uint256:
    return staticcall IERC4626(_vaultToken).convertToAssets(_vaultTokenAmount)


@view
@external
def getVaultTokenAmount(_asset: address, _assetAmount: uint256, _vaultToken: address) -> uint256:
    if empty(address) in [_asset, _vaultToken] or _assetAmount == 0:
        return 0 # bad inputs
    if self._getUnderlyingAsset(_vaultToken) != _asset:
        return 0 # invalid vault token or asset
    return staticcall IERC4626(_vaultToken).convertToShares(_assetAmount)


# usd value


@view
@external
def getUsdValueOfVaultToken(_vaultToken: address, _vaultTokenAmount: uint256, _appraiser: address = empty(address)) -> uint256:
    return self._getUsdValueOfVaultToken(_vaultToken, _vaultTokenAmount, _appraiser)


@view
@internal
def _getUsdValueOfVaultToken(_vaultToken: address, _vaultTokenAmount: uint256, _appraiser: address) -> uint256:
    asset: address = empty(address)
    underlyingAmount: uint256 = 0
    usdValue: uint256 = 0
    asset, underlyingAmount, usdValue = self._getUnderlyingData(_vaultToken, _vaultTokenAmount, _appraiser)
    return usdValue


# all underlying data together


@view
@external
def getUnderlyingData(_vaultToken: address, _vaultTokenAmount: uint256, _appraiser: address = empty(address)) -> (address, uint256, uint256):
    return self._getUnderlyingData(_vaultToken, _vaultTokenAmount, _appraiser)


@view
@internal
def _getUnderlyingData(_vaultToken: address, _vaultTokenAmount: uint256, _appraiser: address) -> (address, uint256, uint256):
    if _vaultTokenAmount == 0 or _vaultToken == empty(address):
        return empty(address), 0, 0 # bad inputs
    asset: address = self._getUnderlyingAsset(_vaultToken)
    if asset == empty(address):
        return empty(address), 0, 0 # invalid vault token
    underlyingAmount: uint256 = self._getUnderlyingAmount(_vaultToken, _vaultTokenAmount)
    usdValue: uint256 = self._getUsdValue(asset, underlyingAmount, _appraiser)
    return asset, underlyingAmount, usdValue


@view
@internal
def _getUsdValue(_asset: address, _amount: uint256, _appraiser: address) -> uint256:
    appraiser: address = _appraiser
    if _appraiser == empty(address):
        appraiser = addys._getAppraiserAddr()
    return staticcall Appraiser(appraiser).getUsdValue(_asset, _amount)


# other


@view
@external
def totalAssets(_vaultToken: address) -> uint256:
    if not self._isVaultToken(_vaultToken):
        return 0 # invalid vault token
    return staticcall IERC4626(_vaultToken).totalAssets()


@view
@external
def totalBorrows(_vaultToken: address) -> uint256:
    return 0 # TODO


# price per share


@view
@external
def getPricePerShare(_asset: address, _decimals: uint256) -> uint256:
    return staticcall IERC4626(_asset).convertToAssets(10 ** _decimals)


################
# Registration #
################


@external
def addAssetOpportunity(_asset: address, _vaultAddr: address):
    pass


@external
def removeAssetOpportunity(_asset: address, _vaultAddr: address):
    pass


@internal
def _registerAsset(_asset: address, _vaultAddr: address):
    assert extcall IERC20(_asset).approve(_vaultAddr, max_value(uint256), default_return_value=True) # dev: max approval failed
    yld._addAssetOpportunity(_asset, _vaultAddr)


# update ledger registration


@internal
def _updateLedgerVaultToken(
    _underlyingAsset: address,
    _vaultToken: address,
    _ledger: address,
    _legoBook: address,
):
    if empty(address) in [_underlyingAsset, _vaultToken]:
        return

    if not staticcall Ledger(_ledger).isRegisteredVaultToken(_vaultToken):
        legoId: uint256 = staticcall UndyRegistry(_legoBook).getRegId(self)
        decimals: uint256 = convert(staticcall IERC20Detailed(_vaultToken).decimals(), uint256)
        extcall Ledger(_ledger).setVaultToken(_vaultToken, legoId, _underlyingAsset, decimals, self._isRebasing())


#########
# Other #
#########


@external
def swapTokens(
    _amountIn: uint256,
    _minAmountOut: uint256,
    _tokenPath: DynArray[address, MAX_TOKEN_PATH],
    _poolPath: DynArray[address, MAX_TOKEN_PATH - 1],
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256, uint256):
    return 0, 0, 0


@external
def mintOrRedeemAsset(
    _tokenIn: address,
    _tokenOut: address,
    _tokenInAmount: uint256,
    _minAmountOut: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256, bool, uint256):
    return 0, 0, False, 0
    

@external
def confirmMintOrRedeemAsset(
    _tokenIn: address,
    _tokenOut: address,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    return 0, 0


@external
def addLiquidity(
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _amountA: uint256,
    _amountB: uint256,
    _minAmountA: uint256,
    _minAmountB: uint256,
    _minLpAmount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (address, uint256, uint256, uint256, uint256):
    return empty(address), 0, 0, 0, 0


@external
def removeLiquidity(
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _lpToken: address,
    _lpAmount: uint256,
    _minAmountA: uint256,
    _minAmountB: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256, uint256, uint256):
    return 0, 0, 0, 0


@external
def addLiquidityConcentrated(
    _nftTokenId: uint256,
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _tickLower: int24,
    _tickUpper: int24,
    _amountA: uint256,
    _amountB: uint256,
    _minAmountA: uint256,
    _minAmountB: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256, uint256, uint256, uint256):
    return 0, 0, 0, 0, 0


@external
def removeLiquidityConcentrated(
    _nftTokenId: uint256,
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _liqToRemove: uint256,
    _minAmountA: uint256,
    _minAmountB: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256, uint256, bool, uint256):
    return 0, 0, 0, False, 0


@view
@external
def getPrice(_asset: address, _decimals: uint256) -> uint256:
    return 0
