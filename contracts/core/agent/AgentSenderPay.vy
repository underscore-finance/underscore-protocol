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
#     ║  ** Agent Sender Pay **                                           ║
#     ║  AgentSender that orchestrates an agent payment via a vendor.     ║
#     ╚═══════════════════════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# The orchestrating AgentSender for agent payments. Like the other senders it is owner-authorized
# (owner = the agent operator, via the Ownership module) and callable by any broadcaster carrying that
# signature. On a valid signature it (optionally withdraws from an earn vault first, then) pushes the
# user's USDC to the service VendorProxy — either a direct Payee transfer or, for a one-off / non-payee, a
# create-and-pay cheque — and calls PayProcessor.register (routed by protocolId), which pulls the
# funds out of the vendor and settles. Must be registered in both the AgentWrapper (addSender) and the
# PayProcessor (setSender).

# @version 0.4.3
# pragma optimize codesize


initializes: ownership
exports: ownership.__interface__

import contracts.modules.Ownership as ownership
from interfaces import AgentWrapperInt

interface Registry:
    def getAddr(_regId: uint256) -> address: view

interface PayProcessor:
    def register(_protocolId: uint8, _agentWrapper: address, _vendor: address, _userWallet: address, _amount: uint256, _dest: address, _paymentId: bytes32, _merchantRef: bytes32, _extraData: Bytes[256]) -> bytes32: nonpayable

PAY_PROCESSOR_ID: constant(uint256) = 13
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
    vendor: indexed(address)
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
def pay(
    _protocolId: uint8,
    _agentWrapper: address,
    _userWallet: address,
    _vendor: address,
    _amount: uint256,
    _dest: address,
    _paymentId: bytes32,
    _merchantRef: bytes32,
    _isCheque: bool = False,
    _extraData: Bytes[256] = b"",
    _vault: VaultSource = empty(VaultSource),
    _sig: Signature = empty(Signature),
) -> bytes32:
    # One entry point for every rail. `_protocolId` (1 = MPP, 2 = x402) selects the processor route;
    # `_isCheque` selects how funds are sourced into the vendor (createAndPayCheque for a one-off /
    # non-payee, else a direct Payee transfer); `_extraData` carries protocol-specific inputs
    # (x402: abi_encode(validAfter, validBefore)). Returns the processor result (x402 digest; MPP empty).
    self._authenticateAccess(
        _userWallet,
        keccak256(abi_encode(_protocolId, _agentWrapper, _userWallet, _vendor, _amount, _dest, _paymentId, _merchantRef, _isCheque, _extraData, _vault, self, USDC, _sig.nonce, _sig.expiration)),
        _sig,
    )
    moved: uint256 = self._sourceAndSend(_agentWrapper, _userWallet, _vendor, _amount, _isCheque, _vault)
    result: bytes32 = extcall PayProcessor(self._processor()).register(_protocolId, _agentWrapper, _vendor, _userWallet, moved, _dest, _paymentId, _merchantRef, _extraData)
    log PaymentSent(paymentId=_paymentId, userWallet=_userWallet, vendor=_vendor, amount=moved, rail=_protocolId)
    return result


@external
def incrementNonce(_userWallet: address):
    # owner-only escape hatch: bump the nonce to invalidate any outstanding (leaked / stale) payment
    # signature for this userWallet. Mirrors AgentSenderGeneric / AgentSenderSpecial.
    assert msg.sender == ownership.owner  # dev: no perms
    newNonce: uint256 = self.currentNonce[_userWallet] + 1
    self.currentNonce[_userWallet] = newNonce
    log NonceIncremented(userWallet=_userWallet, newNonce=newNonce)


@view
@internal
def _processor() -> address:
    return staticcall Registry(HQ).getAddr(PAY_PROCESSOR_ID)


@internal
def _sourceAndSend(_agentWrapper: address, _userWallet: address, _vendor: address, _amount: uint256, _isCheque: bool, _vault: VaultSource) -> uint256:
    # if a vault is set, withdraw from yield first (excess stays liquid in the wallet); then move the
    # payment amount to the vendor (the UserWallet's Payee) through the AgentWrapper's rules.
    # reject a partial VaultSource (one of legoId / vaultToken set without the other) so a malformed
    # config can neither silently skip a signed withdrawal nor slip an unsigned one through.
    assert (_vault.legoId != 0) == (_vault.vaultToken != empty(address))  # dev: partial vault config
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
    if _isCheque:
        # one-off / non-payee vendor: create + pay a cheque so the debit is authorized on the wallet
        moved, usdValue = extcall AgentWrapperInt(_agentWrapper).createAndPayCheque(_userWallet, _vendor, USDC, _amount)
    else:
        # vendor is an approved Payee on the wallet: direct transfer
        moved, usdValue = extcall AgentWrapperInt(_agentWrapper).transferFunds(_userWallet, _vendor, USDC, _amount)
    assert moved == _amount  # dev: moved must equal the signed amount
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
def getPayHash(_protocolId: uint8, _agentWrapper: address, _userWallet: address, _vendor: address, _amount: uint256, _dest: address, _paymentId: bytes32, _merchantRef: bytes32, _isCheque: bool, _extraData: Bytes[256], _expiration: uint256, _vault: VaultSource = empty(VaultSource)) -> (bytes32, uint256, uint256):
    nonce: uint256 = self.currentNonce[_userWallet]
    msgHash: bytes32 = keccak256(abi_encode(_protocolId, _agentWrapper, _userWallet, _vendor, _amount, _dest, _paymentId, _merchantRef, _isCheque, _extraData, _vault, self, USDC, nonce, _expiration))
    return (keccak256(concat(SIG_PREFIX, self._domainSeparator(), msgHash)), nonce, _expiration)
