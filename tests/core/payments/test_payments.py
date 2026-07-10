import pytest
import boa
from eth_account import Account
from eth_utils import keccak

from constants import ZERO_ADDRESS

EMPTY32 = b"\x00" * 32
NO_VAULT = (0, ZERO_ADDRESS, 0, EMPTY32)
FAR_FUTURE = 9_999_999_999
PAY1 = (1).to_bytes(32, "big")
PAY2 = (2).to_bytes(32, "big")
REF = keccak(text="challenge:joker")
MAGIC = bytes.fromhex("1626ba7e")
FAIL = bytes.fromhex("ffffffff")

RAIL_MPP = 1
RAIL_X402 = 2


def _a(x):
    return str(x).lower()


def _logs(c, name):
    return [e for e in c.get_logs() if type(e).__name__ == name]


def _dests(vendor):
    # enumerate the vendor's 1-based dest list via its public getters (getDestinations was removed)
    return [_a(vendor.dests(i)) for i in range(1, vendor.numDests())]


def _x402_extra(valid_after, valid_before):
    # protocol-specific extraData for the x402 rail: abi_encode(uint256 validAfter, uint256 validBefore).
    # two static uint256 => just the two 32-byte words concatenated.
    return valid_after.to_bytes(32, "big") + valid_before.to_bytes(32, "big")


@pytest.fixture
def admin(env):
    return env.generate_address("payments_admin")


@pytest.fixture
def usdc():
    return boa.load("contracts/mock/MockUsdc.vy", "USD Coin", "USDC", 6)


@pytest.fixture
def mock_hq(admin):
    hq = boa.load("contracts/mock/MockPaymentsHq.vy")
    hq.setAddr(4, hq.address)      # switchboard = self
    hq.setSwitcher(admin, True)
    return hq


@pytest.fixture
def vendor_partial():
    return boa.load_partial("contracts/core/payments/VendorProxy.vy")


@pytest.fixture
def registry(mock_hq, vendor_partial, admin):
    template = vendor_partial.deploy_as_blueprint()
    s = boa.load("contracts/core/payments/VendorRegistry.vy", mock_hq.address, template.address)
    mock_hq.setAddr(12, s.address)
    return s


@pytest.fixture
def bridge_address(env):
    return env.generate_address("bridge_liquidation")


@pytest.fixture
def mock_billing(mock_hq):
    b = boa.load("contracts/mock/MockBilling.vy")
    mock_hq.setAddr(9, b.address)
    return b


@pytest.fixture
def processor(mock_hq, usdc):
    p = boa.load("contracts/core/payments/PayProcessor.vy", mock_hq.address, usdc.address)
    mock_hq.setAddr(13, p.address)
    return p


@pytest.fixture
def joker(registry, admin, vendor_partial):
    return vendor_partial.at(registry.createVendor("x402joker.com", sender=admin))


@pytest.fixture
def agent_wrapper(env):
    return env.generate_address("agent_wrapper")


# ═══════════════════════════ VendorRegistry: factory + registry; VendorProxy: self-contained allow-list ═══════════════════════════

def test_create_vendor(registry, admin, vendor_partial):
    addr = registry.createVendor("x402joker.com", sender=admin)
    assert registry.indexOfVendor(addr) == 1                 # 1-based registry
    assert registry.getNumVendors() == 1
    assert registry.isVendor(addr) is True                   # registered on creation
    assert _a(registry.vendors(1)[0]) == _a(addr)           # id lives on the record
    assert registry.vendors(1)[1] == "x402joker.com"
    # ids are labels now (no id index): a second vendor just takes the next reg id
    addr2 = registry.createVendor("x402joker.com", sender=admin)
    assert registry.indexOfVendor(addr2) == 2
    assert registry.getNumVendors() == 2


def test_create_vendor_perms(registry, alice):
    with boa.reverts("no perms"):
        registry.createVendor("nope.com", sender=alice)


def test_destinations_live_in_vendor(registry, admin, joker, vendor_partial, env):
    # each vendor owns its own allow-list; the Switchboard edits it directly on the vendor.
    d1 = env.generate_address("d1")
    d2 = env.generate_address("d2")
    service2 = vendor_partial.at(registry.createVendor("service2.com", sender=admin))
    joker.addDestination(d1, sender=admin)
    joker.addDestination(d2, sender=admin)
    service2.addDestination(d1, sender=admin)  # same dest, independent per-vendor list
    assert joker.isAllowed(d1) is True
    assert _dests(joker) == [_a(d1), _a(d2)]
    assert _dests(service2) == [_a(d1)]
    joker.addDestination(d1, sender=admin)     # idempotent — no duplicate
    assert _dests(joker) == [_a(d1), _a(d2)]
    # remove d1 from joker: swap-removed there, service2 untouched (self-contained)
    joker.removeDestination(d1, sender=admin)
    assert joker.isAllowed(d1) is False
    assert _dests(joker) == [_a(d2)]
    assert _dests(service2) == [_a(d1)]


