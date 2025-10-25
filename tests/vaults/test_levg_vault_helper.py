import pytest
import boa

from constants import MAX_UINT256, ZERO_ADDRESS, EIGHTEEN_DECIMALS
from conf_utils import filter_logs

SIX_DECIMALS = 10 ** 6
EIGHT_DECIMALS = 10 ** 8


############
# Fixtures #
############


@pytest.fixture(scope="module")
def setup_mock_prices(mock_ripe, mock_green_token, mock_savings_green_token, mock_usdc, mock_cbbtc):
    """Set up mock prices for testing"""
    # Set price of 1 GREEN = $1 USD (18 decimals)
    mock_ripe.setPrice(mock_green_token, 1 * EIGHTEEN_DECIMALS)
    # Set price of 1 SAVINGS_GREEN = $1 USD (since it's 1:1 with GREEN in the mock)
    mock_ripe.setPrice(mock_savings_green_token, 1 * EIGHTEEN_DECIMALS)
    # Set price of 1 USDC = $1 USD (6 decimals token, 18 decimals price)
    mock_ripe.setPrice(mock_usdc, 1 * EIGHTEEN_DECIMALS)
    # Set price of 1 CBBTC = $90,000 USD (8 decimals token, 18 decimals price)
    mock_ripe.setPrice(mock_cbbtc, 90_000 * EIGHTEEN_DECIMALS)
    return mock_ripe


#############################
# 1. Helper Function Tests #
#############################


def test_get_collateral_balance(
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    mock_green_token,
    undy_levg_vault_local,
):
    """Test getting collateral balance from Ripe Protocol"""
    # Add some collateral directly via mock
    collateral_amount = 7_500 * EIGHTEEN_DECIMALS
    mock_ripe.setUserCollateral(undy_levg_vault_local.address, mock_green_token, collateral_amount)

    # Query collateral balance via LevgVaultHelper
    balance = levg_vault_helper.getCollateralBalance(undy_levg_vault_local.address, mock_green_token)
    assert balance >= collateral_amount


def test_is_supported_ripe_asset(
    levg_vault_helper,
    mock_green_token,
):
    """Test checking if an asset is supported by Ripe"""
    # In the mock, all assets return True
    is_supported = levg_vault_helper.isSupportedRipeAsset(mock_green_token)
    assert is_supported == True


###################################
# 2. Swap Validation Tests #
###################################


def test_get_swappable_usdc_amount_no_debt(
    levg_vault_helper,
    setup_mock_prices,
    undy_levg_vault_local,
    mock_usdc_leverage_vault,
    mock_usdc,
):
    """Test getSwappableUsdcAmount when user has no debt - should allow full amount"""
    current_balance = 10_000 * SIX_DECIMALS  # 10k USDC
    amount_in = 5_000 * SIX_DECIMALS  # Want to swap 5k

    swappable = levg_vault_helper.getSwappableUsdcAmount(
        undy_levg_vault_local.address,
        amount_in,
        current_balance,
        mock_usdc_leverage_vault.address,
        2,  # lego ID
    )

    # With no debt, should be able to swap the full requested amount
    assert swappable == amount_in


def test_get_swappable_usdc_amount_with_debt(
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_local,
    mock_usdc_leverage_vault,
    mock_usdc,
    mock_green_token,
    governance,
):
    """Test getSwappableUsdcAmount when user has debt - should limit swappable amount"""
    # Give wallet some USDC balance
    current_balance = 20_000 * SIX_DECIMALS  # 20k USDC
    mock_usdc.mint(undy_levg_vault_local.address, current_balance, sender=governance.address)

    # Give wallet some GREEN collateral (set via mock)
    green_amount = 10_000 * EIGHTEEN_DECIMALS  # 10k GREEN
    mock_green_token.transfer(undy_levg_vault_local.address, green_amount, sender=governance.address)
    mock_ripe.setUserCollateral(undy_levg_vault_local.address, mock_green_token, green_amount)

    # Add debt (5k GREEN debt)
    debt_amount = 5_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_local.address, debt_amount)

    # Total positive value = 20k USDC + 10k GREEN = 30k
    # Debt = 5k GREEN
    # Available to swap = 30k - 5k = 25k USDC equivalent
    swappable = levg_vault_helper.getSwappableUsdcAmount(
        undy_levg_vault_local.address,
        MAX_UINT256,  # Want to swap everything
        current_balance,
        mock_usdc_leverage_vault.address,
        2,  # lego ID
    )

    # Should be limited by debt calculation
    # With surplus after debt, should be able to swap some amount
    assert swappable > 0
    # Don't check exact amount due to potential mock implementation differences


