import pytest
import boa
from constants import ZERO_ADDRESS


@pytest.fixture
def pending_whitelist(user_wallet):
    """Create a pending whitelist struct"""
    return (
        boa.env.evm.patch.block_number,         # initiatedBlock
        boa.env.evm.patch.block_number + 100,  # confirmBlock
        user_wallet.address,                    # currentOwner
    )


@pytest.fixture
def pending_payee(createPayeeSettings, user_wallet):
    """Create a pending payee struct"""
    settings = createPayeeSettings()
    return (
        settings,                               # settings
        boa.env.evm.patch.block_number,        # initiatedBlock
        boa.env.evm.patch.block_number + 100,  # confirmBlock
        user_wallet.address,                    # currentOwner
    )


@pytest.fixture
def pending_payee(createPayeeSettings, user_wallet):
    """Create a pending payee struct"""
    settings = createPayeeSettings()
    return (
        settings,                               # settings
        boa.env.evm.patch.block_number,        # initiatedBlock
        boa.env.evm.patch.block_number + 100,  # confirmBlock
        user_wallet.address,                    # currentOwner
    )


##########################
# Whitelist Access Tests #
##########################


def test_add_pending_whitelist_access(user_wallet_config, alice, bob, pending_whitelist):
    """Only kernel should be able to add pending whitelist"""
    # Non-kernel address should fail
    with boa.reverts("no perms"):
        user_wallet_config.addPendingWhitelistAddr(alice, pending_whitelist, sender=bob)


def test_cancel_pending_whitelist_access(user_wallet_config, alice, bob):
    """Only kernel should be able to cancel pending whitelist"""
    # Non-kernel address should fail
    with boa.reverts("no perms"):
        user_wallet_config.cancelPendingWhitelistAddr(alice, sender=bob)


def test_confirm_whitelist_access(user_wallet_config, alice, bob):
    """Only kernel should be able to confirm whitelist"""
    # Non-kernel address should fail
    with boa.reverts("no perms"):
        user_wallet_config.confirmWhitelistAddr(alice, sender=bob)


def test_remove_whitelist_access(user_wallet_config, alice, bob):
    """Only kernel should be able to remove whitelist"""
    # Non-kernel address should fail
    with boa.reverts("no perms"):
        user_wallet_config.removeWhitelistAddr(alice, sender=bob)


def test_add_whitelist_via_migrator_access(user_wallet_config, alice, bob):
    """Only migrator should be able to add whitelist directly"""
    # Non-migrator address should fail
    with boa.reverts("no perms"):
        user_wallet_config.addWhitelistAddrViaMigrator(alice, sender=bob)


########################
# Manager Access Tests #
########################


def test_add_manager_access(user_wallet_config, alice, bob, createManagerSettings):
    """Only highCommand or migrator should be able to add manager"""
    settings = createManagerSettings()
    
    # Non-authorized address should fail
    with boa.reverts("no perms"):
        user_wallet_config.addManager(alice, settings, sender=bob)


def test_update_manager_access(user_wallet_config, alice, bob, createManagerSettings):
    """Only highCommand should be able to update manager"""
    settings = createManagerSettings()
    
    # Non-highCommand address should fail
    with boa.reverts("no perms"):
        user_wallet_config.updateManager(alice, settings, sender=bob)


def test_remove_manager_access(user_wallet_config, alice, bob):
    """Only highCommand should be able to remove manager"""
    # Non-highCommand address should fail
    with boa.reverts("no perms"):
        user_wallet_config.removeManager(alice, sender=bob)


def test_set_global_manager_settings_access(user_wallet_config, bob, createGlobalManagerSettings):
    """Only highCommand or migrator should be able to set global manager settings"""
    settings = createGlobalManagerSettings()
    
    # Non-authorized address should fail
    with boa.reverts("no perms"):
        user_wallet_config.setGlobalManagerSettings(settings, sender=bob)


######################
# Payee Access Tests #
######################


def test_add_payee_access(user_wallet_config, alice, bob, createPayeeSettings):
    """Only paymaster or migrator should be able to add payee"""
    settings = createPayeeSettings()
    
    # Non-authorized address should fail
    with boa.reverts("no perms"):
        user_wallet_config.addPayee(alice, settings, sender=bob)


