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


def _dests(proxy):
    # enumerate the proxy's 1-based dest list via its public getters (getDestinations was removed)
    return [_a(proxy.dests(i)) for i in range(1, proxy.numDests())]


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
def proxy_partial():
    return boa.load_partial("contracts/core/payments/PaymentProcessorProxy.vy")


@pytest.fixture
def store(mock_hq, proxy_partial, admin):
    template = proxy_partial.deploy_as_blueprint()
    s = boa.load("contracts/core/payments/ProxyStore.vy", mock_hq.address, template.address)
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
    p = boa.load("contracts/core/payments/PaymentProcessor.vy", mock_hq.address, usdc.address)
    mock_hq.setAddr(13, p.address)
    return p


@pytest.fixture
def joker(store, admin, proxy_partial):
    return proxy_partial.at(store.createProxy("x402joker.com", sender=admin))


@pytest.fixture
def agent_wrapper(env):
    return env.generate_address("agent_wrapper")


# ═══════════════════════════ ProxyStore: factory + registry; Proxy: self-contained allow-list ═══════════════════════════

def test_create_proxy(store, admin, proxy_partial):
    addr = store.createProxy("x402joker.com", sender=admin)
    assert store.indexOfProxy(addr) == 1                 # 1-based registry
    assert store.getNumProxies() == 1
    assert store.isProxy(addr) is True                   # registered on creation
    assert _a(store.proxies(1)[0]) == _a(addr)           # id lives on the record
    assert store.proxies(1)[1] == "x402joker.com"
    assert _a(proxy_partial.at(addr).ID()) == "x402joker.com"
    # ids are labels now (no id index): a second proxy just takes the next reg id
    addr2 = store.createProxy("x402joker.com", sender=admin)
    assert store.indexOfProxy(addr2) == 2
    assert store.getNumProxies() == 2


def test_create_proxy_perms(store, alice):
    with boa.reverts("no perms"):
        store.createProxy("nope.com", sender=alice)


def test_destinations_live_in_proxy(store, admin, joker, proxy_partial, env):
    # each proxy owns its own allow-list; the Switchboard edits it directly on the proxy.
    d1 = env.generate_address("d1")
    d2 = env.generate_address("d2")
    service2 = proxy_partial.at(store.createProxy("service2.com", sender=admin))
    joker.addDestination(d1, sender=admin)
    joker.addDestination(d2, sender=admin)
    service2.addDestination(d1, sender=admin)  # same dest, independent per-proxy list
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
    # the proxy owns the data and lets the Switchboard edit it directly; everyone else is rejected
    d = env.generate_address("d")
    joker.addDestination(d, sender=admin)                # switchboard OK
    assert joker.isAllowed(d) is True
    with boa.reverts("not switchboard"):
        joker.addDestination(env.generate_address("d2"), sender=alice)
    with boa.reverts("not switchboard"):
        joker.removeDestination(d, sender=alice)


def test_curator_can_manage(store, admin, alice, proxy_partial, env):
    store.setCurator(alice, True, sender=admin)          # switchboard grants curator
    proxy = proxy_partial.at(store.createProxy("curated.com", sender=alice))  # curator can create
    assert store.isProxy(proxy.address) is True
    store.removeProxy(proxy.address, sender=alice)        # ...and remove proxies (factory role)
    assert store.isProxy(proxy.address) is False
    # but destinations are switchboard-only, and a curator is not a switchboard admin
    proxy2 = proxy_partial.at(store.createProxy("curated2.com", sender=alice))
    with boa.reverts("not switchboard"):
        proxy2.addDestination(env.generate_address("d"), sender=alice)
    with boa.reverts("no perms"):
        store.setCurator(alice, True, sender=alice)      # not switchboard-admin ops


def test_remove_proxy_perms(store, joker, alice):
    with boa.reverts("no perms"):
        store.removeProxy(joker.address, sender=alice)


def test_remove_proxy_requires_proxy(store, admin, env):
    with boa.reverts("not a proxy"):
        store.removeProxy(env.generate_address("fake"), sender=admin)


# ═══════════════════════════ Proxy: recover funds + pull payment ═══════════════════════════

def test_recover_funds_switchboard_only(joker, usdc, admin, deploy3r, alice, bob):
    usdc.mint(joker.address, 100, sender=deploy3r)
    with boa.reverts("not switchboard"):
        joker.recoverFunds(alice, usdc.address, sender=bob)
    joker.recoverFunds(alice, usdc.address, sender=admin)  # switchboard sweeps stray funds
    assert usdc.balanceOf(alice) == 100
    assert usdc.balanceOf(joker.address) == 0


def test_proxy_pull_payment_only_processor(joker, alice, bob, usdc):
    with boa.reverts("only processor"):
        joker.pullPayment(alice, usdc.address, 100, False, sender=bob)


