# @version 0.4.3
# pragma optimize codesize

from interfaces import Wallet as wi

interface BossValidator:
    def canSignerPerformActionWithConfig(_isOwner: bool, _isManager: bool, _data: ManagerData, _config: ManagerSettings, _globalConfig: GlobalManagerSettings, _userWalletConfig: address, _action: wi.ActionType, _assets: DynArray[address, MAX_ASSETS] = [], _legoIds: DynArray[uint256, MAX_LEGOS] = [], _transferRecipient: address = empty(address)) -> bool: view
    def checkManagerUsdLimitsAndUpdateData(_txUsdValue: uint256, _specificLimits: ManagerLimits, _globalLimits: ManagerLimits, _managerPeriod: uint256, _data: ManagerData) -> ManagerData: view
    def createDefaultGlobalManagerSettings(_managerPeriod: uint256, _minTimeLock: uint256, _defaultActivationLength: uint256) -> GlobalManagerSettings: view
    def createStarterAgentSettings(_startingAgentActivationLength: uint256) -> ManagerSettings: view

interface Paymaster:
    def isValidPayeeWithConfig(_isWhitelisted: bool, _isOwner: bool, _isPayee: bool, _asset: address, _amount: uint256, _txUsdValue: uint256, _config: PayeeSettings, _globalConfig: GlobalPayeeSettings, _data: PayeeData) -> (bool, PayeeData): view

interface Backpack:
    def getBackpackData(_user: address) -> BackpackData: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

struct ActionData:
    missionControl: address
    legoBook: address
    backpack: address
    appraiser: address
    bossValidator: address
    paymaster: address
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
    timeLockOnModify: uint256
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

struct PendingWhitelist:
    initiatedBlock: uint256
    confirmBlock: uint256

struct PendingOwnerChange:
    newOwner: address
    initiatedBlock: uint256
    confirmBlock: uint256

struct BackpackData:
    missionControl: address
    legoBook: address
    appraiser: address
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

# core
wallet: public(address)
groupId: public(uint256)
owner: public(address)
pendingOwner: public(PendingOwnerChange)

# helper contracts
bossValidator: public(address)
paymaster: public(address)

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
ejectModeFeeDetails: public(EjectModeFeeDetails)

startingAgent: public(address)
didSetWallet: public(bool)

API_VERSION: constant(String[28]) = "0.1.0"

MAX_CONFIG_ASSETS: constant(uint256) = 40
MAX_CONFIG_LEGOS: constant(uint256) = 25
MAX_ALLOWED_PAYEES: constant(uint256) = 40
MAX_ASSETS: constant(uint256) = 10
MAX_LEGOS: constant(uint256) = 10

# registry ids
HATCHERY_ID: constant(uint256) = 6
BACKPACK_ID: constant(uint256) = 7
LEGO_BOOK_ID: constant(uint256) = 4

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
    # initial agent
    _startingAgent: address,
    _startingAgentActivationLength: uint256,
    # global manager settings
    _managerPeriod: uint256,
    _defaultActivationLength: uint256,
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
    self.globalManagerSettings = staticcall BossValidator(_bossValidator).createDefaultGlobalManagerSettings(_managerPeriod, _minTimeLock, _defaultActivationLength)

    # initial agent
    if _startingAgent != empty(address):
        self.managerSettings[_startingAgent] = staticcall BossValidator(_bossValidator).createStarterAgentSettings(_startingAgentActivationLength)
        self.startingAgent = _startingAgent
        self._registerManager(_startingAgent)

    # TODO: global payee settings
    self.globalPayeeSettings = GlobalPayeeSettings(
        defaultPeriodLength = 43_200,
        timeLockOnModify = 43_200,
        activationLength = 43_200 * 365,
        maxNumTxsPerPeriod = 0,
        txCooldownBlocks = 0,
        failOnZeroPrice = False,
        usdLimits = PayeeLimits(
            perTxCap = max_value(uint256),  # No limit
            perPeriodCap = max_value(uint256),  # No limit
            lifetimeCap = max_value(uint256),  # No limit
        ),
        canPayOwner = True,
    )


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
    assert staticcall BossValidator(ad.bossValidator).canSignerPerformActionWithConfig(c.isOwner, c.isManager, c.data, c.config, c.globalConfig, ad.walletConfig, _action, _assets, _legoIds, _transferRecipient) # dev: no permission

    # signer is not owner
    if not c.isOwner:
        ad.isManager = True

    return ad


