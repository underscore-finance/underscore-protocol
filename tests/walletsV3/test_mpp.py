import boa
import pytest
from eth_utils import keccak

from conftest import deploy_v3
from test_debt_and_operator import attach_debt


ZERO = "0x0000000000000000000000000000000000000000"


def method_selector(method, *args):
    return bytes(method.prepare_calldata(*args)[:4])


def attach_payment(wallet, extender, helper, owner, version=1):
    external_selector = method_selector(
        extender.authorizeExternalExact,
        wallet.address,
        b"\x00" * 32,
        ZERO,
        1,
        ZERO,
        0,
        1,
        b"\x01" * 32,
    )
    reserved_selector = method_selector(
        extender.authorizeReservedTransfer,
        wallet.address,
        b"\x00" * 32,
        ZERO,
        1,
        ZERO,
        ZERO,
    )
    wallet.attachExtender(
        (
            keccak(text="wallet-v3-payment-family"),
            version,
            extender.address,
            ZERO,
            ZERO,
            helper.address,
            [
                (external_selector, 20, 1, 2),
                (reserved_selector, 21, 1, 2),
            ],
            [],
        ),
        sender=owner,
    )
    return {
        "external": external_selector,
        "reserved": reserved_selector,
    }


@pytest.fixture
def payment_stack(wallet, token, owner, recipient, config_factory):
    destination = recipient
    operator = boa.env.generate_address("wallet_v3_settlement_operator")
    helper = deploy_v3("contracts/walletsV3/rails/X402Helper.vy", token.address)
    extender = deploy_v3(
        "contracts/walletsV3/extenders/PaymentExtender.vy",
        helper.address,
    )
    config = config_factory(
        wallet,
        recipients=[destination],
        tokens=[(token.address, 10**24, 10**24)],
    )
    wallet.replaceConfig(config.address, sender=owner)
    selectors = attach_payment(wallet, extender, helper, owner)
    token.mint(wallet.address, 1_000)
    return {
        "wallet": wallet,
        "token": token,
        "owner": owner,
        "destination": destination,
        "operator": operator,
        "helper": helper,
        "extender": extender,
        "selectors": selectors,
    }


def authorize_reserved(stack, commitment_id, amount):
    stack["wallet"].execute(
        stack["extender"].authorizeReservedTransfer.prepare_calldata(
            stack["wallet"].address,
            commitment_id,
            stack["token"].address,
            amount,
            stack["destination"],
            stack["operator"],
        ),
        sender=stack["owner"],
    )


def authorize_external(stack, commitment_id, amount, nonce, valid_after, valid_before):
    stack["wallet"].execute(
        stack["extender"].authorizeExternalExact.prepare_calldata(
            stack["wallet"].address,
            commitment_id,
            stack["token"].address,
            amount,
            stack["destination"],
            valid_after,
            valid_before,
            nonce,
        ),
        sender=stack["owner"],
    )


def test_s4_e1_commitment_creation_is_active_typed_and_allowlisted(
    payment_stack,
    stranger,
    config_factory,
):
    stack = payment_stack
    commitment_id = keccak(text="mpp-active-only")
    fields = (
        commitment_id,
        stack["token"].address,
        10,
        stack["destination"],
        stack["operator"],
    )
    envelope = (
        21,
        1,
        ZERO,
        stack["token"].address,
        stack["token"].address,
        10,
        stack["destination"],
        b"\x00" * 32,
    )
    with boa.reverts():
        stack["wallet"].createReservedTransfer(
            fields,
            envelope,
            sender=stack["extender"].address,
        )
    with boa.reverts():
        authorize_reserved(stack, commitment_id, 0)

    denied_destination = stranger
    with boa.reverts():
        stack["wallet"].execute(
            stack["extender"].authorizeReservedTransfer.prepare_calldata(
                stack["wallet"].address,
                commitment_id,
                stack["token"].address,
                10,
                denied_destination,
                stack["operator"],
            ),
            sender=stack["owner"],
        )
    assert stack["wallet"].reserved(stack["token"].address) == 0


