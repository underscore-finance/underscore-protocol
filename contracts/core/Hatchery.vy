# @version 0.4.3

implements: Department

exports: addys.__interface__
exports: deptBasics.__interface__

initializes: addys
initializes: deptBasics[addys := addys]

import contracts.modules.Addys as addys
import contracts.modules.DeptBasics as deptBasics
from interfaces import Department

from ethereum.ercs import IERC20
from ethereum.ercs import IERC20Detailed

interface UserWalletConfig:
    def preparePayment(asset: address, legoId: uint256, underlyingAsset: address, amount: uint256) -> (uint256, uint256): nonpayable
    def setWallet(_wallet: address) -> bool: nonpayable
    def removeTrialFunds() -> uint256: nonpayable
    def trialFundsAmount() -> uint256: view
    def trialFundsAsset() -> address: view
    def owner() -> address: view

interface Ledger:
    def createUserWallet(_user: address, _ambassador: address): nonpayable
    def vaultTokens(_vaultToken: address) -> VaultToken: view
    def isUserWallet(_user: address) -> bool: view
    def createAgent(_agent: address): nonpayable
    def numUserWallets() -> uint256: view
    def numAgents() -> uint256: view

interface UserWallet:
    def assetData(asset: address) -> WalletAssetData: view
    def assets(i: uint256) -> address: view
    def walletConfig() -> address: view
    def numAssets() -> uint256: view

interface MissionControl:
    def getUserWalletCreationConfig(_creator: address) -> UserWalletCreationConfig: view
    def getAgentCreationConfig(_creator: address) -> AgentCreationConfig: view
    def getAssetUsdValueConfig(_asset: address) -> AssetUsdValueConfig: view

interface Appraiser:
    def getPricePerShareWithConfig(asset: address, legoAddr: address, staleBlocks: uint256) -> uint256: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

struct WalletAssetData:
    assetBalance: uint256
    usdValue: uint256
    isYieldAsset: bool
    lastYieldPrice: uint256

struct VaultToken:
    legoId: uint256
    underlyingAsset: address
    decimals: uint256
    isRebasing: bool

struct UserWalletCreationConfig:
    numUserWalletsAllowed: uint256
    isCreatorAllowed: bool
    walletTemplate: address
    configTemplate: address
    startingAgent: address
    startingAgentActivationLength: uint256
    managerPeriod: uint256
    managerActivationLength: uint256
    payeePeriod: uint256
    payeeActivationLength: uint256
    trialAsset: address
    trialAmount: uint256
    minKeyActionTimeLock: uint256
    maxKeyActionTimeLock: uint256

struct AgentCreationConfig:
    agentTemplate: address
    numAgentsAllowed: uint256
    isCreatorAllowed: bool
    minTimeLock: uint256
    maxTimeLock: uint256

struct AssetUsdValueConfig:
    legoId: uint256
    legoAddr: address
    decimals: uint256
    staleBlocks: uint256
    isYieldAsset: bool
    underlyingAsset: address

event UserWalletCreated:
    mainAddr: indexed(address)
    configAddr: indexed(address)
    owner: indexed(address)
    agent: address
    ambassador: address
    creator: address
    trialFundsAsset: address
    trialFundsAmount: uint256

event AgentCreated:
    agent: indexed(address)
    owner: indexed(address)
    creator: indexed(address)

HUNDRED_PERCENT: constant(uint256) = 100_00 # 100.00%

WETH: public(immutable(address))
ETH: public(immutable(address))


@deploy
def __init__(_undyHq: address, _wethAddr: address, _ethAddr: address):
    addys.__init__(_undyHq)
    deptBasics.__init__(False, False) # no minting

    WETH = _wethAddr
    ETH = _ethAddr


######################
# Create User Wallet #
######################


