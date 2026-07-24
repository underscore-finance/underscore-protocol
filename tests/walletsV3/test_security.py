import boa
from eth_abi import encode
from eth_utils import keccak
from vyper.compiler.settings import OptimizationLevel

from conftest import REPO_ROOT, V3_COMPILER_ARGS, deploy_v3
from test_mpp import authorize_external, attach_payment
from test_yield_session import yield_stack


ZERO = "0x0000000000000000000000000000000000000000"
INVALID = bytes.fromhex("ffffffff")


def _mutate(values, index, replacement):
    changed = list(values)
    changed[index] = replacement
    return tuple(changed)


def _hostile_core_stack(
    wallet,
    token,
    owner,
    recipient,
    config_factory,
    consumer_mode,
):
    malicious = deploy_v3("contracts/walletsV3/mocks/MaliciousExtender.vy")
    lego = deploy_v3("contracts/walletsV3/mocks/MockDebtLego.vy")
    operator = deploy_v3("contracts/walletsV3/mocks/MockOperatorProtocol.vy")
    helper = deploy_v3("contracts/walletsV3/rails/X402Helper.vy", token.address)
    config = config_factory(
        wallet,
        recipients=[recipient, lego.address],
        tokens=[(token.address, 10**24, 10**24)],
    )
    wallet.replaceConfig(config.address, sender=owner)
    token.mint(wallet.address, 1_000)

    valid_after = boa.env.evm.patch.timestamp - 1
    valid_before = valid_after + 1_000
    external_fields = (
        keccak(text="hostile-external"),
        token.address,
        11,
        recipient,
        valid_after,
        valid_before,
        keccak(text="hostile-external-nonce"),
        helper.address,
        b"\x00" * 32,
    )
    external_fields = _mutate(
        external_fields,
        8,
        helper.digest(
            wallet.address,
            recipient,
            11,
            valid_after,
            valid_before,
            external_fields[6],
        ),
    )
    reserved_fields = (
        keccak(text="hostile-reserved"),
        token.address,
        13,
        recipient,
        owner,
    )
    external_data_hash = keccak(
        encode(
            [
                "bytes32",
                "address",
                "uint256",
                "address",
                "uint256",
                "uint256",
                "bytes32",
                "address",
                "bytes32",
            ],
            list(external_fields),
        )
    )
    reserved_data_hash = keccak(
        encode(
            ["bytes32", "address", "uint256", "address", "address"],
            list(reserved_fields),
        )
    )
    operator_data_hash = keccak(
        encode(
            ["address", "address", "bool"],
            [operator.address, lego.address, True],
        )
    )
    envelopes = {
        "external": (
            20,
            1,
            ZERO,
            token.address,
            token.address,
            11,
            recipient,
            external_data_hash,
        ),
        "reserved": (
            21,
            1,
            ZERO,
            token.address,
            token.address,
            13,
            recipient,
            reserved_data_hash,
        ),
        "operator": (
            13,
            4,
            ZERO,
            operator.address,
            ZERO,
            0,
            lego.address,
            operator_data_hash,
        ),
    }
    selectors = {
        "external": bytes(
            malicious.openThenExternal.prepare_calldata(
                wallet.address,
                envelopes["external"],
                external_fields,
                envelopes["external"],
            )[:4]
        ),
        "reserved": bytes(
            malicious.openThenReserved.prepare_calldata(
                wallet.address,
                envelopes["reserved"],
                reserved_fields,
                envelopes["reserved"],
            )[:4]
        ),
        "operator": bytes(
            malicious.openThenOperator.prepare_calldata(
                wallet.address,
                envelopes["operator"],
                True,
                envelopes["operator"],
            )[:4]
        ),
    }
    wallet.attachExtender(
        (
            keccak(text=f"hostile-core-family-{consumer_mode}"),
            1,
            malicious.address,
            lego.address,
            operator.address,
            helper.address,
            [
                (selectors["external"], 20, 1, consumer_mode),
                (selectors["reserved"], 21, 1, consumer_mode),
                (selectors["operator"], 13, 4, consumer_mode),
            ],
            [],
        ),
        sender=owner,
    )
    return {
        "wallet": wallet,
        "token": token,
        "owner": owner,
        "recipient": recipient,
        "malicious": malicious,
        "lego": lego,
        "operator": operator,
        "helper": helper,
        "external_fields": external_fields,
        "reserved_fields": reserved_fields,
        "envelopes": envelopes,
    }


