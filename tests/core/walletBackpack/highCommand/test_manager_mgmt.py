import pytest
import boa

from constants import ONE_DAY_IN_BLOCKS, ONE_MONTH_IN_BLOCKS, ONE_YEAR_IN_BLOCKS, ZERO_ADDRESS
from conf_utils import filter_logs
from config.BluePrint import PARAMS


###############
# Add Manager #
###############


def test_add_manager_verifies_real_user_wallet(high_command, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test that addManager verifies it's a real user wallet"""
    # Try to add manager to a non-wallet address (bob's EOA)
    with boa.reverts("invalid user wallet"):
        high_command.addManager(
            bob,  # Not a real user wallet, just an EOA
            alice,  # manager
            createManagerLimits(),
            createLegoPerms(),
            createSwapPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],  # allowed assets
            False,  # canClaimLoot
            sender=bob
        )


def test_add_manager_verifies_caller_is_owner(high_command, user_wallet, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, charlie):
    """Test that only the owner can add a manager"""
    # Try to add manager as non-owner (alice)
    with boa.reverts("no perms"):
        high_command.addManager(
            user_wallet,
            charlie,  # manager
            createManagerLimits(),
            createLegoPerms(),
            createSwapPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            False,  # canClaimLoot
            sender=alice  # Not the owner
        )


def test_add_manager_invalid_manager_addresses(high_command, user_wallet, user_wallet_config, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, bob):
    """Test that certain addresses cannot be managers"""
    # Cannot add zero address
    with boa.reverts("invalid manager"):
        high_command.addManager(
            user_wallet,
            ZERO_ADDRESS,  # invalid
            createManagerLimits(),
            createLegoPerms(),
            createSwapPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            False,  # canClaimLoot
            sender=bob
        )
    
    # Cannot add owner as manager
    with boa.reverts("invalid manager"):
        high_command.addManager(
            user_wallet,
            bob,  # owner cannot be manager
            createManagerLimits(),
            createLegoPerms(),
            createSwapPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            False,  # canClaimLoot
            sender=bob
        )
    
    # Cannot add wallet config as manager
    with boa.reverts("invalid manager"):
        high_command.addManager(
            user_wallet,
            user_wallet_config.address,  # invalid
            createManagerLimits(),
            createLegoPerms(),
            createSwapPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            False,  # canClaimLoot
            sender=bob
        )
    
    # Cannot add user wallet itself as manager
    with boa.reverts("invalid manager"):
        high_command.addManager(
            user_wallet,
            user_wallet,  # invalid
            createManagerLimits(),
            createLegoPerms(),
            createSwapPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            False,  # canClaimLoot
            sender=bob
        )


def test_add_manager_validation_failure(high_command, user_wallet, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test that invalid manager settings are rejected"""
    # Invalid limits: per tx > per period
    invalid_limits = createManagerLimits(
        _maxUsdValuePerTx=10000 * 10**6,
        _maxUsdValuePerPeriod=1000 * 10**6
    )
    
    with boa.reverts("invalid manager"):
        high_command.addManager(
            user_wallet,
            alice,
            invalid_limits,
            createLegoPerms(),
            createSwapPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            False,  # canClaimLoot
            sender=bob
        )


def test_add_manager_saves_settings_in_wallet_config(high_command, user_wallet, user_wallet_config, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob, alpha_token, bravo_token):
    """Test that addManager correctly saves all manager settings in user wallet config"""
    # Create specific settings to verify they're saved correctly
    limits = createManagerLimits(
        _maxUsdValuePerTx=1000 * 10**6,
        _maxUsdValuePerPeriod=10000 * 10**6,
        _maxUsdValueLifetime=100000 * 10**6,
        _maxNumTxsPerPeriod=50,
        _txCooldownBlocks=100,
        _failOnZeroPrice=True
    )
    
    lego_perms = createLegoPerms(
        _canManageYield=True,
        _canBuyAndSell=False,
        _allowedLegos=[1, 2]
    )

    swap_perms = createSwapPerms()

    whitelist_perms = createWhitelistPerms(
        _canAddPending=True,
        _canConfirm=True,
        _canCancel=False,
        _canRemove=False
    )

    transfer_perms = createTransferPerms(
        _canTransfer=True,
        _canCreateCheque=False,
        _allowedPayees=[]
    )

    # Add manager with specific settings
    result = high_command.addManager(
        user_wallet,
        alice,
        limits,
        lego_perms,
        swap_perms,
        whitelist_perms,
        transfer_perms,
        [alpha_token.address, bravo_token.address],  # allowed assets
        False,  # canClaimLoot
        ONE_DAY_IN_BLOCKS,  # start delay
        ONE_YEAR_IN_BLOCKS,  # activation length
        sender=bob
    )
    
    assert result == True
    
    # Verify the manager was added by checking the index
    assert user_wallet_config.indexOfManager(alice) != 0
    
    # Get the saved settings
    saved_settings = user_wallet_config.managerSettings(alice)
    
    # Verify timing settings
    expected_start_block = boa.env.evm.patch.block_number + ONE_DAY_IN_BLOCKS
    assert saved_settings.startBlock == expected_start_block
    assert saved_settings.expiryBlock == expected_start_block + ONE_YEAR_IN_BLOCKS
    
    # Verify limits
    assert saved_settings.limits.maxUsdValuePerTx == 1000 * 10**6
    assert saved_settings.limits.maxUsdValuePerPeriod == 10000 * 10**6
    assert saved_settings.limits.maxUsdValueLifetime == 100000 * 10**6
    assert saved_settings.limits.maxNumTxsPerPeriod == 50
    assert saved_settings.limits.txCooldownBlocks == 100
    
    # Verify lego permissions
    assert saved_settings.legoPerms.canManageYield == True
    assert saved_settings.legoPerms.canBuyAndSell == False
    assert len(saved_settings.legoPerms.allowedLegos) == 2
    assert saved_settings.legoPerms.allowedLegos[0] == 1
    assert saved_settings.legoPerms.allowedLegos[1] == 2
    
    # Verify whitelist permissions
    assert saved_settings.whitelistPerms.canAddPending == True
    assert saved_settings.whitelistPerms.canConfirm == True
    assert saved_settings.whitelistPerms.canCancel == False
    assert saved_settings.whitelistPerms.canRemove == False
    
    # Verify transfer permissions
    assert saved_settings.transferPerms.canTransfer == True
    assert saved_settings.transferPerms.canCreateCheque == False
    assert len(saved_settings.transferPerms.allowedPayees) == 0
    
    # Verify allowed assets
    assert len(saved_settings.allowedAssets) == 2
    assert saved_settings.allowedAssets[0] == alpha_token.address
    assert saved_settings.allowedAssets[1] == bravo_token.address


def test_add_manager_emits_event(high_command, user_wallet, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test that addManager emits the correct event"""
    limits = createManagerLimits(
        _maxUsdValuePerTx=2000 * 10**6,
        _maxUsdValuePerPeriod=20000 * 10**6,
        _maxUsdValueLifetime=200000 * 10**6,
        _maxNumTxsPerPeriod=100,
        _txCooldownBlocks=200,
        _failOnZeroPrice=True
    )
    
    # Add manager
    high_command.addManager(
        user_wallet,
        alice,
        limits,
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )
    
    # Get the event
    event = filter_logs(high_command, "ManagerSettingsModified")[0]
    
    # Verify indexed fields
    assert event.user == user_wallet.address
    assert event.manager == alice
    
    # Verify limits in event
    assert event.maxUsdValuePerTx == 2000 * 10**6
    assert event.maxUsdValuePerPeriod == 20000 * 10**6
    assert event.maxUsdValueLifetime == 200000 * 10**6
    assert event.maxNumTxsPerPeriod == 100
    assert event.txCooldownBlocks == 200
    
    # Verify timing
    assert event.startBlock > 0
    assert event.expiryBlock > event.startBlock


def test_add_manager_uses_global_settings_when_zero(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test that zero start delay and activation length use global settings"""
    # Set global manager settings
    global_settings = createGlobalManagerSettings(
        _startDelay=ONE_DAY_IN_BLOCKS * 2,
        _activationLength=ONE_MONTH_IN_BLOCKS * 6
    )
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    # Add manager with zero values (should use global)
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        0,  # start delay
        0,  # activation length
        sender=bob
    )
    
    # Get the saved settings
    saved_settings = user_wallet_config.managerSettings(alice)
    
    # Verify it used global settings
    expected_start_block = boa.env.evm.patch.block_number + (ONE_DAY_IN_BLOCKS * 2)
    assert saved_settings.startBlock == expected_start_block
    assert saved_settings.expiryBlock == expected_start_block + (ONE_MONTH_IN_BLOCKS * 6)


def test_add_manager_increments_index(high_command, user_wallet, user_wallet_config, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, charlie, bob):
    """Test that adding managers increments the index properly"""
    # Check initial state
    assert user_wallet_config.indexOfManager(alice) == 0
    assert user_wallet_config.indexOfManager(charlie) == 0
    
    # Add alice
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )
    
    alice_index = user_wallet_config.indexOfManager(alice)
    assert alice_index > 0
    
    # Add charlie
    high_command.addManager(
        user_wallet,
        charlie,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )
    
    charlie_index = user_wallet_config.indexOfManager(charlie)
    assert charlie_index > alice_index


def test_add_manager_cannot_add_existing_manager(high_command, user_wallet, createGlobalManagerSettings, createManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob, user_wallet_config):
    """Test that cannot add a manager that already exists"""
    # First set global settings
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)

    # Add alice as manager
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )

    # Try to add alice again
    with boa.reverts("invalid manager"):
        high_command.addManager(
            user_wallet,
            alice,
            createManagerLimits(),
            createLegoPerms(),
            createSwapPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            False,  # canClaimLoot
            sender=bob
        )


#################################################
# Add Manager - onlyApprovedYieldOpps Property #
#################################################


def test_add_manager_with_only_approved_yield_opps_true(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test adding manager with onlyApprovedYieldOpps=True saves correctly"""
    # Setup global settings
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)

    # Create lego perms with onlyApprovedYieldOpps=True
    lego_perms = createLegoPerms(
        _canManageYield=True,
        _canBuyAndSell=False,
        _onlyApprovedYieldOpps=True
    )

    # Add manager
    result = high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        lego_perms,
        createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )

    assert result == True

    # Verify the setting was saved correctly
    saved_settings = user_wallet_config.managerSettings(alice)
    assert saved_settings.legoPerms.onlyApprovedYieldOpps == True


