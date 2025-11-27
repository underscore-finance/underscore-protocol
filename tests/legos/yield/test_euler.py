import pytest
import boa

from config.BluePrint import TOKENS, TEST_AMOUNTS, INTEGRATION_ADDYS
from constants import ACTION_TYPE


VAULT_TOKENS = {
    "base": {
        "USDC": TOKENS["base"]["EULER_USDC"],
        "WETH": TOKENS["base"]["EULER_WETH"],
        "EURC": TOKENS["base"]["EULER_EURC"],
        "CBBTC": TOKENS["base"]["EULER_CBBTC"],
    },
}


TEST_ASSETS = [
    "USDC",
    "WETH",
    "EURC",
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
def test_euler_deposit_max(
    token_str,
    testLegoDeposit,
    getTokenAndWhale,
    bob_user_wallet,
    lego_euler,
    getVaultToken,
):
    # setup
    vault_token = getVaultToken(token_str)
    asset, whale = getTokenAndWhale(token_str)
    asset.transfer(bob_user_wallet.address, TEST_AMOUNTS[token_str] * (10 ** asset.decimals()), sender=whale)

    testLegoDeposit(lego_euler, asset, vault_token)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_euler_deposit_partial(
    token_str,
    testLegoDeposit,
    getVaultToken,
    bob_user_wallet,
    lego_euler,
    getTokenAndWhale,
):
    # setup
    vault_token = getVaultToken(token_str)
    asset, whale = getTokenAndWhale(token_str)
    amount = TEST_AMOUNTS[token_str] * (10 ** asset.decimals())
    asset.transfer(bob_user_wallet.address, amount, sender=whale)

    testLegoDeposit(lego_euler, asset, vault_token, amount // 2)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_euler_withdraw_max(
    token_str,
    setupWithdrawal,
    lego_euler,
    getVaultToken,
    testLegoWithdrawal,
    lego_book,
):
    lego_id = lego_book.getRegId(lego_euler)
    vault_token = getVaultToken(token_str)
    asset, _ = setupWithdrawal(lego_id, token_str, vault_token)

    testLegoWithdrawal(lego_id, asset, vault_token)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_euler_withdraw_partial(
    token_str,
    setupWithdrawal,
    lego_euler,
    getVaultToken,
    testLegoWithdrawal,
    lego_book,
):
    lego_id = lego_book.getRegId(lego_euler)
    vault_token = getVaultToken(token_str)
    asset, vault_tokens_received = setupWithdrawal(lego_id, token_str, vault_token)

    testLegoWithdrawal(lego_id, asset, vault_token, vault_tokens_received // 2)


@pytest.always
def test_euler_operator_access(
    lego_euler,
    bob,
    user_wallet,
    user_wallet_config,
    lego_book,
    fork,
):
    if fork == "local":
        pytest.skip("no euler rewards on this fork")

    # set rewards
    euler_rewards = boa.from_etherscan(INTEGRATION_ADDYS[fork]["EULER_REWARDS"], name="euler_rewards")

    # no acccess
    assert not euler_rewards.operators(user_wallet.address, lego_euler.address)

    # set access
    lego_id = lego_book.getRegId(lego_euler)
    user_wallet_config.setLegoAccessForAction(lego_id, ACTION_TYPE.REWARDS, sender=bob)

    # has access
    assert euler_rewards.operators(user_wallet.address, lego_euler.address)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_euler_view_functions(
    token_str,
    getVaultToken,
    lego_euler,
    testLegoViewFunctions,
):
    vault_token = getVaultToken(token_str)
    testLegoViewFunctions(lego_euler, vault_token, token_str)