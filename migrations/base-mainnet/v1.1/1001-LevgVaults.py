from scripts.utils.migration import Migration
from tests.constants import ZERO_ADDRESS


def migrate(migration: Migration):
    hq = migration.get_address("UndyHq")

    # execute after migration
    return

    # vaults
    vault_registry = migration.get_contract("VaultRegistry")
    levg_vault_helper = migration.get_contract("LevgVaultHelper")

    usdc_levg_vault = migration.deploy(
        "LevgVault",
        migration.blueprint.TOKENS["USDC"],  # _asset: address,
        migration.blueprint.VAULT_INFO["LEVG_USDC"]["name"],  # _tokenName: String[64],
        migration.blueprint.VAULT_INFO["LEVG_USDC"]["symbol"],  # _tokenSymbol: String[32],
        hq,  # _undyHq: address,
        migration.get_address("UndyUsd"),  # _collateralVaultToken: address,
        migration.blueprint.LEGO_IDS.UNDERSCORE,  # _collateralVaultTokenLegoId: uint256,
        migration.blueprint.LEGO_IDS.RIPE,  # _collateralVaultTokenRipeVaultId: uint256,
        migration.get_address("UndyUsd"),  # _leverageVaultToken: address,
        migration.blueprint.LEGO_IDS.UNDERSCORE,  # _leverageVaultTokenLegoId: uint256,
        migration.blueprint.LEGO_IDS.RIPE,  # _leverageVaultTokenRipeVaultId: uint256,
        migration.blueprint.TOKENS["USDC"],  # _usdc: address,
        migration.blueprint.TOKENS["GREEN"],  # _green: address,
        migration.blueprint.TOKENS["SAVINGS_GREEN"],  # _savingsGreen: address,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_GOV_TIMELOCK"],  # _minHqTimeLock: uint256,
        migration.blueprint.PARAMS["UNDY_HQ_MAX_GOV_TIMELOCK"],  # _maxHqTimeLock: uint256,
        migration.blueprint.INTEGRATION_ADDYS["GOVERNANCE"],  # _startingAgent: address,
        levg_vault_helper,  # _levgVaultHelper: address,
    )
    migration.execute(vault_registry.startAddNewAddressToRegistry, usdc_levg_vault.address, "Undy Levg USDC Vault")
    assert migration.execute(vault_registry.confirmNewAddressToRegistry,
                             usdc_levg_vault.address,
                             True,  # isLeveragedVault
                             False,  # shouldEnforceAllowlist
                             [],  # doesn't matter for leverage vault
                             0,  # maxDepositAmount (0 = unlimited)
                             100_000_000_000,  # doesn't matter for leverage vault
                             0,  # doesn't matter for leverage vault
                             ZERO_ADDRESS,  # doesn't matter for leverage vault
                             True,  # shouldAutoDeposit
                             True,  # canDeposit
                             True,  # canWithdraw
                             False,  # isVaultOpsFrozen
                             2_00,  # redemptionBuffer (2%)
                             )

    cbbtc_levg_vault = migration.deploy(
        "LevgVault",
        migration.blueprint.TOKENS["CBBTC"],  # _asset: address,
        migration.blueprint.VAULT_INFO["LEVG_CBBTC"]["name"],  # _tokenName: String[64],
        migration.blueprint.VAULT_INFO["LEVG_CBBTC"]["symbol"],  # _tokenSymbol: String[32],
        hq,  # _undyHq: address,
        migration.get_address("UndyBtc"),  # _collateralVaultToken: address,
        migration.blueprint.LEGO_IDS.UNDERSCORE,  # _collateralVaultTokenLegoId: uint256,
        migration.blueprint.LEGO_IDS.RIPE,  # _collateralVaultTokenRipeVaultId: uint256,
        migration.get_address("UndyUsd"),  # _leverageVaultToken: address,
        migration.blueprint.LEGO_IDS.UNDERSCORE,  # _leverageVaultTokenLegoId: uint256,
        migration.blueprint.LEGO_IDS.RIPE,  # _leverageVaultTokenRipeVaultId: uint256,
        migration.blueprint.TOKENS["USDC"],  # _usdc: address,
        migration.blueprint.TOKENS["GREEN"],  # _green: address,
        migration.blueprint.TOKENS["SAVINGS_GREEN"],  # _savingsGreen: address,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_GOV_TIMELOCK"],  # _minHqTimeLock: uint256,
        migration.blueprint.PARAMS["UNDY_HQ_MAX_GOV_TIMELOCK"],  # _maxHqTimeLock: uint256,
        migration.blueprint.INTEGRATION_ADDYS["GOVERNANCE"],  # _startingAgent: address,
        levg_vault_helper,  # _levgVaultHelper: address,
    )

    migration.execute(vault_registry.startAddNewAddressToRegistry, cbbtc_levg_vault.address, "Undy Levg CBBTC Vault")
    assert vault_registry.confirmNewAddressToRegistry(
        cbbtc_levg_vault.address,
        True,  # isLeveragedVault
        False,  # shouldEnforceAllowlist
        [],  # doesn't matter for leverage vault
        0,  # maxDepositAmount (0 = unlimited)
        100_000_000_000,  # doesn't matter for leverage vault
        0,  # doesn't matter for leverage vault
        ZERO_ADDRESS,  # doesn't matter for leverage vault
        True,  # shouldAutoDeposit
        True,  # canDeposit
        True,  # canWithdraw
        False,  # isVaultOpsFrozen
        2_00,  # redemptionBuffer (2%)
    ) > 0
