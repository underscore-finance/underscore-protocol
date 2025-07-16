# @version 0.4.3

exports: addys.__interface__
exports: gov.__interface__
exports: timeLock.__interface__

initializes: addys
initializes: gov
initializes: timeLock[gov := gov]

import contracts.modules.Addys as addys
import contracts.modules.LocalGov as gov
import contracts.modules.TimeLock as timeLock

import interfaces.ConfigStructs as cs

interface MissionControl:
    def setUserWalletConfig(_config: cs.UserWalletConfig): nonpayable
    def userWalletConfig() -> cs.UserWalletConfig: view

flag ActionType:
    USER_WALLET_TEMPLATES
    TRIAL_FUNDS
    WALLET_CREATION_LIMITS
    KEY_ACTION_TIMELOCK_BOUNDS
    DEFAULT_STALE_BLOCKS
    TX_FEES
    AMBASSADOR_REV_SHARE
    DEFAULT_YIELD_PARAMS
    LOOT_PARAMS

event PendingUserWalletTemplatesChange:
    walletTemplate: address
    configTemplate: address
    confirmationBlock: uint256
    actionId: uint256

event UserWalletTemplatesSet:
    walletTemplate: address
    configTemplate: address

event PendingTrialFundsChange:
    trialAsset: address
    trialAmount: uint256
    confirmationBlock: uint256
    actionId: uint256

event TrialFundsSet:
    trialAsset: address
    trialAmount: uint256

event PendingWalletCreationLimitsChange:
    numUserWalletsAllowed: uint256
    enforceCreatorWhitelist: bool
    confirmationBlock: uint256
    actionId: uint256

event WalletCreationLimitsSet:
    numUserWalletsAllowed: uint256
    enforceCreatorWhitelist: bool

event PendingKeyActionTimelockBoundsChange:
    minKeyActionTimeLock: uint256
    maxKeyActionTimeLock: uint256
    confirmationBlock: uint256
    actionId: uint256

event KeyActionTimelockBoundsSet:
    minKeyActionTimeLock: uint256
    maxKeyActionTimeLock: uint256

event PendingDefaultStaleBlocksChange:
    defaultStaleBlocks: uint256
    confirmationBlock: uint256
    actionId: uint256

event DefaultStaleBlocksSet:
    defaultStaleBlocks: uint256

event PendingTxFeesChange:
    swapFee: uint256
    stableSwapFee: uint256
    rewardsFee: uint256
    confirmationBlock: uint256
    actionId: uint256

event TxFeesSet:
    swapFee: uint256
    stableSwapFee: uint256
    rewardsFee: uint256

event PendingAmbassadorRevShareChange:
    swapRatio: uint256
    rewardsRatio: uint256
    yieldRatio: uint256
    confirmationBlock: uint256
    actionId: uint256

event AmbassadorRevShareSet:
    swapRatio: uint256
    rewardsRatio: uint256
    yieldRatio: uint256

event PendingDefaultYieldParamsChange:
    defaultYieldMaxIncrease: uint256
    defaultYieldPerformanceFee: uint256
    defaultYieldAmbassadorBonusRatio: uint256
    defaultYieldBonusRatio: uint256
    defaultYieldAltBonusAsset: address
    confirmationBlock: uint256
    actionId: uint256

event DefaultYieldParamsSet:
    defaultYieldMaxIncrease: uint256
    defaultYieldPerformanceFee: uint256
    defaultYieldAmbassadorBonusRatio: uint256
    defaultYieldBonusRatio: uint256
    defaultYieldAltBonusAsset: address

event PendingLootParamsChange:
    depositRewardsAsset: address
    lootClaimCoolOffPeriod: uint256
    confirmationBlock: uint256
    actionId: uint256

event LootParamsSet:
    depositRewardsAsset: address
    lootClaimCoolOffPeriod: uint256

# pending config changes
actionType: public(HashMap[uint256, ActionType]) # aid -> type
pendingUserWalletConfig: public(HashMap[uint256, cs.UserWalletConfig]) # aid -> config

HUNDRED_PERCENT: constant(uint256) = 100_00 # 100%


