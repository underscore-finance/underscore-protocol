#    ┳┳
#    ┃┃┏┏┓┏┓
#    ┗┛┛┗ ┛
#               .---.             ,--,    ,--,                 ___
#              /. ./|           ,--.'|  ,--.'|               ,--.'|_
#          .--'.  ' ;           |  | :  |  | :               |  | :,'
#         /__./ \ : |           :  : '  :  : '               :  : ' :
#     .--'.  '   \' .  ,--.--.  |  ' |  |  ' |      ,---.  .;__,'  /
#    /___/ \ |    ' ' /       \ '  | |  '  | |     /     \ |  |   |
#    ;   \  \;      :.--.  .-. ||  | :  |  | :    /    /  |:__,'| :
#     \   ;  `      | \__\/: . .'  : |__'  : |__ .    ' / |  '  : |__
#      .   \    .\  ; ," .--.; ||  | '.'|  | '.'|'   ;   /|  |  | '.'|
#       \   \   ' \ |/  /  ,.  |;  :    ;  :    ;'   |  / |  ;  :    ;
#        :   '  |--";  :   .'   \  ,   /|  ,   / |   :    |  |  ,   /
#         \   \ ;   |  ,     .-./---`-'  ---`-'   \   \  /    ---`-'
#          '---"     `--`---'                      `----'
#     ╔══════════════════════════════════════════╗
#     ║  ** User Wallet V3 **                    ║
#     ║  Handles all user wallet functionality   ║
#     ╚══════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

"""
@title User Wallet V3
@notice Custodies wallet assets and executes Config-authorized actions through versioned extenders.
@dev Uses a transient phase machine, capability envelopes, dependency codehash pins, strict ERC20 calls, and reserved commitments to constrain every asset or authority effect.
"""

from contracts.poc.userWallet.types import WalletV3Types as w3
from contracts.poc.userWallet.interfaces import IOperatorProtocolV3
from contracts.poc.userWallet.interfaces import IX402Helper

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

# data
config: public(address) # config() returns the active policy contract
reserved: public(HashMap[address, uint256]) # reserved(token) returns committed unavailable amount

# attachment data
attachments: HashMap[uint256, w3.AttachmentView] # attachment id -> data
routes: HashMap[uint256, HashMap[bytes4, w3.RouteView]] # attachment id -> selector -> route
routeSelectors: HashMap[uint256, HashMap[uint256, bytes4]] # attachment id -> index -> selector
currentRouteIds: HashMap[bytes4, uint256] # selector -> attachment id
currentFamilyAttachment: HashMap[bytes32, uint256] # family id -> attachment id
attachmentCount: uint256
sessionNonce: uint256

# commitment data
commitments: HashMap[bytes32, w3.CommitmentView] # commitment id -> data
digestCommitmentId: HashMap[bytes32, bytes32] # digest -> commitment id
usedCommitmentId: HashMap[bytes32, bool]
usedExternalDigest: HashMap[bytes32, bool]
usedExternalNonce: HashMap[bytes32, bool]

# session data
currentPhase: transient(uint8)
frameCaller: transient(address)
frameConfig: transient(address)
frameAttachmentId: transient(uint256)
frameSelector: transient(bytes4)
frameCalldataHash: transient(bytes32)
frameActionId: transient(uint16)
frameNonce: transient(uint256)
frameOpened: transient(bool)

# capability data
capActionId: transient(uint16)
capEffectClass: transient(uint8)
capConsumer: transient(address)
capTarget: transient(address)
capSemanticHash: transient(bytes32)
capResource: transient(address)
capMaxAmount: transient(uint256)
capBeneficiary: transient(address)
capConsumed: transient(bool)
capStartBalance: transient(uint256)
capStartReserved: transient(uint256)

# constants
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

OWNER: immutable(address)


@deploy
def __init__(_owner: address):
    """
    @notice Deploys a wallet with an immutable owner.
    @dev The owner can replace the Config, attach extender versions, and refund live reserved-transfer commitments. A Config is installed separately after deployment.
    @param _owner The address receiving permanent owner authority over this wallet.
    """
    assert _owner != empty(address)
    OWNER = _owner


@view
@external
def owner() -> address:
    """
    @notice Returns the wallet's immutable owner.
    @return The owner address fixed at deployment.
    """
    return OWNER


@view
@external
def phase() -> uint8:
    """
    @notice Returns the wallet's current execution phase.
    @dev The phase is transient storage used as both a reentrancy guard and a callback state machine. It is normally PHASE_IDLE outside an active transaction.
    @return The current phase constant.
    """
    return self.currentPhase


@view
@internal
def _getTokenBalance(_token: address) -> uint256:
    """
    @notice Reads this wallet's ERC20 balance using the strict token-response policy.
    @dev Performs a static balanceOf call and accepts only an exact 32-byte uint256 response. Requesting 33 bytes makes oversized responses detectable.
    @param _token The token whose balance is being read.
    @return The token balance owned by this wallet.
    """
    # request one extra byte so oversized responses fail the exact length check
    success: bool = False
    returndata: Bytes[33] = b""
    success, returndata = raw_call(
        _token,
        concat(method_id("balanceOf(address)"), abi_encode(self)),
        max_outsize = 33,
        is_static_call = True,
        revert_on_failure = False,
    )
    assert success and len(returndata) == 32
    return abi_decode(returndata, uint256)


