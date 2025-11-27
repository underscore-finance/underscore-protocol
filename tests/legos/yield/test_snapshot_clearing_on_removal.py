"""Test for L-02: Clearing a vault token opportunity clears its snapshots"""

import pytest
import boa
from constants import EIGHTEEN_DECIMALS, MAX_UINT256


def test_snapshot_clearing_on_opportunity_removal(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
    env
):
    """
    Test that removing an asset opportunity properly clears all snapshot data.
    This addresses audit finding L-02.
    """

    # Configure snapshots to allow multiple
    config = (
        300,   # minSnapshotDelay
        10,    # maxNumSnapshots
        500,   # maxUpsideDeviation (5%)
        86400,  # staleTime (1 day)
    )
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    lego_id = lego_book.getRegId(mock_yield_lego)
    deposit_amount = 100 * EIGHTEEN_DECIMALS

    # Step 1: Create initial snapshots by depositing multiple times
    for i in range(3):
        yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
        bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

        # Time travel to allow next snapshot
        env.time_travel(seconds=301)

    # Verify snapshots were created
    snapshot_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert snapshot_data.nextIndex == 3, "Should have 3 snapshots"

    # Verify individual snapshots exist
    for i in range(3):
        snapshot = mock_yield_lego.snapShots(yield_vault_token.address, i)
        assert snapshot.pricePerShare > 0, f"Snapshot {i} should exist with price > 0"
        assert snapshot.totalSupply > 0, f"Snapshot {i} should have totalSupply > 0"

    # Step 2: Withdraw all funds
    vault_balance = yield_vault_token.balanceOf(bob_user_wallet.address)
    bob_user_wallet.withdrawFromYield(lego_id, yield_vault_token, vault_balance, sender=bob)

    # Step 3: Remove the asset opportunity (deregister the vault token)
    # This should now clear all snapshot data due to our fix
    mock_yield_lego.deregisterVaultTokenLocally(
        yield_underlying_token.address,
        yield_vault_token.address,
        sender=switchboard_alpha.address
    )

    # Step 4: Verify snapshots were cleared
    snapshot_data_after = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert snapshot_data_after.nextIndex == 0, "NextIndex should be reset to 0"
    assert snapshot_data_after.lastSnapShot.pricePerShare == 0, "Last snapshot should be cleared"
    assert snapshot_data_after.lastSnapShot.totalSupply == 0, "Last snapshot supply should be 0"
    assert snapshot_data_after.lastSnapShot.lastUpdate == 0, "Last snapshot update time should be 0"

    # Verify individual snapshots are cleared
    for i in range(3):
        snapshot = mock_yield_lego.snapShots(yield_vault_token.address, i)
        assert snapshot.pricePerShare == 0, f"Snapshot {i} should be cleared (price = 0)"
        assert snapshot.totalSupply == 0, f"Snapshot {i} should be cleared (supply = 0)"
        assert snapshot.lastUpdate == 0, f"Snapshot {i} should be cleared (lastUpdate = 0)"

    # Step 5: Re-add the same vault token and deposit again
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Step 6: Verify new snapshot starts fresh (no contamination from old data)
    new_snapshot_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert new_snapshot_data.nextIndex == 1, "Should have exactly 1 new snapshot"
    assert new_snapshot_data.lastSnapShot.pricePerShare > 0, "New snapshot should have valid price"

    # First snapshot slot should be the new one
    first_snapshot = mock_yield_lego.snapShots(yield_vault_token.address, 0)
    assert first_snapshot.pricePerShare > 0, "First snapshot should be the new one"

    # Other slots should still be empty (not contaminated with old data)
    for i in range(1, 3):
        snapshot = mock_yield_lego.snapShots(yield_vault_token.address, i)
        assert snapshot.pricePerShare == 0, f"Snapshot slot {i} should remain empty"

    # Step 7: Verify weighted price calculation uses only new data
    weighted_price = mock_yield_lego.getWeightedPricePerShare(yield_vault_token.address)
    assert weighted_price == new_snapshot_data.lastSnapShot.pricePerShare, \
        "Weighted price should equal the single new snapshot price (no old data contamination)"