@deploy
def __init__(
    _undyHq: address,
    _tempGov: address,
    _minConfigTimeLock: uint256,
    _maxConfigTimeLock: uint256,
):
    addys.__init__(_undyHq)
    gov.__init__(_undyHq, _tempGov, 0, 0, 0)
    timeLock.__init__(_minConfigTimeLock, _maxConfigTimeLock, 0, _maxConfigTimeLock)


######################
# User Wallet Config #
######################


# user wallet templates


@external
def setUserWalletTemplates(_walletTemplate: address, _configTemplate: address) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms

    assert self._areValidUserWalletTemplates(_walletTemplate, _configTemplate) # dev: invalid user wallet templates
    return self._setUserWalletConfig(ActionType.USER_WALLET_TEMPLATES, _walletTemplate, _configTemplate)


@view
@internal
def _areValidUserWalletTemplates(_walletTemplate: address, _configTemplate: address) -> bool:
    if empty(address) in [_walletTemplate, _configTemplate]:
        return False
    if not _walletTemplate.is_contract or not _configTemplate.is_contract:
        return False
    return True


# trial funds


@external
def setTrialFunds(_trialAsset: address, _trialAmount: uint256) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    return self._setUserWalletConfig(
        ActionType.TRIAL_FUNDS,
        empty(address),
        empty(address),
        _trialAsset,
        _trialAmount
    )


# wallet creation limits


@external
def setWalletCreationLimits(_numUserWalletsAllowed: uint256, _enforceCreatorWhitelist: bool) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    
    assert self._isValidNumUserWalletsAllowed(_numUserWalletsAllowed) # dev: invalid num user wallets allowed
    return self._setUserWalletConfig(
        ActionType.WALLET_CREATION_LIMITS,
        empty(address),
        empty(address),
        empty(address),
        0,
        _numUserWalletsAllowed,
        _enforceCreatorWhitelist
    )


@view
@internal
def _isValidNumUserWalletsAllowed(_numUserWalletsAllowed: uint256) -> bool:
    if _numUserWalletsAllowed == 0:
        return False
    if _numUserWalletsAllowed == max_value(uint256):
        return False
    return True


# key action timelock bounds


@external
def setKeyActionTimelockBounds(_minKeyActionTimeLock: uint256, _maxKeyActionTimeLock: uint256) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    
    assert self._areValidKeyActionTimelockBounds(_minKeyActionTimeLock, _maxKeyActionTimeLock) # dev: invalid key action timelock bounds
    return self._setUserWalletConfig(
        ActionType.KEY_ACTION_TIMELOCK_BOUNDS,
        empty(address),
        empty(address),
        empty(address),
        0,
        0,
        False,
        _minKeyActionTimeLock,
        _maxKeyActionTimeLock
    )


@view
@internal
def _areValidKeyActionTimelockBounds(_minKeyActionTimeLock: uint256, _maxKeyActionTimeLock: uint256) -> bool:
    if 0 in [_minKeyActionTimeLock, _maxKeyActionTimeLock]:
        return False
    if max_value(uint256) in [_minKeyActionTimeLock, _maxKeyActionTimeLock]:
        return False
    if _minKeyActionTimeLock >= _maxKeyActionTimeLock:
        return False
    return True


# default stale blocks


@external
def setDefaultStaleBlocks(_defaultStaleBlocks: uint256) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    
    assert self._isValidDefaultStaleBlocks(_defaultStaleBlocks) # dev: invalid default stale blocks
    return self._setUserWalletConfig(
        ActionType.DEFAULT_STALE_BLOCKS,
        empty(address),
        empty(address),
        empty(address),
        0,
        0,
        False,
        0,
        0,
        _defaultStaleBlocks
    )


@view
@internal
def _isValidDefaultStaleBlocks(_defaultStaleBlocks: uint256) -> bool:
    if _defaultStaleBlocks == 0:
        return False
    if _defaultStaleBlocks == max_value(uint256):
        return False
    return True


# tx fees


@external
def setTxFees(_swapFee: uint256, _stableSwapFee: uint256, _rewardsFee: uint256) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    
    assert self._areValidTxFees(_swapFee, _stableSwapFee, _rewardsFee) # dev: invalid tx fees
    return self._setUserWalletConfig(
        ActionType.TX_FEES,
        empty(address),
        empty(address),
        empty(address),
        0,
        0,
        False,
        0,
        0,
        0,
        empty(address),
        _swapFee,
        _stableSwapFee,
        _rewardsFee
    )


