"""
Test comprehensive real-world scenarios for BossValidator
"""
import pytest
import boa
from eth_utils import to_checksum_address

from contracts.core.userWallet import UserWallet, UserWalletConfig
from constants import EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ZERO_ADDRESS, ACTION_TYPE
from conf_utils import filter_logs


@pytest.fixture(scope="module")
def setup_wallet(setUserWalletConfig, setManagerConfig, hatchery, bob):
    """Setup user wallet with config"""
    setUserWalletConfig()
    setManagerConfig()
    
    wallet_addr = hatchery.createUserWallet(sender=bob)
    assert wallet_addr != ZERO_ADDRESS
    return UserWallet.at(wallet_addr)


@pytest.fixture(scope="module")
def setup_contracts(setup_wallet, boss_validator, alice, bob, charlie, sally,
                   mock_lego_asset, alpha_token, whale, alpha_token_whale):
    """Setup contracts and basic configuration"""
    user_wallet = setup_wallet
    wallet_config_addr = user_wallet.walletConfig()
    wallet_config = UserWalletConfig.at(wallet_config_addr)
    owner = bob
    
    # Fund wallet
    mock_lego_asset.transfer(user_wallet.address, 10000 * EIGHTEEN_DECIMALS, sender=whale)
    alpha_token.transfer(user_wallet.address, 10000 * EIGHTEEN_DECIMALS, sender=alpha_token_whale)
    
    return {
        'wallet': user_wallet,
        'wallet_config': wallet_config,
        'boss_validator': boss_validator,
        'owner': owner,
        'manager1': alice,
        'manager2': charlie,
        'manager3': sally,
        'asset1': mock_lego_asset,
        'asset2': alpha_token
    }


# Test complete manager lifecycle with real operations


