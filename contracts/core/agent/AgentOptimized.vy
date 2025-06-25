# @version 0.4.3

from interfaces import Wallet
from interfaces import LegoPartner as Lego
from ethereum.ercs import IERC20

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
    signer: address
    expiration: uint256

# Optimized ActionInstruction struct - keeping extra params as dedicated fields
struct ActionInstruction:
    # Core action data (packed when possible)
    usePrevAmountOut: bool
    action: uint8  # Using uint8 instead of full ActionType enum
    legoId: uint16  # Support up to 65,535 legos
    
    # Primary fields (reused based on action type)
    asset: address      # Primary asset/token
    target: address     # Vault/pool/recipient/nftAddr
    amount: uint256     # Primary amount
    
    # Secondary fields (for complex actions)
    asset2: address     # Secondary asset (tokenB, etc)
    amount2: uint256    # Secondary amount
    minOut1: uint256    # Min amount out / minAmountA
    minOut2: uint256    # Min amount out B / minLpAmount
    
    # Tick values (only for concentrated liquidity)
    tickLower: int24
    tickUpper: int24
    
    # Extra params (always available as per Wallet interface)
    extraAddr: address
    extraVal: uint256
    extraData: bytes32
    
    # Additional encoding field for complex actions (not passed to wallet functions)
    auxData: bytes32    # For encoding pool addresses, minLpAmount, etc.
    
    # Swap instructions (only used for SWAP action)
    swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS]

# Field mapping by action type:
# EARN_DEPOSIT:      asset=asset, target=vaultAddr, amount=amount
# EARN_WITHDRAW:     asset=vaultToken, amount=amount  
# EARN_REBALANCE:    asset=fromVaultToken, target=toVaultAddr, amount=amount, legoId=fromLegoId, amount2=toLegoId
# SWAP:              swapInstructions used
# MINT_REDEEM:       asset=tokenIn, target=tokenOut, amount=amountIn, minOut1=minAmountOut
# CONFIRM_MINT_REDEEM: asset=tokenIn, target=tokenOut
# ADD_COLLATERAL:    asset=asset, amount=amount
# REMOVE_COLLATERAL: asset=asset, amount=amount
# BORROW:            asset=borrowAsset, amount=amount
# REPAY_DEBT:        asset=paymentAsset, amount=amount
# ADD_LIQ:           target=pool, asset=tokenA, asset2=tokenB, amount=amountA, amount2=amountB, minOut1=minAmountA, minOut2=minAmountB, auxData=minLpAmount(encoded)
# ADD_LIQ_CONC:      target=nftAddr, asset=tokenA, asset2=tokenB, amount=amountA, amount2=amountB, minOut1=minAmountA, minOut2=minAmountB, auxData=pool+nftTokenId(encoded), tickLower/tickUpper used
# REMOVE_LIQ:        target=pool, asset=tokenA, asset2=tokenB, amount=lpAmount, minOut1=minAmountA, minOut2=minAmountB, auxData=lpToken(encoded)
# REMOVE_LIQ_CONC:   target=nftAddr, asset=tokenA, asset2=tokenB, amount=liqToRemove, minOut1=minAmountA, minOut2=minAmountB, auxData=pool+nftTokenId(encoded)
# TRANSFER:          target=recipient, asset=asset, amount=amount
# REWARDS:           asset=rewardToken, amount=rewardAmount
# ETH_TO_WETH:       amount=amount
# WETH_TO_ETH:       amount=amount

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

# core
owner: public(address)

# config
timeLock: public(uint256) # num blocks!
pendingOwner: public(PendingOwnerChange)
usedSignatures: public(HashMap[Bytes[65], bool])

MAX_INSTRUCTIONS: constant(uint256) = 15
MAX_SWAP_INSTRUCTIONS: constant(uint256) = 5
MAX_TOKEN_PATH: constant(uint256) = 5
MISSION_CONTROL_ID: constant(uint256) = 3
API_VERSION: constant(String[28]) = "0.2.0"  # Updated version

