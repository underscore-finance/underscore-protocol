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
#     ║  ** Earn Vault Agent Wrapper **                                                ║
#     ║  Manages yield operations for Earn Vaults: deposit, withdraw, swap, claim      ║
#     ╚════════════════════════════════════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

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
    action: uint8              # Action type: 10=depositYield, 11=withdrawYield
    legoId: uint16             # Protocol/Lego ID
    asset: address             # Primary asset/token (or vaultToken for withdrawals)
    target: address            # vaultAddr for deposits, unused for withdrawals
    amount: uint256            # Primary amount (or max_value for "all")
    extraData: bytes32         # Protocol-specific extra data

event NonceIncremented:
    userWallet: address
    oldNonce: uint256
    newNonce: uint256

groupId: public(uint256)
currentNonce: public(HashMap[address, uint256])

MAX_INSTRUCTIONS: constant(uint256) = 15
MAX_SWAP_INSTRUCTIONS: constant(uint256) = 5
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

    # deposit for yield
    if instruction.action == 10:
        assetAmount: uint256 = 0
        vaultToken: address = empty(address)
        assetAmount, vaultToken, nextAmount, txUsdValue = extcall Wallet(_userWallet).depositForYield(convert(instruction.legoId, uint256), instruction.asset, instruction.target, nextAmount, instruction.extraData)
        return nextAmount

    # withdraw from yield
    elif instruction.action == 11:
        underlyingAmount: uint256 = 0
        underlyingToken: address = empty(address)
        underlyingAmount, underlyingToken, nextAmount, txUsdValue = extcall Wallet(_userWallet).withdrawFromYield(convert(instruction.legoId, uint256), instruction.asset, nextAmount, instruction.extraData, False)
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
