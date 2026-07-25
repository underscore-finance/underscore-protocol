# @version 0.4.3

from contracts.poc.userWallet.interfaces import IUserWalletV3
from contracts.poc.userWallet.interfaces import IDebtLegoV3
from contracts.poc.userWallet.types import WalletV3Types as w3


LEGO: public(immutable(address))
OPERATOR_PROTOCOL: public(immutable(address))
EXTENDER_MARKER: constant(bytes32) = keccak256("underscore.wallet-v3-debt-extender-poc-v1")


@deploy
def __init__(lego: address, operatorProtocol: address):
    assert lego.is_contract and operatorProtocol.is_contract
    LEGO = lego
    OPERATOR_PROTOCOL = operatorProtocol


@view
@external
def walletV3ExtenderMarker() -> bytes32:
    return EXTENDER_MARKER


@external
def borrow(wallet: address, protocol: address, asset: address, amount: uint256):
    actionDataHash: bytes32 = keccak256(abi_encode(protocol, asset, amount, wallet))
    request: w3.ActionEnvelope = w3.ActionEnvelope(
        actionId=10,
        effectClass=2,
        consumer=LEGO,
        target=protocol,
        resource=asset,
        maxAmount=amount,
        beneficiary=wallet,
        actionDataHash=actionDataHash,
    )
    extcall IUserWalletV3(wallet).openSession(request)
    extcall IDebtLegoV3(LEGO).borrow(wallet, protocol, asset, amount)


@external
def repayClose(wallet: address, protocol: address, asset: address, maxAmount: uint256):
    actionDataHash: bytes32 = keccak256(abi_encode(protocol, asset, maxAmount, wallet))
    request: w3.ActionEnvelope = w3.ActionEnvelope(
        actionId=11,
        effectClass=1,
        consumer=LEGO,
        target=protocol,
        resource=asset,
        maxAmount=maxAmount,
        beneficiary=wallet,
        actionDataHash=actionDataHash,
    )
    extcall IUserWalletV3(wallet).openSession(request)
    extcall IDebtLegoV3(LEGO).repayClose(wallet, protocol, asset, maxAmount)


@external
def removeCollateral(wallet: address, protocol: address, asset: address, amount: uint256):
    actionDataHash: bytes32 = keccak256(abi_encode(protocol, asset, amount, wallet))
    request: w3.ActionEnvelope = w3.ActionEnvelope(
        actionId=12,
        effectClass=3,
        consumer=LEGO,
        target=protocol,
        resource=asset,
        maxAmount=amount,
        beneficiary=wallet,
        actionDataHash=actionDataHash,
    )
    extcall IUserWalletV3(wallet).openSession(request)
    extcall IDebtLegoV3(LEGO).removeCollateral(wallet, protocol, asset, amount)


@external
def grantOperator(wallet: address):
    actionDataHash: bytes32 = keccak256(abi_encode(OPERATOR_PROTOCOL, LEGO, True))
    request: w3.ActionEnvelope = w3.ActionEnvelope(
        actionId=13,
        effectClass=4,
        consumer=empty(address),
        target=OPERATOR_PROTOCOL,
        resource=empty(address),
        maxAmount=0,
        beneficiary=LEGO,
        actionDataHash=actionDataHash,
    )
    extcall IUserWalletV3(wallet).openSession(request)
    extcall IUserWalletV3(wallet).setDebtOperator(True, request)


@external
def revokeOperator(wallet: address):
    actionDataHash: bytes32 = keccak256(abi_encode(OPERATOR_PROTOCOL, LEGO, False))
    request: w3.ActionEnvelope = w3.ActionEnvelope(
        actionId=14,
        effectClass=4,
        consumer=empty(address),
        target=OPERATOR_PROTOCOL,
        resource=empty(address),
        maxAmount=0,
        beneficiary=LEGO,
        actionDataHash=actionDataHash,
    )
    extcall IUserWalletV3(wallet).openSession(request)
    extcall IUserWalletV3(wallet).setDebtOperator(False, request)
