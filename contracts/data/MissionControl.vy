# @version 0.4.3

implements: Department

exports: addys.__interface__
exports: deptBasics.__interface__

initializes: addys
initializes: deptBasics[addys := addys]

import contracts.modules.Addys as addys
import contracts.modules.DeptBasics as deptBasics
from interfaces import Department

struct UserWalletConfig:
    walletTemplate: address
    configTemplate: address
    trialAsset: address
    trialAmount: uint256
    numUserWalletsAllowed: uint256
    enforceCreatorWhitelist: bool
    minKeyActionTimeLock: uint256
    maxKeyActionTimeLock: uint256
    defaultStaleBlocks: uint256
    depositRewardsAsset: address
    txFees: TxFees
    ambassadorRevShare: AmbassadorRevShare
    defaultYieldMaxIncrease: uint256
    defaultYieldPerformanceFee: uint256
    defaultYieldAmbassadorBonusRatio: uint256

struct AssetConfig:
    legoId: uint256
    isStablecoin: bool
    decimals: uint256
    staleBlocks: uint256
    txFees: TxFees
    ambassadorRevShare: AmbassadorRevShare
    yieldConfig: YieldConfig

struct TxFees:
    swapFee: uint256
    stableSwapFee: uint256
    rewardsFee: uint256

struct AmbassadorRevShare:
    swapRatio: uint256
    rewardsRatio: uint256
    yieldRatio: uint256

struct YieldConfig:
    isYieldAsset: bool
    isRebasing: bool
    underlyingAsset: address
    maxYieldIncrease: uint256
    performanceFee: uint256
    ambassadorBonusRatio: uint256

struct AgentConfig:
    agentTemplate: address
    numAgentsAllowed: uint256
    enforceCreatorWhitelist: bool

struct ManagerConfig:
    startingAgent: address
    startingAgentActivationLength: uint256
    managerPeriod: uint256
    managerActivationLength: uint256

struct PayeeConfig:
    payeePeriod: uint256
    payeeActivationLength: uint256

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
    ambassadorRevShare: AmbassadorRevShare
    ambassadorBonusRatio: uint256
    underlyingAsset: address
    decimals: uint256

# general wallet config
userWalletConfig: public(UserWalletConfig)
agentConfig: public(AgentConfig)
managerConfig: public(ManagerConfig)
payeeConfig: public(PayeeConfig)

# asset config
assetConfig: public(HashMap[address, AssetConfig])

# security / limits
creatorWhitelist: public(HashMap[address, bool]) # creator -> is whitelisted
canPerformSecurityAction: public(HashMap[address, bool]) # signer -> can perform security action
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


@external
def setManagerConfig(_config: ManagerConfig):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    self.managerConfig = _config


@external
def setPayeeConfig(_config: PayeeConfig):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    self.payeeConfig = _config


# helper


@view
@external
def getUserWalletCreationConfig(_creator: address) -> UserWalletCreationConfig:
    config: UserWalletConfig = self.userWalletConfig
    managerConfig: ManagerConfig = self.managerConfig
    payeeConfig: PayeeConfig = self.payeeConfig
    return UserWalletCreationConfig(
        numUserWalletsAllowed = config.numUserWalletsAllowed,
        isCreatorAllowed = self._isCreatorAllowed(config.enforceCreatorWhitelist, _creator),
        walletTemplate = config.walletTemplate,
        configTemplate = config.configTemplate,
        startingAgent = managerConfig.startingAgent,
        startingAgentActivationLength = managerConfig.startingAgentActivationLength,
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
    assetConfig: AssetConfig = self.assetConfig[_asset]

    ambassadorRevShare: AmbassadorRevShare = assetConfig.ambassadorRevShare
    ambassadorBonusRatio: uint256 = assetConfig.yieldConfig.ambassadorBonusRatio
    if assetConfig.decimals == 0:
        walletConfig: UserWalletConfig = self.userWalletConfig
        ambassadorRevShare = walletConfig.ambassadorRevShare
        ambassadorBonusRatio = walletConfig.defaultYieldAmbassadorBonusRatio

    return AmbassadorConfig(
        ambassador = _ambassador,
        ambassadorRevShare = ambassadorRevShare,
        ambassadorBonusRatio = ambassadorBonusRatio,
        underlyingAsset = assetConfig.yieldConfig.underlyingAsset,
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


########################
# Asset / Yield Config #
########################


@external
def setAssetConfig(_asset: address, _config: AssetConfig):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    self.assetConfig[_asset] = _config


# helpers


@view
@external
def getProfitCalcConfig(_asset: address) -> ProfitCalcConfig:
    assetConfig: AssetConfig = self.assetConfig[_asset]

    staleBlocks: uint256 = assetConfig.staleBlocks
    maxYieldIncrease: uint256 = assetConfig.yieldConfig.maxYieldIncrease
    performanceFee: uint256 = assetConfig.yieldConfig.performanceFee
    if assetConfig.decimals == 0:
        walletConfig: UserWalletConfig = self.userWalletConfig
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
    assetConfig: AssetConfig = self.assetConfig[_asset]

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
    inConfig: AssetConfig = self.assetConfig[_tokenIn]
    outConfig: AssetConfig = self.assetConfig[_tokenOut]

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
    config: AssetConfig = self.assetConfig[_asset]
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