@external
def createUserWallet(
    _owner: address = msg.sender,
    _ambassador: address = empty(address),
    _shouldUseTrialFunds: bool = True,
    _groupId: uint256 = 1,
) -> address:
    assert not deptBasics.isPaused # dev: contract paused
    a: addys.Addys = addys._getAddys()

    config: UserWalletCreationConfig = staticcall MissionControl(a.missionControl).getUserWalletCreationConfig(msg.sender)

    # validation
    assert config.isCreatorAllowed # dev: creator not allowed
    assert empty(address) not in [config.walletTemplate, config.configTemplate, _owner] # dev: invalid setup
    if config.numUserWalletsAllowed != 0:
        assert staticcall Ledger(a.ledger).numUserWallets() < config.numUserWalletsAllowed # dev: max user wallets reached

    # ambassador
    ambassador: address = empty(address)
    if _ambassador != empty(address) and staticcall Ledger(a.ledger).isUserWallet(_ambassador):
        ambassador = _ambassador

    # trial funds
    trialFundsAsset: address = empty(address)
    trialFundsAmount: uint256 = 0
    if _shouldUseTrialFunds and config.trialAsset != empty(address) and config.trialAmount != 0 and staticcall IERC20(config.trialAsset).balanceOf(self) >= config.trialAmount:
        trialFundsAsset = config.trialAsset
        trialFundsAmount = config.trialAmount

    # create wallet contracts
    walletConfigAddr: address = create_from_blueprint(
        config.configTemplate,
        a.hq,
        _owner,
        _groupId,
        a.bossValidator,
        a.paymaster,
        a.migrator,
        config.startingAgent,
        config.startingAgentActivationLength,
        config.managerPeriod,
        config.managerActivationLength,
        config.payeePeriod,
        config.payeeActivationLength,
        trialFundsAsset,
        trialFundsAmount,
        WETH,
        ETH,
        config.minKeyActionTimeLock,
        config.maxKeyActionTimeLock,
    )
    mainWalletAddr: address = create_from_blueprint(config.walletTemplate, WETH, ETH, walletConfigAddr)
    assert extcall UserWalletConfig(walletConfigAddr).setWallet(mainWalletAddr) # dev: could not set wallet

    # update ledger
    extcall Ledger(a.ledger).createUserWallet(mainWalletAddr, ambassador)

    # transfer trial funds after initialization
    if trialFundsAsset != empty(address) and trialFundsAmount != 0:
        assert extcall IERC20(trialFundsAsset).transfer(mainWalletAddr, trialFundsAmount, default_return_value=True) # dev: gift transfer failed

    log UserWalletCreated(
        mainAddr=mainWalletAddr,
        configAddr=walletConfigAddr,
        owner=_owner,
        agent=config.startingAgent,
        ambassador=ambassador,
        creator=msg.sender,
        trialFundsAsset=trialFundsAsset,
        trialFundsAmount=trialFundsAmount,
    )
    return mainWalletAddr


################
# Create Agent #
################


@external
def createAgent(_owner: address = msg.sender) -> address:
    assert not deptBasics.isPaused # dev: contract paused
    a: addys.Addys = addys._getAddys()

    # validation
    config: AgentCreationConfig = staticcall MissionControl(a.missionControl).getAgentCreationConfig(msg.sender)
    assert config.isCreatorAllowed # dev: creator not allowed
    assert empty(address) not in [config.agentTemplate, _owner] # dev: invalid setup
    if config.numAgentsAllowed != 0:
        assert staticcall Ledger(a.ledger).numAgents() < config.numAgentsAllowed # dev: max agents reached

    # create agent contract
    agentAddr: address = create_from_blueprint(config.agentTemplate, a.hq, _owner, config.minTimeLock, config.maxTimeLock)

    # update ledger
    extcall Ledger(a.ledger).createAgent(agentAddr)

    log AgentCreated(
        agent=agentAddr,
        owner=_owner,
        creator=msg.sender,
    )
    return agentAddr


###############
# Trial Funds #
###############


# clawback trial funds


@external
def clawBackTrialFunds(_user: address) -> uint256:
    a: addys.Addys = addys._getAddys()
    assert staticcall Ledger(a.ledger).isUserWallet(_user) # dev: not a user wallet
    walletConfig: address = staticcall UserWallet(_user).walletConfig()
    assert addys._isSwitchboardAddr(msg.sender) or staticcall UserWalletConfig(walletConfig).owner() == msg.sender # dev: no perms
    return self._clawBackTrialFunds(_user, walletConfig, a.missionControl, a.legoBook, a.appraiser, a.ledger)


@internal
def _clawBackTrialFunds(
    _user: address,
    _walletConfig: address,
    _missionControl: address,
    _legoBook: address,
    _appraiser: address,
    _ledger: address,
) -> uint256:
    trialFundsAmount: uint256 = staticcall UserWalletConfig(_walletConfig).trialFundsAmount()
    trialFundsAsset: address = staticcall UserWalletConfig(_walletConfig).trialFundsAsset()
    if trialFundsAmount == 0 or trialFundsAsset == empty(address):
        return 0

    # if we already have enough, just remove what we have
    amountRecovered: uint256 = staticcall IERC20(trialFundsAsset).balanceOf(_user)
    if amountRecovered >= trialFundsAmount:
        return extcall UserWalletConfig(_walletConfig).removeTrialFunds()

    # add 1% buffer to ensure we recover enough
    targetRecoveryAmount: uint256 = trialFundsAmount * 101_00 // HUNDRED_PERCENT

    # find all vault tokens and withdraw from them
    numAssets: uint256 = staticcall UserWallet(_user).numAssets()
    if numAssets != 0:
        for i: uint256 in range(1, numAssets, bound=max_value(uint256)):
            if amountRecovered >= targetRecoveryAmount:
                break

            asset: address = staticcall UserWallet(_user).assets(i)
            if asset == empty(address):
                continue

            data: WalletAssetData = staticcall UserWallet(_user).assetData(asset)
            if not data.isYieldAsset or data.assetBalance == 0:
                continue

            # get underlying details
            config: AssetUsdValueConfig = self._getAssetUsdValueConfig(asset, _missionControl, _legoBook, _ledger)
            if config.underlyingAsset != trialFundsAsset:
                continue

            # get price per share for this vault token
            pricePerShare: uint256 = staticcall Appraiser(_appraiser).getPricePerShareWithConfig(asset, config.legoAddr, config.staleBlocks)
            if pricePerShare == 0:
                continue

            # calculate how many vault tokens we need to withdraw
            amountStillNeeded: uint256 = targetRecoveryAmount - amountRecovered
            vaultTokensNeeded: uint256 = amountStillNeeded * (10 ** config.decimals) // pricePerShare

            # withdraw vault tokens to get underlying
            underlyingAmount: uint256 = 0
            na: uint256 = 0
            underlyingAmount, na = extcall UserWalletConfig(_walletConfig).preparePayment(config.underlyingAsset, config.legoId, asset, vaultTokensNeeded)

            # update recovered amount
            amountRecovered += underlyingAmount

    # now remove trial funds
    return extcall UserWalletConfig(_walletConfig).removeTrialFunds()


