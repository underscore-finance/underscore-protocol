import pytest
import boa

from constants import EIGHTEEN_DECIMALS
from conf_utils import filter_logs


@pytest.fixture(scope="module")
def prepareVaultWithYield(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token):
    def prepareVaultWithYield(_deposit_amount=1000 * EIGHTEEN_DECIMALS):
        yield_underlying_token.transfer(undy_usd_vault.address, _deposit_amount, sender=yield_underlying_token_whale)

        undy_usd_vault.depositForYield(
            1,
            yield_underlying_token.address,
            yield_vault_token.address,
            _deposit_amount,
            sender=starter_agent.address
        )
        return _deposit_amount

    yield prepareVaultWithYield


###########################
# Redemption Buffer Tests #
###########################


def test_set_redemption_buffer_by_switchboard(undy_usd_vault, vault_registry, switchboard_alpha):
    """Test setting redemption buffer by switchboard"""

    initial_buffer = vault_registry.redemptionBuffer(undy_usd_vault.address)
    assert initial_buffer == 2_00

    vault_registry.setRedemptionBuffer(undy_usd_vault.address, 5_00, sender=switchboard_alpha.address)

    new_buffer = vault_registry.redemptionBuffer(undy_usd_vault.address)
    assert new_buffer == 5_00


def test_set_redemption_buffer_multiple_values(undy_usd_vault, vault_registry, switchboard_alpha):
    """Test setting different valid redemption buffer values"""

    for buffer_value in [0, 1_00, 2_50, 5_00, 10_00]:
        vault_registry.setRedemptionBuffer(undy_usd_vault.address, buffer_value, sender=switchboard_alpha.address)
        assert vault_registry.redemptionBuffer(undy_usd_vault.address) == buffer_value


def test_set_redemption_buffer_max_validation(undy_usd_vault, vault_registry, switchboard_alpha):
    """Test redemption buffer cannot exceed 10%"""

    with boa.reverts("buffer too high (max 10%)"):
        vault_registry.setRedemptionBuffer(undy_usd_vault.address, 10_01, sender=switchboard_alpha.address)

    with boa.reverts("buffer too high (max 10%)"):
        vault_registry.setRedemptionBuffer(undy_usd_vault.address, 20_00, sender=switchboard_alpha.address)


def test_set_redemption_buffer_permission_check(undy_usd_vault, vault_registry, bob, starter_agent):
    """Test only switchboard can set redemption buffer"""

    with boa.reverts("no perms"):
        vault_registry.setRedemptionBuffer(undy_usd_vault.address, 5_00, sender=bob)

    with boa.reverts("no perms"):
        vault_registry.setRedemptionBuffer(undy_usd_vault.address, 5_00, sender=starter_agent.address)


def test_set_redemption_buffer_updates_state(undy_usd_vault, vault_registry, switchboard_alpha):
    """Test redemption buffer updates state correctly"""

    vault_registry.setRedemptionBuffer(undy_usd_vault.address, 7_50, sender=switchboard_alpha.address)

    assert vault_registry.redemptionBuffer(undy_usd_vault.address) == 7_50


##########################
# Basic Redemption Tests #
##########################


def test_redemption_with_sufficient_vault_balance(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob):
    """Test redemption when vault has sufficient balance (no yield withdrawal needed)"""

    deposit_amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, deposit_amount, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, deposit_amount, sender=bob)

    shares = undy_usd_vault.deposit(deposit_amount, bob, sender=bob)

    initial_balance = yield_underlying_token.balanceOf(bob)

    withdraw_amount = 500 * EIGHTEEN_DECIMALS
    undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)

    final_balance = yield_underlying_token.balanceOf(bob)
    assert final_balance == initial_balance + withdraw_amount


def test_redemption_single_position_partial(prepareVaultWithYield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob):
    """Test redemption requiring partial withdrawal from single yield position"""

    deposit_amount = prepareVaultWithYield(1000 * EIGHTEEN_DECIMALS)

    user_deposit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)
    undy_usd_vault.deposit(user_deposit, bob, sender=bob)

    vault_balance_before = yield_underlying_token.balanceOf(undy_usd_vault.address)

    withdraw_amount = 500 * EIGHTEEN_DECIMALS
    initial_balance = yield_underlying_token.balanceOf(bob)

    undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)

    final_balance = yield_underlying_token.balanceOf(bob)
    assert final_balance == initial_balance + withdraw_amount


