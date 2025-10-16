import pytest
import boa
from constants import EIGHTEEN_DECIMALS


def test_freeze_vault_prevents_deposit_for_yield(
    undy_usd_vault,
    vault_registry,
    starter_agent,
    switchboard_alpha,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
):
    """Test that freezing vault prevents manager from depositing for yield"""

    # Prepare funds
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)

    # Initial deposit works (not frozen)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Freeze the vault
    vault_registry.setVaultOpsFrozen(undy_usd_vault.address, True, sender=switchboard_alpha.address)
    assert vault_registry.isVaultOpsFrozen(undy_usd_vault.address) == True

    # Prepare more funds
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)

    # Now deposit should fail
    with boa.reverts("frozen vault"):
        undy_usd_vault.depositForYield(
            1,
            yield_underlying_token.address,
            yield_vault_token.address,
            deposit_amount,
            sender=starter_agent.address
        )


def test_freeze_vault_prevents_withdraw_from_yield(
    undy_usd_vault,
    vault_registry,
    starter_agent,
    switchboard_alpha,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
):
    """Test that freezing vault prevents manager from withdrawing from yield"""

    # Setup: deposit some funds first
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

    # Freeze the vault
    vault_registry.setVaultOpsFrozen(undy_usd_vault.address, True, sender=switchboard_alpha.address)

    # Withdrawal should fail
    with boa.reverts("frozen vault"):
        undy_usd_vault.withdrawFromYield(
            1,
            yield_vault_token.address,
            vault_balance,
            sender=starter_agent.address
        )




def test_freeze_vault_prevents_claim_rewards(
    undy_usd_vault,
    vault_registry,
    starter_agent,
    switchboard_alpha,
    yield_underlying_token,
):
    """Test that freezing vault prevents manager from claiming rewards"""

    # Freeze the vault
    vault_registry.setVaultOpsFrozen(undy_usd_vault.address, True, sender=switchboard_alpha.address)

    # Claim rewards should fail
    with boa.reverts("frozen vault"):
        undy_usd_vault.claimRewards(
            1,  # lego id
            yield_underlying_token.address,  # reward token
            sender=starter_agent.address
        )


def test_freeze_vault_allows_user_withdrawals(
    undy_usd_vault,
    vault_registry,
    starter_agent,
    switchboard_alpha,
    bob,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
):
    """Test that frozen vault still allows users to withdraw via ERC4626"""

    # Setup: user deposits and vault deposits for yield
    user_deposit = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)
    undy_usd_vault.deposit(user_deposit, bob, sender=bob)

    # Manager deposits some to yield
    manager_deposit = 500 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, manager_deposit, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        manager_deposit,
        sender=starter_agent.address
    )

    # Freeze the vault
    vault_registry.setVaultOpsFrozen(undy_usd_vault.address, True, sender=switchboard_alpha.address)

    # User should still be able to withdraw (ERC4626 withdraw)
    bob_shares = undy_usd_vault.balanceOf(bob)
    assert bob_shares > 0

    # Withdraw half
    withdraw_amount = user_deposit // 2
    initial_balance = yield_underlying_token.balanceOf(bob)

    shares_burned = undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)

    final_balance = yield_underlying_token.balanceOf(bob)
    assert final_balance > initial_balance
    assert shares_burned > 0


def test_freeze_vault_allows_user_deposits(
    undy_usd_vault,
    vault_registry,
    switchboard_alpha,
    bob,
    yield_underlying_token,
    yield_underlying_token_whale,
):
    """Test that frozen vault still allows users to deposit via ERC4626 (if canDeposit=true)"""

    # Freeze the vault
    vault_registry.setVaultOpsFrozen(undy_usd_vault.address, True, sender=switchboard_alpha.address)

    # User should still be able to deposit via ERC4626
    user_deposit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)

    initial_shares = undy_usd_vault.balanceOf(bob)
    shares = undy_usd_vault.deposit(user_deposit, bob, sender=bob)
    final_shares = undy_usd_vault.balanceOf(bob)

    assert shares > 0
    assert final_shares == initial_shares + shares


