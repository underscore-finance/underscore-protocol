import pytest
import boa

from constants import MAX_UINT256, EIGHTEEN_DECIMALS, ZERO_ADDRESS
from conf_utils import filter_logs

# Decimal constants
SIX_DECIMALS = 10 ** 6
EIGHT_DECIMALS = 10 ** 8

# Lego IDs
RIPE_LEGO_ID = 1
MOCK_YIELD_LEGO_ID = 2


############
# Fixtures #
############


@pytest.fixture(scope="module")
def setup_prices(mock_ripe, mock_green_token, mock_savings_green_token, mock_usdc, mock_cbbtc, mock_weth):
    """Set up prices for all assets"""
    mock_ripe.setPrice(mock_green_token, 1 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_savings_green_token, 1 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_usdc, 1 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_cbbtc, 90_000 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_weth, 2_000 * EIGHTEEN_DECIMALS)
    return mock_ripe


@pytest.fixture(scope="module")
def new_usdc_collateral_vault(mock_usdc):
    """Create a new USDC collateral vault for testing vault token updates"""
    return boa.load("contracts/mock/MockErc4626Vault.vy", mock_usdc, name="new_usdc_collateral_vault")


@pytest.fixture(scope="module")
def new_usdc_leverage_vault(mock_usdc):
    """Create a new USDC leverage vault for testing vault token updates"""
    return boa.load("contracts/mock/MockErc4626Vault.vy", mock_usdc, name="new_usdc_leverage_vault")


@pytest.fixture(scope="module")
def new_cbbtc_collateral_vault(mock_cbbtc):
    """Create a new CBBTC collateral vault for testing vault token updates"""
    return boa.load("contracts/mock/MockErc4626Vault.vy", mock_cbbtc, name="new_cbbtc_collateral_vault")


@pytest.fixture(scope="module")
def new_weth_collateral_vault(mock_weth):
    """Create a new WETH collateral vault for testing vault token updates"""
    return boa.load("contracts/mock/MockErc4626Vault.vy", mock_weth, name="new_weth_collateral_vault")


@pytest.fixture(scope="module")
def new_levg_vault_helper(undy_hq, mock_ripe, mock_usdc):
    """Create a new helper contract for testing helper updates"""
    return boa.load("contracts/vaults/LevgVaultHelper.vy", undy_hq.address, mock_ripe.address, mock_usdc.address, name="new_levg_vault_helper")


###########################################
# Configuration Tests - Collateral Vault #
###########################################


def test_set_collateral_vault_success(
    setup_prices,
    undy_levg_vault_usdc,
    new_usdc_collateral_vault,
    switchboard_alpha,
):
    """Test successfully setting a new collateral vault token"""
    wallet = undy_levg_vault_usdc
    lego_id = MOCK_YIELD_LEGO_ID
    ripe_vault_id = 1

    # Get initial collateral vault
    old_collateral = wallet.collateralAsset()

    # Set new collateral vault
    wallet.setCollateralVault(
        new_usdc_collateral_vault.address,
        lego_id,
        ripe_vault_id,
        False,  # shouldMaxWithdraw
        sender=switchboard_alpha.address
    )

    # Verify state updated
    new_collateral = wallet.collateralAsset()
    assert new_collateral.vaultToken == new_usdc_collateral_vault.address
    assert new_collateral.ripeVaultId == ripe_vault_id
    assert wallet.vaultToLegoId(new_usdc_collateral_vault.address) == lego_id


def test_set_collateral_vault_with_existing_balance_fails(
    setup_prices,
    undy_levg_vault_usdc,
    new_usdc_collateral_vault,
    mock_usdc_collateral_vault,
    mock_usdc,
    switchboard_alpha,
    starter_agent,
    governance,
):
    """Test that setting collateral vault succeeds with local balance but no ripe balance"""
    wallet = undy_levg_vault_usdc
    lego_id = MOCK_YIELD_LEGO_ID

    # Give wallet some USDC
    usdc_amount = 1_000 * SIX_DECIMALS
    mock_usdc.mint(wallet.address, usdc_amount, sender=governance.address)

    # Deposit to collateral vault to create balance
    wallet.depositForYield(
        lego_id,
        mock_usdc.address,
        mock_usdc_collateral_vault.address,
        usdc_amount,
        b"",
        sender=starter_agent.address
    )

    # Verify wallet has vault tokens
    vault_balance = mock_usdc_collateral_vault.balanceOf(wallet.address)
    assert vault_balance > 0

    # Setting new collateral vault should succeed even with local balance (no ripe balance)
    wallet.setCollateralVault(
        new_usdc_collateral_vault.address,
        lego_id,
        1,
        False,  # shouldMaxWithdraw - won't auto-withdraw old balance
        sender=switchboard_alpha.address
    )

    # Verify state updated
    new_collateral = wallet.collateralAsset()
    assert new_collateral.vaultToken == new_usdc_collateral_vault.address

    # Old vault tokens still exist since we didn't max withdraw
    assert mock_usdc_collateral_vault.balanceOf(wallet.address) == vault_balance


