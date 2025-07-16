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
    def setCanPerformSecurityAction(_signer: address, _canPerform: bool): nonpayable
    def setCreatorWhitelist(_creator: address, _isWhitelisted: bool): nonpayable
    def setLockedSigner(_signer: address, _isLocked: bool): nonpayable
    def setUserWalletConfig(_config: cs.UserWalletConfig): nonpayable
    def canPerformSecurityAction(_signer: address) -> bool: view
    def setManagerConfig(_config: cs.ManagerConfig): nonpayable
    def setPayeeConfig(_config: cs.PayeeConfig): nonpayable
    def setAgentConfig(_config: cs.AgentConfig): nonpayable
    def userWalletConfig() -> cs.UserWalletConfig: view
    def agentConfig() -> cs.AgentConfig: view

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
    AGENT_TEMPLATE
    AGENT_CREATION_LIMITS
    STARTER_AGENT_PARAMS
    MANAGER_CONFIG
    PAYEE_CONFIG
    CAN_PERFORM_SECURITY_ACTION

struct IsAddrAllowed:
    addr: address
    isAllowed: bool

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

event PendingAgentTemplateChange:
    agentTemplate: address
    confirmationBlock: uint256
    actionId: uint256

event AgentTemplateSet:
    agentTemplate: address

event PendingAgentCreationLimitsChange:
    numAgentsAllowed: uint256
    enforceCreatorWhitelist: bool
    confirmationBlock: uint256
    actionId: uint256

event AgentCreationLimitsSet:
    numAgentsAllowed: uint256
    enforceCreatorWhitelist: bool

event PendingStarterAgentParamsChange:
    startingAgent: address
    startingAgentActivationLength: uint256
    confirmationBlock: uint256
    actionId: uint256

event StarterAgentParamsSet:
    startingAgent: address
    startingAgentActivationLength: uint256

event PendingManagerConfigChange:
    managerPeriod: uint256
    managerActivationLength: uint256
    confirmationBlock: uint256
    actionId: uint256

event PendingPayeeConfigChange:
    payeePeriod: uint256
    payeeActivationLength: uint256
    confirmationBlock: uint256
    actionId: uint256

event PendingCanPerformSecurityAction:
    signer: address
    canPerform: bool
    confirmationBlock: uint256
    actionId: uint256

event CreatorWhitelistSet:
    creator: address
    isWhitelisted: bool
    caller: address

event ManagerConfigSet:
    managerPeriod: uint256
    managerActivationLength: uint256

event PayeeConfigSet:
    payeePeriod: uint256
    payeeActivationLength: uint256

event CanPerformSecurityAction:
    signer: address
    canPerform: bool

event LockedSignerSet:
    signer: address
    isLocked: bool
    caller: address

# pending config changes
actionType: public(HashMap[uint256, ActionType]) # aid -> type
pendingUserWalletConfig: public(HashMap[uint256, cs.UserWalletConfig]) # aid -> config
pendingAgentConfig: public(HashMap[uint256, cs.AgentConfig]) # aid -> config
pendingManagerConfig: public(HashMap[uint256, cs.ManagerConfig]) # aid -> config
pendingPayeeConfig: public(HashMap[uint256, cs.PayeeConfig]) # aid -> config
pendingAddrToBool: public(HashMap[uint256, IsAddrAllowed])

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


# access control


@view
@internal
def _hasPermsToEnable(_caller: address, _shouldEnable: bool) -> bool:
    if gov._canGovern(_caller):
        return True
    if not _shouldEnable:
        return staticcall MissionControl(addys._getMissionControlAddr()).canPerformSecurityAction(_caller)
    return False


######################
# User Wallet Config #
######################


# user wallet templates


