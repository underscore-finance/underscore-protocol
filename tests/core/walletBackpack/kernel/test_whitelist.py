import pytest
import boa

from constants import WHITELIST_ACTION, ZERO_ADDRESS
from conf_utils import filter_logs


###################################
# Whitelist Management Validation #
###################################


def test_owner_can_manage_all_whitelist_actions(kernel, user_wallet, bob):
    """Test that the owner has permission for all whitelist actions"""
    # Owner should have permission for all actions
    assert kernel.canManageWhitelist(user_wallet, bob, WHITELIST_ACTION.ADD_PENDING)
    assert kernel.canManageWhitelist(user_wallet, bob, WHITELIST_ACTION.CONFIRM_WHITELIST)
    assert kernel.canManageWhitelist(user_wallet, bob, WHITELIST_ACTION.CANCEL_WHITELIST)
    assert kernel.canManageWhitelist(user_wallet, bob, WHITELIST_ACTION.REMOVE_WHITELIST)


def test_manager_whitelist_permissions_individual(createGlobalManagerSettings, createWhitelistPerms, sally, createManagerSettings, kernel, user_wallet, user_wallet_config, alice, high_command):
    """Test manager permissions for individual whitelist actions"""
    # Set global permissions to allow all actions
    global_whitelist_perms = createWhitelistPerms(_canAddPending=True, _canConfirm=True, _canCancel=True, _canRemove=True)
    new_global_manager_settings = createGlobalManagerSettings(_whitelistPerms=global_whitelist_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    # Test canAddPending permission only
    manager_whitelist_perms = createWhitelistPerms(_canAddPending=True, _canConfirm=False, _canCancel=False, _canRemove=False)
    new_manager_settings = createManagerSettings(_whitelistPerms=manager_whitelist_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    assert kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.ADD_PENDING)
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.CONFIRM_WHITELIST)
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.CANCEL_WHITELIST)
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.REMOVE_WHITELIST)
    
    # Test canConfirm permission only
    manager_whitelist_perms = createWhitelistPerms(_canAddPending=False, _canConfirm=True, _canCancel=False, _canRemove=False)
    new_manager_settings = createManagerSettings(_whitelistPerms=manager_whitelist_perms)
    user_wallet_config.addManager(sally, new_manager_settings, sender=high_command.address)
    
    assert not kernel.canManageWhitelist(user_wallet, sally, WHITELIST_ACTION.ADD_PENDING)
    assert kernel.canManageWhitelist(user_wallet, sally, WHITELIST_ACTION.CONFIRM_WHITELIST)
    assert not kernel.canManageWhitelist(user_wallet, sally, WHITELIST_ACTION.CANCEL_WHITELIST)
    assert not kernel.canManageWhitelist(user_wallet, sally, WHITELIST_ACTION.REMOVE_WHITELIST)


def test_manager_whitelist_permissions_multiple(createGlobalManagerSettings, createWhitelistPerms, createManagerSettings, kernel, user_wallet, user_wallet_config, alice, high_command):
    """Test manager with multiple whitelist permissions"""
    whitelist_perms = createWhitelistPerms(_canAddPending=True, _canConfirm=True, _canCancel=True, _canRemove=False)
    new_global_manager_settings = createGlobalManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    new_manager_settings = createManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    assert kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.ADD_PENDING)
    assert kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.CONFIRM_WHITELIST)
    assert kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.CANCEL_WHITELIST)
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.REMOVE_WHITELIST)


def test_global_whitelist_permissions_override(createGlobalManagerSettings, createWhitelistPerms, createManagerSettings, kernel, user_wallet, user_wallet_config, alice, high_command):
    """Test that both manager and global permissions must be true"""
    # Set global permissions to allow all
    global_whitelist_perms = createWhitelistPerms(_canAddPending=True, _canConfirm=True, _canCancel=True, _canRemove=True)
    new_global_manager_settings = createGlobalManagerSettings(_whitelistPerms=global_whitelist_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    # But manager permissions only allow ADD_PENDING
    manager_whitelist_perms = createWhitelistPerms(_canAddPending=True, _canConfirm=False, _canCancel=False, _canRemove=False)
    new_manager_settings = createManagerSettings(_whitelistPerms=manager_whitelist_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Only ADD_PENDING should be allowed (both global and manager are true)
    assert kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.ADD_PENDING)
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.CONFIRM_WHITELIST)
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.CANCEL_WHITELIST)
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.REMOVE_WHITELIST)