def test_s4_e5_and_e6_partial_settlement_refund_and_terminal_replay(
    payment_stack,
    stranger,
):
    stack = payment_stack
    commitment_id = keccak(text="mpp-partial")
    authorize_reserved(stack, commitment_id, 100)
    assert stack["wallet"].reserved(stack["token"].address) == 100
    assert stack["wallet"].availableBalance(stack["token"].address) == 900

    with boa.reverts():
        stack["wallet"].settleReservedTransfer(commitment_id, 1, sender=stranger)
    with boa.reverts():
        stack["wallet"].settleReservedTransfer(commitment_id, 101, sender=stack["operator"])

    stack["wallet"].settleReservedTransfer(commitment_id, 30, sender=stack["operator"])
    commitment = stack["wallet"].commitment(commitment_id)
    assert commitment.remainingAmount == 70
    assert stack["token"].balanceOf(stack["destination"]) == 30
    assert stack["wallet"].reserved(stack["token"].address) == 70

    with boa.reverts():
        stack["wallet"].refundReservedTransfer(commitment_id, sender=stranger)
    wallet_balance = stack["token"].balanceOf(stack["wallet"].address)
    stack["wallet"].refundReservedTransfer(commitment_id, sender=stack["owner"])
    assert stack["token"].balanceOf(stack["wallet"].address) == wallet_balance
    assert stack["wallet"].reserved(stack["token"].address) == 0
    assert stack["wallet"].commitment(commitment_id).state == 5
    with boa.reverts():
        stack["wallet"].refundReservedTransfer(commitment_id, sender=stack["owner"])
    with boa.reverts():
        authorize_reserved(stack, commitment_id, 1)


def test_s4_e6_state_updates_before_transfer_and_reentrancy_rolls_back(payment_stack):
    stack = payment_stack
    commitment_id = keccak(text="mpp-reentrant")
    authorize_reserved(stack, commitment_id, 100)
    callback = stack["wallet"].settleReservedTransfer.prepare_calldata(commitment_id, 1)
    stack["token"].configureCallback(
        stack["wallet"].address,
        callback,
        True,
        False,
    )
    with boa.reverts():
        stack["wallet"].settleReservedTransfer(
            commitment_id,
            25,
            sender=stack["operator"],
        )
    commitment = stack["wallet"].commitment(commitment_id)
    assert commitment.remainingAmount == 100
    assert commitment.state == 1
    assert stack["wallet"].reserved(stack["token"].address) == 100
    assert stack["token"].balanceOf(stack["destination"]) == 0
    assert stack["wallet"].phase() == 0


def test_s4_e7_reserved_value_blocks_transfer_yield_debt_and_double_commit(
    payment_stack,
    recipient,
    config_factory,
):
    stack = payment_stack
    commitment_id = keccak(text="reserve-full-balance")
    authorize_reserved(stack, commitment_id, 1_000)
    with boa.reverts():
        stack["wallet"].transferFunds(
            recipient,
            stack["token"].address,
            1,
            sender=stack["owner"],
        )
    with boa.reverts():
        authorize_reserved(stack, keccak(text="second-reservation"), 1)

    yield_lego = deploy_v3("contracts/walletsV3/mocks/MockYieldLego.vy")
    vault = deploy_v3(
        "contracts/walletsV3/mocks/MockVault.vy",
        stack["token"].address,
    )
    yield_extender = deploy_v3(
        "contracts/walletsV3/extenders/YieldExtender.vy",
        yield_lego.address,
    )
    yield_selector = method_selector(
        yield_extender.deposit,
        stack["wallet"].address,
        vault.address,
        stack["token"].address,
        1,
    )
    stack["wallet"].attachExtender(
        (
            keccak(text="reserved-yield-family"),
            1,
            yield_extender.address,
            yield_lego.address,
            ZERO,
            ZERO,
            [(yield_selector, 1, 1, 1)],
            [],
        ),
        sender=stack["owner"],
    )
    with boa.reverts():
        stack["wallet"].execute(
            yield_extender.deposit.prepare_calldata(
                stack["wallet"].address,
                vault.address,
                stack["token"].address,
                1,
            ),
            sender=stack["owner"],
        )

    debt_lego = deploy_v3("contracts/walletsV3/mocks/MockDebtLego.vy")
    debt_protocol = deploy_v3("contracts/walletsV3/mocks/MockDebtProtocol.vy")
    operator_protocol = deploy_v3("contracts/walletsV3/mocks/MockOperatorProtocol.vy")
    debt_extender = deploy_v3(
        "contracts/walletsV3/extenders/DebtExtender.vy",
        debt_lego.address,
        operator_protocol.address,
    )
    replacement = config_factory(
        stack["wallet"],
        recipients=[stack["destination"], debt_lego.address],
        tokens=[(stack["token"].address, 10**24, 10**24)],
    )
    stack["wallet"].replaceConfig(replacement.address, sender=stack["owner"])
    attach_debt(
        stack["wallet"],
        debt_extender,
        debt_lego,
        operator_protocol,
        stack["owner"],
    )
    debt_protocol.seedCollateral(stack["wallet"].address, stack["token"].address, 1)
    # Seed a debt position without transferring more value to the wallet.
    debt_protocol.seedDebt(stack["wallet"].address, stack["token"].address, 1)
    with boa.reverts():
        stack["wallet"].execute(
            debt_extender.repayClose.prepare_calldata(
                stack["wallet"].address,
                debt_protocol.address,
                stack["token"].address,
                1,
            ),
            sender=stack["owner"],
        )


