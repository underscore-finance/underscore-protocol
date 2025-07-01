# @version 0.4.3
# pragma optimize codesize

from interfaces import Wallet as wi
from ethereum.ercs import IERC20

interface UserWalletConfig:
    def indexOfManager(_manager: address) -> uint256: view
    def hasPendingOwnerChange() -> bool: view
    def startingAgent() -> address: view
    def numManagers() -> uint256: view
    def groupId() -> uint256: view
    def owner() -> address: view

interface UserWallet:
    def assets(_index: uint256) -> address: view
    def trialFundsAmount() -> uint256: view
    def walletConfig() -> address: view
    def numAssets() -> uint256: view

interface Registry:
    def isValidRegId(_regId: uint256) -> bool: view
    def getAddr(_regId: uint256) -> address: view

interface WalletBackpack:
    def getBackpackData(_userWallet: address) -> BackpackData: view

interface Ledger:
    def isUserWallet(_user: address) -> bool: view

struct ActionData:
    legoBook: address
    walletBackpack: address
    feeRecipient: address
    wallet: address
    walletConfig: address
    walletOwner: address
    inEjectMode: bool
    isFrozen: bool
    lastTotalUsdValue: uint256
    signer: address
    isManager: bool
    legoId: uint256
    legoAddr: address
    eth: address
    weth: address

struct ManagerData:
    numTxsInPeriod: uint256
    totalUsdValueInPeriod: uint256
    numTxs: uint256
    totalUsdValue: uint256
    lastTxBlock: uint256

struct Limits:
    maxVolumePerTx: uint256
    maxVolumePerPeriod: uint256
    maxNumTxsPerPeriod: uint256
    txCooldownBlocks: uint256
    failOnZeroPrice: bool

struct LegoPerms:
    canManageYield: bool
    canBuyAndSell: bool
    canManageDebt: bool
    canManageLiq: bool
    canClaimRewards: bool
    allowedLegos: DynArray[uint256, MAX_CONFIG_LEGOS]

struct TransferPerms:
    canTransfer: bool
    canCreateCheque: bool
    canAddPendingRecipient: bool
    allowedRecipients: DynArray[address, MAX_CONFIG_RECIPIENTS]

struct ManagerSettings:
    startBlock: uint256
    expiryBlock: uint256
    limits: Limits
    legoPerms: LegoPerms
    transferPerms: TransferPerms
    allowedAssets: DynArray[address, MAX_CONFIG_ASSETS]

struct GlobalManagerSettings:
    managerPeriod: uint256
    startDelay: uint256
    activationLength: uint256
    limits: Limits
    legoPerms: LegoPerms
    transferPerms: TransferPerms
    allowedAssets: DynArray[address, MAX_CONFIG_ASSETS]

struct PendingGlobalManagerSettings:
    config: GlobalManagerSettings
    initiatedBlock: uint256
    confirmBlock: uint256

struct PendingOwnerChange:
    newOwner: address
    initiatedBlock: uint256
    confirmBlock: uint256

struct BackpackData:
    legoBook: address
    feeRecipient: address
    lastTotalUsdValue: uint256

struct EjectModeFeeDetails:
    feeRecipient: address
    swapFee: uint256
    rewardsFee: uint256

event OwnershipChangeInitiated:
    prevOwner: indexed(address)
    newOwner: indexed(address)
    confirmBlock: uint256

event OwnershipChangeConfirmed:
    prevOwner: indexed(address)
    newOwner: indexed(address)
    initiatedBlock: uint256
    confirmBlock: uint256

event OwnershipChangeCancelled:
    cancelledOwner: indexed(address)
    cancelledBy: indexed(address)
    initiatedBlock: uint256
    confirmBlock: uint256

event TimeLockSet:
    numBlocks: uint256

event EjectionModeSet:
    inEjectMode: bool
    feeRecipient: address
    swapFee: uint256
    rewardsFee: uint256
    caller: indexed(address)

event FrozenSet:
    isFrozen: bool
    caller: indexed(address)

event GlobalManagerSettingsModified:
    state: String[10]
    managerPeriod: uint256
    startDelay: uint256
    activationLength: uint256
    maxVolumePerTx: uint256
    maxVolumePerPeriod: uint256
    maxNumTxsPerPeriod: uint256
    txCooldownBlocks: uint256
    canManageYield: bool
    canBuyAndSell: bool
    canManageDebt: bool
    canManageLiq: bool
    canClaimRewards: bool
    numAllowedLegos: uint256
    canTransfer: bool
    canCreateCheque: bool
    canAddPendingRecipient: bool
    numAllowedRecipients: uint256
    numAllowedAssets: uint256

event ManagerSettingsModified:
    manager: indexed(address)
    state: String[10]
    startBlock: uint256
    expiryBlock: uint256
    maxVolumePerTx: uint256
    maxVolumePerPeriod: uint256
    maxNumTxsPerPeriod: uint256
    txCooldownBlocks: uint256
    canManageYield: bool
    canBuyAndSell: bool
    canManageDebt: bool
    canManageLiq: bool
    canClaimRewards: bool
    numAllowedLegos: uint256
    canTransfer: bool
    canCreateCheque: bool
    canAddPendingRecipient: bool
    numAllowedRecipients: uint256
    numAllowedAssets: uint256

event ManagerRemoved:
    manager: indexed(address)

event ManagerActivationLengthAdjusted:
    manager: indexed(address)
    activationLength: uint256
    didRestart: bool

# core
wallet: public(address)
groupId: public(uint256)
owner: public(address)
pendingOwner: public(PendingOwnerChange)

