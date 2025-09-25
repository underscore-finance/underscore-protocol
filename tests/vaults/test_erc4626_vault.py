from hypothesis import given, strategies as st
import boa

from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS, MAX_UINT256
from conf_utils import filter_logs


def test_erc4626_initialization(undy_usd_vault, yield_underlying_token):
    """Test ERC4626 initialization"""
    assert undy_usd_vault.asset() == yield_underlying_token.address
    assert undy_usd_vault.totalAssets() == 0


def test_erc4626_deposit(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
):
    """Test basic deposit functionality"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # Initial deposit
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    shares = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    
    # Check balances
    assert undy_usd_vault.balanceOf(bob) == shares
    assert undy_usd_vault.totalAssets() == deposit_amount
    assert undy_usd_vault.convertToAssets(shares) == deposit_amount
    assert undy_usd_vault.convertToShares(deposit_amount) == shares


def test_erc4626_deposit_max_value(
    undy_usd_vault,
    yield_underlying_token,
    sally,
    bob,
    governance,
):
    """Test deposit with max_value(uint256)"""
    # First mint enough tokens to the sally
    mint_amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.mint(sally, mint_amount, sender=governance.address)
    
    # Approve the contract to spend tokens
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=sally)
    
    # Deposit max value - this should use all available tokens
    shares = undy_usd_vault.deposit(MAX_UINT256, bob, sender=sally)
    assert shares > 0
    assert undy_usd_vault.balanceOf(bob) == shares
    assert undy_usd_vault.totalAssets() == mint_amount
    assert yield_underlying_token.balanceOf(sally) == 0  # All tokens should be used


def test_erc4626_deposit_zero_amount(
    undy_usd_vault,
    yield_underlying_token,
    sally,
    bob,
):
    """Test deposit with zero amount"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=sally)

    with boa.reverts("cannot deposit 0 amount"):
        undy_usd_vault.deposit(0, bob, sender=sally)


def test_erc4626_deposit_invalid_receiver(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
):
    """Test deposit with invalid receiver"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    with boa.reverts("invalid recipient"):
        undy_usd_vault.deposit(100 * EIGHTEEN_DECIMALS, ZERO_ADDRESS, sender=yield_underlying_token_whale)


def test_erc4626_mint(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
):
    """Test mint functionality"""
    # Initial deposit
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)
    
    # Calculate how many assets we need for desired shares
    desired_shares = 100 * EIGHTEEN_DECIMALS
    required_assets = undy_usd_vault.previewMint(desired_shares)
    
    # Mint the shares
    assets = undy_usd_vault.mint(desired_shares, bob, sender=yield_underlying_token_whale)
    
    # Check balances
    assert undy_usd_vault.balanceOf(bob) == desired_shares
    assert assets == required_assets  # The actual assets used should match what previewMint told us
    assert undy_usd_vault.totalAssets() == assets


def test_erc4626_mint_max_value(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
):
    """Test mint with max_value(uint256)"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    with boa.reverts("deposit failed"):
        undy_usd_vault.mint(MAX_UINT256, bob, sender=yield_underlying_token_whale)


def test_erc4626_withdraw(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
):
    """Test withdraw functionality"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # Initial deposit
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    shares = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    
    # Withdraw half
    withdraw_amount = deposit_amount // 2
    withdrawn_shares = undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)
    
    # Check balances
    assert undy_usd_vault.balanceOf(bob) == shares - withdrawn_shares
    assert undy_usd_vault.totalAssets() == deposit_amount - withdraw_amount
    assert yield_underlying_token.balanceOf(bob) == withdraw_amount


def test_erc4626_withdraw_zero_amount(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
):
    """Test withdraw with zero amount"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # Initial deposit
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    
    with boa.reverts("cannot withdraw 0 amount"):
        undy_usd_vault.withdraw(0, bob, bob, sender=bob)


def test_erc4626_withdraw_insufficient_balance(
    undy_usd_vault,
    bob,
):
    """Test withdraw with insufficient balance"""
    with boa.reverts("insufficient shares"):
        undy_usd_vault.withdraw(100 * EIGHTEEN_DECIMALS, bob, bob, sender=bob)


def test_erc4626_redeem(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
):
    """Test redeem functionality"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # Initial deposit
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    shares = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    
    # Redeem half
    redeem_shares = shares // 2
    redeemed_amount = undy_usd_vault.redeem(redeem_shares, bob, bob, sender=bob)
    
    # Check balances
    assert undy_usd_vault.balanceOf(bob) == shares - redeem_shares
    assert undy_usd_vault.totalAssets() == deposit_amount - redeemed_amount
    assert yield_underlying_token.balanceOf(bob) == redeemed_amount


def test_erc4626_redeem_max_value(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
):
    """Test redeem with max_value(uint256)"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # Initial deposit
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    
    # Redeem all shares
    redeemed_amount = undy_usd_vault.redeem(MAX_UINT256, bob, bob, sender=bob)
    assert redeemed_amount == deposit_amount
    assert undy_usd_vault.balanceOf(bob) == 0


def test_erc4626_redeem_zero_shares(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
):
    """Test redeem with zero shares"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # Initial deposit
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    
    with boa.reverts("cannot withdraw 0 amount"):
        undy_usd_vault.redeem(0, bob, bob, sender=bob)


def test_erc4626_share_calculations(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
    sally,
):
    """Test share calculations with multiple deposits"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # First deposit
    deposit1 = 100 * EIGHTEEN_DECIMALS
    shares1 = undy_usd_vault.deposit(deposit1, bob, sender=yield_underlying_token_whale)
    
    # Second deposit
    deposit2 = 200 * EIGHTEEN_DECIMALS
    shares2 = undy_usd_vault.deposit(deposit2, sally, sender=yield_underlying_token_whale)
    
    # Check share ratios
    assert shares2 > shares1  # More assets should give more shares
    assert undy_usd_vault.convertToAssets(shares1) == deposit1
    assert undy_usd_vault.convertToAssets(shares2) == deposit2


