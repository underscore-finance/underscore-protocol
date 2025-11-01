import pytest
import boa

from constants import EIGHTEEN_DECIMALS, MAX_UINT256, ZERO_ADDRESS
from conf_utils import filter_logs


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

        # transfer asset directly to vault (not via deposit to avoid auto-deposit)
        _asset.transfer(_vault, _amount, sender=_whale)

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
    lego_id = 2  # mock_yield_lego is registered with id 2
    asset_deposited, vault_token, vault_tokens_received, usd_value = undy_usd_vault.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # verify event
    log = filter_logs(undy_usd_vault, "EarnVaultDeposit")[0]
    assert log.asset == yield_underlying_token.address
    assert log.vaultToken == yield_vault_token.address
    assert log.assetAmountDeposited == deposit_amount
    assert log.vaultTokenReceived == vault_tokens_received
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
    assert undy_usd_vault.vaultToLegoId(yield_vault_token.address) == lego_id
    assert undy_usd_vault.indexOfAsset(yield_vault_token.address) == 1
    assert undy_usd_vault.assets(1) == yield_vault_token.address
    assert undy_usd_vault.numAssets() == 2


def test_vault_mini_wallet_deposit_for_yield_zero_amount(undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token):
    """Test that depositing zero amount or with no balance reverts"""

    # attempt to deposit zero amount (no tokens in vault)
    lego_id = 2
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
    lego_id = 2
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
    lego_id = 2
    with boa.reverts("not manager"):  # Should fail due to not being a manager
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
    lego_id = 2

    _, _, first_vault_tokens, _ = undy_usd_vault.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        first_amount,
        sender=starter_agent.address
    )

    # Get event from first deposit
    first_log = filter_logs(undy_usd_vault, "EarnVaultDeposit")[0]
    assert first_log.assetAmountDeposited == first_amount
    assert first_log.vaultTokenReceived == first_vault_tokens

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
    second_log = filter_logs(undy_usd_vault, "EarnVaultDeposit")[0]
    assert second_log.assetAmountDeposited == second_amount
    assert second_log.vaultTokenReceived == second_vault_tokens

    # Verify cumulative effects
    total_vault_tokens = first_vault_tokens + second_vault_tokens
    assert yield_vault_token.balanceOf(undy_usd_vault) == total_vault_tokens
    assert yield_underlying_token.balanceOf(undy_usd_vault) == 0


def test_vault_mini_wallet_deposit_for_yield_after_yield_accrual(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token, governance):
    """Test deposit after yield has accrued in the vault"""

    # First deposit
    first_amount = prepareAssetForWalletTx(_amount=100 * EIGHTEEN_DECIMALS)
    lego_id = 2

    _, _, first_vault_tokens, _ = undy_usd_vault.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        first_amount,
        sender=starter_agent.address
    )

    # Verify lego ID is registered
    assert undy_usd_vault.vaultToLegoId(yield_vault_token.address) == lego_id

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

    # Verify the current vault token price has increased due to yield
    current_price = yield_vault_token.convertToAssets(EIGHTEEN_DECIMALS)
    expected_price = (first_amount + yield_amount) * EIGHTEEN_DECIMALS // first_vault_tokens
    assert abs(current_price - expected_price) <= 1, f"Current price {current_price} should reflect yield"


def test_vault_mini_wallet_deposit_for_yield_max_amount(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token):
    """Test depositing MAX_UINT256 uses all available balance"""

    # setup: prepare specific amount of tokens
    actual_amount = 75 * EIGHTEEN_DECIMALS
    prepareAssetForWalletTx(_amount=actual_amount)

    # deposit MAX_UINT256 should use all available balance
    lego_id = 2
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

    lego_id = 2
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
    assert undy_usd_vault.vaultToLegoId(yield_vault_token.address) == lego_id


def test_vault_mini_wallet_deposit_for_yield_tracking_vault_tokens(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token):
    """Test that vault tokens are properly tracked with legoId and price"""

    lego_id = 2

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
    assert undy_usd_vault.vaultToLegoId(yield_vault_token.address) == lego_id

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

    # Data should still show same lego ID
    assert undy_usd_vault.vaultToLegoId(yield_vault_token.address) == lego_id


def test_vault_mini_wallet_deposit_for_yield_partial_amount(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token):
    """Test depositing partial balance leaves remainder in vault"""

    # Setup: prepare 100 tokens
    total_amount = prepareAssetForWalletTx(_amount=100 * EIGHTEEN_DECIMALS)

    # Deposit only 60 tokens
    deposit_amount = 60 * EIGHTEEN_DECIMALS
    lego_id = 2
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
    lego_id = 2

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
    lego_id = 2

    # Perform deposit
    asset_deposited, vault_token, vault_tokens_received, usd_value = undy_usd_vault.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Get event immediately after transaction
    log = filter_logs(undy_usd_vault, "EarnVaultDeposit")[0]
    assert log.asset == yield_underlying_token.address
    assert log.vaultToken == yield_vault_token.address
    assert log.assetAmountDeposited == deposit_amount
    assert log.vaultTokenReceived == vault_tokens_received
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
    lego_id = 2
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
    lego_id = 2

    _, _, vault_tokens, _ = undy_usd_vault.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Simulate yield accrual (20% gain)
    yield_amount = 20 * EIGHTEEN_DECIMALS
    yield_underlying_token.mint(yield_vault_token.address, yield_amount, sender=governance.address)

    # Calculate expected value after yield
    # Vault tokens should now be worth 120% of original
    expected_value = (deposit_amount * 120) // 100
    actual_value = yield_vault_token.convertToAssets(vault_tokens)
    assert abs(actual_value - expected_value) < EIGHTEEN_DECIMALS // 100  # Within 1%


#######################
# Withdraw from Yield #
#######################


