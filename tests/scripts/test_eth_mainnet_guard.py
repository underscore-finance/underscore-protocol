import os

import click
import pytest

# `scripts.migrate` reads ETHERSCAN_API_KEY at import time.
os.environ.setdefault("ETHERSCAN_API_KEY", "test")

from scripts.migrate import (  # noqa: E402
    ALLOW_ETH_MAINNET_ENV,
    ETH_MAINNET_CHAIN_ID,
    assert_eth_mainnet_allowed,
)

BASE_RPC = "https://base-mainnet.example/v2/key"
ETH_RPC = "https://eth-mainnet.example/v2/key"


@pytest.fixture(autouse=True)
def _no_override(monkeypatch):
    monkeypatch.delenv(ALLOW_ETH_MAINNET_ENV, raising=False)


@pytest.fixture
def chain_id(monkeypatch):
    """Stub the chain id probe so tests never touch the network."""
    def _set(value):
        monkeypatch.setattr(
            "scripts.migrate.resolve_chain_id", lambda *_a, **_k: value)
    return _set


def test_blocks_explicit_eth_mainnet_without_probing(chain_id):
    chain_id(None)  # name alone must be enough
    with pytest.raises(click.ClickException):
        assert_eth_mainnet_allowed("eth-mainnet", ETH_RPC, fork=False)


def test_blocks_when_rpc_is_mainnet_despite_innocent_chain_name(chain_id):
    """`--rpc` decides where we connect, so `--chain` alone is not trustworthy."""
    chain_id(ETH_MAINNET_CHAIN_ID)
    with pytest.raises(click.ClickException):
        assert_eth_mainnet_allowed("base-mainnet", ETH_RPC, fork=False)


def test_fails_closed_when_chain_id_is_unverifiable(chain_id):
    chain_id(None)
    with pytest.raises(click.ClickException):
        assert_eth_mainnet_allowed("base-mainnet", BASE_RPC, fork=False)


def test_allows_base_mainnet(chain_id):
    chain_id(8453)
    assert_eth_mainnet_allowed("base-mainnet", BASE_RPC, fork=False)


def test_allows_local_and_forks_without_probing(chain_id):
    chain_id(None)
    assert_eth_mainnet_allowed("local", "boa", fork=False)
    assert_eth_mainnet_allowed("eth-mainnet", ETH_RPC, fork=True)


@pytest.mark.parametrize("chain,probe", [
    ("eth-mainnet", ETH_MAINNET_CHAIN_ID),
    ("base-mainnet", None),
])
def test_override_env_permits_the_run(monkeypatch, chain_id, chain, probe):
    chain_id(probe)
    monkeypatch.setenv(ALLOW_ETH_MAINNET_ENV, "1")
    assert_eth_mainnet_allowed(chain, ETH_RPC, fork=False)
