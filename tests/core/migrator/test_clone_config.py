"""
Test config cloning functionality in Migrator
"""
import pytest
import boa

from contracts.core import Migrator
from contracts.core.userWallet import UserWallet, UserWalletConfig
from constants import EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ONE_YEAR_IN_BLOCKS, ZERO_ADDRESS
from conf_utils import filter_logs


@pytest.fixture(scope="module")
def setup_wallets(setUserWalletConfig, setManagerConfig, setPayeeConfig, hatchery, bob, alice):
    """Setup user wallets for config cloning tests"""
    # Configure without starting agent for clean wallets
    setManagerConfig(_startingAgent=ZERO_ADDRESS)
    setUserWalletConfig()
    setPayeeConfig()
    
    # Create source wallet with configuration
    source_wallet_addr = hatchery.createUserWallet(
        bob,
        ZERO_ADDRESS,
        False,
        1,
        sender=bob
    )
    
    # Create destination wallets
    dest_wallet_addr = hatchery.createUserWallet(
        bob,
        ZERO_ADDRESS,
        False,
        1,
        sender=bob
    )
    
    # Create wallet with different group ID
    diff_group_wallet_addr = hatchery.createUserWallet(
        bob,
        ZERO_ADDRESS,
        False,
        2,  # Different group ID
        sender=bob
    )
    
    # Create wallet with different owner
    alice_wallet_addr = hatchery.createUserWallet(
        alice,
        ZERO_ADDRESS,
        False,
        1,
        sender=alice
    )
    
    # Now configure with starting agent for some test wallets
    setManagerConfig()  # Use default starting agent
    
    # Create wallet with starting agent
    wallet_with_agent_addr = hatchery.createUserWallet(
        bob,
        ZERO_ADDRESS,
        False,
        1,
        sender=bob
    )
    
    assert all(addr != ZERO_ADDRESS for addr in [
        source_wallet_addr, dest_wallet_addr, diff_group_wallet_addr, 
        alice_wallet_addr, wallet_with_agent_addr
    ])
    
    return {
        'source_wallet': UserWallet.at(source_wallet_addr),
        'dest_wallet': UserWallet.at(dest_wallet_addr),
        'diff_group_wallet': UserWallet.at(diff_group_wallet_addr),
        'alice_wallet': UserWallet.at(alice_wallet_addr),
        'wallet_with_agent': UserWallet.at(wallet_with_agent_addr)
    }


