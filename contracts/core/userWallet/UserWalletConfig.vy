# @version 0.4.3
# pragma optimize codesize

from interfaces import Wallet as wi
from ethereum.ercs import IERC721

interface UserWalletConfig:
    def managerSettings(_manager: address) -> ManagerSettings: view
    def globalManagerSettings() -> GlobalManagerSettings: view
    def payeeSettings(_payee: address) -> PayeeSettings: view
    def globalPayeeSettings() -> GlobalPayeeSettings: view
    def whitelistAddr(i: uint256) -> address: view
    def managers(i: uint256) -> address: view
    def payees(i: uint256) -> address: view
    def numWhitelisted() -> uint256: view
    def numManagers() -> uint256: view
    def numPayees() -> uint256: view
    def owner() -> address: view

interface UserWallet:
    def preparePayment(_legoId: uint256, _vaultToken: address, _vaultAmount: uint256 = max_value(uint256), _ad: ActionData = empty(ActionData)) -> (uint256, address, uint256, uint256): nonpayable
    def transferFundsTrusted(_recipient: address, _asset: address = empty(address), _amount: uint256 = max_value(uint256), _ad: ActionData = empty(ActionData)) -> (uint256, uint256): nonpayable
    def updateAssetData(_legoId: uint256, _asset: address, _shouldCheckYield: bool, _totalUsdValue: uint256, _ad: ActionData = empty(ActionData)) -> uint256: nonpayable
    def assets(i: uint256) -> address: view
    def walletConfig() -> address: view
    def numAssets() -> uint256: view

interface BossValidator:
    def canSignerPerformActionWithConfig(_isOwner: bool, _isManager: bool, _data: ManagerData, _config: ManagerSettings, _globalConfig: GlobalManagerSettings, _userWalletConfig: address, _action: wi.ActionType, _assets: DynArray[address, MAX_ASSETS] = [], _legoIds: DynArray[uint256, MAX_LEGOS] = [], _transferRecipient: address = empty(address)) -> bool: view
    def checkManagerUsdLimitsAndUpdateData(_txUsdValue: uint256, _specificLimits: ManagerLimits, _globalLimits: ManagerLimits, _managerPeriod: uint256, _data: ManagerData) -> ManagerData: view
    def createDefaultGlobalManagerSettings(_managerPeriod: uint256, _minTimeLock: uint256, _defaultActivationLength: uint256) -> GlobalManagerSettings: view
    def createStarterAgentSettings(_startingAgentActivationLength: uint256) -> ManagerSettings: view

interface Paymaster:
    def isValidPayeeWithConfig(_isWhitelisted: bool, _isOwner: bool, _isPayee: bool, _asset: address, _amount: uint256, _txUsdValue: uint256, _config: PayeeSettings, _globalConfig: GlobalPayeeSettings, _data: PayeeData) -> (bool, PayeeData): view
    def createDefaultGlobalPayeeSettings(_defaultPeriodLength: uint256, _startDelay: uint256, _activationLength: uint256) -> GlobalPayeeSettings: view

interface LootDistributor:
    def updateDepositPointsWithData(_user: address, _newUserValue: uint256, _didChange: bool): nonpayable

interface Migrator:
    def canMigrateFundsToNewWallet(_newWallet: address, _thisWallet: address) -> bool: view

interface Ledger:
    def getLastTotalUsdValue(_user: address) -> uint256: view

interface Switchboard:
    def isSwitchboardAddr(_addr: address) -> bool: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

struct ActionData:
    missionControl: address
    legoBook: address
    switchboard: address
    hatchery: address
    lootDistributor: address
    appraiser: address
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

struct RecipientConfigBundle:
    isWhitelisted: bool
    isOwner: bool
    isPayee: bool
    config: PayeeSettings
    globalConfig: GlobalPayeeSettings
    data: PayeeData

struct ManagerConfigBundle:
    isOwner: bool
    isManager: bool
    config: ManagerSettings
    globalConfig: GlobalManagerSettings
    data: ManagerData

struct ManagerSettingsBundle:
    owner: address
    isManager: bool
    bossValidator: address
    timeLock: uint256
    inEjectMode: bool
    walletConfig: address
    legoBook: address

struct WhitelistConfigBundle:
    owner: address
    wallet: address
    isWhitelisted: bool
    pendingWhitelist: PendingWhitelist
    timeLock: uint256
    walletConfig: address
    inEjectMode: bool
    isManager: bool
    isOwner: bool
    whitelistPerms: WhitelistPerms
    globalWhitelistPerms: WhitelistPerms

struct MigrationConfigBundle:
    owner: address
    trialFundsAmount: uint256
    isFrozen: bool
    numPayees: uint256
    numWhitelisted: uint256
    numManagers: uint256
    startingAgent: address
    startingAgentIndex: uint256
    hasPendingOwnerChange: bool
    groupId: uint256
    didMigrateSettings: bool
    didMigrateFunds: bool

