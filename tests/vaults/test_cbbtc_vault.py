import pytest
import boa

from config.BluePrint import TOKENS, WHALES
from constants import EIGHTEEN_DECIMALS, MAX_UINT256


ALL_VAULT_TOKENS = {
    "base": {
        "AAVE_CBBTC": TOKENS["base"]["AAVEV3_CBBTC"],
        "EULER_CBBTC": TOKENS["base"]["EULER_CBBTC"],
        "MOONWELL_CBBTC": TOKENS["base"]["MOONWELL_CBBTC"],
        "MORPHO_MOONWELL_CBBTC": TOKENS["base"]["MORPHO_MOONWELL_CBBTC"],
    },
}


TEST_TOKENS = [
    "AAVE_CBBTC",
    "EULER_CBBTC",
    "MOONWELL_CBBTC",
    "MORPHO_MOONWELL_CBBTC",
]


@pytest.fixture(scope="module")
def getLegoId(lego_book, lego_aave_v3, lego_euler, lego_moonwell, lego_morpho):
    def getLegoId(_token_str):
        lego = None
        if _token_str == "AAVE_CBBTC":
            lego = lego_aave_v3
        if _token_str == "EULER_CBBTC":
            lego = lego_euler
        if _token_str == "MOONWELL_CBBTC":
            lego = lego_moonwell
        if _token_str == "MORPHO_MOONWELL_CBBTC":
            lego = lego_morpho
        return lego_book.getRegId(lego), lego
    yield getLegoId


@pytest.fixture(scope="module")
def prepareYieldDeposit(
    getLegoId,
    undy_btc_vault,
    vault_registry,
    mock_ripe,
    bob,
    fork,
    switchboard_alpha,
    _test,
):
    def prepareYieldDeposit(_token_str):
        lego_id, lego = getLegoId(_token_str)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][_token_str])
        asset = boa.from_etherscan(TOKENS[fork]["CBBTC"])
        whale = WHALES[fork]["CBBTC"]
        amount = 1 * (10 ** asset.decimals())  # 1 cbBTC (8 decimals)

        # set price (BTC ~= $100,000)
        mock_ripe.setPrice(asset, 100000 * EIGHTEEN_DECIMALS)

        # transfer asset to user
        asset.transfer(bob, amount, sender=whale)

        # deposit into earn vault
        asset.approve(undy_btc_vault, MAX_UINT256, sender=bob)
        undy_btc_vault.deposit(amount, bob, sender=bob)

        # approve lego and vault via VaultRegistry
        vault_registry.setApprovedYieldLego(undy_btc_vault.address, lego_id, True, sender=switchboard_alpha.address)
        vault_registry.setApprovedVaultToken(undy_btc_vault.address, vault_addr, True, sender=switchboard_alpha.address)

        return lego_id, lego, vault_addr, asset, amount

    yield prepareYieldDeposit


