from scripts.utils.migration import Migration


def migrate(migration: Migration):
    hq = migration.get_address("UndyHq")

    migration.deploy(
        'LootDistributor',
        hq,
        migration.blueprint.TOKENS["RIPE"],
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
        migration.blueprint.PARAMS["LOOT_DISTRIBUTOR_RIPE_STAKE_RATIO"],
        migration.blueprint.PARAMS["LOOT_DISTRIBUTOR_RIPE_LOCK_DURATION"],
    )
