import pytest
import boa

from constants import ZERO_ADDRESS, EIGHTEEN_DECIMALS
from conf_utils import filter_logs


@pytest.fixture(scope="module")
def mock_dept_can_mint_undy(undy_hq_deploy):
    return boa.load("contracts/mock/MockDept.vy", undy_hq_deploy, True, name="mock_dept_can_mint_undy")


@pytest.fixture(scope="module") 
def mock_dept_cannot_mint_undy(undy_hq_deploy):
    return boa.load("contracts/mock/MockDept.vy", undy_hq_deploy, False, name="mock_dept_cannot_mint_undy")


#############
# Hq Config #
#############


def test_hq_config_change_basic(
    undy_hq,
    mock_dept_can_mint_undy,
    governance,
    bob,
):
    time_lock = undy_hq.registryChangeTimeLock()

    # Add department that can mint
    undy_hq.startAddNewAddressToRegistry(mock_dept_can_mint_undy, "Undy Minter", sender=governance.address)
    boa.env.time_travel(blocks=time_lock)
    dept_reg_id = undy_hq.confirmNewAddressToRegistry(mock_dept_can_mint_undy, sender=governance.address)

    # Test no perms
    with boa.reverts("no perms"):
        undy_hq.initiateHqConfigChange(dept_reg_id, True, False, sender=bob)

    # Start config change
    undy_hq.initiateHqConfigChange(dept_reg_id, True, False, sender=governance.address)
    
    # Verify pending event
    pending_log = filter_logs(undy_hq, "HqConfigChangeInitiated")[0]
    assert pending_log.regId == dept_reg_id
    assert pending_log.description == "Undy Minter"
    assert pending_log.canMintUndy
    assert not pending_log.canSetTokenBlacklist
    assert pending_log.confirmBlock == boa.env.evm.patch.block_number + time_lock

    # Verify pending state
    assert undy_hq.hasPendingHqConfigChange(dept_reg_id)
    pending = undy_hq.pendingHqConfig(dept_reg_id)
    assert pending.newHqConfig.canMintUndy
    assert not pending.newHqConfig.canSetTokenBlacklist
    assert pending.initiatedBlock == boa.env.evm.patch.block_number
    assert pending.confirmBlock == pending_log.confirmBlock

    # time lock not reached
    with boa.reverts("time lock not reached"):
        undy_hq.confirmHqConfigChange(dept_reg_id, sender=governance.address)

    # time travel
    boa.env.time_travel(blocks=time_lock)

    # Test no perms
    with boa.reverts("no perms"):
        undy_hq.confirmHqConfigChange(dept_reg_id, sender=bob)

    # Confirm config change
    assert undy_hq.confirmHqConfigChange(dept_reg_id, sender=governance.address)

    # Verify confirmed event
    confirmed_log = filter_logs(undy_hq, "HqConfigChangeConfirmed")[0]
    assert confirmed_log.regId == dept_reg_id
    assert confirmed_log.description == "Undy Minter"
    assert confirmed_log.canMintUndy
    assert not confirmed_log.canSetTokenBlacklist
    assert confirmed_log.initiatedBlock == pending.initiatedBlock
    assert confirmed_log.confirmBlock == pending.confirmBlock

    # Verify config is set
    config = undy_hq.hqConfig(dept_reg_id)
    assert config.canMintUndy
    assert not config.canSetTokenBlacklist

    # Verify pending is cleared
    assert not undy_hq.hasPendingHqConfigChange(dept_reg_id)


