import pytest
import boa

from contracts.core.userWallet import UserWallet
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS
from conf_utils import filter_logs


@pytest.fixture(scope="module") 
def user_wallet_cl(setUserWalletConfig, setManagerConfig, hatchery, bob, setAssetConfig, mock_yield_lego, yield_underlying_token, yield_vault_token, alpha_token, bravo_token, whale):
    setUserWalletConfig()
    setManagerConfig()  # Set up manager config with default agent
    
    # Configure assets with zero fees for testing
    setAssetConfig(yield_underlying_token, _swapFee=0, _rewardsFee=0, _legoId=2)
    setAssetConfig(yield_vault_token, _swapFee=0, _rewardsFee=0, _legoId=2)
    setAssetConfig(alpha_token, _swapFee=0, _rewardsFee=0, _legoId=2)
    setAssetConfig(bravo_token, _swapFee=0, _rewardsFee=0, _legoId=2)
    
    wallet_addr = hatchery.createUserWallet(sender=bob)
    assert wallet_addr != ZERO_ADDRESS
    return UserWallet.at(wallet_addr)


@pytest.fixture
def setup_wallet_for_cl(user_wallet_cl, mock_yield_lego, alpha_token, bravo_token, alpha_token_whale, bravo_token_whale):
    """Setup user wallet with tokens for concentrated liquidity testing"""
    # Transfer tokens to user wallet
    alpha_token.transfer(user_wallet_cl.address, 1000 * EIGHTEEN_DECIMALS, sender=alpha_token_whale)
    bravo_token.transfer(user_wallet_cl.address, 1000 * EIGHTEEN_DECIMALS, sender=bravo_token_whale)
    
    return user_wallet_cl, mock_yield_lego, alpha_token, bravo_token


def test_add_concentrated_liquidity_success(setup_wallet_for_cl, bob):
    """Test adding concentrated liquidity successfully"""
    user_wallet, mock_yield_lego, alpha_token, bravo_token = setup_wallet_for_cl
    owner = bob
    
    # Initial balances
    initial_alpha_balance = alpha_token.balanceOf(user_wallet.address)
    initial_bravo_balance = bravo_token.balanceOf(user_wallet.address)
    
    # Add concentrated liquidity
    amount_a = 100 * EIGHTEEN_DECIMALS
    amount_b = 100 * EIGHTEEN_DECIMALS
    
    # Clear previous events
    _ = user_wallet.get_logs()
    
    # Call addLiquidityConcentrated
    nft_token_id, actual_amount_a, actual_amount_b, liquidity_added, tx_usd_value = user_wallet.addLiquidityConcentrated(
        2,  # legoId for MockYieldLego
        boa.env.eoa,  # nftAddr (not used in mock)
        0,  # nftTokenId (not used for new position)
        boa.env.eoa,  # pool (not used in mock)
        alpha_token.address,  # tokenA
        bravo_token.address,  # tokenB
        amount_a,  # amountA
        amount_b,  # amountB
        500,  # tickLower
        1000,  # tickUpper
        0,  # minAmountA
        0,  # minAmountB
        sender=owner
    )
    
    # Get events
    cl_added_logs = filter_logs(user_wallet, "ConcentratedLiquidityAdded")
    
    # Verify return values
    assert actual_amount_a == amount_a
    assert actual_amount_b == amount_b
    expected_liquidity = amount_a + amount_b  # MockYieldLego returns sum
    assert liquidity_added == expected_liquidity
    assert nft_token_id > 0  # Should get a valid NFT token ID
    assert tx_usd_value > 0
    
    # Verify token balances decreased
    assert alpha_token.balanceOf(user_wallet.address) == initial_alpha_balance - amount_a
    assert bravo_token.balanceOf(user_wallet.address) == initial_bravo_balance - amount_b
    
    # Verify events
    assert len(cl_added_logs) == 1
    event = cl_added_logs[0]
    assert event.nftTokenId == nft_token_id
    assert event.pool == boa.env.eoa
    assert event.tokenA == alpha_token.address
    assert event.amountA == amount_a
    assert event.tokenB == bravo_token.address
    assert event.amountB == amount_b
    assert event.liqAdded == expected_liquidity
    assert event.legoId == 2
    assert event.signer == owner


