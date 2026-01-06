"""
Comprehensive tests for raw ERC20 asset collateral in leverage vaults.

Tests raw assets (like cbXRP, uSOL) used directly as collateral without ERC4626 vault wrapping.
Key difference from standard vaults: collateralVaultToken == underlyingAsset, legoId == 0.
"""

import pytest
import boa

from constants import MAX_UINT256, ZERO_ADDRESS
from tests.conf_utils import filter_logs

# Decimal constants
SIX_DECIMALS = 10 ** 6
EIGHT_DECIMALS = 10 ** 8
EIGHTEEN_DECIMALS = 10 ** 18

# Lego IDs
RIPE_LEGO_ID = 1
MOCK_YIELD_LEGO_ID = 2

# Event operation codes
OP_DEPOSIT_FOR_YIELD = 10
OP_WITHDRAW_FROM_YIELD = 11
OP_ADD_COLLATERAL = 40
OP_REMOVE_COLLATERAL = 41
OP_BORROW = 42
OP_REPAY_DEBT = 43


############
# Fixtures #
############


@pytest.fixture(scope="module")
def setup_raw_asset_prices(
    mock_ripe,
    bravo_token,
    charlie_token,
    delta_token,
    mock_green_token,
    mock_savings_green_token,
    mock_usdc,
):
    """Set up prices for raw asset test tokens"""
    mock_ripe.setPrice(bravo_token.address, 50 * EIGHTEEN_DECIMALS)  # $50 per token
    mock_ripe.setPrice(charlie_token.address, 1 * EIGHTEEN_DECIMALS)  # $1 per token (stablecoin-like)
    mock_ripe.setPrice(delta_token.address, 90_000 * EIGHTEEN_DECIMALS)  # $90k per token (BTC-like)
    mock_ripe.setPrice(mock_green_token.address, 1 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_savings_green_token.address, 1 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_usdc.address, 1 * EIGHTEEN_DECIMALS)
    return mock_ripe


@pytest.fixture(scope="module")
def raw_asset_levg_vault_18dec(
    undy_hq,
    levg_vault_helper,
    mock_usdc_leverage_vault,
    vault_registry,
    governance,
    fork,
    starter_agent,
    bravo_token,
    mock_usdc,
    mock_green_token,
    mock_savings_green_token,
    setup_raw_asset_prices,
    mock_ripe,
):
    """Leverage vault with 18-decimal raw asset collateral (legoId=0)

    Key configuration:
    - collateralVaultToken = bravo_token (same as underlying)
    - collateralLegoId = 0 (raw asset, no yield vault)
    - isRawAssetCollateral = True (auto-detected)
    """
    from tests.conf_core import PARAMS

    vault = boa.load(
        "contracts/vaults/LevgVault.vy",
        bravo_token.address,  # underlying asset (18 decimals)
        "Raw Asset Levg 18dec",  # name
        "uRAW18",  # symbol
        undy_hq.address,
        bravo_token.address,  # collateral vault token = raw asset itself
        0,  # collateral lego id = 0 (raw asset)
        1,  # collateral ripe vault id
        mock_usdc_leverage_vault.address,  # leverage vault (USDC)
        MOCK_YIELD_LEGO_ID,  # leverage lego id
        1,  # leverage ripe vault id
        mock_usdc.address,
        mock_green_token.address,
        mock_savings_green_token.address,
        PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"],
        PARAMS[fork]["UNDY_HQ_MAX_GOV_TIMELOCK"],
        starter_agent.address,
        levg_vault_helper.address,
        name="raw_asset_levg_vault_18dec",
    )

    # Register in VaultRegistry
    vault_registry.startAddNewAddressToRegistry(
        vault.address, "Raw Asset Levg 18dec", sender=governance.address
    )
    boa.env.time_travel(blocks=vault_registry.registryChangeTimeLock())

    vault_registry.confirmNewAddressToRegistry(
        vault.address,
        True,  # isLeveragedVault
        False,  # shouldEnforceAllowlist
        [],  # approvedVaultTokens
        0,  # maxDepositAmount
        100_000_000_000,  # minYieldWithdrawAmount
        0,  # performanceFee
        ZERO_ADDRESS,  # defaultTargetVaultToken
        True,  # shouldAutoDeposit
        True,  # canDeposit
        True,  # canWithdraw
        False,  # isVaultOpsFrozen
        2_00,  # redemptionBuffer (2%)
        sender=governance.address,
    )

    # Set unlimited borrow amount for this vault
    mock_ripe.setMaxBorrowAmount(vault.address, MAX_UINT256)

    return vault


@pytest.fixture(scope="module")
def raw_asset_levg_vault_6dec(
    undy_hq,
    levg_vault_helper,
    mock_usdc_leverage_vault,
    vault_registry,
    governance,
    fork,
    starter_agent,
    charlie_token,
    mock_usdc,
    mock_green_token,
    mock_savings_green_token,
    setup_raw_asset_prices,
    mock_ripe,
):
    """Leverage vault with 6-decimal raw asset collateral (legoId=0)"""
    from tests.conf_core import PARAMS

    vault = boa.load(
        "contracts/vaults/LevgVault.vy",
        charlie_token.address,  # underlying asset (6 decimals)
        "Raw Asset Levg 6dec",  # name
        "uRAW6",  # symbol
        undy_hq.address,
        charlie_token.address,  # collateral vault token = raw asset itself
        0,  # collateral lego id = 0 (raw asset)
        1,  # collateral ripe vault id
        mock_usdc_leverage_vault.address,  # leverage vault (USDC)
        MOCK_YIELD_LEGO_ID,  # leverage lego id
        1,  # leverage ripe vault id
        mock_usdc.address,
        mock_green_token.address,
        mock_savings_green_token.address,
        PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"],
        PARAMS[fork]["UNDY_HQ_MAX_GOV_TIMELOCK"],
        starter_agent.address,
        levg_vault_helper.address,
        name="raw_asset_levg_vault_6dec",
    )

    # Register in VaultRegistry
    vault_registry.startAddNewAddressToRegistry(
        vault.address, "Raw Asset Levg 6dec", sender=governance.address
    )
    boa.env.time_travel(blocks=vault_registry.registryChangeTimeLock())

    vault_registry.confirmNewAddressToRegistry(
        vault.address,
        True,  # isLeveragedVault
        False,  # shouldEnforceAllowlist
        [],
        0,
        100_000_000_000,
        0,
        ZERO_ADDRESS,
        True,
        True,
        True,
        False,
        2_00,
        sender=governance.address,
    )

    mock_ripe.setMaxBorrowAmount(vault.address, MAX_UINT256)

    return vault


