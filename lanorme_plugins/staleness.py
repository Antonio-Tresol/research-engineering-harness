"""STALE-001/002: the bookkeeping artefacts have kept up with the work.

Every other check verifies internal consistency: that a claim's evidence exists,
that statuses are legal, that numbers resolve. None of them notice when the
research tree simply stopped being updated. A project can run twenty experiments
against a placeholder `Q1` and pass everything.

    STALE-001  the research tree has not changed for N commits, while the
               watched paths (results, scripts, src) have.  [warning]
    STALE-002  a document declares `updated:` in its frontmatter, and git shows
               the file changed after that date.  [warning]

Both use git, so both are silent outside a repository or before the first
commit. Both are warnings: only a person can say whether an experiment produced
a belief worth recording, and a gate that blocks on that judgement gets bypassed.

Configure:

    [staleness]
    watch = ["results/**", "scripts/**", "src/**"]
    artefacts = ["TREE.md"]
    max_commits_behind = 8
    dated_docs = ["reports/**/*.md"]     # enables STALE-002

Run:
    lanorme check . --check=staleness
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Final

from lanorme import CheckResult, Status, Violation, register

from ._common import is_glob_match

UPDATED_RE: Final[re.Pattern[str]] = re.compile(
    r"^updated:\s*(\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE
)
FRONTMATTER_RE: Final[re.Pattern[str]] = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

STALE_001: Final[str] = "STALE-001: bookkeeping artefacts keep pace with the work"
STALE_002: Final[str] = "STALE-002: a document's `updated:` date matches its last change"


def git(root: Path, *args: str) -> str | None:
    """Run git, returning stripped stdout, or None when git cannot answer."""
    try:
        done = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, check=False, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def is_git_repo(root: Path) -> bool:
    return git(root, "rev-parse", "--git-dir") is not None


def last_commit_for(root: Path, path: str) -> str | None:
    """Short hash of the last commit touching `path`."""
    out = git(root, "log", "-1", "--format=%h", "--", path)
    return out or None


def commits_touching_since(root: Path, since: str, patterns: list[str]) -> int:
    """How many commits since `since` touched any watched path."""
    out = git(root, "rev-list", "--count", f"{since}..HEAD", "--", *patterns)
    return int(out) if out and out.isdigit() else 0


def last_commit_date(root: Path, path: str) -> date | None:
    out = git(root, "log", "-1", "--format=%cs", "--", path)
    try:
        return date.fromisoformat(out) if out else None
    except ValueError:
        return None


def declared_updated(text: str) -> date | None:
    """The `updated:` date in a document's frontmatter, if present."""
    front = FRONTMATTER_RE.match(text)
    if front is None:
        return None
    found = UPDATED_RE.search(front.group(1))
    if found is None:
        return None
    try:
        return date.fromisoformat(found.group(1))
    except ValueError:
        return None


@dataclass
class StalenessCheck:
    """Bookkeeping artefacts have kept up with the work."""

    name: str = "staleness"
    description: str = "Research bookkeeping keeps pace with the code and results"
    enabled: bool = True
    max_commits_behind: int = 8
    watch: list[str] = field(default_factory=lambda: ["results", "scripts", "src"])
    artefacts: list[str] = field(default_factory=lambda: ["TREE.md"])
    dated_docs: list[str] = field(default_factory=list)
    rules: list[str] = field(
        default_factory=lambda: [
            "STALE-001: bookkeeping artefacts keep pace with the work (warning)",
            "STALE-002: a document's `updated:` date matches its last change (warning)",
        ]
    )

    def configure(self, *, settings: dict[str, object]) -> None:
        enabled = settings.get("enabled")
        if isinstance(enabled, bool):
            self.enabled = enabled
        behind = settings.get("max_commits_behind")
        if isinstance(behind, int):
            self.max_commits_behind = behind
        for key in ("watch", "artefacts", "dated_docs"):
            value = settings.get(key)
            if isinstance(value, list):
                setattr(self, key, [str(v) for v in value])

    def check_artefacts(self, root: Path) -> list[Violation]:
        found: list[Violation] = []
        for artefact in self.artefacts:
            if not (root / artefact).is_file():
                continue
            anchor = last_commit_for(root, artefact)
            if anchor is None:
                continue  # never committed; nothing to measure against
            behind = commits_touching_since(root, anchor, self.watch)
            if behind <= self.max_commits_behind:
                continue
            found.append(Violation(
                file=artefact, line=1, rule=STALE_001,
                message=(
                    f"{artefact} has not changed while {behind} commits touched "
                    f"{', '.join(self.watch)}"
                ),
                fix=(
                    "Record what those runs established: move an experiment to [done], "
                    "add the claims it produced, or note in the log why nothing changed"
                ),
            ))
        return found

    def check_dated_docs(self, root: Path) -> list[Violation]:
        found: list[Violation] = []
        for path in sorted(root.rglob("*.md")):
            if ".git" in path.parts:
                continue
            relative = str(path.relative_to(root))
            if not is_glob_match(relative, self.dated_docs):
                continue
            declared = declared_updated(path.read_text(encoding="utf-8"))
            if declared is None:
                continue
            changed = last_commit_date(root, relative)
            if changed is None or changed <= declared:
                continue
            found.append(Violation(
                file=relative, line=1, rule=STALE_002,
                message=f"Frontmatter says updated: {declared}, but the file changed on {changed}",
                fix=f"Set `updated: {changed}` and confirm the content still reflects the data",
            ))
        return found

    def run(self, *, src_root: str) -> CheckResult:
        root = Path(src_root)
        if not self.enabled or not is_git_repo(root):
            return CheckResult(check=self.name, status=Status.PASS)
        warnings = self.check_artefacts(root) + self.check_dated_docs(root)
        status = Status.WARN if warnings else Status.PASS
        return CheckResult(check=self.name, status=status, warnings=warnings)


register(StalenessCheck())
