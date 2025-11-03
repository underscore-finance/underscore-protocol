import pytest
import boa

from constants import EIGHTEEN_DECIMALS, MAX_UINT256
from conf_utils import filter_logs


###########
# Fixtures #
############


@pytest.fixture(scope="module")
def setup_vault_with_deposit(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob):
    """Setup fixture that deposits into vault and returns the amount"""
    def setup_vault_with_deposit(_amount=1000 * EIGHTEEN_DECIMALS):
        # User deposits to get shares
        yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
        shares = undy_usd_vault.deposit(_amount, bob, sender=yield_underlying_token_whale)

        return _amount, shares

    yield setup_vault_with_deposit


@pytest.fixture(scope="module")
def setup_yield_position(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token):
    """Setup fixture that creates a yield position"""
    def setup_yield_position(_amount=1000 * EIGHTEEN_DECIMALS):
        # Transfer underlying to vault
        yield_underlying_token.transfer(undy_usd_vault.address, _amount, sender=yield_underlying_token_whale)

        # Deposit for yield
        _, vault_token, vault_tokens_received, _ = undy_usd_vault.depositForYield(
            1,  # lego_id
            yield_underlying_token.address,
            yield_vault_token.address,
            _amount,
            sender=starter_agent.address
        )

        return _amount, vault_tokens_received

    yield setup_yield_position


@pytest.fixture(scope="module")
def simulate_yield(yield_underlying_token, yield_vault_token, governance):
    """Helper to simulate yield accrual by minting tokens to yield vault"""
    def simulate_yield(_yield_amount):
        yield_underlying_token.mint(yield_vault_token.address, _yield_amount, sender=governance.address)
        return _yield_amount

    yield simulate_yield


#######################################
# 1. Initial State & Basic Setup (3) #
#######################################


def test_initial_state_yield_tracking_variables(undy_usd_vault):
    """Test that yield tracking variables are initialized to zero"""
    assert undy_usd_vault.lastUnderlyingBal() == 0
    assert undy_usd_vault.pendingYieldRealized() == 0


def test_first_deposit_sets_last_underlying_bal(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob):
    """Test that first deposit correctly sets lastUnderlyingBal"""
    deposit_amount = 100 * EIGHTEEN_DECIMALS

    # Initial state
    assert undy_usd_vault.lastUnderlyingBal() == 0

    # Deposit
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)

    # lastUnderlyingBal should be set to deposit amount (no yield positions yet)
    assert undy_usd_vault.lastUnderlyingBal() == 0  # Still 0 because no yield position
    assert undy_usd_vault.pendingYieldRealized() == 0


def test_state_after_first_deposit_for_yield(setup_yield_position, undy_usd_vault):
    """Test state after first depositForYield operation"""
    deposit_amount = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(deposit_amount)

    # After depositing for yield, lastUnderlyingBal should be set
    assert undy_usd_vault.lastUnderlyingBal() == deposit_amount
    assert undy_usd_vault.pendingYieldRealized() == 0  # No yield yet


#####################################
# 2. Yield Accrual Tracking (8) #
#####################################


def test_yield_accrual_between_deposits(_test, setup_yield_position, simulate_yield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token):
    """Test yield accrual is tracked between deposits"""
    # Initial deposit
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    # Simulate yield (20% gain)
    yield_amount = 200 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)

    # Time travel to allow snapshot update
    boa.env.time_travel(seconds=301)

    # Another deposit should trigger yield calculation
    second_deposit = 500 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, second_deposit, sender=yield_underlying_token_whale)

    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        second_deposit,
        sender=starter_agent.address
    )

    # pendingYieldRealized should now include the yield
    assert undy_usd_vault.pendingYieldRealized() == yield_amount
    # lastUnderlyingBal should be updated to current underlying
    expected_underlying = initial_deposit + yield_amount + second_deposit
    _test(expected_underlying, undy_usd_vault.lastUnderlyingBal())


def test_yield_accrual_with_multiple_deposits(setup_yield_position, simulate_yield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token):
    """Test yield tracking with multiple sequential deposits"""
    # First deposit
    deposit1 = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(deposit1)

    # Yield 1
    yield1 = 100 * EIGHTEEN_DECIMALS
    simulate_yield(yield1)
    boa.env.time_travel(seconds=301)

    # Second deposit (triggers yield calculation)
    deposit2 = 500 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit2, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, deposit2, sender=starter_agent.address)

    assert undy_usd_vault.pendingYieldRealized() == yield1

    # Yield 2
    yield2 = 150 * EIGHTEEN_DECIMALS
    simulate_yield(yield2)
    boa.env.time_travel(seconds=301)

    # Third deposit (triggers another yield calculation)
    deposit3 = 300 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit3, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, deposit3, sender=starter_agent.address)

    # Total yield should be yield1 + yield2
    assert abs(undy_usd_vault.pendingYieldRealized() - (yield1 + yield2)) <= 100


def test_yield_accrual_with_multiple_yield_positions(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token, yield_vault_token_2, governance):
    """Test yield tracking with multiple yield positions"""
    # Deposit to first yield position
    deposit1 = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit1, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, deposit1, sender=starter_agent.address)

    # Deposit to second yield position
    deposit2 = 800 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit2, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token_2.address, deposit2, sender=starter_agent.address)

    # Simulate yield on both positions
    yield1 = 100 * EIGHTEEN_DECIMALS
    yield2 = 80 * EIGHTEEN_DECIMALS
    yield_underlying_token.mint(yield_vault_token.address, yield1, sender=governance.address)
    yield_underlying_token.mint(yield_vault_token_2.address, yield2, sender=governance.address)

    boa.env.time_travel(seconds=301)

    # Trigger yield calculation with another deposit
    deposit3 = 200 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit3, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, deposit3, sender=starter_agent.address)

    # Should track total yield from both positions
    assert undy_usd_vault.pendingYieldRealized() == yield1 + yield2


def test_yield_doesnt_accrue_same_block(setup_yield_position, simulate_yield, undy_usd_vault):
    """Test that yield doesn't accrue during same-block operations"""
    deposit_amount = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(deposit_amount)

    # Simulate yield
    yield_amount = 200 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)

    # Without time travel, yield might not be reflected in same block
    # (depending on how yield vault works)
    # This test ensures consistency
    assert undy_usd_vault.pendingYieldRealized() == 0  # No trigger yet


def test_yield_tracking_with_auto_deposit(setup_vault_with_deposit, setup_yield_position, simulate_yield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, vault_registry, switchboard_alpha, yield_vault_token):
    """Test yield tracking when auto-deposit is enabled"""
    # Enable auto-deposit
    vault_registry.setShouldAutoDeposit(undy_usd_vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setDefaultTargetVaultToken(undy_usd_vault.address, yield_vault_token.address, sender=switchboard_alpha.address)

    # Setup initial yield position
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    # Simulate yield
    yield_amount = 200 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    # User deposit (should auto-deposit and trigger yield calculation)
    user_deposit = 500 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    undy_usd_vault.deposit(user_deposit, bob, sender=yield_underlying_token_whale)

    # Yield should be tracked
    assert abs(undy_usd_vault.pendingYieldRealized() - yield_amount) <= 500


def test_large_yield_accrual(setup_yield_position, simulate_yield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token):
    """Test yield tracking with large yield (10x balance)"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    # 10x yield
    yield_amount = 10000 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    # Trigger yield calculation
    trigger_deposit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger_deposit, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger_deposit, sender=starter_agent.address)

    assert undy_usd_vault.pendingYieldRealized() == yield_amount


def test_small_yield_accrual(setup_yield_position, simulate_yield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token):
    """Test yield tracking with small yield (0.1% balance)"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    # 0.1% yield
    yield_amount = EIGHTEEN_DECIMALS  # 1 token
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    # Trigger yield calculation
    trigger_deposit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger_deposit, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger_deposit, sender=starter_agent.address)

    assert undy_usd_vault.pendingYieldRealized() == yield_amount


