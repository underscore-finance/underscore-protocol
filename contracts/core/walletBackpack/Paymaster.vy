# @version 0.4.3

from interfaces import WalletConfigStructs as wcs

interface UserWalletConfig:
    def addPendingPayee(_payee: address, _pending: wcs.PendingPayee): nonpayable
    def updatePayee(_payee: address, _config: wcs.PayeeSettings): nonpayable
    def setGlobalPayeeSettings(_config: wcs.GlobalPayeeSettings): nonpayable
    def addPayee(_payee: address, _config: wcs.PayeeSettings): nonpayable
    def managerSettings(_addr: address) -> wcs.ManagerSettings: view
    def globalManagerSettings() -> wcs.GlobalManagerSettings: view
    def payeeSettings(_payee: address) -> wcs.PayeeSettings: view
    def pendingPayees(_payee: address) -> wcs.PendingPayee: view
    def globalPayeeSettings() -> wcs.GlobalPayeeSettings: view
    def indexOfWhitelist(_addr: address) -> uint256: view
    def confirmPendingPayee(_payee: address): nonpayable
    def cancelPendingPayee(_payee: address): nonpayable
    def indexOfManager(_addr: address) -> uint256: view
    def indexOfPayee(_payee: address) -> uint256: view
    def removePayee(_payee: address): nonpayable
    def timeLock() -> uint256: view
    def owner() -> address: view

interface MissionControl:
    def canPerformSecurityAction(_addr: address) -> bool: view

interface Ledger:
    def isUserWallet(_user: address) -> bool: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

interface UserWallet:
    def walletConfig() -> address: view

event PayeeAdded:
    user: indexed(address)
    payee: indexed(address)
    startBlock: uint256
    expiryBlock: uint256
    canPull: bool
    periodLength: uint256
    maxNumTxsPerPeriod: uint256
    txCooldownBlocks: uint256
    failOnZeroPrice: bool
    primaryAsset: address
    onlyPrimaryAsset: bool
    unitPerTxCap: uint256
    unitPerPeriodCap: uint256
    unitLifetimeCap: uint256
    usdPerTxCap: uint256
    usdPerPeriodCap: uint256
    usdLifetimeCap: uint256

event PayeeUpdated:
    user: indexed(address)
    payee: indexed(address)
    startBlock: uint256
    expiryBlock: uint256
    canPull: bool
    periodLength: uint256
    maxNumTxsPerPeriod: uint256
    txCooldownBlocks: uint256
    failOnZeroPrice: bool
    primaryAsset: address
    onlyPrimaryAsset: bool
    unitPerTxCap: uint256
    unitPerPeriodCap: uint256
    unitLifetimeCap: uint256
    usdPerTxCap: uint256
    usdPerPeriodCap: uint256
    usdLifetimeCap: uint256

event PayeeRemoved:
    user: indexed(address)
    payee: indexed(address)
    removedBy: indexed(address)

event GlobalPayeeSettingsModified:
    user: indexed(address)
    defaultPeriodLength: uint256
    startDelay: uint256
    activationLength: uint256
    maxNumTxsPerPeriod: uint256
    txCooldownBlocks: uint256
    failOnZeroPrice: bool
    canPayOwner: bool
    usdPerTxCap: uint256
    usdPerPeriodCap: uint256
    usdLifetimeCap: uint256

event PayeePending:
    user: indexed(address)
    payee: indexed(address)
    confirmBlock: uint256
    addedBy: indexed(address)
    canPull: bool
    periodLength: uint256
    maxNumTxsPerPeriod: uint256
    txCooldownBlocks: uint256
    failOnZeroPrice: bool
    primaryAsset: address
    onlyPrimaryAsset: bool
    unitPerTxCap: uint256
    unitPerPeriodCap: uint256
    unitLifetimeCap: uint256
    usdPerTxCap: uint256
    usdPerPeriodCap: uint256
    usdLifetimeCap: uint256

event PayeePendingConfirmed:
    user: indexed(address)
    payee: indexed(address)
    initiatedBlock: uint256
    confirmBlock: uint256
    confirmedBy: indexed(address)

event PayeePendingCancelled:
    user: indexed(address)
    payee: indexed(address)
    initiatedBlock: uint256
    confirmBlock: uint256
    cancelledBy: indexed(address)

