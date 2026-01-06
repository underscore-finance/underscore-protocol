from scripts.utils.migration import Migration


def migrate(migration: Migration):
    hq = migration.get_address("UndyHq")

    # vaults
    levg_vault_helper = migration.deploy(
        "LevgVaultHelper", hq, migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"], migration.blueprint.TOKENS["USDC"])
    levg_vault_tools = migration.deploy(
        "LevgVaultTools", hq, migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"], migration.blueprint.TOKENS["USDC"])

    levg_vault_agent = migration.deploy(
        "LevgVaultAgent",
        hq,
        migration.blueprint.INTEGRATION_ADDYS["VAULT_AGENT_OWNER"],
        migration.blueprint.PARAMS["UNDY_HQ_MIN_GOV_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_GOV_TIMELOCK"],
        migration.blueprint.TOKENS["GREEN"],
        migration.blueprint.TOKENS["SAVINGS_GREEN"],
    )

    usdc_levg_vault = migration.deploy(
        "LevgVault",
        migration.blueprint.TOKENS["USDC"],  # _asset: address,
        migration.blueprint.VAULT_INFO["AMP_USDC"]["name"],  # _tokenName: String[64],
        migration.blueprint.VAULT_INFO["AMP_USDC"]["symbol"],  # _tokenSymbol: String[32],
        hq,  # _undyHq: address,
        migration.get_address("UndyUsd"),  # _collateralVaultToken: address,
        migration.blueprint.LEGO_IDS.UNDERSCORE,  # _collateralVaultTokenLegoId: uint256,
        migration.blueprint.PARAMS["RIPE_COLLATERAL_VAULT_ID"],  # _collateralVaultTokenRipeVaultId: uint256,
        migration.get_address("UndyUsd"),  # _leverageVaultToken: address,
        migration.blueprint.LEGO_IDS.UNDERSCORE,  # _leverageVaultTokenLegoId: uint256,
        migration.blueprint.PARAMS["RIPE_COLLATERAL_VAULT_ID"],  # _leverageVaultTokenRipeVaultId: uint256,
        migration.blueprint.TOKENS["USDC"],  # _usdc: address,
        migration.blueprint.TOKENS["GREEN"],  # _green: address,
        migration.blueprint.TOKENS["SAVINGS_GREEN"],  # _savingsGreen: address,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_GOV_TIMELOCK"],  # _minHqTimeLock: uint256,
        migration.blueprint.PARAMS["UNDY_HQ_MAX_GOV_TIMELOCK"],  # _maxHqTimeLock: uint256,
        levg_vault_agent,  # _startingAgent: address,
        levg_vault_helper,  # _levgVaultHelper: address,
    )

    cbbtc_levg_vault = migration.deploy(
        "LevgVault",
        migration.blueprint.TOKENS["CBBTC"],  # _asset: address,
        migration.blueprint.VAULT_INFO["AMP_CBBTC"]["name"],  # _tokenName: String[64],
        migration.blueprint.VAULT_INFO["AMP_CBBTC"]["symbol"],  # _tokenSymbol: String[32],
        hq,  # _undyHq: address,
        migration.get_address("UndyBtc"),  # _collateralVaultToken: address,
        migration.blueprint.LEGO_IDS.UNDERSCORE,  # _collateralVaultTokenLegoId: uint256,
        migration.blueprint.PARAMS["RIPE_COLLATERAL_VAULT_ID"],  # _collateralVaultTokenRipeVaultId: uint256,
        migration.get_address("UndyUsd"),  # _leverageVaultToken: address,
        migration.blueprint.LEGO_IDS.UNDERSCORE,  # _leverageVaultTokenLegoId: uint256,
        migration.blueprint.PARAMS["RIPE_COLLATERAL_VAULT_ID"],  # _leverageVaultTokenRipeVaultId: uint256,
        migration.blueprint.TOKENS["USDC"],  # _usdc: address,
        migration.blueprint.TOKENS["GREEN"],  # _green: address,
        migration.blueprint.TOKENS["SAVINGS_GREEN"],  # _savingsGreen: address,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_GOV_TIMELOCK"],  # _minHqTimeLock: uint256,
        migration.blueprint.PARAMS["UNDY_HQ_MAX_GOV_TIMELOCK"],  # _maxHqTimeLock: uint256,
        levg_vault_agent,  # _startingAgent: address,
        levg_vault_helper,  # _levgVaultHelper: address,
    )
