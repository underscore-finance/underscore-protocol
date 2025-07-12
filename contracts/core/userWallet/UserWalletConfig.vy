# @version 0.4.3
# pragma optimize codesize

from interfaces import WalletStructs as ws
from interfaces import WalletConfigStructs as wcs
from ethereum.ercs import IERC721

interface UserWallet:
    def withdrawFromYield(_legoId: uint256, _vaultToken: address, _amount: uint256 = max_value(uint256), _extraData: bytes32 = empty(bytes32), _isTrustedTx: bool = False) -> (uint256, address, uint256, uint256): nonpayable
    def transferFunds(_recipient: address, _asset: address = empty(address), _amount: uint256 = max_value(uint256), _isTrustedTx: bool = False) -> (uint256, uint256): nonpayable
    def updateAssetData(_legoId: uint256, _asset: address, _shouldCheckYield: bool, _totalUsdValue: uint256, _ad: ws.ActionData = empty(ws.ActionData)) -> uint256: nonpayable
    def recoverNft(_collection: address, _nftTokenId: uint256, _recipient: address): nonpayable
    def assets(i: uint256) -> address: view
    def walletConfig() -> address: view
    def numAssets() -> uint256: view

interface BossValidator:
    def canSignerPerformActionWithConfig(_isOwner: bool, _isManager: bool, _data: wcs.ManagerData, _config: wcs.ManagerSettings, _globalConfig: wcs.GlobalManagerSettings, _userWalletConfig: address, _action: ws.ActionType, _assets: DynArray[address, MAX_ASSETS] = [], _legoIds: DynArray[uint256, MAX_LEGOS] = [], _transferRecipient: address = empty(address)) -> bool: view
    def checkManagerUsdLimitsAndUpdateData(_txUsdValue: uint256, _specificLimits: wcs.ManagerLimits, _globalLimits: wcs.ManagerLimits, _managerPeriod: uint256, _data: wcs.ManagerData) -> wcs.ManagerData: view
    def createDefaultGlobalManagerSettings(_managerPeriod: uint256, _minTimeLock: uint256, _defaultActivationLength: uint256) -> wcs.GlobalManagerSettings: view
    def createStarterAgentSettings(_startingAgentActivationLength: uint256) -> wcs.ManagerSettings: view

interface Paymaster:
    def isValidPayeeWithConfig(_isWhitelisted: bool, _isOwner: bool, _isPayee: bool, _asset: address, _amount: uint256, _txUsdValue: uint256, _config: wcs.PayeeSettings, _globalConfig: wcs.GlobalPayeeSettings, _data: wcs.PayeeData) -> (bool, wcs.PayeeData): view
    def createDefaultGlobalPayeeSettings(_defaultPeriodLength: uint256, _startDelay: uint256, _activationLength: uint256) -> wcs.GlobalPayeeSettings: view

interface Migrator:
    def canMigrateFundsToNewWallet(_newWallet: address, _thisWallet: address) -> bool: view

interface LootDistributor:
    def updateDepositPointsWithNewValue(_user: address, _newUsdValue: uint256): nonpayable

interface Ledger:
    def getLastTotalUsdValue(_user: address) -> uint256: view

interface Switchboard:
    def isSwitchboardAddr(_addr: address) -> bool: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

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
pendingOwner: public(wcs.PendingOwnerChange)

# helper contracts
bossValidator: public(address)
paymaster: public(address)
migrator: public(address)

# trial funds info
trialFundsAsset: public(address)
trialFundsAmount: public(uint256)

# managers
managerSettings: public(HashMap[address, wcs.ManagerSettings])
managerPeriodData: public(HashMap[address, wcs.ManagerData])
managers: public(HashMap[uint256, address]) # index -> manager
indexOfManager: public(HashMap[address, uint256]) # manager -> index
numManagers: public(uint256) # num managers

# payees
payeeSettings: public(HashMap[address, wcs.PayeeSettings])
payeePeriodData: public(HashMap[address, wcs.PayeeData])
payees: public(HashMap[uint256, address]) # index -> payee
indexOfPayee: public(HashMap[address, uint256]) # payee -> index
numPayees: public(uint256) # num payees
pendingPayees: public(HashMap[address, wcs.PendingPayee])

# whitelist
whitelistAddr: public(HashMap[uint256, address]) # index -> whitelist
indexOfWhitelist: public(HashMap[address, uint256]) # whitelist -> index
numWhitelisted: public(uint256) # num whitelisted
pendingWhitelist: public(HashMap[address, wcs.PendingWhitelist]) # addr -> pending whitelist

# global config
globalManagerSettings: public(wcs.GlobalManagerSettings)
globalPayeeSettings: public(wcs.GlobalPayeeSettings)

# config
timeLock: public(uint256)
isFrozen: public(bool)
inEjectMode: public(bool)

