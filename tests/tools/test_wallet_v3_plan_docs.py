import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ARCHITECTURE = (
    REPO_ROOT
    / "docs"
    / "wallets-v3"
    / "simplified-user-wallet-action-architecture-codex.md"
)
PLAN = REPO_ROOT / "docs" / "wallets-v3" / "user-wallet-v3-implementation-plan-codex.md"


def expand_invariant_cell(cell: str) -> set[int]:
    expanded: set[int] = set()
    for start_text, end_text in re.findall(r"S(\d+)(?:[–-]S?(\d+))?", cell):
        start = int(start_text)
        end = int(end_text or start_text)
        expanded.update(range(start, end + 1))
    return expanded


def test_invariant_matrix_covers_every_governing_invariant() -> None:
    architecture = ARCHITECTURE.read_text()
    plan = PLAN.read_text()
    governing_ids = {
        int(match.group(1))
        for match in re.finditer(r"^S(\d+)\s", architecture, re.MULTILINE)
    }
    assert governing_ids
    assert governing_ids == set(range(1, max(governing_ids) + 1))

    matrix = plan.split("### 5.3 Security-invariant traceability", 1)[1].split(
        "The matrix is a coverage index",
        1,
    )[0]
    mapped_ids: set[int] = set()
    for line in matrix.splitlines():
        if line.startswith("| S"):
            mapped_ids.update(expand_invariant_cell(line.split("|")[1]))

    assert mapped_ids == governing_ids, (
        f"unmapped={sorted(governing_ids - mapped_ids)}, "
        f"unknown={sorted(mapped_ids - governing_ids)}"
    )


def test_phase_zero_and_one_packages_expose_required_contract_fields() -> None:
    plan = PLAN.read_text()
    implementation_packages = re.findall(
        r"(### (?:6|7)\.\d+ Package .*?)(?=\n### |\n---\n)",
        plan,
        re.DOTALL,
    )
    assert implementation_packages
    headings = [package.splitlines()[0] for package in implementation_packages]
    assert len(headings) == len(set(headings))

    required_labels = (
        "**Status:**",
        "**Entry evidence:**",
        "**Question:**",
        "**Fund and authority flow:**",
        "**Security invariants:**",
        "**Measurements:**",
        "**Rollback:**",
        "**Evidence record:**",
    )
    for package in implementation_packages:
        heading = package.splitlines()[0]
        for label in required_labels:
            assert label in package, f"{heading} is missing {label}"
        assert "**Changes:**" in package or "**Changed surfaces:**" in package, (
            f"{heading} is missing changed surfaces"
        )
        assert "**Untouched:**" in package or "**Untouched surfaces:**" in package, (
            f"{heading} is missing untouched surfaces"
        )
        assert "**Disposition" in package, f"{heading} is missing disposition"
