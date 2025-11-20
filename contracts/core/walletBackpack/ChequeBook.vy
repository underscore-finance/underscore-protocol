#    ┓ ┏  ┓┓   
#    ┃┃┃┏┓┃┃┏┓╋
#    ┗┻┛┗┻┗┗┗ ┗
#     ______   __  __   ______   ______   __  __   ______       ______   ______   ______   __  __    
#    /\  ___\ /\ \_\ \ /\  ___\ /\  __ \ /\ \/\ \ /\  ___\     /\  == \ /\  __ \ /\  __ \ /\ \/ /    
#    \ \ \____\ \  __ \\ \  __\ \ \ \/\_\\ \ \_\ \\ \  __\     \ \  __< \ \ \/\ \\ \ \/\ \\ \  _"-.  
#     \ \_____\\ \_\ \_\\ \_____\\ \___\_\\ \_____\\ \_____\    \ \_____\\ \_____\\ \_____\\ \_\ \_\ 
#      \/_____/ \/_/\/_/ \/_____/ \/___/_/ \/_____/ \/_____/     \/_____/ \/_____/ \/_____/ \/_/\/_/ 
#                                                                                                
#     ╔══════════════════════════════════════════════╗
#     ║  ** Cheque Book **                           ║
#     ║  Cheque book functionality for user wallets  ║
#     ╚══════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

from interfaces import WalletConfigStructs as wcs

interface UserWalletConfig:
    def createCheque(_recipient: address, _cheque: wcs.Cheque, _chequeData: wcs.ChequeData, _isExistingCheque: bool): nonpayable
    def managerSettings(_addr: address) -> wcs.ManagerSettings: view
    def setChequeSettings(_config: wcs.ChequeSettings): nonpayable
    def indexOfWhitelist(_addr: address) -> uint256: view
    def cheques(_recipient: address) -> wcs.Cheque: view
    def cancelCheque(_recipient: address): nonpayable
    def indexOfManager(_addr: address) -> uint256: view
    def indexOfPayee(_addr: address) -> uint256: view
    def chequeSettings() -> wcs.ChequeSettings: view
    def chequePeriodData() -> wcs.ChequeData: view
    def numActiveCheques() -> uint256: view
    def timeLock() -> uint256: view
    def owner() -> address: view

interface Appraiser:
    def updatePriceAndGetUsdValue(_asset: address, _amount: uint256, _missionControl: address = empty(address), _legoBook: address = empty(address)) -> uint256: nonpayable

interface MissionControl:
    def canPerformSecurityAction(_addr: address) -> bool: view

interface Ledger:
    def isUserWallet(_user: address) -> bool: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

interface UserWallet:
    def walletConfig() -> address: view

event ChequeCreated:
    user: indexed(address)
    recipient: indexed(address)
    asset: address
    amount: uint256
    usdValue: uint256
    unlockBlock: uint256
    expiryBlock: uint256
    canManagerPay: bool
    canBePulled: bool
    creator: indexed(address)

event ChequeCancelled:
    user: indexed(address)
    recipient: indexed(address)
    asset: address
    amount: uint256
    usdValue: uint256
    unlockBlock: uint256
    expiryBlock: uint256
    canManagerPay: bool
    canBePulled: bool
    cancelledBy: indexed(address)

event ChequeSettingsModified:
    user: indexed(address)
    maxNumActiveCheques: uint256
    maxChequeUsdValue: uint256
    instantUsdThreshold: uint256
    perPeriodPaidUsdCap: uint256
    maxNumChequesPaidPerPeriod: uint256
    payCooldownBlocks: uint256
    perPeriodCreatedUsdCap: uint256
    maxNumChequesCreatedPerPeriod: uint256
    createCooldownBlocks: uint256
    periodLength: uint256
    expensiveDelayBlocks: uint256
    defaultExpiryBlocks: uint256
    canManagersCreateCheques: bool
    canManagerPay: bool
    canBePulled: bool

UNDY_HQ: public(immutable(address))
LEDGER_ID: constant(uint256) = 1
MISSION_CONTROL_ID: constant(uint256) = 2
APPRAISER_ID: constant(uint256) = 7
MAX_CONFIG_ASSETS: constant(uint256) = 40

