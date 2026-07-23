# @version 0.4.3

from contracts.walletsV3.types import WalletV3Types as w3
from contracts.walletsV3.interfaces import IOperatorProtocolV3
from contracts.walletsV3.interfaces import IX402Helper


OWNER: immutable(address)

config: public(address)
reserved: public(HashMap[address, uint256])

_attachments: HashMap[uint256, w3.AttachmentView]
_routes: HashMap[uint256, HashMap[bytes4, w3.RouteView]]
_routeSelectors: HashMap[uint256, HashMap[uint256, bytes4]]
_currentRouteIds: HashMap[bytes4, uint256]
_currentFamilyAttachment: HashMap[bytes32, uint256]
attachmentCount: uint256
sessionNonce: uint256
_commitments: HashMap[bytes32, w3.CommitmentView]
_digestCommitmentId: HashMap[bytes32, bytes32]
_usedCommitmentId: HashMap[bytes32, bool]
_usedExternalDigest: HashMap[bytes32, bool]
_usedExternalNonce: HashMap[bytes32, bool]

_phase: transient(uint8)
_frameCaller: transient(address)
_frameConfig: transient(address)
_frameAttachmentId: transient(uint256)
_frameSelector: transient(bytes4)
_frameCalldataHash: transient(bytes32)
_frameActionId: transient(uint16)
_frameNonce: transient(uint256)
_frameOpened: transient(bool)

_capActionId: transient(uint16)
_capEffectClass: transient(uint8)
_capConsumer: transient(address)
_capTarget: transient(address)
_capSemanticHash: transient(bytes32)
_capResource: transient(address)
_capMaxAmount: transient(uint256)
_capBeneficiary: transient(address)
_capConsumed: transient(bool)
_capStartBalance: transient(uint256)
_capStartReserved: transient(uint256)

PHASE_IDLE: constant(uint8) = 0
PHASE_DIRECT: constant(uint8) = 1
PHASE_ADMIN: constant(uint8) = 2
PHASE_DISPATCHING: constant(uint8) = 3
PHASE_ACTIVE: constant(uint8) = 4
PHASE_SETTLING: constant(uint8) = 5
PHASE_COMMITMENT: constant(uint8) = 6

LIFECYCLE_ACTIVE: constant(uint8) = 1
LIFECYCLE_DRAIN_ONLY: constant(uint8) = 2

EFFECT_SPEND: constant(uint8) = 1
EFFECT_LIABILITY: constant(uint8) = 2
EFFECT_ASSET_RELEASE: constant(uint8) = 3
EFFECT_AUTHORITY: constant(uint8) = 4

CONSUMER_LEGO: constant(uint8) = 1
CONSUMER_CORE: constant(uint8) = 2
CONSUMER_NONE: constant(uint8) = 3

MAX_ATTACHMENTS: constant(uint256) = 16
ACTION_DOMAIN: constant(bytes32) = keccak256("underscore.wallet-v3-action-v1")

COMMITMENT_EXTERNAL_EXACT: constant(uint8) = 1
COMMITMENT_RESERVED_TRANSFER: constant(uint8) = 2
COMMITMENT_LIVE: constant(uint8) = 1
COMMITMENT_USED: constant(uint8) = 2
COMMITMENT_EXPIRED: constant(uint8) = 3
COMMITMENT_SETTLED: constant(uint8) = 4
COMMITMENT_REFUNDED: constant(uint8) = 5

ERC1271_MAGIC: constant(bytes4) = 0x1626ba7e
ERC1271_INVALID: constant(bytes4) = 0xffffffff
ERC165_INTERFACE: constant(bytes4) = 0x01ffc9a7

CONFIG_PROBE_GAS: constant(uint256) = 30_000
CONFIG_INTERFACE_MARKER: constant(bytes32) = keccak256(
    "underscore.user-wallet-config-v3-poc-v1"
)

event AttachmentAdded:
    attachmentId: indexed(uint256)
    familyId: indexed(bytes32)
    version: uint32
    extender: address

event SessionOpened:
    attachmentId: indexed(uint256)
    selector: indexed(bytes4)
    calldataHash: bytes32
    semanticHash: bytes32
    nonce: uint256


