#     /$$$$$$$                     /$$$$$$$                                                                               
#     | $$__  $$                   | $$__  $$                                                                              
#     | $$  \ $$ /$$$$$$  /$$   /$$| $$  \ $$ /$$$$$$   /$$$$$$   /$$$$$$$  /$$$$$$   /$$$$$$$ /$$$$$$$  /$$$$$$   /$$$$$$ 
#     | $$$$$$$/|____  $$| $$  | $$| $$$$$$$//$$__  $$ /$$__  $$ /$$_____/ /$$__  $$ /$$_____//$$_____/ /$$__  $$ /$$__  $$
#     | $$____/  /$$$$$$$| $$  | $$| $$____/| $$  \__/| $$  \ $$| $$      | $$$$$$$$|  $$$$$$|  $$$$$$ | $$  \ $$| $$  \__/
#     | $$      /$$__  $$| $$  | $$| $$     | $$      | $$  | $$| $$      | $$_____/ \____  $$\____  $$| $$  | $$| $$      
#     | $$     |  $$$$$$$|  $$$$$$$| $$     | $$      |  $$$$$$/|  $$$$$$$|  $$$$$$$ /$$$$$$$//$$$$$$$/|  $$$$$$/| $$      
#     |__/      \_______/ \____  $$|__/     |__/       \______/  \_______/ \_______/|_______/|_______/  \______/ |__/      
#                         /$$  | $$                                                                                        
#                        |  $$$$$$/                                                                                        
#                         \______/                                                                                           
#
#     ╔═══════════════════════════════════════════════════════════════════╗
#     ║  ** Pay Processor **                                              ║
#     ║  UndyHq dept: the x402 hub + MPP hub (settlement engine).         ║
#     ╚═══════════════════════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# The money engine for agent payments. A registered AgentSenderPay pushes a user's USDC into a service
# VendorProxy, then calls register(protocolId) here; the processor pulls the USDC out of the vendor and
# settles:
#   • MPP  — escrows the payment, emits OperationRegistered (which gates the omnibus Tempo settle); then
#            settle() marks each op non-refundable and moves its balance into availToBridge, and bridge()
#            later batches availToBridge to the configured Bridge liquidation address (which off-ramps to
#            Tempo). refund() returns an unsettled op to the payer.
#   • x402 — binds the USDC EIP-3009 authorization for a destination the vendor's own allow-list marks
#            live (only while the vendor is registered in VendorRegistry); the processor is the EIP-1271 payer
#            (isValidSignature -> MAGIC), so the
#            seller's facilitator settles transferWithAuthorization(from=processor, to=dest).
# Only Switchboard-registered senders may register ops; settle()/bridge()/refund() are switchboard-gated.

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

interface VendorRegistry:
    def indexOfVendor(_vendor: address) -> uint256: view

interface VendorProxy:
    def transferToProcessor(_asset: address, _amount: uint256) -> uint256: nonpayable
    def isAllowed(_dest: address) -> bool: view

interface UsdcAuth:
    def authorizationState(_authorizer: address, _nonce: bytes32) -> bool: view
    def DOMAIN_SEPARATOR() -> bytes32: view

VENDOR_REGISTRY_ID: constant(uint256) = 12
RAIL_MPP: constant(uint8) = 1                       # protocolId: Machine Payments Protocol (Tempo)
RAIL_X402: constant(uint8) = 2                      # protocolId: x402 exact scheme
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
    vendor: address          # the service vendor this payment went through
    agentWrapper: address   # the AgentWrapper that initiated it (audit/query only — never an authz input)
    amount: uint256
    refunded: uint256
    merchantRef: bytes32
    exists: bool
    settled: bool           # MPP: finalized (sent to the bridge) — no longer refundable
    protocolId: uint8       # immutable rail discriminant (RAIL_MPP / RAIL_X402), set at register — never inferred from the mutable opDigest
    dest: address           # payment destination (x402: the bound payee; MPP: recorded for audit + future settlement confirmation)

senders: public(HashMap[address, bool])             # AgentSenderPays that may register ops (switchboard-set)
bridgeAddress: public(address)                      # Bridge (company) liquidation address — a plain USDC send off-ramps to Tempo (switchboard-set; the server cannot redirect)
operations: public(HashMap[bytes32, Operation])     # paymentId => Operation
opDigest: public(HashMap[bytes32, bytes32])         # paymentId => bound x402 digest (0 for MPP)
pendingTotal: public(uint256)                      # MPP escrow not yet settled / refunded (refundable)
availToBridge: public(uint256)                      # MPP settled, awaiting a bridge() batch (non-refundable)
authorized: public(HashMap[bytes32, bool])          # x402 EIP-3009 digests this processor will honor

