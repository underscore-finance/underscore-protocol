"""
Test manager access control functionality in BossValidator
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
def setup_contracts(setup_wallet, boss_validator, alice, bob, charlie):
    """Setup contracts and basic configuration"""
    user_wallet = setup_wallet
    wallet_config_addr = user_wallet.walletConfig()
    wallet_config = UserWalletConfig.at(wallet_config_addr)
    owner = bob  # bob is the owner
    
    # Advance some blocks to ensure we're not at block 0
    boa.env.time_travel(blocks=100)
    
    return {
        'wallet': user_wallet,
        'wallet_config': wallet_config,
        'boss_validator': boss_validator,
        'owner': owner,
        'manager': alice,
        'non_manager': charlie
    }


# Test owner access


def test_owner_can_perform_all_actions(setup_contracts):
    """Owner should be able to perform all actions"""
    ctx = setup_contracts
    owner = ctx['owner']
    wallet = ctx['wallet']
    boss = ctx['boss_validator']
    
    # Test all action types
    # Test all action types
    actions = [
        int(ACTION_TYPE.TRANSFER),
        ACTION_TYPE.EARN_DEPOSIT,
        ACTION_TYPE.EARN_WITHDRAW,
        int(ACTION_TYPE.SWAP),
        ACTION_TYPE.REWARDS,
        ACTION_TYPE.BORROW,
        ACTION_TYPE.ADD_COLLATERAL,
    ]
    
    for action in actions:
        assert boss.canSignerPerformAction(
            wallet.address,
            owner,
            int(action)
        ), f"Owner should be able to perform {action}"


def test_non_manager_cannot_perform_actions(setup_contracts):
    """Non-manager should not be able to perform any actions"""
    ctx = setup_contracts
    non_manager = ctx['non_manager']
    wallet = ctx['wallet']
    boss = ctx['boss_validator']
    
    # Test all action types
    # Test action types
    actions = [
        int(ACTION_TYPE.TRANSFER),
        ACTION_TYPE.EARN_DEPOSIT,
        ACTION_TYPE.EARN_WITHDRAW,
        int(ACTION_TYPE.SWAP),
    ]
    
    for action in actions:
        assert not boss.canSignerPerformAction(
            wallet.address,
            non_manager,
            int(action)
        ), f"Non-manager should not be able to perform {action}"


# Test manager permissions


def test_manager_with_specific_permissions(setup_contracts, createManagerLimits,
                                          createLegoPerms, createTransferPerms, 
                                          createWhitelistPerms):
    """Test manager with specific permissions"""
    ctx = setup_contracts
    manager = ctx['manager']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    boss = ctx['boss_validator']
    owner = ctx['owner']
    
    # Create manager with specific permissions
    lego_perms = createLegoPerms(
        _canManageYield=True,
        _canBuyAndSell=True,
        _canManageDebt=False,
        _canManageLiq=False,
        _canClaimRewards=True
    )
    
    transfer_perms = createTransferPerms(
        _canTransfer=True,
        _canCreateCheque=False
    )
    
    # Create full manager settings
    limits = createManagerLimits()
    whitelist_perms = createWhitelistPerms()
    
    # Add manager through BossValidator
    boss.addManager(
        wallet.address,
        manager,
        limits,
        lego_perms,
        whitelist_perms,
        transfer_perms,
        [],  # No asset restrictions
        0,  # startDelay
        0,  # activationLength (0 = use global default)
        sender=owner
    )
    
    # Verify manager was added
    assert wallet_config.isManager(manager), "Manager should be registered"
    
    # Get manager settings to debug
    settings = wallet_config.managerSettings(manager)
    manager_start = settings[0]
    
    # Advance to manager start block if needed
    current_block = boa.env.evm.patch.block_number
    if current_block < manager_start:
        blocks_to_advance = manager_start - current_block + 1
        boa.env.time_travel(blocks=blocks_to_advance)
    
    # Test allowed actions
    assert boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.TRANSFER))
    assert boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.EARN_DEPOSIT))
    assert boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.SWAP))
    assert boss.canSignerPerformAction(wallet.address, manager, int(ACTION_TYPE.REWARDS))


def test_manager_expired(setup_contracts, createManagerSettings):
    """Test that expired managers cannot perform actions"""
    ctx = setup_contracts
    manager = ctx['manager']
    wallet = ctx['wallet']
    boss = ctx['boss_validator']
    owner = ctx['owner']
    
    # Create manager settings (will be adjusted by fixture)
    settings = createManagerSettings()
    
    # Add manager with minimum activation length
    min_activation = 1800  # MIN_ACTIVATION_LENGTH from config
    boss.addManager(
        wallet.address,
        manager,
        settings[2],  # limits
        settings[3],  # lego perms
        settings[4],  # whitelist perms
        settings[5],  # transfer perms
        settings[6],  # allowed assets
        0,  # startDelay = 0 (start immediately)
        min_activation,  # activationLength = minimum allowed
        sender=owner
    )
    
    # Advance time so manager expires
    # Need to account for the start block plus activation length
    wallet_config = ctx['wallet_config']
    settings = wallet_config.managerSettings(manager)
    manager_start = settings[0]
    manager_expiry = settings[1]
    current_block = boa.env.evm.patch.block_number
    
    # Advance past expiry
    blocks_to_advance = manager_expiry - current_block + 10
    boa.env.time_travel(blocks=blocks_to_advance)
    
    # Should not be able to perform actions
    assert not boss.canSignerPerformAction(
        wallet.address,
        manager,
        int(ACTION_TYPE.TRANSFER)
    ), "Expired manager should not be able to perform actions"


def test_manager_not_yet_active(setup_contracts, createManagerSettings):
    """Test that managers not yet active cannot perform actions"""
    ctx = setup_contracts
    manager = ctx['manager']
    wallet = ctx['wallet']
    boss = ctx['boss_validator']
    owner = ctx['owner']
    
    # Create manager settings
    settings = createManagerSettings()
    
    # Add future manager through BossValidator
    future_start_delay = 1000
    activation_length = 1800  # Use minimum activation length
    
    boss.addManager(
        wallet.address,
        manager,
        settings[2],  # limits
        settings[3],  # lego perms
        settings[4],  # whitelist perms
        settings[5],  # transfer perms
        settings[6],  # allowed assets
        future_start_delay,  # startDelay - starts in 1000 blocks
        activation_length,  # activationLength
        sender=owner
    )
    
    # Should not be able to perform actions yet
    assert not boss.canSignerPerformAction(
        wallet.address,
        manager,
        int(ACTION_TYPE.TRANSFER)
    ), "Future manager should not be able to perform actions yet"


# Test with custom config


def test_access_with_custom_config(setup_contracts, createManagerData, 
                                  createManagerSettings, createGlobalManagerSettings,
                                  createManagerLimits):
    """Test access control with custom configuration"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    # Create custom data
    data = createManagerData(
        _numTxsInPeriod=5,
        _totalUsdValueInPeriod=1000 * EIGHTEEN_DECIMALS
    )
    
    # Create restrictive settings
    limits = createManagerLimits(
        _maxNumTxsPerPeriod=10,
        _maxUsdValuePerPeriod=2000 * EIGHTEEN_DECIMALS
    )
    
    settings = createManagerSettings(_limits=limits)
    global_settings = createGlobalManagerSettings(_canOwnerManage=True)
    
    # Test with manager
    result = boss.canSignerPerformActionWithConfig(
        False,  # isOwner
        True,   # isManager
        data,
        settings,
        global_settings,
        ctx['wallet_config'].address,
        int(ACTION_TYPE.TRANSFER)
    )
    
    assert result, "Manager with valid config should be able to perform action"
    
    # Test with non-manager
    result = boss.canSignerPerformActionWithConfig(
        False,  # isOwner
        False,  # isManager
        data,
        settings,
        global_settings,
        ctx['wallet_config'].address,
        int(ACTION_TYPE.TRANSFER)
    )
    
    assert not result, "Non-manager should not be able to perform action"


