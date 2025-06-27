# @version 0.4.3

implements: Department

exports: addys.__interface__
exports: deptBasics.__interface__

initializes: addys
initializes: deptBasics[addys := addys]

import contracts.modules.Addys as addys
import contracts.modules.DeptBasics as deptBasics
from interfaces import Department

struct AssetConfig:
    hasConfig: bool
    isYieldAsset: bool
    isRebasing: bool
    maxIncrease: uint256
    performanceFee: uint256
    decimals: uint256
    stalePriceNumBlocks: uint256

struct UserWalletConfig:
    walletTemplate: address
    configTemplate: address
    trialAsset: address
    trialAmount: uint256
    numUserWalletsAllowed: uint256
    enforceCreatorWhitelist: bool
    minKeyActionTimeLock: uint256
    maxKeyActionTimeLock: uint256

struct AgentConfig:
    agentTemplate: address
    numAgentsAllowed: uint256
    enforceCreatorWhitelist: bool

struct ManagerConfig:
    startingAgent: address
    startingAgentActivationLength: uint256
    managerPeriod: uint256
    defaultStartDelay: uint256
    defaultActivationLength: uint256
    minManagerPeriod: uint256
    maxManagerPeriod: uint256

# helpers

struct WalletAssetConfig:
    hasConfig: bool
    isYieldAsset: bool
    isRebasing: bool
    maxIncrease: uint256
    performanceFee: uint256
    decimals: uint256
    stalePriceNumBlocks: uint256

struct UserWalletCreationConfig:
    walletConfig: UserWalletConfig
    managerConfig: ManagerConfig
    isCreatorAllowed: bool

struct AgentCreationConfig:
    agentTemplate: address
    numAgentsAllowed: uint256
    isCreatorAllowed: bool
    minTimeLock: uint256
    maxTimeLock: uint256

# core configs
userWalletConfig: public(UserWalletConfig)
agentConfig: public(AgentConfig)
managerConfig: public(ManagerConfig)
assetConfig: public(HashMap[address, AssetConfig])

# other
feeRecipient: public(address)
creatorWhitelist: public(HashMap[address, bool]) # creator -> is whitelisted
canPerformSecurityAction: public(HashMap[address, bool]) # signer -> can perform security action

# locked
isLockedSigner: public(HashMap[address, bool]) # signer -> is locked


@deploy
def __init__(_undyHq: address):
    addys.__init__(_undyHq)
    deptBasics.__init__(False, False) # no minting


######################
# User Wallet Config #
######################


@external
def setUserWalletConfig(_config: UserWalletConfig):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    self.userWalletConfig = _config


@view
@external
def getUserWalletCreationConfig(_creator: address) -> UserWalletCreationConfig:
    config: UserWalletConfig = self.userWalletConfig
    return UserWalletCreationConfig(
        walletConfig = config,
        managerConfig = self.managerConfig,
        isCreatorAllowed = self._isCreatorAllowed(config.enforceCreatorWhitelist, _creator),
    )


##################
# Manager Config #
##################


@external
def setManagerConfig(_config: ManagerConfig):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    self.managerConfig = _config


################
# Agent Config #
################


@external
def setAgentConfig(_config: AgentConfig):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    self.agentConfig = _config


@view
@external
def getAgentCreationConfig(_creator: address) -> AgentCreationConfig:
    config: AgentConfig = self.agentConfig
    userConfig: UserWalletConfig = self.userWalletConfig
    return AgentCreationConfig(
        agentTemplate = config.agentTemplate,
        numAgentsAllowed = config.numAgentsAllowed,
        isCreatorAllowed = self._isCreatorAllowed(config.enforceCreatorWhitelist, _creator),
        minTimeLock = userConfig.minKeyActionTimeLock,
        maxTimeLock = userConfig.maxKeyActionTimeLock,
    )


################
# Asset Config #
################


@external
def setAssetConfig(_asset: address, _config: AssetConfig):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    self.assetConfig[_asset] = _config


# NOTE: creating different struct for user wallet in case main config struct diverges, updates, changes


@external
def getUserWalletAssetConfig(_asset: address) -> WalletAssetConfig:
    config: AssetConfig = self.assetConfig[_asset]
    return WalletAssetConfig(
        hasConfig = config.hasConfig,
        isYieldAsset = config.isYieldAsset,
        isRebasing = config.isRebasing,
        maxIncrease = config.maxIncrease,
        performanceFee = config.performanceFee,
        decimals = config.decimals,
        stalePriceNumBlocks = config.stalePriceNumBlocks,
    )


#########
# Other #
#########


# can perform security action


@external
def setCanPerformSecurityAction(_signer: address, _canPerform: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    self.canPerformSecurityAction[_signer] = _canPerform


# creator whitelist


@external
def setCreatorWhitelist(_creator: address, _isWhitelisted: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    self.creatorWhitelist[_creator] = _isWhitelisted


# locked signer


@external
def setLockedSigner(_signer: address, _isLocked: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    self.isLockedSigner[_signer] = _isLocked


# fee recipient


@external
def setFeeRecipient(_feeRecipient: address):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    self.feeRecipient = _feeRecipient


#########
# Utils #
#########


@view
@internal
def _isCreatorAllowed(_shouldEnforceWhitelist: bool, _creator: address) -> bool:
    if _shouldEnforceWhitelist:
        return self.creatorWhitelist[_creator]
    return True