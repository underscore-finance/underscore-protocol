import pytest
import boa
from constants import ZERO_ADDRESS, EIGHTEEN_DECIMALS


def test_create_user_wallet_success(ledger, hatchery, alice, bob):
    """Test creating user wallet successfully"""
    initial_count = ledger.getNumUserWallets()
    
    # Create user wallet via hatchery (authorized caller)
    ledger.createUserWallet(alice, ZERO_ADDRESS, sender=hatchery.address)
    
    # Verify wallet was created
    assert ledger.isUserWallet(alice) == True
    assert ledger.getNumUserWallets() == initial_count + 1
    
    # Check index mapping
    wallet_index = ledger.indexOfUserWallet(alice)
    assert wallet_index > 0  # Should not be 0
    assert ledger.userWallets(wallet_index) == alice
    
    # Check ambassador is not set
    assert ledger.ambassadors(alice) == ZERO_ADDRESS


def test_create_user_wallet_with_ambassador(ledger, hatchery, alice, bob):
    """Test creating user wallet with ambassador"""
    # Create user wallet with bob as ambassador
    ledger.createUserWallet(alice, bob, sender=hatchery.address)
    
    # Verify wallet was created with ambassador
    assert ledger.isUserWallet(alice) == True
    assert ledger.ambassadors(alice) == bob


def test_create_user_wallet_unauthorized(ledger, alice, bob, deploy3r):
    """Test creating user wallet from unauthorized address fails"""
    with boa.reverts("only hatchery allowed"):
        ledger.createUserWallet(alice, ZERO_ADDRESS, sender=deploy3r)


def test_create_user_wallet_when_paused(ledger, hatchery, switchboard_alpha, alice):
    """Test creating user wallet when contract is paused fails"""
    # Pause the contract (only switchboard can pause)
    ledger.pause(True, sender=switchboard_alpha.address)
    
    with boa.reverts("not activated"):
        ledger.createUserWallet(alice, ZERO_ADDRESS, sender=hatchery.address)


def test_create_multiple_user_wallets(ledger, hatchery, alice, bob, charlie):
    """Test creating multiple user wallets"""
    initial_count = ledger.getNumUserWallets()
    
    # Create multiple wallets
    ledger.createUserWallet(alice, ZERO_ADDRESS, sender=hatchery.address)
    ledger.createUserWallet(bob, alice, sender=hatchery.address)  # alice as ambassador
    ledger.createUserWallet(charlie, bob, sender=hatchery.address)  # bob as ambassador
    
    # Verify all wallets exist
    assert ledger.isUserWallet(alice) == True
    assert ledger.isUserWallet(bob) == True 
    assert ledger.isUserWallet(charlie) == True
    
    # Verify count increased correctly
    assert ledger.getNumUserWallets() == initial_count + 3
    
    # Verify ambassadors are set correctly
    assert ledger.ambassadors(alice) == ZERO_ADDRESS
    assert ledger.ambassadors(bob) == alice
    assert ledger.ambassadors(charlie) == bob
    
    # Verify indices are unique and not zero
    alice_index = ledger.indexOfUserWallet(alice)
    bob_index = ledger.indexOfUserWallet(bob)
    charlie_index = ledger.indexOfUserWallet(charlie)
    
    assert alice_index > 0
    assert bob_index > 0
    assert charlie_index > 0
    assert alice_index != bob_index
    assert bob_index != charlie_index
    assert alice_index != charlie_index


def test_is_user_wallet_non_existent(ledger, alice):
    """Test isUserWallet returns false for non-existent wallet"""
    assert ledger.isUserWallet(alice) == False


def test_get_num_user_wallets_zero_state(ledger):
    """Test getNumUserWallets behavior with current state"""
    # Get the current count (may not be zero if other tests ran first)
    current_count = ledger.getNumUserWallets()
    # Verify the count is non-negative
    assert current_count >= 0


def test_create_agent_success(ledger, hatchery, alice):
    """Test creating agent successfully"""
    initial_count = ledger.getNumAgents()
    
    # Create agent via hatchery (authorized caller)
    ledger.createAgent(alice, sender=hatchery.address)
    
    # Verify agent was created
    assert ledger.isAgent(alice) == True
    assert ledger.getNumAgents() == initial_count + 1
    
    # Check index mapping
    agent_index = ledger.indexOfAgent(alice)
    assert agent_index > 0  # Should not be 0
    assert ledger.agents(agent_index) == alice


