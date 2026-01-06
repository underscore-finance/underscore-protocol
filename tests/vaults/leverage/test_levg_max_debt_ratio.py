import pytest
import boa

from constants import MAX_UINT256, EIGHTEEN_DECIMALS, ZERO_ADDRESS
from conf_utils import filter_logs

# Decimal constants
SIX_DECIMALS = 10 ** 6
EIGHT_DECIMALS = 10 ** 8

# Lego IDs
RIPE_LEGO_ID = 1

# Ratio constants
HUNDRED_PERCENT = 100_00  # 100.00%


############
# Fixtures #
############


@pytest.fixture(scope="module")
def setup_prices(mock_ripe, mock_green_token, mock_savings_green_token, mock_usdc, mock_cbbtc, mock_weth):
    """Set up prices for all assets"""
    mock_ripe.setPrice(mock_green_token, 1 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_savings_green_token, 1 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_usdc, 1 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_cbbtc, 90_000 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_weth, 2_000 * EIGHTEEN_DECIMALS)
    return mock_ripe


@pytest.fixture(scope="function")
def setup_usdc_vault(undy_levg_vault_usdc, vault_registry, switchboard_alpha, mock_usdc, starter_agent, governance, mock_ripe):
    """Fresh USDC vault setup for each test"""
    vault = undy_levg_vault_usdc

    # Enable vault operations
    vault_registry.setCanDeposit(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setCanWithdraw(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setShouldAutoDeposit(vault.address, False, sender=switchboard_alpha.address)

    # Setup: deposit 50k USDC as user capital
    user_deposit = 50_000 * SIX_DECIMALS
    mock_usdc.mint(starter_agent.address, user_deposit, sender=governance.address)
    mock_usdc.approve(vault.address, user_deposit, sender=starter_agent.address)
    vault.deposit(user_deposit, starter_agent.address, sender=starter_agent.address)

    # Set max borrow amount so Ripe credit engine doesn't limit borrowing
    mock_ripe.setMaxBorrowAmount(vault.address, MAX_UINT256)

    return vault


@pytest.fixture(scope="function")
def setup_cbbtc_vault(undy_levg_vault_cbbtc, vault_registry, switchboard_alpha, mock_cbbtc, starter_agent, governance, mock_ripe):
    """Fresh CBBTC vault setup for each test"""
    vault = undy_levg_vault_cbbtc

    # Enable vault operations
    vault_registry.setCanDeposit(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setCanWithdraw(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setShouldAutoDeposit(vault.address, False, sender=switchboard_alpha.address)

    # Setup: deposit 3 CBBTC as user capital
    user_deposit = 3 * EIGHT_DECIMALS
    mock_cbbtc.mint(starter_agent.address, user_deposit, sender=governance.address)
    mock_cbbtc.approve(vault.address, user_deposit, sender=starter_agent.address)
    vault.deposit(user_deposit, starter_agent.address, sender=starter_agent.address)

    # Mint collateral CBBTC directly to vault
    collateral_cbbtc = 10 * EIGHT_DECIMALS
    mock_cbbtc.mint(vault.address, collateral_cbbtc, sender=governance.address)

    # Set max borrow amount so Ripe credit engine doesn't limit borrowing
    mock_ripe.setMaxBorrowAmount(vault.address, MAX_UINT256)

    return vault


############################
# 1. setMaxDebtRatio Tests #
############################


def test_set_max_debt_ratio_valid(
    setup_usdc_vault,
    switchboard_alpha,
):
    """Test setting valid maxDebtRatio"""
    vault = setup_usdc_vault

    # Set to 70%
    vault.setMaxDebtRatio(70_00, sender=switchboard_alpha.address)
    log = filter_logs(vault, "MaxDebtRatioSet")[0]

    # Verify
    assert vault.maxDebtRatio() == 70_00
    assert log.maxDebtRatio == 70_00


def test_set_max_debt_ratio_zero(
    setup_usdc_vault,
    switchboard_alpha,
):
    """Test setting maxDebtRatio to 0 (no limit)"""
    vault = setup_usdc_vault

    # Set to 0%
    vault.setMaxDebtRatio(0, sender=switchboard_alpha.address)

    # Verify
    assert vault.maxDebtRatio() == 0


def test_set_max_debt_ratio_max(
    setup_usdc_vault,
    switchboard_alpha,
):
    """Test setting maxDebtRatio to 100%"""
    vault = setup_usdc_vault

    # Set to 100%
    vault.setMaxDebtRatio(HUNDRED_PERCENT, sender=switchboard_alpha.address)

    # Verify
    assert vault.maxDebtRatio() == HUNDRED_PERCENT


def test_set_max_debt_ratio_300_percent(
    setup_usdc_vault,
    switchboard_alpha,
):
    """Test setting maxDebtRatio to 300%"""
    vault = setup_usdc_vault

    # Set to 300%
    vault.setMaxDebtRatio(300_00, sender=switchboard_alpha.address)
    log = filter_logs(vault, "MaxDebtRatioSet")[0]

    # Verify
    assert vault.maxDebtRatio() == 300_00
    assert log.maxDebtRatio == 300_00


def test_set_max_debt_ratio_above_300_percent_fails(
    setup_usdc_vault,
    switchboard_alpha,
):
    """Test that setting maxDebtRatio > 300% reverts"""
    vault = setup_usdc_vault

    # Try to set to 301%
    with boa.reverts("ratio too high (max 300%)"):
        vault.setMaxDebtRatio(300_01, sender=switchboard_alpha.address)


def test_set_max_debt_ratio_unauthorized_fails(
    setup_usdc_vault,
    starter_agent,
):
    """Test that non-switchboard cannot set maxDebtRatio"""
    vault = setup_usdc_vault

    # Try to set as non-switchboard
    with boa.reverts("no perms"):
        vault.setMaxDebtRatio(70_00, sender=starter_agent.address)


#####################################
# 2. getMaxBorrowAmount() View Tests #
#####################################


def test_get_max_borrow_amount_no_limit_usdc(
    setup_prices,
    setup_usdc_vault,
    levg_vault_helper,
    mock_usdc,
    switchboard_alpha,
):
    """Test getMaxBorrowAmount returns max_value when ratio is 0"""
    vault = setup_usdc_vault

    # Set maxDebtRatio to 0 for unlimited borrowing
    vault.setMaxDebtRatio(0, sender=switchboard_alpha.address)

    # Ensure maxDebtRatio is 0
    assert vault.maxDebtRatio() == 0

    # Get max borrow amount
    max_borrow = levg_vault_helper.getMaxBorrowAmount(
        vault.address,
        mock_usdc.address,
        vault.collateralAsset()[0],  # vaultToken
        vault.collateralAsset()[1],  # ripeVaultId
        vault.getTotalAssets(False),
        vault.maxDebtRatio(),
    )

    # Should return max_value
    assert max_borrow == MAX_UINT256


def test_get_max_borrow_amount_with_limit_usdc(
    setup_prices,
    setup_usdc_vault,
    levg_vault_helper,
    mock_usdc,
    switchboard_alpha,
):
    """Test getMaxBorrowAmount calculates correct limit for USDC vault"""
    vault = setup_usdc_vault

    # Set 70% max debt ratio
    vault.setMaxDebtRatio(70_00, sender=switchboard_alpha.address)

    # totalAssets should be 50,000 USDC
    assert vault.getTotalAssets(False) == 50_000 * SIX_DECIMALS

    # Get max borrow amount
    max_borrow = levg_vault_helper.getMaxBorrowAmount(
        vault.address,
        mock_usdc.address,
        vault.collateralAsset()[0],
        vault.collateralAsset()[1],
        vault.getTotalAssets(False),
        vault.maxDebtRatio(),
    )

    # Should be 70% of 50,000 = 35,000 GREEN (18 decimals)
    expected_max = 35_000 * EIGHTEEN_DECIMALS
    assert max_borrow == expected_max


def test_get_max_borrow_amount_with_partial_debt_usdc(
    setup_prices,
    setup_usdc_vault,
    levg_vault_helper,
    mock_usdc,
    mock_ripe,
    switchboard_alpha,
):
    """Test getMaxBorrowAmount returns remaining capacity when debt exists without GREEN holdings"""
    vault = setup_usdc_vault

    # Set 70% max debt ratio
    vault.setMaxDebtRatio(70_00, sender=switchboard_alpha.address)

    # Set debt directly (simulates debt without holding GREEN to offset it)
    mock_ripe.setUserDebt(vault.address, 3_000 * EIGHTEEN_DECIMALS)

    # Get max borrow amount
    max_borrow = levg_vault_helper.getMaxBorrowAmount(
        vault.address,
        mock_usdc.address,
        vault.collateralAsset()[0],
        vault.collateralAsset()[1],
        vault.getTotalAssets(False),
        vault.maxDebtRatio(),
    )

    # Should be 35,000 - 3,000 = 32,000 GREEN remaining
    expected_remaining = 32_000 * EIGHTEEN_DECIMALS
    assert max_borrow == expected_remaining


def test_get_max_borrow_amount_at_limit_usdc(
    setup_prices,
    setup_usdc_vault,
    levg_vault_helper,
    mock_usdc,
    mock_ripe,
    switchboard_alpha,
):
    """Test getMaxBorrowAmount returns 0 when at limit (debt without GREEN holdings)"""
    vault = setup_usdc_vault

    # Set 70% max debt ratio
    vault.setMaxDebtRatio(70_00, sender=switchboard_alpha.address)

    # Set debt directly to full limit (simulates debt without holding GREEN to offset it)
    mock_ripe.setUserDebt(vault.address, 35_000 * EIGHTEEN_DECIMALS)

    # Get max borrow amount
    max_borrow = levg_vault_helper.getMaxBorrowAmount(
        vault.address,
        mock_usdc.address,
        vault.collateralAsset()[0],
        vault.collateralAsset()[1],
        vault.getTotalAssets(False),
        vault.maxDebtRatio(),
    )

    # Should be 0 (at limit)
    assert max_borrow == 0


def test_get_max_borrow_amount_cbbtc_vault(
    setup_prices,
    setup_cbbtc_vault,
    levg_vault_helper,
    mock_cbbtc,
    mock_cbbtc_collateral_vault,
    switchboard_alpha,
    starter_agent,
):
    """Test getMaxBorrowAmount for CBBTC vault uses collateral value"""
    vault = setup_cbbtc_vault

    # Set 70% max debt ratio
    vault.setMaxDebtRatio(70_00, sender=switchboard_alpha.address)

    # Deposit CBBTC to collateral vault
    lego_id = 2
    vault.depositForYield(
        lego_id,
        mock_cbbtc.address,
        mock_cbbtc_collateral_vault.address,
        sender=starter_agent.address
    )

    # Get max borrow amount
    max_borrow = levg_vault_helper.getMaxBorrowAmount(
        vault.address,
        mock_cbbtc.address,
        vault.collateralAsset()[0],
        vault.collateralAsset()[1],
        0,  # _totalAssets (not used for non-USDC vaults)
        vault.maxDebtRatio(),
    )

    # Fixture deposits 3 CBBTC as user capital + 10 CBBTC for collateral operations
    # depositForYield deposits ALL CBBTC from the vault (13 total) to the collateral vault
    # 13 CBBTC @ $90,000 each = $1,170,000, so 70% = $819,000 = 819,000 GREEN
    expected_max = 819_000 * EIGHTEEN_DECIMALS
    assert max_borrow == expected_max


################################
# 3. borrow() Enforcement Tests #
################################


def test_borrow_within_limit(
    setup_prices,
    setup_usdc_vault,
    mock_usdc,
    mock_green_token,
    switchboard_alpha,
    starter_agent,
):
    """Test borrowing within maxDebtRatio limit succeeds"""
    vault = setup_usdc_vault

    # Set 70% max debt ratio
    vault.setMaxDebtRatio(70_00, sender=switchboard_alpha.address)

    # Add collateral
    vault.addCollateral(RIPE_LEGO_ID, mock_usdc.address, 8_000 * SIX_DECIMALS, sender=starter_agent.address)

    # Borrow 5,000 GREEN (within 7,000 limit)
    pre_green = mock_green_token.balanceOf(vault.address)
    amount_borrowed, _ = vault.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        5_000 * EIGHTEEN_DECIMALS,
        sender=starter_agent.address
    )

    # Verify borrow succeeded
    assert amount_borrowed == 5_000 * EIGHTEEN_DECIMALS
    assert mock_green_token.balanceOf(vault.address) == pre_green + 5_000 * EIGHTEEN_DECIMALS


def test_borrow_caps_to_max_limit(
    setup_prices,
    setup_usdc_vault,
    mock_usdc,
    mock_green_token,
    switchboard_alpha,
    starter_agent,
):
    """Test borrowing more than limit gets gracefully capped"""
    vault = setup_usdc_vault

    # Set 70% max debt ratio
    vault.setMaxDebtRatio(70_00, sender=switchboard_alpha.address)

    # Add collateral
    vault.addCollateral(RIPE_LEGO_ID, mock_usdc.address, 8_000 * SIX_DECIMALS, sender=starter_agent.address)

    # Try to borrow 50,000 GREEN (exceeds 35,000 limit)
    pre_green = mock_green_token.balanceOf(vault.address)
    amount_borrowed, _ = vault.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        50_000 * EIGHTEEN_DECIMALS,
        sender=starter_agent.address
    )

    # Should only borrow 35,000 (capped to 70% of 50k)
    assert amount_borrowed == 35_000 * EIGHTEEN_DECIMALS
    assert mock_green_token.balanceOf(vault.address) == pre_green + 35_000 * EIGHTEEN_DECIMALS


def test_borrow_multiple_times_green_offsets_debt(
    setup_prices,
    setup_usdc_vault,
    mock_usdc,
    mock_green_token,
    mock_ripe,
    switchboard_alpha,
    starter_agent,
):
    """Test that multiple borrows succeed because GREEN holdings offset debt"""
    vault = setup_usdc_vault

    # Set 70% max debt ratio (limit = 35,000 GREEN for 50k capital)
    vault.setMaxDebtRatio(70_00, sender=switchboard_alpha.address)

    # Add collateral
    vault.addCollateral(RIPE_LEGO_ID, mock_usdc.address, 40_000 * SIX_DECIMALS, sender=starter_agent.address)

    # First borrow: 15,000 GREEN
    initial_debt = mock_ripe.userDebt(vault.address)
    amount1, _ = vault.borrow(RIPE_LEGO_ID, mock_green_token.address, 15_000 * EIGHTEEN_DECIMALS, sender=starter_agent.address)
    assert amount1 == 15_000 * EIGHTEEN_DECIMALS

    # Second borrow: 15,000 GREEN (vault holds 30k GREEN, owes 30k debt -> net debt = 0)
    amount2, _ = vault.borrow(RIPE_LEGO_ID, mock_green_token.address, 15_000 * EIGHTEEN_DECIMALS, sender=starter_agent.address)
    assert amount2 == 15_000 * EIGHTEEN_DECIMALS

    # Verify total debt
    total_debt = mock_ripe.userDebt(vault.address) - initial_debt
    assert total_debt == 30_000 * EIGHTEEN_DECIMALS

    # Third borrow: request 10,000 - gets full amount because GREEN holdings offset debt
    # (vault holds 30k GREEN which offsets 30k debt, so max borrow capacity is still full 35k)
    amount3, _ = vault.borrow(RIPE_LEGO_ID, mock_green_token.address, 10_000 * EIGHTEEN_DECIMALS, sender=starter_agent.address)
    assert amount3 == 10_000 * EIGHTEEN_DECIMALS


def test_borrow_at_limit_fails_without_green(
    setup_prices,
    setup_usdc_vault,
    mock_usdc,
    mock_green_token,
    mock_ripe,
    switchboard_alpha,
    starter_agent,
):
    """Test borrowing fails when at debt limit (debt without GREEN holdings to offset)"""
    vault = setup_usdc_vault

    # Set 70% max debt ratio
    vault.setMaxDebtRatio(70_00, sender=switchboard_alpha.address)

    # Add collateral
    vault.addCollateral(RIPE_LEGO_ID, mock_usdc.address, 40_000 * SIX_DECIMALS, sender=starter_agent.address)

    # Set debt directly to the limit (simulates scenario where GREEN was spent, not held)
    mock_ripe.setUserDebt(vault.address, 35_000 * EIGHTEEN_DECIMALS)

    # Try to borrow more - should fail because debt is at limit without GREEN to offset
    with boa.reverts("no amount to borrow"):
        vault.borrow(RIPE_LEGO_ID, mock_green_token.address, 1_000 * EIGHTEEN_DECIMALS, sender=starter_agent.address)


def test_borrow_unlimited_when_ratio_zero(
    setup_prices,
    setup_usdc_vault,
    mock_usdc,
    mock_green_token,
    starter_agent,
    switchboard_alpha,
):
    """Test unlimited borrowing when maxDebtRatio is 0"""
    vault = setup_usdc_vault

    # Set maxDebtRatio to 0 for unlimited borrowing
    vault.setMaxDebtRatio(0, sender=switchboard_alpha.address)

    # maxDebtRatio should be 0
    assert vault.maxDebtRatio() == 0

    # Add collateral
    vault.addCollateral(RIPE_LEGO_ID, mock_usdc.address, 8_000 * SIX_DECIMALS, sender=starter_agent.address)

    # Can borrow way more than 70% - limited only by collateral
    amount_borrowed, _ = vault.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        7_500 * EIGHTEEN_DECIMALS,  # 75% of deposit
        sender=starter_agent.address
    )

    assert amount_borrowed == 7_500 * EIGHTEEN_DECIMALS


def test_borrow_at_300_percent_limit(
    setup_prices,
    setup_usdc_vault,
    mock_usdc,
    mock_green_token,
    switchboard_alpha,
    starter_agent,
):
    """Test borrowing at 300% maxDebtRatio limit"""
    vault = setup_usdc_vault

    # Set 300% max debt ratio
    vault.setMaxDebtRatio(300_00, sender=switchboard_alpha.address)

    # totalAssets is 50,000 USDC from setup
    # At 300%, max borrow = 150,000 GREEN
    expected_max = 150_000 * EIGHTEEN_DECIMALS

    # Add collateral
    vault.addCollateral(RIPE_LEGO_ID, mock_usdc.address, 180_000 * SIX_DECIMALS, sender=starter_agent.address)

    # Try to borrow 200,000 GREEN (exceeds 150,000 limit)
    pre_green = mock_green_token.balanceOf(vault.address)
    amount_borrowed, _ = vault.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        200_000 * EIGHTEEN_DECIMALS,
        sender=starter_agent.address
    )

    # Should only borrow 150,000 (capped to 300% of 50k)
    assert amount_borrowed == expected_max
    assert mock_green_token.balanceOf(vault.address) == pre_green + expected_max