def test_proxy_pull_payment_routes_billing(processor, joker, mock_billing, usdc, alice):
    # only the PaymentProcessor may drive the pull; `_isCheque` routes cheque vs payee in Billing
    joker.pullPayment(alice, usdc.address, 100, True, sender=processor.address)
    assert mock_billing.lastWasCheque() is True
    assert _a(mock_billing.lastUserWallet()) == _a(alice)
    assert mock_billing.lastAmount() == 100
    joker.pullPayment(alice, usdc.address, 50, False, sender=processor.address)
    assert mock_billing.lastWasCheque() is False
    assert mock_billing.lastAmount() == 50


# ═══════════════════════════ PaymentProcessor: register (MPP rail) ═══════════════════════════

def test_register_mpp_pulls_and_escrows(processor, joker, usdc, admin, deploy3r, alice, bob, agent_wrapper, env):
    dest = env.generate_address("merchant")
    processor.setSender(bob, True, sender=admin)
    joker.addDestination(dest, sender=admin)
    usdc.mint(joker.address, 100, sender=deploy3r)       # sender already pushed funds into the proxy
    ret = processor.register(RAIL_MPP, agent_wrapper, joker.address, alice, 100, dest, PAY1, REF, b"", sender=bob)
    assert bytes(ret) == EMPTY32                          # MPP returns empty
    logs = _logs(processor, "OperationRegistered")
    assert usdc.balanceOf(processor.address) == 100
    assert usdc.balanceOf(joker.address) == 0
    op = processor.operations(PAY1)
    assert _a(op[0]) == _a(alice) and _a(op[1]) == _a(joker.address) and _a(op[2]) == _a(agent_wrapper)
    assert op[3] == 100 and op[6] is True                # agentWrapper recorded at [2]; amount [3]; exists [6]
    assert processor.pendingTotal() == 100
    assert logs[0].amount == 100 and logs[0].rail == 1
    assert _a(logs[0].agentWrapper) == _a(agent_wrapper)  # initiating wrapper emitted for audit


def test_register_mpp_gates_dest(processor, joker, usdc, admin, deploy3r, alice, bob, agent_wrapper, env):
    # MPP now takes + validates a dest against the proxy allow-list, like x402
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


def test_register_rejects_unknown_proxy(processor, admin, alice, bob, env, agent_wrapper):
    # a non-proxy is not registered in the ProxyStore, so settlement refuses it
    processor.setSender(bob, True, sender=admin)
    with boa.reverts("not a proxy"):
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


def test_removed_proxy_blocks_both_rails(processor, store, joker, usdc, admin, deploy3r, alice, bob, env, agent_wrapper):
    dest = env.generate_address("payto")
    processor.setSender(bob, True, sender=admin)
    joker.addDestination(dest, sender=admin)
    usdc.mint(joker.address, 100, sender=deploy3r)
    store.removeProxy(joker.address, sender=admin)               # remove — takes it out of the index
    assert store.isProxy(joker.address) is False
    with boa.reverts("not a proxy"):
        processor.register(RAIL_MPP, agent_wrapper, joker.address, alice, 100, dest, PAY1, REF, b"", sender=bob)
    with boa.reverts("not a proxy"):
        processor.register(RAIL_X402, agent_wrapper, joker.address, alice, 100, dest, PAY1, REF, _x402_extra(0, FAR_FUTURE), sender=bob)


# ═══════════════════════════ PaymentProcessor: register (x402 rail) ═══════════════════════════

def test_register_x402_binds_digest_and_gates_dest(processor, store, joker, usdc, admin, deploy3r, alice, bob, env, agent_wrapper):
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
    # revoke -> no longer honored
    processor.setRelayer(bob, True, sender=admin)
    processor.revokeX402(PAY1, sender=bob)
    assert bytes(processor.isValidSignature(digest, b"")) == FAIL


def _register_x402(processor, store, joker, usdc, admin, deploy3r, alice, bob, dest, agent_wrapper, amount=100, pid=PAY1):
    processor.setSender(bob, True, sender=admin)
    processor.setRelayer(bob, True, sender=admin)
    joker.addDestination(dest, sender=admin)
    usdc.mint(joker.address, amount, sender=deploy3r)
    return processor.register(RAIL_X402, agent_wrapper, joker.address, alice, amount, dest, pid, REF, _x402_extra(0, FAR_FUTURE), sender=bob)


