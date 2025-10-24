import pytest
import boa

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


def test_ripe_get_collateral_balance(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    lego_book,
    bob,
):
    """Test getting collateral balance from Ripe Protocol"""
    lego_id = lego_book.getRegId(lego_ripe)

    # Add some collateral
    collateral_amount = 7_500 * EIGHTEEN_DECIMALS
    bob_wallet_with_green.addCollateral(
        lego_id,
        mock_green_token,
        collateral_amount,
        sender=bob
    )

    # Query collateral balance
    balance = lego_ripe.getCollateralBalance(bob_wallet_with_green.address, mock_green_token)
    assert balance >= collateral_amount


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


def test_ripe_get_user_debt_amount(
    lego_ripe,
    setup_mock_prices,
    bob_wallet_with_green,
    mock_green_token,
    lego_book,
    bob,
):
    """Test getting user debt amount"""
    lego_id = lego_book.getRegId(lego_ripe)

    # Add collateral and borrow
    bob_wallet_with_green.addCollateral(
        lego_id,
        mock_green_token,
        50_000 * EIGHTEEN_DECIMALS,
        sender=bob
    )
    borrow_amount = 15_000 * EIGHTEEN_DECIMALS
    bob_wallet_with_green.borrow(
        lego_id,
        mock_green_token,
        borrow_amount,
        sender=bob
    )

    # Query debt amount
    debt = lego_ripe.getUserDebtAmount(bob_wallet_with_green.address)
    assert debt >= borrow_amount


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


def test_ripe_is_supported_asset(
    lego_ripe,
    mock_green_token,
):
    """Test checking if an asset is supported by Ripe"""
    # In the mock, all assets return True
    is_supported = lego_ripe.isSupportedRipeAsset(mock_green_token)
    assert is_supported == True


def test_ripe_get_usd_value(
    lego_ripe,
    setup_mock_prices,
    mock_green_token,
):
    """Test getting USD value of an asset amount"""
    amount = 100 * EIGHTEEN_DECIMALS
    usd_value = lego_ripe.getUsdValue(mock_green_token, amount)
    # With price at $1, 100 tokens = $100
    assert usd_value == 100 * EIGHTEEN_DECIMALS


def test_ripe_get_asset_amount(
    lego_ripe,
    setup_mock_prices,
    mock_green_token,
):
    """Test getting asset amount from USD value"""
    usd_value = 100 * EIGHTEEN_DECIMALS  # $100
    asset_amount = lego_ripe.getAssetAmount(mock_green_token, usd_value)
    # With price at $1, $100 = 100 tokens
    assert asset_amount == 100 * EIGHTEEN_DECIMALS


def test_ripe_green_token(
    lego_ripe,
    mock_green_token,
):
    """Test getting the GREEN token address"""
    green = lego_ripe.greenToken()
    assert green == mock_green_token.address


def test_ripe_savings_green(
    lego_ripe,
    mock_savings_green_token,
):
    """Test getting the SAVINGS_GREEN token address"""
    savings = lego_ripe.savingsGreen()
    assert savings == mock_savings_green_token.address


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
