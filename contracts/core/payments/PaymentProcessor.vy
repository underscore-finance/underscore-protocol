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
#     ║  ** Payment Processor **                                          ║
#     ║  UndyHq dept: the x402 hub + MPP hub (settlement engine).         ║
#     ╚═══════════════════════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# The money engine for agent payments. A registered PaymentSender pushes a user's USDC into a service
# Proxy, then calls registerMpp/registerX402 here; the processor pulls the USDC out of the proxy and
# settles:
#   • MPP  — escrows the payment, emits OperationRegistered (which gates the omnibus Tempo settle), and
#            later bridge()s pooled USDC to the configured Base→Tempo route; refund() returns to the payer.
#   • x402 — binds the USDC EIP-3009 authorization for a destination the proxy's own allow-list marks
#            live (only while the proxy is enabled in ProxyStore); the processor is the EIP-1271 payer
#            (isValidSignature -> MAGIC), so the
#            seller's facilitator settles transferWithAuthorization(from=processor, to=dest).
# Only Switchboard-registered senders may register ops; bridge()/refund()/revoke are relayer-gated.

# @version 0.4.3
# pragma optimize codesize

implements: Department

exports: addys.__interface__
exports: deptBasics.__interface__

initializes: addys
initializes: deptBasics[addys := addys]

import contracts.modules.Addys as addys
import contracts.modules.DeptBasics as deptBasics
from interfaces import Department
from ethereum.ercs import IERC20

interface Registry:
    def getAddr(_regId: uint256) -> address: view

interface ProxyStore:
    def isProxyEnabled(_proxy: address) -> bool: view

interface Proxy:
    def transferToProcessor(_asset: address, _amount: uint256) -> uint256: nonpayable
    def isAllowed(_dest: address) -> bool: view

interface UsdcAuth:
    def authorizationState(_authorizer: address, _nonce: bytes32) -> bool: view

interface BridgeAdapter:
    def bridge(_token: address, _amount: uint256, _recipient: address, _destChainId: uint256): nonpayable

PROXY_STORE_ID: constant(uint256) = 12
HQ: public(immutable(address))
USDC: public(immutable(address))

# EIP-1271 / EIP-3009 (USDC "USD Coin" v2 domain) — the x402 `exact` scheme
MAGIC: constant(bytes4) = 0x1626ba7e
FAIL: constant(bytes4) = 0xffffffff
_DOMAIN_TYPEHASH: constant(bytes32) = keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)")
_TWA_TYPEHASH: constant(bytes32) = keccak256("TransferWithAuthorization(address from,address to,uint256 value,uint256 validAfter,uint256 validBefore,bytes32 nonce)")
_NAME_HASH: constant(bytes32) = keccak256("USD Coin")
_VERSION_HASH: constant(bytes32) = keccak256("2")
_EIP712_PREFIX: constant(bytes2) = 0x1901

struct Operation:
    payer: address          # the UserWallet (refund destination — locked)
    proxy: address          # the service proxy this payment went through
    agentWrapper: address   # the AgentWrapper that initiated it (audit/query only — never an authz input)
    amount: uint256
    refunded: uint256
    merchantRef: bytes32
    exists: bool

senders: public(HashMap[address, bool])             # PaymentSenders that may register ops (switchboard-set)
relayers: public(HashMap[address, bool])            # may bridge() / refund() / revoke (switchboard-set)
bridgeAdapter: public(address)                      # bridge adapter that moves USDC Base→Tempo (switchboard-set)
tempoRecipient: public(address)                     # the registered Tempo wallet — protected; the server cannot set it
destChainId: public(uint256)                        # destination chain id (Tempo mainnet = 4217)
operations: public(HashMap[bytes32, Operation])     # paymentId => Operation
opDigest: public(HashMap[bytes32, bytes32])         # paymentId => bound x402 digest (0 for MPP)
pendingTotal: public(uint256)                      # MPP escrow not yet bridged / refunded
authorized: public(HashMap[bytes32, bool])          # x402 EIP-3009 digests this processor will honor

event OperationRegistered:
    paymentId: indexed(bytes32)
    payer: indexed(address)
    proxy: indexed(address)
    agentWrapper: address                           # initiating wrapper (data field — 3 indexed topics already used)
    amount: uint256
    merchantRef: bytes32
    rail: uint8                                     # 1 = MPP, 2 = x402

event X402Authorized:
    paymentId: indexed(bytes32)
    dest: indexed(address)
    digest: bytes32

event X402Revoked:
    paymentId: indexed(bytes32)
    digest: bytes32

event Bridged:
    recipient: indexed(address)
    amount: uint256

event Refunded:
    paymentId: indexed(bytes32)
    payer: indexed(address)
    amount: uint256

event RoleSet:
    what: indexed(bytes32)
    account: indexed(address)
    allowed: bool

event BridgeSet:
    adapter: indexed(address)
    recipient: indexed(address)
    destChainId: uint256