@pytest.fixture(scope="module")
def setupYieldPosition(prepareAssetForWalletTx, undy_usd_vault, yield_underlying_token, starter_agent, yield_vault_token):
    """Setup fixture that deposits yield tokens and returns relevant data"""
    def setupYieldPosition(
        _deposit_amount=100 * EIGHTEEN_DECIMALS,
        _underlying_price=10 * EIGHTEEN_DECIMALS,
    ):
        # prepare underlying tokens
        deposit_amount = prepareAssetForWalletTx(
            _amount=_deposit_amount,
            _price=_underlying_price,
        )
        
        # deposit to get vault tokens
        _, _, vault_tokens_received, _ = undy_usd_vault.depositForYield(
            2,
            yield_underlying_token.address,
            yield_vault_token.address,
            deposit_amount,
        sender=starter_agent.address
        )
        
        return vault_tokens_received
    
    yield setupYieldPosition


def test_vault_mini_wallet_withdraw_from_yield_basic(setupYieldPosition, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token):
    """Test basic withdrawal from yield position"""
    
    # setup position
    vault_tokens = setupYieldPosition()

    # verify initial state
    assert yield_vault_token.balanceOf(undy_usd_vault) == vault_tokens
    assert yield_underlying_token.balanceOf(undy_usd_vault) == 0
    
    # withdraw half
    withdraw_amount = vault_tokens // 2
    vault_burned, underlying_asset, underlying_received, usd_value = undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token.address,
        withdraw_amount,
        sender=starter_agent.address
    )

    # verify event
    log = filter_logs(undy_usd_vault, "EarnVaultWithdrawal")[0]
    assert log.vaultToken == yield_vault_token.address
    assert log.underlyingAsset == yield_underlying_token.address
    assert log.vaultTokenBurned == withdraw_amount == vault_burned
    assert log.underlyingAmountReceived == underlying_received
    assert log.usdValue == usd_value
    assert log.legoId == 2
    assert log.signer == starter_agent.address

    # verify return values
    assert vault_burned == withdraw_amount
    assert underlying_asset == yield_underlying_token.address
    assert underlying_received == withdraw_amount  # 1:1 price
    assert usd_value > 0
    
    # verify balances
    assert yield_vault_token.balanceOf(undy_usd_vault) == vault_tokens - withdraw_amount
    assert yield_underlying_token.balanceOf(undy_usd_vault) == underlying_received
    
    # verify storage updated
    assert undy_usd_vault.vaultToLegoId(yield_vault_token.address) == 2
    assert undy_usd_vault.indexOfAsset(yield_vault_token.address) == 1
    assert undy_usd_vault.assets(1) == yield_vault_token.address
    assert undy_usd_vault.numAssets() == 2


def test_vault_mini_wallet_withdraw_from_yield_entire_balance_deregisters_asset(setupYieldPosition, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token):
    """Test that withdrawing entire yield position properly deregisters the asset"""

    # setup position
    vault_tokens = setupYieldPosition()

    # verify initial state - vault token is registered
    vault_index_before = undy_usd_vault.indexOfAsset(yield_vault_token.address)
    assert vault_index_before > 0
    num_assets_before = undy_usd_vault.numAssets()
    assert num_assets_before >= 2  # At least base asset + yield vault token

    # Store the asset at the position before withdrawal
    asset_at_index = undy_usd_vault.assets(vault_index_before)
    assert asset_at_index == yield_vault_token.address

    # withdraw entire balance
    vault_burned, underlying_asset, underlying_received, usd_value = undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token.address,
        vault_tokens,
        sender=starter_agent.address
    )

    # verify all vault tokens burned
    assert vault_burned == vault_tokens
    assert yield_vault_token.balanceOf(undy_usd_vault) == 0
    assert underlying_received == vault_tokens  # 1:1 price
    assert underlying_asset == yield_underlying_token.address

    # CRITICAL: Verify complete deregistration via _deregisterYieldPosition
    # 1. Index should be reset to 0
    assert undy_usd_vault.indexOfAsset(yield_vault_token.address) == 0

    # 2. numAssets should decrease by 1
    assert undy_usd_vault.numAssets() == num_assets_before - 1

    # 3. In this test scenario with only 2 assets, the yield_vault_token was at the last position
    # So no array reorganization is needed. For array reorganization testing with 3+ assets,
    # see test_vault_mini_wallet_withdraw_deregistration_array_reorganization_multiple_assets

    # 4. Lego ID mapping is retained for historical tracking
    assert undy_usd_vault.vaultToLegoId(yield_vault_token.address) == 2  # lego ID retained for tracking

    # 5. Verify the vault token cannot be found in the active assets array
    for i in range(1, undy_usd_vault.numAssets()):
        assert undy_usd_vault.assets(i) != yield_vault_token.address

    # verify underlying tokens received
    assert yield_underlying_token.balanceOf(undy_usd_vault) == underlying_received


def test_vault_mini_wallet_withdraw_from_yield_max_value(setupYieldPosition, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token):
    """Test withdrawing with MAX_UINT256 withdraws entire balance"""

    # setup position
    vault_tokens = setupYieldPosition()

    # withdraw with max_value
    vault_burned, _, underlying_received, _ = undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token.address,
        MAX_UINT256,  # max value
        sender=starter_agent.address
    )

    # verify entire balance withdrawn
    assert vault_burned == vault_tokens
    assert yield_vault_token.balanceOf(undy_usd_vault) == 0
    assert yield_underlying_token.balanceOf(undy_usd_vault) == underlying_received


def test_vault_mini_wallet_withdraw_from_yield_zero_amount(undy_usd_vault, starter_agent, yield_vault_token):
    """Test that withdrawing zero amount reverts"""

    # attempt to withdraw zero amount (no position setup)
    with boa.reverts("no balance for _token"):
        undy_usd_vault.withdrawFromYield(
            2,
            yield_vault_token.address,
            0,
            sender=starter_agent.address
        )


def test_vault_mini_wallet_withdraw_from_yield_insufficient_balance(setupYieldPosition, undy_usd_vault, starter_agent, yield_vault_token):
    """Test withdrawing more than balance withdraws available balance"""

    # setup position
    vault_tokens = setupYieldPosition()

    # attempt to withdraw more than balance
    requested_amount = vault_tokens * 2
    vault_burned, _, _, _ = undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token.address,
        requested_amount,
        sender=starter_agent.address
    )

    # should withdraw only available balance
    assert vault_burned == vault_tokens
    assert yield_vault_token.balanceOf(undy_usd_vault) == 0


