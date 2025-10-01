import pytest
import boa

from config.BluePrint import TOKENS, WHALES
from constants import EIGHTEEN_DECIMALS, MAX_UINT256


ALL_VAULT_TOKENS = {
    "base": {
        "AAVE_USDC": TOKENS["base"]["AAVEV3_USDC"],
        "COMPOUND_USDC": TOKENS["base"]["COMPOUNDV3_USDC"],
        "EULER_USDC": TOKENS["base"]["EULER_USDC"],
        "FLUID_USDC": TOKENS["base"]["FLUID_USDC"],
        "MOONWELL_USDC": TOKENS["base"]["MOONWELL_USDC"],
        "MORPHO_MOONWELL_USDC": TOKENS["base"]["MORPHO_MOONWELL_USDC"],
        "FORTY_ACRES_USDC": TOKENS["base"]["FORTY_ACRES_USDC"],
    },
}


TEST_TOKENS = [
    "AAVE_USDC",
    "COMPOUND_USDC",
    "EULER_USDC",
    "FLUID_USDC",
    "MOONWELL_USDC",
    "MORPHO_MOONWELL_USDC",
    "FORTY_ACRES_USDC",
]


@pytest.fixture(scope="module")
def getLegoId(lego_book, lego_aave_v3, lego_compound_v3, lego_euler, lego_fluid, lego_moonwell, lego_morpho, lego_40_acres):
    def getLegoId(_token_str):
        lego = None
        if _token_str == "AAVE_USDC":
            lego = lego_aave_v3
        if _token_str == "COMPOUND_USDC":
            lego = lego_compound_v3
        if _token_str == "EULER_USDC":
            lego = lego_euler
        if _token_str == "FLUID_USDC":
            lego = lego_fluid
        if _token_str == "MOONWELL_USDC":
            lego = lego_moonwell
        if _token_str == "MORPHO_MOONWELL_USDC":
            lego = lego_morpho
        if _token_str == "FORTY_ACRES_USDC":
            lego = lego_40_acres
        return lego_book.getRegId(lego)
    yield getLegoId


@pytest.fixture(scope="module")
def prepareYieldDeposit(
    getLegoId,
    undy_usd_vault,
    mock_ripe,
    bob,
    fork,
    switchboard_alpha,
    _test,
):
    def prepareYieldDeposit(_token_str):
        lego_id = getLegoId(_token_str)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][_token_str])
        asset = boa.from_etherscan(TOKENS[fork]["USDC"])
        whale = WHALES[fork]["USDC"]
        amount = 100 * (10 ** asset.decimals())

        # set price
        mock_ripe.setPrice(asset, 1 * EIGHTEEN_DECIMALS)

        # transfer asset to user
        asset.transfer(bob, amount, sender=whale)

        # deposit into earn vault
        asset.approve(undy_usd_vault, MAX_UINT256, sender=bob)
        undy_usd_vault.deposit(amount, bob, sender=bob)

        # approve lego and vault
        undy_usd_vault.setApprovedYieldLego(lego_id, True, sender=switchboard_alpha.address)
        undy_usd_vault.setApprovedVaultToken(vault_addr, True, sender=switchboard_alpha.address)

        return lego_id, vault_addr, asset, amount

    yield prepareYieldDeposit


#########
# Tests #
#########


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_usdc_vault_deposit(
    prepareYieldDeposit,
    undy_usd_vault,
    starter_agent,
    token_str,
    _test,
    bob,
):
    lego_id, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # deposit into yield vault
    asset_deposited, vault_token, vault_tokens_received, usd_value = undy_usd_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # total assets
    assert asset_deposited == amount
    _test(undy_usd_vault.totalAssets(), amount)

    # vault token
    assert vault_token == vault_addr.address
    assert vault_addr.balanceOf(undy_usd_vault) == vault_tokens_received

    # vault shares
    bob_shares = undy_usd_vault.balanceOf(bob)
    _test(undy_usd_vault.convertToAssets(bob_shares), amount)

    # usd value
    _test(usd_value, 100 * EIGHTEEN_DECIMALS)