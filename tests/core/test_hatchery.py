import pytest
import boa

from contracts.core.userWallet import UserWallet, UserWalletConfig
from contracts.core.agent import AgentWrapper
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS
from conf_utils import filter_logs


######################
# Create User Wallet #
######################


def test_create_user_wallet_basic(hatchery, alice):
    """Test basic wallet creation"""

    # Create wallet
    wallet_address = hatchery.createUserWallet(sender=alice)

    # Verify wallet was created
    wallet = UserWallet.at(wallet_address)
    assert wallet != ZERO_ADDRESS

    # Verify wallet config
    wallet_config = UserWalletConfig.at(wallet.walletConfig())
    assert wallet_config.owner() == alice


def test_create_user_wallet_with_ambassador(hatchery, alice, bob, ledger):
    """Test that ambassador is properly set when provided"""

    # First create an ambassador wallet
    ambassador_wallet_addr = hatchery.createUserWallet(sender=alice)
    
    # Create a user wallet with ambassador
    user_wallet_addr = hatchery.createUserWallet(
        bob,
        ambassador_wallet_addr,
        sender=bob
    )
    
    # Verify ambassador relationship in ledger
    assert ledger.ambassadors(user_wallet_addr) == ambassador_wallet_addr
    
    # Verify ambassador is a valid user wallet
    assert ledger.isUserWallet(ambassador_wallet_addr) == True


def test_create_user_wallet_ledger_registration(hatchery, alice, ledger):
    """Test that user wallet gets registered with Ledger after creation"""

    initial_count = ledger.numUserWallets()

    # Create wallet
    wallet_address = hatchery.createUserWallet(sender=alice)
    
    # Verify wallet is registered in ledger
    assert ledger.isUserWallet(wallet_address) == True
    assert ledger.userWallets(initial_count) == wallet_address
    assert ledger.indexOfUserWallet(wallet_address) == initial_count

    # Verify wallet count increased
    assert ledger.numUserWallets() == initial_count + 1


def test_user_wallet_config_data(hatchery, alice, setUserWalletConfig):
    """Test that data stored in user wallet and config reflect expected values"""

    # Setup specific configuration
    setUserWalletConfig(
        _minTimeLock=10,
        _maxTimeLock=100,
    )
    
    # Create wallet with specific group ID
    group_id = 42
    wallet_address = hatchery.createUserWallet(
        alice,
        ZERO_ADDRESS,
        group_id,
        sender=alice
    )
    
    # Get wallet and config
    wallet = UserWallet.at(wallet_address)
    wallet_config = UserWalletConfig.at(wallet.walletConfig())
    
    # Verify config data
    assert wallet_config.wallet() == wallet_address
    assert wallet_config.groupId() == group_id
    assert wallet_config.owner() == alice

    assert wallet_config.MIN_TIMELOCK() == 10
    assert wallet_config.MAX_TIMELOCK() == 100


def test_create_user_wallet_permissions(hatchery, alice, bob, charlie, setUserWalletConfig, mission_control, switchboard_alpha):
    """Test permissions around who can create wallets"""

    # By default, anyone can create wallets
    wallet1 = hatchery.createUserWallet(sender=alice)
    assert UserWalletConfig.at(UserWallet.at(wallet1).walletConfig()).owner() == alice
    
    # Create wallet for someone else
    wallet2 = hatchery.createUserWallet(bob, sender=alice)
    assert UserWalletConfig.at(UserWallet.at(wallet2).walletConfig()).owner() == bob
    
    # Restrict wallet creation by enabling whitelist
    setUserWalletConfig(
        _enforceCreatorWhitelist=True
    )
    # Add charlie to whitelist
    mission_control.setCreatorWhitelist(charlie, True, sender=switchboard_alpha.address)
    
    # Non-allowed creator should fail
    with boa.reverts("creator not allowed"):
        hatchery.createUserWallet(sender=bob)
    
    # Allowed creator should succeed
    wallet3 = hatchery.createUserWallet(sender=charlie)
    assert UserWalletConfig.at(UserWallet.at(wallet3).walletConfig()).owner() == charlie


def test_create_user_wallet_limits(hatchery, alice, setUserWalletConfig, ledger):
    """Test limits on how many wallets can be created"""
    # Get current number of wallets
    current_wallet_count = ledger.numUserWallets()
    
    # Set max wallets limit to current + 5 more
    max_wallets = current_wallet_count + 5
    setUserWalletConfig(
        _numUserWalletsAllowed=max_wallets
    )
    
    # Create wallets up to the limit (we can create 5 more)
    created_wallets = []
    for i in range(5):
        wallet = hatchery.createUserWallet(sender=alice)
        created_wallets.append(wallet)
    
    # Verify all wallets were created
    assert len(created_wallets) == 5
    assert ledger.numUserWallets() == max_wallets
    
    # Try to create one more - should fail
    with boa.reverts("max user wallets reached"):
        hatchery.createUserWallet(sender=alice)


