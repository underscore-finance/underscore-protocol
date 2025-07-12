import pytest
import boa

from constants import ZERO_ADDRESS


def test_payee_example_test(createGlobalPayeeSettings, charlie, alpha_token, bravo_token, bob, createPayeeLimits, createPayeeSettings, sentintel, user_wallet, user_wallet_config, alice):

    # set global payee settings
    new_global_payee_settings = createGlobalPayeeSettings(_canPayOwner=False)
    user_wallet_config.setGlobalPayeeSettings(new_global_payee_settings, sender=paymaster.address)

    # add payee
    unit_limits = createPayeeLimits(_perTxCap=10)
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _onlyPrimaryAsset=True, _unitLimits=unit_limits)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)

    # cannot pay owner
    assert not sentintel.isValidPayee(user_wallet, bob, alpha_token, 1, 1)

    # not payee
    assert not sentintel.isValidPayee(user_wallet, charlie, alpha_token, 1, 1)

    # payee -- not primary asset
    assert not sentintel.isValidPayee(user_wallet, alice, bravo_token, 9, 1)

    # payee -- primary asset
    assert sentintel.isValidPayee(user_wallet, alice, alpha_token, 9, 1)

    # payee -- over limit
    assert not sentintel.isValidPayee(user_wallet, alice, alpha_token, 11, 1)


# whitelist tests


def test_whitelisted_recipient_always_valid(alpha_token, bravo_token, delta_token, sentintel, user_wallet, user_wallet_config, alice):
    # add alice to whitelist
    user_wallet_config.confirmWhitelistAddr(alice, sender=paymaster.address)
    
    # whitelisted addresses should always be valid regardless of amounts or assets
    assert sentintel.isValidPayee(user_wallet, alice, alpha_token, 1_000_000, 1_000_000)
    assert sentintel.isValidPayee(user_wallet, alice, bravo_token, 999_999_999, 999_999_999)
    assert sentintel.isValidPayee(user_wallet, alice, delta_token, 1, 1)
    assert sentintel.isValidPayee(user_wallet, alice, ZERO_ADDRESS, 0, 0)  # even with zero address


def test_non_whitelisted_non_payee_invalid(alpha_token, sentintel, user_wallet, sally):
    # sally is neither whitelisted nor a payee
    assert not sentintel.isValidPayee(user_wallet, sally, alpha_token, 1, 1)


# owner tests


def test_owner_payment_with_canPayOwner_true(createGlobalPayeeSettings, alpha_token, bob, sentintel, user_wallet, user_wallet_config):
    # set global payee settings with canPayOwner=True
    new_global_payee_settings = createGlobalPayeeSettings(_canPayOwner=True)
    user_wallet_config.setGlobalPayeeSettings(new_global_payee_settings, sender=paymaster.address)
    
    # owner (bob) should be valid payee
    assert sentintel.isValidPayee(user_wallet, bob, alpha_token, 100, 100)


def test_owner_payment_with_canPayOwner_false(createGlobalPayeeSettings, alpha_token, bob, sentintel, user_wallet, user_wallet_config):
    # set global payee settings with canPayOwner=False
    new_global_payee_settings = createGlobalPayeeSettings(_canPayOwner=False)
    user_wallet_config.setGlobalPayeeSettings(new_global_payee_settings, sender=paymaster.address)
    
    # owner (bob) should not be valid payee
    assert not sentintel.isValidPayee(user_wallet, bob, alpha_token, 100, 100)


# activation / expiry tests


def test_payee_not_yet_active(createPayeeSettings, alpha_token, alice, sentintel, user_wallet, user_wallet_config):
    # add payee with future start block
    future_start = boa.env.evm.patch.block_number + 1000
    new_payee_settings = createPayeeSettings(_startBlock=future_start)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # payee should not be valid before start block
    assert not sentintel.isValidPayee(user_wallet, alice, alpha_token, 1, 1)


def test_payee_active(createPayeeSettings, alpha_token, alice, sentintel, user_wallet, user_wallet_config):
    # add payee with current block as start
    current_block = boa.env.evm.patch.block_number
    new_payee_settings = createPayeeSettings(_startBlock=current_block)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # payee should be valid at start block
    assert sentintel.isValidPayee(user_wallet, alice, alpha_token, 1, 1)