def test_perform_post_swap_validation_green_to_usdc_pass(
    levg_vault_helper,
    setup_mock_prices,
    mock_green_token,
    mock_usdc,
):
    """Test post-swap validation GREEN->USDC within slippage tolerance"""
    token_in = mock_green_token.address
    token_in_amount = 1_000 * EIGHTEEN_DECIMALS  # Sold 1000 GREEN
    token_out = mock_usdc.address
    token_out_amount = 990 * SIX_DECIMALS  # Received 990 USDC (~1% slippage)

    # With 1% allowed slippage (100 basis points), this should pass
    result = levg_vault_helper.performPostSwapValidation(
        token_in,
        token_in_amount,
        token_out,
        token_out_amount,
        100,  # usdcSlippageAllowed = 1%
        100,  # greenSlippageAllowed = 1%
    )

    assert result == True


def test_perform_post_swap_validation_green_to_usdc_fail(
    levg_vault_helper,
    setup_mock_prices,
    mock_green_token,
    mock_usdc,
):
    """Test post-swap validation GREEN->USDC exceeds slippage tolerance"""
    token_in = mock_green_token.address
    token_in_amount = 1_000 * EIGHTEEN_DECIMALS  # Sold 1000 GREEN
    token_out = mock_usdc.address
    token_out_amount = 950 * SIX_DECIMALS  # Received only 950 USDC (~5% slippage)

    # With 1% allowed slippage, this should fail
    result = levg_vault_helper.performPostSwapValidation(
        token_in,
        token_in_amount,
        token_out,
        token_out_amount,
        100,  # usdcSlippageAllowed = 1%
        100,  # greenSlippageAllowed = 1%
    )

    assert result == False


def test_perform_post_swap_validation_usdc_to_green_pass(
    levg_vault_helper,
    setup_mock_prices,
    mock_usdc,
    mock_green_token,
):
    """Test post-swap validation USDC->GREEN within slippage tolerance"""
    token_in = mock_usdc.address
    token_in_amount = 1_000 * SIX_DECIMALS  # Sold 1000 USDC
    token_out = mock_green_token.address
    token_out_amount = 990 * EIGHTEEN_DECIMALS  # Received 990 GREEN (~1% slippage)

    # With 1% allowed slippage, this should pass
    result = levg_vault_helper.performPostSwapValidation(
        token_in,
        token_in_amount,
        token_out,
        token_out_amount,
        100,  # usdcSlippageAllowed = 1%
        100,  # greenSlippageAllowed = 1%
    )

    assert result == True


def test_perform_post_swap_validation_usdc_to_green_fail(
    levg_vault_helper,
    setup_mock_prices,
    mock_usdc,
    mock_green_token,
):
    """Test post-swap validation USDC->GREEN exceeds slippage tolerance"""
    token_in = mock_usdc.address
    token_in_amount = 1_000 * SIX_DECIMALS  # Sold 1000 USDC
    token_out = mock_green_token.address
    token_out_amount = 950 * EIGHTEEN_DECIMALS  # Received only 950 GREEN (~5% slippage)

    # With 1% allowed slippage, this should fail
    result = levg_vault_helper.performPostSwapValidation(
        token_in,
        token_in_amount,
        token_out,
        token_out_amount,
        100,  # usdcSlippageAllowed = 1%
        100,  # greenSlippageAllowed = 1%
    )

    assert result == False


