from scripts.utils.migration import Migration


def migrate(migration: Migration):
    hq = migration.get_address("UndyHq")

    loot_distributor = migration.deploy(
        'LootDistributor',
        hq,
        migration.blueprint.TOKENS["RIPE"],
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
        migration.blueprint.PARAMS["LOOT_DISTRIBUTOR_RIPE_STAKE_RATIO"],
        migration.blueprint.PARAMS["LOOT_DISTRIBUTOR_RIPE_LOCK_DURATION"],
    )

    switchboard_alpha = migration.deploy(
        'SwitchboardAlpha',
        hq,
        migration.blueprint.CONSTANTS.ZERO_ADDRESS,
        migration.blueprint.PARAMS["GEN_MIN_CONFIG_TIMELOCK"],
        migration.blueprint.PARAMS["GEN_MAX_CONFIG_TIMELOCK"],
    )

    switchboard_charlie = migration.deploy(
        'SwitchboardCharlie',
        hq,
        migration.blueprint.CONSTANTS.ZERO_ADDRESS,
        migration.blueprint.PARAMS["GEN_MIN_CONFIG_TIMELOCK"],
        migration.blueprint.PARAMS["GEN_MAX_CONFIG_TIMELOCK"],
    )