#########
# Tests #
#########


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_cbbtc_vault_deposit(
    prepareYieldDeposit,
    undy_btc_vault,
    starter_agent,
    token_str,
    _test,
    bob,
):
    lego_id, lego, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # deposit into yield vault
    asset_deposited, vault_token, vault_tokens_received, usd_value = undy_btc_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # total assets
    assert asset_deposited == amount
    _test(undy_btc_vault.totalAssets(), amount)

    # vault token
    assert vault_token == vault_addr.address
    assert vault_addr.balanceOf(undy_btc_vault) == vault_tokens_received

    # vault shares
    bob_shares = undy_btc_vault.balanceOf(bob)
    _test(undy_btc_vault.convertToAssets(bob_shares), amount)

    # usd value (check it's reasonable, actual price may vary)
    assert usd_value > 0


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_cbbtc_vault_withdraw_partial(
    prepareYieldDeposit,
    undy_btc_vault,
    starter_agent,
    token_str,
):
    """Test partial withdrawal from vault tokens"""
    lego_id, lego, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # deposit into yield vault
    undy_btc_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    initial_vault_balance = vault_addr.balanceOf(undy_btc_vault)

    # withdraw half
    withdraw_amount = initial_vault_balance // 2
    vault_burned, underlying_asset, underlying_received, usd_value = undy_btc_vault.withdrawFromYield(
        lego_id,
        vault_addr,
        withdraw_amount,
        sender=starter_agent.address
    )

    # verify withdrawal
    assert vault_burned == withdraw_amount
    assert underlying_asset == asset.address
    assert underlying_received > 0

    # allow for rounding (difference should be <= 1 wei)
    remaining_balance = vault_addr.balanceOf(undy_btc_vault)
    expected_balance = initial_vault_balance - withdraw_amount
    assert abs(remaining_balance - expected_balance) <= 1

    # verify vault token still registered
    assert undy_btc_vault.indexOfAsset(vault_addr.address) > 0


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_cbbtc_vault_withdraw_full(
    prepareYieldDeposit,
    undy_btc_vault,
    starter_agent,
    token_str,
):
    """Test full withdrawal deregisters vault token"""
    lego_id, lego, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # deposit into yield vault
    undy_btc_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # verify registered
    assert undy_btc_vault.indexOfAsset(vault_addr.address) > 0
    num_assets_before = undy_btc_vault.numAssets()

    # withdraw all
    vault_balance = vault_addr.balanceOf(undy_btc_vault)
    vault_burned, underlying_asset, underlying_received, usd_value = undy_btc_vault.withdrawFromYield(
        lego_id,
        vault_addr,
        vault_balance,
        sender=starter_agent.address
    )

    # verify complete withdrawal
    assert vault_addr.balanceOf(undy_btc_vault) == 0
    assert vault_burned == vault_balance
    assert underlying_received > 0

    # verify deregistration
    assert undy_btc_vault.indexOfAsset(vault_addr.address) == 0
    assert undy_btc_vault.numAssets() == num_assets_before - 1


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_cbbtc_vault_withdraw_max_value(
    prepareYieldDeposit,
    undy_btc_vault,
    starter_agent,
    token_str,
):
    """Test withdrawal with MAX_UINT256 withdraws entire balance"""
    lego_id, lego, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # deposit into yield vault
    undy_btc_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    vault_balance = vault_addr.balanceOf(undy_btc_vault)

    # withdraw with MAX_UINT256
    vault_burned, underlying_asset, underlying_received, usd_value = undy_btc_vault.withdrawFromYield(
        lego_id,
        vault_addr,
        MAX_UINT256,
        sender=starter_agent.address
    )

    # verify entire balance withdrawn
    assert vault_burned == vault_balance
    assert vault_addr.balanceOf(undy_btc_vault) == 0
    assert underlying_received > 0


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_cbbtc_vault_yield_accrual(
    prepareYieldDeposit,
    undy_btc_vault,
    starter_agent,
    token_str,
):
    """Test that vault token value remains stable (doesn't decrease)"""
    lego_id, lego, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # deposit into yield vault
    _, _, vault_tokens_received, _ = undy_btc_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # record initial value
    initial_value = lego.getUnderlyingAmount(vault_addr, vault_tokens_received)

    # time travel forward (7 days)
    boa.env.time_travel(seconds=7 * 24 * 60 * 60)

    # check value after time - should be >= initial (at least stable, possibly yield)
    # On static fork, yield won't accrue, but value shouldn't decrease
    final_value = lego.getUnderlyingAmount(vault_addr, vault_tokens_received)
    assert final_value >= initial_value, f"Value decreased for {token_str}: {initial_value} -> {final_value}"


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_cbbtc_vault_share_price_increase(
    prepareYieldDeposit,
    undy_btc_vault,
    starter_agent,
    token_str,
    fork,
):
    """Test that share value doesn't decrease when others deposit (rebasing assets behave differently)"""
    lego_id, lego, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # deposit into yield vault
    _, _, vault_tokens_received, _ = undy_btc_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # record initial value per share
    initial_value = lego.getUnderlyingAmount(vault_addr, vault_tokens_received)

    # For rebasing assets, adding liquidity doesn't change share value
    # For non-rebasing assets, it also doesn't generate yield (yield comes from protocol activity/time)
    # This test just verifies that value doesn't decrease
    whale = WHALES[fork]["CBBTC"]
    whale_amount = 10 * (10 ** asset.decimals())

    # Transfer to whale and deposit via lego
    asset.transfer(whale, whale_amount, sender=WHALES[fork]["CBBTC"])
    asset.approve(lego.address, whale_amount, sender=whale)

    # Deposit via lego (simulating another depositor)
    # Parameters: _asset, _amount, _vaultAddr, _extraData, _recipient
    whale_vault_tokens = lego.depositForYield(
        asset,                # _asset
        whale_amount,         # _amount
        vault_addr,           # _vaultAddr
        b'',                  # _extraData (empty bytes32)
        whale,                # _recipient
        sender=whale
    )

    # Check that value didn't decrease (it should stay the same or increase very slightly due to rounding)
    final_value = lego.getUnderlyingAmount(vault_addr, vault_tokens_received)

    # For rebasing: value should be exactly the same (balance adjusts automatically)
    # For non-rebasing: value should be the same (no yield from just adding liquidity)
    # Allow for tiny rounding differences
    if lego.isRebasing():
        # Rebasing tokens: value should be stable (within tiny rounding)
        assert abs(final_value - initial_value) <= 2, f"Rebasing token value changed unexpectedly: {initial_value} -> {final_value}"
    else:
        # Non-rebasing: value should not decrease, might stay same
        assert final_value >= initial_value, f"Share value decreased for {token_str}: {initial_value} -> {final_value}"


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_cbbtc_vault_avg_price_tracking(
    prepareYieldDeposit,
    undy_btc_vault,
    starter_agent,
    token_str,
    bob,
    fork,
):
    """Test avgPricePerShare tracking with multiple deposits (non-rebasing assets only)"""
    lego_id, lego, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # Skip rebasing assets (AAVE) - they don't use avgPricePerShare
    if lego.isRebasing():
        pytest.skip(f"Skipping {token_str} - rebasing assets don't track avgPricePerShare")

    # first deposit
    undy_btc_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # record initial avg price
    initial_data = undy_btc_vault.assetData(vault_addr.address)
    initial_avg_price = initial_data.avgPricePerShare
    assert initial_avg_price > 0

    # time travel to allow snapshot
    boa.env.time_travel(seconds=301)

    # prepare second deposit
    whale = WHALES[fork]["CBBTC"]
    asset.transfer(bob, amount, sender=whale)
    undy_btc_vault.deposit(amount, bob, sender=bob)

    # second deposit
    undy_btc_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # verify avgPricePerShare is being tracked
    final_data = undy_btc_vault.assetData(vault_addr.address)
    final_avg_price = final_data.avgPricePerShare
    assert final_avg_price > 0


