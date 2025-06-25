import pytest
import boa

from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS
from conf_utils import filter_logs


def test_hatchery_create_user_wallet(setUserWalletConfig, hatchery, bob, agent, alice, sally, alpha_token, alpha_token_whale, ledger):
    setUserWalletConfig()
    alpha_token.transfer(hatchery, 10 * EIGHTEEN_DECIMALS, sender=alpha_token_whale)

    wallet_addr = hatchery.createUserWallet(bob, alice, True, sender=sally)
    assert wallet_addr != ZERO_ADDRESS
    
    log = filter_logs(hatchery, "UserWalletCreated")[0]
    assert log.mainAddr == wallet_addr
    assert log.configAddr != ZERO_ADDRESS
    assert log.owner == bob
    assert log.agent == agent
    assert log.ambassador == ZERO_ADDRESS # alice not a underscore wallet
    assert log.creator == sally
    assert log.trialFundsAsset == alpha_token.address
    assert log.trialFundsAmount == 10 * EIGHTEEN_DECIMALS
    
    # ledger data
    assert ledger.isUserWallet(wallet_addr)

    assert ledger.indexOfUserWallet(wallet_addr) == 1
    assert ledger.userWallets(1) == wallet_addr
    assert ledger.numUserWallets() == 2  # First wallet gets index 1, so numUserWallets is 2

    data = ledger.userWalletData(wallet_addr)
    assert data.ambassador == ZERO_ADDRESS
    assert data.depositPoints == 0


def test_hatchery_create_user_wallet_no_trial_funds(setUserWalletConfig, hatchery, bob, agent, sally, alpha_token):
    setUserWalletConfig()
    
    # Create wallet without trial funds
    wallet_addr = hatchery.createUserWallet(bob, ZERO_ADDRESS, False, sender=sally)
    assert wallet_addr != ZERO_ADDRESS
    
    log = filter_logs(hatchery, "UserWalletCreated")[0]
    assert log.mainAddr == wallet_addr
    assert log.owner == bob
    assert log.agent == agent
    assert log.ambassador == ZERO_ADDRESS
    assert log.creator == sally
    assert log.trialFundsAsset == ZERO_ADDRESS  # No trial funds
    assert log.trialFundsAmount == 0
    
    # Verify no tokens were transferred
    assert alpha_token.balanceOf(wallet_addr) == 0


def test_hatchery_create_user_wallet_with_ambassador(setUserWalletConfig, hatchery, bob, alice, sally, alpha_token, alpha_token_whale, ledger):
    setUserWalletConfig()
    alpha_token.transfer(hatchery, 20 * EIGHTEEN_DECIMALS, sender=alpha_token_whale)
    
    # First create alice's wallet so she can be an ambassador
    alice_wallet = hatchery.createUserWallet(alice, ZERO_ADDRESS, True, sender=sally)
    assert ledger.isUserWallet(alice_wallet)
    
    # Create bob's wallet with alice as ambassador
    wallet_addr = hatchery.createUserWallet(bob, alice_wallet, True, sender=sally)
    
    # Get all logs and find the one for bob's wallet
    logs = filter_logs(hatchery, "UserWalletCreated")
    bob_log = None
    for log in logs:
        if log.owner == bob:
            bob_log = log
            break
    
    assert bob_log is not None
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


def test_hatchery_create_user_wallet_max_wallets_reached(setUserWalletConfig, hatchery, bob, alice, sally, alpha_token, alpha_token_whale):
    # Set max wallets to 1 (no wallets exist yet)
    setUserWalletConfig(_numUserWalletsAllowed=1)
    alpha_token.transfer(hatchery, 10 * EIGHTEEN_DECIMALS, sender=alpha_token_whale)
    
    # Create one wallet (should succeed)
    hatchery.createUserWallet(alice, ZERO_ADDRESS, True, sender=sally)
    
    # Try to create another (should fail)
    with boa.reverts("max user wallets reached"):
        hatchery.createUserWallet(bob, ZERO_ADDRESS, True, sender=sally)


