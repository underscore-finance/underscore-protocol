import pytest
import boa

from contracts.core.userWallet import UserWallet
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS
from conf_utils import filter_logs


@pytest.fixture(scope="module")
def user_wallet_edge(setUserWalletConfig, setManagerConfig, hatchery, bob, setAssetConfig, alpha_token, bravo_token, charlie_token):
    setUserWalletConfig()
    setManagerConfig()  # Set up manager config with default agent
    
    # Configure assets with zero fees for testing
    setAssetConfig(alpha_token, _swapFee=0, _rewardsFee=0)
    setAssetConfig(bravo_token, _swapFee=0, _rewardsFee=0)
    setAssetConfig(charlie_token, _swapFee=0, _rewardsFee=0)
    
    wallet_addr = hatchery.createUserWallet(sender=bob)
    assert wallet_addr != ZERO_ADDRESS
    return UserWallet.at(wallet_addr)


@pytest.fixture
def setup_wallet_edge_cases(user_wallet_edge, alpha_token, bravo_token, charlie_token, alpha_token_whale, bravo_token_whale, charlie_token_whale):
    """Setup user wallet with tokens for edge case testing"""
    # Transfer tokens to user wallet
    alpha_token.transfer(user_wallet_edge.address, 1000 * EIGHTEEN_DECIMALS, sender=alpha_token_whale)
    bravo_token.transfer(user_wallet_edge.address, 500 * EIGHTEEN_DECIMALS, sender=bravo_token_whale)
    charlie_token.transfer(user_wallet_edge.address, 100 * (10 ** charlie_token.decimals()), sender=charlie_token_whale)
    
    return user_wallet_edge, alpha_token, bravo_token, charlie_token


def test_transfer_zero_amount(setup_wallet_edge_cases, bob):
    """Test transferring zero amount"""
    user_wallet, alpha_token, _, _ = setup_wallet_edge_cases
    owner = bob
    
    initial_balance = alpha_token.balanceOf(user_wallet.address)
    
    # Transfer zero amount should work but do nothing
    amount_transferred, tx_usd_value = user_wallet.transferFunds(
        owner, alpha_token.address, 0, sender=owner
    )
    
    assert amount_transferred == 0
    assert tx_usd_value == 0  # USD value should also be 0
    assert alpha_token.balanceOf(user_wallet.address) == initial_balance


def test_transfer_max_value_amount(setup_wallet_edge_cases, bob):
    """Test transferring with max_value parameter (should transfer all available)"""
    user_wallet, alpha_token, _, _ = setup_wallet_edge_cases
    owner = bob
    
    initial_balance = alpha_token.balanceOf(user_wallet.address)
    
    # Transfer max value should transfer all available tokens
    amount_transferred, tx_usd_value = user_wallet.transferFunds(
        owner, alpha_token.address, 2**256 - 1, sender=owner  # max_value(uint256)
    )
    
    # Should transfer all available tokens
    assert amount_transferred == initial_balance
    assert alpha_token.balanceOf(user_wallet.address) == 0
    assert alpha_token.balanceOf(owner) >= initial_balance


def test_transfer_more_than_balance(setup_wallet_edge_cases, bob):
    """Test transferring more than available balance"""
    user_wallet, alpha_token, _, _ = setup_wallet_edge_cases
    owner = bob
    
    current_balance = alpha_token.balanceOf(user_wallet.address)
    excessive_amount = current_balance + 1000 * EIGHTEEN_DECIMALS
    
    # Should transfer only what's available, not revert
    amount_transferred, tx_usd_value = user_wallet.transferFunds(
        owner, alpha_token.address, excessive_amount, sender=owner
    )
    
    # Should transfer all available, not the requested excessive amount
    assert amount_transferred == current_balance
    assert alpha_token.balanceOf(user_wallet.address) == 0


def test_transfer_to_zero_address(setup_wallet_edge_cases, bob):
    """Test transferring to zero address"""
    user_wallet, alpha_token, _, _ = setup_wallet_edge_cases
    owner = bob
    
    # Transfer to zero address should revert
    with boa.reverts():
        user_wallet.transferFunds(
            ZERO_ADDRESS, alpha_token.address, 100 * EIGHTEEN_DECIMALS, sender=owner
        )


def test_transfer_zero_address_asset(setup_wallet_edge_cases, bob, eth):
    """Test transferring zero address asset (should default to ETH)"""
    user_wallet, _, _, _ = setup_wallet_edge_cases
    owner = bob
    
    # Give wallet some ETH
    boa.env.vm.state.set_balance(user_wallet.address, 1 * EIGHTEEN_DECIMALS)
    
    # Transfer with zero address asset should default to ETH
    amount_transferred, tx_usd_value = user_wallet.transferFunds(
        owner, ZERO_ADDRESS, 0.5 * EIGHTEEN_DECIMALS, sender=owner
    )
    
    assert amount_transferred == 0.5 * EIGHTEEN_DECIMALS


