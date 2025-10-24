import pytest
import boa
from constants import ZERO_ADDRESS


########################
# Access Control Tests #
########################


def test_create_user_wallet_access(ledger, bob, alice):
    """Only hatchery should be able to create user wallets"""
    # Non-hatchery address should fail
    with boa.reverts("only hatchery allowed"):
        ledger.createUserWallet(alice, ZERO_ADDRESS, sender=bob)


def test_set_user_points_access(ledger, bob, alice):
    """Only loot distributor should be able to set user points"""
    points_data = (1000, 100, 12345)  # usdValue, depositPoints, lastUpdate
    
    # Non-loot distributor address should fail
    with boa.reverts("only loot distributor allowed"):
        ledger.setUserPoints(alice, points_data, sender=bob)


def test_set_global_points_access(ledger, bob):
    """Only loot distributor should be able to set global points"""
    points_data = (1000000, 100000, 12345)  # usdValue, depositPoints, lastUpdate
    
    # Non-loot distributor address should fail
    with boa.reverts("only loot distributor allowed"):
        ledger.setGlobalPoints(points_data, sender=bob)


def test_set_user_and_global_points_access(ledger, bob, alice):
    """Only loot distributor should be able to set user and global points"""
    user_points_data = (1000, 100, 12345)
    global_points_data = (1000000, 100000, 12345)
    
    # Non-loot distributor address should fail
    with boa.reverts("only loot distributor allowed"):
        ledger.setUserAndGlobalPoints(alice, user_points_data, global_points_data, sender=bob)


def test_set_vault_token_access(ledger, bob, alice):
    """Only lego book addresses should be able to set vault tokens"""
    # Non-lego book address should fail
    with boa.reverts("no perms"):
        ledger.setVaultToken(
            alice,      # vault token
            1,          # lego id
            alice,      # underlying asset
            18,         # decimals
            False,      # is rebasing
            sender=bob
        )


def test_register_backpack_item_access(ledger, bob, alice):
    """Only wallet backpack should be able to register backpack items"""
    # Non-wallet backpack address should fail
    with boa.reverts("no perms"):
        ledger.registerBackpackItem(alice, sender=bob)


def test_create_agent_access(ledger, bob, alice):
    """Only hatchery should be able to create agents"""
    # Non-hatchery address should fail
    with boa.reverts("only hatchery allowed"):
        ledger.createAgent(alice, sender=bob)


def test_paused_state_blocks_changes(ledger, hatchery, loot_distributor, wallet_backpack, lego_aave_v3, switchboard_alpha, alice, bob):
    """All setter functions should fail when protocol is paused"""
    # Pause the protocol
    ledger.pause(True, sender=switchboard_alpha.address)
    
    # All these should fail when paused
    with boa.reverts("not activated"):
        ledger.createUserWallet(alice, ZERO_ADDRESS, sender=hatchery.address)
    
    with boa.reverts("not activated"):
        ledger.setUserPoints(alice, (1000, 100, 12345), sender=loot_distributor.address)
    
    with boa.reverts("not activated"):
        ledger.setGlobalPoints((1000000, 100000, 12345), sender=loot_distributor.address)
    
    with boa.reverts("not activated"):
        ledger.setUserAndGlobalPoints(
            alice, 
            (1000, 100, 12345), 
            (1000000, 100000, 12345), 
            sender=loot_distributor.address
        )
    
    with boa.reverts("not activated"):
        ledger.setVaultToken(alice, 1, alice, 18, False, sender=lego_aave_v3.address)
    
    with boa.reverts("not activated"):
        ledger.registerBackpackItem(alice, sender=wallet_backpack.address)
    
    with boa.reverts("not activated"):
        ledger.createAgent(alice, sender=hatchery.address)


###########################
# State Persistence Tests #
###########################


def test_create_user_wallet_persistence(ledger, hatchery, alice, bob, charlie):
    """User wallet creation should persist data correctly"""
    # Get initial state (might not be 0 if other tests ran first)
    initial_count = ledger.getNumUserWallets()
    assert not ledger.isUserWallet(alice)
    
    # Create first user wallet without ambassador
    ledger.createUserWallet(alice, ZERO_ADDRESS, sender=hatchery.address)
    
    # Verify persistence
    assert ledger.getNumUserWallets() == initial_count + 1
    assert ledger.isUserWallet(alice)
    # Check the actual index, not assuming it's 1
    alice_index = ledger.indexOfUserWallet(alice)
    assert alice_index > 0
    assert ledger.userWallets(alice_index) == alice
    assert ledger.ambassadors(alice) == ZERO_ADDRESS
    
    # Create second user wallet with ambassador
    ledger.createUserWallet(bob, charlie, sender=hatchery.address)
    
    # Verify persistence
    assert ledger.getNumUserWallets() == initial_count + 2
    assert ledger.isUserWallet(bob)
    bob_index = ledger.indexOfUserWallet(bob)
    assert bob_index > 0
    assert ledger.userWallets(bob_index) == bob
    assert ledger.ambassadors(bob) == charlie