# managers
managerSettings: public(HashMap[address, ManagerSettings])
managerPeriodData: public(HashMap[address, ManagerData])

# managers (iterable)
managers: public(HashMap[uint256, address]) # index -> manager
indexOfManager: public(HashMap[address, uint256]) # manager -> index
numManagers: public(uint256) # num managers

# global config
globalManagerSettings: public(GlobalManagerSettings)
pendingGlobalManagerSettings: public(PendingGlobalManagerSettings)

# config
isFrozen: public(bool)
inEjectMode: public(bool)
timeLock: public(uint256)
didSetWallet: public(bool)

# other
ejectModeFeeDetails: public(EjectModeFeeDetails)
startingAgent: public(address)

API_VERSION: constant(String[28]) = "0.1.0"

MAX_CONFIG_ASSETS: constant(uint256) = 40
MAX_CONFIG_LEGOS: constant(uint256) = 25
MAX_CONFIG_ACTIONS: constant(uint256) = 20
MAX_CONFIG_RECIPIENTS: constant(uint256) = 40
MAX_ASSETS: constant(uint256) = 10
MAX_LEGOS: constant(uint256) = 10

# time (blocks)
ONE_DAY_IN_BLOCKS: constant(uint256) = 43_200
ONE_MONTH_IN_BLOCKS: constant(uint256) = ONE_DAY_IN_BLOCKS * 30
ONE_YEAR_IN_BLOCKS: constant(uint256) = ONE_DAY_IN_BLOCKS * 365

# registry ids
LEDGER_ID: constant(uint256) = 2
LEGO_BOOK_ID: constant(uint256) = 4
HATCHERY_ID: constant(uint256) = 6
WALLET_BACKPACK_ID: constant(uint256) = 7

UNDY_HQ: public(immutable(address))
MIN_TIMELOCK: public(immutable(uint256))
MAX_TIMELOCK: public(immutable(uint256))
MIN_MANAGER_PERIOD: public(immutable(uint256))
MAX_MANAGER_PERIOD: public(immutable(uint256))


@deploy
def __init__(
    _undyHq: address,
    _owner: address,
    _startingAgent: address,
    _startingAgentActivationLength: uint256,
    _managerPeriod: uint256,
    _defaultStartDelay: uint256,
    _defaultActivationLength: uint256,
    _groupId: uint256,
    _minManagerPeriod: uint256,
    _maxManagerPeriod: uint256,
    _minTimeLock: uint256,
    _maxTimeLock: uint256,
):
    assert empty(address) not in [_undyHq, _owner] # dev: invalid addrs
    UNDY_HQ = _undyHq
    self.owner = _owner
    self.groupId = _groupId

    # manager periods (set this first)
    assert _minManagerPeriod != 0 and _minManagerPeriod < _maxManagerPeriod # dev: invalid manager periods
    MIN_MANAGER_PERIOD = _minManagerPeriod
    MAX_MANAGER_PERIOD = _maxManagerPeriod

    # global manager settings
    config: GlobalManagerSettings = empty(GlobalManagerSettings)
    assert self._isValidManagerPeriod(_managerPeriod) # dev: invalid manager period
    assert self._isValidStartDelay(_defaultStartDelay) # dev: invalid start delay
    assert self._isValidActivationLength(_defaultActivationLength) # dev: invalid activation length
    config.managerPeriod = _managerPeriod
    config.startDelay = _defaultStartDelay
    config.activationLength = _defaultActivationLength
    config.legoPerms, config.transferPerms = self._createHappyDefaults()
    self.globalManagerSettings = config

    # initial manager
    if _startingAgent != empty(address):
        assert self._isValidActivationLength(_startingAgentActivationLength) # dev: invalid activation length
        self.managerSettings[_startingAgent] = ManagerSettings(
            startBlock = block.number,
            expiryBlock = block.number + _startingAgentActivationLength,
            limits = empty(Limits), # no limits
            legoPerms = config.legoPerms, # all set to True
            transferPerms = config.transferPerms, # all set to True
            allowedAssets = [],
        )
        self._registerManager(_startingAgent)
        self.startingAgent = _startingAgent

    # time lock
    assert _minTimeLock < _maxTimeLock # dev: invalid delay
    MIN_TIMELOCK = _minTimeLock
    MAX_TIMELOCK = _maxTimeLock
    self.timeLock = _minTimeLock


@external
def setWallet(_wallet: address) -> bool:
    assert not self.didSetWallet # dev: wallet already set
    assert _wallet != empty(address) # dev: invalid wallet
    assert msg.sender == staticcall Registry(UNDY_HQ).getAddr(HATCHERY_ID) # dev: no perms
    self.wallet = _wallet
    self.didSetWallet = True
    return True


@pure
@external
def apiVersion() -> String[28]:
    return API_VERSION


#############
# Core Data #
#############


@view
@external
def getActionDataBundle() -> ActionData:
    return self._getActionDataBundle()


@view
@internal
def _getActionDataBundle() -> ActionData:
    wallet: address = self.wallet
    inEjectMode: bool = self.inEjectMode

    walletBackpack: address = empty(address)
    backpackData: BackpackData = empty(BackpackData)
    if not inEjectMode:
        walletBackpack = staticcall Registry(UNDY_HQ).getAddr(WALLET_BACKPACK_ID)
        backpackData = staticcall WalletBackpack(walletBackpack).getBackpackData(wallet)

    return ActionData(
        legoBook = backpackData.legoBook,
        walletBackpack = walletBackpack,
        feeRecipient = backpackData.feeRecipient,
        wallet = wallet,
        walletConfig = self,
        walletOwner = self.owner,
        inEjectMode = inEjectMode,
        isFrozen = self.isFrozen,
        lastTotalUsdValue = backpackData.lastTotalUsdValue,
        signer = empty(address),
        isManager = False,
        legoId = 0,
        legoAddr = empty(address),
        eth = empty(address),
        weth = empty(address),
    )


