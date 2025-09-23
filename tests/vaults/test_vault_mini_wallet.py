import pytest
import boa

from contracts.core.userWallet import UserWalletConfig
from constants import EIGHTEEN_DECIMALS, MAX_UINT256
from conf_utils import filter_logs
from config.BluePrint import TOKENS


@pytest.fixture(scope="module")
def prepareAssetForWalletTx(undy_usd_vault, bob, yield_underlying_token, yield_underlying_token_whale, mock_ripe):
    def prepareAssetForWalletTx(
        _user = bob,
        _asset = yield_underlying_token,
        _amount = 100 * EIGHTEEN_DECIMALS,
        _whale = yield_underlying_token_whale,
        _vault = undy_usd_vault,
        _price = 1 * EIGHTEEN_DECIMALS,
    ):
        # set price
        mock_ripe.setPrice(_asset, _price)

        # transfer asset to user
        _asset.transfer(_user, _amount, sender=_whale)

        # deposit into earn vault
        _asset.approve(_vault, MAX_UINT256, sender=_user)
        _vault.deposit(_amount, _user, sender=_user)

        return _amount

    yield prepareAssetForWalletTx


#####################
# Deposit for Yield #
#####################


def test_vault_mini_wallet_deposit_for_yield_basic(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token):
    """Test basic deposit for yield functionality"""
    
    # setup: prepare underlying tokens in wallet
    deposit_amount = prepareAssetForWalletTx()
    
    # deposit for yield
    lego_id = 1  # mock_yield_lego is registered with id 1
    asset_deposited, vault_token, vault_tokens_received, usd_value = undy_usd_vault.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # verify event
    log = filter_logs(undy_usd_vault, "EarnVaultAction")[0]
    assert log.op == 10  # EARN_DEPOSIT operation
    assert log.asset1 == yield_underlying_token.address
    assert log.asset2 == yield_vault_token.address
    assert log.amount1 == deposit_amount
    assert log.amount2 == vault_tokens_received
    assert log.usdValue == usd_value
    assert log.legoId == lego_id
    assert log.signer == starter_agent.address

    # verify return values
    assert asset_deposited == deposit_amount
    assert vault_token == yield_vault_token.address
    assert vault_tokens_received > 0
    assert usd_value == 100 * EIGHTEEN_DECIMALS  # 100 tokens * 1 USD
    
    # verify balances
    assert yield_underlying_token.balanceOf(undy_usd_vault) == 0
    assert yield_vault_token.balanceOf(undy_usd_vault) == vault_tokens_received
        
    # verify saved data
    vault_data = undy_usd_vault.assetData(yield_vault_token.address)
    assert vault_data.legoId == lego_id
    assert vault_data.isRebasing == False
    assert vault_data.vaultTokenDecimals == 18
    assert vault_data.avgPricePerShare == EIGHTEEN_DECIMALS

    assert undy_usd_vault.indexOfAsset(yield_vault_token.address) == 1
    assert undy_usd_vault.assets(1) == yield_vault_token.address
    assert undy_usd_vault.numAssets() == 2


def test_vault_mini_wallet_deposit_for_yield_zero_amount(undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token):
    """Test that depositing zero amount or with no balance reverts"""

    # attempt to deposit zero amount (no tokens in vault)
    lego_id = 1
    with boa.reverts("no balance for _token"):
        undy_usd_vault.depositForYield(
            lego_id,
            yield_underlying_token.address,
            yield_vault_token.address,
            0,  # zero amount
            sender=starter_agent.address
        )


def test_vault_mini_wallet_deposit_for_yield_insufficient_balance(undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token, bob, mock_ripe):
    """Test that depositing more than balance reverts"""

    # setup: user has no tokens in vault
    mock_ripe.setPrice(yield_underlying_token, EIGHTEEN_DECIMALS)

    # attempt to deposit without balance
    lego_id = 1
    deposit_amount = 100 * EIGHTEEN_DECIMALS

    with boa.reverts("no balance for _token"):  # Should fail due to no balance
        undy_usd_vault.depositForYield(
            lego_id,
            yield_underlying_token.address,
            yield_vault_token.address,
            deposit_amount,
            sender=starter_agent.address
        )


def test_vault_mini_wallet_deposit_for_yield_unauthorized_caller(prepareAssetForWalletTx, undy_usd_vault, bob, yield_underlying_token, yield_vault_token):
    """Test that only authorized callers can deposit for yield"""

    # setup: prepare underlying tokens in wallet
    deposit_amount = prepareAssetForWalletTx()

    # attempt to deposit from unauthorized address (bob instead of starter_agent)
    lego_id = 1
    with boa.reverts("no permission"):  # Should fail due to no permission
        undy_usd_vault.depositForYield(
            lego_id,
            yield_underlying_token.address,
            yield_vault_token.address,
            deposit_amount,
            sender=bob  # unauthorized
        )


