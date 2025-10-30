from scripts.utils.migration import Migration

AERO_VAULTS = [
    '0x784efeB622244d2348d4F2522f8860B96fbEcE89',
    '0x73902f619CEB9B31FD8EFecf435CbDf89E369Ba6',
]

EURC_VAULTS = [
    '0xf24608E0CCb972b0b0f4A6446a0BBf58c701a026',
    '0xBeEF086b8807Dc5E5A1740C5E3a7C4c366eA6ab5',
    '0x1c155be6bC51F2c37d472d4C2Eba7a637806e122',
    '0x9ECD9fbbdA32b81dee51AdAed28c5C5039c87117',
    '0x90DA57E0A6C0d166Bf15764E03b83745Dc90025B',
    '0x1943FA26360f038230442525Cf1B9125b5DCB401',
    '0xb682c840B5F4FC58B20769E691A6fa1305A501a2',
]


def migrate(migration: Migration):
    hq = migration.get_address("UndyHq")

    # vaults
    vault_registry = migration.get_contract('VaultRegistry')

    aeroVault = migration.deploy(
        'EarnVault',
        migration.blueprint.TOKENS["AERO"],
        migration.blueprint.VAULT_INFO["AERO"]["name"],
        migration.blueprint.VAULT_INFO["AERO"]["symbol"],
        hq,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
        migration.blueprint.INTEGRATION_ADDYS["STARTER_AGENT"],
        label="UndyAero",
    )
    assert migration.execute(vault_registry.startAddNewAddressToRegistry, aeroVault, "UndyAERO Vault")
    assert migration.execute(
        vault_registry.confirmNewAddressToRegistry,
        aeroVault,
        AERO_VAULTS,
        0,  # _maxDepositAmount: uint256,
        10000000000000000,  # _minYieldWithdrawAmount: uint256 - 0.01 AERO with 18 decimals,
        20_00,  # _performanceFee: uint256,
        migration.blueprint.CONSTANTS.ZERO_ADDRESS,  # _defaultTargetVaultToken: address,
        True,  # _shouldAutoDeposit: bool,
        True,  # _canDeposit: bool,
        True,  # _canWithdraw: bool,
        False,  # _isVaultOpsFrozen: bool,
        2_00,  # _redemptionBuffer: uint256,
    ) > 0

    eurcVault = migration.deploy(
        'EarnVault',
        migration.blueprint.TOKENS["EURC"],
        migration.blueprint.VAULT_INFO["EURC"]["name"],
        migration.blueprint.VAULT_INFO["EURC"]["symbol"],
        hq,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
        migration.blueprint.INTEGRATION_ADDYS["STARTER_AGENT"],
        label="UndyEurc",
    )
    assert migration.execute(vault_registry.startAddNewAddressToRegistry, eurcVault, "UndyEURC Vault")
    assert migration.execute(
        vault_registry.confirmNewAddressToRegistry,
        eurcVault,
        EURC_VAULTS,
        0,  # _maxDepositAmount: uint256,
        10000,  # _minYieldWithdrawAmount: uint256 - $0.016 EURC with 6 decimals,
        20_00,  # _performanceFee: uint256,
        migration.blueprint.CONSTANTS.ZERO_ADDRESS,  # _defaultTargetVaultToken: address,
        True,  # _shouldAutoDeposit: bool,
        True,  # _canDeposit: bool,
        True,  # _canWithdraw: bool,
        False,  # _isVaultOpsFrozen: bool,
        2_00,  # _redemptionBuffer: uint256,
    ) > 0
