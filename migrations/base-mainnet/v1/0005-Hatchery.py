from scripts.utils.migration import Migration


def migrate(migration: Migration):
    migration.log.h2("Hatchery")
    hq = migration.get_contract("UndyHq")

    hatchery = migration.deploy(
        'Hatchery',
        hq,
        migration.blueprint.TOKENS["WETH"],
        migration.blueprint.TOKENS["ETH"],
    )

    assert migration.execute(hq.startAddNewAddressToRegistry, hatchery, "Hatchery")
    assert migration.execute(hq.confirmNewAddressToRegistry, hatchery) == 5
