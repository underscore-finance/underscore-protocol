# @version 0.4.3

from interfaces import WalletStructs as ws
from interfaces import WalletConfigStructs as wcs

from ethereum.ercs import IERC20

interface UserWalletConfig:
    def transferFundsDuringMigration(_recipient: address, _asset: address, _amount: uint256, _ad: ws.ActionData) -> (uint256, uint256): nonpayable
    def getActionDataBundle(_legoId: uint256, _signer: address) -> ws.ActionData: view
    def setGlobalManagerSettings(_config: wcs.GlobalManagerSettings): nonpayable
    def addManager(_manager: address, _config: wcs.ManagerSettings): nonpayable
    def setGlobalPayeeSettings(_config: wcs.GlobalPayeeSettings): nonpayable
    def addPayee(_payee: address, _config: wcs.PayeeSettings): nonpayable
    def managerSettings(_manager: address) -> wcs.ManagerSettings: view
    def getMigrationConfigBundle() -> wcs.MigrationConfigBundle: view
    def addWhitelistAddrViaMigrator(_addr: address): nonpayable
    def globalManagerSettings() -> wcs.GlobalManagerSettings: view
    def payeeSettings(_payee: address) -> wcs.PayeeSettings: view
    def globalPayeeSettings() -> wcs.GlobalPayeeSettings: view
    def whitelistAddr(i: uint256) -> address: view
    def managers(i: uint256) -> address: view
    def setDidMigrateSettings(): nonpayable
    def payees(i: uint256) -> address: view
    def numWhitelisted() -> uint256: view
    def setDidMigrateFunds(): nonpayable
    def startingAgent() -> address: view
    def numManagers() -> uint256: view
    def numPayees() -> uint256: view

interface UserWallet:
    def assets(i: uint256) -> address: view
    def walletConfig() -> address: view
    def numAssets() -> uint256: view

interface Ledger:
    def isUserWallet(_user: address) -> bool: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

event ConfigCloned:
    fromWallet: indexed(address)
    toWallet: indexed(address)
    numManagersCopied: uint256
    numPayeesCopied: uint256
    numWhitelistCopied: uint256

event FundsMigrated:
    fromWallet: indexed(address)
    toWallet: indexed(address)
    numAssetsMigrated: uint256

UNDY_HQ: public(immutable(address))
LEDGER_ID: constant(uint256) = 2


@deploy
def __init__(_undyHq: address):
    assert _undyHq != empty(address) # dev: invalid undy hq
    UNDY_HQ = _undyHq


#################
# Migrate Funds #
#################


@external
def migrateFunds(_fromWallet: address, _toWallet: address) -> uint256:
    fromConfig: address = staticcall UserWallet(_fromWallet).walletConfig()
    assert self._canMigrateFundsToNewWallet(_fromWallet, _toWallet, msg.sender, fromConfig) # dev: cannot migrate to new wallet

    # extra validation, though shouldn't be necessary
    ad: ws.ActionData = staticcall UserWalletConfig(fromConfig).getActionDataBundle(0, msg.sender)
    assert ad.signer == ad.walletOwner # dev: no perms
    assert _fromWallet == ad.wallet # dev: wallet mismatch

    # number of assets
    numAssets: uint256 = staticcall UserWallet(_fromWallet).numAssets()
    if numAssets == 0:
        extcall UserWalletConfig(fromConfig).setDidMigrateFunds()
        log FundsMigrated(fromWallet = _fromWallet, toWallet = _toWallet, numAssetsMigrated = 0)
        return 0

    # transfer tokens
    numMigrated: uint256 = 0
    for i: uint256 in range(1, numAssets, bound=max_value(uint256)):
        asset: address = staticcall UserWallet(_fromWallet).assets(i)
        if asset == empty(address):
            continue

        # check balance
        balance: uint256 = staticcall IERC20(asset).balanceOf(_fromWallet)
        if balance != 0:
            amount: uint256 = 0
            na: uint256 = 0
            amount, na = extcall UserWalletConfig(fromConfig).transferFundsDuringMigration(_toWallet, asset, max_value(uint256), ad)
            if amount != 0:
                numMigrated += 1

    # set didMigrateFunds
    extcall UserWalletConfig(fromConfig).setDidMigrateFunds()

    log FundsMigrated(fromWallet = _fromWallet, toWallet = _toWallet, numAssetsMigrated = numMigrated)
    return numMigrated


# validation


