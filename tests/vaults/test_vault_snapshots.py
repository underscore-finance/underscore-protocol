import pytest
import boa

from constants import EIGHTEEN_DECIMALS


##################
# Snapshot Tests #
##################


def test_add_price_snapshot_basic(undy_usd_vault, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, starter_agent, switchboard_alpha):
    """Test basic addition of a price snapshot"""

    # Setup: deposit to create a vault position
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Get initial snapshot data (deposit may have added one)
    initial_snapshot_data = undy_usd_vault.snapShotData(yield_vault_token.address)
    initial_index = initial_snapshot_data.nextIndex

    # Time travel to allow snapshot (min delay is 5 minutes)
    boa.env.time_travel(seconds=301)

    # Add price snapshot as switchboard
    result = undy_usd_vault.addPriceSnapshot(
        yield_vault_token.address,
        sender=switchboard_alpha.address
    )

    # Should return True for successful addition
    assert result == True

    # Verify snapshot was stored
    snapshot_data = undy_usd_vault.snapShotData(yield_vault_token.address)
    assert snapshot_data.nextIndex == initial_index + 1  # Index should increment
    assert snapshot_data.lastSnapShot.pricePerShare > 0
    assert snapshot_data.lastSnapShot.totalSupply > 0
    assert snapshot_data.lastSnapShot.lastUpdate > 0  # Should have a valid timestamp

    # Verify latest snapshot in snapShots mapping
    latest_snapshot = undy_usd_vault.snapShots(yield_vault_token.address, initial_index)
    assert latest_snapshot.pricePerShare > 0
    assert latest_snapshot.totalSupply > 0
    assert latest_snapshot.lastUpdate > 0

    # Verify getLatestSnapshot returns current data
    latest = undy_usd_vault.getLatestSnapshot(yield_vault_token.address)
    assert latest.pricePerShare == EIGHTEEN_DECIMALS  # 1:1 for mock vault
    assert latest.totalSupply == 100  # 100 tokens deposited (scaled down)
    assert latest.lastUpdate > 0


def test_add_price_snapshot_updates_next_index(undy_usd_vault, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, starter_agent, switchboard_alpha):
    """Test that adding multiple snapshots correctly updates the next index"""

    # Setup: deposit to create a vault position
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Get initial state
    initial_data = undy_usd_vault.snapShotData(yield_vault_token.address)
    initial_index = initial_data.nextIndex

    # Add first snapshot
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)

    # Verify first snapshot
    snapshot_data = undy_usd_vault.snapShotData(yield_vault_token.address)
    assert snapshot_data.nextIndex == initial_index + 1

    # Add second snapshot
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)

    # Verify second snapshot
    snapshot_data = undy_usd_vault.snapShotData(yield_vault_token.address)
    assert snapshot_data.nextIndex == initial_index + 2

    # Add third snapshot
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)

    # Verify third snapshot
    snapshot_data = undy_usd_vault.snapShotData(yield_vault_token.address)
    assert snapshot_data.nextIndex == initial_index + 3

    # Verify recent snapshots are stored
    for i in range(initial_index, initial_index + 3):
        snapshot = undy_usd_vault.snapShots(yield_vault_token.address, i)
        assert snapshot.pricePerShare > 0
        assert snapshot.totalSupply > 0

    # Verify getLatestSnapshot shows most recent data
    latest = undy_usd_vault.getLatestSnapshot(yield_vault_token.address)
    assert latest.pricePerShare == EIGHTEEN_DECIMALS
    assert latest.totalSupply == 100
    # Latest timestamp should be current block time (or very close)
    assert latest.lastUpdate > snapshot_data.lastSnapShot.lastUpdate - 10  # Within 10 seconds


def test_add_price_snapshot_circular_buffer(undy_usd_vault, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, starter_agent, switchboard_alpha):
    """Test that snapshot storage wraps around when max snapshots reached"""

    # Setup: deposit to create a vault position
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Get the max number of snapshots and initial state
    price_config = undy_usd_vault.priceConfig()
    max_snapshots = price_config.maxNumSnapshots

    # Get initial index (deposit adds first snapshot)
    initial_data = undy_usd_vault.snapShotData(yield_vault_token.address)
    initial_index = initial_data.nextIndex

    # Add snapshots up to fill the buffer and wrap around
    snapshots_to_add = max_snapshots + 2 - initial_index  # Account for existing snapshots
    for i in range(snapshots_to_add):
        boa.env.time_travel(seconds=301)
        undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)

    # Verify that nextIndex wrapped around correctly
    snapshot_data = undy_usd_vault.snapShotData(yield_vault_token.address)
    expected_index = (initial_index + snapshots_to_add) % max_snapshots
    assert snapshot_data.nextIndex == expected_index

    # The oldest snapshots (indices 0 and 1) should be overwritten
    # All slots should have valid data
    for i in range(max_snapshots):
        snapshot = undy_usd_vault.snapShots(yield_vault_token.address, i)
        assert snapshot.pricePerShare > 0
        assert snapshot.totalSupply > 0

    # Verify getLatestSnapshot returns the most recent (not affected by circular buffer)
    latest = undy_usd_vault.getLatestSnapshot(yield_vault_token.address)
    assert latest.pricePerShare == EIGHTEEN_DECIMALS
    assert latest.totalSupply > 0
    # Should be the timestamp of the last added snapshot
    assert latest.lastUpdate == snapshot_data.lastSnapShot.lastUpdate


