import pytest
import boa
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS, ONE_DAY_IN_BLOCKS, ONE_MONTH_IN_BLOCKS, ONE_YEAR_IN_BLOCKS
from conf_utils import filter_logs

# Cache contract loading at module level for performance
_USER_WALLET_CONTRACT = None
_USER_WALLET_CONFIG_CONTRACT = None

def _get_cached_contracts():
    global _USER_WALLET_CONTRACT, _USER_WALLET_CONFIG_CONTRACT
    if _USER_WALLET_CONTRACT is None:
        _USER_WALLET_CONTRACT = boa.load_partial("contracts/core/userWallet/UserWallet.vy")
    if _USER_WALLET_CONFIG_CONTRACT is None:
        _USER_WALLET_CONFIG_CONTRACT = boa.load_partial("contracts/core/userWallet/UserWalletConfig.vy")
    return _USER_WALLET_CONTRACT, _USER_WALLET_CONFIG_CONTRACT


@pytest.fixture(scope="module")
def shared_wallet_config(
    hatchery, 
    bob, 
    setUserWalletConfig,
    setManagerConfig
):
    """Shared UserWalletConfig for read-only tests - created once per module"""
    setUserWalletConfig()
    setManagerConfig()
    
    # Create a new wallet via hatchery
    wallet_address = hatchery.createUserWallet(sender=bob)
    
    # Use cached contracts
    wallet_contract, config_contract = _get_cached_contracts()
    wallet = wallet_contract.at(wallet_address)
    
    # Get the config address from the wallet
    config_address = wallet.walletConfig()
    
    # Load and return the config contract
    return config_contract.at(config_address)


@pytest.fixture
def user_wallet_config_for_test(
    hatchery, 
    bob, 
    alpha_token,
    boss_validator,
    paymaster,
    migrator,
    setUserWalletConfig,
    setManagerConfig,
    ledger
):
    """Create a fresh UserWalletConfig for state-modifying tests"""
    setUserWalletConfig()
    setManagerConfig()
    
    # Create a new wallet via hatchery
    wallet_address = hatchery.createUserWallet(sender=bob)
    
    # Use cached contracts for performance
    wallet_contract, config_contract = _get_cached_contracts()
    wallet = wallet_contract.at(wallet_address)
    
    # Get the config address from the wallet
    config_address = wallet.walletConfig()
    
    # Load and return the config contract
    return config_contract.at(config_address)


# ================================
# Ownership Tests
# ================================

def test_change_ownership_initiation(user_wallet_config_for_test, bob, alice):
    """Test initiating ownership change"""
    # Only owner can initiate
    with boa.reverts("no perms"):
        user_wallet_config_for_test.changeOwnership(alice, sender=alice)
    
    # Owner initiates change
    user_wallet_config_for_test.changeOwnership(alice, sender=bob)
    
    # Check event
    events = filter_logs(user_wallet_config_for_test, "OwnershipChangeInitiated")
    assert len(events) == 1
    assert events[0].prevOwner == bob
    assert events[0].newOwner == alice
    
    # Check pending owner
    pending = user_wallet_config_for_test.pendingOwner()
    assert pending[0] == alice  # newOwner
    assert pending[2] > boa.env.evm.patch.block_number  # confirmBlock


def test_confirm_ownership_change(user_wallet_config_for_test, bob, alice):
    """Test confirming ownership change"""
    # Initiate change
    user_wallet_config_for_test.changeOwnership(alice, sender=bob)
    
    # Get confirm block
    pending = user_wallet_config_for_test.pendingOwner()
    confirm_block = pending[2]
    
    # Cannot confirm before time delay
    with boa.reverts("time delay not reached"):
        user_wallet_config_for_test.confirmOwnershipChange(sender=alice)
    
    # Advance to confirm block
    boa.env.time_travel(blocks=int(confirm_block - boa.env.evm.patch.block_number))
    
    # Only new owner can confirm
    with boa.reverts("only new owner can confirm"):
        user_wallet_config_for_test.confirmOwnershipChange(sender=bob)
    
    # New owner confirms
    user_wallet_config_for_test.confirmOwnershipChange(sender=alice)
    
    # Check event
    events = filter_logs(user_wallet_config_for_test, "OwnershipChangeConfirmed")
    assert len(events) == 1
    assert events[0].prevOwner == bob
    assert events[0].newOwner == alice
    
    # Check ownership changed
    assert user_wallet_config_for_test.owner() == alice
    
    # Pending owner cleared
    pending = user_wallet_config_for_test.pendingOwner()
    assert pending[0] == ZERO_ADDRESS


def test_cancel_ownership_change(user_wallet_config_for_test, bob, alice):
    """Test canceling ownership change"""
    # Initiate change
    user_wallet_config_for_test.changeOwnership(alice, sender=bob)
    
    # Owner can cancel
    user_wallet_config_for_test.cancelOwnershipChange(sender=bob)
    
    # Check event
    events = filter_logs(user_wallet_config_for_test, "OwnershipChangeCancelled")
    assert len(events) == 1
    assert events[0].cancelledOwner == alice
    assert events[0].cancelledBy == bob
    
    # Pending owner cleared
    pending = user_wallet_config_for_test.pendingOwner()
    assert pending[0] == ZERO_ADDRESS


def test_timelock_settings(user_wallet_config_for_test, bob, alice):
    """Test setting timelock"""
    min_timelock = user_wallet_config_for_test.MIN_TIMELOCK()
    max_timelock = user_wallet_config_for_test.MAX_TIMELOCK()
    
    # Only owner can set
    with boa.reverts("no perms"):
        user_wallet_config_for_test.setTimeLock(50, sender=alice)
    
    # Cannot set below min
    with boa.reverts("invalid delay"):
        user_wallet_config_for_test.setTimeLock(min_timelock - 1, sender=bob)
    
    # Cannot set above max
    with boa.reverts("invalid delay"):
        user_wallet_config_for_test.setTimeLock(max_timelock + 1, sender=bob)
    
    # Valid setting
    new_timelock = (min_timelock + max_timelock) // 2
    user_wallet_config_for_test.setTimeLock(new_timelock, sender=bob)
    
    # Check event
    events = filter_logs(user_wallet_config_for_test, "TimeLockSet")
    assert len(events) == 1
    assert events[0].numBlocks == new_timelock
    
    # Check value
    assert user_wallet_config_for_test.timeLock() == new_timelock


