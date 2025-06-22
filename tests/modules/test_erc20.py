import pytest
import boa

from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS, MAX_UINT256
from conf_utils import filter_logs
from config.BluePrint import PARAMS


@pytest.fixture(scope="module")
def mock_undy_hq(governance, fork, undy_token):
    return boa.load(
        "contracts/registries/UndyHq.vy",
        undy_token,
        governance,
        PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"],
        PARAMS[fork]["UNDY_HQ_MAX_GOV_TIMELOCK"],
        PARAMS[fork]["UNDY_HQ_MIN_REG_TIMELOCK"],
        PARAMS[fork]["UNDY_HQ_MAX_REG_TIMELOCK"],
        name="undy_hq",
    )


@pytest.fixture(scope="module")
def mock_dept_can_mint_undy(mock_undy_hq):
    return boa.load("contracts/mock/MockDept.vy", mock_undy_hq, True, name="mock_dept_can_mint_undy")


@pytest.fixture(scope="module") 
def mock_dept_cannot_mint_undy(mock_undy_hq):
    return boa.load("contracts/mock/MockDept.vy", mock_undy_hq, False, name="mock_dept_cannot_mint_undy")

# tests


def test_undy_token_basic_info(undy_token):
    """Test basic ERC20 token information for Undy Token"""
    assert undy_token.name() == "Undy DAO Governance Token"
    assert undy_token.symbol() == "UNDY"
    assert undy_token.decimals() == 18
    assert undy_token.totalSupply() == 10_000_000 * EIGHTEEN_DECIMALS


def test_undy_token_transfer(undy_token, whale, bob, alice):
    """Test basic ERC20 transfer functionality for Undy Token"""
    initial_balance = undy_token.balanceOf(whale)
    transfer_amount = 100 * EIGHTEEN_DECIMALS

    # Test successful transfer
    assert undy_token.transfer(bob, transfer_amount, sender=whale)

    # Test transfer event
    log = filter_logs(undy_token, "Transfer")[0]
    assert log.sender == whale
    assert log.recipient == bob
    assert log.amount == transfer_amount

    assert undy_token.balanceOf(whale) == initial_balance - transfer_amount
    assert undy_token.balanceOf(bob) == transfer_amount

    # Test transfer to zero address
    with boa.reverts("invalid recipient"):
        undy_token.transfer(ZERO_ADDRESS, transfer_amount, sender=whale)

    # Test transfer to self
    with boa.reverts("invalid recipient"):
        undy_token.transfer(undy_token.address, transfer_amount, sender=whale)

    # Test transfer zero amount
    with boa.reverts("cannot transfer 0 amount"):
        undy_token.transfer(bob, 0, sender=whale)

    # Test insufficient balance
    with boa.reverts("insufficient funds"):
        undy_token.transfer(whale, transfer_amount, sender=alice)


def test_undy_token_approve(undy_token, whale, bob):
    """Test ERC20 approve functionality for Undy Token"""
    approve_amount = 100 * EIGHTEEN_DECIMALS

    # Test successful approval
    assert undy_token.approve(bob, approve_amount, sender=whale)

    # Test approval event
    log = filter_logs(undy_token, "Approval")[0]
    assert log.owner == whale
    assert log.spender == bob
    assert log.amount == approve_amount

    assert undy_token.allowance(whale, bob) == approve_amount

    # Test approve zero address
    with boa.reverts("invalid spender"):
        undy_token.approve(ZERO_ADDRESS, approve_amount, sender=whale)


def test_undy_token_transfer_from(undy_token, whale, bob, alice):
    """Test ERC20 transferFrom functionality for Undy Token"""
    approve_amount = 100 * EIGHTEEN_DECIMALS
    transfer_amount = 50 * EIGHTEEN_DECIMALS

    # Approve bob to spend whale's tokens
    undy_token.approve(bob, approve_amount, sender=whale)

    # Test successful transferFrom
    assert undy_token.transferFrom(whale, alice, transfer_amount, sender=bob)

    # Test transferFrom event
    log = filter_logs(undy_token, "Transfer")[0]
    assert log.sender == whale
    assert log.recipient == alice
    assert log.amount == transfer_amount

    assert undy_token.balanceOf(alice) == transfer_amount
    assert undy_token.allowance(whale, bob) == approve_amount - transfer_amount

    # Test insufficient allowance
    with boa.reverts("insufficient allowance"):
        undy_token.transferFrom(whale, alice, approve_amount, sender=bob)

    # Test transferFrom zero address
    with boa.reverts("invalid recipient"):
        undy_token.transferFrom(whale, ZERO_ADDRESS, transfer_amount, sender=bob)

    # Test transferFrom to self
    with boa.reverts("invalid recipient"):
        undy_token.transferFrom(whale, undy_token.address, transfer_amount, sender=bob)

    # Test transferFrom zero amount
    with boa.reverts("cannot transfer 0 amount"):
        undy_token.transferFrom(whale, alice, 0, sender=bob)


