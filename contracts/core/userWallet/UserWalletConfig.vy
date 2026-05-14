#    ┓ ┏  ┓┓   
#    ┃┃┃┏┓┃┃┏┓╋
#    ┗┻┛┗┻┗┗┗ ┗
#      ,----..                                                   
#     /   /   \                        .--.,   ,--,              
#    |   :     :  ,---.        ,---, ,--.'  \,--.'|              
#    .   |  ;. / '   ,'\   ,-+-. /  ||  | /\/|  |,     ,----._,. 
#    .   ; /--` /   /   | ,--.'|'   |:  : :  `--'_    /   /  ' / 
#    ;   | ;   .   ; ,. :|   |  ,"' |:  | |-,,' ,'|  |   :     | 
#    |   : |   '   | |: :|   | /  | ||  : :/|'  | |  |   | .\  . 
#    .   | '___'   | .; :|   | |  | ||  |  .'|  | :  .   ; ';  | 
#    '   ; : .'|   :    ||   | |  |/ '  : '  '  : |__'   .   . | 
#    '   | '/  :\   \  / |   | |--'  |  | |  |  | '.'|`---`-'| | 
#    |   :    /  `----'  |   |/      |  : \  ;  :    ;.'__/\_: | 
#     \   \ .'           '---'       |  |,'  |  ,   / |   :    : 
#      `---`                         `--'     ---`-'   \   \  /  
#                                                       `--`-'   
#     ╔════════════════════════════════════════════════╗
#     ║  ** User Wallet Config **                      ║
#     ║  Handles all user wallet config functionality  ║
#     ╚════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3
# pragma optimize codesize

initializes: ownership
exports: ownership.__interface__
import contracts.modules.Ownership as ownership

from interfaces import WalletStructs as ws
from interfaces import WalletConfigStructs as wcs

interface UserWallet:
    def withdrawFromYield(_legoId: uint256, _vaultToken: address, _amount: uint256, _extraData: bytes32, _isSpecialTx: bool) -> (uint256, address, uint256, uint256): nonpayable
    def updateAssetData(_legoId: uint256, _asset: address, _shouldCheckYield: bool, _totalUsdValue: uint256, _ad: ws.ActionData) -> uint256: nonpayable
    def transferFunds(_recipient: address, _asset: address, _amount: uint256, _isCheque: bool, _isSpecialTx: bool) -> (uint256, uint256): nonpayable
    def recoverNft(_collection: address, _nftTokenId: uint256, _recipient: address): nonpayable
    def setLegoAccessForAction(_legoAddr: address, _action: ws.ActionType): nonpayable
    def deregisterAsset(_asset: address): nonpayable
    def assets(i: uint256) -> address: view
    def numAssets() -> uint256: view

interface ActionDataProvider:
    def checkSignerPermissionsAndGetBundle(_walletConfig: address, _signer: address, _action: ws.ActionType, _undyHq: address, _eth: address, _weth: address, _sentinel: address, _assets: DynArray[address, MAX_ASSETS], _legoIds: DynArray[uint256, MAX_LEGOS], _transferRecipient: address) -> ws.ActionData: view
    def getActionDataBundle(_walletConfig: address, _legoId: uint256, _signer: address, _undyHq: address, _eth: address, _weth: address) -> ws.ActionData: view
    def canSetBackpackItem(_newBackpackAddr: address, _caller: address, _owner: address, _undyHq: address) -> bool: view
    def canPerformSecurityAction(_addr: address, _undyHq: address) -> bool: view
    def isPrivilegedUndyAddr(_addr: address, _undyHq: address) -> bool: view
    def isValidRegistryAddr(_addr: address, _undyHq: address) -> bool: view
    def isSwitchboardAddr(_addr: address, _undyHq: address) -> bool: view
    def isAgentSender(_addr: address, _agent: address) -> bool: view

