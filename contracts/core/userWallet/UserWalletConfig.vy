# @version 0.4.1
# pragma optimize codesize

initializes: own
exports: own.__interface__

from interfaces import LegoPartner as Lego

import contracts.modules.Ownership as own
from ethereum.ercs import IERC20
from interfaces import LegoYield

interface UserWallet:
    def migrateWalletOut(_newWallet: address, _assetsToMigrate: DynArray[address, MAX_MIGRATION_ASSETS], _whitelistToMigrate: DynArray[address, MAX_MIGRATION_WHITELIST]) -> bool: nonpayable
    def trialFundsInitialAmount() -> uint256: view
    def clawBackTrialFunds() -> bool: nonpayable
    def trialFundsAsset() -> address: view
    def walletConfig() -> address: view
    def canBeAmbassador() -> bool: view

interface WalletConfig:
    def vaultTokenAmounts(_vaultToken: address) -> uint256: view
    def depositedAmounts(_vaultToken: address) -> uint256: view
    def isRecipientAllowed(_addr: address) -> bool: view
    def hasPendingOwnerChange() -> bool: view
    def myAmbassador() -> address: view
    def owner() -> address: view

interface LegoRegistry:
    def getLegoFromVaultToken(_vaultToken: address) -> (uint256, address): view
    def getUnderlyingForUser(_user: address, _asset: address) -> uint256: view
    def isVaultToken(_vaultToken: address) -> bool: view
    def isValidLegoId(_legoId: uint256) -> bool: view

interface PriceSheets:
    def getCombinedSubData(_user: address, _agent: address, _agentPaidThru: uint256, _protocolPaidThru: uint256, _oracleRegistry: address) -> (SubPaymentInfo, SubPaymentInfo): view
    def getAgentSubPriceData(_agent: address) -> SubscriptionInfo: view
    def protocolSubPriceData() -> SubscriptionInfo: view

interface AgentFactory:
    def canCancelCriticalAction(_addr: address) -> bool: view
    def isUserWallet(_wallet: address) -> bool: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

interface Ledger:
    def isLockedSigner(_agent: address) -> bool: view

struct AgentInfo:
    isActive: bool
    installBlock: uint256
    paidThroughBlock: uint256
    allowedAssets: DynArray[address, MAX_ASSETS]
    allowedLegoIds: DynArray[uint256, MAX_LEGOS]
    allowedActions: AllowedActions

struct PendingWhitelist:
    initiatedBlock: uint256
    confirmBlock: uint256

struct CoreData:
    owner: address
    wallet: address
    walletConfig: address
    addyRegistry: address
    agentFactory: address
    legoRegistry: address
    priceSheets: address
    oracleRegistry: address
    trialFundsAsset: address
    trialFundsInitialAmount: uint256

struct SubPaymentInfo:
    recipient: address
    asset: address
    amount: uint256
    usdValue: uint256
    paidThroughBlock: uint256
    didChange: bool

struct ProtocolSub:
    installBlock: uint256
    paidThroughBlock: uint256

struct AllowedActions:
    isSet: bool
    canManageYield: bool
    canSwapAssets: bool
    canManageDebt: bool
    canManageLiquidity: bool
    canTransfer: bool
    canClaimRewards: bool
    canWrapWeth: bool

struct ReserveAsset:
    asset: address
    amount: uint256

struct SubscriptionInfo:
    asset: address
    usdValue: uint256
    trialPeriod: uint256
    payPeriod: uint256

event AgentAdded:
    agent: indexed(address)
    allowedAssets: uint256
    allowedLegoIds: uint256

event AgentModified:
    agent: indexed(address)
    allowedAssets: uint256
    allowedLegoIds: uint256

event AgentDisabled:
    agent: indexed(address)
    prevAllowedAssets: uint256
    prevAllowedLegoIds: uint256

event LegoIdAddedToAgent:
    agent: indexed(address)
    legoId: indexed(uint256)

event AssetAddedToAgent:
    agent: indexed(address)
    asset: indexed(address)

event AllowedActionsModified:
    agent: indexed(address)
    canDeposit: bool
    canWithdraw: bool
    canRebalance: bool
    canTransfer: bool
    canSwap: bool
    canConvert: bool
    canAddLiq: bool
    canRemoveLiq: bool
    canClaimRewards: bool
    canBorrow: bool
    canRepay: bool

event CanTransferToAltOwnerWalletsSet:
    canTransfer: bool

event WhitelistAddrPending:
    addr: indexed(address)
    confirmBlock: uint256

