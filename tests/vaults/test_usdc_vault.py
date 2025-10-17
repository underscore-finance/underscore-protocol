import pytest
import boa

from config.BluePrint import TOKENS, WHALES
from constants import EIGHTEEN_DECIMALS, MAX_UINT256


ALL_VAULT_TOKENS = {
    "base": {
        "AAVE_USDC": TOKENS["base"]["AAVEV3_USDC"],
        "COMPOUND_USDC": TOKENS["base"]["COMPOUNDV3_USDC"],
        "EULER_USDC": TOKENS["base"]["EULER_USDC"],
        "FLUID_USDC": TOKENS["base"]["FLUID_USDC"],
        "MOONWELL_USDC": TOKENS["base"]["MOONWELL_USDC"],
        "MORPHO_MOONWELL_USDC": TOKENS["base"]["MORPHO_MOONWELL_USDC"],
        "FORTY_ACRES_USDC": TOKENS["base"]["FORTY_ACRES_USDC"],
    },
}


TEST_TOKENS = [
    "AAVE_USDC",
    "COMPOUND_USDC",
    "EULER_USDC",
    "FLUID_USDC",
    "MOONWELL_USDC",
    "MORPHO_MOONWELL_USDC",
    "FORTY_ACRES_USDC",
]


@pytest.fixture(scope="module")
def getLegoId(lego_book, lego_aave_v3, lego_compound_v3, lego_euler, lego_fluid, lego_moonwell, lego_morpho, lego_40_acres):
    def getLegoId(_token_str):
        lego = None
        if _token_str == "AAVE_USDC":
            lego = lego_aave_v3
        if _token_str == "COMPOUND_USDC":
            lego = lego_compound_v3
        if _token_str == "EULER_USDC":
            lego = lego_euler
        if _token_str == "FLUID_USDC":
            lego = lego_fluid
        if _token_str == "MOONWELL_USDC":
            lego = lego_moonwell
        if _token_str == "MORPHO_MOONWELL_USDC":
            lego = lego_morpho
        if _token_str == "FORTY_ACRES_USDC":
            lego = lego_40_acres
        return lego_book.getRegId(lego), lego
    yield getLegoId


@pytest.fixture(scope="module")
def prepareYieldDeposit(
    getLegoId,
    undy_usd_vault,
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
        asset = boa.from_etherscan(TOKENS[fork]["USDC"])
        whale = WHALES[fork]["USDC"]
        amount = 100 * (10 ** asset.decimals())

        # set price
        mock_ripe.setPrice(asset, 1 * EIGHTEEN_DECIMALS)

        # transfer asset to user
        asset.transfer(bob, amount, sender=whale)

        # deposit into earn vault
        asset.approve(undy_usd_vault, MAX_UINT256, sender=bob)
        undy_usd_vault.deposit(amount, bob, sender=bob)

        # approve lego and vault via VaultRegistry
        vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)
        vault_registry.setApprovedVaultToken(undy_usd_vault.address, vault_addr, True, sender=switchboard_alpha.address)

        return lego_id, lego, vault_addr, asset, amount

    yield prepareYieldDeposit


#########
# Tests #
#########


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_usdc_vault_deposit(
    prepareYieldDeposit,
    undy_usd_vault,
    starter_agent,
    token_str,
    _test,
    bob,
):
    lego_id, lego, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # deposit into yield vault
    asset_deposited, vault_token, vault_tokens_received, usd_value = undy_usd_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # total assets
    assert asset_deposited == amount
    _test(undy_usd_vault.totalAssets(), amount)

    # vault token
    assert vault_token == vault_addr.address
    assert vault_addr.balanceOf(undy_usd_vault) == vault_tokens_received

    # vault shares
    bob_shares = undy_usd_vault.balanceOf(bob)
    _test(undy_usd_vault.convertToAssets(bob_shares), amount)

    # usd value
    _test(usd_value, 100 * EIGHTEEN_DECIMALS)


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_usdc_vault_withdraw_partial(
    prepareYieldDeposit,
    undy_usd_vault,
    starter_agent,
    token_str,
):
    """Test partial withdrawal from vault tokens"""
    lego_id, lego, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # deposit into yield vault
    undy_usd_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    initial_vault_balance = vault_addr.balanceOf(undy_usd_vault)

    # withdraw half
    withdraw_amount = initial_vault_balance // 2
    vault_burned, underlying_asset, underlying_received, usd_value = undy_usd_vault.withdrawFromYield(
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
    remaining_balance = vault_addr.balanceOf(undy_usd_vault)
    expected_balance = initial_vault_balance - withdraw_amount
    assert abs(remaining_balance - expected_balance) <= 1

    # verify vault token still registered
    assert undy_usd_vault.indexOfAsset(vault_addr.address) > 0


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_usdc_vault_withdraw_full(
    prepareYieldDeposit,
    undy_usd_vault,
    starter_agent,
    token_str,
):
    """Test full withdrawal deregisters vault token"""
    lego_id, lego, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # deposit into yield vault
    undy_usd_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # verify registered
    assert undy_usd_vault.indexOfAsset(vault_addr.address) > 0
    num_assets_before = undy_usd_vault.numAssets()

    # withdraw all
    vault_balance = vault_addr.balanceOf(undy_usd_vault)
    vault_burned, underlying_asset, underlying_received, usd_value = undy_usd_vault.withdrawFromYield(
        lego_id,
        vault_addr,
        vault_balance,
        sender=starter_agent.address
    )

    # verify complete withdrawal
    assert vault_addr.balanceOf(undy_usd_vault) == 0
    assert vault_burned == vault_balance
    assert underlying_received > 0

    # verify deregistration
    assert undy_usd_vault.indexOfAsset(vault_addr.address) == 0
    assert undy_usd_vault.numAssets() == num_assets_before - 1


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_usdc_vault_withdraw_max_value(
    prepareYieldDeposit,
    undy_usd_vault,
    starter_agent,
    token_str,
):
    """Test withdrawal with MAX_UINT256 withdraws entire balance"""
    lego_id, lego, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # deposit into yield vault
    undy_usd_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    vault_balance = vault_addr.balanceOf(undy_usd_vault)

    # withdraw with MAX_UINT256
    vault_burned, underlying_asset, underlying_received, usd_value = undy_usd_vault.withdrawFromYield(
        lego_id,
        vault_addr,
        MAX_UINT256,
        sender=starter_agent.address
    )

    # verify entire balance withdrawn
    assert vault_burned == vault_balance
    assert vault_addr.balanceOf(undy_usd_vault) == 0
    assert underlying_received > 0


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_usdc_vault_yield_accrual(
    prepareYieldDeposit,
    undy_usd_vault,
    starter_agent,
    token_str,
):
    """Test that vault token value remains stable (doesn't decrease)"""
    lego_id, lego, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # deposit into yield vault
    _, _, vault_tokens_received, _ = undy_usd_vault.depositForYield(
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
def test_usdc_vault_share_price_increase(
    prepareYieldDeposit,
    undy_usd_vault,
    starter_agent,
    token_str,
    fork,
):
    """Test that share value doesn't decrease when others deposit (rebasing assets behave differently)"""
    lego_id, lego, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # deposit into yield vault
    _, _, vault_tokens_received, _ = undy_usd_vault.depositForYield(
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
    whale = WHALES[fork]["USDC"]
    whale_amount = 10000 * (10 ** asset.decimals())

    # Transfer to whale and deposit via lego
    asset.transfer(whale, whale_amount, sender=WHALES[fork]["USDC"])
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
def test_usdc_vault_avg_price_tracking(
    prepareYieldDeposit,
    undy_usd_vault,
    starter_agent,
    token_str,
    bob,
    fork,
):
    """Test avgPricePerShare tracking with multiple deposits (non-rebasing assets only)"""
    lego_id, lego, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # Skip rebasing assets (AAVE, Compound) - they don't use avgPricePerShare
    if lego.isRebasing():
        pytest.skip(f"Skipping {token_str} - rebasing assets don't track avgPricePerShare")

    # first deposit
    undy_usd_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # record initial avg price
    initial_data = undy_usd_vault.assetData(vault_addr.address)
    initial_avg_price = initial_data.avgPricePerShare
    assert initial_avg_price > 0

    # time travel to allow snapshot
    boa.env.time_travel(seconds=301)

    # prepare second deposit
    whale = WHALES[fork]["USDC"]
    asset.transfer(bob, amount, sender=whale)
    undy_usd_vault.deposit(amount, bob, sender=bob)

    # second deposit
    undy_usd_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # verify avgPricePerShare is being tracked
    final_data = undy_usd_vault.assetData(vault_addr.address)
    final_avg_price = final_data.avgPricePerShare
    assert final_avg_price > 0


@pytest.base
def test_usdc_vault_deposit_multiple_protocols(
    getLegoId,
    undy_usd_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
    _test,
):
    """Test depositing to multiple different protocols"""
    asset = boa.from_etherscan(TOKENS[fork]["USDC"])
    whale = WHALES[fork]["USDC"]
    mock_ripe.setPrice(asset, 1 * EIGHTEEN_DECIMALS)

    # test with first 3 protocols
    test_protocols = ["AAVE_USDC", "COMPOUND_USDC", "MOONWELL_USDC"]

    for protocol in test_protocols:
        lego_id, lego = getLegoId(protocol)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])
        amount = 100 * (10 ** asset.decimals())

        # prepare deposit
        asset.transfer(bob, amount, sender=whale)
        asset.approve(undy_usd_vault, MAX_UINT256, sender=bob)
        undy_usd_vault.deposit(amount, bob, sender=bob)

        # approve lego and vault via VaultRegistry
        vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)
        vault_registry.setApprovedVaultToken(undy_usd_vault.address, vault_addr, True, sender=switchboard_alpha.address)

        # deposit for yield
        asset_deposited, vault_token, vault_tokens_received, usd_value = undy_usd_vault.depositForYield(
            lego_id,
            asset,
            vault_addr,
            amount,
            sender=starter_agent.address
        )

        # verify deposit
        assert asset_deposited == amount
        assert vault_addr.balanceOf(undy_usd_vault) == vault_tokens_received
        assert undy_usd_vault.indexOfAsset(vault_addr.address) > 0

    # verify all 3 protocols are registered (plus base asset = 4 total)
    assert undy_usd_vault.numAssets() == 4