def test_add_destination_perms(joker, alice, env):
    with boa.reverts("not switchboard"):
        joker.addDestination(env.generate_address("d"), sender=alice)


def test_only_switchboard_can_edit_destinations(joker, admin, alice, env):
    # the vendor owns the data and lets the Switchboard edit it directly; everyone else is rejected
    d = env.generate_address("d")
    joker.addDestination(d, sender=admin)                # switchboard OK
    assert joker.isAllowed(d) is True
    with boa.reverts("not switchboard"):
        joker.addDestination(env.generate_address("d2"), sender=alice)
    with boa.reverts("not switchboard"):
        joker.removeDestination(d, sender=alice)


def test_remove_vendor_perms(registry, joker, alice):
    with boa.reverts("no perms"):
        registry.removeVendor(joker.address, sender=alice)


def test_remove_vendor_requires_vendor(registry, admin, env):
    with boa.reverts("not a vendor"):
        registry.removeVendor(env.generate_address("fake"), sender=admin)


# ═══════════════════════════ VendorProxy: recover funds + pull payment ═══════════════════════════

def test_recover_funds_switchboard_only(joker, usdc, admin, deploy3r, alice, bob):
    usdc.mint(joker.address, 100, sender=deploy3r)
    with boa.reverts("not switchboard"):
        joker.recoverFunds(alice, usdc.address, sender=bob)
    joker.recoverFunds(alice, usdc.address, sender=admin)  # switchboard sweeps stray funds
    assert usdc.balanceOf(alice) == 100
    assert usdc.balanceOf(joker.address) == 0


def test_vendor_pull_payment_only_processor(joker, alice, bob, usdc):
    with boa.reverts("only processor"):
        joker.pullPayment(alice, usdc.address, 100, False, sender=bob)


def test_vendor_pull_payment_routes_billing(processor, joker, mock_billing, usdc, alice):
    # only the PayProcessor may drive the pull; `_isCheque` routes cheque vs payee in Billing
    joker.pullPayment(alice, usdc.address, 100, True, sender=processor.address)
    assert mock_billing.lastWasCheque() is True
    assert _a(mock_billing.lastUserWallet()) == _a(alice)
    assert mock_billing.lastAmount() == 100
    joker.pullPayment(alice, usdc.address, 50, False, sender=processor.address)
    assert mock_billing.lastWasCheque() is False
    assert mock_billing.lastAmount() == 50


# ═══════════════════════════ PayProcessor: register (MPP rail) ═══════════════════════════

def test_register_mpp_pulls_and_escrows(processor, joker, usdc, admin, deploy3r, alice, bob, agent_wrapper, env):
    dest = env.generate_address("merchant")
    processor.setSender(bob, True, sender=admin)
    joker.addDestination(dest, sender=admin)
    usdc.mint(joker.address, 100, sender=deploy3r)       # sender already pushed funds into the vendor
    ret = processor.register(RAIL_MPP, agent_wrapper, joker.address, alice, 100, dest, PAY1, REF, b"", sender=bob)
    assert bytes(ret) == EMPTY32                          # MPP returns empty
    logs = _logs(processor, "OperationRegistered")
    assert usdc.balanceOf(processor.address) == 100
    assert usdc.balanceOf(joker.address) == 0
    op = processor.operations(PAY1)
    assert _a(op[0]) == _a(alice) and _a(op[1]) == _a(joker.address) and _a(op[2]) == _a(agent_wrapper)
    assert op[3] == 100 and op[6] is True                # agentWrapper recorded at [2]; amount [3]; exists [6]
    assert _a(op[9]) == _a(dest)                          # dest recorded on the op ([9])
    assert processor.pendingTotal() == 100
    assert logs[0].amount == 100 and logs[0].rail == 1
    assert _a(logs[0].agentWrapper) == _a(agent_wrapper)  # initiating wrapper emitted for audit