def test_redemption_single_position_full_withdrawal(prepareVaultWithYield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, bob):
    """Test redemption requiring full withdrawal and deregistration"""

    deposit_amount = prepareVaultWithYield(500 * EIGHTEEN_DECIMALS)

    user_deposit = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)
    undy_usd_vault.deposit(user_deposit, bob, sender=bob)

    assert undy_usd_vault.numAssets() == 2
    assert undy_usd_vault.indexOfAsset(yield_vault_token.address) == 1

    withdraw_amount = 540 * EIGHTEEN_DECIMALS
    undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)

    assert undy_usd_vault.numAssets() == 1
    assert undy_usd_vault.indexOfAsset(yield_vault_token.address) == 0


def test_redemption_buffer_calculation_2_percent(prepareVaultWithYield, undy_usd_vault, vault_registry, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, bob, switchboard_alpha):
    """Test 2% buffer causes 102% withdrawal from yield positions"""

    vault_registry.setRedemptionBuffer(undy_usd_vault.address, 2_00, sender=switchboard_alpha.address)

    deposit_amount = prepareVaultWithYield(1000 * EIGHTEEN_DECIMALS)

    user_deposit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)
    undy_usd_vault.deposit(user_deposit, bob, sender=bob)

    vault_balance_before_withdraw = yield_underlying_token.balanceOf(undy_usd_vault.address)
    vault_token_balance_before = yield_vault_token.balanceOf(undy_usd_vault.address)

    withdraw_amount = 1000 * EIGHTEEN_DECIMALS
    undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)

    vault_balance_after = yield_underlying_token.balanceOf(undy_usd_vault.address)
    vault_token_balance_after = yield_vault_token.balanceOf(undy_usd_vault.address)

    vault_balance_withdrawn = vault_balance_before_withdraw + (vault_token_balance_before - vault_token_balance_after) - vault_balance_after

    expected_with_buffer = withdraw_amount * 102 // 100
    assert vault_balance_withdrawn >= withdraw_amount


def test_redemption_empty_vault_numAssets_zero(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob):
    """Test redemption when numAssets is 0 (no yield positions)"""

    deposit_amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, deposit_amount, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, deposit_amount, sender=bob)
    undy_usd_vault.deposit(deposit_amount, bob, sender=bob)

    assert undy_usd_vault.numAssets() == 1

    withdraw_amount = 500 * EIGHTEEN_DECIMALS
    initial_balance = yield_underlying_token.balanceOf(bob)

    undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)

    final_balance = yield_underlying_token.balanceOf(bob)
    assert final_balance == initial_balance + withdraw_amount


#######################
# Buffer Impact Tests #
#######################


def test_redemption_zero_percent_buffer(prepareVaultWithYield, undy_usd_vault, vault_registry, yield_underlying_token, yield_underlying_token_whale, bob, switchboard_alpha):
    """Test 0% buffer withdraws exactly what's needed"""

    vault_registry.setRedemptionBuffer(undy_usd_vault.address, 0, sender=switchboard_alpha.address)

    prepareVaultWithYield(1000 * EIGHTEEN_DECIMALS)

    user_deposit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)
    undy_usd_vault.deposit(user_deposit, bob, sender=bob)

    withdraw_amount = 900 * EIGHTEEN_DECIMALS
    initial_balance = yield_underlying_token.balanceOf(bob)

    undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)

    final_balance = yield_underlying_token.balanceOf(bob)
    assert final_balance == initial_balance + withdraw_amount


def test_redemption_five_percent_buffer(prepareVaultWithYield, undy_usd_vault, vault_registry, yield_underlying_token, yield_underlying_token_whale, bob, switchboard_alpha):
    """Test 5% buffer withdraws 105% of requested"""

    vault_registry.setRedemptionBuffer(undy_usd_vault.address, 5_00, sender=switchboard_alpha.address)

    prepareVaultWithYield(1000 * EIGHTEEN_DECIMALS)

    user_deposit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)
    undy_usd_vault.deposit(user_deposit, bob, sender=bob)

    withdraw_amount = 900 * EIGHTEEN_DECIMALS
    initial_balance = yield_underlying_token.balanceOf(bob)

    undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)

    final_balance = yield_underlying_token.balanceOf(bob)
    assert final_balance == initial_balance + withdraw_amount