interface Sentinel:
    def checkManagerLimitsPostTx(_txUsdValue: uint256, _specificLimits: wcs.ManagerLimits, _globalLimits: wcs.ManagerLimits, _managerPeriod: uint256, _data: wcs.ManagerData, _needsVaultApproval: bool, _underlyingAsset: address, _vaultToken: address, _shouldCheckSwap: bool, _specificSwapPerms: wcs.SwapPerms, _globalSwapPerms: wcs.SwapPerms, _fromAssetUsdValue: uint256, _toAssetUsdValue: uint256, _vaultRegistry: address) -> (bool, wcs.ManagerData): view
    def isValidPayeeAndGetData(_isWhitelisted: bool, _isPayee: bool, _asset: address, _amount: uint256, _txUsdValue: uint256, _config: wcs.PayeeSettings, _globalConfig: wcs.GlobalPayeeSettings, _data: wcs.PayeeData) -> (bool, wcs.PayeeData, bool): view
    def isValidChequeAndGetData(_asset: address, _amount: uint256, _txUsdValue: uint256, _cheque: wcs.Cheque, _globalConfig: wcs.ChequeSettings, _chequeData: wcs.ChequeData, _isManager: bool) -> (bool, wcs.ChequeData, bool): view

interface LootDistributor:
    def updateDepositPointsWithNewValue(_user: address, _newUsdValue: uint256): nonpayable

interface Registry:
    def getAddr(_regId: uint256) -> address: view

event EjectionModeSet:
    inEjectMode: bool

event FrozenSet:
    isFrozen: bool
    caller: indexed(address)

event NftRecovered:
    collection: indexed(address)
    nftTokenId: uint256
    recipient: indexed(address)

event MigrationConfigApplied:
    fromConfig: indexed(address)
    timeLock: uint256

# core
wallet: public(address)

# wallet backpack contracts
kernel: public(address)
sentinel: public(address)
highCommand: public(address)
paymaster: public(address)
chequeBook: public(address)
migrator: public(address)

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

# whitelist
whitelistAddr: public(HashMap[uint256, address]) # index -> whitelist
indexOfWhitelist: public(HashMap[address, uint256]) # whitelist -> index
numWhitelisted: public(uint256) # num whitelisted
pendingWhitelist: public(HashMap[address, wcs.PendingWhitelist]) # addr -> pending whitelist

# cheques
cheques: public(HashMap[address, wcs.Cheque]) # addr -> cheque
chequeSettings: public(wcs.ChequeSettings)
chequePeriodData: public(wcs.ChequeData)
numActiveCheques: public(uint256)

# global config
globalManagerSettings: public(wcs.GlobalManagerSettings)
globalPayeeSettings: public(wcs.GlobalPayeeSettings)

# timelock
timeLock: public(uint256)
pendingTimeLock: public(wcs.PendingTimeLock)

# instant action settings
instantActionSettings: public(wcs.InstantActionSettings)
pendingInstantActionSettings: public(wcs.PendingInstantActionSettings)

# other config
pendingMigration: public(wcs.PendingMigration)
isFrozen: public(bool)
inEjectMode: public(bool)
groupId: public(uint256)
startingAgent: public(address)

MAX_ASSETS: constant(uint256) = 10
MAX_LEGOS: constant(uint256) = 10

UNDY_HQ: immutable(address)
WETH: immutable(address)
ETH: immutable(address)
ACTION_DATA_PROVIDER: immutable(address)

MIN_TIMELOCK: public(immutable(uint256))
MAX_TIMELOCK: public(immutable(uint256))


@deploy
def __init__(
    _undyHq: address,
    _owner: address,
    _groupId: uint256,
    # manager / payee settings
    _globalManagerSettings: wcs.GlobalManagerSettings,
    _globalPayeeSettings: wcs.GlobalPayeeSettings,
    _chequeSettings: wcs.ChequeSettings,
    _startingAgent: address,
    _starterAgentSettings: wcs.ManagerSettings,
    # key contracts / addrs
    _kernel: address,
    _sentinel: address,
    _highCommand: address,
    _paymaster: address,
    _chequeBook: address,
    _migrator: address,
    _actionDataProvider: address,
    _wethAddr: address,
    _ethAddr: address,
    # timelock
    _minTimeLock: uint256,
    _maxTimeLock: uint256,
    _instantActionSettings: wcs.InstantActionSettings,
):
    # initialize ownership
    ownership.__init__(_undyHq, _owner, _minTimeLock, _maxTimeLock)
    UNDY_HQ = _undyHq

    # wallet backpack addrs
    self.kernel = _kernel
    self.sentinel = _sentinel
    self.highCommand = _highCommand
    self.paymaster = _paymaster
    self.chequeBook = _chequeBook
    self.migrator = _migrator
    ACTION_DATA_PROVIDER = _actionDataProvider

    # eth addrs
    WETH = _wethAddr
    ETH = _ethAddr

    # not using 0 index
    self.numManagers = 1
    self.numPayees = 1
    self.numWhitelisted = 1

    # group id
    self.groupId = _groupId

    # timelock
    MIN_TIMELOCK = _minTimeLock
    MAX_TIMELOCK = _maxTimeLock
    self.timeLock = _minTimeLock

    # manager / payee settings
    self.globalManagerSettings = _globalManagerSettings
    self.globalPayeeSettings = _globalPayeeSettings
    self.chequeSettings = _chequeSettings
    self.instantActionSettings = _instantActionSettings

    # initial agent
    if _startingAgent != empty(address):
        self.managerSettings[_startingAgent] = _starterAgentSettings
        self.startingAgent = _startingAgent
        self.managers[1] = _startingAgent
        self.indexOfManager[_startingAgent] = 1
        self.numManagers = 2