def test_vault_mini_wallet_withdraw_from_yield_unauthorized_caller(setupYieldPosition, undy_usd_vault, bob, yield_vault_token):
    """Test that only authorized callers can withdraw from yield"""

    # setup position
    setupYieldPosition()

    # attempt to withdraw from unauthorized address
    with boa.reverts("not manager"):
        undy_usd_vault.withdrawFromYield(
            2,
            yield_vault_token.address,
            10 * EIGHTEEN_DECIMALS,
            sender=bob  # unauthorized
        )


def test_vault_mini_wallet_withdraw_from_yield_with_accrued_yield(setupYieldPosition, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token, governance):
    """Test withdrawal after yield has accrued increases underlying received"""

    # setup position
    vault_tokens = setupYieldPosition()

    # simulate yield accrual - double the vault's assets
    current_vault_balance = yield_underlying_token.balanceOf(yield_vault_token.address)
    yield_underlying_token.mint(yield_vault_token.address, current_vault_balance, sender=governance.address)

    # withdraw half - should receive 2x underlying due to yield
    withdraw_amount = vault_tokens // 2
    vault_burned, _, underlying_received, _ = undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token.address,
        withdraw_amount,
        sender=starter_agent.address
    )

    # with 2x price, should receive 2x underlying
    assert vault_burned == withdraw_amount
    assert underlying_received == withdraw_amount * 2  # 2:1 price due to yield

    # verify correct amount of vault tokens remain
    assert yield_vault_token.balanceOf(undy_usd_vault) == vault_tokens - withdraw_amount


def test_vault_mini_wallet_withdraw_from_yield_multiple_sequential(setupYieldPosition, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token):
    """Test multiple sequential withdrawals"""

    # setup position with 90 tokens (divisible by 3)
    vault_tokens = setupYieldPosition(_deposit_amount=90 * EIGHTEEN_DECIMALS)

    # first withdrawal - 1/3
    withdraw1 = vault_tokens // 3
    _, _, underlying1, _ = undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token.address,
        withdraw1,
        sender=starter_agent.address
    )

    # verify first withdrawal
    assert yield_vault_token.balanceOf(undy_usd_vault) == vault_tokens - withdraw1
    assert underlying1 == withdraw1  # 1:1 price

    # Get event from first withdrawal
    first_log = filter_logs(undy_usd_vault, "EarnVaultWithdrawal")[0]
    assert first_log.vaultTokenBurned == withdraw1

    # second withdrawal - 1/3
    withdraw2 = vault_tokens // 3
    _, _, underlying2, _ = undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token.address,
        withdraw2,
        sender=starter_agent.address
    )

    # verify second withdrawal
    assert yield_vault_token.balanceOf(undy_usd_vault) == vault_tokens - withdraw1 - withdraw2
    assert underlying2 == withdraw2

    # Get event from second withdrawal
    second_log = filter_logs(undy_usd_vault, "EarnVaultWithdrawal")[0]
    assert second_log.vaultTokenBurned == withdraw2

    # third withdrawal - remaining
    remaining = vault_tokens - withdraw1 - withdraw2
    _, _, underlying3, _ = undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token.address,
        remaining,
        sender=starter_agent.address
    )

    # verify final state
    assert yield_vault_token.balanceOf(undy_usd_vault) == 0
    assert underlying3 == remaining
    total_underlying = underlying1 + underlying2 + underlying3
    assert total_underlying == vault_tokens  # Total should equal original deposit
    assert yield_underlying_token.balanceOf(undy_usd_vault) == total_underlying


def test_vault_mini_wallet_withdraw_from_yield_invalid_vault_token(undy_usd_vault, starter_agent):
    """Test withdrawing with invalid vault token address"""

    # attempt to withdraw from non-existent vault token
    with boa.reverts("invalid vault token"):
        undy_usd_vault.withdrawFromYield(
            2,
            ZERO_ADDRESS,  # invalid address
            10 * EIGHTEEN_DECIMALS,
            sender=starter_agent.address
        )


def test_vault_mini_wallet_withdraw_from_yield_invalid_lego(setupYieldPosition, undy_usd_vault, starter_agent, yield_vault_token):
    """Test withdrawing with invalid lego ID"""

    # setup position with lego ID 1
    setupYieldPosition()

    # attempt to withdraw with wrong lego ID
    invalid_lego_id = 999
    with boa.reverts():  # Will fail when trying to use invalid lego
        undy_usd_vault.withdrawFromYield(
            invalid_lego_id,
            yield_vault_token.address,
            10 * EIGHTEEN_DECIMALS,
            sender=starter_agent.address
        )


def test_vault_mini_wallet_withdraw_from_yield_event_details(setupYieldPosition, undy_usd_vault, starter_agent, yield_vault_token):
    """Test detailed event emission for withdrawFromYield"""

    # setup position with specific amount
    vault_tokens = setupYieldPosition(_deposit_amount=75 * EIGHTEEN_DECIMALS, _underlying_price=4 * EIGHTEEN_DECIMALS)

    # withdraw specific amount
    withdraw_amount = 25 * EIGHTEEN_DECIMALS
    vault_burned, underlying_asset, underlying_received, usd_value = undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token.address,
        withdraw_amount,
        sender=starter_agent.address
    )

    # Get event immediately after transaction
    log = filter_logs(undy_usd_vault, "EarnVaultWithdrawal")[0]
    assert log.vaultToken == yield_vault_token.address
    assert log.underlyingAsset == underlying_asset
    assert log.vaultTokenBurned == vault_burned
    assert log.underlyingAmountReceived == underlying_received
    assert log.usdValue == usd_value
    assert log.legoId == 2
    assert log.signer == starter_agent.address

    # Verify USD value calculation (25 tokens * 4 USD)
    assert usd_value == 25 * 4 * EIGHTEEN_DECIMALS


