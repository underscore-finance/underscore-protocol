"""
Shared fixtures for leverage vault tests
"""

import pytest
import boa

from constants import MAX_UINT256, EIGHTEEN_DECIMALS

# Decimal constants
SIX_DECIMALS = 10 ** 6
EIGHT_DECIMALS = 10 ** 8


@pytest.fixture(scope="session")
def setup_mock_swap_lego_in_legobook(lego_book, mock_swap_lego, governance):
    """Register mock_swap_lego in the lego book"""
    # Check if already registered (session-scoped lego_book may already have it)
    if lego_book.isLegoAddr(mock_swap_lego.address):
        return mock_swap_lego

    lego_book.startAddNewAddressToRegistry(mock_swap_lego.address, "Mock Swap Lego", sender=governance.address)
    boa.env.time_travel(blocks=lego_book.registryChangeTimeLock() + 1)
    lego_id = lego_book.confirmNewAddressToRegistry(mock_swap_lego.address, sender=governance.address)
    assert lego_id != 0, "Failed to register mock_swap_lego"
    return mock_swap_lego


@pytest.fixture(scope="module")
def setup_prices(mock_ripe, mock_green_token, mock_savings_green_token, mock_usdc, mock_cbbtc, mock_weth, mock_swap_lego, governance, setup_mock_swap_lego_in_legobook,
                 undy_levg_vault_usdc, undy_levg_vault_cbbtc, undy_levg_vault_weth):
    """Set up prices for all assets"""
    # Ripe prices (for debt calculations)
    mock_ripe.setPrice(mock_green_token, 1 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_savings_green_token, 1 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_usdc, 1 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_cbbtc, 90_000 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_weth, 2_000 * EIGHTEEN_DECIMALS)

    # Swap lego prices (for GREEN <-> USDC swaps)
    mock_swap_lego.setPrice(mock_green_token.address, 1 * EIGHTEEN_DECIMALS, sender=governance.address)
    mock_swap_lego.setPrice(mock_usdc.address, 1 * EIGHTEEN_DECIMALS, sender=governance.address)

    # Set max borrow amounts for all vaults so Ripe credit engine doesn't limit borrowing
    mock_ripe.setMaxBorrowAmount(undy_levg_vault_usdc.address, MAX_UINT256)
    mock_ripe.setMaxBorrowAmount(undy_levg_vault_cbbtc.address, MAX_UINT256)
    mock_ripe.setMaxBorrowAmount(undy_levg_vault_weth.address, MAX_UINT256)

    return mock_ripe


@pytest.fixture(scope="module")
def usdc_wallet_with_funds(undy_levg_vault_usdc, mock_usdc, governance, switchboard_alpha):
    """Give USDC vault wallet some USDC"""
    amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_usdc.address, amount, sender=governance.address)

    # Set maxDebtRatio to 0 for unlimited borrowing in wallet action tests
    undy_levg_vault_usdc.setMaxDebtRatio(0, sender=switchboard_alpha.address)

    return undy_levg_vault_usdc


@pytest.fixture(scope="module")
def cbbtc_wallet_with_funds(undy_levg_vault_cbbtc, mock_cbbtc, governance):
    """Give CBBTC vault wallet some CBBTC"""
    amount = 1 * EIGHT_DECIMALS  # 1 CBBTC
    mock_cbbtc.mint(undy_levg_vault_cbbtc.address, amount, sender=governance.address)
    return undy_levg_vault_cbbtc


@pytest.fixture(scope="module")
def weth_wallet_with_funds(undy_levg_vault_weth, mock_weth, governance):
    """Give WETH vault wallet some WETH"""
    amount = 5 * EIGHTEEN_DECIMALS  # 5 WETH

    # For WETH, we need to deposit ETH to get WETH
    boa.env.set_balance(governance.address, amount)
    mock_weth.deposit(value=amount, sender=governance.address)
    mock_weth.transfer(undy_levg_vault_weth.address, amount, sender=governance.address)

    return undy_levg_vault_weth
