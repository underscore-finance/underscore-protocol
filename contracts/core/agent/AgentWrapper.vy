#             _                   _                 _               _                 _       
#            / /\                /\ \              /\ \            /\ \     _        /\ \     
#           / /  \              /  \ \            /  \ \          /  \ \   /\_\      \_\ \    
#          / / /\ \            / /\ \_\          / /\ \ \        / /\ \ \_/ / /      /\__ \   
#         / / /\ \ \          / / /\/_/         / / /\ \_\      / / /\ \___/ /      / /_ \ \  
#        / / /  \ \ \        / / / ______      / /_/_ \/_/     / / /  \/____/      / / /\ \ \ 
#       / / /___/ /\ \      / / / /\_____\    / /____/\       / / /    / / /      / / /  \/_/ 
#      / / /_____/ /\ \    / / /  \/____ /   / /\____\/      / / /    / / /      / / /        
#     / /_________/\ \ \  / / /_____/ / /   / / /______     / / /    / / /      / / /         
#    / / /_       __\ \_\/ / /______\/ /   / / /_______\   / / /    / / /      /_/ /          
#    \_\___\     /____/_/\/___________/    \/__________/   \/_/     \/_/       \_\/           
#                                                                                         
#     ╔════════════════════════════════════════════════════════════════════════════════╗
#     ║  ** Agent Wrapper **                                                           ║
#     ║  Handles all agent wrapper functionality                                       ║
#     ╚════════════════════════════════════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3
# pragma optimize codesize

initializes: ownership
exports: ownership.__interface__
import contracts.modules.Ownership as ownership

from interfaces import Wallet

struct Signature:
    signature: Bytes[65]
    nonce: uint256
    expiration: uint256

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
    proofs: DynArray[bytes32, MAX_PROOFS]  # Merkle proofs for claimIncentives (action 50)

event NonceIncremented:
    userWallet: address
    oldNonce: uint256
    newNonce: uint256

groupId: public(uint256)
currentNonce: public(HashMap[address, uint256])

MAX_INSTRUCTIONS: constant(uint256) = 15
MAX_SWAP_INSTRUCTIONS: constant(uint256) = 5
MAX_TOKEN_PATH: constant(uint256) = 5
MAX_PROOFS: constant(uint256) = 25

# unified signature validation
ECRECOVER_PRECOMPILE: constant(address) = 0x0000000000000000000000000000000000000001
SIG_PREFIX: constant(bytes32) = 0x1901000000000000000000000000000000000000000000000000000000000000


@deploy
def __init__(
    _undyHq: address,
    _owner: address,
    _groupId: uint256,
    _minTimeLock: uint256,
    _maxTimeLock: uint256,
):
    ownership.__init__(_undyHq, _owner, _minTimeLock, _maxTimeLock)
    self.groupId = _groupId


##################
# Transfer Funds #
##################


@external
def transferFunds(
    _userWallet: address,
    _recipient: address,
    _asset: address = empty(address),
    _amount: uint256 = max_value(uint256),
    _isCheque: bool = False,
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(1, uint8), _userWallet, _recipient, _asset, _amount, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).transferFunds(_recipient, _asset, _amount, _isCheque, False)


#########
# Yield #
#########


@external
def depositForYield(
    _userWallet: address,
    _legoId: uint256,
    _asset: address,
    _vaultAddr: address = empty(address),
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, address, uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(10, uint8), _userWallet, _legoId, _asset, _vaultAddr, _amount, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).depositForYield(_legoId, _asset, _vaultAddr, _amount, _extraData)


@external
def withdrawFromYield(
    _userWallet: address,
    _legoId: uint256,
    _vaultToken: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, address, uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(11, uint8), _userWallet, _legoId, _vaultToken, _amount, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).withdrawFromYield(_legoId, _vaultToken, _amount, _extraData, False)


@external
def rebalanceYieldPosition(
    _userWallet: address,
    _fromLegoId: uint256,
    _fromVaultToken: address,
    _toLegoId: uint256,
    _toVaultAddr: address = empty(address),
    _fromVaultAmount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, address, uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(12, uint8), _userWallet, _fromLegoId, _fromVaultToken, _toLegoId, _toVaultAddr, _fromVaultAmount, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).rebalanceYieldPosition(_fromLegoId, _fromVaultToken, _toLegoId, _toVaultAddr, _fromVaultAmount, _extraData)


###################
# Swap / Exchange #
###################


