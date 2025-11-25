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
from interfaces import LegoStructs as ls

import contracts.modules.Addys as addys
import contracts.modules.YieldLegoData as yld

from ethereum.ercs import IERC20
from ethereum.ercs import IERC4626
from ethereum.ercs import IERC20Detailed

interface RipeTeller:
    def repay(_paymentAmount: uint256 = max_value(uint256), _user: address = msg.sender, _isPaymentSavingsGreen: bool = False, _shouldRefundSavingsGreen: bool = True) -> bool: nonpayable
    def withdraw(_asset: address, _amount: uint256 = max_value(uint256), _user: address = msg.sender, _vaultAddr: address = empty(address), _vaultId: uint256 = 0) -> uint256: nonpayable
    def deposit(_asset: address, _amount: uint256 = max_value(uint256), _user: address = msg.sender, _vaultAddr: address = empty(address), _vaultId: uint256 = 0) -> uint256: nonpayable
    def borrow(_greenAmount: uint256 = max_value(uint256), _user: address = msg.sender, _wantsSavingsGreen: bool = True, _shouldEnterStabPool: bool = False) -> uint256: nonpayable
    def deleverageWithSpecificAssets(_assets: DynArray[DeleverageAsset, MAX_DELEVERAGE_ASSETS], _user: address = msg.sender) -> uint256: nonpayable
    def depositIntoGovVault(_asset: address, _amount: uint256, _lockDuration: uint256, _user: address = msg.sender) -> uint256: nonpayable
    def claimLoot(_user: address = msg.sender, _shouldStake: bool = True) -> uint256: nonpayable

interface Ledger:
    def setVaultToken(_vaultToken: address, _legoId: uint256, _underlyingAsset: address, _decimals: uint256, _isRebasing: bool): nonpayable
    def isRegisteredVaultToken(_vaultToken: address) -> bool: view
    def isUserWallet(_user: address) -> bool: view

interface Registry:
    def getRegId(_addr: address) -> uint256: view
    def getAddr(_regId: uint256) -> address: view
    def isValidAddr(_addr: address) -> bool: view
    
interface RipeRegistry:
    def savingsGreen() -> address: view
    def greenToken() -> address: view
    def ripeToken() -> address: view

interface Appraiser:
    def getUsdValue(_asset: address, _amount: uint256, _missionControl: address = empty(address), _legoBook: address = empty(address), _ledger: address = empty(address)) -> uint256: view
    def getUnderlyingUsdValue(_asset: address, _amount: uint256) -> uint256: view

interface EndaomentPsm:
    def redeemGreen(_paymentAmount: uint256 = max_value(uint256), _recipient: address = msg.sender, _isPaymentSavingsGreen: bool = False) -> uint256: nonpayable
    def mintGreen(_usdcAmount: uint256 = max_value(uint256), _recipient: address = msg.sender, _wantsSavingsGreen: bool = False) -> uint256: nonpayable

interface RipeMissionControl:
    def doesUndyLegoHaveAccess(_wallet: address, _legoAddr: address) -> bool: view

interface VaultRegistry:
    def isEarnVault(_vaultAddr: address) -> bool: view

interface UserWalletConfig:
    def isAgentSender(_addr: address) -> bool: view

interface UserWallet:
    def walletConfig() -> address: view

struct DeleverageAsset:
    vaultId: uint256
    asset: address
    targetRepayAmount: uint256

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

event RipeEndaomentPsmSwap:
    sender: indexed(address)
    tokenIn: indexed(address)
    tokenOut: indexed(address)
    amountIn: uint256
    amountOut: uint256
    usdValue: uint256
    numTokens: uint256
    recipient: address

# ripe addrs
RIPE_REGISTRY: public(immutable(address))
RIPE_GREEN_TOKEN: public(immutable(address))
RIPE_SAVINGS_GREEN: public(immutable(address))
RIPE_TOKEN: public(immutable(address))
USDC: public(immutable(address))

