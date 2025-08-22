from scripts.utils.migration import Migration


def migrate(migration: Migration):
    hq = migration.get_address("UndyHq")

    migration.deploy(
        'Yo',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["YO_REGISTRY"],
    )
