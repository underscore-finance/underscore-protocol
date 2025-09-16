from scripts.utils.migration import Migration


def migrate(migration: Migration):
    hq = migration.get_address("UndyHq")
    migration.deploy(
        'RipeLego',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
    )
    migration.deploy(
        'UndyRewardsLego',
        hq,
        migration.blueprint.TOKENS["RIPE"],
    )