def _assert_no_hostile_effect(stack):
    assert stack["wallet"].phase() == 0
    assert stack["wallet"].reserved(stack["token"].address) == 0
    assert stack["wallet"].commitment(stack["external_fields"][0]).mode == 0
    assert stack["wallet"].commitment(stack["reserved_fields"][0]).mode == 0
    assert not stack["operator"].isOperator(
        stack["wallet"].address,
        stack["lego"].address,
    )


def test_s5_e1_none_route_cannot_consume_named_core_primitives(
    wallet,
    token,
    owner,
    recipient,
    config_factory,
):
    stack = _hostile_core_stack(
        wallet,
        token,
        owner,
        recipient,
        config_factory,
        consumer_mode=3,
    )
    malicious = stack["malicious"]
    attempts = [
        malicious.openThenExternal.prepare_calldata(
            wallet.address,
            stack["envelopes"]["external"],
            stack["external_fields"],
            stack["envelopes"]["external"],
        ),
        malicious.openThenReserved.prepare_calldata(
            wallet.address,
            stack["envelopes"]["reserved"],
            stack["reserved_fields"],
            stack["envelopes"]["reserved"],
        ),
        malicious.openThenOperator.prepare_calldata(
            wallet.address,
            stack["envelopes"]["operator"],
            True,
            stack["envelopes"]["operator"],
        ),
    ]
    for calldata in attempts:
        with boa.reverts():
            wallet.execute(calldata, sender=owner)
        _assert_no_hostile_effect(stack)


def test_s5_e1_hostile_active_extender_cannot_mutate_core_effect_fields(
    wallet,
    token,
    owner,
    recipient,
    stranger,
    config_factory,
):
    stack = _hostile_core_stack(
        wallet,
        token,
        owner,
        recipient,
        config_factory,
        consumer_mode=2,
    )
    malicious = stack["malicious"]
    wrong_hash = keccak(text="hostile-wrong-action-data")

    reserved_field_mutations = [
        (0, keccak(text="hostile-reserved-other-id")),
        (1, stranger),
        (2, 14),
        (3, stranger),
        (4, stranger),
    ]
    for index, replacement in reserved_field_mutations:
        fields = _mutate(stack["reserved_fields"], index, replacement)
        with boa.reverts():
            wallet.execute(
                malicious.openThenReserved.prepare_calldata(
                    wallet.address,
                    stack["envelopes"]["reserved"],
                    fields,
                    stack["envelopes"]["reserved"],
                ),
                sender=owner,
            )
        _assert_no_hostile_effect(stack)

    external_field_mutations = [
        (0, keccak(text="hostile-external-other-id")),
        (1, stranger),
        (2, 12),
        (3, stranger),
        (4, stack["external_fields"][4] - 1),
        (5, stack["external_fields"][5] + 1),
        (6, keccak(text="hostile-external-other-nonce")),
        (7, stranger),
        (8, wrong_hash),
    ]
    for index, replacement in external_field_mutations:
        fields = _mutate(stack["external_fields"], index, replacement)
        with boa.reverts():
            wallet.execute(
                malicious.openThenExternal.prepare_calldata(
                    wallet.address,
                    stack["envelopes"]["external"],
                    fields,
                    stack["envelopes"]["external"],
                ),
                sender=owner,
            )
        _assert_no_hostile_effect(stack)

    common_envelope_mutations = [
        (0, 30),
        (1, 2),
        (2, stranger),
        (3, stranger),
        (4, stranger),
        (5, 14),
        (6, stranger),
        (7, wrong_hash),
    ]
    for name, fields, method in [
        ("reserved", stack["reserved_fields"], malicious.openThenReserved),
        ("external", stack["external_fields"], malicious.openThenExternal),
    ]:
        for index, replacement in common_envelope_mutations:
            actual = _mutate(stack["envelopes"][name], index, replacement)
            with boa.reverts():
                wallet.execute(
                    method.prepare_calldata(
                        wallet.address,
                        stack["envelopes"][name],
                        fields,
                        actual,
                    ),
                    sender=owner,
                )
            _assert_no_hostile_effect(stack)

    for index, replacement in common_envelope_mutations:
        actual = _mutate(stack["envelopes"]["operator"], index, replacement)
        with boa.reverts():
            wallet.execute(
                malicious.openThenOperator.prepare_calldata(
                    wallet.address,
                    stack["envelopes"]["operator"],
                    True,
                    actual,
                ),
                sender=owner,
            )
        _assert_no_hostile_effect(stack)
    with boa.reverts():
        wallet.execute(
            malicious.openThenOperator.prepare_calldata(
                wallet.address,
                stack["envelopes"]["operator"],
                False,
                stack["envelopes"]["operator"],
            ),
            sender=owner,
        )
    _assert_no_hostile_effect(stack)

    wallet.execute(
        malicious.openThenOperator.prepare_calldata(
            wallet.address,
            stack["envelopes"]["operator"],
            True,
            stack["envelopes"]["operator"],
        ),
        sender=owner,
    )
    assert stack["operator"].isOperator(wallet.address, stack["lego"].address)
    wallet.execute(
        malicious.openThenReserved.prepare_calldata(
            wallet.address,
            stack["envelopes"]["reserved"],
            stack["reserved_fields"],
            stack["envelopes"]["reserved"],
        ),
        sender=owner,
    )
    wallet.execute(
        malicious.openThenExternal.prepare_calldata(
            wallet.address,
            stack["envelopes"]["external"],
            stack["external_fields"],
            stack["envelopes"]["external"],
        ),
        sender=owner,
    )
    assert wallet.commitment(stack["reserved_fields"][0]).mode == 2
    assert wallet.commitment(stack["external_fields"][0]).mode == 1
    assert wallet.reserved(token.address) == 24
    assert wallet.phase() == 0