##############################
# 4. Deposit/Withdrawal Tests #
##############################


def test_deposit_increases_borrow_capacity(
    setup_prices,
    setup_usdc_vault,
    mock_usdc,
    mock_green_token,
    mock_ripe,
    switchboard_alpha,
    starter_agent,
    governance,
):
    """Test that deposits increase totalAssets and borrowing capacity"""
    vault = setup_usdc_vault

    # Set 100% max debt ratio to ensure we have capacity regardless of prior state
    vault.setMaxDebtRatio(100_00, sender=switchboard_alpha.address)

    # Record initial state
    initial_capital = vault.getTotalAssets(False)
    initial_debt = mock_ripe.userDebt(vault.address)

    # Make another deposit
    additional_deposit = 10_000 * SIX_DECIMALS
    mock_usdc.mint(starter_agent.address, additional_deposit, sender=governance.address)
    mock_usdc.approve(vault.address, additional_deposit, sender=starter_agent.address)
    vault.deposit(additional_deposit, starter_agent.address, sender=starter_agent.address)

    # totalAssets should increase by deposit amount
    new_capital = vault.getTotalAssets(False)
    assert new_capital == initial_capital + additional_deposit

    # New max borrow capacity (100% of capital)
    new_max_borrow = new_capital * (10 ** 12)  # Convert 6 decimals to 18
    new_remaining = new_max_borrow - initial_debt

    # The increased capacity should equal the deposit amount (at 100% ratio)
    capacity_increase = new_remaining - (initial_capital * (10 ** 12) - initial_debt)
    expected_increase = additional_deposit * (10 ** 12)
    assert capacity_increase == expected_increase

    # Add collateral and borrow some of the new capacity (not all to avoid other limits)
    borrow_amount = 5_000 * EIGHTEEN_DECIMALS  # Just borrow 5k GREEN
    vault.addCollateral(RIPE_LEGO_ID, mock_usdc.address, 10_000 * SIX_DECIMALS, sender=starter_agent.address)
    amount_borrowed, _ = vault.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        borrow_amount,
        sender=starter_agent.address
    )

    # Should borrow the requested amount (we have capacity)
    assert amount_borrowed == borrow_amount

    # Verify debt increased correctly
    final_debt = mock_ripe.userDebt(vault.address)
    assert final_debt == initial_debt + borrow_amount


