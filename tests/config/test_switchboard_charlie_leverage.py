import pytest
import boa
from conf_utils import filter_logs
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS


###########################################
# setCollateralVault() Tests
###########################################

def test_set_collateral_vault_success(switchboard_charlie, undy_levg_vault_usdc, mock_usdc_collateral_vault, governance):
    """Test successful collateral vault update through full lifecycle"""
    vault = undy_levg_vault_usdc
    new_vault_token = mock_usdc_collateral_vault.address
    lego_id = 2  # Mock yield lego
    ripe_vault_id = 1

    # Get initial state
    initial_collateral = vault.collateralAsset()

    # Step 1: Initiate change
    aid = switchboard_charlie.setCollateralVault(
        vault.address,
        new_vault_token,
        ripe_vault_id,
        lego_id,
        sender=governance.address
    )

    # Step 2: Verify pending event
    logs = filter_logs(switchboard_charlie, "PendingCollateralVaultChange")
    assert len(logs) >= 1
    assert logs[-1].vaultAddr == vault.address
    assert logs[-1].vaultToken == new_vault_token
    assert logs[-1].ripeVaultId == ripe_vault_id
    assert logs[-1].legoId == lego_id
    assert logs[-1].actionId == aid
    expected_confirmation_block = boa.env.evm.patch.block_number + switchboard_charlie.actionTimeLock()
    assert logs[-1].confirmationBlock == expected_confirmation_block

    # Step 3: Verify pending state
    assert switchboard_charlie.actionType(aid) == 512  # COLLATERAL_VAULT (2^9)
    pending = switchboard_charlie.pendingCollateralVault(aid)
    assert pending.vaultAddr == vault.address
    assert pending.vaultToken == new_vault_token
    assert pending.ripeVaultId == ripe_vault_id
    assert pending.legoId == lego_id

    # Step 4: Try to execute before timelock
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == False

    # Verify no state change
    current_collateral = vault.collateralAsset()
    assert current_collateral.vaultToken == initial_collateral.vaultToken

    # Step 5: Time travel to timelock
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())

    # Step 6: Execute should succeed
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    # Step 7: Verify execution event
    exec_logs = filter_logs(switchboard_charlie, "CollateralVaultSet")
    assert len(exec_logs) >= 1
    assert exec_logs[-1].vaultAddr == vault.address
    assert exec_logs[-1].vaultToken == new_vault_token
    assert exec_logs[-1].ripeVaultId == ripe_vault_id
    assert exec_logs[-1].legoId == lego_id

    # Step 8: Verify state changes in LevgVault
    updated_collateral = vault.collateralAsset()
    assert updated_collateral.vaultToken == new_vault_token
    assert updated_collateral.ripeVaultId == ripe_vault_id
    assert vault.vaultToLegoId(new_vault_token) == lego_id

    # Step 9: Verify action is cleared
    assert switchboard_charlie.actionType(aid) == 0


def test_set_collateral_vault_empty_address_success(switchboard_charlie, undy_levg_vault_usdc, governance):
    """Test setting collateral vault to empty address (allowed per code)"""
    vault = undy_levg_vault_usdc

    # Initiate change to empty address
    aid = switchboard_charlie.setCollateralVault(
        vault.address,
        ZERO_ADDRESS,
        0,
        0,
        sender=governance.address
    )

    # Timelock and execute
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    # Verify state
    updated_collateral = vault.collateralAsset()
    assert updated_collateral.vaultToken == ZERO_ADDRESS


def test_set_collateral_vault_invalid_vault_fails(switchboard_charlie, governance):
    """Test that invalid vault address is rejected"""
    invalid_vault = boa.env.generate_address()

    with boa.reverts("invalid vault addr"):
        switchboard_charlie.setCollateralVault(
            invalid_vault,
            boa.env.generate_address(),
            1,
            2,
            sender=governance.address
        )


def test_set_collateral_vault_invalid_token_fails(switchboard_charlie, undy_levg_vault_usdc, governance):
    """Test that invalid vault token is rejected by helper validation"""
    vault = undy_levg_vault_usdc
    invalid_token = boa.env.generate_address()

    with boa.reverts("invalid collateral vault token"):
        switchboard_charlie.setCollateralVault(
            vault.address,
            invalid_token,
            999,  # Invalid ripe vault ID
            999,  # Invalid lego ID
            sender=governance.address
        )


