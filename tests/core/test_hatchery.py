import pytest
import boa

from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS
from conf_utils import filter_logs


def test_hatchery_create_user_wallet(setUserWalletConfig, setManagerConfig, hatchery, bob, agent_eoa, alice, sally, alpha_token, alpha_token_whale, ledger):
    setUserWalletConfig()
    setManagerConfig()  # Set up manager config with default agent
    
    # Ensure hatchery has enough trial funds
    hatchery_balance = alpha_token.balanceOf(hatchery)
    if hatchery_balance < 10 * EIGHTEEN_DECIMALS:
        alpha_token.transfer(hatchery, 10 * EIGHTEEN_DECIMALS - hatchery_balance, sender=alpha_token_whale)

    # Get initial count
    initial_wallet_count = ledger.numUserWallets()

    wallet_addr = hatchery.createUserWallet(bob, alice, True, sender=sally)
    assert wallet_addr != ZERO_ADDRESS
    
    # Find the log for this specific wallet creation
    log = filter_logs(hatchery, "UserWalletCreated")[0]
    assert log.mainAddr == wallet_addr
    assert log.configAddr != ZERO_ADDRESS
    assert log.owner == bob
    assert log.agent == agent_eoa  # This is the starting agent from manager config
    assert log.ambassador == ZERO_ADDRESS # alice not a underscore wallet
    assert log.creator == sally
    assert log.trialFundsAsset == alpha_token.address
    assert log.trialFundsAmount == 10 * EIGHTEEN_DECIMALS
    
    # ledger data
    assert ledger.isUserWallet(wallet_addr)

    # Check that wallet was added (don't assume absolute index)
    wallet_index = ledger.indexOfUserWallet(wallet_addr)
    assert wallet_index > 0  # Valid index
    assert ledger.userWallets(wallet_index) == wallet_addr
    # Verify count increased
    assert ledger.numUserWallets() > initial_wallet_count

    data = ledger.userWalletData(wallet_addr)
    assert data.ambassador == ZERO_ADDRESS
    assert data.depositPoints == 0


def test_hatchery_create_user_wallet_no_trial_funds(setUserWalletConfig, setManagerConfig, hatchery, bob, agent_eoa, sally, alpha_token):
    setUserWalletConfig()
    setManagerConfig()
    
    # Create wallet without trial funds
    wallet_addr = hatchery.createUserWallet(bob, ZERO_ADDRESS, False, sender=sally)
    assert wallet_addr != ZERO_ADDRESS
    
    log = filter_logs(hatchery, "UserWalletCreated")[0]
    assert log.mainAddr == wallet_addr
    assert log.owner == bob
    assert log.agent == agent_eoa
    assert log.ambassador == ZERO_ADDRESS
    assert log.creator == sally
    assert log.trialFundsAsset == ZERO_ADDRESS  # No trial funds
    assert log.trialFundsAmount == 0
    
    # Verify no tokens were transferred
    assert alpha_token.balanceOf(wallet_addr) == 0


def test_hatchery_create_user_wallet_with_ambassador(setUserWalletConfig, setManagerConfig, hatchery, bob, alice, sally, alpha_token, alpha_token_whale, ledger):
    setUserWalletConfig()
    setManagerConfig()
    
    # Ensure hatchery has enough trial funds (need 20 for 2 wallets)
    hatchery_balance = alpha_token.balanceOf(hatchery)
    if hatchery_balance < 20 * EIGHTEEN_DECIMALS:
        alpha_token.transfer(hatchery, 20 * EIGHTEEN_DECIMALS - hatchery_balance, sender=alpha_token_whale)
    
    # First create alice's wallet so she can be an ambassador
    alice_wallet = hatchery.createUserWallet(alice, ZERO_ADDRESS, True, sender=sally)
    assert ledger.isUserWallet(alice_wallet)
    
    # Create bob's wallet with alice as ambassador
    wallet_addr = hatchery.createUserWallet(bob, alice_wallet, True, sender=sally)
    
    # Get the log for bob's wallet creation - it will be the first log after this transaction
    bob_log = filter_logs(hatchery, "UserWalletCreated")[0]
    assert bob_log.owner == bob
    assert bob_log.mainAddr == wallet_addr
    assert bob_log.ambassador == alice_wallet  # alice's wallet is the ambassador
    
    data = ledger.userWalletData(wallet_addr)
    assert data.ambassador == alice_wallet