def test_update_payee_access(user_wallet_config, alice, bob, createPayeeSettings):
    """Only paymaster should be able to update payee"""
    settings = createPayeeSettings()
    
    # Non-paymaster address should fail
    with boa.reverts("no perms"):
        user_wallet_config.updatePayee(alice, settings, sender=bob)


def test_remove_payee_access(user_wallet_config, alice, bob):
    """Only paymaster should be able to remove payee"""
    # Non-paymaster address should fail
    with boa.reverts("no perms"):
        user_wallet_config.removePayee(alice, sender=bob)


def test_set_global_payee_settings_access(user_wallet_config, bob, createGlobalPayeeSettings):
    """Only paymaster or migrator should be able to set global payee settings"""
    settings = createGlobalPayeeSettings()
    
    # Non-authorized address should fail
    with boa.reverts("no perms"):
        user_wallet_config.setGlobalPayeeSettings(settings, sender=bob)


def test_add_pending_payee_access(user_wallet_config, alice, bob, pending_payee):
    """Only paymaster should be able to add pending payee"""
    # Non-paymaster address should fail
    with boa.reverts("no perms"):
        user_wallet_config.addPendingPayee(alice, pending_payee, sender=bob)


def test_confirm_pending_payee_access(user_wallet_config, alice, bob):
    """Only paymaster should be able to confirm pending payee"""
    # Non-paymaster address should fail
    with boa.reverts("no perms"):
        user_wallet_config.confirmPendingPayee(alice, sender=bob)


def test_cancel_pending_payee_access(user_wallet_config, alice, bob):
    """Only paymaster should be able to cancel pending payee"""
    # Non-paymaster address should fail
    with boa.reverts("no perms"):
        user_wallet_config.cancelPendingPayee(alice, sender=bob)


#######################
# Cheque Access Tests #
#######################


def test_create_cheque_access(user_wallet_config, alice, bob, createCheque, createChequeData):
    """Only chequeBook should be able to create cheque"""
    cheque = createCheque()
    cheque_data = createChequeData()
    
    # Non-chequeBook address should fail
    with boa.reverts("no perms"):
        user_wallet_config.createCheque(alice, cheque, cheque_data, False, sender=bob)


def test_cancel_cheque_access(user_wallet_config, alice, bob):
    """Only chequeBook should be able to cancel cheque"""
    # Non-chequeBook address should fail
    with boa.reverts("no perms"):
        user_wallet_config.cancelCheque(alice, sender=bob)


def test_set_cheque_settings_access(user_wallet_config, bob, createChequeSettings):
    """Only chequeBook should be able to set cheque settings"""
    settings = createChequeSettings()
    
    # Non-chequeBook address should fail
    with boa.reverts("no perms"):
        user_wallet_config.setChequeSettings(settings, sender=bob)


###############################
# Whitelist Persistence Tests #
###############################


