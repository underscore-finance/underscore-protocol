import pytest
import boa
from eth_abi import encode
from eth_utils import keccak

from contracts.core.userWallet import UserWallet, UserWalletConfig
from constants import EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ONE_MONTH_IN_BLOCKS, ZERO_ADDRESS
from conf_utils import (
    confirm_pending_instant_action_settings,
    filter_logs,
    fresh_user_wallet,
    instant_action_settings_tuple,
    set_user_instant_action_settings,
)


def _fresh_wallet_config(hatchery, owner):
    return fresh_user_wallet(hatchery, owner)[1]


def stage_pending_cheque_settings(cheque_book, user_wallet, createChequeSettings, *, sender):
    restrictive = createChequeSettings(
        _maxNumActiveCheques=2,
        _maxChequeUsdValue=300 * EIGHTEEN_DECIMALS,
        _instantUsdThreshold=25 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_DAY_IN_BLOCKS,
        _expensiveDelayBlocks=2 * ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=ONE_DAY_IN_BLOCKS,
        _canManagersCreateCheques=False,
        _canManagerPay=False,
        _canBePulled=False,
    )
    cheque_book.setChequeSettings(user_wallet.address, *restrictive, sender=sender)

    widening = createChequeSettings(
        _maxNumActiveCheques=0,
        _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_DAY_IN_BLOCKS,
        _expensiveDelayBlocks=ONE_DAY_IN_BLOCKS,
        _defaultExpiryBlocks=2 * ONE_DAY_IN_BLOCKS,
        _canManagersCreateCheques=False,
        _canManagerPay=False,
        _canBePulled=False,
    )
    cheque_book.setChequeSettings(user_wallet.address, *widening, sender=sender)


def deploy_registered_cheque_book(cheque_book, wallet_backpack_deploy, governance):
    replacement = boa.load(
        "contracts/core/walletBackpack/ChequeBook.vy",
        cheque_book.UNDY_HQ(),
        cheque_book.MIN_CHEQUE_PERIOD(),
        cheque_book.MAX_CHEQUE_PERIOD(),
        cheque_book.MIN_EXPENSIVE_CHEQUE_DELAY(),
        cheque_book.MAX_UNLOCK_BLOCKS(),
        cheque_book.MAX_EXPIRY_BLOCKS(),
        cheque_book.canInstantSetChequeSettings(),
        name="replacement_cheque_book",
    )
    wallet_backpack_deploy.addPendingChequeBook(replacement.address, sender=governance.address)
    boa.env.time_travel(blocks=wallet_backpack_deploy.actionTimeLock())
    wallet_backpack_deploy.confirmPendingChequeBook(sender=governance.address)
    return replacement