def test_snapshot_clearing_with_stale_time_zero(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
    env
):
    """
    Test snapshot clearing when staleTime is 0 (snapshots never go stale).
    This is a critical edge case mentioned in the audit finding.
    """

    # Configure with staleTime = 0 (snapshots never expire)
    config = (
        300,   # minSnapshotDelay
        10,    # maxNumSnapshots
        500,   # maxUpsideDeviation (5%)
        0,     # staleTime = 0 (never stale)
    )
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    lego_id = lego_book.getRegId(mock_yield_lego)
    deposit_amount = 100 * EIGHTEEN_DECIMALS

    # Create multiple snapshots
    for i in range(3):
        yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
        bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)
        env.time_travel(seconds=301)

    # Record the old price
    old_snapshot_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    old_price = old_snapshot_data.lastSnapShot.pricePerShare

    # Time travel far into the future
    env.time_travel(seconds=365 * 24 * 3600)  # 1 year

    # Without our fix, these old snapshots would still be valid after re-adding
    # because staleTime = 0 means they never expire

    # Withdraw all
    vault_balance = yield_vault_token.balanceOf(bob_user_wallet.address)
    bob_user_wallet.withdrawFromYield(lego_id, yield_vault_token, vault_balance, sender=bob)

    # Remove opportunity
    mock_yield_lego.deregisterVaultTokenLocally(
        yield_underlying_token.address,
        yield_vault_token.address,
        sender=switchboard_alpha.address
    )

    # Re-add the vault token by depositing again
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount * 2, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Verify weighted price is ONLY based on new snapshot, not contaminated by old ones
    weighted_price = mock_yield_lego.getWeightedPricePerShare(yield_vault_token.address)
    current_snapshot_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    current_price = current_snapshot_data.lastSnapShot.pricePerShare

    # The weighted price should equal the current price (only 1 new snapshot)
    assert weighted_price == current_price, \
        "With staleTime=0, old snapshots would contaminate the average if not properly cleared"

    # Also verify we only have 1 snapshot now, not 4 (3 old + 1 new)
    assert current_snapshot_data.nextIndex == 1, "Should only have 1 new snapshot, not old ones"


def test_snapshot_clearing_with_full_buffer(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
    env
):
    """
    Test snapshot clearing when the circular buffer is completely full.
    This ensures we properly clear all snapshots even at maximum capacity.
    """

    # Configure with a small buffer for easier testing
    max_snapshots = 5
    config = (
        10,    # minSnapshotDelay (short for faster testing)
        max_snapshots,    # maxNumSnapshots
        500,   # maxUpsideDeviation (5%)
        86400,  # staleTime (1 day)
    )
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    lego_id = lego_book.getRegId(mock_yield_lego)
    deposit_amount = 10 * EIGHTEEN_DECIMALS

    # Fill the circular buffer completely and wrap around
    for i in range(max_snapshots + 2):  # Overfill to test wraparound
        yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
        bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)
        env.time_travel(seconds=11)

    # Verify buffer wrapped around
    snapshot_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    # nextIndex should have wrapped: (max_snapshots + 2) % max_snapshots = 2
    expected_next_index = (max_snapshots + 2) % max_snapshots
    assert snapshot_data.nextIndex == expected_next_index, f"Buffer should have wrapped to index {expected_next_index}"

    # Verify all slots have data
    for i in range(max_snapshots):
        snapshot = mock_yield_lego.snapShots(yield_vault_token.address, i)
        assert snapshot.pricePerShare > 0, f"Snapshot {i} should have data"

    # Withdraw all
    vault_balance = yield_vault_token.balanceOf(bob_user_wallet.address)
    bob_user_wallet.withdrawFromYield(lego_id, yield_vault_token, vault_balance, sender=bob)

    # Remove opportunity
    mock_yield_lego.deregisterVaultTokenLocally(
        yield_underlying_token.address,
        yield_vault_token.address,
        sender=switchboard_alpha.address
    )

    # Verify ALL snapshots were cleared, even with wrapped buffer
    for i in range(max_snapshots):
        snapshot = mock_yield_lego.snapShots(yield_vault_token.address, i)
        assert snapshot.pricePerShare == 0, f"Snapshot {i} should be cleared"
        assert snapshot.totalSupply == 0, f"Snapshot {i} totalSupply should be 0"
        assert snapshot.lastUpdate == 0, f"Snapshot {i} lastUpdate should be 0"

    # Verify snapshot data is reset
    cleared_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert cleared_data.nextIndex == 0, "NextIndex should be reset"
    assert cleared_data.lastSnapShot.pricePerShare == 0, "Last snapshot should be cleared"