def test_hq_config_change_validation(
    undy_hq,
    mock_dept_can_mint_undy,
    mock_dept_cannot_mint_undy,
    governance,
):
    time_lock = undy_hq.registryChangeTimeLock()

    # Add departments
    undy_hq.startAddNewAddressToRegistry(mock_dept_can_mint_undy, "Undy Minter", sender=governance.address)
    boa.env.time_travel(blocks=time_lock)
    can_mint_reg_id = undy_hq.confirmNewAddressToRegistry(mock_dept_can_mint_undy, sender=governance.address)

    undy_hq.startAddNewAddressToRegistry(mock_dept_cannot_mint_undy, "No Mint Dept", sender=governance.address)
    boa.env.time_travel(blocks=time_lock)
    cannot_mint_reg_id = undy_hq.confirmNewAddressToRegistry(mock_dept_cannot_mint_undy, sender=governance.address)

    # Test invalid reg ID
    with boa.reverts("invalid hq config"):
        undy_hq.initiateHqConfigChange(0, True, False, sender=governance.address)
    with boa.reverts("invalid hq config"):
        undy_hq.initiateHqConfigChange(999, True, False, sender=governance.address)

    # Test token reg ID cannot mint
    with boa.reverts("invalid hq config"):
        undy_hq.initiateHqConfigChange(1, True, False, sender=governance.address)  # undy token

    # Test department must support minting if trying to enable minting
    with boa.reverts("invalid hq config"):
        undy_hq.initiateHqConfigChange(cannot_mint_reg_id, True, False, sender=governance.address)  # can't mint undy

    # Valid config changes should work
    undy_hq.initiateHqConfigChange(can_mint_reg_id, True, False, sender=governance.address)
    undy_hq.initiateHqConfigChange(cannot_mint_reg_id, False, True, sender=governance.address)  # can set blacklist but not mint


def test_hq_config_change_cancel(
    undy_hq,
    mock_dept_can_mint_undy,
    governance,
    bob,
):
    time_lock = undy_hq.registryChangeTimeLock()

    # Add department that can mint
    undy_hq.startAddNewAddressToRegistry(mock_dept_can_mint_undy, "Undy Minter", sender=governance.address)
    boa.env.time_travel(blocks=time_lock)
    dept_reg_id = undy_hq.confirmNewAddressToRegistry(mock_dept_can_mint_undy, sender=governance.address)

    # Start config change
    undy_hq.initiateHqConfigChange(dept_reg_id, True, False, sender=governance.address)

    # Test no perms
    with boa.reverts("no perms"):
        undy_hq.cancelHqConfigChange(dept_reg_id, sender=bob)

    # Test no pending
    with boa.reverts("no pending change"):
        undy_hq.cancelHqConfigChange(999, sender=governance.address)

    # Cancel config change
    assert undy_hq.cancelHqConfigChange(dept_reg_id, sender=governance.address)

    # Verify cancel event
    cancel_log = filter_logs(undy_hq, "HqConfigChangeCancelled")[0]
    assert cancel_log.regId == dept_reg_id
    assert cancel_log.description == "Undy Minter"
    assert cancel_log.canMintUndy
    assert not cancel_log.canSetTokenBlacklist
    assert cancel_log.initiatedBlock == boa.env.evm.patch.block_number
    assert cancel_log.confirmBlock == boa.env.evm.patch.block_number + time_lock

    # Verify pending is cleared
    assert not undy_hq.hasPendingHqConfigChange(dept_reg_id)


def test_hq_config_change_invalid_after_time_lock(
    undy_hq,
    mock_dept_can_mint_undy,
    mock_dept_cannot_mint_undy,
    governance,
):
    time_lock = undy_hq.registryChangeTimeLock()

    # Add initial department that can mint undy
    undy_hq.startAddNewAddressToRegistry(mock_dept_can_mint_undy, "Undy Minter", sender=governance.address)
    boa.env.time_travel(blocks=time_lock)
    reg_id = undy_hq.confirmNewAddressToRegistry(mock_dept_can_mint_undy, sender=governance.address)

    # Start config change for undy minting
    undy_hq.initiateHqConfigChange(reg_id, True, False, sender=governance.address)

    # Update the address to one that can't mint undy
    undy_hq.startAddressUpdateToRegistry(reg_id, mock_dept_cannot_mint_undy, sender=governance.address)
    boa.env.time_travel(blocks=time_lock)
    assert undy_hq.confirmAddressUpdateToRegistry(reg_id, sender=governance.address)

    # Now try to confirm the config change - should fail as the address can no longer mint undy
    assert not undy_hq.confirmHqConfigChange(reg_id, sender=governance.address)
    assert not undy_hq.hasPendingHqConfigChange(reg_id)


