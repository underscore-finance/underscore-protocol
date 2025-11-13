from scripts.utils.migration import Migration


def migrate(migration: Migration):
    migration.log.h2("Core")

    user_wallet_template = migration.deploy_bp("UserWallet")
    user_wallet_config_template = migration.deploy_bp("UserWalletConfig")
    agent_template = migration.deploy_bp("AgentWrapper")

    migration.deploy(
        "DefaultsBase",
        user_wallet_template,
        user_wallet_config_template,
        agent_template,
        migration.blueprint.CONSTANTS.ZERO_ADDRESS,  # starting agent
        migration.blueprint.TOKENS["RIPE"],  # rewards asset
    )

    migration.deploy(
        'UndyHq',
        migration.account,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_GOV_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_GOV_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
    )
