# @version 0.4.3

implements: Lego

exports: addys.__interface__
exports: legoAssets.__interface__

initializes: addys
initializes: legoAssets[addys := addys]

from interfaces import LegoPartner as Lego
from interfaces import Wallet as wi

import contracts.modules.Addys as addys
import contracts.modules.LegoAssets as legoAssets

from ethereum.ercs import IERC20
from ethereum.ercs import IERC20Detailed
from ethereum.ercs import IERC4626
from ethereum.ercs import IERC721

interface Appraiser:
    def updatePriceAndGetUsdValue(_asset: address, _amount: uint256) -> uint256: nonpayable

MAX_TOKEN_PATH: constant(uint256) = 5

# mock price config
price: public(HashMap[address, uint256])


@deploy
def __init__(_undyHq: address):
    addys.__init__(_undyHq)
    legoAssets.__init__(False)


@view
@external
def hasCapability(_action: wi.ActionType) -> bool:
    return _action in (
        wi.ActionType.EARN_DEPOSIT | 
        wi.ActionType.EARN_WITHDRAW |
        wi.ActionType.ADD_LIQ_CONC |
        wi.ActionType.REMOVE_LIQ_CONC
    )


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

    # pre balances
    preLegoBalance: uint256 = staticcall IERC20(_asset).balanceOf(self)

    amount: uint256 = min(_amount, staticcall IERC20(_asset).balanceOf(msg.sender))
    assert amount != 0 # dev: nothing to transfer
    assert extcall IERC20(_asset).transferFrom(msg.sender, self, amount, default_return_value=True) # dev: transfer failed

    # deposit assets into lego partner
    depositAmount: uint256 = min(amount, staticcall IERC20(_asset).balanceOf(self))
    vaultTokenAmountReceived: uint256 = extcall IERC4626(_vaultAddr).deposit(depositAmount, _recipient)
    assert vaultTokenAmountReceived != 0 # dev: no vault tokens received

    # refund if full deposit didn't get through
    currentLegoBalance: uint256 = staticcall IERC20(_asset).balanceOf(self)
    refundAssetAmount: uint256 = 0
    if currentLegoBalance > preLegoBalance:
        refundAssetAmount = currentLegoBalance - preLegoBalance
        assert extcall IERC20(_asset).transfer(msg.sender, refundAssetAmount, default_return_value=True) # dev: transfer failed
        depositAmount -= refundAssetAmount

    # usd value
    usdValue: uint256 = extcall Appraiser(addys._getAppraiserAddr()).updatePriceAndGetUsdValue(_asset, depositAmount)

    # register lego asset
    legoAssets._registerLegoAsset(_asset)

    return depositAmount, _vaultAddr, vaultTokenAmountReceived, usdValue


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

    # pre balances
    preLegoVaultBalance: uint256 = staticcall IERC20(_vaultToken).balanceOf(self)

    # transfer vaults tokens to this contract
    amount: uint256 = min(_amount, staticcall IERC20(_vaultToken).balanceOf(msg.sender))
    assert amount != 0 # dev: nothing to transfer
    assert extcall IERC20(_vaultToken).transferFrom(msg.sender, self, amount, default_return_value=True) # dev: transfer failed

    # withdraw assets from lego partner
    vaultTokenAmount: uint256 = min(amount, staticcall IERC20(_vaultToken).balanceOf(self))
    assetAmountReceived: uint256 = extcall IERC4626(_vaultToken).redeem(vaultTokenAmount, _recipient, self)
    assert assetAmountReceived != 0 # dev: no asset amount received

    # refund if full withdrawal didn't happen
    currentLegoVaultBalance: uint256 = staticcall IERC20(_vaultToken).balanceOf(self)
    refundVaultTokenAmount: uint256 = 0
    if currentLegoVaultBalance > preLegoVaultBalance:
        refundVaultTokenAmount = currentLegoVaultBalance - preLegoVaultBalance
        assert extcall IERC20(_vaultToken).transfer(msg.sender, refundVaultTokenAmount, default_return_value=True) # dev: transfer failed
        vaultTokenAmount -= refundVaultTokenAmount

    # usd value
    asset: address = staticcall IERC4626(_vaultToken).asset()
    usdValue: uint256 = extcall Appraiser(addys._getAppraiserAddr()).updatePriceAndGetUsdValue(asset, assetAmountReceived)

    return vaultTokenAmount, asset, assetAmountReceived, usdValue


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
) -> (uint256, uint256, uint256):
    return 0, 0, 0


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
    return 0, 0, False, 0
    

