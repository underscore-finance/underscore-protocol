#    ┓ ┏  ┓┓   
#    ┃┃┃┏┓┃┃┏┓╋
#    ┗┻┛┗┻┗┗┗ ┗
#     ______   ______   __   __   ______  __   __   __   ______   __        
#    /\  ___\ /\  ___\ /\ "-.\ \ /\__  _\/\ \ /\ "-.\ \ /\  ___\ /\ \       
#    \ \___  \\ \  __\ \ \ \-.  \\/_/\ \/\ \ \\ \ \-.  \\ \  __\ \ \ \____  
#     \/\_____\\ \_____\\ \_\\"\_\  \ \_\ \ \_\\ \_\\"\_\\ \_____\\ \_____\ 
#      \/_____/ \/_____/ \/_/ \/_/   \/_/  \/_/ \/_/ \/_/ \/_____/ \/_____/ 
#                                                                                                
#     ╔════════════════════════════════════════╗
#     ║  ** Sentinel **                        ║
#     ║  Validation on user wallet activity.   ║
#     ╚════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

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

interface VaultRegistry:
    def isApprovedVaultTokenForAsset(_underlyingAsset: address, _vaultToken: address) -> bool: view

interface UserWallet:
    def walletConfig() -> address: view

MAX_CONFIG_ASSETS: constant(uint256) = 40
MAX_ASSETS: constant(uint256) = 10
MAX_LEGOS: constant(uint256) = 10
HUNDRED_PERCENT: constant(uint256) = 100_00


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
    _txRecipient: address = empty(address),
) -> bool:
    c: wcs.ManagerConfigBundle = self._getManagerConfigBundle(_user, _signer, _txRecipient)
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
    _txRecipient: address = empty(address),
) -> bool:
    return self._canSignerPerformAction(_isOwner, _isManager, _managerData, _config, _globalConfig, _action, _assets, _legoIds, _txRecipient)


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
    _txRecipient: address,
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
    if not self._checkManagerPermsAndLimitsPreAction(managerData, _action, _assets, _legoIds, _txRecipient, _managerConfig.limits, _managerConfig.legoPerms, _managerConfig.transferPerms, _managerConfig.allowedAssets):
        return False

    # global manager settings
    if not self._checkManagerPermsAndLimitsPreAction(managerData, _action, _assets, _legoIds, _txRecipient, _globalConfig.limits, _globalConfig.legoPerms, _globalConfig.transferPerms, _globalConfig.allowedAssets):
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
        managerData.numSwapsInPeriod = 0
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
    _txRecipient: address,
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
    if _txRecipient != empty(address) and len(_transferPerms.allowedPayees) != 0:
        if _txRecipient not in _transferPerms.allowedPayees:
            return False

    # check action permissions
    if _txAction in (ws.ActionType.TRANSFER | ws.ActionType.PAY_CHEQUE):
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
def canManagerFinishTx(
    _user: address,
    _manager: address,
    _txUsdValue: uint256,
    _underlyingAsset: address,
    _vaultToken: address,
    _isSwap: bool,
    _specificSwapPerms: wcs.SwapPerms,
    _globalSwapPerms: wcs.SwapPerms,
    _fromAssetUsdValue: uint256,
    _toAssetUsdValue: uint256,
    _vaultRegistry: address,
) -> bool:
    c: wcs.ManagerConfigBundle = self._getManagerConfigBundle(_user, _manager)
    canFinishTx: bool = False
    na: wcs.ManagerData = empty(wcs.ManagerData)
    requiresVaultApproval: bool = (c.config.legoPerms.onlyApprovedYieldOpps or c.globalConfig.legoPerms.onlyApprovedYieldOpps)
    canFinishTx, na = self._checkManagerLimitsPostTx(_txUsdValue, c.config.limits, c.globalConfig.limits, c.globalConfig.managerPeriod, c.data, requiresVaultApproval, _underlyingAsset, _vaultToken, _isSwap, c.config.swapPerms, c.globalConfig.swapPerms, _fromAssetUsdValue, _toAssetUsdValue, _vaultRegistry)
    return canFinishTx