@pytest.fixture
def pending_whitelist(user_wallet):
    """Create a pending whitelist struct"""
    return (
        boa.env.evm.patch.block_number,         # initiatedBlock
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


def test_wallet_binding_is_factory_initialized_and_permanently_one_shot(
    undy_hq,
    hatchery,
    user_wallet_factory,
    alice,
    bob,
    weth,
    kernel,
    sentinel,
    high_command,
    paymaster,
    cheque_book,
    migrator,
    action_data_provider,
    createGlobalManagerSettings,
    createGlobalPayeeSettings,
    createChequeSettings,
    createManagerSettings,
):
    group_id = 97
    tier = 1
    wallet = UserWallet.at(
        hatchery.createUserWallet(
            alice,
            ZERO_ADDRESS,
            group_id,
            tier,
            sender=alice,
        )
    )
    config = UserWalletConfig.at(wallet.walletConfig())
    wallet_salt = keccak(
        encode(
            ["address", "uint256", "uint256"],
            [str(alice), group_id, tier],
        )
    )

    assert config.initialized() is True
    assert config.wallet() == wallet.address
    assert config.walletSalt() == wallet_salt
    assert user_wallet_factory.isUserWalletConfig(config.address, wallet_salt)
    assert not hasattr(config, "setWallet")

    # Binding now occurs inside the factory's atomic initializer path. Once the
    # canonical config is paired, no caller (including Hatchery) can rebind it.
    with boa.reverts("already initialized"):
        config.initialize(
            wallet.address,
            undy_hq.address,
            alice,
            group_id,
            tier,
            createGlobalManagerSettings(),
            createGlobalPayeeSettings(),
            createChequeSettings(),
            ZERO_ADDRESS,
            createManagerSettings(),
            kernel.address,
            sentinel.address,
            high_command.address,
            paymaster.address,
            cheque_book.address,
            migrator.address,
            action_data_provider.address,
            weth.address,
            hatchery.ETH(),
            ONE_DAY_IN_BLOCKS,
            ONE_MONTH_IN_BLOCKS,
            (True, True, True, True),
            sender=bob,
        )


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


def test_set_global_manager_settings_access(user_wallet_config, bob, high_command, migrator, createGlobalManagerSettings):
    """Only highCommand should be able to set global manager settings"""
    settings = createGlobalManagerSettings()
    
    # Non-authorized address should fail
    with boa.reverts("no perms"):
        user_wallet_config.setGlobalManagerSettings(settings, sender=bob)
    with boa.reverts("no perms"):
        user_wallet_config.setGlobalManagerSettings(settings, sender=migrator.address)

    user_wallet_config.setGlobalManagerSettings(settings, sender=high_command.address)


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


def test_set_global_payee_settings_access(user_wallet_config, bob, paymaster, migrator, createGlobalPayeeSettings):
    """Only paymaster should be able to set global payee settings"""
    settings = createGlobalPayeeSettings()
    
    # Non-authorized address should fail
    with boa.reverts("no perms"):
        user_wallet_config.setGlobalPayeeSettings(settings, sender=bob)
    with boa.reverts("no perms"):
        user_wallet_config.setGlobalPayeeSettings(settings, sender=migrator.address)

    user_wallet_config.setGlobalPayeeSettings(settings, sender=paymaster.address)


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


def test_whitelist_via_migrator_rejects_empty_and_duplicate_addresses(user_wallet_config, migrator, alice):
    """Migrator whitelist writes enforce the local checks that fit inside UserWalletConfig."""
    with boa.reverts():
        user_wallet_config.addWhitelistAddrViaMigrator(ZERO_ADDRESS, sender=migrator.address)

    user_wallet_config.addWhitelistAddrViaMigrator(alice, sender=migrator.address)
    with boa.reverts():
        user_wallet_config.addWhitelistAddrViaMigrator(alice, sender=migrator.address)


def test_whitelist_via_migrator_rejects_existing_roles(
    user_wallet_config,
    migrator,
    paymaster,
    high_command,
    cheque_book,
    alice,
    charlie,
    sally,
    createPayeeSettings,
    createManagerSettings,
    createCheque,
    createChequeData,
):
    """Migrator cannot whitelist payees, managers, or active cheque recipients"""
    user_wallet_config.addPayee(alice, createPayeeSettings(), sender=paymaster.address)
    with boa.reverts():
        user_wallet_config.addWhitelistAddrViaMigrator(alice, sender=migrator.address)

    user_wallet_config.addManager(charlie, createManagerSettings(), sender=high_command.address)
    with boa.reverts():
        user_wallet_config.addWhitelistAddrViaMigrator(charlie, sender=migrator.address)

    cheque = createCheque(_recipient=sally)
    user_wallet_config.createCheque(sally, cheque, createChequeData(), False, sender=cheque_book.address)
    with boa.reverts():
        user_wallet_config.addWhitelistAddrViaMigrator(sally, sender=migrator.address)


def test_whitelist_via_migrator_rejects_registry_addresses(user_wallet_config, migrator, ledger):
    """Migrator cannot whitelist privileged Undy registry addresses."""
    with boa.reverts("invalid address"):
        user_wallet_config.addWhitelistAddrViaMigrator(ledger.address, sender=migrator.address)


def test_whitelist_via_migrator_rejects_backpack_items(user_wallet_config, migrator, kernel):
    """Migrator cannot whitelist registered backpack items."""
    with boa.reverts("invalid address"):
        user_wallet_config.addWhitelistAddrViaMigrator(kernel.address, sender=migrator.address)


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


def test_duplicate_payee_add(user_wallet_config, paymaster, alice, createPayeeSettings):
    """Test that duplicate payee entries are rejected"""
    settings = createPayeeSettings()

    user_wallet_config.addPayee(alice, settings, sender=paymaster.address)
    alice_index = user_wallet_config.indexOfPayee(alice)
    assert alice_index > 0

    initial_count = user_wallet_config.numPayees()
    with boa.reverts("already payee"):
        user_wallet_config.addPayee(alice, settings, sender=paymaster.address)

    assert user_wallet_config.numPayees() == initial_count
    assert user_wallet_config.indexOfPayee(alice) == alice_index


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
    
    # Try to add again via migrator - should reject instead of silently no-oping
    initial_count = user_wallet_config.numWhitelisted()
    with boa.reverts():
        user_wallet_config.addWhitelistAddrViaMigrator(alice, sender=migrator.address)
    
    # Count should not increase
    assert user_wallet_config.numWhitelisted() == initial_count
    assert user_wallet_config.indexOfWhitelist(alice) == alice_index


def test_duplicate_manager_add(user_wallet_config, high_command, alice, createManagerSettings):
    """Test that duplicate manager entries are rejected"""
    settings = createManagerSettings()
    
    # Add first time
    user_wallet_config.addManager(alice, settings, sender=high_command.address)
    alice_index = user_wallet_config.indexOfManager(alice)
    assert alice_index > 0
    
    # Try to add again - should reject instead of silently overwriting settings
    initial_count = user_wallet_config.numManagers()
    with boa.reverts("already manager"):
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


def test_whitelist_confirm_enforces_delay(user_wallet_config, kernel, alice, user_wallet):
    """UserWalletConfig keeps the storage-layer whitelist delay check"""
    fresh_pending = (
        boa.env.evm.patch.block_number,         # initiatedBlock
        boa.env.evm.patch.block_number + 10,   # confirmBlock (10 blocks later)
        user_wallet.address,                    # currentOwner
    )
    user_wallet_config.addPendingWhitelistAddr(alice, fresh_pending, sender=kernel.address)

    with boa.reverts("time delay not reached"):
        user_wallet_config.confirmWhitelistAddr(alice, sender=kernel.address)

    boa.env.time_travel(blocks=10)
    user_wallet_config.confirmWhitelistAddr(alice, sender=kernel.address)
    assert user_wallet_config.indexOfWhitelist(alice) != 0


def test_whitelist_confirm_requires_pending_entry(user_wallet_config, kernel, alice):
    """UserWalletConfig cannot confirm a missing pending whitelist entry"""
    with boa.reverts("no pending whitelist"):
        user_wallet_config.confirmWhitelistAddr(alice, sender=kernel.address)
    

###################
# Time Lock Tests #
###################


def test_set_time_lock_access(user_wallet_config, alice):
    """Only the owner can request time lock changes"""
    with boa.reverts("no perms"):
        user_wallet_config.setTimeLock(user_wallet_config.timeLock() + 1, sender=alice)


def test_set_time_lock_enforces_bounds(user_wallet_config, bob):
    """UserWalletConfig rejects time locks outside configured bounds"""
    high_time_lock = user_wallet_config.MAX_TIMELOCK() + 1
    with boa.reverts("invalid time lock"):
        user_wallet_config.setTimeLock(high_time_lock, sender=bob)

    with boa.reverts("invalid time lock"):
        user_wallet_config.setTimeLock(0, sender=bob)


def test_set_time_lock_increase_applies_immediately(user_wallet_config, bob):
    """Increasing the wallet time lock should update live state immediately"""
    new_time_lock = user_wallet_config.timeLock() + 10
    user_wallet_config.setTimeLock(new_time_lock, sender=bob)

    assert user_wallet_config.timeLock() == new_time_lock
    assert user_wallet_config.pendingTimeLock().confirmBlock == 0


def test_set_time_lock_decrease_stages_pending(user_wallet_config, bob):
    """Decreasing the wallet time lock should stage pending state"""
    higher_time_lock = user_wallet_config.MAX_TIMELOCK()
    user_wallet_config.setTimeLock(higher_time_lock, sender=bob)

    lower_time_lock = user_wallet_config.MIN_TIMELOCK()
    user_wallet_config.setTimeLock(lower_time_lock, sender=bob)

    pending = user_wallet_config.pendingTimeLock()
    assert user_wallet_config.timeLock() == higher_time_lock
    assert pending.confirmBlock != 0
    assert pending.newTimeLock == lower_time_lock
    assert pending.currentOwner == bob
    assert pending.confirmBlock == pending.initiatedBlock + higher_time_lock


def test_set_time_lock_second_decrease_reverts_while_pending_exists(user_wallet_config, bob):
    """A second staged time lock decrease should be rejected while one is already pending"""
    user_wallet_config.setTimeLock(user_wallet_config.MAX_TIMELOCK(), sender=bob)
    user_wallet_config.setTimeLock(user_wallet_config.MIN_TIMELOCK(), sender=bob)

    with boa.reverts("pending time lock already exists"):
        user_wallet_config.setTimeLock(user_wallet_config.MIN_TIMELOCK(), sender=bob)


def test_confirm_pending_time_lock_after_delay_updates_live(user_wallet_config, bob):
    """Pending time lock decreases should confirm after the live time lock delay"""
    higher_time_lock = user_wallet_config.MAX_TIMELOCK()
    lower_time_lock = user_wallet_config.MIN_TIMELOCK()
    user_wallet_config.setTimeLock(higher_time_lock, sender=bob)
    user_wallet_config.setTimeLock(lower_time_lock, sender=bob)

    pending = user_wallet_config.pendingTimeLock()
    with boa.reverts("time delay not reached"):
        user_wallet_config.confirmPendingTimeLock(sender=bob)

    boa.env.time_travel(blocks=pending.confirmBlock - boa.env.evm.patch.block_number)
    user_wallet_config.confirmPendingTimeLock(sender=bob)

    assert user_wallet_config.timeLock() == lower_time_lock
    assert user_wallet_config.pendingTimeLock().confirmBlock == 0
    pending = user_wallet_config.pendingTimeLock()
    assert pending.newTimeLock == 0
    assert pending.confirmBlock == 0
    assert pending.currentOwner == ZERO_ADDRESS


def test_confirm_pending_time_lock_at_exact_confirm_block_succeeds(user_wallet_config, bob):
    """Pending time lock confirms should work exactly at confirmBlock"""
    user_wallet_config.setTimeLock(user_wallet_config.MAX_TIMELOCK(), sender=bob)
    user_wallet_config.setTimeLock(user_wallet_config.MIN_TIMELOCK(), sender=bob)

    pending = user_wallet_config.pendingTimeLock()
    boa.env.time_travel(blocks=pending.confirmBlock - boa.env.evm.patch.block_number - 1)
    with boa.reverts("time delay not reached"):
        user_wallet_config.confirmPendingTimeLock(sender=bob)

    boa.env.time_travel(blocks=1)
    user_wallet_config.confirmPendingTimeLock(sender=bob)

    assert user_wallet_config.timeLock() == user_wallet_config.MIN_TIMELOCK()
    assert user_wallet_config.pendingTimeLock().confirmBlock == 0


def test_cancel_pending_time_lock_security_action_can_cancel(
    user_wallet_config, bob, alice, mission_control, switchboard_alpha
):
    """Owner security operators should be able to cancel pending time lock decreases"""
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)

    higher_time_lock = user_wallet_config.MAX_TIMELOCK()
    lower_time_lock = user_wallet_config.MIN_TIMELOCK()
    user_wallet_config.setTimeLock(higher_time_lock, sender=bob)
    user_wallet_config.setTimeLock(lower_time_lock, sender=bob)

    user_wallet_config.cancelPendingTimeLock(sender=alice)

    assert user_wallet_config.timeLock() == higher_time_lock
    assert user_wallet_config.pendingTimeLock().confirmBlock == 0