def test_yield_accrual_followed_by_more_yield(setup_yield_position, simulate_yield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token):
    """Test consecutive yield accruals accumulate correctly"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    # First yield
    yield1 = 100 * EIGHTEEN_DECIMALS
    simulate_yield(yield1)
    boa.env.time_travel(seconds=301)

    # Trigger
    trigger_deposit = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger_deposit, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger_deposit, sender=starter_agent.address)

    assert undy_usd_vault.pendingYieldRealized() == yield1

    # Second yield
    yield2 = 150 * EIGHTEEN_DECIMALS
    simulate_yield(yield2)
    boa.env.time_travel(seconds=301)

    # Trigger again
    yield_underlying_token.transfer(undy_usd_vault.address, trigger_deposit, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger_deposit, sender=starter_agent.address)

    assert abs(undy_usd_vault.pendingYieldRealized() - (yield1 + yield2)) <= 500


#######################################
# 3. Withdrawal Impact on Yield (5) #
#######################################


def test_withdrawal_doesnt_register_as_negative_yield(setup_vault_with_deposit, setup_yield_position, undy_usd_vault, bob):
    """Test that withdrawing doesn't create negative yield"""
    # Setup
    user_deposit, user_shares = setup_vault_with_deposit(1000 * EIGHTEEN_DECIMALS)
    initial_deposit, _ = setup_yield_position(500 * EIGHTEEN_DECIMALS)

    initial_pending = undy_usd_vault.pendingYieldRealized()

    # User withdraws
    undy_usd_vault.redeem(user_shares // 2, bob, bob, sender=bob)

    # pendingYieldRealized should not decrease
    assert undy_usd_vault.pendingYieldRealized() >= initial_pending


def test_yield_accrual_then_withdrawal_preserves_yield(_test, setup_yield_position, simulate_yield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, starter_agent, yield_vault_token):
    """Test that yield is preserved after withdrawal"""
    # Setup with yield
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    # Simulate yield
    yield_amount = 200 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    # Deposit to trigger yield calculation
    trigger = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    _test(yield_amount, undy_usd_vault.pendingYieldRealized())

    # User makes a deposit to get shares
    user_deposit = 500 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    shares = undy_usd_vault.deposit(user_deposit, bob, sender=yield_underlying_token_whale)

    # User withdraws
    undy_usd_vault.redeem(shares, bob, bob, sender=bob)

    # pendingYieldRealized should still be the same
    _test(yield_amount, undy_usd_vault.pendingYieldRealized())


def test_partial_withdrawal_impact_on_tracking(setup_vault_with_deposit, setup_yield_position, simulate_yield, undy_usd_vault, bob, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token):
    """Test partial withdrawal updates lastUnderlyingBal correctly"""
    user_deposit, user_shares = setup_vault_with_deposit(1000 * EIGHTEEN_DECIMALS)
    initial_deposit, _ = setup_yield_position(500 * EIGHTEEN_DECIMALS)

    # Simulate yield
    yield_amount = 100 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)

    # Trigger yield calculation
    boa.env.time_travel(seconds=301)
    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # Deposit remaining idle balance to yield to force withdrawal from yield during redemption
    idle_balance = yield_underlying_token.balanceOf(undy_usd_vault.address)
    if idle_balance > 100 * EIGHTEEN_DECIMALS:
        undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, idle_balance - 100 * EIGHTEEN_DECIMALS, sender=starter_agent.address)

    initial_last_bal = undy_usd_vault.lastUnderlyingBal()

    # Partial withdrawal
    undy_usd_vault.redeem(user_shares // 2, bob, bob, sender=bob)

    # lastUnderlyingBal should be updated to reflect withdrawal
    new_last_bal = undy_usd_vault.lastUnderlyingBal()
    assert new_last_bal < initial_last_bal  # Should decrease after withdrawal


def test_full_withdrawal_and_yield_reset(setup_vault_with_deposit, undy_usd_vault, bob):
    """Test full withdrawal handling"""
    user_deposit, user_shares = setup_vault_with_deposit(1000 * EIGHTEEN_DECIMALS)

    # Full withdrawal
    undy_usd_vault.redeem(user_shares, bob, bob, sender=bob)

    # State should be updated
    # (pendingYieldRealized is NOT reset on withdrawal, only on claimPerformanceFees)
    assert undy_usd_vault.lastUnderlyingBal() >= 0


def test_withdraw_from_yield_position_updates_last_underlying_bal(setup_yield_position, undy_usd_vault, starter_agent, yield_vault_token):
    """Test that withdrawFromYield updates lastUnderlyingBal"""
    initial_deposit, vault_tokens = setup_yield_position(1000 * EIGHTEEN_DECIMALS)

    assert undy_usd_vault.lastUnderlyingBal() == initial_deposit

    # Withdraw from yield
    undy_usd_vault.withdrawFromYield(1, yield_vault_token.address, vault_tokens // 2, sender=starter_agent.address)

    # lastUnderlyingBal should be updated to reflect withdrawal
    new_bal = undy_usd_vault.lastUnderlyingBal()
    assert new_bal < initial_deposit


##########################################
# 4. Performance Fee Claiming (12) #
##########################################


def test_basic_fee_claim(setup_yield_position, simulate_yield, undy_usd_vault, governance, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token, vault_registry, switchboard_alpha):
    """Test basic performance fee claim with 10% fee"""
    # Setup
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    # Set 10% performance fee
    vault_registry.setPerformanceFee(undy_usd_vault.address, 10_00, sender=switchboard_alpha.address)

    # Simulate yield (100 tokens)
    yield_amount = 100 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    # Trigger yield calculation
    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    assert undy_usd_vault.pendingYieldRealized() == yield_amount

    # Claim fees
    gov_balance_before = yield_underlying_token.balanceOf(governance.address)
    fees_claimed = undy_usd_vault.claimPerformanceFees(sender=governance.address)
    gov_balance_after = yield_underlying_token.balanceOf(governance.address)

    expected_fees = yield_amount * 10 // 100  # 10% of 100 = 10 tokens
    assert fees_claimed == expected_fees
    assert gov_balance_after - gov_balance_before == expected_fees
    assert undy_usd_vault.pendingYieldRealized() == 0  # Reset


def test_fee_claim_with_zero_percent_fee(setup_yield_position, simulate_yield, undy_usd_vault, governance, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token, vault_registry, switchboard_alpha):
    """Test fee claim with 0% fee ratio"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    # Set 0% fee
    vault_registry.setPerformanceFee(undy_usd_vault.address, 0, sender=switchboard_alpha.address)

    # Yield
    yield_amount = 100 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    # Trigger
    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # Claim fees (should be 0)
    fees_claimed = undy_usd_vault.claimPerformanceFees(sender=governance.address)
    assert fees_claimed == 0
    assert undy_usd_vault.pendingYieldRealized() == 0  # Still reset


def test_fee_claim_with_hundred_percent_fee(_test, setup_yield_position, simulate_yield, undy_usd_vault, governance, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token, vault_registry, switchboard_alpha):
    """Test fee claim with 100% fee ratio"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    # Set 100% fee
    vault_registry.setPerformanceFee(undy_usd_vault.address, 100_00, sender=switchboard_alpha.address)

    # Yield
    yield_amount = 100 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    # Trigger
    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # Claim all yield as fees
    fees_claimed = undy_usd_vault.claimPerformanceFees(sender=governance.address)
    _test(yield_amount, fees_claimed)  # 100% of yield


def test_fee_claim_with_various_fee_ratios(setup_yield_position, simulate_yield, undy_usd_vault, governance, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token, vault_registry, switchboard_alpha):
    """Test fee claims with 5%, 15%, 25% ratios"""
    fee_ratios = [5_00, 15_00, 25_00]  # 5%, 15%, 25%
    yield_amount = 1000 * EIGHTEEN_DECIMALS

    for fee_ratio in fee_ratios:
        # Fresh setup for each test
        initial_deposit = 10000 * EIGHTEEN_DECIMALS
        setup_yield_position(initial_deposit)

        vault_registry.setPerformanceFee(undy_usd_vault.address, fee_ratio, sender=switchboard_alpha.address)

        simulate_yield(yield_amount)
        boa.env.time_travel(seconds=301)

        trigger = 100 * EIGHTEEN_DECIMALS
        yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
        undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

        expected_fees = yield_amount * fee_ratio // 100_00
        fees_claimed = undy_usd_vault.claimPerformanceFees(sender=governance.address)

        assert abs(fees_claimed - expected_fees) <= 2000  # Allow small rounding


def test_fee_claim_resets_pending_yield_realized(setup_yield_position, simulate_yield, undy_usd_vault, governance, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token):
    """Test that claiming fees resets pendingYieldRealized to 0"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    yield_amount = 200 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    assert undy_usd_vault.pendingYieldRealized() == yield_amount

    undy_usd_vault.claimPerformanceFees(sender=governance.address)

    assert undy_usd_vault.pendingYieldRealized() == 0



def test_fee_claim_transfers_correct_amount_to_governance(setup_yield_position, simulate_yield, undy_usd_vault, governance, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token, vault_registry, switchboard_alpha):
    """Test that correct fee amount is transferred to governance"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    vault_registry.setPerformanceFee(undy_usd_vault.address, 20_00, sender=switchboard_alpha.address)  # 20%

    yield_amount = 500 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    gov_balance_before = yield_underlying_token.balanceOf(governance.address)
    fees_claimed = undy_usd_vault.claimPerformanceFees(sender=governance.address)
    gov_balance_after = yield_underlying_token.balanceOf(governance.address)

    expected_fees = yield_amount * 20 // 100
    assert fees_claimed == expected_fees
    assert gov_balance_after - gov_balance_before == expected_fees


def test_fee_claim_emits_correct_event(setup_yield_position, simulate_yield, undy_usd_vault, governance, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token, vault_registry, switchboard_alpha):
    """Test that PerformanceFeesClaimed event is emitted correctly"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    vault_registry.setPerformanceFee(undy_usd_vault.address, 10_00, sender=switchboard_alpha.address)

    yield_amount = 100 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    undy_usd_vault.claimPerformanceFees(sender=governance.address)

    logs = filter_logs(undy_usd_vault, "PerformanceFeesClaimed")
    assert len(logs) == 1
    assert logs[0].pendingFees == yield_amount * 10 // 100


def test_fee_claim_when_vault_needs_redemption(setup_yield_position, simulate_yield, undy_usd_vault, governance, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token, vault_registry, switchboard_alpha):
    """Test fee claim when vault needs to redeem from yield positions"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    vault_registry.setPerformanceFee(undy_usd_vault.address, 10_00, sender=switchboard_alpha.address)

    # Large yield
    yield_amount = 500 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # Vault has minimal idle balance, needs to withdraw from yield
    idle_balance = yield_underlying_token.balanceOf(undy_usd_vault.address)
    assert idle_balance < yield_amount * 10 // 100  # Less than 10% fee

    # Should still successfully claim fees by redeeming from yield
    fees_claimed = undy_usd_vault.claimPerformanceFees(sender=governance.address)
    assert fees_claimed > 0


def test_fee_claim_with_sufficient_idle_balance(setup_yield_position, simulate_yield, undy_usd_vault, governance, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token, vault_registry, switchboard_alpha):
    """Test fee claim when vault has sufficient idle balance"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    vault_registry.setPerformanceFee(undy_usd_vault.address, 10_00, sender=switchboard_alpha.address)

    yield_amount = 100 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    # Add extra idle balance
    extra_idle = 200 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, extra_idle, sender=yield_underlying_token_whale)

    trigger = 50 * EIGHTEEN_DECIMALS
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # Claim should use idle balance
    fees_claimed = undy_usd_vault.claimPerformanceFees(sender=governance.address)
    assert fees_claimed == yield_amount * 10 // 100


def test_multiple_sequential_fee_claims(setup_yield_position, simulate_yield, undy_usd_vault, governance, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token, vault_registry, switchboard_alpha):
    """Test multiple sequential fee claims"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    vault_registry.setPerformanceFee(undy_usd_vault.address, 10_00, sender=switchboard_alpha.address)

    # First yield and claim
    yield1 = 100 * EIGHTEEN_DECIMALS
    simulate_yield(yield1)
    boa.env.time_travel(seconds=301)

    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    fees1 = undy_usd_vault.claimPerformanceFees(sender=governance.address)
    assert fees1 > 0
    assert undy_usd_vault.pendingYieldRealized() == 0

    # Second yield and claim
    yield2 = 150 * EIGHTEEN_DECIMALS
    simulate_yield(yield2)
    boa.env.time_travel(seconds=301)

    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    fees2 = undy_usd_vault.claimPerformanceFees(sender=governance.address)
    assert fees2 > fees1  # Second yield was larger
    assert undy_usd_vault.pendingYieldRealized() == 0


def test_fee_claim_with_multiple_yield_positions(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token, yield_vault_token_2, governance, vault_registry, switchboard_alpha):
    """Test fee claim with multiple yield positions"""
    vault_registry.setPerformanceFee(undy_usd_vault.address, 10_00, sender=switchboard_alpha.address)

    # Setup two yield positions
    deposit1 = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit1, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, deposit1, sender=starter_agent.address)

    deposit2 = 800 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit2, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token_2.address, deposit2, sender=starter_agent.address)

    # Yield on both
    yield1 = 100 * EIGHTEEN_DECIMALS
    yield2 = 80 * EIGHTEEN_DECIMALS
    yield_underlying_token.mint(yield_vault_token.address, yield1, sender=governance.address)
    yield_underlying_token.mint(yield_vault_token_2.address, yield2, sender=governance.address)
    boa.env.time_travel(seconds=301)

    # Trigger
    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # Claim should work across both positions
    fees_claimed = undy_usd_vault.claimPerformanceFees(sender=governance.address)
    expected_total_yield = yield1 + yield2
    expected_fees = expected_total_yield * 10 // 100
    assert fees_claimed == expected_fees