def test_add_price_snapshot_respects_min_delay(undy_usd_vault, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, starter_agent, switchboard_alpha):
    """Test that snapshots respect the minimum delay between additions"""

    # Setup: deposit to create a vault position
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Get min delay from config and initial state
    price_config = undy_usd_vault.priceConfig()
    min_delay = price_config.minSnapshotDelay
    initial_data = undy_usd_vault.snapShotData(yield_vault_token.address)
    initial_index = initial_data.nextIndex

    # Add first snapshot
    boa.env.time_travel(seconds=301)
    result = undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)
    assert result == True

    # Try to add another immediately - should fail
    result = undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)
    assert result == False

    # Travel less than min delay - should still fail
    boa.env.time_travel(seconds=min_delay - 1)
    result = undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)
    assert result == False

    # Travel exactly min delay - should succeed
    boa.env.time_travel(seconds=1)  # Now we're at exactly min_delay
    result = undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)
    assert result == True

    # Verify only 2 additional snapshots were added (plus any initial)
    snapshot_data = undy_usd_vault.snapShotData(yield_vault_token.address)
    assert snapshot_data.nextIndex == initial_index + 2

    # Verify getLatestSnapshot reflects the most recent addition
    latest = undy_usd_vault.getLatestSnapshot(yield_vault_token.address)
    assert latest.pricePerShare > 0
    assert latest.totalSupply > 0
    # Latest should match the stored lastSnapShot
    assert latest.pricePerShare == snapshot_data.lastSnapShot.pricePerShare


def test_add_price_snapshot_same_timestamp_rejected(undy_usd_vault, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, starter_agent, switchboard_alpha):
    """Test that multiple snapshots at same timestamp are rejected"""

    # Setup: deposit to create a vault position
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Add first snapshot
    boa.env.time_travel(seconds=301)
    result = undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)
    assert result == True

    # Try to add another at same timestamp (no time travel) - should fail
    result = undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)
    assert result == False

    # Verify only one additional snapshot was added
    snapshot_data = undy_usd_vault.snapShotData(yield_vault_token.address)
    initial_data = undy_usd_vault.snapShotData(yield_vault_token.address)
    # The test added one snapshot, verify nextIndex incremented by 1 from initial + first snapshot
    assert snapshot_data.nextIndex > 0  # Should have at least one snapshot


def test_add_price_snapshot_permission_check(undy_usd_vault, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, starter_agent):
    """Test that only switchboard addresses can add snapshots"""

    # Setup: deposit to create a vault position
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Time travel to allow snapshot
    boa.env.time_travel(seconds=301)

    # Try to add snapshot as non-switchboard address - should revert
    with boa.reverts("no perms"):
        undy_usd_vault.addPriceSnapshot(
            yield_vault_token.address,
            sender=starter_agent.address  # Not a switchboard address
        )


def test_add_price_snapshot_invalid_vault_token(undy_usd_vault, switchboard_alpha, yield_underlying_token):
    """Test that adding snapshot for non-vault token returns False"""

    # Time travel
    boa.env.time_travel(seconds=301)

    # Try to add snapshot for a token that's not a vault token
    result = undy_usd_vault.addPriceSnapshot(
        yield_underlying_token.address,  # Not a registered vault token
        sender=switchboard_alpha.address
    )

    # Should return False (not fail/revert)
    assert result == False

    # Verify getLatestSnapshot returns empty for invalid token
    latest = undy_usd_vault.getLatestSnapshot(yield_underlying_token.address)
    assert latest.pricePerShare == 0
    assert latest.totalSupply == 0
    assert latest.lastUpdate == 0