##################
# Access Control #
##################


@view
@external
def validateAccessAndGetBundle(
    _signer: address,
    _action: wi.ActionType,
    _assets: DynArray[address, MAX_ASSETS] = [],
    _legoIds: DynArray[uint256, MAX_LEGOS] = [],
    _transferRecipient: address = empty(address),
) -> ActionData:
    data: ActionData = self._getActionDataBundle()

    # trusted signers
    trustedSigners: DynArray[address, 3] = [self.owner, self]
    if data.walletBackpack != empty(address):
        trustedSigners.append(data.walletBackpack)

    # check permissions if not trusted signer
    if _signer not in trustedSigners:
        assert self._canManagerPerformAction(_signer, _action, _assets, _legoIds, _transferRecipient) # dev: no permission

    # wallet backpack can only perform withdraw from yield
    if data.walletBackpack != empty(address) and _signer == data.walletBackpack:
        assert _action == wi.ActionType.EARN_WITHDRAW # dev: invalid action

    # during migration, using `transfer` action
    if _signer == self:
        assert _action == wi.ActionType.TRANSFER # dev: invalid action

    data.signer = _signer
    data.isManager = _signer not in trustedSigners
    return data


# check basic permissions


@view
@external
def canManagerPerformAction(
    _signer: address,
    _action: wi.ActionType,
    _assets: DynArray[address, MAX_ASSETS] = [],
    _legoIds: DynArray[uint256, MAX_LEGOS] = [],
    _transferRecipient: address = empty(address),
) -> bool:
    return self._canManagerPerformAction(_signer, _action, _assets, _legoIds, _transferRecipient)


@view
@internal
def _canManagerPerformAction(
    _signer: address,
    _action: wi.ActionType,
    _assets: DynArray[address, MAX_ASSETS],
    _legoIds: DynArray[uint256, MAX_LEGOS],
    _transferRecipient: address,
) -> bool:
    if self.indexOfManager[_signer] == 0:
        return False # signer is not a manager

    # manager is not active
    config: ManagerSettings = self.managerSettings[_signer]
    if config.startBlock > block.number or config.expiryBlock < block.number:
        return False

    # first, check manager permissions
    if not self._checkPermissions(
        _action,
        _assets,
        _legoIds,
        _transferRecipient,
        config.allowedAssets,
        config.legoPerms,
        config.transferPerms,
    ):
        return False

    # then, check global manager permissions
    globalConfig: GlobalManagerSettings = self.globalManagerSettings
    if not self._checkPermissions(
        _action,
        _assets,
        _legoIds,
        _transferRecipient,
        globalConfig.allowedAssets,
        globalConfig.legoPerms,
        globalConfig.transferPerms,
    ):
        return False

    # validate limits (the ones we can do before knowing tx value)
    limits: Limits = self._getCurrentLimits(config.limits, globalConfig.limits)
    data: ManagerData = self._getLatestManagerData(_signer, globalConfig.managerPeriod)
    if limits.maxNumTxsPerPeriod != 0 and data.numTxsInPeriod >= limits.maxNumTxsPerPeriod:
        return False # max num txs per period reached

    # check cooldown
    if limits.txCooldownBlocks != 0 and data.lastTxBlock + limits.txCooldownBlocks > block.number:
        return False

    return True


@view
@internal
def _checkPermissions(
    _action: wi.ActionType,
    _assets: DynArray[address, MAX_ASSETS],
    _legoIds: DynArray[uint256, MAX_LEGOS],
    _transferRecipient: address,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
    _legoPerms: LegoPerms,
    _transferPerms: TransferPerms,
) -> bool:

    # check allowed assets
    if len(_allowedAssets) != 0:
        for a: address in _assets:
            if a != empty(address) and a not in _allowedAssets:
                return False

    # check allowed lego ids
    if len(_legoPerms.allowedLegos) != 0:
        for lid: uint256 in _legoIds:
            if lid != 0 and lid not in _legoPerms.allowedLegos:
                return False

    # check allowed recipients
    if _action == wi.ActionType.TRANSFER:
        if len(_transferPerms.allowedRecipients) != 0:
            if _transferRecipient not in _transferPerms.allowedRecipients:
                return False

    return self._canPerformSpecificAction(_action, _legoPerms, _transferPerms.canTransfer)


@view
@internal
def _canPerformSpecificAction(_action: wi.ActionType, _legoPerms: LegoPerms, _canTransfer: bool) -> bool:
    if _action == wi.ActionType.TRANSFER:
        return _canTransfer
    elif _action in (wi.ActionType.EARN_DEPOSIT | wi.ActionType.EARN_WITHDRAW | wi.ActionType.EARN_REBALANCE):
        return _legoPerms.canManageYield
    elif _action in (wi.ActionType.SWAP | wi.ActionType.MINT_REDEEM | wi.ActionType.CONFIRM_MINT_REDEEM):
        return _legoPerms.canBuyAndSell
    elif _action in (wi.ActionType.ADD_COLLATERAL | wi.ActionType.REMOVE_COLLATERAL | wi.ActionType.BORROW | wi.ActionType.REPAY_DEBT):
        return _legoPerms.canManageDebt
    elif _action in (wi.ActionType.ADD_LIQ | wi.ActionType.REMOVE_LIQ | wi.ActionType.ADD_LIQ_CONC | wi.ActionType.REMOVE_LIQ_CONC):
        return _legoPerms.canManageLiq
    elif _action == wi.ActionType.REWARDS:
        return _legoPerms.canClaimRewards
    else:
        return True


