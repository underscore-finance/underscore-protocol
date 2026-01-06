import pytest
import boa

from constants import MAX_UINT256, EIGHTEEN_DECIMALS

SIX_DECIMALS = 10 ** 6
EIGHT_DECIMALS = 10 ** 8

# Test configuration - list of leverage vaults to test
TEST_LEVG_VAULTS = ["usdc", "cbbtc", "weth"]

# Decimal configurations for each vault type
VAULT_DECIMALS = {
    "usdc": SIX_DECIMALS,
    "cbbtc": EIGHT_DECIMALS,
    "weth": EIGHTEEN_DECIMALS,
}


############
# Fixtures #
############


@pytest.fixture(scope="module")
def setup_mock_prices(mock_ripe, mock_green_token, mock_savings_green_token, mock_usdc, mock_cbbtc, mock_weth):
    """Set up mock prices for testing"""
    mock_ripe.setPrice(mock_green_token, 1 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_savings_green_token, 1 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_usdc, 1 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_cbbtc, 90_000 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_weth, 2_000 * EIGHTEEN_DECIMALS)
    return mock_ripe


@pytest.fixture(scope="module")
def register_vault_tokens_with_lego(
    mock_yield_lego,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mock_usdc_collateral_vault,
    mock_cbbtc_collateral_vault,
    mock_weth_collateral_vault,
    mock_usdc_leverage_vault,
    switchboard_bravo,
):
    """Register vault tokens with mock_yield_lego for proper conversion."""
    mock_yield_lego.registerVaultTokenLocally(mock_usdc.address, mock_usdc_collateral_vault.address, sender=switchboard_bravo.address)
    mock_yield_lego.registerVaultTokenLocally(mock_cbbtc.address, mock_cbbtc_collateral_vault.address, sender=switchboard_bravo.address)
    mock_yield_lego.registerVaultTokenLocally(mock_weth.address, mock_weth_collateral_vault.address, sender=switchboard_bravo.address)
    mock_yield_lego.registerVaultTokenLocally(mock_usdc.address, mock_usdc_leverage_vault.address, sender=switchboard_bravo.address)

    mock_yield_lego.addPriceSnapshot(mock_usdc_collateral_vault.address, sender=switchboard_bravo.address)
    mock_yield_lego.addPriceSnapshot(mock_cbbtc_collateral_vault.address, sender=switchboard_bravo.address)
    mock_yield_lego.addPriceSnapshot(mock_weth_collateral_vault.address, sender=switchboard_bravo.address)
    mock_yield_lego.addPriceSnapshot(mock_usdc_leverage_vault.address, sender=switchboard_bravo.address)

    return mock_yield_lego


@pytest.fixture(scope="module")
def mock_weth_whale(env, mock_weth, whale):
    """Create a whale with WETH by depositing ETH"""
    weth_amount = 1000 * EIGHTEEN_DECIMALS
    boa.env.set_balance(whale, weth_amount)
    mock_weth.deposit(value=weth_amount, sender=whale)
    return whale


@pytest.fixture(scope="module")
def mint_to_vault(governance, mock_weth_whale, mock_weth):
    """Helper function to mint tokens to a vault, handling WETH specially"""
    def _mint_to_vault(token, vault_address, amount, is_weth=False):
        if is_weth:
            mock_weth.transfer(vault_address, amount, sender=mock_weth_whale)
        else:
            token.mint(vault_address, amount, sender=governance.address)
    return _mint_to_vault


#############################################
# 1. getTotalUnderlyingAmount Tests         #
#############################################


def test_get_total_underlying_collateral_counts_cbbtc_not_usdc(
    levg_vault_tools,
    setup_mock_prices,
    undy_levg_vault_cbbtc,
    mock_cbbtc,
    mock_usdc,
    governance,
):
    """Test collateral query counts cbBTC, ignores USDC."""
    cbbtc_amount = 10 * EIGHT_DECIMALS

    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, cbbtc_amount, sender=governance.address)
    result_before_usdc = levg_vault_tools.getTotalUnderlyingAmount(undy_levg_vault_cbbtc.address, True, False)

    usdc_amount = 50_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_cbbtc.address, usdc_amount, sender=governance.address)
    result_after_usdc = levg_vault_tools.getTotalUnderlyingAmount(undy_levg_vault_cbbtc.address, True, False)

    # Raw cbBTC should be exactly counted
    assert result_before_usdc == cbbtc_amount
    # Adding USDC should not change collateral result
    assert result_after_usdc == result_before_usdc


def test_get_total_underlying_leverage_counts_usdc_not_cbbtc(
    levg_vault_tools,
    setup_mock_prices,
    undy_levg_vault_cbbtc,
    mock_cbbtc,
    mock_usdc,
    governance,
):
    """Test leverage query counts USDC, ignores cbBTC."""
    usdc_amount = 50_000 * SIX_DECIMALS

    mock_usdc.mint(undy_levg_vault_cbbtc.address, usdc_amount, sender=governance.address)
    result_before_cbbtc = levg_vault_tools.getTotalUnderlyingAmount(undy_levg_vault_cbbtc.address, False, False)

    cbbtc_amount = 10 * EIGHT_DECIMALS
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, cbbtc_amount, sender=governance.address)
    result_after_cbbtc = levg_vault_tools.getTotalUnderlyingAmount(undy_levg_vault_cbbtc.address, False, False)

    # Raw USDC should be exactly counted
    assert result_before_cbbtc == usdc_amount
    # Adding cbBTC should not change leverage result
    assert result_after_cbbtc == result_before_cbbtc


def test_get_total_underlying_collateral_with_vault_tokens(
    levg_vault_tools,
    setup_mock_prices,
    register_vault_tokens_with_lego,
    undy_levg_vault_cbbtc,
    mock_cbbtc,
    mock_cbbtc_collateral_vault,
    governance,
    _test,
):
    """Test collateral query counts both raw cbBTC and cbBTC from vault tokens."""
    raw_amount = 5 * EIGHT_DECIMALS
    vault_deposit = 3 * EIGHT_DECIMALS

    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, raw_amount, sender=governance.address)
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, vault_deposit, sender=governance.address)
    mock_cbbtc.approve(mock_cbbtc_collateral_vault.address, vault_deposit, sender=undy_levg_vault_cbbtc.address)
    mock_cbbtc_collateral_vault.deposit(vault_deposit, undy_levg_vault_cbbtc.address, sender=undy_levg_vault_cbbtc.address)

    result = levg_vault_tools.getTotalUnderlyingAmount(undy_levg_vault_cbbtc.address, True, False)

    expected_total = raw_amount + vault_deposit
    _test(expected_total, result, 100)


def test_get_total_underlying_leverage_with_vault_tokens(
    levg_vault_tools,
    setup_mock_prices,
    register_vault_tokens_with_lego,
    undy_levg_vault_cbbtc,
    mock_usdc,
    mock_usdc_leverage_vault,
    governance,
    _test,
):
    """Test leverage query counts both raw USDC and USDC from vault tokens."""
    raw_amount = 10_000 * SIX_DECIMALS
    vault_deposit = 5_000 * SIX_DECIMALS

    mock_usdc.mint(undy_levg_vault_cbbtc.address, raw_amount, sender=governance.address)
    mock_usdc.mint(undy_levg_vault_cbbtc.address, vault_deposit, sender=governance.address)
    mock_usdc.approve(mock_usdc_leverage_vault.address, vault_deposit, sender=undy_levg_vault_cbbtc.address)
    mock_usdc_leverage_vault.deposit(vault_deposit, undy_levg_vault_cbbtc.address, sender=undy_levg_vault_cbbtc.address)

    result = levg_vault_tools.getTotalUnderlyingAmount(undy_levg_vault_cbbtc.address, False, False)

    expected_total = raw_amount + vault_deposit
    _test(expected_total, result, 100)


def test_get_total_underlying_weth_vault_collateral_counts_weth(
    levg_vault_tools,
    setup_mock_prices,
    undy_levg_vault_weth,
    mock_weth,
    mock_usdc,
    mock_weth_whale,
    governance,
):
    """Test WETH vault collateral query counts WETH, ignores USDC."""
    weth_amount = 50 * EIGHTEEN_DECIMALS
    usdc_amount = 100_000 * SIX_DECIMALS

    mock_weth.transfer(undy_levg_vault_weth.address, weth_amount, sender=mock_weth_whale)
    mock_usdc.mint(undy_levg_vault_weth.address, usdc_amount, sender=governance.address)

    result = levg_vault_tools.getTotalUnderlyingAmount(undy_levg_vault_weth.address, True, False)

    assert result == weth_amount