struct PayeeManagementBundle:
    owner: address
    wallet: address
    isRegisteredPayee: bool
    isWhitelisted: bool
    isManager: bool
    payeeSettings: PayeeSettings
    globalPayeeSettings: GlobalPayeeSettings
    timeLock: uint256
    walletConfig: address
    inEjectMode: bool

struct ManagerData:
    numTxsInPeriod: uint256
    totalUsdValueInPeriod: uint256
    totalNumTxs: uint256
    totalUsdValue: uint256
    lastTxBlock: uint256
    periodStartBlock: uint256

struct ManagerSettings:
    startBlock: uint256
    expiryBlock: uint256
    limits: ManagerLimits
    legoPerms: LegoPerms
    whitelistPerms: WhitelistPerms
    transferPerms: TransferPerms
    allowedAssets: DynArray[address, MAX_CONFIG_ASSETS]

struct GlobalManagerSettings:
    managerPeriod: uint256
    startDelay: uint256
    activationLength: uint256
    canOwnerManage: bool
    limits: ManagerLimits
    legoPerms: LegoPerms
    whitelistPerms: WhitelistPerms
    transferPerms: TransferPerms
    allowedAssets: DynArray[address, MAX_CONFIG_ASSETS]

struct ManagerLimits:
    maxUsdValuePerTx: uint256
    maxUsdValuePerPeriod: uint256
    maxUsdValueLifetime: uint256
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

struct WhitelistPerms:
    canAddPending: bool
    canConfirm: bool
    canCancel: bool
    canRemove: bool

struct TransferPerms:
    canTransfer: bool
    canCreateCheque: bool
    canAddPendingPayee: bool
    allowedPayees: DynArray[address, MAX_ALLOWED_PAYEES]

struct PayeeData:
    numTxsInPeriod: uint256
    totalUnitsInPeriod: uint256
    totalUsdValueInPeriod: uint256
    totalNumTxs: uint256
    totalUnits: uint256
    totalUsdValue: uint256
    lastTxBlock: uint256
    periodStartBlock: uint256

struct PayeeSettings:
    startBlock: uint256
    expiryBlock: uint256
    canPull: bool
    periodLength: uint256
    maxNumTxsPerPeriod: uint256
    txCooldownBlocks: uint256
    failOnZeroPrice: bool
    primaryAsset: address
    onlyPrimaryAsset: bool
    unitLimits: PayeeLimits
    usdLimits: PayeeLimits

struct GlobalPayeeSettings:
    defaultPeriodLength: uint256
    startDelay: uint256
    activationLength: uint256
    maxNumTxsPerPeriod: uint256
    txCooldownBlocks: uint256
    failOnZeroPrice: bool
    usdLimits: PayeeLimits
    canPayOwner: bool

struct PayeeLimits:
    perTxCap: uint256
    perPeriodCap: uint256
    lifetimeCap: uint256

struct PendingPayee:
    settings: PayeeSettings
    initiatedBlock: uint256
    confirmBlock: uint256

struct PendingWhitelist:
    initiatedBlock: uint256
    confirmBlock: uint256

struct PendingOwnerChange:
    newOwner: address
    initiatedBlock: uint256
    confirmBlock: uint256

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

event FrozenSet:
    isFrozen: bool
    caller: indexed(address)

event NftRecovered:
    collection: indexed(address)
    nftTokenId: uint256
    recipient: indexed(address)

# core
wallet: public(address)
groupId: public(uint256)
owner: public(address)
pendingOwner: public(PendingOwnerChange)

# helper contracts
bossValidator: public(address)
paymaster: public(address)
migrator: public(address)

# trial funds info
trialFundsAsset: public(address)
trialFundsAmount: public(uint256)

# managers
managerSettings: public(HashMap[address, ManagerSettings])
managerPeriodData: public(HashMap[address, ManagerData])
managers: public(HashMap[uint256, address]) # index -> manager
indexOfManager: public(HashMap[address, uint256]) # manager -> index
numManagers: public(uint256) # num managers

# payees
payeeSettings: public(HashMap[address, PayeeSettings])
payeePeriodData: public(HashMap[address, PayeeData])
payees: public(HashMap[uint256, address]) # index -> payee
indexOfPayee: public(HashMap[address, uint256]) # payee -> index
numPayees: public(uint256) # num payees
pendingPayees: public(HashMap[address, PendingPayee])

# whitelist
whitelistAddr: public(HashMap[uint256, address]) # index -> whitelist
indexOfWhitelist: public(HashMap[address, uint256]) # whitelist -> index
numWhitelisted: public(uint256) # num whitelisted
pendingWhitelist: public(HashMap[address, PendingWhitelist]) # addr -> pending whitelist