@internal
def _strictErc20Call(_token: address, _calldata: Bytes[132]):
    """
    @notice Executes a state-changing ERC20 call that must return canonical True.
    @dev Reverts unless the token call succeeds and returns exactly 32 bytes decoding to True. No-return and false-return token behavior is intentionally rejected.
    @param _token The token contract to call.
    @param _calldata The fully encoded ERC20 function call.
    """
    # unlike permissive ERC20 wrappers, require an exact 32-byte True response
    success: bool = False
    returndata: Bytes[33] = b""
    success, returndata = raw_call(
        _token,
        _calldata,
        max_outsize = 33,
        revert_on_failure = False,
    )
    assert success and len(returndata) == 32
    assert abi_decode(returndata, bool)


@view
@internal
def _callConfigBool(_candidate: address, _calldata: Bytes[356]) -> bool:
    """
    @notice Calls a boolean authorization method on a Config candidate.
    @dev Uses a bounded-gas static call and returns False when the call fails, returns a non-32-byte value, or returns anything other than the canonical word 1.
    @param _candidate The Config contract being queried.
    @param _calldata The encoded Config authorization call.
    @return True only for a successful exact canonical authorization response.
    """
    # configs are untrusted: bound their gas and reject malformed return data
    success: bool = False
    returndata: Bytes[33] = b""
    success, returndata = raw_call(
        _candidate,
        _calldata,
        gas = CONFIG_PROBE_GAS,
        max_outsize = 33,
        is_static_call = True,
        revert_on_failure = False,
    )
    return success and len(returndata) == 32 and abi_decode(returndata, uint256) == 1


@view
@internal
def _authorizedTransfer(
    _candidate: address,
    _realCaller: address,
    _recipient: address,
    _token: address,
    _amount: uint256,
) -> bool:
    """
    @notice Asks the Config whether a direct token transfer is authorized.
    @dev Preserves the original external caller so Config policy can distinguish owners, managers, recipients, tokens, and amounts.
    @param _candidate The active Config captured before entering the direct-transfer phase.
    @param _realCaller The account that called transferFunds.
    @param _recipient The proposed token recipient.
    @param _token The token proposed for transfer.
    @param _amount The exact proposed transfer amount.
    @return True only when the Config explicitly authorizes the transfer.
    """
    return self._callConfigBool(
        _candidate,
        concat(
            method_id("authorizeTransfer(address,address,address,uint256)"),
            abi_encode(_realCaller, _recipient, _token, _amount),
        ),
    )


@view
@internal
def _getTokenAllowance(_token: address, _owner: address, _spender: address) -> uint256:
    """
    @notice Reads an ERC20 allowance using the strict token-response policy.
    @dev Performs a static allowance call and accepts only an exact 32-byte uint256 response.
    @param _token The token whose allowance is being read.
    @param _owner The account that granted the allowance.
    @param _spender The account permitted to spend tokens.
    @return The current allowance from owner to spender.
    """
    # keep allowance reads under the same strict ERC20 return-data policy
    success: bool = False
    returndata: Bytes[33] = b""
    success, returndata = raw_call(
        _token,
        concat(method_id("allowance(address,address)"), abi_encode(_owner, _spender)),
        max_outsize = 33,
        is_static_call = True,
        revert_on_failure = False,
    )
    assert success and len(returndata) == 32
    return abi_decode(returndata, uint256)


@view
@internal
def _authorizedSession(
    _candidate: address,
    _realCaller: address,
    _attachmentId: uint256,
    _selector: bytes4,
    _request: w3.ActionEnvelope,
) -> bool:
    """
    @notice Asks the Config whether an extender session and its proposed capability are authorized.
    @dev Binds Config approval to the original caller, attachment, route selector, and complete action envelope.
    @param _candidate The Config captured when dispatch began.
    @param _realCaller The account that initiated execute or executeAttached.
    @param _attachmentId The attachment being dispatched.
    @param _selector The registered extender route selector.
    @param _request The capability envelope proposed by the extender.
    @return True only when the Config explicitly authorizes the complete session request.
    """
    return self._callConfigBool(
        _candidate,
        concat(
            method_id(
                "authorizeSession(address,uint256,bytes4,(uint16,uint8,address,address,address,uint256,address,bytes32))"
            ),
            abi_encode(_realCaller, _attachmentId, _selector, _request),
        ),
    )


@view
@internal
def _getConfigResponse(_candidate: address, _selector: Bytes[4]) -> Bytes[33]:
    """
    @notice Reads one exact ABI word from a no-argument Config probe.
    @dev Reverts unless the bounded-gas static call succeeds with exactly 32 return bytes. The caller decodes the word as the expected marker or wallet address.
    @param _candidate The Config candidate being validated.
    @param _selector The four-byte selector for configInterfaceMarker or wallet.
    @return The exact 32-byte response in a bounded Bytes value.
    """
    # typed calls cannot express this exact-length and bounded-gas probe policy
    success: bool = False
    returndata: Bytes[33] = b""
    success, returndata = raw_call(
        _candidate,
        _selector,
        gas = CONFIG_PROBE_GAS,
        max_outsize = 33,
        is_static_call = True,
        revert_on_failure = False,
    )
    assert success and len(returndata) == 32
    return returndata


@view
@internal
def _semanticHash(_request: w3.ActionEnvelope) -> bytes32:
    """
    @notice Computes the semantic identity of the capability proposed for the current frame.
    @dev Domain-separates by action domain, chain, wallet, attachment, and selector before hashing every ActionEnvelope field.
    @param _request The proposed or actual action envelope.
    @return The semantic hash used to bind authorization to later capability consumption.
    """
    return keccak256(
        abi_encode(
            ACTION_DOMAIN,
            chain.id,
            self,
            self.frameAttachmentId,
            self.frameSelector,
            _request.actionId,
            _request.effectClass,
            _request.consumer,
            _request.target,
            _request.resource,
            _request.maxAmount,
            _request.beneficiary,
            _request.actionDataHash,
        )
    )


