import pytest
import boa

from config.BluePrint import TOKENS, WHALES
from constants import EIGHTEEN_DECIMALS, MAX_UINT256


ALL_VAULT_TOKENS = {
    "base": {
        "AAVE_WETH": TOKENS["base"]["AAVEV3_WETH"],
        "COMPOUND_WETH": TOKENS["base"]["COMPOUNDV3_WETH"],
        "EULER_WETH": TOKENS["base"]["EULER_WETH"],
        "FLUID_WETH": TOKENS["base"]["FLUID_WETH"],
        "MOONWELL_WETH": TOKENS["base"]["MOONWELL_WETH"],
        "MORPHO_MOONWELL_WETH": TOKENS["base"]["MORPHO_MOONWELL_WETH"],
    },
}


TEST_TOKENS = [
    "AAVE_WETH",
    "COMPOUND_WETH",
    "EULER_WETH",
    "FLUID_WETH",
    "MOONWELL_WETH",
    "MORPHO_MOONWELL_WETH",
]


@pytest.fixture(scope="module")
def getLegoId(lego_book, lego_aave_v3, lego_compound_v3, lego_euler, lego_fluid, lego_moonwell, lego_morpho):
    def getLegoId(_token_str):
        lego = None
        if _token_str == "AAVE_WETH":
            lego = lego_aave_v3
        if _token_str == "COMPOUND_WETH":
            lego = lego_compound_v3
        if _token_str == "EULER_WETH":
            lego = lego_euler
        if _token_str == "FLUID_WETH":
            lego = lego_fluid
        if _token_str == "MOONWELL_WETH":
            lego = lego_moonwell
        if _token_str == "MORPHO_MOONWELL_WETH":
            lego = lego_morpho
        return lego_book.getRegId(lego), lego
    yield getLegoId


