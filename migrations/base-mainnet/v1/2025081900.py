from scripts.utils.migration import Migration


def migrate(migration: Migration):
    migration.deploy_bp("AgentWrapper")
    migration.deploy('SignatureHelper')

    hq = migration.get_address("UndyHq")
    migration.deploy(
        'SwitchboardAlpha',
        hq,
        migration.blueprint.CONSTANTS.ZERO_ADDRESS,
        migration.blueprint.PARAMS["GEN_MIN_CONFIG_TIMELOCK"],
        migration.blueprint.PARAMS["GEN_MAX_CONFIG_TIMELOCK"],
    )
    migration.deploy(
        'LootDistributor',
        hq,
        migration.blueprint.TOKENS["RIPE"],
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
        migration.blueprint.PARAMS["LOOT_DISTRIBUTOR_RIPE_LOCK_DURATION"],
    )
