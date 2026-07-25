# @version 0.4.3

from contracts.poc.userWallet.types import WalletV3Types as w3


WALLET: immutable(address)
CONFIG_INTERFACE_MARKER: constant(bytes32) = keccak256(
    "underscore.user-wallet-config-v3-poc-v1"
)


@deploy
def __init__(wallet: address):
    WALLET = wallet


@view
@external
def configInterfaceMarker() -> bytes32:
    return CONFIG_INTERFACE_MARKER


@view
@external
def wallet() -> address:
    return WALLET


@view
@external
def authorizeTransfer(
    realCaller: address,
    recipient: address,
    token: address,
    amount: uint256,
) -> bool:
    raise "broken authorization"


@view
@external
def authorizeSession(
    realCaller: address,
    attachmentId: uint256,
    selector: bytes4,
    actionEnvelope: w3.ActionEnvelope,
) -> bool:
    raise "broken authorization"
