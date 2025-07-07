"""
Test helper functions and edge cases in BossValidator
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
def setup_contracts(setup_wallet, boss_validator, alice, bob):
    """Setup contracts and basic configuration"""
    user_wallet = setup_wallet
    wallet_config_addr = user_wallet.walletConfig()
    wallet_config = UserWalletConfig.at(wallet_config_addr)
    owner = bob
    
    # Advance some blocks
    boa.env.time_travel(blocks=100)
    
    return {
        'wallet': user_wallet,
        'wallet_config': wallet_config,
        'boss_validator': boss_validator,
        'owner': owner,
        'manager': alice
    }


# Test latest manager data calculation


def test_get_latest_manager_data_no_reset(setup_contracts, createManagerData, createManagerLimits):
    """Test manager data doesn't reset when period hasn't ended"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    current_block = boa.env.evm.patch.block_number
    
    # Create data from current period
    data = createManagerData(
        _numTxsInPeriod=5,
        _totalUsdValueInPeriod=1000 * EIGHTEEN_DECIMALS,
        _periodStartBlock=current_block - 100
    )
    
    # Use checkManagerUsdLimitsAndUpdateData which internally calls _getLatestManagerData
    limits = createManagerLimits()
    updated_data = boss.checkManagerUsdLimitsAndUpdateData(
        100 * EIGHTEEN_DECIMALS,  # New transaction
        limits,
        limits,
        ONE_DAY_IN_BLOCKS,
        data
    )
    
    # Period data should not be reset, just updated
    assert updated_data[0] == 6  # numTxsInPeriod incremented
    assert updated_data[1] == 1100 * EIGHTEEN_DECIMALS  # totalUsdValueInPeriod updated
    assert updated_data[5] == current_block - 100  # periodStartBlock unchanged


def test_get_latest_manager_data_with_reset(setup_contracts, createManagerData, createManagerLimits):
    """Test manager data resets when period has ended"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    # First advance enough blocks to ensure we can have an old period
    boa.env.time_travel(blocks=ONE_DAY_IN_BLOCKS * 2)
    
    current_block = boa.env.evm.patch.block_number
    
    # Create data from old period
    old_period_start = current_block - (ONE_DAY_IN_BLOCKS + 100)
    data = createManagerData(
        _numTxsInPeriod=10,
        _totalUsdValueInPeriod=2000 * EIGHTEEN_DECIMALS,
        _totalNumTxs=50,
        _totalUsdValue=10000 * EIGHTEEN_DECIMALS,
        _periodStartBlock=old_period_start
    )
    
    # Use checkManagerUsdLimitsAndUpdateData which internally resets the period
    limits = createManagerLimits()
    updated_data = boss.checkManagerUsdLimitsAndUpdateData(
        100 * EIGHTEEN_DECIMALS,  # New transaction
        limits,
        limits,
        ONE_DAY_IN_BLOCKS,
        data
    )
    
    # Period data should be reset
    assert updated_data[0] == 1  # numTxsInPeriod reset to 1 (new tx)
    assert updated_data[1] == 100 * EIGHTEEN_DECIMALS  # totalUsdValueInPeriod reset to new tx value
    # Lifetime data preserved and updated
    assert updated_data[2] == 51  # totalNumTxs incremented
    assert updated_data[3] == 10100 * EIGHTEEN_DECIMALS  # totalUsdValue updated
    # New period start
    assert updated_data[5] >= current_block  # New period started


def test_get_latest_manager_data_first_transaction(setup_contracts, createManagerData, createManagerLimits):
    """Test manager data for first transaction"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    # Empty data (first transaction)
    data = createManagerData()
    
    # Use checkManagerUsdLimitsAndUpdateData for first transaction
    limits = createManagerLimits()
    updated_data = boss.checkManagerUsdLimitsAndUpdateData(
        100 * EIGHTEEN_DECIMALS,  # First transaction
        limits,
        limits,
        ONE_DAY_IN_BLOCKS,
        data
    )
    
    # Should initialize with first transaction
    assert updated_data[0] == 1  # numTxsInPeriod = 1
    assert updated_data[1] == 100 * EIGHTEEN_DECIMALS  # totalUsdValueInPeriod
    assert updated_data[2] == 1  # totalNumTxs = 1
    assert updated_data[3] == 100 * EIGHTEEN_DECIMALS  # totalUsdValue
    assert updated_data[5] > 0  # periodStartBlock initialized