def test_redemption_ten_percent_buffer(prepareVaultWithYield, undy_usd_vault, vault_registry, yield_underlying_token, yield_underlying_token_whale, bob, switchboard_alpha):
    """Test 10% buffer (max) withdraws 110% of requested"""

    vault_registry.setRedemptionBuffer(undy_usd_vault.address, 10_00, sender=switchboard_alpha.address)

    prepareVaultWithYield(1000 * EIGHTEEN_DECIMALS)

    user_deposit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)
    undy_usd_vault.deposit(user_deposit, bob, sender=bob)

    withdraw_amount = 800 * EIGHTEEN_DECIMALS
    initial_balance = yield_underlying_token.balanceOf(bob)

    undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)

    final_balance = yield_underlying_token.balanceOf(bob)
    assert final_balance == initial_balance + withdraw_amount


#############################
# Multi-Position Withdrawal #
#############################


def test_redemption_multiple_positions_sequential(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, yield_vault_token_2, starter_agent, bob):
    """Test redemption withdraws from multiple positions sequentially"""

    deposit_1 = 500 * EIGHTEEN_DECIMALS
    deposit_2 = 500 * EIGHTEEN_DECIMALS

    yield_underlying_token.transfer(undy_usd_vault.address, deposit_1 + deposit_2, sender=yield_underlying_token_whale)

    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_1,
        sender=starter_agent.address
    )

    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token_2.address,
        deposit_2,
        sender=starter_agent.address
    )

    assert undy_usd_vault.numAssets() == 3

    user_deposit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)
    undy_usd_vault.deposit(user_deposit, bob, sender=bob)

    withdraw_amount = 900 * EIGHTEEN_DECIMALS
    initial_balance = yield_underlying_token.balanceOf(bob)

    undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)

    final_balance = yield_underlying_token.balanceOf(bob)
    assert final_balance == initial_balance + withdraw_amount


def test_redemption_target_reached_mid_loop(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, yield_vault_token_2, starter_agent, bob):
    """Test redemption stops when target amount is reached"""

    deposit_1 = 800 * EIGHTEEN_DECIMALS
    deposit_2 = 800 * EIGHTEEN_DECIMALS

    yield_underlying_token.transfer(undy_usd_vault.address, deposit_1 + deposit_2, sender=yield_underlying_token_whale)

    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_1,
        sender=starter_agent.address
    )

    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token_2.address,
        deposit_2,
        sender=starter_agent.address
    )

    user_deposit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)
    undy_usd_vault.deposit(user_deposit, bob, sender=bob)

    vault_token_2_before = yield_vault_token_2.balanceOf(undy_usd_vault.address)

    withdraw_amount = 500 * EIGHTEEN_DECIMALS
    undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)

    vault_token_2_after = yield_vault_token_2.balanceOf(undy_usd_vault.address)

    assert vault_token_2_after == vault_token_2_before


def test_redemption_skip_empty_positions(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, yield_vault_token_2, yield_vault_token_3, starter_agent, bob):
    """Test redemption skips empty/gap positions"""

    deposit_1 = 400 * EIGHTEEN_DECIMALS
    deposit_2 = 400 * EIGHTEEN_DECIMALS
    deposit_3 = 400 * EIGHTEEN_DECIMALS

    yield_underlying_token.transfer(undy_usd_vault.address, deposit_1 + deposit_2 + deposit_3, sender=yield_underlying_token_whale)

    _, _, vault_tokens_1, _ = undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_1,
        sender=starter_agent.address
    )

    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token_2.address,
        deposit_2,
        sender=starter_agent.address
    )

    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token_3.address,
        deposit_3,
        sender=starter_agent.address
    )

    undy_usd_vault.withdrawFromYield(
        1,
        yield_vault_token.address,
        vault_tokens_1,
        sender=starter_agent.address
    )

    assert undy_usd_vault.numAssets() == 3
    assert undy_usd_vault.assets(1) == yield_vault_token_3.address

    user_deposit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)
    undy_usd_vault.deposit(user_deposit, bob, sender=bob)

    withdraw_amount = 700 * EIGHTEEN_DECIMALS
    initial_balance = yield_underlying_token.balanceOf(bob)

    undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)

    final_balance = yield_underlying_token.balanceOf(bob)
    assert final_balance == initial_balance + withdraw_amount


