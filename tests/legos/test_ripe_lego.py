import pytest
import boa

from contracts.core.userWallet import UserWalletConfig
from constants import MAX_UINT256, ZERO_ADDRESS, EIGHTEEN_DECIMALS
from conf_utils import filter_logs


############
# Fixtures #
############


@pytest.fixture(scope="module")
def setup_mock_prices(mock_ripe, mock_green_token, mock_savings_green_token, mock_ripe_token):
    """Set up mock prices for testing"""
    # Set price of 1 GREEN = $1 USD (18 decimals)
    mock_ripe.setPrice(mock_green_token, 1 * EIGHTEEN_DECIMALS)
    # Set price of 1 SAVINGS_GREEN = $1 USD (since it's 1:1 with GREEN in the mock)
    mock_ripe.setPrice(mock_savings_green_token, 1 * EIGHTEEN_DECIMALS)
    # Set price of 1 RIPE = $2 USD
    mock_ripe.setPrice(mock_ripe_token, 2 * EIGHTEEN_DECIMALS)
    return mock_ripe


@pytest.fixture(scope="module")
def bob_wallet_with_green(bob_user_wallet, mock_green_token, whale):
    """Give bob's wallet some GREEN tokens"""
    amount = 100_000 * EIGHTEEN_DECIMALS
    mock_green_token.transfer(bob_user_wallet.address, amount, sender=whale)
    return bob_user_wallet


@pytest.fixture(scope="module")
def bob_wallet_with_savings_green(bob_user_wallet, mock_savings_green_token, mock_green_token, whale):
    """Give bob's wallet some SAVINGS_GREEN tokens"""
    # First get GREEN tokens
    green_amount = 100_000 * EIGHTEEN_DECIMALS
    mock_green_token.transfer(bob_user_wallet.address, green_amount, sender=whale)

    # Deposit into savings green via bob's wallet
    # This requires calling deposit on the vault from the wallet
    # For now, just transfer savings green directly
    savings_amount = 50_000 * EIGHTEEN_DECIMALS
    mock_green_token.approve(mock_savings_green_token, savings_amount, sender=whale)
    mock_savings_green_token.deposit(savings_amount, whale, sender=whale)
    mock_savings_green_token.transfer(bob_user_wallet.address, savings_amount, sender=whale)
    return bob_user_wallet


@pytest.fixture(scope="module")
def bob_wallet_with_ripe(bob_user_wallet, mock_ripe_token, whale):
    """Give bob's wallet some RIPE tokens"""
    amount = 10_000 * EIGHTEEN_DECIMALS
    mock_ripe_token.transfer(bob_user_wallet.address, amount, sender=whale)
    return bob_user_wallet


@pytest.fixture(scope="module")
def bob_wallet_with_usdc(bob_user_wallet, mock_usdc, governance):
    """Give bob's wallet some USDC tokens"""
    amount = 100_000 * (10 ** 6)  # 100k USDC (6 decimals)
    mock_usdc.mint(bob_user_wallet.address, amount, sender=governance.address)
    return bob_user_wallet


@pytest.fixture
def mock_deleverage_lego(lego_book, governance, mock_green_token):
    lego = boa.load("contracts/mock/MockDeleverageLego.vy", mock_green_token, name="mock_deleverage_lego")
    lego_book.startAddNewAddressToRegistry(lego.address, "Mock Deleverage", sender=governance.address)
    boa.env.time_travel(blocks=lego_book.registryChangeTimeLock() + 1)
    lego_id = lego_book.confirmNewAddressToRegistry(lego.address, sender=governance.address)
    return lego, lego_id


#################################
# 1. Yield Operations Tests #
#################################


def test_ripe_savings_green_deposit_max(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    mock_savings_green_token,
    lego_book,
    bob,
    _test,
):
    """Test full deposit of GREEN_TOKEN into SAVINGS_GREEN vault"""
    lego_id = lego_book.getRegId(lego_ripe)

    # Pre balances
    pre_green_balance = mock_green_token.balanceOf(bob_wallet_with_green)
    pre_savings_balance = mock_savings_green_token.balanceOf(bob_wallet_with_green)

    # Deposit all GREEN tokens into SAVINGS_GREEN
    deposit_amount, vault_token, vault_tokens_received, usd_value = bob_wallet_with_green.depositForYield(
        lego_id,
        mock_green_token,
        mock_savings_green_token,
        MAX_UINT256,
        sender=bob
    )

    # Verify deposit occurred
    assert deposit_amount > 0
    assert vault_tokens_received > 0
    assert vault_token == mock_savings_green_token.address
    assert usd_value > 0

    # Verify balances changed correctly
    _test(mock_green_token.balanceOf(bob_wallet_with_green), pre_green_balance - deposit_amount)
    assert mock_savings_green_token.balanceOf(bob_wallet_with_green) > pre_savings_balance

    # Verify event was logged
    log_wallet = filter_logs(bob_wallet_with_green, "WalletAction")[0]
    assert log_wallet.op == 10  # yield deposit
    assert log_wallet.asset1 == mock_green_token.address
    assert log_wallet.asset2 == vault_token


def test_ripe_savings_green_deposit_partial(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    mock_savings_green_token,
    lego_book,
    bob,
    _test,
):
    """Test partial deposit of GREEN_TOKEN into SAVINGS_GREEN vault"""
    lego_id = lego_book.getRegId(lego_ripe)

    # Pre balances
    pre_green_balance = mock_green_token.balanceOf(bob_wallet_with_green)
    partial_amount = pre_green_balance // 2

    # Deposit half of GREEN tokens
    deposit_amount, vault_token, vault_tokens_received, usd_value = bob_wallet_with_green.depositForYield(
        lego_id,
        mock_green_token,
        mock_savings_green_token,
        partial_amount,
        sender=bob
    )

    # Verify deposit occurred
    assert deposit_amount > 0
    _test(deposit_amount, partial_amount)
    assert vault_tokens_received > 0

    # Verify partial amount was used
    _test(mock_green_token.balanceOf(bob_wallet_with_green), pre_green_balance - partial_amount)