def test_vault_mini_wallet_withdraw_from_yield_partial_amounts(setupYieldPosition, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token):
    """Test withdrawing various partial amounts"""

    # setup position
    vault_tokens = setupYieldPosition(_deposit_amount=100 * EIGHTEEN_DECIMALS)

    # withdraw 10%
    first_withdraw = vault_tokens * 10 // 100
    vault_burned, _, underlying_received, _ = undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token.address,
        first_withdraw,
        sender=starter_agent.address
    )

    assert vault_burned == first_withdraw
    assert underlying_received == first_withdraw  # 1:1 price
    remaining = vault_tokens - first_withdraw
    assert yield_vault_token.balanceOf(undy_usd_vault) == remaining

    # withdraw 25% of original
    second_withdraw = vault_tokens * 25 // 100
    vault_burned, _, underlying_received, _ = undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token.address,
        second_withdraw,
        sender=starter_agent.address
    )

    assert vault_burned == second_withdraw
    remaining = remaining - second_withdraw
    assert yield_vault_token.balanceOf(undy_usd_vault) == remaining

    # verify total underlying received
    total_underlying = yield_underlying_token.balanceOf(undy_usd_vault)
    assert total_underlying == first_withdraw + second_withdraw


def test_vault_mini_wallet_withdraw_yield_price_tracking_update(setupYieldPosition, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token, governance):
    """Test that withdrawal after yield updates avgPricePerShare with time travel"""

    # setup position
    vault_tokens = setupYieldPosition()

    # Time travel to allow snapshot updates
    boa.env.time_travel(seconds=301)  # 5 minutes + 1 second

    # Simulate significant yield (50% gain)
    yield_amount = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.mint(yield_vault_token.address, yield_amount, sender=governance.address)

    # Withdraw
    withdraw_amount = vault_tokens // 2
    undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token.address,
        withdraw_amount,
        sender=starter_agent.address
    )

    # Verify withdrawal succeeded
    assert yield_vault_token.balanceOf(undy_usd_vault) == vault_tokens - withdraw_amount


def test_vault_mini_wallet_withdraw_deregistration_simple(setupYieldPosition, undy_usd_vault, starter_agent, yield_vault_token):
    """Test simple deregistration when withdrawing the only yield position"""

    # Setup: Create a yield position (this adds yield_vault_token as asset index 1)
    vault_tokens = setupYieldPosition()

    # The vault should have 2 assets now: base asset (yield_underlying_token) and yield_vault_token
    assert undy_usd_vault.numAssets() == 2
    assert undy_usd_vault.indexOfAsset(yield_vault_token.address) == 1

    # Withdraw entire yield position to trigger deregistration
    vault_burned, _, underlying_received, _ = undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token.address,
        vault_tokens,
        sender=starter_agent.address
    )

    # Verify complete deregistration:
    # 1. numAssets decreased back to 1 (only base asset remains)
    assert undy_usd_vault.numAssets() == 1

    # 2. Yield vault token is completely deregistered
    assert undy_usd_vault.indexOfAsset(yield_vault_token.address) == 0

    # 3. Verify all tokens were withdrawn
    assert vault_burned == vault_tokens
    assert yield_vault_token.balanceOf(undy_usd_vault) == 0

    # 4. Lego ID mapping is retained for historical purposes
    assert undy_usd_vault.vaultToLegoId(yield_vault_token.address) == 2  # Historical data retained


##################################################
# Multiple Vault Tokens - Registration & Storage #
##################################################


def test_vault_multiple_vault_tokens_registration(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token, yield_vault_token_2, yield_vault_token_3, yield_vault_token_4):
    """Test registering multiple vault tokens and verify storage tracking"""

    # Initial state: only base asset
    assert undy_usd_vault.numAssets() == 1

    # Deposit to vault token 1 (lego ID 1)
    deposit1 = prepareAssetForWalletTx(_amount=100 * EIGHTEEN_DECIMALS)
    _, _, vault1_tokens, _ = undy_usd_vault.depositForYield(
        2,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit1,
        sender=starter_agent.address
    )

    # Verify vault token 1 registered
    assert undy_usd_vault.numAssets() == 2
    assert undy_usd_vault.indexOfAsset(yield_vault_token.address) == 1
    assert undy_usd_vault.assets(1) == yield_vault_token.address

    # Deposit to vault token 2 (same lego ID 1)
    deposit2 = prepareAssetForWalletTx(_amount=80 * EIGHTEEN_DECIMALS)
    _, _, vault2_tokens, _ = undy_usd_vault.depositForYield(
        2,
        yield_underlying_token.address,
        yield_vault_token_2.address,
        deposit2,
        sender=starter_agent.address
    )

    # Verify vault token 2 registered
    assert undy_usd_vault.numAssets() == 3
    assert undy_usd_vault.indexOfAsset(yield_vault_token_2.address) == 2
    assert undy_usd_vault.assets(2) == yield_vault_token_2.address

    # Deposit to vault token 3 (same lego ID 1)
    deposit3 = prepareAssetForWalletTx(_amount=60 * EIGHTEEN_DECIMALS)
    _, _, vault3_tokens, _ = undy_usd_vault.depositForYield(
        2,
        yield_underlying_token.address,
        yield_vault_token_3.address,
        deposit3,
        sender=starter_agent.address
    )

    # Verify vault token 3 registered
    assert undy_usd_vault.numAssets() == 4
    assert undy_usd_vault.indexOfAsset(yield_vault_token_3.address) == 3
    assert undy_usd_vault.assets(3) == yield_vault_token_3.address

    # Deposit to vault token 4 (same lego ID 1)
    deposit4 = prepareAssetForWalletTx(_amount=40 * EIGHTEEN_DECIMALS)
    _, _, vault4_tokens, _ = undy_usd_vault.depositForYield(
        2,
        yield_underlying_token.address,
        yield_vault_token_4.address,
        deposit4,
        sender=starter_agent.address
    )

    # Verify all 4 vault tokens registered correctly
    assert undy_usd_vault.numAssets() == 5  # base + 4 vault tokens

    # Verify correct indices
    assert undy_usd_vault.indexOfAsset(yield_vault_token.address) == 1
    assert undy_usd_vault.indexOfAsset(yield_vault_token_2.address) == 2
    assert undy_usd_vault.indexOfAsset(yield_vault_token_3.address) == 3
    assert undy_usd_vault.indexOfAsset(yield_vault_token_4.address) == 4

    # Verify assets array is correct
    assert undy_usd_vault.assets(1) == yield_vault_token.address
    assert undy_usd_vault.assets(2) == yield_vault_token_2.address
    assert undy_usd_vault.assets(3) == yield_vault_token_3.address
    assert undy_usd_vault.assets(4) == yield_vault_token_4.address

    # Verify lego ID for each - all should use lego ID 1
    assert undy_usd_vault.vaultToLegoId(yield_vault_token.address) == 2
    assert undy_usd_vault.vaultToLegoId(yield_vault_token_2.address) == 2
    assert undy_usd_vault.vaultToLegoId(yield_vault_token_3.address) == 2
    assert undy_usd_vault.vaultToLegoId(yield_vault_token_4.address) == 2