UNDY_HQ: public(immutable(address))
LEDGER_ID: constant(uint256) = 2
MISSION_CONTROL_ID: constant(uint256) = 3

MIN_PAYEE_PERIOD: public(immutable(uint256))
MAX_PAYEE_PERIOD: public(immutable(uint256))
MIN_ACTIVATION_LENGTH: public(immutable(uint256))
MAX_ACTIVATION_LENGTH: public(immutable(uint256))
MAX_START_DELAY: public(immutable(uint256))


@deploy
def __init__(
    _undyHq: address,
    _minPayeePeriod: uint256,
    _maxPayeePeriod: uint256,
    _minActivationLength: uint256,
    _maxActivationLength: uint256,
    _maxStartDelay: uint256,
):
    assert _undyHq != empty(address) # dev: invalid undy hq
    UNDY_HQ = _undyHq

    assert _minPayeePeriod != 0 and _minPayeePeriod < _maxPayeePeriod # dev: invalid payee period
    MIN_PAYEE_PERIOD = _minPayeePeriod
    MAX_PAYEE_PERIOD = _maxPayeePeriod

    assert _minActivationLength != 0 and _minActivationLength < _maxActivationLength # dev: invalid activation length
    MIN_ACTIVATION_LENGTH = _minActivationLength
    MAX_ACTIVATION_LENGTH = _maxActivationLength

    assert _maxStartDelay != 0 # dev: invalid start delay
    MAX_START_DELAY = _maxStartDelay


#########################
# Global Payee Settings #
#########################


@external
def setGlobalPayeeSettings(
    _userWallet: address,
    _defaultPeriodLength: uint256,
    _startDelay: uint256,
    _activationLength: uint256,
    _maxNumTxsPerPeriod: uint256,
    _txCooldownBlocks: uint256,
    _failOnZeroPrice: bool,
    _usdLimits: wcs.PayeeLimits,
    _canPayOwner: bool,
) -> bool:
    assert self._isValidUserWallet(_userWallet) # dev: invalid user wallet

    # only owner can set global payee settings
    config: wcs.PayeeManagementBundle = self._getPayeeConfig(_userWallet, empty(address))
    assert msg.sender == config.owner # dev: no perms

    # validate global settings
    assert self._isValidGlobalPayeeSettings(_defaultPeriodLength, _startDelay, _activationLength, _maxNumTxsPerPeriod, _txCooldownBlocks, _failOnZeroPrice, _usdLimits, _canPayOwner, config.timeLock) # dev: invalid settings

    # update global settings in wallet config
    settings: wcs.GlobalPayeeSettings = wcs.GlobalPayeeSettings(
        defaultPeriodLength = _defaultPeriodLength,
        startDelay = _startDelay,
        activationLength = _activationLength,
        maxNumTxsPerPeriod = _maxNumTxsPerPeriod,
        txCooldownBlocks = _txCooldownBlocks,
        failOnZeroPrice = _failOnZeroPrice,
        usdLimits = _usdLimits,
        canPayOwner = _canPayOwner,
    )
    extcall UserWalletConfig(config.walletConfig).setGlobalPayeeSettings(settings)

    log GlobalPayeeSettingsModified(
        user = _userWallet,
        defaultPeriodLength = _defaultPeriodLength,
        startDelay = _startDelay,
        activationLength = _activationLength,
        maxNumTxsPerPeriod = _maxNumTxsPerPeriod,
        txCooldownBlocks = _txCooldownBlocks,
        failOnZeroPrice = _failOnZeroPrice,
        canPayOwner = _canPayOwner,
        usdPerTxCap = _usdLimits.perTxCap,
        usdPerPeriodCap = _usdLimits.perPeriodCap,
        usdLifetimeCap = _usdLimits.lifetimeCap,
    )
    return True


####################
# Payee Management #
####################


# add payee


