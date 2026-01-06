"""
Tests for netUserShares tracking in USDC leverage vaults.

These tests verify that netUserShares correctly tracks user deposits/withdrawals
and that convertToAssets(netUserShares) reflects the true value including interest.

For USDC vaults (where collateralToken == leverageToken), netUserShares is used
instead of collateral balance to determine user capital for max borrow calculations.
"""

import pytest

from constants import MAX_UINT256, EIGHTEEN_DECIMALS

# Decimal constants
SIX_DECIMALS = 10 ** 6


#################
# Fixtures #
#################


@pytest.fixture(scope="function")
def usdc_vault(undy_levg_vault_usdc, vault_registry, switchboard_alpha, mock_ripe):
    """Fresh USDC vault setup for each test (no initial deposit)"""
    vault = undy_levg_vault_usdc

    vault_registry.setCanDeposit(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setCanWithdraw(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setShouldAutoDeposit(vault.address, False, sender=switchboard_alpha.address)

    mock_ripe.setMaxBorrowAmount(vault.address, MAX_UINT256)

    return vault


###################################
# Priority 1 - Critical Tests #
###################################


def test_net_user_shares_increases_on_deposit(
    setup_prices,
    usdc_vault,
    mock_usdc,
    starter_agent,
    governance,
):
    """Test that netUserShares increases by minted shares on deposit"""
    vault = usdc_vault

    # Initial state
    assert vault.netUserShares() == 0
    assert vault.totalSupply() == 0

    # Deposit 50k USDC
    deposit_amount = 50_000 * SIX_DECIMALS
    mock_usdc.mint(starter_agent.address, deposit_amount, sender=governance.address)
    mock_usdc.approve(vault.address, deposit_amount, sender=starter_agent.address)

    shares_minted = vault.deposit(deposit_amount, starter_agent.address, sender=starter_agent.address)

    # Verify netUserShares == minted shares
    assert vault.netUserShares() == shares_minted
    assert vault.netUserShares() == vault.balanceOf(starter_agent.address)
    assert vault.netUserShares() == vault.totalSupply()

    # Verify convertToAssets returns deposit amount (no appreciation yet)
    assert vault.convertToAssets(vault.netUserShares()) == deposit_amount


def test_net_user_shares_decreases_on_withdrawal(
    setup_prices,
    usdc_vault,
    mock_usdc,
    starter_agent,
    governance,
):
    """Test that netUserShares decreases by burned shares on withdrawal"""
    vault = usdc_vault

    # Setup: deposit 50k USDC
    deposit_amount = 50_000 * SIX_DECIMALS
    mock_usdc.mint(starter_agent.address, deposit_amount, sender=governance.address)
    mock_usdc.approve(vault.address, deposit_amount, sender=starter_agent.address)
    initial_shares = vault.deposit(deposit_amount, starter_agent.address, sender=starter_agent.address)

    initial_net_shares = vault.netUserShares()
    assert initial_net_shares == initial_shares

    # Withdraw 20k USDC worth
    withdraw_amount = 20_000 * SIX_DECIMALS
    shares_to_burn = vault.convertToShares(withdraw_amount)

    vault.withdraw(withdraw_amount, starter_agent.address, starter_agent.address, sender=starter_agent.address)

    # Verify netUserShares decreased by burned shares
    expected_remaining = initial_net_shares - shares_to_burn
    assert vault.netUserShares() == expected_remaining
    assert vault.netUserShares() == vault.balanceOf(starter_agent.address)

    # Remaining value should be ~30k
    remaining_value = vault.convertToAssets(vault.netUserShares())
    assert remaining_value >= 29_900 * SIX_DECIMALS  # Within 0.3% tolerance
    assert remaining_value <= 30_100 * SIX_DECIMALS


def test_net_user_shares_with_interest_accrual(
    setup_prices,
    usdc_vault,
    mock_usdc,
    starter_agent,
    governance,
):
    """Test that convertToAssets(netUserShares) increases when vault accrues interest"""
    vault = usdc_vault

    # Deposit 50k USDC
    deposit_amount = 50_000 * SIX_DECIMALS
    mock_usdc.mint(starter_agent.address, deposit_amount, sender=governance.address)
    mock_usdc.approve(vault.address, deposit_amount, sender=starter_agent.address)
    vault.deposit(deposit_amount, starter_agent.address, sender=starter_agent.address)

    # Record initial state
    initial_shares = vault.netUserShares()
    initial_value = vault.convertToAssets(initial_shares)
    assert initial_value == deposit_amount

    # Simulate 10% interest accrual by minting USDC directly to the vault
    # This increases the underlying value without changing shares
    interest_amount = 5_000 * SIX_DECIMALS  # 10% of 50k
    mock_usdc.mint(vault.address, interest_amount, sender=governance.address)

    # netUserShares should be unchanged
    assert vault.netUserShares() == initial_shares

    # But convertToAssets should reflect the increased value
    new_value = vault.convertToAssets(vault.netUserShares())
    assert new_value > initial_value
    assert new_value >= deposit_amount + interest_amount - (100 * SIX_DECIMALS)  # Within $100 tolerance

    # User can withdraw more than they deposited
    vault.redeem(initial_shares, starter_agent.address, starter_agent.address, sender=starter_agent.address)
    final_balance = mock_usdc.balanceOf(starter_agent.address)
    assert final_balance >= deposit_amount + interest_amount - (100 * SIX_DECIMALS)


def test_net_user_shares_multi_user_at_different_prices(
    setup_prices,
    usdc_vault,
    mock_usdc,
    alice,
    bob,
    governance,
):
    """Test fair share distribution when users deposit at different share prices"""
    vault = usdc_vault

    # Alice deposits 50k USDC at 1:1 (first depositor)
    alice_deposit = 50_000 * SIX_DECIMALS
    mock_usdc.mint(alice, alice_deposit, sender=governance.address)
    mock_usdc.approve(vault.address, alice_deposit, sender=alice)
    alice_shares = vault.deposit(alice_deposit, alice, sender=alice)

    initial_net_shares = vault.netUserShares()
    assert initial_net_shares == alice_shares
    assert alice_shares == alice_deposit  # 1:1 for first depositor

    # Vault appreciates 20% (interest accrues) - mint directly to vault
    appreciation = 10_000 * SIX_DECIMALS  # 20% of 50k
    mock_usdc.mint(vault.address, appreciation, sender=governance.address)

    # Alice's shares now worth 60k (50k deposit + 10k appreciation)
    alice_value = vault.convertToAssets(alice_shares)
    assert alice_value >= 59_000 * SIX_DECIMALS
    assert alice_value <= 61_000 * SIX_DECIMALS

    # Share price is now 1.2 USDC per share (60k assets / 50k shares)
    # Bob deposits same dollar amount as Alice originally did (50k)
    # At 1.2 price, he gets fewer shares
    bob_deposit = 50_000 * SIX_DECIMALS
    mock_usdc.mint(bob, bob_deposit, sender=governance.address)
    mock_usdc.approve(vault.address, bob_deposit, sender=bob)
    bob_shares = vault.deposit(bob_deposit, bob, sender=bob)

    # Bob should get fewer shares than Alice (since share price > 1)
    # Bob's shares = 50k * 50k / 60k = ~41.67k shares
    assert bob_shares < alice_shares
    expected_bob_shares = bob_deposit * alice_shares // (alice_deposit + appreciation)
    assert bob_shares >= expected_bob_shares - 1000  # Tolerance for rounding
    assert bob_shares <= expected_bob_shares + 1000

    # netUserShares should be updated correctly
    expected_net_shares = alice_shares + bob_shares
    assert vault.netUserShares() == expected_net_shares

    # Both users redeem - should get fair value
    alice_redeemed = vault.redeem(alice_shares, alice, alice, sender=alice)
    bob_redeemed = vault.redeem(bob_shares, bob, bob, sender=bob)

    # Alice should get her deposit + appreciation (~60k)
    assert alice_redeemed >= 59_000 * SIX_DECIMALS

    # Bob should get approximately what he deposited (no appreciation for him)
    assert bob_redeemed >= 49_000 * SIX_DECIMALS
    assert bob_redeemed <= 51_000 * SIX_DECIMALS


def test_net_user_shares_full_withdrawal_to_zero(
    setup_prices,
    usdc_vault,
    mock_usdc,
    starter_agent,
    governance,
):
    """Test that full withdrawal results in netUserShares == 0 and new deposits work"""
    vault = usdc_vault

    # Deposit
    deposit_amount = 50_000 * SIX_DECIMALS
    mock_usdc.mint(starter_agent.address, deposit_amount, sender=governance.address)
    mock_usdc.approve(vault.address, deposit_amount, sender=starter_agent.address)
    shares = vault.deposit(deposit_amount, starter_agent.address, sender=starter_agent.address)

    assert vault.netUserShares() == shares
    assert vault.totalSupply() == shares

    # Redeem all shares
    vault.redeem(shares, starter_agent.address, starter_agent.address, sender=starter_agent.address)

    # Verify zero state
    assert vault.netUserShares() == 0
    assert vault.totalSupply() == 0
    assert vault.balanceOf(starter_agent.address) == 0

    # New deposit should work correctly from zero state
    new_deposit = 10_000 * SIX_DECIMALS
    mock_usdc.mint(starter_agent.address, new_deposit, sender=governance.address)
    mock_usdc.approve(vault.address, new_deposit, sender=starter_agent.address)
    new_shares = vault.deposit(new_deposit, starter_agent.address, sender=starter_agent.address)

    # Should get 1:1 shares again (fresh start)
    assert vault.netUserShares() == new_shares
    assert vault.convertToAssets(new_shares) == new_deposit


def test_max_borrow_uses_converted_shares_usdc_vault(
    setup_prices,
    usdc_vault,
    levg_vault_helper,
    mock_usdc,
    mock_ripe,
    starter_agent,
    switchboard_alpha,
    governance,
):
    """Test that getMaxBorrowAmount uses appreciated value of netUserShares"""
    vault = usdc_vault

    # Deposit 50k USDC
    deposit_amount = 50_000 * SIX_DECIMALS
    mock_usdc.mint(starter_agent.address, deposit_amount, sender=governance.address)
    mock_usdc.approve(vault.address, deposit_amount, sender=starter_agent.address)
    vault.deposit(deposit_amount, starter_agent.address, sender=starter_agent.address)

    # Set 70% max debt ratio
    vault.setMaxDebtRatio(70_00, sender=switchboard_alpha.address)

    # Initial max borrow: 70% of 50k = 35k GREEN
    initial_max_borrow = levg_vault_helper.getMaxBorrowAmount(
        vault.address,
        mock_usdc.address,
        vault.collateralAsset()[0],
        vault.collateralAsset()[1],
        vault.netUserShares(),
        vault.maxDebtRatio(),
    )
    expected_initial = 35_000 * EIGHTEEN_DECIMALS
    assert initial_max_borrow == expected_initial

    # Simulate 20% appreciation - mint directly to vault
    appreciation = 10_000 * SIX_DECIMALS
    mock_usdc.mint(vault.address, appreciation, sender=governance.address)

    # New max borrow should be 70% of 60k = 42k GREEN
    new_max_borrow = levg_vault_helper.getMaxBorrowAmount(
        vault.address,
        mock_usdc.address,
        vault.collateralAsset()[0],
        vault.collateralAsset()[1],
        vault.netUserShares(),
        vault.maxDebtRatio(),
    )
    expected_new = 42_000 * EIGHTEEN_DECIMALS
    # Allow some tolerance for rounding
    assert new_max_borrow >= expected_new - (100 * EIGHTEEN_DECIMALS)
    assert new_max_borrow <= expected_new + (100 * EIGHTEEN_DECIMALS)

    # Verify it increased
    assert new_max_borrow > initial_max_borrow


#####################################
# Priority 2 - Important Edge Cases #
#####################################


def test_net_user_shares_with_max_leverage_300_percent(
    setup_prices,
    usdc_vault,
    levg_vault_helper,
    mock_usdc,
    mock_ripe,
    starter_agent,
    switchboard_alpha,
    governance,
):
    """Test netUserShares tracking with extreme leverage (300% debt ratio)"""
    vault = usdc_vault

    # Deposit 50k USDC
    deposit_amount = 50_000 * SIX_DECIMALS
    mock_usdc.mint(starter_agent.address, deposit_amount, sender=governance.address)
    mock_usdc.approve(vault.address, deposit_amount, sender=starter_agent.address)
    vault.deposit(deposit_amount, starter_agent.address, sender=starter_agent.address)

    # Set 300% max debt ratio (30000 basis points)
    vault.setMaxDebtRatio(300_00, sender=switchboard_alpha.address)

    # Max borrow should be 300% of 50k = 150k GREEN
    max_borrow = levg_vault_helper.getMaxBorrowAmount(
        vault.address,
        mock_usdc.address,
        vault.collateralAsset()[0],
        vault.collateralAsset()[1],
        vault.netUserShares(),
        vault.maxDebtRatio(),
    )

    expected_max = 150_000 * EIGHTEEN_DECIMALS
    assert max_borrow == expected_max

    # netUserShares should remain unchanged regardless of debt ratio setting
    assert vault.convertToAssets(vault.netUserShares()) == deposit_amount


def test_net_user_shares_partial_withdrawal_precision(
    setup_prices,
    usdc_vault,
    mock_usdc,
    starter_agent,
    governance,
):
    """Test precision of netUserShares with fractional withdrawals"""
    vault = usdc_vault

    # Deposit 100k USDC
    deposit_amount = 100_000 * SIX_DECIMALS
    mock_usdc.mint(starter_agent.address, deposit_amount, sender=governance.address)
    mock_usdc.approve(vault.address, deposit_amount, sender=starter_agent.address)
    initial_shares = vault.deposit(deposit_amount, starter_agent.address, sender=starter_agent.address)

    # Withdraw exactly 1/3 (33.333...%)
    withdraw_shares = initial_shares // 3
    vault.redeem(withdraw_shares, starter_agent.address, starter_agent.address, sender=starter_agent.address)

    # Remaining should be 2/3 of initial
    expected_remaining = initial_shares - withdraw_shares
    assert vault.netUserShares() == expected_remaining

    # Value should be approximately 66.67k
    remaining_value = vault.convertToAssets(vault.netUserShares())
    assert remaining_value >= 66_600 * SIX_DECIMALS
    assert remaining_value <= 66_700 * SIX_DECIMALS

    # Withdraw remaining - should leave no dust
    final_shares = vault.balanceOf(starter_agent.address)
    vault.redeem(final_shares, starter_agent.address, starter_agent.address, sender=starter_agent.address)

    assert vault.netUserShares() == 0
    assert vault.totalSupply() == 0


def test_net_user_shares_unchanged_during_debt_operations(
    setup_prices,
    usdc_vault,
    mock_usdc,
    mock_ripe,
    starter_agent,
    switchboard_alpha,
    governance,
):
    """Test that netUserShares is not affected by borrowing/repaying debt"""
    vault = usdc_vault

    # Deposit 50k USDC
    deposit_amount = 50_000 * SIX_DECIMALS
    mock_usdc.mint(starter_agent.address, deposit_amount, sender=governance.address)
    mock_usdc.approve(vault.address, deposit_amount, sender=starter_agent.address)
    vault.deposit(deposit_amount, starter_agent.address, sender=starter_agent.address)

    initial_net_shares = vault.netUserShares()

    # Simulate debt being added (via mock)
    debt_amount = 20_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(vault.address, debt_amount)

    # netUserShares should be unchanged
    assert vault.netUserShares() == initial_net_shares

    # Simulate debt being repaid
    mock_ripe.setUserDebt(vault.address, 0)

    # netUserShares still unchanged
    assert vault.netUserShares() == initial_net_shares

    # User can still withdraw full amount
    shares = vault.balanceOf(starter_agent.address)
    vault.redeem(shares, starter_agent.address, starter_agent.address, sender=starter_agent.address)

    assert mock_usdc.balanceOf(starter_agent.address) == deposit_amount


def test_net_user_shares_invariant_equals_balance(
    setup_prices,
    usdc_vault,
    mock_usdc,
    starter_agent,
    governance,
):
    """Test invariant: for single user vault, netUserShares == balanceOf(user) == totalSupply"""
    vault = usdc_vault

    # Multiple deposit/withdraw cycles
    for i in range(5):
        deposit_amount = (10_000 + i * 5_000) * SIX_DECIMALS
        mock_usdc.mint(starter_agent.address, deposit_amount, sender=governance.address)
        mock_usdc.approve(vault.address, deposit_amount, sender=starter_agent.address)
        vault.deposit(deposit_amount, starter_agent.address, sender=starter_agent.address)

        # Check invariants after each deposit
        assert vault.netUserShares() == vault.balanceOf(starter_agent.address)
        assert vault.netUserShares() == vault.totalSupply()

        # Partial withdrawal
        if i > 0:
            withdraw_shares = vault.balanceOf(starter_agent.address) // 4
            vault.redeem(withdraw_shares, starter_agent.address, starter_agent.address, sender=starter_agent.address)

            # Check invariants after withdrawal
            assert vault.netUserShares() == vault.balanceOf(starter_agent.address)
            assert vault.netUserShares() == vault.totalSupply()


#############################
# Priority 3 - Stress Tests #
#############################


def test_net_user_shares_sequential_deposits_withdrawals(
    setup_prices,
    usdc_vault,
    mock_usdc,
    starter_agent,
    governance,
):
    """Stress test: 20 cycles of deposit/withdraw with no precision loss"""
    vault = usdc_vault

    cumulative_deposits = 0
    cumulative_withdrawals = 0

    for i in range(20):
        # Deposit 10k
        deposit_amount = 10_000 * SIX_DECIMALS
        mock_usdc.mint(starter_agent.address, deposit_amount, sender=governance.address)
        mock_usdc.approve(vault.address, deposit_amount, sender=starter_agent.address)
        vault.deposit(deposit_amount, starter_agent.address, sender=starter_agent.address)
        cumulative_deposits += deposit_amount

        # Withdraw 5k (50% of deposit)
        if vault.balanceOf(starter_agent.address) > 0:
            withdraw_amount = 5_000 * SIX_DECIMALS
            vault.withdraw(withdraw_amount, starter_agent.address, starter_agent.address, sender=starter_agent.address)
            cumulative_withdrawals += withdraw_amount

    # Expected net: 20 * (10k - 5k) = 100k USDC worth of shares
    expected_value = cumulative_deposits - cumulative_withdrawals
    actual_value = vault.convertToAssets(vault.netUserShares())

    # Allow 0.1% tolerance for rounding over many operations
    tolerance = expected_value // 1000
    assert actual_value >= expected_value - tolerance
    assert actual_value <= expected_value + tolerance

    # Invariants still hold
    assert vault.netUserShares() == vault.balanceOf(starter_agent.address)
    assert vault.netUserShares() == vault.totalSupply()


def test_debt_to_deposit_ratio_uses_net_user_shares(
    setup_prices,
    usdc_vault,
    levg_vault_tools,
    mock_usdc,
    mock_ripe,
    starter_agent,
    governance,
):
    """Test that getDebtToDepositRatio uses netUserShares for USDC vaults"""
    vault = usdc_vault

    # Deposit 50k USDC
    deposit_amount = 50_000 * SIX_DECIMALS
    mock_usdc.mint(starter_agent.address, deposit_amount, sender=governance.address)
    mock_usdc.approve(vault.address, deposit_amount, sender=starter_agent.address)
    vault.deposit(deposit_amount, starter_agent.address, sender=starter_agent.address)

    # Set 50% debt (25k GREEN = 25k USD)
    debt_amount = 25_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(vault.address, debt_amount)

    # Debt to deposit ratio should be 50% (5000 basis points)
    ratio = levg_vault_tools.getDebtToDepositRatio(
        vault.address,
        mock_usdc.address,
        vault.collateralAsset()[0],
        vault.collateralAsset()[1],
        vault.leverageAsset()[0],
        vault.netUserShares(),
    )

    # 25k debt / 50k deposit = 50% = 5000 basis points
    expected_ratio = 50_00
    assert ratio >= expected_ratio - 10  # Within 0.1% tolerance
    assert ratio <= expected_ratio + 10

    # Simulate 20% appreciation - ratio should decrease - mint directly to vault
    appreciation = 10_000 * SIX_DECIMALS
    mock_usdc.mint(vault.address, appreciation, sender=governance.address)

    new_ratio = levg_vault_tools.getDebtToDepositRatio(
        vault.address,
        mock_usdc.address,
        vault.collateralAsset()[0],
        vault.collateralAsset()[1],
        vault.leverageAsset()[0],
        vault.netUserShares(),
    )

    # 25k debt / 60k deposit = 41.67% = 4167 basis points
    expected_new_ratio = 41_67
    assert new_ratio >= expected_new_ratio - 50  # Within 0.5% tolerance
    assert new_ratio <= expected_new_ratio + 50

    # Ratio should have decreased (more assets backing the debt)
    assert new_ratio < ratio