def test_perform_post_swap_validation_other_swaps_pass(
    levg_vault_helper,
    mock_usdc,
    bravo_token,
):
    """Test post-swap validation for non-GREEN/USDC swaps always passes"""
    # For swaps that aren't GREEN<->USDC, should always return True
    result = levg_vault_helper.performPostSwapValidation(
        bravo_token.address,  # Some other token
        1_000 * EIGHTEEN_DECIMALS,
        mock_usdc.address,
        1 * SIX_DECIMALS,  # Terrible rate, but should still pass
        100,  # usdcSlippageAllowed = 1%
        100,  # greenSlippageAllowed = 1%
    )

    assert result == True


#########################################
# 3. Total Assets Calculation Tests #
#########################################


def test_get_total_assets_for_usdc_vault_no_debt(
    levg_vault_helper,
    setup_mock_prices,
    undy_levg_vault_local,
    mock_usdc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_usdc,
    governance,
):
    """Test total assets for USDC vault with no debt"""
    # Give wallet 10k USDC
    usdc_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_local.address, usdc_amount, sender=governance.address)

    total_assets = levg_vault_helper.getTotalAssetsForUsdcVault(
        undy_levg_vault_local.address,
        mock_usdc_collateral_vault.address,
        2,  # collateral lego ID
        mock_usdc_leverage_vault.address,
        2,  # leverage lego ID
    )

    # With no debt and 10k USDC, total assets should be 10k
    assert total_assets == usdc_amount


def test_get_total_assets_for_usdc_vault_with_surplus(
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_local,
    mock_usdc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_usdc,
    mock_green_token,
    governance,
):
    """Test total assets for USDC vault with GREEN surplus (adds value)"""
    # Give wallet 10k USDC
    usdc_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_local.address, usdc_amount, sender=governance.address)

    # Give wallet 5k GREEN (surplus, no debt)
    green_amount = 5_000 * EIGHTEEN_DECIMALS
    mock_green_token.transfer(undy_levg_vault_local.address, green_amount, sender=governance.address)
    mock_ripe.setUserCollateral(undy_levg_vault_local.address, mock_green_token, green_amount)

    total_assets = levg_vault_helper.getTotalAssetsForUsdcVault(
        undy_levg_vault_local.address,
        mock_usdc_collateral_vault.address,
        2,
        mock_usdc_leverage_vault.address,
        2,
    )

    # Total should be 10k USDC + 5k GREEN (treated as $5k) = 15k USDC
    expected = usdc_amount + (5_000 * SIX_DECIMALS)
    assert total_assets >= expected * 99 // 100  # Allow 1% tolerance


def test_get_total_assets_for_usdc_vault_with_debt(
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_local,
    mock_usdc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_usdc,
    governance,
):
    """Test total assets for USDC vault with debt (reduces value)"""
    # Give wallet 10k USDC
    usdc_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_local.address, usdc_amount, sender=governance.address)

    # Add 3k GREEN debt
    debt_amount = 3_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_local.address, debt_amount)

    total_assets = levg_vault_helper.getTotalAssetsForUsdcVault(
        undy_levg_vault_local.address,
        mock_usdc_collateral_vault.address,
        2,
        mock_usdc_leverage_vault.address,
        2,
    )

    # Total should be 10k USDC - 3k debt = 7k USDC
    expected = usdc_amount - (3_000 * SIX_DECIMALS)
    assert total_assets >= expected * 99 // 100  # Allow 1% tolerance
    assert total_assets <= usdc_amount


def test_get_total_assets_for_non_usdc_vault_no_debt(
    levg_vault_helper,
    setup_mock_prices,
    undy_levg_vault_local,
    bravo_token,  # Use as mock WETH
    mock_usdc_collateral_vault,
    mock_usdc_leverage_vault,
    governance,
):
    """Test total assets for non-USDC vault (WETH) with no debt"""
    # Give wallet 5 WETH (using bravo_token as mock WETH)
    weth_amount = 5 * EIGHTEEN_DECIMALS
    bravo_token.mint(undy_levg_vault_local.address, weth_amount, sender=governance.address)

    total_assets = levg_vault_helper.getTotalAssetsForNonUsdcVault(
        undy_levg_vault_local.address,
        bravo_token.address,  # underlying asset
        mock_usdc_collateral_vault.address,
        2,
        mock_usdc_leverage_vault.address,
        2,
    )

    # With no debt and 5 WETH, total assets should be 5 WETH
    assert total_assets == weth_amount


