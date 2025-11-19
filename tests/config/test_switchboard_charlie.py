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
    lego_id = 2  # mock_yield_lego
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
    lego_id = 2  # mock_yield_lego
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
    lego_id = 2  # mock_yield_lego
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
        False,  # _shouldMaxWithdraw
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
    """Test disapproving a vault token - executes immediately without timelock"""
    # yield_vault_token is already approved in fixtures
    assert vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, yield_vault_token.address) == True

    # Disapproval executes immediately (no timelock)
    aid = switchboard_charlie.setApprovedVaultToken(
        undy_usd_vault.address,
        yield_vault_token.address,
        False,
        False,  # _shouldMaxWithdraw
        sender=governance.address
    )

    # Should return 0 (no action ID) for immediate execution
    assert aid == 0

    # Verify immediately disapproved (no timelock wait)
    assert vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, yield_vault_token.address) == False

    # Verify event was emitted
    logs = filter_logs(switchboard_charlie, "ApprovedVaultTokenSet")
    assert len(logs) >= 1
    assert logs[-1].vaultAddr == undy_usd_vault.address
    assert logs[-1].vaultToken == yield_vault_token.address
    assert logs[-1].isApproved == False


def test_set_approved_vault_token_zero_address_fails(switchboard_charlie, undy_usd_vault, governance):
    """Test that zero address vault token is rejected"""
    with boa.reverts("invalid vault token"):
        switchboard_charlie.setApprovedVaultToken(
            undy_usd_vault.address,
            ZERO_ADDRESS,
            True,
            False,  # _shouldMaxWithdraw
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
            False,  # _shouldMaxWithdraw
            sender=governance.address
        )


def test_set_approved_vault_token_security_action_can_disapprove(switchboard_charlie, vault_registry, undy_usd_vault, mission_control, switchboard_alpha, alice, yield_vault_token):
    """Test that security action users can disapprove vault tokens immediately"""
    # Setup alice as security action user
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)

    # yield_vault_token is already approved
    assert vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, yield_vault_token.address) == True

    # Alice (security action user) disapproves immediately
    aid = switchboard_charlie.setApprovedVaultToken(
        undy_usd_vault.address,
        yield_vault_token.address,
        False,
        False,  # _shouldMaxWithdraw
        sender=alice
    )

    # Should return 0 (no action ID) for immediate execution
    assert aid == 0

    # Verify immediately disapproved (no timelock wait)
    assert vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, yield_vault_token.address) == False

    # Verify event was emitted
    logs = filter_logs(switchboard_charlie, "ApprovedVaultTokenSet")
    assert len(logs) >= 1
    assert logs[-1].vaultAddr == undy_usd_vault.address
    assert logs[-1].vaultToken == yield_vault_token.address
    assert logs[-1].isApproved == False


def test_set_approved_vault_token_security_action_cannot_approve(switchboard_charlie, undy_usd_vault, mission_control, switchboard_alpha, alice):
    """Test that security action users cannot approve vault tokens"""
    # Setup alice as security action user
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)

    new_vault_token = boa.env.generate_address()

    # Alice tries to approve - should fail
    with boa.reverts("no perms"):
        switchboard_charlie.setApprovedVaultToken(
            undy_usd_vault.address,
            new_vault_token,
            True,
            False,  # _shouldMaxWithdraw
            sender=alice
        )


def test_set_approved_vault_token_unauthorized_cannot_approve(switchboard_charlie, undy_usd_vault, alice):
    """Test that unauthorized users cannot approve vault tokens"""
    vault_token = boa.env.generate_address()

    with boa.reverts("no perms"):
        switchboard_charlie.setApprovedVaultToken(
            undy_usd_vault.address,
            vault_token,
            True,
            False,  # _shouldMaxWithdraw
            sender=alice
        )


def test_set_approved_vault_token_unauthorized_cannot_disapprove(switchboard_charlie, undy_usd_vault, alice, yield_vault_token):
    """Test that unauthorized users cannot disapprove vault tokens"""
    with boa.reverts("no perms"):
        switchboard_charlie.setApprovedVaultToken(
            undy_usd_vault.address,
            yield_vault_token.address,
            False,
            False,  # _shouldMaxWithdraw
            sender=alice
        )


# setApprovedVaultTokens tests (plural)


def test_set_approved_vault_tokens_governance_can_approve(switchboard_charlie, vault_registry, undy_usd_vault, governance):
    """Test that governance can approve multiple vault tokens"""
    token1 = boa.env.generate_address()
    token2 = boa.env.generate_address()
    token3 = boa.env.generate_address()
    vault_tokens = [token1, token2, token3]

    # Initially not approved
    for token in vault_tokens:
        assert vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, token) == False

    # Initiate approval
    aid = switchboard_charlie.setApprovedVaultTokens(
        undy_usd_vault.address,
        vault_tokens,
        True,
        False,  # _shouldMaxWithdraw
        sender=governance.address
    )

    # Verify event
    logs = filter_logs(switchboard_charlie, "PendingApprovedVaultTokensChange")
    assert len(logs) >= 1
    assert logs[-1].vaultAddr == undy_usd_vault.address
    assert logs[-1].numTokens == 3
    assert logs[-1].isApproved == True

    # Execute after timelock
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())
    result = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert result == True

    # Verify all tokens are approved
    for token in vault_tokens:
        assert vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, token) == True