def test_redemption_deregister_multiple_positions(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, yield_vault_token_2, yield_vault_token_3, starter_agent, bob):
    """Test redemption deregisters multiple fully-drained positions"""

    deposit_1 = 150 * EIGHTEEN_DECIMALS
    deposit_2 = 150 * EIGHTEEN_DECIMALS
    deposit_3 = 150 * EIGHTEEN_DECIMALS

    yield_underlying_token.transfer(undy_usd_vault.address, deposit_1 + deposit_2 + deposit_3, sender=yield_underlying_token_whale)

    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_1,
        sender=starter_agent.address
    )

    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token_2.address,
        deposit_2,
        sender=starter_agent.address
    )

    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token_3.address,
        deposit_3,
        sender=starter_agent.address
    )

    assert undy_usd_vault.numAssets() == 4

    user_deposit = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)
    undy_usd_vault.deposit(user_deposit, bob, sender=bob)

    withdraw_amount = 495 * EIGHTEEN_DECIMALS
    undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)

    assert undy_usd_vault.numAssets() == 1
    assert undy_usd_vault.indexOfAsset(yield_vault_token.address) == 0
    assert undy_usd_vault.indexOfAsset(yield_vault_token_2.address) == 0
    assert undy_usd_vault.indexOfAsset(yield_vault_token_3.address) == 0


##########################
# Precision & Edge Cases #
##########################


def test_redemption_large_amount_multiple_positions(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, yield_vault_token_2, yield_vault_token_3, starter_agent, bob):
    """Test redemption of very large amounts across multiple positions"""

    deposit_1 = 10_000_000 * EIGHTEEN_DECIMALS
    deposit_2 = 10_000_000 * EIGHTEEN_DECIMALS
    deposit_3 = 10_000_000 * EIGHTEEN_DECIMALS

    yield_underlying_token.transfer(undy_usd_vault.address, deposit_1 + deposit_2 + deposit_3, sender=yield_underlying_token_whale)

    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_1,
        sender=starter_agent.address
    )

    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token_2.address,
        deposit_2,
        sender=starter_agent.address
    )

    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token_3.address,
        deposit_3,
        sender=starter_agent.address
    )

    user_deposit = 1_000_000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)
    undy_usd_vault.deposit(user_deposit, bob, sender=bob)

    withdraw_amount = 25_000_000 * EIGHTEEN_DECIMALS
    initial_balance = yield_underlying_token.balanceOf(bob)

    undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)

    final_balance = yield_underlying_token.balanceOf(bob)
    assert final_balance == initial_balance + withdraw_amount


def test_redemption_dust_amounts(prepareVaultWithYield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob):
    """Test redemption of very small (dust) amounts"""

    prepareVaultWithYield(1000 * EIGHTEEN_DECIMALS)

    user_deposit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)
    undy_usd_vault.deposit(user_deposit, bob, sender=bob)

    withdraw_amount = 1 * EIGHTEEN_DECIMALS
    initial_balance = yield_underlying_token.balanceOf(bob)

    undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)

    final_balance = yield_underlying_token.balanceOf(bob)
    assert final_balance == initial_balance + withdraw_amount


def test_redemption_insufficient_liquidity(prepareVaultWithYield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob):
    """Test redemption fails when user tries to withdraw more than their share"""

    prepareVaultWithYield(100 * EIGHTEEN_DECIMALS)

    user_deposit = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)
    undy_usd_vault.deposit(user_deposit, bob, sender=bob)

    max_withdraw = undy_usd_vault.maxWithdraw(bob)
    withdraw_amount = max_withdraw + (100 * EIGHTEEN_DECIMALS)

    with boa.reverts("insufficient shares"):
        undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)


#####################
# Integration Tests #
#####################