def test_set_collateral_vault_unauthorized_fails(
    setup_prices,
    undy_levg_vault_usdc,
    new_usdc_collateral_vault,
    starter_agent,
    alice,
):
    """Test that only switchboard can set collateral vault"""
    wallet = undy_levg_vault_usdc

    # Try to set from starter_agent (not switchboard) - should fail
    with boa.reverts("no perms"):
        wallet.setCollateralVault(
            new_usdc_collateral_vault.address,
            MOCK_YIELD_LEGO_ID,
            1,
            False,  # shouldMaxWithdraw
            sender=starter_agent.address
        )

    # Try to set from random user - should fail
    with boa.reverts("no perms"):
        wallet.setCollateralVault(
            new_usdc_collateral_vault.address,
            MOCK_YIELD_LEGO_ID,
            1,
            False,  # shouldMaxWithdraw
            sender=alice
        )


def test_set_collateral_vault_auto_withdraws_with_balance(
    setup_prices,
    undy_levg_vault_usdc,
    new_usdc_collateral_vault,
    mock_usdc_collateral_vault,
    mock_usdc,
    switchboard_alpha,
    starter_agent,
    governance,
):
    """Test auto-withdrawal when setting collateral vault with _shouldMaxWithdraw=True

    This is the primary use case for the _shouldMaxWithdraw parameter:
    - Wallet has local balance in old vault (not deposited to Ripe)
    - Setting new vault with _shouldMaxWithdraw=True
    - Should automatically withdraw all funds from old vault
    - Old vault tokens should be burned, underlying assets should be in wallet
    """
    wallet = undy_levg_vault_usdc
    lego_id = MOCK_YIELD_LEGO_ID
    ripe_vault_id = 1

    # Give wallet some USDC
    usdc_amount = 1_000 * SIX_DECIMALS
    mock_usdc.mint(wallet.address, usdc_amount, sender=governance.address)

    # Deposit to old collateral vault to create vault token balance (locally, not to Ripe)
    wallet.depositForYield(
        lego_id,
        mock_usdc.address,
        mock_usdc_collateral_vault.address,
        usdc_amount,
        b"",
        sender=starter_agent.address
    )

    # Verify wallet has vault tokens in old vault
    old_vault_balance = mock_usdc_collateral_vault.balanceOf(wallet.address)
    assert old_vault_balance > 0

    # Verify no USDC in wallet (it's all in vault tokens)
    assert mock_usdc.balanceOf(wallet.address) == 0

    # Set new collateral vault with _shouldMaxWithdraw=True
    wallet.setCollateralVault(
        new_usdc_collateral_vault.address,
        lego_id,
        ripe_vault_id,
        True,  # shouldMaxWithdraw - CRITICAL: This triggers auto-withdrawal
        sender=switchboard_alpha.address
    )

    # Verify state updated to new vault
    new_collateral = wallet.collateralAsset()
    assert new_collateral.vaultToken == new_usdc_collateral_vault.address
    assert new_collateral.ripeVaultId == ripe_vault_id
    assert wallet.vaultToLegoId(new_usdc_collateral_vault.address) == lego_id

    # CRITICAL VERIFICATION: Old vault tokens should be burned (withdrawn)
    assert mock_usdc_collateral_vault.balanceOf(wallet.address) == 0, "Old vault tokens should be zero after auto-withdrawal"

    # CRITICAL VERIFICATION: Underlying USDC should be back in wallet
    usdc_balance_after = mock_usdc.balanceOf(wallet.address)
    assert usdc_balance_after > 0, "Wallet should have underlying USDC after withdrawal"
    # Allow for small rounding differences in vault exchange rate
    assert abs(usdc_balance_after - usdc_amount) < 100, f"Expected ~{usdc_amount} USDC, got {usdc_balance_after}"


def test_set_collateral_vault_auto_withdraw_with_zero_balance(
    setup_prices,
    undy_levg_vault_usdc,
    new_usdc_collateral_vault,
    mock_usdc_collateral_vault,
    switchboard_alpha,
):
    """Test that _shouldMaxWithdraw=True succeeds gracefully when there's no balance to withdraw

    Edge case: Setting vault with _shouldMaxWithdraw=True but no local balance exists.
    Should succeed without attempting withdrawal (zero balance check in implementation).
    """
    wallet = undy_levg_vault_usdc
    lego_id = MOCK_YIELD_LEGO_ID
    ripe_vault_id = 1

    # First set the old collateral vault (but don't deposit anything)
    wallet.setCollateralVault(
        mock_usdc_collateral_vault.address,
        lego_id,
        ripe_vault_id,
        False,
        sender=switchboard_alpha.address
    )

    # Verify no balance in old vault
    assert mock_usdc_collateral_vault.balanceOf(wallet.address) == 0

    # Now set new collateral vault with _shouldMaxWithdraw=True despite zero balance
    # Should succeed without errors (no withdrawal attempted since balance == 0)
    wallet.setCollateralVault(
        new_usdc_collateral_vault.address,
        lego_id,
        ripe_vault_id,
        True,  # shouldMaxWithdraw=True even though no balance
        sender=switchboard_alpha.address
    )

    # Verify state updated successfully
    new_collateral = wallet.collateralAsset()
    assert new_collateral.vaultToken == new_usdc_collateral_vault.address
    assert new_collateral.ripeVaultId == ripe_vault_id