# eip-712
ECRECOVER_PRECOMPILE: constant(address) = 0x0000000000000000000000000000000000000001
DOMAIN_TYPE_HASH: constant(bytes32) = keccak256('EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)')
DEPOSIT_TYPE_HASH: constant(bytes32) = keccak256('Deposit(address userWallet,uint256 legoId,address asset,address vaultAddr,uint256 amount,address extraAddr,uint256 extraVal,bytes32 extraData,uint256 expiration)')
WITHDRAWAL_TYPE_HASH: constant(bytes32) = keccak256('Withdrawal(address userWallet,uint256 legoId,address vaultToken,uint256 amount,address extraAddr,uint256 extraVal,bytes32 extraData,uint256 expiration)')
REBALANCE_TYPE_HASH: constant(bytes32) = keccak256('Rebalance(address userWallet,uint256 fromLegoId,address fromVaultToken,uint256 toLegoId,address toVaultAddr,uint256 fromVaultAmount,address extraAddr,uint256 extraVal,bytes32 extraData,uint256 expiration)')
SWAP_ACTION_TYPE_HASH: constant(bytes32) =  keccak256('Swap(address userWallet,SwapInstruction[] swapInstructions,uint256 expiration)')
SWAP_INSTRUCTION_TYPE_HASH: constant(bytes32) = keccak256('SwapInstruction(uint256 legoId,uint256 amountIn,uint256 minAmountOut,address[] tokenPath,address[] poolPath)')
MINT_REDEEM_TYPE_HASH: constant(bytes32) = keccak256('MintOrRedeem(address userWallet,uint256 legoId,address tokenIn,address tokenOut,uint256 amountIn,uint256 minAmountOut,address extraAddr,uint256 extraVal,bytes32 extraData,uint256 expiration)')
CONFIRM_MINT_REDEEM_TYPE_HASH: constant(bytes32) = keccak256('ConfirmMintOrRedeem(address userWallet,uint256 legoId,address tokenIn,address tokenOut,address extraAddr,uint256 extraVal,bytes32 extraData,uint256 expiration)')
ADD_COLLATERAL_TYPE_HASH: constant(bytes32) = keccak256('AddCollateral(address userWallet,uint256 legoId,address asset,uint256 amount,address extraAddr,uint256 extraVal,bytes32 extraData,uint256 expiration)')
REMOVE_COLLATERAL_TYPE_HASH: constant(bytes32) = keccak256('RemoveCollateral(address userWallet,uint256 legoId,address asset,uint256 amount,address extraAddr,uint256 extraVal,bytes32 extraData,uint256 expiration)')
BORROW_TYPE_HASH: constant(bytes32) = keccak256('Borrow(address userWallet,uint256 legoId,address borrowAsset,uint256 amount,address extraAddr,uint256 extraVal,bytes32 extraData,uint256 expiration)')
REPAY_DEBT_TYPE_HASH: constant(bytes32) = keccak256('RepayDebt(address userWallet,uint256 legoId,address paymentAsset,uint256 paymentAmount,address extraAddr,uint256 extraVal,bytes32 extraData,uint256 expiration)')
ADD_LIQUIDITY_TYPE_HASH: constant(bytes32) = keccak256('AddLiquidity(address userWallet,uint256 legoId,address pool,address tokenA,address tokenB,uint256 amountA,uint256 amountB,uint256 minAmountA,uint256 minAmountB,uint256 minLpAmount,address extraAddr,uint256 extraVal,bytes32 extraData,uint256 expiration)')
ADD_LIQUIDITY_CONCENTRATED_TYPE_HASH: constant(bytes32) = keccak256('AddLiquidityConcentrated(address userWallet,uint256 legoId,address nftAddr,uint256 nftTokenId,address pool,address tokenA,address tokenB,uint256 amountA,uint256 amountB,int24 tickLower,int24 tickUpper,uint256 minAmountA,uint256 minAmountB,address extraAddr,uint256 extraVal,bytes32 extraData,uint256 expiration)')
REMOVE_LIQUIDITY_TYPE_HASH: constant(bytes32) = keccak256('RemoveLiquidity(address userWallet,uint256 legoId,address pool,address tokenA,address tokenB,address lpToken,uint256 lpAmount,uint256 minAmountA,uint256 minAmountB,address extraAddr,uint256 extraVal,bytes32 extraData,uint256 expiration)')
REMOVE_LIQUIDITY_CONCENTRATED_TYPE_HASH: constant(bytes32) = keccak256('RemoveLiquidityConcentrated(address userWallet,uint256 legoId,address nftAddr,uint256 nftTokenId,address pool,address tokenA,address tokenB,uint256 liqToRemove,uint256 minAmountA,uint256 minAmountB,address extraAddr,uint256 extraVal,bytes32 extraData,uint256 expiration)')
TRANSFER_FUNDS_TYPE_HASH: constant(bytes32) = keccak256('TransferFunds(address userWallet,address recipient,address asset,uint256 amount,uint256 expiration)')
CLAIM_REWARDS_TYPE_HASH: constant(bytes32) = keccak256('ClaimRewards(address userWallet,uint256 legoId,address rewardToken,uint256 rewardAmount,address extraAddr,uint256 extraVal,bytes32 extraData,uint256 expiration)')
CONVERT_ETH_TO_WETH_TYPE_HASH: constant(bytes32) = keccak256('ConvertEthToWeth(address userWallet,uint256 amount,uint256 expiration)')
CONVERT_WETH_TO_ETH_TYPE_HASH: constant(bytes32) = keccak256('ConvertWethToEth(address userWallet,uint256 amount,uint256 expiration)')
BATCH_ACTIONS_TYPE_HASH: constant(bytes32) = keccak256('BatchActions(address userWallet,ActionInstruction[] instructions,uint256 expiration)')
ACTION_INSTRUCTION_TYPE_HASH: constant(bytes32) = keccak256('ActionInstruction(bool usePrevAmountOut,uint8 action,uint16 legoId,address asset,address target,uint256 amount,address asset2,uint256 amount2,uint256 minOut1,uint256 minOut2,int24 tickLower,int24 tickUpper,address extraAddr,uint256 extraVal,bytes32 extraData,bytes32 auxData,SwapInstruction[] swapInstructions)')

