# @version 0.4.3
# pragma optimize codesize

from interfaces import WalletConfigStructs as wcs

interface UserWalletConfig:
    def getWhitelistConfigBundle(_addr: address, _signer: address) -> wcs.WhitelistConfigBundle: view
    def addPendingWhitelistAddr(_addr: address, _pending: wcs.PendingWhitelist): nonpayable
    def getPayeeManagementBundle(_payee: address) -> wcs.PayeeManagementBundle: view
    def getRecipientConfigs(_recipient: address) -> wcs.RecipientConfigBundle: view
    def addPendingPayee(_payee: address, _pending: wcs.PendingPayee): nonpayable
    def setGlobalPayeeSettings(_config: wcs.GlobalPayeeSettings): nonpayable
    def updatePayee(_payee: address, _config: wcs.PayeeSettings): nonpayable
    def addPayee(_payee: address, _config: wcs.PayeeSettings): nonpayable
    def cancelPendingWhitelistAddr(_addr: address): nonpayable
    def pendingPayees(_payee: address) -> wcs.PendingPayee: view
    def canAddPendingPayee(_caller: address) -> bool: view
    def confirmWhitelistAddr(_addr: address): nonpayable
    def confirmPendingPayee(_payee: address): nonpayable
    def removeWhitelistAddr(_addr: address): nonpayable
    def cancelPendingPayee(_payee: address): nonpayable
    def removePayee(_payee: address): nonpayable

interface Switchboard:
    def isSwitchboardAddr(_addr: address) -> bool: view

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
SWITCHBOARD_ID: constant(uint256) = 5

# payee validation bounds
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

    MAX_START_DELAY = _maxStartDelay


########################
# Recipient Validation #
########################


# is valid payee


@view
@external
def isValidPayee(
    _user: address,
    _recipient: address,
    _asset: address,
    _amount: uint256,
    _txUsdValue: uint256,
) -> bool:
    userWalletConfig: address = staticcall UserWallet(_user).walletConfig()
    c: wcs.RecipientConfigBundle = staticcall UserWalletConfig(userWalletConfig).getRecipientConfigs(_recipient)
    canPay: bool = False
    na: wcs.PayeeData = empty(wcs.PayeeData)
    canPay, na = self._isValidPayeeAndGetData(c.isWhitelisted, c.isOwner, c.isPayee, _asset, _amount, _txUsdValue, c.config, c.globalConfig, c.data)
    return canPay


# is valid payee (with config)


@view
@external
def isValidPayeeAndGetData(
    _isWhitelisted: bool,
    _isOwner: bool,
    _isPayee: bool,
    _asset: address,
    _amount: uint256,
    _txUsdValue: uint256,
    _config: wcs.PayeeSettings,
    _globalConfig: wcs.GlobalPayeeSettings,
    _payeeData: wcs.PayeeData,
) -> (bool, wcs.PayeeData):
    return self._isValidPayeeAndGetData(_isWhitelisted, _isOwner, _isPayee, _asset, _amount, _txUsdValue, _config, _globalConfig, _payeeData)


# core logic -- is valid payee


@view
@internal
def _isValidPayeeAndGetData(
    _isWhitelisted: bool,
    _isOwner: bool,
    _isPayee: bool,
    _asset: address,
    _amount: uint256,
    _txUsdValue: uint256,
    _payeeConfig: wcs.PayeeSettings,
    _globalConfig: wcs.GlobalPayeeSettings,
    _payeeData: wcs.PayeeData,
) -> (bool, wcs.PayeeData):

    # whitelisted
    if _isWhitelisted:
        return True, empty(wcs.PayeeData)

    # check if recipient is owner
    if _isOwner and _globalConfig.canPayOwner:
        return True, empty(wcs.PayeeData)

    # registered payee
    if not _isPayee:
        return False, empty(wcs.PayeeData)

    # get payee data
    payeeData: wcs.PayeeData = self._getLatestPayeeData(_payeeData, _payeeConfig.periodLength)

    # check specific payee settings
    if not self._checkSpecificPayeeSettings(_asset, _amount, _txUsdValue, payeeData, _payeeConfig):
        return False, empty(wcs.PayeeData)

    # check global payee settings
    if not self._checkGlobalPayeeSettings(_txUsdValue, payeeData, _globalConfig):
        return False, empty(wcs.PayeeData)

    # update payee data
    payeeData.numTxsInPeriod += 1
    payeeData.totalUsdValueInPeriod += _txUsdValue
    payeeData.totalNumTxs += 1
    payeeData.totalUsdValue += _txUsdValue
    payeeData.lastTxBlock = block.number
    
    # update unit amounts if this is the primary asset
    if _payeeConfig.primaryAsset == _asset:
        payeeData.totalUnitsInPeriod += _amount
        payeeData.totalUnits += _amount

    return True, payeeData


