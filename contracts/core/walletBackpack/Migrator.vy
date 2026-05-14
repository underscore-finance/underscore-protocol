#    ┓ ┏  ┓┓   
#    ┃┃┃┏┓┃┃┏┓╋
#    ┗┻┛┗┻┗┗┗ ┗
#     __    __   __   ______   ______   ______   ______  ______   ______    
#    /\ "-./  \ /\ \ /\  ___\ /\  == \ /\  __ \ /\__  _\/\  __ \ /\  == \   
#    \ \ \-./\ \\ \ \\ \ \__ \\ \  __< \ \  __ \\/_/\ \/\ \ \/\ \\ \  __<   
#     \ \_\ \ \_\\ \_\\ \_____\\ \_\ \_\\ \_\ \_\  \ \_\ \ \_____\\ \_\ \_\ 
#      \/_/  \/_/ \/_/ \/_____/ \/_/ /_/ \/_/\/_/   \/_/  \/_____/ \/_/ /_/ 
#                                                         
#     ╔═══════════════════════════════════════════════════╗
#     ║  ** Migrator **                                   ║
#     ║  Migrate funds and config between user wallets.   ║
#     ╚═══════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

from interfaces import WalletStructs as ws
from interfaces import WalletConfigStructs as wcs
from ethereum.ercs import IERC20

interface UserWalletConfig:
    def applyMigratedConfigSettings(_fromConfig: address, _timeLock: uint256, _instantSettings: wcs.InstantActionSettings, _globalManagerSettings: wcs.GlobalManagerSettings, _globalPayeeSettings: wcs.GlobalPayeeSettings, _chequeSettings: wcs.ChequeSettings): nonpayable
    def updateAssetData(_legoId: uint256, _asset: address, _shouldCheckYield: bool) -> uint256: nonpayable
    def updateManager(_manager: address, _config: wcs.ManagerSettings): nonpayable
    def pendingInstantActionSettings() -> wcs.PendingInstantActionSettings: view
    def migrateFunds(_toWallet: address, _asset: address) -> uint256: nonpayable
    def addManager(_manager: address, _config: wcs.ManagerSettings): nonpayable
    def addPayee(_payee: address, _config: wcs.PayeeSettings): nonpayable
    def managerSettings(_manager: address) -> wcs.ManagerSettings: view
    def pendingOwnershipTimeLock() -> PendingOwnershipTimeLock: view
    def globalManagerSettings() -> wcs.GlobalManagerSettings: view
    def instantActionSettings() -> wcs.InstantActionSettings: view
    def payeeSettings(_payee: address) -> wcs.PayeeSettings: view
    def globalPayeeSettings() -> wcs.GlobalPayeeSettings: view
    def addWhitelistAddrViaMigrator(_addr: address): nonpayable
    def setPendingMigration(_toWallet: address): nonpayable
    def indexOfWhitelist(_addr: address) -> uint256: view
    def pendingMigration() -> wcs.PendingMigration: view
    def indexOfManager(_addr: address) -> uint256: view
    def indexOfPayee(_addr: address) -> uint256: view
    def pendingTimeLock() -> wcs.PendingTimeLock: view
    def chequeSettings() -> wcs.ChequeSettings: view
    def deregisterAsset(_asset: address): nonpayable
    def cheques(_addr: address) -> wcs.Cheque: view
    def whitelistAddr(i: uint256) -> address: view
    def managers(i: uint256) -> address: view
    def hasPendingOwnerChange() -> bool: view
    def payees(i: uint256) -> address: view
    def numActiveCheques() -> uint256: view
    def clearPendingMigration(): nonpayable
    def numWhitelisted() -> uint256: view
    def startingAgent() -> address: view
    def numManagers() -> uint256: view
    def chequeBook() -> address: view
    def paymaster() -> address: view
    def numPayees() -> uint256: view
    def migrator() -> address: view
    def timeLock() -> uint256: view
    def groupId() -> uint256: view
    def owner() -> address: view
    def isFrozen() -> bool: view

interface UserWallet:
    def assetData(_asset: address) -> ws.WalletAssetData: view
    def assets(i: uint256) -> address: view
    def walletConfig() -> address: view
    def numAssets() -> uint256: view

