import boa
import pytest

from conftest import deploy_v3


ZERO = "0x0000000000000000000000000000000000000000"
EMPTY_REQUEST = (
    b"\x00" * 32,
    0,
    ZERO,
    ZERO,
    ZERO,
    ZERO,
    [],
    [],
)
EMPTY_ENVELOPE = (0, 0, ZERO, ZERO, ZERO, 0, ZERO, b"\x00" * 32)


def test_s1_e1_owner_manager_and_unauthorized_transfer(
    configured_wallet,
    config,
    token,
    owner,
    manager,
    recipient,
    stranger,
):
    token.mint(configured_wallet.address, 100)

    configured_wallet.transferFunds(recipient, token.address, 10, sender=owner)
    configured_wallet.transferFunds(recipient, token.address, 15, sender=manager)

    with boa.reverts():
        configured_wallet.transferFunds(recipient, token.address, 1, sender=stranger)

    assert token.balanceOf(recipient) == 25
    assert token.balanceOf(configured_wallet.address) == 75
    assert configured_wallet.phase() == 0


def test_s1_e2_boot_is_fail_closed(wallet, token, owner):
    assert wallet.owner() == owner
    assert wallet.config() == ZERO
    assert wallet.phase() == 0
    assert wallet.reserved(token.address) == 0
    assert wallet.availableBalance(token.address) == 0

    calls = [
        lambda: wallet.transferFunds(owner, token.address, 1, sender=owner),
        lambda: wallet.attachExtender(EMPTY_REQUEST, sender=owner),
        lambda: wallet.execute(b"\x00\x00\x00\x00", sender=owner),
        lambda: wallet.executeAttached(1, b"\x00\x00\x00\x00", sender=owner),
        lambda: wallet.openSession(EMPTY_ENVELOPE, sender=owner),
        lambda: wallet.consumeCapability(EMPTY_ENVELOPE, sender=owner),
        lambda: wallet.syncExternalPull(b"\x01" * 32, sender=owner),
        lambda: wallet.settleReservedTransfer(b"\x01" * 32, 1, sender=owner),
    ]
    for call in calls:
        with boa.reverts():
            call()

    assert wallet.phase() == 0


def test_s1_e3_rejects_invalid_config_candidates(
    wallet,
    owner,
    stranger,
    malformed_word_candidate,
    oversized_word_candidate,
):
    other_wallet = deploy_v3("contracts/walletsV3/UserWalletV3.vy", stranger)
    wrong_wallet = deploy_v3(
        "contracts/walletsV3/UserWalletConfigV3.vy",
        other_wallet.address,
        [],
        [owner],
        [],
        [],
    )
    wrong_marker = deploy_v3(
        "contracts/walletsV3/mocks/MockAdversarialConfig.vy",
        wallet.address,
        1,
    )
    reverting = deploy_v3(
        "contracts/walletsV3/mocks/MockAdversarialConfig.vy",
        wallet.address,
        2,
    )
    gas_exhausting = deploy_v3(
        "contracts/walletsV3/mocks/MockAdversarialConfig.vy",
        wallet.address,
        3,
    )

    candidates = [
        stranger,
        wrong_wallet.address,
        wrong_marker.address,
        reverting.address,
        gas_exhausting.address,
        malformed_word_candidate,
        oversized_word_candidate,
    ]
    for candidate in candidates:
        with boa.reverts():
            wallet.replaceConfig(candidate, sender=owner)
        assert wallet.config() == ZERO
        assert wallet.phase() == 0


def test_s1_e3_reviewed_config_has_no_initializer_or_rebinding(config):
    method_names = {entry.get("name") for entry in config.abi if entry["type"] == "function"}
    assert "initialize" not in method_names
    assert "setWallet" not in method_names
    assert "rebind" not in method_names


def test_s1_e4_config_token_and_reentrancy_failures_rollback(
    wallet,
    config,
    token,
    owner,
    recipient,
):
    wallet.replaceConfig(config.address, sender=owner)
    token.mint(wallet.address, 100)

    broken = deploy_v3(
        "contracts/walletsV3/mocks/MockBrokenConfig.vy",
        wallet.address,
    )
    wallet.replaceConfig(broken.address, sender=owner)
    with boa.reverts():
        wallet.transferFunds(recipient, token.address, 10, sender=owner)
    assert token.balanceOf(wallet.address) == 100
    assert wallet.config() == broken.address

    wallet.replaceConfig(config.address, sender=owner)
    false_token = deploy_v3("contracts/walletsV3/mocks/MockMalformedToken.vy")
    false_token.mint(wallet.address, 100)
    replacement = deploy_v3(
        "contracts/walletsV3/UserWalletConfigV3.vy",
        wallet.address,
        [],
        [recipient],
        [(false_token.address, 100, 100)],
        [],
    )
    wallet.replaceConfig(replacement.address, sender=owner)
    with boa.reverts():
        wallet.transferFunds(recipient, false_token.address, 10, sender=owner)
    assert false_token.balanceOf(wallet.address) == 100
    assert false_token.balanceOf(recipient) == 0

    wallet.replaceConfig(config.address, sender=owner)
    callback = wallet.transferFunds.prepare_calldata(recipient, token.address, 1)
    token.configureCallback(wallet.address, callback, True, False)
    with boa.reverts():
        wallet.transferFunds(recipient, token.address, 10, sender=owner)
    assert token.balanceOf(wallet.address) == 100
    assert token.balanceOf(recipient) == 0
    assert wallet.reserved(token.address) == 0
    assert wallet.phase() == 0


def test_s1_e5_broken_config_can_be_replaced_without_moving_assets(
    wallet,
    config_factory,
    token,
    owner,
    manager,
    recipient,
):
    token.mint(wallet.address, 100)
    broken = deploy_v3(
        "contracts/walletsV3/mocks/MockBrokenConfig.vy",
        wallet.address,
    )
    wallet.replaceConfig(broken.address, sender=owner)
    assert broken.configInterfaceMarker() != b"\x00" * 32
    assert broken.wallet() == wallet.address

    fresh = config_factory(
        wallet,
        managers=[],
        recipients=[recipient],
        tokens=[(token.address, 7, 50)],
        actions=[],
    )
    wallet.replaceConfig(fresh.address, sender=owner)

    assert wallet.config() == fresh.address
    assert token.balanceOf(wallet.address) == 100
    with boa.reverts():
        wallet.transferFunds(recipient, token.address, 1, sender=manager)
    wallet.transferFunds(recipient, token.address, 7, sender=owner)
    assert token.balanceOf(recipient) == 7
