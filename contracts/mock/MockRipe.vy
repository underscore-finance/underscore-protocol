# @version 0.4.3

from ethereum.ercs import IERC20Detailed

mockPrices: public(HashMap[address, uint256]) # asset -> price


@deploy
def __init__():
    pass


# MOCK CONFIG PRICE


@external
def setPrice(_asset: address, _price: uint256):
    self.mockPrices[_asset] = _price


# MOCK RIPE HQ


@view
@external
def getAddr(_regId: uint256) -> address:
    return self


# MOCK RIPE PRICE DESK


@view
@external
def getPrice(_asset: address, _shouldRaise: bool = False) -> uint256:
    return self.mockPrices[_asset]


@view
@external
def getUsdValue(_asset: address, _amount: uint256, _shouldRaise: bool = False) -> uint256:
    decimals: uint256 = convert(staticcall IERC20Detailed(_asset).decimals(), uint256)
    return self.mockPrices[_asset] * _amount // (10 ** decimals)