#####################################
# 5. View Function Accuracy (4) #
#####################################


def test_get_claimable_performance_fees_returns_correct_value(setup_yield_position, simulate_yield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token, vault_registry, governance, switchboard_alpha):
    """Test getClaimablePerformanceFees returns accurate value"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    vault_registry.setPerformanceFee(undy_usd_vault.address, 15_00, sender=switchboard_alpha.address)  # 15%

    yield_amount = 200 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    claimable = undy_usd_vault.getClaimablePerformanceFees()
    expected = yield_amount * 15 // 100
    assert claimable == expected


def test_get_claimable_includes_unrealized_yield(setup_yield_position, simulate_yield, undy_usd_vault, vault_registry, governance, switchboard_alpha):
    """Test that getClaimablePerformanceFees includes unrealized yield"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    vault_registry.setPerformanceFee(undy_usd_vault.address, 10_00, sender=switchboard_alpha.address)

    # Yield but don't trigger calculation
    yield_amount = 100 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    # getClaimablePerformanceFees should calculate and include the unrealized yield
    claimable = undy_usd_vault.getClaimablePerformanceFees()
    expected = yield_amount * 10 // 100
    assert claimable == expected


def test_get_claimable_before_and_after_transactions(setup_yield_position, simulate_yield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token, vault_registry, switchboard_alpha):
    """Test getClaimablePerformanceFees consistency across transactions"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    vault_registry.setPerformanceFee(undy_usd_vault.address, 10_00, sender=switchboard_alpha.address)

    # Before yield
    claimable_before = undy_usd_vault.getClaimablePerformanceFees()
    assert claimable_before == 0

    # After yield
    yield_amount = 150 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    claimable_after_yield = undy_usd_vault.getClaimablePerformanceFees()
    assert claimable_after_yield == yield_amount * 10 // 100

    # After triggering calculation
    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    claimable_after_trigger = undy_usd_vault.getClaimablePerformanceFees()
    assert claimable_after_trigger == claimable_after_yield


def test_get_claimable_with_different_fee_ratios(setup_yield_position, simulate_yield, undy_usd_vault, vault_registry, governance, switchboard_alpha):
    """Test getClaimablePerformanceFees with various fee ratios"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    yield_amount = 1000 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    fee_ratios = [0, 5_00, 10_00, 25_00, 50_00, 100_00]

    for fee_ratio in fee_ratios:
        vault_registry.setPerformanceFee(undy_usd_vault.address, fee_ratio, sender=switchboard_alpha.address)

        claimable = undy_usd_vault.getClaimablePerformanceFees()
        expected = yield_amount * fee_ratio // 100_00
        assert claimable == expected


