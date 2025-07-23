from scripts.utils.migration import Migration


def migrate(migration: Migration):
    migration.log.h2("Appraiser")
    hq = migration.get_contract("UndyHq")

    appraiser = migration.deploy(
        'Appraiser',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
        migration.blueprint.TOKENS["WETH"],
        migration.blueprint.TOKENS["ETH"],
    )

    assert migration.execute(hq.startAddNewAddressToRegistry, appraiser, "Appraiser")
    assert migration.execute(hq.confirmNewAddressToRegistry, appraiser) == 7