UNDY_HQ: public(immutable(address))
MIN_TIMELOCK: public(immutable(uint256))
MAX_TIMELOCK: public(immutable(uint256))


@deploy
def __init__(
    _undyHq: address,
    _owner: address,
    _minTimeLock: uint256,
    _maxTimeLock: uint256,
):
    assert empty(address) not in [_undyHq, _owner] # dev: invalid addrs
    UNDY_HQ = _undyHq
    self.owner = _owner

    # time lock
    assert _minTimeLock < _maxTimeLock # dev: invalid delay
    MIN_TIMELOCK = _minTimeLock
    MAX_TIMELOCK = _maxTimeLock
    self.timeLock = _minTimeLock


@pure
@external
def apiVersion() -> String[28]:
    return API_VERSION


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


#########
# Yield #
#########


# deposit


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
    owner: address = self.owner
    if msg.sender != owner:
        self._isValidSignature(abi_encode(DEPOSIT_TYPE_HASH, _userWallet, _legoId, _asset, _vaultAddr, _amount, _extraAddr, _extraVal, _extraData, _sig.expiration), _sig)
        assert _sig.signer == owner # dev: invalid signer
    return extcall Wallet(_userWallet).depositForYield(_legoId, _asset, _vaultAddr, _amount, _extraAddr, _extraVal, _extraData)


# withdraw


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
    owner: address = self.owner
    if msg.sender != owner:
        self._isValidSignature(abi_encode(WITHDRAWAL_TYPE_HASH, _userWallet, _legoId, _vaultToken, _amount, _extraAddr, _extraVal, _extraData, _sig.expiration), _sig)
        assert _sig.signer == owner # dev: invalid signer
    return extcall Wallet(_userWallet).withdrawFromYield(_legoId, _vaultToken, _amount, _extraAddr, _extraVal, _extraData)


# rebalance position


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
    owner: address = self.owner
    if msg.sender != owner:
        self._isValidSignature(abi_encode(REBALANCE_TYPE_HASH, _userWallet, _fromLegoId, _fromVaultToken, _toLegoId, _toVaultAddr, _fromVaultAmount, _extraAddr, _extraVal, _extraData, _sig.expiration), _sig)
        assert _sig.signer == owner # dev: invalid signer
    return extcall Wallet(_userWallet).rebalanceYieldPosition(_fromLegoId, _fromVaultToken, _toLegoId, _toVaultAddr, _fromVaultAmount, _extraAddr, _extraVal, _extraData)


###################
# Swap / Exchange #
###################


# swap


@nonreentrant
@external
def swapTokens(
    _userWallet: address,
    _swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS],
    _sig: Signature = empty(Signature),
) -> (address, uint256, address, uint256):
    owner: address = self.owner
    if msg.sender != owner:
        self._isValidSwapSignature(self._hashSwapInstructions(_userWallet, _swapInstructions, _sig.expiration), _sig)
        assert _sig.signer == owner # dev: invalid signer
    return extcall Wallet(_userWallet).swapTokens(_swapInstructions)


@view
@internal
def _encodeSwapInstruction(_instruction: Wallet.SwapInstruction) -> Bytes[544]:
    # Just encode, no hash
    return abi_encode(
        SWAP_INSTRUCTION_TYPE_HASH,
        _instruction.legoId,
        _instruction.amountIn,
        _instruction.minAmountOut,
        _instruction.tokenPath,
        _instruction.poolPath
    )


@view
@internal
def _encodeSwapInstructions(_swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS]) -> Bytes[2720]:
    concatenated: Bytes[2720] = empty(Bytes[2720]) # max size for 5 instructions - 5*544
    for i: uint256 in range(len(_swapInstructions), bound=MAX_SWAP_INSTRUCTIONS):
        concatenated = convert(
            concat(
                concatenated, 
                self._encodeSwapInstruction(_swapInstructions[i])
            ),
            Bytes[2720]
        )
    return concatenated


@view
@internal
def _hashSwapInstructions(
    _userWallet: address,
    _swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS],
    _expiration: uint256,
) -> Bytes[2880]:
    # Now we encode everything and hash only once at the end
    return abi_encode(
        SWAP_ACTION_TYPE_HASH,
        _userWallet,
        self._encodeSwapInstructions(_swapInstructions),
        _expiration
    )


