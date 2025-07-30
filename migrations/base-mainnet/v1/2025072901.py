from scripts.utils.migration import Migration


def migrate(migration: Migration):
    migration.log.h2("Remove Non-Reentrant")
    hq = migration.get_contract("UndyHq")

    migration.deploy(
        'LootDistributor',
        hq,
    )

    migration.deploy(
        'Billing',
        hq,
        migration.blueprint.TOKENS["WETH"],
        migration.blueprint.TOKENS["ETH"],
    )

    migration.deploy(
        'Kernel',
        hq,
    )

    migration.deploy(
        'Migrator',
        hq,
    )

    migration.deploy(
        'ChequeBook',
        hq,
        migration.blueprint.PARAMS["CHEQUE_MIN_PERIOD"],
        migration.blueprint.PARAMS["CHEQUE_MAX_PERIOD"],
        migration.blueprint.PARAMS["CHEQUE_MIN_EXPENSIVE_DELAY"],
        migration.blueprint.PARAMS["CHEQUE_MAX_UNLOCK_BLOCKS"],
        migration.blueprint.PARAMS["CHEQUE_MAX_EXPIRY_BLOCKS"],
    )

    migration.deploy(
        'HighCommand',
        hq,
        migration.blueprint.PARAMS["BOSS_MIN_MANAGER_PERIOD"],
        migration.blueprint.PARAMS["BOSS_MAX_MANAGER_PERIOD"],
        migration.blueprint.PARAMS["BOSS_MIN_ACTIVATION_LENGTH"],
        migration.blueprint.PARAMS["BOSS_MAX_ACTIVATION_LENGTH"],
        migration.blueprint.PARAMS["BOSS_MAX_START_DELAY"],
    )
