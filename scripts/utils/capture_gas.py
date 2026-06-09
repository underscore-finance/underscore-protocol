#!/usr/bin/env python3
"""
Capture representative Boa gas usage from pytest flows.

The default target set is intentionally workflow-oriented: wallet swaps/actions,
agent/signature paths, cheque paths, earn vault flows, and leverage vault flows.
It records per-test Boa gas usage after fixtures are prepared, so deployment/setup
gas does not drown out the transaction paths under test.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import boa
import pytest


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "tools" / "gas-baseline-pre-cleanup.json"
DEFAULT_TARGETS = [
    "tests/core/userWallet/test_user_wallet.py::test_transfer_eth_native_token",
    "tests/core/userWallet/test_user_wallet_swap.py",
    "tests/core/userWallet/test_user_wallet_debt.py",
    "tests/core/agent/test_agent_batch_actions.py",
    "tests/core/agent/test_agent_signatures.py",
    "tests/core/walletBackpack/chequeBook/test_cheque_mgmt.py",
    "tests/vaults/earn/test_earn_vault_actions.py",
    "tests/vaults/leverage/test_levg_vault_wallet_actions.py",
    "tests/vaults/leverage/test_levg_erc4626_vault.py",
]


@dataclass
class GasRecord:
    nodeid: str
    gas: int = 0
    outcome: str = "unknown"


@dataclass(eq=False)
class GasPlugin:
    records: dict[str, GasRecord] = field(default_factory=dict)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item):
        gas_before = int(boa.env.get_gas_used())
        outcome = yield
        gas_after = int(boa.env.get_gas_used())
        gas_used = max(0, gas_after - gas_before)
        record = self.records.setdefault(item.nodeid, GasRecord(nodeid=item.nodeid))
        record.gas = gas_used
        if outcome.excinfo is None:
            record.outcome = "passed"
        else:
            record.outcome = "failed"

    def pytest_runtest_logreport(self, report):
        if report.when != "call" or report.nodeid not in self.records:
            return
        self.records[report.nodeid].outcome = report.outcome


def git_value(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def write_report(output: Path, targets: list[str], exit_code: int, plugin: GasPlugin) -> None:
    records = [record.__dict__ for record in plugin.records.values()]
    records.sort(key=lambda item: item["nodeid"])
    total_gas = sum(item["gas"] for item in records)
    payload = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "branch": git_value("branch", "--show-current"),
            "commit": git_value("rev-parse", "HEAD"),
            "exit_code": exit_code,
            "targets": targets,
            "test_count": len(records),
            "total_gas": total_gas,
            "command": "python scripts/utils/capture_gas.py",
        },
        "tests": records,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture representative pytest gas usage.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--fork", default="local", choices=["local", "mainnet", "base"])
    parser.add_argument("targets", nargs="*", default=DEFAULT_TARGETS)
    args, passthrough = parser.parse_known_args()

    plugin = GasPlugin()
    pytest_args = ["--fork", args.fork, "-q", *args.targets, *passthrough]
    exit_code = pytest.main(pytest_args, plugins=[plugin])
    write_report(args.output, args.targets, exit_code, plugin)
    print(f"wrote gas report: {args.output}")
    print(f"tests captured: {len(plugin.records)}")
    print(f"total gas: {sum(record.gas for record in plugin.records.values())}")
    return int(exit_code)


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