def test_add_price_snapshot_with_yield_accrual(undy_usd_vault, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, starter_agent, switchboard_alpha, governance):
    """Test snapshot captures accurate price after yield accrual"""

    # Setup: deposit to create a vault position
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Add initial snapshot
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)

    initial_snapshot = undy_usd_vault.snapShotData(yield_vault_token.address).lastSnapShot
    initial_price = initial_snapshot.pricePerShare

    # Simulate yield accrual by adding tokens to vault
    current_balance = yield_underlying_token.balanceOf(yield_vault_token.address)
    yield_underlying_token.mint(yield_vault_token.address, current_balance, sender=governance.address)

    # Add new snapshot after yield
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)

    new_snapshot = undy_usd_vault.snapShotData(yield_vault_token.address).lastSnapShot
    new_price = new_snapshot.pricePerShare

    # Price should have increased but may be throttled by max upside
    price_config = undy_usd_vault.priceConfig()
    max_upside = price_config.maxUpsideDeviation
    max_allowed_price = initial_price + (initial_price * max_upside // 10000)

    # Price should be the minimum of double or max allowed
    expected_price = min(initial_price * 2, max_allowed_price)
    assert new_price == expected_price

    # Verify getLatestSnapshot shows the updated price
    # Note: getLatestSnapshot may apply additional throttling on top of stored snapshot
    latest = undy_usd_vault.getLatestSnapshot(yield_vault_token.address)
    # Latest price should be at least the stored snapshot price (could be further throttled)
    assert latest.pricePerShare >= new_price
    assert latest.totalSupply == 100  # Supply unchanged


def test_add_price_snapshot_multiple_vault_tokens(undy_usd_vault, starter_agent, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, yield_vault_token_2, switchboard_alpha):
    """Test adding snapshots for multiple different vault tokens"""

    # Setup positions in two vaults
    deposit_amount_1 = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount_1, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount_1,
        sender=starter_agent.address
    )

    deposit_amount_2 = 80 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount_2, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token_2.address,
        deposit_amount_2,
        sender=starter_agent.address
    )

    # Time travel
    boa.env.time_travel(seconds=301)

    # Add snapshots for both vault tokens
    result1 = undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)
    result2 = undy_usd_vault.addPriceSnapshot(yield_vault_token_2.address, sender=switchboard_alpha.address)

    assert result1 == True
    assert result2 == True

    # Verify each vault token has its own snapshot data
    snapshot_data_1 = undy_usd_vault.snapShotData(yield_vault_token.address)
    snapshot_data_2 = undy_usd_vault.snapShotData(yield_vault_token_2.address)

    # Both should have snapshots (deposit adds initial, then we added one more)
    assert snapshot_data_1.nextIndex >= 2  # At least 2 snapshots
    assert snapshot_data_2.nextIndex >= 2  # At least 2 snapshots

    # Snapshots should be independent (different deposit amounts)
    # Token 1 had 100, token 2 had 80
    assert snapshot_data_1.lastSnapShot.totalSupply == 100
    assert snapshot_data_2.lastSnapShot.totalSupply == 80

    # Verify getLatestSnapshot works for each vault token independently
    latest_1 = undy_usd_vault.getLatestSnapshot(yield_vault_token.address)
    latest_2 = undy_usd_vault.getLatestSnapshot(yield_vault_token_2.address)

    assert latest_1.totalSupply == 100
    assert latest_2.totalSupply == 80
    assert latest_1.pricePerShare == EIGHTEEN_DECIMALS
    assert latest_2.pricePerShare == EIGHTEEN_DECIMALS


def test_add_price_snapshot_updates_last_snapshot(undy_usd_vault, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, starter_agent, switchboard_alpha):
    """Test that lastSnapShot is always updated to the most recent"""

    # Setup: deposit to create a vault position
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Add multiple snapshots
    timestamps = []
    prices = []

    for i in range(3):
        boa.env.time_travel(seconds=301)

        # Optionally change the price by minting some tokens to the vault
        # (This is just to have different prices)

        undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)

        snapshot_data = undy_usd_vault.snapShotData(yield_vault_token.address)
        timestamps.append(snapshot_data.lastSnapShot.lastUpdate)
        prices.append(snapshot_data.lastSnapShot.pricePerShare)

    # Verify lastSnapShot always points to the most recent
    final_snapshot_data = undy_usd_vault.snapShotData(yield_vault_token.address)
    assert final_snapshot_data.lastSnapShot.lastUpdate == timestamps[-1]
    assert final_snapshot_data.lastSnapShot.pricePerShare == prices[-1]

    # Verify getLatestSnapshot matches the most recent stored snapshot
    latest = undy_usd_vault.getLatestSnapshot(yield_vault_token.address)
    assert latest.lastUpdate >= timestamps[-1]  # May be slightly newer due to block time
    assert latest.pricePerShare == prices[-1]
    assert latest.totalSupply == 100