event WhitelistAddrConfirmed:
    addr: indexed(address)
    initiatedBlock: uint256
    confirmBlock: uint256

event WhitelistAddrCancelled:
    addr: indexed(address)
    initiatedBlock: uint256
    confirmBlock: uint256
    cancelledBy: indexed(address)

event WhitelistAddrRemoved:
    addr: indexed(address)

event WhitelistAddrSetViaMigration:
    addr: indexed(address)

event ReserveAssetSet:
    asset: indexed(address)
    amount: uint256

event CanWalletBeAmbassadorSet:
    canWalletBeAmbassador: bool

event AmbassadorForwarderSet:
    addr: indexed(address)

event FundsRecovered:
    asset: indexed(address)
    recipient: indexed(address)
    balance: uint256

event UserWalletStartMigration:
    newWallet: indexed(address)
    numAssetsToMigrate: uint256
    numWhitelistToMigrate: uint256

event UserWalletFinishMigration:
    oldWallet: indexed(address)
    numWhitelistMigrated: uint256
    numVaultTokensMigrated: uint256
    numAssetsMigrated: uint256

# core
wallet: public(address)
didSetWallet: public(bool)

# user settings
protocolSub: public(ProtocolSub) # subscription info
reserveAssets: public(HashMap[address, uint256]) # asset -> reserve amount
agentSettings: public(HashMap[address, AgentInfo]) # agent -> agent info

# transfer whitelist
isRecipientAllowed: public(HashMap[address, bool]) # recipient -> is allowed
pendingWhitelist: public(HashMap[address, PendingWhitelist]) # addr -> pending whitelist
canTransferToAltOwnerWallets: public(bool)

# ambassador settings
canWalletBeAmbassador: public(bool)
ambassadorForwarder: public(address)
myAmbassador: public(address) # cannot be edited -- inviter of THIS user wallet

# migration
didMigrateIn: public(bool)
didMigrateOut: public(bool)

# yield tracking
isVaultToken: public(HashMap[address, bool]) # asset -> is vault token
vaultTokenAmounts: public(HashMap[address, uint256]) # vault token -> vault token amount
depositedAmounts: public(HashMap[address, uint256]) # vault token -> underlying asset amount

# registry ids
LEDGER_ID: constant(uint256) = 2

MAX_MIGRATION_ASSETS: constant(uint256) = 40
MAX_MIGRATION_WHITELIST: constant(uint256) = 20
MAX_ASSETS: constant(uint256) = 10
MAX_LEGOS: constant(uint256) = 10
API_VERSION: constant(String[28]) = "0.0.4"

UNDY_HQ: public(immutable(address))


@deploy
def __init__(
    _owner: address,
    _initialAgent: address,
    _ambassador: address,
    _undyHq: address,
    _minOwnerChangeDelay: uint256,
    _maxOwnerChangeDelay: uint256,
):
    assert empty(address) not in [_undyHq, _owner] # dev: invalid addrs
    UNDY_HQ = _undyHq

    # initialize ownership
    assert _initialAgent != _owner # dev: agent cannot be owner
    own.__init__(_owner, _undyHq, _minOwnerChangeDelay, _maxOwnerChangeDelay)

    # ambassador settings
    self.canWalletBeAmbassador = True
    if _ambassador != empty(address):
        self.myAmbassador = _ambassador

    self.canTransferToAltOwnerWallets = True


@external
def setWallet(_wallet: address) -> bool:
    assert not self.didSetWallet # dev: wallet already set
    assert _wallet != empty(address) # dev: invalid wallet
    assert msg.sender == staticcall Registry(UNDY_HQ).getAddr(WALLET_FACTORY_ID) # dev: no perms
    self.wallet = _wallet
    self.didSetWallet = True
    return True


@pure
@external
def apiVersion() -> String[28]:
    return API_VERSION


################
# Agent Access #
################


@view
@external
def canAccessWallet(
    _signer: address,
    _action: Lego.ActionType,
    _assets: DynArray[address, MAX_ASSETS],
    _legoIds: DynArray[uint256, MAX_LEGOS],
) -> bool:

    ledger: address = staticcall Registry(UNDY_HQ).getAddr(LEDGER_ID)
    if staticcall Ledger(ledger).isLockedSigner(_signer):
        return False

    if _signer == own.owner:
        return True

    return self._canAccessWallet(self.agentSettings[_signer], _action, _assets, _legoIds)


