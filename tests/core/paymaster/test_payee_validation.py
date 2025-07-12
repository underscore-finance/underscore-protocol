import pytest
import boa

from constants import ZERO_ADDRESS


def test_payee_example_test(createGlobalPayeeSettings, charlie, alpha_token, bravo_token, bob, createPayeeLimits, createPayeeSettings, paymaster, user_wallet, user_wallet_config, alice):

    # set global payee settings
    new_global_payee_settings = createGlobalPayeeSettings(_canPayOwner=False)
    user_wallet_config.setGlobalPayeeSettings(new_global_payee_settings, sender=paymaster.address)

    # add payee
    unit_limits = createPayeeLimits(_perTxCap=10)
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _onlyPrimaryAsset=True, _unitLimits=unit_limits)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)

    # cannot pay owner
    assert not paymaster.isValidPayee(user_wallet, bob, alpha_token, 1, 1)

    # not payee
    assert not paymaster.isValidPayee(user_wallet, charlie, alpha_token, 1, 1)

    # payee -- not primary asset
    assert not paymaster.isValidPayee(user_wallet, alice, bravo_token, 9, 1)

    # payee -- primary asset
    assert paymaster.isValidPayee(user_wallet, alice, alpha_token, 9, 1)

    # payee -- over limit
    assert not paymaster.isValidPayee(user_wallet, alice, alpha_token, 11, 1)


# whitelist tests


def test_whitelisted_recipient_always_valid(alpha_token, bravo_token, delta_token, paymaster, user_wallet, user_wallet_config, alice):
    # add alice to whitelist
    user_wallet_config.confirmWhitelistAddr(alice, sender=paymaster.address)
    
    # whitelisted addresses should always be valid regardless of amounts or assets
    assert paymaster.isValidPayee(user_wallet, alice, alpha_token, 1_000_000, 1_000_000)
    assert paymaster.isValidPayee(user_wallet, alice, bravo_token, 999_999_999, 999_999_999)
    assert paymaster.isValidPayee(user_wallet, alice, delta_token, 1, 1)
    assert paymaster.isValidPayee(user_wallet, alice, ZERO_ADDRESS, 0, 0)  # even with zero address


def test_non_whitelisted_non_payee_invalid(alpha_token, paymaster, user_wallet, sally):
    # sally is neither whitelisted nor a payee
    assert not paymaster.isValidPayee(user_wallet, sally, alpha_token, 1, 1)


# owner tests


def test_owner_payment_with_canPayOwner_true(createGlobalPayeeSettings, alpha_token, bob, paymaster, user_wallet, user_wallet_config):
    # set global payee settings with canPayOwner=True
    new_global_payee_settings = createGlobalPayeeSettings(_canPayOwner=True)
    user_wallet_config.setGlobalPayeeSettings(new_global_payee_settings, sender=paymaster.address)
    
    # owner (bob) should be valid payee
    assert paymaster.isValidPayee(user_wallet, bob, alpha_token, 100, 100)


def test_owner_payment_with_canPayOwner_false(createGlobalPayeeSettings, alpha_token, bob, paymaster, user_wallet, user_wallet_config):
    # set global payee settings with canPayOwner=False
    new_global_payee_settings = createGlobalPayeeSettings(_canPayOwner=False)
    user_wallet_config.setGlobalPayeeSettings(new_global_payee_settings, sender=paymaster.address)
    
    # owner (bob) should not be valid payee
    assert not paymaster.isValidPayee(user_wallet, bob, alpha_token, 100, 100)


# activation / expiry tests


def test_payee_not_yet_active(createPayeeSettings, alpha_token, alice, paymaster, user_wallet, user_wallet_config):
    # add payee with future start block
    future_start = boa.env.evm.patch.block_number + 1000
    new_payee_settings = createPayeeSettings(_startBlock=future_start)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # payee should not be valid before start block
    assert not paymaster.isValidPayee(user_wallet, alice, alpha_token, 1, 1)


def test_payee_active(createPayeeSettings, alpha_token, alice, paymaster, user_wallet, user_wallet_config):
    # add payee with current block as start
    current_block = boa.env.evm.patch.block_number
    new_payee_settings = createPayeeSettings(_startBlock=current_block)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # payee should be valid at start block
    assert paymaster.isValidPayee(user_wallet, alice, alpha_token, 1, 1)