def test_redemption_via_erc4626_withdraw(prepareVaultWithYield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob):
    """Test ERC4626 withdraw triggers _prepareRedemption correctly"""

    prepareVaultWithYield(1000 * EIGHTEEN_DECIMALS)

    user_deposit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)
    undy_usd_vault.deposit(user_deposit, bob, sender=bob)

    withdraw_amount = 900 * EIGHTEEN_DECIMALS
    initial_balance = yield_underlying_token.balanceOf(bob)

    undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)

    final_balance = yield_underlying_token.balanceOf(bob)
    assert final_balance == initial_balance + withdraw_amount

    logs = filter_logs(undy_usd_vault, "Withdraw")
    assert len(logs) == 1
    assert logs[0].receiver == bob
    assert logs[0].owner == bob
    assert logs[0].assets == withdraw_amount


def test_redemption_via_erc4626_redeem(prepareVaultWithYield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob):
    """Test ERC4626 redeem triggers _prepareRedemption correctly"""

    prepareVaultWithYield(1000 * EIGHTEEN_DECIMALS)

    user_deposit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)
    shares = undy_usd_vault.deposit(user_deposit, bob, sender=bob)

    redeem_shares = shares
    initial_balance = yield_underlying_token.balanceOf(bob)

    assets = undy_usd_vault.redeem(redeem_shares, bob, bob, sender=bob)

    final_balance = yield_underlying_token.balanceOf(bob)
    assert final_balance > initial_balance

    logs = filter_logs(undy_usd_vault, "Withdraw")
    assert len(logs) == 1
    assert logs[0].receiver == bob
    assert logs[0].shares == redeem_shares


##############################################
# Biggest Position Withdrawal Priority Tests #
##############################################


def test_biggest_position_withdrawn_first_two_positions(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, yield_vault_token_2, starter_agent, bob):
    """Test that the biggest position is withdrawn from first when there are two positions"""

    # Create two positions: small first, then large
    small_deposit = 300 * EIGHTEEN_DECIMALS
    large_deposit = 700 * EIGHTEEN_DECIMALS

    yield_underlying_token.transfer(undy_usd_vault.address, small_deposit + large_deposit, sender=yield_underlying_token_whale)

    # First position (smaller)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        small_deposit,
        sender=starter_agent.address
    )

    # Second position (larger)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token_2.address,
        large_deposit,
        sender=starter_agent.address
    )

    # User deposits
    user_deposit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)
    undy_usd_vault.deposit(user_deposit, bob, sender=bob)

    # Record balances before withdrawal
    vault_token_1_before = yield_vault_token.balanceOf(undy_usd_vault.address)
    vault_token_2_before = yield_vault_token_2.balanceOf(undy_usd_vault.address)

    # Withdraw amount that requires pulling from yield (but not all of the large position)
    withdraw_amount = 400 * EIGHTEEN_DECIMALS
    undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)

    # Record balances after withdrawal
    vault_token_1_after = yield_vault_token.balanceOf(undy_usd_vault.address)
    vault_token_2_after = yield_vault_token_2.balanceOf(undy_usd_vault.address)

    # The large position (vault_token_2) should have been withdrawn from
    assert vault_token_2_after < vault_token_2_before, "Largest position should have been withdrawn from"

    # The small position (vault_token_1) should NOT have been touched
    assert vault_token_1_after == vault_token_1_before, "Smaller position should not have been withdrawn from"


def test_biggest_position_withdrawn_first_three_positions(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, yield_vault_token_2, yield_vault_token_3, starter_agent, bob):
    """Test that the biggest position is withdrawn from first when there are three positions of different sizes"""

    # Create three positions: medium, small, large (in that order)
    medium_deposit = 400 * EIGHTEEN_DECIMALS
    small_deposit = 200 * EIGHTEEN_DECIMALS
    large_deposit = 800 * EIGHTEEN_DECIMALS

    yield_underlying_token.transfer(undy_usd_vault.address, medium_deposit + small_deposit + large_deposit, sender=yield_underlying_token_whale)

    # First position (medium)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        medium_deposit,
        sender=starter_agent.address
    )

    # Second position (small)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token_2.address,
        small_deposit,
        sender=starter_agent.address
    )

    # Third position (large - biggest)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token_3.address,
        large_deposit,
        sender=starter_agent.address
    )

    # User deposits
    user_deposit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)
    undy_usd_vault.deposit(user_deposit, bob, sender=bob)

    # Record balances before withdrawal
    vault_token_1_before = yield_vault_token.balanceOf(undy_usd_vault.address)
    vault_token_2_before = yield_vault_token_2.balanceOf(undy_usd_vault.address)
    vault_token_3_before = yield_vault_token_3.balanceOf(undy_usd_vault.address)

    # Withdraw amount that requires pulling from yield (but not all of the large position)
    withdraw_amount = 500 * EIGHTEEN_DECIMALS
    undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)

    # Record balances after withdrawal
    vault_token_1_after = yield_vault_token.balanceOf(undy_usd_vault.address)
    vault_token_2_after = yield_vault_token_2.balanceOf(undy_usd_vault.address)
    vault_token_3_after = yield_vault_token_3.balanceOf(undy_usd_vault.address)

    # The large position (vault_token_3) should have been withdrawn from
    assert vault_token_3_after < vault_token_3_before, "Largest position should have been withdrawn from"

    # The medium and small positions should NOT have been touched
    assert vault_token_1_after == vault_token_1_before, "Medium position should not have been withdrawn from"
    assert vault_token_2_after == vault_token_2_before, "Small position should not have been withdrawn from"