@view
@internal
def _requireDependencyCodehashes(_attachmentId: uint256):
    """
    @notice Verifies that every contract dependency still has its attachment-time codehash.
    @dev Always checks the extender and conditionally checks the lego, authority target, and x402 helper when those optional addresses are configured.
    @param _attachmentId The attachment whose pinned dependency codehashes must be verified.
    """
    record: w3.AttachmentView = self.attachments[_attachmentId]
    assert record.extender.codehash == record.extenderCodehash
    if record.lego != empty(address):
        assert record.lego.codehash == record.legoCodehash
    if record.authorityTarget != empty(address):
        assert record.authorityTarget.codehash == record.authorityTargetCodehash
    if record.x402Helper != empty(address):
        assert record.x402Helper.codehash == record.x402HelperCodehash


@internal
def _clearSession():
    """
    @notice Clears all transient frame and capability state after dispatch settlement.
    @dev Prevents any authorization, allowance baseline, or caller context from leaking into a later execution. The caller separately restores PHASE_IDLE.
    """
    self.frameCaller = empty(address)
    self.frameConfig = empty(address)
    self.frameAttachmentId = 0
    self.frameSelector = empty(bytes4)
    self.frameCalldataHash = empty(bytes32)
    self.frameActionId = 0
    self.frameNonce = 0
    self.frameOpened = False
    self.capActionId = 0
    self.capEffectClass = 0
    self.capConsumer = empty(address)
    self.capTarget = empty(address)
    self.capSemanticHash = empty(bytes32)
    self.capResource = empty(address)
    self.capMaxAmount = 0
    self.capBeneficiary = empty(address)
    self.capConsumed = False
    self.capStartBalance = 0
    self.capStartReserved = 0


@view
@external
def availableBalance(_token: address) -> uint256:
    """
    @notice Returns the token balance that is not reserved by live commitments.
    @dev Saturates at zero when recorded reservations equal or exceed the actual token balance.
    @param _token The ERC20 token to inspect.
    @return The amount currently available for transfers or new capabilities.
    """
    balance: uint256 = self._getTokenBalance(_token)
    amountReserved: uint256 = self.reserved[_token]
    if amountReserved >= balance:
        return 0
    return balance - amountReserved


@view
@external
def attachment(_attachmentId: uint256) -> w3.AttachmentView:
    """
    @notice Returns the stored dependency and lifecycle data for an attachment.
    @param _attachmentId The attachment identifier assigned when the extender version was added.
    @return The attachment record, or an empty record when the identifier does not exist.
    """
    return self.attachments[_attachmentId]


@view
@external
def currentRoute(_selector: bytes4) -> w3.RouteView:
    """
    @notice Returns the active route currently published for an extender selector.
    @param _selector The extender function selector to resolve.
    @return The active route record, or an empty record when the selector is not published.
    """
    attachmentId: uint256 = self.currentRouteIds[_selector]
    return self.routes[attachmentId][_selector]


@view
@external
def commitment(_commitmentId: bytes32) -> w3.CommitmentView:
    """
    @notice Returns the stored state and settlement terms for a commitment.
    @param _commitmentId The unique commitment identifier.
    @return The commitment record, or an empty record when the identifier does not exist.
    """
    return self.commitments[_commitmentId]


#################
# Configuration #
#################


@external
def replaceConfig(_newConfig: address):
    """
    @notice Replaces the policy Config used to authorize direct transfers and extender sessions.
    @dev Owner-only and idle-only. The candidate must be a contract that returns the exact interface marker and identifies this wallet from bounded-gas static probes.
    @param _newConfig The wallet-bound Config contract to install.
    """
    assert self.currentPhase == PHASE_IDLE
    assert msg.sender == OWNER
    self.currentPhase = PHASE_ADMIN
    assert _newConfig.is_contract

    # probe rather than using the interface directly so malformed configs fail closed
    markerReturn: Bytes[33] = self._getConfigResponse(_newConfig, method_id("configInterfaceMarker()"))
    assert abi_decode(markerReturn, bytes32) == CONFIG_INTERFACE_MARKER

    walletReturn: Bytes[33] = self._getConfigResponse(_newConfig, method_id("wallet()"))
    assert abi_decode(walletReturn, address) == self

    self.config = _newConfig
    self.currentPhase = PHASE_IDLE


##################
# Transfer Funds #
##################


@external
def transferFunds(_recipient: address, _token: address, _amount: uint256):
    """
    @notice Transfers an exact amount of unreserved ERC20 tokens after Config authorization.
    @dev Captures the active Config, enters PHASE_DIRECT, checks the original caller and transfer terms, excludes reserved funds, and requires a canonical True token response.
    @param _recipient The address receiving the tokens.
    @param _token The ERC20 token to transfer.
    @param _amount The exact token amount to transfer.
    """
    assert self.currentPhase == PHASE_IDLE
    candidate: address = self.config
    assert candidate != empty(address)
    self.currentPhase = PHASE_DIRECT
    assert self._authorizedTransfer(candidate, msg.sender, _recipient, _token, _amount)
    balance: uint256 = self._getTokenBalance(_token)
    assert _amount <= balance - min(balance, self.reserved[_token])
    self._strictErc20Call(
        _token,
        concat(method_id("transfer(address,uint256)"), abi_encode(_recipient, _amount)),
    )
    self.currentPhase = PHASE_IDLE


###############
# Attachments #
###############


