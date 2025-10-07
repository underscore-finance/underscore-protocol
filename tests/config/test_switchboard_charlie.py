import pytest
import boa
from conf_utils import filter_logs
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS


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
            mock_asset.address,  # asset
            undy_hq_deploy.address,  # undyHq
            0,  # minHqTimeLock
            0,  # maxHqTimeLock
            boa.env.generate_address(),  # startingAgent
        )
    return _deploy


def test_set_can_deposit_disable_by_security_action(switchboard_charlie, vault_registry, undy_usd_vault, mission_control, switchboard_alpha, alice):
    """Test that security action users can disable deposits"""
    # Setup alice as security action user
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)

    # Initially deposits are enabled
    assert vault_registry.canDeposit(undy_usd_vault.address) == True

    # Alice (security action user) disables deposits
    switchboard_charlie.setCanDeposit(undy_usd_vault.address, False, sender=alice)

    # Verify deposits are disabled
    assert vault_registry.canDeposit(undy_usd_vault.address) == False

    # Verify event was emitted
    logs = filter_logs(switchboard_charlie, "CanDepositSet")
    assert len(logs) >= 1
    assert logs[-1].vaultAddr == undy_usd_vault.address
    assert logs[-1].canDeposit == False
    assert logs[-1].caller == alice


def test_set_can_deposit_enable_requires_governance(switchboard_charlie, vault_registry, undy_usd_vault, mission_control, switchboard_alpha, alice, governance):
    """Test that enabling deposits requires governance, security action users cannot enable"""
    # Setup alice as security action user
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)

    # Disable deposits first
    switchboard_charlie.setCanDeposit(undy_usd_vault.address, False, sender=governance.address)
    assert vault_registry.canDeposit(undy_usd_vault.address) == False

    # Alice (security action user) tries to enable deposits - should fail
    with boa.reverts("no perms"):
        switchboard_charlie.setCanDeposit(undy_usd_vault.address, True, sender=alice)

    # Governance can enable
    switchboard_charlie.setCanDeposit(undy_usd_vault.address, True, sender=governance.address)
    assert vault_registry.canDeposit(undy_usd_vault.address) == True


def test_set_can_deposit_governance_can_do_both(switchboard_charlie, vault_registry, undy_usd_vault, governance):
    """Test that governance can both enable and disable deposits"""
    # Governance disables
    switchboard_charlie.setCanDeposit(undy_usd_vault.address, False, sender=governance.address)
    assert vault_registry.canDeposit(undy_usd_vault.address) == False

    # Governance enables
    switchboard_charlie.setCanDeposit(undy_usd_vault.address, True, sender=governance.address)
    assert vault_registry.canDeposit(undy_usd_vault.address) == True


def test_set_can_deposit_unauthorized_fails(switchboard_charlie, undy_usd_vault, alice):
    """Test that unauthorized users cannot set canDeposit"""
    with boa.reverts("no perms"):
        switchboard_charlie.setCanDeposit(undy_usd_vault.address, False, sender=alice)


def test_set_can_withdraw_disable_by_security_action(switchboard_charlie, vault_registry, undy_usd_vault, mission_control, switchboard_alpha, alice):
    """Test that security action users can disable withdrawals"""
    # Setup alice as security action user
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)

    # Initially withdrawals are enabled
    assert vault_registry.canWithdraw(undy_usd_vault.address) == True

    # Alice (security action user) disables withdrawals
    switchboard_charlie.setCanWithdraw(undy_usd_vault.address, False, sender=alice)

    # Verify withdrawals are disabled
    assert vault_registry.canWithdraw(undy_usd_vault.address) == False

    # Verify event was emitted
    logs = filter_logs(switchboard_charlie, "CanWithdrawSet")
    assert len(logs) >= 1
    assert logs[-1].vaultAddr == undy_usd_vault.address
    assert logs[-1].canWithdraw == False
    assert logs[-1].caller == alice


def test_set_can_withdraw_enable_requires_governance(switchboard_charlie, vault_registry, undy_usd_vault, mission_control, switchboard_alpha, alice, governance):
    """Test that enabling withdrawals requires governance"""
    # Setup alice as security action user
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)

    # Disable withdrawals first
    switchboard_charlie.setCanWithdraw(undy_usd_vault.address, False, sender=governance.address)
    assert vault_registry.canWithdraw(undy_usd_vault.address) == False

    # Alice tries to enable - should fail
    with boa.reverts("no perms"):
        switchboard_charlie.setCanWithdraw(undy_usd_vault.address, True, sender=alice)

    # Governance can enable
    switchboard_charlie.setCanWithdraw(undy_usd_vault.address, True, sender=governance.address)
    assert vault_registry.canWithdraw(undy_usd_vault.address) == True


