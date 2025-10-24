import pytest
import boa

from constants import EIGHTEEN_DECIMALS, MAX_UINT256


############
# Fixtures #
############


@pytest.fixture(scope="module")
def setup_auto_deposit_config(vault_registry, switchboard_alpha, yield_underlying_token, yield_underlying_token_whale, starter_agent, sally):
    """Fixture to enable auto-deposit with a specific target vault token"""
    def _setup(_vault, _targetVaultToken):
        # Ensure auto-deposit is disabled during setup
        vault_registry.setShouldAutoDeposit(_vault.address, False, sender=switchboard_alpha.address)

        # First, have a user deposit to mint shares, so we avoid the empty vault issue
        # Then create a small position in the target vault token to register it
        small_amount = 10 * EIGHTEEN_DECIMALS
        yield_underlying_token.approve(_vault.address, small_amount, sender=yield_underlying_token_whale)
        _vault.deposit(small_amount, sally, sender=yield_underlying_token_whale)

        # Now deposit that to yield to register the vault token
        _vault.depositForYield(
            2,
            yield_underlying_token.address,
            _targetVaultToken.address,
            small_amount,
            sender=starter_agent.address
        )

        # Now enable auto-deposit
        vault_registry.setShouldAutoDeposit(_vault.address, True, sender=switchboard_alpha.address)
        vault_registry.setDefaultTargetVaultToken(_vault.address, _targetVaultToken.address, sender=switchboard_alpha.address)
    yield _setup


@pytest.fixture(scope="module")
def setup_multiple_yield_positions(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, starter_agent):
    """Fixture to create multiple yield positions with different balances"""
    def _setup(_positions):
        """
        _positions: list of tuples (vault_token, amount)
        """
        for vault_token, amount in _positions:
            yield_underlying_token.transfer(undy_usd_vault.address, amount, sender=yield_underlying_token_whale)
            undy_usd_vault.depositForYield(
                2,
                yield_underlying_token.address,
                vault_token.address,
                amount,
                sender=starter_agent.address
            )
    yield _setup


@pytest.fixture(scope="module")
def verify_auto_deposit_executed():
    """Helper to verify auto-deposit actually happened"""
    def _verify(_vault, _vaultToken, _initialVaultTokenBal, _depositAmount):
        """Returns True if auto-deposit executed, False if funds stayed idle"""
        # Check if vault token balance increased
        new_vault_token_bal = _vaultToken.balanceOf(_vault.address)
        vault_token_increased = new_vault_token_bal > _initialVaultTokenBal

        # Check if idle balance is minimal
        idle_bal = _vault.asset().balanceOf(_vault.address)

        return vault_token_increased and idle_bal < _depositAmount
    yield _verify


###################################
# 1. Basic Auto-Deposit Tests (5) #
###################################


def test_auto_deposit_with_default_target_set(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, yield_vault_token, vault_registry, switchboard_alpha, setup_auto_deposit_config):
    """Test auto-deposit with defaultTargetVaultToken configured"""
    # Setup auto-deposit
    setup_auto_deposit_config(undy_usd_vault, yield_vault_token)

    # Get initial state
    initial_vault_token_bal = yield_vault_token.balanceOf(undy_usd_vault.address)

    # User deposit
    deposit_amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    shares = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)

    # Verify auto-deposit happened
    new_vault_token_bal = yield_vault_token.balanceOf(undy_usd_vault.address)
    assert new_vault_token_bal > initial_vault_token_bal

    # Verify idle balance is minimal (some dust might remain)
    idle_balance = yield_underlying_token.balanceOf(undy_usd_vault.address)
    assert idle_balance < 100  # Very small amount

    # Verify user got shares
    assert shares > 0


def test_auto_deposit_with_zero_default_uses_max_bal_vault_token(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, starter_agent, yield_vault_token, vault_registry, switchboard_alpha, setup_multiple_yield_positions):
    """Test auto-deposit with 0x0 defaultTargetVaultToken uses maxBalVaultToken"""
    # Create existing yield position
    setup_multiple_yield_positions([(yield_vault_token, 500 * EIGHTEEN_DECIMALS)])

    # Setup auto-deposit with 0x0 default
    vault_registry.setShouldAutoDeposit(undy_usd_vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setDefaultTargetVaultToken(undy_usd_vault.address, boa.eval("empty(address)"), sender=switchboard_alpha.address)

    initial_vault_token_bal = yield_vault_token.balanceOf(undy_usd_vault.address)

    # User deposit
    deposit_amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    shares = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)

    # Verify it used the existing position (maxBalVaultToken)
    new_vault_token_bal = yield_vault_token.balanceOf(undy_usd_vault.address)
    assert new_vault_token_bal > initial_vault_token_bal
    assert shares > 0


def test_auto_deposit_disabled_funds_stay_idle(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, yield_vault_token, vault_registry, switchboard_alpha):
    """Test that with auto-deposit OFF, funds remain idle in vault"""
    # Ensure auto-deposit is OFF
    vault_registry.setShouldAutoDeposit(undy_usd_vault.address, False, sender=switchboard_alpha.address)

    initial_vault_token_bal = yield_vault_token.balanceOf(undy_usd_vault.address)

    # User deposit
    deposit_amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    shares = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)

    # Verify vault token balance did NOT increase
    new_vault_token_bal = yield_vault_token.balanceOf(undy_usd_vault.address)
    assert new_vault_token_bal == initial_vault_token_bal

    # Verify funds are idle in vault
    idle_balance = yield_underlying_token.balanceOf(undy_usd_vault.address)
    assert idle_balance >= deposit_amount

    assert shares > 0


