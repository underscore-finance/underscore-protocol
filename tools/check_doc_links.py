"""Validate relative file and anchor links in repository Markdown and HTML."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote, urlsplit


REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_SUFFIXES = {".md", ".html"}
EXCLUDED_DIRS = {
    ".git",
    ".hypothesis",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "venv",
}

MARKDOWN_LINK_RE = re.compile(
    r"!?\[[^\]]*]\(\s*(<[^>]+>|[^)\s]+)"
    r"(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)"
)
MARKDOWN_REFERENCE_RE = re.compile(r"^\s*\[[^\]]+]:\s*(<[^>]+>|[^\s]+)", re.MULTILINE)
HTML_HREF_RE = re.compile(r"\bhref\s*=\s*([\"'])(.*?)\1", re.IGNORECASE)
HTML_ANCHOR_RE = re.compile(r"\b(?:id|name)\s*=\s*([\"'])(.*?)\1", re.IGNORECASE)
ATX_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
SETEXT_HEADING_RE = re.compile(r"^\s{0,3}(=+|-+)\s*$")
LINE_ANCHOR_RE = re.compile(r"^L(\d+)(?:-L(\d+))?$", re.IGNORECASE)


def skipped_path_message(path: Path | str, error: OSError) -> str:
    try:
        display_path = Path(path).resolve().relative_to(REPO_ROOT)
    except (OSError, ValueError):
        display_path = Path(path)
    return f"{display_path}: {type(error).__name__}: {error}"


def git_documentation_candidates(include_untracked: bool = False) -> list[Path]:
    command = ["git", "ls-files", "-z", "--cached"]
    if include_untracked:
        command.extend(["--others", "--exclude-standard"])

    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
    )
    if result.returncode:
        detail = result.stderr.decode(errors="replace").strip()
        message = "git ls-files failed"
        if detail:
            message = f"{message}: {detail}"
        raise RuntimeError(message)

    return [
        REPO_ROOT / os.fsdecode(raw_path)
        for raw_path in result.stdout.split(b"\0")
        if raw_path and Path(os.fsdecode(raw_path)).suffix.lower() in DOC_SUFFIXES
    ]


def documentation_files(
    skipped: list[str] | None = None,
    *,
    include_untracked: bool = False,
) -> list[Path]:
    skipped_paths = skipped if skipped is not None else []
    files: list[Path] = []

    for path in git_documentation_candidates(include_untracked):
        if path.suffix.lower() not in DOC_SUFFIXES:
            continue
        if any(part in EXCLUDED_DIRS for part in path.relative_to(REPO_ROOT).parts):
            continue
        try:
            if path.is_file():
                files.append(path)
        except OSError as error:
            skipped_paths.append(skipped_path_message(path, error))

    return sorted(files)


def without_fenced_code(text: str) -> str:
    visible: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        stripped = line.lstrip()
        marker = stripped[:3]
        if fence is None and marker in {"```", "~~~"}:
            fence = marker
            visible.append("")
            continue
        if fence is not None:
            if stripped.startswith(fence):
                fence = None
            visible.append("")
            continue
        visible.append(line)
    return "\n".join(visible)


def github_slug(heading: str) -> str:
    heading = re.sub(r"<[^>]+>", "", heading)
    heading = re.sub(r"\[([^\]]+)]\([^)]*\)", r"\1", heading)
    heading = heading.replace("`", "")
    heading = heading.strip().lower()
    heading = re.sub(
        r"""[!\"#$%&'()*+,./:;<=>?@\[\\\]^{}|~\u2000-\u206f\u2e00-\u2e7f]""",
        "",
        heading,
    )
    return re.sub(r"\s", "-", heading)


def markdown_anchors(text: str) -> set[str]:
    visible = without_fenced_code(text)
    lines = visible.splitlines()
    base_counts: defaultdict[str, int] = defaultdict(int)
    anchors: set[str] = set()

    def add_heading(value: str) -> None:
        base = github_slug(value)
        suffix = base_counts[base]
        base_counts[base] += 1
        anchors.add(base if suffix == 0 else f"{base}-{suffix}")

    for index, line in enumerate(lines):
        atx = ATX_HEADING_RE.match(line)
        if atx:
            add_heading(atx.group(1))
            continue
        if index > 0 and lines[index - 1].strip() and SETEXT_HEADING_RE.match(line):
            add_heading(lines[index - 1].strip())

    anchors.update(match.group(2) for match in HTML_ANCHOR_RE.finditer(visible))
    return anchors


