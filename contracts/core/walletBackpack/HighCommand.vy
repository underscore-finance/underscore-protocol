#    ┓ ┏  ┓┓   
#    ┃┃┃┏┓┃┃┏┓╋
#    ┗┻┛┗┻┗┗┗ ┗
#     __  __   __   ______   __  __       ______   ______   __    __   __    __   ______   __   __   _____    
#    /\ \_\ \ /\ \ /\  ___\ /\ \_\ \     /\  ___\ /\  __ \ /\ "-./  \ /\ "-./  \ /\  __ \ /\ "-.\ \ /\  __-.  
#    \ \  __ \\ \ \\ \ \__ \\ \  __ \    \ \ \____\ \ \/\ \\ \ \-./\ \\ \ \-./\ \\ \  __ \\ \ \-.  \\ \ \/\ \ 
#     \ \_\ \_\\ \_\\ \_____\\ \_\ \_\    \ \_____\\ \_____\\ \_\ \ \_\\ \_\ \ \_\\ \_\ \_\\ \_\\"\_\\ \____- 
#      \/_/\/_/ \/_/ \/_____/ \/_/\/_/     \/_____/ \/_____/ \/_/  \/_/ \/_/  \/_/ \/_/\/_/ \/_/ \/_/ \/____/ 
#                                                                                                
#     ╔════════════════════════════════════════════════════╗
#     ║  ** High Command **                                ║
#     ║  Manager settings / functionality for user wallets ║
#     ╚════════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

from interfaces import WalletConfigStructs as wcs

interface UserWalletConfig:
    def updateManager(_manager: address, _config: wcs.ManagerSettings): nonpayable
    def setGlobalManagerSettings(_config: wcs.GlobalManagerSettings): nonpayable
    def addManager(_manager: address, _config: wcs.ManagerSettings): nonpayable
    def managerSettings(_manager: address) -> wcs.ManagerSettings: view
    def globalManagerSettings() -> wcs.GlobalManagerSettings: view
    def indexOfManager(_addr: address) -> uint256: view
    def indexOfPayee(_payee: address) -> uint256: view
    def removeManager(_manager: address): nonpayable
    def timeLock() -> uint256: view
    def owner() -> address: view

interface Registry:
    def isValidRegId(_regId: uint256) -> bool: view
    def getAddr(_regId: uint256) -> address: view

interface MissionControl:
    def canPerformSecurityAction(_addr: address) -> bool: view

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
    canClaimLoot: bool

event ManagerRemoved:
    user: indexed(address)
    manager: indexed(address)

event ManagerActivationLengthAdjusted:
    user: indexed(address)
    manager: indexed(address)
    activationLength: uint256
    didRestart: bool

UNDY_HQ: public(immutable(address))
LEDGER_ID: constant(uint256) = 1
MISSION_CONTROL_ID: constant(uint256) = 2
LEGO_BOOK_ID: constant(uint256) = 3

MAX_CONFIG_ASSETS: constant(uint256) = 40
MAX_CONFIG_LEGOS: constant(uint256) = 25
MAX_ALLOWED_PAYEES: constant(uint256) = 40

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

    assert _maxStartDelay != 0 # dev: invalid start delay
    MAX_START_DELAY = _maxStartDelay


####################
# Manager Settings #
####################


# add manager


@external
def addManager(
    _userWallet: address,
    _manager: address,
    _limits: wcs.ManagerLimits,
    _legoPerms: wcs.LegoPerms,
    _swapPerms: wcs.SwapPerms,
    _whitelistPerms: wcs.WhitelistPerms,
    _transferPerms: wcs.TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
    _canClaimLoot: bool,
    _startDelay: uint256 = 0,
    _activationLength: uint256 = 0,
) -> bool:
    assert self._isValidUserWallet(_userWallet) # dev: invalid user wallet

    config: wcs.ManagerSettingsBundle = self._getManagerSettingsBundle(_userWallet, _manager)
    assert msg.sender == config.owner # dev: no perms
    assert _manager not in [empty(address), config.owner, config.walletConfig, _userWallet] # dev: invalid manager

    isValid: bool = False
    settings: wcs.ManagerSettings = empty(wcs.ManagerSettings)
    isValid, settings = self._isValidNewManager(config.isManager, _startDelay, _activationLength, _limits, _legoPerms, _swapPerms, _whitelistPerms, _transferPerms, _allowedAssets, _canClaimLoot, config.globalManagerSettings, config.timeLock, config.legoBook, config.walletConfig)
    assert isValid # dev: invalid manager
    
    extcall UserWalletConfig(config.walletConfig).addManager(_manager, settings)
    log ManagerSettingsModified(
        user = _userWallet,
        manager = _manager,
        startBlock = settings.startBlock,
        expiryBlock = settings.expiryBlock,
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
        canClaimLoot = _canClaimLoot,
    )
    return True


