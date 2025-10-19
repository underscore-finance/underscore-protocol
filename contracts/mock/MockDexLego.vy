# @version 0.4.3

implements: Lego

exports: addys.__interface__
exports: dld.__interface__

initializes: addys
initializes: dld[addys := addys]

from interfaces import LegoPartner as Lego
from interfaces import WalletStructs as ws

import contracts.modules.Addys as addys
import contracts.modules.DexLegoData as dld

from ethereum.ercs import IERC20
from ethereum.ercs import IERC20Detailed

interface Appraiser:
    def getNormalAssetPrice(_asset: address, _missionControl: address = empty(address), _legoBook: address = empty(address), _ledger: address = empty(address)) -> uint256: view
    def updatePriceAndGetUsdValue(_asset: address, _amount: uint256, _missionControl: address = empty(address), _legoBook: address = empty(address)) -> uint256: nonpayable

interface MockToken:
    def mint(_to: address, _value: uint256): nonpayable
    def burn(_value: uint256) -> bool: nonpayable

struct BestPool:
    pool: address
    fee: uint256
    liquidity: uint256
    numCoins: uint256

struct PendingMintOrRedeem:
    tokenIn: address
    tokenOut: address
    amount: uint256

asset: public(address)
altAsset: public(address)
lpToken: public(address)
debtToken: public(address)

pendingMintOrRedeem: public(HashMap[address, PendingMintOrRedeem])
hasAccess: public(bool)
immediateMintOrRedeem: public(bool)

# mock price config
price: public(HashMap[address, uint256])

EIGHTEEN_DECIMALS: constant(uint256) = 10 ** 18
MAX_TOKEN_PATH: constant(uint256) = 5
LEGO_ACCESS_ABI: constant(String[64]) = "setLegoAccess(address)"


@deploy
def __init__(
    _undyHq: address,
    _asset: address,
    _altAsset: address,
    _lpToken: address,
    _debtToken: address,
):
    # modules
    addys.__init__(_undyHq)
    dld.__init__(False)

    # mock assets
    assert empty(address) not in [_asset, _altAsset, _lpToken, _debtToken] # dev: invalid tokens
    self.asset = _asset
    self.altAsset = _altAsset
    self.lpToken = _lpToken
    self.debtToken = _debtToken
    self.hasAccess = False


@view
@external
def hasCapability(_action: ws.ActionType) -> bool:
    return _action in (
        ws.ActionType.SWAP | 
        ws.ActionType.MINT_REDEEM | 
        ws.ActionType.CONFIRM_MINT_REDEEM | 
        ws.ActionType.ADD_COLLATERAL | 
        ws.ActionType.REMOVE_COLLATERAL | 
        ws.ActionType.BORROW | 
        ws.ActionType.REPAY_DEBT | 
        ws.ActionType.REWARDS | 
        ws.ActionType.ADD_LIQ | 
        ws.ActionType.REMOVE_LIQ
    )


@view
@external
def getRegistries() -> DynArray[address, 10]:
    return []


@view
@external
def isYieldLego() -> bool:
    return False


@view
@external
def isDexLego() -> bool:
    return True


@view
@internal
def _areValidTokens(_tokens: DynArray[address, 4]) -> bool:
    validTokens: address[4] = [self.asset, self.altAsset, self.lpToken, self.debtToken]
    for t: address in _tokens:
        if t in validTokens:
            continue
        return False
    return True


# normal price (not yield)


@view
@external
def getPrice(_asset: address, _decimals: uint256) -> uint256:
    return self.price[_asset]


# MOCK config


@external
def setPrice(_asset: address, _price: uint256):
    self.price[_asset] = _price


@external
def setImmediateMintOrRedeem(_isImmediate: bool):
    self.immediateMintOrRedeem = _isImmediate


###################
# Swap / Exchange #
###################


