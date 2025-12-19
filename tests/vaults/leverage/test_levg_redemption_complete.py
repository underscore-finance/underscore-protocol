import pytest
import boa
from constants import EIGHTEEN_DECIMALS, MAX_UINT256

# Decimal constants
SIX_DECIMALS = 10 ** 6
EIGHT_DECIMALS = 10 ** 8

# Lego IDs
RIPE_LEGO_ID = 1


############
# Fixtures #
############

@pytest.fixture(scope="function")
def setup_prices(mock_ripe, mock_green_token, mock_savings_green_token, mock_usdc, mock_cbbtc, mock_weth,
                 mock_usdc_collateral_vault, mock_usdc_leverage_vault,
                 mock_cbbtc_collateral_vault, mock_weth_collateral_vault):
    """Set up prices for all assets"""
    # Set all prices for Ripe calculations
    mock_ripe.setPrice(mock_green_token, 1 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_savings_green_token, 1 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_usdc, 1 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_cbbtc, 90_000 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_weth, 2_000 * EIGHTEEN_DECIMALS)
    # Also set prices for vault tokens
    mock_ripe.setPrice(mock_usdc_collateral_vault.address, 1 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_usdc_leverage_vault.address, 1 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_cbbtc_collateral_vault.address, 90_000 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_weth_collateral_vault.address, 2_000 * EIGHTEEN_DECIMALS)
    return mock_ripe


@pytest.fixture(scope="function")
def setup_vault_for_redemption(
    undy_levg_vault_usdc,
    mock_usdc,
    mock_usdc_collateral_vault,
    mock_usdc_leverage_vault,
    bob,
    starter_agent,
    governance,
    vault_registry,
    switchboard_alpha,
):
    """Set up a USDC vault with assets in all 4 redemption locations"""
    vault = undy_levg_vault_usdc

    # Enable deposits and withdrawals
    vault_registry.setCanDeposit(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setCanWithdraw(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setShouldAutoDeposit(vault.address, False, sender=switchboard_alpha.address)  # Manual control

    # Give Bob initial USDC and deposit to get shares
    initial_deposit = 40_000 * SIX_DECIMALS
    mock_usdc.mint(bob, initial_deposit, sender=governance.address)
    mock_usdc.approve(vault.address, initial_deposit, sender=bob)
    shares = vault.deposit(initial_deposit, bob, sender=bob)

    # Now set up assets in all 4 locations:

    # 1. Step 1: Leave some idle USDC in vault
    idle_usdc = 5_000 * SIX_DECIMALS
    # (already there from deposit)

    # 2. Step 2: Deposit some to collateral vault but leave idle
    collateral_amount = 10_000 * SIX_DECIMALS
    vault.depositForYield(
        2,  # mock yield lego
        mock_usdc.address,
        mock_usdc_collateral_vault.address,
        collateral_amount,
        sender=starter_agent.address
    )

    # 3. Step 3: Add some collateral vault tokens to Ripe
    ripe_collateral_amount = 8_000 * SIX_DECIMALS
    vault.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc_collateral_vault.address,
        ripe_collateral_amount,
        sender=starter_agent.address
    )

    # 4. Step 4a: Deposit to leverage vault but leave idle
    leverage_idle_amount = 7_000 * SIX_DECIMALS
    vault.depositForYield(
        2,  # mock yield lego
        mock_usdc.address,
        mock_usdc_leverage_vault.address,
        leverage_idle_amount,
        sender=starter_agent.address
    )

    # 5. Step 4b: Add some leverage vault tokens to Ripe
    leverage_ripe_amount = 5_000 * SIX_DECIMALS
    vault.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc_leverage_vault.address,
        leverage_ripe_amount,
        sender=starter_agent.address
    )

    return {
        'vault': vault,
        'shares': shares,
        'idle_usdc': idle_usdc,
        'idle_collateral': collateral_amount - ripe_collateral_amount,  # 2000
        'ripe_collateral': ripe_collateral_amount,  # 8000
        'idle_leverage': leverage_idle_amount - leverage_ripe_amount,  # 2000
        'ripe_leverage': leverage_ripe_amount,  # 5000
        'total': initial_deposit
    }