def test_vault_mini_wallet_deposit_for_yield_multiple_sequential(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token):
    """Test multiple sequential deposits for yield"""

    # First deposit
    first_amount = prepareAssetForWalletTx(_amount=50 * EIGHTEEN_DECIMALS)
    lego_id = 1

    _, _, first_vault_tokens, _ = undy_usd_vault.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        first_amount,
        sender=starter_agent.address
    )

    # Get event from first deposit
    first_log = filter_logs(undy_usd_vault, "EarnVaultAction")[0]
    assert first_log.amount1 == first_amount
    assert first_log.amount2 == first_vault_tokens

    # Second deposit
    second_amount = prepareAssetForWalletTx(_amount=30 * EIGHTEEN_DECIMALS)

    _, _, second_vault_tokens, _ = undy_usd_vault.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        second_amount,
        sender=starter_agent.address
    )

    # Get event from second deposit
    second_log = filter_logs(undy_usd_vault, "EarnVaultAction")[0]
    assert second_log.amount1 == second_amount
    assert second_log.amount2 == second_vault_tokens

    # Verify cumulative effects
    total_vault_tokens = first_vault_tokens + second_vault_tokens
    assert yield_vault_token.balanceOf(undy_usd_vault) == total_vault_tokens
    assert yield_underlying_token.balanceOf(undy_usd_vault) == 0


def test_vault_mini_wallet_deposit_for_yield_after_yield_accrual(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token, governance):
    """Test deposit after yield has accrued in the vault"""

    # First deposit
    first_amount = prepareAssetForWalletTx(_amount=100 * EIGHTEEN_DECIMALS)
    lego_id = 1

    _, _, first_vault_tokens, _ = undy_usd_vault.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        first_amount,
        sender=starter_agent.address
    )

    # Record initial average price per share
    initial_vault_data = undy_usd_vault.assetData(yield_vault_token.address)
    initial_avg_price = initial_vault_data.avgPricePerShare
    assert initial_avg_price > 0  # Should have an initial price

    # Time travel to allow snapshot updates (min delay is 5 minutes)
    boa.env.time_travel(seconds=301)  # Travel 5 minutes + 1 second

    # Simulate yield accrual by minting tokens to the yield vault
    # This increases the value of vault tokens
    yield_amount = 20 * EIGHTEEN_DECIMALS
    yield_underlying_token.mint(yield_vault_token.address, yield_amount, sender=governance.address)

    # Second deposit after yield accrual
    second_amount = prepareAssetForWalletTx(_amount=100 * EIGHTEEN_DECIMALS)

    _, _, second_vault_tokens, _ = undy_usd_vault.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        second_amount,
        sender=starter_agent.address
    )

    # Due to yield accrual, second deposit should receive fewer vault tokens for same amount
    # With 20% yield (20 tokens added to 100), vault tokens are now worth 1.2x
    # So for 100 tokens, should get ~83.33 vault tokens (100/1.2)
    expected_second_vault_tokens = (second_amount * first_vault_tokens) // (first_amount + yield_amount)
    assert abs(second_vault_tokens - expected_second_vault_tokens) <= 1  # Allow for rounding

    # Total vault tokens held
    assert yield_vault_token.balanceOf(undy_usd_vault) == first_vault_tokens + second_vault_tokens

    # Verify average price per share tracking
    final_vault_data = undy_usd_vault.assetData(yield_vault_token.address)
    final_avg_price = final_vault_data.avgPricePerShare

    # The avgPricePerShare uses a snapshot mechanism that may require specific conditions
    # to update (like time delays or explicit updates). For now, verify that:
    # 1. The price is being tracked (non-zero)
    assert final_avg_price > 0, f"Average price should be tracked: {final_avg_price}"

    # 2. The current vault token price has increased due to yield
    current_price = yield_vault_token.convertToAssets(EIGHTEEN_DECIMALS)
    expected_price = (first_amount + yield_amount) * EIGHTEEN_DECIMALS // first_vault_tokens
    assert abs(current_price - expected_price) <= 1, f"Current price {current_price} should reflect yield"

    # Note: The avgPricePerShare may not immediately update due to snapshot timing requirements
    # In production, price updates would happen based on the priceConfig settings
    # (minSnapshotDelay, maxNumSnapshots, staleTime, etc.)

    # With time travel, the snapshot MUST update and reflect the new weighted average
    # The average price MUST increase because:
    # 1. First deposit was at 1:1 ratio
    # 2. Second deposit was at ~1.2:1 ratio after yield
    # 3. The weighted average must be between 1.0 and 1.2
    assert final_avg_price > initial_avg_price, \
        f"Average price must increase after yield accrual: {initial_avg_price} -> {final_avg_price}"

    # The increase should be meaningful but less than the full 20% yield
    price_increase_ratio = (final_avg_price - initial_avg_price) * 100 // initial_avg_price
    assert 0 < price_increase_ratio < 20, \
        f"Price increase should be between 0% and 20%, got {price_increase_ratio}%"


