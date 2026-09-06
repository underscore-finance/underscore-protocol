from contextlib import contextmanager
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest
from click.testing import CliRunner

import scripts.migrate as migrate_module
from scripts.migrate import cli
from scripts.utils.mock_account import MockAccount


DEPLOYER = "0x14051A647C2B647363739ccfD4B008AfEeb8FD8e"
MIGRATE_PATH = Path(migrate_module.__file__)


# CLI unit tests stub their execution environments and do not need the repo's
# full protocol deployment from the two global autouse fixtures.
@pytest.fixture(scope="session")
def undy_hq():
    return None


@pytest.fixture(scope="session")
def wallet_backpack():
    return None


def _stub_migration_execution(monkeypatch, module=migrate_module):
    state = SimpleNamespace(
        runs=[],
        add_account_calls=[],
        balances=[],
        chain_checks=[],
    )

    class FakeMigrationRunner:
        def __init__(self, *_args, **_kwargs):
            pass

        def run(self, deploy_args, *_args, **_kwargs):
            state.runs.append(deploy_args)
            return 0

    fake_env = SimpleNamespace(eoa=None)
    fake_env.add_account = lambda account, **kwargs: state.add_account_calls.append(
        (account, kwargs)
    )
    fake_env.set_balance = lambda address, balance: state.balances.append(
        (address, balance)
    )

    @contextmanager
    def fake_environment(*_args, **_kwargs):
        yield fake_env

    monkeypatch.setattr(module, "MigrationRunner", FakeMigrationRunner)
    monkeypatch.setattr(module, "load_vyper_files", lambda: {})
    monkeypatch.setattr(module.boa, "fork", fake_environment)
    monkeypatch.setattr(module.boa, "set_network_env", fake_environment)
    monkeypatch.setattr(module.boa, "set_env", fake_environment)
    monkeypatch.setattr(
        module.boa.deployments,
        "set_deployments_db",
        lambda _db: None,
    )
    monkeypatch.setattr(
        module,
        "assert_chain_id",
        lambda expected, *, env: state.chain_checks.append((expected, env)),
    )
    state.env = fake_env
    return state


def _install_fake_ledger_module(monkeypatch):
    state = SimpleNamespace(calls=[], instances=[])

    class FakeLedgerAccount:
        def __init__(
            self,
            rpc_url,
            account_index=0,
            derivation_path=None,
        ):
            self.address = DEPLOYER
            state.calls.append((rpc_url, account_index, derivation_path))
            state.instances.append(self)

    fake_module = ModuleType("scripts.utils.ledger_account")
    fake_module.LedgerAccount = FakeLedgerAccount
    monkeypatch.setitem(sys.modules, "scripts.utils.ledger_account", fake_module)
    return state


@pytest.mark.parametrize(
    ("rpc_url", "expected_label"),
    [
        (
            "https://user:secret@rpc.example/path/APIKEY?token=x",
            "https://rpc.example",
        ),
        ("http://127.0.0.1:8545/private", "http://127.0.0.1:8545"),
        ("boa", "boa"),
    ],
)
def test_rpc_log_label_strips_credentials_and_path_tokens(rpc_url, expected_label):
    assert migrate_module.rpc_log_label(rpc_url) == expected_label


def test_migration_cli_help_loads_without_optional_dotenv_dependency():
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "Deploys the protocol by running migration scripts." in result.output
    assert "--ledger-path" in result.output


def test_ledger_index_binds_hardware_sender_for_live_migration(monkeypatch):
    execution = _stub_migration_execution(monkeypatch)
    ledger = _install_fake_ledger_module(monkeypatch)
    monkeypatch.setattr(
        migrate_module,
        "get_account",
        lambda _name: pytest.fail("private-key account should not be loaded"),
    )

    result = CliRunner().invoke(
        cli,
        [
            "--chain",
            "robinhood-mainnet",
            "--blueprint",
            "robinhood",
            "--rpc",
            "http://127.0.0.1:8545",
            "--start-timestamp",
            "0000",
            "--ledger",
            "3",
        ],
    )

    assert result.exit_code == 0, result.output
    assert ledger.calls == [("http://127.0.0.1:8545", 3, None)]
    assert execution.runs[0].sender is ledger.instances[0]
    assert execution.add_account_calls == [
        (ledger.instances[0], {"force_eoa": True})
    ]


def test_ledger_index_binds_mock_at_device_address_for_fork(monkeypatch):
    execution = _stub_migration_execution(monkeypatch)
    ledger = _install_fake_ledger_module(monkeypatch)
    monkeypatch.setattr(
        migrate_module,
        "get_account",
        lambda _name: pytest.fail("private-key account should not be loaded"),
    )

    result = CliRunner().invoke(
        cli,
        [
            "--chain",
            "robinhood-mainnet",
            "--blueprint",
            "robinhood",
            "--rpc",
            "http://127.0.0.1:8545",
            "--start-timestamp",
            "0000",
            "--fork",
            "--ledger",
            "2",
        ],
    )

    assert result.exit_code == 0, result.output
    assert ledger.calls == [("http://127.0.0.1:8545", 2, None)]
    sender = execution.runs[0].sender
    assert isinstance(sender, MockAccount)
    assert sender.address == DEPLOYER
    assert sender is not ledger.instances[0]
    assert execution.env.eoa == DEPLOYER
    assert execution.balances == [(DEPLOYER, 10 * 10**18)]