@view
@internal
def _canAccessWallet(
    _agentInfo: AgentInfo,
    _action: Lego.ActionType,
    _assets: DynArray[address, MAX_ASSETS],
    _legoIds: DynArray[uint256, MAX_LEGOS],
) -> bool:
    if not _agentInfo.isActive:
        return False

    # check allowed actions
    if not self._canAgentPerformAction(_action, _agentInfo.allowedActions):
        return False

    # check allowed assets
    if len(_agentInfo.allowedAssets) != 0:
        for a: address in _assets:
            if a != empty(address) and a not in _agentInfo.allowedAssets:
                return False

    # check allowed lego ids
    if len(_agentInfo.allowedLegoIds) != 0:
        for legoId: uint256 in _legoIds:
            if legoId != 0 and legoId not in _agentInfo.allowedLegoIds:
                return False

    return True


@view
@internal
def _canAgentPerformAction(_action: Lego.ActionType, _allowedActions: AllowedActions) -> bool:
    if not _allowedActions.isSet or _action == empty(Lego.ActionType):
        return True
    if _action == Lego.ActionType.EARN:
        return _allowedActions.canManageYield
    elif _action == Lego.ActionType.EXCHANGE:
        return _allowedActions.canSwapAssets
    elif _action == Lego.ActionType.DEBT:
        return _allowedActions.canManageDebt
    elif _action == Lego.ActionType.LIQUIDITY:
        return _allowedActions.canManageLiquidity
    elif _action == Lego.ActionType.TRANSFER:
        return _allowedActions.canTransfer
    elif _action == Lego.ActionType.REWARDS:
        return _allowedActions.canClaimRewards
    elif _action == Lego.ActionType.WETH_WRAP:
        return _allowedActions.canWrapWeth
    else:
        return True # no action specified


@view
@external
def isAgentActive(_agent: address) -> bool:
    return self.agentSettings[_agent].isActive


##################
# Agent Settings #
##################


# add or modify agent settings


@nonreentrant
@external
def addOrModifyAgent(
    _agent: address,
    _allowedAssets: DynArray[address, MAX_ASSETS] = [],
    _allowedLegoIds: DynArray[uint256, MAX_LEGOS] = [],
    _allowedActions: AllowedActions = empty(AllowedActions),
) -> bool:
    owner: address = own.owner
    assert msg.sender == owner # dev: no perms
    assert _agent != owner # dev: agent cannot be owner
    assert _agent != empty(address) # dev: invalid agent

    agentInfo: AgentInfo = self.agentSettings[_agent]
    agentInfo.isActive = True

    # allowed actions
    agentInfo.allowedActions = _allowedActions
    agentInfo.allowedActions.isSet = self._hasAllowedActionsSet(_allowedActions)

    # sanitize other input data
    agentInfo.allowedAssets, agentInfo.allowedLegoIds = self._sanitizeAgentInputData(_allowedAssets, _allowedLegoIds)

    # get subscription info
    priceSheets: address = staticcall Registry(UNDY_HQ).getAddr(PRICE_SHEETS_ID)
    subInfo: SubscriptionInfo = staticcall PriceSheets(priceSheets).getAgentSubPriceData(_agent)
    
    isNewAgent: bool = (agentInfo.installBlock == 0)
    if isNewAgent:
        agentInfo.installBlock = block.number
        if subInfo.usdValue != 0:
            agentInfo.paidThroughBlock = block.number + subInfo.trialPeriod

    # may not have had sub setup before
    elif subInfo.usdValue != 0:
        agentInfo.paidThroughBlock = max(agentInfo.paidThroughBlock, agentInfo.installBlock + subInfo.trialPeriod)

    self.agentSettings[_agent] = agentInfo

    # log event
    if isNewAgent:
        log AgentAdded(agent=_agent, allowedAssets=len(agentInfo.allowedAssets), allowedLegoIds=len(agentInfo.allowedLegoIds))
    else:
        log AgentModified(agent=_agent, allowedAssets=len(agentInfo.allowedAssets), allowedLegoIds=len(agentInfo.allowedLegoIds))
    return True


