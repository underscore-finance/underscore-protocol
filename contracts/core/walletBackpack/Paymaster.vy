# @version 0.4.3
# pragma optimize codesize

from interfaces import WalletConfigStructs as wcs

interface UserWalletConfig:
    def createCheque(_recipient: address, _cheque: wcs.Cheque, _chequeData: wcs.ChequeData, _isExistingCheque: bool): nonpayable
    def addPendingWhitelistAddr(_addr: address, _pending: wcs.PendingWhitelist): nonpayable
    def addPendingPayee(_payee: address, _pending: wcs.PendingPayee): nonpayable
    def updatePayee(_payee: address, _config: wcs.PayeeSettings): nonpayable
    def setGlobalPayeeSettings(_config: wcs.GlobalPayeeSettings): nonpayable
    def addPayee(_payee: address, _config: wcs.PayeeSettings): nonpayable
    def pendingWhitelist(_addr: address) -> wcs.PendingWhitelist: view
    def managerSettings(_addr: address) -> wcs.ManagerSettings: view
    def globalManagerSettings() -> wcs.GlobalManagerSettings: view
    def setChequeSettings(_config: wcs.ChequeSettings): nonpayable
    def payeeSettings(_payee: address) -> wcs.PayeeSettings: view
    def pendingPayees(_payee: address) -> wcs.PendingPayee: view
    def globalPayeeSettings() -> wcs.GlobalPayeeSettings: view
    def cancelPendingWhitelistAddr(_addr: address): nonpayable
    def indexOfWhitelist(_addr: address) -> uint256: view
    def confirmWhitelistAddr(_addr: address): nonpayable
    def confirmPendingPayee(_payee: address): nonpayable
    def cheques(_recipient: address) -> wcs.Cheque: view
    def removeWhitelistAddr(_addr: address): nonpayable
    def cancelPendingPayee(_payee: address): nonpayable
    def indexOfManager(_addr: address) -> uint256: view
    def indexOfPayee(_payee: address) -> uint256: view
    def cancelCheque(_recipient: address): nonpayable
    def chequeSettings() -> wcs.ChequeSettings: view
    def chequePeriodData() -> wcs.ChequeData: view
    def removePayee(_payee: address): nonpayable
    def numActiveCheques() -> uint256: view
    def timeLock() -> uint256: view
    def wallet() -> address: view
    def owner() -> address: view

interface Appraiser:
    def updatePriceAndGetUsdValue(_asset: address, _amount: uint256, _missionControl: address = empty(address), _legoBook: address = empty(address)) -> uint256: nonpayable

interface MissionControl:
    def canPerformSecurityAction(_addr: address) -> bool: view

interface Ledger:
    def isUserWallet(_user: address) -> bool: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

interface UserWallet:
    def walletConfig() -> address: view

event WhitelistAddrPending:
    user: indexed(address)
    addr: indexed(address)
    confirmBlock: uint256
    addedBy: indexed(address)

event WhitelistAddrConfirmed:
    user: indexed(address)
    addr: indexed(address)
    initiatedBlock: uint256
    confirmBlock: uint256
    confirmedBy: indexed(address)

event WhitelistAddrCancelled:
    user: indexed(address)
    addr: indexed(address)
    initiatedBlock: uint256
    confirmBlock: uint256
    cancelledBy: indexed(address)

event WhitelistAddrRemoved:
    user: indexed(address)
    addr: indexed(address)
    removedBy: indexed(address)

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

event ChequeCreated:
    user: indexed(address)
    recipient: indexed(address)
    asset: address
    amount: uint256
    usdValue: uint256
    unlockBlock: uint256
    expiryBlock: uint256
    canManagerPay: bool
    canBePulled: bool
    creator: indexed(address)

event ChequeCancelled:
    user: indexed(address)
    recipient: indexed(address)
    asset: address
    amount: uint256
    usdValue: uint256
    unlockBlock: uint256
    expiryBlock: uint256
    canManagerPay: bool
    canBePulled: bool
    cancelledBy: indexed(address)

event ChequeSettingsModified:
    user: indexed(address)
    maxNumActiveCheques: uint256
    maxChequeUsdValue: uint256
    instantUsdThreshold: uint256
    perPeriodPaidUsdCap: uint256
    maxNumChequesPaidPerPeriod: uint256
    payCooldownBlocks: uint256
    perPeriodCreatedUsdCap: uint256
    maxNumChequesCreatedPerPeriod: uint256
    createCooldownBlocks: uint256
    periodLength: uint256
    expensiveDelayBlocks: uint256
    defaultExpiryBlocks: uint256
    canManagersCreateCheques: bool
    canManagerPay: bool
    canBePulled: bool