@view
@external
def canMigrateFundsToNewWallet(_fromWallet: address, _toWallet: address, _caller: address) -> bool:
    ledger: address = staticcall Registry(UNDY_HQ).getAddr(LEDGER_ID)
    
    # Check if fromWallet is a valid UserWallet before calling walletConfig
    fromConfig: address = empty(address)
    if staticcall Ledger(ledger).isUserWallet(_fromWallet):
        fromConfig = staticcall UserWallet(_fromWallet).walletConfig()
    
    return self._canMigrateFundsToNewWallet(_fromWallet, _toWallet, _caller, fromConfig)


@view
@internal
def _canMigrateFundsToNewWallet(
    _fromWallet: address,
    _toWallet: address,
    _caller: address,
    _fromConfig: address,
) -> bool:
    ledger: address = staticcall Registry(UNDY_HQ).getAddr(LEDGER_ID)

    # validate fromWallet is Underscore wallet
    if not staticcall Ledger(ledger).isUserWallet(_fromWallet):
        return False

    # validate toWallet is Underscore wallet
    if not staticcall Ledger(ledger).isUserWallet(_toWallet):
        return False

    # validate fromConfig is not empty
    if _fromConfig == empty(address):
        return False

    # get fromWallet data
    fromBundle: wcs.MigrationConfigBundle = staticcall UserWalletConfig(_fromConfig).getMigrationConfigBundle()

    # validate caller is owner of fromWallet
    if _caller != fromBundle.owner:
        return False

    # cannot migrate if fromWallet has already migrated funds
    if fromBundle.didMigrateFunds:
        return False

    # cannot migrate if fromWallet has trial funds
    if fromBundle.trialFundsAmount != 0:
        return False

    # cannot migrate if fromWallet is frozen
    if fromBundle.isFrozen:
        return False

    # cannot migrate if fromWallet has pending owner change
    if fromBundle.hasPendingOwnerChange:
        return False

    # toWallet bundle
    toWalletConfig: address = staticcall UserWallet(_toWallet).walletConfig()
    toWalletBundle: wcs.MigrationConfigBundle = staticcall UserWalletConfig(toWalletConfig).getMigrationConfigBundle()

    # owners must be the same
    if fromBundle.owner != toWalletBundle.owner:
        return False

    # cannot migrate if toWallet has pending owner change
    if toWalletBundle.hasPendingOwnerChange:
        return False

    # group id must be the same
    if fromBundle.groupId != toWalletBundle.groupId:
        return False

    # cannot migrate if toWallet is frozen
    if toWalletBundle.isFrozen:
        return False

    # toWallet cannot have any payees
    if toWalletBundle.numPayees != 0:
        return False

    # toWallet cannot have any whitelisted addresses
    if toWalletBundle.numWhitelisted != 0:
        return False

    # cannot have managers (if starting agent is not set)
    if toWalletBundle.startingAgent == empty(address) and toWalletBundle.numManagers != 0:
        return False
    
    # cannot have managers other than starting agent
    if toWalletBundle.startingAgent != empty(address):
        if toWalletBundle.startingAgentIndex != 1:
            return False
        if toWalletBundle.numManagers != 2:
            return False

    return True


################
# Clone Config #
################


@external
def cloneConfig(_fromWallet: address, _toWallet: address):
    fromConfig: address = staticcall UserWallet(_fromWallet).walletConfig()
    toConfig: address = staticcall UserWallet(_toWallet).walletConfig()
    assert self._canCopyWalletConfig(_fromWallet, _toWallet, msg.sender, fromConfig, toConfig) # dev: cannot copy config

    managersCopied: uint256 = 0
    payeesCopied: uint256 = 0
    whitelistCopied: uint256 = 0

    # 1. copy global manager settings
    globalManagerSettings: wcs.GlobalManagerSettings = staticcall UserWalletConfig(fromConfig).globalManagerSettings()
    extcall UserWalletConfig(toConfig).setGlobalManagerSettings(globalManagerSettings)

    # get starting agent from source wallet to skip it during copy
    fromStartingAgent: address = staticcall UserWalletConfig(fromConfig).startingAgent()
    
    # 2. copy all managers (except starting agent)
    numManagers: uint256 = staticcall UserWalletConfig(fromConfig).numManagers()
    if numManagers != 0:
        for i: uint256 in range(1, numManagers, bound=max_value(uint256)):
            manager: address = staticcall UserWalletConfig(fromConfig).managers(i)
            if manager == empty(address):
                continue

            # skip the starting agent from source wallet
            if manager == fromStartingAgent:
                continue

            settings: wcs.ManagerSettings = staticcall UserWalletConfig(fromConfig).managerSettings(manager)
            if settings.startBlock != 0:
                extcall UserWalletConfig(toConfig).addManager(manager, settings)
                managersCopied += 1

    # 3. copy global payee settings
    globalPayeeSettings: wcs.GlobalPayeeSettings = staticcall UserWalletConfig(fromConfig).globalPayeeSettings()
    extcall UserWalletConfig(toConfig).setGlobalPayeeSettings(globalPayeeSettings)
    
    # 4. copy all payees
    numPayees: uint256 = staticcall UserWalletConfig(fromConfig).numPayees()
    if numPayees != 0:
        for i: uint256 in range(1, numPayees, bound=max_value(uint256)):
            payee: address = staticcall UserWalletConfig(fromConfig).payees(i)
            if payee == empty(address):
                continue

            settings: wcs.PayeeSettings = staticcall UserWalletConfig(fromConfig).payeeSettings(payee)
            if settings.startBlock != 0:
                extcall UserWalletConfig(toConfig).addPayee(payee, settings)
                payeesCopied += 1

    # 5. copy all whitelisted addresses
    numWhitelisted: uint256 = staticcall UserWalletConfig(fromConfig).numWhitelisted()
    if numWhitelisted != 0:
        for i: uint256 in range(1, numWhitelisted, bound=max_value(uint256)):
            addr: address = staticcall UserWalletConfig(fromConfig).whitelistAddr(i)
            if addr != empty(address):
                extcall UserWalletConfig(toConfig).addWhitelistAddrViaMigrator(addr)
                whitelistCopied += 1

    # set didMigrateSettings
    extcall UserWalletConfig(fromConfig).setDidMigrateSettings()

    log ConfigCloned(
        fromWallet = _fromWallet,
        toWallet = _toWallet,
        numManagersCopied = managersCopied,
        numPayeesCopied = payeesCopied,
        numWhitelistCopied = whitelistCopied
    )