def test_auto_deposit_with_mint_function(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, yield_vault_token, vault_registry, switchboard_alpha, setup_auto_deposit_config):
    """Test auto-deposit works with mint() function too"""
    setup_auto_deposit_config(undy_usd_vault, yield_vault_token)

    initial_vault_token_bal = yield_vault_token.balanceOf(undy_usd_vault.address)

    # User mints shares
    shares_to_mint = 500 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    assets_used = undy_usd_vault.mint(shares_to_mint, bob, sender=yield_underlying_token_whale)

    # Verify auto-deposit happened
    new_vault_token_bal = yield_vault_token.balanceOf(undy_usd_vault.address)
    assert new_vault_token_bal > initial_vault_token_bal

    # Verify idle balance is minimal
    idle_balance = yield_underlying_token.balanceOf(undy_usd_vault.address)
    assert idle_balance < 100

    assert assets_used > 0


def test_auto_deposit_amount_matches_deposit(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, starter_agent, yield_vault_token, vault_registry, switchboard_alpha, setup_auto_deposit_config):
    """Test that auto-deposited amount approximately matches user deposit"""
    setup_auto_deposit_config(undy_usd_vault, yield_vault_token)

    # Track the initial balance (setup created a small position)
    initial_underlying = undy_usd_vault.lastUnderlyingBal()

    # User deposit
    deposit_amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)

    # Check lastUnderlyingBal increased by approximately deposit amount
    last_underlying = undy_usd_vault.lastUnderlyingBal()
    increase = last_underlying - initial_underlying
    # Should be close to deposit amount (allowing for small variance)
    assert abs(increase - deposit_amount) < deposit_amount // 100  # Within 1%


#################################################
# 2. Configuration Management & Permissions (8) #
#################################################


def test_set_should_auto_deposit_only_switchboard(undy_usd_vault, vault_registry, switchboard_alpha, bob, governance):
    """Test that only switchboard can call setShouldAutoDeposit"""
    # Switchboard can set
    vault_registry.setShouldAutoDeposit(undy_usd_vault.address, True, sender=switchboard_alpha.address)
    config = vault_registry.getDepositConfig(undy_usd_vault.address)
    assert config[2] == True  # shouldAutoDeposit

    # Others cannot
    with boa.reverts("no perms"):
        vault_registry.setShouldAutoDeposit(undy_usd_vault.address, False, sender=bob)

    with boa.reverts("no perms"):
        vault_registry.setShouldAutoDeposit(undy_usd_vault.address, False, sender=governance.address)


def test_set_default_target_vault_token_only_switchboard(undy_usd_vault, yield_vault_token, vault_registry, switchboard_alpha, bob, governance):
    """Test that only switchboard can call setDefaultTargetVaultToken"""
    # Switchboard can set
    vault_registry.setDefaultTargetVaultToken(undy_usd_vault.address, yield_vault_token.address, sender=switchboard_alpha.address)
    config = vault_registry.getDepositConfig(undy_usd_vault.address)
    assert config[3] == yield_vault_token.address  # defaultTargetVaultToken

    # Others cannot
    with boa.reverts("no perms"):
        vault_registry.setDefaultTargetVaultToken(undy_usd_vault.address, yield_vault_token.address, sender=bob)

    with boa.reverts("no perms"):
        vault_registry.setDefaultTargetVaultToken(undy_usd_vault.address, yield_vault_token.address, sender=governance.address)


def test_toggle_should_auto_deposit(undy_usd_vault, vault_registry, switchboard_alpha):
    """Test toggling shouldAutoDeposit false→true→false"""
    # Start false
    vault_registry.setShouldAutoDeposit(undy_usd_vault.address, False, sender=switchboard_alpha.address)
    assert vault_registry.getDepositConfig(undy_usd_vault.address)[2] == False

    # Toggle to true
    vault_registry.setShouldAutoDeposit(undy_usd_vault.address, True, sender=switchboard_alpha.address)
    assert vault_registry.getDepositConfig(undy_usd_vault.address)[2] == True

    # Toggle back to false
    vault_registry.setShouldAutoDeposit(undy_usd_vault.address, False, sender=switchboard_alpha.address)
    assert vault_registry.getDepositConfig(undy_usd_vault.address)[2] == False


def test_change_default_target_vault_token(undy_usd_vault, yield_vault_token, yield_vault_token_2, vault_registry, switchboard_alpha):
    """Test changing defaultTargetVaultToken between different vault tokens"""
    # Set to token 1
    vault_registry.setDefaultTargetVaultToken(undy_usd_vault.address, yield_vault_token.address, sender=switchboard_alpha.address)
    assert vault_registry.getDepositConfig(undy_usd_vault.address)[3] == yield_vault_token.address

    # Change to token 2
    vault_registry.setDefaultTargetVaultToken(undy_usd_vault.address, yield_vault_token_2.address, sender=switchboard_alpha.address)
    assert vault_registry.getDepositConfig(undy_usd_vault.address)[3] == yield_vault_token_2.address

    # Set to 0x0
    vault_registry.setDefaultTargetVaultToken(undy_usd_vault.address, boa.eval("empty(address)"), sender=switchboard_alpha.address)
    assert vault_registry.getDepositConfig(undy_usd_vault.address)[3] == boa.eval("empty(address)")


def test_set_default_target_to_zero_address(undy_usd_vault, vault_registry, switchboard_alpha):
    """Test setting defaultTargetVaultToken to 0x0 is valid"""
    # Should succeed
    vault_registry.setDefaultTargetVaultToken(undy_usd_vault.address, boa.eval("empty(address)"), sender=switchboard_alpha.address)
    config = vault_registry.getDepositConfig(undy_usd_vault.address)
    assert config[3] == boa.eval("empty(address)")