@external
def attachExtender(_request: w3.AttachmentRequest):
    """
    @notice Adds a new versioned extender attachment and publishes its routes.
    @dev Owner-only with a Config installed. Validates dependencies and unique routes, pins dependency codehashes, and places the predecessor in drain-only mode while preserving only its declared exit routes.
    @param _request The family, version, dependencies, routes, and drain-only exit selectors to attach.
    """
    assert self.currentPhase == PHASE_IDLE
    assert msg.sender == OWNER
    assert self.config != empty(address)
    self.currentPhase = PHASE_ADMIN

    assert self.attachmentCount < MAX_ATTACHMENTS
    assert _request.familyId != empty(bytes32)
    assert _request.version != 0
    assert _request.extender.is_contract
    assert len(_request.routes) != 0
    if _request.lego != empty(address):
        assert _request.lego.is_contract
    if _request.authorityTarget != empty(address):
        assert _request.authorityTarget.is_contract
    if _request.x402Helper != empty(address):
        assert _request.x402Helper.is_contract

    predecessorId: uint256 = self.currentFamilyAttachment[_request.familyId]
    if predecessorId != 0:
        predecessor: w3.AttachmentView = self.attachments[predecessorId]
        assert _request.version > predecessor.version
        assert _request.extender != predecessor.extender

    for i: uint256 in range(len(_request.routes), bound = 8):
        route: w3.RouteSpec = _request.routes[i]
        assert route.selector != empty(bytes4)
        assert route.actionId != 0
        assert route.effectClass >= EFFECT_SPEND and route.effectClass <= EFFECT_AUTHORITY
        assert route.consumerMode >= CONSUMER_LEGO and route.consumerMode <= CONSUMER_NONE
        if route.consumerMode == CONSUMER_LEGO:
            assert _request.lego != empty(address)
        for j: uint256 in range(8):
            if j < i:
                assert _request.routes[j].selector != route.selector
                assert _request.routes[j].actionId != route.actionId
        existingRoute: uint256 = self.currentRouteIds[route.selector]
        assert existingRoute == 0 or existingRoute == predecessorId

    for i: uint256 in range(len(_request.exitSelectors), bound = 4):
        exitSelector: bytes4 = _request.exitSelectors[i]
        found: bool = False
        for j: uint256 in range(len(_request.routes), bound = 8):
            if _request.routes[j].selector == exitSelector:
                found = True
        assert found
        for j: uint256 in range(4):
            if j < i:
                assert _request.exitSelectors[j] != exitSelector

    if predecessorId != 0:
        predecessor: w3.AttachmentView = self.attachments[predecessorId]
        for i: uint256 in range(8):
            if i < convert(predecessor.routeCount, uint256):
                oldSelector: bytes4 = self.routeSelectors[predecessorId][i]
                if self.currentRouteIds[oldSelector] == predecessorId:
                    self.currentRouteIds[oldSelector] = 0
        self.attachments[predecessorId].lifecycle = LIFECYCLE_DRAIN_ONLY

    attachmentId: uint256 = self.attachmentCount + 1
    self.attachmentCount = attachmentId
    self.attachments[attachmentId] = w3.AttachmentView(
        familyId = _request.familyId,
        version = _request.version,
        lifecycle = LIFECYCLE_ACTIVE,
        extender = _request.extender,
        extenderCodehash = _request.extender.codehash,
        lego = _request.lego,
        legoCodehash = _request.lego.codehash,
        authorityTarget = _request.authorityTarget,
        authorityTargetCodehash = _request.authorityTarget.codehash,
        x402Helper = _request.x402Helper,
        x402HelperCodehash = _request.x402Helper.codehash,
        routeCount = convert(len(_request.routes), uint8),
        exitCount = convert(len(_request.exitSelectors), uint8),
    )
    for i: uint256 in range(len(_request.routes), bound = 8):
        route: w3.RouteSpec = _request.routes[i]
        self.routeSelectors[attachmentId][i] = route.selector
        self.routes[attachmentId][route.selector] = w3.RouteView(
            attachmentId = attachmentId,
            actionId = route.actionId,
            effectClass = route.effectClass,
            consumerMode = route.consumerMode,
            isExit = False,
        )
        self.currentRouteIds[route.selector] = attachmentId
    for i: uint256 in range(len(_request.exitSelectors), bound = 4):
        self.routes[attachmentId][_request.exitSelectors[i]].isExit = True

    self.currentFamilyAttachment[_request.familyId] = attachmentId
    self.currentPhase = PHASE_IDLE
    log AttachmentAdded(
        attachmentId = attachmentId,
        familyId = _request.familyId,
        version = _request.version,
        extender = _request.extender,
    )


