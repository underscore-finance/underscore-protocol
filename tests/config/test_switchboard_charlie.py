import pytest
import boa
from conf_utils import filter_logs
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS
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
            "contracts/vaults/EarnVault.vy",
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
    with boa.reverts("invalid redemption buffer"):
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


def test_set_min_yield_withdraw_amount_success(switchboard_charlie, vault_registry, undy_usd_vault, governance):
    """Test successful min yield withdraw amount update through full lifecycle"""
    # Get initial amount
    initial_amount = vault_registry.minYieldWithdrawAmount(undy_usd_vault.address)

    # Step 1: Initiate amount change
    new_amount = 1000 * EIGHTEEN_DECIMALS
    aid = switchboard_charlie.setMinYieldWithdrawAmount(
        undy_usd_vault.address,
        new_amount,
        sender=governance.address
    )

    # Step 2: Verify event was emitted
    logs = filter_logs(switchboard_charlie, "PendingMinYieldWithdrawAmountChange")
    assert len(logs) >= 1
    assert logs[-1].vaultAddr == undy_usd_vault.address
    assert logs[-1].amount == new_amount
    assert logs[-1].actionId == aid
    expected_confirmation_block = boa.env.evm.patch.block_number + switchboard_charlie.actionTimeLock()
    assert logs[-1].confirmationBlock == expected_confirmation_block

    # Step 3: Verify pending state
    assert switchboard_charlie.actionType(aid) == 2  # MIN_YIELD_WITHDRAW_AMOUNT (2^1)
    pending = switchboard_charlie.pendingMinYieldWithdrawAmount(aid)
    assert pending.vaultAddr == undy_usd_vault.address
    assert pending.amount == new_amount

    # Step 4: Try to execute before timelock - should fail
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == False

    # Verify no state change
    assert vault_registry.minYieldWithdrawAmount(undy_usd_vault.address) == initial_amount

    # Step 5: Time travel to timelock
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())

    # Step 6: Execute should succeed
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    # Step 7: Verify execution event
    exec_logs = filter_logs(switchboard_charlie, "MinYieldWithdrawAmountSet")
    assert len(exec_logs) >= 1
    assert exec_logs[-1].vaultAddr == undy_usd_vault.address
    assert exec_logs[-1].amount == new_amount

    # Step 8: Verify state changes in VaultRegistry
    assert vault_registry.minYieldWithdrawAmount(undy_usd_vault.address) == new_amount

    # Step 9: Verify action is cleared
    assert switchboard_charlie.actionType(aid) == 0


def test_set_min_yield_withdraw_amount_invalid_vault_fails(switchboard_charlie, governance):
    """Test that invalid vault address is rejected"""
    invalid_vault = boa.env.generate_address()

    with boa.reverts("invalid vault addr"):
        switchboard_charlie.setMinYieldWithdrawAmount(
            invalid_vault,
            1000 * EIGHTEEN_DECIMALS,
            sender=governance.address
        )


def test_set_min_yield_withdraw_amount_non_governance_fails(switchboard_charlie, undy_usd_vault, alice):
    """Test that non-governance cannot set min yield withdraw amount"""
    with boa.reverts("no perms"):
        switchboard_charlie.setMinYieldWithdrawAmount(
            undy_usd_vault.address,
            1000 * EIGHTEEN_DECIMALS,
            sender=alice
        )


def test_set_snapshot_price_config_success(switchboard_charlie, mock_yield_lego, governance):
    """Test successful snapshot price config update"""
    # Get initial config
    lego_id = 1  # mock_yield_lego
    initial_config = mock_yield_lego.snapShotPriceConfig()

    # Initiate config change
    aid = switchboard_charlie.setSnapShotPriceConfig(
        lego_id,
        600,    # _minSnapshotDelay
        15,     # _maxNumSnapshots
        2000,   # _maxUpsideDeviation
        86400,  # _staleTime
        sender=governance.address
    )

    # Verify event
    logs = filter_logs(switchboard_charlie, "PendingSnapShotPriceConfigChange")
    assert len(logs) >= 1
    assert logs[-1].legoId == lego_id
    assert logs[-1].minSnapshotDelay == 600
    assert logs[-1].maxNumSnapshots == 15
    assert logs[-1].maxUpsideDeviation == 2000
    assert logs[-1].staleTime == 86400

    # Verify pending state
    assert switchboard_charlie.actionType(aid) == 4  # SNAPSHOT_PRICE_CONFIG (2^2)

    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    # Verify execution event
    exec_logs = filter_logs(switchboard_charlie, "SnapShotPriceConfigSet")
    assert len(exec_logs) >= 1
    assert exec_logs[-1].legoId == lego_id
    assert exec_logs[-1].legoAddr == mock_yield_lego.address
    assert exec_logs[-1].minSnapshotDelay == 600

    # Verify state changes
    updated_config = mock_yield_lego.snapShotPriceConfig()
    assert updated_config.minSnapshotDelay == 600
    assert updated_config.maxNumSnapshots == 15
    assert updated_config.maxUpsideDeviation == 2000
    assert updated_config.staleTime == 86400


