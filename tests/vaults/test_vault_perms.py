import pytest
import boa
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS


# Test setApprovedVaultToken functionality

def test_set_approved_vault_token_by_switchboard(undy_usd_vault, vault_registry, switchboard_alpha, mock_yield_lego, lego_book):
    """Test that switchboard can approve/disapprove vault tokens"""


    # Create a new mock vault token that's not pre-approved
    new_vault_token = boa.load("contracts/mock/MockErc4626Vault.vy", boa.load("contracts/mock/MockErc20.vy", boa.env.generate_address(), "Test", "TST", 18, 1_000_000))

    # Initially not approved
    assert not vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, new_vault_token.address)

    # Approve the vault token
    vault_registry.setApprovedVaultToken(undy_usd_vault.address, new_vault_token.address, True, sender=switchboard_alpha.address)
    assert vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, new_vault_token.address)

    # Disapprove the vault token
    vault_registry.setApprovedVaultToken(undy_usd_vault.address, new_vault_token.address, False, sender=switchboard_alpha.address)
    assert not vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, new_vault_token.address)


def test_set_approved_vault_token_non_switchboard_fails(undy_usd_vault, vault_registry, bob, starter_agent):
    """Test that non-switchboard addresses cannot approve vault tokens"""

    new_vault_token = boa.load("contracts/mock/MockErc4626Vault.vy", boa.load("contracts/mock/MockErc20.vy", boa.env.generate_address(), "Test", "TST", 18, 1_000_000))

    # Bob (non-switchboard) cannot approve
    with boa.reverts("no perms"):
        vault_registry.setApprovedVaultToken(undy_usd_vault.address, new_vault_token.address, True, sender=bob)

    # Even starter_agent (manager) cannot approve vault tokens
    with boa.reverts("no perms"):
        vault_registry.setApprovedVaultToken(undy_usd_vault.address, new_vault_token.address, True, sender=starter_agent.address)


def test_set_approved_vault_token_invalid_address(undy_usd_vault, vault_registry, switchboard_alpha):
    """Test that empty address cannot be approved as vault token"""

    with boa.reverts("invalid vault token"):
        vault_registry.setApprovedVaultToken(undy_usd_vault.address, ZERO_ADDRESS, True, sender=switchboard_alpha.address)


def test_set_approved_vault_token_no_change(undy_usd_vault, vault_registry, switchboard_alpha, yield_vault_token):
    """Test that setting the same approval state reverts"""

    # yield_vault_token is already approved in fixture
    assert vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, yield_vault_token.address)

    # Try to approve again (no change)
    with boa.reverts("nothing to change"):
        vault_registry.setApprovedVaultToken(undy_usd_vault.address, yield_vault_token.address, True, sender=switchboard_alpha.address)


# Test setApprovedYieldLego functionality

def test_set_approved_yield_lego_by_switchboard(undy_usd_vault, vault_registry, switchboard_alpha):
    """Test that switchboard can approve/disapprove yield legos"""

    # Lego ID 2 should not be approved initially
    assert not vault_registry.isApprovedYieldLegoByAddr(undy_usd_vault.address, 2)

    # Approve lego ID 2
    vault_registry.setApprovedYieldLego(undy_usd_vault.address, 2, True, sender=switchboard_alpha.address)
    assert vault_registry.isApprovedYieldLegoByAddr(undy_usd_vault.address, 2)

    # Disapprove lego ID 2
    vault_registry.setApprovedYieldLego(undy_usd_vault.address, 2, False, sender=switchboard_alpha.address)
    assert not vault_registry.isApprovedYieldLegoByAddr(undy_usd_vault.address, 2)


def test_set_approved_yield_lego_non_switchboard_fails(undy_usd_vault, vault_registry, bob, starter_agent):
    """Test that non-switchboard addresses cannot approve yield legos"""

    # Bob cannot approve
    with boa.reverts("no perms"):
        vault_registry.setApprovedYieldLego(undy_usd_vault.address, 2, True, sender=bob)

    # Even starter_agent (manager) cannot approve
    with boa.reverts("no perms"):
        vault_registry.setApprovedYieldLego(undy_usd_vault.address, 2, True, sender=starter_agent.address)


def test_set_approved_yield_lego_invalid_id(undy_usd_vault, vault_registry, switchboard_alpha):
    """Test that lego ID 0 cannot be approved"""

    with boa.reverts("invalid lego id"):
        vault_registry.setApprovedYieldLego(undy_usd_vault.address, 0, True, sender=switchboard_alpha.address)


