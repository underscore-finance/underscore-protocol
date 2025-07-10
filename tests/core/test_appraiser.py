import pytest
import boa
from constants import ONE_DAY_IN_BLOCKS, EIGHTEEN_DECIMALS, ZERO_ADDRESS


#########
# Utils #
#########


# get profit calc config


def test_appraiser_get_profit_calc_config_no_config(appraiser, yield_vault_token):
    """ no mission control asset config, no ledger vault token registration, will use global defaults """

    config = appraiser.getProfitCalcConfig(yield_vault_token)
    assert config.legoId == 0

    assert config.staleBlocks == ONE_DAY_IN_BLOCKS // 2
    assert config.maxYieldIncrease == 5_00
    assert config.performanceFee == 20_00

    # because not a yield asset, will not get decimals
    assert config.decimals == 0


def test_appraiser_get_profit_calc_config_with_asset_config(mock_yield_lego, appraiser, yield_vault_token, yield_underlying_token, setAssetConfig, createAssetYieldConfig):
    """ mission control asset config is set, no ledger vault token registration, will use mission control config """

    # set mission control asset config
    yield_config = createAssetYieldConfig(
        _isYieldAsset = True,
        _isRebasing = True,
        _underlyingAsset = yield_underlying_token,
        _maxYieldIncrease = 9_00,
        _performanceFee = 26_00,
    )
    setAssetConfig(
        yield_vault_token,
        _legoId = 1,
        _staleBlocks = 2 * ONE_DAY_IN_BLOCKS,
        _yieldConfig = yield_config,
    )

    config = appraiser.getProfitCalcConfig(yield_vault_token)
    assert config.legoId == 1
    assert config.legoAddr == mock_yield_lego.address

    assert config.staleBlocks == 2 * ONE_DAY_IN_BLOCKS
    assert config.maxYieldIncrease == 9_00
    assert config.performanceFee == 26_00

    # because yield asset, will get decimals
    assert config.decimals == yield_vault_token.decimals()


