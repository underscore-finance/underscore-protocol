"""Measure the UserWallet runtime before and after removing the action catalog.

This is a feasibility measurement, not a production source transformation. It
creates scratch variants in a temporary directory, compiles them with the
repository's pinned Vyper version and an explicit EVM target, and reports the
exact removed function set and bytecode sizes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

import vyper
from vyper.ast import parse_to_ast
from vyper.evm.opcodes import DEFAULT_EVM_VERSION


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = REPO_ROOT / "contracts/core/userWallet/UserWallet.vy"
EIP_170_LIMIT = 24_576
PINNED_EVM_VERSION = "prague"

CATALOG_EXTERNAL_FUNCTIONS = (
    "depositForYield",
    "withdrawFromYield",
    "rebalanceYieldPosition",
    "swapTokens",
    "mintOrRedeemAsset",
    "confirmMintOrRedeemAsset",
    "addCollateral",
    "removeCollateral",
    "borrow",
    "repayDebt",
    "deleverage",
    "claimIncentives",
    "addLiquidity",
    "removeLiquidity",
    "addLiquidityConcentrated",
    "removeLiquidityConcentrated",
)

CATALOG_ONLY_INTERNAL_FUNCTIONS = (
    "_depositForYield",
    "_withdrawFromYield",
    "_performSwapInstruction",
    "_validateAndGetSwapInfo",
    "_packMiniAddys",
)

LEGACY_OPERATOR_FUNCTIONS = (
    "setLegoAccessForAction",
    "_setLegoAccessForAction",
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git_value(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def function_spans(source: str) -> dict[str, tuple[int, int]]:
    """Return zero-based, end-exclusive spans including decorators."""

    module = parse_to_ast(
        source,
        source_id=0,
        module_path=str(SOURCE_PATH.relative_to(REPO_ROOT)),
    )
    lines = source.splitlines(keepends=True)
    spans: dict[str, tuple[int, int]] = {}

    for node in module.get_children():
        if type(node).__name__ != "FunctionDef":
            continue

        start = node.lineno - 1
        while start > 0 and lines[start - 1].lstrip().startswith("@"):
            start -= 1

        spans[node.name] = (start, node.end_lineno)

    return spans


def stripped_source(source: str, removed_functions: tuple[str, ...]) -> str:
    lines = source.splitlines(keepends=True)
    spans = function_spans(source)
    missing = sorted(set(removed_functions) - set(spans))
    if missing:
        raise ValueError(f"Functions missing from source: {', '.join(missing)}")

    removed_lines: set[int] = set()
    for function_name in removed_functions:
        start, end = spans[function_name]
        removed_lines.update(range(start, end))

    transformed = "".join(
        line for index, line in enumerate(lines) if index not in removed_lines
    )
    implements_line = "implements: wi\n"
    if implements_line not in transformed:
        raise ValueError("Legacy Wallet interface declaration missing from source")
    return transformed.replace(
        implements_line,
        "# Scratch measurement: legacy Wallet interface catalog removed.\n",
        1,
    )


def without_legacy_operator_bridge(
    source: str,
    removed_functions: tuple[str, ...],
) -> str:
    transformed = stripped_source(source, removed_functions)
    legacy_pre_action_call = (
        "    # make sure lego can perform the action\n"
        "    if _shouldCheckAccess:\n"
        "        self._setLegoAccessForAction(ad.legoAddr, _action)\n"
    )
    if legacy_pre_action_call not in transformed:
        raise ValueError("Legacy pre-action operator call missing from source")
    return transformed.replace(
        legacy_pre_action_call,
        "    # Scratch measurement: legacy operator bridge call removed.\n",
        1,
    )


def compile_hex(path: Path, output_format: str, *, pinned: bool) -> bytes:
    command = ["vyper", "-p", str(REPO_ROOT)]
    if pinned:
        command.extend(["--evm-version", PINNED_EVM_VERSION])
    command.extend([str(path), "-f", output_format])
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Vyper failed for {path.name} ({output_format}):\n{exc.stderr}"
        ) from exc
    encoded = completed.stdout.strip()
    if not encoded.startswith("0x"):
        raise ValueError(f"Unexpected {output_format} output from Vyper")
    return bytes.fromhex(encoded[2:])


def measure_variant(
    scratch_dir: Path,
    name: str,
    source: str,
    removed_functions: tuple[str, ...],
) -> dict[str, object]:
    path = scratch_dir / f"{name}.vy"
    path.write_text(source)

    runtime = compile_hex(path, "bytecode_runtime", pinned=True)
    creation = compile_hex(path, "bytecode", pinned=True)
    return {
        "name": name,
        "removedFunctions": list(removed_functions),
        "sourceSha256": sha256_bytes(source.encode()),
        "runtimeBytes": len(runtime),
        "runtimeHeadroomBytes": EIP_170_LIMIT - len(runtime),
        "runtimeSha256": sha256_bytes(runtime),
        "creationBytes": len(creation),
        "creationSha256": sha256_bytes(creation),
    }


def run_measurement() -> dict[str, object]:
    source = SOURCE_PATH.read_text()
    source_bytes = source.encode()

    catalog_removed = (
        *CATALOG_EXTERNAL_FUNCTIONS,
        *CATALOG_ONLY_INTERNAL_FUNCTIONS,
    )
    catalog_and_operator_removed = (
        *catalog_removed,
        *LEGACY_OPERATOR_FUNCTIONS,
    )

    with tempfile.TemporaryDirectory(prefix="wallet-v3-catalog-strip-") as temp:
        scratch_dir = Path(temp)
        baseline_path = scratch_dir / "baseline.vy"
        baseline_path.write_text(source)

        implicit_runtime = compile_hex(
            baseline_path,
            "bytecode_runtime",
            pinned=False,
        )
        pinned_runtime = compile_hex(
            baseline_path,
            "bytecode_runtime",
            pinned=True,
        )
        if implicit_runtime != pinned_runtime:
            raise ValueError(
                "Implicit and explicitly pinned baseline bytecode differ; "
                "resolve the EVM-target mismatch before using this report."
            )

        variants = [
            measure_variant(scratch_dir, "baseline", source, ()),
            measure_variant(
                scratch_dir,
                "catalog_stripped",
                stripped_source(source, catalog_removed),
                catalog_removed,
            ),
            measure_variant(
                scratch_dir,
                "catalog_and_legacy_operator_stripped",
                without_legacy_operator_bridge(
                    source,
                    catalog_and_operator_removed,
                ),
                catalog_and_operator_removed,
            ),
        ]

    return {
        "measurementType": "feasibility upper bound",
        "repositoryCommit": git_value("rev-parse", "HEAD"),
        "repositoryDirty": bool(git_value("status", "--short")),
        "sourcePath": str(SOURCE_PATH.relative_to(REPO_ROOT)),
        "sourceLastModifiedCommit": git_value(
            "log",
            "-1",
            "--format=%H",
            "--",
            str(SOURCE_PATH.relative_to(REPO_ROOT)),
        ),
        "sourceSha256": sha256_bytes(source_bytes),
        "sourceLines": len(source.splitlines()),
        "vyperVersion": vyper.__version__,
        "optimizer": "codesize (source pragma)",
        "implicitDefaultEvmVersion": DEFAULT_EVM_VERSION,
        "pinnedEvmVersion": PINNED_EVM_VERSION,
        "implicitAndPinnedBaselineMatch": True,
        "eip170RuntimeLimitBytes": EIP_170_LIMIT,
        "variants": variants,
        "scratchSourceAdjustments": [
            "Catalog-stripped variants remove the legacy `implements: wi` "
            "declaration because that interface requires the removed external "
            "catalog. The production Wallet v3 interface is not defined by "
            "this measurement.",
            "The legacy-operator comparator also removes the call from the "
            "source-retained pre-action helper to the deleted arbitrary-ABI "
            "operator bridge.",
        ],
        "interpretation": [
            "The stripped result is an upper bound on room made available by "
            "removing the hardcoded action catalog.",
            "Source-retained shared helpers may be omitted from runtime as "
            "unreachable until the routed kernel calls them.",
            "No PROCEED or STOP disposition follows until a provisional kernel "
            "is compiled and compared with a reviewed safety reserve.",
            "The legacy-operator comparator measures the small additional "
            "effect of retiring the arbitrary-ABI operator bridge; it does not "
            "approve a replacement authority design.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON report.",
    )
    args = parser.parse_args()
    report = run_measurement()
    print(json.dumps(report, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