startingAgent: public(address)
didSetWallet: public(bool)
didMigrateFunds: public(bool)
didMigrateSettings: public(bool)

API_VERSION: constant(String[28]) = "0.1.0"
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
    _action: ws.ActionType,
    _assets: DynArray[address, MAX_ASSETS] = [],
    _legoIds: DynArray[uint256, MAX_LEGOS] = [],
    _transferRecipient: address = empty(address),
) -> ws.ActionData:
    legoId: uint256 = 0
    if len(_legoIds) != 0:
        legoId = _legoIds[0]

    # main data for this transaction
    ad: ws.ActionData = self._getActionDataBundle(legoId, _signer)

    # main validation
    c: wcs.ManagerConfigBundle = self._getManagerConfigs(_signer, ad.walletOwner)
    assert staticcall BossValidator(self.bossValidator).canSignerPerformActionWithConfig(c.isOwner, c.isManager, c.data, c.config, c.globalConfig, ad.walletConfig, _action, _assets, _legoIds, _transferRecipient) # dev: no permission

    # signer is not owner
    if not c.isOwner:
        ad.isManager = True

    return ad


# post action (usd value limits)


@external
def checkManagerUsdLimitsAndUpdateData(_manager: address, _txUsdValue: uint256) -> bool:
    assert msg.sender == self.wallet # dev: no perms

    config: wcs.ManagerSettings = self.managerSettings[_manager]
    globalConfig: wcs.GlobalManagerSettings = self.globalManagerSettings
    data: wcs.ManagerData = staticcall BossValidator(self.bossValidator).checkManagerUsdLimitsAndUpdateData(_txUsdValue, config.limits, globalConfig.limits, globalConfig.managerPeriod, self.managerPeriodData[_manager])
    self.managerPeriodData[_manager] = data
    return True


# manager config bundle


@view
@external
def getManagerConfigs(_signer: address) -> wcs.ManagerConfigBundle:
    return self._getManagerConfigs(_signer, self.owner)


@view
@internal
def _getManagerConfigs(_signer: address, _walletOwner: address) -> wcs.ManagerConfigBundle:
    return wcs.ManagerConfigBundle(
        isOwner = _signer == _walletOwner,
        isManager = self.indexOfManager[_signer] != 0,
        config = self.managerSettings[_signer],
        globalConfig = self.globalManagerSettings,
        data = self.managerPeriodData[_signer],
    )


# manager settings bundle


@view
@external
def getManagerSettingsBundle(_manager: address) -> wcs.ManagerSettingsBundle:
    return wcs.ManagerSettingsBundle(
        owner = self.owner,
        isManager = self._isManager(_manager),
        bossValidator = self.bossValidator,
        timeLock = self.timeLock,
        inEjectMode = self.inEjectMode,
        walletConfig = self,
        legoBook = staticcall Registry(UNDY_HQ).getAddr(LEGO_BOOK_ID),
    )


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

    c: wcs.RecipientConfigBundle = self._getRecipientConfigs(_recipient)

    # check if payee is valid
    canPayRecipient: bool = False
    data: wcs.PayeeData = empty(wcs.PayeeData)
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
def getRecipientConfigs(_recipient: address) -> wcs.RecipientConfigBundle:
    return self._getRecipientConfigs(_recipient)


@view
@internal
def _getRecipientConfigs(_recipient: address) -> wcs.RecipientConfigBundle:
    isWhitelisted: bool = self._isWhitelisted(_recipient)

    isOwner: bool = False
    isPayee: bool = False
    config: wcs.PayeeSettings = empty(wcs.PayeeSettings)
    globalConfig: wcs.GlobalPayeeSettings = empty(wcs.GlobalPayeeSettings)
    data: wcs.PayeeData = empty(wcs.PayeeData)
    if not isWhitelisted:
        isOwner = _recipient == self.owner
        isPayee = self._isRegisteredPayee(_recipient)
        config = self.payeeSettings[_recipient]
        globalConfig = self.globalPayeeSettings
        data = self.payeePeriodData[_recipient]

    return wcs.RecipientConfigBundle(
        isWhitelisted = isWhitelisted,
        isOwner = isOwner,
        isPayee = isPayee,
        config = config,
        globalConfig = globalConfig,
        data = data,
    )


# payee management bundle