def test_add_concentrated_liquidity_zero_amounts(setup_wallet_for_cl, bob):
    """Test adding concentrated liquidity with zero amounts"""
    user_wallet, mock_yield_lego, alpha_token, bravo_token = setup_wallet_for_cl
    owner = bob
    
    # Add liquidity with zero amounts
    nft_token_id, actual_amount_a, actual_amount_b, liquidity_added, tx_usd_value = user_wallet.addLiquidityConcentrated(
        2,  # legoId
        boa.env.eoa,  # pool
        alpha_token.address,  # tokenA
        bravo_token.address,  # tokenB
        0,  # amountA = 0
        0,  # amountB = 0
        0,  # minAmountA
        0,  # minAmountB
        0,  # minLiquidity
        500,  # tickLower
        1000,  # tickUpper
        sender=owner
    )
    
    # Should work but with zero values
    assert actual_amount_a == 0
    assert actual_amount_b == 0
    assert liquidity_added == 0
    assert nft_token_id > 0  # Still get NFT token ID


def test_add_concentrated_liquidity_insufficient_balance(setup_wallet_for_cl, bob):
    """Test adding concentrated liquidity with insufficient token balance"""
    user_wallet, mock_yield_lego, alpha_token, bravo_token = setup_wallet_for_cl
    owner = bob
    
    # Try to add more liquidity than available
    excessive_amount = 2000 * EIGHTEEN_DECIMALS  # More than the 1000 tokens available
    
    with boa.reverts():  # Should revert due to insufficient balance
        user_wallet.addLiquidityConcentrated(
            2, boa.env.eoa, alpha_token.address, bravo_token.address,
            excessive_amount, excessive_amount, 0, 0, 0, 500, 1000, sender=owner
        )


def test_remove_concentrated_liquidity_success(setup_wallet_for_cl, bob):
    """Test removing concentrated liquidity successfully"""
    user_wallet, mock_yield_lego, alpha_token, bravo_token = setup_wallet_for_cl
    owner = bob
    
    # First add concentrated liquidity
    amount_a = 200 * EIGHTEEN_DECIMALS
    amount_b = 200 * EIGHTEEN_DECIMALS
    nft_token_id, _, _, liquidity_added, _ = user_wallet.addLiquidityConcentrated(
        2, boa.env.eoa, alpha_token.address, bravo_token.address,
        amount_a, amount_b, 0, 0, 0, 500, 1000, sender=owner
    )
    
    # Initial balances after adding liquidity
    initial_alpha_balance = alpha_token.balanceOf(user_wallet.address)
    initial_bravo_balance = bravo_token.balanceOf(user_wallet.address)
    
    # Remove half the liquidity
    liquidity_to_remove = liquidity_added // 2
    
    # Clear previous events
    _ = user_wallet.get_logs()
    
    # Call removeLiquidityConcentrated
    amount_a_received, amount_b_received, liquidity_removed, tx_usd_value = user_wallet.removeLiquidityConcentrated(
        2,  # legoId
        nft_token_id,  # nftTokenId
        boa.env.eoa,  # pool
        alpha_token.address,  # tokenA
        bravo_token.address,  # tokenB
        liquidity_to_remove,  # liquidity
        0,  # minAmountA
        0,  # minAmountB
        sender=owner
    )
    
    # Get events
    cl_removed_logs = filter_logs(user_wallet, "ConcentratedLiquidityRemoved")
    
    # Verify return values
    expected_return = liquidity_to_remove // 2  # MockYieldLego returns half of liquidity to each
    assert amount_a_received == expected_return
    assert amount_b_received == expected_return
    assert liquidity_removed == liquidity_to_remove
    assert tx_usd_value > 0
    
    # Verify tokens were returned
    assert alpha_token.balanceOf(user_wallet.address) == initial_alpha_balance + expected_return
    assert bravo_token.balanceOf(user_wallet.address) == initial_bravo_balance + expected_return
    
    # Verify events
    assert len(cl_removed_logs) == 1
    event = cl_removed_logs[0]
    assert event.nftTokenId == nft_token_id
    assert event.pool == boa.env.eoa
    assert event.tokenA == alpha_token.address
    assert event.amountAReceived == expected_return
    assert event.tokenB == bravo_token.address
    assert event.amountBReceived == expected_return
    assert event.liqRemoved == liquidity_to_remove
    assert event.legoId == 2
    assert event.signer == owner


