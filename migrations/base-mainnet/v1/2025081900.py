from scripts.utils.migration import Migration


def migrate(migration: Migration):
    hq = migration.get_address("UndyHq")

    aw =migration.deploy_bp("AgentWrapper")
    migration.deploy('SignatureHelper')

    sb_alpha = migration.deploy(
        'SwitchboardAlpha',
        hq,
        migration.account,
        migration.blueprint.PARAMS["GEN_MIN_CONFIG_TIMELOCK"],
        migration.blueprint.PARAMS["GEN_MAX_CONFIG_TIMELOCK"],
    )
    migration.execute(sb_alpha.setAgentTemplate, aw)
    migration.execute(sb_alpha.setActionTimeLockAfterSetup)
    migration.execute(sb_alpha.relinquishGov)

    migration.deploy(
        'LootDistributor',
        hq,
        migration.blueprint.TOKENS["RIPE"],
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
        migration.blueprint.PARAMS["LOOT_DISTRIBUTOR_RIPE_LOCK_DURATION"],
    )
