#            _            _            _             _            _            _      
#           / /\         /\ \         /\ \     _    /\ \         /\ \         /\ \    
#          / /  \       /  \ \       /  \ \   /\_\ /  \ \____   /  \ \       /  \ \   
#         / / /\ \__   / /\ \ \     / /\ \ \_/ / // /\ \_____\ / /\ \ \     / /\ \ \  
#        / / /\ \___\ / / /\ \_\   / / /\ \___/ // / /\/___  // / /\ \_\   / / /\ \_\ 
#        \ \ \ \/___// /_/_ \/_/  / / /  \/____// / /   / / // /_/_ \/_/  / / /_/ / / 
#         \ \ \     / /____/\    / / /    / / // / /   / / // /____/\    / / /__\/ /  
#     _    \ \ \   / /\____\/   / / /    / / // / /   / / // /\____\/   / / /_____/   
#    /_/\__/ / /  / / /______  / / /    / / / \ \ \__/ / // / /______  / / /\ \ \     
#    \ \/___/ /  / / /_______\/ / /    / / /   \ \___\/ // / /_______\/ / /  \ \ \    
#     \_____\/   \/__________/\/_/     \/_/     \/_____/ \/__________/\/_/    \_\/    
#
#     ╔═══════════════════════════════════════════════════════════════════╗
#     ║  ** Agent Sender - Generic **                                     ║
#     ║  Generic sender with batch actions and signature verification.    ║
#     ╚═══════════════════════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3
# pragma optimize codesize

initializes: ownership
exports: ownership.__interface__
import contracts.modules.Ownership as ownership

from interfaces import Wallet
from interfaces import AgentWrapper
from interfaces import WalletStructs as ws
from interfaces import WalletConfigStructs as wcs

interface UserWalletConfig:
    def cheques(_recipient: address) -> wcs.Cheque: view

interface UserWallet:
    def walletConfig() -> address: view

struct Signature:
    signature: Bytes[65]
    nonce: uint256
    expiration: uint256

struct ActionInstruction:
    usePrevAmountOut: bool     # Use output from previous instruction as amount
    action: uint8              # 1=transfer, 4=createAndPayCheque, 6=payCheque, 10-12=yield, 20-22=swap/exchange, 30-33=liq, 40-43=debt, 50=claimIncentives, 60-62=whitelist, 80-82=loot
    legoId: uint16             # Protocol/Lego ID (use amount2 for toLegoId in rebalance)
    asset: address             # Primary asset/token (or vaultToken for withdrawals)
    target: address            # Varies: recipient/vaultAddr/tokenOut/pool based on action
    amount: uint256            # Primary amount (or max_value for "all")
    asset2: address            # Secondary asset (tokenB for liquidity ops)
    amount2: uint256           # Varies: amountB for liquidity, toLegoId for rebalance, expectedCreationBlock for action 6 payCheque
    minOut1: uint256           # Min output for primary asset (or minAmountOut)
    minOut2: uint256           # Min output for secondary asset (liquidity ops)
    tickLower: int24           # For concentrated liquidity positions
    tickUpper: int24           # For concentrated liquidity positions
    extraData: bytes32         # Protocol-specific extra data
    auxData: bytes32           # Packed data: lpToken addr (action 31) or pool+nftId (32-33)
    swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS]
    proofs: DynArray[bytes32, MAX_PROOFS]  # Merkle proofs for claimIncentives (action 50)

event NonceIncremented:
    userWallet: address
    oldNonce: uint256
    newNonce: uint256

currentNonce: public(HashMap[address, uint256])

MAX_INSTRUCTIONS: constant(uint256) = 15
MAX_SWAP_INSTRUCTIONS: constant(uint256) = 5
MAX_PROOFS: constant(uint256) = 25
MAX_DELEVERAGE_WALLET_ASSETS: constant(uint256) = 10

# unified signature validation
ECRECOVER_PRECOMPILE: constant(address) = 0x0000000000000000000000000000000000000001
SIG_PREFIX: constant(bytes32) = 0x1901000000000000000000000000000000000000000000000000000000000000


