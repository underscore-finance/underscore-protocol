
from enum import IntFlag

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
EIGHTEEN_DECIMALS = 10 ** 18
MAX_UINT256 = 2 ** 256 - 1
HUNDRED_PERCENT = 100_00
MIN_INT24 = -8_388_608
MAX_INT24 = 8_388_607

# time (blocks)
ONE_DAY_IN_BLOCKS = 43_200
ONE_MONTH_IN_BLOCKS = ONE_DAY_IN_BLOCKS * 30
ONE_YEAR_IN_BLOCKS = ONE_DAY_IN_BLOCKS * 365


# Action types for UserWallet operations
# These match the Vyper flag enum (powers of 2)
class ACTION_TYPE(IntFlag):
    TRANSFER = 1  # 2^0
    EARN_DEPOSIT = 2  # 2^1
    EARN_WITHDRAW = 4  # 2^2
    EARN_REBALANCE = 8  # 2^3
    SWAP = 16  # 2^4
    MINT_REDEEM = 32  # 2^5
    CONFIRM_MINT_REDEEM = 64  # 2^6
    ADD_COLLATERAL = 128  # 2^7
    REMOVE_COLLATERAL = 256  # 2^8
    BORROW = 512  # 2^9
    REPAY_DEBT = 1024  # 2^10
    REWARDS = 2048  # 2^11
    ETH_TO_WETH = 4096  # 2^12
    WETH_TO_ETH = 8192  # 2^13
    ADD_LIQ = 16384  # 2^14
    REMOVE_LIQ = 32768  # 2^15
    ADD_LIQ_CONC = 65536  # 2^16
    REMOVE_LIQ_CONC = 131072  # 2^17


# Action types for UserWallet operations
# These match the Vyper flag enum (powers of 2)
class WHITELIST_ACTION(IntFlag):
    ADD_PENDING = 1  # 2^0
    CONFIRM_WHITELIST = 2  # 2^1
    CANCEL_WHITELIST = 4  # 2^2
    REMOVE_WHITELIST = 8  # 2^3


# Action types for SwitchboardAlpha configuration operations
# These match the Vyper flag enum (powers of 2)
class CONFIG_ACTION_TYPE(IntFlag):
    USER_WALLET_TEMPLATES = 1  # 2^0
    TRIAL_FUNDS = 2  # 2^1
    WALLET_CREATION_LIMITS = 4  # 2^2
    KEY_ACTION_TIMELOCK_BOUNDS = 8  # 2^3
    DEFAULT_STALE_BLOCKS = 16  # 2^4
    TX_FEES = 32  # 2^5
    AMBASSADOR_REV_SHARE = 64  # 2^6
    DEFAULT_YIELD_PARAMS = 128  # 2^7
    LOOT_PARAMS = 256  # 2^8
    AGENT_TEMPLATE = 512  # 2^9
    AGENT_CREATION_LIMITS = 1024  # 2^10
    STARTER_AGENT_PARAMS = 2048  # 2^11
    MANAGER_CONFIG = 4096  # 2^12
    PAYEE_CONFIG = 8192  # 2^13
    CAN_PERFORM_SECURITY_ACTION = 16384  # 2^14