def test_payee_expired(createPayeeSettings, alpha_token, alice, paymaster, user_wallet, user_wallet_config):
    # add payee with short expiry
    current_block = boa.env.evm.patch.block_number
    new_payee_settings = createPayeeSettings(_startBlock=current_block, _expiryBlock=current_block + 10, _primaryAsset=alpha_token)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # travel past expiry
    boa.env.time_travel(blocks=11)
    
    # payee should not be valid after expiry
    assert not paymaster.isValidPayee(user_wallet, alice, alpha_token, 1, 1)


# asset restrictions


def test_primary_asset_only_restriction(createPayeeSettings, alpha_token, bravo_token, alice, paymaster, user_wallet, user_wallet_config):
    # add payee with onlyPrimaryAsset=True
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _onlyPrimaryAsset=True)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # should be valid for primary asset
    assert paymaster.isValidPayee(user_wallet, alice, alpha_token, 1, 1)
    
    # should not be valid for other assets
    assert not paymaster.isValidPayee(user_wallet, alice, bravo_token, 1, 1)


def test_no_primary_asset_restriction(createPayeeSettings, alpha_token, bravo_token, alice, paymaster, user_wallet, user_wallet_config):
    # add payee without asset restrictions
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _onlyPrimaryAsset=False)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # should be valid for any asset
    assert paymaster.isValidPayee(user_wallet, alice, alpha_token, 1, 1)
    assert paymaster.isValidPayee(user_wallet, alice, bravo_token, 1, 1)


# transaction limits