@internal
def _dispatch(
    _attachmentId: uint256,
    _typedExtenderCalldata: Bytes[1024],
    _drainOnly: bool,
):
    """
    @notice Executes one registered extender route inside the wallet capability state machine.
    @dev Captures caller, Config, route, calldata hash, and nonce; checks dependency codehashes; invokes the dynamic extender selector; enforces session and capability postconditions; revokes spend approval; checks balance and reservation bounds; then clears transient state.
    @param _attachmentId The attachment whose route will execute.
    @param _typedExtenderCalldata The complete ABI-encoded extender function call.
    @param _drainOnly Whether execution must target an exit route on a superseded attachment.
    """
    assert self.currentPhase == PHASE_IDLE
    candidate: address = self.config
    assert candidate != empty(address)
    assert len(_typedExtenderCalldata) >= 4
    selector: bytes4 = convert(slice(_typedExtenderCalldata, 0, 4), bytes4)
    record: w3.AttachmentView = self.attachments[_attachmentId]
    route: w3.RouteView = self.routes[_attachmentId][selector]
    assert route.attachmentId == _attachmentId
    if _drainOnly:
        assert record.lifecycle == LIFECYCLE_DRAIN_ONLY
        assert route.isExit
    else:
        assert record.lifecycle == LIFECYCLE_ACTIVE
        assert self.currentRouteIds[selector] == _attachmentId

    self.currentPhase = PHASE_DISPATCHING
    self.frameCaller = msg.sender
    self.frameConfig = candidate
    self.frameAttachmentId = _attachmentId
    self.frameSelector = selector
    self.frameCalldataHash = keccak256(_typedExtenderCalldata)
    self.frameActionId = route.actionId
    self.sessionNonce += 1
    self.frameNonce = self.sessionNonce
    self.frameOpened = False
    self._requireDependencyCodehashes(_attachmentId)

    # attached selectors are dynamic, so no single typed extender interface can dispatch them
    raw_call(record.extender, _typedExtenderCalldata, max_outsize = 0)
    assert self.frameOpened and self.currentPhase == PHASE_ACTIVE
    if route.consumerMode == CONSUMER_NONE:
        assert not self.capConsumed
    else:
        assert self.capConsumed
    self.currentPhase = PHASE_SETTLING

    if self.capEffectClass == EFFECT_SPEND and self.capConsumer != empty(address):
        self._strictErc20Call(
            self.capResource,
            concat(
                method_id("approve(address,uint256)"),
                abi_encode(self.capConsumer, convert(0, uint256)),
            ),
        )
        finalBalance: uint256 = self._getTokenBalance(self.capResource)
        if finalBalance < self.capStartBalance:
            assert self.capStartBalance - finalBalance <= self.capMaxAmount
        assert self.reserved[self.capResource] == self.capStartReserved
        assert self._getTokenAllowance(self.capResource, self, self.capConsumer) == 0

    self._clearSession()
    self.currentPhase = PHASE_IDLE


@external
def execute(_typedExtenderCalldata: Bytes[1024]):
    """
    @notice Executes the currently active attachment published for the calldata selector.
    @dev Resolves the first four calldata bytes through currentRouteIds and dispatches only an active route.
    @param _typedExtenderCalldata The complete ABI-encoded extender function call.
    """
    assert len(_typedExtenderCalldata) >= 4
    selector: bytes4 = convert(slice(_typedExtenderCalldata, 0, 4), bytes4)
    attachmentId: uint256 = self.currentRouteIds[selector]
    assert attachmentId != 0
    self._dispatch(attachmentId, _typedExtenderCalldata, False)


@external
def executeAttached(_attachmentId: uint256, _typedExtenderCalldata: Bytes[1024]):
    """
    @notice Executes a declared exit route on a superseded drain-only attachment.
    @dev Allows positions created by an old extender version to be unwound after a successor takes over its active selectors.
    @param _attachmentId The superseded attachment that owns the exit route.
    @param _typedExtenderCalldata The complete ABI-encoded exit function call.
    """
    self._dispatch(_attachmentId, _typedExtenderCalldata, True)


############
# Sessions #
############


@external
def openSession(_request: w3.ActionEnvelope):
    """
    @notice Opens the capability session proposed by the extender currently being dispatched.
    @dev Extender-only during PHASE_DISPATCHING. Verifies route semantics, pinned dependencies, and Config authorization; snapshots the authorized envelope; and grants a bounded temporary ERC20 allowance when a spend consumer is required.
    @param _request The action, effect, consumer, target, resource, amount, beneficiary, and action-data commitment proposed by the extender.
    """
    assert self.currentPhase == PHASE_DISPATCHING
    assert not self.frameOpened
    attachmentId: uint256 = self.frameAttachmentId
    record: w3.AttachmentView = self.attachments[attachmentId]
    route: w3.RouteView = self.routes[attachmentId][self.frameSelector]
    assert msg.sender == record.extender
    assert _request.actionId == self.frameActionId
    assert self.frameActionId == route.actionId
    assert _request.effectClass == route.effectClass
    if route.consumerMode == CONSUMER_LEGO:
        assert _request.consumer == record.lego
    else:
        assert _request.consumer == empty(address)
    if _request.effectClass == EFFECT_SPEND:
        assert _request.maxAmount != 0
    self._requireDependencyCodehashes(attachmentId)

    semanticHash: bytes32 = self._semanticHash(_request)
    assert self._authorizedSession(
        self.frameConfig,
        self.frameCaller,
        attachmentId,
        self.frameSelector,
        _request,
    )

    self.capActionId = _request.actionId
    self.capEffectClass = _request.effectClass
    self.capConsumer = _request.consumer
    self.capTarget = _request.target
    self.capSemanticHash = semanticHash
    self.capResource = _request.resource
    self.capMaxAmount = _request.maxAmount
    self.capBeneficiary = _request.beneficiary
    self.capConsumed = False
    self.frameOpened = True

    if _request.effectClass == EFFECT_SPEND and _request.consumer != empty(address):
        startBalance: uint256 = self._getTokenBalance(_request.resource)
        startReserved: uint256 = self.reserved[_request.resource]
        assert startBalance > startReserved
        assert _request.maxAmount <= startBalance - startReserved
        assert self._getTokenAllowance(_request.resource, self, _request.consumer) == 0
        self.capStartBalance = startBalance
        self.capStartReserved = startReserved
        self._strictErc20Call(
            _request.resource,
            concat(
                method_id("approve(address,uint256)"),
                abi_encode(_request.consumer, _request.maxAmount),
            ),
        )

    self.currentPhase = PHASE_ACTIVE
    log SessionOpened(
        attachmentId = attachmentId,
        selector = self.frameSelector,
        calldataHash = self.frameCalldataHash,
        semanticHash = semanticHash,
        nonce = self.frameNonce,
    )


