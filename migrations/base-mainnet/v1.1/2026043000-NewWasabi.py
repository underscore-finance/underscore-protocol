from scripts.utils.migration import Migration


def migrate(migration: Migration):
    hq = migration.get_contract("UndyHq")
    wasabi_lego = migration.deploy(
        'Wasabi',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["WASABI_LONG_POOL"],
        migration.blueprint.INTEGRATION_ADDYS["WASABI_SHORT_POOL"],
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
    )