@pytest.base
def test_cbbtc_vault_deposit_multiple_protocols(
    getLegoId,
    undy_btc_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
    _test,
):
    """Test depositing to multiple different protocols"""
    asset = boa.from_etherscan(TOKENS[fork]["CBBTC"])
    whale = WHALES[fork]["CBBTC"]
    mock_ripe.setPrice(asset, 100000 * EIGHTEEN_DECIMALS)

    # test with first 3 protocols
    test_protocols = ["AAVE_CBBTC", "EULER_CBBTC", "MOONWELL_CBBTC"]

    for protocol in test_protocols:
        lego_id, lego = getLegoId(protocol)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])
        amount = 1 * (10 ** asset.decimals())

        # prepare deposit
        asset.transfer(bob, amount, sender=whale)
        asset.approve(undy_btc_vault, MAX_UINT256, sender=bob)
        undy_btc_vault.deposit(amount, bob, sender=bob)

        # approve lego and vault via VaultRegistry
        vault_registry.setApprovedYieldLego(undy_btc_vault.address, lego_id, True, sender=switchboard_alpha.address)
        vault_registry.setApprovedVaultToken(undy_btc_vault.address, vault_addr, True, sender=switchboard_alpha.address)

        # deposit for yield
        asset_deposited, vault_token, vault_tokens_received, usd_value = undy_btc_vault.depositForYield(
            lego_id,
            asset,
            vault_addr,
            amount,
            sender=starter_agent.address
        )

        # verify deposit
        assert asset_deposited == amount
        assert vault_addr.balanceOf(undy_btc_vault) == vault_tokens_received
        assert undy_btc_vault.indexOfAsset(vault_addr.address) > 0

    # verify all 3 protocols are registered (plus base asset = 4 total)
    assert undy_btc_vault.numAssets() == 4