@deploy
def __init__(owner: address):
    assert owner != empty(address)
    OWNER = owner


@view
@external
def owner() -> address:
    return OWNER


@view
@external
def phase() -> uint8:
    return self._phase


@internal
@view
def _balanceOf(token: address) -> uint256:
    success: bool = False
    returndata: Bytes[33] = b""
    success, returndata = raw_call(
        token,
        concat(method_id("balanceOf(address)"), abi_encode(self)),
        max_outsize=33,
        is_static_call=True,
        revert_on_failure=False,
    )
    assert success and len(returndata) == 32
    return abi_decode(returndata, uint256)


@internal
def _exactBoolCall(target: address, calldata: Bytes[132]):
    success: bool = False
    returndata: Bytes[33] = b""
    success, returndata = raw_call(
        target,
        calldata,
        max_outsize=33,
        revert_on_failure=False,
    )
    assert success and len(returndata) == 32
    assert abi_decode(returndata, bool)


@internal
@view
def _authorizedTransfer(
    candidate: address,
    realCaller: address,
    recipient: address,
    token: address,
    amount: uint256,
) -> bool:
    success: bool = False
    returndata: Bytes[33] = b""
    success, returndata = raw_call(
        candidate,
        concat(
            method_id("authorizeTransfer(address,address,address,uint256)"),
            abi_encode(realCaller, recipient, token, amount),
        ),
        gas=CONFIG_PROBE_GAS,
        max_outsize=33,
        is_static_call=True,
        revert_on_failure=False,
    )
    return (
        success
        and len(returndata) == 32
        and abi_decode(returndata, uint256) == 1
    )


@internal
@view
def _allowance(token: address, owner: address, spender: address) -> uint256:
    success: bool = False
    returndata: Bytes[33] = b""
    success, returndata = raw_call(
        token,
        concat(method_id("allowance(address,address)"), abi_encode(owner, spender)),
        max_outsize=33,
        is_static_call=True,
        revert_on_failure=False,
    )
    assert success and len(returndata) == 32
    return abi_decode(returndata, uint256)


@internal
@view
def _authorizedSession(
    candidate: address,
    realCaller: address,
    attachmentId: uint256,
    selector: bytes4,
    request: w3.ActionEnvelope,
) -> bool:
    success: bool = False
    returndata: Bytes[33] = b""
    success, returndata = raw_call(
        candidate,
        concat(
            method_id(
                "authorizeSession(address,uint256,bytes4,(uint16,uint8,address,address,address,uint256,address,bytes32))"
            ),
            abi_encode(realCaller, attachmentId, selector, request),
        ),
        gas=CONFIG_PROBE_GAS,
        max_outsize=33,
        is_static_call=True,
        revert_on_failure=False,
    )
    return (
        success
        and len(returndata) == 32
        and abi_decode(returndata, uint256) == 1
    )


@internal
@view
def _semanticHash(request: w3.ActionEnvelope) -> bytes32:
    return keccak256(
        abi_encode(
            ACTION_DOMAIN,
            chain.id,
            self,
            self._frameAttachmentId,
            self._frameSelector,
            request.actionId,
            request.effectClass,
            request.consumer,
            request.target,
            request.resource,
            request.maxAmount,
            request.beneficiary,
            request.actionDataHash,
        )
    )


@internal
@view
def _requireDependencyCodehashes(attachmentId: uint256):
    record: w3.AttachmentView = self._attachments[attachmentId]
    assert record.extender.codehash == record.extenderCodehash
    if record.lego != empty(address):
        assert record.lego.codehash == record.legoCodehash
    if record.authorityTarget != empty(address):
        assert (
            record.authorityTarget.codehash == record.authorityTargetCodehash
        )
    if record.x402Helper != empty(address):
        assert record.x402Helper.codehash == record.x402HelperCodehash


@internal
def _clearSession():
    self._frameCaller = empty(address)
    self._frameConfig = empty(address)
    self._frameAttachmentId = 0
    self._frameSelector = empty(bytes4)
    self._frameCalldataHash = empty(bytes32)
    self._frameActionId = 0
    self._frameNonce = 0
    self._frameOpened = False
    self._capActionId = 0
    self._capEffectClass = 0
    self._capConsumer = empty(address)
    self._capTarget = empty(address)
    self._capSemanticHash = empty(bytes32)
    self._capResource = empty(address)
    self._capMaxAmount = 0
    self._capBeneficiary = empty(address)
    self._capConsumed = False
    self._capStartBalance = 0
    self._capStartReserved = 0