def test_set_snapshot_price_config_invalid_config_fails(switchboard_charlie, governance):
    """Test that invalid price config is rejected"""
    lego_id = 1  # mock_yield_lego
    # Invalid: maxNumSnapshots = 0
    with boa.reverts("invalid price config"):
        switchboard_charlie.setSnapShotPriceConfig(
            lego_id,
            300,     # _minSnapshotDelay
            0,       # _maxNumSnapshots (invalid)
            1000,    # _maxUpsideDeviation
            259200,  # _staleTime
            sender=governance.address
        )


def test_set_snapshot_price_config_invalid_lego_id_fails(switchboard_charlie, governance):
    """Test that invalid lego id is rejected"""
    invalid_lego_id = 999  # non-existent lego

    with boa.reverts("invalid lego id"):
        switchboard_charlie.setSnapShotPriceConfig(
            invalid_lego_id,
            300,     # _minSnapshotDelay
            20,      # _maxNumSnapshots
            1000,    # _maxUpsideDeviation
            259200,  # _staleTime
            sender=governance.address
        )


def test_set_snapshot_price_config_non_governance_fails(switchboard_charlie, alice):
    """Test that non-governance cannot set snapshot config"""
    lego_id = 1  # mock_yield_lego
    with boa.reverts("no perms"):
        switchboard_charlie.setSnapShotPriceConfig(
            lego_id,
            600,    # _minSnapshotDelay
            15,     # _maxNumSnapshots
            2000,   # _maxUpsideDeviation
            86400,  # _staleTime
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
    assert switchboard_charlie.actionType(aid) == 8  # APPROVED_VAULT_TOKEN (2^3)

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


def test_multiple_pending_actions(switchboard_charlie, vault_registry, undy_usd_vault, mock_yield_lego, governance):
    """Test creating multiple pending actions with different action IDs"""
    # Create first pending action (redemption buffer)
    aid1 = switchboard_charlie.setRedemptionBuffer(
        undy_usd_vault.address,
        300,
        sender=governance.address
    )

    # Create second pending action (snapshot config)
    lego_id = 1  # mock_yield_lego
    aid2 = switchboard_charlie.setSnapShotPriceConfig(
        lego_id,
        600,    # _minSnapshotDelay
        15,     # _maxNumSnapshots
        2000,   # _maxUpsideDeviation
        86400,  # _staleTime
        sender=governance.address
    )

    # Verify different action IDs
    assert aid1 != aid2

    # Verify both are pending
    assert switchboard_charlie.actionType(aid1) == 1  # REDEMPTION_BUFFER
    assert switchboard_charlie.actionType(aid2) == 4  # SNAPSHOT_PRICE_CONFIG

    # Execute second action first
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid2, sender=governance.address)
    assert result == True

    # Verify snapshot config updated
    config = mock_yield_lego.snapShotPriceConfig()
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


# setShouldAutoDeposit tests


def test_set_should_auto_deposit_disable_by_security_action(switchboard_charlie, vault_registry, undy_usd_vault, mission_control, switchboard_alpha, alice):
    """Test that security action users can disable auto deposit"""
    # Setup alice as security action user
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)

    # Initially auto deposit is enabled
    assert vault_registry.shouldAutoDeposit(undy_usd_vault.address) == True

    # Alice (security action user) disables auto deposit
    switchboard_charlie.setShouldAutoDeposit(undy_usd_vault.address, False, sender=alice)

    # Verify auto deposit is disabled
    assert vault_registry.shouldAutoDeposit(undy_usd_vault.address) == False

    # Verify event was emitted
    logs = filter_logs(switchboard_charlie, "ShouldAutoDepositSet")
    assert len(logs) >= 1
    assert logs[-1].vaultAddr == undy_usd_vault.address
    assert logs[-1].shouldAutoDeposit == False
    assert logs[-1].caller == alice