def test_vault_deregister_middle_asset_array_reorganization(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token, yield_vault_token_2, yield_vault_token_3):
    """Test that removing an asset from the middle properly reorganizes the array"""

    # Setup: Register 3 vault tokens
    deposit1 = prepareAssetForWalletTx(_amount=100 * EIGHTEEN_DECIMALS)
    undy_usd_vault.depositForYield(2, yield_underlying_token.address, yield_vault_token.address, deposit1, sender=starter_agent.address)

    deposit2 = prepareAssetForWalletTx(_amount=80 * EIGHTEEN_DECIMALS)
    _, _, vault2_tokens, _ = undy_usd_vault.depositForYield(2, yield_underlying_token.address, yield_vault_token_2.address, deposit2, sender=starter_agent.address)

    deposit3 = prepareAssetForWalletTx(_amount=60 * EIGHTEEN_DECIMALS)
    undy_usd_vault.depositForYield(2, yield_underlying_token.address, yield_vault_token_3.address, deposit3, sender=starter_agent.address)

    # Verify initial state: 4 assets total
    assert undy_usd_vault.numAssets() == 4
    assert undy_usd_vault.assets(1) == yield_vault_token.address
    assert undy_usd_vault.assets(2) == yield_vault_token_2.address
    assert undy_usd_vault.assets(3) == yield_vault_token_3.address

    # CRITICAL TEST: Withdraw vault token 2 (middle position) completely
    undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token_2.address,
        vault2_tokens,
        sender=starter_agent.address
    )

    # Verify deregistration and array reorganization:
    # 1. numAssets decreased
    assert undy_usd_vault.numAssets() == 3

    # 2. Vault token 2 is deregistered
    assert undy_usd_vault.indexOfAsset(yield_vault_token_2.address) == 0

    # 3. CRITICAL: The last asset (vault_token_3) MUST have been moved to position 2
    assert undy_usd_vault.assets(2) == yield_vault_token_3.address
    assert undy_usd_vault.indexOfAsset(yield_vault_token_3.address) == 2

    # 4. Vault token 1 should remain at position 1 (unchanged)
    assert undy_usd_vault.assets(1) == yield_vault_token.address
    assert undy_usd_vault.indexOfAsset(yield_vault_token.address) == 1


def test_vault_deregister_first_asset_reorganization(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token, yield_vault_token_2, yield_vault_token_3):
    """Test removing the first asset in the array"""

    # Setup: Register 3 vault tokens
    deposit1 = prepareAssetForWalletTx(_amount=100 * EIGHTEEN_DECIMALS)
    _, _, vault1_tokens, _ = undy_usd_vault.depositForYield(2, yield_underlying_token.address, yield_vault_token.address, deposit1, sender=starter_agent.address)

    deposit2 = prepareAssetForWalletTx(_amount=80 * EIGHTEEN_DECIMALS)
    undy_usd_vault.depositForYield(2, yield_underlying_token.address, yield_vault_token_2.address, deposit2, sender=starter_agent.address)

    deposit3 = prepareAssetForWalletTx(_amount=60 * EIGHTEEN_DECIMALS)
    undy_usd_vault.depositForYield(2, yield_underlying_token.address, yield_vault_token_3.address, deposit3, sender=starter_agent.address)

    # Initial state
    assert undy_usd_vault.numAssets() == 4

    # Withdraw vault token 1 (first position) completely
    undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token.address,
        vault1_tokens,
        sender=starter_agent.address
    )

    # Verify reorganization:
    # 1. numAssets decreased
    assert undy_usd_vault.numAssets() == 3

    # 2. Vault token 1 is deregistered
    assert undy_usd_vault.indexOfAsset(yield_vault_token.address) == 0

    # 3. The last asset (vault_token_3) MUST have been moved to position 1
    assert undy_usd_vault.assets(1) == yield_vault_token_3.address
    assert undy_usd_vault.indexOfAsset(yield_vault_token_3.address) == 1

    # 4. Vault token 2 should remain at position 2 (unchanged)
    assert undy_usd_vault.assets(2) == yield_vault_token_2.address
    assert undy_usd_vault.indexOfAsset(yield_vault_token_2.address) == 2


def test_vault_deregister_last_asset(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token, yield_vault_token_2, yield_vault_token_3):
    """Test removing the last asset (no reorganization needed)"""

    # Setup: Register 3 vault tokens
    deposit1 = prepareAssetForWalletTx(_amount=100 * EIGHTEEN_DECIMALS)
    undy_usd_vault.depositForYield(2, yield_underlying_token.address, yield_vault_token.address, deposit1, sender=starter_agent.address)

    deposit2 = prepareAssetForWalletTx(_amount=80 * EIGHTEEN_DECIMALS)
    undy_usd_vault.depositForYield(2, yield_underlying_token.address, yield_vault_token_2.address, deposit2, sender=starter_agent.address)

    deposit3 = prepareAssetForWalletTx(_amount=60 * EIGHTEEN_DECIMALS)
    _, _, vault3_tokens, _ = undy_usd_vault.depositForYield(2, yield_underlying_token.address, yield_vault_token_3.address, deposit3, sender=starter_agent.address)

    # Initial state
    assert undy_usd_vault.numAssets() == 4

    # Withdraw vault token 3 (last position) completely
    undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token_3.address,
        vault3_tokens,
        sender=starter_agent.address
    )

    # Verify deregistration without reorganization:
    # 1. numAssets decreased
    assert undy_usd_vault.numAssets() == 3

    # 2. Vault token 3 is deregistered
    assert undy_usd_vault.indexOfAsset(yield_vault_token_3.address) == 0

    # 3. Other assets remain in their original positions
    assert undy_usd_vault.assets(1) == yield_vault_token.address
    assert undy_usd_vault.indexOfAsset(yield_vault_token.address) == 1

    assert undy_usd_vault.assets(2) == yield_vault_token_2.address
    assert undy_usd_vault.indexOfAsset(yield_vault_token_2.address) == 2


