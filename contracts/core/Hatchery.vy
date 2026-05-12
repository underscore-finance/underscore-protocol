#          ___           ___                       ___           ___           ___           ___                 
#         /__/\         /  /\          ___        /  /\         /__/\         /  /\         /  /\          ___   
#         \  \:\       /  /::\        /  /\      /  /:/         \  \:\       /  /:/_       /  /::\        /__/|  
#          \__\:\     /  /:/\:\      /  /:/     /  /:/           \__\:\     /  /:/ /\     /  /:/\:\      |  |:|  
#      ___ /  /::\   /  /:/~/::\    /  /:/     /  /:/  ___   ___ /  /::\   /  /:/ /:/_   /  /:/~/:/      |  |:|  
#     /__/\  /:/\:\ /__/:/ /:/\:\  /  /::\    /__/:/  /  /\ /__/\  /:/\:\ /__/:/ /:/ /\ /__/:/ /:/___  __|__|:|  
#     \  \:\/:/__\/ \  \:\/:/__\/ /__/:/\:\   \  \:\ /  /:/ \  \:\/:/__\/ \  \:\/:/ /:/ \  \:\/:::::/ /__/::::\  
#      \  \::/       \  \::/      \__\/  \:\   \  \:\  /:/   \  \::/       \  \::/ /:/   \  \::/~~~~     ~\~~\:\ 
#       \  \:\        \  \:\           \  \:\   \  \:\/:/     \  \:\        \  \:\/:/     \  \:\           \  \:\
#        \  \:\        \  \:\           \__\/    \  \::/       \  \:\        \  \::/       \  \:\           \__\/
#         \__\/         \__\/                     \__\/         \__\/         \__\/         \__\/                
#
#     ╔════════════════════════════════════════════════════╗
#     ║  ** Hatchery **                                    ║
#     ║  Handles user wallet creation.                     ║
#     ╚════════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

implements: Department

exports: addys.__interface__
exports: deptBasics.__interface__

initializes: addys
initializes: deptBasics[addys := addys]

import contracts.modules.Addys as addys
import contracts.modules.DeptBasics as deptBasics

from interfaces import Department
from interfaces import WalletConfigStructs as wcs
import interfaces.ConfigStructs as cs

interface WalletBackpack:
    def highCommand() -> address: view
    def chequeBook() -> address: view
    def paymaster() -> address: view
    def migrator() -> address: view
    def sentinel() -> address: view
    def kernel() -> address: view

interface Ledger:
    def createUserWallet(_user: address, _ambassador: address): nonpayable
    def isUserWallet(_user: address) -> bool: view
    def numUserWallets() -> uint256: view

interface MissionControl:
    def getUserWalletCreationConfig(_creator: address) -> UserWalletCreationConfig: view
    def creatorWhitelist(_creator: address) -> bool: view

interface HighCommand:
    def isValidUserWalletManagerDefaults(_managerPeriod: uint256, _timeLock: uint256, _managerActivationLength: uint256, _mustHaveUsdValueOnSwaps: bool, _maxNumSwapsPerPeriod: uint256, _maxSlippageOnSwaps: uint256, _startingAgent: address, _startingAgentActivationLength: uint256, _owner: address) -> bool: view
    def createDefaultGlobalManagerSettings(_managerPeriod: uint256, _minTimeLock: uint256, _defaultActivationLength: uint256, _mustHaveUsdValueOnSwaps: bool, _maxNumSwapsPerPeriod: uint256, _maxSlippageOnSwaps: uint256, _onlyApprovedYieldOpps: bool) -> wcs.GlobalManagerSettings: view
    def createStarterAgentSettings(_startingAgentActivationLength: uint256) -> wcs.ManagerSettings: view

interface ChequeBook:
    def isValidUserWalletChequeDefaults(_maxNumActiveCheques: uint256, _instantUsdThreshold: uint256, _periodLength: uint256, _expensiveDelayBlocks: uint256, _defaultExpiryBlocks: uint256, _timeLock: uint256) -> bool: view
    def createDefaultChequeSettings(_maxNumActiveCheques: uint256, _instantUsdThreshold: uint256, _periodLength: uint256, _expensiveDelayBlocks: uint256, _defaultExpiryBlocks: uint256) -> wcs.ChequeSettings: view