@deploy
def __init__(
    _undyHq: address,
    _owner: address,
    _minTimeLock: uint256,
    _maxTimeLock: uint256,
):
    ownership.__init__(_undyHq, _owner, _minTimeLock, _maxTimeLock)


##################
# Transfer Funds #
##################


@external
def transferFunds(
    _agentWrapper: address,
    _userWallet: address,
    _recipient: address,
    _asset: address = empty(address),
    _amount: uint256 = max_value(uint256),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(1, uint8), _agentWrapper, _userWallet, _recipient, _asset, _amount, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).transferFunds(_userWallet, _recipient, _asset, _amount)


@external
def createAndPayCheque(
    _agentWrapper: address,
    _userWallet: address,
    _recipient: address,
    _asset: address,
    _amount: uint256,
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(4, uint8), _agentWrapper, _userWallet, _recipient, _asset, _amount, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).createAndPayCheque(_userWallet, _recipient, _asset, _amount)


@external
def createCheque(
    _agentWrapper: address,
    _userWallet: address,
    _recipient: address,
    _asset: address,
    _amount: uint256,
    _unlockNumBlocks: uint256,
    _expiryNumBlocks: uint256,
    _canManagerPay: bool,
    _canBePulled: bool,
    _sig: Signature = empty(Signature),
) -> bool:
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(5, uint8), _agentWrapper, _userWallet, _recipient, _asset, _amount, _unlockNumBlocks, _expiryNumBlocks, _canManagerPay, _canBePulled, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).createCheque(_userWallet, _recipient, _asset, _amount, _unlockNumBlocks, _expiryNumBlocks, _canManagerPay, _canBePulled)


# Signed-message version guard: old signatures must not pay replaced cheques.
@view
@internal
def _assertChequeVersionMatches(_userWallet: address, _recipient: address, _expectedCreationBlock: uint256):
    assert _expectedCreationBlock != 0 # dev: invalid expected block
    walletConfig: address = staticcall UserWallet(_userWallet).walletConfig()
    cheque: wcs.Cheque = staticcall UserWalletConfig(walletConfig).cheques(_recipient)
    assert cheque.creationBlock == _expectedCreationBlock # dev: stale cheque


@external
def payCheque(
    _agentWrapper: address,
    _userWallet: address,
    _recipient: address,
    _asset: address,
    _amount: uint256,
    _expectedCreationBlock: uint256,
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
    assert _expectedCreationBlock != 0 # dev: invalid expected block
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(6, uint8), _agentWrapper, _userWallet, _recipient, _asset, _amount, _expectedCreationBlock, _sig.nonce, _sig.expiration)), _sig)
    self._assertChequeVersionMatches(_userWallet, _recipient, _expectedCreationBlock)
    return extcall AgentWrapper(_agentWrapper).payCheque(_userWallet, _recipient, _asset, _amount, _expectedCreationBlock)


#########
# Yield #
#########


@external
def depositForYield(
    _agentWrapper: address,
    _userWallet: address,
    _legoId: uint256,
    _asset: address,
    _vaultAddr: address = empty(address),
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, address, uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(10, uint8), _agentWrapper, _userWallet, _legoId, _asset, _vaultAddr, _amount, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).depositForYield(_userWallet, _legoId, _asset, _vaultAddr, _amount, _extraData)


@external
def withdrawFromYield(
    _agentWrapper: address,
    _userWallet: address,
    _legoId: uint256,
    _vaultToken: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, address, uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(11, uint8), _agentWrapper, _userWallet, _legoId, _vaultToken, _amount, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).withdrawFromYield(_userWallet, _legoId, _vaultToken, _amount, _extraData)


@external
def rebalanceYieldPosition(
    _agentWrapper: address,
    _userWallet: address,
    _fromLegoId: uint256,
    _fromVaultToken: address,
    _toLegoId: uint256,
    _toVaultAddr: address = empty(address),
    _fromVaultAmount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, address, uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(12, uint8), _agentWrapper, _userWallet, _fromLegoId, _fromVaultToken, _toLegoId, _toVaultAddr, _fromVaultAmount, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).rebalanceYieldPosition(_userWallet, _fromLegoId, _fromVaultToken, _toLegoId, _toVaultAddr, _fromVaultAmount, _extraData)