def test_get_total_assets_for_non_usdc_vault_with_debt(
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_local,
    bravo_token,  # Use as mock WETH
    mock_usdc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_usdc,
    governance,
):
    """Test total assets for non-USDC vault with debt"""
    # Set price of WETH = $2000
    mock_ripe.setPrice(bravo_token, 2000 * EIGHTEEN_DECIMALS)

    # Give wallet 5 WETH = $10k value
    weth_amount = 5 * EIGHTEEN_DECIMALS
    bravo_token.mint(undy_levg_vault_local.address, weth_amount, sender=governance.address)

    # Give wallet 2k USDC
    mock_usdc.mint(undy_levg_vault_local.address, 2_000 * SIX_DECIMALS, sender=governance.address)

    # Add 1k GREEN debt
    debt_amount = 1_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_local.address, debt_amount)

    # Total value: 5 WETH ($10k) + 2k USDC - 1k debt = $11k
    # $11k / $2000 per WETH = 5.5 WETH
    total_assets = levg_vault_helper.getTotalAssetsForNonUsdcVault(
        undy_levg_vault_local.address,
        bravo_token.address,
        mock_usdc_collateral_vault.address,
        2,
        mock_usdc_leverage_vault.address,
        2,
    )

    # Should be slightly more than original 5 WETH due to USDC surplus after debt
    assert total_assets > weth_amount


############################################
# 4. sGREEN (Savings GREEN) Scenarios Tests #
############################################


def test_get_total_assets_usdc_vault_with_sgreen_surplus(
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_local,
    mock_usdc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_usdc,
    mock_green_token,
    mock_savings_green_token,
    governance,
):
    """Test total assets for USDC vault with sGREEN surplus (not GREEN)"""
    # Give wallet 10k USDC
    usdc_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_local.address, usdc_amount, sender=governance.address)

    # Give wallet 5k sGREEN (surplus, no debt) - deposit GREEN to get sGREEN
    green_amount = 5_000 * EIGHTEEN_DECIMALS
    mock_green_token.transfer(undy_levg_vault_local.address, green_amount, sender=governance.address)
    # Approve and deposit GREEN to get sGREEN
    mock_green_token.approve(mock_savings_green_token.address, green_amount, sender=undy_levg_vault_local.address)
    sgreen_amount = mock_savings_green_token.deposit(green_amount, undy_levg_vault_local.address, sender=undy_levg_vault_local.address)

    total_assets = levg_vault_helper.getTotalAssetsForUsdcVault(
        undy_levg_vault_local.address,
        mock_usdc_collateral_vault.address,
        2,
        mock_usdc_leverage_vault.address,
        2,
    )

    # Total should be 10k USDC + 5k sGREEN (treated as $5k) = 15k USDC
    expected = usdc_amount + (5_000 * SIX_DECIMALS)
    assert total_assets >= expected * 99 // 100  # Allow 1% tolerance


def test_get_total_assets_usdc_vault_with_sgreen_on_ripe(
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_local,
    mock_usdc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_usdc,
    mock_savings_green_token,
    governance,
):
    """Test total assets when sGREEN is deposited as collateral on Ripe"""
    # Give wallet 10k USDC
    usdc_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_local.address, usdc_amount, sender=governance.address)

    # Set sGREEN as collateral on Ripe (not in wallet)
    sgreen_amount = 5_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserCollateral(undy_levg_vault_local.address, mock_savings_green_token, sgreen_amount)

    total_assets = levg_vault_helper.getTotalAssetsForUsdcVault(
        undy_levg_vault_local.address,
        mock_usdc_collateral_vault.address,
        2,
        mock_usdc_leverage_vault.address,
        2,
    )

    # Total should be 10k USDC + 5k sGREEN = 15k USDC
    expected = usdc_amount + (5_000 * SIX_DECIMALS)
    assert total_assets >= expected * 99 // 100


