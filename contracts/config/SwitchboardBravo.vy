#        ______   __     __   __   ______  ______   __  __   ______   ______   ______   ______   _____    
#       /\  ___\ /\ \  _ \ \ /\ \ /\__  _\/\  ___\ /\ \_\ \ /\  == \ /\  __ \ /\  __ \ /\  == \ /\  __-.  
#       \ \___  \\ \ \/ ".\ \\ \ \\/_/\ \/\ \ \____\ \  __ \\ \  __< \ \ \/\ \\ \  __ \\ \  __< \ \ \/\ \ 
#        \/\_____\\ \__/".~\_\\ \_\  \ \_\ \ \_____\\ \_\ \_\\ \_____\\ \_____\\ \_\ \_\\ \_\ \_\\ \____- 
#         \/_____/ \/_/   \/_/ \/_/   \/_/  \/_____/ \/_/\/_/ \/_____/ \/_____/ \/_/\/_/ \/_/ /_/ \/____/ 
#                                                   ┳┓        
#                                                   ┣┫┏┓┏┓┓┏┏┓
#                                                   ┻┛┛ ┗┻┗┛┗┛
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
import interfaces.WalletConfigStructs as wcs

interface Migrator:
    def migrateAll(_fromWallet: address, _toWallet: address) -> (uint256, bool): nonpayable
    def initiateMigration(_fromWallet: address, _toWallet: address) -> bool: nonpayable
    def migrateFunds(_fromWallet: address, _toWallet: address) -> uint256: nonpayable
    def cloneConfig(_fromWallet: address, _toWallet: address) -> bool: nonpayable
    def setInstantMigrationEnabled(_isEnabled: bool) -> bool: nonpayable
    def instantMigrationEnabled() -> bool: view

interface MissionControl:
    def setCanPerformSecurityAction(_signer: address, _canPerform: bool): nonpayable
    def setCreatorWhitelist(_creator: address, _isWhitelisted: bool): nonpayable
    def setRipeRewardsConfig(_config: cs.RipeRewardsConfig): nonpayable
    def setLockedSigner(_signer: address, _isLocked: bool): nonpayable
    def canPerformSecurityAction(_signer: address) -> bool: view

interface LootDistributor:
    def adjustLoot(_user: address, _asset: address, _newClaimable: uint256) -> bool: nonpayable
    def updateDepositPointsOnEjection(_user: address): nonpayable
    def recoverDepositRewards(_recipient: address): nonpayable
    def claimAllLoot(_user: address) -> bool: nonpayable
    def updateDepositPoints(_user: address): nonpayable

interface Hatchery:
    def setStarterAgentConfig(_starterAgentType: cs.StarterAgentType, _startingAgent: address, _startingAgentActivationLength: uint256): nonpayable
    def getDefaultInstantActionSettingsChange(_target: wcs.InstantActionSettings) -> (bool, bool, wcs.InstantActionSettings): view
    def setDefaultInstantActionSettings(_settings: wcs.InstantActionSettings): nonpayable
    def setNonProdCreator(_nonProdCreator: address): nonpayable

interface UndyEcoContract:
    def recoverFundsMany(_recipient: address, _assets: DynArray[address, MAX_RECOVER_ASSETS]): nonpayable
    def recoverNft(_collection: address, _nftTokenId: uint256, _recipient: address): nonpayable
    def recoverFunds(_recipient: address, _asset: address): nonpayable
    def pause(_shouldPause: bool): nonpayable

interface Paymaster:
    def setCanInstantSetGlobalPayeeSettings(_isEnabled: bool) -> bool: nonpayable
    def setCanInstantAddPayee(_isEnabled: bool) -> bool: nonpayable
    def canInstantSetGlobalPayeeSettings() -> bool: view
    def canInstantAddPayee() -> bool: view

interface UserWalletConfig:
    def updateAssetData(_legoId: uint256, _asset: address, _shouldCheckYield: bool) -> uint256: nonpayable
    def updateAllAssetData(_shouldCheckYield: bool) -> uint256: nonpayable
    def setEjectionMode(_shouldEject: bool): nonpayable

interface ChequeBook:
    def setCanInstantSetChequeSettings(_isEnabled: bool) -> bool: nonpayable
    def canInstantSetChequeSettings() -> bool: view

interface HighCommand:
    def setCanInstantAddManager(_isEnabled: bool) -> bool: nonpayable
    def canInstantAddManager() -> bool: view

interface Ledger:
    def isRegisteredBackpackItem(_addr: address) -> bool: view

interface UserWallet:
    def walletConfig() -> address: view

flag ActionType:
    RECOVER_FUNDS
    RECOVER_FUNDS_MANY
    RECOVER_NFT
    LOOT_ADJUST
    RECOVER_DEPOSIT_REWARDS
    SET_EJECTION_MODE
    CAN_PERFORM_SECURITY_ACTION
    ENABLE_INSTANT_MIGRATION
    ENABLE_CAN_INSTANT_ADD_MANAGER
    ENABLE_CAN_INSTANT_ADD_PAYEE
    ENABLE_CAN_INSTANT_SET_GLOBAL_PAYEE_SETTINGS
    ENABLE_CAN_INSTANT_SET_CHEQUE_SETTINGS
    RIPE_REWARDS_CONFIG
    ENABLE_HATCHERY_DEFAULT_INSTANT_SETTINGS

struct PauseAction:
    contractAddr: address
    shouldPause: bool

struct RecoverFundsAction:
    contractAddr: address
    recipient: address
    asset: address

struct RecoverFundsManyAction:
    contractAddr: address
    recipient: address
    assets: DynArray[address, MAX_RECOVER_ASSETS]

struct RecoverNftAction:
    contractAddr: address
    collection: address
    nftTokenId: uint256
    recipient: address

struct LootAdjustAction:
    user: address
    asset: address
    newClaimable: uint256
    lootDistributor: address