# specific payee settings


@view
@internal
def _checkSpecificPayeeSettings(
    _asset: address,
    _amount: uint256,
    _txUsdValue: uint256,
    _payeeData: wcs.PayeeData,
    _payeeConfig: wcs.PayeeSettings,
) -> bool:

    # check zero price
    if _txUsdValue == 0 and _payeeConfig.failOnZeroPrice:
        return False

    # is payee active
    if _payeeConfig.startBlock > block.number or _payeeConfig.expiryBlock <= block.number:
        return False
    
    # check if asset is allowed
    if _payeeConfig.onlyPrimaryAsset and _payeeConfig.primaryAsset != empty(address):
        if _payeeConfig.primaryAsset != _asset:
            return False

    # check transaction limits
    if not self._checkTransactionLimits(_payeeConfig.maxNumTxsPerPeriod, _payeeConfig.txCooldownBlocks, _payeeData.numTxsInPeriod, _payeeData.lastTxBlock):
        return False

    # check USD limits 
    if not self._checkUsdLimits(_txUsdValue, _payeeConfig.usdLimits, _payeeData):
        return False

    # check unit limits if this is the primary asset
    if _payeeConfig.primaryAsset == _asset:
        if not self._checkUnitLimits(_amount, _payeeConfig.unitLimits, _payeeData):
            return False

    return True


# global payee settings


@view
@internal
def _checkGlobalPayeeSettings(
    _txUsdValue: uint256,
    _payeeData: wcs.PayeeData,
    _globalConfig: wcs.GlobalPayeeSettings,
) -> bool:

    # check zero price
    if _txUsdValue == 0 and _globalConfig.failOnZeroPrice:
        return False

    # check transaction limits
    if not self._checkTransactionLimits(_globalConfig.maxNumTxsPerPeriod, _globalConfig.txCooldownBlocks, _payeeData.numTxsInPeriod, _payeeData.lastTxBlock):
        return False

    # check USD limits
    if not self._checkUsdLimits(_txUsdValue, _globalConfig.usdLimits, _payeeData):
        return False

    return True


# get latest payee data (period reset)


@view
@internal
def _getLatestPayeeData(_payeeData: wcs.PayeeData, _periodLength: uint256) -> wcs.PayeeData:
    payeeData: wcs.PayeeData = _payeeData
    
    # initialize period if first transaction
    if payeeData.periodStartBlock == 0:
        payeeData.periodStartBlock = block.number
    
    # check if current period has ended
    elif block.number >= payeeData.periodStartBlock + _periodLength:
        payeeData.numTxsInPeriod = 0
        payeeData.totalUnitsInPeriod = 0
        payeeData.totalUsdValueInPeriod = 0
        payeeData.periodStartBlock = block.number
    
    return payeeData


# check USD limits


@view
@internal
def _checkUsdLimits(_txUsdValue: uint256, _limits: wcs.PayeeLimits, _payeeData: wcs.PayeeData) -> bool:
    if _limits.perTxCap != 0:
        if _txUsdValue > _limits.perTxCap:
            return False
    
    if _limits.perPeriodCap != 0:
        if _payeeData.totalUsdValueInPeriod + _txUsdValue > _limits.perPeriodCap:
            return False
    
    if _limits.lifetimeCap != 0:
        if _payeeData.totalUsdValue + _txUsdValue > _limits.lifetimeCap:
            return False
    
    return True