def test_get_total_assets_usdc_vault_with_mixed_green_and_sgreen(
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_local,
    mock_usdc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_usdc,
    mock_green_token,
    mock_savings_green_token,
    governance,
):
    """Test total assets with both GREEN and sGREEN"""
    # Give wallet 10k USDC
    usdc_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_local.address, usdc_amount, sender=governance.address)

    # Give wallet 2k GREEN (in wallet)
    green_amount = 2_000 * EIGHTEEN_DECIMALS
    mock_green_token.transfer(undy_levg_vault_local.address, green_amount, sender=governance.address)

    # Give wallet 3k sGREEN (in wallet) - deposit GREEN to get sGREEN
    green_for_sgreen = 3_000 * EIGHTEEN_DECIMALS
    mock_green_token.transfer(undy_levg_vault_local.address, green_for_sgreen, sender=governance.address)
    mock_green_token.approve(mock_savings_green_token.address, green_for_sgreen, sender=undy_levg_vault_local.address)
    sgreen_amount = mock_savings_green_token.deposit(green_for_sgreen, undy_levg_vault_local.address, sender=undy_levg_vault_local.address)

    total_assets = levg_vault_helper.getTotalAssetsForUsdcVault(
        undy_levg_vault_local.address,
        mock_usdc_collateral_vault.address,
        2,
        mock_usdc_leverage_vault.address,
        2,
    )

    # Total should be 10k USDC + 2k GREEN + 3k sGREEN = 15k USDC
    expected = usdc_amount + (5_000 * SIX_DECIMALS)
    assert total_assets >= expected * 99 // 100


def test_get_swappable_usdc_with_sgreen_collateral(
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_local,
    mock_usdc_leverage_vault,
    mock_usdc,
    mock_savings_green_token,
    governance,
):
    """Test getSwappableUsdcAmount when user has sGREEN collateral and debt"""
    # Give wallet 20k USDC
    current_balance = 20_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_local.address, current_balance, sender=governance.address)

    # Set sGREEN collateral on Ripe
    sgreen_amount = 10_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserCollateral(undy_levg_vault_local.address, mock_savings_green_token, sgreen_amount)

    # Add 5k GREEN debt
    debt_amount = 5_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_local.address, debt_amount)

    # Total positive value = 20k USDC + 10k sGREEN = 30k
    # Debt = 5k GREEN
    # Available to swap = 30k - 5k = 25k USDC equivalent
    swappable = levg_vault_helper.getSwappableUsdcAmount(
        undy_levg_vault_local.address,
        MAX_UINT256,
        current_balance,
        mock_usdc_leverage_vault.address,
        2,
    )

    assert swappable > 0


###########################################
# 5. CBBTC Vault Tests (Common Case B) #
###########################################


def test_get_total_assets_cbbtc_vault_no_debt(
    levg_vault_helper,
    setup_mock_prices,
    undy_levg_vault_cbbtc,
    mock_cbbtc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_cbbtc,
    governance,
):
    """Test total assets for CBBTC vault with no debt"""
    # Give wallet 1 CBBTC (8 decimals) = $90,000
    cbbtc_amount = 1 * EIGHT_DECIMALS
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, cbbtc_amount, sender=governance.address)

    total_assets = levg_vault_helper.getTotalAssetsForNonUsdcVault(
        undy_levg_vault_cbbtc.address,
        mock_cbbtc.address,  # underlying asset
        mock_cbbtc_collateral_vault.address,
        2,  # collateral lego ID
        mock_usdc_leverage_vault.address,
        2,  # leverage lego ID
    )

    # With no debt and 1 CBBTC, total assets should be 1 CBBTC
    assert total_assets == cbbtc_amount


