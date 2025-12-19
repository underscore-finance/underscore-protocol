import pytest
import boa

from constants import ZERO_ADDRESS
from conf_utils import filter_logs
from config.BluePrint import PARAMS


def test_helpers_deploy(
    helpers_deploy,
    fork,
):
    """Test that Helpers registry deploys correctly."""
    assert helpers_deploy.getRegistryDescription() == "Helpers.vy"
    # Initial timelock is 0 before setup
    assert helpers_deploy.registryChangeTimeLock() == 0
    assert helpers_deploy.numAddrs() == 1

    assert helpers_deploy.minRegistryTimeLock() == PARAMS[fork]["UNDY_HQ_MIN_REG_TIMELOCK"]
    assert helpers_deploy.maxRegistryTimeLock() == PARAMS[fork]["UNDY_HQ_MAX_REG_TIMELOCK"]


def test_helpers_deploy_is_helpers_addr_zero(
    helpers_deploy,
    bob,
):
    """Test isHelpersAddr returns False for unregistered addresses."""
    assert not helpers_deploy.isHelpersAddr(bob)
    assert not helpers_deploy.isHelpersAddr(ZERO_ADDRESS)


def test_helpers_deploy_add_new_address_requires_governance(
    helpers_deploy,
    bob,
    mock_rando_contract,
):
    """Test that non-governance addresses cannot add new helpers."""
    with boa.reverts("no perms"):
        helpers_deploy.startAddNewAddressToRegistry(mock_rando_contract, "Test Helper", sender=bob)


def test_helpers_deploy_add_and_confirm_address(
    helpers_deploy,
    governance,
    mock_rando_contract,
):
    """Test basic workflow for adding a new helper address using helpers_deploy (no timelock yet)."""
    # Since timelock is 0 at deploy, we can confirm immediately
    assert helpers_deploy.registryChangeTimeLock() == 0

    # Start adding new address
    assert helpers_deploy.startAddNewAddressToRegistry(mock_rando_contract, "Test Helper", sender=governance.address)

    # Can confirm immediately since timelock is 0
    reg_id = helpers_deploy.confirmNewAddressToRegistry(mock_rando_contract, sender=governance.address)
    assert reg_id == 1

    # Verify registration
    assert helpers_deploy.isHelpersAddr(mock_rando_contract)
    assert helpers_deploy.getRegId(mock_rando_contract) == 1
    assert helpers_deploy.getAddr(1) == mock_rando_contract.address


def test_helpers_deploy_cancel_new_address(
    helpers_deploy,
    governance,
    mock_rando_contract,
):
    """Test canceling a pending new helper address."""
    # Start adding new address
    helpers_deploy.startAddNewAddressToRegistry(mock_rando_contract, "Cancel Test", sender=governance.address)

    # Cancel
    assert helpers_deploy.cancelNewAddressToRegistry(mock_rando_contract, sender=governance.address)

    # Verify pending state is cleared
    assert helpers_deploy.pendingNewAddr(mock_rando_contract).confirmBlock == 0

    # Address should not be registered
    assert not helpers_deploy.isHelpersAddr(mock_rando_contract)


def test_helpers_deploy_set_registry_timelock_after_setup(
    helpers_deploy,
    governance,
    fork,
):
    """Test setRegistryTimeLockAfterSetup function."""
    # Initial timelock is 0
    assert helpers_deploy.registryChangeTimeLock() == 0

    # Set timelock
    assert helpers_deploy.setRegistryTimeLockAfterSetup(sender=governance.address)

    # Timelock should now be set to minimum
    assert helpers_deploy.registryChangeTimeLock() == PARAMS[fork]["UNDY_HQ_MIN_REG_TIMELOCK"]

    # Cannot set again
    with boa.reverts("already set"):
        helpers_deploy.setRegistryTimeLockAfterSetup(sender=governance.address)


# Tests that require the full helpers fixture (with lego_tools and levg_vault_tools)
# These will skip on local fork due to DEX lego dependencies

