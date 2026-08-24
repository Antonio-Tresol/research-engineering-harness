#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest>=8.0"]
# ///
"""Tests for the installer's project seeding.

The regression that motivates this file: copy_dir(".claude") used to bring the
harness's own settings.json along, and the COPY_AS step that installs
templates/claude-settings.json then skipped as "exists" — so template settings
(including the validator hook) never reached a project. Invisible while the
two files matched; caught live the day they diverged.

Run:  uv run tests/test_install.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HARNESS = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def installed(tmp_path_factory: pytest.TempPathFactory) -> Path:
    target = tmp_path_factory.mktemp("proj")
    done = subprocess.run(
        [
            sys.executable,
            str(HARNESS / "install.py"),
            str(target),
            "--name",
            "Install Test",
            "--description",
            "d",
            "--question",
            "Does the installer seed everything?",
            "--no-input",
            "--no-reference",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert done.returncode == 0, done.stderr
    return target


def test_project_settings_come_from_the_template(installed: Path) -> None:
    """The template's settings must win over the harness's own .claude copy."""
    settings = json.loads((installed / ".claude" / "settings.json").read_text())
    template = json.loads((HARNESS / "templates" / "claude-settings.json").read_text())
    assert settings == template
    assert "PostToolUse" in settings.get("hooks", {})


def test_validator_hook_ships_and_is_wired(installed: Path) -> None:
    hook = installed / ".claude" / "hooks" / "validate_research_hook.py"
    assert hook.is_file()
    settings = (installed / ".claude" / "settings.json").read_text()
    assert "validate_research_hook.py" in settings


def test_session_verify_hook_ships_and_is_wired(installed: Path) -> None:
    """Session start is where the record re-anchors an agent after context loss."""
    hook = installed / ".claude" / "hooks" / "session_verify_hook.py"
    assert hook.is_file()
    settings = json.loads((installed / ".claude" / "settings.json").read_text())
    assert "SessionStart" in settings.get("hooks", {})
    assert "session_verify_hook.py" in json.dumps(settings["hooks"]["SessionStart"])


def test_fresh_project_validates(installed: Path) -> None:
    done = subprocess.run(
        [sys.executable, "scripts/validate_research.py"],
        cwd=installed,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert done.returncode == 0, done.stdout


def test_shipped_scripts_are_exactly_the_record_tooling(installed: Path) -> None:
    """Every scripts/ file is a conscious shipping decision.

    The eval runners and graders are the harness's lab equipment (they measure
    agent behaviour ON the harness) and must stay home. A new script failing
    this test is the forcing function: either it ships (add it here) or it is
    lab equipment (make it match a COPY_IGNORE pattern in install.py).

    review_clarity.py ships even though it spawns an agent, because it is
    aimed at the project's own documents rather than at the harness: every
    project needs a reader who has never seen its repository.
    """
    shipped = {p.name for p in (installed / "scripts").glob("*.py")}
    assert shipped == {
        "validate_research.py",
        "research_graph.py",
        "research_graph_model.py",
        "research_graph_write.py",
        "research_graph_checks.py",
        "research_graph_glossary.py",
        "research_graph_txn.py",
        "research_graph_verification.py",
        "research_graph_views.py",
        "research_graph_review.py",
        "review_clarity.py",
    }


def test_harness_only_tests_stay_home(installed: Path) -> None:
    """test_install.py needs install.py and templates/, which do not ship."""
    shipped = {p.name for p in (installed / "tests").glob("*.py")}
    assert "test_install.py" not in shipped
    assert {"test_validate_research.py", "test_research_graph.py"} <= shipped


def test_graph_verify_passes_in_fresh_project(installed: Path) -> None:
    done = subprocess.run(
        [sys.executable, "scripts/research_graph.py", "verify"],
        cwd=installed,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert "record verified" in done.stdout


def _run_installer(target: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(HARNESS / "install.py"),
            str(target),
            "--name",
            "Hook Test",
            "--no-input",
            "--no-reference",
            *extra,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


@pytest.fixture()
def git_target(tmp_path: Path) -> Path:
    """A target directory that is already a git repository before install runs."""
    target = tmp_path / "proj"
    target.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=target, check=True, timeout=60)
    return target


def test_pre_commit_wired_into_existing_git_repo(git_target: Path) -> None:
    done = _run_installer(git_target)
    assert done.returncode == 0, done.stderr
    hook = git_target / ".git" / "hooks" / "pre-commit"
    assert hook.is_file()
    assert hook.stat().st_mode & 0o111, "the hook must be executable"
    assert hook.read_bytes() == (HARNESS / "hooks" / "pre-commit").read_bytes()


def test_existing_pre_commit_is_never_replaced(git_target: Path) -> None:
    """Even --force must not reach into .git: the hook there may be someone else's."""
    sentinel = "#!/bin/sh\n# somebody else's machinery\n"
    hook = git_target / ".git" / "hooks" / "pre-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(sentinel)
    done = _run_installer(git_target, "--force")
    assert done.returncode == 0, done.stderr
    assert hook.read_text() == sentinel
    assert "SKIP" in done.stdout and ".git/hooks/pre-commit" in done.stdout


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