def test_global_permissions_restrict_manager(createGlobalManagerSettings, createWhitelistPerms, createManagerSettings, kernel, user_wallet, user_wallet_config, alice, high_command):
    """Test that global permissions can restrict manager permissions"""
    # Set global permissions to deny all except ADD_PENDING
    global_whitelist_perms = createWhitelistPerms(_canAddPending=True, _canConfirm=False, _canCancel=False, _canRemove=False)
    new_global_manager_settings = createGlobalManagerSettings(_whitelistPerms=global_whitelist_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    # Manager permissions allow all
    manager_whitelist_perms = createWhitelistPerms(_canAddPending=True, _canConfirm=True, _canCancel=True, _canRemove=True)
    new_manager_settings = createManagerSettings(_whitelistPerms=manager_whitelist_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Only ADD_PENDING should be allowed (global restricts the others)
    assert kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.ADD_PENDING)
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.CONFIRM_WHITELIST)
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.CANCEL_WHITELIST)
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.REMOVE_WHITELIST)


def test_non_manager_non_owner_denied(kernel, user_wallet, charlie):
    """Test that non-manager/non-owner users are denied all whitelist actions"""
    assert not kernel.canManageWhitelist(user_wallet, charlie, WHITELIST_ACTION.ADD_PENDING)
    assert not kernel.canManageWhitelist(user_wallet, charlie, WHITELIST_ACTION.CONFIRM_WHITELIST)
    assert not kernel.canManageWhitelist(user_wallet, charlie, WHITELIST_ACTION.CANCEL_WHITELIST)
    assert not kernel.canManageWhitelist(user_wallet, charlie, WHITELIST_ACTION.REMOVE_WHITELIST)


def test_manager_with_all_permissions_false(createGlobalManagerSettings, createWhitelistPerms, createManagerSettings, kernel, user_wallet, user_wallet_config, alice, high_command):
    """Test manager with all whitelist permissions set to false"""
    whitelist_perms = createWhitelistPerms(_canAddPending=False, _canConfirm=False, _canCancel=False, _canRemove=False)
    new_global_manager_settings = createGlobalManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    new_manager_settings = createManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Manager should be denied all actions
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.ADD_PENDING)
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.CONFIRM_WHITELIST)
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.CANCEL_WHITELIST)
    assert not kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.REMOVE_WHITELIST)


def test_whitelist_management_example(createGlobalManagerSettings, createWhitelistPerms, sally, charlie, bob, createManagerSettings, kernel, user_wallet, user_wallet_config, alice, high_command):

    whitelist_perms = createWhitelistPerms(_canAddPending=True, _canConfirm=False, _canCancel=False, _canRemove=False)

    # set global manager settings
    new_global_manager_settings = createGlobalManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)

    # add manager
    new_manager_settings = createManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)

    # owner can manage
    assert kernel.canManageWhitelist(user_wallet, bob, WHITELIST_ACTION.ADD_PENDING)

    # manager -- allowed
    assert kernel.canManageWhitelist(user_wallet, alice, WHITELIST_ACTION.ADD_PENDING)

    # another manager -- not allowed
    whitelist_perms = createWhitelistPerms(_canAddPending=False)
    new_manager_settings = createManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.addManager(sally, new_manager_settings, sender=high_command.address)

    assert not kernel.canManageWhitelist(user_wallet, sally, WHITELIST_ACTION.ADD_PENDING)

    # not manager
    assert not kernel.canManageWhitelist(user_wallet, charlie, WHITELIST_ACTION.ADD_PENDING)


###########################
# Whitelist - Add Pending #
###########################


def test_add_pending_whitelist_success(kernel, user_wallet, user_wallet_config, bob, charlie):
    """Test successful pending whitelist creation"""
    # Add pending whitelist as owner
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Verify pending whitelist data was saved
    pending = user_wallet_config.pendingWhitelist(charlie)
    assert pending.initiatedBlock == boa.env.evm.patch.block_number
    assert pending.confirmBlock == boa.env.evm.patch.block_number + user_wallet_config.timeLock()
    assert pending.currentOwner == bob
    
    # Verify event emission
    log = filter_logs(kernel, "WhitelistAddrPending")[0]
    assert log.user == user_wallet.address
    assert log.addr == charlie
    assert log.confirmBlock == pending.confirmBlock
    assert log.addedBy == bob


def test_add_pending_whitelist_with_timelock(kernel, user_wallet, user_wallet_config, bob, alice):
    """Test pending whitelist respects timelock"""
    timelock = user_wallet_config.timeLock()
    initial_block = boa.env.evm.patch.block_number
    
    # Add pending whitelist
    kernel.addPendingWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Verify confirmBlock is set correctly with timelock
    pending = user_wallet_config.pendingWhitelist(alice)
    assert pending.confirmBlock == initial_block + timelock