###################
# Swap / Exchange #
###################


@external
def swapTokens(
    _agentWrapper: address,
    _userWallet: address,
    _swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS],
    _sig: Signature = empty(Signature),
) -> (address, uint256, address, uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(20, uint8), _agentWrapper, _userWallet, _swapInstructions, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).swapTokens(_userWallet, _swapInstructions)


@external
def mintOrRedeemAsset(
    _agentWrapper: address,
    _userWallet: address,
    _legoId: uint256,
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256 = max_value(uint256),
    _minAmountOut: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256, bool, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(21, uint8), _agentWrapper, _userWallet, _legoId, _tokenIn, _tokenOut, _amountIn, _minAmountOut, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).mintOrRedeemAsset(_userWallet, _legoId, _tokenIn, _tokenOut, _amountIn, _minAmountOut, _extraData)


@external
def confirmMintOrRedeemAsset(
    _agentWrapper: address,
    _userWallet: address,
    _legoId: uint256,
    _tokenIn: address,
    _tokenOut: address,
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(22, uint8), _agentWrapper, _userWallet, _legoId, _tokenIn, _tokenOut, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).confirmMintOrRedeemAsset(_userWallet, _legoId, _tokenIn, _tokenOut, _extraData)


###################
# Debt Management #
###################


@external
def addCollateral(
    _agentWrapper: address,
    _userWallet: address,
    _legoId: uint256,
    _asset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(40, uint8), _agentWrapper, _userWallet, _legoId, _asset, _amount, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).addCollateral(_userWallet, _legoId, _asset, _amount, _extraData)


@external
def removeCollateral(
    _agentWrapper: address,
    _userWallet: address,
    _legoId: uint256,
    _asset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(41, uint8), _agentWrapper, _userWallet, _legoId, _asset, _amount, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).removeCollateral(_userWallet, _legoId, _asset, _amount, _extraData)


@external
def borrow(
    _agentWrapper: address,
    _userWallet: address,
    _legoId: uint256,
    _borrowAsset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(42, uint8), _agentWrapper, _userWallet, _legoId, _borrowAsset, _amount, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).borrow(_userWallet, _legoId, _borrowAsset, _amount, _extraData)


@external
def repayDebt(
    _agentWrapper: address,
    _userWallet: address,
    _legoId: uint256,
    _paymentAsset: address,
    _paymentAmount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(43, uint8), _agentWrapper, _userWallet, _legoId, _paymentAsset, _paymentAmount, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).repayDebt(_userWallet, _legoId, _paymentAsset, _paymentAmount, _extraData)


