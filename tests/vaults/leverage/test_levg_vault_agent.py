"""
Comprehensive tests for LevgVaultAgent.vy

Tests cover:
- Agent deployment and setup
- Authentication (owner bypass)
- Specialized workflows:
  - borrowAndEarnYield
  - deleverage (3 modes)
  - compoundYieldGains
"""

import pytest
import boa

from constants import MAX_UINT256, EIGHTEEN_DECIMALS, ZERO_ADDRESS
from conf_utils import filter_logs

# Decimal constants
SIX_DECIMALS = 10 ** 6
EIGHT_DECIMALS = 10 ** 8

# Lego IDs
RIPE_LEGO_ID = 1
MOCK_YIELD_LEGO_ID = 2

# Position types
POSITION_COLLATERAL = 0
POSITION_LEVERAGE = 1
POSITION_STAB_POOL = 2

# Workflow codes
WORKFLOW_BORROW_AND_EARN = 100
WORKFLOW_DELEVERAGE = 101
WORKFLOW_COMPOUND_YIELD = 102


############
# Fixtures #
############


@pytest.fixture(scope="module")
def levg_vault_agent(undy_hq, governance, mock_green_token, mock_savings_green_token):
    """Deploy LevgVaultAgent contract"""
    # Use small but valid timelocks for testing (minTimeLock must be > 0)
    return boa.load(
        "contracts/core/agent/LevgVaultAgent.vy",
        undy_hq.address,
        governance.address,  # owner
        1,  # minTimeLock (must be > 0)
        100,  # maxTimeLock
        mock_green_token.address,
        mock_savings_green_token.address,
        name="levg_vault_agent",
    )


@pytest.fixture(scope="module")
def agent_registered_usdc_wallet(levg_vault_agent, usdc_wallet_with_funds, switchboard_alpha):
    """Register agent as manager on USDC wallet"""
    usdc_wallet_with_funds.addManager(levg_vault_agent.address, sender=switchboard_alpha.address)
    return usdc_wallet_with_funds


# Empty signature for owner bypass
EMPTY_SIG = (b"", 0, 0)


#####################################
# 1. Agent Deployment & Setup Tests #
#####################################


def test_agent_deployment_sets_correct_addresses(
    levg_vault_agent,
    undy_hq,
    mock_green_token,
    mock_savings_green_token,
):
    """Test that agent deployment sets correct addresses"""
    assert levg_vault_agent.UNDY_HQ() == undy_hq.address
    assert levg_vault_agent.GREEN() == mock_green_token.address
    assert levg_vault_agent.SAVINGS_GREEN() == mock_savings_green_token.address


def test_agent_initial_nonce_is_zero(
    levg_vault_agent,
    usdc_wallet_with_funds,
):
    """Test that nonce starts at 0 for new wallets"""
    assert levg_vault_agent.currentNonce(usdc_wallet_with_funds.address) == 0
    assert levg_vault_agent.getNonce(usdc_wallet_with_funds.address) == 0


def test_agent_can_be_added_as_manager(
    levg_vault_agent,
    usdc_wallet_with_funds,
    switchboard_alpha,
):
    """Test that agent can be registered as manager"""
    # Add agent as manager (must use switchboard)
    usdc_wallet_with_funds.addManager(levg_vault_agent.address, sender=switchboard_alpha.address)

    # Verify agent is manager
    assert usdc_wallet_with_funds.indexOfManager(levg_vault_agent.address) != 0


#########################################
# 2. Workflow: borrowAndEarnYield Tests #
#########################################