@view
@internal
def _areValidTxFees(_swapFee: uint256, _stableSwapFee: uint256, _rewardsFee: uint256) -> bool:
    if _swapFee > HUNDRED_PERCENT:
        return False
    if _stableSwapFee > HUNDRED_PERCENT:
        return False
    if _rewardsFee > HUNDRED_PERCENT:
        return False
    return True


# ambassador rev share


@external
def setAmbassadorRevShare(_swapRatio: uint256, _rewardsRatio: uint256, _yieldRatio: uint256) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    
    assert self._areValidAmbassadorRevShareRatios(_swapRatio, _rewardsRatio, _yieldRatio) # dev: invalid ambassador rev share ratios
    return self._setUserWalletConfig(
        ActionType.AMBASSADOR_REV_SHARE,
        empty(address),
        empty(address),
        empty(address),
        0,
        0,
        False,
        0,
        0,
        0,
        empty(address),
        0,
        0,
        0,
        _swapRatio,
        _rewardsRatio,
        _yieldRatio
    )


@view
@internal
def _areValidAmbassadorRevShareRatios(_swapRatio: uint256, _rewardsRatio: uint256, _yieldRatio: uint256) -> bool:
    if _swapRatio > HUNDRED_PERCENT:
        return False
    if _rewardsRatio > HUNDRED_PERCENT:
        return False
    if _yieldRatio > HUNDRED_PERCENT:
        return False
    return True


# default yield params


@external
def setDefaultYieldParams(
    _defaultYieldMaxIncrease: uint256,
    _defaultYieldPerformanceFee: uint256,
    _defaultYieldAmbassadorBonusRatio: uint256,
    _defaultYieldBonusRatio: uint256,
    _defaultYieldAltBonusAsset: address
) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    
    assert self._areValidDefaultYieldParams(
        _defaultYieldMaxIncrease,
        _defaultYieldPerformanceFee,
        _defaultYieldAmbassadorBonusRatio,
        _defaultYieldBonusRatio
    ) # dev: invalid default yield params
    
    return self._setUserWalletConfig(
        ActionType.DEFAULT_YIELD_PARAMS,
        empty(address),
        empty(address),
        empty(address),
        0,
        0,
        False,
        0,
        0,
        0,
        empty(address),
        0,
        0,
        0,
        0,
        0,
        0,
        _defaultYieldMaxIncrease,
        _defaultYieldPerformanceFee,
        _defaultYieldAmbassadorBonusRatio,
        _defaultYieldBonusRatio,
        _defaultYieldAltBonusAsset
    )


@view
@internal
def _areValidDefaultYieldParams(
    _defaultYieldMaxIncrease: uint256,
    _defaultYieldPerformanceFee: uint256,
    _defaultYieldAmbassadorBonusRatio: uint256,
    _defaultYieldBonusRatio: uint256
) -> bool:
    if _defaultYieldMaxIncrease > HUNDRED_PERCENT:
        return False
    if _defaultYieldPerformanceFee > HUNDRED_PERCENT:
        return False
    if _defaultYieldAmbassadorBonusRatio > HUNDRED_PERCENT:
        return False
    if _defaultYieldBonusRatio > HUNDRED_PERCENT:
        return False
    return True


# loot params


@external
def setLootParams(_depositRewardsAsset: address, _lootClaimCoolOffPeriod: uint256) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    
    assert self._areValidLootParams(_lootClaimCoolOffPeriod) # dev: invalid loot params
    return self._setUserWalletConfig(
        ActionType.LOOT_PARAMS,
        empty(address),
        empty(address),
        empty(address),
        0,
        0,
        False,
        0,
        0,
        0,
        _depositRewardsAsset,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        empty(address),
        _lootClaimCoolOffPeriod
    )


@view
@internal
def _areValidLootParams(_lootClaimCoolOffPeriod: uint256) -> bool:
    if _lootClaimCoolOffPeriod == 0:
        return False
    if _lootClaimCoolOffPeriod == max_value(uint256):
        return False
    return True


# set pending general config


