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

interface UndyEcoContract:
    def recoverFundsMany(_recipient: address, _assets: DynArray[address, MAX_RECOVER_ASSETS]): nonpayable
    def recoverNft(_collection: address, _nftTokenId: uint256, _recipient: address): nonpayable
    def recoverFunds(_recipient: address, _asset: address): nonpayable
    def pause(_shouldPause: bool): nonpayable

interface MissionControl:
    def canPerformSecurityAction(_signer: address) -> bool: view

flag ActionType:
    RECOVER_FUNDS
    RECOVER_FUNDS_MANY
    RECOVER_NFT

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

# pending actions storage
actionType: public(HashMap[uint256, ActionType])
pendingPauseActions: public(HashMap[uint256, PauseAction])
pendingRecoverFundsActions: public(HashMap[uint256, RecoverFundsAction])
pendingRecoverFundsManyActions: public(HashMap[uint256, RecoverFundsManyAction])
pendingRecoverNftActions: public(HashMap[uint256, RecoverNftAction])

MAX_RECOVER_ASSETS: constant(uint256) = 20


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
def hasPermsForLiteAction(_caller: address, _hasLiteAccess: bool) -> bool:
    if gov._canGovern(_caller):
        return True
    if _hasLiteAccess:
        return staticcall MissionControl(addys._getMissionControlAddr()).canPerformSecurityAction(_caller)
    return False


###############
# Dept Basics #
###############


# pause contract


@external
def pause(_contractAddr: address, _shouldPause: bool) -> bool:
    assert self.hasPermsForLiteAction(msg.sender, _shouldPause) # dev: no perms

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
