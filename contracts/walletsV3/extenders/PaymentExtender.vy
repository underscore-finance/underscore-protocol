# @version 0.4.3

from contracts.walletsV3.interfaces import IUserWalletV3
from contracts.walletsV3.interfaces import IX402Helper
from contracts.walletsV3.types import WalletV3Types as w3


HELPER: public(immutable(address))
EXTENDER_MARKER: constant(bytes32) = keccak256("underscore.wallet-v3-payment-extender-poc-v1")


@deploy
def __init__(helper: address):
    assert helper.is_contract
    HELPER = helper


@view
@external
def walletV3ExtenderMarker() -> bytes32:
    return EXTENDER_MARKER


@external
def authorizeExternalExact(
    wallet: address,
    commitmentId: bytes32,
    token: address,
    amount: uint256,
    destination: address,
    validAfter: uint256,
    validBefore: uint256,
    nonce: bytes32,
):
    digest: bytes32 = staticcall IX402Helper(HELPER).digest(
        wallet,
        destination,
        amount,
        validAfter,
        validBefore,
        nonce,
    )
    fields: w3.ExternalExactFields = w3.ExternalExactFields(
        commitmentId=commitmentId,
        token=token,
        amount=amount,
        destination=destination,
        validAfter=validAfter,
        validBefore=validBefore,
        nonce=nonce,
        helper=HELPER,
        digest=digest,
    )
    request: w3.ActionEnvelope = w3.ActionEnvelope(
        actionId=20,
        effectClass=1,
        consumer=empty(address),
        target=token,
        resource=token,
        maxAmount=amount,
        beneficiary=destination,
        actionDataHash=keccak256(
            abi_encode(
                commitmentId,
                token,
                amount,
                destination,
                validAfter,
                validBefore,
                nonce,
                HELPER,
                digest,
            )
        ),
    )
    extcall IUserWalletV3(wallet).openSession(request)
    extcall IUserWalletV3(wallet).createExternalExact(fields, request)


@external
def authorizeReservedTransfer(
    wallet: address,
    commitmentId: bytes32,
    token: address,
    totalAmount: uint256,
    destination: address,
    settlementOperator: address,
):
    fields: w3.ReservedTransferFields = w3.ReservedTransferFields(
        commitmentId=commitmentId,
        token=token,
        totalAmount=totalAmount,
        destination=destination,
        settlementOperator=settlementOperator,
    )
    request: w3.ActionEnvelope = w3.ActionEnvelope(
        actionId=21,
        effectClass=1,
        consumer=empty(address),
        target=token,
        resource=token,
        maxAmount=totalAmount,
        beneficiary=destination,
        actionDataHash=keccak256(
            abi_encode(
                commitmentId,
                token,
                totalAmount,
                destination,
                settlementOperator,
            )
        ),
    )
    extcall IUserWalletV3(wallet).openSession(request)
    extcall IUserWalletV3(wallet).createReservedTransfer(fields, request)