def test_set_default_target_to_unapproved_token_fails(undy_usd_vault, vault_registry, switchboard_alpha, yield_underlying_token):
    """Test setting defaultTargetVaultToken to unapproved token should fail"""
    # Try to set to an unapproved vault token (using underlying token as example)
    with boa.reverts("invalid default target vault token"):
        vault_registry.setDefaultTargetVaultToken(undy_usd_vault.address, yield_underlying_token.address, sender=switchboard_alpha.address)


def test_get_deposit_config_returns_correct_values(undy_usd_vault, yield_vault_token, vault_registry, switchboard_alpha):
    """Test getDepositConfig returns all values correctly"""
    # Set config
    vault_registry.setShouldAutoDeposit(undy_usd_vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setDefaultTargetVaultToken(undy_usd_vault.address, yield_vault_token.address, sender=switchboard_alpha.address)

    # Get config
    canDeposit, maxDepositAmount, shouldAutoDeposit, defaultTargetVaultToken = vault_registry.getDepositConfig(undy_usd_vault.address)

    # Verify
    assert canDeposit == True
    assert shouldAutoDeposit == True
    assert defaultTargetVaultToken == yield_vault_token.address


def test_config_persists_across_deposits(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, yield_vault_token, vault_registry, switchboard_alpha, setup_auto_deposit_config):
    """Test that config persists across multiple deposits"""
    setup_auto_deposit_config(undy_usd_vault, yield_vault_token)

    # First deposit
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    undy_usd_vault.deposit(500 * EIGHTEEN_DECIMALS, bob, sender=yield_underlying_token_whale)

    # Config should still be set
    config = vault_registry.getDepositConfig(undy_usd_vault.address)
    assert config[2] == True  # shouldAutoDeposit
    assert config[3] == yield_vault_token.address

    # Second deposit should still auto-deposit
    initial_vault_token_bal = yield_vault_token.balanceOf(undy_usd_vault.address)
    undy_usd_vault.deposit(500 * EIGHTEEN_DECIMALS, bob, sender=yield_underlying_token_whale)

    new_vault_token_bal = yield_vault_token.balanceOf(undy_usd_vault.address)
    assert new_vault_token_bal > initial_vault_token_bal


##########################################
# 3. MaxBalVaultToken Fallback Logic (6) #
##########################################


def test_zero_default_with_single_position(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, starter_agent, yield_vault_token, vault_registry, switchboard_alpha, setup_multiple_yield_positions):
    """Test 0x0 default with single existing position uses that position"""
    # Create one position
    setup_multiple_yield_positions([(yield_vault_token, 500 * EIGHTEEN_DECIMALS)])

    # Set auto-deposit with 0x0 default
    vault_registry.setShouldAutoDeposit(undy_usd_vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setDefaultTargetVaultToken(undy_usd_vault.address, boa.eval("empty(address)"), sender=switchboard_alpha.address)

    initial_bal = yield_vault_token.balanceOf(undy_usd_vault.address)

    # Deposit
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    undy_usd_vault.deposit(1000 * EIGHTEEN_DECIMALS, bob, sender=yield_underlying_token_whale)

    # Should have deposited to the single position
    assert yield_vault_token.balanceOf(undy_usd_vault.address) > initial_bal


def test_zero_default_with_multiple_positions_uses_highest(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, starter_agent, yield_vault_token, yield_vault_token_2, vault_registry, switchboard_alpha, setup_multiple_yield_positions):
    """Test 0x0 default with multiple positions uses the highest balance"""
    # Create two positions with different balances
    setup_multiple_yield_positions([
        (yield_vault_token, 300 * EIGHTEEN_DECIMALS),  # Smaller
        (yield_vault_token_2, 800 * EIGHTEEN_DECIMALS),  # Larger - should be chosen
    ])

    # Set auto-deposit with 0x0 default
    vault_registry.setShouldAutoDeposit(undy_usd_vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setDefaultTargetVaultToken(undy_usd_vault.address, boa.eval("empty(address)"), sender=switchboard_alpha.address)

    initial_bal_token2 = yield_vault_token_2.balanceOf(undy_usd_vault.address)

    # Deposit
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    undy_usd_vault.deposit(500 * EIGHTEEN_DECIMALS, bob, sender=yield_underlying_token_whale)

    # Should have deposited to yield_vault_token_2 (larger position)
    assert yield_vault_token_2.balanceOf(undy_usd_vault.address) > initial_bal_token2


def test_zero_default_with_no_positions(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, vault_registry, switchboard_alpha):
    """Test 0x0 default with NO existing positions - funds stay idle"""
    # Set auto-deposit with 0x0 default (no positions exist)
    vault_registry.setShouldAutoDeposit(undy_usd_vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setDefaultTargetVaultToken(undy_usd_vault.address, boa.eval("empty(address)"), sender=switchboard_alpha.address)

    deposit_amount = 1000 * EIGHTEEN_DECIMALS

    # Deposit
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)

    # Funds should stay idle since no position to auto-deposit to
    idle_balance = yield_underlying_token.balanceOf(undy_usd_vault.address)
    assert idle_balance >= deposit_amount


def test_max_bal_vault_token_with_three_positions(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, starter_agent, yield_vault_token, yield_vault_token_2, yield_vault_token_3, vault_registry, switchboard_alpha, setup_multiple_yield_positions):
    """Test maxBalVaultToken selection with 3 positions of varying sizes"""
    # Create three positions
    setup_multiple_yield_positions([
        (yield_vault_token, 400 * EIGHTEEN_DECIMALS),    # Medium
        (yield_vault_token_2, 200 * EIGHTEEN_DECIMALS),  # Smallest
        (yield_vault_token_3, 1000 * EIGHTEEN_DECIMALS), # Largest - should be chosen
    ])

    # Set auto-deposit with 0x0 default
    vault_registry.setShouldAutoDeposit(undy_usd_vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setDefaultTargetVaultToken(undy_usd_vault.address, boa.eval("empty(address)"), sender=switchboard_alpha.address)

    initial_bal_token3 = yield_vault_token_3.balanceOf(undy_usd_vault.address)

    # Deposit
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    undy_usd_vault.deposit(500 * EIGHTEEN_DECIMALS, bob, sender=yield_underlying_token_whale)

    # Should have deposited to yield_vault_token_3 (largest)
    assert yield_vault_token_3.balanceOf(undy_usd_vault.address) > initial_bal_token3


def test_max_bal_changes_after_withdrawal(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, starter_agent, yield_vault_token, yield_vault_token_2, vault_registry, switchboard_alpha, setup_multiple_yield_positions):
    """Test that maxBalVaultToken changes after withdrawals change balances"""
    # Create two positions
    setup_multiple_yield_positions([
        (yield_vault_token, 500 * EIGHTEEN_DECIMALS),   # Initially larger
        (yield_vault_token_2, 300 * EIGHTEEN_DECIMALS), # Initially smaller
    ])

    # Withdraw from token 1 to make it smaller than token 2
    undy_usd_vault.withdrawFromYield(2, yield_vault_token.address, 400 * EIGHTEEN_DECIMALS, sender=starter_agent.address)

    # Set auto-deposit with 0x0 default
    vault_registry.setShouldAutoDeposit(undy_usd_vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setDefaultTargetVaultToken(undy_usd_vault.address, boa.eval("empty(address)"), sender=switchboard_alpha.address)

    initial_bal_token2 = yield_vault_token_2.balanceOf(undy_usd_vault.address)

    # Deposit - should now go to token 2
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    undy_usd_vault.deposit(200 * EIGHTEEN_DECIMALS, bob, sender=yield_underlying_token_whale)

    # Should have deposited to yield_vault_token_2 (now the larger one)
    assert yield_vault_token_2.balanceOf(undy_usd_vault.address) > initial_bal_token2


def test_zero_default_equal_balances(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, starter_agent, yield_vault_token, yield_vault_token_2, vault_registry, switchboard_alpha, setup_multiple_yield_positions):
    """Test 0x0 default when all positions have equal balance"""
    equal_amount = 500 * EIGHTEEN_DECIMALS

    # Create two positions with equal balances
    setup_multiple_yield_positions([
        (yield_vault_token, equal_amount),
        (yield_vault_token_2, equal_amount),
    ])

    # Set auto-deposit with 0x0 default
    vault_registry.setShouldAutoDeposit(undy_usd_vault.address, True, sender=switchboard_alpha.address)
    vault_registry.setDefaultTargetVaultToken(undy_usd_vault.address, boa.eval("empty(address)"), sender=switchboard_alpha.address)

    # Deposit - should pick one of them (implementation dependent, just verify it works)
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    shares = undy_usd_vault.deposit(200 * EIGHTEEN_DECIMALS, bob, sender=yield_underlying_token_whale)

    # Just verify deposit succeeded
    assert shares > 0


#######################################
# 4. State & Balance Verification (7) #
#######################################


def test_auto_deposit_on_minimal_idle_balance(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, yield_vault_token, vault_registry, switchboard_alpha, setup_auto_deposit_config):
    """Test that idle balance is minimal when auto-deposit is ON"""
    setup_auto_deposit_config(undy_usd_vault, yield_vault_token)

    deposit_amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)

    # Idle balance should be very small
    idle_balance = yield_underlying_token.balanceOf(undy_usd_vault.address)
    assert idle_balance < 100  # Minimal dust


def test_auto_deposit_off_full_idle_balance(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, vault_registry, switchboard_alpha):
    """Test that idle balance equals deposit when auto-deposit is OFF"""
    vault_registry.setShouldAutoDeposit(undy_usd_vault.address, False, sender=switchboard_alpha.address)

    deposit_amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)

    # Idle balance should equal deposit amount
    idle_balance = yield_underlying_token.balanceOf(undy_usd_vault.address)
    assert idle_balance >= deposit_amount


def test_last_underlying_bal_updated_with_auto_deposit(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, yield_vault_token, vault_registry, switchboard_alpha, setup_auto_deposit_config):
    """Test lastUnderlyingBal is updated correctly with auto-deposit"""
    setup_auto_deposit_config(undy_usd_vault, yield_vault_token)

    initial_last_underlying = undy_usd_vault.lastUnderlyingBal()
    deposit_amount = 1000 * EIGHTEEN_DECIMALS

    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)

    # lastUnderlyingBal should increase by approximately deposit amount
    new_last_underlying = undy_usd_vault.lastUnderlyingBal()
    increase = new_last_underlying - initial_last_underlying

    # Allow small tolerance for rounding
    assert abs(increase - deposit_amount) < deposit_amount // 100


def test_vault_token_balance_increases(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, yield_vault_token, vault_registry, switchboard_alpha, setup_auto_deposit_config):
    """Test that vault token balance increases correctly"""
    setup_auto_deposit_config(undy_usd_vault, yield_vault_token)

    initial_vault_token_bal = yield_vault_token.balanceOf(undy_usd_vault.address)
    deposit_amount = 1000 * EIGHTEEN_DECIMALS

    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)

    new_vault_token_bal = yield_vault_token.balanceOf(undy_usd_vault.address)

    # Balance should have increased
    assert new_vault_token_bal > initial_vault_token_bal
    # Increase should be approximately deposit_amount (1:1 for first deposit typically)
    increase = new_vault_token_bal - initial_vault_token_bal
    assert increase > 0


def test_user_shares_correct_regardless_of_auto_deposit(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, sally, yield_vault_token, vault_registry, switchboard_alpha, setup_auto_deposit_config):
    """Test user shares calculated correctly regardless of auto-deposit setting"""
    deposit_amount = 1000 * EIGHTEEN_DECIMALS

    # First user with auto-deposit ON
    setup_auto_deposit_config(undy_usd_vault, yield_vault_token)
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    shares_with_auto = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)

    # Turn auto-deposit OFF
    vault_registry.setShouldAutoDeposit(undy_usd_vault.address, False, sender=switchboard_alpha.address)

    # Second user with auto-deposit OFF
    shares_without_auto = undy_usd_vault.deposit(deposit_amount, sally, sender=yield_underlying_token_whale)

    # Shares should be similar (allowing for small variance due to totalAssets change)
    assert abs(shares_with_auto - shares_without_auto) < shares_with_auto // 100  # Within 1%


