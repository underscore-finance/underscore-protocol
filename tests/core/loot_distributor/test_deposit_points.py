"""
Test LootDistributor deposit points functionality
"""
import pytest
import boa
from constants import EIGHTEEN_DECIMALS


def test_update_deposit_points_accumulation(setup_contracts, ledger, switchboard_alpha):
    """Test deposit points accumulation over time"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    
    # Set initial USD value with no points
    initial_block = boa.env.evm.patch.block_number
    user_points = (
        1000 * EIGHTEEN_DECIMALS,  # usdValue
        0,  # depositPoints
        initial_block  # lastUpdate
    )
    global_points = (
        5000 * EIGHTEEN_DECIMALS,  # usdValue (total across all users)
        0,  # depositPoints
        initial_block  # lastUpdate
    )
    ledger.setUserAndGlobalPoints(bob_wallet.address, user_points, global_points, sender=loot.address)
    
    # Advance 100 blocks
    boa.env.time_travel(blocks=100)
    
    # Update points
    loot.updateDepositPoints(bob_wallet.address, sender=switchboard_alpha.address)
    
    # Check points accumulated
    updated_user, updated_global = ledger.getUserAndGlobalPoints(bob_wallet.address)
    
    # User should have: (1000 * 10^18 * 100 blocks) / 10^18 = 100000 points
    assert updated_user.depositPoints == 100000
    assert updated_user.lastUpdate == initial_block + 100
    
    # Global should have: (5000 * 10^18 * 100 blocks) / 10^18 = 500000 points
    assert updated_global.depositPoints == 500000
    assert updated_global.lastUpdate == initial_block + 100


def test_update_deposit_points_with_data(setup_contracts, ledger, switchboard_alpha):
    """Test deposit points update with value change using updateDepositPointsWithData"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    alice_wallet = ctx['alice_wallet']
    
    # Set initial state
    initial_block = boa.env.evm.patch.block_number
    user_points = (
        500 * EIGHTEEN_DECIMALS,  # usdValue
        0,  # depositPoints
        initial_block
    )
    global_points = (
        2000 * EIGHTEEN_DECIMALS,  # usdValue
        0,  # depositPoints
        initial_block
    )
    ledger.setUserAndGlobalPoints(alice_wallet.address, user_points, global_points, sender=loot.address)
    
    # Advance blocks
    boa.env.time_travel(blocks=50)
    
    # Update with new value using switchboard
    new_value = 800 * EIGHTEEN_DECIMALS
    loot.updateDepositPointsWithData(
        alice_wallet.address, 
        new_value,
        True,  # didChange
        sender=switchboard_alpha.address
    )
    
    # Check updated values
    updated_user, updated_global = ledger.getUserAndGlobalPoints(alice_wallet.address)
    
    # User points: (500 * 10^18 * 50) / 10^18 = 25000
    assert updated_user.depositPoints == 25000
    assert updated_user.usdValue == new_value
    
    # Global points: (2000 * 10^18 * 50) / 10^18 = 100000
    assert updated_global.depositPoints == 100000
    # Global value: 2000 - 500 + 800 = 2300
    assert updated_global.usdValue == 2300 * EIGHTEEN_DECIMALS