def test_ripe_savings_green_withdraw_max(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    mock_savings_green_token,
    lego_book,
    bob,
    _test,
):
    """Test full withdrawal from SAVINGS_GREEN vault"""
    lego_id = lego_book.getRegId(lego_ripe)

    # First deposit some tokens
    bob_wallet_with_green.depositForYield(
        lego_id,
        mock_green_token,
        mock_savings_green_token,
        10_000 * EIGHTEEN_DECIMALS,
        sender=bob
    )

    # Pre balances
    pre_green_balance = mock_green_token.balanceOf(bob_wallet_with_green)
    pre_savings_balance = mock_savings_green_token.balanceOf(bob_wallet_with_green)

    # Withdraw all SAVINGS_GREEN
    vault_token_burned, underlying_asset, underlying_amount, usd_value = bob_wallet_with_green.withdrawFromYield(
        lego_id,
        mock_savings_green_token,
        MAX_UINT256,
        sender=bob
    )

    # Verify withdrawal occurred
    assert vault_token_burned > 0
    assert underlying_amount > 0
    assert underlying_asset == mock_green_token.address
    assert usd_value > 0

    # Verify balances changed correctly
    _test(vault_token_burned, pre_savings_balance)
    assert mock_green_token.balanceOf(bob_wallet_with_green) > pre_green_balance

    # Verify event was logged
    log_wallet = filter_logs(bob_wallet_with_green, "WalletAction")[0]
    assert log_wallet.op == 11  # yield withdraw
    assert log_wallet.asset2 == underlying_asset


def test_ripe_savings_green_withdraw_partial(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    mock_savings_green_token,
    lego_book,
    bob,
    _test,
):
    """Test partial withdrawal from SAVINGS_GREEN vault"""
    lego_id = lego_book.getRegId(lego_ripe)

    # First deposit some tokens
    _, _, vault_tokens_received, _ = bob_wallet_with_green.depositForYield(
        lego_id,
        mock_green_token,
        mock_savings_green_token,
        20_000 * EIGHTEEN_DECIMALS,
        sender=bob
    )

    # Withdraw half
    partial_amount = vault_tokens_received // 2
    vault_token_burned, underlying_asset, underlying_amount, usd_value = bob_wallet_with_green.withdrawFromYield(
        lego_id,
        mock_savings_green_token,
        partial_amount,
        sender=bob
    )

    # Verify partial withdrawal
    assert vault_token_burned > 0
    _test(vault_token_burned, partial_amount)
    assert underlying_amount > 0


####################################
# 2. Collateral Management Tests #
####################################


def test_ripe_add_collateral_green_token(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    mock_ripe,
    lego_book,
    bob,
    _test,
):
    """Test adding GREEN_TOKEN as collateral to Ripe Protocol"""
    lego_id = lego_book.getRegId(lego_ripe)

    # Pre balances
    pre_green_balance = mock_green_token.balanceOf(bob_wallet_with_green)

    # Add collateral
    collateral_amount = 5_000 * EIGHTEEN_DECIMALS
    amount_deposited, usd_value = bob_wallet_with_green.addCollateral(
        lego_id,
        mock_green_token,
        collateral_amount,
        sender=bob
    )

    # Verify collateral was added
    assert amount_deposited > 0
    _test(amount_deposited, collateral_amount)
    assert usd_value > 0

    # Verify balance changed
    _test(mock_green_token.balanceOf(bob_wallet_with_green), pre_green_balance - collateral_amount)

    # Verify collateral is tracked in mock
    assert mock_ripe.userCollateral(bob_wallet_with_green.address, mock_green_token) == collateral_amount


def test_ripe_add_collateral_ripe_token(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_ripe,
    mock_ripe_token,
    mock_ripe,
    lego_book,
    bob,
    _test,
):
    """Test adding RIPE_TOKEN as collateral (governance vault)"""
    lego_id = lego_book.getRegId(lego_ripe)

    # Pre balances
    pre_ripe_balance = mock_ripe_token.balanceOf(bob_wallet_with_ripe)

    # Add collateral with lock duration in extraData
    collateral_amount = 1_000 * EIGHTEEN_DECIMALS
    lock_duration = 30 * 24 * 60 * 60  # 30 days in seconds

    amount_deposited, usd_value = bob_wallet_with_ripe.addCollateral(
        lego_id,
        mock_ripe_token,
        collateral_amount,
        lock_duration.to_bytes(32, 'big'),  # extraData for lock duration (as bytes32)
        sender=bob
    )

    # Verify collateral was added
    assert amount_deposited > 0
    assert usd_value > 0

    # Verify balance changed
    _test(mock_ripe_token.balanceOf(bob_wallet_with_ripe), pre_ripe_balance - collateral_amount)


def test_ripe_remove_collateral(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    mock_ripe,
    lego_book,
    bob,
    _test,
):
    """Test removing collateral from Ripe Protocol"""
    lego_id = lego_book.getRegId(lego_ripe)

    # First add collateral
    collateral_amount = 10_000 * EIGHTEEN_DECIMALS
    bob_wallet_with_green.addCollateral(
        lego_id,
        mock_green_token,
        collateral_amount,
        sender=bob
    )

    # Pre balances
    pre_green_balance = mock_green_token.balanceOf(bob_wallet_with_green)

    # Remove half the collateral
    remove_amount = collateral_amount // 2
    amount_removed, usd_value = bob_wallet_with_green.removeCollateral(
        lego_id,
        mock_green_token,
        remove_amount,
        sender=bob
    )

    # Verify collateral was removed
    assert amount_removed > 0
    _test(amount_removed, remove_amount)
    assert usd_value > 0

    # Verify balance changed
    _test(mock_green_token.balanceOf(bob_wallet_with_green), pre_green_balance + remove_amount)




#################################
# 3. Borrow & Repayment Tests #
#################################


def test_ripe_borrow_green_token(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    mock_ripe,
    lego_book,
    bob,
    _test,
):
    """Test borrowing GREEN_TOKEN from Ripe Protocol"""
    lego_id = lego_book.getRegId(lego_ripe)

    # First add collateral
    bob_wallet_with_green.addCollateral(
        lego_id,
        mock_green_token,
        50_000 * EIGHTEEN_DECIMALS,
        sender=bob
    )

    # Pre balances
    pre_green_balance = mock_green_token.balanceOf(bob_wallet_with_green)

    # Borrow GREEN tokens
    borrow_amount = 10_000 * EIGHTEEN_DECIMALS
    amount_borrowed, usd_value = bob_wallet_with_green.borrow(
        lego_id,
        mock_green_token,
        borrow_amount,
        sender=bob
    )

    # Verify borrow occurred
    assert amount_borrowed > 0
    _test(amount_borrowed, borrow_amount)
    assert usd_value > 0

    # Verify balance changed
    _test(mock_green_token.balanceOf(bob_wallet_with_green), pre_green_balance + borrow_amount)

    # Verify debt is tracked
    assert mock_ripe.userDebt(bob_wallet_with_green.address) == borrow_amount


