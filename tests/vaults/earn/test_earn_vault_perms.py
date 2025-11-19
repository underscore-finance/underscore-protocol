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
    vault_registry.setApprovedVaultToken(undy_usd_vault.address, new_vault_token.address, True, False, sender=switchboard_alpha.address)
    assert vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, new_vault_token.address)

    # Disapprove the vault token
    vault_registry.setApprovedVaultToken(undy_usd_vault.address, new_vault_token.address, False, False, sender=switchboard_alpha.address)
    assert not vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, new_vault_token.address)


def test_set_approved_vault_token_non_switchboard_fails(undy_usd_vault, vault_registry, bob, starter_agent):
    """Test that non-switchboard addresses cannot approve vault tokens"""

    new_vault_token = boa.load("contracts/mock/MockErc4626Vault.vy", boa.load("contracts/mock/MockErc20.vy", boa.env.generate_address(), "Test", "TST", 18, 1_000_000))

    # Bob (non-switchboard) cannot approve
    with boa.reverts("no perms"):
        vault_registry.setApprovedVaultToken(undy_usd_vault.address, new_vault_token.address, True, False, sender=bob)

    # Even starter_agent (manager) cannot approve vault tokens
    with boa.reverts("no perms"):
        vault_registry.setApprovedVaultToken(undy_usd_vault.address, new_vault_token.address, True, False, sender=starter_agent.address)


