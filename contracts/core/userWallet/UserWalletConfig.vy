# @version 0.4.3
# pragma optimize codesize

from interfaces import Wallet as wi
from ethereum.ercs import IERC20
from ethereum.ercs import IERC721

interface UserWalletConfig:
    def indexOfManager(_manager: address) -> uint256: view
    def hasPendingOwnerChange() -> bool: view
    def startingAgent() -> address: view
    def numManagers() -> uint256: view
    def groupId() -> uint256: view
    def owner() -> address: view

interface Sentinel:
    def canSignerPerformActionWithConfig(_isOwner: bool, _isManager: bool, _data: ManagerData, _config: ManagerSettings, _globalConfig: GlobalManagerSettings, _userWalletConfig: address, _action: wi.ActionType, _assets: DynArray[address, MAX_ASSETS] = [], _legoIds: DynArray[uint256, MAX_LEGOS] = [], _transferRecipient: address = empty(address)) -> bool: view
    def isValidPayeeWithConfig(_isWhitelisted: bool, _isOwner: bool, _isPayee: bool, _asset: address, _amount: uint256, _txUsdValue: uint256, _config: PayeeSettings, _globalConfig: GlobalPayeeSettings, _data: PayeeData) -> (bool, PayeeData): view
    def canSignerPerformAction(_user: address, _signer: address, _action: wi.ActionType, _assets: DynArray[address, MAX_ASSETS] = [], _legoIds: DynArray[uint256, MAX_LEGOS] = [], _transferRecipient: address = empty(address)) -> bool: view
    def checkManagerUsdLimitsAndUpdateData(_txUsdValue: uint256, _specificLimits: ManagerLimits, _globalLimits: ManagerLimits, _managerPeriod: uint256, _data: ManagerData) -> ManagerData: view
    def canManageWhitelist(_signer: address, _isOwner: bool, _isManager: bool, _action: WhitelistAction, _config: WhitelistPerms, _globalConfig: WhitelistPerms) -> bool: view

interface UserWallet:
    def transferFundsTrusted(_recipient: address, _asset: address = empty(address), _amount: uint256 = max_value(uint256), _ad: ActionData = empty(ActionData)) -> (uint256, uint256): nonpayable
    def preparePayment(_legoId: uint256, _vaultToken: address, _amount: uint256 = max_value(uint256), _ad: ActionData = empty(ActionData)) -> (uint256, address, uint256, uint256): nonpayable
    def recoverNft(_collection: address, _nftTokenId: uint256, _recipient: address) -> bool: nonpayable
    def assets(_index: uint256) -> address: view
    def trialFundsAmount() -> uint256: view
    def walletConfig() -> address: view
    def numAssets() -> uint256: view

interface Registry:
    def isValidRegId(_regId: uint256) -> bool: view
    def getAddr(_regId: uint256) -> address: view

interface Backpack:
    def getBackpackData(_user: address) -> BackpackData: view

interface Ledger:
    def isUserWallet(_user: address) -> bool: view

flag WhitelistAction:
    ADD_WHITELIST
    CONFIRM_WHITELIST
    CANCEL_WHITELIST
    REMOVE_WHITELIST

struct ActionData:
    missionControl: address
    legoBook: address
    backpack: address
    appraiser: address
    sentinel: address
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

struct PendingGlobalPayeeSettings:
    config: GlobalPayeeSettings
    initiatedBlock: uint256
    confirmBlock: uint256

struct PendingWhitelist:
    initiatedBlock: uint256
    confirmBlock: uint256

struct PendingGlobalManagerSettings:
    config: GlobalManagerSettings
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
    canAddPendingWhitelist: bool
    canConfirmWhitelist: bool
    canCancelWhitelist: bool
    canRemoveWhitelist: bool
    canTransfer: bool
    canCreateCheque: bool
    canAddPendingPayee: bool
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
    canAddPendingWhitelist: bool
    canConfirmWhitelist: bool
    canCancelWhitelist: bool
    canRemoveWhitelist: bool
    canTransfer: bool
    canCreateCheque: bool
    canAddPendingPayee: bool
    numAllowedRecipients: uint256
    numAllowedAssets: uint256

event ManagerRemoved:
    manager: indexed(address)

event ManagerActivationLengthAdjusted:
    manager: indexed(address)
    activationLength: uint256
    didRestart: bool

event WhitelistAddrPending:
    addr: indexed(address)
    confirmBlock: uint256
    addedBy: indexed(address)

event WhitelistAddrConfirmed:
    addr: indexed(address)
    initiatedBlock: uint256
    confirmBlock: uint256
    confirmedBy: indexed(address)