def test_register_mpp_gates_dest(processor, joker, usdc, admin, deploy3r, alice, bob, agent_wrapper, env):
    # MPP now takes + validates a dest against the vendor allow-list, like x402
    dest = env.generate_address("merchant")
    processor.setSender(bob, True, sender=admin)
    usdc.mint(joker.address, 100, sender=deploy3r)
    with boa.reverts("dest not allowed"):
        processor.register(RAIL_MPP, agent_wrapper, joker.address, alice, 100, dest, PAY1, REF, b"", sender=bob)
    joker.addDestination(dest, sender=admin)
    processor.register(RAIL_MPP, agent_wrapper, joker.address, alice, 100, dest, PAY1, REF, b"", sender=bob)
    assert processor.pendingTotal() == 100


def test_register_sender_gated(processor, joker, alice, bob, agent_wrapper, env):
    with boa.reverts("not a sender"):
        processor.register(RAIL_MPP, agent_wrapper, joker.address, alice, 100, env.generate_address("d"), PAY1, REF, b"", sender=bob)


def test_register_rejects_unknown_vendor(processor, admin, alice, bob, env, agent_wrapper):
    # a non-vendor is not registered in the VendorRegistry, so settlement refuses it
    processor.setSender(bob, True, sender=admin)
    with boa.reverts("not a vendor"):
        processor.register(RAIL_MPP, agent_wrapper, env.generate_address("fake"), alice, 100, env.generate_address("d"), PAY1, REF, b"", sender=bob)


def test_register_rejects_empty_agent_wrapper(processor, joker, admin, alice, bob, env):
    # the initiating wrapper is audit-only, but must be present so the trail can't be polluted with a zero
    processor.setSender(bob, True, sender=admin)
    with boa.reverts("no agent wrapper"):
        processor.register(RAIL_MPP, ZERO_ADDRESS, joker.address, alice, 100, env.generate_address("d"), PAY1, REF, b"", sender=bob)


def test_register_rejects_bad_protocol(processor, joker, usdc, admin, deploy3r, alice, bob, env, agent_wrapper):
    dest = env.generate_address("merchant")
    processor.setSender(bob, True, sender=admin)
    joker.addDestination(dest, sender=admin)
    usdc.mint(joker.address, 100, sender=deploy3r)
    with boa.reverts("bad protocol"):
        processor.register(3, agent_wrapper, joker.address, alice, 100, dest, PAY1, REF, b"", sender=bob)


def test_removed_vendor_blocks_both_rails(processor, registry, joker, usdc, admin, deploy3r, alice, bob, env, agent_wrapper):
    dest = env.generate_address("payto")
    processor.setSender(bob, True, sender=admin)
    joker.addDestination(dest, sender=admin)
    usdc.mint(joker.address, 100, sender=deploy3r)
    registry.removeVendor(joker.address, sender=admin)               # remove — takes it out of the index
    assert registry.isVendor(joker.address) is False
    with boa.reverts("not a vendor"):
        processor.register(RAIL_MPP, agent_wrapper, joker.address, alice, 100, dest, PAY1, REF, b"", sender=bob)
    with boa.reverts("not a vendor"):
        processor.register(RAIL_X402, agent_wrapper, joker.address, alice, 100, dest, PAY1, REF, _x402_extra(0, FAR_FUTURE), sender=bob)


# ═══════════════════════════ PayProcessor: register (x402 rail) ═══════════════════════════

def test_register_x402_binds_digest_and_gates_dest(processor, registry, joker, usdc, admin, deploy3r, alice, bob, env, agent_wrapper):
    dest = env.generate_address("joker_payto")
    extra = _x402_extra(0, FAR_FUTURE)
    processor.setSender(bob, True, sender=admin)
    usdc.mint(joker.address, 100, sender=deploy3r)
    # dest not yet allow-listed -> reverts
    with boa.reverts("dest not allowed"):
        processor.register(RAIL_X402, agent_wrapper, joker.address, alice, 100, dest, PAY1, REF, extra, sender=bob)
    # allow-list it, then it binds the EIP-3009 digest and the processor honors it via EIP-1271
    joker.addDestination(dest, sender=admin)
    digest = processor.register(RAIL_X402, agent_wrapper, joker.address, alice, 100, dest, PAY1, REF, extra, sender=bob)
    assert bytes(digest) == bytes(processor.getX402Digest(dest, 100, 0, FAR_FUTURE, PAY1))  # nonce derived from paymentId
    assert bytes(processor.isValidSignature(digest, b"")) == MAGIC
    assert bytes(processor.isValidSignature(PAY2, b"")) == FAIL   # unbound digest


def _register_x402(processor, registry, joker, usdc, admin, deploy3r, alice, bob, dest, agent_wrapper, amount=100, pid=PAY1):
    processor.setSender(bob, True, sender=admin)
    joker.addDestination(dest, sender=admin)
    usdc.mint(joker.address, amount, sender=deploy3r)
    return processor.register(RAIL_X402, agent_wrapper, joker.address, alice, amount, dest, pid, REF, _x402_extra(0, FAR_FUTURE), sender=bob)


