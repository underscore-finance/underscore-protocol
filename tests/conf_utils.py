import pytest
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


##########
# Config #
##########


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


################
# Asset Config #
################


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


#########
# Agent #
#########


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


###########
# Manager #
###########


@pytest.fixture(scope="session")
def setManagerConfig(mission_control, switchboard_alpha, agent_eoa):
    def setManagerConfig(
        _managerPeriod = ONE_DAY_IN_BLOCKS,
        _defaultActivationLength = ONE_MONTH_IN_BLOCKS,
    ):
        config = (
            _managerPeriod,
            _defaultActivationLength,
        )
        mission_control.setManagerConfig(config, sender=switchboard_alpha.address)
    yield setManagerConfig


# Manager Limits
@pytest.fixture(scope="session")
def createManagerLimits():
    def createManagerLimits(
        _maxUsdValuePerTx = 0,  # 0 = unlimited
        _maxUsdValuePerPeriod = 0,  # 0 = unlimited
        _maxUsdValueLifetime = 0,  # 0 = unlimited
        _maxNumTxsPerPeriod = 0,  # 0 = unlimited
        _txCooldownBlocks = 0,  # 0 = no cooldown
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


# Lego Permissions
@pytest.fixture(scope="session")
def createLegoPerms():
    def createLegoPerms(
        _canManageYield = True,
        _canBuyAndSell = True,
        _canManageDebt = True,
        _canManageLiq = True,
        _canClaimRewards = True,
        _allowedLegos = [],  # empty = all legos allowed
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


# Whitelist Permissions
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


# Transfer Permissions
@pytest.fixture(scope="session")
def createTransferPerms():
    def createTransferPerms(
        _canTransfer = True,
        _canCreateCheque = True,
        _canAddPendingPayee = True,
        _allowedPayees = [],  # empty = all payees allowed
    ):
        return (
            _canTransfer,
            _canCreateCheque,
            _canAddPendingPayee,
            _allowedPayees,
        )
    yield createTransferPerms


# Manager Data
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


# Manager Settings
@pytest.fixture(scope="session")
def createManagerSettings(createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms):
    def createManagerSettings(
        _startBlock = 0,
        _expiryBlock = 0,  # 0 = will default to 1 year from start
        _limits = None,
        _legoPerms = None,
        _whitelistPerms = None,
        _transferPerms = None,
        _allowedAssets = [],
    ):
        import boa
        
        # If startBlock is 0, use current block
        if _startBlock == 0:
            _startBlock = boa.env.evm.patch.block_number
        
        # If expiryBlock is 0, set to 1 year after startBlock
        if _expiryBlock == 0:
            _expiryBlock = _startBlock + ONE_YEAR_IN_BLOCKS
        
        # Use defaults if not provided
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
        )
    yield createManagerSettings


# Global Manager Settings
@pytest.fixture(scope="session")
def createGlobalManagerSettings(createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms):
    def createGlobalManagerSettings(
        _managerPeriod = ONE_DAY_IN_BLOCKS,
        _startDelay = ONE_DAY_IN_BLOCKS,
        _activationLength = ONE_MONTH_IN_BLOCKS,
        _canOwnerManage = True,
        _limits = None,
        _legoPerms = None,
        _whitelistPerms = None,
        _transferPerms = None,
        _allowedAssets = [],
    ):
        # Use defaults if not provided
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


# Set Global Manager Settings (creates and sets in contract)
@pytest.fixture(scope="session")
def setGlobalManagerSettings(createGlobalManagerSettings, boss_validator):
    def setGlobalManagerSettings(
        _userWalletConfig,  # UserWalletConfig instance
        _managerPeriod = ONE_DAY_IN_BLOCKS,
        _startDelay = ONE_DAY_IN_BLOCKS,
        _activationLength = ONE_MONTH_IN_BLOCKS,
        _canOwnerManage = True,
        _limits = None,
        _legoPerms = None,
        _whitelistPerms = None,
        _transferPerms = None,
        _allowedAssets = [],
    ):
        # Create the settings
        settings = createGlobalManagerSettings(
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
        
        # Set in contract
        _userWalletConfig.setGlobalManagerSettings(settings, sender=boss_validator)
        
        return settings
    yield setGlobalManagerSettings


# Set Manager Settings (creates and sets in contract)
@pytest.fixture(scope="session")
def setManagerSettings(createManagerSettings, boss_validator):
    def setManagerSettings(
        _userWalletConfig,  # UserWalletConfig instance
        _manager,  # Manager address
        _startBlock = 0,
        _expiryBlock = 0,
        _limits = None,
        _legoPerms = None,
        _whitelistPerms = None,
        _transferPerms = None,
        _allowedAssets = [],
    ):
        # Create the settings
        settings = createManagerSettings(
            _startBlock,
            _expiryBlock,
            _limits,
            _legoPerms,
            _whitelistPerms,
            _transferPerms,
            _allowedAssets,
        )
        
        # Add manager with settings
        _userWalletConfig.addManager(_manager, settings, sender=boss_validator)
        
        return settings
    yield setManagerSettings


##########
# Payees #
##########


@pytest.fixture(scope="session")
def setPayeeConfig(mission_control, switchboard_alpha):
    def setPayeeConfig(
        _payeePeriod = ONE_DAY_IN_BLOCKS,
        _payeeActivationLength = ONE_MONTH_IN_BLOCKS,
    ):
        config = (
            _payeePeriod,
            _payeeActivationLength,
        )
        mission_control.setPayeeConfig(config, sender=switchboard_alpha.address)
    yield setPayeeConfig


# Payee Limits
@pytest.fixture(scope="session")
def createPayeeLimits():
    def createPayeeLimits(
        _perTxCap = 0,  # 0 = unlimited
        _perPeriodCap = 0,  # 0 = unlimited
        _lifetimeCap = 0,  # 0 = unlimited
    ):
        return (
            _perTxCap,
            _perPeriodCap,
            _lifetimeCap,
        )
    yield createPayeeLimits


# Payee Data
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


# Payee Settings
@pytest.fixture(scope="session")
def createPayeeSettings(createPayeeLimits):
    def createPayeeSettings(
        _startBlock = 0,  # 0 = current block
        _expiryBlock = 0,  # 0 = 1 year from start
        _canPull = False,
        _periodLength = ONE_DAY_IN_BLOCKS,
        _maxNumTxsPerPeriod = 0,  # 0 = unlimited
        _txCooldownBlocks = 0,  # 0 = no cooldown
        _failOnZeroPrice = False,
        _primaryAsset = ZERO_ADDRESS,  # zero address
        _onlyPrimaryAsset = False,
        _unitLimits = None,
        _usdLimits = None,
    ):
        import boa
        
        # If startBlock is 0, use current block
        if _startBlock == 0:
            _startBlock = boa.env.evm.patch.block_number
        
        # If expiryBlock is 0, set to 1 year after startBlock
        if _expiryBlock == 0:
            _expiryBlock = _startBlock + ONE_YEAR_IN_BLOCKS
        
        # Use defaults if not provided
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


# Global Payee Settings
@pytest.fixture(scope="session")
def createGlobalPayeeSettings(createPayeeLimits):
    def createGlobalPayeeSettings(
        _defaultPeriodLength = ONE_DAY_IN_BLOCKS,
        _startDelay = ONE_DAY_IN_BLOCKS,
        _activationLength = ONE_YEAR_IN_BLOCKS,
        _maxNumTxsPerPeriod = 0,  # 0 = unlimited
        _txCooldownBlocks = 0,  # 0 = no cooldown
        _failOnZeroPrice = False,
        _usdLimits = None,
        _canPayOwner = True,
    ):
        # Use defaults if not provided
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


# Set Global Payee Settings (creates and sets in contract)
@pytest.fixture(scope="session")
def setGlobalPayeeSettings(createGlobalPayeeSettings, paymaster):
    def setGlobalPayeeSettings(
        _userWalletConfig,  # UserWalletConfig instance
        _defaultPeriodLength = ONE_DAY_IN_BLOCKS,
        _startDelay = ONE_DAY_IN_BLOCKS,
        _activationLength = ONE_YEAR_IN_BLOCKS,
        _maxNumTxsPerPeriod = 0,
        _txCooldownBlocks = 0,
        _failOnZeroPrice = False,
        _usdLimits = None,
        _canPayOwner = True,
    ):
        # Create the settings
        settings = createGlobalPayeeSettings(
            _defaultPeriodLength,
            _startDelay,
            _activationLength,
            _maxNumTxsPerPeriod,
            _txCooldownBlocks,
            _failOnZeroPrice,
            _usdLimits,
            _canPayOwner,
        )
        
        # Set in contract
        _userWalletConfig.setGlobalPayeeSettings(settings, sender=paymaster)
        
        return settings
    yield setGlobalPayeeSettings


# Set Payee Settings (creates and sets in contract)
@pytest.fixture(scope="session")
def setPayeeSettings(createPayeeSettings, paymaster):
    def setPayeeSettings(
        _userWalletConfig,  # UserWalletConfig instance
        _payee,  # Payee address
        _startBlock = 0,
        _expiryBlock = 0,
        _canPull = False,
        _periodLength = ONE_DAY_IN_BLOCKS,
        _maxNumTxsPerPeriod = 0,
        _txCooldownBlocks = 0,
        _failOnZeroPrice = False,
        _primaryAsset = ZERO_ADDRESS,
        _onlyPrimaryAsset = False,
        _unitLimits = None,
        _usdLimits = None,
    ):
        # Create the settings
        settings = createPayeeSettings(
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
        
        # Add payee with settings
        _userWalletConfig.addPayee(_payee, settings, sender=paymaster)
        
        return settings
    yield setPayeeSettings