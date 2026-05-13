#        ______   __     __   __   ______  ______   __  __   ______   ______   ______   ______   _____    
#       /\  ___\ /\ \  _ \ \ /\ \ /\__  _\/\  ___\ /\ \_\ \ /\  == \ /\  __ \ /\  __ \ /\  == \ /\  __-.  
#       \ \___  \\ \ \/ ".\ \\ \ \\/_/\ \/\ \ \____\ \  __ \\ \  __< \ \ \/\ \\ \  __ \\ \  __< \ \ \/\ \ 
#        \/\_____\\ \__/".~\_\\ \_\  \ \_\ \ \_____\\ \_\ \_\\ \_____\\ \_____\\ \_\ \_\\ \_\ \_\\ \____- 
#         \/_____/ \/_/   \/_/ \/_/   \/_/  \/_____/ \/_/\/_/ \/_____/ \/_____/ \/_/\/_/ \/_/ /_/ \/____/ 
#                                                  ┏┓┓  ┓   
#                                                  ┣┫┃┏┓┣┓┏┓
#                                                  ┛┗┗┣┛┛┗┗┻
#                                                     ┛     
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3
# pragma optimize codesize

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
    def setAssetConfig(_asset: address, _config: cs.AssetConfig): nonpayable
    def setIsStablecoin(_asset: address, _isStablecoin: bool): nonpayable
    def setUserWalletConfig(_config: cs.UserWalletConfig): nonpayable
    def canPerformSecurityAction(_signer: address) -> bool: view
    def setManagerConfig(_config: cs.ManagerConfig): nonpayable
    def setChequeConfig(_config: cs.ChequeConfig): nonpayable
    def assetConfig(_asset: address) -> cs.AssetConfig: view
    def setPayeeConfig(_config: cs.PayeeConfig): nonpayable
    def setAgentConfig(_config: cs.AgentConfig): nonpayable
    def userWalletConfig() -> cs.UserWalletConfig: view
    def managerConfig() -> cs.ManagerConfig: view
    def chequeConfig() -> cs.ChequeConfig: view
    def payeeConfig() -> cs.PayeeConfig: view
    def agentConfig() -> cs.AgentConfig: view

interface ChequeBook:
    def isValidUserWalletChequeDefaults(_maxNumActiveCheques: uint256, _instantUsdThreshold: uint256, _periodLength: uint256, _expensiveDelayBlocks: uint256, _defaultExpiryBlocks: uint256, _timeLock: uint256) -> bool: view
    def MAX_UNLOCK_BLOCKS() -> uint256: view
    def MAX_EXPIRY_BLOCKS() -> uint256: view

interface WalletBackpack:
    def highCommand() -> address: view
    def chequeBook() -> address: view
    def paymaster() -> address: view

interface AgentWrapper:
    def removeSender(_sender: address): nonpayable
    def addSender(_sender: address): nonpayable

interface HighCommand:
    def isValidUserWalletManagerDefaults(_managerPeriod: uint256, _timeLock: uint256, _managerActivationLength: uint256, _mustHaveUsdValueOnSwaps: bool, _maxNumSwapsPerPeriod: uint256, _maxSlippageOnSwaps: uint256, _startingAgent: address, _startingAgentActivationLength: uint256, _owner: address) -> bool: view

interface Paymaster:
    def isValidUserWalletPayeeDefaults(_defaultPeriodLength: uint256, _startDelay: uint256, _activationLength: uint256) -> bool: view

flag ActionType:
    USER_WALLET_TEMPLATES
    WALLET_CREATION_LIMITS
    KEY_ACTION_TIMELOCK_BOUNDS
    TX_FEES
    AMBASSADOR_REV_SHARE
    DEFAULT_YIELD_PARAMS
    LOOT_PARAMS
    STARTER_AGENT_PARAMS
    MANAGER_CONFIG
    PAYEE_CONFIG
    ASSET_CONFIG
    ASSET_TX_FEES
    ASSET_AMBASSADOR_REV_SHARE
    ASSET_YIELD_CONFIG
    IS_STABLECOIN
    AGENT_WRAPPER_SENDER
    CHEQUE_CONFIG

struct IsAddrAllowed:
    addr: address
    isAllowed: bool

struct PendingAssetConfig:
    asset: address
    config: cs.AssetConfig

struct PendingAssetTxFees:
    asset: address
    txFees: cs.TxFees

struct PendingAssetAmbassadorRevShare:
    asset: address
    ambassadorRevShare: cs.AmbassadorRevShare

struct PendingAssetYieldConfig:
    asset: address
    yieldConfig: cs.YieldConfig

struct PendingAgentWrapperSender:
    agentWrapper: address
    agentSender: address

event PendingUserWalletTemplatesChange:
    walletTemplate: address
    configTemplate: address
    confirmationBlock: uint256
    actionId: uint256

event UserWalletTemplatesSet:
    walletTemplate: address
    configTemplate: address

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
    defaultYieldBonusAsset: address
    confirmationBlock: uint256
    actionId: uint256

event DefaultYieldParamsSet:
    defaultYieldMaxIncrease: uint256
    defaultYieldPerformanceFee: uint256
    defaultYieldAmbassadorBonusRatio: uint256
    defaultYieldBonusRatio: uint256
    defaultYieldBonusAsset: address

event PendingLootParamsChange:
    depositRewardsAsset: address
    lootClaimCoolOffPeriod: uint256
    confirmationBlock: uint256
    actionId: uint256

event LootParamsSet:
    depositRewardsAsset: address
    lootClaimCoolOffPeriod: uint256

event PendingAssetConfigChange:
    asset: address
    txFeesSwapFee: uint256
    txFeesStableSwapFee: uint256
    txFeesRewardsFee: uint256
    ambassadorRevShareSwapRatio: uint256
    ambassadorRevShareRewardsRatio: uint256
    ambassadorRevShareYieldRatio: uint256
    maxYieldIncrease: uint256
    performanceFee: uint256
    ambassadorBonusRatio: uint256
    bonusRatio: uint256
    bonusAsset: address
    confirmationBlock: uint256
    actionId: uint256

