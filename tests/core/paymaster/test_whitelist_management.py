"""
Test whitelist management functionality in Paymaster
"""
import pytest
import boa

from contracts.core import Paymaster
from contracts.core.userWallet import UserWallet, UserWalletConfig
from constants import EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ZERO_ADDRESS
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
def setup_contracts(setup_wallet, paymaster, boss_validator, alpha_token, bob, alice, charlie, env, governance):
    """Setup contracts and basic configuration"""
    user_wallet = setup_wallet
    wallet_config_addr = user_wallet.walletConfig()
    wallet_config = UserWalletConfig.at(wallet_config_addr)
    owner = bob
    
    # Fund wallet for testing
    alpha_token.transfer(user_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Create manager address
    manager = env.generate_address("manager")
    
    return {
        'wallet': user_wallet,
        'wallet_config': wallet_config,
        'paymaster': paymaster,
        'boss_validator': boss_validator,
        'owner': owner,
        'addr1': alice,
        'addr2': charlie,
        'manager': manager,
        'alpha_token': alpha_token
    }


# Test adding whitelist addresses


def test_add_whitelist_addr_basic(setup_contracts):
    """Test basic whitelist address addition"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    addr = ctx['addr1']
    
    # Add whitelist address
    tx = paymaster.addWhitelistAddr(wallet.address, addr, sender=owner)
    
    # Check events
    events = filter_logs(paymaster, "WhitelistAddrPending")
    assert len(events) == 1
    event = events[0]
    assert event.user == wallet.address
    assert event.addr == addr
    assert event.confirmBlock > boa.env.evm.patch.block_number
    assert event.addedBy == owner
    
    # Verify pending whitelist exists
    pending = wallet_config.pendingWhitelist(addr)
    assert pending[0] != 0  # initiatedBlock
    assert pending[1] == event.confirmBlock  # confirmBlock


def test_add_whitelist_invalid_addresses(setup_contracts):
    """Test cannot add invalid whitelist addresses"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    
    # Cannot add zero address
    with boa.reverts("invalid addr"):
        paymaster.addWhitelistAddr(wallet.address, ZERO_ADDRESS, sender=owner)
    
    # Cannot add wallet itself
    with boa.reverts("invalid addr"):
        paymaster.addWhitelistAddr(wallet.address, wallet.address, sender=owner)
    
    # Cannot add owner
    with boa.reverts("invalid addr"):
        paymaster.addWhitelistAddr(wallet.address, owner, sender=owner)
    
    # Cannot add wallet config
    with boa.reverts("invalid addr"):
        paymaster.addWhitelistAddr(wallet.address, wallet_config.address, sender=owner)


def test_add_whitelist_already_whitelisted(setup_contracts):
    """Test cannot add address that is already whitelisted"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    addr = boa.env.generate_address()
    
    # Add and confirm whitelist
    paymaster.addWhitelistAddr(wallet.address, addr, sender=owner)
    boa.env.time_travel(blocks=wallet_config.timeLock() + 1)
    paymaster.confirmWhitelistAddr(wallet.address, addr, sender=owner)
    
    # Try to add again
    with boa.reverts("already whitelisted"):
        paymaster.addWhitelistAddr(wallet.address, addr, sender=owner)


def test_add_whitelist_pending_exists(setup_contracts):
    """Test cannot add whitelist if pending already exists"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    owner = ctx['owner']
    addr = boa.env.generate_address()
    
    # Add pending whitelist
    paymaster.addWhitelistAddr(wallet.address, addr, sender=owner)
    
    # Try to add again
    with boa.reverts("pending whitelist already exists"):
        paymaster.addWhitelistAddr(wallet.address, addr, sender=owner)


# Test confirming whitelist addresses


def test_confirm_whitelist_addr(setup_contracts):
    """Test confirming whitelist address"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    addr = ctx['addr2']
    
    # Add whitelist address
    paymaster.addWhitelistAddr(wallet.address, addr, sender=owner)
    
    # Cannot confirm before timelock
    with boa.reverts("time delay not reached"):
        paymaster.confirmWhitelistAddr(wallet.address, addr, sender=owner)
    
    # Get pending info
    pending = wallet_config.pendingWhitelist(addr)
    initiated_block = pending[0]
    confirm_block = pending[1]
    
    # Advance past timelock
    boa.env.time_travel(blocks=wallet_config.timeLock() + 1)
    
    # Confirm whitelist
    tx = paymaster.confirmWhitelistAddr(wallet.address, addr, sender=owner)
    
    # Check events
    events = filter_logs(paymaster, "WhitelistAddrConfirmed")
    assert len(events) == 1
    event = events[0]
    assert event.user == wallet.address
    assert event.addr == addr
    assert event.initiatedBlock == initiated_block
    assert event.confirmBlock == confirm_block
    assert event.confirmedBy == owner
    
    # Verify whitelisted
    assert wallet_config.isWhitelisted(addr)
    
    # Verify pending cleared
    pending = wallet_config.pendingWhitelist(addr)
    assert pending[0] == 0  # initiatedBlock cleared


def test_confirm_whitelist_no_pending(setup_contracts):
    """Test cannot confirm whitelist without pending"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    owner = ctx['owner']
    addr = boa.env.generate_address()
    
    with boa.reverts("no pending whitelist"):
        paymaster.confirmWhitelistAddr(wallet.address, addr, sender=owner)


# Test cancelling pending whitelist


def test_cancel_pending_whitelist_addr(setup_contracts):
    """Test cancelling pending whitelist"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    addr = boa.env.generate_address()
    
    # Add pending whitelist
    paymaster.addWhitelistAddr(wallet.address, addr, sender=owner)
    
    # Get pending info
    pending = wallet_config.pendingWhitelist(addr)
    initiated_block = pending[0]
    confirm_block = pending[1]
    
    # Cancel pending
    tx = paymaster.cancelPendingWhitelistAddr(wallet.address, addr, sender=owner)
    
    # Check events
    events = filter_logs(paymaster, "WhitelistAddrCancelled")
    assert len(events) == 1
    event = events[0]
    assert event.user == wallet.address
    assert event.addr == addr
    assert event.initiatedBlock == initiated_block
    assert event.confirmBlock == confirm_block
    assert event.cancelledBy == owner
    
    # Verify pending cleared
    pending = wallet_config.pendingWhitelist(addr)
    assert pending[0] == 0
    
    # Verify not whitelisted
    assert not wallet_config.isWhitelisted(addr)


def test_cancel_pending_whitelist_no_pending(setup_contracts):
    """Test cannot cancel whitelist without pending"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    owner = ctx['owner']
    addr = boa.env.generate_address()
    
    with boa.reverts("no pending whitelist"):
        paymaster.cancelPendingWhitelistAddr(wallet.address, addr, sender=owner)


# Test removing whitelist addresses


def test_remove_whitelist_addr(setup_contracts):
    """Test removing whitelist address"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    addr = boa.env.generate_address()
    
    # First add and confirm whitelist
    paymaster.addWhitelistAddr(wallet.address, addr, sender=owner)
    boa.env.time_travel(blocks=wallet_config.timeLock() + 1)
    paymaster.confirmWhitelistAddr(wallet.address, addr, sender=owner)
    
    # Verify whitelisted
    assert wallet_config.isWhitelisted(addr)
    
    # Remove whitelist
    tx = paymaster.removeWhitelistAddr(wallet.address, addr, sender=owner)
    
    # Check events
    events = filter_logs(paymaster, "WhitelistAddrRemoved")
    assert len(events) == 1
    event = events[0]
    assert event.user == wallet.address
    assert event.addr == addr
    assert event.removedBy == owner
    
    # Verify no longer whitelisted
    assert not wallet_config.isWhitelisted(addr)


def test_remove_whitelist_not_whitelisted(setup_contracts):
    """Test cannot remove address that is not whitelisted"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    owner = ctx['owner']
    addr = boa.env.generate_address()
    
    with boa.reverts("not whitelisted"):
        paymaster.removeWhitelistAddr(wallet.address, addr, sender=owner)


# Test manager permissions for whitelist


def test_manager_whitelist_permissions(setup_contracts, createManagerSettings, createWhitelistPerms, createGlobalManagerSettings):
    """Test manager permissions for whitelist operations"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    boss_validator = ctx['boss_validator']
    owner = ctx['owner']
    manager = ctx['manager']
    addr = boa.env.generate_address()
    
    # First set global whitelist permissions to allow managers to add
    global_whitelist_perms = createWhitelistPerms(
        _canAddPending=True,
        _canConfirm=True,
        _canCancel=True,
        _canRemove=True
    )
    global_settings = createGlobalManagerSettings(
        _whitelistPerms=global_whitelist_perms
    )
    wallet_config.setGlobalManagerSettings(global_settings, sender=boss_validator.address)
    
    # Add manager with whitelist permissions
    whitelist_perms = createWhitelistPerms(
        _canAddPending=True,
        _canConfirm=True,
        _canCancel=True,
        _canRemove=True
    )
    manager_settings = createManagerSettings(_whitelistPerms=whitelist_perms)
    wallet_config.addManager(manager, manager_settings, sender=boss_validator.address)
    
    # Manager can add pending whitelist
    tx = paymaster.addWhitelistAddr(wallet.address, addr, sender=manager)
    events = filter_logs(paymaster, "WhitelistAddrPending")
    assert len(events) == 1
    assert events[0].addedBy == manager
    
    # Advance past timelock
    boa.env.time_travel(blocks=wallet_config.timeLock() + 1)
    
    # Manager can confirm
    tx = paymaster.confirmWhitelistAddr(wallet.address, addr, sender=manager)
    events = filter_logs(paymaster, "WhitelistAddrConfirmed")
    assert len(events) == 1
    assert events[0].confirmedBy == manager
    
    # Manager can remove
    tx = paymaster.removeWhitelistAddr(wallet.address, addr, sender=manager)
    events = filter_logs(paymaster, "WhitelistAddrRemoved")
    assert len(events) == 1
    assert events[0].removedBy == manager


def test_manager_limited_whitelist_permissions(setup_contracts, createManagerSettings, createWhitelistPerms):
    """Test manager with limited whitelist permissions"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    boss_validator = ctx['boss_validator']
    owner = ctx['owner']
    manager = boa.env.generate_address()
    addr = boa.env.generate_address()
    
    # Add manager with limited permissions (can only confirm and cancel)
    whitelist_perms = createWhitelistPerms(
        _canAddPending=False,
        _canConfirm=True,
        _canCancel=True,
        _canRemove=False
    )
    manager_settings = createManagerSettings(_whitelistPerms=whitelist_perms)
    wallet_config.addManager(manager, manager_settings, sender=boss_validator.address)
    
    # Manager cannot add pending
    with boa.reverts("no perms"):
        paymaster.addWhitelistAddr(wallet.address, addr, sender=manager)
    
    # Owner adds pending
    paymaster.addWhitelistAddr(wallet.address, addr, sender=owner)
    
    # Manager can cancel
    tx = paymaster.cancelPendingWhitelistAddr(wallet.address, addr, sender=manager)
    events = filter_logs(paymaster, "WhitelistAddrCancelled")
    assert len(events) == 1
    assert events[0].cancelledBy == manager
    
    # Add and confirm whitelist (by owner)
    paymaster.addWhitelistAddr(wallet.address, addr, sender=owner)
    boa.env.time_travel(blocks=wallet_config.timeLock() + 1)
    paymaster.confirmWhitelistAddr(wallet.address, addr, sender=owner)
    
    # Manager cannot remove
    with boa.reverts("no perms"):
        paymaster.removeWhitelistAddr(wallet.address, addr, sender=manager)


def test_whitelist_and_payee_interaction(setup_contracts, createPayeeLimits):
    """Test interaction between whitelist and payee systems"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    addr = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    
    # First whitelist an address
    paymaster.addWhitelistAddr(wallet.address, addr, sender=owner)
    boa.env.time_travel(blocks=wallet_config.timeLock() + 1)
    paymaster.confirmWhitelistAddr(wallet.address, addr, sender=owner)
    
    # Try to add whitelisted address as payee
    unit_limits = createPayeeLimits()
    usd_limits = createPayeeLimits()
    
    with boa.reverts("already whitelisted"):
        paymaster.addPayee(
            wallet.address,
            addr,
            False,
            ONE_DAY_IN_BLOCKS,
            10,
            0,
            False,
            alpha_token.address,
            False,
            unit_limits,
            usd_limits,
            sender=owner
        )
    
    # Remove from whitelist
    paymaster.removeWhitelistAddr(wallet.address, addr, sender=owner)
    
    # Now can add as payee
    tx = paymaster.addPayee(
        wallet.address,
        addr,
        False,
        ONE_DAY_IN_BLOCKS,
        10,
        0,
        False,
        alpha_token.address,
        False,
        unit_limits,
        usd_limits,
        sender=owner
    )
    
    assert wallet_config.isRegisteredPayee(addr)


def test_whitelist_validation_always_passes(setup_contracts):
    """Test that whitelisted addresses always pass validation"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    addr = boa.env.generate_address()
    alpha_token = ctx['alpha_token']
    
    # Whitelist address
    paymaster.addWhitelistAddr(wallet.address, addr, sender=owner)
    boa.env.time_travel(blocks=wallet_config.timeLock() + 1)
    paymaster.confirmWhitelistAddr(wallet.address, addr, sender=owner)
    
    # Any amount should be valid for whitelisted addresses
    huge_amount = 1000000 * EIGHTEEN_DECIMALS
    huge_usd_value = 1000000 * EIGHTEEN_DECIMALS
    
    is_valid, data = paymaster.isValidPayee(
        wallet.address,
        addr,
        alpha_token.address,
        huge_amount,
        huge_usd_value
    )
    
    assert is_valid
    # Data should be empty for whitelisted
    assert data[0] == 0
    assert data[1] == 0
    assert data[2] == 0


def test_backpack_cancel_whitelist(setup_contracts, undy_hq, backpack):
    """Test that Backpack can cancel pending whitelist in non-eject mode"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    addr = boa.env.generate_address()
    
    # Backpack is already passed as parameter
    
    # Add pending whitelist
    paymaster.addWhitelistAddr(wallet.address, addr, sender=owner)
    
    # Backpack can cancel
    tx = paymaster.cancelPendingWhitelistAddr(wallet.address, addr, sender=backpack.address)
    
    # Check events
    events = filter_logs(paymaster, "WhitelistAddrCancelled")
    assert len(events) == 1
    assert events[0].cancelledBy == backpack.address
    
    # Verify cancelled
    pending = wallet_config.pendingWhitelist(addr)
    assert pending[0] == 0


def test_multiple_whitelist_operations(setup_contracts):
    """Test multiple whitelist operations in sequence"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    
    # Create multiple addresses
    addrs = [boa.env.generate_address() for _ in range(3)]
    
    # Add all as pending
    for addr in addrs:
        paymaster.addWhitelistAddr(wallet.address, addr, sender=owner)
    
    # Advance past timelock
    boa.env.time_travel(blocks=wallet_config.timeLock() + 1)
    
    # Confirm first two
    paymaster.confirmWhitelistAddr(wallet.address, addrs[0], sender=owner)
    paymaster.confirmWhitelistAddr(wallet.address, addrs[1], sender=owner)
    
    # Cancel third
    paymaster.cancelPendingWhitelistAddr(wallet.address, addrs[2], sender=owner)
    
    # Verify states
    assert wallet_config.isWhitelisted(addrs[0])
    assert wallet_config.isWhitelisted(addrs[1])
    assert not wallet_config.isWhitelisted(addrs[2])
    
    # Remove first
    paymaster.removeWhitelistAddr(wallet.address, addrs[0], sender=owner)
    
    # Final states
    assert not wallet_config.isWhitelisted(addrs[0])
    assert wallet_config.isWhitelisted(addrs[1])
    assert not wallet_config.isWhitelisted(addrs[2])


def test_backpack_can_remove_from_whitelist(setup_contracts, backpack):
    """Test that Backpack can remove addresses from whitelist in non-eject mode"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    addr = boa.env.generate_address()
    
    # First add and confirm whitelist address
    paymaster.addWhitelistAddr(wallet.address, addr, sender=owner)
    boa.env.time_travel(blocks=wallet_config.timeLock() + 1)
    paymaster.confirmWhitelistAddr(wallet.address, addr, sender=owner)
    
    # Verify whitelisted
    assert wallet_config.isWhitelisted(addr)
    
    # Backpack removes from whitelist
    tx = paymaster.removeWhitelistAddr(wallet.address, addr, sender=backpack.address)
    
    # Check event
    events = filter_logs(paymaster, "WhitelistAddrRemoved")
    assert len(events) == 1
    assert events[0].user == wallet.address
    assert events[0].addr == addr
    assert events[0].removedBy == backpack.address
    
    # Verify no longer whitelisted
    assert not wallet_config.isWhitelisted(addr)


def test_address_can_remove_themselves_from_whitelist(setup_contracts):
    """Test that addresses can remove themselves from whitelist"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    addr = ctx['addr1']  # Use alice address
    
    # First add and confirm whitelist address
    paymaster.addWhitelistAddr(wallet.address, addr, sender=owner)
    boa.env.time_travel(blocks=wallet_config.timeLock() + 1)
    paymaster.confirmWhitelistAddr(wallet.address, addr, sender=owner)
    
    # Verify whitelisted
    assert wallet_config.isWhitelisted(addr)
    
    # Address removes themselves from whitelist
    tx = paymaster.removeWhitelistAddr(wallet.address, addr, sender=addr)
    
    # Check event
    events = filter_logs(paymaster, "WhitelistAddrRemoved")
    assert len(events) == 1
    assert events[0].user == wallet.address
    assert events[0].addr == addr
    assert events[0].removedBy == addr
    
    # Verify no longer whitelisted
    assert not wallet_config.isWhitelisted(addr)


def test_non_authorized_cannot_remove_from_whitelist(setup_contracts):
    """Test that non-authorized addresses cannot remove from whitelist"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    owner = ctx['owner']
    addr = boa.env.generate_address()
    alice = ctx['addr1']  # Random address
    
    # First add and confirm whitelist address
    paymaster.addWhitelistAddr(wallet.address, addr, sender=owner)
    boa.env.time_travel(blocks=wallet_config.timeLock() + 1)
    paymaster.confirmWhitelistAddr(wallet.address, addr, sender=owner)
    
    # Random address cannot remove from whitelist
    with boa.reverts("no perms"):
        paymaster.removeWhitelistAddr(wallet.address, addr, sender=alice)


def test_manager_cannot_remove_others_from_whitelist(setup_contracts, createManagerSettings, 
                                                    createWhitelistPerms, createGlobalManagerSettings):
    """Test that manager without remove permission cannot remove others from whitelist"""
    ctx = setup_contracts
    paymaster = ctx['paymaster']
    wallet = ctx['wallet']
    wallet_config = ctx['wallet_config']
    boss_validator = ctx['boss_validator']
    owner = ctx['owner']
    manager = ctx['manager']
    addr = boa.env.generate_address()
    
    # Set global whitelist permissions
    global_whitelist_perms = createWhitelistPerms(
        _canAddPending=True,
        _canConfirm=True,
        _canCancel=True,
        _canRemove=False  # No remove permission
    )
    global_settings = createGlobalManagerSettings(
        _whitelistPerms=global_whitelist_perms
    )
    wallet_config.setGlobalManagerSettings(global_settings, sender=boss_validator.address)
    
    # Add manager without remove permission
    whitelist_perms = createWhitelistPerms(
        _canAddPending=True,
        _canConfirm=True,
        _canCancel=True,
        _canRemove=False  # No remove permission
    )
    manager_settings = createManagerSettings(_whitelistPerms=whitelist_perms)
    wallet_config.addManager(manager, manager_settings, sender=boss_validator.address)
    
    # Add and confirm whitelist address
    paymaster.addWhitelistAddr(wallet.address, addr, sender=owner)
    boa.env.time_travel(blocks=wallet_config.timeLock() + 1)
    paymaster.confirmWhitelistAddr(wallet.address, addr, sender=owner)
    
    # Manager without permission cannot remove
    with boa.reverts("no perms"):
        paymaster.removeWhitelistAddr(wallet.address, addr, sender=manager)