#!/usr/bin/env python3
"""
Scan Vyper contracts for mutability cleanup candidates.

Rules:
- view-revert: no assert, raise, or raw_revert inside @view / @pure functions.
- can-be-view: @external / @internal functions that compile when @view is added.
- view-could-be-pure: @view functions that compile when @view is replaced by @pure.
- interface-mismatch: unique local interface declarations must match the implementation mutability.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import vyper.ast as vy_ast
from vyper.compiler import compile_from_file_input
from vyper.compiler.input_bundle import FileInput, FilesystemInputBundle


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DIR = ROOT / "contracts"
DEFAULT_BASELINE = ROOT / "tools" / "mutability-baseline.yml"
VALID_EXEMPTION_RULES = {"view-revert", "can-be-view", "view-could-be-pure"}
BASELINE_RULES = VALID_EXEMPTION_RULES | {"interface-mismatch"}
EXEMPTION_RE = re.compile(
    r"^\s*#\s*mutability-exempt\[(?P<rule>[a-z-]+)\]:\s*(?P<reason>.+?)\s*$"
)
IMPORT_RE = re.compile(r"^\s*import\s+(contracts(?:\.[A-Za-z0-9_]+)+)\s+as\s+\w+\s*$")


@dataclasses.dataclass(frozen=True)
class FunctionInfo:
    file: str
    line: int
    end_line: int
    name: str
    decorators: tuple[str, ...]
    decorator_lines: tuple[tuple[str, int], ...]
    signature: str

    @property
    def mutability(self) -> str:
        if "pure" in self.decorators:
            return "pure"
        if "view" in self.decorators:
            return "view"
        if "payable" in self.decorators:
            return "payable"
        return "nonpayable"

    @property
    def is_external(self) -> bool:
        return "external" in self.decorators

    @property
    def is_internal(self) -> bool:
        return "internal" in self.decorators

    @property
    def is_deploy(self) -> bool:
        return "deploy" in self.decorators or self.name == "__init__"

    @property
    def top_decorator_line(self) -> int:
        if not self.decorator_lines:
            return self.line
        return min(line for _, line in self.decorator_lines)


@dataclasses.dataclass(frozen=True)
class InterfaceFunction:
    file: str
    line: int
    interface: str
    name: str
    signature: str
    mutability: str


@dataclasses.dataclass(frozen=True)
class Finding:
    file: str
    line: int
    rule: str
    symbol: str
    reason: str
    detail: str = ""
    exempt_reason: str | None = None

    def key(self) -> tuple[str, int, str, str]:
        return (self.file, self.line, self.rule, self.symbol)

    def identity(self) -> tuple[str, str, str]:
        return (self.file, self.rule, self.symbol)


@dataclasses.dataclass(frozen=True)
class BaselineEntry:
    file: str
    line: int
    rule: str
    symbol: str
    reason: str

    def key(self) -> tuple[str, int, str, str]:
        return (self.file, self.line, self.rule, self.symbol)

    def identity(self) -> tuple[str, str, str]:
        return (self.file, self.rule, self.symbol)


class OverlayFilesystemInputBundle(FilesystemInputBundle):
    def __init__(self, search_paths: list[Path], overlays: dict[Path, str]):
        super().__init__(search_paths)
        self.overlays = {path.resolve(): contents for path, contents in overlays.items()}

    def _load_from_path(self, resolved_path: Path, original_path: Path) -> FileInput:
        resolved = Path(resolved_path).resolve()
        if resolved in self.overlays:
            source_id = self._generate_source_id(resolved)
            return FileInput(source_id, original_path, resolved, self.overlays[resolved])
        return super()._load_from_path(resolved_path, original_path)


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def source_segment(source: str, node) -> str:
    raw = getattr(node, "src", None)
    if not raw:
        return ""
    start_s, length_s, *_ = raw.split(":")
    start = int(start_s)
    length = int(length_s)
    return source[start : start + length]


def annotation_text(source: str, node) -> str:
    return " ".join(source_segment(source, node).split())


def function_signature(source: str, node) -> str:
    arg_types = [annotation_text(source, arg.annotation) for arg in node.args.args]
    return f"{node.name}({','.join(arg_types)})"


def decorator_name(node) -> str:
    return getattr(node, "id", "")


def parse_contract(path: Path) -> tuple[list[FunctionInfo], list[InterfaceFunction]]:
    source = path.read_text()
    module = vy_ast.parse_to_ast(source)
    functions: list[FunctionInfo] = []
    interfaces: list[InterfaceFunction] = []
    file = rel(path)

    for node in module.body:
        if type(node).__name__ == "FunctionDef":
            decorators = tuple(decorator_name(deco) for deco in node.decorator_list)
            decorator_lines = tuple((decorator_name(deco), deco.lineno) for deco in node.decorator_list)
            functions.append(
                FunctionInfo(
                    file=file,
                    line=node.lineno,
                    end_line=node.end_lineno,
                    name=node.name,
                    decorators=decorators,
                    decorator_lines=decorator_lines,
                    signature=function_signature(source, node),
                )
            )
        elif type(node).__name__ == "InterfaceDef":
            for item in node.body:
                if type(item).__name__ != "FunctionDef":
                    continue
                mutability = "nonpayable"
                if item.body and type(item.body[0]).__name__ == "Expr":
                    value = getattr(item.body[0], "value", None)
                    mutability = getattr(value, "id", "nonpayable")
                interfaces.append(
                    InterfaceFunction(
                        file=file,
                        line=item.lineno,
                        interface=node.name,
                        name=item.name,
                        signature=function_signature(source, item),
                        mutability=mutability,
                    )
                )

    return functions, interfaces


def parse_all(paths: Iterable[Path]) -> tuple[list[FunctionInfo], list[InterfaceFunction]]:
    functions: list[FunctionInfo] = []
    interfaces: list[InterfaceFunction] = []
    for path in paths:
        file_functions, file_interfaces = parse_contract(path)
        functions.extend(file_functions)
        interfaces.extend(file_interfaces)
    return functions, interfaces


def has_revert_statement(path: Path, fn: FunctionInfo) -> tuple[int, str] | None:
    source = path.read_text()
    module = vy_ast.parse_to_ast(source)
    for node in module.body:
        if type(node).__name__ != "FunctionDef" or node.name != fn.name or node.lineno != fn.line:
            continue
        for child in node.get_descendants():
            if type(child).__name__ in {"Assert", "Raise"}:
                return child.lineno, type(child).__name__
            if type(child).__name__ == "Call" and getattr(getattr(child, "func", None), "id", None) == "raw_revert":
                return child.lineno, "raw_revert"
    return None


def find_exemption(path: Path, fn: FunctionInfo, rule: str) -> tuple[str | None, str | None]:
    lines = path.read_text().splitlines()
    comment_index = fn.top_decorator_line - 2
    if comment_index < 0 or comment_index >= len(lines):
        return None, None
    match = EXEMPTION_RE.match(lines[comment_index])
    if not match:
        return None, None
    found_rule = match.group("rule")
    reason = match.group("reason").strip()
    if found_rule not in VALID_EXEMPTION_RULES:
        return None, f"invalid exemption category '{found_rule}'"
    if not reason:
        return None, "empty exemption reason"
    if found_rule != rule:
        return None, None
    return reason, None


def mutate_to_view(path: Path, fn: FunctionInfo) -> str:
    lines = path.read_text().splitlines(keepends=True)
    insert_at = fn.top_decorator_line - 1
    indent = re.match(r"^(\s*)", lines[insert_at]).group(1)
    lines.insert(insert_at, f"{indent}@view\n")
    return "".join(lines)


def mutate_to_pure(path: Path, fn: FunctionInfo) -> str:
    lines = path.read_text().splitlines(keepends=True)
    for name, line in fn.decorator_lines:
        if name == "view":
            index = line - 1
            lines[index] = lines[index].replace("@view", "@pure", 1)
            return "".join(lines)
    raise ValueError(f"{fn.file}:{fn.line} has no @view decorator")


def compile_file_input(target: Path, source: str, overlays: dict[Path, str] | None = None) -> None:
    resolved = target.resolve()
    file_input = FileInput(-1, target, resolved, source)
    bundle = OverlayFilesystemInputBundle([ROOT], overlays or {})
    compile_from_file_input(file_input, input_bundle=bundle, output_formats=["abi"])


def compiles_source(target: Path, source: str, overlays: dict[Path, str] | None = None) -> bool:
    try:
        compile_file_input(target, source, overlays)
        return True
    except Exception:
        return False


def imported_contract_paths(path: Path) -> set[str]:
    imports: set[str] = set()
    for line in path.read_text().splitlines():
        match = IMPORT_RE.match(line)
        if not match:
            continue
        dotted = match.group(1)
        imports.add(dotted.replace(".", "/") + ".vy")
    return imports


def compile_targets(paths: list[Path]) -> dict[str, str]:
    direct: dict[str, bool] = {}
    for path in paths:
        direct[rel(path)] = compiles_source(path, path.read_text())

    importers: dict[str, list[Path]] = defaultdict(list)
    for path in paths:
        for imported in imported_contract_paths(path):
            importers[imported].append(path)

    targets: dict[str, str] = {}
    for path in paths:
        file = rel(path)
        if direct[file]:
            targets[file] = file
            continue
        for importer in sorted(importers.get(file, [])):
            importer_rel = rel(importer)
            if direct.get(importer_rel):
                targets[file] = importer_rel
                break
        if file not in targets:
            targets[file] = file
    return targets


def compile_candidate_task(args: tuple[str, int, str, str]) -> tuple[str, int, str, bool, str]:
    file, line, rule, target_file = args
    path = ROOT / file
    functions, _ = parse_contract(path)
    fn = next(item for item in functions if item.line == line)
    source = mutate_to_view(path, fn) if rule == "can-be-view" else mutate_to_pure(path, fn)
    target = ROOT / target_file
    target_source = source if target_file == file else target.read_text()
    overlays = {path: source} if target_file != file else {}
    try:
        compile_file_input(target, target_source, overlays)
        return file, line, rule, True, ""
    except Exception as exc:
        return file, line, rule, False, exc.__class__.__name__


def run_compile_candidates(
    candidates: list[tuple[FunctionInfo, str]],
    targets: dict[str, str],
    jobs: int,
) -> dict[tuple[str, int, str], bool]:
    tasks = [(fn.file, fn.line, rule, targets[fn.file]) for fn, rule in candidates]
    results: dict[tuple[str, int, str], bool] = {}
    if not tasks:
        return results
    if jobs <= 1:
        for task in tasks:
            file, line, rule, ok, _ = compile_candidate_task(task)
            results[(file, line, rule)] = ok
        return results
    try:
        with concurrent.futures.ProcessPoolExecutor(max_workers=jobs) as executor:
            for file, line, rule, ok, _ in executor.map(compile_candidate_task, tasks):
                results[(file, line, rule)] = ok
    except PermissionError:
        for task in tasks:
            file, line, rule, ok, _ = compile_candidate_task(task)
            results[(file, line, rule)] = ok
    return results


def interface_findings(functions: list[FunctionInfo], interfaces: list[InterfaceFunction]) -> tuple[list[Finding], list[str]]:
    impls_by_signature: dict[str, list[FunctionInfo]] = defaultdict(list)
    for fn in functions:
        if fn.is_external and not fn.is_deploy:
            impls_by_signature[fn.signature].append(fn)

    findings: list[Finding] = []
    ambiguous: list[str] = []
    for iface in interfaces:
        matches = [fn for fn in impls_by_signature.get(iface.signature, []) if fn.file != iface.file]
        if len(matches) == 1:
            impl = matches[0]
            if iface.mutability != impl.mutability:
                findings.append(
                    Finding(
                        file=iface.file,
                        line=iface.line,
                        rule="interface-mismatch",
                        symbol=f"{iface.interface}.{iface.name}",
                        reason="local interface mutability does not match unique implementation",
                        detail=(
                            f"interface is {iface.mutability}; "
                            f"implementation {impl.file}:{impl.line} is {impl.mutability}"
                        ),
                    )
                )
        elif len(matches) > 1:
            locations = ", ".join(f"{fn.file}:{fn.line} ({fn.mutability})" for fn in matches)
            ambiguous.append(f"{iface.file}:{iface.line} {iface.interface}.{iface.name} -> {locations}")
    return findings, ambiguous


def scan(paths: list[Path], jobs: int) -> tuple[list[Finding], list[str], dict[str, int]]:
    functions, interfaces = parse_all(paths)
    targets = compile_targets(paths)
    findings: list[Finding] = []
    invalid_exemptions: list[str] = []

    for fn in functions:
        path = ROOT / fn.file
        for rule in VALID_EXEMPTION_RULES:
            _, error = find_exemption(path, fn, rule)
            if error:
                invalid_exemptions.append(f"{fn.file}:{fn.top_decorator_line - 1}: {error}")

        if fn.mutability in {"view", "pure"}:
            revert = has_revert_statement(path, fn)
            if revert:
                statement_line, statement_type = revert
                exempt_reason, _ = find_exemption(path, fn, "view-revert")
                findings.append(
                    Finding(
                        file=fn.file,
                        line=fn.line,
                        rule="view-revert",
                        symbol=fn.name,
                        reason="view/pure function contains revert statement",
                        detail=f"{statement_type} at line {statement_line}",
                        exempt_reason=exempt_reason,
                    )
                )

    compile_candidates: list[tuple[FunctionInfo, str]] = []
    for fn in functions:
        if fn.is_deploy or not (fn.is_external or fn.is_internal):
            continue
        if fn.mutability not in {"view", "pure"}:
            compile_candidates.append((fn, "can-be-view"))
        elif fn.mutability == "view":
            compile_candidates.append((fn, "view-could-be-pure"))

    compile_results = run_compile_candidates(compile_candidates, targets, jobs)
    for fn, rule in compile_candidates:
        if not compile_results.get((fn.file, fn.line, rule), False):
            continue
        exempt_reason, _ = find_exemption(ROOT / fn.file, fn, rule)
        reason = "function compiles with @view" if rule == "can-be-view" else "function compiles with @pure"
        findings.append(
            Finding(
                file=fn.file,
                line=fn.line,
                rule=rule,
                symbol=fn.name,
                reason=reason,
                exempt_reason=exempt_reason,
            )
        )

    iface_findings, ambiguous_interfaces = interface_findings(functions, interfaces)
    findings.extend(iface_findings)

    for message in invalid_exemptions:
        findings.append(
            Finding(
                file=message.split(":", 1)[0],
                line=int(message.split(":", 2)[1]),
                rule="invalid-exemption",
                symbol="mutability-exempt",
                reason=message,
            )
        )

    counts = {
        "vyper_files": len(paths),
        "defs": len(functions),
        "view": sum(1 for fn in functions if fn.mutability == "view"),
        "pure": sum(1 for fn in functions if fn.mutability == "pure"),
        "nonreentrant": sum(1 for fn in functions if "nonreentrant" in fn.decorators),
    }
    return sorted(findings, key=lambda item: (item.file, item.line, item.rule, item.symbol)), ambiguous_interfaces, counts


def write_baseline(path: Path, findings: list[Finding]) -> None:
    entries = [
        finding
        for finding in findings
        if finding.rule in BASELINE_RULES and finding.exempt_reason is None
    ]
    lines = ["# tools/mutability-baseline.yml", "# Generated by tools/mutability_scanner.py --write-baseline", ""]
    for finding in sorted(entries, key=lambda item: (item.file, item.line, item.rule)):
        lines.extend(
            [
                f"- file: {finding.file}",
                f"  line: {finding.line}",
                f"  rule: {finding.rule}",
                f"  symbol: {finding.symbol}",
                "  reason: migration baseline",
            ]
        )
    path.write_text("\n".join(lines) + "\n")


def load_baseline(path: Path) -> list[BaselineEntry]:
    if not path.exists():
        return []
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- "):
            if current:
                entries.append(current)
            current = {}
            line = line[2:].strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if current is None:
            current = {}
        current[key.strip()] = value.strip()
    if current:
        entries.append(current)

    parsed: list[BaselineEntry] = []
    for entry in entries:
        parsed.append(
            BaselineEntry(
                file=entry["file"],
                line=int(entry["line"]),
                rule=entry["rule"],
                symbol=entry["symbol"],
                reason=entry.get("reason", ""),
            )
        )
    return parsed


def compare_baseline(findings: list[Finding], baseline: list[BaselineEntry]) -> tuple[list[Finding], list[BaselineEntry]]:
    baseline_by_key = {entry.identity(): entry for entry in baseline}
    finding_by_key = {
        finding.identity(): finding
        for finding in findings
        if finding.rule in BASELINE_RULES and finding.exempt_reason is None
    }
    new_findings = [finding for key, finding in finding_by_key.items() if key not in baseline_by_key]
    stale_entries = [entry for key, entry in baseline_by_key.items() if key not in finding_by_key]
    return sorted(new_findings, key=lambda item: item.key()), sorted(stale_entries, key=lambda item: item.key())


def write_inventory(path: Path, findings: list[Finding], ambiguous: list[str], counts: dict[str, int]) -> None:
    by_rule: dict[str, list[Finding]] = defaultdict(list)
    for finding in findings:
        by_rule[finding.rule].append(finding)

    lines = [
        "# Mutability Scanner Inventory",
        "",
        "## Counts",
        "",
    ]
    for key in ["vyper_files", "defs", "view", "pure", "nonreentrant"]:
        lines.append(f"- {key}: {counts[key]}")
    lines.append("")

    for rule in ["view-revert", "can-be-view", "view-could-be-pure", "interface-mismatch", "invalid-exemption"]:
        entries = by_rule.get(rule, [])
        lines.extend([f"## {rule} ({len(entries)})", ""])
        if entries:
            for finding in entries:
                suffix = f" - {finding.detail}" if finding.detail else ""
                exempt = f" [exempt: {finding.exempt_reason}]" if finding.exempt_reason else ""
                lines.append(f"- {finding.file}:{finding.line} {finding.symbol}{suffix}{exempt}")
        else:
            lines.append("- none")
        lines.append("")

    lines.extend([f"## interface-ambiguous ({len(ambiguous)})", ""])
    if ambiguous:
        for item in ambiguous:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.append("")
    path.write_text("\n".join(lines))


def print_summary(findings: list[Finding], counts: dict[str, int], ambiguous: list[str]) -> None:
    print(
        "counts: "
        f"{counts['vyper_files']} Vyper files, "
        f"{counts['defs']} defs, "
        f"{counts['view']} @view, "
        f"{counts['pure']} @pure, "
        f"{counts['nonreentrant']} @nonreentrant"
    )
    by_rule: dict[str, int] = defaultdict(int)
    for finding in findings:
        by_rule[finding.rule] += 1
    for rule in ["view-revert", "can-be-view", "view-could-be-pure", "interface-mismatch", "invalid-exemption"]:
        print(f"{rule}: {by_rule[rule]}")
    print(f"interface-ambiguous: {len(ambiguous)}")


def print_failure(finding: Finding, label: str) -> None:
    print(f"FAIL {finding.file}:{finding.line} {finding.symbol}: {finding.rule} ({label})")
    if finding.detail:
        print(f"  Detail: {finding.detail}")
    if finding.rule == "view-revert":
        print("  To fix:")
        print("    1. Refactor: move assert to caller and return a sentinel")
        print("    2. Exempt:   add comment above the topmost decorator:")
        print("                 # mutability-exempt[view-revert]: <reason>")
    elif finding.rule == "can-be-view":
        print("  To fix:")
        print("    1. Add @view above the topmost decorator")
        print("    2. Exempt:   add comment above the topmost decorator:")
        print("                 # mutability-exempt[can-be-view]: <reason>")
    elif finding.rule == "view-could-be-pure":
        print("  To fix:")
        print("    1. Replace @view with @pure")
        print("    2. Exempt:   add comment above the topmost decorator:")
        print("                 # mutability-exempt[view-could-be-pure]: <reason>")
    elif finding.rule == "interface-mismatch":
        print("  To fix:")
        print("    Update the local interface declaration to match the implementation mutability.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan Vyper mutability policy.")
    parser.add_argument("--contracts-dir", type=Path, default=CONTRACTS_DIR)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--write-baseline", type=Path, default=None)
    parser.add_argument("--inventory", type=Path, default=None)
    parser.add_argument("--jobs", type=int, default=max(1, min(os.cpu_count() or 1, 8)))
    args = parser.parse_args()

    paths = sorted(args.contracts_dir.rglob("*.vy"))
    findings, ambiguous, counts = scan(paths, args.jobs)
    print_summary(findings, counts, ambiguous)

    if args.inventory:
        write_inventory(args.inventory, findings, ambiguous, counts)
        print(f"wrote inventory: {args.inventory}")

    if args.write_baseline:
        write_baseline(args.write_baseline, findings)
        print(f"wrote baseline: {args.write_baseline}")
        return 0

    baseline = load_baseline(args.baseline)
    new_findings, stale_entries = compare_baseline(findings, baseline)
    invalid_findings = [finding for finding in findings if finding.rule == "invalid-exemption"]

    for finding in new_findings:
        print_failure(finding, "new violation, not in baseline")
    for entry in stale_entries:
        print(
            f"FAIL {entry.file}:{entry.line} {entry.symbol}: {entry.rule} "
            "(baseline entry no longer matches a current violation; remove it)"
        )
    for finding in invalid_findings:
        print_failure(finding, "invalid exemption")

    if new_findings or stale_entries or invalid_findings:
        return 1

    print("mutability scanner passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
