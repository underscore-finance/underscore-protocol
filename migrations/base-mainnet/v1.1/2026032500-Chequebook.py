from scripts.utils.migration import Migration


def migrate(migration: Migration):
    hq = migration.get_contract("UndyHq")
    migration.deploy(
        "ChequeBook",
        hq,
        migration.blueprint.PARAMS["CHEQUE_MIN_PERIOD"],
        migration.blueprint.PARAMS["CHEQUE_MAX_PERIOD"],
        migration.blueprint.PARAMS["CHEQUE_MIN_EXPENSIVE_DELAY"],
        migration.blueprint.PARAMS["CHEQUE_MAX_UNLOCK_BLOCKS"],
        migration.blueprint.PARAMS["CHEQUE_MAX_EXPIRY_BLOCKS"],
    )