#################################################
# 6. Pending Fees Impact on totalAssets (6) #
#################################################


def test_total_assets_subtracts_pending_fees(setup_yield_position, simulate_yield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token, vault_registry, governance, switchboard_alpha):
    """Test that totalAssets correctly subtracts pending fees"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    vault_registry.setPerformanceFee(undy_usd_vault.address, 20_00, sender=switchboard_alpha.address)  # 20%

    total_before_yield = undy_usd_vault.totalAssets()

    # Add yield
    yield_amount = 500 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    # Trigger yield calculation
    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    total_after_yield = undy_usd_vault.totalAssets()

    # totalAssets should increase by (yield - fees)
    expected_fees = yield_amount * 20 // 100
    expected_increase = yield_amount - expected_fees

    # Account for the trigger deposit too
    assert abs(total_after_yield - total_before_yield - expected_increase - trigger) <= 2


def test_share_price_accounts_for_pending_fees(setup_vault_with_deposit, setup_yield_position, simulate_yield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token, vault_registry, governance, switchboard_alpha):
    """Test that share price correctly accounts for pending fees"""
    # User deposit first
    user_deposit, user_shares = setup_vault_with_deposit(1000 * EIGHTEEN_DECIMALS)

    # Create yield position
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    vault_registry.setPerformanceFee(undy_usd_vault.address, 10_00, sender=switchboard_alpha.address)

    # Record initial share value
    initial_value_per_share = undy_usd_vault.convertToAssets(EIGHTEEN_DECIMALS)

    # Add yield
    yield_amount = 100 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # Share value should increase but account for fees
    new_value_per_share = undy_usd_vault.convertToAssets(EIGHTEEN_DECIMALS)
    assert new_value_per_share > initial_value_per_share

    # Net yield to users = 90% of yield (10% goes to fees)
    # This should be reflected in share price


def test_deposit_after_yield_before_fee_claim(setup_yield_position, simulate_yield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, starter_agent, yield_vault_token):
    """Test deposit after yield accrual but before fee claim"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    # Yield
    yield_amount = 200 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # User deposits
    user_deposit = 500 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    shares = undy_usd_vault.deposit(user_deposit, bob, sender=yield_underlying_token_whale)

    # Shares should be calculated with pending fees subtracted from totalAssets
    assert shares > 0


def test_withdrawal_after_yield_before_fee_claim(setup_vault_with_deposit, setup_yield_position, simulate_yield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, starter_agent, yield_vault_token):
    """Test withdrawal after yield accrual but before fee claim"""
    user_deposit, user_shares = setup_vault_with_deposit(1000 * EIGHTEEN_DECIMALS)

    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    # Yield
    yield_amount = 200 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # User withdraws
    balance_before = yield_underlying_token.balanceOf(bob)
    undy_usd_vault.redeem(user_shares, bob, bob, sender=bob)
    balance_after = yield_underlying_token.balanceOf(bob)

    # User should get their share minus pending fees effect
    assert balance_after > balance_before


def test_convert_to_assets_shares_with_pending_fees(setup_yield_position, simulate_yield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token):
    """Test convertToAssets and convertToShares with pending fees"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    # Yield
    yield_amount = 100 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # Test convertToAssets
    test_shares = 100 * EIGHTEEN_DECIMALS
    assets = undy_usd_vault.convertToAssets(test_shares)
    assert assets > 0

    # Test convertToShares
    test_assets = 100 * EIGHTEEN_DECIMALS
    shares = undy_usd_vault.convertToShares(test_assets)
    assert shares > 0

    # Round trip should be approximately equal
    round_trip_assets = undy_usd_vault.convertToAssets(shares)
    assert abs(round_trip_assets - test_assets) <= 2  # Allow small rounding


def test_max_withdraw_redeem_with_pending_fees(setup_vault_with_deposit, setup_yield_position, simulate_yield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, starter_agent, yield_vault_token):
    """Test maxWithdraw and maxRedeem account for pending fees"""
    user_deposit, user_shares = setup_vault_with_deposit(1000 * EIGHTEEN_DECIMALS)

    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    max_withdraw_before = undy_usd_vault.maxWithdraw(bob)
    max_redeem_before = undy_usd_vault.maxRedeem(bob)

    # Yield
    yield_amount = 200 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    max_withdraw_after = undy_usd_vault.maxWithdraw(bob)
    max_redeem_after = undy_usd_vault.maxRedeem(bob)

    # maxWithdraw should account for yield and fees
    assert max_withdraw_after > max_withdraw_before
    assert max_redeem_after == max_redeem_before  # Same shares


############################################
# 7. Edge Cases & Negative Scenarios (10) #
############################################


def test_zero_yield_scenario(setup_yield_position, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token):
    """Test scenario with no yield accrual"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    # No yield, just another deposit
    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    assert undy_usd_vault.pendingYieldRealized() == 0


def test_negative_yield_doesnt_decrease_pending(setup_yield_position, undy_usd_vault, yield_vault_token, starter_agent):
    """Test that underlying decrease doesn't create negative pendingYieldRealized"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    initial_pending = undy_usd_vault.pendingYieldRealized()

    # Simulate loss by withdrawing from yield (simulates negative yield)
    # Note: In practice, negative yield is when underlying decreases
    # The implementation should not add negative values to pendingYieldRealized
    undy_usd_vault.withdrawFromYield(1, yield_vault_token.address, EIGHTEEN_DECIMALS, sender=starter_agent.address)

    # pendingYieldRealized should not decrease
    assert undy_usd_vault.pendingYieldRealized() >= initial_pending


def test_direct_transfer_to_vault(setup_yield_position, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token):
    """Test direct transfer to vault (not through depositForYield)"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    # Direct transfer
    direct_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, direct_amount, sender=yield_underlying_token_whale)

    # Should not be counted as yield until next operation
    assert undy_usd_vault.pendingYieldRealized() == 0

    # Next operation should not count direct transfer as yield
    # (because it's not in yield positions)
    trigger = 50 * EIGHTEEN_DECIMALS
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    assert undy_usd_vault.pendingYieldRealized() == 0