@external
def swapTokens(
    _userWallet: address,
    _swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS],
    _sig: Signature = empty(Signature),
) -> (address, uint256, address, uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(20, uint8), _userWallet, _swapInstructions, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).swapTokens(_swapInstructions)


@external
def mintOrRedeemAsset(
    _userWallet: address,
    _legoId: uint256,
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256 = max_value(uint256),
    _minAmountOut: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256, bool, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(21, uint8), _userWallet, _legoId, _tokenIn, _tokenOut, _amountIn, _minAmountOut, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).mintOrRedeemAsset(_legoId, _tokenIn, _tokenOut, _amountIn, _minAmountOut, _extraData)


@external
def confirmMintOrRedeemAsset(
    _userWallet: address,
    _legoId: uint256,
    _tokenIn: address,
    _tokenOut: address,
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(22, uint8), _userWallet, _legoId, _tokenIn, _tokenOut, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).confirmMintOrRedeemAsset(_legoId, _tokenIn, _tokenOut, _extraData)


###################
# Debt Management #
###################


@external
def addCollateral(
    _userWallet: address,
    _legoId: uint256,
    _asset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(40, uint8), _userWallet, _legoId, _asset, _amount, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).addCollateral(_legoId, _asset, _amount, _extraData)


@external
def removeCollateral(
    _userWallet: address,
    _legoId: uint256,
    _asset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(41, uint8), _userWallet, _legoId, _asset, _amount, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).removeCollateral(_legoId, _asset, _amount, _extraData)


@external
def borrow(
    _userWallet: address,
    _legoId: uint256,
    _borrowAsset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(42, uint8), _userWallet, _legoId, _borrowAsset, _amount, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).borrow(_legoId, _borrowAsset, _amount, _extraData)


@external
def repayDebt(
    _userWallet: address,
    _legoId: uint256,
    _paymentAsset: address,
    _paymentAmount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(43, uint8), _userWallet, _legoId, _paymentAsset, _paymentAmount, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).repayDebt(_legoId, _paymentAsset, _paymentAmount, _extraData)


#################
# Claim Rewards #
#################


@external
def claimIncentives(
    _userWallet: address,
    _legoId: uint256,
    _rewardToken: address = empty(address),
    _rewardAmount: uint256 = max_value(uint256),
    _proofs: DynArray[bytes32, MAX_PROOFS] = [],
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(50, uint8), _userWallet, _legoId, _rewardToken, _rewardAmount, _proofs, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).claimIncentives(_legoId, _rewardToken, _rewardAmount, _proofs)


###############
# Wrapped ETH #
###############


@external
def convertWethToEth(_userWallet: address, _amount: uint256 = max_value(uint256), _sig: Signature = empty(Signature)) -> (uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(2, uint8), _userWallet, _amount, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).convertWethToEth(_amount)


@external
def convertEthToWeth(_userWallet: address, _amount: uint256 = max_value(uint256), _sig: Signature = empty(Signature)) -> (uint256, uint256):
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(3, uint8), _userWallet, _amount, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).convertEthToWeth(_amount)


#############
# Liquidity #
#############


@external
def addLiquidity(
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
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(30, uint8), _userWallet, _legoId, _pool, _tokenA, _tokenB, _amountA, _amountB, _minAmountA, _minAmountB, _minLpAmount, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).addLiquidity(_legoId, _pool, _tokenA, _tokenB, _amountA, _amountB, _minAmountA, _minAmountB, _minLpAmount, _extraData)


@external
def removeLiquidity(
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
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(31, uint8), _userWallet, _legoId, _pool, _tokenA, _tokenB, _lpToken, _lpAmount, _minAmountA, _minAmountB, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).removeLiquidity(_legoId, _pool, _tokenA, _tokenB, _lpToken, _lpAmount, _minAmountA, _minAmountB, _extraData)


@external
def addLiquidityConcentrated(
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
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(32, uint8), _userWallet, _legoId, _nftAddr, _nftTokenId, _pool, _tokenA, _tokenB, _amountA, _amountB, _tickLower, _tickUpper, _minAmountA, _minAmountB, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).addLiquidityConcentrated(_legoId, _nftAddr, _nftTokenId, _pool, _tokenA, _tokenB, _amountA, _amountB, _tickLower, _tickUpper, _minAmountA, _minAmountB, _extraData)


