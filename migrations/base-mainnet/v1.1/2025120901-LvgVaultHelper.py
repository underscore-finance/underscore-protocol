from scripts.utils.migration import Migration


def migrate(migration: Migration):
    hq = migration.get_contract("UndyHq")
    levg_vault_helper = migration.deploy(
        "LevgVaultHelper",
        hq,
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
        migration.blueprint.TOKENS["USDC"],
    )
