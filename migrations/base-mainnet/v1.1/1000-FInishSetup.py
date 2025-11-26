from scripts.utils.migration import Migration


def migrate(migration: Migration):
    migration.log.h2("Finish Setup")

    switchboard_alpha = migration.get_contract("SwitchboardAlpha")
    migration.execute(switchboard_alpha.relinquishGov)

    switchboard_bravo = migration.get_contract("SwitchboardBravo")
    migration.execute(switchboard_bravo.relinquishGov)

    switchboard_charlie = migration.get_contract("SwitchboardCharlie")
    migration.execute(switchboard_charlie.relinquishGov)

    wallet_backpack = migration.get_contract("WalletBackpack")
    migration.execute(wallet_backpack.relinquishGov)

    switchboard = migration.get_contract("Switchboard")
    migration.execute(switchboard.relinquishGov)

    lego_book = migration.get_contract("LegoBook")
    migration.execute(lego_book.relinquishGov)

    vault_registry = migration.get_contract("VaultRegistry")
    migration.execute(vault_registry.relinquishGov)

    # # TO DO AFTER MIGRATION
    return

    wallet_backpack = migration.get_contract("WalletBackpack")
    migration.execute(wallet_backpack.addPendingKernel, migration.get_address("Kernel"))
    migration.execute(wallet_backpack.confirmPendingKernel)

    migration.execute(wallet_backpack.addPendingSentinel, migration.get_address("Sentinel"))
    migration.execute(wallet_backpack.confirmPendingSentinel)

    migration.execute(wallet_backpack.addPendingHighCommand, migration.get_address("HighCommand"))
    migration.execute(wallet_backpack.confirmPendingHighCommand)

    migration.execute(wallet_backpack.addPendingPaymaster, migration.get_address("Paymaster"))
    migration.execute(wallet_backpack.confirmPendingPaymaster)

    migration.execute(wallet_backpack.addPendingChequeBook, migration.get_address("ChequeBook"))
    migration.execute(wallet_backpack.confirmPendingChequeBook)

    migration.execute(wallet_backpack.addPendingMigrator, migration.get_address("Migrator"))
    migration.execute(wallet_backpack.confirmPendingMigrator)

    # some config
    actionId = migration.execute(switchboard_alpha.setCreatorWhitelist,
                                 migration.blueprint.INTEGRATION_ADDYS["WALLET_CREATOR"],
                                 True)
    migration.execute(switchboard_alpha.executePendingAction, actionId)

    actionId = migration.execute(switchboard_alpha.addSender,
                                 migration.get_address("AgentWrapper"),
                                 migration.get_address("AgentSenderGeneric"),
                                 True)
    migration.execute(switchboard_alpha.executePendingAction, actionId)

    actionId = migration.execute(switchboard_alpha.addSender,
                                 migration.get_address("AgentWrapper"),
                                 migration.get_address("AgentSenderSpecial"),
                                 True)
    migration.execute(switchboard_alpha.executePendingAction, actionId)