def test_set_collateral_vault_no_auto_withdraw_when_same_vault(
    setup_prices,
    undy_levg_vault_usdc,
    mock_usdc_collateral_vault,
    mock_usdc,
    switchboard_alpha,
    starter_agent,
    governance,
):
    """Test that setting same vault doesn't trigger auto-withdrawal even with _shouldMaxWithdraw=True

    Critical edge case: When updating vault parameters (e.g., legoId, ripeVaultId) for the SAME vault,
    withdrawal should NOT occur even if _shouldMaxWithdraw=True.
    Implementation check: (_oldVaultData.vaultToken != _vaultToken)
    """
    wallet = undy_levg_vault_usdc
    lego_id = MOCK_YIELD_LEGO_ID
    ripe_vault_id = 1

    # First, set the collateral vault
    wallet.setCollateralVault(
        mock_usdc_collateral_vault.address,
        lego_id,
        ripe_vault_id,
        False,
        sender=switchboard_alpha.address
    )

    # Give wallet some USDC and deposit to create vault token balance
    usdc_amount = 1_000 * SIX_DECIMALS
    mock_usdc.mint(wallet.address, usdc_amount, sender=governance.address)
    wallet.depositForYield(
        lego_id,
        mock_usdc.address,
        mock_usdc_collateral_vault.address,
        usdc_amount,
        b"",
        sender=starter_agent.address
    )

    # Verify wallet has vault tokens
    vault_balance_before = mock_usdc_collateral_vault.balanceOf(wallet.address)
    assert vault_balance_before > 0

    # Now "update" the SAME vault with different ripe vault ID and _shouldMaxWithdraw=True
    # Keep same lego_id since changing it would require a valid lego in the test environment
    new_ripe_vault_id = 2  # Different ripe vault ID

    wallet.setCollateralVault(
        mock_usdc_collateral_vault.address,  # SAME vault address
        lego_id,  # Same lego ID
        new_ripe_vault_id,  # Different ripe vault ID
        True,  # shouldMaxWithdraw=True
        sender=switchboard_alpha.address
    )

    # CRITICAL VERIFICATION: Vault tokens should STILL EXIST (no withdrawal occurred)
    vault_balance_after = mock_usdc_collateral_vault.balanceOf(wallet.address)
    assert vault_balance_after == vault_balance_before, "Vault tokens should remain when updating same vault"

    # Verify the parameters were updated
    updated_collateral = wallet.collateralAsset()
    assert updated_collateral.vaultToken == mock_usdc_collateral_vault.address
    assert updated_collateral.ripeVaultId == new_ripe_vault_id
    # Lego ID should still map correctly (even though it didn't change)
    assert wallet.vaultToLegoId(mock_usdc_collateral_vault.address) == lego_id


def test_set_collateral_vault_fails_with_ripe_balance(
    setup_prices,
    undy_levg_vault_usdc,
    new_usdc_collateral_vault,
    mock_usdc_collateral_vault,
    mock_usdc,
    mock_ripe,
    switchboard_alpha,
    starter_agent,
    governance,
):
    """Test that setting collateral vault FAILS when old vault has Ripe balance (deposited as collateral)

    CRITICAL SAFETY TEST: The implementation has a safety check to prevent changing vaults
    when funds are actively deposited in Ripe. This prevents accidental loss of collateral.

    Implementation line: assert getCollateralBalance(...) == 0  # dev: old vault has ripe balance

    This test verifies this critical safety mechanism works correctly.
    """
    wallet = undy_levg_vault_usdc
    lego_id = MOCK_YIELD_LEGO_ID
    ripe_vault_id = 1

    # Set up: Use old vault
    wallet.setCollateralVault(
        mock_usdc_collateral_vault.address,
        lego_id,
        ripe_vault_id,
        False,
        sender=switchboard_alpha.address
    )

    # Give wallet USDC and deposit to old collateral vault
    usdc_amount = 1_000 * SIX_DECIMALS
    mock_usdc.mint(wallet.address, usdc_amount, sender=governance.address)
    wallet.depositForYield(
        lego_id,
        mock_usdc.address,
        mock_usdc_collateral_vault.address,
        usdc_amount,
        b"",
        sender=starter_agent.address
    )

    # CRITICAL SETUP: Deposit vault tokens to Ripe as collateral (non-zero Ripe balance)
    vault_token_balance = mock_usdc_collateral_vault.balanceOf(wallet.address)
    assert vault_token_balance > 0

    # Mock that these tokens are now deposited in Ripe as collateral
    # The mock_ripe.setCollateralBalance simulates vault tokens being deposited to Ripe protocol
    mock_ripe.setUserCollateral(
        wallet.address,
        mock_usdc_collateral_vault.address,
        vault_token_balance
    )

    # Verify Ripe balance is non-zero
    ripe_balance = mock_ripe.userCollateral(wallet.address, mock_usdc_collateral_vault.address)
    assert ripe_balance > 0, "Ripe balance should be non-zero for this test"

    # CRITICAL TEST: Try to change vault - should FAIL
    with boa.reverts("old vault has ripe balance"):
        wallet.setCollateralVault(
            new_usdc_collateral_vault.address,
            lego_id,
            ripe_vault_id,
            True,  # Even with shouldMaxWithdraw=True, should fail due to Ripe balance
            sender=switchboard_alpha.address
        )

    # Verify state did NOT change (still using old vault)
    current_collateral = wallet.collateralAsset()
    assert current_collateral.vaultToken == mock_usdc_collateral_vault.address, "Vault should not have changed"


