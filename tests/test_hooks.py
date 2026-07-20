#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest>=8.0"]
# ///
"""Tests for the pre-commit hook.

The hook is the only piece an agent meets on every commit, and until now it was
the only piece with no tests. Each case builds a throwaway repository, stages a
particular shape of change, runs the real hook, and asserts on what it said.

The blocking behaviour matters as much as the reminders: a hook that blocks on a
judgement call gets bypassed, so the tests pin which conditions may exit
non-zero and which may not.

Run:  uv run tests/test_hooks.py
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "pre-commit"


def run_git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    run_git(tmp_path, "init", "-q")
    run_git(tmp_path, "config", "user.email", "t@example.com")
    run_git(tmp_path, "config", "user.name", "T")
    (tmp_path / "TREE.md").write_text("- Q1: q [open]\n")
    (tmp_path / "RESEARCH_LOG.md").write_text("# log\n")
    run_git(tmp_path, "add", "-A")
    run_git(tmp_path, "commit", "-q", "-m", "init")
    return tmp_path


def stage(root: Path, relative: str, text: str = "x") -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    run_git(root, "add", str(path.relative_to(root)))


def hook(root: Path) -> subprocess.CompletedProcess[str]:
    """Run the real hook against the staged state."""
    return subprocess.run(
        ["bash", str(HOOK)], cwd=root, capture_output=True, text=True, check=False,
    )


# --- Reminders fire ------------------------------------------------------

def test_reminds_when_results_change_without_tree(repo: Path) -> None:
    stage(repo, "results/run.json", "{}")
    out = hook(repo).stdout
    assert "TREE.md did not" in out


def test_reminder_names_the_offending_file(repo: Path) -> None:
    """A vague reminder gets skimmed; a specific one gets acted on."""
    stage(repo, "results/steering.json", "{}")
    assert "results/steering.json" in hook(repo).stdout


def test_reminds_when_skill_changes_without_docs(repo: Path) -> None:
    stage(repo, ".claude/skills/a/SKILL.md", "---\nname: a\ndescription: d\n---\n\nbody\n")
    assert "AGENTS.md and the README" in hook(repo).stdout


def test_reminds_to_bump_a_stale_updated_date(repo: Path) -> None:
    old = (date.today() - timedelta(days=5)).isoformat()
    stage(repo, "reports/f.md", f"---\ntitle: F\nupdated: {old}\n---\n\nBody.\n")
    out = hook(repo).stdout
    assert "updated:" in out and date.today().isoformat() in out


def test_reminds_to_rerun_gates_when_code_and_results_move_together(repo: Path) -> None:
    stage(repo, "scripts/run.py", "x = 1\n")
    stage(repo, "results/run.json", "{}")
    assert "re-run falsify or validate-claims" in hook(repo).stdout


# --- Reminders stay quiet ------------------------------------------------

def test_quiet_when_tree_updated_alongside_results(repo: Path) -> None:
    stage(repo, "results/run.json", "{}")
    stage(repo, "TREE.md", "- Q1: q [answered]\n")
    out = hook(repo).stdout
    assert "TREE.md did not" not in out


def test_quiet_when_updated_date_is_today(repo: Path) -> None:
    today = date.today().isoformat()
    stage(repo, "reports/f.md", f"---\ntitle: F\nupdated: {today}\n---\n\nBody.\n")
    assert "Bump it" not in hook(repo).stdout


def test_quiet_for_a_document_without_an_updated_field(repo: Path) -> None:
    stage(repo, "reports/f.md", "---\ntitle: F\n---\n\nBody.\n")
    assert "updated:" not in hook(repo).stdout


def test_quiet_on_a_documentation_only_commit(repo: Path) -> None:
    """Editing prose owes the research tree nothing."""
    stage(repo, "README.md", "# readme\n")
    out = hook(repo).stdout
    assert "worth checking" not in out


def test_no_output_when_nothing_is_staged(repo: Path) -> None:
    assert hook(repo).stdout.strip() == ""


# --- Blocking behaviour --------------------------------------------------

def test_reminders_never_block_the_commit(repo: Path) -> None:
    """The whole design rests on this: judgement calls must not fail a commit."""
    stage(repo, "results/run.json", "{}")
    stage(repo, ".claude/skills/a/SKILL.md", "---\nname: a\ndescription: d\n---\n\nbody\n")
    result = hook(repo)
    assert result.returncode == 0
    assert "do not block" in result.stdout


def test_blocks_when_checks_fail(repo: Path) -> None:
    """A failing check.sh is objective, so it stops the commit."""
    (repo / "check.sh").write_text("#!/usr/bin/env bash\nexit 1\n")
    (repo / "check.sh").chmod(0o755)
    stage(repo, "results/run.json", "{}")
    result = hook(repo)
    assert result.returncode == 1
    assert "--no-verify" in result.stdout


def test_passes_when_checks_pass(repo: Path) -> None:
    (repo / "check.sh").write_text("#!/usr/bin/env bash\nexit 0\n")
    (repo / "check.sh").chmod(0o755)
    stage(repo, "README.md", "# readme\n")
    assert hook(repo).returncode == 0


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