@external
def setWallet(_wallet: address):
    assert msg.sender == staticcall Registry(UNDY_HQ).getAddr(5) # dev: no perms
    assert self.wallet == empty(address) # dev: wallet already set
    assert _wallet != empty(address) # dev: invalid wallet
    self.wallet = _wallet


#############
# Time Lock #
#############


@external
def setTimeLock(_numBlocks: uint256):
    assert msg.sender == ownership.owner # dev: no perms
    assert _numBlocks >= MIN_TIMELOCK and _numBlocks <= MAX_TIMELOCK # dev: invalid time lock

    currentTimeLock: uint256 = self.timeLock
    pendingConfirmBlock: uint256 = self.pendingTimeLock.confirmBlock

    if _numBlocks >= currentTimeLock:
        if _numBlocks == currentTimeLock:
            return

        if pendingConfirmBlock != 0:
            self.pendingTimeLock = empty(wcs.PendingTimeLock)

        self.timeLock = _numBlocks
        return

    assert pendingConfirmBlock == 0 # dev: pending time lock already exists

    self.pendingTimeLock = wcs.PendingTimeLock(
        newTimeLock = _numBlocks,
        initiatedBlock = block.number,
        confirmBlock = unsafe_add(block.number, currentTimeLock),
        currentOwner = ownership.owner,
    )


@external
def confirmPendingTimeLock():
    assert msg.sender == ownership.owner # dev: no perms

    pending: wcs.PendingTimeLock = self.pendingTimeLock
    assert pending.confirmBlock != 0 # dev: no pending time lock
    assert block.number >= pending.confirmBlock # dev: time delay not reached
    assert pending.currentOwner == ownership.owner # dev: owner must match
    assert pending.newTimeLock >= MIN_TIMELOCK and pending.newTimeLock <= MAX_TIMELOCK # dev: pending time lock out of bounds

    self.timeLock = pending.newTimeLock
    self.pendingTimeLock = empty(wcs.PendingTimeLock)


@external
def cancelPendingTimeLock():
    if msg.sender != ownership.owner:
        assert self._canPerformSecurityAction(msg.sender) # dev: no perms

    assert self.pendingTimeLock.confirmBlock != 0 # dev: no pending time lock
    self.pendingTimeLock = empty(wcs.PendingTimeLock)


###########################
# Instant Action Settings #
###########################


@external
def setInstantActionSettings(_settings: wcs.InstantActionSettings):
    assert msg.sender == ownership.owner # dev: no perms

    current: wcs.InstantActionSettings = self.instantActionSettings
    hasEnable: bool = (
        (not current.canInstantAddManager and _settings.canInstantAddManager) or
        (not current.canInstantAddPayee and _settings.canInstantAddPayee) or
        (not current.canInstantSetGlobalPayeeSettings and _settings.canInstantSetGlobalPayeeSettings) or
        (not current.canInstantSetChequeSettings and _settings.canInstantSetChequeSettings)
    )
    if not hasEnable:
        self.instantActionSettings = _settings
        if self.pendingInstantActionSettings.confirmBlock != 0:
            self.pendingInstantActionSettings = empty(wcs.PendingInstantActionSettings)
        return

    assert self.pendingInstantActionSettings.confirmBlock == 0 # dev: pending instant settings already exist
    self.instantActionSettings = wcs.InstantActionSettings(
        canInstantAddManager = current.canInstantAddManager and _settings.canInstantAddManager,
        canInstantAddPayee = current.canInstantAddPayee and _settings.canInstantAddPayee,
        canInstantSetGlobalPayeeSettings = current.canInstantSetGlobalPayeeSettings and _settings.canInstantSetGlobalPayeeSettings,
        canInstantSetChequeSettings = current.canInstantSetChequeSettings and _settings.canInstantSetChequeSettings,
    )
    self.pendingInstantActionSettings = wcs.PendingInstantActionSettings(
        settings = _settings,
        initiatedBlock = block.number,
        confirmBlock = unsafe_add(block.number, self.timeLock),
        currentOwner = ownership.owner,
    )