# global config
globalManagerSettings: public(GlobalManagerSettings)
globalPayeeSettings: public(GlobalPayeeSettings)

# config
timeLock: public(uint256)
isFrozen: public(bool)
inEjectMode: public(bool)

startingAgent: public(address)
didSetWallet: public(bool)
didMigrateFunds: public(bool)
didMigrateSettings: public(bool)

API_VERSION: constant(String[28]) = "0.1.0"

MAX_CONFIG_ASSETS: constant(uint256) = 40
MAX_CONFIG_LEGOS: constant(uint256) = 25
MAX_ALLOWED_PAYEES: constant(uint256) = 40
MAX_ASSETS: constant(uint256) = 10
MAX_LEGOS: constant(uint256) = 10

# registry ids
LEDGER_ID: constant(uint256) = 2
MISSION_CONTROL_ID: constant(uint256) = 3
LEGO_BOOK_ID: constant(uint256) = 4
SWITCHBOARD_ID: constant(uint256) = 5
HATCHERY_ID: constant(uint256) = 6
LOOT_DISTRIBUTOR_ID: constant(uint256) = 7
APPRAISER_ID: constant(uint256) = 8

UNDY_HQ: public(immutable(address))
WETH: public(immutable(address))
ETH: public(immutable(address))

MIN_TIMELOCK: public(immutable(uint256))
MAX_TIMELOCK: public(immutable(uint256))


@deploy
def __init__(
    _undyHq: address,
    _owner: address,
    _groupId: uint256,
    # key contracts
    _bossValidator: address,
    _paymaster: address,
    _migrator: address,
    # initial agent
    _startingAgent: address,
    _startingAgentActivationLength: uint256,
    # default manager settings
    _managerPeriod: uint256,
    _managerActivationLength: uint256,
    # default payee settings
    _payeePeriod: uint256,
    _payeeActivationLength: uint256,
    # trial funds
    _trialFundsAsset: address,
    _trialFundsAmount: uint256,
    # key addrs
    _wethAddr: address,
    _ethAddr: address,
    # timelock
    _minTimeLock: uint256,
    _maxTimeLock: uint256,
):
    assert empty(address) not in [_undyHq, _owner, _bossValidator, _paymaster, _wethAddr, _ethAddr] # dev: invalid addrs
    UNDY_HQ = _undyHq
    WETH = _wethAddr
    ETH = _ethAddr

    # core
    self.owner = _owner
    self.groupId = _groupId

    # set key addrs
    self.bossValidator = _bossValidator
    self.paymaster = _paymaster
    self.migrator = _migrator

    # trial funds info
    if _trialFundsAsset != empty(address) and _trialFundsAmount != 0:   
        self.trialFundsAsset = _trialFundsAsset
        self.trialFundsAmount = _trialFundsAmount

    # timelock
    assert _minTimeLock != 0 and _minTimeLock < _maxTimeLock # dev: invalid delay
    MIN_TIMELOCK = _minTimeLock
    MAX_TIMELOCK = _maxTimeLock
    self.timeLock = _minTimeLock

    # set global manager settings
    self.globalManagerSettings = staticcall BossValidator(_bossValidator).createDefaultGlobalManagerSettings(_managerPeriod, _minTimeLock, _managerActivationLength)

    # initial agent
    if _startingAgent != empty(address):
        self.managerSettings[_startingAgent] = staticcall BossValidator(_bossValidator).createStarterAgentSettings(_startingAgentActivationLength)
        self.startingAgent = _startingAgent
        self._registerManager(_startingAgent)

    # set global payee settings using defaults from paymaster
    payeePeriod: uint256 = _payeePeriod
    payeeActivationLength: uint256 = _payeeActivationLength
    if _payeePeriod == 0 or _payeeActivationLength == 0:
        payeePeriod = _managerPeriod
        payeeActivationLength = _managerActivationLength
    self.globalPayeeSettings = staticcall Paymaster(_paymaster).createDefaultGlobalPayeeSettings(payeePeriod, _minTimeLock, payeeActivationLength)


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


##################
# Manager Limits #
##################


# pre action


@view
@external
def checkSignerPermissionsAndGetBundle(
    _signer: address,
    _action: wi.ActionType,
    _assets: DynArray[address, MAX_ASSETS] = [],
    _legoIds: DynArray[uint256, MAX_LEGOS] = [],
    _transferRecipient: address = empty(address),
) -> ActionData:
    legoId: uint256 = 0
    if len(_legoIds) != 0:
        legoId = _legoIds[0]

    # main data for this transaction
    ad: ActionData = self._getActionDataBundle(legoId, _signer)

    # main validation
    c: ManagerConfigBundle = self._getManagerConfigs(_signer, ad.walletOwner)
    assert staticcall BossValidator(self.bossValidator).canSignerPerformActionWithConfig(c.isOwner, c.isManager, c.data, c.config, c.globalConfig, ad.walletConfig, _action, _assets, _legoIds, _transferRecipient) # dev: no permission

    # signer is not owner
    if not c.isOwner:
        ad.isManager = True

    return ad