def test_get_total_underlying_weth_vault_leverage_counts_usdc(
    levg_vault_tools,
    setup_mock_prices,
    undy_levg_vault_weth,
    mock_weth,
    mock_usdc,
    mock_weth_whale,
    governance,
):
    """Test WETH vault leverage query counts USDC, ignores WETH."""
    weth_amount = 50 * EIGHTEEN_DECIMALS
    usdc_amount = 100_000 * SIX_DECIMALS

    mock_weth.transfer(undy_levg_vault_weth.address, weth_amount, sender=mock_weth_whale)
    mock_usdc.mint(undy_levg_vault_weth.address, usdc_amount, sender=governance.address)

    result = levg_vault_tools.getTotalUnderlyingAmount(undy_levg_vault_weth.address, False, False)

    assert result == usdc_amount


def test_get_total_underlying_collateral_on_ripe(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc,
    governance,
):
    """Test collateral query counts cbBTC deposited on Ripe."""
    wallet_amount = 5 * EIGHT_DECIMALS
    ripe_amount = 3 * EIGHT_DECIMALS

    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, wallet_amount, sender=governance.address)
    mock_ripe.setUserCollateral(undy_levg_vault_cbbtc.address, mock_cbbtc.address, ripe_amount)

    result = levg_vault_tools.getTotalUnderlyingAmount(undy_levg_vault_cbbtc.address, True, False)

    expected_total = wallet_amount + ripe_amount
    assert result == expected_total


def test_get_total_underlying_leverage_on_ripe(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_usdc,
    governance,
):
    """Test leverage query counts USDC deposited on Ripe."""
    wallet_amount = 10_000 * SIX_DECIMALS
    ripe_amount = 5_000 * SIX_DECIMALS

    mock_usdc.mint(undy_levg_vault_cbbtc.address, wallet_amount, sender=governance.address)
    mock_ripe.setUserCollateral(undy_levg_vault_cbbtc.address, mock_usdc.address, ripe_amount)

    result = levg_vault_tools.getTotalUnderlyingAmount(undy_levg_vault_cbbtc.address, False, False)

    expected_total = wallet_amount + ripe_amount
    assert result == expected_total


def test_get_total_underlying_collateral_only_on_ripe(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc,
):
    """Test collateral query with cbBTC only on Ripe (nothing in wallet)."""
    ripe_amount = 7 * EIGHT_DECIMALS

    mock_ripe.setUserCollateral(undy_levg_vault_cbbtc.address, mock_cbbtc.address, ripe_amount)

    result = levg_vault_tools.getTotalUnderlyingAmount(undy_levg_vault_cbbtc.address, True, False)

    assert result == ripe_amount


def test_get_total_underlying_leverage_only_on_ripe(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_usdc,
):
    """Test leverage query with USDC only on Ripe (nothing in wallet)."""
    ripe_amount = 25_000 * SIX_DECIMALS

    mock_ripe.setUserCollateral(undy_levg_vault_cbbtc.address, mock_usdc.address, ripe_amount)

    result = levg_vault_tools.getTotalUnderlyingAmount(undy_levg_vault_cbbtc.address, False, False)

    assert result == ripe_amount


#######################################
# 2. getAmountForAsset Tests          #
#######################################


def test_get_amount_for_asset_in_wallet_only(
    levg_vault_tools,
    setup_mock_prices,
    undy_levg_vault_usdc,
    mock_usdc,
    mock_ripe,
    governance,
):
    """Test getting asset amount when only in wallet"""
    # Clear any previous ripe collateral state
    mock_ripe.setUserCollateral(undy_levg_vault_usdc.address, mock_usdc.address, 0)

    # Record existing balance (session-scoped fixture may have prior state)
    existing_balance = mock_usdc.balanceOf(undy_levg_vault_usdc.address)

    amount = 5_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_usdc.address, amount, sender=governance.address)

    result = levg_vault_tools.getAmountForAsset(undy_levg_vault_usdc.address, mock_usdc.address)

    assert result == existing_balance + amount


def test_get_amount_for_asset_on_ripe_only(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_usdc,
    mock_usdc,
):
    """Test getting asset amount when deposited on Ripe"""
    # Record existing wallet balance (session-scoped fixture may have prior state)
    existing_wallet_balance = mock_usdc.balanceOf(undy_levg_vault_usdc.address)

    amount = 3_000 * SIX_DECIMALS
    mock_ripe.setUserCollateral(undy_levg_vault_usdc.address, mock_usdc.address, amount)

    result = levg_vault_tools.getAmountForAsset(undy_levg_vault_usdc.address, mock_usdc.address)

    assert result == existing_wallet_balance + amount


def test_get_amount_for_asset_in_both_locations(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_usdc,
    mock_usdc,
    governance,
):
    """Test getting asset amount when in both wallet and Ripe"""
    # Record existing wallet balance (session-scoped fixture may have prior state)
    existing_wallet_balance = mock_usdc.balanceOf(undy_levg_vault_usdc.address)

    wallet_amount = 2_000 * SIX_DECIMALS
    ripe_amount = 3_000 * SIX_DECIMALS

    mock_usdc.mint(undy_levg_vault_usdc.address, wallet_amount, sender=governance.address)
    mock_ripe.setUserCollateral(undy_levg_vault_usdc.address, mock_usdc.address, ripe_amount)

    result = levg_vault_tools.getAmountForAsset(undy_levg_vault_usdc.address, mock_usdc.address)

    assert result == existing_wallet_balance + wallet_amount + ripe_amount


##########################################
# 3. getRipeCollateralBalance Tests      #
##########################################


def test_get_ripe_collateral_balance_with_collateral(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_usdc,
    mock_green_token,
):
    """Test getting Ripe collateral balance"""
    collateral_amount = 7_500 * EIGHTEEN_DECIMALS
    mock_ripe.setUserCollateral(undy_levg_vault_usdc.address, mock_green_token.address, collateral_amount)

    result = levg_vault_tools.getRipeCollateralBalance(undy_levg_vault_usdc.address, mock_green_token.address)

    assert result == collateral_amount


def test_get_ripe_collateral_balance_no_collateral(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_usdc,
    mock_green_token,
):
    """Test Ripe collateral balance when none deposited"""
    mock_ripe.setUserCollateral(undy_levg_vault_usdc.address, mock_green_token.address, 0)

    result = levg_vault_tools.getRipeCollateralBalance(undy_levg_vault_usdc.address, mock_green_token.address)

    assert result == 0


#############################################
# 4. getUnderlyingAmountForVaultToken Tests #
#############################################


def test_get_underlying_amount_for_vault_token_with_lego(
    levg_vault_tools,
    setup_mock_prices,
    register_vault_tokens_with_lego,
    undy_levg_vault_usdc,
    mock_usdc,
    mock_usdc_collateral_vault,
    governance,
    _test,
):
    """Test underlying amount from vault tokens with proper lego registration."""
    underlying_amount = 1_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_usdc.address, underlying_amount, sender=governance.address)
    mock_usdc.approve(mock_usdc_collateral_vault.address, underlying_amount, sender=undy_levg_vault_usdc.address)
    mock_usdc_collateral_vault.deposit(underlying_amount, undy_levg_vault_usdc.address, sender=undy_levg_vault_usdc.address)

    result = levg_vault_tools.getUnderlyingAmountForVaultToken(undy_levg_vault_usdc.address, True, False)

    _test(underlying_amount, result, 100)


def test_get_underlying_amount_for_vault_token_should_get_max(
    levg_vault_tools,
    setup_mock_prices,
    register_vault_tokens_with_lego,
    undy_levg_vault_usdc,
    mock_usdc,
    mock_usdc_collateral_vault,
    governance,
    _test,
):
    """Test underlying amount with shouldGetMax=True returns >= safe amount."""
    underlying_amount = 500 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_usdc.address, underlying_amount, sender=governance.address)
    mock_usdc.approve(mock_usdc_collateral_vault.address, underlying_amount, sender=undy_levg_vault_usdc.address)
    mock_usdc_collateral_vault.deposit(underlying_amount, undy_levg_vault_usdc.address, sender=undy_levg_vault_usdc.address)

    safe_result = levg_vault_tools.getUnderlyingAmountForVaultToken(undy_levg_vault_usdc.address, True, False)
    max_result = levg_vault_tools.getUnderlyingAmountForVaultToken(undy_levg_vault_usdc.address, True, True)

    # max should be >= safe (uses different lego methods)
    assert max_result >= safe_result
    # Both should be within tolerance of underlying amount
    _test(underlying_amount, max_result, 100)


######################################
# 5. getUnderlyingGreenAmount Tests  #
######################################