def test_ripe_borrow_savings_green(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    mock_savings_green_token,
    mock_ripe,
    lego_book,
    bob,
):
    """Test borrowing SAVINGS_GREEN from Ripe Protocol"""
    lego_id = lego_book.getRegId(lego_ripe)

    # First add collateral
    bob_wallet_with_green.addCollateral(
        lego_id,
        mock_green_token,
        50_000 * EIGHTEEN_DECIMALS,
        sender=bob
    )

    # Pre balances
    pre_savings_balance = mock_savings_green_token.balanceOf(bob_wallet_with_green)

    # Borrow SAVINGS_GREEN tokens
    borrow_amount = 10_000 * EIGHTEEN_DECIMALS
    amount_borrowed, usd_value = bob_wallet_with_green.borrow(
        lego_id,
        mock_savings_green_token,
        borrow_amount,
        sender=bob
    )

    # Verify borrow occurred
    assert amount_borrowed > 0
    assert usd_value > 0

    # Verify balance increased
    assert mock_savings_green_token.balanceOf(bob_wallet_with_green) > pre_savings_balance


def test_ripe_repay_with_green_token(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    mock_ripe,
    lego_book,
    bob,
    _test,
):
    """Test repaying debt with GREEN_TOKEN"""
    lego_id = lego_book.getRegId(lego_ripe)

    # First add collateral and borrow
    bob_wallet_with_green.addCollateral(
        lego_id,
        mock_green_token,
        50_000 * EIGHTEEN_DECIMALS,
        sender=bob
    )
    borrow_amount = 10_000 * EIGHTEEN_DECIMALS
    bob_wallet_with_green.borrow(
        lego_id,
        mock_green_token,
        borrow_amount,
        sender=bob
    )

    # Pre balances
    pre_green_balance = mock_green_token.balanceOf(bob_wallet_with_green)
    pre_debt = mock_ripe.userDebt(bob_wallet_with_green.address)

    # Repay half the debt
    repay_amount = borrow_amount // 2
    amount_repaid, usd_value = bob_wallet_with_green.repayDebt(
        lego_id,
        mock_green_token,
        repay_amount,
        sender=bob
    )

    # Verify repayment occurred
    assert amount_repaid > 0
    assert usd_value > 0

    # Verify balance changed
    assert mock_green_token.balanceOf(bob_wallet_with_green) < pre_green_balance

    # Verify debt decreased
    assert mock_ripe.userDebt(bob_wallet_with_green.address) < pre_debt


def test_ripe_repay_with_savings_green(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    mock_savings_green_token,
    mock_ripe,
    lego_book,
    bob,
    _test,
):
    """Test repaying debt with SAVINGS_GREEN"""
    lego_id = lego_book.getRegId(lego_ripe)

    # First add collateral and borrow GREEN
    bob_wallet_with_green.addCollateral(
        lego_id,
        mock_green_token,
        50_000 * EIGHTEEN_DECIMALS,
        sender=bob
    )
    borrow_amount = 10_000 * EIGHTEEN_DECIMALS
    bob_wallet_with_green.borrow(
        lego_id,
        mock_green_token,
        borrow_amount,
        sender=bob
    )

    # Convert some GREEN to SAVINGS_GREEN for repayment
    green_to_convert = 5_000 * EIGHTEEN_DECIMALS
    bob_wallet_with_green.depositForYield(
        lego_id,
        mock_green_token,
        mock_savings_green_token,
        green_to_convert,
        sender=bob
    )

    # Pre balances
    pre_savings_balance = mock_savings_green_token.balanceOf(bob_wallet_with_green)
    pre_debt = mock_ripe.userDebt(bob_wallet_with_green.address)

    # Repay with SAVINGS_GREEN (use half of what we have)
    repay_savings_amount = pre_savings_balance // 2
    amount_repaid, usd_value = bob_wallet_with_green.repayDebt(
        lego_id,
        mock_savings_green_token,
        repay_savings_amount,
        sender=bob
    )

    # Verify repayment occurred
    assert amount_repaid > 0
    assert usd_value > 0

    # Verify SAVINGS_GREEN balance decreased
    assert mock_savings_green_token.balanceOf(bob_wallet_with_green) < pre_savings_balance

    # Verify debt decreased (by approximately the GREEN amount redeemed from SAVINGS_GREEN)
    current_debt = mock_ripe.userDebt(bob_wallet_with_green.address)
    assert current_debt < pre_debt
    # The debt should have decreased by roughly the amount we repaid
    _test(pre_debt - current_debt, amount_repaid)


def test_user_wallet_deleverage_specific_assets(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_usdc,
    mock_ripe,
    mock_green_token,
    mock_usdc,
    lego_book,
    bob,
):
    """Specific user-wallet deleverage goes through the wallet and logs action 44."""
    lego_id = lego_book.getRegId(lego_ripe)
    debt = 500 * EIGHTEEN_DECIMALS
    repay_amount = 125 * EIGHTEEN_DECIMALS
    mock_ripe.setPrice(mock_usdc, 1 * EIGHTEEN_DECIMALS)
    mock_ripe.setUserDebt(bob_wallet_with_usdc.address, debt)
    assert mock_usdc.balanceOf(bob_wallet_with_usdc.address) > 0

    deleverage_assets = [(1, mock_usdc.address, repay_amount)]
    repaid, usd_value = bob_wallet_with_usdc.deleverage(
        lego_id,
        deleverage_assets,
        0,
        b"",
        sender=bob,
    )

    assert repaid == repay_amount
    assert usd_value == repay_amount
    assert mock_ripe.userDebt(bob_wallet_with_usdc.address) == debt - repay_amount
    assert mock_green_token.allowance(bob_wallet_with_usdc.address, lego_ripe.address) == 0
    assert mock_usdc.allowance(bob_wallet_with_usdc.address, lego_ripe.address) == 0

    log_wallet = filter_logs(bob_wallet_with_usdc, "WalletAction")[-1]
    assert log_wallet.op == 44
    assert log_wallet.asset1 == mock_green_token.address
    assert log_wallet.amount1 == repay_amount
    assert log_wallet.amount2 == len(deleverage_assets)
    assert log_wallet.usdValue == usd_value
    assert log_wallet.legoId == lego_id
    assert log_wallet.signer == bob


def test_user_wallet_deleverage_auto_caps_to_debt(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_ripe,
    mock_green_token,
    lego_book,
    bob,
):
    """Auto user-wallet deleverage previews first, caps to actual debt, and logs action 45."""
    lego_id = lego_book.getRegId(lego_ripe)
    debt = 300 * EIGHTEEN_DECIMALS
    auto_amount = 1_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(bob_wallet_with_green.address, debt)

    repaid, usd_value = bob_wallet_with_green.deleverage(
        lego_id,
        [],
        auto_amount,
        b"",
        sender=bob,
    )

    assert repaid == debt
    assert usd_value == debt
    assert mock_ripe.userDebt(bob_wallet_with_green.address) == 0
    assert mock_green_token.allowance(bob_wallet_with_green.address, lego_ripe.address) == 0

    log_wallet = filter_logs(bob_wallet_with_green, "WalletAction")[-1]
    assert log_wallet.op == 45
    assert log_wallet.asset1 == mock_green_token.address
    assert log_wallet.amount1 == debt
    assert log_wallet.amount2 == auto_amount
    assert log_wallet.usdValue == usd_value
    assert log_wallet.legoId == lego_id
    assert log_wallet.signer == bob