def test_add_pending_whitelist_invalid_addresses(kernel, user_wallet, user_wallet_config, bob):
    """Test invalid address validation"""
    # Cannot add zero address
    with boa.reverts("invalid addr"):
        kernel.addPendingWhitelistAddr(user_wallet, ZERO_ADDRESS, sender=bob)
    
    # Cannot add the wallet itself
    with boa.reverts("invalid addr"):
        kernel.addPendingWhitelistAddr(user_wallet, user_wallet, sender=bob)
    
    # Cannot add the owner
    with boa.reverts("invalid addr"):
        kernel.addPendingWhitelistAddr(user_wallet, bob, sender=bob)
    
    # Cannot add the wallet config
    with boa.reverts("invalid addr"):
        kernel.addPendingWhitelistAddr(user_wallet, user_wallet_config.address, sender=bob)


def test_add_pending_whitelist_already_pending(kernel, user_wallet, bob, charlie):
    """Test cannot add duplicate pending whitelist"""
    # Add pending whitelist first time
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Try to add same address again
    with boa.reverts("pending whitelist already exists"):
        kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)


def test_add_pending_whitelist_already_whitelisted(kernel, user_wallet, user_wallet_config, bob, alice):
    """Test cannot add pending for already whitelisted address"""
    # First add alice to whitelist (pending -> confirm)
    kernel.addPendingWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Advance blocks to pass timelock
    boa.env.time_travel(blocks=user_wallet_config.timeLock())

    # Confirm the whitelist
    kernel.confirmWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Verify alice is whitelisted
    assert user_wallet_config.indexOfWhitelist(alice) != 0
    
    # Try to add pending whitelist for already whitelisted address
    with boa.reverts("already whitelisted"):
        kernel.addPendingWhitelistAddr(user_wallet, alice, sender=bob)


def test_add_pending_whitelist_fails_for_payee(
    kernel, user_wallet, bob, alice, paymaster, createPayeeLimits,
    createGlobalPayeeSettings, user_wallet_config
):
    """Test H-04 fix: Cannot whitelist an address that is already a payee"""
    from constants import EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS

    # Set up global payee settings
    global_settings = createGlobalPayeeSettings(_canPull=False, _failOnZeroPrice=False)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)

    # Add alice as a payee
    usd_limits = createPayeeLimits(
        _perTxCap=100 * EIGHTEEN_DECIMALS,
        _perPeriodCap=1000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=10000 * EIGHTEEN_DECIMALS
    )
    paymaster.addPayee(
        user_wallet.address,
        alice,  # payee
        False,  # canPull
        2 * ONE_DAY_IN_BLOCKS,  # periodLength
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        createPayeeLimits(),  # unitLimits
        usd_limits,  # usdLimits
        0,  # startDelay
        2**256 - 1,  # activationLength
        sender=bob
    )

    # Verify alice is now a payee
    assert user_wallet_config.indexOfPayee(alice) != 0

    # Try to add alice to whitelist - should fail with H-04 protection
    with boa.reverts():
        kernel.addPendingWhitelistAddr(user_wallet, alice, sender=bob)


def test_add_pending_whitelist_fails_for_active_cheque_recipient(
    kernel, user_wallet, bob, charlie, cheque_book, user_wallet_config, mock_ripe, alpha_token
):
    """Test H-04 fix: Cannot whitelist an address that has an active cheque"""
    from constants import EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ONE_MONTH_IN_BLOCKS

    # Set up cheque settings
    ONE_WEEK_IN_BLOCKS = ONE_DAY_IN_BLOCKS * 7
    cheque_book.setChequeSettings(
        user_wallet.address,
        0,  # maxNumActiveCheques
        0,  # maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # instantUsdThreshold
        0,  # perPeriodPaidUsdCap
        0,  # maxNumChequesPaidPerPeriod
        0,  # payCooldownBlocks
        0,  # perPeriodCreatedUsdCap
        0,  # maxNumChequesCreatedPerPeriod
        0,  # createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # periodLength
        ONE_DAY_IN_BLOCKS,  # expensiveDelayBlocks
        0,  # defaultExpiryBlocks
        [],  # allowedAssets
        True,  # canManagersCreateCheques
        True,  # canManagerPay
        True,  # canBePulled
        sender=bob
    )

    # Set price for the asset
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)

    # Create a cheque for charlie
    cheque_book.createCheque(
        user_wallet.address,
        charlie,
        alpha_token.address,
        50 * EIGHTEEN_DECIMALS,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,  # canManagerPay
        True,  # canBePulled
        sender=bob
    )

    # Verify charlie has an active cheque
    cheque = user_wallet_config.cheques(charlie)
    assert cheque[10] == True  # active flag

    # Try to add charlie to whitelist - should fail with H-04 protection
    with boa.reverts():
        kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)