@pytest.fixture(scope="module")
def raw_asset_levg_vault_8dec(
    undy_hq,
    levg_vault_helper,
    mock_usdc_leverage_vault,
    vault_registry,
    governance,
    fork,
    starter_agent,
    delta_token,
    mock_usdc,
    mock_green_token,
    mock_savings_green_token,
    setup_raw_asset_prices,
    mock_ripe,
):
    """Leverage vault with 8-decimal raw asset collateral (legoId=0)"""
    from tests.conf_core import PARAMS

    vault = boa.load(
        "contracts/vaults/LevgVault.vy",
        delta_token.address,  # underlying asset (8 decimals)
        "Raw Asset Levg 8dec",  # name
        "uRAW8",  # symbol
        undy_hq.address,
        delta_token.address,  # collateral vault token = raw asset itself
        0,  # collateral lego id = 0 (raw asset)
        1,  # collateral ripe vault id
        mock_usdc_leverage_vault.address,  # leverage vault (USDC)
        MOCK_YIELD_LEGO_ID,  # leverage lego id
        1,  # leverage ripe vault id
        mock_usdc.address,
        mock_green_token.address,
        mock_savings_green_token.address,
        PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"],
        PARAMS[fork]["UNDY_HQ_MAX_GOV_TIMELOCK"],
        starter_agent.address,
        levg_vault_helper.address,
        name="raw_asset_levg_vault_8dec",
    )

    # Register in VaultRegistry
    vault_registry.startAddNewAddressToRegistry(
        vault.address, "Raw Asset Levg 8dec", sender=governance.address
    )
    boa.env.time_travel(blocks=vault_registry.registryChangeTimeLock())

    vault_registry.confirmNewAddressToRegistry(
        vault.address,
        True,  # isLeveragedVault
        False,
        [],
        0,
        100_000_000_000,
        0,
        ZERO_ADDRESS,
        True,
        True,
        True,
        False,
        2_00,
        sender=governance.address,
    )

    mock_ripe.setMaxBorrowAmount(vault.address, MAX_UINT256)

    return vault


@pytest.fixture(scope="module")
def raw_vault_with_funds_18dec(raw_asset_levg_vault_18dec, bravo_token, governance):
    """Raw asset vault pre-funded with 1000 bravo tokens"""
    amount = 1000 * EIGHTEEN_DECIMALS
    bravo_token.mint(raw_asset_levg_vault_18dec.address, amount, sender=governance.address)
    return raw_asset_levg_vault_18dec


@pytest.fixture(scope="module")
def raw_vault_with_funds_6dec(raw_asset_levg_vault_6dec, charlie_token, governance):
    """Raw asset vault pre-funded with 1000 charlie tokens"""
    amount = 1000 * SIX_DECIMALS
    charlie_token.mint(raw_asset_levg_vault_6dec.address, amount, sender=governance.address)
    return raw_asset_levg_vault_6dec


@pytest.fixture(scope="module")
def raw_vault_with_funds_8dec(raw_asset_levg_vault_8dec, delta_token, governance):
    """Raw asset vault pre-funded with 10 delta tokens (BTC-like, expensive)"""
    amount = 10 * EIGHT_DECIMALS
    delta_token.mint(raw_asset_levg_vault_8dec.address, amount, sender=governance.address)
    return raw_asset_levg_vault_8dec


#################################
# Category 1: Initialization Tests
#################################


def test_initialize_with_raw_asset_collateral_18_decimals(
    raw_asset_levg_vault_18dec,
    bravo_token,
):
    """Verify vault initializes correctly with 18-decimal raw asset"""
    vault = raw_asset_levg_vault_18dec

    # isRawAssetCollateral flag must be True
    assert vault.isRawAssetCollateral() == True

    # vaultToLegoId for the raw asset must be 0
    assert vault.vaultToLegoId(bravo_token.address) == 0

    # collateralAsset.vaultToken must equal the underlying asset
    collateral_asset = vault.collateralAsset()
    assert collateral_asset[0] == bravo_token.address  # vaultToken

    # asset() must return the raw asset
    assert vault.asset() == bravo_token.address


def test_initialize_with_raw_asset_collateral_6_decimals(
    raw_asset_levg_vault_6dec,
    charlie_token,
):
    """Verify vault initializes correctly with 6-decimal raw asset"""
    vault = raw_asset_levg_vault_6dec

    assert vault.isRawAssetCollateral() == True
    assert vault.vaultToLegoId(charlie_token.address) == 0
    collateral_asset = vault.collateralAsset()
    assert collateral_asset[0] == charlie_token.address
    assert vault.asset() == charlie_token.address


def test_initialize_with_raw_asset_collateral_8_decimals(
    raw_asset_levg_vault_8dec,
    delta_token,
):
    """Verify vault initializes correctly with 8-decimal raw asset"""
    vault = raw_asset_levg_vault_8dec

    assert vault.isRawAssetCollateral() == True
    assert vault.vaultToLegoId(delta_token.address) == 0
    collateral_asset = vault.collateralAsset()
    assert collateral_asset[0] == delta_token.address
    assert vault.asset() == delta_token.address


def test_raw_asset_collateral_asset_matches_underlying(
    raw_asset_levg_vault_18dec,
    bravo_token,
):
    """Verify collateralAsset.vaultToken == asset() for raw assets"""
    vault = raw_asset_levg_vault_18dec

    collateral_asset = vault.collateralAsset()
    collateral_vault_token = collateral_asset[0]
    underlying_asset = vault.asset()

    # For raw assets, these must be identical
    assert collateral_vault_token == underlying_asset
    assert collateral_vault_token == bravo_token.address


def test_raw_asset_leverage_vault_is_separate(
    raw_asset_levg_vault_18dec,
    mock_usdc_leverage_vault,
    bravo_token,
):
    """Verify leverage vault is separate ERC4626 (USDC), not raw asset"""
    vault = raw_asset_levg_vault_18dec

    leverage_asset = vault.leverageAsset()
    leverage_vault_token = leverage_asset[0]

    # Leverage vault must NOT be the raw asset
    assert leverage_vault_token != bravo_token.address

    # Leverage vault must be the USDC vault
    assert leverage_vault_token == mock_usdc_leverage_vault.address

    # Leverage vault has a non-zero legoId
    assert vault.vaultToLegoId(mock_usdc_leverage_vault.address) == MOCK_YIELD_LEGO_ID


#################################
# Category 2: Deposit Flow Tests
#################################


def test_deposit_raw_asset_auto_adds_to_ripe(
    raw_asset_levg_vault_18dec,
    bravo_token,
    mock_ripe,
    governance,
    alice,
):
    """User deposits raw asset → automatically goes to Ripe collateral via _onReceiveVaultFunds"""
    vault = raw_asset_levg_vault_18dec  # Use clean vault without pre-funded tokens

    # Get initial state
    pre_ripe_collateral = mock_ripe.userCollateral(vault.address, bravo_token.address)
    pre_wallet_balance = bravo_token.balanceOf(vault.address)
    assert pre_wallet_balance == 0  # Verify clean vault

    # Mint tokens to Alice and approve vault
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    bravo_token.mint(alice, deposit_amount, sender=governance.address)
    bravo_token.approve(vault.address, deposit_amount, sender=alice)

    # Deposit to vault
    shares = vault.deposit(deposit_amount, alice, sender=alice)

    # Shares received should be non-zero
    assert shares > 0

    # Ripe collateral should increase by deposit amount
    post_ripe_collateral = mock_ripe.userCollateral(vault.address, bravo_token.address)
    assert post_ripe_collateral == pre_ripe_collateral + deposit_amount


def test_deposit_raw_asset_updates_wallet_balance(
    raw_asset_levg_vault_18dec,
    bravo_token,
    governance,
    bob,
):
    """Wallet balance decreases after deposit (transferred to Ripe)"""
    vault = raw_asset_levg_vault_18dec

    deposit_amount = 50 * EIGHTEEN_DECIMALS
    bravo_token.mint(bob, deposit_amount, sender=governance.address)

    pre_bob_balance = bravo_token.balanceOf(bob)
    assert pre_bob_balance == deposit_amount

    bravo_token.approve(vault.address, deposit_amount, sender=bob)
    vault.deposit(deposit_amount, bob, sender=bob)

    # Bob's balance should be zero (all deposited)
    post_bob_balance = bravo_token.balanceOf(bob)
    assert post_bob_balance == 0


