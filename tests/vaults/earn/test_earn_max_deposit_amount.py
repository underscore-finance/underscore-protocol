import boa

from constants import EIGHTEEN_DECIMALS, MAX_UINT256


def test_max_deposit_amount_initialization(undy_usd_vault, vault_registry):
    assert vault_registry.maxDepositAmount(undy_usd_vault.address) == 0


def test_set_max_deposit_amount(undy_usd_vault, vault_registry, switchboard_alpha, mission_control):
    max_amount = 1_000_000 * EIGHTEEN_DECIMALS

    mission_control.setCanPerformSecurityAction(
        switchboard_alpha.address, True, sender=switchboard_alpha.address
    )

    vault_registry.setMaxDepositAmount(undy_usd_vault.address, max_amount, sender=switchboard_alpha.address)

    assert vault_registry.maxDepositAmount(undy_usd_vault.address) == max_amount


def test_set_max_deposit_amount_no_perms(undy_usd_vault, vault_registry, bob):
    max_amount = 1_000_000 * EIGHTEEN_DECIMALS

    with boa.reverts("no perms"):
        vault_registry.setMaxDepositAmount(undy_usd_vault.address, max_amount, sender=bob)


def test_max_deposit_with_limit(
    undy_usd_vault,
    vault_registry,
    yield_underlying_token,
    yield_underlying_token_whale,
    switchboard_alpha,
    mission_control,
    bob,
):
    mission_control.setCanPerformSecurityAction(
        switchboard_alpha.address, True, sender=switchboard_alpha.address
    )

    max_amount = 1_000_000 * EIGHTEEN_DECIMALS
    vault_registry.setMaxDepositAmount(undy_usd_vault.address, max_amount, sender=switchboard_alpha.address)

    assert undy_usd_vault.maxDeposit(bob) == max_amount

    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)
    deposit_amount = 500_000 * EIGHTEEN_DECIMALS
    undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)

    assert undy_usd_vault.maxDeposit(bob) == max_amount - deposit_amount


def test_max_deposit_zero_limit(undy_usd_vault, bob):
    assert undy_usd_vault.maxDeposit(bob) == MAX_UINT256


def test_max_deposit_deposits_disabled(
    undy_usd_vault,
    vault_registry,
    switchboard_alpha,
    mission_control,
    bob,
):
    mission_control.setCanPerformSecurityAction(
        switchboard_alpha.address, True, sender=switchboard_alpha.address
    )

    max_amount = 1_000_000 * EIGHTEEN_DECIMALS
    vault_registry.setMaxDepositAmount(undy_usd_vault.address, max_amount, sender=switchboard_alpha.address)

    vault_registry.setCanDeposit(undy_usd_vault.address, False, sender=switchboard_alpha.address)

    assert undy_usd_vault.maxDeposit(bob) == 0


def test_deposit_exceeds_max_deposit_amount(
    undy_usd_vault,
    vault_registry,
    yield_underlying_token,
    yield_underlying_token_whale,
    switchboard_alpha,
    mission_control,
    bob,
):
    mission_control.setCanPerformSecurityAction(
        switchboard_alpha.address, True, sender=switchboard_alpha.address
    )

    max_amount = 1_000_000 * EIGHTEEN_DECIMALS
    vault_registry.setMaxDepositAmount(undy_usd_vault.address, max_amount, sender=switchboard_alpha.address)

    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    with boa.reverts("exceeds max deposit"):
        undy_usd_vault.deposit(max_amount + 1, bob, sender=yield_underlying_token_whale)


def test_deposit_at_max_limit(
    undy_usd_vault,
    vault_registry,
    yield_underlying_token,
    yield_underlying_token_whale,
    switchboard_alpha,
    mission_control,
    bob,
):
    mission_control.setCanPerformSecurityAction(
        switchboard_alpha.address, True, sender=switchboard_alpha.address
    )

    max_amount = 1_000_000 * EIGHTEEN_DECIMALS
    vault_registry.setMaxDepositAmount(undy_usd_vault.address, max_amount, sender=switchboard_alpha.address)

    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    undy_usd_vault.deposit(max_amount, bob, sender=yield_underlying_token_whale)

    assert undy_usd_vault.totalAssets() == max_amount
    assert undy_usd_vault.maxDeposit(bob) == 0