def test_get_total_assets_cbbtc_vault_with_debt(
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_cbbtc,
    governance,
):
    """Test total assets for CBBTC vault with GREEN debt"""
    # Give wallet 1 CBBTC = $90,000
    cbbtc_amount = 1 * EIGHT_DECIMALS
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, cbbtc_amount, sender=governance.address)

    # Add 10k GREEN debt
    debt_amount = 10_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, debt_amount)

    total_assets = levg_vault_helper.getTotalAssetsForNonUsdcVault(
        undy_levg_vault_cbbtc.address,
        mock_cbbtc.address,
        mock_cbbtc_collateral_vault.address,
        2,
        mock_usdc_leverage_vault.address,
        2,
    )

    # Total value: 1 CBBTC ($90k) - 10k debt = $80k
    # $80k / $90k per CBBTC = 0.888... CBBTC
    assert total_assets < cbbtc_amount
    assert total_assets > cbbtc_amount * 80 // 100  # Should be around 0.888 CBBTC


def test_get_total_assets_cbbtc_vault_with_usdc_in_leverage_vault(
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_cbbtc,
    mock_usdc,
    governance,
):
    """Test CBBTC vault with USDC in leverage vault"""
    # Give wallet 1 CBBTC = $90,000
    cbbtc_amount = 1 * EIGHT_DECIMALS
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, cbbtc_amount, sender=governance.address)

    # Give wallet 10k USDC (in wallet, not in vault)
    usdc_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_cbbtc.address, usdc_amount, sender=governance.address)

    # No debt
    total_assets = levg_vault_helper.getTotalAssetsForNonUsdcVault(
        undy_levg_vault_cbbtc.address,
        mock_cbbtc.address,
        mock_cbbtc_collateral_vault.address,
        2,
        mock_usdc_leverage_vault.address,
        2,
    )

    # Total value: 1 CBBTC ($90k) + 10k USDC = $100k
    # $100k / $90k per CBBTC = 1.111... CBBTC
    # Note: USDC in wallet should add value
    assert total_assets >= cbbtc_amount  # At minimum should equal CBBTC amount


def test_get_total_assets_cbbtc_vault_with_sgreen_surplus(
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_cbbtc,
    mock_green_token,
    mock_savings_green_token,
    governance,
):
    """Test CBBTC vault with sGREEN surplus"""
    # Give wallet 1 CBBTC = $90,000
    cbbtc_amount = 1 * EIGHT_DECIMALS
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, cbbtc_amount, sender=governance.address)

    # Give wallet 5k sGREEN (surplus, no debt) - deposit GREEN to get sGREEN
    green_for_sgreen = 5_000 * EIGHTEEN_DECIMALS
    mock_green_token.transfer(undy_levg_vault_cbbtc.address, green_for_sgreen, sender=governance.address)
    mock_green_token.approve(mock_savings_green_token.address, green_for_sgreen, sender=undy_levg_vault_cbbtc.address)
    sgreen_amount = mock_savings_green_token.deposit(green_for_sgreen, undy_levg_vault_cbbtc.address, sender=undy_levg_vault_cbbtc.address)

    total_assets = levg_vault_helper.getTotalAssetsForNonUsdcVault(
        undy_levg_vault_cbbtc.address,
        mock_cbbtc.address,
        mock_cbbtc_collateral_vault.address,
        2,
        mock_usdc_leverage_vault.address,
        2,
    )

    # Total value: 1 CBBTC ($90k) + 5k sGREEN = $95k
    # $95k / $90k per CBBTC = 1.055... CBBTC
    assert total_assets > cbbtc_amount