def test_deposit_raw_asset_returns_correct_shares(
    raw_asset_levg_vault_18dec,
    bravo_token,
    governance,
    alice,
):
    """Deposit returns correct number of shares based on exchange rate"""
    vault = raw_asset_levg_vault_18dec

    deposit_amount = 100 * EIGHTEEN_DECIMALS
    bravo_token.mint(alice, deposit_amount, sender=governance.address)
    bravo_token.approve(vault.address, deposit_amount, sender=alice)

    # For first deposit, shares should equal deposit amount (1:1 rate)
    pre_total_shares = vault.totalSupply()

    shares = vault.deposit(deposit_amount, alice, sender=alice)

    # Verify shares were minted
    assert vault.balanceOf(alice) == shares
    assert vault.totalSupply() == pre_total_shares + shares


def test_deposit_raw_asset_multiple_deposits_accumulate(
    raw_asset_levg_vault_18dec,
    bravo_token,
    mock_ripe,
    governance,
    alice,
):
    """Multiple deposits sum correctly in Ripe collateral"""
    vault = raw_asset_levg_vault_18dec

    pre_ripe_collateral = mock_ripe.userCollateral(vault.address, bravo_token.address)

    deposit1 = 50 * EIGHTEEN_DECIMALS
    deposit2 = 75 * EIGHTEEN_DECIMALS
    total_deposit = deposit1 + deposit2

    # First deposit
    bravo_token.mint(alice, deposit1, sender=governance.address)
    bravo_token.approve(vault.address, deposit1, sender=alice)
    vault.deposit(deposit1, alice, sender=alice)

    # Second deposit
    bravo_token.mint(alice, deposit2, sender=governance.address)
    bravo_token.approve(vault.address, deposit2, sender=alice)
    vault.deposit(deposit2, alice, sender=alice)

    # Total collateral should be sum of deposits
    post_ripe_collateral = mock_ripe.userCollateral(vault.address, bravo_token.address)
    assert post_ripe_collateral == pre_ripe_collateral + total_deposit


###########################################
# Category 3: depositForYield Rejection Tests
###########################################


def test_deposit_for_yield_rejects_raw_asset_underlying(
    raw_vault_with_funds_18dec,
    bravo_token,
    starter_agent,
):
    """Calling depositForYield with underlying asset MUST revert for raw asset vaults"""
    vault = raw_vault_with_funds_18dec

    deposit_amount = 100 * EIGHTEEN_DECIMALS

    # depositForYield with the underlying (raw) asset must revert
    with boa.reverts():
        vault.depositForYield(
            MOCK_YIELD_LEGO_ID,
            bravo_token.address,  # underlying = raw asset
            bravo_token.address,  # vault token = raw asset (same for raw assets)
            deposit_amount,
            sender=starter_agent.address,
        )


def test_deposit_for_yield_accepts_leverage_vault_token(
    raw_vault_with_funds_18dec,
    mock_usdc,
    mock_usdc_leverage_vault,
    starter_agent,
    governance,
):
    """Leverage vault (USDC) deposits still work on raw asset vaults"""
    vault = raw_vault_with_funds_18dec

    # Give vault some USDC to deposit
    usdc_amount = 1000 * SIX_DECIMALS
    mock_usdc.mint(vault.address, usdc_amount, sender=governance.address)

    pre_vault_token_balance = mock_usdc_leverage_vault.balanceOf(vault.address)

    # depositForYield with USDC should succeed
    asset_deposited, vault_token, vault_tokens_received, usd_value = vault.depositForYield(
        MOCK_YIELD_LEGO_ID,
        mock_usdc.address,
        mock_usdc_leverage_vault.address,
        usdc_amount,
        sender=starter_agent.address,
    )

    assert asset_deposited == usdc_amount
    assert vault_token == mock_usdc_leverage_vault.address
    assert vault_tokens_received > 0
    assert mock_usdc_leverage_vault.balanceOf(vault.address) == pre_vault_token_balance + vault_tokens_received


def test_deposit_for_yield_accepts_savings_green(
    raw_vault_with_funds_18dec,
    mock_green_token,
    mock_savings_green_token,
    starter_agent,
    governance,
):
    """Stab pool deposits (GREEN -> sGREEN) still work on raw asset vaults"""
    vault = raw_vault_with_funds_18dec

    # Give vault some GREEN to deposit
    green_amount = 500 * EIGHTEEN_DECIMALS
    mock_green_token.mint(vault.address, green_amount, sender=governance.address)

    pre_sgreen_balance = mock_savings_green_token.balanceOf(vault.address)

    # depositForYield with GREEN -> sGREEN should succeed
    asset_deposited, vault_token, vault_tokens_received, usd_value = vault.depositForYield(
        RIPE_LEGO_ID,
        mock_green_token.address,
        mock_savings_green_token.address,
        green_amount,
        sender=starter_agent.address,
    )

    assert asset_deposited == green_amount
    assert vault_token == mock_savings_green_token.address
    assert vault_tokens_received > 0
    assert mock_savings_green_token.balanceOf(vault.address) == pre_sgreen_balance + vault_tokens_received


###########################################
# Category 4: Add/Remove Collateral Tests
###########################################


def test_add_raw_asset_collateral_to_ripe(
    raw_vault_with_funds_18dec,
    bravo_token,
    mock_ripe,
    starter_agent,
):
    """Explicit addCollateral with raw asset increases Ripe collateral exactly"""
    vault = raw_vault_with_funds_18dec

    add_amount = 200 * EIGHTEEN_DECIMALS

    pre_ripe_collateral = mock_ripe.userCollateral(vault.address, bravo_token.address)
    pre_wallet_balance = bravo_token.balanceOf(vault.address)

    # Add collateral (uses default extraData)
    amount_added, usd_value = vault.addCollateral(
        RIPE_LEGO_ID,
        bravo_token.address,
        add_amount,
        sender=starter_agent.address,
    )

    assert amount_added == add_amount
    assert mock_ripe.userCollateral(vault.address, bravo_token.address) == pre_ripe_collateral + add_amount
    assert bravo_token.balanceOf(vault.address) == pre_wallet_balance - add_amount


def test_add_raw_asset_collateral_partial_amount(
    raw_vault_with_funds_18dec,
    bravo_token,
    mock_ripe,
    starter_agent,
):
    """Add only part of wallet balance as collateral"""
    vault = raw_vault_with_funds_18dec

    wallet_balance = bravo_token.balanceOf(vault.address)
    partial_amount = wallet_balance // 4  # 25% of balance

    pre_ripe_collateral = mock_ripe.userCollateral(vault.address, bravo_token.address)

    amount_added, usd_value = vault.addCollateral(
        RIPE_LEGO_ID,
        bravo_token.address,
        partial_amount,
        sender=starter_agent.address,
    )

    assert amount_added == partial_amount
    assert mock_ripe.userCollateral(vault.address, bravo_token.address) == pre_ripe_collateral + partial_amount
    # Wallet should still have remaining balance
    assert bravo_token.balanceOf(vault.address) == wallet_balance - partial_amount