def test_add_manager_with_only_approved_yield_opps_false(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test adding manager with onlyApprovedYieldOpps=False saves correctly"""
    # Setup global settings
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)

    # Create lego perms with onlyApprovedYieldOpps=False
    lego_perms = createLegoPerms(
        _canManageYield=True,
        _canBuyAndSell=False,
        _onlyApprovedYieldOpps=False
    )

    # Add manager
    result = high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        lego_perms,
        createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )

    assert result == True

    # Verify the setting was saved correctly
    saved_settings = user_wallet_config.managerSettings(alice)
    assert saved_settings.legoPerms.onlyApprovedYieldOpps == False


##################
# Update Manager #
##################


def test_update_manager_verifies_real_user_wallet(high_command, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test that updateManager verifies it's a real user wallet"""
    # Try to update manager on a non-wallet address (bob's EOA)
    with boa.reverts("invalid user wallet"):
        high_command.updateManager(
            bob,  # Not a real user wallet, just an EOA
            alice,  # manager
            createManagerLimits(),
            createLegoPerms(),
            createSwapPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            False,  # canClaimLoot
            sender=bob
        )


def test_update_manager_verifies_caller_is_owner(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, charlie, bob):
    """Test that only the owner can update a manager"""
    # Setup: add alice as manager
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )
    
    # Try to update manager as non-owner (charlie)
    with boa.reverts("no perms"):
        high_command.updateManager(
            user_wallet,
            alice,
            createManagerLimits(),
            createLegoPerms(),
            createSwapPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            False,  # canClaimLoot
            sender=charlie  # Not the owner
        )


def test_update_manager_must_exist(high_command, user_wallet, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test that can only update existing managers"""
    # Try to update a non-existent manager
    with boa.reverts("invalid settings"):
        high_command.updateManager(
            user_wallet,
            alice,  # not a manager
            createManagerLimits(),
            createLegoPerms(),
            createSwapPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            False,  # canClaimLoot
            sender=bob
        )


def test_update_manager_validation_failure(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test that invalid manager settings are rejected on update"""
    # Setup: add alice as manager
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )
    
    # Try to update with invalid limits
    invalid_limits = createManagerLimits(
        _maxUsdValuePerTx=10000 * 10**6,
        _maxUsdValuePerPeriod=1000 * 10**6  # invalid: per tx > per period
    )
    
    with boa.reverts("invalid settings"):
        high_command.updateManager(
            user_wallet,
            alice,
            invalid_limits,
            createLegoPerms(),
            createSwapPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            False,  # canClaimLoot
            sender=bob
        )


