# @version 0.4.3
# Minimal Billing stand-in for the proxy pull-payment unit tests. Records the last pull call and which
# path (cheque vs payee) the proxy routed to, and echoes the requested amount back.

lastUserWallet: public(address)
lastAsset: public(address)
lastAmount: public(uint256)
lastWasCheque: public(bool)

@external
def pullPaymentAsCheque(_userWallet: address, _paymentAsset: address, _paymentAmount: uint256) -> (uint256, uint256):
    self.lastUserWallet = _userWallet
    self.lastAsset = _paymentAsset
    self.lastAmount = _paymentAmount
    self.lastWasCheque = True
    return (_paymentAmount, _paymentAmount)

@external
def pullPaymentAsPayee(_userWallet: address, _paymentAsset: address, _paymentAmount: uint256) -> (uint256, uint256):
    self.lastUserWallet = _userWallet
    self.lastAsset = _paymentAsset
    self.lastAmount = _paymentAmount
    self.lastWasCheque = False
    return (_paymentAmount, _paymentAmount)