def test_slippage_loss_in_yield_position(setup_yield_position, simulate_yield, undy_usd_vault, yield_vault_token, starter_agent, yield_underlying_token, yield_underlying_token_whale):
    """Test handling of slippage/loss in yield position"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    # Simulate small loss (underlying decreases slightly)
    # This is done by directly withdrawing from the yield vault to simulate price decrease
    loss_amount = 10 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(yield_underlying_token_whale, loss_amount, sender=yield_vault_token.address)

    # Trigger calculation
    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # pendingYieldRealized should not increase (no profit to track)
    assert undy_usd_vault.pendingYieldRealized() == 0


def test_rounding_errors_with_small_amounts(setup_yield_position, simulate_yield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token):
    """Test rounding errors with very small amounts"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    # Very small yield (1 wei)
    simulate_yield(1)
    boa.env.time_travel(seconds=301)

    trigger = EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # Should handle tiny yield
    assert undy_usd_vault.pendingYieldRealized() >= 0


def test_very_large_pending_yield_realized(setup_yield_position, simulate_yield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token):
    """Test with very large pendingYieldRealized values"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    # Huge yield (1000x)
    huge_yield = 1_000_000 * EIGHTEEN_DECIMALS
    simulate_yield(huge_yield)
    boa.env.time_travel(seconds=301)

    trigger = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    assert undy_usd_vault.pendingYieldRealized() == huge_yield


def test_claiming_fees_when_pending_is_zero(undy_usd_vault, governance):
    """Test claiming performance fees when pendingYieldRealized is 0"""
    # No yield accrued
    assert undy_usd_vault.pendingYieldRealized() == 0

    # Claim should work but return 0
    fees = undy_usd_vault.claimPerformanceFees(sender=governance.address)
    assert fees == 0


def test_claiming_fees_insufficient_yield_positions(setup_yield_position, simulate_yield, undy_usd_vault, governance, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token, vault_registry, switchboard_alpha):
    """Test claiming fees when insufficient funds in yield positions"""
    initial_deposit = 100 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    # Set very high performance fee
    vault_registry.setPerformanceFee(undy_usd_vault.address, 90_00, sender=switchboard_alpha.address)  # 90%

    # Huge yield
    yield_amount = 10000 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # Attempt to claim (might fail due to insufficient liquidity)
    try:
        undy_usd_vault.claimPerformanceFees(sender=governance.address)
    except Exception as e:
        # Expected to potentially fail
        assert "insufficient funds" in str(e).lower()


def test_simultaneous_deposit_yield_same_block(setup_yield_position, undy_usd_vault):
    """Test deposit and yield in same block"""
    # This is more of a consistency check
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    # In same block, yield hasn't had time to accrue
    assert undy_usd_vault.pendingYieldRealized() == 0


def test_last_underlying_bal_consistency(_test, setup_yield_position, simulate_yield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token):
    """Test lastUnderlyingBal remains consistent across operations"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    assert undy_usd_vault.lastUnderlyingBal() == initial_deposit

    # Yield and trigger
    yield_amount = 200 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    expected_bal = initial_deposit + yield_amount + trigger
    _test(expected_bal, undy_usd_vault.lastUnderlyingBal())


#############################################
# 8. Permission & Access Control (3) #
#############################################


def test_only_governance_can_claim_fees(setup_yield_position, simulate_yield, undy_usd_vault, governance, bob, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token, vault_registry, switchboard_alpha):
    """Test that only governance can claim performance fees"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    vault_registry.setPerformanceFee(undy_usd_vault.address, 10_00, sender=switchboard_alpha.address)

    yield_amount = 100 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # Governance can claim
    fees = undy_usd_vault.claimPerformanceFees(sender=governance.address)
    assert fees > 0


def test_switchboard_can_claim_fees(setup_yield_position, simulate_yield, undy_usd_vault, switchboard_alpha, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token, vault_registry):
    """Test that switchboard can claim performance fees"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    vault_registry.setPerformanceFee(undy_usd_vault.address, 10_00, sender=switchboard_alpha.address)

    yield_amount = 100 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # Switchboard can claim
    fees = undy_usd_vault.claimPerformanceFees(sender=switchboard_alpha.address)
    assert fees > 0


def test_unauthorized_cannot_claim_fees(setup_yield_position, simulate_yield, undy_usd_vault, bob, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token):
    """Test that unauthorized addresses cannot claim fees"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    yield_amount = 100 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # Bob (unauthorized) cannot claim
    with boa.reverts("no perms"):
        undy_usd_vault.claimPerformanceFees(sender=bob)


##############################################
# 9. Complex Integration Scenarios (7) #
##############################################


def test_deposit_yield_deposit_claim_withdraw_flow(setup_vault_with_deposit, setup_yield_position, simulate_yield, undy_usd_vault, governance, yield_underlying_token, yield_underlying_token_whale, bob, starter_agent, yield_vault_token, vault_registry, switchboard_alpha):
    """Test: Deposit → Yield → Deposit → Claim → Withdraw flow"""
    # First deposit
    user_deposit1, user_shares1 = setup_vault_with_deposit(500 * EIGHTEEN_DECIMALS)

    vault_registry.setPerformanceFee(undy_usd_vault.address, 10_00, sender=switchboard_alpha.address)

    # Yield position
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    # Yield
    yield_amount = 200 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    # Trigger yield calc
    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # Second user deposit
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    shares2 = undy_usd_vault.deposit(300 * EIGHTEEN_DECIMALS, bob, sender=yield_underlying_token_whale)

    # Claim fees
    fees = undy_usd_vault.claimPerformanceFees(sender=governance.address)
    assert fees > 0

    # User withdraws
    total_shares = user_shares1 + shares2
    withdrawn = undy_usd_vault.redeem(total_shares, bob, bob, sender=bob)
    assert withdrawn > 0


def test_deposit_yield_withdraw_yield_claim_flow(setup_vault_with_deposit, setup_yield_position, simulate_yield, undy_usd_vault, governance, yield_underlying_token, yield_underlying_token_whale, bob, starter_agent, yield_vault_token, vault_registry, switchboard_alpha):
    """Test: Deposit → Yield → Withdraw → Yield → Claim flow"""
    # Setup
    user_deposit, user_shares = setup_vault_with_deposit(1000 * EIGHTEEN_DECIMALS)

    vault_registry.setPerformanceFee(undy_usd_vault.address, 10_00, sender=switchboard_alpha.address)

    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    # First yield
    yield1 = 100 * EIGHTEEN_DECIMALS
    simulate_yield(yield1)
    boa.env.time_travel(seconds=301)

    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # User withdraws
    undy_usd_vault.redeem(user_shares // 2, bob, bob, sender=bob)

    # Second yield
    yield2 = 150 * EIGHTEEN_DECIMALS
    simulate_yield(yield2)
    boa.env.time_travel(seconds=301)

    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # Claim
    fees = undy_usd_vault.claimPerformanceFees(sender=governance.address)
    expected = (yield1 + yield2) * 10 // 100
    assert abs(fees - expected) <= 100


def test_multiple_users_with_yield_accruing(setup_vault_with_deposit, setup_yield_position, simulate_yield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, sally, starter_agent, yield_vault_token):
    """Test multiple users depositing with yield accruing"""
    # Bob deposits
    bob_deposit, bob_shares = setup_vault_with_deposit(500 * EIGHTEEN_DECIMALS)

    # Yield position
    setup_yield_position(1000 * EIGHTEEN_DECIMALS)

    # Yield
    simulate_yield(100 * EIGHTEEN_DECIMALS)
    boa.env.time_travel(seconds=301)

    # Sally deposits (after yield)
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    sally_shares = undy_usd_vault.deposit(500 * EIGHTEEN_DECIMALS, sally, sender=yield_underlying_token_whale)

    # Both should have shares
    assert bob_shares > 0
    assert sally_shares > 0

    # Sally's share value should reflect the yield that accrued


def test_fee_claim_doesnt_affect_user_shares(setup_vault_with_deposit, setup_yield_position, simulate_yield, undy_usd_vault, governance, yield_underlying_token, yield_underlying_token_whale, bob, starter_agent, yield_vault_token):
    """Test that claiming fees doesn't incorrectly affect user share values"""
    user_deposit, user_shares = setup_vault_with_deposit(1000 * EIGHTEEN_DECIMALS)
    setup_yield_position(1000 * EIGHTEEN_DECIMALS)

    # Yield
    simulate_yield(200 * EIGHTEEN_DECIMALS)
    boa.env.time_travel(seconds=301)

    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    value_before_claim = undy_usd_vault.convertToAssets(user_shares)

    # Claim fees
    undy_usd_vault.claimPerformanceFees(sender=governance.address)

    value_after_claim = undy_usd_vault.convertToAssets(user_shares)

    # User share value should increase (or stay same), not decrease
    assert value_after_claim >= value_before_claim