def test_whitelist_persistence(user_wallet_config, kernel, alice, bob, charlie, pending_whitelist, user_wallet):
    """Test whitelist data persistence and iteration"""
    # Initial state - check current number
    initial_count = user_wallet_config.numWhitelisted()
    assert user_wallet_config.indexOfWhitelist(alice) == 0
    
    # Add pending whitelist
    user_wallet_config.addPendingWhitelistAddr(alice, pending_whitelist, sender=kernel.address)
    
    # Verify pending data
    pending = user_wallet_config.pendingWhitelist(alice)
    assert pending.initiatedBlock == pending_whitelist[0]  # initiatedBlock
    assert pending.confirmBlock == pending_whitelist[1]  # confirmBlock
    assert pending.currentOwner == pending_whitelist[2]  # currentOwner
    
    # Time travel and confirm
    boa.env.time_travel(blocks=100)
    user_wallet_config.confirmWhitelistAddr(alice, sender=kernel.address)
    
    # Verify whitelist registered
    assert user_wallet_config.numWhitelisted() == 2
    assert user_wallet_config.indexOfWhitelist(alice) == 1
    assert user_wallet_config.whitelistAddr(1) == alice
    
    # Verify pending cleared
    pending = user_wallet_config.pendingWhitelist(alice)
    assert pending.initiatedBlock == 0
    assert pending.confirmBlock == 0
    assert pending.currentOwner == ZERO_ADDRESS
    
    # Add more addresses - create new pending data with current block
    pending_bob = (
        boa.env.evm.patch.block_number,         # initiatedBlock
        boa.env.evm.patch.block_number + 100,  # confirmBlock
        user_wallet.address,                    # currentOwner
    )
    user_wallet_config.addPendingWhitelistAddr(bob, pending_bob, sender=kernel.address)
    boa.env.time_travel(blocks=100)
    user_wallet_config.confirmWhitelistAddr(bob, sender=kernel.address)
    
    pending_charlie = (
        boa.env.evm.patch.block_number,         # initiatedBlock
        boa.env.evm.patch.block_number + 100,  # confirmBlock
        user_wallet.address,                    # currentOwner
    )
    user_wallet_config.addPendingWhitelistAddr(charlie, pending_charlie, sender=kernel.address)
    boa.env.time_travel(blocks=100)
    user_wallet_config.confirmWhitelistAddr(charlie, sender=kernel.address)
    
    # Verify all registered
    assert user_wallet_config.numWhitelisted() == initial_count + 3
    assert user_wallet_config.indexOfWhitelist(bob) > 0
    assert user_wallet_config.indexOfWhitelist(charlie) > 0
    assert user_wallet_config.whitelistAddr(user_wallet_config.indexOfWhitelist(bob)) == bob
    assert user_wallet_config.whitelistAddr(user_wallet_config.indexOfWhitelist(charlie)) == charlie
    
    # Remove middle item (bob)
    user_wallet_config.removeWhitelistAddr(bob, sender=kernel.address)
    
    # Verify removal and reindexing
    assert user_wallet_config.numWhitelisted() == 3
    assert user_wallet_config.indexOfWhitelist(bob) == 0  # Removed
    assert user_wallet_config.indexOfWhitelist(charlie) == 2  # Moved to bob's position
    assert user_wallet_config.whitelistAddr(2) == charlie  # Charlie moved


def test_whitelist_cancel_pending(user_wallet_config, kernel, alice, pending_whitelist):
    """Test canceling pending whitelist"""
    # Add pending
    user_wallet_config.addPendingWhitelistAddr(alice, pending_whitelist, sender=kernel.address)
    
    # Verify pending exists
    pending = user_wallet_config.pendingWhitelist(alice)
    assert pending.confirmBlock != 0
    
    # Cancel pending
    user_wallet_config.cancelPendingWhitelistAddr(alice, sender=kernel.address)
    
    # Verify cancelled
    pending = user_wallet_config.pendingWhitelist(alice)
    assert pending.initiatedBlock == 0
    assert pending.confirmBlock == 0
    assert pending.currentOwner == ZERO_ADDRESS


def test_whitelist_via_migrator(user_wallet_config, migrator, alice):
    """Test adding whitelist directly via migrator"""
    # Initial state
    assert user_wallet_config.indexOfWhitelist(alice) == 0
    
    # Add via migrator (no pending/confirm needed)
    user_wallet_config.addWhitelistAddrViaMigrator(alice, sender=migrator.address)
    
    # Verify immediately registered
    assert user_wallet_config.indexOfWhitelist(alice) > 0
    assert user_wallet_config.whitelistAddr(user_wallet_config.indexOfWhitelist(alice)) == alice


#############################
# Manager Persistence Tests #
#############################


