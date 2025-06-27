
PARAMS = {
    "base": {
        # undy hq - gov changes (blocks)
        "UNDY_HQ_MIN_GOV_TIMELOCK": 43_200,  # 1 day on Base
        "UNDY_HQ_MAX_GOV_TIMELOCK": 302_400,  # 7 days on Base
        # undy hq - registry changes (blocks)
        "UNDY_HQ_MIN_REG_TIMELOCK": 21_600,  # 12 hours on Base
        "UNDY_HQ_MAX_REG_TIMELOCK": 302_400,  # 7 days on Base
        # gen config changes (blocks)
        "GEN_MIN_CONFIG_TIMELOCK": 10_800,  # 6 hours on Base
        "GEN_MAX_CONFIG_TIMELOCK": 302_400,  # 7 days on Base
    },
    "local": {
        # undy hq - gov changes (blocks)
        "UNDY_HQ_MIN_GOV_TIMELOCK": 43_200,
        "UNDY_HQ_MAX_GOV_TIMELOCK": 302_400,
        # undy hq - registry changes (blocks)
        "UNDY_HQ_MIN_REG_TIMELOCK": 21_600,
        "UNDY_HQ_MAX_REG_TIMELOCK": 302_400,
        # gen config changes (blocks)
        "GEN_MIN_CONFIG_TIMELOCK": 10_800,
        "GEN_MAX_CONFIG_TIMELOCK": 302_400,
    },
}


TOKENS = {
    "base": {
        # important tokens / representations
        "WETH": "0x4200000000000000000000000000000000000006",
        "ETH": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "BTC": "0xbBbBBBBbbBBBbbbBbbBbbbbBBbBbbbbBbBbbBBbB",
    },
    "local": {
        # important tokens / representations
        "WETH": "0x4200000000000000000000000000000000000006",
        "ETH": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "BTC": "0xbBbBBBBbbBBBbbbBbbBbbbbBBbBbbbbBbBbbBBbB",
    },
}


INTEGRATION_ADDYS = {
    "base": {
        "RIPE_HQ": "0x6162df1b329E157479F8f1407E888260E0EC3d2b",
    },
}