def test_max_mint_with_limit(
    undy_usd_vault,
    vault_registry,
    yield_underlying_token,
    yield_underlying_token_whale,
    switchboard_alpha,
    mission_control,
    bob,
):
    mission_control.setCanPerformSecurityAction(
        switchboard_alpha.address, True, sender=switchboard_alpha.address
    )

    max_amount = 1_000_000 * EIGHTEEN_DECIMALS
    vault_registry.setMaxDepositAmount(undy_usd_vault.address, max_amount, sender=switchboard_alpha.address)

    max_shares = undy_usd_vault.maxMint(bob)
    assert max_shares == max_amount

    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)
    deposit_amount = 500_000 * EIGHTEEN_DECIMALS
    undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)

    remaining_amount = max_amount - deposit_amount
    expected_shares = undy_usd_vault.convertToShares(remaining_amount)
    assert undy_usd_vault.maxMint(bob) == expected_shares


def test_max_mint_zero_limit(undy_usd_vault, bob):
    assert undy_usd_vault.maxMint(bob) == MAX_UINT256


def test_mint_respects_max_deposit_amount(
    undy_usd_vault,
    vault_registry,
    yield_underlying_token,
    yield_underlying_token_whale,
    switchboard_alpha,
    mission_control,
    bob,
):
    mission_control.setCanPerformSecurityAction(
        switchboard_alpha.address, True, sender=switchboard_alpha.address
    )

    max_amount = 1_000_000 * EIGHTEEN_DECIMALS
    vault_registry.setMaxDepositAmount(undy_usd_vault.address, max_amount, sender=switchboard_alpha.address)

    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    shares_over_limit = undy_usd_vault.convertToShares(max_amount + EIGHTEEN_DECIMALS)

    with boa.reverts("exceeds max deposit"):
        undy_usd_vault.mint(shares_over_limit, bob, sender=yield_underlying_token_whale)


def test_max_deposit_actually_works(
    undy_usd_vault,
    vault_registry,
    yield_underlying_token,
    yield_underlying_token_whale,
    switchboard_alpha,
    mission_control,
    bob,
):
    mission_control.setCanPerformSecurityAction(
        switchboard_alpha.address, True, sender=switchboard_alpha.address
    )

    max_amount = 1_000_000 * EIGHTEEN_DECIMALS
    vault_registry.setMaxDepositAmount(undy_usd_vault.address, max_amount, sender=switchboard_alpha.address)

    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    max_deposit = undy_usd_vault.maxDeposit(bob)
    assert max_deposit == max_amount

    shares = undy_usd_vault.deposit(max_deposit, bob, sender=yield_underlying_token_whale)
    assert shares > 0
    assert undy_usd_vault.totalAssets() == max_amount


def test_max_mint_actually_works(
    undy_usd_vault,
    vault_registry,
    yield_underlying_token,
    yield_underlying_token_whale,
    switchboard_alpha,
    mission_control,
    bob,
):
    mission_control.setCanPerformSecurityAction(
        switchboard_alpha.address, True, sender=switchboard_alpha.address
    )

    max_amount = 1_000_000 * EIGHTEEN_DECIMALS
    vault_registry.setMaxDepositAmount(undy_usd_vault.address, max_amount, sender=switchboard_alpha.address)

    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    max_shares = undy_usd_vault.maxMint(bob)
    assert max_shares > 0

    assets_used = undy_usd_vault.mint(max_shares, bob, sender=yield_underlying_token_whale)
    assert assets_used > 0
    assert undy_usd_vault.totalAssets() <= max_amount


def test_max_mint_with_existing_deposits(
    undy_usd_vault,
    vault_registry,
    yield_underlying_token,
    yield_underlying_token_whale,
    switchboard_alpha,
    mission_control,
    bob,
    alice,
):
    mission_control.setCanPerformSecurityAction(
        switchboard_alpha.address, True, sender=switchboard_alpha.address
    )

    max_amount = 1_000_000 * EIGHTEEN_DECIMALS
    vault_registry.setMaxDepositAmount(undy_usd_vault.address, max_amount, sender=switchboard_alpha.address)

    yield_underlying_token.approve(undy_usd_vault, MAX_UINT256, sender=yield_underlying_token_whale)

    initial_deposit = 300_000 * EIGHTEEN_DECIMALS
    undy_usd_vault.deposit(initial_deposit, alice, sender=yield_underlying_token_whale)

    max_shares = undy_usd_vault.maxMint(bob)
    assert max_shares > 0

    assets_used = undy_usd_vault.mint(max_shares, bob, sender=yield_underlying_token_whale)
    assert assets_used > 0
    assert undy_usd_vault.totalAssets() <= max_amount
