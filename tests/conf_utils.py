import pytest
import boa
from constants import HUNDRED_PERCENT, EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ONE_MONTH_IN_BLOCKS, ONE_YEAR_IN_BLOCKS, ZERO_ADDRESS


def filter_logs(contract, event_name, _strict=False):
    return [e for e in contract.get_logs(strict=_strict) if type(e).__name__ == event_name]


@pytest.fixture(scope="session")
def _test():
    def _test(_expectedValue, _actualValue, _buffer=50):
        if _expectedValue == 0 or _actualValue == 0:
            assert _expectedValue == _actualValue
        else:
            buffer = _expectedValue * _buffer // HUNDRED_PERCENT
            assert _expectedValue + buffer >= _actualValue >= _expectedValue - buffer

    yield _test


#################
# Global Config #
#################


# general wallet config (mission control)


@pytest.fixture(scope="session")
def setUserWalletConfig(mission_control, switchboard_alpha, user_wallet_template, user_wallet_config_template, createTxFees, createAmbassadorRevShare):
    def setUserWalletConfig(
        _walletTemplate = user_wallet_template,
        _configTemplate = user_wallet_config_template,
        _trialAsset = ZERO_ADDRESS,
        _trialAmount = 0,
        _numUserWalletsAllowed = 100,
        _enforceCreatorWhitelist = False,
        _minTimeLock = ONE_DAY_IN_BLOCKS // 2,
        _maxTimeLock = 7 * ONE_DAY_IN_BLOCKS,
        _staleBlocks = 0,
        _depositRewardsAsset = ZERO_ADDRESS,
        _txFees = createTxFees(),
        _ambassadorRevShare = createAmbassadorRevShare(),
        _defaultYieldMaxIncrease = 5_00,
        _defaultYieldPerformanceFee = 20_00,
        _defaultYieldAmbassadorBonusRatio = 0,
        _defaultYieldBonusRatio = 0,
        _defaultYieldAltBonusAsset = ZERO_ADDRESS,
        _lootClaimCoolOffPeriod = 0,
    ):
        config = (
            _walletTemplate,
            _configTemplate,
            _trialAsset,
            _trialAmount,
            _numUserWalletsAllowed,
            _enforceCreatorWhitelist,
            _minTimeLock,
            _maxTimeLock,
            _staleBlocks,
            _depositRewardsAsset,
            _txFees,
            _ambassadorRevShare,
            _defaultYieldMaxIncrease,
            _defaultYieldPerformanceFee,
            _defaultYieldAmbassadorBonusRatio,
            _defaultYieldBonusRatio,
            _defaultYieldAltBonusAsset,
            _lootClaimCoolOffPeriod,
        )
        mission_control.setUserWalletConfig(config, sender=switchboard_alpha.address)
    yield setUserWalletConfig


@pytest.fixture(scope="session")
def createTxFees():
    def createTxFees(
        _swapFee = 0,
        _stableSwapFee = 0,
        _rewardsFee = 0,
    ):
        return (
            _swapFee,
            _stableSwapFee,
            _rewardsFee,
        )
    yield createTxFees


@pytest.fixture(scope="session")
def createAmbassadorRevShare():
    def createAmbassadorRevShare(
        _swapRatio = 0,
        _rewardsRatio = 0,
        _yieldRatio = 0,
    ):
        return (
            _swapRatio,
            _rewardsRatio,
            _yieldRatio,
        )
    yield createAmbassadorRevShare


# asset config (mission control)


@pytest.fixture(scope="session")
def setAssetConfig(mission_control, switchboard_alpha, createTxFees, createAmbassadorRevShare, createAssetYieldConfig):
    def setAssetConfig(
        _asset,
        _legoId = 1,
        _isStablecoin = False,
        _staleBlocks = 0,
        _txFees = createTxFees(),
        _ambassadorRevShare = createAmbassadorRevShare(),
        _yieldConfig = createAssetYieldConfig(),
    ):
        config = (
            _legoId,
            _isStablecoin,
            _asset.decimals(),
            _staleBlocks,
            _txFees,
            _ambassadorRevShare,
            _yieldConfig,
        )
        mission_control.setAssetConfig(_asset, config, sender=switchboard_alpha.address)
    yield setAssetConfig


@pytest.fixture(scope="session")
def createAssetYieldConfig():
    def createAssetYieldConfig(
        _isYieldAsset = False,
        _isRebasing = False,
        _underlyingAsset = ZERO_ADDRESS,
        _maxYieldIncrease = 5_00,
        _performanceFee = 20_00,
        _ambassadorBonusRatio = 0,
        _bonusRatio = 0,
        _altBonusAsset = ZERO_ADDRESS,
    ):
        return (
            _isYieldAsset,
            _isRebasing,
            _underlyingAsset,
            _maxYieldIncrease,
            _performanceFee,
            _ambassadorBonusRatio,
            _bonusRatio,
            _altBonusAsset,
        )
    yield createAssetYieldConfig


# agent config (mission control)