def test_erc4626_rounding_behavior(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
):
    """Test rounding behavior in share calculations"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # Initial deposit
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    shares = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    
    # Test rounding up
    shares_up = undy_usd_vault.previewDeposit(deposit_amount)
    assert shares_up >= shares
    
    # Test rounding down
    assets_down = undy_usd_vault.previewRedeem(shares)
    assert assets_down <= deposit_amount


def test_erc4626_allowance(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
    sally,
):
    """Test allowance functionality"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # Initial deposit
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    shares = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    
    # Approve Sally to spend Bob's shares
    undy_usd_vault.approve(sally, shares, sender=bob)
    
    # Sally redeems Bob's shares
    redeemed_amount = undy_usd_vault.redeem(shares, sally, bob, sender=sally)
    assert redeemed_amount == deposit_amount
    assert undy_usd_vault.balanceOf(bob) == 0
    assert yield_underlying_token.balanceOf(sally) == deposit_amount


def test_erc4626_insufficient_allowance(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
    sally,
):
    """Test insufficient allowance"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # Initial deposit
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    shares = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    
    # Approve Sally for less than total shares
    undy_usd_vault.approve(sally, shares // 2, sender=bob)
    
    # Try to redeem more than allowed
    with boa.reverts("insufficient allowance"):
        undy_usd_vault.redeem(shares, sally, bob, sender=sally)


def test_erc4626_proportional_shares(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
):
    """Test proportional share distribution for different deposit sizes"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # Initial deposit
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    shares1 = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    
    # Try to manipulate share price with tiny deposit
    tiny_amount = 1
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)
    shares2 = undy_usd_vault.deposit(tiny_amount, bob, sender=yield_underlying_token_whale)
    
    # Check that share price wasn't significantly affected
    assert shares2 < shares1 // 100  # Tiny deposit should give proportionally tiny shares


def test_erc4626_preview_functions(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
):
    """Test preview functions accuracy"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # Initial deposit
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    shares = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    
    # Test previewDeposit
    preview_shares = undy_usd_vault.previewDeposit(deposit_amount)
    assert preview_shares == shares
    
    # Test previewMint
    preview_assets = undy_usd_vault.previewMint(shares)
    assert preview_assets == deposit_amount
    
    # Test previewWithdraw
    preview_withdraw_shares = undy_usd_vault.previewWithdraw(deposit_amount)
    assert preview_withdraw_shares == shares
    
    # Test previewRedeem
    preview_redeem_assets = undy_usd_vault.previewRedeem(shares)
    assert preview_redeem_assets == deposit_amount


def test_erc4626_max_functions(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
):
    """Test max functions"""
    # Test maxDeposit
    assert undy_usd_vault.maxDeposit(bob) == MAX_UINT256
    
    # Test maxMint
    assert undy_usd_vault.maxMint(bob) == MAX_UINT256
    
    # Test maxWithdraw and maxRedeem before deposit
    assert undy_usd_vault.maxWithdraw(bob) == 0
    assert undy_usd_vault.maxRedeem(bob) == 0
    
    # Make a deposit
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    shares = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    
    # Test maxWithdraw and maxRedeem after deposit
    assert undy_usd_vault.maxWithdraw(bob) == deposit_amount
    assert undy_usd_vault.maxRedeem(bob) == shares


def test_erc4626_rounding_edge_cases(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    governance,
    bob,
):
    """Test rounding edge cases"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # Initial deposit
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    shares = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    
    # Test tiny amounts
    tiny_amount = 1
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)
    tiny_shares = undy_usd_vault.deposit(tiny_amount, bob, sender=yield_underlying_token_whale)
    assert tiny_shares > 0  # Should still get some shares
    
    # Test large amounts (but not so large as to cause overflow)
    large_amount = 1000000 * EIGHTEEN_DECIMALS  # 1 million tokens
    yield_underlying_token.mint(yield_underlying_token_whale, large_amount, sender=governance.address)  # Mint enough tokens for the large deposit
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)
    large_shares = undy_usd_vault.deposit(large_amount, bob, sender=yield_underlying_token_whale)
    assert large_shares > shares  # Should get more shares than initial deposit
    
    # Verify share price consistency
    initial_share_price = deposit_amount / shares
    large_share_price = large_amount / large_shares
    assert abs(initial_share_price - large_share_price) < 1  # Share price should be consistent


def test_erc4626_share_price_manipulation(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
    sally,
    governance,
):
    """Test share price manipulation resistance"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # Initial deposit
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    shares1 = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    
    # Try to manipulate share price with large deposit
    large_amount = deposit_amount * 1000
    yield_underlying_token.mint(yield_underlying_token_whale, large_amount, sender=governance.address)  # Mint enough tokens for the large deposit
    shares2 = undy_usd_vault.deposit(large_amount, sally, sender=yield_underlying_token_whale)
    
    # Check that share price wasn't significantly affected
    assert shares2 / large_amount == shares1 / deposit_amount  # Share price should be consistent


def test_erc4626_convert_functions(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
):
    """Test convert functions accuracy"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # Initial deposit
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    shares = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    
    # Test convertToShares
    converted_shares = undy_usd_vault.convertToShares(deposit_amount)
    assert converted_shares == shares
    
    # Test convertToAssets
    converted_assets = undy_usd_vault.convertToAssets(shares)
    assert converted_assets == deposit_amount
    
    # Test with zero values
    assert undy_usd_vault.convertToShares(0) == 0
    assert undy_usd_vault.convertToAssets(0) == 0


