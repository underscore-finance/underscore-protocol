# @version 0.4.3

from contracts.poc.userWallet.interfaces import IUserWalletV3
from contracts.poc.userWallet.interfaces import IYieldLegoV3
from contracts.poc.userWallet.types import WalletV3Types as w3


LEGO: public(immutable(address))
EXTENDER_MARKER: constant(bytes32) = keccak256("underscore.wallet-v3-yield-extender-poc-v1")


@deploy
def __init__(lego: address):
    assert lego.is_contract
    LEGO = lego


@view
@external
def walletV3ExtenderMarker() -> bytes32:
    return EXTENDER_MARKER


@external
def deposit(wallet: address, vault: address, token: address, amount: uint256):
    actionDataHash: bytes32 = keccak256(abi_encode(vault, token, amount, wallet))
    request: w3.ActionEnvelope = w3.ActionEnvelope(
        actionId=1,
        effectClass=1,
        consumer=LEGO,
        target=vault,
        resource=token,
        maxAmount=amount,
        beneficiary=wallet,
        actionDataHash=actionDataHash,
    )
    extcall IUserWalletV3(wallet).openSession(request)
    extcall IYieldLegoV3(LEGO).deposit(wallet, vault, token, amount)
