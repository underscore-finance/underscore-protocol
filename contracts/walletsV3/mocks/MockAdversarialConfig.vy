# @version 0.4.3

from contracts.walletsV3.types import WalletV3Types as w3


WALLET: immutable(address)
MODE: immutable(uint8)
CONFIG_INTERFACE_MARKER: constant(bytes32) = keccak256(
    "underscore.user-wallet-config-v3-poc-v1"
)


@deploy
def __init__(wallet: address, mode: uint8):
    WALLET = wallet
    MODE = mode


@view
@external
def configInterfaceMarker() -> bytes32:
    if MODE == 1:
        return keccak256("wrong")
    if MODE == 2:
        raise "marker revert"
    if MODE == 3:
        accumulator: uint256 = 0
        for i: uint256 in range(20_000):
            accumulator = unsafe_add(accumulator, i)
        assert accumulator != 0
    return CONFIG_INTERFACE_MARKER


@view
@external
def wallet() -> address:
    if MODE == 4:
        raise "wallet revert"
    return WALLET


@view
@external
def authorizeTransfer(
    realCaller: address,
    recipient: address,
    token: address,
    amount: uint256,
) -> bool:
    if MODE == 5:
        raise "operational revert"
    if MODE == 6:
        success: bool = False
        success = raw_call(
            WALLET,
            concat(
                method_id("transferFunds(address,address,uint256)"),
                abi_encode(recipient, token, amount),
            ),
            max_outsize=0,
            is_static_call=True,
            revert_on_failure=False,
        )
        return not success
    return True


@view
@external
def authorizeSession(
    realCaller: address,
    attachmentId: uint256,
    selector: bytes4,
    actionEnvelope: w3.ActionEnvelope,
) -> bool:
    if MODE == 5:
        raise "operational revert"
    return True
