import boa
import pytest
from eth_abi import encode
from eth_utils import keccak

from conftest import deploy_v3


ZERO = "0x0000000000000000000000000000000000000000"
ACTION_DOMAIN = keccak(text="underscore.wallet-v3-action-v1")


def selector(bound_method, *args):
    return bytes(bound_method.prepare_calldata(*args)[:4])


@pytest.fixture
def yield_stack(configured_wallet, token, owner):
    lego = deploy_v3("contracts/walletsV3/mocks/MockYieldLego.vy")
    vault = deploy_v3("contracts/walletsV3/mocks/MockVault.vy", token.address)
    extender = deploy_v3(
        "contracts/walletsV3/extenders/YieldExtender.vy",
        lego.address,
    )
    deposit_selector = selector(
        extender.deposit,
        configured_wallet.address,
        vault.address,
        token.address,
        1,
    )
    request = (
        keccak(text="wallet-v3-yield-family"),
        1,
        extender.address,
        lego.address,
        ZERO,
        ZERO,
        [(deposit_selector, 1, 1, 1)],
        [],
    )
    configured_wallet.attachExtender(request, sender=owner)
    return {
        "wallet": configured_wallet,
        "token": token,
        "lego": lego,
        "vault": vault,
        "extender": extender,
        "selector": deposit_selector,
        "attachment_id": 1,
        "request": request,
    }


def execute_deposit(stack, amount, sender):
    calldata = stack["extender"].deposit.prepare_calldata(
        stack["wallet"].address,
        stack["vault"].address,
        stack["token"].address,
        amount,
    )
    stack["wallet"].execute(calldata, sender=sender)
    return calldata


def test_s2_e1_routed_extender_opens_once_and_direct_calls_fail(
    yield_stack,
    owner,
):
    stack = yield_stack
    stack["token"].mint(stack["wallet"].address, 100)

    with boa.reverts():
        stack["extender"].deposit(
            stack["wallet"].address,
            stack["vault"].address,
            stack["token"].address,
            10,
            sender=owner,
        )
    with boa.reverts():
        stack["wallet"].executeAttached(
            stack["attachment_id"],
            stack["extender"].deposit.prepare_calldata(
                stack["wallet"].address,
                stack["vault"].address,
                stack["token"].address,
                10,
            ),
            sender=owner,
        )

    execute_deposit(stack, 10, owner)
    assert stack["lego"].consumeCount() == 1
    assert stack["wallet"].phase() == 0


def test_s2_e2_empty_session_has_no_effect_or_approval(
    configured_wallet,
    token,
    owner,
):
    benchmark = deploy_v3(
        "contracts/walletsV3/mocks/MockBenchmarkExtender.vy"
    )
    empty_selector = selector(benchmark.emptySession, configured_wallet.address)
    configured_wallet.attachExtender(
        (
            keccak(text="wallet-v3-benchmark-family"),
            1,
            benchmark.address,
            ZERO,
            ZERO,
            ZERO,
            [(empty_selector, 255, 2, 3)],
            [],
        ),
        sender=owner,
    )
    token.mint(configured_wallet.address, 100)
    calldata = benchmark.emptySession.prepare_calldata(configured_wallet.address)
    configured_wallet.execute(calldata, sender=owner)
    opened = next(
        event
        for event in configured_wallet.get_logs()
        if type(event).__name__ == "SessionOpened"
    )
    assert opened.nonce == 1
    assert opened.calldataHash == keccak(calldata)
    assert token.balanceOf(configured_wallet.address) == 100
    assert configured_wallet.reserved(token.address) == 0
    assert configured_wallet.phase() == 0


def test_s2_e3_and_e8_semantic_hash_binds_full_yield_action(
    yield_stack,
    owner,
):
    stack = yield_stack
    amount = 17
    stack["token"].mint(stack["wallet"].address, 100)
    execute_deposit(stack, amount, owner)
    opened = next(
        event
        for event in stack["wallet"].get_logs()
        if type(event).__name__ == "SessionOpened"
    )
    action_data_hash = keccak(
        encode(
            ["address", "address", "uint256", "address"],
            [
                stack["vault"].address,
                stack["token"].address,
                amount,
                stack["wallet"].address,
            ],
        )
    )
    expected = keccak(
        encode(
            [
                "bytes32",
                "uint256",
                "address",
                "uint256",
                "bytes4",
                "uint16",
                "uint8",
                "address",
                "address",
                "address",
                "uint256",
                "address",
                "bytes32",
            ],
            [
                ACTION_DOMAIN,
                boa.env.evm.patch.chain_id,
                stack["wallet"].address,
                stack["attachment_id"],
                stack["selector"],
                1,
                1,
                stack["lego"].address,
                stack["vault"].address,
                stack["token"].address,
                amount,
                stack["wallet"].address,
                action_data_hash,
            ],
        )
    )
    assert opened.semanticHash == expected
    assert stack["lego"].lastActionDataHash() == action_data_hash

    for mode in [1, 2, 3, 4, 5]:
        stack["lego"].setMode(mode)
        with boa.reverts():
            execute_deposit(stack, 1, owner)
    assert stack["vault"].balanceOf(stack["wallet"].address) == amount