def test_set_can_withdraw_unauthorized_fails(switchboard_charlie, undy_usd_vault, alice):
    """Test that unauthorized users cannot set canWithdraw"""
    with boa.reverts("no perms"):
        switchboard_charlie.setCanWithdraw(undy_usd_vault.address, False, sender=alice)


def test_set_vault_ops_frozen_by_security_action(switchboard_charlie, vault_registry, undy_usd_vault, mission_control, switchboard_alpha, alice):
    """Test that security action users can freeze vault ops"""
    # Setup alice as security action user
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)

    # Initially not frozen
    assert vault_registry.isVaultOpsFrozen(undy_usd_vault.address) == False

    # Alice (security action user) freezes vault ops
    switchboard_charlie.setVaultOpsFrozen(undy_usd_vault.address, True, sender=alice)

    # Verify vault ops are frozen
    assert vault_registry.isVaultOpsFrozen(undy_usd_vault.address) == True

    # Verify event was emitted
    logs = filter_logs(switchboard_charlie, "VaultOpsFrozenSet")
    assert len(logs) >= 1
    assert logs[-1].vaultAddr == undy_usd_vault.address
    assert logs[-1].isFrozen == True
    assert logs[-1].caller == alice


def test_set_vault_ops_frozen_unfreeze_requires_governance(switchboard_charlie, vault_registry, undy_usd_vault, mission_control, switchboard_alpha, alice, governance):
    """Test that unfreezing vault ops requires governance"""
    # Setup alice as security action user
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)

    # Freeze vault ops first
    switchboard_charlie.setVaultOpsFrozen(undy_usd_vault.address, True, sender=alice)
    assert vault_registry.isVaultOpsFrozen(undy_usd_vault.address) == True

    # Alice tries to unfreeze - should fail
    with boa.reverts("no perms"):
        switchboard_charlie.setVaultOpsFrozen(undy_usd_vault.address, False, sender=alice)

    # Governance can unfreeze
    switchboard_charlie.setVaultOpsFrozen(undy_usd_vault.address, False, sender=governance.address)
    assert vault_registry.isVaultOpsFrozen(undy_usd_vault.address) == False


def test_set_vault_ops_frozen_governance_can_do_both(switchboard_charlie, vault_registry, undy_usd_vault, governance):
    """Test that governance can both freeze and unfreeze vault ops"""
    # Governance freezes
    switchboard_charlie.setVaultOpsFrozen(undy_usd_vault.address, True, sender=governance.address)
    assert vault_registry.isVaultOpsFrozen(undy_usd_vault.address) == True

    # Governance unfreezes
    switchboard_charlie.setVaultOpsFrozen(undy_usd_vault.address, False, sender=governance.address)
    assert vault_registry.isVaultOpsFrozen(undy_usd_vault.address) == False


def test_set_vault_ops_frozen_unauthorized_fails(switchboard_charlie, undy_usd_vault, alice):
    """Test that unauthorized users cannot freeze vault ops"""
    with boa.reverts("no perms"):
        switchboard_charlie.setVaultOpsFrozen(undy_usd_vault.address, True, sender=alice)