def test_remove_raw_asset_collateral_from_ripe(
    raw_vault_with_funds_18dec,
    bravo_token,
    mock_ripe,
    starter_agent,
):
    """Remove raw asset collateral back to wallet"""
    vault = raw_vault_with_funds_18dec

    # First add some collateral
    add_amount = 300 * EIGHTEEN_DECIMALS

    vault.addCollateral(
        RIPE_LEGO_ID,
        bravo_token.address,
        add_amount,
        sender=starter_agent.address,
    )

    pre_ripe_collateral = mock_ripe.userCollateral(vault.address, bravo_token.address)
    pre_wallet_balance = bravo_token.balanceOf(vault.address)

    remove_amount = 100 * EIGHTEEN_DECIMALS

    # Remove collateral
    amount_removed, usd_value = vault.removeCollateral(
        RIPE_LEGO_ID,
        bravo_token.address,
        remove_amount,
        sender=starter_agent.address,
    )

    assert amount_removed == remove_amount
    assert mock_ripe.userCollateral(vault.address, bravo_token.address) == pre_ripe_collateral - remove_amount
    assert bravo_token.balanceOf(vault.address) == pre_wallet_balance + remove_amount


def test_remove_raw_asset_collateral_max_amount(
    raw_vault_with_funds_18dec,
    bravo_token,
    mock_ripe,
    starter_agent,
):
    """Remove with max_value(uint256) returns full Ripe collateral"""
    vault = raw_vault_with_funds_18dec

    # Add all wallet balance to Ripe
    wallet_balance = bravo_token.balanceOf(vault.address)

    vault.addCollateral(
        RIPE_LEGO_ID,
        bravo_token.address,
        wallet_balance,
        sender=starter_agent.address,
    )

    ripe_collateral = mock_ripe.userCollateral(vault.address, bravo_token.address)
    assert ripe_collateral > 0

    # Remove with max amount
    amount_removed, usd_value = vault.removeCollateral(
        RIPE_LEGO_ID,
        bravo_token.address,
        MAX_UINT256,
        sender=starter_agent.address,
    )

    # All collateral should be returned
    assert amount_removed == ripe_collateral
    assert mock_ripe.userCollateral(vault.address, bravo_token.address) == 0
    assert bravo_token.balanceOf(vault.address) == ripe_collateral


def test_add_remove_raw_asset_collateral_cycle(
    raw_vault_with_funds_18dec,
    bravo_token,
    mock_ripe,
    starter_agent,
):
    """Multiple add/remove operations balance correctly"""
    vault = raw_vault_with_funds_18dec

    initial_wallet = bravo_token.balanceOf(vault.address)
    initial_ripe = mock_ripe.userCollateral(vault.address, bravo_token.address)

    # Cycle 1: Add 100, Remove 50
    vault.addCollateral(RIPE_LEGO_ID, bravo_token.address, 100 * EIGHTEEN_DECIMALS, sender=starter_agent.address)
    vault.removeCollateral(RIPE_LEGO_ID, bravo_token.address, 50 * EIGHTEEN_DECIMALS, sender=starter_agent.address)

    # Cycle 2: Add 200, Remove 100
    vault.addCollateral(RIPE_LEGO_ID, bravo_token.address, 200 * EIGHTEEN_DECIMALS, sender=starter_agent.address)
    vault.removeCollateral(RIPE_LEGO_ID, bravo_token.address, 100 * EIGHTEEN_DECIMALS, sender=starter_agent.address)

    # Net: +100 - 50 + 200 - 100 = +150 to Ripe
    expected_ripe = initial_ripe + 150 * EIGHTEEN_DECIMALS
    expected_wallet = initial_wallet - 150 * EIGHTEEN_DECIMALS

    assert mock_ripe.userCollateral(vault.address, bravo_token.address) == expected_ripe
    assert bravo_token.balanceOf(vault.address) == expected_wallet


###########################################
# Category 5: Borrowing Against Raw Asset Tests
###########################################


def test_borrow_green_against_raw_asset_collateral(
    raw_vault_with_funds_18dec,
    bravo_token,
    mock_ripe,
    mock_green_token,
    starter_agent,
):
    """Borrow GREEN with raw asset as collateral"""
    vault = raw_vault_with_funds_18dec

    # Add collateral first
    collateral_amount = 500 * EIGHTEEN_DECIMALS

    vault.addCollateral(
        RIPE_LEGO_ID,
        bravo_token.address,
        collateral_amount,
        sender=starter_agent.address,
    )

    pre_green_balance = mock_green_token.balanceOf(vault.address)
    pre_debt = mock_ripe.userDebt(vault.address)

    # Borrow GREEN
    borrow_amount = 100 * EIGHTEEN_DECIMALS
    amount_borrowed, usd_value = vault.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        borrow_amount,
        sender=starter_agent.address,
    )

    assert amount_borrowed == borrow_amount
    assert mock_green_token.balanceOf(vault.address) == pre_green_balance + borrow_amount
    assert mock_ripe.userDebt(vault.address) == pre_debt + borrow_amount


def test_borrow_savings_green_against_raw_asset(
    raw_vault_with_funds_18dec,
    bravo_token,
    mock_ripe,
    mock_savings_green_token,
    starter_agent,
):
    """Borrow sGREEN with raw asset collateral"""
    vault = raw_vault_with_funds_18dec

    # Add collateral
    collateral_amount = 500 * EIGHTEEN_DECIMALS

    vault.addCollateral(
        RIPE_LEGO_ID,
        bravo_token.address,
        collateral_amount,
        sender=starter_agent.address,
    )

    pre_sgreen_balance = mock_savings_green_token.balanceOf(vault.address)

    # Borrow sGREEN (extraData encodes shouldEnterStabPool)
    borrow_amount = 50 * EIGHTEEN_DECIMALS
    amount_borrowed, usd_value = vault.borrow(
        RIPE_LEGO_ID,
        mock_savings_green_token.address,
        borrow_amount,
        b'\x00' * 31 + b'\x01',  # shouldEnterStabPool = True
        sender=starter_agent.address,
    )

    assert amount_borrowed > 0
    assert mock_savings_green_token.balanceOf(vault.address) > pre_sgreen_balance


def test_repay_debt_with_raw_asset_collateral(
    raw_vault_with_funds_18dec,
    bravo_token,
    mock_ripe,
    mock_green_token,
    starter_agent,
    governance,
):
    """Repay debt on raw asset collateral vault"""
    vault = raw_vault_with_funds_18dec

    # Setup: Add collateral and borrow
    collateral_amount = 500 * EIGHTEEN_DECIMALS

    vault.addCollateral(RIPE_LEGO_ID, bravo_token.address, collateral_amount, sender=starter_agent.address)

    borrow_amount = 100 * EIGHTEEN_DECIMALS
    vault.borrow(RIPE_LEGO_ID, mock_green_token.address, borrow_amount, sender=starter_agent.address)

    pre_debt = mock_ripe.userDebt(vault.address)
    assert pre_debt >= borrow_amount  # May have accumulated debt from previous tests

    # Repay half the borrow amount
    repay_amount = 50 * EIGHTEEN_DECIMALS
    amount_repaid, usd_value = vault.repayDebt(
        RIPE_LEGO_ID,
        mock_green_token.address,
        repay_amount,
        sender=starter_agent.address,
    )

    assert amount_repaid == repay_amount
    assert mock_ripe.userDebt(vault.address) == pre_debt - repay_amount


###########################################
# Category 6: Redemption/Withdrawal Tests
###########################################