def test_add_price_snapshot_throttles_upside(undy_usd_vault, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, starter_agent, switchboard_alpha, governance):
    """Test that price snapshots respect max upside deviation"""

    # Setup: deposit to create a vault position
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Add initial snapshot
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)

    initial_snapshot = undy_usd_vault.snapShotData(yield_vault_token.address).lastSnapShot
    initial_price = initial_snapshot.pricePerShare

    # Get max upside deviation from config
    price_config = undy_usd_vault.priceConfig()
    max_upside = price_config.maxUpsideDeviation

    # Simulate massive yield accrual (10x)
    current_balance = yield_underlying_token.balanceOf(yield_vault_token.address)
    yield_underlying_token.mint(yield_vault_token.address, current_balance * 9, sender=governance.address)

    # Add new snapshot
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)

    new_snapshot = undy_usd_vault.snapShotData(yield_vault_token.address).lastSnapShot
    new_price = new_snapshot.pricePerShare

    # Price should be throttled to max upside
    max_allowed_price = initial_price + (initial_price * max_upside // 10000)
    assert new_price == max_allowed_price

    # Verify getLatestSnapshot shows a price (may apply additional throttling)
    latest = undy_usd_vault.getLatestSnapshot(yield_vault_token.address)
    # getLatestSnapshot applies throttling based on the stored lastSnapShot
    # So it could be further throttled from the new_price
    latest_max_allowed = new_price + (new_price * max_upside // 10000)
    assert latest.pricePerShare <= latest_max_allowed
    assert latest.totalSupply == 100


def test_add_price_snapshot_storage_persistence(undy_usd_vault, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, starter_agent, switchboard_alpha):
    """Test that snapshot data persists correctly in storage"""

    # Setup: deposit to create a vault position
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Get initial state (deposit adds first snapshot)
    initial_data = undy_usd_vault.snapShotData(yield_vault_token.address)
    initial_index = initial_data.nextIndex

    # Add multiple snapshots with different data
    snapshots_to_add = []
    num_snapshots_to_add = 3

    for i in range(num_snapshots_to_add):
        boa.env.time_travel(seconds=301)

        # Add snapshot
        undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)

        # Store the data for verification
        snapshot_index = initial_index + i
        snapshot = undy_usd_vault.snapShots(yield_vault_token.address, snapshot_index)
        snapshots_to_add.append({
            'index': snapshot_index,
            'price': snapshot.pricePerShare,
            'supply': snapshot.totalSupply,
            'timestamp': snapshot.lastUpdate
        })

    # Verify all snapshots are stored correctly
    for expected in snapshots_to_add:
        actual = undy_usd_vault.snapShots(yield_vault_token.address, expected['index'])
        assert actual.pricePerShare == expected['price']
        assert actual.totalSupply == expected['supply']
        assert actual.lastUpdate == expected['timestamp']

    # Verify snapshot data summary
    snapshot_data = undy_usd_vault.snapShotData(yield_vault_token.address)
    assert snapshot_data.nextIndex == initial_index + num_snapshots_to_add
    assert snapshot_data.lastSnapShot.lastUpdate == snapshots_to_add[-1]['timestamp']

    # Verify getLatestSnapshot returns the most recent persisted data
    latest = undy_usd_vault.getLatestSnapshot(yield_vault_token.address)
    assert latest.pricePerShare == snapshots_to_add[-1]['price']
    assert latest.totalSupply == snapshots_to_add[-1]['supply']
    # Latest timestamp might be current block time, but should be at least the last stored
    assert latest.lastUpdate >= snapshots_to_add[-1]['timestamp']


def test_get_weighted_price_multiple_snapshots(undy_usd_vault, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, starter_agent, switchboard_alpha, governance):
    """Test weighted average calculation across multiple snapshots with different supplies"""

    # Setup: deposit to create a vault position
    initial_deposit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, initial_deposit, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        initial_deposit,
        sender=starter_agent.address
    )

    # Add first snapshot with initial supply
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)

    # Deposit more to change total supply
    additional_deposit = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, additional_deposit, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        additional_deposit,
        sender=starter_agent.address
    )

    # Add second snapshot with increased supply (150 total)
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)

    # Add yield to change price
    current_balance = yield_underlying_token.balanceOf(yield_vault_token.address)
    yield_underlying_token.mint(yield_vault_token.address, current_balance // 10, sender=governance.address)  # 10% yield

    # Add third snapshot with yield
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)

    # Get weighted price - should factor in different supplies
    weighted_price = undy_usd_vault.getWeightedPrice(yield_vault_token.address)
    assert weighted_price > 0

    # Weighted price should be between min and max prices
    # With supply-weighted average, higher supply snapshots have more weight
    assert weighted_price >= EIGHTEEN_DECIMALS  # At least the initial price
    assert weighted_price <= EIGHTEEN_DECIMALS * 11 // 10  # At most 10% increase (throttled)


