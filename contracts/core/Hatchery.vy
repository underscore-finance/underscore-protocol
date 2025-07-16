# @version 0.4.3

implements: Department

exports: addys.__interface__
exports: deptBasics.__interface__

initializes: addys
initializes: deptBasics[addys := addys]

import contracts.modules.Addys as addys
import contracts.modules.DeptBasics as deptBasics

from interfaces import Department
from interfaces import YieldLego as YieldLego
from interfaces import WalletConfigStructs as wcs

from ethereum.ercs import IERC20
from ethereum.ercs import IERC20Detailed

interface UserWalletConfig:
    def preparePayment(_targetAsset: address, _legoId: uint256, _vaultToken: address, _vaultAmount: uint256 = max_value(uint256)) -> (uint256, uint256): nonpayable
    def deregisterAsset(_asset: address) -> bool: nonpayable
    def setWallet(_wallet: address) -> bool: nonpayable
    def getTrialFundsInfo() -> (address, uint256): view
    def removeTrialFunds() -> uint256: nonpayable
    def owner() -> address: view

interface Ledger:
    def createUserWallet(_user: address, _ambassador: address): nonpayable
    def isRegisteredBackpackItem(_addr: address) -> bool: view
    def vaultTokens(_vaultToken: address) -> VaultToken: view
    def isUserWallet(_user: address) -> bool: view
    def createAgent(_agent: address): nonpayable
    def numUserWallets() -> uint256: view
    def numAgents() -> uint256: view

interface MissionControl:
    def getUserWalletCreationConfig(_creator: address) -> UserWalletCreationConfig: view
    def getAgentCreationConfig(_creator: address) -> AgentCreationConfig: view
    def getAssetUsdValueConfig(_asset: address) -> AssetUsdValueConfig: view
    def canPerformSecurityAction(_addr: address) -> bool: view

interface UserWallet:
    def assetData(asset: address) -> WalletAssetData: view
    def assets(i: uint256) -> address: view
    def walletConfig() -> address: view
    def numAssets() -> uint256: view

interface WalletBackpack:
    def highCommand() -> address: view
    def paymaster() -> address: view
    def migrator() -> address: view
    def sentinel() -> address: view

interface HighCommand:
    def createDefaultGlobalManagerSettings(_managerPeriod: uint256, _minTimeLock: uint256, _defaultActivationLength: uint256) -> wcs.GlobalManagerSettings: view
    def createStarterAgentSettings(_startingAgentActivationLength: uint256) -> wcs.ManagerSettings: view

interface Paymaster:
    def createDefaultGlobalPayeeSettings(_defaultPeriodLength: uint256, _startDelay: uint256, _activationLength: uint256) -> wcs.GlobalPayeeSettings: view

interface Appraiser:
    def getPricePerShareWithConfig(asset: address, legoAddr: address, staleBlocks: uint256, _decimals: uint256) -> uint256: view

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
    groupId: uint256

event AgentCreated:
    agent: indexed(address)
    owner: indexed(address)
    creator: indexed(address)
    groupId: uint256

HUNDRED_PERCENT: constant(uint256) = 100_00 # 100.00%
MAX_DEREGISTER_ASSETS: constant(uint256) = 25

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
    assert config.startingAgent != _owner # dev: starting agent cannot be the owner

    # validation
    if not addys._isSwitchboardAddr(msg.sender):
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

    # get wallet backpack addys
    sentinel: address = staticcall WalletBackpack(a.walletBackpack).sentinel()
    highCommand: address = staticcall WalletBackpack(a.walletBackpack).highCommand()
    paymaster: address = staticcall WalletBackpack(a.walletBackpack).paymaster()
    migrator: address = staticcall WalletBackpack(a.walletBackpack).migrator()

    # default manager / payee settings
    globalManagerSettings: wcs.GlobalManagerSettings = staticcall HighCommand(highCommand).createDefaultGlobalManagerSettings(config.managerPeriod, config.minKeyActionTimeLock, config.managerActivationLength)
    globalPayeeSettings: wcs.GlobalPayeeSettings = staticcall Paymaster(paymaster).createDefaultGlobalPayeeSettings(config.payeePeriod, config.minKeyActionTimeLock, config.payeeActivationLength)
    starterAgentSettings: wcs.ManagerSettings = empty(wcs.ManagerSettings)
    if config.startingAgent != empty(address):
        starterAgentSettings = staticcall HighCommand(highCommand).createStarterAgentSettings(config.startingAgentActivationLength)

    # create wallet contracts
    walletConfigAddr: address = create_from_blueprint(
        config.configTemplate,
        a.hq,
        _owner,
        _groupId,
        trialFundsAsset,
        trialFundsAmount,
        globalManagerSettings,
        globalPayeeSettings,
        config.startingAgent,
        starterAgentSettings,
        sentinel,
        highCommand,
        paymaster,
        migrator,
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
        groupId=_groupId,
    )
    return mainWalletAddr


################
# Create Agent #
################


@external
def createAgent(_owner: address = msg.sender, _groupId: uint256 = 1) -> address:
    assert not deptBasics.isPaused # dev: contract paused
    a: addys.Addys = addys._getAddys()

    # validation
    config: AgentCreationConfig = staticcall MissionControl(a.missionControl).getAgentCreationConfig(msg.sender)
    if not addys._isSwitchboardAddr(msg.sender):
        assert config.isCreatorAllowed # dev: creator not allowed
    assert empty(address) not in [config.agentTemplate, _owner] # dev: invalid setup
    if config.numAgentsAllowed != 0:
        assert staticcall Ledger(a.ledger).numAgents() < config.numAgentsAllowed # dev: max agents reached

    # create agent contract
    agentAddr: address = create_from_blueprint(config.agentTemplate, a.hq, _owner, _groupId, config.minTimeLock, config.maxTimeLock)

    # update ledger
    extcall Ledger(a.ledger).createAgent(agentAddr)

    log AgentCreated(
        agent=agentAddr,
        owner=_owner,
        creator=msg.sender,
        groupId=_groupId,
    )
    return agentAddr