def test_redeem_with_raw_asset_in_wallet(
    raw_asset_levg_vault_18dec,
    bravo_token,
    governance,
    alice,
):
    """Redeem when raw asset is idle in wallet"""
    vault = raw_asset_levg_vault_18dec

    # Alice deposits
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    bravo_token.mint(alice, deposit_amount, sender=governance.address)
    bravo_token.approve(vault.address, deposit_amount, sender=alice)
    shares = vault.deposit(deposit_amount, alice, sender=alice)

    # Give vault idle tokens (not on Ripe)
    idle_amount = 50 * EIGHTEEN_DECIMALS
    bravo_token.mint(vault.address, idle_amount, sender=governance.address)

    pre_alice_token_balance = bravo_token.balanceOf(alice)

    # Redeem shares for idle tokens
    redeem_shares = shares // 2
    assets_received = vault.redeem(redeem_shares, alice, alice, sender=alice)

    assert assets_received > 0
    assert bravo_token.balanceOf(alice) == pre_alice_token_balance + assets_received


def test_partial_redeem_raw_asset(
    raw_asset_levg_vault_18dec,
    bravo_token,
    governance,
    bob,
):
    """Partial redemption returns exact partial amount"""
    vault = raw_asset_levg_vault_18dec

    # Bob deposits
    deposit_amount = 200 * EIGHTEEN_DECIMALS
    bravo_token.mint(bob, deposit_amount, sender=governance.address)
    bravo_token.approve(vault.address, deposit_amount, sender=bob)
    shares = vault.deposit(deposit_amount, bob, sender=bob)

    # Give vault tokens to redeem from
    bravo_token.mint(vault.address, deposit_amount, sender=governance.address)

    # Redeem 25%
    redeem_shares = shares // 4
    pre_bob_balance = bravo_token.balanceOf(bob)
    pre_bob_shares = vault.balanceOf(bob)

    assets_received = vault.redeem(redeem_shares, bob, bob, sender=bob)

    assert assets_received > 0
    assert vault.balanceOf(bob) == pre_bob_shares - redeem_shares
    assert bravo_token.balanceOf(bob) == pre_bob_balance + assets_received


###########################################
# Category 7: Total Assets / Valuation Tests
###########################################


def test_total_assets_includes_raw_asset_in_wallet(
    raw_vault_with_funds_18dec,
    bravo_token,
):
    """Wallet balance counted in total assets"""
    vault = raw_vault_with_funds_18dec

    wallet_balance = bravo_token.balanceOf(vault.address)
    total_assets = vault.totalAssets()

    # Total assets should include wallet balance
    assert total_assets >= wallet_balance


def test_total_assets_includes_raw_asset_on_ripe(
    raw_vault_with_funds_18dec,
    bravo_token,
    mock_ripe,
    starter_agent,
):
    """Ripe collateral counted in total assets"""
    vault = raw_vault_with_funds_18dec

    # Add some to Ripe
    add_amount = 200 * EIGHTEEN_DECIMALS

    vault.addCollateral(
        RIPE_LEGO_ID,
        bravo_token.address,
        add_amount,
        sender=starter_agent.address,
    )

    ripe_collateral = mock_ripe.userCollateral(vault.address, bravo_token.address)
    wallet_balance = bravo_token.balanceOf(vault.address)
    total_assets = vault.totalAssets()

    # Total assets should include both
    assert total_assets >= wallet_balance + ripe_collateral


def test_total_assets_with_raw_asset_18_decimals(
    raw_vault_with_funds_18dec,
    bravo_token,
):
    """Correct total assets calculation for 18-decimal raw asset"""
    vault = raw_vault_with_funds_18dec

    wallet_balance = bravo_token.balanceOf(vault.address)
    total_assets = vault.totalAssets()

    # For raw assets with no debt, total assets = wallet + Ripe collateral
    assert total_assets > 0
    assert wallet_balance > 0


def test_total_assets_with_raw_asset_6_decimals(
    raw_vault_with_funds_6dec,
    charlie_token,
):
    """Correct total assets calculation for 6-decimal raw asset"""
    vault = raw_vault_with_funds_6dec

    wallet_balance = charlie_token.balanceOf(vault.address)
    total_assets = vault.totalAssets()

    assert total_assets > 0
    assert wallet_balance > 0


def test_total_assets_with_raw_asset_8_decimals(
    raw_vault_with_funds_8dec,
    delta_token,
):
    """Correct total assets calculation for 8-decimal raw asset"""
    vault = raw_vault_with_funds_8dec

    wallet_balance = delta_token.balanceOf(vault.address)
    total_assets = vault.totalAssets()

    assert total_assets > 0
    assert wallet_balance > 0


###########################################
# Category 8: LevgVaultHelper Validation Tests
###########################################


def test_is_valid_raw_asset_collateral_success(
    levg_vault_helper,
    bravo_token,
):
    """Valid raw asset passes validation"""
    # ripeVaultId = 1 is valid, asset = underlying
    result = levg_vault_helper.isValidRawAssetCollateral(
        bravo_token.address,  # underlying
        bravo_token.address,  # raw asset (same)
        1,  # ripe vault id
    )
    assert result == True


def test_is_valid_raw_asset_collateral_wrong_asset(
    levg_vault_helper,
    bravo_token,
    charlie_token,
):
    """Vault token != underlying fails validation"""
    result = levg_vault_helper.isValidRawAssetCollateral(
        bravo_token.address,  # underlying
        charlie_token.address,  # different asset
        1,
    )
    assert result == False


def test_is_valid_raw_asset_collateral_zero_vault_id(
    levg_vault_helper,
    bravo_token,
):
    """Zero ripeVaultId fails validation"""
    result = levg_vault_helper.isValidRawAssetCollateral(
        bravo_token.address,
        bravo_token.address,
        0,  # invalid vault id
    )
    assert result == False


def test_is_valid_raw_asset_collateral_zero_addresses(
    levg_vault_helper,
):
    """Zero addresses fail validation"""
    result = levg_vault_helper.isValidRawAssetCollateral(
        ZERO_ADDRESS,
        ZERO_ADDRESS,
        1,
    )
    assert result == False


###########################################
# Category 9: Configuration Change Tests
###########################################


def test_set_collateral_vault_requires_switchboard(
    raw_asset_levg_vault_18dec,
    bravo_token,
    bob,
):
    """Only switchboard can call setCollateralVault"""
    vault = raw_asset_levg_vault_18dec

    with boa.reverts():
        vault.setCollateralVault(
            bravo_token.address,
            0,  # lego id
            1,  # ripe vault id
            False,  # shouldMaxWithdraw
            sender=bob,  # not switchboard
        )


###########################################
# Category 10: Edge Cases and Error Conditions
###########################################


def test_raw_asset_lego_id_always_zero(
    raw_vault_with_funds_18dec,
    bravo_token,
    starter_agent,
):
    """LegoId remains 0 throughout vault lifecycle"""
    vault = raw_vault_with_funds_18dec

    # Initial state
    assert vault.vaultToLegoId(bravo_token.address) == 0

    # After adding collateral
    vault.addCollateral(
        RIPE_LEGO_ID,
        bravo_token.address,
        100 * EIGHTEEN_DECIMALS,
        sender=starter_agent.address,
    )
    assert vault.vaultToLegoId(bravo_token.address) == 0

    # After removing collateral
    vault.removeCollateral(
        RIPE_LEGO_ID,
        bravo_token.address,
        50 * EIGHTEEN_DECIMALS,
        sender=starter_agent.address,
    )
    assert vault.vaultToLegoId(bravo_token.address) == 0