def test_manager_persistence(user_wallet_config, high_command, alice, bob, charlie, createManagerSettings):
    """Test manager data persistence and iteration"""
    # Initial state - check current number
    initial_count = user_wallet_config.numManagers()
    assert user_wallet_config.indexOfManager(alice) == 0
    
    # Add first manager
    settings1 = createManagerSettings(
        _startBlock=1000,
        _expiryBlock=2000,
        _canClaimLoot=True
    )
    user_wallet_config.addManager(alice, settings1, sender=high_command.address)
    
    # Verify registration
    assert user_wallet_config.numManagers() == initial_count + 1
    assert user_wallet_config.indexOfManager(alice) > 0
    assert user_wallet_config.managers(user_wallet_config.indexOfManager(alice)) == alice
    
    # Verify settings persisted
    saved_settings = user_wallet_config.managerSettings(alice)
    assert saved_settings.startBlock == 1000
    assert saved_settings.expiryBlock == 2000
    assert saved_settings.canClaimLoot == True
    
    # Add more managers
    settings2 = createManagerSettings()
    user_wallet_config.addManager(bob, settings2, sender=high_command.address)
    user_wallet_config.addManager(charlie, settings2, sender=high_command.address)
    
    # Verify all registered
    assert user_wallet_config.numManagers() == initial_count + 3
    assert user_wallet_config.indexOfManager(bob) > 0
    assert user_wallet_config.indexOfManager(charlie) > 0
    
    # Update manager settings
    settings3 = createManagerSettings(_canClaimLoot=True)
    user_wallet_config.updateManager(alice, settings3, sender=high_command.address)
    
    # Verify update
    saved_settings = user_wallet_config.managerSettings(alice)
    assert saved_settings.canClaimLoot == True
    
    # Remove manager (bob)
    bob_index = user_wallet_config.indexOfManager(bob)
    charlie_index = user_wallet_config.indexOfManager(charlie)
    user_wallet_config.removeManager(bob, sender=high_command.address)
    
    # Verify removal and reindexing
    assert user_wallet_config.numManagers() == initial_count + 2
    assert user_wallet_config.indexOfManager(bob) == 0  # Removed
    # If charlie was after bob, it should have moved to bob's position
    if charlie_index > bob_index:
        assert user_wallet_config.indexOfManager(charlie) == bob_index
    
    # Verify settings cleared
    saved_settings = user_wallet_config.managerSettings(bob)
    assert saved_settings.startBlock == 0


def test_global_manager_settings_persistence(user_wallet_config, high_command, createGlobalManagerSettings):
    """Test global manager settings persistence"""
    # Set global settings
    settings = createGlobalManagerSettings(
        _managerPeriod=100000,
        _startDelay=50,
        _activationLength=200000,
        _canOwnerManage=False
    )
    user_wallet_config.setGlobalManagerSettings(settings, sender=high_command.address)
    
    # Verify persistence
    saved = user_wallet_config.globalManagerSettings()
    assert saved.managerPeriod == 100000
    assert saved.startDelay == 50
    assert saved.activationLength == 200000
    assert saved.canOwnerManage == False


###########################
# Payee Persistence Tests #
###########################


def test_payee_persistence(user_wallet_config, paymaster, alice, bob, charlie, createPayeeSettings):
    """Test payee data persistence and iteration"""
    # Initial state - check current number
    initial_count = user_wallet_config.numPayees()
    assert user_wallet_config.indexOfPayee(alice) == 0
    
    # Add first payee
    settings1 = createPayeeSettings(
        _startBlock=1000,
        _expiryBlock=2000,
        _canPull=True,
        _periodLength=50000
    )
    user_wallet_config.addPayee(alice, settings1, sender=paymaster.address)
    
    # Verify registration
    assert user_wallet_config.numPayees() == initial_count + 1
    assert user_wallet_config.indexOfPayee(alice) > 0
    assert user_wallet_config.payees(user_wallet_config.indexOfPayee(alice)) == alice
    
    # Verify settings persisted
    saved_settings = user_wallet_config.payeeSettings(alice)
    assert saved_settings.startBlock == 1000
    assert saved_settings.expiryBlock == 2000
    assert saved_settings.canPull == True
    assert saved_settings.periodLength == 50000
    
    # Add more payees
    settings2 = createPayeeSettings()
    user_wallet_config.addPayee(bob, settings2, sender=paymaster.address)
    user_wallet_config.addPayee(charlie, settings2, sender=paymaster.address)
    
    # Verify all registered
    assert user_wallet_config.numPayees() == initial_count + 3
    assert user_wallet_config.indexOfPayee(bob) > 0
    assert user_wallet_config.indexOfPayee(charlie) > 0
    
    # Update payee settings
    settings3 = createPayeeSettings(_canPull=True, _onlyPrimaryAsset=True)
    user_wallet_config.updatePayee(alice, settings3, sender=paymaster.address)
    
    # Verify update
    saved_settings = user_wallet_config.payeeSettings(alice)
    assert saved_settings.canPull == True
    assert saved_settings.onlyPrimaryAsset == True
    
    # Remove payee (bob)
    bob_index = user_wallet_config.indexOfPayee(bob)
    charlie_index = user_wallet_config.indexOfPayee(charlie)
    user_wallet_config.removePayee(bob, sender=paymaster.address)
    
    # Verify removal and reindexing
    assert user_wallet_config.numPayees() == initial_count + 2
    assert user_wallet_config.indexOfPayee(bob) == 0  # Removed
    # If charlie was after bob, it should have moved to bob's position
    if charlie_index > bob_index:
        assert user_wallet_config.indexOfPayee(charlie) == bob_index
    
    # Verify settings cleared
    saved_settings = user_wallet_config.payeeSettings(bob)
    assert saved_settings.startBlock == 0


