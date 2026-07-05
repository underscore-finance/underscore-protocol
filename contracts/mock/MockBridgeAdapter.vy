# @version 0.4.3
# Reference/test bridge adapter for the PaymentProcessor. Implements IBridgeAdapter: it pulls the
# processor's approved USDC and records the call. A real adapter would forward to a Base→Tempo bridge
# (deposit address / on-chain call) for the given recipient + destChainId — swappable without touching
# the PaymentProcessor.

from ethereum.ercs import IERC20

lastToken: public(address)
lastAmount: public(uint256)
lastRecipient: public(address)
lastDestChainId: public(uint256)

@external
def bridge(_token: address, _amount: uint256, _recipient: address, _destChainId: uint256):
    assert extcall IERC20(_token).transferFrom(msg.sender, self, _amount, default_return_value=True)
    self.lastToken = _token
    self.lastAmount = _amount
    self.lastRecipient = _recipient
    self.lastDestChainId = _destChainId
