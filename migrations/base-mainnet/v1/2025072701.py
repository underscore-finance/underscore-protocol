from scripts.utils.migration import Migration


def migrate(migration: Migration):
    migration.log.h2("Update to Non-Reentrant")

    migration.deploy_bp("UserWallet")
    migration.deploy_bp("AgentWrapper")

    hq = migration.get_contract("UndyHq")
    migration.deploy(
        'Hatchery',
        hq,
        migration.blueprint.TOKENS["WETH"],
        migration.blueprint.TOKENS["ETH"],
    )