interface Ledger:
    def isRegisteredBackpackItem(_addr: address) -> bool: view
    def isUserWallet(_user: address) -> bool: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view
    def isValidAddr(_addr: address) -> bool: view

interface Paymaster:
    def hasPendingGlobalPayeeSettings(_userWallet: address) -> bool: view

interface ChequeBook:
    def hasPendingChequeSettings(_userWallet: address) -> bool: view

interface MissionControl:
    def canPerformSecurityAction(_addr: address) -> bool: view

interface Switchboard:
    def isSwitchboardAddr(_addr: address) -> bool: view

struct PendingOwnershipTimeLock:
    newTimeLock: uint256
    initiatedBlock: uint256
    confirmBlock: uint256
    currentOwner: address

event FundsMigrated:
    fromWallet: indexed(address)
    toWallet: indexed(address)
    numAssetsMigrated: uint256
    totalUsdValue: uint256

event ConfigCloned:
    fromWallet: indexed(address)
    toWallet: indexed(address)
    numManagersCopied: uint256
    numPayeesCopied: uint256
    numWhitelistCopied: uint256

event InstantMigrationEnabledSet:
    isEnabled: bool
    caller: indexed(address)

event PendingMigrationInitiated:
    fromWallet: indexed(address)
    toWallet: indexed(address)
    initiatedBlock: uint256
    confirmBlock: uint256
    currentOwner: indexed(address)

event PendingMigrationConfirmed:
    fromWallet: indexed(address)
    toWallet: indexed(address)
    initiatedBlock: uint256
    confirmBlock: uint256

event PendingMigrationCancelled:
    fromWallet: indexed(address)
    toWallet: indexed(address)
    initiatedBlock: uint256
    confirmBlock: uint256
    cancelledBy: indexed(address)

UNDY_HQ: public(immutable(address))
LEDGER_ID: constant(uint256) = 1
MISSION_CONTROL_ID: constant(uint256) = 2
SWITCHBOARD_ID: constant(uint256) = 4
MAX_DEREGISTER_ASSETS: constant(uint256) = 25

instantMigrationEnabled: public(bool)


@deploy
def __init__(_undyHq: address, _instantMigrationEnabled: bool):
    assert _undyHq != empty(address) # dev: invalid undy hq
    assert _undyHq.is_contract # dev: invalid undy hq
    UNDY_HQ = _undyHq
    self.instantMigrationEnabled = _instantMigrationEnabled


#####################
# Migration Control #
#####################


@external
def setInstantMigrationEnabled(_isEnabled: bool) -> bool:
    assert self._isSwitchboardAddr(msg.sender) # dev: no perms
    self.instantMigrationEnabled = _isEnabled
    log InstantMigrationEnabledSet(isEnabled = _isEnabled, caller = msg.sender)
    return True


@external
def initiateMigration(_fromWallet: address, _toWallet: address) -> bool:
    assert _toWallet != empty(address) # dev: invalid migration
    assert not self.instantMigrationEnabled # dev: instant migration enabled
    assert (
        self._canMigrateFundsToNewWallet(_fromWallet, _toWallet, msg.sender, False) or
        self._canCopyWalletConfig(_fromWallet, _toWallet, msg.sender, False)
    ) # dev: invalid migration

    fromConfig: address = staticcall UserWallet(_fromWallet).walletConfig()
    existingPending: wcs.PendingMigration = staticcall UserWalletConfig(fromConfig).pendingMigration()
    assert existingPending.confirmBlock == 0 # dev: pending migration exists
    extcall UserWalletConfig(fromConfig).setPendingMigration(_toWallet)
    pending: wcs.PendingMigration = staticcall UserWalletConfig(fromConfig).pendingMigration()
    log PendingMigrationInitiated(
        fromWallet = _fromWallet,
        toWallet = _toWallet,
        initiatedBlock = pending.initiatedBlock,
        confirmBlock = pending.confirmBlock,
        currentOwner = pending.currentOwner,
    )
    return True


