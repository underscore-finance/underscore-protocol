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
    def setGlobalManagerSettings(_config: wcs.GlobalManagerSettings): nonpayable
    def migrateFunds(_toWallet: address, _asset: address) -> uint256: nonpayable
    def addManager(_manager: address, _config: wcs.ManagerSettings): nonpayable
    def setGlobalPayeeSettings(_config: wcs.GlobalPayeeSettings): nonpayable
    def addPayee(_payee: address, _config: wcs.PayeeSettings): nonpayable
    def managerSettings(_manager: address) -> wcs.ManagerSettings: view
    def globalManagerSettings() -> wcs.GlobalManagerSettings: view
    def payeeSettings(_payee: address) -> wcs.PayeeSettings: view
    def addWhitelistAddrViaMigrator(_addr: address): nonpayable
    def globalPayeeSettings() -> wcs.GlobalPayeeSettings: view
    def deregisterAsset(_asset: address) -> bool: nonpayable
    def indexOfManager(_addr: address) -> uint256: view
    def whitelistAddr(i: uint256) -> address: view
    def managers(i: uint256) -> address: view
    def hasPendingOwnerChange() -> bool: view
    def payees(i: uint256) -> address: view
    def numActiveCheques() -> uint256: view
    def numWhitelisted() -> uint256: view
    def startingAgent() -> address: view
    def numManagers() -> uint256: view
    def numPayees() -> uint256: view
    def groupId() -> uint256: view
    def owner() -> address: view
    def isFrozen() -> bool: view

interface UserWallet:
    def assetData(_asset: address) -> ws.WalletAssetData: view
    def assets(i: uint256) -> address: view
    def walletConfig() -> address: view
    def numAssets() -> uint256: view

interface Ledger:
    def isUserWallet(_user: address) -> bool: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

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

UNDY_HQ: public(immutable(address))
LEDGER_ID: constant(uint256) = 1
MAX_DEREGISTER_ASSETS: constant(uint256) = 25


@deploy
def __init__(_undyHq: address):
    assert _undyHq != empty(address) # dev: invalid undy hq
    UNDY_HQ = _undyHq


############################
# Migrate - Funds & Config #
############################


@external
def migrateAll(_fromWallet: address, _toWallet: address) -> (uint256, bool):

    # migrate funds
    numFundsMigrated: uint256 = 0
    if self._canMigrateFundsToNewWallet(_fromWallet, _toWallet, msg.sender):
        numAssets: uint256 = staticcall UserWallet(_fromWallet).numAssets()
        if numAssets > 1:
            numFundsMigrated = self._migrateFunds(_fromWallet, _toWallet, numAssets)
            assert numFundsMigrated != 0 # dev: no assets migrated

    # migrate config
    didMigrateConfig: bool = False
    if self._canCopyWalletConfig(_fromWallet, _toWallet, msg.sender):
        didMigrateConfig = self._cloneConfig(_fromWallet, _toWallet)

    assert numFundsMigrated != 0 or didMigrateConfig # dev: no funds or config to migrate
    return numFundsMigrated, didMigrateConfig


#################
# Migrate Funds #
#################


@external
def migrateFunds(_fromWallet: address, _toWallet: address) -> uint256:
    assert self._canMigrateFundsToNewWallet(_fromWallet, _toWallet, msg.sender) # dev: invalid migration

    # validate fromWallet has assets to migrate
    numAssets: uint256 = staticcall UserWallet(_fromWallet).numAssets()
    assert numAssets > 1 # dev: no assets to migrate

    # migrate funds
    numMigrated: uint256 = self._migrateFunds(_fromWallet, _toWallet, numAssets)
    assert numMigrated != 0 # dev: no assets migrated

    return numMigrated


@internal
def _migrateFunds(_fromWallet: address, _toWallet: address, _numAssets: uint256) -> uint256:

    # get wallet config
    walletConfig: address = staticcall UserWallet(_fromWallet).walletConfig()

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
    return self._canMigrateFundsToNewWallet(_fromWallet, _toWallet, _caller)