def test_set_approved_vault_tokens_governance_can_disapprove(switchboard_charlie, vault_registry, undy_usd_vault, governance, yield_vault_token, yield_vault_token_2):
    """Test that governance can disapprove multiple vault tokens immediately"""
    # Both tokens should be approved in fixtures
    assert vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, yield_vault_token.address) == True
    assert vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, yield_vault_token_2.address) == True

    vault_tokens = [yield_vault_token.address, yield_vault_token_2.address]

    # Disapproval executes immediately (no timelock)
    aid = switchboard_charlie.setApprovedVaultTokens(
        undy_usd_vault.address,
        vault_tokens,
        False,
        False,  # _shouldMaxWithdraw
        sender=governance.address
    )

    # Should return 0 (no action ID) for immediate execution
    assert aid == 0

    # Verify all tokens are immediately disapproved (no timelock wait)
    for token in vault_tokens:
        assert vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, token) == False

    # Verify event was emitted
    logs = filter_logs(switchboard_charlie, "ApprovedVaultTokensSet")
    assert len(logs) >= 1
    assert logs[-1].vaultAddr == undy_usd_vault.address
    assert logs[-1].numTokens == 2
    assert logs[-1].isApproved == False


def test_set_approved_vault_tokens_security_action_can_disapprove(switchboard_charlie, vault_registry, undy_usd_vault, mission_control, switchboard_alpha, alice, yield_vault_token, yield_vault_token_2):
    """Test that security action users can disapprove multiple vault tokens immediately"""
    # Setup alice as security action user
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)

    # Both tokens should be approved
    assert vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, yield_vault_token.address) == True
    assert vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, yield_vault_token_2.address) == True

    vault_tokens = [yield_vault_token.address, yield_vault_token_2.address]

    # Alice (security action user) disapproves immediately
    aid = switchboard_charlie.setApprovedVaultTokens(
        undy_usd_vault.address,
        vault_tokens,
        False,
        False,  # _shouldMaxWithdraw
        sender=alice
    )

    # Should return 0 (no action ID) for immediate execution
    assert aid == 0

    # Verify all tokens are immediately disapproved (no timelock wait)
    for token in vault_tokens:
        assert vault_registry.isApprovedVaultTokenByAddr(undy_usd_vault.address, token) == False

    # Verify event was emitted
    logs = filter_logs(switchboard_charlie, "ApprovedVaultTokensSet")
    assert len(logs) >= 1
    assert logs[-1].vaultAddr == undy_usd_vault.address
    assert logs[-1].numTokens == 2
    assert logs[-1].isApproved == False


def test_set_approved_vault_tokens_security_action_cannot_approve(switchboard_charlie, undy_usd_vault, mission_control, switchboard_alpha, alice):
    """Test that security action users cannot approve multiple vault tokens"""
    # Setup alice as security action user
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)

    token1 = boa.env.generate_address()
    token2 = boa.env.generate_address()
    vault_tokens = [token1, token2]

    # Alice tries to approve - should fail
    with boa.reverts("no perms"):
        switchboard_charlie.setApprovedVaultTokens(
            undy_usd_vault.address,
            vault_tokens,
            True,
            False,  # _shouldMaxWithdraw
            sender=alice
        )


def test_set_approved_vault_tokens_unauthorized_cannot_approve(switchboard_charlie, undy_usd_vault, alice):
    """Test that unauthorized users cannot approve multiple vault tokens"""
    token1 = boa.env.generate_address()
    token2 = boa.env.generate_address()
    vault_tokens = [token1, token2]

    with boa.reverts("no perms"):
        switchboard_charlie.setApprovedVaultTokens(
            undy_usd_vault.address,
            vault_tokens,
            True,
            False,  # _shouldMaxWithdraw
            sender=alice
        )


def test_set_approved_vault_tokens_unauthorized_cannot_disapprove(switchboard_charlie, undy_usd_vault, alice, yield_vault_token, yield_vault_token_2):
    """Test that unauthorized users cannot disapprove multiple vault tokens"""
    vault_tokens = [yield_vault_token.address, yield_vault_token_2.address]

    with boa.reverts("no perms"):
        switchboard_charlie.setApprovedVaultTokens(
            undy_usd_vault.address,
            vault_tokens,
            False,
            False,  # _shouldMaxWithdraw
            sender=alice
        )


def test_set_approved_vault_tokens_empty_list_fails(switchboard_charlie, undy_usd_vault, governance):
    """Test that empty vault tokens list is rejected"""
    with boa.reverts("no vault tokens"):
        switchboard_charlie.setApprovedVaultTokens(
            undy_usd_vault.address,
            [],
            True,
            False,  # _shouldMaxWithdraw
            sender=governance.address
        )