# Test create happy defaults


def test_create_happy_manager_defaults(setup_contracts):
    """Test happy manager defaults through createStarterAgentSettings"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    # Get defaults through createStarterAgentSettings
    settings = boss.createStarterAgentSettings(ONE_DAY_IN_BLOCKS)
    
    # Extract permissions
    lego_perms = settings[3]  # LegoPerms
    whitelist_perms = settings[4]  # WhitelistPerms
    transfer_perms = settings[5]  # TransferPerms
    
    # Verify lego permissions - all enabled
    assert lego_perms[0] == True  # canManageYield
    assert lego_perms[1] == True  # canBuyAndSell
    assert lego_perms[2] == True  # canManageDebt
    assert lego_perms[3] == True  # canManageLiq
    assert lego_perms[4] == True  # canClaimRewards
    assert len(lego_perms[5]) == 0  # No lego restrictions
    
    # Verify whitelist permissions
    assert whitelist_perms[0] == False  # canAddPending
    assert whitelist_perms[1] == True   # canConfirm
    assert whitelist_perms[2] == True   # canCancel
    assert whitelist_perms[3] == False  # canRemove
    
    # Verify transfer permissions
    assert transfer_perms[0] == True  # canTransfer
    assert transfer_perms[1] == True  # canCreateCheque
    assert transfer_perms[2] == True  # canAddPendingPayee
    assert len(transfer_perms[3]) == 0  # No payee restrictions


# Test action type mappings


def test_action_type_to_permission_mapping(setup_contracts, createManagerLimits,
                                         createLegoPerms, createWhitelistPerms,
                                         createTransferPerms, sally):
    """Test that action types map correctly to permissions"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    owner = ctx['owner']
    manager = sally  # Use sally for this test
    
    # Add manager with specific permissions disabled
    lego_perms = createLegoPerms(
        _canManageYield=False,
        _canBuyAndSell=False,
        _canManageDebt=True,
        _canManageLiq=True,
        _canClaimRewards=False
    )
    
    boss.addManager(
        wallet.address,
        manager,
        createManagerLimits(),
        lego_perms,
        createWhitelistPerms(),
        createTransferPerms(),
        [],
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
    
    # Test action mappings
    # EARN_DEPOSIT/WITHDRAW require canManageYield
    assert not boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.EARN_DEPOSIT))
    assert not boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.EARN_WITHDRAW))
    
    # SWAP requires canBuyAndSell
    assert not boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.SWAP))
    
    # REWARDS requires canClaimRewards
    assert not boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.REWARDS))
    
    # These should work (debt/liquidity management enabled)
    assert boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.ADD_COLLATERAL))
    assert boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.ADD_LIQ))


# Test edge cases


def test_zero_address_validation(setup_contracts, createManagerLimits, createLegoPerms,
                                createWhitelistPerms, createTransferPerms):
    """Test that zero addresses are properly rejected"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    owner = ctx['owner']
    
    # Try to add zero address as manager
    with boa.reverts("invalid manager"):
        boss.addManager(
            wallet.address,
            ZERO_ADDRESS,
            createManagerLimits(),
            createLegoPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            sender=owner
        )


def test_self_manager(setup_contracts, createManagerLimits, createLegoPerms,
                     createWhitelistPerms, createTransferPerms):
    """Test adding wallet as its own manager"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    owner = ctx['owner']
    
    # Add wallet as its own manager (this is allowed by design)
    boss.addManager(
        wallet.address,
        wallet.address,  # Wallet as manager
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        sender=owner
    )
    
    # Verify wallet is now a manager of itself
    assert ctx['wallet_config'].isManager(wallet.address)
    
    # Wallet should be able to perform actions on itself as a manager
    # (after activation delay passes)
    wallet_config = ctx['wallet_config']
    settings = wallet_config.managerSettings(wallet.address)
    if boa.env.evm.patch.block_number < settings[0]:
        boa.env.time_travel(blocks=settings[0] - boa.env.evm.patch.block_number + 1)
    
    assert boss.canSignerPerformAction(wallet.address, wallet.address, int(ACTION_TYPE.TRANSFER))


