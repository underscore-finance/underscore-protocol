import pytest
import boa

from constants import MAX_UINT256, EIGHTEEN_DECIMALS, ZERO_ADDRESS
from conf_utils import filter_logs

# Decimal constants
SIX_DECIMALS = 10 ** 6
EIGHT_DECIMALS = 10 ** 8

# Lego IDs
RIPE_LEGO_ID = 1


############
# Fixtures #
############


@pytest.fixture(scope="module")
def setup_mock_swap_lego_in_legobook(lego_book, mock_swap_lego, governance):
    """Register mock_swap_lego in the lego book"""
    lego_book.startAddNewAddressToRegistry(mock_swap_lego.address, "Mock Swap Lego", sender=governance.address)
    boa.env.time_travel(blocks=lego_book.registryChangeTimeLock() + 1)
    lego_id = lego_book.confirmNewAddressToRegistry(mock_swap_lego.address, sender=governance.address)
    assert lego_id != 0, "Failed to register mock_swap_lego"
    return mock_swap_lego


@pytest.fixture(scope="module")
def setup_prices(mock_ripe, mock_green_token, mock_savings_green_token, mock_usdc, mock_cbbtc, mock_weth, mock_swap_lego, governance, setup_mock_swap_lego_in_legobook):
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

    return mock_ripe


@pytest.fixture(scope="module")
def usdc_wallet_with_funds(undy_levg_vault_usdc, mock_usdc, governance):
    """Give USDC vault wallet some USDC"""
    amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(undy_levg_vault_usdc.address, amount, sender=governance.address)
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


###########################
# 1. Yield Operations Tests #
###########################