def test_set_approved_vault_tokens_zero_address_fails(switchboard_charlie, undy_usd_vault, governance):
    """Test that vault tokens list containing zero address is rejected"""
    token1 = boa.env.generate_address()
    vault_tokens = [token1, ZERO_ADDRESS]

    with boa.reverts("invalid vault tokens"):
        switchboard_charlie.setApprovedVaultTokens(
            undy_usd_vault.address,
            vault_tokens,
            True,
            False,  # _shouldMaxWithdraw
            sender=governance.address
        )


def test_set_approved_vault_tokens_invalid_vault_fails(switchboard_charlie, governance):
    """Test that invalid vault address is rejected"""
    invalid_vault = boa.env.generate_address()
    token1 = boa.env.generate_address()
    vault_tokens = [token1]

    with boa.reverts("invalid vault addr"):
        switchboard_charlie.setApprovedVaultTokens(
            invalid_vault,
            vault_tokens,
            True,
            False,  # _shouldMaxWithdraw
            sender=governance.address
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
    lego_id = 2  # mock_yield_lego
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
    assert switchboard_charlie.actionType(aid) == 32  # PERFORMANCE_FEE (2^5)
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
    assert switchboard_charlie.actionType(aid) == 64  # DEFAULT_TARGET_VAULT_TOKEN (2^6)
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
    assert switchboard_charlie.actionType(aid) == 128  # MAX_DEPOSIT_AMOUNT (2^7)
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


# addPriceSnapshot tests


def test_add_price_snapshot_governance_can_call(
    switchboard_charlie,
    mock_yield_lego,
    yield_vault_token,
    yield_underlying_token,
    yield_underlying_token_whale,
    user_wallet,
    bob,
    lego_book,
    governance
):
    """Test that governance can call addPriceSnapshot"""
    lego_id = lego_book.getRegId(mock_yield_lego)  # Get actual lego ID

    # Register vault token via deposit
    amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(user_wallet.address, amount, sender=yield_underlying_token_whale)
    user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, amount, sender=bob)

    # Time travel to allow another snapshot
    boa.env.time_travel(seconds=301)

    # Governance calls addPriceSnapshot
    result = switchboard_charlie.addPriceSnapshot(
        lego_id,
        yield_vault_token.address,
        sender=governance.address
    )

    # Verify it returns a boolean
    assert isinstance(result, bool)

    # Verify event was emitted
    logs = filter_logs(switchboard_charlie, "PriceSnapshotAdded")
    assert len(logs) >= 1
    assert logs[-1].legoId == lego_id
    assert logs[-1].legoAddr == mock_yield_lego.address
    assert logs[-1].vaultToken == yield_vault_token.address
    assert logs[-1].success == result
    assert logs[-1].caller == governance.address


def test_add_price_snapshot_security_action_can_call(
    switchboard_charlie,
    mock_yield_lego,
    yield_vault_token,
    yield_underlying_token,
    yield_underlying_token_whale,
    user_wallet,
    bob,
    lego_book,
    mission_control,
    switchboard_alpha,
    alice
):
    """Test that security action users can call addPriceSnapshot"""
    # Setup alice as security action user
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)

    lego_id = lego_book.getRegId(mock_yield_lego)  # Get actual lego ID

    # Register vault token via deposit
    amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(user_wallet.address, amount, sender=yield_underlying_token_whale)
    user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, amount, sender=bob)

    # Time travel to allow another snapshot
    boa.env.time_travel(seconds=301)

    # Alice (security action user) calls addPriceSnapshot
    result = switchboard_charlie.addPriceSnapshot(
        lego_id,
        yield_vault_token.address,
        sender=alice
    )

    # Verify it returns a boolean
    assert isinstance(result, bool)

    # Verify event was emitted
    logs = filter_logs(switchboard_charlie, "PriceSnapshotAdded")
    assert len(logs) >= 1
    assert logs[-1].legoId == lego_id
    assert logs[-1].legoAddr == mock_yield_lego.address
    assert logs[-1].vaultToken == yield_vault_token.address
    assert logs[-1].success == result
    assert logs[-1].caller == alice


def test_add_price_snapshot_unauthorized_fails(switchboard_charlie, yield_vault_token, alice):
    """Test that unauthorized users cannot call addPriceSnapshot"""
    lego_id = 2  # mock_yield_lego

    # Unauthorized user tries to call
    with boa.reverts("no perms"):
        switchboard_charlie.addPriceSnapshot(
            lego_id,
            yield_vault_token.address,
            sender=alice
        )


def test_add_price_snapshot_invalid_lego_id_fails(switchboard_charlie, yield_vault_token, governance):
    """Test that invalid lego id fails"""
    invalid_lego_id = 999  # non-existent lego

    with boa.reverts("invalid lego id"):
        switchboard_charlie.addPriceSnapshot(
            invalid_lego_id,
            yield_vault_token.address,
            sender=governance.address
        )