def test_get_underlying_green_amount_in_wallet(
    levg_vault_tools,
    setup_mock_prices,
    undy_levg_vault_usdc,
    mock_green_token,
    governance,
):
    """Test GREEN amount when in wallet"""
    green_amount = 5_000 * EIGHTEEN_DECIMALS
    mock_green_token.mint(undy_levg_vault_usdc.address, green_amount, sender=governance.address)

    result = levg_vault_tools.getUnderlyingGreenAmount(undy_levg_vault_usdc.address)

    assert result == green_amount


def test_get_underlying_green_amount_sgreen_in_wallet(
    levg_vault_tools,
    setup_mock_prices,
    undy_levg_vault_usdc,
    mock_green_token,
    mock_savings_green_token,
    governance,
):
    """Test GREEN amount from sGREEN in wallet is correctly converted"""
    green_amount = 2_000 * EIGHTEEN_DECIMALS
    mock_green_token.mint(undy_levg_vault_usdc.address, green_amount, sender=governance.address)
    mock_green_token.approve(mock_savings_green_token.address, green_amount, sender=undy_levg_vault_usdc.address)
    mock_savings_green_token.deposit(green_amount, undy_levg_vault_usdc.address, sender=undy_levg_vault_usdc.address)

    # Get sGREEN balance and expected conversion
    sgreen_balance = mock_savings_green_token.balanceOf(undy_levg_vault_usdc.address)
    expected_green = mock_savings_green_token.previewRedeem(sgreen_balance)

    result = levg_vault_tools.getUnderlyingGreenAmount(undy_levg_vault_usdc.address)

    # Result should be exactly the converted sGREEN amount
    assert result == expected_green


def test_get_underlying_green_amount_sgreen_on_ripe(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_usdc,
    mock_savings_green_token,
):
    """Test GREEN amount from sGREEN deposited on Ripe"""
    sgreen_amount = 3_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserCollateral(undy_levg_vault_usdc.address, mock_savings_green_token.address, sgreen_amount)

    result = levg_vault_tools.getUnderlyingGreenAmount(undy_levg_vault_usdc.address)

    assert result >= sgreen_amount


def test_get_underlying_green_amount_mixed_sources(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_usdc,
    mock_green_token,
    mock_savings_green_token,
    governance,
):
    """Test GREEN amount from multiple sources"""
    green_wallet = 1_000 * EIGHTEEN_DECIMALS
    mock_green_token.mint(undy_levg_vault_usdc.address, green_wallet, sender=governance.address)

    sgreen_ripe = 2_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserCollateral(undy_levg_vault_usdc.address, mock_savings_green_token.address, sgreen_ripe)

    result = levg_vault_tools.getUnderlyingGreenAmount(undy_levg_vault_usdc.address)

    assert result >= green_wallet + sgreen_ripe


#################################
# 6. getGreenAmounts Tests      #
#################################


def test_get_green_amounts_returns_all_four_values(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_usdc,
    mock_green_token,
    mock_savings_green_token,
    governance,
):
    """Test getGreenAmounts returns all four breakdown values"""
    debt_amount = 5_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_usdc.address, debt_amount)

    green_wallet = 1_000 * EIGHTEEN_DECIMALS
    mock_green_token.mint(undy_levg_vault_usdc.address, green_wallet, sender=governance.address)

    sgreen_ripe = 2_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserCollateral(undy_levg_vault_usdc.address, mock_savings_green_token.address, sgreen_ripe)

    (user_debt, green_in_wallet, sgreen_wallet_converted, sgreen_ripe_converted) = \
        levg_vault_tools.getGreenAmounts(undy_levg_vault_usdc.address)

    assert user_debt == debt_amount
    assert green_in_wallet == green_wallet
    assert sgreen_ripe_converted >= sgreen_ripe


def test_get_green_amounts_with_no_debt(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_usdc,
    mock_green_token,
    governance,
):
    """Test getGreenAmounts with no debt"""
    mock_ripe.setUserDebt(undy_levg_vault_usdc.address, 0)

    green_amount = 3_000 * EIGHTEEN_DECIMALS
    mock_green_token.mint(undy_levg_vault_usdc.address, green_amount, sender=governance.address)

    (user_debt, green_in_wallet, sgreen_wallet_converted, sgreen_ripe_converted) = \
        levg_vault_tools.getGreenAmounts(undy_levg_vault_usdc.address)

    assert user_debt == 0
    assert green_in_wallet == green_amount


########################################
# 7. getSwappableUsdcAmount Tests      #
########################################


def test_get_swappable_usdc_amount_raw_usdc_counted(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_usdc,
    governance,
):
    """Test swappable USDC counts raw USDC in wallet with no debt."""
    usdc_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_cbbtc.address, usdc_amount, sender=governance.address)
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, 0)

    result = levg_vault_tools.getSwappableUsdcAmount(undy_levg_vault_cbbtc.address)

    # With no debt, all raw USDC should be swappable
    assert result == usdc_amount


def test_get_swappable_usdc_amount_on_ripe_counted(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_usdc,
    governance,
):
    """Test swappable USDC counts USDC deposited on Ripe."""
    wallet_usdc = 10_000 * SIX_DECIMALS
    ripe_usdc = 5_000 * SIX_DECIMALS

    mock_usdc.mint(undy_levg_vault_cbbtc.address, wallet_usdc, sender=governance.address)
    mock_ripe.setUserCollateral(undy_levg_vault_cbbtc.address, mock_usdc.address, ripe_usdc)
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, 0)

    result = levg_vault_tools.getSwappableUsdcAmount(undy_levg_vault_cbbtc.address)

    # With no debt, all USDC (wallet + Ripe) should be swappable
    expected_total = wallet_usdc + ripe_usdc
    assert result == expected_total


def test_get_swappable_usdc_amount_only_on_ripe(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_usdc,
):
    """Test swappable USDC with USDC only on Ripe."""
    ripe_usdc = 20_000 * SIX_DECIMALS

    mock_ripe.setUserCollateral(undy_levg_vault_cbbtc.address, mock_usdc.address, ripe_usdc)
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, 0)

    result = levg_vault_tools.getSwappableUsdcAmount(undy_levg_vault_cbbtc.address)

    # With no debt, all raw USDC on Ripe should be swappable
    assert result == ripe_usdc


def test_get_swappable_usdc_amount_combined_raw_and_vault_tokens(
    levg_vault_tools,
    setup_mock_prices,
    register_vault_tokens_with_lego,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_usdc,
    mock_usdc_leverage_vault,
    governance,
    _test,
):
    """Test swappable USDC counts both raw USDC and USDC from vault tokens."""
    raw_usdc = 10_000 * SIX_DECIMALS
    vault_usdc = 5_000 * SIX_DECIMALS

    mock_usdc.mint(undy_levg_vault_cbbtc.address, raw_usdc, sender=governance.address)
    mock_usdc.mint(undy_levg_vault_cbbtc.address, vault_usdc, sender=governance.address)
    mock_usdc.approve(mock_usdc_leverage_vault.address, vault_usdc, sender=undy_levg_vault_cbbtc.address)
    mock_usdc_leverage_vault.deposit(vault_usdc, undy_levg_vault_cbbtc.address, sender=undy_levg_vault_cbbtc.address)
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, 0)

    result = levg_vault_tools.getSwappableUsdcAmount(undy_levg_vault_cbbtc.address)

    expected_total = raw_usdc + vault_usdc
    _test(expected_total, result, 100)


def test_get_swappable_usdc_amount_green_covers_all_debt(
    levg_vault_tools,
    setup_mock_prices,
    register_vault_tokens_with_lego,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_usdc,
    mock_usdc_leverage_vault,
    mock_green_token,
    governance,
    _test,
):
    """Test swappable USDC when GREEN covers all debt."""
    usdc_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_cbbtc.address, usdc_amount, sender=governance.address)
    mock_usdc.approve(mock_usdc_leverage_vault.address, usdc_amount, sender=undy_levg_vault_cbbtc.address)
    mock_usdc_leverage_vault.deposit(usdc_amount, undy_levg_vault_cbbtc.address, sender=undy_levg_vault_cbbtc.address)

    green_amount = 5_000 * EIGHTEEN_DECIMALS
    mock_green_token.mint(undy_levg_vault_cbbtc.address, green_amount, sender=governance.address)

    debt_amount = 3_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, debt_amount)

    result = levg_vault_tools.getSwappableUsdcAmount(undy_levg_vault_cbbtc.address)

    _test(usdc_amount, result, 100)