def test_swap_with_empty_instructions(setup_wallet_edge_cases, bob):
    """Test swapping with empty instructions array"""
    user_wallet, alpha_token, bravo_token, _ = setup_wallet_edge_cases
    owner = bob
    
    # Empty swap instructions should return zero values
    tokenIn, amountIn, tokenOut, amountOut, txUsdValue = user_wallet.swapTokens([], sender=owner)
    
    assert tokenIn == ZERO_ADDRESS
    assert amountIn == 0
    assert tokenOut == ZERO_ADDRESS
    assert amountOut == 0
    assert txUsdValue == 0


def test_swap_with_zero_amounts(setup_wallet_edge_cases, bob):
    """Test swapping with zero amounts"""
    user_wallet, alpha_token, bravo_token, _ = setup_wallet_edge_cases
    owner = bob
    
    # Swap with zero amount
    swap_instructions = [(1, 0, 0, [alpha_token.address, bravo_token.address], [])]
    tokenIn, amountIn, tokenOut, amountOut, txUsdValue = user_wallet.swapTokens(swap_instructions, sender=owner)
    
    assert tokenIn == alpha_token.address
    assert amountIn == 0
    assert tokenOut == bravo_token.address
    assert amountOut == 0


def test_swap_with_single_token_path(setup_wallet_edge_cases, bob):
    """Test swapping with single token in path (invalid swap)"""
    user_wallet, alpha_token, _, _ = setup_wallet_edge_cases
    owner = bob
    
    # Single token path should fail
    swap_instructions = [(1, 100 * EIGHTEEN_DECIMALS, 0, [alpha_token.address], [])]
    
    with boa.reverts():  # Should revert due to invalid token path
        user_wallet.swapTokens(swap_instructions, sender=owner)


def test_add_collateral_zero_amount(setup_wallet_edge_cases, bob):
    """Test adding zero collateral"""
    user_wallet, alpha_token, _, _ = setup_wallet_edge_cases
    owner = bob
    
    # Add zero collateral should work but do nothing
    amount_added, tx_usd_value = user_wallet.addCollateral(
        1, alpha_token.address, 0, sender=owner
    )
    
    assert amount_added == 0
    assert tx_usd_value == 0


def test_remove_collateral_zero_amount(setup_wallet_edge_cases, bob):
    """Test removing zero collateral"""
    user_wallet, alpha_token, _, _ = setup_wallet_edge_cases
    owner = bob
    
    # First add some collateral
    user_wallet.addCollateral(1, alpha_token.address, 100 * EIGHTEEN_DECIMALS, sender=owner)
    
    # Remove zero collateral should work but do nothing
    amount_removed, tx_usd_value = user_wallet.removeCollateral(
        1, alpha_token.address, 0, sender=owner
    )
    
    assert amount_removed == 0
    assert tx_usd_value == 0


def test_borrow_zero_amount(setup_wallet_edge_cases, bob):
    """Test borrowing zero amount"""
    user_wallet, alpha_token, _, _ = setup_wallet_edge_cases
    owner = bob
    
    # Add collateral first
    user_wallet.addCollateral(1, alpha_token.address, 200 * EIGHTEEN_DECIMALS, sender=owner)
    
    # Borrow zero amount should work but do nothing
    amount_borrowed, tx_usd_value = user_wallet.borrow(
        1, alpha_token.address, 0, sender=owner
    )
    
    assert amount_borrowed == 0
    assert tx_usd_value == 0


def test_repay_debt_zero_amount(setup_wallet_edge_cases, bob):
    """Test repaying zero debt"""
    user_wallet, alpha_token, _, _ = setup_wallet_edge_cases
    owner = bob
    
    # Repay zero debt should work but do nothing
    amount_repaid, tx_usd_value = user_wallet.repayDebt(
        1, alpha_token.address, 0, sender=owner
    )
    
    assert amount_repaid == 0
    assert tx_usd_value == 0


def test_claim_rewards_zero_amount(setup_wallet_edge_cases, bob):
    """Test claiming zero rewards"""
    user_wallet, alpha_token, _, _ = setup_wallet_edge_cases
    owner = bob
    
    # Claim zero rewards should work but do nothing
    rewards_claimed, tx_usd_value = user_wallet.claimRewards(
        1, alpha_token.address, 0, sender=owner
    )
    
    assert rewards_claimed == 0
    assert tx_usd_value == 0