def test_add_price_snapshot_multiple_calls(
    switchboard_charlie,
    mock_yield_lego,
    yield_vault_token,
    yield_underlying_token,
    yield_underlying_token_whale,
    user_wallet,
    bob,
    lego_book,
    governance
):
    """Test multiple consecutive addPriceSnapshot calls"""
    lego_id = lego_book.getRegId(mock_yield_lego)  # Get actual lego ID

    # Register vault token via deposit
    amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(user_wallet.address, amount, sender=yield_underlying_token_whale)
    user_wallet.depositForYield(lego_id, yield_underlying_token, yield_vault_token, amount, sender=bob)

    # Time travel to allow another snapshot
    boa.env.time_travel(seconds=301)

    # First call
    result1 = switchboard_charlie.addPriceSnapshot(
        lego_id,
        yield_vault_token.address,
        sender=governance.address
    )
    assert isinstance(result1, bool)

    # Verify first event was emitted
    logs1 = filter_logs(switchboard_charlie, "PriceSnapshotAdded")
    assert len(logs1) >= 1
    assert logs1[-1].caller == governance.address

    # Time travel to allow another snapshot
    boa.env.time_travel(seconds=301)

    # Second call - should succeed without reverting
    result2 = switchboard_charlie.addPriceSnapshot(
        lego_id,
        yield_vault_token.address,
        sender=governance.address
    )
    assert isinstance(result2, bool)

    # Verify we can call it twice successfully (no revert)


# updateYieldPosition tests


def test_update_yield_position_governance_can_call(switchboard_charlie, undy_usd_vault, yield_vault_token, governance):
    """Test that governance can call updateYieldPosition"""
    # Call updateYieldPosition
    switchboard_charlie.updateYieldPosition(
        undy_usd_vault.address,
        yield_vault_token.address,
        sender=governance.address
    )

    # Verify event was emitted
    logs = filter_logs(switchboard_charlie, "YieldPositionUpdated")
    assert len(logs) >= 1
    assert logs[-1].vaultAddr == undy_usd_vault.address
    assert logs[-1].vaultToken == yield_vault_token.address
    assert logs[-1].caller == governance.address


def test_update_yield_position_security_action_can_call(switchboard_charlie, undy_usd_vault, yield_vault_token, mission_control, switchboard_alpha, alice):
    """Test that security action users can call updateYieldPosition"""
    # Setup alice as security action user
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)

    # Alice (security action user) calls updateYieldPosition
    switchboard_charlie.updateYieldPosition(
        undy_usd_vault.address,
        yield_vault_token.address,
        sender=alice
    )

    # Verify event was emitted
    logs = filter_logs(switchboard_charlie, "YieldPositionUpdated")
    assert len(logs) >= 1
    assert logs[-1].vaultAddr == undy_usd_vault.address
    assert logs[-1].vaultToken == yield_vault_token.address
    assert logs[-1].caller == alice


def test_update_yield_position_unauthorized_fails(switchboard_charlie, undy_usd_vault, yield_vault_token, alice):
    """Test that unauthorized users cannot call updateYieldPosition"""
    with boa.reverts("no perms"):
        switchboard_charlie.updateYieldPosition(
            undy_usd_vault.address,
            yield_vault_token.address,
            sender=alice
        )


def test_update_yield_position_invalid_vault_fails(switchboard_charlie, yield_vault_token, governance):
    """Test that invalid vault address is rejected"""
    invalid_vault = boa.env.generate_address()

    with boa.reverts("invalid vault addr"):
        switchboard_charlie.updateYieldPosition(
            invalid_vault,
            yield_vault_token.address,
            sender=governance.address
        )


# claimPerformanceFees tests


def test_claim_performance_fees_governance_can_call(switchboard_charlie, undy_usd_vault, governance):
    """Test that governance can call claimPerformanceFees"""
    # Call claimPerformanceFees
    amount = switchboard_charlie.claimPerformanceFees(
        undy_usd_vault.address,
        sender=governance.address
    )

    # Verify it returns a uint256
    assert isinstance(amount, int)
    assert amount >= 0

    # Verify event was emitted
    logs = filter_logs(switchboard_charlie, "PerformanceFeesClaimed")
    assert len(logs) >= 1
    assert logs[-1].vaultAddr == undy_usd_vault.address
    assert logs[-1].amount == amount
    assert logs[-1].caller == governance.address


def test_claim_performance_fees_security_action_can_call(switchboard_charlie, undy_usd_vault, mission_control, switchboard_alpha, alice):
    """Test that security action users can call claimPerformanceFees"""
    # Setup alice as security action user
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)

    # Alice (security action user) calls claimPerformanceFees
    amount = switchboard_charlie.claimPerformanceFees(
        undy_usd_vault.address,
        sender=alice
    )

    # Verify it returns a uint256
    assert isinstance(amount, int)
    assert amount >= 0

    # Verify event was emitted
    logs = filter_logs(switchboard_charlie, "PerformanceFeesClaimed")
    assert len(logs) >= 1
    assert logs[-1].vaultAddr == undy_usd_vault.address
    assert logs[-1].amount == amount
    assert logs[-1].caller == alice


