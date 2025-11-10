import pytest
import boa

from constants import MAX_UINT256, EIGHTEEN_DECIMALS, ZERO_ADDRESS

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
        ripe_vault_id,
        lego_id,
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
    """Test that setting collateral vault fails when old vault has balance"""
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

    # Try to set new collateral vault - should fail due to existing balance
    with boa.reverts():  # dev: old vault has local balance
        wallet.setCollateralVault(
            new_usdc_collateral_vault.address,
            1,
            lego_id,
            sender=switchboard_alpha.address
        )


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
    with boa.reverts():  # dev: no perms
        wallet.setCollateralVault(
            new_usdc_collateral_vault.address,
            1,
            MOCK_YIELD_LEGO_ID,
            sender=starter_agent.address
        )

    # Try to set from random user - should fail
    with boa.reverts():  # dev: no perms
        wallet.setCollateralVault(
            new_usdc_collateral_vault.address,
            1,
            MOCK_YIELD_LEGO_ID,
            sender=alice
        )


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
    """Test that setting leverage vault fails when old vault has balance"""
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

    # Try to set new leverage vault - should fail due to existing balance
    with boa.reverts():  # dev: old vault has local balance
        wallet.setLeverageVault(
            new_usdc_leverage_vault.address,
            lego_id,
            1,
            sender=switchboard_alpha.address
        )


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
    with boa.reverts():  # dev: no perms
        wallet.setLeverageVault(
            new_usdc_leverage_vault.address,
            MOCK_YIELD_LEGO_ID,
            1,
            sender=starter_agent.address
        )

    # Try to set from random user - should fail
    with boa.reverts():  # dev: no perms
        wallet.setLeverageVault(
            new_usdc_leverage_vault.address,
            MOCK_YIELD_LEGO_ID,
            1,
            sender=alice
        )


######################################
# Configuration Tests - Slippage     #
######################################


def test_set_usdc_slippage_allowed_success(
    undy_levg_vault_usdc,
    switchboard_alpha,
):
    """Test successfully setting USDC slippage allowed"""
    wallet = undy_levg_vault_usdc

    # Set slippage to 1% (100 basis points)
    new_slippage = 100  # 1%
    wallet.setUsdcSlippageAllowed(new_slippage, sender=switchboard_alpha.address)

    # Verify state updated
    assert wallet.usdcSlippageAllowed() == new_slippage


    # Test setting to 0% (0 basis points)
    wallet.setUsdcSlippageAllowed(0, sender=switchboard_alpha.address)
    assert wallet.usdcSlippageAllowed() == 0

    # Test setting to max (10% = 1000 basis points)
    wallet.setUsdcSlippageAllowed(1000, sender=switchboard_alpha.address)
    assert wallet.usdcSlippageAllowed() == 1000


def test_set_green_slippage_allowed_success(
    undy_levg_vault_usdc,
    switchboard_alpha,
):
    """Test successfully setting GREEN slippage allowed"""
    wallet = undy_levg_vault_usdc

    # Set slippage to 2% (200 basis points)
    new_slippage = 200  # 2%
    wallet.setGreenSlippageAllowed(new_slippage, sender=switchboard_alpha.address)

    # Verify state updated
    assert wallet.greenSlippageAllowed() == new_slippage


    # Test setting to 0% (0 basis points)
    wallet.setGreenSlippageAllowed(0, sender=switchboard_alpha.address)
    assert wallet.greenSlippageAllowed() == 0

    # Test setting to max (10% = 1000 basis points)
    wallet.setGreenSlippageAllowed(1000, sender=switchboard_alpha.address)
    assert wallet.greenSlippageAllowed() == 1000


def test_set_slippage_exceeds_max_fails(
    undy_levg_vault_usdc,
    switchboard_alpha,
):
    """Test that setting slippage above max (10%) fails"""
    wallet = undy_levg_vault_usdc

    # Try to set USDC slippage above 10% - should fail
    with boa.reverts():  # dev: slippage too high (max 10%)
        wallet.setUsdcSlippageAllowed(1001, sender=switchboard_alpha.address)

    # Try to set GREEN slippage above 10% - should fail
    with boa.reverts():  # dev: slippage too high (max 10%)
        wallet.setGreenSlippageAllowed(1001, sender=switchboard_alpha.address)

    # Try with a very large value
    with boa.reverts():  # dev: slippage too high (max 10%)
        wallet.setUsdcSlippageAllowed(10000, sender=switchboard_alpha.address)


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
    with boa.reverts():  # dev: no perms
        wallet.setLevgVaultHelper(
            new_levg_vault_helper.address,
            sender=starter_agent.address
        )

    # Try to set from random user - should fail
    with boa.reverts():  # dev: no perms
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
    with boa.reverts():  # dev: no perms
        wallet.addManager(alice, sender=starter_agent.address)

    # Try to add from random user - should fail
    with boa.reverts():  # dev: no perms
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
    with boa.reverts():  # dev: no perms
        wallet.removeManager(alice, sender=starter_agent.address)

    # Try to remove from random user - should fail
    with boa.reverts():  # dev: no perms
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
        1,
        MOCK_YIELD_LEGO_ID,
        sender=switchboard_alpha.address
    )

    # Verify state updated
    new_collateral = wallet.collateralAsset()
    assert new_collateral.vaultToken == new_vault.address