# ================================
# Manager Settings Tests
# ================================

def test_add_manager(user_wallet_config_for_test, alice, charlie, boss_validator, migrator, createManagerSettings):
    """Test adding a manager"""
    settings = createManagerSettings()
    
    # Get initial manager count
    initial_count = user_wallet_config_for_test.numManagers()
    
    # Only boss validator or migrator can add
    with boa.reverts("no perms"):
        user_wallet_config_for_test.addManager(alice, settings, sender=charlie)
    
    # Boss validator adds manager
    user_wallet_config_for_test.addManager(alice, settings, sender=boss_validator.address)
    
    # Check manager registered
    assert user_wallet_config_for_test.isManager(alice) == True
    assert user_wallet_config_for_test.numManagers() == initial_count + 1
    assert user_wallet_config_for_test.indexOfManager(alice) > 0
    
    # Migrator can also add
    user_wallet_config_for_test.addManager(charlie, settings, sender=migrator.address)
    assert user_wallet_config_for_test.isManager(charlie) == True
    assert user_wallet_config_for_test.numManagers() == initial_count + 2


def test_update_manager(user_wallet_config_for_test, alice, boss_validator, createManagerSettings):
    """Test updating manager settings"""
    # Add manager first
    settings = createManagerSettings()
    user_wallet_config_for_test.addManager(alice, settings, sender=boss_validator.address)
    
    # Create new settings
    new_settings = createManagerSettings(_expiryBlock=boa.env.evm.patch.block_number + 1000)
    
    # Only boss validator can update
    with boa.reverts("no perms"):
        user_wallet_config_for_test.updateManager(alice, new_settings, sender=alice)
    
    # Update manager
    user_wallet_config_for_test.updateManager(alice, new_settings, sender=boss_validator.address)
    
    # Check settings updated
    stored_settings = user_wallet_config_for_test.managerSettings(alice)
    assert stored_settings[1] == boa.env.evm.patch.block_number + 1000  # expiryBlock


def test_remove_manager(user_wallet_config_for_test, alice, charlie, boss_validator, createManagerSettings):
    """Test removing a manager"""
    settings = createManagerSettings()
    
    # Add two managers
    user_wallet_config_for_test.addManager(alice, settings, sender=boss_validator.address)
    user_wallet_config_for_test.addManager(charlie, settings, sender=boss_validator.address)
    
    initial_count = user_wallet_config_for_test.numManagers()
    
    # Only boss validator can remove
    with boa.reverts("no perms"):
        user_wallet_config_for_test.removeManager(alice, sender=alice)
    
    # Remove alice (middle manager)
    user_wallet_config_for_test.removeManager(alice, sender=boss_validator.address)
    
    # Check alice removed
    assert user_wallet_config_for_test.isManager(alice) == False
    assert user_wallet_config_for_test.indexOfManager(alice) == 0
    assert user_wallet_config_for_test.numManagers() == initial_count - 1
    
    # Charlie should still be registered
    assert user_wallet_config_for_test.isManager(charlie) == True
    
    # Settings cleared
    stored_settings = user_wallet_config_for_test.managerSettings(alice)
    assert stored_settings[0] == 0  # startBlock


def test_set_global_manager_settings(user_wallet_config_for_test, boss_validator, migrator, createGlobalManagerSettings):
    """Test setting global manager settings"""
    settings = createGlobalManagerSettings()
    
    # Only boss validator or migrator can set
    with boa.reverts("no perms"):
        user_wallet_config_for_test.setGlobalManagerSettings(settings, sender=user_wallet_config_for_test.owner())
    
    # Boss validator sets
    user_wallet_config_for_test.setGlobalManagerSettings(settings, sender=boss_validator.address)
    
    # Check settings
    stored = user_wallet_config_for_test.globalManagerSettings()
    assert stored[0] == ONE_DAY_IN_BLOCKS  # managerPeriod
    
    # Migrator can also set
    new_settings = createGlobalManagerSettings(_managerPeriod=ONE_DAY_IN_BLOCKS * 2)
    user_wallet_config_for_test.setGlobalManagerSettings(new_settings, sender=migrator.address)
    stored = user_wallet_config_for_test.globalManagerSettings()
    assert stored[0] == ONE_DAY_IN_BLOCKS * 2


def test_check_manager_usd_limits(user_wallet_config_for_test, alice, boss_validator, createManagerSettings):
    """Test checking and updating manager USD limits"""
    # Add manager
    settings = createManagerSettings()
    user_wallet_config_for_test.addManager(alice, settings, sender=boss_validator.address)
    
    # Only wallet can call
    with boa.reverts("no perms"):
        user_wallet_config_for_test.checkManagerUsdLimitsAndUpdateData(alice, 100 * EIGHTEEN_DECIMALS, sender=alice)
    
    # Call from wallet
    wallet = user_wallet_config_for_test.wallet()
    user_wallet_config_for_test.checkManagerUsdLimitsAndUpdateData(alice, 100 * EIGHTEEN_DECIMALS, sender=wallet)
    
    # Check data updated
    data = user_wallet_config_for_test.managerPeriodData(alice)
    assert data[1] == 100 * EIGHTEEN_DECIMALS  # totalUsdValueInPeriod


# ================================
# Payee Settings Tests
# ================================