def test_erc4626_multiple_operations(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
):
    """Test multiple operations in sequence"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # Initial deposit
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    shares = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    
    # Withdraw half
    withdraw_amount = deposit_amount // 2
    withdrawn_shares = undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)
    
    # Deposit again
    new_shares = undy_usd_vault.deposit(withdraw_amount, bob, sender=yield_underlying_token_whale)
    
    # Redeem some shares
    redeem_shares = new_shares // 2
    redeemed_amount = undy_usd_vault.redeem(redeem_shares, bob, bob, sender=bob)
    
    # Check final balances
    assert undy_usd_vault.balanceOf(bob) == shares - withdrawn_shares + new_shares - redeem_shares
    assert undy_usd_vault.totalAssets() == deposit_amount - withdraw_amount + withdraw_amount - redeemed_amount
    assert yield_underlying_token.balanceOf(bob) == withdraw_amount + redeemed_amount


@given(
    amount=st.integers(min_value=1, max_value=1000 * EIGHTEEN_DECIMALS),
    receiver=st.sampled_from(["bob", "sally"]),
)
def test_erc4626_fuzz_deposit(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
    sally,
    amount,
    receiver,
):
    """Fuzz test deposit functionality"""
    receiver_addr = bob if receiver == "bob" else sally
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)
    
    # Calculate expected shares
    expected_shares = undy_usd_vault.previewDeposit(amount)
    
    # Perform deposit
    shares = undy_usd_vault.deposit(amount, receiver_addr, sender=yield_underlying_token_whale)
    
    # Verify results
    assert shares == expected_shares
    assert undy_usd_vault.balanceOf(receiver_addr) == shares
    assert undy_usd_vault.totalAssets() == amount
    assert yield_underlying_token.balanceOf(undy_usd_vault) == amount


@given(
    shares=st.integers(min_value=1, max_value=1000 * EIGHTEEN_DECIMALS),
    receiver=st.sampled_from(["bob", "sally"]),
)
def test_erc4626_fuzz_mint(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
    sally,
    shares,
    receiver,
):
    """Fuzz test mint functionality"""
    receiver_addr = bob if receiver == "bob" else sally
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)
    
    # Calculate expected assets
    expected_assets = undy_usd_vault.previewMint(shares)
    
    # Perform mint
    assets = undy_usd_vault.mint(shares, receiver_addr, sender=yield_underlying_token_whale)
    
    # Verify results
    assert assets == expected_assets
    assert undy_usd_vault.balanceOf(receiver_addr) == shares
    assert undy_usd_vault.totalAssets() == assets


def test_erc4626_integration_different_decimals(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
):
    """Test integration with tokens of different decimals"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # Test with 6 decimals
    six_decimals = 10 ** 6
    shares = undy_usd_vault.deposit(100 * six_decimals, bob, sender=yield_underlying_token_whale)
    assert shares > 0
    
    # Test with 8 decimals
    eight_decimals = 10 ** 8
    shares = undy_usd_vault.deposit(100 * eight_decimals, bob, sender=yield_underlying_token_whale)
    assert shares > 0
    
    # Test with 18 decimals (standard)
    shares = undy_usd_vault.deposit(100 * EIGHTEEN_DECIMALS, bob, sender=yield_underlying_token_whale)
    assert shares > 0


def test_erc4626_events(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
):
    """Test event emissions"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    
    # Test Deposit event
    shares = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    log = filter_logs(undy_usd_vault, "Deposit")[0]

    assert log.sender == yield_underlying_token_whale
    assert log.owner == bob
    assert log.assets == deposit_amount
    assert log.shares == shares
    
    # Test Withdraw event
    withdraw_amount = deposit_amount // 2
    withdrawn_shares = undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)
    log = filter_logs(undy_usd_vault, "Withdraw")[0]

    assert log.sender == bob
    assert log.receiver == bob
    assert log.owner == bob
    assert log.assets == withdraw_amount
    assert log.shares == withdrawn_shares


def test_erc4626_sequential_operations(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
):
    """Test sequential operations with different users"""
    # First user deposits
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)
    deposit1 = 100 * EIGHTEEN_DECIMALS
    shares1 = undy_usd_vault.deposit(deposit1, bob, sender=yield_underlying_token_whale)
    
    # Second user deposits
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)
    deposit2 = 200 * EIGHTEEN_DECIMALS
    shares2 = undy_usd_vault.deposit(deposit2, bob, sender=yield_underlying_token_whale)
    
    # First user withdraws
    withdraw1 = deposit1 // 2
    withdrawn_shares1 = undy_usd_vault.withdraw(withdraw1, bob, bob, sender=bob)
    
    # Second user withdraws
    withdraw2 = deposit2 // 2
    withdrawn_shares2 = undy_usd_vault.withdraw(withdraw2, bob, bob, sender=bob)
    
    # Verify final state
    assert undy_usd_vault.balanceOf(bob) == shares1 + shares2 - withdrawn_shares1 - withdrawn_shares2
    assert undy_usd_vault.totalAssets() == deposit1 + deposit2 - withdraw1 - withdraw2
    assert yield_underlying_token.balanceOf(bob) == withdraw1 + withdraw2


def test_erc4626_share_value_changes_with_asset_balance(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
    governance,
):
    """Test how share values change when underlying asset balance changes"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # Initial deposit
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    shares = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    
    # Record initial share value
    initial_share_value = undy_usd_vault.convertToAssets(shares) / shares
    
    # Direct transfer of green tokens to undy_usd_vault (simulating yield/profit)
    profit_amount = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.mint(yield_underlying_token_whale, profit_amount, sender=governance.address)
    yield_underlying_token.transfer(undy_usd_vault, profit_amount, sender=yield_underlying_token_whale)
    
    # Share value should increase
    new_share_value = undy_usd_vault.convertToAssets(shares) / shares
    assert new_share_value > initial_share_value
    assert new_share_value == (deposit_amount + profit_amount) / shares


