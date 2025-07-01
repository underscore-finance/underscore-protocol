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
    feeRecipient: address
    walletFees: WalletFees
    defaultStaleBlocks: uint256

struct AssetConfig:
    legoId: uint256
    isStablecoin: bool
    decimals: uint256
    staleBlocks: uint256
    fees: WalletFees
    isYieldAsset: bool
    yieldConfig: YieldAssetConfig

struct YieldAssetConfig:
    isRebasing: bool
    underlyingAsset: address
    maxYieldIncrease: uint256
    yieldProfitFee: uint256

struct WalletFees:
    swapFee: uint256
    stableSwapFee: uint256
    rewardsFee: uint256

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

struct EjectModeFeeDetails:
    feeRecipient: address
    swapFee: uint256
    rewardsFee: uint256

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

struct SwapFeeConfig:
    tokenInIsStablecoin: bool
    tokenOutIsStablecoin: bool
    tokenOutIsConfigured: bool
    tokenOutSwapFee: uint256
    genStableSwapFee: uint256
    genSwapFee: uint256

struct RewardsFeeConfig:
    tokenIsConfigured: bool
    tokenRewardsFee: uint256
    genRewardsFee: uint256

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
    yieldProfitFee: uint256

# general wallet config
userWalletConfig: public(UserWalletConfig)
agentConfig: public(AgentConfig)
managerConfig: public(ManagerConfig)

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


@view
@external
def feeRecipient() -> address:
    return self.userWalletConfig.feeRecipient


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
    config: AssetConfig = self.assetConfig[_asset]

    staleBlocks: uint256 = config.staleBlocks
    if config.decimals == 0:
        staleBlocks = self.userWalletConfig.defaultStaleBlocks

    return ProfitCalcConfig(
        legoId = config.legoId,
        legoAddr = empty(address),
        decimals = config.decimals,
        staleBlocks = staleBlocks,
        isYieldAsset = config.isYieldAsset,
        isRebasing = config.yieldConfig.isRebasing,
        underlyingAsset = config.yieldConfig.underlyingAsset,
        maxYieldIncrease = config.yieldConfig.maxYieldIncrease,
        yieldProfitFee = config.yieldConfig.yieldProfitFee,
    )


@view
@external
def getAssetUsdValueConfig(_asset: address) -> AssetUsdValueConfig:
    config: AssetConfig = self.assetConfig[_asset]

    staleBlocks: uint256 = config.staleBlocks
    if config.decimals == 0:
        staleBlocks = self.userWalletConfig.defaultStaleBlocks

    return AssetUsdValueConfig(
        legoId = config.legoId,
        legoAddr = empty(address),
        decimals = config.decimals,
        staleBlocks = staleBlocks,
        isYieldAsset = config.isYieldAsset,
        underlyingAsset = config.yieldConfig.underlyingAsset,
    )


@view
@external
def getSwapFeeConfig(_tokenIn: address, _tokenOut: address) -> SwapFeeConfig:
    inConfig: AssetConfig = self.assetConfig[_tokenIn]
    outConfig: AssetConfig = self.assetConfig[_tokenOut]
    
    # only call userWalletConfig if we need to get the global swap fee data
    userWalletConfig: UserWalletConfig = empty(UserWalletConfig)
    if inConfig.isStablecoin and outConfig.isStablecoin or outConfig.decimals == 0:
        userWalletConfig = self.userWalletConfig

    return SwapFeeConfig(
        tokenInIsStablecoin = inConfig.isStablecoin,
        tokenOutIsStablecoin = outConfig.isStablecoin,
        tokenOutIsConfigured = outConfig.decimals != 0,
        tokenOutSwapFee = outConfig.fees.swapFee,
        genStableSwapFee = userWalletConfig.walletFees.stableSwapFee,
        genSwapFee = userWalletConfig.walletFees.swapFee,
    )


@view
@external
def getRewardsFeeConfig(_asset: address) -> RewardsFeeConfig:
    config: AssetConfig = self.assetConfig[_asset]
    return RewardsFeeConfig(
        tokenIsConfigured = config.decimals != 0,
        tokenRewardsFee = config.fees.rewardsFee,
        genRewardsFee = self.userWalletConfig.walletFees.rewardsFee,
    )


@view
@external
def getUnderlyingAssetAndDecimals(_asset: address) -> (address, uint256):
    assetConfig: AssetConfig = self.assetConfig[_asset]
    underlyingAsset: address = assetConfig.yieldConfig.underlyingAsset
    return (underlyingAsset, self.assetConfig[underlyingAsset].decimals)


@view
@external
def getEjectModeFeeDetails() -> EjectModeFeeDetails:
    config: UserWalletConfig = self.userWalletConfig
    return EjectModeFeeDetails(
        feeRecipient = config.feeRecipient,
        swapFee = config.walletFees.swapFee,
        rewardsFee = config.walletFees.rewardsFee,
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


#########
# Utils #
#########


@view
@internal
def _isCreatorAllowed(_shouldEnforceWhitelist: bool, _creator: address) -> bool:
    if _shouldEnforceWhitelist:
        return self.creatorWhitelist[_creator]
    return True