@external
def cancelPendingMigration(_fromWallet: address) -> bool:
    assert self._isValidUserWallet(_fromWallet) # dev: invalid user wallet

    fromConfig: address = staticcall UserWallet(_fromWallet).walletConfig()
    pending: wcs.PendingMigration = staticcall UserWalletConfig(fromConfig).pendingMigration()
    assert pending.confirmBlock != 0 # dev: no pending migration

    owner: address = staticcall UserWalletConfig(fromConfig).owner()
    if msg.sender != owner:
        assert self._canPerformSecurityAction(msg.sender) # dev: no perms

    extcall UserWalletConfig(fromConfig).clearPendingMigration()
    log PendingMigrationCancelled(
        fromWallet = _fromWallet,
        toWallet = pending.toWallet,
        initiatedBlock = pending.initiatedBlock,
        confirmBlock = pending.confirmBlock,
        cancelledBy = msg.sender,
    )
    return True


############################
# Migrate - Funds & Config #
############################


@nonreentrant
@external
def migrateAll(_fromWallet: address, _toWallet: address) -> (uint256, bool):
    assert _fromWallet != _toWallet # dev: invalid migration

    # migrate funds
    numFundsMigrated: uint256 = 0
    if self._canMigrateFundsToNewWallet(_fromWallet, _toWallet, msg.sender, True):
        numAssets: uint256 = staticcall UserWallet(_fromWallet).numAssets()
        if numAssets > 1:
            numFundsMigrated = self._migrateFunds(_fromWallet, _toWallet, numAssets)

    # migrate config
    didMigrateConfig: bool = False
    if self._canCopyWalletConfig(_fromWallet, _toWallet, msg.sender, True):
        didMigrateConfig = self._cloneConfig(_fromWallet, _toWallet)

    assert numFundsMigrated != 0 or didMigrateConfig # dev: no funds or config to migrate
    self._confirmAndClearPendingMigration(_fromWallet, _toWallet)
    return numFundsMigrated, didMigrateConfig


#################
# Migrate Funds #
#################


@nonreentrant
@external
def migrateFunds(_fromWallet: address, _toWallet: address) -> uint256:
    assert self._canMigrateFundsToNewWallet(_fromWallet, _toWallet, msg.sender, True) # dev: invalid migration

    # validate fromWallet has assets to migrate
    numAssets: uint256 = staticcall UserWallet(_fromWallet).numAssets()
    assert numAssets > 1 # dev: no assets to migrate

    # migrate funds
    numMigrated: uint256 = self._migrateFunds(_fromWallet, _toWallet, numAssets)
    assert numMigrated != 0 # dev: no assets migrated

    self._confirmAndClearPendingMigration(_fromWallet, _toWallet)
    return numMigrated


@internal
def _migrateFunds(_fromWallet: address, _toWallet: address, _numAssets: uint256) -> uint256:

    # get wallet config
    walletConfig: address = staticcall UserWallet(_fromWallet).walletConfig()
    toConfig: address = staticcall UserWallet(_toWallet).walletConfig()

    # migrate funds
    numMigrated: uint256 = 0
    usdValue: uint256 = 0
    assetsToDeregister: DynArray[address, MAX_DEREGISTER_ASSETS] = []
    for i: uint256 in range(1, _numAssets, bound=max_value(uint256)):
        asset: address = staticcall UserWallet(_fromWallet).assets(i)
        if asset == empty(address):
            continue

        # check balance
        balance: uint256 = staticcall IERC20(asset).balanceOf(_fromWallet)
        if balance == 0:
            continue

        # get last usd value
        data: ws.WalletAssetData = staticcall UserWallet(_fromWallet).assetData(asset)

        # transfer funds
        amount: uint256 = extcall UserWalletConfig(walletConfig).migrateFunds(_toWallet, asset)
        if amount != 0:
            extcall UserWalletConfig(toConfig).updateAssetData(0, asset, False)
            numMigrated += 1
            usdValue += data.usdValue

            if len(assetsToDeregister) < MAX_DEREGISTER_ASSETS:
                assetsToDeregister.append(asset)

    # deregister assets
    if len(assetsToDeregister) != 0:
        for asset: address in assetsToDeregister:
            extcall UserWalletConfig(walletConfig).deregisterAsset(asset)

    log FundsMigrated(fromWallet = _fromWallet, toWallet = _toWallet, numAssetsMigrated = numMigrated, totalUsdValue = usdValue)
    return numMigrated