def test_add_pending_whitelist_succeeds_for_inactive_cheque_recipient(
    kernel, user_wallet, bob, charlie, cheque_book, user_wallet_config, mock_ripe, alpha_token
):
    """Test that whitelisting succeeds for inactive cheque (cancelled or expired)"""
    from constants import EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ONE_MONTH_IN_BLOCKS

    # Set up cheque settings
    ONE_WEEK_IN_BLOCKS = ONE_DAY_IN_BLOCKS * 7
    cheque_book.setChequeSettings(
        user_wallet.address,
        0,  # maxNumActiveCheques
        0,  # maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # instantUsdThreshold
        0,  # perPeriodPaidUsdCap
        0,  # maxNumChequesPaidPerPeriod
        0,  # payCooldownBlocks
        0,  # perPeriodCreatedUsdCap
        0,  # maxNumChequesCreatedPerPeriod
        0,  # createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # periodLength
        ONE_DAY_IN_BLOCKS,  # expensiveDelayBlocks
        0,  # defaultExpiryBlocks
        [],  # allowedAssets
        True,  # canManagersCreateCheques
        True,  # canManagerPay
        True,  # canBePulled
        sender=bob
    )

    # Set price for the asset
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)

    # Create a cheque for charlie
    cheque_book.createCheque(
        user_wallet.address,
        charlie,
        alpha_token.address,
        50 * EIGHTEEN_DECIMALS,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,
        True,
        sender=bob
    )

    # Verify charlie has an active cheque
    cheque = user_wallet_config.cheques(charlie)
    assert cheque[10] == True  # active flag

    # Now cancel the cheque
    cheque_book.cancelCheque(user_wallet.address, charlie, sender=bob)

    # Verify cheque is now inactive
    cheque_after = user_wallet_config.cheques(charlie)
    assert cheque_after[10] == False  # active flag should be False

    # Now adding charlie to whitelist should succeed
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)

    # Verify pending whitelist was created
    pending = user_wallet_config.pendingWhitelist(charlie)
    assert pending.initiatedBlock != 0


def test_add_pending_whitelist_succeeds_for_non_payee_non_cheque(
    kernel, user_wallet, user_wallet_config, bob, sally
):
    """Test that whitelisting succeeds for address that is not a payee or cheque recipient"""
    # Sally is neither a payee nor has a cheque - should succeed
    kernel.addPendingWhitelistAddr(user_wallet, sally, sender=bob)

    # Verify pending whitelist was created
    pending = user_wallet_config.pendingWhitelist(sally)
    assert pending.initiatedBlock != 0


def test_add_pending_whitelist_invalid_user_wallet(kernel, bob, alice):
    """Test validation of user wallet"""
    # Try with random address that's not a user wallet
    with boa.reverts("invalid user wallet"):
        kernel.addPendingWhitelistAddr(alice, bob, sender=bob)


def test_add_pending_whitelist_by_manager(createGlobalManagerSettings, createWhitelistPerms, createManagerSettings, kernel, user_wallet, user_wallet_config, alice, charlie, high_command):
    """Test manager can add pending whitelist with proper permissions"""
    # Setup manager with add pending permission
    whitelist_perms = createWhitelistPerms(_canAddPending=True, _canConfirm=False, _canCancel=False, _canRemove=False)
    new_global_manager_settings = createGlobalManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    new_manager_settings = createManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Manager adds pending whitelist
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=alice)
    
    # Verify event shows manager as addedBy
    log = filter_logs(kernel, "WhitelistAddrPending")[0]
    assert log.addedBy == alice


#######################
# Whitelist - Confirm #
#######################


def test_confirm_whitelist_fails_if_address_becomes_payee_during_timelock(
    kernel, user_wallet, user_wallet_config, bob, sally, paymaster,
    createPayeeLimits, createGlobalPayeeSettings
):
    """Test that confirmation fails if address becomes payee during timelock period (H-04 edge case)"""
    from constants import EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS

    # Add pending whitelist for sally
    kernel.addPendingWhitelistAddr(user_wallet, sally, sender=bob)

    pending = user_wallet_config.pendingWhitelist(sally)
    assert pending.initiatedBlock != 0

    # During the timelock period, make sally a payee
    # Set up global payee settings
    global_settings = createGlobalPayeeSettings(_canPull=False, _failOnZeroPrice=False)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)

    # Add sally as payee
    usd_limits = createPayeeLimits(
        _perTxCap=100 * EIGHTEEN_DECIMALS,
        _perPeriodCap=1000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=10000 * EIGHTEEN_DECIMALS
    )
    paymaster.addPayee(
        user_wallet.address,
        sally,  # payee
        False,  # canPull
        2 * ONE_DAY_IN_BLOCKS,  # periodLength
        10,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        ZERO_ADDRESS,  # primaryAsset
        False,  # onlyPrimaryAsset
        createPayeeLimits(),  # unitLimits
        usd_limits,  # usdLimits
        0,  # startDelay
        2**256 - 1,  # activationLength
        sender=bob
    )

    # Verify sally is now a payee
    assert user_wallet_config.indexOfPayee(sally) != 0

    # Advance past timelock for whitelist
    boa.env.time_travel(blocks=pending.confirmBlock - boa.env.evm.patch.block_number + 1)

    # Try to confirm whitelist - should fail because sally is now a payee
    with boa.reverts():
        kernel.confirmWhitelistAddr(user_wallet, sally, sender=bob)