def test_token_specific_restrictions(
    undy_hq,
    governance,
):
    # Test token getter
    assert undy_hq.undyToken() == undy_hq.getAddr(1)

    # Test that token ID cannot be configured for minting
    with boa.reverts("invalid hq config"):
        undy_hq.initiateHqConfigChange(1, True, False, sender=governance.address)  # undy token

    # Test that token ID cannot set its own blacklist
    with boa.reverts("invalid hq config"):
        undy_hq.initiateHqConfigChange(1, False, True, sender=governance.address)  # undy token


def test_minting_capability_validation(
    undy_hq,
    mock_dept_can_mint_undy,
    governance,
):
    time_lock = undy_hq.registryChangeTimeLock()

    # Add department that can mint undy
    undy_hq.startAddNewAddressToRegistry(mock_dept_can_mint_undy, "Undy Minter", sender=governance.address)
    boa.env.time_travel(blocks=time_lock)
    reg_id = undy_hq.confirmNewAddressToRegistry(mock_dept_can_mint_undy, sender=governance.address)

    # Test that both contract config and department capability are required
    assert not undy_hq.canMintUndy(mock_dept_can_mint_undy)  # No config yet
    undy_hq.initiateHqConfigChange(reg_id, True, False, sender=governance.address)
    boa.env.time_travel(blocks=time_lock)
    assert undy_hq.confirmHqConfigChange(reg_id, sender=governance.address)
    assert undy_hq.canMintUndy(mock_dept_can_mint_undy)  # Both config and capability

    # Test that zero address cannot mint
    assert not undy_hq.canMintUndy(ZERO_ADDRESS)

    # Test that disabled addresses cannot mint
    undy_hq.startAddressDisableInRegistry(reg_id, sender=governance.address)
    boa.env.time_travel(blocks=time_lock)
    assert undy_hq.confirmAddressDisableInRegistry(reg_id, sender=governance.address)
    assert not undy_hq.canMintUndy(mock_dept_can_mint_undy)


def test_fund_recovery(
    undy_hq,
    governance,
    bob,
    alpha_token,
    alpha_token_whale,
    bravo_token,
    charlie_token,
    bravo_token_whale,
    charlie_token_whale,
    sally,
):
    # Test no perms
    with boa.reverts("no perms"):
        undy_hq.recoverFunds(bob, alpha_token, sender=bob)

    # Test invalid recipient
    with boa.reverts("invalid recipient or asset"):
        undy_hq.recoverFunds(ZERO_ADDRESS, alpha_token, sender=governance.address)

    # Test invalid asset
    with boa.reverts("invalid recipient or asset"):
        undy_hq.recoverFunds(bob, ZERO_ADDRESS, sender=governance.address)

    # Test zero balance
    with boa.reverts("nothing to recover"):
        undy_hq.recoverFunds(bob, alpha_token, sender=governance.address)

    # Test successful recovery
    alpha_token.transfer(undy_hq, 1000, sender=alpha_token_whale)
    undy_hq.recoverFunds(bob, alpha_token, sender=governance.address)
    assert alpha_token.balanceOf(bob) == 1000

    # Test multiple asset recovery
    alpha_token.transfer(undy_hq, 2000, sender=alpha_token_whale)
    bravo_token.transfer(undy_hq, 2000, sender=bravo_token_whale)
    charlie_token.transfer(undy_hq, 2000, sender=charlie_token_whale)

    assets = [alpha_token, bravo_token, charlie_token]
    undy_hq.recoverFundsMany(sally, assets, sender=governance.address)
    assert alpha_token.balanceOf(sally) == 2000
    assert bravo_token.balanceOf(sally) == 2000
    assert charlie_token.balanceOf(sally) == 2000