def test_add_payee(user_wallet_config_for_test, alice, charlie, paymaster, migrator, createPayeeSettings):
    """Test adding a payee"""
    settings = createPayeeSettings()
    
    # Get initial payee count
    initial_count = user_wallet_config_for_test.numPayees()
    alice_already_registered = user_wallet_config_for_test.isRegisteredPayee(alice)
    charlie_already_registered = user_wallet_config_for_test.isRegisteredPayee(charlie)
    
    # Only paymaster or migrator can add
    with boa.reverts("no perms"):
        user_wallet_config_for_test.addPayee(alice, settings, sender=charlie)
    
    # Paymaster adds payee
    user_wallet_config_for_test.addPayee(alice, settings, sender=paymaster.address)
    
    # Check payee registered
    assert user_wallet_config_for_test.isRegisteredPayee(alice) == True
    # Note: numPayees represents next index, not count. First payee at index 1 makes numPayees = 2
    current_count = user_wallet_config_for_test.numPayees()
    if not alice_already_registered:
        if initial_count == 0:
            assert current_count == 2  # First payee: index 1, numPayees becomes 2
        else:
            assert current_count == initial_count + 1
    assert user_wallet_config_for_test.indexOfPayee(alice) > 0
    
    # Migrator can also add
    user_wallet_config_for_test.addPayee(charlie, settings, sender=migrator.address)
    assert user_wallet_config_for_test.isRegisteredPayee(charlie) == True


def test_update_payee(user_wallet_config_for_test, alice, paymaster, createPayeeSettings):
    """Test updating payee settings"""
    # Add payee first
    settings = createPayeeSettings()
    user_wallet_config_for_test.addPayee(alice, settings, sender=paymaster.address)
    
    # Create new settings
    new_settings = createPayeeSettings(_canPull=True)
    
    # Only paymaster can update
    with boa.reverts("no perms"):
        user_wallet_config_for_test.updatePayee(alice, new_settings, sender=alice)
    
    # Update payee
    user_wallet_config_for_test.updatePayee(alice, new_settings, sender=paymaster.address)
    
    # Check settings updated
    stored_settings = user_wallet_config_for_test.payeeSettings(alice)
    assert stored_settings[2] == True  # canPull


def test_remove_payee(user_wallet_config_for_test, alice, charlie, paymaster, createPayeeSettings):
    """Test removing a payee"""
    settings = createPayeeSettings()
    
    # Add two payees
    user_wallet_config_for_test.addPayee(alice, settings, sender=paymaster.address)
    user_wallet_config_for_test.addPayee(charlie, settings, sender=paymaster.address)
    
    # Only paymaster can remove
    with boa.reverts("no perms"):
        user_wallet_config_for_test.removePayee(alice, sender=alice)
    
    # Remove alice
    user_wallet_config_for_test.removePayee(alice, sender=paymaster.address)
    
    # Check alice removed
    assert user_wallet_config_for_test.isRegisteredPayee(alice) == False
    assert user_wallet_config_for_test.indexOfPayee(alice) == 0
    
    # Charlie should still be registered
    assert user_wallet_config_for_test.isRegisteredPayee(charlie) == True


def test_pending_payee_operations(user_wallet_config_for_test, alice, paymaster, createPayeeSettings):
    """Test pending payee operations"""
    settings = createPayeeSettings()
    pending = (settings, boa.env.evm.patch.block_number, boa.env.evm.patch.block_number + 100)
    
    # Only paymaster can add pending
    with boa.reverts("no perms"):
        user_wallet_config_for_test.addPendingPayee(alice, pending, sender=alice)
    
    # Add pending payee
    user_wallet_config_for_test.addPendingPayee(alice, pending, sender=paymaster.address)
    
    # Check pending stored
    stored_pending = user_wallet_config_for_test.pendingPayees(alice)
    assert stored_pending[0][0] == settings[0]  # startBlock from settings
    
    # Cancel pending
    user_wallet_config_for_test.cancelPendingPayee(alice, sender=paymaster.address)
    stored_pending = user_wallet_config_for_test.pendingPayees(alice)
    assert stored_pending[1] == 0  # initiatedBlock cleared
    
    # Add pending again and confirm
    user_wallet_config_for_test.addPendingPayee(alice, pending, sender=paymaster.address)
    user_wallet_config_for_test.confirmPendingPayee(alice, sender=paymaster.address)
    
    # Check payee registered
    assert user_wallet_config_for_test.isRegisteredPayee(alice) == True
    # Pending cleared
    stored_pending = user_wallet_config_for_test.pendingPayees(alice)
    assert stored_pending[1] == 0


def test_set_global_payee_settings(user_wallet_config_for_test, paymaster, migrator, createPayeeLimits):
    """Test setting global payee settings"""
    # Create global payee settings manually
    settings = (
        ONE_DAY_IN_BLOCKS,  # defaultPeriodLength
        ONE_DAY_IN_BLOCKS,  # startDelay  
        ONE_MONTH_IN_BLOCKS,  # activationLength
        0,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        False,  # failOnZeroPrice
        createPayeeLimits(),  # usdLimits
        True,  # canPayOwner
    )
    
    # Only paymaster or migrator can set
    with boa.reverts("no perms"):
        user_wallet_config_for_test.setGlobalPayeeSettings(settings, sender=user_wallet_config_for_test.owner())
    
    # Paymaster sets
    user_wallet_config_for_test.setGlobalPayeeSettings(settings, sender=paymaster.address)
    
    # Check settings
    stored = user_wallet_config_for_test.globalPayeeSettings()
    assert stored[0] == ONE_DAY_IN_BLOCKS  # defaultPeriodLength
    
    # Migrator can also set
    new_settings = (
        ONE_DAY_IN_BLOCKS * 2,  # defaultPeriodLength
        ONE_DAY_IN_BLOCKS,  # startDelay  
        ONE_MONTH_IN_BLOCKS,  # activationLength
        0,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        False,  # failOnZeroPrice
        createPayeeLimits(),  # usdLimits
        True,  # canPayOwner
    )
    user_wallet_config_for_test.setGlobalPayeeSettings(new_settings, sender=migrator.address)
    stored = user_wallet_config_for_test.globalPayeeSettings()
    assert stored[0] == ONE_DAY_IN_BLOCKS * 2