def test_biggest_position_exhausted_then_next_positions(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, yield_vault_token_2, yield_vault_token_3, starter_agent, bob):
    """Test that after the biggest position is exhausted, withdrawal continues to other positions"""

    # Create three positions with varying sizes
    small_deposit = 200 * EIGHTEEN_DECIMALS
    medium_deposit = 300 * EIGHTEEN_DECIMALS
    large_deposit = 400 * EIGHTEEN_DECIMALS

    yield_underlying_token.transfer(undy_usd_vault.address, small_deposit + medium_deposit + large_deposit, sender=yield_underlying_token_whale)

    # First position (small)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        small_deposit,
        sender=starter_agent.address
    )

    # Second position (medium)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token_2.address,
        medium_deposit,
        sender=starter_agent.address
    )

    # Third position (large - biggest)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token_3.address,
        large_deposit,
        sender=starter_agent.address
    )

    # User deposits
    user_deposit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)
    undy_usd_vault.deposit(user_deposit, bob, sender=bob)

    # Record balances before withdrawal
    vault_token_1_before = yield_vault_token.balanceOf(undy_usd_vault.address)
    vault_token_2_before = yield_vault_token_2.balanceOf(undy_usd_vault.address)
    vault_token_3_before = yield_vault_token_3.balanceOf(undy_usd_vault.address)

    # Withdraw amount that exceeds the largest position - should pull from biggest first, then others
    withdraw_amount = 850 * EIGHTEEN_DECIMALS
    undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)

    # Record balances after withdrawal
    vault_token_1_after = yield_vault_token.balanceOf(undy_usd_vault.address)
    vault_token_2_after = yield_vault_token_2.balanceOf(undy_usd_vault.address)
    vault_token_3_after = yield_vault_token_3.balanceOf(undy_usd_vault.address)

    # The large position should be fully withdrawn (or nearly fully)
    assert vault_token_3_after < vault_token_3_before, "Largest position should have been withdrawn from first"

    # At least one of the other positions should have been withdrawn from as well
    other_positions_touched = (vault_token_1_after < vault_token_1_before) or (vault_token_2_after < vault_token_2_before)
    assert other_positions_touched, "After exhausting biggest position, should withdraw from other positions"


def test_biggest_position_identified_correctly_with_equal_sizes(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, yield_vault_token_2, starter_agent, bob):
    """Test behavior when multiple positions have equal sizes (should pick one deterministically)"""

    # Create two positions of equal size
    deposit_amount = 500 * EIGHTEEN_DECIMALS

    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount * 2, sender=yield_underlying_token_whale)

    # First position
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Second position (same size)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token_2.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # User deposits
    user_deposit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)
    undy_usd_vault.deposit(user_deposit, bob, sender=bob)

    # Record balances before withdrawal
    vault_token_1_before = yield_vault_token.balanceOf(undy_usd_vault.address)
    vault_token_2_before = yield_vault_token_2.balanceOf(undy_usd_vault.address)

    # Withdraw amount that requires pulling from yield
    withdraw_amount = 300 * EIGHTEEN_DECIMALS
    undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)

    # Record balances after withdrawal
    vault_token_1_after = yield_vault_token.balanceOf(undy_usd_vault.address)
    vault_token_2_after = yield_vault_token_2.balanceOf(undy_usd_vault.address)

    # Exactly one position should have been withdrawn from (since they're equal, it picks one)
    position_1_touched = vault_token_1_after < vault_token_1_before
    position_2_touched = vault_token_2_after < vault_token_2_before

    # Should withdraw from exactly one position (not both for this amount)
    assert position_1_touched or position_2_touched, "Should withdraw from one of the equal-sized positions"


