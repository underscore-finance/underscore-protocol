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
    _groupId: uint256 = 1,
) -> address:
    assert not deptBasics.isPaused # dev: contract paused
    a: addys.Addys = addys._getAddys()
    assert empty(address) not in [a.hq, a.ledger, a.missionControl, a.walletBackpack] # dev: invalid setup

    config: UserWalletCreationConfig = staticcall MissionControl(a.missionControl).getUserWalletCreationConfig(msg.sender)
    assert config.startingAgent != _owner # dev: starting agent cannot be the owner

    # validation
    if not addys._isSwitchboardAddr(msg.sender):
        assert config.isCreatorAllowed # dev: creator not allowed
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
    assert staticcall HighCommand(highCommand).isValidUserWalletManagerDefaults(config.managerPeriod, config.minKeyActionTimeLock, config.managerActivationLength, config.mustHaveUsdValueOnSwaps, config.maxNumSwapsPerPeriod, config.maxSlippageOnSwaps, config.startingAgent, config.startingAgentActivationLength, _owner) # dev: invalid setup
    assert staticcall Paymaster(paymaster).isValidUserWalletPayeeDefaults(config.payeePeriod, config.minKeyActionTimeLock, config.payeeActivationLength) # dev: invalid setup
    assert staticcall ChequeBook(chequeBook).isValidUserWalletChequeDefaults(config.chequeMaxNumActiveCheques, config.chequeInstantUsdThreshold, config.chequePeriodLength, config.chequeExpensiveDelayBlocks, config.chequeDefaultExpiryBlocks, config.minKeyActionTimeLock) # dev: invalid setup

    # default manager / payee / cheque settings
    globalManagerSettings: wcs.GlobalManagerSettings = staticcall HighCommand(highCommand).createDefaultGlobalManagerSettings(config.managerPeriod, config.minKeyActionTimeLock, config.managerActivationLength, config.mustHaveUsdValueOnSwaps, config.maxNumSwapsPerPeriod, config.maxSlippageOnSwaps, config.onlyApprovedYieldOpps)
    globalPayeeSettings: wcs.GlobalPayeeSettings = staticcall Paymaster(paymaster).createDefaultGlobalPayeeSettings(config.payeePeriod, config.minKeyActionTimeLock, config.payeeActivationLength)
    chequeSettings: wcs.ChequeSettings = staticcall ChequeBook(chequeBook).createDefaultChequeSettings(config.chequeMaxNumActiveCheques, config.chequeInstantUsdThreshold, config.chequePeriodLength, config.chequeExpensiveDelayBlocks, config.chequeDefaultExpiryBlocks)

    starterAgentSettings: wcs.ManagerSettings = empty(wcs.ManagerSettings)
    if config.startingAgent != empty(address):
        starterAgentSettings = staticcall HighCommand(highCommand).createStarterAgentSettings(config.startingAgentActivationLength)

    # create wallet contracts
    walletConfigAddr: address = create_from_blueprint(
        config.configTemplate,
        a.hq,
        _owner,
        _groupId,
        globalManagerSettings,
        globalPayeeSettings,
        chequeSettings,
        config.startingAgent,
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
        agent=config.startingAgent,
        ambassador=ambassador,
        creator=msg.sender,
        groupId=_groupId,
    )
    return mainWalletAddr


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