def test_create_user_wallet_invalid_ambassador(hatchery, alice, bob, ledger):
    """Test that invalid ambassador addresses are rejected"""

    # Try to use a non-wallet address as ambassador
    user_wallet_addr = hatchery.createUserWallet(
        alice,
        bob,  # bob is an EOA, not a wallet
        sender=alice
    )

    # will fail gracefully
    assert ledger.ambassadors(user_wallet_addr) == ZERO_ADDRESS


def test_create_user_wallet_events(hatchery, alice, charlie, bob, ambassador_wallet, setAgentConfig):
    """Test that correct events are emitted during wallet creation"""

    # Setup agent config
    setAgentConfig(
        _startingAgent=charlie
    )

    # Create user wallet and capture events
    wallet_addr = hatchery.createUserWallet(
        alice,
        ambassador_wallet,
        5,
        sender=bob
    )

    # Check for UserWalletCreated event
    event = filter_logs(hatchery, "UserWalletCreated")[0]
    assert event.mainAddr == wallet_addr
    assert event.configAddr == UserWallet.at(wallet_addr).walletConfig()
    assert event.owner == alice
    assert event.agent == charlie
    assert event.ambassador == ambassador_wallet.address
    assert event.creator == bob
    assert event.groupId == 5
    

def test_create_user_wallet_paused(hatchery, alice, switchboard_alpha):
    """Test that wallet creation fails when contract is paused"""

    # Pause the contract
    hatchery.pause(True, sender=switchboard_alpha.address)
    
    # Try to create wallet - should fail
    with boa.reverts("contract paused"):
        hatchery.createUserWallet(sender=alice)
    
    # Unpause and verify it works again
    hatchery.pause(False, sender=switchboard_alpha.address)

    wallet = hatchery.createUserWallet(sender=alice)
    assert UserWalletConfig.at(UserWallet.at(wallet).walletConfig()).owner() == alice


def test_create_user_wallet_invalid_owner(hatchery, alice):
    """Test that wallet creation fails when owner is ZERO_ADDRESS"""
    
    # Try to create wallet with ZERO_ADDRESS as owner - should fail
    with boa.reverts("invalid setup"):
        hatchery.createUserWallet(
            ZERO_ADDRESS,  # Invalid owner
            ZERO_ADDRESS,
            1,
            sender=alice
        )


def test_create_user_wallet_starting_agent_same_as_owner(hatchery, alice, setAgentConfig):
    """Test that wallet creation fails when starting agent is the same as owner"""
    
    # Set starting agent to be alice
    setAgentConfig(
        _startingAgent=alice
    )
    
    # Try to create wallet where owner and starting agent are the same - should fail
    with boa.reverts("starting agent cannot be the owner"):
        hatchery.createUserWallet(
            alice,  # Owner is alice
            ZERO_ADDRESS,
            1,
            sender=alice  # Starting agent will be alice based on config
        )


################
# Create Agent #
################


def test_create_agent_basic(hatchery, alice, ledger):
    """Test basic agent creation with default parameters"""
    
    initial_count = ledger.numAgents()
    
    # Create agent with defaults (owner=msg.sender, groupId=1)
    agent_address = hatchery.createAgent(sender=alice)
    
    # Verify agent was created
    assert agent_address != ZERO_ADDRESS
    
    # Verify agent is registered in ledger
    assert ledger.isAgent(agent_address) == True
    assert ledger.agents(initial_count) == agent_address
    assert ledger.indexOfAgent(agent_address) == initial_count
    
    # Verify agent count increased
    assert ledger.numAgents() == initial_count + 1


def test_create_agent_custom_owner(hatchery, alice, bob, ledger):
    """Test agent creation with custom owner"""
    
    # Create agent for bob (different from sender)
    agent_address = hatchery.createAgent(bob, sender=alice)
    
    # Verify agent was created
    assert agent_address != ZERO_ADDRESS
    
    # Verify agent is registered in ledger
    assert ledger.isAgent(agent_address) == True
    
    # Verify owner is bob
    assert AgentWrapper.at(agent_address).owner() == bob


def test_create_agent_custom_group_id(hatchery, alice):
    """Test agent creation with custom group ID"""
    
    # Create agent with custom group ID
    group_id = 42
    agent_address = hatchery.createAgent(alice, group_id, sender=alice)
    
    # verify group id
    assert AgentWrapper.at(agent_address).groupId() == group_id


