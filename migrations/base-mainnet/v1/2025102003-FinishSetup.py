from scripts.utils.migration import Migration


def migrate(migration: Migration):
    lego_book = migration.get_contract('LegoBook')
    vault_registry = migration.get_contract('VaultRegistry')
    switchboard_charlie = migration.get_contract('SwitchboardCharlie')

    migration.execute(lego_book.setRegistryTimeLockAfterSetup)
    migration.execute(lego_book.relinquishGov)

    migration.execute(vault_registry.setRegistryTimeLockAfterSetup)
    migration.execute(vault_registry.relinquishGov)

    migration.execute(switchboard_charlie.setActionTimeLockAfterSetup)
    migration.execute(switchboard_charlie.relinquishGov)
