# @version 0.4.3

from ethereum.ercs import IERC20

event Transfer:
    sender: indexed(address)
    receiver: indexed(address)
    value: uint256

event Approval:
    owner: indexed(address)
    spender: indexed(address)
    value: uint256

asset: public(address)
balanceOf: public(HashMap[address, uint256]) # user -> shares
totalSupply: public(uint256)
allowance: public(HashMap[address, HashMap[address, uint256]])

# NOTE: this does not include ALL required erc20/4626 methods. 
# This only includes what we use/need for our strats


@deploy
def __init__(_asset: address):
    self.asset = _asset


# compound v3


@view
@external
def baseToken() -> address:
    return self.asset


@external
def supplyTo(_recipient: address, _asset: address, _amount: uint256):
    assert extcall IERC20(_asset).transferFrom(msg.sender, self, _amount, default_return_value=True) # dev: transfer failed
    self.balanceOf[_recipient] += _amount
    self.totalSupply += _amount


@external
def withdrawTo(_recipient: address, _asset: address, _amount: uint256):
    shares: uint256 = min(_amount, self.balanceOf[msg.sender])
    amount: uint256 = min(shares, staticcall IERC20(_asset).balanceOf(self))
    assert extcall IERC20(_asset).transfer(_recipient, amount, default_return_value=True) # dev: transfer failed
    self.balanceOf[msg.sender] -= shares
    self.totalSupply -= shares


# compound v2 (moonwell)


@view
@external
def underlying() -> address:
    return self.asset


@external
def mint(_amount: uint256) -> uint256:
    assert extcall IERC20(self.asset).transferFrom(msg.sender, self, _amount, default_return_value=True) # dev: transfer failed
    self.balanceOf[msg.sender] += _amount
    self.totalSupply += _amount
    return 0


@external
def redeem(_ctokenAmount: uint256) -> uint256:
    shares: uint256 = min(_ctokenAmount, self.balanceOf[msg.sender])
    amount: uint256 = min(shares, staticcall IERC20(self.asset).balanceOf(self))
    assert extcall IERC20(self.asset).transfer(msg.sender, amount, default_return_value=True) # dev: transfer failed
    self.balanceOf[msg.sender] -= shares
    self.totalSupply -= shares
    return 0


# erc20 methods


@external
def transfer(_to: address, _value: uint256) -> bool:
    self.balanceOf[msg.sender] -= _value
    self.balanceOf[_to] += _value
    log Transfer(sender=msg.sender, receiver=_to, value=_value)
    return True


@external
def transferFrom(_from: address, _to: address, _value: uint256) -> bool:
    self.balanceOf[_from] -= _value
    self.balanceOf[_to] += _value
    self.allowance[_from][msg.sender] -= _value
    log Transfer(sender=_from, receiver=_to, value=_value)
    return True


@external
def approve(_spender: address, _value: uint256) -> bool:
    self.allowance[msg.sender][_spender] = _value
    log Approval(owner=msg.sender, spender=_spender, value=_value)
    return True