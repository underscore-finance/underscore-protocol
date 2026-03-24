# @version 0.4.3

from ethereum.ercs import IERC20
from ethereum.ercs import IERC20Detailed

event Transfer:
    sender: indexed(address)
    receiver: indexed(address)
    value: uint256

event Approval:
    owner: indexed(address)
    spender: indexed(address)
    value: uint256

asset: public(address)
balanceOf: public(HashMap[address, uint256])
totalSupply: public(uint256)
allowance: public(HashMap[address, HashMap[address, uint256]])
reportedAssets: public(uint256)


@deploy
def __init__(_asset: address):
    self.asset = _asset


@external
def deposit(_amount: uint256, _receiver: address) -> uint256:
    shares: uint256 = self._calcSharesOnDeposit(_amount)
    assert extcall IERC20(self.asset).transferFrom(msg.sender, self, _amount, default_return_value=True) # dev: transfer failed
    self.balanceOf[_receiver] += shares
    self.totalSupply += shares
    self.reportedAssets += _amount
    return shares


@external
def redeem(_shares: uint256, _receiver: address, _owner: address) -> uint256:
    shares: uint256 = min(_shares, self.balanceOf[_owner])
    reportedAmount: uint256 = self._sharesToAmount(shares)
    amount: uint256 = min(reportedAmount, staticcall IERC20(self.asset).balanceOf(self))
    assert extcall IERC20(self.asset).transfer(_receiver, amount, default_return_value=True) # dev: transfer failed
    self.balanceOf[_owner] -= shares
    self.totalSupply -= shares
    if self.reportedAssets <= reportedAmount:
        self.reportedAssets = 0
    else:
        self.reportedAssets -= reportedAmount
    return amount


@view
@external
def convertToAssets(_shares: uint256) -> uint256:
    return self._sharesToAmount(_shares)


@view
@external
def previewRedeem(_shares: uint256) -> uint256:
    return self._sharesToAmount(_shares)


@view
@internal
def _sharesToAmount(_shares: uint256) -> uint256:
    if _shares == 0:
        return 0
    totalShares: uint256 = self.totalSupply
    if totalShares == 0:
        return _shares
    totalAssets: uint256 = self.reportedAssets
    if _shares == totalShares:
        return totalAssets
    return totalAssets * _shares // totalShares


@view
@external
def convertToShares(_amount: uint256) -> uint256:
    return self._amountToShares(_amount)


@view
@internal
def _calcSharesOnDeposit(_amount: uint256) -> uint256:
    totalShares: uint256 = self.totalSupply
    shares: uint256 = 0
    if totalShares == 0:
        shares = _amount
        assert shares > 10 ** convert(staticcall IERC20Detailed(self.asset).decimals() // 2, uint256) # dev: amount too small
    else:
        shares = _amount * totalShares // self.reportedAssets
    assert shares != 0 # dev: did not calc shares
    return shares


@view
@external
def totalAssets() -> uint256:
    return self.reportedAssets


@view
@internal
def _amountToShares(_amount: uint256) -> uint256:
    if _amount == 0:
        return 0
    totalAssets: uint256 = self.reportedAssets
    totalShares: uint256 = self.totalSupply
    if totalAssets == 0 or totalShares == 0:
        return 0
    return _amount * totalShares // totalAssets


@external
def transferAssetOut(_to: address, _value: uint256) -> bool:
    assert extcall IERC20(self.asset).transfer(_to, _value, default_return_value=True) # dev: transfer failed
    return True


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


@view
@external
def decimals() -> uint8:
    return staticcall IERC20Detailed(self.asset).decimals()