@internal
def _isValidSwapSignature(_encodedValue: Bytes[2880], _sig: Signature):
    encoded_hash: bytes32 = keccak256(_encodedValue)
    domain_sep: bytes32 = self._domainSeparator()
    
    digest: bytes32 = keccak256(concat(b'\x19\x01', domain_sep, encoded_hash))
    
    assert not self.usedSignatures[_sig.signature] # dev: signature already used
    assert _sig.expiration >= block.timestamp # dev: signature expired
    
    # NOTE: signature is packed as r, s, v
    r: bytes32 = convert(slice(_sig.signature, 0, 32), bytes32)
    s: bytes32 = convert(slice(_sig.signature, 32, 32), bytes32)
    v: uint8 = convert(slice(_sig.signature, 64, 1), uint8)
    
    response: Bytes[32] = raw_call(
        ECRECOVER_PRECOMPILE,
        abi_encode(digest, v, r, s),
        max_outsize=32,
        is_static_call=True # This is a view function
    )
    
    assert len(response) == 32 # dev: invalid ecrecover response length
    assert abi_decode(response, address) == _sig.signer # dev: invalid signature
    self.usedSignatures[_sig.signature] = True


@view
@external
def getSwapActionHash(
    _userWallet: address,
    _swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS],
    _expiration: uint256,
) -> bytes32:
    encodedValue: Bytes[2880] = self._hashSwapInstructions(_userWallet, _swapInstructions, _expiration)
    encoded_hash: bytes32 = keccak256(encodedValue)
    return keccak256(concat(b'\x19\x01', self._domainSeparator(), encoded_hash))


# mint / redeem


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
    owner: address = self.owner
    if msg.sender != owner:
        self._isValidSignature(abi_encode(MINT_REDEEM_TYPE_HASH, _userWallet, _legoId, _tokenIn, _tokenOut, _amountIn, _minAmountOut, _extraAddr, _extraVal, _extraData, _sig.expiration), _sig)
        assert _sig.signer == owner # dev: invalid signer
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
) -> (uint256, uint256):
    owner: address = self.owner
    if msg.sender != owner:
        self._isValidSignature(abi_encode(CONFIRM_MINT_REDEEM_TYPE_HASH, _userWallet, _legoId, _tokenIn, _tokenOut, _extraAddr, _extraVal, _extraData, _sig.expiration), _sig)
        assert _sig.signer == owner # dev: invalid signer
    return extcall Wallet(_userWallet).confirmMintOrRedeemAsset(_legoId, _tokenIn, _tokenOut, _extraAddr, _extraVal, _extraData)


########
# Debt #
########


# add collateral


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
    owner: address = self.owner
    if msg.sender != owner:
        self._isValidSignature(abi_encode(ADD_COLLATERAL_TYPE_HASH, _userWallet, _legoId, _asset, _amount, _extraAddr, _extraVal, _extraData, _sig.expiration), _sig)
        assert _sig.signer == owner # dev: invalid signer
    return extcall Wallet(_userWallet).addCollateral(_legoId, _asset, _amount, _extraAddr, _extraVal, _extraData)


# remove collateral


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
    owner: address = self.owner
    if msg.sender != owner:
        self._isValidSignature(abi_encode(REMOVE_COLLATERAL_TYPE_HASH, _userWallet, _legoId, _asset, _amount, _extraAddr, _extraVal, _extraData, _sig.expiration), _sig)
        assert _sig.signer == owner # dev: invalid signer
    return extcall Wallet(_userWallet).removeCollateral(_legoId, _asset, _amount, _extraAddr, _extraVal, _extraData)


# borrow


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
) -> (address, uint256):
    owner: address = self.owner
    if msg.sender != owner:
        self._isValidSignature(abi_encode(BORROW_TYPE_HASH, _userWallet, _legoId, _borrowAsset, _amount, _extraAddr, _extraVal, _extraData, _sig.expiration), _sig)
        assert _sig.signer == owner # dev: invalid signer
    return extcall Wallet(_userWallet).borrow(_legoId, _borrowAsset, _amount, _extraAddr, _extraVal, _extraData)


# repay debt


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
    owner: address = self.owner
    if msg.sender != owner:
        self._isValidSignature(abi_encode(REPAY_DEBT_TYPE_HASH, _userWallet, _legoId, _paymentAsset, _paymentAmount, _extraAddr, _extraVal, _extraData, _sig.expiration), _sig)
        assert _sig.signer == owner # dev: invalid signer
    return extcall Wallet(_userWallet).repayDebt(_legoId, _paymentAsset, _paymentAmount, _extraAddr, _extraVal, _extraData)


#############
# Liquidity #
#############


# add liquidity


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
    owner: address = self.owner
    if msg.sender != owner:
        self._isValidSignature(abi_encode(ADD_LIQUIDITY_TYPE_HASH, _userWallet, _legoId, _pool, _tokenA, _tokenB, _amountA, _amountB, _minAmountA, _minAmountB, _minLpAmount, _extraAddr, _extraVal, _extraData, _sig.expiration), _sig)
        assert _sig.signer == owner # dev: invalid signer
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
    owner: address = self.owner
    if msg.sender != owner:
        self._isValidSignature(abi_encode(ADD_LIQUIDITY_CONCENTRATED_TYPE_HASH, _userWallet, _legoId, _nftAddr, _nftTokenId, _pool, _tokenA, _tokenB, _amountA, _amountB, _tickLower, _tickUpper, _minAmountA, _minAmountB, _extraAddr, _extraVal, _extraData, _sig.expiration), _sig)
        assert _sig.signer == owner # dev: invalid signer
    return extcall Wallet(_userWallet).addLiquidityConcentrated(_legoId, _nftAddr, _nftTokenId, _pool, _tokenA, _tokenB, _amountA, _amountB, _tickLower, _tickUpper, _minAmountA, _minAmountB, _extraAddr, _extraVal, _extraData)