# post action (usd value limits)


@external
def checkManagerUsdLimitsAndUpdateData(_manager: address, _txUsdValue: uint256, _bossValidator: address) -> bool:
    assert msg.sender == self.wallet # dev: no perms

    config: ManagerSettings = self.managerSettings[_manager]
    globalConfig: GlobalManagerSettings = self.globalManagerSettings
    data: ManagerData = staticcall BossValidator(_bossValidator).checkManagerUsdLimitsAndUpdateData(_txUsdValue, config.limits, globalConfig.limits, globalConfig.managerPeriod, self.managerPeriodData[_manager])
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
    _paymaster: address,
) -> bool:
    assert msg.sender == self.wallet # dev: no perms

    c: RecipientConfigBundle = self._getRecipientConfigs(_recipient)

    # check if payee is valid
    canPayRecipient: bool = False
    data: PayeeData = empty(PayeeData)
    canPayRecipient, data = staticcall Paymaster(_paymaster).isValidPayeeWithConfig(c.isWhitelisted, c.isOwner, c.isPayee, _asset, _amount, _txUsdValue, c.config, c.globalConfig, c.data)

    # !!!!
    assert canPayRecipient # dev: invalid payee

    # only save if data was updated  
    if data.lastTxBlock != 0:
        self.payeePeriodData[_recipient] = data
    
    return True


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
    if not self._isSignerBackpack(msg.sender, self.inEjectMode):
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
    if not self._isSignerBackpack(msg.sender, self.inEjectMode):
        assert msg.sender == self.owner # dev: no perms

    self.isFrozen = _isFrozen
    log FrozenSet(isFrozen=_isFrozen, caller=msg.sender)


# ejection mode


@external
def setEjectionMode(_shouldEject: bool, _feeDetails: EjectModeFeeDetails):
    # NOTE: this needs to be triggered from Backpack, as it has other side effects / reactions
    assert msg.sender == staticcall Registry(UNDY_HQ).getAddr(BACKPACK_ID) # dev: no perms

    assert _shouldEject != self.inEjectMode # dev: nothing to change
    self.inEjectMode = _shouldEject
    self.ejectModeFeeDetails = _feeDetails

    log EjectionModeSet(
        inEjectMode = _shouldEject,
        feeRecipient = _feeDetails.feeRecipient,
        swapFee = _feeDetails.swapFee,
        rewardsFee = _feeDetails.rewardsFee,
        caller = msg.sender,
    )


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
    assert msg.sender == self.bossValidator # dev: no perms
    self.globalManagerSettings = _config


# add manager


@external
def addManager(_manager: address, _config: ManagerSettings):
    assert msg.sender == self.bossValidator # dev: no perms
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
    assert msg.sender == self.paymaster # dev: no perms
    self.globalPayeeSettings = _config


# add payee


@external
def addPayee(_payee: address, _config: PayeeSettings):
    assert msg.sender == self.paymaster # dev: no perms
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


#############
# Whitelist #
#############


# is whitelisted


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

    if self._isWhitelisted(_addr):
        return

    self.pendingWhitelist[_addr] = empty(PendingWhitelist)

    wid: uint256 = self.numWhitelisted
    if wid == 0:
        wid = 1 # not using 0 index
    self.whitelistAddr[wid] = _addr
    self.indexOfWhitelist[_addr] = wid
    self.numWhitelisted = wid + 1


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


#############
# Utilities #
#############


@view
@internal
def _isSignerBackpack(_signer: address, _inEjectMode: bool) -> bool:
    if _inEjectMode:
        return False
    return _signer == staticcall Registry(UNDY_HQ).getAddr(BACKPACK_ID)


# action data bundle


