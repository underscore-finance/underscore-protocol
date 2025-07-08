# @version 0.4.3

implements: IERC20
implements: IERC20Detailed

from ethereum.ercs import IERC20
from ethereum.ercs import IERC20Detailed

event Deposit:
    user: indexed(address)
    amount: uint256

event Withdrawal:
    user: indexed(address)
    amount: uint256

event Transfer:
    sender: indexed(address)
    receiver: indexed(address)
    amount: uint256

event Approval:
    owner: indexed(address)
    spender: indexed(address)
    amount: uint256

# erc20 metadata
NAME: constant(String[13]) = "Wrapped Ether"
SYMBOL: constant(String[4]) = "WETH"
DECIMALS: constant(uint8) = 18

# erc20 state variables
balanceOf: public(HashMap[address, uint256])
allowance: public(HashMap[address, HashMap[address, uint256]])


@deploy
def __init__():
    pass


@view
@external
def name() -> String[13]:
    return NAME


@view
@external
def symbol() -> String[4]:
    return SYMBOL


@view
@external
def decimals() -> uint8:
    return DECIMALS


@view
@external
def totalSupply() -> uint256:
    return self.balance


@payable
@external
def deposit():
    self.balanceOf[msg.sender] += msg.value
    log Deposit(user=msg.sender, amount=msg.value)


@external
def withdraw(_amount: uint256):
    assert self.balanceOf[msg.sender] >= _amount # dev: not enough balance
    self.balanceOf[msg.sender] -= _amount
    send(msg.sender, _amount)
    log Withdrawal(user=msg.sender, amount=_amount)


@external
def transfer(_recipient: address, _amount: uint256) -> bool:
    self.balanceOf[msg.sender] -= _amount
    self.balanceOf[_recipient] += _amount
    log Transfer(sender=msg.sender, receiver=_recipient, amount=_amount)
    return True


@external
def transferFrom(_sender: address, _recipient: address, _amount: uint256) -> bool:
    self.allowance[_sender][msg.sender] -= _amount
    self.balanceOf[_sender] -= _amount
    self.balanceOf[_recipient] += _amount
    log Transfer(sender=_sender, receiver=_recipient, amount=_amount)
    return True


@external
def approve(_spender: address, _amount: uint256) -> bool:
    self.allowance[msg.sender][_spender] = _amount
    log Approval(owner=msg.sender, spender=_spender, amount=_amount)
    return True
