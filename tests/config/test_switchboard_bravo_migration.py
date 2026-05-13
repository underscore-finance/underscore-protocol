import pytest
import boa

from constants import EIGHTEEN_DECIMALS
from contracts.core.userWallet import UserWallet, UserWalletConfig


@pytest.fixture(scope="module")
def prepareAssetForMigration(alpha_token, alpha_token_whale, mock_ripe, switchboard, switchboard_alpha):
    def prepareAssetForMigration(
        _wallet,
        _asset=alpha_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=alpha_token_whale,
        _price=2 * EIGHTEEN_DECIMALS,
    ):
        mock_ripe.setPrice(_asset, _price)
        _asset.transfer(_wallet, _amount, sender=_whale)

        wallet_config = UserWalletConfig.at(_wallet.walletConfig())
        wallet_config.updateAssetData(0, _asset, False, sender=switchboard_alpha.address)
        return _amount

    yield prepareAssetForMigration


def _time_travel_to_pending_confirmation(from_wallet):
    pending = UserWalletConfig.at(from_wallet.walletConfig()).pendingMigration()
    blocks = pending.confirmBlock - boa.env.evm.patch.block_number
    if blocks > 0:
        boa.env.time_travel(blocks=blocks)
    return pending


def test_switchboard_bravo_can_initiate_and_migrate_wallet(
    switchboard,
    switchboard_bravo,
    migrator,
    user_wallet,
    hatchery,
    bob,
    governance,
    alpha_token,
    prepareAssetForMigration,
):
    to_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    amount = prepareAssetForMigration(user_wallet, alpha_token)

    assert switchboard_bravo.initiateWalletMigration(migrator, user_wallet, to_wallet, sender=governance.address)
    _time_travel_to_pending_confirmation(user_wallet)

    num_funds_migrated, did_migrate_config = switchboard_bravo.migrateWallet(
        migrator,
        user_wallet,
        to_wallet,
        sender=governance.address,
    )

    assert num_funds_migrated == 1
    assert did_migrate_config is True
    assert alpha_token.balanceOf(user_wallet) == 0
    assert alpha_token.balanceOf(to_wallet) == amount
    assert UserWalletConfig.at(user_wallet.walletConfig()).pendingMigration().confirmBlock == 0


def test_switchboard_bravo_can_call_funds_and_config_wrappers(
    switchboard,
    switchboard_bravo,
    migrator,
    hatchery,
    bob,
    governance,
    alpha_token,
    prepareAssetForMigration,
):
    from_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    to_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    amount = prepareAssetForMigration(from_wallet, alpha_token)

    aid = switchboard_bravo.setInstantMigrationEnabled(migrator, True, sender=governance.address)
    assert aid != 0
    pending_enable = switchboard_bravo.pendingInstantMigrationEnable()
    assert pending_enable.actionId == aid
    assert pending_enable.migrator == migrator.address
    assert not migrator.instantMigrationEnabled()
    assert not switchboard_bravo.executePendingAction(aid, sender=governance.address)

    confirmation_block = switchboard_bravo.getActionConfirmationBlock(aid)
    blocks = confirmation_block - boa.env.evm.patch.block_number
    boa.env.time_travel(blocks=blocks)
    assert switchboard_bravo.executePendingAction(aid, sender=governance.address)
    assert switchboard_bravo.pendingInstantMigrationEnable().actionId == 0
    assert migrator.instantMigrationEnabled()

    assert switchboard_bravo.migrateWalletFunds(migrator, from_wallet, to_wallet, sender=governance.address) == 1
    assert switchboard_bravo.cloneWalletConfig(migrator, from_wallet, to_wallet, sender=governance.address) is True
    assert switchboard_bravo.setInstantMigrationEnabled(migrator, False, sender=governance.address) == 0
    assert not migrator.instantMigrationEnabled()

    assert alpha_token.balanceOf(from_wallet) == 0
    assert alpha_token.balanceOf(to_wallet) == amount