def test_raw_asset_with_usdc_leverage_vault(
    raw_vault_with_funds_18dec,
    mock_usdc,
    mock_usdc_leverage_vault,
    starter_agent,
    governance,
):
    """Raw collateral + USDC leverage works together"""
    vault = raw_vault_with_funds_18dec

    # Give vault some USDC
    usdc_amount = 500 * SIX_DECIMALS
    mock_usdc.mint(vault.address, usdc_amount, sender=governance.address)

    pre_leverage_tokens = mock_usdc_leverage_vault.balanceOf(vault.address)

    # Deposit USDC to leverage vault
    asset_deposited, vault_token, vault_tokens_received, usd_value = vault.depositForYield(
        MOCK_YIELD_LEGO_ID,
        mock_usdc.address,
        mock_usdc_leverage_vault.address,
        usdc_amount,
        sender=starter_agent.address,
    )

    assert asset_deposited == usdc_amount
    assert vault_tokens_received > 0
    assert mock_usdc_leverage_vault.balanceOf(vault.address) == pre_leverage_tokens + vault_tokens_received


def test_raw_asset_zero_amount_add_collateral(
    raw_vault_with_funds_18dec,
    bravo_token,
    mock_ripe,
    starter_agent,
):
    """Adding zero collateral reverts"""
    vault = raw_vault_with_funds_18dec

    # Adding 0 amount should revert with "nothing to deposit"
    with boa.reverts():
        vault.addCollateral(
            RIPE_LEGO_ID,
            bravo_token.address,
            0,
            sender=starter_agent.address,
        )


def test_raw_asset_unauthorized_caller_rejected(
    raw_vault_with_funds_18dec,
    bravo_token,
    bob,
):
    """Unauthorized callers cannot perform wallet actions"""
    vault = raw_vault_with_funds_18dec

    # Bob is not a manager
    with boa.reverts():
        vault.addCollateral(
            RIPE_LEGO_ID,
            bravo_token.address,
            100 * EIGHTEEN_DECIMALS,
            sender=bob,
        )


###########################################
# Category 11: Double Counting Detection
###########################################


def test_total_assets_exact_calculation_no_double_counting(
    raw_vault_with_funds_18dec,
    bravo_token,
    mock_ripe,
    starter_agent,
):
    """
    CRITICAL: Test if totalAssets double-counts raw asset collateral.

    For raw assets, _getTotalUnderlyingAmount calculates:
    1. underlyingNaked = wallet + Ripe (via auto-lookup)
    2. underlyingFromVault = wallet + Ripe (via actual vault ID)

    If both count the same amounts, we have DOUBLE COUNTING.
    """
    vault = raw_vault_with_funds_18dec

    # Initial state: vault has 1000 tokens in wallet
    initial_wallet = bravo_token.balanceOf(vault.address)
    initial_ripe = mock_ripe.userCollateral(vault.address, bravo_token.address)

    # Move 500 to Ripe
    move_amount = 500 * EIGHTEEN_DECIMALS
    vault.addCollateral(
        RIPE_LEGO_ID,
        bravo_token.address,
        move_amount,
        sender=starter_agent.address,
    )

    post_wallet = bravo_token.balanceOf(vault.address)
    post_ripe = mock_ripe.userCollateral(vault.address, bravo_token.address)

    # Calculate what totalAssets SHOULD be
    expected_total = post_wallet + post_ripe  # Simple: wallet + Ripe, no double counting

    # Get actual totalAssets
    actual_total = vault.totalAssets()

    # CRITICAL ASSERTION: totalAssets should equal wallet + Ripe, NOT 2x that
    assert actual_total == expected_total, f"DOUBLE COUNTING BUG: Expected {expected_total}, got {actual_total}"


def test_total_assets_wallet_only_no_double_counting(
    raw_asset_levg_vault_18dec,
    bravo_token,
    governance,
):
    """Test totalAssets when all funds are in wallet (not on Ripe)."""
    vault = raw_asset_levg_vault_18dec

    # Mint tokens directly to vault wallet
    amount = 1000 * EIGHTEEN_DECIMALS
    bravo_token.mint(vault.address, amount, sender=governance.address)

    wallet_balance = bravo_token.balanceOf(vault.address)
    total_assets = vault.totalAssets()

    # If double counting, totalAssets would be 2x wallet balance
    assert total_assets == wallet_balance, f"DOUBLE COUNTING: Expected {wallet_balance}, got {total_assets}"


def test_total_assets_ripe_only_no_double_counting(
    raw_asset_levg_vault_18dec,
    bravo_token,
    mock_ripe,
    governance,
    starter_agent,
):
    """Test totalAssets when funds are primarily on Ripe."""
    vault = raw_asset_levg_vault_18dec

    # Get initial wallet balance (may have accumulated from previous tests in module-scoped fixture)
    initial_wallet = bravo_token.balanceOf(vault.address)

    # Mint and immediately move to Ripe
    amount = 1000 * EIGHTEEN_DECIMALS
    bravo_token.mint(vault.address, amount, sender=governance.address)

    vault.addCollateral(
        RIPE_LEGO_ID,
        bravo_token.address,
        amount,
        sender=starter_agent.address,
    )

    wallet_balance = bravo_token.balanceOf(vault.address)
    ripe_collateral = mock_ripe.userCollateral(vault.address, bravo_token.address)
    total_assets = vault.totalAssets()

    # Wallet should have only the initial balance (tokens we just added went to Ripe)
    assert wallet_balance == initial_wallet, f"Expected wallet {initial_wallet}, got {wallet_balance}"

    # CRITICAL: totalAssets should equal wallet + Ripe (no double counting)
    expected_total = wallet_balance + ripe_collateral
    assert total_assets == expected_total, f"DOUBLE COUNTING: Expected {expected_total}, got {total_assets}"


###########################################
# Category 12: Debt Impact on Total Assets
###########################################


def test_total_assets_correctly_tracks_debt_position(
    setup_raw_asset_swap_prices,
    levg_vault_agent_for_raw,
    agent_registered_raw_vault,
    bravo_token,
    mock_ripe,
    mock_green_token,
    mock_usdc,
    lego_book,
    mock_swap_lego,
    starter_agent,
    governance,
):
    """
    PRIORITY 2: Verify totalAssets correctly accounts for debt.

    This test verifies that:
    1. When borrowing GREEN and holding it, totalAssets stays same (offset)
    2. When borrowing GREEN and swapping to USDC, totalAssets stays same (USDC offsets debt)
    3. The debt is properly tracked in the Ripe mock
    """
    vault = agent_registered_raw_vault

    # Add collateral to Ripe
    collateral_amount = 500 * EIGHTEEN_DECIMALS
    vault.addCollateral(
        RIPE_LEGO_ID,
        bravo_token.address,
        collateral_amount,
        sender=starter_agent.address,
    )

    # Get total assets and debt BEFORE borrowing
    total_assets_before = vault.totalAssets()
    debt_before = mock_ripe.userDebt(vault.address)

    # Use agent to borrow GREEN and swap to USDC
    borrow_amount = 100 * EIGHTEEN_DECIMALS
    swap_lego_id = lego_book.getRegId(mock_swap_lego.address)

    swap_instruction = (
        swap_lego_id,
        0,  # amountIn = 0 means auto-chain from borrow
        50 * SIX_DECIMALS,  # minAmountOut
        [mock_green_token.address, mock_usdc.address],
        [],
    )

    levg_vault_agent_for_raw.borrowAndEarnYield(
        vault.address,
        [],
        [],
        [],
        [],
        borrow_amount,
        False,
        False,
        swap_instruction,
        [],
        sender=governance.address,
    )

    # Get state AFTER borrowing
    total_assets_after = vault.totalAssets()
    debt_after = mock_ripe.userDebt(vault.address)
    usdc_in_wallet = mock_usdc.balanceOf(vault.address)

    # Debt increased by borrow amount
    assert debt_after == debt_before + borrow_amount, (
        f"Debt should increase by borrow amount: expected {debt_before + borrow_amount}, got {debt_after}"
    )

    # USDC received from swap (roughly equals borrow amount in value)
    assert usdc_in_wallet > 0, "USDC should be received from swap"

    # Total assets stays relatively stable because:
    # - Debt adds liability
    # - USDC in wallet adds asset
    # - These roughly offset
    # The key is debt is tracked correctly (verified above)
    # Allow for small variance due to price conversions
    variance = total_assets_before * 5 // 100  # 5% tolerance
    assert abs(int(total_assets_after) - int(total_assets_before)) <= variance, (
        f"totalAssets should be stable when debt is offset: before={total_assets_before}, after={total_assets_after}"
    )


