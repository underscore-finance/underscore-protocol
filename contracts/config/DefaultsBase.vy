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
USER_WALLET_TEMPLATE: constant(address) = 0x880E453Ec494FB17bffba537BeaB4Cc6CD1B7C12
USER_WALLET_CONFIG_TEMPLATE: constant(address) = 0xbF7bAdf4c71102cA49b3f82D50348256cE6C10Fb

# agent
STARTING_AGENT: constant(address) = 0x761fCDFfF8B187901eA11415237632A3F7E0203B
WALLET_CREATOR: constant(address) = 0x84edC07f0Cead3275059373F8FA47A566Dd429df

# rewards
REWARDS_ASSET: constant(address) = 0x2A0a59d6B975828e781EcaC125dBA40d7ee5dDC0
BONUS_ASSET: constant(address) = 0x2A0a59d6B975828e781EcaC125dBA40d7ee5dDC0


# general configs


@view
@external
def userWalletConfig() -> cs.UserWalletConfig:
    return cs.UserWalletConfig(
        walletTemplate = USER_WALLET_TEMPLATE,
        configTemplate = USER_WALLET_CONFIG_TEMPLATE,
        numUserWalletsAllowed = 100_000,
        enforceCreatorWhitelist = True,
        minKeyActionTimeLock = DAY_IN_BLOCKS // 2,
        maxKeyActionTimeLock = 2 * WEEK_IN_BLOCKS,
        depositRewardsAsset = REWARDS_ASSET,
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
            bonusAsset = BONUS_ASSET,
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
    return [WALLET_CREATOR]


@view
@external
def whitelistedCreators() -> DynArray[address, 50]:
    return [WALLET_CREATOR]