@external
def confirmPendingInstantActionSettings():
    assert msg.sender == ownership.owner # dev: no perms

    pending: wcs.PendingInstantActionSettings = self.pendingInstantActionSettings
    assert pending.confirmBlock != 0 # dev: no pending instant settings
    assert block.number >= pending.confirmBlock # dev: time delay not reached
    assert pending.currentOwner == ownership.owner # dev: owner must match

    self.instantActionSettings = pending.settings
    self.pendingInstantActionSettings = empty(wcs.PendingInstantActionSettings)


@external
def cancelPendingInstantActionSettings():
    if msg.sender != ownership.owner:
        assert self._canPerformSecurityAction(msg.sender) # dev: no perms

    assert self.pendingInstantActionSettings.confirmBlock != 0 # dev: no pending instant settings
    self.pendingInstantActionSettings = empty(wcs.PendingInstantActionSettings)


#####################
# Pending Migration #
#####################


@external
def setPendingMigration(_toWallet: address):
    assert msg.sender == self.migrator # dev: no perms
    assert self.pendingMigration.confirmBlock == 0 # dev: pending migration exists

    self.pendingMigration = wcs.PendingMigration(
        toWallet = _toWallet,
        initiatedBlock = block.number,
        confirmBlock = unsafe_add(block.number, self.timeLock),
        currentOwner = ownership.owner,
    )


@external
def clearPendingMigration():
    assert msg.sender == self.migrator # dev: no perms
    self.pendingMigration = empty(wcs.PendingMigration)


@external
def applyMigratedConfigSettings(
    _fromConfig: address,
    _timeLock: uint256,
    _instantSettings: wcs.InstantActionSettings,
    _globalManagerSettings: wcs.GlobalManagerSettings,
    _globalPayeeSettings: wcs.GlobalPayeeSettings,
    _chequeSettings: wcs.ChequeSettings,
):
    assert msg.sender == self.migrator # dev: no perms
    assert _fromConfig != empty(address) # dev: invalid source config

    self.timeLock = max(MIN_TIMELOCK, min(_timeLock, MAX_TIMELOCK))
    self.instantActionSettings = _instantSettings
    self.globalManagerSettings = _globalManagerSettings
    self.globalPayeeSettings = _globalPayeeSettings
    self.chequeSettings = _chequeSettings

    log MigrationConfigApplied(
        fromConfig = _fromConfig,
        timeLock = self.timeLock,
    )


#####################
# Signer Validation #
#####################


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
    return staticcall ActionDataProvider(ACTION_DATA_PROVIDER).checkSignerPermissionsAndGetBundle(
        self,
        _signer,
        _action,
        UNDY_HQ,
        ETH,
        WETH,
        self.sentinel,
        _assets,
        _legoIds,
        _transferRecipient,
    )


# post action (usd value limits)


@external
def checkManagerLimitsPostTx(
    _manager: address,
    _txUsdValue: uint256,
    _underlyingAsset: address,
    _vaultToken: address,
    _shouldCheckSwap: bool,
    _fromAssetUsdValue: uint256,
    _toAssetUsdValue: uint256,
    _vaultRegistry: address,
):
    assert msg.sender == self.wallet # dev: no perms

    # required data / config
    config: wcs.ManagerSettings = self.managerSettings[_manager]
    globalConfig: wcs.GlobalManagerSettings = self.globalManagerSettings
    managerData: wcs.ManagerData = self.managerPeriodData[_manager]

    # check usd value limits
    canFinishTx: bool = False
    canFinishTx, managerData = staticcall Sentinel(self.sentinel).checkManagerLimitsPostTx(
        _txUsdValue,
        config.limits,
        globalConfig.limits,
        globalConfig.managerPeriod,
        managerData,
        (config.legoPerms.onlyApprovedYieldOpps or globalConfig.legoPerms.onlyApprovedYieldOpps),
        _underlyingAsset,
        _vaultToken,
        _shouldCheckSwap,
        config.swapPerms,
        globalConfig.swapPerms,
        _fromAssetUsdValue,
        _toAssetUsdValue,
        _vaultRegistry,
    )

    # IMPORTANT -- this checks manager limits (usd values)
    assert canFinishTx # dev: manager limits not allowed

    self.managerPeriodData[_manager] = managerData


