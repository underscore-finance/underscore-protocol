from scripts.utils.migration import Migration

USDC_VAULTS = [
    '0x7BfA7C4f149E7415b73bdeDfe609237e29CBF34A',
    '0xbeeF010f9cb27031ad51e3333f9aF9C6B1228183',
    '0xc1256Ae5FF1cf2719D4937adb3bbCCab2E00A2Ca',
    '0x616a4E1db48e22028f6bbf20444Cd3b8e3273738',
    '0xeE8F4eC5672F09119b96Ab6fB59C27E1b7e44b61',
    '0xBEEFE94c8aD530842bfE7d8B397938fFc1cb83b2',
    '0x23479229e52Ab6aaD312D0B03DF9F33B46753B5e',
    '0xBEEFA7B88064FeEF0cEe02AAeBBd95D30df3878F',
    '0xE74c499fA461AF1844fCa84204490877787cED56',
    '0x1D3b1Cd0a0f242d598834b3F2d126dC6bd774657',
    '0xc0c5689e6f4D256E861F65465b691aeEcC0dEb12',
    '0xB7890CEE6CF4792cdCC13489D36D9d42726ab863',
    '0x12AFDeFb2237a5963e7BAb3e2D46ad0eee70406e',
    '0x236919F11ff9eA9550A4287696C2FC9e18E6e890',
    '0x0A1a3b5f2041F33522C4efc754a7D096f880eE16',
    '0x085178078796Da17B191f9081b5E2fCCc79A7eE7',
    '0x4e65fE4DbA92790696d040ac24Aa414708F5c0AB',
    '0xb125E6687d4313864e53df431d5425969c15Eb2F',
    '0xf42f5795D9ac7e9D757dB633D693cD548Cfd9169',
    '0xEdc817A28E8B93B03976FBd4a3dDBc9f7D176c22',
    '0xb99b6df96d4d5448cc0a5b3e0ef7896df9507cf5',
]
USDC_LEGOS = [2, 3, 4, 5, 6, 7, 14]

ETH_VAULTS = [
    '0xa0E430870c4604CcfC7B38Ca7845B1FF653D0ff1',
    '0x27D8c7273fd3fcC6956a0B370cE5Fd4A7fc65c18',
    '0x5A32099837D89E3a794a44fb131CBbAD41f87a8C',
    '0x09832347586E238841F49149C84d121Bc2191C53',
    '0x6b13c060F13Af1fdB319F52315BbbF3fb1D88844',
    '0x859160DB5841E5cfB8D3f144C6b3381A85A4b410',
    '0xF3BB6b0a9bEAF9240D7F4a91341d5Df6bF37cAea',
    '0xD4a0e0b9149BCee3C920d2E00b5dE09138fd8bb7',
    '0x46e6b214b524310239732D51387075E0e70970bf',
    '0x9272D6153133175175Bc276512B2336BE3931CE9',
    '0x628ff693426583D9a7FB391E54366292F509D457',
]
ETH_LEGOS = [2, 3, 4, 5, 6, 7]

BTC_VAULTS = [
    '0x543257eF2161176D7C8cD90BA65C2d4CaEF5a796',
    '0x6770216aC60F634483Ec073cBABC4011c94307Cb',
    '0x5a47C803488FE2BB0A0EAaf346b420e4dF22F3C7',
    '0x882018411Bc4A020A879CEE183441fC9fa5D7f8B',
    '0xe72eA97aAF905c5f10040f78887cc8dE8eAec7E4',
    '0xBdb9300b7CDE636d9cD4AFF00f6F009fFBBc8EE6',
    '0xF877ACaFA28c19b96727966690b2f44d35aD5976',
]
BTC_LEGOS = [2, 4, 6, 7]


def migrate(migration: Migration):
    hq = migration.get_address("UndyHq")

    # vaults
    vault_registry = migration.get_contract('VaultRegistry')

    usdcVault = migration.deploy(
        'Autopilot',
        migration.blueprint.TOKENS["USDC"],
        migration.blueprint.VAULT_INFO["USDC"]["name"],
        migration.blueprint.VAULT_INFO["USDC"]["symbol"],
        hq,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
        migration.blueprint.INTEGRATION_ADDYS["STARTER_AGENT"],
        label="undyUSDCVault",
    )
    assert migration.execute(vault_registry.startAddNewAddressToRegistry, usdcVault, "UndyUSD Vault")
    assert migration.execute(
        vault_registry.confirmNewAddressToRegistry,
        usdcVault,
        USDC_VAULTS,
        0,  # _maxDepositAmount: uint256,
        10000,  # _minYieldWithdrawAmount: uint256 - 0.01 USDC with 6 decimals,
        20_00,  # _performanceFee: uint256,
        migration.blueprint.CONSTANTS.ZERO_ADDRESS,  # _defaultTargetVaultToken: address,
        True,  # _shouldAutoDeposit: bool,
        True,  # _canDeposit: bool,
        True,  # _canWithdraw: bool,
        False,  # _isVaultOpsFrozen: bool,
        2_00,  # _redemptionBuffer: uint256,
    ) == 1

    ethVault = migration.deploy(
        'Autopilot',
        migration.blueprint.TOKENS["WETH"],
        migration.blueprint.VAULT_INFO["WETH"]["name"],
        migration.blueprint.VAULT_INFO["WETH"]["symbol"],
        hq,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
        migration.blueprint.INTEGRATION_ADDYS["STARTER_AGENT"],
        label="undyETHVault",
    )
    assert migration.execute(vault_registry.startAddNewAddressToRegistry, ethVault, "UndyETH Vault")
    assert migration.execute(
        vault_registry.confirmNewAddressToRegistry,
        ethVault,
        ETH_VAULTS,
        0,  # _maxDepositAmount: uint256,
        25 * 10**11,  # _minYieldWithdrawAmount: uint256 - $0.01 ETH with 18 decimals,
        20_00,  # _performanceFee: uint256,
        migration.blueprint.CONSTANTS.ZERO_ADDRESS,  # _defaultTargetVaultToken: address,
        True,  # _shouldAutoDeposit: bool,
        True,  # _canDeposit: bool,
        True,  # _canWithdraw: bool,
        False,  # _isVaultOpsFrozen: bool,
        2_00,  # _redemptionBuffer: uint256,
    ) == 2

    btcVault = migration.deploy(
        'Autopilot',
        migration.blueprint.TOKENS["CBBTC"],
        migration.blueprint.VAULT_INFO["CBBTC"]["name"],
        migration.blueprint.VAULT_INFO["CBBTC"]["symbol"],
        hq,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
        migration.blueprint.INTEGRATION_ADDYS["STARTER_AGENT"],
        label="undyBTCVault",
    )
    assert migration.execute(vault_registry.startAddNewAddressToRegistry, btcVault, "UndyBTC Vault")
    assert migration.execute(
        vault_registry.confirmNewAddressToRegistry,
        btcVault,
        BTC_VAULTS,
        0,  # _maxDepositAmount: uint256,
        10,  # _minYieldWithdrawAmount: uint256 - $0.01 BTC with 8 decimals,
        20_00,  # _performanceFee: uint256,
        migration.blueprint.CONSTANTS.ZERO_ADDRESS,  # _defaultTargetVaultToken: address,
        True,  # _shouldAutoDeposit: bool,
        True,  # _canDeposit: bool,
        True,  # _canWithdraw: bool,
        False,  # _isVaultOpsFrozen: bool,
        2_00,  # _redemptionBuffer: uint256,
    ) == 3