def test_set_redemption_buffer_success(switchboard_charlie, vault_registry, undy_usd_vault, governance):
    """Test successful redemption buffer update through full lifecycle"""
    # Get initial buffer
    initial_buffer = vault_registry.redemptionBuffer(undy_usd_vault.address)

    # Step 1: Initiate buffer change
    new_buffer = 500  # 5%
    aid = switchboard_charlie.setRedemptionBuffer(
        undy_usd_vault.address,
        new_buffer,
        sender=governance.address
    )

    # Step 2: Verify event was emitted
    logs = filter_logs(switchboard_charlie, "PendingRedemptionBufferChange")
    assert len(logs) >= 1
    assert logs[-1].vaultAddr == undy_usd_vault.address
    assert logs[-1].buffer == new_buffer
    assert logs[-1].actionId == aid
    expected_confirmation_block = boa.env.evm.patch.block_number + switchboard_charlie.actionTimeLock()
    assert logs[-1].confirmationBlock == expected_confirmation_block

    # Step 3: Verify pending state
    assert switchboard_charlie.actionType(aid) == 1  # REDEMPTION_BUFFER (2^0)
    pending = switchboard_charlie.pendingRedemptionBuffer(aid)
    assert pending.vaultAddr == undy_usd_vault.address
    assert pending.buffer == new_buffer

    # Step 4: Try to execute before timelock - should fail
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == False

    # Verify no state change
    assert vault_registry.redemptionBuffer(undy_usd_vault.address) == initial_buffer

    # Step 5: Time travel to timelock
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())

    # Step 6: Execute should succeed
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    # Step 7: Verify execution event
    exec_logs = filter_logs(switchboard_charlie, "RedemptionBufferSet")
    assert len(exec_logs) >= 1
    assert exec_logs[-1].vaultAddr == undy_usd_vault.address
    assert exec_logs[-1].buffer == new_buffer

    # Step 8: Verify state changes in VaultRegistry
    assert vault_registry.redemptionBuffer(undy_usd_vault.address) == new_buffer

    # Step 9: Verify action is cleared
    assert switchboard_charlie.actionType(aid) == 0


def test_set_redemption_buffer_too_high_fails(switchboard_charlie, undy_usd_vault, governance):
    """Test that buffer > 10% is rejected"""
    with boa.reverts("buffer too high (max 10%)"):
        switchboard_charlie.setRedemptionBuffer(
            undy_usd_vault.address,
            1001,  # 10.01%
            sender=governance.address
        )

    # 10% should work
    aid = switchboard_charlie.setRedemptionBuffer(
        undy_usd_vault.address,
        1000,  # 10%
        sender=governance.address
    )
    assert aid > 0


def test_set_redemption_buffer_invalid_vault_fails(switchboard_charlie, governance):
    """Test that invalid vault address is rejected"""
    invalid_vault = boa.env.generate_address()

    with boa.reverts("invalid vault addr"):
        switchboard_charlie.setRedemptionBuffer(
            invalid_vault,
            500,
            sender=governance.address
        )


def test_set_redemption_buffer_non_governance_fails(switchboard_charlie, undy_usd_vault, alice):
    """Test that non-governance cannot set redemption buffer"""
    with boa.reverts("no perms"):
        switchboard_charlie.setRedemptionBuffer(
            undy_usd_vault.address,
            500,
            sender=alice
        )


def test_set_snapshot_price_config_success(switchboard_charlie, vault_registry, undy_usd_vault, governance):
    """Test successful snapshot price config update"""
    # Get initial config
    initial_config = vault_registry.snapShotPriceConfig(undy_usd_vault.address)

    # New config: (minSnapshotDelay, maxNumSnapshots, maxUpsideDeviation, staleTime)
    new_config = (600, 15, 2000, 86400)

    # Initiate config change
    aid = switchboard_charlie.setSnapShotPriceConfig(
        undy_usd_vault.address,
        new_config,
        sender=governance.address
    )

    # Verify event
    logs = filter_logs(switchboard_charlie, "PendingSnapShotPriceConfigChange")
    assert len(logs) >= 1
    assert logs[-1].vaultAddr == undy_usd_vault.address
    assert logs[-1].minSnapshotDelay == 600
    assert logs[-1].maxNumSnapshots == 15
    assert logs[-1].maxUpsideDeviation == 2000
    assert logs[-1].staleTime == 86400

    # Verify pending state
    assert switchboard_charlie.actionType(aid) == 2  # SNAPSHOT_PRICE_CONFIG (2^1)

    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    # Verify execution event
    exec_logs = filter_logs(switchboard_charlie, "SnapShotPriceConfigSet")
    assert len(exec_logs) >= 1
    assert exec_logs[-1].vaultAddr == undy_usd_vault.address
    assert exec_logs[-1].minSnapshotDelay == 600

    # Verify state changes
    updated_config = vault_registry.snapShotPriceConfig(undy_usd_vault.address)
    assert updated_config.minSnapshotDelay == 600
    assert updated_config.maxNumSnapshots == 15
    assert updated_config.maxUpsideDeviation == 2000
    assert updated_config.staleTime == 86400