def test_deposit_to_collateral_vault_usdc(
    setup_prices,
    usdc_wallet_with_funds,
    mock_usdc_collateral_vault,
    mock_usdc,
    starter_agent,
):
    """Test depositing USDC to collateral vault"""
    wallet = usdc_wallet_with_funds
    lego_id = 2  # Mock yield lego ID

    # Pre-check balances
    pre_usdc_balance = mock_usdc.balanceOf(wallet.address)
    pre_vault_balance = mock_usdc_collateral_vault.balanceOf(wallet.address)

    # Deposit to collateral vault
    deposit_amount = 1_000 * SIX_DECIMALS
    asset_deposited, vault_token, vault_tokens_received, usd_value = wallet.depositForYield(
        lego_id,
        mock_usdc.address,
        mock_usdc_collateral_vault.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Verify event immediately after transaction
    log = filter_logs(wallet, "LevgVaultAction")[0]
    assert log.op == 10  # depositForYield
    assert log.asset1 == mock_usdc.address
    assert log.asset2 == mock_usdc_collateral_vault.address
    assert log.amount1 == deposit_amount
    assert log.amount2 == vault_tokens_received
    assert log.signer == starter_agent.address

    # Verify deposit
    assert asset_deposited == deposit_amount
    assert vault_token == mock_usdc_collateral_vault.address
    assert vault_tokens_received > 0
    assert usd_value == 1_000 * EIGHTEEN_DECIMALS  # $1000 USD value

    # Verify balances
    assert mock_usdc.balanceOf(wallet.address) == pre_usdc_balance - deposit_amount
    assert mock_usdc_collateral_vault.balanceOf(wallet.address) == pre_vault_balance + vault_tokens_received


def test_deposit_to_leverage_vault_usdc(
    setup_prices,
    usdc_wallet_with_funds,
    mock_usdc_leverage_vault,
    mock_usdc,
    starter_agent,
):
    """Test depositing USDC to leverage vault"""
    wallet = usdc_wallet_with_funds
    lego_id = 2

    # Pre-check balances
    pre_usdc_balance = mock_usdc.balanceOf(wallet.address)

    # Deposit to leverage vault
    deposit_amount = 2_000 * SIX_DECIMALS
    asset_deposited, vault_token, vault_tokens_received, usd_value = wallet.depositForYield(
        lego_id,
        mock_usdc.address,
        mock_usdc_leverage_vault.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Verify deposit
    assert asset_deposited == deposit_amount
    assert vault_token == mock_usdc_leverage_vault.address
    assert vault_tokens_received > 0
    assert usd_value > 0

    # Verify balances
    assert mock_usdc.balanceOf(wallet.address) == pre_usdc_balance - deposit_amount
    assert mock_usdc_leverage_vault.balanceOf(wallet.address) == vault_tokens_received


def test_deposit_green_to_savings_green(
    setup_prices,
    usdc_wallet_with_funds,
    mock_green_token,
    mock_savings_green_token,
    governance,
    starter_agent,
):
    """Test depositing GREEN to SAVINGS_GREEN vault"""
    wallet = usdc_wallet_with_funds
    lego_id = RIPE_LEGO_ID

    # Give wallet some GREEN
    green_amount = 1_000 * EIGHTEEN_DECIMALS
    mock_green_token.mint(wallet.address, green_amount, sender=governance.address)

    # Deposit GREEN to SAVINGS_GREEN
    asset_deposited, vault_token, vault_tokens_received, usd_value = wallet.depositForYield(
        lego_id,
        mock_green_token.address,
        mock_savings_green_token.address,
        green_amount,
        sender=starter_agent.address
    )

    # Verify
    assert asset_deposited == green_amount
    assert vault_token == mock_savings_green_token.address
    assert vault_tokens_received > 0
    assert mock_savings_green_token.balanceOf(wallet.address) == vault_tokens_received


def test_withdraw_from_collateral_vault(
    setup_prices,
    usdc_wallet_with_funds,
    mock_usdc_collateral_vault,
    mock_usdc,
    starter_agent,
):
    """Test withdrawing from collateral vault"""
    wallet = usdc_wallet_with_funds
    lego_id = 2

    # First deposit
    deposit_amount = 1_000 * SIX_DECIMALS
    _, _, vault_tokens, _ = wallet.depositForYield(
        lego_id,
        mock_usdc.address,
        mock_usdc_collateral_vault.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Pre-check balances
    pre_usdc_balance = mock_usdc.balanceOf(wallet.address)

    # Withdraw half
    withdraw_amount = vault_tokens // 2
    vault_burned, underlying_asset, underlying_received, usd_value = wallet.withdrawFromYield(
        lego_id,
        mock_usdc_collateral_vault.address,
        withdraw_amount,
        sender=starter_agent.address
    )

    # Verify event immediately after transaction
    log = filter_logs(wallet, "LevgVaultAction")[0]
    assert log.op == 11  # withdrawFromYield
    assert log.asset1 == mock_usdc_collateral_vault.address
    assert log.asset2 == mock_usdc.address

    # Verify withdrawal
    assert vault_burned == withdraw_amount
    assert underlying_asset == mock_usdc.address
    assert underlying_received > 0
    assert usd_value > 0

    # Verify balances
    assert mock_usdc.balanceOf(wallet.address) == pre_usdc_balance + underlying_received
    assert mock_usdc_collateral_vault.balanceOf(wallet.address) == vault_tokens - withdraw_amount


def test_withdraw_max_amount(
    setup_prices,
    usdc_wallet_with_funds,
    mock_usdc_collateral_vault,
    mock_usdc,
    starter_agent,
):
    """Test withdrawing MAX_UINT256 withdraws entire balance"""
    wallet = usdc_wallet_with_funds
    lego_id = 2

    # First deposit
    _, _, vault_tokens, _ = wallet.depositForYield(
        lego_id,
        mock_usdc.address,
        mock_usdc_collateral_vault.address,
        500 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    # Withdraw max
    vault_burned, _, underlying_received, _ = wallet.withdrawFromYield(
        lego_id,
        mock_usdc_collateral_vault.address,
        MAX_UINT256,
        sender=starter_agent.address
    )

    # Verify entire balance withdrawn
    assert vault_burned == vault_tokens
    assert mock_usdc_collateral_vault.balanceOf(wallet.address) == 0


###########################
# 2. Swap Operations Tests #
###########################


def test_swap_green_to_usdc_basic(
    setup_prices,
    usdc_wallet_with_funds,
    mock_green_token,
    mock_usdc,
    governance,
    starter_agent,
    lego_book,
    mock_swap_lego,
):
    """Test basic GREEN -> USDC swap"""
    wallet = usdc_wallet_with_funds

    # Give wallet GREEN
    green_amount = 1_000 * EIGHTEEN_DECIMALS
    mock_green_token.mint(wallet.address, green_amount, sender=governance.address)

    # Pre-check balances
    pre_green = mock_green_token.balanceOf(wallet.address)
    pre_usdc = mock_usdc.balanceOf(wallet.address)

    # Setup swap instruction (legoId, amountIn, minAmountOut, tokenPath, poolPath)
    swap_lego_id = lego_book.getRegId(mock_swap_lego.address)
    swap_instruction = (
        swap_lego_id,
        500 * EIGHTEEN_DECIMALS,
        490 * SIX_DECIMALS,  # 2% slippage tolerance
        [mock_green_token.address, mock_usdc.address],
        []
    )

    # Execute swap
    token_in, amount_in, token_out, amount_out, usd_value = wallet.swapTokens(
        [swap_instruction],
        sender=starter_agent.address
    )

    # Verify event immediately after transaction
    log = filter_logs(wallet, "LevgVaultAction")[0]
    assert log.op == 20  # swap
    assert log.asset1 == mock_green_token.address
    assert log.asset2 == mock_usdc.address

    # Verify swap
    assert token_in == mock_green_token.address
    assert token_out == mock_usdc.address
    assert amount_in == 500 * EIGHTEEN_DECIMALS
    assert amount_out == 500 * SIX_DECIMALS  # 1:1 price
    assert usd_value == 500 * EIGHTEEN_DECIMALS

    # Verify balances
    assert mock_green_token.balanceOf(wallet.address) == pre_green - 500 * EIGHTEEN_DECIMALS
    assert mock_usdc.balanceOf(wallet.address) == pre_usdc + 500 * SIX_DECIMALS


def test_swap_with_slippage_validation(
    setup_prices,
    usdc_wallet_with_funds,
    mock_green_token,
    mock_usdc,
    governance,
    starter_agent,
    lego_book,
    mock_swap_lego,
):
    """Test that swap validates slippage via performPostSwapValidation"""
    wallet = usdc_wallet_with_funds

    # Give wallet GREEN
    mock_green_token.mint(wallet.address, 1_000 * EIGHTEEN_DECIMALS, sender=governance.address)

    # This swap should succeed (within 1% slippage tolerance set in wallet)
    swap_lego_id = lego_book.getRegId(mock_swap_lego.address)
    swap_instruction = (
        swap_lego_id,
        100 * EIGHTEEN_DECIMALS,
        99 * SIX_DECIMALS,  # 1% slippage
        [mock_green_token.address, mock_usdc.address],
        []
    )

    # Should succeed - performPostSwapValidation passes with 1% slippage
    _, _, _, amount_out, _ = wallet.swapTokens([swap_instruction], sender=starter_agent.address)
    assert amount_out == 100 * SIX_DECIMALS


def test_swap_invalid_asset_collateral_vault_token(
    setup_prices,
    usdc_wallet_with_funds,
    mock_usdc_collateral_vault,
    mock_usdc,
    starter_agent,
    lego_book,
    mock_swap_lego,
):
    """Test that swapping collateral vault token is rejected"""
    wallet = usdc_wallet_with_funds

    # Try to swap collateral vault token (should be blocked)
    # Validation: tokenIn not in [collateralVaultToken, ...]
    swap_lego_id = lego_book.getRegId(mock_swap_lego.address)
    swap_instruction = (swap_lego_id, 100 * EIGHTEEN_DECIMALS, 0, [mock_usdc_collateral_vault.address, mock_usdc.address], [])

    # Should revert - cannot swap collateral vault tokens
    with boa.reverts("invalid swap asset"):
        wallet.swapTokens([swap_instruction], sender=starter_agent.address)


def test_swap_invalid_asset_leverage_vault_token(
    setup_prices,
    usdc_wallet_with_funds,
    mock_usdc_leverage_vault,
    mock_usdc,
    starter_agent,
    lego_book,
    mock_swap_lego,
):
    """Test that swapping leverage vault token is rejected"""
    wallet = usdc_wallet_with_funds

    # Try to swap leverage vault token (should be blocked)
    # Validation: tokenIn not in [leverageVaultToken, ...]
    swap_lego_id = lego_book.getRegId(mock_swap_lego.address)
    swap_instruction = (swap_lego_id, 100 * EIGHTEEN_DECIMALS, 0, [mock_usdc_leverage_vault.address, mock_usdc.address], [])

    with boa.reverts("invalid swap asset"):
        wallet.swapTokens([swap_instruction], sender=starter_agent.address)


def test_swap_invalid_asset_vault_asset(
    setup_prices,
    usdc_wallet_with_funds,
    mock_usdc,
    mock_green_token,
    starter_agent,
    lego_book,
    mock_swap_lego,
):
    """Test that swapping vault's underlying asset is rejected"""
    wallet = usdc_wallet_with_funds

    # Try to swap vault asset (USDC for USDC vault) to GREEN (should be blocked)
    # Validation: tokenIn not in [ad.vaultAsset, ...]
    swap_lego_id = lego_book.getRegId(mock_swap_lego.address)
    swap_instruction = (swap_lego_id, 100 * SIX_DECIMALS, 0, [mock_usdc.address, mock_green_token.address], [])

    with boa.reverts("invalid swap asset"):
        wallet.swapTokens([swap_instruction], sender=starter_agent.address)


def test_swap_invalid_asset_savings_green(
    setup_prices,
    usdc_wallet_with_funds,
    mock_savings_green_token,
    mock_green_token,
    mock_usdc,
    governance,
    starter_agent,
    lego_book,
    mock_swap_lego,
):
    """Test that swapping SAVINGS_GREEN is rejected"""
    wallet = usdc_wallet_with_funds

    # Give wallet some SAVINGS_GREEN by depositing GREEN into the vault
    green_amount = 100 * EIGHTEEN_DECIMALS
    mock_green_token.mint(wallet.address, green_amount, sender=governance.address)
    mock_green_token.approve(mock_savings_green_token.address, green_amount, sender=wallet.address)
    mock_savings_green_token.deposit(green_amount, wallet.address, sender=wallet.address)

    # Try to swap SAVINGS_GREEN (should be blocked)
    # Validation: tokenIn not in [savingsGreen, ...]
    swap_lego_id = lego_book.getRegId(mock_swap_lego.address)
    swap_instruction = (swap_lego_id, 100 * EIGHTEEN_DECIMALS, 0, [mock_savings_green_token.address, mock_usdc.address], [])

    with boa.reverts("invalid swap asset"):
        wallet.swapTokens([swap_instruction], sender=starter_agent.address)


def test_swap_green_can_only_go_to_usdc(
    setup_prices,
    usdc_wallet_with_funds,
    mock_green_token,
    bravo_token,
    governance,
    starter_agent,
    lego_book,
    mock_swap_lego,
):
    """Test that GREEN can only be swapped to USDC (not other tokens)"""
    wallet = usdc_wallet_with_funds

    # Give wallet some GREEN
    mock_green_token.mint(wallet.address, 1_000 * EIGHTEEN_DECIMALS, sender=governance.address)

    # Try to swap GREEN to non-USDC token (should fail)
    # Validation: if tokenIn == green: assert tokenOut == usdc
    swap_lego_id = lego_book.getRegId(mock_swap_lego.address)
    swap_instruction = (swap_lego_id, 100 * EIGHTEEN_DECIMALS, 0, [mock_green_token.address, bravo_token.address], [])

    with boa.reverts("GREEN can only go to USDC"):
        wallet.swapTokens([swap_instruction], sender=starter_agent.address)


def test_swap_usdc_to_non_green_must_be_vault_asset(
    setup_prices,
    cbbtc_wallet_with_funds,
    mock_usdc,
    bravo_token,
    governance,
    starter_agent,
    lego_book,
    mock_swap_lego,
):
    """Test that USDC swapped to non-GREEN must go to vault asset"""
    wallet = cbbtc_wallet_with_funds

    # Give wallet some USDC
    mock_usdc.mint(wallet.address, 1_000 * SIX_DECIMALS, sender=governance.address)

    # Try to swap USDC to non-vault-asset token (should fail)
    # For CBBTC vault, vaultAsset is CBBTC, not BRAVO
    # Validation: if tokenIn == usdc and tokenOut != green: assert tokenOut == ad.vaultAsset
    swap_lego_id = lego_book.getRegId(mock_swap_lego.address)
    swap_instruction = (swap_lego_id, 100 * SIX_DECIMALS, 0, [mock_usdc.address, bravo_token.address], [])

    with boa.reverts("must swap into vault asset"):
        wallet.swapTokens([swap_instruction], sender=starter_agent.address)


def test_swap_post_swap_validation_called(
    setup_prices,
    usdc_wallet_with_funds,
    mock_green_token,
    mock_usdc,
    governance,
    starter_agent,
    lego_book,
    mock_swap_lego,
):
    """Test that performPostSwapValidation is called for GREEN <-> USDC swaps"""
    wallet = usdc_wallet_with_funds

    # Give wallet GREEN
    mock_green_token.mint(wallet.address, 1_000 * EIGHTEEN_DECIMALS, sender=governance.address)

    # Swap GREEN -> USDC
    # This should trigger performPostSwapValidation check
    swap_lego_id = lego_book.getRegId(mock_swap_lego.address)
    swap_instruction = (
        swap_lego_id,
        100 * EIGHTEEN_DECIMALS,
        99 * SIX_DECIMALS,  # Within slippage tolerance
        [mock_green_token.address, mock_usdc.address],
        []
    )

    # Should succeed - performPostSwapValidation passes
    token_in, amount_in, token_out, amount_out, _ = wallet.swapTokens(
        [swap_instruction],
        sender=starter_agent.address
    )

    # Verify swap executed
    assert token_in == mock_green_token.address
    assert token_out == mock_usdc.address
    assert amount_out == 100 * SIX_DECIMALS  # 1:1 price with mock


#################################
# 3. Debt Management Tests #
#################################


def test_add_collateral_underlying_asset(
    setup_prices,
    usdc_wallet_with_funds,
    mock_usdc,
    mock_ripe,
    starter_agent,
):
    """Test adding underlying USDC as collateral to Ripe"""
    wallet = usdc_wallet_with_funds

    # Pre-check
    pre_usdc = mock_usdc.balanceOf(wallet.address)

    # Add collateral
    collateral_amount = 1_000 * SIX_DECIMALS
    amount_deposited, usd_value = wallet.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc.address,
        collateral_amount,
        sender=starter_agent.address
    )

    # Verify event immediately after transaction
    log = filter_logs(wallet, "LevgVaultAction")[0]
    assert log.op == 40  # addCollateral
    assert log.asset1 == mock_usdc.address
    assert log.amount1 == collateral_amount

    # Verify
    assert amount_deposited == collateral_amount
    assert usd_value == 1_000 * EIGHTEEN_DECIMALS
    assert mock_usdc.balanceOf(wallet.address) == pre_usdc - collateral_amount
    assert mock_ripe.userCollateral(wallet.address, mock_usdc) == collateral_amount


def test_add_collateral_leverage_vault_token(
    setup_prices,
    usdc_wallet_with_funds,
    mock_usdc_leverage_vault,
    mock_usdc,
    mock_ripe,
    starter_agent,
):
    """Test adding leverage vault tokens as collateral"""
    wallet = usdc_wallet_with_funds

    # First deposit to get vault tokens
    _, _, vault_tokens, _ = wallet.depositForYield(
        2,
        mock_usdc.address,
        mock_usdc_leverage_vault.address,
        1_000 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    # Add vault tokens as collateral
    amount_deposited, usd_value = wallet.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc_leverage_vault.address,
        vault_tokens,
        sender=starter_agent.address
    )

    # Verify
    assert amount_deposited == vault_tokens
    assert usd_value > 0
    assert mock_usdc_leverage_vault.balanceOf(wallet.address) == 0
    assert mock_ripe.userCollateral(wallet.address, mock_usdc_leverage_vault) == vault_tokens


def test_add_collateral_savings_green(
    setup_prices,
    usdc_wallet_with_funds,
    mock_green_token,
    mock_savings_green_token,
    mock_ripe,
    governance,
    starter_agent,
):
    """Test adding SAVINGS_GREEN as collateral"""
    wallet = usdc_wallet_with_funds

    # Give wallet GREEN and deposit to savings
    mock_green_token.mint(wallet.address, 1_000 * EIGHTEEN_DECIMALS, sender=governance.address)
    _, _, sgreen_tokens, _ = wallet.depositForYield(
        RIPE_LEGO_ID,
        mock_green_token.address,
        mock_savings_green_token.address,
        1_000 * EIGHTEEN_DECIMALS,
        sender=starter_agent.address
    )

    # Add SAVINGS_GREEN as collateral
    amount_deposited, usd_value = wallet.addCollateral(
        RIPE_LEGO_ID,
        mock_savings_green_token.address,
        sgreen_tokens,
        sender=starter_agent.address
    )

    # Verify
    assert amount_deposited == sgreen_tokens
    assert usd_value > 0
    assert mock_ripe.userCollateral(wallet.address, mock_savings_green_token) == sgreen_tokens


def test_remove_collateral_basic(
    setup_prices,
    usdc_wallet_with_funds,
    mock_usdc,
    mock_ripe,
    starter_agent,
):
    """Test removing collateral from Ripe"""
    wallet = usdc_wallet_with_funds

    # First add collateral
    collateral_amount = 2_000 * SIX_DECIMALS
    wallet.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc.address,
        collateral_amount,
        sender=starter_agent.address
    )

    # Pre-check
    pre_usdc = mock_usdc.balanceOf(wallet.address)

    # Remove half
    remove_amount = collateral_amount // 2
    amount_removed, usd_value = wallet.removeCollateral(
        RIPE_LEGO_ID,
        mock_usdc.address,
        remove_amount,
        sender=starter_agent.address
    )

    # Verify event immediately after transaction
    log = filter_logs(wallet, "LevgVaultAction")[0]
    assert log.op == 41  # removeCollateral
    assert log.asset1 == mock_usdc.address

    # Verify
    assert amount_removed == remove_amount
    assert usd_value > 0
    assert mock_usdc.balanceOf(wallet.address) == pre_usdc + remove_amount
    assert mock_ripe.userCollateral(wallet.address, mock_usdc) == collateral_amount - remove_amount


def test_invalid_collateral_fails(
    setup_prices,
    usdc_wallet_with_funds,
    bravo_token,
    starter_agent,
):
    """Test that adding invalid collateral asset fails"""
    wallet = usdc_wallet_with_funds

    # Try to add invalid asset as collateral
    with boa.reverts("invalid collateral"):
        wallet.addCollateral(
            RIPE_LEGO_ID,
            bravo_token.address,
            100 * EIGHTEEN_DECIMALS,
            sender=starter_agent.address
        )


###################################
# 4. Borrow & Repay Debt Tests #
###################################


def test_borrow_green_basic(
    setup_prices,
    usdc_wallet_with_funds,
    mock_usdc,
    mock_green_token,
    mock_ripe,
    starter_agent,
):
    """Test borrowing GREEN from Ripe"""
    wallet = usdc_wallet_with_funds

    # First add collateral
    wallet.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc.address,
        5_000 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    # Pre-check
    pre_green = mock_green_token.balanceOf(wallet.address)

    # Borrow GREEN
    borrow_amount = 1_000 * EIGHTEEN_DECIMALS
    amount_borrowed, usd_value = wallet.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        borrow_amount,
        sender=starter_agent.address
    )

    # Verify event immediately after transaction
    log = filter_logs(wallet, "LevgVaultAction")[0]
    assert log.op == 42  # borrow
    assert log.asset1 == mock_green_token.address
    assert log.amount1 == borrow_amount

    # Verify
    assert amount_borrowed == borrow_amount
    assert usd_value == 1_000 * EIGHTEEN_DECIMALS
    assert mock_green_token.balanceOf(wallet.address) == pre_green + borrow_amount
    assert mock_ripe.userDebt(wallet.address) == borrow_amount


def test_borrow_savings_green(
    setup_prices,
    usdc_wallet_with_funds,
    mock_usdc,
    mock_savings_green_token,
    starter_agent,
):
    """Test borrowing SAVINGS_GREEN from Ripe"""
    wallet = usdc_wallet_with_funds

    # Add collateral
    wallet.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc.address,
        5_000 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    # Borrow SAVINGS_GREEN
    borrow_amount = 500 * EIGHTEEN_DECIMALS
    amount_borrowed, usd_value = wallet.borrow(
        RIPE_LEGO_ID,
        mock_savings_green_token.address,
        borrow_amount,
        sender=starter_agent.address
    )

    # Verify
    assert amount_borrowed > 0
    assert usd_value > 0
    assert mock_savings_green_token.balanceOf(wallet.address) > 0


def test_repay_debt_with_green(
    setup_prices,
    usdc_wallet_with_funds,
    mock_usdc,
    mock_green_token,
    mock_ripe,
    starter_agent,
):
    """Test repaying debt with GREEN"""
    wallet = usdc_wallet_with_funds

    # Add collateral and borrow
    wallet.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc.address,
        5_000 * SIX_DECIMALS,
        sender=starter_agent.address
    )
    borrow_amount = 1_000 * EIGHTEEN_DECIMALS
    wallet.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        borrow_amount,
        sender=starter_agent.address
    )

    # Pre-check
    pre_green = mock_green_token.balanceOf(wallet.address)
    pre_debt = mock_ripe.userDebt(wallet.address)

    # Repay half
    repay_amount = borrow_amount // 2
    amount_repaid, usd_value = wallet.repayDebt(
        RIPE_LEGO_ID,
        mock_green_token.address,
        repay_amount,
        sender=starter_agent.address
    )

    # Verify event immediately after transaction
    log = filter_logs(wallet, "LevgVaultAction")[0]
    assert log.op == 43  # repayDebt
    assert log.asset1 == mock_green_token.address

    # Verify
    assert amount_repaid == repay_amount
    assert usd_value > 0
    assert mock_green_token.balanceOf(wallet.address) == pre_green - repay_amount
    assert mock_ripe.userDebt(wallet.address) == pre_debt - repay_amount


