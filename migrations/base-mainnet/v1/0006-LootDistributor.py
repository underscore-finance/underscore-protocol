from scripts.utils.migration import Migration


def migrate(migration: Migration):
    migration.log.h2("Loot Distributor")
    hq = migration.get_contract("UndyHq")

    loot_distributor = migration.deploy(
        'LootDistributor',
        hq,
    )

    assert migration.execute(hq.startAddNewAddressToRegistry, loot_distributor, "Loot Distributor")
    assert migration.execute(hq.confirmNewAddressToRegistry, loot_distributor) == 6