def test_update_manager_saves_new_settings(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob, alpha_token, bravo_token, charlie_token):
    """Test that updateManager correctly saves all new settings"""
    # Setup: add alice as manager with initial settings
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    initial_limits = createManagerLimits(
        _maxUsdValuePerTx=500 * 10**6,
        _maxUsdValuePerPeriod=5000 * 10**6,
        _failOnZeroPrice=True
    )
    
    high_command.addManager(
        user_wallet,
        alice,
        initial_limits,
        createLegoPerms(_canManageYield=True, _canBuyAndSell=False),
        createSwapPerms(),
        createWhitelistPerms(_canAddPending=False, _canConfirm=True),
        createTransferPerms(_canTransfer=False, _canCreateCheque=True),
        [alpha_token.address],
        False,  # canClaimLoot
        sender=bob
    )
    
    # Get initial settings to verify timing doesn't change
    initial_settings = user_wallet_config.managerSettings(alice)
    initial_start_block = initial_settings.startBlock
    initial_expiry_block = initial_settings.expiryBlock
    
    # Advance some blocks to ensure update happens at a different block
    boa.env.time_travel(blocks=100)
    
    # Update with new settings
    new_limits = createManagerLimits(
        _maxUsdValuePerTx=1000 * 10**6,
        _maxUsdValuePerPeriod=10000 * 10**6,
        _maxUsdValueLifetime=100000 * 10**6,
        _maxNumTxsPerPeriod=75,
        _txCooldownBlocks=150,
        _failOnZeroPrice=True
    )
    
    new_lego_perms = createLegoPerms(
        _canManageYield=False,
        _canBuyAndSell=True,
        _canManageDebt=True,
        _allowedLegos=[1, 2]
    )

    new_swap_perms = createSwapPerms()

    new_whitelist_perms = createWhitelistPerms(
        _canAddPending=True,
        _canConfirm=False,
        _canCancel=True,
        _canRemove=False
    )

    new_transfer_perms = createTransferPerms(
        _canTransfer=True,
        _canCreateCheque=False,
        _canAddPendingPayee=True,
        _allowedPayees=[]  # Use empty list instead of token address
    )

    result = high_command.updateManager(
        user_wallet,
        alice,
        new_limits,
        new_lego_perms,
        new_swap_perms,
        new_whitelist_perms,
        new_transfer_perms,
        [bravo_token.address, charlie_token.address],
        False,  # canClaimLoot
        sender=bob
    )
    
    assert result == True
    
    # Get updated settings
    updated_settings = user_wallet_config.managerSettings(alice)
    
    # Verify timing didn't change
    assert updated_settings.startBlock == initial_start_block
    assert updated_settings.expiryBlock == initial_expiry_block
    
    # Verify new limits
    assert updated_settings.limits.maxUsdValuePerTx == 1000 * 10**6
    assert updated_settings.limits.maxUsdValuePerPeriod == 10000 * 10**6
    assert updated_settings.limits.maxUsdValueLifetime == 100000 * 10**6
    assert updated_settings.limits.maxNumTxsPerPeriod == 75
    assert updated_settings.limits.txCooldownBlocks == 150
    
    # Verify new lego permissions
    assert updated_settings.legoPerms.canManageYield == False
    assert updated_settings.legoPerms.canBuyAndSell == True
    assert updated_settings.legoPerms.canManageDebt == True
    assert len(updated_settings.legoPerms.allowedLegos) == 2
    assert updated_settings.legoPerms.allowedLegos[0] == 1
    assert updated_settings.legoPerms.allowedLegos[1] == 2
    
    # Verify new whitelist permissions
    assert updated_settings.whitelistPerms.canAddPending == True
    assert updated_settings.whitelistPerms.canConfirm == False
    assert updated_settings.whitelistPerms.canCancel == True
    assert updated_settings.whitelistPerms.canRemove == False
    
    # Verify new transfer permissions
    assert updated_settings.transferPerms.canTransfer == True
    assert updated_settings.transferPerms.canCreateCheque == False
    assert updated_settings.transferPerms.canAddPendingPayee == True
    assert len(updated_settings.transferPerms.allowedPayees) == 0
    
    # Verify new allowed assets
    assert len(updated_settings.allowedAssets) == 2
    assert updated_settings.allowedAssets[0] == bravo_token.address
    assert updated_settings.allowedAssets[1] == charlie_token.address


def test_update_manager_emits_event(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test that updateManager emits the correct event"""
    # Setup: add alice as manager
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )
    
    # Update with new limits
    new_limits = createManagerLimits(
        _maxUsdValuePerTx=3000 * 10**6,
        _maxUsdValuePerPeriod=30000 * 10**6,
        _maxUsdValueLifetime=300000 * 10**6,
        _maxNumTxsPerPeriod=150,
        _txCooldownBlocks=300,
        _failOnZeroPrice=True
    )
    
    # Update manager
    high_command.updateManager(
        user_wallet,
        alice,
        new_limits,
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )
    
    # Get the event from update
    events = filter_logs(high_command, "ManagerSettingsModified")
    assert len(events) == 1
    event = events[0]  # The update event
    
    # Verify indexed fields
    assert event.user == user_wallet.address
    assert event.manager == alice
    
    # Verify new limits in event
    assert event.maxUsdValuePerTx == 3000 * 10**6
    assert event.maxUsdValuePerPeriod == 30000 * 10**6
    assert event.maxUsdValueLifetime == 300000 * 10**6
    assert event.maxNumTxsPerPeriod == 150
    assert event.txCooldownBlocks == 300


def test_update_manager_preserves_timing(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test that updating a manager preserves start and expiry blocks"""
    # Setup: add alice as manager with specific timing
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        ONE_DAY_IN_BLOCKS * 3,  # start delay
        ONE_YEAR_IN_BLOCKS * 2,  # activation length
        sender=bob
    )
    
    # Get initial timing
    initial_settings = user_wallet_config.managerSettings(alice)
    initial_start = initial_settings.startBlock
    initial_expiry = initial_settings.expiryBlock
    
    # Advance some blocks to ensure update happens at a different block
    boa.env.time_travel(blocks=50)
    
    # Update manager
    high_command.updateManager(
        user_wallet,
        alice,
        createManagerLimits(_maxUsdValuePerTx=5000 * 10**6, _failOnZeroPrice=True),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )
    
    # Verify timing unchanged
    updated_settings = user_wallet_config.managerSettings(alice)
    assert updated_settings.startBlock == initial_start
    assert updated_settings.expiryBlock == initial_expiry


def test_update_manager_index_unchanged(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test that updating a manager doesn't change their index"""
    # Setup: add alice as manager
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)

    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )

    # Get initial index
    initial_index = user_wallet_config.indexOfManager(alice)

    # Advance some blocks to ensure update happens at a different block
    boa.env.time_travel(blocks=25)

    # Update manager
    high_command.updateManager(
        user_wallet,
        alice,
        createManagerLimits(_maxUsdValuePerTx=5000 * 10**6, _failOnZeroPrice=True),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )

    # Verify index unchanged
    assert user_wallet_config.indexOfManager(alice) == initial_index


####################################################
# Update Manager - onlyApprovedYieldOpps Property #
####################################################


def test_update_manager_changes_only_approved_yield_opps_false_to_true(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test updating onlyApprovedYieldOpps from False to True"""
    # Setup: add alice as manager with onlyApprovedYieldOpps=False
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)

    initial_lego_perms = createLegoPerms(
        _canManageYield=True,
        _onlyApprovedYieldOpps=False
    )

    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        initial_lego_perms,
        createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )

    # Verify initial setting
    initial_settings = user_wallet_config.managerSettings(alice)
    assert initial_settings.legoPerms.onlyApprovedYieldOpps == False

    # Update to True
    updated_lego_perms = createLegoPerms(
        _canManageYield=True,
        _onlyApprovedYieldOpps=True
    )

    result = high_command.updateManager(
        user_wallet,
        alice,
        createManagerLimits(),
        updated_lego_perms,
        createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )

    assert result == True

    # Verify the update
    updated_settings = user_wallet_config.managerSettings(alice)
    assert updated_settings.legoPerms.onlyApprovedYieldOpps == True


def test_update_manager_changes_only_approved_yield_opps_true_to_false(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test updating onlyApprovedYieldOpps from True to False"""
    # Setup: add alice as manager with onlyApprovedYieldOpps=True
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)

    initial_lego_perms = createLegoPerms(
        _canManageYield=True,
        _onlyApprovedYieldOpps=True
    )

    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        initial_lego_perms,
        createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )

    # Verify initial setting
    initial_settings = user_wallet_config.managerSettings(alice)
    assert initial_settings.legoPerms.onlyApprovedYieldOpps == True

    # Update to False
    updated_lego_perms = createLegoPerms(
        _canManageYield=True,
        _onlyApprovedYieldOpps=False
    )

    result = high_command.updateManager(
        user_wallet,
        alice,
        createManagerLimits(),
        updated_lego_perms,
        createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )

    assert result == True

    # Verify the update
    updated_settings = user_wallet_config.managerSettings(alice)
    assert updated_settings.legoPerms.onlyApprovedYieldOpps == False


##################
# Remove Manager #
##################


