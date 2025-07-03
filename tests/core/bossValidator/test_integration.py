"""
Test integration scenarios for BossValidator
"""
import pytest
import boa

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
def setup_contracts(setup_wallet, boss_validator, alice, bob, charlie, whale,
                   mock_lego_asset, alpha_token, alpha_token_whale):
    """Setup contracts and basic configuration"""
    user_wallet = setup_wallet
    wallet_config_addr = user_wallet.walletConfig()
    wallet_config = UserWalletConfig.at(wallet_config_addr)
    owner = bob
    
    # Fund wallet with tokens
    mock_lego_asset.transfer(user_wallet.address, 10000 * EIGHTEEN_DECIMALS, sender=whale)
    alpha_token.transfer(user_wallet.address, 10000 * EIGHTEEN_DECIMALS, sender=alpha_token_whale)
    
    # Advance some blocks
    boa.env.time_travel(blocks=100)
    
    return {
        'wallet': user_wallet,
        'wallet_config': wallet_config,
        'boss_validator': boss_validator,
        'owner': owner,
        'manager': alice,
        'manager2': charlie,
        'asset1': mock_lego_asset,
        'asset2': alpha_token
    }


# Test complete manager lifecycle


def test_manager_lifecycle(setup_contracts, createManagerLimits, createLegoPerms,
                         createWhitelistPerms, createTransferPerms):
    """Test complete manager lifecycle from addition to removal"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    manager = ctx['manager']
    
    # 1. Add manager with specific permissions
    limits = createManagerLimits(
        _maxUsdValuePerTx=100 * EIGHTEEN_DECIMALS,
        _maxNumTxsPerPeriod=10
    )
    
    lego_perms = createLegoPerms(
        _canManageYield=True,
        _canBuyAndSell=False
    )
    
    boss.addManager(
        wallet.address,
        manager,
        limits,
        lego_perms,
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        sender=owner
    )
    
    # Advance time to ensure manager is active
    settings = wallet_config.managerSettings(manager)
    manager_start = settings[0]
    current_block = boa.env.evm.patch.block_number
    if current_block < manager_start:
        blocks_to_advance = manager_start - current_block + 1
        boa.env.time_travel(blocks=blocks_to_advance)
    
    # 2. Verify manager can perform allowed actions
    assert boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.EARN_DEPOSIT))
    assert not boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.SWAP))
    
    # 3. Update manager permissions
    new_lego_perms = createLegoPerms(
        _canManageYield=True,
        _canBuyAndSell=True  # Now allowed
    )
    
    boss.updateManager(
        wallet.address,
        manager,
        limits,
        new_lego_perms,
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        sender=owner
    )
    
    # 4. Verify updated permissions
    assert boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.SWAP))
    
    # 5. Adjust activation length
    boss.adjustManagerActivationLength(
        wallet.address,
        manager,
        ONE_DAY_IN_BLOCKS * 60,  # 60 days
        False,
        sender=owner
    )
    
    # 6. Remove manager
    boss.removeManager(wallet.address, manager, sender=owner)
    
    # 7. Verify manager removed
    assert not wallet_config.isManager(manager)
    assert not boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.TRANSFER))


# Test global and specific limits interaction


def test_global_and_specific_limits(setup_contracts, createGlobalManagerSettings,
                                  createManagerLimits, createLegoPerms,
                                  createWhitelistPerms, createTransferPerms,
                                  createManagerData):
    """Test interaction between global and specific manager limits"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    manager = ctx['manager']
    
    # 1. Set restrictive global limits
    global_limits = createManagerLimits(
        _maxUsdValuePerTx=50 * EIGHTEEN_DECIMALS,
        _maxNumTxsPerPeriod=5
    )
    
    global_settings = createGlobalManagerSettings(
        _limits=global_limits,
        _canOwnerManage=True
    )
    
    boss.setGlobalManagerSettings(
        wallet.address,  # user wallet, not config
        global_settings[0],  # managerPeriod
        global_settings[1],  # startDelay  
        global_settings[2],  # activationLength
        global_settings[3],  # canOwnerManage
        global_settings[4],  # limits
        global_settings[5],  # legoPerms
        global_settings[6],  # whitelistPerms
        global_settings[7],  # transferPerms
        global_settings[8],  # allowedAssets
        sender=owner  # owner, not boss
    )
    
    # 2. Add manager with generous limits
    manager_limits = createManagerLimits(
        _maxUsdValuePerTx=1000 * EIGHTEEN_DECIMALS,
        _maxNumTxsPerPeriod=100
    )
    
    boss.addManager(
        wallet.address,
        manager,
        manager_limits,
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        sender=owner
    )
    
    # 3. Test that global limits take precedence
    # Transaction over global limit should fail
    manager_data = createManagerData()  # Create empty manager data
    
    with boa.reverts():
        boss.checkManagerUsdLimitsAndUpdateData(
            60 * EIGHTEEN_DECIMALS,  # Over global limit of 50
            manager_limits,
            global_limits,  # Global limits (not global_limits[4])
            ONE_DAY_IN_BLOCKS,
            manager_data
        )