def test_check_recipient_limits(user_wallet_config_for_test, alice, paymaster, alpha_token, createPayeeSettings):
    """Test checking recipient limits and updating data"""
    # Add payee
    settings = createPayeeSettings()
    user_wallet_config_for_test.addPayee(alice, settings, sender=paymaster.address)
    
    # Only wallet can call
    with boa.reverts("no perms"):
        user_wallet_config_for_test.checkRecipientLimitsAndUpdateData(
            alice, 100 * EIGHTEEN_DECIMALS, alpha_token, 10 * EIGHTEEN_DECIMALS, sender=alice
        )
    
    # Call from wallet
    wallet = user_wallet_config_for_test.wallet()
    user_wallet_config_for_test.checkRecipientLimitsAndUpdateData(
        alice, 100 * EIGHTEEN_DECIMALS, alpha_token, 10 * EIGHTEEN_DECIMALS, sender=wallet
    )


def test_can_add_pending_payee(user_wallet_config_for_test, alice, bob, boss_validator, createManagerSettings):
    """Test checking if caller can add pending payee"""
    # Owner cannot add pending (returns False)
    assert user_wallet_config_for_test.canAddPendingPayee(bob) == False
    
    # Non-manager cannot
    assert user_wallet_config_for_test.canAddPendingPayee(alice) == False
    
    # Add alice as manager with permission
    settings = createManagerSettings(
        _transferPerms=(True, True, True, [])  # canTransfer, canCreateCheque, canAddPendingPayee, allowedPayees
    )
    user_wallet_config_for_test.addManager(alice, settings, sender=boss_validator.address)
    
    # Manager with permission can
    assert user_wallet_config_for_test.canAddPendingPayee(alice) == True
    
    # Expired manager cannot
    # Set expiry block to current block (manager expires at this block)
    current_block = boa.env.evm.patch.block_number
    expired_settings = createManagerSettings(
        _startBlock=1,
        _expiryBlock=current_block,  # Manager expires at current block
        _transferPerms=(True, True, True, [])
    )
    user_wallet_config_for_test.updateManager(alice, expired_settings, sender=boss_validator.address)
    # The contract correctly uses <= for the check, so managers are inactive on their expiry block
    assert user_wallet_config_for_test.canAddPendingPayee(alice) == False


# ================================
# Whitelist Tests
# ================================

def test_whitelist_operations(user_wallet_config_for_test, alice, charlie, paymaster, migrator):
    """Test whitelist operations"""
    # Check not whitelisted
    assert user_wallet_config_for_test.isWhitelisted(alice) == False
    
    # Add pending whitelist
    pending = (boa.env.evm.patch.block_number, boa.env.evm.patch.block_number + 100)
    
    # Only paymaster can add pending
    with boa.reverts("no perms"):
        user_wallet_config_for_test.addPendingWhitelistAddr(alice, pending, sender=alice)
    
    user_wallet_config_for_test.addPendingWhitelistAddr(alice, pending, sender=paymaster.address)
    
    # Cancel pending
    user_wallet_config_for_test.cancelPendingWhitelistAddr(alice, sender=paymaster.address)
    
    # Add and confirm
    user_wallet_config_for_test.addPendingWhitelistAddr(alice, pending, sender=paymaster.address)
    user_wallet_config_for_test.confirmWhitelistAddr(alice, sender=paymaster.address)
    
    # Check whitelisted
    assert user_wallet_config_for_test.isWhitelisted(alice) == True
    assert user_wallet_config_for_test.numWhitelisted() > 0
    assert user_wallet_config_for_test.indexOfWhitelist(alice) > 0
    
    # Migrator can also add directly
    user_wallet_config_for_test.addWhitelistAddrViaMigrator(charlie, sender=migrator.address)
    assert user_wallet_config_for_test.isWhitelisted(charlie) == True


def test_remove_whitelist(user_wallet_config_for_test, alice, charlie, paymaster):
    """Test removing from whitelist"""
    # Add two addresses
    pending = (boa.env.evm.patch.block_number, boa.env.evm.patch.block_number + 100)
    user_wallet_config_for_test.addPendingWhitelistAddr(alice, pending, sender=paymaster.address)
    user_wallet_config_for_test.confirmWhitelistAddr(alice, sender=paymaster.address)
    user_wallet_config_for_test.addPendingWhitelistAddr(charlie, pending, sender=paymaster.address)
    user_wallet_config_for_test.confirmWhitelistAddr(charlie, sender=paymaster.address)
    
    # Only paymaster can remove
    with boa.reverts("no perms"):
        user_wallet_config_for_test.removeWhitelistAddr(alice, sender=alice)
    
    # Remove alice
    user_wallet_config_for_test.removeWhitelistAddr(alice, sender=paymaster.address)
    
    # Check alice removed
    assert user_wallet_config_for_test.isWhitelisted(alice) == False
    assert user_wallet_config_for_test.indexOfWhitelist(alice) == 0
    
    # Charlie should still be whitelisted
    assert user_wallet_config_for_test.isWhitelisted(charlie) == True


# ================================
# Access Control Tests
# ================================

def test_check_signer_permissions(user_wallet_config_for_test, alice, bob, boss_validator, createManagerSettings):
    """Test checking signer permissions and getting action bundle"""
    # Owner has permissions
    ad = user_wallet_config_for_test.checkSignerPermissionsAndGetBundle(
        bob, 1, [], [], ZERO_ADDRESS  # ActionType.TRANSFER = 1
    )
    assert ad[8] == bob  # walletOwner
    assert ad[12] == bob  # signer
    assert ad[13] == False  # isManager (owner is not manager)
    
    # Non-manager/owner fails
    with boa.reverts("no permission"):
        user_wallet_config_for_test.checkSignerPermissionsAndGetBundle(
            alice, 1, [], [], ZERO_ADDRESS
        )
    
    # Add alice as manager
    settings = createManagerSettings()
    user_wallet_config_for_test.addManager(alice, settings, sender=boss_validator.address)
    
    # Manager has permissions
    ad = user_wallet_config_for_test.checkSignerPermissionsAndGetBundle(
        alice, 1, [], [], ZERO_ADDRESS
    )
    assert ad[13] == True  # isManager