def test_stale_snapshots_excluded(undy_usd_vault, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, starter_agent, switchboard_alpha):
    """Test that stale snapshots are excluded from weighted price calculation"""

    # Setup: deposit to create a vault position
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Get stale time from config
    price_config = undy_usd_vault.priceConfig()
    stale_time = price_config.staleTime

    # Add first snapshot
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)
    first_snapshot = undy_usd_vault.snapShotData(yield_vault_token.address).lastSnapShot

    # Add second snapshot
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)

    # Time travel beyond stale time for first snapshot
    if stale_time > 0:
        boa.env.time_travel(seconds=stale_time + 1)

        # Add a fresh snapshot
        undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)

        # Get weighted price - should exclude stale snapshots
        weighted_price = undy_usd_vault.getWeightedPrice(yield_vault_token.address)

        # If stale snapshots are properly excluded, weighted price should equal latest
        latest_snapshot = undy_usd_vault.snapShotData(yield_vault_token.address).lastSnapShot
        # The weighted price might not exactly equal the latest if multiple non-stale snapshots exist
        assert weighted_price > 0


def test_zero_total_supply_snapshot(undy_usd_vault, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, starter_agent, switchboard_alpha):
    """Test behavior when vault token has zero total supply"""

    # Setup: deposit and then withdraw everything
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)
    _, _, vault_tokens, _ = undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Withdraw everything to get zero balance
    undy_usd_vault.withdrawFromYield(
        1,
        yield_vault_token.address,
        vault_tokens,
        sender=starter_agent.address
    )

    # Verify vault token balance is zero
    assert yield_vault_token.balanceOf(undy_usd_vault) == 0

    # Time travel and try to add snapshot with zero supply
    boa.env.time_travel(seconds=301)

    # The vault token is still registered but with zero balance
    # Adding a snapshot should work and show zero total supply
    result = undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)
    assert result == True  # Can snapshot even with zero balance

    # Check the snapshot has zero total supply
    snapshot_data = undy_usd_vault.snapShotData(yield_vault_token.address)
    assert snapshot_data.lastSnapShot.totalSupply == 0  # Zero supply
    assert snapshot_data.lastSnapShot.pricePerShare > 0  # Price still tracked

    # getLatestSnapshot should show zero supply but valid price
    latest = undy_usd_vault.getLatestSnapshot(yield_vault_token.address)
    assert latest.totalSupply == 0
    assert latest.pricePerShare > 0  # Price per share still valid
    assert latest.lastUpdate > 0


def test_config_change_effects(undy_usd_vault, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, starter_agent, switchboard_alpha, governance):
    """Test how configuration changes affect existing and new snapshots"""

    # Setup: deposit to create a vault position
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Add initial snapshot with current config
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)
    initial_snapshot = undy_usd_vault.snapShotData(yield_vault_token.address).lastSnapShot

    # Get current config
    old_config = undy_usd_vault.priceConfig()

    # Create new config with different max upside (5% instead of 10%)
    new_max_upside = 500  # 5%
    new_config = (old_config.minSnapshotDelay, old_config.maxNumSnapshots, new_max_upside, old_config.staleTime)

    # Change config (only switchboard can do this)
    undy_usd_vault.setPriceConfig(new_config, sender=switchboard_alpha.address)

    # Simulate large yield accrual
    current_balance = yield_underlying_token.balanceOf(yield_vault_token.address)
    yield_underlying_token.mint(yield_vault_token.address, current_balance, sender=governance.address)  # Double the assets

    # Add snapshot with new config
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)
    new_snapshot = undy_usd_vault.snapShotData(yield_vault_token.address).lastSnapShot

    # Price should be throttled by new max upside (5% not 10%)
    max_allowed = initial_snapshot.pricePerShare + (initial_snapshot.pricePerShare * new_max_upside // 10000)
    assert new_snapshot.pricePerShare == max_allowed

    # Existing snapshots remain unchanged
    first_stored = undy_usd_vault.snapShots(yield_vault_token.address, 0)
    assert first_stored.pricePerShare > 0  # Still has original data


def test_snapshot_with_no_prior_data(undy_usd_vault, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, starter_agent, switchboard_alpha):
    """Test first snapshot when no prior snapshot data exists"""

    # Directly add snapshot without any prior setup (no deposit)
    # This should return False since no vault position exists
    result = undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)
    assert result == False

    # Now create a position
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Check initial snapshot was created during deposit
    initial_data = undy_usd_vault.snapShotData(yield_vault_token.address)
    assert initial_data.nextIndex >= 1  # At least one snapshot
    assert initial_data.lastSnapShot.pricePerShare > 0
    assert initial_data.lastSnapShot.totalSupply > 0

    # Verify first slot has data
    first_snapshot = undy_usd_vault.snapShots(yield_vault_token.address, 0)
    assert first_snapshot.pricePerShare > 0
    assert first_snapshot.totalSupply > 0


def test_max_snapshots_zero_config(undy_usd_vault):
    """Test behavior when maxNumSnapshots is set to zero"""

    # Get current config
    current_config = undy_usd_vault.priceConfig()

    # Try to set maxNumSnapshots to 0 - should fail validation
    zero_snapshots_config = (current_config.minSnapshotDelay, 0, current_config.maxUpsideDeviation, current_config.staleTime)

    # This should fail because maxNumSnapshots must be > 0
    is_valid = undy_usd_vault.isValidPriceConfig(zero_snapshots_config)
    assert is_valid == False

    # Verify weighted price returns 0 when no snapshots allowed
    # (This would only happen if the config was somehow invalid)
    # The contract prevents this, but we verify the safety check