def test_cancel_pending_time_lock_without_pending_reverts(user_wallet_config, bob):
    """Cancelling a wallet time lock decrease should require pending state"""
    with boa.reverts("no pending time lock"):
        user_wallet_config.cancelPendingTimeLock(sender=bob)


def test_cancel_pending_time_lock_non_security_reverts(user_wallet_config, bob, charlie):
    """Non-owner callers without security permission cannot cancel pending time locks"""
    higher_time_lock = user_wallet_config.MAX_TIMELOCK()
    lower_time_lock = user_wallet_config.MIN_TIMELOCK()
    user_wallet_config.setTimeLock(higher_time_lock, sender=bob)
    user_wallet_config.setTimeLock(lower_time_lock, sender=bob)

    with boa.reverts("no perms"):
        user_wallet_config.cancelPendingTimeLock(sender=charlie)


def test_confirm_pending_time_lock_owner_changed_reverts(user_wallet_config, bob, alice):
    """Pending time lock confirms should fail after ownership changes"""
    higher_time_lock = user_wallet_config.MAX_TIMELOCK()
    lower_time_lock = user_wallet_config.MIN_TIMELOCK()
    user_wallet_config.setTimeLock(higher_time_lock, sender=bob)
    user_wallet_config.setTimeLock(lower_time_lock, sender=bob)

    pending = user_wallet_config.pendingTimeLock()
    user_wallet_config.changeOwnership(alice, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.ownershipTimeLock())
    user_wallet_config.confirmOwnershipChange(sender=alice)
    boa.env.time_travel(blocks=pending.confirmBlock - boa.env.evm.patch.block_number)

    with boa.reverts("owner must match"):
        user_wallet_config.confirmPendingTimeLock(sender=alice)

    user_wallet_config.cancelPendingTimeLock(sender=alice)