@view
@external
def availableBalance(token: address) -> uint256:
    balance: uint256 = self._balanceOf(token)
    amountReserved: uint256 = self.reserved[token]
    if amountReserved >= balance:
        return 0
    return balance - amountReserved


@view
@external
def attachment(attachmentId: uint256) -> w3.AttachmentView:
    return self._attachments[attachmentId]


@view
@external
def currentRoute(selector: bytes4) -> w3.RouteView:
    attachmentId: uint256 = self._currentRouteIds[selector]
    return self._routes[attachmentId][selector]


@view
@external
def commitment(commitmentId: bytes32) -> w3.CommitmentView:
    return self._commitments[commitmentId]


@external
def replaceConfig(newConfig: address):
    assert self._phase == PHASE_IDLE
    assert msg.sender == OWNER
    self._phase = PHASE_ADMIN
    assert newConfig.is_contract

    markerSuccess: bool = False
    markerReturn: Bytes[33] = b""
    markerSuccess, markerReturn = raw_call(
        newConfig,
        method_id("configInterfaceMarker()"),
        gas=CONFIG_PROBE_GAS,
        max_outsize=33,
        is_static_call=True,
        revert_on_failure=False,
    )
    assert markerSuccess and len(markerReturn) == 32
    assert abi_decode(markerReturn, bytes32) == CONFIG_INTERFACE_MARKER

    walletSuccess: bool = False
    walletReturn: Bytes[33] = b""
    walletSuccess, walletReturn = raw_call(
        newConfig,
        method_id("wallet()"),
        gas=CONFIG_PROBE_GAS,
        max_outsize=33,
        is_static_call=True,
        revert_on_failure=False,
    )
    assert walletSuccess and len(walletReturn) == 32
    assert abi_decode(walletReturn, address) == self

    self.config = newConfig
    self._phase = PHASE_IDLE


@external
def transferFunds(recipient: address, token: address, amount: uint256):
    assert self._phase == PHASE_IDLE
    candidate: address = self.config
    assert candidate != empty(address)
    self._phase = PHASE_DIRECT
    assert self._authorizedTransfer(candidate, msg.sender, recipient, token, amount)
    balance: uint256 = self._balanceOf(token)
    assert amount <= balance - min(balance, self.reserved[token])
    self._exactBoolCall(
        token,
        concat(method_id("transfer(address,uint256)"), abi_encode(recipient, amount)),
    )
    self._phase = PHASE_IDLE