def test_owner_as_manager(setup_contracts, createManagerLimits, createLegoPerms,
                         createWhitelistPerms, createTransferPerms):
    """Test that owner cannot be added as a manager"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    owner = ctx['owner']
    
    # Try to add owner as manager - should fail
    with boa.reverts("invalid manager"):
        boss.addManager(
            wallet.address,
            owner,
            createManagerLimits(),
            createLegoPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            sender=owner
        )
    
    # Owner is already owner and doesn't need to be a manager
    config = ctx['wallet_config'].getManagerConfigs(owner)
    assert config[0] == True  # isOwner
    assert config[1] == False  # isManager (not needed, owner has full permissions)


def test_validate_and_create_manager_settings(setup_contracts, createManagerLimits,
                                             createLegoPerms, createWhitelistPerms,
                                             createTransferPerms, createGlobalManagerSettings):
    """Test validateAndCreateManagerSettings function"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet_config = ctx['wallet_config']
    
    # Create global settings
    global_settings = createGlobalManagerSettings()
    
    # Create and validate settings
    validated_settings = boss.validateAndCreateManagerSettings(
        100,  # startDelay
        ONE_DAY_IN_BLOCKS * 30,  # activationLength
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],  # allowedAssets
        0,  # currentTimeLock
        global_settings,
        False,  # inEjectMode
        ZERO_ADDRESS,  # legoBookAddr
        wallet_config.address
    )
    
    # Should have proper structure
    assert validated_settings[0] > 0  # startBlock
    assert validated_settings[1] > validated_settings[0]  # expiryBlock > startBlock
    assert len(validated_settings[2]) == 6  # ManagerLimits tuple
    assert len(validated_settings[3]) == 6  # LegoPerms tuple
    assert len(validated_settings[4]) == 4  # WhitelistPerms tuple
    assert len(validated_settings[5]) == 4  # TransferPerms tuple


def test_non_existent_wallet(setup_contracts, createManagerLimits, createLegoPerms,
                            createWhitelistPerms, createTransferPerms):
    """Test operations on non-existent wallet"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    owner = ctx['owner']
    manager = ctx['manager']
    
    fake_wallet = to_checksum_address("0x" + "9" * 40)
    
    # Should fail - wallet doesn't exist
    with boa.reverts("not a user wallet"):
        boss.addManager(
            fake_wallet,
            manager,
            createManagerLimits(),
            createLegoPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            sender=owner
        )


def test_max_values_validation(setup_contracts, createManagerLimits, createManagerData):
    """Test validation with maximum uint256 values"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    max_uint = 2**256 - 1
    
    # Create limits with max values
    max_limits = createManagerLimits(
        _maxUsdValuePerTx=max_uint,
        _maxUsdValuePerPeriod=max_uint,
        _maxUsdValueLifetime=max_uint
    )
    
    # Should pass validation (0 means unlimited, max is effectively unlimited)
    # This tests overflow protection
    data = createManagerData()
    
    # Should handle large values gracefully
    updated_data = boss.checkManagerUsdLimitsAndUpdateData(
        EIGHTEEN_DECIMALS,  # Small tx value
        max_limits,
        createManagerLimits(),
        ONE_DAY_IN_BLOCKS,
        data
    )