MIN_CHEQUE_PERIOD: public(immutable(uint256))
MAX_CHEQUE_PERIOD: public(immutable(uint256))
MIN_EXPENSIVE_CHEQUE_DELAY: public(immutable(uint256))
MAX_UNLOCK_BLOCKS: public(immutable(uint256))
MAX_EXPIRY_BLOCKS: public(immutable(uint256))


@deploy
def __init__(
    _undyHq: address,
    _minChequePeriod: uint256,
    _maxChequePeriod: uint256,
    _minExpensiveChequeDelay: uint256,
    _maxUnlockBlocks: uint256,
    _maxExpiryBlocks: uint256,
):
    assert _undyHq != empty(address) # dev: invalid undy hq
    UNDY_HQ = _undyHq

    assert _minChequePeriod != 0 and _minChequePeriod < _maxChequePeriod # dev: invalid cheque period
    MIN_CHEQUE_PERIOD = _minChequePeriod
    MAX_CHEQUE_PERIOD = _maxChequePeriod

    assert _minExpensiveChequeDelay != 0 # dev: invalid expensive cheque delay
    MIN_EXPENSIVE_CHEQUE_DELAY = _minExpensiveChequeDelay

    assert _maxUnlockBlocks != 0 # dev: invalid unlock blocks
    MAX_UNLOCK_BLOCKS = _maxUnlockBlocks

    assert _maxExpiryBlocks != 0 # dev: invalid expiry blocks
    MAX_EXPIRY_BLOCKS = _maxExpiryBlocks


#####################
# Cheque Management #
#####################


@external
def createCheque(
    _userWallet: address,
    _recipient: address,
    _asset: address,
    _amount: uint256,
    _unlockNumBlocks: uint256,
    _expiryNumBlocks: uint256,
    _canManagerPay: bool,
    _canBePulled: bool,
) -> bool:
    assert self._isValidUserWallet(_userWallet) # dev: invalid user wallet

    # get cheque config / data
    config: wcs.ChequeManagementBundle = self._getChequeConfig(_userWallet, msg.sender, _recipient)
    
    # check if caller can create cheques
    assert self._canCreateCheque(
        config.owner == msg.sender,
        config.isCreatorManager,
        config.chequeSettings.canManagersCreateCheques,
        config.managerSettings,
    ) # dev: not authorized to create cheques
    
    # get USD value
    appraiser: address = staticcall Registry(UNDY_HQ).getAddr(APPRAISER_ID)
    usdValue: uint256 = extcall Appraiser(appraiser).updatePriceAndGetUsdValue(_asset, _amount)

    # validate and create cheque
    isValid: bool = False
    cheque: wcs.Cheque = empty(wcs.Cheque)
    updatedChequeData: wcs.ChequeData = empty(wcs.ChequeData)
    isValid, cheque, updatedChequeData = self._isValidNewCheque(
        config.wallet,
        config.walletConfig,
        config.owner,
        config.isRecipientOnWhitelist,
        config.chequeSettings,
        config.chequeData,
        config.isExistingCheque,
        config.numActiveCheques,
        config.isExistingPayee,
        config.timeLock,
        _recipient,
        _asset,
        _amount,
        _unlockNumBlocks,
        _expiryNumBlocks,
        _canManagerPay,
        _canBePulled,
        msg.sender,
        usdValue,
    )
    assert isValid # dev: invalid cheque
    
    # save cheque
    extcall UserWalletConfig(config.walletConfig).createCheque(_recipient, cheque, updatedChequeData, config.isExistingCheque)
    log ChequeCreated(
        user = _userWallet,
        recipient = _recipient,
        asset = _asset,
        amount = _amount,
        usdValue = usdValue,
        unlockBlock = cheque.unlockBlock,
        expiryBlock = cheque.expiryBlock,
        canManagerPay = _canManagerPay,
        canBePulled = _canBePulled,
        creator = msg.sender,
    )
    return True


# can create cheque


@view
@external
def canCreateCheque(
    _isCreatorOwner: bool,
    _isCreatorManager: bool,
    _canManagersCreateCheques: bool,
    _managerSettings: wcs.ManagerSettings,
) -> bool:
    return self._canCreateCheque(
        _isCreatorOwner,
        _isCreatorManager,
        _canManagersCreateCheques,
        _managerSettings,
    )