@external
def addPayee(
    _userWallet: address,
    _payee: address,
    _canPull: bool,
    _periodLength: uint256,
    _maxNumTxsPerPeriod: uint256,
    _txCooldownBlocks: uint256,
    _failOnZeroPrice: bool,
    _primaryAsset: address,
    _onlyPrimaryAsset: bool,
    _unitLimits: wcs.PayeeLimits,
    _usdLimits: wcs.PayeeLimits,
    _startDelay: uint256 = 0,
    _activationLength: uint256 = 0,
) -> bool:
    assert self._isValidUserWallet(_userWallet) # dev: invalid user wallet

    # only owner can add payee
    config: wcs.PayeeManagementBundle = self._getPayeeConfig(_userWallet, _payee)
    assert msg.sender == config.owner # dev: no perms

    # validate and prepare payee settings
    isValid: bool = False
    settings: wcs.PayeeSettings = empty(wcs.PayeeSettings)
    isValid, settings = self._isValidNewPayee(_payee, config, _canPull, _periodLength, _maxNumTxsPerPeriod, _txCooldownBlocks, _failOnZeroPrice, _primaryAsset, _onlyPrimaryAsset, _unitLimits, _usdLimits, _startDelay, _activationLength)
    assert isValid # dev: invalid payee settings

    extcall UserWalletConfig(config.walletConfig).addPayee(_payee, settings)
    log PayeeAdded(
        user = _userWallet,
        payee = _payee,
        startBlock = settings.startBlock,
        expiryBlock = settings.expiryBlock,
        canPull = settings.canPull,
        periodLength = settings.periodLength,
        maxNumTxsPerPeriod = settings.maxNumTxsPerPeriod,
        txCooldownBlocks = settings.txCooldownBlocks,
        failOnZeroPrice = settings.failOnZeroPrice,
        primaryAsset = settings.primaryAsset,
        onlyPrimaryAsset = settings.onlyPrimaryAsset,
        unitPerTxCap = settings.unitLimits.perTxCap,
        unitPerPeriodCap = settings.unitLimits.perPeriodCap,
        unitLifetimeCap = settings.unitLimits.lifetimeCap,
        usdPerTxCap = settings.usdLimits.perTxCap,
        usdPerPeriodCap = settings.usdLimits.perPeriodCap,
        usdLifetimeCap = settings.usdLimits.lifetimeCap,
    )
    return True


# update existing payee


@external
def updatePayee(
    _userWallet: address,
    _payee: address,
    _canPull: bool,
    _periodLength: uint256,
    _maxNumTxsPerPeriod: uint256,
    _txCooldownBlocks: uint256,
    _failOnZeroPrice: bool,
    _primaryAsset: address,
    _onlyPrimaryAsset: bool,
    _unitLimits: wcs.PayeeLimits,
    _usdLimits: wcs.PayeeLimits,
) -> bool:
    assert self._isValidUserWallet(_userWallet) # dev: invalid user wallet

    # only owner can update payee
    config: wcs.PayeeManagementBundle = self._getPayeeConfig(_userWallet, _payee)
    assert msg.sender == config.owner # dev: no perms

    # validate payee settings
    assert self._isValidPayeeUpdate(config.isRegisteredPayee, _canPull, _periodLength, _maxNumTxsPerPeriod, _txCooldownBlocks, _failOnZeroPrice, _primaryAsset, _onlyPrimaryAsset, _unitLimits, _usdLimits) # dev: invalid payee settings

    # update config while preserving start/expiry blocks
    settings: wcs.PayeeSettings = wcs.PayeeSettings(
        startBlock = config.payeeSettings.startBlock,
        expiryBlock = config.payeeSettings.expiryBlock,
        canPull = _canPull,
        periodLength = _periodLength,
        maxNumTxsPerPeriod = _maxNumTxsPerPeriod,
        txCooldownBlocks = _txCooldownBlocks,
        failOnZeroPrice = _failOnZeroPrice,
        primaryAsset = _primaryAsset,
        onlyPrimaryAsset = _onlyPrimaryAsset,
        unitLimits = _unitLimits,
        usdLimits = _usdLimits,
    )

    extcall UserWalletConfig(config.walletConfig).updatePayee(_payee, settings)
    log PayeeUpdated(
        user = _userWallet,
        payee = _payee,
        startBlock = settings.startBlock,
        expiryBlock = settings.expiryBlock,
        canPull = _canPull,
        periodLength = _periodLength,
        maxNumTxsPerPeriod = _maxNumTxsPerPeriod,
        txCooldownBlocks = _txCooldownBlocks,
        failOnZeroPrice = _failOnZeroPrice,
        primaryAsset = _primaryAsset,
        onlyPrimaryAsset = _onlyPrimaryAsset,
        unitPerTxCap = _unitLimits.perTxCap,
        unitPerPeriodCap = _unitLimits.perPeriodCap,
        unitLifetimeCap = _unitLimits.lifetimeCap,
        usdPerTxCap = _usdLimits.perTxCap,
        usdPerPeriodCap = _usdLimits.perPeriodCap,
        usdLifetimeCap = _usdLimits.lifetimeCap,
    )
    return True