def test_pending_payee_persistence(user_wallet_config, paymaster, alice, createPayeeSettings):
    """Test pending payee functionality"""
    # Create pending payee
    settings = createPayeeSettings(_canPull=True)
    pending_data = (
        settings,
        boa.env.evm.patch.block_number,         # initiatedBlock
        boa.env.evm.patch.block_number + 100,  # confirmBlock
        user_wallet_config.wallet(),            # currentOwner
    )
    
    # Add pending
    user_wallet_config.addPendingPayee(alice, pending_data, sender=paymaster.address)
    
    # Verify pending data
    saved_pending = user_wallet_config.pendingPayees(alice)
    assert saved_pending.initiatedBlock == pending_data[1]
    assert saved_pending.confirmBlock == pending_data[2]
    assert saved_pending.currentOwner == pending_data[3]
    assert saved_pending.settings.canPull == True
    
    # Time travel and confirm
    boa.env.time_travel(blocks=100)
    user_wallet_config.confirmPendingPayee(alice, sender=paymaster.address)
    
    # Verify payee registered with settings
    assert user_wallet_config.indexOfPayee(alice) > 0
    saved_settings = user_wallet_config.payeeSettings(alice)
    assert saved_settings.canPull == True
    
    # Verify pending cleared
    saved_pending = user_wallet_config.pendingPayees(alice)
    assert saved_pending.confirmBlock == 0


def test_global_payee_settings_persistence(user_wallet_config, paymaster, createGlobalPayeeSettings):
    """Test global payee settings persistence"""
    # Set global settings
    settings = createGlobalPayeeSettings(
        _startDelay=100,
        _activationLength=50000,
        _defaultPeriodLength=10000
    )
    user_wallet_config.setGlobalPayeeSettings(settings, sender=paymaster.address)
    
    # Verify persistence
    saved = user_wallet_config.globalPayeeSettings()
    assert saved.startDelay == 100
    assert saved.activationLength == 50000
    assert saved.defaultPeriodLength == 10000


############################
# Cheque Persistence Tests #
############################


def test_cheque_persistence(user_wallet_config, cheque_book, alice, bob, createCheque, createChequeData):
    """Test cheque data persistence"""
    # Initial state
    assert user_wallet_config.numActiveCheques() == 0
    
    # Create first cheque
    cheque1 = createCheque(
        _recipient=alice,
        _asset=bob,  # Using bob as mock asset
        _amount=1000,
        _usdValueOnCreation=1000,
        _canManagerPay=False
    )
    cheque_data = createChequeData()
    
    user_wallet_config.createCheque(alice, cheque1, cheque_data, False, sender=cheque_book.address)
    
    # Verify cheque saved
    saved_cheque = user_wallet_config.cheques(alice)
    assert saved_cheque.recipient == alice
    assert saved_cheque.asset == bob
    assert saved_cheque.amount == 1000
    assert saved_cheque.usdValueOnCreation == 1000
    assert saved_cheque.canManagerPay == False
    assert saved_cheque.active == True
    
    # Verify count
    assert user_wallet_config.numActiveCheques() == 1
    
    # Create another cheque
    cheque2 = createCheque(_recipient=bob)
    user_wallet_config.createCheque(bob, cheque2, cheque_data, False, sender=cheque_book.address)
    assert user_wallet_config.numActiveCheques() == 2
    
    # Cancel first cheque
    user_wallet_config.cancelCheque(alice, sender=cheque_book.address)
    
    # Verify cancelled
    saved_cheque = user_wallet_config.cheques(alice)
    assert saved_cheque.recipient == ZERO_ADDRESS  # Cleared
    assert user_wallet_config.numActiveCheques() == 1
    
    # Update existing cheque (isExistingCheque=True doesn't increment count)
    cheque3 = createCheque(_recipient=bob, _amount=2000)
    user_wallet_config.createCheque(bob, cheque3, cheque_data, True, sender=cheque_book.address)
    
    # Verify update
    saved_cheque = user_wallet_config.cheques(bob)
    assert saved_cheque.amount == 2000
    assert user_wallet_config.numActiveCheques() == 1  # Count unchanged