RIPE_MISSION_CONTROL_ID: constant(uint256) = 5
RIPE_TELLER_ID: constant(uint256) = 17
RIPE_ENDAOMENT_PSM_ID: constant(uint256) = 22

LEGO_ACCESS_ABI: constant(String[64]) = "setUndyLegoAccess(address)"
MAX_TOKEN_PATH: constant(uint256) = 5
MAX_PROOFS: constant(uint256) = 25
MAX_DELEVERAGE_ASSETS: constant(uint256) = 25


@deploy
def __init__(_undyHq: address, _ripeRegistry: address, _usdc: address):
    addys.__init__(_undyHq)
    yld.__init__(False)

    assert _ripeRegistry != empty(address) # dev: invalid ripe registry
    RIPE_REGISTRY = _ripeRegistry
    RIPE_GREEN_TOKEN = staticcall RipeRegistry(RIPE_REGISTRY).greenToken()
    RIPE_SAVINGS_GREEN = staticcall RipeRegistry(RIPE_REGISTRY).savingsGreen()
    RIPE_TOKEN = staticcall RipeRegistry(RIPE_REGISTRY).ripeToken()

    assert _usdc != empty(address) # dev: invalid usdc
    USDC = _usdc


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
def isYieldLego() -> bool:
    return True # savings green


@view
@external
def isDexLego() -> bool:
    return False


###################
# Underlying Data #
###################


# underlying asset


@view
@external
def getUnderlyingAsset(_vaultToken: address) -> address:
    return self._getUnderlyingAsset(_vaultToken)


@view
@internal
def _getUnderlyingAsset(_vaultToken: address) -> address:
    asset: address = yld.vaultToAsset[_vaultToken].underlyingAsset
    if asset != empty(address):
        return asset
    return RIPE_GREEN_TOKEN


# underlying balances (both true and safe)


@view
@external
def getUnderlyingBalances(_vaultToken: address, _vaultTokenBalance: uint256) -> (uint256, uint256):
    if _vaultTokenBalance == 0:
        return 0, 0

    trueUnderlying: uint256 = self._getUnderlyingAmount(_vaultToken, _vaultTokenBalance)
    safeUnderlying: uint256 = self._getUnderlyingAmountSafe(_vaultToken, _vaultTokenBalance)
    if safeUnderlying == 0:
        safeUnderlying = trueUnderlying

    return trueUnderlying, min(trueUnderlying, safeUnderlying)


# underlying amount (true)


@view
@external
def getUnderlyingAmount(_vaultToken: address, _vaultTokenAmount: uint256) -> uint256:
    return self._getUnderlyingAmount(_vaultToken, _vaultTokenAmount)


@view
@internal
def _getUnderlyingAmount(_vaultToken: address, _vaultTokenAmount: uint256) -> uint256:
    return staticcall IERC4626(_vaultToken).convertToAssets(_vaultTokenAmount)


# underlying amount (safe)


@view
@external
def getUnderlyingAmountSafe(_vaultToken: address, _vaultTokenBalance: uint256) -> uint256:
    return self._getUnderlyingAmountSafe(_vaultToken, _vaultTokenBalance)


@view
@internal
def _getUnderlyingAmountSafe(_vaultToken: address, _vaultTokenBalance: uint256) -> uint256:
    vaultInfo: ls.VaultTokenInfo = yld.vaultToAsset[_vaultToken]
    if vaultInfo.decimals == 0:
        return 0 # not registered

    # safe underlying amount (using cached weighted average from snapshots)
    return _vaultTokenBalance * vaultInfo.lastAveragePricePerShare // (10 ** vaultInfo.decimals)


# underlying data (combined)


@view
@external
def getUnderlyingData(_vaultToken: address, _vaultTokenAmount: uint256, _appraiser: address = empty(address)) -> (address, uint256, uint256):
    return self._getUnderlyingData(_vaultToken, _vaultTokenAmount, _appraiser)