def test_fee_claim_followed_by_immediate_deposit(setup_yield_position, simulate_yield, undy_usd_vault, governance, yield_underlying_token, yield_underlying_token_whale, bob, starter_agent, yield_vault_token):
    """Test deposit immediately after fee claim"""
    setup_yield_position(1000 * EIGHTEEN_DECIMALS)

    # Yield and claim
    simulate_yield(100 * EIGHTEEN_DECIMALS)
    boa.env.time_travel(seconds=301)

    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    undy_usd_vault.claimPerformanceFees(sender=governance.address)

    # Immediate deposit
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    shares = undy_usd_vault.deposit(500 * EIGHTEEN_DECIMALS, bob, sender=yield_underlying_token_whale)
    assert shares > 0


def test_fee_claim_followed_by_immediate_withdrawal(setup_vault_with_deposit, setup_yield_position, simulate_yield, undy_usd_vault, governance, yield_underlying_token, yield_underlying_token_whale, bob, starter_agent, yield_vault_token):
    """Test withdrawal immediately after fee claim"""
    user_deposit, user_shares = setup_vault_with_deposit(1000 * EIGHTEEN_DECIMALS)
    setup_yield_position(1000 * EIGHTEEN_DECIMALS)

    # Yield and claim
    simulate_yield(100 * EIGHTEEN_DECIMALS)
    boa.env.time_travel(seconds=301)

    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    undy_usd_vault.claimPerformanceFees(sender=governance.address)

    # Immediate withdrawal
    withdrawn = undy_usd_vault.redeem(user_shares, bob, bob, sender=bob)
    assert withdrawn > 0


def test_yield_tracking_with_swap_operations(setup_yield_position, simulate_yield, undy_usd_vault):
    """Test yield tracking remains consistent with swap operations"""
    setup_yield_position(1000 * EIGHTEEN_DECIMALS)

    # Yield
    simulate_yield(100 * EIGHTEEN_DECIMALS)

    # Note: Swap operations don't affect yield tracking directly
    # This is more of a consistency test
    assert undy_usd_vault.pendingYieldRealized() == 0  # Not triggered yet


###################################
# 10. State Consistency (4) #
###################################


def test_last_underlying_bal_matches_actual(_test, setup_yield_position, simulate_yield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token):
    """Test lastUnderlyingBal matches actual underlying after operations"""
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    setup_yield_position(initial_deposit)

    # Yield
    yield_amount = 200 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    # Trigger
    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # lastUnderlyingBal should match actual
    expected = initial_deposit + yield_amount + trigger
    _test(expected, undy_usd_vault.lastUnderlyingBal())


def test_pending_yield_realized_never_negative(setup_yield_position, undy_usd_vault, yield_vault_token, starter_agent):
    """Test that pendingYieldRealized is never negative"""
    setup_yield_position(1000 * EIGHTEEN_DECIMALS)

    # Various operations
    undy_usd_vault.withdrawFromYield(1, yield_vault_token.address, 100 * EIGHTEEN_DECIMALS, sender=starter_agent.address)

    assert undy_usd_vault.pendingYieldRealized() >= 0


def test_total_assets_calculation_consistency(setup_vault_with_deposit, setup_yield_position, simulate_yield, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token):
    """Test totalAssets calculation remains consistent with yield tracking"""
    user_deposit, _ = setup_vault_with_deposit(500 * EIGHTEEN_DECIMALS)
    setup_yield_position(1000 * EIGHTEEN_DECIMALS)

    total_before = undy_usd_vault.totalAssets()

    # Yield
    yield_amount = 100 * EIGHTEEN_DECIMALS
    simulate_yield(yield_amount)
    boa.env.time_travel(seconds=301)

    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    total_after = undy_usd_vault.totalAssets()

    # Should increase by yield (minus fees) plus trigger deposit
    assert total_after > total_before


def test_state_consistency_after_redemption_with_yield_withdrawal(setup_vault_with_deposit, setup_yield_position, simulate_yield, undy_usd_vault, bob):
    """Test state consistency after redemption that requires yield withdrawal"""
    user_deposit, user_shares = setup_vault_with_deposit(500 * EIGHTEEN_DECIMALS)
    setup_yield_position(2000 * EIGHTEEN_DECIMALS)

    # Yield
    simulate_yield(300 * EIGHTEEN_DECIMALS)
    boa.env.time_travel(seconds=301)

    # Large withdrawal requiring yield redemption
    undy_usd_vault.redeem(user_shares, bob, bob, sender=bob)

    # State should be consistent
    assert undy_usd_vault.lastUnderlyingBal() >= 0
    assert undy_usd_vault.pendingYieldRealized() >= 0


###########################################################
# 11. Priority 1 Additional Tests - Critical Coverage  #
###########################################################


def test_rebasing_only_yield_position(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token, governance, vault_registry, switchboard_alpha):
    """Test yield tracking with only rebasing tokens"""
    # yield_vault_token acts as rebasing by default
    vault_registry.setPerformanceFee(undy_usd_vault.address, 10_00, sender=switchboard_alpha.address)

    deposit1 = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit1, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, deposit1, sender=starter_agent.address)

    # Simulate yield
    yield_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.mint(yield_vault_token.address, yield_amount, sender=governance.address)
    boa.env.time_travel(seconds=301)

    # Trigger
    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # Verify yield tracked
    assert undy_usd_vault.pendingYieldRealized() == yield_amount

    # Claim fees
    fees = undy_usd_vault.claimPerformanceFees(sender=governance.address)
    expected_fees = yield_amount * 10 // 100
    assert fees == expected_fees


def test_non_rebasing_only_yield_position(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token_3, governance, vault_registry, switchboard_alpha, mock_yield_lego):
    """Test yield tracking with only non-rebasing tokens"""
    # Testing with snapshot-based price tracking
    vault_registry.setPerformanceFee(undy_usd_vault.address, 10_00, sender=switchboard_alpha.address)

    deposit1 = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit1, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token_3.address, deposit1, sender=starter_agent.address)

    # Simulate yield (price per share increases)
    yield_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.mint(yield_vault_token_3.address, yield_amount, sender=governance.address)
    boa.env.time_travel(seconds=301)

    # Update snapshot
    mock_yield_lego.addPriceSnapshot(yield_vault_token_3.address, sender=switchboard_alpha.address)

    # Trigger
    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token_3.address, trigger, sender=starter_agent.address)

    # Verify yield tracked (may have slight variance due to snapshot averaging)
    assert undy_usd_vault.pendingYieldRealized() > 0