# post action (usd value limits)


@external
def checkManagerUsdLimitsAndUpdateData(_manager: address, _txUsdValue: uint256) -> bool:
    assert msg.sender == self.wallet # dev: no perms

    config: ManagerSettings = self.managerSettings[_manager]
    globalConfig: GlobalManagerSettings = self.globalManagerSettings
    data: ManagerData = staticcall BossValidator(self.bossValidator).checkManagerUsdLimitsAndUpdateData(_txUsdValue, config.limits, globalConfig.limits, globalConfig.managerPeriod, self.managerPeriodData[_manager])
    self.managerPeriodData[_manager] = data
    return True


####################
# Recipient Limits #
####################


@external
def checkRecipientLimitsAndUpdateData(
    _recipient: address,
    _txUsdValue: uint256,
    _asset: address,
    _amount: uint256,
) -> bool:
    assert msg.sender == self.wallet # dev: no perms

    c: RecipientConfigBundle = self._getRecipientConfigs(_recipient)

    # check if payee is valid
    canPayRecipient: bool = False
    data: PayeeData = empty(PayeeData)
    canPayRecipient, data = staticcall Paymaster(self.paymaster).isValidPayeeWithConfig(c.isWhitelisted, c.isOwner, c.isPayee, _asset, _amount, _txUsdValue, c.config, c.globalConfig, c.data)

    # !!!!
    assert canPayRecipient # dev: invalid payee

    # only save if data was updated  
    if data.lastTxBlock != 0:
        self.payeePeriodData[_recipient] = data
    
    return True


# recipient config bundle


@view
@external
def getRecipientConfigs(_recipient: address) -> RecipientConfigBundle:
    return self._getRecipientConfigs(_recipient)


@view
@internal
def _getRecipientConfigs(_recipient: address) -> RecipientConfigBundle:
    isWhitelisted: bool = self._isWhitelisted(_recipient)

    isOwner: bool = False
    isPayee: bool = False
    config: PayeeSettings = empty(PayeeSettings)
    globalConfig: GlobalPayeeSettings = empty(GlobalPayeeSettings)
    data: PayeeData = empty(PayeeData)
    if not isWhitelisted:
        isOwner = _recipient == self.owner
        isPayee = self._isRegisteredPayee(_recipient)
        config = self.payeeSettings[_recipient]
        globalConfig = self.globalPayeeSettings
        data = self.payeePeriodData[_recipient]

    return RecipientConfigBundle(
        isWhitelisted = isWhitelisted,
        isOwner = isOwner,
        isPayee = isPayee,
        config = config,
        globalConfig = globalConfig,
        data = data,
    )


#############
# Ownership #
#############


# change ownership


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
    log OwnershipChangeInitiated(prevOwner = currentOwner, newOwner = _newOwner, confirmBlock = confirmBlock)


# confirm ownership change


@external
def confirmOwnershipChange():
    data: PendingOwnerChange = self.pendingOwner
    assert data.newOwner != empty(address) # dev: no pending owner
    assert data.confirmBlock != 0 and block.number >= data.confirmBlock # dev: time delay not reached
    assert msg.sender == data.newOwner # dev: only new owner can confirm

    prevOwner: address = self.owner
    self.owner = data.newOwner
    self.pendingOwner = empty(PendingOwnerChange)
    log OwnershipChangeConfirmed(prevOwner = prevOwner, newOwner = data.newOwner, initiatedBlock = data.initiatedBlock, confirmBlock = data.confirmBlock)


# cancel ownership change


@external
def cancelOwnershipChange():
    if not self._isSwitchboardAddr(msg.sender, self.inEjectMode):
        assert msg.sender == self.owner # dev: no perms

    data: PendingOwnerChange = self.pendingOwner
    assert data.confirmBlock != 0 # dev: no pending change
    self.pendingOwner = empty(PendingOwnerChange)
    log OwnershipChangeCancelled(cancelledOwner = data.newOwner, cancelledBy = msg.sender, initiatedBlock = data.initiatedBlock, confirmBlock = data.confirmBlock)


# utilities


@view
@external
def hasPendingOwnerChange() -> bool:
    return self._hasPendingOwnerChange()


@view
@internal
def _hasPendingOwnerChange() -> bool:
    return self.pendingOwner.confirmBlock != 0


# time lock


@external
def setTimeLock(_numBlocks: uint256):
    assert msg.sender == self.owner # dev: no perms
    assert _numBlocks >= MIN_TIMELOCK and _numBlocks <= MAX_TIMELOCK # dev: invalid delay
    self.timeLock = _numBlocks
    log TimeLockSet(numBlocks=_numBlocks)