def test_get_swappable_usdc_amount_green_partially_covers_debt(
    levg_vault_tools,
    setup_mock_prices,
    register_vault_tokens_with_lego,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_usdc,
    mock_usdc_leverage_vault,
    mock_green_token,
    governance,
    _test,
):
    """Test swappable USDC when GREEN only partially covers debt."""
    usdc_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_cbbtc.address, usdc_amount, sender=governance.address)
    mock_usdc.approve(mock_usdc_leverage_vault.address, usdc_amount, sender=undy_levg_vault_cbbtc.address)
    mock_usdc_leverage_vault.deposit(usdc_amount, undy_levg_vault_cbbtc.address, sender=undy_levg_vault_cbbtc.address)

    green_amount = 2_000 * EIGHTEEN_DECIMALS
    mock_green_token.mint(undy_levg_vault_cbbtc.address, green_amount, sender=governance.address)

    debt_amount = 5_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, debt_amount)

    result = levg_vault_tools.getSwappableUsdcAmount(undy_levg_vault_cbbtc.address)

    # GREEN ($2k) partially covers debt ($5k), leaving $3k debt
    # USDC value ($10k) minus remaining debt ($3k) = $7k swappable
    # 7000 USDC in 6 decimals = 7_000_000_000
    remaining_debt = debt_amount - green_amount  # 3000 * 10^18
    usdc_value = usdc_amount * EIGHTEEN_DECIMALS // SIX_DECIMALS  # Convert to 18 decimals for comparison
    expected_swappable_value = usdc_value - remaining_debt
    expected_swappable_usdc = expected_swappable_value * SIX_DECIMALS // EIGHTEEN_DECIMALS

    _test(expected_swappable_usdc, result, 100)


def test_get_swappable_usdc_amount_underwater_returns_zero(
    levg_vault_tools,
    setup_mock_prices,
    register_vault_tokens_with_lego,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_usdc,
    mock_usdc_leverage_vault,
    governance,
):
    """Test swappable USDC returns 0 when underwater."""
    usdc_amount = 5_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_cbbtc.address, usdc_amount, sender=governance.address)
    mock_usdc.approve(mock_usdc_leverage_vault.address, usdc_amount, sender=undy_levg_vault_cbbtc.address)
    mock_usdc_leverage_vault.deposit(usdc_amount, undy_levg_vault_cbbtc.address, sender=undy_levg_vault_cbbtc.address)

    debt_amount = 10_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, debt_amount)

    result = levg_vault_tools.getSwappableUsdcAmount(undy_levg_vault_cbbtc.address)

    assert result == 0


def test_get_swappable_usdc_amount_usdc_vault_returns_zero(
    levg_vault_tools,
    setup_mock_prices,
    register_vault_tokens_with_lego,
    mock_ripe,
    undy_levg_vault_usdc,
    mock_usdc,
    mock_usdc_leverage_vault,
    governance,
):
    """Test USDC vault returns 0 (collateral == leverage asset)."""
    usdc_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_usdc.address, usdc_amount, sender=governance.address)
    mock_usdc.approve(mock_usdc_leverage_vault.address, usdc_amount, sender=undy_levg_vault_usdc.address)
    mock_usdc_leverage_vault.deposit(usdc_amount, undy_levg_vault_usdc.address, sender=undy_levg_vault_usdc.address)
    mock_ripe.setUserDebt(undy_levg_vault_usdc.address, 0)

    result = levg_vault_tools.getSwappableUsdcAmount(undy_levg_vault_usdc.address)

    assert result == 0


################################
# 8. Borrow Helper Tests       #
################################


def test_get_borrow_rate_returns_ripe_rate(
    levg_vault_tools,
    mock_ripe,
    undy_levg_vault_usdc,
):
    """Test getBorrowRate returns rate from Ripe"""
    mock_borrow_rate = 500
    mock_ripe.setBorrowRate(mock_borrow_rate)

    result = levg_vault_tools.getBorrowRate(undy_levg_vault_usdc.address)

    assert result == mock_borrow_rate


def test_get_debt_amount_returns_ripe_debt(
    levg_vault_tools,
    mock_ripe,
    undy_levg_vault_usdc,
):
    """Test getDebtAmount returns debt from Ripe"""
    debt_amount = 5_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_usdc.address, debt_amount)

    result = levg_vault_tools.getDebtAmount(undy_levg_vault_usdc.address)

    assert result == debt_amount


def test_get_debt_amount_returns_zero_when_no_debt(
    levg_vault_tools,
    mock_ripe,
    undy_levg_vault_usdc,
):
    """Test getDebtAmount returns 0 when no debt"""
    mock_ripe.setUserDebt(undy_levg_vault_usdc.address, 0)

    result = levg_vault_tools.getDebtAmount(undy_levg_vault_usdc.address)

    assert result == 0


def test_get_true_max_borrow_amount_returns_min_of_limits(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc,
    governance,
):
    """Test getTrueMaxBorrowAmount returns min of debt ratio limit and Ripe LTV limit"""
    cbbtc_amount = 1 * EIGHT_DECIMALS  # 1 cbBTC = $90,000
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, cbbtc_amount, sender=governance.address)
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, 0)

    # Set Ripe max to a specific value
    ripe_max = 50_000 * EIGHTEEN_DECIMALS
    mock_ripe.setMaxBorrowAmount(undy_levg_vault_cbbtc.address, ripe_max)

    # Get both limits individually
    debt_ratio_limit = levg_vault_tools.getMaxBorrowAmountByMaxDebtRatio(undy_levg_vault_cbbtc.address)
    ripe_ltv_limit = levg_vault_tools.getMaxBorrowAmountByRipeLtv(undy_levg_vault_cbbtc.address)

    result = levg_vault_tools.getTrueMaxBorrowAmount(undy_levg_vault_cbbtc.address)

    # True max should be the minimum of both limits
    assert result == min(debt_ratio_limit, ripe_ltv_limit)


def test_get_max_borrow_amount_by_max_debt_ratio_no_debt(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc,
    governance,
):
    """Test max borrow with no existing debt equals collateral_usd * maxDebtRatio"""
    cbbtc_amount = 1 * EIGHT_DECIMALS  # 1 cbBTC = $90,000
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, cbbtc_amount, sender=governance.address)
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, 0)

    result = levg_vault_tools.getMaxBorrowAmountByMaxDebtRatio(undy_levg_vault_cbbtc.address)

    # Default maxDebtRatio is 100% (10000 / 10000)
    # 1 cbBTC = $90,000 -> max borrow = $90,000 * 100% = $90,000
    expected_max_borrow = 90_000 * EIGHTEEN_DECIMALS
    assert result == expected_max_borrow


def test_get_max_borrow_amount_by_max_debt_ratio_green_offsets_debt(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc,
    mock_green_token,
    governance,
):
    """Test that GREEN offsets debt, increasing borrow capacity by exact amount"""
    cbbtc_amount = 1 * EIGHT_DECIMALS
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, cbbtc_amount, sender=governance.address)

    debt_amount = 30_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, debt_amount)

    # Get max borrow WITHOUT green
    result_without_green = levg_vault_tools.getMaxBorrowAmountByMaxDebtRatio(undy_levg_vault_cbbtc.address)

    # Add GREEN
    green_amount = 10_000 * EIGHTEEN_DECIMALS
    mock_green_token.mint(undy_levg_vault_cbbtc.address, green_amount, sender=governance.address)

    # Get max borrow WITH green
    result_with_green = levg_vault_tools.getMaxBorrowAmountByMaxDebtRatio(undy_levg_vault_cbbtc.address)

    # GREEN should offset debt, increasing capacity by exactly the GREEN amount
    assert result_with_green == result_without_green + green_amount


def test_get_max_borrow_amount_by_max_debt_ratio_with_existing_debt(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc,
    governance,
):
    """Test max borrow calculation with existing debt reduces capacity."""
    cbbtc_amount = 1 * EIGHT_DECIMALS  # 1 cbBTC = $90,000
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, cbbtc_amount, sender=governance.address)

    # First get max borrow with no debt
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, 0)
    result_no_debt = levg_vault_tools.getMaxBorrowAmountByMaxDebtRatio(undy_levg_vault_cbbtc.address)

    # Now add debt and verify capacity is reduced
    debt_amount = 10_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, debt_amount)
    result_with_debt = levg_vault_tools.getMaxBorrowAmountByMaxDebtRatio(undy_levg_vault_cbbtc.address)

    # With debt, remaining capacity should be reduced by exactly the debt amount
    assert result_with_debt == result_no_debt - debt_amount


def test_get_max_borrow_amount_by_ripe_ltv_returns_raw_limit(
    levg_vault_tools,
    mock_ripe,
    undy_levg_vault_usdc,
):
    """Test returns raw Ripe max borrow (no GREEN offset)"""
    ripe_max = 100_000 * EIGHTEEN_DECIMALS
    mock_ripe.setMaxBorrowAmount(undy_levg_vault_usdc.address, ripe_max)

    result = levg_vault_tools.getMaxBorrowAmountByRipeLtv(undy_levg_vault_usdc.address)

    assert result == ripe_max