@internal
def _setUserWalletConfig(
    _actionType: ActionType,
    _walletTemplate: address = empty(address),
    _configTemplate: address = empty(address),
    _trialAsset: address = empty(address),
    _trialAmount: uint256 = 0,
    _numUserWalletsAllowed: uint256 = 0,
    _enforceCreatorWhitelist: bool = False,
    _minKeyActionTimeLock: uint256 = 0,
    _maxKeyActionTimeLock: uint256 = 0,
    _defaultStaleBlocks: uint256 = 0,
    _depositRewardsAsset: address = empty(address),
    _txFeesSwapFee: uint256 = 0,
    _txFeesStableSwapFee: uint256 = 0,
    _txFeesRewardsFee: uint256 = 0,
    _ambassadorRevShareSwapRatio: uint256 = 0,
    _ambassadorRevShareRewardsRatio: uint256 = 0,
    _ambassadorRevShareYieldRatio: uint256 = 0,
    _defaultYieldMaxIncrease: uint256 = 0,
    _defaultYieldPerformanceFee: uint256 = 0,
    _defaultYieldAmbassadorBonusRatio: uint256 = 0,
    _defaultYieldBonusRatio: uint256 = 0,
    _defaultYieldAltBonusAsset: address = empty(address),
    _lootClaimCoolOffPeriod: uint256 = 0,
) -> uint256:
    aid: uint256 = timeLock._initiateAction()

    self.actionType[aid] = _actionType
    self.pendingUserWalletConfig[aid] = cs.UserWalletConfig(
        walletTemplate=_walletTemplate,
        configTemplate=_configTemplate,
        trialAsset=_trialAsset,
        trialAmount=_trialAmount,
        numUserWalletsAllowed=_numUserWalletsAllowed,
        enforceCreatorWhitelist=_enforceCreatorWhitelist,
        minKeyActionTimeLock=_minKeyActionTimeLock,
        maxKeyActionTimeLock=_maxKeyActionTimeLock,
        defaultStaleBlocks=_defaultStaleBlocks,
        depositRewardsAsset=_depositRewardsAsset,
        txFees=cs.TxFees(
            swapFee=_txFeesSwapFee,
            stableSwapFee=_txFeesStableSwapFee,
            rewardsFee=_txFeesRewardsFee,
        ),
        ambassadorRevShare=cs.AmbassadorRevShare(
            swapRatio=_ambassadorRevShareSwapRatio,
            rewardsRatio=_ambassadorRevShareRewardsRatio,
            yieldRatio=_ambassadorRevShareYieldRatio,
        ),
        defaultYieldMaxIncrease=_defaultYieldMaxIncrease,
        defaultYieldPerformanceFee=_defaultYieldPerformanceFee,
        defaultYieldAmbassadorBonusRatio=_defaultYieldAmbassadorBonusRatio,
        defaultYieldBonusRatio=_defaultYieldBonusRatio,
        defaultYieldAltBonusAsset=_defaultYieldAltBonusAsset,
        lootClaimCoolOffPeriod=_lootClaimCoolOffPeriod,
    )

    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    if _actionType == ActionType.USER_WALLET_TEMPLATES:
        log PendingUserWalletTemplatesChange(
            walletTemplate=_walletTemplate,
            configTemplate=_configTemplate,
            confirmationBlock=confirmationBlock,
            actionId=aid,
        )
    elif _actionType == ActionType.TRIAL_FUNDS:
        log PendingTrialFundsChange(
            trialAsset=_trialAsset,
            trialAmount=_trialAmount,
            confirmationBlock=confirmationBlock,
            actionId=aid,
        )
    elif _actionType == ActionType.WALLET_CREATION_LIMITS:
        log PendingWalletCreationLimitsChange(
            numUserWalletsAllowed=_numUserWalletsAllowed,
            enforceCreatorWhitelist=_enforceCreatorWhitelist,
            confirmationBlock=confirmationBlock,
            actionId=aid,
        )
    elif _actionType == ActionType.KEY_ACTION_TIMELOCK_BOUNDS:
        log PendingKeyActionTimelockBoundsChange(
            minKeyActionTimeLock=_minKeyActionTimeLock,
            maxKeyActionTimeLock=_maxKeyActionTimeLock,
            confirmationBlock=confirmationBlock,
            actionId=aid,
        )
    elif _actionType == ActionType.DEFAULT_STALE_BLOCKS:
        log PendingDefaultStaleBlocksChange(
            defaultStaleBlocks=_defaultStaleBlocks,
            confirmationBlock=confirmationBlock,
            actionId=aid,
        )
    elif _actionType == ActionType.TX_FEES:
        log PendingTxFeesChange(
            swapFee=_txFeesSwapFee,
            stableSwapFee=_txFeesStableSwapFee,
            rewardsFee=_txFeesRewardsFee,
            confirmationBlock=confirmationBlock,
            actionId=aid,
        )
    elif _actionType == ActionType.AMBASSADOR_REV_SHARE:
        log PendingAmbassadorRevShareChange(
            swapRatio=_ambassadorRevShareSwapRatio,
            rewardsRatio=_ambassadorRevShareRewardsRatio,
            yieldRatio=_ambassadorRevShareYieldRatio,
            confirmationBlock=confirmationBlock,
            actionId=aid,
        )
    elif _actionType == ActionType.DEFAULT_YIELD_PARAMS:
        log PendingDefaultYieldParamsChange(
            defaultYieldMaxIncrease=_defaultYieldMaxIncrease,
            defaultYieldPerformanceFee=_defaultYieldPerformanceFee,
            defaultYieldAmbassadorBonusRatio=_defaultYieldAmbassadorBonusRatio,
            defaultYieldBonusRatio=_defaultYieldBonusRatio,
            defaultYieldAltBonusAsset=_defaultYieldAltBonusAsset,
            confirmationBlock=confirmationBlock,
            actionId=aid,
        )
    elif _actionType == ActionType.LOOT_PARAMS:
        log PendingLootParamsChange(
            depositRewardsAsset=_depositRewardsAsset,
            lootClaimCoolOffPeriod=_lootClaimCoolOffPeriod,
            confirmationBlock=confirmationBlock,
            actionId=aid,
        )
    return aid