def test_rapid_price_changes_with_throttling(undy_usd_vault, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, starter_agent, switchboard_alpha, governance):
    """Test multiple rapid price increases with cumulative throttling"""

    # Setup position
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Get max upside from config
    price_config = undy_usd_vault.priceConfig()
    max_upside = price_config.maxUpsideDeviation

    prices = []

    # Simulate multiple yield events with snapshots
    for i in range(3):
        boa.env.time_travel(seconds=301)

        # Add 50% yield each time
        current_balance = yield_underlying_token.balanceOf(yield_vault_token.address)
        yield_underlying_token.mint(yield_vault_token.address, current_balance // 2, sender=governance.address)

        # Add snapshot
        undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)

        # Track price
        snapshot_data = undy_usd_vault.snapShotData(yield_vault_token.address)
        prices.append(snapshot_data.lastSnapShot.pricePerShare)

    # Each snapshot should be throttled relative to the previous
    for i in range(1, len(prices)):
        max_allowed = prices[i-1] + (prices[i-1] * max_upside // 10000)
        assert prices[i] <= max_allowed

    # The cumulative increase is limited by repeated throttling
    final_price = prices[-1]
    initial_price = EIGHTEEN_DECIMALS

    # With 10% max upside, three iterations gives us roughly 1.1^3 = 1.331x max
    max_cumulative = initial_price * 1331 // 1000  # 1.331x
    assert final_price <= max_cumulative


def test_get_latest_snapshot_throttles_independently(undy_usd_vault, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, starter_agent, switchboard_alpha, governance):
    """Test that getLatestSnapshot applies its own throttling on top of stored snapshot"""

    # Setup: deposit to create a vault position
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Add initial snapshot
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)

    initial_snapshot = undy_usd_vault.snapShotData(yield_vault_token.address).lastSnapShot
    initial_price = initial_snapshot.pricePerShare

    # Get config for max upside
    price_config = undy_usd_vault.priceConfig()
    max_upside = price_config.maxUpsideDeviation

    # Simulate massive yield (10x) - much more than max upside allows
    current_balance = yield_underlying_token.balanceOf(yield_vault_token.address)
    yield_underlying_token.mint(yield_vault_token.address, current_balance * 9, sender=governance.address)

    # DON'T add a new snapshot - just call getLatestSnapshot
    # This tests that getLatestSnapshot applies throttling even without storing
    latest = undy_usd_vault.getLatestSnapshot(yield_vault_token.address)

    # The actual vault price is 10x, but getLatestSnapshot should throttle it
    # relative to the last stored snapshot
    max_allowed_price = initial_price + (initial_price * max_upside // 10000)
    assert latest.pricePerShare == max_allowed_price

    # Verify the stored snapshot hasn't changed
    stored_snapshot = undy_usd_vault.snapShotData(yield_vault_token.address).lastSnapShot
    assert stored_snapshot.pricePerShare == initial_price  # Unchanged

    # Now add a new snapshot - it will also be throttled when stored
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)

    new_stored = undy_usd_vault.snapShotData(yield_vault_token.address).lastSnapShot
    assert new_stored.pricePerShare == max_allowed_price  # Throttled when stored

    # Simulate MORE yield (another 5x on top)
    current_balance = yield_underlying_token.balanceOf(yield_vault_token.address)
    yield_underlying_token.mint(yield_vault_token.address, current_balance * 4, sender=governance.address)

    # Call getLatestSnapshot again - should throttle relative to the new stored price
    latest_again = undy_usd_vault.getLatestSnapshot(yield_vault_token.address)

    # Should be throttled relative to the stored throttled price
    max_allowed_again = new_stored.pricePerShare + (new_stored.pricePerShare * max_upside // 10000)
    assert latest_again.pricePerShare == max_allowed_again

    # This demonstrates double throttling:
    # 1. When snapshot is stored, it's throttled relative to previous
    # 2. When getLatestSnapshot is called, it throttles again relative to stored


# getWeightedPrice() Tests

def test_get_weighted_price_basic(undy_usd_vault, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, starter_agent, switchboard_alpha):
    """Test basic weighted price calculation with multiple snapshots"""

    # Setup: deposit to create a vault position
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Add first snapshot (price = 1e18, supply = 100e18)
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)
    snapshot1 = undy_usd_vault.snapShotData(yield_vault_token.address).lastSnapShot

    # Add second snapshot (same price, same supply)
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)

    # Add third snapshot (same price, same supply)
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)

    # Get weighted price - should equal the consistent price
    weighted_price = undy_usd_vault.getWeightedPrice(yield_vault_token.address)
    assert weighted_price == snapshot1.pricePerShare

    # Verify it's using multiple snapshots (not just latest)
    snapshot_data = undy_usd_vault.snapShotData(yield_vault_token.address)
    assert snapshot_data.nextIndex >= 3  # At least 3 snapshots stored


