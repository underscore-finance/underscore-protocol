from types import SimpleNamespace

import pytest

from scripts import ledger_signing_smoke as smoke
from scripts.utils import ledger_account


DEPLOYER = "0x14051A647C2B647363739ccfD4B008AfEeb8FD8e"
LEDGER_LIVE_ACCOUNT_ONE = "44'/60'/1'/0/0"


@pytest.fixture(scope="session")
def undy_hq():
    return None


@pytest.fixture(scope="session")
def wallet_backpack():
    return None


class FakeEth:
    def __init__(self, chain_id=4_663, latest=0, pending=0):
        self.chain_id = chain_id
        self.nonces = {"latest": latest, "pending": pending}
        self.calls = []

    def get_transaction_count(self, address, block_identifier):
        self.calls.append((address, block_identifier))
        return self.nonces[block_identifier]


def test_largest_initcode_covers_every_rh_core_create_and_measures_vault_registry():
    assert len(smoke.LARGEST_ARTIFACTS) == 25
    assert smoke._largest_initcode_size() == 24_376


def test_expected_deployer_check_fails_closed():
    smoke._require_expected_deployer(DEPLOYER.lower())

    with pytest.raises(SystemExit, match="LEDGER_SMOKE_DEPLOYER_MISMATCH"):
        smoke._require_expected_deployer("0x" + "12" * 20)


def test_real_chain_nonce_check_requires_latest_and_pending_zero():
    eth = FakeEth()

    assert smoke._require_pristine_deployer(SimpleNamespace(eth=eth), DEPLOYER) == (
        0,
        0,
    )
    assert eth.calls == [(DEPLOYER, "latest"), (DEPLOYER, "pending")]


@pytest.mark.parametrize(
    ("chain_id", "latest", "pending", "message"),
    [
        (8453, 0, 0, "LEDGER_SMOKE_CHAIN_MISMATCH"),
        (4_663, 1, 1, "LEDGER_SMOKE_DEPLOYER_NONCE_MISMATCH"),
        (4_663, 0, 1, "LEDGER_SMOKE_DEPLOYER_NONCE_MISMATCH"),
    ],
)
def test_real_chain_nonce_check_fails_closed(chain_id, latest, pending, message):
    w3 = SimpleNamespace(eth=FakeEth(chain_id, latest, pending))

    with pytest.raises(SystemExit, match=message):
        smoke._require_pristine_deployer(w3, DEPLOYER)


def test_discovery_reports_nonzero_live_nonce_without_blocking_path_result(
    monkeypatch,
    capsys,
):
    path = "44'/60'/1'/0/0"
    w3 = SimpleNamespace(eth=FakeEth(latest=12, pending=13))
    monkeypatch.setattr("sys.argv", ["ledger_signing_smoke.py", "--discover-path"])
    monkeypatch.setattr(smoke, "_discover_deployer_path", lambda: (path, DEPLOYER))
    monkeypatch.setattr(smoke, "_real_robinhood_web3", lambda: w3)
    monkeypatch.setattr(
        smoke,
        "_require_pristine_deployer",
        lambda *_args: pytest.fail("discovery must not require a pristine nonce"),
    )

    assert smoke.main() == 0

    output = capsys.readouterr().out
    assert "latest=12 pending=13" in output
    assert "Path discovery still passed" in output
    assert "LEDGER PATH DISCOVERY PASSED" in output


def test_path_discovery_scans_table_and_resolves_ledger_live_account_one(
    monkeypatch,
    capsys,
):
    import ledgereth.accounts

    requested_paths = []
    device = SimpleNamespace(closed=False)
    device.close = lambda: setattr(device, "closed", True)

    def fake_get_account_by_path(path, *, dongle):
        assert dongle is device
        requested_paths.append(path)
        address = DEPLOYER if path == LEDGER_LIVE_ACCOUNT_ONE else "0x" + "00" * 20
        return SimpleNamespace(address=address)

    monkeypatch.setattr(ledger_account, "get_dongle", lambda: device)
    monkeypatch.setattr(
        ledgereth.accounts,
        "get_account_by_path",
        fake_get_account_by_path,
    )

    path, address = smoke._discover_deployer_path()

    output = capsys.readouterr().out
    assert path == LEDGER_LIVE_ACCOUNT_ONE
    assert address == DEPLOYER
    assert len(requested_paths) == 15
    assert device.closed
    assert "Convention" in output
    assert "BIP44 address index" in output
    assert "Ledger Live account" in output
    assert "Ledger Legacy" in output
    assert f"m/{LEDGER_LIVE_ACCOUNT_ONE}" in output
    assert f'--ledger-path "m/{LEDGER_LIVE_ACCOUNT_ONE}"' in output


def test_path_discovery_fails_closed_when_pinned_deployer_is_not_found(
    monkeypatch,
):
    import ledgereth.accounts

    device = SimpleNamespace(close=lambda: None)
    monkeypatch.setattr(ledger_account, "get_dongle", lambda: device)
    monkeypatch.setattr(
        ledgereth.accounts,
        "get_account_by_path",
        lambda _path, *, dongle: SimpleNamespace(address="0x" + "00" * 20),
    )

    with pytest.raises(SystemExit, match="LEDGER_PATH_NOT_FOUND"):
        smoke._discover_deployer_path()


def test_path_discovery_fails_closed_when_distinct_paths_match(
    monkeypatch,
):
    import ledgereth.accounts

    matching_paths = {
        "44'/60'/0'/0/1",
        "44'/60'/1'/0/0",
    }
    device = SimpleNamespace(close=lambda: None)
    monkeypatch.setattr(ledger_account, "get_dongle", lambda: device)
    monkeypatch.setattr(
        ledgereth.accounts,
        "get_account_by_path",
        lambda path, *, dongle: SimpleNamespace(
            address=DEPLOYER if path in matching_paths else "0x" + "00" * 20
        ),
    )

    with pytest.raises(SystemExit, match="LEDGER_PATH_AMBIGUOUS"):
        smoke._discover_deployer_path()