def test_set_time_lock_increase_clears_pending_decrease(user_wallet_config, bob):
    """An immediate non-decrease should clear any staged time lock reduction"""
    current_time_lock = min(user_wallet_config.MIN_TIMELOCK() + 1, user_wallet_config.MAX_TIMELOCK())
    user_wallet_config.setTimeLock(current_time_lock, sender=bob)
    user_wallet_config.setTimeLock(user_wallet_config.MIN_TIMELOCK(), sender=bob)

    tightened_time_lock = user_wallet_config.MAX_TIMELOCK()
    user_wallet_config.setTimeLock(tightened_time_lock, sender=bob)

    assert user_wallet_config.timeLock() == tightened_time_lock
    assert user_wallet_config.pendingTimeLock().confirmBlock == 0


def test_set_time_lock_same_value_preserves_pending(user_wallet_config, bob):
    """Re-submitting the live time lock should be a no-op and preserve pending state"""
    current_time_lock = min(user_wallet_config.MIN_TIMELOCK() + 1, user_wallet_config.MAX_TIMELOCK())
    user_wallet_config.setTimeLock(current_time_lock, sender=bob)
    user_wallet_config.setTimeLock(user_wallet_config.MIN_TIMELOCK(), sender=bob)
    pending_before = user_wallet_config.pendingTimeLock()

    user_wallet_config.setTimeLock(current_time_lock, sender=bob)

    pending_after = user_wallet_config.pendingTimeLock()
    assert user_wallet_config.timeLock() == current_time_lock
    assert pending_after.newTimeLock == pending_before.newTimeLock
    assert pending_after.initiatedBlock == pending_before.initiatedBlock
    assert pending_after.confirmBlock == pending_before.confirmBlock
    assert pending_after.currentOwner == pending_before.currentOwner


def test_apply_migrated_config_settings_access_and_clamps(
    user_wallet_config,
    hatchery,
    bob,
    alice,
    migrator,
    createGlobalManagerSettings,
    createGlobalPayeeSettings,
    createChequeSettings,
):
    """The migrator-only settings apply validates source config, access, and scalar field copies."""
    source_config = _fresh_wallet_config(hatchery, bob)
    instant_settings = (True, False, True, False)
    global_manager_settings = createGlobalManagerSettings(
        _managerPeriod=ONE_DAY_IN_BLOCKS,
        _startDelay=7,
        _activationLength=2 * ONE_MONTH_IN_BLOCKS,
        _canOwnerManage=False,
    )
    global_payee_settings = createGlobalPayeeSettings(
        _defaultPeriodLength=2 * ONE_DAY_IN_BLOCKS,
        _startDelay=11,
        _activationLength=3 * ONE_MONTH_IN_BLOCKS,
        _maxNumTxsPerPeriod=9,
        _txCooldownBlocks=13,
        _failOnZeroPrice=True,
        _canPull=False,
    )
    cheque_settings = createChequeSettings(
        _maxNumActiveCheques=3,
        _maxChequeUsdValue=100 * EIGHTEEN_DECIMALS,
        _instantUsdThreshold=10 * EIGHTEEN_DECIMALS,
        _periodLength=ONE_DAY_IN_BLOCKS,
        _expensiveDelayBlocks=5,
        _defaultExpiryBlocks=6,
        _canManagersCreateCheques=False,
        _canManagerPay=False,
        _canBePulled=False,
    )
    args = (
        source_config.address,
        user_wallet_config.MAX_TIMELOCK(),
        instant_settings,
        global_manager_settings,
        global_payee_settings,
        cheque_settings,
    )
    with boa.reverts("no perms"):
        user_wallet_config.applyMigratedConfigSettings(*args, sender=alice)
    with boa.reverts("invalid source config"):
        user_wallet_config.applyMigratedConfigSettings(ZERO_ADDRESS, *args[1:], sender=migrator.address)

    min_time_lock = user_wallet_config.MIN_TIMELOCK()
    max_time_lock = user_wallet_config.MAX_TIMELOCK()

    user_wallet_config.applyMigratedConfigSettings(
        source_config.address,
        min_time_lock,
        instant_settings,
        global_manager_settings,
        global_payee_settings,
        cheque_settings,
        sender=migrator.address,
    )
    assert user_wallet_config.timeLock() == min_time_lock

    user_wallet_config.applyMigratedConfigSettings(
        source_config.address,
        max_time_lock,
        instant_settings,
        global_manager_settings,
        global_payee_settings,
        cheque_settings,
        sender=migrator.address,
    )
    event = filter_logs(user_wallet_config, "MigrationConfigApplied")[-1]
    assert user_wallet_config.timeLock() == max_time_lock
    assert instant_action_settings_tuple(user_wallet_config.instantActionSettings()) == instant_settings
    assert user_wallet_config.globalManagerSettings() == global_manager_settings
    assert user_wallet_config.globalPayeeSettings() == global_payee_settings
    assert user_wallet_config.chequeSettings() == cheque_settings

    assert event.fromConfig == source_config.address
    assert event.timeLock == max_time_lock

    user_wallet_config.applyMigratedConfigSettings(
        source_config.address,
        0,
        instant_settings,
        global_manager_settings,
        global_payee_settings,
        cheque_settings,
        sender=migrator.address,
    )
    assert user_wallet_config.timeLock() == min_time_lock

    user_wallet_config.applyMigratedConfigSettings(
        source_config.address,
        max_time_lock + 1,
        instant_settings,
        global_manager_settings,
        global_payee_settings,
        cheque_settings,
        sender=migrator.address,
    )
    assert user_wallet_config.timeLock() == max_time_lock


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
    
    # Same-value updates are accepted; backpack contracts own higher-level validation.
    user_wallet_config.setFrozen(False, sender=owner)
    assert user_wallet_config.isFrozen() == False


