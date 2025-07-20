#    ┓ ┏  ┓┓   
#    ┃┃┃┏┓┃┃┏┓╋
#    ┗┻┛┗┻┗┗┗ ┗
#     __  __   ______   ______   __   __   ______   __        
#    /\ \/ /  /\  ___\ /\  == \ /\ "-.\ \ /\  ___\ /\ \       
#    \ \  _"-.\ \  __\ \ \  __< \ \ \-.  \\ \  __\ \ \ \____  
#     \ \_\ \_\\ \_____\\ \_\ \_\\ \_\\"\_\\ \_____\\ \_____\ 
#      \/_/\/_/ \/_____/ \/_/ /_/ \/_/ \/_/ \/_____/ \/_____/ 
#                                                         
#     ╔═══════════════════════════════════════════╗
#     ║  ** Kernel **                             ║
#     ║  Whitelist management for user wallets.   ║
#     ╚═══════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/hightophq/underscore-protocol/blob/master/LICENSE.md
#     Hightop Financial, Inc. (C) 2025   

# @version 0.4.3

from interfaces import WalletConfigStructs as wcs

interface UserWalletConfig:
    def addPendingWhitelistAddr(_addr: address, _pending: wcs.PendingWhitelist): nonpayable
    def pendingWhitelist(_addr: address) -> wcs.PendingWhitelist: view
    def managerSettings(_addr: address) -> wcs.ManagerSettings: view
    def globalManagerSettings() -> wcs.GlobalManagerSettings: view
    def cancelPendingWhitelistAddr(_addr: address): nonpayable
    def indexOfWhitelist(_addr: address) -> uint256: view
    def confirmWhitelistAddr(_addr: address): nonpayable
    def removeWhitelistAddr(_addr: address): nonpayable
    def indexOfManager(_addr: address) -> uint256: view
    def timeLock() -> uint256: view
    def wallet() -> address: view
    def owner() -> address: view

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

UNDY_HQ: public(immutable(address))
LEDGER_ID: constant(uint256) = 1
MISSION_CONTROL_ID: constant(uint256) = 2


@deploy
def __init__(_undyHq: address):
    assert _undyHq != empty(address) # dev: invalid undy hq
    UNDY_HQ = _undyHq


########################
# Whitelist Management #
########################


# add whitelist


@nonreentrant
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


@nonreentrant
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


@nonreentrant
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


@nonreentrant
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