@view
@internal
def _canMigrateFundsToNewWallet(_fromWallet: address, _toWallet: address, _caller: address) -> bool:
    ledger: address = staticcall Registry(UNDY_HQ).getAddr(LEDGER_ID)

    # validate fromWallet is Underscore wallet
    if not staticcall Ledger(ledger).isUserWallet(_fromWallet):
        return False

    # validate toWallet is Underscore wallet
    if not staticcall Ledger(ledger).isUserWallet(_toWallet):
        return False

    # get fromWallet data
    fromData: wcs.MigrationConfigBundle = self._getMigrationConfigBundle(_fromWallet)

    # validate caller is owner of fromWallet
    if _caller != fromData.owner:
        return False

    # cannot migrate if fromWallet is frozen
    if fromData.isFrozen:
        return False

    # cannot migrate if fromWallet has pending owner change
    if fromData.hasPendingOwnerChange:
        return False

    # toWallet bundle
    toData: wcs.MigrationConfigBundle = self._getMigrationConfigBundle(_toWallet)

    # owners must be the same
    if fromData.owner != toData.owner:
        return False

    # cannot migrate if toWallet has pending owner change
    if toData.hasPendingOwnerChange:
        return False

    # group id must be the same
    if fromData.groupId != toData.groupId:
        return False

    # cannot migrate if toWallet is frozen
    if toData.isFrozen:
        return False

    # toWallet cannot have any payees
    if toData.numPayees > 1:
        return False

    # toWallet cannot have any whitelisted addresses
    if toData.numWhitelisted > 1:
        return False

    # toWallet cannot have any active cheques
    if toData.numActiveCheques != 0:
        return False

    # cannot have managers (if starting agent is not set)
    if toData.startingAgent == empty(address) and toData.numManagers > 1:
        return False
    
    # cannot have managers other than starting agent
    if toData.startingAgent != empty(address):
        if toData.startingAgentIndex != 1:
            return False
        if toData.numManagers > 2:
            return False

    return True


################
# Clone Config #
################


@external
def cloneConfig(_fromWallet: address, _toWallet: address) -> bool:
    assert self._canCopyWalletConfig(_fromWallet, _toWallet, msg.sender) # dev: cannot copy config
    return self._cloneConfig(_fromWallet, _toWallet)