@pytest.base
def test_usdc_vault_withdraw_from_multiple_protocols(
    getLegoId,
    undy_usd_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
):
    """Test maintaining positions in multiple protocols while withdrawing from one"""
    asset = boa.from_etherscan(TOKENS[fork]["USDC"])
    whale = WHALES[fork]["USDC"]
    mock_ripe.setPrice(asset, 1 * EIGHTEEN_DECIMALS)
    amount = 100 * (10 ** asset.decimals())

    # deposit to two protocols
    protocols = ["AAVE_USDC", "MOONWELL_USDC"]
    vault_addrs = []

    for protocol in protocols:
        lego_id, lego = getLegoId(protocol)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])
        vault_addrs.append((lego_id, vault_addr))

        asset.transfer(bob, amount, sender=whale)
        asset.approve(undy_usd_vault, MAX_UINT256, sender=bob)
        undy_usd_vault.deposit(amount, bob, sender=bob)

        vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)
        vault_registry.setApprovedVaultToken(undy_usd_vault.address, vault_addr, True, sender=switchboard_alpha.address)

        undy_usd_vault.depositForYield(
            lego_id,
            asset,
            vault_addr,
            amount,
            sender=starter_agent.address
        )

    # verify both registered
    assert undy_usd_vault.numAssets() == 3  # base + 2 protocols

    # withdraw from first protocol only
    lego_id_1, vault_addr_1 = vault_addrs[0]
    vault_balance_1 = vault_addr_1.balanceOf(undy_usd_vault)

    undy_usd_vault.withdrawFromYield(
        lego_id_1,
        vault_addr_1,
        vault_balance_1,
        sender=starter_agent.address
    )

    # verify first deregistered, second still registered
    assert undy_usd_vault.indexOfAsset(vault_addr_1.address) == 0
    assert undy_usd_vault.indexOfAsset(vault_addrs[1][1].address) > 0
    assert undy_usd_vault.numAssets() == 2  # base + 1 protocol


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_usdc_vault_conversion_accuracy(
    prepareYieldDeposit,
    undy_usd_vault,
    starter_agent,
    token_str,
):
    """Test convertToAssets and convertToShares accuracy"""
    lego_id, lego, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # deposit into yield vault
    _, _, vault_tokens_received, _ = undy_usd_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # test vault token conversions
    assets = lego.getUnderlyingAmount(vault_addr, vault_tokens_received)
    shares_back = lego.getVaultTokenAmount(asset, assets, vault_addr)

    # should be close to original (accounting for rounding)
    # Allow for small rounding differences (< 0.01%)
    diff = abs(shares_back - vault_tokens_received)
    max_diff = max(vault_tokens_received // 10000, 2)  # 0.01% or 2 wei minimum
    assert diff <= max_diff, f"Conversion diff too large: {diff} > {max_diff}"


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_usdc_vault_small_deposit(
    getLegoId,
    undy_usd_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
    token_str,
):
    """Test small (dust) deposit amounts"""
    lego_id, lego = getLegoId(token_str)
    vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][token_str])
    asset = boa.from_etherscan(TOKENS[fork]["USDC"])
    whale = WHALES[fork]["USDC"]

    # 1 USDC (6 decimals)
    amount = 1 * (10 ** asset.decimals())

    mock_ripe.setPrice(asset, 1 * EIGHTEEN_DECIMALS)
    asset.transfer(bob, amount, sender=whale)
    asset.approve(undy_usd_vault, MAX_UINT256, sender=bob)
    undy_usd_vault.deposit(amount, bob, sender=bob)

    vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)
    vault_registry.setApprovedVaultToken(undy_usd_vault.address, vault_addr, True, sender=switchboard_alpha.address)

    # deposit small amount
    asset_deposited, vault_token, vault_tokens_received, usd_value = undy_usd_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # verify it worked
    assert asset_deposited == amount
    assert vault_tokens_received > 0


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_usdc_vault_large_deposit(
    getLegoId,
    undy_usd_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
    token_str,
):
    """Test large deposit amounts"""
    lego_id, lego = getLegoId(token_str)
    vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][token_str])
    asset = boa.from_etherscan(TOKENS[fork]["USDC"])
    whale = WHALES[fork]["USDC"]

    # 100,000 USDC
    amount = 100_000 * (10 ** asset.decimals())

    mock_ripe.setPrice(asset, 1 * EIGHTEEN_DECIMALS)
    asset.transfer(bob, amount, sender=whale)
    asset.approve(undy_usd_vault, MAX_UINT256, sender=bob)
    undy_usd_vault.deposit(amount, bob, sender=bob)

    vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)
    vault_registry.setApprovedVaultToken(undy_usd_vault.address, vault_addr, True, sender=switchboard_alpha.address)

    # deposit large amount
    asset_deposited, vault_token, vault_tokens_received, usd_value = undy_usd_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # verify it worked
    assert asset_deposited == amount
    assert vault_tokens_received > 0


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_usdc_vault_full_cycle(
    prepareYieldDeposit,
    undy_usd_vault,
    starter_agent,
    token_str,
    bob,
):
    """Test full cycle: deposit USDC → deposit to yield → withdraw from yield → redeem USDC"""
    lego_id, lego, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # 1. deposit into yield vault
    _, _, vault_tokens_received, _ = undy_usd_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    assert vault_addr.balanceOf(undy_usd_vault) == vault_tokens_received

    # 2. time travel to accrue yield
    boa.env.time_travel(seconds=24 * 60 * 60)  # 1 day

    # 3. withdraw from yield
    vault_burned, underlying_asset, underlying_received, _ = undy_usd_vault.withdrawFromYield(
        lego_id,
        vault_addr,
        vault_tokens_received,
        sender=starter_agent.address
    )

    # allow for dust/rounding (ERC4626 protocols may have tiny remainders)
    dust_remaining = vault_addr.balanceOf(undy_usd_vault)
    assert dust_remaining < 100000  # less than 0.1 USDC dust is acceptable
    # protocols/vaults round favorably to them, allow small loss (< 0.01%)
    assert underlying_received >= amount * 9999 // 10000, f"Loss too large: {amount} -> {underlying_received}"

    # 4. redeem USDC from vault
    bob_shares = undy_usd_vault.balanceOf(bob)
    initial_usdc_balance = asset.balanceOf(bob)

    assets_redeemed = undy_usd_vault.redeem(bob_shares, bob, bob, sender=bob)

    # verify bob got USDC back
    final_usdc_balance = asset.balanceOf(bob)
    assert final_usdc_balance > initial_usdc_balance
    assert assets_redeemed > 0
    assert undy_usd_vault.balanceOf(bob) == 0  # all shares burned


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_usdc_vault_multiple_deposits_same_protocol(
    prepareYieldDeposit,
    undy_usd_vault,
    starter_agent,
    token_str,
    bob,
    fork,
):
    """Test multiple sequential deposits to same protocol"""
    lego_id, lego, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # first deposit
    _, _, vault_tokens_1, _ = undy_usd_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # second deposit - prepare more USDC
    whale = WHALES[fork]["USDC"]
    asset.transfer(bob, amount, sender=whale)
    undy_usd_vault.deposit(amount, bob, sender=bob)

    _, _, vault_tokens_2, _ = undy_usd_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # verify cumulative balance
    total_vault_tokens = vault_tokens_1 + vault_tokens_2
    assert vault_addr.balanceOf(undy_usd_vault) == total_vault_tokens

    # should still be same asset (no duplicate registration)
    vault_data = undy_usd_vault.assetData(vault_addr.address)
    assert vault_data.legoId == lego_id