####################
# Payee Validation #
####################


@external
def checkRecipientLimitsAndUpdateData(
    _recipient: address,
    _txUsdValue: uint256,
    _asset: address,
    _amount: uint256,
):
    assert msg.sender == self.wallet # dev: no perms

    # whitelisted
    isWhitelisted: bool = self.indexOfWhitelist[_recipient] != 0

    # only get the extra data if the recipient is not whitelisted
    isPayee: bool = False
    config: wcs.PayeeSettings = empty(wcs.PayeeSettings)
    globalConfig: wcs.GlobalPayeeSettings = empty(wcs.GlobalPayeeSettings)
    data: wcs.PayeeData = empty(wcs.PayeeData)
    if not isWhitelisted:
        isPayee = self.indexOfPayee[_recipient] != 0
        config = self.payeeSettings[_recipient]
        globalConfig = self.globalPayeeSettings
        data = self.payeePeriodData[_recipient]

    # check if payee is valid
    canPayRecipient: bool = False
    didUpdate: bool = False
    canPayRecipient, data, didUpdate = staticcall Sentinel(self.sentinel).isValidPayeeAndGetData(
        isWhitelisted,
        isPayee,
        _asset,
        _amount,
        _txUsdValue,
        config,
        globalConfig,
        data,
    )

    # IMPORTANT -- make sure this recipient can receive funds
    assert canPayRecipient # dev: invalid payee

    # only save if data was updated  
    if didUpdate:
        self.payeePeriodData[_recipient] = data
    

#####################
# Cheque Validation #
#####################


@external
def validateCheque(
    _recipient: address,
    _asset: address,
    _amount: uint256,
    _txUsdValue: uint256,
    _signer: address,
):
    assert msg.sender == self.wallet # dev: no perms

    # get required config / data
    cheque: wcs.Cheque = self.cheques[_recipient]
    globalConfig: wcs.ChequeSettings = self.chequeSettings
    data: wcs.ChequeData = self.chequePeriodData

    isManager: bool = _signer != ownership.owner and self.indexOfManager[_signer] != 0

    # cheque validation
    isValidCheque: bool = False
    didPay: bool = False
    isValidCheque, data, didPay = staticcall Sentinel(self.sentinel).isValidChequeAndGetData(
        _asset,
        _amount,
        _txUsdValue,
        cheque,
        globalConfig,
        data,
        isManager,
    )

    # IMPORTANT -- make sure this recipient has valid cheque
    assert isValidCheque # dev: invalid cheque

    # only save if data was updated
    if didPay:
        self.chequePeriodData = data
        self.numActiveCheques -= 1

        # deactivate cheque after payment to prevent double-pulling
        self.cheques[_recipient] = empty(wcs.Cheque)


#############
# Whitelist #
#############


# add pending


@external
def addPendingWhitelistAddr(_addr: address, _pending: wcs.PendingWhitelist):
    assert msg.sender == self.kernel # dev: no perms
    self.pendingWhitelist[_addr] = _pending


# cancel pending


@external
def cancelPendingWhitelistAddr(_addr: address):
    assert msg.sender == self.kernel # dev: no perms
    self.pendingWhitelist[_addr] = empty(wcs.PendingWhitelist)


# confirm pending


@external
def confirmWhitelistAddr(_addr: address):
    assert msg.sender == self.kernel # dev: no perms
    pending: wcs.PendingWhitelist = self.pendingWhitelist[_addr]
    assert pending.confirmBlock != 0 # dev: no pending whitelist
    assert pending.confirmBlock <= block.number # dev: time delay not reached
    self.pendingWhitelist[_addr] = empty(wcs.PendingWhitelist)
    self._registerWhitelistAddr(_addr)


# add via migrator


