# @version 0.4.3

from contracts.walletsV3.types import WalletV3Types as w3


interface WalletOwner:
    def owner() -> address: view


CONFIG_INTERFACE_MARKER: constant(bytes32) = keccak256(
    "underscore.user-wallet-config-v3-poc-v1"
)

WALLET: public(immutable(address))
OWNER: immutable(address)

isManager: public(HashMap[address, bool])
isRecipient: public(HashMap[address, bool])
tokenTransferCap: public(HashMap[address, uint256])
tokenSessionCap: public(HashMap[address, uint256])
actionAllowed: public(HashMap[uint16, bool])
actionCap: public(HashMap[uint16, uint256])


@deploy
def __init__(
    wallet: address,
    managers: DynArray[address, 4],
    recipients: DynArray[address, 8],
    tokenPolicies: DynArray[w3.TokenPolicy, 8],
    actionPolicies: DynArray[w3.ActionPolicy, 16],
):
    assert wallet != empty(address), "invalid wallet"
    WALLET = wallet
    OWNER = staticcall WalletOwner(wallet).owner()
    assert OWNER != empty(address), "invalid owner"

    for manager: address in managers:
        assert manager != empty(address), "invalid manager"
        assert manager != OWNER and not self.isManager[manager], "duplicate manager"
        self.isManager[manager] = True

    for recipient: address in recipients:
        assert recipient != empty(address), "invalid recipient"
        assert not self.isRecipient[recipient], "duplicate recipient"
        self.isRecipient[recipient] = True

    for policy: w3.TokenPolicy in tokenPolicies:
        assert policy.token != empty(address), "invalid token"
        assert self.tokenTransferCap[policy.token] == 0, "duplicate token"
        assert policy.maxTransferAmount != 0 and policy.maxSessionAmount != 0, "zero cap"
        self.tokenTransferCap[policy.token] = policy.maxTransferAmount
        self.tokenSessionCap[policy.token] = policy.maxSessionAmount

    for policy: w3.ActionPolicy in actionPolicies:
        assert policy.actionId != 0, "invalid action"
        assert not self.actionAllowed[policy.actionId], "duplicate action"
        self.actionAllowed[policy.actionId] = True
        self.actionCap[policy.actionId] = policy.maxAmount


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
def owner() -> address:
    return OWNER


@view
@external
def authorizeTransfer(
    realCaller: address,
    recipient: address,
    token: address,
    amount: uint256,
) -> bool:
    if realCaller != OWNER and not self.isManager[realCaller]:
        return False
    if not self.isRecipient[recipient] or amount == 0:
        return False
    cap: uint256 = self.tokenTransferCap[token]
    return cap != 0 and amount <= cap


@view
@external
def authorizeSession(
    realCaller: address,
    attachmentId: uint256,
    selector: bytes4,
    actionEnvelope: w3.ActionEnvelope,
) -> bool:
    if realCaller != OWNER and not self.isManager[realCaller]:
        return False
    if attachmentId == 0 or selector == empty(bytes4):
        return False
    if not self.actionAllowed[actionEnvelope.actionId]:
        return False
    if actionEnvelope.maxAmount > self.actionCap[actionEnvelope.actionId]:
        return False
    if actionEnvelope.resource != empty(address):
        tokenCap: uint256 = self.tokenSessionCap[actionEnvelope.resource]
        if tokenCap == 0 or actionEnvelope.maxAmount > tokenCap:
            return False
    if (
        actionEnvelope.beneficiary != WALLET
        and actionEnvelope.beneficiary != actionEnvelope.consumer
        and not self.isRecipient[actionEnvelope.beneficiary]
    ):
        return False
    return True
