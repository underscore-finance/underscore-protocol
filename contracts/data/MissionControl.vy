#     _     _  __  __  _  ___  _         __   ___  _   ________  ___  _    
#    | |\/|| |( (`( (`| |/ / \| |\ |    / /` / / \| |\ || || |_)/ / \| |   
#    |_|  ||_|_)_)_)_)|_|\_\_/|_| \|    \_\_,\_\_/|_| \||_||_| \\_\_/|_|__ 
#
#     ╔════════════════════════════════════════════════════╗
#     ║  ** Mission Control **                             ║
#     ║  Stores all configuration data for Underscore      ║
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
import interfaces.ConfigStructs as cs
from interfaces import Defaults

interface Ledger:
    def vaultTokens(_vaultToken: address) -> VaultToken: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

struct VaultToken:
    legoId: uint256
    underlyingAsset: address
    decimals: uint256
    isRebasing: bool

struct AssetUsdValueConfig:
    legoId: uint256
    legoAddr: address
    isYieldAsset: bool
    underlyingAsset: address

struct ProfitCalcConfig:
    legoId: uint256
    legoAddr: address
    isYieldAsset: bool
    underlyingAsset: address
    maxYieldIncrease: uint256
    performanceFee: uint256
    isRebasing: bool
    decimals: uint256

struct LootDistroConfig:
    legoId: uint256
    legoAddr: address
    underlyingAsset: address
    ambassador: address
    ambassadorRevShare: cs.AmbassadorRevShare
    ambassadorBonusRatio: uint256
    bonusRatio: uint256
    bonusAsset: address

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

# global configs
userWalletConfig: public(cs.UserWalletConfig)
agentConfig: public(cs.AgentConfig)
managerConfig: public(cs.ManagerConfig)
payeeConfig: public(cs.PayeeConfig)
chequeConfig: public(cs.ChequeConfig)
ripeRewardsConfig: public(cs.RipeRewardsConfig)

# asset config
assetConfig: public(HashMap[address, cs.AssetConfig])
isStablecoin: public(HashMap[address, bool])

# security / limits
isLockedSigner: public(HashMap[address, bool]) # signer -> is locked

# security signers (iterable)
securitySigners: public(HashMap[uint256, address]) # index -> signer
indexOfSecuritySigner: public(HashMap[address, uint256]) # signer -> index
numSecuritySigners: public(uint256)

# whitelisted creators (iterable)
whitelistedCreators: public(HashMap[uint256, address]) # index -> creator
indexOfWhitelistedCreator: public(HashMap[address, uint256]) # creator -> index
numWhitelistedCreators: public(uint256)


@deploy
def __init__(_undyHq: address, _defaults: address):
    addys.__init__(_undyHq)
    deptBasics.__init__(False, False) # no minting

    # start at 1, index 0 means "not in list"
    self.numSecuritySigners = 1
    self.numWhitelistedCreators = 1

    if _defaults != empty(address):
        self.userWalletConfig = staticcall Defaults(_defaults).userWalletConfig()
        self.agentConfig = staticcall Defaults(_defaults).agentConfig()
        self.managerConfig = staticcall Defaults(_defaults).managerConfig()
        self.payeeConfig = staticcall Defaults(_defaults).payeeConfig()
        self.chequeConfig = staticcall Defaults(_defaults).chequeConfig()
        self.ripeRewardsConfig = staticcall Defaults(_defaults).ripeRewardsConfig()


######################
# User Wallet Config #
######################


@external
def setUserWalletConfig(_config: cs.UserWalletConfig):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert not deptBasics.isPaused # dev: not activated
    self.userWalletConfig = _config


@external
def setManagerConfig(_config: cs.ManagerConfig):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert not deptBasics.isPaused # dev: not activated
    self.managerConfig = _config


@external
def setPayeeConfig(_config: cs.PayeeConfig):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert not deptBasics.isPaused # dev: not activated
    self.payeeConfig = _config