def test_undy_token_increase_decrease_allowance(undy_token, whale, bob):
    """Test increaseAllowance and decreaseAllowance functionality for Undy Token"""
    initial_amount = 100 * EIGHTEEN_DECIMALS
    increase_amount = 50 * EIGHTEEN_DECIMALS
    decrease_amount = 30 * EIGHTEEN_DECIMALS

    # Set initial allowance
    undy_token.approve(bob, initial_amount, sender=whale)

    # Test increaseAllowance
    assert undy_token.increaseAllowance(bob, increase_amount, sender=whale)
    assert undy_token.allowance(whale, bob) == initial_amount + increase_amount

    # Test decreaseAllowance
    assert undy_token.decreaseAllowance(bob, decrease_amount, sender=whale)
    assert undy_token.allowance(whale, bob) == initial_amount + increase_amount - decrease_amount

    # Test decreaseAllowance with amount greater than current allowance
    current_allowance = undy_token.allowance(whale, bob)
    assert undy_token.decreaseAllowance(bob, current_allowance + 1, sender=whale)
    assert undy_token.allowance(whale, bob) == 0  # Should be capped at 0

    # Test increaseAllowance with max uint256
    max_uint = 2**256 - 1
    current_allowance = undy_token.allowance(whale, bob)
    max_uint - current_allowance
    assert undy_token.increaseAllowance(bob, max_uint, sender=whale)
    assert undy_token.allowance(whale, bob) == max_uint  # Should be capped at max_uint


def test_undy_token_pause_functionality(undy_token, whale, bob, governance):
    """Test token pause functionality"""
    # Test initial state
    assert not undy_token.isPaused()

    # Test pause
    undy_token.pause(True, sender=governance.address)
    assert undy_token.isPaused()

    # Test operations when paused
    with boa.reverts("token paused"):
        undy_token.transfer(bob, 100 * EIGHTEEN_DECIMALS, sender=whale)
    
    with boa.reverts("token paused"):
        undy_token.approve(bob, 100 * EIGHTEEN_DECIMALS, sender=whale)
    
    with boa.reverts("token paused"):
        undy_token.increaseAllowance(bob, 100 * EIGHTEEN_DECIMALS, sender=whale)
    
    with boa.reverts("token paused"):
        undy_token.decreaseAllowance(bob, 100 * EIGHTEEN_DECIMALS, sender=whale)
    
    with boa.reverts("token paused"):
        undy_token.burn(100 * EIGHTEEN_DECIMALS, sender=whale)

    # Test unpause
    undy_token.pause(False, sender=governance.address)
    assert not undy_token.isPaused()

    # Verify operations work again
    assert undy_token.transfer(bob, 100 * EIGHTEEN_DECIMALS, sender=whale)
    assert undy_token.approve(bob, 100 * EIGHTEEN_DECIMALS, sender=whale)


def test_undy_token_blacklist_functionality(undy_token, whale, bob, switchboard, governance):
    """Test token blacklist functionality"""
    # Test initial state
    assert not undy_token.blacklisted(whale)
    assert not undy_token.blacklisted(bob)

    # Test blacklist
    undy_token.setBlacklist(whale, True, sender=switchboard.address)
    assert undy_token.blacklisted(whale)

    # Test operations when blacklisted
    with boa.reverts("sender blacklisted"):
        undy_token.transfer(bob, 100 * EIGHTEEN_DECIMALS, sender=whale)
    
    with boa.reverts("owner blacklisted"):
        undy_token.approve(bob, 100 * EIGHTEEN_DECIMALS, sender=whale)

    # Test blacklist spender
    undy_token.setBlacklist(bob, True, sender=switchboard.address)
    assert undy_token.blacklisted(bob)

    undy_token.setBlacklist(whale, False, sender=switchboard.address)

    # Test operations with blacklisted spender
    with boa.reverts("spender blacklisted"):
        undy_token.approve(bob, 100 * EIGHTEEN_DECIMALS, sender=whale)

    undy_token.setBlacklist(whale, True, sender=switchboard.address)

    # Test burn blacklisted tokens
    initial_balance = undy_token.balanceOf(whale)
    undy_token.burnBlacklistTokens(whale, sender=governance.address)
    assert undy_token.balanceOf(whale) == 0
    assert undy_token.totalSupply() == initial_balance - initial_balance

    # Test unblacklist
    undy_token.setBlacklist(whale, False, sender=switchboard.address)
    assert not undy_token.blacklisted(whale)