def test_remove_manager_verifies_real_user_wallet(high_command, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test that removeManager verifies it's a real user wallet"""
    # Try to remove manager from a non-wallet address (bob's EOA)
    with boa.reverts("invalid user wallet"):
        high_command.removeManager(
            bob,  # Not a real user wallet, just an EOA
            alice,  # manager
            sender=bob
        )


def test_remove_manager_by_owner(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test that owner can remove a manager"""
    # Setup: add alice as manager
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )
    
    # Verify alice is a manager
    assert user_wallet_config.indexOfManager(alice) != 0
    
    # Remove alice as owner
    result = high_command.removeManager(
        user_wallet,
        alice,
        sender=bob  # owner
    )
    
    assert result == True
    
    # Verify alice is no longer a manager
    assert user_wallet_config.indexOfManager(alice) == 0


def test_remove_manager_by_self(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test that a manager can remove themselves"""
    # Setup: add alice as manager
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )
    
    # Verify alice is a manager
    assert user_wallet_config.indexOfManager(alice) != 0
    
    # Remove alice as themselves
    result = high_command.removeManager(
        user_wallet,
        alice,
        sender=alice  # manager removing themselves
    )
    
    assert result == True
    
    # Verify alice is no longer a manager
    assert user_wallet_config.indexOfManager(alice) == 0


def test_remove_manager_by_unauthorized(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob, charlie):
    """Test that unauthorized users cannot remove a manager"""
    # Setup: add alice as manager
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )
    
    # Try to remove alice as unauthorized user
    with boa.reverts("no perms"):
        high_command.removeManager(
            user_wallet,
            alice,
            sender=charlie  # not owner, not manager, not security
        )


def test_remove_manager_by_security_admin(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob, charlie, mission_control, switchboard_alpha):
    """Test that security admin can remove a manager"""
    # Set charlie as security operator
    mission_control.setCanPerformSecurityAction(charlie, True, sender=switchboard_alpha.address)
    
    # Setup: add alice as manager
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )
    
    # Verify alice is a manager
    assert user_wallet_config.indexOfManager(alice) != 0
    
    # Remove alice as security admin (charlie)
    result = high_command.removeManager(
        user_wallet,
        alice,
        sender=charlie  # security admin
    )
    
    assert result == True
    
    # Verify alice is no longer a manager
    assert user_wallet_config.indexOfManager(alice) == 0


def test_remove_manager_not_found(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, alice, bob):
    """Test that cannot remove a non-existent manager"""
    # Setup: set global settings but don't add alice as manager
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    # Try to remove alice who is not a manager
    with boa.reverts("manager not found"):
        high_command.removeManager(
            user_wallet,
            alice,  # not a manager
            sender=bob
        )


def test_remove_manager_emits_event(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test that removeManager emits the correct event"""
    # Setup: add alice as manager
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )
    
    # Remove manager
    high_command.removeManager(
        user_wallet,
        alice,
        sender=bob
    )
    
    # Get the event
    events = filter_logs(high_command, "ManagerRemoved")
    assert len(events) == 1
    event = events[0]
    
    # Verify event fields
    assert event.user == user_wallet.address
    assert event.manager == alice


def test_remove_manager_clears_all_settings(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob, alpha_token):
    """Test that removing a manager clears all their settings"""
    # Setup: add alice as manager with specific settings
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(
            _maxUsdValuePerTx=1000 * 10**6,
            _maxNumTxsPerPeriod=50,
            _failOnZeroPrice=True
        ),
        createLegoPerms(_canManageYield=True, _allowedLegos=[1, 2]),
        createSwapPerms(),
        createWhitelistPerms(_canAddPending=True),
        createTransferPerms(_canTransfer=True),
        [alpha_token.address],
        False,  # canClaimLoot
        sender=bob
    )
    
    # Verify settings exist
    settings_before = user_wallet_config.managerSettings(alice)
    assert settings_before.limits.maxUsdValuePerTx == 1000 * 10**6
    assert settings_before.startBlock > 0
    
    # Remove manager
    high_command.removeManager(
        user_wallet,
        alice,
        sender=bob
    )
    
    # Verify settings are cleared
    settings_after = user_wallet_config.managerSettings(alice)
    assert settings_after.startBlock == 0
    assert settings_after.expiryBlock == 0
    assert settings_after.limits.maxUsdValuePerTx == 0
    assert len(settings_after.allowedAssets) == 0
    assert len(settings_after.legoPerms.allowedLegos) == 0


def test_remove_manager_updates_indices(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, charlie, bob):
    """Test that removing a manager properly updates indices"""
    # Setup: add multiple managers
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    # Add alice
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )
    
    # Add charlie
    high_command.addManager(
        user_wallet,
        charlie,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )
    
    # Get initial indices
    alice_index_before = user_wallet_config.indexOfManager(alice)
    charlie_index_before = user_wallet_config.indexOfManager(charlie)
    
    assert alice_index_before > 0
    assert charlie_index_before > alice_index_before
    
    # Remove alice (first manager)
    high_command.removeManager(
        user_wallet,
        alice,
        sender=bob
    )
    
    # Verify alice index is 0
    assert user_wallet_config.indexOfManager(alice) == 0
    
    # Charlie's index should have changed (moved to alice's position)
    charlie_index_after = user_wallet_config.indexOfManager(charlie)
    assert charlie_index_after == alice_index_before


def test_remove_multiple_managers_sequentially(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, charlie, sally, bob):
    """Test removing multiple managers one by one"""
    # Setup: add three managers
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    managers = [alice, charlie, sally]
    for manager in managers:
        high_command.addManager(
            user_wallet,
            manager,
            createManagerLimits(),
            createLegoPerms(),
            createSwapPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            False,  # canClaimLoot
            sender=bob
        )
    
    # Verify all are managers
    for manager in managers:
        assert user_wallet_config.indexOfManager(manager) != 0
    
    # Remove managers one by one
    for manager in managers:
        high_command.removeManager(
            user_wallet,
            manager,
            sender=bob
        )
        
        # Verify manager is removed
        assert user_wallet_config.indexOfManager(manager) == 0


#####################
# Adjust Activation #
#####################


def test_adjust_activation_length_verifies_real_user_wallet(high_command, alice, bob):
    """Test that adjustManagerActivationLength verifies it's a real user wallet"""
    # Try to adjust on a non-wallet address (bob's EOA)
    with boa.reverts("invalid user wallet"):
        high_command.adjustManagerActivationLength(
            bob,  # Not a real user wallet, just an EOA
            alice,  # manager
            ONE_YEAR_IN_BLOCKS,  # new activation length
            sender=bob
        )


def test_adjust_activation_length_verifies_caller_is_owner(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob, charlie):
    """Test that only the owner can adjust manager activation length"""
    # Setup: add alice as manager
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )
    
    # Advance blocks to make manager active
    boa.env.time_travel(blocks=100)
    
    # Try to adjust as non-owner
    with boa.reverts("no perms"):
        high_command.adjustManagerActivationLength(
            user_wallet,
            alice,
            ONE_YEAR_IN_BLOCKS * 2,
            sender=charlie  # Not the owner
        )


def test_adjust_activation_length_manager_must_exist(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, alice, bob):
    """Test that can only adjust activation for existing managers"""
    # Setup: set global settings but don't add alice as manager
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    # Try to adjust for non-existent manager
    with boa.reverts("no manager found"):
        high_command.adjustManagerActivationLength(
            user_wallet,
            alice,  # not a manager
            ONE_YEAR_IN_BLOCKS,
            sender=bob
        )


