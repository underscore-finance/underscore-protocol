# @version 0.4.3
# pragma optimize codesize

from interfaces import WalletStructs as ws
from interfaces import WalletConfigStructs as wcs

interface UserWalletConfig:
    def getManagerSettingsBundle(_manager: address) -> wcs.ManagerSettingsBundle: view
    def updateManager(_manager: address, _config: wcs.ManagerSettings): nonpayable
    def setGlobalManagerSettings(_config: wcs.GlobalManagerSettings): nonpayable
    def addManager(_manager: address, _config: wcs.ManagerSettings): nonpayable
    def getManagerConfigs(_signer: address, _transferRecipient: address = empty(address)) -> wcs.ManagerConfigBundle: view
    def managerSettings(_manager: address) -> wcs.ManagerSettings: view
    def globalManagerSettings() -> wcs.GlobalManagerSettings: view
    def isRegisteredPayee(_addr: address) -> bool: view
    def removeManager(_manager: address): nonpayable

interface Registry:
    def isValidRegId(_regId: uint256) -> bool: view
    def getAddr(_regId: uint256) -> address: view

interface Switchboard:
    def isSwitchboardAddr(_addr: address) -> bool: view

interface Ledger:
    def isUserWallet(_user: address) -> bool: view

interface UserWallet:
    def walletConfig() -> address: view

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
SWITCHBOARD_ID: constant(uint256) = 5

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


#########################
# Global Manager Config #
#########################


@view
@external
def validateGlobalManagerSettings(
    _settings: wcs.GlobalManagerSettings,
    _inEjectMode: bool,
    _currentTimeLock: uint256,
    _legoBookAddr: address,
    _walletConfig: address,
) -> bool:
    return self._validateGlobalManagerSettings(_settings, _inEjectMode, _currentTimeLock, _legoBookAddr, _walletConfig)


