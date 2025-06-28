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

interface Ledger:
    def createUserWallet(_user: address, _ambassador: address): nonpayable
    def isUserWallet(_user: address) -> bool: view
    def createAgent(_agent: address): nonpayable
    def numUserWallets() -> uint256: view
    def numAgents() -> uint256: view

interface MissionControl:
    def getUserWalletCreationConfig(_creator: address) -> UserWalletCreationConfig: view
    def getAgentCreationConfig(_creator: address) -> AgentCreationConfig: view

interface WalletConfig:
    def setWallet(_wallet: address) -> bool: nonpayable

struct UserWalletCreationConfig:
    numUserWalletsAllowed: uint256
    isCreatorAllowed: bool
    walletTemplate: address
    configTemplate: address
    startingAgent: address
    startingAgentActivationLength: uint256
    managerPeriod: uint256
    defaultStartDelay: uint256
    defaultActivationLength: uint256
    trialAsset: address
    trialAmount: uint256
    minManagerPeriod: uint256
    maxManagerPeriod: uint256
    minKeyActionTimeLock: uint256
    maxKeyActionTimeLock: uint256

struct AgentCreationConfig:
    agentTemplate: address
    numAgentsAllowed: uint256
    isCreatorAllowed: bool
    minTimeLock: uint256
    maxTimeLock: uint256

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
        config.startingAgent,
        config.startingAgentActivationLength,
        config.managerPeriod,
        config.defaultStartDelay,
        config.defaultActivationLength,
        trialFundsAsset,
        trialFundsAmount,
        config.minManagerPeriod,
        config.maxManagerPeriod,
        config.minKeyActionTimeLock,
        config.maxKeyActionTimeLock,
    )
    mainWalletAddr: address = create_from_blueprint(config.walletTemplate, a.hq, WETH, ETH, walletConfigAddr)
    assert extcall WalletConfig(walletConfigAddr).setWallet(mainWalletAddr) # dev: could not set wallet

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
