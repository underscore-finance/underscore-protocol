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
#     Underscore Protocol License: https://github.com/hightophq/underscore-protocol/blob/master/LICENSE.md
#     Hightop Financial, Inc. (C) 2025 

# @version 0.4.3
# pragma optimize codesize

initializes: ownership
exports: ownership.__interface__
import contracts.modules.Ownership as ownership

from interfaces import WalletStructs as ws
from interfaces import WalletConfigStructs as wcs

from ethereum.ercs import IERC721
from ethereum.ercs import IERC20

interface UserWallet:
    def withdrawFromYield(_legoId: uint256, _vaultToken: address, _amount: uint256 = max_value(uint256), _extraData: bytes32 = empty(bytes32), _isSpecialTx: bool = False) -> (uint256, address, uint256, uint256): nonpayable
    def transferFunds(_recipient: address, _asset: address = empty(address), _amount: uint256 = max_value(uint256), _isCheque: bool = False, _isSpecialTx: bool = False) -> (uint256, uint256): nonpayable
    def updateAssetData(_legoId: uint256, _asset: address, _shouldCheckYield: bool, _totalUsdValue: uint256, _ad: ws.ActionData = empty(ws.ActionData)) -> uint256: nonpayable
    def recoverNft(_collection: address, _nftTokenId: uint256, _recipient: address): nonpayable
    def setLegoAccessForAction(_legoAddr: address, _action: ws.ActionType) -> bool: nonpayable
    def assetData(_asset: address) -> ws.WalletAssetData: view
    def deregisterAsset(_asset: address) -> bool: nonpayable
    def assets(i: uint256) -> address: view
    def walletConfig() -> address: view
    def numAssets() -> uint256: view

interface Sentinel:
    def canSignerPerformActionWithConfig(_isOwner: bool, _isManager: bool, _data: wcs.ManagerData, _config: wcs.ManagerSettings, _globalConfig: wcs.GlobalManagerSettings, _action: ws.ActionType, _assets: DynArray[address, MAX_ASSETS] = [], _legoIds: DynArray[uint256, MAX_LEGOS] = [], _payee: address = empty(address)) -> bool: view
    def isValidPayeeAndGetData(_isWhitelisted: bool, _isOwner: bool, _isPayee: bool, _asset: address, _amount: uint256, _txUsdValue: uint256, _config: wcs.PayeeSettings, _globalConfig: wcs.GlobalPayeeSettings, _data: wcs.PayeeData) -> (bool, wcs.PayeeData): view
    def isValidChequeAndGetData(_asset: address, _amount: uint256, _txUsdValue: uint256, _cheque: wcs.Cheque, _globalConfig: wcs.ChequeSettings, _chequeData: wcs.ChequeData, _isManager: bool) -> (bool, wcs.ChequeData): view
    def checkManagerUsdLimitsAndUpdateData(_txUsdValue: uint256, _specificLimits: wcs.ManagerLimits, _globalLimits: wcs.ManagerLimits, _managerPeriod: uint256, _data: wcs.ManagerData) -> (bool, wcs.ManagerData): view

interface Ledger:
    def isRegisteredBackpackItem(_addr: address) -> bool: view
    def getLastTotalUsdValue(_user: address) -> uint256: view

interface MissionControl:
    def canPerformSecurityAction(_addr: address) -> bool: view
    def isLockedSigner(_signer: address) -> bool: view

interface Registry:
    def isValidAddr(_addr: address) -> bool: view
    def getAddr(_regId: uint256) -> address: view

interface LootDistributor:
    def updateDepositPointsWithNewValue(_user: address, _newUsdValue: uint256): nonpayable

interface Switchboard:
    def isSwitchboardAddr(_addr: address) -> bool: view

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

# wallet backpack contracts
kernel: public(address)
sentinel: public(address)
highCommand: public(address)
paymaster: public(address)
chequeBook: public(address)
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

# cheques
cheques: public(HashMap[address, wcs.Cheque]) # addr -> cheque
chequeSettings: public(wcs.ChequeSettings)
chequePeriodData: public(wcs.ChequeData)
numActiveCheques: public(uint256)

# global config
globalManagerSettings: public(wcs.GlobalManagerSettings)
globalPayeeSettings: public(wcs.GlobalPayeeSettings)