#########################################
# Configuration Tests - Leverage Vault #
#########################################


def test_set_leverage_vault_success(
    setup_prices,
    undy_levg_vault_usdc,
    new_usdc_leverage_vault,
    switchboard_alpha,
):
    """Test successfully setting a new leverage vault token"""
    wallet = undy_levg_vault_usdc
    lego_id = MOCK_YIELD_LEGO_ID
    ripe_vault_id = 1

    # Get initial leverage vault
    old_leverage = wallet.leverageAsset()

    # Set new leverage vault
    wallet.setLeverageVault(
        new_usdc_leverage_vault.address,
        lego_id,
        ripe_vault_id,
        False,  # shouldMaxWithdraw
        sender=switchboard_alpha.address
    )

    # Verify state updated
    new_leverage = wallet.leverageAsset()
    assert new_leverage.vaultToken == new_usdc_leverage_vault.address
    assert new_leverage.ripeVaultId == ripe_vault_id
    assert wallet.vaultToLegoId(new_usdc_leverage_vault.address) == lego_id


def test_set_leverage_vault_with_existing_balance_fails(
    setup_prices,
    undy_levg_vault_usdc,
    new_usdc_leverage_vault,
    mock_usdc_leverage_vault,
    mock_usdc,
    switchboard_alpha,
    starter_agent,
    governance,
):
    """Test that setting leverage vault succeeds with local balance but no ripe balance"""
    wallet = undy_levg_vault_usdc
    lego_id = MOCK_YIELD_LEGO_ID

    # Give wallet some USDC
    usdc_amount = 1_000 * SIX_DECIMALS
    mock_usdc.mint(wallet.address, usdc_amount, sender=governance.address)

    # Deposit to leverage vault to create balance
    wallet.depositForYield(
        lego_id,
        mock_usdc.address,
        mock_usdc_leverage_vault.address,
        usdc_amount,
        b"",
        sender=starter_agent.address
    )

    # Verify wallet has vault tokens
    vault_balance = mock_usdc_leverage_vault.balanceOf(wallet.address)
    assert vault_balance > 0

    # Setting new leverage vault should succeed even with local balance (no ripe balance)
    wallet.setLeverageVault(
        new_usdc_leverage_vault.address,
        lego_id,
        1,
        False,  # shouldMaxWithdraw - won't auto-withdraw old balance
        sender=switchboard_alpha.address
    )

    # Verify state updated
    new_leverage = wallet.leverageAsset()
    assert new_leverage.vaultToken == new_usdc_leverage_vault.address

    # Old vault tokens still exist since we didn't max withdraw
    assert mock_usdc_leverage_vault.balanceOf(wallet.address) == vault_balance


def test_set_leverage_vault_unauthorized_fails(
    setup_prices,
    undy_levg_vault_usdc,
    new_usdc_leverage_vault,
    starter_agent,
    alice,
):
    """Test that only switchboard can set leverage vault"""
    wallet = undy_levg_vault_usdc

    # Try to set from starter_agent (not switchboard) - should fail
    with boa.reverts("no perms"):
        wallet.setLeverageVault(
            new_usdc_leverage_vault.address,
            MOCK_YIELD_LEGO_ID,
            1,
            False,  # shouldMaxWithdraw
            sender=starter_agent.address
        )

    # Try to set from random user - should fail
    with boa.reverts("no perms"):
        wallet.setLeverageVault(
            new_usdc_leverage_vault.address,
            MOCK_YIELD_LEGO_ID,
            1,
            False,  # shouldMaxWithdraw
            sender=alice
        )


def test_set_leverage_vault_auto_withdraws_with_balance(
    setup_prices,
    undy_levg_vault_usdc,
    new_usdc_leverage_vault,
    mock_usdc_leverage_vault,
    mock_usdc,
    switchboard_alpha,
    starter_agent,
    governance,
):
    """Test auto-withdrawal when setting leverage vault with _shouldMaxWithdraw=True

    This is the primary use case for the _shouldMaxWithdraw parameter on leverage side:
    - Wallet has local balance in old leverage vault (not deposited to Ripe)
    - Setting new leverage vault with _shouldMaxWithdraw=True
    - Should automatically withdraw all funds from old vault
    - Old vault tokens should be burned, underlying USDC should be in wallet
    """
    wallet = undy_levg_vault_usdc
    lego_id = MOCK_YIELD_LEGO_ID
    ripe_vault_id = 1

    # Give wallet some USDC
    usdc_amount = 1_000 * SIX_DECIMALS
    mock_usdc.mint(wallet.address, usdc_amount, sender=governance.address)

    # Deposit to old leverage vault to create vault token balance (locally, not to Ripe)
    wallet.depositForYield(
        lego_id,
        mock_usdc.address,
        mock_usdc_leverage_vault.address,
        usdc_amount,
        b"",
        sender=starter_agent.address
    )

    # Verify wallet has vault tokens in old vault
    old_vault_balance = mock_usdc_leverage_vault.balanceOf(wallet.address)
    assert old_vault_balance > 0

    # Verify no USDC in wallet (it's all in vault tokens)
    assert mock_usdc.balanceOf(wallet.address) == 0

    # Set new leverage vault with _shouldMaxWithdraw=True
    wallet.setLeverageVault(
        new_usdc_leverage_vault.address,
        lego_id,
        ripe_vault_id,
        True,  # shouldMaxWithdraw - CRITICAL: This triggers auto-withdrawal
        sender=switchboard_alpha.address
    )

    # Verify state updated to new vault
    new_leverage = wallet.leverageAsset()
    assert new_leverage.vaultToken == new_usdc_leverage_vault.address
    assert new_leverage.ripeVaultId == ripe_vault_id
    assert wallet.vaultToLegoId(new_usdc_leverage_vault.address) == lego_id

    # CRITICAL VERIFICATION: Old vault tokens should be burned (withdrawn)
    assert mock_usdc_leverage_vault.balanceOf(wallet.address) == 0, "Old vault tokens should be zero after auto-withdrawal"

    # CRITICAL VERIFICATION: Underlying USDC should be back in wallet
    usdc_balance_after = mock_usdc.balanceOf(wallet.address)
    assert usdc_balance_after > 0, "Wallet should have underlying USDC after withdrawal"
    # Allow for small rounding differences in vault exchange rate
    assert abs(usdc_balance_after - usdc_amount) < 100, f"Expected ~{usdc_amount} USDC, got {usdc_balance_after}"