# validation


@view
@external
def canMigrateFundsToNewWallet(_fromWallet: address, _toWallet: address, _caller: address) -> bool:
    return self._canMigrateFundsToNewWallet(_fromWallet, _toWallet, _caller, False)


@view
@internal
def _canMigrateFundsToNewWallet(_fromWallet: address, _toWallet: address, _caller: address, _requirePending: bool) -> bool:
    return self._canExecuteWalletMigration(_fromWallet, _toWallet, _caller, _requirePending)


################
# Clone Config #
################


@nonreentrant
@external
def cloneConfig(_fromWallet: address, _toWallet: address) -> bool:
    assert self._canCopyWalletConfig(_fromWallet, _toWallet, msg.sender, True) # dev: cannot copy config
    didClone: bool = self._cloneConfig(_fromWallet, _toWallet)
    self._confirmAndClearPendingMigration(_fromWallet, _toWallet)
    return didClone


@internal
def _cloneConfig(_fromWallet: address, _toWallet: address) -> bool:
    fromConfig: address = staticcall UserWallet(_fromWallet).walletConfig()
    toConfig: address = staticcall UserWallet(_toWallet).walletConfig()
    toOwner: address = staticcall UserWalletConfig(toConfig).owner()

    timeLock: uint256 = staticcall UserWalletConfig(fromConfig).timeLock()
    instantSettings: wcs.InstantActionSettings = staticcall UserWalletConfig(fromConfig).instantActionSettings()
    globalManagerSettings: wcs.GlobalManagerSettings = staticcall UserWalletConfig(fromConfig).globalManagerSettings()
    globalPayeeSettings: wcs.GlobalPayeeSettings = staticcall UserWalletConfig(fromConfig).globalPayeeSettings()
    chequeSettings: wcs.ChequeSettings = staticcall UserWalletConfig(fromConfig).chequeSettings()

    # get starting agent from source wallet to skip it during copy
    fromStartingAgent: address = staticcall UserWalletConfig(fromConfig).startingAgent()

    # copy all managers (except starting agent)
    managersCopied: uint256 = 0
    numManagers: uint256 = staticcall UserWalletConfig(fromConfig).numManagers()
    if numManagers > 1:
        for i: uint256 in range(1, numManagers, bound=max_value(uint256)):
            manager: address = staticcall UserWalletConfig(fromConfig).managers(i)
            if manager == empty(address):
                continue
            if manager in [toOwner, _toWallet, toConfig]:
                continue

            # skip the starting agent from source wallet
            if manager == fromStartingAgent:
                continue

            managerSettings: wcs.ManagerSettings = staticcall UserWalletConfig(fromConfig).managerSettings(manager)
            if managerSettings.startBlock != 0:
                assert self._isValidMigratorConfigAddr(toConfig, manager, True) # dev: manager collision on clone
                extcall UserWalletConfig(toConfig).addManager(manager, managerSettings)
                managersCopied += 1

    # transfer starter agent settings
    if fromStartingAgent != empty(address):
        if staticcall UserWalletConfig(toConfig).startingAgent() == fromStartingAgent:
            sourceStarterSettings: wcs.ManagerSettings = staticcall UserWalletConfig(fromConfig).managerSettings(fromStartingAgent)
            if sourceStarterSettings.startBlock != 0:
                destStarterSettings: wcs.ManagerSettings = staticcall UserWalletConfig(toConfig).managerSettings(fromStartingAgent)
                destStarterSettings.limits = sourceStarterSettings.limits
                destStarterSettings.legoPerms = sourceStarterSettings.legoPerms
                destStarterSettings.swapPerms = sourceStarterSettings.swapPerms
                destStarterSettings.whitelistPerms = sourceStarterSettings.whitelistPerms
                destStarterSettings.transferPerms = sourceStarterSettings.transferPerms
                destStarterSettings.allowedAssets = sourceStarterSettings.allowedAssets
                destStarterSettings.canClaimLoot = sourceStarterSettings.canClaimLoot
                extcall UserWalletConfig(toConfig).updateManager(fromStartingAgent, destStarterSettings)

    # copy all payees
    payeesCopied: uint256 = 0
    numPayees: uint256 = staticcall UserWalletConfig(fromConfig).numPayees()
    if numPayees > 1:
        for i: uint256 in range(1, numPayees, bound=max_value(uint256)):
            payee: address = staticcall UserWalletConfig(fromConfig).payees(i)
            if payee in [empty(address), toOwner, _toWallet, toConfig]:
                continue

            payeeSettings: wcs.PayeeSettings = staticcall UserWalletConfig(fromConfig).payeeSettings(payee)
            if payeeSettings.startBlock != 0:
                assert self._isValidMigratorConfigAddr(toConfig, payee, False) # dev: payee collision on clone
                extcall UserWalletConfig(toConfig).addPayee(payee, payeeSettings)
                payeesCopied += 1

    # copy all whitelisted addresses
    whitelistCopied: uint256 = 0
    numWhitelisted: uint256 = staticcall UserWalletConfig(fromConfig).numWhitelisted()
    if numWhitelisted > 1:
        for i: uint256 in range(1, numWhitelisted, bound=max_value(uint256)):
            addr: address = staticcall UserWalletConfig(fromConfig).whitelistAddr(i)
            if addr in [empty(address), toOwner, _toWallet, toConfig]:
                continue

            assert self._isValidMigratorConfigAddr(toConfig, addr, False) # dev: invalid addr
            extcall UserWalletConfig(toConfig).addWhitelistAddrViaMigrator(addr)
            whitelistCopied += 1

    # Individual cheques are NOT migrated - users must manually recreate them.
    # Validation ensures destination has no active cheques before migration

    # Apply scalar settings after the loops so the destination event pairs with ConfigCloned counts.
    extcall UserWalletConfig(toConfig).applyMigratedConfigSettings(
        fromConfig,
        timeLock,
        instantSettings,
        globalManagerSettings,
        globalPayeeSettings,
        chequeSettings,
    )

    log ConfigCloned(
        fromWallet = _fromWallet,
        toWallet = _toWallet,
        numManagersCopied = managersCopied,
        numPayeesCopied = payeesCopied,
        numWhitelistCopied = whitelistCopied
    )
    return True