@pytest.always
def test_helpers_registration_order(
    helpers,
    lego_tools,
    levg_vault_tools,
):
    """Test that LegoTools is registered first (regId=1), LevgVaultTools second (regId=2)."""
    # LegoTools should be regId=1
    assert helpers.getRegId(lego_tools) == 1
    assert helpers.getAddr(1) == lego_tools.address

    # LevgVaultTools should be regId=2
    assert helpers.getRegId(levg_vault_tools) == 2
    assert helpers.getAddr(2) == levg_vault_tools.address

    # Verify numAddrs (1 reserved + 2 registered = 3)
    assert helpers.numAddrs() == 3


def test_helpers_is_helpers_addr(
    helpers,
    lego_tools,
    levg_vault_tools,
    bob,
):
    """Test isHelpersAddr returns correct values."""
    # Registered addresses should return True
    assert helpers.isHelpersAddr(lego_tools)
    assert helpers.isHelpersAddr(levg_vault_tools)

    # Unregistered addresses should return False
    assert not helpers.isHelpersAddr(bob)
    assert not helpers.isHelpersAddr(ZERO_ADDRESS)


def test_helpers_registry_timelock_set(
    helpers,
    fork,
):
    """Test that setRegistryTimeLockAfterSetup was called successfully."""
    # After setup, timelock should be set to minimum
    assert helpers.registryChangeTimeLock() == PARAMS[fork]["UNDY_HQ_MIN_REG_TIMELOCK"]


def test_helpers_get_addr_info(
    helpers,
    lego_tools,
    levg_vault_tools,
):
    """Test getAddrInfo returns correct info for registered helpers."""
    # LegoTools info
    lego_tools_info = helpers.getAddrInfo(1)
    assert lego_tools_info.addr == lego_tools.address
    assert lego_tools_info.version == 1
    assert lego_tools_info.description == "LegoTools"

    # LevgVaultTools info
    levg_info = helpers.getAddrInfo(2)
    assert levg_info.addr == levg_vault_tools.address
    assert levg_info.version == 1
    assert levg_info.description == "LevgVaultTools"


def test_helpers_add_new_address_requires_governance(
    helpers,
    bob,
    mock_rando_contract,
):
    """Test that non-governance addresses cannot add new helpers."""
    with boa.reverts("no perms"):
        helpers.startAddNewAddressToRegistry(mock_rando_contract, "Test Helper", sender=bob)


def test_helpers_add_new_address_basic(
    helpers,
    governance,
    mock_rando_contract,
):
    """Test basic workflow for adding a new helper address."""
    time_lock = helpers.registryChangeTimeLock()

    # Start adding new address
    assert helpers.startAddNewAddressToRegistry(mock_rando_contract, "New Helper", sender=governance.address)

    # Verify pending state
    pending = helpers.pendingNewAddr(mock_rando_contract)
    assert pending.description == "New Helper"
    assert pending.confirmBlock == boa.env.evm.patch.block_number + time_lock

    # Cannot confirm before timelock
    with boa.reverts("time lock not reached"):
        helpers.confirmNewAddressToRegistry(mock_rando_contract, sender=governance.address)

    # Time travel past timelock
    boa.env.time_travel(blocks=time_lock)

    # Confirm new address
    reg_id = helpers.confirmNewAddressToRegistry(mock_rando_contract, sender=governance.address)
    assert reg_id == 3  # After LegoTools (1) and LevgVaultTools (2)

    # Verify registration
    assert helpers.isHelpersAddr(mock_rando_contract)
    assert helpers.getRegId(mock_rando_contract) == 3
    assert helpers.getAddr(3) == mock_rando_contract.address