def test_cheque_settings_persistence(user_wallet_config, cheque_book, createChequeSettings):
    """Test cheque settings persistence"""
    # Set cheque settings
    settings = createChequeSettings(
        _maxNumActiveCheques=5,
        _maxChequeUsdValue=10000,
        _instantUsdThreshold=100,
        _periodLength=50000,
        _canManagersCreateCheques=False
    )
    user_wallet_config.setChequeSettings(settings, sender=cheque_book.address)
    
    # Verify persistence
    saved = user_wallet_config.chequeSettings()
    assert saved.maxNumActiveCheques == 5
    assert saved.maxChequeUsdValue == 10000
    assert saved.instantUsdThreshold == 100
    assert saved.periodLength == 50000
    assert saved.canManagersCreateCheques == False


def test_cheque_period_data_persistence(user_wallet_config, cheque_book, alice, createCheque, createChequeData):
    """Test cheque period data updates"""
    # Create initial cheque data
    cheque_data = createChequeData(
        _numChequesPaidInPeriod=2,
        _totalUsdValuePaidInPeriod=5000,
        _totalNumChequesPaid=10,
        _totalUsdValuePaid=50000
    )
    
    # Create cheque with data
    cheque = createCheque()
    user_wallet_config.createCheque(alice, cheque, cheque_data, False, sender=cheque_book.address)
    
    # Verify period data saved
    saved_data = user_wallet_config.chequePeriodData()
    assert saved_data.numChequesPaidInPeriod == 2
    assert saved_data.totalUsdValuePaidInPeriod == 5000
    assert saved_data.totalNumChequesPaid == 10
    assert saved_data.totalUsdValuePaid == 50000


#################################
# Edge Cases and Security Tests #
#################################


def test_duplicate_whitelist_add(user_wallet_config, kernel, alice, pending_whitelist, migrator):
    """Test that duplicate whitelist entries are handled correctly"""
    # Add and confirm first time
    user_wallet_config.addPendingWhitelistAddr(alice, pending_whitelist, sender=kernel.address)
    boa.env.time_travel(blocks=100)
    user_wallet_config.confirmWhitelistAddr(alice, sender=kernel.address)
    
    alice_index = user_wallet_config.indexOfWhitelist(alice)
    assert alice_index > 0
    
    # Try to add again via migrator - should not create duplicate
    initial_count = user_wallet_config.numWhitelisted()
    user_wallet_config.addWhitelistAddrViaMigrator(alice, sender=migrator.address)
    
    # Count should not increase
    assert user_wallet_config.numWhitelisted() == initial_count
    assert user_wallet_config.indexOfWhitelist(alice) == alice_index


def test_duplicate_manager_add(user_wallet_config, high_command, alice, createManagerSettings):
    """Test that duplicate manager entries are handled correctly"""
    settings = createManagerSettings()
    
    # Add first time
    user_wallet_config.addManager(alice, settings, sender=high_command.address)
    alice_index = user_wallet_config.indexOfManager(alice)
    assert alice_index > 0
    
    # Try to add again - should not create duplicate
    initial_count = user_wallet_config.numManagers()
    user_wallet_config.addManager(alice, settings, sender=high_command.address)
    
    # Count should not increase
    assert user_wallet_config.numManagers() == initial_count
    assert user_wallet_config.indexOfManager(alice) == alice_index


def test_remove_non_existent_items(user_wallet_config, kernel, high_command, paymaster, alice):
    """Test removing non-existent items doesn't break state"""
    # Remove non-existent whitelist
    initial_whitelist_count = user_wallet_config.numWhitelisted()
    user_wallet_config.removeWhitelistAddr(alice, sender=kernel.address)
    assert user_wallet_config.numWhitelisted() == initial_whitelist_count
    
    # Remove non-existent manager
    initial_manager_count = user_wallet_config.numManagers()
    user_wallet_config.removeManager(alice, sender=high_command.address)
    assert user_wallet_config.numManagers() == initial_manager_count
    
    # Remove non-existent payee
    initial_payee_count = user_wallet_config.numPayees()
    user_wallet_config.removePayee(alice, sender=paymaster.address)
    assert user_wallet_config.numPayees() == initial_payee_count