def test_set_frozen_by_owner_only(user_wallet_config):
    """Test that owner can freeze/unfreeze their wallet"""
    owner = user_wallet_config.owner()
    
    # Initial state
    assert user_wallet_config.isFrozen() == False
    
    # Owner can freeze their own wallet
    user_wallet_config.setFrozen(True, sender=owner)
    assert user_wallet_config.isFrozen() == True
    
    # Same-value updates are accepted.
    user_wallet_config.setFrozen(True, sender=owner)
    assert user_wallet_config.isFrozen() == True
    
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
    
    # Setting to the same value is idempotent.
    user_wallet_config.setFrozen(True, sender=owner)
    
    # State should still be frozen
    assert user_wallet_config.isFrozen() == True
    
    # Unfreeze
    user_wallet_config.setFrozen(False, sender=owner)
    assert user_wallet_config.isFrozen() == False
    
    # Setting to the same value is idempotent.
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
    
    # Same-value updates are accepted.
    user_wallet_config.setEjectionMode(True, sender=switchboard_alpha.address)
    assert user_wallet_config.inEjectMode() == True
    
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
    
    # Setting to the same value is idempotent.
    user_wallet_config.setEjectionMode(True, sender=switchboard_alpha.address)
    
    # State should still be true
    assert user_wallet_config.inEjectMode() == True
    
    # Disable ejection mode
    user_wallet_config.setEjectionMode(False, sender=switchboard_alpha.address)
    assert user_wallet_config.inEjectMode() == False
    
    # Setting to the same value is idempotent.
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
    """Can set ejection mode"""
    # Should be able to set ejection mode
    user_wallet_config.setEjectionMode(True, sender=switchboard_alpha.address)
    assert user_wallet_config.inEjectMode() == True

    # Reset back
    user_wallet_config.setEjectionMode(False, sender=switchboard_alpha.address)
    assert user_wallet_config.inEjectMode() == False


##############################
# Backpack Item Setter Tests #
##############################


def test_set_kernel_access(user_wallet_config, alice, kernel):
    """Only owner can set kernel and it must be a registered backpack item"""
    owner = user_wallet_config.owner()
    
    # Non-owner should fail
    with boa.reverts("no perms"):
        user_wallet_config.setKernel(kernel.address, sender=alice)
    
    # Owner should succeed (kernel is already a registered backpack item)
    user_wallet_config.setKernel(kernel.address, sender=owner)
    assert user_wallet_config.kernel() == kernel.address


def test_set_sentinel_access(user_wallet_config, alice, sentinel):
    """Only owner can set sentinel and it must be a registered backpack item"""
    owner = user_wallet_config.owner()
    
    # Non-owner should fail
    with boa.reverts("no perms"):
        user_wallet_config.setSentinel(sentinel.address, sender=alice)
    
    # Owner should succeed (sentinel is already a registered backpack item)
    user_wallet_config.setSentinel(sentinel.address, sender=owner)
    assert user_wallet_config.sentinel() == sentinel.address


def test_set_high_command_access(user_wallet_config, alice, high_command):
    """Only owner can set high command and it must be a registered backpack item"""
    owner = user_wallet_config.owner()
    
    # Non-owner should fail
    with boa.reverts("no perms"):
        user_wallet_config.setHighCommand(high_command.address, sender=alice)
    
    # Owner should succeed (high_command is already a registered backpack item)
    user_wallet_config.setHighCommand(high_command.address, sender=owner)
    assert user_wallet_config.highCommand() == high_command.address


def test_set_paymaster_access(user_wallet_config, alice, paymaster):
    """Only owner can set paymaster and it must be a registered backpack item"""
    owner = user_wallet_config.owner()
    
    # Non-owner should fail
    with boa.reverts("no perms"):
        user_wallet_config.setPaymaster(paymaster.address, sender=alice)
    
    # Owner should succeed (paymaster is already a registered backpack item)
    user_wallet_config.setPaymaster(paymaster.address, sender=owner)
    assert user_wallet_config.paymaster() == paymaster.address


def test_set_cheque_book_access(user_wallet_config, alice, cheque_book):
    """Only owner can set cheque book and it must be a registered backpack item"""
    owner = user_wallet_config.owner()
    
    # Non-owner should fail
    with boa.reverts("no perms"):
        user_wallet_config.setChequeBook(cheque_book.address, sender=alice)
    
    # Owner should succeed (cheque_book is already a registered backpack item)
    user_wallet_config.setChequeBook(cheque_book.address, sender=owner)
    assert user_wallet_config.chequeBook() == cheque_book.address


def test_set_cheque_book_same_address_succeeds_with_pending_settings(
    user_wallet, user_wallet_config, bob, cheque_book, createChequeSettings
):
    stage_pending_cheque_settings(cheque_book, user_wallet, createChequeSettings, sender=bob)
    assert cheque_book.hasPendingChequeSettings(user_wallet.address)

    user_wallet_config.setChequeBook(cheque_book.address, sender=bob)

    assert user_wallet_config.chequeBook() == cheque_book.address
    cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=bob)


def test_set_cheque_book_different_registered_book_trusts_registered_sender_with_pending_settings(
    user_wallet,
    user_wallet_config,
    bob,
    cheque_book,
    wallet_backpack_deploy,
    governance,
    createChequeSettings,
):
    replacement = deploy_registered_cheque_book(cheque_book, wallet_backpack_deploy, governance)
    stage_pending_cheque_settings(cheque_book, user_wallet, createChequeSettings, sender=bob)
    assert cheque_book.hasPendingChequeSettings(user_wallet.address)

    user_wallet_config.setChequeBook(replacement.address, sender=bob)

    assert user_wallet_config.chequeBook() == replacement.address


def test_set_cheque_book_different_registered_book_succeeds_after_pending_settings_cleared(
    user_wallet,
    user_wallet_config,
    bob,
    cheque_book,
    wallet_backpack_deploy,
    governance,
    createChequeSettings,
):
    replacement = deploy_registered_cheque_book(cheque_book, wallet_backpack_deploy, governance)
    stage_pending_cheque_settings(cheque_book, user_wallet, createChequeSettings, sender=bob)
    assert cheque_book.hasPendingChequeSettings(user_wallet.address)
    cheque_book.cancelPendingChequeSettings(user_wallet.address, sender=bob)
    assert not cheque_book.hasPendingChequeSettings(user_wallet.address)

    user_wallet_config.setChequeBook(replacement.address, sender=bob)

    assert user_wallet_config.chequeBook() == replacement.address


