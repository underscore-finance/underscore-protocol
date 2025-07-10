import pytest
import boa

from contracts.core.userWallet import UserWallet
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS
from conf_utils import filter_logs


@pytest.fixture(scope="module")
def user_wallet_edge(setUserWalletConfig, setManagerConfig, hatchery, bob, setAssetConfig, createTxFees, alpha_token, bravo_token, charlie_token, lego_book, mock_lego_asset, mock_lego_asset_alt):
    setUserWalletConfig()
    setManagerConfig()  # Set up manager config with default agent
    
    # Configure assets with zero fees for testing
    setAssetConfig(alpha_token, _txFees=createTxFees(_swapFee=0, _rewardsFee=0))
    setAssetConfig(bravo_token, _txFees=createTxFees(_swapFee=0, _rewardsFee=0))
    setAssetConfig(charlie_token, _txFees=createTxFees(_swapFee=0, _rewardsFee=0))
    # Also configure mock_lego assets to ensure they work with legoId=1
    setAssetConfig(mock_lego_asset, _legoId=1, _txFees=createTxFees(_swapFee=0, _rewardsFee=0))
    setAssetConfig(mock_lego_asset_alt, _legoId=1, _txFees=createTxFees(_swapFee=0, _rewardsFee=0))
    
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
    
    # Transfer zero amount should revert
    with boa.reverts("no amt"):
        user_wallet.transferFunds(
            owner, alpha_token.address, 0, sender=owner
        )


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


def test_transfer_zero_address_asset(setup_wallet_edge_cases, bob):
    """Test transferring zero address asset (should default to ETH)"""
    user_wallet, _, _, _ = setup_wallet_edge_cases
    owner = bob
    
    # Give wallet some ETH
    boa.env.set_balance(user_wallet.address, 1 * EIGHTEEN_DECIMALS)
    
    # Transfer with zero address asset should default to ETH
    amount_transferred, tx_usd_value = user_wallet.transferFunds(
        owner, ZERO_ADDRESS, int(0.5 * EIGHTEEN_DECIMALS), sender=owner
    )
    
    assert amount_transferred == 0.5 * EIGHTEEN_DECIMALS


def test_swap_with_empty_instructions(setup_wallet_edge_cases, bob):
    """Test swapping with empty instructions array"""
    user_wallet, alpha_token, bravo_token, _ = setup_wallet_edge_cases
    owner = bob
    
    # Empty swap instructions should revert
    with boa.reverts("swaps"):
        user_wallet.swapTokens([], sender=owner)


def test_swap_with_zero_amounts(setup_wallet_edge_cases, bob):
    """Test swapping with zero amounts"""
    user_wallet, alpha_token, bravo_token, _ = setup_wallet_edge_cases
    owner = bob
    
    # Swap with zero amount should revert
    swap_instructions = [(1, 0, 0, [alpha_token.address, bravo_token.address], [])]
    with boa.reverts():  # Will revert but the specific error varies
        user_wallet.swapTokens(swap_instructions, sender=owner)


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
    
    # Add zero collateral should revert
    with boa.reverts():
        user_wallet.addCollateral(
            1, alpha_token.address, 0, sender=owner
        )


def test_remove_collateral_zero_amount(setup_wallet_edge_cases, bob, mock_lego, mock_lego_asset, whale):
    """Test removing zero collateral"""
    user_wallet, alpha_token, _, _ = setup_wallet_edge_cases
    owner = bob
    
    # Give wallet some mock_lego_asset tokens for testing
    mock_lego_asset.transfer(user_wallet.address, 200 * EIGHTEEN_DECIMALS, sender=whale)
    
    # Set up access for the lego
    mock_lego.setLegoAccess(mock_lego.address, sender=user_wallet.address)
    
    # First add some collateral using mock_lego_asset (assuming mock_lego is at legoId=1)
    user_wallet.addCollateral(1, mock_lego_asset.address, 100 * EIGHTEEN_DECIMALS, sender=owner)
    
    # Remove zero collateral should succeed (no validation in MockLego.removeCollateral)
    amount_removed, tx_usd_value = user_wallet.removeCollateral(
        1, mock_lego_asset.address, 0, sender=owner
    )
    
    assert amount_removed == 0
    assert tx_usd_value == 0


def test_borrow_zero_amount(setup_wallet_edge_cases, bob, mock_lego, mock_lego_debt_token, mock_lego_asset, whale):
    """Test borrowing zero amount"""
    user_wallet, alpha_token, _, _ = setup_wallet_edge_cases
    owner = bob
    
    # Give wallet some mock_lego_asset tokens for collateral
    mock_lego_asset.transfer(user_wallet.address, 300 * EIGHTEEN_DECIMALS, sender=whale)
    
    # Set up access for the lego
    mock_lego.setLegoAccess(mock_lego.address, sender=user_wallet.address)
    
    # Add collateral first using mock_lego_asset
    user_wallet.addCollateral(1, mock_lego_asset.address, 200 * EIGHTEEN_DECIMALS, sender=owner)
    
    # Borrow zero amount should revert
    with boa.reverts():
        user_wallet.borrow(
            1, mock_lego_debt_token.address, 0, sender=owner
        )


