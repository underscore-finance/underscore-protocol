import boa
from eth_utils import keccak
from vyper.compiler.settings import OptimizationLevel

from conftest import REPO_ROOT, V3_COMPILER_ARGS, deploy_v3
from test_mpp import authorize_external, attach_payment
from test_yield_session import yield_stack


ZERO = "0x0000000000000000000000000000000000000000"
INVALID = bytes.fromhex("ffffffff")


def test_s5_e2_capability_reuse_cross_action_and_stale_session_fail(
    yield_stack,
    owner,
):
    # Reuse and cross-field mutations are driven by the planned Lego's test
    # modes; a direct post-transaction consume proves transient state is stale.
    stack = yield_stack
    stack["token"].mint(stack["wallet"].address, 100)
    for mode in [1, 2, 3]:
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
    oversized_word_candidate,
):
    config = config_factory(
        wallet,
        recipients=[recipient],
        tokens=[(oversized_word_candidate, 10, 10)],
        actions=[],
    )
    wallet.replaceConfig(config.address, sender=owner)
    with boa.reverts():
        wallet.transferFunds(
            recipient,
            oversized_word_candidate,
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
    assert runtime_size == 11_913
    assert runtime_size < 16_384