@pytest.fixture(scope="session")
def setAgentConfig(mission_control, switchboard_alpha, agent_template, agent_eoa):
    def setAgentConfig(
        _agentTemplate = agent_template,
        _numAgentsAllowed = 100,
        _enforceCreatorWhitelist = False,
        _startingAgent = agent_eoa,
        _startingAgentActivationLength = ONE_YEAR_IN_BLOCKS,
    ):
        config = (
            _agentTemplate,
            _numAgentsAllowed,
            _enforceCreatorWhitelist,
            _startingAgent,
            _startingAgentActivationLength,
        )
        mission_control.setAgentConfig(config, sender=switchboard_alpha.address)
    yield setAgentConfig


# manager config (mission control)


@pytest.fixture(scope="session")
def setManagerConfig(mission_control, switchboard_alpha):
    def setManagerConfig(
        _managerPeriod = ONE_MONTH_IN_BLOCKS,
        _defaultActivationLength = ONE_YEAR_IN_BLOCKS,
    ):
        config = (
            _managerPeriod,
            _defaultActivationLength,
        )
        mission_control.setManagerConfig(config, sender=switchboard_alpha.address)
    yield setManagerConfig


# payee settings (mission control)


@pytest.fixture(scope="session")
def setMissionControlPayeeConfig(mission_control, switchboard_alpha):
    def setMissionControlPayeeConfig(
        _payeePeriod = ONE_MONTH_IN_BLOCKS,
        _payeeActivationLength = ONE_YEAR_IN_BLOCKS,
    ):
        config = (
            _payeePeriod,
            _payeeActivationLength,
        )
        mission_control.setMissionControlPayeeConfig(config, sender=switchboard_alpha.address)
    yield setMissionControlPayeeConfig


##########################
# User Wallet - Managers #
##########################


# global manager settings (user wallet)


@pytest.fixture(scope="session")
def createGlobalManagerSettings(createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms):
    def createGlobalManagerSettings(
        _managerPeriod = ONE_MONTH_IN_BLOCKS,
        _startDelay = ONE_DAY_IN_BLOCKS // 2,
        _activationLength = ONE_YEAR_IN_BLOCKS,
        _canOwnerManage = True,
        _limits = None,
        _legoPerms = None,
        _whitelistPerms = None,
        _transferPerms = None,
        _allowedAssets = [],
    ):
        if _limits is None:
            _limits = createManagerLimits()
        if _legoPerms is None:
            _legoPerms = createLegoPerms()
        if _whitelistPerms is None:
            _whitelistPerms = createWhitelistPerms()
        if _transferPerms is None:
            _transferPerms = createTransferPerms()
            
        return (
            _managerPeriod,
            _startDelay,
            _activationLength,
            _canOwnerManage,
            _limits,
            _legoPerms,
            _whitelistPerms,
            _transferPerms,
            _allowedAssets,
        )
    yield createGlobalManagerSettings


# manager data (user wallet)


@pytest.fixture(scope="session")
def createManagerData():
    def createManagerData(
        _numTxsInPeriod = 0,
        _totalUsdValueInPeriod = 0,
        _totalNumTxs = 0,
        _totalUsdValue = 0,
        _lastTxBlock = 0,
        _periodStartBlock = 0,
    ):
        return (
            _numTxsInPeriod,
            _totalUsdValueInPeriod,
            _totalNumTxs,
            _totalUsdValue,
            _lastTxBlock,
            _periodStartBlock,
        )
    yield createManagerData


# manager settings (user wallet)


@pytest.fixture(scope="session")
def createManagerSettings(createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms):
    def createManagerSettings(
        _startBlock = 0,
        _expiryBlock = 0,
        _limits = None,
        _legoPerms = None,
        _whitelistPerms = None,
        _transferPerms = None,
        _allowedAssets = [],
        _canClaimLoot = False,
    ):
        if _startBlock == 0:
            _startBlock = boa.env.evm.patch.block_number
        if _expiryBlock == 0:
            _expiryBlock = _startBlock + ONE_YEAR_IN_BLOCKS
        
        if _limits is None:
            _limits = createManagerLimits()
        if _legoPerms is None:
            _legoPerms = createLegoPerms()
        if _whitelistPerms is None:
            _whitelistPerms = createWhitelistPerms()
        if _transferPerms is None:
            _transferPerms = createTransferPerms()
            
        return (
            _startBlock,
            _expiryBlock,
            _limits,
            _legoPerms,
            _whitelistPerms,
            _transferPerms,
            _allowedAssets,
            _canClaimLoot,
        )
    yield createManagerSettings


@pytest.fixture(scope="session")
def createManagerLimits():
    def createManagerLimits(
        _maxUsdValuePerTx = 0, # 0 = unlimited
        _maxUsdValuePerPeriod = 0, # 0 = unlimited
        _maxUsdValueLifetime = 0, # 0 = unlimited
        _maxNumTxsPerPeriod = 0, # 0 = unlimited
        _txCooldownBlocks = 0, # 0 = no cooldown
        _failOnZeroPrice = False,
    ):
        return (
            _maxUsdValuePerTx,
            _maxUsdValuePerPeriod,
            _maxUsdValueLifetime,
            _maxNumTxsPerPeriod,
            _txCooldownBlocks,
            _failOnZeroPrice,
        )
    yield createManagerLimits