def test_set_approved_yield_lego_no_change(undy_usd_vault, vault_registry, switchboard_alpha):
    """Test that setting the same approval state reverts"""

    # Lego ID 1 is already approved in fixture
    assert vault_registry.isApprovedYieldLegoByAddr(undy_usd_vault.address, 1)

    # Try to approve again (no change)
    with boa.reverts("nothing to change"):
        vault_registry.setApprovedYieldLego(undy_usd_vault.address, 1, True, sender=switchboard_alpha.address)


# Test deposit restrictions with unapproved tokens/legos

def test_deposit_with_unapproved_vault_token_fails(undy_usd_vault, vault_registry, starter_agent, yield_underlying_token, yield_underlying_token_whale, switchboard_alpha):
    """Test that deposits fail when vault token is not approved"""

    # Create a new unapproved vault token
    new_vault_token = boa.load("contracts/mock/MockErc4626Vault.vy", yield_underlying_token)

    # Transfer underlying tokens to vault
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)

    # Deposit should fail with unapproved vault token
    with boa.reverts("lego or vault token not approved"):
        undy_usd_vault.depositForYield(
            1,  # Lego ID 1 is approved
            yield_underlying_token.address,
            new_vault_token.address,
            deposit_amount,
            sender=starter_agent.address
        )

    # Now approve the vault token
    vault_registry.setApprovedVaultToken(undy_usd_vault.address, new_vault_token.address, True, sender=switchboard_alpha.address)

    # Deposit should succeed
    asset_deposited, vault_token, vault_tokens_received, usd_value = undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        new_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    assert asset_deposited == deposit_amount
    assert vault_token == new_vault_token.address
    assert vault_tokens_received > 0


