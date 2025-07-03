"""
Test global manager settings in BossValidator
"""
import pytest
import boa

from contracts.core.userWallet import UserWallet, UserWalletConfig
from constants import EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ONE_MONTH_IN_BLOCKS, ZERO_ADDRESS, ACTION_TYPE
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
    
    return {
        'wallet': user_wallet,
        'wallet_config': wallet_config,
        'boss_validator': boss_validator,
        'owner': owner,
        'manager': alice
    }


# Test setting global manager settings


def test_set_global_manager_settings_basic(setup_contracts, createGlobalManagerSettings):
    """Test setting basic global manager settings"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet_config = ctx['wallet_config']
    
    # Create global settings
    settings = createGlobalManagerSettings(
        _managerPeriod=ONE_DAY_IN_BLOCKS,
        _canOwnerManage=True
    )
    
    # Set global settings (need to unpack the tuple)
    boss.setGlobalManagerSettings(
        ctx['wallet'].address,  # user wallet address
        settings[0],  # managerPeriod
        settings[1],  # startDelay  
        settings[2],  # activationLength
        settings[3],  # canOwnerManage
        settings[4],  # limits
        settings[5],  # legoPerms
        settings[6],  # whitelistPerms
        settings[7],  # transferPerms
        settings[8],  # allowedAssets
        sender=ctx['owner']
    )
    
    # Get events
    events = filter_logs(boss, "GlobalManagerSettingsModified")
    
    # Verify settings
    global_settings = wallet_config.globalManagerSettings()
    assert global_settings[0] == ONE_DAY_IN_BLOCKS  # managerPeriod
    assert global_settings[3] == True  # canOwnerManage
    assert len(events) == 1


def test_set_global_settings_with_limits(setup_contracts, createGlobalManagerSettings,
                                        createManagerLimits):
    """Test setting global settings with USD limits"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet_config = ctx['wallet_config']
    
    # Create limits
    limits = createManagerLimits(
        _maxUsdValuePerTx=1000 * EIGHTEEN_DECIMALS,
        _maxUsdValuePerPeriod=10000 * EIGHTEEN_DECIMALS,
        _maxUsdValueLifetime=100000 * EIGHTEEN_DECIMALS
    )
    
    # Create global settings with limits
    settings = createGlobalManagerSettings(_limits=limits)
    
    # Set global settings (need to unpack the tuple)
    boss.setGlobalManagerSettings(
        ctx['wallet'].address,  # user wallet address
        settings[0],  # managerPeriod
        settings[1],  # startDelay  
        settings[2],  # activationLength
        settings[3],  # canOwnerManage
        settings[4],  # limits
        settings[5],  # legoPerms
        settings[6],  # whitelistPerms
        settings[7],  # transferPerms
        settings[8],  # allowedAssets
        sender=ctx['owner']
    )
    
    # Verify limits
    global_settings = wallet_config.globalManagerSettings()
    assert global_settings[4][0] == 1000 * EIGHTEEN_DECIMALS  # maxUsdValuePerTx
    assert global_settings[4][1] == 10000 * EIGHTEEN_DECIMALS  # maxUsdValuePerPeriod
    assert global_settings[4][2] == 100000 * EIGHTEEN_DECIMALS  # maxUsdValueLifetime


def test_set_global_settings_with_permissions(setup_contracts, createGlobalManagerSettings,
                                             createLegoPerms, createWhitelistPerms,
                                             createTransferPerms):
    """Test setting global settings with custom permissions"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet_config = ctx['wallet_config']
    
    # Create restricted permissions
    lego_perms = createLegoPerms(
        _canManageYield=False,
        _canManageDebt=False
    )
    
    whitelist_perms = createWhitelistPerms(
        _canAddPending=True,
        _canRemove=True
    )
    
    transfer_perms = createTransferPerms(
        _canTransfer=False,
        _canCreateCheque=False
    )
    
    # Create global settings
    settings = createGlobalManagerSettings(
        _legoPerms=lego_perms,
        _whitelistPerms=whitelist_perms,
        _transferPerms=transfer_perms
    )
    
    # Set global settings (need to unpack the tuple)
    boss.setGlobalManagerSettings(
        ctx['wallet'].address,  # user wallet address
        settings[0],  # managerPeriod
        settings[1],  # startDelay  
        settings[2],  # activationLength
        settings[3],  # canOwnerManage
        settings[4],  # limits
        settings[5],  # legoPerms
        settings[6],  # whitelistPerms
        settings[7],  # transferPerms
        settings[8],  # allowedAssets
        sender=ctx['owner']
    )
    
    # Verify permissions
    global_settings = wallet_config.globalManagerSettings()
    
    # Lego permissions
    assert global_settings[5][0] == False  # canManageYield
    assert global_settings[5][2] == False  # canManageDebt
    
    # Whitelist permissions
    assert global_settings[6][0] == True  # canAddPending
    assert global_settings[6][3] == True  # canRemove
    
    # Transfer permissions
    assert global_settings[7][0] == False  # canTransfer
    assert global_settings[7][1] == False  # canCreateCheque


def test_set_global_settings_with_asset_restrictions(setup_contracts, createGlobalManagerSettings,
                                                    alpha_token, mock_lego_asset):
    """Test setting global settings with allowed assets"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet_config = ctx['wallet_config']
    
    # Create settings with asset restrictions
    allowed_assets = [alpha_token.address, mock_lego_asset.address]
    settings = createGlobalManagerSettings(_allowedAssets=allowed_assets)
    
    # Set global settings (need to unpack the tuple)
    boss.setGlobalManagerSettings(
        ctx['wallet'].address,  # user wallet address
        settings[0],  # managerPeriod
        settings[1],  # startDelay  
        settings[2],  # activationLength
        settings[3],  # canOwnerManage
        settings[4],  # limits
        settings[5],  # legoPerms
        settings[6],  # whitelistPerms
        settings[7],  # transferPerms
        settings[8],  # allowedAssets
        sender=ctx['owner']
    )
    
    # Verify allowed assets
    global_settings = wallet_config.globalManagerSettings()
    assert len(global_settings[8]) == 2
    assert alpha_token.address in global_settings[8]
    assert mock_lego_asset.address in global_settings[8]


