from scripts.utils.migration import Migration

USDC_VAULTS = [
    '0x4e65fE4DbA92790696d040ac24Aa414708F5c0AB',
    '0xb125E6687d4313864e53df431d5425969c15Eb2F',
    '0x0A1a3b5f2041F33522C4efc754a7D096f880eE16',
    '0xf42f5795D9ac7e9D757dB633D693cD548Cfd9169',
    '0xEdc817A28E8B93B03976FBd4a3dDBc9f7D176c22',
    '0xeE8F4eC5672F09119b96Ab6fB59C27E1b7e44b61',
    '0x7BfA7C4f149E7415b73bdeDfe609237e29CBF34A',
    '0x12AFDeFb2237a5963e7BAb3e2D46ad0eee70406e',
    '0x23479229e52Ab6aaD312D0B03DF9F33B46753B5e',
    '0x616a4E1db48e22028f6bbf20444Cd3b8e3273738',
    '0xc1256Ae5FF1cf2719D4937adb3bbCCab2E00A2Ca',
    '0xc0c5689e6f4D256E861F65465b691aeEcC0dEb12',
    '0xbeeF010f9cb27031ad51e3333f9aF9C6B1228183',
]
USDC_LEGOS = [2,3,4,5,6,7]

ETH_VAULTS = [
    '0xD4a0e0b9149BCee3C920d2E00b5dE09138fd8bb7',
    '0x46e6b214b524310239732D51387075E0e70970bf',
    '0x859160DB5841E5cfB8D3f144C6b3381A85A4b410',
    '0x9272D6153133175175Bc276512B2336BE3931CE9',
    '0x628ff693426583D9a7FB391E54366292F509D457',
    '0x5496b42ad0deCebFab0db944D83260e60D54f667',
    '0x6b13c060F13Af1fdB319F52315BbbF3fb1D88844',
    '0x27D8c7273fd3fcC6956a0B370cE5Fd4A7fc65c18',
    '0xA2Cac0023a4797b4729Db94783405189a4203AFc',
    '0x5A32099837D89E3a794a44fb131CBbAD41f87a8C',
    '0xa0E430870c4604CcfC7B38Ca7845B1FF653D0ff1',
]
ETH_LEGOS = [2,3,4,5,6,7]

BTC_VAULTS = [
    '0xBdb9300b7CDE636d9cD4AFF00f6F009fFBBc8EE6',
    '0x882018411Bc4A020A879CEE183441fC9fa5D7f8B',
    '0xf877acafa28c19b96727966690b2f44d35ad5976',
    '0x5a47C803488FE2BB0A0EAaf346b420e4dF22F3C7',
    '0x543257eF2161176D7C8cD90BA65C2d4CaEF5a796',
    '0x6770216aC60F634483Ec073cBABC4011c94307Cb',
]
BTC_LEGOS = [2,4,6,7]


def migrate(migration: Migration):
    hq = migration.get_address("UndyHq")

    switchboard_charlie = migration.get_contract("SwitchboardCharlie")

    usdcVault = migration.get_address("UndyUsd")
    ethVault = migration.get_address("UndyEth")
    btcVault = migration.get_address("UndyBtc")

    priceConfig = (
        migration.blueprint.PARAMS["EARN_VAULT_MIN_SNAPSHOT_DELAY"],
        migration.blueprint.PARAMS["EARN_VAULT_MAX_NUM_SNAPSHOTS"],
        migration.blueprint.PARAMS["EARN_VAULT_MAX_UPSIDE_DEVIATION"],
        migration.blueprint.PARAMS["EARN_VAULT_STALE_TIME"],
    )

    aid = migration.execute(
        switchboard_charlie.initializeVaultConfig,
        usdcVault, # _vaultAddr: address,
        True, # _canDeposit: bool,
        True, #_canWithdraw: bool,
        1_000_000 * 10**6, # _maxDepositAmount: uint256,
        2_00, # _redemptionBuffer: uint256,
        10000, # _minYieldWithdrawAmount: uint256 - 0.01 USDC with 6 decimals,
        priceConfig, # _snapShotPriceConfig
        USDC_VAULTS, # _approvedVaultTokens: DynArray[address, 25] = [],
        USDC_LEGOS, # _approvedYieldLegos: DynArray[uint256, 25] = [],
    )
    assert migration.execute(switchboard_charlie.executePendingAction, aid)

    aid = migration.execute(
        switchboard_charlie.initializeVaultConfig,
        ethVault, # _vaultAddr: address,
        True, # _canDeposit: bool,
        True, #_canWithdraw: bool,
        250 * 10**18, # _maxDepositAmount: uint256,
        2_00, # _redemptionBuffer: uint256,
        25 * 10**11, # _minYieldWithdrawAmount: uint256 - $0.01 ETH with 18 decimals,
        priceConfig, # _snapShotPriceConfig
        ETH_VAULTS, # _approvedVaultTokens: DynArray[address, 25] = [],
        ETH_LEGOS, # _approvedYieldLegos: DynArray[uint256, 25] = [],
    )
    assert migration.execute(switchboard_charlie.executePendingAction, aid)

    aid = migration.execute(
        switchboard_charlie.initializeVaultConfig,
        btcVault, # _vaultAddr: address,
        True, # _canDeposit: bool,
        True, #_canWithdraw: bool,
        10 * 10**8, # _maxDepositAmount: uint256,
        2_00, # _redemptionBuffer: uint256,
        10, # _minYieldWithdrawAmount: uint256 - $0.01 BTC with 8 decimals,
        priceConfig, # _snapShotPriceConfig
        BTC_VAULTS, # _approvedVaultTokens: DynArray[address, 25] = [],
        BTC_LEGOS, # _approvedYieldLegos: DynArray[uint256, 25] = [],
    )
    assert migration.execute(switchboard_charlie.executePendingAction, aid)

    migration.execute(switchboard_charlie.setActionTimeLockAfterSetup)
    migration.execute(switchboard_charlie.relinquishGov)


