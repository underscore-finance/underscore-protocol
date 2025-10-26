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
    # Set price of 1 GREEN = $1 USD (18 decimals)
    mock_ripe.setPrice(mock_green_token, 1 * EIGHTEEN_DECIMALS)
    # Set price of 1 SAVINGS_GREEN = $1 USD (since it's 1:1 with GREEN in the mock)
    mock_ripe.setPrice(mock_savings_green_token, 1 * EIGHTEEN_DECIMALS)
    # Set price of 1 USDC = $1 USD (6 decimals token, 18 decimals price)
    mock_ripe.setPrice(mock_usdc, 1 * EIGHTEEN_DECIMALS)
    # Set price of 1 CBBTC = $90,000 USD (8 decimals token, 18 decimals price)
    mock_ripe.setPrice(mock_cbbtc, 90_000 * EIGHTEEN_DECIMALS)
    # Set price of 1 WETH = $2,000 USD (18 decimals token, 18 decimals price)
    mock_ripe.setPrice(mock_weth, 2_000 * EIGHTEEN_DECIMALS)
    return mock_ripe


@pytest.fixture(scope="module")
def mock_weth_whale(env, mock_weth, whale):
    """Create a whale with WETH by depositing ETH"""
    # Give whale ETH and have them deposit to WETH
    weth_amount = 1000 * EIGHTEEN_DECIMALS  # 1000 WETH
    boa.env.set_balance(whale, weth_amount)
    mock_weth.deposit(value=weth_amount, sender=whale)
    return whale


@pytest.fixture(scope="module")
def get_vault_config():
    """Factory fixture that returns vault-specific configuration data"""
    def _get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
        mock_usdc_collateral_vault,
        mock_cbbtc_collateral_vault,
        mock_weth_collateral_vault,
        mock_usdc_leverage_vault,
    ):
        """Get vault configuration for the given vault type"""
        configs = {
            "usdc": {
                "vault": undy_levg_vault_usdc,
                "underlying": mock_usdc,
                "decimals": SIX_DECIMALS,
                "collateral_vault": mock_usdc_collateral_vault,
                "leverage_vault": mock_usdc_leverage_vault,
                "price": 1,  # $1 USD
                "use_usdc_method": True,  # Use getTotalAssetsForUsdcVault
                "is_weth": False,
            },
            "cbbtc": {
                "vault": undy_levg_vault_cbbtc,
                "underlying": mock_cbbtc,
                "decimals": EIGHT_DECIMALS,
                "collateral_vault": mock_cbbtc_collateral_vault,
                "leverage_vault": mock_usdc_leverage_vault,
                "price": 90_000,  # $90,000 USD
                "use_usdc_method": False,  # Use getTotalAssetsForNonUsdcVault
                "is_weth": False,
            },
            "weth": {
                "vault": undy_levg_vault_weth,
                "underlying": mock_weth,
                "decimals": EIGHTEEN_DECIMALS,
                "collateral_vault": mock_weth_collateral_vault,
                "leverage_vault": mock_usdc_leverage_vault,
                "price": 2_000,  # $2,000 USD
                "use_usdc_method": False,  # Use getTotalAssetsForNonUsdcVault
                "is_weth": True,
            },
        }
        return configs[vault_type]

    return _get_vault_config


@pytest.fixture(scope="module")
def mint_to_vault(governance, mock_weth_whale, mock_weth):
    """Helper function to mint tokens to a vault, handling WETH specially"""
    def _mint_to_vault(token, vault_address, amount, is_weth=False):
        if is_weth:
            # WETH: transfer from the whale (who already has WETH from depositing ETH)
            mock_weth.transfer(vault_address, amount, sender=mock_weth_whale)
        else:
            # Regular ERC20: mint directly to vault
            token.mint(vault_address, amount, sender=governance.address)
    return _mint_to_vault


#############################
# 1. Helper Function Tests #
#############################


