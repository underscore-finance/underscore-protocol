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
        return lego_book.getRegId(lego)
    yield getLegoId


@pytest.fixture(scope="module")
def prepareYieldDeposit(
    getLegoId,
    undy_usd_vault,
    mock_ripe,
    bob,
    fork,
    switchboard_alpha,
    _test,
):
    def prepareYieldDeposit(_token_str):
        lego_id = getLegoId(_token_str)
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

        # approve lego and vault
        undy_usd_vault.setApprovedYieldLego(lego_id, True, sender=switchboard_alpha.address)
        undy_usd_vault.setApprovedVaultToken(vault_addr, True, sender=switchboard_alpha.address)

        return lego_id, vault_addr, asset, amount

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
    lego_id, vault_addr, asset, amount = prepareYieldDeposit(token_str)

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
    lego_id, vault_addr, asset, amount = prepareYieldDeposit(token_str)

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
    lego_id, vault_addr, asset, amount = prepareYieldDeposit(token_str)

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
    lego_id, vault_addr, asset, amount = prepareYieldDeposit(token_str)

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
    """Test that yield accrues over time in real protocols"""
    lego_id, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # deposit into yield vault
    _, _, vault_tokens_received, _ = undy_usd_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # record initial value
    initial_value = vault_addr.convertToAssets(vault_tokens_received)

    # time travel forward (7 days)
    boa.env.time_travel(seconds=7 * 24 * 60 * 60)

    # check value after time - should be >= initial (yield accrued or at least stable)
    final_value = vault_addr.convertToAssets(vault_tokens_received)
    assert final_value >= initial_value, f"Value decreased for {token_str}: {initial_value} -> {final_value}"


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
    """Test avgPricePerShare tracking with multiple deposits"""
    lego_id, vault_addr, asset, amount = prepareYieldDeposit(token_str)

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
        lego_id = getLegoId(protocol)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])
        amount = 100 * (10 ** asset.decimals())

        # prepare deposit
        asset.transfer(bob, amount, sender=whale)
        asset.approve(undy_usd_vault, MAX_UINT256, sender=bob)
        undy_usd_vault.deposit(amount, bob, sender=bob)

        # approve lego and vault
        undy_usd_vault.setApprovedYieldLego(lego_id, True, sender=switchboard_alpha.address)
        undy_usd_vault.setApprovedVaultToken(vault_addr, True, sender=switchboard_alpha.address)

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
def test_usdc_vault_rebalance_between_protocols(
    getLegoId,
    undy_usd_vault,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
):
    """Test rebalancing from one protocol to another"""
    asset = boa.from_etherscan(TOKENS[fork]["USDC"])
    whale = WHALES[fork]["USDC"]
    mock_ripe.setPrice(asset, 1 * EIGHTEEN_DECIMALS)
    amount = 100 * (10 ** asset.decimals())

    # setup first protocol (Aave)
    lego_id_1 = getLegoId("AAVE_USDC")
    vault_addr_1 = boa.from_etherscan(ALL_VAULT_TOKENS[fork]["AAVE_USDC"])

    asset.transfer(bob, amount, sender=whale)
    asset.approve(undy_usd_vault, MAX_UINT256, sender=bob)
    undy_usd_vault.deposit(amount, bob, sender=bob)

    undy_usd_vault.setApprovedYieldLego(lego_id_1, True, sender=switchboard_alpha.address)
    undy_usd_vault.setApprovedVaultToken(vault_addr_1, True, sender=switchboard_alpha.address)

    # deposit to Aave
    _, _, vault_tokens_1, _ = undy_usd_vault.depositForYield(
        lego_id_1,
        asset,
        vault_addr_1,
        amount,
        sender=starter_agent.address
    )

    # setup second protocol (Compound)
    lego_id_2 = getLegoId("COMPOUND_USDC")
    vault_addr_2 = boa.from_etherscan(ALL_VAULT_TOKENS[fork]["COMPOUND_USDC"])

    undy_usd_vault.setApprovedYieldLego(lego_id_2, True, sender=switchboard_alpha.address)
    undy_usd_vault.setApprovedVaultToken(vault_addr_2, True, sender=switchboard_alpha.address)

    # rebalance from Aave to Compound
    underlying_amount, to_vault_token, to_vault_tokens_received, usd_value = undy_usd_vault.rebalanceYieldPosition(
        lego_id_1,
        vault_addr_1,
        lego_id_2,
        vault_addr_2,
        vault_tokens_1,
        sender=starter_agent.address
    )

    # verify rebalance
    assert vault_addr_1.balanceOf(undy_usd_vault) == 0  # Aave empty
    assert vault_addr_2.balanceOf(undy_usd_vault) == to_vault_tokens_received  # Compound has tokens
    assert undy_usd_vault.indexOfAsset(vault_addr_1.address) == 0  # Aave deregistered
    assert undy_usd_vault.indexOfAsset(vault_addr_2.address) > 0  # Compound registered