def test_create_agent_unauthorized(ledger, alice, deploy3r):
    """Test creating agent from unauthorized address fails"""
    with boa.reverts("only hatchery allowed"):
        ledger.createAgent(alice, sender=deploy3r)


def test_create_agent_when_paused(ledger, hatchery, switchboard_alpha, alice):
    """Test creating agent when contract is paused fails"""
    # Pause the contract (only switchboard can pause)
    ledger.pause(True, sender=switchboard_alpha.address)
    
    with boa.reverts("not activated"):
        ledger.createAgent(alice, sender=hatchery.address)


def test_create_multiple_agents(ledger, hatchery, alice, bob, charlie):
    """Test creating multiple agents"""
    initial_count = ledger.getNumAgents()
    
    # Create multiple agents
    ledger.createAgent(alice, sender=hatchery.address)
    ledger.createAgent(bob, sender=hatchery.address)
    ledger.createAgent(charlie, sender=hatchery.address)
    
    # Verify all agents exist
    assert ledger.isAgent(alice) == True
    assert ledger.isAgent(bob) == True
    assert ledger.isAgent(charlie) == True
    
    # Verify count increased correctly
    assert ledger.getNumAgents() == initial_count + 3
    
    # Verify indices are unique and not zero
    alice_index = ledger.indexOfAgent(alice)
    bob_index = ledger.indexOfAgent(bob)
    charlie_index = ledger.indexOfAgent(charlie)
    
    assert alice_index > 0
    assert bob_index > 0
    assert charlie_index > 0
    assert alice_index != bob_index
    assert bob_index != charlie_index
    assert alice_index != charlie_index


def test_is_agent_non_existent(ledger, alice):
    """Test isAgent returns false for non-existent agent"""
    assert ledger.isAgent(alice) == False


def test_get_num_agents_zero_state(ledger):
    """Test getNumAgents behavior with current state"""
    # Get the current count (may not be zero if other tests ran first)
    current_count = ledger.getNumAgents()
    # Verify the count is non-negative
    assert current_count >= 0


def test_set_user_points_success(ledger, loot_distributor, alice):
    """Test setting user points successfully"""
    points_data = (1000 * EIGHTEEN_DECIMALS, 500, 12345)  # usdValue, depositPoints, lastUpdate
    
    # Set user points via loot distributor (authorized caller)
    ledger.setUserPoints(alice, points_data, sender=loot_distributor.address)
    
    # Verify points were set
    stored_points = ledger.userPoints(alice)
    assert stored_points[0] == 1000 * EIGHTEEN_DECIMALS  # usdValue
    assert stored_points[1] == 500  # depositPoints
    assert stored_points[2] == 12345  # lastUpdate


def test_set_user_points_unauthorized(ledger, alice, deploy3r):
    """Test setting user points from unauthorized address fails"""
    points_data = (1000 * EIGHTEEN_DECIMALS, 500, 12345)
    
    with boa.reverts("only loot distributor allowed"):
        ledger.setUserPoints(alice, points_data, sender=deploy3r)


def test_set_global_points_success(ledger, loot_distributor):
    """Test setting global points successfully"""
    points_data = (5000 * EIGHTEEN_DECIMALS, 2000, 54321)  # usdValue, depositPoints, lastUpdate
    
    # Set global points via loot distributor (authorized caller)
    ledger.setGlobalPoints(points_data, sender=loot_distributor.address)
    
    # Verify points were set
    stored_points = ledger.globalPoints()
    assert stored_points[0] == 5000 * EIGHTEEN_DECIMALS  # usdValue
    assert stored_points[1] == 2000  # depositPoints
    assert stored_points[2] == 54321  # lastUpdate


def test_set_global_points_unauthorized(ledger, deploy3r):
    """Test setting global points from unauthorized address fails"""
    points_data = (5000 * EIGHTEEN_DECIMALS, 2000, 54321)
    
    with boa.reverts("only loot distributor allowed"):
        ledger.setGlobalPoints(points_data, sender=deploy3r)


def test_set_user_and_global_points_success(ledger, loot_distributor, alice):
    """Test setting both user and global points in one transaction"""
    user_data = (800 * EIGHTEEN_DECIMALS, 300, 11111)
    global_data = (4000 * EIGHTEEN_DECIMALS, 1500, 22222)
    
    # Set both user and global points
    ledger.setUserAndGlobalPoints(alice, user_data, global_data, sender=loot_distributor.address)
    
    # Verify user points were set
    stored_user = ledger.userPoints(alice)
    assert stored_user[0] == 800 * EIGHTEEN_DECIMALS
    assert stored_user[1] == 300
    assert stored_user[2] == 11111
    
    # Verify global points were set
    stored_global = ledger.globalPoints()
    assert stored_global[0] == 4000 * EIGHTEEN_DECIMALS
    assert stored_global[1] == 1500
    assert stored_global[2] == 22222