@view
@internal
def _getUnderlyingData(_vaultToken: address, _vaultTokenAmount: uint256, _appraiser: address) -> (address, uint256, uint256):
    asset: address = self._getUnderlyingAsset(_vaultToken)
    if asset == empty(address):
        return empty(address), 0, 0 # invalid vault token
    underlyingAmount: uint256 = self._getUnderlyingAmount(_vaultToken, _vaultTokenAmount)
    usdValue: uint256 = self._getUsdValueViaAppraiser(asset, underlyingAmount, _appraiser)
    return asset, underlyingAmount, usdValue


# usd value


@view
@external
def getUsdValueOfVaultToken(_vaultToken: address, _vaultTokenAmount: uint256, _appraiser: address = empty(address)) -> uint256:
    return self._getUsdValueOfVaultToken(_vaultToken, _vaultTokenAmount, _appraiser)


@view
@internal
def _getUsdValueOfVaultToken(_vaultToken: address, _vaultTokenAmount: uint256, _appraiser: address) -> uint256:
    return self._getUnderlyingData(_vaultToken, _vaultTokenAmount, _appraiser)[2]


@view
@internal
def _getUsdValueViaAppraiser(_asset: address, _amount: uint256, _appraiser: address) -> uint256:
    appraiser: address = _appraiser
    if _appraiser == empty(address):
        appraiser = addys._getAppraiserAddr()
    return staticcall Appraiser(appraiser).getUnderlyingUsdValue(_asset, _amount)


###############
# Other Utils #
###############


# basics


@view
@external
def isRebasing() -> bool:
    return self._isRebasing()


@view
@internal
def _isRebasing() -> bool:
    return False


# price per share


@view
@external
def getPricePerShare(_vaultToken: address, _decimals: uint256 = 0) -> uint256:
    decimals: uint256 = _decimals
    if decimals == 0:
        decimals = yld.vaultToAsset[_vaultToken].decimals
    if decimals == 0:
        decimals = convert(staticcall IERC20Detailed(_vaultToken).decimals(), uint256)
    return self._getPricePerShare(_vaultToken, decimals)


@view
@internal
def _getPricePerShare(_vaultToken: address, _decimals: uint256) -> uint256:
    return staticcall IERC4626(_vaultToken).convertToAssets(10 ** _decimals)


# vault token amount


@view
@external
def getVaultTokenAmount(_asset: address, _assetAmount: uint256, _vaultToken: address) -> uint256:
    return staticcall IERC4626(_vaultToken).convertToShares(_assetAmount)


# total assets


@view
@external
def totalAssets(_vaultToken: address) -> uint256:
    return staticcall IERC4626(_vaultToken).totalAssets()


# total borrows


@view
@external
def totalBorrows(_vaultToken: address) -> uint256:
    # no borrowing related to _vaultToken
    return 0


# avail liquidity


@view
@external
def getAvailLiquidity(_vaultToken: address) -> uint256:
    return staticcall IERC4626(_vaultToken).totalAssets()


# utilization


@view
@external
def getUtilizationRatio(_vaultToken: address) -> uint256:
    # no borrowing related to _vaultToken
    return 0


# extras


@view
@external
def isEligibleForYieldBonus(_asset: address) -> bool:
    return False


@view
@external
def getWithdrawalFees(_vaultToken: address, _vaultTokenAmount: uint256) -> uint256:
    return 0


################
# Registration #
################


# can vault be registered


@view
@external
def canRegisterVaultToken(_asset: address, _vaultToken: address) -> bool:
    return self._canRegisterVaultToken(_asset, _vaultToken)


@view
@internal
def _canRegisterVaultToken(_asset: address, _vaultToken: address) -> bool:
    if empty(address) in [_asset, _vaultToken]:
        return False
    return _asset == RIPE_GREEN_TOKEN and _vaultToken == RIPE_SAVINGS_GREEN


# register vault token locally