def test_manager_lifecycle_with_operations(setup_contracts, createManagerLimits,
                                         createLegoPerms, createWhitelistPerms,
                                         createTransferPerms, createManagerData):
    """Test complete manager lifecycle including permission changes during operations"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    manager = ctx['manager1']
    
    # Phase 1: Add manager with limited permissions
    initial_limits = createManagerLimits(
        _maxUsdValuePerTx=500 * EIGHTEEN_DECIMALS,
        _maxUsdValuePerPeriod=2000 * EIGHTEEN_DECIMALS,
        _maxUsdValueLifetime=10000 * EIGHTEEN_DECIMALS
    )
    
    initial_perms = createLegoPerms(
        _canManageYield=True,
        _canBuyAndSell=False,  # Initially cannot swap
        _canManageDebt=False,
        _canManageLiq=True,
        _canClaimRewards=False
    )
    
    boss.addManager(
        wallet.address,
        manager,
        initial_limits,
        initial_perms,
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        sender=owner
    )
    
    # Advance to make manager active
    settings = wallet_config.managerSettings(manager)
    if boa.env.evm.patch.block_number < settings[0]:
        boa.env.time_travel(blocks=settings[0] - boa.env.evm.patch.block_number + 1)
    
    # Verify initial permissions
    assert boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.EARN_DEPOSIT))
    assert not boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.SWAP))
    assert boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.ADD_LIQ))
    assert not boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.REWARDS))
    
    # Phase 2: Simulate some transactions to accumulate data
    manager_data = createManagerData()
    
    # First transaction
    manager_data = boss.checkManagerUsdLimitsAndUpdateData(
        300 * EIGHTEEN_DECIMALS,
        initial_limits,
        createManagerLimits(),  # No global limits
        ONE_DAY_IN_BLOCKS,
        manager_data
    )
    
    assert manager_data[0] == 1  # numTxsInPeriod
    assert manager_data[1] == 300 * EIGHTEEN_DECIMALS  # totalUsdValueInPeriod
    
    # Second transaction
    manager_data = boss.checkManagerUsdLimitsAndUpdateData(
        400 * EIGHTEEN_DECIMALS,
        initial_limits,
        createManagerLimits(),
        ONE_DAY_IN_BLOCKS,
        manager_data
    )
    
    assert manager_data[0] == 2  # numTxsInPeriod
    assert manager_data[1] == 700 * EIGHTEEN_DECIMALS  # totalUsdValueInPeriod
    
    # Phase 3: Update manager permissions while they have accumulated data
    updated_limits = createManagerLimits(
        _maxUsdValuePerTx=1000 * EIGHTEEN_DECIMALS,  # Increased
        _maxUsdValuePerPeriod=5000 * EIGHTEEN_DECIMALS,  # Increased
        _maxUsdValueLifetime=20000 * EIGHTEEN_DECIMALS  # Increased
    )
    
    updated_perms = createLegoPerms(
        _canManageYield=True,
        _canBuyAndSell=True,  # Now can swap
        _canManageDebt=True,  # Now can manage debt
        _canManageLiq=True,
        _canClaimRewards=True  # Now can claim rewards
    )
    
    boss.updateManager(
        wallet.address,
        manager,
        updated_limits,
        updated_perms,
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        sender=owner
    )
    
    # Verify updated permissions
    assert boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.SWAP))
    assert boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.BORROW))
    assert boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.REWARDS))
    
    # Phase 4: Test with new limits - should be able to do larger transaction
    manager_data = boss.checkManagerUsdLimitsAndUpdateData(
        800 * EIGHTEEN_DECIMALS,  # Would have failed with old limit
        updated_limits,
        createManagerLimits(),
        ONE_DAY_IN_BLOCKS,
        manager_data
    )
    
    assert manager_data[0] == 3  # numTxsInPeriod
    assert manager_data[1] == 1500 * EIGHTEEN_DECIMALS  # totalUsdValueInPeriod
    assert manager_data[2] == 3  # totalNumTxs
    assert manager_data[3] == 1500 * EIGHTEEN_DECIMALS  # totalUsdValue
    
    # Phase 5: Remove manager
    boss.removeManager(wallet.address, manager, sender=owner)
    
    # Verify manager removed
    assert not wallet_config.isManager(manager)
    assert not boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.TRANSFER))


# Test global settings changes affecting active managers


def test_global_settings_impact_on_active_managers(setup_contracts, createGlobalManagerSettings,
                                                  createManagerLimits, createLegoPerms,
                                                  createWhitelistPerms, createTransferPerms,
                                                  createManagerData):
    """Test how global settings changes affect managers with ongoing operations"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    manager1 = ctx['manager1']
    manager2 = ctx['manager2']
    
    # Set initial permissive global settings
    initial_global_limits = createManagerLimits(
        _maxUsdValuePerTx=2000 * EIGHTEEN_DECIMALS,
        _maxUsdValuePerPeriod=10000 * EIGHTEEN_DECIMALS
    )
    
    initial_global_settings = createGlobalManagerSettings(
        _limits=initial_global_limits,
        _canOwnerManage=True
    )
    
    boss.setGlobalManagerSettings(
        wallet.address,
        initial_global_settings[0],  # managerPeriod
        initial_global_settings[1],  # startDelay
        initial_global_settings[2],  # activationLength
        initial_global_settings[3],  # canOwnerManage
        initial_global_settings[4],  # limits
        initial_global_settings[5],  # legoPerms
        initial_global_settings[6],  # whitelistPerms
        initial_global_settings[7],  # transferPerms
        initial_global_settings[8],  # allowedAssets
        sender=owner
    )
    
    # Add two managers with different specific limits
    manager1_limits = createManagerLimits(
        _maxUsdValuePerTx=1500 * EIGHTEEN_DECIMALS
    )
    
    manager2_limits = createManagerLimits(
        _maxUsdValuePerTx=500 * EIGHTEEN_DECIMALS
    )
    
    boss.addManager(wallet.address, manager1, manager1_limits,
                   createLegoPerms(), createWhitelistPerms(),
                   createTransferPerms(), [], sender=owner)
    
    boss.addManager(wallet.address, manager2, manager2_limits,
                   createLegoPerms(), createWhitelistPerms(),
                   createTransferPerms(), [], sender=owner)
    
    # Advance to activate managers
    boa.env.time_travel(blocks=100)
    
    # Both managers do some transactions
    manager1_data = createManagerData()
    manager2_data = createManagerData()
    
    # Manager1 transaction at 1000 (within both limits)
    manager1_data = boss.checkManagerUsdLimitsAndUpdateData(
        1000 * EIGHTEEN_DECIMALS,
        manager1_limits,
        initial_global_limits,
        ONE_DAY_IN_BLOCKS,
        manager1_data
    )
    assert manager1_data[1] == 1000 * EIGHTEEN_DECIMALS
    
    # Manager2 transaction at 400 (within both limits)
    manager2_data = boss.checkManagerUsdLimitsAndUpdateData(
        400 * EIGHTEEN_DECIMALS,
        manager2_limits,
        initial_global_limits,
        ONE_DAY_IN_BLOCKS,
        manager2_data
    )
    assert manager2_data[1] == 400 * EIGHTEEN_DECIMALS
    
    # Change global settings to be more restrictive
    restrictive_global_limits = createManagerLimits(
        _maxUsdValuePerTx=300 * EIGHTEEN_DECIMALS,  # Very restrictive
        _maxUsdValuePerPeriod=1000 * EIGHTEEN_DECIMALS
    )
    
    restrictive_global_settings = createGlobalManagerSettings(
        _limits=restrictive_global_limits,
        _canOwnerManage=False  # Also disable owner management
    )
    
    boss.setGlobalManagerSettings(
        wallet.address,
        restrictive_global_settings[0],
        restrictive_global_settings[1],
        restrictive_global_settings[2],
        restrictive_global_settings[3],
        restrictive_global_settings[4],
        restrictive_global_settings[5],
        restrictive_global_settings[6],
        restrictive_global_settings[7],
        restrictive_global_settings[8],
        sender=owner
    )
    
    # Advance time to reset periods for both managers
    boa.env.time_travel(blocks=ONE_DAY_IN_BLOCKS + 1)
    
    # Now both managers are limited by new global settings
    # Manager1 trying to do 1000 should fail (over global per-tx limit of 300)
    with boa.reverts("usd value limit exceeded"):
        boss.checkManagerUsdLimitsAndUpdateData(
            1000 * EIGHTEEN_DECIMALS,  # Over global per-tx limit
            manager1_limits,
            restrictive_global_limits,
            ONE_DAY_IN_BLOCKS,
            manager1_data
        )
    
    # Manager2 trying to do 400 should also fail (over global per-tx limit of 300)
    with boa.reverts("usd value limit exceeded"):
        boss.checkManagerUsdLimitsAndUpdateData(
            400 * EIGHTEEN_DECIMALS,  # Over global per-tx limit
            manager2_limits,
            restrictive_global_limits,
            ONE_DAY_IN_BLOCKS,
            manager2_data
        )
    
    # But transactions within new global limit should work
    manager1_data = boss.checkManagerUsdLimitsAndUpdateData(
        250 * EIGHTEEN_DECIMALS,  # Within new global per-tx limit
        manager1_limits,
        restrictive_global_limits,
        ONE_DAY_IN_BLOCKS,
        manager1_data
    )
    # Period should be reset, so this is the first transaction of new period
    assert manager1_data[0] == 1  # numTxsInPeriod reset
    assert manager1_data[1] == 250 * EIGHTEEN_DECIMALS  # totalUsdValueInPeriod reset