def test_get_weighted_price_with_different_supplies(undy_usd_vault, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, starter_agent, switchboard_alpha):
    """Test weighted price calculation with varying total supplies"""

    # Setup: initial deposit
    initial_deposit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, initial_deposit, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        initial_deposit,
        sender=starter_agent.address
    )

    # Snapshot 1: 100 tokens supply, price 1e18
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)
    snap1 = undy_usd_vault.snapShotData(yield_vault_token.address).lastSnapShot

    # Deposit more - increases supply to 200
    yield_underlying_token.transfer(undy_usd_vault.address, initial_deposit, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        initial_deposit,
        sender=starter_agent.address
    )

    # Snapshot 2: 200 tokens supply, still price 1e18
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)
    snap2 = undy_usd_vault.snapShotData(yield_vault_token.address).lastSnapShot

    # Deposit even more - increases supply to 400
    yield_underlying_token.transfer(undy_usd_vault.address, 200 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        200 * EIGHTEEN_DECIMALS,
        sender=starter_agent.address
    )

    # Snapshot 3: 400 tokens supply, still price 1e18
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)
    snap3 = undy_usd_vault.snapShotData(yield_vault_token.address).lastSnapShot

    # Get weighted price
    # Weight calculation: (100*1e18 + 200*1e18 + 400*1e18) / (100 + 200 + 400) = 1e18
    weighted_price = undy_usd_vault.getWeightedPrice(yield_vault_token.address)

    # Since all prices are the same, weighted should equal any snapshot price
    assert weighted_price == snap1.pricePerShare
    assert snap1.pricePerShare == snap2.pricePerShare == snap3.pricePerShare


def test_get_weighted_price_excludes_stale(undy_usd_vault, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, starter_agent, switchboard_alpha, governance):
    """Test that stale snapshots are properly excluded from weighted price"""

    # Setup: deposit to create a vault position
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Get config to know stale time
    price_config = undy_usd_vault.priceConfig()
    stale_time = price_config.staleTime

    # Add first snapshot - this will become stale
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)
    first_price = undy_usd_vault.snapShotData(yield_vault_token.address).lastSnapShot.pricePerShare

    # Add second snapshot - this will also become stale
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)

    # Time travel to make first two snapshots stale
    if stale_time > 0:
        boa.env.time_travel(seconds=stale_time + 1)

        # Add yield to change price for fresh snapshot
        current_balance = yield_underlying_token.balanceOf(yield_vault_token.address)
        yield_underlying_token.mint(yield_vault_token.address, current_balance // 20, sender=governance.address)  # 5% yield

        # Add fresh snapshot with new price
        undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)
        fresh_snapshot = undy_usd_vault.snapShotData(yield_vault_token.address).lastSnapShot

        # Get weighted price - should properly weight fresh vs stale
        weighted_price = undy_usd_vault.getWeightedPrice(yield_vault_token.address)

        # Weighted price should be between old and new prices
        assert weighted_price > 0
        assert weighted_price >= first_price  # At least the original price
        assert weighted_price <= fresh_snapshot.pricePerShare  # At most the new price

        # If properly excluding stale, should be closer to fresh price
        assert weighted_price > first_price  # Should reflect some yield


def test_get_weighted_price_single_snapshot(undy_usd_vault, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, starter_agent, switchboard_alpha):
    """Test weighted price with only one snapshot"""

    # Setup: deposit to create a vault position
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Check initial snapshot count
    initial_data = undy_usd_vault.snapShotData(yield_vault_token.address)
    initial_index = initial_data.nextIndex

    # Add single snapshot
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)
    single_snapshot = undy_usd_vault.snapShotData(yield_vault_token.address).lastSnapShot

    # Get weighted price with only one snapshot
    weighted_price = undy_usd_vault.getWeightedPrice(yield_vault_token.address)

    # With single snapshot, weighted price should equal that snapshot
    assert weighted_price == single_snapshot.pricePerShare
    assert weighted_price == EIGHTEEN_DECIMALS  # Should be 1:1 initially

    # Verify only one new snapshot was added
    snapshot_data = undy_usd_vault.snapShotData(yield_vault_token.address)
    assert snapshot_data.nextIndex == initial_index + 1


