import pytest
import boa

from config.BluePrint import TOKENS, TEST_AMOUNTS


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
    lego_book,
):
    # setup
    vault_token = getVaultToken(token_str)
    asset, whale = getTokenAndWhale(token_str)
    asset.transfer(bob_user_wallet.address, TEST_AMOUNTS[token_str] * (10 ** asset.decimals()), sender=whale)

    testLegoDeposit(lego_book.getRegId(lego_euler), asset, vault_token)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_euler_deposit_partial(
    token_str,
    testLegoDeposit,
    getVaultToken,
    bob_user_wallet,
    lego_euler,
    getTokenAndWhale,
    lego_book,
):
    # setup
    vault_token = getVaultToken(token_str)
    asset, whale = getTokenAndWhale(token_str)
    amount = TEST_AMOUNTS[token_str] * (10 ** asset.decimals())
    asset.transfer(bob_user_wallet.address, amount, sender=whale)

    testLegoDeposit(lego_book.getRegId(lego_euler), asset, vault_token, amount // 2)


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


# @pytest.always
# def test_euler_operator_access(
#     lego_euler,
#     bob,
#     bob_user_wallet,
#     governor,
#     lego_book,
# ):
#     # set rewards
#     euler_rewards = boa.from_etherscan("0x3ef3d8ba38ebe18db133cec108f4d14ce00dd9ae", name="euler_rewards")
#     assert lego_euler.setEulerRewardsAddr(euler_rewards, sender=governor)

#     # no acccess
#     assert not euler_rewards.operators(bob_user_wallet.address, lego_euler.address)

#     # claim rewards, will only set access (no reward token given)
#     bob_user_wallet.claimRewards(lego_book.getRegId(lego_euler), sender=bob)

#     # has access
#     assert euler_rewards.operators(bob_user_wallet.address, lego_euler.address)