@external
def setUserWalletTemplates(_walletTemplate: address, _configTemplate: address) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms

    assert self._areValidUserWalletTemplates(_walletTemplate, _configTemplate) # dev: invalid user wallet templates
    return self._setPendingUserWalletConfig(ActionType.USER_WALLET_TEMPLATES, _walletTemplate, _configTemplate)


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
    return self._setPendingUserWalletConfig(
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
    return self._setPendingUserWalletConfig(
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
    return self._setPendingUserWalletConfig(
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
    return self._setPendingUserWalletConfig(
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
    return self._setPendingUserWalletConfig(
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
    return self._setPendingUserWalletConfig(
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
    
    return self._setPendingUserWalletConfig(
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
    return self._setPendingUserWalletConfig(
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


################
# Agent Config #
################


# agent template


@external
def setAgentTemplate(_agentTemplate: address) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    
    assert self._isValidAgentTemplate(_agentTemplate) # dev: invalid agent template
    return self._setPendingAgentConfig(
        ActionType.AGENT_TEMPLATE,
        _agentTemplate
    )


@view
@internal
def _isValidAgentTemplate(_agentTemplate: address) -> bool:
    if _agentTemplate == empty(address):
        return False
    if not _agentTemplate.is_contract:
        return False
    return True


# agent creation limits


@external
def setAgentCreationLimits(_numAgentsAllowed: uint256, _enforceCreatorWhitelist: bool) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    
    assert self._isValidNumAgentsAllowed(_numAgentsAllowed) # dev: invalid num agents allowed
    return self._setPendingAgentConfig(
        ActionType.AGENT_CREATION_LIMITS,
        empty(address),
        _numAgentsAllowed,
        _enforceCreatorWhitelist
    )


@view
@internal
def _isValidNumAgentsAllowed(_numAgentsAllowed: uint256) -> bool:
    if _numAgentsAllowed == 0:
        return False
    if _numAgentsAllowed == max_value(uint256):
        return False
    return True


# starter agent params


@external
def setStarterAgentParams(_startingAgent: address, _startingAgentActivationLength: uint256) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    
    assert self._areValidStarterAgentParams(_startingAgent, _startingAgentActivationLength) # dev: invalid starter agent params
    return self._setPendingAgentConfig(
        ActionType.STARTER_AGENT_PARAMS,
        empty(address),
        0,
        False,
        _startingAgent,
        _startingAgentActivationLength
    )


@view
@internal
def _areValidStarterAgentParams(_startingAgent: address, _startingAgentActivationLength: uint256) -> bool:

    # If starting agent is set, activation length must be non-zero
    if _startingAgent != empty(address) and _startingAgentActivationLength == 0:
        return False

    # If starting agent is zero address, activation length must be zero
    if _startingAgent == empty(address) and _startingAgentActivationLength != 0:
        return False

    # Activation length cannot be max value
    if _startingAgentActivationLength == max_value(uint256):
        return False

    return True


##################
# Manager Config #
##################


@external
def setManagerConfig(_managerPeriod: uint256, _managerActivationLength: uint256) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    
    assert 0 not in [_managerPeriod, _managerActivationLength] # dev: invalid manager config
    assert max_value(uint256) not in [_managerPeriod, _managerActivationLength] # dev: invalid manager config

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.MANAGER_CONFIG
    self.pendingManagerConfig[aid] = cs.ManagerConfig(
        managerPeriod=_managerPeriod,
        managerActivationLength=_managerActivationLength
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingManagerConfigChange(
        managerPeriod=_managerPeriod,
        managerActivationLength=_managerActivationLength,
        confirmationBlock=confirmationBlock,
        actionId=aid,
    )
    return aid


################
# Payee Config #
################


@external
def setPayeeConfig(_payeePeriod: uint256, _payeeActivationLength: uint256) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    
    assert 0 not in [_payeePeriod, _payeeActivationLength] # dev: invalid payee config
    assert max_value(uint256) not in [_payeePeriod, _payeeActivationLength] # dev: invalid payee config

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.PAYEE_CONFIG
    self.pendingPayeeConfig[aid] = cs.PayeeConfig(
        payeePeriod=_payeePeriod,
        payeeActivationLength=_payeeActivationLength
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingPayeeConfigChange(
        payeePeriod=_payeePeriod,
        payeeActivationLength=_payeeActivationLength,
        confirmationBlock=confirmationBlock,
        actionId=aid,
    )
    return aid


#########
# Other #
#########


# can perform security action


@external
def setCanPerformSecurityAction(_signer: address, _canPerform: bool) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.CAN_PERFORM_SECURITY_ACTION
    self.pendingAddrToBool[aid] = IsAddrAllowed(addr=_signer, isAllowed=_canPerform)
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingCanPerformSecurityAction(signer=_signer, canPerform=_canPerform, confirmationBlock=confirmationBlock, actionId=aid)
    return aid


# set creator whitelist


@external
def setCreatorWhitelist(_creator: address, _isWhitelisted: bool):
    assert self._hasPermsToEnable(msg.sender, _isWhitelisted) # dev: no perms

    assert _creator != empty(address) # dev: invalid creator
    mc: address = addys._getMissionControlAddr()
    extcall MissionControl(mc).setCreatorWhitelist(_creator, _isWhitelisted)

    log CreatorWhitelistSet(creator=_creator, isWhitelisted=_isWhitelisted, caller=msg.sender)


# locked signer


@external
def setLockedSigner(_signer: address, _isLocked: bool):
    assert self._hasPermsToEnable(msg.sender, _isLocked) # dev: no perms

    assert _signer != empty(address) # dev: invalid creator
    mc: address = addys._getMissionControlAddr()
    extcall MissionControl(mc).setLockedSigner(_signer, _isLocked)

    log LockedSignerSet(signer=_signer, isLocked=_isLocked, caller=msg.sender)


###############
# Set Pending #
###############


@internal
def _setPendingUserWalletConfig(
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


@internal
def _setPendingAgentConfig(
    _actionType: ActionType,
    _agentTemplate: address = empty(address),
    _numAgentsAllowed: uint256 = 0,
    _enforceCreatorWhitelist: bool = False,
    _startingAgent: address = empty(address),
    _startingAgentActivationLength: uint256 = 0,
) -> uint256:
    aid: uint256 = timeLock._initiateAction()

    self.actionType[aid] = _actionType
    self.pendingAgentConfig[aid] = cs.AgentConfig(
        agentTemplate=_agentTemplate,
        numAgentsAllowed=_numAgentsAllowed,
        enforceCreatorWhitelist=_enforceCreatorWhitelist,
        startingAgent=_startingAgent,
        startingAgentActivationLength=_startingAgentActivationLength,
    )

    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    if _actionType == ActionType.AGENT_TEMPLATE:
        log PendingAgentTemplateChange(
            agentTemplate=_agentTemplate,
            confirmationBlock=confirmationBlock,
            actionId=aid,
        )
    elif _actionType == ActionType.AGENT_CREATION_LIMITS:
        log PendingAgentCreationLimitsChange(
            numAgentsAllowed=_numAgentsAllowed,
            enforceCreatorWhitelist=_enforceCreatorWhitelist,
            confirmationBlock=confirmationBlock,
            actionId=aid,
        )
    elif _actionType == ActionType.STARTER_AGENT_PARAMS:
        log PendingStarterAgentParamsChange(
            startingAgent=_startingAgent,
            startingAgentActivationLength=_startingAgentActivationLength,
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

    elif actionType == ActionType.AGENT_TEMPLATE:
        config: cs.AgentConfig = staticcall MissionControl(mc).agentConfig()
        p: cs.AgentConfig = self.pendingAgentConfig[_aid]
        config.agentTemplate = p.agentTemplate
        extcall MissionControl(mc).setAgentConfig(config)
        log AgentTemplateSet(agentTemplate=p.agentTemplate)

    elif actionType == ActionType.AGENT_CREATION_LIMITS:
        config: cs.AgentConfig = staticcall MissionControl(mc).agentConfig()
        p: cs.AgentConfig = self.pendingAgentConfig[_aid]
        config.numAgentsAllowed = p.numAgentsAllowed
        config.enforceCreatorWhitelist = p.enforceCreatorWhitelist
        extcall MissionControl(mc).setAgentConfig(config)
        log AgentCreationLimitsSet(numAgentsAllowed=p.numAgentsAllowed, enforceCreatorWhitelist=p.enforceCreatorWhitelist)

    elif actionType == ActionType.STARTER_AGENT_PARAMS:
        config: cs.AgentConfig = staticcall MissionControl(mc).agentConfig()
        p: cs.AgentConfig = self.pendingAgentConfig[_aid]
        config.startingAgent = p.startingAgent
        config.startingAgentActivationLength = p.startingAgentActivationLength
        extcall MissionControl(mc).setAgentConfig(config)
        log StarterAgentParamsSet(startingAgent=p.startingAgent, startingAgentActivationLength=p.startingAgentActivationLength)

    elif actionType == ActionType.MANAGER_CONFIG:
        p: cs.ManagerConfig = self.pendingManagerConfig[_aid]
        extcall MissionControl(mc).setManagerConfig(p)
        log ManagerConfigSet(managerPeriod=p.managerPeriod, managerActivationLength=p.managerActivationLength)

    elif actionType == ActionType.PAYEE_CONFIG:
        p: cs.PayeeConfig = self.pendingPayeeConfig[_aid]
        extcall MissionControl(mc).setPayeeConfig(p)
        log PayeeConfigSet(payeePeriod=p.payeePeriod, payeeActivationLength=p.payeeActivationLength)

    elif actionType == ActionType.CAN_PERFORM_SECURITY_ACTION:
        data: IsAddrAllowed = self.pendingAddrToBool[_aid]
        extcall MissionControl(mc).setCanPerformSecurityAction(data.addr, data.isAllowed)
        log CanPerformSecurityAction(signer=data.addr, canPerform=data.isAllowed)

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