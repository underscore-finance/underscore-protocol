#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

interface UndyHq:
    def isValidAddr(_addr: address) -> bool: view
    def getAddr(_regId: uint256) -> address: view
    def undyToken() -> address: view

interface Switchboard:
    def isSwitchboardAddr(_addr: address) -> bool: view

interface LegoBook:
    def isLegoAddr(_addr: address) -> bool: view

struct Addys:
    hq: address
    undyToken: address
    ledger: address
    missionControl: address
    legoBook: address
    switchboard: address
    hatchery: address
    lootDistributor: address
    appraiser: address
    walletBackpack: address
    billing: address
    vaultRegistry: address

# hq
UNDY_HQ_FOR_ADDYS: immutable(address)

# core addys
LEDGER_ID: constant(uint256) = 1
MISSION_CONTROL_ID: constant(uint256) = 2
LEGO_BOOK_ID: constant(uint256) = 3
SWITCHBOARD_ID: constant(uint256) = 4
HATCHERY_ID: constant(uint256) = 5
LOOT_DISTRIBUTOR_ID: constant(uint256) = 6
APPRAISER_ID: constant(uint256) = 7
WALLET_BACKPACK_ID: constant(uint256) = 8
BILLING_ID: constant(uint256) = 9
VAULT_REGISTRY_ID: constant(uint256) = 10
HELPERS_ID: constant(uint256) = 11


@deploy
def __init__(_undyHq: address):
    assert _undyHq != empty(address) # dev: invalid undy hq
    UNDY_HQ_FOR_ADDYS = _undyHq


########
# Core #
########


@view
@external
def getAddys() -> Addys:
    return self._generateAddys()


@view
@internal
def _getAddys(_addys: Addys = empty(Addys)) -> Addys:
    if _addys.hq != empty(address):
        return _addys
    return self._generateAddys()


@view
@internal
def _generateAddys() -> Addys:
    hq: address = UNDY_HQ_FOR_ADDYS
    return Addys(
        hq = hq,
        undyToken = staticcall UndyHq(hq).undyToken(),
        ledger = staticcall UndyHq(hq).getAddr(LEDGER_ID),
        missionControl = staticcall UndyHq(hq).getAddr(MISSION_CONTROL_ID),
        legoBook = staticcall UndyHq(hq).getAddr(LEGO_BOOK_ID),
        switchboard = staticcall UndyHq(hq).getAddr(SWITCHBOARD_ID),
        hatchery = staticcall UndyHq(hq).getAddr(HATCHERY_ID),
        lootDistributor = staticcall UndyHq(hq).getAddr(LOOT_DISTRIBUTOR_ID),
        appraiser = staticcall UndyHq(hq).getAddr(APPRAISER_ID),
        walletBackpack = staticcall UndyHq(hq).getAddr(WALLET_BACKPACK_ID),
        billing = staticcall UndyHq(hq).getAddr(BILLING_ID),
        vaultRegistry = staticcall UndyHq(hq).getAddr(VAULT_REGISTRY_ID),
    )


##########
# Tokens #
##########


@view
@internal
def _getUndyToken() -> address:
    return staticcall UndyHq(UNDY_HQ_FOR_ADDYS).undyToken()


###########
# Helpers #
###########


# undy hq


@view
@external
def getUndyHq() -> address:
    return self._getUndyHq()


@view
@internal
def _getUndyHq() -> address:
    return UNDY_HQ_FOR_ADDYS


# utils


@view
@internal
def _isValidUndyAddr(_addr: address, _hq: address = empty(address)) -> bool:
    hq: address = _hq
    if _hq == empty(address):
        hq = UNDY_HQ_FOR_ADDYS
    
    # core departments
    if staticcall UndyHq(hq).isValidAddr(_addr):
        return True

    # lego book
    legoBook: address = staticcall UndyHq(hq).getAddr(LEGO_BOOK_ID)
    if legoBook != empty(address) and staticcall LegoBook(legoBook).isLegoAddr(_addr):
        return True

    # switchboard config
    switchboard: address = staticcall UndyHq(hq).getAddr(SWITCHBOARD_ID)
    if switchboard != empty(address) and staticcall Switchboard(switchboard).isSwitchboardAddr(_addr):
        return True

    return False