@view
@internal
def _sanitizeAgentInputData(
    _allowedAssets: DynArray[address, MAX_ASSETS],
    _allowedLegoIds: DynArray[uint256, MAX_LEGOS],
) -> (DynArray[address, MAX_ASSETS], DynArray[uint256, MAX_LEGOS]):

    # nothing to do here
    if len(_allowedAssets) == 0 and len(_allowedLegoIds) == 0:
        return _allowedAssets, _allowedLegoIds

    # sanitize and dedupe assets
    cleanAssets: DynArray[address, MAX_ASSETS] = []
    for i: uint256 in range(len(_allowedAssets), bound=MAX_ASSETS):
        asset: address = _allowedAssets[i]
        if asset == empty(address):
            continue
        if asset not in cleanAssets:
            cleanAssets.append(asset)

    # validate and dedupe lego ids
    cleanLegoIds: DynArray[uint256, MAX_LEGOS] = []
    if len(_allowedLegoIds) != 0:
        legoRegistry: address = staticcall Registry(UNDY_HQ).getAddr(LEGO_BOOK_ID)
        for i: uint256 in range(len(_allowedLegoIds), bound=MAX_LEGOS):
            legoId: uint256 = _allowedLegoIds[i]
            if not staticcall LegoRegistry(legoRegistry).isValidLegoId(legoId):
                continue
            if legoId not in cleanLegoIds:
                cleanLegoIds.append(legoId)

    return cleanAssets, cleanLegoIds


# disable agent


@nonreentrant
@external
def disableAgent(_agent: address) -> bool:
    assert msg.sender == own.owner # dev: no perms

    agentInfo: AgentInfo = self.agentSettings[_agent]
    assert agentInfo.isActive # dev: agent not active
    agentInfo.isActive = False
    self.agentSettings[_agent] = agentInfo

    log AgentDisabled(agent=_agent, prevAllowedAssets=len(agentInfo.allowedAssets), prevAllowedLegoIds=len(agentInfo.allowedLegoIds))
    return True


# add lego id for agent


@nonreentrant
@external
def addLegoIdForAgent(_agent: address, _legoId: uint256) -> bool:
    assert msg.sender == own.owner # dev: no perms

    agentInfo: AgentInfo = self.agentSettings[_agent]
    assert agentInfo.isActive # dev: agent not active

    legoRegistry: address = staticcall Registry(UNDY_HQ).getAddr(LEGO_BOOK_ID)
    assert staticcall LegoRegistry(legoRegistry).isValidLegoId(_legoId)
    assert _legoId not in agentInfo.allowedLegoIds # dev: lego id already saved

    # save data
    agentInfo.allowedLegoIds.append(_legoId)
    self.agentSettings[_agent] = agentInfo

    # log event
    log LegoIdAddedToAgent(agent=_agent, legoId=_legoId)
    return True


# add asset for agent


@nonreentrant
@external
def addAssetForAgent(_agent: address, _asset: address) -> bool:
    assert msg.sender == own.owner # dev: no perms

    agentInfo: AgentInfo = self.agentSettings[_agent]
    assert agentInfo.isActive # dev: agent not active

    assert _asset != empty(address) # dev: invalid asset
    assert _asset not in agentInfo.allowedAssets # dev: asset already saved

    # save data
    agentInfo.allowedAssets.append(_asset)
    self.agentSettings[_agent] = agentInfo

    # log event
    log AssetAddedToAgent(agent=_agent, asset=_asset)
    return True


# modify allowed actions


@nonreentrant
@external
def modifyAllowedActions(_agent: address, _allowedActions: AllowedActions = empty(AllowedActions)) -> bool:
    assert msg.sender == own.owner # dev: no perms

    agentInfo: AgentInfo = self.agentSettings[_agent]
    assert agentInfo.isActive # dev: agent not active

    agentInfo.allowedActions = _allowedActions
    agentInfo.allowedActions.isSet = self._hasAllowedActionsSet(_allowedActions)
    self.agentSettings[_agent] = agentInfo

    log AllowedActionsModified(agent=_agent, canDeposit=_allowedActions.canDeposit, canWithdraw=_allowedActions.canWithdraw, canRebalance=_allowedActions.canRebalance, canTransfer=_allowedActions.canTransfer, canSwap=_allowedActions.canSwap, canConvert=_allowedActions.canConvert, canAddLiq=_allowedActions.canAddLiq, canRemoveLiq=_allowedActions.canRemoveLiq, canClaimRewards=_allowedActions.canClaimRewards, canBorrow=_allowedActions.canBorrow, canRepay=_allowedActions.canRepay)
    return True


@view
@internal
def _hasAllowedActionsSet(_actions: AllowedActions) -> bool:
    return _actions.canDeposit or _actions.canWithdraw or _actions.canRebalance or _actions.canTransfer or _actions.canSwap or _actions.canConvert


######################
# Transfer Whitelist #
######################


