import pytest
import boa
from constants import MAX_UINT256, EIGHTEEN_DECIMALS

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
def setup_multiple_users(bob, alice, charlie, governance, mock_usdc):
    """Set up multiple test users with USDC balances"""
    users = {
        'alice': alice,
        'bob': bob,
        'charlie': charlie
    }

    # Give each user different amounts of USDC
    mock_usdc.mint(alice, 100_000 * SIX_DECIMALS, sender=governance.address)  # Whale
    mock_usdc.mint(bob, 10_000 * SIX_DECIMALS, sender=governance.address)    # Medium
    mock_usdc.mint(charlie, 100 * SIX_DECIMALS, sender=governance.address)   # Small

    return users


@pytest.fixture(scope="function")
def setup_vault_for_multi_user(
    undy_levg_vault_usdc,
    vault_registry,
    switchboard_alpha,
):
    """Set up vault with proper permissions for multi-user testing"""
    vault = undy_levg_vault_usdc

    # Enable deposits and withdrawals
    vault_registry.setCanDeposit(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setCanWithdraw(vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setShouldAutoDeposit(vault.address, False, sender=switchboard_alpha.address)

    return vault


#############################################
# Test 1: Multiple Users at Different Prices #
#############################################

def test_multiple_users_different_share_prices(
    setup_prices,
    setup_multiple_users,
    setup_vault_for_multi_user,
    mock_usdc,
    mock_usdc_collateral_vault,
    mock_yield_lego,
    starter_agent,
    switchboard_alpha,
    governance,
):
    """Test multiple users deposit at different share prices and all get fair treatment"""
    vault = setup_vault_for_multi_user
    users = setup_multiple_users
    alice = users['alice']
    bob = users['bob']
    charlie = users['charlie']

    # Configure snapshot to use only most recent price for safe values close to current price
    mock_yield_lego.setSnapShotPriceConfig(
        (60 * 10, 1, 10_00, 60 * 60 * 24),  # (minSnapshotDelay, maxNumSnapshots=1, maxUpsideDeviation, staleTime)
        sender=switchboard_alpha.address
    )

    # Alice deposits first at 1:1 share price
    alice_deposit = 10_000 * SIX_DECIMALS
    mock_usdc.approve(vault.address, alice_deposit, sender=alice)
    alice_shares = vault.deposit(alice_deposit, alice, sender=alice)

    # Verify initial 1:1 ratio
    assert alice_shares == alice_deposit
    assert vault.convertToAssets(alice_shares, sender=alice) == alice_deposit

    # Generate yield by depositing to collateral vault and simulating returns
    vault.depositForYield(
        2,
        mock_usdc.address,
        mock_usdc_collateral_vault.address,
        alice_deposit,
        sender=starter_agent.address
    )

    # Simulate 10% yield by minting extra USDC to the vault
    yield_amount = alice_deposit // 10  # 10% yield
    mock_usdc.mint(mock_usdc_collateral_vault.address, yield_amount, sender=governance.address)

    # Advance time to allow snapshot update (minSnapshotDelay = 10 minutes)
    boa.env.time_travel(seconds=60 * 11)  # 11 minutes

    # Update price snapshot to reflect the new yield
    mock_yield_lego.addPriceSnapshot(mock_usdc_collateral_vault.address, sender=switchboard_alpha.address)

    # Now total assets = 11,000 USDC, total shares = 10,000
    # Share price = 1.1 USDC per share

    # Bob deposits at new share price
    bob_deposit = 5_500 * SIX_DECIMALS  # Should get 5,000 shares
    mock_usdc.approve(vault.address, bob_deposit, sender=bob)
    bob_shares = vault.deposit(bob_deposit, bob, sender=bob)

    # Verify Bob gets correct shares at new price
    expected_bob_shares = 5_000 * SIX_DECIMALS
    assert bob_shares == expected_bob_shares

    # Generate more yield
    additional_yield = 1_000 * SIX_DECIMALS
    mock_usdc.mint(mock_usdc_collateral_vault.address, additional_yield, sender=governance.address)

    # Advance time to allow snapshot update
    boa.env.time_travel(seconds=60 * 11)  # 11 minutes

    # Update price snapshot to reflect the additional yield
    mock_yield_lego.addPriceSnapshot(mock_usdc_collateral_vault.address, sender=switchboard_alpha.address)

    # Now total assets = 17,500 USDC, total shares = 15,000
    # Share price = 1.167 USDC per share

    # Charlie deposits at latest share price
    charlie_deposit = 100 * SIX_DECIMALS  # Charlie only has 100 USDC
    mock_usdc.approve(vault.address, charlie_deposit, sender=charlie)
    charlie_shares = vault.deposit(charlie_deposit, charlie, sender=charlie)

    # Verify Charlie gets correct shares
    assert charlie_shares > 0
    assert charlie_shares < charlie_deposit  # Gets fewer shares due to higher price

    # All users should be able to redeem proportionally
    # Alice redeems - use minAmountOut to handle rounding after yield
    alice_assets = vault.convertToAssets(alice_shares, sender=alice)
    alice_min = alice_assets * 999 // 1000  # Accept 99.9% to handle rounding
    alice_redeemed = vault.redeemWithMinAmountOut(alice_shares, alice_min, alice, alice, sender=alice)
    assert alice_redeemed >= alice_min
    assert alice_redeemed > alice_deposit  # Alice earned yield

    # Bob redeems - use minAmountOut to handle rounding after yield
    bob_assets = vault.convertToAssets(bob_shares, sender=bob)
    bob_min = bob_assets * 999 // 1000  # Accept 99.9% to handle rounding
    bob_redeemed = vault.redeemWithMinAmountOut(bob_shares, bob_min, bob, bob, sender=bob)
    assert bob_redeemed >= bob_min
    assert bob_redeemed > bob_deposit  # Bob also earned yield

    # Charlie redeems - use minAmountOut to handle rounding after yield
    charlie_assets = vault.convertToAssets(charlie_shares, sender=charlie)
    charlie_min = charlie_assets * 999 // 1000  # Accept 99.9% to handle rounding
    charlie_redeemed = vault.redeemWithMinAmountOut(charlie_shares, charlie_min, charlie, charlie, sender=charlie)
    assert charlie_redeemed >= charlie_min
    # Charlie joined last, minimal yield
    assert charlie_redeemed >= charlie_deposit - 1  # Allow 1 wei rounding


def test_concurrent_deposits_and_withdrawals(
    setup_prices,
    setup_multiple_users,
    setup_vault_for_multi_user,
    mock_usdc,
):
    """Test deposits and withdrawals happening in the same transaction batch"""
    vault = setup_vault_for_multi_user
    users = setup_multiple_users
    alice = users['alice']
    bob = users['bob']
    charlie = users['charlie']

    # Initial deposits from all users
    alice_deposit = 10_000 * SIX_DECIMALS
    bob_deposit = 5_000 * SIX_DECIMALS
    charlie_deposit = 100 * SIX_DECIMALS

    mock_usdc.approve(vault.address, alice_deposit, sender=alice)
    mock_usdc.approve(vault.address, bob_deposit, sender=bob)
    mock_usdc.approve(vault.address, charlie_deposit, sender=charlie)

    alice_shares = vault.deposit(alice_deposit, alice, sender=alice)
    bob_shares = vault.deposit(bob_deposit, bob, sender=bob)
    charlie_shares = vault.deposit(charlie_deposit, charlie, sender=charlie)

    # Record state before concurrent operations
    initial_total_supply = vault.totalSupply(sender=alice)
    initial_total_assets = vault.totalAssets(sender=alice)
    initial_share_price = vault.convertToAssets(10 ** 6, sender=alice)  # Price per 1M shares

    # Simulate concurrent operations:
    # Alice withdraws half while Bob deposits more
    alice_withdraw_shares = alice_shares // 2
    bob_additional_deposit = 2_000 * SIX_DECIMALS
    mock_usdc.approve(vault.address, bob_additional_deposit, sender=bob)

    # Execute "concurrently" (in same block)
    alice_withdrawn = vault.redeem(alice_withdraw_shares, alice, alice, sender=alice)
    bob_new_shares = vault.deposit(bob_additional_deposit, bob, sender=bob)

    # Verify share price remained consistent during concurrent ops
    new_share_price = vault.convertToAssets(10 ** 6, sender=alice)
    assert new_share_price == initial_share_price  # No manipulation possible

    # Verify accounting is correct
    expected_total_supply = initial_total_supply - alice_withdraw_shares + bob_new_shares
    assert vault.totalSupply(sender=alice) == expected_total_supply

    # Charlie should be unaffected
    charlie_assets = vault.convertToAssets(charlie_shares, sender=charlie)
    assert charlie_assets == charlie_deposit  # No change for Charlie


def test_whale_deposit_doesnt_dilute_small_holders(
    setup_prices,
    setup_multiple_users,
    setup_vault_for_multi_user,
    mock_usdc,
):
    """Test that large deposits don't dilute existing small holders"""
    vault = setup_vault_for_multi_user
    users = setup_multiple_users
    alice = users['alice']  # Whale
    charlie = users['charlie']  # Small holder

    # Charlie deposits first (small amount)
    charlie_deposit = 100 * SIX_DECIMALS
    mock_usdc.approve(vault.address, charlie_deposit, sender=charlie)
    charlie_shares = vault.deposit(charlie_deposit, charlie, sender=charlie)

    # Record Charlie's share value
    charlie_initial_value = vault.convertToAssets(charlie_shares, sender=charlie)
    assert charlie_initial_value == charlie_deposit

    # Alice (whale) deposits massive amount
    whale_deposit = 90_000 * SIX_DECIMALS  # 900x Charlie's deposit
    mock_usdc.approve(vault.address, whale_deposit, sender=alice)
    alice_shares = vault.deposit(whale_deposit, alice, sender=alice)

    # Verify Charlie's share value unchanged
    charlie_value_after_whale = vault.convertToAssets(charlie_shares, sender=charlie)
    assert charlie_value_after_whale == charlie_initial_value

    # Verify proportional ownership
    total_shares = vault.totalSupply(sender=alice)
    charlie_ownership_pct = (charlie_shares * 100) / total_shares
    expected_ownership_pct = (charlie_deposit * 100) / (charlie_deposit + whale_deposit)

    # Allow tiny rounding difference
    assert abs(charlie_ownership_pct - expected_ownership_pct) <= 1

    # Both should be able to withdraw their exact deposits
    charlie_redeemed = vault.redeem(charlie_shares, charlie, charlie, sender=charlie)
    alice_redeemed = vault.redeem(alice_shares, alice, alice, sender=alice)

    assert charlie_redeemed == charlie_deposit
    assert alice_redeemed == whale_deposit


def test_share_price_donation_vulnerability(
    setup_prices,
    setup_vault_for_multi_user,
    mock_usdc,
    alice,
    bob,
    governance,
):
    """Test documenting share price dilution via donation attack (vulnerability)"""
    vault = setup_vault_for_multi_user

    # Mint USDC for testing
    mock_usdc.mint(alice, 100_000 * SIX_DECIMALS, sender=governance.address)
    mock_usdc.mint(bob, 10_000 * SIX_DECIMALS, sender=governance.address)

    # Alice executes donation attack:
    # 1. Deposit to get shares
    alice_deposit = 100 * SIX_DECIMALS
    mock_usdc.approve(vault.address, MAX_UINT256, sender=alice)
    alice_shares = vault.deposit(alice_deposit, alice, sender=alice)

    # 2. Donate to inflate share price before Bob deposits
    donation = 1_000 * SIX_DECIMALS
    mock_usdc.transfer(vault.address, donation, sender=alice)

    # Total vault assets before Bob: 100 (Alice) + 1000 (donation) = 1100
    # Share price: 1100 / 100 shares = 11 USDC per share

    # 3. Bob deposits at inflated price
    bob_deposit = 10_000 * SIX_DECIMALS
    mock_usdc.approve(vault.address, bob_deposit, sender=bob)
    bob_shares = vault.deposit(bob_deposit, bob, sender=bob)

    # Bob should get: 10,000 / 11 = ~909 shares
    # Alice has 100 shares, Bob has ~909 shares
    # Total assets: 1100 + 10000 = 11,100
    # Bob's portion: 909/1009 * 11,100 = ~10,010 (~10,000 of his + ~10 of donation)
    # Alice's portion: 100/1009 * 11,100 = ~1,100 (~100 of hers + ~990 of donation stolen)

    # Calculate actual result
    total_assets = vault.totalAssets(sender=bob)
    total_shares = vault.totalSupply(sender=bob)
    bob_assets = vault.convertToAssets(bob_shares, sender=bob)
    alice_assets = vault.convertToAssets(alice_shares, sender=alice)

    # With ERC4626, Bob deposits at current share price which includes the donation
    # Share price before Bob: 1100 / 100 = 11
    # Bob gets: 10000 / 11 = 909.09 shares
    # After Bob: 11100 assets / 1009.09 shares = 11 per share
    # Bob's value: 909.09 * 11 = 10000 (gets his deposit back!)
    # Alice's value: 100 * 11 = 1100 (her deposit + the donation!)

    # Verify Bob gets essentially his full deposit back (protected by ERC4626 pricing)
    assert bob_assets >= bob_deposit * 999 // 1000, f"Bob should get ~100% back: {bob_assets} vs {bob_deposit}"
    assert bob_assets <= bob_deposit * 1001 // 1000, f"Bob shouldn't profit from Alice's donation: {bob_assets}"

    # Verify Alice kept her donation value (she didn't successfully steal from Bob)
    expected_alice = alice_deposit + donation
    assert alice_assets >= expected_alice * 999 // 1000, f"Alice should keep donation: {alice_assets} vs {expected_alice}"
    assert alice_assets <= expected_alice * 1001 // 1000

    # This demonstrates that ERC4626 share pricing prevents the classic donation attack
    # Bob paid fair price and gets fair value back


def test_multiple_users_with_yield_accrual(
    setup_prices,
    setup_multiple_users,
    setup_vault_for_multi_user,
    mock_usdc,
    mock_usdc_collateral_vault,
    mock_yield_lego,
    starter_agent,
    switchboard_alpha,
    governance,
):
    """Test fair yield distribution among multiple users over time"""
    vault = setup_vault_for_multi_user
    users = setup_multiple_users
    alice = users['alice']
    bob = users['bob']
    charlie = users['charlie']

    # Configure snapshot for responsive safe values
    mock_yield_lego.setSnapShotPriceConfig(
        (60 * 10, 1, 10_00, 60 * 60 * 24),
        sender=switchboard_alpha.address
    )

    # Time 0: Alice deposits
    alice_deposit = 10_000 * SIX_DECIMALS
    mock_usdc.approve(vault.address, alice_deposit, sender=alice)
    alice_shares = vault.deposit(alice_deposit, alice, sender=alice)

    # Deploy capital to earn yield
    vault.depositForYield(
        2,
        mock_usdc.address,
        mock_usdc_collateral_vault.address,
        alice_deposit,
        sender=starter_agent.address
    )

    # Time 1: 10% yield accrues, Bob joins
    yield_1 = 1_000 * SIX_DECIMALS
    mock_usdc.mint(mock_usdc_collateral_vault.address, yield_1, sender=governance.address)

    # Advance time to allow snapshot update
    boa.env.time_travel(seconds=60 * 11)  # 11 minutes

    # Update price snapshot to reflect the new yield
    mock_yield_lego.addPriceSnapshot(mock_usdc_collateral_vault.address, sender=switchboard_alpha.address)

    bob_deposit = 5_000 * SIX_DECIMALS
    mock_usdc.approve(vault.address, bob_deposit, sender=bob)
    bob_shares = vault.deposit(bob_deposit, bob, sender=bob)

    # Bob should get fewer shares due to appreciated share price
    assert bob_shares < bob_deposit

    # Time 2: Another 10% yield on total, Charlie joins
    total_assets_t1 = vault.totalAssets(sender=alice)
    yield_2 = total_assets_t1 // 10
    mock_usdc.mint(mock_usdc_collateral_vault.address, yield_2, sender=governance.address)

    # Advance time to allow snapshot update
    boa.env.time_travel(seconds=60 * 11)  # 11 minutes

    # Update price snapshot to reflect the additional yield
    mock_yield_lego.addPriceSnapshot(mock_usdc_collateral_vault.address, sender=switchboard_alpha.address)

    charlie_deposit = 100 * SIX_DECIMALS
    mock_usdc.approve(vault.address, charlie_deposit, sender=charlie)
    charlie_shares = vault.deposit(charlie_deposit, charlie, sender=charlie)

    # Time 3: Final redemptions
    # Users should have GAINED yield, not lost value
    # Alice was in longest - captured full yield_1 (10%) + her share of yield_2
    # Expected: ~10% on 10k initial + share of second 10% yield
    alice_final = vault.redeem(alice_shares, alice, alice, sender=alice)
    alice_profit = alice_final - alice_deposit
    assert alice_profit > 0, f"Alice should have gained yield, not lost. Profit: {alice_profit}"
    alice_return_pct = (alice_profit * 10000) / alice_deposit  # In basis points

    # Bob was in for yield_2 only - should get portion of second yield
    bob_final = vault.redeem(bob_shares, bob, bob, sender=bob)
    bob_profit = bob_final - bob_deposit
    assert bob_profit > 0, f"Bob should have gained yield, not lost. Profit: {bob_profit}"
    bob_return_pct = (bob_profit * 10000) / bob_deposit  # In basis points

    # Charlie was in shortest time - smallest share of yield_2
    charlie_final = vault.redeem(charlie_shares, charlie, charlie, sender=charlie)
    charlie_profit = charlie_final - charlie_deposit
    assert charlie_profit >= 0, f"Charlie should have at least broken even. Profit: {charlie_profit}"

    # Verify yield distribution is fair - ordered by time in vault
    assert alice_return_pct > bob_return_pct, f"Alice ({alice_return_pct} bps) should have higher return than Bob ({bob_return_pct} bps)"
    assert bob_profit > charlie_profit, f"Bob (${bob_profit}) should have earned more than Charlie (${charlie_profit})"

    # Alice should have earned close to full 10% from first yield + her share of second
    # She had 100% of vault for yield_1 (1000 USDC) = 10% return
    # For yield_2, she had ~10/15 of vault, getting ~2/3 of yield_2
    expected_alice_min = alice_deposit * 115 // 100  # At least 15% total return
    assert alice_final >= expected_alice_min, f"Alice should have earned significant yield: {alice_final} vs expected {expected_alice_min}"


def test_front_running_protection_deposit(
    setup_prices,
    setup_vault_for_multi_user,
    mock_usdc,
    alice,
    bob,
    governance,
):
    """Test that front-running deposits doesn't give unfair advantage"""
    vault = setup_vault_for_multi_user

    # Give users USDC
    mock_usdc.mint(alice, 20_000 * SIX_DECIMALS, sender=governance.address)
    mock_usdc.mint(bob, 20_000 * SIX_DECIMALS, sender=governance.address)

    # Both users approve
    mock_usdc.approve(vault.address, MAX_UINT256, sender=alice)
    mock_usdc.approve(vault.address, MAX_UINT256, sender=bob)

    # Simulate front-running scenario:
    # Bob wants to deposit 10,000 USDC
    # Alice sees this and front-runs with same amount

    # Alice front-runs
    alice_deposit = 10_000 * SIX_DECIMALS
    alice_shares = vault.deposit(alice_deposit, alice, sender=alice)

    # Bob's transaction goes through after
    bob_deposit = 10_000 * SIX_DECIMALS
    bob_shares = vault.deposit(bob_deposit, bob, sender=bob)

    # Both should get same shares for same deposit amount
    assert alice_shares == bob_shares

    # Neither has advantage
    alice_value = vault.convertToAssets(alice_shares, sender=alice)
    bob_value = vault.convertToAssets(bob_shares, sender=bob)
    assert alice_value == bob_value


def test_front_running_protection_withdrawal(
    setup_prices,
    setup_vault_for_multi_user,
    mock_usdc,
    mock_usdc_collateral_vault,
    mock_yield_lego,
    alice,
    bob,
    starter_agent,
    switchboard_alpha,
    governance,
):
    """Test that front-running withdrawals doesn't give unfair advantage"""
    vault = setup_vault_for_multi_user

    # Configure snapshot for responsive safe values
    mock_yield_lego.setSnapShotPriceConfig(
        (60 * 10, 1, 10_00, 60 * 60 * 24),
        sender=switchboard_alpha.address
    )

    # Give users USDC and deposit
    mock_usdc.mint(alice, 10_000 * SIX_DECIMALS, sender=governance.address)
    mock_usdc.mint(bob, 10_000 * SIX_DECIMALS, sender=governance.address)

    mock_usdc.approve(vault.address, MAX_UINT256, sender=alice)
    mock_usdc.approve(vault.address, MAX_UINT256, sender=bob)

    alice_shares = vault.deposit(10_000 * SIX_DECIMALS, alice, sender=alice)
    bob_shares = vault.deposit(10_000 * SIX_DECIMALS, bob, sender=bob)

    # Deploy funds to yield
    vault.depositForYield(
        2,
        mock_usdc.address,
        mock_usdc_collateral_vault.address,
        20_000 * SIX_DECIMALS,
        sender=starter_agent.address
    )

    # Generate some yield
    mock_usdc.mint(mock_usdc_collateral_vault.address, 2_000 * SIX_DECIMALS, sender=governance.address)

    # Advance time to allow snapshot update
    boa.env.time_travel(seconds=60 * 11)  # 11 minutes

    # Update price snapshot to reflect the new yield
    mock_yield_lego.addPriceSnapshot(mock_usdc_collateral_vault.address, sender=switchboard_alpha.address)

    # Simulate front-running on withdrawal:
    # Bob wants to withdraw
    # Alice sees this and front-runs

    initial_alice_balance = mock_usdc.balanceOf(alice)
    initial_bob_balance = mock_usdc.balanceOf(bob)

    # Alice front-runs withdrawal
    alice_withdrawn = vault.redeem(alice_shares, alice, alice, sender=alice)

    # Bob withdraws after
    bob_withdrawn = vault.redeem(bob_shares, bob, bob, sender=bob)

    # Both should get same amount (they had same shares)
    assert alice_withdrawn == bob_withdrawn

    # Verify both got their principal + equal yield
    assert alice_withdrawn > 10_000 * SIX_DECIMALS
    assert bob_withdrawn > 10_000 * SIX_DECIMALS


def test_multiple_users_different_vault_types(
    setup_prices,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    alice,
    bob,
    charlie,
    governance,
    vault_registry,
    switchboard_alpha,
):
    """Test multiple users interacting with different vault types simultaneously"""

    # Enable all vaults
    for vault in [undy_levg_vault_usdc, undy_levg_vault_cbbtc, undy_levg_vault_weth]:
        vault_registry.setCanDeposit(vault.address, True, sender=switchboard_alpha.address)
        vault_registry.setCanWithdraw(vault.address, True, sender=switchboard_alpha.address)

    # Alice uses USDC vault
    mock_usdc.mint(alice, 10_000 * SIX_DECIMALS, sender=governance.address)
    mock_usdc.approve(undy_levg_vault_usdc.address, MAX_UINT256, sender=alice)
    alice_shares_usdc = undy_levg_vault_usdc.deposit(10_000 * SIX_DECIMALS, alice, sender=alice)

    # Bob uses CBBTC vault
    mock_cbbtc.mint(bob, 1 * EIGHT_DECIMALS, sender=governance.address)
    mock_cbbtc.approve(undy_levg_vault_cbbtc.address, MAX_UINT256, sender=bob)
    bob_shares_cbbtc = undy_levg_vault_cbbtc.deposit(1 * EIGHT_DECIMALS, bob, sender=bob)

    # Charlie uses WETH vault
    boa.env.set_balance(charlie, 5 * EIGHTEEN_DECIMALS)
    mock_weth.deposit(value=5 * EIGHTEEN_DECIMALS, sender=charlie)
    mock_weth.approve(undy_levg_vault_weth.address, MAX_UINT256, sender=charlie)
    charlie_shares_weth = undy_levg_vault_weth.deposit(5 * EIGHTEEN_DECIMALS, charlie, sender=charlie)

    # Verify all vaults have independent share accounting
    assert undy_levg_vault_usdc.balanceOf(alice, sender=alice) == alice_shares_usdc
    assert undy_levg_vault_cbbtc.balanceOf(bob, sender=bob) == bob_shares_cbbtc
    assert undy_levg_vault_weth.balanceOf(charlie, sender=charlie) == charlie_shares_weth

    # Each vault maintains its own total supply
    assert undy_levg_vault_usdc.totalSupply(sender=alice) == alice_shares_usdc
    assert undy_levg_vault_cbbtc.totalSupply(sender=bob) == bob_shares_cbbtc
    assert undy_levg_vault_weth.totalSupply(sender=charlie) == charlie_shares_weth

    # All can redeem independently with minAmountOut to handle rounding
    alice_min = 10_000 * SIX_DECIMALS * 999 // 1000
    alice_redeemed = undy_levg_vault_usdc.redeemWithMinAmountOut(alice_shares_usdc, alice_min, alice, alice, sender=alice)

    bob_min = 1 * EIGHT_DECIMALS * 999 // 1000
    bob_redeemed = undy_levg_vault_cbbtc.redeemWithMinAmountOut(bob_shares_cbbtc, bob_min, bob, bob, sender=bob)

    charlie_min = 5 * EIGHTEEN_DECIMALS * 999 // 1000
    charlie_redeemed = undy_levg_vault_weth.redeemWithMinAmountOut(charlie_shares_weth, charlie_min, charlie, charlie, sender=charlie)

    # Verify redemptions
    assert alice_redeemed >= alice_min
    assert bob_redeemed >= bob_min
    assert charlie_redeemed >= charlie_min


def test_deposit_withdraw_same_block(
    setup_prices,
    setup_vault_for_multi_user,
    mock_usdc,
    alice,
    governance,
):
    """Test user depositing and withdrawing in the same block"""
    vault = setup_vault_for_multi_user

    # Give Alice USDC
    mock_usdc.mint(alice, 10_000 * SIX_DECIMALS, sender=governance.address)
    mock_usdc.approve(vault.address, MAX_UINT256, sender=alice)

    # Deposit and immediately withdraw in "same block"
    deposit_amount = 10_000 * SIX_DECIMALS
    shares = vault.deposit(deposit_amount, alice, sender=alice)

    # Immediately withdraw
    withdrawn = vault.redeem(shares, alice, alice, sender=alice)

    # Should get exact amount back (no yield accrued)
    assert withdrawn == deposit_amount

    # Vault should be empty
    assert vault.totalSupply(sender=alice) == 0
    assert vault.totalAssets(sender=alice) == 0


def test_many_small_deposits_vs_one_large(
    setup_prices,
    setup_vault_for_multi_user,
    mock_usdc,
    alice,
    bob,
    governance,
):
    """Test that many small deposits equal one large deposit in share allocation"""
    vault = setup_vault_for_multi_user

    # Give users USDC
    mock_usdc.mint(alice, 10_000 * SIX_DECIMALS, sender=governance.address)
    mock_usdc.mint(bob, 10_000 * SIX_DECIMALS, sender=governance.address)

    mock_usdc.approve(vault.address, MAX_UINT256, sender=alice)
    mock_usdc.approve(vault.address, MAX_UINT256, sender=bob)

    # Alice does 100 small deposits of 100 USDC each
    alice_total_shares = 0
    for _ in range(100):
        shares = vault.deposit(100 * SIX_DECIMALS, alice, sender=alice)
        alice_total_shares += shares

    # Bob does one large deposit of 10,000 USDC
    bob_shares = vault.deposit(10_000 * SIX_DECIMALS, bob, sender=bob)

    # Both should have equal shares
    assert alice_total_shares == bob_shares

    # Both should have equal claim on assets
    alice_assets = vault.convertToAssets(alice_total_shares, sender=alice)
    bob_assets = vault.convertToAssets(bob_shares, sender=bob)
    assert alice_assets == bob_assets


def test_user_cannot_grief_others_by_donating(
    setup_prices,
    setup_vault_for_multi_user,
    mock_usdc,
    alice,
    bob,
    governance,
):
    """Test that donating assets to vault doesn't harm other users"""
    vault = setup_vault_for_multi_user

    # Give users USDC
    mock_usdc.mint(alice, 20_000 * SIX_DECIMALS, sender=governance.address)
    mock_usdc.mint(bob, 10_000 * SIX_DECIMALS, sender=governance.address)

    # Bob deposits first
    mock_usdc.approve(vault.address, MAX_UINT256, sender=bob)
    bob_deposit = 10_000 * SIX_DECIMALS
    bob_shares = vault.deposit(bob_deposit, bob, sender=bob)
    bob_initial_value = vault.convertToAssets(bob_shares, sender=bob)

    # Alice donates to vault (griefing attempt)
    donation = 5_000 * SIX_DECIMALS
    mock_usdc.transfer(vault.address, donation, sender=alice)

    # Bob's shares should now be worth more (he benefits from donation)
    bob_new_value = vault.convertToAssets(bob_shares, sender=bob)
    assert bob_new_value > bob_initial_value

    # Alice deposits after donating
    mock_usdc.approve(vault.address, MAX_UINT256, sender=alice)
    alice_deposit = 10_000 * SIX_DECIMALS
    alice_shares = vault.deposit(alice_deposit, alice, sender=alice)

    # Alice gets fewer shares due to her own donation increasing share price
    assert alice_shares < alice_deposit

    # But both users can still redeem fairly
    bob_redeemed = vault.redeem(bob_shares, bob, bob, sender=bob)
    alice_redeemed = vault.redeem(alice_shares, alice, alice, sender=alice)

    # Bob profits from the donation
    assert bob_redeemed > bob_deposit

    # Alice gets back her deposit (minus the donation she gave away)
    assert alice_redeemed == alice_deposit