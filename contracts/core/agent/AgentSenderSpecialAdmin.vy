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
#     ╔════════════════════════════════════════════════════════════════════╗
#     ║  ** Agent Sender - Special Admin Workflows **                      ║
#     ║  Code-size split for special actions 104-106 to keep Special small. ║
#     ╚════════════════════════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

initializes: ownership
exports: ownership.__interface__
import contracts.modules.Ownership as ownership

from interfaces import Wallet
from interfaces import AgentWrapper
from ethereum.ercs import IERC20

struct ChequeInstruction:
    recipient: address
    asset: address
    amount: uint256
    unlockNumBlocks: uint256
    expiryNumBlocks: uint256
    canManagerPay: bool
    canBePulled: bool

struct Signature:
    signature: Bytes[65]
    nonce: uint256
    expiration: uint256

event NonceIncremented:
    userWallet: address
    oldNonce: uint256
    newNonce: uint256

currentNonce: public(HashMap[address, uint256])

MAX_CHEQUES: constant(uint256) = 25
MAX_WHITELIST_ADDRS: constant(uint256) = 25
MAX_SWAP_INSTRUCTIONS: constant(uint256) = 5
MAX_PROOFS: constant(uint256) = 25

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


#########################
# Specialized Workflows #
#########################


@external
def issuePullCheques(
    _agentWrapper: address,
    _userWallet: address,
    _cheques: DynArray[ChequeInstruction, MAX_CHEQUES],
    _sig: Signature = empty(Signature),
):
    # 1. validate workflow-specific cheque flags before authentication
    for cheque: ChequeInstruction in _cheques:
        assert not cheque.canManagerPay and cheque.canBePulled # dev: invalid pull cheque flags

    # 2. authenticate access (action code 104)
    messageHash: bytes32 = keccak256(abi_encode(
        convert(104, uint8),
        _agentWrapper,
        _userWallet,
        _cheques,
        _sig.nonce,
        _sig.expiration
    ))
    self._authenticateAccess(_userWallet, messageHash, _sig)

    # 3. create typed pull cheques. Any invalid cheque reverts the full workflow.
    for cheque: ChequeInstruction in _cheques:
        assert extcall AgentWrapper(_agentWrapper).createCheque(
            _userWallet,
            cheque.recipient,
            cheque.asset,
            cheque.amount,
            cheque.unlockNumBlocks,
            cheque.expiryNumBlocks,
            False,
            True,
        )


@external
def whitelistMaintenance(
    _agentWrapper: address,
    _userWallet: address,
    _confirmAddrs: DynArray[address, MAX_WHITELIST_ADDRS] = [],
    _cancelPendingAddrs: DynArray[address, MAX_WHITELIST_ADDRS] = [],
    _removeAddrs: DynArray[address, MAX_WHITELIST_ADDRS] = [],
    _sig: Signature = empty(Signature),
):
    # 1. validate duplicates before auth so bad maintenance payloads do not consume nonces.
    self._validateWhitelistMaintenance(_confirmAddrs, _cancelPendingAddrs, _removeAddrs)

    # 2. authenticate access (action code 105)
    messageHash: bytes32 = keccak256(abi_encode(
        convert(105, uint8),
        _agentWrapper,
        _userWallet,
        _confirmAddrs,
        _cancelPendingAddrs,
        _removeAddrs,
        _sig.nonce,
        _sig.expiration
    ))
    self._authenticateAccess(_userWallet, messageHash, _sig)

    # 3. execute confirms, cancels, then removes in signed array order.
    for addr: address in _confirmAddrs:
        assert extcall AgentWrapper(_agentWrapper).confirmWhitelistAddr(_userWallet, addr)

    for addr: address in _cancelPendingAddrs:
        assert extcall AgentWrapper(_agentWrapper).cancelPendingWhitelistAddr(_userWallet, addr)

    for addr: address in _removeAddrs:
        assert extcall AgentWrapper(_agentWrapper).removeWhitelistAddr(_userWallet, addr)