def test_multiple_pending_configs(
    undy_hq,
    mock_dept_can_mint_undy,
    mock_dept_cannot_mint_undy,
    governance,
):
    time_lock = undy_hq.registryChangeTimeLock()

    # Add first department that can mint undy
    undy_hq.startAddNewAddressToRegistry(mock_dept_can_mint_undy, "Undy Minter", sender=governance.address)
    boa.env.time_travel(blocks=time_lock)
    reg_id_1 = undy_hq.confirmNewAddressToRegistry(mock_dept_can_mint_undy, sender=governance.address)

    # Add second department that cannot mint but can set blacklist
    undy_hq.startAddNewAddressToRegistry(mock_dept_cannot_mint_undy, "Blacklist Manager", sender=governance.address)
    boa.env.time_travel(blocks=time_lock)
    reg_id_2 = undy_hq.confirmNewAddressToRegistry(mock_dept_cannot_mint_undy, sender=governance.address)

    # Start multiple pending configs
    undy_hq.initiateHqConfigChange(reg_id_1, True, False, sender=governance.address)
    undy_hq.initiateHqConfigChange(reg_id_2, False, True, sender=governance.address)

    # Verify both are pending
    assert undy_hq.hasPendingHqConfigChange(reg_id_1)
    assert undy_hq.hasPendingHqConfigChange(reg_id_2)

    # Verify pending configs have correct values
    pending_1 = undy_hq.pendingHqConfig(reg_id_1)
    assert pending_1.newHqConfig.canMintUndy
    assert not pending_1.newHqConfig.canSetTokenBlacklist

    pending_2 = undy_hq.pendingHqConfig(reg_id_2)
    assert not pending_2.newHqConfig.canMintUndy
    assert pending_2.newHqConfig.canSetTokenBlacklist

    # Confirm both configs
    boa.env.time_travel(blocks=time_lock)
    assert undy_hq.confirmHqConfigChange(reg_id_1, sender=governance.address)
    assert undy_hq.confirmHqConfigChange(reg_id_2, sender=governance.address)

    # Verify final configs are set correctly
    config_1 = undy_hq.hqConfig(reg_id_1)
    assert config_1.canMintUndy
    assert not config_1.canSetTokenBlacklist

    config_2 = undy_hq.hqConfig(reg_id_2)
    assert not config_2.canMintUndy
    assert config_2.canSetTokenBlacklist


###########################
# Minting Circuit Breaker #
###########################


def test_mint_enabled_by_default(undy_hq):
    """Test that minting is enabled by default"""
    assert undy_hq.mintEnabled() == True


def test_disable_minting(undy_hq, governance):
    """Test that governance can disable minting"""
    # Disable minting
    undy_hq.setMintingEnabled(False, sender=governance.address)
    assert undy_hq.mintEnabled() == False


def test_enable_minting(undy_hq, governance):
    """Test that governance can re-enable minting"""
    # First disable
    undy_hq.setMintingEnabled(False, sender=governance.address)
    assert undy_hq.mintEnabled() == False
    
    # Then enable
    undy_hq.setMintingEnabled(True, sender=governance.address)
    assert undy_hq.mintEnabled() == True


def test_only_governance_can_toggle_minting(undy_hq, alice):
    """Test that only governance can enable/disable minting"""
    # Non-governance cannot disable
    with boa.reverts("no perms"):
        undy_hq.setMintingEnabled(False, sender=alice)
    
    # Non-governance cannot enable  
    with boa.reverts("no perms"):
        undy_hq.setMintingEnabled(True, sender=alice)


def test_cannot_set_same_state(undy_hq, governance):
    """Test that setting the same state fails"""
    # Minting is enabled by default, try to enable again
    with boa.reverts("already set"):
        undy_hq.setMintingEnabled(True, sender=governance.address)
    
    # Disable minting
    undy_hq.setMintingEnabled(False, sender=governance.address)
    
    # Try to disable again
    with boa.reverts("already set"):
        undy_hq.setMintingEnabled(False, sender=governance.address)


