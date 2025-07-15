# @version 0.4.3

from ethereum.ercs import IERC20Detailed

mockPrices: public(HashMap[address, uint256]) # asset -> price
addr: public(address)


@deploy
def __init__():
    self.addr = self


# MOCK CONFIG PRICE


@external
def setPrice(_asset: address, _price: uint256):
    self.mockPrices[_asset] = _price


@external
def setAddr(_addr: address):
    self.addr = _addr


# MOCK RIPE HQ


@view
@external
def getAddr(_regId: uint256) -> address:
    return self.addr


@external
def addPriceSnapshot(_asset: address) -> bool:
    return True


# MOCK RIPE PRICE DESK


@view
@external
def getPrice(_asset: address, _shouldRaise: bool = False) -> uint256:
    return self.mockPrices[_asset]
