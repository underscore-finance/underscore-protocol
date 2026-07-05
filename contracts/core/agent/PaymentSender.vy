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
#     ║  ** Payment Sender **                                             ║
#     ║  AgentSender that orchestrates an agent payment via a proxy.      ║
#     ╚═══════════════════════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# The orchestrating AgentSender for agent payments. Like the other senders it is owner-authorized
# (owner = the agent operator, via the Ownership module) and callable by any broadcaster carrying that
# signature. On a valid signature it (optionally withdraws from an earn vault first, then) pushes the
# user's USDC to the service Proxy via AgentWrapper.transferFunds — the proxy is the UserWallet's Payee
# — and calls PaymentProcessor.registerMpp / registerX402, which pulls the funds out of the proxy and
# settles. Must be registered in both the AgentWrapper (addSender) and the PaymentProcessor (setSender).

# @version 0.4.3
# pragma optimize codesize


initializes: ownership
exports: ownership.__interface__

import contracts.modules.Ownership as ownership
from interfaces import AgentWrapperInt

interface Registry:
    def getAddr(_regId: uint256) -> address: view

interface PaymentProcessor:
    def registerMpp(_agentWrapper: address, _proxy: address, _userWallet: address, _amount: uint256, _paymentId: bytes32, _merchantRef: bytes32) -> uint256: nonpayable
    def registerX402(_agentWrapper: address, _proxy: address, _userWallet: address, _amount: uint256, _dest: address, _validAfter: uint256, _validBefore: uint256, _paymentId: bytes32, _merchantRef: bytes32) -> bytes32: nonpayable

PAYMENT_PROCESSOR_ID: constant(uint256) = 13
ECRECOVER_PRECOMPILE: constant(address) = 0x0000000000000000000000000000000000000001
SIG_PREFIX: constant(bytes32) = 0x1901000000000000000000000000000000000000000000000000000000000000

HQ: public(immutable(address))
USDC: public(immutable(address))

struct Signature:
    signature: Bytes[65]
    nonce: uint256
    expiration: uint256

struct VaultSource:                 # optional: withdraw from an earn vault before paying
    legoId: uint256
    vaultToken: address
    vaultTokenAmount: uint256
    extraData: bytes32

currentNonce: public(HashMap[address, uint256])     # per userWallet (replay protection)

event NonceIncremented:
    userWallet: indexed(address)
    newNonce: uint256

event PaymentSent:
    paymentId: indexed(bytes32)
    userWallet: indexed(address)
    proxy: indexed(address)
    amount: uint256
    rail: uint8                                     # 1 = MPP, 2 = x402


@deploy
def __init__(_undyHq: address, _usdc: address, _owner: address, _minTimeLock: uint256, _maxTimeLock: uint256):
    ownership.__init__(_undyHq, _owner, _minTimeLock, _maxTimeLock)
    assert _usdc != empty(address)  # dev: usdc required
    HQ = _undyHq
    USDC = _usdc


###############################################
# actions (owner-authorized, any broadcaster) #
###############################################


@external
def payMpp(
    _agentWrapper: address,
    _userWallet: address,
    _proxy: address,
    _amount: uint256,
    _paymentId: bytes32,
    _merchantRef: bytes32,
    _vault: VaultSource = empty(VaultSource),
    _sig: Signature = empty(Signature),
) -> uint256:
    self._authenticateAccess(
        _userWallet,
        keccak256(abi_encode(convert(1, uint8), _agentWrapper, _userWallet, _proxy, _amount, _paymentId, _merchantRef, _vault, self, USDC, _sig.nonce, _sig.expiration)),
        _sig,
    )
    moved: uint256 = self._sourceAndSend(_agentWrapper, _userWallet, _proxy, _amount, _vault)
    extcall PaymentProcessor(self._processor()).registerMpp(_agentWrapper, _proxy, _userWallet, moved, _paymentId, _merchantRef)
    log PaymentSent(paymentId=_paymentId, userWallet=_userWallet, proxy=_proxy, amount=moved, rail=1)
    return moved


@external
def payX402(
    _agentWrapper: address,
    _userWallet: address,
    _proxy: address,
    _amount: uint256,
    _dest: address,
    _validAfter: uint256,
    _validBefore: uint256,
    _paymentId: bytes32,
    _merchantRef: bytes32,
    _vault: VaultSource = empty(VaultSource),
    _sig: Signature = empty(Signature),
) -> bytes32:
    self._authenticateAccess(
        _userWallet,
        keccak256(abi_encode(convert(2, uint8), _agentWrapper, _userWallet, _proxy, _amount, _dest, _validAfter, _validBefore, _paymentId, _merchantRef, _vault, self, USDC, _sig.nonce, _sig.expiration)),
        _sig,
    )
    moved: uint256 = self._sourceAndSend(_agentWrapper, _userWallet, _proxy, _amount, _vault)
    digest: bytes32 = extcall PaymentProcessor(self._processor()).registerX402(_agentWrapper, _proxy, _userWallet, moved, _dest, _validAfter, _validBefore, _paymentId, _merchantRef)
    log PaymentSent(paymentId=_paymentId, userWallet=_userWallet, proxy=_proxy, amount=moved, rail=2)
    return digest