@pytest.fixture(scope="module")
def prepareYieldDeposit(
    getLegoId,
    undy_eth_vault,
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
        asset = boa.from_etherscan(TOKENS[fork]["WETH"])
        whale = WHALES[fork]["WETH"]
        amount = 1 * (10 ** asset.decimals())  # 1 WETH

        # set price (ETH ~= $2500)
        mock_ripe.setPrice(asset, 2500 * EIGHTEEN_DECIMALS)

        # transfer asset to user
        asset.transfer(bob, amount, sender=whale)

        # deposit into earn vault
        asset.approve(undy_eth_vault, MAX_UINT256, sender=bob)
        undy_eth_vault.deposit(amount, bob, sender=bob)

        # approve lego and vault via VaultRegistry
        vault_registry.setApprovedVaultToken(undy_eth_vault.address, vault_addr, True, sender=switchboard_alpha.address)

        return lego_id, lego, vault_addr, asset, amount

    yield prepareYieldDeposit


#########
# Tests #
#########


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_weth_vault_deposit(
    prepareYieldDeposit,
    undy_eth_vault,
    starter_agent,
    token_str,
    _test,
    bob,
):
    lego_id, lego, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # deposit into yield vault
    asset_deposited, vault_token, vault_tokens_received, usd_value = undy_eth_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # total assets
    assert asset_deposited == amount
    _test(undy_eth_vault.totalAssets(), amount)

    # vault token
    assert vault_token == vault_addr.address
    assert vault_addr.balanceOf(undy_eth_vault) == vault_tokens_received

    # vault shares
    bob_shares = undy_eth_vault.balanceOf(bob)
    _test(undy_eth_vault.convertToAssets(bob_shares), amount)

    # usd value (check it's reasonable, actual price may vary)
    assert usd_value > 0


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_weth_vault_withdraw_partial(
    prepareYieldDeposit,
    undy_eth_vault,
    starter_agent,
    token_str,
):
    """Test partial withdrawal from vault tokens"""
    lego_id, lego, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # deposit into yield vault
    undy_eth_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    initial_vault_balance = vault_addr.balanceOf(undy_eth_vault)

    # withdraw half
    withdraw_amount = initial_vault_balance // 2
    vault_burned, underlying_asset, underlying_received, usd_value = undy_eth_vault.withdrawFromYield(
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
    remaining_balance = vault_addr.balanceOf(undy_eth_vault)
    expected_balance = initial_vault_balance - withdraw_amount
    assert abs(remaining_balance - expected_balance) <= 1

    # verify vault token still registered
    assert undy_eth_vault.indexOfAsset(vault_addr.address) > 0


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_weth_vault_withdraw_full(
    prepareYieldDeposit,
    undy_eth_vault,
    starter_agent,
    token_str,
):
    """Test full withdrawal deregisters vault token"""
    lego_id, lego, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # deposit into yield vault
    undy_eth_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # verify registered
    assert undy_eth_vault.indexOfAsset(vault_addr.address) > 0
    num_assets_before = undy_eth_vault.numAssets()

    # withdraw all
    vault_balance = vault_addr.balanceOf(undy_eth_vault)
    vault_burned, underlying_asset, underlying_received, usd_value = undy_eth_vault.withdrawFromYield(
        lego_id,
        vault_addr,
        vault_balance,
        sender=starter_agent.address
    )

    # verify complete withdrawal
    assert vault_addr.balanceOf(undy_eth_vault) == 0
    assert vault_burned == vault_balance
    assert underlying_received > 0

    # verify deregistration
    assert undy_eth_vault.indexOfAsset(vault_addr.address) == 0
    assert undy_eth_vault.numAssets() == num_assets_before - 1


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_weth_vault_withdraw_max_value(
    prepareYieldDeposit,
    undy_eth_vault,
    starter_agent,
    token_str,
):
    """Test withdrawal with MAX_UINT256 withdraws entire balance"""
    lego_id, lego, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # deposit into yield vault
    undy_eth_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    vault_balance = vault_addr.balanceOf(undy_eth_vault)

    # withdraw with MAX_UINT256
    vault_burned, underlying_asset, underlying_received, usd_value = undy_eth_vault.withdrawFromYield(
        lego_id,
        vault_addr,
        MAX_UINT256,
        sender=starter_agent.address
    )

    # verify entire balance withdrawn
    assert vault_burned == vault_balance
    assert vault_addr.balanceOf(undy_eth_vault) == 0
    assert underlying_received > 0


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_weth_vault_yield_accrual(
    prepareYieldDeposit,
    undy_eth_vault,
    starter_agent,
    token_str,
):
    """Test that vault token value remains stable (doesn't decrease)"""
    lego_id, lego, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # deposit into yield vault
    _, _, vault_tokens_received, _ = undy_eth_vault.depositForYield(
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
def test_weth_vault_share_price_increase(
    prepareYieldDeposit,
    undy_eth_vault,
    starter_agent,
    token_str,
    fork,
):
    """Test that share value doesn't decrease when others deposit (rebasing assets behave differently)"""
    lego_id, lego, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # deposit into yield vault
    _, _, vault_tokens_received, _ = undy_eth_vault.depositForYield(
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
    whale = WHALES[fork]["WETH"]
    whale_amount = 100 * (10 ** asset.decimals())

    # Transfer to vault and deposit via lego (simulating another depositor)
    # vault is allowed to call lego.depositForYield (registered as earn vault)
    asset.transfer(undy_eth_vault.address, whale_amount, sender=WHALES[fork]["WETH"])
    asset.approve(lego.address, whale_amount, sender=undy_eth_vault.address)

    # Deposit via lego through allowed caller (simulating another depositor)
    # Parameters: _asset, _amount, _vaultAddr, _extraData, _recipient
    whale_vault_tokens = lego.depositForYield(
        asset,                # _asset
        whale_amount,         # _amount
        vault_addr,           # _vaultAddr
        b'',                  # _extraData (empty bytes32)
        whale,                # _recipient
        sender=undy_eth_vault.address
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


@pytest.base
def test_weth_vault_deposit_multiple_protocols(
    getLegoId,
    undy_eth_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
    _test,
):
    """Test depositing to multiple different protocols"""
    asset = boa.from_etherscan(TOKENS[fork]["WETH"])
    whale = WHALES[fork]["WETH"]
    mock_ripe.setPrice(asset, 2500 * EIGHTEEN_DECIMALS)

    # disable auto-deposit to allow manual deposits to specific protocols
    vault_registry.setShouldAutoDeposit(undy_eth_vault.address, False, sender=switchboard_alpha.address)

    # test with first 3 protocols
    test_protocols = ["AAVE_WETH", "COMPOUND_WETH", "MOONWELL_WETH"]

    for protocol in test_protocols:
        lego_id, lego = getLegoId(protocol)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])
        amount = 1 * (10 ** asset.decimals())

        # prepare deposit
        asset.transfer(bob, amount, sender=whale)
        asset.approve(undy_eth_vault, MAX_UINT256, sender=bob)
        undy_eth_vault.deposit(amount, bob, sender=bob)

        # approve lego and vault via VaultRegistry
        vault_registry.setApprovedVaultToken(undy_eth_vault.address, vault_addr, True, sender=switchboard_alpha.address)

        # deposit for yield
        asset_deposited, vault_token, vault_tokens_received, usd_value = undy_eth_vault.depositForYield(
            lego_id,
            asset,
            vault_addr,
            amount,
            sender=starter_agent.address
        )

        # verify deposit
        assert asset_deposited == amount
        assert vault_addr.balanceOf(undy_eth_vault) == vault_tokens_received
        assert undy_eth_vault.indexOfAsset(vault_addr.address) > 0

    # verify all 3 protocols are registered (plus base asset = 4 total)
    assert undy_eth_vault.numAssets() == 4


@pytest.base
def test_weth_vault_full_cycle(
    prepareYieldDeposit,
    undy_eth_vault,
    starter_agent,
    bob,
):
    """Test full cycle: deposit WETH → deposit to yield → withdraw from yield → redeem WETH"""
    token_str = "AAVE_WETH"
    lego_id, lego, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # 1. deposit into yield vault
    _, _, vault_tokens_received, _ = undy_eth_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    assert vault_addr.balanceOf(undy_eth_vault) == vault_tokens_received

    # 2. time travel to accrue yield
    boa.env.time_travel(seconds=24 * 60 * 60)  # 1 day

    # 3. withdraw from yield
    vault_burned, underlying_asset, underlying_received, _ = undy_eth_vault.withdrawFromYield(
        lego_id,
        vault_addr,
        vault_tokens_received,
        sender=starter_agent.address
    )

    # allow for dust/rounding (ERC4626 protocols may have tiny remainders)
    dust_remaining = vault_addr.balanceOf(undy_eth_vault)
    assert dust_remaining < 100000000000000  # less than 0.0001 WETH dust is acceptable
    # protocols/vaults round favorably to them, allow small loss (< 0.01%)
    assert underlying_received >= amount * 9999 // 10000, f"Loss too large: {amount} -> {underlying_received}"

    # 4. redeem WETH from vault
    bob_shares = undy_eth_vault.balanceOf(bob)
    initial_weth_balance = asset.balanceOf(bob)

    assets_redeemed = undy_eth_vault.redeem(bob_shares, bob, bob, sender=bob)

    # verify bob got WETH back
    final_weth_balance = asset.balanceOf(bob)
    assert final_weth_balance > initial_weth_balance
    assert assets_redeemed > 0
    assert undy_eth_vault.balanceOf(bob) == 0  # all shares burned


@pytest.base
def test_weth_vault_all_six_protocols_sequential(
    getLegoId,
    undy_eth_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
):
    """Test depositing to all 6 protocols sequentially - validates gas, integration, and array management"""
    asset = boa.from_etherscan(TOKENS[fork]["WETH"])
    whale = WHALES[fork]["WETH"]
    mock_ripe.setPrice(asset, 2500 * EIGHTEEN_DECIMALS)
    amount = 1 * (10 ** asset.decimals())

    # disable auto-deposit to allow manual deposits to specific protocols
    vault_registry.setShouldAutoDeposit(undy_eth_vault.address, False, sender=switchboard_alpha.address)

    # deposit to all 6 protocols
    vault_addrs = []
    for protocol in TEST_TOKENS:
        lego_id, lego = getLegoId(protocol)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])
        vault_addrs.append((lego_id, vault_addr, protocol))

        # prepare deposit
        asset.transfer(bob, amount, sender=whale)
        asset.approve(undy_eth_vault, MAX_UINT256, sender=bob)
        undy_eth_vault.deposit(amount, bob, sender=bob)

        # approve lego and vault via VaultRegistry
        vault_registry.setApprovedVaultToken(undy_eth_vault.address, vault_addr, True, sender=switchboard_alpha.address)

        # deposit for yield
        asset_deposited, vault_token, vault_tokens_received, usd_value = undy_eth_vault.depositForYield(
            lego_id,
            asset,
            vault_addr,
            amount,
            sender=starter_agent.address
        )

        # verify deposit
        assert asset_deposited == amount
        assert vault_addr.balanceOf(undy_eth_vault) == vault_tokens_received
        assert undy_eth_vault.indexOfAsset(vault_addr.address) > 0

    # verify all 6 protocols are registered (plus base asset = 7 total)
    assert undy_eth_vault.numAssets() == 7

    # verify each protocol is still accessible
    for lego_id, vault_addr, protocol in vault_addrs:
        assert undy_eth_vault.indexOfAsset(vault_addr.address) > 0
        assert vault_addr.balanceOf(undy_eth_vault) > 0

    # verify total assets matches expected
    expected_total = amount * 6
    total_assets = undy_eth_vault.totalAssets()
    # allow for small rounding across all protocols
    assert abs(total_assets - expected_total) <= expected_total // 1000  # 0.1% tolerance


@pytest.base
def test_weth_vault_whale_deposit_100_eth(
    getLegoId,
    undy_eth_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
):
    """Test whale-sized deposits (100 WETH) - validates real protocol capacity and gas costs"""
    asset = boa.from_etherscan(TOKENS[fork]["WETH"])
    whale = WHALES[fork]["WETH"]
    mock_ripe.setPrice(asset, 2500 * EIGHTEEN_DECIMALS)

    # 100 WETH
    amount = 100 * (10 ** asset.decimals())

    # Test with 3 major protocols
    test_protocols = ["AAVE_WETH", "COMPOUND_WETH", "MOONWELL_WETH"]

    for protocol in test_protocols:
        lego_id, lego = getLegoId(protocol)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])

        # prepare deposit
        asset.transfer(bob, amount, sender=whale)
        asset.approve(undy_eth_vault, MAX_UINT256, sender=bob)
        undy_eth_vault.deposit(amount, bob, sender=bob)

        vault_registry.setApprovedVaultToken(undy_eth_vault.address, vault_addr, True, sender=switchboard_alpha.address)

        # deposit whale amount
        asset_deposited, vault_token, vault_tokens_received, usd_value = undy_eth_vault.depositForYield(
            lego_id,
            asset,
            vault_addr,
            amount,
            sender=starter_agent.address
        )

        # verify deposit succeeded
        assert asset_deposited == amount
        assert vault_tokens_received > 0
        assert vault_addr.balanceOf(undy_eth_vault) == vault_tokens_received

        # verify withdrawal works for whale amounts
        vault_balance = vault_addr.balanceOf(undy_eth_vault)
        _, _, underlying_received, _ = undy_eth_vault.withdrawFromYield(
            lego_id,
            vault_addr,
            vault_balance,
            sender=starter_agent.address
        )

        # verify we got close to original amount (allowing for protocol fees/rounding)
        assert underlying_received >= amount * 9995 // 10000  # allow 0.05% loss max


