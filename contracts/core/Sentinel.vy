# @version 0.4.3

from interfaces import WalletStructs as ws
from interfaces import WalletConfigStructs as wcs

interface UserWalletConfig:
    def managerSettings(_addr: address) -> wcs.ManagerSettings: view
    def managerPeriodData(_addr: address) -> wcs.ManagerData: view
    def globalManagerSettings() -> wcs.GlobalManagerSettings: view
    def payeeSettings(_addr: address) -> wcs.PayeeSettings: view
    def payeePeriodData(_addr: address) -> wcs.PayeeData: view
    def globalPayeeSettings() -> wcs.GlobalPayeeSettings: view
    def indexOfWhitelist(_addr: address) -> uint256: view
    def indexOfManager(_addr: address) -> uint256: view
    def indexOfPayee(_addr: address) -> uint256: view
    def owner() -> address: view

interface UserWallet:
    def walletConfig() -> address: view

MAX_CONFIG_ASSETS: constant(uint256) = 40
MAX_ASSETS: constant(uint256) = 10
MAX_LEGOS: constant(uint256) = 10


@deploy
def __init__():
    pass


###################################
# Manager Validation - Pre Action #
###################################


@view
@external
def canSignerPerformAction(
    _user: address,
    _signer: address,
    _action: ws.ActionType,
    _assets: DynArray[address, MAX_ASSETS] = [],
    _legoIds: DynArray[uint256, MAX_LEGOS] = [],
    _transferRecipient: address = empty(address),
) -> bool:
    c: wcs.ManagerConfigBundle = self._getManagerConfigBundle(_user, _signer, _transferRecipient)
    return self._canSignerPerformAction(c.isOwner, c.isManager, c.data, c.config, c.globalConfig, _action, _assets, _legoIds, c.payee)


@view
@external
def canSignerPerformActionWithConfig(
    _isOwner: bool,
    _isManager: bool,
    _managerData: wcs.ManagerData,
    _config: wcs.ManagerSettings,
    _globalConfig: wcs.GlobalManagerSettings,
    _action: ws.ActionType,
    _assets: DynArray[address, MAX_ASSETS] = [],
    _legoIds: DynArray[uint256, MAX_LEGOS] = [],
    _payee: address = empty(address),
) -> bool:
    return self._canSignerPerformAction(_isOwner, _isManager, _managerData, _config, _globalConfig, _action, _assets, _legoIds, _payee)


# core logic -- manager access control


@view
@internal
def _canSignerPerformAction(
    _isOwner: bool,
    _isManager: bool,
    _managerData: wcs.ManagerData,
    _managerConfig: wcs.ManagerSettings,
    _globalConfig: wcs.GlobalManagerSettings,
    _action: ws.ActionType,
    _assets: DynArray[address, MAX_ASSETS],
    _legoIds: DynArray[uint256, MAX_LEGOS],
    _payee: address,
) -> bool:
    # check if signer is the owner, and if owner can manage
    if _isOwner and _globalConfig.canOwnerManage:
        return True

    # check if signer is a manager
    if not _isManager:
        return False

    # get latest manager data
    managerData: wcs.ManagerData = self._getLatestManagerData(_managerData, _globalConfig.managerPeriod)

    # manager is not active
    if _managerConfig.startBlock > block.number or _managerConfig.expiryBlock <= block.number:
        return False

    # specific manager
    if not self._checkManagerPermsAndLimitsPreAction(managerData, _action, _assets, _legoIds, _payee, _managerConfig.limits, _managerConfig.legoPerms, _managerConfig.transferPerms, _managerConfig.allowedAssets):
        return False

    # global manager settings
    if not self._checkManagerPermsAndLimitsPreAction(managerData, _action, _assets, _legoIds, _payee, _globalConfig.limits, _globalConfig.legoPerms, _globalConfig.transferPerms, _globalConfig.allowedAssets):
        return False

    return True


# latest manager data


@view
@internal
def _getLatestManagerData(_managerData: wcs.ManagerData, _managerPeriod: uint256) -> wcs.ManagerData:
    managerData: wcs.ManagerData = _managerData

    # initialize period if first transaction
    if managerData.periodStartBlock == 0:
        managerData.periodStartBlock = block.number
    
    # check if current period has ended
    elif block.number >= managerData.periodStartBlock + _managerPeriod:
        managerData.numTxsInPeriod = 0
        managerData.totalUsdValueInPeriod = 0
        managerData.periodStartBlock = block.number

    return managerData


