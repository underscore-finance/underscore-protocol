#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

implements: Defaults
from interfaces import Defaults
import interfaces.ConfigStructs as cs

EIGHTEEN_DECIMALS: constant(uint256) = 10 ** 18

# blocks
# Robinhood is an Arbitrum chain. EVM block.number is the ~12-second L1
# ancestor estimate, not the sub-second child height.
BLOCKS_PER_MINUTE: constant(uint256) = 5
HOUR_IN_BLOCKS: constant(uint256) = 60 * BLOCKS_PER_MINUTE
DAY_IN_BLOCKS: constant(uint256) = 24 * HOUR_IN_BLOCKS
WEEK_IN_BLOCKS: constant(uint256) = 7 * DAY_IN_BLOCKS
MONTH_IN_BLOCKS: constant(uint256) = 30 * DAY_IN_BLOCKS
YEAR_IN_BLOCKS: constant(uint256) = 365 * DAY_IN_BLOCKS

# user wallet templates deployed on Robinhood before this contract
USER_WALLET_TEMPLATE: immutable(address)
USER_WALLET_CONFIG_TEMPLATE: immutable(address)


@deploy
def __init__(
    _walletTemplate: address,
    _configTemplate: address,
):
    assert empty(address) not in [_walletTemplate, _configTemplate] # dev: invalid template
    assert _walletTemplate.is_contract and _configTemplate.is_contract # dev: invalid template
    assert _walletTemplate != _configTemplate # dev: duplicate template
    USER_WALLET_TEMPLATE = _walletTemplate
    USER_WALLET_CONFIG_TEMPLATE = _configTemplate


# general configs


@view
@external
def userWalletConfig() -> cs.UserWalletConfig:
    return cs.UserWalletConfig(
        walletTemplate = USER_WALLET_TEMPLATE,
        configTemplate = USER_WALLET_CONFIG_TEMPLATE,
        numUserWalletsAllowed = 100_000,
        # Fail closed until governance approves and adds a Robinhood creator.
        enforceCreatorWhitelist = True,
        minKeyActionTimeLock = DAY_IN_BLOCKS // 2,
        maxKeyActionTimeLock = 2 * WEEK_IN_BLOCKS,
        # Robinhood RIPE currently has no PriceDesk price. Rewards stay disabled
        # until governance approves a priced asset; do not copy Base RIPE here.
        depositRewardsAsset = empty(address),
        lootClaimCoolOffPeriod = 0,
        txFees = cs.TxFees(
            swapFee = 25,
            stableSwapFee = 25,
            rewardsFee = 20_00,
        ),
        ambassadorRevShare = cs.AmbassadorRevShare(
            swapRatio = 0,
            rewardsRatio = 0,
            yieldRatio = 0,
        ),
        yieldConfig = cs.YieldConfig(
            maxYieldIncrease = 5_00,
            performanceFee = 20_00,
            ambassadorBonusRatio = 100_00,
            bonusRatio = 100_00,
            # A zero bonus asset makes LootDistributor return before valuation.
            bonusAsset = empty(address),
        ),
    )


@view
@external
def agentConfig() -> cs.AgentConfig:
    # AgentConfig no longer carries an agent-template field. The AgentWrapper
    # blueprint deployed before DefaultsRobinhood only preserves nonce sequence.
    return cs.AgentConfig(
        startingAgent = empty(address),
        startingAgentActivationLength = 0,
    )


@view
@external
def managerConfig() -> cs.ManagerConfig:
    return cs.ManagerConfig(
        managerPeriod = DAY_IN_BLOCKS,
        managerActivationLength = MONTH_IN_BLOCKS,
        mustHaveUsdValueOnSwaps = True,
        maxNumSwapsPerPeriod = 2,
        maxSlippageOnSwaps = 5_00,
        onlyApprovedYieldOpps = True,
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
        lockDuration = 6 * MONTH_IN_BLOCKS,
    )


@view
@external
def securitySigners() -> DynArray[address, 10]:
    return []


@view
@external
def whitelistedCreators() -> DynArray[address, 50]:
    return []