UNDY_HQ: public(immutable(address))
LEDGER_ID: constant(uint256) = 2
MISSION_CONTROL_ID: constant(uint256) = 3
APPRAISER_ID: constant(uint256) = 8

# constants
MAX_CONFIG_ASSETS: constant(uint256) = 40

# payee validation bounds
MIN_PAYEE_PERIOD: public(immutable(uint256))
MAX_PAYEE_PERIOD: public(immutable(uint256))
MIN_ACTIVATION_LENGTH: public(immutable(uint256))
MAX_ACTIVATION_LENGTH: public(immutable(uint256))
MAX_START_DELAY: public(immutable(uint256))
MIN_CHEQUE_PERIOD: public(immutable(uint256))
MAX_CHEQUE_PERIOD: public(immutable(uint256))
MIN_EXPENSIVE_CHEQUE_DELAY: public(immutable(uint256))
MAX_UNLOCK_BLOCKS: public(immutable(uint256))
MAX_EXPIRY_BLOCKS: public(immutable(uint256))


@deploy
def __init__(
    _undyHq: address,
    _minPayeePeriod: uint256,
    _maxPayeePeriod: uint256,
    _minActivationLength: uint256,
    _maxActivationLength: uint256,
    _maxStartDelay: uint256,
    _minChequePeriod: uint256,
    _maxChequePeriod: uint256,
    _minExpensiveChequeDelay: uint256,
    _maxUnlockBlocks: uint256,
    _maxExpiryBlocks: uint256,
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

    assert _minChequePeriod != 0 and _minChequePeriod < _maxChequePeriod # dev: invalid cheque period
    MIN_CHEQUE_PERIOD = _minChequePeriod
    MAX_CHEQUE_PERIOD = _maxChequePeriod

    assert _minExpensiveChequeDelay != 0 # dev: invalid expensive cheque delay
    MIN_EXPENSIVE_CHEQUE_DELAY = _minExpensiveChequeDelay

    assert _maxUnlockBlocks != 0 # dev: invalid unlock blocks
    MAX_UNLOCK_BLOCKS = _maxUnlockBlocks

    assert _maxExpiryBlocks != 0 # dev: invalid expiry blocks
    MAX_EXPIRY_BLOCKS = _maxExpiryBlocks


########################
# Whitelist Management #
########################


# add whitelist


@external
def addPendingWhitelistAddr(_userWallet: address, _whitelistAddr: address):
    assert self._isValidUserWallet(_userWallet) # dev: invalid user wallet

    # validate permissions
    c: wcs.WhitelistConfigBundle = self._getWhitelistConfig(_userWallet, _whitelistAddr, msg.sender)
    assert self._canManageWhitelist(c.isOwner, c.isManager, wcs.WhitelistAction.ADD_PENDING, c.whitelistPerms, c.globalWhitelistPerms) # dev: no perms

    # validate input
    assert _whitelistAddr not in [empty(address), c.wallet, c.owner, c.walletConfig] # dev: invalid addr
    assert not c.isWhitelisted # dev: already whitelisted
    assert c.pendingWhitelist.initiatedBlock == 0 # dev: pending whitelist already exists

    # under time lock
    confirmBlock: uint256 = block.number + c.timeLock
    c.pendingWhitelist = wcs.PendingWhitelist(
        initiatedBlock = block.number,
        confirmBlock = confirmBlock,
        currentOwner = c.owner,
    )
    extcall UserWalletConfig(c.walletConfig).addPendingWhitelistAddr(_whitelistAddr, c.pendingWhitelist)

    log WhitelistAddrPending(user = _userWallet, addr = _whitelistAddr, confirmBlock = confirmBlock, addedBy = msg.sender)


# confirm whitelist


@external
def confirmWhitelistAddr(_userWallet: address, _whitelistAddr: address):
    assert self._isValidUserWallet(_userWallet) # dev: invalid user wallet

    c: wcs.WhitelistConfigBundle = self._getWhitelistConfig(_userWallet, _whitelistAddr, msg.sender)
    assert self._canManageWhitelist(c.isOwner, c.isManager, wcs.WhitelistAction.CONFIRM_WHITELIST, c.whitelistPerms, c.globalWhitelistPerms) # dev: no perms

    assert c.pendingWhitelist.initiatedBlock != 0 # dev: no pending whitelist
    assert c.pendingWhitelist.confirmBlock != 0 and block.number >= c.pendingWhitelist.confirmBlock # dev: time delay not reached
    assert c.pendingWhitelist.currentOwner == c.owner # dev: owner must match

    extcall UserWalletConfig(c.walletConfig).confirmWhitelistAddr(_whitelistAddr)
    log WhitelistAddrConfirmed(user = _userWallet, addr = _whitelistAddr, initiatedBlock = c.pendingWhitelist.initiatedBlock, confirmBlock = c.pendingWhitelist.confirmBlock, confirmedBy = msg.sender)


# cancel pending whitelist


@external
def cancelPendingWhitelistAddr(_userWallet: address, _whitelistAddr: address):
    assert self._isValidUserWallet(_userWallet) # dev: invalid user wallet

    c: wcs.WhitelistConfigBundle = self._getWhitelistConfig(_userWallet, _whitelistAddr, msg.sender)
    if not self._canManageWhitelist(c.isOwner, c.isManager, wcs.WhitelistAction.CANCEL_WHITELIST, c.whitelistPerms, c.globalWhitelistPerms):
        assert self._canPerformSecurityAction(msg.sender) # dev: no perms

    assert c.pendingWhitelist.initiatedBlock != 0 # dev: no pending whitelist
    extcall UserWalletConfig(c.walletConfig).cancelPendingWhitelistAddr(_whitelistAddr)

    log WhitelistAddrCancelled(user = _userWallet, addr = _whitelistAddr, initiatedBlock = c.pendingWhitelist.initiatedBlock, confirmBlock = c.pendingWhitelist.confirmBlock, cancelledBy = msg.sender)


# remove whitelist


@external
def removeWhitelistAddr(_userWallet: address, _whitelistAddr: address):
    assert self._isValidUserWallet(_userWallet) # dev: invalid user wallet

    c: wcs.WhitelistConfigBundle = self._getWhitelistConfig(_userWallet, _whitelistAddr, msg.sender)
    if not self._canManageWhitelist(c.isOwner, c.isManager, wcs.WhitelistAction.REMOVE_WHITELIST, c.whitelistPerms, c.globalWhitelistPerms):
        assert self._canPerformSecurityAction(msg.sender) # dev: no perms

    assert c.isWhitelisted # dev: not whitelisted
    extcall UserWalletConfig(c.walletConfig).removeWhitelistAddr(_whitelistAddr)

    log WhitelistAddrRemoved(user = _userWallet, addr = _whitelistAddr, removedBy = msg.sender)


# can manage whitelist


@view
@external
def canManageWhitelist(
    _userWallet: address,
    _caller: address,
    _action: wcs.WhitelistAction,
) -> bool:
    c: wcs.WhitelistConfigBundle = self._getWhitelistConfig(_userWallet, empty(address), _caller)
    return self._canManageWhitelist(c.isOwner, c.isManager, _action, c.whitelistPerms, c.globalWhitelistPerms)


@view
@internal
def _canManageWhitelist(
    _isOwner: bool,
    _isManager: bool,
    _action: wcs.WhitelistAction,
    _config: wcs.WhitelistPerms,
    _globalConfig: wcs.WhitelistPerms,
) -> bool:

    # owner can manage whitelist
    if _isOwner:
        return True

    # if not a manager, cannot manage whitelist
    if not _isManager:
        return False 

    # add to whitelist
    if _action == wcs.WhitelistAction.ADD_PENDING:
        return _config.canAddPending and _globalConfig.canAddPending
    
    # confirm whitelist
    elif _action == wcs.WhitelistAction.CONFIRM_WHITELIST:
        return _config.canConfirm and _globalConfig.canConfirm
    
    # cancel whitelist
    elif _action == wcs.WhitelistAction.CANCEL_WHITELIST:
        return _config.canCancel and _globalConfig.canCancel
    
    # remove from whitelist
    elif _action == wcs.WhitelistAction.REMOVE_WHITELIST:
        return _config.canRemove and _globalConfig.canRemove
    
    # invalid action
    else:
        return False


# get whitelist config


@view
@external
def getWhitelistConfig(_userWallet: address, _whitelistAddr: address, _caller: address) -> wcs.WhitelistConfigBundle:
    return self._getWhitelistConfig(_userWallet, _whitelistAddr, _caller)


@view
@internal
def _getWhitelistConfig(_userWallet: address, _whitelistAddr: address, _caller: address) -> wcs.WhitelistConfigBundle:
    walletConfig: address = staticcall UserWallet(_userWallet).walletConfig()
    managerSettings: wcs.ManagerSettings = staticcall UserWalletConfig(walletConfig).managerSettings(_caller)
    globalManagerSettings: wcs.GlobalManagerSettings = staticcall UserWalletConfig(walletConfig).globalManagerSettings()
    owner: address = staticcall UserWalletConfig(walletConfig).owner()

    return wcs.WhitelistConfigBundle(
        owner = owner,
        wallet = staticcall UserWalletConfig(walletConfig).wallet(),
        isWhitelisted = staticcall UserWalletConfig(walletConfig).indexOfWhitelist(_whitelistAddr) != 0,
        pendingWhitelist = staticcall UserWalletConfig(walletConfig).pendingWhitelist(_whitelistAddr),
        timeLock = staticcall UserWalletConfig(walletConfig).timeLock(),
        walletConfig = walletConfig,
        isManager = staticcall UserWalletConfig(walletConfig).indexOfManager(_caller) != 0,
        isOwner = _caller == owner,
        whitelistPerms = managerSettings.whitelistPerms,
        globalWhitelistPerms = globalManagerSettings.whitelistPerms,
    )


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


#####################
# Cheque Management #
#####################


@external
def createCheque(
    _userWallet: address,
    _recipient: address,
    _asset: address,
    _amount: uint256,
    _unlockNumBlocks: uint256,
    _expiryNumBlocks: uint256,
    _canManagerPay: bool,
    _canBePulled: bool,
) -> bool:
    assert self._isValidUserWallet(_userWallet) # dev: invalid user wallet

    # get cheque config / data
    config: wcs.ChequeManagementBundle = self._getChequeConfig(_userWallet, msg.sender, _recipient)
    
    # check if caller can create cheques
    assert self._canCreateCheque(
        config.owner == msg.sender,
        config.isCreatorManager,
        config.chequeSettings.canManagersCreateCheques,
        config.managerSettings,
    ) # dev: not authorized to create cheques
    
    # get USD value
    appraiser: address = staticcall Registry(UNDY_HQ).getAddr(APPRAISER_ID)
    usdValue: uint256 = extcall Appraiser(appraiser).updatePriceAndGetUsdValue(_asset, _amount)
    
    # validate and create cheque
    isValid: bool = False
    cheque: wcs.Cheque = empty(wcs.Cheque)
    updatedChequeData: wcs.ChequeData = empty(wcs.ChequeData)
    isValid, cheque, updatedChequeData = self._isValidNewCheque(
        config,
        _recipient,
        _asset,
        _amount,
        _unlockNumBlocks,
        _expiryNumBlocks,
        _canManagerPay,
        _canBePulled,
        msg.sender,
        usdValue,
    )
    assert isValid # dev: invalid cheque
    
    # save cheque
    extcall UserWalletConfig(config.walletConfig).createCheque(_recipient, cheque, updatedChequeData, config.isExistingCheque)
    log ChequeCreated(
        user = _userWallet,
        recipient = _recipient,
        asset = _asset,
        amount = _amount,
        usdValue = usdValue,
        unlockBlock = cheque.unlockBlock,
        expiryBlock = cheque.expiryBlock,
        canManagerPay = _canManagerPay,
        canBePulled = _canBePulled,
        creator = msg.sender,
    )
    
    return True


# can create cheque


@view
@internal
def canCreateCheque(_userWallet: address, _creator: address, _recipient: address) -> bool:
    config: wcs.ChequeManagementBundle = self._getChequeConfig(_userWallet, _creator, _recipient)
    return self._canCreateCheque(config.owner == msg.sender, config.isCreatorManager, config.chequeSettings.canManagersCreateCheques, config.managerSettings)


@view
@internal
def _canCreateCheque(
    _isCreatorOwner: bool,
    _isCreatorManager: bool,
    _canManagersCreateCheques: bool,
    _managerSettings: wcs.ManagerSettings,
) -> bool:

    # owner can always create cheques
    if _isCreatorOwner:
        return True
    
    # if not owner, must be a manager
    if not _isCreatorManager:
        return False
    
    # check global setting - can managers create cheques
    if not _canManagersCreateCheques:
        return False
    
    # check manager's specific transfer permissions
    if not _managerSettings.transferPerms.canCreateCheque:
        return False
    
    # check if manager is active (within start/expiry blocks)
    if _managerSettings.startBlock > block.number:
        return False
    if _managerSettings.expiryBlock != 0 and _managerSettings.expiryBlock <= block.number:
        return False
    
    return True


# is valid new cheque


@view
@external
def isValidNewCheque(
    _userWallet: address,
    _creator: address,
    _recipient: address,
    _asset: address,
    _amount: uint256,
    _usdValue: uint256,
    _unlockNumBlocks: uint256,
    _expiryNumBlocks: uint256,
    _canManagerPay: bool,
    _canBePulled: bool,
) -> (bool, wcs.Cheque, wcs.ChequeData):
    config: wcs.ChequeManagementBundle = self._getChequeConfig(_userWallet, _creator, _recipient)
    return self._isValidNewCheque(config, _recipient, _asset, _amount, _unlockNumBlocks, _expiryNumBlocks, _canManagerPay, _canBePulled, _creator, _usdValue)


@view
@internal
def _isValidNewCheque(
    _config: wcs.ChequeManagementBundle,
    _recipient: address,
    _asset: address,
    _amount: uint256,
    _unlockNumBlocks: uint256,
    _expiryNumBlocks: uint256,
    _canManagerPay: bool,
    _canBePulled: bool,
    _creator: address,
    _usdValue: uint256,
) -> (bool, wcs.Cheque, wcs.ChequeData):

    # validate recipient
    if _config.isRecipientOnWhitelist:
        return False, empty(wcs.Cheque), empty(wcs.ChequeData)
    if _recipient == empty(address):
        return False, empty(wcs.Cheque), empty(wcs.ChequeData)
    if _recipient in [_config.wallet, _config.walletConfig, _config.owner]:
        return False, empty(wcs.Cheque), empty(wcs.ChequeData)

    # validate asset and amount
    if _asset == empty(address):
        return False, empty(wcs.Cheque), empty(wcs.ChequeData)
    if _amount == 0:
        return False, empty(wcs.Cheque), empty(wcs.ChequeData)
    
    # check if asset is allowed
    if len(_config.chequeSettings.allowedAssets) != 0:
        if _asset not in _config.chequeSettings.allowedAssets:
            return False, empty(wcs.Cheque), empty(wcs.ChequeData)

    # validate canBePulled and canManagerPay against global settings
    if _canBePulled and not _config.chequeSettings.canBePulled:
        return False, empty(wcs.Cheque), empty(wcs.ChequeData)
    if _canManagerPay and not _config.chequeSettings.canManagerPay:
        return False, empty(wcs.Cheque), empty(wcs.ChequeData)

    # check max number of active cheques (only if creating new cheque, not replacing)
    if not _config.isExistingCheque and _config.chequeSettings.maxNumActiveCheques != 0:
        if _config.numActiveCheques >= _config.chequeSettings.maxNumActiveCheques:
            return False, empty(wcs.Cheque), empty(wcs.ChequeData)

    # get latest cheque data (with period reset if needed)
    chequeData: wcs.ChequeData = self._getLatestChequeData(_config.chequeData, _config.chequeSettings.periodLength)

    # check creation cooldown
    if _config.chequeSettings.createCooldownBlocks != 0 and chequeData.lastChequeCreatedBlock != 0:
        if block.number < chequeData.lastChequeCreatedBlock + _config.chequeSettings.createCooldownBlocks:
            return False, empty(wcs.Cheque), empty(wcs.ChequeData)

    # check max num cheques created per period
    if _config.chequeSettings.maxNumChequesCreatedPerPeriod != 0:
        if chequeData.numChequesCreatedInPeriod >= _config.chequeSettings.maxNumChequesCreatedPerPeriod:
            return False, empty(wcs.Cheque), empty(wcs.ChequeData)

    # if no usd value, return False
    if _usdValue == 0:
        return False, empty(wcs.Cheque), empty(wcs.ChequeData)

    # check max cheque USD value
    if _config.chequeSettings.maxChequeUsdValue != 0:
        if _usdValue > _config.chequeSettings.maxChequeUsdValue:
            return False, empty(wcs.Cheque), empty(wcs.ChequeData)

    # check per period created USD cap
    if _config.chequeSettings.perPeriodCreatedUsdCap != 0:
        if chequeData.totalUsdValueCreatedInPeriod + _usdValue > _config.chequeSettings.perPeriodCreatedUsdCap:
            return False, empty(wcs.Cheque), empty(wcs.ChequeData)

    # cannot be too long
    if _unlockNumBlocks > MAX_UNLOCK_BLOCKS:
        return False, empty(wcs.Cheque), empty(wcs.ChequeData)

    # calculate unlock block
    unlockBlock: uint256 = block.number + _unlockNumBlocks

    # apply time lock if USD value exceeds instant threshold
    if _config.chequeSettings.instantUsdThreshold != 0 and _usdValue > _config.chequeSettings.instantUsdThreshold:
        if _config.chequeSettings.expensiveDelayBlocks != 0:
            unlockBlock = max(unlockBlock, block.number + _config.chequeSettings.expensiveDelayBlocks)
        else:
            unlockBlock = max(unlockBlock, block.number + _config.timeLock)

    # calculate expiry block
    expiryBlock: uint256 = 0
    if _expiryNumBlocks != 0:
        expiryBlock = unlockBlock + _expiryNumBlocks
    elif _config.chequeSettings.defaultExpiryBlocks != 0:
        expiryBlock = unlockBlock + _config.chequeSettings.defaultExpiryBlocks
    else:
        expiryBlock = unlockBlock + _config.timeLock

    # cannot be too long (active duration)
    activeDuration: uint256 = expiryBlock - unlockBlock
    if activeDuration > MAX_EXPIRY_BLOCKS:
        return False, empty(wcs.Cheque), empty(wcs.ChequeData)

    # create cheque
    cheque: wcs.Cheque = wcs.Cheque(
        recipient = _recipient,
        asset = _asset,
        amount = _amount,
        creationBlock = block.number,
        unlockBlock = unlockBlock,
        expiryBlock = expiryBlock,
        usdValueOnCreation = _usdValue,
        canManagerPay = _canManagerPay,
        canBePulled = _canBePulled,
        creator = _creator,
        active = True,
    )

    # update cheque data
    chequeData.numChequesCreatedInPeriod += 1
    chequeData.totalUsdValueCreatedInPeriod += _usdValue
    chequeData.totalNumChequesCreated += 1
    chequeData.totalUsdValueCreated += _usdValue
    chequeData.lastChequeCreatedBlock = block.number

    return True, cheque, chequeData


# get latest cheque data (period reset)


@view
@internal
def _getLatestChequeData(_chequeData: wcs.ChequeData, _periodLength: uint256) -> wcs.ChequeData:
    chequeData: wcs.ChequeData = _chequeData
    
    # initialize period if first cheque
    if chequeData.periodStartBlock == 0:
        chequeData.periodStartBlock = block.number
    
    # check if current period has ended
    elif _periodLength != 0 and block.number >= chequeData.periodStartBlock + _periodLength:

        # reset paid period data
        chequeData.numChequesPaidInPeriod = 0
        chequeData.totalUsdValuePaidInPeriod = 0

        # reset created period data
        chequeData.numChequesCreatedInPeriod = 0
        chequeData.totalUsdValueCreatedInPeriod = 0
        chequeData.periodStartBlock = block.number
    
    return chequeData


# cancel cheque


@external
def cancelCheque(_userWallet: address, _recipient: address) -> bool:
    assert self._isValidUserWallet(_userWallet) # dev: invalid user wallet

    # get wallet config
    walletConfig: address = staticcall UserWallet(_userWallet).walletConfig()
    owner: address = staticcall UserWalletConfig(walletConfig).owner()

    # check permissions - only owner or security action can cancel
    if msg.sender != owner:
        assert self._canPerformSecurityAction(msg.sender) # dev: no perms

    # check if cheque exists
    cheque: wcs.Cheque = staticcall UserWalletConfig(walletConfig).cheques(_recipient)
    assert cheque.active # dev: no active cheque

    # cancel the cheque
    extcall UserWalletConfig(walletConfig).cancelCheque(_recipient)
    log ChequeCancelled(
        user = _userWallet,
        recipient = _recipient,
        asset = cheque.asset,
        amount = cheque.amount,
        usdValue = cheque.usdValueOnCreation,
        unlockBlock = cheque.unlockBlock,
        expiryBlock = cheque.expiryBlock,
        canManagerPay = cheque.canManagerPay,
        canBePulled = cheque.canBePulled,
        cancelledBy = msg.sender,
    )
    
    return True


###################
# Cheque Settings #
###################


# set cheque settings


@external
def setChequeSettings(
    _userWallet: address,
    _maxNumActiveCheques: uint256,
    _maxChequeUsdValue: uint256,
    _instantUsdThreshold: uint256,
    _perPeriodPaidUsdCap: uint256,
    _maxNumChequesPaidPerPeriod: uint256,
    _payCooldownBlocks: uint256,
    _perPeriodCreatedUsdCap: uint256,
    _maxNumChequesCreatedPerPeriod: uint256,
    _createCooldownBlocks: uint256,
    _periodLength: uint256,
    _expensiveDelayBlocks: uint256,
    _defaultExpiryBlocks: uint256,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
    _canManagersCreateCheques: bool,
    _canManagerPay: bool,
    _canBePulled: bool,
) -> bool:
    assert self._isValidUserWallet(_userWallet) # dev: invalid user wallet
    
    # only owner can set cheque settings
    walletConfig: address = staticcall UserWallet(_userWallet).walletConfig()
    assert msg.sender == staticcall UserWalletConfig(walletConfig).owner() # dev: no perms

    # validate cheque settings with timelock
    assert self._isValidChequeSettings(
        _maxNumActiveCheques,
        _maxChequeUsdValue,
        _instantUsdThreshold,
        _perPeriodPaidUsdCap,
        _maxNumChequesPaidPerPeriod,
        _payCooldownBlocks,
        _perPeriodCreatedUsdCap,
        _maxNumChequesCreatedPerPeriod,
        _createCooldownBlocks,
        _periodLength,
        _expensiveDelayBlocks,
        _defaultExpiryBlocks,
        staticcall UserWalletConfig(walletConfig).timeLock(),
    ) # dev: invalid cheque settings
    
    # create settings
    settings: wcs.ChequeSettings = wcs.ChequeSettings(
        maxNumActiveCheques = _maxNumActiveCheques,
        maxChequeUsdValue = _maxChequeUsdValue,
        instantUsdThreshold = _instantUsdThreshold,
        perPeriodPaidUsdCap = _perPeriodPaidUsdCap,
        maxNumChequesPaidPerPeriod = _maxNumChequesPaidPerPeriod,
        payCooldownBlocks = _payCooldownBlocks,
        perPeriodCreatedUsdCap = _perPeriodCreatedUsdCap,
        maxNumChequesCreatedPerPeriod = _maxNumChequesCreatedPerPeriod,
        createCooldownBlocks = _createCooldownBlocks,
        periodLength = _periodLength,
        expensiveDelayBlocks = _expensiveDelayBlocks,
        defaultExpiryBlocks = _defaultExpiryBlocks,
        allowedAssets = _allowedAssets,
        canManagersCreateCheques = _canManagersCreateCheques,
        canManagerPay = _canManagerPay,
        canBePulled = _canBePulled,
    )
    
    # update settings
    extcall UserWalletConfig(walletConfig).setChequeSettings(settings)
    
    log ChequeSettingsModified(
        user = _userWallet,
        maxNumActiveCheques = _maxNumActiveCheques,
        maxChequeUsdValue = _maxChequeUsdValue,
        instantUsdThreshold = _instantUsdThreshold,
        perPeriodPaidUsdCap = _perPeriodPaidUsdCap,
        maxNumChequesPaidPerPeriod = _maxNumChequesPaidPerPeriod,
        payCooldownBlocks = _payCooldownBlocks,
        perPeriodCreatedUsdCap = _perPeriodCreatedUsdCap,
        maxNumChequesCreatedPerPeriod = _maxNumChequesCreatedPerPeriod,
        createCooldownBlocks = _createCooldownBlocks,
        periodLength = _periodLength,
        expensiveDelayBlocks = _expensiveDelayBlocks,
        defaultExpiryBlocks = _defaultExpiryBlocks,
        canManagersCreateCheques = _canManagersCreateCheques,
        canManagerPay = _canManagerPay,
        canBePulled = _canBePulled,
    )
    
    return True


# cheque settings validation


@view
@external
def isValidChequeSettings(
    _userWallet: address,
    _maxNumActiveCheques: uint256,
    _maxChequeUsdValue: uint256,
    _instantUsdThreshold: uint256,
    _perPeriodPaidUsdCap: uint256,
    _maxNumChequesPaidPerPeriod: uint256,
    _payCooldownBlocks: uint256,
    _perPeriodCreatedUsdCap: uint256,
    _maxNumChequesCreatedPerPeriod: uint256,
    _createCooldownBlocks: uint256,
    _periodLength: uint256,
    _expensiveDelayBlocks: uint256,
    _defaultExpiryBlocks: uint256,
    _timeLock: uint256,
) -> bool:
    return self._isValidChequeSettings(
        _maxNumActiveCheques,
        _maxChequeUsdValue,
        _instantUsdThreshold,
        _perPeriodPaidUsdCap,
        _maxNumChequesPaidPerPeriod,
        _payCooldownBlocks,
        _perPeriodCreatedUsdCap,
        _maxNumChequesCreatedPerPeriod,
        _createCooldownBlocks,
        _periodLength,
        _expensiveDelayBlocks,
        _defaultExpiryBlocks,
        _timeLock,
    )


@view
@internal
def _isValidChequeSettings(
    _maxNumActiveCheques: uint256,
    _maxChequeUsdValue: uint256,
    _instantUsdThreshold: uint256,
    _perPeriodPaidUsdCap: uint256,
    _maxNumChequesPaidPerPeriod: uint256,
    _payCooldownBlocks: uint256,
    _perPeriodCreatedUsdCap: uint256,
    _maxNumChequesCreatedPerPeriod: uint256,
    _createCooldownBlocks: uint256,
    _periodLength: uint256,
    _expensiveDelayBlocks: uint256,
    _defaultExpiryBlocks: uint256,
    _timeLock: uint256,
) -> bool:

    # validate period length
    if not self._isValidChequePeriod(_periodLength):
        return False
    
    # validate cooldowns
    if not self._isValidChequeCooldowns(_payCooldownBlocks, _createCooldownBlocks, _periodLength):
        return False
    
    # validate expensive delay
    if not self._isValidExpensiveDelay(_expensiveDelayBlocks, _timeLock):
        return False
    
    # validate USD caps consistency
    if not self._isValidChequeUsdCaps(_maxChequeUsdValue, _perPeriodPaidUsdCap, _perPeriodCreatedUsdCap):
        return False
    
    # validate instant threshold configuration
    if not self._isValidInstantThreshold(_instantUsdThreshold, _expensiveDelayBlocks):
        return False
    
    # validate expiry blocks
    if not self._isValidExpiryBlocks(_defaultExpiryBlocks, _timeLock):
        return False
    
    return True


# validate cheque period


@view
@internal
def _isValidChequePeriod(_periodLength: uint256) -> bool:
    # period length cannot be zero
    if _periodLength == 0:
        return False
    return _periodLength >= MIN_CHEQUE_PERIOD and _periodLength <= MAX_CHEQUE_PERIOD


# validate cheque cooldowns


@view
@internal
def _isValidChequeCooldowns(_payCooldownBlocks: uint256, _createCooldownBlocks: uint256, _periodLength: uint256) -> bool:
    # cooldowns cannot exceed period length
    if _payCooldownBlocks > _periodLength:
        return False
    if _createCooldownBlocks > _periodLength:
        return False
    
    return True


# validate expensive delay


@view
@internal
def _isValidExpensiveDelay(_expensiveDelayBlocks: uint256, _timeLock: uint256) -> bool:
    # NOTE: When set to zero, expensive cheque delay will use UserWalletConfig.timeLock()
    if _expensiveDelayBlocks == 0:
        return True

    # must meet minimum and cannot be less than current timelock
    if _expensiveDelayBlocks < MIN_EXPENSIVE_CHEQUE_DELAY:
        return False
    if _expensiveDelayBlocks < _timeLock:
        return False

    # cannot exceed maximum unlock blocks
    if _expensiveDelayBlocks > MAX_UNLOCK_BLOCKS:
        return False
    return True


# validate cheque USD caps consistency


@view
@internal
def _isValidChequeUsdCaps(_maxChequeUsdValue: uint256, _perPeriodPaidUsdCap: uint256, _perPeriodCreatedUsdCap: uint256) -> bool:
    if _maxChequeUsdValue == 0:
        return True
    
    # per-cheque cap should not exceed period caps
    if _perPeriodPaidUsdCap != 0 and _maxChequeUsdValue > _perPeriodPaidUsdCap:
        return False
    if _perPeriodCreatedUsdCap != 0 and _maxChequeUsdValue > _perPeriodCreatedUsdCap:
        return False
    
    return True


# validate instant threshold configuration


@view
@internal
def _isValidInstantThreshold(_instantUsdThreshold: uint256, _expensiveDelayBlocks: uint256) -> bool:
    # instant threshold cannot be zero
    if _instantUsdThreshold == 0:
        return False
    # if instant threshold is set, expensive delay must be set
    if _expensiveDelayBlocks == 0:
        return False
    return True


# validate expiry blocks


@view
@internal
def _isValidExpiryBlocks(_defaultExpiryBlocks: uint256, _timeLock: uint256) -> bool:
    # NOTE: When set to zero, expiry blocks will use UserWalletConfig.timeLock()
    if _defaultExpiryBlocks == 0:
        return True
    if _defaultExpiryBlocks > MAX_EXPIRY_BLOCKS:
        return False
    if _defaultExpiryBlocks < _timeLock:
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


# get cheque management bundle


@view
@external
def getChequeConfig(_userWallet: address, _creator: address, _recipient: address) -> wcs.ChequeManagementBundle:
    return self._getChequeConfig(_userWallet, _creator, _recipient)


@view
@internal
def _getChequeConfig(_userWallet: address, _creator: address, _recipient: address) -> wcs.ChequeManagementBundle:
    walletConfig: address = staticcall UserWallet(_userWallet).walletConfig()
    cheque: wcs.Cheque = staticcall UserWalletConfig(walletConfig).cheques(_recipient)
    return wcs.ChequeManagementBundle(
        wallet = _userWallet,
        walletConfig = walletConfig,
        owner = staticcall UserWalletConfig(walletConfig).owner(),
        isRecipientOnWhitelist = staticcall UserWalletConfig(walletConfig).indexOfWhitelist(_recipient) != 0,
        isCreatorManager = staticcall UserWalletConfig(walletConfig).indexOfManager(_creator) != 0,
        managerSettings = staticcall UserWalletConfig(walletConfig).managerSettings(_creator),
        chequeSettings = staticcall UserWalletConfig(walletConfig).chequeSettings(),
        chequeData = staticcall UserWalletConfig(walletConfig).chequePeriodData(),
        isExistingCheque = cheque.active,
        numActiveCheques = staticcall UserWalletConfig(walletConfig).numActiveCheques(),
        timeLock = staticcall UserWalletConfig(walletConfig).timeLock(),
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