def test_confirm_whitelist_fails_if_address_gets_cheque_during_timelock(
    kernel, user_wallet, user_wallet_config, bob, sally, cheque_book, alpha_token, mock_ripe
):
    """Test that confirmation fails if address gets active cheque during timelock period (H-04 edge case)"""
    from constants import EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ONE_MONTH_IN_BLOCKS

    # Add pending whitelist for sally
    kernel.addPendingWhitelistAddr(user_wallet, sally, sender=bob)

    pending = user_wallet_config.pendingWhitelist(sally)
    assert pending.initiatedBlock != 0

    # During the timelock period, create a cheque for sally
    # Set up cheque settings
    ONE_WEEK_IN_BLOCKS = ONE_DAY_IN_BLOCKS * 7
    cheque_book.setChequeSettings(
        user_wallet.address,
        0,  # maxNumActiveCheques
        0,  # maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # instantUsdThreshold
        0,  # perPeriodPaidUsdCap
        0,  # maxNumChequesPaidPerPeriod
        0,  # payCooldownBlocks
        0,  # perPeriodCreatedUsdCap
        0,  # maxNumChequesCreatedPerPeriod
        0,  # createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # periodLength
        ONE_DAY_IN_BLOCKS,  # expensiveDelayBlocks
        0,  # defaultExpiryBlocks
        [],  # allowedAssets
        True,  # canManagersCreateCheques
        True,  # canManagerPay
        False,  # canBePulled
        sender=bob
    )

    # Set price for the asset
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)  # $1 per token

    # Create cheque for sally
    amount = 50 * EIGHTEEN_DECIMALS
    cheque_book.createCheque(
        user_wallet.address,
        sally,
        alpha_token.address,
        amount,
        ONE_DAY_IN_BLOCKS,  # delayBlocks
        ONE_WEEK_IN_BLOCKS,  # expiryBlocks
        True,  # canManagerPay
        False,  # canBePulled
        sender=bob
    )

    # Verify sally now has an active cheque
    cheque = user_wallet_config.cheques(sally)
    assert cheque[10] == True  # active flag

    # Advance past timelock for whitelist
    boa.env.time_travel(blocks=pending.confirmBlock - boa.env.evm.patch.block_number + 1)

    # Try to confirm whitelist - should fail because sally now has an active cheque
    with boa.reverts():
        kernel.confirmWhitelistAddr(user_wallet, sally, sender=bob)


def test_confirm_whitelist_success(kernel, user_wallet, user_wallet_config, bob, charlie):
    """Test successful whitelist confirmation after timelock"""
    # Add pending whitelist
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)

    # Get pending whitelist data before confirmation
    pending = user_wallet_config.pendingWhitelist(charlie)
    initiated_block = pending.initiatedBlock
    confirm_block = pending.confirmBlock
    
    # Advance blocks to pass timelock
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    
    # Confirm the whitelist
    kernel.confirmWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Verify address is now whitelisted
    assert user_wallet_config.indexOfWhitelist(charlie) != 0
    
    # Verify pending whitelist is cleared
    pending_after = user_wallet_config.pendingWhitelist(charlie)
    assert pending_after.initiatedBlock == 0
    assert pending_after.confirmBlock == 0
    
    # Verify event emission
    log = filter_logs(kernel, "WhitelistAddrConfirmed")[0]
    assert log.user == user_wallet.address
    assert log.addr == charlie
    assert log.initiatedBlock == initiated_block
    assert log.confirmBlock == confirm_block
    assert log.confirmedBy == bob