@external
def registerVaultTokenLocally(_asset: address, _vaultAddr: address) -> ls.VaultTokenInfo:
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert self._canRegisterVaultToken(_asset, _vaultAddr) # dev: cannot register vault token
    assert not yld._isAssetOpportunity(_asset, _vaultAddr) # dev: already registered
    vaultInfo: ls.VaultTokenInfo = self._registerVaultTokenLocally(_asset, _vaultAddr)
    self._registerVaultTokenGlobally(_asset, _vaultAddr, vaultInfo.decimals, addys._getLedgerAddr(), addys._getLegoBookAddr())
    return vaultInfo


@internal
def _registerVaultTokenLocally(_asset: address, _vaultAddr: address) -> ls.VaultTokenInfo:
    assert extcall IERC20(_asset).approve(_vaultAddr, max_value(uint256), default_return_value=True) # dev: max approval failed
    vaultInfo: ls.VaultTokenInfo = yld._addAssetOpportunity(_asset, _vaultAddr)
    assert vaultInfo.decimals != 0 # dev: invalid vault token
    return vaultInfo


# remove vault token locally


@external
def deregisterVaultTokenLocally(_asset: address, _vaultAddr: address):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert yld._isAssetOpportunity(_asset, _vaultAddr) # dev: already registered
    self._deregisterVaultTokenLocally(_asset, _vaultAddr)


@internal
def _deregisterVaultTokenLocally(_asset: address, _vaultAddr: address):
    assert extcall IERC20(_asset).approve(_vaultAddr, 0, default_return_value=True) # dev: max approval failed
    yld._removeAssetOpportunity(_asset, _vaultAddr)


# ledger registration


@internal
def _registerVaultTokenGlobally(_underlyingAsset: address, _vaultToken: address, _decimals: uint256, _ledger: address, _legoBook: address):
    if not staticcall Ledger(_ledger).isRegisteredVaultToken(_vaultToken):
        legoId: uint256 = staticcall Registry(_legoBook).getRegId(self)
        extcall Ledger(_ledger).setVaultToken(_vaultToken, legoId, _underlyingAsset, _decimals, self._isRebasing())


#################
# Yield Actions #
#################


# add price snapshot


@external
def addPriceSnapshot(_vaultToken: address) -> bool:
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    vaultInfo: ls.VaultTokenInfo = yld.vaultToAsset[_vaultToken]
    assert vaultInfo.decimals != 0 # dev: not registered
    pricePerShare: uint256 = self._getPricePerShare(_vaultToken, vaultInfo.decimals)
    return yld._addPriceSnapshot(_vaultToken, pricePerShare, vaultInfo.decimals)


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
    assert self._isAllowedToPerformAction(msg.sender) # dev: no perms
    assert not yld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = yld._getMiniAddys(_miniAddys)
    vaultInfo: ls.VaultTokenInfo = self._getVaultInfoOnDeposit(_asset, _vaultAddr, miniAddys.ledger, miniAddys.legoBook)

    # pre balances
    preLegoBalance: uint256 = staticcall IERC20(_asset).balanceOf(self)

    # transfer deposit asset to this contract
    depositAmount: uint256 = min(_amount, staticcall IERC20(_asset).balanceOf(msg.sender))
    assert depositAmount != 0 # dev: nothing to transfer
    assert extcall IERC20(_asset).transferFrom(msg.sender, self, depositAmount, default_return_value=True) # dev: transfer failed

    # deposit assets into lego partner
    vaultTokenAmountReceived: uint256 = extcall IERC4626(_vaultAddr).deposit(depositAmount, _recipient)
    assert vaultTokenAmountReceived != 0 # dev: no vault tokens received

    # refund if full deposit didn't get through
    currentLegoBalance: uint256 = staticcall IERC20(_asset).balanceOf(self)
    refundAssetAmount: uint256 = 0
    if currentLegoBalance > preLegoBalance:
        refundAssetAmount = currentLegoBalance - preLegoBalance
        assert extcall IERC20(_asset).transfer(msg.sender, refundAssetAmount, default_return_value=True) # dev: transfer failed
        depositAmount -= refundAssetAmount

    usdValue: uint256 = staticcall Appraiser(miniAddys.appraiser).getUnderlyingUsdValue(_asset, depositAmount)
    log RipeSavingsGreenDeposit(
        sender = msg.sender,
        asset = _asset,
        vaultToken = _vaultAddr,
        assetAmountDeposited = depositAmount,
        usdValue = usdValue,
        vaultTokenAmountReceived = vaultTokenAmountReceived,
        recipient = _recipient,
    )

    # add price snapshot
    pricePerShare: uint256 = self._getPricePerShare(_vaultAddr, vaultInfo.decimals)
    yld._addPriceSnapshot(_vaultAddr, pricePerShare, vaultInfo.decimals)

    return depositAmount, _vaultAddr, vaultTokenAmountReceived, usdValue