def test_payee_expired(createPayeeSettings, alpha_token, alice, sentintel, user_wallet, user_wallet_config):
    # add payee with short expiry
    current_block = boa.env.evm.patch.block_number
    new_payee_settings = createPayeeSettings(_startBlock=current_block, _expiryBlock=current_block + 10, _primaryAsset=alpha_token)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # travel past expiry
    boa.env.time_travel(blocks=11)
    
    # payee should not be valid after expiry
    assert not sentintel.isValidPayee(user_wallet, alice, alpha_token, 1, 1)


# asset restrictions


def test_primary_asset_only_restriction(createPayeeSettings, alpha_token, bravo_token, alice, sentintel, user_wallet, user_wallet_config):
    # add payee with onlyPrimaryAsset=True
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _onlyPrimaryAsset=True)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # should be valid for primary asset
    assert sentintel.isValidPayee(user_wallet, alice, alpha_token, 1, 1)
    
    # should not be valid for other assets
    assert not sentintel.isValidPayee(user_wallet, alice, bravo_token, 1, 1)


def test_no_primary_asset_restriction(createPayeeSettings, alpha_token, bravo_token, alice, sentintel, user_wallet, user_wallet_config):
    # add payee without asset restrictions
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _onlyPrimaryAsset=False)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # should be valid for any asset
    assert sentintel.isValidPayee(user_wallet, alice, alpha_token, 1, 1)
    assert sentintel.isValidPayee(user_wallet, alice, bravo_token, 1, 1)


# transaction limits


def test_max_txs_per_period_limit(createGlobalPayeeSettings, createPayeeSettings, createPayeeData, alpha_token, alice, sentintel, user_wallet_config):
    # add payee with max 3 txs per period
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _maxNumTxsPerPeriod=3)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # simulate payee has already made 3 txs in period
    payee_data = createPayeeData(_numTxsInPeriod=3, _periodStartBlock=boa.env.evm.patch.block_number)
    
    # need global config for isValidPayeeAndGetData call
    new_global_payee_settings = createGlobalPayeeSettings()
    
    # should not be valid when limit reached
    is_valid, _ = sentintel.isValidPayeeAndGetData(
        False,
        False,
        True,
        alpha_token,
        1,
        1,
        new_payee_settings,
        new_global_payee_settings,
        payee_data
    )
    assert not is_valid


def test_tx_cooldown_blocks(createGlobalPayeeSettings, createPayeeSettings, createPayeeData, alpha_token, alice, sentintel, user_wallet_config):
    # add payee with 10 block cooldown
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _txCooldownBlocks=10)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # simulate recent transaction
    boa.env.time_travel(blocks=110)
    current_block = boa.env.evm.patch.block_number
    payee_data = createPayeeData(_lastTxBlock=current_block - 5, _periodStartBlock=current_block - 100)
    
    # need global config for isValidPayeeAndGetData call
    new_global_payee_settings = createGlobalPayeeSettings()
    
    # should not be valid during cooldown
    is_valid, _ = sentintel.isValidPayeeAndGetData(
        False,
        False,
        True,
        alpha_token,
        1,
        1,
        new_payee_settings,
        new_global_payee_settings,
        payee_data
    )
    assert not is_valid
    
    # simulate cooldown passed
    payee_data_after_cooldown = createPayeeData(_lastTxBlock=current_block - 11, _periodStartBlock=current_block - 100)
    is_valid, _ = sentintel.isValidPayeeAndGetData(
        False,
        False,
        True,
        alpha_token,
        1,
        1,
        new_payee_settings,
        new_global_payee_settings,
        payee_data_after_cooldown
    )
    assert is_valid


# usd limits


def test_usd_per_tx_cap(createPayeeSettings, createPayeeLimits, alpha_token, alice, sentintel, user_wallet, user_wallet_config):
    # add payee with $100 per tx cap
    usd_limits = createPayeeLimits(_perTxCap=100)
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _usdLimits=usd_limits)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # should be valid under limit
    assert sentintel.isValidPayee(user_wallet, alice, alpha_token, 1, 99)
    
    # should not be valid over limit
    assert not sentintel.isValidPayee(user_wallet, alice, alpha_token, 1, 101)