def test_refund_x402_before_pull_revokes_and_refunds(processor, registry, joker, usdc, admin, deploy3r, alice, bob, env, agent_wrapper):
    dest = env.generate_address("payto")
    digest = _register_x402(processor, registry, joker, usdc, admin, deploy3r, alice, bob, dest, agent_wrapper)
    # merchant has NOT pulled -> refund revokes the authorization and returns the funds to the payer
    processor.refund(PAY1, 100, sender=admin)
    assert usdc.balanceOf(alice) == 100
    assert bytes(processor.isValidSignature(digest, b"")) == FAIL   # revoked — can't be pulled after
    assert processor.operations(PAY1)[4] == 100                     # refunded at [4] (agentWrapper recorded at [2])


def test_refund_x402_after_pull_reverts(processor, registry, joker, usdc, admin, deploy3r, alice, bob, env, agent_wrapper):
    dest = env.generate_address("payto")
    _register_x402(processor, registry, joker, usdc, admin, deploy3r, alice, bob, dest, agent_wrapper)
    # simulate the merchant pulling via transferWithAuthorization -> the EIP-3009 nonce is consumed
    usdc.setAuthUsed(processor.address, processor.x402Nonce(PAY1), True)
    with boa.reverts("already settled"):
        processor.refund(PAY1, 100, sender=admin)


# ═══════════════════════════ PayProcessor: settle / bridge (MPP) + refund ═══════════════════════════

def test_settle_moves_to_avail_to_bridge(processor, joker, usdc, admin, deploy3r, alice, bob, agent_wrapper, env):
    dest = env.generate_address("merchant")
    processor.setSender(bob, True, sender=admin)
    joker.addDestination(dest, sender=admin)
    usdc.mint(joker.address, 100, sender=deploy3r)
    processor.register(RAIL_MPP, agent_wrapper, joker.address, alice, 100, dest, PAY1, REF, b"", sender=bob)
    assert processor.pendingTotal() == 100 and processor.availToBridge() == 0
    # settle moves the balance escrow -> availToBridge; no USDC leaves the processor yet
    processor.settle(PAY1, sender=admin)
    assert processor.pendingTotal() == 0
    assert processor.availToBridge() == 100
    assert usdc.balanceOf(processor.address) == 100      # funds stay until bridge()
    assert processor.operations(PAY1)[7] is True         # settled flag at [7]
    # settled -> no longer refundable, and can't be settled twice
    with boa.reverts("already settled"):
        processor.refund(PAY1, 100, sender=admin)
    with boa.reverts("already settled"):
        processor.settle(PAY1, sender=admin)


def test_mpp_refund_then_settle_remainder(processor, joker, usdc, admin, deploy3r, alice, bob, agent_wrapper, env):
    dest = env.generate_address("merchant")
    processor.setSender(bob, True, sender=admin)
    joker.addDestination(dest, sender=admin)
    usdc.mint(joker.address, 100, sender=deploy3r)
    processor.register(RAIL_MPP, agent_wrapper, joker.address, alice, 100, dest, PAY1, REF, b"", sender=bob)
    # before settlement the payer can be refunded (partial ok)
    processor.refund(PAY1, 25, sender=admin)
    assert usdc.balanceOf(alice) == 25
    assert processor.operations(PAY1)[4] == 25           # refunded at [4]
    assert processor.pendingTotal() == 75
    # settle the remainder -> 75 moves into availToBridge, op final
    processor.settle(PAY1, sender=admin)
    assert processor.availToBridge() == 75
    assert processor.pendingTotal() == 0
    assert processor.operations(PAY1)[7] is True
    with boa.reverts("already settled"):
        processor.refund(PAY1, 10, sender=admin)


def test_settle_gated_and_mpp_only(processor, joker, usdc, admin, deploy3r, alice, bob, agent_wrapper, env):
    dest = env.generate_address("merchant")
    processor.setSender(bob, True, sender=admin)
    joker.addDestination(dest, sender=admin)
    # an x402 op cannot be settled here (it settles via the facilitator's EIP-3009 pull)
    usdc.mint(joker.address, 100, sender=deploy3r)
    processor.register(RAIL_X402, agent_wrapper, joker.address, alice, 100, dest, PAY1, REF, _x402_extra(0, FAR_FUTURE), sender=bob)
    with boa.reverts("not mpp op"):
        processor.settle(PAY1, sender=admin)
    # and only switchboard may settle
    usdc.mint(joker.address, 100, sender=deploy3r)
    processor.register(RAIL_MPP, agent_wrapper, joker.address, alice, 100, dest, PAY2, REF, b"", sender=bob)
    with boa.reverts("not switchboard"):
        processor.settle(PAY2, sender=alice)