@external
def consumeCapability(_actualEnvelope: w3.ActionEnvelope):
    """
    @notice Marks a lego-consumer capability as consumed after validating the actual action.
    @dev Callable only by the authorized nonzero consumer during PHASE_ACTIVE. Every envelope field and its semantic hash must exactly match the capability opened for this frame.
    @param _actualEnvelope The action envelope describing what the lego is actually about to execute.
    """
    assert self.currentPhase == PHASE_ACTIVE
    assert self.frameOpened
    assert self.routes[self.frameAttachmentId][self.frameSelector].consumerMode == CONSUMER_LEGO
    assert self.capConsumer != empty(address)
    assert msg.sender == self.capConsumer
    assert not self.capConsumed
    assert _actualEnvelope.actionId == self.capActionId
    assert _actualEnvelope.effectClass == self.capEffectClass
    assert _actualEnvelope.consumer == self.capConsumer
    assert _actualEnvelope.target == self.capTarget
    assert _actualEnvelope.resource == self.capResource
    assert _actualEnvelope.maxAmount == self.capMaxAmount
    assert _actualEnvelope.beneficiary == self.capBeneficiary
    assert self._semanticHash(_actualEnvelope) == self.capSemanticHash
    self.capConsumed = True


#################
# Debt Operator #
#################


@external
def setDebtOperator(_enabled: bool, _actualEnvelope: w3.ActionEnvelope):
    """
    @notice Enables or disables the attachment's lego as an operator on its pinned debt authority target.
    @dev Extender-only core capability. Uses action 13 for enable and 14 for disable, verifies the complete authority envelope and action-data hash, consumes the capability, then calls the pinned operator protocol.
    @param _enabled Whether the lego should receive or lose operator authority.
    @param _actualEnvelope The authority action envelope that must match the opened capability.
    """
    assert self.currentPhase == PHASE_ACTIVE
    assert self.frameOpened and msg.sender == self.attachments[self.frameAttachmentId].extender
    assert not self.capConsumed
    assert self.routes[self.frameAttachmentId][self.frameSelector].consumerMode == CONSUMER_CORE
    expectedAction: uint16 = 13 if _enabled else 14
    record: w3.AttachmentView = self.attachments[self.frameAttachmentId]
    assert self.capActionId == expectedAction
    assert self.capEffectClass == EFFECT_AUTHORITY
    assert self.capConsumer == empty(address)
    assert self.capTarget == record.authorityTarget
    assert self.capResource == empty(address)
    assert self.capMaxAmount == 0
    assert self.capBeneficiary == record.lego
    assert _actualEnvelope.actionId == expectedAction
    assert _actualEnvelope.effectClass == EFFECT_AUTHORITY
    assert _actualEnvelope.consumer == empty(address)
    assert _actualEnvelope.target == record.authorityTarget
    assert _actualEnvelope.resource == empty(address)
    assert _actualEnvelope.maxAmount == 0
    assert _actualEnvelope.beneficiary == record.lego
    expectedDataHash: bytes32 = keccak256(
        abi_encode(record.authorityTarget, record.lego, _enabled)
    )
    assert _actualEnvelope.actionDataHash == expectedDataHash
    assert self._semanticHash(_actualEnvelope) == self.capSemanticHash
    self._requireDependencyCodehashes(self.frameAttachmentId)
    self.capConsumed = True
    extcall IOperatorProtocolV3(record.authorityTarget).setOperator(record.lego, _enabled)


###############
# Commitments #
###############


# external exact


@external
def createExternalExact(_fields: w3.ExternalExactFields, _actualEnvelope: w3.ActionEnvelope):
    """
    @notice Creates a token reservation backing one exact externally pulled payment.
    @dev Extender-only action 20 core capability. Verifies the pinned x402 helper, helper-derived digest, envelope, replay keys, time ordering, available balance, and dependency codehashes before reserving funds and making the digest eligible for ERC1271 validation.
    @param _fields The commitment identifier, token, exact amount, destination, validity window, nonce, helper, and helper-derived digest.
    @param _actualEnvelope The spend action envelope that must exactly match the opened capability and commitment fields.
    """
    assert self.currentPhase == PHASE_ACTIVE
    attachmentId: uint256 = self.frameAttachmentId
    record: w3.AttachmentView = self.attachments[attachmentId]
    assert self.frameOpened and msg.sender == record.extender
    assert not self.capConsumed
    assert self.routes[attachmentId][self.frameSelector].consumerMode == CONSUMER_CORE
    assert self.capActionId == 20 and _actualEnvelope.actionId == 20
    assert self.capEffectClass == EFFECT_SPEND and _actualEnvelope.effectClass == EFFECT_SPEND
    assert self.capConsumer == empty(address) and _actualEnvelope.consumer == empty(address)
    assert record.x402Helper != empty(address)
    assert _fields.helper == record.x402Helper
    assert _fields.token == staticcall IX402Helper(_fields.helper).token()
    derivedDigest: bytes32 = staticcall IX402Helper(_fields.helper).digest(
        self,
        _fields.destination,
        _fields.amount,
        _fields.validAfter,
        _fields.validBefore,
        _fields.nonce,
    )
    assert _fields.digest == derivedDigest
    expectedDataHash: bytes32 = keccak256(
        abi_encode(
            _fields.commitmentId,
            _fields.token,
            _fields.amount,
            _fields.destination,
            _fields.validAfter,
            _fields.validBefore,
            _fields.nonce,
            _fields.helper,
            _fields.digest,
        )
    )
    assert _actualEnvelope.target == _fields.token
    assert _actualEnvelope.resource == _fields.token
    assert _actualEnvelope.maxAmount == _fields.amount
    assert _actualEnvelope.beneficiary == _fields.destination
    assert _actualEnvelope.actionDataHash == expectedDataHash
    assert self.capTarget == _actualEnvelope.target
    assert self.capResource == _actualEnvelope.resource
    assert self.capMaxAmount == _actualEnvelope.maxAmount
    assert self.capBeneficiary == _actualEnvelope.beneficiary
    assert self._semanticHash(_actualEnvelope) == self.capSemanticHash
    assert _fields.amount != 0 and _fields.destination != empty(address)
    assert _fields.validBefore > _fields.validAfter
    assert not self.usedCommitmentId[_fields.commitmentId]
    assert not self.usedExternalDigest[_fields.digest]
    assert not self.usedExternalNonce[_fields.nonce]
    assert not staticcall IX402Helper(_fields.helper).authorizationUsed(self, _fields.nonce)
    balance: uint256 = self._getTokenBalance(_fields.token)
    assert balance > self.reserved[_fields.token]
    assert _fields.amount <= balance - self.reserved[_fields.token]
    self._requireDependencyCodehashes(attachmentId)

    self.capConsumed = True
    self.usedCommitmentId[_fields.commitmentId] = True
    self.usedExternalDigest[_fields.digest] = True
    self.usedExternalNonce[_fields.nonce] = True
    self.digestCommitmentId[_fields.digest] = _fields.commitmentId
    self.reserved[_fields.token] += _fields.amount
    self.commitments[_fields.commitmentId] = w3.CommitmentView(
        mode = COMMITMENT_EXTERNAL_EXACT,
        state = COMMITMENT_LIVE,
        token = _fields.token,
        totalAmount = _fields.amount,
        remainingAmount = _fields.amount,
        destination = _fields.destination,
        settlementOperator = empty(address),
        digest = _fields.digest,
        validAfter = _fields.validAfter,
        validBefore = _fields.validBefore,
        nonce = _fields.nonce,
        helper = _fields.helper,
        helperCodehash = record.x402HelperCodehash,
    )