def test_remove_concentrated_liquidity_zero_amount(setup_wallet_for_cl, bob):
    """Test removing zero concentrated liquidity"""
    user_wallet, mock_yield_lego, alpha_token, bravo_token = setup_wallet_for_cl
    owner = bob
    
    # First add concentrated liquidity
    nft_token_id, _, _, _, _ = user_wallet.addLiquidityConcentrated(
        2, boa.env.eoa, alpha_token.address, bravo_token.address,
        100 * EIGHTEEN_DECIMALS, 100 * EIGHTEEN_DECIMALS, 0, 0, 0, 500, 1000, sender=owner
    )
    
    # Remove zero liquidity
    amount_a_received, amount_b_received, liquidity_removed, tx_usd_value = user_wallet.removeLiquidityConcentrated(
        2,  # legoId
        nft_token_id,  # nftTokenId
        boa.env.eoa,  # pool
        alpha_token.address,  # tokenA
        bravo_token.address,  # tokenB
        0,  # liquidity = 0
        0,  # minAmountA
        0,  # minAmountB
        sender=owner
    )
    
    # Should work but with zero values
    assert amount_a_received == 0
    assert amount_b_received == 0
    assert liquidity_removed == 0


def test_concentrated_liquidity_complete_lifecycle(setup_wallet_for_cl, bob):
    """Test complete concentrated liquidity lifecycle"""
    user_wallet, mock_yield_lego, alpha_token, bravo_token = setup_wallet_for_cl
    owner = bob
    
    # Record initial balances
    initial_alpha = alpha_token.balanceOf(user_wallet.address)
    initial_bravo = bravo_token.balanceOf(user_wallet.address)
    
    # 1. Add concentrated liquidity
    add_amount_a = 150 * EIGHTEEN_DECIMALS
    add_amount_b = 150 * EIGHTEEN_DECIMALS
    nft_token_id, _, _, total_liquidity, _ = user_wallet.addLiquidityConcentrated(
        2, boa.env.eoa, alpha_token.address, bravo_token.address,
        add_amount_a, add_amount_b, 0, 0, 0, 500, 1000, sender=owner
    )
    
    # Verify balances after add
    assert alpha_token.balanceOf(user_wallet.address) == initial_alpha - add_amount_a
    assert bravo_token.balanceOf(user_wallet.address) == initial_bravo - add_amount_b
    
    # 2. Remove all liquidity
    _, _, _, _ = user_wallet.removeLiquidityConcentrated(
        2, nft_token_id, boa.env.eoa, alpha_token.address, bravo_token.address,
        total_liquidity, 0, 0, sender=owner
    )
    
    # Verify final balances (should be close to initial, accounting for mock behavior)
    final_alpha = alpha_token.balanceOf(user_wallet.address)
    final_bravo = bravo_token.balanceOf(user_wallet.address)
    
    # In MockYieldLego, removing liquidity returns half of liquidity amount to each token
    expected_return_each = total_liquidity // 2
    assert final_alpha == initial_alpha - add_amount_a + expected_return_each
    assert final_bravo == initial_bravo - add_amount_b + expected_return_each


def test_concentrated_liquidity_with_different_tick_ranges(setup_wallet_for_cl, bob):
    """Test concentrated liquidity with different tick ranges"""
    user_wallet, mock_yield_lego, alpha_token, bravo_token = setup_wallet_for_cl
    owner = bob
    
    # Test different tick ranges
    tick_ranges = [
        (100, 200),   # Narrow range
        (0, 1000),    # Wide range
        (-500, 500),  # Symmetric range
    ]
    
    for tick_lower, tick_upper in tick_ranges:
        nft_token_id, _, _, _, _ = user_wallet.addLiquidityConcentrated(
            2, boa.env.eoa, alpha_token.address, bravo_token.address,
            50 * EIGHTEEN_DECIMALS, 50 * EIGHTEEN_DECIMALS, 0, 0, 0,
            tick_lower, tick_upper, sender=owner
        )
        
        # Should succeed with any tick range
        assert nft_token_id > 0