def test_usd_per_period_cap(createGlobalPayeeSettings, createPayeeSettings, createPayeeLimits, createPayeeData, alpha_token, alice, sentintel, user_wallet_config):
    # add payee with $1000 per period cap
    usd_limits = createPayeeLimits(_perPeriodCap=1000)
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _usdLimits=usd_limits)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # simulate $800 already spent in period
    payee_data = createPayeeData(_totalUsdValueInPeriod=800, _periodStartBlock=boa.env.evm.patch.block_number)
    
    # need global config for isValidPayeeAndGetData call
    new_global_payee_settings = createGlobalPayeeSettings()
    
    # should be valid for $199 (total would be $999)
    is_valid, _ = sentintel.isValidPayeeAndGetData(
        False,
        False,
        True,
        alpha_token,
        1,
        199,
        new_payee_settings,
        new_global_payee_settings,
        payee_data
    )
    assert is_valid
    
    # should not be valid for $201 (total would be $1001)
    is_valid, _ = sentintel.isValidPayeeAndGetData(
        False,
        False,
        True,
        alpha_token,
        1,
        201,
        new_payee_settings,
        new_global_payee_settings,
        payee_data
    )
    assert not is_valid


def test_usd_lifetime_cap(createGlobalPayeeSettings, createPayeeSettings, createPayeeLimits, createPayeeData, alpha_token, alice, sentintel, user_wallet_config):
    # add payee with $10000 lifetime cap
    usd_limits = createPayeeLimits(_lifetimeCap=10000)
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _usdLimits=usd_limits)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # simulate $9900 already spent lifetime
    payee_data = createPayeeData(_totalUsdValue=9900)
    
    # need global config for isValidPayeeAndGetData call
    new_global_payee_settings = createGlobalPayeeSettings()
    
    # should be valid for $100
    is_valid, _ = sentintel.isValidPayeeAndGetData(
        False,
        False,
        True,
        alpha_token,
        1,
        100,
        new_payee_settings,
        new_global_payee_settings,
        payee_data
    )
    assert is_valid
    
    # should not be valid for $101
    is_valid, _ = sentintel.isValidPayeeAndGetData(
        False,
        False,
        True,
        alpha_token,
        1,
        101,
        new_payee_settings,
        new_global_payee_settings,
        payee_data
    )
    assert not is_valid


# unit limits


def test_unit_per_tx_cap(createPayeeSettings, createPayeeLimits, alpha_token, alice, sentintel, user_wallet, user_wallet_config):
    # add payee with 1000 units per tx cap
    unit_limits = createPayeeLimits(_perTxCap=1000)
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _unitLimits=unit_limits)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # should be valid under limit
    assert sentintel.isValidPayee(user_wallet, alice, alpha_token, 999, 1)
    
    # should not be valid over limit
    assert not sentintel.isValidPayee(user_wallet, alice, alpha_token, 1001, 1)


def test_unit_limits_only_apply_to_primary_asset(createPayeeSettings, createPayeeLimits, alpha_token, bravo_token, alice, sentintel, user_wallet, user_wallet_config):
    # add payee with unit limits on alpha token (primary asset)
    unit_limits = createPayeeLimits(_perTxCap=100)
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _unitLimits=unit_limits, _onlyPrimaryAsset=False)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # unit limit should apply to primary asset
    assert not sentintel.isValidPayee(user_wallet, alice, alpha_token, 101, 1)
    
    # unit limit should NOT apply to other assets
    assert sentintel.isValidPayee(user_wallet, alice, bravo_token, 1000, 1)


def test_unit_per_period_cap(createGlobalPayeeSettings, createPayeeSettings, createPayeeLimits, createPayeeData, alpha_token, alice, sentintel, user_wallet_config):
    # add payee with 10000 units per period cap
    unit_limits = createPayeeLimits(_perPeriodCap=10000)
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _unitLimits=unit_limits)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # simulate 9500 units already spent in period
    payee_data = createPayeeData(_totalUnitsInPeriod=9500, _periodStartBlock=boa.env.evm.patch.block_number)
    
    # need global config for isValidPayeeAndGetData call
    new_global_payee_settings = createGlobalPayeeSettings()
    
    # should be valid for 500 units
    is_valid, _ = sentintel.isValidPayeeAndGetData(
        False,
        False,
        True,
        alpha_token,
        500,
        1,
        new_payee_settings,
        new_global_payee_settings,
        payee_data
    )
    assert is_valid
    
    # should not be valid for 501 units
    is_valid, _ = sentintel.isValidPayeeAndGetData(
        False,
        False,
        True,
        alpha_token,
        501,
        1,
        new_payee_settings,
        new_global_payee_settings,
        payee_data
    )
    assert not is_valid