def test_switchboard_bravo_disabling_cancels_pending_instant_migration_enable(
    switchboard_bravo,
    migrator,
    governance,
    alice,
    mission_control,
):
    aid = switchboard_bravo.setInstantMigrationEnabled(migrator, True, sender=governance.address)
    assert switchboard_bravo.pendingInstantMigrationEnable().actionId == aid
    assert switchboard_bravo.hasPendingAction(aid)

    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_bravo.address)

    assert switchboard_bravo.setInstantMigrationEnabled(migrator, False, sender=alice) == 0

    assert switchboard_bravo.pendingInstantMigrationEnable().actionId == 0
    assert not switchboard_bravo.hasPendingAction(aid)
    assert not switchboard_bravo.executePendingAction(aid, sender=governance.address)
    assert not migrator.instantMigrationEnabled()


def test_switchboard_bravo_rejects_duplicate_pending_instant_migration_enable(
    switchboard_bravo,
    migrator,
    governance,
):
    aid = switchboard_bravo.setInstantMigrationEnabled(migrator, True, sender=governance.address)
    assert switchboard_bravo.pendingInstantMigrationEnable().actionId == aid

    with boa.reverts("pending enable exists"):
        switchboard_bravo.setInstantMigrationEnabled(migrator, True, sender=governance.address)


def test_cancel_pending_action_cancels_pending_instant_migration_enable_and_allows_restaging(
    switchboard_bravo,
    migrator,
    governance,
):
    aid = switchboard_bravo.setInstantMigrationEnabled(migrator, True, sender=governance.address)
    assert switchboard_bravo.pendingInstantMigrationEnable().actionId == aid

    assert switchboard_bravo.cancelPendingAction(aid, sender=governance.address)

    assert not switchboard_bravo.hasPendingAction(aid)
    assert switchboard_bravo.pendingInstantMigrationEnable().actionId == aid

    new_aid = switchboard_bravo.setInstantMigrationEnabled(migrator, True, sender=governance.address)
    assert new_aid != aid
    assert switchboard_bravo.pendingInstantMigrationEnable().actionId == new_aid
    assert switchboard_bravo.hasPendingAction(new_aid)


def test_security_signer_can_disable_instant_migration(
    switchboard_bravo,
    migrator,
    governance,
    alice,
    mission_control,
):
    aid = switchboard_bravo.setInstantMigrationEnabled(migrator, True, sender=governance.address)
    confirmation_block = switchboard_bravo.getActionConfirmationBlock(aid)
    blocks = confirmation_block - boa.env.evm.patch.block_number
    boa.env.time_travel(blocks=blocks)
    assert switchboard_bravo.executePendingAction(aid, sender=governance.address)
    assert migrator.instantMigrationEnabled()

    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_bravo.address)

    assert switchboard_bravo.setInstantMigrationEnabled(migrator, False, sender=alice) == 0
    assert not migrator.instantMigrationEnabled()


def test_switchboard_bravo_rejects_unregistered_migrator(
    switchboard_bravo,
    user_wallet,
    hatchery,
    bob,
    alice,
    governance,
):
    to_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))

    with boa.reverts("invalid migrator"):
        switchboard_bravo.setInstantMigrationEnabled(alice, True, sender=governance.address)

    with boa.reverts("invalid migrator"):
        switchboard_bravo.setInstantMigrationEnabled(alice, False, sender=governance.address)

    with boa.reverts("invalid migrator"):
        switchboard_bravo.initiateWalletMigration(alice, user_wallet, to_wallet, sender=governance.address)

    with boa.reverts("invalid migrator"):
        switchboard_bravo.migrateWalletFunds(alice, user_wallet, to_wallet, sender=governance.address)

    with boa.reverts("invalid migrator"):
        switchboard_bravo.cloneWalletConfig(alice, user_wallet, to_wallet, sender=governance.address)

    with boa.reverts("invalid migrator"):
        switchboard_bravo.migrateWallet(alice, user_wallet, to_wallet, sender=governance.address)


def test_switchboard_bravo_migration_requires_governance(
    switchboard,
    switchboard_bravo,
    migrator,
    user_wallet,
    hatchery,
    bob,
    alice,
    mission_control,
):
    to_wallet = UserWallet.at(hatchery.createUserWallet(sender=bob))
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_bravo.address)

    with boa.reverts("no perms"):
        switchboard_bravo.initiateWalletMigration(migrator, user_wallet, to_wallet, sender=alice)

    with boa.reverts("no perms"):
        switchboard_bravo.setInstantMigrationEnabled(migrator, True, sender=alice)

    with boa.reverts("no perms"):
        switchboard_bravo.migrateWallet(migrator, user_wallet, to_wallet, sender=alice)