# validation


@view
@external
def canCopyWalletConfig(_fromWallet: address, _toWallet: address, _caller: address) -> bool:
    return self._canCopyWalletConfig(_fromWallet, _toWallet, _caller, False)


@view
@internal
def _canCopyWalletConfig(_fromWallet: address, _toWallet: address, _caller: address, _requirePending: bool) -> bool:
    return self._canExecuteWalletMigration(_fromWallet, _toWallet, _caller, _requirePending)


#############
# Utilities #
#############


@view
@external
def getMigrationConfigBundle(_userWallet: address) -> wcs.MigrationConfigBundle:
    return self._getMigrationConfigBundle(_userWallet)


@view
@internal
def _isValidUserWallet(_userWallet: address) -> bool:
    ledger: address = staticcall Registry(UNDY_HQ).getAddr(LEDGER_ID)
    if ledger == empty(address):
        return False
    return staticcall Ledger(ledger).isUserWallet(_userWallet)


@view
@internal
def _canExecuteMigration(_caller: address, _owner: address) -> bool:
    if _caller == _owner:
        return True
    return self._isSwitchboardAddr(_caller)


@view
@internal
def _canExecuteWalletMigration(_fromWallet: address, _toWallet: address, _caller: address, _requirePending: bool) -> bool:
    if not self._hasValidMigrationPair(_fromWallet, _toWallet, _requirePending):
        return False

    fromData: wcs.MigrationConfigBundle = self._getMigrationConfigBundle(_fromWallet)
    toData: wcs.MigrationConfigBundle = self._getMigrationConfigBundle(_toWallet)

    if fromData.owner != toData.owner:
        return False
    if not self._canExecuteMigration(_caller, fromData.owner):
        return False
    if fromData.groupId != toData.groupId:
        return False
    if not self._isMigrationSourceReady(fromData):
        return False
    if not self._isMigrationDestinationReady(toData):
        return False

    return True