def test_points_persistence(ledger, loot_distributor, alice):
    """Points data should persist correctly"""
    # Initial state
    user_points = ledger.userPoints(alice)
    assert user_points.usdValue == 0
    assert user_points.depositPoints == 0
    assert user_points.lastUpdate == 0
    
    global_points = ledger.globalPoints()
    assert global_points.usdValue == 0
    assert global_points.depositPoints == 0
    assert global_points.lastUpdate == 0
    
    # Set user points
    user_data = (1000, 100, 12345)
    ledger.setUserPoints(alice, user_data, sender=loot_distributor.address)
    
    # Verify persistence
    user_points = ledger.userPoints(alice)
    assert user_points.usdValue == 1000
    assert user_points.depositPoints == 100
    assert user_points.lastUpdate == 12345
    assert ledger.getLastTotalUsdValue(alice) == 1000
    
    # Set global points
    global_data = (1000000, 100000, 54321)
    ledger.setGlobalPoints(global_data, sender=loot_distributor.address)
    
    # Verify persistence
    global_points = ledger.globalPoints()
    assert global_points.usdValue == 1000000
    assert global_points.depositPoints == 100000
    assert global_points.lastUpdate == 54321
    
    # Set both user and global points
    new_user_data = (2000, 200, 67890)
    new_global_data = (2000000, 200000, 67890)
    ledger.setUserAndGlobalPoints(alice, new_user_data, new_global_data, sender=loot_distributor.address)
    
    # Verify persistence
    user_points, global_points = ledger.getUserAndGlobalPoints(alice)
    assert user_points.usdValue == 2000
    assert user_points.depositPoints == 200
    assert user_points.lastUpdate == 67890
    assert global_points.usdValue == 2000000
    assert global_points.depositPoints == 200000
    assert global_points.lastUpdate == 67890


def test_vault_token_persistence(ledger, lego_aave_v3, alice, bob):
    """Vault token data should persist correctly"""
    vault_token = alice
    underlying_asset = bob
    
    # Initial state
    assert not ledger.isRegisteredVaultToken(vault_token)
    vault_data = ledger.vaultTokens(vault_token)
    assert vault_data.legoId == 0
    assert vault_data.underlyingAsset == ZERO_ADDRESS
    assert vault_data.decimals == 0
    assert vault_data.isRebasing == False
    
    # Set vault token
    ledger.setVaultToken(
        vault_token,
        1,                  # lego id
        underlying_asset,   # underlying asset
        18,                 # decimals
        True,               # is rebasing
        sender=lego_aave_v3.address
    )
    
    # Verify persistence
    assert ledger.isRegisteredVaultToken(vault_token)
    vault_data = ledger.vaultTokens(vault_token)
    assert vault_data.legoId == 1  # lego_ripe
    assert vault_data.underlyingAsset == underlying_asset
    assert vault_data.decimals == 18
    assert vault_data.isRebasing == True
    
    # Update vault token with different values
    ledger.setVaultToken(
        vault_token,
        2,                  # lego id
        alice,              # different underlying asset
        6,                  # decimals
        False,              # is rebasing
        sender=lego_aave_v3.address
    )
    
    # Verify update
    vault_data = ledger.vaultTokens(vault_token)
    assert vault_data.legoId == 2
    assert vault_data.underlyingAsset == alice
    assert vault_data.decimals == 6
    assert vault_data.isRebasing == False


def test_backpack_item_persistence(ledger, wallet_backpack, alice, bob):
    """Backpack item registration should persist correctly"""
    # Initial state
    assert not ledger.isRegisteredBackpackItem(alice)
    assert not ledger.isRegisteredBackpackItem(bob)
    
    # Register first item
    ledger.registerBackpackItem(alice, sender=wallet_backpack.address)
    
    # Verify persistence
    assert ledger.isRegisteredBackpackItem(alice)
    assert not ledger.isRegisteredBackpackItem(bob)
    
    # Register second item
    ledger.registerBackpackItem(bob, sender=wallet_backpack.address)
    
    # Verify persistence
    assert ledger.isRegisteredBackpackItem(alice)
    assert ledger.isRegisteredBackpackItem(bob)