def test_appraiser_get_profit_calc_config_with_vault_registration(appraiser, yield_underlying_token_whale, yield_vault_token, yield_underlying_token, mock_yield_lego, ledger):
    """ no mission control asset config, ledger vault token registration, will use ledger config """

    # need to deposit to register vault token
    yield_underlying_token.approve(mock_yield_lego, 1_000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(
        yield_underlying_token,
        1_000 * EIGHTEEN_DECIMALS,
        yield_vault_token,
        sender=yield_underlying_token_whale,
    )

    # verify vault token registration
    vault_token = ledger.vaultTokens(yield_vault_token)
    assert vault_token.legoId == 1
    assert vault_token.underlyingAsset == yield_underlying_token.address
    assert vault_token.decimals == yield_vault_token.decimals()
    assert vault_token.isRebasing == False

    # get profit calc config
    config = appraiser.getProfitCalcConfig(yield_vault_token)
    assert config.legoId == 1
    assert config.legoAddr == mock_yield_lego.address
    assert config.decimals == yield_vault_token.decimals()
    assert config.isYieldAsset == True
    assert config.isRebasing == False
    assert config.underlyingAsset == yield_underlying_token.address

    # will use global defaults
    assert config.staleBlocks == ONE_DAY_IN_BLOCKS // 2
    assert config.maxYieldIncrease == 5_00
    assert config.performanceFee == 20_00


# get asset usd value config


def test_appraiser_get_asset_usd_value_config_no_config(appraiser, yield_vault_token):
    """ no mission control asset config, no ledger vault token registration, will use global defaults """

    config = appraiser.getAssetUsdValueConfig(yield_vault_token)
    assert config.legoId == 0
    assert config.legoAddr == ZERO_ADDRESS
    assert config.decimals == yield_vault_token.decimals()
    assert config.staleBlocks == ONE_DAY_IN_BLOCKS // 2
    assert config.isYieldAsset == False
    assert config.underlyingAsset == ZERO_ADDRESS


def test_appraiser_get_asset_usd_value_config_with_asset_config(mock_yield_lego, appraiser, yield_vault_token, yield_underlying_token, setAssetConfig, createAssetYieldConfig):
    """ mission control asset config is set, no ledger vault token registration, will use mission control config """

    # set mission control asset config
    yield_config = createAssetYieldConfig(
        _isYieldAsset = True,
        _underlyingAsset = yield_underlying_token,
    )
    setAssetConfig(
        yield_vault_token,
        _legoId = 1,
        _staleBlocks = 2 * ONE_DAY_IN_BLOCKS,
        _yieldConfig = yield_config,
    )

    config = appraiser.getAssetUsdValueConfig(yield_vault_token)
    assert config.legoId == 1
    assert config.legoAddr == mock_yield_lego.address
    assert config.decimals == yield_vault_token.decimals()
    assert config.staleBlocks == 2 * ONE_DAY_IN_BLOCKS
    assert config.isYieldAsset == True
    assert config.underlyingAsset == yield_underlying_token.address


def test_appraiser_get_asset_usd_value_config_with_vault_registration(appraiser, yield_underlying_token_whale, yield_vault_token, yield_underlying_token, mock_yield_lego, ledger):
    """ no mission control asset config, ledger vault token registration, will use ledger config """

    # need to deposit to register vault token
    yield_underlying_token.approve(mock_yield_lego, 1_000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(
        yield_underlying_token,
        1_000 * EIGHTEEN_DECIMALS,
        yield_vault_token,
        sender=yield_underlying_token_whale,
    )

    # verify vault token registration
    vault_token = ledger.vaultTokens(yield_vault_token)
    assert vault_token.legoId == 1
    assert vault_token.underlyingAsset == yield_underlying_token.address
    assert vault_token.decimals == yield_vault_token.decimals()
    assert vault_token.isRebasing == False

    # get asset usd value config
    config = appraiser.getAssetUsdValueConfig(yield_vault_token)
    assert config.legoId == 1
    assert config.legoAddr == mock_yield_lego.address
    assert config.decimals == yield_vault_token.decimals()
    assert config.isYieldAsset == True
    assert config.underlyingAsset == yield_underlying_token.address

    # will use global defaults
    assert config.staleBlocks == ONE_DAY_IN_BLOCKS // 2


########################
# Normal Asset - Price #
########################


def test_appraiser_normal_asset_price_same_block_caching(appraiser, alpha_token, mock_ripe, lego_book):
    """ Test that _getNormalAssetPriceAndDidUpdate returns cached price when called in same block """

    boa.env.time_travel(blocks=5)
    original_price = 20 * EIGHTEEN_DECIMALS
        
    # Set price in Ripe
    mock_ripe.setPrice(alpha_token, original_price)  # $20
    
    # First call to establish cached price
    price1 = appraiser.updateAndGetNormalAssetPrice(alpha_token, sender=lego_book.address)
    assert price1 == original_price

    # verify last price is set
    last_price = appraiser.lastPrice(alpha_token)
    assert last_price.price == original_price
    assert last_price.lastUpdate == boa.env.evm.patch.block_number
    
    # Change Ripe price
    new_price = 25 * EIGHTEEN_DECIMALS
    mock_ripe.setPrice(alpha_token, new_price)  # $25
    
    # Second call in same block should return cached price, not new Ripe price
    price2 = appraiser.getNormalAssetPrice(alpha_token)
    assert price2 == original_price  # Should still be $20 from cache


def test_appraiser_normal_asset_price_stale_blocks_caching(appraiser, alpha_token, setUserWalletConfig, mock_ripe, lego_book):
    """ Test that _getNormalAssetPriceAndDidUpdate returns cached price when within stale blocks period """

    boa.env.time_travel(blocks=5)

    # Set global config stale blocks to 20
    setUserWalletConfig(_staleBlocks=20)
    original_price = 20 * EIGHTEEN_DECIMALS

    # Set initial price in Ripe
    mock_ripe.setPrice(alpha_token, original_price)  # $20
    
    # First call to establish cached price
    price1 = appraiser.updateAndGetNormalAssetPrice(alpha_token, sender=lego_book.address)
    assert price1 == original_price
    
    # Advance 10 blocks (less than 20 stale blocks)
    boa.env.time_travel(blocks=10)
    
    # Change Ripe price
    new_price = 25 * EIGHTEEN_DECIMALS
    mock_ripe.setPrice(alpha_token, new_price)  # $25
    
    # Call should return cached price since we're within stale blocks period
    price2 = appraiser.getNormalAssetPrice(alpha_token)
    assert price2 == original_price  # Should still be $20 from cache
    
    # Now should get new price from Ripe
    boa.env.time_travel(blocks=20)
    price3 = appraiser.getNormalAssetPrice(alpha_token)
    assert price3 == new_price  # Should get new $25 price


def test_appraiser_normal_asset_price_ripe_returns_valid_price(appraiser, alpha_token, mock_ripe):
    """ Test that _getNormalAssetPriceAndDidUpdate gets price from Ripe when it returns valid price """

    boa.env.time_travel(blocks=5)
    original_price = 20 * EIGHTEEN_DECIMALS

    # Set price in Ripe for $20
    mock_ripe.setPrice(alpha_token, original_price)
    
    # Get price should return Ripe price
    price = appraiser.getNormalAssetPrice(alpha_token)
    assert price == original_price


def test_appraiser_normal_asset_price_ripe_zero_lego_fallback(appraiser, alpha_token, mock_ripe, mock_yield_lego, setAssetConfig):
    """ Test that _getNormalAssetPriceAndDidUpdate falls back to lego when Ripe returns zero """

    boa.env.time_travel(blocks=5)

    # need to add lego id so this works
    setAssetConfig(
        alpha_token,
        _legoId = 1,
    )

    # Set Ripe to return 0
    mock_ripe.setPrice(alpha_token, 0)
    
    # Set lego to return $30
    orig_price = 30 * EIGHTEEN_DECIMALS
    mock_yield_lego.setPrice(alpha_token, orig_price)
    
    # Get price should return lego price since Ripe returned 0
    price = appraiser.getNormalAssetPrice(alpha_token)
    assert price == orig_price


def test_appraiser_update_normal_asset_price_saves_to_cache_when_price_changes(appraiser, alpha_token, mock_ripe, lego_book, setUserWalletConfig):
    """ Test that updateAndGetNormalAssetPrice saves new price to cache when didPriceChange=True """

    setUserWalletConfig(_staleBlocks=5)
    boa.env.time_travel(blocks=5)

    # Set initial price in Ripe
    original_price = 20 * EIGHTEEN_DECIMALS
    mock_ripe.setPrice(alpha_token, original_price)  # $20
    
    # First call to establish cached price
    price1 = appraiser.updateAndGetNormalAssetPrice(alpha_token, sender=lego_book.address)
    assert price1 == original_price
    
    # Advance blocks and change Ripe price, should go past stale blocks
    boa.env.time_travel(blocks=10)
    new_price = 25 * EIGHTEEN_DECIMALS
    mock_ripe.setPrice(alpha_token, new_price)  # $25
    
    # Update price - this should save new price to cache since price changed
    price2 = appraiser.updateAndGetNormalAssetPrice(alpha_token, sender=lego_book.address)
    assert price2 == new_price

    last_price = appraiser.lastPrice(alpha_token)
    assert last_price.price == new_price
    assert last_price.lastUpdate == boa.env.evm.patch.block_number

    # Verify cache was updated by calling view function in same block
    # View function should return cached price even though we're in same block
    price3 = appraiser.getNormalAssetPrice(alpha_token)
    assert price3 == new_price  # Should return cached $25, not old $20


def test_appraiser_update_normal_asset_price_no_change_behavior(appraiser, alpha_token, mock_ripe, lego_book, setUserWalletConfig):
    """ Test updateAndGetNormalAssetPrice behavior when price doesn't change """

    setUserWalletConfig(_staleBlocks=5)

    boa.env.time_travel(blocks=5)
    original_price = 20 * EIGHTEEN_DECIMALS

    # Set initial price in Ripe
    mock_ripe.setPrice(alpha_token, original_price)  # $20
    
    # First call to establish cached price
    price1 = appraiser.updateAndGetNormalAssetPrice(alpha_token, sender=lego_book.address)
    assert price1 == original_price

    orig_last_price = appraiser.lastPrice(alpha_token)
    assert orig_last_price.price == original_price
    assert orig_last_price.lastUpdate == boa.env.evm.patch.block_number

    # Advance blocks but keep same price in Ripe, should go past stale blocks
    boa.env.time_travel(blocks=10)
    # Ripe price stays at $20
    
    # Update price - price hasn't changed, so didPriceChange should be False
    price2 = appraiser.updateAndGetNormalAssetPrice(alpha_token, sender=lego_book.address)
    assert price2 == original_price

    # same data saved
    next_last_price = appraiser.lastPrice(alpha_token)
    assert next_last_price.price == original_price
    assert next_last_price.lastUpdate == orig_last_price.lastUpdate

    # Verify cache still works correctly
    price3 = appraiser.getNormalAssetPrice(alpha_token)
    assert price3 == original_price


#################################
# Yield Asset - Price Per Share #
#################################


def test_appraiser_price_per_share_same_block_caching(appraiser, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, mock_yield_lego, lego_book):
    """ Test that _getPricePerShareAndDidUpdate returns cached price when called in same block """
    
    # Register vault token via deposit
    yield_underlying_token.approve(mock_yield_lego, 1_000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(
        yield_underlying_token,
        1_000 * EIGHTEEN_DECIMALS,
        yield_vault_token,
        sender=yield_underlying_token_whale,
    )
    
    orig_price_per_share = mock_yield_lego.getPricePerShare(yield_vault_token, yield_vault_token.decimals())
    assert orig_price_per_share == 1 * EIGHTEEN_DECIMALS
    
    # First call to establish cached price
    price1 = appraiser.updateAndGetPricePerShare(yield_vault_token, sender=lego_book.address)
    assert price1 == orig_price_per_share
    
    # double the price
    yield_underlying_token.transfer(yield_vault_token, 1_000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    doubled_price_per_share = mock_yield_lego.getPricePerShare(yield_vault_token, yield_vault_token.decimals())
    assert doubled_price_per_share == 2 * orig_price_per_share
    
    # Second call in same block should return cached price, not new lego price
    price2 = appraiser.getPricePerShare(yield_vault_token)
    assert price2 == orig_price_per_share


def test_appraiser_price_per_share_stale_blocks_caching(appraiser, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, mock_yield_lego, setUserWalletConfig, lego_book):
    """ Test that _getPricePerShareAndDidUpdate returns cached price when within stale blocks period """
    
    # Set global config with 10 stale blocks
    setUserWalletConfig(_staleBlocks=10)
    
    # Register vault token via deposit
    yield_underlying_token.approve(mock_yield_lego, 1_000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(
        yield_underlying_token,
        1_000 * EIGHTEEN_DECIMALS,
        yield_vault_token,
        sender=yield_underlying_token_whale,
    )
    
    # Get initial price per share (should be 1.0)
    orig_price_per_share = mock_yield_lego.getPricePerShare(yield_vault_token, yield_vault_token.decimals())
    assert orig_price_per_share == 1 * EIGHTEEN_DECIMALS
    
    # First call to establish cached price
    price1 = appraiser.updateAndGetPricePerShare(yield_vault_token, sender=lego_book.address)
    assert price1 == orig_price_per_share
    
    # Advance 5 blocks (less than 10 stale blocks)
    boa.env.time_travel(blocks=5)
    
    # Double the price by transferring tokens to vault
    yield_underlying_token.transfer(yield_vault_token, 1_000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    doubled_price_per_share = mock_yield_lego.getPricePerShare(yield_vault_token, yield_vault_token.decimals())
    assert doubled_price_per_share == 2 * orig_price_per_share
    
    # Call should return cached price since we're within stale blocks period
    price2 = appraiser.getPricePerShare(yield_vault_token)
    assert price2 == orig_price_per_share  # Should still be original from cache
    
    # Advance 6 more blocks (total 11 blocks, exceeding 10 stale blocks)
    boa.env.time_travel(blocks=6)
    
    # Now should get new price from lego
    price3 = appraiser.getPricePerShare(yield_vault_token)
    assert price3 == doubled_price_per_share  # Should get new doubled price


def test_appraiser_price_per_share_lego_returns_valid_price(appraiser, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, mock_yield_lego):
    """ Test that _getPricePerShareAndDidUpdate gets price from lego when it returns valid price """
    
    # Register vault token via deposit
    yield_underlying_token.approve(mock_yield_lego, 1_000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(
        yield_underlying_token,
        1_000 * EIGHTEEN_DECIMALS,
        yield_vault_token,
        sender=yield_underlying_token_whale,
    )
    
    # Get natural price per share from lego
    expected_price = mock_yield_lego.getPricePerShare(yield_vault_token, yield_vault_token.decimals())
    assert expected_price == 1 * EIGHTEEN_DECIMALS
    
    # Get price should return lego price
    price = appraiser.getPricePerShare(yield_vault_token)
    assert price == expected_price


def test_appraiser_price_per_share_lego_zero_ripe_fallback(appraiser, yield_vault_token, mock_ripe):
    """ Test that _getPricePerShareAndDidUpdate falls back to Ripe when lego returns zero """
   
    # Set Ripe to return a price
    mock_ripe.setPrice(yield_vault_token, 2 * EIGHTEEN_DECIMALS)
    
    # Get price should return Ripe price since lego returned 0
    price = appraiser.getPricePerShare(yield_vault_token)
    assert price == 2 * EIGHTEEN_DECIMALS


def test_appraiser_update_price_per_share_no_update_within_stale_blocks(appraiser, setUserWalletConfig, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, mock_yield_lego, lego_book):
    """ Test that updateAndGetPricePerShare does NOT update cache when within stale blocks, even if actual price changed """

    # Set global config with 10 stale blocks
    setUserWalletConfig(_staleBlocks=10)

    # Register vault token via deposit
    yield_underlying_token.approve(mock_yield_lego, 1_000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(
        yield_underlying_token,
        1_000 * EIGHTEEN_DECIMALS,
        yield_vault_token,
        sender=yield_underlying_token_whale,
    )
    
    # Get initial price per share
    orig_price_per_share = mock_yield_lego.getPricePerShare(yield_vault_token, yield_vault_token.decimals())
    assert orig_price_per_share == 1 * EIGHTEEN_DECIMALS
    
    # First call to establish cached price
    price1 = appraiser.updateAndGetPricePerShare(yield_vault_token, sender=lego_book.address)
    assert price1 == orig_price_per_share

    orig_last_price = appraiser.lastPricePerShare(yield_vault_token)
    assert orig_last_price.pricePerShare == orig_price_per_share
    original_update_block = orig_last_price.lastUpdate

    # Advance blocks, still within stale blocks (5 < 10)
    boa.env.time_travel(blocks=5)
    
    # Change actual price by transferring tokens
    yield_underlying_token.transfer(yield_vault_token, 1_000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    new_actual_price = mock_yield_lego.getPricePerShare(yield_vault_token, yield_vault_token.decimals())
    assert new_actual_price == 2 * orig_price_per_share  # Actual price doubled
    
    # Update price - should NOT update cache because within stale blocks
    returned_price = appraiser.updateAndGetPricePerShare(yield_vault_token, sender=lego_book.address)
    assert returned_price == orig_price_per_share  # Should return old cached price
    
    # Verify cache was NOT updated
    cached_price = appraiser.lastPricePerShare(yield_vault_token)
    assert cached_price.pricePerShare == orig_price_per_share  # Still old price
    assert cached_price.lastUpdate == original_update_block  # Same update block


def test_appraiser_update_price_per_share_updates_when_outside_stale_blocks_and_price_changed(appraiser, setUserWalletConfig, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, mock_yield_lego, lego_book):
    """ Test that updateAndGetPricePerShare DOES update cache when outside stale blocks and price changed """

    # Set global config with 5 stale blocks
    setUserWalletConfig(_staleBlocks=5)

    # Register vault token via deposit
    yield_underlying_token.approve(mock_yield_lego, 1_000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(
        yield_underlying_token,
        1_000 * EIGHTEEN_DECIMALS,
        yield_vault_token,
        sender=yield_underlying_token_whale,
    )
    
    # Get initial price per share
    orig_price_per_share = mock_yield_lego.getPricePerShare(yield_vault_token, yield_vault_token.decimals())
    assert orig_price_per_share == 1 * EIGHTEEN_DECIMALS
    
    # First call to establish cached price
    price1 = appraiser.updateAndGetPricePerShare(yield_vault_token, sender=lego_book.address)
    assert price1 == orig_price_per_share

    # Advance beyond stale blocks (10 > 5)
    boa.env.time_travel(blocks=10)
    
    # Change actual price by transferring tokens
    yield_underlying_token.transfer(yield_vault_token, 1_500 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    new_actual_price = mock_yield_lego.getPricePerShare(yield_vault_token, yield_vault_token.decimals())
    assert new_actual_price > orig_price_per_share  # Price increased
    
    # Update price - should update cache because outside stale blocks AND price changed
    returned_price = appraiser.updateAndGetPricePerShare(yield_vault_token, sender=lego_book.address)
    assert returned_price == new_actual_price  # Should return new price
    
    # Verify cache WAS updated
    cached_price = appraiser.lastPricePerShare(yield_vault_token)
    assert cached_price.pricePerShare == new_actual_price  # New price saved
    assert cached_price.lastUpdate == boa.env.evm.patch.block_number  # New update block
    
    # Verify same-block caching works with new price
    same_block_price = appraiser.getPricePerShare(yield_vault_token)
    assert same_block_price == new_actual_price


def test_appraiser_update_price_per_share_no_update_when_outside_stale_blocks_but_price_same(appraiser, setUserWalletConfig, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, mock_yield_lego, lego_book):
    """ Test that updateAndGetPricePerShare does NOT update cache when outside stale blocks but price hasn't changed """

    # Set global config with 5 stale blocks
    setUserWalletConfig(_staleBlocks=5)

    # Register vault token via deposit
    yield_underlying_token.approve(mock_yield_lego, 1_000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(
        yield_underlying_token,
        1_000 * EIGHTEEN_DECIMALS,
        yield_vault_token,
        sender=yield_underlying_token_whale,
    )
    
    # Get initial price per share
    orig_price_per_share = mock_yield_lego.getPricePerShare(yield_vault_token, yield_vault_token.decimals())
    assert orig_price_per_share == 1 * EIGHTEEN_DECIMALS
    
    # First call to establish cached price
    price1 = appraiser.updateAndGetPricePerShare(yield_vault_token, sender=lego_book.address)
    assert price1 == orig_price_per_share

    orig_last_price = appraiser.lastPricePerShare(yield_vault_token)
    original_update_block = orig_last_price.lastUpdate

    # Advance beyond stale blocks (10 > 5)
    boa.env.time_travel(blocks=10)
    
    # Price stays the same (no token transfers)
    current_actual_price = mock_yield_lego.getPricePerShare(yield_vault_token, yield_vault_token.decimals())
    assert current_actual_price == orig_price_per_share  # Price unchanged
    
    # Update price - should NOT update cache because price didn't change (didPriceChange=False)
    returned_price = appraiser.updateAndGetPricePerShare(yield_vault_token, sender=lego_book.address)
    assert returned_price == orig_price_per_share  # Should return same price
    
    # Verify cache was NOT updated (didPriceChange=False means no storage write)
    cached_price = appraiser.lastPricePerShare(yield_vault_token)
    assert cached_price.pricePerShare == orig_price_per_share  # Same price
    assert cached_price.lastUpdate == original_update_block  # Same update block (no write happened)


######################
# Prices - USD Value #
######################


def test_appraiser_get_usd_value_normal_asset(appraiser, alpha_token, mock_ripe):
    """ Test getUsdValue for normal assets with direct price """
    
    # Set price at $20
    price = 20 * EIGHTEEN_DECIMALS
    mock_ripe.setPrice(alpha_token, price)
    
    # Test with 100 tokens
    amount = 100 * EIGHTEEN_DECIMALS
    usd_value = appraiser.getUsdValue(alpha_token, amount)
    
    # 100 tokens * $20 = $2000
    expected_value = 2000 * EIGHTEEN_DECIMALS
    assert usd_value == expected_value


def test_appraiser_get_usd_value_yield_asset_no_underlying(appraiser, yield_vault_token, mock_ripe):
    """ Test getUsdValue for yield assets without underlying (treated as normal asset) """
    
    # Set direct price for yield token at $50
    price = 50 * EIGHTEEN_DECIMALS
    mock_ripe.setPrice(yield_vault_token, price)
    
    # Test with 10 tokens
    amount = 10 * EIGHTEEN_DECIMALS
    usd_value = appraiser.getUsdValue(yield_vault_token, amount)
    
    # 10 tokens * $50 = $500
    expected_value = 500 * EIGHTEEN_DECIMALS
    assert usd_value == expected_value


def test_appraiser_get_usd_value_yield_asset_with_underlying(appraiser, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, mock_yield_lego, mock_ripe):
    """ Test getUsdValue for yield assets with underlying using price per share """
    
    # Register vault token via deposit
    yield_underlying_token.approve(mock_yield_lego, 1_000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(
        yield_underlying_token,
        1_000 * EIGHTEEN_DECIMALS,
        yield_vault_token,
        sender=yield_underlying_token_whale,
    )
    
    # Set underlying token price at $10
    underlying_price = 10 * EIGHTEEN_DECIMALS
    mock_ripe.setPrice(yield_underlying_token, underlying_price)
    
    # Double the vault value
    yield_underlying_token.transfer(yield_vault_token, 1_000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    
    # Price per share should be 2.0
    price_per_share = mock_yield_lego.getPricePerShare(yield_vault_token, yield_vault_token.decimals())
    assert price_per_share == 2 * EIGHTEEN_DECIMALS
    
    # Test with 50 vault tokens
    amount = 50 * EIGHTEEN_DECIMALS
    usd_value = appraiser.getUsdValue(yield_vault_token, amount)
    
    # 50 vault tokens * 2.0 price per share * $10 underlying = $1000
    expected_value = 1000 * EIGHTEEN_DECIMALS
    assert usd_value == expected_value


def test_appraiser_get_usd_value_uses_cached_prices(appraiser, alpha_token, mock_ripe, lego_book):
    """ Test that getUsdValue uses cached prices from previous updates """
    
    # Set initial price at $20
    initial_price = 20 * EIGHTEEN_DECIMALS
    mock_ripe.setPrice(alpha_token, initial_price)
    
    # Update price to cache it
    appraiser.updateAndGetNormalAssetPrice(alpha_token, sender=lego_book.address)
    
    # Change Ripe price to $30
    new_price = 30 * EIGHTEEN_DECIMALS
    mock_ripe.setPrice(alpha_token, new_price)
    
    # getUsdValue should use cached price ($20) not new price ($30)
    amount = 100 * EIGHTEEN_DECIMALS
    usd_value = appraiser.getUsdValue(alpha_token, amount)
    
    # 100 tokens * $20 (cached) = $2000
    expected_value = 2000 * EIGHTEEN_DECIMALS
    assert usd_value == expected_value


def test_appraiser_update_price_and_get_usd_value_permission_check(appraiser, alpha_token, mock_ripe, bob):
    """ Test that updatePriceAndGetUsdValue enforces permission checks """
    
    # Set price
    mock_ripe.setPrice(alpha_token, 10 * EIGHTEEN_DECIMALS)
    
    # Should fail when called by unauthorized address
    with boa.reverts("no perms"):
        appraiser.updatePriceAndGetUsdValue(alpha_token, 100 * EIGHTEEN_DECIMALS, sender=bob)


def test_appraiser_update_price_and_get_usd_value_normal_asset(appraiser, alpha_token, mock_ripe, lego_book):
    """ Test updatePriceAndGetUsdValue for normal assets """
    
    # Set price at $25
    price = 25 * EIGHTEEN_DECIMALS
    mock_ripe.setPrice(alpha_token, price)
    
    # Test with 40 tokens
    amount = 40 * EIGHTEEN_DECIMALS
    usd_value = appraiser.updatePriceAndGetUsdValue(alpha_token, amount, sender=lego_book.address)
    
    # 40 tokens * $25 = $1000
    expected_value = 1000 * EIGHTEEN_DECIMALS
    assert usd_value == expected_value
    
    # Verify price was cached
    last_price = appraiser.lastPrice(alpha_token)
    assert last_price.price == price
    assert last_price.lastUpdate == boa.env.evm.patch.block_number


def test_appraiser_update_price_and_get_usd_value_yield_asset(appraiser, yield_vault_token, lego_book, yield_underlying_token, yield_underlying_token_whale, mock_yield_lego, mock_ripe):
    """ Test updatePriceAndGetUsdValue for yield assets with underlying """
    
    # Register vault token via deposit
    yield_underlying_token.approve(mock_yield_lego, 2_000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(
        yield_underlying_token,
        2_000 * EIGHTEEN_DECIMALS,
        yield_vault_token,
        sender=yield_underlying_token_whale,
    )
    
    # Set underlying token price at $15
    underlying_price = 15 * EIGHTEEN_DECIMALS
    mock_ripe.setPrice(yield_underlying_token, underlying_price)
    
    # Increase vault value by 50%
    yield_underlying_token.transfer(yield_vault_token, 1_000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    
    # Price per share should be 1.5
    price_per_share = mock_yield_lego.getPricePerShare(yield_vault_token, yield_vault_token.decimals())
    assert price_per_share == 15 * EIGHTEEN_DECIMALS // 10  # 1.5
    
    # Test with 100 vault tokens
    amount = 100 * EIGHTEEN_DECIMALS
    usd_value = appraiser.updatePriceAndGetUsdValue(yield_vault_token, amount, sender=lego_book.address)
    
    # 100 vault tokens * 1.5 price per share * $15 underlying = $2250
    expected_value = 2250 * EIGHTEEN_DECIMALS
    assert usd_value == expected_value
    
    # Verify both prices were cached
    last_price_per_share = appraiser.lastPricePerShare(yield_vault_token)
    assert last_price_per_share.pricePerShare == price_per_share
    assert last_price_per_share.lastUpdate == boa.env.evm.patch.block_number
    
    last_price = appraiser.lastPrice(yield_underlying_token)
    assert last_price.price == underlying_price


def test_appraiser_update_price_and_get_usd_value_caching_behavior(appraiser, alpha_token, mock_ripe, setUserWalletConfig, lego_book):
    """ Test that updatePriceAndGetUsdValue properly updates cache based on stale blocks """
    
    # Set user wallet and stale blocks
    setUserWalletConfig(_staleBlocks=10)
    
    # Set initial price at $30
    initial_price = 30 * EIGHTEEN_DECIMALS
    mock_ripe.setPrice(alpha_token, initial_price)
    
    # First update
    amount = 50 * EIGHTEEN_DECIMALS
    usd_value1 = appraiser.updatePriceAndGetUsdValue(alpha_token, amount, sender=lego_book.address)
    assert usd_value1 == 1500 * EIGHTEEN_DECIMALS  # 50 * $30
    
    # Advance 5 blocks (within stale blocks)
    boa.env.time_travel(blocks=5)
    
    # Change price to $40
    new_price = 40 * EIGHTEEN_DECIMALS
    mock_ripe.setPrice(alpha_token, new_price)
    
    # Second update within stale blocks - should return cached price
    usd_value2 = appraiser.updatePriceAndGetUsdValue(alpha_token, amount, sender=lego_book.address)
    assert usd_value2 == 1500 * EIGHTEEN_DECIMALS  # Still 50 * $30 (cached)
    
    # Advance beyond stale blocks
    boa.env.time_travel(blocks=6)  # Total 11 blocks
    
    # Third update beyond stale blocks - should get new price
    usd_value3 = appraiser.updatePriceAndGetUsdValue(alpha_token, amount, sender=lego_book.address)
    assert usd_value3 == 2000 * EIGHTEEN_DECIMALS  # 50 * $40 (new price)
    
    # Verify cache was updated
    last_price = appraiser.lastPrice(alpha_token)
    assert last_price.price == new_price


def test_appraiser_get_usd_value_zero_amount(appraiser, alpha_token, mock_ripe):
    """ Test getUsdValue with zero amount returns zero """
    
    # Set price
    mock_ripe.setPrice(alpha_token, 100 * EIGHTEEN_DECIMALS)
    
    # Zero amount should return zero USD value
    usd_value = appraiser.getUsdValue(alpha_token, 0)
    assert usd_value == 0


def test_appraiser_get_usd_value_price_fallback_to_lego(appraiser, alpha_token, mock_ripe, mock_yield_lego, setAssetConfig):
    """ Test getUsdValue falls back to lego price when Ripe returns zero """
    
    # Configure asset with lego
    setAssetConfig(alpha_token, _legoId=1)
    
    # Ripe returns 0
    mock_ripe.setPrice(alpha_token, 0)
    
    # Lego returns $75
    lego_price = 75 * EIGHTEEN_DECIMALS
    mock_yield_lego.setPrice(alpha_token, lego_price)
    
    # Test with 20 tokens
    amount = 20 * EIGHTEEN_DECIMALS
    usd_value = appraiser.getUsdValue(alpha_token, amount)
    
    # 20 tokens * $75 = $1500
    expected_value = 1500 * EIGHTEEN_DECIMALS
    assert usd_value == expected_value


def test_appraiser_usd_value_with_six_decimal_tokens(appraiser, charlie_token, charlie_token_vault, charlie_token_whale, mock_yield_lego, mock_ripe, lego_book):
    """ Test getUsdValue and updatePriceAndGetUsdValue work correctly with 6 decimal tokens """
    
    # Verify both tokens have 6 decimals
    charlie_decimals = charlie_token.decimals()
    vault_decimals = charlie_token_vault.decimals()
    assert charlie_decimals == 6
    assert vault_decimals == 6
    
    # Register vault token via deposit
    deposit_amount = 10_000 * 10**charlie_decimals  # 10,000 USDC
    charlie_token.approve(mock_yield_lego, deposit_amount, sender=charlie_token_whale)
    mock_yield_lego.depositForYield(
        charlie_token,
        deposit_amount,
        charlie_token_vault,
        sender=charlie_token_whale,
    )
    
    # Set underlying token price at $1 (USDC)
    underlying_price = 1 * EIGHTEEN_DECIMALS
    mock_ripe.setPrice(charlie_token, underlying_price)
    
    # Initial price per share should be 1.0 (in 6 decimals)
    price_per_share = mock_yield_lego.getPricePerShare(charlie_token_vault, vault_decimals)
    assert price_per_share == 1 * 10**charlie_decimals  # 1.0 in 6 decimals
    
    # Test getUsdValue with 5000 vault tokens (6 decimals)
    vault_amount = 5_000 * 10**vault_decimals
    usd_value = appraiser.getUsdValue(charlie_token_vault, vault_amount)
    
    # 5000 vault tokens * 1.0 price per share * $1 underlying = $5000
    expected_value = 5_000 * EIGHTEEN_DECIMALS
    assert usd_value == expected_value
    
    # Increase vault value by 50%
    charlie_token.transfer(charlie_token_vault, 5_000 * 10**charlie_decimals, sender=charlie_token_whale)
    
    # Price per share should be 1.5 (in 6 decimals)
    new_price_per_share = mock_yield_lego.getPricePerShare(charlie_token_vault, vault_decimals)
    assert new_price_per_share == 15 * 10**charlie_decimals // 10  # 1.5 in 6 decimals
    
    # Test updatePriceAndGetUsdValue
    usd_value2 = appraiser.updatePriceAndGetUsdValue(charlie_token_vault, vault_amount, sender=lego_book.address)
    
    # 5000 vault tokens * 1.5 price per share * $1 underlying = $7500
    expected_value2 = 7_500 * EIGHTEEN_DECIMALS
    assert usd_value2 == expected_value2
    
    # Verify prices were cached correctly
    last_price_per_share = appraiser.lastPricePerShare(charlie_token_vault)
    assert last_price_per_share.pricePerShare == new_price_per_share
    
    last_price = appraiser.lastPrice(charlie_token)
    assert last_price.price == underlying_price

