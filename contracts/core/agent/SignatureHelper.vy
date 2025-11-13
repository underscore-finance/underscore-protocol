#     ╔════════════════════════════════════════════════════════════════════════════════╗
#     ║  ** Signature Helper **                                                        ║
#     ║  Generates message hashes for AgentWrapper signatures                          ║
#     ╚════════════════════════════════════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3
# pragma optimize codesize

import contracts.modules.SigHelper as sigHelper

from interfaces import Wallet

struct ActionInstruction:
    usePrevAmountOut: bool     # Use output from previous instruction as amount
    action: uint8              # Action type: 1=transfer, 2=weth2eth, 3=eth2weth, 10=depositYield, 11=withdrawYield, 12=rebalanceYield, 20=swap, 21=mint/redeem, 22=confirmMint/redeem, 30=addLiq, 31=removeLiq, 32=addLiqConc, 33=removeLiqConc, 40=addCollateral, 41=removeCollateral, 42=borrow, 43=repay, 50=claimRewards
    legoId: uint16             # Protocol/Lego ID (use amount2 for toLegoId in rebalance)
    asset: address             # Primary asset/token (or vaultToken for withdrawals)
    target: address            # Varies: recipient/vaultAddr/tokenOut/pool based on action
    amount: uint256            # Primary amount (or max_value for "all")
    asset2: address            # Secondary asset (tokenB for liquidity ops)
    amount2: uint256           # Varies: amountB for liquidity, toLegoId for rebalance
    minOut1: uint256           # Min output for primary asset (or minAmountOut)
    minOut2: uint256           # Min output for secondary asset (liquidity ops)
    tickLower: int24           # For concentrated liquidity positions
    tickUpper: int24           # For concentrated liquidity positions
    extraData: bytes32         # Protocol-specific extra data (LSB used for isCheque in transfers)
    auxData: bytes32           # Packed data: lpToken addr (action 15) or pool+nftId (16-17)
    swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS]

MAX_INSTRUCTIONS: constant(uint256) = 15
MAX_SWAP_INSTRUCTIONS: constant(uint256) = 5


##################
# Transfer Funds #
##################


@view
@external
def getTransferFundsHash(
    _agentWrapper: address,
    _userWallet: address,
    _recipient: address,
    _asset: address = empty(address),
    _amount: uint256 = max_value(uint256),
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for transferFunds function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentWrapper, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentWrapper, keccak256(abi_encode(convert(1, uint8), _userWallet, _recipient, _asset, _amount, nonce, expiration))), nonce, expiration)


#########
# Yield #
#########


@view
@external
def getDepositForYieldHash(
    _agentWrapper: address,
    _userWallet: address,
    _legoId: uint256,
    _asset: address,
    _vaultAddr: address = empty(address),
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for depositForYield function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentWrapper, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentWrapper, keccak256(abi_encode(convert(10, uint8), _userWallet, _legoId, _asset, _vaultAddr, _amount, _extraData, nonce, expiration))), nonce, expiration)


@view
@external
def getWithdrawFromYieldHash(
    _agentWrapper: address,
    _userWallet: address,
    _legoId: uint256,
    _vaultToken: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for withdrawFromYield function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentWrapper, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentWrapper, keccak256(abi_encode(convert(11, uint8), _userWallet, _legoId, _vaultToken, _amount, _extraData, nonce, expiration))), nonce, expiration)


@view
@external
def getRebalanceYieldPositionHash(
    _agentWrapper: address,
    _userWallet: address,
    _fromLegoId: uint256,
    _fromVaultToken: address,
    _toLegoId: uint256,
    _toVaultAddr: address = empty(address),
    _fromVaultAmount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for rebalanceYieldPosition function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentWrapper, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentWrapper, keccak256(abi_encode(convert(12, uint8), _userWallet, _fromLegoId, _fromVaultToken, _toLegoId, _toVaultAddr, _fromVaultAmount, _extraData, nonce, expiration))), nonce, expiration)


###################
# Swap / Exchange #
###################


@view
@external
def getSwapTokensHash(
    _agentWrapper: address,
    _userWallet: address,
    _swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS],
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for swapTokens function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentWrapper, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentWrapper, keccak256(abi_encode(convert(20, uint8), _userWallet, _swapInstructions, nonce, expiration))), nonce, expiration)


@view
@external
def getMintOrRedeemAssetHash(
    _agentWrapper: address,
    _userWallet: address,
    _legoId: uint256,
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256 = max_value(uint256),
    _minAmountOut: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for mintOrRedeemAsset function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentWrapper, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentWrapper, keccak256(abi_encode(convert(21, uint8), _userWallet, _legoId, _tokenIn, _tokenOut, _amountIn, _minAmountOut, _extraData, nonce, expiration))), nonce, expiration)


@view
@external
def getConfirmMintOrRedeemAssetHash(
    _agentWrapper: address,
    _userWallet: address,
    _legoId: uint256,
    _tokenIn: address,
    _tokenOut: address,
    _extraData: bytes32 = empty(bytes32),
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for confirmMintOrRedeemAsset function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentWrapper, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentWrapper, keccak256(abi_encode(convert(22, uint8), _userWallet, _legoId, _tokenIn, _tokenOut, _extraData, nonce, expiration))), nonce, expiration)


###################
# Debt Management #
###################


@view
@external
def getAddCollateralHash(
    _agentWrapper: address,
    _userWallet: address,
    _legoId: uint256,
    _asset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for addCollateral function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentWrapper, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentWrapper, keccak256(abi_encode(convert(40, uint8), _userWallet, _legoId, _asset, _amount, _extraData, nonce, expiration))), nonce, expiration)


