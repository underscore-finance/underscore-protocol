from scripts.utils.migration import Migration


def migrate(migration: Migration):
    # PR #67 changes WalletBackpack.vy (adds actionDataProvider storage +
    # pending/confirm/cancel flow) and the constructors of every backpack item
    # (instant-action protocol flags). The new Hatchery reads
    # WalletBackpack.actionDataProvider(), so a fresh WalletBackpack must be
    # deployed, initialized with all 7 items (see 2026060699-FinishSetup), and
    # rotated into UndyHq reg id 8 by governance.
    migration.log.h2("Wallet Backpack + Items")
    hq = migration.get_contract("UndyHq")

    # New WalletBackpack registry (deployer holds temp gov for item setup)
    migration.deploy(
        "WalletBackpack",
        hq,
        migration.account,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
    )

    migration.deploy("Kernel", hq)

    migration.deploy("Sentinel")

    # Instant-action V1: cutover protocol flags are all true except Migrator.
    migration.deploy(
        "HighCommand",
        hq,
        migration.blueprint.PARAMS["BOSS_MIN_MANAGER_PERIOD"],
        migration.blueprint.PARAMS["BOSS_MAX_MANAGER_PERIOD"],
        migration.blueprint.PARAMS["BOSS_MIN_ACTIVATION_LENGTH"],
        migration.blueprint.PARAMS["BOSS_MAX_ACTIVATION_LENGTH"],
        migration.blueprint.PARAMS["BOSS_MAX_START_DELAY"],
        True,  # _canInstantAddManager
    )

    migration.deploy(
        "Paymaster",
        hq,
        migration.blueprint.PARAMS["PAYMASTER_MIN_PAYEE_PERIOD"],
        migration.blueprint.PARAMS["PAYMASTER_MAX_PAYEE_PERIOD"],
        migration.blueprint.PARAMS["PAYMASTER_MIN_ACTIVATION_LENGTH"],
        migration.blueprint.PARAMS["PAYMASTER_MAX_ACTIVATION_LENGTH"],
        migration.blueprint.PARAMS["PAYMASTER_MAX_START_DELAY"],
        True,  # _canInstantAddPayee
        True,  # _canInstantSetGlobalPayeeSettings
    )

    migration.deploy(
        "ChequeBook",
        hq,
        migration.blueprint.PARAMS["CHEQUE_MIN_PERIOD"],
        migration.blueprint.PARAMS["CHEQUE_MAX_PERIOD"],
        migration.blueprint.PARAMS["CHEQUE_MIN_EXPENSIVE_DELAY"],
        migration.blueprint.PARAMS["CHEQUE_MAX_UNLOCK_BLOCKS"],
        migration.blueprint.PARAMS["CHEQUE_MAX_EXPIRY_BLOCKS"],
        True,  # _canInstantSetChequeSettings
    )

    migration.deploy(
        "Migrator",
        hq,
        False,  # _instantMigrationEnabled (stays false at cutover)
    )
