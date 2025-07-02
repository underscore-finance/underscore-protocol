# @version 0.4.3

implements: Department

exports: addys.__interface__
exports: deptBasics.__interface__

initializes: addys
initializes: deptBasics[addys := addys]

import contracts.modules.Addys as addys
import contracts.modules.DeptBasics as deptBasics
from interfaces import Department
from interfaces import Wallet as wi

from ethereum.ercs import IERC20

interface UserWalletConfig:
    def getRecipientConfigs(_recipient: address) -> RecipientConfigBundle: view
    def getManagerConfigs(_signer: address) -> ManagerConfigBundle: view
    def isWhitelisted(_addr: address) -> bool: view

interface UserWallet:
    def walletConfig() -> address: view

flag WhitelistAction:
    ADD_WHITELIST
    CONFIRM_WHITELIST
    CANCEL_WHITELIST
    REMOVE_WHITELIST

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

# managers

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

# payees

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

MAX_CONFIG_ASSETS: constant(uint256) = 40
MAX_CONFIG_LEGOS: constant(uint256) = 25
MAX_ALLOWED_PAYEES: constant(uint256) = 40
MAX_ASSETS: constant(uint256) = 10
MAX_LEGOS: constant(uint256) = 10


@deploy
def __init__(_undyHq: address):
    addys.__init__(_undyHq)
    deptBasics.__init__(False, False) # no minting


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


# check manager usd limits


@view
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
def checkManagerUsdLimitsAndUpdateDataNoConfig(_user: address, _manager: address, _txUsdValue: uint256) -> ManagerData:
    userWalletConfig: address = staticcall UserWallet(_user).walletConfig()
    c: ManagerConfigBundle = staticcall UserWalletConfig(userWalletConfig).getManagerConfigs(_manager)
    data: ManagerData = self._getLatestManagerData(c.data, c.globalConfig.managerPeriod)
    return self._checkManagerUsdLimitsAndUpdateData(_txUsdValue, c.config.limits, c.globalConfig.limits, c.globalConfig.managerPeriod, data)


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
) -> (bool, PayeeData):
    userWalletConfig: address = staticcall UserWallet(_user).walletConfig()
    c: RecipientConfigBundle = staticcall UserWalletConfig(userWalletConfig).getRecipientConfigs(_recipient)
    return self._isValidPayee(c.isWhitelisted, c.isOwner, c.isPayee, _asset, _amount, _txUsdValue, c.config, c.globalConfig, c.data)


# is valid payee (with config)


@view
@external
def isValidPayeeWithConfig(
    _isWhitelisted: bool,
    _isOwner: bool,
    _isPayee: bool,
    _asset: address,
    _amount: uint256,
    _txUsdValue: uint256,
    _config: PayeeSettings,
    _globalConfig: GlobalPayeeSettings,
    _data: PayeeData,
) -> (bool, PayeeData):
    return self._isValidPayee(_isWhitelisted, _isOwner, _isPayee, _asset, _amount, _txUsdValue, _config, _globalConfig, _data)


# core logic -- is valid payee


@view
@internal
def _isValidPayee(
    _isWhitelisted: bool,
    _isOwner: bool,
    _isPayee: bool,
    _asset: address,
    _amount: uint256,
    _txUsdValue: uint256,
    _config: PayeeSettings,
    _globalConfig: GlobalPayeeSettings,
    _data: PayeeData,
) -> (bool, PayeeData):

    # whitelisted
    if _isWhitelisted:
        return True, empty(PayeeData)

    # check if recipient is owner
    if _isOwner and _globalConfig.canPayOwner:
        return True, empty(PayeeData)

    # registered payee
    if not _isPayee:
        return False, empty(PayeeData)

    # get payee data
    data: PayeeData = self._getLatestPayeeData(_data, _config.periodLength)

    # check specific payee settings
    if not self._checkSpecificPayeeSettings(_asset, _amount, _txUsdValue, data, _config):
        return False, empty(PayeeData)

    # check global payee settings
    if not self._checkGlobalPayeeSettings(_txUsdValue, data, _globalConfig):
        return False, empty(PayeeData)

    updatedData: PayeeData = self._updatePayeeData(_amount, _txUsdValue, data, _config.primaryAsset == _asset)
    return True, updatedData


# update payee data


@view
@internal
def _updatePayeeData(
    _amount: uint256,
    _txUsdValue: uint256,
    _data: PayeeData,
    _isPrimaryAsset: bool,
) -> PayeeData:
    data: PayeeData = _data

    # update transaction details
    data.numTxsInPeriod += 1
    data.totalUsdValueInPeriod += _txUsdValue
    data.totalNumTxs += 1
    data.totalUsdValue += _txUsdValue
    data.lastTxBlock = block.number
    
    # update unit amounts if this is the primary asset
    if _isPrimaryAsset:
        data.totalUnitsInPeriod += _amount
        data.totalUnits += _amount

    return data


# specific payee settings