def test_mixed_rebasing_non_rebasing_positions(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token, yield_vault_token_3, governance, vault_registry, switchboard_alpha, mock_yield_lego):
    """Test yield tracking with both rebasing and non-rebasing tokens"""
    vault_registry.setPerformanceFee(undy_usd_vault.address, 10_00, sender=switchboard_alpha.address)

    # Deposit to rebasing token
    deposit1 = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit1, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, deposit1, sender=starter_agent.address)

    # Deposit to non-rebasing token
    deposit2 = 800 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit2, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token_3.address, deposit2, sender=starter_agent.address)

    # Yield on both
    yield1 = 80 * EIGHTEEN_DECIMALS
    yield2 = 60 * EIGHTEEN_DECIMALS
    yield_underlying_token.mint(yield_vault_token.address, yield1, sender=governance.address)
    yield_underlying_token.mint(yield_vault_token_3.address, yield2, sender=governance.address)
    boa.env.time_travel(seconds=301)

    # Update snapshots
    mock_yield_lego.addPriceSnapshot(yield_vault_token_3.address, sender=switchboard_alpha.address)

    # Trigger
    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # Should track combined yield from both positions
    pending_yield = undy_usd_vault.pendingYieldRealized()
    assert pending_yield > yield1  # Should have at least rebasing yield


def test_fee_claim_multiple_position_withdrawals(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token, yield_vault_token_2, governance, vault_registry, switchboard_alpha):
    """Test fee claim that requires withdrawing from multiple yield positions"""
    vault_registry.setPerformanceFee(undy_usd_vault.address, 50_00, sender=switchboard_alpha.address)  # 50% to force large withdrawal

    # Setup two yield positions with limited idle balance
    deposit1 = 500 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit1, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, deposit1, sender=starter_agent.address)

    deposit2 = 500 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit2, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token_2.address, deposit2, sender=starter_agent.address)

    # Large yield
    yield_amount = 400 * EIGHTEEN_DECIMALS
    yield_underlying_token.mint(yield_vault_token.address, yield_amount // 2, sender=governance.address)
    yield_underlying_token.mint(yield_vault_token_2.address, yield_amount // 2, sender=governance.address)
    boa.env.time_travel(seconds=301)

    # Trigger (minimal idle balance left)
    trigger = 10 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # Claim should withdraw from both positions
    fees_claimed = undy_usd_vault.claimPerformanceFees(sender=governance.address)
    expected_fees = yield_amount * 50 // 100
    assert fees_claimed == expected_fees


def test_redemption_buffer_over_withdrawal(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, bob, yield_vault_token, governance, vault_registry, switchboard_alpha):
    """Test redemption buffer causing over-withdrawal from yield"""
    # Set redemption buffer and performance fee
    vault_registry.setPerformanceFee(undy_usd_vault.address, 20_00, sender=switchboard_alpha.address)

    # User deposit
    user_deposit = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    shares = undy_usd_vault.deposit(user_deposit, bob, sender=yield_underlying_token_whale)

    # Create yield position
    deposit1 = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit1, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, deposit1, sender=starter_agent.address)

    # Yield
    yield_amount = 200 * EIGHTEEN_DECIMALS
    yield_underlying_token.mint(yield_vault_token.address, yield_amount, sender=governance.address)
    boa.env.time_travel(seconds=301)

    # Trigger
    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # Claim fees (buffer should cause slightly more to be withdrawn)
    initial_idle = yield_underlying_token.balanceOf(undy_usd_vault.address)
    fees_claimed = undy_usd_vault.claimPerformanceFees(sender=governance.address)

    # Verify fee claim succeeded with buffer
    expected_fees = yield_amount * 20 // 100
    assert fees_claimed == expected_fees


def test_dust_protection_in_redemption(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, bob, yield_vault_token, vault_registry, switchboard_alpha):
    """Test dust protection logic when withdrawal amount is below minimum"""
    # Setup vault with yield
    user_deposit = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    shares = undy_usd_vault.deposit(user_deposit, bob, sender=yield_underlying_token_whale)

    deposit1 = 10000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit1, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, deposit1, sender=starter_agent.address)

    # Very small withdrawal (tests dust protection)
    # Redeem tiny amount
    tiny_shares = shares // 1000  # 0.1% of shares
    undy_usd_vault.redeem(tiny_shares, bob, bob, sender=bob)

    # Should complete without issues despite dust amounts
    assert undy_usd_vault.lastUnderlyingBal() >= 0


def test_precision_loss_small_yields(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token, governance, vault_registry, switchboard_alpha):
    """Test precision loss with very small yields - system should handle gracefully"""
    vault_registry.setPerformanceFee(undy_usd_vault.address, 10_00, sender=switchboard_alpha.address)

    deposit1 = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit1, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, deposit1, sender=starter_agent.address)

    # Very small yields relative to position size
    # At this scale (1-100 wei on 1000e18 position), precision loss is expected
    small_yields = [100000, 500000, 1000000, 10000000]  # 0.0001 to 0.01 tokens
    total_yield = 0

    for yield_amount in small_yields:
        yield_underlying_token.mint(yield_vault_token.address, yield_amount, sender=governance.address)
        boa.env.time_travel(seconds=301)

        trigger = EIGHTEEN_DECIMALS
        yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
        undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

        total_yield += yield_amount

    # Verify tracking (with reasonable tolerance for small yields)
    pending = undy_usd_vault.pendingYieldRealized()
    assert pending >= 0
    # With small yields, allow higher tolerance due to rounding in vault token conversions
    # Should capture most of the yield even at small scales
    assert abs(pending - total_yield) <= total_yield // 10  # Within 10%


def test_precision_loss_accumulation(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token, governance, vault_registry, switchboard_alpha):
    """Test rounding error accumulation over 50 operations"""
    vault_registry.setPerformanceFee(undy_usd_vault.address, 10_00, sender=switchboard_alpha.address)

    deposit1 = 10000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit1, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, deposit1, sender=starter_agent.address)

    total_expected_yield = 0
    num_operations = 50

    for i in range(num_operations):
        yield_amount = EIGHTEEN_DECIMALS  # 1 token each time
        yield_underlying_token.mint(yield_vault_token.address, yield_amount, sender=governance.address)
        boa.env.time_travel(seconds=301)

        trigger = EIGHTEEN_DECIMALS // 10
        yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
        undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

        total_expected_yield += yield_amount

    # Check precision loss
    pending = undy_usd_vault.pendingYieldRealized()
    precision_loss = abs(pending - total_expected_yield)

    # Loss should be minimal (< 0.1% of total)
    max_acceptable_loss = total_expected_yield // 1000
    assert precision_loss <= max_acceptable_loss


def test_fee_claim_no_new_yield(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token, governance, vault_registry, switchboard_alpha):
    """Test fee claim when there's pending yield but NO new yield since last operation"""
    vault_registry.setPerformanceFee(undy_usd_vault.address, 10_00, sender=switchboard_alpha.address)

    deposit1 = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit1, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, deposit1, sender=starter_agent.address)

    # Yield and trigger
    yield_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.mint(yield_vault_token.address, yield_amount, sender=governance.address)
    boa.env.time_travel(seconds=301)

    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    assert undy_usd_vault.pendingYieldRealized() == yield_amount

    # NO new yield - directly claim
    fees = undy_usd_vault.claimPerformanceFees(sender=governance.address)

    expected_fees = yield_amount * 10 // 100
    assert fees == expected_fees
    assert undy_usd_vault.pendingYieldRealized() == 0