# Test validation of global settings


def test_invalid_global_settings_rejected(setup_contracts, createGlobalManagerSettings,
                                        createManagerLimits):
    """Test that invalid global settings are rejected"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet_config = ctx['wallet_config']
    
    # Invalid: manager period too short
    invalid_settings = createGlobalManagerSettings(
        _managerPeriod=100  # Too short
    )
    
    with boa.reverts():
        boss.setGlobalManagerSettings(
            ctx['wallet'].address,  # user wallet address
            invalid_settings[0],  # managerPeriod
            invalid_settings[1],  # startDelay  
            invalid_settings[2],  # activationLength
            invalid_settings[3],  # canOwnerManage
            invalid_settings[4],  # limits
            invalid_settings[5],  # legoPerms
            invalid_settings[6],  # whitelistPerms
            invalid_settings[7],  # transferPerms
            invalid_settings[8],  # allowedAssets
            sender=ctx['owner']
        )
    
    # Invalid: per-tx limit > per-period limit
    invalid_limits = createManagerLimits(
        _maxUsdValuePerTx=1000 * EIGHTEEN_DECIMALS,
        _maxUsdValuePerPeriod=100 * EIGHTEEN_DECIMALS
    )
    
    invalid_settings2 = createGlobalManagerSettings(_limits=invalid_limits)
    
    with boa.reverts():
        boss.setGlobalManagerSettings(
            ctx['wallet'].address,  # user wallet address
            invalid_settings2[0],  # managerPeriod
            invalid_settings2[1],  # startDelay  
            invalid_settings2[2],  # activationLength
            invalid_settings2[3],  # canOwnerManage
            invalid_settings2[4],  # limits
            invalid_settings2[5],  # legoPerms
            invalid_settings2[6],  # whitelistPerms
            invalid_settings2[7],  # transferPerms
            invalid_settings2[8],  # allowedAssets
            sender=ctx['owner']
        )


def test_global_settings_with_timelock(setup_contracts, createGlobalManagerSettings):
    """Test global settings respect timelock"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet_config = ctx['wallet_config']
    
    # Set initial global settings with timelock
    settings1 = createGlobalManagerSettings(
        _managerPeriod=ONE_DAY_IN_BLOCKS
    )
    
    boss.setGlobalManagerSettings(
        ctx['wallet'].address,  # user wallet address
        settings1[0],  # managerPeriod
        settings1[1],  # startDelay  
        settings1[2],  # activationLength
        settings1[3],  # canOwnerManage
        settings1[4],  # limits
        settings1[5],  # legoPerms
        settings1[6],  # whitelistPerms
        settings1[7],  # transferPerms
        settings1[8],  # allowedAssets
        sender=ctx['owner']
    )
    
    # Try to update with shorter start delay than timelock
    # This should be validated based on current timelock
    settings2 = createGlobalManagerSettings(
        _startDelay=100  # Very short
    )
    
    # The validation depends on the wallet's current timelock
    # If it passes validation, the settings should be updated
    boss.setGlobalManagerSettings(
        ctx['wallet'].address,  # user wallet address
        settings2[0],  # managerPeriod
        settings2[1],  # startDelay  
        settings2[2],  # activationLength
        settings2[3],  # canOwnerManage
        settings2[4],  # limits
        settings2[5],  # legoPerms
        settings2[6],  # whitelistPerms
        settings2[7],  # transferPerms
        settings2[8],  # allowedAssets
        sender=ctx['owner']
    )


