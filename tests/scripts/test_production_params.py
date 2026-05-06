import importlib
import json
import sys
from pathlib import Path

import pytest

from scripts.params.production_params import classify_sender_by_abi

ROOT = Path(__file__).resolve().parents[2]
PARAM_SCRIPT_MODULES = (
    "deployments",
    "lego_params",
    "production_params",
    "regenerate_defaults",
    "vaults_params",
)


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


@pytest.mark.parametrize("module_name", PARAM_SCRIPT_MODULES)
def test_params_scripts_support_package_imports(module_name):
    assert importlib.import_module(f"scripts.params.{module_name}") is not None


@pytest.mark.parametrize("module_name", PARAM_SCRIPT_MODULES)
def test_params_scripts_support_standalone_imports(module_name, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts" / "params"))
    sys.modules.pop(module_name, None)
    assert importlib.import_module(module_name) is not None
