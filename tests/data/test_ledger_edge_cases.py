import pytest
import boa
from constants import ZERO_ADDRESS, EIGHTEEN_DECIMALS


def test_user_wallet_index_starts_at_one(ledger, hatchery, alice, bob):
    """Test that user wallet indices are sequential and don't use 0"""
    # Get initial count to know what indices to expect
    initial_count = ledger.getNumUserWallets()
    
    # Create first user wallet
    ledger.createUserWallet(alice, ZERO_ADDRESS, sender=hatchery.address)
    
    # Alice should get the next available index
    alice_index = ledger.indexOfUserWallet(alice)
    assert alice_index == initial_count + 1
    assert ledger.userWallets(alice_index) == alice
    
    # Create second wallet
    ledger.createUserWallet(bob, ZERO_ADDRESS, sender=hatchery.address)
    
    # Bob should get the next sequential index
    bob_index = ledger.indexOfUserWallet(bob)
    assert bob_index == initial_count + 2
    assert ledger.userWallets(bob_index) == bob
    
    # Index 0 should never be used
    assert ledger.userWallets(0) == ZERO_ADDRESS


def test_agent_index_starts_at_one(ledger, hatchery, alice, bob):
    """Test that agent indices are sequential and don't use 0"""
    # Get initial count to know what indices to expect
    initial_count = ledger.getNumAgents()
    
    # Create first agent
    ledger.createAgent(alice, sender=hatchery.address)
    
    # Alice should get the next available index
    alice_index = ledger.indexOfAgent(alice)
    assert alice_index == initial_count + 1
    assert ledger.agents(alice_index) == alice
    
    # Create second agent
    ledger.createAgent(bob, sender=hatchery.address)
    
    # Bob should get the next sequential index
    bob_index = ledger.indexOfAgent(bob)
    assert bob_index == initial_count + 2
    assert ledger.agents(bob_index) == bob
    
    # Index 0 should never be used
    assert ledger.agents(0) == ZERO_ADDRESS


def test_same_address_as_wallet_and_agent(ledger, hatchery, alice):
    """Test that same address can be both user wallet and agent"""
    # Create user wallet
    ledger.createUserWallet(alice, ZERO_ADDRESS, sender=hatchery.address)
    assert ledger.isUserWallet(alice) == True
    
    # Create agent with same address
    ledger.createAgent(alice, sender=hatchery.address)
    assert ledger.isAgent(alice) == True
    
    # Both should exist independently
    assert ledger.isUserWallet(alice) == True
    assert ledger.isAgent(alice) == True
    
    # Indices are from independent counters, so they can be the same value
    wallet_index = ledger.indexOfUserWallet(alice)
    agent_index = ledger.indexOfAgent(alice)
    assert wallet_index > 0
    assert agent_index > 0
    
    # Verify alice appears in both mappings
    assert ledger.userWallets(wallet_index) == alice
    assert ledger.agents(agent_index) == alice


def test_ambassador_as_zero_address(ledger, hatchery, alice):
    """Test creating user wallet with zero address as ambassador"""
    # Create wallet with zero address ambassador
    ledger.createUserWallet(alice, ZERO_ADDRESS, sender=hatchery.address)
    
    # Ambassador should be zero address
    assert ledger.ambassadors(alice) == ZERO_ADDRESS


def test_points_data_struct_fields(ledger, loot_distributor, alice):
    """Test that points data struct fields are correctly set and retrieved"""
    usd_value = 12345 * EIGHTEEN_DECIMALS
    deposit_points = 6789
    last_update = 98765
    
    points_data = (usd_value, deposit_points, last_update)
    
    # Set user points
    ledger.setUserPoints(alice, points_data, sender=loot_distributor.address)
    
    # Verify each field individually
    stored_points = ledger.userPoints(alice)
    assert stored_points[0] == usd_value  # usdValue
    assert stored_points[1] == deposit_points  # depositPoints
    assert stored_points[2] == last_update  # lastUpdate
    
    # Verify USD value getter works
    assert ledger.getLastTotalUsdValue(alice) == usd_value