def test_set_should_auto_deposit_enable_requires_governance(switchboard_charlie, vault_registry, undy_usd_vault, mission_control, switchboard_alpha, alice, governance):
    """Test that enabling auto deposit requires governance"""
    # Setup alice as security action user
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)

    # Disable auto deposit first
    switchboard_charlie.setShouldAutoDeposit(undy_usd_vault.address, False, sender=governance.address)
    assert vault_registry.shouldAutoDeposit(undy_usd_vault.address) == False

    # Alice tries to enable - should fail
    with boa.reverts("no perms"):
        switchboard_charlie.setShouldAutoDeposit(undy_usd_vault.address, True, sender=alice)

    # Governance can enable
    switchboard_charlie.setShouldAutoDeposit(undy_usd_vault.address, True, sender=governance.address)
    assert vault_registry.shouldAutoDeposit(undy_usd_vault.address) == True


def test_set_should_auto_deposit_unauthorized_fails(switchboard_charlie, undy_usd_vault, alice):
    """Test that unauthorized users cannot set should auto deposit"""
    with boa.reverts("no perms"):
        switchboard_charlie.setShouldAutoDeposit(undy_usd_vault.address, False, sender=alice)


# setPerformanceFee tests


def test_set_performance_fee_success(switchboard_charlie, vault_registry, undy_usd_vault, governance):
    """Test successful performance fee update through full lifecycle"""
    # Get initial fee
    initial_fee = vault_registry.getPerformanceFee(undy_usd_vault.address)

    # Initiate fee change to 15%
    new_fee = 15_00  # 15%
    aid = switchboard_charlie.setPerformanceFee(
        undy_usd_vault.address,
        new_fee,
        sender=governance.address
    )

    # Verify event
    logs = filter_logs(switchboard_charlie, "PendingPerformanceFeeChange")
    assert len(logs) >= 1
    assert logs[-1].vaultAddr == undy_usd_vault.address
    assert logs[-1].performanceFee == new_fee
    assert logs[-1].actionId == aid

    # Verify pending state
    assert switchboard_charlie.actionType(aid) == 16  # PERFORMANCE_FEE (2^4)
    pending = switchboard_charlie.pendingPerformanceFee(aid)
    assert pending.vaultAddr == undy_usd_vault.address
    assert pending.performanceFee == new_fee

    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    # Verify execution event
    exec_logs = filter_logs(switchboard_charlie, "PerformanceFeeSet")
    assert len(exec_logs) >= 1
    assert exec_logs[-1].vaultAddr == undy_usd_vault.address
    assert exec_logs[-1].performanceFee == new_fee

    # Verify state changes in VaultRegistry
    assert vault_registry.getPerformanceFee(undy_usd_vault.address) == new_fee


def test_set_performance_fee_too_high_fails(switchboard_charlie, undy_usd_vault, governance):
    """Test that performance fee > 100% is rejected"""
    with boa.reverts("invalid performance fee"):
        switchboard_charlie.setPerformanceFee(
            undy_usd_vault.address,
            10001,  # 100.01%
            sender=governance.address
        )


def test_set_performance_fee_invalid_vault_fails(switchboard_charlie, governance):
    """Test that invalid vault address is rejected"""
    invalid_vault = boa.env.generate_address()

    with boa.reverts("invalid vault addr"):
        switchboard_charlie.setPerformanceFee(
            invalid_vault,
            15_00,
            sender=governance.address
        )


def test_set_performance_fee_non_governance_fails(switchboard_charlie, undy_usd_vault, alice):
    """Test that non-governance cannot set performance fee"""
    with boa.reverts("no perms"):
        switchboard_charlie.setPerformanceFee(
            undy_usd_vault.address,
            15_00,
            sender=alice
        )


# setDefaultTargetVaultToken tests