@external
def addWhitelistAddrViaMigrator(_addr: address):
    assert msg.sender == self.migrator # dev: no perms
    assert _addr != empty(address) # dev: invalid address
    assert not staticcall ActionDataProvider(ACTION_DATA_PROVIDER).isPrivilegedUndyAddr(_addr, UNDY_HQ) # dev: invalid address
    assert self.indexOfPayee[_addr] == 0 and not self.cheques[_addr].active and self.indexOfManager[_addr] == 0 # dev: payee, manager, or active cheque
    self._registerWhitelistAddr(_addr)


# register whitelist


@internal
def _registerWhitelistAddr(_addr: address):
    assert self.indexOfWhitelist[_addr] == 0 # dev: already whitelisted
    wid: uint256 = self.numWhitelisted
    self.whitelistAddr[wid] = _addr
    self.indexOfWhitelist[_addr] = wid
    self.numWhitelisted = wid + 1


# remove whitelist


@external
def removeWhitelistAddr(_addr: address):
    assert msg.sender == self.kernel # dev: no perms

    numWhitelisted: uint256 = self.numWhitelisted
    targetIndex: uint256 = self.indexOfWhitelist[_addr]
    if targetIndex == 0:
        return

    # update data
    lastIndex: uint256 = numWhitelisted - 1
    self.numWhitelisted = lastIndex

    # get last item, replace the removed item
    lastItem: address = self.whitelistAddr[lastIndex]
    self.whitelistAddr[targetIndex] = lastItem
    self.indexOfWhitelist[lastItem] = targetIndex
    self.indexOfWhitelist[_addr] = 0


####################
# Manager Settings #
####################


# add manager


@external
def addManager(_manager: address, _config: wcs.ManagerSettings):
    assert msg.sender == self.highCommand or msg.sender == self.migrator # dev: no perms
    self.managerSettings[_manager] = _config
    self._registerManager(_manager)


# update manager


@external
def updateManager(_manager: address, _config: wcs.ManagerSettings):
    assert msg.sender == self.highCommand or msg.sender == self.migrator # dev: no perms
    self.managerSettings[_manager] = _config


# register manager


@internal
def _registerManager(_manager: address):
    assert self.indexOfManager[_manager] == 0 # dev: already manager
    mid: uint256 = self.numManagers
    self.managers[mid] = _manager
    self.indexOfManager[_manager] = mid
    self.numManagers = mid + 1


# remove manager


@external
def removeManager(_manager: address):
    assert msg.sender == self.highCommand # dev: no perms

    numManagers: uint256 = self.numManagers
    targetIndex: uint256 = self.indexOfManager[_manager]
    if targetIndex == 0:
        return

    self.managerSettings[_manager] = empty(wcs.ManagerSettings)
    self.managerPeriodData[_manager] = empty(wcs.ManagerData)

    # update data
    lastIndex: uint256 = numManagers - 1
    self.numManagers = lastIndex

    # get last item, replace the removed item
    lastItem: address = self.managers[lastIndex]
    self.managers[targetIndex] = lastItem
    self.indexOfManager[lastItem] = targetIndex
    self.indexOfManager[_manager] = 0


# global manager settings


@external
def setGlobalManagerSettings(_config: wcs.GlobalManagerSettings):
    assert msg.sender == self.highCommand # dev: no perms
    self.globalManagerSettings = _config


##################
# Payee Settings #
##################


# add payee


@external
def addPayee(_payee: address, _config: wcs.PayeeSettings):
    assert msg.sender == self.paymaster or msg.sender == self.migrator # dev: no perms
    self.payeeSettings[_payee] = _config
    self._registerPayee(_payee)
    

# update payee


@external
def updatePayee(_payee: address, _config: wcs.PayeeSettings):
    assert msg.sender == self.paymaster # dev: no perms
    self.payeeSettings[_payee] = _config


# register payee


@internal
def _registerPayee(_payee: address):
    assert self.indexOfPayee[_payee] == 0 # dev: already payee
    pid: uint256 = self.numPayees
    self.payees[pid] = _payee
    self.indexOfPayee[_payee] = pid
    self.numPayees = pid + 1


# remove payee