@view
@internal
def _canCreateCheque(
    _isCreatorOwner: bool,
    _isCreatorManager: bool,
    _canManagersCreateCheques: bool,
    _managerSettings: wcs.ManagerSettings,
) -> bool:

    # owner can always create cheques
    if _isCreatorOwner:
        return True
    
    # if not owner, must be a manager
    if not _isCreatorManager:
        return False
    
    # check global setting - can managers create cheques
    if not _canManagersCreateCheques:
        return False
    
    # check manager's specific transfer permissions
    if not _managerSettings.transferPerms.canCreateCheque:
        return False
    
    # check if manager is active (within start/expiry blocks)
    if _managerSettings.startBlock > block.number:
        return False
    if _managerSettings.expiryBlock != 0 and _managerSettings.expiryBlock <= block.number:
        return False
    
    return True


# is valid new cheque


@view
@external
def isValidNewCheque(
    _wallet: address,
    _walletConfig: address,
    _owner: address,
    _isRecipientOnWhitelist: bool,
    _chequeSettings: wcs.ChequeSettings,
    _chequeData: wcs.ChequeData,
    _isExistingCheque: bool,
    _numActiveCheques: uint256,
    _isExistingPayee: bool,
    _timeLock: uint256,
    _recipient: address,
    _asset: address,
    _amount: uint256,
    _unlockNumBlocks: uint256,
    _expiryNumBlocks: uint256,
    _canManagerPay: bool,
    _canBePulled: bool,
    _creator: address,
    _usdValue: uint256,
) -> bool:
    isValid: bool = False
    cheque: wcs.Cheque = empty(wcs.Cheque)
    chequeData: wcs.ChequeData = empty(wcs.ChequeData)    
    isValid, cheque, chequeData = self._isValidNewCheque(
        _wallet,
        _walletConfig,
        _owner,
        _isRecipientOnWhitelist,
        _chequeSettings,
        _chequeData,
        _isExistingCheque,
        _numActiveCheques,
        _isExistingPayee,
        _timeLock,
        _recipient,
        _asset,
        _amount,
        _unlockNumBlocks,
        _expiryNumBlocks,
        _canManagerPay,
        _canBePulled,
        _creator,
        _usdValue,
    )
    return isValid