def test_bridge_batches_avail_to_bridge(processor, joker, usdc, admin, deploy3r, alice, bob, bridge_address, agent_wrapper, env):
    dest = env.generate_address("merchant")
    processor.setSender(bob, True, sender=admin)
    processor.setBridge(bridge_address, sender=admin)    # only switchboard sets the destination
    joker.addDestination(dest, sender=admin)
    # settle two ops into availToBridge, then bridge the accumulated batch in one transfer
    usdc.mint(joker.address, 100, sender=deploy3r)
    processor.register(RAIL_MPP, agent_wrapper, joker.address, alice, 100, dest, PAY1, REF, b"", sender=bob)
    usdc.mint(joker.address, 100, sender=deploy3r)
    processor.register(RAIL_MPP, agent_wrapper, joker.address, alice, 100, dest, PAY2, REF, b"", sender=bob)
    processor.settle(PAY1, sender=admin)
    processor.settle(PAY2, sender=admin)
    assert processor.availToBridge() == 200
    assert usdc.balanceOf(processor.address) == 200      # nothing bridged yet
    processor.bridge(200, sender=admin)                    # switchboard clears the batch (>= Bridge min, off-chain)
    assert usdc.balanceOf(bridge_address) == 200
    assert usdc.balanceOf(processor.address) == 0
    assert processor.availToBridge() == 0
    with boa.reverts("amount over avail"):
        processor.bridge(1, sender=admin)                  # nothing left to bridge
    with boa.reverts("not switchboard"):
        processor.bridge(1, sender=alice)


def test_bridge_requires_config(processor, admin):
    with boa.reverts("bridge not configured"):
        processor.bridge(1, sender=admin)                  # no Bridge address set


def test_only_switchboard_sets_the_bridge_address(processor, admin, bob, alice, bridge_address):
    # only the Switchboard defines where the funds land — no other caller can setBridge
    processor.setBridge(bridge_address, sender=admin)
    assert _a(processor.bridgeAddress()) == _a(bridge_address)
    with boa.reverts("no perms"):
        processor.setBridge(bob, sender=bob)             # non-switchboard can't redirect
    with boa.reverts("no perms"):
        processor.setBridge(alice, sender=alice)


# ═══════════════════════════ AgentSenderPay: unified pay() orchestration ═══════════════════════════

@pytest.fixture
def test_signer():
    return Account.from_key("0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")


@pytest.fixture
def mock_wrapper(usdc, deploy3r):
    w = boa.load("contracts/mock/MockMppAgentWrapper.vy", usdc.address)
    usdc.mint(w.address, 1_000_000, sender=deploy3r)
    return w


@pytest.fixture
def sender(mock_hq, usdc, test_signer, processor, admin, fork):
    from config.BluePrint import PARAMS
    s = boa.load(
        "contracts/core/agent/AgentSenderPay.vy",
        mock_hq.address, usdc.address, test_signer.address,
        PARAMS[fork]["GEN_MIN_CONFIG_TIMELOCK"], PARAMS[fork]["GEN_MAX_CONFIG_TIMELOCK"],
    )
    processor.setSender(s.address, True, sender=admin)
    return s


def _sign_pay(sender, test_signer, protocol_id, wrapper, wallet, vendor, amount, dest, pid, ref, is_cheque=False, extra=b""):
    digest, nonce, exp = sender.getPayHash(protocol_id, wrapper, wallet, vendor, amount, dest, pid, ref, is_cheque, extra, FAR_FUTURE)
    return (test_signer.unsafe_sign_hash(digest).signature, nonce, exp)


def test_pay_mpp_end_to_end(sender, mock_wrapper, joker, processor, usdc, test_signer, admin, alice, bob, env):
    dest = env.generate_address("merchant")
    joker.addDestination(dest, sender=admin)
    sig = _sign_pay(sender, test_signer, RAIL_MPP, mock_wrapper.address, alice, joker.address, 100, dest, PAY1, REF)
    # any broadcaster submits; owner (test_signer) signature authorizes
    sender.pay(RAIL_MPP, mock_wrapper.address, alice, joker.address, 100, dest, PAY1, REF, False, b"", NO_VAULT, sig, sender=bob)
    # funds flowed UW(mock) -> vendor -> processor; op recorded
    assert usdc.balanceOf(processor.address) == 100
    assert usdc.balanceOf(joker.address) == 0
    assert processor.operations(PAY1)[3] == 100                          # amount at [3] (agentWrapper recorded at [2])
    assert _a(processor.operations(PAY1)[2]) == _a(mock_wrapper.address)  # AgentSenderPay threads the wrapper through
    assert sender.currentNonce(alice) == 1
    assert mock_wrapper.lastWasCheque() is False                         # direct Payee transfer, not a cheque