# config
timeLock: public(uint256)
isFrozen: public(bool)
inEjectMode: public(bool)
groupId: public(uint256)
startingAgent: public(address)
didSetWallet: public(bool)

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
    # trial funds
    _trialFundsAsset: address,
    _trialFundsAmount: uint256,
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
    _wethAddr: address,
    _ethAddr: address,
    # timelock
    _minTimeLock: uint256,
    _maxTimeLock: uint256,
):
    # initialize ownership
    ownership.__init__(_undyHq, _owner, _minTimeLock, _maxTimeLock)
    UNDY_HQ = _undyHq

    # wallet backpack addrs
    assert empty(address) not in [_kernel, _sentinel, _highCommand, _paymaster, _chequeBook, _migrator, _wethAddr, _ethAddr] # dev: invalid addrs
    self.kernel = _kernel
    self.sentinel = _sentinel
    self.highCommand = _highCommand
    self.paymaster = _paymaster
    self.chequeBook = _chequeBook
    self.migrator = _migrator

    # eth addrs
    WETH = _wethAddr
    ETH = _ethAddr

    # not using 0 index
    self.numManagers = 1
    self.numPayees = 1
    self.numWhitelisted = 1

    # trial funds / group id
    self.groupId = _groupId
    self.trialFundsAsset = _trialFundsAsset
    self.trialFundsAmount = _trialFundsAmount

    # timelock
    assert _minTimeLock != 0 and _minTimeLock < _maxTimeLock # dev: invalid delay
    MIN_TIMELOCK = _minTimeLock
    MAX_TIMELOCK = _maxTimeLock
    self.timeLock = _minTimeLock

    # manager / payee settings
    self.globalManagerSettings = _globalManagerSettings
    self.globalPayeeSettings = _globalPayeeSettings
    self.chequeSettings = _chequeSettings

    # initial agent
    if _startingAgent != empty(address):
        self.managerSettings[_startingAgent] = _starterAgentSettings
        self.startingAgent = _startingAgent
        self._registerManager(_startingAgent)


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
    legoId: uint256 = 0
    if len(_legoIds) != 0:
        legoId = _legoIds[0]

    # main data for this transaction
    ad: ws.ActionData = self._getActionDataBundle(legoId, _signer)

    # make sure signer is not locked
    assert not staticcall MissionControl(ad.missionControl).isLockedSigner(_signer) # dev: signer is locked

    # if _transferRecipient is whitelisted, set to 0x0, will not check `allowedPayees` for manager
    recipient: address = _transferRecipient
    if _transferRecipient != empty(address) and self.indexOfWhitelist[_transferRecipient] != 0:
        recipient = empty(address)

    # main validation
    hasPermission: bool = staticcall Sentinel(self.sentinel).canSignerPerformActionWithConfig(
        _signer == ad.walletOwner,
        self.indexOfManager[_signer] != 0,
        self.managerPeriodData[_signer],
        self.managerSettings[_signer],
        self.globalManagerSettings,
        _action,
        _assets,
        _legoIds,
        recipient,
    )

    # IMPORTANT -- checks if the signer is allowed to perform the action
    assert hasPermission # dev: no permission

    return ad


# post action (usd value limits)


@external
def checkManagerUsdLimitsAndUpdateData(_manager: address, _txUsdValue: uint256) -> bool:
    assert msg.sender == self.wallet # dev: no perms

    # required data / config
    config: wcs.ManagerSettings = self.managerSettings[_manager]
    globalConfig: wcs.GlobalManagerSettings = self.globalManagerSettings
    managerData: wcs.ManagerData = self.managerPeriodData[_manager]

    # check usd value limits
    canFinishTx: bool = False
    canFinishTx, managerData = staticcall Sentinel(self.sentinel).checkManagerUsdLimitsAndUpdateData(
        _txUsdValue,
        config.limits,
        globalConfig.limits,
        globalConfig.managerPeriod,
        managerData,
    )

    # IMPORTANT -- this checks manager limits (usd values)
    assert canFinishTx # dev: usd value limit exceeded

    self.managerPeriodData[_manager] = managerData
    return True


####################
# Payee Validation #
####################