def test_hatchery_create_user_wallet_creator_not_allowed(setUserWalletConfig, hatchery, bob, alice):
    # Set up config with enforced whitelist but don't add alice
    setUserWalletConfig(_enforceCreatorWhitelist=True)
    # Note: alice is not added to whitelist, so she should not be allowed
    
    with boa.reverts("creator not allowed"):
        hatchery.createUserWallet(bob, ZERO_ADDRESS, True, sender=alice)


def test_hatchery_create_user_wallet_invalid_setup(setUserWalletConfig, hatchery, bob, sally):
    # Set up config with invalid wallet template
    setUserWalletConfig(_walletTemplate=ZERO_ADDRESS)
    
    with boa.reverts("invalid setup"):
        hatchery.createUserWallet(bob, ZERO_ADDRESS, True, sender=sally)


def test_hatchery_create_user_wallet_max_wallets_reached(setUserWalletConfig, setManagerConfig, hatchery, bob, alice, sally, alpha_token, alpha_token_whale, ledger):
    # Get current wallet count
    current_wallet_count = ledger.numUserWallets()
    
    # Set max wallets to current + 1 (so we can create exactly one more)
    setUserWalletConfig(_numUserWalletsAllowed=current_wallet_count + 1)
    setManagerConfig()
    
    # Ensure hatchery has enough trial funds
    hatchery_balance = alpha_token.balanceOf(hatchery)
    if hatchery_balance < 10 * EIGHTEEN_DECIMALS:
        alpha_token.transfer(hatchery, 10 * EIGHTEEN_DECIMALS - hatchery_balance, sender=alpha_token_whale)
    
    # Create one wallet (should succeed)
    hatchery.createUserWallet(alice, ZERO_ADDRESS, True, sender=sally)
    
    # Try to create another (should fail)
    with boa.reverts("max user wallets reached"):
        hatchery.createUserWallet(bob, ZERO_ADDRESS, True, sender=sally)


def test_hatchery_create_user_wallet_insufficient_trial_funds(setUserWalletConfig, setManagerConfig, hatchery, bob, sally, alpha_token):
    setUserWalletConfig()
    setManagerConfig()
    # Don't transfer any tokens to hatchery
    
    wallet_addr = hatchery.createUserWallet(bob, ZERO_ADDRESS, True, sender=sally)
    
    log = filter_logs(hatchery, "UserWalletCreated")[0]
    assert log.trialFundsAsset == ZERO_ADDRESS  # No trial funds due to insufficient balance
    assert log.trialFundsAmount == 0
    
    assert alpha_token.balanceOf(wallet_addr) == 0


def test_hatchery_create_agent(setUserWalletConfig, setAgentConfig, hatchery, bob, sally, ledger):
    # Get initial count
    initial_agent_count = ledger.numAgents()
    
    # Set up wallet config first (needed for agent timelocks)
    setUserWalletConfig()
    # Set up agent config using the fixture
    setAgentConfig()
    
    # Create agent
    agent_addr = hatchery.createAgent(bob, sender=sally)
    assert agent_addr != ZERO_ADDRESS
    
    # Find the log for this specific agent creation
    log = filter_logs(hatchery, "AgentCreated")[0]
    assert log.agent == agent_addr
    assert log.owner == bob
    assert log.creator == sally
    
    # Verify ledger was updated
    assert ledger.isAgent(agent_addr)
    # Verify count increased
    assert ledger.numAgents() > initial_agent_count