def test_repay_debt_with_savings_green(
    setup_prices,
    usdc_wallet_with_funds,
    mock_usdc,
    mock_green_token,
    mock_savings_green_token,
    mock_ripe,
    governance,
    starter_agent,
):
    """Test repaying debt with SAVINGS_GREEN"""
    wallet = usdc_wallet_with_funds

    # Add collateral and borrow
    wallet.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc.address,
        5_000 * SIX_DECIMALS,
        sender=starter_agent.address
    )
    wallet.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        1_000 * EIGHTEEN_DECIMALS,
        sender=starter_agent.address
    )

    # Get some SAVINGS_GREEN for repayment
    mock_green_token.mint(wallet.address, 500 * EIGHTEEN_DECIMALS, sender=governance.address)
    _, _, sgreen_tokens, _ = wallet.depositForYield(
        RIPE_LEGO_ID,
        mock_green_token.address,
        mock_savings_green_token.address,
        500 * EIGHTEEN_DECIMALS,
        sender=starter_agent.address
    )

    # Repay with SAVINGS_GREEN
    pre_debt = mock_ripe.userDebt(wallet.address)
    amount_repaid, usd_value = wallet.repayDebt(
        RIPE_LEGO_ID,
        mock_savings_green_token.address,
        sgreen_tokens,
        sender=starter_agent.address
    )

    # Verify
    assert amount_repaid > 0
    assert mock_ripe.userDebt(wallet.address) < pre_debt