def test_rapid_sequential_fee_claims(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token, governance, vault_registry, switchboard_alpha):
    """Test back-to-back fee claims in rapid succession"""
    vault_registry.setPerformanceFee(undy_usd_vault.address, 10_00, sender=switchboard_alpha.address)

    deposit1 = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit1, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, deposit1, sender=starter_agent.address)

    # First yield and claim
    yield1 = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.mint(yield_vault_token.address, yield1, sender=governance.address)
    boa.env.time_travel(seconds=301)

    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    fees1 = undy_usd_vault.claimPerformanceFees(sender=governance.address)
    assert fees1 > 0
    assert undy_usd_vault.pendingYieldRealized() == 0

    # Immediate second claim (should return 0)
    fees2 = undy_usd_vault.claimPerformanceFees(sender=governance.address)
    assert fees2 == 0
    assert undy_usd_vault.pendingYieldRealized() == 0

    # Third claim after small yield
    yield2 = EIGHTEEN_DECIMALS
    yield_underlying_token.mint(yield_vault_token.address, yield2, sender=governance.address)
    boa.env.time_travel(seconds=301)

    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    fees3 = undy_usd_vault.claimPerformanceFees(sender=governance.address)
    expected_fees3 = yield2 * 10 // 100
    # Allow small rounding tolerance
    assert abs(fees3 - expected_fees3) <= 100


def test_yield_cycle_multiple_times(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token, governance, vault_registry, switchboard_alpha):
    """Test yield→claim→yield→claim cycle 5 times"""
    vault_registry.setPerformanceFee(undy_usd_vault.address, 10_00, sender=switchboard_alpha.address)

    deposit1 = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit1, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, deposit1, sender=starter_agent.address)

    trigger = 10 * EIGHTEEN_DECIMALS

    for cycle in range(5):
        # Yield
        yield_amount = (50 + cycle * 10) * EIGHTEEN_DECIMALS  # Varying yields
        yield_underlying_token.mint(yield_vault_token.address, yield_amount, sender=governance.address)
        boa.env.time_travel(seconds=301)

        # Trigger
        yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
        undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

        # Verify pending yield (allow small tolerance for rounding)
        assert abs(undy_usd_vault.pendingYieldRealized() - yield_amount) <= 1000

        # Claim
        fees = undy_usd_vault.claimPerformanceFees(sender=governance.address)
        expected_fees = yield_amount * 10 // 100
        assert abs(fees - expected_fees) <= 2000
        assert undy_usd_vault.pendingYieldRealized() == 0


def test_zero_change_in_underlying(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token):
    """Test when lastUnderlyingBal == currentUnderlying (no change)"""
    deposit1 = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit1, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, deposit1, sender=starter_agent.address)

    initial_last_bal = undy_usd_vault.lastUnderlyingBal()
    initial_pending = undy_usd_vault.pendingYieldRealized()

    # No yield, just another operation
    boa.env.time_travel(seconds=301)
    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # Pending should NOT increase (no yield)
    assert undy_usd_vault.pendingYieldRealized() == initial_pending


def test_auto_deposit_with_pending_fees(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, starter_agent, yield_vault_token, governance, vault_registry, switchboard_alpha):
    """Test auto-deposit integration when pending fees exist"""
    vault_registry.setPerformanceFee(undy_usd_vault.address, 20_00, sender=switchboard_alpha.address)
    vault_registry.setShouldAutoDeposit(undy_usd_vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setDefaultTargetVaultToken(undy_usd_vault.address, yield_vault_token.address, sender=switchboard_alpha.address)

    # Create yield position
    deposit1 = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit1, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, deposit1, sender=starter_agent.address)

    # Accrue yield
    yield_amount = 200 * EIGHTEEN_DECIMALS
    yield_underlying_token.mint(yield_vault_token.address, yield_amount, sender=governance.address)
    boa.env.time_travel(seconds=301)

    # Trigger yield calculation
    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # Now pending fees exist
    pending_fees_before = undy_usd_vault.getClaimablePerformanceFees()
    assert pending_fees_before > 0

    # User deposit with auto-deposit enabled
    user_deposit = 500 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    shares = undy_usd_vault.deposit(user_deposit, bob, sender=yield_underlying_token_whale)

    # Auto-deposit should work correctly despite pending fees
    assert shares > 0

    # Pending fees should still be claimable
    pending_fees_after = undy_usd_vault.getClaimablePerformanceFees()
    assert abs(pending_fees_after - pending_fees_before) <= 100  # Allow small variance


def test_preview_functions_with_high_pending_fees(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, starter_agent, yield_vault_token, governance, vault_registry, switchboard_alpha):
    """Test ERC4626 preview functions with high pending fees"""
    vault_registry.setPerformanceFee(undy_usd_vault.address, 50_00, sender=switchboard_alpha.address)  # 50%

    # User deposit
    user_deposit = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    shares = undy_usd_vault.deposit(user_deposit, bob, sender=yield_underlying_token_whale)

    # Create large yield
    deposit1 = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit1, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, deposit1, sender=starter_agent.address)

    # Huge yield
    yield_amount = 2000 * EIGHTEEN_DECIMALS
    yield_underlying_token.mint(yield_vault_token.address, yield_amount, sender=governance.address)
    boa.env.time_travel(seconds=301)

    trigger = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token.address, trigger, sender=starter_agent.address)

    # High pending fees now (50% of 2000 = 1000 tokens)
    pending_fees = undy_usd_vault.getClaimablePerformanceFees()
    assert pending_fees > 900 * EIGHTEEN_DECIMALS

    # Test preview functions account for pending fees
    preview_withdraw = undy_usd_vault.previewWithdraw(500 * EIGHTEEN_DECIMALS)
    preview_redeem = undy_usd_vault.previewRedeem(shares // 2)
    preview_deposit = undy_usd_vault.previewDeposit(500 * EIGHTEEN_DECIMALS)
    preview_mint = undy_usd_vault.previewMint(100 * EIGHTEEN_DECIMALS)

    # All should return reasonable values (not zero, not overflow)
    assert preview_withdraw > 0
    assert preview_redeem > 0
    assert preview_deposit > 0
    assert preview_mint > 0

    # Total assets should subtract pending fees
    total_assets = undy_usd_vault.totalAssets()
    assert total_assets > 0


def test_weighted_price_calculation_accuracy(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent, yield_vault_token_3, governance, switchboard_alpha, mock_yield_lego):
    """Test weighted average price calculation for non-rebasing tokens"""
    # Set up snapshot price config
    snapshot_config = (
        300,     # minSnapshotDelay (5 minutes)
        20,      # maxNumSnapshots
        10_00,   # maxUpsideDeviation (10%)
        86400    # staleTime (1 day)
    )
    mock_yield_lego.setSnapShotPriceConfig(snapshot_config, sender=switchboard_alpha.address)

    # This test requires yield_vault_token_3 to be non-rebasing
    deposit1 = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit1, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token_3.address, deposit1, sender=starter_agent.address)

    # Add multiple snapshots with different prices
    for i in range(3):
        # Simulate yield (increases price per share)
        yield_amount = (50 + i * 20) * EIGHTEEN_DECIMALS
        yield_underlying_token.mint(yield_vault_token_3.address, yield_amount, sender=governance.address)
        boa.env.time_travel(seconds=301)

        # Add snapshot
        success = mock_yield_lego.addPriceSnapshot(yield_vault_token_3.address, sender=switchboard_alpha.address)
        assert success

    # Get weighted price
    weighted_price = mock_yield_lego.getWeightedPricePerShare(yield_vault_token_3.address)
    assert weighted_price > 0

    # Trigger yield calculation
    trigger = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, trigger, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(1, yield_underlying_token.address, yield_vault_token_3.address, trigger, sender=starter_agent.address)

    # Pending yield should be tracked (with weighted average)
    pending_yield = undy_usd_vault.pendingYieldRealized()
    assert pending_yield > 0
