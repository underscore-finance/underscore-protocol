# @version 0.4.3

implements: Lego

exports: addys.__interface__
exports: yld.__interface__

initializes: addys
initializes: yld[addys := addys]

from interfaces import LegoPartner as Lego
from interfaces import Wallet as wi

import contracts.modules.Addys as addys
import contracts.modules.YieldLegoData as yld

from ethereum.ercs import IERC20
from ethereum.ercs import IERC20Detailed

interface MockToken:
    def mint(_to: address, _value: uint256): nonpayable
    def burn(_value: uint256) -> bool: nonpayable

struct PendingMintOrRedeem:
    tokenIn: address
    tokenOut: address
    amount: uint256

asset: public(address)
vaultToken: public(address)
altAsset: public(address)
altVaultToken: public(address)
lpToken: public(address)
debtToken: public(address)

pendingMintOrRedeem: public(HashMap[address, PendingMintOrRedeem])
hasAccess: public(bool)

# mock price config
pricePerShare: public(HashMap[address, uint256])
price: public(HashMap[address, uint256])

EIGHTEEN_DECIMALS: constant(uint256) = 10 ** 18
MAX_TOKEN_PATH: constant(uint256) = 5
LEGO_ACCESS_ABI: constant(String[64]) = "setLegoAccess(address)"


@deploy
def __init__(
    _undyHq: address,
    _asset: address,
    _vaultToken: address,
    _altAsset: address,
    _altVaultToken: address,
    _lpToken: address,
    _debtToken: address,
):
    # modules
    addys.__init__(_undyHq)
    yld.__init__(False)

    # mock assets
    assert empty(address) not in [_asset, _vaultToken, _altAsset, _altVaultToken, _lpToken, _debtToken] # dev: invalid tokens
    self.asset = _asset
    self.vaultToken = _vaultToken
    self.altAsset = _altAsset
    self.altVaultToken = _altVaultToken
    self.lpToken = _lpToken
    self.debtToken = _debtToken
    self.hasAccess = False

    self.pricePerShare[_asset] = EIGHTEEN_DECIMALS
    self.price[_asset] = EIGHTEEN_DECIMALS
    self.pricePerShare[_vaultToken] = EIGHTEEN_DECIMALS
    self.price[_vaultToken] = EIGHTEEN_DECIMALS
    self.pricePerShare[_altAsset] = EIGHTEEN_DECIMALS
    self.price[_altAsset] = EIGHTEEN_DECIMALS
    self.pricePerShare[_altVaultToken] = EIGHTEEN_DECIMALS
    self.price[_altVaultToken] = EIGHTEEN_DECIMALS
    self.pricePerShare[_lpToken] = EIGHTEEN_DECIMALS
    self.price[_lpToken] = EIGHTEEN_DECIMALS
    self.pricePerShare[_debtToken] = EIGHTEEN_DECIMALS
    self.price[_debtToken] = EIGHTEEN_DECIMALS