###################
# Add Transaction #
###################


@external
def addNewManagerTransaction(_manager: address, _txUsdValue: uint256):
    assert msg.sender == self.wallet # dev: no perms

    # config
    config: ManagerSettings = self.managerSettings[_manager]
    globalConfig: GlobalManagerSettings = self.globalManagerSettings

    # validate tx value
    limits: Limits = self._getCurrentLimits(config.limits, globalConfig.limits)

    # check zero price
    if _txUsdValue == 0:
        assert not limits.failOnZeroPrice # dev: zero price not allowed

    # validate max volume per tx
    if limits.maxVolumePerTx != 0:
        assert _txUsdValue <= limits.maxVolumePerTx # dev: tx value exceeds max volume per tx

    # validate caps per period
    data: ManagerData = self._getLatestManagerData(_manager, globalConfig.managerPeriod)
    if limits.maxVolumePerPeriod != 0:
        assert data.totalUsdValueInPeriod + _txUsdValue <= limits.maxVolumePerPeriod # dev: max volume per period reached
    if limits.maxNumTxsPerPeriod != 0:
        assert data.numTxsInPeriod < limits.maxNumTxsPerPeriod # dev: max num txs per period reached

    # check cooldown
    if limits.txCooldownBlocks != 0:
        assert data.lastTxBlock + limits.txCooldownBlocks < block.number # dev: tx cooldown not reached

    # update transaction details
    data.numTxsInPeriod += 1
    data.totalUsdValueInPeriod += _txUsdValue
    data.totalUsdValue += _txUsdValue
    data.numTxs += 1
    data.lastTxBlock = block.number
    self.managerPeriodData[_manager] = data


@view
@internal
def _getCurrentLimits(_managerLimits: Limits, _globalLimits: Limits) -> Limits:
    limits: Limits = _globalLimits

    if _managerLimits.maxVolumePerTx != 0:
        limits.maxVolumePerTx = min(limits.maxVolumePerTx, _managerLimits.maxVolumePerTx)
    if _managerLimits.maxVolumePerPeriod != 0:
        limits.maxVolumePerPeriod = min(limits.maxVolumePerPeriod, _managerLimits.maxVolumePerPeriod)
    if _managerLimits.maxNumTxsPerPeriod != 0:
        limits.maxNumTxsPerPeriod = min(limits.maxNumTxsPerPeriod, _managerLimits.maxNumTxsPerPeriod)
    if _managerLimits.txCooldownBlocks != 0:
        limits.txCooldownBlocks = max(limits.txCooldownBlocks, _managerLimits.txCooldownBlocks) # using max here!

    limits.failOnZeroPrice = _managerLimits.failOnZeroPrice or _globalLimits.failOnZeroPrice
    return limits


@view
@internal
def _getLatestManagerData(_manager: address, _managerPeriod: uint256) -> ManagerData:
    data: ManagerData = self.managerPeriodData[_manager]

    # reset if period has ended
    if data.lastTxBlock + _managerPeriod < block.number:
        data.numTxsInPeriod = 0
        data.totalUsdValueInPeriod = 0

    return data


#############
# Ownership #
#############


@external
def changeOwnership(_newOwner: address):
    currentOwner: address = self.owner
    assert msg.sender == currentOwner # dev: no perms
    assert _newOwner not in [empty(address), currentOwner] # dev: invalid new owner

    confirmBlock: uint256 = block.number + self.timeLock
    self.pendingOwner = PendingOwnerChange(
        newOwner = _newOwner,
        initiatedBlock = block.number,
        confirmBlock = confirmBlock,
    )
    log OwnershipChangeInitiated(prevOwner=currentOwner, newOwner=_newOwner, confirmBlock=confirmBlock)


@external
def confirmOwnershipChange():
    data: PendingOwnerChange = self.pendingOwner
    assert data.newOwner != empty(address) # dev: no pending owner
    assert data.confirmBlock != 0 and block.number >= data.confirmBlock # dev: time delay not reached
    assert msg.sender == data.newOwner # dev: only new owner can confirm

    prevOwner: address = self.owner
    self.owner = data.newOwner
    self.pendingOwner = empty(PendingOwnerChange)
    log OwnershipChangeConfirmed(prevOwner=prevOwner, newOwner=data.newOwner, initiatedBlock=data.initiatedBlock, confirmBlock=data.confirmBlock)


@external
def cancelOwnershipChange():
    if msg.sender != self.owner:
        walletBackpack: address = staticcall Registry(UNDY_HQ).getAddr(WALLET_BACKPACK_ID)
        assert msg.sender == walletBackpack # dev: no perms

    data: PendingOwnerChange = self.pendingOwner
    assert data.confirmBlock != 0 # dev: no pending change
    self.pendingOwner = empty(PendingOwnerChange)
    log OwnershipChangeCancelled(cancelledOwner=data.newOwner, cancelledBy=msg.sender, initiatedBlock=data.initiatedBlock, confirmBlock=data.confirmBlock)


# utils