def test_deposit_with_unapproved_lego_fails(undy_usd_vault, vault_registry, starter_agent, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, switchboard_alpha, lego_book, undy_hq_deploy, governance):
    """Test that deposits fail when yield lego is not approved, then succeed when approved"""

    # Deploy another mock yield lego
    new_mock_yield_lego = boa.load("contracts/mock/MockYieldLego.vy", undy_hq_deploy)

    # Register it in the lego book
    assert lego_book.startAddNewAddressToRegistry(new_mock_yield_lego, "New Mock Yield Lego", sender=governance.address)
    boa.env.time_travel(blocks=lego_book.registryChangeTimeLock() + 1)
    new_lego_id = lego_book.confirmNewAddressToRegistry(new_mock_yield_lego, sender=governance.address)
    # Verify it was registered
    assert new_lego_id == lego_book.getRegId(new_mock_yield_lego)

    # Transfer underlying tokens to vault
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)

    # Deposit should fail with unapproved lego
    with boa.reverts("lego or vault token not approved"):
        undy_usd_vault.depositForYield(
            new_lego_id,  # Not approved yet
            yield_underlying_token.address,
            yield_vault_token.address,
            deposit_amount,
            sender=starter_agent.address
        )

    # Approve the new lego
    vault_registry.setApprovedYieldLego(undy_usd_vault.address, new_lego_id, True, sender=switchboard_alpha.address)

    # Now deposit should succeed
    asset_deposited, vault_token, vault_tokens_received, usd_value = undy_usd_vault.depositForYield(
        new_lego_id,  # Now approved
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    assert asset_deposited == deposit_amount
    assert vault_token == yield_vault_token.address
    assert vault_tokens_received > 0


def test_deposit_both_unapproved_fails(undy_usd_vault, vault_registry, starter_agent, yield_underlying_token, yield_underlying_token_whale, switchboard_alpha, lego_book, undy_hq_deploy, governance):
    """Test that deposits fail when both vault token AND lego are unapproved"""

    # Create unapproved vault token
    new_vault_token = boa.load("contracts/mock/MockErc4626Vault.vy", yield_underlying_token)

    # Deploy and register another mock yield lego
    another_mock_yield_lego = boa.load("contracts/mock/MockYieldLego.vy", undy_hq_deploy)
    assert lego_book.startAddNewAddressToRegistry(another_mock_yield_lego, "Another Mock Yield Lego", sender=governance.address)
    boa.env.time_travel(blocks=lego_book.registryChangeTimeLock() + 1)
    another_lego_id = lego_book.confirmNewAddressToRegistry(another_mock_yield_lego, sender=governance.address)

    # Transfer underlying tokens to vault
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)

    # Should fail on combined check (lego is registered but not approved)
    with boa.reverts("lego or vault token not approved"):
        undy_usd_vault.depositForYield(
            another_lego_id,  # Registered but not approved lego
            yield_underlying_token.address,
            new_vault_token.address,  # Unapproved vault token
            deposit_amount,
            sender=starter_agent.address
        )

    # Approve the lego only
    vault_registry.setApprovedYieldLego(undy_usd_vault.address, another_lego_id, True, sender=switchboard_alpha.address)

    # Should now fail on vault token check
    with boa.reverts("lego or vault token not approved"):
        undy_usd_vault.depositForYield(
            another_lego_id,  # Now approved lego
            yield_underlying_token.address,
            new_vault_token.address,  # Still unapproved vault token
            deposit_amount,
            sender=starter_agent.address
        )

    # Approve the vault token too
    vault_registry.setApprovedVaultToken(undy_usd_vault.address, new_vault_token.address, True, sender=switchboard_alpha.address)

    # Now it should succeed with both approved
    asset_deposited, vault_token, vault_tokens_received, usd_value = undy_usd_vault.depositForYield(
        another_lego_id,
        yield_underlying_token.address,
        new_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    assert asset_deposited == deposit_amount
    assert vault_tokens_received > 0


def test_withdrawals_work_regardless_of_approval(undy_usd_vault, vault_registry, starter_agent, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, switchboard_alpha):
    """Test that withdrawals still work even after vault token is disapproved"""

    # First deposit with approved token
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)

    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    vault_balance = yield_vault_token.balanceOf(undy_usd_vault.address)
    assert vault_balance > 0

    # Now disapprove the vault token
    vault_registry.setApprovedVaultToken(undy_usd_vault.address, yield_vault_token.address, False, sender=switchboard_alpha.address)
    assert not vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, yield_vault_token.address)

    # Withdrawals should still work (no approval check on withdrawals)
    vault_burned, underlying_asset, underlying_received, usd_value = undy_usd_vault.withdrawFromYield(
        1,
        yield_vault_token.address,
        vault_balance,
        sender=starter_agent.address
    )

    assert vault_burned == vault_balance
    assert underlying_asset == yield_underlying_token.address
    assert underlying_received > 0

    # Vault should have no more vault tokens
    assert yield_vault_token.balanceOf(undy_usd_vault.address) == 0




def test_approval_events(undy_usd_vault, vault_registry, switchboard_alpha):
    """Test that approval changes emit the correct events"""

    # Create new vault token
    new_vault_token = boa.load("contracts/mock/MockErc4626Vault.vy", boa.load("contracts/mock/MockErc20.vy", boa.env.generate_address(), "Test", "TST", 18, 1_000_000))

    # Test vault token approval event
    vault_registry.setApprovedVaultToken(undy_usd_vault.address, new_vault_token.address, True, sender=switchboard_alpha.address)

    # Check event was emitted on VaultRegistry
    events = vault_registry.get_logs()
    assert len(events) > 0

    # Find the ApprovedVaultTokenSet event
    vault_token_event = None
    for event in events:
        if hasattr(event, 'vaultToken'):
            vault_token_event = event
            break

    assert vault_token_event is not None
    assert vault_token_event.vaultAddr == undy_usd_vault.address
    assert vault_token_event.vaultToken == new_vault_token.address
    assert vault_token_event.isApproved == True

    # Test lego approval event
    vault_registry.setApprovedYieldLego(undy_usd_vault.address, 5, True, sender=switchboard_alpha.address)

    events = vault_registry.get_logs()

    # Find the ApprovedYieldLegoSet event
    lego_event = None
    for event in reversed(events):  # Check from the end
        if hasattr(event, 'legoId'):
            lego_event = event
            break

    assert lego_event is not None
    assert lego_event.vaultAddr == undy_usd_vault.address
    assert lego_event.legoId == 5
    assert lego_event.isApproved == True


