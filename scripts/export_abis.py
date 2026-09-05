"""
Export ABIs for deployable and standalone Vyper contracts.

Excluded by default:
- mock contracts under `contracts/mock/`
- embedded mixin modules that are only compiled through parent contracts

Usage:
    python scripts/export_abis.py
    python scripts/export_abis.py --output-dir ./my-abis
"""

import argparse
import json
from pathlib import Path

from vyper.compiler import compile_code


EMBEDDED_MODULES = {
    "modules/AddressRegistry.vy",
    "modules/DeptBasics.vy",
    "modules/DexLegoData.vy",
    "modules/Timelock.vy",
    "modules/YieldLegoData.vy",
}


def export_abis(
    contracts_dir: Path,
    output_dir: Path,
    exclude_dirs: list[str] | None = None,
    exclude_files: set[str] | None = None,
) -> int:
    exclude_dirs = exclude_dirs or ["mock"]
    exclude_files = exclude_files or EMBEDDED_MODULES
    output_dir.mkdir(parents=True, exist_ok=True)

    contract_files = list(contracts_dir.rglob("*.vy"))
    exported = 0
    skipped_dirs = 0
    skipped_files = 0
    failures: list[tuple[Path, str]] = []

    for vy_file in sorted(contract_files):
        rel_path = vy_file.relative_to(contracts_dir).as_posix()

        # Skip excluded directories
        if any(excluded in vy_file.parts for excluded in exclude_dirs):
            skipped_dirs += 1
            continue

        if rel_path in exclude_files:
            skipped_files += 1
            continue

        try:
            with open(vy_file) as f:
                code = f.read()

            result = compile_code(code, output_formats=["abi"])
            abi = result["abi"]

            output_file = output_dir / f"{vy_file.stem}.json"
            with open(output_file, "w") as f:
                json.dump(abi, f, indent=2)

            print(f"✓ {vy_file.stem}")
            exported += 1

        except Exception as e:
            print(f"✗ {vy_file.stem}: {e}")
            failures.append((vy_file, str(e)))

    print(f"\nExported {exported} ABIs to {output_dir}")
    print(f"Skipped {skipped_dirs} contracts in excluded directories")
    print(f"Skipped {skipped_files} embedded modules")

    if failures:
        print(f"\nEncountered {len(failures)} export failures:")
        for path, err in failures:
            print(f"- {path}: {err.splitlines()[0]}")
        return 1

    return 0


def main():
    parser = argparse.ArgumentParser(description="Export ABIs for Vyper contracts")
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path("scripts/abis"),
        help="Output directory for ABI files (default: scripts/abis)",
    )
    parser.add_argument(
        "--contracts-dir",
        "-c",
        type=Path,
        default=Path("contracts"),
        help="Contracts directory (default: contracts)",
    )
    args = parser.parse_args()

    raise SystemExit(export_abis(args.contracts_dir, args.output_dir))


if __name__ == "__main__":
    main()