def test_hatchery_create_agent_creator_not_allowed(mission_control, switchboard_alpha, hatchery, bob, alice, agent_template):
    # Set up config with enforced whitelist but don't add alice
    config = (
        agent_template,
        100,
        True,  # enforceCreatorWhitelist
    )
    mission_control.setAgentConfig(config, sender=switchboard_alpha.address)
    
    with boa.reverts("creator not allowed"):
        hatchery.createAgent(bob, sender=alice)


def test_hatchery_create_agent_invalid_setup(mission_control, switchboard_alpha, hatchery, bob, sally):
    # Set up config with invalid agent template
    config = (
        ZERO_ADDRESS,  # Invalid template
        100,
        False,
    )
    mission_control.setAgentConfig(config, sender=switchboard_alpha.address)
    
    with boa.reverts("invalid setup"):
        hatchery.createAgent(bob, sender=sally)


def test_hatchery_create_agent_max_agents_reached(setUserWalletConfig, setAgentConfig, hatchery, bob, alice, sally, ledger):
    # Get current agent count
    current_agent_count = ledger.numAgents()
    
    # Set up wallet config first (needed for agent timelocks)
    setUserWalletConfig()
    # Set max agents to current + 1
    setAgentConfig(_numAgentsAllowed=current_agent_count + 1)
    
    # Create one agent (should succeed)
    hatchery.createAgent(alice, sender=sally)
    
    # Try to create another (should fail)
    with boa.reverts("max agents reached"):
        hatchery.createAgent(bob, sender=sally)


def test_hatchery_paused(setUserWalletConfig, setManagerConfig, setAgentConfig, hatchery, bob, sally, switchboard_alpha):
    setUserWalletConfig()
    setManagerConfig()
    setAgentConfig()
    
    # Pause the contract
    hatchery.pause(True, sender=switchboard_alpha.address)
    
    # Try to create user wallet
    with boa.reverts("contract paused"):
        hatchery.createUserWallet(bob, ZERO_ADDRESS, True, sender=sally)
    
    # Try to create agent
    with boa.reverts("contract paused"):
        hatchery.createAgent(bob, sender=sally)
    
    # Unpause for other tests
    hatchery.pause(False, sender=switchboard_alpha.address)


def test_hatchery_create_user_wallet_default_params(setUserWalletConfig, setManagerConfig, hatchery, sally, alpha_token, alpha_token_whale):
    setUserWalletConfig()
    setManagerConfig()  # Set up manager config with default agent
    
    # Ensure hatchery has enough trial funds
    hatchery_balance = alpha_token.balanceOf(hatchery)
    if hatchery_balance < 10 * EIGHTEEN_DECIMALS:
        alpha_token.transfer(hatchery, 10 * EIGHTEEN_DECIMALS - hatchery_balance, sender=alpha_token_whale)
    
    # Create wallet using default params (msg.sender as owner)
    wallet_addr = hatchery.createUserWallet(sender=sally)
    
    # Find the log for this specific wallet creation
    log = filter_logs(hatchery, "UserWalletCreated")[0]
    assert log.mainAddr == wallet_addr
    assert log.owner == sally  # Default owner is msg.sender
    assert log.creator == sally


def test_hatchery_create_agent_default_params(setUserWalletConfig, setAgentConfig, hatchery, sally):
    # Set up wallet config first (needed for agent timelocks)
    setUserWalletConfig()
    # Set up agent config using the fixture
    setAgentConfig()
    
    # Create agent using default params (msg.sender as owner)
    agent_addr = hatchery.createAgent(sender=sally)
    
    # Find the log for this specific agent creation
    log = filter_logs(hatchery, "AgentCreated")[0]
    assert log.agent == agent_addr
    assert log.owner == sally  # Default owner is msg.sender
    assert log.creator == sally