def test_confirm_whitelist_timelock_not_reached(kernel, user_wallet, user_wallet_config, bob, alice):
    """Test cannot confirm before timelock expires"""
    # Add pending whitelist
    kernel.addPendingWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Try to confirm immediately (without advancing blocks)
    with boa.reverts("time delay not reached"):
        kernel.confirmWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Advance blocks but not enough to pass timelock
    boa.env.time_travel(blocks=user_wallet_config.timeLock() - 1)
    
    # Should still fail
    with boa.reverts("time delay not reached"):
        kernel.confirmWhitelistAddr(user_wallet, alice, sender=bob)


def test_confirm_whitelist_exactly_at_timelock(kernel, user_wallet, user_wallet_config, bob, alice):
    """Test can confirm exactly when timelock expires"""
    # Add pending whitelist
    kernel.addPendingWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Advance exactly to the confirm block
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    
    # Should succeed
    kernel.confirmWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Verify whitelisted
    assert user_wallet_config.indexOfWhitelist(alice) != 0


def test_confirm_whitelist_no_pending(kernel, user_wallet, bob, charlie):
    """Test cannot confirm non-existent pending whitelist"""
    # Try to confirm without adding pending first
    with boa.reverts("no pending whitelist"):
        kernel.confirmWhitelistAddr(user_wallet, charlie, sender=bob)


def test_confirm_whitelist_owner_changed(kernel, user_wallet, user_wallet_config, bob, alice, charlie):
    """Test cannot confirm if owner changed after pending was created"""
    # Add pending whitelist as current owner (bob)
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Transfer ownership to alice
    user_wallet_config.changeOwnership(alice, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.ownershipTimeLock())
    user_wallet_config.confirmOwnershipChange(sender=alice)

    boa.env.time_travel(blocks=user_wallet_config.timeLock())

    # Try to confirm - should fail because owner changed
    with boa.reverts("owner must match"):
        kernel.confirmWhitelistAddr(user_wallet, charlie, sender=alice)


def test_confirm_whitelist_invalid_user_wallet(kernel, bob, alice):
    """Test validation of user wallet"""
    # Try with random address that's not a user wallet
    with boa.reverts("invalid user wallet"):
        kernel.confirmWhitelistAddr(alice, bob, sender=bob)


def test_confirm_whitelist_by_manager(createGlobalManagerSettings, createWhitelistPerms, createManagerSettings, kernel, user_wallet, user_wallet_config, alice, charlie, bob, high_command):
    """Test manager can confirm whitelist with proper permissions"""
    # Setup manager with confirm permission
    whitelist_perms = createWhitelistPerms(_canAddPending=False, _canConfirm=True, _canCancel=False, _canRemove=False)
    new_global_manager_settings = createGlobalManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    new_manager_settings = createManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Owner adds pending whitelist
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Advance blocks to pass timelock
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    
    # Manager confirms the whitelist
    kernel.confirmWhitelistAddr(user_wallet, charlie, sender=alice)
    
    # Verify event shows manager as confirmedBy
    log = filter_logs(kernel, "WhitelistAddrConfirmed")[0]
    assert log.confirmedBy == alice
    
    # Verify whitelisted
    assert user_wallet_config.indexOfWhitelist(charlie) != 0