def test_pay_x402_end_to_end(sender, mock_wrapper, joker, processor, usdc, test_signer, admin, alice, bob, env):
    dest = env.generate_address("merchant")
    joker.addDestination(dest, sender=admin)
    extra = _x402_extra(0, FAR_FUTURE)
    sig = _sign_pay(sender, test_signer, RAIL_X402, mock_wrapper.address, alice, joker.address, 100, dest, PAY1, REF, extra=extra)
    digest = sender.pay(RAIL_X402, mock_wrapper.address, alice, joker.address, 100, dest, PAY1, REF, False, extra, NO_VAULT, sig, sender=bob)
    # x402 returns the bound digest, which the processor honors via EIP-1271
    assert bytes(digest) == bytes(processor.getX402Digest(dest, 100, 0, FAR_FUTURE, PAY1))
    assert bytes(processor.isValidSignature(digest, b"")) == MAGIC


def test_pay_cheque_routes_create_and_pay(sender, mock_wrapper, joker, processor, test_signer, admin, alice, bob, env):
    dest = env.generate_address("merchant")
    joker.addDestination(dest, sender=admin)
    sig = _sign_pay(sender, test_signer, RAIL_MPP, mock_wrapper.address, alice, joker.address, 100, dest, PAY1, REF, is_cheque=True)
    sender.pay(RAIL_MPP, mock_wrapper.address, alice, joker.address, 100, dest, PAY1, REF, True, b"", NO_VAULT, sig, sender=bob)
    assert mock_wrapper.lastWasCheque() is True          # one-off: routed through createAndPayCheque
    assert processor.operations(PAY1)[3] == 100


def test_pay_wrong_signer_reverts(sender, mock_wrapper, joker, admin, alice, bob, env):
    dest = env.generate_address("merchant")
    joker.addDestination(dest, sender=admin)
    wrong = Account.from_key("0x" + "11" * 32)
    digest, nonce, exp = sender.getPayHash(RAIL_MPP, mock_wrapper.address, alice, joker.address, 100, dest, PAY1, REF, False, b"", FAR_FUTURE)
    bad = (wrong.unsafe_sign_hash(digest).signature, nonce, exp)
    with boa.reverts("invalid signer"):
        sender.pay(RAIL_MPP, mock_wrapper.address, alice, joker.address, 100, dest, PAY1, REF, False, b"", NO_VAULT, bad, sender=bob)


def test_pay_replay_reverts(sender, mock_wrapper, joker, test_signer, admin, alice, bob, env):
    dest = env.generate_address("merchant")
    joker.addDestination(dest, sender=admin)
    sig = _sign_pay(sender, test_signer, RAIL_MPP, mock_wrapper.address, alice, joker.address, 100, dest, PAY1, REF)
    sender.pay(RAIL_MPP, mock_wrapper.address, alice, joker.address, 100, dest, PAY1, REF, False, b"", NO_VAULT, sig, sender=bob)
    with boa.reverts("invalid nonce"):
        sender.pay(RAIL_MPP, mock_wrapper.address, alice, joker.address, 100, dest, PAY2, REF, False, b"", NO_VAULT, sig, sender=bob)


# ═══════════════════════════ Leto: Vendor* list-idiom edge cases + untested branches ═══════════════════════════
# Coverage gaps found during the PR #76 audit (VendorRegistry / VendorProxy). The swap-remove idiom has a
# self-referential write when the removed element is the LAST slot (indexOf[last]=target then indexOf[removed]=0
# on the same address) — these lock in that ordering, plus branches the original 31-case suite never exercised.