def test_s4_e8_commitments_survive_config_and_payment_successor(
    payment_stack,
    recipient,
    config_factory,
):
    stack = payment_stack
    now = boa.env.evm.patch.timestamp
    external_id = keccak(text="external-survives-successor")
    nonce = keccak(text="external-survives-successor-nonce")
    reserved_id = keccak(text="reserved-survives-successor")
    authorize_external(stack, external_id, 40, nonce, now - 1, now + 3600)
    authorize_reserved(stack, reserved_id, 60)

    helper_v2 = deploy_v3(
        "contracts/walletsV3/rails/X402Helper.vy",
        stack["token"].address,
    )
    extender_v2 = deploy_v3(
        "contracts/walletsV3/extenders/PaymentExtender.vy",
        helper_v2.address,
    )
    fresh = config_factory(
        stack["wallet"],
        recipients=[recipient],
        tokens=[(stack["token"].address, 10**24, 10**24)],
    )
    stack["wallet"].replaceConfig(fresh.address, sender=stack["owner"])
    attach_payment(stack["wallet"], extender_v2, helper_v2, stack["owner"], 2)

    stack["token"].transferWithAuthorization(
        stack["wallet"].address,
        stack["destination"],
        40,
        now - 1,
        now + 3600,
        nonce,
        b"stored-commitment",
        sender=stack["operator"],
    )
    stack["wallet"].syncExternalPull(external_id, sender=stack["operator"])
    stack["wallet"].settleReservedTransfer(
        reserved_id,
        20,
        sender=stack["operator"],
    )
    stack["wallet"].refundReservedTransfer(reserved_id, sender=stack["owner"])
    assert stack["wallet"].commitment(external_id).state == 2
    assert stack["wallet"].commitment(reserved_id).state == 5
    assert stack["wallet"].reserved(stack["token"].address) == 0


def test_s4_e9_token_and_helper_failures_preserve_commitment_state(
    payment_stack,
    recipient,
    config_factory,
):
    stack = payment_stack
    false_token = deploy_v3("contracts/walletsV3/mocks/MockMalformedToken.vy")
    false_token.mint(stack["wallet"].address, 50)
    fresh = config_factory(
        stack["wallet"],
        recipients=[recipient],
        tokens=[
            (stack["token"].address, 10**24, 10**24),
            (false_token.address, 50, 50),
        ],
    )
    stack["wallet"].replaceConfig(fresh.address, sender=stack["owner"])
    false_id = keccak(text="false-token-settlement")
    stack["wallet"].execute(
        stack["extender"].authorizeReservedTransfer.prepare_calldata(
            stack["wallet"].address,
            false_id,
            false_token.address,
            50,
            stack["destination"],
            stack["operator"],
        ),
        sender=stack["owner"],
    )
    with boa.reverts():
        stack["wallet"].settleReservedTransfer(false_id, 10, sender=stack["operator"])
    assert stack["wallet"].commitment(false_id).remainingAmount == 50
    assert stack["wallet"].reserved(false_token.address) == 50

    now = boa.env.evm.patch.timestamp
    external_id = keccak(text="helper-codehash-failure")
    nonce = keccak(text="helper-codehash-failure-nonce")
    authorize_external(stack, external_id, 10, nonce, now - 1, now + 100)
    boa.env.set_code(stack["helper"].address, b"\x00")
    with boa.reverts():
        stack["wallet"].syncExternalPull(external_id, sender=stack["operator"])
    assert stack["wallet"].commitment(external_id).state == 1
    assert stack["wallet"].reserved(stack["token"].address) == 10