@view
@internal
def _checkSpecificPayeeSettings(
    _asset: address,
    _amount: uint256,
    _txUsdValue: uint256,
    _data: PayeeData,
    _config: PayeeSettings,
) -> bool:

    # check zero price
    if _txUsdValue == 0 and _config.failOnZeroPrice:
        return False

    # is payee active
    if _config.startBlock > block.number or _config.expiryBlock < block.number:
        return False
    
    # check if asset is allowed
    if _config.onlyPrimaryAsset and _config.primaryAsset != empty(address):
        if _config.primaryAsset != _asset:
            return False

    # check transaction limits
    if not self._checkTransactionLimits(_config.maxNumTxsPerPeriod, _config.txCooldownBlocks, _data.numTxsInPeriod, _data.lastTxBlock):
        return False

    # check USD limits 
    if not self._checkUsdLimits(_txUsdValue, _config.usdLimits, _data):
        return False

    # check unit limits if this is the primary asset
    if _config.primaryAsset == _asset:
        if not self._checkUnitLimits(_amount, _config.unitLimits, _data):
            return False

    return True


# global payee settings


@view
@internal
def _checkGlobalPayeeSettings(
    _txUsdValue: uint256,
    _data: PayeeData,
    _config: GlobalPayeeSettings,
) -> bool:

    # check zero price
    if _txUsdValue == 0 and _config.failOnZeroPrice:
        return False

    # check transaction limits
    if not self._checkTransactionLimits(_config.maxNumTxsPerPeriod, _config.txCooldownBlocks, _data.numTxsInPeriod, _data.lastTxBlock):
        return False

    # check USD limits
    if not self._checkUsdLimits(_txUsdValue, _config.usdLimits, _data):
        return False

    return True


# get latest payee data (period reset)


@view
@internal
def _getLatestPayeeData(_data: PayeeData, _periodLength: uint256) -> PayeeData:
    data: PayeeData = _data
    
    # initialize period if first transaction
    if data.periodStartBlock == 0:
        data.periodStartBlock = block.number
    
    # check if current period has ended
    elif block.number >= data.periodStartBlock + _periodLength:
        data.numTxsInPeriod = 0
        data.totalUnitsInPeriod = 0
        data.totalUsdValueInPeriod = 0
        data.periodStartBlock = block.number
    
    return data


# check USD limits


@view
@internal
def _checkUsdLimits(_txUsdValue: uint256, _limits: PayeeLimits, _data: PayeeData) -> bool:
    if _limits.perTxCap != 0 and _txUsdValue > _limits.perTxCap:
        return False
    
    if _limits.perPeriodCap != 0 and _data.totalUsdValueInPeriod + _txUsdValue > _limits.perPeriodCap:
        return False
    
    if _limits.lifetimeCap != 0 and _data.totalUsdValue + _txUsdValue > _limits.lifetimeCap:
        return False
    
    return True


# check unit limits


@view
@internal
def _checkUnitLimits(_amount: uint256, _limits: PayeeLimits, _data: PayeeData) -> bool:
    if _limits.perTxCap != 0 and _amount > _limits.perTxCap:
        return False
    
    if _limits.perPeriodCap != 0 and _data.totalUnitsInPeriod + _amount > _limits.perPeriodCap:
        return False
    
    if _limits.lifetimeCap != 0 and _data.totalUnits + _amount > _limits.lifetimeCap:
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


########################
# Whitelist Management #
########################


@view
@external
def canManageWhitelistNoConfig(_user: address, _signer: address, _action: WhitelistAction) -> bool:
    userWalletConfig: address = staticcall UserWallet(_user).walletConfig()
    c: ManagerConfigBundle = staticcall UserWalletConfig(userWalletConfig).getManagerConfigs(_signer)
    return self._canManageWhitelist(_signer, c.isOwner, c.isManager, _action, c.config.whitelistPerms, c.globalConfig.whitelistPerms)


@view
@external
def canManageWhitelist(
    _signer: address,
    _isOwner: bool,
    _isManager: bool,
    _action: WhitelistAction,
    _config: WhitelistPerms,
    _globalConfig: WhitelistPerms,
) -> bool:
    return self._canManageWhitelist(_signer, _isOwner, _isManager, _action, _config, _globalConfig)


@view
@internal
def _canManageWhitelist(
    _signer: address,
    _isOwner: bool,
    _isManager: bool,
    _action: WhitelistAction,
    _config: WhitelistPerms,
    _globalConfig: WhitelistPerms,
) -> bool:

    # check if signer is the owner
    if _isOwner:
        return True

    # check if signer is a manager
    if not _isManager:
        return False 

    # add to whitelist
    if _action == WhitelistAction.ADD_WHITELIST:
        return _config.canAddPending and _globalConfig.canAddPending
    
    # confirm whitelist
    elif _action == WhitelistAction.CONFIRM_WHITELIST:
        return _config.canConfirm and _globalConfig.canConfirm
    
    # cancel whitelist
    elif _action == WhitelistAction.CANCEL_WHITELIST:
        return _config.canCancel and _globalConfig.canCancel
    
    # remove from whitelist
    elif _action == WhitelistAction.REMOVE_WHITELIST:
        return _config.canRemove and _globalConfig.canRemove
    
    # invalid action
    else:
        return False