# vault info on deposit


@internal
def _getVaultInfoOnDeposit(_asset: address, _vaultAddr: address, _ledger: address, _legoBook: address) -> ls.VaultTokenInfo:
    vaultInfo: ls.VaultTokenInfo = yld.vaultToAsset[_vaultAddr]
    if vaultInfo.decimals == 0:
        assert self._canRegisterVaultToken(_asset, _vaultAddr) # dev: cannot register vault token
        vaultInfo = self._registerVaultTokenLocally(_asset, _vaultAddr)
        self._registerVaultTokenGlobally(_asset, _vaultAddr, vaultInfo.decimals, _ledger, _legoBook)
    else:
        assert vaultInfo.underlyingAsset == _asset # dev: asset mismatch
    return vaultInfo


# withdraw


@external
def withdrawFromYield(
    _vaultToken: address,
    _amount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, address, uint256, uint256):
    assert self._isAllowedToPerformAction(msg.sender) # dev: no perms
    assert not yld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = yld._getMiniAddys(_miniAddys)
    vaultInfo: ls.VaultTokenInfo = self._getVaultInfoOnWithdrawal(_vaultToken, miniAddys.ledger, miniAddys.legoBook)

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

    usdValue: uint256 = staticcall Appraiser(miniAddys.appraiser).getUnderlyingUsdValue(vaultInfo.underlyingAsset, assetAmountReceived)
    log RipeSavingsGreenWithdrawal(
        sender = msg.sender,
        asset = vaultInfo.underlyingAsset,
        vaultToken = _vaultToken,
        assetAmountReceived = assetAmountReceived,
        usdValue = usdValue,
        vaultTokenAmountBurned = vaultTokenAmount,
        recipient = _recipient,
    )

    # add price snapshot
    pricePerShare: uint256 = self._getPricePerShare(_vaultToken, vaultInfo.decimals)
    yld._addPriceSnapshot(_vaultToken, pricePerShare, vaultInfo.decimals)

    return vaultTokenAmount, vaultInfo.underlyingAsset, assetAmountReceived, usdValue


# vault info on withdrawal


@internal
def _getVaultInfoOnWithdrawal(_vaultAddr: address, _ledger: address, _legoBook: address) -> ls.VaultTokenInfo:
    vaultInfo: ls.VaultTokenInfo = yld.vaultToAsset[_vaultAddr]
    if vaultInfo.decimals == 0:
        asset: address = staticcall IERC4626(_vaultAddr).asset()
        assert self._canRegisterVaultToken(asset, _vaultAddr) # dev: cannot register vault token
        vaultInfo = self._registerVaultTokenLocally(asset, _vaultAddr)
        self._registerVaultTokenGlobally(asset, _vaultAddr, vaultInfo.decimals, _ledger, _legoBook)
    return vaultInfo


#################
# Swaps via PSM #
#################