@external
def attachExtender(request: w3.AttachmentRequest):
    assert self._phase == PHASE_IDLE
    assert msg.sender == OWNER
    assert self.config != empty(address)
    self._phase = PHASE_ADMIN

    assert self.attachmentCount < MAX_ATTACHMENTS
    assert request.familyId != empty(bytes32)
    assert request.version != 0
    assert request.extender.is_contract
    assert len(request.routes) != 0
    if request.lego != empty(address):
        assert request.lego.is_contract
    if request.authorityTarget != empty(address):
        assert request.authorityTarget.is_contract
    if request.x402Helper != empty(address):
        assert request.x402Helper.is_contract

    predecessorId: uint256 = self._currentFamilyAttachment[request.familyId]
    if predecessorId != 0:
        predecessor: w3.AttachmentView = self._attachments[predecessorId]
        assert request.version > predecessor.version
        assert request.extender != predecessor.extender

    for i: uint256 in range(len(request.routes), bound=8):
        route: w3.RouteSpec = request.routes[i]
        assert route.selector != empty(bytes4)
        assert route.actionId != 0
        assert (
            route.effectClass >= EFFECT_SPEND
            and route.effectClass <= EFFECT_AUTHORITY
        )
        assert (
            route.consumerMode >= CONSUMER_LEGO
            and route.consumerMode <= CONSUMER_NONE
        )
        if route.consumerMode == CONSUMER_LEGO:
            assert request.lego != empty(address)
        for j: uint256 in range(8):
            if j < i:
                assert request.routes[j].selector != route.selector
                assert request.routes[j].actionId != route.actionId
        existingRoute: uint256 = self._currentRouteIds[route.selector]
        assert (
            existingRoute == 0 or existingRoute == predecessorId
        )

    for i: uint256 in range(len(request.exitSelectors), bound=4):
        exitSelector: bytes4 = request.exitSelectors[i]
        found: bool = False
        for j: uint256 in range(len(request.routes), bound=8):
            if request.routes[j].selector == exitSelector:
                found = True
        assert found
        for j: uint256 in range(4):
            if j < i:
                assert request.exitSelectors[j] != exitSelector

    if predecessorId != 0:
        predecessor: w3.AttachmentView = self._attachments[predecessorId]
        for i: uint256 in range(8):
            if i < convert(predecessor.routeCount, uint256):
                oldSelector: bytes4 = self._routeSelectors[predecessorId][i]
                if self._currentRouteIds[oldSelector] == predecessorId:
                    self._currentRouteIds[oldSelector] = 0
        self._attachments[predecessorId].lifecycle = LIFECYCLE_DRAIN_ONLY

    attachmentId: uint256 = self.attachmentCount + 1
    self.attachmentCount = attachmentId
    self._attachments[attachmentId] = w3.AttachmentView(
        familyId=request.familyId,
        version=request.version,
        lifecycle=LIFECYCLE_ACTIVE,
        extender=request.extender,
        extenderCodehash=request.extender.codehash,
        lego=request.lego,
        legoCodehash=request.lego.codehash,
        authorityTarget=request.authorityTarget,
        authorityTargetCodehash=request.authorityTarget.codehash,
        x402Helper=request.x402Helper,
        x402HelperCodehash=request.x402Helper.codehash,
        routeCount=convert(len(request.routes), uint8),
        exitCount=convert(len(request.exitSelectors), uint8),
    )
    for i: uint256 in range(len(request.routes), bound=8):
        route: w3.RouteSpec = request.routes[i]
        self._routeSelectors[attachmentId][i] = route.selector
        self._routes[attachmentId][route.selector] = w3.RouteView(
            attachmentId=attachmentId,
            actionId=route.actionId,
            effectClass=route.effectClass,
            consumerMode=route.consumerMode,
            isExit=False,
        )
        self._currentRouteIds[route.selector] = attachmentId
    for i: uint256 in range(len(request.exitSelectors), bound=4):
        self._routes[attachmentId][request.exitSelectors[i]].isExit = True

    self._currentFamilyAttachment[request.familyId] = attachmentId
    self._phase = PHASE_IDLE
    log AttachmentAdded(
        attachmentId=attachmentId,
        familyId=request.familyId,
        version=request.version,
        extender=request.extender,
    )


@internal
def _dispatch(
    attachmentId: uint256,
    typedExtenderCalldata: Bytes[1024],
    drainOnly: bool,
):
    assert self._phase == PHASE_IDLE
    candidate: address = self.config
    assert candidate != empty(address)
    assert len(typedExtenderCalldata) >= 4
    selector: bytes4 = convert(slice(typedExtenderCalldata, 0, 4), bytes4)
    record: w3.AttachmentView = self._attachments[attachmentId]
    route: w3.RouteView = self._routes[attachmentId][selector]
    assert route.attachmentId == attachmentId
    if drainOnly:
        assert record.lifecycle == LIFECYCLE_DRAIN_ONLY
        assert route.isExit
    else:
        assert record.lifecycle == LIFECYCLE_ACTIVE
        assert self._currentRouteIds[selector] == attachmentId

    self._phase = PHASE_DISPATCHING
    self._frameCaller = msg.sender
    self._frameConfig = candidate
    self._frameAttachmentId = attachmentId
    self._frameSelector = selector
    self._frameCalldataHash = keccak256(typedExtenderCalldata)
    self._frameActionId = route.actionId
    self.sessionNonce += 1
    self._frameNonce = self.sessionNonce
    self._frameOpened = False
    self._requireDependencyCodehashes(attachmentId)

    raw_call(record.extender, typedExtenderCalldata, max_outsize=0)
    assert self._frameOpened and self._phase == PHASE_ACTIVE
    if route.consumerMode == CONSUMER_NONE:
        assert not self._capConsumed
    else:
        assert self._capConsumed
    self._phase = PHASE_SETTLING

    if self._capEffectClass == EFFECT_SPEND and self._capConsumer != empty(address):
        self._exactBoolCall(
            self._capResource,
            concat(
                method_id("approve(address,uint256)"),
                abi_encode(self._capConsumer, convert(0, uint256)),
            ),
        )
        finalBalance: uint256 = self._balanceOf(self._capResource)
        if finalBalance < self._capStartBalance:
            assert (
                self._capStartBalance - finalBalance <= self._capMaxAmount
            )
        assert self.reserved[self._capResource] == self._capStartReserved
        assert (
            self._allowance(self._capResource, self, self._capConsumer) == 0
        )

    self._clearSession()
    self._phase = PHASE_IDLE