def test_user_wallet_deleverage_mode_guard(
    lego_ripe,
    bob_wallet_with_green,
    mock_usdc,
    lego_book,
    bob,
):
    lego_id = lego_book.getRegId(lego_ripe)
    deleverage_assets = [(1, mock_usdc.address, 1)]

    with boa.reverts("invalid mode"):
        bob_wallet_with_green.deleverage(lego_id, [], 0, b"", sender=bob)

    with boa.reverts("invalid mode"):
        bob_wallet_with_green.deleverage(lego_id, deleverage_assets, 1, b"", sender=bob)


def test_user_wallet_deleverage_non_ripe_lego_reverts(
    bob_wallet_with_green,
    mock_usdc,
    mock_dex_lego,
    lego_book,
    bob,
):
    mock_dex_lego_id = lego_book.getRegId(mock_dex_lego)
    assert mock_dex_lego_id != 0
    assert lego_book.getAddr(mock_dex_lego_id) == mock_dex_lego.address
    deleverage_assets = [(1, mock_usdc.address, 1)]

    with boa.reverts():
        bob_wallet_with_green.deleverage(mock_dex_lego_id, deleverage_assets, 0, b"", sender=bob)


def test_ripe_direct_user_wallet_deleverage_compat_allows_agent_sender(
    lego_ripe,
    user_wallet,
    mock_ripe,
    mock_usdc,
    starter_agent_sender,
):
    """v_compat keeps the old direct specific deleverage path alive for agent senders."""
    debt = 100 * EIGHTEEN_DECIMALS
    repay_amount = 10 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(user_wallet.address, debt)
    deleverage_assets = [(1, mock_usdc.address, 10 * EIGHTEEN_DECIMALS)]

    repaid = lego_ripe.deleverageWithSpecificAssets(
        deleverage_assets,
        user_wallet.address,
        sender=starter_agent_sender.address,
    )
    assert repaid == repay_amount
    assert mock_ripe.userDebt(user_wallet.address) == debt - repay_amount

    with boa.reverts("no perms"):
        lego_ripe.deleverageWithSpecificAssets(
            deleverage_assets,
            user_wallet.address,
        )


def test_ripe_direct_user_wallet_auto_deleverage_compat_allows_agent_sender(
    lego_ripe,
    user_wallet,
    mock_ripe,
    starter_agent_sender,
):
    """v_compat keeps the old direct auto deleverage path alive for agent senders."""
    debt = 90 * EIGHTEEN_DECIMALS
    target = 25 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(user_wallet.address, debt)

    repaid = lego_ripe.deleverageUser(
        user_wallet.address,
        target,
        sender=starter_agent_sender.address,
    )
    assert repaid == target
    assert mock_ripe.userDebt(user_wallet.address) == debt - target

    with boa.reverts("no perms"):
        lego_ripe.deleverageUser(
            user_wallet.address,
            target,
        )


def test_user_wallet_deleverage_empty_preview_reverts(
    mock_deleverage_lego,
    bob_wallet_with_green,
    mock_green_token,
    bob,
):
    lego, lego_id = mock_deleverage_lego
    lego.setResponse([], [], 1, 1, mock_green_token.address)

    with boa.reverts("no preview assets"):
        bob_wallet_with_green.deleverage(lego_id, [], 1, b"", sender=bob)


def test_user_wallet_deleverage_empty_touched_reverts(
    mock_deleverage_lego,
    bob_wallet_with_green,
    mock_green_token,
    bob,
):
    lego, lego_id = mock_deleverage_lego
    lego.setResponse([mock_green_token.address], [], 1, 1, mock_green_token.address)

    with boa.reverts("no touched assets"):
        bob_wallet_with_green.deleverage(lego_id, [], 1, b"", sender=bob)


def test_user_wallet_deleverage_empty_touched_asset_reverts(
    mock_deleverage_lego,
    bob_wallet_with_green,
    mock_green_token,
    bob,
):
    lego, lego_id = mock_deleverage_lego
    lego.setResponse([mock_green_token.address], [ZERO_ADDRESS], 1, 1, mock_green_token.address)

    with boa.reverts("invalid touched"):
        bob_wallet_with_green.deleverage(lego_id, [], 1, b"", sender=bob)


def test_user_wallet_deleverage_auto_touched_must_be_preview_subset(
    mock_deleverage_lego,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    mock_usdc,
    bob,
):
    lego, lego_id = mock_deleverage_lego
    lego.setResponse([mock_green_token.address], [mock_usdc.address], 1, 1, mock_green_token.address)

    with boa.reverts("touched not subset"):
        bob_wallet_with_green.deleverage(lego_id, [], 1, b"", sender=bob)


def test_user_wallet_deleverage_specific_touched_must_be_requested_subset(
    mock_deleverage_lego,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    mock_usdc,
    bob,
):
    lego, lego_id = mock_deleverage_lego
    lego.setResponse([], [mock_green_token.address], 1, 1, mock_green_token.address)
    deleverage_assets = [(1, mock_usdc.address, 1)]

    with boa.reverts("touched not subset"):
        bob_wallet_with_green.deleverage(lego_id, deleverage_assets, 0, b"", sender=bob)


def test_user_wallet_deleverage_duplicate_touched_assets_allowed(
    mock_deleverage_lego,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    mock_usdc,
    bob,
):
    lego, lego_id = mock_deleverage_lego
    lego.setResponse([], [mock_usdc.address, mock_usdc.address], 7, 7, mock_green_token.address)
    deleverage_assets = [(1, mock_usdc.address, 7)]

    repaid, usd_value = bob_wallet_with_green.deleverage(lego_id, deleverage_assets, 0, b"", sender=bob)

    assert repaid == 7
    assert usd_value == 7
    log_wallet = filter_logs(bob_wallet_with_green, "WalletAction")[-1]
    assert log_wallet.op == 44
    assert log_wallet.amount1 == 7
    assert log_wallet.amount2 == len(deleverage_assets)