def test_refund_x402_before_pull_revokes_and_refunds(processor, store, joker, usdc, admin, deploy3r, alice, bob, env, agent_wrapper):
    dest = env.generate_address("payto")
    digest = _register_x402(processor, store, joker, usdc, admin, deploy3r, alice, bob, dest, agent_wrapper)
    # merchant has NOT pulled -> refund revokes the authorization and returns the funds to the payer
    processor.refund(PAY1, 100, sender=bob)
    assert usdc.balanceOf(alice) == 100
    assert bytes(processor.isValidSignature(digest, b"")) == FAIL   # revoked — can't be pulled after
    assert processor.operations(PAY1)[4] == 100                     # refunded at [4] (agentWrapper recorded at [2])


def test_refund_x402_after_pull_reverts(processor, store, joker, usdc, admin, deploy3r, alice, bob, env, agent_wrapper):
    dest = env.generate_address("payto")
    _register_x402(processor, store, joker, usdc, admin, deploy3r, alice, bob, dest, agent_wrapper)
    # simulate the merchant pulling via transferWithAuthorization -> the EIP-3009 nonce is consumed
    usdc.setAuthUsed(processor.address, processor.x402Nonce(PAY1), True)
    with boa.reverts("already settled"):
        processor.refund(PAY1, 100, sender=bob)


# ═══════════════════════════ PaymentProcessor: bridge + refund ═══════════════════════════

def test_bridge_sends_usdc_and_refund(processor, joker, usdc, admin, deploy3r, alice, bob, bridge_address, agent_wrapper, env):
    dest = env.generate_address("merchant")
    processor.setSender(bob, True, sender=admin)
    processor.setRelayer(bob, True, sender=admin)
    processor.setBridge(bridge_address, sender=admin)    # only switchboard sets the destination
    joker.addDestination(dest, sender=admin)
    usdc.mint(joker.address, 100, sender=deploy3r)
    processor.register(RAIL_MPP, agent_wrapper, joker.address, alice, 100, dest, PAY1, REF, b"", sender=bob)
    # the relayer (server) triggers the bridge + amount; the destination is fixed switchboard config
    processor.bridge(60, sender=bob)
    assert usdc.balanceOf(bridge_address) == 60          # plain USDC send to the Bridge liquidation address
    assert usdc.balanceOf(processor.address) == 40
    assert processor.pendingTotal() == 40
    # refund 25 to the recorded payer
    processor.refund(PAY1, 25, sender=bob)
    assert usdc.balanceOf(alice) == 25
    assert processor.operations(PAY1)[4] == 25           # refunded at [4] (agentWrapper recorded at [2])
    with boa.reverts("not a relayer"):
        processor.bridge(10, sender=alice)


def test_only_switchboard_sets_the_bridge_address(processor, admin, bob, alice, bridge_address):
    # the relayer (server) can trigger bridge() but can NOT define where the funds land
    processor.setBridge(bridge_address, sender=admin)
    assert _a(processor.bridgeAddress()) == _a(bridge_address)
    with boa.reverts("no perms"):
        processor.setBridge(bob, sender=bob)             # relayer can't redirect
    with boa.reverts("no perms"):
        processor.setBridge(alice, sender=alice)


# ═══════════════════════════ PaymentSender: unified pay() orchestration ═══════════════════════════

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
        "contracts/core/agent/PaymentSender.vy",
        mock_hq.address, usdc.address, test_signer.address,
        PARAMS[fork]["GEN_MIN_CONFIG_TIMELOCK"], PARAMS[fork]["GEN_MAX_CONFIG_TIMELOCK"],
    )
    processor.setSender(s.address, True, sender=admin)
    return s


def _sign_pay(sender, test_signer, protocol_id, wrapper, wallet, proxy, amount, dest, pid, ref, is_cheque=False, extra=b""):
    digest, nonce, exp = sender.getPayHash(protocol_id, wrapper, wallet, proxy, amount, dest, pid, ref, is_cheque, extra, FAR_FUTURE)
    return (test_signer.unsafe_sign_hash(digest).signature, nonce, exp)


def test_pay_mpp_end_to_end(sender, mock_wrapper, joker, processor, usdc, test_signer, admin, alice, bob, env):
    dest = env.generate_address("merchant")
    joker.addDestination(dest, sender=admin)
    sig = _sign_pay(sender, test_signer, RAIL_MPP, mock_wrapper.address, alice, joker.address, 100, dest, PAY1, REF)
    # any broadcaster submits; owner (test_signer) signature authorizes
    sender.pay(RAIL_MPP, mock_wrapper.address, alice, joker.address, 100, dest, PAY1, REF, False, b"", NO_VAULT, sig, sender=bob)
    # funds flowed UW(mock) -> proxy -> processor; op recorded
    assert usdc.balanceOf(processor.address) == 100
    assert usdc.balanceOf(joker.address) == 0
    assert processor.operations(PAY1)[3] == 100                          # amount at [3] (agentWrapper recorded at [2])
    assert _a(processor.operations(PAY1)[2]) == _a(mock_wrapper.address)  # PaymentSender threads the wrapper through
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