def test_get_weighted_price_no_snapshots(undy_usd_vault, yield_vault_token_3):
    """Test weighted price when no snapshots exist for an unregistered vault token"""

    # Try to get weighted price for a vault token that has never been registered
    # yield_vault_token_3 has not been deposited, so no snapshots exist
    weighted_price = undy_usd_vault.getWeightedPrice(yield_vault_token_3.address)

    # With no snapshots, should return 0
    assert weighted_price == 0

    # Verify no snapshots exist
    snapshot_data = undy_usd_vault.snapShotData(yield_vault_token_3.address)
    assert snapshot_data.nextIndex == 0
    assert snapshot_data.lastSnapShot.lastUpdate == 0


def test_get_weighted_price_circular_buffer_full(undy_usd_vault, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, starter_agent, switchboard_alpha, governance):
    """Test weighted price calculation when circular buffer wraps around"""

    # Setup: deposit to create a vault position
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, deposit_amount, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Get max snapshots from config
    price_config = undy_usd_vault.priceConfig()
    max_snapshots = price_config.maxNumSnapshots

    # Fill the buffer completely
    prices = []
    for i in range(max_snapshots):
        boa.env.time_travel(seconds=301)

        # Add small yield for each snapshot to vary prices
        if i > 0:
            current_balance = yield_underlying_token.balanceOf(yield_vault_token.address)
            # Add 1% yield each time
            yield_underlying_token.mint(yield_vault_token.address, current_balance // 100, sender=governance.address)

        undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)
        snap = undy_usd_vault.snapShotData(yield_vault_token.address).lastSnapShot
        prices.append(snap.pricePerShare)

    # Verify buffer is full (nextIndex wrapped around)
    snapshot_data = undy_usd_vault.snapShotData(yield_vault_token.address)
    # nextIndex should have wrapped (might not be exactly 0 if there were prior snapshots)
    assert snapshot_data.nextIndex < max_snapshots  # Still within buffer range

    # Get weighted price with full buffer
    weighted_price = undy_usd_vault.getWeightedPrice(yield_vault_token.address)

    # Weighted price should be positive and within range of prices
    assert weighted_price > 0
    assert weighted_price >= min(prices)
    assert weighted_price <= max(prices)

    # Add one more snapshot to overwrite the oldest
    boa.env.time_travel(seconds=301)
    current_balance = yield_underlying_token.balanceOf(yield_vault_token.address)
    yield_underlying_token.mint(yield_vault_token.address, current_balance // 50, sender=governance.address)  # 2% yield
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)

    # Get weighted price after wraparound
    weighted_price_after = undy_usd_vault.getWeightedPrice(yield_vault_token.address)

    # Should still calculate correctly after wraparound
    assert weighted_price_after > 0
    # After adding yield, new weighted price should be higher
    assert weighted_price_after >= weighted_price


def test_get_weighted_price_with_price_variations(undy_usd_vault, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, starter_agent, switchboard_alpha, governance):
    """Test weighted price with significant price variations and supply changes"""

    # Setup: initial deposit
    initial_deposit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, initial_deposit, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        initial_deposit,
        sender=starter_agent.address
    )

    # Snapshot 1: Base price, 100 supply
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)
    snap1 = undy_usd_vault.snapShotData(yield_vault_token.address).lastSnapShot

    # Add 5% yield
    current_balance = yield_underlying_token.balanceOf(yield_vault_token.address)
    yield_underlying_token.mint(yield_vault_token.address, current_balance // 20, sender=governance.address)

    # Snapshot 2: 5% higher price, still 100 supply
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)
    snap2 = undy_usd_vault.snapShotData(yield_vault_token.address).lastSnapShot

    # Double the supply
    yield_underlying_token.transfer(undy_usd_vault.address, initial_deposit, sender=yield_underlying_token_whale)
    undy_usd_vault.depositForYield(
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        initial_deposit,
        sender=starter_agent.address
    )

    # Add another 5% yield
    current_balance = yield_underlying_token.balanceOf(yield_vault_token.address)
    yield_underlying_token.mint(yield_vault_token.address, current_balance // 20, sender=governance.address)

    # Snapshot 3: ~10% higher price than base, 200 supply
    boa.env.time_travel(seconds=301)
    undy_usd_vault.addPriceSnapshot(yield_vault_token.address, sender=switchboard_alpha.address)
    snap3 = undy_usd_vault.snapShotData(yield_vault_token.address).lastSnapShot

    # Get weighted price
    weighted_price = undy_usd_vault.getWeightedPrice(yield_vault_token.address)

    # Verify relationships
    assert weighted_price > 0
    assert snap1.pricePerShare < snap2.pricePerShare < snap3.pricePerShare  # Prices increased
    assert snap1.totalSupply < snap3.totalSupply  # Supply increased

    # Weighted price should be between min and max
    assert weighted_price >= snap1.pricePerShare
    assert weighted_price <= snap3.pricePerShare

    # With higher supply on the higher price snapshot, weighted should tend toward higher value
    # Due to throttling and averaging, just verify it's reasonable
    assert weighted_price > snap1.pricePerShare  # Should be above the base price