@view
@internal
def _isValidNewCheque(
    _wallet: address,
    _walletConfig: address,
    _owner: address,
    _isRecipientOnWhitelist: bool,
    _chequeSettings: wcs.ChequeSettings,
    _chequeData: wcs.ChequeData,
    _isExistingCheque: bool,
    _numActiveCheques: uint256,
    _isExistingPayee: bool,
    _timeLock: uint256,
    _recipient: address,
    _asset: address,
    _amount: uint256,
    _unlockNumBlocks: uint256,
    _expiryNumBlocks: uint256,
    _canManagerPay: bool,
    _canBePulled: bool,
    _creator: address,
    _usdValue: uint256,
) -> (bool, wcs.Cheque, wcs.ChequeData):

    # validate recipient
    if _recipient == empty(address):
        return False, empty(wcs.Cheque), empty(wcs.ChequeData)
    if _recipient in [_wallet, _walletConfig, _owner]:
        return False, empty(wcs.Cheque), empty(wcs.ChequeData)

    # cheque recipients can't be whitelisted
    if _isRecipientOnWhitelist:
        return False, empty(wcs.Cheque), empty(wcs.ChequeData)

    # cheque recipients can't be existing payees
    if _isExistingPayee:
        return False, empty(wcs.Cheque), empty(wcs.ChequeData)

    # validate asset and amount
    if _asset == empty(address):
        return False, empty(wcs.Cheque), empty(wcs.ChequeData)
    if _amount == 0:
        return False, empty(wcs.Cheque), empty(wcs.ChequeData)
    
    # check if asset is allowed
    if len(_chequeSettings.allowedAssets) != 0:
        if _asset not in _chequeSettings.allowedAssets:
            return False, empty(wcs.Cheque), empty(wcs.ChequeData)

    # validate canBePulled and canManagerPay against global settings
    if _canBePulled and not _chequeSettings.canBePulled:
        return False, empty(wcs.Cheque), empty(wcs.ChequeData)
    if _canManagerPay and not _chequeSettings.canManagerPay:
        return False, empty(wcs.Cheque), empty(wcs.ChequeData)

    # check max number of active cheques (only if creating new cheque, not replacing)
    if not _isExistingCheque and _chequeSettings.maxNumActiveCheques != 0:
        if _numActiveCheques >= _chequeSettings.maxNumActiveCheques:
            return False, empty(wcs.Cheque), empty(wcs.ChequeData)

    # get latest cheque data (with period reset if needed)
    chequeData: wcs.ChequeData = self._getLatestChequeData(_chequeData, _chequeSettings.periodLength)

    # check creation cooldown
    if _chequeSettings.createCooldownBlocks != 0 and chequeData.lastChequeCreatedBlock != 0:
        if block.number < chequeData.lastChequeCreatedBlock + _chequeSettings.createCooldownBlocks:
            return False, empty(wcs.Cheque), empty(wcs.ChequeData)

    # check max num cheques created per period
    if _chequeSettings.maxNumChequesCreatedPerPeriod != 0:
        if chequeData.numChequesCreatedInPeriod >= _chequeSettings.maxNumChequesCreatedPerPeriod:
            return False, empty(wcs.Cheque), empty(wcs.ChequeData)

    # if no usd value, return False
    if _usdValue == 0:
        return False, empty(wcs.Cheque), empty(wcs.ChequeData)

    # check max cheque USD value
    if _chequeSettings.maxChequeUsdValue != 0:
        if _usdValue > _chequeSettings.maxChequeUsdValue:
            return False, empty(wcs.Cheque), empty(wcs.ChequeData)

    # check per period created USD cap
    if _chequeSettings.perPeriodCreatedUsdCap != 0:
        if chequeData.totalUsdValueCreatedInPeriod + _usdValue > _chequeSettings.perPeriodCreatedUsdCap:
            return False, empty(wcs.Cheque), empty(wcs.ChequeData)

    # cannot be too long
    if _unlockNumBlocks > MAX_UNLOCK_BLOCKS:
        return False, empty(wcs.Cheque), empty(wcs.ChequeData)

    # calculate unlock block
    unlockBlock: uint256 = block.number + _unlockNumBlocks

    # apply time lock if USD value exceeds instant threshold
    if _chequeSettings.instantUsdThreshold != 0 and _usdValue > _chequeSettings.instantUsdThreshold:
        if _chequeSettings.expensiveDelayBlocks != 0:
            unlockBlock = max(unlockBlock, block.number + _chequeSettings.expensiveDelayBlocks)
        else:
            unlockBlock = max(unlockBlock, block.number + _timeLock)

    # calculate expiry block
    expiryBlock: uint256 = 0
    if _expiryNumBlocks != 0:
        expiryBlock = unlockBlock + _expiryNumBlocks
    elif _chequeSettings.defaultExpiryBlocks != 0:
        expiryBlock = unlockBlock + _chequeSettings.defaultExpiryBlocks
    else:
        expiryBlock = unlockBlock + _timeLock

    # cannot be too long (active duration)
    activeDuration: uint256 = expiryBlock - unlockBlock
    if activeDuration > MAX_EXPIRY_BLOCKS:
        return False, empty(wcs.Cheque), empty(wcs.ChequeData)

    # create cheque
    cheque: wcs.Cheque = wcs.Cheque(
        recipient = _recipient,
        asset = _asset,
        amount = _amount,
        creationBlock = block.number,
        unlockBlock = unlockBlock,
        expiryBlock = expiryBlock,
        usdValueOnCreation = _usdValue,
        canManagerPay = _canManagerPay,
        canBePulled = _canBePulled,
        creator = _creator,
        active = True,
    )

    # update cheque data
    chequeData.numChequesCreatedInPeriod += 1
    chequeData.totalUsdValueCreatedInPeriod += _usdValue
    chequeData.totalNumChequesCreated += 1
    chequeData.totalUsdValueCreated += _usdValue
    chequeData.lastChequeCreatedBlock = block.number

    return True, cheque, chequeData


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


# cancel cheque