@external
def deleverage(
    _agentWrapper: address,
    _userWallet: address,
    _legoId: uint256,
    _deleverageAssets: DynArray[ws.DeleverageAsset, MAX_DELEVERAGE_WALLET_ASSETS],
    _autoDeleverageAmount: uint256,
    _extraData: bytes32,
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
    isSpecific: bool = len(_deleverageAssets) != 0
    isAuto: bool = _autoDeleverageAmount != 0
    assert isSpecific != isAuto # dev: invalid mode

    action: uint8 = convert(44, uint8)
    if isAuto:
        action = convert(45, uint8)
    self._authenticateAccess(_userWallet, keccak256(abi_encode(action, _agentWrapper, _userWallet, _legoId, _deleverageAssets, _autoDeleverageAmount, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).deleverage(_userWallet, _legoId, _deleverageAssets, _autoDeleverageAmount, _extraData)


####################
# Claim Incentives #
####################


@external
def claimIncentives(
    _agentWrapper: address,
    _userWallet: address,
    _legoId: uint256,
    _rewardToken: address = empty(address),
    _rewardAmount: uint256 = max_value(uint256),
    _proofs: DynArray[bytes32, MAX_PROOFS] = [],
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(50, uint8), _agentWrapper, _userWallet, _legoId, _rewardToken, _rewardAmount, _proofs, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).claimIncentives(_userWallet, _legoId, _rewardToken, _rewardAmount, _proofs)


#############
# Whitelist #
#############


@external
def confirmWhitelistAddr(
    _agentWrapper: address,
    _userWallet: address,
    _whitelistAddr: address,
    _sig: Signature = empty(Signature),
) -> bool:
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(60, uint8), _agentWrapper, _userWallet, _whitelistAddr, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).confirmWhitelistAddr(_userWallet, _whitelistAddr)


@external
def cancelPendingWhitelistAddr(
    _agentWrapper: address,
    _userWallet: address,
    _whitelistAddr: address,
    _sig: Signature = empty(Signature),
) -> bool:
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(61, uint8), _agentWrapper, _userWallet, _whitelistAddr, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).cancelPendingWhitelistAddr(_userWallet, _whitelistAddr)


@external
def removeWhitelistAddr(
    _agentWrapper: address,
    _userWallet: address,
    _whitelistAddr: address,
    _sig: Signature = empty(Signature),
) -> bool:
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(62, uint8), _agentWrapper, _userWallet, _whitelistAddr, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).removeWhitelistAddr(_userWallet, _whitelistAddr)


######################
# Manager Self-Admin #
######################


@external
def removeSelfAsManager(
    _agentWrapper: address,
    _userWallet: address,
    _sig: Signature = empty(Signature),
) -> bool:
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(70, uint8), _agentWrapper, _userWallet, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).removeSelfAsManager(_userWallet)


###################
# Protocol Claims #
###################


@external
def claimAllLoot(
    _agentWrapper: address,
    _userWallet: address,
    _sig: Signature = empty(Signature),
) -> bool:
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(80, uint8), _agentWrapper, _userWallet, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).claimAllLoot(_userWallet)


@external
def claimRevShareAndBonusLoot(
    _agentWrapper: address,
    _userWallet: address,
    _sig: Signature = empty(Signature),
) -> uint256:
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(81, uint8), _agentWrapper, _userWallet, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).claimRevShareAndBonusLoot(_userWallet)


@external
def claimDepositRewards(
    _agentWrapper: address,
    _userWallet: address,
    _sig: Signature = empty(Signature),
) -> uint256:
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(82, uint8), _agentWrapper, _userWallet, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).claimDepositRewards(_userWallet)


@view
@external
def canClaimLootFor(_agentWrapper: address, _userWallet: address) -> bool:
    return staticcall AgentWrapper(_agentWrapper).canClaimLootFor(_userWallet)


###############
# Wrapped ETH #
###############


@external
def convertWethToEth(_agentWrapper: address, _userWallet: address, _amount: uint256 = max_value(uint256), _sig: Signature = empty(Signature)) -> (uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(2, uint8), _agentWrapper, _userWallet, _amount, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).convertWethToEth(_userWallet, _amount)


@external
def convertEthToWeth(_agentWrapper: address, _userWallet: address, _amount: uint256 = max_value(uint256), _sig: Signature = empty(Signature)) -> (uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(3, uint8), _agentWrapper, _userWallet, _amount, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).convertEthToWeth(_userWallet, _amount)


#############
# Liquidity #
#############


@external
def addLiquidity(
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
    _sig: Signature = empty(Signature),
) -> (uint256, uint256, uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(30, uint8), _agentWrapper, _userWallet, _legoId, _pool, _tokenA, _tokenB, _amountA, _amountB, _minAmountA, _minAmountB, _minLpAmount, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).addLiquidity(_userWallet, _legoId, _pool, _tokenA, _tokenB, _amountA, _amountB, _minAmountA, _minAmountB, _minLpAmount, _extraData)