@internal
def _cloneConfig(_fromWallet: address, _toWallet: address) -> bool:
    fromConfig: address = staticcall UserWallet(_fromWallet).walletConfig()
    toConfig: address = staticcall UserWallet(_toWallet).walletConfig()

    # 1. copy global manager settings
    globalManagerSettings: wcs.GlobalManagerSettings = staticcall UserWalletConfig(fromConfig).globalManagerSettings()
    extcall UserWalletConfig(toConfig).setGlobalManagerSettings(globalManagerSettings)

    # get starting agent from source wallet to skip it during copy
    fromStartingAgent: address = staticcall UserWalletConfig(fromConfig).startingAgent()
    
    # 2. copy all managers (except starting agent)
    managersCopied: uint256 = 0
    numManagers: uint256 = staticcall UserWalletConfig(fromConfig).numManagers()
    if numManagers > 1:
        for i: uint256 in range(1, numManagers, bound=max_value(uint256)):
            manager: address = staticcall UserWalletConfig(fromConfig).managers(i)
            if manager == empty(address):
                continue

            # skip the starting agent from source wallet
            if manager == fromStartingAgent:
                continue

            managerSettings: wcs.ManagerSettings = staticcall UserWalletConfig(fromConfig).managerSettings(manager)
            if managerSettings.startBlock != 0:
                extcall UserWalletConfig(toConfig).addManager(manager, managerSettings)
                managersCopied += 1

    # 3. copy global payee settings
    globalPayeeSettings: wcs.GlobalPayeeSettings = staticcall UserWalletConfig(fromConfig).globalPayeeSettings()
    extcall UserWalletConfig(toConfig).setGlobalPayeeSettings(globalPayeeSettings)
    
    # 4. copy all payees
    payeesCopied: uint256 = 0
    numPayees: uint256 = staticcall UserWalletConfig(fromConfig).numPayees()
    if numPayees > 1:
        for i: uint256 in range(1, numPayees, bound=max_value(uint256)):
            payee: address = staticcall UserWalletConfig(fromConfig).payees(i)
            if payee == empty(address):
                continue

            payeeSettings: wcs.PayeeSettings = staticcall UserWalletConfig(fromConfig).payeeSettings(payee)
            if payeeSettings.startBlock != 0:
                extcall UserWalletConfig(toConfig).addPayee(payee, payeeSettings)
                payeesCopied += 1

    # 5. copy all whitelisted addresses
    whitelistCopied: uint256 = 0
    numWhitelisted: uint256 = staticcall UserWalletConfig(fromConfig).numWhitelisted()
    if numWhitelisted > 1:
        for i: uint256 in range(1, numWhitelisted, bound=max_value(uint256)):
            addr: address = staticcall UserWalletConfig(fromConfig).whitelistAddr(i)
            if addr != empty(address):
                extcall UserWalletConfig(toConfig).addWhitelistAddrViaMigrator(addr)
                whitelistCopied += 1

    # NOTE (FIX L-04): Cheque settings are NOT migrated - destination wallet uses default settings
    # Individual cheques are also NOT migrated - users must manually recreate them
    # Validation ensures destination has no active cheques before migration

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
    return self._canCopyWalletConfig(_fromWallet, _toWallet, _caller)


@view
@internal
def _canCopyWalletConfig(_fromWallet: address, _toWallet: address, _caller: address) -> bool:
    ledger: address = staticcall Registry(UNDY_HQ).getAddr(LEDGER_ID)

    # validate fromWallet is Underscore wallet
    if not staticcall Ledger(ledger).isUserWallet(_fromWallet):
        return False

    # validate toWallet is Underscore wallet
    if not staticcall Ledger(ledger).isUserWallet(_toWallet):
        return False

    # get toWallet data
    toData: wcs.MigrationConfigBundle = self._getMigrationConfigBundle(_toWallet)

    # validate caller is owner of toWallet
    if _caller != toData.owner:
        return False

    # cannot copy if toWallet has pending owner change
    if toData.hasPendingOwnerChange:
        return False

    # cannot copy if toWallet is frozen
    if toData.isFrozen:
        return False

    # toWallet cannot have any payees
    if toData.numPayees > 1:
        return False

    # toWallet cannot have any whitelisted addresses
    if toData.numWhitelisted > 1:
        return False

    # toWallet cannot have any active cheques
    if toData.numActiveCheques != 0:
        return False

    # cannot have managers (if starting agent is not set)
    if toData.startingAgent == empty(address) and toData.numManagers > 1:
        return False
    
    # cannot have managers other than starting agent
    if toData.startingAgent != empty(address):
        if toData.startingAgentIndex != 1:
            return False
        if toData.numManagers > 2:
            return False

    # fromWallet bundle
    fromData: wcs.MigrationConfigBundle = self._getMigrationConfigBundle(_fromWallet)

    # cannot copy if fromWallet is frozen
    if fromData.isFrozen:
        return False

    # owners must be the same
    if fromData.owner != toData.owner:
        return False

    # group id must be the same
    if fromData.groupId != toData.groupId:
        return False

    # cannot copy if fromWallet has pending owner change
    if fromData.hasPendingOwnerChange:
        return False

    return True


#############
# Utilities #
#############


@view
@external
def getMigrationConfigBundle(_userWallet: address) -> wcs.MigrationConfigBundle:
    return self._getMigrationConfigBundle(_userWallet)


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