@view
@external
def getPayeeManagementBundle(_payee: address) -> wcs.PayeeManagementBundle:
    owner: address = self.owner
    return wcs.PayeeManagementBundle(
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
    self.pendingOwner = wcs.PendingOwnerChange(
        newOwner = _newOwner,
        initiatedBlock = block.number,
        confirmBlock = confirmBlock,
    )
    log OwnershipChangeInitiated(prevOwner = currentOwner, newOwner = _newOwner, confirmBlock = confirmBlock)


# confirm ownership change


@external
def confirmOwnershipChange():
    data: wcs.PendingOwnerChange = self.pendingOwner
    assert data.newOwner != empty(address) # dev: no pending owner
    assert data.confirmBlock != 0 and block.number >= data.confirmBlock # dev: time delay not reached
    assert msg.sender == data.newOwner # dev: only new owner can confirm

    prevOwner: address = self.owner
    self.owner = data.newOwner
    self.pendingOwner = empty(wcs.PendingOwnerChange)
    log OwnershipChangeConfirmed(prevOwner = prevOwner, newOwner = data.newOwner, initiatedBlock = data.initiatedBlock, confirmBlock = data.confirmBlock)


# cancel ownership change


@external
def cancelOwnershipChange():
    if not self._isSwitchboardAddr(msg.sender, self.inEjectMode):
        assert msg.sender == self.owner # dev: no perms

    data: wcs.PendingOwnerChange = self.pendingOwner
    assert data.confirmBlock != 0 # dev: no pending change
    self.pendingOwner = empty(wcs.PendingOwnerChange)
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
def setGlobalManagerSettings(_config: wcs.GlobalManagerSettings):
    assert msg.sender in [self.bossValidator, self.migrator] # dev: no perms
    self.globalManagerSettings = _config


# add manager


@external
def addManager(_manager: address, _config: wcs.ManagerSettings):
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
def updateManager(_manager: address, _config: wcs.ManagerSettings):
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

    self.managerSettings[_manager] = empty(wcs.ManagerSettings)
    self.managerPeriodData[_manager] = empty(wcs.ManagerData)

    # update data
    lastIndex: uint256 = numManagers - 1
    self.numManagers = lastIndex
    self.indexOfManager[_manager] = 0

    # get last item, replace the removed item
    if targetIndex != lastIndex:
        lastItem: address = self.managers[lastIndex]
        self.managers[targetIndex] = lastItem
        self.indexOfManager[lastItem] = targetIndex


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
def setGlobalPayeeSettings(_config: wcs.GlobalPayeeSettings):
    assert msg.sender in [self.paymaster, self.migrator] # dev: no perms
    self.globalPayeeSettings = _config


# add payee


@external
def addPayee(_payee: address, _config: wcs.PayeeSettings):
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
def updatePayee(_payee: address, _config: wcs.PayeeSettings):
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

    self.payeeSettings[_payee] = empty(wcs.PayeeSettings)
    self.payeePeriodData[_payee] = empty(wcs.PayeeData)

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
def addPendingPayee(_payee: address, _pending: wcs.PendingPayee):
    assert msg.sender == self.paymaster # dev: no perms
    self.pendingPayees[_payee] = _pending


@external
def cancelPendingPayee(_payee: address):
    assert msg.sender == self.paymaster # dev: no perms
    self.pendingPayees[_payee] = empty(wcs.PendingPayee)


@external
def confirmPendingPayee(_payee: address):
    assert msg.sender == self.paymaster # dev: no perms

    if self._isRegisteredPayee(_payee):
        return

    self.payeeSettings[_payee] = self.pendingPayees[_payee].settings
    self.pendingPayees[_payee] = empty(wcs.PendingPayee)
    self._registerPayee(_payee)


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
    managerSettings: wcs.ManagerSettings = self.managerSettings[_caller]
    
    # check if manager is active
    if managerSettings.startBlock > block.number or managerSettings.expiryBlock <= block.number:
        return False
    
    # check if manager has permission
    globalSettings: wcs.GlobalManagerSettings = self.globalManagerSettings
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
def addPendingWhitelistAddr(_addr: address, _pending: wcs.PendingWhitelist):
    assert msg.sender == self.paymaster # dev: no perms
    self.pendingWhitelist[_addr] = _pending


# cancel pending whitelist


@external
def cancelPendingWhitelistAddr(_addr: address):
    assert msg.sender == self.paymaster # dev: no perms
    self.pendingWhitelist[_addr] = empty(wcs.PendingWhitelist)


# confirm whitelist


@external
def confirmWhitelistAddr(_addr: address):
    assert msg.sender == self.paymaster # dev: no perms
    self.pendingWhitelist[_addr] = empty(wcs.PendingWhitelist)
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
def getWhitelistConfigBundle(_addr: address, _signer: address) -> wcs.WhitelistConfigBundle:
    owner: address = self.owner
    return wcs.WhitelistConfigBundle(
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
def getActionDataBundle(_legoId: uint256, _signer: address) -> ws.ActionData:
    return self._getActionDataBundle(_legoId, _signer)


@view
@internal
def _getActionDataBundle(_legoId: uint256, _signer: address) -> ws.ActionData:
    wallet: address = self.wallet
    inEjectMode: bool = self.inEjectMode

    # addys
    hq: address = empty(address)
    ledger: address = empty(address)
    missionControl: address = empty(address)
    legoBook: address = empty(address)
    hatchery: address = empty(address)
    lootDistributor: address = empty(address)
    appraiser: address = empty(address)
    lastTotalUsdValue: uint256 = 0
    if not inEjectMode:
        hq = UNDY_HQ
        ledger = staticcall Registry(hq).getAddr(LEDGER_ID)
        missionControl = staticcall Registry(hq).getAddr(MISSION_CONTROL_ID)
        legoBook = staticcall Registry(hq).getAddr(LEGO_BOOK_ID)
        hatchery = staticcall Registry(hq).getAddr(HATCHERY_ID)
        lootDistributor = staticcall Registry(hq).getAddr(LOOT_DISTRIBUTOR_ID)
        appraiser = staticcall Registry(hq).getAddr(APPRAISER_ID)
        lastTotalUsdValue = staticcall Ledger(ledger).getLastTotalUsdValue(wallet)

    # lego details
    legoAddr: address = empty(address)
    if _legoId != 0 and legoBook != empty(address):
        legoAddr = staticcall Registry(legoBook).getAddr(_legoId)

    return ws.ActionData(
        ledger = ledger,
        missionControl = missionControl,
        legoBook = legoBook,
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
    ad: ws.ActionData = self._getActionDataBundle(_legoId, msg.sender)
    assert self._isSwitchboardAddr(msg.sender, ad.inEjectMode) # dev: no perms
    newTotalUsdValue: uint256 = extcall UserWallet(ad.wallet).updateAssetData(_legoId, _asset, _shouldCheckYield, ad.lastTotalUsdValue, ad)
    extcall LootDistributor(ad.lootDistributor).updateDepositPointsWithNewValue(ad.wallet, newTotalUsdValue)
    return newTotalUsdValue


@external
def updateAllAssetData(_shouldCheckYield: bool) -> uint256:
    ad: ws.ActionData = self._getActionDataBundle(0, msg.sender)
    assert self._isSwitchboardAddr(msg.sender, ad.inEjectMode) # dev: no perms

    numAssets: uint256 = staticcall UserWallet(ad.wallet).numAssets()
    if numAssets == 0:
        return ad.lastTotalUsdValue

    newTotalUsdValue: uint256 = ad.lastTotalUsdValue
    for i: uint256 in range(1, numAssets, bound=max_value(uint256)):           
        asset: address = staticcall UserWallet(ad.wallet).assets(i)
        if asset != empty(address):
            newTotalUsdValue = extcall UserWallet(ad.wallet).updateAssetData(0, asset, _shouldCheckYield, newTotalUsdValue, ad)

    extcall LootDistributor(ad.lootDistributor).updateDepositPointsWithNewValue(ad.wallet, newTotalUsdValue)
    return newTotalUsdValue


# remove trial funds


@view
@external
def getTrialFundsInfo() -> (address, uint256):
    return self.trialFundsAsset, self.trialFundsAmount


@external
def removeTrialFunds() -> uint256:
    ad: ws.ActionData = self._getActionDataBundle(0, msg.sender)
    assert ad.hatchery == msg.sender and ad.hatchery != empty(address) # dev: no perms

    # trial funds info
    trialFundsAmount: uint256 = self.trialFundsAmount
    trialFundsAsset: address = self.trialFundsAsset
    assert trialFundsAsset != empty(address) and trialFundsAmount != 0 # dev: no trial funds

    # transfer assets
    amount: uint256 = 0
    na: uint256 = 0
    amount, na = extcall UserWallet(ad.wallet).transferFunds(ad.hatchery, trialFundsAsset, trialFundsAmount, True)

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
    ad: ws.ActionData = self._getActionDataBundle(_legoId, msg.sender)
    if msg.sender != ad.hatchery:
        assert self._isSwitchboardAddr(msg.sender, ad.inEjectMode) # dev: no perms

    # withdraw from yield position
    na: uint256 = 0
    underlyingAsset: address = empty(address)
    underlyingAmount: uint256 = 0
    txUsdValue: uint256 = 0
    na, underlyingAsset, underlyingAmount, txUsdValue = extcall UserWallet(ad.wallet).withdrawFromYield(_legoId, _vaultToken, _vaultAmount, empty(bytes32), True)
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
    extcall UserWallet(wallet).recoverNft(_collection, _nftTokenId, _recipient)
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
) -> (uint256, uint256):
    assert msg.sender == self.migrator # dev: no perms
    return extcall UserWallet(self.wallet).transferFunds(_recipient, _asset, _amount, True)


@view
@external
def getMigrationConfigBundle() -> wcs.MigrationConfigBundle:
    startingAgent: address = self.startingAgent
    return wcs.MigrationConfigBundle(
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