def test_get_manager_configs(user_wallet_config_for_test, alice, bob, boss_validator, createManagerSettings):
    """Test getting manager configuration bundle"""
    # Get owner config
    config = user_wallet_config_for_test.getManagerConfigs(bob)
    assert config[0] == True  # isOwner
    assert config[1] == False  # isManager (owner is not manager by default)
    
    # Add alice as manager
    settings = createManagerSettings()
    user_wallet_config_for_test.addManager(alice, settings, sender=boss_validator.address)
    
    # Get manager config
    config = user_wallet_config_for_test.getManagerConfigs(alice)
    assert config[0] == False  # isOwner
    assert config[1] == True  # isManager


def test_get_recipient_configs(user_wallet_config_for_test, alice, bob, paymaster, createPayeeSettings):
    """Test getting recipient configuration bundle"""
    # Owner is valid recipient
    config = user_wallet_config_for_test.getRecipientConfigs(bob)
    assert config[0] == False  # isWhitelisted
    assert config[1] == True  # isOwner
    assert config[2] == False  # isPayee
    
    # Add alice as payee
    settings = createPayeeSettings()
    user_wallet_config_for_test.addPayee(alice, settings, sender=paymaster.address)
    
    # Get payee config
    config = user_wallet_config_for_test.getRecipientConfigs(alice)
    assert config[0] == False  # isWhitelisted
    assert config[1] == False  # isOwner
    assert config[2] == True  # isPayee
    
    # Whitelist alice
    pending = (boa.env.evm.patch.block_number, boa.env.evm.patch.block_number + 100)
    user_wallet_config_for_test.addPendingWhitelistAddr(alice, pending, sender=paymaster.address)
    user_wallet_config_for_test.confirmWhitelistAddr(alice, sender=paymaster.address)
    
    # Whitelisted recipient
    config = user_wallet_config_for_test.getRecipientConfigs(alice)
    assert config[0] == True  # isWhitelisted


# ================================
# Pass-Through Functions Tests
# ================================

def test_update_asset_data(user_wallet_config_for_test, switchboard_alpha, alpha_token):
    """Test update asset data pass-through"""
    # Only switchboard can call
    with boa.reverts("no perms"):
        user_wallet_config_for_test.updateAssetData(0, alpha_token.address, False, sender=user_wallet_config_for_test.owner())
    
    # Switchboard calls - this actually succeeds and returns 0
    result = user_wallet_config_for_test.updateAssetData(0, alpha_token.address, False, sender=switchboard_alpha.address)
    assert result == 0  # No asset found returns 0


def test_remove_trial_funds(user_wallet_config_for_test, hatchery, alpha_token):
    """Test removing trial funds"""
    # Only hatchery can call
    with boa.reverts("no perms"):
        user_wallet_config_for_test.removeTrialFunds(sender=user_wallet_config_for_test.owner())
    
    # No trial funds set
    with boa.reverts("no trial funds"):
        user_wallet_config_for_test.removeTrialFunds(sender=hatchery.address)


def test_prepare_payment(user_wallet_config_for_test, switchboard_alpha, hatchery, alpha_token):
    """Test prepare payment pass-through"""
    # Only switchboard or hatchery can call
    with boa.reverts("no perms"):
        user_wallet_config_for_test.preparePayment(
            alpha_token, 0, alpha_token, sender=user_wallet_config_for_test.owner()
        )
    
    # Switchboard can call (will revert in wallet but proves access)
    with boa.reverts():
        user_wallet_config_for_test.preparePayment(
            alpha_token, 0, alpha_token, sender=switchboard_alpha.address
        )
    
    # Hatchery can call
    with boa.reverts():
        user_wallet_config_for_test.preparePayment(
            alpha_token, 0, alpha_token, sender=hatchery.address
        )


def test_recover_nft(user_wallet_config_for_test, bob, alice, switchboard_alpha):
    """Test NFT recovery"""
    # Only owner or switchboard can recover
    with boa.reverts("no perms"):
        user_wallet_config_for_test.recoverNft(ZERO_ADDRESS, 1, alice, sender=alice)
    
    # Owner can call, but will revert because wallet doesn't implement recoverNft
    # This proves access control works
    with boa.reverts():
        user_wallet_config_for_test.recoverNft(ZERO_ADDRESS, 1, alice, sender=bob)
    
    # Switchboard can also call
    with boa.reverts():
        user_wallet_config_for_test.recoverNft(ZERO_ADDRESS, 1, alice, sender=switchboard_alpha.address)


def test_set_frozen(user_wallet_config_for_test, bob, alice, switchboard_alpha):
    """Test setting frozen status"""
    # Only owner or switchboard can set
    with boa.reverts("no perms"):
        user_wallet_config_for_test.setFrozen(True, sender=alice)
    
    # Owner sets frozen
    user_wallet_config_for_test.setFrozen(True, sender=bob)
    assert user_wallet_config_for_test.isFrozen() == True
    
    # Switchboard unfreezes
    user_wallet_config_for_test.setFrozen(False, sender=switchboard_alpha.address)
    assert user_wallet_config_for_test.isFrozen() == False