@view
@external
def checkManagerLimitsPostTx(
    _txUsdValue: uint256,
    _specificLimits: wcs.ManagerLimits,
    _globalLimits: wcs.ManagerLimits,
    _managerPeriod: uint256,
    _managerData: wcs.ManagerData,
    _requiresVaultApproval: bool,
    _underlyingAsset: address,
    _vaultToken: address,
    _isSwap: bool,
    _specificSwapPerms: wcs.SwapPerms,
    _globalSwapPerms: wcs.SwapPerms,
    _fromAssetUsdValue: uint256,
    _toAssetUsdValue: uint256,
    _vaultRegistry: address,
) -> (bool, wcs.ManagerData):
    return self._checkManagerLimitsPostTx(_txUsdValue, _specificLimits, _globalLimits, _managerPeriod, _managerData, _requiresVaultApproval, _underlyingAsset, _vaultToken, _isSwap, _specificSwapPerms, _globalSwapPerms, _fromAssetUsdValue, _toAssetUsdValue, _vaultRegistry)


@view
@internal
def _checkManagerLimitsPostTx(
    _txUsdValue: uint256,
    _specificLimits: wcs.ManagerLimits,
    _globalLimits: wcs.ManagerLimits,
    _managerPeriod: uint256,
    _managerData: wcs.ManagerData,
    _requiresVaultApproval: bool,
    _underlyingAsset: address,
    _vaultToken: address,
    _isSwap: bool,
    _specificSwapPerms: wcs.SwapPerms,
    _globalSwapPerms: wcs.SwapPerms,
    _fromAssetUsdValue: uint256,
    _toAssetUsdValue: uint256,
    _vaultRegistry: address,
) -> (bool, wcs.ManagerData):
    managerData: wcs.ManagerData = self._getLatestManagerData(_managerData, _managerPeriod)

    # manager usd value limits
    if not self._checkManagerUsdLimits(_txUsdValue, _specificLimits, managerData):
        return False, empty(wcs.ManagerData)

    # global usd value limits
    if not self._checkManagerUsdLimits(_txUsdValue, _globalLimits, managerData):
        return False, empty(wcs.ManagerData)

    # vault token approval
    if _requiresVaultApproval and empty(address) not in [_underlyingAsset, _vaultToken, _vaultRegistry]:
        if not staticcall VaultRegistry(_vaultRegistry).isApprovedVaultTokenForAsset(_underlyingAsset, _vaultToken):
            return False, empty(wcs.ManagerData)

    # swap-specific validations
    if _isSwap:

        # check if USD values are required and present (non-zero)
        if not self._checkSwapHasUsdValue(_specificSwapPerms, _globalSwapPerms, _fromAssetUsdValue, _toAssetUsdValue):
            return False, empty(wcs.ManagerData)

        # check swap count limit
        if not self._checkSwapCountLimit(_specificSwapPerms, _globalSwapPerms, managerData):
            return False, empty(wcs.ManagerData)

        # check slippage (loss prevention)
        if not self._hasAcceptableSlippage(_specificSwapPerms, _globalSwapPerms, _fromAssetUsdValue, _toAssetUsdValue):
            return False, empty(wcs.ManagerData)

        # Increment swap counter
        managerData.numSwapsInPeriod += 1

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


# check swap has usd value


@pure
@internal
def _checkSwapHasUsdValue(_specific: wcs.SwapPerms, _global: wcs.SwapPerms, _fromUsdValue: uint256, _toUsdValue: uint256) -> bool:

    # if either manager-specific or global requires USD values, enforce it
    mustHaveUsdValue: bool = _specific.mustHaveUsdValue or _global.mustHaveUsdValue
    if not mustHaveUsdValue:
        return True # no requirement for USD values

    # from and to assets must have USD values (non-zero)
    return _fromUsdValue != 0 and _toUsdValue != 0


# check swap count limit


@pure
@internal
def _checkSwapCountLimit(_specific: wcs.SwapPerms, _global: wcs.SwapPerms, _data: wcs.ManagerData) -> bool:
    # use manager-specific limit if set, otherwise use global
    limit: uint256 = _specific.maxNumSwapsPerPeriod if _specific.maxNumSwapsPerPeriod != 0 else _global.maxNumSwapsPerPeriod
    if limit == 0:
        return True # no limit
    return _data.numSwapsInPeriod < limit


# check swap slippage (loss prevention)