@deploy
def __init__(_undyHq: address, _usdc: address):
    addys.__init__(_undyHq)
    deptBasics.__init__(False, False)  # not paused; cannot mint UNDY
    assert _usdc != empty(address)  # dev: usdc required
    HQ = _undyHq
    USDC = _usdc


@view
@internal
def _proxyStore() -> address:
    return staticcall Registry(HQ).getAddr(PROXY_STORE_ID)


@internal
def _pull(_proxy: address, _amount: uint256) -> uint256:
    # the sender has already moved the user's USDC into the proxy; pull it into the processor
    store: address = self._proxyStore()
    assert staticcall ProxyStore(store).isProxyEnabled(_proxy)  # dev: proxy not enabled
    pulled: uint256 = extcall Proxy(_proxy).transferToProcessor(USDC, _amount)
    assert pulled >= _amount  # dev: proxy underfunded
    return pulled


########################################
# register (called by a PaymentSender) #
########################################


@external
def registerMpp(_agentWrapper: address, _proxy: address, _userWallet: address, _amount: uint256, _paymentId: bytes32, _merchantRef: bytes32) -> uint256:
    assert not deptBasics.isPaused  # dev: paused
    assert self.senders[msg.sender]  # dev: not a sender
    assert _agentWrapper != empty(address)  # dev: no agent wrapper
    assert _amount > 0  # dev: zero amount
    assert not self.operations[_paymentId].exists  # dev: paymentId reused
    self._pull(_proxy, _amount)
    self.operations[_paymentId] = Operation(payer=_userWallet, proxy=_proxy, agentWrapper=_agentWrapper, amount=_amount, refunded=0, merchantRef=_merchantRef, exists=True)
    self.pendingTotal += _amount
    log OperationRegistered(paymentId=_paymentId, payer=_userWallet, proxy=_proxy, agentWrapper=_agentWrapper, amount=_amount, merchantRef=_merchantRef, rail=1)
    return _amount


@external
def registerX402(_agentWrapper: address, _proxy: address, _userWallet: address, _amount: uint256, _dest: address, _validAfter: uint256, _validBefore: uint256, _paymentId: bytes32, _merchantRef: bytes32) -> bytes32:
    assert not deptBasics.isPaused  # dev: paused
    assert self.senders[msg.sender]  # dev: not a sender
    assert _agentWrapper != empty(address)  # dev: no agent wrapper
    assert _amount > 0  # dev: zero amount
    assert not self.operations[_paymentId].exists  # dev: paymentId reused
    store: address = self._proxyStore()
    assert staticcall ProxyStore(store).isProxyEnabled(_proxy)  # dev: proxy not enabled
    assert staticcall Proxy(_proxy).isAllowed(_dest)  # dev: dest not allowed
    pulled: uint256 = extcall Proxy(_proxy).transferToProcessor(USDC, _amount)
    assert pulled >= _amount  # dev: proxy underfunded
    # EIP-3009 nonce is derived from the paymentId — one paymentId => one nonce => one USDC pull
    digest: bytes32 = self._x402Digest(_dest, _amount, _validAfter, _validBefore, keccak256(_paymentId))
    self.authorized[digest] = True
    self.operations[_paymentId] = Operation(payer=_userWallet, proxy=_proxy, agentWrapper=_agentWrapper, amount=_amount, refunded=0, merchantRef=_merchantRef, exists=True)
    self.opDigest[_paymentId] = digest
    log OperationRegistered(paymentId=_paymentId, payer=_userWallet, proxy=_proxy, agentWrapper=_agentWrapper, amount=_amount, merchantRef=_merchantRef, rail=2)
    log X402Authorized(paymentId=_paymentId, dest=_dest, digest=digest)
    return digest


#######################
# x402 EIP-1271 payer #
#######################


@view
@internal
def _domainSeparator() -> bytes32:
    return keccak256(abi_encode(_DOMAIN_TYPEHASH, _NAME_HASH, _VERSION_HASH, chain.id, USDC))


@view
@internal
def _x402Digest(_to: address, _value: uint256, _validAfter: uint256, _validBefore: uint256, _nonce: bytes32) -> bytes32:
    structHash: bytes32 = keccak256(abi_encode(_TWA_TYPEHASH, self, _to, _value, _validAfter, _validBefore, _nonce))
    return keccak256(concat(_EIP712_PREFIX, self._domainSeparator(), structHash))


@view
@external
def x402Nonce(_paymentId: bytes32) -> bytes32:
    # the EIP-3009 nonce the facilitator must submit for this payment
    return keccak256(_paymentId)


@view
@external
def getX402Digest(_to: address, _value: uint256, _validAfter: uint256, _validBefore: uint256, _paymentId: bytes32) -> bytes32:
    return self._x402Digest(_to, _value, _validAfter, _validBefore, keccak256(_paymentId))


@view
@external
def isValidSignature(_hash: bytes32, _signature: Bytes[256]) -> bytes4:
    # USDC (via SignatureChecker) and the facilitator call this with the EIP-3009 digest. We return
    # MAGIC only for a digest a registered sender authorized; `_signature` is ignored (the funded,
    # dest-gated registration IS the authorization). USDC's per-`from` nonce blocks replay/double-spend.
    if self.authorized[_hash]:
        return MAGIC
    return FAIL