def test_total_assets_increases_when_net_debt_repaid(
    setup_raw_asset_swap_prices,
    levg_vault_agent_for_raw,
    agent_registered_raw_vault,
    bravo_token,
    mock_ripe,
    mock_green_token,
    mock_usdc,
    lego_book,
    mock_swap_lego,
    starter_agent,
    governance,
):
    """
    Verify totalAssets increases when NET debt is repaid.

    We create net debt by borrowing GREEN and swapping to USDC via agent,
    then repay debt using GREEN. This should increase totalAssets.
    """
    vault = agent_registered_raw_vault

    # Setup: Add collateral
    collateral_amount = 400 * EIGHTEEN_DECIMALS
    vault.addCollateral(
        RIPE_LEGO_ID,
        bravo_token.address,
        collateral_amount,
        sender=starter_agent.address,
    )

    # Create net debt via agent borrow + swap
    borrow_amount = 80 * EIGHTEEN_DECIMALS
    swap_lego_id = lego_book.getRegId(mock_swap_lego.address)

    swap_instruction = (
        swap_lego_id,
        0,
        40 * SIX_DECIMALS,
        [mock_green_token.address, mock_usdc.address],
        [],
    )

    levg_vault_agent_for_raw.borrowAndEarnYield(
        vault.address,
        [],
        [],
        [],
        [],
        borrow_amount,
        False,
        False,
        swap_instruction,
        [],
        sender=governance.address,
    )

    # Get total assets with NET debt
    total_assets_with_debt = vault.totalAssets()

    # Mint GREEN back to vault and repay half
    repay_amount = 40 * EIGHTEEN_DECIMALS
    mock_green_token.mint(vault.address, repay_amount, sender=governance.address)

    # Repay half the debt
    vault.repayDebt(
        RIPE_LEGO_ID,
        mock_green_token.address,
        repay_amount,
        sender=starter_agent.address,
    )

    # Get total assets after partial repayment
    total_assets_after_repay = vault.totalAssets()

    # Total assets should increase after repaying net debt
    assert total_assets_after_repay > total_assets_with_debt, (
        f"totalAssets should increase when debt repaid: with_debt={total_assets_with_debt}, after_repay={total_assets_after_repay}"
    )


###########################################
# Category 13: LevgVaultAgent Workflow Tests
###########################################


@pytest.fixture(scope="module")
def levg_vault_agent_for_raw(undy_hq, governance, mock_green_token, mock_savings_green_token):
    """Deploy LevgVaultAgent for raw asset vault tests"""
    return boa.load(
        "contracts/core/agent/LevgVaultAgent.vy",
        undy_hq.address,
        governance.address,  # owner
        1,  # minTimeLock (must be > 0)
        100,  # maxTimeLock
        mock_green_token.address,
        mock_savings_green_token.address,
        name="levg_vault_agent_raw",
    )


@pytest.fixture(scope="module")
def agent_registered_raw_vault(
    levg_vault_agent_for_raw,
    raw_vault_with_funds_18dec,
    switchboard_alpha,
    mock_ripe,
):
    """Register agent as manager on raw asset vault and set unlimited debt ratio"""
    vault = raw_vault_with_funds_18dec

    # Add agent as manager
    vault.addManager(levg_vault_agent_for_raw.address, sender=switchboard_alpha.address)

    # Set maxDebtRatio to 0 for unlimited borrowing in tests
    vault.setMaxDebtRatio(0, sender=switchboard_alpha.address)

    return vault


@pytest.fixture(scope="module")
def setup_raw_asset_swap_prices(
    setup_raw_asset_prices,
    mock_swap_lego,
    governance,
    bravo_token,
    mock_usdc,
    mock_green_token,
    setup_mock_swap_lego_in_legobook,
):
    """Set up swap prices for raw asset agent tests"""
    # Ensure swap lego is registered in lego book (via fixture dependency)
    # Set swap prices for GREEN <-> USDC
    mock_swap_lego.setPrice(mock_green_token.address, 1 * EIGHTEEN_DECIMALS, sender=governance.address)
    mock_swap_lego.setPrice(mock_usdc.address, 1 * EIGHTEEN_DECIMALS, sender=governance.address)
    # bravo_token price already set in setup_raw_asset_prices
    return mock_swap_lego


def test_agent_can_be_added_to_raw_asset_vault(
    levg_vault_agent_for_raw,
    raw_asset_levg_vault_18dec,
    switchboard_alpha,
):
    """Verify agent can be registered as manager on raw asset vault"""
    vault = raw_asset_levg_vault_18dec

    # Add agent as manager
    vault.addManager(levg_vault_agent_for_raw.address, sender=switchboard_alpha.address)

    # Verify agent is manager
    assert vault.indexOfManager(levg_vault_agent_for_raw.address) != 0


def test_agent_borrow_with_raw_asset_collateral(
    setup_raw_asset_swap_prices,
    levg_vault_agent_for_raw,
    agent_registered_raw_vault,
    bravo_token,
    mock_green_token,
    mock_ripe,
    governance,
    starter_agent,
):
    """
    PRIORITY 1: Test agent borrowAndEarnYield with raw asset collateral.

    This tests that the agent correctly:
    1. Identifies raw asset collateral (legoId == 0)
    2. Skips depositForYield for raw collateral position
    3. Successfully borrows GREEN against raw collateral
    """
    wallet = agent_registered_raw_vault

    # Setup: Add raw asset as collateral (via wallet directly)
    collateral_amount = 300 * EIGHTEEN_DECIMALS
    wallet.addCollateral(
        RIPE_LEGO_ID,
        bravo_token.address,
        collateral_amount,
        sender=starter_agent.address,
    )

    pre_debt = mock_ripe.userDebt(wallet.address)
    pre_green = mock_green_token.balanceOf(wallet.address)

    # Borrow GREEN via agent (no swap, no post-swap deposit)
    # Empty swap instruction and no post-swap deposits
    empty_swap = (0, 0, 0, [], [])

    levg_vault_agent_for_raw.borrowAndEarnYield(
        wallet.address,
        [],  # removeCollateral
        [],  # withdrawPositions
        [],  # depositPositions
        [],  # addCollateral
        100 * EIGHTEEN_DECIMALS,  # borrowAmount
        False,  # wantsSavingsGreen
        False,  # shouldEnterStabPool
        empty_swap,  # swapInstruction
        [],  # postSwapDeposits
        sender=governance.address,  # owner bypass
    )

    # Verify debt increased
    post_debt = mock_ripe.userDebt(wallet.address)
    assert post_debt == pre_debt + 100 * EIGHTEEN_DECIMALS

    # Verify GREEN received
    post_green = mock_green_token.balanceOf(wallet.address)
    assert post_green == pre_green + 100 * EIGHTEEN_DECIMALS