@external
def setChequeConfig(_config: cs.ChequeConfig):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert not deptBasics.isPaused # dev: not activated
    self.chequeConfig = _config


# helper


@view
@external
def getUserWalletCreationConfig(_creator: address) -> UserWalletCreationConfig:
    config: cs.UserWalletConfig = self.userWalletConfig
    managerConfig: cs.ManagerConfig = self.managerConfig
    payeeConfig: cs.PayeeConfig = self.payeeConfig
    agentConfig: cs.AgentConfig = self.agentConfig
    chequeConfig: cs.ChequeConfig = self.chequeConfig
    return UserWalletCreationConfig(
        numUserWalletsAllowed = config.numUserWalletsAllowed,
        isCreatorAllowed = self._isCreatorAllowed(config.enforceCreatorWhitelist, _creator),
        walletTemplate = config.walletTemplate,
        configTemplate = config.configTemplate,
        startingAgent = agentConfig.startingAgent,
        startingAgentActivationLength = agentConfig.startingAgentActivationLength,
        managerPeriod = managerConfig.managerPeriod,
        managerActivationLength = managerConfig.managerActivationLength,
        mustHaveUsdValueOnSwaps = managerConfig.mustHaveUsdValueOnSwaps,
        maxNumSwapsPerPeriod = managerConfig.maxNumSwapsPerPeriod,
        maxSlippageOnSwaps = managerConfig.maxSlippageOnSwaps,
        onlyApprovedYieldOpps = managerConfig.onlyApprovedYieldOpps,
        payeePeriod = payeeConfig.payeePeriod,
        payeeActivationLength = payeeConfig.payeeActivationLength,
        chequeMaxNumActiveCheques = chequeConfig.maxNumActiveCheques,
        chequeInstantUsdThreshold = chequeConfig.instantUsdThreshold,
        chequePeriodLength = chequeConfig.periodLength,
        chequeExpensiveDelayBlocks = chequeConfig.expensiveDelayBlocks,
        chequeDefaultExpiryBlocks = chequeConfig.defaultExpiryBlocks,
        minKeyActionTimeLock = config.minKeyActionTimeLock,
        maxKeyActionTimeLock = config.maxKeyActionTimeLock,
    )


@view
@external
def getDepositRewardsAsset() -> address:
    return self.userWalletConfig.depositRewardsAsset


@view
@external
def getLootClaimCoolOffPeriod() -> uint256:
    return self.userWalletConfig.lootClaimCoolOffPeriod


#######################
# Ripe Rewards Config #
#######################


@external
def setRipeRewardsConfig(_config: cs.RipeRewardsConfig):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert not deptBasics.isPaused # dev: not activated
    self.ripeRewardsConfig = _config


@view
@external
def getRipeRewardsConfig() -> cs.RipeRewardsConfig:
    return self.ripeRewardsConfig


################
# Agent Config #
################


@external
def setAgentConfig(_config: cs.AgentConfig):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert not deptBasics.isPaused # dev: not activated
    self.agentConfig = _config


@external
def setStarterAgent(_agent: address):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert not deptBasics.isPaused # dev: not activated
    self.agentConfig.startingAgent = _agent


########################
# Asset / Yield Config #
########################


@external
def setAssetConfig(_asset: address, _config: cs.AssetConfig):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert not deptBasics.isPaused # dev: not activated
    self.assetConfig[_asset] = _config