interface Paymaster:
    def isValidUserWalletPayeeDefaults(_defaultPeriodLength: uint256, _startDelay: uint256, _activationLength: uint256) -> bool: view
    def createDefaultGlobalPayeeSettings(_defaultPeriodLength: uint256, _startDelay: uint256, _activationLength: uint256) -> wcs.GlobalPayeeSettings: view

interface UserWalletConfig:
    def setWallet(_wallet: address) -> bool: nonpayable

struct UserWalletCreationConfig:
    numUserWalletsAllowed: uint256
    isCreatorAllowed: bool
    walletTemplate: address
    configTemplate: address
    startingAgent: address
    startingAgentActivationLength: uint256
    managerPeriod: uint256
    managerActivationLength: uint256
    mustHaveUsdValueOnSwaps: bool
    maxNumSwapsPerPeriod: uint256
    maxSlippageOnSwaps: uint256
    onlyApprovedYieldOpps: bool
    payeePeriod: uint256
    payeeActivationLength: uint256
    chequeMaxNumActiveCheques: uint256
    chequeInstantUsdThreshold: uint256
    chequePeriodLength: uint256
    chequeExpensiveDelayBlocks: uint256
    chequeDefaultExpiryBlocks: uint256
    minKeyActionTimeLock: uint256
    maxKeyActionTimeLock: uint256

event UserWalletCreated:
    mainAddr: indexed(address)
    configAddr: indexed(address)
    owner: indexed(address)
    agent: address
    ambassador: address
    creator: address
    groupId: uint256

event StarterAgentConfigSet:
    starterAgentType: cs.StarterAgentType
    startingAgent: indexed(address)
    startingAgentActivationLength: uint256

event NonProdCreatorSet:
    nonProdCreator: indexed(address)

WETH: public(immutable(address))
ETH: public(immutable(address))