def test_vault_mini_wallet_deposit_for_yield_max_amount(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token):
    """Test depositing MAX_UINT256 uses all available balance"""

    # setup: prepare specific amount of tokens
    actual_amount = 75 * EIGHTEEN_DECIMALS
    prepareAssetForWalletTx(_amount=actual_amount)

    # deposit MAX_UINT256 should use all available balance
    lego_id = 1
    asset_deposited, vault_token, vault_tokens_received, usd_value = undy_usd_vault.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        MAX_UINT256,  # max amount
        sender=starter_agent.address
    )

    # verify it used the actual balance
    assert asset_deposited == actual_amount
    assert vault_tokens_received > 0
    assert usd_value == 75 * EIGHTEEN_DECIMALS
    assert yield_underlying_token.balanceOf(undy_usd_vault) == 0
    assert yield_vault_token.balanceOf(undy_usd_vault) == vault_tokens_received


def test_vault_mini_wallet_deposit_for_yield_invalid_lego(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token):
    """Test depositing with invalid/unregistered lego ID"""

    # setup: prepare underlying tokens
    deposit_amount = prepareAssetForWalletTx()

    # attempt with invalid lego ID
    invalid_lego_id = 999  # non-existent lego

    # When lego ID doesn't exist, legoAddr will be empty and fail
    with boa.reverts():  # Will fail when trying to call empty lego address
        undy_usd_vault.depositForYield(
            invalid_lego_id,
            yield_underlying_token.address,
            yield_vault_token.address,
            deposit_amount,
            sender=starter_agent.address
        )


def test_vault_mini_wallet_deposit_for_yield_duplicate_with_different_amounts(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token):
    """Test that multiple deposits to same yield opportunity track correctly"""

    lego_id = 1
    amounts = [25 * EIGHTEEN_DECIMALS, 40 * EIGHTEEN_DECIMALS, 35 * EIGHTEEN_DECIMALS]
    total_deposited = 0
    total_vault_tokens = 0

    for amount in amounts:
        prepareAssetForWalletTx(_amount=amount)

        asset_deposited, _, vault_tokens_received, _ = undy_usd_vault.depositForYield(
            lego_id,
            yield_underlying_token.address,
            yield_vault_token.address,
            amount,
            sender=starter_agent.address
        )

        total_deposited += asset_deposited
        total_vault_tokens += vault_tokens_received

        # Verify running totals
        assert yield_vault_token.balanceOf(undy_usd_vault) == total_vault_tokens

    # Verify final state
    assert total_deposited == sum(amounts)
    vault_data = undy_usd_vault.assetData(yield_vault_token.address)
    assert vault_data.legoId == lego_id

    # All deposits at same price should maintain 1:1 average
    assert vault_data.avgPricePerShare == EIGHTEEN_DECIMALS


def test_vault_mini_wallet_deposit_for_yield_tracking_vault_tokens(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token):
    """Test that vault tokens are properly tracked with legoId and price"""

    lego_id = 1

    # First deposit
    first_amount = prepareAssetForWalletTx(_amount=50 * EIGHTEEN_DECIMALS)
    _, _, vault_tokens_1, _ = undy_usd_vault.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        first_amount,
        sender=starter_agent.address
    )

    # Verify vault token is tracked with correct lego ID
    data = undy_usd_vault.assetData(yield_vault_token.address)
    assert data.legoId == lego_id
    assert data.avgPricePerShare == EIGHTEEN_DECIMALS
    assert data.isRebasing == False
    assert data.vaultTokenDecimals == 18

    # Second deposit to same vault
    second_amount = prepareAssetForWalletTx(_amount=30 * EIGHTEEN_DECIMALS)
    _, _, vault_tokens_2, _ = undy_usd_vault.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        second_amount,
        sender=starter_agent.address
    )

    # Verify cumulative tracking
    total_vault_tokens = vault_tokens_1 + vault_tokens_2
    assert yield_vault_token.balanceOf(undy_usd_vault) == total_vault_tokens

    # Data should still show same lego ID and price
    data = undy_usd_vault.assetData(yield_vault_token.address)
    assert data.legoId == lego_id
    assert data.avgPricePerShare == EIGHTEEN_DECIMALS  # No yield, so price unchanged


