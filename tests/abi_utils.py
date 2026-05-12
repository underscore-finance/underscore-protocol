import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def count_abi_arities(path, name):
    abi_path = Path(path)
    if not abi_path.is_absolute():
        abi_path = REPO_ROOT / abi_path
    with open(abi_path) as f:
        abi = json.load(f)
    return sorted(
        len(item["inputs"])
        for item in abi
        if item.get("type") == "function" and item.get("name") == name
    )