@external
def swapTokens(
    _amountIn: uint256,
    _minAmountOut: uint256,
    _tokenPath: DynArray[address, MAX_TOKEN_PATH],
    _poolPath: DynArray[address, MAX_TOKEN_PATH - 1],
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256, uint256):
    assert not yld.isPaused # dev: paused
    assert self._isAllowedToPerformAction(msg.sender) # dev: no perms
    miniAddys: ws.MiniAddys = yld._getMiniAddys(_miniAddys)

    assert len(_tokenPath) == 2 # dev: invalid token path
    tokenIn: address = _tokenPath[0]
    tokenOut: address = _tokenPath[1]
    assert tokenIn != tokenOut # dev: same token

    # must be GREEN and USDC
    savingsGreen: address = RIPE_SAVINGS_GREEN
    green: address = RIPE_GREEN_TOKEN
    usdc: address = USDC
    assert tokenIn in [green, savingsGreen, usdc] # dev: invalid tokens
    assert tokenOut in [green, savingsGreen, usdc] # dev: invalid tokens

    # prevent GREEN <-> SAVINGS_GREEN swaps (use depositForYield/withdrawFromYield instead)
    bothAreGreenVariants: bool = (tokenIn in [green, savingsGreen]) and (tokenOut in [green, savingsGreen])
    assert not bothAreGreenVariants # dev: cannot swap into or out of savings green

    # pre balances
    preLegoBalance: uint256 = staticcall IERC20(tokenIn).balanceOf(self)

    # transfer swap asset to this contract
    amountIn: uint256 = min(_amountIn, staticcall IERC20(tokenIn).balanceOf(msg.sender))
    assert amountIn != 0 # dev: nothing to transfer
    assert extcall IERC20(tokenIn).transferFrom(msg.sender, self, amountIn, default_return_value=True) # dev: transfer failed

    # swap via endaoment psm
    endaomentPsm: address = staticcall Registry(RIPE_REGISTRY).getAddr(RIPE_ENDAOMENT_PSM_ID)
    assert extcall IERC20(tokenIn).approve(endaomentPsm, amountIn, default_return_value=True) # dev: approval failed

    # swap GREEN -> USDC
    amountOut: uint256 = 0
    if tokenIn in [green, savingsGreen]:
        amountOut = extcall EndaomentPsm(endaomentPsm).redeemGreen(amountIn, _recipient, tokenIn == savingsGreen)

    # swap USDC -> GREEN
    elif tokenIn == usdc:
        amountOut = extcall EndaomentPsm(endaomentPsm).mintGreen(amountIn, _recipient, tokenOut == savingsGreen)

    # reset approvals
    assert extcall IERC20(tokenIn).approve(endaomentPsm, 0, default_return_value=True) # dev: approval failed

    # refund if full swap didn't get through
    currentLegoBalance: uint256 = staticcall IERC20(tokenIn).balanceOf(self)
    refundAssetAmount: uint256 = 0
    if currentLegoBalance > preLegoBalance:
        refundAssetAmount = currentLegoBalance - preLegoBalance
        assert extcall IERC20(tokenIn).transfer(msg.sender, refundAssetAmount, default_return_value=True) # dev: transfer failed
        amountIn -= refundAssetAmount

    # adjust min amount out
    minAmountOut: uint256 = _minAmountOut
    if amountIn < _amountIn and _amountIn != max_value(uint256):
        minAmountOut = _minAmountOut * amountIn // _amountIn
    assert amountOut >= minAmountOut # dev: min amount out not met

    # get usd values
    usdValue: uint256 = staticcall Appraiser(miniAddys.appraiser).getUsdValue(tokenIn, amountIn, miniAddys.missionControl, miniAddys.legoBook, miniAddys.ledger)
    if usdValue == 0:
        usdValue = staticcall Appraiser(miniAddys.appraiser).getUsdValue(tokenOut, amountOut, miniAddys.missionControl, miniAddys.legoBook, miniAddys.ledger)

    log RipeEndaomentPsmSwap(
        sender = msg.sender,
        tokenIn = tokenIn,
        tokenOut = tokenOut,
        amountIn = amountIn,
        amountOut = amountOut,
        usdValue = usdValue,
        numTokens = 2,
        recipient = _recipient,
    )
    return amountIn, amountOut, usdValue


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
    assert self._isAllowedToPerformAction(msg.sender) # dev: no perms
    assert not yld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = yld._getMiniAddys(_miniAddys)

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

    usdValue: uint256 = staticcall Appraiser(miniAddys.appraiser).getUsdValue(_asset, depositAmount, miniAddys.missionControl, miniAddys.legoBook, miniAddys.ledger)
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
    assert self._isAllowedToPerformAction(msg.sender) # dev: no perms
    assert not yld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = yld._getMiniAddys(_miniAddys)

    assert msg.sender == _recipient # dev: recipient must be caller

    vaultId: uint256 = 0
    if _extraData != empty(bytes32):
        vaultId = convert(_extraData, uint256)

    # withdraw from Ripe Protocol
    ripeHq: address = RIPE_REGISTRY
    teller: address = staticcall Registry(ripeHq).getAddr(RIPE_TELLER_ID)
    amountRemoved: uint256 = extcall RipeTeller(teller).withdraw(_asset, _amount, _recipient, empty(address), vaultId)
    assert amountRemoved != 0 # dev: no asset amount received

    usdValue: uint256 = staticcall Appraiser(miniAddys.appraiser).getUsdValue(_asset, amountRemoved, miniAddys.missionControl, miniAddys.legoBook, miniAddys.ledger)
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
    assert self._isAllowedToPerformAction(msg.sender) # dev: no perms
    assert not yld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = yld._getMiniAddys(_miniAddys)

    assert msg.sender == _recipient # dev: recipient must be caller

    savingsGreen: address = RIPE_SAVINGS_GREEN
    assert _borrowAsset in [RIPE_GREEN_TOKEN, savingsGreen] # dev: invalid borrow asset
    wantsSavingsGreen: bool = _borrowAsset == savingsGreen

    # Extract shouldEnterStabPool from extraData (1 bit in lowest position)
    shouldEnterStabPool: bool = convert(convert(_extraData, uint256) & 1, bool)

    # borrow from Ripe
    teller: address = staticcall Registry(RIPE_REGISTRY).getAddr(RIPE_TELLER_ID)
    borrowAmount: uint256 = extcall RipeTeller(teller).borrow(_amount, _recipient, wantsSavingsGreen, shouldEnterStabPool)
    assert borrowAmount != 0 # dev: no borrow amount received

    usdValue: uint256 = staticcall Appraiser(miniAddys.appraiser).getUnderlyingUsdValue(_borrowAsset, borrowAmount)
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
    assert self._isAllowedToPerformAction(msg.sender) # dev: no perms
    assert not yld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = yld._getMiniAddys(_miniAddys)

    assert msg.sender == _recipient # dev: recipient must be caller

    savingsGreen: address = RIPE_SAVINGS_GREEN
    assert _paymentAsset in [RIPE_GREEN_TOKEN, savingsGreen] # dev: invalid payment asset
    isPaymentSavingsGreen: bool = _paymentAsset == savingsGreen

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

    usdValue: uint256 = staticcall Appraiser(miniAddys.appraiser).getUsdValue(_paymentAsset, paymentAmount, miniAddys.missionControl, miniAddys.legoBook, miniAddys.ledger)
    log RipeRepay(
        sender = msg.sender,
        asset = _paymentAsset,
        assetAmountRepaid = paymentAmount,
        usdValue = usdValue,
        recipient = _recipient,
    )
    return paymentAmount, usdValue