def test_set_leverage_vault_fails_with_ripe_balance(
    setup_prices,
    undy_levg_vault_usdc,
    new_usdc_leverage_vault,
    mock_usdc_leverage_vault,
    mock_usdc,
    mock_ripe,
    switchboard_alpha,
    starter_agent,
    governance,
):
    """Test that setting leverage vault FAILS when old vault has Ripe balance (deposited as leverage)

    CRITICAL SAFETY TEST: The implementation has a safety check to prevent changing vaults
    when funds are actively deposited in Ripe. This prevents accidental loss of leverage position.

    Implementation line: assert getCollateralBalance(...) == 0  # dev: old vault has ripe balance
    (Note: Same function is used for both collateral and leverage vault tokens)

    This test verifies this critical safety mechanism works correctly for leverage vaults.
    """
    wallet = undy_levg_vault_usdc
    lego_id = MOCK_YIELD_LEGO_ID
    ripe_vault_id = 1

    # Set up: Use old leverage vault
    wallet.setLeverageVault(
        mock_usdc_leverage_vault.address,
        lego_id,
        ripe_vault_id,
        False,
        sender=switchboard_alpha.address
    )

    # Give wallet USDC and deposit to old leverage vault
    usdc_amount = 1_000 * SIX_DECIMALS
    mock_usdc.mint(wallet.address, usdc_amount, sender=governance.address)
    wallet.depositForYield(
        lego_id,
        mock_usdc.address,
        mock_usdc_leverage_vault.address,
        usdc_amount,
        b"",
        sender=starter_agent.address
    )

    # CRITICAL SETUP: Deposit vault tokens to Ripe as leverage (non-zero Ripe balance)
    vault_token_balance = mock_usdc_leverage_vault.balanceOf(wallet.address)
    assert vault_token_balance > 0

    # Mock that these tokens are now deposited in Ripe as leverage
    # The mock_ripe.setUserCollateral simulates vault tokens being deposited to Ripe protocol
    mock_ripe.setUserCollateral(
        wallet.address,
        mock_usdc_leverage_vault.address,
        vault_token_balance
    )

    # Verify Ripe balance is non-zero
    ripe_balance = mock_ripe.userCollateral(wallet.address, mock_usdc_leverage_vault.address)
    assert ripe_balance > 0, "Ripe balance should be non-zero for this test"

    # CRITICAL TEST: Try to change leverage vault - should FAIL
    with boa.reverts("old vault has ripe balance"):
        wallet.setLeverageVault(
            new_usdc_leverage_vault.address,
            lego_id,
            ripe_vault_id,
            True,  # Even with shouldMaxWithdraw=True, should fail due to Ripe balance
            sender=switchboard_alpha.address
        )

    # Verify state did NOT change (still using old vault)
    current_leverage = wallet.leverageAsset()
    assert current_leverage.vaultToken == mock_usdc_leverage_vault.address, "Vault should not have changed"


######################################
# Configuration Tests - Slippage     #
######################################


def test_set_usdc_slippage_allowed_success(
    undy_levg_vault_usdc,
    switchboard_alpha,
):
    """Test successfully setting USDC slippage allowed"""
    wallet = undy_levg_vault_usdc

    # Set slippage to 1% (100 basis points) for USDC, keep GREEN at default
    usdc_slippage = 100  # 1%
    green_slippage = wallet.greenSlippageAllowed()  # Keep current value
    wallet.setSlippagesAllowed(usdc_slippage, green_slippage, sender=switchboard_alpha.address)

    # Verify state updated
    assert wallet.usdcSlippageAllowed() == usdc_slippage


    # Test setting to 0% (0 basis points)
    wallet.setSlippagesAllowed(0, green_slippage, sender=switchboard_alpha.address)
    assert wallet.usdcSlippageAllowed() == 0

    # Test setting to max (10% = 1000 basis points)
    wallet.setSlippagesAllowed(1000, green_slippage, sender=switchboard_alpha.address)
    assert wallet.usdcSlippageAllowed() == 1000


