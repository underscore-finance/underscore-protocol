# @version 0.4.1

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
    legoBook: address
    switchboard: address

# hq
UNDY_HQ_FOR_ADDYS: immutable(address)

# core addys
UNDY_TOKEN_ID: constant(uint256) = 1
LEGO_BOOK_ID: constant(uint256) = 2
SWITCHBOARD_ID: constant(uint256) = 3


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
        hq=hq,
        undyToken=staticcall UndyHq(hq).getAddr(UNDY_TOKEN_ID),
        legoBook=staticcall UndyHq(hq).getAddr(LEGO_BOOK_ID),
        switchboard=staticcall UndyHq(hq).getAddr(SWITCHBOARD_ID),
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
def _isValidUndyAddr(_addr: address) -> bool:
    hq: address = UNDY_HQ_FOR_ADDYS
    
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