@external
def removePayee(_payee: address):
    assert msg.sender == self.paymaster # dev: no perms

    numPayees: uint256 = self.numPayees
    targetIndex: uint256 = self.indexOfPayee[_payee]
    if targetIndex == 0:
        return

    self.payeeSettings[_payee] = empty(wcs.PayeeSettings)
    self.payeePeriodData[_payee] = empty(wcs.PayeeData)

    # update data
    lastIndex: uint256 = numPayees - 1
    self.numPayees = lastIndex

    # get last item, replace the removed item
    lastItem: address = self.payees[lastIndex]
    self.payees[targetIndex] = lastItem
    self.indexOfPayee[lastItem] = targetIndex
    self.indexOfPayee[_payee] = 0


# global payee settings


@external
def setGlobalPayeeSettings(_config: wcs.GlobalPayeeSettings):
    assert msg.sender == self.paymaster # dev: no perms
    self.globalPayeeSettings = _config


###################
# Cheque Settings #
###################


# create cheque


@external
def createCheque(
    _recipient: address,
    _cheque: wcs.Cheque,
    _chequeData: wcs.ChequeData,
    _isExistingCheque: bool,
):
    assert msg.sender == self.chequeBook # dev: no perms
    self.cheques[_recipient] = _cheque
    self.chequePeriodData = _chequeData
    if not _isExistingCheque:
        self.numActiveCheques += 1


# cancel cheque


@external
def cancelCheque(_recipient: address):
    assert msg.sender == self.chequeBook # dev: no perms
    self.cheques[_recipient] = empty(wcs.Cheque)
    self.numActiveCheques -= 1


# global cheque settings


@external
def setChequeSettings(_config: wcs.ChequeSettings):
    assert msg.sender == self.chequeBook # dev: no perms
    self.chequeSettings = _config


################
# Wallet Tools #
################


# update asset data


@external
def updateAssetData(_legoId: uint256, _asset: address, _shouldCheckYield: bool) -> uint256:
    if msg.sender != self.migrator and not self._isSwitchboardAddr(msg.sender):
        assert self._canPerformSecurityAction(msg.sender) # dev: no perms
    ad: ws.ActionData = self._getActionDataBundle(_legoId, msg.sender)
    newTotalUsdValue: uint256 = extcall UserWallet(ad.wallet).updateAssetData(_legoId, _asset, _shouldCheckYield, ad.lastTotalUsdValue, ad)
    extcall LootDistributor(ad.lootDistributor).updateDepositPointsWithNewValue(ad.wallet, newTotalUsdValue)
    return newTotalUsdValue


@external
def updateAllAssetData(_shouldCheckYield: bool) -> uint256:
    ad: ws.ActionData = self._getActionDataBundle(0, msg.sender)
    if not self._isSwitchboardAddr(msg.sender):
        assert self._canPerformSecurityAction(msg.sender) # dev: no perms

    numAssets: uint256 = staticcall UserWallet(ad.wallet).numAssets()
    newTotalUsdValue: uint256 = ad.lastTotalUsdValue
    for i: uint256 in range(1, numAssets, bound=max_value(uint256)):           
        asset: address = staticcall UserWallet(ad.wallet).assets(i)
        if asset != empty(address):
            newTotalUsdValue = extcall UserWallet(ad.wallet).updateAssetData(0, asset, _shouldCheckYield, newTotalUsdValue, ad)

    extcall LootDistributor(ad.lootDistributor).updateDepositPointsWithNewValue(ad.wallet, newTotalUsdValue)
    return newTotalUsdValue


# migrate funds


@external
def migrateFunds(_toWallet: address, _asset: address) -> uint256:
    assert msg.sender == self.migrator # dev: no perms
    amount: uint256 = 0
    na: uint256 = 0
    amount, na = extcall UserWallet(self.wallet).transferFunds(_toWallet, _asset, max_value(uint256), False, True)
    return amount


# prepare payment


@external
def preparePayment(
    _targetAsset: address,
    _legoId: uint256,
    _vaultToken: address,
    _vaultAmount: uint256 = max_value(uint256),
) -> (uint256, uint256):
    assert self._isValidRegistryAddr(msg.sender) # dev: no perms
    assert _targetAsset != empty(address) # dev: invalid target asset

    # withdraw from yield position
    na: uint256 = 0
    underlyingAsset: address = empty(address)
    underlyingAmount: uint256 = 0
    txUsdValue: uint256 = 0
    na, underlyingAsset, underlyingAmount, txUsdValue = extcall UserWallet(self.wallet).withdrawFromYield(_legoId, _vaultToken, _vaultAmount, empty(bytes32), True)
    assert underlyingAsset == _targetAsset # dev: asset mismatch

    return underlyingAmount, txUsdValue