def test_snapshot_clearing_multiple_vault_tokens(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    yield_vault_token_2,
    switchboard_alpha,
    env
):
    """
    Test that removing one vault token's opportunity doesn't affect another's snapshots.
    This ensures snapshot clearing is properly isolated per vault token.
    """

    config = (
        10,    # minSnapshotDelay
        10,    # maxNumSnapshots
        500,   # maxUpsideDeviation (5%)
        86400,  # staleTime (1 day)
    )
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    lego_id = lego_book.getRegId(mock_yield_lego)
    deposit_amount = 50 * EIGHTEEN_DECIMALS

    # Create snapshots for both vault tokens
    for vault_token in [yield_vault_token, yield_vault_token_2]:
        for i in range(3):
            yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
            bob_user_wallet.depositForYield(lego_id, yield_underlying_token, vault_token, MAX_UINT256, sender=bob)
            env.time_travel(seconds=11)

    # Verify both have snapshots
    data1 = mock_yield_lego.snapShotData(yield_vault_token.address)
    data2 = mock_yield_lego.snapShotData(yield_vault_token_2.address)
    assert data1.nextIndex == 3, "Vault token 1 should have 3 snapshots"
    assert data2.nextIndex == 3, "Vault token 2 should have 3 snapshots"

    # Withdraw from vault token 1 only
    balance1 = yield_vault_token.balanceOf(bob_user_wallet.address)
    bob_user_wallet.withdrawFromYield(lego_id, yield_vault_token, balance1, sender=bob)

    # Remove opportunity for vault token 1 only
    mock_yield_lego.deregisterVaultTokenLocally(
        yield_underlying_token.address,
        yield_vault_token.address,
        sender=switchboard_alpha.address
    )

    # Verify vault token 1 snapshots are cleared
    data1_after = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert data1_after.nextIndex == 0, "Vault token 1 snapshots should be cleared"

    for i in range(3):
        snapshot = mock_yield_lego.snapShots(yield_vault_token.address, i)
        assert snapshot.pricePerShare == 0, f"Vault token 1 snapshot {i} should be cleared"

    # Verify vault token 2 snapshots are UNTOUCHED
    data2_after = mock_yield_lego.snapShotData(yield_vault_token_2.address)
    assert data2_after.nextIndex == 3, "Vault token 2 should still have 3 snapshots"
    assert data2_after.lastSnapShot.pricePerShare > 0, "Vault token 2 last snapshot should be intact"

    for i in range(3):
        snapshot = mock_yield_lego.snapShots(yield_vault_token_2.address, i)
        assert snapshot.pricePerShare > 0, f"Vault token 2 snapshot {i} should still exist"