@view
@external
def hasPendingOwnerChange() -> bool:
    return self._hasPendingOwnerChange()


@view
@internal
def _hasPendingOwnerChange() -> bool:
    return self.pendingOwner.confirmBlock != 0


###############
# Other Admin #
###############


# time lock


@external
def setTimeLock(_numBlocks: uint256):
    assert msg.sender == self.owner # dev: no perms
    assert _numBlocks >= MIN_TIMELOCK and _numBlocks <= MAX_TIMELOCK # dev: invalid delay
    self.timeLock = _numBlocks
    log TimeLockSet(numBlocks=_numBlocks)


# freeze wallet


@external
def setFrozen(_isFrozen: bool):
    if msg.sender != self.owner:
        walletBackpack: address = staticcall Registry(UNDY_HQ).getAddr(WALLET_BACKPACK_ID)
        assert msg.sender == walletBackpack # dev: no perms
        assert self.groupId != 0 # dev: must have group id

    self.isFrozen = _isFrozen
    log FrozenSet(isFrozen=_isFrozen, caller=msg.sender)


# ejection mode


@external
def setEjectionMode(_inEjectMode: bool, _feeDetails: EjectModeFeeDetails):
    walletBackpack: address = staticcall Registry(UNDY_HQ).getAddr(WALLET_BACKPACK_ID)
    assert msg.sender == walletBackpack # dev: no perms
    assert _inEjectMode != self.inEjectMode # dev: nothing to change

    self.inEjectMode = _inEjectMode
    if _inEjectMode:
        self.ejectModeFeeDetails = _feeDetails

    log EjectionModeSet(
        inEjectMode = _inEjectMode,
        feeRecipient = _feeDetails.feeRecipient,
        swapFee = _feeDetails.swapFee,
        rewardsFee = _feeDetails.rewardsFee,
        caller = msg.sender,
    )


###########################
# Global Manager Settings #
###########################


# set pending global manager settings


@external
def setPendingGlobalManagerSettings(
    _managerPeriod: uint256,
    _startDelay: uint256,
    _activationLength: uint256,
    _limits: Limits,
    _legoPerms: LegoPerms,
    _transferPerms: TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
) -> bool:
    assert msg.sender == self.owner # dev: no perms

    # validation
    assert self._isValidManagerPeriod(_managerPeriod) # dev: invalid manager period
    assert self._isValidStartDelay(_startDelay) # dev: invalid start delay
    assert self._isValidActivationLength(_activationLength) # dev: invalid activation length
    assert self._isValidLimits(_limits) # dev: invalid limits
    assert self._isValidLegoPerms(_legoPerms) # dev: invalid lego perms
    assert self._isValidTransferPerms(_transferPerms) # dev: invalid transfer perms
    assert self._isValidAllowedAssets(_allowedAssets) # dev: invalid allowed assets

    config: GlobalManagerSettings = GlobalManagerSettings(
        managerPeriod = _managerPeriod,
        startDelay = _startDelay,
        activationLength = _activationLength,
        limits = _limits,
        legoPerms = _legoPerms,
        transferPerms = _transferPerms,
        allowedAssets = _allowedAssets,
    )

    # put in pending state
    self.pendingGlobalManagerSettings = PendingGlobalManagerSettings(
        config = config,
        initiatedBlock = block.number,
        confirmBlock = block.number + self.timeLock,
    )

    log GlobalManagerSettingsModified(
        state = "PENDING",
        managerPeriod = _managerPeriod,
        startDelay = _startDelay,
        activationLength = _activationLength,
        maxVolumePerTx = _limits.maxVolumePerTx,
        maxVolumePerPeriod = _limits.maxVolumePerPeriod,
        maxNumTxsPerPeriod = _limits.maxNumTxsPerPeriod,
        txCooldownBlocks = _limits.txCooldownBlocks,
        canManageYield = _legoPerms.canManageYield,
        canBuyAndSell = _legoPerms.canBuyAndSell,
        canManageDebt = _legoPerms.canManageDebt,
        canManageLiq = _legoPerms.canManageLiq,
        canClaimRewards = _legoPerms.canClaimRewards,
        numAllowedLegos = len(_legoPerms.allowedLegos),
        canTransfer = _transferPerms.canTransfer,
        canCreateCheque = _transferPerms.canCreateCheque,
        canAddPendingRecipient = _transferPerms.canAddPendingRecipient,
        numAllowedRecipients = len(_transferPerms.allowedRecipients),
        numAllowedAssets = len(_allowedAssets),
    )
    return True


# confirm global manager settings


@external
def confirmPendingGlobalManagerSettings() -> bool:
    assert msg.sender == self.owner # dev: no perms

    data: PendingGlobalManagerSettings = self.pendingGlobalManagerSettings
    assert data.confirmBlock != 0 and block.number >= data.confirmBlock # dev: time delay not reached
    self.globalManagerSettings = data.config
    self.pendingGlobalManagerSettings = empty(PendingGlobalManagerSettings)

    log GlobalManagerSettingsModified(
        state = "CONFIRMED",
        managerPeriod = data.config.managerPeriod,
        startDelay = data.config.startDelay,
        activationLength = data.config.activationLength,
        maxVolumePerTx = data.config.limits.maxVolumePerTx,
        maxVolumePerPeriod = data.config.limits.maxVolumePerPeriod,
        maxNumTxsPerPeriod = data.config.limits.maxNumTxsPerPeriod,
        txCooldownBlocks = data.config.limits.txCooldownBlocks,
        canManageYield = data.config.legoPerms.canManageYield,
        canBuyAndSell = data.config.legoPerms.canBuyAndSell,
        canManageDebt = data.config.legoPerms.canManageDebt,
        canManageLiq = data.config.legoPerms.canManageLiq,
        canClaimRewards = data.config.legoPerms.canClaimRewards,
        numAllowedLegos = len(data.config.legoPerms.allowedLegos),
        canTransfer = data.config.transferPerms.canTransfer,
        canCreateCheque = data.config.transferPerms.canCreateCheque,
        canAddPendingRecipient = data.config.transferPerms.canAddPendingRecipient,
        numAllowedRecipients = len(data.config.transferPerms.allowedRecipients),
        numAllowedAssets = len(data.config.allowedAssets),
    )
    return True