@external
def swapTokens(
    _amountIn: uint256,
    _minAmountOut: uint256,
    _tokenPath: DynArray[address, MAX_TOKEN_PATH],
    _poolPath: DynArray[address, MAX_TOKEN_PATH - 1],
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256, uint256):
    assert not dld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = dld._getMiniAddys(_miniAddys)

    assert len(_tokenPath) >= 2 # dev: invalid token path
    tokenIn: address = _tokenPath[0]
    tokenOut: address = _tokenPath[len(_tokenPath) - 1]
    assert self._areValidTokens([tokenIn, tokenOut]) # dev: invalid tokens

    amount: uint256 = min(_amountIn, staticcall IERC20(tokenIn).balanceOf(msg.sender))
    assert amount != 0 # dev: nothing to transfer
    assert extcall IERC20(tokenIn).transferFrom(msg.sender, self, amount, default_return_value=True) # dev: transfer failed

    extcall MockToken(tokenIn).burn(amount)
    extcall MockToken(tokenOut).mint(_recipient, amount)

    # get usd values
    usdValue: uint256 = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(tokenIn, amount, miniAddys.missionControl, miniAddys.legoBook)
    if usdValue == 0:
        usdValue = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(tokenOut, amount, miniAddys.missionControl, miniAddys.legoBook)

    return amount, amount, usdValue
    

# mint / redeem


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
    assert self._areValidTokens([_tokenIn, _tokenOut]) # dev: invalid tokens
    assert not dld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = dld._getMiniAddys(_miniAddys)

    amount: uint256 = min(_tokenInAmount, staticcall IERC20(_tokenIn).balanceOf(msg.sender))
    assert amount != 0 # dev: nothing to transfer
    assert extcall IERC20(_tokenIn).transferFrom(msg.sender, self, amount, default_return_value=True) # dev: transfer failed
    extcall MockToken(_tokenIn).burn(amount)

    amountOut: uint256 = amount

    # immediate mint (default)
    usdValue: uint256 = 0
    if self.immediateMintOrRedeem:
        extcall MockToken(_tokenOut).mint(_recipient, amount)
        usdValue = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(_tokenOut, amount, miniAddys.missionControl, miniAddys.legoBook)

    # create pending mint
    else:
        self.pendingMintOrRedeem[msg.sender] = PendingMintOrRedeem(
            tokenIn = _tokenIn,
            tokenOut = _tokenOut,
            amount = amount,
        )
        amountOut = 0

    return amount, amountOut, not self.immediateMintOrRedeem, usdValue
    