def test_explicit_ledger_path_binds_hardware_sender(monkeypatch):
    execution = _stub_migration_execution(monkeypatch)
    ledger = _install_fake_ledger_module(monkeypatch)
    path = "m/44'/60'/1'/0/0"

    result = CliRunner().invoke(
        cli,
        [
            "--chain",
            "robinhood-mainnet",
            "--blueprint",
            "robinhood",
            "--rpc",
            "http://127.0.0.1:8545",
            "--start-timestamp",
            "0000",
            "--ledger-path",
            path,
        ],
    )

    assert result.exit_code == 0, result.output
    assert ledger.calls == [("http://127.0.0.1:8545", 0, path)]
    assert execution.runs[0].sender is ledger.instances[0]


def test_ledger_path_and_index_are_rejected_together(monkeypatch):
    ledger = _install_fake_ledger_module(monkeypatch)

    result = CliRunner().invoke(
        cli,
        [
            "--chain",
            "local",
            "--ledger",
            "1",
            "--ledger-path",
            "m/44'/60'/1'/0/0",
        ],
    )

    assert result.exit_code == 2
    assert "--ledger-path and --ledger cannot be used together" in result.output
    assert ledger.calls == []


@pytest.mark.parametrize(
    "ledger_args",
    [
        ["--ledger", "1"],
        ["--ledger-path", "m/44'/60'/1'/0/0"],
    ],
)
def test_safe_and_ledger_backends_are_rejected_together(ledger_args):
    result = CliRunner().invoke(
        cli,
        [
            "--chain",
            "local",
            "--fork",
            "--safe",
            DEPLOYER,
            *ledger_args,
        ],
    )

    assert result.exit_code == 2
    assert "--safe cannot be used with --ledger or --ledger-path" in result.output