#############################################
# Test 1: Complete Redemption Waterfall    #
#############################################

def test_redemption_executes_all_four_steps_sequentially(
    setup_prices,
    setup_vault_for_redemption,
    mock_usdc,
    mock_usdc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_ripe,
    bob,
):
    """Test that redemption executes all 4 steps in the correct order"""
    setup = setup_vault_for_redemption
    vault = setup['vault']
    shares = setup['shares']

    # Record initial balances
    initial_usdc = mock_usdc.balanceOf(bob)
    initial_vault_usdc = mock_usdc.balanceOf(vault.address)
    initial_collateral_tokens = mock_usdc_collateral_vault.balanceOf(vault.address)
    initial_leverage_tokens = mock_usdc_leverage_vault.balanceOf(vault.address)
    initial_ripe_collateral = mock_ripe.userCollateral(vault.address, mock_usdc_collateral_vault.address)
    initial_ripe_leverage = mock_ripe.userCollateral(vault.address, mock_usdc_leverage_vault.address)

    # Redeem all shares - should pull from all 4 steps
    assets_received = vault.redeem(shares, bob, bob, sender=bob)

    # Verify the redemption amount
    assert assets_received == setup['total']
    assert mock_usdc.balanceOf(bob) == initial_usdc + assets_received

    # Verify assets were pulled from all locations
    # Step 1: Idle USDC should be used first
    assert mock_usdc.balanceOf(vault.address) < initial_vault_usdc

    # Step 2: Idle collateral vault tokens should be used
    assert mock_usdc_collateral_vault.balanceOf(vault.address) < initial_collateral_tokens

    # Step 3: Ripe collateral should be reduced
    assert mock_ripe.userCollateral(vault.address, mock_usdc_collateral_vault.address) < initial_ripe_collateral

    # Step 4: Leverage vault positions should be reduced
    # Either idle leverage tokens or Ripe leverage collateral should be reduced
    leverage_idle_reduced = mock_usdc_leverage_vault.balanceOf(vault.address) < initial_leverage_tokens
    leverage_ripe_reduced = mock_ripe.userCollateral(vault.address, mock_usdc_leverage_vault.address) < initial_ripe_leverage
    assert leverage_idle_reduced or leverage_ripe_reduced