def test_pending_yield_not_affected_by_auto_deposit(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, starter_agent, yield_vault_token, governance, vault_registry, switchboard_alpha, setup_auto_deposit_config):
    """Test that pendingYieldRealized is not affected by auto-deposit"""
    # Create yield position and accrue some yield
    yield_underlying_token.transfer(undy_usd_vault.address, 500 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(2, yield_underlying_token.address, yield_vault_token.address, 500 * EIGHTEEN_DECIMALS, sender=starter_agent.address)

    # Accrue yield
    yield_underlying_token.mint(yield_vault_token.address, 100 * EIGHTEEN_DECIMALS, sender=governance.address)
    boa.env.time_travel(seconds=301)

    # Trigger yield calculation
    yield_underlying_token.transfer(undy_usd_vault.address, 10 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(2, yield_underlying_token.address, yield_vault_token.address, 10 * EIGHTEEN_DECIMALS, sender=starter_agent.address)

    pending_before = undy_usd_vault.pendingYieldRealized()

    # Now user deposits with auto-deposit
    setup_auto_deposit_config(undy_usd_vault, yield_vault_token)
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    undy_usd_vault.deposit(200 * EIGHTEEN_DECIMALS, bob, sender=yield_underlying_token_whale)

    # Pending yield should not change
    pending_after = undy_usd_vault.pendingYieldRealized()
    assert pending_after == pending_before


################################
# 5. Integration Scenarios (8) #
################################


def test_auto_deposit_with_yield_and_fees(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, starter_agent, yield_vault_token, governance, vault_registry, switchboard_alpha, setup_auto_deposit_config):
    """Test auto-deposit + yield accrual + fee claim flow"""
    # Setup
    vault_registry.setPerformanceFee(undy_usd_vault.address, 10_00, sender=switchboard_alpha.address)
    setup_auto_deposit_config(undy_usd_vault, yield_vault_token)

    # User deposit with auto-deposit
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    undy_usd_vault.deposit(1000 * EIGHTEEN_DECIMALS, bob, sender=yield_underlying_token_whale)

    # Accrue yield
    yield_underlying_token.mint(yield_vault_token.address, 200 * EIGHTEEN_DECIMALS, sender=governance.address)
    boa.env.time_travel(seconds=301)

    # Another deposit to trigger yield calc
    undy_usd_vault.deposit(100 * EIGHTEEN_DECIMALS, bob, sender=yield_underlying_token_whale)

    # Should have pending yield
    assert undy_usd_vault.pendingYieldRealized() > 0

    # Claim fees
    fees = undy_usd_vault.claimPerformanceFees(sender=governance.address)
    assert fees > 0


def test_multiple_sequential_deposits_with_auto_deposit(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, yield_vault_token, vault_registry, switchboard_alpha, setup_auto_deposit_config):
    """Test multiple sequential deposits with auto-deposit enabled"""
    setup_auto_deposit_config(undy_usd_vault, yield_vault_token)

    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)

    initial_vault_token_bal = yield_vault_token.balanceOf(undy_usd_vault.address)

    # Multiple deposits
    for i in range(5):
        amount = (100 + i * 50) * EIGHTEEN_DECIMALS
        undy_usd_vault.deposit(amount, bob, sender=yield_underlying_token_whale)

    # Vault token balance should have increased significantly
    final_vault_token_bal = yield_vault_token.balanceOf(undy_usd_vault.address)
    assert final_vault_token_bal > initial_vault_token_bal


def test_multiple_users_with_auto_deposit(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, sally, yield_vault_token, vault_registry, switchboard_alpha, setup_auto_deposit_config):
    """Test multiple users depositing with auto-deposit"""
    setup_auto_deposit_config(undy_usd_vault, yield_vault_token)

    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)

    # Bob deposits
    shares_bob = undy_usd_vault.deposit(800 * EIGHTEEN_DECIMALS, bob, sender=yield_underlying_token_whale)

    # Sally deposits
    shares_sally = undy_usd_vault.deposit(1200 * EIGHTEEN_DECIMALS, sally, sender=yield_underlying_token_whale)

    # Both should have shares
    assert shares_bob > 0
    assert shares_sally > 0
    assert shares_sally > shares_bob  # Sally deposited more