@pytest.fixture(scope="module")
def setup_contracts(setup_wallets, migrator, paymaster, boss_validator, alpha_token, 
                   bravo_token, governance, bob, alice, charlie, createPayeeLimits,
                   createManagerSettings, createTransferPerms):
    """Setup contracts and configurations"""
    wallets = setup_wallets
    
    # Get wallet configs
    source_config = UserWalletConfig.at(wallets['source_wallet'].walletConfig())
    dest_config = UserWalletConfig.at(wallets['dest_wallet'].walletConfig())
    
    # Fund source wallet
    alpha_token.transfer(wallets['source_wallet'].address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    bravo_token.transfer(wallets['source_wallet'].address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    return {
        'source_wallet': wallets['source_wallet'],
        'dest_wallet': wallets['dest_wallet'],
        'diff_group_wallet': wallets['diff_group_wallet'],
        'alice_wallet': wallets['alice_wallet'],
        'wallet_with_agent': wallets['wallet_with_agent'],
        'source_config': source_config,
        'dest_config': dest_config,
        'migrator': migrator,
        'paymaster': paymaster,
        'boss_validator': boss_validator,
        'alpha_token': alpha_token,
        'bravo_token': bravo_token,
        'bob': bob,
        'alice': alice,
        'charlie': charlie,
        'governance': governance,
        'createPayeeLimits': createPayeeLimits,
        'createManagerSettings': createManagerSettings,
        'createTransferPerms': createTransferPerms
    }


# Basic config cloning tests


def test_clone_config_with_payees(setup_contracts, hatchery):
    """Test cloning configuration with payees"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    paymaster = ctx['paymaster']
    bob = ctx['bob']
    alpha_token = ctx['alpha_token']
    createPayeeLimits = ctx['createPayeeLimits']
    
    # Create fresh wallets for this test (may have starting agents)
    source_wallet_addr = hatchery.createUserWallet(bob, ZERO_ADDRESS, False, 1, sender=bob)
    dest_wallet_addr = hatchery.createUserWallet(bob, ZERO_ADDRESS, False, 1, sender=bob)
    
    source_wallet = UserWallet.at(source_wallet_addr)
    dest_wallet = UserWallet.at(dest_wallet_addr)
    source_config = UserWalletConfig.at(source_wallet.walletConfig())
    dest_config = UserWalletConfig.at(dest_wallet.walletConfig())
    
    # Get initial payee count before adding new ones
    initial_source_payees = source_config.numPayees()
    initial_dest_payees = dest_config.numPayees()
    
    # Note: Fresh wallets might have payees from previous tests due to module-scope fixtures
    # We'll track how many we add
    
    payee1 = boa.env.generate_address()
    payee2 = boa.env.generate_address()
    
    # Add payees to source wallet
    unit_limits = createPayeeLimits(
        _perTxCap=100 * EIGHTEEN_DECIMALS,
        _perPeriodCap=1000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=10000 * EIGHTEEN_DECIMALS
    )
    usd_limits = createPayeeLimits(
        _perTxCap=100 * EIGHTEEN_DECIMALS,
        _perPeriodCap=1000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=10000 * EIGHTEEN_DECIMALS
    )
    
    # Add first payee
    paymaster.addPayee(
        source_wallet.address,
        payee1,
        False,  # canPull
        ONE_DAY_IN_BLOCKS,
        10,
        0,
        False,
        alpha_token.address,
        False,
        unit_limits,
        usd_limits,
        sender=bob
    )
    
    # Add second payee with different settings
    paymaster.addPayee(
        source_wallet.address,
        payee2,
        True,  # canPull = True
        ONE_DAY_IN_BLOCKS * 7,  # Week period
        5,
        100,  # cooldown
        True,  # failOnZeroPrice
        ctx['bravo_token'].address,
        True,  # onlyPrimaryAsset
        unit_limits,
        usd_limits,
        sender=bob
    )
    
    # Verify we added exactly 2 payees
    # Fresh wallets start with numPayees = 0, after adding 2 payees, numPayees = 3 (1-indexed)
    assert source_config.numPayees() == 3
    
    # Clone configuration
    migrator.cloneConfig(source_wallet.address, dest_wallet.address, sender=bob)
    
    # Check event
    events = filter_logs(migrator, "ConfigCloned")
    assert len(events) == 1
    event = events[0]
    assert event.fromWallet == source_wallet.address
    assert event.toWallet == dest_wallet.address
    assert event.numPayeesCopied == 2
    
    # Verify destination now has same number of payees as source  
    assert dest_config.numPayees() == source_config.numPayees()
    
    # Verify payee settings were copied correctly
    payee1_settings_src = source_config.payeeSettings(payee1)
    payee1_settings_dst = dest_config.payeeSettings(payee1)
    assert payee1_settings_src.canPull == payee1_settings_dst.canPull
    assert payee1_settings_src.periodLength == payee1_settings_dst.periodLength
    assert payee1_settings_src.primaryAsset == payee1_settings_dst.primaryAsset
    
    payee2_settings_src = source_config.payeeSettings(payee2)
    payee2_settings_dst = dest_config.payeeSettings(payee2)
    assert payee2_settings_dst.canPull == True
    assert payee2_settings_dst.periodLength == ONE_DAY_IN_BLOCKS * 7
    assert payee2_settings_dst.primaryAsset == ctx['bravo_token'].address
    
    # Verify migration flag
    bundle = source_config.getMigrationConfigBundle()
    assert bundle.didMigrateSettings
    
    # Clean up
    for payee in [payee1, payee2]:
        paymaster.removePayee(source_wallet.address, payee, sender=bob)
        paymaster.removePayee(dest_wallet.address, payee, sender=bob)


def test_clone_config_with_whitelist(setup_contracts, hatchery):
    """Test cloning configuration with whitelisted addresses"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    paymaster = ctx['paymaster']
    # Create fresh wallets for this test
    source_addr = hatchery.createUserWallet(ctx['bob'], ZERO_ADDRESS, False, 1, sender=ctx['bob'])
    dest_addr = hatchery.createUserWallet(ctx['bob'], ZERO_ADDRESS, False, 1, sender=ctx['bob'])
    
    source_wallet = UserWallet.at(source_addr)
    dest_wallet = UserWallet.at(dest_addr)
    source_config = UserWalletConfig.at(source_wallet.walletConfig())
    dest_config = UserWalletConfig.at(dest_wallet.walletConfig())
    
    bob = ctx['bob']
    addr1 = boa.env.generate_address()
    addr2 = boa.env.generate_address()
    addr3 = boa.env.generate_address()
    
    # Add whitelisted addresses to source
    for addr in [addr1, addr2, addr3]:
        paymaster.addWhitelistAddr(source_wallet.address, addr, sender=bob)
        boa.env.time_travel(blocks=source_config.timeLock() + 1)
        paymaster.confirmWhitelistAddr(source_wallet.address, addr, sender=bob)
    
    # Verify source has 3 whitelisted addresses
    # Note: whitelisted addresses are 1-indexed, so numWhitelisted = 4 for 3 addresses
    assert source_config.numWhitelisted() == 4
    assert dest_config.numWhitelisted() == 0
    
    # Clone configuration
    tx = migrator.cloneConfig(source_wallet.address, dest_wallet.address, sender=bob)
    
    # Check event
    events = filter_logs(migrator, "ConfigCloned")
    assert len(events) == 1
    event = events[0]
    assert event.numWhitelistCopied == 3
    
    # Verify destination has same whitelisted addresses
    assert dest_config.numWhitelisted() == 4  # 3 addresses (1-indexed)
    
    # Verify all addresses are whitelisted
    for addr in [addr1, addr2, addr3]:
        assert dest_config.isWhitelisted(addr)
    
    # Clean up
    for addr in [addr1, addr2, addr3]:
        paymaster.removeWhitelistAddr(source_wallet.address, addr, sender=bob)
        paymaster.removeWhitelistAddr(dest_wallet.address, addr, sender=bob)


def test_clone_config_with_managers(setup_contracts, hatchery):
    """Test cloning configuration with managers"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    boss_validator = ctx['boss_validator']
    # Create fresh wallets for this test
    # Use hatchery from fixture
    source_addr = hatchery.createUserWallet(ctx['bob'], ZERO_ADDRESS, False, 1, sender=ctx['bob'])
    dest_addr = hatchery.createUserWallet(ctx['bob'], ZERO_ADDRESS, False, 1, sender=ctx['bob'])
    
    source_wallet = UserWallet.at(source_addr)
    dest_wallet = UserWallet.at(dest_addr)
    source_config = UserWalletConfig.at(source_wallet.walletConfig())
    dest_config = UserWalletConfig.at(dest_wallet.walletConfig())
    
    bob = ctx['bob']
    manager1 = boa.env.generate_address()
    manager2 = boa.env.generate_address()
    createManagerSettings = ctx['createManagerSettings']
    
    # Get initial manager counts (may include starting agent)
    initial_source_managers = source_config.numManagers()
    initial_dest_managers = dest_config.numManagers()
    
    # Check if they have the same starting agent
    source_bundle = source_config.getMigrationConfigBundle()
    dest_bundle = dest_config.getMigrationConfigBundle()
    same_starting_agent = (source_bundle.startingAgent != ZERO_ADDRESS and 
                          source_bundle.startingAgent == dest_bundle.startingAgent)
    
    # Add managers to source wallet
    manager_settings = createManagerSettings()
    start_block, expiry_block, limits, lego_perms, whitelist_perms, transfer_perms, allowed_assets = manager_settings
    
    boss_validator.addManager(
        source_wallet.address,
        manager1,
        limits,
        lego_perms,
        whitelist_perms,
        transfer_perms,
        allowed_assets,
        sender=bob
    )
    
    # Add second manager with different permissions
    modified_transfer_perms = ctx['createTransferPerms'](
        _canTransfer=False,
        _canCreateCheque=True,
        _canAddPendingPayee=False
    )
    
    boss_validator.addManager(
        source_wallet.address,
        manager2,
        limits,
        lego_perms,
        whitelist_perms,
        modified_transfer_perms,
        allowed_assets,
        sender=bob
    )
    
    # Verify source has 2 more managers than initial
    assert source_config.numManagers() == initial_source_managers + 2
    
    # Clone configuration
    tx = migrator.cloneConfig(source_wallet.address, dest_wallet.address, sender=bob)
    
    # Check event
    events = filter_logs(migrator, "ConfigCloned")
    assert len(events) == 1
    event = events[0]
    # Event counts non-owner managers copied
    # We added 2 new managers, and starting agent is always skipped
    assert event.numManagersCopied == 2
    
    # Verify destination has same managers
    assert dest_config.numManagers() == source_config.numManagers()
    
    # Verify manager settings were copied
    manager1_settings_src = source_config.managerSettings(manager1)
    manager1_settings_dst = dest_config.managerSettings(manager1)
    assert manager1_settings_src.transferPerms.canTransfer == manager1_settings_dst.transferPerms.canTransfer
    
    manager2_settings_dst = dest_config.managerSettings(manager2)
    assert manager2_settings_dst.transferPerms.canTransfer == False
    assert manager2_settings_dst.transferPerms.canCreateCheque == True
    
    # Clean up
    for manager in [manager1, manager2]:
        boss_validator.removeManager(source_wallet.address, manager, sender=bob)
        boss_validator.removeManager(dest_wallet.address, manager, sender=bob)


def test_clone_config_global_settings(setup_contracts, hatchery):
    """Test cloning global manager and payee settings"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    boss_validator = ctx['boss_validator']
    paymaster = ctx['paymaster']
    # Create fresh wallets
    # Use hatchery from fixture
    source_addr = hatchery.createUserWallet(ctx['bob'], ZERO_ADDRESS, False, 1, sender=ctx['bob'])
    dest_addr = hatchery.createUserWallet(ctx['bob'], ZERO_ADDRESS, False, 1, sender=ctx['bob'])
    
    source_wallet = UserWallet.at(source_addr)
    dest_wallet = UserWallet.at(dest_addr)
    source_config = UserWalletConfig.at(source_wallet.walletConfig())
    dest_config = UserWalletConfig.at(dest_wallet.walletConfig())
    
    bob = ctx['bob']
    
    # Modify global manager settings in source
    new_global_manager_settings = boss_validator.createDefaultGlobalManagerSettings(
        ONE_DAY_IN_BLOCKS * 30,  # 30 day period
        ONE_DAY_IN_BLOCKS,  # 1 day timelock
        ONE_DAY_IN_BLOCKS * 7  # 7 day activation
    )
    source_config.setGlobalManagerSettings(new_global_manager_settings, sender=boss_validator.address)
    
    # Modify global payee settings in source
    new_global_payee_settings = paymaster.createDefaultGlobalPayeeSettings(
        ONE_DAY_IN_BLOCKS * 14,  # 14 day default period
        ONE_DAY_IN_BLOCKS * 2,  # 2 day start delay
        ONE_DAY_IN_BLOCKS * 3  # 3 day activation
    )
    source_config.setGlobalPayeeSettings(new_global_payee_settings, sender=paymaster.address)
    
    # Clone configuration
    migrator.cloneConfig(source_wallet.address, dest_wallet.address, sender=bob)
    
    # Verify global settings were copied
    dest_global_manager = dest_config.globalManagerSettings()
    assert dest_global_manager.managerPeriod == ONE_DAY_IN_BLOCKS * 30
    assert dest_global_manager.activationLength == ONE_DAY_IN_BLOCKS * 7
    
    dest_global_payee = dest_config.globalPayeeSettings()
    assert dest_global_payee.defaultPeriodLength == ONE_DAY_IN_BLOCKS * 14
    assert dest_global_payee.startDelay == ONE_DAY_IN_BLOCKS * 2
    assert dest_global_payee.activationLength == ONE_DAY_IN_BLOCKS * 3


def test_clone_empty_config(setup_contracts, hatchery):
    """Test cloning wallet with no configuration"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    # Create fresh wallets
    # Use hatchery from fixture
    source_addr = hatchery.createUserWallet(ctx['bob'], ZERO_ADDRESS, False, 1, sender=ctx['bob'])
    dest_addr = hatchery.createUserWallet(ctx['bob'], ZERO_ADDRESS, False, 1, sender=ctx['bob'])
    
    source_wallet = UserWallet.at(source_addr)
    source_config = UserWalletConfig.at(source_wallet.walletConfig())
    
    bob = ctx['bob']
    
    # Source has no payees, whitelist, or extra managers
    # Clone should still work
    tx = migrator.cloneConfig(source_addr, dest_addr, sender=bob)
    
    # Check event
    events = filter_logs(migrator, "ConfigCloned")
    assert len(events) == 1
    event = events[0]
    assert event.numManagersCopied == 0
    assert event.numPayeesCopied == 0
    assert event.numWhitelistCopied == 0
    
    # Verify migration flag
    bundle = source_config.getMigrationConfigBundle()
    assert bundle.didMigrateSettings


# Validation tests


def test_cannot_clone_config_twice(setup_contracts, hatchery):
    """Test that config cannot be cloned twice from same source"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    paymaster = ctx['paymaster']
    bob = ctx['bob']
    createPayeeLimits = ctx['createPayeeLimits']
    
    # Create fresh wallets
    source_addr = hatchery.createUserWallet(bob, ZERO_ADDRESS, False, 1, sender=bob)
    dest1_addr = hatchery.createUserWallet(bob, ZERO_ADDRESS, False, 1, sender=bob)
    dest2_addr = hatchery.createUserWallet(bob, ZERO_ADDRESS, False, 1, sender=bob)
    
    source_wallet = UserWallet.at(source_addr)
    source_config = UserWalletConfig.at(source_wallet.walletConfig())
    
    # Add some config to source
    payee = boa.env.generate_address()
    unit_limits = createPayeeLimits()
    usd_limits = createPayeeLimits()
    
    paymaster.addPayee(
        source_wallet.address,
        payee,
        False,
        ONE_DAY_IN_BLOCKS,
        10,
        0,
        False,
        ctx['alpha_token'].address,
        False,
        unit_limits,
        usd_limits,
        sender=bob
    )
    
    # First clone should succeed
    migrator.cloneConfig(source_addr, dest1_addr, sender=bob)
    
    # Verify flag is set
    bundle = source_config.getMigrationConfigBundle()
    assert bundle.didMigrateSettings
    
    # Second clone should fail
    with boa.reverts("cannot copy config"):
        migrator.cloneConfig(source_addr, dest2_addr, sender=bob)
    
    # Clean up
    paymaster.removePayee(source_wallet.address, payee, sender=bob)
    paymaster.removePayee(UserWallet.at(dest1_addr).address, payee, sender=bob)


def test_cannot_clone_config_different_owner(setup_contracts):
    """Test cannot clone config between wallets with different owners"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    source_wallet = ctx['source_wallet']
    alice_wallet = ctx['alice_wallet']
    bob = ctx['bob']
    
    # Bob cannot clone to Alice's wallet
    with boa.reverts("cannot copy config"):
        migrator.cloneConfig(source_wallet.address, alice_wallet.address, sender=bob)


def test_cannot_clone_config_different_group(setup_contracts):
    """Test cannot clone config between wallets with different group IDs"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    source_wallet = ctx['source_wallet']
    diff_group_wallet = ctx['diff_group_wallet']
    bob = ctx['bob']
    
    # Cannot clone between different groups
    with boa.reverts("cannot copy config"):
        migrator.cloneConfig(source_wallet.address, diff_group_wallet.address, sender=bob)


def test_cannot_clone_to_wallet_with_config(setup_contracts):
    """Test cannot clone to wallet that already has configuration"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    paymaster = ctx['paymaster']
    source_wallet = ctx['source_wallet']
    dest_wallet = ctx['dest_wallet']
    bob = ctx['bob']
    createPayeeLimits = ctx['createPayeeLimits']
    
    # Add payee to destination wallet
    payee = boa.env.generate_address()
    unit_limits = createPayeeLimits()
    usd_limits = createPayeeLimits()
    
    paymaster.addPayee(
        dest_wallet.address,
        payee,
        False,
        ONE_DAY_IN_BLOCKS,
        10,
        0,
        False,
        ctx['alpha_token'].address,
        False,
        unit_limits,
        usd_limits,
        sender=bob
    )
    
    # Should not be able to clone to wallet with existing payees
    with boa.reverts("cannot copy config"):
        migrator.cloneConfig(source_wallet.address, dest_wallet.address, sender=bob)
    
    # Clean up
    paymaster.removePayee(dest_wallet.address, payee, sender=bob)


def test_clone_to_wallet_with_starting_agent(setup_contracts):
    """Test can clone to wallet that only has starting agent"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    paymaster = ctx['paymaster']
    source_wallet = ctx['source_wallet']
    wallet_with_agent = ctx['wallet_with_agent']
    wallet_with_agent_config = UserWalletConfig.at(wallet_with_agent.walletConfig())
    bob = ctx['bob']
    createPayeeLimits = ctx['createPayeeLimits']
    
    # Verify wallet has starting agent
    bundle = wallet_with_agent_config.getMigrationConfigBundle()
    assert bundle.startingAgent != ZERO_ADDRESS
    assert bundle.numManagers == 2  # Owner + starting agent
    
    # Add config to source
    payee = boa.env.generate_address()
    unit_limits = createPayeeLimits()
    usd_limits = createPayeeLimits()
    
    paymaster.addPayee(
        source_wallet.address,
        payee,
        False,
        ONE_DAY_IN_BLOCKS,
        10,
        0,
        False,
        ctx['alpha_token'].address,
        False,
        unit_limits,
        usd_limits,
        sender=bob
    )
    
    # Should be able to clone to wallet with only starting agent
    migrator.cloneConfig(source_wallet.address, wallet_with_agent.address, sender=bob)
    
    # Verify config was copied
    # numPayees is 1-indexed, so numPayees=2 means there's 1 payee at index 1
    assert wallet_with_agent_config.numPayees() == 2
    
    # Clean up
    paymaster.removePayee(source_wallet.address, payee, sender=bob)
    paymaster.removePayee(wallet_with_agent.address, payee, sender=bob)


def test_clone_config_skips_starting_agent(setup_contracts, boss_validator, setManagerConfig, hatchery):
    """Test that cloning config skips the starting agent from source wallet"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    bob = ctx['bob']
    
    # Create wallets with starting agents
    setManagerConfig()  # Use default starting agent
    source_addr = hatchery.createUserWallet(bob, ZERO_ADDRESS, False, 1, sender=bob)
    dest_addr = hatchery.createUserWallet(bob, ZERO_ADDRESS, False, 1, sender=bob)
    
    source_wallet = UserWallet.at(source_addr)
    dest_wallet = UserWallet.at(dest_addr)
    source_config = UserWalletConfig.at(source_wallet.walletConfig())
    dest_config = UserWalletConfig.at(dest_wallet.walletConfig())
    
    # Get the starting agents
    source_bundle = source_config.getMigrationConfigBundle()
    dest_bundle = dest_config.getMigrationConfigBundle()
    source_starting_agent = source_bundle.startingAgent
    dest_starting_agent = dest_bundle.startingAgent
    
    # Verify both have starting agents
    assert source_starting_agent != ZERO_ADDRESS
    assert dest_starting_agent != ZERO_ADDRESS
    assert source_config.numManagers() == 2  # Owner + starting agent
    assert dest_config.numManagers() == 2  # Owner + starting agent
    
    # Add an additional manager to source
    manager1 = boa.env.generate_address()
    createManagerSettings = ctx['createManagerSettings']
    manager_settings = createManagerSettings()
    start_block, expiry_block, limits, lego_perms, whitelist_perms, transfer_perms, allowed_assets = manager_settings
    
    boss_validator.addManager(
        source_wallet.address,
        manager1,
        limits,
        lego_perms,
        whitelist_perms,
        transfer_perms,
        allowed_assets,
        sender=bob
    )
    
    assert source_config.numManagers() == 3  # Owner + starting agent + manager1
    
    # Clone config
    tx = migrator.cloneConfig(source_wallet.address, dest_wallet.address, sender=bob)
    
    # Check event - should only copy manager1, not the starting agent
    events = filter_logs(migrator, "ConfigCloned")
    assert len(events) == 1
    event = events[0]
    assert event.numManagersCopied == 1  # Only manager1
    
    # Verify destination still has its original starting agent plus the new manager
    assert dest_config.numManagers() == 3  # Owner + original starting agent + manager1
    
    # Verify the new manager was added
    manager1_settings = dest_config.managerSettings(manager1)
    assert manager1_settings.startBlock != 0
    
    # Verify source starting agent was NOT copied (dest still has its original)
    dest_starting_agent_after = dest_config.getMigrationConfigBundle().startingAgent
    assert dest_starting_agent_after == dest_starting_agent  # Unchanged
    
    # Clean up
    boss_validator.removeManager(source_wallet.address, manager1, sender=bob)
    boss_validator.removeManager(dest_wallet.address, manager1, sender=bob)


def test_clone_config_with_same_starting_agent(setup_contracts, boss_validator, setManagerConfig, hatchery):
    """Test cloning config when both wallets have the same starting agent"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    bob = ctx['bob']
    
    # Create wallets with a known starting agent
    setManagerConfig()  # Use default starting agent
    
    # Create source and destination wallets with the same starting agent
    source_with_agent = hatchery.createUserWallet(bob, ZERO_ADDRESS, False, 1, sender=bob)
    dest_with_agent = hatchery.createUserWallet(bob, ZERO_ADDRESS, False, 1, sender=bob)
    
    source_wallet = UserWallet.at(source_with_agent)
    dest_wallet = UserWallet.at(dest_with_agent)
    source_config = UserWalletConfig.at(source_wallet.walletConfig())
    dest_config = UserWalletConfig.at(dest_wallet.walletConfig())
    
    # Verify both have the same starting agent
    source_bundle = source_config.getMigrationConfigBundle()
    dest_bundle = dest_config.getMigrationConfigBundle()
    assert source_bundle.startingAgent != ZERO_ADDRESS
    assert source_bundle.startingAgent == dest_bundle.startingAgent
    
    # Add an additional manager to source
    manager1 = boa.env.generate_address()
    createManagerSettings = ctx['createManagerSettings']
    manager_settings = createManagerSettings()
    start_block, expiry_block, limits, lego_perms, whitelist_perms, transfer_perms, allowed_assets = manager_settings
    
    boss_validator.addManager(
        source_wallet.address,
        manager1,
        limits,
        lego_perms,
        whitelist_perms,
        transfer_perms,
        allowed_assets,
        sender=bob
    )
    
    # Record initial manager counts
    initial_source_managers = source_config.numManagers()
    initial_dest_managers = dest_config.numManagers()
    
    # Clone config
    migrator.cloneConfig(source_wallet.address, dest_wallet.address, sender=bob)
    events = filter_logs(migrator, "ConfigCloned")
    assert len(events) == 1
    event = events[0]
    # Should only copy manager1, not the starting agent (already exists)
    assert event.numManagersCopied == 1
    
    # Verify destination has the new manager
    assert dest_config.numManagers() == initial_dest_managers + 1
    
    # Verify the new manager was added
    manager1_settings = dest_config.managerSettings(manager1)
    assert manager1_settings.startBlock != 0
    
    # Clean up
    boss_validator.removeManager(source_wallet.address, manager1, sender=bob)
    boss_validator.removeManager(dest_wallet.address, manager1, sender=bob)


def test_clone_config_frozen_wallet(setup_contracts, switchboard_alpha, hatchery):
    """Test cannot clone from or to frozen wallets"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    bob = ctx['bob']
    
    # Create fresh wallets
    source_addr = hatchery.createUserWallet(bob, ZERO_ADDRESS, False, 1, sender=bob)
    dest_addr = hatchery.createUserWallet(bob, ZERO_ADDRESS, False, 1, sender=bob)
    
    source_config = UserWalletConfig.at(UserWallet.at(source_addr).walletConfig())
    dest_config = UserWalletConfig.at(UserWallet.at(dest_addr).walletConfig())
    
    # Test frozen source
    source_config.setFrozen(True, sender=switchboard_alpha.address)
    with boa.reverts("cannot copy config"):
        migrator.cloneConfig(source_addr, dest_addr, sender=bob)
    source_config.setFrozen(False, sender=switchboard_alpha.address)
    
    # Test frozen destination
    dest_config.setFrozen(True, sender=switchboard_alpha.address)
    with boa.reverts("cannot copy config"):
        migrator.cloneConfig(source_addr, dest_addr, sender=bob)
    dest_config.setFrozen(False, sender=switchboard_alpha.address)


# Integration tests


def test_complete_migration_flow(setup_contracts, hatchery, switchboard_alpha):
    """Test complete migration: clone config and migrate funds to separate wallets"""
    ctx = setup_contracts
    migrator = ctx['migrator']
    paymaster = ctx['paymaster']
    # Create fresh wallets - need separate destinations for config and funds
    source_addr = hatchery.createUserWallet(ctx['bob'], ZERO_ADDRESS, False, 1, sender=ctx['bob'])
    config_dest_addr = hatchery.createUserWallet(ctx['bob'], ZERO_ADDRESS, False, 1, sender=ctx['bob'])
    funds_dest_addr = hatchery.createUserWallet(ctx['bob'], ZERO_ADDRESS, False, 1, sender=ctx['bob'])
    
    source_wallet = UserWallet.at(source_addr)
    config_dest_wallet = UserWallet.at(config_dest_addr)
    funds_dest_wallet = UserWallet.at(funds_dest_addr)
    source_config = UserWalletConfig.at(source_wallet.walletConfig())
    config_dest_config = UserWalletConfig.at(config_dest_wallet.walletConfig())
    
    bob = ctx['bob']
    alpha_token = ctx['alpha_token']
    governance = ctx['governance']
    createPayeeLimits = ctx['createPayeeLimits']
    
    # Setup source wallet with config and funds
    payee = boa.env.generate_address()
    whitelist_addr = boa.env.generate_address()
    
    # Add payee
    unit_limits = createPayeeLimits()
    usd_limits = createPayeeLimits()
    paymaster.addPayee(
        source_wallet.address,
        payee,
        False,
        ONE_DAY_IN_BLOCKS,
        10,
        0,
        False,
        alpha_token.address,
        False,
        unit_limits,
        usd_limits,
        sender=bob
    )
    
    # Add whitelist
    paymaster.addWhitelistAddr(source_wallet.address, whitelist_addr, sender=bob)
    boa.env.time_travel(blocks=source_config.timeLock() + 1)
    paymaster.confirmWhitelistAddr(source_wallet.address, whitelist_addr, sender=bob)
    
    # Add funds
    alpha_token.transfer(source_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    source_config.updateAssetData(0, alpha_token.address, False, sender=switchboard_alpha.address)
    
    # Step 1: Clone config to one destination
    migrator.cloneConfig(source_wallet.address, config_dest_wallet.address, sender=bob)
    
    # Verify config migrated
    # 1-indexed: numPayees=2 means 1 payee, numWhitelisted=2 means 1 whitelisted address
    assert config_dest_config.numPayees() == 2
    assert config_dest_config.numWhitelisted() == 2
    assert config_dest_config.isWhitelisted(whitelist_addr)
    bundle = source_config.getMigrationConfigBundle()
    assert bundle.didMigrateSettings
    assert not bundle.didMigrateFunds
    
    # Step 2: Migrate funds to a different destination (can't migrate to wallet with config)
    num_migrated = migrator.migrateFunds(source_wallet.address, funds_dest_wallet.address, sender=bob)
    assert num_migrated == 1
    
    # Verify funds migrated
    assert alpha_token.balanceOf(funds_dest_wallet.address) == 1000 * EIGHTEEN_DECIMALS
    bundle = source_config.getMigrationConfigBundle()
    assert bundle.didMigrateSettings
    assert bundle.didMigrateFunds
    
    # Clean up
    paymaster.removePayee(source_wallet.address, payee, sender=bob)
    paymaster.removePayee(config_dest_wallet.address, payee, sender=bob)
    paymaster.removeWhitelistAddr(source_wallet.address, whitelist_addr, sender=bob)
    paymaster.removeWhitelistAddr(config_dest_wallet.address, whitelist_addr, sender=bob)