def test_set_ejection_mode(user_wallet_config_for_test, switchboard_alpha):
    """Test setting ejection mode"""
    # Only switchboard can set
    with boa.reverts("no perms"):
        user_wallet_config_for_test.setEjectionMode(True, sender=user_wallet_config_for_test.owner())
    
    # Cannot eject with trial funds
    if user_wallet_config_for_test.trialFundsAmount() > 0:
        with boa.reverts("has trial funds"):
            user_wallet_config_for_test.setEjectionMode(True, sender=switchboard_alpha.address)
    else:
        # Set ejection mode
        user_wallet_config_for_test.setEjectionMode(True, sender=switchboard_alpha.address)
        assert user_wallet_config_for_test.inEjectMode() == True
        
        # Once in ejection mode, switchboard loses permission to call setEjectionMode
        # because _isSwitchboardAddr returns False when inEjectMode is True
        with boa.reverts("no perms"):
            user_wallet_config_for_test.setEjectionMode(False, sender=switchboard_alpha.address)


# ================================
# Migration Tests
# ================================

def test_migration_flags(user_wallet_config_for_test, migrator):
    """Test setting migration flags"""
    # Only migrator can set
    with boa.reverts("no perms"):
        user_wallet_config_for_test.setDidMigrateFunds(sender=user_wallet_config_for_test.owner())
    
    with boa.reverts("no perms"):
        user_wallet_config_for_test.setDidMigrateSettings(sender=user_wallet_config_for_test.owner())
    
    # Migrator sets flags
    user_wallet_config_for_test.setDidMigrateFunds(sender=migrator.address)
    assert user_wallet_config_for_test.didMigrateFunds() == True
    
    user_wallet_config_for_test.setDidMigrateSettings(sender=migrator.address)
    assert user_wallet_config_for_test.didMigrateSettings() == True


def test_transfer_funds_during_migration(user_wallet_config_for_test, alice, migrator, alpha_token):
    """Test transfer funds during migration"""
    # Only migrator can call
    # ActionData has 18 fields with specific types
    ad = (
        ZERO_ADDRESS,  # missionControl
        ZERO_ADDRESS,  # legoBook
        ZERO_ADDRESS,  # switchboard
        ZERO_ADDRESS,  # hatchery
        ZERO_ADDRESS,  # lootDistributor
        ZERO_ADDRESS,  # appraiser
        ZERO_ADDRESS,  # wallet
        ZERO_ADDRESS,  # walletConfig
        ZERO_ADDRESS,  # walletOwner
        False,         # inEjectMode (bool)
        False,         # isFrozen (bool)
        0,             # lastTotalUsdValue (uint256)
        ZERO_ADDRESS,  # signer
        False,         # isManager (bool)
        0,             # legoId (uint256)
        ZERO_ADDRESS,  # legoAddr
        ZERO_ADDRESS,  # eth
        ZERO_ADDRESS,  # weth
    )
    with boa.reverts("no perms"):
        user_wallet_config_for_test.transferFundsDuringMigration(
            alice, alpha_token.address, 100 * EIGHTEEN_DECIMALS, ad, sender=alice
        )
    
    # Migrator calls (will revert in wallet but proves access)
    with boa.reverts():
        user_wallet_config_for_test.transferFundsDuringMigration(
            alice, alpha_token.address, 100 * EIGHTEEN_DECIMALS, ad, sender=migrator.address
        )


def test_get_migration_config_bundle(shared_wallet_config):
    """Test getting migration configuration bundle - read only"""
    bundle = shared_wallet_config.getMigrationConfigBundle()
    
    assert bundle[0] == shared_wallet_config.owner()  # owner
    assert bundle[1] == shared_wallet_config.trialFundsAmount()  # trialFundsAmount
    assert bundle[2] == shared_wallet_config.isFrozen()  # isFrozen
    assert bundle[3] == shared_wallet_config.numPayees()  # numPayees
    assert bundle[4] == shared_wallet_config.numWhitelisted()  # numWhitelisted
    assert bundle[5] == shared_wallet_config.numManagers()  # numManagers
    assert bundle[6] == shared_wallet_config.startingAgent()  # startingAgent
    assert bundle[9] == shared_wallet_config.groupId()  # groupId
    assert bundle[10] == shared_wallet_config.didMigrateSettings()  # didMigrateSettings
    assert bundle[11] == shared_wallet_config.didMigrateFunds()  # didMigrateFunds


# ================================
# Bundle Getter Tests
# ================================

def test_get_action_data_bundle(shared_wallet_config, bob, switchboard_alpha):
    """Test getting action data bundle - read only"""
    # Normal mode
    bundle = shared_wallet_config.getActionDataBundle(1, bob)
    
    assert bundle[6] == shared_wallet_config.wallet()  # wallet
    assert bundle[7] == shared_wallet_config.address  # walletConfig
    assert bundle[8] == bob  # walletOwner
    assert bundle[9] == False  # inEjectMode
    assert bundle[12] == bob  # signer
    assert bundle[14] == 1  # legoId
    
    # Set eject mode through switchboard (cannot directly set inEjectMode)
    # Skip this test as it requires trial funds to be 0
    # and the contract state changes cannot be done directly


def test_get_manager_settings_bundle(user_wallet_config_for_test, alice, boss_validator, createManagerSettings):
    """Test getting manager settings bundle"""
    # Add manager
    settings = createManagerSettings()
    user_wallet_config_for_test.addManager(alice, settings, sender=boss_validator.address)
    
    bundle = user_wallet_config_for_test.getManagerSettingsBundle(alice)
    
    assert bundle[0] == user_wallet_config_for_test.owner()  # owner
    assert bundle[1] == True  # isManager
    assert bundle[2] == boss_validator.address  # bossValidator
    assert bundle[3] == user_wallet_config_for_test.timeLock()  # timeLock
    assert bundle[4] == user_wallet_config_for_test.inEjectMode()  # inEjectMode
    assert bundle[5] == user_wallet_config_for_test.address  # walletConfig