def test_time_delay_enforcement(user_wallet_config, kernel, paymaster, alice, pending_whitelist, createPayeeSettings, user_wallet):
    """Test that time delays are enforced for pending items"""
    # Test whitelist time delay with fresh pending data
    fresh_pending = (
        boa.env.evm.patch.block_number,         # initiatedBlock
        boa.env.evm.patch.block_number + 10,   # confirmBlock (10 blocks later)
        user_wallet.address,                    # currentOwner
    )
    user_wallet_config.addPendingWhitelistAddr(alice, fresh_pending, sender=kernel.address)
    
    # Should fail before time delay
    # Current block is still less than confirmBlock
    with boa.reverts("time delay not reached"):
        user_wallet_config.confirmWhitelistAddr(alice, sender=kernel.address)
    
    # Should succeed after time delay
    boa.env.time_travel(blocks=10)  # Now at confirmBlock
    user_wallet_config.confirmWhitelistAddr(alice, sender=kernel.address)
    
    # Remove alice from whitelist first to test payee
    user_wallet_config.removeWhitelistAddr(alice, sender=kernel.address)
    
    # Test payee time delay
    settings = createPayeeSettings()
    fresh_payee_data = (
        settings,
        boa.env.evm.patch.block_number,         # initiatedBlock
        boa.env.evm.patch.block_number + 10,    # confirmBlock (10 blocks later)
        user_wallet_config.wallet(),             # currentOwner
    )
    user_wallet_config.addPendingPayee(alice, fresh_payee_data, sender=paymaster.address)
    
    # Should fail before time delay
    # Current block is still less than confirmBlock
    with boa.reverts("time delay not reached"):
        user_wallet_config.confirmPendingPayee(alice, sender=paymaster.address)
    
    # Should succeed after time delay
    boa.env.time_travel(blocks=10)  # Now at confirmBlock
    user_wallet_config.confirmPendingPayee(alice, sender=paymaster.address)


#######################
# Security Mode Tests #
#######################


def test_set_frozen_access(user_wallet_config, alice, charlie):
    """Only owner or addresses with security permissions should be able to freeze/unfreeze"""
    # Get the wallet owner
    owner = user_wallet_config.owner()
    
    # Use charlie as the non-owner address
    assert charlie != owner, f"Charlie should not be the wallet owner. Owner: {owner}, Charlie: {charlie}"
    
    # Initial state should be unfrozen
    assert user_wallet_config.isFrozen() == False
    
    # First freeze the wallet as owner
    user_wallet_config.setFrozen(True, sender=owner)
    assert user_wallet_config.isFrozen() == True
    
    # Non-owner address should fail to unfreeze
    with boa.reverts("no perms"):
        user_wallet_config.setFrozen(False, sender=charlie)
    
    # State should still be frozen
    assert user_wallet_config.isFrozen() == True
    
    # Owner can unfreeze
    user_wallet_config.setFrozen(False, sender=owner)
    assert user_wallet_config.isFrozen() == False
    
    # Can't set to same value
    with boa.reverts("nothing to change"):
        user_wallet_config.setFrozen(False, sender=owner)


def test_set_frozen_by_owner_only(user_wallet_config):
    """Test that owner can freeze/unfreeze their wallet"""
    owner = user_wallet_config.owner()
    
    # Initial state
    assert user_wallet_config.isFrozen() == False
    
    # Owner can freeze their own wallet
    user_wallet_config.setFrozen(True, sender=owner)
    assert user_wallet_config.isFrozen() == True
    
    # Can't set to same value
    with boa.reverts("nothing to change"):
        user_wallet_config.setFrozen(True, sender=owner)
    
    # Owner can unfreeze
    user_wallet_config.setFrozen(False, sender=owner)
    assert user_wallet_config.isFrozen() == False