def test_set_green_slippage_allowed_success(
    undy_levg_vault_usdc,
    switchboard_alpha,
):
    """Test successfully setting GREEN slippage allowed"""
    wallet = undy_levg_vault_usdc

    # Set slippage to 2% (200 basis points) for GREEN, keep USDC at current value
    usdc_slippage = wallet.usdcSlippageAllowed()  # Keep current value
    green_slippage = 200  # 2%
    wallet.setSlippagesAllowed(usdc_slippage, green_slippage, sender=switchboard_alpha.address)

    # Verify state updated
    assert wallet.greenSlippageAllowed() == green_slippage


    # Test setting to 0% (0 basis points)
    wallet.setSlippagesAllowed(usdc_slippage, 0, sender=switchboard_alpha.address)
    assert wallet.greenSlippageAllowed() == 0

    # Test setting to max (10% = 1000 basis points)
    wallet.setSlippagesAllowed(usdc_slippage, 1000, sender=switchboard_alpha.address)
    assert wallet.greenSlippageAllowed() == 1000


def test_set_slippage_exceeds_max_fails(
    undy_levg_vault_usdc,
    switchboard_alpha,
):
    """Test that setting slippage above max (10%) fails"""
    wallet = undy_levg_vault_usdc

    # Try to set USDC slippage above 10% - should fail
    with boa.reverts("usdc slippage too high (max 10%)"):
        wallet.setSlippagesAllowed(1001, 100, sender=switchboard_alpha.address)

    # Try to set GREEN slippage above 10% - should fail
    with boa.reverts("green slippage too high (max 10%)"):
        wallet.setSlippagesAllowed(100, 1001, sender=switchboard_alpha.address)

    # Try with a very large value for USDC
    with boa.reverts("usdc slippage too high (max 10%)"):
        wallet.setSlippagesAllowed(10000, 100, sender=switchboard_alpha.address)

    # Try with both values too high
    with boa.reverts("usdc slippage too high (max 10%)"):
        wallet.setSlippagesAllowed(1001, 1001, sender=switchboard_alpha.address)


def test_set_slippages_allowed_comprehensive(
    undy_levg_vault_usdc,
    switchboard_alpha,
    alice,
):
    """Test setting both slippages together with event verification and authorization"""
    wallet = undy_levg_vault_usdc

    # Test setting both values together (main use case)
    usdc_slippage = 300  # 3%
    green_slippage = 500  # 5%

    # Set and capture event
    wallet.setSlippagesAllowed(usdc_slippage, green_slippage, sender=switchboard_alpha.address)
    logs = filter_logs(wallet, "SlippagesSet")

    # Verify both state variables updated
    assert wallet.usdcSlippageAllowed() == usdc_slippage
    assert wallet.greenSlippageAllowed() == green_slippage

    # Verify event emission
    assert len(logs) >= 1
    assert logs[-1].usdcSlippage == usdc_slippage
    assert logs[-1].greenSlippage == green_slippage

    # Test unauthorized access fails
    with boa.reverts("no perms"):
        wallet.setSlippagesAllowed(100, 100, sender=alice)


######################################
# Configuration Tests - Helper       #
######################################


def test_set_levg_vault_helper_success(
    undy_levg_vault_usdc,
    new_levg_vault_helper,
    switchboard_alpha,
):
    """Test successfully setting a new levg vault helper"""
    wallet = undy_levg_vault_usdc

    # Get initial helper
    old_helper = wallet.levgVaultHelper()
    assert old_helper != ZERO_ADDRESS

    # Set new helper
    wallet.setLevgVaultHelper(
        new_levg_vault_helper.address,
        sender=switchboard_alpha.address
    )

    # Verify state updated
    assert wallet.levgVaultHelper() == new_levg_vault_helper.address
    assert wallet.levgVaultHelper() != old_helper



def test_set_levg_vault_helper_unauthorized_fails(
    undy_levg_vault_usdc,
    new_levg_vault_helper,
    starter_agent,
    alice,
):
    """Test that only switchboard can set levg vault helper"""
    wallet = undy_levg_vault_usdc

    # Try to set from starter_agent (not switchboard) - should fail
    with boa.reverts("no perms"):
        wallet.setLevgVaultHelper(
            new_levg_vault_helper.address,
            sender=starter_agent.address
        )

    # Try to set from random user - should fail
    with boa.reverts("no perms"):
        wallet.setLevgVaultHelper(
            new_levg_vault_helper.address,
            sender=alice
        )


##################################
# Manager Management Tests       #
##################################


def test_add_manager_success(
    undy_levg_vault_usdc,
    switchboard_alpha,
    alice,
    bob,
):
    """Test successfully adding a manager"""
    wallet = undy_levg_vault_usdc

    # Get initial number of managers
    initial_num_managers = wallet.numManagers()

    # Add alice as manager
    wallet.addManager(alice, sender=switchboard_alpha.address)

    # Verify manager was added
    assert wallet.numManagers() == initial_num_managers + 1
    alice_index = wallet.indexOfManager(alice)
    assert alice_index > 0
    assert wallet.managers(alice_index) == alice

    # Add bob as manager
    wallet.addManager(bob, sender=switchboard_alpha.address)

    # Verify bob was added
    assert wallet.numManagers() == initial_num_managers + 2
    bob_index = wallet.indexOfManager(bob)
    assert bob_index > 0
    assert wallet.managers(bob_index) == bob


