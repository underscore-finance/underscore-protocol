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
            '0x4e65fE4DbA92790696d040ac24Aa414708F5c0AB',
            '0xb125E6687d4313864e53df431d5425969c15Eb2F',
            '0xf42f5795D9ac7e9D757dB633D693cD548Cfd9169',
            '0xEdc817A28E8B93B03976FBd4a3dDBc9f7D176c22',
            '0xb99b6df96d4d5448cc0a5b3e0ef7896df9507cf5',
            '0x1c4a802fd6b591bb71daa01d8335e43719048b24',
            '0x944766f715b51967e56afde5f0aa76ceacc9e7f9',
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