@view
@internal
def _hasValidMigrationPair(_fromWallet: address, _toWallet: address, _requirePending: bool) -> bool:
    if _fromWallet == _toWallet:
        return False
    if not self._isValidUserWallet(_fromWallet):
        return False
    if not self._isValidUserWallet(_toWallet):
        return False

    fromConfig: address = staticcall UserWallet(_fromWallet).walletConfig()
    toConfig: address = staticcall UserWallet(_toWallet).walletConfig()
    if staticcall UserWalletConfig(fromConfig).migrator() != self:
        return False
    if staticcall UserWalletConfig(toConfig).migrator() != self:
        return False

    if _requirePending and not self.instantMigrationEnabled:
        if not self._hasValidPendingMigration(_fromWallet, _toWallet):
            return False

    if self._hasBlockingPendingMigrationState(_fromWallet):
        return False
    if self._hasBlockingPendingMigrationState(_toWallet):
        return False

    return True


@view
@internal
def _hasBlockingPendingMigrationState(_userWallet: address) -> bool:
    if self._hasPendingChequeSettings(_userWallet):
        return True
    if self._hasPendingGlobalPayeeSettings(_userWallet):
        return True
    if self._hasPendingTimeLock(_userWallet):
        return True
    if self._hasPendingInstantActionSettings(_userWallet):
        return True
    if self._hasPendingOwnershipTimeLock(_userWallet):
        return True

    return False


@pure
@internal
def _isMigrationSourceReady(_data: wcs.MigrationConfigBundle) -> bool:
    if _data.isFrozen:
        return False
    if _data.hasPendingOwnerChange:
        return False
    if _data.numActiveCheques != 0:
        return False

    return True


@pure
@internal
def _isMigrationDestinationReady(_data: wcs.MigrationConfigBundle) -> bool:
    if not self._isMigrationSourceReady(_data):
        return False
    if _data.numPayees > 1:
        return False
    if _data.numWhitelisted > 1:
        return False
    if _data.startingAgent == empty(address) and _data.numManagers > 1:
        return False
    if _data.startingAgent != empty(address):
        if _data.startingAgentIndex != 1:
            return False
        if _data.numManagers > 2:
            return False

    return True


@view
@internal
def _hasPendingChequeSettings(_userWallet: address) -> bool:
    walletConfig: address = staticcall UserWallet(_userWallet).walletConfig()
    chequeBook: address = staticcall UserWalletConfig(walletConfig).chequeBook()
    return staticcall ChequeBook(chequeBook).hasPendingChequeSettings(_userWallet)


@view
@internal
def _hasPendingGlobalPayeeSettings(_userWallet: address) -> bool:
    walletConfig: address = staticcall UserWallet(_userWallet).walletConfig()
    paymaster: address = staticcall UserWalletConfig(walletConfig).paymaster()
    return staticcall Paymaster(paymaster).hasPendingGlobalPayeeSettings(_userWallet)


@view
@internal
def _hasPendingTimeLock(_userWallet: address) -> bool:
    walletConfig: address = staticcall UserWallet(_userWallet).walletConfig()
    pending: wcs.PendingTimeLock = staticcall UserWalletConfig(walletConfig).pendingTimeLock()
    return pending.confirmBlock != 0


@view
@internal
def _hasPendingInstantActionSettings(_userWallet: address) -> bool:
    walletConfig: address = staticcall UserWallet(_userWallet).walletConfig()
    pending: wcs.PendingInstantActionSettings = staticcall UserWalletConfig(walletConfig).pendingInstantActionSettings()
    return pending.confirmBlock != 0


@view
@internal
def _hasPendingOwnershipTimeLock(_userWallet: address) -> bool:
    walletConfig: address = staticcall UserWallet(_userWallet).walletConfig()
    pending: PendingOwnershipTimeLock = staticcall UserWalletConfig(walletConfig).pendingOwnershipTimeLock()
    return pending.confirmBlock != 0


