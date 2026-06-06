from scripts.utils.migration import Migration


def migrate(migration: Migration):
    # Initialize the freshly deployed WalletBackpack with all 7 items while the
    # deployer still holds temp gov (action time lock is 0 during setup), then
    # lock it down and relinquish gov to protocol governance.
    #
    # Remaining cutover steps are governance-timelocked and run separately
    # (see docs/deploy-checklist.md):
    #   - rotate this WalletBackpack into UndyHq reg id 8
    #   - SwitchboardAlpha.setUserWalletTemplates (new UserWallet/UserWalletConfig)
    #   - register the new Hatchery + AgentWrapper/senders + Switchboards
    #   - instant-action flag / Hatchery-default cutover via SwitchboardBravo
    migration.log.h2("Finish Setup - Wallet Backpack")
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

    migration.execute(wallet_backpack.addPendingActionDataProvider, migration.get_address("ActionDataProvider"))
    migration.execute(wallet_backpack.confirmPendingActionDataProvider)

    # Lock in the post-setup action time lock, then hand off governance.
    migration.execute(wallet_backpack.setActionTimeLockAfterSetup)
    migration.execute(wallet_backpack.relinquishGov)