# deleverage


@external
def deleverageWithSpecificAssets(_assets: DynArray[DeleverageAsset, MAX_DELEVERAGE_ASSETS], _user: address) -> uint256:
    walletConfig: address = staticcall UserWallet(_user).walletConfig()
    assert staticcall UserWalletConfig(walletConfig).isAgentSender(msg.sender) # dev: no perms

    teller: address = staticcall Registry(RIPE_REGISTRY).getAddr(RIPE_TELLER_ID)
    return extcall RipeTeller(teller).deleverageWithSpecificAssets(_assets, _user)


# shared utils


@internal
def _getRipeTellerAndApprove(_asset: address) -> address:
    teller: address = staticcall Registry(RIPE_REGISTRY).getAddr(RIPE_TELLER_ID)
    # some vault tokens require max value approval (comp v3)
    assert extcall IERC20(_asset).approve(teller, max_value(uint256), default_return_value = True) # dev: appr
    return teller


@internal
def _resetTellerApproval(_asset: address, _teller: address):
    if _teller != empty(address):
        assert extcall IERC20(_asset).approve(_teller, 0, default_return_value = True) # dev: approval failed


@view
@internal
def _isUserWalletOrEarnVault(_user: address) -> bool:
    return staticcall Ledger(addys._getLedgerAddr()).isUserWallet(_user) or staticcall VaultRegistry(addys._getVaultRegistryAddr()).isEarnVault(_user)