# remove payee


@external
def removePayee(_userWallet: address, _payee: address) -> bool:
    assert self._isValidUserWallet(_userWallet) # dev: invalid user wallet

    # only owner or payee can remove payee
    config: wcs.PayeeManagementBundle = self._getPayeeConfig(_userWallet, _payee)
    if msg.sender not in [config.owner, _payee]:
        assert self._canPerformSecurityAction(msg.sender) # dev: no perms

    # validate payee exists
    assert config.isRegisteredPayee # dev: payee not found

    # remove payee from wallet config
    extcall UserWalletConfig(config.walletConfig).removePayee(_payee)
    log PayeeRemoved(user = _userWallet, payee = _payee, removedBy = msg.sender)
    return True


##################
# Pending Payees #
##################


# add pending payee (for managers)


@external
def addPendingPayee(
    _userWallet: address,
    _payee: address,
    _canPull: bool,
    _periodLength: uint256,
    _maxNumTxsPerPeriod: uint256,
    _txCooldownBlocks: uint256,
    _failOnZeroPrice: bool,
    _primaryAsset: address,
    _onlyPrimaryAsset: bool,
    _unitLimits: wcs.PayeeLimits,
    _usdLimits: wcs.PayeeLimits,
    _startDelay: uint256 = 0,
    _activationLength: uint256 = 0,
) -> bool:
    assert self._isValidUserWallet(_userWallet) # dev: invalid user wallet

    # check if caller has permission to add pending payee
    config: wcs.PayeeManagementBundle = self._getPayeeConfig(_userWallet, _payee)
    assert self._canAddPendingPayee(msg.sender, _payee, config.owner, config.walletConfig) # dev: no permission to add pending payee

    # validate and prepare payee settings
    isValid: bool = False
    settings: wcs.PayeeSettings = empty(wcs.PayeeSettings)
    isValid, settings = self._isValidNewPayee(_payee, config, _canPull, _periodLength, _maxNumTxsPerPeriod, _txCooldownBlocks, _failOnZeroPrice, _primaryAsset, _onlyPrimaryAsset, _unitLimits, _usdLimits, _startDelay, _activationLength)
    assert isValid # dev: invalid payee settings

    # create pending payee with timelock
    confirmBlock: uint256 = block.number + config.timeLock
    pending: wcs.PendingPayee = wcs.PendingPayee(
        settings = settings,
        initiatedBlock = block.number,
        confirmBlock = confirmBlock,
        currentOwner = config.owner,
    )
    extcall UserWalletConfig(config.walletConfig).addPendingPayee(_payee, pending)

    log PayeePending(
        user = _userWallet,
        payee = _payee,
        confirmBlock = confirmBlock,
        addedBy = msg.sender,
        canPull = settings.canPull,
        periodLength = settings.periodLength,
        maxNumTxsPerPeriod = settings.maxNumTxsPerPeriod,
        txCooldownBlocks = settings.txCooldownBlocks,
        failOnZeroPrice = settings.failOnZeroPrice,
        primaryAsset = settings.primaryAsset,
        onlyPrimaryAsset = settings.onlyPrimaryAsset,
        unitPerTxCap = settings.unitLimits.perTxCap,
        unitPerPeriodCap = settings.unitLimits.perPeriodCap,
        unitLifetimeCap = settings.unitLimits.lifetimeCap,
        usdPerTxCap = settings.usdLimits.perTxCap,
        usdPerPeriodCap = settings.usdLimits.perPeriodCap,
        usdLifetimeCap = settings.usdLimits.lifetimeCap,
    )
    return True


# confirm pending payee (for owner)