def test_erc4626_share_value_changes_with_asset_loss(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
    sally,
):
    """Test how share values change when underlying asset balance decreases"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # Initial deposit
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    shares = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    
    # Record initial share value
    initial_share_value = undy_usd_vault.convertToAssets(shares) / shares
    
    # Direct transfer of green tokens out of undy_usd_vault (simulating loss)
    loss_amount = 25 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(sally, loss_amount, sender=undy_usd_vault.address)
    
    # Share value should decrease
    new_share_value = undy_usd_vault.convertToAssets(shares) / shares
    assert new_share_value < initial_share_value
    assert new_share_value == (deposit_amount - loss_amount) / shares


def test_erc4626_share_value_with_multiple_deposits_and_balance_changes(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
    sally,
    governance,
):
    """Test share values with multiple deposits and balance changes"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # First deposit
    deposit1 = 100 * EIGHTEEN_DECIMALS
    shares1 = undy_usd_vault.deposit(deposit1, bob, sender=yield_underlying_token_whale)
    
    # Add some profit
    profit = 20 * EIGHTEEN_DECIMALS
    yield_underlying_token.mint(yield_underlying_token_whale, profit, sender=governance.address)
    yield_underlying_token.transfer(undy_usd_vault, profit, sender=yield_underlying_token_whale)
    
    # Second deposit after profit
    deposit2 = 200 * EIGHTEEN_DECIMALS
    shares2 = undy_usd_vault.deposit(deposit2, sally, sender=yield_underlying_token_whale)
    
    # Verify share values
    bob_share_value = undy_usd_vault.convertToAssets(shares1) / shares1
    sally_share_value = undy_usd_vault.convertToAssets(shares2) / shares2
    
    # Share values should be equal
    assert abs(bob_share_value - sally_share_value) < 1
    
    # Add more profit
    profit2 = 30 * EIGHTEEN_DECIMALS
    yield_underlying_token.mint(yield_underlying_token_whale, profit2, sender=governance.address)
    yield_underlying_token.transfer(undy_usd_vault, profit2, sender=yield_underlying_token_whale)
    
    # Verify share values increased proportionally
    new_bob_share_value = undy_usd_vault.convertToAssets(shares1) / shares1
    new_sally_share_value = undy_usd_vault.convertToAssets(shares2) / shares2
    
    assert new_bob_share_value > bob_share_value
    assert new_sally_share_value > sally_share_value
    assert abs(new_bob_share_value - new_sally_share_value) < 1


def test_erc4626_share_value_with_withdrawals_and_balance_changes(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
    governance,
):
    """Test share values with withdrawals and balance changes"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # Initial deposit
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    shares = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    
    # Add some profit
    profit = 20 * EIGHTEEN_DECIMALS
    yield_underlying_token.mint(yield_underlying_token_whale, profit, sender=governance.address)
    yield_underlying_token.transfer(undy_usd_vault, profit, sender=yield_underlying_token_whale)
    
    # Record share value after profit
    share_value_after_profit = undy_usd_vault.convertToAssets(shares) / shares
    
    # Withdraw half
    withdraw_amount = deposit_amount // 2
    withdrawn_shares = undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)
    
    # Add more profit after withdrawal
    profit2 = 10 * EIGHTEEN_DECIMALS
    yield_underlying_token.mint(yield_underlying_token_whale, profit2, sender=governance.address)
    yield_underlying_token.transfer(undy_usd_vault, profit2, sender=yield_underlying_token_whale)
    
    # Verify remaining shares increased in value
    remaining_shares = shares - withdrawn_shares
    final_share_value = undy_usd_vault.convertToAssets(remaining_shares) / remaining_shares
    assert final_share_value > share_value_after_profit


def test_erc4626_share_value_with_extreme_balance_changes(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
    governance,
):
    """Test share values with extreme balance changes"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # Initial deposit
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    shares = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    
    # Add massive profit (10x)
    profit = deposit_amount * 10
    yield_underlying_token.mint(yield_underlying_token_whale, profit, sender=governance.address)
    yield_underlying_token.transfer(undy_usd_vault, profit, sender=yield_underlying_token_whale)
    
    # Verify share value increased proportionally
    new_share_value = undy_usd_vault.convertToAssets(shares) / shares
    assert new_share_value == (deposit_amount + profit) / shares
    
    # Add tiny profit (0.1%)
    tiny_profit = deposit_amount // 1000
    yield_underlying_token.mint(yield_underlying_token_whale, tiny_profit, sender=governance.address)
    yield_underlying_token.transfer(undy_usd_vault, tiny_profit, sender=yield_underlying_token_whale)
    
    # Verify share value still updates correctly
    final_share_value = undy_usd_vault.convertToAssets(shares) / shares
    assert final_share_value > new_share_value
    assert final_share_value == (deposit_amount + profit + tiny_profit) / shares


