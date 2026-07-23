import boa
from eth_utils import keccak

from conftest import deploy_v3
from test_debt_and_operator import attach_debt


def test_s3_e6_and_e7_debt_position_survives_successor_and_old_exact_exits(
    wallet,
    token,
    owner,
    recipient,
    config_factory,
):
    protocol = deploy_v3("contracts/walletsV3/mocks/MockDebtProtocol.vy")
    operator = deploy_v3("contracts/walletsV3/mocks/MockOperatorProtocol.vy")
    lego_v1 = deploy_v3("contracts/walletsV3/mocks/MockDebtLego.vy")
    lego_v2 = deploy_v3("contracts/walletsV3/mocks/MockDebtLego.vy")
    extender_v1 = deploy_v3(
        "contracts/walletsV3/extenders/DebtExtender.vy",
        lego_v1.address,
        operator.address,
    )
    extender_v2 = deploy_v3(
        "contracts/walletsV3/extenders/DebtExtender.vy",
        lego_v2.address,
        operator.address,
    )
    working_v1 = config_factory(
        wallet,
        recipients=[recipient, lego_v1.address, lego_v2.address],
        tokens=[(token.address, 10**24, 10**24)],
    )
    wallet.replaceConfig(working_v1.address, sender=owner)
    selectors = attach_debt(wallet, extender_v1, lego_v1, operator, owner, 1)
    token.mint(protocol.address, 1_000)

    wallet.execute(
        extender_v1.grantOperator.prepare_calldata(wallet.address),
        sender=owner,
    )
    wallet.execute(
        extender_v1.borrow.prepare_calldata(
            wallet.address,
            protocol.address,
            token.address,
            40,
        ),
        sender=owner,
    )
    assert protocol.positionOwner(wallet.address) == wallet.address
    assert protocol.debt(wallet.address, token.address) == 40

    broken = deploy_v3(
        "contracts/walletsV3/mocks/MockBrokenConfig.vy",
        wallet.address,
    )
    wallet.replaceConfig(broken.address, sender=owner)
    working_v2 = config_factory(
        wallet,
        recipients=[recipient, lego_v1.address, lego_v2.address],
        tokens=[(token.address, 10**24, 10**24)],
    )
    wallet.replaceConfig(working_v2.address, sender=owner)
    attach_debt(wallet, extender_v2, lego_v2, operator, owner, 2)

    old = wallet.attachment(1)
    new = wallet.attachment(2)
    assert old.lifecycle == 2
    assert new.lifecycle == 1
    assert old.familyId == new.familyId == keccak(text="wallet-v3-debt-family")
    assert old.extender != new.extender

    borrow_v1 = extender_v1.borrow.prepare_calldata(
        wallet.address,
        protocol.address,
        token.address,
        1,
    )
    assert wallet.currentRoute(selectors["borrow"]).attachmentId == 2
    assert wallet.currentRoute(selectors["repay"]).attachmentId == 2
    assert wallet.currentRoute(selectors["remove"]).attachmentId == 2
    assert wallet.currentRoute(selectors["grant"]).attachmentId == 2
    assert wallet.currentRoute(selectors["revoke"]).attachmentId == 2
    with boa.reverts():
        wallet.executeAttached(1, borrow_v1, sender=owner)

    wallet.executeAttached(
        1,
        extender_v1.repayClose.prepare_calldata(
            wallet.address,
            protocol.address,
            token.address,
            40,
        ),
        sender=owner,
    )
    wallet.executeAttached(
        1,
        extender_v1.revokeOperator.prepare_calldata(wallet.address),
        sender=owner,
    )
    assert protocol.debt(wallet.address, token.address) == 0
    assert protocol.positionOwner(wallet.address) == wallet.address
    assert not operator.isOperator(wallet.address, lego_v1.address)
    assert wallet.owner() == owner


def test_s5_e7_old_route_collision_nonexit_and_codehash_mutation_fail(
    wallet,
    token,
    owner,
    recipient,
    config_factory,
):
    protocol = deploy_v3("contracts/walletsV3/mocks/MockDebtProtocol.vy")
    operator = deploy_v3("contracts/walletsV3/mocks/MockOperatorProtocol.vy")
    lego = deploy_v3("contracts/walletsV3/mocks/MockDebtLego.vy")
    extender_v1 = deploy_v3(
        "contracts/walletsV3/extenders/DebtExtender.vy",
        lego.address,
        operator.address,
    )
    extender_v2 = deploy_v3(
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
    attach_debt(wallet, extender_v1, lego, operator, owner, 1)
    attach_debt(wallet, extender_v2, lego, operator, owner, 2)
    with boa.reverts():
        wallet.executeAttached(
            1,
            extender_v1.removeCollateral.prepare_calldata(
                wallet.address,
                protocol.address,
                token.address,
                1,
            ),
            sender=owner,
        )
    boa.env.set_code(extender_v2.address, b"\x00")
    with boa.reverts():
        wallet.execute(
            extender_v2.borrow.prepare_calldata(
                wallet.address,
                protocol.address,
                token.address,
                1,
            ),
            sender=owner,
        )
