from scripts.utils.migration import Migration


def migrate(migration: Migration):
    hq = migration.get_address("UndyHq")

    # legos
    forty_acres_lego = migration.deploy(
        '40Acres',
        hq,
        migration.blueprint.TOKENS["FORTY_ACRES_USDC"],
    )
    ripe_lego = migration.deploy(
        'RipeLego',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
        migration.blueprint.TOKENS["GREEN_USDC"],
        migration.blueprint.TOKENS["USDC"],
        10,
    )
    underyield_lego = migration.deploy(
        'UnderscoreLego',
        hq,
        migration.blueprint.TOKENS["RIPE"],
    )

    # switchboard
    switchboard_charlie = migration.deploy(
        'SwitchboardCharlie',
        hq,
        migration.account,
        migration.blueprint.PARAMS["GEN_MIN_CONFIG_TIMELOCK"],
        migration.blueprint.PARAMS["GEN_MAX_CONFIG_TIMELOCK"],
    )

    # vaults
    vault_registry = migration.deploy(
        'VaultRegistry',
        hq,
        migration.account,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
    )

    usdcVault = migration.deploy(
        'UndyUsd',
        migration.blueprint.TOKENS["USDC"],
        hq,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
        migration.blueprint.INTEGRATION_ADDYS["STARTER_AGENT"],
    )

    assert migration.execute(vault_registry.startAddNewAddressToRegistry, usdcVault, "UndyUSD Vault")
    assert migration.execute(vault_registry.confirmNewAddressToRegistry, usdcVault) == 1

    ethVault = migration.deploy(
        'UndyEth',
        migration.blueprint.TOKENS["WETH"],
        hq,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
        migration.blueprint.INTEGRATION_ADDYS["STARTER_AGENT"],
    )

    assert migration.execute(vault_registry.startAddNewAddressToRegistry, ethVault, "UndyETH Vault")
    assert migration.execute(vault_registry.confirmNewAddressToRegistry, ethVault) == 2


    btcVault = migration.deploy(
        'UndyBtc',
        migration.blueprint.TOKENS["CBBTC"],
        hq,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
        migration.blueprint.INTEGRATION_ADDYS["STARTER_AGENT"],
    )

    migration.execute(vault_registry.setRegistryTimeLockAfterSetup)
    migration.execute(vault_registry.relinquishGov)

   