def test_undy_token_undy_hq_changes(undy_token, governance, undy_hq_deploy, mock_undy_hq):
    """Test UndyHq change functionality"""

    # Test initial state
    assert not undy_token.hasPendingHqChange()
    
    # Test initiate hq change
    undy_token.initiateHqChange(mock_undy_hq, sender=governance.address)
    assert undy_token.hasPendingHqChange()
    
    # Test confirm before time lock
    with boa.reverts("time lock not reached"):
        undy_token.confirmHqChange(sender=governance.address)
    
    # Time travel past time lock
    boa.env.time_travel(blocks=undy_token.hqChangeTimeLock())
    
    # Test confirm hq change
    assert undy_token.confirmHqChange(sender=governance.address)
    assert not undy_token.hasPendingHqChange()
    assert undy_token.undyHq() == mock_undy_hq.address
    
    # Test cancel hq change
    undy_token.initiateHqChange(undy_hq_deploy, sender=governance.address)
    undy_token.cancelHqChange(sender=governance.address)
    assert not undy_token.hasPendingHqChange()


def test_undy_token_time_lock_config(undy_token, governance):
    """Test time lock configuration"""
    min_time_lock = undy_token.minHqTimeLock()
    max_time_lock = undy_token.maxHqTimeLock()
    
    # Test invalid time locks
    with boa.reverts("invalid time lock"):
        undy_token.setHqChangeTimeLock(min_time_lock - 1, sender=governance.address)
    
    with boa.reverts("invalid time lock"):
        undy_token.setHqChangeTimeLock(max_time_lock + 1, sender=governance.address)
    
    # Test valid time lock
    new_time_lock = min_time_lock + 100
    assert undy_token.setHqChangeTimeLock(new_time_lock, sender=governance.address)
    assert undy_token.hqChangeTimeLock() == new_time_lock


def test_undy_token_edge_cases(undy_token, whale, bob, alice):
    """Test edge cases for token operations"""
    # Test transfer to self
    with boa.reverts("invalid recipient"):
        undy_token.transfer(undy_token.address, 100 * EIGHTEEN_DECIMALS, sender=whale)
    
    # Test transfer to zero address
    with boa.reverts("invalid recipient"):
        undy_token.transfer(ZERO_ADDRESS, 100 * EIGHTEEN_DECIMALS, sender=whale)
    
    # Test approve zero address
    with boa.reverts("invalid spender"):
        undy_token.approve(ZERO_ADDRESS, 100 * EIGHTEEN_DECIMALS, sender=whale)
    
    # Test transferFrom to self
    undy_token.approve(bob, 100 * EIGHTEEN_DECIMALS, sender=whale)
    with boa.reverts("invalid recipient"):
        undy_token.transferFrom(whale, undy_token.address, 50 * EIGHTEEN_DECIMALS, sender=bob)
    
    # Test transferFrom to zero address
    with boa.reverts("invalid recipient"):
        undy_token.transferFrom(whale, ZERO_ADDRESS, 50 * EIGHTEEN_DECIMALS, sender=bob)
    
    # Test transfer zero amount
    with boa.reverts("cannot transfer 0 amount"):
        undy_token.transfer(bob, 0, sender=whale)
    
    # Test transferFrom zero amount
    with boa.reverts("cannot transfer 0 amount"):
        undy_token.transferFrom(whale, alice, 0, sender=bob)
    
    # Test burn zero amount (should succeed)
    initial_balance = undy_token.balanceOf(whale)
    initial_supply = undy_token.totalSupply()
    assert undy_token.burn(0, sender=whale)
    assert undy_token.balanceOf(whale) == initial_balance
    assert undy_token.totalSupply() == initial_supply