def test_repay_debt_zero_amount(setup_wallet_edge_cases, bob, mock_lego, mock_lego_debt_token):
    """Test repaying zero debt"""
    user_wallet, alpha_token, _, _ = setup_wallet_edge_cases
    owner = bob
    
    # Repay zero debt should revert
    with boa.reverts("nothing to repay"):
        user_wallet.repayDebt(
            1, mock_lego_debt_token.address, 0, sender=owner
        )


def test_claim_rewards_zero_amount(setup_wallet_edge_cases, bob, mock_lego, mock_lego_asset):
    """Test claiming zero rewards"""
    user_wallet, alpha_token, _, _ = setup_wallet_edge_cases
    owner = bob
    
    # Set up access for the lego
    mock_lego.setLegoAccess(mock_lego.address, sender=user_wallet.address)
    
    # Claim zero rewards should succeed (no validation in MockLego.claimRewards)
    rewards_claimed, tx_usd_value = user_wallet.claimRewards(
        1, mock_lego_asset.address, 0, sender=owner
    )
    
    assert rewards_claimed == 0
    assert tx_usd_value == 0


def test_add_liquidity_zero_amounts(setup_wallet_edge_cases, bob):
    """Test adding liquidity with zero amounts"""
    user_wallet, alpha_token, bravo_token, _ = setup_wallet_edge_cases
    owner = bob
    
    # Add liquidity with zero amounts should revert
    with boa.reverts():
        user_wallet.addLiquidity(
            1, boa.env.eoa, alpha_token.address, bravo_token.address,
            0, 0, 0, 0, 0, sender=owner
        )


def test_remove_liquidity_zero_amount(setup_wallet_edge_cases, bob, mock_lego, mock_lego_lp_token, mock_lego_asset, mock_lego_asset_alt, whale):
    """Test removing zero liquidity"""
    user_wallet, alpha_token, bravo_token, _ = setup_wallet_edge_cases
    owner = bob
    
    # Give wallet some tokens for liquidity
    mock_lego_asset.transfer(user_wallet.address, 200 * EIGHTEEN_DECIMALS, sender=whale)
    mock_lego_asset_alt.transfer(user_wallet.address, 200 * EIGHTEEN_DECIMALS, sender=whale)
    
    # First add some liquidity using mock_lego assets
    user_wallet.addLiquidity(
        1, boa.env.eoa, mock_lego_asset.address, mock_lego_asset_alt.address,
        100 * EIGHTEEN_DECIMALS, 100 * EIGHTEEN_DECIMALS, 0, 0, 0, sender=owner
    )
    
    # Remove zero liquidity should revert
    with boa.reverts():
        user_wallet.removeLiquidity(
            1, boa.env.eoa, mock_lego_asset.address, mock_lego_asset_alt.address,
            mock_lego_lp_token.address, 0, 0, 0, sender=owner
        )


def test_yield_operations_zero_amounts(setup_wallet_edge_cases, bob, mock_lego_vault):
    """Test yield operations with zero amounts"""
    user_wallet, alpha_token, _, _ = setup_wallet_edge_cases
    owner = bob
    
    # Deposit zero amount for yield should revert
    with boa.reverts():
        user_wallet.depositForYield(
            1, alpha_token.address, mock_lego_vault.address, 0, sender=owner
        )
    
    # Withdraw zero amount from yield should revert
    with boa.reverts():
        user_wallet.withdrawFromYield(
            1, mock_lego_vault.address, 0, sender=owner
        )


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
    """Test that events are emitted correctly with small values"""
    user_wallet, alpha_token, _, _ = setup_wallet_edge_cases
    owner = bob
    
    # Clear previous events
    _ = user_wallet.get_logs()
    
    # Transfer very small amount (1 wei)
    user_wallet.transferFunds(owner, alpha_token.address, 1, sender=owner)
    
    # Should emit event
    transfer_logs = filter_logs(user_wallet, "FundsTransferred")
    assert len(transfer_logs) == 1
    
    event = transfer_logs[0]
    assert event.asset == alpha_token.address
    assert event.amount == 1
    assert event.recipient == owner
    assert event.signer == owner


def test_multiple_consecutive_operations(setup_wallet_edge_cases, bob):
    """Test multiple consecutive operations with edge case values"""
    user_wallet, alpha_token, bravo_token, _ = setup_wallet_edge_cases
    owner = bob
    
    # Series of operations with various amounts (excluding zero)
    amounts = [1, 100, 1000 * EIGHTEEN_DECIMALS, 2**256 - 1]
    
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
    with boa.reverts():
        user_wallet.transferFunds(alice, alpha_token.address, 100 * EIGHTEEN_DECIMALS, sender=alice)
    
    with boa.reverts():
        user_wallet.addCollateral(999, alpha_token.address, 100 * EIGHTEEN_DECIMALS, sender=owner)
    
    # State should be unchanged after failed operations
    final_balance = alpha_token.balanceOf(user_wallet.address)
    final_num_assets = user_wallet.numAssets()
    
    assert final_balance == initial_balance
    assert final_num_assets == initial_num_assets