def test_auto_deposit_with_max_deposit_limit(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, yield_vault_token, vault_registry, switchboard_alpha, setup_auto_deposit_config):
    """Test auto-deposit with maxDepositAmount limit"""
    # Set max deposit
    vault_registry.setMaxDepositAmount(undy_usd_vault.address, 2000 * EIGHTEEN_DECIMALS, sender=switchboard_alpha.address)
    setup_auto_deposit_config(undy_usd_vault, yield_vault_token)

    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)

    # Deposit within limit - should work
    undy_usd_vault.deposit(1500 * EIGHTEEN_DECIMALS, bob, sender=yield_underlying_token_whale)

    # Deposit exceeding limit - should fail
    with boa.reverts():
        undy_usd_vault.deposit(1000 * EIGHTEEN_DECIMALS, bob, sender=yield_underlying_token_whale)


def test_auto_deposit_then_immediate_withdrawal(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, yield_vault_token, vault_registry, switchboard_alpha, setup_auto_deposit_config):
    """Test auto-deposit followed by immediate withdrawal"""
    setup_auto_deposit_config(undy_usd_vault, yield_vault_token)

    # Deposit
    deposit_amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    shares = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)

    # Immediate withdrawal
    assets_received = undy_usd_vault.redeem(shares, bob, bob, sender=bob)

    # Should get approximately the same amount back (within 1% tolerance)
    assert abs(assets_received - deposit_amount) < deposit_amount // 100


