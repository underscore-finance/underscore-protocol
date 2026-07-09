#      _   __            __           ___                   
#     | | / /__ ___  ___/ /__  ____  / _ \_______ __ ____ __
#     | |/ / -_) _ \/ _  / _ \/ __/ / ___/ __/ _ \\ \ / // /
#     |___/\__/_//_/\_,_/\___/_/   /_/  /_/  \___/_\_\\_, / 
#                                                    /___/  
#                                                                                                     
#     ╔═══════════════════════════════════════════════════════════════════╗
#     ║  ** Vendor Proxy **                                               ║
#     ║  Per-service payee that forwards funds to the PayProcessor.       ║
#     ╚═══════════════════════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# A minimal, per-service contract deployed by the VendorRegistry (which holds the vendor's human id on
# its own record). It IS the address a UserWallet authorizes as a Payee — so authorizing "pay this
# service" is a first-class Underscore Payee grant. It only holds funds transiently: after a debit
# lands here (UserWallet → vendor), the PayProcessor pulls it out via `transferToProcessor` to
# settle. It is self-contained: it owns this service's allow-listed destinations, and the list is edited
# directly by the Switchboard (`isSwitchboardAddr(msg.sender)`). The PayProcessor reads `isAllowed`
# to gate x402 settlement. The Switchboard can also recover any stray funds parked on the vendor.

# @version 0.4.3
# pragma optimize codesize


from ethereum.ercs import IERC20

interface Registry:
    def getAddr(_regId: uint256) -> address: view

interface Switchboard:
    def isSwitchboardAddr(_addr: address) -> bool: view

interface Billing:
    def pullPaymentAsCheque(_userWallet: address, _paymentAsset: address, _paymentAmount: uint256) -> (uint256, uint256): nonpayable
    def pullPaymentAsPayee(_userWallet: address, _paymentAsset: address, _paymentAmount: uint256) -> (uint256, uint256): nonpayable

PAY_PROCESSOR_ID: constant(uint256) = 13  # UndyHq dept id of the PayProcessor
SWITCHBOARD_ID: constant(uint256) = 4         # UndyHq dept id of the Switchboard (the only allow-list editor)
BILLING_ID: constant(uint256) = 9             # UndyHq dept id of Billing (payee / cheque pull entry point)
MAX_RECOVER_ASSETS: constant(uint256) = 20

HQ: public(immutable(address))

# self-contained destination allow-list (1-based; count == numDests - 1). Edited only by the Switchboard.
isAllowed: public(HashMap[address, bool])       # dest -> allowed (O(1) gate read by the PayProcessor)
numDests: public(uint256)                       # next free idx (starts at 1)
dests: public(HashMap[uint256, address])        # idx -> dest
indexOfDest: public(HashMap[address, uint256])  # dest -> idx (0 = not allowed)

event PulledToProcessor:
    processor: indexed(address)
    asset: indexed(address)
    amount: uint256

event DestinationAdded:
    dest: indexed(address)

event DestinationRemoved:
    dest: indexed(address)

event FundsRecovered:
    asset: indexed(address)
    recipient: indexed(address)
    balance: uint256


@deploy
def __init__(_hq: address):
    assert _hq != empty(address)  # dev: hq required
    HQ = _hq
    self.numDests = 1  # 1-based list (Underscore list style)


@view
@internal
def _processor() -> address:
    return staticcall Registry(HQ).getAddr(PAY_PROCESSOR_ID)


@view
@external
def processor() -> address:
    return self._processor()


@view
@internal
def _isSwitchboard(_caller: address) -> bool:
    switchboard: address = staticcall Registry(HQ).getAddr(SWITCHBOARD_ID)
    return switchboard != empty(address) and staticcall Switchboard(switchboard).isSwitchboardAddr(_caller)