def test_set_snapshot_price_config_invalid_config_fails(switchboard_charlie, undy_usd_vault, governance):
    """Test that invalid price config is rejected"""
    # Invalid: maxNumSnapshots = 0
    invalid_config = (300, 0, 1000, 259200)

    with boa.reverts("invalid price config"):
        switchboard_charlie.setSnapShotPriceConfig(
            undy_usd_vault.address,
            invalid_config,
            sender=governance.address
        )


def test_set_snapshot_price_config_invalid_vault_fails(switchboard_charlie, governance):
    """Test that invalid vault address is rejected"""
    invalid_vault = boa.env.generate_address()
    valid_config = (300, 20, 1000, 259200)

    with boa.reverts("invalid vault addr"):
        switchboard_charlie.setSnapShotPriceConfig(
            invalid_vault,
            valid_config,
            sender=governance.address
        )


def test_set_snapshot_price_config_non_governance_fails(switchboard_charlie, undy_usd_vault, alice):
    """Test that non-governance cannot set snapshot config"""
    config = (600, 15, 2000, 86400)

    with boa.reverts("no perms"):
        switchboard_charlie.setSnapShotPriceConfig(
            undy_usd_vault.address,
            config,
            sender=alice
        )


def test_set_approved_vault_token_success(switchboard_charlie, vault_registry, undy_usd_vault, governance):
    """Test successful vault token approval"""
    new_vault_token = boa.env.generate_address()

    # Initially not approved
    assert vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, new_vault_token) == False

    # Initiate approval
    aid = switchboard_charlie.setApprovedVaultToken(
        undy_usd_vault.address,
        new_vault_token,
        True,
        sender=governance.address
    )

    # Verify event
    logs = filter_logs(switchboard_charlie, "PendingApprovedVaultTokenChange")
    assert len(logs) >= 1
    assert logs[-1].vaultAddr == undy_usd_vault.address
    assert logs[-1].vaultToken == new_vault_token
    assert logs[-1].isApproved == True

    # Verify pending state
    assert switchboard_charlie.actionType(aid) == 4  # APPROVED_VAULT_TOKEN (2^2)

    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    # Verify execution event
    exec_logs = filter_logs(switchboard_charlie, "ApprovedVaultTokenSet")
    assert len(exec_logs) >= 1
    assert exec_logs[-1].vaultAddr == undy_usd_vault.address
    assert exec_logs[-1].vaultToken == new_vault_token
    assert exec_logs[-1].isApproved == True

    # Verify state changes
    assert vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, new_vault_token) == True


def test_set_approved_vault_token_disapprove(switchboard_charlie, vault_registry, undy_usd_vault, governance, yield_vault_token):
    """Test disapproving a vault token"""
    # yield_vault_token is already approved in fixtures
    assert vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, yield_vault_token.address) == True

    # Initiate disapproval
    aid = switchboard_charlie.setApprovedVaultToken(
        undy_usd_vault.address,
        yield_vault_token.address,
        False,
        sender=governance.address
    )

    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    # Verify disapproved
    assert vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, yield_vault_token.address) == False


def test_set_approved_vault_token_zero_address_fails(switchboard_charlie, undy_usd_vault, governance):
    """Test that zero address vault token is rejected"""
    with boa.reverts("invalid vault token"):
        switchboard_charlie.setApprovedVaultToken(
            undy_usd_vault.address,
            ZERO_ADDRESS,
            True,
            sender=governance.address
        )


def test_set_approved_vault_token_invalid_vault_fails(switchboard_charlie, governance):
    """Test that invalid vault address is rejected"""
    invalid_vault = boa.env.generate_address()
    vault_token = boa.env.generate_address()

    with boa.reverts("invalid vault addr"):
        switchboard_charlie.setApprovedVaultToken(
            invalid_vault,
            vault_token,
            True,
            sender=governance.address
        )


def test_set_approved_vault_token_non_governance_fails(switchboard_charlie, undy_usd_vault, alice):
    """Test that non-governance cannot approve vault tokens"""
    vault_token = boa.env.generate_address()

    with boa.reverts("no perms"):
        switchboard_charlie.setApprovedVaultToken(
            undy_usd_vault.address,
            vault_token,
            True,
            sender=alice
        )