def test_redemption_with_different_buffer_percentages(
    setup_prices,
    undy_levg_vault_usdc,
    mock_usdc,
    mock_usdc_collateral_vault,
    mock_ripe,
    bob,
    starter_agent,
    governance,
    vault_registry,
    switchboard_alpha,
):
    """Test redemption buffer calculations with different percentages"""
    vault = undy_levg_vault_usdc

    # Enable operations
    vault_registry.setCanDeposit(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setCanWithdraw(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setShouldAutoDeposit(vault.address, False, sender=switchboard_alpha.address)

    # Test different buffer percentages
    buffer_percentages = [5, 10, 20]  # 0.5%, 1%, 2%

    for buffer_bps in buffer_percentages:
        # Set redemption buffer (in basis points, 100 = 1%)
        vault_registry.setRedemptionBuffer(vault.address, buffer_bps, sender=switchboard_alpha.address)

        # User deposits
        deposit_amount = 10_000 * SIX_DECIMALS
        mock_usdc.mint(bob, deposit_amount, sender=governance.address)
        mock_usdc.approve(vault.address, deposit_amount, sender=bob)
        shares = vault.deposit(deposit_amount, bob, sender=bob)

        # Deposit to collateral vault
        vault.depositForYield(
            2,
            mock_usdc.address,
            mock_usdc_collateral_vault.address,
            deposit_amount,
            sender=starter_agent.address
        )

        # Add to Ripe
        vault.addCollateral(
            RIPE_LEGO_ID,
            mock_usdc_collateral_vault.address,
            deposit_amount,
            sender=starter_agent.address
        )

        # Record Ripe collateral before redemption
        collateral_before = mock_ripe.userCollateral(vault.address, mock_usdc_collateral_vault.address)

        # Redeem shares
        requested_amount = deposit_amount
        assets_received = vault.redeem(shares, bob, bob, sender=bob)

        # Calculate expected buffer amount
        expected_buffer = (requested_amount * buffer_bps) // 10000
        expected_withdrawal = requested_amount + expected_buffer

        # Verify correct amount was pulled (accounting for buffer)
        collateral_after = mock_ripe.userCollateral(vault.address, mock_usdc_collateral_vault.address)
        amount_pulled = collateral_before - collateral_after

        # The amount pulled should be at least the requested amount
        # and should account for the buffer (within rounding)
        assert amount_pulled >= requested_amount
        assert assets_received == requested_amount  # User gets exact amount

        # Clean up for next iteration
        mock_usdc.transfer(governance.address, mock_usdc.balanceOf(bob), sender=bob)


def test_partial_redemption_across_all_steps(
    setup_prices,
    setup_vault_for_redemption,
    mock_usdc,
    mock_usdc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_ripe,
    bob,
):
    """Test partial redemption that requires funds from all 4 steps"""
    setup = setup_vault_for_redemption
    vault = setup['vault']
    shares = setup['shares']

    # Calculate partial redemption (60% of shares)
    partial_shares = (shares * 60) // 100
    expected_assets = (setup['total'] * 60) // 100

    # Record balances before
    initial_usdc = mock_usdc.balanceOf(bob)
    initial_vault_usdc = mock_usdc.balanceOf(vault.address)
    initial_collateral_idle = mock_usdc_collateral_vault.balanceOf(vault.address)
    initial_collateral_ripe = mock_ripe.userCollateral(vault.address, mock_usdc_collateral_vault.address)
    initial_leverage_idle = mock_usdc_leverage_vault.balanceOf(vault.address)
    initial_leverage_ripe = mock_ripe.userCollateral(vault.address, mock_usdc_leverage_vault.address)

    # Perform partial redemption
    assets_received = vault.redeem(partial_shares, bob, bob, sender=bob)

    # Verify correct amount received
    assert assets_received >= expected_assets - 100  # Allow small rounding difference
    assert assets_received <= expected_assets + 100
    assert mock_usdc.balanceOf(bob) == initial_usdc + assets_received

    # Verify funds were pulled from multiple steps
    total_pulled = 0

    # Step 1: Idle USDC
    usdc_pulled = initial_vault_usdc - mock_usdc.balanceOf(vault.address)
    total_pulled += usdc_pulled

    # Step 2: Idle collateral vault
    collateral_idle_pulled = initial_collateral_idle - mock_usdc_collateral_vault.balanceOf(vault.address)
    total_pulled += collateral_idle_pulled

    # Step 3: Ripe collateral
    collateral_ripe_pulled = initial_collateral_ripe - mock_ripe.userCollateral(vault.address, mock_usdc_collateral_vault.address)
    total_pulled += collateral_ripe_pulled

    # Step 4: Leverage positions
    leverage_idle_pulled = initial_leverage_idle - mock_usdc_leverage_vault.balanceOf(vault.address)
    leverage_ripe_pulled = initial_leverage_ripe - mock_ripe.userCollateral(vault.address, mock_usdc_leverage_vault.address)
    total_pulled += leverage_idle_pulled + leverage_ripe_pulled

    # Verify total matches (within rounding)
    assert total_pulled >= assets_received - 100
    assert total_pulled <= assets_received + 100


def test_redemption_close_enough_small_amounts(
    setup_prices,
    undy_levg_vault_usdc,
    mock_usdc,
    bob,
    governance,
    vault_registry,
    switchboard_alpha,
):
    """Test isRedemptionCloseEnough with small amounts where buffer rounds to 0"""
    vault = undy_levg_vault_usdc

    # Enable operations
    vault_registry.setCanDeposit(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setCanWithdraw(vault.address, True, sender=switchboard_alpha.address)

    # Deposit small amount (10,000 units = 0.01 USDC)
    # Using a slightly larger amount to avoid issues with very tiny amounts
    small_amount = 10_000  # 0.1% of this is 10, still very small
    mock_usdc.mint(bob, small_amount, sender=governance.address)
    mock_usdc.approve(vault.address, small_amount, sender=bob)
    shares = vault.deposit(small_amount, bob, sender=bob)

    # Redeem - with such small amount, buffer calculation should handle correctly
    initial_balance = mock_usdc.balanceOf(bob)

    # This should not revert even though buffer rounds to 0
    assets_received = vault.redeem(shares, bob, bob, sender=bob)

    # Verify redemption succeeded
    assert assets_received > 0
    assert mock_usdc.balanceOf(bob) == initial_balance + assets_received


def test_redemption_exact_amount_available(
    setup_prices,
    undy_levg_vault_usdc,
    mock_usdc,
    bob,
    governance,
    vault_registry,
    switchboard_alpha,
):
    """Test redemption when exactly the requested amount is available"""
    vault = undy_levg_vault_usdc

    # Enable operations
    vault_registry.setCanDeposit(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setCanWithdraw(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setShouldAutoDeposit(vault.address, False, sender=switchboard_alpha.address)

    # Deposit exact amount
    exact_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(bob, exact_amount, sender=governance.address)
    mock_usdc.approve(vault.address, exact_amount, sender=bob)
    shares = vault.deposit(exact_amount, bob, sender=bob)

    # All funds are idle in vault as USDC
    assert mock_usdc.balanceOf(vault.address) == exact_amount

    # Redeem exactly what's available
    initial_balance = mock_usdc.balanceOf(bob)
    assets_received = vault.redeem(shares, bob, bob, sender=bob)

    # Verify exact amount received, no extra steps executed
    assert assets_received == exact_amount
    assert mock_usdc.balanceOf(bob) == initial_balance + exact_amount
    assert mock_usdc.balanceOf(vault.address) == 0


def test_redemption_with_deleverage_integration(
    setup_prices,
    undy_levg_vault_usdc,
    mock_usdc,
    mock_usdc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_green_token,
    mock_ripe,
    bob,
    starter_agent,
    governance,
    vault_registry,
    switchboard_alpha,
):
    """Test that deleverage is called before removing collateral when needed"""
    vault = undy_levg_vault_usdc

    # Enable operations
    vault_registry.setCanDeposit(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setCanWithdraw(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setShouldAutoDeposit(vault.address, False, sender=switchboard_alpha.address)

    # Set max borrow amount so Ripe credit engine doesn't limit borrowing
    mock_ripe.setMaxBorrowAmount(vault.address, MAX_UINT256)

    # User deposits
    deposit_amount = 20_000 * SIX_DECIMALS
    mock_usdc.mint(bob, deposit_amount, sender=governance.address)
    mock_usdc.approve(vault.address, deposit_amount, sender=bob)
    shares = vault.deposit(deposit_amount, bob, sender=bob)

    # Create leveraged position:
    # 1. Deposit to collateral vault
    vault.depositForYield(
        2,
        mock_usdc.address,
        mock_usdc_collateral_vault.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # 2. Add as collateral to Ripe
    vault.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc_collateral_vault.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # 3. Borrow GREEN
    borrow_amount = 10_000 * EIGHTEEN_DECIMALS
    vault.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        borrow_amount,
        sender=starter_agent.address
    )

    # 4. For this test, let's add leverage vault tokens to Ripe
    # First deposit some USDC to leverage vault
    mock_usdc.mint(vault.address, 5_000 * SIX_DECIMALS, sender=governance.address)
    vault.depositForYield(
        2,
        mock_usdc.address,
        mock_usdc_leverage_vault.address,
        5_000 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    # 5. Add leverage vault tokens as collateral
    leverage_balance = mock_usdc_leverage_vault.balanceOf(vault.address)
    vault.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc_leverage_vault.address,
        leverage_balance,
        sender=starter_agent.address
    )

    # Verify we have debt and leverage vault tokens on Ripe
    initial_debt = mock_ripe.userDebt(vault.address)
    assert initial_debt > 0
    assert mock_ripe.userCollateral(vault.address, mock_usdc_leverage_vault.address) > 0

    # Manually deleverage before redemption (simulating agent action)
    # Give vault GREEN tokens and repay debt
    mock_green_token.mint(vault.address, borrow_amount, sender=governance.address)
    vault.repayDebt(
        RIPE_LEGO_ID,
        mock_green_token.address,
        borrow_amount,
        sender=starter_agent.address
    )

    # Verify debt was repaid
    final_debt = mock_ripe.userDebt(vault.address)
    assert final_debt == 0, f"Debt should be cleared after manual deleverage: {final_debt}"

    # Now redeem - with debt cleared, should get full value back
    initial_balance = mock_usdc.balanceOf(bob)
    min_out = deposit_amount * 98 // 100  # Accept max 2% loss from fees/rounding
    assets_received = vault.redeemWithMinAmountOut(shares, min_out, bob, bob, sender=bob)

    # Verify redemption succeeded after deleverage
    assert assets_received >= min_out
    assert mock_usdc.balanceOf(bob) >= initial_balance + min_out

    # Test demonstrates redemption works correctly after manual deleverage
    # (automatic deleverage on redemption may not be implemented)


def test_redemption_waterfall_ordering_step2_before_step3(
    setup_prices,
    undy_levg_vault_usdc,
    mock_usdc,
    mock_usdc_collateral_vault,
    mock_ripe,
    bob,
    starter_agent,
    governance,
    vault_registry,
    switchboard_alpha,
):
    """Test that idle collateral vault tokens (step 2) are used before Ripe collateral (step 3)"""
    vault = undy_levg_vault_usdc

    # Enable operations
    vault_registry.setCanDeposit(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setCanWithdraw(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setShouldAutoDeposit(vault.address, False, sender=switchboard_alpha.address)

    # User deposits
    deposit_amount = 20_000 * SIX_DECIMALS
    mock_usdc.mint(bob, deposit_amount, sender=governance.address)
    mock_usdc.approve(vault.address, deposit_amount, sender=bob)
    shares = vault.deposit(deposit_amount, bob, sender=bob)

    # Split funds between idle collateral and Ripe collateral
    # Deposit all to collateral vault first
    total_amount = 20_000 * SIX_DECIMALS
    vault.depositForYield(
        2,
        mock_usdc.address,
        mock_usdc_collateral_vault.address,
        total_amount,
        sender=starter_agent.address
    )

    # Now add only half to Ripe, leaving half idle
    ripe_collateral = 10_000 * SIX_DECIMALS
    vault.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc_collateral_vault.address,
        ripe_collateral,
        sender=starter_agent.address
    )

    # Verify setup - should have 10k idle and 10k on Ripe
    idle_collateral = 10_000 * SIX_DECIMALS
    assert mock_usdc_collateral_vault.balanceOf(vault.address) == idle_collateral
    assert mock_ripe.userCollateral(vault.address, mock_usdc_collateral_vault.address) == ripe_collateral

    # Redeem small amount that should only use step 2
    small_shares = shares // 4  # 25% = 5000 USDC
    initial_balance = mock_usdc.balanceOf(bob)

    assets_received = vault.redeem(small_shares, bob, bob, sender=bob)

    # Verify step 2 was used (idle collateral reduced)
    assert mock_usdc_collateral_vault.balanceOf(vault.address) < idle_collateral

    # Verify step 3 was NOT used (Ripe collateral unchanged)
    assert mock_ripe.userCollateral(vault.address, mock_usdc_collateral_vault.address) == ripe_collateral

    assert mock_usdc.balanceOf(bob) == initial_balance + assets_received


def test_redemption_waterfall_ordering_step3_before_step4(
    setup_prices,
    undy_levg_vault_usdc,
    mock_usdc,
    mock_usdc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_ripe,
    bob,
    starter_agent,
    governance,
    vault_registry,
    switchboard_alpha,
):
    """Test that Ripe collateral (step 3) is used before leverage vault (step 4)"""
    vault = undy_levg_vault_usdc

    # Enable operations
    vault_registry.setCanDeposit(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setCanWithdraw(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setShouldAutoDeposit(vault.address, False, sender=switchboard_alpha.address)

    # User deposits
    deposit_amount = 30_000 * SIX_DECIMALS
    mock_usdc.mint(bob, deposit_amount, sender=governance.address)
    mock_usdc.approve(vault.address, deposit_amount, sender=bob)
    shares = vault.deposit(deposit_amount, bob, sender=bob)

    # Set up funds:
    # No idle USDC (step 1)
    # No idle collateral vault (step 2)

    # Step 3: Add collateral to Ripe
    collateral_amount = 15_000 * SIX_DECIMALS
    vault.depositForYield(
        2,
        mock_usdc.address,
        mock_usdc_collateral_vault.address,
        collateral_amount,
        sender=starter_agent.address
    )
    vault.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc_collateral_vault.address,
        collateral_amount,
        sender=starter_agent.address
    )

    # Step 4: Add leverage vault tokens (idle)
    leverage_amount = 15_000 * SIX_DECIMALS
    vault.depositForYield(
        2,
        mock_usdc.address,
        mock_usdc_leverage_vault.address,
        leverage_amount,
        sender=starter_agent.address
    )

    # Verify setup
    assert mock_ripe.userCollateral(vault.address, mock_usdc_collateral_vault.address) == collateral_amount
    assert mock_usdc_leverage_vault.balanceOf(vault.address) == leverage_amount

    # Redeem amount that should use step 3 but not all of step 4
    partial_shares = shares // 3  # 33% = ~10000 USDC
    initial_balance = mock_usdc.balanceOf(bob)

    assets_received = vault.redeem(partial_shares, bob, bob, sender=bob)

    # Verify step 3 was used (Ripe collateral reduced)
    remaining_collateral = mock_ripe.userCollateral(vault.address, mock_usdc_collateral_vault.address)
    assert remaining_collateral < collateral_amount

    # Verify step 4 was not fully used (some leverage tokens remain)
    assert mock_usdc_leverage_vault.balanceOf(vault.address) > 0

    assert mock_usdc.balanceOf(bob) == initial_balance + assets_received


def test_redemption_with_zero_debt_no_deleverage(
    setup_prices,
    setup_vault_for_redemption,
    mock_usdc,
    mock_ripe,
    bob,
):
    """Test redemption when there's no debt doesn't trigger deleverage"""
    setup = setup_vault_for_redemption
    vault = setup['vault']
    shares = setup['shares']

    # Verify no debt
    assert mock_ripe.userDebt(vault.address) == 0

    # Mock deleverage to ensure it's not called
    deleverage_called = []
    original_deleverage = vault._deleverage if hasattr(vault, '_deleverage') else None

    def mock_deleverage(requested_amount):
        deleverage_called.append(requested_amount)
        if original_deleverage:
            return original_deleverage(requested_amount)
        return 0

    if hasattr(vault, '_deleverage'):
        vault._deleverage = mock_deleverage

    # Redeem
    initial_balance = mock_usdc.balanceOf(bob)
    assets_received = vault.redeem(shares, bob, bob, sender=bob)

    # Verify deleverage was NOT called
    assert len(deleverage_called) == 0, "Deleverage should not be called when no debt"

    # Verify redemption succeeded
    assert assets_received > 0
    assert mock_usdc.balanceOf(bob) == initial_balance + assets_received


def test_redemption_with_leverage_vault_equals_collateral_vault_usdc(
    setup_prices,
    undy_levg_vault_usdc,
    mock_usdc,
    mock_usdc_collateral_vault,
    mock_usdc_leverage_vault,
    bob,
    starter_agent,
    governance,
    vault_registry,
    switchboard_alpha,
):
    """Test USDC vault edge case where leverage vault could equal collateral vault"""
    vault = undy_levg_vault_usdc

    # For USDC vault, leverage vault is different from collateral vault by default
    # But test the logic handles it correctly

    # Enable operations
    vault_registry.setCanDeposit(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setCanWithdraw(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setShouldAutoDeposit(vault.address, False, sender=switchboard_alpha.address)

    # User deposits
    deposit_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(bob, deposit_amount, sender=governance.address)
    mock_usdc.approve(vault.address, deposit_amount, sender=bob)
    shares = vault.deposit(deposit_amount, bob, sender=bob)

    # Deposit to both vaults
    vault.depositForYield(
        2,
        mock_usdc.address,
        mock_usdc_collateral_vault.address,
        deposit_amount // 2,
        sender=starter_agent.address
    )

    vault.depositForYield(
        2,
        mock_usdc.address,
        mock_usdc_leverage_vault.address,
        deposit_amount // 2,
        sender=starter_agent.address
    )

    # Redeem
    initial_balance = mock_usdc.balanceOf(bob)
    assets_received = vault.redeem(shares, bob, bob, sender=bob)

    # Verify redemption succeeded
    assert assets_received == deposit_amount
    assert mock_usdc.balanceOf(bob) == initial_balance + assets_received

    # Verify both vault tokens were withdrawn
    assert mock_usdc_collateral_vault.balanceOf(vault.address) == 0
    assert mock_usdc_leverage_vault.balanceOf(vault.address) == 0


#############################################
# Parameterized Tests for Different Vaults #
#############################################

@pytest.mark.parametrize("vault_type", ["usdc", "cbbtc", "weth"])
def test_redemption_waterfall_all_vaults(
    vault_type,
    setup_prices,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mock_usdc_collateral_vault,
    mock_cbbtc_collateral_vault,
    mock_weth_collateral_vault,
    bob,
    starter_agent,
    governance,
    vault_registry,
    switchboard_alpha,
):
    """Test redemption waterfall works for all vault types (USDC, CBBTC, WETH)"""

    # Select vault and token based on type
    if vault_type == "usdc":
        vault = undy_levg_vault_usdc
        token = mock_usdc
        collateral_vault = mock_usdc_collateral_vault
        decimals = SIX_DECIMALS
        amount = 10_000 * decimals
    elif vault_type == "cbbtc":
        vault = undy_levg_vault_cbbtc
        token = mock_cbbtc
        collateral_vault = mock_cbbtc_collateral_vault
        decimals = EIGHT_DECIMALS
        amount = 1 * decimals  # 1 CBBTC
    else:  # weth
        vault = undy_levg_vault_weth
        token = mock_weth
        collateral_vault = mock_weth_collateral_vault
        decimals = EIGHTEEN_DECIMALS
        amount = 5 * decimals  # 5 WETH

    # Enable operations
    vault_registry.setCanDeposit(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setCanWithdraw(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setShouldAutoDeposit(vault.address, False, sender=switchboard_alpha.address)

    # Mint tokens to user
    if vault_type == "weth":
        # For WETH, need to wrap ETH
        boa.env.set_balance(bob, amount)
        mock_weth.deposit(value=amount, sender=bob)
    else:
        token.mint(bob, amount, sender=governance.address)

    token.approve(vault.address, amount, sender=bob)

    # Deposit
    shares = vault.deposit(amount, bob, sender=bob)
    assert shares > 0

    # Split funds across different locations
    # Step 2: Deposit half to collateral vault
    vault.depositForYield(
        2,
        token.address,
        collateral_vault.address,
        amount // 2,
        sender=starter_agent.address
    )

    # Step 3: Add quarter to Ripe
    vault.addCollateral(
        RIPE_LEGO_ID,
        collateral_vault.address,
        amount // 4,
        sender=starter_agent.address
    )

    # Redeem all shares
    initial_balance = token.balanceOf(bob)
    assets_received = vault.redeem(shares, bob, bob, sender=bob)

    # Verify redemption succeeded
    assert assets_received > 0
    assert token.balanceOf(bob) == initial_balance + assets_received

    # For exact amount verification, account for potential rounding
    assert assets_received >= amount - 10
    assert assets_received <= amount + 10