def test_local_chain_loads_without_ledger_modules(monkeypatch):
    # Import a fresh copy while explicitly making the hardware-only module
    # unavailable. This catches both a top-level import and an import reached by
    # the ordinary local-account branch.
    monkeypatch.setitem(sys.modules, "scripts.utils.ledger_account", None)
    spec = importlib.util.spec_from_file_location(
        "migrate_without_ledger_dependencies",
        MIGRATE_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    execution = _stub_migration_execution(monkeypatch, module)
    local_account = SimpleNamespace(address=DEPLOYER)
    monkeypatch.setattr(module, "get_account", lambda _name: local_account)

    result = CliRunner().invoke(module.cli, ["--chain", "local"])

    assert result.exit_code == 0, result.output
    assert execution.runs[0].sender is local_account


def test_robinhood_private_key_backend_fails_closed(monkeypatch):
    account_loads = []
    monkeypatch.delenv("DEPLOYER_PRIVATE_KEY", raising=False)
    monkeypatch.setattr(
        migrate_module,
        "get_account",
        lambda name: account_loads.append(name),
    )

    result = CliRunner().invoke(
        cli,
        [
            "--chain",
            "robinhood-mainnet",
            "--blueprint",
            "robinhood",
            "--rpc",
            "http://127.0.0.1:8545",
            "--start-timestamp",
            "0000",
        ],
    )

    assert result.exit_code == 2
    assert "DEPLOYER_PRIVATE_KEY must be set for robinhood-mainnet" in result.output
    assert account_loads == []


def test_robinhood_chain_rejects_base_blueprint():
    result = CliRunner().invoke(
        cli,
        [
            "--chain",
            "robinhood-mainnet",
            "--blueprint",
            "base",
            "--rpc",
            "http://127.0.0.1:1",
        ],
    )

    assert result.exit_code == 2
    assert (
        "--chain robinhood-mainnet requires --blueprint robinhood; got 'base'"
        in result.output
    )


def test_robinhood_chain_requires_rpc_environment(monkeypatch):
    monkeypatch.delenv("ROBINHOOD_MAINNET_RPC_URL", raising=False)

    result = CliRunner().invoke(
        cli,
        [
            "--chain",
            "robinhood-mainnet",
            "--blueprint",
            "robinhood",
        ],
    )

    assert result.exit_code == 2
    assert "ROBINHOOD_MAINNET_RPC_URL must be set" in result.output


def test_robinhood_chain_requires_explicit_start_timestamp():
    result = CliRunner().invoke(
        cli,
        [
            "--chain",
            "robinhood-mainnet",
            "--blueprint",
            "robinhood",
            "--rpc",
            "http://127.0.0.1:1",
        ],
    )

    assert result.exit_code == 2
    assert (
        "--chain robinhood-mainnet requires an explicit --start-timestamp"
        in result.output
    )


def test_robinhood_chain_rejects_positional_log_replay():
    result = CliRunner().invoke(
        cli,
        [
            "--chain",
            "robinhood-mainnet",
            "--blueprint",
            "robinhood",
            "--rpc",
            "http://127.0.0.1:1",
            "--start-timestamp",
            "0000",
            "--is-retry",
        ],
    )

    assert result.exit_code == 2
    assert "--is-retry is disabled for robinhood-mainnet" in result.output


@pytest.mark.parametrize("start_timestamp", ["0000", "0001"])
def test_robinhood_wrong_chain_never_reaches_migration_runner(
    monkeypatch,
    start_timestamp,
):
    run_calls = []
    monkeypatch.setenv("DEPLOYER_PRIVATE_KEY", "test-only")

    class FakeMigrationRunner:
        def __init__(self, *_args, **_kwargs):
            pass

        def run(self, *_args, **_kwargs):
            run_calls.append(True)
            return 0

    fake_env = SimpleNamespace(
        eoa=None,
        set_balance=lambda *_args, **_kwargs: None,
    )

    @contextmanager
    def fake_fork(*_args, **_kwargs):
        yield fake_env

    def reject_wrong_chain(*_args, **_kwargs):
        raise RuntimeError("wrong chain id: expected 4663, got 8453")

    monkeypatch.setattr(migrate_module, "MigrationRunner", FakeMigrationRunner)
    monkeypatch.setattr(migrate_module, "load_vyper_files", lambda: {})
    monkeypatch.setattr(
        migrate_module,
        "get_account",
        lambda _name: SimpleNamespace(address=DEPLOYER),
    )
    monkeypatch.setattr(migrate_module.boa, "fork", fake_fork)
    monkeypatch.setattr(
        migrate_module.boa.deployments,
        "set_deployments_db",
        lambda _db: None,
    )
    monkeypatch.setattr(
        migrate_module,
        "assert_chain_id",
        reject_wrong_chain,
    )

    result = CliRunner().invoke(
        cli,
        [
            "--chain",
            "robinhood-mainnet",
            "--blueprint",
            "robinhood",
            "--rpc",
            "http://127.0.0.1:1",
            "--fork",
            "--start-timestamp",
            start_timestamp,
        ],
    )

    assert result.exit_code == 1
    assert isinstance(result.exception, RuntimeError)
    assert str(result.exception) == "wrong chain id: expected 4663, got 8453"
    assert run_calls == []


@pytest.mark.parametrize(
    ("fork_args", "expected_history_environment"),
    [([], "release-v1"), (["--fork"], "release-v1-fork")],
)
def test_fork_and_production_use_separate_migration_history_paths(
    monkeypatch,
    fork_args,
    expected_history_environment,
):
    runner_paths = []
    chain_checks = []
    monkeypatch.setenv("DEPLOYER_PRIVATE_KEY", "test-only")

    class FakeMigrationRunner:
        def __init__(self, migrations_dir, history_dir, _files):
            runner_paths.append((migrations_dir, history_dir))

        def run(self, *_args, **_kwargs):
            return 0

    fake_env = SimpleNamespace(
        eoa=None,
        set_balance=lambda *_args, **_kwargs: None,
        add_account=lambda *_args, **_kwargs: None,
    )

    @contextmanager
    def fake_environment(*_args, **_kwargs):
        yield fake_env

    monkeypatch.setattr(migrate_module, "MigrationRunner", FakeMigrationRunner)
    monkeypatch.setattr(
        migrate_module,
        "assert_chain_id",
        lambda expected, *, env: chain_checks.append((expected, env)),
    )
    monkeypatch.setattr(migrate_module, "load_vyper_files", lambda: {})
    monkeypatch.setattr(
        migrate_module,
        "get_account",
        lambda _name: SimpleNamespace(address=DEPLOYER),
    )
    monkeypatch.setattr(migrate_module.boa, "fork", fake_environment)
    monkeypatch.setattr(migrate_module.boa, "set_network_env", fake_environment)
    monkeypatch.setattr(
        migrate_module.boa.deployments,
        "set_deployments_db",
        lambda _db: None,
    )

    result = CliRunner().invoke(
        cli,
        [
            "--chain",
            "robinhood-mainnet",
            "--blueprint",
            "robinhood",
            "--rpc",
            "http://127.0.0.1:1",
            "--environment",
            "release-v1",
            "--start-timestamp",
            "0000",
            *fork_args,
        ],
    )

    assert result.exit_code == 0, result.output
    assert runner_paths == [
        (
            "./migrations/robinhood-mainnet/release-v1",
            "./migration_history/robinhood-mainnet/"
            f"{expected_history_environment}",
        )
    ]
    assert chain_checks == [(4_663, fake_env)]
