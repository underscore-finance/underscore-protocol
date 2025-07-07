# @version 0.4.3

interface UndyHq:
    def isValidAddr(_addr: address) -> bool: view
    def getAddr(_regId: uint256) -> address: view

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
    bossValidator: address
    paymaster: address
    migrator: address

# hq
UNDY_HQ_FOR_ADDYS: immutable(address)

# core addys
UNDY_TOKEN_ID: constant(uint256) = 1
LEDGER_ID: constant(uint256) = 2
MISSION_CONTROL_ID: constant(uint256) = 3
LEGO_BOOK_ID: constant(uint256) = 4
SWITCHBOARD_ID: constant(uint256) = 5
HATCHERY_ID: constant(uint256) = 6
LOOT_DISTRIBUTOR_ID: constant(uint256) = 7
APPRAISER_ID: constant(uint256) = 8
BOSS_VALIDATOR_ID: constant(uint256) = 9
PAYMASTER_ID: constant(uint256) = 10
MIGRATOR_ID: constant(uint256) = 11


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
        undyToken = staticcall UndyHq(hq).getAddr(UNDY_TOKEN_ID),
        ledger = staticcall UndyHq(hq).getAddr(LEDGER_ID),
        missionControl = staticcall UndyHq(hq).getAddr(MISSION_CONTROL_ID),
        legoBook = staticcall UndyHq(hq).getAddr(LEGO_BOOK_ID),
        switchboard = staticcall UndyHq(hq).getAddr(SWITCHBOARD_ID),
        hatchery = staticcall UndyHq(hq).getAddr(HATCHERY_ID),
        lootDistributor = staticcall UndyHq(hq).getAddr(LOOT_DISTRIBUTOR_ID),
        appraiser = staticcall UndyHq(hq).getAddr(APPRAISER_ID),
        bossValidator = staticcall UndyHq(hq).getAddr(BOSS_VALIDATOR_ID),
        paymaster = staticcall UndyHq(hq).getAddr(PAYMASTER_ID),
        migrator = staticcall UndyHq(hq).getAddr(MIGRATOR_ID),
    )


##########
# Tokens #
##########


@view
@internal
def _getUndyToken() -> address:
    return staticcall UndyHq(UNDY_HQ_FOR_ADDYS).getAddr(UNDY_TOKEN_ID)


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


# boss validator


@view
@internal
def _getBossValidatorId() -> uint256:
    return BOSS_VALIDATOR_ID


@view
@internal
def _getBossValidatorAddr() -> address:
    return staticcall UndyHq(UNDY_HQ_FOR_ADDYS).getAddr(BOSS_VALIDATOR_ID)


# paymaster


@view
@internal
def _getPaymasterId() -> uint256:
    return PAYMASTER_ID


@view
@internal
def _getPaymasterAddr() -> address:
    return staticcall UndyHq(UNDY_HQ_FOR_ADDYS).getAddr(PAYMASTER_ID)


# migrator


@view
@internal
def _getMigratorId() -> uint256:
    return MIGRATOR_ID


@view
@internal
def _getMigratorAddr() -> address:
    return staticcall UndyHq(UNDY_HQ_FOR_ADDYS).getAddr(MIGRATOR_ID)