def test_registry_remove_middle_vendor_swaps_last_into_slot(registry, admin, vendor_partial):
    # 3 vendors, remove the MIDDLE one: the last row must swap into the freed slot and keep a valid index,
    # or PayProcessor.register (which gates on indexOfVendor != 0) would wrongly reject the swapped vendor.
    a = vendor_partial.at(registry.createVendor("a.com", sender=admin))   # regId 1
    b = vendor_partial.at(registry.createVendor("b.com", sender=admin))   # regId 2
    c = vendor_partial.at(registry.createVendor("c.com", sender=admin))   # regId 3
    assert registry.getNumVendors() == 3
    registry.removeVendor(b.address, sender=admin)
    # b is gone
    assert registry.isVendor(b.address) is False and registry.indexOfVendor(b.address) == 0
    # c (was last) swapped into slot 2 and is still live at the RIGHT index
    assert registry.indexOfVendor(c.address) == 2
    assert _a(registry.vendors(2)[0]) == _a(c.address)
    assert registry.isVendor(c.address) is True
    # a untouched, tail slot cleared, count decremented
    assert registry.indexOfVendor(a.address) == 1 and registry.isVendor(a.address) is True
    assert _a(registry.vendors(3)[0]) == _a(ZERO_ADDRESS)
    assert registry.getNumVendors() == 2


def test_registry_remove_last_index_vendor_self_swap(registry, admin, vendor_partial):
    # removing the vendor that occupies the LAST slot hits the self-referential write path; the record
    # must end at index 0 (not 1), else a removed vendor would still pass the settlement gate.
    a = vendor_partial.at(registry.createVendor("a.com", sender=admin))   # regId 1
    b = vendor_partial.at(registry.createVendor("b.com", sender=admin))   # regId 2 (last)
    registry.removeVendor(b.address, sender=admin)
    assert registry.indexOfVendor(b.address) == 0 and registry.isVendor(b.address) is False
    assert _a(registry.vendors(2)[0]) == _a(ZERO_ADDRESS)
    assert registry.getNumVendors() == 1 and registry.isVendor(a.address) is True
    # re-create reuses the freed slot with a fresh index — no collision with the live vendor
    d = vendor_partial.at(registry.createVendor("d.com", sender=admin))
    assert registry.indexOfVendor(d.address) == 2 and registry.getNumVendors() == 2


def test_vendor_remove_last_destination_self_swap_and_reempty(joker, admin, env):
    # dest allow-list uses the same swap-remove idiom: removing the LAST dest (targetIndex == lastIndex)
    # must clear indexOfDest AND isAllowed; emptying then re-adding must yield a fresh 1-based index.
    d1 = env.generate_address("d1")
    d2 = env.generate_address("d2")
    joker.addDestination(d1, sender=admin)   # idx 1
    joker.addDestination(d2, sender=admin)   # idx 2 (last)
    joker.removeDestination(d2, sender=admin)
    assert joker.isAllowed(d2) is False and joker.indexOfDest(d2) == 0
    assert _dests(joker) == [_a(d1)]
    assert joker.isAllowed(d1) is True and joker.indexOfDest(d1) == 1
    # remove the final dest -> empty
    joker.removeDestination(d1, sender=admin)
    assert joker.isAllowed(d1) is False and joker.indexOfDest(d1) == 0
    assert _dests(joker) == [] and joker.numDests() == 1
    # re-add after emptying: fresh index, allow-list flag restored
    joker.addDestination(d1, sender=admin)
    assert joker.indexOfDest(d1) == 1 and joker.isAllowed(d1) is True


def test_vendor_transfer_to_processor_only_processor(joker, usdc, deploy3r, bob):
    # the funds-out path is processor-only; a stranger cannot drain a vendor's transient balance
    usdc.mint(joker.address, 100, sender=deploy3r)
    with boa.reverts("only processor"):
        joker.transferToProcessor(usdc.address, 100, sender=bob)


def test_vendor_transfer_to_processor_full_balance_default(processor, joker, usdc, deploy3r):
    # the default _amount = max_value branch sweeps the whole balance (register always passes an explicit
    # amount, so this branch was never exercised by the original suite)
    usdc.mint(joker.address, 250, sender=deploy3r)
    moved = joker.transferToProcessor(usdc.address, sender=processor.address)
    assert moved == 250
    assert usdc.balanceOf(joker.address) == 0 and usdc.balanceOf(processor.address) == 250


def test_vendor_recover_many_and_nothing_to_recover(joker, usdc, admin, deploy3r, alice):
    # recoverFundsMany + the "nothing to recover" guard (both untested in the original suite)
    with boa.reverts("nothing to recover"):
        joker.recoverFunds(alice, usdc.address, sender=admin)
    usdc.mint(joker.address, 100, sender=deploy3r)
    joker.recoverFundsMany(alice, [usdc.address], sender=admin)
    assert usdc.balanceOf(alice) == 100 and usdc.balanceOf(joker.address) == 0