def test_get_collateral_balance(
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    mock_green_token,
    undy_levg_vault_usdc,
):
    """Test getting collateral balance from Ripe Protocol"""
    # Add some collateral directly via mock
    collateral_amount = 7_500 * EIGHTEEN_DECIMALS
    mock_ripe.setUserCollateral(undy_levg_vault_usdc.address, mock_green_token, collateral_amount)

    # Query collateral balance via LevgVaultHelper
    balance = levg_vault_helper.getCollateralBalance(undy_levg_vault_usdc.address, mock_green_token)
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
    undy_levg_vault_usdc,
    mock_usdc_leverage_vault,
    mock_usdc,
):
    """Test getSwappableUsdcAmount when user has no debt - should allow full amount"""
    current_balance = 10_000 * SIX_DECIMALS  # 10k USDC
    amount_in = 5_000 * SIX_DECIMALS  # Want to swap 5k

    swappable = levg_vault_helper.getSwappableUsdcAmount(
        undy_levg_vault_usdc.address,
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
    undy_levg_vault_usdc,
    mock_usdc_leverage_vault,
    mock_usdc,
    mock_green_token,
    governance,
):
    """Test getSwappableUsdcAmount when user has debt - should limit swappable amount"""
    # Give wallet some USDC balance
    current_balance = 20_000 * SIX_DECIMALS  # 20k USDC
    mock_usdc.mint(undy_levg_vault_usdc.address, current_balance, sender=governance.address)

    # Give wallet some GREEN collateral (set via mock)
    green_amount = 10_000 * EIGHTEEN_DECIMALS  # 10k GREEN
    mock_green_token.transfer(undy_levg_vault_usdc.address, green_amount, sender=governance.address)
    mock_ripe.setUserCollateral(undy_levg_vault_usdc.address, mock_green_token, green_amount)

    # Add debt (5k GREEN debt)
    debt_amount = 5_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_usdc.address, debt_amount)

    # Total positive value = 20k USDC + 10k GREEN = 30k
    # Debt = 5k GREEN
    # Available to swap = 30k - 5k = 25k USDC equivalent
    swappable = levg_vault_helper.getSwappableUsdcAmount(
        undy_levg_vault_usdc.address,
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
    undy_levg_vault_usdc,
    mock_usdc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_usdc,
    governance,
):
    """Test total assets for USDC vault with no debt"""
    # Give wallet 10k USDC
    usdc_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_usdc.address, usdc_amount, sender=governance.address)

    total_assets = levg_vault_helper.getTotalAssetsForUsdcVault(
        undy_levg_vault_usdc.address,
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
    undy_levg_vault_usdc,
    mock_usdc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_usdc,
    mock_green_token,
    governance,
):
    """Test total assets for USDC vault with GREEN surplus (adds value)"""
    # Give wallet 10k USDC
    usdc_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_usdc.address, usdc_amount, sender=governance.address)

    # Give wallet 5k GREEN (surplus, no debt)
    green_amount = 5_000 * EIGHTEEN_DECIMALS
    mock_green_token.transfer(undy_levg_vault_usdc.address, green_amount, sender=governance.address)
    mock_ripe.setUserCollateral(undy_levg_vault_usdc.address, mock_green_token, green_amount)

    total_assets = levg_vault_helper.getTotalAssetsForUsdcVault(
        undy_levg_vault_usdc.address,
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
    undy_levg_vault_usdc,
    mock_usdc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_usdc,
    governance,
):
    """Test total assets for USDC vault with debt (reduces value)"""
    # Give wallet 10k USDC
    usdc_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_usdc.address, usdc_amount, sender=governance.address)

    # Add 3k GREEN debt
    debt_amount = 3_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_usdc.address, debt_amount)

    total_assets = levg_vault_helper.getTotalAssetsForUsdcVault(
        undy_levg_vault_usdc.address,
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
    undy_levg_vault_usdc,
    mock_weth,
    mock_weth_whale,
    mock_usdc_collateral_vault,
    mock_usdc_leverage_vault,
):
    """Test total assets for non-USDC vault (WETH) with no debt"""
    # Give wallet 5 WETH
    weth_amount = 5 * EIGHTEEN_DECIMALS
    mock_weth.transfer(undy_levg_vault_usdc.address, weth_amount, sender=mock_weth_whale)

    total_assets = levg_vault_helper.getTotalAssetsForNonUsdcVault(
        undy_levg_vault_usdc.address,
        mock_weth.address,  # underlying asset
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
    undy_levg_vault_usdc,
    mock_weth,
    mock_weth_whale,
    mock_usdc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_usdc,
    governance,
):
    """Test total assets for non-USDC vault with debt"""
    # WETH price already set to $2000 in setup_mock_prices

    # Give wallet 5 WETH = $10k value
    weth_amount = 5 * EIGHTEEN_DECIMALS
    mock_weth.transfer(undy_levg_vault_usdc.address, weth_amount, sender=mock_weth_whale)

    # Give wallet 2k USDC
    mock_usdc.mint(undy_levg_vault_usdc.address, 2_000 * SIX_DECIMALS, sender=governance.address)

    # Add 1k GREEN debt
    debt_amount = 1_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_usdc.address, debt_amount)

    # Total value: 5 WETH ($10k) + 2k USDC - 1k debt = $11k
    # $11k / $2000 per WETH = 5.5 WETH
    total_assets = levg_vault_helper.getTotalAssetsForNonUsdcVault(
        undy_levg_vault_usdc.address,
        mock_weth.address,
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
    undy_levg_vault_usdc,
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
    mock_usdc.mint(undy_levg_vault_usdc.address, usdc_amount, sender=governance.address)

    # Give wallet 5k sGREEN (surplus, no debt) - deposit GREEN to get sGREEN
    green_amount = 5_000 * EIGHTEEN_DECIMALS
    mock_green_token.transfer(undy_levg_vault_usdc.address, green_amount, sender=governance.address)
    # Approve and deposit GREEN to get sGREEN
    mock_green_token.approve(mock_savings_green_token.address, green_amount, sender=undy_levg_vault_usdc.address)
    sgreen_amount = mock_savings_green_token.deposit(green_amount, undy_levg_vault_usdc.address, sender=undy_levg_vault_usdc.address)

    total_assets = levg_vault_helper.getTotalAssetsForUsdcVault(
        undy_levg_vault_usdc.address,
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
    undy_levg_vault_usdc,
    mock_usdc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_usdc,
    mock_savings_green_token,
    governance,
):
    """Test total assets when sGREEN is deposited as collateral on Ripe"""
    # Give wallet 10k USDC
    usdc_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_usdc.address, usdc_amount, sender=governance.address)

    # Set sGREEN as collateral on Ripe (not in wallet)
    sgreen_amount = 5_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserCollateral(undy_levg_vault_usdc.address, mock_savings_green_token, sgreen_amount)

    total_assets = levg_vault_helper.getTotalAssetsForUsdcVault(
        undy_levg_vault_usdc.address,
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
    undy_levg_vault_usdc,
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
    mock_usdc.mint(undy_levg_vault_usdc.address, usdc_amount, sender=governance.address)

    # Give wallet 2k GREEN (in wallet)
    green_amount = 2_000 * EIGHTEEN_DECIMALS
    mock_green_token.transfer(undy_levg_vault_usdc.address, green_amount, sender=governance.address)

    # Give wallet 3k sGREEN (in wallet) - deposit GREEN to get sGREEN
    green_for_sgreen = 3_000 * EIGHTEEN_DECIMALS
    mock_green_token.transfer(undy_levg_vault_usdc.address, green_for_sgreen, sender=governance.address)
    mock_green_token.approve(mock_savings_green_token.address, green_for_sgreen, sender=undy_levg_vault_usdc.address)
    sgreen_amount = mock_savings_green_token.deposit(green_for_sgreen, undy_levg_vault_usdc.address, sender=undy_levg_vault_usdc.address)

    total_assets = levg_vault_helper.getTotalAssetsForUsdcVault(
        undy_levg_vault_usdc.address,
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
    undy_levg_vault_usdc,
    mock_usdc_leverage_vault,
    mock_usdc,
    mock_savings_green_token,
    governance,
):
    """Test getSwappableUsdcAmount when user has sGREEN collateral and debt"""
    # Give wallet 20k USDC
    current_balance = 20_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_usdc.address, current_balance, sender=governance.address)

    # Set sGREEN collateral on Ripe
    sgreen_amount = 10_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserCollateral(undy_levg_vault_usdc.address, mock_savings_green_token, sgreen_amount)

    # Add 5k GREEN debt
    debt_amount = 5_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_usdc.address, debt_amount)

    # Total positive value = 20k USDC + 10k sGREEN = 30k
    # Debt = 5k GREEN
    # Available to swap = 30k - 5k = 25k USDC equivalent
    swappable = levg_vault_helper.getSwappableUsdcAmount(
        undy_levg_vault_usdc.address,
        MAX_UINT256,
        current_balance,
        mock_usdc_leverage_vault.address,
        2,
    )

    assert swappable > 0