def test_user_wallet_deleverage_reconciles_green_when_touched(
    mock_deleverage_lego,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    whale,
    switchboard_alpha,
    bob,
):
    lego, lego_id = mock_deleverage_lego
    wallet_config = UserWalletConfig.at(bob_wallet_with_green.walletConfig())
    wallet_config.updateAssetData(0, mock_green_token.address, False, sender=switchboard_alpha.address)
    initial_data = bob_wallet_with_green.assetData(mock_green_token.address)

    extra_green = 17 * EIGHTEEN_DECIMALS
    mock_green_token.transfer(bob_wallet_with_green.address, extra_green, sender=whale)
    lego.setResponse([mock_green_token.address], [mock_green_token.address], 1, 1, mock_green_token.address)

    bob_wallet_with_green.deleverage(lego_id, [], 1, b"", sender=bob)

    updated_data = bob_wallet_with_green.assetData(mock_green_token.address)
    assert updated_data.assetBalance == mock_green_token.balanceOf(bob_wallet_with_green.address)
    assert updated_data.assetBalance == initial_data.assetBalance + extra_green


def test_user_wallet_deleverage_gas_profile_records_preview_and_execution(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_ripe,
    lego_book,
    bob,
):
    lego_id = lego_book.getRegId(lego_ripe)
    mock_ripe.setUserDebt(bob_wallet_with_green.address, 20 * EIGHTEEN_DECIMALS)

    before = int(boa.env.get_gas_used())
    bob_wallet_with_green.deleverage(
        lego_id,
        [],
        5 * EIGHTEEN_DECIMALS,
        b"",
        sender=bob,
    )
    gas_used = int(boa.env.get_gas_used()) - before

    assert gas_used > 0
    assert gas_used < 5_000_000


def test_user_wallet_deleverage_zero_repaid_reverts(
    mock_deleverage_lego,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    bob,
):
    lego, lego_id = mock_deleverage_lego
    lego.setResponse([mock_green_token.address], [mock_green_token.address], 0, 0, mock_green_token.address)

    with boa.reverts("no repayment"):
        bob_wallet_with_green.deleverage(lego_id, [], 1, b"", sender=bob)


def test_user_wallet_deleverage_reentrancy_reverts(
    mock_deleverage_lego,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    bob,
):
    lego, lego_id = mock_deleverage_lego
    lego.setResponse([mock_green_token.address], [mock_green_token.address], 1, 1, mock_green_token.address)
    lego.setReenter(True, lego_id)

    with boa.reverts():
        bob_wallet_with_green.deleverage(lego_id, [], 1, b"", sender=bob)


def test_user_wallet_deleverage_frozen_wallet_reverts(
    lego_ripe,
    bob_wallet_with_green,
    mock_usdc,
    lego_book,
    bob,
):
    lego_id = lego_book.getRegId(lego_ripe)
    wallet_config = UserWalletConfig.at(bob_wallet_with_green.walletConfig())
    deleverage_assets = [(1, mock_usdc.address, 1)]

    with boa.env.anchor():
        wallet_config.setFrozen(True, sender=bob)
        with boa.reverts("frozen wallet"):
            bob_wallet_with_green.deleverage(lego_id, deleverage_assets, 0, b"", sender=bob)


def test_user_wallet_deleverage_eject_mode_reverts(
    lego_ripe,
    bob_wallet_with_green,
    mock_usdc,
    lego_book,
    switchboard_alpha,
    bob,
):
    lego_id = lego_book.getRegId(lego_ripe)
    wallet_config = UserWalletConfig.at(bob_wallet_with_green.walletConfig())
    deleverage_assets = [(1, mock_usdc.address, 1)]

    with boa.env.anchor():
        wallet_config.setEjectionMode(True, sender=switchboard_alpha.address)
        with boa.reverts("invalid action in eject mode"):
            bob_wallet_with_green.deleverage(lego_id, deleverage_assets, 0, b"", sender=bob)


def test_user_wallet_deleverage_owner_respects_can_owner_manage_false(
    mock_deleverage_lego,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    high_command,
    createGlobalManagerSettings,
    bob,
):
    lego, lego_id = mock_deleverage_lego
    lego.setResponse([mock_green_token.address], [mock_green_token.address], 1, 1, mock_green_token.address)
    wallet_config = UserWalletConfig.at(bob_wallet_with_green.walletConfig())

    with boa.env.anchor():
        global_settings = createGlobalManagerSettings(_canOwnerManage=False)
        wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)

        with boa.reverts("no permission"):
            bob_wallet_with_green.deleverage(lego_id, [], 1, b"", sender=bob)


###################
# 4. View Functions Tests #
###################


def test_ripe_get_underlying_asset(
    lego_ripe,
    mock_green_token,
    mock_savings_green_token,
):
    """Test getting underlying asset from SAVINGS_GREEN"""
    underlying = lego_ripe.getUnderlyingAsset(mock_savings_green_token)
    assert underlying == mock_green_token.address


def test_ripe_get_price_per_share(
    lego_ripe,
    setup_mock_prices,
    mock_savings_green_token,
    lego_book,
    bob_wallet_with_green,
    mock_green_token,
    bob,
):
    """Test getting price per share for SAVINGS_GREEN"""
    # First deposit to register the vault
    lego_id = lego_book.getRegId(lego_ripe)
    bob_wallet_with_green.depositForYield(
        lego_id,
        mock_green_token,
        mock_savings_green_token,
        1_000 * EIGHTEEN_DECIMALS,
        sender=bob
    )

    # Get decimals from the vault
    decimals = mock_savings_green_token.decimals()

    # Get price per share
    pps = lego_ripe.getPricePerShare(mock_savings_green_token, decimals)
    assert pps > 0


def test_ripe_get_vault_token_amount(
    lego_ripe,
    mock_green_token,
    mock_savings_green_token,
):
    """Test calculating vault token amount from asset amount"""
    asset_amount = 1_000 * EIGHTEEN_DECIMALS
    vault_amount = lego_ripe.getVaultTokenAmount(
        mock_green_token,
        asset_amount,
        mock_savings_green_token
    )
    assert vault_amount > 0


########################
# 5. Registration Tests #
########################


def test_ripe_can_register_vault_token(
    lego_ripe,
    mock_green_token,
    mock_savings_green_token,
    bravo_token,
):
    """Test that only SAVINGS_GREEN can be registered"""
    # Should be able to register SAVINGS_GREEN with GREEN_TOKEN
    can_register = lego_ripe.canRegisterVaultToken(mock_green_token, mock_savings_green_token)
    assert can_register == True

    # Should NOT be able to register other tokens
    can_register_other = lego_ripe.canRegisterVaultToken(bravo_token, mock_savings_green_token)
    assert can_register_other == False