# reserved transfer


@external
def createReservedTransfer(_fields: w3.ReservedTransferFields, _actualEnvelope: w3.ActionEnvelope):
    """
    @notice Creates a reservation that an appointed operator can settle to one destination in installments.
    @dev Extender-only action 21 core capability. Verifies the complete envelope, unique commitment identifier, nonzero terms, and available balance before reserving the total amount.
    @param _fields The commitment identifier, token, total amount, destination, and authorized settlement operator.
    @param _actualEnvelope The spend action envelope that must exactly match the opened capability and reservation terms.
    """
    assert self.currentPhase == PHASE_ACTIVE
    record: w3.AttachmentView = self.attachments[self.frameAttachmentId]
    assert self.frameOpened and msg.sender == record.extender
    assert not self.capConsumed
    assert self.routes[self.frameAttachmentId][self.frameSelector].consumerMode == CONSUMER_CORE
    assert self.capActionId == 21 and _actualEnvelope.actionId == 21
    assert self.capEffectClass == EFFECT_SPEND and _actualEnvelope.effectClass == EFFECT_SPEND
    assert self.capConsumer == empty(address) and _actualEnvelope.consumer == empty(address)
    expectedDataHash: bytes32 = keccak256(
        abi_encode(
            _fields.commitmentId,
            _fields.token,
            _fields.totalAmount,
            _fields.destination,
            _fields.settlementOperator,
        )
    )
    assert _actualEnvelope.target == _fields.token
    assert _actualEnvelope.resource == _fields.token
    assert _actualEnvelope.maxAmount == _fields.totalAmount
    assert _actualEnvelope.beneficiary == _fields.destination
    assert _actualEnvelope.actionDataHash == expectedDataHash
    assert self.capTarget == _actualEnvelope.target
    assert self.capResource == _actualEnvelope.resource
    assert self.capMaxAmount == _actualEnvelope.maxAmount
    assert self.capBeneficiary == _actualEnvelope.beneficiary
    assert self._semanticHash(_actualEnvelope) == self.capSemanticHash
    assert _fields.totalAmount != 0 and _fields.destination != empty(address) and _fields.settlementOperator != empty(address)
    assert not self.usedCommitmentId[_fields.commitmentId]
    balance: uint256 = self._getTokenBalance(_fields.token)
    assert balance > self.reserved[_fields.token]
    assert _fields.totalAmount <= balance - self.reserved[_fields.token]

    self.capConsumed = True
    self.usedCommitmentId[_fields.commitmentId] = True
    self.reserved[_fields.token] += _fields.totalAmount
    self.commitments[_fields.commitmentId] = w3.CommitmentView(
        mode = COMMITMENT_RESERVED_TRANSFER,
        state = COMMITMENT_LIVE,
        token = _fields.token,
        totalAmount = _fields.totalAmount,
        remainingAmount = _fields.totalAmount,
        destination = _fields.destination,
        settlementOperator = _fields.settlementOperator,
        digest = empty(bytes32),
        validAfter = 0,
        validBefore = 0,
        nonce = empty(bytes32),
        helper = empty(address),
        helperCodehash = empty(bytes32),
    )


# sync external pull


@external
def syncExternalPull(_commitmentId: bytes32):
    """
    @notice Finalizes a live external-exact commitment after its helper reports the authorization was used.
    @dev Permissionless and idle-only. Rechecks the pinned helper codehash, marks the commitment used, zeroes its remaining amount, and releases the full reservation.
    @param _commitmentId The external-exact commitment to synchronize.
    """
    assert self.currentPhase == PHASE_IDLE
    self.currentPhase = PHASE_COMMITMENT
    commitment: w3.CommitmentView = self.commitments[_commitmentId]
    assert commitment.mode == COMMITMENT_EXTERNAL_EXACT
    assert commitment.state == COMMITMENT_LIVE
    assert commitment.helper.codehash == commitment.helperCodehash
    assert staticcall IX402Helper(commitment.helper).authorizationUsed(
        self, commitment.nonce
    )
    self.commitments[_commitmentId].state = COMMITMENT_USED
    self.commitments[_commitmentId].remainingAmount = 0
    self.reserved[commitment.token] -= commitment.totalAmount
    self.currentPhase = PHASE_IDLE