# update existing manager


@external
def updateManager(
    _userWallet: address,
    _manager: address,
    _limits: wcs.ManagerLimits,
    _legoPerms: wcs.LegoPerms,
    _swapPerms: wcs.SwapPerms,
    _whitelistPerms: wcs.WhitelistPerms,
    _transferPerms: wcs.TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
    _canClaimLoot: bool,
) -> bool:
    assert self._isValidUserWallet(_userWallet) # dev: invalid user wallet

    config: wcs.ManagerSettingsBundle = self._getManagerSettingsBundle(_userWallet, _manager)
    assert msg.sender == config.owner # dev: no perms

    # validate inputs
    assert self._validateManagerOnUpdate(config.isManager, _limits, _legoPerms, _swapPerms, _whitelistPerms, _transferPerms, _allowedAssets, _canClaimLoot, config.globalManagerSettings.managerPeriod, config.legoBook, config.walletConfig) # dev: invalid settings

    # update config
    settings: wcs.ManagerSettings = staticcall UserWalletConfig(config.walletConfig).managerSettings(_manager)
    settings.limits = _limits
    settings.legoPerms = _legoPerms
    settings.swapPerms = _swapPerms
    settings.whitelistPerms = _whitelistPerms
    settings.transferPerms = _transferPerms
    settings.allowedAssets = _allowedAssets
    settings.canClaimLoot = _canClaimLoot
    extcall UserWalletConfig(config.walletConfig).updateManager(_manager, settings)

    log ManagerSettingsModified(
        user = _userWallet,
        manager = _manager,
        startBlock = settings.startBlock,
        expiryBlock = settings.expiryBlock,
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
        canClaimLoot = _canClaimLoot,
    )
    return True


# remove manager


@external
def removeManager(_userWallet: address, _manager: address) -> bool:
    assert self._isValidUserWallet(_userWallet) # dev: invalid user wallet

    config: wcs.ManagerSettingsBundle = self._getManagerSettingsBundle(_userWallet, _manager)
    if msg.sender not in [config.owner, _manager]:
        assert self._canPerformSecurityAction(msg.sender) # dev: no perms
    assert config.isManager # dev: manager not found

    extcall UserWalletConfig(config.walletConfig).removeManager(_manager)
    log ManagerRemoved(user = _userWallet, manager = _manager)
    return True


# adjust activation length


@external
def adjustManagerActivationLength(
    _userWallet: address,
    _manager: address,
    _activationLength: uint256,
    _shouldResetStartBlock: bool = False,
) -> bool:
    assert self._isValidUserWallet(_userWallet) # dev: invalid user wallet

    config: wcs.ManagerSettingsBundle = self._getManagerSettingsBundle(_userWallet, _manager)
    assert msg.sender == config.owner # dev: no perms
    assert config.isManager # dev: no manager found

    # validation
    settings: wcs.ManagerSettings = staticcall UserWalletConfig(config.walletConfig).managerSettings(_manager)
    assert settings.startBlock < block.number # dev: manager not active yet
    assert self._validateActivationLength(_activationLength) # dev: invalid activation length

    # update config
    didRestart: bool = False
    if _shouldResetStartBlock or settings.expiryBlock < block.number:
        settings.startBlock = block.number
        didRestart = True

    settings.expiryBlock = settings.startBlock + _activationLength
    assert settings.expiryBlock > block.number # dev: invalid expiry block
    extcall UserWalletConfig(config.walletConfig).updateManager(_manager, settings)

    log ManagerActivationLengthAdjusted(
        user = _userWallet,
        manager = _manager,
        activationLength = _activationLength,
        didRestart = didRestart,
    )
    return True


###########################
# Global Manager Settings #
###########################