def test_deposit_points_zero_value(setup_contracts, ledger, switchboard_alpha):
    """Test that zero USD value generates no points"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    
    # Set zero USD value
    initial_block = boa.env.evm.patch.block_number
    user_points = (0, 0, initial_block)
    global_points = (1000 * EIGHTEEN_DECIMALS, 0, initial_block)
    ledger.setUserAndGlobalPoints(bob_wallet.address, user_points, global_points, sender=loot.address)
    
    # Advance many blocks
    boa.env.time_travel(blocks=1000)
    
    # Update points
    loot.updateDepositPoints(bob_wallet.address, sender=switchboard_alpha.address)
    
    # Should have no points
    updated_user, _ = ledger.getUserAndGlobalPoints(bob_wallet.address)
    assert updated_user.depositPoints == 0


def test_deposit_points_multiple_updates_merged(setup_contracts, ledger, switchboard_alpha):
    """Test multiple updates and idempotency in same block"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    
    # Initial setup
    initial_block = boa.env.evm.patch.block_number
    user_points = (1000 * EIGHTEEN_DECIMALS, 0, initial_block)
    global_points = (2000 * EIGHTEEN_DECIMALS, 0, initial_block)
    ledger.setUserAndGlobalPoints(bob_wallet.address, user_points, global_points, sender=loot.address)
    
    # First update after 10 blocks
    boa.env.time_travel(blocks=10)
    loot.updateDepositPoints(bob_wallet.address, sender=switchboard_alpha.address)
    
    user1, global1 = ledger.getUserAndGlobalPoints(bob_wallet.address)
    assert user1.depositPoints == 10000  # (1000 * 10)
    assert global1.depositPoints == 20000  # (2000 * 10)
    
    # Second update after another 20 blocks
    boa.env.time_travel(blocks=20)
    loot.updateDepositPoints(bob_wallet.address, sender=switchboard_alpha.address)
    
    user2, global2 = ledger.getUserAndGlobalPoints(bob_wallet.address)
    assert user2.depositPoints == 30000  # 10000 + (1000 * 20)
    assert global2.depositPoints == 60000  # 20000 + (2000 * 20)
    
    # Third update in same block (idempotency check)
    loot.updateDepositPoints(bob_wallet.address, sender=switchboard_alpha.address)
    
    user3, global3 = ledger.getUserAndGlobalPoints(bob_wallet.address)
    assert user3.depositPoints == user2.depositPoints
    assert user3.lastUpdate == user2.lastUpdate


def test_deposit_points_no_blocks_elapsed(setup_contracts, ledger, switchboard_alpha):
    """Test updating points when no blocks have elapsed"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    
    # Set initial points
    current_block = boa.env.evm.patch.block_number
    user_points = (
        1000 * EIGHTEEN_DECIMALS,  # usdValue
        50 * EIGHTEEN_DECIMALS,  # depositPoints
        current_block
    )
    ledger.setUserAndGlobalPoints(bob_wallet.address, user_points, user_points, sender=loot.address)
    
    # Update without advancing blocks
    loot.updateDepositPoints(bob_wallet.address, sender=switchboard_alpha.address)
    
    # No new points should accumulate
    updated_user, _ = ledger.getUserAndGlobalPoints(bob_wallet.address)
    assert updated_user.depositPoints == 50 * EIGHTEEN_DECIMALS
    assert updated_user.lastUpdate == current_block


def test_points_calculation_precision(setup_contracts, ledger, switchboard_alpha):
    """Test deposit points calculation maintains precision"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    
    # Set small USD value to test precision
    initial_block = boa.env.evm.patch.block_number
    user_points = (
        1,  # 1 wei worth
        0,  # depositPoints
        initial_block
    )
    global_points = user_points
    ledger.setUserAndGlobalPoints(bob_wallet.address, user_points, global_points, sender=loot.address)
    
    # Advance many blocks
    boa.env.time_travel(blocks=10**18)
    
    # Update points
    loot.updateDepositPoints(bob_wallet.address, sender=switchboard_alpha.address)
    
    # Should have (1 * 10^18) / 10^18 = 1 point
    updated_user, _ = ledger.getUserAndGlobalPoints(bob_wallet.address)
    assert updated_user.depositPoints == 1