def test_undy_token_minting_permissions(undy_token, undy_hq, mock_dept_can_mint_undy, mock_dept_cannot_mint_undy, alice, governance):
    """Test minting permissions"""
    time_lock = undy_hq.registryChangeTimeLock()
    mint_amount = 100 * EIGHTEEN_DECIMALS
    
    # Register and configure department that can mint
    undy_hq.startAddNewAddressToRegistry(mock_dept_can_mint_undy, "Undy Minter", sender=governance.address)
    boa.env.time_travel(blocks=time_lock)
    can_mint_reg_id = undy_hq.confirmNewAddressToRegistry(mock_dept_can_mint_undy, sender=governance.address)
    
    undy_hq.initiateHqConfigChange(can_mint_reg_id, True, False, sender=governance.address)  # canMintUndy=True
    boa.env.time_travel(blocks=time_lock)
    undy_hq.confirmHqConfigChange(can_mint_reg_id, sender=governance.address)
    
    # Register department that cannot mint (no config change needed)
    undy_hq.startAddNewAddressToRegistry(mock_dept_cannot_mint_undy, "No Mint Dept", sender=governance.address)
    boa.env.time_travel(blocks=time_lock)
    cannot_mint_reg_id = undy_hq.confirmNewAddressToRegistry(mock_dept_cannot_mint_undy, sender=governance.address)
    
    # Test that authorized department can mint
    initial_balance = undy_token.balanceOf(alice)
    initial_supply = undy_token.totalSupply()
    
    assert undy_token.mint(alice, mint_amount, sender=mock_dept_can_mint_undy.address)
    assert undy_token.balanceOf(alice) == initial_balance + mint_amount
    assert undy_token.totalSupply() == initial_supply + mint_amount
    
    # Test that unauthorized department cannot mint
    with boa.reverts("cannot mint"):
        undy_token.mint(alice, mint_amount, sender=mock_dept_cannot_mint_undy.address)


def test_undy_token_minting_circuit_breaker(undy_token, undy_hq, mock_dept_can_mint_undy, alice, governance):
    """Test minting circuit breaker functionality"""
    time_lock = undy_hq.registryChangeTimeLock()
    mint_amount = 100 * EIGHTEEN_DECIMALS
    
    # Register and configure department that can mint
    undy_hq.startAddNewAddressToRegistry(mock_dept_can_mint_undy, "Undy Minter", sender=governance.address)
    boa.env.time_travel(blocks=time_lock)
    can_mint_reg_id = undy_hq.confirmNewAddressToRegistry(mock_dept_can_mint_undy, sender=governance.address)
    
    undy_hq.initiateHqConfigChange(can_mint_reg_id, True, False, sender=governance.address)  # canMintUndy=True
    boa.env.time_travel(blocks=time_lock)
    undy_hq.confirmHqConfigChange(can_mint_reg_id, sender=governance.address)
    
    # Test that department can mint when enabled (default state)
    assert undy_token.mint(alice, mint_amount, sender=mock_dept_can_mint_undy.address)
    
    # Disable minting globally
    undy_hq.setMintingEnabled(False, sender=governance.address)
    
    # Test that even authorized department cannot mint when circuit breaker is active
    with boa.reverts("cannot mint"):
        undy_token.mint(alice, mint_amount, sender=mock_dept_can_mint_undy.address)
    
    # Re-enable minting
    undy_hq.setMintingEnabled(True, sender=governance.address)
    
    # Test that department can mint again
    assert undy_token.mint(alice, mint_amount, sender=mock_dept_can_mint_undy.address)


def test_undy_token_minting_edge_cases(undy_token, undy_hq, mock_dept_can_mint_undy, whale, switchboard, alice, governance):
    """Test minting edge cases"""
    time_lock = undy_hq.registryChangeTimeLock()
    
    # Register and configure department that can mint
    undy_hq.startAddNewAddressToRegistry(mock_dept_can_mint_undy, "Undy Minter", sender=governance.address)
    boa.env.time_travel(blocks=time_lock)
    can_mint_reg_id = undy_hq.confirmNewAddressToRegistry(mock_dept_can_mint_undy, sender=governance.address)
    
    undy_hq.initiateHqConfigChange(can_mint_reg_id, True, False, sender=governance.address)  # canMintUndy=True
    boa.env.time_travel(blocks=time_lock)
    undy_hq.confirmHqConfigChange(can_mint_reg_id, sender=governance.address)
    
    # Test minting to zero address
    with boa.reverts("invalid recipient"):
        undy_token.mint(ZERO_ADDRESS, 100 * EIGHTEEN_DECIMALS, sender=mock_dept_can_mint_undy.address)
    
    # Test minting to self
    with boa.reverts("invalid recipient"):
        undy_token.mint(undy_token.address, 100 * EIGHTEEN_DECIMALS, sender=mock_dept_can_mint_undy.address)
    
    # Test minting to blacklisted address
    undy_token.setBlacklist(whale, True, sender=switchboard.address)
    with boa.reverts("blacklisted"):
        undy_token.mint(whale, 100 * EIGHTEEN_DECIMALS, sender=mock_dept_can_mint_undy.address)
    
    # Test minting when paused
    undy_token.pause(True, sender=governance.address)
    with boa.reverts("token paused"):
        undy_token.mint(alice, 100 * EIGHTEEN_DECIMALS, sender=mock_dept_can_mint_undy.address)