def test_registry_create_requires_template(mock_hq, admin):
    # a registry with no vendor template cannot mint vendors
    s = boa.load("contracts/core/payments/VendorRegistry.vy", mock_hq.address, ZERO_ADDRESS)
    with boa.reverts("no template"):
        s.createVendor("x.com", sender=admin)


def test_registry_set_template_switchboard_only(registry, admin, alice, vendor_partial):
    t2 = vendor_partial.deploy_as_blueprint()
    with boa.reverts("no perms"):
        registry.setVendorTemplate(t2.address, sender=alice)
    registry.setVendorTemplate(t2.address, sender=admin)
    assert _a(registry.vendorTemplate()) == _a(t2.address)
# ═══════════════════════════ SwitchboardDelta: payments config + ops gateway ═══════════════════════════

@pytest.fixture
def mock_mc(mock_hq):
    mc = boa.load("contracts/mock/MockMissionControl.vy")
    mock_hq.setAddr(2, mc.address)      # MISSION_CONTROL_ID
    return mc


@pytest.fixture
def delta(mock_hq, registry, processor, mock_mc, admin, env, fork):
    from config.BluePrint import PARAMS
    mock_hq.setGov(env.generate_address("hq_gov"))   # LocalGov needs an hq gov, distinct from the local gov (admin)
    d = boa.load(
        "contracts/config/SwitchboardDelta.vy",
        mock_hq.address, admin,          # tempGov = admin (local governor)
        PARAMS[fork]["GEN_MIN_CONFIG_TIMELOCK"], PARAMS[fork]["GEN_MAX_CONFIG_TIMELOCK"],
    )
    mock_hq.setSwitcher(d.address, True)  # Delta is a switchboard address -> the departments accept its calls
    return d


def test_delta_operate_gating(delta, registry, mock_mc, admin, alice, bob):
    # a random address can't run operate actions
    with boa.reverts("no perms"):
        delta.createVendor("nope.com", sender=alice)
    # a MissionControl security signer can
    mock_mc.setSecuritySigner(bob, True)
    addr = delta.createVendor("via-signer.com", sender=bob)
    assert registry.isVendor(addr) is True
    # governance is a superuser too
    addr2 = delta.createVendor("via-gov.com", sender=admin)
    assert registry.isVendor(addr2) is True


def test_delta_operate_routes_to_payprocessor(delta, mock_mc, alice, bob):
    mock_mc.setSecuritySigner(bob, True)
    # settle routes Delta -> PayProcessor; an unknown op reverts with PayProcessor's error (the call landed)
    with boa.reverts("unknown paymentId"):
        delta.settle(PAY1, sender=bob)
    # Delta gates a non-authorized caller before it ever reaches PayProcessor
    with boa.reverts("no perms"):
        delta.settle(PAY1, sender=alice)


def test_delta_config_setSender_timelocked(delta, processor, admin, alice, bob):
    delta.setActionTimeLockAfterSetup(0, sender=admin)   # config timelock = minimum
    # only governance may initiate config
    with boa.reverts("no perms"):
        delta.setSender(bob, True, sender=alice)
    aid = delta.setSender(bob, True, sender=admin)
    # not executable before the timelock elapses
    assert delta.executePendingAction(aid, sender=admin) is False
    assert processor.senders(bob) is False
    boa.env.time_travel(blocks=delta.actionTimeLock())
    assert delta.executePendingAction(aid, sender=admin) is True
    assert processor.senders(bob) is True                 # Delta set it on PayProcessor


def test_delta_pause_immediate_unpause_timelocked(delta, registry, processor, mock_mc, admin, alice, bob):
    delta.setActionTimeLockAfterSetup(0, sender=admin)
    mock_mc.setSecuritySigner(bob, True)
    # disable is immediate (a security signer) and freezes both departments
    delta.setPaused(True, sender=bob)
    assert processor.isPaused() is True and registry.isPaused() is True
    with boa.reverts("paused"):
        delta.createVendor("frozen.com", sender=bob)
    with boa.reverts("no perms"):
        delta.setPaused(True, sender=alice)               # random addr can't pause
    with boa.reverts("no perms"):
        delta.setPaused(False, sender=bob)                # a security signer can't unpause (governance only)
    # enable (unpause) is governance + timelock
    aid = delta.setPaused(False, sender=admin)
    assert delta.executePendingAction(aid, sender=admin) is False
    assert processor.isPaused() is True                   # still paused before the timelock
    boa.env.time_travel(blocks=delta.actionTimeLock())
    assert delta.executePendingAction(aid, sender=admin) is True
    assert processor.isPaused() is False and registry.isPaused() is False
    delta.createVendor("thawed.com", sender=bob)          # works again