@view
@external
def hasCapability(_action: wi.ActionType) -> bool:
    return _action in (
        wi.ActionType.EARN_DEPOSIT | 
        wi.ActionType.EARN_WITHDRAW | 
        wi.ActionType.SWAP | 
        wi.ActionType.MINT_REDEEM | 
        wi.ActionType.CONFIRM_MINT_REDEEM | 
        wi.ActionType.ADD_COLLATERAL | 
        wi.ActionType.REMOVE_COLLATERAL | 
        wi.ActionType.BORROW | 
        wi.ActionType.REPAY_DEBT | 
        wi.ActionType.REWARDS | 
        wi.ActionType.ADD_LIQ | 
        wi.ActionType.REMOVE_LIQ
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
    return False


#########
# Yield #
#########


# deposit


@external
def depositForYield(
    _asset: address,
    _amount: uint256,
    _vaultAddr: address,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
) -> (uint256, address, uint256, uint256):
    assert self._areValidTokens([_asset, _vaultAddr]) # dev: invalid tokens

    amount: uint256 = min(_amount, staticcall IERC20(_asset).balanceOf(msg.sender))
    assert amount != 0 # dev: nothing to transfer
    assert extcall IERC20(_asset).transferFrom(msg.sender, self, amount, default_return_value=True) # dev: transfer failed

    extcall MockToken(_asset).burn(amount)
    extcall MockToken(_vaultAddr).mint(_recipient, amount)

    # register lego asset
    if not yld._isAssetOpportunity(_asset, _vaultAddr):
        yld._addAssetOpportunity(_asset, _vaultAddr)

    return amount, _vaultAddr, amount, amount


# withdraw


@external
def withdrawFromYield(
    _vaultToken: address,
    _amount: uint256,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
) -> (uint256, address, uint256, uint256):
    assert self._areValidTokens([_vaultToken]) # dev: invalid tokens

    amount: uint256 = min(_amount, staticcall IERC20(_vaultToken).balanceOf(msg.sender))
    assert amount != 0 # dev: nothing to transfer
    assert extcall IERC20(_vaultToken).transferFrom(msg.sender, self, amount, default_return_value=True) # dev: transfer failed

    asset: address = self.asset
    extcall MockToken(_vaultToken).burn(amount)
    extcall MockToken(asset).mint(_recipient, amount)

    # register lego asset
    if not yld._isAssetOpportunity(asset, _vaultToken):
        yld._addAssetOpportunity(asset, _vaultToken)

    return amount, asset, amount, amount


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
) -> (uint256, uint256, uint256):
    assert len(_tokenPath) >= 2 # dev: invalid token path
    tokenIn: address = _tokenPath[0]
    tokenOut: address = _tokenPath[len(_tokenPath) - 1]
    assert self._areValidTokens([tokenIn, tokenOut]) # dev: invalid tokens

    amount: uint256 = min(_amountIn, staticcall IERC20(tokenIn).balanceOf(msg.sender))
    assert amount != 0 # dev: nothing to transfer
    assert extcall IERC20(tokenIn).transferFrom(msg.sender, self, amount, default_return_value=True) # dev: transfer failed

    extcall MockToken(tokenIn).burn(amount)
    extcall MockToken(tokenOut).mint(_recipient, amount)

    return amount, amount, amount
    

# mint / redeem


@external
def mintOrRedeemAsset(
    _tokenIn: address,
    _tokenOut: address,
    _tokenInAmount: uint256,
    _minAmountOut: uint256,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
) -> (uint256, uint256, bool, uint256):
    assert self._areValidTokens([_tokenIn, _tokenOut]) # dev: invalid tokens

    amount: uint256 = min(_tokenInAmount, staticcall IERC20(_tokenIn).balanceOf(msg.sender))
    assert amount != 0 # dev: nothing to transfer
    assert extcall IERC20(_tokenIn).transferFrom(msg.sender, self, amount, default_return_value=True) # dev: transfer failed
    extcall MockToken(_tokenIn).burn(amount)

    # immediate mint (default)
    usdValue: uint256 = 0
    if _extraVal == 0:
        extcall MockToken(_tokenOut).mint(_recipient, amount)
        usdValue = amount

    # create pending mint
    else:
        self.pendingMintOrRedeem[msg.sender] = PendingMintOrRedeem(
            tokenIn = _tokenIn,
            tokenOut = _tokenOut,
            amount = amount,
        )
        amount = 0

    return amount, amount, _extraVal != 0, usdValue
    

@external
def confirmMintOrRedeemAsset(
    _tokenIn: address,
    _tokenOut: address,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
) -> (uint256, uint256):
    pending: PendingMintOrRedeem = self.pendingMintOrRedeem[msg.sender]
    assert pending.tokenIn == _tokenIn and pending.tokenOut == _tokenOut # dev: invalid tokens
    assert pending.amount != 0 # dev: nothing to confirm

    extcall MockToken(pending.tokenOut).mint(_recipient, pending.amount)
    self.pendingMintOrRedeem[msg.sender] = empty(PendingMintOrRedeem)

    return pending.amount, pending.amount


