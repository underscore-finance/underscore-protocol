# @version 0.4.3
# Minimal AgentWrapper stand-in for the payments unit tests. `transferFunds` / `createAndPayCheque`
# move the token from this (pre-funded) mock to the recipient, simulating a push from the user's
# wallet; `lastWasCheque` records which path the PaymentSender took. `withdrawFromYield` reports a
# configurable underlying amount received (the funds are assumed already held here).

from ethereum.ercs import IERC20

usdc: public(address)
nextWithdrawAmount: public(uint256)
lastWasCheque: public(bool)

@deploy
def __init__(_usdc: address):
    self.usdc = _usdc

@external
def setNextWithdraw(_amount: uint256):
    self.nextWithdrawAmount = _amount

@external
def transferFunds(_userWallet: address, _recipient: address, _asset: address, _amount: uint256) -> (uint256, uint256):
    self.lastWasCheque = False
    assert extcall IERC20(_asset).transfer(_recipient, _amount, default_return_value=True)
    return (_amount, _amount)

@external
def createAndPayCheque(_userWallet: address, _recipient: address, _asset: address, _amount: uint256) -> (uint256, uint256):
    self.lastWasCheque = True
    assert extcall IERC20(_asset).transfer(_recipient, _amount, default_return_value=True)
    return (_amount, _amount)

@external
def withdrawFromYield(_userWallet: address, _legoId: uint256, _vaultToken: address, _amount: uint256, _extraData: bytes32) -> (uint256, address, uint256, uint256):
    return (_amount, self.usdc, self.nextWithdrawAmount, 0)