@external
def confirmPendingPayee(_userWallet: address, _payee: address) -> bool:
    assert self._isValidUserWallet(_userWallet) # dev: invalid user wallet

    # only owner can confirm pending payee
    config: wcs.PayeeManagementBundle = self._getPayeeConfig(_userWallet, _payee)
    assert msg.sender == config.owner # dev: no perms
    
    # get pending payee
    pendingPayee: wcs.PendingPayee = staticcall UserWalletConfig(config.walletConfig).pendingPayees(_payee)
    assert pendingPayee.initiatedBlock != 0 # dev: no pending payee
    assert pendingPayee.confirmBlock != 0 and block.number >= pendingPayee.confirmBlock # dev: time delay not reached
    assert pendingPayee.currentOwner == config.owner # dev: must be same owner
    
    # confirm the pending payee
    extcall UserWalletConfig(config.walletConfig).confirmPendingPayee(_payee)
    log PayeePendingConfirmed(
        user = _userWallet,
        payee = _payee,
        initiatedBlock = pendingPayee.initiatedBlock,
        confirmBlock = pendingPayee.confirmBlock,
        confirmedBy = msg.sender
    )
    return True


# cancel pending payee


@external
def cancelPendingPayee(_userWallet: address, _payee: address) -> bool:
    assert self._isValidUserWallet(_userWallet) # dev: invalid user wallet

    # only owner or payee can cancel pending payee
    config: wcs.PayeeManagementBundle = self._getPayeeConfig(_userWallet, _payee)
    if msg.sender not in [config.owner, _payee]:
        assert self._canPerformSecurityAction(msg.sender) # dev: no perms

    # get pending payee
    pendingPayee: wcs.PendingPayee = staticcall UserWalletConfig(config.walletConfig).pendingPayees(_payee)
    assert pendingPayee.initiatedBlock != 0 # dev: no pending payee

    # cancel the pending payee
    extcall UserWalletConfig(config.walletConfig).cancelPendingPayee(_payee)
    log PayeePendingCancelled(
        user = _userWallet,
        payee = _payee,
        initiatedBlock = pendingPayee.initiatedBlock,
        confirmBlock = pendingPayee.confirmBlock,
        cancelledBy = msg.sender
    )
    return True


####################
# Payee Validation #
####################


# is valid new payee


@view
@external
def isValidNewPayee(
    _userWallet: address,
    _payee: address,
    _canPull: bool,
    _periodLength: uint256,
    _maxNumTxsPerPeriod: uint256,
    _txCooldownBlocks: uint256,
    _failOnZeroPrice: bool,
    _primaryAsset: address,
    _onlyPrimaryAsset: bool,
    _unitLimits: wcs.PayeeLimits,
    _usdLimits: wcs.PayeeLimits,
    _startDelay: uint256 = 0,
    _activationLength: uint256 = 0,
) -> bool:
    config: wcs.PayeeManagementBundle = self._getPayeeConfig(_userWallet, _payee)
    isValid: bool = False
    na: wcs.PayeeSettings = empty(wcs.PayeeSettings)
    isValid, na = self._isValidNewPayee(_payee, config, _canPull, _periodLength, _maxNumTxsPerPeriod, _txCooldownBlocks, _failOnZeroPrice, _primaryAsset, _onlyPrimaryAsset, _unitLimits, _usdLimits, _startDelay, _activationLength)
    return isValid


