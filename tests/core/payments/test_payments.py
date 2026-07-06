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


def _a(x):
    return str(x).lower()


def _logs(c, name):
    return [e for e in c.get_logs() if type(e).__name__ == name]


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
def tempo_recipient(env):
    return env.generate_address("tempo_omnibus")


@pytest.fixture
def bridge_adapter():
    return boa.load("contracts/mock/MockBridgeAdapter.vy")


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
    assert store.indexOfProxy(addr) == 1
    assert store.numProxies() == 1
    assert store.isProxyEnabled(addr) is True            # enabled on creation
    assert _a(store.getProxyById("x402joker.com")) == _a(addr)
    assert _a(proxy_partial.at(addr).ID()) == "x402joker.com"
    with boa.reverts("id taken"):
        store.createProxy("x402joker.com", sender=admin)


def test_create_proxy_perms(store, alice):
    with boa.reverts("no perms"):
        store.createProxy("nope.com", sender=alice)


def test_destinations_live_in_proxy(store, admin, joker, proxy_partial, env):
    # CRUD flows through the ProxyStore (the only entry point), but each proxy owns its own allow-list.
    d1 = env.generate_address("d1")
    d2 = env.generate_address("d2")
    service2 = proxy_partial.at(store.createProxy("service2.com", sender=admin))
    store.addDestination(joker.address, d1, sender=admin)
    store.addDestination(joker.address, d2, sender=admin)
    store.addDestination(service2.address, d1, sender=admin)  # same dest, independent per-proxy list
    assert joker.isAllowed(d1) is True
    assert [_a(x) for x in joker.getDestinations()] == [_a(d1), _a(d2)]
    assert [_a(x) for x in service2.getDestinations()] == [_a(d1)]
    store.addDestination(joker.address, d1, sender=admin)     # idempotent — no duplicate
    assert [_a(x) for x in joker.getDestinations()] == [_a(d1), _a(d2)]
    # remove d1 from joker: swap-removed there, service2 untouched (self-contained)
    store.removeDestination(joker.address, d1, sender=admin)
    assert joker.isAllowed(d1) is False
    assert [_a(x) for x in joker.getDestinations()] == [_a(d2)]
    assert [_a(x) for x in service2.getDestinations()] == [_a(d1)]


def test_add_destination_perms(store, joker, alice, env):
    with boa.reverts("no perms"):
        store.addDestination(joker.address, env.generate_address("d"), sender=alice)


def test_only_store_can_edit_destinations(joker, admin, env):
    # the proxy holds the data but rejects any editor except the ProxyStore — even a switchboard admin
    with boa.reverts("only store"):
        joker.addDestination(env.generate_address("d"), sender=admin)
    with boa.reverts("only store"):
        joker.removeDestination(env.generate_address("d"), sender=admin)


def test_curator_can_manage(store, admin, alice, proxy_partial, env):
    store.setCurator(alice, True, sender=admin)          # switchboard grants curator
    proxy = proxy_partial.at(store.createProxy("curated.com", sender=alice))  # curator can now create
    store.addDestination(proxy.address, env.generate_address("d"), sender=alice)  # ...and manage via the store
    assert len(proxy.getDestinations()) == 1
    with boa.reverts("no perms"):
        store.setCurator(alice, True, sender=alice)      # but not switchboard-admin ops


def test_set_proxy_enabled_perms(store, joker, alice):
    with boa.reverts("no perms"):
        store.setProxyEnabled(joker.address, False, sender=alice)


def test_set_proxy_enabled_requires_proxy(store, admin, env):
    with boa.reverts("not a proxy"):
        store.setProxyEnabled(env.generate_address("fake"), False, sender=admin)


# ═══════════════════════════ PaymentProcessor: MPP hub ═══════════════════════════

def test_register_mpp_pulls_and_escrows(processor, joker, usdc, admin, deploy3r, alice, bob, agent_wrapper):
    processor.setSender(bob, True, sender=admin)
    usdc.mint(joker.address, 100, sender=deploy3r)       # sender already pushed funds into the proxy
    processor.registerMpp(agent_wrapper, joker.address, alice, 100, PAY1, REF, sender=bob)
    logs = _logs(processor, "OperationRegistered")
    assert usdc.balanceOf(processor.address) == 100
    assert usdc.balanceOf(joker.address) == 0
    op = processor.operations(PAY1)
    assert _a(op[0]) == _a(alice) and _a(op[1]) == _a(joker.address) and _a(op[2]) == _a(agent_wrapper)
    assert op[3] == 100 and op[6] is True                # agentWrapper recorded at [2]; amount shifts to [3], exists to [6]
    assert processor.pendingTotal() == 100
    assert logs[0].amount == 100 and logs[0].rail == 1
    assert _a(logs[0].agentWrapper) == _a(agent_wrapper)  # initiating wrapper emitted for audit


