import boa

from scripts.utils.migration import Migration
from scripts.utils.registry_preconditions import register_address, require_registry_prefix


def _execute_true(migration: Migration, transaction, *args, action: str):
    result = migration.execute(transaction, *args, no_retry=True)
    if result is not True:
        raise RuntimeError(f"{action}: got {result!r}")


def _require_appraiser(migration: Migration, hq):
    names = (
        "Ledger",
        "MissionControl",
        "LegoBook",
        "Switchboard",
        "Hatchery",
        "LootDistributor",
        "Appraiser",
    )
    try:
        expected_entries = tuple(
            (name, migration.get_address(name)) for name in names
        )
    except (KeyError, TypeError) as exc:
        raise RuntimeError(
            "Robinhood core prefix is missing from the prior manifest; "
            "refusing to deploy WalletBackpack"
        ) from exc

    require_registry_prefix(
        hq,
        expected_entries,
        "before Robinhood WalletBackpack deployment",
    )
    for name, address in expected_entries:
        if not boa.env.get_code(address):
            raise RuntimeError(
                f"{name} has no code; refusing to deploy WalletBackpack"
            )


def migrate(migration: Migration):
    migration.log.h2("Wallet Backpack")
    hq = migration.get_contract("UndyHq")
    _require_appraiser(migration, hq)
    migration.discard_transaction_replay()

    # UndyHq governance can configure every LocalGov child during setup. A
    # distinct temporary governor is unnecessary, and LocalGov deliberately
    # rejects setting it to the same address as UndyHq governance.
    wallet_backpack = migration.deploy(
        "WalletBackpack",
        hq,
        migration.blueprint.CONSTANTS.ZERO_ADDRESS,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
        no_retry=True,
    )

    register_address(
        migration,
        hq,
        wallet_backpack,
        "Wallet Backpack",
        8,
    )

    kernel = migration.deploy("Kernel", hq, no_retry=True)
    sentinel = migration.deploy("Sentinel", no_retry=True)

    # Match the audited Base cutover defaults: the user-facing instant-action
    # capabilities are enabled, while wallet migration remains timelocked.
    high_command = migration.deploy(
        "HighCommand",
        hq,
        migration.blueprint.PARAMS["BOSS_MIN_MANAGER_PERIOD"],
        migration.blueprint.PARAMS["BOSS_MAX_MANAGER_PERIOD"],
        migration.blueprint.PARAMS["BOSS_MIN_ACTIVATION_LENGTH"],
        migration.blueprint.PARAMS["BOSS_MAX_ACTIVATION_LENGTH"],
        migration.blueprint.PARAMS["BOSS_MAX_START_DELAY"],
        True,
        no_retry=True,
    )

    paymaster = migration.deploy(
        "Paymaster",
        hq,
        migration.blueprint.PARAMS["PAYMASTER_MIN_PAYEE_PERIOD"],
        migration.blueprint.PARAMS["PAYMASTER_MAX_PAYEE_PERIOD"],
        migration.blueprint.PARAMS["PAYMASTER_MIN_ACTIVATION_LENGTH"],
        migration.blueprint.PARAMS["PAYMASTER_MAX_ACTIVATION_LENGTH"],
        migration.blueprint.PARAMS["PAYMASTER_MAX_START_DELAY"],
        True,
        True,
        no_retry=True,
    )

    cheque_book = migration.deploy(
        "ChequeBook",
        hq,
        migration.blueprint.PARAMS["CHEQUE_MIN_PERIOD"],
        migration.blueprint.PARAMS["CHEQUE_MAX_PERIOD"],
        migration.blueprint.PARAMS["CHEQUE_MIN_EXPENSIVE_DELAY"],
        migration.blueprint.PARAMS["CHEQUE_MAX_UNLOCK_BLOCKS"],
        migration.blueprint.PARAMS["CHEQUE_MAX_EXPIRY_BLOCKS"],
        True,
        no_retry=True,
    )

    migrator = migration.deploy(
        "Migrator",
        hq,
        False,
        no_retry=True,
    )
    action_data_provider = migration.deploy("ActionDataProvider", no_retry=True)

    _execute_true(
        migration,
        wallet_backpack.addPendingKernel,
        kernel,
        action="failed to stage Kernel",
    )
    _execute_true(
        migration,
        wallet_backpack.confirmPendingKernel,
        action="failed to confirm Kernel",
    )

    _execute_true(
        migration,
        wallet_backpack.addPendingSentinel,
        sentinel,
        action="failed to stage Sentinel",
    )
    _execute_true(
        migration,
        wallet_backpack.confirmPendingSentinel,
        action="failed to confirm Sentinel",
    )

    _execute_true(
        migration,
        wallet_backpack.addPendingHighCommand,
        high_command,
        action="failed to stage HighCommand",
    )
    _execute_true(
        migration,
        wallet_backpack.confirmPendingHighCommand,
        action="failed to confirm HighCommand",
    )

    _execute_true(
        migration,
        wallet_backpack.addPendingPaymaster,
        paymaster,
        action="failed to stage Paymaster",
    )
    _execute_true(
        migration,
        wallet_backpack.confirmPendingPaymaster,
        action="failed to confirm Paymaster",
    )

    _execute_true(
        migration,
        wallet_backpack.addPendingChequeBook,
        cheque_book,
        action="failed to stage ChequeBook",
    )
    _execute_true(
        migration,
        wallet_backpack.confirmPendingChequeBook,
        action="failed to confirm ChequeBook",
    )

    _execute_true(
        migration,
        wallet_backpack.addPendingMigrator,
        migrator,
        action="failed to stage Migrator",
    )
    _execute_true(
        migration,
        wallet_backpack.confirmPendingMigrator,
        action="failed to confirm Migrator",
    )

    # Hatchery requires this seventh item and forwards it to every wallet
    # config. Omitting it makes createUserWallet fail closed as "invalid setup".
    _execute_true(
        migration,
        wallet_backpack.addPendingActionDataProvider,
        action_data_provider,
        action="failed to stage ActionDataProvider",
    )
    _execute_true(
        migration,
        wallet_backpack.confirmPendingActionDataProvider,
        action="failed to confirm ActionDataProvider",
    )
