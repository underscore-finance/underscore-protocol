# time (blocks)
HOUR_IN_BLOCKS = 1_800
DAY_IN_BLOCKS = 43_200
MONTH_IN_BLOCKS = DAY_IN_BLOCKS * 30
YEAR_IN_BLOCKS = DAY_IN_BLOCKS * 365


PARAMS = {
    "base": {
        # undy hq - gov changes (blocks)
        "UNDY_HQ_MIN_GOV_TIMELOCK": 1 * DAY_IN_BLOCKS,
        "UNDY_HQ_MAX_GOV_TIMELOCK": 7 * DAY_IN_BLOCKS,
        # undy hq - registry changes (blocks)
        "UNDY_HQ_MIN_REG_TIMELOCK": 12 * HOUR_IN_BLOCKS,
        "UNDY_HQ_MAX_REG_TIMELOCK": 7 * DAY_IN_BLOCKS,
        # gen config changes (blocks)
        "GEN_MIN_CONFIG_TIMELOCK": 6 * HOUR_IN_BLOCKS,
        "GEN_MAX_CONFIG_TIMELOCK": 7 * DAY_IN_BLOCKS,
        # boss validator
        "BOSS_MIN_MANAGER_PERIOD": 12 * HOUR_IN_BLOCKS,
        "BOSS_MAX_MANAGER_PERIOD": 1 * YEAR_IN_BLOCKS,
        "BOSS_MIN_ACTIVATION_LENGTH": 1 * HOUR_IN_BLOCKS,
        "BOSS_MAX_ACTIVATION_LENGTH": 5 * YEAR_IN_BLOCKS,
        "BOSS_MAX_START_DELAY": 1 * MONTH_IN_BLOCKS,
        # paymaster
        "PAYMASTER_MIN_PAYEE_PERIOD": 12 * HOUR_IN_BLOCKS,
        "PAYMASTER_MAX_PAYEE_PERIOD": 1 * YEAR_IN_BLOCKS,
        "PAYMASTER_MIN_ACTIVATION_LENGTH": 1 * HOUR_IN_BLOCKS,
        "PAYMASTER_MAX_ACTIVATION_LENGTH": 5 * YEAR_IN_BLOCKS,
        "PAYMASTER_MAX_START_DELAY": 1 * MONTH_IN_BLOCKS,
    },
    "local": {
        # undy hq - gov changes (blocks)
        "UNDY_HQ_MIN_GOV_TIMELOCK": 1 * DAY_IN_BLOCKS,
        "UNDY_HQ_MAX_GOV_TIMELOCK": 7 * DAY_IN_BLOCKS,
        # undy hq - registry changes (blocks)
        "UNDY_HQ_MIN_REG_TIMELOCK": 12 * HOUR_IN_BLOCKS,
        "UNDY_HQ_MAX_REG_TIMELOCK": 7 * DAY_IN_BLOCKS,
        # gen config changes (blocks)
        "GEN_MIN_CONFIG_TIMELOCK": 6 * HOUR_IN_BLOCKS,
        "GEN_MAX_CONFIG_TIMELOCK": 7 * DAY_IN_BLOCKS,
        # boss validator
        "BOSS_MIN_MANAGER_PERIOD": 12 * HOUR_IN_BLOCKS,
        "BOSS_MAX_MANAGER_PERIOD": 1 * YEAR_IN_BLOCKS,
        "BOSS_MIN_ACTIVATION_LENGTH": 1 * HOUR_IN_BLOCKS,
        "BOSS_MAX_ACTIVATION_LENGTH": 5 * YEAR_IN_BLOCKS,
        "BOSS_MAX_START_DELAY": 1 * MONTH_IN_BLOCKS,
        # paymaster
        "PAYMASTER_MIN_PAYEE_PERIOD": 12 * HOUR_IN_BLOCKS,
        "PAYMASTER_MAX_PAYEE_PERIOD": 1 * YEAR_IN_BLOCKS,
        "PAYMASTER_MIN_ACTIVATION_LENGTH": 1 * HOUR_IN_BLOCKS,
        "PAYMASTER_MAX_ACTIVATION_LENGTH": 5 * YEAR_IN_BLOCKS,
        "PAYMASTER_MAX_START_DELAY": 1 * MONTH_IN_BLOCKS,
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