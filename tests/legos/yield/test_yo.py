import pytest
import boa

from config.BluePrint import TOKENS, TEST_AMOUNTS


VAULT_TOKENS = {
    "base": {
        "USDC": TOKENS["base"]["YO_USD"],
        "WETH": TOKENS["base"]["YO_ETH"],
        "CBBTC": TOKENS["base"]["YO_BTC"],
    },
}


TEST_ASSETS = [
    "USDC",
    "WETH",
    "CBBTC",
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
def test_yo_deposit_max(
    token_str,
    testLegoDeposit,
    getTokenAndWhale,
    bob_user_wallet,
    lego_yo,
    getVaultToken,
    lego_book,
):
    # setup
    vault_token = getVaultToken(token_str)
    asset, whale = getTokenAndWhale(token_str)
    asset.transfer(bob_user_wallet.address, TEST_AMOUNTS[token_str] * (10 ** asset.decimals()), sender=whale)

    testLegoDeposit(lego_book.getRegId(lego_yo), asset, vault_token)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_yo_deposit_partial(
    token_str,
    testLegoDeposit,
    getVaultToken,
    bob_user_wallet,
    lego_yo,
    getTokenAndWhale,
    lego_book,
):
    # setup
    vault_token = getVaultToken(token_str)
    asset, whale = getTokenAndWhale(token_str)
    amount = TEST_AMOUNTS[token_str] * (10 ** asset.decimals())
    asset.transfer(bob_user_wallet.address, amount, sender=whale)

    testLegoDeposit(lego_book.getRegId(lego_yo), asset, vault_token, amount // 2)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_yo_withdraw_max(
    token_str,
    setupWithdrawal,
    lego_yo,
    getVaultToken,
    testLegoWithdrawal,
    lego_book,
):
    lego_id = lego_book.getRegId(lego_yo)
    vault_token = getVaultToken(token_str)
    asset, _ = setupWithdrawal(lego_id, token_str, vault_token)

    testLegoWithdrawal(lego_id, asset, vault_token)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_yo_withdraw_partial(
    token_str,
    setupWithdrawal,
    lego_yo,
    getVaultToken,
    testLegoWithdrawal,
    lego_book,
):
    lego_id = lego_book.getRegId(lego_yo)
    vault_token = getVaultToken(token_str)
    asset, vault_tokens_received = setupWithdrawal(lego_id, token_str, vault_token)

    testLegoWithdrawal(lego_id, asset, vault_token, vault_tokens_received // 2)