def test_s5_e2_capability_reuse_cross_action_and_stale_session_fail(
    yield_stack,
    owner,
):
    # Reuse and cross-field mutations are driven by the planned Lego's test
    # modes; a direct post-transaction consume proves transient state is stale.
    stack = yield_stack
    stack["token"].mint(stack["wallet"].address, 100)
    for mode in [1, 2, 3, 4, 5]:
        stack["lego"].setMode(mode)
        with boa.reverts():
            stack["wallet"].execute(
                stack["extender"].deposit.prepare_calldata(
                    stack["wallet"].address,
                    stack["vault"].address,
                    stack["token"].address,
                    1,
                ),
                sender=owner,
            )
    stale = (
        1,
        1,
        stack["lego"].address,
        stack["vault"].address,
        stack["token"].address,
        1,
        stack["wallet"].address,
        keccak(b"stale"),
    )
    with boa.reverts():
        stack["wallet"].consumeCapability(stale, sender=stack["lego"].address)


def test_s5_e2_unconsumed_spend_session_cannot_settle(
    configured_wallet,
    token,
    owner,
):
    malicious = deploy_v3("contracts/walletsV3/mocks/MaliciousExtender.vy")
    lego = deploy_v3("contracts/walletsV3/mocks/MockYieldLego.vy")
    vault = deploy_v3("contracts/walletsV3/mocks/MockVault.vy", token.address)
    amount = 10
    request = (
        1,
        1,
        lego.address,
        vault.address,
        token.address,
        amount,
        configured_wallet.address,
        keccak(
            encode(
                ["address", "address", "uint256", "address"],
                [
                    vault.address,
                    token.address,
                    amount,
                    configured_wallet.address,
                ],
            )
        ),
    )
    selector = bytes(
        malicious.openThenConsumerSpend.prepare_calldata(
            configured_wallet.address,
            request,
            lego.address,
            vault.address,
            token.address,
            amount,
            True,
        )[:4]
    )
    configured_wallet.attachExtender(
        (
            keccak(text="unconsumed-spend-family"),
            1,
            malicious.address,
            lego.address,
            ZERO,
            ZERO,
            [(selector, 1, 1, 1)],
            [],
        ),
        sender=owner,
    )
    token.mint(configured_wallet.address, 100)
    wrong_consumer = _mutate(request, 2, malicious.address)
    with boa.reverts():
        configured_wallet.execute(
            malicious.openThenConsumerSpend.prepare_calldata(
                configured_wallet.address,
                wrong_consumer,
                lego.address,
                vault.address,
                token.address,
                amount,
                True,
            ),
            sender=owner,
        )
    assert token.balanceOf(configured_wallet.address) == 100
    assert token.balanceOf(malicious.address) == 0
    assert token.balanceOf(vault.address) == 0
    assert vault.balanceOf(configured_wallet.address) == 0
    assert token.allowance(configured_wallet.address, malicious.address) == 0
    assert configured_wallet.phase() == 0

    configured_wallet.execute(
        malicious.openThenConsumerSpend.prepare_calldata(
            configured_wallet.address,
            request,
            lego.address,
            vault.address,
            token.address,
            amount,
            True,
        ),
        sender=owner,
    )
    assert token.balanceOf(configured_wallet.address) == 90
    assert token.balanceOf(malicious.address) == 0
    assert token.balanceOf(vault.address) == amount
    assert vault.balanceOf(configured_wallet.address) == amount
    assert lego.consumeCount() == 1
    assert token.allowance(configured_wallet.address, lego.address) == 0
    assert configured_wallet.phase() == 0

    with boa.reverts():
        configured_wallet.execute(
            malicious.openThenConsumerSpend.prepare_calldata(
                configured_wallet.address,
                request,
                lego.address,
                vault.address,
                token.address,
                amount,
                False,
            ),
            sender=owner,
        )
    assert token.balanceOf(configured_wallet.address) == 90
    assert token.balanceOf(malicious.address) == 0
    assert token.balanceOf(vault.address) == amount
    assert vault.balanceOf(configured_wallet.address) == amount
    assert lego.consumeCount() == 1
    assert token.allowance(configured_wallet.address, malicious.address) == 0
    assert token.allowance(configured_wallet.address, lego.address) == 0
    assert configured_wallet.phase() == 0


