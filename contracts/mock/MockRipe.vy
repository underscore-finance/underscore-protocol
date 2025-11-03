# @version 0.4.3

from ethereum.ercs import IERC20Detailed
from ethereum.ercs import IERC20

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


@view
@external
def isValidAddr(_addr: address) -> bool:
    return True


# MOCK RIPE PRICE DESK


@view
@external
def getPrice(_asset: address, _shouldRaise: bool = False) -> uint256:
    return self.mockPrices[_asset]


@external
def depositIntoGovVault(
    _asset: address,
    _amount: uint256,
    _lockDuration: uint256,
    _user: address = msg.sender,
) -> uint256:
    amount: uint256 = min(_amount, staticcall IERC20(_asset).balanceOf(msg.sender))
    assert amount != 0 # dev: cannot transfer 0 amount
    assert extcall IERC20(_asset).transferFrom(msg.sender, self, amount, default_return_value=True) # dev: transfer failed
    return amount