event WhitelistAddrCancelled:
    addr: indexed(address)
    initiatedBlock: uint256
    confirmBlock: uint256
    cancelledBy: indexed(address)

event WhitelistAddrRemoved:
    addr: indexed(address)
    removedBy: indexed(address)

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

# global manager config
globalManagerSettings: public(GlobalManagerSettings)
pendingGlobalManagerSettings: public(PendingGlobalManagerSettings)

# payees
payeeSettings: public(HashMap[address, PayeeSettings])
payeePeriodData: public(HashMap[address, PayeeData])

# payees (iterable)
payees: public(HashMap[uint256, address]) # index -> payee
indexOfPayee: public(HashMap[address, uint256]) # payee -> index
numPayees: public(uint256) # num payees

# global payee config
globalPayeeSettings: public(GlobalPayeeSettings)
pendingGlobalPayeeSettings: public(PendingGlobalPayeeSettings)

# whitelist
whitelistAddr: public(HashMap[uint256, address]) # index -> whitelist
indexOfWhitelist: public(HashMap[address, uint256]) # whitelist -> index
numWhitelisted: public(uint256) # num whitelisted
pendingWhitelist: public(HashMap[address, PendingWhitelist]) # addr -> pending whitelist

# config
isFrozen: public(bool)
inEjectMode: public(bool)
timeLock: public(uint256)
didSetWallet: public(bool)
sentinel: public(address)

# other
ejectModeFeeDetails: public(EjectModeFeeDetails)
startingAgent: public(address)

# trial funds info
trialFundsAsset: public(address)
trialFundsAmount: public(uint256)

API_VERSION: constant(String[28]) = "0.1.0"

MAX_CONFIG_ASSETS: constant(uint256) = 40
MAX_CONFIG_LEGOS: constant(uint256) = 25
MAX_ALLOWED_PAYEES: constant(uint256) = 40
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
BACKPACK_ID: constant(uint256) = 7

UNDY_HQ: public(immutable(address))
MIN_TIMELOCK: public(immutable(uint256))
MAX_TIMELOCK: public(immutable(uint256))
MIN_MANAGER_PERIOD: public(immutable(uint256))
MAX_MANAGER_PERIOD: public(immutable(uint256))

WETH: public(immutable(address))
ETH: public(immutable(address))