def test_ripe_vault_auto_registration(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    mock_savings_green_token,
    lego_book,
    bob,
):
    """Test that vault auto-registers on first deposit"""
    lego_id = lego_book.getRegId(lego_ripe)

    # Do a deposit - this should auto-register the vault
    bob_wallet_with_green.depositForYield(
        lego_id,
        mock_green_token,
        mock_savings_green_token,
        1_000 * EIGHTEEN_DECIMALS,
        sender=bob
    )

    # Verify the vault is now tracked (we can get price per share)
    decimals = mock_savings_green_token.decimals()
    pps = lego_ripe.getPricePerShare(mock_savings_green_token, decimals)
    assert pps > 0


#######################################
# 6. Access Control & Edge Cases Tests #
#######################################


def test_ripe_access_check(
    lego_ripe,
    bob_wallet_with_green,
):
    """Test getting access info for the lego"""
    # In the mock, access is always granted
    teller, abi, value = lego_ripe.getAccessForLego(bob_wallet_with_green.address, 0)
    # Since mock returns True for access, should return empty values
    assert teller == ZERO_ADDRESS


def test_ripe_has_capabilities(
    lego_ripe,
):
    """Test that RipeLego advertises correct capabilities"""
    # Should support these ActionTypes (flag enum values are powers of 2)
    assert lego_ripe.hasCapability(2) == True  # EARN_DEPOSIT (2^1)
    assert lego_ripe.hasCapability(4) == True  # EARN_WITHDRAW (2^2)
    assert lego_ripe.hasCapability(128) == True  # ADD_COLLATERAL (2^7)
    assert lego_ripe.hasCapability(256) == True  # REMOVE_COLLATERAL (2^8)
    assert lego_ripe.hasCapability(512) == True  # BORROW (2^9)
    assert lego_ripe.hasCapability(1024) == True  # REPAY_DEBT (2^10)
    assert lego_ripe.hasCapability(2048) == True  # REWARDS (2^11)

    # Should NOT support swap (2^4)
    assert lego_ripe.hasCapability(16) == False  # SWAP


def test_ripe_is_yield_lego(
    lego_ripe,
):
    """Test that RipeLego identifies as a yield lego"""
    assert lego_ripe.isYieldLego() == True


def test_ripe_is_not_dex_lego(
    lego_ripe,
):
    """Test that RipeLego does not identify as a dex lego"""
    assert lego_ripe.isDexLego() == False


def test_ripe_is_not_rebasing(
    lego_ripe,
):
    """Test that SAVINGS_GREEN is not marked as rebasing"""
    assert lego_ripe.isRebasing() == False


def test_ripe_get_registries(
    lego_ripe,
    mock_ripe,
):
    """Test getting the registries used by RipeLego"""
    registries = lego_ripe.getRegistries()
    assert len(registries) == 1
    assert registries[0] == mock_ripe.address


###################################
# TIER 1: Critical Missing Coverage #
###################################


def test_ripe_claim_rewards(
    lego_ripe,
    setup_mock_prices,
    mock_ripe_token,
    bob,
):
    """Test claiming RIPE token rewards from protocol"""
    # Pre balance
    pre_ripe_balance = mock_ripe_token.balanceOf(bob)

    # Claim rewards - RipeLego.claimRewards requires msg.sender == _user
    # So we call it directly as bob, not through the wallet
    ripe_claimed, usd_value = lego_ripe.claimRewards(
        bob,  # _user
        mock_ripe_token,  # rewardToken
        MAX_UINT256,  # rewardAmount (not used in RipeLego, but required param)
        b'\x00' * 32,  # extraData (bytes32)
        sender=bob
    )

    # Post balance
    post_ripe_balance = mock_ripe_token.balanceOf(bob)

    # Verify RIPE tokens were claimed
    assert post_ripe_balance > pre_ripe_balance
    # Verify USD value was calculated
    assert usd_value > 0
    # RipeLego returns 0 for ripe_claimed (returns tuple (0, usd_value))
    assert ripe_claimed == 0


def test_ripe_claim_rewards_from_security_signer(
    lego_ripe,
    setup_mock_prices,
    mock_ripe_token,
    mission_control,
    switchboard_alpha,
    alice,
    bob,
):
    """
    Security signers (e.g. the claimer bot) can claim rewards on behalf
    of a user without having to be a user wallet or earn vault. This enables
    the off-chain cron that daily-claims for user wallets.
    """
    # Grant alice canPerformSecurityAction
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)

    pre = mock_ripe_token.balanceOf(bob)
    ripe_claimed, usd_value = lego_ripe.claimRewards(
        bob,              # _user (beneficiary)
        mock_ripe_token,  # rewardToken
        MAX_UINT256,
        b'\x00' * 32,
        sender=alice,     # caller is the security signer
    )
    assert mock_ripe_token.balanceOf(bob) > pre
    assert usd_value > 0
    assert ripe_claimed == 0


def test_ripe_claim_incentives_from_security_signer(
    lego_ripe,
    setup_mock_prices,
    mock_ripe_token,
    mission_control,
    switchboard_alpha,
    alice,
    bob,
):
    """Same as claimRewards but for the claimIncentives entrypoint."""
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)

    pre = mock_ripe_token.balanceOf(bob)
    ripe_claimed, usd_value = lego_ripe.claimIncentives(
        bob,
        mock_ripe_token,
        MAX_UINT256,
        [],  # proofs
        sender=alice,
    )
    assert mock_ripe_token.balanceOf(bob) > pre
    assert usd_value > 0
    assert ripe_claimed == 0


def test_ripe_borrow_invalid_asset_fails(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    bravo_token,
    lego_book,
    bob,
):
    """Test that borrowing unsupported asset fails"""
    lego_id = lego_book.getRegId(lego_ripe)

    # First add collateral
    bob_wallet_with_green.addCollateral(
        lego_id,
        mock_green_token,
        50_000 * EIGHTEEN_DECIMALS,
        sender=bob
    )

    # Try to borrow unsupported asset - should fail
    with boa.reverts():
        bob_wallet_with_green.borrow(
            lego_id,
            bravo_token,  # Invalid asset
            10_000 * EIGHTEEN_DECIMALS,
            sender=bob
        )


def test_ripe_repay_invalid_asset_fails(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    bravo_token,
    lego_book,
    bob,
):
    """Test that repaying with unsupported asset fails"""
    lego_id = lego_book.getRegId(lego_ripe)

    # First add collateral and borrow
    bob_wallet_with_green.addCollateral(
        lego_id,
        mock_green_token,
        50_000 * EIGHTEEN_DECIMALS,
        sender=bob
    )
    bob_wallet_with_green.borrow(
        lego_id,
        mock_green_token,
        10_000 * EIGHTEEN_DECIMALS,
        sender=bob
    )

    # Try to repay with unsupported asset - should fail
    with boa.reverts():
        bob_wallet_with_green.repayDebt(
            lego_id,
            bravo_token,  # Invalid asset
            5_000 * EIGHTEEN_DECIMALS,
            sender=bob
        )


