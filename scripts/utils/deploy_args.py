from config.BluePrint import PARAMS, INTEGRATION_ADDYS, TOKENS, HOUR_IN_BLOCKS, DAY_IN_BLOCKS, MONTH_IN_BLOCKS, YEAR_IN_BLOCKS, VAULT_INFO, LEGO_IDS
from tests.constants import ZERO_ADDRESS, MAX_UINT256, EIGHTEEN_DECIMALS


class Blocks:
    HOUR = HOUR_IN_BLOCKS
    DAY = DAY_IN_BLOCKS
    MONTH = MONTH_IN_BLOCKS
    YEAR = YEAR_IN_BLOCKS


class Constants:
    ZERO_ADDRESS = ZERO_ADDRESS
    MAX_UINT256 = MAX_UINT256
    EIGHTEEN_DECIMALS = EIGHTEEN_DECIMALS


class BluePrint:
    def __init__(self, blueprint):
        self.blueprint = blueprint
        self.PARAMS = PARAMS[blueprint]
        self.INTEGRATION_ADDYS = INTEGRATION_ADDYS[blueprint]
        self.TOKENS = TOKENS[blueprint]
        self.VAULT_INFO = VAULT_INFO
        self.BLOCKS = Blocks
        self.CONSTANTS = Constants
        self.LEGO_IDS = LEGO_IDS


class DeployArgs:
    def __init__(self, sender, chain, ignore_logs, blueprint, rpc):
        self.sender = sender
        self.chain = chain
        self.ignore_logs = ignore_logs
        self.blueprint = BluePrint(blueprint)
        self.rpc = rpc
        self.LEGO_IDS = LEGO_IDS