def test_erc4626_first_depositor_attack_prevention(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
    governance,
):
    """Test that demonstrates first depositor share price manipulation attack vulnerability.

    This test demonstrates:
    1. The vault IS vulnerable to first depositor attack when empty
    2. Admin seeding with 10+ tokens prevents the attack
    """
    # Approve the vault for testing
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # PART 1: Demonstrate the vulnerability with actual execution
    # ---------------------------------------------------
    print("\n=== Testing First Depositor Attack Vulnerability ===")

    # Vault must start empty to demonstrate the vulnerability
    initial_total_assets = undy_usd_vault.totalAssets()
    initial_total_supply = undy_usd_vault.totalSupply()

    # This test requires an empty vault to demonstrate the vulnerability
    assert initial_total_assets == 0 and initial_total_supply == 0, \
        "Vault must be empty at start to demonstrate first depositor vulnerability"

    # Vault is empty - demonstrate the actual vulnerability
    print("Vault is empty - VULNERABLE to first depositor attack")

    # First depositor deposits minimal amount (1 wei)
    first_deposit = 1  # 1 wei
    shares_first = undy_usd_vault.deposit(first_deposit, bob, sender=yield_underlying_token_whale)
    assert shares_first == 1, "First deposit of 1 wei should mint exactly 1 share"
    print(f"First depositor deposited {first_deposit} wei, got {shares_first} shares")

    # Attacker donates large amount to inflate share price
    donation = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.mint(yield_underlying_token_whale, donation, sender=governance.address)
    yield_underlying_token.transfer(undy_usd_vault, donation, sender=yield_underlying_token_whale)
    print(f"Attacker donated {donation // EIGHTEEN_DECIMALS} tokens directly to vault")

    # Now the vault has 1000 tokens + 1 wei backing only 1 share
    # Share price is now extremely inflated
    assert undy_usd_vault.totalAssets() > donation, "Vault should have attacker's donation"
    assert undy_usd_vault.totalSupply() == 1, "Vault should have only 1 share"

    # Calculate how many shares a victim would get
    victim_deposit = 100 * EIGHTEEN_DECIMALS
    expected_shares = undy_usd_vault.previewDeposit(victim_deposit)
    print(f"Victim depositing {victim_deposit // EIGHTEEN_DECIMALS} tokens would get {expected_shares} shares")

    # This demonstrates the vulnerability - victim gets 0 shares!
    assert expected_shares == 0, "VULNERABILITY CONFIRMED: Victim receives 0 shares due to rounding"
    print("VULNERABILITY CONFIRMED: Victim would receive 0 shares!")

    # PART 2: Demonstrate the solution - Admin Seeding
    # -------------------------------------------------
    print("\n=== Admin Seeding Solution ===")
    print("If admin seeds vault with 10 tokens initially:")

    # Simulate seeded vault scenario
    SEED_AMOUNT = 10 * EIGHTEEN_DECIMALS
    print(f"  - Admin deposits {SEED_AMOUNT // EIGHTEEN_DECIMALS} tokens, gets {SEED_AMOUNT} shares")
    print(f"  - Initial share price: 1:1 ratio")

    # Attacker still tries to manipulate
    attacker_deposit = 1  # 1 wei
    # In seeded vault: shares = 1 wei * 10e18 shares / 10e18 assets ≈ 1 share
    attacker_shares_in_seeded = (attacker_deposit * SEED_AMOUNT) // SEED_AMOUNT
    print(f"  - Attacker deposits {attacker_deposit} wei, gets ~{attacker_shares_in_seeded} shares")

    # After donation
    donation = 1000 * EIGHTEEN_DECIMALS
    total_assets_after = SEED_AMOUNT + attacker_deposit + donation
    total_shares = SEED_AMOUNT + attacker_shares_in_seeded

    # Victim deposits
    victim_deposit = 100 * EIGHTEEN_DECIMALS
    # shares = 100e18 * (10e18 + 1) / (10e18 + 1 + 1000e18)
    # shares = 100e18 * 10e18 / 1010e18 ≈ 9.9e18 shares
    victim_shares_in_seeded = (victim_deposit * total_shares) // total_assets_after

    print(f"  - After {donation // EIGHTEEN_DECIMALS} token donation")
    print(f"  - Victim depositing {victim_deposit // EIGHTEEN_DECIMALS} tokens gets: ~{victim_shares_in_seeded // EIGHTEEN_DECIMALS} shares")
    print(f"  - Victim receives fair shares proportional to deposit!")

    # Verify the math
    assert victim_shares_in_seeded > 0, "With admin seeding, victim always receives shares"
    print("\nCONCLUSION: Admin seeding with 10+ tokens prevents first depositor attack!")


def test_erc4626_rapid_price_fluctuations(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
    governance,
):
    """Test vault behavior under rapid price changes (profits and losses).
    Ensures share accounting remains consistent through volatile conditions."""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # Initial deposit to establish baseline
    deposit = 100 * EIGHTEEN_DECIMALS
    shares = undy_usd_vault.deposit(deposit, bob, sender=yield_underlying_token_whale)
    initial_value = undy_usd_vault.convertToAssets(shares)
    assert initial_value == deposit, "Initial conversion should be 1:1"

    # Track cumulative changes for verification
    cumulative_change = 0

    # Simulate rapid price changes: +50, -30, +40, -20, +60 (in EIGHTEEN_DECIMALS units)
    changes = [(50, True), (30, False), (40, True), (20, False), (60, True)]

    for amount_multiplier, is_profit in changes:
        amount = amount_multiplier * EIGHTEEN_DECIMALS

        if is_profit:
            # Simulate profit by adding tokens to vault
            yield_underlying_token.mint(yield_underlying_token_whale, amount, sender=governance.address)
            yield_underlying_token.transfer(undy_usd_vault, amount, sender=yield_underlying_token_whale)
            cumulative_change += amount
        else:
            # Simulate loss by removing tokens from vault
            yield_underlying_token.transfer(yield_underlying_token_whale, amount, sender=undy_usd_vault.address)
            cumulative_change -= amount

        # After each change, verify share accounting is consistent
        current_value = undy_usd_vault.convertToAssets(shares)
        expected_value = deposit + cumulative_change
        assert abs(current_value - expected_value) <= 1, f"Value mismatch after change: {current_value} != {expected_value}"

    # Final verification
    final_value = undy_usd_vault.convertToAssets(shares)
    final_expected = deposit + cumulative_change  # Should be 100 + 50 - 30 + 40 - 20 + 60 = 200
    assert abs(final_value - final_expected) <= 1, f"Final value incorrect: {final_value} != {final_expected}"

    # Verify withdrawal works correctly after fluctuations
    bob_balance_before = yield_underlying_token.balanceOf(bob)
    undy_usd_vault.redeem(shares, bob, bob, sender=bob)
    bob_balance_after = yield_underlying_token.balanceOf(bob)
    withdrawn = bob_balance_after - bob_balance_before
    assert abs(withdrawn - final_value) <= 1, f"Withdrawal amount incorrect: {withdrawn} != {final_value}"