def test_set_collateral_vault_non_governance_fails(switchboard_charlie, undy_levg_vault_usdc, alice):
    """Test that non-governance cannot set collateral vault"""
    with boa.reverts("no perms"):
        switchboard_charlie.setCollateralVault(
            undy_levg_vault_usdc.address,
            boa.env.generate_address(),
            1,
            2,
            sender=alice
        )


###########################################
# setLeverageVault() Tests
###########################################

def test_set_leverage_vault_success(switchboard_charlie, undy_levg_vault_usdc, mock_usdc_leverage_vault, governance):
    """Test successful leverage vault update through full lifecycle"""
    vault = undy_levg_vault_usdc
    new_vault_token = mock_usdc_leverage_vault.address
    lego_id = 2  # Mock yield lego
    ripe_vault_id = 1

    # Get initial state
    initial_leverage = vault.leverageAsset()

    # Step 1: Initiate change
    aid = switchboard_charlie.setLeverageVault(
        vault.address,
        new_vault_token,
        lego_id,
        ripe_vault_id,
        sender=governance.address
    )

    # Step 2: Verify pending event
    logs = filter_logs(switchboard_charlie, "PendingLeverageVaultChange")
    assert len(logs) >= 1
    assert logs[-1].vaultAddr == vault.address
    assert logs[-1].vaultToken == new_vault_token
    assert logs[-1].legoId == lego_id
    assert logs[-1].ripeVaultId == ripe_vault_id
    assert logs[-1].actionId == aid

    # Step 3: Verify pending state
    assert switchboard_charlie.actionType(aid) == 1024  # LEVERAGE_VAULT (2^10)
    pending = switchboard_charlie.pendingLeverageVault(aid)
    assert pending.vaultAddr == vault.address
    assert pending.vaultToken == new_vault_token

    # Step 4: Try to execute before timelock
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == False

    # Step 5: Time travel and execute
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    # Step 6: Verify execution event
    exec_logs = filter_logs(switchboard_charlie, "LeverageVaultSet")
    assert len(exec_logs) >= 1
    assert exec_logs[-1].vaultAddr == vault.address
    assert exec_logs[-1].vaultToken == new_vault_token

    # Step 7: Verify state changes
    updated_leverage = vault.leverageAsset()
    assert updated_leverage.vaultToken == new_vault_token
    assert updated_leverage.ripeVaultId == ripe_vault_id

    # Step 8: Verify action cleared
    assert switchboard_charlie.actionType(aid) == 0


def test_set_leverage_vault_invalid_vault_fails(switchboard_charlie, governance):
    """Test that invalid vault address is rejected"""
    invalid_vault = boa.env.generate_address()

    with boa.reverts("invalid vault addr"):
        switchboard_charlie.setLeverageVault(
            invalid_vault,
            boa.env.generate_address(),
            1,
            2,
            sender=governance.address
        )


def test_set_leverage_vault_invalid_token_fails(switchboard_charlie, undy_levg_vault_usdc, governance):
    """Test that invalid vault token is rejected by helper validation"""
    vault = undy_levg_vault_usdc
    invalid_token = boa.env.generate_address()

    with boa.reverts("invalid leverage vault token"):
        switchboard_charlie.setLeverageVault(
            vault.address,
            invalid_token,
            999,  # Invalid lego ID
            999,  # Invalid ripe vault ID
            sender=governance.address
        )


def test_set_leverage_vault_non_governance_fails(switchboard_charlie, undy_levg_vault_usdc, alice):
    """Test that non-governance cannot set leverage vault"""
    with boa.reverts("no perms"):
        switchboard_charlie.setLeverageVault(
            undy_levg_vault_usdc.address,
            boa.env.generate_address(),
            1,
            2,
            sender=alice
        )


###########################################
# setUsdcSlippageAllowed() Tests
###########################################

def test_set_usdc_slippage_success_zero_percent(switchboard_charlie, undy_levg_vault_usdc, governance):
    """Test setting USDC slippage to 0%"""
    vault = undy_levg_vault_usdc
    slippage = 0  # 0%

    aid = switchboard_charlie.setUsdcSlippageAllowed(vault.address, slippage, sender=governance.address)

    # Verify pending
    assert switchboard_charlie.actionType(aid) == 2048  # USDC_SLIPPAGE (2^11)
    pending = switchboard_charlie.pendingUsdcSlippage(aid)
    assert pending.vaultAddr == vault.address
    assert pending.slippage == slippage

    # Execute
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    # Verify state
    assert vault.usdcSlippageAllowed() == slippage

    # Verify event
    logs = filter_logs(switchboard_charlie, "UsdcSlippageSet")
    assert logs[-1].slippage == slippage


