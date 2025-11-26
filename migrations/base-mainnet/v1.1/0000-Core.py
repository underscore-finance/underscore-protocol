from scripts.utils.migration import Migration


def migrate(migration: Migration):
    migration.log.h2("Core")

    hq = migration.get_address("UndyHq")

    user_wallet_template = migration.deploy_bp("UserWallet")
    user_wallet_config_template = migration.deploy_bp("UserWalletConfig")
    agent_wrapper = migration.deploy("AgentWrapper", hq, 1)
    migration.deploy(
        "AgentSenderGeneric",
        hq,
        migration.blueprint.INTEGRATION_ADDYS["AGENT_OWNER"],
        migration.blueprint.PARAMS["UNDY_HQ_MIN_GOV_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_GOV_TIMELOCK"],
    )
    migration.deploy(
        "AgentSenderSpecial",
        hq,
        migration.blueprint.INTEGRATION_ADDYS["AGENT_OWNER"],
        migration.blueprint.PARAMS["UNDY_HQ_MIN_GOV_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_GOV_TIMELOCK"],
        migration.blueprint.TOKENS["GREEN"],
        migration.blueprint.TOKENS["SAVINGS_GREEN"],
    )

    migration.deploy(
        "DefaultsBase",
        user_wallet_template,
        user_wallet_config_template,
        agent_wrapper,
        migration.blueprint.TOKENS["RIPE"],  # rewards asset
    )