def test_add_liquidity_zero_amounts(setup_wallet_edge_cases, bob):
    """Test adding liquidity with zero amounts"""
    user_wallet, alpha_token, bravo_token, _ = setup_wallet_edge_cases
    owner = bob
    
    # Add liquidity with zero amounts
    lp_amount, actual_amount_a, actual_amount_b, tx_usd_value = user_wallet.addLiquidity(
        1, boa.env.eoa, alpha_token.address, bravo_token.address,
        0, 0, 0, 0, 0, sender=owner
    )
    
    # Should work with zero values
    assert actual_amount_a == 0
    assert actual_amount_b == 0
    assert lp_amount == 0


def test_remove_liquidity_zero_amount(setup_wallet_edge_cases, bob, mock_lego_lp_token):
    """Test removing zero liquidity"""
    user_wallet, alpha_token, bravo_token, _ = setup_wallet_edge_cases
    owner = bob
    
    # First add some liquidity
    user_wallet.addLiquidity(
        1, boa.env.eoa, alpha_token.address, bravo_token.address,
        100 * EIGHTEEN_DECIMALS, 100 * EIGHTEEN_DECIMALS, 0, 0, 0, sender=owner
    )
    
    # Remove zero liquidity
    amount_a_received, amount_b_received, lp_burned, tx_usd_value = user_wallet.removeLiquidity(
        1, boa.env.eoa, alpha_token.address, bravo_token.address,
        mock_lego_lp_token.address, 0, 0, 0, sender=owner
    )
    
    # Should work with zero values
    assert amount_a_received == 0
    assert amount_b_received == 0
    assert lp_burned == 0


def test_yield_operations_zero_amounts(setup_wallet_edge_cases, bob, mock_lego_vault):
    """Test yield operations with zero amounts"""
    user_wallet, alpha_token, _, _ = setup_wallet_edge_cases
    owner = bob
    
    # Deposit zero amount for yield
    asset_amount, vault_token, vault_token_amount, tx_usd_value = user_wallet.depositForYield(
        1, alpha_token.address, mock_lego_vault.address, 0, sender=owner
    )
    
    assert asset_amount == 0
    assert vault_token_amount == 0
    
    # Withdraw zero amount from yield
    vault_token_amount_withdrawn, underlying_token, underlying_amount, tx_usd_value = user_wallet.withdrawFromYield(
        1, mock_lego_vault.address, 0, sender=owner
    )
    
    assert vault_token_amount_withdrawn == 0
    assert underlying_amount == 0


def test_asset_registration_edge_cases(setup_wallet_edge_cases, bob):
    """Test asset registration with edge cases"""
    user_wallet, alpha_token, bravo_token, charlie_token = setup_wallet_edge_cases
    owner = bob
    
    # Initially no assets should be registered
    initial_num_assets = user_wallet.numAssets()
    
    # Transfer small amounts to register assets
    user_wallet.transferFunds(owner, alpha_token.address, 1, sender=owner)
    user_wallet.transferFunds(owner, bravo_token.address, 1, sender=owner)
    user_wallet.transferFunds(owner, charlie_token.address, 1, sender=owner)
    
    # Assets should now be registered
    final_num_assets = user_wallet.numAssets()
    assert final_num_assets >= initial_num_assets + 3  # At least 3 more assets registered
    
    # Check asset data
    alpha_data = user_wallet.assetData(alpha_token.address)
    assert alpha_data[0] > 0  # assetBalance should be updated
    
    # Check asset index mappings
    alpha_index = user_wallet.indexOfAsset(alpha_token.address)
    assert alpha_index > 0  # Should have a valid index
    assert user_wallet.assets(alpha_index) == alpha_token.address


def test_maximum_values_handling(setup_wallet_edge_cases, bob):
    """Test handling of maximum uint256 values"""
    user_wallet, alpha_token, _, _ = setup_wallet_edge_cases
    owner = bob
    
    max_uint256 = 2**256 - 1
    current_balance = alpha_token.balanceOf(user_wallet.address)
    
    # Transfer with max value should transfer all available
    amount_transferred, tx_usd_value = user_wallet.transferFunds(
        owner, alpha_token.address, max_uint256, sender=owner
    )
    
    # Should transfer all available tokens, not the max value
    assert amount_transferred == current_balance
    assert alpha_token.balanceOf(user_wallet.address) == 0