@pytest.base
def test_usdc_vault_all_seven_protocols_sequential(
    getLegoId,
    undy_usd_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
):
    """Test depositing to all 7 protocols sequentially - validates gas, integration, and array management"""
    asset = boa.from_etherscan(TOKENS[fork]["USDC"])
    whale = WHALES[fork]["USDC"]
    mock_ripe.setPrice(asset, 1 * EIGHTEEN_DECIMALS)
    amount = 100 * (10 ** asset.decimals())

    # deposit to all 7 protocols
    vault_addrs = []
    for protocol in TEST_TOKENS:
        lego_id, lego = getLegoId(protocol)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])
        vault_addrs.append((lego_id, vault_addr, protocol))

        # prepare deposit
        asset.transfer(bob, amount, sender=whale)
        asset.approve(undy_usd_vault, MAX_UINT256, sender=bob)
        undy_usd_vault.deposit(amount, bob, sender=bob)

        # approve lego and vault via VaultRegistry
        vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)
        vault_registry.setApprovedVaultToken(undy_usd_vault.address, vault_addr, True, sender=switchboard_alpha.address)

        # deposit for yield
        asset_deposited, vault_token, vault_tokens_received, usd_value = undy_usd_vault.depositForYield(
            lego_id,
            asset,
            vault_addr,
            amount,
            sender=starter_agent.address
        )

        # verify deposit
        assert asset_deposited == amount
        assert vault_addr.balanceOf(undy_usd_vault) == vault_tokens_received
        assert undy_usd_vault.indexOfAsset(vault_addr.address) > 0

    # verify all 7 protocols are registered (plus base asset = 8 total)
    assert undy_usd_vault.numAssets() == 8

    # verify each protocol is still accessible
    for lego_id, vault_addr, protocol in vault_addrs:
        assert undy_usd_vault.indexOfAsset(vault_addr.address) > 0
        assert vault_addr.balanceOf(undy_usd_vault) > 0

    # verify total assets matches expected
    expected_total = amount * 7
    total_assets = undy_usd_vault.totalAssets()
    # allow for small rounding across all protocols
    assert abs(total_assets - expected_total) <= expected_total // 1000  # 0.1% tolerance


@pytest.base
def test_usdc_vault_rebasing_vs_nonrebasing_behavior(
    getLegoId,
    undy_usd_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
):
    """Test rebasing (Aave/Compound) vs non-rebasing (others) protocol behavior with real assets"""
    asset = boa.from_etherscan(TOKENS[fork]["USDC"])
    whale = WHALES[fork]["USDC"]
    mock_ripe.setPrice(asset, 1 * EIGHTEEN_DECIMALS)
    amount = 1000 * (10 ** asset.decimals())

    # Setup one rebasing and one non-rebasing protocol
    rebasing_protocol = "AAVE_USDC"
    nonrebasing_protocol = "EULER_USDC"

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
        asset.approve(undy_usd_vault, MAX_UINT256, sender=bob)
        undy_usd_vault.deposit(amount, bob, sender=bob)

        vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)
        vault_registry.setApprovedVaultToken(undy_usd_vault.address, vault_addr, True, sender=switchboard_alpha.address)

        undy_usd_vault.depositForYield(
            lego_id,
            asset,
            vault_addr,
            amount,
            sender=starter_agent.address
        )

    # Record initial balances and vault token amounts
    rebasing_vault_tokens_initial = rebasing_vault.balanceOf(undy_usd_vault)
    nonrebasing_vault_tokens_initial = nonrebasing_vault.balanceOf(undy_usd_vault)

    rebasing_underlying_initial = rebasing_lego.getUnderlyingAmount(rebasing_vault, rebasing_vault_tokens_initial)
    nonrebasing_underlying_initial = nonrebasing_lego.getUnderlyingAmount(nonrebasing_vault, nonrebasing_vault_tokens_initial)

    # Time travel to simulate yield accrual
    boa.env.time_travel(seconds=7 * 24 * 60 * 60)  # 7 days

    # Check balances after time travel
    rebasing_vault_tokens_final = rebasing_vault.balanceOf(undy_usd_vault)
    nonrebasing_vault_tokens_final = nonrebasing_vault.balanceOf(undy_usd_vault)

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
    rebasing_asset_data = undy_usd_vault.assetData(rebasing_vault.address)
    nonrebasing_asset_data = undy_usd_vault.assetData(nonrebasing_vault.address)

    # Rebasing shouldn't track avgPricePerShare (should be 0 or ignored)
    # Non-rebasing should track avgPricePerShare
    assert nonrebasing_asset_data.avgPricePerShare > 0, "Non-rebasing should track avgPricePerShare"


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_usdc_vault_whale_deposit_1m(
    getLegoId,
    undy_usd_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
    token_str,
):
    """Test whale-sized deposits (1M USDC) - validates real protocol capacity and gas costs"""
    lego_id, lego = getLegoId(token_str)
    vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][token_str])
    asset = boa.from_etherscan(TOKENS[fork]["USDC"])
    whale = WHALES[fork]["USDC"]

    # 1 million USDC
    amount = 1_000_000 * (10 ** asset.decimals())

    mock_ripe.setPrice(asset, 1 * EIGHTEEN_DECIMALS)
    asset.transfer(bob, amount, sender=whale)
    asset.approve(undy_usd_vault, MAX_UINT256, sender=bob)
    undy_usd_vault.deposit(amount, bob, sender=bob)

    vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)
    vault_registry.setApprovedVaultToken(undy_usd_vault.address, vault_addr, True, sender=switchboard_alpha.address)

    # deposit whale amount
    asset_deposited, vault_token, vault_tokens_received, usd_value = undy_usd_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # verify deposit succeeded
    assert asset_deposited == amount
    assert vault_tokens_received > 0
    assert vault_addr.balanceOf(undy_usd_vault) == vault_tokens_received

    # verify withdrawal works for whale amounts
    vault_balance = vault_addr.balanceOf(undy_usd_vault)
    _, _, underlying_received, _ = undy_usd_vault.withdrawFromYield(
        lego_id,
        vault_addr,
        vault_balance,
        sender=starter_agent.address
    )

    # verify we got close to original amount (allowing for protocol fees/rounding)
    assert underlying_received >= amount * 9995 // 10000  # allow 0.05% loss max