def test_borrow_and_earn_basic_flow(
    setup_prices,
    levg_vault_agent,
    agent_registered_usdc_wallet,
    mock_usdc,
    mock_green_token,
    mock_usdc_leverage_vault,
    mock_ripe,
    governance,
    lego_book,
    mock_swap_lego,
    starter_agent,
    _test,
):
    """Test basic borrowAndEarnYield: borrow GREEN → swap to USDC → deposit to leverage vault"""
    wallet = agent_registered_usdc_wallet

    # Setup: Add collateral first (via wallet directly using starter_agent which is already a manager)
    wallet.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc.address,
        2_000 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    pre_debt = mock_ripe.userDebt(wallet.address)
    pre_levg_vault = mock_usdc_leverage_vault.balanceOf(wallet.address)
    pre_usdc_balance = mock_usdc.balanceOf(wallet.address)

    # Create swap instruction: GREEN -> USDC
    swap_lego_id = lego_book.getRegId(mock_swap_lego.address)
    swap_instruction = (
        swap_lego_id,
        0,  # amountIn = 0 means auto-chain from borrow
        400 * SIX_DECIMALS,
        [mock_green_token.address, mock_usdc.address],
        []
    )

    # Post-swap deposit: deposit USDC to leverage vault
    post_swap_deposit = (
        POSITION_LEVERAGE,  # positionType
        0,  # amount (auto-chain from swap)
        False,  # shouldAddToRipeCollateral
        True,  # shouldSweepAll - use entire swap output
    )

    levg_vault_agent.borrowAndEarnYield(
        wallet.address,
        [],  # removeCollateral
        [],  # withdrawPositions
        [],  # depositPositions
        [],  # addCollateral
        500 * EIGHTEEN_DECIMALS,  # borrowAmount
        False,  # wantsSavingsGreen - borrow GREEN
        False,  # shouldEnterStabPool
        swap_instruction,
        [post_swap_deposit],
        sender=governance.address
    )

    # Verify debt increased
    assert mock_ripe.userDebt(wallet.address) == pre_debt + 500 * EIGHTEEN_DECIMALS
    # Verify leverage vault tokens received
    # shouldSweepAll=True deposits all USDC: pre_usdc_balance + 500 USDC from swap
    swap_output = 500 * SIX_DECIMALS  # 500 GREEN → 500 USDC at 1:1
    expected_vault_tokens = pre_usdc_balance + swap_output  # all USDC deposited
    _test(pre_levg_vault + expected_vault_tokens, mock_usdc_leverage_vault.balanceOf(wallet.address))