@external
def removeLiquidity(
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
    _sig: Signature = empty(Signature),
) -> (uint256, uint256, uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(31, uint8), _agentWrapper, _userWallet, _legoId, _pool, _tokenA, _tokenB, _lpToken, _lpAmount, _minAmountA, _minAmountB, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).removeLiquidity(_userWallet, _legoId, _pool, _tokenA, _tokenB, _lpToken, _lpAmount, _minAmountA, _minAmountB, _extraData)


@external
def addLiquidityConcentrated(
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
    _sig: Signature = empty(Signature),
) -> (uint256, uint256, uint256, uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(32, uint8), _agentWrapper, _userWallet, _legoId, _nftAddr, _nftTokenId, _pool, _tokenA, _tokenB, _amountA, _amountB, _tickLower, _tickUpper, _minAmountA, _minAmountB, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).addLiquidityConcentrated(_userWallet, _legoId, _nftAddr, _nftTokenId, _pool, _tokenA, _tokenB, _amountA, _amountB, _tickLower, _tickUpper, _minAmountA, _minAmountB, _extraData)


@external
def removeLiquidityConcentrated(
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
    _sig: Signature = empty(Signature),
) -> (uint256, uint256, uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(33, uint8), _agentWrapper, _userWallet, _legoId, _nftAddr, _nftTokenId, _pool, _tokenA, _tokenB, _liqToRemove, _minAmountA, _minAmountB, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall AgentWrapper(_agentWrapper).removeLiquidityConcentrated(_userWallet, _legoId, _nftAddr, _nftTokenId, _pool, _tokenA, _tokenB, _liqToRemove, _minAmountA, _minAmountB, _extraData)


#################
# Batch Actions #
#################


@external
def performBatchActions(
    _agentWrapper: address,
    _userWallet: address,
    _instructions: DynArray[ActionInstruction, MAX_INSTRUCTIONS],
    _sig: Signature = empty(Signature),
) -> bool:
    assert len(_instructions) > 0 # dev: no instructions
    messageHash: bytes32 = keccak256(abi_encode(convert(0, uint8), _agentWrapper, _userWallet, _instructions, _sig.nonce, _sig.expiration))
    self._authenticateAccess(_userWallet, messageHash, _sig)

    prevAmountReceived: uint256 = 0
    for instruction: ActionInstruction in _instructions:
        prevAmountReceived = self._executeAction(_agentWrapper, _userWallet, instruction, prevAmountReceived)

    return True


@internal
def _executeAction(_agentWrapper: address, _userWallet: address, instruction: ActionInstruction, _prevAmount: uint256) -> uint256:
    nextAmount: uint256 = instruction.amount
    if instruction.usePrevAmountOut and _prevAmount != 0:
        nextAmount = _prevAmount

    txUsdValue: uint256 = 0

    # transfer funds
    if instruction.action == 1:
        nextAmount, txUsdValue = extcall AgentWrapper(_agentWrapper).transferFunds(_userWallet, instruction.target, instruction.asset, nextAmount)
        return nextAmount

    # convert weth to eth
    elif instruction.action == 2:
        nextAmount, txUsdValue = extcall AgentWrapper(_agentWrapper).convertWethToEth(_userWallet, nextAmount)
        return nextAmount

    # convert eth to weth
    elif instruction.action == 3:
        nextAmount, txUsdValue = extcall AgentWrapper(_agentWrapper).convertEthToWeth(_userWallet, nextAmount)
        return nextAmount

    # create and pay cheque
    elif instruction.action == 4:
        nextAmount, txUsdValue = extcall AgentWrapper(_agentWrapper).createAndPayCheque(_userWallet, instruction.target, instruction.asset, nextAmount)
        return nextAmount

    # pay cheque
    elif instruction.action == 6:
        assert not instruction.usePrevAmountOut # dev: cannot use prev amount
        # Use action 4 for atomic create-and-pay; action 5 + 6 intentionally pays an existing cheque.
        self._assertChequeVersionMatches(_userWallet, instruction.target, instruction.amount2)
        nextAmount, txUsdValue = extcall AgentWrapper(_agentWrapper).payCheque(_userWallet, instruction.target, instruction.asset, nextAmount, instruction.amount2)
        return nextAmount

    # deposit for yield
    elif instruction.action == 10:
        assetAmount: uint256 = 0
        vaultToken: address = empty(address)
        assetAmount, vaultToken, nextAmount, txUsdValue = extcall AgentWrapper(_agentWrapper).depositForYield(_userWallet, convert(instruction.legoId, uint256), instruction.asset, instruction.target, nextAmount, instruction.extraData)
        return nextAmount

    # withdraw from yield
    elif instruction.action == 11:
        underlyingAmount: uint256 = 0
        underlyingToken: address = empty(address)
        underlyingAmount, underlyingToken, nextAmount, txUsdValue = extcall AgentWrapper(_agentWrapper).withdrawFromYield(_userWallet, convert(instruction.legoId, uint256), instruction.asset, nextAmount, instruction.extraData)
        return nextAmount

    # rebalance yield position (not a UserWallet op code, but valid AgentWrapper action)
    elif instruction.action == 12:
        underlyingAmount: uint256 = 0
        underlyingToken: address = empty(address)
        # NOTE: amount2 is used as toLegoId (not an amount!)
        # Params: fromLegoId, fromVaultToken, toLegoId (amount2), toVaultAddr (target), fromVaultAmount
        underlyingAmount, underlyingToken, nextAmount, txUsdValue = extcall AgentWrapper(_agentWrapper).rebalanceYieldPosition(_userWallet, convert(instruction.legoId, uint256), instruction.asset, instruction.amount2, instruction.target, nextAmount, instruction.extraData)
        return nextAmount

    # swap tokens
    elif instruction.action == 20:
        if instruction.usePrevAmountOut and _prevAmount != 0:
            instruction.swapInstructions[0].amountIn = _prevAmount
        tokenIn: address = empty(address)
        amountIn: uint256 = 0
        tokenOut: address = empty(address)
        tokenIn, amountIn, tokenOut, nextAmount, txUsdValue = extcall AgentWrapper(_agentWrapper).swapTokens(_userWallet, instruction.swapInstructions)
        return nextAmount

    # mint or redeem asset
    elif instruction.action == 21:
        assetTokenAmount: uint256 = 0
        isPending: bool = False
        assetTokenAmount, nextAmount, isPending, txUsdValue = extcall AgentWrapper(_agentWrapper).mintOrRedeemAsset(_userWallet, convert(instruction.legoId, uint256), instruction.asset, instruction.target, nextAmount, instruction.minOut1, instruction.extraData)
        return nextAmount

    # confirm mint or redeem asset
    elif instruction.action == 22:
        nextAmount, txUsdValue = extcall AgentWrapper(_agentWrapper).confirmMintOrRedeemAsset(_userWallet, convert(instruction.legoId, uint256), instruction.asset, instruction.target, instruction.extraData)
        return nextAmount

    # add collateral
    elif instruction.action == 40:
        nextAmount, txUsdValue = extcall AgentWrapper(_agentWrapper).addCollateral(_userWallet, convert(instruction.legoId, uint256), instruction.asset, nextAmount, instruction.extraData)
        return nextAmount

    # remove collateral
    elif instruction.action == 41:
        nextAmount, txUsdValue = extcall AgentWrapper(_agentWrapper).removeCollateral(_userWallet, convert(instruction.legoId, uint256), instruction.asset, nextAmount, instruction.extraData)
        return nextAmount

    # borrow
    elif instruction.action == 42:
        nextAmount, txUsdValue = extcall AgentWrapper(_agentWrapper).borrow(_userWallet, convert(instruction.legoId, uint256), instruction.asset, nextAmount, instruction.extraData)
        return nextAmount

    # repay debt
    elif instruction.action == 43:
        nextAmount, txUsdValue = extcall AgentWrapper(_agentWrapper).repayDebt(_userWallet, convert(instruction.legoId, uint256), instruction.asset, nextAmount, instruction.extraData)
        return nextAmount

    # claim incentives
    elif instruction.action == 50:
        nextAmount, txUsdValue = extcall AgentWrapper(_agentWrapper).claimIncentives(_userWallet, convert(instruction.legoId, uint256), instruction.asset, nextAmount, instruction.proofs)
        return nextAmount

    # confirm whitelist addr
    elif instruction.action == 60:
        assert not instruction.usePrevAmountOut # dev: cannot use prev amount
        extcall AgentWrapper(_agentWrapper).confirmWhitelistAddr(_userWallet, instruction.target)
        return 0

    # cancel pending whitelist addr
    elif instruction.action == 61:
        assert not instruction.usePrevAmountOut # dev: cannot use prev amount
        extcall AgentWrapper(_agentWrapper).cancelPendingWhitelistAddr(_userWallet, instruction.target)
        return 0

    # remove whitelist addr
    elif instruction.action == 62:
        assert not instruction.usePrevAmountOut # dev: cannot use prev amount
        extcall AgentWrapper(_agentWrapper).removeWhitelistAddr(_userWallet, instruction.target)
        return 0

    # claim all loot
    elif instruction.action == 80:
        assert not instruction.usePrevAmountOut # dev: cannot use prev amount
        success: bool = extcall AgentWrapper(_agentWrapper).claimAllLoot(_userWallet)
        return convert(success, uint256)

    # claim rev-share and bonus loot
    elif instruction.action == 81:
        assert not instruction.usePrevAmountOut # dev: cannot use prev amount
        return extcall AgentWrapper(_agentWrapper).claimRevShareAndBonusLoot(_userWallet)

    # claim deposit rewards
    elif instruction.action == 82:
        assert not instruction.usePrevAmountOut # dev: cannot use prev amount
        return extcall AgentWrapper(_agentWrapper).claimDepositRewards(_userWallet)

    # add liquidity
    elif instruction.action == 30:
        amountA: uint256 = 0
        amountB: uint256 = 0
        nextAmount, amountA, amountB, txUsdValue = extcall AgentWrapper(_agentWrapper).addLiquidity(_userWallet, convert(instruction.legoId, uint256), instruction.target, instruction.asset, instruction.asset2, nextAmount, instruction.amount2, instruction.minOut1, instruction.minOut2, convert(instruction.auxData, uint256), instruction.extraData)
        return nextAmount

    # remove liquidity
    elif instruction.action == 31:
        # Extract lpToken address from auxData (lower 160 bits)
        lpToken: address = convert(convert(instruction.auxData, uint256) & convert(max_value(uint160), uint256), address)
        amountB: uint256 = 0
        lpAmountBurned: uint256 = 0
        # Params: legoId, pool (target), tokenA, tokenB, lpToken, lpAmount, minAmountA (minOut1), minAmountB (minOut2)
        # NOTE: Returns (amountA, amountB, lpBurned) - we pass forward amountA only
        nextAmount, amountB, lpAmountBurned, txUsdValue = extcall AgentWrapper(_agentWrapper).removeLiquidity(_userWallet, convert(instruction.legoId, uint256), instruction.target, instruction.asset, instruction.asset2, lpToken, nextAmount, instruction.minOut1, instruction.minOut2, instruction.extraData)
        return nextAmount

    # add liquidity concentrated
    elif instruction.action == 32:
        # Extract pool address (upper 160 bits) and nftId (lower 96 bits) from auxData
        pool: address = convert(convert(instruction.auxData, uint256) >> 96, address)
        nftId: uint256 = convert(instruction.auxData, uint256) & convert(max_value(uint96), uint256)
        # Params: legoId, nftAddr (target), nftId, pool, tokenA, tokenB, amountA, amountB (amount2)
        extcall AgentWrapper(_agentWrapper).addLiquidityConcentrated(_userWallet, convert(instruction.legoId, uint256), instruction.target, nftId, pool, instruction.asset, instruction.asset2, nextAmount, instruction.amount2, instruction.tickLower, instruction.tickUpper, instruction.minOut1, instruction.minOut2, instruction.extraData)
        return 0

    # remove liquidity concentrated
    elif instruction.action == 33:
        # Extract pool address (upper 160 bits) and nftId (lower 96 bits) from auxData
        pool: address = convert(convert(instruction.auxData, uint256) >> 96, address)
        nftId: uint256 = convert(instruction.auxData, uint256) & convert(max_value(uint96), uint256)
        amountA: uint256 = 0
        amountB: uint256 = 0
        # Params: legoId, nftAddr (target), nftId, pool, tokenA, tokenB, liqToRemove, minAmountA (minOut1), minAmountB (minOut2)
        # NOTE: Returns (amountA, amountB, liquidity) - we pass forward amountA only
        nextAmount, amountA, amountB, txUsdValue = extcall AgentWrapper(_agentWrapper).removeLiquidityConcentrated(_userWallet, convert(instruction.legoId, uint256), instruction.target, nftId, pool, instruction.asset, instruction.asset2, nextAmount, instruction.minOut1, instruction.minOut2, instruction.extraData)
        return nextAmount

    else:
        raise "Invalid action"


##################
# Authentication #
##################


@internal
def _authenticateAccess(_userWallet: address, _messageHash: bytes32, _sig: Signature):
    owner: address = ownership.owner
    if msg.sender != owner:
        # check expiration first to prevent DoS
        assert _sig.expiration >= block.timestamp # dev: signature expired

        # check nonce is valid
        assert _sig.nonce == self.currentNonce[_userWallet] # dev: invalid nonce

        # verify signature and check it's from owner
        signer: address = self._verify(_messageHash, _sig)
        assert signer == owner # dev: invalid signer

        # increment nonce for next use
        self._incrementNonce(_userWallet)
    else:
        assert _sig.signature == empty(Bytes[65]) # dev: must be empty
        assert _sig.nonce == 0 # dev: must be 0
        assert _sig.expiration == 0 # dev: must be 0


@view
@internal
def _verify(_messageHash: bytes32, _sig: Signature) -> address:
    # extract signature components
    r: bytes32 = convert(slice(_sig.signature, 0, 32), bytes32)
    s: bytes32 = convert(slice(_sig.signature, 32, 32), bytes32)
    v: uint8 = convert(slice(_sig.signature, 64, 1), uint8)

    # validate v parameter (27 or 28)
    if v < 27:
        v = v + 27
    assert v == 27 or v == 28 # dev: invalid v parameter

    # prevent signature malleability by ensuring s is in lower half of curve order
    s_uint: uint256 = convert(s, uint256)
    assert s_uint != 0 # dev: invalid s value (zero)
    assert s_uint <= convert(0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0, uint256) # dev: invalid s value

    # create digest with EIP-712
    digest: bytes32 = keccak256(concat(SIG_PREFIX, self._domainSeparator(), _messageHash))

    # call ecrecover precompile
    result: Bytes[32] = raw_call(
        ECRECOVER_PRECOMPILE,
        abi_encode(digest, v, r, s),
        max_outsize=32,
        is_static_call=True
    )

    # return recovered address or empty if failed
    if len(result) != 32:
        return empty(address)

    recovered: address = abi_decode(result, address)
    assert recovered != empty(address) # dev: signature recovery failed
    return recovered


@view
@internal
def _domainSeparator() -> bytes32:
    return keccak256(abi_encode(
        keccak256('EIP712Domain(string name,uint256 chainId,address verifyingContract)'),
        keccak256('UnderscoreAgent'),
        chain.id,
        self
    ))


@external
def incrementNonce(_userWallet: address):
    assert msg.sender == ownership.owner # dev: no perms
    self._incrementNonce(_userWallet)


@internal
def _incrementNonce(_userWallet: address):
    oldNonce: uint256 = self.currentNonce[_userWallet]
    self.currentNonce[_userWallet] = oldNonce + 1
    log NonceIncremented(userWallet=_userWallet, oldNonce=oldNonce, newNonce=oldNonce + 1)


@view
@external
def getNonce(_userWallet: address) -> uint256:
    return self.currentNonce[_userWallet]