@view
@internal
def _validateGlobalManagerSettings(
    _settings: wcs.GlobalManagerSettings,
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


##################
# Manager Config #
##################


# create manager settings


@view
@external
def validateAndCreateManagerSettings(
    _startDelay: uint256,
    _activationLength: uint256,
    _limits: wcs.ManagerLimits,
    _legoPerms: wcs.LegoPerms,
    _whitelistPerms: wcs.WhitelistPerms,
    _transferPerms: wcs.TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
    _currentTimeLock: uint256,
    _config: wcs.GlobalManagerSettings,
    _inEjectMode: bool,
    _legoBookAddr: address,
    _walletConfig: address,
) -> wcs.ManagerSettings:
    return self._validateAndCreateManagerSettings(_startDelay, _activationLength, _limits, _legoPerms, _whitelistPerms, _transferPerms, _allowedAssets, _currentTimeLock, _config, _inEjectMode, _legoBookAddr, _walletConfig)


@view
@internal
def _validateAndCreateManagerSettings(
    _startDelay: uint256,
    _activationLength: uint256,
    _limits: wcs.ManagerLimits,
    _legoPerms: wcs.LegoPerms,
    _whitelistPerms: wcs.WhitelistPerms,
    _transferPerms: wcs.TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
    _currentTimeLock: uint256,
    _config: wcs.GlobalManagerSettings,
    _inEjectMode: bool,
    _legoBookAddr: address,
    _walletConfig: address,
) -> wcs.ManagerSettings:

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

    return wcs.ManagerSettings(
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
    _settings: wcs.ManagerSettings,
    _managerPeriod: uint256,
    _inEjectMode: bool,
    _legoBookAddr: address,
    _walletConfig: address,
) -> bool:
    return self._validateSpecificManagerSettings(_settings, _managerPeriod, _inEjectMode, _legoBookAddr, _walletConfig)


@view
@internal
def _validateSpecificManagerSettings(
    _settings: wcs.ManagerSettings,
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
def _validateManagerLimits(_limits: wcs.ManagerLimits, _managerPeriod: uint256) -> bool:
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
def _validateLegoPerms(_legoPerms: wcs.LegoPerms, _inEjectMode: bool, _legoBookAddr: address) -> bool:
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
def _validateTransferPerms(_transferPerms: wcs.TransferPerms, _walletConfig: address) -> bool:
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
    _limits: wcs.ManagerLimits,
    _legoPerms: wcs.LegoPerms,
    _whitelistPerms: wcs.WhitelistPerms,
    _transferPerms: wcs.TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
) -> bool:
    kconfig: wcs.ManagerSettingsBundle = self._validateAndGetConfig(_user, empty(address))
    assert msg.sender == kconfig.owner # dev: no perms

    config: wcs.GlobalManagerSettings = wcs.GlobalManagerSettings(
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
    _limits: wcs.ManagerLimits,
    _legoPerms: wcs.LegoPerms,
    _whitelistPerms: wcs.WhitelistPerms,
    _transferPerms: wcs.TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
    _startDelay: uint256 = 0,
    _activationLength: uint256 = 0,
) -> bool:
    kconfig: wcs.ManagerSettingsBundle = self._validateAndGetConfig(_user, _manager)
    assert msg.sender == kconfig.owner # dev: no perms

    assert _manager not in [empty(address), kconfig.owner] # dev: invalid manager
    assert not kconfig.isManager # dev: manager already exists
    
    config: wcs.ManagerSettings = self._validateAndCreateManagerSettings(
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
    _limits: wcs.ManagerLimits,
    _legoPerms: wcs.LegoPerms,
    _whitelistPerms: wcs.WhitelistPerms,
    _transferPerms: wcs.TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
) -> bool:
    kconfig: wcs.ManagerSettingsBundle = self._validateAndGetConfig(_user, _manager)
    assert msg.sender == kconfig.owner # dev: no perms
    assert kconfig.isManager # dev: manager not found

    # update config
    config: wcs.ManagerSettings = staticcall UserWalletConfig(kconfig.walletConfig).managerSettings(_manager)
    config.limits = _limits
    config.legoPerms = _legoPerms
    config.whitelistPerms = _whitelistPerms
    config.transferPerms = _transferPerms
    config.allowedAssets = _allowedAssets

    # validation
    globalConfig: wcs.GlobalManagerSettings = staticcall UserWalletConfig(kconfig.walletConfig).globalManagerSettings()
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
    kconfig: wcs.ManagerSettingsBundle = self._validateAndGetConfig(_user, _manager)
    if msg.sender not in [kconfig.owner, _manager]:
        assert self._isSwitchboardAddr(msg.sender, kconfig.inEjectMode) # dev: no perms
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
    kconfig: wcs.ManagerSettingsBundle = self._validateAndGetConfig(_user, _manager)
    assert msg.sender == kconfig.owner # dev: no perms
    assert kconfig.isManager # dev: manager not found

    # validation
    config: wcs.ManagerSettings = staticcall UserWalletConfig(kconfig.walletConfig).managerSettings(_manager)
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
def _validateAndGetConfig(_user: address, _manager: address) -> wcs.ManagerSettingsBundle:
    ledger: address = staticcall Registry(UNDY_HQ).getAddr(LEDGER_ID)
    assert staticcall Ledger(ledger).isUserWallet(_user) # dev: not a user wallet

    walletConfig: address = staticcall UserWallet(_user).walletConfig()
    return staticcall UserWalletConfig(walletConfig).getManagerSettingsBundle(_manager)


# is signer switchboard


@view
@internal
def _isSwitchboardAddr(_signer: address, _inEjectMode: bool) -> bool:
    if _inEjectMode:
        return False
    switchboard: address = staticcall Registry(UNDY_HQ).getAddr(SWITCHBOARD_ID)
    return staticcall Switchboard(switchboard).isSwitchboardAddr(_signer)