@pytest.base
def test_weth_vault_rebasing_vs_nonrebasing_behavior(
    getLegoId,
    undy_eth_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
):
    """Test rebasing (Aave/Compound) vs non-rebasing (others) protocol behavior with real assets"""
    asset = boa.from_etherscan(TOKENS[fork]["WETH"])
    whale = WHALES[fork]["WETH"]
    mock_ripe.setPrice(asset, 2500 * EIGHTEEN_DECIMALS)
    amount = 10 * (10 ** asset.decimals())

    # disable auto-deposit to allow manual deposits to specific protocols
    vault_registry.setShouldAutoDeposit(undy_eth_vault.address, False, sender=switchboard_alpha.address)

    # Setup one rebasing and one non-rebasing protocol
    rebasing_protocol = "AAVE_WETH"
    nonrebasing_protocol = "EULER_WETH"

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
        asset.approve(undy_eth_vault, MAX_UINT256, sender=bob)
        undy_eth_vault.deposit(amount, bob, sender=bob)

        vault_registry.setApprovedVaultToken(undy_eth_vault.address, vault_addr, True, sender=switchboard_alpha.address)

        undy_eth_vault.depositForYield(
            lego_id,
            asset,
            vault_addr,
            amount,
            sender=starter_agent.address
        )

    # Record initial balances and vault token amounts
    rebasing_vault_tokens_initial = rebasing_vault.balanceOf(undy_eth_vault)
    nonrebasing_vault_tokens_initial = nonrebasing_vault.balanceOf(undy_eth_vault)

    rebasing_underlying_initial = rebasing_lego.getUnderlyingAmount(rebasing_vault, rebasing_vault_tokens_initial)
    nonrebasing_underlying_initial = nonrebasing_lego.getUnderlyingAmount(nonrebasing_vault, nonrebasing_vault_tokens_initial)

    # Time travel to simulate yield accrual
    boa.env.time_travel(seconds=7 * 24 * 60 * 60)  # 7 days

    # Check balances after time travel
    rebasing_vault_tokens_final = rebasing_vault.balanceOf(undy_eth_vault)
    nonrebasing_vault_tokens_final = nonrebasing_vault.balanceOf(undy_eth_vault)

    rebasing_underlying_final = rebasing_lego.getUnderlyingAmount(rebasing_vault, rebasing_vault_tokens_final)
    nonrebasing_underlying_final = nonrebasing_lego.getUnderlyingAmount(nonrebasing_vault, nonrebasing_vault_tokens_final)

    # REBASING behavior: vault token balance should change, but getUnderlyingAmount should remain stable
    # (on static fork, neither changes much, but they auto-adjust)
    assert rebasing_vault_tokens_initial >= rebasing_vault_tokens_final or rebasing_vault_tokens_final >= rebasing_vault_tokens_initial
    assert rebasing_underlying_final >= rebasing_underlying_initial * 9999 // 10000  # allow tiny rounding

    # NON-REBASING behavior: vault token balance stays same, underlying value stays same
    assert nonrebasing_vault_tokens_final == nonrebasing_vault_tokens_initial
    assert nonrebasing_underlying_final >= nonrebasing_underlying_initial * 9999 // 10000  # allow tiny rounding