def test_s5_e3_malicious_extender_cannot_use_primitives_or_general_authority(
    configured_wallet,
    token,
    owner,
    recipient,
):
    malicious = deploy_v3("contracts/walletsV3/mocks/MaliciousExtender.vy")
    token.mint(configured_wallet.address, 100)
    envelope = (1, 1, ZERO, token.address, token.address, 1, recipient, b"\x00" * 32)
    external_fields = (
        keccak(text="malicious-external"),
        token.address,
        1,
        recipient,
        0,
        1,
        keccak(text="malicious-nonce"),
        ZERO,
        b"\x00" * 32,
    )
    reserved_fields = (
        keccak(text="malicious-reserved"),
        token.address,
        1,
        recipient,
        owner,
    )
    attacks = [
        lambda: malicious.attackOpen(configured_wallet.address, envelope, sender=owner),
        lambda: malicious.attackConsume(configured_wallet.address, envelope, sender=owner),
        lambda: malicious.attackOperator(configured_wallet.address, envelope, sender=owner),
        lambda: malicious.attackExternal(
            configured_wallet.address,
            external_fields,
            envelope,
            sender=owner,
        ),
        lambda: malicious.attackReserved(
            configured_wallet.address,
            reserved_fields,
            envelope,
            sender=owner,
        ),
        lambda: malicious.attackTransfer(
            configured_wallet.address,
            recipient,
            token.address,
            1,
            sender=owner,
        ),
    ]
    for attack in attacks:
        with boa.reverts():
            attack()
    assert token.balanceOf(configured_wallet.address) == 100
    assert token.balanceOf(malicious.address) == 0