def test_adjust_activation_length_manager_not_active_yet(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test that cannot adjust activation for manager not yet active"""
    # Setup: add alice as manager with future start block
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        ONE_DAY_IN_BLOCKS * 7,  # Start in 7 days
        ONE_YEAR_IN_BLOCKS,
        sender=bob
    )
    
    # Try to adjust before manager is active
    with boa.reverts("manager not active yet"):
        high_command.adjustManagerActivationLength(
            user_wallet,
            alice,
            ONE_YEAR_IN_BLOCKS * 2,
            sender=bob
        )


def test_adjust_activation_length_invalid_length(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob, fork):
    """Test that invalid activation lengths are rejected"""
    # Setup: add alice as manager with immediate start
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    # Get the current block before adding manager
    current_block = boa.env.evm.patch.block_number
    
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        0,  # Start immediately (will use global start delay)
        ONE_MONTH_IN_BLOCKS,
        sender=bob
    )
    
    # Get the actual start block
    settings = user_wallet_config.managerSettings(alice)
    
    # Advance to after the start block so manager is active
    blocks_to_advance = settings.startBlock - current_block + 100
    boa.env.time_travel(blocks=blocks_to_advance)
    
    # Try with activation length too short (less than MIN)
    with boa.reverts("invalid activation length"):
        high_command.adjustManagerActivationLength(
            user_wallet,
            alice,
            PARAMS[fork]["BOSS_MIN_ACTIVATION_LENGTH"] - 1,  # Just below minimum
            sender=bob
        )
    
    # Try with activation length too long (more than MAX)
    with boa.reverts("invalid activation length"):
        high_command.adjustManagerActivationLength(
            user_wallet,
            alice,
            PARAMS[fork]["BOSS_MAX_ACTIVATION_LENGTH"] + 1,  # Just above maximum
            sender=bob
        )


def test_adjust_activation_length_extends_active_manager(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test extending activation length for active manager"""
    # Setup: add alice as manager
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    # Get current block before adding
    current_block = boa.env.evm.patch.block_number
    
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        0,  # start delay
        ONE_MONTH_IN_BLOCKS,  # activation length
        sender=bob
    )
    
    # Get initial settings
    initial_settings = user_wallet_config.managerSettings(alice)
    initial_start = initial_settings.startBlock
    initial_expiry = initial_settings.expiryBlock
    
    # Advance to after start block to make manager active
    blocks_to_advance = initial_start - current_block + 100
    boa.env.time_travel(blocks=blocks_to_advance)
    
    # Extend activation length
    new_activation_length = ONE_YEAR_IN_BLOCKS
    result = high_command.adjustManagerActivationLength(
        user_wallet,
        alice,
        new_activation_length,
        False,  # Don't reset start block
        sender=bob
    )
    
    assert result == True
    
    # Verify settings
    updated_settings = user_wallet_config.managerSettings(alice)
    assert updated_settings.startBlock == initial_start  # Start block unchanged
    assert updated_settings.expiryBlock == initial_start + new_activation_length  # New expiry


def test_adjust_activation_length_with_reset_start_block(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test adjusting activation with reset start block flag"""
    # Setup: add alice as manager
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    # Get current block
    initial_block = boa.env.evm.patch.block_number
    
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )
    
    # Get the manager's start block
    settings = user_wallet_config.managerSettings(alice)
    start_block = settings.startBlock
    
    # Advance past the start block significantly
    blocks_to_advance = start_block - initial_block + 1000
    boa.env.time_travel(blocks=blocks_to_advance)
    
    current_block = boa.env.evm.patch.block_number
    
    # Adjust with reset flag
    new_activation_length = ONE_YEAR_IN_BLOCKS * 2
    result = high_command.adjustManagerActivationLength(
        user_wallet,
        alice,
        new_activation_length,
        True,  # Reset start block to current
        sender=bob
    )
    
    assert result == True
    
    # Verify settings
    updated_settings = user_wallet_config.managerSettings(alice)
    assert updated_settings.startBlock == current_block  # Reset to current block
    assert updated_settings.expiryBlock == current_block + new_activation_length


def test_adjust_activation_length_expired_manager_auto_resets(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test that adjusting expired manager automatically resets start block"""
    # Setup: add alice as manager with short activation
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    initial_block = boa.env.evm.patch.block_number
    
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        0,  # start delay
        ONE_DAY_IN_BLOCKS,  # activation length
        sender=bob
    )
    
    # Get the settings to know when it expires
    settings = user_wallet_config.managerSettings(alice)
    start_block = settings.startBlock
    expiry_block = settings.expiryBlock
    
    # Advance past expiry
    blocks_to_advance = expiry_block - initial_block + 100
    boa.env.time_travel(blocks=blocks_to_advance)
    
    current_block = boa.env.evm.patch.block_number
    
    # Adjust expired manager (should auto-reset even with False flag)
    new_activation_length = ONE_YEAR_IN_BLOCKS
    result = high_command.adjustManagerActivationLength(
        user_wallet,
        alice,
        new_activation_length,
        False,  # Don't explicitly reset, but it should auto-reset
        sender=bob
    )
    
    assert result == True
    
    # Verify settings - should be reset despite False flag
    updated_settings = user_wallet_config.managerSettings(alice)
    assert updated_settings.startBlock == current_block  # Auto-reset to current
    assert updated_settings.expiryBlock == current_block + new_activation_length


def test_adjust_activation_length_emits_event(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test that adjustManagerActivationLength emits correct event"""
    # Setup: add alice as manager
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    initial_block = boa.env.evm.patch.block_number
    
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )
    
    # Get the start block and advance past it
    settings = user_wallet_config.managerSettings(alice)
    blocks_to_advance = settings.startBlock - initial_block + 100
    boa.env.time_travel(blocks=blocks_to_advance)
    
    # Adjust without reset
    new_activation_length = ONE_YEAR_IN_BLOCKS * 2
    high_command.adjustManagerActivationLength(
        user_wallet,
        alice,
        new_activation_length,
        False,
        sender=bob
    )
    
    # Get event
    events = filter_logs(high_command, "ManagerActivationLengthAdjusted")
    assert len(events) == 1
    event = events[0]
    
    # Verify event fields
    assert event.user == user_wallet.address
    assert event.manager == alice
    assert event.activationLength == new_activation_length
    assert event.didRestart == False  # No restart


def test_adjust_activation_length_emits_event_with_restart(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test event emission when restart occurs"""
    # Setup: add alice as manager
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    initial_block = boa.env.evm.patch.block_number
    
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )
    
    # Get the start block and advance past it
    settings = user_wallet_config.managerSettings(alice)
    blocks_to_advance = settings.startBlock - initial_block + 100
    boa.env.time_travel(blocks=blocks_to_advance)
    
    # Adjust with reset flag
    new_activation_length = ONE_YEAR_IN_BLOCKS
    high_command.adjustManagerActivationLength(
        user_wallet,
        alice,
        new_activation_length,
        True,  # Force restart
        sender=bob
    )
    
    # Get event
    events = filter_logs(high_command, "ManagerActivationLengthAdjusted")
    assert len(events) == 1
    event = events[0]
    
    # Verify event shows restart
    assert event.user == user_wallet.address
    assert event.manager == alice
    assert event.activationLength == new_activation_length
    assert event.didRestart == True  # Restarted



def test_adjust_activation_length_invalid_expiry(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob, fork):
    """Test that adjustment resulting in invalid expiry is rejected"""
    # Setup: add alice as manager
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    initial_block = boa.env.evm.patch.block_number
    
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )
    
    # Get the settings
    settings = user_wallet_config.managerSettings(alice)
    initial_start = settings.startBlock
    
    # Advance way past the start block - enough that minimum activation would expire
    min_activation = PARAMS[fork]["BOSS_MIN_ACTIVATION_LENGTH"]
    blocks_to_advance = initial_start - initial_block + min_activation + 100
    boa.env.time_travel(blocks=blocks_to_advance)
    
    # Try to set minimum activation that would make expiry in the past
    with boa.reverts("invalid expiry block"):
        high_command.adjustManagerActivationLength(
            user_wallet,
            alice,
            min_activation,  # This would make expiry in the past
            False,  # Don't reset start
            sender=bob
        )