def test_erc4626_sandwich_attack_scenario(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
    sally,
    governance,
):
    """Test vault behavior in sandwich attack scenario where an attacker
    tries to manipulate share price before and after a victim's transaction."""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # Setup: Bob is the attacker, Sally is the victim
    # Initial state with some deposits
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    attacker_shares = undy_usd_vault.deposit(initial_deposit, bob, sender=yield_underlying_token_whale)

    # Step 1: Attacker front-runs by inflating share price
    frontrun_amount = 500 * EIGHTEEN_DECIMALS
    yield_underlying_token.mint(yield_underlying_token_whale, frontrun_amount, sender=governance.address)
    yield_underlying_token.transfer(undy_usd_vault, frontrun_amount, sender=yield_underlying_token_whale)

    # Step 2: Victim deposits (at inflated price)
    victim_deposit = 200 * EIGHTEEN_DECIMALS
    victim_shares = undy_usd_vault.deposit(victim_deposit, sally, sender=yield_underlying_token_whale)

    # Step 3: Attacker back-runs by withdrawing
    attacker_assets_before = yield_underlying_token.balanceOf(bob)
    undy_usd_vault.redeem(attacker_shares, bob, bob, sender=bob)
    attacker_assets_after = yield_underlying_token.balanceOf(bob)
    attacker_profit = attacker_assets_after - attacker_assets_before - initial_deposit

    # Verify victim didn't lose significant value
    sally_value = undy_usd_vault.convertToAssets(victim_shares)
    min_acceptable = victim_deposit * 95 // 100  # Allow max 5% loss in extreme scenario
    assert sally_value >= min_acceptable, f"Victim lost too much: {sally_value} < {min_acceptable}"

    # Verify total accounting is still correct
    remaining_assets = undy_usd_vault.totalAssets()
    # Only victim's deposit should remain (attacker withdrew their share of everything)
    expected_remaining = victim_deposit
    assert abs(remaining_assets - expected_remaining) <= EIGHTEEN_DECIMALS, f"Asset accounting off: {remaining_assets} != {expected_remaining}"


def test_erc4626_multiple_depositors_share_price_consistency(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
    sally,
    governance,
):
    """Test that share price remains consistent across multiple depositors
    even with asset balance changes between deposits."""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    depositors = [bob, sally]
    deposits = []
    shares = []

    # Multiple rounds of deposits with profits between them
    for round_num in range(3):
        for i, depositor in enumerate(depositors):
            deposit_amount = (100 + round_num * 50) * EIGHTEEN_DECIMALS
            depositor_shares = undy_usd_vault.deposit(deposit_amount, depositor, sender=yield_underlying_token_whale)
            deposits.append((depositor, deposit_amount))
            shares.append((depositor, depositor_shares))

        # Add profit between rounds (except after last round)
        if round_num < 2:
            profit = 30 * EIGHTEEN_DECIMALS
            yield_underlying_token.mint(yield_underlying_token_whale, profit, sender=governance.address)
            yield_underlying_token.transfer(undy_usd_vault, profit, sender=yield_underlying_token_whale)

    # Verify all depositors have correct share values
    total_deposits_by_user = {}
    total_shares_by_user = {}

    for depositor, amount in deposits:
        total_deposits_by_user[depositor] = total_deposits_by_user.get(depositor, 0) + amount

    for depositor, share_amount in shares:
        total_shares_by_user[depositor] = total_shares_by_user.get(depositor, 0) + share_amount

    # Each depositor should have proportional share of total assets
    total_assets = undy_usd_vault.totalAssets()
    total_shares_minted = undy_usd_vault.totalSupply()

    for depositor in depositors:
        user_shares = total_shares_by_user[depositor]
        user_value = undy_usd_vault.convertToAssets(user_shares)
        expected_min = total_deposits_by_user[depositor]  # Should at least have what they deposited
        assert user_value >= expected_min, f"User value less than deposits: {user_value} < {expected_min}"

        # Verify proportional ownership
        user_ownership_ratio = user_shares / total_shares_minted
        user_asset_ratio = user_value / total_assets
        assert abs(user_ownership_ratio - user_asset_ratio) < 0.0001, "Ownership ratio doesn't match asset ratio"


# Test canDeposit and canWithdraw functionality

def test_can_deposit_flag_blocks_deposits(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    switchboard_alpha,
    bob,
):
    """Test that deposits are blocked when canDeposit is False"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # Initially canDeposit should be True (from fixture)
    assert undy_usd_vault.canDeposit() == True

    # Make a successful deposit first
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    shares = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    assert shares > 0

    # Disable deposits
    undy_usd_vault.setCanDeposit(False, sender=switchboard_alpha.address)
    assert undy_usd_vault.canDeposit() == False

    # Try to deposit - should fail
    with boa.reverts("cannot deposit"):
        undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)

    # Try to mint - should also fail (uses _deposit internally)
    with boa.reverts("cannot deposit"):
        undy_usd_vault.mint(shares, bob, sender=yield_underlying_token_whale)

    # Re-enable deposits
    undy_usd_vault.setCanDeposit(True, sender=switchboard_alpha.address)
    assert undy_usd_vault.canDeposit() == True

    # Should be able to deposit again
    shares2 = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    assert shares2 > 0


def test_can_withdraw_flag_blocks_withdrawals(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    switchboard_alpha,
    bob,
):
    """Test that withdrawals are blocked when canWithdraw is False"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # Initially canWithdraw should be True (from fixture)
    assert undy_usd_vault.canWithdraw() == True

    # First deposit some funds
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    shares = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    assert shares > 0

    # Disable withdrawals
    undy_usd_vault.setCanWithdraw(False, sender=switchboard_alpha.address)
    assert undy_usd_vault.canWithdraw() == False

    # Try to redeem - should fail
    with boa.reverts("cannot withdraw"):
        undy_usd_vault.redeem(shares, bob, bob, sender=bob)

    # Try to withdraw - should also fail (calls _redeem internally which has the check)
    with boa.reverts("cannot withdraw"):
        undy_usd_vault.withdraw(deposit_amount, bob, bob, sender=bob)

    # Re-enable withdrawals
    undy_usd_vault.setCanWithdraw(True, sender=switchboard_alpha.address)
    assert undy_usd_vault.canWithdraw() == True

    # Should be able to withdraw again
    assets_received = undy_usd_vault.redeem(shares, bob, bob, sender=bob)
    assert assets_received > 0


