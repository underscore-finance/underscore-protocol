# @version 0.4.3
# pragma optimize codesize

implements: Department

exports: addys.__interface__
exports: deptBasics.__interface__

initializes: addys
initializes: deptBasics[addys := addys]

import contracts.modules.Addys as addys
import contracts.modules.DeptBasics as deptBasics
from interfaces import Department
from interfaces import Wallet as wi

interface UserWalletConfig:
    def getRecipientConfigs(_recipient: address) -> RecipientConfigBundle: view

interface UserWallet:
    def walletConfig() -> address: view

struct RecipientConfigBundle:
    isWhitelisted: bool
    isOwner: bool
    isPayee: bool
    config: PayeeSettings
    globalConfig: GlobalPayeeSettings
    data: PayeeData

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


@deploy
def __init__(_undyHq: address):
    addys.__init__(_undyHq)
    deptBasics.__init__(False, False) # no minting


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


# flag WhitelistAction:
#     ADD_WHITELIST
#     CONFIRM_WHITELIST
#     CANCEL_WHITELIST
#     REMOVE_WHITELIST


# # add whitelist


# @external
# def addWhitelistAddr(_user: address, _addr: address):
#     walletConfig: address = self._validateAndGetWalletConfig(_user)
#     bossValidator: address = staticcall UserWalletConfig(walletConfig).bossValidator()
#     c: ManagerConfigBundle = staticcall UserWalletConfig(walletConfig).getManagerConfigs(msg.sender)
#     assert staticcall BossValidator(bossValidator).canManageWhitelist(msg.sender, c.isOwner, c.isManager, WhitelistAction.ADD_WHITELIST, c.config.whitelistPerms, c.globalConfig.whitelistPerms) # dev: no perms

#     assert _addr not in [empty(address), self, self.wallet, self.owner] # dev: invalid addr
#     assert not self._isWhitelisted(_addr) # dev: already whitelisted
#     assert self.pendingWhitelist[_addr].initiatedBlock == 0 # dev: pending whitelist already exists

#     # this uses same delay as ownership change
#     confirmBlock: uint256 = block.number + self.timeLock
#     self.pendingWhitelist[_addr] = PendingWhitelist(
#         initiatedBlock = block.number,
#         confirmBlock = confirmBlock,
#     )
#     log WhitelistAddrPending(addr=_addr, confirmBlock=confirmBlock, addedBy=msg.sender)


# # confirm whitelist


# @external
# def confirmWhitelistAddr(_user: address, _addr: address):
#     c: ManagerConfigBundle = self._getManagerConfigs(msg.sender, self.owner)
#     assert staticcall BossValidator(bossValidator).canManageWhitelist(msg.sender, c.isOwner, c.isManager, WhitelistAction.CONFIRM_WHITELIST, c.config.whitelistPerms, c.globalConfig.whitelistPerms) # dev: no perms

#     data: PendingWhitelist = self.pendingWhitelist[_addr]
#     assert data.initiatedBlock != 0 # dev: no pending whitelist
#     assert data.confirmBlock != 0 and block.number >= data.confirmBlock # dev: time delay not reached

#     self._registerWhitelist(_addr)
#     self.pendingWhitelist[_addr] = empty(PendingWhitelist)
#     log WhitelistAddrConfirmed(addr=_addr, initiatedBlock=data.initiatedBlock, confirmBlock=data.confirmBlock, confirmedBy=msg.sender)


# # cancel pending whitelist


# @external
# def cancelPendingWhitelistAddr(_user: address, _addr: address):
#     if not self._isSignerBackpack(msg.sender, self.inEjectMode):
#         c: ManagerConfigBundle = self._getManagerConfigs(msg.sender, self.owner)
#         assert staticcall BossValidator(bossValidator).canManageWhitelist(msg.sender, c.isOwner, c.isManager, WhitelistAction.CANCEL_WHITELIST, c.config.whitelistPerms, c.globalConfig.whitelistPerms) # dev: no perms

#     data: PendingWhitelist = self.pendingWhitelist[_addr]
#     assert data.initiatedBlock != 0 # dev: no pending whitelist
#     self.pendingWhitelist[_addr] = empty(PendingWhitelist)
#     log WhitelistAddrCancelled(addr=_addr, initiatedBlock=data.initiatedBlock, confirmBlock=data.confirmBlock, cancelledBy=msg.sender)


# # remove whitelist


# @external
# def removeWhitelistAddr(_user: address, _addr: address):
#     c: ManagerConfigBundle = self._getManagerConfigs(msg.sender, self.owner)
#     assert staticcall BossValidator(bossValidator).canManageWhitelist(msg.sender, c.isOwner, c.isManager, WhitelistAction.REMOVE_WHITELIST, c.config.whitelistPerms, c.globalConfig.whitelistPerms) # dev: no perms

#     assert self._isWhitelisted(_addr) # dev: not whitelisted
#     self._deregisterWhitelist(_addr)
#     log WhitelistAddrRemoved(addr=_addr, removedBy=msg.sender)


# # utils


# @view
# @internal
# def _validateAndGetWalletConfig(_user: address) -> address:
#     ledger: address = staticcall Registry(UNDY_HQ).getAddr(LEDGER_ID)
#     assert staticcall Ledger(ledger).isUserWallet(_user) # dev: not a user wallet
#     return staticcall UserWallet(_user).walletConfig()


# @view
# @external
# def canManageWhitelist(
#     _signer: address,
#     _isOwner: bool,
#     _isManager: bool,
#     _action: WhitelistAction,
#     _config: WhitelistPerms,
#     _globalConfig: WhitelistPerms,
# ) -> bool:

#     # check if signer is the owner
#     if _isOwner:
#         return True

#     # check if signer is a manager
#     if not _isManager:
#         return False 

#     # add to whitelist
#     if _action == WhitelistAction.ADD_WHITELIST:
#         return _config.canAddPending and _globalConfig.canAddPending
    
#     # confirm whitelist
#     elif _action == WhitelistAction.CONFIRM_WHITELIST:
#         return _config.canConfirm and _globalConfig.canConfirm
    
#     # cancel whitelist
#     elif _action == WhitelistAction.CANCEL_WHITELIST:
#         return _config.canCancel and _globalConfig.canCancel
    
#     # remove from whitelist
#     elif _action == WhitelistAction.REMOVE_WHITELIST:
#         return _config.canRemove and _globalConfig.canRemove
    
#     # invalid action
#     else:
#         return False



#############
# Utilities #
#############


# is signer backpack


# @view
# @internal
# def _isSignerBackpack(_signer: address, _inEjectMode: bool) -> bool:
#     if _inEjectMode:
#         return False
#     return _signer == staticcall Registry(UNDY_HQ).getAddr(BACKPACK_ID)