def test_set_approved_yield_lego_success(switchboard_charlie, vault_registry, undy_usd_vault, governance):
    """Test successful yield lego approval"""
    lego_id = 5

    # Initially not approved
    assert vault_registry.isApprovedYieldLegoByAddr(undy_usd_vault.address, lego_id) == False

    # Initiate approval
    aid = switchboard_charlie.setApprovedYieldLego(
        undy_usd_vault.address,
        lego_id,
        True,
        sender=governance.address
    )

    # Verify event
    logs = filter_logs(switchboard_charlie, "PendingApprovedYieldLegoChange")
    assert len(logs) >= 1
    assert logs[-1].vaultAddr == undy_usd_vault.address
    assert logs[-1].legoId == lego_id
    assert logs[-1].isApproved == True

    # Verify pending state
    assert switchboard_charlie.actionType(aid) == 8  # APPROVED_YIELD_LEGO (2^3)

    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    # Verify execution event
    exec_logs = filter_logs(switchboard_charlie, "ApprovedYieldLegoSet")
    assert len(exec_logs) >= 1
    assert exec_logs[-1].vaultAddr == undy_usd_vault.address
    assert exec_logs[-1].legoId == lego_id
    assert exec_logs[-1].isApproved == True

    # Verify state changes
    assert vault_registry.isApprovedYieldLegoByAddr(undy_usd_vault.address, lego_id) == True


def test_set_approved_yield_lego_disapprove(switchboard_charlie, vault_registry, undy_usd_vault, governance):
    """Test disapproving a yield lego"""
    # Lego ID 1 is already approved in fixtures
    assert vault_registry.isApprovedYieldLegoByAddr(undy_usd_vault.address, 1) == True

    # Initiate disapproval
    aid = switchboard_charlie.setApprovedYieldLego(
        undy_usd_vault.address,
        1,
        False,
        sender=governance.address
    )

    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    # Verify disapproved
    assert vault_registry.isApprovedYieldLegoByAddr(undy_usd_vault.address, 1) == False


def test_set_approved_yield_lego_zero_id_fails(switchboard_charlie, undy_usd_vault, governance):
    """Test that lego ID 0 is rejected"""
    with boa.reverts("invalid lego id"):
        switchboard_charlie.setApprovedYieldLego(
            undy_usd_vault.address,
            0,
            True,
            sender=governance.address
        )


def test_set_approved_yield_lego_invalid_vault_fails(switchboard_charlie, governance):
    """Test that invalid vault address is rejected"""
    invalid_vault = boa.env.generate_address()

    with boa.reverts("invalid vault addr"):
        switchboard_charlie.setApprovedYieldLego(
            invalid_vault,
            5,
            True,
            sender=governance.address
        )


def test_set_approved_yield_lego_non_governance_fails(switchboard_charlie, undy_usd_vault, alice):
    """Test that non-governance cannot approve yield legos"""
    with boa.reverts("no perms"):
        switchboard_charlie.setApprovedYieldLego(
            undy_usd_vault.address,
            5,
            True,
            sender=alice
        )


