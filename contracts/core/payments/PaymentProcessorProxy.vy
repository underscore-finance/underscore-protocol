#            _            _            _             _            _            _      
#           / /\         /\ \         /\ \     _    /\ \         /\ \         /\ \    
#          / /  \       /  \ \       /  \ \   /\_\ /  \ \____   /  \ \       /  \ \   
#         / / /\ \__   / /\ \ \     / /\ \ \_/ / // /\ \_____\ / /\ \ \     / /\ \ \  
#        / / /\ \___\ / / /\ \_\   / / /\ \___/ // / /\/___  // / /\ \_\   / / /\ \_\ 
#        \ \ \ \/___// /_/_ \/_/  / / /  \/____// / /   / / // /_/_ \/_/  / / /_/ / / 
#         \ \ \     / /____/\    / / /    / / // / /   / / // /____/\    / / /__\/ /  
#     _    \ \ \   / /\____\/   / / /    / / // / /   / / // /\____\/   / / /_____/   
#    /_/\__/ / /  / / /______  / / /    / / / \ \ \__/ / // / /______  / / /\ \ \     
#    \ \/___/ /  / / /_______\/ / /    / / /   \ \___\/ // / /_______\/ / /  \ \ \    
#     \_____\/   \/__________/\/_/     \/_/     \/_____/ \/__________/\/_/    \_\/    
#
#     ╔═══════════════════════════════════════════════════════════════════╗
#     ║  ** Payment Processor Proxy **                                    ║
#     ║  Per-service payee that forwards funds to the PaymentProcessor.   ║
#     ╚═══════════════════════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# A minimal, per-service contract deployed by the ProxyStore. It carries a human string `ID` (e.g.
# "x402joker.com") and IS the address a UserWallet authorizes as a Payee — so authorizing "pay this
# service" is a first-class Underscore Payee grant. It only holds funds transiently: after a debit
# lands here (UserWallet → proxy), the PaymentProcessor pulls it out via `transferToProcessor` to
# settle. The allow-listed destinations for this service live in the ProxyStore's index, not here.

# @version 0.4.3
# pragma optimize codesize


from ethereum.ercs import IERC20

interface Registry:
    def getAddr(_regId: uint256) -> address: view

PAYMENT_PROCESSOR_ID: constant(uint256) = 13  # UndyHq dept id of the PaymentProcessor

HQ: public(immutable(address))
ID: public(immutable(String[128]))

event PulledToProcessor:
    processor: indexed(address)
    asset: indexed(address)
    amount: uint256


@deploy
def __init__(_hq: address, _id: String[128]):
    assert _hq != empty(address)  # dev: hq required
    HQ = _hq
    ID = _id


@view
@internal
def _processor() -> address:
    return staticcall Registry(HQ).getAddr(PAYMENT_PROCESSOR_ID)


@view
@external
def processor() -> address:
    return self._processor()


@external
def transferToProcessor(_asset: address, _amount: uint256 = max_value(uint256)) -> uint256:
    # Only the PaymentProcessor may pull funds out of this proxy (into itself, to settle). `_amount`
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
