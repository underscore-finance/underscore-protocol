#     __   __ ___ _______ ___     ______       ___     _______ _______ _______ 
#    |  | |  |   |       |   |   |      |     |   |   |       |       |       |
#    |  |_|  |   |    ___|   |   |  _    |    |   |   |    ___|    ___|   _   |
#    |       |   |   |___|   |   | | |   |    |   |   |   |___|   | __|  | |  |
#    |_     _|   |    ___|   |___| |_|   |    |   |___|    ___|   ||  |  |_|  |
#      |   | |   |   |___|       |       |    |       |   |___|   |_| |       |
#      |___| |___|_______|_______|______|     |_______|_______|_______|_______|
#                                                                       
#     ╔═══════════════════════════════════════════╗
#     ║  ** Undy Rewards Lego **                  ║
#     ║  Integration with Undy Protocol           ║
#     ╚═══════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

implements: Lego

exports: addys.__interface__

initializes: addys

from interfaces import LegoPartner as Lego
from interfaces import WalletStructs as ws

import contracts.modules.Addys as addys

from ethereum.ercs import IERC20

interface LootDistributor:
    def claimRevShareAndBonusLoot(_user: address) -> uint256: nonpayable
    def getClaimableDepositRewards(_user: address) -> uint256: view
    def claimDepositRewards(_user: address) -> uint256: nonpayable
    def getTotalClaimableAssets(_user: address) -> uint256: view

interface Appraiser:
    def updatePriceAndGetUsdValue(_asset: address, _amount: uint256, _missionControl: address = empty(address), _legoBook: address = empty(address)) -> uint256: nonpayable

interface Ledger:
    def isUserWallet(_user: address) -> bool: view

MAX_TOKEN_PATH: constant(uint256) = 5
RIPE_TOKEN: immutable(address)

@deploy
def __init__(_undyHq: address, _ripeToken: address):
    addys.__init__(_undyHq)
    RIPE_TOKEN = _ripeToken


##############
# Claim Loot #
##############


@external
def claimRewards(
    _user: address,
    _rewardToken: address,
    _rewardAmount: uint256,
    _extraData: bytes32,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    assert staticcall Ledger(addys._getLedgerAddr()).isUserWallet(msg.sender) # dev: not a user wallet
    assert msg.sender == _user # dev: recipient must be caller

    lootDistributor: address = addys._getLootDistributorAddr()

    # rev share and loot bonus
    totalClaimableAssets: uint256 = staticcall LootDistributor(lootDistributor).getTotalClaimableAssets(_user)
    if totalClaimableAssets != 0:
        extcall LootDistributor(lootDistributor).claimRevShareAndBonusLoot(_user)

    # deposit rewards
    depositRewards: uint256 = staticcall LootDistributor(lootDistributor).getClaimableDepositRewards(_user)
    if depositRewards != 0:
        depositRewards = extcall LootDistributor(lootDistributor).claimDepositRewards(_user)

    appraiser: address = addys._getAppraiserAddr()
    usdValue: uint256 = extcall Appraiser(appraiser).updatePriceAndGetUsdValue(_rewardToken, depositRewards)
    if _rewardToken == RIPE_TOKEN:
        return 0, usdValue
    return depositRewards, usdValue


@view
@external
def hasClaimableRewards(_user: address) -> bool:
    lootDistributor: address = addys._getLootDistributorAddr()
    totalClaimableAssets: uint256 = staticcall LootDistributor(lootDistributor).getTotalClaimableAssets(_user)
    if totalClaimableAssets != 0:
        return True
    depositRewards: uint256 = staticcall LootDistributor(lootDistributor).getClaimableDepositRewards(_user)
    return depositRewards != 0


#########
# Other #
#########


@view
@external
def hasCapability(_action: ws.ActionType) -> bool:
    return _action == ws.ActionType.REWARDS

@view
@external
def getRegistries() -> DynArray[address, 10]:
    return []

@view
@external
def isDexLego() -> bool:
    return False

@view
@external
def isYieldLego() -> bool:
    return False

@view
@external
def isPaused() -> bool:
    return False

@view
@external
def getPricePerShare(_asset: address, _decimals: uint256) -> uint256:
    return 0

@view
@external
def getPrice(_asset: address, _decimals: uint256) -> uint256:
    return 0

@view
@external
def getAccessForLego(_user: address, _action: ws.ActionType) -> (address, String[64], uint256):
    return empty(address), empty(String[64]), 0

@external
def pause(_shouldPause: bool):
    pass

@external
def recoverFunds(_recipient: address, _asset: address):
    pass

@external
def recoverFundsMany(_recipient: address, _assets: DynArray[address, 20]):
    pass

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
def addCollateral(
    _asset: address,
    _amount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    return 0, 0

@external
def removeCollateral(
    _asset: address,
    _amount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    return 0, 0

@external
def borrow(
    _borrowAsset: address,
    _amount: uint256,
    _extraData: bytes32,
    _recipient: address,
    _miniAddys: ws.MiniAddys = empty(ws.MiniAddys),
) -> (uint256, uint256):
    return 0, 0

@external
def repayDebt(
    _paymentAsset: address,
    _paymentAmount: uint256,
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
