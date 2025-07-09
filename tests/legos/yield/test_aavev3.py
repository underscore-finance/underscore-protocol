import pytest
import boa

from config.BluePrint import TOKENS, TEST_AMOUNTS


VAULT_TOKENS = {
    "base": {
        "WETH": TOKENS["base"]["AAVEV3_WETH"],
        "USDC": TOKENS["base"]["AAVEV3_USDC"],
        "WSTETH": TOKENS["base"]["AAVEV3_WSTETH"],
        "CBETH": TOKENS["base"]["AAVEV3_CBETH"],
        "CBBTC": TOKENS["base"]["AAVEV3_CBBTC"],
    },
}


TEST_ASSETS = [
    "ALPHA",
    "USDC",
    "WETH",
    "CBBTC",
    "WSTETH",
    "CBETH",
]


@pytest.fixture(scope="module")
def getVaultToken(fork, mock_aave_v3_pool):
    def getVaultToken(_token_str):
        if fork == "local":
            if _token_str == "ALPHA":
                return mock_aave_v3_pool
            else:
                pytest.skip("asset not relevant on this fork")
        elif _token_str == "ALPHA":
            pytest.skip("asset not relevant on this fork")
  
        vault_token = VAULT_TOKENS[fork][_token_str]
        return boa.from_etherscan(vault_token, name=_token_str + "_vault_token")

    yield getVaultToken


#########
# Tests #
#########


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_aaveV3_deposit_max(
    getVaultToken,
    token_str,
    testLegoDeposit,
    getTokenAndWhale,
    bob_user_wallet,
    lego_aave_v3,
    lego_book,
):
    # setup
    vault_token = getVaultToken(token_str)
    asset, whale = getTokenAndWhale(token_str)
    asset.transfer(bob_user_wallet.address, TEST_AMOUNTS[token_str] * (10 ** asset.decimals()), sender=whale)

    testLegoDeposit(lego_book.getRegId(lego_aave_v3), asset, vault_token)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_aaveV3_deposit_partial(
    token_str,
    testLegoDeposit,
    getTokenAndWhale,
    bob_user_wallet,
    lego_aave_v3,
    getVaultToken,
    lego_book,
):
    # setup
    vault_token = getVaultToken(token_str)
    asset, whale = getTokenAndWhale(token_str)
    amount = TEST_AMOUNTS[token_str] * (10 ** asset.decimals())
    asset.transfer(bob_user_wallet.address, amount, sender=whale)

    testLegoDeposit(lego_book.getRegId(lego_aave_v3), asset, vault_token, amount // 2)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_aaveV3_withdraw_max(
    token_str,
    setupWithdrawal,
    lego_aave_v3,
    testLegoWithdrawal,
    getVaultToken,
    lego_book,
):
    lego_id = lego_book.getRegId(lego_aave_v3)
    vault_token = getVaultToken(token_str)
    asset, _ = setupWithdrawal(lego_id, token_str, vault_token)

    testLegoWithdrawal(lego_id, asset, vault_token)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_aaveV3_withdraw_partial(
    token_str,
    setupWithdrawal,
    lego_aave_v3,
    testLegoWithdrawal,
    getVaultToken,
    lego_book,
):
    lego_id = lego_book.getRegId(lego_aave_v3)
    vault_token = getVaultToken(token_str)
    asset, vault_tokens_received = setupWithdrawal(lego_id, token_str, vault_token)

    testLegoWithdrawal(lego_id, asset, vault_token, vault_tokens_received // 2)