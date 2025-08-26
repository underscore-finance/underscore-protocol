from scripts.utils.migration import Migration


def migrate(migration: Migration):
    hq = migration.get_address("UndyHq")

    migration.deploy(
        'Tokemak',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["TOKEMAK_REGISTRY"],
    )