# manager permissions and limits


@view
@internal
def _checkManagerPermsAndLimitsPreAction(
    _managerData: wcs.ManagerData,
    _txAction: ws.ActionType,
    _txAssets: DynArray[address, MAX_ASSETS],
    _txLegoIds: DynArray[uint256, MAX_LEGOS],
    _txPayee: address,
    _limits: wcs.ManagerLimits,
    _legoPerms: wcs.LegoPerms,
    _transferPerms: wcs.TransferPerms,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
) -> bool:

    # only checking tx limits right now (pre transaction)
    if not self._checkTransactionLimits(_limits.maxNumTxsPerPeriod, _limits.txCooldownBlocks, _managerData.numTxsInPeriod, _managerData.lastTxBlock):
        return False

    # check allowed assets
    if len(_allowedAssets) != 0:
        for a: address in _txAssets:
            if a != empty(address) and a not in _allowedAssets:
                return False

    # check allowed lego ids
    if len(_legoPerms.allowedLegos) != 0:
        for lid: uint256 in _txLegoIds:
            if lid != 0 and lid not in _legoPerms.allowedLegos:
                return False

    # check allowed payees
    if _txPayee != empty(address) and len(_transferPerms.allowedPayees) != 0:
        if _txPayee not in _transferPerms.allowedPayees:
            return False

    # check action permissions
    if _txAction == ws.ActionType.TRANSFER:
        return _transferPerms.canTransfer
    elif _txAction in (ws.ActionType.EARN_DEPOSIT | ws.ActionType.EARN_WITHDRAW | ws.ActionType.EARN_REBALANCE):
        return _legoPerms.canManageYield
    elif _txAction in (ws.ActionType.SWAP | ws.ActionType.MINT_REDEEM | ws.ActionType.CONFIRM_MINT_REDEEM):
        return _legoPerms.canBuyAndSell
    elif _txAction in (ws.ActionType.ADD_COLLATERAL | ws.ActionType.REMOVE_COLLATERAL | ws.ActionType.BORROW | ws.ActionType.REPAY_DEBT):
        return _legoPerms.canManageDebt
    elif _txAction in (ws.ActionType.ADD_LIQ | ws.ActionType.REMOVE_LIQ | ws.ActionType.ADD_LIQ_CONC | ws.ActionType.REMOVE_LIQ_CONC):
        return _legoPerms.canManageLiq
    elif _txAction == ws.ActionType.REWARDS:
        return _legoPerms.canClaimRewards
    else:
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


####################################
# Manager Validation - Post Action #
####################################


@view
@external
def checkManagerUsdLimits(
    _user: address,
    _manager: address,
    _txUsdValue: uint256,
) -> bool:
    c: wcs.ManagerConfigBundle = self._getManagerConfigBundle(_user, _manager)
    canFinishTx: bool = False
    na: wcs.ManagerData = empty(wcs.ManagerData)
    canFinishTx, na = self._checkManagerUsdLimitsAndUpdateData(_txUsdValue, c.config.limits, c.globalConfig.limits, c.globalConfig.managerPeriod, c.data)
    return canFinishTx


@view
@external
def checkManagerUsdLimitsAndUpdateData(
    _txUsdValue: uint256,
    _specificLimits: wcs.ManagerLimits,
    _globalLimits: wcs.ManagerLimits,
    _managerPeriod: uint256,
    _managerData: wcs.ManagerData,
) -> (bool, wcs.ManagerData):
    return self._checkManagerUsdLimitsAndUpdateData(_txUsdValue, _specificLimits, _globalLimits, _managerPeriod, _managerData)


@view
@internal
def _checkManagerUsdLimitsAndUpdateData(
    _txUsdValue: uint256,
    _specificLimits: wcs.ManagerLimits,
    _globalLimits: wcs.ManagerLimits,
    _managerPeriod: uint256,
    _managerData: wcs.ManagerData,
) -> (bool, wcs.ManagerData):
    managerData: wcs.ManagerData = self._getLatestManagerData(_managerData, _managerPeriod)

    # manager usd value limits
    if not self._checkManagerUsdLimits(_txUsdValue, _specificLimits, managerData):
        return False, empty(wcs.ManagerData)

    # global usd value limits
    if not self._checkManagerUsdLimits(_txUsdValue, _globalLimits, managerData):
        return False, empty(wcs.ManagerData)

    # update manager data
    managerData.numTxsInPeriod += 1
    managerData.totalUsdValueInPeriod += _txUsdValue
    managerData.totalNumTxs += 1
    managerData.totalUsdValue += _txUsdValue
    managerData.lastTxBlock = block.number

    return True, managerData