def test_repay_max_amount(
    setup_prices,
    usdc_wallet_with_funds,
    mock_usdc,
    mock_green_token,
    mock_ripe,
    starter_agent,
):
    """Test repaying with MAX_UINT256 repays all debt"""
    wallet = usdc_wallet_with_funds

    # Add collateral and borrow
    wallet.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc.address,
        3_000 * SIX_DECIMALS,
        sender=starter_agent.address
    )
    borrow_amount = 500 * EIGHTEEN_DECIMALS
    wallet.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        borrow_amount,
        sender=starter_agent.address
    )

    # Repay max
    amount_repaid, _ = wallet.repayDebt(
        RIPE_LEGO_ID,
        mock_green_token.address,
        MAX_UINT256,
        sender=starter_agent.address
    )

    # Verify all debt repaid
    assert amount_repaid == borrow_amount
    assert mock_ripe.userDebt(wallet.address) == 0


###################################
# 5. Rewards Claiming Tests #
###################################


def test_claim_rewards_success(
    setup_prices,
    usdc_wallet_with_funds,
    starter_agent,
    governance,
):
    """Test successfully claiming rewards from a lego"""
    wallet = usdc_wallet_with_funds
    lego_id = 2  # Mock yield lego ID

    # Create a mock reward token
    reward_token = boa.load(
        "contracts/mock/MockErc20.vy",
        governance,
        "Reward Token",
        "REWARD",
        18,
        1_000_000_000,
        name="reward_token"
    )

    reward_amount = 100 * EIGHTEEN_DECIMALS

    # Get initial balance
    initial_balance = reward_token.balanceOf(wallet.address)

    # Claim rewards - this calls the lego's claimIncentives function
    # MockYieldLego returns (0, 0), so we just verify the call succeeds
    amount_received, usd_value = wallet.claimIncentives(
        lego_id,
        reward_token.address,
        reward_amount,
        [],  # proofs
        sender=starter_agent.address
    )

    # MockYieldLego returns 0, but the call should succeed
    assert amount_received == 0  # MockYieldLego implementation
    assert usd_value == 0


def test_claim_rewards_unauthorized_fails(
    setup_prices,
    usdc_wallet_with_funds,
    alice,
    governance,
):
    """Test that only managers can claim rewards"""
    wallet = usdc_wallet_with_funds

    # Create a mock reward token
    reward_token = boa.load(
        "contracts/mock/MockErc20.vy",
        governance,
        "Reward Token",
        "REWARD",
        18,
        1_000_000_000,
        name="reward_token_2"
    )

    # Try to claim rewards from unauthorized user - should fail
    with boa.reverts():  # dev: no perms or unauthorized
        wallet.claimIncentives(
            2,  # Mock yield lego ID
            reward_token.address,
            100 * EIGHTEEN_DECIMALS,
            [],  # proofs
            sender=alice
        )


##############################
# 6. Integration Tests #
##############################


def test_full_leverage_loop_usdc_vault(
    setup_prices,
    usdc_wallet_with_funds,
    mock_usdc,
    mock_usdc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_green_token,
    starter_agent,
    lego_book,
    mock_swap_lego,
):
    """Test complete leverage loop: deposit collateral -> borrow GREEN -> swap to USDC -> deposit to leverage vault"""
    wallet = usdc_wallet_with_funds

    # Step 1: Deposit USDC to collateral vault
    _, _, collateral_vault_tokens, _ = wallet.depositForYield(
        2,
        mock_usdc.address,
        mock_usdc_collateral_vault.address,
        2_000 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    # Step 2: Add collateral vault tokens as collateral to Ripe
    wallet.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc_collateral_vault.address,
        collateral_vault_tokens,
        sender=starter_agent.address
    )

    # Step 3: Borrow GREEN
    borrow_amount = 1_000 * EIGHTEEN_DECIMALS
    wallet.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        borrow_amount,
        sender=starter_agent.address
    )

    # Step 4: Swap GREEN -> USDC
    swap_lego_id = lego_book.getRegId(mock_swap_lego.address)
    swap_instruction = (swap_lego_id, borrow_amount, 990 * SIX_DECIMALS, [mock_green_token.address, mock_usdc.address], [])
    _, _, _, usdc_received, _ = wallet.swapTokens([swap_instruction], sender=starter_agent.address)

    # Step 5: Deposit swapped USDC to leverage vault
    _, _, leverage_vault_tokens, _ = wallet.depositForYield(
        2,
        mock_usdc.address,
        mock_usdc_leverage_vault.address,
        usdc_received,
        sender=starter_agent.address
    )

    # Verify final state
    assert leverage_vault_tokens > 0
    assert mock_usdc_leverage_vault.balanceOf(wallet.address) == leverage_vault_tokens
    assert mock_green_token.balanceOf(wallet.address) == 0  # All GREEN swapped


def test_full_deleverage_loop(
    setup_prices,
    usdc_wallet_with_funds,
    mock_usdc,
    mock_usdc_leverage_vault,
    mock_green_token,
    mock_ripe,
    starter_agent,
    lego_book,
    mock_swap_lego,
):
    """Test deleveraging: withdraw from leverage vault -> swap USDC to GREEN -> repay debt"""
    wallet = usdc_wallet_with_funds

    # Setup: Create leveraged position
    wallet.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc.address,
        3_000 * SIX_DECIMALS,
        sender=starter_agent.address
    )
    wallet.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        1_000 * EIGHTEEN_DECIMALS,
        sender=starter_agent.address
    )

    # Swap borrowed GREEN to USDC and deposit to leverage vault
    swap_lego_id = lego_book.getRegId(mock_swap_lego.address)
    swap_instruction = (swap_lego_id, 1_000 * EIGHTEEN_DECIMALS, 0, [mock_green_token.address, mock_usdc.address], [])
    _, _, _, usdc_from_swap, _ = wallet.swapTokens([swap_instruction], sender=starter_agent.address)

    _, _, leverage_tokens, _ = wallet.depositForYield(
        2,
        mock_usdc.address,
        mock_usdc_leverage_vault.address,
        usdc_from_swap,
        sender=starter_agent.address
    )

    # Now deleverage:
    # For USDC vaults, deleveraging means: withdraw from leverage vault -> have USDC available
    # We can verify the USDC is back in the wallet
    _, _, usdc_withdrawn, _ = wallet.withdrawFromYield(
        2,
        mock_usdc_leverage_vault.address,
        leverage_tokens,
        sender=starter_agent.address
    )

    # Verify USDC was withdrawn
    assert usdc_withdrawn == 1_000 * SIX_DECIMALS
    assert mock_usdc.balanceOf(wallet.address) >= usdc_withdrawn

    # Verify initial debt exists (1000 GREEN borrowed)
    initial_debt = mock_ripe.userDebt(wallet.address)
    assert initial_debt == 1_000 * EIGHTEEN_DECIMALS

    # With the USDC withdrawn, the vault has reduced its leverage
    # The debt remains, but the leveraged position is unwound