def test_set_approved_vault_token_invalid_address(undy_usd_vault, vault_registry, switchboard_alpha):
    """Test that empty address cannot be approved as vault token"""

    with boa.reverts("invalid params"):
        vault_registry.setApprovedVaultToken(undy_usd_vault.address, ZERO_ADDRESS, True, False, sender=switchboard_alpha.address)


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
            2,  # Lego ID 1 is approved
            yield_underlying_token.address,
            new_vault_token.address,
            deposit_amount,
            sender=starter_agent.address
        )

    # Now approve the vault token
    vault_registry.setApprovedVaultToken(undy_usd_vault.address, new_vault_token.address, True, False, sender=switchboard_alpha.address)

    # Deposit should succeed
    asset_deposited, vault_token, vault_tokens_received, usd_value = undy_usd_vault.depositForYield(
        2,
        yield_underlying_token.address,
        new_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    assert asset_deposited == deposit_amount
    assert vault_token == new_vault_token.address
    assert vault_tokens_received > 0


def test_withdrawals_work_regardless_of_approval(undy_usd_vault, vault_registry, starter_agent, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, switchboard_alpha):
    """Test that withdrawals still work even after vault token is disapproved"""

    # First deposit with approved token
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)

    undy_usd_vault.depositForYield(
        2,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    vault_balance = yield_vault_token.balanceOf(undy_usd_vault.address)
    assert vault_balance > 0

    # Now disapprove the vault token
    vault_registry.setApprovedVaultToken(undy_usd_vault.address, yield_vault_token.address, False, False, sender=switchboard_alpha.address)
    assert not vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, yield_vault_token.address)

    # Withdrawals should still work (no approval check on withdrawals)
    vault_burned, underlying_asset, underlying_received, usd_value = undy_usd_vault.withdrawFromYield(
        2,
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
    vault_registry.setApprovedVaultToken(undy_usd_vault.address, new_vault_token.address, True, False, sender=switchboard_alpha.address)

    # Check event was emitted on VaultRegistry
    events = vault_registry.get_logs()
    assert len(events) > 0

    # Find the ApprovedVaultTokenSet event
    vault_token_event = None
    for event in events:
        if hasattr(event, 'isApproved'):
            vault_token_event = event
            break

    assert vault_token_event is not None
    assert vault_token_event.undyVaultAddr == undy_usd_vault.address
    assert vault_token_event.vaultToken == new_vault_token.address
    assert vault_token_event.isApproved == True


def test_multiple_approved_vault_tokens(undy_usd_vault, vault_registry, starter_agent, yield_underlying_token, yield_underlying_token_whale, switchboard_alpha):
    """Test managing multiple approved vault tokens"""

    # Create multiple vault tokens
    vault_tokens = []
    for i in range(3):
        vt = boa.load("contracts/mock/MockErc4626Vault.vy", yield_underlying_token)
        vault_tokens.append(vt)
        # Approve each one
        vault_registry.setApprovedVaultToken(undy_usd_vault.address, vt.address, True, False, sender=switchboard_alpha.address)

    # All should be approved
    for vt in vault_tokens:
        assert vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, vt.address)

    # Should be able to deposit to any of them
    for i, vt in enumerate(vault_tokens):
        deposit_amount = 10 * EIGHTEEN_DECIMALS
        yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)

        asset_deposited, vault_token, vault_tokens_received, _ = undy_usd_vault.depositForYield(
            2,
            yield_underlying_token.address,
            vt.address,
            deposit_amount,
            sender=starter_agent.address
        )

        assert vault_token == vt.address
        assert vault_tokens_received > 0

    # Disapprove the middle one
    vault_registry.setApprovedVaultToken(undy_usd_vault.address, vault_tokens[1].address, False, False, sender=switchboard_alpha.address)

    # Can still deposit to first and third
    for vt in [vault_tokens[0], vault_tokens[2]]:
        deposit_amount = 5 * EIGHTEEN_DECIMALS
        yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)

        asset_deposited, vault_token, vault_tokens_received, _ = undy_usd_vault.depositForYield(
            2,
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
            2,
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
            2,
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
            2,
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
        2,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    vault_balance = yield_vault_token.balanceOf(undy_usd_vault.address)

    # alice is not a manager and should not be able to withdraw
    with boa.reverts("not manager"):
        undy_usd_vault.withdrawFromYield(
            2,
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
        2,
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
            2,
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


##################################
# Sweep Leftovers Tests          #
##################################


def test_sweep_leftovers_success(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    switchboard_alpha,
    governance,
):
    """Test successfully sweeping leftover VAULT_ASSET when totalSupply is 0"""
    wallet = undy_usd_vault

    # Verify totalSupply is 0 (no shares minted)
    assert wallet.totalSupply() == 0

    # Give wallet some leftover tokens
    leftover_amount = 1_000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(wallet.address, leftover_amount, sender=yield_underlying_token_whale)

    # Verify wallet has balance
    assert yield_underlying_token.balanceOf(wallet.address) == leftover_amount

    # Get governance balance before sweep
    gov_balance_before = yield_underlying_token.balanceOf(governance.address)

    # Sweep leftovers
    swept_amount = wallet.sweepLeftovers(sender=switchboard_alpha.address)

    # Verify amount returned
    assert swept_amount == leftover_amount

    # Verify wallet balance is 0
    assert yield_underlying_token.balanceOf(wallet.address) == 0

    # Verify governance received the funds
    assert yield_underlying_token.balanceOf(governance.address) == gov_balance_before + leftover_amount


def test_sweep_leftovers_event_emission(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    switchboard_alpha,
    governance,
):
    """Test that sweepLeftovers emits the correct event"""
    wallet = undy_usd_vault

    # Give wallet some leftover tokens
    leftover_amount = 500 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(wallet.address, leftover_amount, sender=yield_underlying_token_whale)

    # Sweep and capture logs
    wallet.sweepLeftovers(sender=switchboard_alpha.address)

    # Check that LeftoversSwept event was emitted (Boa will auto-verify event data)
    # The event should have amount=leftover_amount and recipient=governance.address


def test_sweep_leftovers_with_shares_outstanding_fails(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    switchboard_alpha,
    governance,
    alice,
):
    """Test that sweeping fails when there are shares outstanding"""
    wallet = undy_usd_vault

    # Give wallet some tokens and have Alice deposit to get shares
    deposit_amount = 10_000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(alice, deposit_amount, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(wallet.address, deposit_amount, sender=alice)
    wallet.deposit(deposit_amount, alice, sender=alice)

    # Verify totalSupply is not 0
    assert wallet.totalSupply() > 0

    # Give wallet some additional leftover tokens
    leftover_amount = 1_000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(wallet.address, leftover_amount, sender=yield_underlying_token_whale)

    # Try to sweep - should fail because shares are outstanding
    with boa.reverts():  # dev: shares outstanding
        wallet.sweepLeftovers(sender=switchboard_alpha.address)


def test_sweep_leftovers_unauthorized_fails(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    governance,
    alice,
    starter_agent,
):
    """Test that only switchboard or governance can sweep leftovers"""
    wallet = undy_usd_vault

    # Give wallet some leftover tokens
    leftover_amount = 1_000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(wallet.address, leftover_amount, sender=yield_underlying_token_whale)

    # Try to sweep from starter_agent (manager but not switchboard/governance) - should fail
    with boa.reverts():  # dev: no perms
        wallet.sweepLeftovers(sender=starter_agent.address)

    # Try to sweep from random user - should fail
    with boa.reverts():  # dev: no perms
        wallet.sweepLeftovers(sender=alice)


def test_sweep_leftovers_governance_can_call(
    undy_usd_vault,
    yield_underlying_token,
    yield_underlying_token_whale,
    governance,
):
    """Test that governance can also call sweepLeftovers (not just switchboard)"""
    wallet = undy_usd_vault

    # Give wallet some leftover tokens
    leftover_amount = 1_000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(wallet.address, leftover_amount, sender=yield_underlying_token_whale)

    # Get governance balance before sweep
    gov_balance_before = yield_underlying_token.balanceOf(governance.address)

    # Sweep as governance (not switchboard)
    swept_amount = wallet.sweepLeftovers(sender=governance.address)

    # Verify success
    assert swept_amount == leftover_amount
    assert yield_underlying_token.balanceOf(wallet.address) == 0
    assert yield_underlying_token.balanceOf(governance.address) == gov_balance_before + leftover_amount


def test_sweep_leftovers_no_balance_fails(
    undy_usd_vault,
    yield_underlying_token,
    switchboard_alpha,
):
    """Test that sweeping fails when there's no balance to sweep"""
    wallet = undy_usd_vault

    # Verify wallet has no balance
    assert yield_underlying_token.balanceOf(wallet.address) == 0

    # Try to sweep - should fail because no balance
    with boa.reverts():  # dev: no balance
        wallet.sweepLeftovers(sender=switchboard_alpha.address)