@view
@internal
def _isSwitchboardAddr(_addr: address) -> bool:
    switchboard: address = staticcall UndyHq(UNDY_HQ_FOR_ADDYS).getAddr(SWITCHBOARD_ID)
    if switchboard == empty(address):
        return False
    return staticcall Switchboard(switchboard).isSwitchboardAddr(_addr)


@view
@internal
def _isLegoBookAddr(_addr: address) -> bool:
    legoBook: address = staticcall UndyHq(UNDY_HQ_FOR_ADDYS).getAddr(LEGO_BOOK_ID)
    if legoBook == empty(address):
        return False
    return staticcall LegoBook(legoBook).isLegoAddr(_addr)


###############
# Departments #
###############


# ledger


@view
@internal
def _getLedgerId() -> uint256:
    return LEDGER_ID


@view
@internal
def _getLedgerAddr() -> address:
    return staticcall UndyHq(UNDY_HQ_FOR_ADDYS).getAddr(LEDGER_ID)


# mission control


@view
@internal
def _getMissionControlId() -> uint256:
    return MISSION_CONTROL_ID


@view
@internal
def _getMissionControlAddr() -> address:
    return staticcall UndyHq(UNDY_HQ_FOR_ADDYS).getAddr(MISSION_CONTROL_ID)


# lego book


@view
@internal
def _getLegoBookId() -> uint256:
    return LEGO_BOOK_ID


@view
@internal
def _getLegoBookAddr() -> address:
    return staticcall UndyHq(UNDY_HQ_FOR_ADDYS).getAddr(LEGO_BOOK_ID)


# switchboard


@view
@internal
def _getSwitchboardId() -> uint256:
    return SWITCHBOARD_ID


@view
@internal
def _getSwitchboardAddr() -> address:
    return staticcall UndyHq(UNDY_HQ_FOR_ADDYS).getAddr(SWITCHBOARD_ID)


# hatchery


@view
@internal
def _getHatcheryId() -> uint256:
    return HATCHERY_ID


@view
@internal
def _getHatcheryAddr() -> address:
    return staticcall UndyHq(UNDY_HQ_FOR_ADDYS).getAddr(HATCHERY_ID)


# loot distributor


@view
@internal
def _getLootDistributorId() -> uint256:
    return LOOT_DISTRIBUTOR_ID


@view
@internal
def _getLootDistributorAddr() -> address:
    return staticcall UndyHq(UNDY_HQ_FOR_ADDYS).getAddr(LOOT_DISTRIBUTOR_ID)


# appraiser


@view
@internal
def _getAppraiserId() -> uint256:
    return APPRAISER_ID


@view
@internal
def _getAppraiserAddr() -> address:
    return staticcall UndyHq(UNDY_HQ_FOR_ADDYS).getAddr(APPRAISER_ID)


# wallet backpack


@view
@internal
def _getWalletBackpackId() -> uint256:
    return WALLET_BACKPACK_ID


@view
@internal
def _getWalletBackpackAddr() -> address:
    return staticcall UndyHq(UNDY_HQ_FOR_ADDYS).getAddr(WALLET_BACKPACK_ID)


# billing


@view
@internal
def _getBillingId() -> uint256:
    return BILLING_ID


@view
@internal
def _getBillingAddr() -> address:
    return staticcall UndyHq(UNDY_HQ_FOR_ADDYS).getAddr(BILLING_ID)


# vault registry


@view
@internal
def _getVaultRegistryId() -> uint256:
    return VAULT_REGISTRY_ID


@view
@internal
def _getVaultRegistryAddr() -> address:
    return staticcall UndyHq(UNDY_HQ_FOR_ADDYS).getAddr(VAULT_REGISTRY_ID)


# helpers


@view
@internal
def _getHelpersId() -> uint256:
    return HELPERS_ID


@view
@internal
def _getHelpersAddr() -> address:
    return staticcall UndyHq(UNDY_HQ_FOR_ADDYS).getAddr(HELPERS_ID)