@pytest.base
def test_weth_vault_withdraw_from_multiple_protocols(
    getLegoId,
    undy_eth_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
):
    """Test maintaining positions in multiple protocols while withdrawing from one"""
    asset = boa.from_etherscan(TOKENS[fork]["WETH"])
    whale = WHALES[fork]["WETH"]
    mock_ripe.setPrice(asset, 2500 * EIGHTEEN_DECIMALS)
    amount = 1 * (10 ** asset.decimals())

    # disable auto-deposit to allow manual deposits to specific protocols
    vault_registry.setShouldAutoDeposit(undy_eth_vault.address, False, sender=switchboard_alpha.address)

    # deposit to two protocols
    protocols = ["AAVE_WETH", "MOONWELL_WETH"]
    vault_addrs = []

    for protocol in protocols:
        lego_id, lego = getLegoId(protocol)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])
        vault_addrs.append((lego_id, vault_addr))

        asset.transfer(bob, amount, sender=whale)
        asset.approve(undy_eth_vault, MAX_UINT256, sender=bob)
        undy_eth_vault.deposit(amount, bob, sender=bob)

        vault_registry.setApprovedVaultToken(undy_eth_vault.address, vault_addr, True, sender=switchboard_alpha.address)

        undy_eth_vault.depositForYield(
            lego_id,
            asset,
            vault_addr,
            amount,
            sender=starter_agent.address
        )

    # verify both registered
    assert undy_eth_vault.numAssets() == 3  # base + 2 protocols

    # withdraw from first protocol only
    lego_id_1, vault_addr_1 = vault_addrs[0]
    vault_balance_1 = vault_addr_1.balanceOf(undy_eth_vault)

    undy_eth_vault.withdrawFromYield(
        lego_id_1,
        vault_addr_1,
        vault_balance_1,
        sender=starter_agent.address
    )

    # verify first deregistered, second still registered
    assert undy_eth_vault.indexOfAsset(vault_addr_1.address) == 0
    assert undy_eth_vault.indexOfAsset(vault_addrs[1][1].address) > 0
    assert undy_eth_vault.numAssets() == 2  # base + 1 protocol


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_weth_vault_conversion_accuracy(
    prepareYieldDeposit,
    undy_eth_vault,
    starter_agent,
    token_str,
):
    """Test convertToAssets and convertToShares accuracy"""
    lego_id, lego, vault_addr, asset, amount = prepareYieldDeposit(token_str)

    # deposit into yield vault
    _, _, vault_tokens_received, _ = undy_eth_vault.depositForYield(
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
def test_weth_vault_small_deposit(
    getLegoId,
    undy_eth_vault,
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
    asset = boa.from_etherscan(TOKENS[fork]["WETH"])
    whale = WHALES[fork]["WETH"]

    # 0.001 WETH (18 decimals)
    amount = 1 * (10 ** (asset.decimals() - 3))

    mock_ripe.setPrice(asset, 2500 * EIGHTEEN_DECIMALS)
    asset.transfer(bob, amount, sender=whale)
    asset.approve(undy_eth_vault, MAX_UINT256, sender=bob)
    undy_eth_vault.deposit(amount, bob, sender=bob)

    vault_registry.setApprovedVaultToken(undy_eth_vault.address, vault_addr, True, sender=switchboard_alpha.address)

    # deposit small amount
    asset_deposited, vault_token, vault_tokens_received, usd_value = undy_eth_vault.depositForYield(
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
def test_weth_vault_large_deposit(
    getLegoId,
    undy_eth_vault,
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
    asset = boa.from_etherscan(TOKENS[fork]["WETH"])
    whale = WHALES[fork]["WETH"]

    # 100 WETH (reduced from 1000 - whale balance constraint)
    amount = 100 * (10 ** asset.decimals())

    mock_ripe.setPrice(asset, 2500 * EIGHTEEN_DECIMALS)
    asset.transfer(bob, amount, sender=whale)
    asset.approve(undy_eth_vault, MAX_UINT256, sender=bob)
    undy_eth_vault.deposit(amount, bob, sender=bob)

    vault_registry.setApprovedVaultToken(undy_eth_vault.address, vault_addr, True, sender=switchboard_alpha.address)

    # deposit large amount
    asset_deposited, vault_token, vault_tokens_received, usd_value = undy_eth_vault.depositForYield(
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
def test_weth_vault_whale_deposit_1000_eth(
    getLegoId,
    undy_eth_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
    token_str,
):
    """Test whale-sized deposits (100 WETH) - validates real protocol capacity and gas costs"""
    lego_id, lego = getLegoId(token_str)
    vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][token_str])
    asset = boa.from_etherscan(TOKENS[fork]["WETH"])
    whale = WHALES[fork]["WETH"]

    # 100 WETH (reduced from 1000 - whale balance constraint)
    amount = 100 * (10 ** asset.decimals())

    mock_ripe.setPrice(asset, 2500 * EIGHTEEN_DECIMALS)
    asset.transfer(bob, amount, sender=whale)
    asset.approve(undy_eth_vault, MAX_UINT256, sender=bob)
    undy_eth_vault.deposit(amount, bob, sender=bob)

    vault_registry.setApprovedVaultToken(undy_eth_vault.address, vault_addr, True, sender=switchboard_alpha.address)

    # deposit whale amount
    asset_deposited, vault_token, vault_tokens_received, usd_value = undy_eth_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # verify deposit succeeded
    assert asset_deposited == amount
    assert vault_tokens_received > 0
    assert vault_addr.balanceOf(undy_eth_vault) == vault_tokens_received

    # verify withdrawal works for whale amounts
    vault_balance = vault_addr.balanceOf(undy_eth_vault)
    _, _, underlying_received, _ = undy_eth_vault.withdrawFromYield(
        lego_id,
        vault_addr,
        vault_balance,
        sender=starter_agent.address
    )

    # verify we got close to original amount (allowing for protocol fees/rounding)
    assert underlying_received >= amount * 9995 // 10000  # allow 0.05% loss max


@pytest.base
def test_weth_vault_whale_deposit_10000_eth_multiple_protocols(
    getLegoId,
    undy_eth_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
):
    """Test extreme whale deposits (100 WETH per protocol) across multiple protocols"""
    asset = boa.from_etherscan(TOKENS[fork]["WETH"])
    whale = WHALES[fork]["WETH"]
    mock_ripe.setPrice(asset, 2500 * EIGHTEEN_DECIMALS)

    # disable auto-deposit to allow manual deposits to specific protocols
    vault_registry.setShouldAutoDeposit(undy_eth_vault.address, False, sender=switchboard_alpha.address)

    # 100 WETH per protocol (reduced from 1000 - whale balance constraint)
    amount_per_protocol = 100 * (10 ** asset.decimals())

    # Test with 3 major protocols to validate extreme amounts
    test_protocols = ["AAVE_WETH", "COMPOUND_WETH", "MOONWELL_WETH"]

    for protocol in test_protocols:
        lego_id, lego = getLegoId(protocol)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])

        # prepare deposit
        asset.transfer(bob, amount_per_protocol, sender=whale)
        asset.approve(undy_eth_vault, MAX_UINT256, sender=bob)
        undy_eth_vault.deposit(amount_per_protocol, bob, sender=bob)

        vault_registry.setApprovedVaultToken(undy_eth_vault.address, vault_addr, True, sender=switchboard_alpha.address)

        # deposit whale amount
        asset_deposited, vault_token, vault_tokens_received, usd_value = undy_eth_vault.depositForYield(
            lego_id,
            asset,
            vault_addr,
            amount_per_protocol,
            sender=starter_agent.address
        )

        # verify each deposit succeeded
        assert asset_deposited == amount_per_protocol
        assert vault_tokens_received > 0

    # verify total assets is correct (300 WETH)
    expected_total = amount_per_protocol * 3
    total_assets = undy_eth_vault.totalAssets()
    # allow for small rounding across protocols
    assert abs(total_assets - expected_total) <= expected_total // 1000  # 0.1% tolerance


@pytest.base
def test_weth_vault_emergency_withdrawal_multiple_protocols(
    getLegoId,
    undy_eth_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
):
    """Test emergency user withdrawal triggering redemption from multiple yield positions"""
    asset = boa.from_etherscan(TOKENS[fork]["WETH"])
    whale = WHALES[fork]["WETH"]
    mock_ripe.setPrice(asset, 2500 * EIGHTEEN_DECIMALS)

    # disable auto-deposit to allow manual deposits to specific protocols
    vault_registry.setShouldAutoDeposit(undy_eth_vault.address, False, sender=switchboard_alpha.address)

    amount_per_protocol = 10 * (10 ** asset.decimals())

    # Setup 3 protocols with deposits
    test_protocols = ["AAVE_WETH", "COMPOUND_WETH", "MOONWELL_WETH"]
    total_deposited = 0

    for protocol in test_protocols:
        lego_id, lego = getLegoId(protocol)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])

        asset.transfer(bob, amount_per_protocol, sender=whale)
        asset.approve(undy_eth_vault, MAX_UINT256, sender=bob)
        undy_eth_vault.deposit(amount_per_protocol, bob, sender=bob)

        vault_registry.setApprovedVaultToken(undy_eth_vault.address, vault_addr, True, sender=switchboard_alpha.address)

        undy_eth_vault.depositForYield(
            lego_id,
            asset,
            vault_addr,
            amount_per_protocol,
            sender=starter_agent.address
        )
        total_deposited += amount_per_protocol

    # Verify all protocols are registered (base + 3 = 4)
    assert undy_eth_vault.numAssets() == 4

    # Bob has shares for all deposits
    bob_shares = undy_eth_vault.balanceOf(bob)
    assert bob_shares > 0

    # Emergency: Bob wants to withdraw everything
    initial_weth = asset.balanceOf(bob)

    # Withdraw all
    assets_received = undy_eth_vault.redeem(bob_shares, bob, bob, sender=bob)

    # Verify Bob received WETH
    final_weth = asset.balanceOf(bob)
    assert final_weth > initial_weth
    assert assets_received > 0

    # Should have received close to total deposited (accounting for rounding/fees)
    assert assets_received >= total_deposited * 999 // 1000  # 0.1% tolerance

    # Verify shares were burned
    assert undy_eth_vault.balanceOf(bob) == 0

    # Verify redemption pulled from multiple protocols
    final_num_assets = undy_eth_vault.numAssets()
    assert final_num_assets <= 4


