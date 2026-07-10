"""
Regression tests for cross-rail refund/settle contamination.

Before the fix, PayProcessor inferred the rail from the *mutable* `opDigest[paymentId]`.
A partial x402 refund cleared `opDigest`, after which the op masqueraded as MPP:
settle() would sweep the remainder into availToBridge (payer loss) and a second
refund() would corrupt the MPP `pendingTotal` counter.

Fix: the rail is now an immutable `protocolId` on the Operation, and x402 refunds
must be all-or-nothing. These tests lock in the fixed behavior.
"""

import boa
import pytest
from eth_utils import keccak

from constants import ZERO_ADDRESS

EMPTY32 = b"\x00" * 32
FAR_FUTURE = 9_999_999_999
PAY1 = (1).to_bytes(32, "big")
PAY2 = (2).to_bytes(32, "big")
REF = keccak(text="challenge:joker")
FAIL = bytes.fromhex("ffffffff")
RAIL_MPP = 1
RAIL_X402 = 2


def _x402_extra(valid_after, valid_before):
    return valid_after.to_bytes(32, "big") + valid_before.to_bytes(32, "big")


# --- fixtures (module-scoped fixtures in test_payments.py don't cross files) ---

@pytest.fixture
def admin(env):
    return env.generate_address("payments_admin")


@pytest.fixture
def usdc():
    return boa.load("contracts/mock/MockUsdc.vy", "USD Coin", "USDC", 6)


@pytest.fixture
def mock_hq(admin):
    hq = boa.load("contracts/mock/MockPaymentsHq.vy")
    hq.setAddr(4, hq.address)
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
def processor(mock_hq, usdc):
    p = boa.load("contracts/core/payments/PayProcessor.vy", mock_hq.address, usdc.address, ZERO_ADDRESS, ZERO_ADDRESS)
    mock_hq.setAddr(13, p.address)
    return p


@pytest.fixture
def joker(registry, admin, vendor_partial):
    return vendor_partial.at(registry.createVendor("x402joker.com", sender=admin))


@pytest.fixture
def bridge_address(env):
    return env.generate_address("bridge_liquidation")


@pytest.fixture
def agent_wrapper(env):
    return env.generate_address("agent_wrapper")


def _register_x402(processor, joker, usdc, admin, deploy3r, alice, bob, dest, agent_wrapper, amount, pid):
    processor.setSender(bob, True, sender=admin)
    joker.addDestination(dest, sender=admin)
    usdc.mint(joker.address, amount, sender=deploy3r)
    return processor.register(RAIL_X402, agent_wrapper, joker.address, alice, amount, dest, pid, REF,
                              _x402_extra(0, FAR_FUTURE), sender=bob)


# ═══════════════════════════════════════════════════════════════════════════════
# A partial x402 refund is rejected; a full one revokes + refunds cleanly.
# ═══════════════════════════════════════════════════════════════════════════════

def test_x402_partial_refund_is_blocked(processor, joker, usdc, admin, deploy3r,
                                        alice, bob, agent_wrapper, env):
    dest = env.generate_address("joker_payto")
    digest = _register_x402(processor, joker, usdc, admin, deploy3r, alice, bob, dest, agent_wrapper, 100, PAY1)

    # partial x402 refund is now rejected outright — no half-bound op can exist
    with boa.reverts("x402 partial refund"):
        processor.refund(PAY1, 40, sender=admin)

    # opDigest is untouched by the rejected call; a full refund revokes + returns everything
    assert bytes(processor.opDigest(PAY1)) != EMPTY32
    processor.refund(PAY1, 100, sender=admin)
    assert usdc.balanceOf(alice) == 100
    assert bytes(processor.isValidSignature(digest, b"")) == FAIL
    assert processor.operations(PAY1)[4] == 100     # refunded [4]


# ═══════════════════════════════════════════════════════════════════════════════
# An x402 op is NEVER settleable/bridgeable — even after a full refund the
#      immutable protocolId keeps settle() locked out. (Old bug: a partial refund
#      let settle() sweep the remainder into availToBridge.)
# ═══════════════════════════════════════════════════════════════════════════════

def test_x402_op_never_settleable(processor, joker, usdc, admin, deploy3r,
                                  alice, bob, bridge_address, agent_wrapper, env):
    dest = env.generate_address("joker_payto")
    _register_x402(processor, joker, usdc, admin, deploy3r, alice, bob, dest, agent_wrapper, 100, PAY1)
    processor.setBridge(bridge_address, sender=admin)

    with boa.reverts("not mpp op"):
        processor.settle(PAY1, sender=admin)

    # full refund leaves protocolId immutable -> settle() still refuses it; nothing reaches the bridge pool
    processor.refund(PAY1, 100, sender=admin)
    with boa.reverts("not mpp op"):
        processor.settle(PAY1, sender=admin)
    assert processor.availToBridge() == 0


# ═══════════════════════════════════════════════════════════════════════════════
# F1c: x402 refunds never touch the MPP pendingTotal counter.
# ═══════════════════════════════════════════════════════════════════════════════

def test_x402_refund_does_not_corrupt_mpp_pending_total(processor, joker, usdc, admin, deploy3r,
                                                        alice, bob, agent_wrapper, env):
    dest = env.generate_address("payto")
    processor.setSender(bob, True, sender=admin)
    joker.addDestination(dest, sender=admin)

    # a live, independent MPP escrow of 100
    usdc.mint(joker.address, 100, sender=deploy3r)
    processor.register(RAIL_MPP, agent_wrapper, joker.address, alice, 100, dest, PAY2, REF, b"", sender=bob)
    assert processor.pendingTotal() == 100

    # an x402 op of 100, then a full refund of it
    usdc.mint(joker.address, 100, sender=deploy3r)
    processor.register(RAIL_X402, agent_wrapper, joker.address, alice, 100, dest, PAY1, REF,
                       _x402_extra(0, FAR_FUTURE), sender=bob)
    processor.refund(PAY1, 100, sender=admin)

    # the unrelated MPP escrow counter is untouched
    assert processor.pendingTotal() == 100