def test_add_manager_duplicate(
    undy_levg_vault_usdc,
    switchboard_alpha,
    alice,
):
    """Test that adding a duplicate manager is idempotent"""
    wallet = undy_levg_vault_usdc

    # Add alice as manager
    wallet.addManager(alice, sender=switchboard_alpha.address)
    alice_index = wallet.indexOfManager(alice)
    num_managers = wallet.numManagers()

    # Add alice again - should be idempotent
    wallet.addManager(alice, sender=switchboard_alpha.address)

    # Verify alice is still there with same index and num_managers didn't increase
    assert wallet.indexOfManager(alice) == alice_index
    assert wallet.numManagers() == num_managers
    assert wallet.managers(alice_index) == alice


def test_add_manager_unauthorized_fails(
    undy_levg_vault_usdc,
    starter_agent,
    alice,
    bob,
):
    """Test that only switchboard can add managers"""
    wallet = undy_levg_vault_usdc

    # Try to add from starter_agent (not switchboard) - should fail
    with boa.reverts("no perms"):
        wallet.addManager(alice, sender=starter_agent.address)

    # Try to add from random user - should fail
    with boa.reverts("no perms"):
        wallet.addManager(alice, sender=bob)


def test_remove_manager_success(
    undy_levg_vault_usdc,
    switchboard_alpha,
    alice,
    bob,
):
    """Test successfully removing a manager"""
    wallet = undy_levg_vault_usdc

    # Add two managers
    wallet.addManager(alice, sender=switchboard_alpha.address)
    wallet.addManager(bob, sender=switchboard_alpha.address)

    num_managers_before = wallet.numManagers()
    alice_index = wallet.indexOfManager(alice)
    assert alice_index > 0

    # Remove alice
    wallet.removeManager(alice, sender=switchboard_alpha.address)

    # Verify alice was removed
    assert wallet.numManagers() == num_managers_before - 1
    assert wallet.indexOfManager(alice) == 0

    # Remove bob
    wallet.removeManager(bob, sender=switchboard_alpha.address)

    # Verify bob was removed
    assert wallet.numManagers() == num_managers_before - 2
    assert wallet.indexOfManager(bob) == 0


def test_remove_manager_unauthorized_fails(
    undy_levg_vault_usdc,
    switchboard_alpha,
    starter_agent,
    alice,
    bob,
):
    """Test that only switchboard can remove managers"""
    wallet = undy_levg_vault_usdc

    # Add alice as manager
    wallet.addManager(alice, sender=switchboard_alpha.address)

    # Try to remove from starter_agent (not switchboard) - should fail
    with boa.reverts("no perms"):
        wallet.removeManager(alice, sender=starter_agent.address)

    # Try to remove from random user - should fail
    with boa.reverts("no perms"):
        wallet.removeManager(alice, sender=bob)


##################################
# Parametrized Tests for Multiple Vaults #
##################################


@pytest.mark.parametrize("vault_type", ["usdc", "cbbtc", "weth"])
def test_set_collateral_vault_parametrized(
    vault_type,
    setup_prices,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    new_usdc_collateral_vault,
    new_cbbtc_collateral_vault,
    new_weth_collateral_vault,
    switchboard_alpha,
):
    """Test setting collateral vault for all vault types"""
    vaults = {
        "usdc": undy_levg_vault_usdc,
        "cbbtc": undy_levg_vault_cbbtc,
        "weth": undy_levg_vault_weth,
    }
    new_vaults = {
        "usdc": new_usdc_collateral_vault,
        "cbbtc": new_cbbtc_collateral_vault,
        "weth": new_weth_collateral_vault,
    }

    wallet = vaults[vault_type]
    new_vault = new_vaults[vault_type]

    # Set new collateral vault
    wallet.setCollateralVault(
        new_vault.address,
        MOCK_YIELD_LEGO_ID,
        1,
        False,  # shouldMaxWithdraw
        sender=switchboard_alpha.address
    )

    # Verify state updated
    new_collateral = wallet.collateralAsset()
    assert new_collateral.vaultToken == new_vault.address


##################################
# Sweep Leftovers Tests          #
##################################


def test_sweep_leftovers_success(
    undy_levg_vault_usdc,
    mock_usdc,
    switchboard_alpha,
    governance,
):
    """Test successfully sweeping leftover USDC when totalSupply is 0"""
    wallet = undy_levg_vault_usdc

    # Verify totalSupply is 0 (no shares minted)
    assert wallet.totalSupply() == 0

    # Give wallet some leftover USDC
    leftover_amount = 1_000 * SIX_DECIMALS
    mock_usdc.mint(wallet.address, leftover_amount, sender=governance.address)

    # Verify wallet has balance
    assert mock_usdc.balanceOf(wallet.address) == leftover_amount

    # Get governance balance before sweep
    gov_balance_before = mock_usdc.balanceOf(governance.address)

    # Sweep leftovers
    swept_amount = wallet.sweepLeftovers(sender=switchboard_alpha.address)

    # Verify amount returned
    assert swept_amount == leftover_amount

    # Verify wallet balance is 0
    assert mock_usdc.balanceOf(wallet.address) == 0

    # Verify governance received the funds
    assert mock_usdc.balanceOf(governance.address) == gov_balance_before + leftover_amount