def test_concentrated_liquidity_unauthorized_caller(setup_wallet_for_cl, alice):
    """Test concentrated liquidity operations with unauthorized caller"""
    user_wallet, mock_yield_lego, alpha_token, bravo_token = setup_wallet_for_cl
    unauthorized_user = alice
    
    # Alice should not be able to add liquidity to Bob's wallet
    with boa.reverts():  # Should revert due to unauthorized access
        user_wallet.addLiquidityConcentrated(
            2, boa.env.eoa, alpha_token.address, bravo_token.address,
            100 * EIGHTEEN_DECIMALS, 100 * EIGHTEEN_DECIMALS, 0, 0, 0, 500, 1000,
            sender=unauthorized_user
        )


def test_multiple_concentrated_liquidity_positions(setup_wallet_for_cl, bob):
    """Test managing multiple concentrated liquidity positions"""
    user_wallet, mock_yield_lego, alpha_token, bravo_token = setup_wallet_for_cl
    owner = bob
    
    # Create multiple positions
    positions = []
    for i in range(3):
        nft_token_id, _, _, liquidity, _ = user_wallet.addLiquidityConcentrated(
            2, boa.env.eoa, alpha_token.address, bravo_token.address,
            (50 + i * 10) * EIGHTEEN_DECIMALS, (50 + i * 10) * EIGHTEEN_DECIMALS,
            0, 0, 0, 500 + i * 100, 1000 + i * 100, sender=owner
        )
        positions.append((nft_token_id, liquidity))
    
    # Remove positions in reverse order
    for nft_token_id, liquidity in reversed(positions):
        _, _, _, _ = user_wallet.removeLiquidityConcentrated(
            2, nft_token_id, boa.env.eoa, alpha_token.address, bravo_token.address,
            liquidity, 0, 0, sender=owner
        )
    
    # All operations should complete successfully
    assert True


def test_concentrated_liquidity_events_comprehensive(setup_wallet_for_cl, bob):
    """Test comprehensive event emission for concentrated liquidity"""
    user_wallet, mock_yield_lego, alpha_token, bravo_token = setup_wallet_for_cl
    owner = bob
    
    # Clear existing events
    _ = user_wallet.get_logs()
    
    # Add liquidity
    amount_a = 80 * EIGHTEEN_DECIMALS
    amount_b = 80 * EIGHTEEN_DECIMALS
    tick_lower = 200
    tick_upper = 800
    
    nft_token_id, _, _, liquidity_added, tx_usd_value_add = user_wallet.addLiquidityConcentrated(
        2, boa.env.eoa, alpha_token.address, bravo_token.address,
        amount_a, amount_b, 0, 0, 0, tick_lower, tick_upper, sender=owner
    )
    
    # Verify add event
    add_logs = filter_logs(user_wallet, "ConcentratedLiquidityAdded")
    assert len(add_logs) == 1
    add_event = add_logs[0]
    assert add_event.nftTokenId == nft_token_id
    assert add_event.pool == boa.env.eoa
    assert add_event.tokenA == alpha_token.address
    assert add_event.amountA == amount_a
    assert add_event.tokenB == bravo_token.address
    assert add_event.amountB == amount_b
    assert add_event.txUsdValue == tx_usd_value_add
    assert add_event.liqAdded == liquidity_added
    assert add_event.legoId == 2
    assert add_event.signer == owner
    
    # Clear events before remove
    _ = user_wallet.get_logs()
    
    # Remove liquidity
    _, _, _, tx_usd_value_remove = user_wallet.removeLiquidityConcentrated(
        2, nft_token_id, boa.env.eoa, alpha_token.address, bravo_token.address,
        liquidity_added, 0, 0, sender=owner
    )
    
    # Verify remove event
    remove_logs = filter_logs(user_wallet, "ConcentratedLiquidityRemoved")
    assert len(remove_logs) == 1
    remove_event = remove_logs[0]
    assert remove_event.nftTokenId == nft_token_id
    assert remove_event.pool == boa.env.eoa
    assert remove_event.tokenA == alpha_token.address
    assert remove_event.tokenB == bravo_token.address
    assert remove_event.txUsdValue == tx_usd_value_remove
    assert remove_event.liqRemoved == liquidity_added
    assert remove_event.legoId == 2
    assert remove_event.signer == owner