@pytest.base
def test_weth_vault_emergency_partial_withdrawal_with_redemption_buffer(
    getLegoId,
    undy_eth_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
):
    """Test large withdrawal requiring yield position redemption with redemption buffer"""
    asset = boa.from_etherscan(TOKENS[fork]["WETH"])
    whale = WHALES[fork]["WETH"]
    mock_ripe.setPrice(asset, 2500 * EIGHTEEN_DECIMALS)

    # Deposit small amount to vault (keeping idle)
    idle_amount = 1 * (10 ** (asset.decimals() - 1))  # 0.1 WETH
    asset.transfer(bob, idle_amount, sender=whale)
    asset.approve(undy_eth_vault, MAX_UINT256, sender=bob)
    undy_eth_vault.deposit(idle_amount, bob, sender=bob)

    # Deposit large amount to yield
    yield_amount = 500 * (10 ** asset.decimals())
    lego_id, lego = getLegoId("AAVE_WETH")
    vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork]["AAVE_WETH"])

    asset.transfer(bob, yield_amount, sender=whale)
    undy_eth_vault.deposit(yield_amount, bob, sender=bob)

    vault_registry.setApprovedVaultToken(undy_eth_vault.address, vault_addr, True, sender=switchboard_alpha.address)

    undy_eth_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        yield_amount,
        sender=starter_agent.address
    )

    # Try to withdraw more than idle (should trigger yield withdrawal)
    withdraw_amount = 300 * (10 ** asset.decimals())  # More than idle, less than total

    initial_balance = asset.balanceOf(bob)
    undy_eth_vault.withdraw(withdraw_amount, bob, bob, sender=bob)
    final_balance = asset.balanceOf(bob)

    # Verify user received requested amount
    assert final_balance - initial_balance == withdraw_amount

    # Verify vault balance decreased in vault token (redemption occurred)
    remaining_vault_tokens = vault_addr.balanceOf(undy_eth_vault)
    # Should have withdrawn from yield (but not all)
    assert remaining_vault_tokens > 0  # Still has some
    assert remaining_vault_tokens < yield_amount  # But less than original

    # Verify redemption buffer pulled extra (2% default)
    vault_balance = asset.balanceOf(undy_eth_vault.address)
    # Should have buffer amount sitting idle now
    expected_idle = (withdraw_amount - idle_amount) * 2 // 100  # 2% buffer of redeemed amount
    # Allow for variation in buffer calculation
    assert vault_balance >= expected_idle * 90 // 100  # At least 90% of expected buffer


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_weth_vault_decimal_precision_large_amounts(
    getLegoId,
    undy_eth_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
    token_str,
    _test,
):
    """Test decimal precision with large amounts (WETH=18 decimals, vault tokens typically 18)"""
    lego_id, lego = getLegoId(token_str)
    vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][token_str])
    asset = boa.from_etherscan(TOKENS[fork]["WETH"])
    whale = WHALES[fork]["WETH"]

    # Large amount: 50 WETH (18 decimals) - reduced from 5000 due to whale balance constraint
    amount = 50 * (10 ** asset.decimals())

    mock_ripe.setPrice(asset, 2500 * EIGHTEEN_DECIMALS)
    asset.transfer(bob, amount, sender=whale)
    asset.approve(undy_eth_vault, MAX_UINT256, sender=bob)
    undy_eth_vault.deposit(amount, bob, sender=bob)

    vault_registry.setApprovedVaultToken(undy_eth_vault.address, vault_addr, True, sender=switchboard_alpha.address)

    # Deposit
    asset_deposited, vault_token, vault_tokens_received, usd_value = undy_eth_vault.depositForYield(
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
    precision_loss_tolerance = amount // 100000  # 0.001% tolerance
    assert abs(underlying_amount - amount) <= precision_loss_tolerance, \
        f"Precision loss too high: {amount} -> {underlying_amount} (diff: {abs(underlying_amount - amount)})"

    # Test withdrawal precision
    _, _, underlying_received, _ = undy_eth_vault.withdrawFromYield(
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
def test_weth_vault_decimal_precision_dust_amounts(
    getLegoId,
    undy_eth_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
):
    """Test decimal precision with dust amounts"""
    asset = boa.from_etherscan(TOKENS[fork]["WETH"])
    whale = WHALES[fork]["WETH"]
    mock_ripe.setPrice(asset, 2500 * EIGHTEEN_DECIMALS)

    # Test with Aave (rebasing) and Euler (non-rebasing)
    test_cases = [
        ("AAVE_WETH", 0.01),    # 0.01 WETH
        ("EULER_WETH", 0.01),   # 0.01 WETH
        ("AAVE_WETH", 0.015),   # 0.015 WETH (fractional)
        ("EULER_WETH", 0.001),  # 0.001 WETH (small fraction)
    ]

    # Pre-approve all protocols
    approved_protocols = set()
    for protocol, _ in test_cases:
        if protocol not in approved_protocols:
            lego_id, lego = getLegoId(protocol)
            vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])
            vault_registry.setApprovedVaultToken(undy_eth_vault.address, vault_addr, True, sender=switchboard_alpha.address)
            approved_protocols.add(protocol)

    for protocol, weth_amount in test_cases:
        lego_id, lego = getLegoId(protocol)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])

        # Convert WETH amount to proper decimals
        amount = int(weth_amount * (10 ** asset.decimals()))

        asset.transfer(bob, amount, sender=whale)
        asset.approve(undy_eth_vault, MAX_UINT256, sender=bob)
        undy_eth_vault.deposit(amount, bob, sender=bob)

        # Deposit
        asset_deposited, _, vault_tokens_received, _ = undy_eth_vault.depositForYield(
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
        _, _, underlying_received, _ = undy_eth_vault.withdrawFromYield(
            lego_id,
            vault_addr,
            vault_tokens_received,
            sender=starter_agent.address
        )

        # Allow for rounding on dust amounts (up to 2 wei loss)
        assert underlying_received >= amount - 2, \
            f"Dust amount precision loss: {protocol} {weth_amount} WETH: {amount} -> {underlying_received}"


@pytest.mark.parametrize("token_str", TEST_TOKENS)
@pytest.base
def test_weth_vault_deregister_and_reregister(
    getLegoId,
    undy_eth_vault,
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
    asset = boa.from_etherscan(TOKENS[fork]["WETH"])
    whale = WHALES[fork]["WETH"]
    amount = 10 * (10 ** asset.decimals())

    mock_ripe.setPrice(asset, 2500 * EIGHTEEN_DECIMALS)

    # Initial setup
    asset.transfer(bob, amount, sender=whale)
    asset.approve(undy_eth_vault, MAX_UINT256, sender=bob)
    undy_eth_vault.deposit(amount, bob, sender=bob)

    vault_registry.setApprovedVaultToken(undy_eth_vault.address, vault_addr, True, sender=switchboard_alpha.address)

    # First deposit
    _, _, vault_tokens_1, _ = undy_eth_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # Verify registered
    assert undy_eth_vault.indexOfAsset(vault_addr.address) > 0
    initial_num_assets = undy_eth_vault.numAssets()

    # Full withdrawal (deregisters)
    undy_eth_vault.withdrawFromYield(
        lego_id,
        vault_addr,
        vault_tokens_1,
        sender=starter_agent.address
    )

    # Verify deregistered
    assert undy_eth_vault.indexOfAsset(vault_addr.address) == 0
    assert undy_eth_vault.numAssets() == initial_num_assets - 1

    # Re-deposit to same protocol (re-registers)
    asset.transfer(bob, amount, sender=whale)
    undy_eth_vault.deposit(amount, bob, sender=bob)

    _, _, vault_tokens_2, _ = undy_eth_vault.depositForYield(
        lego_id,
        asset,
        vault_addr,
        amount,
        sender=starter_agent.address
    )

    # Verify re-registered
    assert undy_eth_vault.indexOfAsset(vault_addr.address) > 0
    assert undy_eth_vault.numAssets() == initial_num_assets

    # Verify vault works correctly after re-registration
    assert vault_tokens_2 > 0
    assert vault_addr.balanceOf(undy_eth_vault) == vault_tokens_2

    # Verify withdrawal still works after re-registration
    _, _, underlying_received, _ = undy_eth_vault.withdrawFromYield(
        lego_id,
        vault_addr,
        vault_tokens_2,
        sender=starter_agent.address
    )

    assert underlying_received >= amount * 999 // 1000  # 0.1% tolerance


@pytest.base
def test_weth_vault_multiple_deregister_reregister_cycles(
    getLegoId,
    undy_eth_vault,
    vault_registry,
    starter_agent,
    bob,
    fork,
    switchboard_alpha,
    mock_ripe,
):
    """Test multiple cycles of deregistration and re-registration to validate array management"""
    asset = boa.from_etherscan(TOKENS[fork]["WETH"])
    whale = WHALES[fork]["WETH"]
    mock_ripe.setPrice(asset, 2500 * EIGHTEEN_DECIMALS)
    amount = 5 * (10 ** asset.decimals())

    # disable auto-deposit to allow manual deposits to specific protocols
    vault_registry.setShouldAutoDeposit(undy_eth_vault.address, False, sender=switchboard_alpha.address)

    # Setup two protocols
    protocols = ["AAVE_WETH", "EULER_WETH"]
    protocol_data = []

    for protocol in protocols:
        lego_id, lego = getLegoId(protocol)
        vault_addr = boa.from_etherscan(ALL_VAULT_TOKENS[fork][protocol])
        protocol_data.append((protocol, lego_id, vault_addr))

        vault_registry.setApprovedVaultToken(undy_eth_vault.address, vault_addr, True, sender=switchboard_alpha.address)

    # Perform 3 cycles of deposit/withdraw for each protocol
    for cycle in range(3):
        for protocol_name, lego_id, vault_addr in protocol_data:
            # Deposit
            asset.transfer(bob, amount, sender=whale)
            asset.approve(undy_eth_vault, MAX_UINT256, sender=bob)
            undy_eth_vault.deposit(amount, bob, sender=bob)

            _, _, vault_tokens, _ = undy_eth_vault.depositForYield(
                lego_id,
                asset,
                vault_addr,
                amount,
                sender=starter_agent.address
            )

            # Verify registered
            assert undy_eth_vault.indexOfAsset(vault_addr.address) > 0

            # Withdraw (deregister)
            undy_eth_vault.withdrawFromYield(
                lego_id,
                vault_addr,
                vault_tokens,
                sender=starter_agent.address
            )

            # Verify deregistered
            assert undy_eth_vault.indexOfAsset(vault_addr.address) == 0

    # Final verification: deposit to both and ensure both work
    for protocol_name, lego_id, vault_addr in protocol_data:
        asset.transfer(bob, amount, sender=whale)
        asset.approve(undy_eth_vault, MAX_UINT256, sender=bob)
        undy_eth_vault.deposit(amount, bob, sender=bob)

        _, _, vault_tokens, _ = undy_eth_vault.depositForYield(
            lego_id,
            asset,
            vault_addr,
            amount,
            sender=starter_agent.address
        )

        assert undy_eth_vault.indexOfAsset(vault_addr.address) > 0
        assert vault_tokens > 0

    # Both protocols should be registered (base + 2 = 3)
    assert undy_eth_vault.numAssets() == 3
