"""The Codex hook adapter and the reader's agent-CLI independence.

The adapter is payload-agnostic on purpose: Codex's per-tool payloads
differ from Claude Code's, so it hashes the two record files instead of
parsing the event, and both sides of that bargain need proof — it fires
on a broken record and stays quiet (and cheap) when nothing changed.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
ADAPTER = HARNESS / "templates" / "codex_validate_record_hook.py"

TREE_OK = "- Q1: q [open]\n"
LOG_OK = (
    "# log\n\n## Project summary\n\nA smoke test.\n\n---\n\n# Log\n\n"
    "### 2026-08-24\n\n* What I did: tested.\n"
    "* What I expected vs what happened: as expected.\n"
    "* What this changes about my thinking: nothing.\n"
    "* What I will do next: nothing.\n"
)


def project(tmp_path: Path, tree: str) -> Path:
    root = tmp_path / "proj"
    (root / "scripts").mkdir(parents=True)
    (root / "TREE.md").write_text(tree, encoding="utf-8")
    (root / "RESEARCH_LOG.md").write_text(LOG_OK, encoding="utf-8")
    for name in ("validate_research.py",):
        (root / "scripts" / name).write_bytes((HARNESS / "scripts" / name).read_bytes())
    return root


def run_adapter(root: Path, payload: str, tmp_path: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, TMPDIR=str(tmp_path / "tmp"))
    (tmp_path / "tmp").mkdir(exist_ok=True)
    return subprocess.run(
        [sys.executable, str(ADAPTER)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=120,
        cwd=root,
        env=env,
    )


def test_broken_record_exits_two_with_the_report(tmp_path: Path) -> None:
    root = project(tmp_path, "- Q1: q [bogus-status]\n")
    done = run_adapter(root, json.dumps({"cwd": str(root)}), tmp_path)
    assert done.returncode == 2
    assert "bogus-status" in done.stderr or "status" in done.stderr


def test_valid_record_is_quiet_and_the_second_call_skips_validation(tmp_path: Path) -> None:
    root = project(tmp_path, TREE_OK)
    first = run_adapter(root, json.dumps({"cwd": str(root)}), tmp_path)
    assert first.returncode == 0, first.stderr
    # Second call with unchanged files must take the hash-guard path.
    second = run_adapter(root, "not even json", tmp_path)
    assert second.returncode == 0 and second.stderr == ""


def test_without_a_tree_the_hook_says_nothing(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    done = run_adapter(root, "{}", tmp_path)
    assert done.returncode == 0 and done.stdout == "" and done.stderr == ""


def test_shipped_hooks_json_wires_both_events_to_shipped_files() -> None:
    wiring = json.loads((HARNESS / "templates" / "codex-hooks.json").read_text())
    events = wiring["hooks"]
    assert set(events) == {"SessionStart", "PostToolUse"}
    commands = [
        h["command"] for group in events.values() for entry in group for h in entry["hooks"]
    ]
    assert any("session_verify_hook.py" in c for c in commands)
    assert any("validate_record_hook.py" in c for c in commands)


def test_reader_override_runs_any_agent_command(monkeypatch) -> None:
    import review_clarity

    fake = 'python3 -c "import sys; print(\'{\\"verdict\\": \\"clear\\", \\"findings\\": []}\')"'
    monkeypatch.setenv("RESEARCH_READER_CMD", fake)
    parsed = review_clarity.run_reader("prompt text", "sonnet", 30)
    assert parsed == {"verdict": "clear", "findings": []}


def test_missing_agent_cli_explains_itself(monkeypatch, capsys) -> None:
    import review_clarity

    monkeypatch.delenv("RESEARCH_READER_CMD", raising=False)
    monkeypatch.setenv("PATH", "/nonexistent")
    parsed = review_clarity.run_reader("prompt text", "sonnet", 30)
    assert parsed is None
    err = capsys.readouterr().err
    assert "RESEARCH_READER_CMD" in err and "claude" in err