def test_claim_performance_fees_unauthorized_fails(switchboard_charlie, undy_usd_vault, alice):
    """Test that unauthorized users cannot call claimPerformanceFees"""
    with boa.reverts("no perms"):
        switchboard_charlie.claimPerformanceFees(
            undy_usd_vault.address,
            sender=alice
        )


def test_claim_performance_fees_invalid_vault_fails(switchboard_charlie, governance):
    """Test that invalid vault address is rejected"""
    invalid_vault = boa.env.generate_address()

    with boa.reverts("invalid vault addr"):
        switchboard_charlie.claimPerformanceFees(
            invalid_vault,
            sender=governance.address
        )


# deregisterVaultTokenOnLego tests


def test_deregister_vault_token_on_lego_governance_can_call(
    switchboard_charlie,
    mock_yield_lego,
    yield_vault_token,
    yield_underlying_token,
    lego_book,
    governance
):
    """Test that governance can call deregisterVaultTokenOnLego"""
    lego_id = lego_book.getRegId(mock_yield_lego)

    # First register the vault token
    mock_yield_lego.registerVaultTokenLocally(
        yield_underlying_token.address,
        yield_vault_token.address,
        sender=switchboard_charlie.address
    )

    # Execute deregister (immediate, no timelock)
    result = switchboard_charlie.deregisterVaultTokenOnLego(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        sender=governance.address
    )

    # Verify it returns 0 (immediate execution)
    assert result == 0

    # Verify event was emitted
    logs = filter_logs(switchboard_charlie, "VaultTokenDeregisteredOnLego")
    assert len(logs) >= 1
    assert logs[-1].legoId == lego_id
    assert logs[-1].legoAddr == mock_yield_lego.address
    assert logs[-1].asset == yield_underlying_token.address
    assert logs[-1].vaultToken == yield_vault_token.address
    assert logs[-1].caller == governance.address


def test_deregister_vault_token_on_lego_security_action_can_call(
    switchboard_charlie,
    mock_yield_lego,
    yield_vault_token,
    yield_underlying_token,
    lego_book,
    mission_control,
    switchboard_alpha,
    alice
):
    """Test that security action users can call deregisterVaultTokenOnLego"""
    # Setup alice as security action user
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)

    lego_id = lego_book.getRegId(mock_yield_lego)

    # First register the vault token
    mock_yield_lego.registerVaultTokenLocally(
        yield_underlying_token.address,
        yield_vault_token.address,
        sender=switchboard_charlie.address
    )

    # Alice (security action user) calls deregisterVaultTokenOnLego
    result = switchboard_charlie.deregisterVaultTokenOnLego(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        sender=alice
    )

    # Verify it returns 0 (immediate execution)
    assert result == 0

    # Verify event was emitted
    logs = filter_logs(switchboard_charlie, "VaultTokenDeregisteredOnLego")
    assert len(logs) >= 1
    assert logs[-1].caller == alice


def test_deregister_vault_token_on_lego_unauthorized_fails(
    switchboard_charlie,
    yield_vault_token,
    yield_underlying_token,
    alice
):
    """Test that unauthorized users cannot call deregisterVaultTokenOnLego"""
    lego_id = 2  # mock_yield_lego

    with boa.reverts("no perms"):
        switchboard_charlie.deregisterVaultTokenOnLego(
            lego_id,
            yield_underlying_token.address,
            yield_vault_token.address,
            sender=alice
        )


def test_deregister_vault_token_on_lego_invalid_lego_id_fails(
    switchboard_charlie,
    yield_vault_token,
    yield_underlying_token,
    governance
):
    """Test that invalid lego id fails"""
    invalid_lego_id = 999

    with boa.reverts("invalid lego id"):
        switchboard_charlie.deregisterVaultTokenOnLego(
            invalid_lego_id,
            yield_underlying_token.address,
            yield_vault_token.address,
            sender=governance.address
        )


# registerVaultTokenOnLego tests


def test_register_vault_token_on_lego_governance_can_call(
    switchboard_charlie,
    mock_yield_lego,
    yield_vault_token,
    yield_underlying_token,
    lego_book,
    governance
):
    """Test that governance can call registerVaultTokenOnLego"""
    lego_id = lego_book.getRegId(mock_yield_lego)

    # Initiate registration (timelocked)
    aid = switchboard_charlie.registerVaultTokenOnLego(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        sender=governance.address
    )

    # Verify it returns an action ID (timelocked)
    assert aid > 0

    # Verify pending event was emitted
    logs = filter_logs(switchboard_charlie, "PendingRegisterVaultTokenOnLegoChange")
    assert len(logs) >= 1
    assert logs[-1].legoId == lego_id
    assert logs[-1].asset == yield_underlying_token.address
    assert logs[-1].vaultToken == yield_vault_token.address
    assert logs[-1].actionId == aid