@view
@internal
def _processor() -> address:
    return staticcall Registry(HQ).getAddr(PAYMENT_PROCESSOR_ID)


@internal
def _sourceAndSend(_agentWrapper: address, _userWallet: address, _proxy: address, _amount: uint256, _vault: VaultSource) -> uint256:
    # if a vault is set, withdraw from yield first (excess stays liquid in the wallet); then move the
    # payment amount to the proxy (the UserWallet's Payee) through the AgentWrapper's rules.
    if _vault.legoId != 0 and _vault.vaultToken != empty(address):
        vt: uint256 = 0
        wasset: address = empty(address)
        wamount: uint256 = 0
        wusd: uint256 = 0
        vt, wasset, wamount, wusd = extcall AgentWrapperInt(_agentWrapper).withdrawFromYield(
            _userWallet, _vault.legoId, _vault.vaultToken, _vault.vaultTokenAmount, _vault.extraData
        )
        assert wasset == USDC  # dev: vault underlying not USDC
    moved: uint256 = 0
    usdValue: uint256 = 0
    moved, usdValue = extcall AgentWrapperInt(_agentWrapper).transferFunds(_userWallet, _proxy, USDC, _amount)
    assert moved >= _amount  # dev: moved less than the payment
    return moved


#######################################################################
# signature verification (byte-for-byte the Underscore sender scheme) #
#######################################################################


@internal
def _authenticateAccess(_userWallet: address, _messageHash: bytes32, _sig: Signature):
    owner: address = ownership.owner
    if msg.sender != owner:
        assert _sig.expiration >= block.timestamp  # dev: signature expired
        assert _sig.nonce == self.currentNonce[_userWallet]  # dev: invalid nonce
        recovered: address = self._verify(_messageHash, _sig)
        assert recovered == owner  # dev: invalid signer
        self.currentNonce[_userWallet] = _sig.nonce + 1
        log NonceIncremented(userWallet=_userWallet, newNonce=_sig.nonce + 1)
    else:
        assert _sig.signature == empty(Bytes[65])  # dev: must be empty
        assert _sig.nonce == 0  # dev: must be 0
        assert _sig.expiration == 0  # dev: must be 0


@view
@internal
def _verify(_messageHash: bytes32, _sig: Signature) -> address:
    r: bytes32 = convert(slice(_sig.signature, 0, 32), bytes32)
    s: bytes32 = convert(slice(_sig.signature, 32, 32), bytes32)
    v: uint8 = convert(slice(_sig.signature, 64, 1), uint8)
    if v < 27:
        v = v + 27
    assert v == 27 or v == 28  # dev: invalid v
    s_uint: uint256 = convert(s, uint256)
    assert s_uint != 0  # dev: invalid s (zero)
    assert s_uint <= convert(0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0, uint256)  # dev: invalid s
    digest: bytes32 = keccak256(concat(SIG_PREFIX, self._domainSeparator(), _messageHash))
    result: Bytes[32] = raw_call(ECRECOVER_PRECOMPILE, abi_encode(digest, v, r, s), max_outsize=32, is_static_call=True)
    if len(result) != 32:
        return empty(address)
    recovered: address = abi_decode(result, address)
    assert recovered != empty(address)  # dev: recovery failed
    return recovered


@view
@internal
def _domainSeparator() -> bytes32:
    return keccak256(abi_encode(
        keccak256('EIP712Domain(string name,uint256 chainId,address verifyingContract)'),
        keccak256('UnderscoreAgent'),
        chain.id,
        self,
    ))


@view
@external
def getPayMppHash(_agentWrapper: address, _userWallet: address, _proxy: address, _amount: uint256, _paymentId: bytes32, _merchantRef: bytes32, _vault: VaultSource, _expiration: uint256) -> (bytes32, uint256, uint256):
    nonce: uint256 = self.currentNonce[_userWallet]
    msgHash: bytes32 = keccak256(abi_encode(convert(1, uint8), _agentWrapper, _userWallet, _proxy, _amount, _paymentId, _merchantRef, _vault, self, USDC, nonce, _expiration))
    return (keccak256(concat(SIG_PREFIX, self._domainSeparator(), msgHash)), nonce, _expiration)


@view
@external
def getPayX402Hash(_agentWrapper: address, _userWallet: address, _proxy: address, _amount: uint256, _dest: address, _validAfter: uint256, _validBefore: uint256, _paymentId: bytes32, _merchantRef: bytes32, _vault: VaultSource, _expiration: uint256) -> (bytes32, uint256, uint256):
    nonce: uint256 = self.currentNonce[_userWallet]
    msgHash: bytes32 = keccak256(abi_encode(convert(2, uint8), _agentWrapper, _userWallet, _proxy, _amount, _dest, _validAfter, _validBefore, _paymentId, _merchantRef, _vault, self, USDC, nonce, _expiration))
    return (keccak256(concat(SIG_PREFIX, self._domainSeparator(), msgHash)), nonce, _expiration)