# check if it remains


@view
@external
def doesWalletStillHaveTrialFunds(_user: address) -> bool:
    a: addys.Addys = addys._getAddys()
    walletConfig: address = staticcall UserWallet(_user).walletConfig()
    return self._doesWalletStillHaveTrialFunds(_user, walletConfig, a.missionControl, a.legoBook, a.appraiser, a.ledger)


@view
@external
def doesWalletStillHaveTrialFundsWithAddys(
    _user: address,
    _walletConfig: address,
    _missionControl: address,
    _legoBook: address,
    _appraiser: address,
    _ledger: address,
) -> bool:
    return self._doesWalletStillHaveTrialFunds(_user, _walletConfig, _missionControl, _legoBook, _appraiser, _ledger)


@view
@internal
def _doesWalletStillHaveTrialFunds(
    _user: address,
    _walletConfig: address,
    _missionControl: address,
    _legoBook: address,
    _appraiser: address,
    _ledger: address,
) -> bool:
    trialFundsAmount: uint256 = staticcall UserWalletConfig(_walletConfig).trialFundsAmount()
    trialFundsAsset: address = staticcall UserWalletConfig(_walletConfig).trialFundsAsset()
    if trialFundsAmount == 0 or trialFundsAsset == empty(address):
        return True

    amount: uint256 = staticcall IERC20(trialFundsAsset).balanceOf(_user)
    if amount >= trialFundsAmount:
        return True

    numAssets: uint256 = staticcall UserWallet(_user).numAssets()
    if numAssets == 0:
        return False

    for i: uint256 in range(1, numAssets, bound=max_value(uint256)):
        if amount >= trialFundsAmount:
            return True

        asset: address = staticcall UserWallet(_user).assets(i)
        if asset == empty(address):
            continue

        data: WalletAssetData = staticcall UserWallet(_user).assetData(asset)
        if not data.isYieldAsset:
            continue

        # get underlying details
        config: AssetUsdValueConfig = self._getAssetUsdValueConfig(asset, _missionControl, _legoBook, _ledger)
        if config.underlyingAsset != trialFundsAsset:
            continue

        # get current balance of vault token
        vaultBalance: uint256 = staticcall IERC20(asset).balanceOf(_user)
        if vaultBalance == 0:
            continue

        # get price per share for this vault token
        pricePerShare: uint256 = staticcall Appraiser(_appraiser).getPricePerShareWithConfig(asset, config.legoAddr, config.staleBlocks)
        if pricePerShare == 0:
            continue

        # calculate underlying amount
        amount += vaultBalance * pricePerShare // (10 ** config.decimals)

    return amount >= trialFundsAmount


# get asset usd value config


@view
@external
def getAssetUsdValueConfig(_asset: address) -> AssetUsdValueConfig:
    a: addys.Addys = addys._getAddys()
    return self._getAssetUsdValueConfig(_asset, a.missionControl, a.legoBook, a.ledger)


@view
@internal
def _getAssetUsdValueConfig(
    _asset: address,
    _missionControl: address,
    _legoBook: address,
    _ledger: address,
) -> AssetUsdValueConfig:
    config: AssetUsdValueConfig = staticcall MissionControl(_missionControl).getAssetUsdValueConfig(_asset)

    # if no specific config, fallback to vault token registration
    if config.decimals == 0:
        vaultToken: VaultToken = staticcall Ledger(_ledger).vaultTokens(_asset)
        if vaultToken.underlyingAsset != empty(address):
            config.legoId = vaultToken.legoId
            config.decimals = vaultToken.decimals
            config.isYieldAsset = True
            config.underlyingAsset = vaultToken.underlyingAsset

    # get lego addr if needed
    if config.legoId != 0 and config.legoAddr == empty(address):
        config.legoAddr = staticcall Registry(_legoBook).getAddr(config.legoId)

    # get decimals if needed
    if config.decimals == 0:
        config.decimals = self._getDecimals(_asset)

    return config


# get decimals


@view
@internal
def _getDecimals(_asset: address) -> uint256:
    if _asset in [WETH, ETH]:
        return 18
    return convert(staticcall IERC20Detailed(_asset).decimals(), uint256)