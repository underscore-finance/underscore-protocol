import boa

from config.BluePrint import TOKENS
from conf_utils import fresh_user_wallet
from constants import ACTION_TYPE, ZERO_ADDRESS


def _assert_base_action_data(ad, wallet, config, signer, ledger, mission_control, lego_book, hatchery, loot_distributor, appraiser, billing, vault_registry, eth, weth):
    assert ad.ledger == ledger.address
    assert ad.missionControl == mission_control.address
    assert ad.legoBook == lego_book.address
    assert ad.hatchery == hatchery.address
    assert ad.lootDistributor == loot_distributor.address
    assert ad.appraiser == appraiser.address
    assert ad.billing == billing.address
    assert ad.vaultRegistry == vault_registry.address
    assert ad.wallet == wallet.address
    assert ad.walletConfig == config.address
    assert ad.walletOwner == config.owner()
    assert ad.inEjectMode == config.inEjectMode()
    assert ad.isFrozen == config.isFrozen()
    assert ad.lastTotalUsdValue == ledger.getLastTotalUsdValue(wallet.address)
    assert ad.signer == signer
    assert ad.isManager == (config.indexOfManager(signer) != 0)
    assert ad.eth == eth
    assert ad.weth == weth.address


def _action_data_tuple(ad):
    return (
        ad.ledger,
        ad.missionControl,
        ad.legoBook,
        ad.hatchery,
        ad.lootDistributor,
        ad.appraiser,
        ad.billing,
        ad.vaultRegistry,
        ad.wallet,
        ad.walletConfig,
        ad.walletOwner,
        ad.inEjectMode,
        ad.isFrozen,
        ad.lastTotalUsdValue,
        ad.signer,
        ad.isManager,
        ad.legoId,
        ad.legoAddr,
        ad.eth,
        ad.weth,
    )


def test_action_data_provider_returns_expected_bundle(
    action_data_provider,
    hatchery,
    bob,
    undy_hq_deploy,
    ledger,
    mission_control,
    lego_book,
    loot_distributor,
    appraiser,
    billing,
    vault_registry,
    weth,
    fork,
):
    wallet, config = fresh_user_wallet(hatchery, bob)
    lego_id = 2

    ad = action_data_provider.getActionDataBundle(
        config.address,
        lego_id,
        bob,
        undy_hq_deploy.address,
        TOKENS[fork]["ETH"],
        weth.address,
    )

    _assert_base_action_data(
        ad,
        wallet,
        config,
        bob,
        ledger,
        mission_control,
        lego_book,
        hatchery,
        loot_distributor,
        appraiser,
        billing,
        vault_registry,
        TOKENS[fork]["ETH"],
        weth,
    )
    assert ad.legoId == lego_id
    assert ad.legoAddr == lego_book.getAddr(lego_id)


def test_action_data_provider_handles_empty_lego_id(
    action_data_provider,
    hatchery,
    bob,
    undy_hq_deploy,
    weth,
    fork,
):
    wallet, config = fresh_user_wallet(hatchery, bob)

    ad = action_data_provider.getActionDataBundle(
        config.address,
        0,
        bob,
        undy_hq_deploy.address,
        TOKENS[fork]["ETH"],
        weth.address,
    )

    assert ad.wallet == wallet.address
    assert ad.walletConfig == config.address
    assert ad.legoId == 0
    assert ad.legoAddr == ZERO_ADDRESS


def test_action_data_provider_handles_empty_registry_addresses(
    action_data_provider,
    hatchery,
    bob,
    weth,
    fork,
):
    empty_registry = boa.load("contracts/mock/MockEmptyRegistry.vy", name="empty_registry")
    wallet, config = fresh_user_wallet(hatchery, bob)

    ad = action_data_provider.getActionDataBundle(
        config.address,
        2,
        bob,
        empty_registry.address,
        TOKENS[fork]["ETH"],
        weth.address,
    )

    assert ad.ledger == ZERO_ADDRESS
    assert ad.missionControl == ZERO_ADDRESS
    assert ad.legoBook == ZERO_ADDRESS
    assert ad.hatchery == ZERO_ADDRESS
    assert ad.lootDistributor == ZERO_ADDRESS
    assert ad.appraiser == ZERO_ADDRESS
    assert ad.billing == ZERO_ADDRESS
    assert ad.vaultRegistry == ZERO_ADDRESS
    assert ad.wallet == wallet.address
    assert ad.walletConfig == config.address
    assert ad.walletOwner == bob
    assert ad.lastTotalUsdValue == 0
    assert ad.legoAddr == ZERO_ADDRESS