def test_create_agent_permissions(hatchery, alice, bob, charlie, setAgentConfig, mission_control, switchboard_alpha):
    """Test permissions around who can create agents"""
    
    # By default, anyone can create agents
    agent1 = hatchery.createAgent(sender=alice)
    assert agent1 != ZERO_ADDRESS
    
    # Create agent for someone else
    agent2 = hatchery.createAgent(bob, sender=alice)
    assert agent2 != ZERO_ADDRESS
    
    # Restrict agent creation by enabling whitelist
    setAgentConfig(
        _enforceCreatorWhitelist=True
    )
    
    # Add charlie to whitelist
    mission_control.setCreatorWhitelist(charlie, True, sender=switchboard_alpha.address)
    
    # Non-allowed creator should fail
    with boa.reverts("creator not allowed"):
        hatchery.createAgent(sender=bob)
    
    # Allowed creator should succeed
    agent3 = hatchery.createAgent(sender=charlie)
    assert agent3 != ZERO_ADDRESS


def test_create_agent_limits(hatchery, alice, setAgentConfig, ledger):
    """Test limits on how many agents can be created"""
    
    # Get current agent count
    initial_count = ledger.numAgents()
    
    # Set max agents limit (relative to current count)
    max_new_agents = 3
    max_total_agents = initial_count + max_new_agents
    
    setAgentConfig(
        _numAgentsAllowed=max_total_agents
    )
    
    # Create agents up to the limit
    created_agents = []
    for i in range(max_new_agents):
        agent = hatchery.createAgent(sender=alice)
        created_agents.append(agent)
    
    # Verify all agents were created
    assert len(created_agents) == max_new_agents
    assert ledger.numAgents() == max_total_agents
    
    # Try to create one more - should fail
    with boa.reverts("max agents reached"):
        hatchery.createAgent(sender=alice)


def test_create_agent_invalid_owner(hatchery, alice):
    """Test that agent creation fails when owner is ZERO_ADDRESS"""
    
    # Try to create agent with ZERO_ADDRESS as owner - should fail
    with boa.reverts("invalid setup"):
        hatchery.createAgent(
            ZERO_ADDRESS,  # Invalid owner
            sender=alice
        )


def test_create_agent_events(hatchery, alice, bob):
    """Test that correct events are emitted during agent creation"""
    
    # Create agent with specific parameters
    group_id = 7
    agent_addr = hatchery.createAgent(
        bob,
        group_id,
        sender=alice
    )
    
    # Check for AgentCreated event
    event = filter_logs(hatchery, "AgentCreated")[0]
    assert event.agent == agent_addr
    assert event.owner == bob
    assert event.creator == alice
    assert event.groupId == group_id


def test_create_agent_paused(hatchery, alice, switchboard_alpha):
    """Test that agent creation fails when contract is paused"""
    
    # Pause the contract
    hatchery.pause(True, sender=switchboard_alpha.address)
    
    # Try to create agent - should fail
    with boa.reverts("contract paused"):
        hatchery.createAgent(sender=alice)
    
    # Unpause and verify it works again
    hatchery.pause(False, sender=switchboard_alpha.address)
    
    agent = hatchery.createAgent(sender=alice)
    assert agent != ZERO_ADDRESS


def test_create_agent_multiple_creators(hatchery, alice, bob, charlie, ledger):
    """Test multiple agents created by different creators"""
    
    initial_count = ledger.numAgents()
    
    # Different creators create agents
    agent1 = hatchery.createAgent(sender=alice)
    agent2 = hatchery.createAgent(sender=bob)
    agent3 = hatchery.createAgent(sender=charlie)
    
    # Verify all agents were created and registered
    assert ledger.isAgent(agent1) == True
    assert ledger.isAgent(agent2) == True
    assert ledger.isAgent(agent3) == True
    
    # Verify count increased correctly
    assert ledger.numAgents() == initial_count + 3
    
    # Verify they have different addresses
    assert agent1 != agent2
    assert agent2 != agent3
    assert agent1 != agent3


def test_create_agent_time_lock_config(hatchery, alice, setUserWalletConfig):
    """Test agent creation with different time lock configurations"""
    
    # Set specific time lock values
    min_lock = 100
    max_lock = 1000
    
    setUserWalletConfig(
        _minTimeLock=min_lock,
        _maxTimeLock=max_lock
    )
    
    # Create agent
    agent_address = hatchery.createAgent(sender=alice)
    
    # Verify agent was created
    assert agent_address != ZERO_ADDRESS
    
    assert AgentWrapper.at(agent_address).MIN_OWNERSHIP_TIMELOCK() == min_lock
    assert AgentWrapper.at(agent_address).MAX_OWNERSHIP_TIMELOCK() == max_lock
