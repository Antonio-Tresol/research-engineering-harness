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


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