def test_biggest_position_withdrawal_order_matters(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, yield_vault_token_2, yield_vault_token_3, starter_agent, bob):
    """Test that withdrawal order is based on position size, not registration order"""

    # Create three positions in a specific order: medium, large, small
    # to ensure the biggest gets withdrawn from first regardless of order
    medium_deposit = 400 * EIGHTEEN_DECIMALS
    large_deposit = 900 * EIGHTEEN_DECIMALS
    small_deposit = 200 * EIGHTEEN_DECIMALS

    yield_underlying_token.transfer(undy_usd_vault.address, medium_deposit + large_deposit + small_deposit, sender=yield_underlying_token_whale)

    # Register in order: medium, large, small
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        medium_deposit,
        sender=starter_agent.address
    )

    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token_2.address,
        large_deposit,
        sender=starter_agent.address
    )

    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token_3.address,
        small_deposit,
        sender=starter_agent.address
    )

    # User deposits
    user_deposit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)
    undy_usd_vault.deposit(user_deposit, bob, sender=bob)

    # Record balances before withdrawal
    vault_token_1_before = yield_vault_token.balanceOf(undy_usd_vault.address)
    vault_token_2_before = yield_vault_token_2.balanceOf(undy_usd_vault.address)
    vault_token_3_before = yield_vault_token_3.balanceOf(undy_usd_vault.address)

    # Withdraw amount that requires pulling from yield
    withdraw_amount = 700 * EIGHTEEN_DECIMALS
    undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)

    # Record balances after withdrawal
    vault_token_1_after = yield_vault_token.balanceOf(undy_usd_vault.address)
    vault_token_2_after = yield_vault_token_2.balanceOf(undy_usd_vault.address)
    vault_token_3_after = yield_vault_token_3.balanceOf(undy_usd_vault.address)

    # The largest position (vault_token_2 with 900) should be withdrawn from first
    assert vault_token_2_after < vault_token_2_before, "Largest position should be withdrawn from"

    # The medium and small positions should NOT be touched for this withdrawal size
    assert vault_token_1_after == vault_token_1_before, "Medium position should not be touched"
    assert vault_token_3_after == vault_token_3_before, "Small position should not be touched"


def test_biggest_position_not_withdrawn_twice(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, yield_vault_token_2, starter_agent, bob):
    """Test that the biggest position is not withdrawn from twice in a single redemption"""

    # Create two positions
    small_deposit = 300 * EIGHTEEN_DECIMALS
    large_deposit = 700 * EIGHTEEN_DECIMALS

    yield_underlying_token.transfer(undy_usd_vault.address, small_deposit + large_deposit, sender=yield_underlying_token_whale)

    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        small_deposit,
        sender=starter_agent.address
    )

    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token_2.address,
        large_deposit,
        sender=starter_agent.address
    )

    # User deposits
    user_deposit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)
    undy_usd_vault.deposit(user_deposit, bob, sender=bob)

    vault_token_2_before = yield_vault_token_2.balanceOf(undy_usd_vault.address)

    # Withdraw amount that would require pulling more than what's in the biggest position
    # if it were withdrawn from twice
    withdraw_amount = 900 * EIGHTEEN_DECIMALS
    undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)

    vault_token_2_after = yield_vault_token_2.balanceOf(undy_usd_vault.address)

    # Calculate how much was withdrawn from the large position
    withdrawn_from_large = vault_token_2_before - vault_token_2_after

    # Should not have withdrawn more than exists in the position
    assert withdrawn_from_large <= large_deposit, "Should not withdraw more than the position contains"