# remove liquidity


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
    owner: address = self.owner
    if msg.sender != owner:
        self._isValidSignature(abi_encode(REMOVE_LIQUIDITY_TYPE_HASH, _userWallet, _legoId, _pool, _tokenA, _tokenB, _lpToken, _lpAmount, _minAmountA, _minAmountB, _extraAddr, _extraVal, _extraData, _sig.expiration), _sig)
        assert _sig.signer == owner # dev: invalid signer
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
    owner: address = self.owner
    if msg.sender != owner:
        self._isValidSignature(abi_encode(REMOVE_LIQUIDITY_CONCENTRATED_TYPE_HASH, _userWallet, _legoId, _nftAddr, _nftTokenId, _pool, _tokenA, _tokenB, _liqToRemove, _minAmountA, _minAmountB, _extraAddr, _extraVal, _extraData, _sig.expiration), _sig)
        assert _sig.signer == owner # dev: invalid signer
    return extcall Wallet(_userWallet).removeLiquidityConcentrated(_legoId, _nftAddr, _nftTokenId, _pool, _tokenA, _tokenB, _liqToRemove, _minAmountA, _minAmountB, _extraAddr, _extraVal, _extraData)


##################
# Transfer Funds #
##################


@nonreentrant
@external
def transferFunds(
    _userWallet: address,
    _recipient: address,
    _asset: address = empty(address),
    _amount: uint256 = max_value(uint256),
    _sig: Signature = empty(Signature),
) -> uint256:
    owner: address = self.owner
    if msg.sender != owner:
        self._isValidSignature(abi_encode(TRANSFER_FUNDS_TYPE_HASH, _userWallet, _recipient, _asset, _amount, _sig.expiration), _sig)
        assert _sig.signer == owner # dev: invalid signer
    return extcall Wallet(_userWallet).transferFunds(_recipient, _asset, _amount)


#################
# Claim Rewards #
#################


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
    owner: address = self.owner
    if msg.sender != owner:
        self._isValidSignature(abi_encode(CLAIM_REWARDS_TYPE_HASH, _userWallet, _legoId, _rewardToken, _rewardAmount, _extraAddr, _extraVal, _extraData, _sig.expiration), _sig)
        assert _sig.signer == owner # dev: invalid signer
    return extcall Wallet(_userWallet).claimRewards(_legoId, _rewardToken, _rewardAmount, _extraAddr, _extraVal, _extraData)


################
# Wrapped ETH #
################


# eth -> weth


@nonreentrant
@external
def convertEthToWeth(_userWallet: address, _amount: uint256 = max_value(uint256), _sig: Signature = empty(Signature)) -> uint256:
    owner: address = self.owner
    if msg.sender != owner:
        self._isValidSignature(abi_encode(CONVERT_ETH_TO_WETH_TYPE_HASH, _userWallet, _amount, _sig.expiration), _sig)
        assert _sig.signer == owner # dev: invalid signer
    return extcall Wallet(_userWallet).convertEthToWeth(_amount)


# weth -> eth