def test_set_usdc_slippage_success_five_percent(switchboard_charlie, undy_levg_vault_usdc, governance):
    """Test setting USDC slippage to 5%"""
    vault = undy_levg_vault_usdc
    slippage = 500  # 5%

    aid = switchboard_charlie.setUsdcSlippageAllowed(vault.address, slippage, sender=governance.address)

    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    assert vault.usdcSlippageAllowed() == slippage


def test_set_usdc_slippage_success_max_ten_percent(switchboard_charlie, undy_levg_vault_usdc, governance):
    """Test setting USDC slippage to max 10%"""
    vault = undy_levg_vault_usdc
    slippage = 1000  # 10%

    aid = switchboard_charlie.setUsdcSlippageAllowed(vault.address, slippage, sender=governance.address)

    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    assert vault.usdcSlippageAllowed() == slippage


def test_set_usdc_slippage_exceeds_max_fails(switchboard_charlie, undy_levg_vault_usdc, governance):
    """Test that slippage > 10% is rejected"""
    with boa.reverts():  # dev: slippage too high (max 10%)
        switchboard_charlie.setUsdcSlippageAllowed(
            undy_levg_vault_usdc.address,
            1001,  # 10.01%
            sender=governance.address
        )


def test_set_usdc_slippage_invalid_vault_fails(switchboard_charlie, governance):
    """Test that invalid vault address is rejected"""
    invalid_vault = boa.env.generate_address()

    with boa.reverts("invalid vault addr"):
        switchboard_charlie.setUsdcSlippageAllowed(
            invalid_vault,
            500,
            sender=governance.address
        )


def test_set_usdc_slippage_non_governance_fails(switchboard_charlie, undy_levg_vault_usdc, alice):
    """Test that non-governance cannot set USDC slippage"""
    with boa.reverts("no perms"):
        switchboard_charlie.setUsdcSlippageAllowed(
            undy_levg_vault_usdc.address,
            500,
            sender=alice
        )


###########################################
# setGreenSlippageAllowed() Tests
###########################################

def test_set_green_slippage_success_zero_percent(switchboard_charlie, undy_levg_vault_usdc, governance):
    """Test setting GREEN slippage to 0%"""
    vault = undy_levg_vault_usdc
    slippage = 0  # 0%

    aid = switchboard_charlie.setGreenSlippageAllowed(vault.address, slippage, sender=governance.address)

    # Verify pending
    assert switchboard_charlie.actionType(aid) == 4096  # GREEN_SLIPPAGE (2^12)
    pending = switchboard_charlie.pendingGreenSlippage(aid)
    assert pending.vaultAddr == vault.address
    assert pending.slippage == slippage

    # Execute
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    # Verify state
    assert vault.greenSlippageAllowed() == slippage


def test_set_green_slippage_success_five_percent(switchboard_charlie, undy_levg_vault_usdc, governance):
    """Test setting GREEN slippage to 5%"""
    vault = undy_levg_vault_usdc
    slippage = 500  # 5%

    aid = switchboard_charlie.setGreenSlippageAllowed(vault.address, slippage, sender=governance.address)

    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    assert vault.greenSlippageAllowed() == slippage


def test_set_green_slippage_success_max_ten_percent(switchboard_charlie, undy_levg_vault_usdc, governance):
    """Test setting GREEN slippage to max 10%"""
    vault = undy_levg_vault_usdc
    slippage = 1000  # 10%

    aid = switchboard_charlie.setGreenSlippageAllowed(vault.address, slippage, sender=governance.address)

    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    assert vault.greenSlippageAllowed() == slippage


def test_set_green_slippage_exceeds_max_fails(switchboard_charlie, undy_levg_vault_usdc, governance):
    """Test that slippage > 10% is rejected"""
    with boa.reverts():  # dev: slippage too high (max 10%)
        switchboard_charlie.setGreenSlippageAllowed(
            undy_levg_vault_usdc.address,
            1001,  # 10.01%
            sender=governance.address
        )


def test_set_green_slippage_invalid_vault_fails(switchboard_charlie, governance):
    """Test that invalid vault address is rejected"""
    invalid_vault = boa.env.generate_address()

    with boa.reverts("invalid vault addr"):
        switchboard_charlie.setGreenSlippageAllowed(
            invalid_vault,
            500,
            sender=governance.address
        )


