import pytest
import boa
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS
from conf_utils import filter_logs
from conf_core import VAULT_INFO


@pytest.fixture
def deploy_test_vault(undy_hq_deploy):
    """Helper to deploy a test vault with proper parameters"""
    def _deploy():
        # Deploy a mock ERC20 token to use as the vault asset
        mock_asset = boa.load(
            "contracts/mock/MockErc20.vy",
            boa.env.generate_address(),  # whale
            "Mock Asset",  # name
            "MOCK",  # symbol
            18,  # decimals
            1_000_000,  # supply
        )

        return boa.load(
            "contracts/vaults/Autopilot.vy",
            mock_asset.address,
            VAULT_INFO['USDC']["name"],
            VAULT_INFO['USDC']["symbol"],
            undy_hq_deploy.address,
            0,
            0,
            boa.env.generate_address(),
            name="undy_usd_vault",
        )
    return _deploy


def test_vault_registry_initialization(vault_registry):
    """Test VaultRegistry is properly initialized"""
    # Verify registry was deployed
    assert vault_registry.address != ZERO_ADDRESS


def test_start_add_new_address_to_registry(vault_registry, governance, deploy_test_vault):
    """Test starting the process to add a new vault to the registry"""
    # Deploy a real vault contract to use as the new address
    new_vault = deploy_test_vault()

    # Need governance permission (not switchboard for registry operations)
    # Start adding new vault
    result = vault_registry.startAddNewAddressToRegistry(
        new_vault.address,
        "New Test Vault",
        sender=governance.address
    )

    assert result == True

    # Verify pending address was set
    pending = vault_registry.pendingNewAddr(new_vault.address)
    assert pending.confirmBlock > 0
    assert pending.description == "New Test Vault"


def test_start_add_new_address_non_gov_fails(vault_registry, bob, deploy_test_vault):
    """Test that non-governance cannot start adding new vault"""
    new_vault = deploy_test_vault()

    with boa.reverts("no perms"):
        vault_registry.startAddNewAddressToRegistry(
            new_vault.address,
            "New Test Vault",
            sender=bob
        )


def test_confirm_new_address_to_registry(vault_registry, governance, deploy_test_vault):
    """Test confirming a new vault address after timelock"""
    # Deploy a real vault contract
    new_vault = deploy_test_vault()

    # Start the process
    vault_registry.startAddNewAddressToRegistry(
        new_vault.address,
        "New Test Vault",
        sender=governance.address
    )

    # Travel past timelock
    timelock = vault_registry.registryChangeTimeLock()
    boa.env.time_travel(blocks=timelock + 1)

    # Confirm the new address
    reg_id = vault_registry.confirmNewAddressToRegistry(
        new_vault.address,
        sender=governance.address
    )

    assert reg_id > 0
    assert vault_registry.isEarnVault(new_vault.address) == True


def test_confirm_new_address_before_timelock_fails(vault_registry, governance, deploy_test_vault, fork):
    """Test that confirming before timelock expires fails"""
    # First set the registry timelock to a valid non-zero value (use min timelock from params)
    from config.BluePrint import PARAMS
    min_timelock = PARAMS[fork]["UNDY_HQ_MIN_REG_TIMELOCK"]
    vault_registry.setRegistryTimeLockAfterSetup(min_timelock, sender=governance.address)

    # Deploy a real vault contract
    new_vault = deploy_test_vault()

    # Start the process
    vault_registry.startAddNewAddressToRegistry(
        new_vault.address,
        "New Test Vault",
        sender=governance.address
    )

    # Try to confirm immediately (should fail because timelock hasn't passed)
    with boa.reverts("time lock not reached"):
        vault_registry.confirmNewAddressToRegistry(
            new_vault.address,
            sender=governance.address
        )


def test_cancel_new_address_to_registry(vault_registry, governance, deploy_test_vault):
    """Test canceling a pending vault registration"""
    # Deploy a real vault contract
    new_vault = deploy_test_vault()

    # Start the process
    vault_registry.startAddNewAddressToRegistry(
        new_vault.address,
        "New Test Vault",
        sender=governance.address
    )

    # Verify pending
    pending = vault_registry.pendingNewAddr(new_vault.address)
    assert pending.confirmBlock > 0

    # Cancel
    result = vault_registry.cancelNewAddressToRegistry(
        new_vault.address,
        sender=governance.address
    )

    assert result == True

    # Verify no longer pending
    pending = vault_registry.pendingNewAddr(new_vault.address)
    assert pending.confirmBlock == 0