@view
@external
def getActionDataBundle(_legoId: uint256, _signer: address) -> ActionData:
    return self._getActionDataBundle(_legoId, _signer)


@view
@internal
def _getActionDataBundle(_legoId: uint256, _signer: address) -> ActionData:
    wallet: address = self.wallet
    inEjectMode: bool = self.inEjectMode

    # backpack details
    backpack: address = empty(address)
    backpackData: BackpackData = empty(BackpackData)
    if not inEjectMode:
        hq: address = UNDY_HQ
        backpack = staticcall Registry(hq).getAddr(BACKPACK_ID)
        backpackData = staticcall Backpack(backpack).getBackpackData(wallet)

    # lego details
    legoAddr: address = empty(address)
    if _legoId != 0 and backpackData.legoBook != empty(address):
        legoAddr = staticcall Registry(backpackData.legoBook).getAddr(_legoId)

    return ActionData(
        missionControl = backpackData.missionControl,
        legoBook = backpackData.legoBook,
        backpack = backpack,
        appraiser = backpackData.appraiser,
        bossValidator = self.bossValidator,
        paymaster = self.paymaster,
        feeRecipient = backpackData.feeRecipient,
        wallet = wallet,
        walletConfig = self,
        walletOwner = self.owner,
        inEjectMode = inEjectMode,
        isFrozen = self.isFrozen,
        lastTotalUsdValue = backpackData.lastTotalUsdValue,
        signer = _signer,
        isManager = False,
        legoId = _legoId,
        legoAddr = legoAddr,
        eth = ETH,
        weth = WETH,
    )


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


# # remove trial funds


# @external
# def removeTrialFunds() -> uint256:
#     ad: ActionData = self._getActionDataBundle(0, msg.sender)
#     assert ad.signer == ad.backpack # dev: no perms

#     # trial funds info
#     trialFundsAmount: uint256 = self.trialFundsAmount
#     trialFundsAsset: address = self.trialFundsAsset
#     assert trialFundsAsset != empty(address) and trialFundsAmount != 0 # dev: no trial funds

#     # recipient
#     hatchery: address = staticcall Registry(UNDY_HQ).getAddr(HATCHERY_ID)
#     assert hatchery != empty(address) # dev: invalid recipient

#     # transfer assets
#     amount: uint256 = 0
#     na: uint256 = 0
#     amount, na = extcall UserWallet(ad.wallet).transferFundsTrusted(hatchery, trialFundsAsset, trialFundsAmount, ad)

#     # update trial funds info
#     remainingAmount: uint256 = trialFundsAmount - amount
#     self.trialFundsAmount = remainingAmount
#     if remainingAmount == 0:
#         self.trialFundsAsset = empty(address)

#     return amount


# # prepare payment


# @external
# def preparePayment(
#     _targetAsset: address,
#     _legoId: uint256,
#     _vaultToken: address,
#     _vaultAmount: uint256 = max_value(uint256),
# ) -> (uint256, uint256):
#     ad: ActionData = self._getActionDataBundle(_legoId, msg.sender)
#     assert ad.signer == ad.backpack # dev: no perms

#     # withdraw from yield position
#     na: uint256 = 0
#     underlyingAsset: address = empty(address)
#     underlyingAmount: uint256 = 0
#     txUsdValue: uint256 = 0
#     na, underlyingAsset, underlyingAmount, txUsdValue = extcall UserWallet(ad.wallet).preparePayment(_legoId, _vaultToken, _vaultAmount, ad)
#     assert underlyingAsset == _targetAsset # dev: invalid target asset
   
#     return underlyingAmount, txUsdValue


# # recover nft


# @external
# def recoverNft(_collection: address, _nftTokenId: uint256, _recipient: address) -> bool:
#     assert msg.sender == staticcall Registry(UNDY_HQ).getAddr(BACKPACK_ID) # dev: no perms
#     assert _recipient != empty(address) # dev: invalid recipient
#     wallet: address = self.wallet
#     assert staticcall IERC721(_collection).ownerOf(_nftTokenId) == wallet # dev: not owner
#     return extcall UserWallet(wallet).recoverNft(_collection, _nftTokenId, _recipient)


