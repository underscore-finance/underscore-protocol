from scripts.utils.migration import Migration
from tests.constants import ZERO_ADDRESS

def migrate(migration: Migration):
    hq = migration.get_address("UndyHq")
    usdcVaultV2 =  migration.deploy(
        'EarnVault',
        migration.blueprint.TOKENS["USDC"],
        migration.blueprint.VAULT_INFO["USDC"]['name'],
        migration.blueprint.VAULT_INFO["USDC"]['symbol'],
        hq,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
        "0x8d6DD438B9748DCA269033A01B1581EE8ef21e3b",
        label="UndyUsdV2",
    )