@external
def revokeX402(_paymentId: bytes32):
    # Relayer un-binds an x402 authorization that hasn't settled (e.g. the invoice failed) so USDC can
    # no longer be pulled; funds still held can then be refund()ed to the payer.
    assert self.relayers[msg.sender]  # dev: not a relayer
    digest: bytes32 = self.opDigest[_paymentId]
    assert digest != empty(bytes32)  # dev: no x402 op
    self.authorized[digest] = False
    self.opDigest[_paymentId] = empty(bytes32)
    log X402Revoked(paymentId=_paymentId, digest=digest)


######################################################
# bridge (MPP) + refund (both rails) — relayer-gated #
######################################################


@external
def bridge(_amount: uint256):
    # A relayer (the server) triggers the bridge and chooses the amount — but NOT the destination: the
    # adapter + Tempo recipient are switchboard-set config, so the server can never redirect the funds.
    assert not deptBasics.isPaused  # dev: paused
    assert self.relayers[msg.sender]  # dev: not a relayer
    adapter: address = self.bridgeAdapter
    recipient: address = self.tempoRecipient
    assert adapter != empty(address) and recipient != empty(address)  # dev: bridge not configured
    assert _amount > 0 and _amount <= self.pendingTotal  # dev: amount over escrow
    self.pendingTotal -= _amount
    assert extcall IERC20(USDC).approve(adapter, _amount, default_return_value=True)  # dev: approve failed
    extcall BridgeAdapter(adapter).bridge(USDC, _amount, recipient, self.destChainId)
    assert extcall IERC20(USDC).approve(adapter, 0, default_return_value=True)  # dev: reset failed
    log Bridged(recipient=recipient, amount=_amount)


@external
def refund(_paymentId: bytes32, _amount: uint256):
    assert not deptBasics.isPaused  # dev: paused
    assert self.relayers[msg.sender]  # dev: not a relayer
    op: Operation = self.operations[_paymentId]
    assert op.exists  # dev: unknown paymentId
    assert _amount > 0 and _amount <= op.amount - op.refunded  # dev: over refundable
    digest: bytes32 = self.opDigest[_paymentId]
    if digest != empty(bytes32):
        # x402: never refund an op the merchant already pulled; else revoke so it can't be pulled after
        assert not (staticcall UsdcAuth(USDC).authorizationState(self, keccak256(_paymentId)))  # dev: already settled
        self.authorized[digest] = False
        self.opDigest[_paymentId] = empty(bytes32)
    else:
        # MPP: release the escrow that backs the bridge
        if self.pendingTotal >= _amount:
            self.pendingTotal -= _amount
        else:
            self.pendingTotal = 0
    assert staticcall IERC20(USDC).balanceOf(self) >= _amount  # dev: not funded
    self.operations[_paymentId].refunded = op.refunded + _amount
    assert extcall IERC20(USDC).transfer(op.payer, _amount, default_return_value=True)  # dev: refund failed
    log Refunded(paymentId=_paymentId, payer=op.payer, amount=_amount)


#############################
# admin (Switchboard-gated) #
#############################


# Sender allow-list — deliberate authorization model.
#
# A PaymentSender must be registered on BOTH sides, each switchboard-gated, and both are needed:
#   • setSender (here)        -> it may call registerMpp / registerX402 on this processor
#   • AgentWrapper.addSender  -> it may move that user's USDC through the user's wrapper
#
# We keep this explicit list on purpose, rather than deriving authorization from the user's
# AgentWrapper at settle time (e.g. staticcall-ing the wrapper's isSender, or an active-manager
# check on the wallet): that would pull extra cross-contract trust and call surface into the
# settlement path. Two independent switchboard allow-lists are simpler to audit, and the
# switchboard stays the single trust root on each side.
#
# Authorization never depends on the AgentWrapper: the wrapper is carried into register* and
# recorded (stored on the Operation + emitted) only so the initiating agent is queryable and
# auditable. The sole gate is self.senders[msg.sender].
@external
def setSender(_account: address, _allowed: bool):
    assert addys._isSwitchboardAddr(msg.sender)  # dev: no perms
    self.senders[_account] = _allowed
    log RoleSet(what=convert(b"sender", bytes32), account=_account, allowed=_allowed)


@external
def setRelayer(_account: address, _allowed: bool):
    assert addys._isSwitchboardAddr(msg.sender)  # dev: no perms
    self.relayers[_account] = _allowed
    log RoleSet(what=convert(b"relayer", bytes32), account=_account, allowed=_allowed)


@external
def setBridge(_adapter: address, _recipient: address, _destChainId: uint256):
    # only the Switchboard defines where bridged funds land on Tempo (the recipient) + the adapter/route
    assert addys._isSwitchboardAddr(msg.sender)  # dev: no perms
    self.bridgeAdapter = _adapter
    self.tempoRecipient = _recipient
    self.destChainId = _destChainId
    log BridgeSet(adapter=_adapter, recipient=_recipient, destChainId=_destChainId)