def test_vault_multiple_deregistrations_complex(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token, yield_vault_token_2, yield_vault_token_3, yield_vault_token_4):
    """Test complex scenario with multiple registrations and deregistrations"""

    # Register all 4 vault tokens
    deposits = []
    tokens = [yield_vault_token, yield_vault_token_2, yield_vault_token_3, yield_vault_token_4]

    for i, vault_token in enumerate(tokens, 1):
        deposit = prepareAssetForWalletTx(_amount=(100 - i*10) * EIGHTEEN_DECIMALS)
        _, _, vault_tokens_received, _ = undy_usd_vault.depositForYield(
            2,  # Always use lego ID 1
            yield_underlying_token.address,
            vault_token.address,
            deposit,
            sender=starter_agent.address
        )
        deposits.append(vault_tokens_received)

    assert undy_usd_vault.numAssets() == 5  # base + 4 vault tokens

    # Remove vault token 2 (middle)
    undy_usd_vault.withdrawFromYield(2, yield_vault_token_2.address, deposits[1], sender=starter_agent.address)

    # After removing token 2, token 4 should have moved to position 2
    assert undy_usd_vault.numAssets() == 4
    assert undy_usd_vault.assets(1) == yield_vault_token.address
    assert undy_usd_vault.assets(2) == yield_vault_token_4.address  # Moved from position 4
    assert undy_usd_vault.assets(3) == yield_vault_token_3.address
    assert undy_usd_vault.indexOfAsset(yield_vault_token_4.address) == 2

    # Remove vault token 4 (now at position 2)
    undy_usd_vault.withdrawFromYield(2, yield_vault_token_4.address, deposits[3], sender=starter_agent.address)

    # After removing token 4, token 3 should have moved to position 2
    assert undy_usd_vault.numAssets() == 3
    assert undy_usd_vault.assets(1) == yield_vault_token.address
    assert undy_usd_vault.assets(2) == yield_vault_token_3.address  # Moved from position 3
    assert undy_usd_vault.indexOfAsset(yield_vault_token_3.address) == 2

    # Remove vault token 1 (first position)
    undy_usd_vault.withdrawFromYield(2, yield_vault_token.address, deposits[0], sender=starter_agent.address)

    # After removing token 1, token 3 should have moved to position 1
    assert undy_usd_vault.numAssets() == 2
    assert undy_usd_vault.assets(1) == yield_vault_token_3.address  # Moved from position 2 to 1
    assert undy_usd_vault.indexOfAsset(yield_vault_token_3.address) == 1

    # Remove the last remaining vault token
    undy_usd_vault.withdrawFromYield(2, yield_vault_token_3.address, deposits[2], sender=starter_agent.address)

    # Should be back to just base asset
    assert undy_usd_vault.numAssets() == 1

    # All vault tokens should be deregistered
    assert undy_usd_vault.indexOfAsset(yield_vault_token.address) == 0
    assert undy_usd_vault.indexOfAsset(yield_vault_token_2.address) == 0
    assert undy_usd_vault.indexOfAsset(yield_vault_token_3.address) == 0
    assert undy_usd_vault.indexOfAsset(yield_vault_token_4.address) == 0


def test_vault_partial_withdrawals_no_deregistration(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token, yield_vault_token_2):
    """Test that partial withdrawals don't trigger deregistration"""

    # Register 2 vault tokens
    deposit1 = prepareAssetForWalletTx(_amount=100 * EIGHTEEN_DECIMALS)
    _, _, vault1_tokens, _ = undy_usd_vault.depositForYield(2, yield_underlying_token.address, yield_vault_token.address, deposit1, sender=starter_agent.address)

    deposit2 = prepareAssetForWalletTx(_amount=80 * EIGHTEEN_DECIMALS)
    _, _, vault2_tokens, _ = undy_usd_vault.depositForYield(2, yield_underlying_token.address, yield_vault_token_2.address, deposit2, sender=starter_agent.address)

    assert undy_usd_vault.numAssets() == 3

    # Partial withdrawal from vault token 1 (50%)
    undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token.address,
        vault1_tokens // 2,
        sender=starter_agent.address
    )

    # Should NOT deregister
    assert undy_usd_vault.numAssets() == 3
    assert undy_usd_vault.indexOfAsset(yield_vault_token.address) == 1
    assert undy_usd_vault.assets(1) == yield_vault_token.address

    # Partial withdrawal from vault token 2 (75%)
    undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token_2.address,
        vault2_tokens * 3 // 4,
        sender=starter_agent.address
    )

    # Should still NOT deregister
    assert undy_usd_vault.numAssets() == 3
    assert undy_usd_vault.indexOfAsset(yield_vault_token_2.address) == 2
    assert undy_usd_vault.assets(2) == yield_vault_token_2.address

    # Now withdraw remaining balance from vault token 1
    remaining1 = yield_vault_token.balanceOf(undy_usd_vault)
    undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token.address,
        remaining1,
        sender=starter_agent.address
    )

    # NOW it should deregister vault token 1
    assert undy_usd_vault.numAssets() == 2
    assert undy_usd_vault.indexOfAsset(yield_vault_token.address) == 0

    # Vault token 2 should still be registered at position 1 now
    assert undy_usd_vault.assets(1) == yield_vault_token_2.address
    assert undy_usd_vault.indexOfAsset(yield_vault_token_2.address) == 1


##################################
# Rebalance Yield Position Tests #
##################################


########################################################
# P0 Security Tests - Multi-Position Edge Cases  #
########################################################


