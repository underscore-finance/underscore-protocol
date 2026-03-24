from scripts.utils.migration import Migration


def migrate(migration: Migration):
    hq = migration.get_contract("UndyHq")
    migration.deploy(
        '40Acres',
        hq,
        migration.blueprint.TOKENS["FORTY_ACRES_USDC"],
        migration.blueprint.INTEGRATION_ADDYS["FORTY_ACRES_LOANS"],
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
    )
