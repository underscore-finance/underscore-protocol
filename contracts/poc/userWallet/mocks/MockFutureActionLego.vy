# @version 0.4.3

from contracts.poc.userWallet.interfaces import IUserWalletV3
from contracts.poc.userWallet.types import WalletV3Types as w3


interface FutureProtocol:
    def releaseBond(owner: address, asset: address, amount: uint256, recipient: address): nonpayable


@external
def releaseBond(wallet: address, protocol: address, asset: address, amount: uint256):
    request: w3.ActionEnvelope = w3.ActionEnvelope(
        actionId=30,
        effectClass=3,
        consumer=self,
        target=protocol,
        resource=asset,
        maxAmount=amount,
        beneficiary=wallet,
        actionDataHash=keccak256(abi_encode(protocol, asset, amount, wallet)),
    )
    extcall IUserWalletV3(wallet).consumeCapability(request)
    extcall FutureProtocol(protocol).releaseBond(wallet, asset, amount, wallet)