def test_set_default_target_vault_token_success(switchboard_charlie, vault_registry, undy_usd_vault, governance):
    """Test successful default target vault token update to zero address"""
    # Set to zero address (the only valid non-approved option)
    target_token = ZERO_ADDRESS

    # Initiate change
    aid = switchboard_charlie.setDefaultTargetVaultToken(
        undy_usd_vault.address,
        target_token,
        sender=governance.address
    )

    # Verify event
    logs = filter_logs(switchboard_charlie, "PendingDefaultTargetVaultTokenChange")
    assert len(logs) >= 1
    assert logs[-1].vaultAddr == undy_usd_vault.address
    assert logs[-1].targetVaultToken == target_token
    assert logs[-1].actionId == aid

    # Verify pending state
    assert switchboard_charlie.actionType(aid) == 32  # DEFAULT_TARGET_VAULT_TOKEN (2^5)
    pending = switchboard_charlie.pendingDefaultTargetVaultToken(aid)
    assert pending.vaultAddr == undy_usd_vault.address
    assert pending.targetVaultToken == target_token

    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    # Verify execution event
    exec_logs = filter_logs(switchboard_charlie, "DefaultTargetVaultTokenSet")
    assert len(exec_logs) >= 1
    assert exec_logs[-1].vaultAddr == undy_usd_vault.address
    assert exec_logs[-1].targetVaultToken == target_token


def test_set_default_target_vault_token_already_approved_fails(switchboard_charlie, undy_usd_vault, governance, yield_vault_token):
    """Test that setting an already approved vault token as default fails"""
    # yield_vault_token is already approved
    with boa.reverts("vault token already approved"):
        switchboard_charlie.setDefaultTargetVaultToken(
            undy_usd_vault.address,
            yield_vault_token.address,
            sender=governance.address
        )


def test_set_default_target_vault_token_invalid_vault_fails(switchboard_charlie, governance):
    """Test that invalid vault address is rejected"""
    invalid_vault = boa.env.generate_address()
    target_token = boa.env.generate_address()

    with boa.reverts("invalid vault addr"):
        switchboard_charlie.setDefaultTargetVaultToken(
            invalid_vault,
            target_token,
            sender=governance.address
        )


def test_set_default_target_vault_token_non_governance_fails(switchboard_charlie, undy_usd_vault, alice):
    """Test that non-governance cannot set default target vault token"""
    target_token = boa.env.generate_address()

    with boa.reverts("no perms"):
        switchboard_charlie.setDefaultTargetVaultToken(
            undy_usd_vault.address,
            target_token,
            sender=alice
        )


# setMaxDepositAmount tests


def test_set_max_deposit_amount_success(switchboard_charlie, vault_registry, undy_usd_vault, governance):
    """Test successful max deposit amount update through full lifecycle"""
    # Get initial max deposit
    initial_max = vault_registry.getVaultConfigByAddr(undy_usd_vault.address).maxDepositAmount

    # Initiate change
    new_max = 5_000_000 * EIGHTEEN_DECIMALS
    aid = switchboard_charlie.setMaxDepositAmount(
        undy_usd_vault.address,
        new_max,
        sender=governance.address
    )

    # Verify event
    logs = filter_logs(switchboard_charlie, "PendingMaxDepositAmountChange")
    assert len(logs) >= 1
    assert logs[-1].vaultAddr == undy_usd_vault.address
    assert logs[-1].maxDepositAmount == new_max
    assert logs[-1].actionId == aid

    # Verify pending state
    assert switchboard_charlie.actionType(aid) == 64  # MAX_DEPOSIT_AMOUNT (2^6)
    pending = switchboard_charlie.pendingMaxDepositAmount(aid)
    assert pending.vaultAddr == undy_usd_vault.address
    assert pending.maxDepositAmount == new_max

    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    # Verify execution event
    exec_logs = filter_logs(switchboard_charlie, "MaxDepositAmountSet")
    assert len(exec_logs) >= 1
    assert exec_logs[-1].vaultAddr == undy_usd_vault.address
    assert exec_logs[-1].maxDepositAmount == new_max

    # Verify state changes in VaultRegistry
    updated_config = vault_registry.getVaultConfigByAddr(undy_usd_vault.address)
    assert updated_config.maxDepositAmount == new_max


def test_set_max_deposit_amount_invalid_vault_fails(switchboard_charlie, governance):
    """Test that invalid vault address is rejected"""
    invalid_vault = boa.env.generate_address()

    with boa.reverts("invalid vault addr"):
        switchboard_charlie.setMaxDepositAmount(
            invalid_vault,
            1_000_000 * EIGHTEEN_DECIMALS,
            sender=governance.address
        )


def test_set_max_deposit_amount_non_governance_fails(switchboard_charlie, undy_usd_vault, alice):
    """Test that non-governance cannot set max deposit amount"""
    with boa.reverts("no perms"):
        switchboard_charlie.setMaxDepositAmount(
            undy_usd_vault.address,
            1_000_000 * EIGHTEEN_DECIMALS,
            sender=alice
        )