@external
def execute(typedExtenderCalldata: Bytes[1024]):
    assert len(typedExtenderCalldata) >= 4
    selector: bytes4 = convert(slice(typedExtenderCalldata, 0, 4), bytes4)
    attachmentId: uint256 = self._currentRouteIds[selector]
    assert attachmentId != 0
    self._dispatch(attachmentId, typedExtenderCalldata, False)


@external
def executeAttached(attachmentId: uint256, typedExtenderCalldata: Bytes[1024]):
    self._dispatch(attachmentId, typedExtenderCalldata, True)


@external
def openSession(request: w3.ActionEnvelope):
    assert self._phase == PHASE_DISPATCHING
    assert not self._frameOpened
    attachmentId: uint256 = self._frameAttachmentId
    record: w3.AttachmentView = self._attachments[attachmentId]
    route: w3.RouteView = self._routes[attachmentId][self._frameSelector]
    assert msg.sender == record.extender
    assert request.actionId == self._frameActionId
    assert self._frameActionId == route.actionId
    assert request.effectClass == route.effectClass
    if route.consumerMode == CONSUMER_LEGO:
        assert request.consumer == record.lego
    else:
        assert request.consumer == empty(address)
    if request.effectClass == EFFECT_SPEND:
        assert request.maxAmount != 0
    self._requireDependencyCodehashes(attachmentId)

    semanticHash: bytes32 = self._semanticHash(request)
    assert self._authorizedSession(
        self._frameConfig,
        self._frameCaller,
        attachmentId,
        self._frameSelector,
        request,
    )

    self._capActionId = request.actionId
    self._capEffectClass = request.effectClass
    self._capConsumer = request.consumer
    self._capTarget = request.target
    self._capSemanticHash = semanticHash
    self._capResource = request.resource
    self._capMaxAmount = request.maxAmount
    self._capBeneficiary = request.beneficiary
    self._capConsumed = False
    self._frameOpened = True

    if request.effectClass == EFFECT_SPEND and request.consumer != empty(address):
        startBalance: uint256 = self._balanceOf(request.resource)
        startReserved: uint256 = self.reserved[request.resource]
        assert startBalance > startReserved
        assert request.maxAmount <= startBalance - startReserved
        assert (
            self._allowance(request.resource, self, request.consumer) == 0
        )
        self._capStartBalance = startBalance
        self._capStartReserved = startReserved
        self._exactBoolCall(
            request.resource,
            concat(
                method_id("approve(address,uint256)"),
                abi_encode(request.consumer, request.maxAmount),
            ),
        )

    self._phase = PHASE_ACTIVE
    log SessionOpened(
        attachmentId=attachmentId,
        selector=self._frameSelector,
        calldataHash=self._frameCalldataHash,
        semanticHash=semanticHash,
        nonce=self._frameNonce,
    )


