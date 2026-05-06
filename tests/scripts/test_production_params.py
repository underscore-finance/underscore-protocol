import json
from pathlib import Path

import pytest

from scripts.params.production_params import classify_sender_by_abi

ROOT = Path(__file__).resolve().parents[2]


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