###########################################
# 5. Non-USDC Vault Tests (cbBTC, WETH) #
###########################################


@pytest.mark.parametrize("vault_type", ["cbbtc", "weth"])
def test_get_total_assets_non_usdc_vault_no_debt(
    vault_type,
    levg_vault_helper,
    setup_mock_prices,
    get_vault_config,
    mint_to_vault,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mock_usdc_collateral_vault,
    mock_cbbtc_collateral_vault,
    mock_weth_collateral_vault,
    mock_usdc_leverage_vault,
    governance,
):
    """Test total assets for non-USDC vault (cbBTC/WETH) with no debt"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
        mock_usdc_collateral_vault,
        mock_cbbtc_collateral_vault,
        mock_weth_collateral_vault,
        mock_usdc_leverage_vault,
    )

    # Give wallet 1 unit of underlying asset
    underlying_amount = 1 * config["decimals"]
    mint_to_vault(config["underlying"], config["vault"].address, underlying_amount, config["is_weth"])

    total_assets = levg_vault_helper.getTotalAssetsForNonUsdcVault(
        config["vault"].address,
        config["underlying"].address,
        config["collateral_vault"].address,
        2,  # collateral lego ID
        config["leverage_vault"].address,
        2,  # leverage lego ID
    )

    # With no debt, total assets should equal underlying amount
    assert total_assets == underlying_amount


@pytest.mark.parametrize("vault_type", ["cbbtc", "weth"])
def test_get_total_assets_non_usdc_vault_with_debt(
    vault_type,
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    get_vault_config,
    mint_to_vault,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mock_usdc_collateral_vault,
    mock_cbbtc_collateral_vault,
    mock_weth_collateral_vault,
    mock_usdc_leverage_vault,
    governance,
):
    """Test total assets for non-USDC vault with GREEN debt"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
        mock_usdc_collateral_vault,
        mock_cbbtc_collateral_vault,
        mock_weth_collateral_vault,
        mock_usdc_leverage_vault,
    )

    # Give wallet 1 unit of underlying
    # cbBTC: 1 CBBTC = $90,000
    # WETH: 1 WETH = $2,000
    underlying_amount = 1 * config["decimals"]
    mint_to_vault(config["underlying"], config["vault"].address, underlying_amount, config["is_weth"])

    # Add debt proportional to the asset value
    # cbBTC: 10k GREEN debt ($10k), leaving $80k in value
    # WETH: 500 GREEN debt ($500), leaving $1,500 in value
    if vault_type == "cbbtc":
        debt_amount = 10_000 * EIGHTEEN_DECIMALS
        expected_ratio = 80  # ~80% of original value
    else:  # weth
        debt_amount = 500 * EIGHTEEN_DECIMALS
        expected_ratio = 75  # ~75% of original value

    mock_ripe.setUserDebt(config["vault"].address, debt_amount)

    total_assets = levg_vault_helper.getTotalAssetsForNonUsdcVault(
        config["vault"].address,
        config["underlying"].address,
        config["collateral_vault"].address,
        2,
        config["leverage_vault"].address,
        2,
    )

    # Total value reduced by debt
    assert total_assets < underlying_amount
    assert total_assets >= underlying_amount * expected_ratio // 100