####################################################
# TIER 2: Underlying Data Function Tests #
####################################################


def test_ripe_get_underlying_balances(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    mock_savings_green_token,
    lego_book,
    bob,
):
    """Test getting both true and safe underlying balances"""
    lego_id = lego_book.getRegId(lego_ripe)

    # First deposit to register the vault
    _, _, vault_tokens_received, _ = bob_wallet_with_green.depositForYield(
        lego_id,
        mock_green_token,
        mock_savings_green_token,
        10_000 * EIGHTEEN_DECIMALS,
        sender=bob
    )

    # Get underlying balances
    true_underlying, safe_underlying = lego_ripe.getUnderlyingBalances(
        mock_savings_green_token,
        vault_tokens_received
    )

    # Both should be greater than 0
    assert true_underlying > 0
    assert safe_underlying > 0
    # Safe should be <= true
    assert safe_underlying <= true_underlying


def test_ripe_get_underlying_data(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    mock_savings_green_token,
    lego_book,
    bob,
):
    """Test getting combined underlying data (asset, amount, usd value)"""
    lego_id = lego_book.getRegId(lego_ripe)

    # First deposit to register the vault
    _, _, vault_tokens_received, _ = bob_wallet_with_green.depositForYield(
        lego_id,
        mock_green_token,
        mock_savings_green_token,
        10_000 * EIGHTEEN_DECIMALS,
        sender=bob
    )

    # Get underlying data
    asset, amount, usd_value = lego_ripe.getUnderlyingData(
        mock_savings_green_token,
        vault_tokens_received,
        ZERO_ADDRESS  # Use default appraiser
    )

    # Verify data
    assert asset == mock_green_token.address
    assert amount > 0
    assert usd_value > 0


def test_ripe_get_usd_value_of_vault_token(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    mock_savings_green_token,
    lego_book,
    bob,
):
    """Test getting USD value of vault tokens"""
    lego_id = lego_book.getRegId(lego_ripe)

    # First deposit to register the vault
    _, _, vault_tokens_received, _ = bob_wallet_with_green.depositForYield(
        lego_id,
        mock_green_token,
        mock_savings_green_token,
        10_000 * EIGHTEEN_DECIMALS,
        sender=bob
    )

    # Get USD value
    usd_value = lego_ripe.getUsdValueOfVaultToken(
        mock_savings_green_token,
        vault_tokens_received,
        ZERO_ADDRESS  # Use default appraiser
    )

    # Should have USD value
    assert usd_value > 0


def test_ripe_total_assets(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    mock_savings_green_token,
    lego_book,
    bob,
):
    """Test querying vault's total assets"""
    lego_id = lego_book.getRegId(lego_ripe)

    # First deposit to register the vault
    bob_wallet_with_green.depositForYield(
        lego_id,
        mock_green_token,
        mock_savings_green_token,
        10_000 * EIGHTEEN_DECIMALS,
        sender=bob
    )

    # Get total assets
    total = lego_ripe.totalAssets(mock_savings_green_token)
    assert total > 0


###################################
# 7. Swap Tokens Tests (via PSM) #
###################################


def test_swap_green_to_usdc_full(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    mock_usdc,
    lego_book,
    bob,
    _test,
):
    """Test swapping all GREEN tokens to USDC via swapTokens"""
    lego_id = lego_book.getRegId(lego_ripe)

    # Pre balances
    pre_green_balance = mock_green_token.balanceOf(bob_wallet_with_green)
    pre_usdc_balance = mock_usdc.balanceOf(bob_wallet_with_green)

    # Create swap instruction
    instruction = (
        lego_id,
        MAX_UINT256,  # amountIn - use all GREEN
        0,  # minAmountOut
        [mock_green_token.address, mock_usdc.address],  # tokenPath
        []  # poolPath (empty for RipeLego)
    )

    # Execute swap
    tokenIn, origAmountIn, lastTokenOut, lastTokenOutAmount, usd_value = bob_wallet_with_green.swapTokens(
        [instruction],
        sender=bob
    )

    # Verify results
    assert origAmountIn > 0
    assert lastTokenOutAmount > 0
    assert tokenIn == mock_green_token.address
    assert lastTokenOut == mock_usdc.address

    # Verify balances - GREEN should be fully swapped
    _test(mock_green_token.balanceOf(bob_wallet_with_green), 0)
    # Expected USDC = GREEN / 10^12 (due to decimal conversion 18->6)
    expected_usdc = pre_green_balance // (10 ** 12)
    _test(mock_usdc.balanceOf(bob_wallet_with_green), pre_usdc_balance + expected_usdc)

    # Verify no leftover in lego
    assert mock_green_token.balanceOf(lego_ripe) == 0
    assert mock_usdc.balanceOf(lego_ripe) == 0


def test_swap_usdc_to_green_partial(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_usdc,
    mock_green_token,
    mock_usdc,
    lego_book,
    bob,
    _test,
):
    """Test swapping partial USDC to GREEN"""
    lego_id = lego_book.getRegId(lego_ripe)

    # Pre balances
    pre_usdc_balance = mock_usdc.balanceOf(bob_wallet_with_usdc)
    pre_green_balance = mock_green_token.balanceOf(bob_wallet_with_usdc)

    swap_amount = 500 * (10 ** 6)  # Swap 500 USDC

    instruction = (
        lego_id,
        swap_amount,
        0,
        [mock_usdc.address, mock_green_token.address],
        []
    )

    tokenIn, origAmountIn, lastTokenOut, lastTokenOutAmount, usd_value = bob_wallet_with_usdc.swapTokens(
        [instruction],
        sender=bob
    )

    # Verify
    _test(origAmountIn, swap_amount)
    expected_green = swap_amount * (10 ** 12)  # USDC 6 decimals -> GREEN 18 decimals
    _test(lastTokenOutAmount, expected_green)
    _test(mock_usdc.balanceOf(bob_wallet_with_usdc), pre_usdc_balance - swap_amount)
    _test(mock_green_token.balanceOf(bob_wallet_with_usdc), pre_green_balance + expected_green)


def test_swap_zero_amount_fails(
    lego_ripe,
    bob_wallet_with_green,
    mock_green_token,
    mock_usdc,
    lego_book,
    bob,
):
    """Test that swapping 0 amount fails"""
    lego_id = lego_book.getRegId(lego_ripe)

    instruction = (
        lego_id,
        0,  # Zero amount
        0,
        [mock_green_token.address, mock_usdc.address],
        []
    )

    with boa.reverts():  # Should revert with "dev: nothing to transfer"
        bob_wallet_with_green.swapTokens([instruction], sender=bob)