@external
def removeLiquidityConcentrated(
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
    self._authenticateAccess(_userWallet, keccak256(abi_encode(convert(33, uint8), _userWallet, _legoId, _nftAddr, _nftTokenId, _pool, _tokenA, _tokenB, _liqToRemove, _minAmountA, _minAmountB, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).removeLiquidityConcentrated(_legoId, _nftAddr, _nftTokenId, _pool, _tokenA, _tokenB, _liqToRemove, _minAmountA, _minAmountB, _extraData)


#################
# Batch Actions #
#################


@external
def performBatchActions(
    _userWallet: address,
    _instructions: DynArray[ActionInstruction, MAX_INSTRUCTIONS],
    _sig: Signature = empty(Signature),
) -> bool:
    assert len(_instructions) > 0 # dev: no instructions
    messageHash: bytes32 = keccak256(abi_encode(_userWallet, _instructions, _sig.nonce, _sig.expiration))
    self._authenticateAccess(_userWallet, messageHash, _sig)   

    prevAmountReceived: uint256 = 0
    for instruction: ActionInstruction in _instructions:
        prevAmountReceived = self._executeAction(_userWallet, instruction, prevAmountReceived)

    return True


@internal
def _executeAction(_userWallet: address, instruction: ActionInstruction, _prevAmount: uint256) -> uint256:
    nextAmount: uint256 = instruction.amount
    if instruction.usePrevAmountOut and _prevAmount != 0:
        nextAmount = _prevAmount

    txUsdValue: uint256 = 0

    # transfer funds
    if instruction.action == 1:
        # Extract isCheque from the least significant bit of extraData
        isCheque: bool = convert(convert(instruction.extraData, uint256) & 1, bool)
        nextAmount, txUsdValue = extcall Wallet(_userWallet).transferFunds(instruction.target, instruction.asset, nextAmount, isCheque, False)
        return nextAmount

    # convert weth to eth
    elif instruction.action == 2:
        nextAmount, txUsdValue = extcall Wallet(_userWallet).convertWethToEth(nextAmount)
        return nextAmount

    # convert eth to weth
    elif instruction.action == 3:
        nextAmount, txUsdValue = extcall Wallet(_userWallet).convertEthToWeth(nextAmount)
        return nextAmount

    # deposit for yield
    elif instruction.action == 10:
        assetAmount: uint256 = 0
        vaultToken: address = empty(address)
        assetAmount, vaultToken, nextAmount, txUsdValue = extcall Wallet(_userWallet).depositForYield(convert(instruction.legoId, uint256), instruction.asset, instruction.target, nextAmount, instruction.extraData)
        return nextAmount

    # withdraw from yield
    elif instruction.action == 11:
        underlyingAmount: uint256 = 0
        underlyingToken: address = empty(address)
        underlyingAmount, underlyingToken, nextAmount, txUsdValue = extcall Wallet(_userWallet).withdrawFromYield(convert(instruction.legoId, uint256), instruction.asset, nextAmount, instruction.extraData)
        return nextAmount

    # rebalance yield position (not a UserWallet op code, but valid AgentWrapper action)
    elif instruction.action == 12:
        underlyingAmount: uint256 = 0
        underlyingToken: address = empty(address)
        # NOTE: amount2 is used as toLegoId (not an amount!)
        # Params: fromLegoId, fromVaultToken, toLegoId (amount2), toVaultAddr (target), fromVaultAmount
        underlyingAmount, underlyingToken, nextAmount, txUsdValue = extcall Wallet(_userWallet).rebalanceYieldPosition(convert(instruction.legoId, uint256), instruction.asset, instruction.amount2, instruction.target, nextAmount, instruction.extraData)
        return nextAmount

    # swap tokens
    elif instruction.action == 20:
        if instruction.usePrevAmountOut and _prevAmount != 0:
            instruction.swapInstructions[0].amountIn = _prevAmount
        tokenIn: address = empty(address)
        amountIn: uint256 = 0
        tokenOut: address = empty(address)
        tokenIn, amountIn, tokenOut, nextAmount, txUsdValue = extcall Wallet(_userWallet).swapTokens(instruction.swapInstructions)
        return nextAmount

    # mint or redeem asset
    elif instruction.action == 21:
        assetTokenAmount: uint256 = 0
        isPending: bool = False
        assetTokenAmount, nextAmount, isPending, txUsdValue = extcall Wallet(_userWallet).mintOrRedeemAsset(convert(instruction.legoId, uint256), instruction.asset, instruction.target, nextAmount, instruction.minOut1, instruction.extraData)
        return nextAmount

    # confirm mint or redeem asset
    elif instruction.action == 22:
        nextAmount, txUsdValue = extcall Wallet(_userWallet).confirmMintOrRedeemAsset(convert(instruction.legoId, uint256), instruction.asset, instruction.target, instruction.extraData)
        return nextAmount

    # add collateral
    elif instruction.action == 40:
        nextAmount, txUsdValue = extcall Wallet(_userWallet).addCollateral(convert(instruction.legoId, uint256), instruction.asset, nextAmount, instruction.extraData)
        return nextAmount

    # remove collateral
    elif instruction.action == 41:
        nextAmount, txUsdValue = extcall Wallet(_userWallet).removeCollateral(convert(instruction.legoId, uint256), instruction.asset, nextAmount, instruction.extraData)
        return nextAmount

    # borrow
    elif instruction.action == 42:
        nextAmount, txUsdValue = extcall Wallet(_userWallet).borrow(convert(instruction.legoId, uint256), instruction.asset, nextAmount, instruction.extraData)
        return nextAmount

    # repay debt
    elif instruction.action == 43:
        nextAmount, txUsdValue = extcall Wallet(_userWallet).repayDebt(convert(instruction.legoId, uint256), instruction.asset, nextAmount, instruction.extraData)
        return nextAmount

    # claim incentives
    elif instruction.action == 50:
        nextAmount, txUsdValue = extcall Wallet(_userWallet).claimIncentives(convert(instruction.legoId, uint256), instruction.asset, nextAmount, instruction.proofs)
        return nextAmount

    # add liquidity
    elif instruction.action == 30:
        amountA: uint256 = 0
        amountB: uint256 = 0
        nextAmount, amountA, amountB, txUsdValue = extcall Wallet(_userWallet).addLiquidity(convert(instruction.legoId, uint256), instruction.target, instruction.asset, instruction.asset2, nextAmount, instruction.amount2, instruction.minOut1, instruction.minOut2, convert(instruction.auxData, uint256), instruction.extraData)
        return nextAmount

    # remove liquidity
    elif instruction.action == 31:
        # Extract lpToken address from auxData (lower 160 bits)
        lpToken: address = convert(convert(instruction.auxData, uint256) & convert(max_value(uint160), uint256), address)
        amountB: uint256 = 0
        lpAmountBurned: uint256 = 0
        # Params: legoId, pool (target), tokenA, tokenB, lpToken, lpAmount, minAmountA (minOut1), minAmountB (minOut2)
        # NOTE: Returns (amountA, amountB, lpBurned) - we pass forward amountA only
        nextAmount, amountB, lpAmountBurned, txUsdValue = extcall Wallet(_userWallet).removeLiquidity(convert(instruction.legoId, uint256), instruction.target, instruction.asset, instruction.asset2, lpToken, nextAmount, instruction.minOut1, instruction.minOut2, instruction.extraData)
        return nextAmount

    # add liquidity concentrated
    elif instruction.action == 32:
        # Extract pool address (upper 160 bits) and nftId (lower 96 bits) from auxData
        pool: address = convert(convert(instruction.auxData, uint256) >> 96, address)
        nftId: uint256 = convert(instruction.auxData, uint256) & convert(max_value(uint96), uint256)
        # Params: legoId, nftAddr (target), nftId, pool, tokenA, tokenB, amountA, amountB (amount2)
        extcall Wallet(_userWallet).addLiquidityConcentrated(convert(instruction.legoId, uint256), instruction.target, nftId, pool, instruction.asset, instruction.asset2, nextAmount, instruction.amount2, instruction.tickLower, instruction.tickUpper, instruction.minOut1, instruction.minOut2, instruction.extraData)
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
        nextAmount, amountA, amountB, txUsdValue = extcall Wallet(_userWallet).removeLiquidityConcentrated(convert(instruction.legoId, uint256), instruction.target, nftId, pool, instruction.asset, instruction.asset2, nextAmount, instruction.minOut1, instruction.minOut2, instruction.extraData)
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
        self.currentNonce[_userWallet] += 1


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
    oldNonce: uint256 = self.currentNonce[_userWallet]
    self.currentNonce[_userWallet] += 1
    log NonceIncremented(userWallet=_userWallet, oldNonce=oldNonce, newNonce=self.currentNonce[_userWallet])


@view
@external
def getNonce(_userWallet: address) -> uint256:
    return self.currentNonce[_userWallet]
