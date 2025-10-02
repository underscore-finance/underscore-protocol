import pytest
import boa
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS
from conf_utils import filter_logs


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
            "contracts/vaults/UndyUsd.vy",
            mock_asset.address,  # asset - now a real ERC20 contract
            undy_hq_deploy.address,  # undyHq
            0,  # minHqTimeLock
            0,  # maxHqTimeLock
            boa.env.generate_address(),  # startingAgent
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


def test_set_can_deposit_no_change_reverts(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test that setting same value reverts"""
    # Initially True
    assert vault_registry.canDeposit(undy_usd_vault.address) == True

    # Try to set to True again
    with boa.reverts("nothing to change"):
        vault_registry.setCanDeposit(
            undy_usd_vault.address,
            True,
            sender=switchboard_alpha.address
        )


def test_set_can_deposit_emits_event(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test that setCanDeposit emits VaultConfigSet event"""
    vault_registry.setCanDeposit(
        undy_usd_vault.address,
        False,
        sender=switchboard_alpha.address
    )

    events = filter_logs(vault_registry, "VaultConfigSet")
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


def test_set_can_withdraw_no_change_reverts(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test that setting same value reverts"""
    # Initially True
    assert vault_registry.canWithdraw(undy_usd_vault.address) == True

    # Try to set to True again
    with boa.reverts("nothing to change"):
        vault_registry.setCanWithdraw(
            undy_usd_vault.address,
            True,
            sender=switchboard_alpha.address
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


def test_set_max_deposit_amount_no_change_reverts(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test that setting same value reverts"""
    # Initially 0
    assert vault_registry.maxDepositAmount(undy_usd_vault.address) == 0

    # Try to set to 0 again
    with boa.reverts("nothing to change"):
        vault_registry.setMaxDepositAmount(
            undy_usd_vault.address,
            0,
            sender=switchboard_alpha.address
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


def test_set_vault_ops_frozen_no_change_reverts(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test that setting same value reverts"""
    # Initially False
    assert vault_registry.isVaultOpsFrozen(undy_usd_vault.address) == False

    # Try to set to False again
    with boa.reverts("nothing to change"):
        vault_registry.setVaultOpsFrozen(
            undy_usd_vault.address,
            False,
            sender=switchboard_alpha.address
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
    with boa.reverts("buffer too high (max 10%)"):
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


def test_set_snapshot_price_config(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test setting snapshot price config"""
    # Get initial config
    initial_config = vault_registry.snapShotPriceConfig(undy_usd_vault.address)
    assert initial_config.minSnapshotDelay == 300
    assert initial_config.maxNumSnapshots == 20

    # Create new config - pass as tuple matching SnapShotPriceConfig struct
    # (minSnapshotDelay, maxNumSnapshots, maxUpsideDeviation, staleTime)
    new_config = (600, 15, 2000, 86400)

    vault_registry.setSnapShotPriceConfig(
        undy_usd_vault.address,
        new_config,
        sender=switchboard_alpha.address
    )

    # Verify new config
    updated_config = vault_registry.snapShotPriceConfig(undy_usd_vault.address)
    assert updated_config.minSnapshotDelay == 600
    assert updated_config.maxNumSnapshots == 15
    assert updated_config.maxUpsideDeviation == 2000
    assert updated_config.staleTime == 86400


def test_set_snapshot_price_config_non_switchboard_fails(vault_registry, undy_usd_vault, bob):
    """Test that non-switchboard cannot set snapshot config"""
    new_config = (600, 15, 2000, 86400)

    with boa.reverts("no perms"):
        vault_registry.setSnapShotPriceConfig(
            undy_usd_vault.address,
            new_config,
            sender=bob
        )


def test_set_snapshot_price_config_invalid_min_delay(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test that minSnapshotDelay > ONE_WEEK fails"""
    # (minSnapshotDelay > 1 week, maxNumSnapshots, maxUpsideDeviation, staleTime)
    invalid_config = (60 * 60 * 24 * 7 + 1, 15, 1000, 86400)

    with boa.reverts("invalid config"):
        vault_registry.setSnapShotPriceConfig(
            undy_usd_vault.address,
            invalid_config,
            sender=switchboard_alpha.address
        )


def test_set_snapshot_price_config_invalid_max_snapshots(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test that maxNumSnapshots must be 1-25"""
    # Zero should fail
    invalid_config_zero = (300, 0, 1000, 86400)

    with boa.reverts("invalid config"):
        vault_registry.setSnapShotPriceConfig(
            undy_usd_vault.address,
            invalid_config_zero,
            sender=switchboard_alpha.address
        )

    # > 25 should fail
    invalid_config_too_many = (300, 26, 1000, 86400)

    with boa.reverts("invalid config"):
        vault_registry.setSnapShotPriceConfig(
            undy_usd_vault.address,
            invalid_config_too_many,
            sender=switchboard_alpha.address
        )

    # 25 should work
    valid_config = (300, 25, 1000, 86400)

    vault_registry.setSnapShotPriceConfig(
        undy_usd_vault.address,
        valid_config,
        sender=switchboard_alpha.address
    )

    config = vault_registry.snapShotPriceConfig(undy_usd_vault.address)
    assert config.maxNumSnapshots == 25


def test_set_snapshot_price_config_invalid_upside_deviation(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test that maxUpsideDeviation > 100% fails"""
    # (minSnapshotDelay, maxNumSnapshots, maxUpsideDeviation > 100%, staleTime)
    invalid_config = (300, 15, 10001, 86400)

    with boa.reverts("invalid config"):
        vault_registry.setSnapShotPriceConfig(
            undy_usd_vault.address,
            invalid_config,
            sender=switchboard_alpha.address
        )

    # 100% should work
    valid_config = (300, 15, 10000, 86400)

    vault_registry.setSnapShotPriceConfig(
        undy_usd_vault.address,
        valid_config,
        sender=switchboard_alpha.address
    )

    config = vault_registry.snapShotPriceConfig(undy_usd_vault.address)
    assert config.maxUpsideDeviation == 10000


def test_set_snapshot_price_config_invalid_stale_time(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test that staleTime >= ONE_WEEK fails"""
    # (minSnapshotDelay, maxNumSnapshots, maxUpsideDeviation, staleTime >= 1 week)
    invalid_config = (300, 15, 1000, 60 * 60 * 24 * 7)

    with boa.reverts("invalid config"):
        vault_registry.setSnapShotPriceConfig(
            undy_usd_vault.address,
            invalid_config,
            sender=switchboard_alpha.address
        )

    # Just under 1 week should work
    valid_config = (300, 15, 1000, 60 * 60 * 24 * 7 - 1)

    vault_registry.setSnapShotPriceConfig(
        undy_usd_vault.address,
        valid_config,
        sender=switchboard_alpha.address
    )

    config = vault_registry.snapShotPriceConfig(undy_usd_vault.address)
    assert config.staleTime == 60 * 60 * 24 * 7 - 1


def test_set_snapshot_price_config_emits_event(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test that setSnapShotPriceConfig emits event"""
    new_config = (600, 15, 2000, 86400)

    vault_registry.setSnapShotPriceConfig(
        undy_usd_vault.address,
        new_config,
        sender=switchboard_alpha.address
    )

    events = filter_logs(vault_registry, "SnapShotPriceConfigSet")
    assert len(events) > 0

    latest_event = events[-1]
    assert latest_event.vaultAddr == undy_usd_vault.address
    assert latest_event.minSnapshotDelay == 600
    assert latest_event.maxNumSnapshots == 15
    assert latest_event.maxUpsideDeviation == 2000
    assert latest_event.staleTime == 86400


def test_is_valid_price_config_view(vault_registry):
    """Test isValidPriceConfig view function"""
    # Valid config
    valid_config = (300, 20, 1000, 259200)  # 3 days
    assert vault_registry.isValidPriceConfig(valid_config) == True

    # Invalid: minSnapshotDelay too high
    invalid_delay = (60 * 60 * 24 * 8, 20, 1000, 259200)
    assert vault_registry.isValidPriceConfig(invalid_delay) == False

    # Invalid: maxNumSnapshots = 0
    invalid_snapshots = (300, 0, 1000, 259200)
    assert vault_registry.isValidPriceConfig(invalid_snapshots) == False

    # Invalid: maxUpsideDeviation too high
    invalid_deviation = (300, 20, 20000, 259200)
    assert vault_registry.isValidPriceConfig(invalid_deviation) == False

    # Invalid: staleTime too high
    invalid_stale = (300, 20, 1000, 60 * 60 * 24 * 7)
    assert vault_registry.isValidPriceConfig(invalid_stale) == False


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


def test_set_approved_vault_token_no_change_reverts(vault_registry, undy_usd_vault, switchboard_alpha, yield_vault_token):
    """Test that setting same approval state reverts"""
    # yield_vault_token is already approved in fixtures
    assert vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, yield_vault_token.address) == True

    with boa.reverts("nothing to change"):
        vault_registry.setApprovedVaultToken(
            undy_usd_vault.address,
            yield_vault_token.address,
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


def test_set_approved_yield_lego(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test approving and disapproving yield legos"""
    # Lego ID 5 not approved initially
    assert vault_registry.isApprovedYieldLegoByAddr(undy_usd_vault.address, 5) == False

    # Approve
    vault_registry.setApprovedYieldLego(
        undy_usd_vault.address,
        5,
        True,
        sender=switchboard_alpha.address
    )

    assert vault_registry.isApprovedYieldLegoByAddr(undy_usd_vault.address, 5) == True

    # Disapprove
    vault_registry.setApprovedYieldLego(
        undy_usd_vault.address,
        5,
        False,
        sender=switchboard_alpha.address
    )

    assert vault_registry.isApprovedYieldLegoByAddr(undy_usd_vault.address, 5) == False


def test_set_approved_yield_lego_non_switchboard_fails(vault_registry, undy_usd_vault, bob):
    """Test that non-switchboard cannot approve yield legos"""
    with boa.reverts("no perms"):
        vault_registry.setApprovedYieldLego(
            undy_usd_vault.address,
            5,
            True,
            sender=bob
        )


def test_set_approved_yield_lego_zero_id_fails(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test that lego ID 0 cannot be approved"""
    with boa.reverts("invalid lego id"):
        vault_registry.setApprovedYieldLego(
            undy_usd_vault.address,
            0,
            True,
            sender=switchboard_alpha.address
        )


def test_set_approved_yield_lego_no_change_reverts(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test that setting same approval state reverts"""
    # Lego ID 1 is already approved in fixtures
    assert vault_registry.isApprovedYieldLegoByAddr(undy_usd_vault.address, 1) == True

    with boa.reverts("nothing to change"):
        vault_registry.setApprovedYieldLego(
            undy_usd_vault.address,
            1,
            True,
            sender=switchboard_alpha.address
        )


def test_set_approved_yield_lego_emits_event(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test that setApprovedYieldLego emits event"""
    vault_registry.setApprovedYieldLego(
        undy_usd_vault.address,
        5,
        True,
        sender=switchboard_alpha.address
    )

    events = filter_logs(vault_registry, "ApprovedYieldLegoSet")
    assert len(events) > 0

    latest_event = events[-1]
    assert latest_event.vaultAddr == undy_usd_vault.address
    assert latest_event.legoId == 5
    assert latest_event.isApproved == True


def test_check_vault_approvals(vault_registry, undy_usd_vault, yield_vault_token, switchboard_alpha):
    """Test checkVaultApprovals combined check"""
    # Both approved (from fixtures)
    assert vault_registry.checkVaultApprovals(
        undy_usd_vault.address,
        1,  # Approved lego
        yield_vault_token.address  # Approved vault token
    ) == True

    # Approved lego, unapproved vault token
    new_vault_token = boa.env.generate_address()
    assert vault_registry.checkVaultApprovals(
        undy_usd_vault.address,
        1,  # Approved lego
        new_vault_token  # Not approved vault token
    ) == False

    # Unapproved lego, approved vault token
    assert vault_registry.checkVaultApprovals(
        undy_usd_vault.address,
        99,  # Not approved lego
        yield_vault_token.address  # Approved vault token
    ) == False

    # Both unapproved
    assert vault_registry.checkVaultApprovals(
        undy_usd_vault.address,
        99,  # Not approved lego
        new_vault_token  # Not approved vault token
    ) == False


def test_initialize_vault_config(vault_registry, governance, switchboard_alpha, deploy_test_vault):
    """Test initializing vault config for a new vault"""
    # Deploy a real vault contract
    new_vault = deploy_test_vault()

    # First register the vault
    vault_registry.startAddNewAddressToRegistry(
        new_vault.address,
        "New Vault",
        sender=governance.address
    )

    timelock = vault_registry.registryChangeTimeLock()
    boa.env.time_travel(blocks=timelock + 1)

    vault_registry.confirmNewAddressToRegistry(
        new_vault.address,
        sender=governance.address
    )

    # Create vault tokens to approve
    vault_token_1 = boa.env.generate_address()
    vault_token_2 = boa.env.generate_address()

    # Initialize vault config
    # Snapshot config: (minSnapshotDelay, maxNumSnapshots, maxUpsideDeviation, staleTime)
    snap_config = (300, 20, 1000, 259200)

    vault_registry.initializeVaultConfig(
        new_vault.address,
        True,  # canDeposit
        True,  # canWithdraw
        1_000_000 * EIGHTEEN_DECIMALS,  # maxDepositAmount
        300,  # redemptionBuffer (3%)
        snap_config,
        [vault_token_1, vault_token_2],  # approvedVaultTokens
        [1, 2],  # approvedYieldLegos
        sender=switchboard_alpha.address
    )

    # Verify config was set
    config = vault_registry.getVaultConfigByAddr(new_vault.address)
    assert config.canDeposit == True
    assert config.canWithdraw == True
    assert config.maxDepositAmount == 1_000_000 * EIGHTEEN_DECIMALS
    assert config.redemptionBuffer == 300
    assert config.isVaultOpsFrozen == False

    # Verify snapshot config
    assert config.snapShotPriceConfig.minSnapshotDelay == 300
    assert config.snapShotPriceConfig.maxNumSnapshots == 20

    # Verify approvals
    assert vault_registry.isApprovedVaultTokenByAddr(new_vault.address, vault_token_1) == True
    assert vault_registry.isApprovedVaultTokenByAddr(new_vault.address, vault_token_2) == True
    assert vault_registry.isApprovedYieldLegoByAddr(new_vault.address, 1) == True
    assert vault_registry.isApprovedYieldLegoByAddr(new_vault.address, 2) == True


def test_initialize_vault_config_non_switchboard_fails(vault_registry, bob, deploy_test_vault):
    """Test that non-switchboard cannot initialize vault config"""
    new_vault = deploy_test_vault()

    snap_config = (300, 20, 1000, 259200)

    with boa.reverts("no perms"):
        vault_registry.initializeVaultConfig(
            new_vault.address,
            True,
            True,
            0,
            200,
            snap_config,
            [],
            [],
            sender=bob
        )


def test_initialize_vault_config_invalid_vault_addr(vault_registry, switchboard_alpha):
    """Test that unregistered vault cannot be initialized"""
    random_vault = boa.env.generate_address()

    snap_config = (300, 20, 1000, 259200)

    with boa.reverts("invalid vault addr"):
        vault_registry.initializeVaultConfig(
            random_vault,
            True,
            True,
            0,
            200,
            snap_config,
            [],
            [],
            sender=switchboard_alpha.address
        )


def test_initialize_vault_config_invalid_price_config(vault_registry, governance, switchboard_alpha, deploy_test_vault):
    """Test that invalid price config is rejected"""
    new_vault = deploy_test_vault()

    # Register the vault
    vault_registry.startAddNewAddressToRegistry(
        new_vault.address,
        "New Vault",
        sender=governance.address
    )

    timelock = vault_registry.registryChangeTimeLock()
    boa.env.time_travel(blocks=timelock + 1)

    vault_registry.confirmNewAddressToRegistry(
        new_vault.address,
        sender=governance.address
    )

    # Invalid config: maxNumSnapshots = 0
    invalid_snap_config = (300, 0, 1000, 259200)

    with boa.reverts("invalid price config"):
        vault_registry.initializeVaultConfig(
            new_vault.address,
            True,
            True,
            0,
            200,
            invalid_snap_config,
            [],
            [],
            sender=switchboard_alpha.address
        )


def test_initialize_vault_config_buffer_too_high(vault_registry, governance, switchboard_alpha, deploy_test_vault):
    """Test that buffer > 10% is rejected"""
    new_vault = deploy_test_vault()

    # Register the vault
    vault_registry.startAddNewAddressToRegistry(
        new_vault.address,
        "New Vault",
        sender=governance.address
    )

    timelock = vault_registry.registryChangeTimeLock()
    boa.env.time_travel(blocks=timelock + 1)

    vault_registry.confirmNewAddressToRegistry(
        new_vault.address,
        sender=governance.address
    )

    snap_config = (300, 20, 1000, 259200)

    with boa.reverts("buffer too high (max 10%)"):
        vault_registry.initializeVaultConfig(
            new_vault.address,
            True,
            True,
            0,
            1001,  # 10.01%
            snap_config,
            [],
            [],
            sender=switchboard_alpha.address
        )


def test_initialize_vault_config_skips_empty_vault_tokens(vault_registry, governance, switchboard_alpha, deploy_test_vault):
    """Test that empty addresses in vault tokens are skipped"""
    new_vault = deploy_test_vault()

    # Register the vault
    vault_registry.startAddNewAddressToRegistry(
        new_vault.address,
        "New Vault",
        sender=governance.address
    )

    timelock = vault_registry.registryChangeTimeLock()
    boa.env.time_travel(blocks=timelock + 1)

    vault_registry.confirmNewAddressToRegistry(
        new_vault.address,
        sender=governance.address
    )

    vault_token_1 = boa.env.generate_address()

    snap_config = (300, 20, 1000, 259200)

    # Include ZERO_ADDRESS in the list
    vault_registry.initializeVaultConfig(
        new_vault.address,
        True,
        True,
        0,
        200,
        snap_config,
        [vault_token_1, ZERO_ADDRESS],  # Should skip empty address
        [],
        sender=switchboard_alpha.address
    )

    # Only vault_token_1 should be approved
    assert vault_registry.isApprovedVaultTokenByAddr(new_vault.address, vault_token_1) == True
    assert vault_registry.isApprovedVaultTokenByAddr(new_vault.address, ZERO_ADDRESS) == False


def test_initialize_vault_config_skips_zero_lego_ids(vault_registry, governance, switchboard_alpha, deploy_test_vault):
    """Test that lego ID 0 in list is skipped"""
    new_vault = deploy_test_vault()

    # Register the vault
    vault_registry.startAddNewAddressToRegistry(
        new_vault.address,
        "New Vault",
        sender=governance.address
    )

    timelock = vault_registry.registryChangeTimeLock()
    boa.env.time_travel(blocks=timelock + 1)

    vault_registry.confirmNewAddressToRegistry(
        new_vault.address,
        sender=governance.address
    )

    snap_config = (300, 20, 1000, 259200)

    # Include 0 in the lego IDs
    vault_registry.initializeVaultConfig(
        new_vault.address,
        True,
        True,
        0,
        200,
        snap_config,
        [],
        [1, 0, 2],  # Should skip 0
        sender=switchboard_alpha.address
    )

    # Only 1 and 2 should be approved
    assert vault_registry.isApprovedYieldLegoByAddr(new_vault.address, 1) == True
    assert vault_registry.isApprovedYieldLegoByAddr(new_vault.address, 2) == True
    assert vault_registry.isApprovedYieldLegoByAddr(new_vault.address, 0) == False


def test_initialize_vault_config_emits_all_events(vault_registry, governance, switchboard_alpha, deploy_test_vault):
    """Test that initializeVaultConfig emits all required events"""
    new_vault = deploy_test_vault()

    # Register the vault
    vault_registry.startAddNewAddressToRegistry(
        new_vault.address,
        "New Vault",
        sender=governance.address
    )

    timelock = vault_registry.registryChangeTimeLock()
    boa.env.time_travel(blocks=timelock + 1)

    vault_registry.confirmNewAddressToRegistry(
        new_vault.address,
        sender=governance.address
    )

    vault_token_1 = boa.env.generate_address()

    snap_config = (300, 20, 1000, 259200)

    vault_registry.initializeVaultConfig(
        new_vault.address,
        True,
        True,
        1_000_000 * EIGHTEEN_DECIMALS,
        200,
        snap_config,
        [vault_token_1],
        [1],
        sender=switchboard_alpha.address
    )

    # Should have VaultConfigSet event
    config_events = filter_logs(vault_registry, "VaultConfigSet")
    assert len(config_events) > 0
    assert config_events[-1].vaultAddr == new_vault.address

    # Should have RedemptionBufferSet event
    buffer_events = filter_logs(vault_registry, "RedemptionBufferSet")
    assert len(buffer_events) > 0
    assert buffer_events[-1].vaultAddr == new_vault.address

    # Should have SnapShotPriceConfigSet event
    snapshot_events = filter_logs(vault_registry, "SnapShotPriceConfigSet")
    assert len(snapshot_events) > 0
    assert snapshot_events[-1].vaultAddr == new_vault.address

    # Should have ApprovedVaultTokenSet event
    token_events = filter_logs(vault_registry, "ApprovedVaultTokenSet")
    assert len(token_events) > 0

    # Should have ApprovedYieldLegoSet event
    lego_events = filter_logs(vault_registry, "ApprovedYieldLegoSet")
    assert len(lego_events) > 0


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
    assert config.snapShotPriceConfig.minSnapshotDelay == 300
    assert config.snapShotPriceConfig.maxNumSnapshots == 20


def test_multiple_vaults_independent_configs(vault_registry, governance, switchboard_alpha, deploy_test_vault):
    """Test that different vaults have independent configurations"""
    # Create two new vaults
    vault_1 = deploy_test_vault()
    vault_2 = deploy_test_vault()

    # Register both
    for vault in [vault_1, vault_2]:
        vault_registry.startAddNewAddressToRegistry(
            vault.address,
            f"Vault {vault.address}",
            sender=governance.address
        )

    timelock = vault_registry.registryChangeTimeLock()
    boa.env.time_travel(blocks=timelock + 1)

    for vault in [vault_1, vault_2]:
        vault_registry.confirmNewAddressToRegistry(
            vault.address,
            sender=governance.address
        )

    # Initialize with different configs
    snap_config_1 = (300, 20, 1000, 259200)
    snap_config_2 = (600, 15, 500, 86400)

    vault_token_1 = boa.env.generate_address()
    vault_token_2 = boa.env.generate_address()

    vault_registry.initializeVaultConfig(
        vault_1.address,
        True,  # canDeposit
        False,  # canWithdraw
        500_000 * EIGHTEEN_DECIMALS,
        100,  # 1% buffer
        snap_config_1,
        [vault_token_1],
        [1],
        sender=switchboard_alpha.address
    )

    vault_registry.initializeVaultConfig(
        vault_2.address,
        False,  # canDeposit
        True,  # canWithdraw
        1_000_000 * EIGHTEEN_DECIMALS,
        500,  # 5% buffer
        snap_config_2,
        [vault_token_2],
        [2],
        sender=switchboard_alpha.address
    )

    # Verify vault 1 config
    config_1 = vault_registry.getVaultConfigByAddr(vault_1.address)
    assert config_1.canDeposit == True
    assert config_1.canWithdraw == False
    assert config_1.maxDepositAmount == 500_000 * EIGHTEEN_DECIMALS
    assert config_1.redemptionBuffer == 100
    assert config_1.snapShotPriceConfig.minSnapshotDelay == 300
    assert vault_registry.isApprovedVaultTokenByAddr(vault_1.address, vault_token_1) == True
    assert vault_registry.isApprovedYieldLegoByAddr(vault_1.address, 1) == True

    # Verify vault 2 config
    config_2 = vault_registry.getVaultConfigByAddr(vault_2.address)
    assert config_2.canDeposit == False
    assert config_2.canWithdraw == True
    assert config_2.maxDepositAmount == 1_000_000 * EIGHTEEN_DECIMALS
    assert config_2.redemptionBuffer == 500
    assert config_2.snapShotPriceConfig.minSnapshotDelay == 600
    assert vault_registry.isApprovedVaultTokenByAddr(vault_2.address, vault_token_2) == True
    assert vault_registry.isApprovedYieldLegoByAddr(vault_2.address, 2) == True

    # Verify isolation - vault 1 approvals don't affect vault 2
    assert vault_registry.isApprovedVaultTokenByAddr(vault_1.address, vault_token_2) == False
    assert vault_registry.isApprovedVaultTokenByAddr(vault_2.address, vault_token_1) == False
    assert vault_registry.isApprovedYieldLegoByAddr(vault_1.address, 2) == False
    assert vault_registry.isApprovedYieldLegoByAddr(vault_2.address, 1) == False


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
    """Test that setCanWithdraw emits VaultConfigSet event"""
    vault_registry.setCanWithdraw(
        undy_usd_vault.address,
        False,
        sender=switchboard_alpha.address
    )

    events = filter_logs(vault_registry, "VaultConfigSet")
    assert len(events) > 0

    latest_event = events[-1]
    assert latest_event.vaultAddr == undy_usd_vault.address
    assert latest_event.canWithdraw == False


def test_set_max_deposit_amount_emits_event(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test that setMaxDepositAmount emits VaultConfigSet event"""
    new_max = 5_000_000 * EIGHTEEN_DECIMALS

    vault_registry.setMaxDepositAmount(
        undy_usd_vault.address,
        new_max,
        sender=switchboard_alpha.address
    )

    events = filter_logs(vault_registry, "VaultConfigSet")
    assert len(events) > 0

    latest_event = events[-1]
    assert latest_event.vaultAddr == undy_usd_vault.address
    assert latest_event.maxDepositAmount == new_max


def test_vault_config_set_event_all_fields(vault_registry, undy_usd_vault, switchboard_alpha):
    """Test that VaultConfigSet event contains all expected fields"""
    # Change canDeposit to trigger event
    vault_registry.setCanDeposit(
        undy_usd_vault.address,
        False,
        sender=switchboard_alpha.address
    )

    events = filter_logs(vault_registry, "VaultConfigSet")
    assert len(events) > 0

    latest_event = events[-1]
    # Verify all fields are present
    assert hasattr(latest_event, 'vaultAddr')
    assert hasattr(latest_event, 'canDeposit')
    assert hasattr(latest_event, 'canWithdraw')
    assert hasattr(latest_event, 'maxDepositAmount')

    # Verify field values
    assert latest_event.vaultAddr == undy_usd_vault.address
    assert latest_event.canDeposit == False
    assert latest_event.canWithdraw == True  # unchanged
    assert latest_event.maxDepositAmount == 0  # unchanged from fixture


def test_initialize_vault_config_pending_vault(vault_registry, governance, switchboard_alpha, deploy_test_vault):
    """Test initializing vault config for a vault in pending state (not yet confirmed)"""
    new_vault = deploy_test_vault()

    # Start registration but DON'T confirm yet
    vault_registry.startAddNewAddressToRegistry(
        new_vault.address,
        "Pending Vault",
        sender=governance.address
    )

    # Verify it's pending
    pending = vault_registry.pendingNewAddr(new_vault.address)
    assert pending.confirmBlock > 0

    # Should be able to initialize config even when pending
    snap_config = (300, 20, 1000, 259200)
    vault_token = boa.env.generate_address()

    vault_registry.initializeVaultConfig(
        new_vault.address,
        True,
        True,
        1_000_000 * EIGHTEEN_DECIMALS,
        200,
        snap_config,
        [vault_token],
        [1],
        sender=switchboard_alpha.address
    )

    # Verify config was set
    config = vault_registry.getVaultConfigByAddr(new_vault.address)
    assert config.canDeposit == True
    assert config.maxDepositAmount == 1_000_000 * EIGHTEEN_DECIMALS
    assert vault_registry.isApprovedVaultTokenByAddr(new_vault.address, vault_token) == True


def test_initialize_vault_config_overwrite(vault_registry, governance, switchboard_alpha, deploy_test_vault):
    """Test that re-initializing an already initialized vault overwrites the config"""
    new_vault = deploy_test_vault()

    # Register vault
    vault_registry.startAddNewAddressToRegistry(
        new_vault.address,
        "New Vault",
        sender=governance.address
    )

    timelock = vault_registry.registryChangeTimeLock()
    boa.env.time_travel(blocks=timelock + 1)

    vault_registry.confirmNewAddressToRegistry(
        new_vault.address,
        sender=governance.address
    )

    # Initialize with first config
    snap_config_1 = (300, 20, 1000, 259200)
    vault_token_1 = boa.env.generate_address()

    vault_registry.initializeVaultConfig(
        new_vault.address,
        True,
        False,
        500_000 * EIGHTEEN_DECIMALS,
        100,
        snap_config_1,
        [vault_token_1],
        [1],
        sender=switchboard_alpha.address
    )

    # Verify first config
    config_1 = vault_registry.getVaultConfigByAddr(new_vault.address)
    assert config_1.canDeposit == True
    assert config_1.canWithdraw == False
    assert config_1.maxDepositAmount == 500_000 * EIGHTEEN_DECIMALS
    assert config_1.redemptionBuffer == 100

    # Re-initialize with different config (should overwrite)
    snap_config_2 = (600, 15, 500, 86400)
    vault_token_2 = boa.env.generate_address()

    vault_registry.initializeVaultConfig(
        new_vault.address,
        False,
        True,
        2_000_000 * EIGHTEEN_DECIMALS,
        500,
        snap_config_2,
        [vault_token_2],
        [2],
        sender=switchboard_alpha.address
    )

    # Verify config was overwritten
    config_2 = vault_registry.getVaultConfigByAddr(new_vault.address)
    assert config_2.canDeposit == False  # Changed
    assert config_2.canWithdraw == True  # Changed
    assert config_2.maxDepositAmount == 2_000_000 * EIGHTEEN_DECIMALS  # Changed
    assert config_2.redemptionBuffer == 500  # Changed
    assert config_2.snapShotPriceConfig.minSnapshotDelay == 600  # Changed

    # Old approvals should still exist (not cleared)
    assert vault_registry.isApprovedVaultTokenByAddr(new_vault.address, vault_token_1) == True
    # New approvals should be added
    assert vault_registry.isApprovedVaultTokenByAddr(new_vault.address, vault_token_2) == True
    assert vault_registry.isApprovedYieldLegoByAddr(new_vault.address, 1) == True
    assert vault_registry.isApprovedYieldLegoByAddr(new_vault.address, 2) == True


def test_initialize_vault_config_max_arrays(vault_registry, governance, switchboard_alpha, deploy_test_vault):
    """Test initializing vault config with maximum DynArray sizes (25 tokens, 25 legos)"""
    new_vault = deploy_test_vault()

    # Register vault
    vault_registry.startAddNewAddressToRegistry(
        new_vault.address,
        "Max Arrays Vault",
        sender=governance.address
    )

    timelock = vault_registry.registryChangeTimeLock()
    boa.env.time_travel(blocks=timelock + 1)

    vault_registry.confirmNewAddressToRegistry(
        new_vault.address,
        sender=governance.address
    )

    # Create 25 vault tokens (max DynArray size)
    vault_tokens = [boa.env.generate_address() for _ in range(25)]

    # Create 25 lego IDs (max DynArray size)
    lego_ids = list(range(1, 26))  # IDs 1-25

    snap_config = (300, 20, 1000, 259200)

    # Should succeed with max arrays
    vault_registry.initializeVaultConfig(
        new_vault.address,
        True,
        True,
        1_000_000 * EIGHTEEN_DECIMALS,
        200,
        snap_config,
        vault_tokens,
        lego_ids,
        sender=switchboard_alpha.address
    )

    # Verify all tokens were approved
    for token in vault_tokens:
        assert vault_registry.isApprovedVaultTokenByAddr(new_vault.address, token) == True

    # Verify all legos were approved
    for lego_id in lego_ids:
        assert vault_registry.isApprovedYieldLegoByAddr(new_vault.address, lego_id) == True


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