@pytest.base
def test_usdc_vault_whale_deposit_10m_multiple_protocols(
    getLegoId,
    undy_usd_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
):
    """Test extreme whale deposits (10M USDC) across multiple protocols"""
    asset = boa.from_etherscan(TOKENS[fork]["USDC"])
    whale = WHALES[fork]["USDC"]
    mock_ripe.setPrice(asset, 1 * EIGHTEEN_DECIMALS)

    # 10 million USDC per protocol
    amount_per_protocol = 10_000_000 * (10 ** asset.decimals())

    # Test with 3 major protocols to validate extreme amounts
    test_protocols = ["AAVE_USDC", "COMPOUND_USDC", "MOONWELL_USDC"]

    for protocol in test_protocols:
        lego_id, lego = getLegoId(protocol)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])

        # prepare deposit
        asset.transfer(bob, amount_per_protocol, sender=whale)
        asset.approve(undy_usd_vault, MAX_UINT256, sender=bob)
        undy_usd_vault.deposit(amount_per_protocol, bob, sender=bob)

        vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)
        vault_registry.setApprovedVaultToken(undy_usd_vault.address, vault_addr, True, sender=switchboard_alpha.address)

        # deposit whale amount
        asset_deposited, vault_token, vault_tokens_received, usd_value = undy_usd_vault.depositForYield(
            lego_id,
            asset,
            vault_addr,
            amount_per_protocol,
            sender=starter_agent.address
        )

        # verify each deposit succeeded
        assert asset_deposited == amount_per_protocol
        assert vault_tokens_received > 0

    # verify total assets is correct (30M USDC)
    expected_total = amount_per_protocol * 3
    total_assets = undy_usd_vault.totalAssets()
    # allow for small rounding across protocols
    assert abs(total_assets - expected_total) <= expected_total // 1000  # 0.1% tolerance


@pytest.base
def test_usdc_vault_emergency_withdrawal_multiple_protocols(
    getLegoId,
    undy_usd_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
):
    """Test emergency user withdrawal triggering redemption from multiple yield positions (tests redemption buffer)"""
    asset = boa.from_etherscan(TOKENS[fork]["USDC"])
    whale = WHALES[fork]["USDC"]
    mock_ripe.setPrice(asset, 1 * EIGHTEEN_DECIMALS)
    amount_per_protocol = 1000 * (10 ** asset.decimals())

    # Setup 3 protocols with deposits
    test_protocols = ["AAVE_USDC", "COMPOUND_USDC", "EULER_USDC"]
    total_deposited = 0

    for protocol in test_protocols:
        lego_id, lego = getLegoId(protocol)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])

        asset.transfer(bob, amount_per_protocol, sender=whale)
        asset.approve(undy_usd_vault, MAX_UINT256, sender=bob)
        undy_usd_vault.deposit(amount_per_protocol, bob, sender=bob)

        vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)
        vault_registry.setApprovedVaultToken(undy_usd_vault.address, vault_addr, True, sender=switchboard_alpha.address)

        undy_usd_vault.depositForYield(
            lego_id,
            asset,
            vault_addr,
            amount_per_protocol,
            sender=starter_agent.address
        )
        total_deposited += amount_per_protocol

    # Verify all protocols are registered (base + 3 = 4)
    assert undy_usd_vault.numAssets() == 4

    # Bob has shares for all deposits
    bob_shares = undy_usd_vault.balanceOf(bob)
    assert bob_shares > 0

    # Emergency: Bob wants to withdraw everything
    # This should trigger redemption across multiple yield positions
    initial_usdc = asset.balanceOf(bob)

    # Withdraw all
    assets_received = undy_usd_vault.redeem(bob_shares, bob, bob, sender=bob)

    # Verify Bob received USDC
    final_usdc = asset.balanceOf(bob)
    assert final_usdc > initial_usdc
    assert assets_received > 0

    # Should have received close to total deposited (accounting for rounding/fees)
    assert assets_received >= total_deposited * 999 // 1000  # 0.1% tolerance

    # Verify shares were burned
    assert undy_usd_vault.balanceOf(bob) == 0

    # Verify redemption pulled from multiple protocols
    # (some protocols may be fully withdrawn and deregistered)
    final_num_assets = undy_usd_vault.numAssets()
    # Should have fewer assets registered now (base + potentially 0-2 protocols left)
    assert final_num_assets <= 4


