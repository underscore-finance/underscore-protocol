# @version 0.4.3
# pragma optimize codesize

from interfaces import Wallet
from interfaces import LegoPartner as Lego

interface MissionControl:
    def canPerformSecurityAction(_addr: address) -> bool: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

struct PendingOwnerChange:
    newOwner: address
    initiatedBlock: uint256
    confirmBlock: uint256

struct Signature:
    signature: Bytes[65]
    nonce: uint256
    expiration: uint256

struct ActionInstruction:
    usePrevAmountOut: bool      # Use output from previous instruction as amount
    action: uint8               # Action type (0-17, see ActionType enum)
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
    extraAddr: address         # Protocol-specific extra parameter
    extraVal: uint256          # Protocol-specific extra value
    extraData: bytes32         # Protocol-specific extra data
    auxData: bytes32           # Packed data: lpToken addr (action 15) or pool+nftId (16-17)
    swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS]

event OwnershipChangeInitiated:
    prevOwner: indexed(address)
    newOwner: indexed(address)
    confirmBlock: uint256

event OwnershipChangeConfirmed:
    prevOwner: indexed(address)
    newOwner: indexed(address)
    initiatedBlock: uint256
    confirmBlock: uint256

event OwnershipChangeCancelled:
    cancelledOwner: indexed(address)
    cancelledBy: indexed(address)
    initiatedBlock: uint256
    confirmBlock: uint256

event TimeLockSet:
    numBlocks: uint256

event NonceIncremented:
    oldNonce: uint256
    newNonce: uint256

# core
owner: public(address)
timeLock: public(uint256)
pendingOwner: public(PendingOwnerChange)
currentNonce: public(uint256)

MAX_INSTRUCTIONS: constant(uint256) = 15
MAX_SWAP_INSTRUCTIONS: constant(uint256) = 5
MAX_TOKEN_PATH: constant(uint256) = 5
MISSION_CONTROL_ID: constant(uint256) = 3

# unified signature validation
ECRECOVER_PRECOMPILE: constant(address) = 0x0000000000000000000000000000000000000001
SIG_PREFIX: constant(bytes32) = 0x1901000000000000000000000000000000000000000000000000000000000000

UNDY_HQ: public(immutable(address))
MIN_TIMELOCK: public(immutable(uint256))
MAX_TIMELOCK: public(immutable(uint256))


@deploy
def __init__(_undyHq: address, _owner: address, _minTimeLock: uint256, _maxTimeLock: uint256):
    assert empty(address) not in [_undyHq, _owner] # dev: invalid addrs
    UNDY_HQ = _undyHq
    self.owner = _owner

    # time lock
    assert _minTimeLock < _maxTimeLock # dev: invalid delay
    MIN_TIMELOCK = _minTimeLock
    MAX_TIMELOCK = _maxTimeLock
    self.timeLock = _minTimeLock


###########
# Actions #
###########