@view
@internal
def _hasValidPendingMigration(_fromWallet: address, _toWallet: address) -> bool:
    fromConfig: address = staticcall UserWallet(_fromWallet).walletConfig()
    pending: wcs.PendingMigration = staticcall UserWalletConfig(fromConfig).pendingMigration()
    if pending.confirmBlock == 0:
        return False
    if pending.toWallet != _toWallet:
        return False
    if block.number < pending.confirmBlock:
        return False
    if pending.currentOwner != staticcall UserWalletConfig(fromConfig).owner():
        return False
    return True


@internal
def _confirmAndClearPendingMigration(_fromWallet: address, _toWallet: address):
    fromConfig: address = staticcall UserWallet(_fromWallet).walletConfig()
    pending: wcs.PendingMigration = staticcall UserWalletConfig(fromConfig).pendingMigration()
    if pending.confirmBlock == 0:
        return

    assert pending.toWallet == _toWallet # dev: invalid migration
    assert block.number >= pending.confirmBlock # dev: time delay not reached
    assert pending.currentOwner == staticcall UserWalletConfig(fromConfig).owner() # dev: owner must match

    extcall UserWalletConfig(fromConfig).clearPendingMigration()
    log PendingMigrationConfirmed(
        fromWallet = _fromWallet,
        toWallet = _toWallet,
        initiatedBlock = pending.initiatedBlock,
        confirmBlock = pending.confirmBlock,
    )


@view
@internal
def _isSwitchboardAddr(_addr: address) -> bool:
    switchboard: address = staticcall Registry(UNDY_HQ).getAddr(SWITCHBOARD_ID)
    if switchboard == empty(address):
        return False
    return staticcall Switchboard(switchboard).isSwitchboardAddr(_addr)


@view
@internal
def _canPerformSecurityAction(_addr: address) -> bool:
    missionControl: address = staticcall Registry(UNDY_HQ).getAddr(MISSION_CONTROL_ID)
    if missionControl == empty(address):
        return False
    return staticcall MissionControl(missionControl).canPerformSecurityAction(_addr)


@view
@internal
def _isValidMigratorConfigAddr(_walletConfig: address, _addr: address, _isManagerSlot: bool) -> bool:
    # Destination wallets are prevalidated as effectively empty; keep these checks as defense
    # against validation regressions and starting-agent role collisions during cloning.
    if staticcall UserWalletConfig(_walletConfig).indexOfWhitelist(_addr) != 0:
        return False
    if staticcall UserWalletConfig(_walletConfig).indexOfPayee(_addr) != 0:
        return False
    cheque: wcs.Cheque = staticcall UserWalletConfig(_walletConfig).cheques(_addr)
    if cheque.active:
        return False
    if staticcall UserWalletConfig(_walletConfig).indexOfManager(_addr) != 0:
        return False
    if staticcall Registry(UNDY_HQ).isValidAddr(_addr):
        return False
    ledger: address = staticcall Registry(UNDY_HQ).getAddr(LEDGER_ID)
    if ledger != empty(address):
        if staticcall Ledger(ledger).isRegisteredBackpackItem(_addr):
            return False
        if _isManagerSlot and staticcall Ledger(ledger).isUserWallet(_addr):
            return False
    return True


@view
@internal
def _getMigrationConfigBundle(_userWallet: address) -> wcs.MigrationConfigBundle:
    walletConfig: address = staticcall UserWallet(_userWallet).walletConfig()
    startingAgent: address = staticcall UserWalletConfig(walletConfig).startingAgent()
    return wcs.MigrationConfigBundle(
        owner = staticcall UserWalletConfig(walletConfig).owner(),
        isFrozen = staticcall UserWalletConfig(walletConfig).isFrozen(),
        numPayees = staticcall UserWalletConfig(walletConfig).numPayees(),
        numWhitelisted = staticcall UserWalletConfig(walletConfig).numWhitelisted(),
        numManagers = staticcall UserWalletConfig(walletConfig).numManagers(),
        startingAgent = startingAgent,
        startingAgentIndex = staticcall UserWalletConfig(walletConfig).indexOfManager(startingAgent),
        hasPendingOwnerChange = staticcall UserWalletConfig(walletConfig).hasPendingOwnerChange(),
        groupId = staticcall UserWalletConfig(walletConfig).groupId(),
        numActiveCheques = staticcall UserWalletConfig(walletConfig).numActiveCheques(),
    )
