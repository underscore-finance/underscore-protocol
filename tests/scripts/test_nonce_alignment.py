from types import SimpleNamespace

import boa
import pytest
from boa.network import NetworkEnv

from scripts.utils.migration_helpers import execute_transaction
from scripts.utils.nonce_alignment import (
    _send_zero_value_self_transaction,
    assert_chain_id,
    guard_transaction_nonce,
    require_account_nonce,
)


DEPLOYER = "0x14051A647C2B647363739ccfD4B008AfEeb8FD8e"
OTHER_ACCOUNT = "0x0000000000000000000000000000000000000002"
ROBINHOOD_CHAIN_ID = 4_663


pytestmark = pytest.always


# These are pure fake-NetworkEnv tests. Avoid constructing the protocol from
# the repo-wide autouse fixtures just to exercise RPC/signing-boundary logic.
@pytest.fixture(scope="session")
def undy_hq():
    return None


@pytest.fixture(scope="session")
def wallet_backpack():
    return None


class FakeRpc:
    def __init__(self, latest, pending, chain_id=ROBINHOOD_CHAIN_ID):
        self.latest = latest
        self.pending = pending
        self.chain_id = chain_id
        self.pending_error = None
        self.calls = []

    def fetch(self, method, params):
        self.calls.append((method, params))
        if method == "eth_chainId":
            return hex(self.chain_id)
        assert method == "eth_getTransactionCount"
        block_tag = params[1]
        if block_tag == "pending" and self.pending_error is not None:
            raise self.pending_error
        return hex(self.latest if block_tag == "latest" else self.pending)


class FakeState:
    def __init__(self):
        self.incremented = []

    def increment_nonce(self, address):
        self.incremented.append(address)


class FakeNetworkEnv:
    def __init__(
        self,
        latest,
        pending,
        *,
        rpc_chain_id=ROBINHOOD_CHAIN_ID,
        local_chain_id=ROBINHOOD_CHAIN_ID,
    ):
        self._rpc = FakeRpc(latest, pending, rpc_chain_id)
        self.state = FakeState()
        self.evm = SimpleNamespace(
            patch=SimpleNamespace(chain_id=local_chain_id),
            vm=SimpleNamespace(state=self.state),
        )
        self.raw_call_count = 0
        self.original_get_nonce_calls = 0

    def _get_nonce(self, _address):
        self.original_get_nonce_calls += 1
        return hex(self._rpc.latest)

    def raw_call(self, *_args, **_kwargs):
        self.raw_call_count += 1
        return object()


class RecordingSigner:
    def __init__(self):
        self.transactions = []

    def sign_transaction(self, transaction):
        self.transactions.append(dict(transaction))
        return SimpleNamespace(raw_transaction=b"signed-transaction")


class SigningPathRpc(FakeRpc):
    def __init__(self, latest, pending, *, advance_during_estimate=False):
        super().__init__(latest, pending)
        self.advance_during_estimate = advance_during_estimate
        self.raw_broadcasts = []

    def fetch(self, method, params):
        if method == "eth_estimateGas":
            self.calls.append((method, params))
            if self.advance_during_estimate:
                self.latest += 1
                self.pending += 1
            return "0x5208"
        if method == "eth_sendRawTransaction":
            self.calls.append((method, params))
            self.raw_broadcasts.append(params[0])
            return "0x" + "ab" * 32
        return super().fetch(method, params)

    def wait_for_tx_receipt(self, _tx_hash, _poll_timeout):
        return {
            "status": "0x1",
            "blockHash": "0x" + "cd" * 32,
            "blockNumber": "0x10",
        }


