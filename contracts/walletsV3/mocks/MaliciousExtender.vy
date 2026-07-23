# @version 0.4.3

from contracts.walletsV3.interfaces import IUserWalletV3
from contracts.walletsV3.types import WalletV3Types as w3


interface TokenProbe:
    def probeSignature(wallet: address, digest: bytes32) -> bytes4: view


lastProbe: public(bytes4)


@external
def attackOpen(wallet: address, request: w3.ActionEnvelope):
    extcall IUserWalletV3(wallet).openSession(request)


@external
def attackConsume(wallet: address, request: w3.ActionEnvelope):
    extcall IUserWalletV3(wallet).consumeCapability(request)


@external
def attackOperator(wallet: address, request: w3.ActionEnvelope):
    extcall IUserWalletV3(wallet).setDebtOperator(True, request)


@external
def attackExternal(
    wallet: address,
    fields: w3.ExternalExactFields,
    request: w3.ActionEnvelope,
):
    extcall IUserWalletV3(wallet).createExternalExact(fields, request)


@external
def attackReserved(
    wallet: address,
    fields: w3.ReservedTransferFields,
    request: w3.ActionEnvelope,
):
    extcall IUserWalletV3(wallet).createReservedTransfer(fields, request)


@external
def openThenConsume(
    wallet: address,
    authorizedRequest: w3.ActionEnvelope,
    actualRequest: w3.ActionEnvelope,
):
    extcall IUserWalletV3(wallet).openSession(authorizedRequest)
    extcall IUserWalletV3(wallet).consumeCapability(actualRequest)


@external
def openThenOperator(
    wallet: address,
    authorizedRequest: w3.ActionEnvelope,
    enabled: bool,
    actualRequest: w3.ActionEnvelope,
):
    extcall IUserWalletV3(wallet).openSession(authorizedRequest)
    extcall IUserWalletV3(wallet).setDebtOperator(enabled, actualRequest)


@external
def openThenExternal(
    wallet: address,
    authorizedRequest: w3.ActionEnvelope,
    fields: w3.ExternalExactFields,
    actualRequest: w3.ActionEnvelope,
):
    extcall IUserWalletV3(wallet).openSession(authorizedRequest)
    extcall IUserWalletV3(wallet).createExternalExact(fields, actualRequest)


@external
def openThenReserved(
    wallet: address,
    authorizedRequest: w3.ActionEnvelope,
    fields: w3.ReservedTransferFields,
    actualRequest: w3.ActionEnvelope,
):
    extcall IUserWalletV3(wallet).openSession(authorizedRequest)
    extcall IUserWalletV3(wallet).createReservedTransfer(fields, actualRequest)


@external
def attackTransfer(wallet: address, recipient: address, token: address, amount: uint256):
    raw_call(
        wallet,
        concat(
            method_id("transferFunds(address,address,uint256)"),
            abi_encode(recipient, token, amount),
        ),
        max_outsize=0,
    )


@external
def openEmptyAndProbe(wallet: address, token: address, digest: bytes32):
    request: w3.ActionEnvelope = w3.ActionEnvelope(
        actionId=255,
        effectClass=2,
        consumer=empty(address),
        target=empty(address),
        resource=empty(address),
        maxAmount=0,
        beneficiary=wallet,
        actionDataHash=keccak256("empty"),
    )
    extcall IUserWalletV3(wallet).openSession(request)
    self.lastProbe = staticcall TokenProbe(token).probeSignature(wallet, digest)