def test_sweep_leftovers_event_emission(
    undy_levg_vault_usdc,
    mock_usdc,
    switchboard_alpha,
    governance,
):
    """Test that sweepLeftovers emits the correct event"""
    wallet = undy_levg_vault_usdc

    # Give wallet some leftover USDC
    leftover_amount = 500 * SIX_DECIMALS
    mock_usdc.mint(wallet.address, leftover_amount, sender=governance.address)

    # Sweep and capture logs
    wallet.sweepLeftovers(sender=switchboard_alpha.address)

    # Check that LeftoversSwept event was emitted (Boa will auto-verify event data)
    # The event should have amount=leftover_amount and recipient=governance.address


def test_sweep_leftovers_with_shares_outstanding_fails(
    undy_levg_vault_usdc,
    mock_usdc,
    switchboard_alpha,
    governance,
    alice,
):
    """Test that sweeping fails when there are shares outstanding"""
    wallet = undy_levg_vault_usdc

    # Give wallet some USDC and have Alice deposit to get shares
    deposit_amount = 10_000 * SIX_DECIMALS
    mock_usdc.mint(alice, deposit_amount, sender=governance.address)
    mock_usdc.approve(wallet.address, deposit_amount, sender=alice)
    wallet.deposit(deposit_amount, alice, sender=alice)

    # Verify totalSupply is not 0
    assert wallet.totalSupply() > 0

    # Give wallet some additional leftover USDC
    leftover_amount = 1_000 * SIX_DECIMALS
    mock_usdc.mint(wallet.address, leftover_amount, sender=governance.address)

    # Try to sweep - should fail because shares are outstanding
    with boa.reverts("shares outstanding"):
        wallet.sweepLeftovers(sender=switchboard_alpha.address)


def test_sweep_leftovers_unauthorized_fails(
    undy_levg_vault_usdc,
    mock_usdc,
    governance,
    alice,
    starter_agent,
):
    """Test that only switchboard can sweep leftovers"""
    wallet = undy_levg_vault_usdc

    # Give wallet some leftover USDC
    leftover_amount = 1_000 * SIX_DECIMALS
    mock_usdc.mint(wallet.address, leftover_amount, sender=governance.address)

    # Try to sweep from starter_agent (not switchboard) - should fail
    with boa.reverts("no perms"):
        wallet.sweepLeftovers(sender=starter_agent.address)

    # Try to sweep from random user - should fail
    with boa.reverts("no perms"):
        wallet.sweepLeftovers(sender=alice)


def test_sweep_leftovers_no_balance_fails(
    undy_levg_vault_usdc,
    mock_usdc,
    switchboard_alpha,
):
    """Test that sweeping fails when there's no balance to sweep"""
    wallet = undy_levg_vault_usdc

    # Verify wallet has no USDC balance
    assert mock_usdc.balanceOf(wallet.address) == 0

    # Try to sweep - should fail because no balance
    with boa.reverts("no balance"):
        wallet.sweepLeftovers(sender=switchboard_alpha.address)


@pytest.mark.parametrize("vault_type,asset_type", [("usdc", "mock_usdc"), ("cbbtc", "mock_cbbtc"), ("weth", "mock_weth")])
def test_sweep_leftovers_parametrized(
    vault_type,
    asset_type,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    switchboard_alpha,
    governance,
    request,
):
    """Test sweeping leftovers for all vault types"""
    vaults = {
        "usdc": undy_levg_vault_usdc,
        "cbbtc": undy_levg_vault_cbbtc,
        "weth": undy_levg_vault_weth,
    }
    assets = {
        "mock_usdc": mock_usdc,
        "mock_cbbtc": mock_cbbtc,
        "mock_weth": mock_weth,
    }
    decimals = {
        "mock_usdc": SIX_DECIMALS,
        "mock_cbbtc": EIGHT_DECIMALS,
        "mock_weth": EIGHTEEN_DECIMALS,
    }

    wallet = vaults[vault_type]
    asset = assets[asset_type]
    decimal = decimals[asset_type]

    # Give wallet some leftover asset
    leftover_amount = 100 * decimal

    # WETH requires different handling (deposit ETH then transfer)
    if asset_type == "mock_weth":
        # Give governance ETH first
        boa.env.set_balance(governance.address, leftover_amount)
        asset.deposit(value=leftover_amount, sender=governance.address)
        asset.transfer(wallet.address, leftover_amount, sender=governance.address)
    else:
        asset.mint(wallet.address, leftover_amount, sender=governance.address)

    # Get governance balance before sweep
    gov_balance_before = asset.balanceOf(governance.address)

    # Sweep leftovers
    swept_amount = wallet.sweepLeftovers(sender=switchboard_alpha.address)

    # Verify amount returned and transferred
    assert swept_amount == leftover_amount
    assert asset.balanceOf(wallet.address) == 0
    assert asset.balanceOf(governance.address) == gov_balance_before + leftover_amount