# Test asset restrictions


def test_manager_with_allowed_assets(setup_contracts, createManagerSettings,
                                    mock_lego_asset, alpha_token):
    """Test manager restricted to specific assets"""
    ctx = setup_contracts
    manager = ctx['manager']
    wallet = ctx['wallet']
    boss = ctx['boss_validator']
    owner = ctx['owner']
    
    # Create manager with asset restrictions
    allowed_assets = [mock_lego_asset.address, alpha_token.address]
    settings = createManagerSettings(_allowedAssets=allowed_assets)
    
    boss.addManager(
        wallet.address,
        manager,
        settings[2],  # limits
        settings[3],  # lego perms
        settings[4],  # whitelist perms
        settings[5],  # transfer perms
        allowed_assets,
        0,  # startDelay
        0,  # activationLength
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
    
    # Should be able to transfer allowed assets
    assert boss.canSignerPerformAction(
        wallet.address,
        manager,
        int(ACTION_TYPE.TRANSFER),
        [mock_lego_asset.address]
    ), "Manager should be able to transfer allowed asset"
    
    # Should not be able to transfer non-allowed assets
    other_asset = to_checksum_address("0x" + "1" * 40)
    assert not boss.canSignerPerformAction(
        wallet.address,
        manager,
        int(ACTION_TYPE.TRANSFER),
        [other_asset]
    ), "Manager should not be able to transfer non-allowed asset"


# Test lego restrictions


def test_manager_with_allowed_legos(setup_contracts, createLegoPerms, 
                                   createManagerLimits, createWhitelistPerms,
                                   createTransferPerms):
    """Test manager restricted to specific legos"""
    ctx = setup_contracts
    manager = ctx['manager']
    wallet = ctx['wallet']
    boss = ctx['boss_validator']
    owner = ctx['owner']
    
    # Create manager with lego restrictions
    # Only lego ID 1 exists in the test setup
    allowed_legos = [1]
    lego_perms = createLegoPerms(
        _canBuyAndSell=True,
        _allowedLegos=allowed_legos
    )
    
    boss.addManager(
        wallet.address,
        manager,
        createManagerLimits(),
        lego_perms,
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        0,  # startDelay
        0,  # activationLength
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
    
    # Should be able to use allowed legos
    assert boss.canSignerPerformAction(
        wallet.address,
        manager,
        int(ACTION_TYPE.SWAP),
        [],  # assets
        [1]  # lego ID 1 is allowed
    ), "Manager should be able to use allowed lego"
    
    # Should not be able to use non-allowed legos
    assert not boss.canSignerPerformAction(
        wallet.address,
        manager,
        int(ACTION_TYPE.SWAP),
        [],  # assets
        [2]  # lego ID 2 is not allowed
    ), "Manager should not be able to use non-allowed lego"


# Potential issues to raise:
# 1. The contract doesn't seem to validate if a lego ID actually exists when checking permissions
# 2. Asset restrictions might need to handle ETH (0xEee...) specially
# 3. No explicit action type for debt management, but there's a permission for it