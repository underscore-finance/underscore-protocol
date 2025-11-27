import pytest
import boa

from config.BluePrint import TOKENS, TEST_AMOUNTS


VAULT_TOKENS = {
    "base": {
        "USDC": TOKENS["base"]["EXTRAFI_USDC"],
        "AERO": TOKENS["base"]["EXTRAFI_AERO"],
        "WETH": TOKENS["base"]["EXTRAFI_WETH"],
    },
}


TEST_ASSETS = [
    "USDC",
    "AERO",
    "WETH",
]


@pytest.fixture(scope="module")
def getVaultToken(fork):
    def getVaultToken(_token_str):
        if fork == "local":
            pytest.skip("asset not relevant on this fork")
        vault_token = VAULT_TOKENS[fork][_token_str]
        return boa.from_etherscan(vault_token, name=_token_str + "_vault_token")

    yield getVaultToken


@pytest.fixture(scope="module", autouse=True)
def setupConfig(lego_extrafi, fork, switchboard_alpha):
    usdc = TOKENS["base"]["USDC"]
    extrafi_usdc = TOKENS["base"]["EXTRAFI_USDC"]
    aero = TOKENS["base"]["AERO"]
    extrafi_aero = TOKENS["base"]["EXTRAFI_AERO"]
    weth = TOKENS["base"]["WETH"]
    extrafi_weth = TOKENS["base"]["EXTRAFI_WETH"]

    if fork == "local":
        pytest.skip("asset not relevant on this fork")

    if not lego_extrafi.isAssetOpportunity(usdc, extrafi_usdc):
        lego_extrafi.registerVaultTokenLocally(usdc, extrafi_usdc, 25, sender=switchboard_alpha.address)
    if not lego_extrafi.isAssetOpportunity(aero, extrafi_aero):
        lego_extrafi.registerVaultTokenLocally(aero, extrafi_aero, 3, sender=switchboard_alpha.address)
    if not lego_extrafi.isAssetOpportunity(weth, extrafi_weth):
        lego_extrafi.registerVaultTokenLocally(weth, extrafi_weth, 1, sender=switchboard_alpha.address)


#########
# Tests #
#########


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_extrafi_deposit_max(
    token_str,
    testLegoDeposit,
    getTokenAndWhale,
    bob_user_wallet,
    lego_extrafi,
    getVaultToken,
):
    # setup
    vault_token = getVaultToken(token_str)
    asset, whale = getTokenAndWhale(token_str)
    asset.transfer(bob_user_wallet.address, TEST_AMOUNTS[token_str] * (10 ** asset.decimals()), sender=whale)

    testLegoDeposit(lego_extrafi, asset, vault_token)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_extrafi_deposit_partial(
    token_str,
    testLegoDeposit,
    getVaultToken,
    bob_user_wallet,
    lego_extrafi,
    getTokenAndWhale,
):
    # setup
    vault_token = getVaultToken(token_str)
    asset, whale = getTokenAndWhale(token_str)
    amount = TEST_AMOUNTS[token_str] * (10 ** asset.decimals())
    asset.transfer(bob_user_wallet.address, amount, sender=whale)

    testLegoDeposit(lego_extrafi, asset, vault_token, amount // 2)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_extrafi_withdraw_max(
    token_str,
    setupWithdrawal,
    lego_extrafi,
    getVaultToken,
    testLegoWithdrawal,
    lego_book,
):
    lego_id = lego_book.getRegId(lego_extrafi)
    vault_token = getVaultToken(token_str)
    asset, _ = setupWithdrawal(lego_id, token_str, vault_token)

    testLegoWithdrawal(lego_id, asset, vault_token)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_extrafi_withdraw_partial(
    token_str,
    setupWithdrawal,
    lego_extrafi,
    getVaultToken,
    testLegoWithdrawal,
    lego_book,
):
    lego_id = lego_book.getRegId(lego_extrafi)
    vault_token = getVaultToken(token_str)
    asset, vault_tokens_received = setupWithdrawal(lego_id, token_str, vault_token)

    testLegoWithdrawal(lego_id, asset, vault_token, vault_tokens_received // 2)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_extrafi_view_functions(
    token_str,
    getVaultToken,
    lego_extrafi,
    testLegoViewFunctions,
):
    vault_token = getVaultToken(token_str)
    testLegoViewFunctions(lego_extrafi, vault_token, token_str)
