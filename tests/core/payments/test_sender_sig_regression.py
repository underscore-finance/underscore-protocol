"""
Regression tests (Moto, for Gina's F2/F3/F4) — AgentSenderPay signing scheme.

F2 (HIGH): `_vault` must be covered by the owner signature — a broadcaster must not be able to
           inject/alter the yield withdrawal on a validly-signed payment.
F3 (MED):  owner-only `incrementNonce()` can revoke a leaked/stale payment signature.
F4 (LOW):  `_sourceAndSend` asserts `moved == _amount` (covered indirectly here; the canonical
           mock returns exactly `_amount`, so the end-to-end payments in test_payments.py exercise it).
Plus: a partial VaultSource is rejected.
"""

import boa
import pytest
from eth_account import Account
from eth_utils import keccak

from constants import ZERO_ADDRESS

EMPTY32 = b"\x00" * 32
NO_VAULT = (0, ZERO_ADDRESS, 0, EMPTY32)
FAR_FUTURE = 9_999_999_999
PAY1 = (1).to_bytes(32, "big")
REF = keccak(text="challenge:joker")
RAIL_MPP = 1


def _a(x):
    return str(x).lower()


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


def _sign(sender, test_signer, wrapper, wallet, vendor, amount, dest, pid, ref, is_cheque=False, extra=b"", vault=NO_VAULT):
    digest, nonce, exp = sender.getPayHash(RAIL_MPP, wrapper, wallet, vendor, amount, dest, pid, ref, is_cheque, extra, FAR_FUTURE, vault)
    return (test_signer.unsafe_sign_hash(digest).signature, nonce, exp)


# ═══════════════════════════ F2: the vault is part of the signed payload ═══════════════════════════

def test_vault_injection_fails_signature(sender, mock_wrapper, joker, test_signer, admin, alice, bob, env):
    # owner signs a payment with NO vault; a broadcaster tries to bolt on a yield withdrawal
    dest = env.generate_address("merchant")
    joker.addDestination(dest, sender=admin)
    sig = _sign(sender, test_signer, mock_wrapper.address, alice, joker.address, 100, dest, PAY1, REF)  # vault=NO_VAULT
    injected = (1, env.generate_address("victim_vault_token"), 2**256 - 1, EMPTY32)
    with boa.reverts("invalid signer"):
        sender.pay(RAIL_MPP, mock_wrapper.address, alice, joker.address, 100, dest, PAY1, REF, False, b"", injected, sig, sender=bob)


def test_signed_vault_is_accepted(sender, mock_wrapper, joker, processor, usdc, test_signer, admin, alice, bob, env):
    # the same vault that was signed goes through (proves the field is bound, not banned)
    dest = env.generate_address("merchant")
    joker.addDestination(dest, sender=admin)
    vault = (1, env.generate_address("vault_token"), 50, EMPTY32)
    sig = _sign(sender, test_signer, mock_wrapper.address, alice, joker.address, 100, dest, PAY1, REF, vault=vault)
    sender.pay(RAIL_MPP, mock_wrapper.address, alice, joker.address, 100, dest, PAY1, REF, False, b"", vault, sig, sender=bob)
    assert processor.operations(PAY1)[3] == 100


def test_partial_vault_is_rejected(sender, mock_wrapper, joker, test_signer, admin, alice, bob, env):
    # legoId set but vaultToken empty -> malformed; must revert (even though correctly signed)
    dest = env.generate_address("merchant")
    joker.addDestination(dest, sender=admin)
    partial = (1, ZERO_ADDRESS, 0, EMPTY32)
    sig = _sign(sender, test_signer, mock_wrapper.address, alice, joker.address, 100, dest, PAY1, REF, vault=partial)
    with boa.reverts("partial vault config"):
        sender.pay(RAIL_MPP, mock_wrapper.address, alice, joker.address, 100, dest, PAY1, REF, False, b"", partial, sig, sender=bob)


# ═══════════════════════════ F3: owner can revoke a leaked signature ═══════════════════════════

def test_increment_nonce_revokes_pending_signature(sender, mock_wrapper, joker, test_signer, admin, alice, bob, env):
    dest = env.generate_address("merchant")
    joker.addDestination(dest, sender=admin)
    sig = _sign(sender, test_signer, mock_wrapper.address, alice, joker.address, 100, dest, PAY1, REF)

    # owner bumps the nonce before the (leaked) signature is broadcast
    sender.incrementNonce(alice, sender=test_signer.address)
    assert sender.currentNonce(alice) == 1

    # the pre-signed nonce-0 payment is now dead
    with boa.reverts("invalid nonce"):
        sender.pay(RAIL_MPP, mock_wrapper.address, alice, joker.address, 100, dest, PAY1, REF, False, b"", NO_VAULT, sig, sender=bob)


def test_increment_nonce_owner_only(sender, alice, bob):
    with boa.reverts("no perms"):
        sender.incrementNonce(alice, sender=bob)