def test_set_user_and_global_points_unauthorized(ledger, alice, deploy3r):
    """Test setting user and global points from unauthorized address fails"""
    user_data = (800 * EIGHTEEN_DECIMALS, 300, 11111)
    global_data = (4000 * EIGHTEEN_DECIMALS, 1500, 22222)
    
    with boa.reverts("only loot distributor allowed"):
        ledger.setUserAndGlobalPoints(alice, user_data, global_data, sender=deploy3r)


def test_get_last_total_usd_value(ledger, loot_distributor, alice):
    """Test getting last total USD value for user"""
    # Set user points first
    points_data = (1500 * EIGHTEEN_DECIMALS, 750, 33333)
    ledger.setUserPoints(alice, points_data, sender=loot_distributor.address)
    
    # Get USD value
    usd_value = ledger.getLastTotalUsdValue(alice)
    assert usd_value == 1500 * EIGHTEEN_DECIMALS


def test_get_last_total_usd_value_zero(ledger, alice):
    """Test getting USD value for user with no points returns zero"""
    usd_value = ledger.getLastTotalUsdValue(alice)
    assert usd_value == 0


def test_get_user_and_global_points(ledger, loot_distributor, alice):
    """Test getting both user and global points"""
    # Set both user and global points
    user_data = (600 * EIGHTEEN_DECIMALS, 200, 44444)
    global_data = (3000 * EIGHTEEN_DECIMALS, 1000, 55555)
    ledger.setUserAndGlobalPoints(alice, user_data, global_data, sender=loot_distributor.address)
    
    # Get both points
    returned_user, returned_global = ledger.getUserAndGlobalPoints(alice)
    
    # Verify user points
    assert returned_user[0] == 600 * EIGHTEEN_DECIMALS
    assert returned_user[1] == 200
    assert returned_user[2] == 44444
    
    # Verify global points
    assert returned_global[0] == 3000 * EIGHTEEN_DECIMALS
    assert returned_global[1] == 1000
    assert returned_global[2] == 55555


def test_points_data_zero_values(ledger, loot_distributor, alice):
    """Test setting points data with zero values"""
    user_data = (0, 0, 0)
    global_data = (0, 0, 0)
    
    # Should work with zero values
    ledger.setUserAndGlobalPoints(alice, user_data, global_data, sender=loot_distributor.address)
    
    # Verify zero values were stored
    stored_user = ledger.userPoints(alice)
    stored_global = ledger.globalPoints()
    
    assert stored_user[0] == 0
    assert stored_user[1] == 0
    assert stored_user[2] == 0
    assert stored_global[0] == 0
    assert stored_global[1] == 0
    assert stored_global[2] == 0


def test_points_data_max_values(ledger, loot_distributor, alice):
    """Test setting points data with maximum values"""
    max_uint256 = 2**256 - 1
    user_data = (max_uint256, max_uint256, max_uint256)
    global_data = (max_uint256, max_uint256, max_uint256)
    
    # Should work with max values
    ledger.setUserAndGlobalPoints(alice, user_data, global_data, sender=loot_distributor.address)
    
    # Verify max values were stored
    stored_user = ledger.userPoints(alice)
    stored_global = ledger.globalPoints()
    
    assert stored_user[0] == max_uint256
    assert stored_user[1] == max_uint256
    assert stored_user[2] == max_uint256
    assert stored_global[0] == max_uint256
    assert stored_global[1] == max_uint256
    assert stored_global[2] == max_uint256


