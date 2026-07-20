"""Shared plumbing for the harness's lanorme checks."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Final

from lanorme import CheckResult, Status, Violation

SKIP_PARTS: Final[frozenset[str]] = frozenset({
    ".git", ".venv", "__pycache__", "node_modules",
})

# (violations, warnings) produced by scanning one file.
FileScan = Callable[[Path, str], "tuple[list[Violation], list[Violation]]"]


def scan_tree(*, name: str, src_root: str, pattern: str, scan: FileScan) -> CheckResult:
    """Run `scan` over every file matching `pattern` and aggregate the result.

    Status is FAIL when anything is a violation, WARN when only warnings, else PASS.
    """
    root = Path(src_root)
    violations: list[Violation] = []
    warnings: list[Violation] = []
    for path in sorted(root.rglob(pattern)):
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        found, warned = scan(path, str(path.relative_to(root)))
        violations.extend(found)
        warnings.extend(warned)
    status = Status.FAIL if violations else (Status.WARN if warnings else Status.PASS)
    return CheckResult(check=name, status=status, violations=violations, warnings=warnings)


def normalize(text: str) -> str:
    """Collapse all whitespace to single spaces.

    Required before substring-matching a YAML value: folded block scalars (`>-`)
    wrap lines mid-phrase, so a literal like "use when" can be split across a
    newline and silently fail to match.
    """
    return " ".join(text.split())