event OperationRegistered:
    paymentId: indexed(bytes32)
    payer: indexed(address)
    vendor: indexed(address)
    agentWrapper: address                           # initiating wrapper (data field — 3 indexed topics already used)
    amount: uint256
    merchantRef: bytes32
    rail: uint8                                     # 1 = MPP, 2 = x402

event X402Authorized:
    paymentId: indexed(bytes32)
    dest: indexed(address)
    digest: bytes32

event Settled:
    paymentId: indexed(bytes32)
    amount: uint256

event Bridged:
    recipient: indexed(address)
    amount: uint256

event Refunded:
    paymentId: indexed(bytes32)
    payer: indexed(address)
    amount: uint256

event SenderSet:
    account: indexed(address)
    allowed: bool

event BridgeSet:
    bridgeAddress: indexed(address)


@deploy
def __init__(_undyHq: address, _usdc: address):
    addys.__init__(_undyHq)
    deptBasics.__init__(False, False)  # not paused; cannot mint UNDY
    assert _usdc != empty(address)  # dev: usdc required
    HQ = _undyHq
    USDC = _usdc
    # Bind to the exact USDC EIP-712 domain at deploy. A wrong token (e.g. bridged USDbC, whose
    # name() is "USD Base Coin") would leave x402 silently un-settleable — the processor would authorize
    # digests no facilitator can ever satisfy. Fail the deploy loudly instead of shipping a dead rail.
    assert staticcall UsdcAuth(_usdc).DOMAIN_SEPARATOR() == self._domainSeparator()  # dev: usdc domain mismatch


@view
@internal
def _vendorRegistry() -> address:
    return staticcall Registry(HQ).getAddr(VENDOR_REGISTRY_ID)


##########################################
# register (called by an AgentSenderPay) #
##########################################


@external
def register(_protocolId: uint8, _agentWrapper: address, _vendor: address, _userWallet: address, _amount: uint256, _dest: address, _paymentId: bytes32, _merchantRef: bytes32, _extraData: Bytes[256] = b"") -> bytes32:
    # Single entry point for every payment rail. The validation + vendor/dest gate + pull + Operation
    # record are common to all rails; `_protocolId` routes only the tail (MPP escrow vs x402 digest
    # binding). Protocol-specific inputs ride in `_extraData` (x402: abi_encode(validAfter, validBefore);
    # MPP: empty), so adding a rail is one more branch here — no change to AgentSenderPay or this
    # signature. Always returns bytes32: the bound EIP-3009 digest for x402, empty for MPP.
    assert not deptBasics.isPaused  # dev: paused
    assert self.senders[msg.sender]  # dev: not a sender
    assert _agentWrapper != empty(address)  # dev: no agent wrapper
    assert _amount != 0  # dev: zero amount
    assert not self.operations[_paymentId].exists  # dev: paymentId reused

    # common: vendor must be registered + dest allow-listed, then pull the pushed USDC out of the vendor
    registry: address = self._vendorRegistry()
    assert staticcall VendorRegistry(registry).indexOfVendor(_vendor) != 0  # dev: not a vendor
    assert staticcall VendorProxy(_vendor).isAllowed(_dest)  # dev: dest not allowed
    pulled: uint256 = extcall VendorProxy(_vendor).transferToProcessor(USDC, _amount)
    assert pulled >= _amount  # dev: vendor underfunded

    # common: record the operation
    self.operations[_paymentId] = Operation(payer=_userWallet, vendor=_vendor, agentWrapper=_agentWrapper, amount=_amount, refunded=0, merchantRef=_merchantRef, exists=True, settled=False, protocolId=_protocolId, dest=_dest)
    log OperationRegistered(paymentId=_paymentId, payer=_userWallet, vendor=_vendor, agentWrapper=_agentWrapper, amount=_amount, merchantRef=_merchantRef, rail=_protocolId)

    # route by protocol
    if _protocolId == RAIL_MPP:
        self.pendingTotal += _amount
        return empty(bytes32)

    elif _protocolId == RAIL_X402:
        validAfter: uint256 = 0
        validBefore: uint256 = 0
        validAfter, validBefore = abi_decode(_extraData, (uint256, uint256))
        assert validAfter < validBefore  # dev: bad x402 window
        # EIP-3009 nonce is derived from the paymentId — one paymentId => one nonce => one USDC pull
        digest: bytes32 = self._x402Digest(_dest, _amount, validAfter, validBefore, keccak256(_paymentId))
        self.authorized[digest] = True
        self.opDigest[_paymentId] = digest
        log X402Authorized(paymentId=_paymentId, dest=_dest, digest=digest)
        return digest

    raise "bad protocol"


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