def html_anchors(text: str) -> set[str]:
    return {match.group(2) for match in HTML_ANCHOR_RE.finditer(text)}


def link_targets(path: Path, text: str) -> list[str]:
    if path.suffix.lower() == ".html":
        return [match.group(2) for match in HTML_HREF_RE.finditer(text)]

    visible = without_fenced_code(text)
    targets = [match.group(1) for match in MARKDOWN_LINK_RE.finditer(visible)]
    targets.extend(match.group(1) for match in MARKDOWN_REFERENCE_RE.finditer(visible))
    targets.extend(match.group(2) for match in HTML_HREF_RE.finditer(visible))
    return targets


def resolved_target(source: Path, raw_target: str) -> tuple[Path, str] | None:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]

    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or target.startswith("/"):
        return None

    relative_path = unquote(parsed.path)
    destination = source if not relative_path else (source.parent / relative_path)
    return destination.resolve(), unquote(parsed.fragment)


def validate_anchor(destination: Path, fragment: str) -> str | None:
    if not fragment:
        return None

    line_anchor = LINE_ANCHOR_RE.fullmatch(fragment)
    if line_anchor:
        try:
            line_count = len(destination.read_text(errors="replace").splitlines())
        except OSError as error:
            return f"cannot read target: {type(error).__name__}: {error}"
        start = int(line_anchor.group(1))
        end = int(line_anchor.group(2) or start)
        if 1 <= start <= end <= line_count:
            return None
        return f"line anchor #{fragment} exceeds {line_count} lines"

    if destination.suffix.lower() not in DOC_SUFFIXES:
        return f"cannot resolve non-line anchor #{fragment} in {destination.name}"

    try:
        text = destination.read_text(errors="replace")
    except OSError as error:
        return f"cannot read target: {type(error).__name__}: {error}"
    anchors = (
        markdown_anchors(text)
        if destination.suffix.lower() == ".md"
        else html_anchors(text)
    )
    if fragment in anchors:
        return None
    return f"anchor #{fragment} does not exist"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-untracked",
        action="store_true",
        help="also validate non-ignored, untracked Markdown and HTML files",
    )
    args = parser.parse_args(argv)

    skipped: list[str] = []
    try:
        files = documentation_files(
            skipped,
            include_untracked=args.include_untracked,
        )
    except RuntimeError as error:
        print(f"Documentation link validation failed: {error}", file=sys.stderr)
        return 2

    failures: list[str] = []
    local_links = 0
    anchor_links = 0

    for source in files:
        try:
            text = source.read_text(errors="replace")
        except OSError as error:
            skipped.append(skipped_path_message(source, error))
            continue
        for raw_target in link_targets(source, text):
            resolved = resolved_target(source, raw_target)
            if resolved is None:
                continue

            local_links += 1
            destination, fragment = resolved
            if fragment:
                anchor_links += 1

            label = f"{source.relative_to(REPO_ROOT)} -> {raw_target}"
            try:
                destination_exists = destination.exists()
                destination_is_dir = destination.is_dir()
            except OSError as error:
                failures.append(
                    f"{label}: cannot stat target: {type(error).__name__}: {error}"
                )
                continue

            if not destination_exists:
                failures.append(f"{label}: target does not exist")
                continue
            if destination_is_dir and fragment:
                readme = destination / "README.md"
                try:
                    readme_exists = readme.exists()
                except OSError as error:
                    failures.append(
                        f"{label}: cannot stat directory README: "
                        f"{type(error).__name__}: {error}"
                    )
                    continue
                if not readme_exists:
                    failures.append(f"{label}: directory has no README.md")
                    continue
                destination = readme

            anchor_failure = validate_anchor(destination, fragment)
            if anchor_failure:
                failures.append(f"{label}: {anchor_failure}")

    if skipped:
        print(
            f"Skipped {len(skipped)} unreadable documentation path(s):",
            file=sys.stderr,
        )
        for skipped_path in skipped:
            print(f"- {skipped_path}", file=sys.stderr)

    if failures:
        print("Documentation link validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(
        "Documentation links valid "
        f"({'tracked + untracked' if args.include_untracked else 'tracked'} files): "
        f"{len(files)} files, {local_links} relative links, "
        f"{anchor_links} anchor links."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
