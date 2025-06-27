# @version 0.4.3

implements: Department

exports: addys.__interface__
exports: deptBasics.__interface__

initializes: addys
initializes: deptBasics[addys := addys]

import contracts.modules.Addys as addys
import contracts.modules.DeptBasics as deptBasics
from interfaces import Department

interface RipePriceDesk:
    def getPrice(_asset: address, _shouldRaise: bool = False) -> uint256: view

interface RipeHq:
    def getAddr(_regId: uint256) -> address: view

interface Ledger:
    def isUserWallet(_user: address) -> bool: view

interface LegoBook:
    def isLegoAddr(_addr: address) -> bool: view

struct LastPrice:
    price: uint256
    lastUpdate: uint256

lastPrice: public(HashMap[address, LastPrice]) # asset -> last price

RIPE_PRICE_DESK_ID: constant(uint256) = 7
RIPE_HQ: immutable(address)


@deploy
def __init__(_undyHq: address, _ripeHq: address):
    addys.__init__(_undyHq)
    deptBasics.__init__(False, False) # no minting

    RIPE_HQ = _ripeHq


#############
# Get Price #
#############


# get price


@view
@external
def getPrice(_asset: address, _isYieldAsset: bool, _staleBlocks: uint256) -> uint256:
    data: LastPrice = empty(LastPrice)
    na: bool = False
    data, na = self._getPrice(_asset, _isYieldAsset, _staleBlocks)
    return data.price


@view
@internal
def _getPrice(_asset: address, _isYieldAsset: bool, _staleBlocks: uint256) -> (LastPrice, bool):
    data: LastPrice = self.lastPrice[_asset]

    # same block, return cached price
    if data.lastUpdate == block.number:
        return data, False

    prevPrice: uint256 = data.price

    # yield assets handled slightly differently
    if _isYieldAsset:
        data.price = self._getYieldAssetPrice(_asset)

    # normal assets
    else:

        # check if recent price is good enough
        if _staleBlocks != 0 and data.lastUpdate + _staleBlocks > block.number:
            return data, False

        # get price from Ripe
        data.price = self._getRipePrice(_asset)

    # check if price changed
    didPriceChange: bool = False
    if data.price != prevPrice:
        didPriceChange = True

    data.lastUpdate = block.number
    return data, didPriceChange


@view
@internal
def _getYieldAssetPrice(_asset: address) -> uint256:
    # TODO: get CURRENT price per share from Lego, instead of snapshot/weighted ripe price
    return self._getRipePrice(_asset)


################
# Update Price #
################


# from lego


@external
def updateAndGetPriceLego(_asset: address) -> uint256:
    assert staticcall LegoBook(addys._getLegoBookAddr()).isLegoAddr(msg.sender) # dev: no perms

    # TODO

    return 0


# from user wallet


@external
def updateAndGetPriceFromWallet(
    _asset: address,
    _isYieldAsset: bool,
    _staleBlocks: uint256,
) -> uint256:
    assert staticcall Ledger(addys._getLedgerAddr()).isUserWallet(msg.sender) # dev: no perms

    if _asset == empty(address):
        return 0

    # get latest price
    data: LastPrice = empty(LastPrice)
    didPriceChange: bool = False
    data, didPriceChange = self._getPrice(_asset, _isYieldAsset, _staleBlocks)

    # only save if price changed
    if didPriceChange:
        self.lastPrice[_asset] = data

    return data.price



####################
# Ripe Integration #
####################


@view
@external
def getRipePrice(_asset: address) -> uint256:
    return self._getRipePrice(_asset)


@view
@internal
def _getRipePrice(_asset: address) -> uint256:
    ripePriceDesk: address = staticcall RipeHq(RIPE_HQ).getAddr(RIPE_PRICE_DESK_ID)
    if ripePriceDesk == empty(address):
        return 0
    return staticcall RipePriceDesk(ripePriceDesk).getPrice(_asset, False)