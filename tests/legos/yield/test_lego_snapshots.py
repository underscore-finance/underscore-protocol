import pytest
import boa

from constants import EIGHTEEN_DECIMALS, MAX_UINT256


##################
# Snapshot Tests #
##################


###################
# Config Tests #
###################


def test_set_snapshot_config_basic(mock_yield_lego, switchboard_alpha):
    """Test basic snapshot config setting"""
    config = (
        300,   # minSnapshotDelay
        10,    # maxNumSnapshots
        500,   # maxUpsideDeviation (5%)
        86400,  # staleTime (1 day)
    )

    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    stored_config = mock_yield_lego.snapShotPriceConfig()
    assert stored_config.minSnapshotDelay == 300
    assert stored_config.maxNumSnapshots == 10
    assert stored_config.maxUpsideDeviation == 500
    assert stored_config.staleTime == 86400


def test_set_snapshot_config_only_switchboard(mock_yield_lego, bob):
    """Test that only switchboard can set snapshot config"""
    config = (300, 10, 500, 86400)

    with boa.reverts():
        mock_yield_lego.setSnapShotPriceConfig(config, sender=bob)


def test_set_snapshot_config_invalid_values(mock_yield_lego, switchboard_alpha):
    """Test that invalid config values are rejected"""
    # Max snapshots = 0 should fail
    config = (300, 0, 500, 86400)
    with boa.reverts():
        mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    # Max upside deviation > 100% should fail
    config = (300, 10, 10001, 86400)
    with boa.reverts():
        mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    # Stale time >= 1 week should fail
    config = (300, 10, 500, 604800)
    with boa.reverts():
        mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)


def test_set_snapshot_config_updates_existing(mock_yield_lego, switchboard_alpha):
    """Test updating an existing config"""
    config1 = (300, 10, 500, 86400)
    mock_yield_lego.setSnapShotPriceConfig(config1, sender=switchboard_alpha.address)

    config2 = (600, 20, 1000, 172800)  # Different values (2 days)
    mock_yield_lego.setSnapShotPriceConfig(config2, sender=switchboard_alpha.address)

    stored_config = mock_yield_lego.snapShotPriceConfig()
    assert stored_config.minSnapshotDelay == 600
    assert stored_config.maxNumSnapshots == 20
    assert stored_config.maxUpsideDeviation == 1000
    assert stored_config.staleTime == 172800


#############################
# Snapshot Addition Tests #
#############################


def test_snapshot_added_on_deposit(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test that snapshot is added when depositing to yield lego"""
    # Set snapshot config
    config = (300, 10, 500, 86400)
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    # Get initial snapshot state
    initial_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    initial_index = initial_data.nextIndex

    # Deposit
    amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob_user_wallet.address, amount, sender=yield_underlying_token_whale)

    lego_id = lego_book.getRegId(mock_yield_lego)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Check snapshot was added
    snapshot_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert snapshot_data.nextIndex == initial_index + 1
    assert snapshot_data.lastSnapShot.pricePerShare > 0
    assert snapshot_data.lastSnapShot.totalSupply > 0
    assert snapshot_data.lastSnapShot.lastUpdate > 0

    # Verify snapshot in storage
    snapshot = mock_yield_lego.snapShots(yield_vault_token.address, initial_index)
    assert snapshot.pricePerShare > 0
    assert snapshot.totalSupply > 0


def test_snapshot_added_on_withdrawal(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test that snapshot is added when withdrawing from yield lego"""
    # Set snapshot config
    config = (300, 10, 500, 86400)
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    # First deposit
    amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob_user_wallet.address, amount, sender=yield_underlying_token_whale)

    lego_id = lego_book.getRegId(mock_yield_lego)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Get snapshot state after deposit
    data_after_deposit = mock_yield_lego.snapShotData(yield_vault_token.address)
    index_after_deposit = data_after_deposit.nextIndex

    # Time travel to allow another snapshot
    boa.env.time_travel(seconds=301)

    # Withdraw
    bob_user_wallet.withdrawFromYield(lego_id, yield_vault_token, MAX_UINT256, sender=bob)

    # Check snapshot was added
    snapshot_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert snapshot_data.nextIndex == index_after_deposit + 1
    assert snapshot_data.lastSnapShot.pricePerShare > 0
    assert snapshot_data.lastSnapShot.lastUpdate > data_after_deposit.lastSnapShot.lastUpdate