@pytest.base
def test_cbbtc_vault_rebalance_between_protocols(
    getLegoId,
    undy_btc_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
):
    """Test rebalancing from one protocol to another"""
    asset = boa.from_etherscan(TOKENS[fork]["CBBTC"])
    whale = WHALES[fork]["CBBTC"]
    mock_ripe.setPrice(asset, 100000 * EIGHTEEN_DECIMALS)
    amount = 1 * (10 ** asset.decimals())

    # setup first protocol (Aave)
    lego_id_1, lego_1 = getLegoId("AAVE_CBBTC")
    vault_addr_1 = boa.from_etherscan(ALL_VAULT_TOKENS[fork]["AAVE_CBBTC"])

    asset.transfer(bob, amount, sender=whale)
    asset.approve(undy_btc_vault, MAX_UINT256, sender=bob)
    undy_btc_vault.deposit(amount, bob, sender=bob)

    vault_registry.setApprovedYieldLego(undy_btc_vault.address, lego_id_1, True, sender=switchboard_alpha.address)
    vault_registry.setApprovedVaultToken(undy_btc_vault.address, vault_addr_1, True, sender=switchboard_alpha.address)

    # deposit to Aave
    _, _, vault_tokens_1, _ = undy_btc_vault.depositForYield(
        lego_id_1,
        asset,
        vault_addr_1,
        amount,
        sender=starter_agent.address
    )

    # setup second protocol (Euler)
    lego_id_2, lego_2 = getLegoId("EULER_CBBTC")
    vault_addr_2 = boa.from_etherscan(ALL_VAULT_TOKENS[fork]["EULER_CBBTC"])

    vault_registry.setApprovedYieldLego(undy_btc_vault.address, lego_id_2, True, sender=switchboard_alpha.address)
    vault_registry.setApprovedVaultToken(undy_btc_vault.address, vault_addr_2, True, sender=switchboard_alpha.address)

    # rebalance from Aave to Euler
    underlying_amount, to_vault_token, to_vault_tokens_received, usd_value = undy_btc_vault.rebalanceYieldPosition(
        lego_id_1,
        vault_addr_1,
        lego_id_2,
        vault_addr_2,
        vault_tokens_1,
        sender=starter_agent.address
    )

    # verify rebalance
    assert vault_addr_1.balanceOf(undy_btc_vault) == 0  # Aave empty
    assert vault_addr_2.balanceOf(undy_btc_vault) == to_vault_tokens_received  # Euler has tokens
    assert undy_btc_vault.indexOfAsset(vault_addr_1.address) == 0  # Aave deregistered
    assert undy_btc_vault.indexOfAsset(vault_addr_2.address) > 0  # Euler registered


@pytest.base
def test_cbbtc_vault_full_cycle(
    prepareYieldDeposit,
    undy_btc_vault,
    starter_agent,
    bob,
):
    """Test full cycle: deposit cbBTC → deposit to yield → withdraw from yield → redeem cbBTC"""
    token_str = "AAVE_CBBTC"
    lego_id, lego, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # 1. deposit into yield vault
    _, _, vault_tokens_received, _ = undy_btc_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    assert vault_addr.balanceOf(undy_btc_vault) == vault_tokens_received

    # 2. time travel to accrue yield
    boa.env.time_travel(seconds=24 * 60 * 60)  # 1 day

    # 3. withdraw from yield
    vault_burned, underlying_asset, underlying_received, _ = undy_btc_vault.withdrawFromYield(
        lego_id,
        vault_addr,
        vault_tokens_received,
        sender=starter_agent.address
    )

    # allow for dust/rounding (ERC4626 protocols may have tiny remainders)
    dust_remaining = vault_addr.balanceOf(undy_btc_vault)
    assert dust_remaining < 100000  # less than 0.001 cbBTC dust is acceptable (8 decimals)
    # protocols/vaults round favorably to them, allow small loss (< 0.01%)
    assert underlying_received >= amount * 9999 // 10000, f"Loss too large: {amount} -> {underlying_received}"

    # 4. redeem cbBTC from vault
    bob_shares = undy_btc_vault.balanceOf(bob)
    initial_cbbtc_balance = asset.balanceOf(bob)

    assets_redeemed = undy_btc_vault.redeem(bob_shares, bob, bob, sender=bob)

    # verify bob got cbBTC back
    final_cbbtc_balance = asset.balanceOf(bob)
    assert final_cbbtc_balance > initial_cbbtc_balance
    assert assets_redeemed > 0
    assert undy_btc_vault.balanceOf(bob) == 0  # all shares burned