stagingStarterAgentConfig: public(cs.AgentConfig)
devStarterAgentConfig: public(cs.AgentConfig)
nonProdCreator: public(address)


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
    _groupId: uint256 = 1,
    _starterAgentType: uint256 = 1,
) -> address:
    assert not deptBasics.isPaused # dev: contract paused
    a: addys.Addys = addys._getAddys()
    assert empty(address) not in [a.hq, a.ledger, a.missionControl, a.walletBackpack] # dev: invalid setup

    config: UserWalletCreationConfig = staticcall MissionControl(a.missionControl).getUserWalletCreationConfig(msg.sender)
    starterAgentType: cs.StarterAgentType = convert(_starterAgentType, cs.StarterAgentType)

    # validation
    assert empty(address) not in [config.walletTemplate, config.configTemplate, _owner] # dev: invalid setup
    assert config.minKeyActionTimeLock != 0 and config.minKeyActionTimeLock < config.maxKeyActionTimeLock # dev: invalid setup
    if config.numUserWalletsAllowed != 0:
        assert staticcall Ledger(a.ledger).numUserWallets() < config.numUserWalletsAllowed # dev: max user wallets reached

    # ambassador
    ambassador: address = empty(address)
    if _ambassador != empty(address) and staticcall Ledger(a.ledger).isUserWallet(_ambassador) and staticcall MissionControl(a.missionControl).creatorWhitelist(msg.sender):
        ambassador = _ambassador

    # get wallet backpack addys
    kernel: address = staticcall WalletBackpack(a.walletBackpack).kernel()
    sentinel: address = staticcall WalletBackpack(a.walletBackpack).sentinel()
    highCommand: address = staticcall WalletBackpack(a.walletBackpack).highCommand()
    paymaster: address = staticcall WalletBackpack(a.walletBackpack).paymaster()
    chequeBook: address = staticcall WalletBackpack(a.walletBackpack).chequeBook()
    migrator: address = staticcall WalletBackpack(a.walletBackpack).migrator()
    assert empty(address) not in [kernel, sentinel, highCommand, paymaster, chequeBook, migrator, WETH, ETH] # dev: invalid setup
    assert WETH.is_contract # dev: invalid setup

    assert self._isValidStarterAgentType(starterAgentType) # dev: invalid starter agent type
    isProdStarterAgentType: bool = starterAgentType == cs.StarterAgentType.PROD
    if isProdStarterAgentType:
        assert msg.sender != self.nonProdCreator # dev: non-prod creator cannot create prod
    else:
        assert msg.sender == self.nonProdCreator # dev: no perms
        assert not staticcall MissionControl(a.missionControl).creatorWhitelist(msg.sender) # dev: non-prod creator is whitelisted
    if isProdStarterAgentType and not addys._isSwitchboardAddr(msg.sender):
        assert config.isCreatorAllowed # dev: creator not allowed

    starterConfig: cs.AgentConfig = self._resolveStarterAgentConfig(config, starterAgentType)
    assert starterConfig.startingAgent != _owner # dev: starting agent cannot be the owner
    assert staticcall HighCommand(highCommand).isValidUserWalletManagerDefaults(config.managerPeriod, config.minKeyActionTimeLock, config.managerActivationLength, config.mustHaveUsdValueOnSwaps, config.maxNumSwapsPerPeriod, config.maxSlippageOnSwaps, starterConfig.startingAgent, starterConfig.startingAgentActivationLength, _owner) # dev: invalid setup
    assert staticcall Paymaster(paymaster).isValidUserWalletPayeeDefaults(config.payeePeriod, config.minKeyActionTimeLock, config.payeeActivationLength) # dev: invalid setup
    assert staticcall ChequeBook(chequeBook).isValidUserWalletChequeDefaults(config.chequeMaxNumActiveCheques, config.chequeInstantUsdThreshold, config.chequePeriodLength, config.chequeExpensiveDelayBlocks, config.chequeDefaultExpiryBlocks, config.minKeyActionTimeLock) # dev: invalid setup

    # default manager / payee / cheque settings
    globalManagerSettings: wcs.GlobalManagerSettings = staticcall HighCommand(highCommand).createDefaultGlobalManagerSettings(config.managerPeriod, config.minKeyActionTimeLock, config.managerActivationLength, config.mustHaveUsdValueOnSwaps, config.maxNumSwapsPerPeriod, config.maxSlippageOnSwaps, config.onlyApprovedYieldOpps)
    globalPayeeSettings: wcs.GlobalPayeeSettings = staticcall Paymaster(paymaster).createDefaultGlobalPayeeSettings(config.payeePeriod, config.minKeyActionTimeLock, config.payeeActivationLength)
    chequeSettings: wcs.ChequeSettings = staticcall ChequeBook(chequeBook).createDefaultChequeSettings(config.chequeMaxNumActiveCheques, config.chequeInstantUsdThreshold, config.chequePeriodLength, config.chequeExpensiveDelayBlocks, config.chequeDefaultExpiryBlocks)

    starterAgentSettings: wcs.ManagerSettings = empty(wcs.ManagerSettings)
    if starterConfig.startingAgent != empty(address):
        starterAgentSettings = staticcall HighCommand(highCommand).createStarterAgentSettings(starterConfig.startingAgentActivationLength)

    # create wallet contracts
    walletConfigAddr: address = create_from_blueprint(
        config.configTemplate,
        a.hq,
        _owner,
        _groupId,
        globalManagerSettings,
        globalPayeeSettings,
        chequeSettings,
        starterConfig.startingAgent,
        starterAgentSettings,
        kernel,
        sentinel,
        highCommand,
        paymaster,
        chequeBook,
        migrator,
        WETH,
        ETH,
        config.minKeyActionTimeLock,
        config.maxKeyActionTimeLock,
    )
    assert walletConfigAddr != empty(address) # dev: invalid setup
    mainWalletAddr: address = create_from_blueprint(config.walletTemplate, WETH, ETH, walletConfigAddr)
    assert extcall UserWalletConfig(walletConfigAddr).setWallet(mainWalletAddr) # dev: could not set wallet

    # update ledger
    extcall Ledger(a.ledger).createUserWallet(mainWalletAddr, ambassador)

    log UserWalletCreated(
        mainAddr=mainWalletAddr,
        configAddr=walletConfigAddr,
        owner=_owner,
        agent=starterConfig.startingAgent,
        ambassador=ambassador,
        creator=msg.sender,
        groupId=_groupId,
    )
    return mainWalletAddr


