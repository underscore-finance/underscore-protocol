from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

import scripts.migrate as migrate_module
from scripts.migrate import cli


DEPLOYER = "0x14051A647C2B647363739ccfD4B008AfEeb8FD8e"


# CLI unit tests stub their execution environments and do not need the repo's
# full protocol deployment from the two global autouse fixtures.
@pytest.fixture(scope="session")
def undy_hq():
    return None


@pytest.fixture(scope="session")
def wallet_backpack():
    return None


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