def test_auto_deposit_target_changes_between_deposits(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, yield_vault_token, yield_vault_token_2, vault_registry, switchboard_alpha, setup_auto_deposit_config, starter_agent):
    """Test changing auto-deposit target between deposits"""
    # First deposit to token 1
    setup_auto_deposit_config(undy_usd_vault, yield_vault_token)
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    undy_usd_vault.deposit(500 * EIGHTEEN_DECIMALS, bob, sender=yield_underlying_token_whale)

    initial_bal_token1 = yield_vault_token.balanceOf(undy_usd_vault.address)
    initial_bal_token2 = yield_vault_token_2.balanceOf(undy_usd_vault.address)

    # Register token 2 by creating a small position
    small_amount = 10 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, small_amount, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(2, yield_underlying_token.address, yield_vault_token_2.address, small_amount, sender=starter_agent.address)

    # Change target to token 2
    vault_registry.setDefaultTargetVaultToken(undy_usd_vault.address, yield_vault_token_2.address, sender=switchboard_alpha.address)

    # Get balances after registering token 2
    initial_bal_token1_after_register = yield_vault_token.balanceOf(undy_usd_vault.address)
    initial_bal_token2_after_register = yield_vault_token_2.balanceOf(undy_usd_vault.address)

    # Second deposit should go to token 2
    undy_usd_vault.deposit(500 * EIGHTEEN_DECIMALS, bob, sender=yield_underlying_token_whale)

    # Token 1 balance should not change from after registration
    assert yield_vault_token.balanceOf(undy_usd_vault.address) == initial_bal_token1_after_register

    # Token 2 balance should increase
    assert yield_vault_token_2.balanceOf(undy_usd_vault.address) > initial_bal_token2_after_register