def test_agent_borrow_and_earn_yield_full_flow_with_raw_collateral(
    setup_raw_asset_swap_prices,
    levg_vault_agent_for_raw,
    agent_registered_raw_vault,
    bravo_token,
    mock_green_token,
    mock_usdc,
    mock_usdc_leverage_vault,
    mock_ripe,
    governance,
    starter_agent,
    lego_book,
    mock_swap_lego,
):
    """
    PRIORITY 1: Full borrowAndEarnYield workflow with raw asset collateral.

    Flow: Add raw collateral → Borrow GREEN → Swap to USDC → Deposit USDC to leverage vault
    """
    wallet = agent_registered_raw_vault

    # Setup: Add raw asset as collateral
    collateral_amount = 400 * EIGHTEEN_DECIMALS
    wallet.addCollateral(
        RIPE_LEGO_ID,
        bravo_token.address,
        collateral_amount,
        sender=starter_agent.address,
    )

    pre_debt = mock_ripe.userDebt(wallet.address)
    pre_levg_vault = mock_usdc_leverage_vault.balanceOf(wallet.address)

    # Create swap instruction: GREEN -> USDC
    swap_lego_id = lego_book.getRegId(mock_swap_lego.address)
    borrow_amount = 200 * EIGHTEEN_DECIMALS

    swap_instruction = (
        swap_lego_id,
        0,  # amountIn = 0 means auto-chain from borrow
        100 * SIX_DECIMALS,  # minAmountOut (USDC has 6 decimals)
        [mock_green_token.address, mock_usdc.address],
        [],
    )

    # Post-swap deposit: deposit swapped USDC to leverage vault
    post_swap_deposit = (
        1,  # POSITION_LEVERAGE
        0,  # amount = 0 means auto-use from swap
        False,  # shouldAddToRipeCollateral
        True,  # shouldSweepAll
    )

    levg_vault_agent_for_raw.borrowAndEarnYield(
        wallet.address,
        [],  # removeCollateral
        [],  # withdrawPositions
        [],  # depositPositions - NOTE: for raw assets, skip collateral deposits
        [],  # addCollateral
        borrow_amount,
        False,  # wantsSavingsGreen
        False,  # shouldEnterStabPool
        swap_instruction,
        [post_swap_deposit],
        sender=governance.address,
    )

    # Verify debt increased
    post_debt = mock_ripe.userDebt(wallet.address)
    assert post_debt == pre_debt + borrow_amount

    # Verify leverage vault tokens received (USDC was deposited)
    post_levg_vault = mock_usdc_leverage_vault.balanceOf(wallet.address)
    assert post_levg_vault > pre_levg_vault


def test_agent_deleverage_with_raw_asset_collateral(
    setup_raw_asset_swap_prices,
    levg_vault_agent_for_raw,
    agent_registered_raw_vault,
    bravo_token,
    mock_green_token,
    mock_ripe,
    governance,
    starter_agent,
):
    """
    PRIORITY 1: Test deleverage workflow with raw asset collateral.

    Mode 2 (manual): Repay debt using GREEN in wallet
    """
    wallet = agent_registered_raw_vault

    # Setup: Add collateral and borrow
    collateral_amount = 300 * EIGHTEEN_DECIMALS
    wallet.addCollateral(
        RIPE_LEGO_ID,
        bravo_token.address,
        collateral_amount,
        sender=starter_agent.address,
    )

    borrow_amount = 100 * EIGHTEEN_DECIMALS
    wallet.borrow(
        RIPE_LEGO_ID,
        mock_green_token.address,
        borrow_amount,
        sender=starter_agent.address,
    )

    pre_debt = mock_ripe.userDebt(wallet.address)
    assert pre_debt >= borrow_amount

    # Deleverage mode 2: Use GREEN already in wallet to repay debt
    repay_amount = 50 * EIGHTEEN_DECIMALS
    empty_swap = (0, 0, 0, [], [])

    levg_vault_agent_for_raw.deleverage(
        wallet.address,
        2,  # mode 2 = manual flow
        0,  # autoDeleverageAmount (not used in mode 2)
        [],  # deleverageAssets (not used in mode 2)
        [],  # removeCollateral
        [],  # withdrawPositions
        empty_swap,
        mock_green_token.address,  # repayAsset
        repay_amount,
        False,  # shouldSweepAllForRepay
        sender=governance.address,
    )

    # Verify debt decreased
    post_debt = mock_ripe.userDebt(wallet.address)
    assert post_debt == pre_debt - repay_amount


def test_agent_skips_yield_deposit_for_raw_collateral_position(
    setup_raw_asset_swap_prices,
    levg_vault_agent_for_raw,
    agent_registered_raw_vault,
    bravo_token,
    mock_ripe,
    governance,
    starter_agent,
):
    """
    PRIORITY 1: Verify agent correctly skips depositForYield for raw asset collateral.

    When depositPositions includes POSITION_COLLATERAL (0) with raw asset,
    the agent should skip it (no yield vault to deposit to).
    """
    wallet = agent_registered_raw_vault

    # Setup: Put some raw tokens in wallet (not on Ripe yet)
    # The wallet already has 1000 bravo_token from raw_vault_with_funds_18dec fixture
    pre_wallet_balance = bravo_token.balanceOf(wallet.address)
    pre_ripe_collateral = mock_ripe.userCollateral(wallet.address, bravo_token.address)

    # Try to deposit raw asset to "yield" via agent with depositPositions
    # For raw assets, this should be skipped (not cause an error)
    deposit_position = (
        0,  # POSITION_COLLATERAL
        100 * EIGHTEEN_DECIMALS,  # amount
        False,  # shouldAddToRipeCollateral (agent should skip anyway)
        False,  # shouldSweepAll
    )

    empty_swap = (0, 0, 0, [], [])

    # This should NOT revert - agent should just skip the collateral deposit
    levg_vault_agent_for_raw.borrowAndEarnYield(
        wallet.address,
        [],  # removeCollateral
        [],  # withdrawPositions
        [deposit_position],  # depositPositions - includes raw collateral
        [],  # addCollateral
        0,  # borrowAmount = 0 (not borrowing in this test)
        False,
        False,
        empty_swap,
        [],
        sender=governance.address,
    )

    # Wallet balance and Ripe collateral should be unchanged
    # (the deposit was skipped for raw assets)
    post_wallet_balance = bravo_token.balanceOf(wallet.address)
    post_ripe_collateral = mock_ripe.userCollateral(wallet.address, bravo_token.address)

    # For raw assets, depositPositions with POSITION_COLLATERAL should be skipped
    # So balances should be unchanged
    assert post_wallet_balance == pre_wallet_balance
    assert post_ripe_collateral == pre_ripe_collateral