###############
# Trial Funds #
###############


# clawback trial funds


@external
def clawBackTrialFunds(_user: address) -> uint256:
    assert not deptBasics.isPaused # dev: contract paused
    a: addys.Addys = addys._getAddys()
    assert staticcall Ledger(a.ledger).isUserWallet(_user) # dev: not a user wallet
    walletConfig: address = staticcall UserWallet(_user).walletConfig()
    assert self._canClawbackTrialFunds(msg.sender, walletConfig, a.missionControl, a.ledger) # dev: no perms
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
    trialFundsAsset: address = empty(address)
    trialFundsAmount: uint256 = 0
    trialFundsAsset, trialFundsAmount = staticcall UserWalletConfig(_walletConfig).getTrialFundsInfo()
    if trialFundsAmount == 0 or trialFundsAsset == empty(address):
        return 0

    # if we already have enough, just remove what we have
    amountRecovered: uint256 = staticcall IERC20(trialFundsAsset).balanceOf(_user)
    if amountRecovered >= trialFundsAmount:
        amountRemoved: uint256 = extcall UserWalletConfig(_walletConfig).removeTrialFunds()
        extcall UserWalletConfig(_walletConfig).deregisterAsset(trialFundsAsset)
        return amountRemoved

    # add 1% buffer to ensure we recover enough
    targetRecoveryAmount: uint256 = trialFundsAmount * 101_00 // HUNDRED_PERCENT
    assetsToDeregister: DynArray[address, MAX_DEREGISTER_ASSETS] = []

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
            if config.underlyingAsset != trialFundsAsset or config.legoId == 0:
                continue

            # get price per share for this vault token
            pricePerShare: uint256 = staticcall Appraiser(_appraiser).getPricePerShareWithConfig(asset, config.legoAddr, config.staleBlocks, config.decimals)
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

            # add to deregister list
            if len(assetsToDeregister) < MAX_DEREGISTER_ASSETS:
                assetsToDeregister.append(asset)

    # nothing to recover, roh roh roh
    if amountRecovered == 0 or staticcall IERC20(trialFundsAsset).balanceOf(_user) == 0:
        return 0

    # now remove trial funds
    amountRemoved: uint256 = extcall UserWalletConfig(_walletConfig).removeTrialFunds()

    # deregister assets -- this will only deregister if it truly has no balance left
    if len(assetsToDeregister) < MAX_DEREGISTER_ASSETS:
        assetsToDeregister.append(trialFundsAsset)
    for asset: address in assetsToDeregister:
        extcall UserWalletConfig(_walletConfig).deregisterAsset(asset)

    return amountRemoved


# access to clawback


@view
@external
def canClawbackTrialFunds(_user: address, _caller: address) -> bool:
    a: addys.Addys = addys._getAddys()
    walletConfig: address = staticcall UserWallet(_user).walletConfig()
    return self._canClawbackTrialFunds(_caller, walletConfig, a.missionControl, a.ledger)


@view
@internal
def _canClawbackTrialFunds(
    _caller: address,
    _walletConfig: address,
    _missionControl: address,
    _ledger: address,
) -> bool:
    if staticcall MissionControl(_missionControl).canPerformSecurityAction(_caller):
        return True

    if staticcall UserWalletConfig(_walletConfig).owner() == _caller:
        return True

    if addys._isSwitchboardAddr(_caller):
        return True

    return staticcall Ledger(_ledger).isRegisteredBackpackItem(_caller)


# view functions on trial funds


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
    trialFundsAsset: address = empty(address)
    trialFundsAmount: uint256 = 0
    trialFundsAsset, trialFundsAmount = staticcall UserWalletConfig(_walletConfig).getTrialFundsInfo()
    if trialFundsAmount == 0 or trialFundsAsset == empty(address):
        return True

    # allow minor buffer to account for rounding errors in lending protocols
    acceptableAmount: uint256 = trialFundsAmount * 99_00 // HUNDRED_PERCENT

    # check the wallet directly
    amount: uint256 = staticcall IERC20(trialFundsAsset).balanceOf(_user)
    if amount >= acceptableAmount:
        return True

    numAssets: uint256 = staticcall UserWallet(_user).numAssets()
    if numAssets == 0:
        return False

    for i: uint256 in range(1, numAssets, bound=max_value(uint256)):
        if amount >= acceptableAmount:
            return True

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

        # get current balance of vault token
        assetBalance: uint256 = staticcall IERC20(asset).balanceOf(_user)
        if assetBalance == 0:
            continue

        # need lego addr!
        if config.legoAddr == empty(address):
            continue

        # check if the asset can be used as trial funds
        if not staticcall YieldLego(config.legoAddr).isEligibleVaultForTrialFunds(asset, trialFundsAsset):
            continue

        # get price per share for this vault token
        pricePerShare: uint256 = staticcall Appraiser(_appraiser).getPricePerShareWithConfig(asset, config.legoAddr, config.staleBlocks, config.decimals)
        if pricePerShare == 0:
            continue

        # calculate underlying amount
        amount += assetBalance * pricePerShare // (10 ** config.decimals)

    return amount >= acceptableAmount


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