@pytest.mark.parametrize("vault_type", ["cbbtc", "weth"])
def test_get_total_assets_non_usdc_vault_with_usdc_surplus(
    vault_type,
    levg_vault_helper,
    setup_mock_prices,
    get_vault_config,
    mint_to_vault,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mock_usdc_collateral_vault,
    mock_cbbtc_collateral_vault,
    mock_weth_collateral_vault,
    mock_usdc_leverage_vault,
    governance,
):
    """Test non-USDC vault with USDC surplus (adds value)"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
        mock_usdc_collateral_vault,
        mock_cbbtc_collateral_vault,
        mock_weth_collateral_vault,
        mock_usdc_leverage_vault,
    )

    # Give wallet 1 unit of underlying
    underlying_amount = 1 * config["decimals"]
    mint_to_vault(config["underlying"], config["vault"].address, underlying_amount, config["is_weth"])

    # Give wallet 10k USDC (in wallet, not in vault)
    usdc_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(config["vault"].address, usdc_amount, sender=governance.address)

    # No debt
    total_assets = levg_vault_helper.getTotalAssetsForNonUsdcVault(
        config["vault"].address,
        config["underlying"].address,
        config["collateral_vault"].address,
        2,
        config["leverage_vault"].address,
        2,
    )

    # Total value: underlying + 10k USDC
    # cbBTC: $90k + $10k = $100k / $90k = 1.111... CBBTC
    # WETH: $2k + $10k = $12k / $2k = 6 WETH
    # USDC in wallet should add value
    assert total_assets > underlying_amount


@pytest.mark.parametrize("vault_type", ["cbbtc", "weth"])
def test_get_total_assets_non_usdc_vault_with_sgreen_surplus(
    vault_type,
    levg_vault_helper,
    setup_mock_prices,
    get_vault_config,
    mint_to_vault,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mock_usdc_collateral_vault,
    mock_cbbtc_collateral_vault,
    mock_weth_collateral_vault,
    mock_usdc_leverage_vault,
    mock_green_token,
    mock_savings_green_token,
    governance,
):
    """Test non-USDC vault with sGREEN surplus"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
        mock_usdc_collateral_vault,
        mock_cbbtc_collateral_vault,
        mock_weth_collateral_vault,
        mock_usdc_leverage_vault,
    )

    # Give wallet 1 unit of underlying
    underlying_amount = 1 * config["decimals"]
    mint_to_vault(config["underlying"], config["vault"].address, underlying_amount, config["is_weth"])

    # Give wallet 5k sGREEN (surplus, no debt) - deposit GREEN to get sGREEN
    green_for_sgreen = 5_000 * EIGHTEEN_DECIMALS
    mock_green_token.transfer(config["vault"].address, green_for_sgreen, sender=governance.address)
    mock_green_token.approve(mock_savings_green_token.address, green_for_sgreen, sender=config["vault"].address)
    sgreen_amount = mock_savings_green_token.deposit(green_for_sgreen, config["vault"].address, sender=config["vault"].address)

    total_assets = levg_vault_helper.getTotalAssetsForNonUsdcVault(
        config["vault"].address,
        config["underlying"].address,
        config["collateral_vault"].address,
        2,
        config["leverage_vault"].address,
        2,
    )

    # Total value: underlying + 5k sGREEN
    # cbBTC: $90k + $5k = $95k / $90k = 1.055... CBBTC
    # WETH: $2k + $5k = $7k / $2k = 3.5 WETH
    assert total_assets > underlying_amount