@nonreentrant
@external
def convertWethToEth(_userWallet: address, _amount: uint256 = max_value(uint256), _sig: Signature = empty(Signature)) -> uint256:
    owner: address = self.owner
    if msg.sender != owner:
        self._isValidSignature(abi_encode(CONVERT_WETH_TO_ETH_TYPE_HASH, _userWallet, _amount, _sig.expiration), _sig)
        assert _sig.signer == owner # dev: invalid signer
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
    owner: address = self.owner
    if msg.sender != owner:
        self._isValidBatchSignature(self._hashBatchActions(_userWallet, _instructions, _sig.expiration), _sig)
        assert _sig.signer == owner # dev: invalid signer

    assert len(_instructions) != 0 # dev: no instructions
    prevAmountReceived: uint256 = 0

    # not using these vars
    naAddyA: address = empty(address)
    naAddyB: address = empty(address)
    naValueA: uint256 = 0
    naValueB: uint256 = 0
    naValueC: uint256 = 0
    naValueD: uint256 = 0
    naBool: bool = False

    # iterate through instructions
    for j: ActionInstruction in _instructions:
        i: ActionInstruction = j
        
        # Convert action to ActionType enum
        action: Wallet.ActionType = self._convertActionType(i.action)

        # deposit
        if action == Wallet.ActionType.EARN_DEPOSIT:
            amount: uint256 = i.amount
            if i.usePrevAmountOut and prevAmountReceived != 0:
                amount = prevAmountReceived
            naValueA, naAddyA, prevAmountReceived = extcall Wallet(_userWallet).depositForYield(convert(i.legoId, uint256), i.asset, i.target, amount, i.extraAddr, i.extraVal, i.extraData)

        # withdraw
        elif action == Wallet.ActionType.EARN_WITHDRAW:
            amount: uint256 = i.amount
            if i.usePrevAmountOut and prevAmountReceived != 0:
                amount = prevAmountReceived
            naValueA, naAddyA, prevAmountReceived = extcall Wallet(_userWallet).withdrawFromYield(convert(i.legoId, uint256), i.asset, amount, i.extraAddr, i.extraVal, i.extraData)

        # rebalance
        elif action == Wallet.ActionType.EARN_REBALANCE:
            amount: uint256 = i.amount
            if i.usePrevAmountOut and prevAmountReceived != 0:
                amount = prevAmountReceived
            # amount2 holds toLegoId
            naValueA, naAddyA, prevAmountReceived = extcall Wallet(_userWallet).rebalanceYieldPosition(convert(i.legoId, uint256), i.asset, i.amount2, i.target, amount, i.extraAddr, i.extraVal, i.extraData)

        # swap
        elif action == Wallet.ActionType.SWAP:
            if i.usePrevAmountOut and prevAmountReceived != 0:
                i.swapInstructions[0].amountIn = prevAmountReceived
            naAddyA, naValueA, naAddyB, prevAmountReceived = extcall Wallet(_userWallet).swapTokens(i.swapInstructions)

        # mint / redeem
        elif action == Wallet.ActionType.MINT_REDEEM:
            amount: uint256 = i.amount
            if i.usePrevAmountOut and prevAmountReceived != 0:
                amount = prevAmountReceived
            naValueA, prevAmountReceived, naBool = extcall Wallet(_userWallet).mintOrRedeemAsset(convert(i.legoId, uint256), i.asset, i.target, amount, i.minOut1, i.extraAddr, i.extraVal, i.extraData)

        # confirm mint / redeem
        elif action == Wallet.ActionType.CONFIRM_MINT_REDEEM:
            naValueA, prevAmountReceived = extcall Wallet(_userWallet).confirmMintOrRedeemAsset(convert(i.legoId, uint256), i.asset, i.target, i.extraAddr, i.extraVal, i.extraData)

        # add collateral
        elif action == Wallet.ActionType.ADD_COLLATERAL:
            amount: uint256 = i.amount
            if i.usePrevAmountOut and prevAmountReceived != 0:
                amount = prevAmountReceived
            naValueA = extcall Wallet(_userWallet).addCollateral(convert(i.legoId, uint256), i.asset, amount, i.extraAddr, i.extraVal, i.extraData)
            prevAmountReceived = 0 # clearing this out

        # remove collateral
        elif action == Wallet.ActionType.REMOVE_COLLATERAL:
            amount: uint256 = i.amount
            if i.usePrevAmountOut and prevAmountReceived != 0:
                amount = prevAmountReceived
            prevAmountReceived = extcall Wallet(_userWallet).removeCollateral(convert(i.legoId, uint256), i.asset, amount, i.extraAddr, i.extraVal, i.extraData)

        # borrow
        elif action == Wallet.ActionType.BORROW:
            amount: uint256 = i.amount
            if i.usePrevAmountOut and prevAmountReceived != 0:
                amount = prevAmountReceived
            naAddyA, prevAmountReceived = extcall Wallet(_userWallet).borrow(convert(i.legoId, uint256), i.asset, amount, i.extraAddr, i.extraVal, i.extraData)

        # repay debt
        elif action == Wallet.ActionType.REPAY_DEBT:
            amount: uint256 = i.amount
            if i.usePrevAmountOut and prevAmountReceived != 0:
                amount = prevAmountReceived
            naValueA = extcall Wallet(_userWallet).repayDebt(convert(i.legoId, uint256), i.asset, amount, i.extraAddr, i.extraVal, i.extraData)
            prevAmountReceived = 0 # clearing this out

        # add liquidity
        elif action == Wallet.ActionType.ADD_LIQ:
            amountA: uint256 = i.amount
            if i.usePrevAmountOut and prevAmountReceived != 0:
                amountA = prevAmountReceived
            # minLpAmount encoded in auxData
            minLpAmount: uint256 = convert(i.auxData, uint256)
            prevAmountReceived, naValueA, naValueB = extcall Wallet(_userWallet).addLiquidity(convert(i.legoId, uint256), i.target, i.asset, i.asset2, amountA, i.amount2, i.minOut1, i.minOut2, minLpAmount, i.extraAddr, i.extraVal, i.extraData)

        # add liquidity (concentrated)
        elif action == Wallet.ActionType.ADD_LIQ_CONC:
            amountA: uint256 = i.amount
            if i.usePrevAmountOut and prevAmountReceived != 0:
                amountA = prevAmountReceived
            # Pool address in first 20 bytes of auxData, nftTokenId in last 12 bytes
            pool: address = convert(convert(i.auxData, uint256) >> 96, address)
            nftTokenId: uint256 = convert(i.auxData, uint256) & convert(max_value(uint96), uint256)
            naValueA, naValueB, naValueC, naValueD = extcall Wallet(_userWallet).addLiquidityConcentrated(convert(i.legoId, uint256), i.target, nftTokenId, pool, i.asset, i.asset2, amountA, i.amount2, i.tickLower, i.tickUpper, i.minOut1, i.minOut2, i.extraAddr, i.extraVal, i.extraData)
            prevAmountReceived = 0 # clearing this out (nft is received back)

        # remove liquidity
        elif action == Wallet.ActionType.REMOVE_LIQ:
            lpAmount: uint256 = i.amount
            if i.usePrevAmountOut and prevAmountReceived != 0:
                lpAmount = prevAmountReceived
            # lpToken encoded in auxData
            lpToken: address = convert(convert(i.auxData, uint256) & convert(max_value(uint160), uint256), address)
            prevAmountReceived, naValueA, naValueB = extcall Wallet(_userWallet).removeLiquidity(convert(i.legoId, uint256), i.target, i.asset, i.asset2, lpToken, lpAmount, i.minOut1, i.minOut2, i.extraAddr, i.extraVal, i.extraData)

        # remove liquidity (concentrated)
        elif action == Wallet.ActionType.REMOVE_LIQ_CONC:
            liqToRemove: uint256 = i.amount
            if i.usePrevAmountOut and prevAmountReceived != 0:
                liqToRemove = prevAmountReceived
            # Pool address in first 20 bytes of auxData, nftTokenId in last 12 bytes
            pool: address = convert(convert(i.auxData, uint256) >> 96, address)
            nftTokenId: uint256 = convert(i.auxData, uint256) & convert(max_value(uint96), uint256)
            prevAmountReceived, naValueA, naValueB = extcall Wallet(_userWallet).removeLiquidityConcentrated(convert(i.legoId, uint256), i.target, nftTokenId, pool, i.asset, i.asset2, liqToRemove, i.minOut1, i.minOut2, i.extraAddr, i.extraVal, i.extraData)

        # transfer
        elif action == Wallet.ActionType.TRANSFER:
            amount: uint256 = i.amount
            if i.usePrevAmountOut and prevAmountReceived != 0:
                amount = prevAmountReceived
            naValueA = extcall Wallet(_userWallet).transferFunds(i.target, i.asset, amount)
            prevAmountReceived = 0 # clearing this out

        # claim rewards
        elif action == Wallet.ActionType.REWARDS:
            prevAmountReceived = extcall Wallet(_userWallet).claimRewards(convert(i.legoId, uint256), i.asset, i.amount, i.extraAddr, i.extraVal, i.extraData)

        # eth -> weth
        elif action == Wallet.ActionType.ETH_TO_WETH:
            amount: uint256 = i.amount
            if i.usePrevAmountOut and prevAmountReceived != 0:
                amount = prevAmountReceived
            prevAmountReceived = extcall Wallet(_userWallet).convertEthToWeth(amount)

        # weth -> eth
        elif action == Wallet.ActionType.WETH_TO_ETH:
            amount: uint256 = i.amount
            if i.usePrevAmountOut and prevAmountReceived != 0:
                amount = prevAmountReceived
            prevAmountReceived = extcall Wallet(_userWallet).convertWethToEth(amount)

    return True


