"""Prove a connected Ledger will sign a Robinhood deployment transaction.

The normal ``--fork`` migration gate cannot prove this. Titanoboa executes
against forked state in-process, so it never serialises, signs, or broadcasts a
transaction and the device is never asked for a signature.

This smoke test checks, with one transaction confirmation, that:

* one common Ledger path derives Underscore's pinned Robinhood deployer;
* that deployer still has latest and pending nonce zero on Robinhood;
* the Ethereum app accepts chain id 4663 and a contract creation;
* a real-size deployment payload survives roughly 95 full APDU chunks; and
* the signed transaction is accepted and mined by a local Robinhood fork.

No transaction is sent to Robinhood. The real RPC is used only for read-only
chain-id and nonce checks and as anvil's fork source, and its URL is never
printed because it may contain a provider key.

Discover the correct path without signing::

    PYTHONPATH=. .venv/bin/python scripts/ledger_signing_smoke.py \
      --discover-path

Then run the full smoke in two shells::

    anvil --fork-url "$ROBINHOOD_MAINNET_RPC_URL" --chain-id 4663 \
      --port 8545 --silent
    PYTHONPATH=. .venv/bin/python scripts/ledger_signing_smoke.py

Or let this script start and stop anvil itself::

    PYTHONPATH=. .venv/bin/python scripts/ledger_signing_smoke.py \
      --manage-anvil
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.migrate import ROBINHOOD_CHAIN_ID
from scripts.utils.robinhood_runtime import ROBINHOOD_UNDY_HQ_DEPLOYER


ANVIL_RPC = "http://127.0.0.1:8545"

# Initcode that CODECOPYs 10 bytes from offset 12 and returns them as runtime.
# Anything appended past byte 22 is neither executed nor copied. This lets the
# smoke test sign at real deployment size without executing a production
# contract or manufacturing valid constructor state for it.
SMOKE_INITCODE = "600a600c600039600a6000f3600360005260206000f3"

# Every direct CREATE in Robinhood migrations 0000-0011. True means the
# migration calls deploy_as_blueprint; False means an ordinary CREATE whose
# constructor calldata is included in the signed initcode measurement.
LARGEST_ARTIFACTS = (
    ("contracts/core/userWallet/UserWallet.vy", True),
    ("contracts/core/userWallet/UserWalletConfig.vy", True),
    ("contracts/core/agent/AgentWrapper.vy", True),
    ("contracts/config/DefaultsRobinhood.vy", False),
    ("contracts/registries/UndyHq.vy", False),
    ("contracts/data/Ledger.vy", False),
    ("contracts/data/MissionControl.vy", False),
    ("contracts/registries/LegoBook.vy", False),
    ("contracts/registries/Switchboard.vy", False),
    ("contracts/config/SwitchboardAlpha.vy", False),
    ("contracts/config/SwitchboardBravo.vy", False),
    ("contracts/core/Hatchery.vy", False),
    ("contracts/core/LootDistributor.vy", False),
    ("contracts/core/Appraiser.vy", False),
    ("contracts/registries/WalletBackpack.vy", False),
    ("contracts/core/walletBackpack/Kernel.vy", False),
    ("contracts/core/walletBackpack/Sentinel.vy", False),
    ("contracts/core/walletBackpack/HighCommand.vy", False),
    ("contracts/core/walletBackpack/Paymaster.vy", False),
    ("contracts/core/walletBackpack/ChequeBook.vy", False),
    ("contracts/core/walletBackpack/Migrator.vy", False),
    ("contracts/core/userWallet/ActionDataProvider.vy", False),
    ("contracts/core/Billing.vy", False),
    ("contracts/registries/VaultRegistry.vy", False),
    ("contracts/registries/Helpers.vy", False),
)

_ZERO_ADDRESS = "0x" + "00" * 20


def _require_robinhood_chain_id(chain_id: int) -> None:
    if chain_id != ROBINHOOD_CHAIN_ID:
        raise SystemExit(
            "LEDGER_SMOKE_CHAIN_MISMATCH "
            f"expected={ROBINHOOD_CHAIN_ID} observed={chain_id}"
        )


def _require_expected_deployer(address: str) -> None:
    if address.lower() != ROBINHOOD_UNDY_HQ_DEPLOYER.lower():
        raise SystemExit(
            "LEDGER_SMOKE_DEPLOYER_MISMATCH "
            f"expected={ROBINHOOD_UNDY_HQ_DEPLOYER} observed={address}"
        )


def _discover_deployer_path() -> tuple[str, str]:
    """Scan common Ledger paths and resolve the pinned deployer without signing."""
    from ledgereth.accounts import get_account_by_path

    from scripts.utils.ledger_account import (
        get_dongle,
        iter_ledger_derivation_paths,
    )

    rows = []
    failures = []
    device = get_dongle()
    try:
        for convention, index, path in iter_ledger_derivation_paths():
            try:
                address = str(get_account_by_path(path, dongle=device).address)
            except Exception as error:
                address = f"<error: {type(error).__name__}>"
                failures.append((path, type(error).__name__))
            rows.append((convention, index, path, address))
    finally:
        device.close()

    print("\n  Ledger derivation-path discovery (read-only; no prompt):")
    print(f"  {'Convention':<21} {'N':>2}  {'Derivation path':<22} Address")
    print(f"  {'-' * 21} {'-' * 2}  {'-' * 22} {'-' * 42}")
    for convention, index, path, address in rows:
        print(f"  {convention:<21} {index:>2}  {'m/' + path:<22} {address}")

    if failures:
        raise SystemExit(
            "LEDGER_PATH_SCAN_INCOMPLETE "
            f"failed_rows={len(failures)}; no signing attempted"
        )

    matches = {}
    for convention, index, path, address in rows:
        if address.lower() == ROBINHOOD_UNDY_HQ_DEPLOYER.lower():
            match = matches.setdefault(path, {"address": address, "rows": []})
            match["rows"].append((convention, index))

    if not matches:
        raise SystemExit(
            "LEDGER_PATH_NOT_FOUND "
            f"expected={ROBINHOOD_UNDY_HQ_DEPLOYER}; scanned all three common "
            "Ethereum conventions at N=0..4. This device is not the pinned "
            "Base deployer, or its path is outside the scan; no signing attempted."
        )
    if len(matches) != 1:
        paths = ",".join(f"m/{path}" for path in matches)
        raise SystemExit(
            "LEDGER_PATH_AMBIGUOUS "
            f"expected={ROBINHOOD_UNDY_HQ_DEPLOYER} matched_paths={paths}; "
            "no signing attempted"
        )

    path, match = next(iter(matches.items()))
    labels = ", ".join(
        f"{convention} N={index}" for convention, index in match["rows"]
    )
    print(f"\n  Pinned deployer match    m/{path} ({labels})")
    print(f'  Migration signer flag   --ledger-path "m/{path}"')
    return path, match["address"]


def _read_robinhood_deployer_nonces(w3, address: str) -> tuple[int, int]:
    """Read latest and pending nonce from an authenticated Robinhood RPC."""
    _require_robinhood_chain_id(w3.eth.chain_id)
    latest = w3.eth.get_transaction_count(address, "latest")
    pending = w3.eth.get_transaction_count(address, "pending")
    return latest, pending


def _require_pristine_deployer(w3, address: str) -> tuple[int, int]:
    """Require the address-critical EOA to be unused on real Robinhood."""
    latest, pending = _read_robinhood_deployer_nonces(w3, address)
    if latest != 0 or pending != 0:
        raise SystemExit(
            "LEDGER_SMOKE_DEPLOYER_NONCE_MISMATCH "
            f"address={address} expected_latest=0 observed_latest={latest} "
            f"expected_pending=0 observed_pending={pending}"
        )
    return latest, pending


def _report_live_deployer_nonces(address: str) -> tuple[int, int] | None:
    """Report chain state without making device path discovery depend on it."""
    try:
        nonces = _read_robinhood_deployer_nonces(
            _real_robinhood_web3(),
            address,
        )
    except SystemExit as error:
        print(f"  real RH deployer nonce   unavailable ({error})")
        return None
    except Exception:
        print("  real RH deployer nonce   unavailable (RPC read failed)")
        return None

    print(
        "  real RH deployer nonce   "
        f"latest={nonces[0]} pending={nonces[1]}"
    )
    if nonces != (0, 0):
        print(
            "  NOTE: the deployer is not pristine. Path discovery still passed; "
            "reconcile live migration state before resuming."
        )
    return nonces


def _zero_value(param):
    """Build an ABI-encodable zero for a static constructor parameter."""
    typ = param["type"]
    if typ == "tuple":
        return tuple(_zero_value(component) for component in param["components"])
    if typ == "address":
        return _ZERO_ADDRESS
    if typ == "bool":
        return False
    if typ.startswith(("uint", "int")):
        return 0
    if typ.startswith("bytes") and typ != "bytes":
        return b"\0" * int(typ.removeprefix("bytes"))
    # Dynamic data cannot be measured from its ABI type alone. Fail closed if
    # a future ordinary CREATE introduces it instead of under-sizing the smoke.
    raise ValueError(f"dynamic or unsupported constructor type: {typ}")


def _artifact_initcode_size(path: str, blueprint: bool) -> int:
    import boa
    from boa.util.eip5202 import generate_blueprint_bytecode
    from eth_abi.abi import encode
    from eth_utils.abi import collapse_if_tuple
    from vyper.compiler.output import build_abi_output

    compiler_data = boa.load_partial(str(ROOT / path)).compiler_data
    bytecode = compiler_data.bytecode

    if blueprint:
        return len(generate_blueprint_bytecode(bytecode))

    abi = build_abi_output(compiler_data)
    constructor = next(
        (item for item in abi if item["type"] == "constructor"),
        None,
    )
    inputs = [] if constructor is None else constructor["inputs"]
    constructor_data = encode(
        [collapse_if_tuple(param) for param in inputs],
        [_zero_value(param) for param in inputs],
    )
    return len(bytecode) + len(constructor_data)


def _largest_initcode_size() -> int:
    """Measure the biggest transaction data field in the RH core deployment."""
    return max(
        _artifact_initcode_size(path, blueprint)
        for path, blueprint in LARGEST_ARTIFACTS
    )


def _rpc_url() -> str:
    url = os.environ.get("ROBINHOOD_MAINNET_RPC_URL")
    if not url:
        env = ROOT / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("ROBINHOOD_MAINNET_RPC_URL="):
                    url = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not url:
        raise SystemExit("ROBINHOOD_MAINNET_RPC_URL is not set")
    return url


def _real_robinhood_web3():
    from web3 import Web3

    w3 = Web3(Web3.HTTPProvider(_rpc_url()))
    try:
        connected = w3.is_connected()
    except Exception:
        raise SystemExit(
            "LEDGER_SMOKE_RPC_UNAVAILABLE could not reach Robinhood RPC"
        ) from None
    if not connected:
        raise SystemExit(
            "LEDGER_SMOKE_RPC_UNAVAILABLE could not reach Robinhood RPC"
        )
    return w3


@contextmanager
def _anvil(manage: bool):
    """Run anvil forked from Robinhood, or use one already listening."""
    if not manage:
        yield
        return
    if shutil.which("anvil") is None:
        raise SystemExit("anvil not found on PATH (install Foundry)")
    # Both streams are discarded because anvil may echo the credential-bearing
    # fork URL. Failures below deliberately report only a non-secret label.
    process = subprocess.Popen(
        [
            "anvil",
            "--fork-url",
            _rpc_url(),
            "--chain-id",
            str(ROBINHOOD_CHAIN_ID),
            "--port",
            "8545",
            "--silent",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        from web3 import Web3

        w3 = Web3(Web3.HTTPProvider(ANVIL_RPC))
        for _ in range(60):
            if process.poll() is not None:
                raise SystemExit("anvil exited during startup")
            try:
                if w3.is_connected():
                    break
            except Exception:
                pass
            time.sleep(0.5)
        else:
            raise SystemExit("anvil did not become ready")
        print("  anvil forked from Robinhood and listening")
        yield
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        print("  anvil stopped")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--discover-path",
        action="store_true",
        help=(
            "Scan the three common Ledger Ethereum derivation conventions, "
            "verify the pinned deployer, report live nonce, then exit without "
            "signing. A nonzero nonce does not block path discovery."
        ),
    )
    parser.add_argument(
        "--toy-payload",
        action="store_true",
        help=(
            "Sign 22 bytes instead of the real ~24KB deployment payload. "
            "Faster, but does not exercise large-payload APDU streaming."
        ),
    )
    parser.add_argument(
        "--manage-anvil",
        action="store_true",
        help="Start and stop anvil around the test instead of using a running one.",
    )
    args = parser.parse_args()

    resolved_path, resolved_address = _discover_deployer_path()
    if args.discover_path:
        _report_live_deployer_nonces(resolved_address)
        print("\nLEDGER PATH DISCOVERY PASSED (read-only; no signing attempted)")
        return 0

    try:
        real_nonces = _require_pristine_deployer(
            _real_robinhood_web3(),
            resolved_address,
        )
    except SystemExit:
        raise
    except Exception:
        raise SystemExit(
            "LEDGER_SMOKE_RPC_UNAVAILABLE could not read Robinhood deployer nonce"
        ) from None
    print(
        "  real RH deployer nonce   "
        f"latest={real_nonces[0]} pending={real_nonces[1]}"
    )

    from web3 import Web3

    with _anvil(args.manage_anvil):
        w3 = Web3(Web3.HTTPProvider(ANVIL_RPC))
        if not w3.is_connected():
            raise SystemExit(
                f"nothing listening on {ANVIL_RPC}. Start anvil first, or pass "
                "--manage-anvil."
            )
        chain_id = w3.eth.chain_id
        print(f"  anvil chain id           {chain_id}")
        _require_robinhood_chain_id(chain_id)

        from scripts.utils.ledger_account import LedgerAccount

        # Fund the resolved address on the fork before LedgerAccount performs
        # its balance diagnostic; otherwise that diagnostic correctly scans all
        # 15 common paths to help locate a funded account, duplicating discovery.
        w3.provider.make_request(
            "anvil_setBalance",
            [resolved_address, hex(10**18)],
        )

        print("\n  Connecting to Ledger (unlock it, open the Ethereum app)...")
        account = LedgerAccount(ANVIL_RPC, derivation_path=resolved_path)
        sender = account.address
        print(f"  resolved Ledger path     m/{resolved_path}")
        print(f"  resolved Ledger address  {sender}")
        _require_expected_deployer(sender)
        if sender.lower() != resolved_address.lower():
            raise SystemExit(
                "LEDGER_PATH_CHANGED address derived during signing setup does "
                "not match the discovery result; no transaction broadcast"
            )

        if args.toy_payload:
            data = "0x" + SMOKE_INITCODE
            print("  payload size             22 bytes (toy -- streaming untested)")
        else:
            print("\n  Measuring every initcode in RH migrations 0000-0011...")
            target = _largest_initcode_size()
            padding = max(0, target - len(SMOKE_INITCODE) // 2)
            data = "0x" + SMOKE_INITCODE + ("00" * padding)
            print(
                f"  payload size             {target:,} bytes "
                f"(~{target // 255} full APDU chunks)"
            )

        nonce = w3.eth.get_transaction_count(sender)
        base_fee = w3.eth.get_block("latest").get("baseFeePerGas") or 10**9
        tx = {
            "from": sender,
            "value": 0,
            "gas": 6_000_000,
            "nonce": nonce,
            "data": data,
            "chainId": chain_id,
            "maxPriorityFeePerGas": 10**9,
            "maxFeePerGas": base_fee * 2 + 10**9,
        }

        print(
            "\n  A CONTRACT CREATION is about to be sent to the device.\n"
            "  Confirm it on the Ledger. Chain 4663 is unknown to the Ethereum\n"
            "  app, so an unknown-network warning is expected. If it rejects\n"
            "  blind signing, enable Ethereum > Settings > Blind signing --\n"
            "  every RH core contract creation needs it. A full-size payload\n"
            "  streams in roughly 95 full chunks, so older firmware or app\n"
            "  versions may stall or reject where a toy payload succeeds.\n"
        )
        signed = account.sign_transaction(tx)
        raw = signed.raw_transaction
        print(f"  signed payload           {len(raw)} bytes")

        tx_hash = w3.eth.send_raw_transaction(raw)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        if receipt.status != 1:
            raise SystemExit(f"transaction reverted: {receipt}")
        recovered = receipt["from"]
        if recovered.lower() != sender.lower():
            raise SystemExit(
                f"signature recovered to {recovered}, not {sender} -- the "
                "device signed for a different account than it reported."
            )
        print(f"  mined in block           {receipt.blockNumber}")
        print(f"  contract created at      {receipt.contractAddress}")
        print(f"  recovered sender         {recovered}")

        print(
            "\nLEDGER SIGNING PROVED (local anvil fork; no transaction reached "
            "Robinhood)\n"
            f"  The pinned deployer signs contract creations for chain {chain_id}\n"
            "  at real deployment size, and the payload is accepted and mined.\n"
            "  Blind signing is enabled and the live deployer nonce is zero."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