def test_confirm_whitelist_already_confirmed(kernel, user_wallet, user_wallet_config, bob, alice):
    """Test cannot confirm already confirmed whitelist"""
    # Add and confirm whitelist
    kernel.addPendingWhitelistAddr(user_wallet, alice, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    kernel.confirmWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Try to confirm again
    with boa.reverts("no pending whitelist"):
        kernel.confirmWhitelistAddr(user_wallet, alice, sender=bob)


######################
# Whitelist - Cancel #
######################


def test_cancel_pending_whitelist_success(kernel, user_wallet, user_wallet_config, bob, charlie):
    """Test successful pending whitelist cancellation by owner"""
    # Add pending whitelist
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Get pending whitelist data before cancellation
    pending = user_wallet_config.pendingWhitelist(charlie)
    initiated_block = pending.initiatedBlock
    confirm_block = pending.confirmBlock
    
    # Cancel the pending whitelist
    kernel.cancelPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Verify pending whitelist is cleared
    pending_after = user_wallet_config.pendingWhitelist(charlie)
    assert pending_after.initiatedBlock == 0
    assert pending_after.confirmBlock == 0
    assert pending_after.currentOwner == ZERO_ADDRESS
    
    # Verify address is not whitelisted
    assert user_wallet_config.indexOfWhitelist(charlie) == 0
    
    # Verify event emission
    log = filter_logs(kernel, "WhitelistAddrCancelled")[0]
    assert log.user == user_wallet.address
    assert log.addr == charlie
    assert log.initiatedBlock == initiated_block
    assert log.confirmBlock == confirm_block
    assert log.cancelledBy == bob


def test_cancel_pending_whitelist_no_pending(kernel, user_wallet, bob, charlie):
    """Test cannot cancel non-existent pending whitelist"""
    # Try to cancel without adding pending first
    with boa.reverts("no pending whitelist"):
        kernel.cancelPendingWhitelistAddr(user_wallet, charlie, sender=bob)


def test_cancel_pending_whitelist_after_timelock(kernel, user_wallet, user_wallet_config, bob, alice):
    """Test can cancel even after timelock expires"""
    # Add pending whitelist
    kernel.addPendingWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Advance blocks past timelock
    boa.env.time_travel(blocks=user_wallet_config.timeLock() + 10)
    
    # Should still be able to cancel
    kernel.cancelPendingWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Verify cancelled
    pending = user_wallet_config.pendingWhitelist(alice)
    assert pending.initiatedBlock == 0


def test_cancel_pending_whitelist_invalid_user_wallet(kernel, bob, alice):
    """Test validation of user wallet"""
    # Try with random address that's not a user wallet
    with boa.reverts("invalid user wallet"):
        kernel.cancelPendingWhitelistAddr(alice, bob, sender=bob)


def test_cancel_pending_whitelist_by_manager(createGlobalManagerSettings, createWhitelistPerms, createManagerSettings, kernel, user_wallet, user_wallet_config, alice, charlie, bob, high_command):
    """Test manager can cancel pending whitelist with proper permissions"""
    # Setup manager with cancel permission
    whitelist_perms = createWhitelistPerms(_canAddPending=False, _canConfirm=False, _canCancel=True, _canRemove=False)
    new_global_manager_settings = createGlobalManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    new_manager_settings = createManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Owner adds pending whitelist
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Manager cancels the pending whitelist
    kernel.cancelPendingWhitelistAddr(user_wallet, charlie, sender=alice)
    
    # Verify event shows manager as cancelledBy
    log = filter_logs(kernel, "WhitelistAddrCancelled")[0]
    assert log.cancelledBy == alice
    
    # Verify cancelled
    pending = user_wallet_config.pendingWhitelist(charlie)
    assert pending.initiatedBlock == 0


def test_cancel_pending_whitelist_by_security_action(kernel, user_wallet, user_wallet_config, bob, charlie, alice, mission_control, switchboard_alpha):
    """Test security action permission can cancel pending whitelist"""
    # Set alice as security operator
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)
    
    # Add pending whitelist
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Alice doesn't have cancel permission but has security action permission
    # This should work via security action fallback
    kernel.cancelPendingWhitelistAddr(user_wallet, charlie, sender=alice)
    
    # Verify cancelled
    pending = user_wallet_config.pendingWhitelist(charlie)
    assert pending.initiatedBlock == 0
    
    # Verify event shows alice as cancelledBy
    log = filter_logs(kernel, "WhitelistAddrCancelled")[0]
    assert log.cancelledBy == alice


def test_cancel_pending_whitelist_no_permission(kernel, user_wallet, bob, charlie, alice):
    """Test cannot cancel without proper permissions"""
    # Add pending whitelist
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Alice has no permissions
    with boa.reverts("no perms"):
        kernel.cancelPendingWhitelistAddr(user_wallet, charlie, sender=alice)


def test_cancel_then_add_again(kernel, user_wallet, user_wallet_config, bob, charlie):
    """Test can add pending whitelist again after cancellation"""
    # Add pending whitelist
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Cancel it
    kernel.cancelPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Should be able to add again
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Verify new pending exists
    pending = user_wallet_config.pendingWhitelist(charlie)
    assert pending.initiatedBlock != 0
    assert pending.confirmBlock != 0