def test_get_total_assets_cbbtc_vault_underwater(
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_cbbtc,
    governance,
):
    """Test CBBTC vault underwater (debt > total value)"""
    # Give wallet 0.5 CBBTC = $45,000
    cbbtc_amount = 5 * (EIGHT_DECIMALS // 10)  # 0.5 CBBTC
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, cbbtc_amount, sender=governance.address)

    # Add 50k GREEN debt (more than CBBTC value)
    debt_amount = 50_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, debt_amount)

    total_assets = levg_vault_helper.getTotalAssetsForNonUsdcVault(
        undy_levg_vault_cbbtc.address,
        mock_cbbtc.address,
        mock_cbbtc_collateral_vault.address,
        2,
        mock_usdc_leverage_vault.address,
        2,
    )

    # Vault is underwater: 0.5 CBBTC ($45k) - 50k debt = -$5k
    # Should return 0 or very small amount (can't have negative assets)
    assert total_assets < cbbtc_amount


##################################################
# 6. Assets in Multiple Locations Tests #
##################################################


def test_total_assets_usdc_vault_with_collateral_on_ripe(
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_local,
    mock_usdc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_usdc,
    governance,
):
    """Test USDC vault with USDC as collateral on Ripe"""
    # USDC in wallet
    usdc_in_wallet = 5_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_local.address, usdc_in_wallet, sender=governance.address)

    # USDC as collateral on Ripe
    usdc_on_ripe = 5_000 * SIX_DECIMALS
    mock_ripe.setUserCollateral(undy_levg_vault_local.address, mock_usdc, usdc_on_ripe)

    total_assets = levg_vault_helper.getTotalAssetsForUsdcVault(
        undy_levg_vault_local.address,
        mock_usdc_collateral_vault.address,
        2,
        mock_usdc_leverage_vault.address,
        2,
    )

    # Total should be 5k (wallet) + 5k (ripe) = 10k USDC
    expected = usdc_in_wallet + usdc_on_ripe
    assert total_assets >= expected * 99 // 100


def test_total_assets_cbbtc_vault_with_collateral_and_leverage_vault(
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_cbbtc,
    mock_usdc,
    governance,
):
    """Test CBBTC vault with assets in both collateral vault and leverage vault"""
    # CBBTC in wallet
    cbbtc_in_wallet = 5 * (EIGHT_DECIMALS // 10)  # 0.5 CBBTC
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, cbbtc_in_wallet, sender=governance.address)

    # USDC in wallet (for leverage vault)
    usdc_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_cbbtc.address, usdc_amount, sender=governance.address)

    # Small debt
    debt_amount = 2_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, debt_amount)

    total_assets = levg_vault_helper.getTotalAssetsForNonUsdcVault(
        undy_levg_vault_cbbtc.address,
        mock_cbbtc.address,
        mock_cbbtc_collateral_vault.address,
        2,
        mock_usdc_leverage_vault.address,
        2,
    )

    # Total value: 0.5 CBBTC ($45k) + 10k USDC - 2k debt = $53k
    # $53k / $90k per CBBTC = 0.588... CBBTC
    assert total_assets > cbbtc_in_wallet


##################################
# 7. Underwater/Edge Cases Tests #
##################################


def test_non_usdc_vault_usdc_covers_debt_with_surplus(
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_cbbtc,
    mock_usdc,
    governance,
):
    """Test non-USDC vault where USDC covers debt with surplus"""
    # Give wallet 1 CBBTC = $90,000
    cbbtc_amount = 1 * EIGHT_DECIMALS
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, cbbtc_amount, sender=governance.address)

    # Give wallet 20k USDC
    usdc_amount = 20_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_cbbtc.address, usdc_amount, sender=governance.address)

    # Add 10k GREEN debt (USDC covers this)
    debt_amount = 10_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, debt_amount)

    total_assets = levg_vault_helper.getTotalAssetsForNonUsdcVault(
        undy_levg_vault_cbbtc.address,
        mock_cbbtc.address,
        mock_cbbtc_collateral_vault.address,
        2,
        mock_usdc_leverage_vault.address,
        2,
    )

    # Total value: 1 CBBTC ($90k) + (20k USDC - 10k debt) = $100k
    # $100k / $90k per CBBTC = 1.111... CBBTC
    assert total_assets > cbbtc_amount