####################
# Manager Settings #
####################


@view
@external
def isManager(_manager: address) -> bool:
    return self._isManager(_manager)


@view
@internal
def _isManager(_manager: address) -> bool:
    return self.indexOfManager[_manager] != 0


# global manager settings


@external
def setGlobalManagerSettings(_config: GlobalManagerSettings):
    assert msg.sender in [self.bossValidator, self.migrator] # dev: no perms
    self.globalManagerSettings = _config


# add manager


@external
def addManager(_manager: address, _config: ManagerSettings):
    assert msg.sender in [self.bossValidator, self.migrator] # dev: no perms
    self.managerSettings[_manager] = _config
    self._registerManager(_manager)


@internal
def _registerManager(_manager: address):
    if self._isManager(_manager):
        return

    mid: uint256 = self.numManagers
    if mid == 0:
        mid = 1 # not using 0 index
    self.managers[mid] = _manager
    self.indexOfManager[_manager] = mid
    self.numManagers = mid + 1
    

# update manager


@external
def updateManager(_manager: address, _config: ManagerSettings):
    assert msg.sender == self.bossValidator # dev: no perms
    self.managerSettings[_manager] = _config


# remove manager


@external
def removeManager(_manager: address):
    assert msg.sender == self.bossValidator # dev: no perms

    numManagers: uint256 = self.numManagers
    if numManagers == 0:
        return

    targetIndex: uint256 = self.indexOfManager[_manager]
    if targetIndex == 0:
        return

    self.managerSettings[_manager] = empty(ManagerSettings)
    self.managerPeriodData[_manager] = empty(ManagerData)

    # update data
    lastIndex: uint256 = numManagers - 1
    self.numManagers = lastIndex
    self.indexOfManager[_manager] = 0

    # get last item, replace the removed item
    if targetIndex != lastIndex:
        lastItem: address = self.managers[lastIndex]
        self.managers[targetIndex] = lastItem
        self.indexOfManager[lastItem] = targetIndex


# manager config bundle


@view
@external
def getManagerConfigs(_signer: address) -> ManagerConfigBundle:
    return self._getManagerConfigs(_signer, self.owner)


@view
@internal
def _getManagerConfigs(_signer: address, _walletOwner: address) -> ManagerConfigBundle:
    return ManagerConfigBundle(
        isOwner = _signer == _walletOwner,
        isManager = self.indexOfManager[_signer] != 0,
        config = self.managerSettings[_signer],
        globalConfig = self.globalManagerSettings,
        data = self.managerPeriodData[_signer],
    )


# manager settings bundle


@view
@external
def getManagerSettingsBundle(_manager: address) -> ManagerSettingsBundle:
    return ManagerSettingsBundle(
        owner = self.owner,
        isManager = self._isManager(_manager),
        bossValidator = self.bossValidator,
        timeLock = self.timeLock,
        inEjectMode = self.inEjectMode,
        walletConfig = self,
        legoBook = staticcall Registry(UNDY_HQ).getAddr(LEGO_BOOK_ID),
    )


##################
# Payee Settings #
##################


@view
@external
def isRegisteredPayee(_addr: address) -> bool:
    return self._isRegisteredPayee(_addr)


@view
@internal
def _isRegisteredPayee(_addr: address) -> bool:
    return self.indexOfPayee[_addr] != 0


# global payee settings


@external
def setGlobalPayeeSettings(_config: GlobalPayeeSettings):
    assert msg.sender in [self.paymaster, self.migrator] # dev: no perms
    self.globalPayeeSettings = _config


# add payee


@external
def addPayee(_payee: address, _config: PayeeSettings):
    assert msg.sender in [self.paymaster, self.migrator] # dev: no perms
    self.payeeSettings[_payee] = _config
    self._registerPayee(_payee)


@internal
def _registerPayee(_payee: address):
    if self._isRegisteredPayee(_payee):
        return

    pid: uint256 = self.numPayees
    if pid == 0:
        pid = 1 # not using 0 index
    self.payees[pid] = _payee
    self.indexOfPayee[_payee] = pid
    self.numPayees = pid + 1
    

# update payee


@external
def updatePayee(_payee: address, _config: PayeeSettings):
    assert msg.sender == self.paymaster # dev: no perms
    self.payeeSettings[_payee] = _config


# remove payee


@external
def removePayee(_payee: address):
    assert msg.sender == self.paymaster # dev: no perms

    numPayees: uint256 = self.numPayees
    if numPayees == 0:
        return

    targetIndex: uint256 = self.indexOfPayee[_payee]
    if targetIndex == 0:
        return

    self.payeeSettings[_payee] = empty(PayeeSettings)
    self.payeePeriodData[_payee] = empty(PayeeData)

    # update data
    lastIndex: uint256 = numPayees - 1
    self.numPayees = lastIndex
    self.indexOfPayee[_payee] = 0

    # get last item, replace the removed item
    if targetIndex != lastIndex:
        lastItem: address = self.payees[lastIndex]
        self.payees[targetIndex] = lastItem
        self.indexOfPayee[lastItem] = targetIndex