def test_cancel_pending_whitelist_already_confirmed(kernel, user_wallet, user_wallet_config, bob, alice):
    """Test cannot cancel after confirmation"""
    # Add and confirm whitelist
    kernel.addPendingWhitelistAddr(user_wallet, alice, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    kernel.confirmWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Try to cancel - should fail because no pending exists anymore
    with boa.reverts("no pending whitelist"):
        kernel.cancelPendingWhitelistAddr(user_wallet, alice, sender=bob)


######################
# Whitelist - Remove #
######################


def test_remove_whitelist_success(kernel, user_wallet, user_wallet_config, bob, charlie):
    """Test successful whitelist removal by owner"""
    # First add and confirm whitelist
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    kernel.confirmWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Verify whitelisted
    assert user_wallet_config.indexOfWhitelist(charlie) != 0
    
    # Remove from whitelist
    kernel.removeWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Verify no longer whitelisted
    assert user_wallet_config.indexOfWhitelist(charlie) == 0
    
    # Verify event emission
    log = filter_logs(kernel, "WhitelistAddrRemoved")[0]
    assert log.user == user_wallet.address
    assert log.addr == charlie
    assert log.removedBy == bob


def test_remove_whitelist_not_whitelisted(kernel, user_wallet, bob, charlie):
    """Test cannot remove non-whitelisted address"""
    # Try to remove without whitelisting first
    with boa.reverts("not whitelisted"):
        kernel.removeWhitelistAddr(user_wallet, charlie, sender=bob)


def test_remove_whitelist_after_removal(kernel, user_wallet, user_wallet_config, bob, alice):
    """Test cannot remove already removed address"""
    # Add, confirm, and remove
    kernel.addPendingWhitelistAddr(user_wallet, alice, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    kernel.confirmWhitelistAddr(user_wallet, alice, sender=bob)
    kernel.removeWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Try to remove again
    with boa.reverts("not whitelisted"):
        kernel.removeWhitelistAddr(user_wallet, alice, sender=bob)


def test_remove_whitelist_invalid_user_wallet(kernel, bob, alice):
    """Test validation of user wallet"""
    # Try with random address that's not a user wallet
    with boa.reverts("invalid user wallet"):
        kernel.removeWhitelistAddr(alice, bob, sender=bob)


def test_remove_whitelist_by_manager(createGlobalManagerSettings, createWhitelistPerms, createManagerSettings, kernel, user_wallet, user_wallet_config, alice, charlie, bob, high_command):
    """Test manager can remove whitelist with proper permissions"""
    # Setup manager with remove permission
    whitelist_perms = createWhitelistPerms(_canAddPending=False, _canConfirm=False, _canCancel=False, _canRemove=True)
    new_global_manager_settings = createGlobalManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    new_manager_settings = createManagerSettings(_whitelistPerms=whitelist_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Owner adds and confirms whitelist
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    kernel.confirmWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Manager removes from whitelist
    kernel.removeWhitelistAddr(user_wallet, charlie, sender=alice)
    
    # Verify event shows manager as removedBy
    log = filter_logs(kernel, "WhitelistAddrRemoved")[0]
    assert log.removedBy == alice
    
    # Verify removed
    assert user_wallet_config.indexOfWhitelist(charlie) == 0


def test_remove_whitelist_by_security_action(kernel, user_wallet, user_wallet_config, bob, charlie, alice, mission_control, switchboard_alpha):
    """Test security action permission can remove whitelist"""
    # Set alice as security operator
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)
    
    # Owner adds and confirms whitelist
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    kernel.confirmWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Alice doesn't have remove permission but has security action permission
    # This should work via security action fallback
    kernel.removeWhitelistAddr(user_wallet, charlie, sender=alice)
    
    # Verify removed
    assert user_wallet_config.indexOfWhitelist(charlie) == 0
    
    # Verify event shows alice as removedBy
    log = filter_logs(kernel, "WhitelistAddrRemoved")[0]
    assert log.removedBy == alice


def test_remove_whitelist_no_permission(kernel, user_wallet, user_wallet_config, bob, charlie, alice):
    """Test cannot remove without proper permissions"""
    # Add and confirm whitelist as owner
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    kernel.confirmWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Alice has no permissions
    with boa.reverts("no perms"):
        kernel.removeWhitelistAddr(user_wallet, charlie, sender=alice)


def test_remove_then_add_again(kernel, user_wallet, user_wallet_config, bob, charlie):
    """Test can add to whitelist again after removal"""
    # Add, confirm, and remove
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    kernel.confirmWhitelistAddr(user_wallet, charlie, sender=bob)
    kernel.removeWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Should be able to add again
    kernel.addPendingWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Verify new pending exists
    pending = user_wallet_config.pendingWhitelist(charlie)
    assert pending.initiatedBlock != 0
    assert pending.confirmBlock != 0
    
    # Confirm again
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    kernel.confirmWhitelistAddr(user_wallet, charlie, sender=bob)
    
    # Verify whitelisted again
    assert user_wallet_config.indexOfWhitelist(charlie) != 0


def test_remove_whitelist_pending_exists(kernel, user_wallet, user_wallet_config, bob, alice):
    """Test pending whitelist is independent of confirmed whitelist"""
    # Add and confirm alice to whitelist
    kernel.addPendingWhitelistAddr(user_wallet, alice, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    kernel.confirmWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Add pending for alice again (should fail)
    with boa.reverts("already whitelisted"):
        kernel.addPendingWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Remove alice from whitelist
    kernel.removeWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Now can add pending again
    kernel.addPendingWhitelistAddr(user_wallet, alice, sender=bob)
    
    # Verify pending exists
    pending = user_wallet_config.pendingWhitelist(alice)
    assert pending.initiatedBlock != 0