@external
def confirmMintOrRedeemAsset(
    _tokenIn: address,
    _tokenOut: address,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
) -> (uint256, uint256):
    return 0, 0


@external
def addCollateral(
    _asset: address,
    _amount: uint256,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
) -> (uint256, uint256):
    return 0, 0


@external
def removeCollateral(
    _asset: address,
    _amount: uint256,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
) -> (uint256, uint256):
    return 0, 0


@external
def borrow(
    _borrowAsset: address,
    _amount: uint256,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
) -> (uint256, uint256):
    return 0, 0


@external
def repayDebt(
    _paymentAsset: address,
    _paymentAmount: uint256,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
) -> (uint256, uint256):
    return 0, 0


@external
def claimRewards(
    _user: address,
    _rewardToken: address,
    _rewardAmount: uint256,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
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
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
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
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
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
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _recipient: address,
) -> (uint256, uint256, uint256, uint256, uint256):
    # Transfer tokens from sender (simulate liquidity add)
    if _amountA > 0:
        assert extcall IERC20(_tokenA).transferFrom(msg.sender, self, _amountA, default_return_value=True)
    if _amountB > 0:
        assert extcall IERC20(_tokenB).transferFrom(msg.sender, self, _amountB, default_return_value=True)
    
    # For concentrated liquidity, _extraAddr should contain the NFT manager address
    # The actual NFT token ID handling:
    nftTokenId: uint256 = _nftTokenId
    
    if _nftTokenId == 0:
        # New position - we use a predetermined token ID
        # In the test, we pre-mint token ID 1 to the wallet
        nftTokenId = 1
    else:
        # Existing position - NFT was transferred to us, transfer it back
        if _extraAddr != empty(address):
            extcall IERC721(_extraAddr).transferFrom(self, _recipient, _nftTokenId)
    
    # Mock liquidity amount (sum of amounts)
    liquidity: uint256 = _amountA + _amountB
    
    # Mock USD value
    usdValue: uint256 = liquidity
    
    return nftTokenId, _amountA, _amountB, liquidity, usdValue


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
    # Mock removing liquidity - return half to each token
    amountA: uint256 = _liqToRemove // 2
    amountB: uint256 = _liqToRemove // 2
    
    # Transfer tokens to recipient (simulate liquidity removal)
    if amountA > 0 and staticcall IERC20(_tokenA).balanceOf(self) >= amountA:
        assert extcall IERC20(_tokenA).transfer(_recipient, amountA, default_return_value=True)
    if amountB > 0 and staticcall IERC20(_tokenB).balanceOf(self) >= amountB:
        assert extcall IERC20(_tokenB).transfer(_recipient, amountB, default_return_value=True)
    
    # The NFT was transferred to us before this call
    # We need to transfer it back unless the position is depleted
    # For simplicity, we'll say it's not depleted
    isDepleted: bool = False
    
    # Transfer NFT back to recipient if not depleted
    # _extraAddr contains the NFT manager address
    if not isDepleted and _extraAddr != empty(address):
        extcall IERC721(_extraAddr).transferFrom(self, _recipient, _nftTokenId)
    
    # Mock USD value
    usdValue: uint256 = _liqToRemove
    
    return amountA, amountB, _liqToRemove, isDepleted, usdValue


@view
@external
def getAccessForLego(_user: address, _action: wi.ActionType) -> (address, String[64], uint256):
    return empty(address), empty(String[64]), 0


#################
# Price Support #
#################


# price per share


@view
@external
def getPricePerShare(_yieldAsset: address) -> uint256:
    decimals: uint256 = convert(staticcall IERC20Detailed(_yieldAsset).decimals(), uint256)
    return staticcall IERC4626(_yieldAsset).convertToAssets(10 ** decimals)


# normal price (not yield)


@view
@external
def getPrice(_asset: address) -> uint256:
    return self.price[_asset]


@external
def onERC721Received(_operator: address, _from: address, _tokenId: uint256, _data: Bytes[1024]) -> bytes4:
    """
    ERC721 receiver function to accept NFT transfers.
    Returns the correct selector to indicate successful receipt.
    """
    # ERC721_RECEIVE_DATA = 0x150b7a02
    return 0x150b7a02


# mock (set price)


@external
def setPrice(_asset: address, _price: uint256):
    self.price[_asset] = _price