#####################################
# 9. Combination Query Tests        #
#####################################


def test_get_vault_token_amounts_wallet_and_ripe(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_usdc,
    mock_usdc,
    mock_usdc_collateral_vault,
    governance,
):
    """Test vault token amounts in wallet and Ripe"""
    underlying_amount = 1_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_usdc.address, underlying_amount, sender=governance.address)
    mock_usdc.approve(mock_usdc_collateral_vault.address, underlying_amount, sender=undy_levg_vault_usdc.address)
    vault_token_amount = mock_usdc_collateral_vault.deposit(underlying_amount, undy_levg_vault_usdc.address, sender=undy_levg_vault_usdc.address)

    ripe_vault_token_amount = 500 * SIX_DECIMALS
    mock_ripe.setUserCollateral(undy_levg_vault_usdc.address, mock_usdc_collateral_vault.address, ripe_vault_token_amount)

    (wallet_amount, ripe_amount) = levg_vault_tools.getVaultTokenAmounts(undy_levg_vault_usdc.address, True)

    assert wallet_amount == vault_token_amount
    assert ripe_amount == ripe_vault_token_amount


def test_get_underlying_amounts_all_four_values(
    levg_vault_tools,
    setup_mock_prices,
    register_vault_tokens_with_lego,
    mock_ripe,
    undy_levg_vault_usdc,
    mock_usdc,
    mock_usdc_collateral_vault,
    governance,
    _test,
):
    """Test underlying amounts breakdown with proper lego setup."""
    # Record existing balances (session-scoped fixture may have prior state)
    existing_usdc_balance = mock_usdc.balanceOf(undy_levg_vault_usdc.address)
    existing_vault_token_balance = mock_usdc_collateral_vault.balanceOf(undy_levg_vault_usdc.address)

    wallet_underlying = 1_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_usdc.address, wallet_underlying, sender=governance.address)

    deposit_amount = 500 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_usdc.address, deposit_amount, sender=governance.address)
    mock_usdc.approve(mock_usdc_collateral_vault.address, deposit_amount, sender=undy_levg_vault_usdc.address)
    mock_usdc_collateral_vault.deposit(deposit_amount, undy_levg_vault_usdc.address, sender=undy_levg_vault_usdc.address)

    ripe_underlying = 300 * SIX_DECIMALS
    mock_ripe.setUserCollateral(undy_levg_vault_usdc.address, mock_usdc.address, ripe_underlying)

    ripe_vault_token = 200 * SIX_DECIMALS
    mock_ripe.setUserCollateral(undy_levg_vault_usdc.address, mock_usdc_collateral_vault.address, ripe_vault_token)

    (underlying_wallet, vault_token_wallet_converted, underlying_ripe, vault_token_ripe_converted) = \
        levg_vault_tools.getUnderlyingAmounts(undy_levg_vault_usdc.address, True, False)

    # Assert all 4 return values (account for pre-existing balances)
    assert underlying_wallet == existing_usdc_balance + wallet_underlying
    # vault_token_wallet_converted should include both existing and new vault tokens
    _test(deposit_amount, vault_token_wallet_converted - existing_vault_token_balance, 100)
    assert underlying_ripe == ripe_underlying
    _test(ripe_vault_token, vault_token_ripe_converted, 100)


#####################################
# 10. Edge Cases                    #
#####################################


def test_edge_case_empty_vault_returns_zero(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
):
    """Test that queries on empty vault return zero"""
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, 0)

    result = levg_vault_tools.getTotalUnderlyingAmount(undy_levg_vault_cbbtc.address, True, False)

    assert result == 0


def test_edge_case_decimal_precision_usdc(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_usdc,
    mock_usdc,
    governance,
):
    """Test decimal precision handling for 6 decimal USDC"""
    # Clear ripe collateral state and record existing balance
    mock_ripe.setUserCollateral(undy_levg_vault_usdc.address, mock_usdc.address, 0)
    existing_balance = mock_usdc.balanceOf(undy_levg_vault_usdc.address)

    precise_amount = 123_456
    mock_usdc.mint(undy_levg_vault_usdc.address, precise_amount, sender=governance.address)

    result = levg_vault_tools.getAmountForAsset(undy_levg_vault_usdc.address, mock_usdc.address)

    assert result == existing_balance + precise_amount


def test_edge_case_decimal_precision_cbbtc(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc,
    governance,
):
    """Test decimal precision handling for 8 decimal cbBTC"""
    precise_amount = 12_345_678
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, precise_amount, sender=governance.address)

    result = levg_vault_tools.getAmountForAsset(undy_levg_vault_cbbtc.address, mock_cbbtc.address)

    assert result == precise_amount


#####################################
# 11. Additional Coverage Tests     #
#####################################


def test_get_vault_token_amounts_leverage_asset(
    levg_vault_tools,
    setup_mock_prices,
    register_vault_tokens_with_lego,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_usdc,
    mock_usdc_leverage_vault,
    governance,
):
    """Test getVaultTokenAmounts with _isCollateralAsset=False (leverage asset)."""
    # Deposit USDC into leverage vault to get vault tokens
    underlying_amount = 1_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_cbbtc.address, underlying_amount, sender=governance.address)
    mock_usdc.approve(mock_usdc_leverage_vault.address, underlying_amount, sender=undy_levg_vault_cbbtc.address)
    vault_token_amount = mock_usdc_leverage_vault.deposit(underlying_amount, undy_levg_vault_cbbtc.address, sender=undy_levg_vault_cbbtc.address)

    # Set vault tokens on Ripe
    ripe_vault_token_amount = 500 * SIX_DECIMALS
    mock_ripe.setUserCollateral(undy_levg_vault_cbbtc.address, mock_usdc_leverage_vault.address, ripe_vault_token_amount)

    # Query for leverage asset (isCollateralAsset=False)
    (wallet_amount, ripe_amount) = levg_vault_tools.getVaultTokenAmounts(undy_levg_vault_cbbtc.address, False)

    assert wallet_amount == vault_token_amount
    assert ripe_amount == ripe_vault_token_amount


def test_get_underlying_amounts_leverage_asset(
    levg_vault_tools,
    setup_mock_prices,
    register_vault_tokens_with_lego,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc,
    mock_usdc,
    mock_usdc_leverage_vault,
    governance,
    _test,
):
    """Test getUnderlyingAmounts with _isCollateralAsset=False (leverage vault token).

    Note: When querying leverage asset, the function still uses the levg vault's
    core asset (cbBTC) for "underlying" values, while vault token conversion
    uses the leverage vault token's underlying (USDC).
    """
    # Raw cbBTC in wallet (underlying refers to the levg vault's core asset)
    wallet_cbbtc = 5 * EIGHT_DECIMALS
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, wallet_cbbtc, sender=governance.address)

    # Deposit USDC into leverage vault to get vault tokens
    vault_deposit = 500 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_cbbtc.address, vault_deposit, sender=governance.address)
    mock_usdc.approve(mock_usdc_leverage_vault.address, vault_deposit, sender=undy_levg_vault_cbbtc.address)
    mock_usdc_leverage_vault.deposit(vault_deposit, undy_levg_vault_cbbtc.address, sender=undy_levg_vault_cbbtc.address)

    # Raw cbBTC on Ripe (underlying refers to the levg vault's core asset)
    ripe_cbbtc = 3 * EIGHT_DECIMALS
    mock_ripe.setUserCollateral(undy_levg_vault_cbbtc.address, mock_cbbtc.address, ripe_cbbtc)

    # Leverage vault tokens on Ripe
    ripe_vault_token = 200 * SIX_DECIMALS
    mock_ripe.setUserCollateral(undy_levg_vault_cbbtc.address, mock_usdc_leverage_vault.address, ripe_vault_token)

    # Query for leverage vault token (isCollateralAsset=False)
    (underlying_wallet, vault_token_wallet_converted, underlying_ripe, vault_token_ripe_converted) = \
        levg_vault_tools.getUnderlyingAmounts(undy_levg_vault_cbbtc.address, False, False)

    # "underlying" values are the levg vault's core asset (cbBTC)
    assert underlying_wallet == wallet_cbbtc
    assert underlying_ripe == ripe_cbbtc
    # Vault token values are leverage vault tokens converted to USDC
    _test(vault_deposit, vault_token_wallet_converted, 100)
    _test(ripe_vault_token, vault_token_ripe_converted, 100)