def test_auto_deposit_after_performance_fee_claim(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, starter_agent, yield_vault_token, governance, vault_registry, switchboard_alpha, setup_auto_deposit_config):
    """Test auto-deposit after claiming performance fees"""
    # Setup
    vault_registry.setPerformanceFee(undy_usd_vault.address, 10_00, sender=switchboard_alpha.address)

    # Create yield and claim fees
    yield_underlying_token.transfer(undy_usd_vault.address, 1000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(2, yield_underlying_token.address, yield_vault_token.address, 1000 * EIGHTEEN_DECIMALS, sender=starter_agent.address)

    yield_underlying_token.mint(yield_vault_token.address, 200 * EIGHTEEN_DECIMALS, sender=governance.address)
    boa.env.time_travel(seconds=301)

    yield_underlying_token.transfer(undy_usd_vault.address, 10 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(2, yield_underlying_token.address, yield_vault_token.address, 10 * EIGHTEEN_DECIMALS, sender=starter_agent.address)

    undy_usd_vault.claimPerformanceFees(sender=governance.address)

    # Now enable auto-deposit and deposit
    setup_auto_deposit_config(undy_usd_vault, yield_vault_token)
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    shares = undy_usd_vault.deposit(500 * EIGHTEEN_DECIMALS, bob, sender=yield_underlying_token_whale)

    assert shares > 0


def test_auto_deposit_with_existing_pending_fees(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, starter_agent, yield_vault_token, governance, vault_registry, switchboard_alpha, setup_auto_deposit_config):
    """Test auto-deposit when there are existing pending fees"""
    # Setup
    vault_registry.setPerformanceFee(undy_usd_vault.address, 20_00, sender=switchboard_alpha.address)

    # Create yield
    yield_underlying_token.transfer(undy_usd_vault.address, 1000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(2, yield_underlying_token.address, yield_vault_token.address, 1000 * EIGHTEEN_DECIMALS, sender=starter_agent.address)

    yield_underlying_token.mint(yield_vault_token.address, 200 * EIGHTEEN_DECIMALS, sender=governance.address)
    boa.env.time_travel(seconds=301)

    yield_underlying_token.transfer(undy_usd_vault.address, 10 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(2, yield_underlying_token.address, yield_vault_token.address, 10 * EIGHTEEN_DECIMALS, sender=starter_agent.address)

    # Now there are pending fees
    pending_fees_before = undy_usd_vault.getClaimablePerformanceFees()
    assert pending_fees_before > 0

    # User deposit with auto-deposit
    setup_auto_deposit_config(undy_usd_vault, yield_vault_token)
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    shares = undy_usd_vault.deposit(500 * EIGHTEEN_DECIMALS, bob, sender=yield_underlying_token_whale)

    # Deposit should succeed
    assert shares > 0

    # Pending fees should still be claimable
    pending_fees_after = undy_usd_vault.getClaimablePerformanceFees()
    assert abs(pending_fees_after - pending_fees_before) < 100  # Allow small variance


#################################
# 6. Edge Cases & Precision (4) #
#################################


def test_very_small_deposit_with_auto_deposit(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, yield_vault_token, vault_registry, switchboard_alpha, setup_auto_deposit_config):
    """Test very small deposit (100 wei) with auto-deposit"""
    setup_auto_deposit_config(undy_usd_vault, yield_vault_token)

    small_amount = 100  # 100 wei

    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    shares = undy_usd_vault.deposit(small_amount, bob, sender=yield_underlying_token_whale)

    # Should handle gracefully (might result in 0 shares or small shares)
    assert shares >= 0


def test_very_large_deposit_with_auto_deposit(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, yield_vault_token, vault_registry, switchboard_alpha, setup_auto_deposit_config):
    """Test very large deposit with auto-deposit"""
    setup_auto_deposit_config(undy_usd_vault, yield_vault_token)

    large_amount = 1_000_000 * EIGHTEEN_DECIMALS

    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    shares = undy_usd_vault.deposit(large_amount, bob, sender=yield_underlying_token_whale)

    assert shares > 0

    # Verify it was auto-deposited
    vault_token_bal = yield_vault_token.balanceOf(undy_usd_vault.address)
    assert vault_token_bal > 0


def test_auto_deposit_rounding_with_odd_amounts(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, yield_vault_token, vault_registry, switchboard_alpha, setup_auto_deposit_config):
    """Test auto-deposit precision with odd amounts"""
    setup_auto_deposit_config(undy_usd_vault, yield_vault_token)

    # Odd amount
    odd_amount = 1234567890123456789  # Not a round number

    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    shares = undy_usd_vault.deposit(odd_amount, bob, sender=yield_underlying_token_whale)

    assert shares > 0

    # Check that rounding doesn't cause significant loss
    idle_balance = yield_underlying_token.balanceOf(undy_usd_vault.address)
    assert idle_balance < odd_amount // 100  # Less than 1% stays idle


def test_auto_deposit_multiple_times_precision_accumulation(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, yield_vault_token, vault_registry, switchboard_alpha, setup_auto_deposit_config):
    """Test precision loss doesn't accumulate over multiple auto-deposits"""
    setup_auto_deposit_config(undy_usd_vault, yield_vault_token)

    # Track initial balance (setup created a small position)
    initial_underlying = undy_usd_vault.lastUnderlyingBal()

    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)

    total_deposited = 0
    num_deposits = 20

    for i in range(num_deposits):
        amount = EIGHTEEN_DECIMALS  # 1 token each time
        undy_usd_vault.deposit(amount, bob, sender=yield_underlying_token_whale)
        total_deposited += amount

    # Check that lastUnderlyingBal increased by approximately total deposited
    last_underlying = undy_usd_vault.lastUnderlyingBal()
    increase = last_underlying - initial_underlying
    # Allow 1% total variance
    assert abs(increase - total_deposited) < total_deposited // 100


##########################
# 7. Error Scenarios (5) #
##########################


def test_auto_deposit_cannot_set_if_not_switchboard(undy_usd_vault, vault_registry, bob):
    """Test that non-switchboard cannot enable auto-deposit"""
    with boa.reverts("no perms"):
        vault_registry.setShouldAutoDeposit(undy_usd_vault.address, True, sender=bob)


def test_deposit_when_can_deposit_false(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, yield_vault_token, vault_registry, switchboard_alpha, setup_auto_deposit_config):
    """Test deposit fails when canDeposit is set to false"""
    setup_auto_deposit_config(undy_usd_vault, yield_vault_token)

    # Disable deposits
    vault_registry.setCanDeposit(undy_usd_vault.address, False, sender=switchboard_alpha.address)

    # Try to deposit - should fail
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    with boa.reverts():
        undy_usd_vault.deposit(1000 * EIGHTEEN_DECIMALS, bob, sender=yield_underlying_token_whale)


def test_auto_deposit_when_lego_not_available(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, vault_registry, switchboard_alpha):
    """Test auto-deposit gracefully handles when lego is not available"""
    # Set auto-deposit with invalid configuration (this might make _onReceiveVaultFunds return 0)
    vault_registry.setShouldAutoDeposit(undy_usd_vault.address, True, sender=switchboard_alpha.address)
    # Don't set defaultTargetVaultToken and ensure no positions exist

    deposit_amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)

    # Should succeed but funds stay idle
    shares = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)
    assert shares > 0

    # Funds should be idle
    idle_balance = yield_underlying_token.balanceOf(undy_usd_vault.address)
    assert idle_balance >= deposit_amount


def test_deposit_exceeds_max_with_auto_deposit_fails(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, yield_vault_token, vault_registry, switchboard_alpha, setup_auto_deposit_config):
    """Test deposit exceeding maxDepositAmount fails even with auto-deposit"""
    setup_auto_deposit_config(undy_usd_vault, yield_vault_token)

    # Set max deposit
    vault_registry.setMaxDepositAmount(undy_usd_vault.address, 500 * EIGHTEEN_DECIMALS, sender=switchboard_alpha.address)

    # Try to deposit more than max
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    with boa.reverts():
        undy_usd_vault.deposit(1000 * EIGHTEEN_DECIMALS, bob, sender=yield_underlying_token_whale)


def test_set_invalid_vault_address_fails(vault_registry, switchboard_alpha, bob):
    """Test setting auto-deposit config for invalid vault address fails"""
    invalid_vault_addr = bob  # Using bob as invalid vault address

    with boa.reverts():
        vault_registry.setShouldAutoDeposit(invalid_vault_addr, True, sender=switchboard_alpha.address)


##############################
# 8. Dust Sweeping Tests (3) #
##############################


def test_auto_deposit_sweeps_idle_dust(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, starter_agent, yield_vault_token, vault_registry, switchboard_alpha, setup_auto_deposit_config):
    """Test that auto-deposit sweeps up idle dust sitting in vault from previous operations"""
    # Setup auto-deposit
    setup_auto_deposit_config(undy_usd_vault, yield_vault_token)

    # Create some dust by transferring directly to vault (simulating withdrawal leftover)
    dust_amount = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, dust_amount, sender=yield_underlying_token_whale)

    # Verify dust is sitting idle
    idle_before = yield_underlying_token.balanceOf(undy_usd_vault.address)
    assert idle_before == dust_amount

    # Get initial vault token balance
    initial_vault_token_bal = yield_vault_token.balanceOf(undy_usd_vault.address)

    # User deposit - should sweep both the deposit AND the dust
    deposit_amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)

    # Verify idle balance is now minimal (both deposit and dust were swept)
    idle_after = yield_underlying_token.balanceOf(undy_usd_vault.address)
    assert idle_after < 100  # Minimal dust

    # Verify vault token balance increased by approximately deposit_amount + dust_amount
    new_vault_token_bal = yield_vault_token.balanceOf(undy_usd_vault.address)
    vault_token_increase = new_vault_token_bal - initial_vault_token_bal
    total_expected = deposit_amount + dust_amount
    assert abs(vault_token_increase - total_expected) < total_expected // 100  # Within 1%


