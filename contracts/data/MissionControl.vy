# @version 0.4.3

implements: Department

exports: addys.__interface__
exports: deptBasics.__interface__

initializes: addys
initializes: deptBasics[addys := addys]

import contracts.modules.Addys as addys
import contracts.modules.DeptBasics as deptBasics

from interfaces import Department
import interfaces.ConfigStructs as cs
from interfaces import Defaults

# helpers

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

struct ProfitCalcConfig:
    legoId: uint256
    legoAddr: address
    decimals: uint256
    staleBlocks: uint256
    isYieldAsset: bool
    isRebasing: bool
    underlyingAsset: address
    maxYieldIncrease: uint256
    performanceFee: uint256

struct AmbassadorConfig:
    ambassador: address
    ambassadorRevShare: cs.AmbassadorRevShare
    ambassadorBonusRatio: uint256
    bonusRatio: uint256
    altBonusAsset: address
    underlyingAsset: address
    isRebasing: bool
    decimals: uint256

# global configs
userWalletConfig: public(cs.UserWalletConfig)
agentConfig: public(cs.AgentConfig)
managerConfig: public(cs.ManagerConfig)
payeeConfig: public(cs.PayeeConfig)

# asset config
assetConfig: public(HashMap[address, cs.AssetConfig])

# security / limits
creatorWhitelist: public(HashMap[address, bool]) # creator -> is whitelisted
canPerformSecurityAction: public(HashMap[address, bool]) # signer -> can perform security action
isLockedSigner: public(HashMap[address, bool]) # signer -> is locked


@deploy
def __init__(_undyHq: address, _defaults: address):
    addys.__init__(_undyHq)
    deptBasics.__init__(False, False) # no minting

    if _defaults != empty(address):
        self.userWalletConfig = staticcall Defaults(_defaults).userWalletConfig()
        self.agentConfig = staticcall Defaults(_defaults).agentConfig()
        self.managerConfig = staticcall Defaults(_defaults).managerConfig()
        self.payeeConfig = staticcall Defaults(_defaults).payeeConfig()


######################
# User Wallet Config #
######################


@external
def setUserWalletConfig(_config: cs.UserWalletConfig):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    self.userWalletConfig = _config


@external
def setManagerConfig(_config: cs.ManagerConfig):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    self.managerConfig = _config


@external
def setPayeeConfig(_config: cs.PayeeConfig):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    self.payeeConfig = _config


# helper


@view
@external
def getUserWalletCreationConfig(_creator: address) -> UserWalletCreationConfig:
    config: cs.UserWalletConfig = self.userWalletConfig
    managerConfig: cs.ManagerConfig = self.managerConfig
    payeeConfig: cs.PayeeConfig = self.payeeConfig
    agentConfig: cs.AgentConfig = self.agentConfig
    return UserWalletCreationConfig(
        numUserWalletsAllowed = config.numUserWalletsAllowed,
        isCreatorAllowed = self._isCreatorAllowed(config.enforceCreatorWhitelist, _creator),
        walletTemplate = config.walletTemplate,
        configTemplate = config.configTemplate,
        startingAgent = agentConfig.startingAgent,
        startingAgentActivationLength = agentConfig.startingAgentActivationLength,
        managerPeriod = managerConfig.managerPeriod,
        managerActivationLength = managerConfig.managerActivationLength,
        payeePeriod = payeeConfig.payeePeriod,
        payeeActivationLength = payeeConfig.payeeActivationLength,
        trialAsset = config.trialAsset,
        trialAmount = config.trialAmount,
        minKeyActionTimeLock = config.minKeyActionTimeLock,
        maxKeyActionTimeLock = config.maxKeyActionTimeLock,
    )


@view
@external
def getAmbassadorConfig(_ambassador: address, _asset: address) -> AmbassadorConfig:
    assetConfig: cs.AssetConfig = self.assetConfig[_asset]

    ambassadorRevShare: cs.AmbassadorRevShare = assetConfig.ambassadorRevShare
    ambassadorBonusRatio: uint256 = assetConfig.yieldConfig.ambassadorBonusRatio
    bonusRatio: uint256 = assetConfig.yieldConfig.bonusRatio
    altBonusAsset: address = assetConfig.yieldConfig.altBonusAsset
    if assetConfig.decimals == 0:
        walletConfig: cs.UserWalletConfig = self.userWalletConfig
        ambassadorRevShare = walletConfig.ambassadorRevShare
        ambassadorBonusRatio = walletConfig.defaultYieldAmbassadorBonusRatio
        bonusRatio = walletConfig.defaultYieldBonusRatio
        altBonusAsset = walletConfig.defaultYieldAltBonusAsset

    return AmbassadorConfig(
        ambassador = _ambassador,
        ambassadorRevShare = ambassadorRevShare,
        ambassadorBonusRatio = ambassadorBonusRatio,
        bonusRatio = bonusRatio,
        altBonusAsset = altBonusAsset,
        underlyingAsset = assetConfig.yieldConfig.underlyingAsset,
        isRebasing = assetConfig.yieldConfig.isRebasing,
        decimals = assetConfig.decimals,
    )