def test_unit_lifetime_cap(createGlobalPayeeSettings, createPayeeSettings, createPayeeLimits, createPayeeData, alpha_token, alice, sentintel, user_wallet_config):
    # add payee with 100000 units lifetime cap
    unit_limits = createPayeeLimits(_lifetimeCap=100000)
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _unitLimits=unit_limits)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # simulate 99999 units already spent lifetime
    payee_data = createPayeeData(_totalUnits=99999)
    
    # need global config for isValidPayeeAndGetData call
    new_global_payee_settings = createGlobalPayeeSettings()
    
    # should be valid for 1 unit
    is_valid, _ = sentintel.isValidPayeeAndGetData(
        False,
        False,
        True,
        alpha_token,
        1,
        1,
        new_payee_settings,
        new_global_payee_settings,
        payee_data
    )
    assert is_valid
    
    # should not be valid for 2 units
    is_valid, _ = sentintel.isValidPayeeAndGetData(
        False,
        False,
        True,
        alpha_token,
        2,
        1,
        new_payee_settings,
        new_global_payee_settings,
        payee_data
    )
    assert not is_valid


# period reset tests


def test_period_reset_after_period_ends(createGlobalPayeeSettings, createPayeeSettings, createPayeeData, alpha_token, alice, sentintel, user_wallet_config):
    # add payee with 100 block period and 5 tx limit per period
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _periodLength=100, _maxNumTxsPerPeriod=5)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # simulate payee has hit limit in past period
    boa.env.time_travel(blocks=200)
    past_period_start = boa.env.evm.patch.block_number - 150
    payee_data = createPayeeData(
        _numTxsInPeriod=5,
        _totalUsdValueInPeriod=1000,
        _totalUnitsInPeriod=500,
        _periodStartBlock=past_period_start
    )
    
    # need global config for isValidPayeeAndGetData call
    new_global_payee_settings = createGlobalPayeeSettings()
    
    # should reset period and allow transaction
    is_valid, updated_data = sentintel.isValidPayeeAndGetData(
        False,
        False,
        True,
        alpha_token,
        100,
        50,
        new_payee_settings,
        new_global_payee_settings,
        payee_data
    )
    assert is_valid

    # check period was reset
    assert updated_data.numTxsInPeriod == 1
    assert updated_data.totalUnitsInPeriod == 100
    assert updated_data.totalUsdValueInPeriod == 50
    assert updated_data.periodStartBlock == boa.env.evm.patch.block_number


def test_first_transaction_initializes_period(createGlobalPayeeSettings, createPayeeSettings, createPayeeData, alpha_token, alice, sentintel, user_wallet_config):
    # add payee
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # empty payee data (first transaction)
    payee_data = createPayeeData()
    
    # need global config for isValidPayeeAndGetData call
    new_global_payee_settings = createGlobalPayeeSettings()
    
    # should be valid and initialize period
    is_valid, updated_data = sentintel.isValidPayeeAndGetData(
        False,
        False,
        True,
        alpha_token,
        100,
        50,
        new_payee_settings,
        new_global_payee_settings,
        payee_data
    )
    assert is_valid
    assert updated_data.periodStartBlock == boa.env.evm.patch.block_number


# zero price tests


def test_fail_on_zero_price_payee_setting(createPayeeSettings, alpha_token, alice, sentintel, user_wallet, user_wallet_config):
    # add payee with failOnZeroPrice=True
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _failOnZeroPrice=True)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # should fail with zero price
    assert not sentintel.isValidPayee(user_wallet, alice, alpha_token, 100, 0)
    
    # should succeed with non-zero price
    assert sentintel.isValidPayee(user_wallet, alice, alpha_token, 100, 1)


def test_fail_on_zero_price_global_setting(createGlobalPayeeSettings, createPayeeSettings, createPayeeData, alpha_token, alice, sentintel, user_wallet_config):
    # set global settings with failOnZeroPrice=True
    new_global_payee_settings = createGlobalPayeeSettings(_failOnZeroPrice=True)
    user_wallet_config.setGlobalPayeeSettings(new_global_payee_settings, sender=paymaster.address)
    
    # add payee with failOnZeroPrice=False (payee allows zero price)
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _failOnZeroPrice=False)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # should still fail due to global setting
    empty_data = createPayeeData()
    is_valid, _ = sentintel.isValidPayeeAndGetData(
        False,
        False,
        True,
        alpha_token,
        100,
        0,
        new_payee_settings,
        new_global_payee_settings,
        empty_data
    )
    assert not is_valid


# data updates


