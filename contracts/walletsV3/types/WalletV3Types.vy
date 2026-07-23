# @version 0.4.3


struct RouteSpec:
    selector: bytes4
    actionId: uint16
    effectClass: uint8
    consumerMode: uint8


struct AttachmentRequest:
    familyId: bytes32
    version: uint32
    extender: address
    lego: address
    authorityTarget: address
    x402Helper: address
    routes: DynArray[RouteSpec, 8]
    exitSelectors: DynArray[bytes4, 4]


struct ActionEnvelope:
    actionId: uint16
    effectClass: uint8
    consumer: address
    target: address
    resource: address
    maxAmount: uint256
    beneficiary: address
    actionDataHash: bytes32


struct TokenPolicy:
    token: address
    maxTransferAmount: uint256
    maxSessionAmount: uint256


struct ActionPolicy:
    actionId: uint16
    maxAmount: uint256


struct AttachmentView:
    familyId: bytes32
    version: uint32
    lifecycle: uint8
    extender: address
    extenderCodehash: bytes32
    lego: address
    legoCodehash: bytes32
    authorityTarget: address
    authorityTargetCodehash: bytes32
    x402Helper: address
    x402HelperCodehash: bytes32
    routeCount: uint8
    exitCount: uint8


struct RouteView:
    attachmentId: uint256
    actionId: uint16
    effectClass: uint8
    consumerMode: uint8
    isExit: bool


struct ExternalExactFields:
    commitmentId: bytes32
    token: address
    amount: uint256
    destination: address
    validAfter: uint256
    validBefore: uint256
    nonce: bytes32
    helper: address
    digest: bytes32


struct ReservedTransferFields:
    commitmentId: bytes32
    token: address
    totalAmount: uint256
    destination: address
    settlementOperator: address


struct CommitmentView:
    mode: uint8
    state: uint8
    token: address
    totalAmount: uint256
    remainingAmount: uint256
    destination: address
    settlementOperator: address
    digest: bytes32
    validAfter: uint256
    validBefore: uint256
    nonce: bytes32
    helper: address
    helperCodehash: bytes32