@external
def consumeCapability(actualEnvelope: w3.ActionEnvelope):
    assert self._phase == PHASE_ACTIVE
    assert self._frameOpened
    assert (
        self._routes[self._frameAttachmentId][self._frameSelector].consumerMode
        == CONSUMER_LEGO
    )
    assert self._capConsumer != empty(address)
    assert msg.sender == self._capConsumer
    assert not self._capConsumed
    assert actualEnvelope.actionId == self._capActionId
    assert actualEnvelope.effectClass == self._capEffectClass
    assert actualEnvelope.consumer == self._capConsumer
    assert actualEnvelope.target == self._capTarget
    assert actualEnvelope.resource == self._capResource
    assert actualEnvelope.maxAmount == self._capMaxAmount
    assert actualEnvelope.beneficiary == self._capBeneficiary
    assert self._semanticHash(actualEnvelope) == self._capSemanticHash
    self._capConsumed = True


@external
def setDebtOperator(enabled: bool, actualEnvelope: w3.ActionEnvelope):
    assert self._phase == PHASE_ACTIVE
    assert self._frameOpened and msg.sender == self._attachments[self._frameAttachmentId].extender
    assert not self._capConsumed
    assert (
        self._routes[self._frameAttachmentId][self._frameSelector].consumerMode
        == CONSUMER_CORE
    )
    expectedAction: uint16 = 13 if enabled else 14
    record: w3.AttachmentView = self._attachments[self._frameAttachmentId]
    assert self._capActionId == expectedAction
    assert self._capEffectClass == EFFECT_AUTHORITY
    assert self._capConsumer == empty(address)
    assert self._capTarget == record.authorityTarget
    assert self._capResource == empty(address)
    assert self._capMaxAmount == 0
    assert self._capBeneficiary == record.lego
    assert actualEnvelope.actionId == expectedAction
    assert actualEnvelope.effectClass == EFFECT_AUTHORITY
    assert actualEnvelope.consumer == empty(address)
    assert actualEnvelope.target == record.authorityTarget
    assert actualEnvelope.resource == empty(address)
    assert actualEnvelope.maxAmount == 0
    assert actualEnvelope.beneficiary == record.lego
    expectedDataHash: bytes32 = keccak256(
        abi_encode(record.authorityTarget, record.lego, enabled)
    )
    assert actualEnvelope.actionDataHash == expectedDataHash
    assert self._semanticHash(actualEnvelope) == self._capSemanticHash
    self._requireDependencyCodehashes(self._frameAttachmentId)
    self._capConsumed = True
    extcall IOperatorProtocolV3(record.authorityTarget).setOperator(record.lego, enabled)


@external
def createExternalExact(fields: w3.ExternalExactFields, actualEnvelope: w3.ActionEnvelope):
    assert self._phase == PHASE_ACTIVE
    attachmentId: uint256 = self._frameAttachmentId
    record: w3.AttachmentView = self._attachments[attachmentId]
    assert self._frameOpened and msg.sender == record.extender
    assert not self._capConsumed
    assert (
        self._routes[attachmentId][self._frameSelector].consumerMode
        == CONSUMER_CORE
    )
    assert self._capActionId == 20 and actualEnvelope.actionId == 20
    assert self._capEffectClass == EFFECT_SPEND and actualEnvelope.effectClass == EFFECT_SPEND
    assert self._capConsumer == empty(address) and actualEnvelope.consumer == empty(address)
    assert record.x402Helper != empty(address)
    assert fields.helper == record.x402Helper
    assert fields.token == staticcall IX402Helper(fields.helper).token()
    derivedDigest: bytes32 = staticcall IX402Helper(fields.helper).digest(
        self,
        fields.destination,
        fields.amount,
        fields.validAfter,
        fields.validBefore,
        fields.nonce,
    )
    assert fields.digest == derivedDigest
    expectedDataHash: bytes32 = keccak256(
        abi_encode(
            fields.commitmentId,
            fields.token,
            fields.amount,
            fields.destination,
            fields.validAfter,
            fields.validBefore,
            fields.nonce,
            fields.helper,
            fields.digest,
        )
    )
    assert actualEnvelope.target == fields.token
    assert actualEnvelope.resource == fields.token
    assert actualEnvelope.maxAmount == fields.amount
    assert actualEnvelope.beneficiary == fields.destination
    assert actualEnvelope.actionDataHash == expectedDataHash
    assert self._capTarget == actualEnvelope.target
    assert self._capResource == actualEnvelope.resource
    assert self._capMaxAmount == actualEnvelope.maxAmount
    assert self._capBeneficiary == actualEnvelope.beneficiary
    assert self._semanticHash(actualEnvelope) == self._capSemanticHash
    assert fields.amount != 0 and fields.destination != empty(address)
    assert fields.validBefore > fields.validAfter
    assert not self._usedCommitmentId[fields.commitmentId]
    assert not self._usedExternalDigest[fields.digest]
    assert not self._usedExternalNonce[fields.nonce]
    assert not staticcall IX402Helper(fields.helper).authorizationUsed(self, fields.nonce)
    balance: uint256 = self._balanceOf(fields.token)
    assert balance > self.reserved[fields.token]
    assert fields.amount <= balance - self.reserved[fields.token]
    self._requireDependencyCodehashes(attachmentId)

    self._capConsumed = True
    self._usedCommitmentId[fields.commitmentId] = True
    self._usedExternalDigest[fields.digest] = True
    self._usedExternalNonce[fields.nonce] = True
    self._digestCommitmentId[fields.digest] = fields.commitmentId
    self.reserved[fields.token] += fields.amount
    self._commitments[fields.commitmentId] = w3.CommitmentView(
        mode=COMMITMENT_EXTERNAL_EXACT,
        state=COMMITMENT_LIVE,
        token=fields.token,
        totalAmount=fields.amount,
        remainingAmount=fields.amount,
        destination=fields.destination,
        settlementOperator=empty(address),
        digest=fields.digest,
        validAfter=fields.validAfter,
        validBefore=fields.validBefore,
        nonce=fields.nonce,
        helper=fields.helper,
        helperCodehash=record.x402HelperCodehash,
    )