def test_set_green_slippage_non_governance_fails(switchboard_charlie, undy_levg_vault_usdc, alice):
    """Test that non-governance cannot set GREEN slippage"""
    with boa.reverts("no perms"):
        switchboard_charlie.setGreenSlippageAllowed(
            undy_levg_vault_usdc.address,
            500,
            sender=alice
        )


###########################################
# setLevgVaultHelper() Tests
###########################################

def test_set_levg_vault_helper_success(switchboard_charlie, undy_levg_vault_usdc, governance):
    """Test successful helper contract update"""
    vault = undy_levg_vault_usdc
    new_helper = boa.env.generate_address()

    # Initiate change
    aid = switchboard_charlie.setLevgVaultHelper(vault.address, new_helper, sender=governance.address)

    # Verify pending
    assert switchboard_charlie.actionType(aid) == 8192  # LEVG_VAULT_HELPER (2^13)
    pending = switchboard_charlie.pendingLevgVaultHelper(aid)
    assert pending.vaultAddr == vault.address
    assert pending.levgVaultHelper == new_helper

    # Execute
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    # Verify state
    assert vault.levgVaultHelper() == new_helper

    # Verify event
    logs = filter_logs(switchboard_charlie, "LevgVaultHelperSet")
    assert logs[-1].levgVaultHelper == new_helper


def test_set_levg_vault_helper_empty_address_fails(switchboard_charlie, undy_levg_vault_usdc, governance):
    """Test that empty helper address is rejected"""
    with boa.reverts():  # dev: invalid helper address
        switchboard_charlie.setLevgVaultHelper(
            undy_levg_vault_usdc.address,
            ZERO_ADDRESS,
            sender=governance.address
        )


def test_set_levg_vault_helper_invalid_vault_fails(switchboard_charlie, governance):
    """Test that invalid vault address is rejected"""
    invalid_vault = boa.env.generate_address()

    with boa.reverts("invalid vault addr"):
        switchboard_charlie.setLevgVaultHelper(
            invalid_vault,
            boa.env.generate_address(),
            sender=governance.address
        )


def test_set_levg_vault_helper_non_governance_fails(switchboard_charlie, undy_levg_vault_usdc, alice):
    """Test that non-governance cannot set helper"""
    with boa.reverts("no perms"):
        switchboard_charlie.setLevgVaultHelper(
            undy_levg_vault_usdc.address,
            boa.env.generate_address(),
            sender=alice
        )


###########################################
# setMaxDebtRatio() Tests
###########################################

def test_set_max_debt_ratio_success_zero_percent(switchboard_charlie, undy_levg_vault_usdc, governance):
    """Test setting max debt ratio to 0%"""
    vault = undy_levg_vault_usdc
    ratio = 0  # 0%

    aid = switchboard_charlie.setMaxDebtRatio(vault.address, ratio, sender=governance.address)

    # Verify pending
    assert switchboard_charlie.actionType(aid) == 16384  # MAX_DEBT_RATIO (2^14)
    pending = switchboard_charlie.pendingMaxDebtRatio(aid)
    assert pending.vaultAddr == vault.address
    assert pending.ratio == ratio

    # Execute
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    # Verify state
    assert vault.maxDebtRatio() == ratio


def test_set_max_debt_ratio_success_seventy_percent(switchboard_charlie, undy_levg_vault_usdc, governance):
    """Test setting max debt ratio to 70%"""
    vault = undy_levg_vault_usdc
    ratio = 7000  # 70%

    aid = switchboard_charlie.setMaxDebtRatio(vault.address, ratio, sender=governance.address)

    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    assert vault.maxDebtRatio() == ratio


def test_set_max_debt_ratio_success_max_hundred_percent(switchboard_charlie, undy_levg_vault_usdc, governance):
    """Test setting max debt ratio to max 100%"""
    vault = undy_levg_vault_usdc
    ratio = 10000  # 100%

    aid = switchboard_charlie.setMaxDebtRatio(vault.address, ratio, sender=governance.address)

    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    assert vault.maxDebtRatio() == ratio


def test_set_max_debt_ratio_exceeds_max_fails(switchboard_charlie, undy_levg_vault_usdc, governance):
    """Test that ratio > 100% is rejected"""
    with boa.reverts():  # dev: ratio too high (max 100%)
        switchboard_charlie.setMaxDebtRatio(
            undy_levg_vault_usdc.address,
            10001,  # 100.01%
            sender=governance.address
        )