class RealBoaSigningPathEnv(FakeNetworkEnv):
    # Exercise Titanoboa's installed transaction construction path, rather
    # than merely calling our temporary _get_nonce override directly.
    _send_txn = NetworkEnv._send_txn

    def __init__(self, latest, pending, *, advance_during_estimate=False):
        super().__init__(latest, pending)
        self._rpc = SigningPathRpc(
            latest,
            pending,
            advance_during_estimate=advance_during_estimate,
        )
        self.signer = RecordingSigner()
        self._accounts = {DEPLOYER: self.signer}
        self.tx_settings = SimpleNamespace(
            estimate_gas_block_identifier=None,
            poll_timeout=1,
        )

    def get_eip1559_fee(self):
        return 1, 1, 2, ROBINHOOD_CHAIN_ID

    def _debug_tt(self, _tx_hash):
        return None

    def _reset_fork(self, **_kwargs):
        # The mocked receipt represents the expected nonce being mined.
        self._rpc.latest = 6
        self._rpc.pending = 6


@pytest.mark.parametrize(
    ("latest", "pending", "expected_message"),
    [
        (4, 5, "deployer has pending transactions: latest nonce 4, pending nonce 5"),
        (5, 6, "deployer has pending transactions: latest nonce 5, pending nonce 6"),
    ],
)
def test_require_account_nonce_rejects_pending_nonce_gap(
    latest,
    pending,
    expected_message,
):
    env = FakeNetworkEnv(latest, pending)

    with pytest.raises(RuntimeError, match=expected_message):
        require_account_nonce(DEPLOYER, expected=latest, env=env)


def test_require_account_nonce_fails_closed_when_pending_rpc_fails():
    env = FakeNetworkEnv(4, 4)
    pending_error = RuntimeError("pending nonce unavailable")
    env._rpc.pending_error = pending_error

    with pytest.raises(RuntimeError) as exc_info:
        require_account_nonce(DEPLOYER, expected=4, env=env)

    assert exc_info.value is pending_error


def test_guard_transaction_nonce_accepts_only_expected_signing_nonce_and_restores():
    env = FakeNetworkEnv(5, 5)

    assert "_get_nonce" not in env.__dict__
    with guard_transaction_nonce(DEPLOYER, expected=5, env=env):
        nonce_at_signing = env._get_nonce(DEPLOYER)
        env._rpc.latest = 6
        env._rpc.pending = 6

    assert nonce_at_signing == "0x5"
    assert env.original_get_nonce_calls == 0
    assert "_get_nonce" not in env.__dict__
    assert env._get_nonce(DEPLOYER) == "0x6"
    assert env.original_get_nonce_calls == 1


def test_guard_transaction_nonce_rejects_changed_nonce_before_signer_or_broadcast():
    env = FakeNetworkEnv(5, 5)
    signer_or_broadcast_calls = 0

    with pytest.raises(
        RuntimeError,
        match="deployer nonce changed at signing boundary: expected 5, got 6",
    ):
        with guard_transaction_nonce(DEPLOYER, expected=5, env=env):
            env._rpc.latest = 6
            env._rpc.pending = 6
            env._get_nonce(DEPLOYER)
            signer_or_broadcast_calls += 1

    assert signer_or_broadcast_calls == 0
    assert env.original_get_nonce_calls == 0
    assert "_get_nonce" not in env.__dict__


def test_guard_transaction_nonce_rejects_new_pending_tx_at_signing_boundary():
    env = FakeNetworkEnv(5, 5)
    signer_or_broadcast_calls = 0

    with pytest.raises(
        RuntimeError,
        match=(
            "deployer has pending transactions at signing boundary: "
            "latest nonce 5, pending nonce 6"
        ),
    ):
        with guard_transaction_nonce(DEPLOYER, expected=5, env=env):
            env._rpc.pending = 6
            env._get_nonce(DEPLOYER)
            signer_or_broadcast_calls += 1

    assert signer_or_broadcast_calls == 0
    assert env.original_get_nonce_calls == 0
    assert "_get_nonce" not in env.__dict__