#################
# Claim Rewards #
#################


@external
def claimIncentives(
    _user: address,
    _rewardToken: address,
    _rewardAmount: uint256,
    _proofs: DynArray[bytes32, MAX_PROOFS],
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    assert self._isAllowedToPerformAction(msg.sender) # dev: no perms
    return self._claimRewards(_user, _rewardToken, _rewardAmount, _miniAddys)


@external
def claimRewards(
    _user: address,
    _rewardToken: address,
    _rewardAmount: uint256,
    _extraData: bytes32,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    assert self._isAllowedToPerformAction(msg.sender) # dev: no perms
    return self._claimRewards(_user, _rewardToken, _rewardAmount, _miniAddys)


@internal
def _claimRewards(
    _user: address,
    _rewardToken: address,
    _rewardAmount: uint256,
    _miniAddys: ws.MiniAddys,
) -> (uint256, uint256):
    miniAddys: ws.MiniAddys = yld._getMiniAddys(_miniAddys)
    assert not yld.isPaused # dev: paused
    assert _rewardToken == RIPE_TOKEN # dev: invalid reward token

    teller: address = staticcall Registry(RIPE_REGISTRY).getAddr(RIPE_TELLER_ID)
    totalRipe: uint256 = extcall RipeTeller(teller).claimLoot(_user, True)
    assert totalRipe != 0 # dev: no ripe tokens received

    usdValue: uint256 = staticcall Appraiser(miniAddys.appraiser).getUnderlyingUsdValue(_rewardToken, totalRipe)
    log RipeClaimRewards(
        sender = msg.sender,
        asset = _rewardToken,
        ripeClaimed = totalRipe,
        usdValue = usdValue,
        recipient = _user,
    )
    return 0, usdValue


# has claimable rewards


@view
@external
def hasClaimableRewards(_user: address) -> bool:
    # TODO: implement
    return False


##################
# Access Control #
##################


@view
@internal
def _isAllowedToPerformAction(_caller: address) -> bool:
    # NOTE: important to not trust `_miniAddys` here, that's why getting ledger and vault registry from addys
    if staticcall VaultRegistry(addys._getVaultRegistryAddr()).isEarnVault(_caller):
        return True
    if staticcall Ledger(addys._getLedgerAddr()).isUserWallet(_caller):
        return True
    return staticcall Registry(RIPE_REGISTRY).isValidAddr(_caller) # Ripe Endaoment is allowed


@view
@external
def getAccessForLego(_user: address, _action: ws.ActionType) -> (address, String[64], uint256):
    ripeHq: address = RIPE_REGISTRY

    mc: address = staticcall Registry(ripeHq).getAddr(RIPE_MISSION_CONTROL_ID)
    if staticcall RipeMissionControl(mc).doesUndyLegoHaveAccess(_user, self):
        return empty(address), empty(String[64]), 0

    else:
        teller: address = staticcall Registry(ripeHq).getAddr(RIPE_TELLER_ID)
        return teller, LEGO_ACCESS_ABI, 1


#########
# Other #
#########


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