@external
def createReservedTransfer(fields: w3.ReservedTransferFields, actualEnvelope: w3.ActionEnvelope):
    assert self._phase == PHASE_ACTIVE
    record: w3.AttachmentView = self._attachments[self._frameAttachmentId]
    assert self._frameOpened and msg.sender == record.extender
    assert not self._capConsumed
    assert (
        self._routes[self._frameAttachmentId][self._frameSelector].consumerMode
        == CONSUMER_CORE
    )
    assert self._capActionId == 21 and actualEnvelope.actionId == 21
    assert self._capEffectClass == EFFECT_SPEND and actualEnvelope.effectClass == EFFECT_SPEND
    assert self._capConsumer == empty(address) and actualEnvelope.consumer == empty(address)
    expectedDataHash: bytes32 = keccak256(
        abi_encode(
            fields.commitmentId,
            fields.token,
            fields.totalAmount,
            fields.destination,
            fields.settlementOperator,
        )
    )
    assert actualEnvelope.target == fields.token
    assert actualEnvelope.resource == fields.token
    assert actualEnvelope.maxAmount == fields.totalAmount
    assert actualEnvelope.beneficiary == fields.destination
    assert actualEnvelope.actionDataHash == expectedDataHash
    assert self._capTarget == actualEnvelope.target
    assert self._capResource == actualEnvelope.resource
    assert self._capMaxAmount == actualEnvelope.maxAmount
    assert self._capBeneficiary == actualEnvelope.beneficiary
    assert self._semanticHash(actualEnvelope) == self._capSemanticHash
    assert (
        fields.totalAmount != 0
        and fields.destination != empty(address)
        and fields.settlementOperator != empty(address)
    )
    assert not self._usedCommitmentId[fields.commitmentId]
    balance: uint256 = self._balanceOf(fields.token)
    assert balance > self.reserved[fields.token]
    assert fields.totalAmount <= balance - self.reserved[fields.token]

    self._capConsumed = True
    self._usedCommitmentId[fields.commitmentId] = True
    self.reserved[fields.token] += fields.totalAmount
    self._commitments[fields.commitmentId] = w3.CommitmentView(
        mode=COMMITMENT_RESERVED_TRANSFER,
        state=COMMITMENT_LIVE,
        token=fields.token,
        totalAmount=fields.totalAmount,
        remainingAmount=fields.totalAmount,
        destination=fields.destination,
        settlementOperator=fields.settlementOperator,
        digest=empty(bytes32),
        validAfter=0,
        validBefore=0,
        nonce=empty(bytes32),
        helper=empty(address),
        helperCodehash=empty(bytes32),
    )