def test_overwrite_existing_points(ledger, loot_distributor, alice):
    """Test overwriting existing points data"""
    # Set initial points
    initial_data = (100 * EIGHTEEN_DECIMALS, 50, 1000)
    ledger.setUserPoints(alice, initial_data, sender=loot_distributor.address)
    
    # Verify initial data
    stored = ledger.userPoints(alice)
    assert stored[0] == 100 * EIGHTEEN_DECIMALS
    
    # Overwrite with new data
    new_data = (200 * EIGHTEEN_DECIMALS, 100, 2000)
    ledger.setUserPoints(alice, new_data, sender=loot_distributor.address)
    
    # Verify data was overwritten (not added)
    stored = ledger.userPoints(alice)
    assert stored[0] == 200 * EIGHTEEN_DECIMALS
    assert stored[1] == 100
    assert stored[2] == 2000


def test_points_precision_with_eighteen_decimals(ledger, loot_distributor, alice):
    """Test points handling with 18 decimal precision"""
    # Use precise values
    precise_value = 1234567890123456789  # 1.234567890123456789 ETH
    points_data = (precise_value, 999999999999999999, 123456789)
    
    ledger.setUserPoints(alice, points_data, sender=loot_distributor.address)
    
    # Verify precision is maintained
    stored = ledger.userPoints(alice)
    assert stored[0] == precise_value
    assert stored[1] == 999999999999999999
    assert stored[2] == 123456789


def test_global_points_independence_from_user_points(ledger, loot_distributor, alice, bob):
    """Test that global points are independent from user points"""
    # Set different user points for multiple users
    alice_data = (100 * EIGHTEEN_DECIMALS, 50, 1000)
    bob_data = (200 * EIGHTEEN_DECIMALS, 100, 2000)
    
    ledger.setUserPoints(alice, alice_data, sender=loot_distributor.address)
    ledger.setUserPoints(bob, bob_data, sender=loot_distributor.address)
    
    # Set global points independently
    global_data = (500 * EIGHTEEN_DECIMALS, 250, 3000)
    ledger.setGlobalPoints(global_data, sender=loot_distributor.address)
    
    # Verify global points are same for both users
    alice_user, alice_global = ledger.getUserAndGlobalPoints(alice)
    bob_user, bob_global = ledger.getUserAndGlobalPoints(bob)
    
    # User points should be different
    assert alice_user[0] == 100 * EIGHTEEN_DECIMALS
    assert bob_user[0] == 200 * EIGHTEEN_DECIMALS
    
    # Global points should be same
    assert alice_global[0] == 500 * EIGHTEEN_DECIMALS
    assert bob_global[0] == 500 * EIGHTEEN_DECIMALS
    assert alice_global[1] == 250
    assert bob_global[1] == 250
    assert alice_global[2] == 3000
    assert bob_global[2] == 3000


def test_maximum_uint256_values(ledger, loot_distributor, alice):
    """Test setting maximum uint256 values"""
    max_uint256 = 2**256 - 1
    max_data = (max_uint256, max_uint256, max_uint256)
    
    # Should handle maximum values
    ledger.setUserPoints(alice, max_data, sender=loot_distributor.address)
    
    stored = ledger.userPoints(alice)
    assert stored[0] == max_uint256
    assert stored[1] == max_uint256
    assert stored[2] == max_uint256
    
    # Test global points with max values
    ledger.setGlobalPoints(max_data, sender=loot_distributor.address)
    
    global_stored = ledger.globalPoints()
    assert global_stored[0] == max_uint256
    assert global_stored[1] == max_uint256
    assert global_stored[2] == max_uint256


def test_zero_values_edge_case(ledger, loot_distributor, alice):
    """Test all zero values edge case"""
    zero_data = (0, 0, 0)
    
    # Should handle all zero values
    ledger.setUserAndGlobalPoints(alice, zero_data, zero_data, sender=loot_distributor.address)
    
    user_stored = ledger.userPoints(alice)
    global_stored = ledger.globalPoints()
    
    # User points
    assert user_stored[0] == 0
    assert user_stored[1] == 0
    assert user_stored[2] == 0
    
    # Global points
    assert global_stored[0] == 0
    assert global_stored[1] == 0
    assert global_stored[2] == 0
    
    # USD value should be zero
    assert ledger.getLastTotalUsdValue(alice) == 0