@view
@internal
def _convertActionType(_action: uint8) -> Wallet.ActionType:
    # Convert uint8 to ActionType enum
    if _action == 0:
        return Wallet.ActionType.EARN_DEPOSIT
    elif _action == 1:
        return Wallet.ActionType.EARN_WITHDRAW
    elif _action == 2:
        return Wallet.ActionType.EARN_REBALANCE
    elif _action == 3:
        return Wallet.ActionType.SWAP
    elif _action == 4:
        return Wallet.ActionType.MINT_REDEEM
    elif _action == 5:
        return Wallet.ActionType.CONFIRM_MINT_REDEEM
    elif _action == 6:
        return Wallet.ActionType.ADD_COLLATERAL
    elif _action == 7:
        return Wallet.ActionType.REMOVE_COLLATERAL
    elif _action == 8:
        return Wallet.ActionType.BORROW
    elif _action == 9:
        return Wallet.ActionType.REPAY_DEBT
    elif _action == 10:
        return Wallet.ActionType.ADD_LIQ
    elif _action == 11:
        return Wallet.ActionType.ADD_LIQ_CONC
    elif _action == 12:
        return Wallet.ActionType.REMOVE_LIQ
    elif _action == 13:
        return Wallet.ActionType.REMOVE_LIQ_CONC
    elif _action == 14:
        return Wallet.ActionType.TRANSFER
    elif _action == 15:
        return Wallet.ActionType.REWARDS
    elif _action == 16:
        return Wallet.ActionType.ETH_TO_WETH
    elif _action == 17:
        return Wallet.ActionType.WETH_TO_ETH
    else:
        raise "Invalid action type"