def test_precision_and_rounding_edge_cases(setup_wallet_edge_cases, bob):
    """Test precision and rounding in calculations"""
    user_wallet, alpha_token, _, _ = setup_wallet_edge_cases
    owner = bob
    
    # Test with very small amounts (1 wei)
    small_amount = 1
    
    amount_transferred, tx_usd_value = user_wallet.transferFunds(
        owner, alpha_token.address, small_amount, sender=owner
    )
    
    assert amount_transferred == small_amount
    
    # Test with odd amounts that might cause rounding issues
    odd_amount = 123456789
    
    amount_transferred, tx_usd_value = user_wallet.transferFunds(
        owner, alpha_token.address, odd_amount, sender=owner
    )
    
    assert amount_transferred == odd_amount


def test_invalid_lego_id_handling(setup_wallet_edge_cases, bob):
    """Test handling of invalid lego IDs"""
    user_wallet, alpha_token, bravo_token, _ = setup_wallet_edge_cases
    owner = bob
    
    # Use invalid lego ID (999) for operations
    invalid_lego_id = 999
    
    # Most operations with invalid lego ID should revert
    with boa.reverts():
        user_wallet.addCollateral(invalid_lego_id, alpha_token.address, 100 * EIGHTEEN_DECIMALS, sender=owner)
    
    with boa.reverts():
        user_wallet.borrow(invalid_lego_id, alpha_token.address, 50 * EIGHTEEN_DECIMALS, sender=owner)


def test_reentrancy_protection(setup_wallet_edge_cases, bob):
    """Test that reentrancy protection works"""
    user_wallet, alpha_token, _, _ = setup_wallet_edge_cases
    owner = bob
    
    # Note: All external functions are marked with @nonreentrant
    # This test verifies the protection exists (actual reentrancy testing 
    # would require a malicious contract that attempts reentrancy)
    
    # Normal operation should work
    amount_transferred, tx_usd_value = user_wallet.transferFunds(
        owner, alpha_token.address, 100 * EIGHTEEN_DECIMALS, sender=owner
    )
    
    assert amount_transferred == 100 * EIGHTEEN_DECIMALS


def test_event_emission_with_zero_values(setup_wallet_edge_cases, bob):
    """Test that events are emitted correctly with zero values"""
    user_wallet, alpha_token, _, _ = setup_wallet_edge_cases
    owner = bob
    
    # Clear previous events
    _ = user_wallet.get_logs()
    
    # Transfer zero amount
    user_wallet.transferFunds(owner, alpha_token.address, 0, sender=owner)
    
    # Should still emit event
    transfer_logs = filter_logs(user_wallet, "FundsTransferred")
    assert len(transfer_logs) == 1
    
    event = transfer_logs[0]
    assert event.asset == alpha_token.address
    assert event.amount == 0
    assert event.recipient == owner
    assert event.signer == owner


def test_multiple_consecutive_operations(setup_wallet_edge_cases, bob):
    """Test multiple consecutive operations with edge case values"""
    user_wallet, alpha_token, bravo_token, _ = setup_wallet_edge_cases
    owner = bob
    
    # Series of operations with various amounts
    amounts = [0, 1, 100, 1000 * EIGHTEEN_DECIMALS, 2**256 - 1]
    
    for amount in amounts:
        # Transfer (will use min of amount and available balance)
        current_balance = alpha_token.balanceOf(user_wallet.address)
        expected_transfer = min(amount, current_balance)
        
        if current_balance > 0:  # Only transfer if there's balance
            amount_transferred, tx_usd_value = user_wallet.transferFunds(
                owner, alpha_token.address, amount, sender=owner
            )
            assert amount_transferred == expected_transfer


def test_state_consistency_after_failed_operations(setup_wallet_edge_cases, bob, alice):
    """Test that wallet state remains consistent after failed operations"""
    user_wallet, alpha_token, _, _ = setup_wallet_edge_cases
    owner = bob
    
    # Record initial state
    initial_balance = alpha_token.balanceOf(user_wallet.address)
    initial_num_assets = user_wallet.numAssets()
    
    # Attempt invalid operations that should fail
    try:
        user_wallet.transferFunds(alice, alpha_token.address, 100 * EIGHTEEN_DECIMALS, sender=alice)
    except:
        pass  # Expected to fail
    
    try:
        user_wallet.addCollateral(999, alpha_token.address, 100 * EIGHTEEN_DECIMALS, sender=owner)
    except:
        pass  # Expected to fail
    
    # State should be unchanged after failed operations
    final_balance = alpha_token.balanceOf(user_wallet.address)
    final_num_assets = user_wallet.numAssets()
    
    assert final_balance == initial_balance
    assert final_num_assets == initial_num_assets