# #############
# # Migration #
# #############


# # migrate funds


# @external
# def migrateFunds(_newWallet: address) -> uint256:
#     owner: address = self.owner
#     assert msg.sender == owner # dev: no perms

#     wallet: address = self.wallet
#     assert self._canMigrateToNewWallet(_newWallet, owner, wallet) # dev: cannot migrate to new wallet

#     numAssets: uint256 = staticcall UserWallet(wallet).numAssets()
#     if numAssets == 0:
#         return 0

#     # transfer tokens
#     numMigrated: uint256 = 0
#     for i: uint256 in range(1, numAssets, bound=max_value(uint256)):           
#         asset: address = staticcall UserWallet(wallet).assets(i)
#         if asset == empty(address):
#             continue

#         balance: uint256 = staticcall IERC20(asset).balanceOf(wallet)
#         if balance != 0:
#             extcall wi(_newWallet).transferFunds(_newWallet, asset)
#         numMigrated += 1

#     return numMigrated


# @view
# @internal
# def _canMigrateToNewWallet(_newWallet: address, _owner: address, _thisWallet: address) -> bool:
#     ledger: address = staticcall Registry(UNDY_HQ).getAddr(LEDGER_ID)

#     # initial validation
#     assert staticcall Ledger(ledger).isUserWallet(_newWallet) # dev: not a user wallet
#     assert staticcall UserWallet(_thisWallet).trialFundsAmount() == 0 # dev: has trial funds
#     assert not self.isFrozen # dev: frozen

#     # wallet config checks
#     newWalletConfig: address = staticcall UserWallet(_newWallet).walletConfig()
#     assert self._isMatchingOwnership(newWalletConfig, _owner) # dev: not same owner
#     assert self._hasNoManagers(newWalletConfig) # dev: has managers

#     # TODO
#     # TODO: once there is proper transfer/whitelist, let's check that is empty also
#     # TODO

#     return True


# # migrate settings


# @external
# def migrateSettings(_oldWallet: address):
#     owner: address = self.owner
#     assert msg.sender == owner # dev: no perms
#     assert self._canMigrateSettings(_oldWallet, owner) # dev: cannot migrate settings

#     # TODO: migrate all settings


# @view
# @internal
# def _canMigrateSettings(_oldWallet: address, _owner: address) -> bool:
#     ledger: address = staticcall Registry(UNDY_HQ).getAddr(LEDGER_ID)
#     assert staticcall Ledger(ledger).isUserWallet(_oldWallet) # dev: not a user wallet

#     oldWalletConfig: address = staticcall UserWallet(_oldWallet).walletConfig()
#     assert self._isMatchingOwnership(oldWalletConfig, _owner) # dev: not same owner
#     assert self._hasNoManagers(self) # dev: has managers

#     # TODO
#     # TODO: once there is proper transfer/whitelist, let's check that is empty also
#     # TODO

#     return True


# # shared utils


# @view
# @internal
# def _isMatchingOwnership(_walletConfig: address, _owner: address) -> bool:
#     assert _owner == staticcall UserWalletConfig(_walletConfig).owner() # dev: not same owner
#     assert not staticcall UserWalletConfig(_walletConfig).hasPendingOwnerChange() # dev: pending owner change
#     assert not self._hasPendingOwnerChange() # dev: pending owner change
#     assert self.groupId == staticcall UserWalletConfig(_walletConfig).groupId() # dev: wrong group id
#     return True


# @view
# @internal
# def _hasNoManagers(_walletConfig: address) -> bool:
#     startingAgent: address = staticcall UserWalletConfig(_walletConfig).startingAgent()
#     if startingAgent == empty(address):
#         assert staticcall UserWalletConfig(_walletConfig).numManagers() == 0 # dev: has managers
#     else:
#         assert staticcall UserWalletConfig(_walletConfig).indexOfManager(startingAgent) == 1 # dev: invalid manager
#         assert staticcall UserWalletConfig(_walletConfig).numManagers() == 2 # dev: has other managers
#     return True