#############
# Execution #
#############


@external
def executePendingAction(_aid: uint256) -> bool:
    assert gov._canGovern(msg.sender) # dev: no perms

    # check time lock
    if not timeLock._confirmAction(_aid):
        if timeLock._isExpired(_aid):
            self._cancelPendingAction(_aid)
        return False

    actionType: ActionType = self.actionType[_aid]
    mc: address = addys._getMissionControlAddr()

    if actionType == ActionType.USER_WALLET_TEMPLATES:
        config: cs.UserWalletConfig = staticcall MissionControl(mc).userWalletConfig()
        p: cs.UserWalletConfig = self.pendingUserWalletConfig[_aid]
        config.walletTemplate = p.walletTemplate
        config.configTemplate = p.configTemplate
        extcall MissionControl(mc).setUserWalletConfig(config)
        log UserWalletTemplatesSet(walletTemplate=p.walletTemplate, configTemplate=p.configTemplate)

    elif actionType == ActionType.TRIAL_FUNDS:
        config: cs.UserWalletConfig = staticcall MissionControl(mc).userWalletConfig()
        p: cs.UserWalletConfig = self.pendingUserWalletConfig[_aid]
        config.trialAsset = p.trialAsset
        config.trialAmount = p.trialAmount
        extcall MissionControl(mc).setUserWalletConfig(config)
        log TrialFundsSet(trialAsset=p.trialAsset, trialAmount=p.trialAmount)

    elif actionType == ActionType.WALLET_CREATION_LIMITS:
        config: cs.UserWalletConfig = staticcall MissionControl(mc).userWalletConfig()
        p: cs.UserWalletConfig = self.pendingUserWalletConfig[_aid]
        config.numUserWalletsAllowed = p.numUserWalletsAllowed
        config.enforceCreatorWhitelist = p.enforceCreatorWhitelist
        extcall MissionControl(mc).setUserWalletConfig(config)
        log WalletCreationLimitsSet(numUserWalletsAllowed=p.numUserWalletsAllowed, enforceCreatorWhitelist=p.enforceCreatorWhitelist)

    elif actionType == ActionType.KEY_ACTION_TIMELOCK_BOUNDS:
        config: cs.UserWalletConfig = staticcall MissionControl(mc).userWalletConfig()
        p: cs.UserWalletConfig = self.pendingUserWalletConfig[_aid]
        config.minKeyActionTimeLock = p.minKeyActionTimeLock
        config.maxKeyActionTimeLock = p.maxKeyActionTimeLock
        extcall MissionControl(mc).setUserWalletConfig(config)
        log KeyActionTimelockBoundsSet(minKeyActionTimeLock=p.minKeyActionTimeLock, maxKeyActionTimeLock=p.maxKeyActionTimeLock)

    elif actionType == ActionType.DEFAULT_STALE_BLOCKS:
        config: cs.UserWalletConfig = staticcall MissionControl(mc).userWalletConfig()
        p: cs.UserWalletConfig = self.pendingUserWalletConfig[_aid]
        config.defaultStaleBlocks = p.defaultStaleBlocks
        extcall MissionControl(mc).setUserWalletConfig(config)
        log DefaultStaleBlocksSet(defaultStaleBlocks=p.defaultStaleBlocks)

    elif actionType == ActionType.TX_FEES:
        config: cs.UserWalletConfig = staticcall MissionControl(mc).userWalletConfig()
        p: cs.UserWalletConfig = self.pendingUserWalletConfig[_aid]
        config.txFees = p.txFees
        extcall MissionControl(mc).setUserWalletConfig(config)
        log TxFeesSet(swapFee=p.txFees.swapFee, stableSwapFee=p.txFees.stableSwapFee, rewardsFee=p.txFees.rewardsFee)

    elif actionType == ActionType.AMBASSADOR_REV_SHARE:
        config: cs.UserWalletConfig = staticcall MissionControl(mc).userWalletConfig()
        p: cs.UserWalletConfig = self.pendingUserWalletConfig[_aid]
        config.ambassadorRevShare = p.ambassadorRevShare
        extcall MissionControl(mc).setUserWalletConfig(config)
        log AmbassadorRevShareSet(swapRatio=p.ambassadorRevShare.swapRatio, rewardsRatio=p.ambassadorRevShare.rewardsRatio, yieldRatio=p.ambassadorRevShare.yieldRatio)

    elif actionType == ActionType.DEFAULT_YIELD_PARAMS:
        config: cs.UserWalletConfig = staticcall MissionControl(mc).userWalletConfig()
        p: cs.UserWalletConfig = self.pendingUserWalletConfig[_aid]
        config.defaultYieldMaxIncrease = p.defaultYieldMaxIncrease
        config.defaultYieldPerformanceFee = p.defaultYieldPerformanceFee
        config.defaultYieldAmbassadorBonusRatio = p.defaultYieldAmbassadorBonusRatio
        config.defaultYieldBonusRatio = p.defaultYieldBonusRatio
        config.defaultYieldAltBonusAsset = p.defaultYieldAltBonusAsset
        extcall MissionControl(mc).setUserWalletConfig(config)
        log DefaultYieldParamsSet(
            defaultYieldMaxIncrease=p.defaultYieldMaxIncrease,
            defaultYieldPerformanceFee=p.defaultYieldPerformanceFee,
            defaultYieldAmbassadorBonusRatio=p.defaultYieldAmbassadorBonusRatio,
            defaultYieldBonusRatio=p.defaultYieldBonusRatio,
            defaultYieldAltBonusAsset=p.defaultYieldAltBonusAsset
        )

    elif actionType == ActionType.LOOT_PARAMS:
        config: cs.UserWalletConfig = staticcall MissionControl(mc).userWalletConfig()
        p: cs.UserWalletConfig = self.pendingUserWalletConfig[_aid]
        config.depositRewardsAsset = p.depositRewardsAsset
        config.lootClaimCoolOffPeriod = p.lootClaimCoolOffPeriod
        extcall MissionControl(mc).setUserWalletConfig(config)
        log LootParamsSet(depositRewardsAsset=p.depositRewardsAsset, lootClaimCoolOffPeriod=p.lootClaimCoolOffPeriod)

    self.actionType[_aid] = empty(ActionType)
    return True


# cancel action


@external
def cancelPendingAction(_aid: uint256) -> bool:
    assert gov._canGovern(msg.sender) # dev: no perms
    self._cancelPendingAction(_aid)
    return True


@internal
def _cancelPendingAction(_aid: uint256):
    assert timeLock._cancelAction(_aid) # dev: cannot cancel action
    self.actionType[_aid] = empty(ActionType)