@nonreentrant
@external
def depositForYield(
    _userWallet: address,
    _legoId: uint256,
    _asset: address,
    _vaultAddr: address = empty(address),
    _amount: uint256 = max_value(uint256),
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, address, uint256):
    self._authenticateAccess(keccak256(abi_encode(convert(0, uint8), _userWallet, _legoId, _asset, _vaultAddr, _amount, _extraAddr, _extraVal, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).depositForYield(_legoId, _asset, _vaultAddr, _amount, _extraAddr, _extraVal, _extraData)


@nonreentrant
@external
def withdrawFromYield(
    _userWallet: address,
    _legoId: uint256,
    _vaultToken: address,
    _amount: uint256 = max_value(uint256),
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, address, uint256):
    self._authenticateAccess(keccak256(abi_encode(convert(1, uint8), _userWallet, _legoId, _vaultToken, _amount, _extraAddr, _extraVal, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).withdrawFromYield(_legoId, _vaultToken, _amount, _extraAddr, _extraVal, _extraData)


@nonreentrant
@external
def rebalanceYieldPosition(
    _userWallet: address,
    _fromLegoId: uint256,
    _fromVaultToken: address,
    _toLegoId: uint256,
    _toVaultAddr: address = empty(address),
    _fromVaultAmount: uint256 = max_value(uint256),
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, address, uint256):
    self._authenticateAccess(keccak256(abi_encode(convert(2, uint8), _userWallet, _fromLegoId, _fromVaultToken, _toLegoId, _toVaultAddr, _fromVaultAmount, _extraAddr, _extraVal, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).rebalanceYieldPosition(_fromLegoId, _fromVaultToken, _toLegoId, _toVaultAddr, _fromVaultAmount, _extraAddr, _extraVal, _extraData)


@nonreentrant
@external
def swapTokens(
    _userWallet: address,
    _swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS],
    _sig: Signature = empty(Signature),
) -> (address, uint256, address, uint256):
    self._authenticateAccess(keccak256(abi_encode(convert(3, uint8), _userWallet, _swapInstructions, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).swapTokens(_swapInstructions)


@nonreentrant
@external
def mintOrRedeemAsset(
    _userWallet: address,
    _legoId: uint256,
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256 = max_value(uint256),
    _minAmountOut: uint256 = 0,
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256, bool):
    self._authenticateAccess(keccak256(abi_encode(convert(4, uint8), _userWallet, _legoId, _tokenIn, _tokenOut, _amountIn, _minAmountOut, _extraAddr, _extraVal, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).mintOrRedeemAsset(_legoId, _tokenIn, _tokenOut, _amountIn, _minAmountOut, _extraAddr, _extraVal, _extraData)


@nonreentrant
@external
def confirmMintOrRedeemAsset(
    _userWallet: address,
    _legoId: uint256,
    _tokenIn: address,
    _tokenOut: address,
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> uint256:
    self._authenticateAccess(keccak256(abi_encode(convert(5, uint8), _userWallet, _legoId, _tokenIn, _tokenOut, _extraAddr, _extraVal, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).confirmMintOrRedeemAsset(_legoId, _tokenIn, _tokenOut, _extraAddr, _extraVal, _extraData)


@nonreentrant
@external
def addCollateral(
    _userWallet: address,
    _legoId: uint256,
    _asset: address,
    _amount: uint256 = max_value(uint256),
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> uint256:
    self._authenticateAccess(keccak256(abi_encode(convert(6, uint8), _userWallet, _legoId, _asset, _amount, _extraAddr, _extraVal, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).addCollateral(_legoId, _asset, _amount, _extraAddr, _extraVal, _extraData)


@nonreentrant
@external
def removeCollateral(
    _userWallet: address,
    _legoId: uint256,
    _asset: address,
    _amount: uint256 = max_value(uint256),
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> uint256:
    self._authenticateAccess(keccak256(abi_encode(convert(7, uint8), _userWallet, _legoId, _asset, _amount, _extraAddr, _extraVal, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).removeCollateral(_legoId, _asset, _amount, _extraAddr, _extraVal, _extraData)


@nonreentrant
@external
def borrow(
    _userWallet: address,
    _legoId: uint256,
    _borrowAsset: address,
    _amount: uint256 = max_value(uint256),
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> uint256:
    self._authenticateAccess(keccak256(abi_encode(convert(8, uint8), _userWallet, _legoId, _borrowAsset, _amount, _extraAddr, _extraVal, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).borrow(_legoId, _borrowAsset, _amount, _extraAddr, _extraVal, _extraData)


@nonreentrant
@external
def repayDebt(
    _userWallet: address,
    _legoId: uint256,
    _paymentAsset: address,
    _paymentAmount: uint256 = max_value(uint256),
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> uint256:
    self._authenticateAccess(keccak256(abi_encode(convert(9, uint8), _userWallet, _legoId, _paymentAsset, _paymentAmount, _extraAddr, _extraVal, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).repayDebt(_legoId, _paymentAsset, _paymentAmount, _extraAddr, _extraVal, _extraData)


@nonreentrant
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
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256, uint256):
    self._authenticateAccess(keccak256(abi_encode(convert(10, uint8), _userWallet, _legoId, _pool, _tokenA, _tokenB, _amountA, _amountB, _minAmountA, _minAmountB, _minLpAmount, _extraAddr, _extraVal, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).addLiquidity(_legoId, _pool, _tokenA, _tokenB, _amountA, _amountB, _minAmountA, _minAmountB, _minLpAmount, _extraAddr, _extraVal, _extraData)


@nonreentrant
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
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256, uint256, uint256):
    self._authenticateAccess(keccak256(abi_encode(convert(11, uint8), _userWallet, _legoId, _nftAddr, _nftTokenId, _pool, _tokenA, _tokenB, _amountA, _amountB, _tickLower, _tickUpper, _minAmountA, _minAmountB, _extraAddr, _extraVal, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).addLiquidityConcentrated(_legoId, _nftAddr, _nftTokenId, _pool, _tokenA, _tokenB, _amountA, _amountB, _tickLower, _tickUpper, _minAmountA, _minAmountB, _extraAddr, _extraVal, _extraData)


@nonreentrant
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
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256, uint256):
    self._authenticateAccess(keccak256(abi_encode(convert(12, uint8), _userWallet, _legoId, _pool, _tokenA, _tokenB, _lpToken, _lpAmount, _minAmountA, _minAmountB, _extraAddr, _extraVal, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).removeLiquidity(_legoId, _pool, _tokenA, _tokenB, _lpToken, _lpAmount, _minAmountA, _minAmountB, _extraAddr, _extraVal, _extraData)


@nonreentrant
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
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256, uint256):
    self._authenticateAccess(keccak256(abi_encode(convert(13, uint8), _userWallet, _legoId, _nftAddr, _nftTokenId, _pool, _tokenA, _tokenB, _liqToRemove, _minAmountA, _minAmountB, _extraAddr, _extraVal, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).removeLiquidityConcentrated(_legoId, _nftAddr, _nftTokenId, _pool, _tokenA, _tokenB, _liqToRemove, _minAmountA, _minAmountB, _extraAddr, _extraVal, _extraData)


@nonreentrant
@external
def transferFunds(
    _userWallet: address,
    _recipient: address,
    _asset: address = empty(address),
    _amount: uint256 = max_value(uint256),
    _sig: Signature = empty(Signature),
) -> uint256:
    self._authenticateAccess(keccak256(abi_encode(convert(14, uint8), _userWallet, _recipient, _asset, _amount, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).transferFunds(_recipient, _asset, _amount)


@nonreentrant
@external
def claimRewards(
    _userWallet: address,
    _legoId: uint256,
    _rewardToken: address = empty(address),
    _rewardAmount: uint256 = max_value(uint256),
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> uint256:
    self._authenticateAccess(keccak256(abi_encode(convert(15, uint8), _userWallet, _legoId, _rewardToken, _rewardAmount, _extraAddr, _extraVal, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).claimRewards(_legoId, _rewardToken, _rewardAmount, _extraAddr, _extraVal, _extraData)


@nonreentrant
@external
def convertEthToWeth(_userWallet: address, _amount: uint256 = max_value(uint256), _sig: Signature = empty(Signature)) -> uint256:
    self._authenticateAccess(keccak256(abi_encode(convert(16, uint8), _userWallet, _amount, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).convertEthToWeth(_amount)


@nonreentrant
@external
def convertWethToEth(_userWallet: address, _amount: uint256 = max_value(uint256), _sig: Signature = empty(Signature)) -> uint256:
    self._authenticateAccess(keccak256(abi_encode(convert(17, uint8), _userWallet, _amount, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_userWallet).convertWethToEth(_amount)


#################
# Batch Actions #
#################


@nonreentrant
@external
def performBatchActions(
    _userWallet: address,
    _instructions: DynArray[ActionInstruction, MAX_INSTRUCTIONS],
    _sig: Signature = empty(Signature),
) -> bool:
    if msg.sender != self.owner:
        messageHash: bytes32 = keccak256(abi_encode(_userWallet, _instructions, _sig.nonce, _sig.expiration))
        self._authenticateAccess(messageHash, _sig)
    
    assert len(_instructions) > 0 # dev: no instructions

    prevAmountReceived: uint256 = 0
    for instruction: ActionInstruction in _instructions:
        prevAmountReceived = self._executeAction(_userWallet, instruction, prevAmountReceived)

    return True


@internal
def _executeAction(_userWallet: address, instruction: ActionInstruction, prevAmountReceived: uint256) -> uint256:
    amount: uint256 = instruction.amount
    if instruction.usePrevAmountOut and prevAmountReceived != 0:
        amount = prevAmountReceived
    
    # transfer funds
    if instruction.action == 0:
        return extcall Wallet(_userWallet).transferFunds(instruction.target, instruction.asset, amount)

    # deposit for yield
    elif instruction.action == 1:
        assetAmount: uint256 = 0
        vaultToken: address = empty(address)
        assetAmount, vaultToken, prevAmountReceived = extcall Wallet(_userWallet).depositForYield(convert(instruction.legoId, uint256), instruction.asset, instruction.target, amount, instruction.extraAddr, instruction.extraVal, instruction.extraData)
        return prevAmountReceived

    # withdraw from yield
    elif instruction.action == 2:
        underlyingAmount: uint256 = 0
        underlyingToken: address = empty(address)
        underlyingAmount, underlyingToken, prevAmountReceived = extcall Wallet(_userWallet).withdrawFromYield(convert(instruction.legoId, uint256), instruction.asset, amount, instruction.extraAddr, instruction.extraVal, instruction.extraData)
        return prevAmountReceived

    # rebalance yield position
    elif instruction.action == 3:
        underlyingAmount: uint256 = 0
        underlyingToken: address = empty(address)
        # NOTE: amount2 is used as toLegoId (not an amount!)
        # Params: fromLegoId, fromVaultToken, toLegoId (amount2), toVaultAddr (target), fromVaultAmount
        underlyingAmount, underlyingToken, prevAmountReceived = extcall Wallet(_userWallet).rebalanceYieldPosition(convert(instruction.legoId, uint256), instruction.asset, instruction.amount2, instruction.target, amount, instruction.extraAddr, instruction.extraVal, instruction.extraData)
        return prevAmountReceived

    # swap tokens
    elif instruction.action == 4:
        if instruction.usePrevAmountOut and prevAmountReceived != 0:
            instruction.swapInstructions[0].amountIn = prevAmountReceived
        tokenIn: address = empty(address)
        amountIn: uint256 = 0
        tokenOut: address = empty(address)
        tokenIn, amountIn, tokenOut, prevAmountReceived = extcall Wallet(_userWallet).swapTokens(instruction.swapInstructions)
        return prevAmountReceived

    # mint or redeem asset
    elif instruction.action == 5:
        assetTokenAmount: uint256 = 0
        isPending: bool = False
        assetTokenAmount, prevAmountReceived, isPending = extcall Wallet(_userWallet).mintOrRedeemAsset(convert(instruction.legoId, uint256), instruction.asset, instruction.target, amount, instruction.minOut1, instruction.extraAddr, instruction.extraVal, instruction.extraData)
        return prevAmountReceived

    # confirm mint or redeem asset
    elif instruction.action == 6:
        return extcall Wallet(_userWallet).confirmMintOrRedeemAsset(convert(instruction.legoId, uint256), instruction.asset, instruction.target, instruction.extraAddr, instruction.extraVal, instruction.extraData)

    # add collateral
    elif instruction.action == 7:
        extcall Wallet(_userWallet).addCollateral(convert(instruction.legoId, uint256), instruction.asset, amount, instruction.extraAddr, instruction.extraVal, instruction.extraData)
        return 0

    # remove collateral
    elif instruction.action == 8:
        return extcall Wallet(_userWallet).removeCollateral(convert(instruction.legoId, uint256), instruction.asset, amount, instruction.extraAddr, instruction.extraVal, instruction.extraData)

    # borrow
    elif instruction.action == 9:
        return extcall Wallet(_userWallet).borrow(convert(instruction.legoId, uint256), instruction.asset, amount, instruction.extraAddr, instruction.extraVal, instruction.extraData)

    # repay debt
    elif instruction.action == 10:
        extcall Wallet(_userWallet).repayDebt(convert(instruction.legoId, uint256), instruction.asset, amount, instruction.extraAddr, instruction.extraVal, instruction.extraData)
        return 0

    # claim rewards
    elif instruction.action == 11:
        return extcall Wallet(_userWallet).claimRewards(convert(instruction.legoId, uint256), instruction.asset, instruction.amount, instruction.extraAddr, instruction.extraVal, instruction.extraData)

    # convert eth to weth
    elif instruction.action == 12:
        return extcall Wallet(_userWallet).convertEthToWeth(amount)

    # convert weth to eth
    elif instruction.action == 13:
        return extcall Wallet(_userWallet).convertWethToEth(amount)

    # add liquidity
    elif instruction.action == 14:
        amountA: uint256 = 0
        amountB: uint256 = 0
        prevAmountReceived, amountA, amountB = extcall Wallet(_userWallet).addLiquidity(convert(instruction.legoId, uint256), instruction.target, instruction.asset, instruction.asset2, amount, instruction.amount2, instruction.minOut1, instruction.minOut2, convert(instruction.auxData, uint256), instruction.extraAddr, instruction.extraVal, instruction.extraData)
        return prevAmountReceived

    # remove liquidity
    elif instruction.action == 15:
        # Extract lpToken address from auxData (lower 160 bits)
        lpToken: address = convert(convert(instruction.auxData, uint256) & convert(max_value(uint160), uint256), address)
        amountB: uint256 = 0
        lpAmountBurned: uint256 = 0
        # Params: legoId, pool (target), tokenA, tokenB, lpToken, lpAmount, minAmountA (minOut1), minAmountB (minOut2)
        # NOTE: Returns (amountA, amountB, lpBurned) - we pass forward amountA only
        prevAmountReceived, amountB, lpAmountBurned = extcall Wallet(_userWallet).removeLiquidity(convert(instruction.legoId, uint256), instruction.target, instruction.asset, instruction.asset2, lpToken, amount, instruction.minOut1, instruction.minOut2, instruction.extraAddr, instruction.extraVal, instruction.extraData)
        return prevAmountReceived

    # add liquidity concentrated
    elif instruction.action == 16:
        # Extract pool address (upper 160 bits) and nftId (lower 96 bits) from auxData
        pool: address = convert(convert(instruction.auxData, uint256) >> 96, address)
        nftId: uint256 = convert(instruction.auxData, uint256) & convert(max_value(uint96), uint256)
        # Params: legoId, nftAddr (target), nftId, pool, tokenA, tokenB, amountA, amountB (amount2)
        extcall Wallet(_userWallet).addLiquidityConcentrated(convert(instruction.legoId, uint256), instruction.target, nftId, pool, instruction.asset, instruction.asset2, amount, instruction.amount2, instruction.tickLower, instruction.tickUpper, instruction.minOut1, instruction.minOut2, instruction.extraAddr, instruction.extraVal, instruction.extraData)
        return 0

    # remove liquidity concentrated
    elif instruction.action == 17:
        # Extract pool address (upper 160 bits) and nftId (lower 96 bits) from auxData
        pool: address = convert(convert(instruction.auxData, uint256) >> 96, address)
        nftId: uint256 = convert(instruction.auxData, uint256) & convert(max_value(uint96), uint256)
        amountA: uint256 = 0
        amountB: uint256 = 0
        # Params: legoId, nftAddr (target), nftId, pool, tokenA, tokenB, liqToRemove, minAmountA (minOut1), minAmountB (minOut2)
        # NOTE: Returns (amountA, amountB, liquidity) - we pass forward amountA only
        prevAmountReceived, amountA, amountB = extcall Wallet(_userWallet).removeLiquidityConcentrated(convert(instruction.legoId, uint256), instruction.target, nftId, pool, instruction.asset, instruction.asset2, amount, instruction.minOut1, instruction.minOut2, instruction.extraAddr, instruction.extraVal, instruction.extraData)
        return prevAmountReceived

    else:
        raise "Invalid action"


##################
# Authentication #
##################


@internal
def _authenticateAccess(_messageHash: bytes32, _sig: Signature):
    if msg.sender != self.owner:
        # check expiration first to prevent DoS
        assert _sig.expiration >= block.timestamp # dev: signature expired

        # check nonce is valid
        assert _sig.nonce == self.currentNonce # dev: invalid nonce

        # verify signature and check it's from owner
        signer: address = self._verify(_messageHash, _sig)
        assert signer == self.owner # dev: invalid signer

        # increment nonce for next use
        self.currentNonce += 1


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


####################
# Nonce Management #
####################


@external
def incrementNonce():
    assert msg.sender == self.owner # dev: no perms
    oldNonce: uint256 = self.currentNonce
    self.currentNonce += 1
    log NonceIncremented(oldNonce=oldNonce, newNonce=self.currentNonce)


@view
@external
def getNonce() -> uint256:
    return self.currentNonce


#############
# Ownership #
#############


@external
def changeOwnership(_newOwner: address):
    currentOwner: address = self.owner
    assert msg.sender == currentOwner # dev: no perms
    assert _newOwner not in [empty(address), currentOwner] # dev: invalid new owner

    confirmBlock: uint256 = block.number + self.timeLock
    self.pendingOwner = PendingOwnerChange(
        newOwner = _newOwner,
        initiatedBlock = block.number,
        confirmBlock = confirmBlock,
    )
    log OwnershipChangeInitiated(prevOwner=currentOwner, newOwner=_newOwner, confirmBlock=confirmBlock)


@external
def confirmOwnershipChange():
    data: PendingOwnerChange = self.pendingOwner
    assert data.newOwner != empty(address) # dev: no pending owner
    assert data.confirmBlock != 0 and block.number >= data.confirmBlock # dev: time delay not reached
    assert msg.sender == data.newOwner # dev: only new owner can confirm

    prevOwner: address = self.owner
    self.owner = data.newOwner
    self.pendingOwner = empty(PendingOwnerChange)
    
    # reset nonce on ownership change for security
    self.currentNonce = 0
    
    log OwnershipChangeConfirmed(prevOwner=prevOwner, newOwner=data.newOwner, initiatedBlock=data.initiatedBlock, confirmBlock=data.confirmBlock)


@external
def cancelOwnershipChange():
    if msg.sender != self.owner:
        missionControl: address = staticcall Registry(UNDY_HQ).getAddr(MISSION_CONTROL_ID)
        assert staticcall MissionControl(missionControl).canPerformSecurityAction(msg.sender) # dev: no perms

    data: PendingOwnerChange = self.pendingOwner
    assert data.confirmBlock != 0 # dev: no pending change
    self.pendingOwner = empty(PendingOwnerChange)
    log OwnershipChangeCancelled(cancelledOwner=data.newOwner, cancelledBy=msg.sender, initiatedBlock=data.initiatedBlock, confirmBlock=data.confirmBlock)


# utils


@view
@external
def hasPendingOwnerChange() -> bool:
    return self._hasPendingOwnerChange()


@view
@internal
def _hasPendingOwnerChange() -> bool:
    return self.pendingOwner.confirmBlock != 0


#############
# Time Lock #
#############


# time lock


@external
def setTimeLock(_numBlocks: uint256):
    assert msg.sender == self.owner # dev: no perms
    assert _numBlocks >= MIN_TIMELOCK and _numBlocks <= MAX_TIMELOCK # dev: invalid delay
    self.timeLock = _numBlocks
    log TimeLockSet(numBlocks=_numBlocks)