@pure
@internal
def _hasAcceptableSlippage(_specific: wcs.SwapPerms, _global: wcs.SwapPerms, _fromUsdValue: uint256, _toUsdValue: uint256) -> bool:
    # use tighter (lower) slippage limit between manager and global
    slippage: uint256 = _specific.maxSlippage
    if slippage == 0 or (_global.maxSlippage != 0 and _global.maxSlippage < slippage):
        slippage = _global.maxSlippage

    if slippage == 0:
        return True # no limit
    
    # calculate minimum acceptable value (loss prevention)
    # Formula: toUsdValue >= fromUsdValue * (10000 - slippage) / 10000
    # Note: USD values are guaranteed to be non-zero here because:
    #   - If slippage > 0, config validation requires mustHaveUsdValue = True
    #   - If mustHaveUsdValue = True, _checkSwapHasUsdValue enforces non-zero USD values
    acceptablePercentage: uint256 = HUNDRED_PERCENT - slippage
    minAcceptableValue: uint256 = (_fromUsdValue * acceptablePercentage) // HUNDRED_PERCENT
    return _toUsdValue >= minAcceptableValue


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


#####################
# Cheque Validation #
#####################


@view
@external
def isValidChequeAndGetData(
    _asset: address,
    _amount: uint256,
    _txUsdValue: uint256,
    _cheque: wcs.Cheque,
    _globalConfig: wcs.ChequeSettings,
    _chequeData: wcs.ChequeData,
    _isManager: bool,
) -> (bool, wcs.ChequeData):

    # check if cheque is active
    if not _cheque.active:
        return False, empty(wcs.ChequeData)

    # check if within expiry and unlock blocks
    if block.number >= _cheque.expiryBlock or block.number < _cheque.unlockBlock:
        return False, empty(wcs.ChequeData)

    # no recipient or asset
    if empty(address) in [_cheque.recipient, _cheque.asset]:
        return False, empty(wcs.ChequeData)

    # check asset matches
    if _cheque.asset != _asset:
        return False, empty(wcs.ChequeData)

    # check amount matches cheque amount
    if _amount != _cheque.amount:
        return False, empty(wcs.ChequeData)

    # check if asset is allowed in global config
    if len(_globalConfig.allowedAssets) != 0:
        if _asset not in _globalConfig.allowedAssets:
            return False, empty(wcs.ChequeData)

    # check if USD value is zero
    if _txUsdValue == 0:
        return False, empty(wcs.ChequeData)

    # check max cheque USD value
    if _globalConfig.maxChequeUsdValue != 0:
        if _txUsdValue > _globalConfig.maxChequeUsdValue:
            return False, empty(wcs.ChequeData)

    # check if manager can pay
    if _isManager:
        if not _globalConfig.canManagerPay or not _cheque.canManagerPay:
            return False, empty(wcs.ChequeData)

    # get latest cheque data
    chequeData: wcs.ChequeData = self._getLatestChequeData(_chequeData, _globalConfig.periodLength)

    # check pay cooldown
    if _globalConfig.payCooldownBlocks != 0:
        if block.number < chequeData.lastChequePaidBlock + _globalConfig.payCooldownBlocks:
            return False, empty(wcs.ChequeData)

    # check max num cheques paid per period
    if _globalConfig.maxNumChequesPaidPerPeriod != 0:
        if chequeData.numChequesPaidInPeriod >= _globalConfig.maxNumChequesPaidPerPeriod:
            return False, empty(wcs.ChequeData)

    # check per period paid USD cap
    if _globalConfig.perPeriodPaidUsdCap != 0:
        if chequeData.totalUsdValuePaidInPeriod + _txUsdValue > _globalConfig.perPeriodPaidUsdCap:
            return False, empty(wcs.ChequeData)

    # update cheque data
    chequeData.numChequesPaidInPeriod += 1
    chequeData.totalUsdValuePaidInPeriod += _txUsdValue
    chequeData.totalNumChequesPaid += 1
    chequeData.totalUsdValuePaid += _txUsdValue
    chequeData.lastChequePaidBlock = block.number

    return True, chequeData


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


#############
# Utilities #
#############


@view
@internal
def _getManagerConfigBundle(_userWallet: address, _signer: address, _txRecipient: address = empty(address)) -> wcs.ManagerConfigBundle:
    userWalletConfig: address = staticcall UserWallet(_userWallet).walletConfig()

    payee: address = _txRecipient
    if _txRecipient != empty(address) and staticcall UserWalletConfig(userWalletConfig).indexOfWhitelist(_txRecipient) != 0:
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