event PendingIsStablecoinChange:
    asset: address
    isStablecoin: bool
    confirmationBlock: uint256
    actionId: uint256

event IsStablecoinSet:
    asset: address
    isStablecoin: bool

event AssetConfigSet:
    asset: address
    txFeesSwapFee: uint256
    txFeesStableSwapFee: uint256
    txFeesRewardsFee: uint256
    ambassadorRevShareSwapRatio: uint256
    ambassadorRevShareRewardsRatio: uint256
    ambassadorRevShareYieldRatio: uint256
    maxYieldIncrease: uint256
    performanceFee: uint256
    ambassadorBonusRatio: uint256
    bonusRatio: uint256
    bonusAsset: address

event PendingAssetTxFeesChange:
    asset: address
    swapFee: uint256
    stableSwapFee: uint256
    rewardsFee: uint256
    confirmationBlock: uint256
    actionId: uint256

event AssetTxFeesSet:
    asset: address
    swapFee: uint256
    stableSwapFee: uint256
    rewardsFee: uint256

event PendingAssetAmbassadorRevShareChange:
    asset: address
    swapRatio: uint256
    rewardsRatio: uint256
    yieldRatio: uint256
    confirmationBlock: uint256
    actionId: uint256

event AssetAmbassadorRevShareSet:
    asset: address
    swapRatio: uint256
    rewardsRatio: uint256
    yieldRatio: uint256

event PendingAssetYieldConfigChange:
    asset: address
    maxYieldIncrease: uint256
    performanceFee: uint256
    ambassadorBonusRatio: uint256
    bonusRatio: uint256
    bonusAsset: address
    confirmationBlock: uint256
    actionId: uint256

event AssetYieldConfigSet:
    asset: address
    maxYieldIncrease: uint256
    performanceFee: uint256
    ambassadorBonusRatio: uint256
    bonusRatio: uint256
    bonusAsset: address

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
    mustHaveUsdValueOnSwaps: bool
    maxNumSwapsPerPeriod: uint256
    maxSlippageOnSwaps: uint256
    onlyApprovedYieldOpps: bool
    confirmationBlock: uint256
    actionId: uint256

event PendingPayeeConfigChange:
    payeePeriod: uint256
    payeeActivationLength: uint256
    confirmationBlock: uint256
    actionId: uint256

event ManagerConfigSet:
    managerPeriod: uint256
    managerActivationLength: uint256

event PayeeConfigSet:
    payeePeriod: uint256
    payeeActivationLength: uint256

event PendingChequeConfigChange:
    maxNumActiveCheques: uint256
    instantUsdThreshold: uint256
    periodLength: uint256
    expensiveDelayBlocks: uint256
    defaultExpiryBlocks: uint256
    confirmationBlock: uint256
    actionId: indexed(uint256)

event ChequeConfigSet:
    maxNumActiveCheques: uint256
    instantUsdThreshold: uint256
    periodLength: uint256
    expensiveDelayBlocks: uint256
    defaultExpiryBlocks: uint256

event PendingAgentWrapperSenderAdd:
    agentWrapper: indexed(address)
    agentSender: indexed(address)
    confirmationBlock: uint256
    actionId: uint256

event AgentWrapperSenderAdded:
    agentWrapper: indexed(address)
    agentSender: indexed(address)

event AgentWrapperSenderRemoved:
    agentWrapper: indexed(address)
    agentSender: indexed(address)

# pending config changes
actionType: public(HashMap[uint256, ActionType]) # aid -> type
pendingUserWalletConfig: public(HashMap[uint256, cs.UserWalletConfig]) # aid -> config
pendingAssetConfig: public(HashMap[uint256, PendingAssetConfig]) # aid -> config
pendingAssetTxFees: public(HashMap[uint256, PendingAssetTxFees]) # aid -> tx fees
pendingAssetAmbassadorRevShare: public(HashMap[uint256, PendingAssetAmbassadorRevShare]) # aid -> ambassador rev share
pendingAssetYieldConfig: public(HashMap[uint256, PendingAssetYieldConfig]) # aid -> yield config
pendingAgentConfig: public(HashMap[uint256, cs.AgentConfig]) # aid -> config
pendingManagerConfig: public(HashMap[uint256, cs.ManagerConfig]) # aid -> config
pendingPayeeConfig: public(HashMap[uint256, cs.PayeeConfig]) # aid -> config
pendingChequeConfig: public(HashMap[uint256, cs.ChequeConfig]) # aid -> config
pendingAddrToBool: public(HashMap[uint256, IsAddrAllowed])
pendingAgentWrapperSender: public(HashMap[uint256, PendingAgentWrapperSender])

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


@view
@internal
def _resolveMissionControl(_missionControl: address) -> address:
    if _missionControl != empty(address):
        return _missionControl
    return addys._getMissionControlAddr()


######################
# User Wallet Config #
######################


# user wallet templates


@external
def setUserWalletTemplates(_walletTemplate: address, _configTemplate: address, _missionControl: address = empty(address)) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms

    mc: address = self._resolveMissionControl(_missionControl)
    assert self._areValidUserWalletTemplates(_walletTemplate, _configTemplate) # dev: invalid user wallet templates
    return self._setPendingUserWalletConfig(ActionType.USER_WALLET_TEMPLATES, mc, _walletTemplate, _configTemplate)


@view
@internal
def _areValidUserWalletTemplates(_walletTemplate: address, _configTemplate: address) -> bool:
    if empty(address) in [_walletTemplate, _configTemplate]:
        return False
    if not _walletTemplate.is_contract or not _configTemplate.is_contract:
        return False
    return True


# wallet creation limits