def test_points_with_large_values(setup_contracts, ledger, switchboard_alpha):
    """Test deposit points with large USD values"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    
    # Set large USD value
    initial_block = boa.env.evm.patch.block_number
    large_value = 10**15 * EIGHTEEN_DECIMALS  # 1 quadrillion USD worth
    user_points = (large_value, 0, initial_block)
    global_points = user_points
    ledger.setUserAndGlobalPoints(bob_wallet.address, user_points, global_points, sender=loot.address)
    
    # Advance 1 block
    boa.env.time_travel(blocks=1)
    
    # Update points
    loot.updateDepositPoints(bob_wallet.address, sender=switchboard_alpha.address)
    
    # Check calculation doesn't overflow
    updated_user, _ = ledger.getUserAndGlobalPoints(bob_wallet.address)
    assert updated_user.depositPoints == 10**15  # (10^15 * 10^18 * 1) / 10^18


def test_global_points_tracking(setup_contracts, ledger, switchboard_alpha):
    """Test global points track all users correctly"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alice_wallet = ctx['alice_wallet']
    
    # Set initial values for Bob
    initial_block = boa.env.evm.patch.block_number
    bob_points = (600 * EIGHTEEN_DECIMALS, 0, initial_block)
    global_points = (1000 * EIGHTEEN_DECIMALS, 0, initial_block)
    ledger.setUserAndGlobalPoints(bob_wallet.address, bob_points, global_points, sender=loot.address)
    
    # Set initial values for Alice  
    alice_points = (400 * EIGHTEEN_DECIMALS, 0, initial_block)
    ledger.setUserAndGlobalPoints(alice_wallet.address, alice_points, global_points, sender=loot.address)
    
    # Advance blocks
    boa.env.time_travel(blocks=100)
    
    # Update Bob's points
    loot.updateDepositPoints(bob_wallet.address, sender=switchboard_alpha.address)
    
    # Global should accumulate: (1000 * 100)
    _, global1 = ledger.getUserAndGlobalPoints(bob_wallet.address)
    assert global1.depositPoints == 100000
    
    # Update Alice's value via switchboard
    loot.updateDepositPointsWithData(
        alice_wallet.address,
        800 * EIGHTEEN_DECIMALS,
        True,
        sender=switchboard_alpha.address
    )
    
    # Global should now have: 100000 (from Bob's update) + Alice's points (1000 * 100) = 200000
    # But Alice's update happens during the switchboard call, so total is (1000 * 100) + (1000 * 100) = 200000
    # Actually, since Alice starts with different global base, we need to check the actual calculation
    # Global value should be: 1000 - 400 + 800 = 1400
    _, global2 = ledger.getUserAndGlobalPoints(alice_wallet.address)
    # Alice's update adds her accumulated points: (1000 * 100) = 100000, so total stays 100000
    # because Bob and Alice both had the same global USD value base of 1000
    assert global2.depositPoints == 100000  # Only Alice's accumulated points
    assert global2.usdValue == 1400 * EIGHTEEN_DECIMALS


def test_points_with_value_decrease(setup_contracts, ledger, switchboard_alpha):
    """Test points when USD value decreases"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    
    # Set initial high value
    initial_block = boa.env.evm.patch.block_number
    user_points = (
        1000 * EIGHTEEN_DECIMALS,  # usdValue
        0,  # depositPoints
        initial_block
    )
    global_points = (
        1500 * EIGHTEEN_DECIMALS,  # usdValue
        0,  # depositPoints
        initial_block
    )
    ledger.setUserAndGlobalPoints(bob_wallet.address, user_points, global_points, sender=loot.address)
    
    # Advance blocks
    boa.env.time_travel(blocks=50)
    
    # Decrease value to 300
    loot.updateDepositPointsWithData(
        bob_wallet.address,
        300 * EIGHTEEN_DECIMALS,
        True,
        sender=switchboard_alpha.address
    )
    
    # Check points accumulated before decrease
    updated_user, updated_global = ledger.getUserAndGlobalPoints(bob_wallet.address)
    assert updated_user.depositPoints == 50000  # (1000 * 50)
    assert updated_user.usdValue == 300 * EIGHTEEN_DECIMALS
    
    # Global value: 1500 - 1000 + 300 = 800
    assert updated_global.usdValue == 800 * EIGHTEEN_DECIMALS