def test_undy_token_transfer_edge_cases(undy_token, whale, bob, governance, switchboard):
    """Test transfer edge cases"""
    # Test transfer with insufficient balance
    with boa.reverts("insufficient funds"):
        undy_token.transfer(whale, 100 * EIGHTEEN_DECIMALS, sender=bob)
    
    # Test transfer when paused
    undy_token.pause(True, sender=governance.address)
    with boa.reverts("token paused"):
        undy_token.transfer(bob, 100 * EIGHTEEN_DECIMALS, sender=whale)
    undy_token.pause(False, sender=governance.address)

    # Test transfer when sender is blacklisted
    undy_token.setBlacklist(whale, True, sender=switchboard.address)
    with boa.reverts("sender blacklisted"):
        undy_token.transfer(bob, 100 * EIGHTEEN_DECIMALS, sender=whale)
    
    # Test transfer when recipient is blacklisted
    undy_token.setBlacklist(whale, False, sender=switchboard.address)
    undy_token.setBlacklist(bob, True, sender=switchboard.address)
    with boa.reverts("recipient blacklisted"):
        undy_token.transfer(bob, 100 * EIGHTEEN_DECIMALS, sender=whale)


def test_undy_token_transfer_from_edge_cases(undy_token, whale, bob, alice, governance, switchboard):
    """Test transferFrom edge cases"""
    # Set up initial state
    transfer_amount = 100 * EIGHTEEN_DECIMALS
    # Remove this line as it's trying to transfer to same address
    # undy_token.transfer(whale, transfer_amount, sender=whale)
    
    # Test transferFrom with infinite allowance
    undy_token.approve(bob, MAX_UINT256, sender=whale)
    assert undy_token.transferFrom(whale, alice, transfer_amount, sender=bob)
    assert undy_token.allowance(whale, bob) == MAX_UINT256
    
    # Test transferFrom when spender is blacklisted
    undy_token.setBlacklist(bob, True, sender=switchboard.address)
    with boa.reverts("spender blacklisted"):
        undy_token.transferFrom(whale, alice, transfer_amount, sender=bob)
    
    # Test transferFrom when paused
    undy_token.setBlacklist(bob, False, sender=switchboard.address)
    undy_token.pause(True, sender=governance.address)
    with boa.reverts("token paused"):
        undy_token.transferFrom(whale, alice, transfer_amount, sender=bob)
    undy_token.pause(False, sender=governance.address)

    undy_token.transfer(alice, undy_token.balanceOf(whale), sender=whale)

    # Test transferFrom with insufficient balance
    with boa.reverts("insufficient funds"):
        undy_token.transferFrom(whale, alice, transfer_amount, sender=bob)


def test_undy_token_undy_hq_edge_cases(undy_token, governance, bob, mock_undy_hq, mock_rando_contract):
    """Test UndyHq edge cases"""
    # Test invalid UndyHq address (zero address)
    with boa.reverts("invalid new hq"):
        undy_token.initiateHqChange(ZERO_ADDRESS, sender=governance.address)
    
    # Test invalid UndyHq address (non-contract)
    with boa.reverts("invalid new hq"):
        undy_token.initiateHqChange(bob, sender=governance.address)
    
    # Test invalid UndyHq address (same as current)
    with boa.reverts("invalid new hq"):
        undy_token.initiateHqChange(undy_token.undyHq(), sender=governance.address)
    
    # Initiate a gov change in the mock UndyHq
    mock_undy_hq.startGovernanceChange(mock_rando_contract, sender=governance.address)
    assert mock_undy_hq.hasPendingGovChange()
    
    # Try to change to UndyHq with pending gov change
    with boa.reverts("invalid new hq"):
        undy_token.initiateHqChange(mock_undy_hq, sender=governance.address)