def test_set_migrator_access(user_wallet_config, alice, migrator):
    """Only owner can set migrator and it must be a registered backpack item"""
    owner = user_wallet_config.owner()
    
    # Non-owner should fail
    with boa.reverts("no perms"):
        user_wallet_config.setMigrator(migrator.address, sender=alice)
    
    # Owner should succeed (migrator is already a registered backpack item)
    user_wallet_config.setMigrator(migrator.address, sender=owner)
    assert user_wallet_config.migrator() == migrator.address


def test_set_migrator_rejects_pending_migration(user_wallet_config, alice, migrator):
    """Migrator swaps are blocked while migration state is pending."""
    owner = user_wallet_config.owner()
    user_wallet_config.setPendingMigration(alice, sender=migrator.address)

    with boa.reverts("pending migration exists"):
        user_wallet_config.setMigrator(migrator.address, sender=owner)

    assert user_wallet_config.migrator() == migrator.address


def test_set_pending_migration_rejects_existing_pending(user_wallet_config, alice, bob, migrator):
    """The config itself rejects pending migration overwrites."""
    user_wallet_config.setPendingMigration(alice, sender=migrator.address)

    with boa.reverts("pending migration exists"):
        user_wallet_config.setPendingMigration(bob, sender=migrator.address)

    assert user_wallet_config.pendingMigration().toWallet == alice


def test_set_backpack_item_not_registered(user_wallet_config, alice):
    """Cannot set backpack item to an unregistered address"""
    owner = user_wallet_config.owner()
    
    # Alice is not a registered backpack item
    # Should fail even when called by owner
    with boa.reverts("no perms"):
        user_wallet_config.setKernel(alice, sender=owner)
    
    with boa.reverts("no perms"):
        user_wallet_config.setSentinel(alice, sender=owner)
    
    with boa.reverts("no perms"):
        user_wallet_config.setHighCommand(alice, sender=owner)
    
    with boa.reverts("no perms"):
        user_wallet_config.setPaymaster(alice, sender=owner)
    
    with boa.reverts("no perms"):
        user_wallet_config.setChequeBook(alice, sender=owner)
    
    with boa.reverts("no perms"):
        user_wallet_config.setMigrator(alice, sender=owner)


def test_backpack_item_persistence(user_wallet_config, kernel, sentinel, high_command, paymaster, cheque_book, migrator):
    """Test that backpack items persist correctly when set"""
    owner = user_wallet_config.owner()
    
    # Store initial values
    initial_kernel = user_wallet_config.kernel()
    initial_sentinel = user_wallet_config.sentinel()
    initial_high_command = user_wallet_config.highCommand()
    initial_paymaster = user_wallet_config.paymaster()
    initial_cheque_book = user_wallet_config.chequeBook()
    initial_migrator = user_wallet_config.migrator()
    
    # All should already be set from fixtures
    assert initial_kernel == kernel.address
    assert initial_sentinel == sentinel.address
    assert initial_high_command == high_command.address
    assert initial_paymaster == paymaster.address
    assert initial_cheque_book == cheque_book.address
    assert initial_migrator == migrator.address
    
    # Setting to the same value should still work
    user_wallet_config.setKernel(kernel.address, sender=owner)
    user_wallet_config.setSentinel(sentinel.address, sender=owner)
    user_wallet_config.setHighCommand(high_command.address, sender=owner)
    user_wallet_config.setPaymaster(paymaster.address, sender=owner)
    user_wallet_config.setChequeBook(cheque_book.address, sender=owner)
    user_wallet_config.setMigrator(migrator.address, sender=owner)
    
    # Values should remain the same
    assert user_wallet_config.kernel() == kernel.address
    assert user_wallet_config.sentinel() == sentinel.address
    assert user_wallet_config.highCommand() == high_command.address
    assert user_wallet_config.paymaster() == paymaster.address
    assert user_wallet_config.chequeBook() == cheque_book.address
    assert user_wallet_config.migrator() == migrator.address


##########################
# Asset Management Tests #
##########################


def test_update_asset_data_access(user_wallet_config, alice, alpha_token):
    """Only switchboard or authorized addresses should be able to update asset data"""
    # Non-authorized address should fail
    with boa.reverts("no perms"):
        user_wallet_config.updateAssetData(0, alpha_token.address, False, sender=alice)


def test_update_asset_data_by_switchboard(user_wallet_config, switchboard_alpha, alpha_token, user_wallet, alpha_token_whale):
    """Switchboard should be able to update asset data"""
    # Give the wallet some of the asset first (assets need balance to be registered)
    alpha_token.transfer(user_wallet.address, 100 * 10**18, sender=alpha_token_whale)
    
    # Update asset data
    new_total_value = user_wallet_config.updateAssetData(0, alpha_token.address, False, sender=switchboard_alpha.address)
    
    # Should return a value (total USD value)
    assert isinstance(new_total_value, int)
    assert new_total_value >= 0
    
    # Asset should now have assetData (even if not in assets array due to zero USD value)
    asset_data = user_wallet.assetData(alpha_token.address)
    assert asset_data.assetBalance > 0


def test_update_all_asset_data_access(user_wallet_config, alice):
    """Only switchboard or authorized addresses should be able to update all asset data"""
    # Non-authorized address should fail
    with boa.reverts("no perms"):
        user_wallet_config.updateAllAssetData(False, sender=alice)


def test_update_all_asset_data_by_switchboard(user_wallet_config, switchboard_alpha):
    """Switchboard should be able to update all asset data"""
    # Should work and return total USD value
    new_total_value = user_wallet_config.updateAllAssetData(False, sender=switchboard_alpha.address)
    
    # Should return a value (total USD value)
    assert isinstance(new_total_value, int)
    assert new_total_value >= 0


def test_deregister_asset_access(user_wallet_config, alice, alpha_token):
    """Only migrator or registered addresses can deregister assets"""
    # Non-authorized address should fail
    with boa.reverts("no perms"):
        user_wallet_config.deregisterAsset(alpha_token.address, sender=alice)


