import pytest
import boa

from config.BluePrint import TOKENS, TEST_AMOUNTS
from constants import MAX_UINT256


VAULT_TOKENS = {
    "base": {
        "USDC": TOKENS["base"]["WASABI_USDC"],
    },
}


TEST_ASSETS = [
    "USDC",
]


@pytest.fixture(scope="module")
def getVaultToken(fork):
    def getVaultToken(_token_str):
        if fork == "local":
            pytest.skip("asset not relevant on this fork")
        vault_token = VAULT_TOKENS[fork][_token_str]
        return boa.from_etherscan(vault_token, name=_token_str + "_vault_token")

    yield getVaultToken


#########
# Tests #
#########


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_wasabi_deposit_max(
    token_str,
    getTokenAndWhale,
    bob_user_wallet,
    bob,
    lego_wasabi,
    lego_book,
    getVaultToken,
):
    # Wasabi deposits are disabled at the protocol level (raise in depositForYield).
    # Verify the user-wallet path surfaces the rejection rather than silently succeeding.
    vault_token = getVaultToken(token_str)
    asset, whale = getTokenAndWhale(token_str)
    asset.transfer(bob_user_wallet.address, TEST_AMOUNTS[token_str] * (10 ** asset.decimals()), sender=whale)
    lego_id = lego_book.getRegId(lego_wasabi)

    with boa.reverts("not allowing deposits right now"):
        bob_user_wallet.depositForYield(lego_id, asset, vault_token, MAX_UINT256, sender=bob)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_wasabi_deposit_partial(
    token_str,
    getVaultToken,
    bob_user_wallet,
    bob,
    lego_wasabi,
    lego_book,
    getTokenAndWhale,
):
    vault_token = getVaultToken(token_str)
    asset, whale = getTokenAndWhale(token_str)
    amount = TEST_AMOUNTS[token_str] * (10 ** asset.decimals())
    asset.transfer(bob_user_wallet.address, amount, sender=whale)
    lego_id = lego_book.getRegId(lego_wasabi)

    with boa.reverts("not allowing deposits right now"):
        bob_user_wallet.depositForYield(lego_id, asset, vault_token, amount // 2, sender=bob)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_wasabi_withdraw_max_without_balance_reverts(
    token_str,
    lego_wasabi,
    getVaultToken,
    bob_user_wallet,
    bob,
    lego_book,
):
    # With Wasabi deposits disabled, no production path can give bob_user_wallet
    # Wasabi vault tokens. Verify the user wallet's withdrawal guard rejects calls
    # against a zero balance with the specific "no balance for _token" message —
    # confirming the wallet's safety check is wired through the Wasabi lego dispatch
    # and not silently swallowed.
    vault_token = getVaultToken(token_str)
    lego_id = lego_book.getRegId(lego_wasabi)

    with boa.reverts("no balance for _token"):
        bob_user_wallet.withdrawFromYield(lego_id, vault_token, MAX_UINT256, sender=bob)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_wasabi_withdraw_partial_without_balance_reverts(
    token_str,
    lego_wasabi,
    getVaultToken,
    bob_user_wallet,
    bob,
    lego_book,
):
    # Same guard exercised with a non-MAX amount, ensuring the wallet's balance check
    # fires before any state mutation regardless of the requested amount.
    vault_token = getVaultToken(token_str)
    lego_id = lego_book.getRegId(lego_wasabi)

    with boa.reverts("no balance for _token"):
        bob_user_wallet.withdrawFromYield(lego_id, vault_token, 1, sender=bob)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_wasabi_view_functions(
    token_str,
    getVaultToken,
    lego_wasabi,
    testLegoViewFunctions,
):
    vault_token = getVaultToken(token_str)
    testLegoViewFunctions(lego_wasabi, vault_token, token_str)