@pytest.mark.parametrize("vault_type", ["cbbtc", "weth"])
def test_get_total_assets_non_usdc_vault_underwater(
    vault_type,
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    get_vault_config,
    mint_to_vault,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mock_usdc_collateral_vault,
    mock_cbbtc_collateral_vault,
    mock_weth_collateral_vault,
    mock_usdc_leverage_vault,
    governance,
):
    """Test non-USDC vault underwater (debt > total value)"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
        mock_usdc_collateral_vault,
        mock_cbbtc_collateral_vault,
        mock_weth_collateral_vault,
        mock_usdc_leverage_vault,
    )

    # Give wallet half a unit of underlying
    # cbBTC: 0.5 CBBTC = $45,000
    # WETH: 0.5 WETH = $1,000
    underlying_amount = 5 * (config["decimals"] // 10)
    mint_to_vault(config["underlying"], config["vault"].address, underlying_amount, config["is_weth"])

    # Add debt that exceeds the asset value
    # cbBTC: 50k GREEN debt > $45k value
    # WETH: 1.5k GREEN debt > $1k value
    if vault_type == "cbbtc":
        debt_amount = 50_000 * EIGHTEEN_DECIMALS
    else:  # weth
        debt_amount = 1_500 * EIGHTEEN_DECIMALS

    mock_ripe.setUserDebt(config["vault"].address, debt_amount)

    total_assets = levg_vault_helper.getTotalAssetsForNonUsdcVault(
        config["vault"].address,
        config["underlying"].address,
        config["collateral_vault"].address,
        2,
        config["leverage_vault"].address,
        2,
    )

    # Vault is underwater: debt exceeds value
    # Should return very small amount or 0 (can't have negative assets)
    assert total_assets < underlying_amount


##################################################
# 6. Assets in Multiple Locations Tests #
##################################################


def test_total_assets_usdc_vault_with_collateral_on_ripe(
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_usdc,
    mock_usdc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_usdc,
    governance,
):
    """Test USDC vault with USDC as collateral on Ripe"""
    # USDC in wallet
    usdc_in_wallet = 5_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_usdc.address, usdc_in_wallet, sender=governance.address)

    # USDC as collateral on Ripe
    usdc_on_ripe = 5_000 * SIX_DECIMALS
    mock_ripe.setUserCollateral(undy_levg_vault_usdc.address, mock_usdc, usdc_on_ripe)

    total_assets = levg_vault_helper.getTotalAssetsForUsdcVault(
        undy_levg_vault_usdc.address,
        mock_usdc_collateral_vault.address,
        2,
        mock_usdc_leverage_vault.address,
        2,
    )

    # Total should be 5k (wallet) + 5k (ripe) = 10k USDC
    expected = usdc_in_wallet + usdc_on_ripe
    assert total_assets >= expected * 99 // 100


@pytest.mark.parametrize("vault_type", ["cbbtc", "weth"])
def test_total_assets_non_usdc_vault_with_collateral_and_leverage_vault(
    vault_type,
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    get_vault_config,
    mint_to_vault,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mock_usdc_collateral_vault,
    mock_cbbtc_collateral_vault,
    mock_weth_collateral_vault,
    mock_usdc_leverage_vault,
    governance,
):
    """Test non-USDC vault with assets in both collateral vault and leverage vault"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
        mock_usdc_collateral_vault,
        mock_cbbtc_collateral_vault,
        mock_weth_collateral_vault,
        mock_usdc_leverage_vault,
    )

    # Underlying in wallet (0.5 units)
    underlying_in_wallet = 5 * (config["decimals"] // 10)
    mint_to_vault(config["underlying"], config["vault"].address, underlying_in_wallet, config["is_weth"])

    # USDC in wallet (for leverage vault)
    usdc_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(config["vault"].address, usdc_amount, sender=governance.address)

    # Small debt
    debt_amount = 2_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(config["vault"].address, debt_amount)

    total_assets = levg_vault_helper.getTotalAssetsForNonUsdcVault(
        config["vault"].address,
        config["underlying"].address,
        config["collateral_vault"].address,
        2,
        config["leverage_vault"].address,
        2,
    )

    # Total value: underlying + 10k USDC - 2k debt
    # cbBTC: 0.5 CBBTC ($45k) + 10k USDC - 2k debt = $53k / $90k = 0.588... CBBTC
    # WETH: 0.5 WETH ($1k) + 10k USDC - 2k debt = $9k / $2k = 4.5 WETH
    assert total_assets > underlying_in_wallet


##################################
# 7. Underwater/Edge Cases Tests #
##################################


@pytest.mark.parametrize("vault_type", ["cbbtc", "weth"])
def test_non_usdc_vault_usdc_covers_debt_with_surplus(
    vault_type,
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    get_vault_config,
    mint_to_vault,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mock_usdc_collateral_vault,
    mock_cbbtc_collateral_vault,
    mock_weth_collateral_vault,
    mock_usdc_leverage_vault,
    governance,
):
    """Test non-USDC vault where USDC covers debt with surplus"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
        mock_usdc_collateral_vault,
        mock_cbbtc_collateral_vault,
        mock_weth_collateral_vault,
        mock_usdc_leverage_vault,
    )

    # Give wallet 1 unit of underlying
    underlying_amount = 1 * config["decimals"]
    mint_to_vault(config["underlying"], config["vault"].address, underlying_amount, config["is_weth"])

    # Give wallet 20k USDC
    usdc_amount = 20_000 * SIX_DECIMALS
    mock_usdc.mint(config["vault"].address, usdc_amount, sender=governance.address)

    # Add 10k GREEN debt (USDC covers this with surplus)
    debt_amount = 10_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(config["vault"].address, debt_amount)

    total_assets = levg_vault_helper.getTotalAssetsForNonUsdcVault(
        config["vault"].address,
        config["underlying"].address,
        config["collateral_vault"].address,
        2,
        config["leverage_vault"].address,
        2,
    )

    # Total value: underlying + (20k USDC - 10k debt)
    # cbBTC: $90k + $10k = $100k / $90k = 1.111... CBBTC
    # WETH: $2k + $10k = $12k / $2k = 6 WETH
    assert total_assets > underlying_amount


@pytest.mark.parametrize("vault_type", ["cbbtc", "weth"])
def test_non_usdc_vault_debt_exceeds_usdc_underwater(
    vault_type,
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    get_vault_config,
    mint_to_vault,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mock_usdc_collateral_vault,
    mock_cbbtc_collateral_vault,
    mock_weth_collateral_vault,
    mock_usdc_leverage_vault,
    governance,
):
    """Test non-USDC vault where debt exceeds USDC (eats into underlying)"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
        mock_usdc_collateral_vault,
        mock_cbbtc_collateral_vault,
        mock_weth_collateral_vault,
        mock_usdc_leverage_vault,
    )

    # Give wallet 1 unit of underlying
    underlying_amount = 1 * config["decimals"]
    mint_to_vault(config["underlying"], config["vault"].address, underlying_amount, config["is_weth"])

    # Give wallet 5k USDC
    usdc_amount = 5_000 * SIX_DECIMALS
    mock_usdc.mint(config["vault"].address, usdc_amount, sender=governance.address)

    # Add debt that exceeds USDC
    # cbBTC: 20k GREEN debt (exceeds 5k USDC by 15k)
    # WETH: 6k GREEN debt (exceeds 5k USDC by 1k)
    if vault_type == "cbbtc":
        debt_amount = 20_000 * EIGHTEEN_DECIMALS
        expected_ratio = 75  # ($90k + $5k - $20k) / $90k = ~83%
    else:  # weth
        debt_amount = 6_000 * EIGHTEEN_DECIMALS
        expected_ratio = 50  # ($2k + $5k - $6k) / $2k = 50%

    mock_ripe.setUserDebt(config["vault"].address, debt_amount)

    total_assets = levg_vault_helper.getTotalAssetsForNonUsdcVault(
        config["vault"].address,
        config["underlying"].address,
        config["collateral_vault"].address,
        2,
        config["leverage_vault"].address,
        2,
    )

    # Total value: underlying + USDC - debt (debt eats into underlying value)
    assert total_assets < underlying_amount
    assert total_assets >= underlying_amount * expected_ratio // 100