def test_set_frozen_persistence(user_wallet_config):
    """Frozen state should persist correctly"""
    owner = user_wallet_config.owner()
    
    # Initial state
    assert user_wallet_config.isFrozen() == False
    
    # Set frozen
    user_wallet_config.setFrozen(True, sender=owner)
    assert user_wallet_config.isFrozen() == True
    
    # Setting to same value should fail
    with boa.reverts("nothing to change"):
        user_wallet_config.setFrozen(True, sender=owner)
    
    # State should still be frozen
    assert user_wallet_config.isFrozen() == True
    
    # Unfreeze
    user_wallet_config.setFrozen(False, sender=owner)
    assert user_wallet_config.isFrozen() == False
    
    # Setting to same value should fail
    with boa.reverts("nothing to change"):
        user_wallet_config.setFrozen(False, sender=owner)
    
    # State should still be unfrozen
    assert user_wallet_config.isFrozen() == False


def test_set_ejection_mode_access(user_wallet_config, alice, bob, switchboard_alpha):
    """Only switchboard should be able to set ejection mode"""
    # Initial state should be false
    assert user_wallet_config.inEjectMode() == False
    
    # Non-switchboard address should fail
    with boa.reverts("no perms"):
        user_wallet_config.setEjectionMode(True, sender=bob)
    
    # Switchboard should succeed
    user_wallet_config.setEjectionMode(True, sender=switchboard_alpha.address)
    assert user_wallet_config.inEjectMode() == True
    
    # Can't set to same value
    with boa.reverts("nothing to change"):
        user_wallet_config.setEjectionMode(True, sender=switchboard_alpha.address)
    
    # Switchboard can turn off ejection mode
    user_wallet_config.setEjectionMode(False, sender=switchboard_alpha.address)
    assert user_wallet_config.inEjectMode() == False


def test_set_ejection_mode_persistence(user_wallet_config, switchboard_alpha):
    """Ejection mode state should persist correctly"""
    # Initial state should be false
    assert user_wallet_config.inEjectMode() == False
    
    # Enable ejection mode
    user_wallet_config.setEjectionMode(True, sender=switchboard_alpha.address)
    assert user_wallet_config.inEjectMode() == True
    
    # Setting to same value should fail
    with boa.reverts("nothing to change"):
        user_wallet_config.setEjectionMode(True, sender=switchboard_alpha.address)
    
    # State should still be true
    assert user_wallet_config.inEjectMode() == True
    
    # Disable ejection mode
    user_wallet_config.setEjectionMode(False, sender=switchboard_alpha.address)
    assert user_wallet_config.inEjectMode() == False
    
    # Setting to same value should fail
    with boa.reverts("nothing to change"):
        user_wallet_config.setEjectionMode(False, sender=switchboard_alpha.address)
    
    # State should still be false
    assert user_wallet_config.inEjectMode() == False


def test_frozen_and_ejection_mode_independence(user_wallet_config, switchboard_alpha):
    """Frozen and ejection mode should be independent states"""
    owner = user_wallet_config.owner()
    
    # Both should start false
    assert user_wallet_config.isFrozen() == False
    assert user_wallet_config.inEjectMode() == False
    
    # Set frozen (by owner)
    user_wallet_config.setFrozen(True, sender=owner)
    assert user_wallet_config.isFrozen() == True
    assert user_wallet_config.inEjectMode() == False  # Should remain unchanged
    
    # Set ejection mode (by switchboard)
    user_wallet_config.setEjectionMode(True, sender=switchboard_alpha.address)
    assert user_wallet_config.isFrozen() == True  # Should remain unchanged
    assert user_wallet_config.inEjectMode() == True
    
    # Unfreeze (by owner)
    user_wallet_config.setFrozen(False, sender=owner)
    assert user_wallet_config.isFrozen() == False
    assert user_wallet_config.inEjectMode() == True  # Should remain unchanged
    
    # Turn off ejection mode (by switchboard)
    user_wallet_config.setEjectionMode(False, sender=switchboard_alpha.address)
    assert user_wallet_config.isFrozen() == False
    assert user_wallet_config.inEjectMode() == False


def test_ejection_mode_no_trial_funds(user_wallet_config, switchboard_alpha):
    """Can set ejection mode when wallet has no trial funds"""
    # This wallet should have no trial funds
    assert user_wallet_config.trialFundsAmount() == 0
    
    # Should be able to set ejection mode
    user_wallet_config.setEjectionMode(True, sender=switchboard_alpha.address)
    assert user_wallet_config.inEjectMode() == True
    
    # Reset back
    user_wallet_config.setEjectionMode(False, sender=switchboard_alpha.address)
    assert user_wallet_config.inEjectMode() == False