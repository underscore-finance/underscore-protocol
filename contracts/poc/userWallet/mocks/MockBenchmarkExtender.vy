# @version 0.4.3

from contracts.poc.userWallet.interfaces import IUserWalletV3
from contracts.poc.userWallet.types import WalletV3Types as w3


EXTENDER_MARKER: constant(bytes32) = keccak256("underscore.wallet-v3-benchmark-extender-poc-v1")
EMPTY_HASH: constant(bytes32) = keccak256("empty")


@view
@external
def walletV3ExtenderMarker() -> bytes32:
    return EXTENDER_MARKER


@external
def emptySession(wallet: address):
    request: w3.ActionEnvelope = w3.ActionEnvelope(
        actionId=255,
        effectClass=2,
        consumer=empty(address),
        target=empty(address),
        resource=empty(address),
        maxAmount=0,
        beneficiary=wallet,
        actionDataHash=EMPTY_HASH,
    )
    extcall IUserWalletV3(wallet).openSession(request)
