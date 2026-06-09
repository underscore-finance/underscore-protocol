from scripts.utils.migration import Migration


def migrate(migration: Migration):
    # Core contracts with directly-changed runtime bytecode in PR #67.
    # Billing is compatibility-relevant: it now calls UserWalletConfig.deregisterAsset
    # with the new (no-return) shape, so it must cut over with the new wallet config.
    migration.log.h2("Core Contracts")
    hq = migration.get_contract("UndyHq")

    migration.deploy(
        "Appraiser",
        hq,
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
    )

    migration.deploy("Billing", hq)

    migration.deploy(
        "RipeLego",
        hq,
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
        migration.blueprint.TOKENS["USDC"],
    )
