# @version 0.4.3
# pragma optimize codesize

from interfaces import Wallet as wi

interface UserWalletConfig:
    def getManagerSettingsBundle(_manager: address) -> ManagerSettingsBundle: view
    def updateManager(_manager: address, _config: ManagerSettings): nonpayable
    def setGlobalManagerSettings(_config: GlobalManagerSettings): nonpayable
    def addManager(_manager: address, _config: ManagerSettings): nonpayable
    def getManagerConfigs(_signer: address) -> ManagerConfigBundle: view
    def managerSettings(_manager: address) -> ManagerSettings: view
    def globalManagerSettings() -> GlobalManagerSettings: view
    def isRegisteredPayee(_addr: address) -> bool: view
    def isWhitelisted(_addr: address) -> bool: view
    def removeManager(_manager: address): nonpayable
    def owner() -> address: view
    def numManagers() -> uint256: view
    def managers(i: uint256) -> address: view

interface Registry:
    def isValidRegId(_regId: uint256) -> bool: view
    def getAddr(_regId: uint256) -> address: view

interface Ledger:
    def isUserWallet(_user: address) -> bool: view

interface UserWallet:
    def walletConfig() -> address: view

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

event GlobalManagerSettingsModified:
    user: indexed(address)
    managerPeriod: uint256
    startDelay: uint256
    activationLength: uint256
    canOwnerManage: bool
    maxUsdValuePerTx: uint256
    maxUsdValuePerPeriod: uint256
    maxUsdValueLifetime: uint256
    maxNumTxsPerPeriod: uint256
    txCooldownBlocks: uint256
    failOnZeroPrice: bool
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
    user: indexed(address)
    manager: indexed(address)
    startBlock: uint256
    expiryBlock: uint256
    maxUsdValuePerTx: uint256
    maxUsdValuePerPeriod: uint256
    maxUsdValueLifetime: uint256
    maxNumTxsPerPeriod: uint256
    txCooldownBlocks: uint256
    failOnZeroPrice: bool
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
    user: indexed(address)
    manager: indexed(address)

event ManagerActivationLengthAdjusted:
    user: indexed(address)
    manager: indexed(address)
    activationLength: uint256
    didRestart: bool

UNDY_HQ: public(immutable(address))
LEDGER_ID: constant(uint256) = 2
BACKPACK_ID: constant(uint256) = 7

MAX_CONFIG_ASSETS: constant(uint256) = 40
MAX_CONFIG_LEGOS: constant(uint256) = 25
MAX_ALLOWED_PAYEES: constant(uint256) = 40
MAX_ASSETS: constant(uint256) = 10
MAX_LEGOS: constant(uint256) = 10

# manager validation bounds
MIN_MANAGER_PERIOD: public(immutable(uint256))
MAX_MANAGER_PERIOD: public(immutable(uint256))
MAX_START_DELAY: public(immutable(uint256))
MIN_ACTIVATION_LENGTH: public(immutable(uint256))
MAX_ACTIVATION_LENGTH: public(immutable(uint256))


@deploy
def __init__(
    _undyHq: address,
    _minManagerPeriod: uint256,
    _maxManagerPeriod: uint256,
    _minActivationLength: uint256,
    _maxActivationLength: uint256,
    _maxStartDelay: uint256,
):
    assert _undyHq != empty(address) # dev: invalid undy hq
    UNDY_HQ = _undyHq

    assert _minManagerPeriod != 0 and _minManagerPeriod < _maxManagerPeriod # dev: invalid manager periods
    MIN_MANAGER_PERIOD = _minManagerPeriod
    MAX_MANAGER_PERIOD = _maxManagerPeriod

    assert _minActivationLength != 0 and _minActivationLength < _maxActivationLength # dev: invalid activation length
    MIN_ACTIVATION_LENGTH = _minActivationLength
    MAX_ACTIVATION_LENGTH = _maxActivationLength

    MAX_START_DELAY = _maxStartDelay


######################
# Manager Validation #
######################


# manager access control


@view
@external
def canSignerPerformAction(
    _user: address,
    _signer: address,
    _action: wi.ActionType,
    _assets: DynArray[address, MAX_ASSETS] = [],
    _legoIds: DynArray[uint256, MAX_LEGOS] = [],
    _transferRecipient: address = empty(address),
) -> bool:
    userWalletConfig: address = staticcall UserWallet(_user).walletConfig()
    c: ManagerConfigBundle = staticcall UserWalletConfig(userWalletConfig).getManagerConfigs(_signer)
    return self._canSignerPerformAction(c.isOwner, c.isManager, c.data, c.config, c.globalConfig, userWalletConfig, _action, _assets, _legoIds, _transferRecipient)


