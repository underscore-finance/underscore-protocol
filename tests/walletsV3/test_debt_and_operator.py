import boa
import pytest
from eth_utils import keccak

from conftest import deploy_v3


ZERO = "0x0000000000000000000000000000000000000000"


def method_selector(method, *args):
    return bytes(method.prepare_calldata(*args)[:4])


def attach_debt(wallet, extender, lego, operator_protocol, owner, version=1):
    selectors = {
        "borrow": method_selector(extender.borrow, wallet.address, ZERO, ZERO, 1),
        "repay": method_selector(extender.repayClose, wallet.address, ZERO, ZERO, 1),
        "remove": method_selector(extender.removeCollateral, wallet.address, ZERO, ZERO, 1),
        "grant": method_selector(extender.grantOperator, wallet.address),
        "revoke": method_selector(extender.revokeOperator, wallet.address),
    }
    wallet.attachExtender(
        (
            keccak(text="wallet-v3-debt-family"),
            version,
            extender.address,
            lego.address,
            operator_protocol.address,
            ZERO,
            [
                (selectors["borrow"], 10, 2, 1),
                (selectors["repay"], 11, 1, 1),
                (selectors["remove"], 12, 3, 1),
                (selectors["grant"], 13, 4, 2),
                (selectors["revoke"], 14, 4, 2),
            ],
            [selectors["repay"], selectors["revoke"]],
        ),
        sender=owner,
    )
    return selectors


@pytest.fixture
def debt_stack(wallet, token, owner, recipient, config_factory):
    lego = deploy_v3("contracts/walletsV3/mocks/MockDebtLego.vy")
    protocol = deploy_v3("contracts/walletsV3/mocks/MockDebtProtocol.vy")
    operator = deploy_v3("contracts/walletsV3/mocks/MockOperatorProtocol.vy")
    extender = deploy_v3(
        "contracts/walletsV3/extenders/DebtExtender.vy",
        lego.address,
        operator.address,
    )
    config = config_factory(
        wallet,
        recipients=[recipient, lego.address],
        tokens=[(token.address, 10**24, 10**24)],
    )
    wallet.replaceConfig(config.address, sender=owner)
    selectors = attach_debt(wallet, extender, lego, operator, owner)
    token.mint(protocol.address, 1_000)
    return {
        "wallet": wallet,
        "token": token,
        "lego": lego,
        "protocol": protocol,
        "operator": operator,
        "extender": extender,
        "selectors": selectors,
        "config": config,
    }


def execute(stack, method, *args, sender):
    stack["wallet"].execute(
        method.prepare_calldata(stack["wallet"].address, *args),
        sender=sender,
    )


def test_s3_e1_non_allowance_effects_are_semantically_bounded(debt_stack, owner):
    stack = debt_stack
    stack["protocol"].seedCollateral(stack["wallet"].address, stack["token"].address, 10)

    for mode in [1, 2, 3]:
        stack["lego"].setMode(mode)
        with boa.reverts():
            execute(
                stack,
                stack["extender"].removeCollateral,
                stack["protocol"].address,
                stack["token"].address,
                1,
                sender=owner,
            )
    assert stack["protocol"].collateral(stack["wallet"].address, stack["token"].address) == 10

    stack["lego"].setMode(0)
    execute(
        stack,
        stack["extender"].removeCollateral,
        stack["protocol"].address,
        stack["token"].address,
        1,
        sender=owner,
    )
    assert stack["protocol"].collateral(stack["wallet"].address, stack["token"].address) == 9


def test_s3_e2_borrowed_and_released_assets_go_to_wallet(debt_stack, owner):
    stack = debt_stack
    stack["protocol"].seedCollateral(stack["wallet"].address, stack["token"].address, 5)
    before = stack["token"].balanceOf(stack["wallet"].address)
    execute(
        stack,
        stack["extender"].borrow,
        stack["protocol"].address,
        stack["token"].address,
        25,
        sender=owner,
    )
    execute(
        stack,
        stack["extender"].removeCollateral,
        stack["protocol"].address,
        stack["token"].address,
        5,
        sender=owner,
    )
    assert stack["token"].balanceOf(stack["wallet"].address) == before + 30
    assert stack["protocol"].positionOwner(stack["wallet"].address) == stack["wallet"].address
    assert stack["token"].balanceOf(stack["lego"].address) == 0
    assert stack["token"].balanceOf(stack["extender"].address) == 0


def test_s3_e3_fixed_operator_target_and_lego_only(debt_stack, owner):
    stack = debt_stack
    stack["wallet"].execute(
        stack["extender"].grantOperator.prepare_calldata(stack["wallet"].address),
        sender=owner,
    )
    assert stack["operator"].isOperator(stack["wallet"].address, stack["lego"].address)

    other_operator = deploy_v3("contracts/walletsV3/mocks/MockOperatorProtocol.vy")
    mismatched = deploy_v3(
        "contracts/walletsV3/extenders/DebtExtender.vy",
        stack["lego"].address,
        other_operator.address,
    )
    other_wallet = deploy_v3("contracts/walletsV3/UserWalletV3.vy", owner)
    # The immutable target is part of the typed extender. A mismatched target
    # cannot be substituted into the already pinned attachment.
    with boa.reverts():
        mismatched.grantOperator(stack["wallet"].address, sender=owner)
    assert not other_operator.isOperator(stack["wallet"].address, stack["lego"].address)
    assert other_wallet.owner() == owner


def test_s3_e4_operator_use_outside_active_session_fails(debt_stack, owner):
    stack = debt_stack
    empty = (10, 2, stack["lego"].address, stack["protocol"].address, stack["token"].address, 1, stack["wallet"].address, b"\x00" * 32)
    with boa.reverts():
        stack["wallet"].setDebtOperator(True, empty, sender=stack["extender"].address)
    with boa.reverts():
        stack["lego"].attemptOperatorUse(
            stack["wallet"].address,
            stack["operator"].address,
            empty,
            sender=owner,
        )
    with boa.reverts():
        stack["operator"].useOperator(stack["wallet"].address, sender=stack["lego"].address)


def test_s3_e5_active_revoke_after_config_replacement(
    debt_stack,
    owner,
    recipient,
    config_factory,
):
    stack = debt_stack
    stack["wallet"].execute(
        stack["extender"].grantOperator.prepare_calldata(stack["wallet"].address),
        sender=owner,
    )
    fresh = config_factory(
        stack["wallet"],
        recipients=[recipient, stack["lego"].address],
        tokens=[(stack["token"].address, 10**24, 10**24)],
    )
    stack["wallet"].replaceConfig(fresh.address, sender=owner)
    stack["wallet"].execute(
        stack["extender"].revokeOperator.prepare_calldata(stack["wallet"].address),
        sender=owner,
    )
    assert not stack["operator"].isOperator(stack["wallet"].address, stack["lego"].address)