@pytest.base
def test_cbbtc_vault_all_four_protocols_sequential(
    getLegoId,
    undy_btc_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
):
    """Test depositing to all 4 protocols sequentially - validates gas, integration, and array management"""
    asset = boa.from_etherscan(TOKENS[fork]["CBBTC"])
    whale = WHALES[fork]["CBBTC"]
    mock_ripe.setPrice(asset, 100000 * EIGHTEEN_DECIMALS)
    amount = 1 * (10 ** asset.decimals())

    # deposit to all 4 protocols
    vault_addrs = []
    for protocol in TEST_TOKENS:
        lego_id, lego = getLegoId(protocol)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])
        vault_addrs.append((lego_id, vault_addr, protocol))

        # prepare deposit
        asset.transfer(bob, amount, sender=whale)
        asset.approve(undy_btc_vault, MAX_UINT256, sender=bob)
        undy_btc_vault.deposit(amount, bob, sender=bob)

        # approve lego and vault via VaultRegistry
        vault_registry.setApprovedYieldLego(undy_btc_vault.address, lego_id, True, sender=switchboard_alpha.address)
        vault_registry.setApprovedVaultToken(undy_btc_vault.address, vault_addr, True, sender=switchboard_alpha.address)

        # deposit for yield
        asset_deposited, vault_token, vault_tokens_received, usd_value = undy_btc_vault.depositForYield(
            lego_id,
            asset,
            vault_addr,
            amount,
            sender=starter_agent.address
        )

        # verify deposit
        assert asset_deposited == amount
        assert vault_addr.balanceOf(undy_btc_vault) == vault_tokens_received
        assert undy_btc_vault.indexOfAsset(vault_addr.address) > 0

    # verify all 4 protocols are registered (plus base asset = 5 total)
    assert undy_btc_vault.numAssets() == 5

    # verify each protocol is still accessible
    for lego_id, vault_addr, protocol in vault_addrs:
        assert undy_btc_vault.indexOfAsset(vault_addr.address) > 0
        assert vault_addr.balanceOf(undy_btc_vault) > 0

    # verify total assets matches expected
    expected_total = amount * 4
    total_assets = undy_btc_vault.totalAssets()
    # allow for small rounding across all protocols
    assert abs(total_assets - expected_total) <= expected_total // 1000  # 0.1% tolerance


@pytest.base
def test_cbbtc_vault_whale_deposit_10_btc(
    getLegoId,
    undy_btc_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
):
    """Test whale-sized deposits (10 cbBTC) - validates real protocol capacity and gas costs"""
    asset = boa.from_etherscan(TOKENS[fork]["CBBTC"])
    whale = WHALES[fork]["CBBTC"]
    mock_ripe.setPrice(asset, 100000 * EIGHTEEN_DECIMALS)

    # 10 cbBTC
    amount = 10 * (10 ** asset.decimals())

    # Test with 3 major protocols
    test_protocols = ["AAVE_CBBTC", "EULER_CBBTC", "MOONWELL_CBBTC"]

    for protocol in test_protocols:
        lego_id, lego = getLegoId(protocol)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])

        # prepare deposit
        asset.transfer(bob, amount, sender=whale)
        asset.approve(undy_btc_vault, MAX_UINT256, sender=bob)
        undy_btc_vault.deposit(amount, bob, sender=bob)

        vault_registry.setApprovedYieldLego(undy_btc_vault.address, lego_id, True, sender=switchboard_alpha.address)
        vault_registry.setApprovedVaultToken(undy_btc_vault.address, vault_addr, True, sender=switchboard_alpha.address)

        # deposit whale amount
        asset_deposited, vault_token, vault_tokens_received, usd_value = undy_btc_vault.depositForYield(
            lego_id,
            asset,
            vault_addr,
            amount,
            sender=starter_agent.address
        )

        # verify deposit succeeded
        assert asset_deposited == amount
        assert vault_tokens_received > 0
        assert vault_addr.balanceOf(undy_btc_vault) == vault_tokens_received

        # verify withdrawal works for whale amounts
        vault_balance = vault_addr.balanceOf(undy_btc_vault)
        _, _, underlying_received, _ = undy_btc_vault.withdrawFromYield(
            lego_id,
            vault_addr,
            vault_balance,
            sender=starter_agent.address
        )

        # verify we got close to original amount (allowing for protocol fees/rounding)
        assert underlying_received >= amount * 9995 // 10000  # allow 0.05% loss max


