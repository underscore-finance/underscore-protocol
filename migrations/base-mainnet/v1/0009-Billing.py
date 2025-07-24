from scripts.utils.migration import Migration


def migrate(migration: Migration):
    migration.log.h2("Billing")
    hq = migration.get_contract("UndyHq")

    billing = migration.deploy(
        'Billing',
        hq,
        migration.blueprint.TOKENS["WETH"],
        migration.blueprint.TOKENS["ETH"],
    )

    assert migration.execute(hq.startAddNewAddressToRegistry, billing, "Billing")
    assert migration.execute(hq.confirmNewAddressToRegistry, billing) == 9