def test_initialize_vault_config_success(switchboard_charlie, vault_registry, governance, deploy_test_vault):
    """Test successful vault config initialization"""
    # Deploy a new vault
    new_vault = deploy_test_vault()

    # Register the vault
    vault_registry.startAddNewAddressToRegistry(
        new_vault.address,
        "New Test Vault",
        sender=governance.address
    )

    timelock = vault_registry.registryChangeTimeLock()
    boa.env.time_travel(blocks=timelock + 1)

    vault_registry.confirmNewAddressToRegistry(
        new_vault.address,
        sender=governance.address
    )

    # Create vault tokens and lego IDs
    vault_token_1 = boa.env.generate_address()
    vault_token_2 = boa.env.generate_address()

    # Snapshot config: (minSnapshotDelay, maxNumSnapshots, maxUpsideDeviation, staleTime)
    snap_config = (300, 20, 1000, 259200)

    # Initiate config initialization
    aid = switchboard_charlie.initializeVaultConfig(
        new_vault.address,
        True,  # canDeposit
        True,  # canWithdraw
        1_000_000 * EIGHTEEN_DECIMALS,  # maxDepositAmount
        300,  # redemptionBuffer (3%)
        0,  # minYieldWithdrawAmount
        snap_config,
        [vault_token_1, vault_token_2],  # approvedVaultTokens
        [1, 2],  # approvedYieldLegos
        sender=governance.address
    )

    # Verify event
    logs = filter_logs(switchboard_charlie, "PendingInitializeVaultConfigChange")
    assert len(logs) >= 1
    assert logs[-1].vaultAddr == new_vault.address
    assert logs[-1].canDeposit == True
    assert logs[-1].canWithdraw == True
    assert logs[-1].maxDepositAmount == 1_000_000 * EIGHTEEN_DECIMALS
    assert logs[-1].redemptionBuffer == 300
    assert logs[-1].numApprovedVaultTokens == 2
    assert logs[-1].numApprovedYieldLegos == 2

    # Verify pending state
    assert switchboard_charlie.actionType(aid) == 16  # INITIALIZE_VAULT_CONFIG (2^4)

    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    # Verify execution event
    exec_logs = filter_logs(switchboard_charlie, "VaultConfigInitialized")
    assert len(exec_logs) >= 1
    assert exec_logs[-1].vaultAddr == new_vault.address
    assert exec_logs[-1].canDeposit == True
    assert exec_logs[-1].canWithdraw == True

    # Verify config was set in VaultRegistry
    config = vault_registry.getVaultConfigByAddr(new_vault.address)
    assert config.canDeposit == True
    assert config.canWithdraw == True
    assert config.maxDepositAmount == 1_000_000 * EIGHTEEN_DECIMALS
    assert config.redemptionBuffer == 300
    assert config.isVaultOpsFrozen == False
    assert config.snapShotPriceConfig.minSnapshotDelay == 300
    assert config.snapShotPriceConfig.maxNumSnapshots == 20

    # Verify approvals
    assert vault_registry.isApprovedVaultTokenByAddr(new_vault.address, vault_token_1) == True
    assert vault_registry.isApprovedVaultTokenByAddr(new_vault.address, vault_token_2) == True
    assert vault_registry.isApprovedYieldLegoByAddr(new_vault.address, 1) == True
    assert vault_registry.isApprovedYieldLegoByAddr(new_vault.address, 2) == True


def test_initialize_vault_config_buffer_too_high_fails(switchboard_charlie, governance, deploy_test_vault, vault_registry):
    """Test that buffer > 10% is rejected"""
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

    snap_config = (300, 20, 1000, 259200)

    with boa.reverts("buffer too high (max 10%)"):
        switchboard_charlie.initializeVaultConfig(
            new_vault.address,
            True,
            True,
            0,
            1001,  # 10.01%
            0,  # minYieldWithdrawAmount
            snap_config,
            [],
            [],
            sender=governance.address
        )


def test_initialize_vault_config_invalid_price_config_fails(switchboard_charlie, governance, deploy_test_vault, vault_registry):
    """Test that invalid price config is rejected"""
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

    # Invalid config: maxNumSnapshots = 0
    invalid_snap_config = (300, 0, 1000, 259200)

    with boa.reverts("invalid price config"):
        switchboard_charlie.initializeVaultConfig(
            new_vault.address,
            True,
            True,
            0,
            200,
            0,  # minYieldWithdrawAmount
            invalid_snap_config,
            [],
            [],
            sender=governance.address
        )


def test_initialize_vault_config_invalid_vault_fails(switchboard_charlie, governance):
    """Test that unregistered vault cannot be initialized"""
    random_vault = boa.env.generate_address()
    snap_config = (300, 20, 1000, 259200)

    # Create pending action
    aid = switchboard_charlie.initializeVaultConfig(
        random_vault,
        True,
        True,
        0,
        200,
        0,  # minYieldWithdrawAmount
        snap_config,
        [],
        [],
        sender=governance.address
    )

    # Time travel to after timelock
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())

    # Execution should fail because vault is not registered
    with boa.reverts("invalid vault addr"):
        switchboard_charlie.executePendingAction(aid, sender=governance.address)


def test_initialize_vault_config_non_governance_fails(switchboard_charlie, alice, deploy_test_vault):
    """Test that non-governance cannot initialize vault config"""
    new_vault = deploy_test_vault()
    snap_config = (300, 20, 1000, 259200)

    with boa.reverts("no perms"):
        switchboard_charlie.initializeVaultConfig(
            new_vault.address,
            True,
            True,
            0,
            200,
            0,  # minYieldWithdrawAmount
            snap_config,
            [],
            [],
            sender=alice
        )