@external
def syncExternalPull(commitmentId: bytes32):
    assert self._phase == PHASE_IDLE
    self._phase = PHASE_COMMITMENT
    commitment: w3.CommitmentView = self._commitments[commitmentId]
    assert commitment.mode == COMMITMENT_EXTERNAL_EXACT
    assert commitment.state == COMMITMENT_LIVE
    assert commitment.helper.codehash == commitment.helperCodehash
    assert staticcall IX402Helper(commitment.helper).authorizationUsed(
        self, commitment.nonce
    )
    self._commitments[commitmentId].state = COMMITMENT_USED
    self._commitments[commitmentId].remainingAmount = 0
    self.reserved[commitment.token] -= commitment.totalAmount
    self._phase = PHASE_IDLE


@external
def expireExternalExact(commitmentId: bytes32):
    assert self._phase == PHASE_IDLE
    self._phase = PHASE_COMMITMENT
    commitment: w3.CommitmentView = self._commitments[commitmentId]
    assert commitment.mode == COMMITMENT_EXTERNAL_EXACT
    assert commitment.state == COMMITMENT_LIVE
    assert block.timestamp >= commitment.validBefore
    assert commitment.helper.codehash == commitment.helperCodehash
    assert not staticcall IX402Helper(commitment.helper).authorizationUsed(
        self, commitment.nonce
    )
    self._commitments[commitmentId].state = COMMITMENT_EXPIRED
    self._commitments[commitmentId].remainingAmount = 0
    self.reserved[commitment.token] -= commitment.totalAmount
    self._phase = PHASE_IDLE


@external
def settleReservedTransfer(commitmentId: bytes32, amount: uint256):
    assert self._phase == PHASE_IDLE
    self._phase = PHASE_COMMITMENT
    commitment: w3.CommitmentView = self._commitments[commitmentId]
    assert commitment.mode == COMMITMENT_RESERVED_TRANSFER
    assert commitment.state == COMMITMENT_LIVE
    assert msg.sender == commitment.settlementOperator
    assert amount != 0 and amount <= commitment.remainingAmount
    remaining: uint256 = commitment.remainingAmount - amount
    self._commitments[commitmentId].remainingAmount = remaining
    self.reserved[commitment.token] -= amount
    if remaining == 0:
        self._commitments[commitmentId].state = COMMITMENT_SETTLED
    self._exactBoolCall(
        commitment.token,
        concat(
            method_id("transfer(address,uint256)"),
            abi_encode(commitment.destination, amount),
        ),
    )
    self._phase = PHASE_IDLE


@external
def refundReservedTransfer(commitmentId: bytes32):
    assert self._phase == PHASE_IDLE
    assert msg.sender == OWNER
    self._phase = PHASE_COMMITMENT
    commitment: w3.CommitmentView = self._commitments[commitmentId]
    assert commitment.mode == COMMITMENT_RESERVED_TRANSFER
    assert commitment.state == COMMITMENT_LIVE
    self._commitments[commitmentId].remainingAmount = 0
    self._commitments[commitmentId].state = COMMITMENT_REFUNDED
    self.reserved[commitment.token] -= commitment.remainingAmount
    self._phase = PHASE_IDLE


@view
@external
def isValidSignature(digest: bytes32, signature: Bytes[256]) -> bytes4:
    if self._phase != PHASE_IDLE:
        return ERC1271_INVALID
    commitmentId: bytes32 = self._digestCommitmentId[digest]
    commitment: w3.CommitmentView = self._commitments[commitmentId]
    if commitment.mode != COMMITMENT_EXTERNAL_EXACT:
        return ERC1271_INVALID
    if commitment.state != COMMITMENT_LIVE or commitment.digest != digest:
        return ERC1271_INVALID
    if msg.sender != commitment.token:
        return ERC1271_INVALID
    if block.timestamp <= commitment.validAfter or block.timestamp >= commitment.validBefore:
        return ERC1271_INVALID
    return ERC1271_MAGIC


@pure
@external
def supportsInterface(interfaceId: bytes4) -> bool:
    if interfaceId == 0xffffffff:
        return False
    return interfaceId == ERC165_INTERFACE or interfaceId == ERC1271_MAGIC
