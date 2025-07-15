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

# pending config changes
actionType: public(HashMap[uint256, ActionType]) # aid -> type
pendingUserWalletConfig: public(HashMap[uint256, cs.UserWalletConfig]) # aid -> config


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