def test_vault_mini_wallet_deposit_for_yield_partial_amount(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token):
    """Test depositing partial balance leaves remainder in vault"""

    # Setup: prepare 100 tokens
    total_amount = prepareAssetForWalletTx(_amount=100 * EIGHTEEN_DECIMALS)

    # Deposit only 60 tokens
    deposit_amount = 60 * EIGHTEEN_DECIMALS
    lego_id = 1
    asset_deposited, _, vault_tokens_received, _ = undy_usd_vault.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Verify correct amounts
    assert asset_deposited == deposit_amount
    assert yield_underlying_token.balanceOf(undy_usd_vault) == total_amount - deposit_amount  # 40 tokens remain
    assert yield_vault_token.balanceOf(undy_usd_vault) == vault_tokens_received


def test_vault_mini_wallet_deposit_for_yield_mismatched_vault_token(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, alpha_token):
    """Test that depositing with mismatched vault token fails"""

    deposit_amount = prepareAssetForWalletTx()
    lego_id = 1

    # Try to deposit yield_underlying_token but specify wrong vault token
    # This should fail in the MockYieldLego when it tries to validate the vault token
    with boa.reverts():  # Will fail in lego's validation
        undy_usd_vault.depositForYield(
            lego_id,
            yield_underlying_token.address,
            alpha_token.address,  # Wrong vault token (not an ERC4626 for yield_underlying_token)
            deposit_amount,
            sender=starter_agent.address
        )


def test_vault_mini_wallet_deposit_for_yield_event_verification_detailed(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token):
    """Test detailed event emission for depositForYield"""

    deposit_amount = prepareAssetForWalletTx(_amount=75 * EIGHTEEN_DECIMALS, _price=4 * EIGHTEEN_DECIMALS)
    lego_id = 1

    # Perform deposit
    asset_deposited, vault_token, vault_tokens_received, usd_value = undy_usd_vault.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Get event immediately after transaction
    log = filter_logs(undy_usd_vault, "EarnVaultAction")[0]
    assert log.op == 10  # EARN_DEPOSIT
    assert log.asset1 == yield_underlying_token.address
    assert log.asset2 == yield_vault_token.address
    assert log.amount1 == deposit_amount
    assert log.amount2 == vault_tokens_received
    assert log.usdValue == usd_value
    assert log.legoId == lego_id
    assert log.signer == starter_agent.address

    # Verify USD value calculation
    assert usd_value == 75 * 4 * EIGHTEEN_DECIMALS  # 75 tokens * 4 USD


def test_vault_mini_wallet_deposit_for_yield_small_amount(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token):
    """Test depositing small amounts for precision handling"""

    # Prepare tokens
    prepareAssetForWalletTx(_amount=10 * EIGHTEEN_DECIMALS)

    # Try to deposit a small but reasonable amount (0.001 tokens)
    lego_id = 1
    small_amount = EIGHTEEN_DECIMALS // 1000  # 0.001 tokens
    asset_deposited, _, vault_tokens_received, _ = undy_usd_vault.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        small_amount,
        sender=starter_agent.address
    )

    # Should handle small amount correctly
    assert asset_deposited == small_amount
    assert vault_tokens_received > 0  # Should get some vault tokens


def test_vault_mini_wallet_deposit_yield_then_withdraw_simulation(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token, governance):
    """Test deposit for yield followed by simulated withdrawal flow"""

    # Initial deposit
    deposit_amount = prepareAssetForWalletTx(_amount=100 * EIGHTEEN_DECIMALS)
    lego_id = 1

    _, _, vault_tokens, _ = undy_usd_vault.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    initial_vault_data = undy_usd_vault.assetData(yield_vault_token.address)

    # Simulate yield accrual (20% gain)
    yield_amount = 20 * EIGHTEEN_DECIMALS
    yield_underlying_token.mint(yield_vault_token.address, yield_amount, sender=governance.address)

    # Calculate expected value after yield
    # Vault tokens should now be worth 120% of original
    expected_value = (deposit_amount * 120) // 100
    actual_value = yield_vault_token.convertToAssets(vault_tokens)
    assert abs(actual_value - expected_value) < EIGHTEEN_DECIMALS // 100  # Within 1%

    # Verify avgPricePerShare hasn't changed (no new deposits)
    vault_data = undy_usd_vault.assetData(yield_vault_token.address)
    assert vault_data.avgPricePerShare == initial_vault_data.avgPricePerShare