@external
def cancelCheque(_userWallet: address, _recipient: address) -> bool:
    assert self._isValidUserWallet(_userWallet) # dev: invalid user wallet

    # get wallet config
    walletConfig: address = staticcall UserWallet(_userWallet).walletConfig()
    owner: address = staticcall UserWalletConfig(walletConfig).owner()

    # check permissions - only owner or security action can cancel
    if msg.sender != owner:
        assert self._canPerformSecurityAction(msg.sender) # dev: no perms

    # check if cheque exists
    cheque: wcs.Cheque = staticcall UserWalletConfig(walletConfig).cheques(_recipient)
    assert cheque.active # dev: no active cheque

    # cancel the cheque
    extcall UserWalletConfig(walletConfig).cancelCheque(_recipient)
    log ChequeCancelled(
        user = _userWallet,
        recipient = _recipient,
        asset = cheque.asset,
        amount = cheque.amount,
        usdValue = cheque.usdValueOnCreation,
        unlockBlock = cheque.unlockBlock,
        expiryBlock = cheque.expiryBlock,
        canManagerPay = cheque.canManagerPay,
        canBePulled = cheque.canBePulled,
        cancelledBy = msg.sender,
    )
    return True


###################
# Cheque Settings #
###################


# set cheque settings


@external
def setChequeSettings(
    _userWallet: address,
    _maxNumActiveCheques: uint256,
    _maxChequeUsdValue: uint256,
    _instantUsdThreshold: uint256,
    _perPeriodPaidUsdCap: uint256,
    _maxNumChequesPaidPerPeriod: uint256,
    _payCooldownBlocks: uint256,
    _perPeriodCreatedUsdCap: uint256,
    _maxNumChequesCreatedPerPeriod: uint256,
    _createCooldownBlocks: uint256,
    _periodLength: uint256,
    _expensiveDelayBlocks: uint256,
    _defaultExpiryBlocks: uint256,
    _allowedAssets: DynArray[address, MAX_CONFIG_ASSETS],
    _canManagersCreateCheques: bool,
    _canManagerPay: bool,
    _canBePulled: bool,
) -> bool:
    assert self._isValidUserWallet(_userWallet) # dev: invalid user wallet
    
    # only owner can set cheque settings
    walletConfig: address = staticcall UserWallet(_userWallet).walletConfig()
    assert msg.sender == staticcall UserWalletConfig(walletConfig).owner() # dev: no perms

    # validate cheque settings with timelock
    assert self._isValidChequeSettings(
        _maxNumActiveCheques,
        _maxChequeUsdValue,
        _instantUsdThreshold,
        _perPeriodPaidUsdCap,
        _maxNumChequesPaidPerPeriod,
        _payCooldownBlocks,
        _perPeriodCreatedUsdCap,
        _maxNumChequesCreatedPerPeriod,
        _createCooldownBlocks,
        _periodLength,
        _expensiveDelayBlocks,
        _defaultExpiryBlocks,
        staticcall UserWalletConfig(walletConfig).timeLock(),
    ) # dev: invalid cheque settings

    # create settings
    settings: wcs.ChequeSettings = wcs.ChequeSettings(
        maxNumActiveCheques = _maxNumActiveCheques,
        maxChequeUsdValue = _maxChequeUsdValue,
        instantUsdThreshold = _instantUsdThreshold,
        perPeriodPaidUsdCap = _perPeriodPaidUsdCap,
        maxNumChequesPaidPerPeriod = _maxNumChequesPaidPerPeriod,
        payCooldownBlocks = _payCooldownBlocks,
        perPeriodCreatedUsdCap = _perPeriodCreatedUsdCap,
        maxNumChequesCreatedPerPeriod = _maxNumChequesCreatedPerPeriod,
        createCooldownBlocks = _createCooldownBlocks,
        periodLength = _periodLength,
        expensiveDelayBlocks = _expensiveDelayBlocks,
        defaultExpiryBlocks = _defaultExpiryBlocks,
        allowedAssets = _allowedAssets,
        canManagersCreateCheques = _canManagersCreateCheques,
        canManagerPay = _canManagerPay,
        canBePulled = _canBePulled,
    )

    # update settings
    extcall UserWalletConfig(walletConfig).setChequeSettings(settings)
    log ChequeSettingsModified(
        user = _userWallet,
        maxNumActiveCheques = _maxNumActiveCheques,
        maxChequeUsdValue = _maxChequeUsdValue,
        instantUsdThreshold = _instantUsdThreshold,
        perPeriodPaidUsdCap = _perPeriodPaidUsdCap,
        maxNumChequesPaidPerPeriod = _maxNumChequesPaidPerPeriod,
        payCooldownBlocks = _payCooldownBlocks,
        perPeriodCreatedUsdCap = _perPeriodCreatedUsdCap,
        maxNumChequesCreatedPerPeriod = _maxNumChequesCreatedPerPeriod,
        createCooldownBlocks = _createCooldownBlocks,
        periodLength = _periodLength,
        expensiveDelayBlocks = _expensiveDelayBlocks,
        defaultExpiryBlocks = _defaultExpiryBlocks,
        canManagersCreateCheques = _canManagersCreateCheques,
        canManagerPay = _canManagerPay,
        canBePulled = _canBePulled,
    )
    return True