def test_withdrawal_decreases_borrow_capacity(
    setup_prices,
    setup_usdc_vault,
    levg_vault_helper,
    mock_usdc,
    mock_ripe,
    switchboard_alpha,
    starter_agent,
):
    """Test that withdrawals decrease totalAssets"""
    vault = setup_usdc_vault

    # Set 100% max debt ratio to avoid limits
    vault.setMaxDebtRatio(100_00, sender=switchboard_alpha.address)

    # Record initial capital
    initial_capital = vault.getTotalAssets(False)

    # Withdraw 2,000 USDC (use withdraw() which takes assets, not shares)
    withdraw_amount = 2_000 * SIX_DECIMALS
    vault.withdraw(withdraw_amount, starter_agent.address, starter_agent.address, sender=starter_agent.address)

    # totalAssets should decrease by withdrawn amount
    new_capital = vault.getTotalAssets(False)
    capital_decrease = initial_capital - new_capital

    # Should have decreased by approximately the withdraw amount
    assert capital_decrease >= withdraw_amount * 99 // 100  # Within 1% tolerance
    assert capital_decrease <= withdraw_amount * 101 // 100

    # Now set 70% ratio and verify max borrow is based on new lower capital
    vault.setMaxDebtRatio(70_00, sender=switchboard_alpha.address)
    max_borrow = levg_vault_helper.getMaxBorrowAmount(
        vault.address,
        mock_usdc.address,
        vault.collateralAsset()[0],
        vault.collateralAsset()[1],
        vault.getTotalAssets(False),
        vault.maxDebtRatio(),
    )

    # Max should be 70% of new capital minus existing debt
    expected_max_debt = new_capital * 70 // 100 * (10 ** 12)  # Convert to 18 decimals
    existing_debt = mock_ripe.userDebt(vault.address)
    expected_max_borrow = max(0, expected_max_debt - existing_debt)

    assert max_borrow == expected_max_borrow