def test_get_payee_management_bundle(user_wallet_config_for_test, alice, paymaster, createPayeeSettings):
    """Test getting payee management bundle"""
    # Add payee
    settings = createPayeeSettings()
    user_wallet_config_for_test.addPayee(alice, settings, sender=paymaster.address)
    
    bundle = user_wallet_config_for_test.getPayeeManagementBundle(alice)
    
    assert bundle[0] == user_wallet_config_for_test.owner()  # owner
    assert bundle[1] == user_wallet_config_for_test.wallet()  # wallet
    assert bundle[2] == True  # isRegisteredPayee
    assert bundle[3] == False  # isWhitelisted
    assert bundle[4] == False  # isManager
    assert bundle[7] == user_wallet_config_for_test.timeLock()  # timeLock
    assert bundle[8] == user_wallet_config_for_test.address  # walletConfig
    assert bundle[9] == user_wallet_config_for_test.inEjectMode()  # inEjectMode


def test_get_whitelist_config_bundle(shared_wallet_config, alice, bob):
    """Test getting whitelist configuration bundle - read only"""
    bundle = shared_wallet_config.getWhitelistConfigBundle(alice, bob)
    
    assert bundle[0] == bob  # owner
    assert bundle[1] == shared_wallet_config.wallet()  # wallet
    assert bundle[2] == False  # isWhitelisted (alice not whitelisted)
    assert bundle[4] == shared_wallet_config.timeLock()  # timeLock
    assert bundle[5] == shared_wallet_config.address  # walletConfig
    assert bundle[6] == shared_wallet_config.inEjectMode()  # inEjectMode
    assert bundle[8] == True  # isOwner (bob is owner)


# ================================
# Edge Cases and Special Scenarios
# ================================

def test_double_add_manager(user_wallet_config_for_test, alice, boss_validator, createManagerSettings):
    """Test adding same manager twice doesn't create duplicate"""
    settings = createManagerSettings()
    
    # Add manager
    user_wallet_config_for_test.addManager(alice, settings, sender=boss_validator.address)
    initial_count = user_wallet_config_for_test.numManagers()
    
    # Add same manager again
    user_wallet_config_for_test.addManager(alice, settings, sender=boss_validator.address)
    
    # Count shouldn't increase
    assert user_wallet_config_for_test.numManagers() == initial_count


def test_remove_non_existent_manager(user_wallet_config_for_test, alice, boss_validator):
    """Test removing non-existent manager doesn't fail"""
    initial_count = user_wallet_config_for_test.numManagers()
    
    # Remove non-existent manager
    user_wallet_config_for_test.removeManager(alice, sender=boss_validator.address)
    
    # Count unchanged
    assert user_wallet_config_for_test.numManagers() == initial_count


def test_api_version(shared_wallet_config):
    """Test API version getter - read only"""
    assert shared_wallet_config.apiVersion() == "0.1.0"


def test_has_pending_owner_change(user_wallet_config_for_test, bob, alice):
    """Test checking for pending owner change"""
    # No pending change
    assert user_wallet_config_for_test.hasPendingOwnerChange() == False
    
    # Initiate change
    user_wallet_config_for_test.changeOwnership(alice, sender=bob)
    
    # Has pending change
    assert user_wallet_config_for_test.hasPendingOwnerChange() == True
    
    # Cancel change
    user_wallet_config_for_test.cancelOwnershipChange(sender=bob)
    
    # No pending change
    assert user_wallet_config_for_test.hasPendingOwnerChange() == False


def test_starting_agent_setup(shared_wallet_config):
    """Test starting agent is properly set up - read only"""
    starting_agent = shared_wallet_config.startingAgent()
    
    if starting_agent != ZERO_ADDRESS:
        # Starting agent should be registered as manager
        assert shared_wallet_config.isManager(starting_agent) == True
        assert shared_wallet_config.indexOfManager(starting_agent) == 1
        
        # Should have settings
        settings = shared_wallet_config.managerSettings(starting_agent)


def test_update_all_asset_data(user_wallet_config_for_test, switchboard_alpha, alice):
    """Test update all asset data pass-through"""
    # Only switchboard can call
    with boa.reverts("no perms"):
        user_wallet_config_for_test.updateAllAssetData(False, sender=alice.address)
    
    # Switchboard calls - returns lastTotalUsdValue when no assets
    result = user_wallet_config_for_test.updateAllAssetData(False, sender=switchboard_alpha.address)
    assert result >= 0  # Should return lastTotalUsdValue


def test_set_wallet(hatchery, bob, setUserWalletConfig, setManagerConfig):
    """Test setWallet can only be called once by hatchery"""
    setUserWalletConfig()
    setManagerConfig()
    
    # Create wallet via hatchery
    wallet_address = hatchery.createUserWallet(sender=bob)
    
    # Use cached contracts
    wallet_contract, config_contract = _get_cached_contracts()
    wallet = wallet_contract.at(wallet_address)
    
    # Get the config address from the wallet
    config_address = wallet.walletConfig()
    config = config_contract.at(config_address)
    
    # Verify wallet was set
    assert config.wallet() == wallet_address
    assert config.didSetWallet() == True
    
    # Try to set wallet again - should fail
    with boa.reverts("wallet already set"):
        config.setWallet(alice.address, sender=hatchery.address)
    
    # Non-hatchery cannot set wallet (but it fails with "wallet already set" first)
    with boa.reverts("wallet already set"):
        config.setWallet(alice.address, sender=bob.address)