# cancel global manager settings


@external
def cancelPendingGlobalManagerSettings() -> bool:
    assert msg.sender == self.owner # dev: no perms

    data: PendingGlobalManagerSettings = self.pendingGlobalManagerSettings
    assert data.confirmBlock != 0 # dev: no pending change
    self.pendingGlobalManagerSettings = empty(PendingGlobalManagerSettings)

    log GlobalManagerSettingsModified(
        state = "CANCELLED",
        managerPeriod = data.config.managerPeriod,
        startDelay = data.config.startDelay,
        activationLength = data.config.activationLength,
        maxVolumePerTx = data.config.limits.maxVolumePerTx,
        maxVolumePerPeriod = data.config.limits.maxVolumePerPeriod,
        maxNumTxsPerPeriod = data.config.limits.maxNumTxsPerPeriod,
        txCooldownBlocks = data.config.limits.txCooldownBlocks,
        canManageYield = data.config.legoPerms.canManageYield,
        canBuyAndSell = data.config.legoPerms.canBuyAndSell,
        canManageDebt = data.config.legoPerms.canManageDebt,
        canManageLiq = data.config.legoPerms.canManageLiq,
        canClaimRewards = data.config.legoPerms.canClaimRewards,
        numAllowedLegos = len(data.config.legoPerms.allowedLegos),
        canTransfer = data.config.transferPerms.canTransfer,
        canCreateCheque = data.config.transferPerms.canCreateCheque,
        canAddPendingRecipient = data.config.transferPerms.canAddPendingRecipient,
        numAllowedRecipients = len(data.config.transferPerms.allowedRecipients),
        numAllowedAssets = len(data.config.allowedAssets),
    )
    return True


#############################
# Specific Manager Settings #
#############################


# set manager settings


@external
def setSpecificManagerSettings(
    _manager: address,
    _limits: Limits,
    _legoPerms: LegoPerms,
    _transferPerms: TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
    _startDelay: uint256 = 0,
    _activationLength: uint256 = 0,
) -> bool:
    assert msg.sender == self.owner # dev: no perms

    # validation
    assert _manager not in [empty(address), self.owner] # dev: invalid manager
    assert self._isValidLimits(_limits) # dev: invalid limits
    assert self._isValidLegoPerms(_legoPerms) # dev: invalid lego perms
    assert self._isValidTransferPerms(_transferPerms) # dev: invalid transfer perms
    assert self._isValidAllowedAssets(_allowedAssets) # dev: invalid allowed assets

    config: ManagerSettings = empty(ManagerSettings)
    stateStr: String[10] = empty(String[10])

    # existing manager
    alreadyRegistered: bool = self.indexOfManager[_manager] != 0
    if alreadyRegistered:
        config = self.managerSettings[_manager]
        config.limits = _limits
        config.legoPerms = _legoPerms
        config.transferPerms = _transferPerms
        config.allowedAssets = _allowedAssets
        stateStr = "UPDATED"
    
    # new manager
    else:
        config = ManagerSettings(
            startBlock = 0,
            expiryBlock = 0,
            limits = _limits,
            legoPerms = _legoPerms,
            transferPerms = _transferPerms,
            allowedAssets = _allowedAssets,
        )
        config.startBlock, config.expiryBlock = self._getStartAndExpiryBlocksForNewManager(_startDelay, _activationLength)
        self._registerManager(_manager)
        stateStr = "ADDED"

    # update config
    self.managerSettings[_manager] = config

    log ManagerSettingsModified(
        manager = _manager,
        state = stateStr,
        startBlock = config.startBlock,
        expiryBlock = config.expiryBlock,
        maxVolumePerTx = config.limits.maxVolumePerTx,
        maxVolumePerPeriod = config.limits.maxVolumePerPeriod,
        maxNumTxsPerPeriod = config.limits.maxNumTxsPerPeriod,
        txCooldownBlocks = config.limits.txCooldownBlocks,
        canManageYield = config.legoPerms.canManageYield,
        canBuyAndSell = config.legoPerms.canBuyAndSell,
        canManageDebt = config.legoPerms.canManageDebt,
        canManageLiq = config.legoPerms.canManageLiq,
        canClaimRewards = config.legoPerms.canClaimRewards,
        numAllowedLegos = len(config.legoPerms.allowedLegos),
        canTransfer = config.transferPerms.canTransfer,
        canCreateCheque = config.transferPerms.canCreateCheque,
        canAddPendingRecipient = config.transferPerms.canAddPendingRecipient,
        numAllowedRecipients = len(config.transferPerms.allowedRecipients),
        numAllowedAssets = len(config.allowedAssets),
    )
    return True


# remove manager