# pending payees


@external
def addPendingPayee(_payee: address, _pending: PendingPayee):
    assert msg.sender == self.paymaster # dev: no perms
    self.pendingPayees[_payee] = _pending


@external
def cancelPendingPayee(_payee: address):
    assert msg.sender == self.paymaster # dev: no perms
    self.pendingPayees[_payee] = empty(PendingPayee)


@external
def confirmPendingPayee(_payee: address):
    assert msg.sender == self.paymaster # dev: no perms

    if self._isRegisteredPayee(_payee):
        return

    self.payeeSettings[_payee] = self.pendingPayees[_payee].settings
    self.pendingPayees[_payee] = empty(PendingPayee)
    self._registerPayee(_payee)


# payee management bundle


@view
@external
def getPayeeManagementBundle(_payee: address) -> PayeeManagementBundle:
    owner: address = self.owner
    return PayeeManagementBundle(
        owner = owner,
        wallet = self.wallet,
        isRegisteredPayee = self._isRegisteredPayee(_payee),
        isWhitelisted = self._isWhitelisted(_payee),
        isManager = self._isManager(_payee),
        payeeSettings = self.payeeSettings[_payee],
        globalPayeeSettings = self.globalPayeeSettings,
        timeLock = self.timeLock,
        walletConfig = self,
        inEjectMode = self.inEjectMode,
    )


# check if caller can add pending payee


@view
@external
def canAddPendingPayee(_caller: address) -> bool:
    # owner can always add payees directly (not pending)
    if _caller == self.owner:
        return False
    
    # check if caller is a manager
    if not self._isManager(_caller):
        return False
    
    # get manager settings
    managerSettings: ManagerSettings = self.managerSettings[_caller]
    
    # check if manager is active
    if managerSettings.startBlock > block.number or managerSettings.expiryBlock <= block.number:
        return False
    
    # check if manager has permission
    globalSettings: GlobalManagerSettings = self.globalManagerSettings
    return managerSettings.transferPerms.canAddPendingPayee and globalSettings.transferPerms.canAddPendingPayee


#############
# Whitelist #
#############


@view
@external
def isWhitelisted(_addr: address) -> bool:
    return self._isWhitelisted(_addr)


@view
@internal
def _isWhitelisted(_addr: address) -> bool:
    return self.indexOfWhitelist[_addr] != 0


# add whitelist


@external
def addPendingWhitelistAddr(_addr: address, _pending: PendingWhitelist):
    assert msg.sender == self.paymaster # dev: no perms
    self.pendingWhitelist[_addr] = _pending


# cancel pending whitelist


@external
def cancelPendingWhitelistAddr(_addr: address):
    assert msg.sender == self.paymaster # dev: no perms
    self.pendingWhitelist[_addr] = empty(PendingWhitelist)


# confirm whitelist


@external
def confirmWhitelistAddr(_addr: address):
    assert msg.sender == self.paymaster # dev: no perms
    self.pendingWhitelist[_addr] = empty(PendingWhitelist)
    self._addWhitelistAddr(_addr)


@internal
def _addWhitelistAddr(_addr: address):
    if self._isWhitelisted(_addr):
        return

    wid: uint256 = self.numWhitelisted
    if wid == 0:
        wid = 1 # not using 0 index
    self.whitelistAddr[wid] = _addr
    self.indexOfWhitelist[_addr] = wid
    self.numWhitelisted = wid + 1


# migration


@external
def addWhitelistAddrViaMigrator(_addr: address):
    assert msg.sender == self.migrator # dev: no perms
    self._addWhitelistAddr(_addr)


# remove whitelist


@external
def removeWhitelistAddr(_addr: address):
    assert msg.sender == self.paymaster # dev: no perms

    numWhitelisted: uint256 = self.numWhitelisted
    if numWhitelisted == 0:
        return

    targetIndex: uint256 = self.indexOfWhitelist[_addr]
    if targetIndex == 0:
        return

    # update data
    lastIndex: uint256 = numWhitelisted - 1
    self.numWhitelisted = lastIndex
    self.indexOfWhitelist[_addr] = 0

    # get last item, replace the removed item
    if targetIndex != lastIndex:
        lastItem: address = self.whitelistAddr[lastIndex]
        self.whitelistAddr[targetIndex] = lastItem
        self.indexOfWhitelist[lastItem] = targetIndex


# whitelist config bundle