@view
@internal
def _resolveStarterAgentConfig(
    _config: UserWalletCreationConfig,
    _starterAgentType: cs.StarterAgentType,
) -> cs.AgentConfig:
    assert self._isValidStarterAgentType(_starterAgentType) # dev: invalid starter agent type

    starterConfig: cs.AgentConfig = empty(cs.AgentConfig)
    if _starterAgentType == cs.StarterAgentType.PROD:
        starterConfig = cs.AgentConfig(
            startingAgent=_config.startingAgent,
            startingAgentActivationLength=_config.startingAgentActivationLength,
        )
    elif _starterAgentType == cs.StarterAgentType.STAGING:
        starterConfig = self.stagingStarterAgentConfig
    else:
        starterConfig = self.devStarterAgentConfig

    if _starterAgentType != cs.StarterAgentType.PROD:
        assert starterConfig.startingAgent != empty(address) # dev: starter agent not set

    return starterConfig


#########################
# Starter Agent Configs #
#########################


@external
def setStarterAgentConfig(
    _starterAgentType: cs.StarterAgentType,
    _startingAgent: address,
    _startingAgentActivationLength: uint256,
):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert not deptBasics.isPaused # dev: not activated
    # Any registered Switchboard may call this intentionally; today only Alpha exposes a wrapper.
    assert self._isValidStarterAgentType(_starterAgentType) # dev: invalid starter agent type
    assert _starterAgentType != cs.StarterAgentType.PROD # dev: prod owned by mission control
    assert self._areValidStarterAgentParams(_startingAgent, _startingAgentActivationLength) # dev: invalid starter agent params

    config: cs.AgentConfig = cs.AgentConfig(
        startingAgent=_startingAgent,
        startingAgentActivationLength=_startingAgentActivationLength,
    )
    if _starterAgentType == cs.StarterAgentType.STAGING:
        self.stagingStarterAgentConfig = config
    else:
        self.devStarterAgentConfig = config

    log StarterAgentConfigSet(
        starterAgentType=_starterAgentType,
        startingAgent=_startingAgent,
        startingAgentActivationLength=_startingAgentActivationLength,
    )


@external
def setNonProdCreator(_nonProdCreator: address):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert not deptBasics.isPaused # dev: not activated
    # Any registered Switchboard may call this intentionally; today only Alpha exposes a wrapper.
    if _nonProdCreator != empty(address):
        missionControl: address = addys._getMissionControlAddr()
        assert missionControl != empty(address) # dev: invalid setup
        assert not staticcall MissionControl(missionControl).creatorWhitelist(_nonProdCreator) # dev: non-prod creator is whitelisted

    self.nonProdCreator = _nonProdCreator
    log NonProdCreatorSet(nonProdCreator=_nonProdCreator)


@view
@internal
def _isValidStarterAgentType(_starterAgentType: cs.StarterAgentType) -> bool:
    return (
        _starterAgentType == cs.StarterAgentType.PROD or
        _starterAgentType == cs.StarterAgentType.STAGING or
        _starterAgentType == cs.StarterAgentType.DEV
    )


@view
@internal
def _areValidStarterAgentParams(_agent: address, _activationLength: uint256) -> bool:
    if _agent != empty(address) and _activationLength == 0:
        return False
    if _agent == empty(address) and _activationLength != 0:
        return False
    if _activationLength == max_value(uint256):
        return False
    return True


# trial funds (legacy wallets)


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
    # backwards compatibility (legacy wallets)
    return True