def test_register_vault_token_on_lego_unauthorized_fails(
    switchboard_charlie,
    yield_vault_token,
    yield_underlying_token,
    alice
):
    """Test that unauthorized users cannot call registerVaultTokenOnLego"""
    lego_id = 2  # mock_yield_lego

    with boa.reverts("no perms"):
        switchboard_charlie.registerVaultTokenOnLego(
            lego_id,
            yield_underlying_token.address,
            yield_vault_token.address,
            sender=alice
        )


def test_register_vault_token_on_lego_invalid_lego_id_fails(
    switchboard_charlie,
    yield_vault_token,
    yield_underlying_token,
    governance
):
    """Test that invalid lego id fails"""
    invalid_lego_id = 999

    with boa.reverts("invalid lego id"):
        switchboard_charlie.registerVaultTokenOnLego(
            invalid_lego_id,
            yield_underlying_token.address,
            yield_vault_token.address,
            sender=governance.address
        )


def test_register_vault_token_on_lego_execution(
    switchboard_charlie,
    mock_yield_lego,
    yield_vault_token,
    yield_underlying_token,
    lego_book,
    governance
):
    """Test executing a registerVaultTokenOnLego action"""
    lego_id = lego_book.getRegId(mock_yield_lego)

    # Initiate registration
    aid = switchboard_charlie.registerVaultTokenOnLego(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        sender=governance.address
    )

    # Fast forward past timelock
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())

    # Execute the action
    success = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert success

    # Verify execution event was emitted
    logs = filter_logs(switchboard_charlie, "VaultTokenRegisteredOnLego")
    assert len(logs) >= 1
    assert logs[-1].legoId == lego_id
    assert logs[-1].legoAddr == mock_yield_lego.address
    assert logs[-1].asset == yield_underlying_token.address
    assert logs[-1].vaultToken == yield_vault_token.address


# setMorphoRewardsAddr tests


def test_set_morpho_rewards_addr_governance_can_call(
    switchboard_charlie,
    mock_yield_lego,
    lego_book,
    governance
):
    """Test that governance can call setMorphoRewardsAddr"""
    lego_id = lego_book.getRegId(mock_yield_lego)
    rewards_addr = boa.env.generate_address()

    # Initiate setting rewards address (timelocked)
    aid = switchboard_charlie.setMorphoRewardsAddr(
        lego_id,
        rewards_addr,
        sender=governance.address
    )

    # Verify it returns an action ID (timelocked)
    assert aid > 0

    # Verify pending event was emitted
    logs = filter_logs(switchboard_charlie, "PendingMorphoRewardsAddrChange")
    assert len(logs) >= 1
    assert logs[-1].legoId == lego_id
    assert logs[-1].rewardsAddr == rewards_addr
    assert logs[-1].actionId == aid


def test_set_morpho_rewards_addr_unauthorized_fails(
    switchboard_charlie,
    alice
):
    """Test that unauthorized users cannot call setMorphoRewardsAddr"""
    lego_id = 2
    rewards_addr = boa.env.generate_address()

    with boa.reverts("no perms"):
        switchboard_charlie.setMorphoRewardsAddr(
            lego_id,
            rewards_addr,
            sender=alice
        )


def test_set_morpho_rewards_addr_invalid_lego_id_fails(
    switchboard_charlie,
    governance
):
    """Test that invalid lego id fails"""
    invalid_lego_id = 999
    rewards_addr = boa.env.generate_address()

    with boa.reverts("invalid lego id"):
        switchboard_charlie.setMorphoRewardsAddr(
            invalid_lego_id,
            rewards_addr,
            sender=governance.address
        )


def test_set_morpho_rewards_addr_execution(
    switchboard_charlie,
    mock_yield_lego,
    lego_book,
    governance
):
    """Test executing a setMorphoRewardsAddr action"""
    lego_id = lego_book.getRegId(mock_yield_lego)
    rewards_addr = boa.env.generate_address()

    # Initiate setting rewards address
    aid = switchboard_charlie.setMorphoRewardsAddr(
        lego_id,
        rewards_addr,
        sender=governance.address
    )

    # Fast forward past timelock
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())

    # Execute the action
    success = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert success

    # Verify execution event was emitted
    logs = filter_logs(switchboard_charlie, "MorphoRewardsAddrSet")
    assert len(logs) >= 1
    assert logs[-1].legoId == lego_id
    assert logs[-1].legoAddr == mock_yield_lego.address
    assert logs[-1].rewardsAddr == rewards_addr


# setEulerRewardsAddr tests


