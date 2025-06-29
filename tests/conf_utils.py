import pytest
from constants import HUNDRED_PERCENT, EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ONE_MONTH_IN_BLOCKS, ONE_YEAR_IN_BLOCKS


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
def setUserWalletConfig(mission_control, switchboard_alpha, user_wallet_template, user_wallet_config_template, alpha_token):
    def setUserWalletConfig(
        _walletTemplate = user_wallet_template,
        _configTemplate = user_wallet_config_template,
        _trialAsset = alpha_token,
        _trialAmount = 10 * EIGHTEEN_DECIMALS,
        _numUserWalletsAllowed = 100,
        _enforceCreatorWhitelist = False,
        _minTimeLock = 10,
        _maxTimeLock = 100,
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
        )
        mission_control.setUserWalletConfig(config, sender=switchboard_alpha.address)
    yield setUserWalletConfig


@pytest.fixture(scope="session")
def setWalletFees(mission_control, switchboard_alpha):
    def setWalletFees(
        _swapFee = 1_00,
        _stableSwapFee = 10,
        _rewardsFee = 20_00,
    ):
        config = (_swapFee, _stableSwapFee, _rewardsFee)
        mission_control.setWalletFees(config, sender=switchboard_alpha.address)
    yield setWalletFees


@pytest.fixture(scope="session")
def setDefaultYieldConfig(mission_control, switchboard_alpha):
    def setDefaultYieldConfig(
        _maxYieldIncrease = 5_00,
        _yieldProfitFee = 20_00,
    ):
        config = (_maxYieldIncrease, _yieldProfitFee)
        mission_control.setDefaultYieldConfig(config, sender=switchboard_alpha.address)
    yield setDefaultYieldConfig


@pytest.fixture(scope="session")
def setAgentConfig(mission_control, switchboard_alpha, agent_template):
    def setAgentConfig(
        _agentTemplate = agent_template,
        _numAgentsAllowed = 100,
        _enforceCreatorWhitelist = False,
    ):
        config = (
            _agentTemplate,
            _numAgentsAllowed,
            _enforceCreatorWhitelist,
        )
        mission_control.setAgentConfig(config, sender=switchboard_alpha.address)
    yield setAgentConfig


@pytest.fixture(scope="session")
def setAssetConfig(mission_control, switchboard_alpha, alpha_token):
    def setAssetConfig(
        _asset,
        _swapFee = 1_00,
        _stableSwapFee = 25,
        _rewardsFee = 20_00,
        _isStablecoin = False,
        _stalePriceNumBlocks = 0,
        _isYieldAsset = False,
        _isRebasing = False,
        _underlyingAsset = alpha_token,
        _maxYieldIncrease = 5_00,
        _yieldProfitFee = 20_00,
    ):
        fees = (
            _swapFee,
            _stableSwapFee,
            _rewardsFee,
        )
        config = (
            _isStablecoin,
            _isYieldAsset,
            _asset.decimals(),
            _stalePriceNumBlocks,
            fees,
        )
        mission_control.setAssetConfig(_asset, config, sender=switchboard_alpha.address)

        if _isYieldAsset:
            yieldConfig = (
                1,
                _isRebasing,
                _underlyingAsset,
                _maxYieldIncrease,
                _yieldProfitFee,
            )
            mission_control.setYieldAssetConfig(_asset, yieldConfig, sender=switchboard_alpha.address)
    yield setAssetConfig


@pytest.fixture(scope="session")
def setManagerConfig(mission_control, switchboard_alpha, agent_eoa):
    def setManagerConfig(
        _startingAgent = agent_eoa,
        _startingAgentActivationLength = ONE_YEAR_IN_BLOCKS,
        _managerPeriod = ONE_DAY_IN_BLOCKS,
        _defaultStartDelay = ONE_DAY_IN_BLOCKS,
        _defaultActivationLength = ONE_MONTH_IN_BLOCKS,
        _minManagerPeriod = ONE_DAY_IN_BLOCKS // 2,
        _maxManagerPeriod = 30 * ONE_DAY_IN_BLOCKS,
    ):
        config = (
            _startingAgent,
            _startingAgentActivationLength,
            _managerPeriod,
            _defaultStartDelay,
            _defaultActivationLength,
            _minManagerPeriod,
            _maxManagerPeriod,
        )
        mission_control.setManagerConfig(config, sender=switchboard_alpha.address)
    yield setManagerConfig