@view
@external
def getWhitelistConfigBundle(_addr: address, _signer: address) -> WhitelistConfigBundle:
    owner: address = self.owner
    return WhitelistConfigBundle(
        owner = owner,
        wallet = self.wallet,
        isWhitelisted = self._isWhitelisted(_addr),
        pendingWhitelist = self.pendingWhitelist[_addr],
        timeLock = self.timeLock,
        walletConfig = self,
        inEjectMode = self.inEjectMode,
        isManager = self._isManager(_signer),
        isOwner = _signer == owner,
        whitelistPerms = self.managerSettings[_signer].whitelistPerms,
        globalWhitelistPerms = self.globalManagerSettings.whitelistPerms,
    )


######################
# Action Data Bundle #
######################


@view
@external
def getActionDataBundle(_legoId: uint256, _signer: address) -> ActionData:
    return self._getActionDataBundle(_legoId, _signer)


@view
@internal
def _getActionDataBundle(_legoId: uint256, _signer: address) -> ActionData:
    wallet: address = self.wallet
    inEjectMode: bool = self.inEjectMode

    # addys
    hq: address = empty(address)
    missionControl: address = empty(address)
    legoBook: address = empty(address)
    switchboard: address = empty(address)
    hatchery: address = empty(address)
    lootDistributor: address = empty(address)
    appraiser: address = empty(address)
    lastTotalUsdValue: uint256 = 0
    if not inEjectMode:
        hq = UNDY_HQ
        missionControl = staticcall Registry(hq).getAddr(MISSION_CONTROL_ID)
        legoBook = staticcall Registry(hq).getAddr(LEGO_BOOK_ID)
        switchboard = staticcall Registry(hq).getAddr(SWITCHBOARD_ID)
        hatchery = staticcall Registry(hq).getAddr(HATCHERY_ID)
        lootDistributor = staticcall Registry(hq).getAddr(LOOT_DISTRIBUTOR_ID)
        appraiser = staticcall Registry(hq).getAddr(APPRAISER_ID)
        ledger: address = staticcall Registry(hq).getAddr(LEDGER_ID)
        lastTotalUsdValue = staticcall Ledger(ledger).getLastTotalUsdValue(wallet)

    # lego details
    legoAddr: address = empty(address)
    if _legoId != 0 and legoBook != empty(address):
        legoAddr = staticcall Registry(legoBook).getAddr(_legoId)

    return ActionData(
        missionControl = missionControl,
        legoBook = legoBook,
        switchboard = switchboard,
        hatchery = hatchery,
        lootDistributor = lootDistributor,
        appraiser = appraiser,
        wallet = wallet,
        walletConfig = self,
        walletOwner = self.owner,
        inEjectMode = inEjectMode,
        isFrozen = self.isFrozen,
        lastTotalUsdValue = lastTotalUsdValue,
        signer = _signer,
        isManager = False,
        legoId = _legoId,
        legoAddr = legoAddr,
        eth = ETH,
        weth = WETH,
    )


################
# Wallet Tools #
################


# update asset data


@external
def updateAssetData(_legoId: uint256, _asset: address, _shouldCheckYield: bool) -> uint256:
    ad: ActionData = self._getActionDataBundle(_legoId, msg.sender)
    assert self._isSwitchboardAddr(msg.sender, ad.inEjectMode) # dev: no perms
    newTotalUsdValue: uint256 = extcall UserWallet(ad.wallet).updateAssetData(_legoId, _asset, _shouldCheckYield, ad.lastTotalUsdValue, ad)
    extcall LootDistributor(ad.lootDistributor).updateDepositPointsWithData(ad.wallet, newTotalUsdValue, True)
    return newTotalUsdValue


@external
def updateAllAssetData(_shouldCheckYield: bool) -> uint256:
    ad: ActionData = self._getActionDataBundle(0, msg.sender)
    assert self._isSwitchboardAddr(msg.sender, ad.inEjectMode) # dev: no perms

    numAssets: uint256 = staticcall UserWallet(ad.wallet).numAssets()
    if numAssets == 0:
        return ad.lastTotalUsdValue

    newTotalUsdValue: uint256 = ad.lastTotalUsdValue
    for i: uint256 in range(1, numAssets, bound=max_value(uint256)):           
        asset: address = staticcall UserWallet(ad.wallet).assets(i)
        if asset != empty(address):
            newTotalUsdValue = extcall UserWallet(ad.wallet).updateAssetData(0, asset, _shouldCheckYield, newTotalUsdValue, ad)

    extcall LootDistributor(ad.lootDistributor).updateDepositPointsWithData(ad.wallet, newTotalUsdValue, True)
    return newTotalUsdValue


# remove trial funds