@external
def removeSpecificManager(_manager: address) -> bool:
    assert msg.sender == self.owner # dev: no perms
    assert self.indexOfManager[_manager] != 0 # dev: manager not found

    self.managerSettings[_manager] = empty(ManagerSettings)
    self.managerPeriodData[_manager] = empty(ManagerData)
    self._deregisterManager(_manager)

    log ManagerRemoved(manager = _manager)
    return True


# adjust activation length


@external
def adjustSpecificManagerActivationLength(_manager: address, _activationLength: uint256, _shouldResetStartBlock: bool = False) -> bool:
    assert msg.sender == self.owner # dev: no perms

    # validation
    assert self.indexOfManager[_manager] != 0 # dev: manager not found
    config: ManagerSettings = self.managerSettings[_manager]
    assert config.startBlock < block.number # dev: manager not active yet
    assert self._isValidActivationLength(_activationLength) # dev: invalid activation length

    # update config
    didRestart: bool = False
    if config.expiryBlock < block.number or _shouldResetStartBlock:
        config.startBlock = block.number
        didRestart = True
    config.expiryBlock = config.startBlock + _activationLength
    self.managerSettings[_manager] = config

    log ManagerActivationLengthAdjusted(
        manager = _manager,
        activationLength = _activationLength,
        didRestart = didRestart,
    )
    return True


##########################
# Manager Settings Utils #
##########################


@view
@external
def isManager(_manager: address) -> bool:
    return self.indexOfManager[_manager] != 0


@view
@internal
def _getStartAndExpiryBlocksForNewManager(_startDelay: uint256, _activationLength: uint256) -> (uint256, uint256):
    config: GlobalManagerSettings = self.globalManagerSettings

    startDelay: uint256 = config.startDelay
    if _startDelay != 0:
        startDelay = max(startDelay, _startDelay) # using max here as extra protection
    assert self._isValidStartDelay(startDelay) # dev: invalid start delay

    activationLength: uint256 = config.activationLength
    if _activationLength != 0:
        activationLength = min(activationLength, _activationLength)
    assert self._isValidActivationLength(activationLength) # dev: invalid activation length

    startBlock: uint256 = block.number + startDelay
    expiryBlock: uint256 = startBlock + activationLength
    return startBlock, expiryBlock


@view
@internal
def _isValidLimits(_limits: Limits) -> bool:
    # Note: 0 values are treated as "unlimited" throughout this validation
    
    # only validate if both values are non-zero (not unlimited)
    if _limits.maxVolumePerTx != 0 and _limits.maxVolumePerPeriod != 0:
        if _limits.maxVolumePerTx > _limits.maxVolumePerPeriod:
            return False

    # cooldown cannot exceed period length (unless cooldown is 0 = no cooldown)
    if _limits.txCooldownBlocks != 0 and _limits.txCooldownBlocks > self.globalManagerSettings.managerPeriod:
        return False

    return True


@view
@internal
def _isValidLegoPerms(_legoPerms: LegoPerms) -> bool:
    if len(_legoPerms.allowedLegos) == 0:
        return True

    canDoAnything: bool = _legoPerms.canManageYield or _legoPerms.canBuyAndSell or _legoPerms.canManageDebt or _legoPerms.canManageLiq or _legoPerms.canClaimRewards

    # _allowedLegos should be empty if there are no permissions
    if not canDoAnything:
        return False

    # if in eject mode, can't add legos as permissions
    if self.inEjectMode:
        return False

    legoBook: address = staticcall Registry(UNDY_HQ).getAddr(LEGO_BOOK_ID)
    if legoBook == empty(address):
        return False

    checkedLegos: DynArray[uint256, MAX_CONFIG_LEGOS] = []
    for i: uint256 in _legoPerms.allowedLegos:
        if not staticcall Registry(legoBook).isValidRegId(i):
            return False

        # duplicates are not allowed
        if i in checkedLegos:
            return False
        checkedLegos.append(i)

    return True


@view
@internal
def _isValidTransferPerms(_transferPerms: TransferPerms) -> bool:
    if len(_transferPerms.allowedRecipients) == 0:
        return True

    canDoAnything: bool = _transferPerms.canTransfer or _transferPerms.canCreateCheque or _transferPerms.canAddPendingRecipient

    # _allowedRecipients should be empty if there are no permissions
    if not canDoAnything:
        return False

    checkedRecipients: DynArray[address, MAX_CONFIG_RECIPIENTS] = []
    for i: address in _transferPerms.allowedRecipients:
        if i == empty(address):
            return False

        # check if recipient is valid
        if not self._isValidRecipient(i):
            return False

        # duplicates are not allowed
        if i in checkedRecipients:
            return False
        checkedRecipients.append(i)

    return True


@view
@internal
def _isValidAllowedAssets(_allowedAssets: DynArray[address, MAX_CONFIG_ASSETS]) -> bool:
    if len(_allowedAssets) == 0:
        return True

    checkedAssets: DynArray[address, MAX_CONFIG_ASSETS] = []
    for i: address in _allowedAssets:
        if i == empty(address):
            return False

        # duplicates are not allowed
        if i in checkedAssets:
            return False
        checkedAssets.append(i)

    return True


@view
@internal
def _isValidStartDelay(_startDelay: uint256) -> bool:
    return _startDelay <= 6 * ONE_MONTH_IN_BLOCKS


@view
@internal
def _isValidManagerPeriod(_managerPeriod: uint256) -> bool:
    return _managerPeriod >= MIN_MANAGER_PERIOD and _managerPeriod <= MAX_MANAGER_PERIOD