def test_guard_binds_nonce_used_by_real_boa_signing_path():
    env = RealBoaSigningPathEnv(5, 5, advance_during_estimate=True)

    with guard_transaction_nonce(DEPLOYER, expected=5, env=env):
        env._send_txn(
            from_=DEPLOYER,
            to=OTHER_ACCOUNT,
            value=0,
            data="0x",
        )

    # A concurrent nonce advance after transaction construction cannot make
    # Boa ask for and sign nonce 6: the exact committed nonce is already in
    # the transaction object handed to the signer.
    assert [transaction["nonce"] for transaction in env.signer.transactions] == [
        "0x5"
    ]
    assert len(env._rpc.raw_broadcasts) == 1


def test_real_boa_signing_path_rejects_pending_gap_before_sign_or_broadcast():
    env = RealBoaSigningPathEnv(5, 5)

    with pytest.raises(
        RuntimeError,
        match=(
            "deployer has pending transactions at signing boundary: "
            "latest nonce 5, pending nonce 6"
        ),
    ):
        with guard_transaction_nonce(DEPLOYER, expected=5, env=env):
            env._rpc.pending = 6
            env._send_txn(
                from_=DEPLOYER,
                to=OTHER_ACCOUNT,
                value=0,
                data="0x",
            )

    assert env.signer.transactions == []
    assert env._rpc.raw_broadcasts == []


def test_guard_transaction_nonce_rejects_wrong_sender_and_restores():
    env = FakeNetworkEnv(5, 5)

    with pytest.raises(
        RuntimeError,
        match=f"unexpected transaction sender {OTHER_ACCOUNT}; expected {DEPLOYER}",
    ):
        with guard_transaction_nonce(DEPLOYER, expected=5, env=env):
            env._get_nonce(OTHER_ACCOUNT)

    assert env.original_get_nonce_calls == 0
    assert "_get_nonce" not in env.__dict__


def test_network_padding_does_not_mutate_local_nonce_when_rpc_does_not_advance():
    env = FakeNetworkEnv(4, 4)

    with boa.set_env(env):
        with pytest.raises(
            RuntimeError,
            match=(
                "nonce padding transaction did not increment the deployer nonce "
                "exactly once: 4 -> latest 4, pending 4"
            ),
        ):
            _send_zero_value_self_transaction(sender=DEPLOYER)

    assert env.raw_call_count == 1
    assert env.state.incremented == []


def test_assert_chain_id_rejects_wrong_rpc_chain():
    env = FakeNetworkEnv(0, 0, rpc_chain_id=8_453, local_chain_id=8_453)

    with pytest.raises(
        RuntimeError,
        match="wrong chain id: expected 4663, got 8453",
    ):
        assert_chain_id(ROBINHOOD_CHAIN_ID, env=env)


def test_assert_chain_id_rejects_rpc_and_boa_state_mismatch():
    env = FakeNetworkEnv(
        0,
        0,
        rpc_chain_id=ROBINHOOD_CHAIN_ID,
        local_chain_id=8_453,
    )

    with pytest.raises(
        RuntimeError,
        match="active RPC chain id 4663 does not match Boa state chain id 8453",
    ):
        assert_chain_id(ROBINHOOD_CHAIN_ID, env=env)


def test_no_retry_calls_once_and_reraises_the_exact_broadcast_error():
    broadcast_error = RuntimeError("ambiguous broadcast failure")
    calls = 0

    def fail_once():
        nonlocal calls
        calls += 1
        raise broadcast_error

    with pytest.raises(RuntimeError) as exc_info:
        execute_transaction(fail_once, no_retry=True)

    assert exc_info.value is broadcast_error
    assert calls == 1


def test_no_retry_does_not_swallow_broadcast_error_containing_nonetype():
    broadcast_error = RuntimeError("NoneType returned after ambiguous broadcast")
    calls = 0

    def fail_once():
        nonlocal calls
        calls += 1
        raise broadcast_error

    with pytest.raises(RuntimeError) as exc_info:
        execute_transaction(fail_once, no_retry=True)

    assert exc_info.value is broadcast_error
    assert calls == 1