@view
@internal
def _isValidNewPayee(
    _payee: address,
    _config: wcs.PayeeManagementBundle,
    _canPull: bool,
    _periodLength: uint256,
    _maxNumTxsPerPeriod: uint256,
    _txCooldownBlocks: uint256,
    _failOnZeroPrice: bool,
    _primaryAsset: address,
    _onlyPrimaryAsset: bool,
    _unitLimits: wcs.PayeeLimits,
    _usdLimits: wcs.PayeeLimits,
    _startDelay: uint256,
    _activationLength: uint256,
) -> (bool, wcs.PayeeSettings):

    # invalid payee
    if _payee in [empty(address), _config.owner, _config.wallet, _config.walletConfig]:
        return False, empty(wcs.PayeeSettings)

    # payee already exists
    if _config.isRegisteredPayee:
        return False, empty(wcs.PayeeSettings)

    # payee is already whitelisted
    if _config.isWhitelisted:
        return False, empty(wcs.PayeeSettings)

    # calculate start delay
    startDelay: uint256 = max(_config.globalPayeeSettings.startDelay, _config.timeLock)
    if _startDelay != 0:
        startDelay = max(startDelay, _startDelay)

    # calculate activation length
    activationLength: uint256 = _config.globalPayeeSettings.activationLength
    if _activationLength != 0:
        activationLength = min(activationLength, _activationLength)

    # use global default period length if not specified
    periodLength: uint256 = _periodLength
    if periodLength == 0:
        periodLength = _config.globalPayeeSettings.defaultPeriodLength

    # validate start delay
    if not self._validateStartDelay(startDelay, _config.timeLock):
        return False, empty(wcs.PayeeSettings)

    # validate period length
    if not self._validatePayeePeriod(periodLength):
        return False, empty(wcs.PayeeSettings)

    # validate activation length
    if not self._validateActivationLength(activationLength):
        return False, empty(wcs.PayeeSettings)

    # validate cooldown
    if not self._validatePayeeCooldown(_txCooldownBlocks, periodLength):
        return False, empty(wcs.PayeeSettings)

    # validate primary asset
    if not self._validatePrimaryAsset(_primaryAsset, _onlyPrimaryAsset):
        return False, empty(wcs.PayeeSettings)

    # validate unit limits
    if not self._validatePayeeLimits(_unitLimits):
        return False, empty(wcs.PayeeSettings)

    # validate usd limits
    if not self._validatePayeeLimits(_usdLimits):
        return False, empty(wcs.PayeeSettings)

    # validate pull payee
    if not self._validatePullPayee(_canPull, _unitLimits, _usdLimits):
        return False, empty(wcs.PayeeSettings)

    # create start and expiry blocks
    startBlock: uint256 = block.number + startDelay
    expiryBlock: uint256 = startBlock + activationLength

    settings: wcs.PayeeSettings = wcs.PayeeSettings(
        startBlock = startBlock,
        expiryBlock = expiryBlock,
        canPull = _canPull,
        periodLength = periodLength,
        maxNumTxsPerPeriod = _maxNumTxsPerPeriod,
        txCooldownBlocks = _txCooldownBlocks,
        failOnZeroPrice = _failOnZeroPrice,
        primaryAsset = _primaryAsset,
        onlyPrimaryAsset = _onlyPrimaryAsset,
        unitLimits = _unitLimits,
        usdLimits = _usdLimits,
    )
    return True, settings


# is valid payee update


@view
@external
def isValidPayeeUpdate(
    _userWallet: address,
    _payee: address,
    _canPull: bool,
    _periodLength: uint256,
    _maxNumTxsPerPeriod: uint256,
    _txCooldownBlocks: uint256,
    _failOnZeroPrice: bool,
    _primaryAsset: address,
    _onlyPrimaryAsset: bool,
    _unitLimits: wcs.PayeeLimits,
    _usdLimits: wcs.PayeeLimits,
) -> bool:
    config: wcs.PayeeManagementBundle = self._getPayeeConfig(_userWallet, _payee)
    return self._isValidPayeeUpdate(config.isRegisteredPayee, _canPull, _periodLength, _maxNumTxsPerPeriod, _txCooldownBlocks, _failOnZeroPrice, _primaryAsset, _onlyPrimaryAsset, _unitLimits, _usdLimits)


@view
@internal
def _isValidPayeeUpdate(
    _isRegisteredPayee: bool,
    _canPull: bool,
    _periodLength: uint256,
    _maxNumTxsPerPeriod: uint256,
    _txCooldownBlocks: uint256,
    _failOnZeroPrice: bool,
    _primaryAsset: address,
    _onlyPrimaryAsset: bool,
    _unitLimits: wcs.PayeeLimits,
    _usdLimits: wcs.PayeeLimits,
) -> bool:

    # payee not found
    if not _isRegisteredPayee:
        return False

    # validate period length
    if not self._validatePayeePeriod(_periodLength):
        return False

    # validate cooldown
    if not self._validatePayeeCooldown(_txCooldownBlocks, _periodLength):
        return False

    # validate primary asset
    if not self._validatePrimaryAsset(_primaryAsset, _onlyPrimaryAsset):
        return False

    # validate unit limits
    if not self._validatePayeeLimits(_unitLimits):
        return False

    # validate usd limits
    if not self._validatePayeeLimits(_usdLimits):
        return False

    # validate pull payee
    if not self._validatePullPayee(_canPull, _unitLimits, _usdLimits):
        return False

    return True