def test_max_txs_per_period_limit(createGlobalPayeeSettings, createPayeeSettings, createPayeeData, alpha_token, alice, paymaster, user_wallet_config):
    # add payee with max 3 txs per period
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _maxNumTxsPerPeriod=3)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # simulate payee has already made 3 txs in period
    payee_data = createPayeeData(_numTxsInPeriod=3, _periodStartBlock=boa.env.evm.patch.block_number)
    
    # need global config for isValidPayeeAndGetData call
    new_global_payee_settings = createGlobalPayeeSettings()
    
    # should not be valid when limit reached
    is_valid, _ = paymaster.isValidPayeeAndGetData(
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


def test_tx_cooldown_blocks(createGlobalPayeeSettings, createPayeeSettings, createPayeeData, alpha_token, alice, paymaster, user_wallet_config):
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
    is_valid, _ = paymaster.isValidPayeeAndGetData(
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
    is_valid, _ = paymaster.isValidPayeeAndGetData(
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


def test_usd_per_tx_cap(createPayeeSettings, createPayeeLimits, alpha_token, alice, paymaster, user_wallet, user_wallet_config):
    # add payee with $100 per tx cap
    usd_limits = createPayeeLimits(_perTxCap=100)
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _usdLimits=usd_limits)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # should be valid under limit
    assert paymaster.isValidPayee(user_wallet, alice, alpha_token, 1, 99)
    
    # should not be valid over limit
    assert not paymaster.isValidPayee(user_wallet, alice, alpha_token, 1, 101)


def test_usd_per_period_cap(createGlobalPayeeSettings, createPayeeSettings, createPayeeLimits, createPayeeData, alpha_token, alice, paymaster, user_wallet_config):
    # add payee with $1000 per period cap
    usd_limits = createPayeeLimits(_perPeriodCap=1000)
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _usdLimits=usd_limits)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # simulate $800 already spent in period
    payee_data = createPayeeData(_totalUsdValueInPeriod=800, _periodStartBlock=boa.env.evm.patch.block_number)
    
    # need global config for isValidPayeeAndGetData call
    new_global_payee_settings = createGlobalPayeeSettings()
    
    # should be valid for $199 (total would be $999)
    is_valid, _ = paymaster.isValidPayeeAndGetData(
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
    is_valid, _ = paymaster.isValidPayeeAndGetData(
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


def test_usd_lifetime_cap(createGlobalPayeeSettings, createPayeeSettings, createPayeeLimits, createPayeeData, alpha_token, alice, paymaster, user_wallet_config):
    # add payee with $10000 lifetime cap
    usd_limits = createPayeeLimits(_lifetimeCap=10000)
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _usdLimits=usd_limits)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # simulate $9900 already spent lifetime
    payee_data = createPayeeData(_totalUsdValue=9900)
    
    # need global config for isValidPayeeAndGetData call
    new_global_payee_settings = createGlobalPayeeSettings()
    
    # should be valid for $100
    is_valid, _ = paymaster.isValidPayeeAndGetData(
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
    is_valid, _ = paymaster.isValidPayeeAndGetData(
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


def test_unit_per_tx_cap(createPayeeSettings, createPayeeLimits, alpha_token, alice, paymaster, user_wallet, user_wallet_config):
    # add payee with 1000 units per tx cap
    unit_limits = createPayeeLimits(_perTxCap=1000)
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _unitLimits=unit_limits)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # should be valid under limit
    assert paymaster.isValidPayee(user_wallet, alice, alpha_token, 999, 1)
    
    # should not be valid over limit
    assert not paymaster.isValidPayee(user_wallet, alice, alpha_token, 1001, 1)


def test_unit_limits_only_apply_to_primary_asset(createPayeeSettings, createPayeeLimits, alpha_token, bravo_token, alice, paymaster, user_wallet, user_wallet_config):
    # add payee with unit limits on alpha token (primary asset)
    unit_limits = createPayeeLimits(_perTxCap=100)
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _unitLimits=unit_limits, _onlyPrimaryAsset=False)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # unit limit should apply to primary asset
    assert not paymaster.isValidPayee(user_wallet, alice, alpha_token, 101, 1)
    
    # unit limit should NOT apply to other assets
    assert paymaster.isValidPayee(user_wallet, alice, bravo_token, 1000, 1)


def test_unit_per_period_cap(createGlobalPayeeSettings, createPayeeSettings, createPayeeLimits, createPayeeData, alpha_token, alice, paymaster, user_wallet_config):
    # add payee with 10000 units per period cap
    unit_limits = createPayeeLimits(_perPeriodCap=10000)
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _unitLimits=unit_limits)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # simulate 9500 units already spent in period
    payee_data = createPayeeData(_totalUnitsInPeriod=9500, _periodStartBlock=boa.env.evm.patch.block_number)
    
    # need global config for isValidPayeeAndGetData call
    new_global_payee_settings = createGlobalPayeeSettings()
    
    # should be valid for 500 units
    is_valid, _ = paymaster.isValidPayeeAndGetData(
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
    is_valid, _ = paymaster.isValidPayeeAndGetData(
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


def test_unit_lifetime_cap(createGlobalPayeeSettings, createPayeeSettings, createPayeeLimits, createPayeeData, alpha_token, alice, paymaster, user_wallet_config):
    # add payee with 100000 units lifetime cap
    unit_limits = createPayeeLimits(_lifetimeCap=100000)
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _unitLimits=unit_limits)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # simulate 99999 units already spent lifetime
    payee_data = createPayeeData(_totalUnits=99999)
    
    # need global config for isValidPayeeAndGetData call
    new_global_payee_settings = createGlobalPayeeSettings()
    
    # should be valid for 1 unit
    is_valid, _ = paymaster.isValidPayeeAndGetData(
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
    is_valid, _ = paymaster.isValidPayeeAndGetData(
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


def test_period_reset_after_period_ends(createGlobalPayeeSettings, createPayeeSettings, createPayeeData, alpha_token, alice, paymaster, user_wallet_config):
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
    is_valid, updated_data = paymaster.isValidPayeeAndGetData(
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


def test_first_transaction_initializes_period(createGlobalPayeeSettings, createPayeeSettings, createPayeeData, alpha_token, alice, paymaster, user_wallet_config):
    # add payee
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # empty payee data (first transaction)
    payee_data = createPayeeData()
    
    # need global config for isValidPayeeAndGetData call
    new_global_payee_settings = createGlobalPayeeSettings()
    
    # should be valid and initialize period
    is_valid, updated_data = paymaster.isValidPayeeAndGetData(
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


def test_fail_on_zero_price_payee_setting(createPayeeSettings, alpha_token, alice, paymaster, user_wallet, user_wallet_config):
    # add payee with failOnZeroPrice=True
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _failOnZeroPrice=True)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # should fail with zero price
    assert not paymaster.isValidPayee(user_wallet, alice, alpha_token, 100, 0)
    
    # should succeed with non-zero price
    assert paymaster.isValidPayee(user_wallet, alice, alpha_token, 100, 1)


def test_fail_on_zero_price_global_setting(createGlobalPayeeSettings, createPayeeSettings, createPayeeData, alpha_token, alice, paymaster, user_wallet_config):
    # set global settings with failOnZeroPrice=True
    new_global_payee_settings = createGlobalPayeeSettings(_failOnZeroPrice=True)
    user_wallet_config.setGlobalPayeeSettings(new_global_payee_settings, sender=paymaster.address)
    
    # add payee with failOnZeroPrice=False (payee allows zero price)
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _failOnZeroPrice=False)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # should still fail due to global setting
    empty_data = createPayeeData()
    is_valid, _ = paymaster.isValidPayeeAndGetData(
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


def test_payee_data_updates_correctly(createGlobalPayeeSettings, createPayeeSettings, createPayeeData, alpha_token, alice, paymaster, user_wallet_config):
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
    is_valid, updated_data = paymaster.isValidPayeeAndGetData(
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


def test_non_primary_asset_does_not_update_units(createGlobalPayeeSettings, createPayeeSettings, createPayeeData, alpha_token, bravo_token, alice, paymaster, user_wallet_config):
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
    is_valid, updated_data = paymaster.isValidPayeeAndGetData(
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


def test_multiple_limits_most_restrictive_applies(createGlobalPayeeSettings, createPayeeSettings, createPayeeLimits, alpha_token, alice, paymaster, user_wallet, user_wallet_config):
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
    assert not paymaster.isValidPayee(user_wallet, alice, alpha_token, 50, 600)
    
    # should fail on unit limit
    assert not paymaster.isValidPayee(user_wallet, alice, alpha_token, 101, 100)
    
    # should pass when both limits satisfied
    assert paymaster.isValidPayee(user_wallet, alice, alpha_token, 50, 100)


def test_global_tx_limits_apply_to_payees(createGlobalPayeeSettings, createPayeeSettings, createPayeeData, alpha_token, alice, paymaster, user_wallet_config):
    # set global settings with tx limits
    new_global_payee_settings = createGlobalPayeeSettings(_maxNumTxsPerPeriod=2, _txCooldownBlocks=5)
    user_wallet_config.setGlobalPayeeSettings(new_global_payee_settings, sender=paymaster.address)
    
    # add payee without specific tx limits
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # simulate 2 txs already made (hitting global limit)
    payee_data = createPayeeData(_numTxsInPeriod=2, _periodStartBlock=boa.env.evm.patch.block_number)
    
    # should fail due to global tx limit
    is_valid, _ = paymaster.isValidPayeeAndGetData(
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


def test_zero_limit_means_unlimited(createPayeeSettings, createPayeeLimits, alpha_token, alice, paymaster, user_wallet, user_wallet_config):
    # add payee with 0 limits (unlimited)
    zero_limits = createPayeeLimits(_perTxCap=0, _perPeriodCap=0, _lifetimeCap=0)
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _usdLimits=zero_limits, _unitLimits=zero_limits)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # should allow very large amounts
    assert paymaster.isValidPayee(user_wallet, alice, alpha_token, 999_999_999, 999_999_999)


def test_empty_primary_asset_with_only_primary_false(createPayeeSettings, alpha_token, bravo_token, alice, paymaster, user_wallet, user_wallet_config):
    # add payee with no primary asset and onlyPrimaryAsset=False
    new_payee_settings = createPayeeSettings(_primaryAsset=ZERO_ADDRESS, _onlyPrimaryAsset=False)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)
    
    # should allow any asset
    assert paymaster.isValidPayee(user_wallet, alice, alpha_token, 100, 100)
    assert paymaster.isValidPayee(user_wallet, alice, bravo_token, 100, 100)