def test_multiple_approved_vault_tokens(undy_usd_vault, vault_registry, starter_agent, yield_underlying_token, yield_underlying_token_whale, switchboard_alpha):
    """Test managing multiple approved vault tokens"""

    # Create multiple vault tokens
    vault_tokens = []
    for i in range(3):
        vt = boa.load("contracts/mock/MockErc4626Vault.vy", yield_underlying_token)
        vault_tokens.append(vt)
        # Approve each one
        vault_registry.setApprovedVaultToken(undy_usd_vault.address, vt.address, True, sender=switchboard_alpha.address)

    # All should be approved
    for vt in vault_tokens:
        assert vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, vt.address)

    # Should be able to deposit to any of them
    for i, vt in enumerate(vault_tokens):
        deposit_amount = 10 * EIGHTEEN_DECIMALS
        yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)

        asset_deposited, vault_token, vault_tokens_received, _ = undy_usd_vault.depositForYield(
            1,
            yield_underlying_token.address,
            vt.address,
            deposit_amount,
            sender=starter_agent.address
        )

        assert vault_token == vt.address
        assert vault_tokens_received > 0

    # Disapprove the middle one
    vault_registry.setApprovedVaultToken(undy_usd_vault.address, vault_tokens[1].address, False, sender=switchboard_alpha.address)

    # Can still deposit to first and third
    for vt in [vault_tokens[0], vault_tokens[2]]:
        deposit_amount = 5 * EIGHTEEN_DECIMALS
        yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)

        asset_deposited, vault_token, vault_tokens_received, _ = undy_usd_vault.depositForYield(
            1,
            yield_underlying_token.address,
            vt.address,
            deposit_amount,
            sender=starter_agent.address
        )
        assert vault_tokens_received > 0

    # Cannot deposit to the disapproved one
    deposit_amount = 5 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)

    with boa.reverts("lego or vault token not approved"):
        undy_usd_vault.depositForYield(
            1,
            yield_underlying_token.address,
            vault_tokens[1].address,
            deposit_amount,
            sender=starter_agent.address
        )


# Test Manager Registration and Removal

def test_add_manager_by_switchboard(undy_usd_vault, switchboard_alpha, alice):
    """Test that switchboard can add new managers"""

    # Initially alice is not a manager
    assert undy_usd_vault.indexOfManager(alice) == 0

    # Add alice as manager
    undy_usd_vault.addManager(alice, sender=switchboard_alpha.address)

    # Now alice should be a manager
    assert undy_usd_vault.indexOfManager(alice) != 0
    assert undy_usd_vault.managers(undy_usd_vault.indexOfManager(alice)) == alice


def test_add_manager_non_switchboard_fails(undy_usd_vault, bob, alice, starter_agent):
    """Test that non-switchboard addresses cannot add managers"""

    # Bob cannot add alice as manager
    with boa.reverts("no perms"):
        undy_usd_vault.addManager(alice, sender=bob)

    # Even existing managers cannot add other managers
    with boa.reverts("no perms"):
        undy_usd_vault.addManager(alice, sender=starter_agent.address)


def test_remove_manager_by_switchboard(undy_usd_vault, switchboard_alpha, alice):
    """Test that switchboard can remove managers"""

    # First add alice as manager
    undy_usd_vault.addManager(alice, sender=switchboard_alpha.address)
    assert undy_usd_vault.indexOfManager(alice) != 0

    # Remove alice as manager
    undy_usd_vault.removeManager(alice, sender=switchboard_alpha.address)

    # Alice should no longer be a manager
    assert undy_usd_vault.indexOfManager(alice) == 0


def test_remove_manager_non_switchboard_fails(undy_usd_vault, switchboard_alpha, bob, alice, starter_agent):
    """Test that non-switchboard addresses cannot remove managers"""

    # Add alice as manager first
    undy_usd_vault.addManager(alice, sender=switchboard_alpha.address)

    # Bob cannot remove alice
    with boa.reverts("no perms"):
        undy_usd_vault.removeManager(alice, sender=bob)

    # Even managers cannot remove other managers
    with boa.reverts("no perms"):
        undy_usd_vault.removeManager(alice, sender=starter_agent.address)


