from scripts.utils.migration import Migration

NEW_USDC_VAULTS = [
    '0x1c4a802fd6b591bb71daa01d8335e43719048b24',
    '0x944766f715b51967e56afde5f0aa76ceacc9e7f9'
]
REMOVE_USDC_VAULTS = [
    '0xE74c499fA461AF1844fCa84204490877787cED56',
    '0x1D3b1Cd0a0f242d598834b3F2d126dC6bd774657'
]

USDS_VAULTS = [
    '0x2c776041CCFe903071AF44aa147368a9c8EEA518',
    '0xb6419c6c2e60c4025d6d06ee4f913ce89425a357',
    '0x556d518FDFDCC4027A3A1388699c5E11AC201D8b',
    '0x5875eEE11Cf8398102FdAd704C9E96607675467a',
]

CBETH_VAULTS = [
    '0xcf3D55c10DB69f28fD1A75Bd73f3D8A2d9c595ad',
    '0x3bf93770f2d4a794c3d9EBEfBAeBAE2a8f09A5E5',
    '0x358f25F82644eaBb441d0df4AF8746614fb9ea49',
]

GHO_VAULTS = [
    '0x067ae75628177FD257c2B1e500993e1a0baBcBd1',
    '0x8DdbfFA3CFda2355a23d6B11105AC624BDbE3631',
]


def migrate(migration: Migration):
    hq = migration.get_address('UndyHq')
    lego_book = migration.get_contract('LegoBook')
    vault_registry = migration.get_contract('VaultRegistry')
    switchboard_charlie = migration.get_contract('SwitchboardCharlie')

    undy_usd_vault = migration.get_address('UndyUsd')
    for vault in NEW_USDC_VAULTS:
        aid = migration.execute(switchboard_charlie.setApprovedVaultToken, undy_usd_vault, vault, True)
        assert migration.execute(switchboard_charlie.executePendingAction, aid)

    for vault in REMOVE_USDC_VAULTS:
        aid = migration.execute(switchboard_charlie.setApprovedVaultToken, undy_usd_vault, vault, False)
        assert migration.execute(switchboard_charlie.executePendingAction, aid)

    # deploy new ap-vaults

    # USDS
    usds_vault = migration.deploy(
        'EarnVault',
        migration.blueprint.TOKENS["USDS"],
        migration.blueprint.VAULT_INFO["USDS"]["name"],
        migration.blueprint.VAULT_INFO["USDS"]["symbol"],
        hq,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
        migration.blueprint.INTEGRATION_ADDYS["STARTER_AGENT"],
        label="UndyUsds",
    )
    assert migration.execute(vault_registry.startAddNewAddressToRegistry, usds_vault, "UndyUSDS Vault")
    assert migration.execute(
        vault_registry.confirmNewAddressToRegistry,
        usds_vault,
        USDS_VAULTS,
        0,  # _maxDepositAmount: uint256,
        10**16,  # _minYieldWithdrawAmount: uint256 - 0.01 USDS with 18 decimals,
        20_00,  # _performanceFee: uint256,
        migration.blueprint.CONSTANTS.ZERO_ADDRESS,  # _defaultTargetVaultToken: address,
        True,  # _shouldAutoDeposit: bool,
        True,  # _canDeposit: bool,
        True,  # _canWithdraw: bool,
        False,  # _isVaultOpsFrozen: bool,
        2_00,  # _redemptionBuffer: uint256,
    ) > 0

    # CBETH
    cbeth_vault = migration.deploy(
        'EarnVault',
        migration.blueprint.TOKENS["CBETH"],
        migration.blueprint.VAULT_INFO["CBETH"]["name"],
        migration.blueprint.VAULT_INFO["CBETH"]["symbol"],
        hq,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
        migration.blueprint.INTEGRATION_ADDYS["STARTER_AGENT"],
        label="UndyCbeth",
    )
    assert migration.execute(vault_registry.startAddNewAddressToRegistry, cbeth_vault, "UndyCBETH Vault")
    assert migration.execute(
        vault_registry.confirmNewAddressToRegistry,
        cbeth_vault,
        CBETH_VAULTS,
        0,  # _maxDepositAmount: uint256,
        25 * 10**11,  # _minYieldWithdrawAmount: uint256 - $0.01 cbETH with 18 decimals,
        20_00,  # _performanceFee: uint256,
        migration.blueprint.CONSTANTS.ZERO_ADDRESS,  # _defaultTargetVaultToken: address,
        True,  # _shouldAutoDeposit: bool,
        True,  # _canDeposit: bool,
        True,  # _canWithdraw: bool,
        False,  # _isVaultOpsFrozen: bool,
        2_00,  # _redemptionBuffer: uint256,
    ) > 0

    # GHO
    gho_vault = migration.deploy(
        'EarnVault',
        migration.blueprint.TOKENS["GHO"],
        migration.blueprint.VAULT_INFO["GHO"]["name"],
        migration.blueprint.VAULT_INFO["GHO"]["symbol"],
        hq,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
        migration.blueprint.INTEGRATION_ADDYS["STARTER_AGENT"],
        label="UndyGho",
    )
    assert migration.execute(vault_registry.startAddNewAddressToRegistry, gho_vault, "UndyGHO Vault")
    assert migration.execute(
        vault_registry.confirmNewAddressToRegistry,
        gho_vault,
        GHO_VAULTS,
        0,  # _maxDepositAmount: uint256,
        10**16,  # _minYieldWithdrawAmount: uint256 - $0.01 GHO with 18 decimals,
        20_00,  # _performanceFee: uint256,
        migration.blueprint.CONSTANTS.ZERO_ADDRESS,  # _defaultTargetVaultToken: address,
        True,  # _shouldAutoDeposit: bool,
        True,  # _canDeposit: bool,
        True,  # _canWithdraw: bool,
        False,  # _isVaultOpsFrozen: bool,
        2_00,  # _redemptionBuffer: uint256,
    ) > 0

    # finish setup

    migration.execute(lego_book.setRegistryTimeLockAfterSetup)
    migration.execute(lego_book.relinquishGov)

    migration.execute(vault_registry.setRegistryTimeLockAfterSetup)
    migration.execute(vault_registry.relinquishGov)

    migration.execute(switchboard_charlie.setActionTimeLockAfterSetup)
    migration.execute(switchboard_charlie.relinquishGov)