# Test manager with asset restrictions


def test_manager_with_asset_restrictions(setup_contracts, createManagerLimits,
                                       createLegoPerms, createWhitelistPerms,
                                       createTransferPerms):
    """Test manager restricted to specific assets"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    owner = ctx['owner']
    manager = ctx['manager']
    asset1 = ctx['asset1']
    asset2 = ctx['asset2']
    
    # Add manager restricted to asset1 only
    boss.addManager(
        wallet.address,
        manager,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [asset1.address],  # Only asset1 allowed
        sender=owner
    )
    
    # Advance time to ensure manager is active
    wallet_config = ctx['wallet_config']
    settings = wallet_config.managerSettings(manager)
    manager_start = settings[0]
    current_block = boa.env.evm.patch.block_number
    if current_block < manager_start:
        blocks_to_advance = manager_start - current_block + 1
        boa.env.time_travel(blocks=blocks_to_advance)
    
    # Manager can transfer asset1
    assert boss.canSignerPerformAction(
        wallet.address,
        manager,
        int(ACTION_TYPE.TRANSFER),
        [asset1.address]
    )
    
    # Manager cannot transfer asset2
    assert not boss.canSignerPerformAction(
        wallet.address,
        manager,
        int(ACTION_TYPE.TRANSFER),
        [asset2.address]
    )
    
    # Manager cannot transfer both
    assert not boss.canSignerPerformAction(
        wallet.address,
        manager,
        int(ACTION_TYPE.TRANSFER),
        [asset1.address, asset2.address]
    )


# Test multiple managers with different permissions


def test_multiple_managers_scenario(setup_contracts, createManagerLimits,
                                  createLegoPerms, createWhitelistPerms,
                                  createTransferPerms):
    """Test multiple managers with different roles"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    trader = ctx['manager']
    yield_manager = ctx['manager2']
    
    # 1. Add trader - can swap but not manage yield
    trader_perms = createLegoPerms(
        _canManageYield=False,
        _canBuyAndSell=True,
        _canManageDebt=False,
        _canManageLiq=False,
        _canClaimRewards=False
    )
    
    boss.addManager(
        wallet.address,
        trader,
        createManagerLimits(_maxUsdValuePerTx=1000 * EIGHTEEN_DECIMALS),
        trader_perms,
        createWhitelistPerms(),
        createTransferPerms(_canTransfer=False),  # Cannot transfer
        [],
        sender=owner
    )
    
    # 2. Add yield manager - can manage yield but not swap
    yield_perms = createLegoPerms(
        _canManageYield=True,
        _canBuyAndSell=False,
        _canManageDebt=True,
        _canManageLiq=True,
        _canClaimRewards=True
    )
    
    boss.addManager(
        wallet.address,
        yield_manager,
        createManagerLimits(_maxUsdValuePerTx=5000 * EIGHTEEN_DECIMALS),
        yield_perms,
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        sender=owner
    )
    
    # Advance time to ensure both managers are active
    for mgr in [trader, yield_manager]:
        settings = wallet_config.managerSettings(mgr)
        manager_start = settings[0]
        current_block = boa.env.evm.patch.block_number
        if current_block < manager_start:
            blocks_to_advance = manager_start - current_block + 1
            boa.env.time_travel(blocks=blocks_to_advance)
    
    # 3. Verify permissions
    # Trader can swap but not yield
    assert boss.canSignerPerformAction(wallet.address, trader, int(ACTION_TYPE.SWAP))
    assert not boss.canSignerPerformAction(wallet.address, trader, int(ACTION_TYPE.EARN_DEPOSIT))
    assert not boss.canSignerPerformAction(wallet.address, trader, int(ACTION_TYPE.TRANSFER))
    
    # Yield manager can yield but not swap
    assert boss.canSignerPerformAction(wallet.address, yield_manager, int(ACTION_TYPE.EARN_DEPOSIT))
    assert not boss.canSignerPerformAction(wallet.address, yield_manager, int(ACTION_TYPE.SWAP))
    assert boss.canSignerPerformAction(wallet.address, yield_manager, int(ACTION_TYPE.TRANSFER))
    
    # Both are managers
    assert wallet_config.isManager(trader)
    assert wallet_config.isManager(yield_manager)