@external
def confirmMintOrRedeemAsset(
    _tokenIn: address,
    _tokenOut: address,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    assert not dld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = dld._getMiniAddys(_miniAddys)

    pending: PendingMintOrRedeem = self.pendingMintOrRedeem[msg.sender]
    assert pending.tokenIn == _tokenIn and pending.tokenOut == _tokenOut # dev: invalid tokens
    assert pending.amount != 0 # dev: nothing to confirm

    extcall MockToken(pending.tokenOut).mint(_recipient, pending.amount)
    self.pendingMintOrRedeem[msg.sender] = empty(PendingMintOrRedeem)

    usdValue: uint256 = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(_tokenOut, pending.amount, miniAddys.missionControl, miniAddys.legoBook)
    return pending.amount, usdValue


########
# Debt #
########


@external
def addCollateral(
    _asset: address,
    _amount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    assert not dld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = dld._getMiniAddys(_miniAddys)

    assert self._areValidTokens([_asset]) # dev: invalid tokens
    assert self.hasAccess # dev: no access

    amount: uint256 = min(_amount, staticcall IERC20(_asset).balanceOf(msg.sender))
    assert amount != 0 # dev: nothing to transfer
    assert extcall IERC20(_asset).transferFrom(msg.sender, self, amount, default_return_value=True) # dev: transfer failed

    extcall MockToken(_asset).burn(amount)

    usdValue: uint256 = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(_asset, amount, miniAddys.missionControl, miniAddys.legoBook)
    return amount, usdValue


@external
def removeCollateral(
    _asset: address,
    _amount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    assert not dld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = dld._getMiniAddys(_miniAddys)

    assert self._areValidTokens([_asset]) # dev: invalid tokens
    assert self.hasAccess # dev: no access

    extcall MockToken(_asset).mint(_recipient, _amount)

    usdValue: uint256 = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(_asset, _amount, miniAddys.missionControl, miniAddys.legoBook)
    return _amount, usdValue


@external
def borrow(
    _borrowAsset: address,
    _amount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    assert not dld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = dld._getMiniAddys(_miniAddys)

    assert _borrowAsset == self.debtToken # dev: invalid borrow asset
    assert self.hasAccess # dev: no access

    assert _amount != 0 # dev: nothing to borrow
    assert _amount != max_value(uint256) # dev: too high

    extcall MockToken(_borrowAsset).mint(_recipient, _amount)

    usdValue: uint256 = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(_borrowAsset, _amount, miniAddys.missionControl, miniAddys.legoBook)
    return _amount, usdValue


@external
def repayDebt(
    _paymentAsset: address,
    _paymentAmount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    assert not dld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = dld._getMiniAddys(_miniAddys)

    assert _paymentAsset == self.debtToken # dev: invalid payment asset
    assert self.hasAccess # dev: no access

    amount: uint256 = min(_paymentAmount, staticcall IERC20(_paymentAsset).balanceOf(msg.sender))
    assert amount != 0 # dev: nothing to repay
    assert extcall IERC20(_paymentAsset).transferFrom(msg.sender, self, amount, default_return_value=True) # dev: transfer failed

    extcall MockToken(_paymentAsset).burn(amount)

    usdValue: uint256 = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(_paymentAsset, amount, miniAddys.missionControl, miniAddys.legoBook)
    return amount, usdValue


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
    assert not dld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = dld._getMiniAddys(_miniAddys)

    assert self._areValidTokens([_rewardToken]) # dev: invalid tokens
    assert self.hasAccess # dev: no access

    extcall MockToken(_rewardToken).mint(_user, _rewardAmount)

    usdValue: uint256 = extcall Appraiser(miniAddys.appraiser).updatePriceAndGetUsdValue(_rewardToken, _rewardAmount, miniAddys.missionControl, miniAddys.legoBook)
    return _rewardAmount, usdValue


#############
# Liquidity #
#############


# add liquidity


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
    assert not dld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = dld._getMiniAddys(_miniAddys)

    assert self._areValidTokens([_tokenA, _tokenB]) # dev: invalid tokens

    actualAmountA: uint256 = 0
    actualAmountB: uint256 = 0

    # handle token A
    if _amountA != 0:
        actualAmountA = min(_amountA, staticcall IERC20(_tokenA).balanceOf(msg.sender))
        if actualAmountA != 0:
            assert extcall IERC20(_tokenA).transferFrom(msg.sender, self, actualAmountA, default_return_value=True) # dev: transfer failed
            extcall MockToken(_tokenA).burn(actualAmountA)

    # handle token B  
    if _amountB != 0:
        actualAmountB = min(_amountB, staticcall IERC20(_tokenB).balanceOf(msg.sender))
        if actualAmountB != 0:
            assert extcall IERC20(_tokenB).transferFrom(msg.sender, self, actualAmountB, default_return_value=True) # dev: transfer failed
            extcall MockToken(_tokenB).burn(actualAmountB)

    # mint LP tokens (sum of both amounts)
    lpAmount: uint256 = actualAmountA + actualAmountB
    assert lpAmount != 0 # dev: nothing to add

    lpToken: address = self.lpToken
    extcall MockToken(lpToken).mint(_recipient, lpAmount)

    usdValue: uint256 = self._getUsdValue(_tokenA, actualAmountA, _tokenB, actualAmountB, miniAddys)
    return lpToken, lpAmount, actualAmountA, actualAmountB, usdValue


# remove liquidity


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
    assert not dld.isPaused # dev: paused
    miniAddys: ws.MiniAddys = dld._getMiniAddys(_miniAddys)

    assert self._areValidTokens([_tokenA, _tokenB, _lpToken]) # dev: invalid tokens
    assert _lpToken == self.lpToken # dev: invalid lp token

    # transfer and burn LP tokens
    actualLpAmount: uint256 = min(_lpAmount, staticcall IERC20(_lpToken).balanceOf(msg.sender))
    assert actualLpAmount != 0 # dev: nothing to remove
    assert extcall IERC20(_lpToken).transferFrom(msg.sender, self, actualLpAmount, default_return_value=True) # dev: transfer failed
    extcall MockToken(_lpToken).burn(actualLpAmount)

    # divide by half and mint asset tokens
    halfAmount: uint256 = actualLpAmount // 2
    extcall MockToken(self.asset).mint(_recipient, halfAmount)
    extcall MockToken(self.altAsset).mint(_recipient, halfAmount)

    usdValue: uint256 = self._getUsdValue(_tokenA, halfAmount, _tokenB, halfAmount, miniAddys)
    return halfAmount, halfAmount, actualLpAmount, usdValue


@internal
def _getUsdValue(
    _tokenA: address,
    _amountA: uint256,
    _tokenB: address,
    _amountB: uint256,
    _miniAddys: ws.MiniAddys,
) -> uint256:

    usdValueA: uint256 = 0
    if _amountA != 0:
        usdValueA = extcall Appraiser(_miniAddys.appraiser).updatePriceAndGetUsdValue(_tokenA, _amountA, _miniAddys.missionControl, _miniAddys.legoBook)

    usdValueB: uint256 = 0
    if _amountB != 0:
        usdValueB = extcall Appraiser(_miniAddys.appraiser).updatePriceAndGetUsdValue(_tokenB, _amountB, _miniAddys.missionControl, _miniAddys.legoBook)

    return usdValueA + usdValueB


###############
# Lego Access #
###############


@view
@external
def getAccessForLego(_user: address, _action: ws.ActionType) -> (address, String[64], uint256):
    if not self.hasAccess:
        return self, LEGO_ACCESS_ABI, 1
    return empty(address), empty(String[64]), 0


@external
def setLegoAccess(_addr: address):
    assert _addr == self # dev: invalid address
    self.hasAccess = True


@external
def revokeLegoAccess():
    # NOTE: for test setup purposes, to reset this
    self.hasAccess = False


#############
# Utilities #
#############


@view
@external
def getLpToken(_pool: address) -> address:
    return _pool


@view
@external
def getPoolForLpToken(_lpToken: address) -> address:
    return _lpToken


@view
@external
def getCoreRouterPool() -> address:
    return empty(address)


@view
@external
def getDeepestLiqPool(_tokenA: address, _tokenB: address) -> BestPool:
    return empty(BestPool)


@view
@external
def getBestSwapAmountOut(_tokenIn: address, _tokenOut: address, _amountIn: uint256) -> (address, uint256):
    return empty(address), 0


@view
@external
def getSwapAmountOut(
    _pool: address,
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256,
) -> uint256:
    return 0


@view
@external
def getBestSwapAmountIn(_tokenIn: address, _tokenOut: address, _amountOut: uint256) -> (address, uint256):
    return empty(address), 0


@view
@external
def getSwapAmountIn(
    _pool: address,
    _tokenIn: address,
    _tokenOut: address,
    _amountOut: uint256,
) -> uint256:
    return 0


@view
@external
def getAddLiqAmountsIn(
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _availAmountA: uint256,
    _availAmountB: uint256,
) -> (uint256, uint256, uint256):
    return 0, 0, 0


@view
@external
def getRemoveLiqAmountsOut(
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _lpAmount: uint256,
) -> (uint256, uint256):
    return 0, 0


@view
@external
def getPriceUnsafe(_pool: address, _targetToken: address, _appraiser: address = empty(address)) -> uint256:
    return 0


#########
# Other #
#########


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


@external
def depositForYield(
    _asset: address,
    _amount: uint256,
    _vaultAddr: address,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, address, uint256, uint256):
    return 0, empty(address), 0, 0


@external
def withdrawFromYield(
    _vaultToken: address,
    _amount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, address, uint256, uint256):
    return 0, empty(address), 0, 0