def test_set_max_debt_ratio_invalid_vault_fails(switchboard_charlie, governance):
    """Test that invalid vault address is rejected"""
    invalid_vault = boa.env.generate_address()

    with boa.reverts("invalid vault addr"):
        switchboard_charlie.setMaxDebtRatio(
            invalid_vault,
            7000,
            sender=governance.address
        )


def test_set_max_debt_ratio_non_governance_fails(switchboard_charlie, undy_levg_vault_usdc, alice):
    """Test that non-governance cannot set max debt ratio"""
    with boa.reverts("no perms"):
        switchboard_charlie.setMaxDebtRatio(
            undy_levg_vault_usdc.address,
            7000,
            sender=alice
        )


###########################################
# addVaultManager() Tests
###########################################

def test_add_vault_manager_success_leverage_vault(switchboard_charlie, undy_levg_vault_usdc, alice, governance):
    """Test adding manager to leverage vault"""
    vault = undy_levg_vault_usdc

    # Get initial manager count
    initial_count = vault.numManagers()

    # Initiate add manager
    aid = switchboard_charlie.addVaultManager(vault.address, alice, sender=governance.address)

    # Verify pending
    assert switchboard_charlie.actionType(aid) == 32768  # ADD_MANAGER (2^15)
    pending = switchboard_charlie.pendingAddManager(aid)
    assert pending.vaultAddr == vault.address
    assert pending.manager == alice

    # Execute
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    # Verify state
    assert vault.numManagers() == initial_count + 1
    assert vault.indexOfManager(alice) > 0

    # Verify event
    logs = filter_logs(switchboard_charlie, "ManagerAdded")
    assert logs[-1].manager == alice


def test_add_vault_manager_success_earn_vault(switchboard_charlie, undy_usd_vault, alice, governance):
    """Test adding manager to earn vault (shared functionality)"""
    vault = undy_usd_vault

    initial_count = vault.numManagers()

    aid = switchboard_charlie.addVaultManager(vault.address, alice, sender=governance.address)

    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    assert vault.numManagers() == initial_count + 1
    assert vault.indexOfManager(alice) > 0


def test_add_vault_manager_multiple_sequential(switchboard_charlie, undy_levg_vault_usdc, alice, bob, governance):
    """Test adding multiple managers sequentially"""
    vault = undy_levg_vault_usdc

    # Add alice
    aid1 = switchboard_charlie.addVaultManager(vault.address, alice, sender=governance.address)
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    switchboard_charlie.executePendingAction(aid1, sender=governance.address)

    # Add bob
    aid2 = switchboard_charlie.addVaultManager(vault.address, bob, sender=governance.address)
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    switchboard_charlie.executePendingAction(aid2, sender=governance.address)

    # Verify both are managers
    assert vault.indexOfManager(alice) > 0
    assert vault.indexOfManager(bob) > 0


def test_add_vault_manager_duplicate_idempotent(switchboard_charlie, undy_levg_vault_usdc, alice, governance):
    """Test adding duplicate manager is idempotent"""
    vault = undy_levg_vault_usdc

    # Add alice first time
    aid1 = switchboard_charlie.addVaultManager(vault.address, alice, sender=governance.address)
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    switchboard_charlie.executePendingAction(aid1, sender=governance.address)

    count_after_first = vault.numManagers()

    # Add alice second time
    aid2 = switchboard_charlie.addVaultManager(vault.address, alice, sender=governance.address)
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    switchboard_charlie.executePendingAction(aid2, sender=governance.address)

    # Count should not increase
    assert vault.numManagers() == count_after_first


def test_add_vault_manager_invalid_vault_fails(switchboard_charlie, alice, governance):
    """Test that invalid vault address is rejected"""
    invalid_vault = boa.env.generate_address()

    with boa.reverts("invalid vault addr"):
        switchboard_charlie.addVaultManager(
            invalid_vault,
            alice,
            sender=governance.address
        )


def test_add_vault_manager_non_governance_fails(switchboard_charlie, undy_levg_vault_usdc, alice, bob):
    """Test that non-governance cannot add manager"""
    with boa.reverts("no perms"):
        switchboard_charlie.addVaultManager(
            undy_levg_vault_usdc.address,
            alice,
            sender=bob
        )


