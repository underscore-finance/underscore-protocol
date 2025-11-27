from scripts.utils.migration import Migration


def migrate(migration: Migration):
    migration.log.h2("Appraiser")
    hq = migration.get_contract("UndyHq")

    migration.deploy(
        'Appraiser',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
    )