def test_get_green_amounts_sgreen_wallet_converted(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_usdc,
    mock_green_token,
    mock_savings_green_token,
    governance,
):
    """Test getGreenAmounts correctly returns sGREEN in wallet converted to GREEN."""
    # Set no debt
    mock_ripe.setUserDebt(undy_levg_vault_usdc.address, 0)

    # Deposit GREEN into sGREEN (in wallet)
    green_amount = 1_500 * EIGHTEEN_DECIMALS
    mock_green_token.mint(undy_levg_vault_usdc.address, green_amount, sender=governance.address)
    mock_green_token.approve(mock_savings_green_token.address, green_amount, sender=undy_levg_vault_usdc.address)
    mock_savings_green_token.deposit(green_amount, undy_levg_vault_usdc.address, sender=undy_levg_vault_usdc.address)

    # Get sGREEN balance and expected conversion
    sgreen_balance = mock_savings_green_token.balanceOf(undy_levg_vault_usdc.address)
    expected_converted = mock_savings_green_token.previewRedeem(sgreen_balance)

    (user_debt, green_in_wallet, sgreen_wallet_converted, sgreen_ripe_converted) = \
        levg_vault_tools.getGreenAmounts(undy_levg_vault_usdc.address)

    assert user_debt == 0
    assert green_in_wallet == 0  # All GREEN was deposited into sGREEN
    assert sgreen_wallet_converted == expected_converted
    assert sgreen_ripe_converted == 0


def test_should_get_max_total_underlying_returns_higher_or_equal(
    levg_vault_tools,
    setup_mock_prices,
    register_vault_tokens_with_lego,
    undy_levg_vault_cbbtc,
    mock_cbbtc,
    mock_cbbtc_collateral_vault,
    governance,
    _test,
):
    """Test shouldGetMax=True returns >= shouldGetMax=False for getTotalUnderlyingAmount."""
    # Deposit cbBTC into vault to get vault tokens
    vault_deposit = 2 * EIGHT_DECIMALS
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, vault_deposit, sender=governance.address)
    mock_cbbtc.approve(mock_cbbtc_collateral_vault.address, vault_deposit, sender=undy_levg_vault_cbbtc.address)
    mock_cbbtc_collateral_vault.deposit(vault_deposit, undy_levg_vault_cbbtc.address, sender=undy_levg_vault_cbbtc.address)

    safe_result = levg_vault_tools.getTotalUnderlyingAmount(undy_levg_vault_cbbtc.address, True, False)
    max_result = levg_vault_tools.getTotalUnderlyingAmount(undy_levg_vault_cbbtc.address, True, True)

    # max should be >= safe (uses getUnderlyingAmount vs getUnderlyingAmountSafe)
    assert max_result >= safe_result
    # Both should be within tolerance of the deposit
    _test(vault_deposit, max_result, 100)


def test_get_swappable_usdc_leverage_vault_tokens_on_ripe(
    levg_vault_tools,
    setup_mock_prices,
    register_vault_tokens_with_lego,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_usdc,
    mock_usdc_leverage_vault,
    governance,
    _test,
):
    """Test swappable USDC counts leverage vault tokens deposited on Ripe."""
    # Deposit USDC into leverage vault to get vault tokens
    vault_deposit = 5_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_cbbtc.address, vault_deposit, sender=governance.address)
    mock_usdc.approve(mock_usdc_leverage_vault.address, vault_deposit, sender=undy_levg_vault_cbbtc.address)
    vault_token_amount = mock_usdc_leverage_vault.deposit(vault_deposit, undy_levg_vault_cbbtc.address, sender=undy_levg_vault_cbbtc.address)

    # Put vault tokens on Ripe (not the vault tokens themselves, simulate via setUserCollateral)
    mock_ripe.setUserCollateral(undy_levg_vault_cbbtc.address, mock_usdc_leverage_vault.address, vault_token_amount)

    # Clear the vault token balance from wallet (transfer somewhere)
    # For this test, we need to verify the Ripe vault tokens are counted
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, 0)

    result = levg_vault_tools.getSwappableUsdcAmount(undy_levg_vault_cbbtc.address)

    # With no debt, the vault tokens on Ripe should be converted and counted
    # The wallet still has the vault tokens, so total should be 2x
    _test(vault_deposit * 2, result, 100)


#####################################
# 12. getDebtToDepositRatio Tests   #
#####################################


def test_get_debt_to_deposit_ratio_no_debt(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc,
    governance,
):
    """No debt means 0% debt ratio, regardless of deposits."""
    cbbtc_amount = 1 * EIGHT_DECIMALS  # 1 cbBTC = $90,000
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, cbbtc_amount, sender=governance.address)
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, 0)

    result = levg_vault_tools.getDebtToDepositRatio(undy_levg_vault_cbbtc.address)

    assert result == 0


def test_get_debt_to_deposit_ratio_green_covers_debt(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc,
    mock_green_token,
    governance,
):
    """GREEN fully covers debt, net debt is 0, so ratio is 0%."""
    cbbtc_amount = 1 * EIGHT_DECIMALS  # 1 cbBTC = $90,000
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, cbbtc_amount, sender=governance.address)

    debt_amount = 10_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, debt_amount)

    green_amount = 15_000 * EIGHTEEN_DECIMALS
    mock_green_token.mint(undy_levg_vault_cbbtc.address, green_amount, sender=governance.address)

    result = levg_vault_tools.getDebtToDepositRatio(undy_levg_vault_cbbtc.address)

    assert result == 0


def test_get_debt_to_deposit_ratio_50_percent(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc,
    governance,
):
    """$45k debt / $90k deposits = 50% = 5000 basis points."""
    cbbtc_amount = 1 * EIGHT_DECIMALS  # 1 cbBTC = $90,000
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, cbbtc_amount, sender=governance.address)

    debt_amount = 45_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, debt_amount)

    result = levg_vault_tools.getDebtToDepositRatio(undy_levg_vault_cbbtc.address)

    assert result == 5000


def test_get_debt_to_deposit_ratio_green_partially_offsets(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc,
    mock_green_token,
    governance,
):
    """$50k debt - $5k GREEN = $45k net debt / $90k = 50%."""
    cbbtc_amount = 1 * EIGHT_DECIMALS  # 1 cbBTC = $90,000
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, cbbtc_amount, sender=governance.address)

    debt_amount = 50_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, debt_amount)

    green_amount = 5_000 * EIGHTEEN_DECIMALS
    mock_green_token.mint(undy_levg_vault_cbbtc.address, green_amount, sender=governance.address)

    result = levg_vault_tools.getDebtToDepositRatio(undy_levg_vault_cbbtc.address)

    assert result == 5000


def test_get_debt_to_deposit_ratio_usdc_vault_uses_net_user_shares(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_usdc,
    mock_usdc,
    mock_usdc_collateral_vault,
    governance,
    vault_registry,
    starter_agent,
    switchboard_alpha,
):
    """USDC vault uses netUserShares converted to assets.

    Since convertToAssets uses totalAssets (which subtracts debt), the ratio is
    calculated against net equity dynamically based on current state.
    """
    vault = undy_levg_vault_usdc

    # Enable vault operations
    vault_registry.setCanDeposit(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setShouldAutoDeposit(vault.address, False, sender=switchboard_alpha.address)

    # Clear any existing debt
    mock_ripe.setUserDebt(vault.address, 0)

    # Record pre-existing state
    existing_assets = vault.totalAssets()

    # Deposit 100k USDC to set netUserShares
    deposit_amount = 100_000 * SIX_DECIMALS
    mock_usdc.mint(starter_agent.address, deposit_amount, sender=governance.address)
    mock_usdc.approve(vault.address, deposit_amount, sender=starter_agent.address)
    vault.deposit(deposit_amount, starter_agent.address, sender=starter_agent.address)

    # Total assets after deposit (no debt yet)
    total_assets_before_debt = vault.totalAssets()

    # Set debt (18 decimals for GREEN)
    debt_amount = 30_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(vault.address, debt_amount)

    result = levg_vault_tools.getDebtToDepositRatio(
        vault.address,
        mock_usdc.address,                    # _underlyingAsset
        mock_usdc_collateral_vault.address,   # _collateralVaultToken
        0,                                    # _collateralVaultTokenRipeVaultId
        mock_usdc_collateral_vault.address,   # _leverageVaultToken
    )

    # Calculate expected: debt / (totalAssets - debt)
    total_assets_after_debt = total_assets_before_debt - (30_000 * SIX_DECIMALS)
    expected_ratio = (30_000 * SIX_DECIMALS * 10000) // total_assets_after_debt

    assert result == expected_ratio


def test_get_debt_to_deposit_ratio_no_deposits_returns_zero(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
):
    """With no deposits, ratio is 0 (not divide by zero error)."""
    debt_amount = 10_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, debt_amount)

    result = levg_vault_tools.getDebtToDepositRatio(undy_levg_vault_cbbtc.address)

    assert result == 0