@pytest.fixture(scope="session")
def createLegoPerms():
    def createLegoPerms(
        _canManageYield = True,
        _canBuyAndSell = True,
        _canManageDebt = True,
        _canManageLiq = True,
        _canClaimRewards = True,
        _allowedLegos = [],
    ):
        return (
            _canManageYield,
            _canBuyAndSell,
            _canManageDebt,
            _canManageLiq,
            _canClaimRewards,
            _allowedLegos,
        )
    yield createLegoPerms


@pytest.fixture(scope="session")
def createWhitelistPerms():
    def createWhitelistPerms(
        _canAddPending = False,
        _canConfirm = True,
        _canCancel = True,
        _canRemove = False,
    ):
        return (
            _canAddPending,
            _canConfirm,
            _canCancel,
            _canRemove,
        )
    yield createWhitelistPerms


@pytest.fixture(scope="session")
def createTransferPerms():
    def createTransferPerms(
        _canTransfer = True,
        _canCreateCheque = True,
        _canAddPendingPayee = True,
        _allowedPayees = [],
    ):
        return (
            _canTransfer,
            _canCreateCheque,
            _canAddPendingPayee,
            _allowedPayees,
        )
    yield createTransferPerms


########################
# User Wallet - Payees #
########################


# global payee settings (user wallet)


@pytest.fixture(scope="session")
def createGlobalPayeeSettings(createPayeeLimits):
    def createGlobalPayeeSettings(
        _defaultPeriodLength = ONE_MONTH_IN_BLOCKS,
        _startDelay = ONE_DAY_IN_BLOCKS // 2,
        _activationLength = ONE_YEAR_IN_BLOCKS,
        _maxNumTxsPerPeriod = 0, # unlimited by default
        _txCooldownBlocks = 0, # no cooldown by default
        _failOnZeroPrice = False, # accept zero-priced transactions by default
        _usdLimits = None,
        _canPayOwner = True, # allow payments to owner by default
    ):
        if _usdLimits is None:
            _usdLimits = createPayeeLimits()

        return (
            _defaultPeriodLength,
            _startDelay,
            _activationLength,
            _maxNumTxsPerPeriod,
            _txCooldownBlocks,
            _failOnZeroPrice,
            _usdLimits,
            _canPayOwner,
        )
    yield createGlobalPayeeSettings


# payee limits


@pytest.fixture(scope="session")
def createPayeeLimits():
    def createPayeeLimits(
        _perTxCap = 0, # 0 = unlimited
        _perPeriodCap = 0, # 0 = unlimited
        _lifetimeCap = 0, # 0 = unlimited
    ):
        return (
            _perTxCap,
            _perPeriodCap,
            _lifetimeCap,
        )
    yield createPayeeLimits


# payee settings (user wallet)


@pytest.fixture(scope="session")
def createPayeeSettings(createPayeeLimits):
    def createPayeeSettings(
        _startBlock = 0,  # 0 = current block
        _expiryBlock = 0,  # 0 = 1 year from start
        _canPull = False,
        _periodLength = ONE_MONTH_IN_BLOCKS,
        _maxNumTxsPerPeriod = 0,  # 0 = unlimited
        _txCooldownBlocks = 0,  # 0 = no cooldown
        _failOnZeroPrice = False,
        _primaryAsset = ZERO_ADDRESS,  # zero address
        _onlyPrimaryAsset = False,
        _unitLimits = None,
        _usdLimits = None,
    ):
        if _startBlock == 0:
            _startBlock = boa.env.evm.patch.block_number
        if _expiryBlock == 0:
            _expiryBlock = _startBlock + ONE_YEAR_IN_BLOCKS
        
        if _unitLimits is None:
            _unitLimits = createPayeeLimits()
        if _usdLimits is None:
            _usdLimits = createPayeeLimits()
            
        return (
            _startBlock,
            _expiryBlock,
            _canPull,
            _periodLength,
            _maxNumTxsPerPeriod,
            _txCooldownBlocks,
            _failOnZeroPrice,
            _primaryAsset,
            _onlyPrimaryAsset,
            _unitLimits,
            _usdLimits,
        )
    yield createPayeeSettings


# payee data


@pytest.fixture(scope="session")
def createPayeeData():
    def createPayeeData(
        _numTxsInPeriod = 0,
        _totalUnitsInPeriod = 0,
        _totalUsdValueInPeriod = 0,
        _totalNumTxs = 0,
        _totalUnits = 0,
        _totalUsdValue = 0,
        _lastTxBlock = 0,
        _periodStartBlock = 0,
    ):
        return (
            _numTxsInPeriod,
            _totalUnitsInPeriod,
            _totalUsdValueInPeriod,
            _totalNumTxs,
            _totalUnits,
            _totalUsdValue,
            _lastTxBlock,
            _periodStartBlock,
        )
    yield createPayeeData
