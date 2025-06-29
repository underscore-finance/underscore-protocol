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
    isStablecoin: bool
    isYieldAsset: bool
    decimals: uint256
    stalePriceNumBlocks: uint256
    fees: WalletFees

struct YieldAssetConfig:
    legoId: uint256
    isRebasing: bool
    underlyingAsset: address
    maxYieldIncrease: uint256
    yieldProfitFee: uint256

struct UserWalletConfig:
    walletTemplate: address
    configTemplate: address
    trialAsset: address
    trialAmount: uint256
    numUserWalletsAllowed: uint256
    enforceCreatorWhitelist: bool
    minKeyActionTimeLock: uint256
    maxKeyActionTimeLock: uint256

struct WalletFees:
    swapFee: uint256
    stableSwapFee: uint256
    rewardsFee: uint256

struct DefaultYieldConfig:
    maxYieldIncrease: uint256
    yieldProfitFee: uint256

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

# general wallet config
userWalletConfig: public(UserWalletConfig)
agentConfig: public(AgentConfig)
managerConfig: public(ManagerConfig)

# default fees
walletFees: public(WalletFees)
defaultYieldConfig: public(DefaultYieldConfig)

# asset config
assetConfig: public(HashMap[address, AssetConfig])
yieldAssetConfig: public(HashMap[address, YieldAssetConfig])

# security / limits
creatorWhitelist: public(HashMap[address, bool]) # creator -> is whitelisted
canPerformSecurityAction: public(HashMap[address, bool]) # signer -> can perform security action
isLockedSigner: public(HashMap[address, bool]) # signer -> is locked

# other
feeRecipient: public(address)


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


@external
def setManagerConfig(_config: ManagerConfig):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    self.managerConfig = _config


@external
def setWalletFees(_fees: WalletFees):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    self.walletFees = _fees


@external
def setDefaultYieldConfig(_config: DefaultYieldConfig):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    self.defaultYieldConfig = _config


# helper


@view
@external
def getUserWalletCreationConfig(_creator: address) -> UserWalletCreationConfig:
    config: UserWalletConfig = self.userWalletConfig
    managerConfig: ManagerConfig = self.managerConfig
    return UserWalletCreationConfig(
        numUserWalletsAllowed = config.numUserWalletsAllowed,
        isCreatorAllowed = self._isCreatorAllowed(config.enforceCreatorWhitelist, _creator),
        walletTemplate = config.walletTemplate,
        configTemplate = config.configTemplate,
        startingAgent = managerConfig.startingAgent,
        startingAgentActivationLength = managerConfig.startingAgentActivationLength,
        managerPeriod = managerConfig.managerPeriod,
        defaultStartDelay = managerConfig.defaultStartDelay,
        defaultActivationLength = managerConfig.defaultActivationLength,
        trialAsset = config.trialAsset,
        trialAmount = config.trialAmount,
        minManagerPeriod = managerConfig.minManagerPeriod,
        maxManagerPeriod = managerConfig.maxManagerPeriod,
        minKeyActionTimeLock = config.minKeyActionTimeLock,
        maxKeyActionTimeLock = config.maxKeyActionTimeLock,
    )


################
# Agent Config #
################


@external
def setAgentConfig(_config: AgentConfig):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    self.agentConfig = _config


# helper


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


@external
def setYieldAssetConfig(_asset: address, _config: YieldAssetConfig):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    self.yieldAssetConfig[_asset] = _config


# helpers


@view
@external
def getSwapFee(_user: address, _tokenIn: address, _tokenOut: address) -> uint256:
    inConfig: AssetConfig = self.assetConfig[_tokenIn]
    outConfig: AssetConfig = self.assetConfig[_tokenOut]

    # stable swap fee
    if inConfig.isStablecoin and outConfig.isStablecoin:
        return self.walletFees.stableSwapFee

    # asset swap fee takes precedence over global swap fee
    if outConfig.decimals != 0:
        return outConfig.fees.swapFee

    return self.walletFees.swapFee


@view
@external
def getRewardsFee(_user: address, _asset: address) -> uint256:
    config: AssetConfig = self.assetConfig[_asset]
    if config.decimals != 0:
        return config.fees.rewardsFee
    return self.walletFees.rewardsFee


@view
@external
def isYieldAssetAndGetDecimals(_asset: address) -> (bool, uint256):
    config: AssetConfig = self.assetConfig[_asset]
    return config.isYieldAsset, config.decimals


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