struct RecoverDepositRewardsAction:
    lootAddr: address
    recipient: address

struct AssetDataUpdate:
    user: address
    legoId: uint256
    asset: address
    shouldCheckYield: bool

struct AllAssetDataUpdate:
    user: address
    shouldCheckYield: bool

struct SetEjectionModeAction:
    user: address
    shouldEject: bool
    lootDistributor: address

struct IsAddrAllowed:
    addr: address
    isAllowed: bool

struct PendingInstantMigrationEnable:
    migrator: address
    actionId: uint256

struct PendingProtocolFlagEnable:
    target: address
    actionId: uint256

struct PendingHatcheryDefaultInstantSettings:
    settings: wcs.InstantActionSettings
    hatchery: address
    actionId: uint256

event PendingRecoverFundsAction:
    contractAddr: indexed(address)
    recipient: indexed(address)
    asset: indexed(address)
    confirmationBlock: uint256
    actionId: uint256

event PendingRecoverFundsManyAction:
    contractAddr: indexed(address)
    recipient: indexed(address)
    numAssets: uint256
    confirmationBlock: uint256
    actionId: uint256

event PendingRecoverNftAction:
    contractAddr: indexed(address)
    collection: indexed(address)
    nftTokenId: uint256
    recipient: indexed(address)
    confirmationBlock: uint256
    actionId: uint256

event PendingLootAdjustAction:
    user: indexed(address)
    asset: indexed(address)
    newClaimable: uint256
    confirmationBlock: uint256
    actionId: uint256

event PendingRecoverDepositRewardsAction:
    lootAddr: indexed(address)
    recipient: indexed(address)
    confirmationBlock: uint256
    actionId: uint256

event AssetDataUpdated:
    numUsers: uint256
    caller: indexed(address)

event AllAssetDataUpdated:
    numUsers: uint256
    caller: indexed(address)

event PendingSetEjectionModeAction:
    user: indexed(address)
    shouldEject: bool
    confirmationBlock: uint256
    actionId: uint256

event PendingCanPerformSecurityAction:
    signer: address
    canPerform: bool
    confirmationBlock: uint256
    actionId: uint256

event PendingRipeRewardsConfigChange:
    ripeStakeRatio: uint256
    ripeLockDuration: uint256
    confirmationBlock: uint256
    actionId: uint256

event PendingEnableInstantMigrationAction:
    migrator: indexed(address)
    confirmationBlock: uint256
    actionId: uint256
    caller: indexed(address)

event PendingEnableWalletCanInstantAddManagerAction:
    target: indexed(address)
    confirmationBlock: uint256
    actionId: uint256
    caller: indexed(address)

event PendingEnableWalletCanInstantAddPayeeAction:
    target: indexed(address)
    confirmationBlock: uint256
    actionId: uint256
    caller: indexed(address)

event PendingEnableWalletCanInstantSetGlobalPayeeSettingsAction:
    target: indexed(address)
    confirmationBlock: uint256
    actionId: uint256
    caller: indexed(address)

event PendingEnableWalletCanInstantSetChequeSettingsAction:
    target: indexed(address)
    confirmationBlock: uint256
    actionId: uint256
    caller: indexed(address)

event PauseExecuted:
    contractAddr: indexed(address)
    shouldPause: bool

event RecoverFundsExecuted:
    contractAddr: indexed(address)
    recipient: indexed(address)
    asset: indexed(address)

event RecoverFundsManyExecuted:
    contractAddr: indexed(address)
    recipient: indexed(address)
    numAssets: uint256

event RecoverNftExecuted:
    contractAddr: indexed(address)
    collection: indexed(address)
    nftTokenId: uint256
    recipient: indexed(address)

event DepositPointsUpdated:
    numUsers: uint256
    caller: indexed(address)

event LootClaimedForUser:
    user: indexed(address)
    caller: indexed(address)

event LootClaimedForManyUsers:
    numUsers: uint256
    caller: indexed(address)

event LootAdjusted:
    user: indexed(address)
    asset: indexed(address)
    newClaimable: uint256

event RecoverDepositRewardsExecuted:
    lootAddr: indexed(address)
    recipient: indexed(address)

event SetEjectionModeExecuted:
    user: indexed(address)
    shouldEject: bool

event CanPerformSecurityAction:
    signer: address
    canPerform: bool

event RipeRewardsConfigSet:
    ripeStakeRatio: uint256
    ripeLockDuration: uint256

event CreatorWhitelistSet:
    creator: address
    isWhitelisted: bool
    caller: address

event LockedSignerSet:
    signer: address
    isLocked: bool
    caller: address

event HatcheryStarterAgentConfigSet:
    hatchery: indexed(address)
    starterAgentType: cs.StarterAgentType
    startingAgent: indexed(address)
    startingAgentActivationLength: uint256

event HatcheryNonProdCreatorSet:
    hatchery: indexed(address)
    nonProdCreator: indexed(address)

event HatcheryDefaultInstantActionSettingsSet:
    hatchery: indexed(address)
    canInstantAddManager: bool
    canInstantAddPayee: bool
    canInstantSetGlobalPayeeSettings: bool
    canInstantSetChequeSettings: bool

event PendingHatcheryDefaultInstantActionSettingsChange:
    hatchery: indexed(address)
    canInstantAddManager: bool
    canInstantAddPayee: bool
    canInstantSetGlobalPayeeSettings: bool
    canInstantSetChequeSettings: bool
    confirmationBlock: uint256
    actionId: uint256

event WalletMigrationInitiated:
    migrator: indexed(address)
    fromWallet: indexed(address)
    toWallet: indexed(address)
    caller: address

event WalletInstantMigrationEnabledSet:
    migrator: indexed(address)
    isEnabled: bool
    caller: indexed(address)

event WalletCanInstantAddManagerSet:
    target: indexed(address)
    isEnabled: bool
    caller: indexed(address)