def test_set_euler_rewards_addr_governance_can_call(
    switchboard_charlie,
    mock_yield_lego,
    lego_book,
    governance
):
    """Test that governance can call setEulerRewardsAddr"""
    lego_id = lego_book.getRegId(mock_yield_lego)
    rewards_addr = boa.env.generate_address()

    # Initiate setting rewards address (timelocked)
    aid = switchboard_charlie.setEulerRewardsAddr(
        lego_id,
        rewards_addr,
        sender=governance.address
    )

    # Verify it returns an action ID (timelocked)
    assert aid > 0

    # Verify pending event was emitted
    logs = filter_logs(switchboard_charlie, "PendingEulerRewardsAddrChange")
    assert len(logs) >= 1
    assert logs[-1].legoId == lego_id
    assert logs[-1].rewardsAddr == rewards_addr
    assert logs[-1].actionId == aid


def test_set_euler_rewards_addr_unauthorized_fails(
    switchboard_charlie,
    alice
):
    """Test that unauthorized users cannot call setEulerRewardsAddr"""
    lego_id = 2
    rewards_addr = boa.env.generate_address()

    with boa.reverts("no perms"):
        switchboard_charlie.setEulerRewardsAddr(
            lego_id,
            rewards_addr,
            sender=alice
        )


def test_set_euler_rewards_addr_invalid_lego_id_fails(
    switchboard_charlie,
    governance
):
    """Test that invalid lego id fails"""
    invalid_lego_id = 999
    rewards_addr = boa.env.generate_address()

    with boa.reverts("invalid lego id"):
        switchboard_charlie.setEulerRewardsAddr(
            invalid_lego_id,
            rewards_addr,
            sender=governance.address
        )


def test_set_euler_rewards_addr_execution(
    switchboard_charlie,
    mock_yield_lego,
    lego_book,
    governance
):
    """Test executing a setEulerRewardsAddr action"""
    lego_id = lego_book.getRegId(mock_yield_lego)
    rewards_addr = boa.env.generate_address()

    # Initiate setting rewards address
    aid = switchboard_charlie.setEulerRewardsAddr(
        lego_id,
        rewards_addr,
        sender=governance.address
    )

    # Fast forward past timelock
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())

    # Execute the action
    success = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert success

    # Verify execution event was emitted
    logs = filter_logs(switchboard_charlie, "EulerRewardsAddrSet")
    assert len(logs) >= 1
    assert logs[-1].legoId == lego_id
    assert logs[-1].legoAddr == mock_yield_lego.address
    assert logs[-1].rewardsAddr == rewards_addr


# setCompRewardsAddr tests


def test_set_comp_rewards_addr_governance_can_call(
    switchboard_charlie,
    mock_yield_lego,
    lego_book,
    governance
):
    """Test that governance can call setCompRewardsAddr"""
    lego_id = lego_book.getRegId(mock_yield_lego)
    rewards_addr = boa.env.generate_address()

    # Initiate setting rewards address (timelocked)
    aid = switchboard_charlie.setCompRewardsAddr(
        lego_id,
        rewards_addr,
        sender=governance.address
    )

    # Verify it returns an action ID (timelocked)
    assert aid > 0

    # Verify pending event was emitted
    logs = filter_logs(switchboard_charlie, "PendingCompRewardsAddrChange")
    assert len(logs) >= 1
    assert logs[-1].legoId == lego_id
    assert logs[-1].rewardsAddr == rewards_addr
    assert logs[-1].actionId == aid


def test_set_comp_rewards_addr_unauthorized_fails(
    switchboard_charlie,
    alice
):
    """Test that unauthorized users cannot call setCompRewardsAddr"""
    lego_id = 2
    rewards_addr = boa.env.generate_address()

    with boa.reverts("no perms"):
        switchboard_charlie.setCompRewardsAddr(
            lego_id,
            rewards_addr,
            sender=alice
        )


def test_set_comp_rewards_addr_invalid_lego_id_fails(
    switchboard_charlie,
    governance
):
    """Test that invalid lego id fails"""
    invalid_lego_id = 999
    rewards_addr = boa.env.generate_address()

    with boa.reverts("invalid lego id"):
        switchboard_charlie.setCompRewardsAddr(
            invalid_lego_id,
            rewards_addr,
            sender=governance.address
        )


def test_set_comp_rewards_addr_execution(
    switchboard_charlie,
    mock_yield_lego,
    lego_book,
    governance
):
    """Test executing a setCompRewardsAddr action"""
    lego_id = lego_book.getRegId(mock_yield_lego)
    rewards_addr = boa.env.generate_address()

    # Initiate setting rewards address
    aid = switchboard_charlie.setCompRewardsAddr(
        lego_id,
        rewards_addr,
        sender=governance.address
    )

    # Fast forward past timelock
    boa.env.time_travel(blocks=switchboard_charlie.actionTimeLock())

    # Execute the action
    success = switchboard_charlie.executePendingAction(aid, sender=governance.address)
    assert success

    # Verify execution event was emitted
    logs = filter_logs(switchboard_charlie, "CompRewardsAddrSet")
    assert len(logs) >= 1
    assert logs[-1].legoId == lego_id
    assert logs[-1].legoAddr == mock_yield_lego.address
    assert logs[-1].rewardsAddr == rewards_addr