def test_borrow_and_earn_with_collateral_removal(
    setup_prices,
    levg_vault_agent,
    agent_registered_usdc_wallet,
    mock_usdc,
    mock_usdc_collateral_vault,
    mock_ripe,
    governance,
    starter_agent,
):
    """Test borrowAndEarnYield with collateral removal step"""
    wallet = agent_registered_usdc_wallet

    # Setup: Deposit to vault and add as collateral (via wallet directly)
    wallet.depositForYield(
        MOCK_YIELD_LEGO_ID,
        mock_usdc.address,
        mock_usdc_collateral_vault.address,
        500 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    vault_tokens = mock_usdc_collateral_vault.balanceOf(wallet.address)

    wallet.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc_collateral_vault.address,
        vault_tokens,
        sender=starter_agent.address
    )

    pre_collateral = mock_ripe.userCollateral(wallet.address, mock_usdc_collateral_vault)

    # Remove collateral position
    remove_collateral = [(POSITION_COLLATERAL, vault_tokens // 2)]

    levg_vault_agent.borrowAndEarnYield(
        wallet.address,
        remove_collateral,  # Step 1: remove collateral
        [],
        [],
        [],
        0,  # No borrow
        False,
        False,
        (0, 0, 0, [], []),  # Empty swap
        [],
        sender=governance.address
    )

    # Verify collateral was removed (exactly vault_tokens // 2)
    expected_collateral = pre_collateral - (vault_tokens // 2)
    assert mock_ripe.userCollateral(wallet.address, mock_usdc_collateral_vault) == expected_collateral


def test_borrow_and_earn_with_savings_green(
    setup_prices,
    levg_vault_agent,
    agent_registered_usdc_wallet,
    mock_usdc,
    mock_savings_green_token,
    mock_ripe,
    governance,
    starter_agent,
    _test,
):
    """Test borrowAndEarnYield with sGREEN borrowing"""
    wallet = agent_registered_usdc_wallet

    # Setup: Add collateral via wallet
    wallet.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc.address,
        2_000 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    pre_sgreen = mock_savings_green_token.balanceOf(wallet.address)

    levg_vault_agent.borrowAndEarnYield(
        wallet.address,
        [],
        [],
        [],
        [],
        500 * EIGHTEEN_DECIMALS,  # borrowAmount
        True,  # wantsSavingsGreen - borrow sGREEN
        False,
        (0, 0, 0, [], []),  # Empty swap
        [],
        sender=governance.address
    )

    # Verify sGREEN received (500 GREEN borrowed → 500 sGREEN at 1:1)
    expected_sgreen = 500 * EIGHTEEN_DECIMALS
    _test(pre_sgreen + expected_sgreen, mock_savings_green_token.balanceOf(wallet.address))


def test_borrow_and_earn_no_borrow_amount(
    setup_prices,
    levg_vault_agent,
    agent_registered_usdc_wallet,
    mock_usdc,
    mock_ripe,
    governance,
):
    """Test borrowAndEarnYield with _borrowAmount=0 skips borrow"""
    wallet = agent_registered_usdc_wallet

    pre_debt = mock_ripe.userDebt(wallet.address)

    levg_vault_agent.borrowAndEarnYield(
        wallet.address,
        [],
        [],
        [],
        [],
        0,  # No borrow
        False,
        False,
        (0, 0, 0, [], []),
        [],
        sender=governance.address
    )

    # Debt should not change
    assert mock_ripe.userDebt(wallet.address) == pre_debt


def test_borrow_and_earn_position_leverage(
    setup_prices,
    levg_vault_agent,
    agent_registered_usdc_wallet,
    mock_usdc,
    mock_usdc_leverage_vault,
    mock_ripe,
    governance,
    starter_agent,
):
    """Test borrowAndEarnYield with POSITION_LEVERAGE type"""
    wallet = agent_registered_usdc_wallet

    # Setup: Deposit to leverage vault and add as collateral via wallet
    wallet.depositForYield(
        MOCK_YIELD_LEGO_ID,
        mock_usdc.address,
        mock_usdc_leverage_vault.address,
        500 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    vault_tokens = mock_usdc_leverage_vault.balanceOf(wallet.address)

    wallet.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc_leverage_vault.address,
        vault_tokens,
        sender=starter_agent.address
    )

    pre_collateral = mock_ripe.userCollateral(wallet.address, mock_usdc_leverage_vault)

    # Remove leverage position collateral
    remove_collateral = [(POSITION_LEVERAGE, vault_tokens // 2)]

    levg_vault_agent.borrowAndEarnYield(
        wallet.address,
        remove_collateral,
        [],
        [],
        [],
        0,
        False,
        False,
        (0, 0, 0, [], []),
        [],
        sender=governance.address
    )

    # Verify leverage collateral was removed (exactly vault_tokens // 2)
    expected_collateral = pre_collateral - (vault_tokens // 2)
    assert mock_ripe.userCollateral(wallet.address, mock_usdc_leverage_vault) == expected_collateral


#################################
# 3. Workflow: deleverage Tests #
#################################


def test_deleverage_mode_0_basic(
    setup_prices,
    levg_vault_agent,
    agent_registered_usdc_wallet,
    mock_usdc,
    mock_green_token,
    mock_ripe,
    governance,
    starter_agent,
):
    """Test deleverage mode 0: auto deleverage user"""
    wallet = agent_registered_usdc_wallet

    # Setup: Add collateral and create debt via wallet
    wallet.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc.address,
        2_000 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    wallet.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        500 * EIGHTEEN_DECIMALS,
        sender=starter_agent.address
    )

    pre_debt = mock_ripe.userDebt(wallet.address)

    # Mode 0: Auto deleverage
    levg_vault_agent.deleverage(
        wallet.address,
        0,  # mode
        200 * EIGHTEEN_DECIMALS,  # autoDeleverageAmount
        [],  # deleverageAssets (not used in mode 0)
        [],  # removeCollateral
        [],  # withdrawPositions
        (0, 0, 0, [], []),  # empty swap
        ZERO_ADDRESS,  # repayAsset - no repay
        0,  # repayAmount
        False,  # shouldSweepAllForRepay
        sender=governance.address
    )

    # Debt should be reduced by deleverageUser (200 GREEN deleveraged)
    assert mock_ripe.userDebt(wallet.address) == pre_debt - 200 * EIGHTEEN_DECIMALS


def test_deleverage_mode_1_single_asset(
    setup_prices,
    levg_vault_agent,
    agent_registered_usdc_wallet,
    mock_usdc,
    mock_green_token,
    mock_ripe,
    governance,
    starter_agent,
):
    """Test deleverage mode 1: with specific assets"""
    wallet = agent_registered_usdc_wallet

    # Setup: Add collateral and create debt via wallet
    wallet.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc.address,
        2_000 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    wallet.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        500 * EIGHTEEN_DECIMALS,
        sender=starter_agent.address
    )

    pre_debt = mock_ripe.userDebt(wallet.address)

    # DeleverageAsset: (vaultId, asset, targetRepayAmount)
    deleverage_assets = [(1, mock_usdc.address, 100 * EIGHTEEN_DECIMALS)]

    levg_vault_agent.deleverage(
        wallet.address,
        1,  # mode 1
        0,  # autoDeleverageAmount (not used)
        deleverage_assets,
        [],
        [],
        (0, 0, 0, [], []),
        ZERO_ADDRESS,
        0,
        False,
        sender=governance.address
    )

    # Debt should be reduced by targetRepayAmount (100 GREEN)
    assert mock_ripe.userDebt(wallet.address) == pre_debt - 100 * EIGHTEEN_DECIMALS


def test_deleverage_mode_2_basic_flow(
    setup_prices,
    levg_vault_agent,
    agent_registered_usdc_wallet,
    mock_usdc,
    mock_green_token,
    mock_usdc_collateral_vault,
    mock_ripe,
    governance,
    starter_agent,
    lego_book,
    mock_swap_lego,
):
    """Test deleverage mode 2: manual flow with withdraw → swap → repay"""
    wallet = agent_registered_usdc_wallet

    # Setup: Deposit to vault, add as collateral, and borrow via wallet
    wallet.depositForYield(
        MOCK_YIELD_LEGO_ID,
        mock_usdc.address,
        mock_usdc_collateral_vault.address,
        1_000 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    vault_tokens = mock_usdc_collateral_vault.balanceOf(wallet.address)

    wallet.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc_collateral_vault.address,
        vault_tokens,
        sender=starter_agent.address
    )

    wallet.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        500 * EIGHTEEN_DECIMALS,
        sender=starter_agent.address
    )

    pre_debt = mock_ripe.userDebt(wallet.address)

    # Mode 2 steps:
    # 1. Remove collateral
    remove_collateral = [(POSITION_COLLATERAL, vault_tokens // 2)]

    # 2. Withdraw from yield
    withdraw_positions = [(POSITION_COLLATERAL, 0)]  # 0 = max

    # Give wallet GREEN to repay
    mock_green_token.mint(wallet.address, 200 * EIGHTEEN_DECIMALS, sender=governance.address)

    levg_vault_agent.deleverage(
        wallet.address,
        2,  # mode 2
        0,
        [],
        remove_collateral,
        withdraw_positions,
        (0, 0, 0, [], []),  # No swap needed, we have GREEN
        mock_green_token.address,  # repayAsset
        200 * EIGHTEEN_DECIMALS,  # repayAmount
        False,
        sender=governance.address
    )

    # Debt should be reduced by repay amount
    assert mock_ripe.userDebt(wallet.address) == pre_debt - 200 * EIGHTEEN_DECIMALS


def test_deleverage_mode_2_sweep_all_for_repay(
    setup_prices,
    levg_vault_agent,
    agent_registered_usdc_wallet,
    mock_usdc,
    mock_green_token,
    mock_ripe,
    governance,
    starter_agent,
):
    """Test deleverage with shouldSweepAllForRepay=True"""
    wallet = agent_registered_usdc_wallet

    # Setup: Add collateral and borrow via wallet
    wallet.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc.address,
        2_000 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    wallet.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        300 * EIGHTEEN_DECIMALS,
        sender=starter_agent.address
    )

    # Wallet now has 300 GREEN from borrow

    levg_vault_agent.deleverage(
        wallet.address,
        2,
        0,
        [],
        [],
        [],
        (0, 0, 0, [], []),
        mock_green_token.address,
        0,  # repayAmount ignored when sweepAll
        True,  # shouldSweepAllForRepay
        sender=governance.address
    )

    # All GREEN should be used for repay
    assert mock_green_token.balanceOf(wallet.address) == 0
    assert mock_ripe.userDebt(wallet.address) == 0


def test_deleverage_no_repay(
    setup_prices,
    levg_vault_agent,
    agent_registered_usdc_wallet,
    mock_usdc,
    mock_green_token,
    mock_ripe,
    governance,
    starter_agent,
):
    """Test deleverage with empty repayAsset skips repay"""
    wallet = agent_registered_usdc_wallet

    # Setup debt via wallet
    wallet.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc.address,
        2_000 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    wallet.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        500 * EIGHTEEN_DECIMALS,
        sender=starter_agent.address
    )

    pre_debt = mock_ripe.userDebt(wallet.address)

    # Mode 0 without repay
    levg_vault_agent.deleverage(
        wallet.address,
        0,
        100 * EIGHTEEN_DECIMALS,
        [],
        [],
        [],
        (0, 0, 0, [], []),
        ZERO_ADDRESS,  # No repay asset
        0,
        False,
        sender=governance.address
    )

    # deleverageUser reduces debt by 100 GREEN (no additional repay)
    assert mock_ripe.userDebt(wallet.address) == pre_debt - 100 * EIGHTEEN_DECIMALS


##########################################
# 4. Workflow: compoundYieldGains Tests #
##########################################


def test_compound_yield_basic_flow(
    setup_prices,
    levg_vault_agent,
    agent_registered_usdc_wallet,
    mock_usdc,
    mock_usdc_collateral_vault,
    mock_usdc_leverage_vault,
    mock_ripe,
    governance,
    starter_agent,
    _test,
):
    """Test basic compoundYieldGains: withdraw → deposit to different vault"""
    wallet = agent_registered_usdc_wallet

    # Setup: Deposit to collateral vault via wallet
    wallet.depositForYield(
        MOCK_YIELD_LEGO_ID,
        mock_usdc.address,
        mock_usdc_collateral_vault.address,
        500 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    coll_vault_tokens = mock_usdc_collateral_vault.balanceOf(wallet.address)
    pre_levg_vault = mock_usdc_leverage_vault.balanceOf(wallet.address)
    pre_usdc_balance = mock_usdc.balanceOf(wallet.address)

    # Withdraw from collateral and deposit to leverage
    withdraw_positions = [(POSITION_COLLATERAL, coll_vault_tokens // 2)]

    post_swap_deposits = [(
        POSITION_LEVERAGE,
        0,  # auto-use from withdraw
        False,
        True,  # shouldSweepAll
    )]

    levg_vault_agent.compoundYieldGains(
        wallet.address,
        [],  # removeCollateral
        withdraw_positions,
        (0, 0, 0, [], []),  # No swap
        post_swap_deposits,
        [],  # addCollateral
        sender=governance.address
    )

    # Verify leverage vault tokens received
    # shouldSweepAll=True deposits all USDC: pre_usdc_balance + withdrawn amount
    withdrawn_usdc = coll_vault_tokens // 2  # 1:1 ratio in mock vaults
    expected_levg_tokens = pre_usdc_balance + withdrawn_usdc
    _test(pre_levg_vault + expected_levg_tokens, mock_usdc_leverage_vault.balanceOf(wallet.address))


def test_compound_yield_with_collateral_removal(
    setup_prices,
    levg_vault_agent,
    agent_registered_usdc_wallet,
    mock_usdc,
    mock_usdc_collateral_vault,
    mock_ripe,
    governance,
    starter_agent,
):
    """Test compoundYieldGains with collateral removal step"""
    wallet = agent_registered_usdc_wallet

    # Setup: Deposit and add to Ripe via wallet
    wallet.depositForYield(
        MOCK_YIELD_LEGO_ID,
        mock_usdc.address,
        mock_usdc_collateral_vault.address,
        500 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    vault_tokens = mock_usdc_collateral_vault.balanceOf(wallet.address)

    wallet.addCollateral(
        RIPE_LEGO_ID,
        mock_usdc_collateral_vault.address,
        vault_tokens,
        sender=starter_agent.address
    )

    pre_collateral = mock_ripe.userCollateral(wallet.address, mock_usdc_collateral_vault)

    # Remove from Ripe collateral
    remove_collateral = [(POSITION_COLLATERAL, vault_tokens // 2)]

    levg_vault_agent.compoundYieldGains(
        wallet.address,
        remove_collateral,
        [],
        (0, 0, 0, [], []),
        [],
        [],
        sender=governance.address
    )

    # Verify collateral reduced (exactly vault_tokens // 2)
    expected_collateral = pre_collateral - (vault_tokens // 2)
    assert mock_ripe.userCollateral(wallet.address, mock_usdc_collateral_vault) == expected_collateral


def test_compound_yield_add_collateral_step(
    setup_prices,
    levg_vault_agent,
    agent_registered_usdc_wallet,
    mock_usdc,
    mock_usdc_collateral_vault,
    mock_ripe,
    governance,
    starter_agent,
):
    """Test compoundYieldGains with final add collateral step"""
    wallet = agent_registered_usdc_wallet

    # Setup: Deposit to get vault tokens via wallet
    wallet.depositForYield(
        MOCK_YIELD_LEGO_ID,
        mock_usdc.address,
        mock_usdc_collateral_vault.address,
        500 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    vault_tokens = mock_usdc_collateral_vault.balanceOf(wallet.address)
    pre_collateral = mock_ripe.userCollateral(wallet.address, mock_usdc_collateral_vault)

    # Add vault tokens as collateral
    add_collateral = [(POSITION_COLLATERAL, vault_tokens)]

    levg_vault_agent.compoundYieldGains(
        wallet.address,
        [],
        [],
        (0, 0, 0, [], []),
        [],
        add_collateral,
        sender=governance.address
    )

    # Verify collateral increased
    assert mock_ripe.userCollateral(wallet.address, mock_usdc_collateral_vault) == pre_collateral + vault_tokens


def test_compound_yield_position_leverage(
    setup_prices,
    levg_vault_agent,
    agent_registered_usdc_wallet,
    mock_usdc,
    mock_usdc_leverage_vault,
    mock_usdc_collateral_vault,
    governance,
    starter_agent,
    _test,
):
    """Test compoundYieldGains with POSITION_LEVERAGE type"""
    wallet = agent_registered_usdc_wallet

    # Setup: Deposit to leverage vault via wallet
    wallet.depositForYield(
        MOCK_YIELD_LEGO_ID,
        mock_usdc.address,
        mock_usdc_leverage_vault.address,
        500 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    levg_vault_tokens = mock_usdc_leverage_vault.balanceOf(wallet.address)
    pre_coll_vault = mock_usdc_collateral_vault.balanceOf(wallet.address)
    pre_usdc_balance = mock_usdc.balanceOf(wallet.address)

    # Withdraw from leverage and deposit to collateral
    withdraw_positions = [(POSITION_LEVERAGE, levg_vault_tokens // 2)]

    post_swap_deposits = [(
        POSITION_COLLATERAL,
        0,
        False,
        True,  # shouldSweepAll
    )]

    levg_vault_agent.compoundYieldGains(
        wallet.address,
        [],
        withdraw_positions,
        (0, 0, 0, [], []),
        post_swap_deposits,
        [],
        sender=governance.address
    )

    # Verify collateral vault tokens received
    # shouldSweepAll=True deposits all USDC: pre_usdc_balance + withdrawn amount
    withdrawn_usdc = levg_vault_tokens // 2  # 1:1 ratio in mock vaults
    expected_coll_tokens = pre_usdc_balance + withdrawn_usdc
    _test(pre_coll_vault + expected_coll_tokens, mock_usdc_collateral_vault.balanceOf(wallet.address))


#############################
# 5. Nonce Management Tests #
#############################


def test_nonce_starts_at_zero(
    levg_vault_agent,
    usdc_wallet_with_funds,
):
    """Test that nonce starts at 0"""
    assert levg_vault_agent.getNonce(usdc_wallet_with_funds.address) == 0


def test_owner_increment_nonce(
    levg_vault_agent,
    usdc_wallet_with_funds,
    governance,
):
    """Test that owner can manually increment nonce"""
    wallet = usdc_wallet_with_funds

    pre_nonce = levg_vault_agent.getNonce(wallet.address)

    levg_vault_agent.incrementNonce(wallet.address, sender=governance.address)

    assert levg_vault_agent.getNonce(wallet.address) == pre_nonce + 1


def test_non_owner_cannot_increment_nonce(
    levg_vault_agent,
    usdc_wallet_with_funds,
    alice,
):
    """Test that non-owner cannot increment nonce"""
    wallet = usdc_wallet_with_funds

    with boa.reverts("no perms"):
        levg_vault_agent.incrementNonce(wallet.address, sender=alice)