def test_payee_data_updates_correctly(createGlobalPayeeSettings, createPayeeSettings, createPayeeData, alpha_token, alice, sentintel, user_wallet_config):
    # add payee
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # initial payee data
    boa.env.time_travel(blocks=60)
    current_block = boa.env.evm.patch.block_number
    payee_data = createPayeeData(
        _numTxsInPeriod=2,
        _totalUnitsInPeriod=200,
        _totalUsdValueInPeriod=400,
        _totalNumTxs=10,
        _totalUnits=1000,
        _totalUsdValue=2000,
        _lastTxBlock=current_block - 10,
        _periodStartBlock=current_block - 50
    )
    
    # need global config for isValidPayeeAndGetData call
    new_global_payee_settings = createGlobalPayeeSettings()
    
    # make a transaction
    is_valid, updated_data = sentintel.isValidPayeeAndGetData(
        False,
        False,
        True,
        alpha_token,
        100,
        150,
        new_payee_settings,
        new_global_payee_settings,
        payee_data
    )
    
    assert is_valid

    # check updated values
    assert updated_data.numTxsInPeriod == 3  # (2 + 1)
    assert updated_data.totalUnitsInPeriod == 300  # (200 + 100)
    assert updated_data.totalUsdValueInPeriod == 550  # (400 + 150)
    assert updated_data.totalNumTxs == 11  # (10 + 1)
    assert updated_data.totalUnits == 1100  # (1000 + 100)
    assert updated_data.totalUsdValue == 2150  # (2000 + 150)
    assert updated_data.lastTxBlock == boa.env.evm.patch.block_number


def test_non_primary_asset_does_not_update_units(createGlobalPayeeSettings, createPayeeSettings, createPayeeData, alpha_token, bravo_token, alice, sentintel, user_wallet_config):
    # add payee with alpha as primary asset
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _onlyPrimaryAsset=False)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # initial payee data
    payee_data = createPayeeData(
        _totalUnitsInPeriod=100,
        _totalUnits=500,
        _periodStartBlock=boa.env.evm.patch.block_number
    )
    
    # need global config for isValidPayeeAndGetData call
    new_global_payee_settings = createGlobalPayeeSettings()
    
    # make transaction with non-primary asset
    is_valid, updated_data = sentintel.isValidPayeeAndGetData(
        False,
        False,
        True,
        bravo_token,  # not primary asset
        200,
        50,
        new_payee_settings,
        new_global_payee_settings,
        payee_data
    )
    
    assert is_valid

    # units should not be updated for non-primary asset
    assert updated_data.totalUnitsInPeriod == 100  # unchanged
    assert updated_data.totalUnits == 500  # unchanged

    # but USD values should be updated
    assert updated_data.totalUsdValueInPeriod == 50
    assert updated_data.totalUsdValue == 50


# edge cases


def test_multiple_limits_most_restrictive_applies(createGlobalPayeeSettings, createPayeeSettings, createPayeeLimits, alpha_token, alice, sentintel, user_wallet, user_wallet_config):
    # set global settings with USD limits
    global_usd_limits = createPayeeLimits(_perTxCap=1000)
    new_global_payee_settings = createGlobalPayeeSettings(_usdLimits=global_usd_limits)
    user_wallet_config.setGlobalPayeeSettings(new_global_payee_settings, sender=paymaster.address)
    
    # add payee with stricter USD limits and unit limits
    payee_usd_limits = createPayeeLimits(_perTxCap=500)  # stricter than global
    unit_limits = createPayeeLimits(_perTxCap=100)
    new_payee_settings = createPayeeSettings(
        _primaryAsset=alpha_token,
        _usdLimits=payee_usd_limits,
        _unitLimits=unit_limits
    )
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # should fail on payee USD limit (most restrictive)
    assert not sentintel.isValidPayee(user_wallet, alice, alpha_token, 50, 600)
    
    # should fail on unit limit
    assert not sentintel.isValidPayee(user_wallet, alice, alpha_token, 101, 100)
    
    # should pass when both limits satisfied
    assert sentintel.isValidPayee(user_wallet, alice, alpha_token, 50, 100)


def test_global_tx_limits_apply_to_payees(createGlobalPayeeSettings, createPayeeSettings, createPayeeData, alpha_token, alice, sentintel, user_wallet_config):
    # set global settings with tx limits
    new_global_payee_settings = createGlobalPayeeSettings(_maxNumTxsPerPeriod=2, _txCooldownBlocks=5)
    user_wallet_config.setGlobalPayeeSettings(new_global_payee_settings, sender=paymaster.address)
    
    # add payee without specific tx limits
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # simulate 2 txs already made (hitting global limit)
    payee_data = createPayeeData(_numTxsInPeriod=2, _periodStartBlock=boa.env.evm.patch.block_number)
    
    # should fail due to global tx limit
    is_valid, _ = sentintel.isValidPayeeAndGetData(
        False,
        False,
        True,
        alpha_token,
        1,
        1,
        new_payee_settings,
        new_global_payee_settings,
        payee_data
    )
    assert not is_valid