# check manager usd limits


@pure
@internal
def _checkManagerUsdLimits(_txUsdValue: uint256, _limits: wcs.ManagerLimits, _managerData: wcs.ManagerData) -> bool:

    # check zero price
    if _txUsdValue == 0 and _limits.failOnZeroPrice:
        return False

    # check max usd value per tx
    if _limits.maxUsdValuePerTx != 0:
        if _txUsdValue > _limits.maxUsdValuePerTx:
            return False
    
    # check max usd value per period
    if _limits.maxUsdValuePerPeriod != 0:
        if _managerData.totalUsdValueInPeriod + _txUsdValue > _limits.maxUsdValuePerPeriod:
            return False
    
    # check max usd value lifetime
    if _limits.maxUsdValueLifetime != 0:
        if _managerData.totalUsdValue + _txUsdValue > _limits.maxUsdValueLifetime:
            return False
    
    return True


####################
# Payee Validation #
####################


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
    c: wcs.RecipientConfigBundle = self._getPayeeConfigs(_user, _recipient)
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


###################
# Wallet Defaults #
###################


# manager settings


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
    config.legoPerms, config.whitelistPerms, config.transferPerms = self._createHappyManagerDefaults()
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
        whitelistPerms = empty(wcs.WhitelistPerms),
        transferPerms = empty(wcs.TransferPerms),
        allowedAssets = [],
    )
    config.legoPerms, config.whitelistPerms, config.transferPerms = self._createHappyManagerDefaults()
    return config


# payee settings


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


# happy defaults


@pure
@internal
def _createHappyManagerDefaults() -> (wcs.LegoPerms, wcs.WhitelistPerms, wcs.TransferPerms):
    return wcs.LegoPerms(
        canManageYield = True,
        canBuyAndSell = True,
        canManageDebt = True,
        canManageLiq = True,
        canClaimRewards = True,
        allowedLegos = [],
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


@view
@internal
def _getManagerConfigBundle(_userWallet: address, _signer: address, _transferRecipient: address = empty(address)) -> wcs.ManagerConfigBundle:
    userWalletConfig: address = staticcall UserWallet(_userWallet).walletConfig()

    payee: address = _transferRecipient
    if _transferRecipient != empty(address) and staticcall UserWalletConfig(userWalletConfig).indexOfWhitelist(_transferRecipient) != 0:
        payee = empty(address)

    return wcs.ManagerConfigBundle(
        isOwner = _signer == staticcall UserWalletConfig(userWalletConfig).owner(),
        isManager = staticcall UserWalletConfig(userWalletConfig).indexOfManager(_signer) != 0,
        config = staticcall UserWalletConfig(userWalletConfig).managerSettings(_signer),
        globalConfig = staticcall UserWalletConfig(userWalletConfig).globalManagerSettings(),
        data = staticcall UserWalletConfig(userWalletConfig).managerPeriodData(_signer),
        payee = payee,
    )


@view
@internal
def _getPayeeConfigs(_userWallet: address, _recipient: address) -> wcs.RecipientConfigBundle:
    userWalletConfig: address = staticcall UserWallet(_userWallet).walletConfig()
    isWhitelisted: bool = staticcall UserWalletConfig(userWalletConfig).indexOfWhitelist(_recipient) != 0

    isOwner: bool = False
    isPayee: bool = False
    config: wcs.PayeeSettings = empty(wcs.PayeeSettings)
    globalConfig: wcs.GlobalPayeeSettings = empty(wcs.GlobalPayeeSettings)
    data: wcs.PayeeData = empty(wcs.PayeeData)
    if not isWhitelisted:
        isOwner = _recipient == staticcall UserWalletConfig(userWalletConfig).owner()
        isPayee = staticcall UserWalletConfig(userWalletConfig).indexOfPayee(_recipient) != 0
        config = staticcall UserWalletConfig(userWalletConfig).payeeSettings(_recipient)
        globalConfig = staticcall UserWalletConfig(userWalletConfig).globalPayeeSettings()
        data = staticcall UserWalletConfig(userWalletConfig).payeePeriodData(_recipient)

    return wcs.RecipientConfigBundle(
        isWhitelisted = isWhitelisted,
        isOwner = isOwner,
        isPayee = isPayee,
        config = config,
        globalConfig = globalConfig,
        data = data,
    )