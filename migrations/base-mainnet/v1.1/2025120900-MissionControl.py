from scripts.utils.migration import Migration


def migrate(migration: Migration):
    hq = migration.get_contract("UndyHq")

    defaults_base = migration.deploy(
        "DefaultsBase",
    )
    migration.deploy(
        'MissionControl',
        hq,
        defaults_base,
    )

    migration.deploy(
        'LootDistributor',
        hq,
        migration.blueprint.TOKENS["RIPE"],
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
    )

    migration.deploy(
        'SwitchboardAlpha',
        hq,
        migration.blueprint.CONSTANTS.ZERO_ADDRESS,
        migration.blueprint.PARAMS["GEN_MIN_CONFIG_TIMELOCK"],
        migration.blueprint.PARAMS["GEN_MAX_CONFIG_TIMELOCK"],
    )

    migration.deploy(
        'EarnVault',
        migration.blueprint.TOKENS["VIRTUAL"],
        migration.blueprint.VAULT_INFO["VIRTUAL"]['name'],
        migration.blueprint.VAULT_INFO["VIRTUAL"]['symbol'],
        hq,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
        migration.get_address("EarnVaultAgent"),
        label="UndyVirtual",
    )
    migration.deploy(
        'ExtraFi',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["EXTRAFI_POOL"],
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
        [
            1,  # WETH
            25,  # USDC
            76,  # CBBTC
            3,  # AERO
            44  # VIRTUAL
        ],
    )