def test_zero_limit_means_unlimited(createPayeeSettings, createPayeeLimits, alpha_token, alice, sentintel, user_wallet, user_wallet_config):
    # add payee with 0 limits (unlimited)
    zero_limits = createPayeeLimits(_perTxCap=0, _perPeriodCap=0, _lifetimeCap=0)
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _usdLimits=zero_limits, _unitLimits=zero_limits)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # should allow very large amounts
    assert sentintel.isValidPayee(user_wallet, alice, alpha_token, 999_999_999, 999_999_999)


def test_empty_primary_asset_with_only_primary_false(createPayeeSettings, alpha_token, bravo_token, alice, sentintel, user_wallet, user_wallet_config):
    # add payee with no primary asset and onlyPrimaryAsset=False
    new_payee_settings = createPayeeSettings(_primaryAsset=ZERO_ADDRESS, _onlyPrimaryAsset=False)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # should allow any asset
    assert sentintel.isValidPayee(user_wallet, alice, alpha_token, 100, 100)
    assert sentintel.isValidPayee(user_wallet, alice, bravo_token, 100, 100)


# additional scenarios


def test_exact_limit_boundaries(createPayeeSettings, createPayeeLimits, alpha_token, alice, sentintel, user_wallet, user_wallet_config):
    # test exact boundary values (at limit, not over/under)
    unit_limits = createPayeeLimits(_perTxCap=100)
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _unitLimits=unit_limits)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # exactly at limit should pass
    assert sentintel.isValidPayee(user_wallet, alice, alpha_token, 100, 1)
    
    # test USD limits at exact boundary
    usd_limits = createPayeeLimits(_perTxCap=500)
    new_payee_settings_usd = createPayeeSettings(_primaryAsset=alpha_token, _usdLimits=usd_limits)
    user_wallet_config.addPayee(alice, new_payee_settings_usd, sender=paymaster.address)
    
    # exactly at USD limit should pass
    assert sentintel.isValidPayee(user_wallet, alice, alpha_token, 1, 500)


def test_transaction_at_exact_period_end(createGlobalPayeeSettings, createPayeeSettings, createPayeeData, alpha_token, alice, sentintel, user_wallet_config):
    # test transaction right at the period boundary
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _periodLength=100)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # set up data with period about to end
    boa.env.time_travel(blocks=100)
    payee_data = createPayeeData(_periodStartBlock=boa.env.evm.patch.block_number - 99)
    
    new_global_payee_settings = createGlobalPayeeSettings()
    
    # transaction at block 99 of 100-block period (last block of period)
    is_valid, updated_data = sentintel.isValidPayeeAndGetData(
        False, False, True, alpha_token, 100, 50,
        new_payee_settings, new_global_payee_settings, payee_data
    )
    assert is_valid
    assert updated_data.periodStartBlock == boa.env.evm.patch.block_number - 99  # still in same period
    
    # next block should trigger period reset
    boa.env.time_travel(blocks=1)
    is_valid, updated_data = sentintel.isValidPayeeAndGetData(
        False, False, True, alpha_token, 100, 50,
        new_payee_settings, new_global_payee_settings, payee_data
    )
    assert is_valid
    assert updated_data.periodStartBlock == boa.env.evm.patch.block_number  # new period


def test_zero_amount_transaction(createPayeeSettings, alpha_token, alice, sentintel, user_wallet, user_wallet_config):
    # test that zero amount transactions are handled correctly
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # zero amount should still be valid (unless other restrictions apply)
    assert sentintel.isValidPayee(user_wallet, alice, alpha_token, 0, 0)
    
    # zero amount with non-zero USD value should work
    assert sentintel.isValidPayee(user_wallet, alice, alpha_token, 0, 100)


