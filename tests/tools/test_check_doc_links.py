from pathlib import Path
from types import SimpleNamespace

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
    monkeypatch.setattr(
        check_doc_links,
        "git_documentation_candidates",
        lambda include_untracked=False: [good_doc, private_doc, envrc],
    )
    monkeypatch.setattr(Path, "is_file", flaky_is_file)

    skipped: list[str] = []
    files = check_doc_links.documentation_files(skipped)

    assert files == [good_doc]
    assert len(skipped) == 1
    assert "private.md: PermissionError" in skipped[0]


def test_git_documentation_candidates_default_to_tracked_files(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs) -> SimpleNamespace:
        calls.append(command)
        return SimpleNamespace(
            returncode=0,
            stdout=b"tracked.md\0script.py\0docs/page.html\0",
            stderr=b"",
        )

    monkeypatch.setattr(check_doc_links, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(check_doc_links.subprocess, "run", fake_run)

    paths = check_doc_links.git_documentation_candidates()

    assert calls == [["git", "ls-files", "-z", "--cached"]]
    assert paths == [tmp_path / "tracked.md", tmp_path / "docs/page.html"]


def test_git_documentation_candidates_can_include_untracked_files(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs) -> SimpleNamespace:
        calls.append(command)
        return SimpleNamespace(
            returncode=0,
            stdout=b"tracked.md\0draft.md\0",
            stderr=b"",
        )

    monkeypatch.setattr(check_doc_links, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(check_doc_links.subprocess, "run", fake_run)

    paths = check_doc_links.git_documentation_candidates(include_untracked=True)

    assert calls == [
        [
            "git",
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
        ]
    ]
    assert paths == [tmp_path / "tracked.md", tmp_path / "draft.md"]


def test_github_slug_removes_unicode_punctuation() -> None:
    assert (
        check_doc_links.github_slug("6.1 Why both gates — the disagreement")
        == "61-why-both-gates--the-disagreement"
    )


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
