"""
x402 EIP-3009 / EIP-712 / EIP-1271 digest-parity checks (Toro).

Why this file exists
--------------------
The PayProcessor is the EIP-1271 payer for the x402 `exact` scheme. At
`register()` it pre-computes the EIP-3009 `TransferWithAuthorization` digest and
stores `authorized[digest] = True`; later, real USDC (FiatTokenV2) recomputes
that SAME digest from the on-chain transfer params and calls
`isValidSignature(digest, sig)` — the processor returns MAGIC iff it authorized
that exact digest.

The whole rail therefore hinges on ONE invariant: the digest the processor
computes must byte-for-byte equal the digest real USDC computes. The existing
suite never checks this — `MockUsdc` has no `transferWithAuthorization`, so
`isValidSignature` is only ever asked about a digest the processor itself made
(circular). A wrong EIP-712 domain (name/version), a wrong typehash, or a
wrong field order would ship silently and x402 would NEVER settle on mainnet.

These tests reconstruct the digest from the raw EIP-712 spec in Python (the
same math FiatTokenV2 runs) and assert equality with the contract, pinning the
encoding so any future drift fails CI.
"""

import boa
import pytest
from eth_abi import encode
from eth_utils import keccak

from constants import ZERO_ADDRESS

EMPTY32 = b"\x00" * 32
FAR_FUTURE = 9_999_999_999
PAY1 = (1).to_bytes(32, "big")
REF = keccak(text="challenge:joker")
MAGIC = bytes.fromhex("1626ba7e")
FAIL = bytes.fromhex("ffffffff")
RAIL_X402 = 2

# --- canonical EIP-712 / EIP-3009 constants (independent of the contract) ---
DOMAIN_TYPEHASH = keccak(
    text="EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
)
TWA_TYPEHASH = keccak(
    text="TransferWithAuthorization(address from,address to,uint256 value,uint256 validAfter,uint256 validBefore,bytes32 nonce)"
)
NAME_HASH = keccak(text="USD Coin")   # native USDC on Base: name() == "USD Coin"
VERSION_HASH = keccak(text="2")       # FiatTokenV2_2 hardcodes EIP-712 version "2"


def _a(x):
    return str(x).lower()


def _x402_extra(valid_after, valid_before):
    return valid_after.to_bytes(32, "big") + valid_before.to_bytes(32, "big")


def _domain_separator(usdc_addr, chain_id):
    return keccak(
        encode(
            ["bytes32", "bytes32", "bytes32", "uint256", "address"],
            [DOMAIN_TYPEHASH, NAME_HASH, VERSION_HASH, chain_id, usdc_addr],
        )
    )


def _expected_digest(processor_addr, to, value, valid_after, valid_before, nonce, usdc_addr, chain_id):
    """The digest real USDC (FiatTokenV2) computes for a transferWithAuthorization
    where from == processor_addr. This is the reference implementation the
    contract's `_x402Digest` must match exactly."""
    struct_hash = keccak(
        encode(
            ["bytes32", "address", "address", "uint256", "uint256", "uint256", "bytes32"],
            [TWA_TYPEHASH, processor_addr, to, value, valid_after, valid_before, nonce],
        )
    )
    return keccak(b"\x19\x01" + _domain_separator(usdc_addr, chain_id) + struct_hash)


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
    p = boa.load("contracts/core/payments/PayProcessor.vy", mock_hq.address, usdc.address)
    mock_hq.setAddr(13, p.address)
    return p


@pytest.fixture
def joker(registry, admin, vendor_partial):
    return vendor_partial.at(registry.createVendor("x402joker.com", sender=admin))


@pytest.fixture
def agent_wrapper(env):
    return env.generate_address("agent_wrapper")


@pytest.fixture
def chain_id():
    return boa.env.evm.patch.chain_id


# ═══════════════════════════════════════════════════════════════════════════
# 1. nonce derivation: EIP-3009 nonce == keccak256(paymentId)
# ═══════════════════════════════════════════════════════════════════════════

def test_x402_nonce_is_keccak_of_payment_id(processor):
    assert bytes(processor.x402Nonce(PAY1)) == keccak(PAY1)


# ═══════════════════════════════════════════════════════════════════════════
# 2. digest parity: the contract's getX402Digest == the raw EIP-712 spec digest
#    that real USDC would compute. If domain name/version, typehash, or field
#    order ever drift, this fails.
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize(
    "value,valid_after,valid_before",
    [
        (100, 0, FAR_FUTURE),
        (1, 0, FAR_FUTURE),
        (2**256 - 1, 123, 456),         # extreme value + tight window
        (10**12, 1_700_000_000, 1_900_000_000),
    ],
)
def test_getX402Digest_matches_eip712_reference(processor, usdc, env, chain_id, value, valid_after, valid_before):
    dest = env.generate_address("merchant")
    nonce = keccak(PAY1)
    expected = _expected_digest(
        processor.address, dest, value, valid_after, valid_before, nonce, usdc.address, chain_id
    )
    got = bytes(processor.getX402Digest(dest, value, valid_after, valid_before, PAY1))
    assert got == expected, "PayProcessor EIP-712 digest diverges from the EIP-3009 spec"


# ═══════════════════════════════════════════════════════════════════════════
# 3. end-to-end: register() binds exactly the spec digest and honors it via 1271
# ═══════════════════════════════════════════════════════════════════════════

def test_register_binds_spec_digest_and_honors_via_1271(processor, joker, usdc, admin, deploy3r, alice, bob, env, chain_id, agent_wrapper):
    dest = env.generate_address("joker_payto")
    processor.setSender(bob, True, sender=admin)
    joker.addDestination(dest, sender=admin)
    usdc.mint(joker.address, 100, sender=deploy3r)

    bound = bytes(
        processor.register(RAIL_X402, agent_wrapper, joker.address, alice, 100, dest, PAY1, REF, _x402_extra(0, FAR_FUTURE), sender=bob)
    )
    expected = _expected_digest(
        processor.address, dest, 100, 0, FAR_FUTURE, keccak(PAY1), usdc.address, chain_id
    )
    assert bound == expected                                   # register bound the spec digest
    assert bytes(processor.isValidSignature(bound, b"")) == MAGIC
    # a one-bit-flipped digest (what a wrong-domain USDC would produce) is NOT honored
    flipped = bytes([bound[0] ^ 0x01]) + bound[1:]
    assert bytes(processor.isValidSignature(flipped, b"")) == FAIL


# ═══════════════════════════════════════════════════════════════════════════
# 4. domain assumption is explicit: the mock (and mainnet) USDC name/version
#    must be exactly "USD Coin" / "2" or the whole rail is dead. This documents
#    the deploy-time requirement the contract hardcodes.
# ═══════════════════════════════════════════════════════════════════════════

def test_usdc_domain_name_matches_hardcoded_assumption(usdc):
    # If a deployment points PayProcessor at a USDC whose name() != "USD Coin"
    # (e.g. bridged USDbC == "USD Base Coin"), _NAME_HASH mismatches and x402
    # can never settle. This test pins the assumption the contract bakes in.
    assert usdc.name() == "USD Coin"
    assert keccak(text=usdc.name()) == NAME_HASH