# check unit limits


@view
@internal
def _checkUnitLimits(_amount: uint256, _limits: wcs.PayeeLimits, _payeeData: wcs.PayeeData) -> bool:
    if _limits.perTxCap != 0:
        if _amount > _limits.perTxCap:
            return False
    
    if _limits.perPeriodCap != 0:
        if _payeeData.totalUnitsInPeriod + _amount > _limits.perPeriodCap:
            return False
    
    if _limits.lifetimeCap != 0:
        if _payeeData.totalUnits + _amount > _limits.lifetimeCap:
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
    if _maxNumTxsPerPeriod != 0:
        if _numTxsInPeriod >= _maxNumTxsPerPeriod:
            return False
    
    if _txCooldownBlocks != 0 and _lastTxBlock != 0:
        if _lastTxBlock + _txCooldownBlocks > block.number:
            return False
    
    return True


####################
# Payee Management #
####################


# add payee


@external
def addPayee(
    _user: address,
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
    bundle: wcs.PayeeManagementBundle = self._validateAndGetPayeeManagementBundle(_user, _payee)
    assert msg.sender == bundle.owner # dev: no perms

    # prepare and validate payee settings
    config: wcs.PayeeSettings = self._validateAndPrepareNewPayeeConfig(
        _payee,
        bundle,
        _canPull,
        _periodLength,
        _maxNumTxsPerPeriod,
        _txCooldownBlocks,
        _failOnZeroPrice,
        _primaryAsset,
        _onlyPrimaryAsset,
        _unitLimits,
        _usdLimits,
        _startDelay,
        _activationLength,
    )

    # add payee to wallet config
    extcall UserWalletConfig(bundle.walletConfig).addPayee(_payee, config)
    log PayeeAdded(
        user = _user,
        payee = _payee,
        startBlock = config.startBlock,
        expiryBlock = config.expiryBlock,
        canPull = config.canPull,
        periodLength = config.periodLength,
        maxNumTxsPerPeriod = config.maxNumTxsPerPeriod,
        txCooldownBlocks = config.txCooldownBlocks,
        failOnZeroPrice = config.failOnZeroPrice,
        primaryAsset = config.primaryAsset,
        onlyPrimaryAsset = config.onlyPrimaryAsset,
        unitPerTxCap = config.unitLimits.perTxCap,
        unitPerPeriodCap = config.unitLimits.perPeriodCap,
        unitLifetimeCap = config.unitLimits.lifetimeCap,
        usdPerTxCap = config.usdLimits.perTxCap,
        usdPerPeriodCap = config.usdLimits.perPeriodCap,
        usdLifetimeCap = config.usdLimits.lifetimeCap,
    )
    return True


# prepare and validate payee settings


@view
@internal
def _validateAndPrepareNewPayeeConfig(
    _payee: address,
    _bundle: wcs.PayeeManagementBundle,
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
) -> wcs.PayeeSettings:
    assert _payee not in [empty(address), _bundle.wallet, _bundle.owner, _bundle.walletConfig] # dev: invalid payee
    assert not _bundle.isRegisteredPayee # dev: payee already exists
    assert not _bundle.isWhitelisted # dev: already whitelisted
    
    # calculate start delay
    startDelay: uint256 = max(_bundle.globalPayeeSettings.startDelay, _bundle.timeLock)
    if _startDelay != 0:
        startDelay = max(startDelay, _startDelay)

    # calculate activation length
    activationLength: uint256 = _bundle.globalPayeeSettings.activationLength
    if _activationLength != 0:
        activationLength = min(activationLength, _activationLength)

    # use global default period length if not specified
    periodLength: uint256 = _periodLength
    if periodLength == 0:
        periodLength = _bundle.globalPayeeSettings.defaultPeriodLength

    # validate the settings
    assert (
        self._validateStartDelay(startDelay, _bundle.timeLock) and
        self._validatePayeePeriod(periodLength) and
        self._validateActivationLength(activationLength) and
        self._validatePayeeCooldown(_txCooldownBlocks, periodLength) and
        self._validatePrimaryAsset(_primaryAsset, _onlyPrimaryAsset) and
        self._validatePayeeLimits(_unitLimits) and
        self._validatePayeeLimits(_usdLimits) and
        self._validatePullPayee(_canPull, _unitLimits, _usdLimits)
    ) # dev: invalid settings

    # create start and expiry blocks
    startBlock: uint256 = block.number + startDelay
    expiryBlock: uint256 = startBlock + activationLength

    return wcs.PayeeSettings(
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


# update existing payee


@external
def updatePayee(
    _user: address,
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
    bundle: wcs.PayeeManagementBundle = self._validateAndGetPayeeManagementBundle(_user, _payee)
    assert msg.sender == bundle.owner # dev: no perms

    # validate payee exists
    assert bundle.isRegisteredPayee # dev: payee not found

    # update config while preserving start/expiry blocks
    updatedConfig: wcs.PayeeSettings = wcs.PayeeSettings(
        startBlock = bundle.payeeSettings.startBlock,
        expiryBlock = bundle.payeeSettings.expiryBlock,
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

    # validate the updated settings (skip timing validation)
    assert (
        self._validatePayeePeriod(updatedConfig.periodLength) and
        self._validatePayeeCooldown(updatedConfig.txCooldownBlocks, updatedConfig.periodLength) and
        self._validatePrimaryAsset(updatedConfig.primaryAsset, updatedConfig.onlyPrimaryAsset) and
        self._validatePayeeLimits(updatedConfig.unitLimits) and
        self._validatePayeeLimits(updatedConfig.usdLimits) and
        self._validatePullPayee(updatedConfig.canPull, updatedConfig.unitLimits, updatedConfig.usdLimits)
    ) # dev: invalid settings

    # update payee in wallet config
    extcall UserWalletConfig(bundle.walletConfig).updatePayee(_payee, updatedConfig)
    log PayeeUpdated(
        user = _user,
        payee = _payee,
        startBlock = updatedConfig.startBlock,
        expiryBlock = updatedConfig.expiryBlock,
        canPull = updatedConfig.canPull,
        periodLength = updatedConfig.periodLength,
        maxNumTxsPerPeriod = updatedConfig.maxNumTxsPerPeriod,
        txCooldownBlocks = updatedConfig.txCooldownBlocks,
        failOnZeroPrice = updatedConfig.failOnZeroPrice,
        primaryAsset = updatedConfig.primaryAsset,
        onlyPrimaryAsset = updatedConfig.onlyPrimaryAsset,
        unitPerTxCap = updatedConfig.unitLimits.perTxCap,
        unitPerPeriodCap = updatedConfig.unitLimits.perPeriodCap,
        unitLifetimeCap = updatedConfig.unitLimits.lifetimeCap,
        usdPerTxCap = updatedConfig.usdLimits.perTxCap,
        usdPerPeriodCap = updatedConfig.usdLimits.perPeriodCap,
        usdLifetimeCap = updatedConfig.usdLimits.lifetimeCap,
    )
    return True


# remove payee


@external
def removePayee(_user: address, _payee: address) -> bool:
    bundle: wcs.PayeeManagementBundle = self._validateAndGetPayeeManagementBundle(_user, _payee)
    if msg.sender not in [bundle.owner, _payee]:
        assert self._isSwitchboardAddr(msg.sender, bundle.inEjectMode) # dev: no perms

    # validate payee exists
    assert bundle.isRegisteredPayee # dev: payee not found

    # remove payee from wallet config
    extcall UserWalletConfig(bundle.walletConfig).removePayee(_payee)
    log PayeeRemoved(user = _user, payee = _payee)
    return True


# add pending payee (for managers)


@external
def addPendingPayee(
    _user: address,
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
    bundle: wcs.PayeeManagementBundle = self._validateAndGetPayeeManagementBundle(_user, _payee)
    assert staticcall UserWalletConfig(bundle.walletConfig).canAddPendingPayee(msg.sender) # dev: no permission to add pending payee

    # check if pending payee already exists
    pendingPayee: wcs.PendingPayee = staticcall UserWalletConfig(bundle.walletConfig).pendingPayees(_payee)
    assert pendingPayee.initiatedBlock == 0 # dev: pending payee already exists

    # validate and prepare payee settings
    config: wcs.PayeeSettings = self._validateAndPrepareNewPayeeConfig(
        _payee,
        bundle,
        _canPull,
        _periodLength,
        _maxNumTxsPerPeriod,
        _txCooldownBlocks,
        _failOnZeroPrice,
        _primaryAsset,
        _onlyPrimaryAsset,
        _unitLimits,
        _usdLimits,
        _startDelay,
        _activationLength,
    )

    # create pending payee with timelock
    confirmBlock: uint256 = block.number + bundle.timeLock
    pending: wcs.PendingPayee = wcs.PendingPayee(
        settings = config,
        initiatedBlock = block.number,
        confirmBlock = confirmBlock,
    )
    extcall UserWalletConfig(bundle.walletConfig).addPendingPayee(_payee, pending)

    log PayeePending(
        user = _user,
        payee = _payee,
        confirmBlock = confirmBlock,
        addedBy = msg.sender,
        canPull = config.canPull,
        periodLength = config.periodLength,
        maxNumTxsPerPeriod = config.maxNumTxsPerPeriod,
        txCooldownBlocks = config.txCooldownBlocks,
        failOnZeroPrice = config.failOnZeroPrice,
        primaryAsset = config.primaryAsset,
        onlyPrimaryAsset = config.onlyPrimaryAsset,
        unitPerTxCap = config.unitLimits.perTxCap,
        unitPerPeriodCap = config.unitLimits.perPeriodCap,
        unitLifetimeCap = config.unitLimits.lifetimeCap,
        usdPerTxCap = config.usdLimits.perTxCap,
        usdPerPeriodCap = config.usdLimits.perPeriodCap,
        usdLifetimeCap = config.usdLimits.lifetimeCap,
    )
    return True


# confirm pending payee (for owner)


@external
def confirmPendingPayee(_user: address, _payee: address) -> bool:
    bundle: wcs.PayeeManagementBundle = self._validateAndGetPayeeManagementBundle(_user, _payee)
    assert msg.sender == bundle.owner # dev: no perms
    
    # get pending payee
    pendingPayee: wcs.PendingPayee = staticcall UserWalletConfig(bundle.walletConfig).pendingPayees(_payee)
    assert pendingPayee.initiatedBlock != 0 # dev: no pending payee
    assert pendingPayee.confirmBlock != 0 and block.number >= pendingPayee.confirmBlock # dev: time delay not reached
    
    # confirm the pending payee
    extcall UserWalletConfig(bundle.walletConfig).confirmPendingPayee(_payee)
    log PayeePendingConfirmed(
        user = _user,
        payee = _payee,
        initiatedBlock = pendingPayee.initiatedBlock,
        confirmBlock = pendingPayee.confirmBlock,
        confirmedBy = msg.sender
    )
    return True


# cancel pending payee


@external
def cancelPendingPayee(_user: address, _payee: address) -> bool:
    bundle: wcs.PayeeManagementBundle = self._validateAndGetPayeeManagementBundle(_user, _payee)
    if msg.sender != bundle.owner and not self._isSwitchboardAddr(msg.sender, bundle.inEjectMode):
        assert staticcall UserWalletConfig(bundle.walletConfig).canAddPendingPayee(msg.sender) # dev: no permission to cancel pending payee

    # get pending payee
    pendingPayee: wcs.PendingPayee = staticcall UserWalletConfig(bundle.walletConfig).pendingPayees(_payee)
    assert pendingPayee.initiatedBlock != 0 # dev: no pending payee

    # cancel the pending payee
    extcall UserWalletConfig(bundle.walletConfig).cancelPendingPayee(_payee)
    log PayeePendingCancelled(
        user = _user,
        payee = _payee,
        initiatedBlock = pendingPayee.initiatedBlock,
        confirmBlock = pendingPayee.confirmBlock,
        cancelledBy = msg.sender
    )
    return True


#########################
# Global Payee Settings #
#########################


@external
def setGlobalPayeeSettings(
    _user: address,
    _defaultPeriodLength: uint256,
    _startDelay: uint256,
    _activationLength: uint256,
    _maxNumTxsPerPeriod: uint256,
    _txCooldownBlocks: uint256,
    _failOnZeroPrice: bool,
    _usdLimits: wcs.PayeeLimits,
    _canPayOwner: bool,
) -> bool:
    bundle: wcs.PayeeManagementBundle = self._validateAndGetPayeeManagementBundle(_user, empty(address))
    assert msg.sender == bundle.owner # dev: no perms

    # create config struct
    config: wcs.GlobalPayeeSettings = wcs.GlobalPayeeSettings(
        defaultPeriodLength = _defaultPeriodLength,
        startDelay = _startDelay,
        activationLength = _activationLength,
        maxNumTxsPerPeriod = _maxNumTxsPerPeriod,
        txCooldownBlocks = _txCooldownBlocks,
        failOnZeroPrice = _failOnZeroPrice,
        usdLimits = _usdLimits,
        canPayOwner = _canPayOwner,
    )

    # validate global settings
    assert (
        self._validatePayeePeriod(config.defaultPeriodLength) and
        self._validateActivationLength(config.activationLength) and
        self._validateTimeLock(config.startDelay, bundle.timeLock) and
        self._validatePayeeCooldown(config.txCooldownBlocks, config.defaultPeriodLength) and
        self._validatePayeeLimits(config.usdLimits)
    ) # dev: invalid settings

    # set global settings in wallet config
    extcall UserWalletConfig(bundle.walletConfig).setGlobalPayeeSettings(config)
    log GlobalPayeeSettingsModified(
        user = _user,
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


# create default global payee settings


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
        maxNumTxsPerPeriod = 0, # unlimited by default
        txCooldownBlocks = 0, # no cooldown by default
        failOnZeroPrice = False, # accept zero-priced transactions by default
        usdLimits = empty(wcs.PayeeLimits),
        canPayOwner = True, # allow payments to owner by default
    )


######################
# Payee Config Utils #
######################


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


@view
@internal
def _validateTimeLock(_timeLock: uint256, _currentTimeLock: uint256) -> bool:
    return _timeLock <= MAX_START_DELAY and _timeLock >= _currentTimeLock


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


# validate and get payee management bundle


@view
@internal
def _validateAndGetPayeeManagementBundle(_user: address, _payee: address) -> wcs.PayeeManagementBundle:
    ledger: address = staticcall Registry(UNDY_HQ).getAddr(LEDGER_ID)
    assert staticcall Ledger(ledger).isUserWallet(_user) # dev: not a user wallet
    walletConfig: address = staticcall UserWallet(_user).walletConfig()
    return staticcall UserWalletConfig(walletConfig).getPayeeManagementBundle(_payee)


# is signer switchboard


@view
@internal
def _isSwitchboardAddr(_signer: address, _inEjectMode: bool) -> bool:
    if _inEjectMode:
        return False
    switchboard: address = staticcall Registry(UNDY_HQ).getAddr(SWITCHBOARD_ID)
    return staticcall Switchboard(switchboard).isSwitchboardAddr(_signer)


########################
# Whitelist Management #
########################


# add whitelist


@external
def addWhitelistAddr(_user: address, _addr: address):
    c: wcs.WhitelistConfigBundle = self._validateAndGetWhitelistConfig(_user, _addr, msg.sender)
    assert self._canManageWhitelist(c.isOwner, c.isManager, wcs.WhitelistAction.ADD_WHITELIST, c.whitelistPerms, c.globalWhitelistPerms) # dev: no perms

    assert _addr not in [empty(address), c.wallet, c.owner, c.walletConfig] # dev: invalid addr
    assert not c.isWhitelisted # dev: already whitelisted
    assert c.pendingWhitelist.initiatedBlock == 0 # dev: pending whitelist already exists

    # this uses same delay as ownership change
    confirmBlock: uint256 = block.number + c.timeLock
    c.pendingWhitelist = wcs.PendingWhitelist(
        initiatedBlock = block.number,
        confirmBlock = confirmBlock,
    )
    extcall UserWalletConfig(c.walletConfig).addPendingWhitelistAddr(_addr, c.pendingWhitelist)
    log WhitelistAddrPending(user = _user, addr = _addr, confirmBlock = confirmBlock, addedBy = msg.sender)


# confirm whitelist


@external
def confirmWhitelistAddr(_user: address, _addr: address):
    c: wcs.WhitelistConfigBundle = self._validateAndGetWhitelistConfig(_user, _addr, msg.sender)
    assert self._canManageWhitelist(c.isOwner, c.isManager, wcs.WhitelistAction.CONFIRM_WHITELIST, c.whitelistPerms, c.globalWhitelistPerms) # dev: no perms

    assert c.pendingWhitelist.initiatedBlock != 0 # dev: no pending whitelist
    assert c.pendingWhitelist.confirmBlock != 0 and block.number >= c.pendingWhitelist.confirmBlock # dev: time delay not reached

    extcall UserWalletConfig(c.walletConfig).confirmWhitelistAddr(_addr)
    log WhitelistAddrConfirmed(user = _user, addr = _addr, initiatedBlock = c.pendingWhitelist.initiatedBlock, confirmBlock = c.pendingWhitelist.confirmBlock, confirmedBy = msg.sender)


# cancel pending whitelist


@external
def cancelPendingWhitelistAddr(_user: address, _addr: address):
    c: wcs.WhitelistConfigBundle = self._validateAndGetWhitelistConfig(_user, _addr, msg.sender)
    if not self._canManageWhitelist(c.isOwner, c.isManager, wcs.WhitelistAction.CANCEL_WHITELIST, c.whitelistPerms, c.globalWhitelistPerms):
        assert self._isSwitchboardAddr(msg.sender, c.inEjectMode) # dev: no perms

    assert c.pendingWhitelist.initiatedBlock != 0 # dev: no pending whitelist
    extcall UserWalletConfig(c.walletConfig).cancelPendingWhitelistAddr(_addr)
    log WhitelistAddrCancelled(user = _user, addr = _addr, initiatedBlock = c.pendingWhitelist.initiatedBlock, confirmBlock = c.pendingWhitelist.confirmBlock, cancelledBy = msg.sender)


# remove whitelist


@external
def removeWhitelistAddr(_user: address, _addr: address):
    c: wcs.WhitelistConfigBundle = self._validateAndGetWhitelistConfig(_user, _addr, msg.sender)
    if not self._canManageWhitelist(c.isOwner, c.isManager, wcs.WhitelistAction.REMOVE_WHITELIST, c.whitelistPerms, c.globalWhitelistPerms):
        assert self._isSwitchboardAddr(msg.sender, c.inEjectMode) or msg.sender == _addr # dev: no perms

    assert c.isWhitelisted # dev: not whitelisted
    extcall UserWalletConfig(c.walletConfig).removeWhitelistAddr(_addr)
    log WhitelistAddrRemoved(user = _user, addr = _addr, removedBy = msg.sender)


# can manage whitelist


@view
@internal
def _canManageWhitelist(
    _isOwner: bool,
    _isManager: bool,
    _action: wcs.WhitelistAction,
    _config: wcs.WhitelistPerms,
    _globalConfig: wcs.WhitelistPerms,
) -> bool:

    # check if signer is the owner
    if _isOwner:
        return True

    # check if signer is a manager
    if not _isManager:
        return False 

    # add to whitelist
    if _action == wcs.WhitelistAction.ADD_WHITELIST:
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


# validation and get wallet config


@view
@internal
def _validateAndGetWhitelistConfig(_user: address, _addr: address, _signer: address) -> wcs.WhitelistConfigBundle:
    ledger: address = staticcall Registry(UNDY_HQ).getAddr(LEDGER_ID)
    assert staticcall Ledger(ledger).isUserWallet(_user) # dev: not a user wallet
    walletConfig: address = staticcall UserWallet(_user).walletConfig()
    return staticcall UserWalletConfig(walletConfig).getWhitelistConfigBundle(_addr, _signer)