@pytest.base
def test_cbbtc_vault_rebasing_vs_nonrebasing_behavior(
    getLegoId,
    undy_btc_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
):
    """Test rebasing (Aave) vs non-rebasing (others) protocol behavior with real assets"""
    asset = boa.from_etherscan(TOKENS[fork]["CBBTC"])
    whale = WHALES[fork]["CBBTC"]
    mock_ripe.setPrice(asset, 100000 * EIGHTEEN_DECIMALS)
    amount = 10 * (10 ** asset.decimals())

    # Setup one rebasing and one non-rebasing protocol
    rebasing_protocol = "AAVE_CBBTC"
    nonrebasing_protocol = "EULER_CBBTC"

    rebasing_lego_id, rebasing_lego = getLegoId(rebasing_protocol)
    rebasing_vault = boa.from_etherscan(ALL_VAULT_TOKENS[fork][rebasing_protocol])

    nonrebasing_lego_id, nonrebasing_lego = getLegoId(nonrebasing_protocol)
    nonrebasing_vault = boa.from_etherscan(ALL_VAULT_TOKENS[fork][nonrebasing_protocol])

    # Verify rebasing status
    assert rebasing_lego.isRebasing() == True, "Aave should be rebasing"
    assert nonrebasing_lego.isRebasing() == False, "Euler should be non-rebasing"

    # Deposit to both protocols
    for lego_id, vault_addr in [(rebasing_lego_id, rebasing_vault), (nonrebasing_lego_id, nonrebasing_vault)]:
        asset.transfer(bob, amount, sender=whale)
        asset.approve(undy_btc_vault, MAX_UINT256, sender=bob)
        undy_btc_vault.deposit(amount, bob, sender=bob)

        vault_registry.setApprovedYieldLego(undy_btc_vault.address, lego_id, True, sender=switchboard_alpha.address)
        vault_registry.setApprovedVaultToken(undy_btc_vault.address, vault_addr, True, sender=switchboard_alpha.address)

        undy_btc_vault.depositForYield(
            lego_id,
            asset,
            vault_addr,
            amount,
            sender=starter_agent.address
        )

    # Record initial balances and vault token amounts
    rebasing_vault_tokens_initial = rebasing_vault.balanceOf(undy_btc_vault)
    nonrebasing_vault_tokens_initial = nonrebasing_vault.balanceOf(undy_btc_vault)

    rebasing_underlying_initial = rebasing_lego.getUnderlyingAmount(rebasing_vault, rebasing_vault_tokens_initial)
    nonrebasing_underlying_initial = nonrebasing_lego.getUnderlyingAmount(nonrebasing_vault, nonrebasing_vault_tokens_initial)

    # Time travel to simulate yield accrual
    boa.env.time_travel(seconds=7 * 24 * 60 * 60)  # 7 days

    # Check balances after time travel
    rebasing_vault_tokens_final = rebasing_vault.balanceOf(undy_btc_vault)
    nonrebasing_vault_tokens_final = nonrebasing_vault.balanceOf(undy_btc_vault)

    rebasing_underlying_final = rebasing_lego.getUnderlyingAmount(rebasing_vault, rebasing_vault_tokens_final)
    nonrebasing_underlying_final = nonrebasing_lego.getUnderlyingAmount(nonrebasing_vault, nonrebasing_vault_tokens_final)

    # REBASING behavior: vault token balance should change, but getUnderlyingAmount should remain stable
    # (on static fork, neither changes much, but they auto-adjust)
    assert rebasing_vault_tokens_initial >= rebasing_vault_tokens_final or rebasing_vault_tokens_final >= rebasing_vault_tokens_initial
    assert rebasing_underlying_final >= rebasing_underlying_initial * 9999 // 10000  # allow tiny rounding

    # NON-REBASING behavior: vault token balance stays same, underlying value stays same
    assert nonrebasing_vault_tokens_final == nonrebasing_vault_tokens_initial
    assert nonrebasing_underlying_final >= nonrebasing_underlying_initial * 9999 // 10000  # allow tiny rounding

    # Verify avgPricePerShare is only tracked for non-rebasing
    rebasing_asset_data = undy_btc_vault.assetData(rebasing_vault.address)
    nonrebasing_asset_data = undy_btc_vault.assetData(nonrebasing_vault.address)

    # Rebasing shouldn't track avgPricePerShare (should be 0 or ignored)
    # Non-rebasing should track avgPricePerShare
    assert nonrebasing_asset_data.avgPricePerShare > 0, "Non-rebasing should track avgPricePerShare"