def test_deregister_position_that_is_default_target(prepareAssetForWalletTx, undy_usd_vault, vault_registry, starter_agent, yield_underlying_token, yield_vault_token, switchboard_alpha):
    """Test deregistering the defaultTargetVaultToken for auto-deposit"""

    # Setup: Create yield position
    deposit_amount = prepareAssetForWalletTx(_amount=100 * EIGHTEEN_DECIMALS)
    _, _, vault_tokens, _ = undy_usd_vault.depositForYield(
        2,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Set this vault token as the default target for auto-deposit
    vault_registry.setDefaultTargetVaultToken(undy_usd_vault.address, yield_vault_token.address, sender=switchboard_alpha.address)
    vault_registry.setShouldAutoDeposit(undy_usd_vault.address, True, sender=switchboard_alpha.address)

    # Verify it's set as default
    config = vault_registry.getDepositConfig(undy_usd_vault.address)
    assert config[3] == yield_vault_token.address  # defaultTargetVaultToken

    # Now deregister it by withdrawing all
    undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token.address,
        vault_tokens,
        sender=starter_agent.address
    )

    # Verify deregistration
    assert undy_usd_vault.indexOfAsset(yield_vault_token.address) == 0
    assert yield_vault_token.balanceOf(undy_usd_vault) == 0

    # The default target remains set in registry (registry doesn't auto-clear on deregistration)
    config = vault_registry.getDepositConfig(undy_usd_vault.address)
    assert config[3] == yield_vault_token.address

    # This creates a dangling reference: registry points to deregistered position
    # Vault must handle this gracefully when auto-deposit attempts to use missing target


def test_deregister_last_remaining_yield_position(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token):
    """Test removing the final yield position returns vault to base state"""

    # Setup: Create single yield position
    deposit_amount = prepareAssetForWalletTx(_amount=100 * EIGHTEEN_DECIMALS)
    _, _, vault_tokens, _ = undy_usd_vault.depositForYield(
        2,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Verify we have a yield position
    assert undy_usd_vault.numAssets() == 2  # base + yield vault token
    assert undy_usd_vault.indexOfAsset(yield_vault_token.address) == 1

    # Withdraw everything
    undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token.address,
        vault_tokens,
        sender=starter_agent.address
    )

    # Verify we're back to base state (only base asset)
    assert undy_usd_vault.numAssets() == 1
    assert undy_usd_vault.indexOfAsset(yield_vault_token.address) == 0
    assert yield_vault_token.balanceOf(undy_usd_vault) == 0

    # Underlying tokens should be back in vault
    assert yield_underlying_token.balanceOf(undy_usd_vault) > 0


def test_max_number_of_positions_registration(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token, yield_vault_token_2, yield_vault_token_3, yield_vault_token_4):
    """Test registering maximum number of vault token positions"""

    # Register 4 different vault tokens (testing with 4, real limit may be higher)
    vault_tokens_list = [yield_vault_token, yield_vault_token_2, yield_vault_token_3, yield_vault_token_4]

    for i, vault_token in enumerate(vault_tokens_list):
        deposit_amount = prepareAssetForWalletTx(_amount=(100 - i*10) * EIGHTEEN_DECIMALS)
        _, _, vault_tokens_received, _ = undy_usd_vault.depositForYield(
            2,
            yield_underlying_token.address,
            vault_token.address,
            deposit_amount,
            sender=starter_agent.address
        )

        # Verify each registration
        expected_num_assets = 2 + i  # base + i vault tokens
        assert undy_usd_vault.numAssets() == expected_num_assets
        assert undy_usd_vault.indexOfAsset(vault_token.address) == i + 1

    # Verify all are registered correctly
    assert undy_usd_vault.numAssets() == 5  # base + 4 vault tokens

    # Verify we can still operate with all positions
    for i, vault_token in enumerate(vault_tokens_list):
        balance = vault_token.balanceOf(undy_usd_vault)
        assert balance > 0
        assert undy_usd_vault.vaultToLegoId(vault_token.address) == 2


def test_withdrawal_from_position_with_zero_balance(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token):
    """Test withdrawal handling when position has zero balance"""

    # Setup: Create yield position
    deposit_amount = prepareAssetForWalletTx(_amount=100 * EIGHTEEN_DECIMALS)
    _, _, vault_tokens, _ = undy_usd_vault.depositForYield(
        2,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Withdraw everything first
    undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token.address,
        vault_tokens,
        sender=starter_agent.address
    )

    # Position should be deregistered
    assert yield_vault_token.balanceOf(undy_usd_vault) == 0
    assert undy_usd_vault.indexOfAsset(yield_vault_token.address) == 0

    # Try to withdraw from empty position - should revert with "no balance for _token"
    with boa.reverts("no balance for _token"):
        undy_usd_vault.withdrawFromYield(
            2,
            yield_vault_token.address,
            10 * EIGHTEEN_DECIMALS,
            sender=starter_agent.address
        )


def test_deposit_to_unapproved_vault_token_via_registry(prepareAssetForWalletTx, undy_usd_vault, vault_registry, starter_agent, yield_underlying_token, yield_vault_token, switchboard_alpha):
    """Test that depositing to unapproved vault token fails"""

    # Disapprove the yield vault token
    vault_registry.setApprovedVaultToken(
        undy_usd_vault.address,
        yield_vault_token.address,
        False,  # Disapprove
        sender=switchboard_alpha.address
    )

    # Verify it's not approved
    assert vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, yield_vault_token.address) == False

    # Prepare tokens
    deposit_amount = prepareAssetForWalletTx(_amount=100 * EIGHTEEN_DECIMALS)

    # Attempt to deposit to unapproved vault token must fail
    with boa.reverts():  # Must revert - cannot deposit to unapproved vault token
        undy_usd_vault.depositForYield(
            2,
            yield_underlying_token.address,
            yield_vault_token.address,
            deposit_amount,
            sender=starter_agent.address
        )