# Test manager expiry and timing


def test_manager_timing_scenarios(setup_contracts, createManagerLimits,
                                createLegoPerms, createWhitelistPerms,
                                createTransferPerms):
    """Test manager timing scenarios"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    owner = ctx['owner']
    manager = ctx['manager']
    
    current_block = boa.env.evm.patch.block_number
    
    # 1. Add manager starting in future
    start_delay = 1000  # blocks in future
    activation_length = 4000  # blocks active
    
    boss.addManager(
        wallet.address,
        manager,
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        start_delay,  # _startDelay parameter
        activation_length,  # _activationLength parameter
        sender=owner
    )
    
    # Manager not active yet
    assert not boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.TRANSFER))
    
    # 2. Advance to activation
    boa.env.time_travel(blocks=1001)
    
    # Now active
    assert boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.TRANSFER))
    
    # 3. Advance near expiry
    boa.env.time_travel(blocks=3500)
    
    # Still active
    assert boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.TRANSFER))
    
    # 4. Advance past expiry
    boa.env.time_travel(blocks=1000)
    
    # No longer active
    assert not boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.TRANSFER))


# Test USD tracking across transactions


def test_usd_tracking_integration(setup_contracts, createManagerLimits,
                                createLegoPerms, createWhitelistPerms,
                                createTransferPerms, createManagerData):
    """Test USD value tracking across multiple transactions"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    manager = ctx['manager']
    
    # Add manager with specific USD limits
    limits = createManagerLimits(
        _maxUsdValuePerTx=100 * EIGHTEEN_DECIMALS,
        _maxUsdValuePerPeriod=500 * EIGHTEEN_DECIMALS,
        _maxUsdValueLifetime=2000 * EIGHTEEN_DECIMALS,
        _maxNumTxsPerPeriod=10
    )
    
    boss.addManager(
        wallet.address,
        manager,
        limits,
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        sender=owner
    )
    
    # Simulate multiple transactions
    manager_data = (0, 0, 0, 0, 0, boa.env.evm.patch.block_number)
    
    # Transaction 1: 80 USD
    updated_data = boss.checkManagerUsdLimitsAndUpdateData(
        80 * EIGHTEEN_DECIMALS,
        limits,
        createManagerLimits(),  # No global limits
        ONE_DAY_IN_BLOCKS,
        manager_data
    )
    
    assert updated_data[0] == 1  # numTxsInPeriod
    assert updated_data[1] == 80 * EIGHTEEN_DECIMALS  # totalUsdValueInPeriod
    
    # Transaction 2: 90 USD
    updated_data = boss.checkManagerUsdLimitsAndUpdateData(
        90 * EIGHTEEN_DECIMALS,
        limits,
        createManagerLimits(),
        ONE_DAY_IN_BLOCKS,
        updated_data
    )
    
    assert updated_data[0] == 2  # numTxsInPeriod
    assert updated_data[1] == 170 * EIGHTEEN_DECIMALS  # totalUsdValueInPeriod
    
    # Transaction 3: Would exceed per-period limit
    with boa.reverts():
        boss.checkManagerUsdLimitsAndUpdateData(
            400 * EIGHTEEN_DECIMALS,  # Would total 570, exceeding 500 limit
            limits,
            createManagerLimits(),
            ONE_DAY_IN_BLOCKS,
            updated_data
        )