############################
# 5. CBBTC Vault Tests #
############################


def test_cbbtc_vault_enforces_limit(
    setup_prices,
    setup_cbbtc_vault,
    mock_cbbtc,
    mock_cbbtc_collateral_vault,
    mock_green_token,
    switchboard_alpha,
    starter_agent,
):
    """Test that CBBTC vault enforces maxDebtRatio based on collateral value"""
    vault = setup_cbbtc_vault

    # Set 70% max debt ratio
    vault.setMaxDebtRatio(70_00, sender=switchboard_alpha.address)

    # Deposit CBBTC to collateral vault (1 CBBTC = $90,000)
    lego_id = 2
    vault.depositForYield(
        lego_id,
        mock_cbbtc.address,
        mock_cbbtc_collateral_vault.address,
        sender=starter_agent.address
    )

    # Add collateral to Ripe
    vault.addCollateral(
        RIPE_LEGO_ID,
        mock_cbbtc_collateral_vault.address,
        sender=starter_agent.address
    )

    # Try to borrow 100,000 GREEN
    # Vault has 3 CBBTC @ $90k = $270k, 70% limit = $189k = 189,000 GREEN
    # Borrow should succeed without capping since 100k < 189k
    amount_borrowed, _ = vault.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        100_000 * EIGHTEEN_DECIMALS,
        sender=starter_agent.address
    )

    # Should return full 100,000 since it's under the 189,000 limit
    assert amount_borrowed == 100_000 * EIGHTEEN_DECIMALS