##########################
# Sweep Leftovers Tests  #
##########################


def test_sweep_leftovers_success_by_governance(switchboard_charlie, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, governance):
    """Test that governance can successfully sweep leftovers from empty vault"""
    # Ensure vault has no shares
    assert undy_usd_vault.totalSupply() == 0

    # Give vault some leftover tokens
    leftover_amount = 1_000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, leftover_amount, sender=yield_underlying_token_whale)

    # Verify vault has balance
    assert yield_underlying_token.balanceOf(undy_usd_vault.address) == leftover_amount

    # Get governance balance before sweep
    gov_balance_before = yield_underlying_token.balanceOf(governance.address)

    # Sweep leftovers via switchboard
    amount = switchboard_charlie.sweepLeftovers(undy_usd_vault.address, sender=governance.address)

    # Verify amount returned
    assert amount == leftover_amount

    # Verify vault balance is 0
    assert yield_underlying_token.balanceOf(undy_usd_vault.address) == 0

    # Verify governance received the funds
    assert yield_underlying_token.balanceOf(governance.address) == gov_balance_before + leftover_amount

    # Verify event was emitted
    logs = filter_logs(switchboard_charlie, "LeftoversSwept")
    assert len(logs) >= 1
    assert logs[-1].vaultAddr == undy_usd_vault.address
    assert logs[-1].amount == leftover_amount
    assert logs[-1].caller == governance.address


def test_sweep_leftovers_success_by_security_action(switchboard_charlie, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, governance, mission_control, switchboard_alpha, alice):
    """Test that security action users can sweep leftovers from empty vault"""
    # Setup alice as security action user
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)

    # Ensure vault has no shares
    assert undy_usd_vault.totalSupply() == 0

    # Give vault some leftover tokens
    leftover_amount = 500 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, leftover_amount, sender=yield_underlying_token_whale)

    # Get governance balance before sweep
    gov_balance_before = yield_underlying_token.balanceOf(governance.address)

    # Sweep leftovers via switchboard as security action user
    amount = switchboard_charlie.sweepLeftovers(undy_usd_vault.address, sender=alice)

    # Verify success
    assert amount == leftover_amount
    assert yield_underlying_token.balanceOf(undy_usd_vault.address) == 0
    assert yield_underlying_token.balanceOf(governance.address) == gov_balance_before + leftover_amount

    # Verify event was emitted with alice as caller
    logs = filter_logs(switchboard_charlie, "LeftoversSwept")
    assert len(logs) >= 1
    assert logs[-1].vaultAddr == undy_usd_vault.address
    assert logs[-1].amount == leftover_amount
    assert logs[-1].caller == alice


def test_sweep_leftovers_fails_with_shares_outstanding(switchboard_charlie, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, governance, alice):
    """Test that sweeping fails when vault has shares outstanding"""
    # Have Alice deposit to get shares
    deposit_amount = 10_000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(alice, deposit_amount, sender=yield_underlying_token_whale)
    yield_underlying_token.approve(undy_usd_vault.address, deposit_amount, sender=alice)
    undy_usd_vault.deposit(deposit_amount, alice, sender=alice)

    # Verify totalSupply is not 0
    assert undy_usd_vault.totalSupply() > 0

    # Give vault some additional leftover tokens
    leftover_amount = 1_000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, leftover_amount, sender=yield_underlying_token_whale)

    # Try to sweep - should fail because shares are outstanding
    with boa.reverts("shares outstanding"):
        switchboard_charlie.sweepLeftovers(undy_usd_vault.address, sender=governance.address)


def test_sweep_leftovers_fails_unauthorized(switchboard_charlie, undy_usd_vault, yield_underlying_token, yield_underlying_token_whale, alice):
    """Test that unauthorized users cannot sweep leftovers"""
    # Give vault some leftover tokens
    leftover_amount = 1_000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(undy_usd_vault.address, leftover_amount, sender=yield_underlying_token_whale)

    # Try to sweep as unauthorized user - should fail
    with boa.reverts("no perms"):
        switchboard_charlie.sweepLeftovers(undy_usd_vault.address, sender=alice)


def test_sweep_leftovers_fails_no_balance(switchboard_charlie, undy_usd_vault, yield_underlying_token, governance):
    """Test that sweeping fails when there's no balance to sweep"""
    # Ensure vault has no shares and no balance
    assert undy_usd_vault.totalSupply() == 0
    assert yield_underlying_token.balanceOf(undy_usd_vault.address) == 0

    # Try to sweep - should fail because no balance
    with boa.reverts("no balance"):
        switchboard_charlie.sweepLeftovers(undy_usd_vault.address, sender=governance.address)


def test_sweep_leftovers_fails_invalid_vault(switchboard_charlie, governance):
    """Test that sweeping fails for invalid vault address"""
    # Try to sweep from a non-vault address - should fail
    with boa.reverts("invalid vault addr"):
        switchboard_charlie.sweepLeftovers(boa.env.generate_address(), sender=governance.address)