# validation


@view
@external
def canCopyWalletConfig(_fromWallet: address, _toWallet: address, _caller: address) -> bool:
    ledger: address = staticcall Registry(UNDY_HQ).getAddr(LEDGER_ID)
    
    # Check if wallets are valid UserWallets before calling walletConfig
    fromConfig: address = empty(address)
    toConfig: address = empty(address)
    
    if staticcall Ledger(ledger).isUserWallet(_fromWallet):
        fromConfig = staticcall UserWallet(_fromWallet).walletConfig()
    
    if staticcall Ledger(ledger).isUserWallet(_toWallet):
        toConfig = staticcall UserWallet(_toWallet).walletConfig()
    
    return self._canCopyWalletConfig(_fromWallet, _toWallet, _caller, fromConfig, toConfig)


@view
@internal
def _canCopyWalletConfig(
    _fromWallet: address,
    _toWallet: address,
    _caller: address,
    _fromConfig: address,
    _toConfig: address,
) -> bool:
    ledger: address = staticcall Registry(UNDY_HQ).getAddr(LEDGER_ID)

    # validate fromWallet is Underscore wallet
    if not staticcall Ledger(ledger).isUserWallet(_fromWallet):
        return False

    # validate toWallet is Underscore wallet
    if not staticcall Ledger(ledger).isUserWallet(_toWallet):
        return False

    # validate configs are not empty
    if _fromConfig == empty(address) or _toConfig == empty(address):
        return False

    # get toWallet data
    toBundle: wcs.MigrationConfigBundle = staticcall UserWalletConfig(_toConfig).getMigrationConfigBundle()

    # validate caller is owner of toWallet
    if _caller != toBundle.owner:
        return False

    # cannot copy if toWallet has pending owner change
    if toBundle.hasPendingOwnerChange:
        return False

    # cannot copy if toWallet is frozen
    if toBundle.isFrozen:
        return False

    # toWallet cannot have any payees
    if toBundle.numPayees != 0:
        return False

    # toWallet cannot have any whitelisted addresses
    if toBundle.numWhitelisted != 0:
        return False

    # cannot have managers (if starting agent is not set)
    if toBundle.startingAgent == empty(address) and toBundle.numManagers != 0:
        return False
    
    # cannot have managers other than starting agent
    if toBundle.startingAgent != empty(address):
        if toBundle.startingAgentIndex != 1:
            return False
        if toBundle.numManagers != 2:
            return False

    # fromWallet bundle
    fromBundle: wcs.MigrationConfigBundle = staticcall UserWalletConfig(_fromConfig).getMigrationConfigBundle()

    # cannot copy if fromWallet has already migrated settings
    if fromBundle.didMigrateSettings:
        return False

    # cannot copy if fromWallet is frozen
    if fromBundle.isFrozen:
        return False

    # owners must be the same
    if fromBundle.owner != toBundle.owner:
        return False

    # group id must be the same
    if fromBundle.groupId != toBundle.groupId:
        return False

    # cannot copy if fromWallet has pending owner change
    if fromBundle.hasPendingOwnerChange:
        return False

    return True

