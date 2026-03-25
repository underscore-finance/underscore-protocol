from scripts.utils.migration import Migration


def migrate(migration: Migration):
    migration.log.h2("Payments - Deploy Contracts")
    hq = migration.get_contract("UndyHq")

    # Agent contracts
    migration.deploy("AgentWrapper", hq, 1)
    migration.deploy(
        "AgentSenderGeneric",
        hq,
        migration.blueprint.INTEGRATION_ADDYS["AGENT_OWNER"],
        migration.blueprint.PARAMS["UNDY_HQ_MIN_GOV_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_GOV_TIMELOCK"],
    )
    migration.deploy("UserWalletSignatureHelper")

    # WalletBackpack contracts
    migration.deploy(
        "Kernel",
        hq,
    )
    migration.deploy(
        "ChequeBook",
        hq,
        migration.blueprint.PARAMS["CHEQUE_MIN_PERIOD"],
        migration.blueprint.PARAMS["CHEQUE_MAX_PERIOD"],
        migration.blueprint.PARAMS["CHEQUE_MIN_EXPENSIVE_DELAY"],
        migration.blueprint.PARAMS["CHEQUE_MAX_UNLOCK_BLOCKS"],
        migration.blueprint.PARAMS["CHEQUE_MAX_EXPIRY_BLOCKS"],
    )
    migration.deploy(
        "Migrator",
        hq,
    )
    migration.deploy(
        "Paymaster",
        hq,
        migration.blueprint.PARAMS["PAYMASTER_MIN_PAYEE_PERIOD"],
        migration.blueprint.PARAMS["PAYMASTER_MAX_PAYEE_PERIOD"],
        migration.blueprint.PARAMS["PAYMASTER_MIN_ACTIVATION_LENGTH"],
        migration.blueprint.PARAMS["PAYMASTER_MAX_ACTIVATION_LENGTH"],
        migration.blueprint.PARAMS["PAYMASTER_MAX_START_DELAY"],
    )
    migration.deploy("Sentinel")
