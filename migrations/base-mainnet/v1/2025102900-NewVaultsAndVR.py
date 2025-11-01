from scripts.utils.migration import Migration
from tests.constants import ZERO_ADDRESS

VAULTS = [
    {
        'token': "USDC",
        'label': "UndyUsd",
        'minYieldWithdrawAmount': 10000,
        'vaults': [
            '0x7BfA7C4f149E7415b73bdeDfe609237e29CBF34A',
            '0xbeeF010f9cb27031ad51e3333f9aF9C6B1228183',
            '0xc1256Ae5FF1cf2719D4937adb3bbCCab2E00A2Ca',
            '0x616a4E1db48e22028f6bbf20444Cd3b8e3273738',
            '0xeE8F4eC5672F09119b96Ab6fB59C27E1b7e44b61',
            '0xBEEFE94c8aD530842bfE7d8B397938fFc1cb83b2',
            '0x23479229e52Ab6aaD312D0B03DF9F33B46753B5e',
            '0xBEEFA7B88064FeEF0cEe02AAeBBd95D30df3878F',
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
            '0x1c4a802fd6b591bb71daa01d8335e43719048b24',
            '0x944766f715b51967e56afde5f0aa76ceacc9e7f9'
        ],
    },
    {
        'token': "WETH",
        'label': "UndyEth",
        'minYieldWithdrawAmount': 25 * 10**11,
        'vaults':  [
            '0xa0E430870c4604CcfC7B38Ca7845B1FF653D0ff1',
            '0x27D8c7273fd3fcC6956a0B370cE5Fd4A7fc65c18',
            '0x5A32099837D89E3a794a44fb131CBbAD41f87a8C',
            '0x09832347586E238841F49149C84d121Bc2191C53',
            '0x6b13c060F13Af1fdB319F52315BbbF3fb1D88844',
            '0xA2Cac0023a4797b4729Db94783405189a4203AFc',
            '0x859160DB5841E5cfB8D3f144C6b3381A85A4b410',
            '0xF3BB6b0a9bEAF9240D7F4a91341d5Df6bF37cAea',
            '0xD4a0e0b9149BCee3C920d2E00b5dE09138fd8bb7',
            '0x46e6b214b524310239732D51387075E0e70970bf',
            '0x9272D6153133175175Bc276512B2336BE3931CE9',
            '0x628ff693426583D9a7FB391E54366292F509D457',
        ],
    },
    {
        'token': "CBBTC",
        'label': "UndyBtc",
        'minYieldWithdrawAmount': 10,
        'vaults':  [
            '0x543257eF2161176D7C8cD90BA65C2d4CaEF5a796',
            '0x6770216aC60F634483Ec073cBABC4011c94307Cb',
            '0x5a47C803488FE2BB0A0EAaf346b420e4dF22F3C7',
            '0x882018411Bc4A020A879CEE183441fC9fa5D7f8B',
            '0xe72eA97aAF905c5f10040f78887cc8dE8eAec7E4',
            '0xBdb9300b7CDE636d9cD4AFF00f6F009fFBBc8EE6',
            '0xF877ACaFA28c19b96727966690b2f44d35aD5976',
        ],
    },
    {
        'token': "AERO",
        'label': "UndyAero",
        'minYieldWithdrawAmount': 10**16,
        'vaults': [
            '0x784efeB622244d2348d4F2522f8860B96fbEcE89',
            '0x73902f619CEB9B31FD8EFecf435CbDf89E369Ba6',
        ],

    },
    {
        'token': "EURC",
        'label': "UndyEurc",
        'minYieldWithdrawAmount': 10000,
        'vaults': [
            '0xf24608E0CCb972b0b0f4A6446a0BBf58c701a026',
            '0xBeEF086b8807Dc5E5A1740C5E3a7C4c366eA6ab5',
            '0x1c155be6bC51F2c37d472d4C2Eba7a637806e122',
            '0x9ECD9fbbdA32b81dee51AdAed28c5C5039c87117',
            '0x90DA57E0A6C0d166Bf15764E03b83745Dc90025B',
            '0x1943FA26360f038230442525Cf1B9125b5DCB401',
            '0xb682c840B5F4FC58B20769E691A6fa1305A501a2',
        ],
    },
    {
        'token': "USDS",
        'label': "UndyUsds",
        'minYieldWithdrawAmount': 10**16,
        'vaults':  [
            '0x2c776041CCFe903071AF44aa147368a9c8EEA518',
            '0xb6419c6c2e60c4025d6d06ee4f913ce89425a357',
            '0x556d518FDFDCC4027A3A1388699c5E11AC201D8b',
            '0x5875eEE11Cf8398102FdAd704C9E96607675467a',
        ],
    },
    {
        'token': "CBETH",
        'label': "UndyCbeth",
        'minYieldWithdrawAmount': 25 * 10**11,
        'vaults': [
            '0xcf3D55c10DB69f28fD1A75Bd73f3D8A2d9c595ad',
            '0x3bf93770f2d4a794c3d9EBEfBAeBAE2a8f09A5E5',
            '0x358f25F82644eaBb441d0df4AF8746614fb9ea49',
        ],
    },
    {
        'token': "GHO",
        'label': "UndyGho",
        'minYieldWithdrawAmount': 10**16,
        'vaults': [
            '0x067ae75628177FD257c2B1e500993e1a0baBcBd1',
            '0x8DdbfFA3CFda2355a23d6B11105AC624BDbE3631',
        ],
    },
]

DEFAULT_CONFIG = {
    "maxDepositAmount": 0,
    "performanceFee": 20_00,
    "defaultTargetVaultToken": ZERO_ADDRESS,
    "shouldAutoDeposit": True,
    "canDeposit": True,
    "canWithdraw": True,
    "isVaultOpsFrozen": False,
    "redemptionBuffer": 2_00,
}


def migrate(migration: Migration):
    hq = migration.get_address("UndyHq")

    # vaults
    vault_registry = migration.deploy(
        'VaultRegistry',
        hq,
        migration.account,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
    )

    for vault in VAULTS:
        new_vault = migration.deploy(
            'EarnVault',
            migration.blueprint.TOKENS[vault['token']],
            migration.blueprint.VAULT_INFO[vault['token']]['name'],
            migration.blueprint.VAULT_INFO[vault['token']]['symbol'],
            hq,
            migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
            migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
            migration.blueprint.INTEGRATION_ADDYS["STARTER_AGENT"],
            label=vault['label'],
        )
        assert migration.execute(vault_registry.startAddNewAddressToRegistry, new_vault, f"{vault['label']} Vault")
        assert migration.execute(
            vault_registry.confirmNewAddressToRegistry,
            new_vault,
            vault['vaults'],
            DEFAULT_CONFIG['maxDepositAmount'],
            vault['minYieldWithdrawAmount'],
            DEFAULT_CONFIG['performanceFee'],
            DEFAULT_CONFIG['defaultTargetVaultToken'],
            DEFAULT_CONFIG['shouldAutoDeposit'],
            DEFAULT_CONFIG['canDeposit'],
            DEFAULT_CONFIG['canWithdraw'],
            DEFAULT_CONFIG['isVaultOpsFrozen'],
            DEFAULT_CONFIG['redemptionBuffer'],
        ) > 0

    migration.execute(vault_registry.setRegistryTimeLockAfterSetup)
    migration.execute(vault_registry.relinquishGov)