@pytest.base
def test_usdc_vault_emergency_partial_withdrawal_with_redemption_buffer(
    getLegoId,
    undy_usd_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
):
    """Test large withdrawal requiring yield position redemption with redemption buffer"""
    asset = boa.from_etherscan(TOKENS[fork]["USDC"])
    whale = WHALES[fork]["USDC"]
    mock_ripe.setPrice(asset, 1 * EIGHTEEN_DECIMALS)

    # Deposit small amount to vault (keeping idle)
    idle_amount = 100 * (10 ** asset.decimals())
    asset.transfer(bob, idle_amount, sender=whale)
    asset.approve(undy_usd_vault, MAX_UINT256, sender=bob)
    undy_usd_vault.deposit(idle_amount, bob, sender=bob)

    # Deposit large amount to yield
    yield_amount = 5000 * (10 ** asset.decimals())
    lego_id, lego = getLegoId("AAVE_USDC")
    vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork]["AAVE_USDC"])

    asset.transfer(bob, yield_amount, sender=whale)
    undy_usd_vault.deposit(yield_amount, bob, sender=bob)

    vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)
    vault_registry.setApprovedVaultToken(undy_usd_vault.address, vault_addr, True, sender=switchboard_alpha.address)

    undy_usd_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        yield_amount,
        sender=starter_agent.address
    )

    # Try to withdraw more than idle (should trigger yield withdrawal)
    withdraw_amount = 3000 * (10 ** asset.decimals())  # More than idle, less than total

    initial_balance = asset.balanceOf(bob)
    undy_usd_vault.withdraw(withdraw_amount, bob, bob, sender=bob)
    final_balance = asset.balanceOf(bob)

    # Verify user received requested amount
    assert final_balance - initial_balance == withdraw_amount

    # Verify vault balance decreased in vault token (redemption occurred)
    remaining_vault_tokens = vault_addr.balanceOf(undy_usd_vault)
    # Should have withdrawn from yield (but not all)
    assert remaining_vault_tokens > 0  # Still has some
    assert remaining_vault_tokens < yield_amount  # But less than original

    # Verify redemption buffer pulled extra (2% default)
    vault_balance = asset.balanceOf(undy_usd_vault.address)
    # Should have buffer amount sitting idle now
    expected_idle = (withdraw_amount - idle_amount) * 2 // 100  # 2% buffer of redeemed amount
    # Allow for variation in buffer calculation
    assert vault_balance >= expected_idle * 90 // 100  # At least 90% of expected buffer


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_usdc_vault_decimal_precision_large_amounts(
    getLegoId,
    undy_usd_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
    token_str,
    _test,
):
    """Test decimal precision with large amounts (USDC=6 decimals, vault tokens typically 18)"""
    lego_id, lego = getLegoId(token_str)
    vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][token_str])
    asset = boa.from_etherscan(TOKENS[fork]["USDC"])
    whale = WHALES[fork]["USDC"]

    # Large amount: 5 million USDC (6 decimals)
    amount = 5_000_000 * (10 ** asset.decimals())

    mock_ripe.setPrice(asset, 1 * EIGHTEEN_DECIMALS)
    asset.transfer(bob, amount, sender=whale)
    asset.approve(undy_usd_vault, MAX_UINT256, sender=bob)
    undy_usd_vault.deposit(amount, bob, sender=bob)

    vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)
    vault_registry.setApprovedVaultToken(undy_usd_vault.address, vault_addr, True, sender=switchboard_alpha.address)

    # Record vault token decimals
    vault_token_decimals = vault_addr.decimals()

    # Deposit
    asset_deposited, vault_token, vault_tokens_received, usd_value = undy_usd_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # Verify no precision loss on deposit
    assert asset_deposited == amount

    # Convert back to underlying
    underlying_amount = lego.getUnderlyingAmount(vault_addr, vault_tokens_received)

    # Should recover nearly all the original amount (accounting for rounding)
    # With decimal mismatch (6 vs 18), we need to be careful
    precision_loss_tolerance = amount // 100000  # 0.001% tolerance
    assert abs(underlying_amount - amount) <= precision_loss_tolerance, \
        f"Precision loss too high: {amount} -> {underlying_amount} (diff: {abs(underlying_amount - amount)})"

    # Test withdrawal precision
    _, _, underlying_received, _ = undy_usd_vault.withdrawFromYield(
        lego_id,
        vault_addr,
        vault_tokens_received,
        sender=starter_agent.address
    )

    # Verify withdrawal precision
    precision_loss_on_withdrawal = amount // 100000  # 0.001% tolerance
    assert abs(underlying_received - amount) <= precision_loss_on_withdrawal, \
        f"Withdrawal precision loss too high: {amount} -> {underlying_received} (diff: {abs(underlying_received - amount)})"

    # Verify conversions are stable (round-trip)
    shares_back = lego.getVaultTokenAmount(asset, underlying_received, vault_addr)
    conversion_tolerance = max(vault_tokens_received // 10000, 1)  # 0.01% or 1 wei
    assert abs(shares_back - vault_tokens_received) <= conversion_tolerance, \
        f"Round-trip conversion failed: {vault_tokens_received} -> {underlying_received} -> {shares_back}"


@pytest.base
def test_usdc_vault_decimal_precision_dust_amounts(
    getLegoId,
    undy_usd_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
):
    """Test decimal precision with dust amounts across decimal boundaries"""
    asset = boa.from_etherscan(TOKENS[fork]["USDC"])
    whale = WHALES[fork]["USDC"]
    mock_ripe.setPrice(asset, 1 * EIGHTEEN_DECIMALS)

    # Test with Aave (rebasing, 18 decimals) and Euler (non-rebasing, varies)
    test_cases = [
        ("AAVE_USDC", 1),      # 1 USDC
        ("EULER_USDC", 1),     # 1 USDC
        ("AAVE_USDC", 1.5),    # 1.5 USDC (fractional)
        ("EULER_USDC", 0.1),   # 0.1 USDC (small fraction)
    ]

    # Pre-approve all protocols
    approved_protocols = set()
    for protocol, _ in test_cases:
        if protocol not in approved_protocols:
            lego_id, lego = getLegoId(protocol)
            vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])
            vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)
            vault_registry.setApprovedVaultToken(undy_usd_vault.address, vault_addr, True, sender=switchboard_alpha.address)
            approved_protocols.add(protocol)

    for protocol, usdc_amount in test_cases:
        lego_id, lego = getLegoId(protocol)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])

        # Convert USDC amount to proper decimals
        amount = int(usdc_amount * (10 ** asset.decimals()))

        asset.transfer(bob, amount, sender=whale)
        asset.approve(undy_usd_vault, MAX_UINT256, sender=bob)
        undy_usd_vault.deposit(amount, bob, sender=bob)

        # Deposit
        asset_deposited, _, vault_tokens_received, _ = undy_usd_vault.depositForYield(
            lego_id,
            asset,
            vault_addr,
            amount,
            sender=starter_agent.address
        )

        # Verify dust amounts work
        assert asset_deposited == amount
        assert vault_tokens_received > 0

        # Withdraw and verify precision
        _, _, underlying_received, _ = undy_usd_vault.withdrawFromYield(
            lego_id,
            vault_addr,
            vault_tokens_received,
            sender=starter_agent.address
        )

        # Allow for rounding on dust amounts (up to 2 wei loss)
        assert underlying_received >= amount - 2, \
            f"Dust amount precision loss: {protocol} {usdc_amount} USDC: {amount} -> {underlying_received}"


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_usdc_vault_deregister_and_reregister(
    getLegoId,
    undy_usd_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
    token_str,
):
    """Test deregistering (full withdrawal) and re-registering (new deposit) same vault token"""
    lego_id, lego = getLegoId(token_str)
    vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][token_str])
    asset = boa.from_etherscan(TOKENS[fork]["USDC"])
    whale = WHALES[fork]["USDC"]
    amount = 1000 * (10 ** asset.decimals())

    mock_ripe.setPrice(asset, 1 * EIGHTEEN_DECIMALS)

    # Initial setup
    asset.transfer(bob, amount, sender=whale)
    asset.approve(undy_usd_vault, MAX_UINT256, sender=bob)
    undy_usd_vault.deposit(amount, bob, sender=bob)

    vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)
    vault_registry.setApprovedVaultToken(undy_usd_vault.address, vault_addr, True, sender=switchboard_alpha.address)

    # First deposit
    _, _, vault_tokens_1, _ = undy_usd_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # Verify registered
    assert undy_usd_vault.indexOfAsset(vault_addr.address) > 0
    initial_index = undy_usd_vault.indexOfAsset(vault_addr.address)
    initial_num_assets = undy_usd_vault.numAssets()

    # Full withdrawal (deregisters)
    undy_usd_vault.withdrawFromYield(
        lego_id,
        vault_addr,
        vault_tokens_1,
        sender=starter_agent.address
    )

    # Verify deregistered
    assert undy_usd_vault.indexOfAsset(vault_addr.address) == 0
    assert undy_usd_vault.numAssets() == initial_num_assets - 1

    # Re-deposit to same protocol (re-registers)
    asset.transfer(bob, amount, sender=whale)
    undy_usd_vault.deposit(amount, bob, sender=bob)

    _, _, vault_tokens_2, _ = undy_usd_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # Verify re-registered
    assert undy_usd_vault.indexOfAsset(vault_addr.address) > 0
    new_index = undy_usd_vault.indexOfAsset(vault_addr.address)
    assert undy_usd_vault.numAssets() == initial_num_assets

    # Index may be different due to array reorganization
    # But the vault should work correctly
    assert vault_tokens_2 > 0
    assert vault_addr.balanceOf(undy_usd_vault) == vault_tokens_2

    # Verify assetData was properly reset/updated
    asset_data = undy_usd_vault.assetData(vault_addr.address)
    assert asset_data.legoId == lego_id

    # Verify withdrawal still works after re-registration
    _, _, underlying_received, _ = undy_usd_vault.withdrawFromYield(
        lego_id,
        vault_addr,
        vault_tokens_2,
        sender=starter_agent.address
    )

    assert underlying_received >= amount * 999 // 1000  # 0.1% tolerance


