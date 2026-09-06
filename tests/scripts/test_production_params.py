import ast
import importlib
import json
import re
import sys
from pathlib import Path

import pytest

from config.BluePrint import BLOCK_TIME_CONSTANTS, PARAMS
from scripts.params.production_params import classify_sender_by_abi

ROOT = Path(__file__).resolve().parents[2]
PARAM_SCRIPT_MODULES = (
    "deployments",
    "lego_params",
    "production_params",
    "regenerate_defaults",
    "vaults_params",
)

DEFAULTS_FILE_BY_NETWORK = {
    "base": "DefaultsBase.vy",
    "local": "DefaultsLocal.vy",
    "robinhood": "DefaultsRobinhood.vy",
}

VYPER_TIME_CONSTANTS = {
    network: {
        name: value
        for name, value in clock.items()
        if name.endswith("_IN_BLOCKS")
    }
    for network, clock in BLOCK_TIME_CONSTANTS.items()
}


def _eval_vyper_uint_expr(expr: str, network: str) -> int:
    constants = VYPER_TIME_CONSTANTS[network]

    def eval_node(node: ast.AST) -> int:
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return node.value
        if isinstance(node, ast.Name) and node.id in constants:
            return constants[node.id]
        if isinstance(node, ast.BinOp):
            left = eval_node(node.left)
            right = eval_node(node.right)
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.FloorDiv):
                return left // right
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
        raise AssertionError(f"Unsupported Vyper uint expression in deploy defaults: {expr}")

    return eval_node(ast.parse(expr, mode="eval").body)


def _read_default_max_key_action_timelock(network: str) -> int:
    defaults_path = ROOT / "contracts" / "config" / DEFAULTS_FILE_BY_NETWORK[network]
    source = defaults_path.read_text()
    match = re.search(r"maxKeyActionTimeLock\s*=\s*([^,\n]+)", source)
    assert match, f"{defaults_path} must define maxKeyActionTimeLock"
    return _eval_vyper_uint_expr(match.group(1).strip(), network)


@pytest.mark.parametrize(
    ("abi_name", "expected_type"),
    [
        ("AgentSenderGeneric", "AgentSenderGeneric"),
        ("AgentSenderSpecial", "AgentSenderSpecial"),
        ("AgentSenderSpecialAdmin", "AgentSenderSpecialAdmin"),
    ],
)
def test_classify_sender_by_abi_identifies_agent_sender_types(abi_name, expected_type):
    abi = json.loads((ROOT / "scripts" / "abis" / f"{abi_name}.json").read_text())

    assert classify_sender_by_abi(abi) == expected_type


@pytest.mark.parametrize("network", ("base", "local", "robinhood"))
def test_max_key_action_timelock_fits_cheque_unlock_and_expiry_windows(network):
    """Deploy defaults must not exceed ChequeBook's max unlock/expiry bounds."""
    max_key_action_timelock = _read_default_max_key_action_timelock(network)
    cheque_params = PARAMS[network]

    assert max_key_action_timelock <= cheque_params["CHEQUE_MAX_UNLOCK_BLOCKS"]
    assert max_key_action_timelock <= cheque_params["CHEQUE_MAX_EXPIRY_BLOCKS"]


@pytest.mark.parametrize("module_name", PARAM_SCRIPT_MODULES)
def test_params_scripts_support_package_imports(module_name):
    assert importlib.import_module(f"scripts.params.{module_name}") is not None


@pytest.mark.parametrize("module_name", PARAM_SCRIPT_MODULES)
def test_params_scripts_support_standalone_imports(module_name, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts" / "params"))
    sys.modules.pop(module_name, None)
    assert importlib.import_module(module_name) is not None