def test_adjust_activation_length_shortens_active_manager(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test shortening activation length for active manager"""
    # Setup: add alice as manager with long activation
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    current_block = boa.env.evm.patch.block_number
    
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        0,  # Start immediately
        ONE_YEAR_IN_BLOCKS * 2,  # Long initial activation
        sender=bob
    )
    
    # Get initial settings
    initial_settings = user_wallet_config.managerSettings(alice)
    initial_start = initial_settings.startBlock
    
    # Advance to make manager active
    blocks_to_advance = initial_start - current_block + 100
    boa.env.time_travel(blocks=blocks_to_advance)
    
    # Shorten activation length
    new_activation_length = ONE_MONTH_IN_BLOCKS * 6  # Shorter than initial
    result = high_command.adjustManagerActivationLength(
        user_wallet,
        alice,
        new_activation_length,
        False,
        sender=bob
    )
    
    assert result == True
    
    # Verify settings
    updated_settings = user_wallet_config.managerSettings(alice)
    assert updated_settings.startBlock == initial_start  # Start unchanged
    assert updated_settings.expiryBlock == initial_start + new_activation_length  # Shortened


def test_adjust_activation_length_boundary_values(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob, fork):
    """Test setting exactly MIN and MAX activation lengths"""
    # Setup: add alice as manager
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    current_block = boa.env.evm.patch.block_number
    
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )
    
    # Get settings and advance to active
    settings = user_wallet_config.managerSettings(alice)
    blocks_to_advance = settings.startBlock - current_block + 100
    boa.env.time_travel(blocks=blocks_to_advance)
    
    # Test MIN activation length
    min_activation = PARAMS[fork]["BOSS_MIN_ACTIVATION_LENGTH"]
    result = high_command.adjustManagerActivationLength(
        user_wallet,
        alice,
        min_activation,  # Exactly minimum
        False,
        sender=bob
    )
    assert result == True
    
    # Verify MIN was set
    updated_settings = user_wallet_config.managerSettings(alice)
    assert updated_settings.expiryBlock == updated_settings.startBlock + min_activation
    
    # Test MAX activation length
    max_activation = PARAMS[fork]["BOSS_MAX_ACTIVATION_LENGTH"]
    result = high_command.adjustManagerActivationLength(
        user_wallet,
        alice,
        max_activation,  # Exactly maximum
        False,
        sender=bob
    )
    assert result == True
    
    # Verify MAX was set
    final_settings = user_wallet_config.managerSettings(alice)
    assert final_settings.expiryBlock == final_settings.startBlock + max_activation


def test_adjust_activation_length_near_expiry_manager(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test adjusting manager who is near expiry but not yet expired"""
    # Setup: add alice as manager with short activation
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    initial_block = boa.env.evm.patch.block_number
    
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        0,
        ONE_DAY_IN_BLOCKS * 2,  # Short activation
        sender=bob
    )
    
    # Get settings
    settings = user_wallet_config.managerSettings(alice)
    expiry_block = settings.expiryBlock
    
    # Advance to 10 blocks before expiry
    blocks_to_advance = expiry_block - initial_block - 10
    boa.env.time_travel(blocks=blocks_to_advance)
    
    # Extend activation when near expiry
    new_activation_length = ONE_YEAR_IN_BLOCKS
    result = high_command.adjustManagerActivationLength(
        user_wallet,
        alice,
        new_activation_length,
        False,
        sender=bob
    )
    
    assert result == True
    
    # Verify extension worked
    updated_settings = user_wallet_config.managerSettings(alice)
    assert updated_settings.expiryBlock > boa.env.evm.patch.block_number  # Still valid
    assert updated_settings.expiryBlock == updated_settings.startBlock + new_activation_length


def test_adjust_activation_length_multiple_adjustments(high_command, user_wallet, user_wallet_config, createGlobalManagerSettings, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test multiple consecutive adjustments to the same manager"""
    # Setup: add alice as manager
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)
    
    current_block = boa.env.evm.patch.block_number
    
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )
    
    # Get settings and advance to active
    settings = user_wallet_config.managerSettings(alice)
    initial_start = settings.startBlock
    blocks_to_advance = initial_start - current_block + 100
    boa.env.time_travel(blocks=blocks_to_advance)
    
    # First adjustment - extend
    high_command.adjustManagerActivationLength(
        user_wallet,
        alice,
        ONE_YEAR_IN_BLOCKS,
        False,
        sender=bob
    )
    
    # Second adjustment - shorten
    high_command.adjustManagerActivationLength(
        user_wallet,
        alice,
        ONE_MONTH_IN_BLOCKS * 6,
        False,
        sender=bob
    )
    
    # Third adjustment - extend again with reset
    boa.env.time_travel(blocks=1000)
    current_block_after = boa.env.evm.patch.block_number
    
    high_command.adjustManagerActivationLength(
        user_wallet,
        alice,
        ONE_YEAR_IN_BLOCKS * 2,
        True,  # Reset this time
        sender=bob
    )
    
    # Verify final state
    final_settings = user_wallet_config.managerSettings(alice)
    assert final_settings.startBlock == current_block_after  # Reset worked
    assert final_settings.expiryBlock == current_block_after + ONE_YEAR_IN_BLOCKS * 2


###########################
# Global Manager Settings #
###########################


def test_set_global_manager_settings_verifies_real_user_wallet(high_command, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test that setGlobalManagerSettings verifies it's a real user wallet"""
    # Try to set global settings on a non-wallet address (bob's EOA)
    with boa.reverts("invalid user wallet"):
        high_command.setGlobalManagerSettings(
            bob,  # Not a real user wallet, just an EOA
            ONE_MONTH_IN_BLOCKS,  # managerPeriod
            ONE_DAY_IN_BLOCKS // 2,  # startDelay
            ONE_YEAR_IN_BLOCKS,  # activationLength
            True,  # canOwnerManage
            createManagerLimits(),
            createLegoPerms(),
            createSwapPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],  # allowedAssets
            sender=bob
        )