def test_s2_e4_and_e5_exact_approval_cleanup_and_direct_beneficiary(
    yield_stack,
    owner,
):
    stack = yield_stack
    stack["token"].mint(stack["wallet"].address, 100)
    with boa.reverts():
        execute_deposit(stack, 0, owner)
    with boa.reverts():
        execute_deposit(stack, 101, owner)
    assert stack["lego"].consumeCount() == 0
    assert stack["token"].allowance(stack["wallet"].address, stack["lego"].address) == 0

    execute_deposit(stack, 40, owner)
    assert stack["lego"].lastWalletAllowance() == 40
    assert stack["lego"].lastProtocolAllowance() == 40
    assert stack["token"].allowance(stack["wallet"].address, stack["lego"].address) == 0
    assert stack["token"].allowance(stack["lego"].address, stack["vault"].address) == 0
    assert stack["token"].balanceOf(stack["lego"].address) == 0
    assert stack["token"].balanceOf(stack["extender"].address) == 0
    assert stack["vault"].balanceOf(stack["wallet"].address) == 40


def test_s2_e4_nested_dispatch_during_approval_rolls_back(
    yield_stack,
    owner,
):
    stack = yield_stack
    stack["token"].mint(stack["wallet"].address, 100)
    calldata = stack["extender"].deposit.prepare_calldata(
        stack["wallet"].address,
        stack["vault"].address,
        stack["token"].address,
        10,
    )
    callback = stack["wallet"].execute.prepare_calldata(calldata)
    stack["token"].configureCallback(
        stack["wallet"].address,
        callback,
        False,
        True,
    )
    with boa.reverts():
        stack["wallet"].execute(calldata, sender=owner)
    assert stack["token"].balanceOf(stack["wallet"].address) == 100
    assert stack["token"].allowance(stack["wallet"].address, stack["lego"].address) == 0
    assert stack["vault"].depositCount() == 0
    assert stack["wallet"].phase() == 0


def test_s2_e6_attachment_bounds_declarations_and_dependencies(
    configured_wallet,
    token,
    owner,
    stranger,
):
    lego = deploy_v3("contracts/walletsV3/mocks/MockYieldLego.vy")
    vault = deploy_v3("contracts/walletsV3/mocks/MockVault.vy", token.address)
    extender = deploy_v3(
        "contracts/walletsV3/extenders/YieldExtender.vy",
        lego.address,
    )
    sel = selector(
        extender.deposit,
        configured_wallet.address,
        vault.address,
        token.address,
        1,
    )
    family = keccak(text="attachment-validation")

    invalid_requests = [
        (family, 1, stranger, lego.address, ZERO, ZERO, [(sel, 1, 1, 1)], []),
        (family, 1, extender.address, stranger, ZERO, ZERO, [(sel, 1, 1, 1)], []),
        (family, 1, extender.address, ZERO, ZERO, ZERO, [(sel, 1, 1, 1)], []),
        (family, 1, extender.address, lego.address, ZERO, ZERO, [(sel, 1, 0, 1)], []),
        (family, 1, extender.address, lego.address, ZERO, ZERO, [(sel, 1, 1, 0)], []),
        (
            family,
            1,
            extender.address,
            lego.address,
            ZERO,
            ZERO,
            [(sel, 1, 1, 1), (sel, 2, 2, 1)],
            [],
        ),
        (family, 1, extender.address, lego.address, ZERO, ZERO, [(sel, 1, 1, 1)], [b"\xff" * 4]),
    ]
    for request in invalid_requests:
        with boa.reverts():
            configured_wallet.attachExtender(request, sender=owner)
    assert configured_wallet.currentRoute(sel).attachmentId == 0

    valid = (
        family,
        1,
        extender.address,
        lego.address,
        ZERO,
        ZERO,
        [(sel, 1, 1, 1)],
        [],
    )
    configured_wallet.attachExtender(valid, sender=owner)
    collision_extender = deploy_v3(
        "contracts/walletsV3/extenders/YieldExtender.vy",
        lego.address,
    )
    with boa.reverts():
        configured_wallet.attachExtender(
            (
                keccak(text="other-family"),
                1,
                collision_extender.address,
                lego.address,
                ZERO,
                ZERO,
                [(sel, 2, 2, 1)],
                [],
            ),
            sender=owner,
        )
    with boa.reverts():
        configured_wallet.attachExtender(
            (
                family,
                1,
                collision_extender.address,
                lego.address,
                ZERO,
                ZERO,
                [(sel, 1, 1, 1)],
                [],
            ),
            sender=owner,
        )

    token.mint(configured_wallet.address, 10)
    boa.env.set_code(lego.address, b"\x00")
    with boa.reverts():
        configured_wallet.execute(
            extender.deposit.prepare_calldata(
                configured_wallet.address,
                vault.address,
                token.address,
                1,
            ),
            sender=owner,
        )