def test_large_number_of_wallets_and_agents(ledger, hatchery, alice, bob, charlie, deploy3r, agent_eoa):
    """Test creating multiple wallets and agents"""
    addresses = [alice, bob, charlie, deploy3r, agent_eoa]
    
    # Get initial counts
    initial_wallet_count = ledger.getNumUserWallets()
    initial_agent_count = ledger.getNumAgents()
    
    # Create wallets for all addresses with specific ambassador chain
    ledger.createUserWallet(addresses[0], ZERO_ADDRESS, sender=hatchery.address)  # alice: no ambassador
    ledger.createUserWallet(addresses[1], addresses[0], sender=hatchery.address)  # bob: alice ambassador
    ledger.createUserWallet(addresses[2], addresses[1], sender=hatchery.address)  # charlie: bob ambassador 
    ledger.createUserWallet(addresses[3], addresses[2], sender=hatchery.address)  # deploy3r: charlie ambassador
    ledger.createUserWallet(addresses[4], addresses[3], sender=hatchery.address)  # agent_eoa: deploy3r ambassador
    
    # Create agents for all addresses
    for addr in addresses:
        ledger.createAgent(addr, sender=hatchery.address)
    
    # Verify all wallets and agents exist
    for addr in addresses:
        assert ledger.isUserWallet(addr) == True
        assert ledger.isAgent(addr) == True
    
    # Verify counts increased correctly
    assert ledger.getNumUserWallets() == initial_wallet_count + len(addresses)
    assert ledger.getNumAgents() == initial_agent_count + len(addresses)
    
    # Verify ambassador chain
    assert ledger.ambassadors(alice) == ZERO_ADDRESS
    assert ledger.ambassadors(bob) == alice
    assert ledger.ambassadors(charlie) == bob
    assert ledger.ambassadors(deploy3r) == charlie
    assert ledger.ambassadors(agent_eoa) == deploy3r


def test_points_functions_only_loot_distributor(ledger, hatchery, switchboard_alpha, alice, bob):
    """Test that only loot distributor can call points functions"""
    points_data = (100 * EIGHTEEN_DECIMALS, 50, 1000)
    
    # Hatchery cannot call points functions
    with boa.reverts("only loot distributor allowed"):
        ledger.setUserPoints(alice, points_data, sender=hatchery.address)
    
    with boa.reverts("only loot distributor allowed"):
        ledger.setGlobalPoints(points_data, sender=hatchery.address)
    
    with boa.reverts("only loot distributor allowed"):
        ledger.setUserAndGlobalPoints(alice, points_data, points_data, sender=hatchery.address)
    
    # Switchboard cannot call points functions
    with boa.reverts("only loot distributor allowed"):
        ledger.setUserPoints(alice, points_data, sender=switchboard_alpha.address)
    
    with boa.reverts("only loot distributor allowed"):
        ledger.setGlobalPoints(points_data, sender=switchboard_alpha.address)
    
    with boa.reverts("only loot distributor allowed"):
        ledger.setUserAndGlobalPoints(alice, points_data, points_data, sender=switchboard_alpha.address)
    
    # Random user cannot call points functions
    with boa.reverts("only loot distributor allowed"):
        ledger.setUserPoints(alice, points_data, sender=bob)
    
    with boa.reverts("only loot distributor allowed"):
        ledger.setGlobalPoints(points_data, sender=bob)
    
    with boa.reverts("only loot distributor allowed"):
        ledger.setUserAndGlobalPoints(alice, points_data, points_data, sender=bob)


def test_wallet_agent_creation_only_hatchery(ledger, loot_distributor, switchboard_alpha, alice, bob):
    """Test that only hatchery can create wallets and agents"""
    # Loot distributor cannot create wallets/agents
    with boa.reverts("only hatchery allowed"):
        ledger.createUserWallet(alice, ZERO_ADDRESS, sender=loot_distributor.address)
    
    with boa.reverts("only hatchery allowed"):
        ledger.createAgent(alice, sender=loot_distributor.address)
    
    # Switchboard cannot create wallets/agents
    with boa.reverts("only hatchery allowed"):
        ledger.createUserWallet(alice, ZERO_ADDRESS, sender=switchboard_alpha.address)
    
    with boa.reverts("only hatchery allowed"):
        ledger.createAgent(alice, sender=switchboard_alpha.address)
    
    # Random user cannot create wallets/agents
    with boa.reverts("only hatchery allowed"):
        ledger.createUserWallet(alice, ZERO_ADDRESS, sender=bob)
    
    with boa.reverts("only hatchery allowed"):
        ledger.createAgent(alice, sender=bob)