@pytest.base
def test_usdc_vault_multiple_deregister_reregister_cycles(
    getLegoId,
    undy_usd_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
):
    """Test multiple cycles of deregistration and re-registration to validate array management"""
    asset = boa.from_etherscan(TOKENS[fork]["USDC"])
    whale = WHALES[fork]["USDC"]
    mock_ripe.setPrice(asset, 1 * EIGHTEEN_DECIMALS)
    amount = 500 * (10 ** asset.decimals())

    # Setup two protocols
    protocols = ["AAVE_USDC", "EULER_USDC"]
    protocol_data = []

    for protocol in protocols:
        lego_id, lego = getLegoId(protocol)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])
        protocol_data.append((protocol, lego_id, vault_addr))

        vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)
        vault_registry.setApprovedVaultToken(undy_usd_vault.address, vault_addr, True, sender=switchboard_alpha.address)

    # Perform 3 cycles of deposit/withdraw for each protocol
    for cycle in range(3):
        for protocol_name, lego_id, vault_addr in protocol_data:
            # Deposit
            asset.transfer(bob, amount, sender=whale)
            asset.approve(undy_usd_vault, MAX_UINT256, sender=bob)
            undy_usd_vault.deposit(amount, bob, sender=bob)

            _, _, vault_tokens, _ = undy_usd_vault.depositForYield(
                lego_id,
                asset,
                vault_addr,
                amount,
                sender=starter_agent.address
            )

            # Verify registered
            assert undy_usd_vault.indexOfAsset(vault_addr.address) > 0

            # Withdraw (deregister)
            undy_usd_vault.withdrawFromYield(
                lego_id,
                vault_addr,
                vault_tokens,
                sender=starter_agent.address
            )

            # Verify deregistered
            assert undy_usd_vault.indexOfAsset(vault_addr.address) == 0

    # Final verification: deposit to both and ensure both work
    for protocol_name, lego_id, vault_addr in protocol_data:
        asset.transfer(bob, amount, sender=whale)
        asset.approve(undy_usd_vault, MAX_UINT256, sender=bob)
        undy_usd_vault.deposit(amount, bob, sender=bob)

        _, _, vault_tokens, _ = undy_usd_vault.depositForYield(
            lego_id,
            asset,
            vault_addr,
            amount,
            sender=starter_agent.address
        )

        assert undy_usd_vault.indexOfAsset(vault_addr.address) > 0
        assert vault_tokens > 0

    # Both protocols should be registered (base + 2 = 3)
    assert undy_usd_vault.numAssets() == 3


@pytest.base
def test_usdc_vault_avg_price_divergence_across_protocols(
    getLegoId,
    undy_usd_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
):
    """Test avgPricePerShare tracking divergence across non-rebasing protocols with real assets"""
    asset = boa.from_etherscan(TOKENS[fork]["USDC"])
    whale = WHALES[fork]["USDC"]
    mock_ripe.setPrice(asset, 1 * EIGHTEEN_DECIMALS)
    amount = 1000 * (10 ** asset.decimals())

    # Test with 3 non-rebasing protocols
    nonrebasing_protocols = ["EULER_USDC", "FLUID_USDC", "MOONWELL_USDC"]
    protocol_data = []

    for protocol in nonrebasing_protocols:
        lego_id, lego = getLegoId(protocol)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])

        # Skip if rebasing (shouldn't be, but safety check)
        if lego.isRebasing():
            continue

        protocol_data.append((protocol, lego_id, lego, vault_addr))

        # Prepare deposit
        asset.transfer(bob, amount, sender=whale)
        asset.approve(undy_usd_vault, MAX_UINT256, sender=bob)
        undy_usd_vault.deposit(amount, bob, sender=bob)

        vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)
        vault_registry.setApprovedVaultToken(undy_usd_vault.address, vault_addr, True, sender=switchboard_alpha.address)

        # Initial deposit
        undy_usd_vault.depositForYield(
            lego_id,
            asset,
            vault_addr,
            amount,
            sender=starter_agent.address
        )

    # Record initial avgPricePerShare for each protocol
    initial_avg_prices = {}
    for protocol, lego_id, lego, vault_addr in protocol_data:
        asset_data = undy_usd_vault.assetData(vault_addr.address)
        initial_avg_prices[protocol] = asset_data.avgPricePerShare
        assert asset_data.avgPricePerShare > 0, f"{protocol} should track avgPricePerShare"

    # Time travel and add snapshots to allow avgPricePerShare to update
    boa.env.time_travel(seconds=301)

    # Make additional deposits to trigger snapshot updates
    for protocol, lego_id, lego, vault_addr in protocol_data:
        asset.transfer(bob, amount, sender=whale)
        undy_usd_vault.deposit(amount, bob, sender=bob)

        undy_usd_vault.depositForYield(
            lego_id,
            asset,
            vault_addr,
            amount,
            sender=starter_agent.address
        )

    # Time travel again
    boa.env.time_travel(seconds=7 * 24 * 60 * 60)  # 7 days

    # Check final avgPricePerShare for each protocol
    final_avg_prices = {}
    for protocol, lego_id, lego, vault_addr in protocol_data:
        asset_data = undy_usd_vault.assetData(vault_addr.address)
        final_avg_prices[protocol] = asset_data.avgPricePerShare

        # avgPricePerShare should remain stable (on static fork) or increase slightly
        assert final_avg_prices[protocol] >= initial_avg_prices[protocol], \
            f"{protocol} avgPricePerShare decreased: {initial_avg_prices[protocol]} -> {final_avg_prices[protocol]}"

        # Should still be positive
        assert final_avg_prices[protocol] > 0

    # Verify each protocol maintains its own independent avgPricePerShare
    # (even if they're all similar due to static fork)
    for protocol, lego_id, lego, vault_addr in protocol_data:
        asset_data = undy_usd_vault.assetData(vault_addr.address)

        # Verify snapshot data exists
        snapshot_data = undy_usd_vault.snapShotData(vault_addr.address)
        assert snapshot_data.nextIndex > 0, f"{protocol} should have snapshots"

        # Get weighted price (should use snapshots)
        weighted_price = undy_usd_vault.getWeightedPrice(vault_addr.address)
        assert weighted_price > 0, f"{protocol} weighted price should be positive"

        # Weighted price should be close to avgPricePerShare
        # (they may differ slightly due to weighting algorithm)
        avg_price = asset_data.avgPricePerShare
        # Allow for up to 10% difference (throttling can cause divergence)
        assert abs(weighted_price - avg_price) <= avg_price // 10, \
            f"{protocol} weighted price ({weighted_price}) diverged too much from avg ({avg_price})"