# cheque settings validation


@view
@external
def isValidChequeSettings(
    _maxNumActiveCheques: uint256,
    _maxChequeUsdValue: uint256,
    _instantUsdThreshold: uint256,
    _perPeriodPaidUsdCap: uint256,
    _maxNumChequesPaidPerPeriod: uint256,
    _payCooldownBlocks: uint256,
    _perPeriodCreatedUsdCap: uint256,
    _maxNumChequesCreatedPerPeriod: uint256,
    _createCooldownBlocks: uint256,
    _periodLength: uint256,
    _expensiveDelayBlocks: uint256,
    _defaultExpiryBlocks: uint256,
    _timeLock: uint256,
) -> bool:
    return self._isValidChequeSettings(
        _maxNumActiveCheques,
        _maxChequeUsdValue,
        _instantUsdThreshold,
        _perPeriodPaidUsdCap,
        _maxNumChequesPaidPerPeriod,
        _payCooldownBlocks,
        _perPeriodCreatedUsdCap,
        _maxNumChequesCreatedPerPeriod,
        _createCooldownBlocks,
        _periodLength,
        _expensiveDelayBlocks,
        _defaultExpiryBlocks,
        _timeLock,
    )


@view
@internal
def _isValidChequeSettings(
    _maxNumActiveCheques: uint256,
    _maxChequeUsdValue: uint256,
    _instantUsdThreshold: uint256,
    _perPeriodPaidUsdCap: uint256,
    _maxNumChequesPaidPerPeriod: uint256,
    _payCooldownBlocks: uint256,
    _perPeriodCreatedUsdCap: uint256,
    _maxNumChequesCreatedPerPeriod: uint256,
    _createCooldownBlocks: uint256,
    _periodLength: uint256,
    _expensiveDelayBlocks: uint256,
    _defaultExpiryBlocks: uint256,
    _timeLock: uint256,
) -> bool:

    # validate period length
    if not self._isValidChequePeriod(_periodLength):
        return False
    
    # validate cooldowns
    if not self._isValidChequeCooldowns(_payCooldownBlocks, _createCooldownBlocks, _periodLength):
        return False
    
    # validate expensive delay
    if not self._isValidExpensiveDelay(_expensiveDelayBlocks, _timeLock):
        return False
    
    # validate USD caps consistency
    if not self._isValidChequeUsdCaps(_maxChequeUsdValue, _perPeriodPaidUsdCap, _perPeriodCreatedUsdCap):
        return False
    
    # validate instant threshold configuration
    if not self._isValidInstantThreshold(_instantUsdThreshold, _expensiveDelayBlocks):
        return False
    
    # validate expiry blocks
    if not self._isValidExpiryBlocks(_defaultExpiryBlocks, _timeLock):
        return False
    
    return True


# validate cheque period


@view
@internal
def _isValidChequePeriod(_periodLength: uint256) -> bool:
    # period length cannot be zero
    if _periodLength == 0:
        return False
    return _periodLength >= MIN_CHEQUE_PERIOD and _periodLength <= MAX_CHEQUE_PERIOD


# validate cheque cooldowns


@view
@internal
def _isValidChequeCooldowns(_payCooldownBlocks: uint256, _createCooldownBlocks: uint256, _periodLength: uint256) -> bool:
    # cooldowns cannot exceed period length
    if _payCooldownBlocks > _periodLength:
        return False
    if _createCooldownBlocks > _periodLength:
        return False
    
    return True


# validate expensive delay


@view
@internal
def _isValidExpensiveDelay(_expensiveDelayBlocks: uint256, _timeLock: uint256) -> bool:
    # NOTE: When set to zero, expensive cheque delay will use UserWalletConfig.timeLock()
    if _expensiveDelayBlocks == 0:
        return True

    # must meet minimum and cannot be less than current timelock
    if _expensiveDelayBlocks < MIN_EXPENSIVE_CHEQUE_DELAY:
        return False
    if _expensiveDelayBlocks < _timeLock:
        return False

    # cannot exceed maximum unlock blocks
    if _expensiveDelayBlocks > MAX_UNLOCK_BLOCKS:
        return False
    return True