@external
def removeTrialFunds() -> uint256:
    ad: ActionData = self._getActionDataBundle(0, msg.sender)
    assert ad.hatchery == msg.sender and ad.hatchery != empty(address) # dev: no perms

    # trial funds info
    trialFundsAmount: uint256 = self.trialFundsAmount
    trialFundsAsset: address = self.trialFundsAsset
    assert trialFundsAsset != empty(address) and trialFundsAmount != 0 # dev: no trial funds

    # transfer assets
    amount: uint256 = 0
    na: uint256 = 0
    amount, na = extcall UserWallet(ad.wallet).transferFundsTrusted(ad.hatchery, trialFundsAsset, trialFundsAmount, ad)

    # update trial funds info
    remainingAmount: uint256 = trialFundsAmount - amount
    self.trialFundsAmount = remainingAmount
    if remainingAmount == 0:
        self.trialFundsAsset = empty(address)

    return amount


# prepare payment


@external
def preparePayment(
    _targetAsset: address,
    _legoId: uint256,
    _vaultToken: address,
    _vaultAmount: uint256 = max_value(uint256),
) -> (uint256, uint256):
    ad: ActionData = self._getActionDataBundle(_legoId, msg.sender)
    if msg.sender != ad.hatchery:
        assert self._isSwitchboardAddr(msg.sender, ad.inEjectMode) # dev: no perms

    # withdraw from yield position
    na: uint256 = 0
    underlyingAsset: address = empty(address)
    underlyingAmount: uint256 = 0
    txUsdValue: uint256 = 0
    na, underlyingAsset, underlyingAmount, txUsdValue = extcall UserWallet(ad.wallet).preparePayment(_legoId, _vaultToken, _vaultAmount, ad)
    assert underlyingAsset == _targetAsset # dev: invalid target asset

    return underlyingAmount, txUsdValue


# recover nft


@external
def recoverNft(_collection: address, _nftTokenId: uint256, _recipient: address):
    if not self._isSwitchboardAddr(msg.sender, self.inEjectMode):
        assert msg.sender == self.owner # dev: no perms
    assert _recipient != empty(address) # dev: invalid recipient
    wallet: address = self.wallet
    assert staticcall IERC721(_collection).ownerOf(_nftTokenId) == wallet # dev: not owner
    extcall wi(wallet).recoverNft(_collection, _nftTokenId, _recipient)
    log NftRecovered(collection = _collection, nftTokenId = _nftTokenId, recipient = _recipient)


# freeze wallet


@external
def setFrozen(_isFrozen: bool):
    if not self._isSwitchboardAddr(msg.sender, self.inEjectMode):
        assert msg.sender == self.owner # dev: no perms

    self.isFrozen = _isFrozen
    log FrozenSet(isFrozen=_isFrozen, caller=msg.sender)


# ejection mode


@external
def setEjectionMode(_shouldEject: bool):
    # NOTE: this needs to be triggered from Switchboard, as it has other side effects / reactions
    assert self._isSwitchboardAddr(msg.sender, self.inEjectMode) # dev: no perms
    assert self.trialFundsAmount == 0 # dev: has trial funds

    assert _shouldEject != self.inEjectMode # dev: nothing to change
    self.inEjectMode = _shouldEject
    log EjectionModeSet(inEjectMode = _shouldEject)


# is signer switchboard


@view
@internal
def _isSwitchboardAddr(_signer: address, _inEjectMode: bool) -> bool:
    if _inEjectMode:
        return False
    switchboard: address = staticcall Registry(UNDY_HQ).getAddr(SWITCHBOARD_ID)
    return staticcall Switchboard(switchboard).isSwitchboardAddr(_signer)


####################
# Wallet Migration #
####################


@external
def setDidMigrateFunds():
    assert msg.sender == self.migrator # dev: no perms
    self.didMigrateFunds = True


@external
def setDidMigrateSettings():
    assert msg.sender == self.migrator # dev: no perms
    self.didMigrateSettings = True


@external
def transferFundsDuringMigration(
    _recipient: address,
    _asset: address,
    _amount: uint256,
    _ad: ActionData,
) -> (uint256, uint256):
    assert msg.sender == self.migrator # dev: no perms
    return extcall UserWallet(self.wallet).transferFundsTrusted(_recipient, _asset, _amount, _ad)


@view
@external
def getMigrationConfigBundle() -> MigrationConfigBundle:
    startingAgent: address = self.startingAgent
    return MigrationConfigBundle(
        owner = self.owner,
        trialFundsAmount = self.trialFundsAmount,
        isFrozen = self.isFrozen,
        numPayees = self.numPayees,
        numWhitelisted = self.numWhitelisted,
        numManagers = self.numManagers,
        startingAgent = startingAgent,
        startingAgentIndex = self.indexOfManager[startingAgent],
        hasPendingOwnerChange = self._hasPendingOwnerChange(),
        groupId = self.groupId,
        didMigrateSettings = self.didMigrateSettings,
        didMigrateFunds = self.didMigrateFunds,
    )