# validate pending payee


@view
@external
def canAddPendingPayee(_userWallet: address, _payee: address, _caller: address) -> bool:
    config: wcs.PayeeManagementBundle = self._getPayeeConfig(_userWallet, _payee)
    return self._canAddPendingPayee(_caller, _payee, config.owner, config.walletConfig)


@view
@internal
def _canAddPendingPayee(_caller: address, _payee: address, _owner: address, _walletConfig: address) -> bool:
    # owner can always add payees directly (not pending)
    if _caller == _owner:
        return False

    # check if caller is a manager
    if staticcall UserWalletConfig(_walletConfig).indexOfManager(_caller) == 0:
        return False

    pendingPayee: wcs.PendingPayee = staticcall UserWalletConfig(_walletConfig).pendingPayees(_payee)
    if pendingPayee.initiatedBlock != 0:
        return False

    # check if manager is active
    managerSettings: wcs.ManagerSettings = staticcall UserWalletConfig(_walletConfig).managerSettings(_caller)
    if managerSettings.startBlock > block.number or managerSettings.expiryBlock <= block.number:
        return False
    
    # check if manager has permission
    globalManagerSettings: wcs.GlobalManagerSettings = staticcall UserWalletConfig(_walletConfig).globalManagerSettings()
    return managerSettings.transferPerms.canAddPendingPayee and globalManagerSettings.transferPerms.canAddPendingPayee


# validate global payee settings


@view
@external
def isValidGlobalPayeeSettings(
    _userWallet: address,
    _defaultPeriodLength: uint256,
    _startDelay: uint256,
    _activationLength: uint256,
    _maxNumTxsPerPeriod: uint256,
    _txCooldownBlocks: uint256,
    _failOnZeroPrice: bool,
    _usdLimits: wcs.PayeeLimits,
    _canPayOwner: bool,
) -> bool:
    config: wcs.PayeeManagementBundle = self._getPayeeConfig(_userWallet, empty(address))
    return self._isValidGlobalPayeeSettings(_defaultPeriodLength, _startDelay, _activationLength, _maxNumTxsPerPeriod, _txCooldownBlocks, _failOnZeroPrice, _usdLimits, _canPayOwner, config.timeLock)


@view
@internal
def _isValidGlobalPayeeSettings(
    _defaultPeriodLength: uint256,
    _startDelay: uint256,
    _activationLength: uint256,
    _maxNumTxsPerPeriod: uint256,
    _txCooldownBlocks: uint256,
    _failOnZeroPrice: bool,
    _usdLimits: wcs.PayeeLimits,
    _canPayOwner: bool,
    _timeLock: uint256,
) -> bool:

    # validate period length
    if not self._validatePayeePeriod(_defaultPeriodLength):
        return False

    # validate cooldown
    if not self._validatePayeeCooldown(_txCooldownBlocks, _defaultPeriodLength):
        return False

    # validate usd limits
    if not self._validatePayeeLimits(_usdLimits):
        return False

    # validate activation length
    if not self._validateActivationLength(_activationLength):
        return False

    if not self._validateStartDelay(_startDelay, _timeLock):
        return False

    return True


##########################
# Payee Validation Utils #
##########################


@view
@internal
def _validateStartDelay(_startDelay: uint256, _currentTimeLock: uint256) -> bool:
    return _startDelay <= MAX_START_DELAY and _startDelay >= _currentTimeLock


@view
@internal
def _validatePayeePeriod(_periodLength: uint256) -> bool:
    return _periodLength >= MIN_PAYEE_PERIOD and _periodLength <= MAX_PAYEE_PERIOD


@view
@internal
def _validateActivationLength(_activationLength: uint256) -> bool:
    return _activationLength >= MIN_ACTIVATION_LENGTH and _activationLength <= MAX_ACTIVATION_LENGTH


@pure
@internal
def _validatePayeeCooldown(_txCooldownBlocks: uint256, _periodLength: uint256) -> bool:
    # 0 means no cooldown, which is valid
    if _txCooldownBlocks == 0:
        return True
    return _txCooldownBlocks <= _periodLength