########
# Debt #
########


@external
def addCollateral(
    _asset: address,
    _amount: uint256,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
) -> (uint256, uint256):
    assert self._areValidTokens([_asset]) # dev: invalid tokens
    assert self.hasAccess # dev: no access

    amount: uint256 = min(_amount, staticcall IERC20(_asset).balanceOf(msg.sender))
    assert amount != 0 # dev: nothing to transfer
    assert extcall IERC20(_asset).transferFrom(msg.sender, self, amount, default_return_value=True) # dev: transfer failed

    extcall MockToken(_asset).burn(amount)
    return amount, amount


@external
def removeCollateral(
    _asset: address,
    _amount: uint256,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
) -> (uint256, uint256):
    assert self._areValidTokens([_asset]) # dev: invalid tokens
    assert self.hasAccess # dev: no access

    extcall MockToken(_asset).mint(_recipient, _amount)
    return _amount, _amount


@external
def borrow(
    _borrowAsset: address,
    _amount: uint256,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
) -> (uint256, uint256):
    assert _borrowAsset == self.debtToken # dev: invalid borrow asset
    assert self.hasAccess # dev: no access

    assert _amount != 0 # dev: nothing to borrow
    assert _amount != max_value(uint256) # dev: too high

    extcall MockToken(_borrowAsset).mint(_recipient, _amount)
    return _amount, _amount


@external
def repayDebt(
    _paymentAsset: address,
    _paymentAmount: uint256,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
) -> (uint256, uint256):
    assert _paymentAsset == self.debtToken # dev: invalid payment asset
    assert self.hasAccess # dev: no access

    amount: uint256 = min(_paymentAmount, staticcall IERC20(_paymentAsset).balanceOf(msg.sender))
    assert amount != 0 # dev: nothing to repay
    assert extcall IERC20(_paymentAsset).transferFrom(msg.sender, self, amount, default_return_value=True) # dev: transfer failed

    extcall MockToken(_paymentAsset).burn(amount)
    return amount, amount


#################
# Claim Rewards #
#################


@external
def claimRewards(
    _user: address,
    _rewardToken: address,
    _rewardAmount: uint256,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
) -> (uint256, uint256):
    assert self._areValidTokens([_rewardToken]) # dev: invalid tokens
    assert self.hasAccess # dev: no access

    extcall MockToken(_rewardToken).mint(_user, _rewardAmount)
    return _rewardAmount, _rewardAmount


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
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
) -> (address, uint256, uint256, uint256, uint256):
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
    return lpToken, lpAmount, actualAmountA, actualAmountB, lpAmount


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
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
) -> (uint256, uint256, uint256, uint256):
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

    return halfAmount, halfAmount, actualLpAmount, actualLpAmount


# concentrated liquidity


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
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
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
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
) -> (uint256, uint256, uint256, bool, uint256):
    return 0, 0, 0, False, 0


###############
# Lego Access #
###############


@view
@external
def getAccessForLego(_user: address, _action: wi.ActionType) -> (address, String[64], uint256):
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


#########
# Utils #
#########


@view
@internal
def _areValidTokens(_tokens: DynArray[address, 6]) -> bool:
    validTokens: address[6] = [self.asset, self.vaultToken, self.altAsset, self.altVaultToken, self.lpToken, self.debtToken]
    for t: address in _tokens:
        if t in validTokens:
            continue
        return False
    return True


#################
# Price Support #
#################


# price per share


@view
@external
def getPricePerShare(_yieldAsset: address) -> uint256:
    return self.pricePerShare[_yieldAsset]


# normal price (not yield)


@view
@external
def getPrice(_asset: address) -> uint256:
    return self.price[_asset]


# MOCK config


@external
def setPricePerShare(_yieldAsset: address, _pricePerShare: uint256):
    self.pricePerShare[_yieldAsset] = _pricePerShare


@external
def setPrice(_asset: address, _price: uint256):
    self.price[_asset] = _price