######################################################
# settle / bridge (MPP) + refund — switchboard-gated #
######################################################


@external
def settle(_paymentId: bytes32):
    # Finalize one MPP op: mark it non-refundable and move its balance from the refundable escrow into
    # availToBridge (no transfer — the USDC stays here until bridge() sends a batch). The Switchboard
    # triggers it one payment at a time. x402 ops settle via the facilitator's EIP-3009 pull, not here.
    assert not deptBasics.isPaused  # dev: paused
    assert addys._isSwitchboardAddr(msg.sender)  # dev: not switchboard
    op: Operation = self.operations[_paymentId]
    assert op.exists  # dev: unknown paymentId
    assert op.protocolId == RAIL_MPP  # dev: not mpp op
    assert not op.settled  # dev: already settled
    amount: uint256 = op.amount - op.refunded
    assert amount != 0  # dev: nothing to settle
    self.operations[_paymentId].settled = True
    self.pendingTotal -= amount
    self.availToBridge += amount
    log Settled(paymentId=_paymentId, amount=amount)


@external
def bridge(_amount: uint256):
    # The Switchboard batches settled funds to the Bridge liquidation address (also switchboard-set).
    # Draws only from availToBridge (settled, non-refundable); Bridge off-ramps the pooled USDC to Tempo.
    # Batched off-chain so each transfer clears the Bridge company's per-transfer minimum.
    assert not deptBasics.isPaused  # dev: paused
    assert addys._isSwitchboardAddr(msg.sender)  # dev: not switchboard
    bridgeAddress: address = self.bridgeAddress
    assert bridgeAddress != empty(address)  # dev: bridge not configured
    assert _amount != 0 and _amount <= self.availToBridge  # dev: amount over avail
    self.availToBridge -= _amount
    assert extcall IERC20(USDC).transfer(bridgeAddress, _amount, default_return_value=True)  # dev: bridge send failed
    log Bridged(recipient=bridgeAddress, amount=_amount)


@external
def refund(_paymentId: bytes32, _amount: uint256):
    assert not deptBasics.isPaused  # dev: paused
    assert addys._isSwitchboardAddr(msg.sender)  # dev: not switchboard
    op: Operation = self.operations[_paymentId]
    assert op.exists  # dev: unknown paymentId
    assert _amount != 0 and _amount <= op.amount - op.refunded  # dev: over refundable
    if op.protocolId == RAIL_X402:
        # x402 is all-or-nothing (the facilitator pulls the full value or nothing), so a refund must
        # clear the whole op — a partial would leave a half-bound op that later masquerades as MPP.
        # Rail is read from the immutable op flag, never from opDigest (which this branch mutates).
        assert _amount == op.amount - op.refunded  # dev: x402 partial refund
        # never refund an op the merchant already pulled; else un-bind so it can't be pulled after
        assert not (staticcall UsdcAuth(USDC).authorizationState(self, keccak256(_paymentId)))  # dev: already settled
        self.authorized[self.opDigest[_paymentId]] = False
        self.opDigest[_paymentId] = empty(bytes32)
    else:
        # MPP: release the escrow — but only if it hasn't been settled (sent to the bridge)
        assert not op.settled  # dev: already settled
        self.pendingTotal -= _amount
    assert staticcall IERC20(USDC).balanceOf(self) >= _amount  # dev: not funded
    self.operations[_paymentId].refunded = op.refunded + _amount
    assert extcall IERC20(USDC).transfer(op.payer, _amount, default_return_value=True)  # dev: refund failed
    log Refunded(paymentId=_paymentId, payer=op.payer, amount=_amount)


#############################
# admin (Switchboard-gated) #
#############################


# Sender allow-list — deliberate authorization model.
#
# A AgentSenderPay must be registered on BOTH sides, each switchboard-gated, and both are needed:
#   • setSender (here)        -> it may call register on this processor
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
    log SenderSet(account=_account, allowed=_allowed)


@external
def setBridge(_bridgeAddress: address):
    # only the Switchboard defines where bridged funds land — the Bridge (company) liquidation address
    assert addys._isSwitchboardAddr(msg.sender)  # dev: no perms
    self.bridgeAddress = _bridgeAddress
    log BridgeSet(bridgeAddress=_bridgeAddress)
