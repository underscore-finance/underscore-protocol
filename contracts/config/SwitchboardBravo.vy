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

interface LootDistributor:
    def adjustLoot(_user: address, _asset: address, _newClaimable: uint256) -> bool: nonpayable
    def updateDepositPointsOnEjection(_user: address): nonpayable
    def recoverDepositRewards(_recipient: address): nonpayable
    def claimAllLoot(_user: address) -> bool: nonpayable
    def updateDepositPoints(_user: address): nonpayable

interface UndyEcoContract:
    def recoverFundsMany(_recipient: address, _assets: DynArray[address, MAX_RECOVER_ASSETS]): nonpayable
    def recoverNft(_collection: address, _nftTokenId: uint256, _recipient: address): nonpayable
    def recoverFunds(_recipient: address, _asset: address): nonpayable
    def pause(_shouldPause: bool): nonpayable

interface UserWalletConfig:
    def updateAssetData(_legoId: uint256, _asset: address, _shouldCheckYield: bool) -> uint256: nonpayable
    def updateAllAssetData(_shouldCheckYield: bool) -> uint256: nonpayable
    def setEjectionMode(_shouldEject: bool): nonpayable

interface Hatchery:
    def clawBackTrialFunds(_user: address) -> uint256: nonpayable

interface MissionControl:
    def canPerformSecurityAction(_signer: address) -> bool: view

interface Ledger:
    def isUserWallet(_user: address) -> bool: view

interface UserWallet:
    def walletConfig() -> address: view

flag ActionType:
    RECOVER_FUNDS
    RECOVER_FUNDS_MANY
    RECOVER_NFT
    LOOT_ADJUST
    RECOVER_DEPOSIT_REWARDS
    SET_EJECTION_MODE

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

event ClawbackTrialFundsExecuted:
    numUsers: uint256

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

# pending actions storage
actionType: public(HashMap[uint256, ActionType])
pendingPauseActions: public(HashMap[uint256, PauseAction])
pendingRecoverFundsActions: public(HashMap[uint256, RecoverFundsAction])
pendingRecoverFundsManyActions: public(HashMap[uint256, RecoverFundsManyAction])
pendingRecoverNftActions: public(HashMap[uint256, RecoverNftAction])
pendingLootAdjustActions: public(HashMap[uint256, LootAdjustAction])
pendingRecoverDepositRewardsActions: public(HashMap[uint256, RecoverDepositRewardsAction])
pendingSetEjectionModeActions: public(HashMap[uint256, SetEjectionModeAction])

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


###############
# Trial Funds #
###############


@external
def clawBackTrialFunds(_users: DynArray[address, MAX_USERS]) -> bool:
    assert self._hasPerms(msg.sender, True) # dev: no perms

    hatchery: address = addys._getHatcheryAddr()
    ledger: address = addys._getLedgerAddr()
    for u: address in _users:
        if not staticcall Ledger(ledger).isUserWallet(u):
            continue
        extcall Hatchery(hatchery).clawBackTrialFunds(u)
    log ClawbackTrialFundsExecuted(numUsers=len(_users))
    return True


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
        newClaimable=_newClaimable
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
        shouldEject=_shouldEject
    )
    confirmationBlock: uint256 = timeLock._getActionConfirmationBlock(aid)
    log PendingSetEjectionModeAction(
        user=_user,
        shouldEject=_shouldEject,
        confirmationBlock=confirmationBlock,
        actionId=aid
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
        extcall LootDistributor(addys._getLootDistributorAddr()).adjustLoot(p.user, p.asset, p.newClaimable)
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
        extcall LootDistributor(addys._getLootDistributorAddr()).updateDepositPointsOnEjection(p.user)

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
    self.actionType[_aid] = empty(ActionType)