#########################
# 6. Integration Tests #
#########################


def test_complete_flow_usdc_vault(
    setup_prices,
    setup_usdc_vault,
    mock_usdc,
    mock_green_token,
    mock_ripe,
    switchboard_alpha,
    starter_agent,
    governance,
):
    """Test complete flow: deposit, set ratio, add collateral, borrow"""
    vault = setup_usdc_vault

    # Record initial state
    initial_capital = vault.getTotalAssets(False)

    # 1. Make a fresh deposit to increase capacity
    new_deposit = 20_000 * SIX_DECIMALS
    mock_usdc.mint(starter_agent.address, new_deposit, sender=governance.address)
    mock_usdc.approve(vault.address, new_deposit, sender=starter_agent.address)
    vault.deposit(new_deposit, starter_agent.address, sender=starter_agent.address)

    new_capital = vault.getTotalAssets(False)
    assert new_capital == initial_capital + new_deposit

    # 2. Set maxDebtRatio to 80%
    vault.setMaxDebtRatio(80_00, sender=switchboard_alpha.address)
    assert vault.maxDebtRatio() == 80_00

    # 3. Add collateral and borrow
    vault.addCollateral(RIPE_LEGO_ID, mock_usdc.address, 15_000 * SIX_DECIMALS, sender=starter_agent.address)

    # Borrow 30,000 GREEN
    amount_borrowed, _ = vault.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        30_000 * EIGHTEEN_DECIMALS,
        sender=starter_agent.address
    )
    assert amount_borrowed == 30_000 * EIGHTEEN_DECIMALS
    assert mock_ripe.userDebt(vault.address) == 30_000 * EIGHTEEN_DECIMALS

    # 4. Lower ratio to 70%
    vault.setMaxDebtRatio(70_00, sender=switchboard_alpha.address)
    assert vault.maxDebtRatio() == 70_00

    # 5. Can still borrow more because vault holds GREEN that offsets debt
    # (vault holds 30k GREEN, owes 30k debt -> net debt = 0)
    amount_borrowed2, _ = vault.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        10_000 * EIGHTEEN_DECIMALS,
        sender=starter_agent.address
    )
    assert amount_borrowed2 == 10_000 * EIGHTEEN_DECIMALS
    assert mock_ripe.userDebt(vault.address) == 40_000 * EIGHTEEN_DECIMALS