def test_cannot_remove_last_manager(undy_usd_vault, switchboard_alpha, alice, bob):
    """Test that the system maintains a minimum number of managers"""

    # First, ensure we have multiple managers - add alice and bob as managers
    undy_usd_vault.addManager(alice, sender=switchboard_alpha.address)
    undy_usd_vault.addManager(bob, sender=switchboard_alpha.address)

    # Get the current count (should be at least 3 now)
    initial_count = undy_usd_vault.numManagers()
    assert initial_count >= 3

    # Remove managers until we can't remove more
    # Based on the contract, it seems to maintain at least 1 manager
    # Let's remove alice first
    undy_usd_vault.removeManager(alice, sender=switchboard_alpha.address)
    count_after_alice = undy_usd_vault.numManagers()
    assert count_after_alice == initial_count - 1

    # Remove bob
    undy_usd_vault.removeManager(bob, sender=switchboard_alpha.address)
    count_after_bob = undy_usd_vault.numManagers()

    # The contract appears to maintain a minimum, let's find what it is
    # Try to remove all remaining managers one by one
    min_managers = count_after_bob
    for i in range(1, count_after_bob + 1):
        manager = undy_usd_vault.managers(i)
        prev_count = undy_usd_vault.numManagers()
        undy_usd_vault.removeManager(manager, sender=switchboard_alpha.address)
        new_count = undy_usd_vault.numManagers()

        # If count didn't change, we've hit the minimum
        if new_count == prev_count:
            min_managers = new_count
            break

    # Verify we can't go below the minimum
    assert undy_usd_vault.numManagers() >= 1
    # The contract maintains at least 1 manager
    assert min_managers >= 1


def test_add_duplicate_manager_ignored(undy_usd_vault, switchboard_alpha, alice):
    """Test that adding a duplicate manager is silently ignored"""

    # Add alice as manager
    undy_usd_vault.addManager(alice, sender=switchboard_alpha.address)
    initial_index = undy_usd_vault.indexOfManager(alice)
    initial_count = undy_usd_vault.numManagers()

    # Try to add alice again - should be ignored
    undy_usd_vault.addManager(alice, sender=switchboard_alpha.address)

    # Manager count and index should remain the same
    assert undy_usd_vault.numManagers() == initial_count
    assert undy_usd_vault.indexOfManager(alice) == initial_index


def test_remove_non_existent_manager_ignored(undy_usd_vault, switchboard_alpha, alice):
    """Test that removing a non-existent manager is silently ignored"""

    # alice is not a manager
    assert undy_usd_vault.indexOfManager(alice) == 0
    initial_count = undy_usd_vault.numManagers()

    # Try to remove alice - should be ignored
    undy_usd_vault.removeManager(alice, sender=switchboard_alpha.address)

    # Manager count should remain the same
    assert undy_usd_vault.numManagers() == initial_count


def test_multiple_managers_can_perform_actions(undy_usd_vault, switchboard_alpha, alice, bob, charlie, yield_underlying_token, yield_underlying_token_whale, yield_vault_token):
    """Test that multiple managers can all perform vault actions"""

    # Get initial manager count
    initial_count = undy_usd_vault.numManagers()

    # Add alice, bob, and charlie as managers
    undy_usd_vault.addManager(alice, sender=switchboard_alpha.address)
    undy_usd_vault.addManager(bob, sender=switchboard_alpha.address)
    undy_usd_vault.addManager(charlie, sender=switchboard_alpha.address)

    # Should have increased by 3
    assert undy_usd_vault.numManagers() == initial_count + 3

    # Transfer underlying tokens to vault
    deposit_amount = 10 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount * 3, sender=yield_underlying_token_whale)

    # Each new manager should be able to deposit
    for manager in [alice, bob, charlie]:
        asset_deposited, vault_token, vault_tokens_received, _ = undy_usd_vault.depositForYield(
            1,
            yield_underlying_token.address,
            yield_vault_token.address,
            deposit_amount,
            sender=manager
        )
        assert vault_tokens_received > 0


def test_manager_removal_updates_array_correctly(undy_usd_vault, switchboard_alpha, alice, bob, charlie):
    """Test that removing a manager from the middle updates the array correctly"""

    # Get initial count
    initial_count = undy_usd_vault.numManagers()

    # Add alice, bob, and charlie as managers
    undy_usd_vault.addManager(alice, sender=switchboard_alpha.address)
    undy_usd_vault.addManager(bob, sender=switchboard_alpha.address)
    undy_usd_vault.addManager(charlie, sender=switchboard_alpha.address)

    # Record indices
    alice_index = undy_usd_vault.indexOfManager(alice)
    bob_index = undy_usd_vault.indexOfManager(bob)
    charlie_index = undy_usd_vault.indexOfManager(charlie)

    # Remove bob (middle manager)
    undy_usd_vault.removeManager(bob, sender=switchboard_alpha.address)

    # Bob should have index 0 (not a manager)
    assert undy_usd_vault.indexOfManager(bob) == 0

    # Manager count should be reduced by 1
    assert undy_usd_vault.numManagers() == initial_count + 2

    # Charlie should have been moved to bob's position if bob wasn't last
    if bob_index < charlie_index:
        assert undy_usd_vault.indexOfManager(charlie) == bob_index
        assert undy_usd_vault.managers(bob_index) == charlie

    # Alice's index should be unchanged if she was before bob
    if alice_index < bob_index:
        assert undy_usd_vault.indexOfManager(alice) == alice_index