# Test manager with asset restrictions and multiple assets


def test_complex_asset_restrictions(setup_contracts, createManagerLimits,
                                   createLegoPerms, createWhitelistPerms,
                                   createTransferPerms, mock_lego_asset,
                                   alpha_token):
    """Test managers with different asset restrictions operating simultaneously"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    manager1 = ctx['manager1']
    manager2 = ctx['manager2']
    manager3 = ctx['manager3']
    
    # Manager1: Can only use asset1
    boss.addManager(
        wallet.address,
        manager1,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [mock_lego_asset.address],  # Only asset1
        sender=owner
    )
    
    # Manager2: Can only use asset2
    boss.addManager(
        wallet.address,
        manager2,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [alpha_token.address],  # Only asset2
        sender=owner
    )
    
    # Manager3: Can use both assets
    boss.addManager(
        wallet.address,
        manager3,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [mock_lego_asset.address, alpha_token.address],  # Both assets
        sender=owner
    )
    
    # Advance to activate all managers
    boa.env.time_travel(blocks=100)
    
    # Test manager1 permissions
    assert boss.canSignerPerformAction(
        wallet.address, manager1, int(ACTION_TYPE.TRANSFER), 
        [mock_lego_asset.address]
    )
    assert not boss.canSignerPerformAction(
        wallet.address, manager1, int(ACTION_TYPE.TRANSFER),
        [alpha_token.address]
    )
    assert not boss.canSignerPerformAction(
        wallet.address, manager1, int(ACTION_TYPE.TRANSFER),
        [mock_lego_asset.address, alpha_token.address]
    )
    
    # Test manager2 permissions
    assert not boss.canSignerPerformAction(
        wallet.address, manager2, int(ACTION_TYPE.TRANSFER),
        [mock_lego_asset.address]
    )
    assert boss.canSignerPerformAction(
        wallet.address, manager2, int(ACTION_TYPE.TRANSFER),
        [alpha_token.address]
    )
    assert not boss.canSignerPerformAction(
        wallet.address, manager2, int(ACTION_TYPE.TRANSFER),
        [mock_lego_asset.address, alpha_token.address]
    )
    
    # Test manager3 permissions
    assert boss.canSignerPerformAction(
        wallet.address, manager3, int(ACTION_TYPE.TRANSFER),
        [mock_lego_asset.address]
    )
    assert boss.canSignerPerformAction(
        wallet.address, manager3, int(ACTION_TYPE.TRANSFER),
        [alpha_token.address]
    )
    assert boss.canSignerPerformAction(
        wallet.address, manager3, int(ACTION_TYPE.TRANSFER),
        [mock_lego_asset.address, alpha_token.address]
    )


# Test period reset with multiple managers


def test_period_reset_multiple_managers(setup_contracts, createManagerLimits,
                                       createLegoPerms, createWhitelistPerms,
                                       createTransferPerms, createManagerData):
    """Test period reset behavior with multiple managers operating"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    owner = ctx['owner']
    manager1 = ctx['manager1']
    manager2 = ctx['manager2']
    
    # Add two managers
    limits = createManagerLimits(
        _maxUsdValuePerPeriod=1000 * EIGHTEEN_DECIMALS
    )
    
    boss.addManager(wallet.address, manager1, limits,
                   createLegoPerms(), createWhitelistPerms(),
                   createTransferPerms(), [], sender=owner)
    
    boss.addManager(wallet.address, manager2, limits,
                   createLegoPerms(), createWhitelistPerms(),
                   createTransferPerms(), [], sender=owner)
    
    # Advance to activate
    boa.env.time_travel(blocks=100)
    
    # Both managers do transactions in current period
    manager1_data = createManagerData()
    manager2_data = createManagerData()
    
    current_block = boa.env.evm.patch.block_number
    
    # Manager1 uses 600
    manager1_data = boss.checkManagerUsdLimitsAndUpdateData(
        600 * EIGHTEEN_DECIMALS,
        limits,
        createManagerLimits(),
        ONE_DAY_IN_BLOCKS,
        manager1_data
    )
    
    # Manager2 uses 800
    manager2_data = boss.checkManagerUsdLimitsAndUpdateData(
        800 * EIGHTEEN_DECIMALS,
        limits,
        createManagerLimits(),
        ONE_DAY_IN_BLOCKS,
        manager2_data
    )
    
    # Advance past period boundary
    boa.env.time_travel(blocks=ONE_DAY_IN_BLOCKS + 1)
    
    # Both managers should have their periods reset independently
    # Manager1 can use full limit again
    manager1_data = boss.checkManagerUsdLimitsAndUpdateData(
        900 * EIGHTEEN_DECIMALS,
        limits,
        createManagerLimits(),
        ONE_DAY_IN_BLOCKS,
        manager1_data
    )
    
    assert manager1_data[0] == 1  # numTxsInPeriod reset
    assert manager1_data[1] == 900 * EIGHTEEN_DECIMALS  # New period value
    assert manager1_data[2] == 2  # totalNumTxs (lifetime)
    assert manager1_data[3] == 1500 * EIGHTEEN_DECIMALS  # totalUsdValue (lifetime)
    
    # Manager2 can also use full limit
    manager2_data = boss.checkManagerUsdLimitsAndUpdateData(
        700 * EIGHTEEN_DECIMALS,
        limits,
        createManagerLimits(),
        ONE_DAY_IN_BLOCKS,
        manager2_data
    )
    
    assert manager2_data[0] == 1  # numTxsInPeriod reset
    assert manager2_data[1] == 700 * EIGHTEEN_DECIMALS  # New period value
    assert manager2_data[2] == 2  # totalNumTxs (lifetime)
    assert manager2_data[3] == 1500 * EIGHTEEN_DECIMALS  # totalUsdValue (lifetime)