def test_get_debt_to_deposit_ratio_over_100_percent(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc,
    governance,
):
    """$135k debt / $90k deposits = 150% = 15000 basis points."""
    cbbtc_amount = 1 * EIGHT_DECIMALS  # 1 cbBTC = $90,000
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, cbbtc_amount, sender=governance.address)

    debt_amount = 135_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, debt_amount)

    result = levg_vault_tools.getDebtToDepositRatio(undy_levg_vault_cbbtc.address)

    assert result == 15000


#####################################
# 13. getDebtUtilization Tests      #
#####################################


def test_get_debt_utilization_no_debt(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc,
    governance,
):
    """No debt means 0% utilization."""
    cbbtc_amount = 1 * EIGHT_DECIMALS
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, cbbtc_amount, sender=governance.address)
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, 0)

    result = levg_vault_tools.getDebtUtilization(undy_levg_vault_cbbtc.address)

    assert result == 0


def test_get_debt_utilization_50_percent_of_max(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc,
    mock_cbbtc_collateral_vault,
    mock_usdc_leverage_vault,
    governance,
):
    """35% debt ratio with 70% max = 50% utilization."""
    # debtRatio = 35% = 3500 bps -> deposit $90k, debt $31.5k
    cbbtc_amount = 1 * EIGHT_DECIMALS  # $90,000
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, cbbtc_amount, sender=governance.address)

    debt_amount = 31_500 * EIGHTEEN_DECIMALS  # 35% of $90k
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, debt_amount)

    # maxDebtRatio = 70% = 7000 bps
    # Pass all params: _underlyingAsset, _collateralVaultToken, _collateralVaultTokenRipeVaultId,
    #                  _leverageVaultToken, _netUserShares, _maxDebtRatio
    result = levg_vault_tools.getDebtUtilization(
        undy_levg_vault_cbbtc.address,
        mock_cbbtc.address,                   # _underlyingAsset
        mock_cbbtc_collateral_vault.address,  # _collateralVaultToken
        0,                                    # _collateralVaultTokenRipeVaultId
        mock_usdc_leverage_vault.address,     # _leverageVaultToken
        0,                                    # _netUserShares
        7000,                                 # _maxDebtRatio
    )

    # 3500 / 7000 = 50% = 5000 bps
    assert result == 5000


def test_get_debt_utilization_at_max(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc,
    mock_cbbtc_collateral_vault,
    mock_usdc_leverage_vault,
    governance,
):
    """70% debt ratio with 70% max = 100% utilization."""
    cbbtc_amount = 1 * EIGHT_DECIMALS  # $90,000
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, cbbtc_amount, sender=governance.address)

    debt_amount = 63_000 * EIGHTEEN_DECIMALS  # 70% of $90k
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, debt_amount)

    result = levg_vault_tools.getDebtUtilization(
        undy_levg_vault_cbbtc.address,
        mock_cbbtc.address,                   # _underlyingAsset
        mock_cbbtc_collateral_vault.address,  # _collateralVaultToken
        0,                                    # _collateralVaultTokenRipeVaultId
        mock_usdc_leverage_vault.address,     # _leverageVaultToken
        0,                                    # _netUserShares
        7000,                                 # _maxDebtRatio
    )

    # 7000 / 7000 = 100% = 10000 bps
    assert result == 10000


def test_get_debt_utilization_over_max(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc,
    mock_cbbtc_collateral_vault,
    mock_usdc_leverage_vault,
    governance,
):
    """84% debt ratio with 70% max = 120% utilization (over limit)."""
    cbbtc_amount = 1 * EIGHT_DECIMALS  # $90,000
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, cbbtc_amount, sender=governance.address)

    debt_amount = 75_600 * EIGHTEEN_DECIMALS  # 84% of $90k
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, debt_amount)

    result = levg_vault_tools.getDebtUtilization(
        undy_levg_vault_cbbtc.address,
        mock_cbbtc.address,                   # _underlyingAsset
        mock_cbbtc_collateral_vault.address,  # _collateralVaultToken
        0,                                    # _collateralVaultTokenRipeVaultId
        mock_usdc_leverage_vault.address,     # _leverageVaultToken
        0,                                    # _netUserShares
        7000,                                 # _maxDebtRatio
    )

    # 8400 / 7000 = 120% = 12000 bps
    assert result == 12000


def test_get_debt_utilization_uses_vault_max_debt_ratio(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc,
    governance,
):
    """When _maxDebtRatio is 0, function fetches from vault's maxDebtRatio()."""
    cbbtc_amount = 1 * EIGHT_DECIMALS  # $90,000
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, cbbtc_amount, sender=governance.address)

    debt_amount = 45_000 * EIGHTEEN_DECIMALS  # 50% of $90k
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, debt_amount)

    # Get the vault's maxDebtRatio to calculate expected utilization
    vault_max_debt_ratio = undy_levg_vault_cbbtc.maxDebtRatio()

    # If vault has no limit, return 0
    if vault_max_debt_ratio == 0:
        expected_result = 0
    else:
        # debtRatio = 5000 (50%), utilization = 5000 * 10000 / vault_max_debt_ratio
        expected_result = 5000 * 10000 // vault_max_debt_ratio

    result = levg_vault_tools.getDebtUtilization(undy_levg_vault_cbbtc.address)

    assert result == expected_result


def test_get_debt_utilization_usdc_vault(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_usdc,
    mock_usdc,
    mock_usdc_collateral_vault,
    governance,
    vault_registry,
    starter_agent,
    switchboard_alpha,
):
    """USDC vault debt utilization.

    Since convertToAssets uses totalAssets (which subtracts debt):
    - We deposit fresh USDC and calculate expected utilization dynamically
    - Account for any pre-existing balance in session-scoped vault
    """
    vault = undy_levg_vault_usdc

    # Enable vault operations
    vault_registry.setCanDeposit(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setShouldAutoDeposit(vault.address, False, sender=switchboard_alpha.address)

    # Clear any existing debt first
    mock_ripe.setUserDebt(vault.address, 0)

    # Record pre-existing state
    existing_assets = vault.totalAssets()

    # Deposit 100k USDC to set netUserShares
    deposit_amount = 100_000 * SIX_DECIMALS
    mock_usdc.mint(starter_agent.address, deposit_amount, sender=governance.address)
    mock_usdc.approve(vault.address, deposit_amount, sender=starter_agent.address)
    vault.deposit(deposit_amount, starter_agent.address, sender=starter_agent.address)

    # Total assets after deposit (no debt yet)
    total_assets_before_debt = vault.totalAssets()
    assert total_assets_before_debt == existing_assets + deposit_amount

    # Debt is in GREEN (18 decimals)
    debt_amount = 40_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(vault.address, debt_amount)

    result = levg_vault_tools.getDebtUtilization(
        vault.address,
        mock_usdc.address,                    # _underlyingAsset
        mock_usdc_collateral_vault.address,   # _collateralVaultToken
        0,                                    # _collateralVaultTokenRipeVaultId
        mock_usdc_collateral_vault.address,   # _leverageVaultToken (same for USDC vault)
        vault.netUserShares(),                # _netUserShares
        8000,                                 # _maxDebtRatio
    )

    # Calculate expected: totalAssets - debt (in USDC terms)
    # totalAssets after debt = total_assets_before_debt - 40k
    total_assets_after_debt = total_assets_before_debt - (40_000 * SIX_DECIMALS)
    # debt ratio = 40k / total_assets_after_debt
    debt_ratio_bps = (40_000 * SIX_DECIMALS * 10000) // total_assets_after_debt
    # utilization = debt_ratio / max_debt_ratio * 10000
    expected_utilization = debt_ratio_bps * 10000 // 8000

    assert result == expected_utilization


###########################################
# 14. getDebtToRipeCollateralRatio Tests  #
###########################################


def test_get_debt_to_ripe_collateral_ratio_no_debt(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
):
    """No debt means 0% ratio regardless of collateral."""
    mock_ripe.setCollateralValue(undy_levg_vault_cbbtc.address, 100_000 * EIGHTEEN_DECIMALS)
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, 0)

    result = levg_vault_tools.getDebtToRipeCollateralRatio(undy_levg_vault_cbbtc.address)

    assert result == 0


def test_get_debt_to_ripe_collateral_ratio_50_percent(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
):
    """$50k debt / $100k collateral = 50%."""
    collateral_value = 100_000 * EIGHTEEN_DECIMALS
    mock_ripe.setCollateralValue(undy_levg_vault_cbbtc.address, collateral_value)

    debt_amount = 50_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, debt_amount)

    result = levg_vault_tools.getDebtToRipeCollateralRatio(undy_levg_vault_cbbtc.address)

    assert result == 5000