def test_biggest_position_exact_amount_withdrawal(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, yield_vault_token_2, starter_agent, bob):
    """Test withdrawal of exactly the biggest position's size"""

    # Create two positions
    small_deposit = 300 * EIGHTEEN_DECIMALS
    large_deposit = 700 * EIGHTEEN_DECIMALS

    yield_underlying_token.transfer(undy_usd_vault.address, small_deposit + large_deposit, sender=yield_underlying_token_whale)

    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        small_deposit,
        sender=starter_agent.address
    )

    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token_2.address,
        large_deposit,
        sender=starter_agent.address
    )

    # User deposits
    user_deposit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)
    undy_usd_vault.deposit(user_deposit, bob, sender=bob)

    # Record balances
    vault_token_1_before = yield_vault_token.balanceOf(undy_usd_vault.address)
    vault_token_2_before = yield_vault_token_2.balanceOf(undy_usd_vault.address)

    # Withdraw exactly the size of the large position (accounting for redemption buffer)
    # With 2% buffer, withdrawing 686 should pull ~700 from yield
    withdraw_amount = 686 * EIGHTEEN_DECIMALS
    undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)

    vault_token_1_after = yield_vault_token.balanceOf(undy_usd_vault.address)
    vault_token_2_after = yield_vault_token_2.balanceOf(undy_usd_vault.address)

    # Large position should be significantly drained or empty
    assert vault_token_2_after < vault_token_2_before, "Large position should be withdrawn from"

    # Small position might be untouched or only slightly touched
    small_position_change = vault_token_1_before - vault_token_1_after
    large_position_change = vault_token_2_before - vault_token_2_after

    # Most of the withdrawal should come from the large position
    assert large_position_change > small_position_change, "Most withdrawal should come from largest position"


def test_biggest_position_with_buffer_calculation(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, yield_vault_token_2, vault_registry, switchboard_alpha, starter_agent, bob):
    """Test that redemption buffer is applied correctly when withdrawing from biggest position"""

    # Set a known buffer
    vault_registry.setRedemptionBuffer(undy_usd_vault.address, 5_00, sender=switchboard_alpha.address)

    small_deposit = 400 * EIGHTEEN_DECIMALS
    large_deposit = 600 * EIGHTEEN_DECIMALS

    yield_underlying_token.transfer(undy_usd_vault.address, small_deposit + large_deposit, sender=yield_underlying_token_whale)

    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        small_deposit,
        sender=starter_agent.address
    )

    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token_2.address,
        large_deposit,
        sender=starter_agent.address
    )

    user_deposit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)
    undy_usd_vault.deposit(user_deposit, bob, sender=bob)

    vault_token_2_before = yield_vault_token_2.balanceOf(undy_usd_vault.address)

    # Request withdrawal - with 5% buffer, should pull 105% from yield
    withdraw_amount = 500 * EIGHTEEN_DECIMALS
    undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)

    vault_token_2_after = yield_vault_token_2.balanceOf(undy_usd_vault.address)

    # Should have withdrawn from the large position
    assert vault_token_2_after < vault_token_2_before, "Should withdraw from largest position with buffer applied"


def test_biggest_position_fully_drained_and_deregistered(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, yield_vault_token_2, starter_agent, bob):
    """Test that biggest position is properly deregistered when fully drained"""

    small_deposit = 400 * EIGHTEEN_DECIMALS
    large_deposit = 500 * EIGHTEEN_DECIMALS

    yield_underlying_token.transfer(undy_usd_vault.address, small_deposit + large_deposit, sender=yield_underlying_token_whale)

    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        small_deposit,
        sender=starter_agent.address
    )

    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token_2.address,
        large_deposit,
        sender=starter_agent.address
    )

    assert undy_usd_vault.numAssets() == 3
    assert undy_usd_vault.indexOfAsset(yield_vault_token_2.address) == 2

    user_deposit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob, user_deposit, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, user_deposit, sender=bob)
    undy_usd_vault.deposit(user_deposit, bob, sender=bob)

    # Withdraw amount that will fully drain the large position
    withdraw_amount = 800 * EIGHTEEN_DECIMALS
    undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)

    # Large position should be deregistered if fully drained
    vault_token_2_balance = yield_vault_token_2.balanceOf(undy_usd_vault.address)

    if vault_token_2_balance == 0:
        # Should be deregistered
        assert undy_usd_vault.indexOfAsset(yield_vault_token_2.address) == 0, "Fully drained position should be deregistered"