event WalletCanInstantAddPayeeSet:
    target: indexed(address)
    isEnabled: bool
    caller: indexed(address)

event WalletCanInstantSetGlobalPayeeSettingsSet:
    target: indexed(address)
    isEnabled: bool
    caller: indexed(address)

event WalletCanInstantSetChequeSettingsSet:
    target: indexed(address)
    isEnabled: bool
    caller: indexed(address)

event WalletFundsMigrated:
    migrator: indexed(address)
    fromWallet: indexed(address)
    toWallet: indexed(address)
    numFundsMigrated: uint256
    caller: address

event WalletConfigCloned:
    migrator: indexed(address)
    fromWallet: indexed(address)
    toWallet: indexed(address)
    caller: address

event WalletMigrated:
    migrator: indexed(address)
    fromWallet: indexed(address)
    toWallet: indexed(address)
    numFundsMigrated: uint256
    didMigrateConfig: bool
    caller: address

# pending actions storage
actionType: public(HashMap[uint256, ActionType])
pendingPauseActions: public(HashMap[uint256, PauseAction])
pendingRecoverFundsActions: public(HashMap[uint256, RecoverFundsAction])
pendingRecoverFundsManyActions: public(HashMap[uint256, RecoverFundsManyAction])
pendingRecoverNftActions: public(HashMap[uint256, RecoverNftAction])
pendingLootAdjustActions: public(HashMap[uint256, LootAdjustAction])
pendingRecoverDepositRewardsActions: public(HashMap[uint256, RecoverDepositRewardsAction])
pendingSetEjectionModeActions: public(HashMap[uint256, SetEjectionModeAction])
pendingAddrToBool: public(HashMap[uint256, IsAddrAllowed])
pendingRipeRewardsConfig: public(HashMap[uint256, cs.RipeRewardsConfig])
pendingInstantMigrationEnable: public(PendingInstantMigrationEnable)
pendingCanInstantAddManagerEnable: public(PendingProtocolFlagEnable)
pendingCanInstantAddPayeeEnable: public(PendingProtocolFlagEnable)
pendingCanInstantSetGlobalPayeeSettingsEnable: public(PendingProtocolFlagEnable)
pendingCanInstantSetChequeSettingsEnable: public(PendingProtocolFlagEnable)
pendingHatcheryDefaultInstantSettings: public(PendingHatcheryDefaultInstantSettings)

MAX_RECOVER_ASSETS: constant(uint256) = 20
MAX_USERS: constant(uint256) = 50


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
def _hasPerms(_caller: address, _isLiteAccess: bool) -> bool:
    if gov._canGovern(_caller):
        return True
    if _isLiteAccess:
        return staticcall MissionControl(addys._getMissionControlAddr()).canPerformSecurityAction(_caller)
    return False


@view
@internal
def _getHatchery() -> address:
    return addys._getHatcheryAddr()


@view
@internal
def _isValidBackpackItem(_addr: address) -> bool:
    if _addr == empty(address):
        return False
    ledger: address = addys._getLedgerAddr()
    if ledger == empty(address):
        return False
    return staticcall Ledger(ledger).isRegisteredBackpackItem(_addr)


###############
# Dept Basics #
###############


# pause contract


@external
def pause(_contractAddr: address, _shouldPause: bool) -> bool:
    assert self._hasPerms(msg.sender, _shouldPause) # dev: no perms

    extcall UndyEcoContract(_contractAddr).pause(_shouldPause)
    log PauseExecuted(contractAddr=_contractAddr, shouldPause=_shouldPause)
    return True


# recover funds