def test_create_agent_persistence(ledger, hatchery, alice, bob, charlie):
    """Agent creation should persist data correctly"""
    # Get initial state (might not be 0 if other tests ran first)
    initial_count = ledger.getNumAgents()
    assert not ledger.isAgent(alice)
    
    # Create first agent
    ledger.createAgent(alice, sender=hatchery.address)
    
    # Verify persistence
    assert ledger.getNumAgents() == initial_count + 1
    assert ledger.isAgent(alice)
    alice_index = ledger.indexOfAgent(alice)
    assert alice_index > 0
    assert ledger.agents(alice_index) == alice
    
    # Create second agent
    ledger.createAgent(bob, sender=hatchery.address)
    
    # Verify persistence
    assert ledger.getNumAgents() == initial_count + 2
    assert ledger.isAgent(bob)
    bob_index = ledger.indexOfAgent(bob)
    assert bob_index > 0
    assert ledger.agents(bob_index) == bob
    
    # Create third agent
    ledger.createAgent(charlie, sender=hatchery.address)
    
    # Verify persistence
    assert ledger.getNumAgents() == initial_count + 3
    assert ledger.isAgent(charlie)
    charlie_index = ledger.indexOfAgent(charlie)
    assert charlie_index > 0
    assert ledger.agents(charlie_index) == charlie
    
    # Verify all agents still exist
    assert ledger.isAgent(alice)
    assert ledger.isAgent(bob)
    assert ledger.isAgent(charlie)


############################
# View Functions Tests     #
############################


def test_num_tracking_consistency(ledger, hatchery, alice, bob, charlie):
    """Test that number tracking for wallets and agents is consistent"""
    # Get initial state (may not be 1 if other tests ran first)
    initial_num_wallets = ledger.numUserWallets()
    initial_num_agents = ledger.numAgents()
    initial_get_num_wallets = ledger.getNumUserWallets()
    initial_get_num_agents = ledger.getNumAgents()
    
    # Verify the relationship between num and getNum (num = getNum + 1)
    assert initial_num_wallets == initial_get_num_wallets + 1
    assert initial_num_agents == initial_get_num_agents + 1
    
    # Add wallets
    ledger.createUserWallet(alice, ZERO_ADDRESS, sender=hatchery.address)
    assert ledger.numUserWallets() == initial_num_wallets + 1
    assert ledger.getNumUserWallets() == initial_get_num_wallets + 1
    
    ledger.createUserWallet(bob, ZERO_ADDRESS, sender=hatchery.address)
    assert ledger.numUserWallets() == initial_num_wallets + 2
    assert ledger.getNumUserWallets() == initial_get_num_wallets + 2
    
    # Add agents
    ledger.createAgent(alice, sender=hatchery.address)
    assert ledger.numAgents() == initial_num_agents + 1
    assert ledger.getNumAgents() == initial_get_num_agents + 1
    
    ledger.createAgent(bob, sender=hatchery.address)
    assert ledger.numAgents() == initial_num_agents + 2
    assert ledger.getNumAgents() == initial_get_num_agents + 2


def test_ambassador_tracking(ledger, hatchery, alice, bob, charlie, sally):
    """Test ambassador relationships are tracked correctly"""
    # Create users with different ambassador setups
    ledger.createUserWallet(alice, ZERO_ADDRESS, sender=hatchery.address)
    ledger.createUserWallet(bob, alice, sender=hatchery.address)
    ledger.createUserWallet(charlie, alice, sender=hatchery.address)
    ledger.createUserWallet(sally, bob, sender=hatchery.address)
    
    # Verify ambassador relationships
    assert ledger.ambassadors(alice) == ZERO_ADDRESS
    assert ledger.ambassadors(bob) == alice
    assert ledger.ambassadors(charlie) == alice
    assert ledger.ambassadors(sally) == bob


def test_index_zero_special_case(ledger):
    """Test that index 0 is reserved for 'not exists' checks"""
    # Verify unregistered addresses return index 0
    assert ledger.indexOfUserWallet(ZERO_ADDRESS) == 0
    assert ledger.indexOfAgent(ZERO_ADDRESS) == 0
    
    # Verify index 0 is not used for actual data
    assert ledger.userWallets(0) == ZERO_ADDRESS
    assert ledger.agents(0) == ZERO_ADDRESS