@view
@external
def getRemoveCollateralHash(
    _agentWrapper: address,
    _userWallet: address,
    _legoId: uint256,
    _asset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for removeCollateral function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentWrapper, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentWrapper, keccak256(abi_encode(convert(41, uint8), _userWallet, _legoId, _asset, _amount, _extraData, nonce, expiration))), nonce, expiration)


@view
@external
def getBorrowHash(
    _agentWrapper: address,
    _userWallet: address,
    _legoId: uint256,
    _borrowAsset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for borrow function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentWrapper, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentWrapper, keccak256(abi_encode(convert(42, uint8), _userWallet, _legoId, _borrowAsset, _amount, _extraData, nonce, expiration))), nonce, expiration)


@view
@external
def getRepayDebtHash(
    _agentWrapper: address,
    _userWallet: address,
    _legoId: uint256,
    _paymentAsset: address,
    _paymentAmount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for repayDebt function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentWrapper, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentWrapper, keccak256(abi_encode(convert(43, uint8), _userWallet, _legoId, _paymentAsset, _paymentAmount, _extraData, nonce, expiration))), nonce, expiration)


#################
# Claim Rewards #
#################


@view
@external
def getClaimRewardsHash(
    _agentWrapper: address,
    _userWallet: address,
    _legoId: uint256,
    _rewardToken: address = empty(address),
    _rewardAmount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for claimRewards function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentWrapper, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentWrapper, keccak256(abi_encode(convert(50, uint8), _userWallet, _legoId, _rewardToken, _rewardAmount, _extraData, nonce, expiration))), nonce, expiration)


###############
# Wrapped ETH #
###############


@view
@external
def getConvertWethToEthHash(
    _agentWrapper: address,
    _userWallet: address,
    _amount: uint256 = max_value(uint256),
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for convertWethToEth function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentWrapper, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentWrapper, keccak256(abi_encode(convert(2, uint8), _userWallet, _amount, nonce, expiration))), nonce, expiration)


@view
@external
def getConvertEthToWethHash(
    _agentWrapper: address,
    _userWallet: address,
    _amount: uint256 = max_value(uint256),
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for convertEthToWeth function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentWrapper, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentWrapper, keccak256(abi_encode(convert(3, uint8), _userWallet, _amount, nonce, expiration))), nonce, expiration)


#############
# Liquidity #
#############


@view
@external
def getAddLiquidityHash(
    _agentWrapper: address,
    _userWallet: address,
    _legoId: uint256,
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _amountA: uint256 = max_value(uint256),
    _amountB: uint256 = max_value(uint256),
    _minAmountA: uint256 = 0,
    _minAmountB: uint256 = 0,
    _minLpAmount: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for addLiquidity function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentWrapper, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentWrapper, keccak256(abi_encode(convert(30, uint8), _userWallet, _legoId, _pool, _tokenA, _tokenB, _amountA, _amountB, _minAmountA, _minAmountB, _minLpAmount, _extraData, nonce, expiration))), nonce, expiration)


@view
@external
def getRemoveLiquidityHash(
    _agentWrapper: address,
    _userWallet: address,
    _legoId: uint256,
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _lpToken: address,
    _lpAmount: uint256 = max_value(uint256),
    _minAmountA: uint256 = 0,
    _minAmountB: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for removeLiquidity function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentWrapper, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentWrapper, keccak256(abi_encode(convert(31, uint8), _userWallet, _legoId, _pool, _tokenA, _tokenB, _lpToken, _lpAmount, _minAmountA, _minAmountB, _extraData, nonce, expiration))), nonce, expiration)


@view
@external
def getAddLiquidityConcentratedHash(
    _agentWrapper: address,
    _userWallet: address,
    _legoId: uint256,
    _nftAddr: address,
    _nftTokenId: uint256,
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _amountA: uint256 = max_value(uint256),
    _amountB: uint256 = max_value(uint256),
    _tickLower: int24 = min_value(int24),
    _tickUpper: int24 = max_value(int24),
    _minAmountA: uint256 = 0,
    _minAmountB: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for addLiquidityConcentrated function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentWrapper, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentWrapper, keccak256(abi_encode(convert(32, uint8), _userWallet, _legoId, _nftAddr, _nftTokenId, _pool, _tokenA, _tokenB, _amountA, _amountB, _tickLower, _tickUpper, _minAmountA, _minAmountB, _extraData, nonce, expiration))), nonce, expiration)


@view
@external
def getRemoveLiquidityConcentratedHash(
    _agentWrapper: address,
    _userWallet: address,
    _legoId: uint256,
    _nftAddr: address,
    _nftTokenId: uint256,
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _liqToRemove: uint256 = max_value(uint256),
    _minAmountA: uint256 = 0,
    _minAmountB: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for removeLiquidityConcentrated function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentWrapper, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentWrapper, keccak256(abi_encode(convert(33, uint8), _userWallet, _legoId, _nftAddr, _nftTokenId, _pool, _tokenA, _tokenB, _liqToRemove, _minAmountA, _minAmountB, _extraData, nonce, expiration))), nonce, expiration)


#################
# Batch Actions #
#################


@view
@external
def getBatchActionsHash(
    _agentWrapper: address,
    _userWallet: address,
    _instructions: DynArray[ActionInstruction, MAX_INSTRUCTIONS],
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for performBatchActions function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentWrapper, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentWrapper, keccak256(abi_encode(_userWallet, _instructions, nonce, expiration))), nonce, expiration)