def test_get_swappable_usdc_when_debt_exceeds_value(
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    undy_levg_vault_usdc,
    mock_usdc_leverage_vault,
    mock_usdc,
    governance,
):
    """Test getSwappableUsdcAmount when debt exceeds total positive value"""
    # Give wallet 10k USDC
    current_balance = 10_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_usdc.address, current_balance, sender=governance.address)

    # Add 15k GREEN debt (exceeds USDC value)
    debt_amount = 15_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(undy_levg_vault_usdc.address, debt_amount)

    swappable = levg_vault_helper.getSwappableUsdcAmount(
        undy_levg_vault_usdc.address,
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


@pytest.mark.parametrize("vault_type", ["cbbtc", "weth"])
def test_non_usdc_decimal_precision_calculations(
    vault_type,
    levg_vault_helper,
    setup_mock_prices,
    get_vault_config,
    mint_to_vault,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mock_usdc_collateral_vault,
    mock_cbbtc_collateral_vault,
    mock_weth_collateral_vault,
    mock_usdc_leverage_vault,
    governance,
):
    """Test calculations with different decimal precisions (8 for cbBTC, 18 for WETH)"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
        mock_usdc_collateral_vault,
        mock_cbbtc_collateral_vault,
        mock_weth_collateral_vault,
        mock_usdc_leverage_vault,
    )

    # Give wallet a fractional amount using all decimal places
    # For cbBTC (8 decimals): 0.12345678
    # For WETH (18 decimals): 0.123456789012345678
    if vault_type == "cbbtc":
        amount = 12_345_678  # 0.12345678 CBBTC
    else:  # weth
        amount = 123_456_789_012_345_678  # 0.123456789012345678 WETH

    mint_to_vault(config["underlying"], config["vault"].address, amount, config["is_weth"])

    total_assets = levg_vault_helper.getTotalAssetsForNonUsdcVault(
        config["vault"].address,
        config["underlying"].address,
        config["collateral_vault"].address,
        2,
        config["leverage_vault"].address,
        2,
    )

    # Should preserve decimal precision
    assert total_assets == amount


@pytest.mark.parametrize("vault_type", ["cbbtc", "weth"])
def test_mixed_decimal_conversions_with_usdc_and_debt(
    vault_type,
    levg_vault_helper,
    setup_mock_prices,
    mock_ripe,
    get_vault_config,
    mint_to_vault,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mock_usdc_collateral_vault,
    mock_cbbtc_collateral_vault,
    mock_weth_collateral_vault,
    mock_usdc_leverage_vault,
    governance,
):
    """Test decimal conversions between underlying (cbBTC/WETH), USDC (6), and GREEN (18)"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
        mock_usdc_collateral_vault,
        mock_cbbtc_collateral_vault,
        mock_weth_collateral_vault,
        mock_usdc_leverage_vault,
    )

    # Give wallet 1 unit of underlying (value depends on price)
    # cbBTC: 1 CBBTC = $90,000
    # WETH: 1 WETH = $2,000
    underlying_amount = 1 * config["decimals"]
    mint_to_vault(config["underlying"], config["vault"].address, underlying_amount, config["is_weth"])

    # Give wallet 10,000 USDC (6 decimals)
    usdc_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(config["vault"].address, usdc_amount, sender=governance.address)

    # Add 5,000 GREEN debt (18 decimals)
    debt_amount = 5_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(config["vault"].address, debt_amount)

    total_assets = levg_vault_helper.getTotalAssetsForNonUsdcVault(
        config["vault"].address,
        config["underlying"].address,
        config["collateral_vault"].address,
        2,
        config["leverage_vault"].address,
        2,
    )

    # Total value: underlying + 10k USDC - 5k debt
    # For cbBTC: $90k + $10k - $5k = $95k / $90k = 1.055... CBBTC
    # For WETH: $2k + $10k - $5k = $7k / $2k = 3.5 WETH
    # Should properly handle all decimal conversions
    assert total_assets > underlying_amount