def test_swap_min_amount_out_not_met(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    mock_usdc,
    lego_book,
    bob,
):
    """Test that swap fails when min amount out is not met"""
    lego_id = lego_book.getRegId(lego_ripe)

    swap_amount = 1_000 * EIGHTEEN_DECIMALS
    impossible_min_out = 10_000 * (10 ** 6)  # Expecting way more USDC than possible

    instruction = (
        lego_id,
        swap_amount,
        impossible_min_out,
        [mock_green_token.address, mock_usdc.address],
        []
    )

    with boa.reverts():  # Should revert with "dev: min amount out not met"
        bob_wallet_with_green.swapTokens([instruction], sender=bob)


def test_swap_same_token_fails(
    lego_ripe,
    bob_wallet_with_green,
    mock_green_token,
    lego_book,
    bob,
):
    """Test that swapping same token fails"""
    lego_id = lego_book.getRegId(lego_ripe)

    instruction = (
        lego_id,
        1_000 * EIGHTEEN_DECIMALS,
        0,
        [mock_green_token.address, mock_green_token.address],  # Same token!
        []
    )

    with boa.reverts():  # Should revert with "dev: same token"
        bob_wallet_with_green.swapTokens([instruction], sender=bob)


def test_swap_invalid_path_length_fails(
    lego_ripe,
    bob_wallet_with_green,
    mock_green_token,
    mock_usdc,
    mock_ripe_token,
    lego_book,
    bob,
):
    """Test that path with != 2 tokens fails"""
    lego_id = lego_book.getRegId(lego_ripe)

    # Try 3-token path
    instruction = (
        lego_id,
        1_000 * EIGHTEEN_DECIMALS,
        0,
        [mock_green_token.address, mock_usdc.address, mock_ripe_token.address],
        []
    )

    with boa.reverts():  # Should revert with "dev: invalid token path"
        bob_wallet_with_green.swapTokens([instruction], sender=bob)


def test_swap_unsupported_token_fails(
    lego_ripe,
    bob_wallet_with_green,
    mock_green_token,
    bravo_token,
    lego_book,
    bob,
):
    """Test that swapping unsupported tokens fails"""
    lego_id = lego_book.getRegId(lego_ripe)

    instruction = (
        lego_id,
        1_000 * EIGHTEEN_DECIMALS,
        0,
        [mock_green_token.address, bravo_token.address],
        []
    )

    with boa.reverts():  # Should revert with "dev: invalid tokens"
        bob_wallet_with_green.swapTokens([instruction], sender=bob)


def test_swap_green_to_savings_green_fails(
    lego_ripe,
    bob_wallet_with_green,
    mock_green_token,
    mock_savings_green_token,
    lego_book,
    bob,
):
    """Test that swapping GREEN to SAVINGS_GREEN fails (must use depositForYield)"""
    lego_id = lego_book.getRegId(lego_ripe)

    instruction = (
        lego_id,
        1_000 * EIGHTEEN_DECIMALS,
        0,
        [mock_green_token.address, mock_savings_green_token.address],
        []
    )

    with boa.reverts():  # Should revert - cannot swap into/out of savings green
        bob_wallet_with_green.swapTokens([instruction], sender=bob)


def test_swap_without_permission_fails(
    lego_ripe,
    bob_wallet_with_green,
    mock_green_token,
    mock_usdc,
    lego_book,
    alice,
):
    """Test that swap fails without proper permissions"""
    lego_id = lego_book.getRegId(lego_ripe)

    instruction = (
        lego_id,
        1_000 * EIGHTEEN_DECIMALS,
        0,
        [mock_green_token.address, mock_usdc.address],
        []
    )

    calldata = bob_wallet_with_green.swapTokens.prepare_calldata([instruction])
    result = boa.env.execute_code(
        to_address=bob_wallet_with_green.address,
        sender=alice,
        data=calldata,
    )
    assert result.is_error


def test_swap_usd_value_calculation(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    mock_usdc,
    lego_book,
    bob,
    _test,
):
    """Test that USD value is correctly calculated"""
    lego_id = lego_book.getRegId(lego_ripe)

    swap_amount = 1_000 * EIGHTEEN_DECIMALS  # 1000 GREEN

    instruction = (
        lego_id,
        swap_amount,
        0,
        [mock_green_token.address, mock_usdc.address],
        []
    )

    tokenIn, origAmountIn, lastTokenOut, lastTokenOutAmount, usd_value = bob_wallet_with_green.swapTokens(
        [instruction],
        sender=bob
    )

    # With price of 1 GREEN = $1, USD value should be ~1000
    expected_usd_value = 1_000 * EIGHTEEN_DECIMALS
    _test(usd_value, expected_usd_value)


def test_swap_return_values(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    mock_usdc,
    lego_book,
    bob,
    _test,
):
    """Test that swap returns correct values"""
    lego_id = lego_book.getRegId(lego_ripe)

    swap_amount = 1_000 * EIGHTEEN_DECIMALS

    instruction = (
        lego_id,
        swap_amount,
        0,
        [mock_green_token.address, mock_usdc.address],
        []
    )

    # Execute swap and verify return values
    tokenIn, origAmountIn, lastTokenOut, lastTokenOutAmount, usd_value = bob_wallet_with_green.swapTokens(
        [instruction],
        sender=bob
    )

    # Verify return values are correct
    assert tokenIn == mock_green_token.address
    assert lastTokenOut == mock_usdc.address
    _test(origAmountIn, swap_amount)
    # Expected USDC = GREEN / 10^12 (decimal conversion)
    expected_usdc = swap_amount // (10 ** 12)
    _test(lastTokenOutAmount, expected_usdc)
    assert usd_value > 0


def test_swap_no_leftover_balance(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    mock_usdc,
    lego_book,
    bob,
):
    """Test that no tokens are left stuck in the lego contract after swap"""
    lego_id = lego_book.getRegId(lego_ripe)

    swap_amount = 5_000 * EIGHTEEN_DECIMALS

    instruction = (
        lego_id,
        swap_amount,
        0,
        [mock_green_token.address, mock_usdc.address],
        []
    )

    # Pre lego balances
    pre_lego_green = mock_green_token.balanceOf(lego_ripe)
    pre_lego_usdc = mock_usdc.balanceOf(lego_ripe)

    bob_wallet_with_green.swapTokens([instruction], sender=bob)

    # Post lego balances - should be unchanged (no stuck tokens)
    post_lego_green = mock_green_token.balanceOf(lego_ripe)
    post_lego_usdc = mock_usdc.balanceOf(lego_ripe)

    assert post_lego_green == pre_lego_green
    assert post_lego_usdc == pre_lego_usdc