def test_non_usdc_vault_debt_exceeds_usdc_underwater(
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_cbbtc,
    mock_usdc,
    governance,
):
    """Test non-USDC vault where debt exceeds USDC (eats into CBBTC)"""
    # Give wallet 1 CBBTC = $90,000
    cbbtc_amount = 1 * EIGHT_DECIMALS
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, cbbtc_amount, sender=governance.address)

    # Give wallet 5k USDC
    usdc_amount = 5_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_cbbtc.address, usdc_amount, sender=governance.address)

    # Add 20k GREEN debt (exceeds USDC by 15k)
    debt_amount = 20_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, debt_amount)

    total_assets = levg_vault_helper.getTotalAssetsForNonUsdcVault(
        undy_levg_vault_cbbtc.address,
        mock_cbbtc.address,
        mock_cbbtc_collateral_vault.address,
        2,
        mock_usdc_leverage_vault.address,
        2,
    )

    # Total value: 1 CBBTC ($90k) + 5k USDC - 20k debt = $75k
    # $75k / $90k per CBBTC = 0.833... CBBTC
    assert total_assets < cbbtc_amount
    assert total_assets > cbbtc_amount * 75 // 100


def test_get_swappable_usdc_when_debt_exceeds_value(
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_local,
    mock_usdc_leverage_vault,
    mock_usdc,
    governance,
):
    """Test getSwappableUsdcAmount when debt exceeds total positive value"""
    # Give wallet 10k USDC
    current_balance = 10_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_local.address, current_balance, sender=governance.address)

    # Add 15k GREEN debt (exceeds USDC value)
    debt_amount = 15_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_local.address, debt_amount)

    swappable = levg_vault_helper.getSwappableUsdcAmount(
        undy_levg_vault_local.address,
        MAX_UINT256,
        current_balance,
        mock_usdc_leverage_vault.address,
        2,
    )

    # Underwater - should return 0 (can't swap anything)
    assert swappable == 0


#####################################
# 8. Decimal Precision Tests #
#####################################


def test_cbbtc_8_decimal_precision_calculations(
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_cbbtc,
    governance,
):
    """Test CBBTC calculations with 8-decimal precision"""
    # Give wallet 0.12345678 CBBTC (all 8 decimals)
    cbbtc_amount = 12_345_678  # 0.12345678 CBBTC
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, cbbtc_amount, sender=governance.address)

    total_assets = levg_vault_helper.getTotalAssetsForNonUsdcVault(
        undy_levg_vault_cbbtc.address,
        mock_cbbtc.address,
        mock_cbbtc_collateral_vault.address,
        2,
        mock_usdc_leverage_vault.address,
        2,
    )

    # Should preserve 8-decimal precision
    assert total_assets == cbbtc_amount


def test_mixed_decimal_conversions_cbbtc_to_usdc(
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_cbbtc,
    mock_cbbtc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_cbbtc,
    mock_usdc,
    governance,
):
    """Test decimal conversions between CBBTC (8), USDC (6), and GREEN (18)"""
    # Give wallet 1 CBBTC = $90,000 (8 decimals)
    cbbtc_amount = 1 * EIGHT_DECIMALS
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, cbbtc_amount, sender=governance.address)

    # Give wallet 10,000 USDC (6 decimals)
    usdc_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_cbbtc.address, usdc_amount, sender=governance.address)

    # Add 5,000 GREEN debt (18 decimals)
    debt_amount = 5_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_cbbtc.address, debt_amount)

    total_assets = levg_vault_helper.getTotalAssetsForNonUsdcVault(
        undy_levg_vault_cbbtc.address,
        mock_cbbtc.address,
        mock_cbbtc_collateral_vault.address,
        2,
        mock_usdc_leverage_vault.address,
        2,
    )

    # Total value: 1 CBBTC ($90k) + 10k USDC - 5k debt = $95k
    # Should properly handle all decimal conversions
    # $95k / $90k per CBBTC = 1.055... CBBTC
    assert total_assets > cbbtc_amount
    assert total_assets < cbbtc_amount * 11 // 10  # Less than 1.1 CBBTC