@view
@internal
def _isValidActivationLength(_numBlocks: uint256) -> bool:
    return _numBlocks <= 5 * ONE_YEAR_IN_BLOCKS and _numBlocks >= ONE_DAY_IN_BLOCKS


@pure
@internal
def _createHappyDefaults() -> (LegoPerms, TransferPerms):
    return LegoPerms(
        canManageYield = True,
        canBuyAndSell = True,
        canManageDebt = True,
        canManageLiq = True,
        canClaimRewards = True,
        allowedLegos = [],
    ), TransferPerms(
        canTransfer = True,
        canCreateCheque = True,
        canAddPendingRecipient = True,
        allowedRecipients = [],
    )


# register / deregister manager


@internal
def _registerManager(_manager: address):
    mid: uint256 = self.numManagers
    if mid == 0:
        mid = 1 # not using 0 index
    self.managers[mid] = _manager
    self.indexOfManager[_manager] = mid
    self.numManagers = mid + 1


@internal
def _deregisterManager(_manager: address) -> bool:
    numManagers: uint256 = self.numManagers
    if numManagers == 0:
        return False

    targetIndex: uint256 = self.indexOfManager[_manager]
    if targetIndex == 0:
        return False

    # update data
    lastIndex: uint256 = numManagers - 1
    self.numManagers = lastIndex
    self.indexOfManager[_manager] = 0

    # get last item, replace the removed item
    if targetIndex != lastIndex:
        lastItem: address = self.managers[lastIndex]
        self.managers[targetIndex] = lastItem
        self.indexOfManager[lastItem] = targetIndex

    return True


#############
# Migration #
#############


# migrate funds


@external
def migrateFunds(_newWallet: address) -> uint256:
    owner: address = self.owner
    assert msg.sender == owner # dev: no perms

    wallet: address = self.wallet
    assert self._canMigrateToNewWallet(_newWallet, owner, wallet) # dev: cannot migrate to new wallet

    numAssets: uint256 = staticcall UserWallet(wallet).numAssets()
    if numAssets == 0:
        return 0

    # transfer tokens
    numMigrated: uint256 = 0
    for i: uint256 in range(1, numAssets, bound=max_value(uint256)):           
        asset: address = staticcall UserWallet(wallet).assets(i)
        if asset == empty(address):
            continue

        balance: uint256 = staticcall IERC20(asset).balanceOf(wallet)
        if balance != 0:
            extcall wi(_newWallet).transferFunds(_newWallet, asset)
        numMigrated += 1

    return numMigrated


@view
@internal
def _canMigrateToNewWallet(_newWallet: address, _owner: address, _thisWallet: address) -> bool:
    ledger: address = staticcall Registry(UNDY_HQ).getAddr(LEDGER_ID)

    # initial validation
    assert staticcall Ledger(ledger).isUserWallet(_newWallet) # dev: not a user wallet
    assert staticcall UserWallet(_thisWallet).trialFundsAmount() == 0 # dev: has trial funds
    assert not self.isFrozen # dev: frozen

    # wallet config checks
    newWalletConfig: address = staticcall UserWallet(_newWallet).walletConfig()
    assert self._isMatchingOwnership(newWalletConfig, _owner) # dev: not same owner
    assert self._hasNoManagers(newWalletConfig) # dev: has managers

    # TODO
    # TODO: once there is proper transfer/whitelist, let's check that is empty also
    # TODO

    return True


# migrate settings


@external
def migrateSettings(_oldWallet: address):
    owner: address = self.owner
    assert msg.sender == owner # dev: no perms
    assert self._canMigrateSettings(_oldWallet, owner) # dev: cannot migrate settings

    # TODO: migrate all settings


@view
@internal
def _canMigrateSettings(_oldWallet: address, _owner: address) -> bool:
    ledger: address = staticcall Registry(UNDY_HQ).getAddr(LEDGER_ID)
    assert staticcall Ledger(ledger).isUserWallet(_oldWallet) # dev: not a user wallet

    oldWalletConfig: address = staticcall UserWallet(_oldWallet).walletConfig()
    assert self._isMatchingOwnership(oldWalletConfig, _owner) # dev: not same owner
    assert self._hasNoManagers(self) # dev: has managers

    # TODO
    # TODO: once there is proper transfer/whitelist, let's check that is empty also
    # TODO

    return True


# shared utils


@view
@internal
def _isMatchingOwnership(_walletConfig: address, _owner: address) -> bool:
    assert _owner == staticcall UserWalletConfig(_walletConfig).owner() # dev: not same owner
    assert not staticcall UserWalletConfig(_walletConfig).hasPendingOwnerChange() # dev: pending owner change
    assert not self._hasPendingOwnerChange() # dev: pending owner change
    assert self.groupId == staticcall UserWalletConfig(_walletConfig).groupId() # dev: wrong group id
    return True


@view
@internal
def _hasNoManagers(_walletConfig: address) -> bool:
    startingAgent: address = staticcall UserWalletConfig(_walletConfig).startingAgent()
    if startingAgent == empty(address):
        assert staticcall UserWalletConfig(_walletConfig).numManagers() == 0 # dev: has managers
    else:
        assert staticcall UserWalletConfig(_walletConfig).indexOfManager(startingAgent) == 1 # dev: invalid manager
        assert staticcall UserWalletConfig(_walletConfig).numManagers() == 2 # dev: has other managers
    return True


#########
# TO DO #
#########


@view
@external
def canTransferToRecipient(_recipient: address) -> bool:
    return True


@view
@internal
def _isValidRecipient(_recipient: address) -> bool:

    # TODO: hook this up

    return True