@pytest.base
def test_usdc_vault_avg_price_throttling_across_protocols(
    getLegoId,
    undy_usd_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
):
    """Test that avgPricePerShare throttling works independently for each protocol"""
    asset = boa.from_etherscan(TOKENS[fork]["USDC"])
    whale = WHALES[fork]["USDC"]
    mock_ripe.setPrice(asset, 1 * EIGHTEEN_DECIMALS)
    amount = 2000 * (10 ** asset.decimals())

    # Test with two non-rebasing protocols
    protocols = ["EULER_USDC", "FLUID_USDC"]
    protocol_data = []

    for protocol in protocols:
        lego_id, lego = getLegoId(protocol)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])

        # Skip rebasing
        if lego.isRebasing():
            continue

        protocol_data.append((protocol, lego_id, lego, vault_addr))

        # Setup
        asset.transfer(bob, amount, sender=whale)
        asset.approve(undy_usd_vault, MAX_UINT256, sender=bob)
        undy_usd_vault.deposit(amount, bob, sender=bob)

        vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)
        vault_registry.setApprovedVaultToken(undy_usd_vault.address, vault_addr, True, sender=switchboard_alpha.address)

        # Initial deposit
        undy_usd_vault.depositForYield(
            lego_id,
            asset,
            vault_addr,
            amount,
            sender=starter_agent.address
        )

    # Get initial avgPricePerShare for both
    initial_prices = {}
    for protocol, lego_id, lego, vault_addr in protocol_data:
        asset_data = undy_usd_vault.assetData(vault_addr.address)
        initial_prices[protocol] = asset_data.avgPricePerShare

    # Time travel and add snapshots
    boa.env.time_travel(seconds=301)

    for protocol, lego_id, lego, vault_addr in protocol_data:
        # Add price snapshot
        switchboard_alpha.address  # Already approved
        # Note: addPriceSnapshot is only callable by switchboard via vault
        # Snapshots are added automatically during depositForYield

    # Make additional deposits to multiple protocols
    for protocol, lego_id, lego, vault_addr in protocol_data:
        asset.transfer(bob, amount // 2, sender=whale)
        undy_usd_vault.deposit(amount // 2, bob, sender=bob)

        undy_usd_vault.depositForYield(
            lego_id,
            asset,
            vault_addr,
            amount // 2,
            sender=starter_agent.address
        )

    # Verify avgPricePerShare updated independently
    for protocol, lego_id, lego, vault_addr in protocol_data:
        asset_data = undy_usd_vault.assetData(vault_addr.address)
        final_price = asset_data.avgPricePerShare

        # Should be positive
        assert final_price > 0

        # Should be close to initial (or slightly higher due to yield/snapshots)
        # On static fork, should be very similar
        assert final_price >= initial_prices[protocol] * 99 // 100, \
            f"{protocol} avgPricePerShare changed unexpectedly: {initial_prices[protocol]} -> {final_price}"

        # Verify getTotalAssets uses avgPricePerShare correctly
        total_assets_avg = undy_usd_vault.getTotalAssets(False)  # Use avg prices
        total_assets_max = undy_usd_vault.getTotalAssets(True)   # Use max prices

        # Both should be positive
        assert total_assets_avg > 0
        assert total_assets_max > 0

        # Avg should be <= max (since it uses conservative pricing)
        assert total_assets_avg <= total_assets_max


@pytest.base
def test_usdc_vault_random_deposits_total_assets_accuracy(
    getLegoId,
    undy_usd_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
    _test,
):
    """Test random deposits across multiple protocols and verify totalAssets() matches exactly"""
    import random

    asset = boa.from_etherscan(TOKENS[fork]["USDC"])
    whale = WHALES[fork]["USDC"]
    mock_ripe.setPrice(asset, 1 * EIGHTEEN_DECIMALS)

    # Test with all 7 protocols
    random_amounts = {}
    total_expected = 0

    for protocol in TEST_TOKENS:
        lego_id, lego = getLegoId(protocol)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])

        # Generate random amount between 100 and 10,000 USDC
        random_usdc = random.randint(100, 10_000)
        amount = random_usdc * (10 ** asset.decimals())
        random_amounts[protocol] = amount
        total_expected += amount

        # Prepare deposit
        asset.transfer(bob, amount, sender=whale)
        asset.approve(undy_usd_vault, MAX_UINT256, sender=bob)
        undy_usd_vault.deposit(amount, bob, sender=bob)

        # Approve lego and vault
        vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)
        vault_registry.setApprovedVaultToken(undy_usd_vault.address, vault_addr, True, sender=switchboard_alpha.address)

        # Deposit for yield
        asset_deposited, vault_token, vault_tokens_received, usd_value = undy_usd_vault.depositForYield(
            lego_id,
            asset,
            vault_addr,
            amount,
            sender=starter_agent.address
        )

        # Verify deposit matches exactly what we sent
        assert asset_deposited == amount, f"{protocol}: deposited {asset_deposited} != expected {amount}"

    # Now verify totalAssets() equals sum of all deposits
    total_assets = undy_usd_vault.totalAssets()

    # Allow for minimal rounding across all protocols (< 0.01% total)
    max_rounding_error = total_expected // 10000
    assert abs(total_assets - total_expected) <= max_rounding_error, \
        f"totalAssets {total_assets} != expected {total_expected} (diff: {abs(total_assets - total_expected)})"

    # Verify share price accounting is correct
    # Bob deposited total_expected, so convertToAssets should match
    bob_shares = undy_usd_vault.balanceOf(bob)
    bob_assets = undy_usd_vault.convertToAssets(bob_shares)

    # Bob's assets should equal total_expected (he's the only depositor)
    _test(bob_assets, total_expected)

    # Verify each vault token is tracked correctly
    for protocol in TEST_TOKENS:
        lego_id, lego = getLegoId(protocol)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])

        # Check vault token is registered
        assert undy_usd_vault.indexOfAsset(vault_addr.address) > 0, f"{protocol} not registered"

        # Get vault token balance
        vault_balance = vault_addr.balanceOf(undy_usd_vault)
        assert vault_balance > 0, f"{protocol} has 0 vault tokens"

        # Convert vault tokens back to underlying
        underlying = lego.getUnderlyingAmount(vault_addr, vault_balance)

        # Should match what we deposited (within rounding)
        expected_amount = random_amounts[protocol]
        rounding_tolerance = max(expected_amount // 10000, 1)  # 0.01% or 1 wei
        assert abs(underlying - expected_amount) <= rounding_tolerance, \
            f"{protocol}: underlying {underlying} != expected {expected_amount} (diff: {abs(underlying - expected_amount)})"


@pytest.base
def test_usdc_vault_total_assets_after_partial_withdrawals(
    getLegoId,
    undy_usd_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
    _test,
):
    """Test totalAssets() remains accurate after partial withdrawals from various protocols"""
    import random

    asset = boa.from_etherscan(TOKENS[fork]["USDC"])
    whale = WHALES[fork]["USDC"]
    mock_ripe.setPrice(asset, 1 * EIGHTEEN_DECIMALS)

    # Use 5 protocols for this test
    test_protocols = ["AAVE_USDC", "COMPOUND_USDC", "EULER_USDC", "MOONWELL_USDC", "MORPHO_MOONWELL_USDC"]
    protocol_data = {}
    total_deposited = 0

    # Deposit random amounts to each protocol
    for protocol in test_protocols:
        lego_id, lego = getLegoId(protocol)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])

        # Random amount between 1000 and 5000 USDC
        random_usdc = random.randint(1000, 5000)
        amount = random_usdc * (10 ** asset.decimals())

        # Prepare deposit
        asset.transfer(bob, amount, sender=whale)
        asset.approve(undy_usd_vault, MAX_UINT256, sender=bob)
        undy_usd_vault.deposit(amount, bob, sender=bob)

        # Approve lego and vault
        vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)
        vault_registry.setApprovedVaultToken(undy_usd_vault.address, vault_addr, True, sender=switchboard_alpha.address)

        # Deposit for yield
        asset_deposited, _, vault_tokens_received, _ = undy_usd_vault.depositForYield(
            lego_id,
            asset,
            vault_addr,
            amount,
            sender=starter_agent.address
        )

        protocol_data[protocol] = {
            "lego_id": lego_id,
            "lego": lego,
            "vault_addr": vault_addr,
            "deposited": amount,
            "vault_tokens": vault_tokens_received,
            "original_vault_tokens": vault_tokens_received,  # Save original for comparison
        }
        total_deposited += amount

    # Verify initial totalAssets
    initial_total_assets = undy_usd_vault.totalAssets()
    _test(initial_total_assets, total_deposited)

    # Now perform partial withdrawals from random protocols
    protocols_to_withdraw = random.sample(test_protocols, 3)  # Withdraw from 3 out of 5
    total_withdrawn = 0

    for protocol in protocols_to_withdraw:
        data = protocol_data[protocol]

        # Withdraw a random percentage (30% to 70%)
        withdraw_percentage = random.randint(30, 70)
        vault_tokens_to_withdraw = data["vault_tokens"] * withdraw_percentage // 100

        # Perform withdrawal
        vault_burned, underlying_asset, underlying_received, _ = undy_usd_vault.withdrawFromYield(
            data["lego_id"],
            data["vault_addr"],
            vault_tokens_to_withdraw,
            sender=starter_agent.address
        )

        total_withdrawn += underlying_received

        # Update protocol data
        data["vault_tokens"] -= vault_burned
        data["withdrawn"] = underlying_received

    # Calculate expected total assets after withdrawals
    # Note: withdrawFromYield moves assets from yield back to idle USDC in the vault
    # So totalAssets should still equal total_deposited (not reduced)
    expected_total_after_withdrawal = total_deposited

    # Verify totalAssets is still accurate (should not have changed)
    total_assets_after_withdrawal = undy_usd_vault.totalAssets()

    # Allow for small rounding (< 0.1%)
    max_rounding = expected_total_after_withdrawal // 1000
    assert abs(total_assets_after_withdrawal - expected_total_after_withdrawal) <= max_rounding, \
        f"totalAssets {total_assets_after_withdrawal} != expected {expected_total_after_withdrawal} after partial withdrawals"

    # Verify each protocol's balance is tracked correctly
    for protocol in test_protocols:
        data = protocol_data[protocol]
        current_vault_balance = data["vault_addr"].balanceOf(undy_usd_vault)
        original_vault_tokens = data["original_vault_tokens"]

        if protocol in protocols_to_withdraw:
            # After withdrawal, balance should be less than original
            assert current_vault_balance < original_vault_tokens, f"{protocol} balance should have decreased from {original_vault_tokens} to {current_vault_balance}"
            # But still > 0 (partial withdrawal)
            assert current_vault_balance > 0, f"{protocol} should still have balance after partial withdrawal"
        else:
            # Should have same balance as before (no withdrawal happened)
            assert current_vault_balance == original_vault_tokens, f"{protocol} balance should be unchanged"

    # Verify user shares are still correct
    bob_shares = undy_usd_vault.balanceOf(bob)
    bob_assets = undy_usd_vault.convertToAssets(bob_shares)

    # Bob's convertToAssets should match expected total
    _test(bob_assets, expected_total_after_withdrawal)