@external
def checkRecipientLimitsAndUpdateData(
    _recipient: address,
    _txUsdValue: uint256,
    _asset: address,
    _amount: uint256,
) -> bool:
    assert msg.sender == self.wallet # dev: no perms

    # whitelisted
    isWhitelisted: bool = self.indexOfWhitelist[_recipient] != 0

    # only get the extra data if the recipient is not whitelisted
    isOwner: bool = False
    isPayee: bool = False
    config: wcs.PayeeSettings = empty(wcs.PayeeSettings)
    globalConfig: wcs.GlobalPayeeSettings = empty(wcs.GlobalPayeeSettings)
    data: wcs.PayeeData = empty(wcs.PayeeData)
    if not isWhitelisted:
        isOwner = _recipient == ownership.owner
        isPayee = self.indexOfPayee[_recipient] != 0
        config = self.payeeSettings[_recipient]
        globalConfig = self.globalPayeeSettings
        data = self.payeePeriodData[_recipient]

    # check if payee is valid
    canPayRecipient: bool = False
    canPayRecipient, data = staticcall Sentinel(self.sentinel).isValidPayeeAndGetData(
        isWhitelisted,
        isOwner,
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
    if data.lastTxBlock != 0:
        self.payeePeriodData[_recipient] = data
    
    return True


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
) -> bool:
    assert msg.sender == self.wallet # dev: no perms

    # get required config / data
    cheque: wcs.Cheque = self.cheques[_recipient]
    globalConfig: wcs.ChequeSettings = self.chequeSettings
    data: wcs.ChequeData = self.chequePeriodData

    isManager: bool = False
    if _signer != ownership.owner:
        isManager = self.indexOfManager[_signer] != 0

    # cheque validation
    isValidCheque: bool = False
    isValidCheque, data = staticcall Sentinel(self.sentinel).isValidChequeAndGetData(
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
    if data.lastChequePaidBlock != 0:
        self.chequePeriodData = data
        self.numActiveCheques -= 1
    
    return True


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
    assert self.pendingWhitelist[_addr].confirmBlock >= block.number # dev: time delay not reached
    self.pendingWhitelist[_addr] = empty(wcs.PendingWhitelist)
    self._registerWhitelistAddr(_addr)


# add via migrator


@external
def addWhitelistAddrViaMigrator(_addr: address):
    assert msg.sender == self.migrator # dev: no perms
    self._registerWhitelistAddr(_addr)


# register whitelist


@internal
def _registerWhitelistAddr(_addr: address):
    if self.indexOfWhitelist[_addr] != 0:
        return
    wid: uint256 = self.numWhitelisted
    self.whitelistAddr[wid] = _addr
    self.indexOfWhitelist[_addr] = wid
    self.numWhitelisted = wid + 1


# remove whitelist


@external
def removeWhitelistAddr(_addr: address):
    assert msg.sender == self.kernel # dev: no perms

    numWhitelisted: uint256 = self.numWhitelisted
    if numWhitelisted == 1:
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


####################
# Manager Settings #
####################


# add manager


@external
def addManager(_manager: address, _config: wcs.ManagerSettings):
    assert msg.sender in [self.highCommand, self.migrator] # dev: no perms
    self.managerSettings[_manager] = _config
    self._registerManager(_manager)


# update manager


@external
def updateManager(_manager: address, _config: wcs.ManagerSettings):
    assert msg.sender == self.highCommand # dev: no perms
    self.managerSettings[_manager] = _config


# register manager


@internal
def _registerManager(_manager: address):
    if self.indexOfManager[_manager] != 0:
        return
    mid: uint256 = self.numManagers
    self.managers[mid] = _manager
    self.indexOfManager[_manager] = mid
    self.numManagers = mid + 1


# remove manager


@external
def removeManager(_manager: address):
    assert msg.sender == self.highCommand # dev: no perms

    numManagers: uint256 = self.numManagers
    if numManagers == 1:
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


# global manager settings


@external
def setGlobalManagerSettings(_config: wcs.GlobalManagerSettings):
    assert msg.sender in [self.highCommand, self.migrator] # dev: no perms
    self.globalManagerSettings = _config


##################
# Payee Settings #
##################


# add payee


@external
def addPayee(_payee: address, _config: wcs.PayeeSettings):
    assert msg.sender in [self.paymaster, self.migrator] # dev: no perms
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
    if self.indexOfPayee[_payee] != 0:
        return
    pid: uint256 = self.numPayees
    self.payees[pid] = _payee
    self.indexOfPayee[_payee] = pid
    self.numPayees = pid + 1


# remove payee


@external
def removePayee(_payee: address):
    assert msg.sender == self.paymaster # dev: no perms

    numPayees: uint256 = self.numPayees
    if numPayees == 1:
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


# global payee settings


@external
def setGlobalPayeeSettings(_config: wcs.GlobalPayeeSettings):
    assert msg.sender in [self.paymaster, self.migrator] # dev: no perms
    self.globalPayeeSettings = _config


# pending payees (when managers add payees)


@external
def addPendingPayee(_payee: address, _pending: wcs.PendingPayee):
    assert msg.sender == self.paymaster # dev: no perms
    self.pendingPayees[_payee] = _pending


@external
def confirmPendingPayee(_payee: address):
    assert msg.sender == self.paymaster # dev: no perms
    pending: wcs.PendingPayee = self.pendingPayees[_payee]
    assert pending.confirmBlock != 0 and pending.confirmBlock >= block.number # dev: time delay not reached
    self.payeeSettings[_payee] = pending.settings
    self.pendingPayees[_payee] = empty(wcs.PendingPayee)
    self._registerPayee(_payee)


@external
def cancelPendingPayee(_payee: address):
    assert msg.sender == self.paymaster # dev: no perms
    self.pendingPayees[_payee] = empty(wcs.PendingPayee)


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
    ad: ws.ActionData = self._getActionDataBundle(_legoId, msg.sender)
    if not self._isSwitchboardAddr(msg.sender):
        assert self._canPerformSecurityAction(msg.sender) # dev: no perms
    newTotalUsdValue: uint256 = extcall UserWallet(ad.wallet).updateAssetData(_legoId, _asset, _shouldCheckYield, ad.lastTotalUsdValue, ad)
    extcall LootDistributor(ad.lootDistributor).updateDepositPointsWithNewValue(ad.wallet, newTotalUsdValue)
    return newTotalUsdValue


@external
def updateAllAssetData(_shouldCheckYield: bool) -> uint256:
    ad: ws.ActionData = self._getActionDataBundle(0, msg.sender)
    if not self._isSwitchboardAddr(msg.sender):
        assert self._canPerformSecurityAction(msg.sender) # dev: no perms

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


@external
def removeTrialFunds() -> uint256:
    hatchery: address = staticcall Registry(UNDY_HQ).getAddr(HATCHERY_ID)
    assert msg.sender == hatchery # dev: no perms

    # trial funds info
    trialFundsAmount: uint256 = self.trialFundsAmount
    trialFundsAsset: address = self.trialFundsAsset
    assert trialFundsAsset != empty(address) and trialFundsAmount != 0 # dev: no trial funds

    # transfer assets
    amount: uint256 = 0
    na: uint256 = 0
    amount, na = extcall UserWallet(self.wallet).transferFunds(hatchery, trialFundsAsset, trialFundsAmount, False, True)

    # update trial funds info
    remainingAmount: uint256 = trialFundsAmount - min(trialFundsAmount, amount)
    self.trialFundsAmount = remainingAmount
    if remainingAmount == 0:
        self.trialFundsAsset = empty(address)

    return amount


@view
@external
def getTrialFundsInfo() -> (address, uint256):
    return self.trialFundsAsset, self.trialFundsAmount


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
    assert staticcall Registry(UNDY_HQ).isValidAddr(msg.sender) # dev: no perms

    # withdraw from yield position
    na: uint256 = 0
    underlyingAsset: address = empty(address)
    underlyingAmount: uint256 = 0
    txUsdValue: uint256 = 0
    na, underlyingAsset, underlyingAmount, txUsdValue = extcall UserWallet(self.wallet).withdrawFromYield(_legoId, _vaultToken, _vaultAmount, empty(bytes32), True)
    assert underlyingAsset == _targetAsset # dev: invalid target asset

    return underlyingAmount, txUsdValue


# deregister asset


@external
def deregisterAsset(_asset: address) -> bool:
    if msg.sender != self.migrator:
        assert staticcall Registry(UNDY_HQ).isValidAddr(msg.sender) # dev: no perms
    return extcall UserWallet(self.wallet).deregisterAsset(_asset)


# recover nft


@external
def recoverNft(_collection: address, _nftTokenId: uint256, _recipient: address):
    if msg.sender != ownership.owner:
        assert self._isSwitchboardAddr(msg.sender) # dev: no perms

    assert _recipient != empty(address) # dev: invalid recipient
    wallet: address = self.wallet
    assert staticcall IERC721(_collection).ownerOf(_nftTokenId) == wallet # dev: not owner
    extcall UserWallet(wallet).recoverNft(_collection, _nftTokenId, _recipient)
    log NftRecovered(collection = _collection, nftTokenId = _nftTokenId, recipient = _recipient)


# freeze wallet


@external
def setFrozen(_isFrozen: bool):
    if msg.sender != ownership.owner:
        assert self._canPerformSecurityAction(msg.sender) # dev: no perms
    assert _isFrozen != self.isFrozen # dev: nothing to change
    self.isFrozen = _isFrozen
    log FrozenSet(isFrozen=_isFrozen, caller=msg.sender)


# ejection mode


@external
def setEjectionMode(_shouldEject: bool):
    # NOTE: this needs to be triggered from Switchboard, as it has other side effects / reactions
    assert self._isSwitchboardAddr(msg.sender) # dev: no perms
    assert self.trialFundsAmount == 0 # dev: has trial funds

    assert _shouldEject != self.inEjectMode # dev: nothing to change
    self.inEjectMode = _shouldEject
    log EjectionModeSet(inEjectMode = _shouldEject)


# lego access


@external
def setLegoAccessForAction(_legoId: uint256, _action: ws.ActionType) -> bool:
    ad: ws.ActionData = self._getActionDataBundle(_legoId, msg.sender)
    if msg.sender != ad.walletOwner:
        assert staticcall Registry(UNDY_HQ).isValidAddr(msg.sender) # dev: no perms
    return extcall UserWallet(ad.wallet).setLegoAccessForAction(ad.legoAddr, _action)


# is signer switchboard



@view
@internal
def _isSwitchboardAddr(_signer: address) -> bool:
    switchboard: address = staticcall Registry(UNDY_HQ).getAddr(SWITCHBOARD_ID)
    if switchboard == empty(address):
        return False
    return staticcall Switchboard(switchboard).isSwitchboardAddr(_signer)


# can perform security action


@view
@internal
def _canPerformSecurityAction(_addr: address) -> bool:
    missionControl: address = staticcall Registry(UNDY_HQ).getAddr(MISSION_CONTROL_ID)
    if missionControl == empty(address):
        return False
    return staticcall MissionControl(missionControl).canPerformSecurityAction(_addr)


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
    self.migrator = _migrator


# validation


@view
@internal
def _canSetBackpackItem(_newBackpackAddr: address, _caller: address) -> bool:
    if _caller != ownership.owner:
        return False
    ledger: address = staticcall Registry(UNDY_HQ).getAddr(LEDGER_ID)
    if ledger == empty(address):
        return False
    return staticcall Ledger(ledger).isRegisteredBackpackItem(_newBackpackAddr)


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
    owner: address = ownership.owner
    hq: address = UNDY_HQ

    # lego details
    legoBook: address = staticcall Registry(hq).getAddr(LEGO_BOOK_ID)
    legoAddr: address = empty(address)
    if _legoId != 0 and legoBook != empty(address):
        legoAddr = staticcall Registry(legoBook).getAddr(_legoId)

    ledger: address = staticcall Registry(hq).getAddr(LEDGER_ID)
    return ws.ActionData(
        ledger = ledger,
        missionControl = staticcall Registry(hq).getAddr(MISSION_CONTROL_ID),
        legoBook = legoBook,
        hatchery = staticcall Registry(hq).getAddr(HATCHERY_ID),
        lootDistributor = staticcall Registry(hq).getAddr(LOOT_DISTRIBUTOR_ID),
        appraiser = staticcall Registry(hq).getAddr(APPRAISER_ID),
        wallet = wallet,
        walletConfig = self,
        walletOwner = owner,
        inEjectMode = self.inEjectMode,
        isFrozen = self.isFrozen,
        lastTotalUsdValue = staticcall Ledger(ledger).getLastTotalUsdValue(wallet),
        signer = _signer,
        isManager = _signer != owner,
        legoId = _legoId,
        legoAddr = legoAddr,
        eth = ETH,
        weth = WETH,
    )