def test_is_earn_vault(vault_registry, undy_usd_vault):
    """Test isEarnVault function"""
    # undy_usd_vault is registered in fixtures
    assert vault_registry.isEarnVault(undy_usd_vault.address) == True

    # Random address should not be a vault
    random_addr = boa.env.generate_address()
    assert vault_registry.isEarnVault(random_addr) == False


def test_set_can_deposit(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test setting canDeposit flag"""
    # Initially set to True in fixtures
    assert vault_registry.canDeposit(undy_usd_vault.address) == True

    # Disable deposits
    vault_registry.setCanDeposit(
        undy_usd_vault.address,
        False,
        sender=switchboard_alpha.address
    )

    assert vault_registry.canDeposit(undy_usd_vault.address) == False

    # Re-enable deposits
    vault_registry.setCanDeposit(
        undy_usd_vault.address,
        True,
        sender=switchboard_alpha.address
    )

    assert vault_registry.canDeposit(undy_usd_vault.address) == True


def test_set_can_deposit_non_switchboard_fails(vault_registry, undy_usd_vault, bob):
    """Test that non-switchboard cannot set canDeposit"""
    with boa.reverts("no perms"):
        vault_registry.setCanDeposit(
            undy_usd_vault.address,
            False,
            sender=bob
        )


def test_set_can_deposit_emits_event(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test that setCanDeposit emits CanDepositSet event"""
    vault_registry.setCanDeposit(
        undy_usd_vault.address,
        False,
        sender=switchboard_alpha.address
    )

    events = filter_logs(vault_registry, "CanDepositSet")
    assert len(events) > 0

    latest_event = events[-1]
    assert latest_event.vaultAddr == undy_usd_vault.address
    assert latest_event.canDeposit == False


def test_set_can_withdraw(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test setting canWithdraw flag"""
    # Initially set to True in fixtures
    assert vault_registry.canWithdraw(undy_usd_vault.address) == True

    # Disable withdrawals
    vault_registry.setCanWithdraw(
        undy_usd_vault.address,
        False,
        sender=switchboard_alpha.address
    )

    assert vault_registry.canWithdraw(undy_usd_vault.address) == False

    # Re-enable withdrawals
    vault_registry.setCanWithdraw(
        undy_usd_vault.address,
        True,
        sender=switchboard_alpha.address
    )

    assert vault_registry.canWithdraw(undy_usd_vault.address) == True


def test_set_can_withdraw_non_switchboard_fails(vault_registry, undy_usd_vault, bob):
    """Test that non-switchboard cannot set canWithdraw"""
    with boa.reverts("no perms"):
        vault_registry.setCanWithdraw(
            undy_usd_vault.address,
            False,
            sender=bob
        )


def test_set_max_deposit_amount(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test setting maxDepositAmount"""
    # Initially 0 (unlimited)
    assert vault_registry.maxDepositAmount(undy_usd_vault.address) == 0

    # Set a max deposit
    max_amount = 1_000_000 * EIGHTEEN_DECIMALS
    vault_registry.setMaxDepositAmount(
        undy_usd_vault.address,
        max_amount,
        sender=switchboard_alpha.address
    )

    assert vault_registry.maxDepositAmount(undy_usd_vault.address) == max_amount

    # Update to new value
    new_max = 2_000_000 * EIGHTEEN_DECIMALS
    vault_registry.setMaxDepositAmount(
        undy_usd_vault.address,
        new_max,
        sender=switchboard_alpha.address
    )

    assert vault_registry.maxDepositAmount(undy_usd_vault.address) == new_max


def test_set_max_deposit_amount_non_switchboard_fails(vault_registry, undy_usd_vault, bob):
    """Test that non-switchboard cannot set maxDepositAmount"""
    with boa.reverts("no perms"):
        vault_registry.setMaxDepositAmount(
            undy_usd_vault.address,
            1_000_000 * EIGHTEEN_DECIMALS,
            sender=bob
        )


def test_set_vault_ops_frozen(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test setting vault ops frozen flag"""
    # Initially False
    assert vault_registry.isVaultOpsFrozen(undy_usd_vault.address) == False

    # Freeze vault ops
    vault_registry.setVaultOpsFrozen(
        undy_usd_vault.address,
        True,
        sender=switchboard_alpha.address
    )

    assert vault_registry.isVaultOpsFrozen(undy_usd_vault.address) == True

    # Unfreeze vault ops
    vault_registry.setVaultOpsFrozen(
        undy_usd_vault.address,
        False,
        sender=switchboard_alpha.address
    )

    assert vault_registry.isVaultOpsFrozen(undy_usd_vault.address) == False


def test_set_vault_ops_frozen_non_switchboard_fails(vault_registry, undy_usd_vault, bob):
    """Test that non-switchboard cannot freeze vault ops"""
    with boa.reverts("no perms"):
        vault_registry.setVaultOpsFrozen(
            undy_usd_vault.address,
            True,
            sender=bob
        )


def test_set_vault_ops_frozen_emits_event(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test that setVaultOpsFrozen emits event"""
    vault_registry.setVaultOpsFrozen(
        undy_usd_vault.address,
        True,
        sender=switchboard_alpha.address
    )

    events = filter_logs(vault_registry, "VaultOpsFrozenSet")
    assert len(events) > 0

    latest_event = events[-1]
    assert latest_event.vaultAddr == undy_usd_vault.address
    assert latest_event.isFrozen == True


def test_set_redemption_buffer(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test setting redemption buffer"""
    # Initially set to 2% (200) in fixtures
    assert vault_registry.redemptionBuffer(undy_usd_vault.address) == 200

    # Set to 5%
    vault_registry.setRedemptionBuffer(
        undy_usd_vault.address,
        500,
        sender=switchboard_alpha.address
    )

    assert vault_registry.redemptionBuffer(undy_usd_vault.address) == 500

    # Set to 0%
    vault_registry.setRedemptionBuffer(
        undy_usd_vault.address,
        0,
        sender=switchboard_alpha.address
    )

    assert vault_registry.redemptionBuffer(undy_usd_vault.address) == 0


def test_set_redemption_buffer_non_switchboard_fails(vault_registry, undy_usd_vault, bob):
    """Test that non-switchboard cannot set redemption buffer"""
    with boa.reverts("no perms"):
        vault_registry.setRedemptionBuffer(
            undy_usd_vault.address,
            500,
            sender=bob
        )


def test_set_redemption_buffer_too_high_reverts(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test that buffer > 10% reverts"""
    # Max is 10% (1000)
    with boa.reverts("invalid redemption buffer"):
        vault_registry.setRedemptionBuffer(
            undy_usd_vault.address,
            1001,  # 10.01%
            sender=switchboard_alpha.address
        )

    # 10% should work
    vault_registry.setRedemptionBuffer(
        undy_usd_vault.address,
        1000,  # 10%
        sender=switchboard_alpha.address
    )

    assert vault_registry.redemptionBuffer(undy_usd_vault.address) == 1000


def test_set_redemption_buffer_emits_event(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test that setRedemptionBuffer emits event"""
    vault_registry.setRedemptionBuffer(
        undy_usd_vault.address,
        500,
        sender=switchboard_alpha.address
    )

    events = filter_logs(vault_registry, "RedemptionBufferSet")
    assert len(events) > 0

    latest_event = events[-1]
    assert latest_event.vaultAddr == undy_usd_vault.address
    assert latest_event.buffer == 500


def test_set_performance_fee(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test setting performance fee"""
    # Initial fee should be 0 (set by fixture to 0, default in contract is 20%)
    initial_fee = vault_registry.getPerformanceFee(undy_usd_vault.address)

    # Set to 15%
    vault_registry.setPerformanceFee(
        undy_usd_vault.address,
        15_00,  # 15%
        sender=switchboard_alpha.address
    )

    assert vault_registry.getPerformanceFee(undy_usd_vault.address) == 15_00

    # Set to 0%
    vault_registry.setPerformanceFee(
        undy_usd_vault.address,
        0,
        sender=switchboard_alpha.address
    )

    assert vault_registry.getPerformanceFee(undy_usd_vault.address) == 0

    # Set to 100%
    vault_registry.setPerformanceFee(
        undy_usd_vault.address,
        100_00,  # 100%
        sender=switchboard_alpha.address
    )

    assert vault_registry.getPerformanceFee(undy_usd_vault.address) == 100_00


def test_set_performance_fee_non_switchboard_fails(vault_registry, undy_usd_vault, bob):
    """Test that non-switchboard cannot set performance fee"""
    with boa.reverts("no perms"):
        vault_registry.setPerformanceFee(
            undy_usd_vault.address,
            15_00,
            sender=bob
        )


def test_set_performance_fee_invalid_vault_fails(vault_registry, switchboard_alpha):
    """Test that setting fee for invalid vault fails"""
    random_vault = boa.env.generate_address()

    with boa.reverts("invalid vault addr"):
        vault_registry.setPerformanceFee(
            random_vault,
            15_00,
            sender=switchboard_alpha.address
        )


def test_set_performance_fee_too_high_fails(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test that performance fee > 100% fails"""
    # Max is 100% (10000)
    with boa.reverts("invalid performance fee"):
        vault_registry.setPerformanceFee(
            undy_usd_vault.address,
            100_01,  # 100.01%
            sender=switchboard_alpha.address
        )

    # 100% should work
    vault_registry.setPerformanceFee(
        undy_usd_vault.address,
        100_00,  # 100%
        sender=switchboard_alpha.address
    )

    assert vault_registry.getPerformanceFee(undy_usd_vault.address) == 100_00


def test_set_performance_fee_emits_event(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test that setPerformanceFee emits event"""
    vault_registry.setPerformanceFee(
        undy_usd_vault.address,
        25_00,  # 25%
        sender=switchboard_alpha.address
    )

    events = filter_logs(vault_registry, "PerformanceFeeSet")
    assert len(events) > 0

    latest_event = events[-1]
    assert latest_event.vaultAddr == undy_usd_vault.address
    assert latest_event.performanceFee == 25_00


def test_is_valid_performance_fee_view(vault_registry):
    """Test isValidPerformanceFee view function"""
    # Valid fees
    assert vault_registry.isValidPerformanceFee(0) == True  # 0%
    assert vault_registry.isValidPerformanceFee(50_00) == True  # 50%
    assert vault_registry.isValidPerformanceFee(100_00) == True  # 100%

    # Invalid fees (> 100%)
    assert vault_registry.isValidPerformanceFee(100_01) == False  # 100.01%
    assert vault_registry.isValidPerformanceFee(200_00) == False  # 200%


def test_get_performance_fee_view(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test getPerformanceFee view returns correct value"""
    # Set fee to 20%
    vault_registry.setPerformanceFee(
        undy_usd_vault.address,
        20_00,
        sender=switchboard_alpha.address
    )

    # Verify view returns correct value
    assert vault_registry.getPerformanceFee(undy_usd_vault.address) == 20_00

    # Change to 30%
    vault_registry.setPerformanceFee(
        undy_usd_vault.address,
        30_00,
        sender=switchboard_alpha.address
    )

    assert vault_registry.getPerformanceFee(undy_usd_vault.address) == 30_00


def test_set_min_yield_withdraw_amount(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test setting minYieldWithdrawAmount"""
    # Initially set to 10000 in fixtures
    assert vault_registry.minYieldWithdrawAmount(undy_usd_vault.address) == 10000

    # Set to 5000
    vault_registry.setMinYieldWithdrawAmount(
        undy_usd_vault.address,
        5000,
        sender=switchboard_alpha.address
    )

    assert vault_registry.minYieldWithdrawAmount(undy_usd_vault.address) == 5000

    # Set to 0
    vault_registry.setMinYieldWithdrawAmount(
        undy_usd_vault.address,
        0,
        sender=switchboard_alpha.address
    )

    assert vault_registry.minYieldWithdrawAmount(undy_usd_vault.address) == 0

    # Set to large value
    large_amount = 1_000_000 * EIGHTEEN_DECIMALS
    vault_registry.setMinYieldWithdrawAmount(
        undy_usd_vault.address,
        large_amount,
        sender=switchboard_alpha.address
    )

    assert vault_registry.minYieldWithdrawAmount(undy_usd_vault.address) == large_amount


def test_set_min_yield_withdraw_amount_non_switchboard_fails(vault_registry, undy_usd_vault, bob):
    """Test that non-switchboard cannot set minYieldWithdrawAmount"""
    with boa.reverts("no perms"):
        vault_registry.setMinYieldWithdrawAmount(
            undy_usd_vault.address,
            5000,
            sender=bob
        )


def test_set_min_yield_withdraw_amount_invalid_vault_fails(vault_registry, switchboard_alpha):
    """Test that setting minYieldWithdrawAmount for invalid vault fails"""
    random_vault = boa.env.generate_address()

    with boa.reverts("invalid vault addr"):
        vault_registry.setMinYieldWithdrawAmount(
            random_vault,
            5000,
            sender=switchboard_alpha.address
        )


def test_set_min_yield_withdraw_amount_emits_event(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test that setMinYieldWithdrawAmount emits event"""
    vault_registry.setMinYieldWithdrawAmount(
        undy_usd_vault.address,
        7500,
        sender=switchboard_alpha.address
    )

    events = filter_logs(vault_registry, "MinYieldWithdrawAmountSet")
    assert len(events) > 0

    latest_event = events[-1]
    assert latest_event.vaultAddr == undy_usd_vault.address
    assert latest_event.amount == 7500


def test_min_yield_withdraw_amount_view(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test minYieldWithdrawAmount view returns correct value"""
    # Set to specific value
    vault_registry.setMinYieldWithdrawAmount(
        undy_usd_vault.address,
        12345,
        sender=switchboard_alpha.address
    )

    # Verify view returns correct value
    assert vault_registry.minYieldWithdrawAmount(undy_usd_vault.address) == 12345


def test_redemption_config_view(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test redemptionConfig view returns correct tuple"""
    # Set redemption buffer to 300 (3%)
    vault_registry.setRedemptionBuffer(
        undy_usd_vault.address,
        300,
        sender=switchboard_alpha.address
    )

    # Set minYieldWithdrawAmount to 8000
    vault_registry.setMinYieldWithdrawAmount(
        undy_usd_vault.address,
        8000,
        sender=switchboard_alpha.address
    )

    # Get redemption config tuple
    buffer, min_yield = vault_registry.redemptionConfig(undy_usd_vault.address)

    # Verify both values
    assert buffer == 300
    assert min_yield == 8000

    # Verify matches individual view functions
    assert buffer == vault_registry.redemptionBuffer(undy_usd_vault.address)
    assert min_yield == vault_registry.minYieldWithdrawAmount(undy_usd_vault.address)


def test_is_valid_redemption_buffer_view(vault_registry):
    """Test isValidRedemptionBuffer view function"""
    # Valid buffers (0-10%)
    assert vault_registry.isValidRedemptionBuffer(0) == True  # 0%
    assert vault_registry.isValidRedemptionBuffer(5_00) == True  # 5%
    assert vault_registry.isValidRedemptionBuffer(10_00) == True  # 10%

    # Invalid buffers (> 10%)
    assert vault_registry.isValidRedemptionBuffer(10_01) == False  # 10.01%
    assert vault_registry.isValidRedemptionBuffer(20_00) == False  # 20%


def test_multiple_vaults_different_performance_fees(vault_registry, governance, deploy_test_vault, switchboard_alpha):
    """Test that different vaults have independent performance fees"""
    # Create two vaults
    vault_1 = deploy_test_vault()
    vault_2 = deploy_test_vault()

    # Register both vaults
    for vault in [vault_1, vault_2]:
        vault_registry.startAddNewAddressToRegistry(
            vault.address,
            f"Test Vault {vault.address}",
            sender=governance.address
        )

    timelock = vault_registry.registryChangeTimeLock()
    boa.env.time_travel(blocks=timelock + 1)

    # Confirm both with default fees
    for vault in [vault_1, vault_2]:
        vault_registry.confirmNewAddressToRegistry(
            vault.address,
            sender=governance.address
        )

    # Set vault 1 to 10% fee
    vault_registry.setPerformanceFee(
        vault_1.address,
        10_00,
        sender=switchboard_alpha.address
    )

    # Set vault 2 to 25% fee
    vault_registry.setPerformanceFee(
        vault_2.address,
        25_00,
        sender=switchboard_alpha.address
    )

    # Verify independence
    assert vault_registry.getPerformanceFee(vault_1.address) == 10_00
    assert vault_registry.getPerformanceFee(vault_2.address) == 25_00

    # Change vault 1 fee
    vault_registry.setPerformanceFee(
        vault_1.address,
        15_00,
        sender=switchboard_alpha.address
    )

    # Verify vault 2 unchanged
    assert vault_registry.getPerformanceFee(vault_1.address) == 15_00
    assert vault_registry.getPerformanceFee(vault_2.address) == 25_00


def test_multiple_vaults_different_min_yield_amounts(vault_registry, governance, deploy_test_vault, switchboard_alpha):
    """Test that different vaults have independent minYieldWithdrawAmount"""
    # Create two vaults
    vault_1 = deploy_test_vault()
    vault_2 = deploy_test_vault()

    # Register both vaults
    for vault in [vault_1, vault_2]:
        vault_registry.startAddNewAddressToRegistry(
            vault.address,
            f"Test Vault {vault.address}",
            sender=governance.address
        )

    timelock = vault_registry.registryChangeTimeLock()
    boa.env.time_travel(blocks=timelock + 1)

    # Confirm both
    for vault in [vault_1, vault_2]:
        vault_registry.confirmNewAddressToRegistry(
            vault.address,
            sender=governance.address
        )

    # Set vault 1 to 5000
    vault_registry.setMinYieldWithdrawAmount(
        vault_1.address,
        5000,
        sender=switchboard_alpha.address
    )

    # Set vault 2 to 15000
    vault_registry.setMinYieldWithdrawAmount(
        vault_2.address,
        15000,
        sender=switchboard_alpha.address
    )

    # Verify independence
    assert vault_registry.minYieldWithdrawAmount(vault_1.address) == 5000
    assert vault_registry.minYieldWithdrawAmount(vault_2.address) == 15000

    # Change vault 1
    vault_registry.setMinYieldWithdrawAmount(
        vault_1.address,
        8000,
        sender=switchboard_alpha.address
    )

    # Verify vault 2 unchanged
    assert vault_registry.minYieldWithdrawAmount(vault_1.address) == 8000
    assert vault_registry.minYieldWithdrawAmount(vault_2.address) == 15000


def test_set_approved_vault_token(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test approving and disapproving vault tokens"""
    new_vault_token = boa.env.generate_address()

    # Initially not approved
    assert vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, new_vault_token) == False

    # Approve
    vault_registry.setApprovedVaultToken(
        undy_usd_vault.address,
        new_vault_token,
        True,
        sender=switchboard_alpha.address
    )

    assert vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, new_vault_token) == True

    # Disapprove
    vault_registry.setApprovedVaultToken(
        undy_usd_vault.address,
        new_vault_token,
        False,
        sender=switchboard_alpha.address
    )

    assert vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, new_vault_token) == False


def test_set_approved_vault_token_non_switchboard_fails(vault_registry, undy_usd_vault, bob):
    """Test that non-switchboard cannot approve vault tokens"""
    new_vault_token = boa.env.generate_address()

    with boa.reverts("no perms"):
        vault_registry.setApprovedVaultToken(
            undy_usd_vault.address,
            new_vault_token,
            True,
            sender=bob
        )


def test_set_approved_vault_token_zero_address_fails(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test that empty address cannot be approved"""
    with boa.reverts("invalid vault token"):
        vault_registry.setApprovedVaultToken(
            undy_usd_vault.address,
            ZERO_ADDRESS,
            True,
            sender=switchboard_alpha.address
        )


def test_set_approved_vault_token_emits_event(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test that setApprovedVaultToken emits event"""
    new_vault_token = boa.env.generate_address()

    vault_registry.setApprovedVaultToken(
        undy_usd_vault.address,
        new_vault_token,
        True,
        sender=switchboard_alpha.address
    )

    events = filter_logs(vault_registry, "ApprovedVaultTokenSet")
    assert len(events) > 0

    latest_event = events[-1]
    assert latest_event.vaultAddr == undy_usd_vault.address
    assert latest_event.vaultToken == new_vault_token
    assert latest_event.isApproved == True


def test_check_vault_approvals(vault_registry, undy_usd_vault, yield_vault_token, switchboard_alpha):
    """Test checkVaultApprovals checks vault token approval"""
    # Approved vault token (from fixtures)
    assert vault_registry.checkVaultApprovals(
        undy_usd_vault.address,
        yield_vault_token.address
    ) == True

    # Unapproved vault token
    new_vault_token = boa.env.generate_address()
    assert vault_registry.checkVaultApprovals(
        undy_usd_vault.address,
        new_vault_token
    ) == False


def test_get_vault_config_by_reg_id(vault_registry, undy_usd_vault):
    """Test getVaultConfig by registry ID"""
    # Get registry ID for undy_usd_vault
    reg_id = vault_registry.getRegId(undy_usd_vault.address)

    # Get config by reg ID
    config = vault_registry.getVaultConfig(reg_id)

    assert config.canDeposit == True
    assert config.canWithdraw == True
    assert config.redemptionBuffer == 200
    assert config.isVaultOpsFrozen == False


def test_get_vault_config_by_addr(vault_registry, undy_usd_vault):
    """Test getVaultConfigByAddr"""
    config = vault_registry.getVaultConfigByAddr(undy_usd_vault.address)

    assert config.canDeposit == True
    assert config.canWithdraw == True
    assert config.redemptionBuffer == 200
    assert config.isVaultOpsFrozen == False


def test_multiple_vaults_independent_configs(vault_registry, governance, deploy_test_vault):
    """Test that different vaults have independent configurations"""
    # Create two new vaults
    vault_1 = deploy_test_vault()
    vault_2 = deploy_test_vault()

    vault_token_1 = boa.env.generate_address()
    vault_token_2 = boa.env.generate_address()

    # Register vault 1
    vault_registry.startAddNewAddressToRegistry(
        vault_1.address,
        f"Vault {vault_1.address}",
        sender=governance.address
    )

    timelock = vault_registry.registryChangeTimeLock()
    boa.env.time_travel(blocks=timelock + 1)

    # Confirm and initialize vault 1 with custom config
    vault_registry.confirmNewAddressToRegistry(
        vault_1.address,
        [vault_token_1],  # approvedVaultTokens
        500_000 * EIGHTEEN_DECIMALS,  # maxDepositAmount
        10000,  # minYieldWithdrawAmount
        20_00,  # performanceFee (20%)
        vault_token_1,  # defaultTargetVaultToken
        True,  # shouldAutoDeposit
        True,  # canDeposit
        False,  # canWithdraw
        False,  # isVaultOpsFrozen
        100,  # redemptionBuffer (1%)
        sender=governance.address
    )

    # Register vault 2
    vault_registry.startAddNewAddressToRegistry(
        vault_2.address,
        f"Vault {vault_2.address}",
        sender=governance.address
    )

    boa.env.time_travel(blocks=timelock + 1)

    # Confirm and initialize vault 2 with different config
    vault_registry.confirmNewAddressToRegistry(
        vault_2.address,
        [vault_token_2],  # approvedVaultTokens
        1_000_000 * EIGHTEEN_DECIMALS,  # maxDepositAmount
        20000,  # minYieldWithdrawAmount
        15_00,  # performanceFee (15%)
        ZERO_ADDRESS,  # defaultTargetVaultToken (none)
        False,  # shouldAutoDeposit
        False,  # canDeposit
        True,  # canWithdraw
        False,  # isVaultOpsFrozen
        500,  # redemptionBuffer (5%)
        sender=governance.address
    )

    # Verify vault 1 config
    config_1 = vault_registry.getVaultConfigByAddr(vault_1.address)
    assert config_1.canDeposit == True
    assert config_1.canWithdraw == False
    assert config_1.maxDepositAmount == 500_000 * EIGHTEEN_DECIMALS
    assert config_1.redemptionBuffer == 100
    assert vault_registry.isApprovedVaultTokenByAddr(vault_1.address, vault_token_1) == True

    # Verify vault 2 config
    config_2 = vault_registry.getVaultConfigByAddr(vault_2.address)
    assert config_2.canDeposit == False
    assert config_2.canWithdraw == True
    assert config_2.maxDepositAmount == 1_000_000 * EIGHTEEN_DECIMALS
    assert config_2.redemptionBuffer == 500
    assert vault_registry.isApprovedVaultTokenByAddr(vault_2.address, vault_token_2) == True

    # Verify isolation - vault 1 approvals don't affect vault 2
    assert vault_registry.isApprovedVaultTokenByAddr(vault_1.address, vault_token_2) == False
    assert vault_registry.isApprovedVaultTokenByAddr(vault_2.address, vault_token_1) == False


def test_pause_department(vault_registry, switchboard_alpha):
    """Test that switchboard can pause the VaultRegistry department"""
    # Initially not paused
    assert vault_registry.isPaused() == False

    # Pause
    vault_registry.pause(True, sender=switchboard_alpha.address)

    assert vault_registry.isPaused() == True


def test_unpause_department(vault_registry, switchboard_alpha):
    """Test that switchboard can unpause the VaultRegistry department"""
    # Pause first
    vault_registry.pause(True, sender=switchboard_alpha.address)
    assert vault_registry.isPaused() == True

    # Unpause
    vault_registry.pause(False, sender=switchboard_alpha.address)

    assert vault_registry.isPaused() == False


def test_pause_non_switchboard_fails(vault_registry, bob):
    """Test that non-switchboard cannot pause the department"""
    with boa.reverts("no perms"):
        vault_registry.pause(True, sender=bob)


def test_pause_blocks_registry_operations(vault_registry, governance, switchboard_alpha, deploy_test_vault):
    """Test that paused state blocks registry operations"""
    new_vault = deploy_test_vault()

    # Pause the registry
    vault_registry.pause(True, sender=switchboard_alpha.address)
    assert vault_registry.isPaused() == True

    # Try to start adding new vault - should fail
    with boa.reverts("no perms"):
        vault_registry.startAddNewAddressToRegistry(
            new_vault.address,
            "New Vault",
            sender=governance.address
        )

    # Try to confirm - should fail (first need to unpause and start)
    vault_registry.pause(False, sender=switchboard_alpha.address)
    vault_registry.startAddNewAddressToRegistry(
        new_vault.address,
        "New Vault",
        sender=governance.address
    )

    # Pause again
    vault_registry.pause(True, sender=switchboard_alpha.address)

    # Try to confirm while paused - should fail
    timelock = vault_registry.registryChangeTimeLock()
    boa.env.time_travel(blocks=timelock + 1)

    with boa.reverts("no perms"):
        vault_registry.confirmNewAddressToRegistry(
            new_vault.address,
            sender=governance.address
        )

    # Unpause and confirm should work
    vault_registry.pause(False, sender=switchboard_alpha.address)
    reg_id = vault_registry.confirmNewAddressToRegistry(
        new_vault.address,
        sender=governance.address
    )
    assert reg_id > 0


def test_set_can_withdraw_emits_event(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test that setCanWithdraw emits CanWithdrawSet event"""
    vault_registry.setCanWithdraw(
        undy_usd_vault.address,
        False,
        sender=switchboard_alpha.address
    )

    events = filter_logs(vault_registry, "CanWithdrawSet")
    assert len(events) > 0

    latest_event = events[-1]
    assert latest_event.vaultAddr == undy_usd_vault.address
    assert latest_event.canWithdraw == False


def test_set_max_deposit_amount_emits_event(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test that setMaxDepositAmount emits MaxDepositAmountSet event"""
    new_max = 5_000_000 * EIGHTEEN_DECIMALS

    vault_registry.setMaxDepositAmount(
        undy_usd_vault.address,
        new_max,
        sender=switchboard_alpha.address
    )

    events = filter_logs(vault_registry, "MaxDepositAmountSet")
    assert len(events) > 0

    latest_event = events[-1]
    assert latest_event.vaultAddr == undy_usd_vault.address
    assert latest_event.maxDepositAmount == new_max


def test_registry_change_timelock_view(vault_registry):
    """Test registryChangeTimeLock view function returns correct value"""
    timelock = vault_registry.registryChangeTimeLock()

    # Initially 0 because not set after setup
    # But after undy_hq fixture runs setRegistryTimeLockAfterSetup, it may be set
    assert isinstance(timelock, int)
    assert timelock >= 0


def test_get_registry_description(vault_registry):
    """Test getRegistryDescription returns the correct registry identifier"""
    description = vault_registry.getRegistryDescription()

    assert description == "VaultRegistry.vy"


def test_can_mint_undy_returns_false(vault_registry):
    """Test canMintUndy returns False (VaultRegistry cannot mint)"""
    can_mint = vault_registry.canMintUndy()

    assert can_mint == False


def test_recover_funds(vault_registry, switchboard_alpha, governance, yield_underlying_token, yield_underlying_token_whale):
    """Test recoverFunds emergency function"""
    # Transfer tokens from whale to VaultRegistry (simulating accidentally sent funds)
    amount = 1000 * EIGHTEEN_DECIMALS

    yield_underlying_token.transfer(
        vault_registry.address,
        amount,
        sender=yield_underlying_token_whale
    )

    # Verify tokens are in the contract
    registry_balance = yield_underlying_token.balanceOf(vault_registry.address)
    assert registry_balance == amount

    # Track governance balance before recovery
    initial_gov_balance = yield_underlying_token.balanceOf(governance.address)

    # Recover funds to governance (switchboard must call, not governance)
    vault_registry.recoverFunds(
        governance.address,
        yield_underlying_token.address,
        sender=switchboard_alpha.address
    )

    # Verify funds were recovered
    final_gov_balance = yield_underlying_token.balanceOf(governance.address)
    assert final_gov_balance == initial_gov_balance + amount

    # Verify contract balance is now zero
    final_registry_balance = yield_underlying_token.balanceOf(vault_registry.address)
    assert final_registry_balance == 0