@pure
@internal
def _validatePrimaryAsset(_primaryAsset: address, _onlyPrimaryAsset: bool) -> bool:
    # if onlyPrimaryAsset is true, primaryAsset must be set
    if _onlyPrimaryAsset and _primaryAsset == empty(address):
        return False
    return True


@pure
@internal
def _validatePullPayee(
    _canPull: bool,
    _unitLimits: wcs.PayeeLimits,
    _usdLimits: wcs.PayeeLimits,
) -> bool:
    if not _canPull:
        return True # not a pull payee, no additional validation needed
    
    # pull payees must have at least one type of limit
    hasUnitLimits: bool = (
        _unitLimits.perTxCap != 0 or 
        _unitLimits.perPeriodCap != 0 or 
        _unitLimits.lifetimeCap != 0
    )
    hasUsdLimits: bool = (
        _usdLimits.perTxCap != 0 or 
        _usdLimits.perPeriodCap != 0 or 
        _usdLimits.lifetimeCap != 0
    )
    return hasUnitLimits or hasUsdLimits


@pure
@internal
def _validatePayeeLimits(_limits: wcs.PayeeLimits) -> bool:
    # NOTE: 0 values are treated as "unlimited"
    
    # validate per-tx cap does not exceed per-period cap (when both are set)
    if _limits.perTxCap != 0 and _limits.perPeriodCap != 0:
        if _limits.perTxCap > _limits.perPeriodCap:
            return False
    
    # validate per-period cap does not exceed lifetime cap (when both are set)
    if _limits.perPeriodCap != 0 and _limits.lifetimeCap != 0:
        if _limits.perPeriodCap > _limits.lifetimeCap:
            return False
    
    # validate per-tx cap does not exceed lifetime cap (when both are set)
    if _limits.perTxCap != 0 and _limits.lifetimeCap != 0:
        if _limits.perTxCap > _limits.lifetimeCap:
            return False

    return True


#############
# Utilities #
#############


# get payee management bundle


@view
@external
def getPayeeConfig(_userWallet: address, _payee: address) -> wcs.PayeeManagementBundle:
    return self._getPayeeConfig(_userWallet, _payee)


@view
@internal
def _getPayeeConfig(_userWallet: address, _payee: address) -> wcs.PayeeManagementBundle:
    walletConfig: address = staticcall UserWallet(_userWallet).walletConfig()
    owner: address = staticcall UserWalletConfig(walletConfig).owner()
    return wcs.PayeeManagementBundle(
        owner = owner,
        wallet = _userWallet,
        isRegisteredPayee = staticcall UserWalletConfig(walletConfig).indexOfPayee(_payee) != 0,
        isWhitelisted = staticcall UserWalletConfig(walletConfig).indexOfWhitelist(_payee) != 0,
        payeeSettings = staticcall UserWalletConfig(walletConfig).payeeSettings(_payee),
        globalPayeeSettings = staticcall UserWalletConfig(walletConfig).globalPayeeSettings(),
        timeLock = staticcall UserWalletConfig(walletConfig).timeLock(),
        walletConfig = walletConfig,
    )


# is valid user wallet


@view
@internal
def _isValidUserWallet(_userWallet: address) -> bool:
    ledger: address = staticcall Registry(UNDY_HQ).getAddr(LEDGER_ID)
    return staticcall Ledger(ledger).isUserWallet(_userWallet)


# can perform security action


@view
@internal
def _canPerformSecurityAction(_addr: address) -> bool:
    missionControl: address = staticcall Registry(UNDY_HQ).getAddr(MISSION_CONTROL_ID)
    if missionControl == empty(address):
        return False
    return staticcall MissionControl(missionControl).canPerformSecurityAction(_addr)


# default global payee settings


@view
@external
def createDefaultGlobalPayeeSettings(
    _defaultPeriodLength: uint256,
    _startDelay: uint256,
    _activationLength: uint256,
) -> wcs.GlobalPayeeSettings:
    return wcs.GlobalPayeeSettings(
        defaultPeriodLength = _defaultPeriodLength,
        startDelay = _startDelay,
        activationLength = _activationLength,
        maxNumTxsPerPeriod = 0,
        txCooldownBlocks = 0,
        failOnZeroPrice = False,
        usdLimits = empty(wcs.PayeeLimits),
        canPayOwner = True,
    )