def test_deregister_asset_by_migrator(user_wallet_config, migrator, alpha_token, switchboard_alpha, user_wallet, alpha_token_whale):
    """Migrator should be able to deregister assets"""
    # Give the wallet some of the asset first
    alpha_token.transfer(user_wallet.address, 100 * 10**18, sender=alpha_token_whale)
    
    # Register the asset
    user_wallet_config.updateAssetData(0, alpha_token.address, False, sender=switchboard_alpha.address)
    
    # Verify asset has assetData
    asset_data = user_wallet.assetData(alpha_token.address)
    assert asset_data.assetBalance > 0
    
    # Deregister the asset
    user_wallet_config.deregisterAsset(alpha_token.address, sender=migrator.address)
    
    # Deregister only removes from assets array but asset data remains
    # The asset balance is still there but it's not tracked in the assets array anymore
    asset_data = user_wallet.assetData(alpha_token.address)
    assert asset_data.assetBalance > 0  # Balance still exists


def test_asset_data_persistence_cycle(user_wallet_config, switchboard_alpha, alpha_token, migrator, user_wallet, alpha_token_whale):
    """Test complete asset lifecycle: register, update, deregister"""
    # Asset should not have assetData initially
    initial_asset_data = user_wallet.assetData(alpha_token.address)
    assert initial_asset_data.assetBalance == 0
    
    # Give the wallet some of the asset
    alpha_token.transfer(user_wallet.address, 100 * 10**18, sender=alpha_token_whale)
    
    # Update asset data to register it
    new_total_value1 = user_wallet_config.updateAssetData(0, alpha_token.address, False, sender=switchboard_alpha.address)
    
    # Asset should now have assetData
    asset_data = user_wallet.assetData(alpha_token.address)
    assert asset_data.assetBalance > 0
    
    # Update asset data again - should work
    new_total_value2 = user_wallet_config.updateAssetData(0, alpha_token.address, False, sender=switchboard_alpha.address)
    
    # Asset should still have data
    asset_data = user_wallet.assetData(alpha_token.address)
    assert asset_data.assetBalance > 0
    
    # Deregister the asset
    user_wallet_config.deregisterAsset(alpha_token.address, sender=migrator.address)
    
    # Deregister only removes from assets array but asset data remains
    # The asset balance is still there but it's not tracked in the assets array anymore
    asset_data = user_wallet.assetData(alpha_token.address)
    assert asset_data.assetBalance > 0  # Balance still exists


def test_update_asset_data_yield_check_parameter(user_wallet_config, switchboard_alpha, alpha_token):
    """Test updateAssetData with different shouldCheckYield values"""
    # Test with shouldCheckYield = False
    new_total_value1 = user_wallet_config.updateAssetData(0, alpha_token.address, False, sender=switchboard_alpha.address)
    assert isinstance(new_total_value1, int)
    
    # Test with shouldCheckYield = True
    new_total_value2 = user_wallet_config.updateAssetData(0, alpha_token.address, True, sender=switchboard_alpha.address)
    assert isinstance(new_total_value2, int)


def test_update_all_asset_data_yield_check_parameter(user_wallet_config, switchboard_alpha):
    """Test updateAllAssetData with different shouldCheckYield values"""
    # Test with shouldCheckYield = False
    new_total_value1 = user_wallet_config.updateAllAssetData(False, sender=switchboard_alpha.address)
    assert isinstance(new_total_value1, int)
    
    # Test with shouldCheckYield = True  
    new_total_value2 = user_wallet_config.updateAllAssetData(True, sender=switchboard_alpha.address)
    assert isinstance(new_total_value2, int)


def test_update_asset_data_with_lego_id(user_wallet_config, switchboard_alpha, alpha_token):
    """Test updateAssetData with different lego IDs"""
    # Test with lego ID 0 (default)
    new_total_value1 = user_wallet_config.updateAssetData(0, alpha_token.address, False, sender=switchboard_alpha.address)
    assert isinstance(new_total_value1, int)
    
    # Test with lego ID 1 (mock yield lego)
    new_total_value2 = user_wallet_config.updateAssetData(1, alpha_token.address, False, sender=switchboard_alpha.address)
    assert isinstance(new_total_value2, int)


###########################
# Instant Action Settings #
###########################


def test_instant_action_settings_default_all_true(hatchery, bob):
    config = _fresh_wallet_config(hatchery, bob)
    assert instant_action_settings_tuple(config.instantActionSettings()) == (True, True, True, True)
    assert config.pendingInstantActionSettings().confirmBlock == 0


def test_enabling_one_instant_action_flag_stages_pending(hatchery, bob):
    config = _fresh_wallet_config(hatchery, bob)
    config.setInstantActionSettings((False, False, False, False), sender=bob)
    requested = (True, False, False, False)

    config.setInstantActionSettings(requested, sender=bob)

    assert instant_action_settings_tuple(config.instantActionSettings()) == (False, False, False, False)
    pending = config.pendingInstantActionSettings()
    assert instant_action_settings_tuple(pending.settings) == requested
    assert pending.initiatedBlock == boa.env.evm.patch.block_number
    assert pending.confirmBlock == boa.env.evm.patch.block_number + config.timeLock()
    assert pending.currentOwner == bob


def test_confirm_pending_instant_action_settings_before_timelock_reverts(hatchery, bob):
    config = _fresh_wallet_config(hatchery, bob)
    config.setInstantActionSettings((False, False, False, False), sender=bob)
    config.setInstantActionSettings((True, False, False, False), sender=bob)

    with boa.reverts("time delay not reached"):
        config.confirmPendingInstantActionSettings(sender=bob)


def test_confirm_pending_instant_action_settings_after_timelock_applies(hatchery, bob):
    config = _fresh_wallet_config(hatchery, bob)
    config.setInstantActionSettings((False, False, False, False), sender=bob)
    requested = (True, False, True, False)
    config.setInstantActionSettings(requested, sender=bob)

    confirm_pending_instant_action_settings(config, bob)

    assert instant_action_settings_tuple(config.instantActionSettings()) == requested
    assert config.pendingInstantActionSettings().confirmBlock == 0