@view
@internal
def _encodeBatchActionInstruction(_instr: ActionInstruction) -> Bytes[3328]:
    encodedSwapInstructions: Bytes[2720] = self._encodeSwapInstructions(_instr.swapInstructions)

    # Encode with new struct format
    return abi_encode(
        ACTION_INSTRUCTION_TYPE_HASH,
        _instr.usePrevAmountOut,
        _instr.action,
        _instr.legoId,
        _instr.asset,
        _instr.target,
        _instr.amount,
        _instr.asset2,
        _instr.amount2,
        _instr.minOut1,
        _instr.minOut2,
        _instr.tickLower,
        _instr.tickUpper,
        _instr.extraAddr,
        _instr.extraVal,
        _instr.extraData,
        _instr.auxData,
        encodedSwapInstructions,
    )


@view
@internal
def _encodeBatchInstructions(_instructions: DynArray[ActionInstruction, MAX_INSTRUCTIONS]) -> Bytes[49920]:
    concatenated: Bytes[49920] = empty(Bytes[49920]) # max size for 15 instructions - 15*3328
    for i: uint256 in range(len(_instructions), bound=MAX_INSTRUCTIONS):
        concatenated = convert(
            concat(
                concatenated, 
                self._encodeBatchActionInstruction(_instructions[i])
            ),
            Bytes[49920]
        )
    return concatenated


@view
@internal
def _hashBatchActions(_userWallet: address, _instructions: DynArray[ActionInstruction, MAX_INSTRUCTIONS], _expiration: uint256) -> Bytes[50080]:
    # Now we encode everything and hash only once at the end
    return abi_encode(
        BATCH_ACTIONS_TYPE_HASH,
        _userWallet,
        self._encodeBatchInstructions(_instructions),
        _expiration
    )


@internal
def _isValidBatchSignature(_encodedValue: Bytes[50080], _sig: Signature):
    encoded_hash: bytes32 = keccak256(_encodedValue)
    domain_sep: bytes32 = self._domainSeparator()
    
    digest: bytes32 = keccak256(concat(b'\x19\x01', domain_sep, encoded_hash))
    
    assert not self.usedSignatures[_sig.signature] # dev: signature already used
    assert _sig.expiration >= block.timestamp # dev: signature expired
    
    # NOTE: signature is packed as r, s, v
    r: bytes32 = convert(slice(_sig.signature, 0, 32), bytes32)
    s: bytes32 = convert(slice(_sig.signature, 32, 32), bytes32)
    v: uint8 = convert(slice(_sig.signature, 64, 1), uint8)
    
    response: Bytes[32] = raw_call(
        ECRECOVER_PRECOMPILE,
        abi_encode(digest, v, r, s),
        max_outsize=32,
        is_static_call=True # This is a view function
    )
    
    assert len(response) == 32 # dev: invalid ecrecover response length
    assert abi_decode(response, address) == _sig.signer # dev: invalid signature
    self.usedSignatures[_sig.signature] = True


@view
@external
def getBatchActionHash(_userWallet: address, _instructions: DynArray[ActionInstruction, MAX_INSTRUCTIONS], _expiration: uint256) -> bytes32:
    encodedValue: Bytes[51520] = self._hashBatchActions(_userWallet, _instructions, _expiration)
    encoded_hash: bytes32 = keccak256(encodedValue)
    return keccak256(concat(b'\x19\x01', self._domainSeparator(), encoded_hash))


###########
# EIP 712 #
###########


@view
@external
def DOMAIN_SEPARATOR() -> bytes32:
    return self._domainSeparator()


@view
@internal
def _domainSeparator() -> bytes32:
    return keccak256(
        concat(
            DOMAIN_TYPE_HASH,
            keccak256('UnderscoreAgent'),
            keccak256(API_VERSION),
            abi_encode(chain.id, self)
        )
    )


@internal
def _isValidSignature(_encodedValue: Bytes[576], _sig: Signature):
    assert not self.usedSignatures[_sig.signature] # dev: signature already used
    assert _sig.expiration >= block.timestamp # dev: signature expired

    digest: bytes32 = keccak256(concat(b'\x19\x01', self._domainSeparator(), keccak256(_encodedValue)))

    # NOTE: signature is packed as r, s, v
    r: bytes32 = convert(slice(_sig.signature, 0, 32), bytes32)
    s: bytes32 = convert(slice(_sig.signature, 32, 32), bytes32)
    v: uint8 = convert(slice(_sig.signature, 64, 1), uint8)

    response: Bytes[32] = raw_call(
        ECRECOVER_PRECOMPILE,
        abi_encode(digest, v, r, s),
        max_outsize=32,
        is_static_call=True # This is a view function
    )

    assert len(response) == 32 # dev: invalid ecrecover response length
    assert abi_decode(response, address) == _sig.signer # dev: invalid signature
    self.usedSignatures[_sig.signature] = True