def test_s4_e3_and_s5_e4_non_idle_rail_answer_is_invalid(
    wallet,
    token,
    owner,
    recipient,
    config_factory,
):
    helper = deploy_v3("contracts/walletsV3/rails/X402Helper.vy", token.address)
    payment = deploy_v3(
        "contracts/walletsV3/extenders/PaymentExtender.vy",
        helper.address,
    )
    malicious = deploy_v3("contracts/walletsV3/mocks/MaliciousExtender.vy")
    config = config_factory(
        wallet,
        recipients=[recipient],
        tokens=[(token.address, 10**24, 10**24)],
    )
    wallet.replaceConfig(config.address, sender=owner)
    attach_payment(wallet, payment, helper, owner)
    token.mint(wallet.address, 100)
    now = boa.env.evm.patch.timestamp
    commitment_id = keccak(text="non-idle-signature")
    nonce = keccak(text="non-idle-signature-nonce")
    stack = {
        "wallet": wallet,
        "token": token,
        "owner": owner,
        "destination": recipient,
        "operator": owner,
        "helper": helper,
        "extender": payment,
    }
    authorize_external(stack, commitment_id, 10, nonce, now - 1, now + 100)
    digest = wallet.commitment(commitment_id).digest

    selector = bytes(
        malicious.openEmptyAndProbe.prepare_calldata(
            wallet.address,
            token.address,
            digest,
        )[:4]
    )
    wallet.attachExtender(
        (
            keccak(text="malicious-probe-family"),
            1,
            malicious.address,
            ZERO,
            ZERO,
            ZERO,
            [(selector, 255, 2, 3)],
            [],
        ),
        sender=owner,
    )
    wallet.execute(
        malicious.openEmptyAndProbe.prepare_calldata(
            wallet.address,
            token.address,
            digest,
        ),
        sender=owner,
    )
    assert malicious.lastProbe() == INVALID


def test_s5_e4_config_reentrancy_and_approval_cleanup_failure_revert_cleanly(
    yield_stack,
    owner,
    recipient,
):
    stack = yield_stack
    stack["token"].mint(stack["wallet"].address, 100)
    stack["token"].setFailZeroApprove(True)
    with boa.reverts():
        stack["wallet"].execute(
            stack["extender"].deposit.prepare_calldata(
                stack["wallet"].address,
                stack["vault"].address,
                stack["token"].address,
                10,
            ),
            sender=owner,
        )
    assert stack["token"].balanceOf(stack["wallet"].address) == 100
    assert stack["vault"].balanceOf(stack["wallet"].address) == 0
    assert stack["token"].allowance(stack["wallet"].address, stack["lego"].address) == 0

    stack["token"].setFailZeroApprove(False)
    reentrant_config = deploy_v3(
        "contracts/walletsV3/mocks/MockAdversarialConfig.vy",
        stack["wallet"].address,
        6,
    )
    stack["wallet"].replaceConfig(reentrant_config.address, sender=owner)
    stack["wallet"].transferFunds(
        recipient,
        stack["token"].address,
        1,
        sender=owner,
    )
    assert stack["token"].balanceOf(recipient) == 1
    assert stack["wallet"].phase() == 0


def test_s5_e4_malformed_erc20_return_fails_closed(
    wallet,
    owner,
    recipient,
    config_factory,
    oversized_token_return,
):
    config = config_factory(
        wallet,
        recipients=[recipient],
        tokens=[(oversized_token_return, 10, 10)],
        actions=[],
    )
    wallet.replaceConfig(config.address, sender=owner)
    with boa.reverts():
        wallet.transferFunds(
            recipient,
            oversized_token_return,
            1,
            sender=owner,
        )
    assert wallet.phase() == 0


def test_s5_e9_core_runtime_size_and_compiler_settings():
    deployer = boa.load_partial(
        str(REPO_ROOT / "contracts/walletsV3/UserWalletV3.vy"),
        compiler_args=V3_COMPILER_ARGS,
    )
    settings = deployer.compiler_data.settings
    runtime_size = len(deployer.compiler_data.bytecode_runtime)
    assert settings.optimize == OptimizationLevel.GAS
    assert settings.evm_version == "cancun"
    assert runtime_size == 12_055
    assert runtime_size < 16_384