def test_undy_token_blacklist_edge_cases(undy_token, undy_hq, governance, switchboard, mock_dept_can_mint_undy):
    """Test blacklist edge cases"""
    time_lock = undy_hq.registryChangeTimeLock()
    
    # Register and configure department that can mint
    undy_hq.startAddNewAddressToRegistry(mock_dept_can_mint_undy, "Undy Minter", sender=governance.address)
    boa.env.time_travel(blocks=time_lock)
    can_mint_reg_id = undy_hq.confirmNewAddressToRegistry(mock_dept_can_mint_undy, sender=governance.address)
    
    undy_hq.initiateHqConfigChange(can_mint_reg_id, True, False, sender=governance.address)  # canMintUndy=True
    boa.env.time_travel(blocks=time_lock)
    undy_hq.confirmHqConfigChange(can_mint_reg_id, sender=governance.address)
    
    # Test blacklisting self
    with boa.reverts("invalid blacklist recipient"):
        undy_token.setBlacklist(undy_token.address, True, sender=switchboard.address)
    
    # Test blacklisting zero address
    with boa.reverts("invalid blacklist recipient"):
        undy_token.setBlacklist(ZERO_ADDRESS, True, sender=switchboard.address)
    
    # Test burning blacklisted tokens with specific amount
    test_address = boa.env.generate_address()
    
    # Mint tokens to test address
    undy_token.mint(test_address, 1000 * EIGHTEEN_DECIMALS, sender=mock_dept_can_mint_undy.address)
    undy_token.setBlacklist(test_address, True, sender=switchboard.address)
    
    burn_amount = 500 * EIGHTEEN_DECIMALS
    undy_token.burnBlacklistTokens(test_address, burn_amount, sender=governance.address)
    assert undy_token.balanceOf(test_address) == 500 * EIGHTEEN_DECIMALS


def test_undy_token_time_lock_edge_cases(undy_token, governance):
    """Test time lock edge cases"""
    min_time_lock = undy_token.minHqTimeLock()
    max_time_lock = undy_token.maxHqTimeLock()
    
    # Test time lock bounds
    with boa.reverts("invalid time lock"):
        undy_token.setHqChangeTimeLock(min_time_lock - 1, sender=governance.address)
    
    with boa.reverts("invalid time lock"):
        undy_token.setHqChangeTimeLock(max_time_lock + 1, sender=governance.address)
    
    # Test valid time lock changes
    new_time_lock = min_time_lock + 100
    assert undy_token.setHqChangeTimeLock(new_time_lock, sender=governance.address)
    
    # Test time lock change event
    log = filter_logs(undy_token, "HqChangeTimeLockModified")[0]
    assert log.newTimeLock == new_time_lock

    assert undy_token.hqChangeTimeLock() == new_time_lock


def test_undy_token_events(undy_token, whale, bob, governance, switchboard, mock_undy_hq):
    """Test token events"""
    # Test Transfer event
    transfer_amount = 100 * EIGHTEEN_DECIMALS
    assert undy_token.transfer(bob, transfer_amount, sender=whale)
    
    transfer_log = filter_logs(undy_token, "Transfer")[0]
    assert transfer_log.sender == whale
    assert transfer_log.recipient == bob
    assert transfer_log.amount == transfer_amount
    
    # Test Approval event
    approve_amount = 200 * EIGHTEEN_DECIMALS
    assert undy_token.approve(bob, approve_amount, sender=whale)
    
    approval_log = filter_logs(undy_token, "Approval")[0]
    assert approval_log.owner == whale
    assert approval_log.spender == bob
    assert approval_log.amount == approve_amount
    
    # Test BlacklistModified event
    assert undy_token.setBlacklist(bob, True, sender=switchboard.address)
    
    blacklist_log = filter_logs(undy_token, "BlacklistModified")[0]
    assert blacklist_log.addr == bob
    assert blacklist_log.isBlacklisted
    
    # Test TokenPauseModified event
    undy_token.pause(True, sender=governance.address)
    
    pause_log = filter_logs(undy_token, "TokenPauseModified")[0]
    assert pause_log.isPaused
      
    undy_token.initiateHqChange(mock_undy_hq, sender=governance.address)
    
    hq_change_log = filter_logs(undy_token, "HqChangeInitiated")[0]
    assert hq_change_log.prevHq == undy_token.undyHq()
    assert hq_change_log.newHq == mock_undy_hq.address
    assert hq_change_log.confirmBlock == boa.env.evm.patch.block_number + undy_token.hqChangeTimeLock()