# manager access control (with config)


@view
@external
def canSignerPerformActionWithConfig(
    _isOwner: bool,
    _isManager: bool,
    _data: ManagerData,
    _config: ManagerSettings,
    _globalConfig: GlobalManagerSettings,
    _userWalletConfig: address,
    _action: wi.ActionType,
    _assets: DynArray[address, MAX_ASSETS] = [],
    _legoIds: DynArray[uint256, MAX_LEGOS] = [],
    _transferRecipient: address = empty(address),
) -> bool:
    return self._canSignerPerformAction(_isOwner, _isManager, _data, _config, _globalConfig, _userWalletConfig, _action, _assets, _legoIds, _transferRecipient)


# core logic -- manager access control


@view
@internal
def _canSignerPerformAction(
    _isOwner: bool,
    _isManager: bool,
    _data: ManagerData,
    _config: ManagerSettings,
    _globalConfig: GlobalManagerSettings,
    _userWalletConfig: address,
    _action: wi.ActionType,
    _assets: DynArray[address, MAX_ASSETS],
    _legoIds: DynArray[uint256, MAX_LEGOS],
    _transferRecipient: address,
) -> bool:
    # check if signer is the owner, and if owner can manage
    if _isOwner and _globalConfig.canOwnerManage:
        return True

    # check if signer is a manager
    if not _isManager:
        return False

    # get latest manager data
    data: ManagerData = self._getLatestManagerData(_data, _globalConfig.managerPeriod)

    # check specific manager permissions
    if not self._checkSpecificManagerPermissions(_userWalletConfig, _action, _assets, _legoIds, _transferRecipient, data, _config):
        return False

    # check global manager permissions
    if not self._checkGlobalManagerPermissions(_userWalletConfig, _action, _assets, _legoIds, _transferRecipient, data, _globalConfig):
        return False

    return True


# specific manager permissions


@view
@internal
def _checkSpecificManagerPermissions(
    _userWalletConfig: address,
    _action: wi.ActionType,
    _assets: DynArray[address, MAX_ASSETS],
    _legoIds: DynArray[uint256, MAX_LEGOS],
    _transferRecipient: address,
    _data: ManagerData,
    _config: ManagerSettings,
) -> bool:

    # manager is not active
    if _config.startBlock > block.number or _config.expiryBlock < block.number:
        return False

    # check manager permissions
    if not self._checkManagerPermissions(_userWalletConfig, _action, _assets, _legoIds, _transferRecipient, _config.allowedAssets, _config.legoPerms, _config.transferPerms):
        return False

    # check manager limits
    return self._checkManagerLimits(_config.limits, _data, True, 0, False)


# global manager permissions


@view
@internal
def _checkGlobalManagerPermissions(
    _userWalletConfig: address,
    _action: wi.ActionType,
    _assets: DynArray[address, MAX_ASSETS],
    _legoIds: DynArray[uint256, MAX_LEGOS],
    _transferRecipient: address,
    _data: ManagerData,
    _config: GlobalManagerSettings,
) -> bool:

    # check manager permissions
    if not self._checkManagerPermissions(_userWalletConfig, _action, _assets, _legoIds, _transferRecipient, _config.allowedAssets, _config.legoPerms, _config.transferPerms):
        return False

    # check manager limits
    return self._checkManagerLimits(_config.limits, _data, True, 0, False)


# manager permissions


