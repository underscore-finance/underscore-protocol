from scripts.utils.migration import Migration


def migrate(migration: Migration):
    migration.log.h2("Wallet Backpack")
    hq = migration.get_contract("UndyHq")

    wallet_backpack = migration.deploy(
        'WalletBackpack',
        hq,
        migration.account,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
    )

    kernel = migration.deploy(
        'Kernel',
        hq,
    )

    high_command = migration.deploy(
        'HighCommand',
        hq,
        migration.blueprint.PARAMS["BOSS_MIN_MANAGER_PERIOD"],
        migration.blueprint.PARAMS["BOSS_MAX_MANAGER_PERIOD"],
        migration.blueprint.PARAMS["BOSS_MIN_ACTIVATION_LENGTH"],
        migration.blueprint.PARAMS["BOSS_MAX_ACTIVATION_LENGTH"],
        migration.blueprint.PARAMS["BOSS_MAX_START_DELAY"],
    )

    paymaster = migration.deploy(
        'Paymaster',
        hq,
        migration.blueprint.PARAMS["PAYMASTER_MIN_PAYEE_PERIOD"],
        migration.blueprint.PARAMS["PAYMASTER_MAX_PAYEE_PERIOD"],
        migration.blueprint.PARAMS["PAYMASTER_MIN_ACTIVATION_LENGTH"],
        migration.blueprint.PARAMS["PAYMASTER_MAX_ACTIVATION_LENGTH"],
        migration.blueprint.PARAMS["PAYMASTER_MAX_START_DELAY"],
    )

    cheque_book = migration.deploy(
        'ChequeBook',
        hq,
        migration.blueprint.PARAMS["CHEQUE_MIN_PERIOD"],
        migration.blueprint.PARAMS["CHEQUE_MAX_PERIOD"],
        migration.blueprint.PARAMS["CHEQUE_MIN_EXPENSIVE_DELAY"],
        migration.blueprint.PARAMS["CHEQUE_MAX_UNLOCK_BLOCKS"],
        migration.blueprint.PARAMS["CHEQUE_MAX_EXPIRY_BLOCKS"],
    )

    migrator = migration.deploy(
        'Migrator',
        hq,
    )

    sentinel = migration.deploy('Sentinel')