def test_unfreeze_restores_manager_operations(
    undy_usd_vault,
    vault_registry,
    starter_agent,
    switchboard_alpha,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
):
    """Test that unfreezing vault restores manager operations"""

    # Freeze the vault
    vault_registry.setVaultOpsFrozen(undy_usd_vault.address, True, sender=switchboard_alpha.address)
    assert vault_registry.isVaultOpsFrozen(undy_usd_vault.address) == True

    # Prepare funds
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)

    # Deposit should fail when frozen
    with boa.reverts("frozen vault"):
        undy_usd_vault.depositForYield(
            1,
            yield_underlying_token.address,
            yield_vault_token.address,
            deposit_amount,
            sender=starter_agent.address
        )

    # Unfreeze the vault
    vault_registry.setVaultOpsFrozen(undy_usd_vault.address, False, sender=switchboard_alpha.address)
    assert vault_registry.isVaultOpsFrozen(undy_usd_vault.address) == False

    # Now deposit should succeed
    asset_deposited, vault_token, vault_tokens_received, usd_value = undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    assert asset_deposited == deposit_amount
    assert vault_tokens_received > 0


def test_freeze_permissions(
    undy_usd_vault,
    vault_registry,
    switchboard_alpha,
    bob,
    starter_agent,
):
    """Test that only switchboard can freeze/unfreeze vault"""

    # Bob (non-switchboard) cannot freeze
    with boa.reverts("no perms"):
        vault_registry.setVaultOpsFrozen(undy_usd_vault.address, True, sender=bob)

    # Even managers cannot freeze
    with boa.reverts("no perms"):
        vault_registry.setVaultOpsFrozen(undy_usd_vault.address, True, sender=starter_agent.address)

    # Switchboard can freeze
    vault_registry.setVaultOpsFrozen(undy_usd_vault.address, True, sender=switchboard_alpha.address)
    assert vault_registry.isVaultOpsFrozen(undy_usd_vault.address) == True

    # Bob cannot unfreeze
    with boa.reverts("no perms"):
        vault_registry.setVaultOpsFrozen(undy_usd_vault.address, False, sender=bob)

    # Switchboard can unfreeze
    vault_registry.setVaultOpsFrozen(undy_usd_vault.address, False, sender=switchboard_alpha.address)
    assert vault_registry.isVaultOpsFrozen(undy_usd_vault.address) == False


def test_freeze_vault_redeem_triggers_redemption(
    undy_usd_vault,
    vault_registry,
    starter_agent,
    switchboard_alpha,
    bob,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
):
    """Test that frozen vault still allows redemption which triggers internal withdrawFromYield"""

    # Setup: user deposits and vault deposits for yield
    user_deposit = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)
    undy_usd_vault.deposit(user_deposit, bob, sender=bob)

    # Manager deposits ALL to yield (no idle balance)
    vault_balance = yield_underlying_token.balanceOf(undy_usd_vault.address)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        vault_balance,
        sender=starter_agent.address
    )

    # Verify no idle balance
    assert yield_underlying_token.balanceOf(undy_usd_vault.address) == 0

    # Freeze the vault
    vault_registry.setVaultOpsFrozen(undy_usd_vault.address, True, sender=switchboard_alpha.address)

    # User redeems all shares (should trigger internal redemption from yield)
    bob_shares = undy_usd_vault.balanceOf(bob)
    initial_balance = yield_underlying_token.balanceOf(bob)

    assets_received = undy_usd_vault.redeem(bob_shares, bob, bob, sender=bob)

    final_balance = yield_underlying_token.balanceOf(bob)
    assert assets_received > 0
    assert final_balance > initial_balance
    assert undy_usd_vault.balanceOf(bob) == 0