def test_register_mpp_sender_gated(processor, joker, alice, bob, agent_wrapper):
    with boa.reverts("not a sender"):
        processor.registerMpp(agent_wrapper, joker.address, alice, 100, PAY1, REF, sender=bob)


def test_register_mpp_rejects_disabled_or_unknown_proxy(processor, admin, alice, bob, env, agent_wrapper):
    # a non-proxy (or a disabled proxy) is not enabled in the ProxyStore, so settlement refuses it
    processor.setSender(bob, True, sender=admin)
    with boa.reverts("proxy not enabled"):
        processor.registerMpp(agent_wrapper, env.generate_address("fake"), alice, 100, PAY1, REF, sender=bob)


def test_disabled_proxy_blocks_both_rails(processor, store, joker, usdc, admin, deploy3r, alice, bob, env, agent_wrapper):
    dest = env.generate_address("payto")
    processor.setSender(bob, True, sender=admin)
    store.addDestination(joker.address, dest, sender=admin)
    usdc.mint(joker.address, 100, sender=deploy3r)
    store.setProxyEnabled(joker.address, False, sender=admin)     # disable — like removing it from the index
    assert store.isProxyEnabled(joker.address) is False
    with boa.reverts("proxy not enabled"):
        processor.registerMpp(agent_wrapper, joker.address, alice, 100, PAY1, REF, sender=bob)
    with boa.reverts("proxy not enabled"):
        processor.registerX402(agent_wrapper, joker.address, alice, 100, dest, 0, FAR_FUTURE, PAY1, REF, sender=bob)
    store.setProxyEnabled(joker.address, True, sender=admin)      # re-enable — state restored
    processor.registerMpp(agent_wrapper, joker.address, alice, 100, PAY1, REF, sender=bob)
    assert usdc.balanceOf(processor.address) == 100
    assert processor.operations(PAY1)[3] == 100


def test_register_rejects_empty_agent_wrapper(processor, joker, admin, alice, bob):
    # the initiating wrapper is audit-only, but must be present so the trail can't be polluted with a zero
    processor.setSender(bob, True, sender=admin)
    with boa.reverts("no agent wrapper"):
        processor.registerMpp(ZERO_ADDRESS, joker.address, alice, 100, PAY1, REF, sender=bob)


# ═══════════════════════════ PaymentProcessor: x402 hub ═══════════════════════════

def test_register_x402_binds_digest_and_gates_dest(processor, store, joker, usdc, admin, deploy3r, alice, bob, env, agent_wrapper):
    dest = env.generate_address("joker_payto")
    processor.setSender(bob, True, sender=admin)
    usdc.mint(joker.address, 100, sender=deploy3r)
    # dest not yet allow-listed -> reverts
    with boa.reverts("dest not allowed"):
        processor.registerX402(agent_wrapper, joker.address, alice, 100, dest, 0, FAR_FUTURE, PAY1, REF, sender=bob)
    # allow-list it, then it binds the EIP-3009 digest and the processor honors it via EIP-1271
    store.addDestination(joker.address, dest, sender=admin)
    digest = processor.registerX402(agent_wrapper, joker.address, alice, 100, dest, 0, FAR_FUTURE, PAY1, REF, sender=bob)
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
    store.addDestination(joker.address, dest, sender=admin)
    usdc.mint(joker.address, amount, sender=deploy3r)
    return processor.registerX402(agent_wrapper, joker.address, alice, amount, dest, 0, FAR_FUTURE, pid, REF, sender=bob)


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