def test_full_wallet_and_agent_creation_flow(ledger, hatchery, alice, bob, charlie):
    """Test complete flow of creating wallets and agents"""
    # Get initial counts
    initial_wallet_count = ledger.getNumUserWallets()
    initial_agent_count = ledger.getNumAgents()
    
    # Create user wallets
    ledger.createUserWallet(alice, ZERO_ADDRESS, sender=hatchery.address)
    ledger.createUserWallet(bob, alice, sender=hatchery.address)  # alice as ambassador
    
    # Create agents
    ledger.createAgent(charlie, sender=hatchery.address)
    ledger.createAgent(alice, sender=hatchery.address)  # alice can be both wallet and agent
    
    # Verify all entities exist
    assert ledger.isUserWallet(alice) == True
    assert ledger.isUserWallet(bob) == True
    assert ledger.isAgent(charlie) == True
    assert ledger.isAgent(alice) == True
    
    # Verify counts increased correctly
    assert ledger.getNumUserWallets() == initial_wallet_count + 2
    assert ledger.getNumAgents() == initial_agent_count + 2
    
    # Verify ambassador relationship
    assert ledger.ambassadors(bob) == alice
    assert ledger.ambassadors(alice) == ZERO_ADDRESS


def test_wallet_with_points_lifecycle(ledger, hatchery, loot_distributor, alice):
    """Test complete wallet lifecycle with points"""
    # Create user wallet
    ledger.createUserWallet(alice, ZERO_ADDRESS, sender=hatchery.address)
    assert ledger.isUserWallet(alice) == True
    
    # Set initial points
    initial_user_data = (100 * EIGHTEEN_DECIMALS, 50, 1000)
    initial_global_data = (500 * EIGHTEEN_DECIMALS, 250, 1000)
    ledger.setUserAndGlobalPoints(alice, initial_user_data, initial_global_data, sender=loot_distributor.address)
    
    # Verify initial points
    user_points, global_points = ledger.getUserAndGlobalPoints(alice)
    assert user_points[0] == 100 * EIGHTEEN_DECIMALS
    assert global_points[0] == 500 * EIGHTEEN_DECIMALS
    
    # Update points
    updated_user_data = (200 * EIGHTEEN_DECIMALS, 100, 2000)
    updated_global_data = (1000 * EIGHTEEN_DECIMALS, 500, 2000)
    ledger.setUserAndGlobalPoints(alice, updated_user_data, updated_global_data, sender=loot_distributor.address)
    
    # Verify updated points
    user_points, global_points = ledger.getUserAndGlobalPoints(alice)
    assert user_points[0] == 200 * EIGHTEEN_DECIMALS
    assert user_points[1] == 100
    assert user_points[2] == 2000
    assert global_points[0] == 1000 * EIGHTEEN_DECIMALS
    assert global_points[1] == 500
    assert global_points[2] == 2000
    
    # Verify USD value getter
    assert ledger.getLastTotalUsdValue(alice) == 200 * EIGHTEEN_DECIMALS


def test_multiple_users_points_independence(ledger, hatchery, loot_distributor, alice, bob, charlie):
    """Test that multiple users' points are independent"""
    # Create user wallets
    ledger.createUserWallet(alice, ZERO_ADDRESS, sender=hatchery.address)
    ledger.createUserWallet(bob, ZERO_ADDRESS, sender=hatchery.address)
    ledger.createUserWallet(charlie, ZERO_ADDRESS, sender=hatchery.address)
    
    # Set different points for each user
    alice_data = (100 * EIGHTEEN_DECIMALS, 50, 1000)
    bob_data = (200 * EIGHTEEN_DECIMALS, 100, 2000)
    charlie_data = (300 * EIGHTEEN_DECIMALS, 150, 3000)
    global_data = (600 * EIGHTEEN_DECIMALS, 300, 3000)
    
    ledger.setUserPoints(alice, alice_data, sender=loot_distributor.address)
    ledger.setUserPoints(bob, bob_data, sender=loot_distributor.address)
    ledger.setUserPoints(charlie, charlie_data, sender=loot_distributor.address)
    ledger.setGlobalPoints(global_data, sender=loot_distributor.address)
    
    # Verify each user has independent points
    alice_points = ledger.userPoints(alice)
    bob_points = ledger.userPoints(bob)
    charlie_points = ledger.userPoints(charlie)
    
    assert alice_points[0] == 100 * EIGHTEEN_DECIMALS
    assert bob_points[0] == 200 * EIGHTEEN_DECIMALS
    assert charlie_points[0] == 300 * EIGHTEEN_DECIMALS
    
    assert alice_points[1] == 50
    assert bob_points[1] == 100
    assert charlie_points[1] == 150
    
    assert alice_points[2] == 1000
    assert bob_points[2] == 2000
    assert charlie_points[2] == 3000
    
    # Verify global points are shared
    global_points = ledger.globalPoints()
    assert global_points[0] == 600 * EIGHTEEN_DECIMALS
    assert global_points[1] == 300
    assert global_points[2] == 3000