def test_helpers_cancel_new_address(
    helpers,
    governance,
    mock_rando_contract,
):
    """Test canceling a pending new helper address."""
    # Start adding new address
    helpers.startAddNewAddressToRegistry(mock_rando_contract, "Cancel Test", sender=governance.address)

    # Cancel
    assert helpers.cancelNewAddressToRegistry(mock_rando_contract, sender=governance.address)

    # Verify pending state is cleared
    assert helpers.pendingNewAddr(mock_rando_contract).confirmBlock == 0

    # Address should not be registered
    assert not helpers.isHelpersAddr(mock_rando_contract)


def test_helpers_pause_blocks_operations(
    helpers,
    governance,
    mock_rando_contract,
    switchboard_alpha,
):
    """Test that pausing the department blocks registry operations."""
    # Pause the department
    helpers.pause(sender=switchboard_alpha.address)
    assert helpers.isPaused()

    # Registry operations should fail when paused
    with boa.reverts("no perms"):
        helpers.startAddNewAddressToRegistry(mock_rando_contract, "Paused Test", sender=governance.address)

    # Unpause
    helpers.unpause(sender=switchboard_alpha.address)
    assert not helpers.isPaused()

    # Should work again after unpause
    assert helpers.startAddNewAddressToRegistry(mock_rando_contract, "Unpaused Test", sender=governance.address)


def test_helpers_address_update_basic(
    helpers,
    governance,
    mock_rando_contract,
):
    """Test updating an existing helper address."""
    time_lock = helpers.registryChangeTimeLock()

    # First, add a new address
    helpers.startAddNewAddressToRegistry(mock_rando_contract, "Update Test", sender=governance.address)
    boa.env.time_travel(blocks=time_lock)
    reg_id = helpers.confirmNewAddressToRegistry(mock_rando_contract, sender=governance.address)

    # Deploy another contract to update to
    new_contract = boa.load("contracts/mock/MockRandoContract.vy")

    # Start update
    assert helpers.startAddressUpdateToRegistry(reg_id, new_contract, sender=governance.address)

    # Wait for timelock
    boa.env.time_travel(blocks=time_lock)

    # Confirm update
    assert helpers.confirmAddressUpdateToRegistry(reg_id, sender=governance.address)

    # Verify update
    assert helpers.getAddr(reg_id) == new_contract.address
    assert helpers.isHelpersAddr(new_contract)
    assert not helpers.isHelpersAddr(mock_rando_contract)


def test_helpers_address_disable_basic(
    helpers,
    governance,
    mock_rando_contract,
):
    """Test disabling an existing helper address."""
    time_lock = helpers.registryChangeTimeLock()

    # First, add a new address
    helpers.startAddNewAddressToRegistry(mock_rando_contract, "Disable Test", sender=governance.address)
    boa.env.time_travel(blocks=time_lock)
    reg_id = helpers.confirmNewAddressToRegistry(mock_rando_contract, sender=governance.address)

    # Verify it's registered
    assert helpers.isHelpersAddr(mock_rando_contract)

    # Start disable
    assert helpers.startAddressDisableInRegistry(reg_id, sender=governance.address)

    # Wait for timelock
    boa.env.time_travel(blocks=time_lock)

    # Confirm disable
    assert helpers.confirmAddressDisableInRegistry(reg_id, sender=governance.address)

    # Verify disabled
    assert not helpers.isHelpersAddr(mock_rando_contract)
    assert helpers.getAddr(reg_id) == ZERO_ADDRESS


def test_helpers_view_functions(
    helpers,
    lego_tools,
    levg_vault_tools,
):
    """Test various view functions."""
    # getNumAddrs (excludes reserved slot 0)
    assert helpers.getNumAddrs() == 2

    # getLastAddr
    assert helpers.getLastAddr() == levg_vault_tools.address

    # getLastRegId
    assert helpers.getLastRegId() == 2

    # getAddrDescription
    assert helpers.getAddrDescription(1) == "LegoTools"
    assert helpers.getAddrDescription(2) == "LevgVaultTools"

    # isValidRegId
    assert helpers.isValidRegId(1)
    assert helpers.isValidRegId(2)
    assert not helpers.isValidRegId(0)
    assert not helpers.isValidRegId(999)
