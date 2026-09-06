import boa
import pytest
from boa.network import NetworkEnv
from boa.rpc import RPC

from scripts.utils.deploy_args import DeployArgs
from scripts.utils.migration_helpers import load_vyper_files
from scripts.utils.migration_runner import MigrationError, MigrationRunner
from scripts.utils.nonce_alignment import get_account_nonces


DEPLOYER = "0x14051A647C2B647363739ccfD4B008AfEeb8FD8e"

pytestmark = pytest.always


@pytest.fixture(scope="session")
def undy_hq():
    return None


@pytest.fixture(scope="session")
def wallet_backpack():
    return None


class RejectingSigner:
    address = DEPLOYER

    def __init__(self):
        self.transactions = []

    def sign_transaction(self, transaction):
        self.transactions.append(dict(transaction))
        raise RuntimeError("device rejected transaction")


class RobinhoodRpc(RPC):
    def __init__(self):
        self.raw_broadcasts = []

    @property
    def identifier(self):
        return f"memory://robinhood-signing-rejection-{id(self)}"

    @property
    def name(self):
        return "fake-robinhood"

    def fetch(self, method, params):
        if method == "eth_chainId":
            return hex(4_663)
        if method == "eth_getBlockByNumber":
            return {
                "number": "0x1",
                "timestamp": "0x1",
                "parentHash": "0x" + "00" * 32,
                "baseFeePerGas": hex(10**9),
            }
        if method == "eth_getBalance":
            funded = str(params[0]).lower() == DEPLOYER.lower()
            return hex(10**20) if funded else "0x0"
        if method == "eth_getCode":
            return "0x"
        if method in ("eth_getTransactionCount", "eth_getStorageAt"):
            return "0x0"
        if method in ("eth_maxPriorityFeePerGas", "eth_gasPrice"):
            return hex(10**9)
        if method == "eth_estimateGas":
            return hex(8_000_000)
        if method == "eth_sendRawTransaction":
            self.raw_broadcasts.append(params[0])
            return "0x" + "ab" * 32
        raise AssertionError(f"unexpected RPC call: {method} {params}")

    def fetch_multi(self, payloads):
        return [self.fetch(method, params) for method, params in payloads]


class UncachedNetworkEnv(NetworkEnv):
    def _reset_fork(self, block_identifier="latest"):
        self.fork_rpc(
            self._rpc,
            reset_traces=False,
            block_identifier=block_identifier,
            cache_dir=None,
        )


def test_robinhood_core_signer_rejection_records_no_progress(tmp_path):
    history = tmp_path / "history"
    rpc = RobinhoodRpc()
    signer = RejectingSigner()
    env = UncachedNetworkEnv(rpc, fork_try_prefetch_state=False)
    env.add_account(signer, force_eoa=True)
    runner = MigrationRunner(
        "migrations/robinhood-mainnet/v1",
        str(history),
        load_vyper_files(),
    )
    deploy_args = DeployArgs(
        signer,
        "robinhood-mainnet",
        ignore_logs=False,
        blueprint="robinhood",
        rpc=rpc.identifier,
    )

    with boa.set_env(env):
        with pytest.raises(MigrationError) as exc_info:
            runner.run(deploy_args, start_timestamp="0000", end_timestamp="0000")

        assert str(exc_info.value.__cause__) == "device rejected transaction"
        assert get_account_nonces(DEPLOYER) == (0, 0)

    assert len(signer.transactions) == 1
    assert signer.transactions[0]["nonce"] == "0x0"
    assert "to" not in signer.transactions[0]
    assert rpc.raw_broadcasts == []
    assert not history.exists()