def test_rapid_remove_readd_cycle(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
    env
):
    """
    Test rapid remove and re-add cycles to ensure no state pollution.
    This simulates a scenario where a vault might be quickly removed and re-added.
    """

    config = (
        0,     # minSnapshotDelay = 0 for rapid testing
        10,    # maxNumSnapshots
        500,   # maxUpsideDeviation (5%)
        3600,  # staleTime (1 hour)
    )
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    lego_id = lego_book.getRegId(mock_yield_lego)
    deposit_amount = 20 * EIGHTEEN_DECIMALS

    # Cycle 1: Add snapshots
    for i in range(3):
        yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
        bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)
        env.time_travel(seconds=1)

    cycle1_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    cycle1_price = cycle1_data.lastSnapShot.pricePerShare
    assert cycle1_data.nextIndex == 3, "Should have 3 snapshots in cycle 1"

    # Remove
    vault_balance = yield_vault_token.balanceOf(bob_user_wallet.address)
    bob_user_wallet.withdrawFromYield(lego_id, yield_vault_token, vault_balance, sender=bob)
    mock_yield_lego.deregisterVaultTokenLocally(
        yield_underlying_token.address,
        yield_vault_token.address,
        sender=switchboard_alpha.address
    )

    # Immediately re-add (no time travel)
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Verify clean slate
    cycle2_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert cycle2_data.nextIndex == 1, "Should have exactly 1 new snapshot after re-add"

    # Add more snapshots in cycle 2
    for i in range(2):
        env.time_travel(seconds=1)
        yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
        bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    cycle2_final_data = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert cycle2_final_data.nextIndex == 3, "Should have 3 new snapshots in cycle 2"

    # Verify weighted price is based only on cycle 2 snapshots
    weighted_price = mock_yield_lego.getWeightedPricePerShare(yield_vault_token.address)

    # The weighted price should be close to the current price (all new snapshots)
    # and not influenced by cycle 1 snapshots
    current_price = cycle2_final_data.lastSnapShot.pricePerShare
    assert abs(weighted_price - current_price) < current_price // 100, \
        "Weighted price should be based only on new snapshots, not old ones"


def test_snapshot_clearing_with_max_config_boundary(
    bob_user_wallet,
    bob,
    mock_yield_lego,
    lego_book,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    switchboard_alpha,
    env
):
    """
    Test snapshot clearing with maxNumSnapshots at boundary values (1 and 25).
    Ensures the clearing logic works correctly at configuration limits.
    """

    lego_id = lego_book.getRegId(mock_yield_lego)
    deposit_amount = 10 * EIGHTEEN_DECIMALS

    # Test with minimum allowed snapshots (1)
    config = (10, 1, 500, 86400)  # maxNumSnapshots = 1
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    # Add snapshot
    yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
    bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)

    # Remove and verify clearing
    vault_balance = yield_vault_token.balanceOf(bob_user_wallet.address)
    bob_user_wallet.withdrawFromYield(lego_id, yield_vault_token, vault_balance, sender=bob)
    mock_yield_lego.deregisterVaultTokenLocally(
        yield_underlying_token.address,
        yield_vault_token.address,
        sender=switchboard_alpha.address
    )

    data = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert data.nextIndex == 0, "Single snapshot should be cleared"
    snapshot = mock_yield_lego.snapShots(yield_vault_token.address, 0)
    assert snapshot.pricePerShare == 0, "Snapshot at index 0 should be cleared"

    # Test with maximum allowed snapshots (25)
    config = (10, 25, 500, 86400)  # maxNumSnapshots = 25
    mock_yield_lego.setSnapShotPriceConfig(config, sender=switchboard_alpha.address)

    # Fill all 25 slots
    for i in range(25):
        yield_underlying_token.transfer(bob_user_wallet.address, deposit_amount, sender=yield_underlying_token_whale)
        bob_user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, MAX_UINT256, sender=bob)
        env.time_travel(seconds=11)

    # Verify all 25 snapshots exist
    data_before = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert data_before.nextIndex == 25 % 25, "Should have wrapped around to index 0"

    # Remove and verify all 25 are cleared
    vault_balance = yield_vault_token.balanceOf(bob_user_wallet.address)
    bob_user_wallet.withdrawFromYield(lego_id, yield_vault_token, vault_balance, sender=bob)
    mock_yield_lego.deregisterVaultTokenLocally(
        yield_underlying_token.address,
        yield_vault_token.address,
        sender=switchboard_alpha.address
    )

    data_after = mock_yield_lego.snapShotData(yield_vault_token.address)
    assert data_after.nextIndex == 0, "All 25 snapshots should be cleared"

    for i in range(25):
        snapshot = mock_yield_lego.snapShots(yield_vault_token.address, i)
        assert snapshot.pricePerShare == 0, f"Snapshot {i} of 25 should be cleared"