# Test manager activation length adjustments - covered in test_manager_operations.py


# Test owner permissions with global settings


def test_owner_permissions_with_global_canOwnerManage(setup_contracts, 
                                                     createGlobalManagerSettings,
                                                     createManagerData):
    """Test owner permissions controlled by global canOwnerManage setting"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    
    # Initially set canOwnerManage to true
    settings_with_owner = createGlobalManagerSettings(
        _canOwnerManage=True
    )
    
    boss.setGlobalManagerSettings(
        wallet.address,
        settings_with_owner[0],
        settings_with_owner[1],
        settings_with_owner[2],
        settings_with_owner[3],
        settings_with_owner[4],
        settings_with_owner[5],
        settings_with_owner[6],
        settings_with_owner[7],
        settings_with_owner[8],
        sender=owner
    )
    
    # Owner should be able to perform actions
    config = wallet_config.getManagerConfigs(owner)
    assert config[0] == True  # isOwner
    
    # Now disable owner management
    settings_without_owner = createGlobalManagerSettings(
        _canOwnerManage=False
    )
    
    boss.setGlobalManagerSettings(
        wallet.address,
        settings_without_owner[0],
        settings_without_owner[1],
        settings_without_owner[2],
        settings_without_owner[3],
        settings_without_owner[4],
        settings_without_owner[5],
        settings_without_owner[6],
        settings_without_owner[7],
        settings_without_owner[8],
        sender=owner
    )
    
    # Check using canSignerPerformActionWithConfig
    global_settings = wallet_config.globalManagerSettings()
    empty_manager_data = createManagerData()
    empty_manager_settings = (0, 0, (0, 0, 0, 0, 0, False), 
                             (True, True, True, True, True, []),
                             (False, True, True, False),
                             (True, True, True, []), [])
    
    # Owner should not be able to perform actions when canOwnerManage is false
    can_perform = boss.canSignerPerformActionWithConfig(
        True,  # isOwner
        False,  # isManager
        empty_manager_data,
        empty_manager_settings,
        global_settings,
        wallet.address,
        ACTION_TYPE.TRANSFER
    )
    
    assert not can_perform  # Owner cannot act when disabled