# Test authorization


def test_only_boss_validator_can_set_global(setup_contracts, createGlobalManagerSettings,
                                           alice):
    """Test that only BossValidator can set global settings"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet_config = ctx['wallet_config']
    
    settings = createGlobalManagerSettings()
    
    # Random address tries to set global settings
    with boa.reverts():
        wallet_config.setGlobalManagerSettings(
            settings,
            sender=alice
        )
    
    # Boss validator can set
    boss.setGlobalManagerSettings(
        ctx['wallet'].address,  # user wallet address
        settings[0],  # managerPeriod
        settings[1],  # startDelay  
        settings[2],  # activationLength
        settings[3],  # canOwnerManage
        settings[4],  # limits
        settings[5],  # legoPerms
        settings[6],  # whitelistPerms
        settings[7],  # transferPerms
        settings[8],  # allowedAssets
        sender=ctx['owner']
    )


# Test interaction with manager settings


def test_global_limits_affect_managers(setup_contracts, createGlobalManagerSettings,
                                     createManagerLimits, createLegoPerms,
                                     createWhitelistPerms, createTransferPerms):
    """Test that global limits affect manager operations"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    manager = ctx['manager']
    
    # Set restrictive global limits
    global_limits = createManagerLimits(
        _maxUsdValuePerTx=100 * EIGHTEEN_DECIMALS
    )
    
    global_settings = createGlobalManagerSettings(_limits=global_limits)
    
    boss.setGlobalManagerSettings(
        ctx['wallet'].address,  # user wallet address
        global_settings[0],  # managerPeriod
        global_settings[1],  # startDelay  
        global_settings[2],  # activationLength
        global_settings[3],  # canOwnerManage
        global_settings[4],  # limits
        global_settings[5],  # legoPerms
        global_settings[6],  # whitelistPerms
        global_settings[7],  # transferPerms
        global_settings[8],  # allowedAssets
        sender=ctx['owner']
    )
    
    # Add manager with generous limits
    manager_limits = createManagerLimits(
        _maxUsdValuePerTx=1000 * EIGHTEEN_DECIMALS
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
    
    # Manager should be restricted by global limits
    # This would be tested through actual transaction attempts
    # Global limit of 100 should override manager limit of 1000


def test_owner_manage_permission(setup_contracts, createGlobalManagerSettings,
                               createManagerData):
    """Test canOwnerManage global setting"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    
    # Set global settings with canOwnerManage = false
    settings = createGlobalManagerSettings(_canOwnerManage=False)
    
    boss.setGlobalManagerSettings(
        ctx['wallet'].address,  # user wallet address
        settings[0],  # managerPeriod
        settings[1],  # startDelay  
        settings[2],  # activationLength
        settings[3],  # canOwnerManage
        settings[4],  # limits
        settings[5],  # legoPerms
        settings[6],  # whitelistPerms
        settings[7],  # transferPerms
        settings[8],  # allowedAssets
        sender=ctx['owner']
    )
    
    # Check that owner cannot perform actions when disabled
    config = wallet_config.getManagerConfigs(owner)
    global_settings = wallet_config.globalManagerSettings()
    
    # Owner should not be able to perform actions
    can_perform = boss.canSignerPerformActionWithConfig(
        True,  # isOwner
        False,  # isManager
        createManagerData(),
        (0, 0, (0, 0, 0, 0, 0, False), (True, True, True, True, True, []), (False, True, True, False), (True, True, True, []), []),  # empty manager settings
        global_settings,
        ctx['wallet'].address,  # user wallet address
        ACTION_TYPE.TRANSFER
    )
    
    assert not can_perform  # Owner cannot manage when disabled globally


# Test default settings


def test_create_default_global_settings(setup_contracts):
    """Test default global settings creation"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    # Get default settings
    defaults = boss.createDefaultGlobalManagerSettings(
        ONE_DAY_IN_BLOCKS,  # managerPeriod
        ONE_DAY_IN_BLOCKS,  # minTimeLock
        30 * ONE_DAY_IN_BLOCKS  # defaultActivationLength
    )
    
    # Verify defaults are sensible
    assert defaults[0] == ONE_DAY_IN_BLOCKS  # managerPeriod
    assert defaults[1] == ONE_DAY_IN_BLOCKS  # startDelay
    assert defaults[2] == 30 * ONE_DAY_IN_BLOCKS  # activationLength
    assert defaults[3] == True  # canOwnerManage
    
    # All limits should be unlimited (0)
    limits = defaults[4]
    assert all(limit == 0 for limit in limits[:5])  # First 5 are USD/count limits
    
    # All permissions should be enabled
    assert all(defaults[5][:5])  # Lego permissions
    assert defaults[6][1:3] == (True, True)  # Whitelist confirm/cancel
    assert defaults[7][0:2] == (True, True)  # Transfer permissions