def test_user_wallet_config_action_data_wrapper_matches_provider(
    action_data_provider,
    hatchery,
    bob,
    undy_hq_deploy,
    weth,
    fork,
):
    _wallet, config = fresh_user_wallet(hatchery, bob)
    lego_id = 2

    direct = action_data_provider.getActionDataBundle(
        config.address,
        lego_id,
        bob,
        undy_hq_deploy.address,
        TOKENS[fork]["ETH"],
        weth.address,
    )
    wrapped = config.getActionDataBundle(lego_id, bob)

    assert _action_data_tuple(wrapped) == _action_data_tuple(direct)


def test_user_wallet_config_permission_wrapper_uses_provider(
    hatchery,
    bob,
    weth,
    fork,
):
    wallet, config = fresh_user_wallet(hatchery, bob)

    ad = config.checkSignerPermissionsAndGetBundle(
        bob,
        ACTION_TYPE.TRANSFER,
        [],
        [],
        ZERO_ADDRESS,
    )

    assert ad.wallet == wallet.address
    assert ad.walletConfig == config.address
    assert ad.walletOwner == bob
    assert ad.signer == bob
    assert ad.eth == TOKENS[fork]["ETH"]
    assert ad.weth == weth.address


def test_action_data_provider_billing_signer_short_circuits_permission_check(
    action_data_provider,
    hatchery,
    bob,
    billing,
    undy_hq_deploy,
    weth,
    fork,
):
    wallet, config = fresh_user_wallet(hatchery, bob)

    ad = action_data_provider.checkSignerPermissionsAndGetBundle(
        config.address,
        billing.address,
        ACTION_TYPE.TRANSFER,
        undy_hq_deploy.address,
        TOKENS[fork]["ETH"],
        weth.address,
        ZERO_ADDRESS,
        [],
        [],
        ZERO_ADDRESS,
    )

    assert ad.wallet == wallet.address
    assert ad.walletConfig == config.address
    assert ad.signer == billing.address
    assert ad.billing == billing.address


def test_action_data_provider_clears_whitelisted_recipient_for_manager_permission(
    action_data_provider,
    hatchery,
    bob,
    alice,
    sally,
    charlie,
    high_command,
    kernel,
    sentinel,
    undy_hq_deploy,
    weth,
    fork,
    createManagerLimits,
    createLegoPerms,
    createSwapPerms,
    createWhitelistPerms,
    createTransferPerms,
):
    with boa.env.anchor():
        wallet, config = fresh_user_wallet(hatchery, bob)
        transfer_perms = createTransferPerms(_allowedPayees=[charlie])

        assert high_command.addManager(
            wallet.address,
            alice,
            createManagerLimits(),
            createLegoPerms(),
            createSwapPerms(),
            createWhitelistPerms(),
            transfer_perms,
            [],
            False,
            0,
            config.timeLock() * 2,
            sender=bob,
        )
        kernel.addPendingWhitelistAddr(wallet.address, sally, sender=bob)
        boa.env.time_travel(blocks=config.timeLock())
        kernel.confirmWhitelistAddr(wallet.address, sally, sender=bob)

        with boa.reverts("no permission"):
            action_data_provider.checkSignerPermissionsAndGetBundle(
                config.address,
                alice,
                ACTION_TYPE.TRANSFER,
                undy_hq_deploy.address,
                TOKENS[fork]["ETH"],
                weth.address,
                sentinel.address,
                [],
                [],
                bob,
            )

        ad = action_data_provider.checkSignerPermissionsAndGetBundle(
            config.address,
            alice,
            ACTION_TYPE.TRANSFER,
            undy_hq_deploy.address,
            TOKENS[fork]["ETH"],
            weth.address,
            sentinel.address,
            [],
            [],
            sally,
        )

        assert ad.wallet == wallet.address
        assert ad.signer == alice
        assert ad.isManager is True


def test_existing_wallet_config_keeps_captured_action_data_provider_after_backpack_rotation(
    hatchery,
    bob,
    wallet_backpack_deploy,
    governance,
):
    with boa.env.anchor():
        _wallet, config = fresh_user_wallet(hatchery, bob)
        original = config.getActionDataBundle(0, bob)
        replacement = boa.load("contracts/mock/MockRando.vy", name="bad_action_data_provider")

        assert wallet_backpack_deploy.addPendingActionDataProvider(replacement.address, sender=governance.address)
        boa.env.time_travel(blocks=wallet_backpack_deploy.actionTimeLock())
        assert wallet_backpack_deploy.confirmPendingActionDataProvider(sender=governance.address)
        assert wallet_backpack_deploy.actionDataProvider() == replacement.address

        after_rotation = config.getActionDataBundle(0, bob)
        assert _action_data_tuple(after_rotation) == _action_data_tuple(original)

        _new_wallet, new_config = fresh_user_wallet(hatchery, bob)
        with boa.reverts():
            new_config.getActionDataBundle(0, bob)