def test_pause_functionality_access_control(ledger, hatchery, loot_distributor, alice):
    """Test that only switchboard can pause/unpause"""
    # Hatchery cannot pause
    with boa.reverts("no perms"):
        ledger.pause(True, sender=hatchery.address)
    
    # Loot distributor cannot pause
    with boa.reverts("no perms"):
        ledger.pause(True, sender=loot_distributor.address)
    
    # Random user cannot pause
    with boa.reverts("no perms"):
        ledger.pause(True, sender=alice)


def test_points_functions_no_pause_check(ledger, loot_distributor, switchboard_alpha, alice):
    """Test that points functions work even when paused (security concern)"""
    # Pause the contract
    ledger.pause(True, sender=switchboard_alpha.address)
    assert ledger.isPaused() == True
    
    # Points functions should still work when paused (this is concerning!)
    points_data = (100 * EIGHTEEN_DECIMALS, 50, 1000)
    
    # These should work even when paused - potential security issue
    ledger.setUserPoints(alice, points_data, sender=loot_distributor.address)
    ledger.setGlobalPoints(points_data, sender=loot_distributor.address)
    ledger.setUserAndGlobalPoints(alice, points_data, points_data, sender=loot_distributor.address)
    
    # Verify points were actually set
    stored = ledger.userPoints(alice)
    assert stored[0] == 100 * EIGHTEEN_DECIMALS


def test_user_wallet_count_consistency(ledger, hatchery, alice, bob, charlie):
    """Test that user wallet count stays consistent"""
    initial_count = ledger.getNumUserWallets()
    
    # Create wallets one by one and verify count
    ledger.createUserWallet(alice, ZERO_ADDRESS, sender=hatchery.address)
    assert ledger.getNumUserWallets() == initial_count + 1
    
    ledger.createUserWallet(bob, ZERO_ADDRESS, sender=hatchery.address)
    assert ledger.getNumUserWallets() == initial_count + 2
    
    ledger.createUserWallet(charlie, ZERO_ADDRESS, sender=hatchery.address)
    assert ledger.getNumUserWallets() == initial_count + 3
    
    # Verify internal counter matches public getter
    assert ledger.numUserWallets() == initial_count + 3 + 1  # +1 because internal counter is one ahead


def test_agent_count_consistency(ledger, hatchery, alice, bob, charlie):
    """Test that agent count stays consistent"""
    initial_count = ledger.getNumAgents()
    
    # Create agents one by one and verify count
    ledger.createAgent(alice, sender=hatchery.address)
    assert ledger.getNumAgents() == initial_count + 1
    
    ledger.createAgent(bob, sender=hatchery.address)
    assert ledger.getNumAgents() == initial_count + 2
    
    ledger.createAgent(charlie, sender=hatchery.address)
    assert ledger.getNumAgents() == initial_count + 3
    
    # Verify internal counter matches public getter
    assert ledger.numAgents() == initial_count + 3 + 1  # +1 because internal counter is one ahead


def test_index_mapping_bidirectional_consistency(ledger, hatchery, alice, bob):
    """Test that index mappings are bidirectionally consistent"""
    # Create user wallets
    ledger.createUserWallet(alice, ZERO_ADDRESS, sender=hatchery.address)
    ledger.createUserWallet(bob, ZERO_ADDRESS, sender=hatchery.address)
    
    # Verify bidirectional mapping for wallets
    alice_index = ledger.indexOfUserWallet(alice)
    bob_index = ledger.indexOfUserWallet(bob)
    
    assert ledger.userWallets(alice_index) == alice
    assert ledger.userWallets(bob_index) == bob
    assert alice_index != bob_index
    
    # Create agents
    ledger.createAgent(alice, sender=hatchery.address)
    ledger.createAgent(bob, sender=hatchery.address)
    
    # Verify bidirectional mapping for agents
    alice_agent_index = ledger.indexOfAgent(alice)
    bob_agent_index = ledger.indexOfAgent(bob)
    
    assert ledger.agents(alice_agent_index) == alice
    assert ledger.agents(bob_agent_index) == bob
    assert alice_agent_index != bob_agent_index
    
    # Wallet and agent indices use independent counters
    # They may have same values but reference different mappings
    assert ledger.userWallets(alice_index) == alice
    assert ledger.agents(alice_agent_index) == alice
    assert ledger.userWallets(bob_index) == bob
    assert ledger.agents(bob_agent_index) == bob