@deploy
def __init__(
    _undyHq: address,
    _owner: address,
    _sentinel: address,
    _startingAgent: address,
    _startingAgentActivationLength: uint256,
    _managerPeriod: uint256,
    _defaultStartDelay: uint256,
    _defaultActivationLength: uint256,
    _groupId: uint256,
    _trialFundsAsset: address,
    _trialFundsAmount: uint256,
    _minManagerPeriod: uint256,
    _maxManagerPeriod: uint256,
    _minTimeLock: uint256,
    _maxTimeLock: uint256,
    _wethAddr: address,
    _ethAddr: address,
):
    assert empty(address) not in [_undyHq, _owner, _sentinel, _wethAddr, _ethAddr] # dev: invalid addrs
    UNDY_HQ = _undyHq
    WETH = _wethAddr
    ETH = _ethAddr

    self.owner = _owner
    self.groupId = _groupId
    self.sentinel = _sentinel

    # trial funds info
    if _trialFundsAsset != empty(address) and _trialFundsAmount != 0:   
        self.trialFundsAsset = _trialFundsAsset
        self.trialFundsAmount = _trialFundsAmount

    # manager periods (set this first)
    assert _minManagerPeriod != 0 and _minManagerPeriod < _maxManagerPeriod # dev: invalid manager periods
    MIN_MANAGER_PERIOD = _minManagerPeriod
    MAX_MANAGER_PERIOD = _maxManagerPeriod

    # # global manager settings
    config: GlobalManagerSettings = empty(GlobalManagerSettings)
    # assert self._isValidManagerPeriod(_managerPeriod) # dev: invalid manager period
    # assert self._isValidStartDelay(_defaultStartDelay) # dev: invalid start delay
    # assert self._isValidActivationLength(_defaultActivationLength) # dev: invalid activation length
    config.managerPeriod = _managerPeriod
    config.startDelay = _defaultStartDelay
    config.activationLength = _defaultActivationLength
    config.canOwnerManage = True
    config.legoPerms, config.whitelistPerms, config.transferPerms = self._createHappyDefaults()
    self.globalManagerSettings = config

    # initialize global payee settings with defaults
    self.globalPayeeSettings = GlobalPayeeSettings(
        defaultPeriodLength = ONE_DAY_IN_BLOCKS,
        timeLockOnModify = ONE_DAY_IN_BLOCKS,
        activationLength = ONE_YEAR_IN_BLOCKS,
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

    # initial manager
    if _startingAgent != empty(address):
        # assert self._isValidActivationLength(_startingAgentActivationLength) # dev: invalid activation length
        self.managerSettings[_startingAgent] = ManagerSettings(
            startBlock = block.number,
            expiryBlock = block.number + _startingAgentActivationLength,
            limits = empty(ManagerLimits), # no limits
            legoPerms = config.legoPerms, # all set to True
            whitelistPerms = config.whitelistPerms, # can cancel, can confirm
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


##################
# Access Control #
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
    assert staticcall Sentinel(ad.sentinel).canSignerPerformActionWithConfig(c.isOwner, c.isManager, c.data, c.config, c.globalConfig, self, _action, _assets, _legoIds, _transferRecipient) # dev: no permission

    # signer is not owner
    if not c.isOwner:
        ad.isManager = True

    return ad


# post action (usd value limits)


@external
def checkManagerUsdLimitsAndUpdateData(_manager: address, _txUsdValue: uint256, _sentinel: address) -> bool:
    assert msg.sender == self.wallet # dev: no perms

    config: ManagerSettings = self.managerSettings[_manager]
    globalConfig: GlobalManagerSettings = self.globalManagerSettings
    data: ManagerData = staticcall Sentinel(_sentinel).checkManagerUsdLimitsAndUpdateData(_txUsdValue, config.limits, globalConfig.limits, globalConfig.managerPeriod, self.managerPeriodData[_manager])
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
    _sentinel: address,
) -> bool:
    assert msg.sender == self.wallet # dev: no perms

    c: RecipientConfigBundle = self._getRecipientConfigs(_recipient)

    # check if payee is valid
    canPayRecipient: bool = False
    data: PayeeData = empty(PayeeData)
    canPayRecipient, data = staticcall Sentinel(_sentinel).isValidPayeeWithConfig(c.isWhitelisted, c.isOwner, c.isPayee, _asset, _amount, _txUsdValue, c.config, c.globalConfig, c.data)

    # !!!!
    assert canPayRecipient # dev: invalid payee

    # only save if data was updated  
    if data.lastTxBlock != 0:
        self.payeePeriodData[_recipient] = data
    
    return True


###########################
# Global Manager Settings #
###########################


# # set pending global manager settings


# @external
# def setPendingGlobalManagerSettings(
#     _managerPeriod: uint256,
#     _startDelay: uint256,
#     _activationLength: uint256,
#     _limits: ManagerLimits,
#     _legoPerms: LegoPerms,
#     _whitelistPerms: WhitelistPerms,
#     _transferPerms: TransferPerms,
#     _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
# ) -> bool:
#     assert msg.sender == self.owner # dev: no perms

#     # validation
#     assert self._isValidManagerPeriod(_managerPeriod) # dev: invalid manager period
#     assert self._isValidStartDelay(_startDelay) # dev: invalid start delay
#     assert self._isValidActivationLength(_activationLength) # dev: invalid activation length
#     assert self._isValidLimits(_limits) # dev: invalid limits
#     assert self._isValidLegoPerms(_legoPerms) # dev: invalid lego perms
#     assert self._isValidTransferPerms(_transferPerms) # dev: invalid transfer perms
#     assert self._isValidAllowedAssets(_allowedAssets) # dev: invalid allowed assets

#     config: GlobalManagerSettings = GlobalManagerSettings(
#         managerPeriod = _managerPeriod,
#         startDelay = _startDelay,
#         activationLength = _activationLength,
#         limits = _limits,
#         legoPerms = _legoPerms,
#         whitelistPerms = _whitelistPerms,
#         transferPerms = _transferPerms,
#         allowedAssets = _allowedAssets,
#     )

#     # put in pending state
#     self.pendingGlobalManagerSettings = PendingGlobalManagerSettings(
#         config = config,
#         initiatedBlock = block.number,
#         confirmBlock = block.number + self.timeLock,
#     )

#     log GlobalManagerSettingsModified(
#         state = "PENDING",
#         managerPeriod = _managerPeriod,
#         startDelay = _startDelay,
#         activationLength = _activationLength,
#         maxVolumePerTx = _limits.maxVolumePerTx,
#         maxVolumePerPeriod = _limits.maxVolumePerPeriod,
#         maxNumTxsPerPeriod = _limits.maxNumTxsPerPeriod,
#         txCooldownBlocks = _limits.txCooldownBlocks,
#         canManageYield = _legoPerms.canManageYield,
#         canBuyAndSell = _legoPerms.canBuyAndSell,
#         canManageDebt = _legoPerms.canManageDebt,
#         canManageLiq = _legoPerms.canManageLiq,
#         canClaimRewards = _legoPerms.canClaimRewards,
#         numAllowedLegos = len(_legoPerms.allowedLegos),
#         canAddPendingWhitelist = _whitelistPerms.canAddPending,
#         canConfirmWhitelist = _whitelistPerms.canConfirm,
#         canCancelWhitelist = _whitelistPerms.canCancel,
#         canRemoveWhitelist = _whitelistPerms.canRemove,
#         canTransfer = _transferPerms.canTransfer,
#         canCreateCheque = _transferPerms.canCreateCheque,
#         canAddPendingPayee = _transferPerms.canAddPendingPayee,
#         numAllowedRecipients = len(_transferPerms.allowedPayees),
#         numAllowedAssets = len(_allowedAssets),
#     )
#     return True


# # confirm global manager settings


# @external
# def confirmPendingGlobalManagerSettings() -> bool:
#     assert msg.sender == self.owner # dev: no perms

#     data: PendingGlobalManagerSettings = self.pendingGlobalManagerSettings
#     assert data.confirmBlock != 0 and block.number >= data.confirmBlock # dev: time delay not reached
#     self.globalManagerSettings = data.config
#     self.pendingGlobalManagerSettings = empty(PendingGlobalManagerSettings)

#     log GlobalManagerSettingsModified(
#         state = "CONFIRMED",
#         managerPeriod = data.config.managerPeriod,
#         startDelay = data.config.startDelay,
#         activationLength = data.config.activationLength,
#         maxVolumePerTx = data.config.limits.maxVolumePerTx,
#         maxVolumePerPeriod = data.config.limits.maxVolumePerPeriod,
#         maxNumTxsPerPeriod = data.config.limits.maxNumTxsPerPeriod,
#         txCooldownBlocks = data.config.limits.txCooldownBlocks,
#         canManageYield = data.config.legoPerms.canManageYield,
#         canBuyAndSell = data.config.legoPerms.canBuyAndSell,
#         canManageDebt = data.config.legoPerms.canManageDebt,
#         canManageLiq = data.config.legoPerms.canManageLiq,
#         canClaimRewards = data.config.legoPerms.canClaimRewards,
#         numAllowedLegos = len(data.config.legoPerms.allowedLegos),
#         canAddPendingWhitelist = data.config.whitelistPerms.canAddPending,
#         canConfirmWhitelist = data.config.whitelistPerms.canConfirm,
#         canCancelWhitelist = data.config.whitelistPerms.canCancel,
#         canRemoveWhitelist = data.config.whitelistPerms.canRemove,
#         canTransfer = data.config.transferPerms.canTransfer,
#         canCreateCheque = data.config.transferPerms.canCreateCheque,
#         canAddPendingPayee = data.config.transferPerms.canAddPendingPayee,
#         numAllowedRecipients = len(data.config.transferPerms.allowedPayees),
#         numAllowedAssets = len(data.config.allowedAssets),
#     )
#     return True


# # cancel global manager settings


# @external
# def cancelPendingGlobalManagerSettings() -> bool:
#     assert msg.sender == self.owner # dev: no perms

#     data: PendingGlobalManagerSettings = self.pendingGlobalManagerSettings
#     assert data.confirmBlock != 0 # dev: no pending change
#     self.pendingGlobalManagerSettings = empty(PendingGlobalManagerSettings)

#     log GlobalManagerSettingsModified(
#         state = "CANCELLED",
#         managerPeriod = data.config.managerPeriod,
#         startDelay = data.config.startDelay,
#         activationLength = data.config.activationLength,
#         maxVolumePerTx = data.config.limits.maxVolumePerTx,
#         maxVolumePerPeriod = data.config.limits.maxVolumePerPeriod,
#         maxNumTxsPerPeriod = data.config.limits.maxNumTxsPerPeriod,
#         txCooldownBlocks = data.config.limits.txCooldownBlocks,
#         canManageYield = data.config.legoPerms.canManageYield,
#         canBuyAndSell = data.config.legoPerms.canBuyAndSell,
#         canManageDebt = data.config.legoPerms.canManageDebt,
#         canManageLiq = data.config.legoPerms.canManageLiq,
#         canClaimRewards = data.config.legoPerms.canClaimRewards,
#         numAllowedLegos = len(data.config.legoPerms.allowedLegos),
#         canAddPendingWhitelist = data.config.whitelistPerms.canAddPending,
#         canConfirmWhitelist = data.config.whitelistPerms.canConfirm,
#         canCancelWhitelist = data.config.whitelistPerms.canCancel,
#         canRemoveWhitelist = data.config.whitelistPerms.canRemove,
#         canTransfer = data.config.transferPerms.canTransfer,
#         canCreateCheque = data.config.transferPerms.canCreateCheque,
#         canAddPendingPayee = data.config.transferPerms.canAddPendingPayee,
#         numAllowedRecipients = len(data.config.transferPerms.allowedPayees),
#         numAllowedAssets = len(data.config.allowedAssets),
#     )
#     return True


#############################
# Specific Manager Settings #
#############################


# # set manager settings


# @external
# def setSpecificManagerSettings(
#     _manager: address,
#     _limits: ManagerLimits,
#     _legoPerms: LegoPerms,
#     _whitelistPerms: WhitelistPerms,
#     _transferPerms: TransferPerms,
#     _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
#     _startDelay: uint256 = 0,
#     _activationLength: uint256 = 0,
# ) -> bool:
#     assert msg.sender == self.owner # dev: no perms

#     # validation
#     assert _manager not in [empty(address), self.owner] # dev: invalid manager
#     assert self._isValidLimits(_limits) # dev: invalid limits
#     assert self._isValidLegoPerms(_legoPerms) # dev: invalid lego perms
#     assert self._isValidTransferPerms(_transferPerms) # dev: invalid transfer perms
#     assert self._isValidAllowedAssets(_allowedAssets) # dev: invalid allowed assets

#     config: ManagerSettings = empty(ManagerSettings)
#     stateStr: String[10] = empty(String[10])

#     # existing manager
#     alreadyRegistered: bool = self.indexOfManager[_manager] != 0
#     if alreadyRegistered:
#         config = self.managerSettings[_manager]
#         config.limits = _limits
#         config.legoPerms = _legoPerms
#         config.whitelistPerms = _whitelistPerms
#         config.transferPerms = _transferPerms
#         config.allowedAssets = _allowedAssets
#         stateStr = "UPDATED"
    
#     # new manager
#     else:
#         config = ManagerSettings(
#             startBlock = 0,
#             expiryBlock = 0,
#             limits = _limits,
#             legoPerms = _legoPerms,
#             whitelistPerms = _whitelistPerms,
#             transferPerms = _transferPerms,
#             allowedAssets = _allowedAssets,
#         )
#         config.startBlock, config.expiryBlock = self._getStartAndExpiryBlocksForNewManager(_startDelay, _activationLength)
#         self._registerManager(_manager)
#         stateStr = "ADDED"

#     # update config
#     self.managerSettings[_manager] = config

#     log ManagerSettingsModified(
#         manager = _manager,
#         state = stateStr,
#         startBlock = config.startBlock,
#         expiryBlock = config.expiryBlock,
#         maxVolumePerTx = config.limits.maxVolumePerTx,
#         maxVolumePerPeriod = config.limits.maxVolumePerPeriod,
#         maxNumTxsPerPeriod = config.limits.maxNumTxsPerPeriod,
#         txCooldownBlocks = config.limits.txCooldownBlocks,
#         canManageYield = config.legoPerms.canManageYield,
#         canBuyAndSell = config.legoPerms.canBuyAndSell,
#         canManageDebt = config.legoPerms.canManageDebt,
#         canManageLiq = config.legoPerms.canManageLiq,
#         canClaimRewards = config.legoPerms.canClaimRewards,
#         numAllowedLegos = len(config.legoPerms.allowedLegos),
#         canAddPendingWhitelist = config.whitelistPerms.canAddPending,
#         canConfirmWhitelist = config.whitelistPerms.canConfirm,
#         canCancelWhitelist = config.whitelistPerms.canCancel,
#         canRemoveWhitelist = config.whitelistPerms.canRemove,
#         canTransfer = config.transferPerms.canTransfer,
#         canCreateCheque = config.transferPerms.canCreateCheque,
#         canAddPendingPayee = config.transferPerms.canAddPendingPayee,
#         numAllowedRecipients = len(config.transferPerms.allowedPayees),
#         numAllowedAssets = len(config.allowedAssets),
#     )
#     return True


# # remove manager


# @external
# def removeSpecificManager(_manager: address) -> bool:
#     assert msg.sender == self.owner # dev: no perms
#     assert self.indexOfManager[_manager] != 0 # dev: manager not found

#     self.managerSettings[_manager] = empty(ManagerSettings)
#     self.managerPeriodData[_manager] = empty(ManagerData)
#     self._deregisterManager(_manager)

#     log ManagerRemoved(manager = _manager)
#     return True


# # adjust activation length


# @external
# def adjustSpecificManagerActivationLength(_manager: address, _activationLength: uint256, _shouldResetStartBlock: bool = False) -> bool:
#     assert msg.sender == self.owner # dev: no perms

#     # validation
#     assert self.indexOfManager[_manager] != 0 # dev: manager not found
#     config: ManagerSettings = self.managerSettings[_manager]
#     assert config.startBlock < block.number # dev: manager not active yet
#     assert self._isValidActivationLength(_activationLength) # dev: invalid activation length

#     # update config
#     didRestart: bool = False
#     if config.expiryBlock < block.number or _shouldResetStartBlock:
#         config.startBlock = block.number
#         didRestart = True
#     config.expiryBlock = config.startBlock + _activationLength
#     self.managerSettings[_manager] = config

#     log ManagerActivationLengthAdjusted(
#         manager = _manager,
#         activationLength = _activationLength,
#         didRestart = didRestart,
#     )
#     return True


##########################
# Manager Settings Utils #
##########################


@view
@external
def isManager(_manager: address) -> bool:
    return self.indexOfManager[_manager] != 0


# @view
# @internal
# def _getStartAndExpiryBlocksForNewManager(_startDelay: uint256, _activationLength: uint256) -> (uint256, uint256):
#     config: GlobalManagerSettings = self.globalManagerSettings

#     startDelay: uint256 = config.startDelay
#     if _startDelay != 0:
#         startDelay = max(startDelay, _startDelay) # using max here as extra protection
#     assert self._isValidStartDelay(startDelay) # dev: invalid start delay

#     activationLength: uint256 = config.activationLength
#     if _activationLength != 0:
#         activationLength = min(activationLength, _activationLength)
#     assert self._isValidActivationLength(activationLength) # dev: invalid activation length

#     startBlock: uint256 = block.number + startDelay
#     expiryBlock: uint256 = startBlock + activationLength
#     return startBlock, expiryBlock


# @view
# @internal
# def _isValidLimits(_limits: ManagerLimits) -> bool:
#     # Note: 0 values are treated as "unlimited" throughout this validation
    
#     # only validate if both values are non-zero (not unlimited)
#     if _limits.maxVolumePerTx != 0 and _limits.maxVolumePerPeriod != 0:
#         if _limits.maxVolumePerTx > _limits.maxVolumePerPeriod:
#             return False

#     # cooldown cannot exceed period length (unless cooldown is 0 = no cooldown)
#     if _limits.txCooldownBlocks != 0 and _limits.txCooldownBlocks > self.globalManagerSettings.managerPeriod:
#         return False

#     return True


# @view
# @internal
# def _isValidLegoPerms(_legoPerms: LegoPerms) -> bool:
#     if len(_legoPerms.allowedLegos) == 0:
#         return True

#     canDoAnything: bool = _legoPerms.canManageYield or _legoPerms.canBuyAndSell or _legoPerms.canManageDebt or _legoPerms.canManageLiq or _legoPerms.canClaimRewards

#     # _allowedLegos should be empty if there are no permissions
#     if not canDoAnything:
#         return False

#     # if in eject mode, can't add legos as permissions
#     if self.inEjectMode:
#         return False

#     legoBook: address = staticcall Registry(UNDY_HQ).getAddr(LEGO_BOOK_ID)
#     if legoBook == empty(address):
#         return False

#     checkedLegos: DynArray[uint256, MAX_CONFIG_LEGOS] = []
#     for i: uint256 in _legoPerms.allowedLegos:
#         if not staticcall Registry(legoBook).isValidRegId(i):
#             return False

#         # duplicates are not allowed
#         if i in checkedLegos:
#             return False
#         checkedLegos.append(i)

#     return True


# @view
# @internal
# def _isValidTransferPerms(_transferPerms: TransferPerms) -> bool:
#     if len(_transferPerms.allowedPayees) == 0:
#         return True

#     canDoAnything: bool = _transferPerms.canTransfer or _transferPerms.canCreateCheque or _transferPerms.canAddPendingPayee

#     # _allowedPayees should be empty if there are no permissions
#     if not canDoAnything:
#         return False

#     checkedPayees: DynArray[address, MAX_ALLOWED_PAYEES] = []
#     for i: address in _transferPerms.allowedPayees:
#         if i == empty(address):
#             return False

#         # check if payee is valid
#         if self.indexOfPayee[i] == 0:
#             return False

#         # duplicates are not allowed
#         if i in checkedPayees:
#             return False
#         checkedPayees.append(i)

#     return True


# @view
# @internal
# def _isValidAllowedAssets(_allowedAssets: DynArray[address, MAX_CONFIG_ASSETS]) -> bool:
#     if len(_allowedAssets) == 0:
#         return True

#     checkedAssets: DynArray[address, MAX_CONFIG_ASSETS] = []
#     for i: address in _allowedAssets:
#         if i == empty(address):
#             return False

#         # duplicates are not allowed
#         if i in checkedAssets:
#             return False
#         checkedAssets.append(i)

#     return True


# @view
# @internal
# def _isValidStartDelay(_startDelay: uint256) -> bool:
#     return _startDelay <= 6 * ONE_MONTH_IN_BLOCKS


# @view
# @internal
# def _isValidManagerPeriod(_managerPeriod: uint256) -> bool:
#     return _managerPeriod >= MIN_MANAGER_PERIOD and _managerPeriod <= MAX_MANAGER_PERIOD


# @view
# @internal
# def _isValidActivationLength(_numBlocks: uint256) -> bool:
#     return _numBlocks <= 5 * ONE_YEAR_IN_BLOCKS and _numBlocks >= ONE_DAY_IN_BLOCKS


@pure
@internal
def _createHappyDefaults() -> (LegoPerms, WhitelistPerms, TransferPerms):
    return LegoPerms(
        canManageYield = True,
        canBuyAndSell = True,
        canManageDebt = True,
        canManageLiq = True,
        canClaimRewards = True,
        allowedLegos = [],
    ), WhitelistPerms(
        canAddPending = False,
        canConfirm = True,
        canCancel = True,
        canRemove = False,
    ), TransferPerms(
        canTransfer = True,
        canCreateCheque = True,
        canAddPendingPayee = True,
        allowedPayees = [],
    )


# register manager


@internal
def _registerManager(_manager: address):
    mid: uint256 = self.numManagers
    if mid == 0:
        mid = 1 # not using 0 index
    self.managers[mid] = _manager
    self.indexOfManager[_manager] = mid
    self.numManagers = mid + 1


# deregister manager


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


##########
# Payees #
##########


# is payee


@view
@external
def isRegisteredPayee(_addr: address) -> bool:
    return self._isRegisteredPayee(_addr)


@view
@internal
def _isRegisteredPayee(_addr: address) -> bool:
    return self.indexOfPayee[_addr] != 0


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


@nonreentrant
@external
def addWhitelistAddr(_addr: address):
    c: ManagerConfigBundle = self._getManagerConfigs(msg.sender, self.owner)
    assert staticcall Sentinel(self.sentinel).canManageWhitelist(msg.sender, c.isOwner, c.isManager, WhitelistAction.ADD_WHITELIST, c.config.whitelistPerms, c.globalConfig.whitelistPerms) # dev: no perms

    assert _addr not in [empty(address), self, self.wallet, self.owner] # dev: invalid addr
    assert not self._isWhitelisted(_addr) # dev: already whitelisted
    assert self.pendingWhitelist[_addr].initiatedBlock == 0 # dev: pending whitelist already exists

    # this uses same delay as ownership change
    confirmBlock: uint256 = block.number + self.timeLock
    self.pendingWhitelist[_addr] = PendingWhitelist(
        initiatedBlock = block.number,
        confirmBlock = confirmBlock,
    )
    log WhitelistAddrPending(addr=_addr, confirmBlock=confirmBlock, addedBy=msg.sender)


# confirm whitelist


@nonreentrant
@external
def confirmWhitelistAddr(_addr: address):
    c: ManagerConfigBundle = self._getManagerConfigs(msg.sender, self.owner)
    assert staticcall Sentinel(self.sentinel).canManageWhitelist(msg.sender, c.isOwner, c.isManager, WhitelistAction.CONFIRM_WHITELIST, c.config.whitelistPerms, c.globalConfig.whitelistPerms) # dev: no perms

    data: PendingWhitelist = self.pendingWhitelist[_addr]
    assert data.initiatedBlock != 0 # dev: no pending whitelist
    assert data.confirmBlock != 0 and block.number >= data.confirmBlock # dev: time delay not reached

    self._registerWhitelist(_addr)
    self.pendingWhitelist[_addr] = empty(PendingWhitelist)
    log WhitelistAddrConfirmed(addr=_addr, initiatedBlock=data.initiatedBlock, confirmBlock=data.confirmBlock, confirmedBy=msg.sender)


# cancel pending whitelist


@nonreentrant
@external
def cancelPendingWhitelistAddr(_addr: address):
    if not self._isSignerBackpack(msg.sender, self.inEjectMode):
        c: ManagerConfigBundle = self._getManagerConfigs(msg.sender, self.owner)
        assert staticcall Sentinel(self.sentinel).canManageWhitelist(msg.sender, c.isOwner, c.isManager, WhitelistAction.CANCEL_WHITELIST, c.config.whitelistPerms, c.globalConfig.whitelistPerms) # dev: no perms

    data: PendingWhitelist = self.pendingWhitelist[_addr]
    assert data.initiatedBlock != 0 # dev: no pending whitelist
    self.pendingWhitelist[_addr] = empty(PendingWhitelist)
    log WhitelistAddrCancelled(addr=_addr, initiatedBlock=data.initiatedBlock, confirmBlock=data.confirmBlock, cancelledBy=msg.sender)


# remove whitelist


@nonreentrant
@external
def removeWhitelistAddr(_addr: address):
    c: ManagerConfigBundle = self._getManagerConfigs(msg.sender, self.owner)
    assert staticcall Sentinel(self.sentinel).canManageWhitelist(msg.sender, c.isOwner, c.isManager, WhitelistAction.REMOVE_WHITELIST, c.config.whitelistPerms, c.globalConfig.whitelistPerms) # dev: no perms

    assert self._isWhitelisted(_addr) # dev: not whitelisted
    self._deregisterWhitelist(_addr)
    log WhitelistAddrRemoved(addr=_addr, removedBy=msg.sender)


# register whitelist


@internal
def _registerWhitelist(_addr: address):
    if self._isWhitelisted(_addr):
        return

    wid: uint256 = self.numWhitelisted
    if wid == 0:
        wid = 1 # not using 0 index
    self.whitelistAddr[wid] = _addr
    self.indexOfWhitelist[_addr] = wid
    self.numWhitelisted = wid + 1


# deregister whitelist


@internal
def _deregisterWhitelist(_addr: address) -> bool:
    numWhitelisted: uint256 = self.numWhitelisted
    if numWhitelisted == 0:
        return False

    targetIndex: uint256 = self.indexOfWhitelist[_addr]
    if targetIndex == 0:
        return False

    # update data
    lastIndex: uint256 = numWhitelisted - 1
    self.numWhitelisted = lastIndex
    self.indexOfWhitelist[_addr] = 0

    # get last item, replace the removed item
    if targetIndex != lastIndex:
        lastItem: address = self.whitelistAddr[lastIndex]
        self.whitelistAddr[targetIndex] = lastItem
        self.indexOfWhitelist[lastItem] = targetIndex

    return True


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
    if not self._isSignerBackpack(msg.sender, self.inEjectMode):
        assert msg.sender == self.owner # dev: no perms

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
    if not self._isSignerBackpack(msg.sender, self.inEjectMode):
        assert msg.sender == self.owner # dev: no perms

    self.isFrozen = _isFrozen
    log FrozenSet(isFrozen=_isFrozen, caller=msg.sender)


# ejection mode


@external
def setEjectionMode(_inEjectMode: bool, _feeDetails: EjectModeFeeDetails):
    # NOTE: this needs to be triggered from Backpack, as it has other side effects / reactions
    backpack: address = staticcall Registry(UNDY_HQ).getAddr(BACKPACK_ID)
    assert msg.sender == backpack # dev: no perms
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


#############
# Utilities #
#############


# remove trial funds


@external
def removeTrialFunds() -> uint256:
    ad: ActionData = self._getActionDataBundle(0, msg.sender)
    assert ad.signer == ad.backpack # dev: no perms

    # trial funds info
    trialFundsAmount: uint256 = self.trialFundsAmount
    trialFundsAsset: address = self.trialFundsAsset
    assert trialFundsAsset != empty(address) and trialFundsAmount != 0 # dev: no trial funds

    # recipient
    hatchery: address = staticcall Registry(UNDY_HQ).getAddr(HATCHERY_ID)
    assert hatchery != empty(address) # dev: invalid recipient

    # transfer assets
    amount: uint256 = 0
    na: uint256 = 0
    amount, na = extcall UserWallet(ad.wallet).transferFundsTrusted(hatchery, trialFundsAsset, trialFundsAmount, ad)

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
    assert ad.signer == ad.backpack # dev: no perms

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
def recoverNft(_collection: address, _nftTokenId: uint256, _recipient: address) -> bool:
    assert msg.sender == staticcall Registry(UNDY_HQ).getAddr(BACKPACK_ID) # dev: no perms
    assert _recipient != empty(address) # dev: invalid recipient
    wallet: address = self.wallet
    assert staticcall IERC721(_collection).ownerOf(_nftTokenId) == wallet # dev: not owner
    return extcall UserWallet(wallet).recoverNft(_collection, _nftTokenId, _recipient)


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
        sentinel = self.sentinel,
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


# is signer backpack


@view
@internal
def _isSignerBackpack(_signer: address, _inEjectMode: bool) -> bool:
    if _inEjectMode:
        return False
    return _signer == staticcall Registry(UNDY_HQ).getAddr(BACKPACK_ID)