def test_get_debt_to_ripe_collateral_ratio_green_offsets(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_green_token,
    governance,
):
    """$50k debt - $10k GREEN = $40k net / $100k collateral = 40%."""
    collateral_value = 100_000 * EIGHTEEN_DECIMALS
    mock_ripe.setCollateralValue(undy_levg_vault_cbbtc.address, collateral_value)

    debt_amount = 50_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, debt_amount)

    green_amount = 10_000 * EIGHTEEN_DECIMALS
    mock_green_token.mint(undy_levg_vault_cbbtc.address, green_amount, sender=governance.address)

    result = levg_vault_tools.getDebtToRipeCollateralRatio(undy_levg_vault_cbbtc.address)

    assert result == 4000


def test_get_debt_to_ripe_collateral_ratio_no_collateral(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
):
    """With no collateral, ratio is 0 (not divide by zero)."""
    mock_ripe.setCollateralValue(undy_levg_vault_cbbtc.address, 0)

    debt_amount = 10_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, debt_amount)

    result = levg_vault_tools.getDebtToRipeCollateralRatio(undy_levg_vault_cbbtc.address)

    assert result == 0


def test_get_debt_to_ripe_collateral_ratio_over_100_percent(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
):
    """$75k debt / $50k collateral = 150%."""
    collateral_value = 50_000 * EIGHTEEN_DECIMALS
    mock_ripe.setCollateralValue(undy_levg_vault_cbbtc.address, collateral_value)

    debt_amount = 75_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, debt_amount)

    result = levg_vault_tools.getDebtToRipeCollateralRatio(undy_levg_vault_cbbtc.address)

    assert result == 15000


#####################################
# 15. getNetUserDebt Tests          #
#####################################


def test_get_net_user_debt_no_debt(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_usdc,
):
    """No debt means net debt is 0."""
    mock_ripe.setUserDebt(undy_levg_vault_usdc.address, 0)

    result = levg_vault_tools.getNetUserDebt(undy_levg_vault_usdc.address)

    assert result == 0


def test_get_net_user_debt_with_debt_no_green(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_usdc,
):
    """Debt with no GREEN returns full debt amount."""
    debt_amount = 10_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_usdc.address, debt_amount)

    result = levg_vault_tools.getNetUserDebt(undy_levg_vault_usdc.address)

    assert result == debt_amount


def test_get_net_user_debt_green_fully_covers_debt(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_usdc,
    mock_green_token,
    governance,
):
    """GREEN fully covers debt, net debt is 0."""
    debt_amount = 5_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_usdc.address, debt_amount)

    green_amount = 10_000 * EIGHTEEN_DECIMALS
    mock_green_token.mint(undy_levg_vault_usdc.address, green_amount, sender=governance.address)

    result = levg_vault_tools.getNetUserDebt(undy_levg_vault_usdc.address)

    assert result == 0


def test_get_net_user_debt_green_exactly_covers_debt(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_usdc,
    mock_green_token,
    governance,
):
    """GREEN exactly equals debt, net debt is 0."""
    debt_amount = 5_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_usdc.address, debt_amount)

    green_amount = 5_000 * EIGHTEEN_DECIMALS
    mock_green_token.mint(undy_levg_vault_usdc.address, green_amount, sender=governance.address)

    result = levg_vault_tools.getNetUserDebt(undy_levg_vault_usdc.address)

    assert result == 0


def test_get_net_user_debt_green_partially_covers_debt(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_usdc,
    mock_green_token,
    governance,
):
    """$10k debt - $3k GREEN = $7k net debt."""
    debt_amount = 10_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_usdc.address, debt_amount)

    green_amount = 3_000 * EIGHTEEN_DECIMALS
    mock_green_token.mint(undy_levg_vault_usdc.address, green_amount, sender=governance.address)

    result = levg_vault_tools.getNetUserDebt(undy_levg_vault_usdc.address)

    expected_net_debt = debt_amount - green_amount
    assert result == expected_net_debt


def test_get_net_user_debt_sgreen_in_wallet_counts(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_usdc,
    mock_green_token,
    mock_savings_green_token,
    governance,
):
    """sGREEN in wallet is converted and offsets debt."""
    debt_amount = 10_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_usdc.address, debt_amount)

    # Deposit GREEN into sGREEN (in wallet)
    green_amount = 5_000 * EIGHTEEN_DECIMALS
    mock_green_token.mint(undy_levg_vault_usdc.address, green_amount, sender=governance.address)
    mock_green_token.approve(mock_savings_green_token.address, green_amount, sender=undy_levg_vault_usdc.address)
    mock_savings_green_token.deposit(green_amount, undy_levg_vault_usdc.address, sender=undy_levg_vault_usdc.address)

    # Get expected converted amount
    sgreen_balance = mock_savings_green_token.balanceOf(undy_levg_vault_usdc.address)
    converted_green = mock_savings_green_token.previewRedeem(sgreen_balance)

    result = levg_vault_tools.getNetUserDebt(undy_levg_vault_usdc.address)

    expected_net_debt = debt_amount - converted_green
    assert result == expected_net_debt


def test_get_net_user_debt_sgreen_on_ripe_counts(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_usdc,
    mock_savings_green_token,
):
    """sGREEN on Ripe is converted and offsets debt."""
    debt_amount = 10_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_usdc.address, debt_amount)

    # Set sGREEN on Ripe
    sgreen_amount = 5_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserCollateral(undy_levg_vault_usdc.address, mock_savings_green_token.address, sgreen_amount)

    # Get expected converted amount
    converted_green = mock_savings_green_token.previewRedeem(sgreen_amount)

    result = levg_vault_tools.getNetUserDebt(undy_levg_vault_usdc.address)

    expected_net_debt = debt_amount - converted_green
    assert result == expected_net_debt


def test_get_net_user_debt_mixed_sources(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_usdc,
    mock_green_token,
    mock_savings_green_token,
    governance,
):
    """GREEN from all sources (wallet, sGREEN wallet, sGREEN Ripe) offset debt."""
    debt_amount = 20_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_usdc.address, debt_amount)

    # 1. GREEN in wallet
    green_wallet = 3_000 * EIGHTEEN_DECIMALS
    mock_green_token.mint(undy_levg_vault_usdc.address, green_wallet, sender=governance.address)

    # 2. Deposit some GREEN into sGREEN (kept in wallet)
    green_for_sgreen = 4_000 * EIGHTEEN_DECIMALS
    mock_green_token.mint(undy_levg_vault_usdc.address, green_for_sgreen, sender=governance.address)
    mock_green_token.approve(mock_savings_green_token.address, green_for_sgreen, sender=undy_levg_vault_usdc.address)
    mock_savings_green_token.deposit(green_for_sgreen, undy_levg_vault_usdc.address, sender=undy_levg_vault_usdc.address)

    # 3. sGREEN on Ripe
    sgreen_ripe = 5_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserCollateral(undy_levg_vault_usdc.address, mock_savings_green_token.address, sgreen_ripe)

    # Calculate total GREEN value
    sgreen_wallet_balance = mock_savings_green_token.balanceOf(undy_levg_vault_usdc.address)
    total_sgreen = sgreen_wallet_balance + sgreen_ripe
    converted_sgreen = mock_savings_green_token.previewRedeem(total_sgreen)
    total_green = green_wallet + converted_sgreen

    result = levg_vault_tools.getNetUserDebt(undy_levg_vault_usdc.address)

    expected_net_debt = debt_amount - total_green
    assert result == expected_net_debt


def test_get_net_user_debt_cbbtc_vault(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_green_token,
    governance,
):
    """Test getNetUserDebt works for cbBTC vault."""
    debt_amount = 50_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, debt_amount)

    green_amount = 20_000 * EIGHTEEN_DECIMALS
    mock_green_token.mint(undy_levg_vault_cbbtc.address, green_amount, sender=governance.address)

    result = levg_vault_tools.getNetUserDebt(undy_levg_vault_cbbtc.address)

    expected_net_debt = debt_amount - green_amount
    assert result == expected_net_debt


def test_get_net_user_debt_weth_vault(
    levg_vault_tools,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_weth,
    mock_green_token,
    governance,
):
    """Test getNetUserDebt works for WETH vault."""
    debt_amount = 100_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_weth.address, debt_amount)

    green_amount = 25_000 * EIGHTEEN_DECIMALS
    mock_green_token.mint(undy_levg_vault_weth.address, green_amount, sender=governance.address)

    result = levg_vault_tools.getNetUserDebt(undy_levg_vault_weth.address)

    expected_net_debt = debt_amount - green_amount
    assert result == expected_net_debt
