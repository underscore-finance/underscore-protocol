# @version 0.4.3

implements: Defaults
from interfaces import Defaults
import interfaces.ConfigStructs as cs

# blocks
DAY_IN_BLOCKS: constant(uint256) = 43_200
WEEK_IN_BLOCKS: constant(uint256) = 7 * DAY_IN_BLOCKS
MONTH_IN_BLOCKS: constant(uint256) = 30 * DAY_IN_BLOCKS
YEAR_IN_BLOCKS: constant(uint256) = 365 * DAY_IN_BLOCKS

# user wallet templates
USER_WALLET_TEMPLATE: immutable(address)
USER_WALLET_CONFIG_TEMPLATE: immutable(address)

# agent template
AGENT_TEMPLATE: immutable(address)
STARTING_AGENT: immutable(address)

# trial funds and rewards
TRIAL_ASSET: immutable(address)
TRIAL_AMOUNT: immutable(uint256)
REWARDS_ASSET: immutable(address)


@deploy
def __init__(
    _walletTemplate: address,
    _configTemplate: address,
    _agentTemplate: address,
    _startingAgent: address,
    _trialAsset: address,
    _trialAmount: uint256,
    _rewardsAsset: address,
):
    USER_WALLET_TEMPLATE = _walletTemplate
    USER_WALLET_CONFIG_TEMPLATE = _configTemplate
    AGENT_TEMPLATE = _agentTemplate
    STARTING_AGENT = _startingAgent

    TRIAL_ASSET = _trialAsset
    TRIAL_AMOUNT = _trialAmount
    REWARDS_ASSET = _rewardsAsset


# general configs


@view
@external
def userWalletConfig() -> cs.UserWalletConfig:
    return cs.UserWalletConfig(
        walletTemplate = USER_WALLET_TEMPLATE,
        configTemplate = USER_WALLET_CONFIG_TEMPLATE,
        trialAsset = TRIAL_ASSET,
        trialAmount = TRIAL_AMOUNT,
        numUserWalletsAllowed = 25,
        enforceCreatorWhitelist = True,
        minKeyActionTimeLock = DAY_IN_BLOCKS // 2,
        maxKeyActionTimeLock = 7 * DAY_IN_BLOCKS,
        defaultStaleBlocks = DAY_IN_BLOCKS // 12,
        depositRewardsAsset = REWARDS_ASSET,
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
        defaultYieldMaxIncrease = 5_00,
        defaultYieldPerformanceFee = 20_00,
        defaultYieldAmbassadorBonusRatio = 0,
        defaultYieldBonusRatio = 0,
        defaultYieldAltBonusAsset = empty(address),
    )


@view
@external
def agentConfig() -> cs.AgentConfig:
    return cs.AgentConfig(
        agentTemplate = AGENT_TEMPLATE,
        numAgentsAllowed = 25,
        enforceCreatorWhitelist = True,
        startingAgent = STARTING_AGENT,
        startingAgentActivationLength = 2 * YEAR_IN_BLOCKS,
    )


@view
@external
def managerConfig() -> cs.ManagerConfig:
    return cs.ManagerConfig(
        managerPeriod = DAY_IN_BLOCKS,
        managerActivationLength = MONTH_IN_BLOCKS,
    )


@view
@external
def payeeConfig() -> cs.PayeeConfig:
    return cs.PayeeConfig(
        payeePeriod = MONTH_IN_BLOCKS,
        payeeActivationLength = YEAR_IN_BLOCKS,
    )