def test_non_manager_cannot_deposit(undy_usd_vault, alice, yield_underlying_token, yield_underlying_token_whale, yield_vault_token):
    """Test that non-managers cannot perform deposit actions"""

    # alice is not a manager
    assert undy_usd_vault.indexOfManager(alice) == 0

    # Transfer underlying tokens to vault
    deposit_amount = 10 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)

    # alice should not be able to deposit
    with boa.reverts("not manager"):
        undy_usd_vault.depositForYield(
            1,
            yield_underlying_token.address,
            yield_vault_token.address,
            deposit_amount,
            sender=alice
        )


def test_non_manager_cannot_withdraw(undy_usd_vault, starter_agent, alice, yield_underlying_token, yield_underlying_token_whale, yield_vault_token):
    """Test that non-managers cannot perform withdraw actions"""

    # First have a manager deposit
    deposit_amount = 10 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)

    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    vault_balance = yield_vault_token.balanceOf(undy_usd_vault.address)

    # alice is not a manager and should not be able to withdraw
    with boa.reverts("not manager"):
        undy_usd_vault.withdrawFromYield(
            1,
            yield_vault_token.address,
            vault_balance,
            sender=alice
        )




def test_removed_manager_loses_permissions(undy_usd_vault, switchboard_alpha, alice, yield_underlying_token, yield_underlying_token_whale, yield_vault_token):
    """Test that removed managers immediately lose their permissions"""

    # Add alice as manager
    undy_usd_vault.addManager(alice, sender=switchboard_alpha.address)

    # Alice can deposit as a manager
    deposit_amount = 10 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)

    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=alice
    )

    # Remove alice as manager
    undy_usd_vault.removeManager(alice, sender=switchboard_alpha.address)

    # Alice should immediately lose permissions
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)

    with boa.reverts("not manager"):
        undy_usd_vault.depositForYield(
            1,
            yield_underlying_token.address,
            yield_vault_token.address,
            deposit_amount,
            sender=alice
        )


def test_manager_array_indexing_consistency(undy_usd_vault, switchboard_alpha, alice, bob, charlie, sally):
    """Test that manager array and indexing remain consistent through add/remove operations"""

    # Get initial count
    initial_count = undy_usd_vault.numManagers()

    # Add multiple managers
    undy_usd_vault.addManager(alice, sender=switchboard_alpha.address)
    undy_usd_vault.addManager(bob, sender=switchboard_alpha.address)
    undy_usd_vault.addManager(charlie, sender=switchboard_alpha.address)
    undy_usd_vault.addManager(sally, sender=switchboard_alpha.address)

    assert undy_usd_vault.numManagers() == initial_count + 4

    # Verify each manager's index points to correct address
    for manager in [alice, bob, charlie, sally]:
        index = undy_usd_vault.indexOfManager(manager)
        assert index != 0
        assert undy_usd_vault.managers(index) == manager

    # Remove managers in various patterns and verify consistency
    undy_usd_vault.removeManager(bob, sender=switchboard_alpha.address)
    assert undy_usd_vault.numManagers() == initial_count + 3
    assert undy_usd_vault.indexOfManager(bob) == 0

    # Remaining managers should still be valid
    for manager in [alice, charlie, sally]:
        index = undy_usd_vault.indexOfManager(manager)
        assert index != 0
        assert undy_usd_vault.managers(index) == manager

    # Remove another and check again
    undy_usd_vault.removeManager(sally, sender=switchboard_alpha.address)
    assert undy_usd_vault.numManagers() == initial_count + 2

    for manager in [alice, charlie]:
        index = undy_usd_vault.indexOfManager(manager)
        assert index != 0
        assert undy_usd_vault.managers(index) == manager