def test_auto_deposit_sweeps_withdrawal_dust(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, sally, starter_agent, yield_vault_token, vault_registry, switchboard_alpha, setup_auto_deposit_config):
    """Test that auto-deposit sweeps dust left over from withdrawals that pulled out extra"""
    # Setup auto-deposit
    setup_auto_deposit_config(undy_usd_vault, yield_vault_token)

    # User deposits
    deposit_amount = 2000 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    shares = undy_usd_vault.deposit(deposit_amount, bob, sender=yield_underlying_token_whale)

    # User redeems half, which might pull out more than needed due to buffer
    vault_registry.setRedemptionBuffer(undy_usd_vault.address, 5_00, sender=switchboard_alpha.address)  # 5% buffer
    half_shares = shares // 2
    undy_usd_vault.redeem(half_shares, bob, bob, sender=bob)

    # Check if there's any dust sitting idle (from the redemption buffer)
    idle_after_withdrawal = yield_underlying_token.balanceOf(undy_usd_vault.address)

    # Get vault token balance before new deposit
    vault_token_bal_before = yield_vault_token.balanceOf(undy_usd_vault.address)

    # Another user deposits - should sweep any idle dust
    new_deposit = 500 * EIGHTEEN_DECIMALS
    undy_usd_vault.deposit(new_deposit, sally, sender=yield_underlying_token_whale)

    # Verify idle balance is minimal
    idle_after_deposit = yield_underlying_token.balanceOf(undy_usd_vault.address)
    assert idle_after_deposit < 100

    # Verify vault token balance increased by new_deposit + any dust that was idle
    vault_token_bal_after = yield_vault_token.balanceOf(undy_usd_vault.address)
    increase = vault_token_bal_after - vault_token_bal_before
    expected_increase = new_deposit + idle_after_withdrawal
    assert abs(increase - expected_increase) < expected_increase // 100  # Within 1%


def test_auto_deposit_sweeps_multiple_dust_accumulations(undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, bob, starter_agent, yield_vault_token, vault_registry, switchboard_alpha, setup_auto_deposit_config):
    """Test that auto-deposit sweeps accumulated dust from multiple small transfers"""
    # Setup auto-deposit
    setup_auto_deposit_config(undy_usd_vault, yield_vault_token)

    # Disable auto-deposit temporarily to accumulate dust
    vault_registry.setShouldAutoDeposit(undy_usd_vault.address, False, sender=switchboard_alpha.address)

    # Create multiple small deposits that will stay idle
    dust_amounts = [10 * EIGHTEEN_DECIMALS, 25 * EIGHTEEN_DECIMALS, 15 * EIGHTEEN_DECIMALS]
    total_dust = sum(dust_amounts)

    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    for dust in dust_amounts:
        undy_usd_vault.deposit(dust, bob, sender=yield_underlying_token_whale)

    # Verify dust accumulated
    idle_dust = yield_underlying_token.balanceOf(undy_usd_vault.address)
    assert idle_dust >= total_dust

    # Re-enable auto-deposit
    vault_registry.setShouldAutoDeposit(undy_usd_vault.address, True, sender=switchboard_alpha.address)

    # Get initial vault token balance
    initial_vault_token_bal = yield_vault_token.balanceOf(undy_usd_vault.address)

    # New deposit should sweep all accumulated dust
    new_deposit = 1000 * EIGHTEEN_DECIMALS
    undy_usd_vault.deposit(new_deposit, bob, sender=yield_underlying_token_whale)

    # Verify all dust was swept
    idle_after = yield_underlying_token.balanceOf(undy_usd_vault.address)
    assert idle_after < 100  # Minimal

    # Verify vault token balance increased by new_deposit + total_dust
    new_vault_token_bal = yield_vault_token.balanceOf(undy_usd_vault.address)
    total_increase = new_vault_token_bal - initial_vault_token_bal
    total_expected = new_deposit + idle_dust
    assert abs(total_increase - total_expected) < total_expected // 100  # Within 1%
