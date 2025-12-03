#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

implements: Defaults
from interfaces import Defaults
import interfaces.ConfigStructs as cs

EIGHTEEN_DECIMALS: constant(uint256) = 10 ** 18

# blocks
DAY_IN_BLOCKS: constant(uint256) = 43_200
WEEK_IN_BLOCKS: constant(uint256) = 7 * DAY_IN_BLOCKS
MONTH_IN_BLOCKS: constant(uint256) = 30 * DAY_IN_BLOCKS
YEAR_IN_BLOCKS: constant(uint256) = 365 * DAY_IN_BLOCKS

# user wallet templates
USER_WALLET_TEMPLATE: immutable(address)
USER_WALLET_CONFIG_TEMPLATE: immutable(address)

# agent
STARTING_AGENT: immutable(address)


@deploy
def __init__(
    _walletTemplate: address,
    _configTemplate: address,
    _startingAgent: address,
):
    USER_WALLET_TEMPLATE = _walletTemplate
    USER_WALLET_CONFIG_TEMPLATE = _configTemplate
    STARTING_AGENT = _startingAgent


# general configs


@view
@external
def userWalletConfig() -> cs.UserWalletConfig:
    return cs.UserWalletConfig(
        walletTemplate = USER_WALLET_TEMPLATE,
        configTemplate = USER_WALLET_CONFIG_TEMPLATE,
        numUserWalletsAllowed = max_value(uint256),
        enforceCreatorWhitelist = False,
        minKeyActionTimeLock = DAY_IN_BLOCKS // 2,
        maxKeyActionTimeLock = 7 * DAY_IN_BLOCKS,
        depositRewardsAsset = empty(address),
        lootClaimCoolOffPeriod = 0,
        txFees = cs.TxFees(
            swapFee = 0,
            stableSwapFee = 0,
            rewardsFee = 0,
        ),
        ambassadorRevShare = cs.AmbassadorRevShare(
            swapRatio = 0,
            rewardsRatio = 0,
            yieldRatio = 0,
        ),
        yieldConfig = cs.YieldConfig(
            maxYieldIncrease = 5_00,
            performanceFee = 20_00,
            ambassadorBonusRatio = 0,
            bonusRatio = 0,
            bonusAsset = empty(address),
        ),
    )


@view
@external
def agentConfig() -> cs.AgentConfig:
    return cs.AgentConfig(
        startingAgent = STARTING_AGENT,
        startingAgentActivationLength = 2 * YEAR_IN_BLOCKS,
    )


@view
@external
def managerConfig() -> cs.ManagerConfig:
    return cs.ManagerConfig(
        managerPeriod = MONTH_IN_BLOCKS,
        managerActivationLength = YEAR_IN_BLOCKS,
        mustHaveUsdValueOnSwaps = False,
        maxNumSwapsPerPeriod = 0,
        maxSlippageOnSwaps = 0,
        onlyApprovedYieldOpps = False,
    )


@view
@external
def payeeConfig() -> cs.PayeeConfig:
    return cs.PayeeConfig(
        payeePeriod = MONTH_IN_BLOCKS,
        payeeActivationLength = YEAR_IN_BLOCKS,
    )


@view
@external
def chequeConfig() -> cs.ChequeConfig:
    return cs.ChequeConfig(
        maxNumActiveCheques = 3,
        instantUsdThreshold = 100 * EIGHTEEN_DECIMALS,
        periodLength = DAY_IN_BLOCKS,
        expensiveDelayBlocks = DAY_IN_BLOCKS,
        defaultExpiryBlocks = 2 * DAY_IN_BLOCKS,
    )


@view
@external
def ripeRewardsConfig() -> cs.RipeRewardsConfig:
    return cs.RipeRewardsConfig(
        stakeRatio = 80_00,
        lockDuration = 1 * DAY_IN_BLOCKS,
    )