@view
@external
def canTransferToRecipient(_recipient: address) -> bool:
    if self.isRecipientAllowed[_recipient]:
        return True

    # pending ownership change, don't even check alt wallet ownership
    if own._hasPendingOwnerChange():
        return False

    # if enabled, check if alt wallet has same owner
    if self.canTransferToAltOwnerWallets:
        return self._doesWalletHaveSameOwner(_recipient)

    return False


@view
@external
def doesWalletHaveSameOwner(_wallet: address) -> bool:
    return self._doesWalletHaveSameOwner(_wallet)


@view
@internal
def _doesWalletHaveSameOwner(_wallet: address) -> bool:
    isSame: bool = False

    # check if wallet is Underscore wallet, if owner is same (no pending ownership changes), transfer is allowed
    agentFactory: address = staticcall Registry(UNDY_HQ).getAddr(WALLET_FACTORY_ID)
    if staticcall AgentFactory(agentFactory).isUserWallet(_wallet):
        walletConfig: address = staticcall UserWallet(_wallet).walletConfig()
        if not staticcall WalletConfig(walletConfig).hasPendingOwnerChange():
            isSame = own.owner == staticcall WalletConfig(walletConfig).owner()

    return isSame


@external
def setCanTransferToAltOwnerWallets(_canTransfer: bool) -> bool:
    assert msg.sender == own.owner # dev: only owner can set
    if self.canTransferToAltOwnerWallets == _canTransfer:
        return False
    self.canTransferToAltOwnerWallets = _canTransfer
    log CanTransferToAltOwnerWalletsSet(canTransfer=_canTransfer)
    return True


@nonreentrant
@external
def addWhitelistAddr(_addr: address):
    owner: address = own.owner
    assert msg.sender == owner # dev: only owner can add whitelist

    assert _addr != empty(address) # dev: invalid addr
    assert _addr != owner # dev: owner cannot be whitelisted
    assert _addr != self # dev: wallet config cannot be whitelisted
    assert _addr != self.wallet # dev: wallet cannot be whitelisted
    assert not self.isRecipientAllowed[_addr] # dev: already whitelisted
    assert self.pendingWhitelist[_addr].initiatedBlock == 0 # dev: pending whitelist already exists

    # this uses same delay as ownership change
    confirmBlock: uint256 = block.number + own.ownershipChangeDelay
    self.pendingWhitelist[_addr] = PendingWhitelist(
        initiatedBlock = block.number,
        confirmBlock = confirmBlock,
    )
    log WhitelistAddrPending(addr=_addr, confirmBlock=confirmBlock)


@nonreentrant
@external
def confirmWhitelistAddr(_addr: address):
    assert msg.sender == own.owner # dev: only owner can confirm

    data: PendingWhitelist = self.pendingWhitelist[_addr]
    assert data.initiatedBlock != 0 # dev: no pending whitelist
    assert data.confirmBlock != 0 and block.number >= data.confirmBlock # dev: time delay not reached

    self.pendingWhitelist[_addr] = empty(PendingWhitelist)
    self.isRecipientAllowed[_addr] = True
    log WhitelistAddrConfirmed(addr=_addr, initiatedBlock=data.initiatedBlock, confirmBlock=data.confirmBlock)


@nonreentrant
@external
def cancelPendingWhitelistAddr(_addr: address):
    agentFactory: address = staticcall Registry(UNDY_HQ).getAddr(WALLET_FACTORY_ID)
    assert msg.sender == own.owner or staticcall AgentFactory(agentFactory).canCancelCriticalAction(msg.sender) # dev: no perms (only owner or governance)

    data: PendingWhitelist = self.pendingWhitelist[_addr]
    assert data.initiatedBlock != 0 # dev: no pending whitelist
    self.pendingWhitelist[_addr] = empty(PendingWhitelist)
    log WhitelistAddrCancelled(addr=_addr, initiatedBlock=data.initiatedBlock, confirmBlock=data.confirmBlock, cancelledBy=msg.sender)


@nonreentrant
@external
def removeWhitelistAddr(_addr: address):
    assert msg.sender == own.owner # dev: only owner can remove whitelist
    assert self.isRecipientAllowed[_addr] # dev: not on whitelist

    self.isRecipientAllowed[_addr] = False
    log WhitelistAddrRemoved(addr=_addr)


@internal
def _setWhitelistAddrFromMigration(_addr: address) -> bool:
    self.isRecipientAllowed[_addr] = True
    log WhitelistAddrSetViaMigration(addr=_addr)
    return True