def test_cooldown_equals_period_length(createGlobalPayeeSettings, user_wallet, createPayeeSettings, createPayeeData, alpha_token, alice, sentintel, user_wallet_config):
    # edge case where cooldown equals period length
    period_length = 100
    new_payee_settings = createPayeeSettings(
        _primaryAsset=alpha_token, 
        _periodLength=period_length,
        _txCooldownBlocks=period_length
    )
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # first transaction should work
    assert sentintel.isValidPayee(user_wallet, alice, alpha_token, 1, 1)
    
    # simulate a transaction just happened
    boa.env.time_travel(blocks=10)
    payee_data = createPayeeData(
        _lastTxBlock=boa.env.evm.patch.block_number,
        _periodStartBlock=boa.env.evm.patch.block_number,
        _numTxsInPeriod=1
    )
    
    new_global_payee_settings = createGlobalPayeeSettings()
    
    # should not be valid during cooldown (which lasts the entire period)
    is_valid, _ = sentintel.isValidPayeeAndGetData(
        False, False, True, alpha_token, 1, 1,
        new_payee_settings, new_global_payee_settings, payee_data
    )
    assert not is_valid
    
    # after period ends, cooldown should be over AND period should reset
    boa.env.time_travel(blocks=period_length)
    is_valid, updated_data = sentintel.isValidPayeeAndGetData(
        False, False, True, alpha_token, 1, 1,
        new_payee_settings, new_global_payee_settings, payee_data
    )
    assert is_valid
    assert updated_data.periodStartBlock == boa.env.evm.patch.block_number


def test_multiple_period_resets(createGlobalPayeeSettings, createPayeeSettings, createPayeeData, alpha_token, alice, sentintel, user_wallet_config):
    # test behavior when multiple periods have passed
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _periodLength=50)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # simulate data from 3 periods ago
    boa.env.time_travel(blocks=200)
    old_period_start = boa.env.evm.patch.block_number - 150
    payee_data = createPayeeData(
        _periodStartBlock=old_period_start,
        _numTxsInPeriod=5,
        _totalUnitsInPeriod=1000,
        _totalUsdValueInPeriod=2000
    )
    
    new_global_payee_settings = createGlobalPayeeSettings()
    
    # should reset to current period
    is_valid, updated_data = sentintel.isValidPayeeAndGetData(
        False, False, True, alpha_token, 100, 50,
        new_payee_settings, new_global_payee_settings, payee_data
    )
    assert is_valid
    assert updated_data.periodStartBlock == boa.env.evm.patch.block_number

    # period data should be reset
    assert updated_data.numTxsInPeriod == 1
    assert updated_data.totalUnitsInPeriod == 100
    assert updated_data.totalUsdValueInPeriod == 50


def test_payee_expires_at_current_block(createPayeeSettings, alpha_token, alice, sentintel, user_wallet, user_wallet_config):
    # edge case: payee expires at exactly the current block
    current_block = boa.env.evm.patch.block_number
    new_payee_settings = createPayeeSettings(
        _startBlock=current_block,
        _expiryBlock=current_block,  # expires at current block
        _primaryAsset=alpha_token
    )
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # should not be valid at current block (expiry <= current block)
    assert not sentintel.isValidPayee(user_wallet, alice, alpha_token, 1, 1)
    
    # test with expiry = current block + 1 (should be valid for exactly current block)
    new_payee_settings_2 = createPayeeSettings(
        _startBlock=current_block,
        _expiryBlock=current_block + 1,  # valid only for current block
        _primaryAsset=alpha_token
    )
    user_wallet_config.addPayee(alice, new_payee_settings_2, sender=paymaster.address)
    
    # should be valid at current block
    assert sentintel.isValidPayee(user_wallet, alice, alpha_token, 1, 1)
    
    # advance one block - should now be invalid (current block >= expiry)
    boa.env.time_travel(blocks=1)
    assert not sentintel.isValidPayee(user_wallet, alice, alpha_token, 1, 1)


def test_global_and_payee_cooldowns_both_apply(createGlobalPayeeSettings, createPayeeSettings, createPayeeData, alpha_token, alice, sentintel, user_wallet_config):
    # test when both global and payee cooldowns are set
    new_global_payee_settings = createGlobalPayeeSettings(_txCooldownBlocks=10)
    user_wallet_config.setGlobalPayeeSettings(new_global_payee_settings, sender=paymaster.address)
    
    # payee has shorter cooldown - global should still apply
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _txCooldownBlocks=5)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # simulate recent transaction
    boa.env.time_travel(blocks=20)
    current_block = boa.env.evm.patch.block_number
    payee_data = createPayeeData(_lastTxBlock=current_block - 7)
    
    # 7 blocks ago - payee cooldown (5) passed but global (10) not passed
    is_valid, _ = sentintel.isValidPayeeAndGetData(
        False, False, True, alpha_token, 1, 1,
        new_payee_settings, new_global_payee_settings, payee_data
    )
    assert not is_valid
    
    # after global cooldown passes
    payee_data_after = createPayeeData(_lastTxBlock=current_block - 11)
    is_valid, _ = sentintel.isValidPayeeAndGetData(
        False, False, True, alpha_token, 1, 1,
        new_payee_settings, new_global_payee_settings, payee_data_after
    )
    assert is_valid


