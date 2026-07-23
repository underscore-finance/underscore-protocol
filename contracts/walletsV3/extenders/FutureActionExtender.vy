# @version 0.4.3

from contracts.walletsV3.interfaces import IUserWalletV3
from contracts.walletsV3.interfaces import IFutureActionLegoV3
from contracts.walletsV3.types import WalletV3Types as w3


LEGO: public(immutable(address))
EXTENDER_MARKER: constant(bytes32) = keccak256("underscore.wallet-v3-future-extender-poc-v1")


@deploy
def __init__(lego: address):
    assert lego.is_contract
    LEGO = lego


@view
@external
def walletV3ExtenderMarker() -> bytes32:
    return EXTENDER_MARKER


@external
def releaseBond(wallet: address, protocol: address, asset: address, amount: uint256):
    actionDataHash: bytes32 = keccak256(abi_encode(protocol, asset, amount, wallet))
    request: w3.ActionEnvelope = w3.ActionEnvelope(
        actionId=30,
        effectClass=3,
        consumer=LEGO,
        target=protocol,
        resource=asset,
        maxAmount=amount,
        beneficiary=wallet,
        actionDataHash=actionDataHash,
    )
    extcall IUserWalletV3(wallet).openSession(request)
    extcall IFutureActionLegoV3(LEGO).releaseBond(wallet, protocol, asset, amount)