@external
def setIsStablecoin(_asset: address, _isStablecoin: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert not deptBasics.isPaused # dev: not activated
    self.isStablecoin[_asset] = _isStablecoin


# swap fee


@view
@external
def getSwapFee(_tokenIn: address, _tokenOut: address) -> uint256:

    # stable swap fee
    if self.isStablecoin[_tokenIn] and self.isStablecoin[_tokenOut]:
        return self.userWalletConfig.txFees.stableSwapFee

    # asset swap fee takes precedence over global swap fee
    outConfig: cs.AssetConfig = self.assetConfig[_tokenOut]
    if outConfig.hasConfig:
        return outConfig.txFees.swapFee

    return self.userWalletConfig.txFees.swapFee


# rewards fee


@view
@external
def getRewardsFee(_asset: address) -> uint256:
    config: cs.AssetConfig = self.assetConfig[_asset]
    if config.hasConfig:
        return config.txFees.rewardsFee
    return self.userWalletConfig.txFees.rewardsFee


# helpers


@view
@external
def getProfitCalcConfig(_asset: address) -> ProfitCalcConfig:
    assetConfig: cs.AssetConfig = self.assetConfig[_asset]
    maxYieldIncrease: uint256 = assetConfig.yieldConfig.maxYieldIncrease
    performanceFee: uint256 = assetConfig.yieldConfig.performanceFee
    if not assetConfig.hasConfig:
        walletConfig: cs.UserWalletConfig = self.userWalletConfig
        maxYieldIncrease = walletConfig.yieldConfig.maxYieldIncrease
        performanceFee = walletConfig.yieldConfig.performanceFee

    # vault token
    ledger: address = addys._getLedgerAddr()
    vaultToken: VaultToken = staticcall Ledger(ledger).vaultTokens(_asset)

    # get lego addr
    legoAddr: address = empty(address)
    if vaultToken.legoId != 0:
        legoBook: address = addys._getLegoBookAddr()
        legoAddr = staticcall Registry(legoBook).getAddr(vaultToken.legoId)

    return ProfitCalcConfig(
        legoId = vaultToken.legoId,
        legoAddr = legoAddr,
        isYieldAsset = vaultToken.underlyingAsset != empty(address),
        underlyingAsset = vaultToken.underlyingAsset,
        maxYieldIncrease = maxYieldIncrease,
        performanceFee = performanceFee,
        isRebasing = vaultToken.isRebasing,
        decimals = vaultToken.decimals,
    )


@view
@external
def getAssetUsdValueConfig(_asset: address) -> AssetUsdValueConfig:
    ledger: address = addys._getLedgerAddr()
    vaultToken: VaultToken = staticcall Ledger(ledger).vaultTokens(_asset)

    # get lego addr
    legoAddr: address = empty(address)
    if vaultToken.legoId != 0:
        legoBook: address = addys._getLegoBookAddr()
        legoAddr = staticcall Registry(legoBook).getAddr(vaultToken.legoId)

    return AssetUsdValueConfig(
        legoId = vaultToken.legoId,
        legoAddr = legoAddr,
        isYieldAsset = vaultToken.underlyingAsset != empty(address),
        underlyingAsset = vaultToken.underlyingAsset,
    )


@view
@external
def getLootDistroConfig(_asset: address) -> LootDistroConfig:
    assetConfig: cs.AssetConfig = self.assetConfig[_asset]
    ambassadorRevShare: cs.AmbassadorRevShare = assetConfig.ambassadorRevShare
    ambassadorBonusRatio: uint256 = assetConfig.yieldConfig.ambassadorBonusRatio
    bonusRatio: uint256 = assetConfig.yieldConfig.bonusRatio
    bonusAsset: address = assetConfig.yieldConfig.bonusAsset
    if not assetConfig.hasConfig:
        walletConfig: cs.UserWalletConfig = self.userWalletConfig
        ambassadorRevShare = walletConfig.ambassadorRevShare
        ambassadorBonusRatio = walletConfig.yieldConfig.ambassadorBonusRatio
        bonusRatio = walletConfig.yieldConfig.bonusRatio
        bonusAsset = walletConfig.yieldConfig.bonusAsset

    # vault token
    ledger: address = addys._getLedgerAddr()
    vaultToken: VaultToken = staticcall Ledger(ledger).vaultTokens(_asset)

    # get lego addr
    legoAddr: address = empty(address)
    if vaultToken.legoId != 0:
        legoBook: address = addys._getLegoBookAddr()
        legoAddr = staticcall Registry(legoBook).getAddr(vaultToken.legoId)

    return LootDistroConfig(
        legoId = vaultToken.legoId,
        legoAddr = legoAddr,
        underlyingAsset = vaultToken.underlyingAsset,
        ambassador = empty(address),
        ambassadorRevShare = ambassadorRevShare,
        ambassadorBonusRatio = ambassadorBonusRatio,
        bonusRatio = bonusRatio,
        bonusAsset = bonusAsset,
    )


####################
# Security Signers #
####################


# set can perform security action


@external
def setCanPerformSecurityAction(_signer: address, _canPerform: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert not deptBasics.isPaused # dev: not activated
    if _canPerform:
        self._addSecuritySigner(_signer)
    else:
        self._removeSecuritySigner(_signer)


# can perform security action


@view
@external
def canPerformSecurityAction(_signer: address) -> bool:
    return self.indexOfSecuritySigner[_signer] != 0


# add security signer


@internal
def _addSecuritySigner(_signer: address):
    if self.indexOfSecuritySigner[_signer] != 0:
        return
    idx: uint256 = self.numSecuritySigners
    self.securitySigners[idx] = _signer
    self.indexOfSecuritySigner[_signer] = idx
    self.numSecuritySigners = idx + 1


# remove security signer


@internal
def _removeSecuritySigner(_signer: address):
    targetIndex: uint256 = self.indexOfSecuritySigner[_signer]
    if targetIndex == 0:
        return

    lastIndex: uint256 = self.numSecuritySigners - 1
    self.numSecuritySigners = lastIndex
    self.indexOfSecuritySigner[_signer] = 0

    # swap with last item if not already last
    if targetIndex != lastIndex:
        lastItem: address = self.securitySigners[lastIndex]
        self.securitySigners[targetIndex] = lastItem
        self.indexOfSecuritySigner[lastItem] = targetIndex

    self.securitySigners[lastIndex] = empty(address)


#####################
# Creator Whitelist #
#####################


# set creator whitelist


@external
def setCreatorWhitelist(_creator: address, _isWhitelisted: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert not deptBasics.isPaused # dev: not activated
    if _isWhitelisted:
        self._addWhitelistedCreator(_creator)
    else:
        self._removeWhitelistedCreator(_creator)


# can create


@view
@external
def creatorWhitelist(_creator: address) -> bool:
    return self.indexOfWhitelistedCreator[_creator] != 0


@view
@internal
def _isCreatorAllowed(_shouldEnforceWhitelist: bool, _creator: address) -> bool:
    if _shouldEnforceWhitelist:
        return self.indexOfWhitelistedCreator[_creator] != 0
    return True


# add creator


@internal
def _addWhitelistedCreator(_creator: address):
    if self.indexOfWhitelistedCreator[_creator] != 0:
        return
    idx: uint256 = self.numWhitelistedCreators
    self.whitelistedCreators[idx] = _creator
    self.indexOfWhitelistedCreator[_creator] = idx
    self.numWhitelistedCreators = idx + 1


# remove creator


@internal
def _removeWhitelistedCreator(_creator: address):
    targetIndex: uint256 = self.indexOfWhitelistedCreator[_creator]
    if targetIndex == 0:
        return

    lastIndex: uint256 = self.numWhitelistedCreators - 1
    self.numWhitelistedCreators = lastIndex
    self.indexOfWhitelistedCreator[_creator] = 0

    # swap with last item if not already last
    if targetIndex != lastIndex:
        lastItem: address = self.whitelistedCreators[lastIndex]
        self.whitelistedCreators[targetIndex] = lastItem
        self.indexOfWhitelistedCreator[lastItem] = targetIndex

    self.whitelistedCreators[lastIndex] = empty(address)


#################
# Locked Signer #
#################


@external
def setLockedSigner(_signer: address, _isLocked: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert not deptBasics.isPaused # dev: not activated
    self.isLockedSigner[_signer] = _isLocked