@external
def harvestAndIssueCheque(
    _agentWrapper: address,
    _userWallet: address,
    _rewardLegoId: uint256 = 0,
    _rewardToken: address = empty(address),
    _rewardAmount: uint256 = max_value(uint256),
    _rewardProofs: DynArray[bytes32, MAX_PROOFS] = [],
    _swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS] = [],
    _cheque: ChequeInstruction = empty(ChequeInstruction),
    _sig: Signature = empty(Signature),
):
    """
    Action 106: optionally harvest incentives and swap, then create the signed cheque amount as-is.
    The cheque amount is not capped to harvested or swapped proceeds; the wallet may not have enough
    balance when the cheque is later paid, so the owner/server is responsible for funding. Optional
    swaps consume the wallet's tokenIn balance and are not limited to newly harvested rewards.
    """
    assert _cheque.recipient != empty(address) # dev: empty cheque recipient

    # 1. authenticate access (action code 106)
    messageHash: bytes32 = keccak256(abi_encode(
        convert(106, uint8),
        _agentWrapper,
        _userWallet,
        _rewardLegoId,
        _rewardToken,
        _rewardAmount,
        _rewardProofs,
        _swapInstructions,
        _cheque,
        _sig.nonce,
        _sig.expiration
    ))
    self._authenticateAccess(_userWallet, messageHash, _sig)

    # 2. optional incentives harvest
    if _rewardLegoId != 0 and _rewardToken != empty(address):
        extcall AgentWrapper(_agentWrapper).claimIncentives(
            _userWallet,
            _rewardLegoId,
            _rewardToken,
            _rewardAmount,
            _rewardProofs
        )

    # 3. optional swap
    if len(_swapInstructions) != 0 and len(_swapInstructions[0].tokenPath) != 0:
        swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS] = _swapInstructions
        tokenIn: address = swapInstructions[0].tokenPath[0]
        swapInstructions[0].amountIn = min(swapInstructions[0].amountIn, staticcall IERC20(tokenIn).balanceOf(_userWallet))
        extcall AgentWrapper(_agentWrapper).swapTokens(_userWallet, swapInstructions)

    # 4. create the signed cheque amount without capping it to harvest/swap proceeds.
    assert extcall AgentWrapper(_agentWrapper).createCheque(
        _userWallet,
        _cheque.recipient,
        _cheque.asset,
        _cheque.amount,
        _cheque.unlockNumBlocks,
        _cheque.expiryNumBlocks,
        _cheque.canManagerPay,
        _cheque.canBePulled,
    )


@view
@internal
def _validateWhitelistMaintenance(
    _confirmAddrs: DynArray[address, MAX_WHITELIST_ADDRS],
    _cancelPendingAddrs: DynArray[address, MAX_WHITELIST_ADDRS],
    _removeAddrs: DynArray[address, MAX_WHITELIST_ADDRS],
):
    for i: uint256 in range(MAX_WHITELIST_ADDRS):
        if i >= len(_confirmAddrs):
            break
        addr: address = _confirmAddrs[i]
        assert not self._hasWhitelistAddr(_confirmAddrs, addr, i, True) # dev: duplicate addr
        assert not self._hasWhitelistAddr(_cancelPendingAddrs, addr, 0, False) # dev: duplicate addr
        assert not self._hasWhitelistAddr(_removeAddrs, addr, 0, False) # dev: duplicate addr

    for i: uint256 in range(MAX_WHITELIST_ADDRS):
        if i >= len(_cancelPendingAddrs):
            break
        addr: address = _cancelPendingAddrs[i]
        assert not self._hasWhitelistAddr(_cancelPendingAddrs, addr, i, True) # dev: duplicate addr
        assert not self._hasWhitelistAddr(_removeAddrs, addr, 0, False) # dev: duplicate addr

    for i: uint256 in range(MAX_WHITELIST_ADDRS):
        if i >= len(_removeAddrs):
            break
        addr: address = _removeAddrs[i]
        assert not self._hasWhitelistAddr(_removeAddrs, addr, i, True) # dev: duplicate addr

@view
@internal
def _hasWhitelistAddr(
    _addrs: DynArray[address, MAX_WHITELIST_ADDRS],
    _addr: address,
    _skipIndex: uint256,
    _shouldSkip: bool,
) -> bool:
    for i: uint256 in range(MAX_WHITELIST_ADDRS):
        if i >= len(_addrs):
            break
        if not (_shouldSkip and i == _skipIndex):
            if _addrs[i] == _addr:
                return True
    return False


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