@external
def setWalletCreationLimits(_numUserWalletsAllowed: uint256, _enforceCreatorWhitelist: bool, _missionControl: address = empty(address)) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms

    mc: address = self._resolveMissionControl(_missionControl)
    assert self._isValidNumUserWalletsAllowed(_numUserWalletsAllowed) # dev: invalid num user wallets allowed
    return self._setPendingUserWalletConfig(
        ActionType.WALLET_CREATION_LIMITS,
        mc,
        empty(address),
        empty(address),
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
def setKeyActionTimelockBounds(_minKeyActionTimeLock: uint256, _maxKeyActionTimeLock: uint256, _missionControl: address = empty(address)) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms

    mc: address = self._resolveMissionControl(_missionControl)
    assert self._areValidKeyActionTimelockBounds(_minKeyActionTimeLock, _maxKeyActionTimeLock) # dev: invalid key action timelock bounds
    assert self._isWalletCreationConfigCoherent(mc, _minKeyActionTimeLock, _maxKeyActionTimeLock) # dev: invalid wallet creation config
    return self._setPendingUserWalletConfig(
        ActionType.KEY_ACTION_TIMELOCK_BOUNDS,
        mc,
        empty(address),
        empty(address),
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


# tx fees


@external
def setTxFees(_swapFee: uint256, _stableSwapFee: uint256, _rewardsFee: uint256, _missionControl: address = empty(address)) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms

    mc: address = self._resolveMissionControl(_missionControl)
    assert self._areValidTxFees(_swapFee, _stableSwapFee, _rewardsFee) # dev: invalid tx fees
    return self._setPendingUserWalletConfig(
        ActionType.TX_FEES,
        mc,
        empty(address),
        empty(address),
        0,
        False,
        0,
        0,
        empty(address),
        0,
        _swapFee,
        _stableSwapFee,
        _rewardsFee
    )


@view
@internal
def _areValidTxFees(_swapFee: uint256, _stableSwapFee: uint256, _rewardsFee: uint256) -> bool:
    if _swapFee > 5_00: # 5% max
        return False
    if _stableSwapFee > 2_00: # 2% max
        return False
    if _rewardsFee > 25_00: # 25% max
        return False
    return True


# ambassador rev share


@external
def setAmbassadorRevShare(_swapRatio: uint256, _rewardsRatio: uint256, _yieldRatio: uint256, _missionControl: address = empty(address)) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms

    mc: address = self._resolveMissionControl(_missionControl)
    assert self._areValidAmbassadorRevShareRatios(_swapRatio, _rewardsRatio, _yieldRatio) # dev: invalid ambassador rev share ratios
    return self._setPendingUserWalletConfig(
        ActionType.AMBASSADOR_REV_SHARE,
        mc,
        empty(address),
        empty(address),
        0,
        False,
        0,
        0,
        empty(address),
        0,
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
    _defaultYieldBonusAsset: address,
    _missionControl: address = empty(address)
) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms

    mc: address = self._resolveMissionControl(_missionControl)
    assert self._areValidYieldParams(
        _defaultYieldMaxIncrease,
        _defaultYieldPerformanceFee,
        _defaultYieldAmbassadorBonusRatio,
        _defaultYieldBonusRatio
    ) # dev: invalid default yield params

    return self._setPendingUserWalletConfig(
        ActionType.DEFAULT_YIELD_PARAMS,
        mc,
        empty(address),
        empty(address),
        0,
        False,
        0,
        0,
        empty(address),
        0,
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
        _defaultYieldBonusAsset
    )


@view
@internal
def _areValidYieldParams(
    _maxIncrease: uint256,
    _performanceFee: uint256,
    _ambassadorBonusRatio: uint256,
    _bonusRatio: uint256
) -> bool:
    if _maxIncrease > 10_00: # 10% max
        return False
    if _performanceFee > 25_00: # 25% max
        return False
    if _ambassadorBonusRatio > HUNDRED_PERCENT:
        return False
    if _bonusRatio > HUNDRED_PERCENT:
        return False
    return True


# loot params


@external
def setLootParams(_depositRewardsAsset: address, _lootClaimCoolOffPeriod: uint256, _missionControl: address = empty(address)) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms

    mc: address = self._resolveMissionControl(_missionControl)
    assert self._areValidLootParams(_lootClaimCoolOffPeriod) # dev: invalid loot params
    return self._setPendingUserWalletConfig(
        ActionType.LOOT_PARAMS,
        mc,
        empty(address),
        empty(address),
        0,
        False,
        0,
        0,
        _depositRewardsAsset,
        _lootClaimCoolOffPeriod,
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
        empty(address)
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
# Asset Config #
################


@external
def setAssetConfig(
    _asset: address,
    _txFeesSwapFee: uint256,
    _txFeesStableSwapFee: uint256,
    _txFeesRewardsFee: uint256,
    _ambassadorRevShareSwapRatio: uint256,
    _ambassadorRevShareRewardsRatio: uint256,
    _ambassadorRevShareYieldRatio: uint256,
    _maxYieldIncrease: uint256,
    _performanceFee: uint256,
    _ambassadorBonusRatio: uint256,
    _bonusRatio: uint256,
    _bonusAsset: address,
    _missionControl: address = empty(address)
) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms

    mc: address = self._resolveMissionControl(_missionControl)
    assert self._isValidAssetConfig(
        _asset,
        _txFeesSwapFee,
        _txFeesStableSwapFee,
        _txFeesRewardsFee,
        _ambassadorRevShareSwapRatio,
        _ambassadorRevShareRewardsRatio,
        _ambassadorRevShareYieldRatio,
        _maxYieldIncrease,
        _performanceFee,
        _ambassadorBonusRatio,
        _bonusRatio,
        _bonusAsset
    ) # dev: invalid asset config

    yieldConfig: cs.YieldConfig = cs.YieldConfig(
        maxYieldIncrease=_maxYieldIncrease,
        performanceFee=_performanceFee,
        ambassadorBonusRatio=_ambassadorBonusRatio,
        bonusRatio=_bonusRatio,
        bonusAsset=_bonusAsset
    )

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.ASSET_CONFIG
    self.pendingAssetConfig[aid] = PendingAssetConfig(
        asset=_asset,
        config=cs.AssetConfig(
            hasConfig=True,
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
            yieldConfig=yieldConfig,
        )
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingAssetConfigChange(
        asset=_asset,
        txFeesSwapFee=_txFeesSwapFee,
        txFeesStableSwapFee=_txFeesStableSwapFee,
        txFeesRewardsFee=_txFeesRewardsFee,
        ambassadorRevShareSwapRatio=_ambassadorRevShareSwapRatio,
        ambassadorRevShareRewardsRatio=_ambassadorRevShareRewardsRatio,
        ambassadorRevShareYieldRatio=_ambassadorRevShareYieldRatio,
        maxYieldIncrease=_maxYieldIncrease,
        performanceFee=_performanceFee,
        ambassadorBonusRatio=_ambassadorBonusRatio,
        bonusRatio=_bonusRatio,
        bonusAsset=_bonusAsset,
        confirmationBlock=confirmationBlock,
        actionId=aid,
    )
    return aid


@view
@internal
def _isValidAssetConfig(
    _asset: address,
    _txFeesSwapFee: uint256,
    _txFeesStableSwapFee: uint256,
    _txFeesRewardsFee: uint256,
    _ambassadorRevShareSwapRatio: uint256,
    _ambassadorRevShareRewardsRatio: uint256,
    _ambassadorRevShareYieldRatio: uint256,
    _maxYieldIncrease: uint256,
    _performanceFee: uint256,
    _ambassadorBonusRatio: uint256,
    _bonusRatio: uint256,
    _bonusAsset: address
) -> bool:
    if _asset == empty(address):
        return False

    if not self._areValidTxFees(_txFeesSwapFee, _txFeesStableSwapFee, _txFeesRewardsFee):
        return False

    if not self._areValidAmbassadorRevShareRatios(_ambassadorRevShareSwapRatio, _ambassadorRevShareRewardsRatio, _ambassadorRevShareYieldRatio):
        return False

    if not self._areValidYieldParams(_maxYieldIncrease, _performanceFee, _ambassadorBonusRatio, _bonusRatio):
        return False

    return True


# granular asset config setters


@external
def setAssetTxFees(
    _asset: address,
    _swapFee: uint256,
    _stableSwapFee: uint256,
    _rewardsFee: uint256,
    _missionControl: address = empty(address)
) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    assert _asset != empty(address) # dev: invalid asset

    # Ensure full asset config has been set first
    mc: address = self._resolveMissionControl(_missionControl)
    existingConfig: cs.AssetConfig = staticcall MissionControl(mc).assetConfig(_asset)
    assert existingConfig.hasConfig # dev: must set full asset config first

    assert self._areValidTxFees(_swapFee, _stableSwapFee, _rewardsFee) # dev: invalid tx fees

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.ASSET_TX_FEES
    self.pendingAssetTxFees[aid] = PendingAssetTxFees(
        asset=_asset,
        txFees=cs.TxFees(
            swapFee=_swapFee,
            stableSwapFee=_stableSwapFee,
            rewardsFee=_rewardsFee
        )
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingAssetTxFeesChange(
        asset=_asset,
        swapFee=_swapFee,
        stableSwapFee=_stableSwapFee,
        rewardsFee=_rewardsFee,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


@external
def setAssetAmbassadorRevShare(
    _asset: address,
    _swapRatio: uint256,
    _rewardsRatio: uint256,
    _yieldRatio: uint256,
    _missionControl: address = empty(address)
) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    assert _asset != empty(address) # dev: invalid asset

    # Ensure full asset config has been set first
    mc: address = self._resolveMissionControl(_missionControl)
    existingConfig: cs.AssetConfig = staticcall MissionControl(mc).assetConfig(_asset)
    assert existingConfig.hasConfig # dev: must set full asset config first

    assert self._areValidAmbassadorRevShareRatios(_swapRatio, _rewardsRatio, _yieldRatio) # dev: invalid ratios

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.ASSET_AMBASSADOR_REV_SHARE
    self.pendingAssetAmbassadorRevShare[aid] = PendingAssetAmbassadorRevShare(
        asset=_asset,
        ambassadorRevShare=cs.AmbassadorRevShare(
            swapRatio=_swapRatio,
            rewardsRatio=_rewardsRatio,
            yieldRatio=_yieldRatio
        )
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingAssetAmbassadorRevShareChange(
        asset=_asset,
        swapRatio=_swapRatio,
        rewardsRatio=_rewardsRatio,
        yieldRatio=_yieldRatio,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


@external
def setAssetYieldConfig(
    _asset: address,
    _maxYieldIncrease: uint256,
    _performanceFee: uint256,
    _ambassadorBonusRatio: uint256,
    _bonusRatio: uint256,
    _bonusAsset: address,
    _missionControl: address = empty(address)
) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    assert _asset != empty(address) # dev: invalid asset

    # Ensure full asset config has been set first
    mc: address = self._resolveMissionControl(_missionControl)
    existingConfig: cs.AssetConfig = staticcall MissionControl(mc).assetConfig(_asset)
    assert existingConfig.hasConfig # dev: must set full asset config first

    assert self._areValidYieldParams(_maxYieldIncrease, _performanceFee, _ambassadorBonusRatio, _bonusRatio) # dev: invalid yield params

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.ASSET_YIELD_CONFIG
    self.pendingAssetYieldConfig[aid] = PendingAssetYieldConfig(
        asset=_asset,
        yieldConfig=cs.YieldConfig(
            maxYieldIncrease=_maxYieldIncrease,
            performanceFee=_performanceFee,
            ambassadorBonusRatio=_ambassadorBonusRatio,
            bonusRatio=_bonusRatio,
            bonusAsset=_bonusAsset
        )
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingAssetYieldConfigChange(
        asset=_asset,
        maxYieldIncrease=_maxYieldIncrease,
        performanceFee=_performanceFee,
        ambassadorBonusRatio=_ambassadorBonusRatio,
        bonusRatio=_bonusRatio,
        bonusAsset=_bonusAsset,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


# is stablecoin


@external
def setIsStablecoin(_asset: address, _isStablecoin: bool, _missionControl: address = empty(address)) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms

    mc: address = self._resolveMissionControl(_missionControl)
    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.IS_STABLECOIN
    self.pendingAddrToBool[aid] = IsAddrAllowed(addr=_asset, isAllowed=_isStablecoin)
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingIsStablecoinChange(asset=_asset, isStablecoin=_isStablecoin, confirmationBlock=confirmationBlock, actionId=aid)
    return aid


################
# Agent Config #
################


# starter agent params


@external
def setStarterAgentParams(_startingAgent: address, _startingAgentActivationLength: uint256, _missionControl: address = empty(address)) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms

    mc: address = self._resolveMissionControl(_missionControl)
    assert self._areValidStarterAgentParams(_startingAgent, _startingAgentActivationLength) # dev: invalid starter agent params
    return self._setPendingAgentConfig(
        mc,
        _startingAgent,
        _startingAgentActivationLength
    )


@view
@internal
def _areValidStarterAgentParams(_startingAgent: address, _startingAgentActivationLength: uint256) -> bool:
    if _startingAgent != empty(address) and _startingAgentActivationLength == 0:
        return False
    if _startingAgent == empty(address) and _startingAgentActivationLength != 0:
        return False
    if _startingAgentActivationLength == max_value(uint256):
        return False
    return True


# agent wrapper sender


@external
def setAgentWrapperSender(_agentWrapper: address, _agentSender: address, _shouldAdd: bool) -> uint256:
    assert self._hasPermsToEnable(msg.sender, _shouldAdd) # dev: no perms
    assert _agentWrapper != empty(address) # dev: invalid agent wrapper
    assert _agentSender != empty(address) # dev: invalid agent sender

    # when removing, execute immediately
    if not _shouldAdd:
        extcall AgentWrapper(_agentWrapper).removeSender(_agentSender)
        log AgentWrapperSenderRemoved(agentWrapper=_agentWrapper, agentSender=_agentSender)
        return 0

    # when adding, use timelock
    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.AGENT_WRAPPER_SENDER
    self.pendingAgentWrapperSender[aid] = PendingAgentWrapperSender(
        agentWrapper=_agentWrapper,
        agentSender=_agentSender
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingAgentWrapperSenderAdd(
        agentWrapper=_agentWrapper,
        agentSender=_agentSender,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


##################
# Manager Config #
##################


@external
def setManagerConfig(
    _managerPeriod: uint256,
    _managerActivationLength: uint256,
    _mustHaveUsdValueOnSwaps: bool,
    _maxNumSwapsPerPeriod: uint256,
    _maxSlippageOnSwaps: uint256,
    _onlyApprovedYieldOpps: bool,
    _missionControl: address = empty(address)
) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms

    mc: address = self._resolveMissionControl(_missionControl)
    assert 0 not in [_managerPeriod, _managerActivationLength] # dev: invalid manager config
    assert max_value(uint256) not in [_managerPeriod, _managerActivationLength] # dev: invalid manager config
    config: cs.ManagerConfig = cs.ManagerConfig(
        managerPeriod=_managerPeriod,
        managerActivationLength=_managerActivationLength,
        mustHaveUsdValueOnSwaps=_mustHaveUsdValueOnSwaps,
        maxNumSwapsPerPeriod=_maxNumSwapsPerPeriod,
        maxSlippageOnSwaps=_maxSlippageOnSwaps,
        onlyApprovedYieldOpps=_onlyApprovedYieldOpps,
    )
    walletConfig: cs.UserWalletConfig = staticcall MissionControl(mc).userWalletConfig()
    assert self._isManagerConfigCoherentForWalletCreation(mc, config, walletConfig.minKeyActionTimeLock) # dev: invalid manager defaults under timelock

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.MANAGER_CONFIG
    self.pendingManagerConfig[aid] = config
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingManagerConfigChange(
        managerPeriod=_managerPeriod,
        managerActivationLength=_managerActivationLength,
        mustHaveUsdValueOnSwaps=_mustHaveUsdValueOnSwaps,
        maxNumSwapsPerPeriod=_maxNumSwapsPerPeriod,
        maxSlippageOnSwaps=_maxSlippageOnSwaps,
        onlyApprovedYieldOpps=_onlyApprovedYieldOpps,
        confirmationBlock=confirmationBlock,
        actionId=aid,
    )
    return aid


################
# Payee Config #
################


@external
def setPayeeConfig(_payeePeriod: uint256, _payeeActivationLength: uint256, _missionControl: address = empty(address)) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms

    mc: address = self._resolveMissionControl(_missionControl)
    assert 0 not in [_payeePeriod, _payeeActivationLength] # dev: invalid payee config
    assert max_value(uint256) not in [_payeePeriod, _payeeActivationLength] # dev: invalid payee config
    config: cs.PayeeConfig = cs.PayeeConfig(
        payeePeriod=_payeePeriod,
        payeeActivationLength=_payeeActivationLength
    )
    walletConfig: cs.UserWalletConfig = staticcall MissionControl(mc).userWalletConfig()
    assert self._isPayeeConfigCoherentForWalletCreation(config, walletConfig.minKeyActionTimeLock) # dev: invalid payee defaults under timelock

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.PAYEE_CONFIG
    self.pendingPayeeConfig[aid] = config
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingPayeeConfigChange(
        payeePeriod=_payeePeriod,
        payeeActivationLength=_payeeActivationLength,
        confirmationBlock=confirmationBlock,
        actionId=aid,
    )
    return aid


#################
# Cheque Config #
#################


@external
def setChequeConfig(
    _maxNumActiveCheques: uint256,
    _instantUsdThreshold: uint256,
    _periodLength: uint256,
    _expensiveDelayBlocks: uint256,
    _defaultExpiryBlocks: uint256,
    _missionControl: address = empty(address),
) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms

    mc: address = self._resolveMissionControl(_missionControl)
    config: cs.ChequeConfig = cs.ChequeConfig(
        maxNumActiveCheques=_maxNumActiveCheques,
        instantUsdThreshold=_instantUsdThreshold,
        periodLength=_periodLength,
        expensiveDelayBlocks=_expensiveDelayBlocks,
        defaultExpiryBlocks=_defaultExpiryBlocks,
    )
    chequeBook: address = self._getCurrentChequeBook()
    assert self._isValidChequeConfig(mc, chequeBook, config) # dev: invalid cheque config

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.CHEQUE_CONFIG
    self.pendingChequeConfig[aid] = config
    log PendingChequeConfigChange(
        maxNumActiveCheques=_maxNumActiveCheques,
        instantUsdThreshold=_instantUsdThreshold,
        periodLength=_periodLength,
        expensiveDelayBlocks=_expensiveDelayBlocks,
        defaultExpiryBlocks=_defaultExpiryBlocks,
        confirmationBlock=timeLock._getActionConfirmationBlock(aid),
        actionId=aid,
    )
    return aid


@view
@internal
def _getCurrentChequeBook() -> address:
    walletBackpack: address = addys._getWalletBackpackAddr()
    return staticcall WalletBackpack(walletBackpack).chequeBook()


@view
@internal
def _isValidChequeConfig(_missionControl: address, _chequeBook: address, _config: cs.ChequeConfig) -> bool:
    walletConfig: cs.UserWalletConfig = staticcall MissionControl(_missionControl).userWalletConfig()
    return staticcall ChequeBook(_chequeBook).isValidUserWalletChequeDefaults(
        _config.maxNumActiveCheques,
        _config.instantUsdThreshold,
        _config.periodLength,
        _config.expensiveDelayBlocks,
        _config.defaultExpiryBlocks,
        walletConfig.minKeyActionTimeLock,
    )


# Cross-validation against live wallet-creation state


@view
@internal
def _isWalletCreationConfigCoherent(
    _missionControl: address,
    _minKeyActionTimeLock: uint256,
    _maxKeyActionTimeLock: uint256,
) -> bool:
    walletBackpack: address = addys._getWalletBackpackAddr()
    if walletBackpack == empty(address):
        return False

    highCommand: address = staticcall WalletBackpack(walletBackpack).highCommand()
    paymaster: address = staticcall WalletBackpack(walletBackpack).paymaster()
    chequeBook: address = staticcall WalletBackpack(walletBackpack).chequeBook()
    if empty(address) in [highCommand, paymaster, chequeBook]:
        return False

    managerConfig: cs.ManagerConfig = staticcall MissionControl(_missionControl).managerConfig()
    payeeConfig: cs.PayeeConfig = staticcall MissionControl(_missionControl).payeeConfig()
    chequeConfig: cs.ChequeConfig = staticcall MissionControl(_missionControl).chequeConfig()
    agentConfig: cs.AgentConfig = staticcall MissionControl(_missionControl).agentConfig()

    if not self._isManagerConfigValidForWalletCreation(
        highCommand,
        managerConfig,
        agentConfig,
        _minKeyActionTimeLock,
    ):
        return False

    if not self._isPayeeConfigValidForWalletCreation(
        paymaster,
        payeeConfig,
        _minKeyActionTimeLock,
    ):
        return False

    if not self._isChequeConfigValidForWalletCreation(
        chequeBook,
        chequeConfig,
        _minKeyActionTimeLock,
    ):
        return False

    if _maxKeyActionTimeLock > staticcall ChequeBook(chequeBook).MAX_UNLOCK_BLOCKS():
        return False
    if _maxKeyActionTimeLock > staticcall ChequeBook(chequeBook).MAX_EXPIRY_BLOCKS():
        return False
    return True


@view
@internal
def _isManagerConfigCoherentForWalletCreation(
    _missionControl: address,
    _config: cs.ManagerConfig,
    _minKeyActionTimeLock: uint256,
) -> bool:
    walletBackpack: address = addys._getWalletBackpackAddr()
    if walletBackpack == empty(address):
        return False
    highCommand: address = staticcall WalletBackpack(walletBackpack).highCommand()
    if highCommand == empty(address):
        return False
    agentConfig: cs.AgentConfig = staticcall MissionControl(_missionControl).agentConfig()

    return self._isManagerConfigValidForWalletCreation(
        highCommand,
        _config,
        agentConfig,
        _minKeyActionTimeLock,
    )


@view
@internal
def _isPayeeConfigCoherentForWalletCreation(_config: cs.PayeeConfig, _minKeyActionTimeLock: uint256) -> bool:
    walletBackpack: address = addys._getWalletBackpackAddr()
    if walletBackpack == empty(address):
        return False
    paymaster: address = staticcall WalletBackpack(walletBackpack).paymaster()
    if paymaster == empty(address):
        return False
    return self._isPayeeConfigValidForWalletCreation(
        paymaster,
        _config,
        _minKeyActionTimeLock,
    )


@view
@internal
def _isManagerConfigValidForWalletCreation(
    _highCommand: address,
    _config: cs.ManagerConfig,
    _agentConfig: cs.AgentConfig,
    _minKeyActionTimeLock: uint256,
) -> bool:
    # Passing empty(address) intentionally bypasses only the starter-agent-vs-owner collision check.
    # That check is per-wallet and cannot be globally validated during governance config.
    # Hatchery still enforces the real owner-specific check at createUserWallet time.
    return staticcall HighCommand(_highCommand).isValidUserWalletManagerDefaults(
        _config.managerPeriod,
        _minKeyActionTimeLock,
        _config.managerActivationLength,
        _config.mustHaveUsdValueOnSwaps,
        _config.maxNumSwapsPerPeriod,
        _config.maxSlippageOnSwaps,
        _agentConfig.startingAgent,
        _agentConfig.startingAgentActivationLength,
        empty(address),
    )


@view
@internal
def _isPayeeConfigValidForWalletCreation(
    _paymaster: address,
    _config: cs.PayeeConfig,
    _minKeyActionTimeLock: uint256,
) -> bool:
    return staticcall Paymaster(_paymaster).isValidUserWalletPayeeDefaults(
        _config.payeePeriod,
        _minKeyActionTimeLock,
        _config.payeeActivationLength,
    )


@view
@internal
def _isChequeConfigValidForWalletCreation(
    _chequeBook: address,
    _config: cs.ChequeConfig,
    _minKeyActionTimeLock: uint256,
) -> bool:
    return staticcall ChequeBook(_chequeBook).isValidUserWalletChequeDefaults(
        _config.maxNumActiveCheques,
        _config.instantUsdThreshold,
        _config.periodLength,
        _config.expensiveDelayBlocks,
        _config.defaultExpiryBlocks,
        _minKeyActionTimeLock,
    )


###############
# Set Pending #
###############


@internal
def _setPendingUserWalletConfig(
    _actionType: ActionType,
    _missionControl: address,
    _walletTemplate: address = empty(address),
    _configTemplate: address = empty(address),
    _numUserWalletsAllowed: uint256 = 0,
    _enforceCreatorWhitelist: bool = False,
    _minKeyActionTimeLock: uint256 = 0,
    _maxKeyActionTimeLock: uint256 = 0,
    _depositRewardsAsset: address = empty(address),
    _lootClaimCoolOffPeriod: uint256 = 0,
    _txFeesSwapFee: uint256 = 0,
    _txFeesStableSwapFee: uint256 = 0,
    _txFeesRewardsFee: uint256 = 0,
    _ambassadorRevShareSwapRatio: uint256 = 0,
    _ambassadorRevShareRewardsRatio: uint256 = 0,
    _ambassadorRevShareYieldRatio: uint256 = 0,
    _yieldMaxIncrease: uint256 = 0,
    _yieldPerformanceFee: uint256 = 0,
    _yieldAmbassadorBonusRatio: uint256 = 0,
    _yieldBonusRatio: uint256 = 0,
    _yieldBonusAsset: address = empty(address),
) -> uint256:
    aid: uint256 = timeLock._initiateAction()

    self.actionType[aid] = _actionType
    self.pendingUserWalletConfig[aid] = cs.UserWalletConfig(
        walletTemplate=_walletTemplate,
        configTemplate=_configTemplate,
        numUserWalletsAllowed=_numUserWalletsAllowed,
        enforceCreatorWhitelist=_enforceCreatorWhitelist,
        minKeyActionTimeLock=_minKeyActionTimeLock,
        maxKeyActionTimeLock=_maxKeyActionTimeLock,
        depositRewardsAsset=_depositRewardsAsset,
        lootClaimCoolOffPeriod=_lootClaimCoolOffPeriod,
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
        yieldConfig=cs.YieldConfig(
            maxYieldIncrease=_yieldMaxIncrease,
            performanceFee=_yieldPerformanceFee,
            ambassadorBonusRatio=_yieldAmbassadorBonusRatio,
            bonusRatio=_yieldBonusRatio,
            bonusAsset=_yieldBonusAsset,
        ),
    )

    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    if _actionType == ActionType.USER_WALLET_TEMPLATES:
        log PendingUserWalletTemplatesChange(
            walletTemplate=_walletTemplate,
            configTemplate=_configTemplate,
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
            defaultYieldMaxIncrease=_yieldMaxIncrease,
            defaultYieldPerformanceFee=_yieldPerformanceFee,
            defaultYieldAmbassadorBonusRatio=_yieldAmbassadorBonusRatio,
            defaultYieldBonusRatio=_yieldBonusRatio,
            defaultYieldBonusAsset=_yieldBonusAsset,
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
    _missionControl: address,
    _startingAgent: address,
    _startingAgentActivationLength: uint256,
) -> uint256:
    aid: uint256 = timeLock._initiateAction()

    self.actionType[aid] = ActionType.STARTER_AGENT_PARAMS
    self.pendingAgentConfig[aid] = cs.AgentConfig(
        startingAgent=_startingAgent,
        startingAgentActivationLength=_startingAgentActivationLength,
    )

    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
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

    elif actionType == ActionType.WALLET_CREATION_LIMITS:
        config: cs.UserWalletConfig = staticcall MissionControl(mc).userWalletConfig()
        p: cs.UserWalletConfig = self.pendingUserWalletConfig[_aid]
        config.numUserWalletsAllowed = p.numUserWalletsAllowed
        config.enforceCreatorWhitelist = p.enforceCreatorWhitelist
        extcall MissionControl(mc).setUserWalletConfig(config)
        log WalletCreationLimitsSet(numUserWalletsAllowed=p.numUserWalletsAllowed, enforceCreatorWhitelist=p.enforceCreatorWhitelist)

    elif actionType == ActionType.KEY_ACTION_TIMELOCK_BOUNDS:
        p: cs.UserWalletConfig = self.pendingUserWalletConfig[_aid]
        assert self._isWalletCreationConfigCoherent(mc, p.minKeyActionTimeLock, p.maxKeyActionTimeLock) # dev: invalid wallet creation config
        config: cs.UserWalletConfig = staticcall MissionControl(mc).userWalletConfig()
        config.minKeyActionTimeLock = p.minKeyActionTimeLock
        config.maxKeyActionTimeLock = p.maxKeyActionTimeLock
        extcall MissionControl(mc).setUserWalletConfig(config)
        log KeyActionTimelockBoundsSet(minKeyActionTimeLock=p.minKeyActionTimeLock, maxKeyActionTimeLock=p.maxKeyActionTimeLock)

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
        config.yieldConfig = p.yieldConfig
        extcall MissionControl(mc).setUserWalletConfig(config)
        log DefaultYieldParamsSet(
            defaultYieldMaxIncrease=p.yieldConfig.maxYieldIncrease,
            defaultYieldPerformanceFee=p.yieldConfig.performanceFee,
            defaultYieldAmbassadorBonusRatio=p.yieldConfig.ambassadorBonusRatio,
            defaultYieldBonusRatio=p.yieldConfig.bonusRatio,
            defaultYieldBonusAsset=p.yieldConfig.bonusAsset
        )

    elif actionType == ActionType.LOOT_PARAMS:
        config: cs.UserWalletConfig = staticcall MissionControl(mc).userWalletConfig()
        p: cs.UserWalletConfig = self.pendingUserWalletConfig[_aid]
        config.depositRewardsAsset = p.depositRewardsAsset
        config.lootClaimCoolOffPeriod = p.lootClaimCoolOffPeriod
        extcall MissionControl(mc).setUserWalletConfig(config)
        log LootParamsSet(depositRewardsAsset=p.depositRewardsAsset, lootClaimCoolOffPeriod=p.lootClaimCoolOffPeriod)

    elif actionType == ActionType.ASSET_CONFIG:
        p: PendingAssetConfig = self.pendingAssetConfig[_aid]
        extcall MissionControl(mc).setAssetConfig(p.asset, p.config)
        log AssetConfigSet(
            asset=p.asset,
            txFeesSwapFee=p.config.txFees.swapFee,
            txFeesStableSwapFee=p.config.txFees.stableSwapFee,
            txFeesRewardsFee=p.config.txFees.rewardsFee,
            ambassadorRevShareSwapRatio=p.config.ambassadorRevShare.swapRatio,
            ambassadorRevShareRewardsRatio=p.config.ambassadorRevShare.rewardsRatio,
            ambassadorRevShareYieldRatio=p.config.ambassadorRevShare.yieldRatio,
            maxYieldIncrease=p.config.yieldConfig.maxYieldIncrease,
            performanceFee=p.config.yieldConfig.performanceFee,
            ambassadorBonusRatio=p.config.yieldConfig.ambassadorBonusRatio,
            bonusRatio=p.config.yieldConfig.bonusRatio,
            bonusAsset=p.config.yieldConfig.bonusAsset,
        )

    elif actionType == ActionType.ASSET_TX_FEES:
        p: PendingAssetTxFees = self.pendingAssetTxFees[_aid]
        config: cs.AssetConfig = staticcall MissionControl(mc).assetConfig(p.asset)
        config.txFees = p.txFees
        extcall MissionControl(mc).setAssetConfig(p.asset, config)
        log AssetTxFeesSet(
            asset=p.asset,
            swapFee=p.txFees.swapFee,
            stableSwapFee=p.txFees.stableSwapFee,
            rewardsFee=p.txFees.rewardsFee
        )

    elif actionType == ActionType.ASSET_AMBASSADOR_REV_SHARE:
        p: PendingAssetAmbassadorRevShare = self.pendingAssetAmbassadorRevShare[_aid]
        config: cs.AssetConfig = staticcall MissionControl(mc).assetConfig(p.asset)
        config.ambassadorRevShare = p.ambassadorRevShare
        extcall MissionControl(mc).setAssetConfig(p.asset, config)
        log AssetAmbassadorRevShareSet(
            asset=p.asset,
            swapRatio=p.ambassadorRevShare.swapRatio,
            rewardsRatio=p.ambassadorRevShare.rewardsRatio,
            yieldRatio=p.ambassadorRevShare.yieldRatio
        )

    elif actionType == ActionType.ASSET_YIELD_CONFIG:
        p: PendingAssetYieldConfig = self.pendingAssetYieldConfig[_aid]
        config: cs.AssetConfig = staticcall MissionControl(mc).assetConfig(p.asset)
        config.yieldConfig = p.yieldConfig
        extcall MissionControl(mc).setAssetConfig(p.asset, config)
        log AssetYieldConfigSet(
            asset=p.asset,
            maxYieldIncrease=p.yieldConfig.maxYieldIncrease,
            performanceFee=p.yieldConfig.performanceFee,
            ambassadorBonusRatio=p.yieldConfig.ambassadorBonusRatio,
            bonusRatio=p.yieldConfig.bonusRatio,
            bonusAsset=p.yieldConfig.bonusAsset
        )

    elif actionType == ActionType.IS_STABLECOIN:
        p: IsAddrAllowed = self.pendingAddrToBool[_aid]
        extcall MissionControl(mc).setIsStablecoin(p.addr, p.isAllowed)
        log IsStablecoinSet(asset=p.addr, isStablecoin=p.isAllowed)

    elif actionType == ActionType.STARTER_AGENT_PARAMS:
        p: cs.AgentConfig = self.pendingAgentConfig[_aid]
        extcall MissionControl(mc).setAgentConfig(p)
        log StarterAgentParamsSet(startingAgent=p.startingAgent, startingAgentActivationLength=p.startingAgentActivationLength)

    elif actionType == ActionType.MANAGER_CONFIG:
        p: cs.ManagerConfig = self.pendingManagerConfig[_aid]
        walletConfig: cs.UserWalletConfig = staticcall MissionControl(mc).userWalletConfig()
        assert self._isManagerConfigCoherentForWalletCreation(mc, p, walletConfig.minKeyActionTimeLock) # dev: invalid manager defaults under timelock
        extcall MissionControl(mc).setManagerConfig(p)
        log ManagerConfigSet(managerPeriod=p.managerPeriod, managerActivationLength=p.managerActivationLength)

    elif actionType == ActionType.PAYEE_CONFIG:
        p: cs.PayeeConfig = self.pendingPayeeConfig[_aid]
        walletConfig: cs.UserWalletConfig = staticcall MissionControl(mc).userWalletConfig()
        assert self._isPayeeConfigCoherentForWalletCreation(p, walletConfig.minKeyActionTimeLock) # dev: invalid payee defaults under timelock
        extcall MissionControl(mc).setPayeeConfig(p)
        log PayeeConfigSet(payeePeriod=p.payeePeriod, payeeActivationLength=p.payeeActivationLength)

    elif actionType == ActionType.CHEQUE_CONFIG:
        p: cs.ChequeConfig = self.pendingChequeConfig[_aid]
        chequeBook: address = self._getCurrentChequeBook()
        assert self._isValidChequeConfig(mc, chequeBook, p) # dev: invalid cheque config
        extcall MissionControl(mc).setChequeConfig(p)
        log ChequeConfigSet(
            maxNumActiveCheques=p.maxNumActiveCheques,
            instantUsdThreshold=p.instantUsdThreshold,
            periodLength=p.periodLength,
            expensiveDelayBlocks=p.expensiveDelayBlocks,
            defaultExpiryBlocks=p.defaultExpiryBlocks,
        )

    elif actionType == ActionType.AGENT_WRAPPER_SENDER:
        p: PendingAgentWrapperSender = self.pendingAgentWrapperSender[_aid]
        extcall AgentWrapper(p.agentWrapper).addSender(p.agentSender)
        log AgentWrapperSenderAdded(agentWrapper=p.agentWrapper, agentSender=p.agentSender)

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