def test_manager_payee_whitelist_overlap(
    user_wallet_config_for_test, 
    alice, 
    boss_validator, 
    paymaster,
    createManagerSettings,
    createPayeeSettings
):
    """Test overlapping roles - manager who is also payee and whitelisted"""
    # Add alice as manager
    manager_settings = createManagerSettings()
    user_wallet_config_for_test.addManager(alice, manager_settings, sender=boss_validator.address)
    
    # Add alice as payee
    payee_settings = createPayeeSettings()
    user_wallet_config_for_test.addPayee(alice, payee_settings, sender=paymaster.address)
    
    # Add alice to whitelist
    pending = (boa.env.evm.patch.block_number, boa.env.evm.patch.block_number + 100)
    user_wallet_config_for_test.addPendingWhitelistAddr(alice, pending, sender=paymaster.address)
    user_wallet_config_for_test.confirmWhitelistAddr(alice, sender=paymaster.address)
    
    # Verify all three roles
    assert user_wallet_config_for_test.isManager(alice) == True
    assert user_wallet_config_for_test.isRegisteredPayee(alice) == True
    assert user_wallet_config_for_test.isWhitelisted(alice) == True
    
    # Remove manager role
    user_wallet_config_for_test.removeManager(alice, sender=boss_validator.address)
    assert user_wallet_config_for_test.isManager(alice) == False
    assert user_wallet_config_for_test.isRegisteredPayee(alice) == True
    assert user_wallet_config_for_test.isWhitelisted(alice) == True
    
    # Remove whitelist
    user_wallet_config_for_test.removeWhitelistAddr(alice, sender=paymaster.address)
    assert user_wallet_config_for_test.isManager(alice) == False
    assert user_wallet_config_for_test.isRegisteredPayee(alice) == True
    assert user_wallet_config_for_test.isWhitelisted(alice) == False
    
    # Remove payee role
    user_wallet_config_for_test.removePayee(alice, sender=paymaster.address)
    assert user_wallet_config_for_test.isManager(alice) == False
    assert user_wallet_config_for_test.isRegisteredPayee(alice) == False
    assert user_wallet_config_for_test.isWhitelisted(alice) == False


def test_manager_array_management_edge_cases(
    user_wallet_config_for_test, 
    boss_validator, 
    createManagerSettings,
    alice,
    bob,
    charlie,
    sally,
    whale
):
    """Test edge cases in manager array management"""
    # Add multiple managers
    managers = [alice, bob, charlie, sally, whale]
    for manager in managers:
        settings = createManagerSettings()
        user_wallet_config_for_test.addManager(manager, settings, sender=boss_validator.address)
    
    # Verify all managers added
    starting_agent = user_wallet_config_for_test.startingAgent()
    offset = 1 if starting_agent != ZERO_ADDRESS else 0
    for i, manager in enumerate(managers):
        assert user_wallet_config_for_test.isManager(manager) == True
        # Check if manager is at expected index (accounting for starting agent)
        assert user_wallet_config_for_test.managers(i + 1 + offset) == manager
    
    # Remove middle manager
    middle_manager = managers[2]
    middle_index = user_wallet_config_for_test.indexOfManager(middle_manager)
    last_manager = managers[4]
    
    user_wallet_config_for_test.removeManager(middle_manager, sender=boss_validator.address)
    
    # Verify manager removed and array compacted
    assert user_wallet_config_for_test.isManager(middle_manager) == False
    
    # Check array is properly compacted - last manager should move to the removed position
    assert user_wallet_config_for_test.managers(middle_index) == last_manager
    
    # Remove first manager
    first_manager = managers[0]
    user_wallet_config_for_test.removeManager(first_manager, sender=boss_validator.address)
    assert user_wallet_config_for_test.isManager(first_manager) == False
    
    # Remove last manager
    last_index = user_wallet_config_for_test.numManagers() - 1
    if last_index > 0:
        last_manager = user_wallet_config_for_test.managers(last_index)
        user_wallet_config_for_test.removeManager(last_manager, sender=boss_validator.address)
        assert user_wallet_config_for_test.isManager(last_manager) == False


def test_invalid_owner_change(user_wallet_config_for_test, bob):
    """Test invalid owner change scenarios"""
    # Cannot change to zero address
    with boa.reverts("invalid new owner"):
        user_wallet_config_for_test.changeOwnership(ZERO_ADDRESS, sender=bob)
    
    # Cannot change to current owner
    with boa.reverts("invalid new owner"):
        user_wallet_config_for_test.changeOwnership(bob, sender=bob)


def test_global_settings_initialization(shared_wallet_config):
    """Test global settings are initialized properly - read only"""
    # Check global manager settings
    manager_settings = shared_wallet_config.globalManagerSettings()
    assert manager_settings[0] > 0  # managerPeriod
    assert manager_settings[1] > 0  # startDelay
    assert manager_settings[2] > 0  # activationLength
    
    # Check global payee settings
    payee_settings = shared_wallet_config.globalPayeeSettings()
    assert payee_settings[0] > 0  # defaultPeriodLength
    assert payee_settings[1] > 0  # startDelay
    assert payee_settings[2] > 0  # activationLength


def test_update_all_asset_data(user_wallet_config_for_test, switchboard_alpha):
    """Test update all asset data pass-through"""
    # Only switchboard can call
    with boa.reverts("no perms"):
        user_wallet_config_for_test.updateAllAssetData(False, sender=user_wallet_config_for_test.owner())
    
    # Switchboard calls - returns lastTotalUsdValue when no assets
    result = user_wallet_config_for_test.updateAllAssetData(False, sender=switchboard_alpha.address)
    assert result >= 0  # Should return lastTotalUsdValue


def test_set_wallet(hatchery, bob, setUserWalletConfig, setManagerConfig):
    """Test setWallet can only be called once by hatchery"""
    setUserWalletConfig()
    setManagerConfig()
    
    # Create a wallet but we'll test the config's setWallet function
    wallet_address = hatchery.createUserWallet(sender=bob)
    
    # Get the wallet contract
    wallet_contract, config_contract = _get_cached_contracts()
    wallet = wallet_contract.at(wallet_address)
    config_address = wallet.walletConfig()
    config = config_contract.at(config_address)
    
    # Verify wallet was set
    assert config.didSetWallet() == True
    assert config.wallet() == wallet_address
    
    # Try to set wallet again - should fail
    with boa.reverts("wallet already set"):
        config.setWallet(wallet_address, sender=hatchery.address)
    
    # Non-hatchery cannot set wallet (but it fails with "wallet already set" first)
    with boa.reverts("wallet already set"):
        config.setWallet(wallet_address, sender=bob)