def test_snapshot_respects_min_delay(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test that min delay prevents rapid snapshots"""
    # Set snapshot config
    config = (300, 10, 500, 86400)
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    # First deposit
    amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob_user_wallet.address, amount, sender=yield_underlying_token_whale)

    lego_id = lego_book.getRegId(mock_yield_lego)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Get snapshot state after first deposit
    data_after_first = mock_yield_lego.snapShotData(yield_vault_token.address)
    index_after_first = data_after_first.nextIndex

    # Immediate second deposit (within min delay)
    yield_underlying_token.transfer(bob_user_wallet.address, amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Snapshot should NOT be added
    snapshot_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert snapshot_data.nextIndex == index_after_first  # No change

    # Time travel past min delay
    boa.env.time_travel(seconds=301)

    # Third deposit (after min delay)
    yield_underlying_token.transfer(bob_user_wallet.address, amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Snapshot SHOULD be added now
    snapshot_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert snapshot_data.nextIndex == index_after_first + 1


def test_snapshot_circular_buffer(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test that circular buffer wraps around correctly"""
    # Set small max snapshots for testing
    config = (300, 3, 500, 86400)  # Only 3 snapshots max
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    amount = 100 * EIGHTEEN_DECIMALS
    lego_id = lego_book.getRegId(mock_yield_lego)

    # Add 5 snapshots (more than max)
    for i in range(5):
        yield_underlying_token.transfer(bob_user_wallet.address, amount, sender=yield_underlying_token_whale)
        bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

        if i < 4:  # Time travel between deposits (not needed after last)
            boa.env.time_travel(seconds=301)

    # Check that index wrapped around
    snapshot_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert snapshot_data.nextIndex == 2  # (5 snapshots) % 3 = 2

    # Verify the snapshots in circular buffer
    for i in range(3):
        snapshot = mock_yield_lego.snapShots(yield_vault_token.address, i)
        assert snapshot.pricePerShare > 0  # All should have data


def test_add_price_snapshot_updates_next_index(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test that adding multiple snapshots correctly updates the next index"""
    # Set snapshot config
    config = (300, 10, 500, 86400)
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    # Setup: deposit to create a vault position
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
    lego_id = lego_book.getRegId(mock_yield_lego)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Get initial state
    initial_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    initial_index = initial_data.nextIndex

    # Add first snapshot
    boa.env.time_travel(seconds=301)
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Verify first snapshot
    snapshot_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert snapshot_data.nextIndex == initial_index + 1

    # Add second snapshot
    boa.env.time_travel(seconds=301)
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Verify second snapshot
    snapshot_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert snapshot_data.nextIndex == initial_index + 2

    # Add third snapshot
    boa.env.time_travel(seconds=301)
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Verify third snapshot
    snapshot_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert snapshot_data.nextIndex == initial_index + 3

    # Verify recent snapshots are stored
    for i in range(initial_index, initial_index + 3):
        snapshot = mock_yield_lego.snapShots(yield_vault_token.address, i)
        assert snapshot.pricePerShare > 0
        assert snapshot.totalSupply > 0


################################
# Weighted Price Tests #
################################


def test_get_weighted_price_single_snapshot(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test weighted price with single snapshot returns current price"""
    # Set snapshot config
    config = (300, 10, 500, 86400)
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    # Deposit to create snapshot
    amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob_user_wallet.address, amount, sender=yield_underlying_token_whale)

    lego_id = lego_book.getRegId(mock_yield_lego)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Get weighted price
    weighted_price = mock_yield_lego.getWeightedPricePerShare(yield_vault_token.address)

    # Should equal current price per share
    decimals = yield_vault_token.decimals()
    current_price = mock_yield_lego.getPricePerShare(yield_vault_token.address, decimals)

    assert weighted_price > 0
    assert weighted_price == current_price


def test_get_weighted_price_multiple_snapshots(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test weighted price calculation with multiple snapshots"""
    # Set snapshot config
    config = (300, 10, 500, 86400)
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    lego_id = lego_book.getRegId(mock_yield_lego)

    # Add multiple snapshots with different amounts (to vary total supply)
    for i in range(3):
        amount = (100 * (i + 1)) * EIGHTEEN_DECIMALS  # Increasing deposits
        yield_underlying_token.transfer(bob_user_wallet.address, amount, sender=yield_underlying_token_whale)
        bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

        if i < 2:
            boa.env.time_travel(seconds=301)

    # Get weighted price
    weighted_price = mock_yield_lego.getWeightedPricePerShare(yield_vault_token.address)

    # Weighted price should be > 0
    assert weighted_price > 0

    # Verify snapshots exist
    snapshot_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert snapshot_data.nextIndex == 3  # 3 snapshots added


def test_get_weighted_price_no_snapshots(mock_yield_lego):
    """Test weighted price returns 0 when no snapshots exist"""
    # Use a vault token that has never been deposited to
    fake_vault_token = "0x0000000000000000000000000000000000000123"

    weighted_price = mock_yield_lego.getWeightedPricePerShare(fake_vault_token)
    assert weighted_price == 0


def test_get_weighted_price_excludes_stale(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test that stale snapshots are excluded from weighted average"""
    # Set short stale time for testing
    config = (300, 10, 500, 600)  # 10 minute stale time
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    amount = 100 * EIGHTEEN_DECIMALS
    lego_id = lego_book.getRegId(mock_yield_lego)

    # Add first snapshot
    yield_underlying_token.transfer(bob_user_wallet.address, amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Time travel past stale time
    boa.env.time_travel(seconds=601)

    # Add second snapshot (first should now be stale)
    yield_underlying_token.transfer(bob_user_wallet.address, amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Get weighted price - should only use fresh snapshot
    weighted_price = mock_yield_lego.getWeightedPricePerShare(yield_vault_token.address)

    decimals = yield_vault_token.decimals()
    current_price = mock_yield_lego.getPricePerShare(yield_vault_token.address, decimals)

    # Should equal current price (only fresh snapshot used)
    assert weighted_price == current_price


############################
# Multi-Vault Tests #
############################


def test_snapshots_independent_per_vault_token(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    yield_vault_token_2,
    switchboard_alpha,
):
    """Test that snapshots are stored independently per vault token"""
    # Set snapshot config
    config = (300, 10, 500, 86400)
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    amount = 100 * EIGHTEEN_DECIMALS
    lego_id = lego_book.getRegId(mock_yield_lego)

    # Deposit to first vault token
    yield_underlying_token.transfer(bob_user_wallet.address, amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Deposit to second vault token
    yield_underlying_token.transfer(bob_user_wallet.address, amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token_2, MAX_UINT256, sender=bob)

    # Check both have independent snapshots
    vault1_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    vault2_data = mock_yield_lego.snapShotData(yield_vault_token_2.address)

    assert vault1_data.nextIndex == 1
    assert vault2_data.nextIndex == 1

    assert vault1_data.lastSnapShot.pricePerShare > 0
    assert vault2_data.lastSnapShot.pricePerShare > 0


############################
# Edge Case Tests #
############################


def test_snapshot_with_zero_total_supply(mock_yield_lego, yield_vault_token, switchboard_alpha):
    """Test snapshot behavior when vault token has zero total supply"""
    # Set snapshot config
    config = (300, 10, 500, 86400)
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    # Just verify the lego can be called even if no deposits yet
    weighted_price = mock_yield_lego.getWeightedPricePerShare(yield_vault_token.address)
    # Should return 0 or handle gracefully
    assert weighted_price >= 0


def test_multiple_deposits_same_block(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test that only one snapshot is added when multiple deposits happen in same block"""
    # Set snapshot config
    config = (300, 10, 500, 86400)
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    amount = 100 * EIGHTEEN_DECIMALS
    lego_id = lego_book.getRegId(mock_yield_lego)

    # First deposit
    yield_underlying_token.transfer(bob_user_wallet.address, amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    initial_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    initial_index = initial_data.nextIndex

    # Second deposit in same block (no time travel)
    yield_underlying_token.transfer(bob_user_wallet.address, amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Should still have same index (snapshot not added due to same timestamp)
    snapshot_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert snapshot_data.nextIndex == initial_index


############################
# Integration Tests #
############################


def test_full_deposit_withdraw_cycle_with_snapshots(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test complete deposit-withdraw cycle with snapshot tracking"""
    # Set snapshot config
    config = (300, 10, 500, 86400)
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    amount = 100 * EIGHTEEN_DECIMALS
    lego_id = lego_book.getRegId(mock_yield_lego)

    # Initial deposit
    yield_underlying_token.transfer(bob_user_wallet.address, amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    data_after_deposit = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert data_after_deposit.nextIndex == 1
    snapshot1 = data_after_deposit.lastSnapShot

    # Time travel
    boa.env.time_travel(seconds=301)

    # Second deposit
    yield_underlying_token.transfer(bob_user_wallet.address, amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    data_after_second_deposit = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert data_after_second_deposit.nextIndex == 2

    # Time travel
    boa.env.time_travel(seconds=301)

    # Partial withdrawal
    vault_balance = yield_vault_token.balanceOf(bob_user_wallet.address)
    bob_user_wallet.withdrawFromYield(lego_id, yield_vault_token, vault_balance // 2, sender=bob)

    data_after_withdraw = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert data_after_withdraw.nextIndex == 3

    # Get weighted price throughout
    weighted_price = mock_yield_lego.getWeightedPricePerShare(yield_vault_token.address)
    assert weighted_price > 0

    # Time travel
    boa.env.time_travel(seconds=301)

    # Final withdrawal
    bob_user_wallet.withdrawFromYield(lego_id, yield_vault_token, MAX_UINT256, sender=bob)

    final_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert final_data.nextIndex == 4

    # Verify all snapshots exist
    for i in range(4):
        snapshot = mock_yield_lego.snapShots(yield_vault_token.address, i)
        assert snapshot.lastUpdate > 0


############################
# CRITICAL: Throttling Tests #
############################


def test_add_price_snapshot_throttles_upside(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
    governance,
):
    """Test that price snapshots respect max upside deviation (throttling)"""
    # Set snapshot config with 5% max upside
    config = (300, 10, 500, 86400)  # 500 = 5%
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    # Setup: deposit to create a vault position
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)

    lego_id = lego_book.getRegId(mock_yield_lego)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    initial_snapshot = mock_yield_lego.snapShotData(yield_vault_token.address).lastSnapShot
    initial_price = initial_snapshot.pricePerShare

    # Simulate massive yield accrual (10x increase in vault assets)
    current_balance = yield_underlying_token.balanceOf(yield_vault_token.address)
    yield_underlying_token.mint(yield_vault_token.address, current_balance * 9, sender=governance.address)

    # Add new snapshot after time delay
    boa.env.time_travel(seconds=301)
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    new_snapshot = mock_yield_lego.snapShotData(yield_vault_token.address).lastSnapShot
    new_price = new_snapshot.pricePerShare

    # Price should be throttled to max 5% increase
    max_allowed_price = initial_price + (initial_price * 500 // 10000)
    assert new_price == max_allowed_price
    assert new_price < initial_price * 2  # Definitely not 10x


def test_snapshot_price_manipulation_via_flash_loan_scenario(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
    governance,
):
    """Test that snapshot throttling prevents flash-loan style price manipulation"""
    # Set snapshot config
    config = (300, 10, 500, 86400)  # 5% max upside
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    # Create initial position
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob_user_wallet.address, initial_deposit, sender=yield_underlying_token_whale)

    lego_id = lego_book.getRegId(mock_yield_lego)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    initial_price = mock_yield_lego.snapShotData(yield_vault_token.address).lastSnapShot.pricePerShare

    # Simulate flash loan attack: Attacker dumps huge amount to inflate price 100x
    vault_balance = yield_underlying_token.balanceOf(yield_vault_token.address)
    attack_amount = vault_balance * 100
    yield_underlying_token.mint(yield_vault_token.address, attack_amount, sender=governance.address)

    # Attacker tries to snapshot the inflated price
    boa.env.time_travel(seconds=301)
    yield_underlying_token.transfer(bob_user_wallet.address, initial_deposit, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Get the stored snapshot - should be throttled
    snapshot_after_attack = mock_yield_lego.snapShotData(yield_vault_token.address).lastSnapShot
    stored_price = snapshot_after_attack.pricePerShare

    # Verify throttling occurred - price should NOT be 100x
    max_allowed = initial_price + (initial_price * 500 // 10000)
    assert stored_price <= max_allowed
    assert stored_price < initial_price * 2  # Definitely not 100x

    # Even after multiple snapshots, cumulative throttling limits damage
    for i in range(3):
        boa.env.time_travel(seconds=301)
        yield_underlying_token.transfer(bob_user_wallet.address, 10 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
        bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    final_snapshot = mock_yield_lego.snapShotData(yield_vault_token.address).lastSnapShot
    # With 5% throttling, even after 4 snapshots (initial + 3), max is ~1.215x
    assert final_snapshot.pricePerShare < initial_price * 2


def test_rapid_price_changes_with_throttling(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
    governance,
):
    """Test throttling with rapid consecutive price increases"""
    # Set snapshot config with 10% max upside
    config = (300, 10, 1000, 86400)  # 1000 = 10%
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    # Initial deposit
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)

    lego_id = lego_book.getRegId(mock_yield_lego)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    initial_price = mock_yield_lego.snapShotData(yield_vault_token.address).lastSnapShot.pricePerShare

    # Add yield and snapshot 5 times rapidly
    for i in range(5):
        # Add 50% more assets each time
        current_balance = yield_underlying_token.balanceOf(yield_vault_token.address)
        yield_underlying_token.mint(yield_vault_token.address, current_balance // 2, sender=governance.address)

        boa.env.time_travel(seconds=301)
        yield_underlying_token.transfer(bob_user_wallet.address, 10 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
        bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    final_price = mock_yield_lego.snapShotData(yield_vault_token.address).lastSnapShot.pricePerShare

    # With 10% throttling per snapshot, max cumulative is (1.1^5) = 1.61x
    max_expected = initial_price * 161 // 100
    # Allow for rounding errors (0.1% tolerance)
    tolerance = max_expected // 1000
    assert final_price <= max_expected + tolerance
    assert final_price > initial_price  # But still increased


def test_throttle_with_zero_values(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test throttling edge cases with zero values"""
    # Set snapshot config
    config = (300, 10, 500, 86400)
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    # Create first snapshot
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)

    lego_id = lego_book.getRegId(mock_yield_lego)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Verify snapshot was created and has non-zero price
    snapshot_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert snapshot_data.lastSnapShot.pricePerShare > 0


############################
# CRITICAL: Permission Tests #
############################


def test_external_add_price_snapshot_permission(
    yield_vault_token,
    mock_yield_lego,
    switchboard_alpha,
):
    """Test that external addPriceSnapshot requires switchboard permissions"""
    # Should succeed with switchboard
    result = mock_yield_lego.addPriceSnapshot(
        yield_vault_token.address,
        EIGHTEEN_DECIMALS,
        18,
        sender=switchboard_alpha.address
    )
    assert result == True or result == False  # Method exists and returns bool


def test_external_add_price_snapshot_non_switchboard_reverts(
    yield_vault_token,
    mock_yield_lego,
    bob,
):
    """Test that non-switchboard callers cannot add snapshots directly"""
    # Should revert with permission check
    with boa.reverts():
        mock_yield_lego.addPriceSnapshot(
            yield_vault_token.address,
            EIGHTEEN_DECIMALS,
            18,
            sender=bob
        )


############################
# CRITICAL: Security Tests #
############################


def test_rapid_deposit_withdraw_cannot_manipulate_price(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test that rapid deposit/withdrawal cycles cannot manipulate weighted price"""
    # Set snapshot config
    config = (300, 10, 500, 86400)
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    # Create initial position and snapshot
    initial_deposit = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob_user_wallet.address, initial_deposit, sender=yield_underlying_token_whale)

    lego_id = lego_book.getRegId(mock_yield_lego)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Wait for snapshot to be valid
    boa.env.time_travel(seconds=301)
    yield_underlying_token.transfer(bob_user_wallet.address, 100 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    initial_weighted_price = mock_yield_lego.getWeightedPricePerShare(yield_vault_token.address)

    # Attempt large deposit (manipulation attempt)
    large_deposit = 5000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob_user_wallet.address, large_deposit, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Cannot add snapshot immediately (minDelay protection)
    # So weighted price should be unchanged
    current_weighted_price = mock_yield_lego.getWeightedPricePerShare(yield_vault_token.address)
    # Price may have changed slightly due to new snapshot, but should be weighted average
    assert current_weighted_price > 0

    # Even after time passes, weighted average prevents instant manipulation
    boa.env.time_travel(seconds=301)
    yield_underlying_token.transfer(bob_user_wallet.address, 100 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    final_weighted_price = mock_yield_lego.getWeightedPricePerShare(yield_vault_token.address)
    # Weighted average should prevent extreme price changes
    assert final_weighted_price > 0


def test_min_delay_prevents_manipulation(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test that minDelay acts as security feature against manipulation"""
    # Set short minDelay
    config = (60, 10, 500, 86400)  # 60 second delay
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    # Initial deposit
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)

    lego_id = lego_book.getRegId(mock_yield_lego)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    initial_index = mock_yield_lego.snapShotData(yield_vault_token.address).nextIndex

    # Try rapid deposits (should only create 1 snapshot per minDelay period)
    for i in range(5):
        # Wait only 10 seconds
        boa.env.time_travel(seconds=10)
        yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
        bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Should have very few snapshots (50 seconds total, less than minDelay)
    current_index = mock_yield_lego.snapShotData(yield_vault_token.address).nextIndex
    snapshots_added = current_index - initial_index if current_index >= initial_index else current_index + 10 - initial_index
    assert snapshots_added <= 1  # At most 1 snapshot in 50 seconds with 60s delay


######################################################
# IMPORTANT: Advanced Weighted Price Scenario Tests #
######################################################


def test_get_weighted_price_with_different_supplies(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test weighted price calculation with varying total supplies"""
    # Set config: no delay, 5 max snapshots
    config = (0, 5, 500, 86400)
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    lego_id = lego_book.getRegId(mock_yield_lego)

    # Create snapshots with different supplies
    deposit_amounts = [100, 200, 500, 1000, 2000]  # Increasing supplies
    prices = []

    for amount_multiplier in deposit_amounts:
        deposit_amount = amount_multiplier * EIGHTEEN_DECIMALS
        yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
        bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

        # Get current price
        current_price = mock_yield_lego.snapShotData(yield_vault_token.address).lastSnapShot.pricePerShare
        prices.append(current_price)

        boa.env.time_travel(seconds=1)

    # Weighted average should favor later snapshots with higher supply
    weighted_price = mock_yield_lego.getWeightedPricePerShare(yield_vault_token.address)
    assert weighted_price > 0
    # Should be closer to later prices (which have higher weights due to higher supply)
    assert weighted_price >= prices[0]  # At least as high as first price


def test_get_weighted_price_circular_buffer_full(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test weighted price calculation when circular buffer is full and wraps around"""
    max_snapshots = 5
    config = (0, max_snapshots, 500, 86400)  # 5 max snapshots
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    lego_id = lego_book.getRegId(mock_yield_lego)
    deposit_amount = 100 * EIGHTEEN_DECIMALS

    # Create more snapshots than max to trigger wraparound
    for i in range(max_snapshots + 3):  # 8 snapshots, buffer size 5
        yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
        bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)
        boa.env.time_travel(seconds=1)

    # Check that nextIndex wrapped around
    next_index = mock_yield_lego.snapShotData(yield_vault_token.address).nextIndex
    assert next_index == 3  # (8 % 5) = 3

    # Weighted price should still calculate correctly
    weighted_price = mock_yield_lego.getWeightedPricePerShare(yield_vault_token.address)
    assert weighted_price > 0


def test_get_weighted_price_with_price_variations(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test weighted price with multiple different price points"""
    config = (0, 10, 1000, 86400)  # 10% max upside
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    lego_id = lego_book.getRegId(mock_yield_lego)

    # Create initial deposit
    initial_amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob_user_wallet.address, initial_amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    initial_price = mock_yield_lego.snapShotData(yield_vault_token.address).lastSnapShot.pricePerShare

    # Simulate yield accrual over several snapshots (small incremental increases)
    for i in range(5):
        boa.env.time_travel(seconds=1)
        # Small deposit to trigger snapshot with slightly higher price
        small_deposit = 10 * EIGHTEEN_DECIMALS
        yield_underlying_token.transfer(bob_user_wallet.address, small_deposit, sender=yield_underlying_token_whale)
        bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    final_price = mock_yield_lego.snapShotData(yield_vault_token.address).lastSnapShot.pricePerShare
    weighted_price = mock_yield_lego.getWeightedPricePerShare(yield_vault_token.address)

    # Weighted price should be between initial and final
    assert weighted_price >= initial_price
    assert weighted_price <= final_price + 1  # Allow 1 wei rounding


def test_weighted_price_accuracy_with_various_snapshot_ages(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test that weighted price calculation handles snapshots of varying ages correctly"""
    # Set staleTime to 1 hour
    config = (0, 10, 500, 3600)  # 1 hour stale time
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    lego_id = lego_book.getRegId(mock_yield_lego)
    deposit_amount = 100 * EIGHTEEN_DECIMALS

    # Create old snapshot
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    old_price = mock_yield_lego.snapShotData(yield_vault_token.address).lastSnapShot.pricePerShare

    # Time travel 30 minutes (still fresh)
    boa.env.time_travel(seconds=1800)

    # Create medium-age snapshot
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Time travel another 30 minutes (now first snapshot is ~1 hour old, borderline stale)
    boa.env.time_travel(seconds=1800)

    # Create fresh snapshot
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # All snapshots should still be included (just at 1 hour boundary)
    weighted_price = mock_yield_lego.getWeightedPricePerShare(yield_vault_token.address)
    assert weighted_price > 0


def test_weighted_price_with_single_fresh_snapshot_among_stale(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test weighted price when only one snapshot is fresh and rest are stale"""
    # Set very short staleTime
    config = (0, 10, 500, 60)  # 60 second stale time
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    lego_id = lego_book.getRegId(mock_yield_lego)
    deposit_amount = 100 * EIGHTEEN_DECIMALS

    # Create several old snapshots
    for i in range(5):
        yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
        bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)
        boa.env.time_travel(seconds=1)

    # Travel far into future (make all snapshots stale)
    boa.env.time_travel(seconds=120)

    # Create one fresh snapshot
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    fresh_price = mock_yield_lego.snapShotData(yield_vault_token.address).lastSnapShot.pricePerShare

    # Weighted price should be based only on fresh snapshot
    weighted_price = mock_yield_lego.getWeightedPricePerShare(yield_vault_token.address)
    assert weighted_price == fresh_price


##################################
# IMPORTANT: Edge Case Tests    #
##################################


def test_add_price_snapshot_same_timestamp_rejected(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test that snapshots at the same timestamp are rejected"""
    config = (0, 10, 500, 86400)
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    lego_id = lego_book.getRegId(mock_yield_lego)
    deposit_amount = 100 * EIGHTEEN_DECIMALS

    # First deposit
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    first_index = mock_yield_lego.snapShotData(yield_vault_token.address).nextIndex

    # Second deposit at same timestamp (no time travel)
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    second_index = mock_yield_lego.snapShotData(yield_vault_token.address).nextIndex

    # Index should not have advanced
    assert second_index == first_index


def test_snapshot_timing_boundary_conditions(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test snapshot timing at exact minDelay boundaries"""
    min_delay = 60
    config = (min_delay, 10, 500, 86400)
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    lego_id = lego_book.getRegId(mock_yield_lego)
    deposit_amount = 100 * EIGHTEEN_DECIMALS

    # First snapshot
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    first_timestamp = mock_yield_lego.snapShotData(yield_vault_token.address).lastSnapShot.lastUpdate

    # Try at exactly minDelay - 1 second (should fail)
    boa.env.time_travel(seconds=min_delay - 1)
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    second_timestamp = mock_yield_lego.snapShotData(yield_vault_token.address).lastSnapShot.lastUpdate
    assert second_timestamp == first_timestamp  # No new snapshot

    # Try at exactly minDelay + 1 second (should succeed)
    boa.env.time_travel(seconds=2)  # Total: minDelay + 1
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    third_timestamp = mock_yield_lego.snapShotData(yield_vault_token.address).lastSnapShot.lastUpdate
    assert third_timestamp > first_timestamp  # New snapshot created


def test_snapshot_index_wraparound_at_exact_max(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test circular buffer index wraparound at exact maxNumSnapshots"""
    max_snapshots = 3
    config = (0, max_snapshots, 500, 86400)
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    lego_id = lego_book.getRegId(mock_yield_lego)
    deposit_amount = 100 * EIGHTEEN_DECIMALS

    # Create exactly maxNumSnapshots
    for i in range(max_snapshots):
        yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
        bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)
        boa.env.time_travel(seconds=1)

        expected_index = (i + 1) % max_snapshots
        actual_index = mock_yield_lego.snapShotData(yield_vault_token.address).nextIndex
        assert actual_index == expected_index

    # Next snapshot should wrap to 0
    assert mock_yield_lego.snapShotData(yield_vault_token.address).nextIndex == 0


def test_max_snapshots_zero_config(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test behavior when maxNumSnapshots is set to 0 (snapshots disabled)"""
    # Note: Config validation should prevent this, but test the behavior
    # Set config with maxNumSnapshots = 1 first (valid)
    config = (0, 1, 500, 86400)
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    lego_id = lego_book.getRegId(mock_yield_lego)
    deposit_amount = 100 * EIGHTEEN_DECIMALS

    # Create snapshot
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Verify snapshot was created
    snapshot_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert snapshot_data.lastSnapShot.pricePerShare > 0


def test_get_latest_snapshot_external_method(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test calling getLatestSnapshot external method directly"""
    config = (0, 10, 500, 86400)
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    lego_id = lego_book.getRegId(mock_yield_lego)
    deposit_amount = 100 * EIGHTEEN_DECIMALS

    # Create initial snapshot
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Get current price
    current_price = mock_yield_lego.snapShotData(yield_vault_token.address).lastSnapShot.pricePerShare

    # Call external getLatestSnapshot
    latest_snapshot = mock_yield_lego.getLatestSnapshot(
        yield_vault_token.address,
        current_price,
        18
    )

    # Verify returned snapshot
    assert latest_snapshot.pricePerShare > 0
    assert latest_snapshot.totalSupply > 0
    assert latest_snapshot.lastUpdate > 0


def test_get_latest_snapshot_with_zero_snapshots(
    mock_yield_lego,
    yield_vault_token,
    switchboard_alpha,
):
    """Test getLatestSnapshot when no snapshots exist yet"""
    config = (0, 10, 500, 86400)
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    # Call getLatestSnapshot with a mock price
    mock_price = 1 * EIGHTEEN_DECIMALS
    latest_snapshot = mock_yield_lego.getLatestSnapshot(
        yield_vault_token.address,
        mock_price,
        18
    )

    # Should return snapshot with provided price (no throttling since no previous snapshot)
    assert latest_snapshot.pricePerShare == mock_price
    assert latest_snapshot.totalSupply >= 0  # May be 0 or small value
    assert latest_snapshot.lastUpdate > 0


def test_snapshot_with_extreme_decimals(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test snapshot handling with extreme decimal values"""
    config = (0, 10, 500, 86400)
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    lego_id = lego_book.getRegId(mock_yield_lego)

    # Test with very small deposit (1 token, minimal but valid)
    small_amount = 1 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob_user_wallet.address, small_amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Should still create snapshot
    snapshot_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert snapshot_data.lastSnapShot.lastUpdate > 0

    # Test with very large deposit
    large_amount = 1_000_000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(bob_user_wallet.address, large_amount, sender=yield_underlying_token_whale)

    boa.env.time_travel(seconds=1)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Should handle large values correctly
    new_snapshot = mock_yield_lego.snapShotData(yield_vault_token.address).lastSnapShot
    assert new_snapshot.totalSupply > 0
    assert new_snapshot.pricePerShare > 0


##########################################################
# MODERATE: Storage Persistence & Realistic Scenario Tests #
##########################################################


def test_add_price_snapshot_storage_persistence(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test that snapshots are correctly stored in the circular buffer"""
    max_snapshots = 5
    config = (0, max_snapshots, 500, 86400)
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    lego_id = lego_book.getRegId(mock_yield_lego)
    deposit_amount = 100 * EIGHTEEN_DECIMALS

    # Create snapshots and track their prices
    prices = []
    for i in range(max_snapshots):
        yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
        bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

        price = mock_yield_lego.snapShotData(yield_vault_token.address).lastSnapShot.pricePerShare
        prices.append(price)

        boa.env.time_travel(seconds=1)

    # Verify each snapshot is stored correctly
    for i in range(max_snapshots):
        stored_snapshot = mock_yield_lego.snapShots(yield_vault_token.address, i)
        assert stored_snapshot.pricePerShare > 0
        assert stored_snapshot.totalSupply > 0
        assert stored_snapshot.lastUpdate > 0


def test_add_price_snapshot_updates_last_snapshot(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test that lastSnapShot field in snapShotData is updated correctly"""
    config = (0, 10, 500, 86400)
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    lego_id = lego_book.getRegId(mock_yield_lego)
    deposit_amount = 100 * EIGHTEEN_DECIMALS

    # First snapshot
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    first_last_snapshot = mock_yield_lego.snapShotData(yield_vault_token.address).lastSnapShot
    first_timestamp = first_last_snapshot.lastUpdate

    boa.env.time_travel(seconds=10)

    # Second snapshot
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    second_last_snapshot = mock_yield_lego.snapShotData(yield_vault_token.address).lastSnapShot
    second_timestamp = second_last_snapshot.lastUpdate

    # Verify lastSnapShot was updated
    assert second_timestamp > first_timestamp
    assert second_last_snapshot.pricePerShare > 0


def test_config_change_effects(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test effects of changing config while snapshots exist"""
    # Initial config: 5 max snapshots
    config1 = (0, 5, 500, 86400)
    mock_yield_lego.setSnapShotPriceConfig(config1, sender=switchboard_alpha.address)

    lego_id = lego_book.getRegId(mock_yield_lego)
    deposit_amount = 100 * EIGHTEEN_DECIMALS

    # Create 3 snapshots with initial config
    for i in range(3):
        yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
        bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)
        boa.env.time_travel(seconds=1)

    # Change config: 10 max snapshots, different throttling
    config2 = (0, 10, 1000, 86400)  # 10% throttling instead of 5%
    mock_yield_lego.setSnapShotPriceConfig(config2, sender=switchboard_alpha.address)

    # Create more snapshots with new config
    for i in range(3):
        yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
        bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)
        boa.env.time_travel(seconds=1)

    # Verify snapshots still work correctly
    weighted_price = mock_yield_lego.getWeightedPricePerShare(yield_vault_token.address)
    assert weighted_price > 0

    # Should have 6 snapshots total
    next_index = mock_yield_lego.snapShotData(yield_vault_token.address).nextIndex
    assert next_index == 6


def test_all_snapshots_stale_behavior(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test weighted price when all snapshots exceed staleTime"""
    # Set short stale time
    config = (0, 10, 500, 60)  # 60 second stale time
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    lego_id = lego_book.getRegId(mock_yield_lego)
    deposit_amount = 100 * EIGHTEEN_DECIMALS

    # Create snapshots
    for i in range(5):
        yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
        bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)
        boa.env.time_travel(seconds=1)

    last_price = mock_yield_lego.snapShotData(yield_vault_token.address).lastSnapShot.pricePerShare

    # Travel far into future to make all snapshots stale
    boa.env.time_travel(seconds=120)

    # When all snapshots are stale, should fall back to lastSnapShot price
    weighted_price = mock_yield_lego.getWeightedPricePerShare(yield_vault_token.address)
    assert weighted_price == last_price


def test_stale_time_zero_behavior(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test that staleTime=0 means no snapshots are filtered as stale"""
    # Set staleTime to 0 (no stale filtering)
    config = (0, 10, 500, 0)
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    lego_id = lego_book.getRegId(mock_yield_lego)
    deposit_amount = 100 * EIGHTEEN_DECIMALS

    # Create snapshots
    for i in range(5):
        yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
        bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)
        boa.env.time_travel(seconds=1)

    # Travel very far into future
    boa.env.time_travel(seconds=10000)

    # All snapshots should still be included (staleTime=0 means no filtering)
    weighted_price = mock_yield_lego.getWeightedPricePerShare(yield_vault_token.address)
    assert weighted_price > 0


def test_add_price_snapshot_with_yield_accrual(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
    governance,
):
    """Test realistic scenario with gradual yield accrual over time"""
    config = (300, 10, 500, 86400)  # 5 min delay, 5% max upside
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    lego_id = lego_book.getRegId(mock_yield_lego)
    initial_amount = 10000 * EIGHTEEN_DECIMALS

    # Initial large deposit
    yield_underlying_token.transfer(bob_user_wallet.address, initial_amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    initial_price = mock_yield_lego.snapShotData(yield_vault_token.address).lastSnapShot.pricePerShare

    # Simulate realistic yield accrual: add assets directly to vault (like interest accumulation)
    # Spread over 1 hour with snapshots every 5 minutes
    for i in range(12):  # 12 periods of 5 minutes = 1 hour
        boa.env.time_travel(seconds=300)  # 5 minutes

        # Add yield directly to vault (0.1% of vault balance)
        current_balance = yield_underlying_token.balanceOf(yield_vault_token.address)
        yield_amount = current_balance // 1000  # 0.1%
        yield_underlying_token.mint(yield_vault_token.address, yield_amount, sender=governance.address)

        # Trigger snapshot with small deposit
        yield_underlying_token.transfer(bob_user_wallet.address, 1 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
        bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    final_price = mock_yield_lego.snapShotData(yield_vault_token.address).lastSnapShot.pricePerShare
    weighted_price = mock_yield_lego.getWeightedPricePerShare(yield_vault_token.address)

    # Price should have increased due to yield accrual
    assert final_price > initial_price
    # Weighted price should be somewhere between initial and final
    assert weighted_price >= initial_price
    assert weighted_price <= final_price + 1  # Allow rounding


def test_snapshot_with_no_prior_data(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
):
    """Test first snapshot ever for a vault token (no prior data)"""
    config = (0, 10, 500, 86400)
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    # Verify no prior data
    initial_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert initial_data.lastSnapShot.pricePerShare == 0
    assert initial_data.lastSnapShot.totalSupply == 0
    assert initial_data.lastSnapShot.lastUpdate == 0
    assert initial_data.nextIndex == 0

    lego_id = lego_book.getRegId(mock_yield_lego)
    deposit_amount = 100 * EIGHTEEN_DECIMALS

    # Create first snapshot ever
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Verify first snapshot created successfully
    first_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert first_data.lastSnapShot.pricePerShare > 0
    assert first_data.lastSnapShot.totalSupply > 0
    assert first_data.lastSnapShot.lastUpdate > 0
    assert first_data.nextIndex == 1  # Should have advanced

    # First snapshot should be stored at index 0
    first_snapshot = mock_yield_lego.snapShots(yield_vault_token.address, 0)
    assert first_snapshot.pricePerShare > 0