def test_mint_circuit_breaker_affects_undy_minting(undy_hq, mock_dept_can_mint_undy, governance):
    """Test that disabling minting prevents UNDY token minting"""
    time_lock = undy_hq.registryChangeTimeLock()

    # Add and configure department
    undy_hq.startAddNewAddressToRegistry(mock_dept_can_mint_undy, "Undy Minter", sender=governance.address)
    boa.env.time_travel(blocks=time_lock)
    reg_id = undy_hq.confirmNewAddressToRegistry(mock_dept_can_mint_undy, sender=governance.address)
    
    undy_hq.initiateHqConfigChange(reg_id, True, False, sender=governance.address)
    boa.env.time_travel(blocks=time_lock)
    undy_hq.confirmHqConfigChange(reg_id, sender=governance.address)
    
    # Department should be able to mint when enabled
    assert undy_hq.canMintUndy(mock_dept_can_mint_undy) == True
    
    # Disable minting
    undy_hq.setMintingEnabled(False, sender=governance.address)
    
    # Department should not be able to mint when disabled
    assert undy_hq.canMintUndy(mock_dept_can_mint_undy) == False
    
    # Re-enable minting
    undy_hq.setMintingEnabled(True, sender=governance.address)
    
    # Should be able to mint again
    assert undy_hq.canMintUndy(mock_dept_can_mint_undy) == True


def test_events_emitted_correctly(undy_hq, governance):
    """Test that events are emitted with correct data"""
    # Test disable event
    undy_hq.setMintingEnabled(False, sender=governance.address)
    events = filter_logs(undy_hq, "MintingEnabled")
    
    assert len(events) == 1
    assert events[0].isEnabled == False
    
    # Test enable event
    undy_hq.setMintingEnabled(True, sender=governance.address)
    events = filter_logs(undy_hq, "MintingEnabled")
    
    assert len(events) == 1
    assert events[0].isEnabled == True


def test_circuit_breaker_blocks_all_minters(undy_hq, mock_dept_can_mint_undy, governance):
    """Test that circuit breaker blocks all contracts from minting"""
    time_lock = undy_hq.registryChangeTimeLock()

    # Add and configure department
    undy_hq.startAddNewAddressToRegistry(mock_dept_can_mint_undy, "Undy Minter", sender=governance.address)
    boa.env.time_travel(blocks=time_lock)
    reg_id = undy_hq.confirmNewAddressToRegistry(mock_dept_can_mint_undy, sender=governance.address)
    
    undy_hq.initiateHqConfigChange(reg_id, True, False, sender=governance.address)
    boa.env.time_travel(blocks=time_lock)
    undy_hq.confirmHqConfigChange(reg_id, sender=governance.address)
    
    # All minters should be able to mint initially
    assert undy_hq.canMintUndy(mock_dept_can_mint_undy) == True
    
    # Disable minting
    undy_hq.setMintingEnabled(False, sender=governance.address)
    
    # No contract should be able to mint
    assert undy_hq.canMintUndy(mock_dept_can_mint_undy) == False
    
    # Even if a contract has permission in hqConfig, circuit breaker overrides
    assert undy_hq.canMintUndy(ZERO_ADDRESS) == False


def test_blacklist_permissions(undy_hq, mock_dept_cannot_mint_undy, governance):
    """Test that departments can be configured to set token blacklists"""
    time_lock = undy_hq.registryChangeTimeLock()

    # Add department
    undy_hq.startAddNewAddressToRegistry(mock_dept_cannot_mint_undy, "Blacklist Manager", sender=governance.address)
    boa.env.time_travel(blocks=time_lock)
    reg_id = undy_hq.confirmNewAddressToRegistry(mock_dept_cannot_mint_undy, sender=governance.address)

    # Initially cannot set blacklist
    assert not undy_hq.canSetTokenBlacklist(mock_dept_cannot_mint_undy)

    # Configure to allow blacklist setting
    undy_hq.initiateHqConfigChange(reg_id, False, True, sender=governance.address)
    boa.env.time_travel(blocks=time_lock)
    assert undy_hq.confirmHqConfigChange(reg_id, sender=governance.address)

    # Now can set blacklist
    assert undy_hq.canSetTokenBlacklist(mock_dept_cannot_mint_undy)
    
    # But still cannot mint
    assert not undy_hq.canMintUndy(mock_dept_cannot_mint_undy)



