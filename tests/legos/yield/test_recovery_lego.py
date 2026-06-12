import boa
import pytest

from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS


@pytest.fixture
def recovery_lego(undy_hq_deploy, governance, lego_book):
    lego = boa.load(
        "contracts/legos/yield/RecoveryLego.vy",
        undy_hq_deploy,
        governance,
        name="recovery_lego",
    )
    lego_book.startAddNewAddressToRegistry(lego, "Recovery Lego", sender=governance.address)
    boa.env.time_travel(blocks=lego_book.registryChangeTimeLock() + 1)
    lego_id = lego_book.confirmNewAddressToRegistry(lego, sender=governance.address)
    return lego, lego_id


def test_recovery_lego_deposit_and_migrate(
    recovery_lego,
    bob_user_wallet,
    bob,
    governance,
    yield_underlying_token,
    yield_underlying_token_whale,
    sally,
):
    lego, lego_id = recovery_lego
    amount = 1_000 * EIGHTEEN_DECIMALS

    yield_underlying_token.transfer(bob_user_wallet, amount, sender=yield_underlying_token_whale)

    deposit_amount, vault_token, vault_token_amount, usd_value = bob_user_wallet.depositForYield(
        lego_id,
        yield_underlying_token,
        ZERO_ADDRESS,
        amount,
        sender=bob,
    )

    assert deposit_amount == amount
    assert vault_token == ZERO_ADDRESS
    assert vault_token_amount == 0
    assert usd_value == 0
    assert yield_underlying_token.balanceOf(lego) == amount
    assert lego.userAssets(bob_user_wallet, yield_underlying_token) == amount

    with boa.reverts("no perms"):
        lego.migrateFunds([(bob_user_wallet.address, yield_underlying_token.address, sally)], sender=bob)

    assert lego.migrateFunds([(bob_user_wallet.address, yield_underlying_token.address, sally)], sender=governance.address)
    assert yield_underlying_token.balanceOf(sally) == amount
    assert yield_underlying_token.balanceOf(lego) == 0
    assert lego.userAssets(bob_user_wallet, yield_underlying_token) == 0


def test_recovery_lego_rejects_non_wallet_deposit(
    recovery_lego,
    bob,
    yield_underlying_token,
    yield_underlying_token_whale,
):
    lego, _ = recovery_lego
    amount = 100 * EIGHTEEN_DECIMALS

    yield_underlying_token.transfer(bob, amount, sender=yield_underlying_token_whale)

    with boa.reverts("not a user wallet"):
        lego.depositForYield(
            yield_underlying_token,
            amount,
            ZERO_ADDRESS,
            b"",
            bob,
            sender=bob,
        )
