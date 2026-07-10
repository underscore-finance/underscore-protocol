"""
Regression tests (Moto) for the deploy-time / input guards T1 + T2.

T1: PayProcessor.__init__ asserts the USDC's DOMAIN_SEPARATOR() equals the EIP-712 domain it hardcodes,
    so pointing it at the wrong token (e.g. bridged USDbC == "USD Base Coin") fails the deploy loudly
    instead of silently shipping an x402 rail that can never settle.
T2: register() rejects an x402 window with validAfter >= validBefore (an op real USDC would always reject).
"""

import boa
import pytest
from eth_utils import keccak

FAR_FUTURE = 9_999_999_999
PAY1 = (1).to_bytes(32, "big")
REF = keccak(text="challenge:joker")
RAIL_X402 = 2


def _x402_extra(a, b):
    return a.to_bytes(32, "big") + b.to_bytes(32, "big")


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
    p = boa.load("contracts/core/payments/PayProcessor.vy", mock_hq.address, usdc.address)
    mock_hq.setAddr(13, p.address)
    return p


@pytest.fixture
def joker(registry, admin, vendor_partial):
    return vendor_partial.at(registry.createVendor("x402joker.com", sender=admin))


@pytest.fixture
def agent_wrapper(env):
    return env.generate_address("agent_wrapper")


# ─────────────────────────── T1: USDC domain must match at deploy ───────────────────────────

def test_deploy_ok_with_matching_usdc_domain(processor, usdc):
    # the standard fixture deploys against a matching-domain mock; deploy succeeds and binds USDC
    assert str(processor.USDC()).lower() == str(usdc.address).lower()


def test_deploy_reverts_on_usdc_domain_mismatch(mock_hq, usdc):
    # force the USDC to report a domain that doesn't match the processor's hardcoded one
    usdc.setDomainSeparator((0xDEAD).to_bytes(32, "big"))
    with boa.reverts("usdc domain mismatch"):
        boa.load("contracts/core/payments/PayProcessor.vy", mock_hq.address, usdc.address)


# ─────────────────────────── T2: x402 window must be validAfter < validBefore ───────────────────────────

def test_register_rejects_inverted_window(processor, joker, usdc, admin, deploy3r, alice, bob, agent_wrapper, env):
    dest = env.generate_address("merchant")
    processor.setSender(bob, True, sender=admin)
    joker.addDestination(dest, sender=admin)
    usdc.mint(joker.address, 100, sender=deploy3r)
    with boa.reverts("bad x402 window"):   # validAfter > validBefore
        processor.register(RAIL_X402, agent_wrapper, joker.address, alice, 100, dest, PAY1, REF, _x402_extra(FAR_FUTURE, 1), sender=bob)


def test_register_rejects_equal_window(processor, joker, usdc, admin, deploy3r, alice, bob, agent_wrapper, env):
    dest = env.generate_address("merchant")
    processor.setSender(bob, True, sender=admin)
    joker.addDestination(dest, sender=admin)
    usdc.mint(joker.address, 100, sender=deploy3r)
    with boa.reverts("bad x402 window"):   # validAfter == validBefore
        processor.register(RAIL_X402, agent_wrapper, joker.address, alice, 100, dest, PAY1, REF, _x402_extra(500, 500), sender=bob)