# deregister asset


@external
def deregisterAsset(_asset: address):
    if msg.sender != self.migrator:
        assert self._isValidRegistryAddr(msg.sender) # dev: no perms
    extcall UserWallet(self.wallet).deregisterAsset(_asset)


# recover nft


@external
def recoverNft(_collection: address, _nftTokenId: uint256, _recipient: address):
    if msg.sender != ownership.owner:
        assert self._isSwitchboardAddr(msg.sender) # dev: no perms

    extcall UserWallet(self.wallet).recoverNft(_collection, _nftTokenId, _recipient)
    log NftRecovered(collection = _collection, nftTokenId = _nftTokenId, recipient = _recipient)


# freeze wallet


@external
def setFrozen(_isFrozen: bool):
    if msg.sender != ownership.owner:
        assert self._canPerformSecurityAction(msg.sender) # dev: no perms
    self.isFrozen = _isFrozen
    log FrozenSet(isFrozen=_isFrozen, caller=msg.sender)


# ejection mode


@external
def setEjectionMode(_shouldEject: bool):
    # NOTE: this needs to be triggered from Switchboard, as it has other side effects / reactions
    assert self._isSwitchboardAddr(msg.sender) # dev: no perms

    self.inEjectMode = _shouldEject
    log EjectionModeSet(inEjectMode = _shouldEject)


# lego access


@external
def setLegoAccessForAction(_legoId: uint256, _action: ws.ActionType):
    ad: ws.ActionData = self._getActionDataBundle(_legoId, msg.sender)
    if msg.sender != ad.walletOwner:
        assert self._isValidRegistryAddr(msg.sender) # dev: no perms
    extcall UserWallet(ad.wallet).setLegoAccessForAction(ad.legoAddr, _action)


# is valid registry addr


@view
@internal
def _isValidRegistryAddr(_addr: address) -> bool:
    return staticcall ActionDataProvider(ACTION_DATA_PROVIDER).isValidRegistryAddr(_addr, UNDY_HQ)


# is signer switchboard



@view
@internal
def _isSwitchboardAddr(_signer: address) -> bool:
    return staticcall ActionDataProvider(ACTION_DATA_PROVIDER).isSwitchboardAddr(_signer, UNDY_HQ)


# can perform security action


@view
@internal
def _canPerformSecurityAction(_addr: address) -> bool:
    return staticcall ActionDataProvider(ACTION_DATA_PROVIDER).canPerformSecurityAction(_addr, UNDY_HQ)


# is agent sender


@view
@external
def isAgentSender(_addr: address) -> bool:
    return staticcall ActionDataProvider(ACTION_DATA_PROVIDER).isAgentSender(_addr, self.startingAgent)


###################
# Wallet Backpack #
###################


@external
def setKernel(_kernel: address):
    assert self._canSetBackpackItem(_kernel, msg.sender) # dev: no perms
    self.kernel = _kernel


@external
def setSentinel(_sentinel: address):
    assert self._canSetBackpackItem(_sentinel, msg.sender) # dev: no perms
    self.sentinel = _sentinel


@external
def setHighCommand(_highCommand: address):
    assert self._canSetBackpackItem(_highCommand, msg.sender) # dev: no perms
    self.highCommand = _highCommand


@external
def setPaymaster(_paymaster: address):
    assert self._canSetBackpackItem(_paymaster, msg.sender) # dev: no perms
    self.paymaster = _paymaster


@external
def setChequeBook(_chequeBook: address):
    assert self._canSetBackpackItem(_chequeBook, msg.sender) # dev: no perms
    self.chequeBook = _chequeBook


@external
def setMigrator(_migrator: address):
    assert self._canSetBackpackItem(_migrator, msg.sender) # dev: no perms
    assert self.pendingMigration.confirmBlock == 0 # dev: pending migration exists
    self.migrator = _migrator


# validation


@view
@internal
def _canSetBackpackItem(_newBackpackAddr: address, _caller: address) -> bool:
    return staticcall ActionDataProvider(ACTION_DATA_PROVIDER).canSetBackpackItem(_newBackpackAddr, _caller, ownership.owner, UNDY_HQ)


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
    return staticcall ActionDataProvider(ACTION_DATA_PROVIDER).getActionDataBundle(self, _legoId, _signer, UNDY_HQ, ETH, WETH)