###########################################
# removeVaultManager() Tests
###########################################

def test_remove_vault_manager_success_leverage_vault(switchboard_charlie, undy_levg_vault_usdc, alice, governance):
    """Test removing manager from leverage vault - executes immediately"""
    vault = undy_levg_vault_usdc

    # First add alice as manager
    aid_add = switchboard_charlie.addVaultManager(vault.address, alice, sender=governance.address)
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    switchboard_charlie.executePendingAction(aid_add, sender=governance.address)

    # Verify alice is a manager
    assert vault.indexOfManager(alice) > 0
    initial_count = vault.numManagers()

    # Remove alice - executes immediately (no timelock)
    aid_remove = switchboard_charlie.removeVaultManager(vault.address, alice, sender=governance.address)

    # Should return 0 (no action ID) for immediate execution
    assert aid_remove == 0

    # Verify state immediately (no timelock wait)
    assert vault.numManagers() == initial_count - 1
    assert vault.indexOfManager(alice) == 0

    # Verify event
    logs = filter_logs(switchboard_charlie, "ManagerRemoved")
    assert logs[-1].vaultAddr == vault.address
    assert logs[-1].manager == alice


def test_remove_vault_manager_success_earn_vault(switchboard_charlie, undy_usd_vault, alice, governance):
    """Test removing manager from earn vault - executes immediately"""
    vault = undy_usd_vault

    # Add alice
    aid_add = switchboard_charlie.addVaultManager(vault.address, alice, sender=governance.address)
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    switchboard_charlie.executePendingAction(aid_add, sender=governance.address)

    initial_count = vault.numManagers()

    # Remove alice - executes immediately (no timelock)
    aid_remove = switchboard_charlie.removeVaultManager(vault.address, alice, sender=governance.address)

    # Should return 0 (no action ID) for immediate execution
    assert aid_remove == 0

    # Verify state immediately (no timelock wait)
    assert vault.numManagers() == initial_count - 1
    assert vault.indexOfManager(alice) == 0


def test_remove_vault_manager_multiple_sequential(switchboard_charlie, undy_levg_vault_usdc, alice, bob, governance):
    """Test removing multiple managers sequentially - executes immediately"""
    vault = undy_levg_vault_usdc

    # Add both alice and bob
    aid1 = switchboard_charlie.addVaultManager(vault.address, alice, sender=governance.address)
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    switchboard_charlie.executePendingAction(aid1, sender=governance.address)

    aid2 = switchboard_charlie.addVaultManager(vault.address, bob, sender=governance.address)
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    switchboard_charlie.executePendingAction(aid2, sender=governance.address)

    # Remove alice - executes immediately (no timelock)
    aid3 = switchboard_charlie.removeVaultManager(vault.address, alice, sender=governance.address)
    assert aid3 == 0
    assert vault.indexOfManager(alice) == 0

    # Remove bob - executes immediately (no timelock)
    aid4 = switchboard_charlie.removeVaultManager(vault.address, bob, sender=governance.address)
    assert aid4 == 0
    assert vault.indexOfManager(bob) == 0

    # Verify both removed
    assert vault.indexOfManager(alice) == 0
    assert vault.indexOfManager(bob) == 0


def test_remove_vault_manager_non_existent_graceful(switchboard_charlie, undy_levg_vault_usdc, alice, governance):
    """Test removing non-existent manager is graceful (no error) - executes immediately"""
    vault = undy_levg_vault_usdc

    # Ensure alice is not a manager
    assert vault.indexOfManager(alice) == 0

    # Try to remove alice (should not error) - executes immediately
    aid = switchboard_charlie.removeVaultManager(vault.address, alice, sender=governance.address)

    # Should return 0 and succeed without error
    assert aid == 0


def test_remove_vault_manager_invalid_vault_fails(switchboard_charlie, alice, governance):
    """Test that invalid vault address is rejected"""
    invalid_vault = boa.env.generate_address()

    with boa.reverts("invalid vault addr"):
        switchboard_charlie.removeVaultManager(
            invalid_vault,
            alice,
            sender=governance.address
        )


def test_remove_vault_manager_non_governance_fails(switchboard_charlie, undy_levg_vault_usdc, alice, bob):
    """Test that non-governance cannot remove manager"""
    with boa.reverts("no perms"):
        switchboard_charlie.removeVaultManager(
            undy_levg_vault_usdc.address,
            alice,
            sender=bob
        )