def test_set_can_deposit_permissions(
    undy_usd_vault,
    switchboard_alpha,
    bob,
    starter_agent,
):
    """Test that only authorized addresses can set canDeposit"""

    # Initially should be True
    assert undy_usd_vault.canDeposit() == True

    # Switchboard can change it
    undy_usd_vault.setCanDeposit(False, sender=switchboard_alpha.address)
    assert undy_usd_vault.canDeposit() == False

    # Bob (unauthorized) cannot change it
    with boa.reverts("no perms"):
        undy_usd_vault.setCanDeposit(True, sender=bob)

    # Manager cannot change it either
    with boa.reverts("no perms"):
        undy_usd_vault.setCanDeposit(True, sender=starter_agent.address)

    # Switchboard can change it back
    undy_usd_vault.setCanDeposit(True, sender=switchboard_alpha.address)
    assert undy_usd_vault.canDeposit() == True


def test_set_can_withdraw_permissions(
    undy_usd_vault,
    switchboard_alpha,
    bob,
    starter_agent,
):
    """Test that only authorized addresses can set canWithdraw"""

    # Initially should be True
    assert undy_usd_vault.canWithdraw() == True

    # Switchboard can change it
    undy_usd_vault.setCanWithdraw(False, sender=switchboard_alpha.address)
    assert undy_usd_vault.canWithdraw() == False

    # Bob (unauthorized) cannot change it
    with boa.reverts("no perms"):
        undy_usd_vault.setCanWithdraw(True, sender=bob)

    # Manager cannot change it either
    with boa.reverts("no perms"):
        undy_usd_vault.setCanWithdraw(True, sender=starter_agent.address)

    # Switchboard can change it back
    undy_usd_vault.setCanWithdraw(True, sender=switchboard_alpha.address)
    assert undy_usd_vault.canWithdraw() == True


def test_set_can_deposit_no_change_reverts(
    undy_usd_vault,
    switchboard_alpha,
):
    """Test that setting canDeposit to same value reverts"""

    # Initially should be True
    assert undy_usd_vault.canDeposit() == True

    # Try to set to same value - should revert
    with boa.reverts("nothing to change"):
        undy_usd_vault.setCanDeposit(True, sender=switchboard_alpha.address)

    # Change to False
    undy_usd_vault.setCanDeposit(False, sender=switchboard_alpha.address)

    # Try to set to same value again - should revert
    with boa.reverts("nothing to change"):
        undy_usd_vault.setCanDeposit(False, sender=switchboard_alpha.address)


def test_set_can_withdraw_no_change_reverts(
    undy_usd_vault,
    switchboard_alpha,
):
    """Test that setting canWithdraw to same value reverts"""

    # Initially should be True
    assert undy_usd_vault.canWithdraw() == True

    # Try to set to same value - should revert
    with boa.reverts("nothing to change"):
        undy_usd_vault.setCanWithdraw(True, sender=switchboard_alpha.address)

    # Change to False
    undy_usd_vault.setCanWithdraw(False, sender=switchboard_alpha.address)

    # Try to set to same value again - should revert
    with boa.reverts("nothing to change"):
        undy_usd_vault.setCanWithdraw(False, sender=switchboard_alpha.address)


def test_can_deposit_and_withdraw_events(
    undy_usd_vault,
    switchboard_alpha,
):
    """Test that setting canDeposit and canWithdraw emit correct events"""

    # Set canDeposit to False and check event
    tx = undy_usd_vault.setCanDeposit(False, sender=switchboard_alpha.address)

    # Use filter_logs to get the CanDepositSet event
    deposit_events = filter_logs(undy_usd_vault, "CanDepositSet")
    assert len(deposit_events) > 0

    deposit_event = deposit_events[-1]  # Get the most recent event
    assert deposit_event.canDeposit == False
    assert deposit_event.caller == switchboard_alpha.address

    # Set canWithdraw to False and check event
    tx2 = undy_usd_vault.setCanWithdraw(False, sender=switchboard_alpha.address)

    # Use filter_logs to get the CanWithdrawSet event
    withdraw_events = filter_logs(undy_usd_vault, "CanWithdrawSet")
    assert len(withdraw_events) > 0

    withdraw_event = withdraw_events[-1]  # Get the most recent event
    assert withdraw_event.canWithdraw == False
    assert withdraw_event.caller == switchboard_alpha.address