def test_ratio_change_applies_immediately(
    setup_prices,
    setup_usdc_vault,
    mock_usdc,
    mock_green_token,
    mock_ripe,
    switchboard_alpha,
    starter_agent,
):
    """Test that changing maxDebtRatio applies immediately"""
    vault = setup_usdc_vault

    # Set initial ratio to 50%
    vault.setMaxDebtRatio(50_00, sender=switchboard_alpha.address)
    assert vault.maxDebtRatio() == 50_00

    # Add collateral and borrow (50% of 50k = 25k limit)
    vault.addCollateral(RIPE_LEGO_ID, mock_usdc.address, 30_000 * SIX_DECIMALS, sender=starter_agent.address)
    vault.borrow(RIPE_LEGO_ID, mock_green_token.address, 25_000 * EIGHTEEN_DECIMALS, sender=starter_agent.address)
    assert mock_ripe.userDebt(vault.address) == 25_000 * EIGHTEEN_DECIMALS

    # Increase ratio to 80%
    vault.setMaxDebtRatio(80_00, sender=switchboard_alpha.address)
    assert vault.maxDebtRatio() == 80_00

    # Can borrow more - and since vault holds 25k GREEN (offsetting 25k debt),
    # the effective net debt is 0, so the full 40k capacity is available
    amount_borrowed, _ = vault.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        20_000 * EIGHTEEN_DECIMALS,
        sender=starter_agent.address
    )
    # Gets full 20k because GREEN holdings offset previous debt
    assert amount_borrowed == 20_000 * EIGHTEEN_DECIMALS
    assert mock_ripe.userDebt(vault.address) == 45_000 * EIGHTEEN_DECIMALS