def test_very_long_inactive_period(createGlobalPayeeSettings, createPayeeSettings, createPayeeData, alpha_token, alice, sentintel, user_wallet_config):
    # test payee that hasn't been used for many periods
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _periodLength=100)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # simulate very old data (1000 blocks ago)
    boa.env.time_travel(blocks=1100)
    very_old_data = createPayeeData(
        _periodStartBlock=boa.env.evm.patch.block_number - 1000,
        _lastTxBlock=boa.env.evm.patch.block_number - 1000,
        _totalUnits=50000,
        _totalUsdValue=100000,
        _totalNumTxs=100
    )
    
    new_global_payee_settings = createGlobalPayeeSettings()
    
    # should still work and reset period
    is_valid, updated_data = sentintel.isValidPayeeAndGetData(
        False, False, True, alpha_token, 100, 50,
        new_payee_settings, new_global_payee_settings, very_old_data
    )
    assert is_valid
    assert updated_data.periodStartBlock == boa.env.evm.patch.block_number

    # lifetime data should persist
    assert updated_data.totalUnits == 50100  # 50000 + 100
    assert updated_data.totalUsdValue == 100050  # 100000 + 50
    assert updated_data.totalNumTxs == 101  # 100 + 1


def test_all_limits_zero_means_unlimited(createGlobalPayeeSettings, user_wallet, createPayeeSettings, createPayeeLimits, alpha_token, alice, sentintel, user_wallet_config):
    # comprehensive test of zero = unlimited behavior
    zero_limits = createPayeeLimits(_perTxCap=0, _perPeriodCap=0, _lifetimeCap=0)
    new_global_payee_settings = createGlobalPayeeSettings(
        _maxNumTxsPerPeriod=0,
        _txCooldownBlocks=0,
        _usdLimits=zero_limits
    )
    user_wallet_config.setGlobalPayeeSettings(new_global_payee_settings, sender=paymaster.address)
    
    new_payee_settings = createPayeeSettings(
        _primaryAsset=alpha_token,
        _maxNumTxsPerPeriod=0,
        _txCooldownBlocks=0,
        _unitLimits=zero_limits,
        _usdLimits=zero_limits
    )
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # should allow massive amounts and many transactions
    assert sentintel.isValidPayee(user_wallet, alice, alpha_token, 10**18, 10**18)
    assert sentintel.isValidPayee(user_wallet, alice, alpha_token, 10**24, 10**24)


def test_lifetime_limits_persist_across_period_resets(createGlobalPayeeSettings, createPayeeSettings, createPayeeData, createPayeeLimits, alpha_token, alice, sentintel, user_wallet_config):
    # ensure lifetime limits aren't reset with period
    unit_limits = createPayeeLimits(_lifetimeCap=1000)
    new_payee_settings = createPayeeSettings(
        _primaryAsset=alpha_token,
        _periodLength=50,
        _unitLimits=unit_limits
    )
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # simulate old period with 900 lifetime units used
    boa.env.time_travel(blocks=100)
    old_data = createPayeeData(
        _totalUnits=900,
        _periodStartBlock=boa.env.evm.patch.block_number - 60,
        _totalUnitsInPeriod=100  # this should reset
    )
    
    new_global_payee_settings = createGlobalPayeeSettings()
    
    # even after period reset, lifetime limit should apply
    is_valid, updated_data = sentintel.isValidPayeeAndGetData(
        False, False, True, alpha_token, 200, 1,
        new_payee_settings, new_global_payee_settings, old_data
    )
    assert not is_valid  # would exceed lifetime cap (900 + 200 > 1000)
    
    # but smaller amount should work
    is_valid, updated_data = sentintel.isValidPayeeAndGetData(
        False, False, True, alpha_token, 99, 1,
        new_payee_settings, new_global_payee_settings, old_data
    )
    assert is_valid
    assert updated_data.totalUnits == 999  # 900 + 99
    assert updated_data.totalUnitsInPeriod == 99  # period was reset