from pathlib import Path

from tools import check_doc_links


def test_documentation_files_skips_unstattable_paths(
    monkeypatch,
    tmp_path: Path,
) -> None:
    good_doc = tmp_path / "good.md"
    good_doc.write_text("# Good\n")
    private_doc = tmp_path / "private.md"
    private_doc.write_text("# Private\n")
    envrc = tmp_path / ".envrc"
    envrc.write_text("layout python\n")

    original_is_file = Path.is_file

    def flaky_is_file(path: Path) -> bool:
        if path == envrc:
            raise AssertionError("non-document suffix should be filtered before stat")
        if path == private_doc:
            raise PermissionError("simulated constrained sandbox")
        return original_is_file(path)

    monkeypatch.setattr(check_doc_links, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(Path, "is_file", flaky_is_file)

    skipped: list[str] = []
    files = check_doc_links.documentation_files(skipped)

    assert files == [good_doc]
    assert len(skipped) == 1
    assert "private.md: PermissionError" in skipped[0]


def test_validate_anchor_reports_unreadable_target(
    monkeypatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "target.md"
    target.write_text("# Target\n")
    original_read_text = Path.read_text

    def flaky_read_text(path: Path, *args, **kwargs) -> str:
        if path == target:
            raise PermissionError("simulated constrained sandbox")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", flaky_read_text)

    result = check_doc_links.validate_anchor(target, "target")

    assert result is not None
    assert "cannot read target: PermissionError" in result