@view
@internal
def _checkManagerPermissions(
    _userWalletConfig: address,
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
    if _action == wi.ActionType.TRANSFER and _transferRecipient != empty(address):
        if len(_transferPerms.allowedPayees) != 0 and not staticcall UserWalletConfig(_userWalletConfig).isWhitelisted(_transferRecipient):
            if  _transferRecipient not in _transferPerms.allowedPayees:
                return False

    # check action permissions
    if _action == wi.ActionType.TRANSFER:
        return _transferPerms.canTransfer
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


# check manager limits


@view
@internal
def _checkManagerLimits(
    _config: ManagerLimits,
    _data: ManagerData,
    _shouldCheckTxLimits: bool,
    _txUsdValue: uint256,
    _shouldCheckUsdValueParams: bool,
) -> bool:

    # check transaction limits
    if _shouldCheckTxLimits and not self._checkTransactionLimits(_config.maxNumTxsPerPeriod, _config.txCooldownBlocks, _data.numTxsInPeriod, _data.lastTxBlock):
        return False

    # check usd value params
    if _shouldCheckUsdValueParams and not self._checkManagerUsdLimits(_txUsdValue, _config, _data):
        return False

    return True


# check transaction limits


@view
@internal
def _checkTransactionLimits(
    _maxNumTxsPerPeriod: uint256,
    _txCooldownBlocks: uint256,
    _numTxsInPeriod: uint256,
    _lastTxBlock: uint256,
) -> bool:
    if _maxNumTxsPerPeriod != 0 and _numTxsInPeriod >= _maxNumTxsPerPeriod:
        return False
    
    if _txCooldownBlocks != 0 and _lastTxBlock + _txCooldownBlocks > block.number:
        return False
    
    return True


# check manager usd limits


@pure
@internal
def _checkManagerUsdLimits(_txUsdValue: uint256, _config: ManagerLimits, _data: ManagerData) -> bool:

    # check zero price
    if _txUsdValue == 0 and _config.failOnZeroPrice:
        return False

    # check max usd value per tx
    if _config.maxUsdValuePerTx != 0 and _txUsdValue > _config.maxUsdValuePerTx:
        return False
    
    # check max usd value per period
    if _config.maxUsdValuePerPeriod != 0 and _data.totalUsdValueInPeriod + _txUsdValue > _config.maxUsdValuePerPeriod:
        return False
    
    # check max usd value lifetime
    if _config.maxUsdValueLifetime != 0 and _data.totalUsdValue + _txUsdValue > _config.maxUsdValueLifetime:
        return False
    
    return True


# latest manager data


@view
@internal
def _getLatestManagerData(_data: ManagerData, _managerPeriod: uint256) -> ManagerData:
    data: ManagerData = _data

    # initialize period if first transaction
    if data.periodStartBlock == 0:
        data.periodStartBlock = block.number
    
    # check if current period has ended
    elif block.number >= data.periodStartBlock + _managerPeriod:
        data.numTxsInPeriod = 0
        data.totalUsdValueInPeriod = 0
        data.periodStartBlock = block.number

    return data


# validate manager post tx


@view
@external
def checkManagerUsdLimitsAndUpdateData(
    _txUsdValue: uint256,
    _specificLimits: ManagerLimits,
    _globalLimits: ManagerLimits,
    _managerPeriod: uint256,
    _data: ManagerData,
) -> ManagerData:
    return self._checkManagerUsdLimitsAndUpdateData(_txUsdValue, _specificLimits, _globalLimits, _managerPeriod, _data)


@view
@internal
def _checkManagerUsdLimitsAndUpdateData(
    _txUsdValue: uint256,
    _specificLimits: ManagerLimits,
    _globalLimits: ManagerLimits,
    _managerPeriod: uint256,
    _data: ManagerData,
) -> ManagerData:
    data: ManagerData = self._getLatestManagerData(_data, _managerPeriod)

    # check usd value limits
    assert self._checkManagerLimits(_specificLimits, data, False, _txUsdValue, True) # dev: usd value limit exceeded
    assert self._checkManagerLimits(_globalLimits, data, False, _txUsdValue, True) # dev: usd value limit exceeded

    # update data
    data.numTxsInPeriod += 1
    data.totalUsdValueInPeriod += _txUsdValue
    data.totalNumTxs += 1
    data.totalUsdValue += _txUsdValue
    data.lastTxBlock = block.number

    return data


#########################
# Global Manager Config #
#########################


@view
@external
def validateGlobalManagerSettings(
    _settings: GlobalManagerSettings,
    _inEjectMode: bool,
    _currentTimeLock: uint256,
    _legoBookAddr: address,
    _walletConfig: address,
) -> bool:
    return self._validateGlobalManagerSettings(_settings, _inEjectMode, _currentTimeLock, _legoBookAddr, _walletConfig)


@view
@internal
def _validateGlobalManagerSettings(
    _settings: GlobalManagerSettings,
    _inEjectMode: bool,
    _currentTimeLock: uint256,
    _legoBookAddr: address,
    _walletConfig: address,
) -> bool:
    return (
        self._validateManagerPeriod(_settings.managerPeriod) and
        self._validateStartDelay(_settings.startDelay, _currentTimeLock) and
        self._validateActivationLength(_settings.activationLength) and
        self._validateManagerLimits(_settings.limits, _settings.managerPeriod) and
        self._validateLegoPerms(_settings.legoPerms, _inEjectMode, _legoBookAddr) and
        self._validateTransferPerms(_settings.transferPerms, _walletConfig) and
        self._validateAllowedAssets(_settings.allowedAssets)
    )


# create default global manager settings


@view
@external
def createDefaultGlobalManagerSettings(
    _managerPeriod: uint256,
    _minTimeLock: uint256,
    _defaultActivationLength: uint256,
) -> GlobalManagerSettings:
    config: GlobalManagerSettings = empty(GlobalManagerSettings)
    config.managerPeriod = _managerPeriod
    config.startDelay = _minTimeLock
    config.activationLength = _defaultActivationLength
    config.canOwnerManage = True
    config.legoPerms, config.whitelistPerms, config.transferPerms = self._createHappyManagerDefaults()
    return config


##################
# Manager Config #
##################


# create manager settings


@view
@external
def validateAndCreateManagerSettings(
    _startDelay: uint256,
    _activationLength: uint256,
    _limits: ManagerLimits,
    _legoPerms: LegoPerms,
    _whitelistPerms: WhitelistPerms,
    _transferPerms: TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
    _currentTimeLock: uint256,
    _config: GlobalManagerSettings,
    _inEjectMode: bool,
    _legoBookAddr: address,
    _walletConfig: address,
) -> ManagerSettings:
    return self._validateAndCreateManagerSettings(_startDelay, _activationLength, _limits, _legoPerms, _whitelistPerms, _transferPerms, _allowedAssets, _currentTimeLock, _config, _inEjectMode, _legoBookAddr, _walletConfig)


@view
@internal
def _validateAndCreateManagerSettings(
    _startDelay: uint256,
    _activationLength: uint256,
    _limits: ManagerLimits,
    _legoPerms: LegoPerms,
    _whitelistPerms: WhitelistPerms,
    _transferPerms: TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
    _currentTimeLock: uint256,
    _config: GlobalManagerSettings,
    _inEjectMode: bool,
    _legoBookAddr: address,
    _walletConfig: address,
) -> ManagerSettings:

    # start delay
    startDelay: uint256 = max(_config.startDelay, _currentTimeLock)
    if _startDelay != 0:
        startDelay = max(startDelay, _startDelay) # using max here as extra protection

    # activation length
    activationLength: uint256 = _config.activationLength
    if _activationLength != 0:
        activationLength = min(activationLength, _activationLength)

    # validate settings
    assert (
        self._validateStartDelay(startDelay, _currentTimeLock) and
        self._validateActivationLength(activationLength) and
        self._validateManagerLimits(_limits, _config.managerPeriod) and
        self._validateLegoPerms(_legoPerms, _inEjectMode, _legoBookAddr) and
        self._validateTransferPerms(_transferPerms, _walletConfig) and
        self._validateAllowedAssets(_allowedAssets)
    ) # dev: invalid settings

    startBlock: uint256 = block.number + startDelay
    expiryBlock: uint256 = startBlock + activationLength

    return ManagerSettings(
        startBlock = startBlock,
        expiryBlock = expiryBlock,
        limits = _limits,
        legoPerms = _legoPerms,
        whitelistPerms = _whitelistPerms,
        transferPerms = _transferPerms,
        allowedAssets = _allowedAssets,
    )


# validate specific manager settings


@view
@external
def validateSpecificManagerSettings(
    _settings: ManagerSettings,
    _managerPeriod: uint256,
    _inEjectMode: bool,
    _legoBookAddr: address,
    _walletConfig: address,
) -> bool:
    return self._validateSpecificManagerSettings(_settings, _managerPeriod, _inEjectMode, _legoBookAddr, _walletConfig)


@view
@internal
def _validateSpecificManagerSettings(
    _settings: ManagerSettings,
    _managerPeriod: uint256,
    _inEjectMode: bool,
    _legoBookAddr: address,
    _walletConfig: address,
) -> bool:
    return (
        self._validateManagerLimits(_settings.limits, _managerPeriod) and
        self._validateLegoPerms(_settings.legoPerms, _inEjectMode, _legoBookAddr) and
        self._validateTransferPerms(_settings.transferPerms, _walletConfig) and
        self._validateAllowedAssets(_settings.allowedAssets)
    )


# create starter agent settings


@view
@external
def createStarterAgentSettings(_startingAgentActivationLength: uint256) -> ManagerSettings:
    config: ManagerSettings = ManagerSettings(
        startBlock = block.number,
        expiryBlock = block.number + _startingAgentActivationLength,
        limits = empty(ManagerLimits),
        legoPerms = empty(LegoPerms),
        whitelistPerms = empty(WhitelistPerms),
        transferPerms = empty(TransferPerms),
        allowedAssets = [],
    )
    config.legoPerms, config.whitelistPerms, config.transferPerms = self._createHappyManagerDefaults()
    return config


########################
# Manager Config Utils #
########################


@view
@internal
def _validateManagerPeriod(_managerPeriod: uint256) -> bool:
    return _managerPeriod >= MIN_MANAGER_PERIOD and _managerPeriod <= MAX_MANAGER_PERIOD


@view
@internal
def _validateStartDelay(_startDelay: uint256, _currentTimeLock: uint256) -> bool:
    return _startDelay <= MAX_START_DELAY and _startDelay >= _currentTimeLock


@view
@internal
def _validateActivationLength(_activationLength: uint256) -> bool:
    return _activationLength >= MIN_ACTIVATION_LENGTH and _activationLength <= MAX_ACTIVATION_LENGTH


@pure
@internal
def _validateManagerLimits(_limits: ManagerLimits, _managerPeriod: uint256) -> bool:
    # NOTE: 0 values are treated as "unlimited" throughout this validation
    
    # validate if both values are non-zero (not unlimited)
    if _limits.maxUsdValuePerTx != 0 and _limits.maxUsdValuePerPeriod != 0:
        if _limits.maxUsdValuePerTx > _limits.maxUsdValuePerPeriod:
            return False
    
    # validate per-period is not less than lifetime (when both are set)
    if _limits.maxUsdValuePerPeriod != 0 and _limits.maxUsdValueLifetime != 0:
        if _limits.maxUsdValuePerPeriod > _limits.maxUsdValueLifetime:
            return False
    
    # cooldown cannot exceed period length (unless cooldown is 0 = no cooldown)
    if _limits.txCooldownBlocks != 0 and _limits.txCooldownBlocks > _managerPeriod:
        return False
    
    return True


@view
@internal
def _validateLegoPerms(_legoPerms: LegoPerms, _inEjectMode: bool, _legoBookAddr: address) -> bool:
    if len(_legoPerms.allowedLegos) == 0:
        return True

    canDoAnything: bool = (_legoPerms.canManageYield or 
                          _legoPerms.canBuyAndSell or 
                          _legoPerms.canManageDebt or 
                          _legoPerms.canManageLiq or 
                          _legoPerms.canClaimRewards)

    # allowedLegos should be empty if there are no permissions
    if not canDoAnything:
        return False

    # if in eject mode, can't add legos as permissions
    if _inEjectMode:
        return False

    # validate lego book address
    if _legoBookAddr == empty(address):
        return False

    # check for duplicates and validate each lego ID
    checkedLegos: DynArray[uint256, MAX_CONFIG_LEGOS] = []
    for legoId: uint256 in _legoPerms.allowedLegos:
        if not staticcall Registry(_legoBookAddr).isValidRegId(legoId):
            return False
        if legoId in checkedLegos:
            return False
        checkedLegos.append(legoId)

    return True


@view
@internal
def _validateTransferPerms(_transferPerms: TransferPerms, _walletConfig: address) -> bool:
    if len(_transferPerms.allowedPayees) == 0:
        return True

    # canTransfer should be True if there are allowed payees
    if not _transferPerms.canTransfer:
        return False

    # validate each payee
    checkedPayees: DynArray[address, MAX_ALLOWED_PAYEES] = []
    for payee: address in _transferPerms.allowedPayees:
        if payee == empty(address):
            return False

        # check if payee is valid
        if not staticcall UserWalletConfig(_walletConfig).isRegisteredPayee(payee):
            return False

        # check for duplicates
        if payee in checkedPayees:
            return False

        checkedPayees.append(payee)

    return True


@pure
@internal
def _validateAllowedAssets(_allowedAssets: DynArray[address, MAX_CONFIG_ASSETS]) -> bool:
    if len(_allowedAssets) == 0:
        return True

    checkedAssets: DynArray[address, MAX_CONFIG_ASSETS] = []
    for asset: address in _allowedAssets:
        if asset == empty(address):
            return False

        # check for duplicates
        if asset in checkedAssets:
            return False
        checkedAssets.append(asset)

    return True


@pure
@internal
def _createHappyManagerDefaults() -> (LegoPerms, WhitelistPerms, TransferPerms):
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


###########################
# Global Manager Settings #
###########################


@external
def setGlobalManagerSettings(
    _user: address,
    _managerPeriod: uint256,
    _startDelay: uint256,
    _activationLength: uint256,
    _canOwnerManage: bool,
    _limits: ManagerLimits,
    _legoPerms: LegoPerms,
    _whitelistPerms: WhitelistPerms,
    _transferPerms: TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
) -> bool:
    kconfig: ManagerSettingsBundle = self._validateAndGetConfig(_user, empty(address))
    assert msg.sender == kconfig.owner # dev: no perms

    config: GlobalManagerSettings = GlobalManagerSettings(
        managerPeriod = _managerPeriod,
        startDelay = _startDelay,
        activationLength = _activationLength,
        canOwnerManage = _canOwnerManage,
        limits = _limits,
        legoPerms = _legoPerms,
        whitelistPerms = _whitelistPerms,
        transferPerms = _transferPerms,
        allowedAssets = _allowedAssets,
    )

    # validation
    assert self._validateGlobalManagerSettings(
        config,
        kconfig.inEjectMode,
        kconfig.timeLock,
        kconfig.legoBook,
        kconfig.walletConfig,
    ) # dev: invalid settings
    extcall UserWalletConfig(kconfig.walletConfig).setGlobalManagerSettings(config)

    log GlobalManagerSettingsModified(
        user = _user,
        managerPeriod = _managerPeriod,
        startDelay = _startDelay,
        activationLength = _activationLength,
        canOwnerManage = _canOwnerManage,
        maxUsdValuePerTx = _limits.maxUsdValuePerTx,
        maxUsdValuePerPeriod = _limits.maxUsdValuePerPeriod,
        maxUsdValueLifetime = _limits.maxUsdValueLifetime,
        maxNumTxsPerPeriod = _limits.maxNumTxsPerPeriod,
        txCooldownBlocks = _limits.txCooldownBlocks,
        failOnZeroPrice = _limits.failOnZeroPrice,
        canManageYield = _legoPerms.canManageYield,
        canBuyAndSell = _legoPerms.canBuyAndSell,
        canManageDebt = _legoPerms.canManageDebt,
        canManageLiq = _legoPerms.canManageLiq,
        canClaimRewards = _legoPerms.canClaimRewards,
        numAllowedLegos = len(_legoPerms.allowedLegos),
        canAddPendingWhitelist = _whitelistPerms.canAddPending,
        canConfirmWhitelist = _whitelistPerms.canConfirm,
        canCancelWhitelist = _whitelistPerms.canCancel,
        canRemoveWhitelist = _whitelistPerms.canRemove,
        canTransfer = _transferPerms.canTransfer,
        canCreateCheque = _transferPerms.canCreateCheque,
        canAddPendingPayee = _transferPerms.canAddPendingPayee,
        numAllowedRecipients = len(_transferPerms.allowedPayees),
        numAllowedAssets = len(_allowedAssets),
    )
    return True


####################
# Manager Settings #
####################


# add manager


@external
def addManager(
    _user: address,
    _manager: address,
    _limits: ManagerLimits,
    _legoPerms: LegoPerms,
    _whitelistPerms: WhitelistPerms,
    _transferPerms: TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
    _startDelay: uint256 = 0,
    _activationLength: uint256 = 0,
) -> bool:
    kconfig: ManagerSettingsBundle = self._validateAndGetConfig(_user, _manager)
    assert msg.sender == kconfig.owner # dev: no perms

    assert _manager not in [empty(address), kconfig.owner] # dev: invalid manager
    assert not kconfig.isManager # dev: manager already exists
    
    config: ManagerSettings = self._validateAndCreateManagerSettings(
        _startDelay,
        _activationLength,
        _limits,
        _legoPerms,
        _whitelistPerms,
        _transferPerms,
        _allowedAssets,
        kconfig.timeLock,
        staticcall UserWalletConfig(kconfig.walletConfig).globalManagerSettings(),
        kconfig.inEjectMode,
        kconfig.legoBook,
        kconfig.walletConfig,
    )
    extcall UserWalletConfig(kconfig.walletConfig).addManager(_manager, config)

    log ManagerSettingsModified(
        user = _user,
        manager = _manager,
        startBlock = config.startBlock,
        expiryBlock = config.expiryBlock,
        maxUsdValuePerTx = _limits.maxUsdValuePerTx,
        maxUsdValuePerPeriod = _limits.maxUsdValuePerPeriod,
        maxUsdValueLifetime = _limits.maxUsdValueLifetime,
        maxNumTxsPerPeriod = _limits.maxNumTxsPerPeriod,
        txCooldownBlocks = _limits.txCooldownBlocks,
        failOnZeroPrice = _limits.failOnZeroPrice,
        canManageYield = _legoPerms.canManageYield,
        canBuyAndSell = _legoPerms.canBuyAndSell,
        canManageDebt = _legoPerms.canManageDebt,
        canManageLiq = _legoPerms.canManageLiq,
        canClaimRewards = _legoPerms.canClaimRewards,
        numAllowedLegos = len(_legoPerms.allowedLegos),
        canAddPendingWhitelist = _whitelistPerms.canAddPending,
        canConfirmWhitelist = _whitelistPerms.canConfirm,
        canCancelWhitelist = _whitelistPerms.canCancel,
        canRemoveWhitelist = _whitelistPerms.canRemove,
        canTransfer = _transferPerms.canTransfer,
        canCreateCheque = _transferPerms.canCreateCheque,
        canAddPendingPayee = _transferPerms.canAddPendingPayee,
        numAllowedRecipients = len(_transferPerms.allowedPayees),
        numAllowedAssets = len(config.allowedAssets),
    )
    return True


# update existing manager


@external
def updateManager(
    _user: address,
    _manager: address,
    _limits: ManagerLimits,
    _legoPerms: LegoPerms,
    _whitelistPerms: WhitelistPerms,
    _transferPerms: TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
) -> bool:
    kconfig: ManagerSettingsBundle = self._validateAndGetConfig(_user, _manager)
    assert msg.sender == kconfig.owner # dev: no perms
    assert kconfig.isManager # dev: manager not found

    # update config
    config: ManagerSettings = staticcall UserWalletConfig(kconfig.walletConfig).managerSettings(_manager)
    config.limits = _limits
    config.legoPerms = _legoPerms
    config.whitelistPerms = _whitelistPerms
    config.transferPerms = _transferPerms
    config.allowedAssets = _allowedAssets

    # validation
    globalConfig: GlobalManagerSettings = staticcall UserWalletConfig(kconfig.walletConfig).globalManagerSettings()
    assert self._validateSpecificManagerSettings(
        config,
        globalConfig.managerPeriod,
        kconfig.inEjectMode,
        kconfig.legoBook,
        kconfig.walletConfig,
    ) # dev: invalid settings
    extcall UserWalletConfig(kconfig.walletConfig).updateManager(_manager, config)

    log ManagerSettingsModified(
        user = _user,
        manager = _manager,
        startBlock = config.startBlock,
        expiryBlock = config.expiryBlock,
        maxUsdValuePerTx = _limits.maxUsdValuePerTx,
        maxUsdValuePerPeriod = _limits.maxUsdValuePerPeriod,
        maxUsdValueLifetime = _limits.maxUsdValueLifetime,
        maxNumTxsPerPeriod = _limits.maxNumTxsPerPeriod,
        txCooldownBlocks = _limits.txCooldownBlocks,
        failOnZeroPrice = _limits.failOnZeroPrice,
        canManageYield = _legoPerms.canManageYield,
        canBuyAndSell = _legoPerms.canBuyAndSell,
        canManageDebt = _legoPerms.canManageDebt,
        canManageLiq = _legoPerms.canManageLiq,
        canClaimRewards = _legoPerms.canClaimRewards,
        numAllowedLegos = len(_legoPerms.allowedLegos),
        canAddPendingWhitelist = _whitelistPerms.canAddPending,
        canConfirmWhitelist = _whitelistPerms.canConfirm,
        canCancelWhitelist = _whitelistPerms.canCancel,
        canRemoveWhitelist = _whitelistPerms.canRemove,
        canTransfer = _transferPerms.canTransfer,
        canCreateCheque = _transferPerms.canCreateCheque,
        canAddPendingPayee = _transferPerms.canAddPendingPayee,
        numAllowedRecipients = len(_transferPerms.allowedPayees),
        numAllowedAssets = len(config.allowedAssets),
    )
    return True


# remove manager


@external
def removeManager(_user: address, _manager: address) -> bool:
    kconfig: ManagerSettingsBundle = self._validateAndGetConfig(_user, _manager)
    if msg.sender not in [kconfig.owner, _manager]:
        assert self._isSignerBackpack(msg.sender, kconfig.inEjectMode) # dev: no perms
    assert kconfig.isManager # dev: manager not found
    extcall UserWalletConfig(kconfig.walletConfig).removeManager(_manager)
    log ManagerRemoved(user = _user, manager = _manager)
    return True


# adjust activation length


@external
def adjustManagerActivationLength(
    _user: address,
    _manager: address,
    _activationLength: uint256,
    _shouldResetStartBlock: bool = False,
) -> bool:
    kconfig: ManagerSettingsBundle = self._validateAndGetConfig(_user, _manager)
    assert msg.sender == kconfig.owner # dev: no perms
    assert kconfig.isManager # dev: manager not found

    # validation
    config: ManagerSettings = staticcall UserWalletConfig(kconfig.walletConfig).managerSettings(_manager)
    assert config.startBlock < block.number # dev: manager not active yet
    assert self._validateActivationLength(_activationLength) # dev: invalid activation length

    # update config
    didRestart: bool = False
    if _shouldResetStartBlock or config.expiryBlock < block.number:
        config.startBlock = block.number
        didRestart = True

    config.expiryBlock = config.startBlock + _activationLength
    assert config.expiryBlock > block.number # dev: invalid expiry block
    extcall UserWalletConfig(kconfig.walletConfig).updateManager(_manager, config)

    log ManagerActivationLengthAdjusted(
        user = _user,
        manager = _manager,
        activationLength = _activationLength,
        didRestart = didRestart,
    )
    return True


# validate user, get config


@view
@internal
def _validateAndGetConfig(_user: address, _manager: address) -> ManagerSettingsBundle:
    ledger: address = staticcall Registry(UNDY_HQ).getAddr(LEDGER_ID)
    assert staticcall Ledger(ledger).isUserWallet(_user) # dev: not a user wallet

    walletConfig: address = staticcall UserWallet(_user).walletConfig()
    return staticcall UserWalletConfig(walletConfig).getManagerSettingsBundle(_manager)


# is signer backpack


@view
@internal
def _isSignerBackpack(_signer: address, _inEjectMode: bool) -> bool:
    if _inEjectMode:
        return False
    return _signer == staticcall Registry(UNDY_HQ).getAddr(BACKPACK_ID)


# ####################
# # Clone Managers   #
# ####################


# @external
# def cloneManagers(_fromWallet: address, _toWallet: address):
#     """Clone manager configuration from one wallet to another"""
#     # Get configs
#     ledger: address = staticcall Registry(UNDY_HQ).getAddr(LEDGER_ID)
#     assert staticcall Ledger(ledger).isUserWallet(_fromWallet) # dev: not a user wallet
#     assert staticcall Ledger(ledger).isUserWallet(_toWallet) # dev: not a user wallet
    
#     # Verify caller is owner of destination wallet
#     toConfig: address = staticcall UserWallet(_toWallet).walletConfig()
#     toOwner: address = staticcall UserWalletConfig(toConfig).owner()
#     assert msg.sender == toOwner # dev: no perms
    
#     # Get source config
#     fromConfig: address = staticcall UserWallet(_fromWallet).walletConfig()
    
#     # Verify same owner and group (similar checks as Paymaster.canCopyWalletConfig)
#     fromOwner: address = staticcall UserWalletConfig(fromConfig).owner()
#     assert fromOwner == toOwner # dev: different owners
    
#     # 1. Copy global manager settings
#     globalSettings: GlobalManagerSettings = staticcall UserWalletConfig(fromConfig).globalManagerSettings()
#     extcall UserWalletConfig(toConfig).setGlobalManagerSettings(globalSettings)
    
#     # 2. Copy all managers
#     numManagers: uint256 = staticcall UserWalletConfig(fromConfig).numManagers()
#     for i: uint256 in range(1, numManagers, bound=max_value(uint256)):
#         manager: address = staticcall UserWalletConfig(fromConfig).managers(i)
#         if manager == empty(address):
#             continue
            
#         settings: ManagerSettings = staticcall UserWalletConfig(fromConfig).managerSettings(manager)
#         if settings.startBlock != 0:
#             # Add manager directly to config
#             extcall UserWalletConfig(toConfig).addManager(manager, settings)