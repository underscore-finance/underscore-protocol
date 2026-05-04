from scripts.utils.migration import Migration


def migrate(migration: Migration):
    hq = migration.get_contract("UndyHq")

    migration.deploy(
        'LootDistributor',
        hq,
        migration.blueprint.TOKENS["RIPE"],
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
    )

    migration.deploy(
        'RipeLego',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
        migration.blueprint.TOKENS["USDC"],
    )
