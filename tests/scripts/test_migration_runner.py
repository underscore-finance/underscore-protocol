from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.utils.migration_runner as migration_runner_module
from scripts.utils.migration_runner import MigrationRunner


pytestmark = pytest.always


@pytest.fixture(scope="session")
def undy_hq():
    return None


@pytest.fixture(scope="session")
def wallet_backpack():
    return None


def test_latest_manifest_timestamp_ignores_current_alias(tmp_path: Path):
    (tmp_path / "current-manifest.json").write_text("{}")
    (tmp_path / "0004-manifest.json").write_text("{}")
    (tmp_path / "0009-manifest.json").write_text("{}")
    (tmp_path / "notes-manifest.json").write_text("{}")

    runner = MigrationRunner("unused", str(tmp_path), {})

    assert runner._latest_manifest_timestamp() == "0009"


def test_latest_manifest_timestamp_returns_none_for_alias_only(tmp_path: Path):
    (tmp_path / "current-manifest.json").write_text("{}")

    runner = MigrationRunner("unused", str(tmp_path), {})

    assert runner._latest_manifest_timestamp() is None


def test_robinhood_runner_rejects_wrong_chain_before_loading_migrations(
    monkeypatch,
    tmp_path: Path,
):
    runner = MigrationRunner("unused", str(tmp_path), {})
    migration_loads = []

    def wrong_chain(expected_chain_id):
        assert expected_chain_id == 4_663
        raise RuntimeError("wrong chain id: expected 4663, got 8453")

    monkeypatch.setattr(migration_runner_module, "assert_chain_id", wrong_chain)
    monkeypatch.setattr(
        runner,
        "_migrations",
        lambda *_args, **_kwargs: migration_loads.append(True),
    )

    with pytest.raises(
        RuntimeError,
        match="wrong chain id: expected 4663, got 8453",
    ):
        runner.run(
            SimpleNamespace(chain="robinhood-mainnet"),
            start_timestamp="0001",
        )

    assert migration_loads == []