def test_multi_step_position_management(
    setup_prices,
    usdc_wallet_with_funds,
    mock_usdc,
    mock_usdc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_green_token,
    mock_savings_green_token,
    mock_ripe,
    starter_agent,
    lego_book,
    mock_swap_lego,
):
    """Test complex multi-step scenario with multiple vault positions and debt"""
    wallet = usdc_wallet_with_funds

    # Phase 1: Build initial position
    # Deposit to collateral vault
    wallet.depositForYield(
        2,
        mock_usdc.address,
        mock_usdc_collateral_vault.address,
        2_000 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    # Add underlying USDC as collateral too
    wallet.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc.address,
        1_000 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    # Borrow GREEN
    wallet.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        800 * EIGHTEEN_DECIMALS,
        sender=starter_agent.address
    )

    # Phase 2: Diversify - convert some GREEN to SAVINGS_GREEN
    wallet.depositForYield(
        RIPE_LEGO_ID,
        mock_green_token.address,
        mock_savings_green_token.address,
        300 * EIGHTEEN_DECIMALS,
        sender=starter_agent.address
    )

    # Swap remaining GREEN to USDC
    swap_lego_id = lego_book.getRegId(mock_swap_lego.address)
    swap_instruction = (swap_lego_id, 500 * EIGHTEEN_DECIMALS, 0, [mock_green_token.address, mock_usdc.address], [])
    wallet.swapTokens([swap_instruction], sender=starter_agent.address)

    # Deposit swapped USDC to leverage vault
    wallet.depositForYield(
        2,
        mock_usdc.address,
        mock_usdc_leverage_vault.address,
        500 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    # Verify complex state
    assert mock_ripe.userDebt(wallet.address) == 800 * EIGHTEEN_DECIMALS
    assert mock_usdc_collateral_vault.balanceOf(wallet.address) > 0
    assert mock_usdc_leverage_vault.balanceOf(wallet.address) > 0
    assert mock_savings_green_token.balanceOf(wallet.address) > 0


####################################
# 7. Access Control & Security #
####################################


def test_unauthorized_caller_fails_deposit(
    setup_prices,
    usdc_wallet_with_funds,
    mock_usdc,
    bob,
):
    """Test that non-manager cannot call depositForYield"""
    wallet = usdc_wallet_with_funds

    # Try to deposit as unauthorized user
    with boa.reverts("not manager"):
        wallet.depositForYield(
            2,
            mock_usdc.address,
            ZERO_ADDRESS,
            100 * SIX_DECIMALS,
            sender=bob
        )


def test_unauthorized_caller_fails_withdraw(
    setup_prices,
    usdc_wallet_with_funds,
    mock_usdc_collateral_vault,
    bob,
):
    """Test that non-manager cannot call withdrawFromYield"""
    wallet = usdc_wallet_with_funds

    with boa.reverts("not manager"):
        wallet.withdrawFromYield(
            2,
            mock_usdc_collateral_vault.address,
            100 * SIX_DECIMALS,
            sender=bob
        )


def test_unauthorized_caller_fails_swap(
    setup_prices,
    usdc_wallet_with_funds,
    mock_green_token,
    mock_usdc,
    bob,
    lego_book,
    mock_swap_lego,
):
    """Test that non-manager cannot call swapTokens"""
    wallet = usdc_wallet_with_funds

    swap_lego_id = lego_book.getRegId(mock_swap_lego.address)
    swap_instruction = (swap_lego_id, 100 * EIGHTEEN_DECIMALS, 0, [mock_green_token.address, mock_usdc.address], [])

    with boa.reverts("not manager"):
        wallet.swapTokens([swap_instruction], sender=bob)


def test_unauthorized_caller_fails_add_collateral(
    setup_prices,
    usdc_wallet_with_funds,
    mock_usdc,
    bob,
):
    """Test that non-manager cannot call addCollateral"""
    wallet = usdc_wallet_with_funds

    with boa.reverts("not manager"):
        wallet.addCollateral(
            RIPE_LEGO_ID,
            mock_usdc.address,
            100 * SIX_DECIMALS,
            sender=bob
        )


def test_unauthorized_caller_fails_remove_collateral(
    setup_prices,
    usdc_wallet_with_funds,
    mock_usdc,
    bob,
):
    """Test that non-manager cannot call removeCollateral"""
    wallet = usdc_wallet_with_funds

    with boa.reverts("not manager"):
        wallet.removeCollateral(
            RIPE_LEGO_ID,
            mock_usdc.address,
            100 * SIX_DECIMALS,
            sender=bob
        )


def test_unauthorized_caller_fails_borrow(
    setup_prices,
    usdc_wallet_with_funds,
    mock_green_token,
    bob,
):
    """Test that non-manager cannot call borrow"""
    wallet = usdc_wallet_with_funds

    with boa.reverts("not manager"):
        wallet.borrow(
            RIPE_LEGO_ID,
            mock_green_token.address,
            100 * EIGHTEEN_DECIMALS,
            sender=bob
        )


def test_unauthorized_caller_fails_repay_debt(
    setup_prices,
    usdc_wallet_with_funds,
    mock_green_token,
    bob,
):
    """Test that non-manager cannot call repayDebt"""
    wallet = usdc_wallet_with_funds

    with boa.reverts("not manager"):
        wallet.repayDebt(
            RIPE_LEGO_ID,
            mock_green_token.address,
            100 * EIGHTEEN_DECIMALS,
            sender=bob
        )


def test_manager_can_perform_all_actions(
    setup_prices,
    usdc_wallet_with_funds,
    mock_usdc,
    mock_usdc_collateral_vault,
    mock_green_token,
    starter_agent,
):
    """Test that authorized manager (starter_agent) can perform all actions"""
    wallet = usdc_wallet_with_funds

    # Verify starter_agent is a manager
    assert wallet.indexOfManager(starter_agent.address) != 0

    # Test deposit works
    wallet.depositForYield(
        2,
        mock_usdc.address,
        mock_usdc_collateral_vault.address,
        100 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    # Test withdraw works
    wallet.withdrawFromYield(
        2,
        mock_usdc_collateral_vault.address,
        50 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    # Test add collateral works
    wallet.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc.address,
        100 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    # Test borrow works
    wallet.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        50 * EIGHTEEN_DECIMALS,
        sender=starter_agent.address
    )

    # All actions succeeded - manager permissions working correctly


def test_invalid_lego_id_fails(
    setup_prices,
    usdc_wallet_with_funds,
    mock_usdc,
    starter_agent,
):
    """Test that invalid lego ID fails"""
    wallet = usdc_wallet_with_funds

    # Try with non-existent lego ID
    with boa.reverts():
        wallet.depositForYield(
            999,  # Invalid lego ID
            mock_usdc.address,
            ZERO_ADDRESS,
            100 * SIX_DECIMALS,
            sender=starter_agent.address
        )


def test_invalid_lego_for_debt_management(
    setup_prices,
    usdc_wallet_with_funds,
    mock_usdc,
    starter_agent,
):
    """Test that non-Ripe lego cannot be used for debt management"""
    wallet = usdc_wallet_with_funds

    # Try to add collateral with wrong lego ID
    with boa.reverts("invalid lego id"):
        wallet.addCollateral(
            2,  # Not RIPE_LEGO_ID
            mock_usdc.address,
            100 * SIX_DECIMALS,
            sender=starter_agent.address
        )


###########################################
# 8. Vault Token Validation Tests #
###########################################


def test_vault_to_lego_id_set_on_init(
    undy_levg_vault_usdc,
    mock_usdc_leverage_vault,
    mock_usdc_collateral_vault,
):
    """Test that vaultToLegoId mapping is set during __init__"""
    wallet = undy_levg_vault_usdc

    # Verify vaultToLegoId was set for leverage vault token
    leverage_vault_lego_id = wallet.vaultToLegoId(mock_usdc_leverage_vault.address)
    assert leverage_vault_lego_id != 0  # Should be set to valid lego ID

    # Verify vaultToLegoId was set for collateral vault token (if exists)
    if mock_usdc_collateral_vault.address != ZERO_ADDRESS:
        collateral_vault_lego_id = wallet.vaultToLegoId(mock_usdc_collateral_vault.address)
        assert collateral_vault_lego_id != 0  # Should be set to valid lego ID


#################################################
# 9. Redemption from Leverage Vault Tests (Step 4) #
#################################################


def test_redeem_withdraws_from_leverage_vault_idle(
    undy_levg_vault_usdc,
    mock_usdc,
    mock_usdc_leverage_vault,
    mock_usdc_collateral_vault,
    mock_ripe,
    bob,
    starter_agent,
    governance,
    vault_registry,
    switchboard_alpha,
):
    """Test that redemption withdraws from idle leverageVaultToken (step 4a)"""
    vault = undy_levg_vault_usdc

    # 1. User deposits USDC into vault to get shares
    deposit_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(bob, deposit_amount, sender=governance.address)
    mock_usdc.approve(vault.address, deposit_amount, sender=bob)

    # Enable deposits and auto-deposit
    vault_registry.setCanDeposit(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setShouldAutoDeposit(vault.address, True, sender=switchboard_alpha.address)

    shares = vault.deposit(deposit_amount, bob, sender=bob)
    assert shares > 0

    # 2. USDC should be auto-deposited into collateral vault
    collateral_balance = mock_usdc_collateral_vault.balanceOf(vault.address)
    assert collateral_balance > 0

    # 3. Add collateral to Ripe
    vault.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc_collateral_vault.address,
        collateral_balance,
        sender=starter_agent.address
    )

    # 4. Manually set user collateral to less than deposited (simulating some was used for borrowing)
    reduced_collateral = collateral_balance // 2  # Half of what we deposited
    mock_ripe.setUserCollateral(vault.address, mock_usdc_collateral_vault.address, reduced_collateral)

    # 5. Deposit some USDC into leverage vault (idle, not on Ripe)
    leverage_deposit = deposit_amount // 2
    mock_usdc.mint(vault.address, leverage_deposit, sender=governance.address)
    vault.depositForYield(
        2,  # mock yield lego
        mock_usdc.address,
        mock_usdc_leverage_vault.address,
        leverage_deposit,
        sender=starter_agent.address
    )

    leverage_vault_balance = mock_usdc_leverage_vault.balanceOf(vault.address)
    assert leverage_vault_balance > 0

    # Enable withdrawals
    vault_registry.setCanWithdraw(vault.address, True, sender=switchboard_alpha.address)

    # 6. User redeems - should trigger step 4a (withdraw from idle leverageVaultToken)
    # When trying to redeem, it will:
    # - Step 1: withdraw idle USDC (none)
    # - Step 2: withdraw idle collateral vault token (none, it's on Ripe)
    # - Step 3: remove collateral from Ripe (reduced amount)
    # - Step 4a: withdraw from idle leverageVaultToken (should happen here!)

    pre_usdc = mock_usdc.balanceOf(bob)
    assets_received = vault.redeem(shares, bob, bob, sender=bob)

    # Verify redemption succeeded by withdrawing from leverage vault
    assert assets_received > 0
    assert mock_usdc.balanceOf(bob) == pre_usdc + assets_received
    assert mock_usdc_leverage_vault.balanceOf(vault.address) < leverage_vault_balance


def test_redeem_withdraws_from_leverage_vault_on_ripe(
    undy_levg_vault_usdc,
    mock_usdc,
    mock_usdc_leverage_vault,
    mock_usdc_collateral_vault,
    mock_ripe,
    bob,
    starter_agent,
    governance,
    vault_registry,
    switchboard_alpha,
):
    """Test that redemption withdraws from leverageVaultToken collateral on Ripe (step 4b)"""
    vault = undy_levg_vault_usdc

    # 1. User deposits USDC into vault to get shares
    deposit_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(bob, deposit_amount, sender=governance.address)
    mock_usdc.approve(vault.address, deposit_amount, sender=bob)

    # Enable deposits and auto-deposit
    vault_registry.setCanDeposit(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setShouldAutoDeposit(vault.address, True, sender=switchboard_alpha.address)

    shares = vault.deposit(deposit_amount, bob, sender=bob)
    assert shares > 0

    # 2. USDC should be auto-deposited into collateral vault
    collateral_balance = mock_usdc_collateral_vault.balanceOf(vault.address)
    assert collateral_balance > 0

    # 3. Add collateral to Ripe
    vault.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc_collateral_vault.address,
        collateral_balance,
        sender=starter_agent.address
    )

    # 4. Manually set user collateral to less than deposited (simulating some was used for borrowing)
    reduced_collateral = collateral_balance // 2
    mock_ripe.setUserCollateral(vault.address, mock_usdc_collateral_vault.address, reduced_collateral)

    # 5. Deposit USDC into leverage vault and add as collateral to Ripe
    leverage_deposit = deposit_amount // 2
    mock_usdc.mint(vault.address, leverage_deposit, sender=governance.address)
    vault.depositForYield(
        2,  # mock yield lego
        mock_usdc.address,
        mock_usdc_leverage_vault.address,
        leverage_deposit,
        sender=starter_agent.address
    )

    leverage_vault_balance = mock_usdc_leverage_vault.balanceOf(vault.address)
    vault.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc_leverage_vault.address,
        leverage_vault_balance,
        sender=starter_agent.address
    )

    # Manually reduce leverage vault collateral on Ripe
    reduced_leverage_collateral = leverage_vault_balance // 2
    mock_ripe.setUserCollateral(vault.address, mock_usdc_leverage_vault.address, reduced_leverage_collateral)

    # Verify leverage vault tokens are on Ripe (idle balance = 0)
    assert mock_usdc_leverage_vault.balanceOf(vault.address) == 0

    # Enable withdrawals
    vault_registry.setCanWithdraw(vault.address, True, sender=switchboard_alpha.address)

    # 6. User redeems - should trigger step 4b (remove from Ripe and withdraw)
    # When trying to redeem, it will:
    # - Step 1: withdraw idle USDC (none)
    # - Step 2: withdraw idle collateral vault token (none, it's on Ripe)
    # - Step 3: remove collateral from Ripe (reduced amount)
    # - Step 4a: withdraw from idle leverageVaultToken (none, it's on Ripe)
    # - Step 4b: remove leverageVaultToken collateral from Ripe (should happen here!)

    pre_usdc = mock_usdc.balanceOf(bob)
    assets_received = vault.redeem(shares, bob, bob, sender=bob)

    # Verify redemption succeeded by removing from Ripe and withdrawing
    assert assets_received > 0
    assert mock_usdc.balanceOf(bob) == pre_usdc + assets_received


def test_redeem_checks_collateral_vault_before_leverage_vault(
    undy_levg_vault_usdc,
    mock_usdc,
    mock_usdc_leverage_vault,
    mock_usdc_collateral_vault,
    bob,
    starter_agent,
    governance,
    vault_registry,
    switchboard_alpha,
):
    """Test that redemption checks collateral vault first, then leverage vault"""
    vault = undy_levg_vault_usdc

    # 1. User deposits USDC into vault to get shares (with auto-deposit)
    deposit_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(bob, deposit_amount, sender=governance.address)
    mock_usdc.approve(vault.address, deposit_amount, sender=bob)

    vault_registry.setCanDeposit(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setShouldAutoDeposit(vault.address, True, sender=switchboard_alpha.address)

    shares = vault.deposit(deposit_amount, bob, sender=bob)
    assert shares > 0

    # 2. After auto-deposit, manually split: withdraw from collateral and deposit some into leverage
    collateral_balance = mock_usdc_collateral_vault.balanceOf(vault.address)
    half = collateral_balance // 2

    # Withdraw half from collateral vault
    vault.withdrawFromYield(
        2,  # mock yield lego
        mock_usdc_collateral_vault.address,
        half,
        sender=starter_agent.address
    )

    # Deposit that half into leverage vault
    vault.depositForYield(
        2,
        mock_usdc.address,
        mock_usdc_leverage_vault.address,
        half,
        sender=starter_agent.address
    )

    # Verify both vaults have USDC
    collateral_balance = mock_usdc_collateral_vault.balanceOf(vault.address)
    leverage_balance = mock_usdc_leverage_vault.balanceOf(vault.address)
    assert collateral_balance > 0
    assert leverage_balance > 0

    # Enable withdrawals
    vault_registry.setCanWithdraw(vault.address, True, sender=switchboard_alpha.address)

    # 3. User redeems small amount - should come from idle USDC and collateral vault first
    small_shares = shares // 10  # 10% of shares
    vault.redeem(small_shares, bob, bob, sender=bob)

    # Verify collateral vault was used (reduced), leverage vault untouched
    assert mock_usdc_collateral_vault.balanceOf(vault.address) < collateral_balance
    assert mock_usdc_leverage_vault.balanceOf(vault.address) == leverage_balance


def test_redeem_uses_leverage_vault_when_collateral_insufficient(
    undy_levg_vault_usdc,
    mock_usdc,
    mock_usdc_leverage_vault,
    mock_usdc_collateral_vault,
    bob,
    starter_agent,
    governance,
    vault_registry,
    switchboard_alpha,
):
    """Test that redemption uses leverage vault when collateral vault is insufficient"""
    vault = undy_levg_vault_usdc

    # 1. User deposits USDC into vault to get shares (with auto-deposit)
    deposit_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(bob, deposit_amount, sender=governance.address)
    mock_usdc.approve(vault.address, deposit_amount, sender=bob)

    vault_registry.setCanDeposit(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setShouldAutoDeposit(vault.address, True, sender=switchboard_alpha.address)

    shares = vault.deposit(deposit_amount, bob, sender=bob)
    assert shares > 0

    # 2. Agent puts most funds in leverage vault, small amount in collateral
    collateral_balance_full = mock_usdc_collateral_vault.balanceOf(vault.address)
    small_amount = collateral_balance_full // 10  # Keep only 10% in collateral
    large_amount = collateral_balance_full - small_amount

    # Withdraw most from collateral vault
    vault.withdrawFromYield(
        2,
        mock_usdc_collateral_vault.address,
        large_amount,
        sender=starter_agent.address
    )

    # Deposit most into leverage vault
    vault.depositForYield(
        2,
        mock_usdc.address,
        mock_usdc_leverage_vault.address,
        large_amount,
        sender=starter_agent.address
    )

    collateral_balance_pre = mock_usdc_collateral_vault.balanceOf(vault.address)
    leverage_balance_pre = mock_usdc_leverage_vault.balanceOf(vault.address)

    assert collateral_balance_pre < leverage_balance_pre  # More in leverage

    # Enable withdrawals
    vault_registry.setCanWithdraw(vault.address, True, sender=switchboard_alpha.address)

    # 3. User redeems large amount - collateral won't be enough, must use leverage vault
    large_shares = shares * 8 // 10  # 80% of shares
    pre_usdc = mock_usdc.balanceOf(bob)
    assets_received = vault.redeem(large_shares, bob, bob, sender=bob)

    # Verify both vaults were used
    collateral_balance_post = mock_usdc_collateral_vault.balanceOf(vault.address)
    leverage_balance_post = mock_usdc_leverage_vault.balanceOf(vault.address)

    assert collateral_balance_post < collateral_balance_pre  # Collateral was used
    assert leverage_balance_post < leverage_balance_pre  # Leverage was also used (step 4)
    assert assets_received > 0
    assert mock_usdc.balanceOf(bob) == pre_usdc + assets_received


#################################################
# 10. Full Lifecycle Integration Tests        #
#################################################


def test_usdc_vault_complete_lifecycle(
    setup_prices,
    usdc_wallet_with_funds,
    mock_usdc,
    mock_usdc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_green_token,
    mock_ripe,
    mock_swap_lego,
    lego_book,
    bob,
    starter_agent,
    governance,
    vault_registry,
    switchboard_alpha,
):
    """Test complete lifecycle for USDC vault: deposit → leverage → yield → deleverage → withdraw"""
    vault = usdc_wallet_with_funds

    # Enable all operations
    vault_registry.setCanDeposit(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setCanWithdraw(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setShouldAutoDeposit(vault.address, True, sender=switchboard_alpha.address)

    # 1. User deposits USDC
    deposit_amount = 20_000 * SIX_DECIMALS
    mock_usdc.mint(bob, deposit_amount, sender=governance.address)
    mock_usdc.approve(vault.address, deposit_amount, sender=bob)
    shares = vault.deposit(deposit_amount, bob, sender=bob)
    assert shares > 0

    # 2. Auto-deposit should have moved USDC to collateral vault
    collateral_balance = mock_usdc_collateral_vault.balanceOf(vault.address)
    assert collateral_balance > 0

    # 3. Add collateral to Ripe
    vault.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc_collateral_vault.address,
        collateral_balance,
        sender=starter_agent.address
    )
    assert mock_ripe.userCollateral(vault.address, mock_usdc_collateral_vault.address) == collateral_balance

    # 4. Borrow GREEN (leverage up)
    borrow_amount = 10_000 * EIGHTEEN_DECIMALS
    vault.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        borrow_amount,
        sender=starter_agent.address
    )
    assert mock_ripe.userDebt(vault.address) == borrow_amount

    # 5. Swap GREEN → USDC
    swap_lego_id = lego_book.getRegId(mock_swap_lego.address)
    swap_instruction = (swap_lego_id, borrow_amount, 9_900 * SIX_DECIMALS, [mock_green_token.address, mock_usdc.address], [])
    _, _, _, usdc_received, _ = vault.swapTokens([swap_instruction], sender=starter_agent.address)
    assert usdc_received >= 9_900 * SIX_DECIMALS

    # 6. Deposit USDC to leverage vault (productive use)
    vault.depositForYield(
        2,
        mock_usdc.address,
        mock_usdc_leverage_vault.address,
        usdc_received,
        sender=starter_agent.address
    )
    leverage_balance = mock_usdc_leverage_vault.balanceOf(vault.address)
    assert leverage_balance > 0

    # 7. Simulate yield generation over time
    yield_amount = leverage_balance // 10  # 10% yield
    mock_usdc.mint(mock_usdc_leverage_vault.address, yield_amount, sender=governance.address)

    # 8. Begin unwinding: withdraw from leverage vault
    total_leverage = mock_usdc_leverage_vault.balanceOf(vault.address)
    _, _, underlying_received, _ = vault.withdrawFromYield(
        2,
        mock_usdc_leverage_vault.address,
        total_leverage,
        sender=starter_agent.address
    )
    assert underlying_received > usdc_received  # Got yield

    # 9. Swap some USDC back to GREEN for debt repayment
    # Only mint what's needed for repayment (no extra since there's no interest in mocks)
    green_needed = borrow_amount
    swap_instruction_back = (swap_lego_id, underlying_received, green_needed, [mock_usdc.address, mock_green_token.address], [])

    # Give vault GREEN for repayment (simulate swap)
    mock_green_token.mint(vault.address, green_needed, sender=governance.address)

    # 10. Repay debt
    vault.repayDebt(
        RIPE_LEGO_ID,
        mock_green_token.address,
        borrow_amount,
        sender=starter_agent.address
    )
    assert mock_ripe.userDebt(vault.address) == 0

    # 11. Remove collateral from Ripe
    collateral_on_ripe = mock_ripe.userCollateral(vault.address, mock_usdc_collateral_vault.address)
    vault.removeCollateral(
        RIPE_LEGO_ID,
        mock_usdc_collateral_vault.address,
        collateral_on_ripe,
        sender=starter_agent.address
    )
    assert mock_ripe.userCollateral(vault.address, mock_usdc_collateral_vault.address) == 0

    # 11b. Withdraw from collateral vault to get USDC back
    vault.withdrawFromYield(
        2,
        mock_usdc_collateral_vault.address,
        collateral_on_ripe,
        sender=starter_agent.address
    )

    # 12. User withdraws (final step)
    initial_balance = mock_usdc.balanceOf(bob)
    # Use redeemWithMinAmountOut to handle rounding issues
    # Accept 99.9% of the deposit as minimum (accounts for rounding)
    min_amount = deposit_amount * 999 // 1000
    assets_received = vault.redeemWithMinAmountOut(shares, min_amount, bob, bob, sender=bob)

    # User should have received original deposit + some yield
    assert assets_received >= deposit_amount
    assert mock_usdc.balanceOf(bob) == initial_balance + assets_received

    # Vault should be empty after full redemption
    assert vault.totalSupply(sender=bob) == 0
    # May have some dust from rounding, but should be minimal (<0.01 USDC)
    assert vault.totalAssets(sender=bob) <= 10000, f"Vault should be empty but has {vault.totalAssets(sender=bob)} assets remaining"  # Allow up to 0.01 USDC dust


def test_weth_vault_complete_lifecycle(
    setup_prices,
    undy_levg_vault_weth,
    mock_weth,
    mock_weth_collateral_vault,
    mock_usdc_leverage_vault,
    mock_green_token,
    mock_usdc,
    mock_ripe,
    mock_swap_lego,
    lego_book,
    bob,
    starter_agent,
    governance,
    vault_registry,
    switchboard_alpha,
):
    """Test complete lifecycle for WETH vault: deposit WETH → leverage → USDC yield → unwind"""
    vault = undy_levg_vault_weth

    # Enable all operations
    vault_registry.setCanDeposit(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setCanWithdraw(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setShouldAutoDeposit(vault.address, False, sender=switchboard_alpha.address)  # Manual control

    # Track initial state (may have leftovers from previous tests due to module fixtures)
    initial_assets = vault.totalAssets()
    initial_supply = vault.totalSupply()

    # 1. User deposits WETH
    deposit_amount = 2 * EIGHTEEN_DECIMALS  # 2 WETH
    boa.env.set_balance(bob, deposit_amount)
    mock_weth.deposit(value=deposit_amount, sender=bob)
    mock_weth.approve(vault.address, deposit_amount, sender=bob)
    shares = vault.deposit(deposit_amount, bob, sender=bob)
    assert shares > 0

    # 2. Deposit WETH to collateral vault
    vault.depositForYield(
        2,
        mock_weth.address,
        mock_weth_collateral_vault.address,
        deposit_amount,
        sender=starter_agent.address
    )
    collateral_balance = mock_weth_collateral_vault.balanceOf(vault.address)
    assert collateral_balance > 0

    # 3. Add WETH collateral to Ripe
    vault.addCollateral(
        RIPE_LEGO_ID,
        mock_weth_collateral_vault.address,
        collateral_balance,
        sender=starter_agent.address
    )
    assert mock_ripe.userCollateral(vault.address, mock_weth_collateral_vault.address) == collateral_balance

    # 4. Borrow GREEN against WETH collateral
    # With WETH at $2000, 2 WETH = $4000 collateral
    # Can safely borrow $2000 worth of GREEN
    borrow_amount = 2_000 * EIGHTEEN_DECIMALS
    vault.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        borrow_amount,
        sender=starter_agent.address
    )
    assert mock_ripe.userDebt(vault.address) == borrow_amount

    # 5. Swap GREEN → USDC to deploy in USDC leverage vault
    swap_lego_id = lego_book.getRegId(mock_swap_lego.address)
    swap_instruction = (swap_lego_id, borrow_amount, 1_980 * SIX_DECIMALS, [mock_green_token.address, mock_usdc.address], [])

    # Mock the swap by minting USDC
    mock_usdc.mint(vault.address, 2_000 * SIX_DECIMALS, sender=governance.address)

    # 6. Deploy USDC to leverage vault for yield
    vault.depositForYield(
        2,
        mock_usdc.address,
        mock_usdc_leverage_vault.address,
        2_000 * SIX_DECIMALS,
        sender=starter_agent.address
    )
    leverage_balance = mock_usdc_leverage_vault.balanceOf(vault.address)
    assert leverage_balance > 0

    # 7. Generate yield
    yield_amount = leverage_balance // 5  # 20% yield
    mock_usdc.mint(mock_usdc_leverage_vault.address, yield_amount, sender=governance.address)

    # 8. Unwind: withdraw from leverage vault
    total_leverage = mock_usdc_leverage_vault.balanceOf(vault.address)
    _, _, usdc_received, _ = vault.withdrawFromYield(
        2,
        mock_usdc_leverage_vault.address,
        total_leverage,
        sender=starter_agent.address
    )
    assert usdc_received > 2_000 * SIX_DECIMALS  # Original + yield

    # 9. Swap USDC back to GREEN for debt repayment
    # Give vault GREEN for repayment
    mock_green_token.mint(vault.address, borrow_amount + (100 * EIGHTEEN_DECIMALS), sender=governance.address)

    # 10. Repay GREEN debt
    vault.repayDebt(
        RIPE_LEGO_ID,
        mock_green_token.address,
        borrow_amount,
        sender=starter_agent.address
    )
    assert mock_ripe.userDebt(vault.address) == 0

    # 11. Remove WETH collateral from Ripe
    collateral_on_ripe = mock_ripe.userCollateral(vault.address, mock_weth_collateral_vault.address)
    vault.removeCollateral(
        RIPE_LEGO_ID,
        mock_weth_collateral_vault.address,
        collateral_on_ripe,
        sender=starter_agent.address
    )

    # 12. Withdraw WETH from collateral vault
    vault.withdrawFromYield(
        2,
        mock_weth_collateral_vault.address,
        collateral_balance,
        sender=starter_agent.address
    )

    # 13. User redeems shares for WETH
    initial_weth = mock_weth.balanceOf(bob)
    # Use redeemWithMinAmountOut to handle rounding issues
    # Account for both deposit and any initial assets (first depositor gets all)
    expected_redemption = deposit_amount + initial_assets
    min_amount = expected_redemption * 999 // 1000
    assets_received = vault.redeemWithMinAmountOut(shares, min_amount, bob, bob, sender=bob)

    # Should receive original WETH deposit + any initial vault assets (yield was in USDC, might have some left)
    assert assets_received >= deposit_amount, f"Should at least get deposit back: {assets_received} >= {deposit_amount}"
    assert mock_weth.balanceOf(bob) == initial_weth + assets_received

    # Vault should be empty after full redemption
    assert vault.totalSupply(sender=bob) == initial_supply, f"Supply should return to initial: {vault.totalSupply()} == {initial_supply}"
    # Note: WETH vault may have USDC yield left from leverage operations
    # This is expected - totalAssets includes value of all assets


def test_cbbtc_vault_complete_lifecycle(
    setup_prices,
    undy_levg_vault_cbbtc,
    mock_cbbtc,
    mock_cbbtc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_green_token,
    mock_savings_green_token,
    mock_usdc,
    mock_ripe,
    mock_swap_lego,
    lego_book,
    bob,
    starter_agent,
    governance,
    vault_registry,
    switchboard_alpha,
):
    """Test complete lifecycle for CBBTC vault with sGREEN integration"""
    vault = undy_levg_vault_cbbtc

    # Enable all operations
    vault_registry.setCanDeposit(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setCanWithdraw(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setShouldAutoDeposit(vault.address, False, sender=switchboard_alpha.address)  # Manual control

    # Track initial state (may have leftovers from previous tests due to module fixtures)
    initial_assets = vault.totalAssets()
    initial_supply = vault.totalSupply()

    # 1. User deposits CBBTC
    deposit_amount = 50000000  # 0.5 CBBTC (8 decimals)
    mock_cbbtc.mint(bob, deposit_amount, sender=governance.address)
    mock_cbbtc.approve(vault.address, deposit_amount, sender=bob)
    shares = vault.deposit(deposit_amount, bob, sender=bob)
    assert shares > 0

    # 2. Deposit CBBTC to collateral vault
    vault.depositForYield(
        2,
        mock_cbbtc.address,
        mock_cbbtc_collateral_vault.address,
        deposit_amount,
        sender=starter_agent.address
    )
    collateral_balance = mock_cbbtc_collateral_vault.balanceOf(vault.address)
    assert collateral_balance > 0

    # 3. Add CBBTC as collateral to Ripe
    vault.addCollateral(
        RIPE_LEGO_ID,
        mock_cbbtc_collateral_vault.address,
        collateral_balance,
        sender=starter_agent.address
    )

    # 4. Borrow GREEN (0.5 BTC at $90k = $45k collateral, borrow $20k GREEN)
    borrow_amount = 20_000 * EIGHTEEN_DECIMALS
    vault.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        borrow_amount,
        sender=starter_agent.address
    )

    # 5. Convert half of GREEN to sGREEN for yield
    sgreen_amount = borrow_amount // 2
    vault.depositForYield(
        RIPE_LEGO_ID,
        mock_green_token.address,
        mock_savings_green_token.address,
        sgreen_amount,
        sender=starter_agent.address
    )
    assert mock_savings_green_token.balanceOf(vault.address) == sgreen_amount

    # 6. Swap remaining GREEN to USDC
    swap_lego_id = lego_book.getRegId(mock_swap_lego.address)
    remaining_green = borrow_amount // 2
    swap_instruction = (swap_lego_id, remaining_green, 9_900 * SIX_DECIMALS, [mock_green_token.address, mock_usdc.address], [])

    # Mock swap by minting USDC
    mock_usdc.mint(vault.address, 10_000 * SIX_DECIMALS, sender=governance.address)

    # 7. Deploy USDC to leverage vault
    vault.depositForYield(
        2,
        mock_usdc.address,
        mock_usdc_leverage_vault.address,
        10_000 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    # 8. Simulate yield on both sGREEN and USDC leverage
    # sGREEN compounds internally (no action needed)
    # USDC leverage vault yields
    usdc_yield = 1_000 * SIX_DECIMALS
    mock_usdc.mint(mock_usdc_leverage_vault.address, usdc_yield, sender=governance.address)

    # 9. Begin unwinding: withdraw from leverage vault
    total_leverage = mock_usdc_leverage_vault.balanceOf(vault.address)
    vault.withdrawFromYield(
        2,
        mock_usdc_leverage_vault.address,
        total_leverage,
        sender=starter_agent.address
    )

    # 10. Withdraw sGREEN back to GREEN
    vault.withdrawFromYield(
        RIPE_LEGO_ID,
        mock_savings_green_token.address,
        sgreen_amount,
        sender=starter_agent.address
    )

    # 11. Repay GREEN debt
    # Give vault enough GREEN for repayment
    mock_green_token.mint(vault.address, borrow_amount, sender=governance.address)
    vault.repayDebt(
        RIPE_LEGO_ID,
        mock_green_token.address,
        borrow_amount,
        sender=starter_agent.address
    )
    assert mock_ripe.userDebt(vault.address) == 0

    # 12. Remove CBBTC collateral from Ripe
    collateral_on_ripe = mock_ripe.userCollateral(vault.address, mock_cbbtc_collateral_vault.address)
    vault.removeCollateral(
        RIPE_LEGO_ID,
        mock_cbbtc_collateral_vault.address,
        collateral_on_ripe,
        sender=starter_agent.address
    )

    # 13. Withdraw from collateral vault
    vault.withdrawFromYield(
        2,
        mock_cbbtc_collateral_vault.address,
        collateral_balance,
        sender=starter_agent.address
    )

    # 14. User redeems shares for CBBTC
    initial_cbbtc = mock_cbbtc.balanceOf(bob)
    # Use redeemWithMinAmountOut to handle rounding issues
    # Account for both deposit and any initial assets (first depositor gets all)
    expected_redemption = deposit_amount + initial_assets
    min_amount = expected_redemption * 999 // 1000
    assets_received = vault.redeemWithMinAmountOut(shares, min_amount, bob, bob, sender=bob)

    # Should receive original CBBTC deposit + any initial vault assets
    assert assets_received >= deposit_amount, f"Should at least get deposit back: {assets_received} >= {deposit_amount}"
    assert mock_cbbtc.balanceOf(bob) == initial_cbbtc + assets_received

    # Vault should be empty after full redemption
    assert vault.totalSupply(sender=bob) == initial_supply, f"Supply should return to initial: {vault.totalSupply()} == {initial_supply}"
    # Note: CBBTC vault may have USDC yield left from leverage operations
    # This is expected - totalAssets includes value of all assets


def test_cross_vault_interactions(
    setup_prices,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    alice,
    bob,
    charlie,
    governance,
    vault_registry,
    switchboard_alpha,
):
    """Test multiple vaults operating independently and correctly"""

    # Enable all vaults
    for vault in [undy_levg_vault_usdc, undy_levg_vault_cbbtc, undy_levg_vault_weth]:
        vault_registry.setCanDeposit(vault.address, True, sender=switchboard_alpha.address)
        vault_registry.setCanWithdraw(vault.address, True, sender=switchboard_alpha.address)
        vault_registry.setShouldAutoDeposit(vault.address, False, sender=switchboard_alpha.address)  # Manual control

    # Track initial state (may have leftovers from previous tests due to module fixtures)
    usdc_initial_assets = undy_levg_vault_usdc.totalAssets()
    cbbtc_initial_assets = undy_levg_vault_cbbtc.totalAssets()
    weth_initial_assets = undy_levg_vault_weth.totalAssets()

    # Alice uses USDC vault
    alice_usdc = 10_000 * SIX_DECIMALS
    mock_usdc.mint(alice, alice_usdc, sender=governance.address)
    mock_usdc.approve(undy_levg_vault_usdc.address, alice_usdc, sender=alice)
    alice_shares = undy_levg_vault_usdc.deposit(alice_usdc, alice, sender=alice)

    # Bob uses CBBTC vault
    bob_cbbtc = 1 * EIGHT_DECIMALS
    mock_cbbtc.mint(bob, bob_cbbtc, sender=governance.address)
    mock_cbbtc.approve(undy_levg_vault_cbbtc.address, bob_cbbtc, sender=bob)
    bob_shares = undy_levg_vault_cbbtc.deposit(bob_cbbtc, bob, sender=bob)

    # Charlie uses WETH vault
    charlie_weth = 3 * EIGHTEEN_DECIMALS
    boa.env.set_balance(charlie, charlie_weth)
    mock_weth.deposit(value=charlie_weth, sender=charlie)
    mock_weth.approve(undy_levg_vault_weth.address, charlie_weth, sender=charlie)
    charlie_shares = undy_levg_vault_weth.deposit(charlie_weth, charlie, sender=charlie)

    # Each vault maintains independent state - only check new shares
    assert undy_levg_vault_usdc.balanceOf(alice) == alice_shares
    assert undy_levg_vault_cbbtc.balanceOf(bob) == bob_shares
    assert undy_levg_vault_weth.balanceOf(charlie) == charlie_shares

    # Each vault has correct underlying assets (new deposits + any previous state)
    assert undy_levg_vault_usdc.totalAssets(sender=alice) == usdc_initial_assets + alice_usdc
    assert undy_levg_vault_cbbtc.totalAssets(sender=bob) == cbbtc_initial_assets + bob_cbbtc
    assert undy_levg_vault_weth.totalAssets(sender=charlie) == weth_initial_assets + charlie_weth

    # All users can redeem from their respective vaults
    alice_redeemed = undy_levg_vault_usdc.redeem(alice_shares, alice, alice, sender=alice)
    bob_redeemed = undy_levg_vault_cbbtc.redeem(bob_shares, bob, bob, sender=bob)
    charlie_redeemed = undy_levg_vault_weth.redeem(charlie_shares, charlie, charlie, sender=charlie)

    # Verify correct redemptions (including any initial state from previous tests)
    # If there were initial assets with 0 shares, first depositor gets them all
    assert alice_redeemed == alice_usdc + usdc_initial_assets
    assert bob_redeemed == bob_cbbtc + cbbtc_initial_assets
    assert charlie_redeemed == charlie_weth + weth_initial_assets

    # Vaults should be empty after full redemption
    assert undy_levg_vault_usdc.totalSupply(sender=alice) == 0
    assert undy_levg_vault_cbbtc.totalSupply(sender=bob) == 0
    assert undy_levg_vault_weth.totalSupply(sender=charlie) == 0