@pytest.base
def test_usdc_vault_withdraw_from_multiple_protocols(
    getLegoId,
    undy_usd_vault,
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
        lego_id = getLegoId(protocol)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])
        vault_addrs.append((lego_id, vault_addr))

        asset.transfer(bob, amount, sender=whale)
        asset.approve(undy_usd_vault, MAX_UINT256, sender=bob)
        undy_usd_vault.deposit(amount, bob, sender=bob)

        undy_usd_vault.setApprovedYieldLego(lego_id, True, sender=switchboard_alpha.address)
        undy_usd_vault.setApprovedVaultToken(vault_addr, True, sender=switchboard_alpha.address)

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
    lego_id, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # deposit into yield vault
    _, _, vault_tokens_received, _ = undy_usd_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # test vault token conversions
    assets = vault_addr.convertToAssets(vault_tokens_received)
    shares_back = vault_addr.convertToShares(assets)

    # should be close to original (accounting for rounding)
    assert abs(shares_back - vault_tokens_received) <= 1


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_usdc_vault_small_deposit(
    getLegoId,
    undy_usd_vault,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
    token_str,
):
    """Test small (dust) deposit amounts"""
    lego_id = getLegoId(token_str)
    vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][token_str])
    asset = boa.from_etherscan(TOKENS[fork]["USDC"])
    whale = WHALES[fork]["USDC"]

    # 1 USDC (6 decimals)
    amount = 1 * (10 ** asset.decimals())

    mock_ripe.setPrice(asset, 1 * EIGHTEEN_DECIMALS)
    asset.transfer(bob, amount, sender=whale)
    asset.approve(undy_usd_vault, MAX_UINT256, sender=bob)
    undy_usd_vault.deposit(amount, bob, sender=bob)

    undy_usd_vault.setApprovedYieldLego(lego_id, True, sender=switchboard_alpha.address)
    undy_usd_vault.setApprovedVaultToken(vault_addr, True, sender=switchboard_alpha.address)

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
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
    token_str,
):
    """Test large deposit amounts"""
    lego_id = getLegoId(token_str)
    vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][token_str])
    asset = boa.from_etherscan(TOKENS[fork]["USDC"])
    whale = WHALES[fork]["USDC"]

    # 100,000 USDC
    amount = 100_000 * (10 ** asset.decimals())

    mock_ripe.setPrice(asset, 1 * EIGHTEEN_DECIMALS)
    asset.transfer(bob, amount, sender=whale)
    asset.approve(undy_usd_vault, MAX_UINT256, sender=bob)
    undy_usd_vault.deposit(amount, bob, sender=bob)

    undy_usd_vault.setApprovedYieldLego(lego_id, True, sender=switchboard_alpha.address)
    undy_usd_vault.setApprovedVaultToken(vault_addr, True, sender=switchboard_alpha.address)

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
    lego_id, vault_addr, asset, amount = prepareYieldDeposit(token_str)

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
    assert underlying_received >= amount  # should be at least original amount

    # 4. redeem USDC from vault
    bob_shares = undy_usd_vault.balanceOf(bob)
    initial_usdc_balance = asset.balanceOf(bob)

    assets_redeemed = undy_usd_vault.redeem(bob_shares, bob, bob, sender=bob)

    # verify bob got USDC back
    final_usdc_balance = asset.balanceOf(bob)
    assert final_usdc_balance > initial_usdc_balance
    assert assets_redeemed > 0


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
    lego_id, vault_addr, asset, amount = prepareYieldDeposit(token_str)

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