@external
def recoverFunds(_contractAddr: address, _recipient: address, _asset: address) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    assert empty(address) not in [_contractAddr, _recipient, _asset] # dev: invalid parameters
    
    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.RECOVER_FUNDS
    self.pendingRecoverFundsActions[aid] = RecoverFundsAction(
        contractAddr=_contractAddr,
        recipient=_recipient,
        asset=_asset
    )
    
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingRecoverFundsAction(
        contractAddr=_contractAddr,
        recipient=_recipient,
        asset=_asset,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


@external
def recoverFundsMany(_contractAddr: address, _recipient: address, _assets: DynArray[address, MAX_RECOVER_ASSETS]) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    assert empty(address) not in [_contractAddr, _recipient] # dev: invalid parameters
    assert len(_assets) != 0 # dev: no assets provided
    
    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.RECOVER_FUNDS_MANY
    self.pendingRecoverFundsManyActions[aid] = RecoverFundsManyAction(
        contractAddr=_contractAddr,
        recipient=_recipient,
        assets=_assets
    )
    
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingRecoverFundsManyAction(
        contractAddr=_contractAddr,
        recipient=_recipient,
        numAssets=len(_assets),
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


# recover nft


@external
def recoverNft(_addr: address, _collection: address, _nftTokenId: uint256, _recipient: address) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    assert empty(address) not in [_addr, _collection, _recipient] # dev: invalid parameters
    
    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.RECOVER_NFT
    self.pendingRecoverNftActions[aid] = RecoverNftAction(
        contractAddr=_addr,
        collection=_collection,
        nftTokenId=_nftTokenId,
        recipient=_recipient
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingRecoverNftAction(
        contractAddr=_addr,
        collection=_collection,
        nftTokenId=_nftTokenId,
        recipient=_recipient,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


####################
# Loot Distributor #
####################


# claim loot 


@external
def claimLootForUser(_user: address):
    assert self._hasPerms(msg.sender, True) # dev: no perms
    assert _user != empty(address) # dev: invalid user

    extcall LootDistributor(addys._getLootDistributorAddr()).claimAllLoot(_user)
    log LootClaimedForUser(user=_user, caller=msg.sender)


# claim loot for many users


@external
def claimLootForManyUsers(_users: DynArray[address, MAX_USERS]):
    assert self._hasPerms(msg.sender, True) # dev: no perms
    assert len(_users) != 0 # dev: no users provided
    for u: address in _users:
        extcall LootDistributor(addys._getLootDistributorAddr()).claimAllLoot(u)
    log LootClaimedForManyUsers(numUsers=len(_users), caller=msg.sender)


# adjust loot


@external
def adjustLoot(_user: address, _asset: address, _newClaimable: uint256) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    assert empty(address) not in [_user, _asset] # dev: invalid parameters
    
    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.LOOT_ADJUST
    self.pendingLootAdjustActions[aid] = LootAdjustAction(
        user=_user,
        asset=_asset,
        newClaimable=_newClaimable,
        lootDistributor=addys._getLootDistributorAddr(),
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingLootAdjustAction(
        user=_user,
        asset=_asset,
        newClaimable=_newClaimable,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


# recover deposit rewards


@external
def recoverDepositRewards(_lootAddr: address, _recipient: address) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    assert empty(address) not in [_lootAddr, _recipient] # dev: invalid parameters

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.RECOVER_DEPOSIT_REWARDS
    self.pendingRecoverDepositRewardsActions[aid] = RecoverDepositRewardsAction(
        lootAddr=_lootAddr,
        recipient=_recipient
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingRecoverDepositRewardsAction(
        lootAddr=_lootAddr,
        recipient=_recipient,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


# update deposit points


@external
def updateDepositPoints(_users: DynArray[address, MAX_USERS]):
    assert self._hasPerms(msg.sender, True) # dev: no perms
    assert len(_users) != 0 # dev: no users provided
    for u: address in _users:
        extcall LootDistributor(addys._getLootDistributorAddr()).updateDepositPoints(u)
    log DepositPointsUpdated(numUsers=len(_users), caller=msg.sender)


######################
# User Wallet Config #
######################


# update asset data


@external
def updateAssetData(_bundles: DynArray[AssetDataUpdate, MAX_USERS]):
    assert self._hasPerms(msg.sender, True) # dev: no perms
    assert len(_bundles) != 0 # dev: no bundles provided
    for b: AssetDataUpdate in _bundles:
        walletConfig: address = staticcall UserWallet(b.user).walletConfig()
        extcall UserWalletConfig(walletConfig).updateAssetData(b.legoId, b.asset, b.shouldCheckYield)
    log AssetDataUpdated(numUsers=len(_bundles), caller=msg.sender)


# update all asset data


@external
def updateAllAssetData(_bundles: DynArray[AllAssetDataUpdate, MAX_USERS]):
    assert self._hasPerms(msg.sender, True) # dev: no perms
    assert len(_bundles) != 0 # dev: no bundles provided
    for b: AllAssetDataUpdate in _bundles:
        walletConfig: address = staticcall UserWallet(b.user).walletConfig()
        extcall UserWalletConfig(walletConfig).updateAllAssetData(b.shouldCheckYield)
    log AllAssetDataUpdated(numUsers=len(_bundles), caller=msg.sender)


# set ejection mode


@external
def setEjectionMode(_user: address, _shouldEject: bool) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    assert _user != empty(address) # dev: invalid user

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.SET_EJECTION_MODE
    self.pendingSetEjectionModeActions[aid] = SetEjectionModeAction(
        user=_user,
        shouldEject=_shouldEject,
        lootDistributor=addys._getLootDistributorAddr(),
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingSetEjectionModeAction(
        user=_user,
        shouldEject=_shouldEject,
        confirmationBlock=confirmationBlock,
        actionId=aid
    )
    return aid


###################
# Security Config #
###################


@external
def setCanPerformSecurityAction(_signer: address, _canPerform: bool) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    mc: address = addys._getMissionControlAddr()

    # when removing, allow to do immediately
    if not _canPerform:
        extcall MissionControl(mc).setCanPerformSecurityAction(_signer, _canPerform)
        log CanPerformSecurityAction(signer=_signer, canPerform=_canPerform)
        return 0

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.CAN_PERFORM_SECURITY_ACTION
    self.pendingAddrToBool[aid] = IsAddrAllowed(addr=_signer, isAllowed=_canPerform)
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingCanPerformSecurityAction(signer=_signer, canPerform=_canPerform, confirmationBlock=confirmationBlock, actionId=aid)
    return aid


@external
def setRipeRewardsConfig(_ripeStakeRatio: uint256, _ripeLockDuration: uint256) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    assert self._isValidRipeRewardsConfig(_ripeStakeRatio, _ripeLockDuration) # dev: invalid ripe rewards config

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.RIPE_REWARDS_CONFIG
    self.pendingRipeRewardsConfig[aid] = cs.RipeRewardsConfig(
        stakeRatio=_ripeStakeRatio,
        lockDuration=_ripeLockDuration,
    )

    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingRipeRewardsConfigChange(
        ripeStakeRatio=_ripeStakeRatio,
        ripeLockDuration=_ripeLockDuration,
        confirmationBlock=confirmationBlock,
        actionId=aid,
    )
    return aid


@view
@internal
def _isValidRipeRewardsConfig(_ripeStakeRatio: uint256, _ripeLockDuration: uint256) -> bool:
    if _ripeStakeRatio > 100_00:
        return False
    return _ripeLockDuration != 0


@external
def setCreatorWhitelist(_creator: address, _isWhitelisted: bool):
    assert self._hasPerms(msg.sender, not _isWhitelisted) # dev: no perms
    assert _creator != empty(address) # dev: invalid creator

    extcall MissionControl(addys._getMissionControlAddr()).setCreatorWhitelist(_creator, _isWhitelisted)
    log CreatorWhitelistSet(creator=_creator, isWhitelisted=_isWhitelisted, caller=msg.sender)


@external
def setLockedSigner(_signer: address, _isLocked: bool):
    assert self._hasPerms(msg.sender, not _isLocked) # dev: no perms
    assert _signer != empty(address) # dev: invalid creator

    extcall MissionControl(addys._getMissionControlAddr()).setLockedSigner(_signer, _isLocked)
    log LockedSignerSet(signer=_signer, isLocked=_isLocked, caller=msg.sender)


###################
# Hatchery Config #
###################


@external
def setHatcheryStarterAgentConfig(
    _starterAgentType: cs.StarterAgentType,
    _startingAgent: address,
    _startingAgentActivationLength: uint256,
) -> bool:
    assert gov._canGovern(msg.sender) # dev: no perms

    hatchery: address = self._getHatchery()
    extcall Hatchery(hatchery).setStarterAgentConfig(
        _starterAgentType,
        _startingAgent,
        _startingAgentActivationLength,
    )
    log HatcheryStarterAgentConfigSet(
        hatchery=hatchery,
        starterAgentType=_starterAgentType,
        startingAgent=_startingAgent,
        startingAgentActivationLength=_startingAgentActivationLength,
    )
    return True


@external
def setHatcheryNonProdCreator(_nonProdCreator: address) -> bool:
    assert gov._canGovern(msg.sender) # dev: no perms

    hatchery: address = self._getHatchery()
    extcall Hatchery(hatchery).setNonProdCreator(_nonProdCreator)
    log HatcheryNonProdCreatorSet(hatchery=hatchery, nonProdCreator=_nonProdCreator)
    return True


@external
def setHatcheryDefaultInstantActionSettings(
    _canInstantAddManager: bool,
    _canInstantAddPayee: bool,
    _canInstantSetGlobalPayeeSettings: bool,
    _canInstantSetChequeSettings: bool,
) -> bool:
    assert gov._canGovern(msg.sender) # dev: no perms

    hatchery: address = self._getHatchery()
    target: wcs.InstantActionSettings = wcs.InstantActionSettings(
        canInstantAddManager=_canInstantAddManager,
        canInstantAddPayee=_canInstantAddPayee,
        canInstantSetGlobalPayeeSettings=_canInstantSetGlobalPayeeSettings,
        canInstantSetChequeSettings=_canInstantSetChequeSettings,
    )

    hasEnable: bool = False
    hasImmediateChange: bool = False
    immediate: wcs.InstantActionSettings = empty(wcs.InstantActionSettings)
    hasEnable, hasImmediateChange, immediate = staticcall Hatchery(hatchery).getDefaultInstantActionSettingsChange(target)

    if not hasEnable:
        pending: PendingHatcheryDefaultInstantSettings = self.pendingHatcheryDefaultInstantSettings
        if pending.actionId != 0:
            if timeLock._hasPendingAction(pending.actionId):
                self._cancelPendingAction(pending.actionId)
            else:
                self.pendingHatcheryDefaultInstantSettings = empty(PendingHatcheryDefaultInstantSettings)
        self._setHatcheryDefaultInstantActionSettings(hatchery, target)
        return True

    existingPending: PendingHatcheryDefaultInstantSettings = self.pendingHatcheryDefaultInstantSettings
    assert existingPending.actionId == 0 or not timeLock._hasPendingAction(existingPending.actionId) # dev: pending enable exists

    if hasImmediateChange:
        self._setHatcheryDefaultInstantActionSettings(hatchery, immediate)

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.ENABLE_HATCHERY_DEFAULT_INSTANT_SETTINGS
    self.pendingHatcheryDefaultInstantSettings = PendingHatcheryDefaultInstantSettings(settings=target, hatchery=hatchery, actionId=aid)

    log PendingHatcheryDefaultInstantActionSettingsChange(
        hatchery=hatchery,
        canInstantAddManager=target.canInstantAddManager,
        canInstantAddPayee=target.canInstantAddPayee,
        canInstantSetGlobalPayeeSettings=target.canInstantSetGlobalPayeeSettings,
        canInstantSetChequeSettings=target.canInstantSetChequeSettings,
        confirmationBlock=timeLock._getActionConfirmationBlock(aid),
        actionId=aid,
    )
    return True


@internal
def _setHatcheryDefaultInstantActionSettings(_hatchery: address, _settings: wcs.InstantActionSettings):
    extcall Hatchery(_hatchery).setDefaultInstantActionSettings(_settings)
    log HatcheryDefaultInstantActionSettingsSet(
        hatchery=_hatchery,
        canInstantAddManager=_settings.canInstantAddManager,
        canInstantAddPayee=_settings.canInstantAddPayee,
        canInstantSetGlobalPayeeSettings=_settings.canInstantSetGlobalPayeeSettings,
        canInstantSetChequeSettings=_settings.canInstantSetChequeSettings,
    )


#########################
# User Wallet Migration #
#########################


@external
def setInstantMigrationEnabled(_migrator: address, _isEnabled: bool) -> uint256:
    assert self._isValidBackpackItem(_migrator) # dev: invalid migrator

    if not _isEnabled:
        assert self._hasPerms(msg.sender, True) # dev: no perms
        pending: PendingInstantMigrationEnable = self.pendingInstantMigrationEnable
        if pending.actionId != 0 and pending.migrator == _migrator:
            if timeLock._hasPendingAction(pending.actionId):
                self._cancelPendingAction(pending.actionId)
            else:
                self.pendingInstantMigrationEnable = empty(PendingInstantMigrationEnable)
        assert extcall Migrator(_migrator).setInstantMigrationEnabled(False) # dev: failed to disable
        log WalletInstantMigrationEnabledSet(migrator=_migrator, isEnabled=False, caller=msg.sender)
        return 0

    assert gov._canGovern(msg.sender) # dev: no perms
    assert not staticcall Migrator(_migrator).instantMigrationEnabled() # dev: already enabled
    existingPending: PendingInstantMigrationEnable = self.pendingInstantMigrationEnable
    assert existingPending.actionId == 0 or not timeLock._hasPendingAction(existingPending.actionId) # dev: pending enable exists

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.ENABLE_INSTANT_MIGRATION
    self.pendingInstantMigrationEnable = PendingInstantMigrationEnable(migrator=_migrator, actionId=aid)

    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingEnableInstantMigrationAction(
        migrator=_migrator,
        confirmationBlock=confirmationBlock,
        actionId=aid,
        caller=msg.sender,
    )
    return aid


@external
def setCanInstantAddManager(_highCommand: address, _isEnabled: bool) -> uint256:
    assert self._isValidBackpackItem(_highCommand) # dev: invalid high command

    if not _isEnabled:
        assert self._hasPerms(msg.sender, True) # dev: no perms
        pending: PendingProtocolFlagEnable = self.pendingCanInstantAddManagerEnable
        if pending.actionId != 0 and pending.target == _highCommand:
            if timeLock._hasPendingAction(pending.actionId):
                self._cancelPendingAction(pending.actionId)
            else:
                self.pendingCanInstantAddManagerEnable = empty(PendingProtocolFlagEnable)
        assert extcall HighCommand(_highCommand).setCanInstantAddManager(False) # dev: failed to disable
        log WalletCanInstantAddManagerSet(target=_highCommand, isEnabled=False, caller=msg.sender)
        return 0

    assert gov._canGovern(msg.sender) # dev: no perms
    assert not staticcall HighCommand(_highCommand).canInstantAddManager() # dev: already enabled
    existingPending: PendingProtocolFlagEnable = self.pendingCanInstantAddManagerEnable
    assert existingPending.actionId == 0 or not timeLock._hasPendingAction(existingPending.actionId) # dev: pending enable exists

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.ENABLE_CAN_INSTANT_ADD_MANAGER
    self.pendingCanInstantAddManagerEnable = PendingProtocolFlagEnable(target=_highCommand, actionId=aid)

    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingEnableWalletCanInstantAddManagerAction(
        target=_highCommand,
        confirmationBlock=confirmationBlock,
        actionId=aid,
        caller=msg.sender,
    )
    return aid


@external
def setCanInstantAddPayee(_paymaster: address, _isEnabled: bool) -> uint256:
    assert self._isValidBackpackItem(_paymaster) # dev: invalid paymaster

    if not _isEnabled:
        assert self._hasPerms(msg.sender, True) # dev: no perms
        pending: PendingProtocolFlagEnable = self.pendingCanInstantAddPayeeEnable
        if pending.actionId != 0 and pending.target == _paymaster:
            if timeLock._hasPendingAction(pending.actionId):
                self._cancelPendingAction(pending.actionId)
            else:
                self.pendingCanInstantAddPayeeEnable = empty(PendingProtocolFlagEnable)
        assert extcall Paymaster(_paymaster).setCanInstantAddPayee(False) # dev: failed to disable
        log WalletCanInstantAddPayeeSet(target=_paymaster, isEnabled=False, caller=msg.sender)
        return 0

    assert gov._canGovern(msg.sender) # dev: no perms
    assert not staticcall Paymaster(_paymaster).canInstantAddPayee() # dev: already enabled
    existingPending: PendingProtocolFlagEnable = self.pendingCanInstantAddPayeeEnable
    assert existingPending.actionId == 0 or not timeLock._hasPendingAction(existingPending.actionId) # dev: pending enable exists

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.ENABLE_CAN_INSTANT_ADD_PAYEE
    self.pendingCanInstantAddPayeeEnable = PendingProtocolFlagEnable(target=_paymaster, actionId=aid)

    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingEnableWalletCanInstantAddPayeeAction(
        target=_paymaster,
        confirmationBlock=confirmationBlock,
        actionId=aid,
        caller=msg.sender,
    )
    return aid


@external
def setCanInstantSetGlobalPayeeSettings(_paymaster: address, _isEnabled: bool) -> uint256:
    assert self._isValidBackpackItem(_paymaster) # dev: invalid paymaster

    if not _isEnabled:
        assert self._hasPerms(msg.sender, True) # dev: no perms
        pending: PendingProtocolFlagEnable = self.pendingCanInstantSetGlobalPayeeSettingsEnable
        if pending.actionId != 0 and pending.target == _paymaster:
            if timeLock._hasPendingAction(pending.actionId):
                self._cancelPendingAction(pending.actionId)
            else:
                self.pendingCanInstantSetGlobalPayeeSettingsEnable = empty(PendingProtocolFlagEnable)
        assert extcall Paymaster(_paymaster).setCanInstantSetGlobalPayeeSettings(False) # dev: failed to disable
        log WalletCanInstantSetGlobalPayeeSettingsSet(target=_paymaster, isEnabled=False, caller=msg.sender)
        return 0

    assert gov._canGovern(msg.sender) # dev: no perms
    assert not staticcall Paymaster(_paymaster).canInstantSetGlobalPayeeSettings() # dev: already enabled
    existingPending: PendingProtocolFlagEnable = self.pendingCanInstantSetGlobalPayeeSettingsEnable
    assert existingPending.actionId == 0 or not timeLock._hasPendingAction(existingPending.actionId) # dev: pending enable exists

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.ENABLE_CAN_INSTANT_SET_GLOBAL_PAYEE_SETTINGS
    self.pendingCanInstantSetGlobalPayeeSettingsEnable = PendingProtocolFlagEnable(target=_paymaster, actionId=aid)

    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingEnableWalletCanInstantSetGlobalPayeeSettingsAction(
        target=_paymaster,
        confirmationBlock=confirmationBlock,
        actionId=aid,
        caller=msg.sender,
    )
    return aid


@external
def setCanInstantSetChequeSettings(_chequeBook: address, _isEnabled: bool) -> uint256:
    assert self._isValidBackpackItem(_chequeBook) # dev: invalid cheque book

    if not _isEnabled:
        assert self._hasPerms(msg.sender, True) # dev: no perms
        pending: PendingProtocolFlagEnable = self.pendingCanInstantSetChequeSettingsEnable
        if pending.actionId != 0 and pending.target == _chequeBook:
            if timeLock._hasPendingAction(pending.actionId):
                self._cancelPendingAction(pending.actionId)
            else:
                self.pendingCanInstantSetChequeSettingsEnable = empty(PendingProtocolFlagEnable)
        assert extcall ChequeBook(_chequeBook).setCanInstantSetChequeSettings(False) # dev: failed to disable
        log WalletCanInstantSetChequeSettingsSet(target=_chequeBook, isEnabled=False, caller=msg.sender)
        return 0

    assert gov._canGovern(msg.sender) # dev: no perms
    assert not staticcall ChequeBook(_chequeBook).canInstantSetChequeSettings() # dev: already enabled
    existingPending: PendingProtocolFlagEnable = self.pendingCanInstantSetChequeSettingsEnable
    assert existingPending.actionId == 0 or not timeLock._hasPendingAction(existingPending.actionId) # dev: pending enable exists

    aid: uint256 = timeLock._initiateAction()
    self.actionType[aid] = ActionType.ENABLE_CAN_INSTANT_SET_CHEQUE_SETTINGS
    self.pendingCanInstantSetChequeSettingsEnable = PendingProtocolFlagEnable(target=_chequeBook, actionId=aid)

    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingEnableWalletCanInstantSetChequeSettingsAction(
        target=_chequeBook,
        confirmationBlock=confirmationBlock,
        actionId=aid,
        caller=msg.sender,
    )
    return aid


@external
def initiateWalletMigration(_migrator: address, _fromWallet: address, _toWallet: address) -> bool:
    assert gov._canGovern(msg.sender) # dev: no perms
    assert self._isValidBackpackItem(_migrator) # dev: invalid migrator
    assert empty(address) not in [_fromWallet, _toWallet] # dev: invalid wallet

    didInitiate: bool = extcall Migrator(_migrator).initiateMigration(_fromWallet, _toWallet)
    log WalletMigrationInitiated(migrator=_migrator, fromWallet=_fromWallet, toWallet=_toWallet, caller=msg.sender)
    return didInitiate


@external
def migrateWalletFunds(_migrator: address, _fromWallet: address, _toWallet: address) -> uint256:
    assert gov._canGovern(msg.sender) # dev: no perms
    assert self._isValidBackpackItem(_migrator) # dev: invalid migrator
    assert empty(address) not in [_fromWallet, _toWallet] # dev: invalid wallet

    numFundsMigrated: uint256 = extcall Migrator(_migrator).migrateFunds(_fromWallet, _toWallet)
    log WalletFundsMigrated(
        migrator=_migrator,
        fromWallet=_fromWallet,
        toWallet=_toWallet,
        numFundsMigrated=numFundsMigrated,
        caller=msg.sender,
    )
    return numFundsMigrated


@external
def cloneWalletConfig(_migrator: address, _fromWallet: address, _toWallet: address) -> bool:
    assert gov._canGovern(msg.sender) # dev: no perms
    assert self._isValidBackpackItem(_migrator) # dev: invalid migrator
    assert empty(address) not in [_fromWallet, _toWallet] # dev: invalid wallet

    didClone: bool = extcall Migrator(_migrator).cloneConfig(_fromWallet, _toWallet)
    log WalletConfigCloned(migrator=_migrator, fromWallet=_fromWallet, toWallet=_toWallet, caller=msg.sender)
    return didClone


@external
def migrateWallet(_migrator: address, _fromWallet: address, _toWallet: address) -> (uint256, bool):
    assert gov._canGovern(msg.sender) # dev: no perms
    assert self._isValidBackpackItem(_migrator) # dev: invalid migrator
    assert empty(address) not in [_fromWallet, _toWallet] # dev: invalid wallet

    numFundsMigrated: uint256 = 0
    didMigrateConfig: bool = False
    numFundsMigrated, didMigrateConfig = extcall Migrator(_migrator).migrateAll(_fromWallet, _toWallet)
    log WalletMigrated(
        migrator=_migrator,
        fromWallet=_fromWallet,
        toWallet=_toWallet,
        numFundsMigrated=numFundsMigrated,
        didMigrateConfig=didMigrateConfig,
        caller=msg.sender,
    )
    return numFundsMigrated, didMigrateConfig


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

    if actionType == ActionType.RECOVER_FUNDS:
        p: RecoverFundsAction = self.pendingRecoverFundsActions[_aid]
        extcall UndyEcoContract(p.contractAddr).recoverFunds(p.recipient, p.asset)
        log RecoverFundsExecuted(contractAddr=p.contractAddr, recipient=p.recipient, asset=p.asset)

    elif actionType == ActionType.RECOVER_FUNDS_MANY:
        p: RecoverFundsManyAction = self.pendingRecoverFundsManyActions[_aid]
        extcall UndyEcoContract(p.contractAddr).recoverFundsMany(p.recipient, p.assets)
        log RecoverFundsManyExecuted(contractAddr=p.contractAddr, recipient=p.recipient, numAssets=len(p.assets))

    elif actionType == ActionType.RECOVER_NFT:
        p: RecoverNftAction = self.pendingRecoverNftActions[_aid]
        extcall UndyEcoContract(p.contractAddr).recoverNft(p.collection, p.nftTokenId, p.recipient)
        log RecoverNftExecuted(contractAddr=p.contractAddr, collection=p.collection, nftTokenId=p.nftTokenId, recipient=p.recipient)

    elif actionType == ActionType.LOOT_ADJUST:
        p: LootAdjustAction = self.pendingLootAdjustActions[_aid]
        extcall LootDistributor(p.lootDistributor).adjustLoot(p.user, p.asset, p.newClaimable)
        log LootAdjusted(user=p.user, asset=p.asset, newClaimable=p.newClaimable)

    elif actionType == ActionType.RECOVER_DEPOSIT_REWARDS:
        p: RecoverDepositRewardsAction = self.pendingRecoverDepositRewardsActions[_aid]
        extcall LootDistributor(p.lootAddr).recoverDepositRewards(p.recipient)
        log RecoverDepositRewardsExecuted(lootAddr=p.lootAddr, recipient=p.recipient)

    elif actionType == ActionType.SET_EJECTION_MODE:
        p: SetEjectionModeAction = self.pendingSetEjectionModeActions[_aid]
        walletConfig: address = staticcall UserWallet(p.user).walletConfig()
        extcall UserWalletConfig(walletConfig).setEjectionMode(p.shouldEject)
        log SetEjectionModeExecuted(user=p.user, shouldEject=p.shouldEject)

        # update loot points
        extcall LootDistributor(p.lootDistributor).updateDepositPointsOnEjection(p.user)

    elif actionType == ActionType.CAN_PERFORM_SECURITY_ACTION:
        data: IsAddrAllowed = self.pendingAddrToBool[_aid]
        extcall MissionControl(addys._getMissionControlAddr()).setCanPerformSecurityAction(data.addr, data.isAllowed)
        log CanPerformSecurityAction(signer=data.addr, canPerform=data.isAllowed)

    elif actionType == ActionType.RIPE_REWARDS_CONFIG:
        p: cs.RipeRewardsConfig = self.pendingRipeRewardsConfig[_aid]
        extcall MissionControl(addys._getMissionControlAddr()).setRipeRewardsConfig(p)
        log RipeRewardsConfigSet(ripeStakeRatio=p.stakeRatio, ripeLockDuration=p.lockDuration)

    elif actionType == ActionType.ENABLE_INSTANT_MIGRATION:
        pending: PendingInstantMigrationEnable = self.pendingInstantMigrationEnable
        assert pending.actionId == _aid # dev: invalid pending enable
        migrator: address = pending.migrator
        assert self._isValidBackpackItem(migrator) # dev: invalid migrator
        assert extcall Migrator(migrator).setInstantMigrationEnabled(True) # dev: failed to enable
        self.pendingInstantMigrationEnable = empty(PendingInstantMigrationEnable)
        log WalletInstantMigrationEnabledSet(migrator=migrator, isEnabled=True, caller=msg.sender)

    elif actionType == ActionType.ENABLE_CAN_INSTANT_ADD_MANAGER:
        pending: PendingProtocolFlagEnable = self.pendingCanInstantAddManagerEnable
        assert pending.actionId == _aid # dev: invalid pending enable
        assert self._isValidBackpackItem(pending.target) # dev: invalid high command
        assert extcall HighCommand(pending.target).setCanInstantAddManager(True) # dev: failed to enable
        self.pendingCanInstantAddManagerEnable = empty(PendingProtocolFlagEnable)
        log WalletCanInstantAddManagerSet(target=pending.target, isEnabled=True, caller=msg.sender)

    elif actionType == ActionType.ENABLE_CAN_INSTANT_ADD_PAYEE:
        pending: PendingProtocolFlagEnable = self.pendingCanInstantAddPayeeEnable
        assert pending.actionId == _aid # dev: invalid pending enable
        assert self._isValidBackpackItem(pending.target) # dev: invalid paymaster
        assert extcall Paymaster(pending.target).setCanInstantAddPayee(True) # dev: failed to enable
        self.pendingCanInstantAddPayeeEnable = empty(PendingProtocolFlagEnable)
        log WalletCanInstantAddPayeeSet(target=pending.target, isEnabled=True, caller=msg.sender)

    elif actionType == ActionType.ENABLE_CAN_INSTANT_SET_GLOBAL_PAYEE_SETTINGS:
        pending: PendingProtocolFlagEnable = self.pendingCanInstantSetGlobalPayeeSettingsEnable
        assert pending.actionId == _aid # dev: invalid pending enable
        assert self._isValidBackpackItem(pending.target) # dev: invalid paymaster
        assert extcall Paymaster(pending.target).setCanInstantSetGlobalPayeeSettings(True) # dev: failed to enable
        self.pendingCanInstantSetGlobalPayeeSettingsEnable = empty(PendingProtocolFlagEnable)
        log WalletCanInstantSetGlobalPayeeSettingsSet(target=pending.target, isEnabled=True, caller=msg.sender)

    elif actionType == ActionType.ENABLE_CAN_INSTANT_SET_CHEQUE_SETTINGS:
        pending: PendingProtocolFlagEnable = self.pendingCanInstantSetChequeSettingsEnable
        assert pending.actionId == _aid # dev: invalid pending enable
        assert self._isValidBackpackItem(pending.target) # dev: invalid cheque book
        assert extcall ChequeBook(pending.target).setCanInstantSetChequeSettings(True) # dev: failed to enable
        self.pendingCanInstantSetChequeSettingsEnable = empty(PendingProtocolFlagEnable)
        log WalletCanInstantSetChequeSettingsSet(target=pending.target, isEnabled=True, caller=msg.sender)

    elif actionType == ActionType.ENABLE_HATCHERY_DEFAULT_INSTANT_SETTINGS:
        pending: PendingHatcheryDefaultInstantSettings = self.pendingHatcheryDefaultInstantSettings
        assert pending.actionId == _aid # dev: invalid pending enable
        self._setHatcheryDefaultInstantActionSettings(pending.hatchery, pending.settings)
        self.pendingHatcheryDefaultInstantSettings = empty(PendingHatcheryDefaultInstantSettings)

    self.actionType[_aid] = empty(ActionType)
    return True


#################
# Cancel Action #
#################


@external
def cancelPendingAction(_aid: uint256) -> bool:
    assert gov._canGovern(msg.sender) # dev: no perms
    self._cancelPendingAction(_aid)
    return True


@internal
def _cancelPendingAction(_aid: uint256):
    assert timeLock._cancelAction(_aid) # dev: cannot cancel action
    actionType: ActionType = self.actionType[_aid]
    self.actionType[_aid] = empty(ActionType)