def test_pending_instant_action_settings_owner_mismatch_blocks_confirm(hatchery, bob, alice):
    config = _fresh_wallet_config(hatchery, bob)
    config.setInstantActionSettings((False, False, False, False), sender=bob)
    config.setInstantActionSettings((True, False, False, False), sender=bob)
    pending = config.pendingInstantActionSettings()

    config.changeOwnership(alice, sender=bob)
    boa.env.time_travel(blocks=config.ownershipTimeLock())
    config.confirmOwnershipChange(sender=alice)
    blocks = max(0, pending.confirmBlock - boa.env.evm.patch.block_number)
    if blocks > 0:
        boa.env.time_travel(blocks=blocks)

    with boa.reverts("owner must match"):
        config.confirmPendingInstantActionSettings(sender=alice)


def test_security_actor_can_cancel_pending_instant_action_settings(
    hatchery, bob, alice, mission_control, switchboard_alpha
):
    config = _fresh_wallet_config(hatchery, bob)
    config.setInstantActionSettings((False, False, False, False), sender=bob)
    config.setInstantActionSettings((True, False, False, False), sender=bob)
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)

    config.cancelPendingInstantActionSettings(sender=alice)

    assert config.pendingInstantActionSettings().confirmBlock == 0
    assert instant_action_settings_tuple(config.instantActionSettings()) == (False, False, False, False)


def test_disabling_only_instant_action_settings_applies_immediately(hatchery, bob):
    config = _fresh_wallet_config(hatchery, bob)
    set_user_instant_action_settings(config, bob, (True, True, False, False))

    config.setInstantActionSettings((False, True, False, False), sender=bob)

    assert instant_action_settings_tuple(config.instantActionSettings()) == (False, True, False, False)
    assert config.pendingInstantActionSettings().confirmBlock == 0


def test_mixed_instant_action_change_disables_immediately_and_stages_enables(hatchery, bob):
    config = _fresh_wallet_config(hatchery, bob)
    set_user_instant_action_settings(config, bob, (True, True, False, False))
    requested = (False, True, True, False)

    config.setInstantActionSettings(requested, sender=bob)

    assert instant_action_settings_tuple(config.instantActionSettings()) == (False, True, False, False)
    pending = config.pendingInstantActionSettings()
    assert instant_action_settings_tuple(pending.settings) == requested
    assert pending.confirmBlock != 0


def test_cancel_pending_mixed_instant_action_change_keeps_immediate_disables(hatchery, bob):
    config = _fresh_wallet_config(hatchery, bob)
    set_user_instant_action_settings(config, bob, (True, True, False, False))

    config.setInstantActionSettings((False, True, True, False), sender=bob)
    config.cancelPendingInstantActionSettings(sender=bob)

    assert instant_action_settings_tuple(config.instantActionSettings()) == (False, True, False, False)
    assert config.pendingInstantActionSettings().confirmBlock == 0


def test_new_instant_action_settings_request_while_pending_exists_reverts(hatchery, bob):
    config = _fresh_wallet_config(hatchery, bob)
    config.setInstantActionSettings((False, False, False, False), sender=bob)
    config.setInstantActionSettings((True, False, False, False), sender=bob)

    with boa.reverts("pending instant settings already exist"):
        config.setInstantActionSettings((False, True, False, False), sender=bob)


def test_resubmitting_current_instant_action_settings_clears_pending(hatchery, bob):
    config = _fresh_wallet_config(hatchery, bob)
    config.setInstantActionSettings((False, False, False, False), sender=bob)
    config.setInstantActionSettings((True, True, False, False), sender=bob)

    # Re-submitting the active settings is the no-enable path and clears stale pending settings.
    config.setInstantActionSettings((False, False, False, False), sender=bob)

    assert instant_action_settings_tuple(config.instantActionSettings()) == (False, False, False, False)
    assert config.pendingInstantActionSettings().confirmBlock == 0


def test_reaffirming_enabled_instant_action_setting_does_not_stage_pending(hatchery, bob):
    config = _fresh_wallet_config(hatchery, bob)
    set_user_instant_action_settings(config, bob, (True, False, False, False))

    config.setInstantActionSettings((True, False, False, False), sender=bob)

    assert instant_action_settings_tuple(config.instantActionSettings()) == (True, False, False, False)
    assert config.pendingInstantActionSettings().confirmBlock == 0


def test_no_change_instant_action_settings_without_pending_noops(hatchery, bob):
    config = _fresh_wallet_config(hatchery, bob)
    before = config.pendingInstantActionSettings()

    config.setInstantActionSettings((True, True, True, True), sender=bob)

    assert instant_action_settings_tuple(config.instantActionSettings()) == (True, True, True, True)
    after = config.pendingInstantActionSettings()
    assert after.initiatedBlock == before.initiatedBlock == 0
    assert after.confirmBlock == before.confirmBlock == 0


def test_instant_action_settings_migrator_setter_sets_active_only(hatchery, bob, migrator):
    config = _fresh_wallet_config(hatchery, bob)
    source_config = _fresh_wallet_config(hatchery, bob)
    config.setInstantActionSettings((False, False, False, False), sender=bob)
    config.setInstantActionSettings((True, False, False, False), sender=bob)
    pending_before = config.pendingInstantActionSettings()

    config.applyMigratedConfigSettings(
        source_config.address,
        config.timeLock(),
        (False, True, False, True),
        config.globalManagerSettings(),
        config.globalPayeeSettings(),
        config.chequeSettings(),
        sender=migrator.address,
    )

    assert instant_action_settings_tuple(config.instantActionSettings()) == (False, True, False, True)
    pending_after = config.pendingInstantActionSettings()
    assert pending_after.confirmBlock == pending_before.confirmBlock
    assert instant_action_settings_tuple(pending_after.settings) == (True, False, False, False)