def test_set_global_manager_settings_verifies_caller_is_owner(high_command, user_wallet, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test that only the owner can set global manager settings"""
    # Try to set global settings as non-owner
    with boa.reverts("no perms"):
        high_command.setGlobalManagerSettings(
            user_wallet,
            ONE_MONTH_IN_BLOCKS,
            ONE_DAY_IN_BLOCKS // 2,
            ONE_YEAR_IN_BLOCKS,
            True,
            createManagerLimits(),
            createLegoPerms(),
            createSwapPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            sender=alice  # Not the owner
        )


def test_set_global_manager_settings_basic(high_command, user_wallet, user_wallet_config, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alpha_token, bravo_token, bob):
    """Test setting basic global manager settings"""
    # Set up custom limits
    limits = createManagerLimits(
        _maxUsdValuePerTx=1000 * 10**6,
        _maxUsdValuePerPeriod=10000 * 10**6,
        _maxUsdValueLifetime=100000 * 10**6,
        _maxNumTxsPerPeriod=50,
        _txCooldownBlocks=100,
        _failOnZeroPrice=True
    )
    
    # Set up lego permissions
    lego_perms = createLegoPerms(
        _canManageYield=True,
        _canBuyAndSell=True,
        _canManageDebt=False,
        _canManageLiq=True,
        _canClaimRewards=True,
        _allowedLegos=[1, 2]
    )

    # Set up swap permissions
    swap_perms = createSwapPerms()

    # Set up whitelist permissions
    whitelist_perms = createWhitelistPerms(
        _canAddPending=True,
        _canConfirm=True,
        _canCancel=False,
        _canRemove=False
    )

    # Set up transfer permissions
    transfer_perms = createTransferPerms(
        _canTransfer=True,
        _canCreateCheque=False,
        _canAddPendingPayee=True,
        _allowedPayees=[]
    )

    # Set global manager settings
    result = high_command.setGlobalManagerSettings(
        user_wallet,
        ONE_MONTH_IN_BLOCKS * 2,  # managerPeriod
        ONE_DAY_IN_BLOCKS,  # startDelay
        ONE_YEAR_IN_BLOCKS // 2,  # activationLength
        False,  # canOwnerManage
        limits,
        lego_perms,
        swap_perms,
        whitelist_perms,
        transfer_perms,
        [alpha_token.address, bravo_token.address],  # allowedAssets
        sender=bob
    )
    
    assert result == True
    
    # Verify settings were applied
    global_settings = user_wallet_config.globalManagerSettings()
    
    # Check basic settings
    assert global_settings.managerPeriod == ONE_MONTH_IN_BLOCKS * 2
    assert global_settings.startDelay == ONE_DAY_IN_BLOCKS
    assert global_settings.activationLength == ONE_YEAR_IN_BLOCKS // 2
    assert global_settings.canOwnerManage == False
    
    # Check limits
    assert global_settings.limits.maxUsdValuePerTx == 1000 * 10**6
    assert global_settings.limits.maxUsdValuePerPeriod == 10000 * 10**6
    assert global_settings.limits.maxUsdValueLifetime == 100000 * 10**6
    assert global_settings.limits.maxNumTxsPerPeriod == 50
    assert global_settings.limits.txCooldownBlocks == 100
    assert global_settings.limits.failOnZeroPrice == True
    
    # Check lego permissions
    assert global_settings.legoPerms.canManageYield == True
    assert global_settings.legoPerms.canBuyAndSell == True
    assert global_settings.legoPerms.canManageDebt == False
    assert global_settings.legoPerms.canManageLiq == True
    assert global_settings.legoPerms.canClaimRewards == True
    assert len(global_settings.legoPerms.allowedLegos) == 2
    assert global_settings.legoPerms.allowedLegos[0] == 1
    assert global_settings.legoPerms.allowedLegos[1] == 2
    
    # Check whitelist permissions
    assert global_settings.whitelistPerms.canAddPending == True
    assert global_settings.whitelistPerms.canConfirm == True
    assert global_settings.whitelistPerms.canCancel == False
    assert global_settings.whitelistPerms.canRemove == False
    
    # Check transfer permissions
    assert global_settings.transferPerms.canTransfer == True
    assert global_settings.transferPerms.canCreateCheque == False
    assert global_settings.transferPerms.canAddPendingPayee == True
    assert len(global_settings.transferPerms.allowedPayees) == 0
    
    # Check allowed assets
    assert len(global_settings.allowedAssets) == 2
    assert global_settings.allowedAssets[0] == alpha_token.address
    assert global_settings.allowedAssets[1] == bravo_token.address


def test_set_global_manager_settings_emits_event(high_command, user_wallet, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, bob):
    """Test that setGlobalManagerSettings emits the correct event"""
    limits = createManagerLimits(
        _maxUsdValuePerTx=2000 * 10**6,
        _maxUsdValuePerPeriod=20000 * 10**6,
        _maxUsdValueLifetime=200000 * 10**6,
        _maxNumTxsPerPeriod=100,
        _txCooldownBlocks=200,
        _failOnZeroPrice=True
    )
    
    lego_perms = createLegoPerms(
        _canManageYield=False,
        _canBuyAndSell=True,
        _canManageDebt=True,
        _canManageLiq=False,
        _canClaimRewards=True,
        _allowedLegos=[]
    )

    swap_perms = createSwapPerms()

    whitelist_perms = createWhitelistPerms(
        _canAddPending=False,
        _canConfirm=True,
        _canCancel=True,
        _canRemove=True
    )

    transfer_perms = createTransferPerms(
        _canTransfer=False,
        _canCreateCheque=True,
        _canAddPendingPayee=False,
        _allowedPayees=[]
    )

    # Set global settings
    high_command.setGlobalManagerSettings(
        user_wallet,
        ONE_MONTH_IN_BLOCKS,
        ONE_DAY_IN_BLOCKS * 2,
        ONE_YEAR_IN_BLOCKS * 2,
        True,
        limits,
        lego_perms,
        swap_perms,
        whitelist_perms,
        transfer_perms,
        [],
        sender=bob
    )
    
    # Verify event
    events = filter_logs(high_command, "GlobalManagerSettingsModified")
    assert len(events) == 1
    
    event = events[0]
    assert event.user == user_wallet.address
    assert event.managerPeriod == ONE_MONTH_IN_BLOCKS
    assert event.startDelay == ONE_DAY_IN_BLOCKS * 2
    assert event.activationLength == ONE_YEAR_IN_BLOCKS * 2
    assert event.canOwnerManage == True
    assert event.maxUsdValuePerTx == 2000 * 10**6
    assert event.maxUsdValuePerPeriod == 20000 * 10**6
    assert event.maxUsdValueLifetime == 200000 * 10**6
    assert event.maxNumTxsPerPeriod == 100
    assert event.txCooldownBlocks == 200
    assert event.failOnZeroPrice == True
    assert event.canManageYield == False
    assert event.canBuyAndSell == True
    assert event.canManageDebt == True
    assert event.canManageLiq == False
    assert event.canClaimRewards == True
    assert event.numAllowedLegos == 0
    assert event.canAddPendingWhitelist == False
    assert event.canConfirmWhitelist == True
    assert event.canCancelWhitelist == True
    assert event.canRemoveWhitelist == True
    assert event.canTransfer == False
    assert event.canCreateCheque == True
    assert event.canAddPendingPayee == False
    assert event.numAllowedRecipients == 0
    assert event.numAllowedAssets == 0


def test_set_global_manager_settings_validates_inputs(high_command, user_wallet, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, bob, fork):
    """Test that invalid global settings are rejected"""
    # Test invalid manager period (too short)
    with boa.reverts("invalid settings"):
        high_command.setGlobalManagerSettings(
            user_wallet,
            PARAMS[fork]["BOSS_MIN_MANAGER_PERIOD"] - 1,  # Below minimum
            ONE_DAY_IN_BLOCKS,
            ONE_YEAR_IN_BLOCKS,
            True,
            createManagerLimits(),
            createLegoPerms(),
            createSwapPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            sender=bob
        )
    
    # Test invalid manager period (too long)
    with boa.reverts("invalid settings"):
        high_command.setGlobalManagerSettings(
            user_wallet,
            PARAMS[fork]["BOSS_MAX_MANAGER_PERIOD"] + 1,  # Above maximum
            ONE_DAY_IN_BLOCKS,
            ONE_YEAR_IN_BLOCKS,
            True,
            createManagerLimits(),
            createLegoPerms(),
            createSwapPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            sender=bob
        )
    
    # Test invalid activation length (too short)
    with boa.reverts("invalid settings"):
        high_command.setGlobalManagerSettings(
            user_wallet,
            ONE_MONTH_IN_BLOCKS,
            ONE_DAY_IN_BLOCKS,
            PARAMS[fork]["BOSS_MIN_ACTIVATION_LENGTH"] - 1,  # Below minimum
            True,
            createManagerLimits(),
            createLegoPerms(),
            createSwapPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            sender=bob
        )
    
    # Test invalid activation length (too long)
    with boa.reverts("invalid settings"):
        high_command.setGlobalManagerSettings(
            user_wallet,
            ONE_MONTH_IN_BLOCKS,
            ONE_DAY_IN_BLOCKS,
            PARAMS[fork]["BOSS_MAX_ACTIVATION_LENGTH"] + 1,  # Above maximum
            True,
            createManagerLimits(),
            createLegoPerms(),
            createSwapPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            sender=bob
        )
    
    # Test invalid start delay (too long)
    with boa.reverts("invalid settings"):
        high_command.setGlobalManagerSettings(
            user_wallet,
            ONE_MONTH_IN_BLOCKS,
            PARAMS[fork]["BOSS_MAX_START_DELAY"] + 1,  # Above maximum
            ONE_YEAR_IN_BLOCKS,
            True,
            createManagerLimits(),
            createLegoPerms(),
            createSwapPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            sender=bob
        )


def test_set_global_manager_settings_respects_timelock(high_command, user_wallet, user_wallet_config, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, bob):
    """Test that start delay must respect user's timelock"""
    # Get the current timelock from user wallet config
    timelock = user_wallet_config.timeLock()
    
    # Try to set start delay less than timelock
    with boa.reverts("invalid settings"):
        high_command.setGlobalManagerSettings(
            user_wallet,
            ONE_MONTH_IN_BLOCKS,
            timelock - 1,  # Less than timelock
            ONE_YEAR_IN_BLOCKS,
            True,
            createManagerLimits(),
            createLegoPerms(),
            createSwapPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            sender=bob
        )


def test_set_global_manager_settings_multiple_updates(high_command, user_wallet, user_wallet_config, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, bob):
    """Test multiple updates to global manager settings"""
    # First update - restrictive settings
    high_command.setGlobalManagerSettings(
        user_wallet,
        ONE_MONTH_IN_BLOCKS,
        ONE_DAY_IN_BLOCKS,
        ONE_MONTH_IN_BLOCKS * 6,
        False,
        createManagerLimits(
            _maxUsdValuePerTx=100 * 10**6,
            _maxUsdValuePerPeriod=1000 * 10**6,
            _maxUsdValueLifetime=10000 * 10**6,
            _failOnZeroPrice=True
        ),
        createLegoPerms(
            _canManageYield=False,
            _canBuyAndSell=False,
            _canManageDebt=False,
            _canManageLiq=False,
            _canClaimRewards=True,
            _allowedLegos=[]
        ),
        createSwapPerms(),
        createWhitelistPerms(
            _canAddPending=False,
            _canConfirm=False,
            _canCancel=True,
            _canRemove=False
        ),
        createTransferPerms(
            _canTransfer=False,
            _canCreateCheque=False,
            _canAddPendingPayee=False,
            _allowedPayees=[]
        ),
        [],
        sender=bob
    )
    
    # Verify first update
    settings1 = user_wallet_config.globalManagerSettings()
    assert settings1.canOwnerManage == False
    assert settings1.limits.maxUsdValuePerTx == 100 * 10**6
    assert settings1.legoPerms.canManageYield == False
    
    # Second update - more permissive settings
    high_command.setGlobalManagerSettings(
        user_wallet,
        ONE_MONTH_IN_BLOCKS * 2,
        ONE_DAY_IN_BLOCKS * 2,
        ONE_YEAR_IN_BLOCKS,
        True,
        createManagerLimits(),  # No limits
        createLegoPerms(),  # All permissions
        createSwapPerms(),
        createWhitelistPerms(),  # Default permissions
        createTransferPerms(),  # All permissions
        [],
        sender=bob
    )
    
    # Verify second update
    settings2 = user_wallet_config.globalManagerSettings()
    assert settings2.canOwnerManage == True
    assert settings2.limits.maxUsdValuePerTx == 0  # No limit
    assert settings2.legoPerms.canManageYield == True
    assert settings2.managerPeriod == ONE_MONTH_IN_BLOCKS * 2


def test_set_global_manager_settings_with_invalid_lego_ids(high_command, user_wallet, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, bob):
    """Test that invalid lego IDs are rejected"""
    # Try with invalid lego ID (99999 doesn't exist)
    lego_perms = createLegoPerms(
        _canManageYield=True,
        _canBuyAndSell=True,
        _canManageDebt=True,
        _canManageLiq=True,
        _canClaimRewards=True,
        _allowedLegos=[1, 99999]  # 99999 is invalid
    )
    
    with boa.reverts("invalid settings"):
        high_command.setGlobalManagerSettings(
            user_wallet,
            ONE_MONTH_IN_BLOCKS,
            ONE_DAY_IN_BLOCKS,
            ONE_YEAR_IN_BLOCKS,
            True,
            createManagerLimits(),
            lego_perms,
            createSwapPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            sender=bob
        )


def test_set_global_manager_settings_cooldown_exceeds_period(high_command, user_wallet, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, bob):
    """Test that cooldown cannot exceed manager period"""
    manager_period = ONE_DAY_IN_BLOCKS * 7  # 7 days
    
    # Try with cooldown longer than period
    limits = createManagerLimits(
        _txCooldownBlocks=manager_period + 1  # Exceeds period
    )
    
    with boa.reverts("invalid settings"):
        high_command.setGlobalManagerSettings(
            user_wallet,
            manager_period,
            ONE_DAY_IN_BLOCKS,
            ONE_YEAR_IN_BLOCKS,
            True,
            limits,
            createLegoPerms(),
            createSwapPerms(),
            createWhitelistPerms(),
            createTransferPerms(),
            [],
            sender=bob
        )


def test_set_global_manager_settings_affects_new_managers(high_command, user_wallet, user_wallet_config, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, alice, bob):
    """Test that global settings affect new managers added after"""
    # Set global settings with specific defaults
    high_command.setGlobalManagerSettings(
        user_wallet,
        ONE_MONTH_IN_BLOCKS,
        ONE_DAY_IN_BLOCKS * 3,  # 3 day start delay
        ONE_MONTH_IN_BLOCKS * 3,  # 3 month activation
        True,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        sender=bob
    )

    current_block = boa.env.evm.patch.block_number

    # Add a new manager without specifying start delay or activation length
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(),
            createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        0,  # start delay
        0,  # activation length
        sender=bob
    )

    # Verify manager got global defaults
    settings = user_wallet_config.managerSettings(alice)
    assert settings.startBlock == current_block + ONE_DAY_IN_BLOCKS * 3  # Global start delay
    assert settings.expiryBlock == settings.startBlock + ONE_MONTH_IN_BLOCKS * 3  # Global activation


##############################################################
# Global Manager Settings - onlyApprovedYieldOpps Property #
##############################################################


def test_set_global_manager_settings_only_approved_yield_opps_saved(high_command, user_wallet, user_wallet_config, createManagerLimits, createLegoPerms, createSwapPerms, createWhitelistPerms, createTransferPerms, bob):
    """Test that global settings correctly saves onlyApprovedYieldOpps property"""
    # Set global settings with onlyApprovedYieldOpps=True
    lego_perms = createLegoPerms(
        _canManageYield=True,
        _canBuyAndSell=True,
        _onlyApprovedYieldOpps=True
    )

    result = high_command.setGlobalManagerSettings(
        user_wallet,
        ONE_MONTH_IN_BLOCKS,
        ONE_DAY_IN_BLOCKS,
        ONE_YEAR_IN_BLOCKS,
        True,
        createManagerLimits(),
        lego_perms,
        createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        sender=bob
    )

    assert result == True

    # Verify the property was saved
    global_settings = user_wallet_config.globalManagerSettings()
    assert global_settings.legoPerms.onlyApprovedYieldOpps == True