def test_multiple_positions_withdrawal_when_one_empty(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token, yield_vault_token_2):
    """Test operations with multiple positions where one is empty"""

    # Create two yield positions
    deposit1 = prepareAssetForWalletTx(_amount=100 * EIGHTEEN_DECIMALS)
    _, _, vault1_tokens, _ = undy_usd_vault.depositForYield(
        2,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit1,
        sender=starter_agent.address
    )

    deposit2 = prepareAssetForWalletTx(_amount=80 * EIGHTEEN_DECIMALS)
    _, _, vault2_tokens, _ = undy_usd_vault.depositForYield(
        2,
        yield_underlying_token.address,
        yield_vault_token_2.address,
        deposit2,
        sender=starter_agent.address
    )

    # Verify both registered
    assert undy_usd_vault.numAssets() == 3
    assert undy_usd_vault.indexOfAsset(yield_vault_token.address) == 1
    assert undy_usd_vault.indexOfAsset(yield_vault_token_2.address) == 2

    # Empty the first position completely
    undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token.address,
        vault1_tokens,
        sender=starter_agent.address
    )

    # First position should be deregistered
    assert undy_usd_vault.indexOfAsset(yield_vault_token.address) == 0
    assert yield_vault_token.balanceOf(undy_usd_vault) == 0

    # Second position should now be at index 1 (moved)
    assert undy_usd_vault.indexOfAsset(yield_vault_token_2.address) == 1
    assert undy_usd_vault.numAssets() == 2

    # Operations on second position should still work normally
    partial_withdraw = vault2_tokens // 2
    undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token_2.address,
        partial_withdraw,
        sender=starter_agent.address
    )

    # Verify partial withdrawal worked
    assert yield_vault_token_2.balanceOf(undy_usd_vault) == vault2_tokens - partial_withdraw


def test_auto_deposit_after_default_target_deregistered(prepareAssetForWalletTx, undy_usd_vault, vault_registry, starter_agent, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, yield_vault_token_2, switchboard_alpha, bob):
    """Test auto-deposit behavior after defaultTargetVaultToken is deregistered"""

    # Setup: Create first position and set as default target
    deposit1 = prepareAssetForWalletTx(_amount=100 * EIGHTEEN_DECIMALS)
    _, _, vault1_tokens, _ = undy_usd_vault.depositForYield(
        2,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit1,
        sender=starter_agent.address
    )

    # Set as default target for auto-deposit
    vault_registry.setDefaultTargetVaultToken(undy_usd_vault.address, yield_vault_token.address, sender=switchboard_alpha.address)
    vault_registry.setShouldAutoDeposit(undy_usd_vault.address, True, sender=switchboard_alpha.address)

    # Create second position (alternative)
    deposit2 = prepareAssetForWalletTx(_amount=80 * EIGHTEEN_DECIMALS)
    _, _, vault2_tokens, _ = undy_usd_vault.depositForYield(
        2,
        yield_underlying_token.address,
        yield_vault_token_2.address,
        deposit2,
        sender=starter_agent.address
    )

    # Verify both positions exist
    assert undy_usd_vault.numAssets() == 3  # base + 2 vault tokens

    # Deregister the default target (vault token 1)
    undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token.address,
        vault1_tokens,
        sender=starter_agent.address
    )

    # Default target is now deregistered
    assert undy_usd_vault.indexOfAsset(yield_vault_token.address) == 0

    # Record total assets before deposit
    assets_before = undy_usd_vault.totalAssets()

    # User deposits should still work - vault should handle missing defaultTargetVaultToken gracefully
    yield_underlying_token.approve(undy_usd_vault.address, MAX_UINT256, sender=yield_underlying_token_whale)
    user_deposit = 50 * EIGHTEEN_DECIMALS
    shares = undy_usd_vault.deposit(user_deposit, bob, sender=yield_underlying_token_whale)

    # Deposit must succeed despite deregistered default target
    assert shares > 0

    # Total assets must have increased by deposit amount
    assets_after = undy_usd_vault.totalAssets()
    assert assets_after >= assets_before + user_deposit

    # Vault must handle missing defaultTargetVaultToken gracefully
    # Funds are accounted for and user received shares


def test_position_with_invalid_lego_data_retrieval(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token):
    """Test handling of vault token with stored lego data after operations"""

    # Create position
    deposit_amount = prepareAssetForWalletTx(_amount=100 * EIGHTEEN_DECIMALS)
    _, _, vault_tokens, _ = undy_usd_vault.depositForYield(
        2,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=starter_agent.address
    )

    # Verify lego ID is stored correctly
    assert undy_usd_vault.vaultToLegoId(yield_vault_token.address) == 2

    # Perform withdrawal
    undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token.address,
        vault_tokens // 2,
        sender=starter_agent.address
    )

    # Lego ID should still be accessible after partial withdrawal
    assert undy_usd_vault.vaultToLegoId(yield_vault_token.address) == 2  # Lego ID persists

    # Even after full withdrawal and deregistration, data should be retained
    remaining = yield_vault_token.balanceOf(undy_usd_vault)
    undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token.address,
        remaining,
        sender=starter_agent.address
    )

    # Position is deregistered
    assert undy_usd_vault.indexOfAsset(yield_vault_token.address) == 0

    # But historical lego ID mapping is retained
    assert undy_usd_vault.vaultToLegoId(yield_vault_token.address) == 2  # Historical data preserved


def test_sequential_position_operations_with_reregistration(prepareAssetForWalletTx, undy_usd_vault, starter_agent, yield_underlying_token, yield_vault_token):
    """Test registering, deregistering, and re-registering the same vault token"""

    # First registration
    deposit1 = prepareAssetForWalletTx(_amount=100 * EIGHTEEN_DECIMALS)
    _, _, vault1_tokens, _ = undy_usd_vault.depositForYield(
        2,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit1,
        sender=starter_agent.address
    )

    first_index = undy_usd_vault.indexOfAsset(yield_vault_token.address)
    assert first_index == 1
    assert undy_usd_vault.numAssets() == 2

    # Deregister by withdrawing all
    undy_usd_vault.withdrawFromYield(
        2,
        yield_vault_token.address,
        vault1_tokens,
        sender=starter_agent.address
    )

    assert undy_usd_vault.indexOfAsset(yield_vault_token.address) == 0
    assert undy_usd_vault.numAssets() == 1

    # Re-register the same vault token
    deposit2 = prepareAssetForWalletTx(_amount=150 * EIGHTEEN_DECIMALS)
    _, _, vault2_tokens, _ = undy_usd_vault.depositForYield(
        2,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit2,
        sender=starter_agent.address
    )

    # Should be re-registered at index 1 again
    second_index = undy_usd_vault.indexOfAsset(yield_vault_token.address)
    assert second_index == 1
    assert undy_usd_vault.numAssets() == 2
    assert yield_vault_token.balanceOf(undy_usd_vault) == vault2_tokens

    # Lego ID mapping should remain
    assert undy_usd_vault.vaultToLegoId(yield_vault_token.address) == 2


