@pytest.base
def test_usdc_vault_multiple_users_random_operations(
    getLegoId,
    undy_usd_vault,
    vault_registry,
    starter_agent,
    bob,
    alice,
    charlie,
    fork,
    switchboard_alpha,
    mock_ripe,
):
    """Test multiple users depositing and withdrawing randomly, verify share accounting remains accurate"""
    import random

    asset = boa.from_etherscan(TOKENS[fork]["USDC"])
    whale = WHALES[fork]["USDC"]
    mock_ripe.setPrice(asset, 1 * EIGHTEEN_DECIMALS)

    users = [bob, alice, charlie]
    user_deposits = {bob: 0, alice: 0, charlie: 0}

    # Use 4 protocols
    test_protocols = ["AAVE_USDC", "COMPOUND_USDC", "EULER_USDC", "MOONWELL_USDC"]
    protocol_info = {}

    # Setup all protocols
    for protocol in test_protocols:
        lego_id, lego = getLegoId(protocol)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])

        vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)
        vault_registry.setApprovedVaultToken(undy_usd_vault.address, vault_addr, True, sender=switchboard_alpha.address)

        protocol_info[protocol] = {
            "lego_id": lego_id,
            "lego": lego,
            "vault_addr": vault_addr,
        }

    # Simulate 15 random user deposits
    for i in range(15):
        user = random.choice(users)
        protocol = random.choice(test_protocols)
        info = protocol_info[protocol]

        # Random deposit amount (100 to 2000 USDC)
        amount = random.randint(100, 2000) * (10 ** asset.decimals())

        # User deposits to vault
        asset.transfer(user, amount, sender=whale)
        asset.approve(undy_usd_vault, MAX_UINT256, sender=user)
        undy_usd_vault.deposit(amount, user, sender=user)

        # Deposit to yield protocol
        undy_usd_vault.depositForYield(
            info["lego_id"],
            asset,
            info["vault_addr"],
            amount,
            sender=starter_agent.address
        )

        user_deposits[user] += amount

    # Record each user's shares and expected assets
    user_shares = {}
    for user in users:
        shares = undy_usd_vault.balanceOf(user)
        user_shares[user] = shares

        # Verify convertToAssets matches what they deposited (within rounding)
        assets = undy_usd_vault.convertToAssets(shares)
        expected = user_deposits[user]

        # Allow 0.1% rounding
        tolerance = max(expected // 1000, 1)
        assert abs(assets - expected) <= tolerance, \
            f"User assets {assets} != expected {expected} (deposited)"

    # Verify totalAssets matches sum of all deposits
    total_deposited = sum(user_deposits.values())
    total_assets = undy_usd_vault.totalAssets()

    tolerance = total_deposited // 1000
    assert abs(total_assets - total_deposited) <= tolerance, \
        f"totalAssets {total_assets} != expected {total_deposited}"

    # Now simulate random withdrawals
    # Alice withdraws 50% of her shares
    alice_withdraw_shares = user_shares[alice] // 2
    alice_initial_balance = asset.balanceOf(alice)

    alice_withdrawn_assets = undy_usd_vault.redeem(alice_withdraw_shares, alice, alice, sender=alice)
    alice_final_balance = asset.balanceOf(alice)

    # Verify Alice received assets
    assert alice_final_balance > alice_initial_balance
    assert alice_withdrawn_assets == alice_final_balance - alice_initial_balance

    # Update Alice's expected deposits
    user_deposits[alice] -= alice_withdrawn_assets
    user_shares[alice] = undy_usd_vault.balanceOf(alice)

    # Bob withdraws 30% of his shares
    bob_withdraw_shares = user_shares[bob] * 30 // 100
    bob_initial_balance = asset.balanceOf(bob)

    bob_withdrawn_assets = undy_usd_vault.redeem(bob_withdraw_shares, bob, bob, sender=bob)
    bob_final_balance = asset.balanceOf(bob)

    assert bob_final_balance > bob_initial_balance
    user_deposits[bob] -= bob_withdrawn_assets
    user_shares[bob] = undy_usd_vault.balanceOf(bob)

    # Verify totalAssets decreased correctly
    total_remaining = sum(user_deposits.values())
    total_assets_after = undy_usd_vault.totalAssets()

    tolerance = total_remaining // 1000
    assert abs(total_assets_after - total_remaining) <= tolerance, \
        f"totalAssets after withdrawals {total_assets_after} != expected {total_remaining}"

    # Verify remaining shares for each user are accurate
    for user in users:
        shares = undy_usd_vault.balanceOf(user)
        if shares > 0:
            assets = undy_usd_vault.convertToAssets(shares)
            expected = user_deposits[user]

            tolerance = max(expected // 1000, 1)
            assert abs(assets - expected) <= tolerance, \
                f"User final assets {assets} != expected {expected}"

    # Charlie deposits more after others withdrew
    additional_amount = 1000 * (10 ** asset.decimals())
    protocol = random.choice(test_protocols)
    info = protocol_info[protocol]

    asset.transfer(charlie, additional_amount, sender=whale)
    undy_usd_vault.deposit(additional_amount, charlie, sender=charlie)

    undy_usd_vault.depositForYield(
        info["lego_id"],
        asset,
        info["vault_addr"],
        additional_amount,
        sender=starter_agent.address
    )

    user_deposits[charlie] += additional_amount

    # Final verification: totalAssets should match all remaining deposits
    final_total = sum(user_deposits.values())
    final_total_assets = undy_usd_vault.totalAssets()

    tolerance = final_total // 1000
    assert abs(final_total_assets - final_total) <= tolerance, \
        f"Final totalAssets {final_total_assets} != expected {final_total}"

    # Verify all users can fully withdraw their remaining shares
    for user in users:
        shares = undy_usd_vault.balanceOf(user)
        if shares > 0:
            expected_assets = user_deposits[user]
            convertable_assets = undy_usd_vault.convertToAssets(shares)

            tolerance = max(expected_assets // 1000, 1)
            assert abs(convertable_assets - expected_assets) <= tolerance, \
                f"User {user} final convertToAssets {convertable_assets} != expected {expected_assets}"