@external
def transferToProcessor(_asset: address, _amount: uint256 = max_value(uint256)) -> uint256:
    # Only the PayProcessor may pull funds out of this vendor (into itself, to settle). `_amount`
    # defaults to the full balance.
    processor: address = self._processor()
    assert msg.sender == processor  # dev: only processor
    amount: uint256 = _amount
    if amount == max_value(uint256):
        amount = staticcall IERC20(_asset).balanceOf(self)
    if amount != 0:
        assert extcall IERC20(_asset).transfer(processor, amount, default_return_value=True)  # dev: transfer failed
    log PulledToProcessor(processor=processor, asset=_asset, amount=amount)
    return amount


######################################################
# pull a payment (payee / cheque) — processor only #
######################################################


@external
def pullPayment(_userWallet: address, _asset: address, _amount: uint256, _isCheque: bool) -> (uint256, uint256):
    # This vendor is registered as a payee / cheque recipient on the user wallet; the PayProcessor
    # drives the pull and the funds land HERE (this vendor is the recipient) via Billing. Processor-only.
    # Future-proof: `_isCheque` routes between Billing's two pull paths (cheque vs payee).
    assert msg.sender == self._processor()  # dev: only processor
    billing: address = staticcall Registry(HQ).getAddr(BILLING_ID)
    assert billing != empty(address)  # dev: no billing
    if _isCheque:
        return extcall Billing(billing).pullPaymentAsCheque(_userWallet, _asset, _amount)
    return extcall Billing(billing).pullPaymentAsPayee(_userWallet, _asset, _amount)


###############################################
# destination allow-list (edited by Switchboard) #
###############################################


@external
def addDestination(_dest: address):
    assert self._isSwitchboard(msg.sender)  # dev: not switchboard
    assert _dest != empty(address)  # dev: zero dest
    if self.isAllowed[_dest]:
        return
    self.isAllowed[_dest] = True
    did: uint256 = self.numDests
    self.dests[did] = _dest
    self.indexOfDest[_dest] = did
    self.numDests = did + 1
    log DestinationAdded(dest=_dest)


@external
def removeDestination(_dest: address):
    assert self._isSwitchboard(msg.sender)  # dev: not switchboard
    targetIndex: uint256 = self.indexOfDest[_dest]
    assert targetIndex != 0  # dev: not allowed
    self.isAllowed[_dest] = False

    # swap the last dest into the freed slot (dense list, Underscore whitelist idiom)
    lastIndex: uint256 = self.numDests - 1
    self.numDests = lastIndex
    lastItem: address = self.dests[lastIndex]
    self.dests[targetIndex] = lastItem
    self.indexOfDest[lastItem] = targetIndex
    self.dests[lastIndex] = empty(address)
    self.indexOfDest[_dest] = 0
    log DestinationRemoved(dest=_dest)


#################
# recover funds #
#################

# Same behavior as the DeptBasics module's recover functions, inlined (the vendor is a minimal blueprint
# and does not initialize the full module). Switchboard-gated, like every other dept recover path.


@external
def recoverFunds(_recipient: address, _asset: address):
    assert self._isSwitchboard(msg.sender)  # dev: not switchboard
    self._recoverFunds(_recipient, _asset)


@external
def recoverFundsMany(_recipient: address, _assets: DynArray[address, MAX_RECOVER_ASSETS]):
    assert self._isSwitchboard(msg.sender)  # dev: not switchboard
    for a: address in _assets:
        self._recoverFunds(_recipient, a)


@internal
def _recoverFunds(_recipient: address, _asset: address):
    assert empty(address) not in [_recipient, _asset]  # dev: invalid recipient or asset
    balance: uint256 = staticcall IERC20(_asset).balanceOf(self)
    assert balance != 0  # dev: nothing to recover
    assert extcall IERC20(_asset).transfer(_recipient, balance, default_return_value=True)  # dev: recovery failed
    log FundsRecovered(asset=_asset, recipient=_recipient, balance=balance)
