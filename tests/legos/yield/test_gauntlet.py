import pytest
import boa

from config.BluePrint import TOKENS, TEST_AMOUNTS
from constants import EIGHTEEN_DECIMALS


VAULT_TOKENS = {
    "base": {
        "USDC": TOKENS["base"]["GAUNTLET_USDC"],
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
def test_gauntlet_deposit_max(
    token_str,
    testLegoMintOrRedeem,
    getTokenAndWhale,
    bob_user_wallet,
    lego_gauntlet,
    getVaultToken,
    lego_book,
):
    # setup
    vault_token = getVaultToken(token_str)
    asset, whale = getTokenAndWhale(token_str)
    asset.transfer(bob_user_wallet.address, TEST_AMOUNTS[token_str] * (10 ** asset.decimals()), sender=whale)

    testLegoMintOrRedeem(lego_book.getRegId(lego_gauntlet), asset, vault_token)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_gauntlet_deposit_partial(
    token_str,
    testLegoMintOrRedeem,
    getVaultToken,
    bob_user_wallet,
    lego_gauntlet,
    getTokenAndWhale,
    lego_book,
):
    # setup
    vault_token = getVaultToken(token_str)
    asset, whale = getTokenAndWhale(token_str)
    amount = TEST_AMOUNTS[token_str] * (10 ** asset.decimals())
    asset.transfer(bob_user_wallet.address, amount, sender=whale)

    testLegoMintOrRedeem(lego_book.getRegId(lego_gauntlet), asset, vault_token, amount // 2)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_gauntlet_withdraw_max(
    token_str,
    bob_user_wallet,
    lego_gauntlet,
    getVaultToken,
    testLegoMintOrRedeem,
    lego_book,
    fork,
):
    lego_id = lego_book.getRegId(lego_gauntlet)
    vault_token = getVaultToken(token_str)

    whale = boa.from_etherscan("0x259E82D48dA7AfAb0A3151abbe65E25053334D9C")
    amount = 10 * EIGHTEEN_DECIMALS
    vault_token.transfer(bob_user_wallet, amount, sender=whale.address)
    asset = boa.from_etherscan(TOKENS[fork][token_str])

    testLegoMintOrRedeem(lego_id, vault_token, asset)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_gauntlet_withdraw_partial(
    token_str,
    bob_user_wallet,
    lego_gauntlet,
    getVaultToken,
    testLegoMintOrRedeem,
    lego_book,
    fork,
):
    lego_id = lego_book.getRegId(lego_gauntlet)
    vault_token = getVaultToken(token_str)

    whale = boa.from_etherscan("0x259E82D48dA7AfAb0A3151abbe65E25053334D9C")
    amount = 10 * EIGHTEEN_DECIMALS
    vault_token.transfer(bob_user_wallet, amount, sender=whale.address)
    asset = boa.from_etherscan(TOKENS[fork][token_str])

    testLegoMintOrRedeem(lego_id, vault_token, asset, amount // 2)