def test_bridge_via_adapter_and_refund(processor, joker, usdc, admin, deploy3r, alice, bob, bridge_adapter, tempo_recipient, agent_wrapper):
    processor.setSender(bob, True, sender=admin)
    processor.setRelayer(bob, True, sender=admin)
    processor.setBridge(bridge_adapter.address, tempo_recipient, 4217, sender=admin)  # only switchboard sets the dest
    usdc.mint(joker.address, 100, sender=deploy3r)
    processor.registerMpp(agent_wrapper, joker.address, alice, 100, PAY1, REF, sender=bob)
    # the relayer (server) triggers the bridge + amount; the adapter + Tempo recipient are fixed config
    processor.bridge(60, sender=bob)
    assert usdc.balanceOf(bridge_adapter.address) == 60
    assert _a(bridge_adapter.lastRecipient()) == _a(tempo_recipient)   # the server never chose this
    assert bridge_adapter.lastAmount() == 60 and bridge_adapter.lastDestChainId() == 4217
    assert usdc.allowance(processor.address, bridge_adapter.address) == 0
    assert processor.pendingTotal() == 40
    # refund 25 to the recorded payer
    processor.refund(PAY1, 25, sender=bob)
    assert usdc.balanceOf(alice) == 25
    assert processor.operations(PAY1)[4] == 25              # refunded at [4] (agentWrapper recorded at [2])
    with boa.reverts("not a relayer"):
        processor.bridge(10, sender=alice)


def test_only_switchboard_sets_the_tempo_destination(processor, admin, bob, alice, bridge_adapter, tempo_recipient):
    # the relayer (server) can trigger bridge() but can NOT define the Tempo recipient/adapter
    processor.setBridge(bridge_adapter.address, tempo_recipient, 4217, sender=admin)
    assert _a(processor.tempoRecipient()) == _a(tempo_recipient)
    with boa.reverts("no perms"):
        processor.setBridge(bridge_adapter.address, bob, 4217, sender=bob)     # relayer can't redirect
    with boa.reverts("no perms"):
        processor.setBridge(bridge_adapter.address, alice, 4217, sender=alice)


# ═══════════════════════════ PaymentSender: full orchestration ═══════════════════════════

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


def _sign_mpp(sender, test_signer, wrapper, wallet, proxy, amount, pid, ref):
    digest, nonce, exp = sender.getPayMppHash(wrapper, wallet, proxy, amount, pid, ref, NO_VAULT, FAR_FUTURE)
    return (test_signer.unsafe_sign_hash(digest).signature, nonce, exp)


def test_pay_mpp_end_to_end(sender, mock_wrapper, joker, processor, usdc, test_signer, alice, bob):
    sig = _sign_mpp(sender, test_signer, mock_wrapper.address, alice, joker.address, 100, PAY1, REF)
    # any broadcaster submits; owner (test_signer) signature authorizes
    sender.payMpp(mock_wrapper.address, alice, joker.address, 100, PAY1, REF, NO_VAULT, sig, sender=bob)
    # funds flowed UW(mock) -> proxy -> processor; op recorded
    assert usdc.balanceOf(processor.address) == 100
    assert usdc.balanceOf(joker.address) == 0
    assert processor.operations(PAY1)[3] == 100                          # amount at [3] (agentWrapper recorded at [2])
    assert _a(processor.operations(PAY1)[2]) == _a(mock_wrapper.address)  # PaymentSender threads the wrapper through
    assert sender.currentNonce(alice) == 1


def test_pay_mpp_wrong_signer_reverts(sender, mock_wrapper, joker, alice, bob):
    wrong = Account.from_key("0x" + "11" * 32)
    digest, nonce, exp = sender.getPayMppHash(mock_wrapper.address, alice, joker.address, 100, PAY1, REF, NO_VAULT, FAR_FUTURE)
    bad = (wrong.unsafe_sign_hash(digest).signature, nonce, exp)
    with boa.reverts("invalid signer"):
        sender.payMpp(mock_wrapper.address, alice, joker.address, 100, PAY1, REF, NO_VAULT, bad, sender=bob)


def test_pay_mpp_replay_reverts(sender, mock_wrapper, joker, test_signer, alice, bob):
    sig = _sign_mpp(sender, test_signer, mock_wrapper.address, alice, joker.address, 100, PAY1, REF)
    sender.payMpp(mock_wrapper.address, alice, joker.address, 100, PAY1, REF, NO_VAULT, sig, sender=bob)
    with boa.reverts("invalid nonce"):
        sender.payMpp(mock_wrapper.address, alice, joker.address, 100, PAY2, REF, NO_VAULT, sig, sender=bob)