def test_hatchery_create_user_wallet_insufficient_trial_funds(setUserWalletConfig, hatchery, bob, sally, alpha_token):
    setUserWalletConfig()
    # Don't transfer any tokens to hatchery
    
    wallet_addr = hatchery.createUserWallet(bob, ZERO_ADDRESS, True, sender=sally)
    
    log = filter_logs(hatchery, "UserWalletCreated")[0]
    assert log.trialFundsAsset == ZERO_ADDRESS  # No trial funds due to insufficient balance
    assert log.trialFundsAmount == 0
    
    assert alpha_token.balanceOf(wallet_addr) == 0


def test_hatchery_create_agent(mission_control, switchboard_alpha, hatchery, bob, sally, agent_template, ledger):
    # Set up agent config
    config = (
        agent_template,  # agentTemplate
        100,            # numAgentsAllowed
        False,          # enforceCreatorWhitelist
    )
    mission_control.setAgentConfig(config, sender=switchboard_alpha.address)
    mission_control.setTimeLockBoundaries(10, 100, sender=switchboard_alpha.address)
    
    # Create agent
    agent_addr = hatchery.createAgent(bob, sender=sally)
    assert agent_addr != ZERO_ADDRESS
    
    log = filter_logs(hatchery, "AgentCreated")[0]
    assert log.agent == agent_addr
    assert log.owner == bob
    assert log.creator == sally
    
    # Verify ledger was updated
    assert ledger.isAgent(agent_addr)
    assert ledger.numAgents() == 2  # First agent gets index 1, so numAgents is 2


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


def test_hatchery_create_agent_max_agents_reached(mission_control, switchboard_alpha, hatchery, bob, alice, sally, agent_template):
    # Set max agents to 1 (no agents exist yet)
    config = (
        agent_template,
        1,  # numAgentsAllowed
        False,
    )
    mission_control.setAgentConfig(config, sender=switchboard_alpha.address)
    mission_control.setTimeLockBoundaries(10, 100, sender=switchboard_alpha.address)
    
    # Create one agent (should succeed)
    hatchery.createAgent(alice, sender=sally)
    
    # Try to create another (should fail)
    with boa.reverts("max agents reached"):
        hatchery.createAgent(bob, sender=sally)


def test_hatchery_paused(setUserWalletConfig, hatchery, bob, sally, mission_control, switchboard_alpha, agent_template):
    setUserWalletConfig()
    
    # Set up agent config
    config = (agent_template, 100, False)
    mission_control.setAgentConfig(config, sender=switchboard_alpha.address)
    mission_control.setTimeLockBoundaries(10, 100, sender=switchboard_alpha.address)
    
    # Pause the contract
    hatchery.pause(True, sender=switchboard_alpha.address)
    
    # Try to create user wallet
    with boa.reverts("contract paused"):
        hatchery.createUserWallet(bob, ZERO_ADDRESS, True, sender=sally)
    
    # Try to create agent
    with boa.reverts("contract paused"):
        hatchery.createAgent(bob, sender=sally)


def test_hatchery_create_user_wallet_default_params(setUserWalletConfig, hatchery, sally, alpha_token, alpha_token_whale):
    setUserWalletConfig()
    alpha_token.transfer(hatchery, 10 * EIGHTEEN_DECIMALS, sender=alpha_token_whale)
    
    # Create wallet using default params (msg.sender as owner)
    wallet_addr = hatchery.createUserWallet(sender=sally)
    
    log = filter_logs(hatchery, "UserWalletCreated")[0]
    assert log.owner == sally  # Default owner is msg.sender
    assert log.creator == sally


def test_hatchery_create_agent_default_params(mission_control, switchboard_alpha, hatchery, sally, agent_template):
    # Set up agent config
    config = (agent_template, 100, False)
    mission_control.setAgentConfig(config, sender=switchboard_alpha.address)
    mission_control.setTimeLockBoundaries(10, 100, sender=switchboard_alpha.address)
    
    # Create agent using default params (msg.sender as owner)
    agent_addr = hatchery.createAgent(sender=sally)
    
    log = filter_logs(hatchery, "AgentCreated")[0]
    assert log.owner == sally  # Default owner is msg.sender
    assert log.creator == sally