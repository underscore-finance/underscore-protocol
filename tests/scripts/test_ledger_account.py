import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.utils import ledger_account


DEPLOYER = "0x14051A647C2B647363739ccfD4B008AfEeb8FD8e"


@pytest.fixture(scope="session")
def undy_hq():
    return None


@pytest.fixture(scope="session")
def wallet_backpack():
    return None


def test_common_derivation_path_scan_covers_all_three_conventions():
    paths = list(ledger_account.iter_ledger_derivation_paths())

    assert len(paths) == 15
    assert ("BIP44 address index", 1, "44'/60'/0'/0/1") in paths
    assert ("Ledger Live account", 1, "44'/60'/1'/0/0") in paths
    assert ("Ledger Legacy", 1, "44'/60'/0'/1") in paths


def test_ledger_utility_import_does_not_load_migration_cli():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import scripts.utils.ledger_account; "
            "assert 'scripts.migrate' not in sys.modules",
        ],
        cwd=Path(__file__).parents[2],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("44'/60'/0'/0/1", "44'/60'/0'/0/1"),
        ("m/44'/60'/1'/0/0", "44'/60'/1'/0/0"),
        ("m/44'/60'/0'/1", "44'/60'/0'/1"),
    ],
)
def test_ledger_path_normalization_accepts_copyable_common_paths(given, expected):
    assert ledger_account.normalize_ledger_path(given) == expected


@pytest.mark.parametrize("path", ["", "m/", "m/44'/60'/not-an-index"])
def test_ledger_path_normalization_rejects_invalid_paths(path):
    with pytest.raises(ValueError, match="Invalid Ledger derivation path"):
        ledger_account.normalize_ledger_path(path)


def test_explicit_derivation_path_overrides_integer_index(monkeypatch):
    monkeypatch.setattr(
        ledger_account.LedgerAccount,
        "_connect_ledger",
        lambda self: setattr(self, "address", DEPLOYER),
    )

    account = ledger_account.LedgerAccount(
        "http://127.0.0.1:8545",
        account_index=4,
        derivation_path="m/44'/60'/1'/0/0",
    )

    assert account._sender_path == "44'/60'/1'/0/0"
    assert "derivation_path=m/44'/60'/1'/0/0" in repr(account)


def test_default_integer_path_behavior_is_unchanged(monkeypatch):
    monkeypatch.setattr(
        ledger_account.LedgerAccount,
        "_connect_ledger",
        lambda self: setattr(self, "address", DEPLOYER),
    )

    account = ledger_account.LedgerAccount(
        "http://127.0.0.1:8545",
        account_index=3,
    )

    assert account._sender_path == "44'/60'/0'/0/3"


def test_ledger_connection_redacts_rpc_path_and_query(capsys):
    secret = "live-alchemy-key"
    account = ledger_account.LedgerAccount.__new__(ledger_account.LedgerAccount)
    account.account_index = 0
    account._sender_path = "44'/60'/0'/0/0"
    account.get_address = lambda: DEPLOYER
    account.w3 = SimpleNamespace(
        eth=SimpleNamespace(
            chain_id=4_663,
            get_balance=lambda _address: 1,
        ),
        provider=SimpleNamespace(
            endpoint_uri=f"https://rpc.example/v2/{secret}?token={secret}"
        ),
        from_wei=lambda value, _unit: value,
    )

    account._connect_ledger()

    output = capsys.readouterr().out
    assert "https://rpc.example" in output
    assert secret not in output
    assert "/v2/" not in output


def test_ledger_network_error_does_not_print_provider_exception(capsys):
    secret = "credential-in-provider-error"

    class FailingEth:
        @property
        def chain_id(self):
            raise RuntimeError(f"request failed at https://rpc.example/{secret}")

    account = ledger_account.LedgerAccount.__new__(ledger_account.LedgerAccount)
    account.account_index = 0
    account._sender_path = "44'/60'/0'/0/0"
    account.get_address = lambda: DEPLOYER
    account.w3 = SimpleNamespace(
        eth=FailingEth(),
        provider=SimpleNamespace(endpoint_uri=f"https://rpc.example/{secret}"),
    )

    account._connect_ledger()

    output = capsys.readouterr().out
    assert secret not in output
    assert "details redacted" in output