# expire external exact


@external
def expireExternalExact(_commitmentId: bytes32):
    """
    @notice Expires an unused external-exact commitment after its validity window ends.
    @dev Permissionless and idle-only. Requires the pinned helper to report the nonce unused, then marks the commitment expired and releases the full reservation.
    @param _commitmentId The external-exact commitment to expire.
    """
    assert self.currentPhase == PHASE_IDLE
    self.currentPhase = PHASE_COMMITMENT
    commitment: w3.CommitmentView = self.commitments[_commitmentId]
    assert commitment.mode == COMMITMENT_EXTERNAL_EXACT
    assert commitment.state == COMMITMENT_LIVE
    assert block.timestamp >= commitment.validBefore
    assert commitment.helper.codehash == commitment.helperCodehash
    assert not staticcall IX402Helper(commitment.helper).authorizationUsed(
        self, commitment.nonce
    )
    self.commitments[_commitmentId].state = COMMITMENT_EXPIRED
    self.commitments[_commitmentId].remainingAmount = 0
    self.reserved[commitment.token] -= commitment.totalAmount
    self.currentPhase = PHASE_IDLE


# settle reserved transfer


@external
def settleReservedTransfer(_commitmentId: bytes32, _amount: uint256):
    """
    @notice Settles part or all of a live reserved-transfer commitment.
    @dev Idle-only and callable only by the appointed settlement operator. Decreases the remaining amount and reservation, marks fully paid commitments settled, and transfers the exact token amount to the fixed destination.
    @param _commitmentId The reserved-transfer commitment to settle.
    @param _amount The nonzero token amount to pay, bounded by the remaining commitment amount.
    """
    assert self.currentPhase == PHASE_IDLE
    self.currentPhase = PHASE_COMMITMENT
    commitment: w3.CommitmentView = self.commitments[_commitmentId]
    assert commitment.mode == COMMITMENT_RESERVED_TRANSFER
    assert commitment.state == COMMITMENT_LIVE
    assert msg.sender == commitment.settlementOperator
    assert _amount != 0 and _amount <= commitment.remainingAmount
    remaining: uint256 = commitment.remainingAmount - _amount
    self.commitments[_commitmentId].remainingAmount = remaining
    self.reserved[commitment.token] -= _amount
    if remaining == 0:
        self.commitments[_commitmentId].state = COMMITMENT_SETTLED
    self._strictErc20Call(
        commitment.token,
        concat(
            method_id("transfer(address,uint256)"),
            abi_encode(commitment.destination, _amount),
        ),
    )
    self.currentPhase = PHASE_IDLE


# refund reserved transfer


@external
def refundReservedTransfer(_commitmentId: bytes32):
    """
    @notice Cancels a live reserved-transfer commitment and releases its unpaid reservation.
    @dev Owner-only and idle-only. No token transfer is needed because the reserved funds never left the wallet.
    @param _commitmentId The reserved-transfer commitment to refund.
    """
    assert self.currentPhase == PHASE_IDLE
    assert msg.sender == OWNER
    self.currentPhase = PHASE_COMMITMENT
    commitment: w3.CommitmentView = self.commitments[_commitmentId]
    assert commitment.mode == COMMITMENT_RESERVED_TRANSFER
    assert commitment.state == COMMITMENT_LIVE
    self.commitments[_commitmentId].remainingAmount = 0
    self.commitments[_commitmentId].state = COMMITMENT_REFUNDED
    self.reserved[commitment.token] -= commitment.remainingAmount
    self.currentPhase = PHASE_IDLE


##############
# Signatures #
##############


@view
@external
def isValidSignature(_digest: bytes32, _signature: Bytes[256]) -> bytes4:
    """
    @notice Reports ERC1271 validity for a live external-exact payment digest.
    @dev Ignores signature bytes because validity comes from the preauthorized commitment. Returns valid only while idle, strictly inside the time window, when called by the committed token, and while the digest maps to the same live commitment.
    @param _digest The digest presented for contract-signature validation.
    @param _signature Unused signature bytes supplied by the ERC1271 caller.
    @return The ERC1271 magic value when valid, otherwise the invalid sentinel.
    """
    if self.currentPhase != PHASE_IDLE:
        return ERC1271_INVALID
    commitmentId: bytes32 = self.digestCommitmentId[_digest]
    commitment: w3.CommitmentView = self.commitments[commitmentId]
    if commitment.mode != COMMITMENT_EXTERNAL_EXACT:
        return ERC1271_INVALID
    if commitment.state != COMMITMENT_LIVE or commitment.digest != _digest:
        return ERC1271_INVALID
    if msg.sender != commitment.token:
        return ERC1271_INVALID
    if block.timestamp <= commitment.validAfter or block.timestamp >= commitment.validBefore:
        return ERC1271_INVALID
    return ERC1271_MAGIC


@pure
@external
def supportsInterface(_interfaceId: bytes4) -> bool:
    """
    @notice Reports support for ERC165 and ERC1271 interface identifiers.
    @param _interfaceId The interface identifier to query.
    @return True for ERC165 or ERC1271, and False for all other identifiers including 0xffffffff.
    """
    if _interfaceId == 0xffffffff:
        return False
    return _interfaceId == ERC165_INTERFACE or _interfaceId == ERC1271_MAGIC