@external
def setGlobalManagerSettings(
    _userWallet: address,
    _managerPeriod: uint256,
    _startDelay: uint256,
    _activationLength: uint256,
    _canOwnerManage: bool,
    _limits: wcs.ManagerLimits,
    _legoPerms: wcs.LegoPerms,
    _swapPerms: wcs.SwapPerms,
    _whitelistPerms: wcs.WhitelistPerms,
    _transferPerms: wcs.TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
) -> bool:
    assert self._isValidUserWallet(_userWallet) # dev: invalid user wallet

    config: wcs.ManagerSettingsBundle = self._getManagerSettingsBundle(_userWallet, empty(address))
    assert msg.sender == config.owner # dev: no perms

    # validate inputs
    assert self._validateGlobalManagerSettings(_managerPeriod, _startDelay, _activationLength, _canOwnerManage, _limits, _legoPerms, _swapPerms, _whitelistPerms, _transferPerms, _allowedAssets, config.timeLock, config.legoBook, config.walletConfig) # dev: invalid settings

    # update config
    settings: wcs.GlobalManagerSettings = wcs.GlobalManagerSettings(
        managerPeriod = _managerPeriod,
        startDelay = _startDelay,
        activationLength = _activationLength,
        canOwnerManage = _canOwnerManage,
        limits = _limits,
        legoPerms = _legoPerms,
        swapPerms = _swapPerms,
        whitelistPerms = _whitelistPerms,
        transferPerms = _transferPerms,
        allowedAssets = _allowedAssets,
    )
    extcall UserWalletConfig(config.walletConfig).setGlobalManagerSettings(settings)

    log GlobalManagerSettingsModified(
        user = _userWallet,
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


######################
# Manager Validation #
######################


# validate on add new


@view
@external
def isValidNewManager(
    _userWallet: address,
    _manager: address,
    _startDelay: uint256,
    _activationLength: uint256,
    _limits: wcs.ManagerLimits,
    _legoPerms: wcs.LegoPerms,
    _swapPerms: wcs.SwapPerms,
    _whitelistPerms: wcs.WhitelistPerms,
    _transferPerms: wcs.TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
    _canClaimLoot: bool,
) -> bool:
    config: wcs.ManagerSettingsBundle = self._getManagerSettingsBundle(_userWallet, _manager)
    isValid: bool = False
    na: wcs.ManagerSettings = empty(wcs.ManagerSettings)
    isValid, na = self._isValidNewManager(config.isManager, _startDelay, _activationLength, _limits, _legoPerms, _swapPerms, _whitelistPerms, _transferPerms, _allowedAssets, _canClaimLoot, config.globalManagerSettings, config.timeLock, config.legoBook, config.walletConfig)
    return isValid


@view
@internal
def _isValidNewManager(
    _isManager: bool,
    _startDelay: uint256,
    _activationLength: uint256,
    _limits: wcs.ManagerLimits,
    _legoPerms: wcs.LegoPerms,
    _swapPerms: wcs.SwapPerms,
    _whitelistPerms: wcs.WhitelistPerms,
    _transferPerms: wcs.TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
    _canClaimLoot: bool,
    _globalConfig: wcs.GlobalManagerSettings,
    _currentTimeLock: uint256,
    _legoBookAddr: address,
    _walletConfig: address,
) -> (bool, wcs.ManagerSettings):

    # already a manager
    if _isManager:
        return False, empty(wcs.ManagerSettings)

    # start delay
    startDelay: uint256 = max(_globalConfig.startDelay, _currentTimeLock)
    if _startDelay != 0:
        startDelay = max(startDelay, _startDelay) # using max here as extra protection

    # activation length
    activationLength: uint256 = _globalConfig.activationLength
    if _activationLength != 0:
        activationLength = min(activationLength, _activationLength)

    # start delay
    if not self._validateStartDelay(startDelay, _currentTimeLock):
        return False, empty(wcs.ManagerSettings)

    # activation length
    if not self._validateActivationLength(activationLength):
        return False, empty(wcs.ManagerSettings)

    # validate limits
    if not self._validateManagerLimits(_limits, _globalConfig.managerPeriod):
        return False, empty(wcs.ManagerSettings)
    
    # validate lego perms
    if not self._validateLegoPerms(_legoPerms, _legoBookAddr):
        return False, empty(wcs.ManagerSettings)

    # validate swap perms
    if not self._validateSwapPerms(_swapPerms):
        return False, empty(wcs.ManagerSettings)

    # validate transfer perms
    if not self._validateTransferPerms(_transferPerms, _walletConfig):
        return False, empty(wcs.ManagerSettings)

    # validate allowed assets
    if not self._validateAllowedAssets(_allowedAssets):
        return False, empty(wcs.ManagerSettings)

    # create settings
    settings: wcs.ManagerSettings = wcs.ManagerSettings(
        startBlock = block.number + startDelay,
        expiryBlock = block.number + startDelay + activationLength,
        limits = _limits,
        legoPerms = _legoPerms,
        swapPerms = _swapPerms,
        whitelistPerms = _whitelistPerms,
        transferPerms = _transferPerms,
        allowedAssets = _allowedAssets,
        canClaimLoot = _canClaimLoot,
    )
    return True, settings


# validate on update


@view
@external
def validateManagerOnUpdate(
    _userWallet: address,
    _manager: address,
    _limits: wcs.ManagerLimits,
    _legoPerms: wcs.LegoPerms,
    _swapPerms: wcs.SwapPerms,
    _whitelistPerms: wcs.WhitelistPerms,
    _transferPerms: wcs.TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
    _canClaimLoot: bool,
) -> bool:
    config: wcs.ManagerSettingsBundle = self._getManagerSettingsBundle(_userWallet, _manager)
    return self._validateManagerOnUpdate(config.isManager, _limits, _legoPerms, _swapPerms, _whitelistPerms, _transferPerms, _allowedAssets, _canClaimLoot, config.globalManagerSettings.managerPeriod, config.legoBook, config.walletConfig)


@view
@internal
def _validateManagerOnUpdate(
    _isManager: bool,
    _limits: wcs.ManagerLimits,
    _legoPerms: wcs.LegoPerms,
    _swapPerms: wcs.SwapPerms,
    _whitelistPerms: wcs.WhitelistPerms,
    _transferPerms: wcs.TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
    _canClaimLoot: bool,
    _managerPeriod: uint256,
    _legoBookAddr: address,
    _walletConfig: address,
) -> bool:
    # must already be a manager
    if not _isManager:
        return False

    # validate limits
    if not self._validateManagerLimits(_limits, _managerPeriod):
        return False

    # validate lego perms
    if not self._validateLegoPerms(_legoPerms, _legoBookAddr):
        return False

    # validate swap perms
    if not self._validateSwapPerms(_swapPerms):
        return False

    # validate transfer perms
    if not self._validateTransferPerms(_transferPerms, _walletConfig):
        return False

    # validate allowed assets
    if not self._validateAllowedAssets(_allowedAssets):
        return False

    return True


# validate global manager settings


@view
@external
def validateGlobalManagerSettings(
    _userWallet: address,
    _managerPeriod: uint256,
    _startDelay: uint256,
    _activationLength: uint256,
    _canOwnerManage: bool,
    _limits: wcs.ManagerLimits,
    _legoPerms: wcs.LegoPerms,
    _swapPerms: wcs.SwapPerms,
    _whitelistPerms: wcs.WhitelistPerms,
    _transferPerms: wcs.TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
) -> bool:
    config: wcs.ManagerSettingsBundle = self._getManagerSettingsBundle(_userWallet, empty(address))
    return self._validateGlobalManagerSettings(_managerPeriod, _startDelay, _activationLength, _canOwnerManage, _limits, _legoPerms, _swapPerms, _whitelistPerms, _transferPerms, _allowedAssets, config.timeLock, config.legoBook, config.walletConfig)


@view
@internal
def _validateGlobalManagerSettings(
    _managerPeriod: uint256,
    _startDelay: uint256,
    _activationLength: uint256,
    _canOwnerManage: bool,
    _limits: wcs.ManagerLimits,
    _legoPerms: wcs.LegoPerms,
    _swapPerms: wcs.SwapPerms,
    _whitelistPerms: wcs.WhitelistPerms,
    _transferPerms: wcs.TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
    _currentTimeLock: uint256,
    _legoBookAddr: address,
    _walletConfig: address,
) -> bool:

    # manager period
    if not self._validateManagerPeriod(_managerPeriod):
        return False

    # default start delay
    if not self._validateStartDelay(_startDelay, _currentTimeLock):
        return False

    # default activation length
    if not self._validateActivationLength(_activationLength):
        return False

    # validate limits
    if not self._validateManagerLimits(_limits, _managerPeriod):
        return False

    # validate lego perms
    if not self._validateLegoPerms(_legoPerms, _legoBookAddr):
        return False

    # validate swap perms
    if not self._validateSwapPerms(_swapPerms):
        return False

    # validate transfer perms
    if not self._validateTransferPerms(_transferPerms, _walletConfig):
        return False

    # validate allowed assets
    if not self._validateAllowedAssets(_allowedAssets):
        return False

    return True


############################
# Manager Validation Utils #
############################


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

    # if any USD limits are set, failOnZeroPrice must be True
    # to prevent bypassing limits when price data is unavailable
    hasUsdLimits: bool = (
        _limits.maxUsdValuePerTx != 0 or
        _limits.maxUsdValuePerPeriod != 0 or
        _limits.maxUsdValueLifetime != 0
    )
    if hasUsdLimits and not _limits.failOnZeroPrice:
        return False

    return True


@view
@internal
def _validateLegoPerms(_legoPerms: wcs.LegoPerms, _legoBookAddr: address) -> bool:
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
        if staticcall UserWalletConfig(_walletConfig).indexOfPayee(payee) == 0:
            return False

        # check for duplicates
        if payee in checkedPayees:
            return False

        checkedPayees.append(payee)

    return True


@pure
@internal
def _validateSwapPerms(_swapPerms: wcs.SwapPerms) -> bool:
    # maxSlippage is in basis points where 10000 = 100%
    # cannot set slippage limit greater than 100%
    if _swapPerms.maxSlippage > 100_00:
        return False

    # if slippage limit is configured, mustHaveUsdValue must be True
    # (cannot validate slippage without USD values)
    if _swapPerms.maxSlippage != 0 and not _swapPerms.mustHaveUsdValue:
        return False

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


###################
# Wallet Defaults #
###################


# global manager settings


@view
@external
def createDefaultGlobalManagerSettings(
    _managerPeriod: uint256,
    _minTimeLock: uint256,
    _defaultActivationLength: uint256,
) -> wcs.GlobalManagerSettings:
    config: wcs.GlobalManagerSettings = empty(wcs.GlobalManagerSettings)
    config.managerPeriod = _managerPeriod
    config.startDelay = _minTimeLock
    config.activationLength = _defaultActivationLength
    config.canOwnerManage = True
    config.legoPerms, config.swapPerms, config.whitelistPerms, config.transferPerms = self._createHappyManagerDefaults()
    return config


# starter agent settings


@view
@external
def createStarterAgentSettings(_startingAgentActivationLength: uint256) -> wcs.ManagerSettings:
    config: wcs.ManagerSettings = wcs.ManagerSettings(
        startBlock = block.number,
        expiryBlock = block.number + _startingAgentActivationLength,
        limits = empty(wcs.ManagerLimits),
        legoPerms = empty(wcs.LegoPerms),
        swapPerms = empty(wcs.SwapPerms),
        whitelistPerms = empty(wcs.WhitelistPerms),
        transferPerms = empty(wcs.TransferPerms),
        allowedAssets = [],
        canClaimLoot = True,
    )
    config.legoPerms, config.swapPerms, config.whitelistPerms, config.transferPerms = self._createHappyManagerDefaults()
    return config


# happy defaults


@pure
@internal
def _createHappyManagerDefaults() -> (wcs.LegoPerms, wcs.SwapPerms, wcs.WhitelistPerms, wcs.TransferPerms):
    return wcs.LegoPerms(
        canManageYield = True,
        canBuyAndSell = True,
        canManageDebt = True,
        canManageLiq = True,
        canClaimRewards = True,
        onlyApprovedYieldOpps = True,
        allowedLegos = [],
    ), wcs.SwapPerms(
        mustHaveUsdValue = True,
        maxNumSwapsPerPeriod = 1,
        maxSlippage = 5_00, # 5%
    ), wcs.WhitelistPerms(
        canAddPending = False,
        canConfirm = True,
        canCancel = True,
        canRemove = False,
    ), wcs.TransferPerms(
        canTransfer = True,
        canCreateCheque = True,
        canAddPendingPayee = True,
        allowedPayees = [],
    )


#############
# Utilities #
#############


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


# manager settings bundle


@view
@external
def getManagerSettingsBundle(_userWallet: address, _manager: address) -> wcs.ManagerSettingsBundle:
    return self._getManagerSettingsBundle(_userWallet, _manager)


@view
@internal
def _getManagerSettingsBundle(_userWallet: address, _manager: address) -> wcs.ManagerSettingsBundle:
    walletConfig: address = staticcall UserWallet(_userWallet).walletConfig()
    return wcs.ManagerSettingsBundle(
        owner = staticcall UserWalletConfig(walletConfig).owner(),
        isManager = staticcall UserWalletConfig(walletConfig).indexOfManager(_manager) != 0,
        timeLock = staticcall UserWalletConfig(walletConfig).timeLock(),
        walletConfig = walletConfig,
        legoBook = staticcall Registry(UNDY_HQ).getAddr(LEGO_BOOK_ID),
        globalManagerSettings = staticcall UserWalletConfig(walletConfig).globalManagerSettings(),
    )