def test_cancel_pending_action(switchboard_charlie, undy_usd_vault, governance):
    """Test canceling a pending action"""
    # Create a pending action
    aid = switchboard_charlie.setRedemptionBuffer(
        undy_usd_vault.address,
        500,
        sender=governance.address
    )

    # Verify pending state
    assert switchboard_charlie.actionType(aid) == 1

    # Cancel the pending action
    result = switchboard_charlie.cancelPendingAction(aid, sender=governance.address)
    assert result == True

    # Verify action is cleared
    assert switchboard_charlie.actionType(aid) == 0

    # Try to execute canceled action - should fail
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == False


def test_cancel_pending_action_non_governance_fails(switchboard_charlie, undy_usd_vault, governance, alice):
    """Test that non-governance cannot cancel pending actions"""
    # Create a pending action
    aid = switchboard_charlie.setRedemptionBuffer(
        undy_usd_vault.address,
        500,
        sender=governance.address
    )

    # Try to cancel as non-governance
    with boa.reverts("no perms"):
        switchboard_charlie.cancelPendingAction(aid, sender=alice)


def test_execute_expired_action(switchboard_charlie, vault_registry, undy_usd_vault, governance):
    """Test that expired actions auto-cancel and cannot be executed"""
    initial_buffer = vault_registry.redemptionBuffer(undy_usd_vault.address)

    # Create a pending action
    aid = switchboard_charlie.setRedemptionBuffer(
        undy_usd_vault.address,
        500,
        sender=governance.address
    )

    # Time travel past expiration (timelock + max timelock)
    max_timelock = switchboard_charlie.maxActionTimeLock()
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock() + max_timelock + 1)

    # Try to execute - should auto-cancel and return False
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == False

    # Verify action is cleared
    assert switchboard_charlie.actionType(aid) == 0

    # Verify buffer hasn't changed
    assert vault_registry.redemptionBuffer(undy_usd_vault.address) == initial_buffer


def test_execute_pending_action_non_governance_fails(switchboard_charlie, undy_usd_vault, governance, alice):
    """Test that non-governance cannot execute pending actions"""
    # Create a pending action
    aid = switchboard_charlie.setRedemptionBuffer(
        undy_usd_vault.address,
        500,
        sender=governance.address
    )

    # Time travel to timelock
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())

    # Try to execute as non-governance
    with boa.reverts("no perms"):
        switchboard_charlie.executePendingAction(aid, sender=alice)


def test_multiple_pending_actions(switchboard_charlie, vault_registry, undy_usd_vault, governance):
    """Test creating multiple pending actions with different action IDs"""
    # Create first pending action (redemption buffer)
    aid1 = switchboard_charlie.setRedemptionBuffer(
        undy_usd_vault.address,
        300,
        sender=governance.address
    )

    # Create second pending action (snapshot config)
    snap_config = (600, 15, 2000, 86400)
    aid2 = switchboard_charlie.setSnapShotPriceConfig(
        undy_usd_vault.address,
        snap_config,
        sender=governance.address
    )

    # Verify different action IDs
    assert aid1 != aid2

    # Verify both are pending
    assert switchboard_charlie.actionType(aid1) == 1  # REDEMPTION_BUFFER
    assert switchboard_charlie.actionType(aid2) == 2  # SNAPSHOT_PRICE_CONFIG

    # Execute second action first
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid2, sender=governance.address)
    assert result == True

    # Verify snapshot config updated
    config = vault_registry.snapShotPriceConfig(undy_usd_vault.address)
    assert config.minSnapshotDelay == 600

    # First action should still be pending
    assert switchboard_charlie.actionType(aid1) == 1

    # Execute first action
    result = switchboard_charlie.executePendingAction(aid1, sender=governance.address)
    assert result == True

    # Verify redemption buffer updated
    assert vault_registry.redemptionBuffer(undy_usd_vault.address) == 300


def test_multiple_vaults_independent_configs(switchboard_charlie, vault_registry, governance, deploy_test_vault):
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

    # Set different buffers via switchboard
    aid1 = switchboard_charlie.setRedemptionBuffer(vault_1.address, 100, sender=governance.address)
    aid2 = switchboard_charlie.setRedemptionBuffer(vault_2.address, 500, sender=governance.address)

    # Execute both
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    switchboard_charlie.executePendingAction(aid1, sender=governance.address)
    switchboard_charlie.executePendingAction(aid2, sender=governance.address)

    # Verify independent configs
    assert vault_registry.redemptionBuffer(vault_1.address) == 100
    assert vault_registry.redemptionBuffer(vault_2.address) == 500