# validate cheque USD caps consistency


@view
@internal
def _isValidChequeUsdCaps(_maxChequeUsdValue: uint256, _perPeriodPaidUsdCap: uint256, _perPeriodCreatedUsdCap: uint256) -> bool:
    if _maxChequeUsdValue == 0:
        return True
    
    # per-cheque cap should not exceed period caps
    if _perPeriodPaidUsdCap != 0 and _maxChequeUsdValue > _perPeriodPaidUsdCap:
        return False
    if _perPeriodCreatedUsdCap != 0 and _maxChequeUsdValue > _perPeriodCreatedUsdCap:
        return False
    
    return True


# validate instant threshold configuration


@view
@internal
def _isValidInstantThreshold(_instantUsdThreshold: uint256, _expensiveDelayBlocks: uint256) -> bool:
    # instant threshold cannot be zero
    if _instantUsdThreshold == 0:
        return False
    # if instant threshold is set, expensive delay must be set
    if _expensiveDelayBlocks == 0:
        return False
    return True


# validate expiry blocks


@view
@internal
def _isValidExpiryBlocks(_defaultExpiryBlocks: uint256, _timeLock: uint256) -> bool:
    # NOTE: When set to zero, expiry blocks will use UserWalletConfig.timeLock()
    if _defaultExpiryBlocks == 0:
        return True
    if _defaultExpiryBlocks > MAX_EXPIRY_BLOCKS:
        return False
    if _defaultExpiryBlocks < _timeLock:
        return False
    return True


#############
# Utilities #
#############

# get cheque management bundle


@view
@external
def getChequeConfig(_userWallet: address, _creator: address, _recipient: address) -> wcs.ChequeManagementBundle:
    return self._getChequeConfig(_userWallet, _creator, _recipient)


@view
@internal
def _getChequeConfig(_userWallet: address, _creator: address, _recipient: address) -> wcs.ChequeManagementBundle:
    walletConfig: address = staticcall UserWallet(_userWallet).walletConfig()
    cheque: wcs.Cheque = staticcall UserWalletConfig(walletConfig).cheques(_recipient)
    return wcs.ChequeManagementBundle(
        wallet = _userWallet,
        walletConfig = walletConfig,
        owner = staticcall UserWalletConfig(walletConfig).owner(),
        isRecipientOnWhitelist = staticcall UserWalletConfig(walletConfig).indexOfWhitelist(_recipient) != 0,
        isCreatorManager = staticcall UserWalletConfig(walletConfig).indexOfManager(_creator) != 0,
        managerSettings = staticcall UserWalletConfig(walletConfig).managerSettings(_creator),
        chequeSettings = staticcall UserWalletConfig(walletConfig).chequeSettings(),
        chequeData = staticcall UserWalletConfig(walletConfig).chequePeriodData(),
        isExistingCheque = cheque.active,
        numActiveCheques = staticcall UserWalletConfig(walletConfig).numActiveCheques(),
        isExistingPayee = staticcall UserWalletConfig(walletConfig).indexOfPayee(_recipient) != 0,
        timeLock = staticcall UserWalletConfig(walletConfig).timeLock(),
    )


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


# default cheque settings


@view
@external
def createDefaultChequeSettings(
    _maxNumActiveCheques: uint256,
    _instantUsdThreshold: uint256,
    _periodLength: uint256,
    _expensiveDelayBlocks: uint256,
    _defaultExpiryBlocks: uint256,
) -> wcs.ChequeSettings:
    return wcs.ChequeSettings(
        maxNumActiveCheques = _maxNumActiveCheques,
        maxChequeUsdValue = 0,
        instantUsdThreshold = _instantUsdThreshold,
        perPeriodPaidUsdCap = 0,
        maxNumChequesPaidPerPeriod = 0,
        payCooldownBlocks = 0,
        perPeriodCreatedUsdCap = 0,
        maxNumChequesCreatedPerPeriod = 0,
        createCooldownBlocks = 0,
        periodLength = _periodLength,
        expensiveDelayBlocks = _expensiveDelayBlocks,
        defaultExpiryBlocks = _defaultExpiryBlocks,
        allowedAssets = [],
        canManagersCreateCheques = False,
        canManagerPay = True,
        canBePulled = False,
    )