@view
@external
def getDepositRewardsAsset() -> address:
    return self.userWalletConfig.depositRewardsAsset


################
# Agent Config #
################


@external
def setAgentConfig(_config: cs.AgentConfig):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    self.agentConfig = _config


# helper


@view
@external
def getAgentCreationConfig(_creator: address) -> AgentCreationConfig:
    config: cs.AgentConfig = self.agentConfig
    userConfig: cs.UserWalletConfig = self.userWalletConfig
    return AgentCreationConfig(
        agentTemplate = config.agentTemplate,
        numAgentsAllowed = config.numAgentsAllowed,
        isCreatorAllowed = self._isCreatorAllowed(config.enforceCreatorWhitelist, _creator),
        minTimeLock = userConfig.minKeyActionTimeLock,
        maxTimeLock = userConfig.maxKeyActionTimeLock,
    )


########################
# Asset / Yield Config #
########################


@external
def setAssetConfig(_asset: address, _config: cs.AssetConfig):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    self.assetConfig[_asset] = _config


# helpers


@view
@external
def getProfitCalcConfig(_asset: address) -> ProfitCalcConfig:
    assetConfig: cs.AssetConfig = self.assetConfig[_asset]

    staleBlocks: uint256 = assetConfig.staleBlocks
    maxYieldIncrease: uint256 = assetConfig.yieldConfig.maxYieldIncrease
    performanceFee: uint256 = assetConfig.yieldConfig.performanceFee
    if assetConfig.decimals == 0:
        walletConfig: cs.UserWalletConfig = self.userWalletConfig
        staleBlocks = walletConfig.defaultStaleBlocks
        maxYieldIncrease = walletConfig.defaultYieldMaxIncrease
        performanceFee = walletConfig.defaultYieldPerformanceFee

    return ProfitCalcConfig(
        legoId = assetConfig.legoId,
        legoAddr = empty(address),
        decimals = assetConfig.decimals,
        staleBlocks = staleBlocks,
        isYieldAsset = assetConfig.yieldConfig.isYieldAsset,
        isRebasing = assetConfig.yieldConfig.isRebasing,
        underlyingAsset = assetConfig.yieldConfig.underlyingAsset,
        maxYieldIncrease = maxYieldIncrease,
        performanceFee = performanceFee,
    )


@view
@external
def getAssetUsdValueConfig(_asset: address) -> AssetUsdValueConfig:
    assetConfig: cs.AssetConfig = self.assetConfig[_asset]

    staleBlocks: uint256 = assetConfig.staleBlocks
    if assetConfig.decimals == 0:
        staleBlocks = self.userWalletConfig.defaultStaleBlocks

    return AssetUsdValueConfig(
        legoId = assetConfig.legoId,
        legoAddr = empty(address),
        decimals = assetConfig.decimals,
        staleBlocks = staleBlocks,
        isYieldAsset = assetConfig.yieldConfig.isYieldAsset,
        underlyingAsset = assetConfig.yieldConfig.underlyingAsset,
    )


@view
@external
def getSwapFee(_user: address, _tokenIn: address, _tokenOut: address) -> uint256:
    # NOTE: passing in `_user` in case we ever have different fees for different users in future
    inConfig: cs.AssetConfig = self.assetConfig[_tokenIn]
    outConfig: cs.AssetConfig = self.assetConfig[_tokenOut]

    # stable swap fee
    if inConfig.isStablecoin and outConfig.isStablecoin:
        return self.userWalletConfig.txFees.stableSwapFee

    # asset swap fee takes precedence over global swap fee
    if outConfig.decimals != 0:
        return outConfig.txFees.swapFee

    return self.userWalletConfig.txFees.swapFee


@view
@external
def getRewardsFee(_user: address, _asset: address) -> uint256:
    # NOTE: passing in `_user` in case we ever have different fees for different users in future
    config: cs.AssetConfig = self.assetConfig[_asset]
    if config.decimals != 0:
        return config.txFees.rewardsFee
    return self.userWalletConfig.txFees.rewardsFee


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


#########
# Utils #
#########


@view
@internal
def _isCreatorAllowed(_shouldEnforceWhitelist: bool, _creator: address) -> bool:
    if _shouldEnforceWhitelist:
        return self.creatorWhitelist[_creator]
    return True