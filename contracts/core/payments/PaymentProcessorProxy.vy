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
# settle. It also owns this service's allow-listed destinations (self-contained): the PaymentProcessor
# reads `isAllowed` to gate x402 settlement, and the list is edited exclusively through the ProxyStore
# CRUD entry point — enforced here by `msg.sender == ProxyStore`.

# @version 0.4.3
# pragma optimize codesize


from ethereum.ercs import IERC20

interface Registry:
    def getAddr(_regId: uint256) -> address: view

PAYMENT_PROCESSOR_ID: constant(uint256) = 13  # UndyHq dept id of the PaymentProcessor
PROXY_STORE_ID: constant(uint256) = 12        # UndyHq dept id of the ProxyStore (the only allow-list editor)
MAX_LIST: constant(uint256) = 100

HQ: public(immutable(address))
ID: public(immutable(String[128]))

# self-contained destination allow-list (managed only via the ProxyStore CRUD entry point)
isAllowed: public(HashMap[address, bool])       # dest -> allowed (O(1) gate read by the PaymentProcessor)
numDests: public(uint256)
dests: public(HashMap[uint256, address])        # 1-based idx -> dest
indexOfDest: public(HashMap[address, uint256])  # dest -> idx

event PulledToProcessor:
    processor: indexed(address)
    asset: indexed(address)
    amount: uint256

event DestinationAdded:
    dest: indexed(address)

event DestinationRemoved:
    dest: indexed(address)


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


@view
@internal
def _store() -> address:
    return staticcall Registry(HQ).getAddr(PROXY_STORE_ID)


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


#######################################################
# destination allow-list (edited only via ProxyStore) #
#######################################################


@external
def addDestination(_dest: address):
    assert msg.sender == self._store()  # dev: only store
    assert _dest != empty(address)  # dev: zero dest
    if self.isAllowed[_dest]:
        return
    self.isAllowed[_dest] = True
    idx: uint256 = self.numDests + 1
    self.dests[idx] = _dest
    self.indexOfDest[_dest] = idx
    self.numDests = idx
    log DestinationAdded(dest=_dest)


@external
def removeDestination(_dest: address):
    assert msg.sender == self._store()  # dev: only store
    assert self.isAllowed[_dest]  # dev: not allowed
    self.isAllowed[_dest] = False
    idx: uint256 = self.indexOfDest[_dest]
    last: uint256 = self.numDests
    if idx != last:
        moved: address = self.dests[last]
        self.dests[idx] = moved
        self.indexOfDest[moved] = idx
    self.dests[last] = empty(address)
    self.indexOfDest[_dest] = 0
    self.numDests = last - 1
    log DestinationRemoved(dest=_dest)


@view
@external
def getDestinations() -> DynArray[address, MAX_LIST]:
    out: DynArray[address, MAX_LIST] = []
    n: uint256 = self.numDests
    for i: uint256 in range(1, MAX_LIST + 1):
        if i > n:
            break
        out.append(self.dests[i])
    return out