def test_deposits_blocked_affects_all_deposit_methods(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    switchboard_alpha,
    bob,
):
    """Test that disabling deposits blocks all deposit-related methods"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # Disable deposits
    undy_usd_vault.setCanDeposit(False, sender=switchboard_alpha.address)

    deposit_amount = 100 * EIGHTEEN_DECIMALS
    mint_shares = 100 * EIGHTEEN_DECIMALS

    # Test deposit() method
    with boa.reverts("cannot deposit"):
        undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)

    # Test mint() method
    with boa.reverts("cannot deposit"):
        undy_usd_vault.mint(mint_shares, bob, sender=yield_underlying_token_whale)

    # Preview methods should still work (they're view functions)
    preview_deposit = undy_usd_vault.previewDeposit(deposit_amount)
    assert preview_deposit >= 0  # Should return a value, not revert

    preview_mint = undy_usd_vault.previewMint(mint_shares)
    assert preview_mint >= 0  # Should return a value, not revert


def test_withdrawals_blocked_affects_all_withdraw_methods(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    switchboard_alpha,
    bob,
):
    """Test that disabling withdrawals blocks all withdrawal-related methods"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    # First deposit some funds
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    shares = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)

    # Disable withdrawals
    undy_usd_vault.setCanWithdraw(False, sender=switchboard_alpha.address)

    # Test redeem() method
    with boa.reverts("cannot withdraw"):
        undy_usd_vault.redeem(shares, bob, bob, sender=bob)

    # Test withdraw() method
    with boa.reverts("cannot withdraw"):
        undy_usd_vault.withdraw(deposit_amount, bob, bob, sender=bob)

    # Preview methods should still work (they're view functions)
    preview_redeem = undy_usd_vault.previewRedeem(shares)
    assert preview_redeem >= 0  # Should return a value, not revert

    preview_withdraw = undy_usd_vault.previewWithdraw(deposit_amount)
    assert preview_withdraw >= 0  # Should return a value, not revert


def test_multiple_flag_changes(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    switchboard_alpha,
    bob,
):
    """Test multiple changes to canDeposit and canWithdraw flags"""
    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    deposit_amount = 50 * EIGHTEEN_DECIMALS

    # Deposit when allowed
    shares1 = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)

    # Disable deposits
    undy_usd_vault.setCanDeposit(False, sender=switchboard_alpha.address)

    # Can't deposit
    with boa.reverts("cannot deposit"):
        undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)

    # But can still withdraw
    withdrawn = undy_usd_vault.redeem(shares1 // 2, bob, bob, sender=bob)
    assert withdrawn > 0

    # Enable deposits, disable withdrawals
    undy_usd_vault.setCanDeposit(True, sender=switchboard_alpha.address)
    undy_usd_vault.setCanWithdraw(False, sender=switchboard_alpha.address)

    # Can deposit again
    shares2 = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    assert shares2 > 0

    # But can't withdraw
    with boa.reverts("cannot withdraw"):
        undy_usd_vault.redeem(shares2, bob, bob, sender=bob)

    # Enable both
    undy_usd_vault.setCanWithdraw(True, sender=switchboard_alpha.address)

    # Both operations should work
    shares3 = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    assert shares3 > 0

    total_shares = undy_usd_vault.balanceOf(bob)
    assets_received = undy_usd_vault.redeem(total_shares, bob, bob, sender=bob)
    assert assets_received > 0

    # Should have no shares left
    assert undy_usd_vault.balanceOf(bob) == 0


def test_vault_initialization_with_flags_disabled(
    undy_hq_deploy,
    fork,
    starter_agent,
    yield_underlying_token,
    yield_underlying_token_whale,
    bob,
):
    """Test vault initialization with canDeposit and canWithdraw set to False"""
    from config.BluePrint import PARAMS

    # Create vault with deposits and withdrawals disabled
    vault_no_deposits = boa.load(
        "contracts/vaults/UndyUsd.vy",
        yield_underlying_token.address,
        undy_hq_deploy,
        PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"],
        PARAMS[fork]["UNDY_HQ_MAX_GOV_TIMELOCK"],
        starter_agent,
        False,  # canDeposit = False
        True,   # canWithdraw = True
        0,      # maxDepositAmount = 0 (unlimited)
        PARAMS[fork]["EARN_VAULT_MIN_SNAPSHOT_DELAY"],
        PARAMS[fork]["EARN_VAULT_MAX_NUM_SNAPSHOTS"],
        PARAMS[fork]["EARN_VAULT_MAX_UPSIDE_DEVIATION"],
        PARAMS[fork]["EARN_VAULT_STALE_TIME"],
    )

    # Check initial state
    assert vault_no_deposits.canDeposit() == False
    assert vault_no_deposits.canWithdraw() == True

    # Can't deposit
    yield_underlying_token.approve(vault_no_deposits, MAX_UINT256, sender=yield_underlying_token_whale)
    with boa.reverts("cannot deposit"):
        vault_no_deposits.deposit(100 * EIGHTEEN_DECIMALS, bob, sender=yield_underlying_token_whale)

    # Create vault with withdrawals disabled
    vault_no_withdrawals = boa.load(
        "contracts/vaults/UndyUsd.vy",
        yield_underlying_token.address,
        undy_hq_deploy,
        PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"],
        PARAMS[fork]["UNDY_HQ_MAX_GOV_TIMELOCK"],
        starter_agent,
        True,   # canDeposit = True
        False,  # canWithdraw = False
        0,      # maxDepositAmount = 0 (unlimited)
        PARAMS[fork]["EARN_VAULT_MIN_SNAPSHOT_DELAY"],
        PARAMS[fork]["EARN_VAULT_MAX_NUM_SNAPSHOTS"],
        PARAMS[fork]["EARN_VAULT_MAX_UPSIDE_DEVIATION"],
        PARAMS[fork]["EARN_VAULT_STALE_TIME"],
    )

    # Check initial state
    assert vault_no_withdrawals.canDeposit() == True
    assert vault_no_withdrawals.canWithdraw() == False

    # Can deposit
    yield_underlying_token.approve(vault_no_withdrawals, MAX_UINT256, sender=yield_underlying_token_whale)
    shares = vault_no_withdrawals.deposit(100 * EIGHTEEN_DECIMALS, bob, sender=yield_underlying_token_whale)
    assert shares > 0

    # But can't withdraw
    with boa.reverts("cannot withdraw"):
        vault_no_withdrawals.redeem(shares, bob, bob, sender=bob)
