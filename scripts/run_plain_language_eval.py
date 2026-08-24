#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Behaviour eval: does the plain-language intervention keep TREE.md and
RESEARCH_LOG.md legible, and is a hook needed before the gate reliably runs?

Four arms, each a complete project workspace seeded from a git revision of
this harness:

  base   pre-intervention harness (main): old templates, skill, validator.
  norms  plain-language docs (branch) with the OLD validator: norms alone.
  gate   the full branch: norms plus the validator tripwire; the agent must
         choose to run it.
  hook   gate plus a PostToolUse hook that runs the validator after every
         edit to TREE.md / RESEARCH_LOG.md and feeds failures back into the
         agent's context — enforcement without agent discipline.

Two tasks:

  dictation    clean project, new results land, but the USER writes in
               telegraph shorthand. Measures whether the new record
               normalises the dialect or copies it.
  inheritance  tree and log already carry telegraph dialect and a freeform
               section; a plainly-worded prompt asks for the session-end
               update. Measures mimicry vs clean-up, and whether the gate
               forces clean-up when it fires.

Grading is mechanical and lives in plain_language_graders.py: a pinned copy
of the branch validator's shorthand patterns, applied identically to every
arm, so the metric cannot drift with the intervention. Transcripts and final
files are copied per run for human reading. Results append to a JSONL keyed
by (task, arm, run); re-running skips completed keys, so a killed sweep
resumes where it stopped.

Run:  uv run scripts/run_plain_language_eval.py --runs 3 --out results/plain_language
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Final

from plain_language_graders import grade
from plain_language_tasks import (
    DESCRIPTION,
    FIXTURES,
    NAME,
    QUESTION,
    SEED_DATE,
    SUMMARY,
    TASKS,
)

HARNESS: Final[Path] = Path(__file__).resolve().parent.parent
# Pinned pre-intervention commit. This was "main" while the intervention lived
# on a branch; once the branch merged, "main" would silently become the
# intervention itself and the base arm would measure nothing.
BASE_REV: Final[str] = "3cc8ff3"
NEW_REV: Final[str] = "HEAD"
# The intervention branch just before the altitude commit: plain-language
# rules and the hook, but no node-length gate. Pinned so the prealt/alt pair
# differs in exactly one thing.
PRE_ALTITUDE_REV: Final[str] = "da766f7"
# The record-CLI commit's parent: the full altitude stack before the CLI
# shipped and the docs began teaching it. Pinned for the same reason as
# BASE_REV — HEAD after the CLI shipped would make an unpinned "alt" arm
# incoherent (docs teaching a CLI the workspace does not contain).
PRE_CLI_REV: Final[str] = "3893353"
# The record CLI and its libraries, shipped only into "cli"-flagged arms.
CLI_MODULES: Final[tuple[str, ...]] = (
    "scripts/research_graph.py",
    "scripts/research_graph_model.py",
    "scripts/research_graph_write.py",
    "scripts/research_graph_checks.py",
)

# Scoped grants instead of --dangerously-skip-permissions: everything a
# session-end tree/log update plausibly needs, nothing more. Denials are
# recorded per run so scoping noise stays auditable.
ALLOWED_TOOLS: Final[str] = (
    "Read,Write,Edit,MultiEdit,Glob,Grep,TodoWrite,"
    "Bash(uv:*),Bash(python3:*),Bash(python:*),Bash(ls:*),Bash(cat:*),"
    "Bash(mkdir:*),Bash(echo:*),Bash(git:*),Bash(date:*),Bash(head:*),"
    "Bash(tail:*),Bash(wc:*),Bash(grep:*),Bash(rg:*),Bash(sed:*),"
    "Bash(awk:*),Bash(cut:*),Bash(sort:*),Bash(uniq:*),Bash(cp:*),"
    "Bash(mv:*),Bash(touch:*),Bash(for:*),Bash(while:*),"
    # Direct script invocation (both scripts ship executable). Granted to every
    # arm identically so a permission denial can never masquerade as low CLI
    # adoption in the cli arm.
    "Bash(scripts/*),Bash(./scripts/*)"
)

log = logging.getLogger("plain-language-eval")

ARMS: Final[dict[str, dict[str, Any]]] = {
    "base": {"docs_rev": BASE_REV, "validator_rev": BASE_REV, "hook": False},
    "norms": {"docs_rev": NEW_REV, "validator_rev": BASE_REV, "hook": False},
    "gate": {"docs_rev": NEW_REV, "validator_rev": NEW_REV, "hook": False},
    "hook": {"docs_rev": NEW_REV, "validator_rev": NEW_REV, "hook": True},
    # Altitude A/B: identical hooked setups differing only in whether the
    # docs and validator carry the altitude rules (node-length gate, notes/
    # relocation contract, codename hygiene).
    "prealt": {"docs_rev": PRE_ALTITUDE_REV, "validator_rev": PRE_ALTITUDE_REV, "hook": True},
    "alt": {"docs_rev": PRE_CLI_REV, "validator_rev": PRE_CLI_REV, "hook": True},
    # CLI usability A/B against alt: identical hooked altitude stacks, but the
    # record CLI ships in the workspace and the docs/skill teach it. The task
    # prompts never mention the CLI — adoption must come from the docs.
    "cli": {"docs_rev": NEW_REV, "validator_rev": NEW_REV, "hook": True, "cli": True},
}

HOOK_SCRIPT: Final[str] = '''#!/usr/bin/env python3
"""PostToolUse hook: after any edit to TREE.md or RESEARCH_LOG.md, run the
research validator and feed failures back to the agent (exit 2 shows stderr)."""
import json
import os
import subprocess
import sys

payload = json.load(sys.stdin)
path = str(payload.get("tool_input", {}).get("file_path", ""))
if not path.endswith(("TREE.md", "RESEARCH_LOG.md")):
    sys.exit(0)
root = os.environ.get("CLAUDE_PROJECT_DIR", ".")
proc = subprocess.run(
    [sys.executable, os.path.join(root, "scripts", "validate_research.py")],
    capture_output=True,
    text=True,
    timeout=60,
)
if proc.returncode != 0:
    sys.stderr.write(proc.stdout + proc.stderr)
    sys.exit(2)
sys.exit(0)
'''

HOOK_SETTINGS: Final[dict[str, Any]] = {
    "hooks": {
        "PostToolUse": [
            {
                "matcher": "Write|Edit|MultiEdit",
                "hooks": [
                    {
                        "type": "command",
                        "command": 'python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/validate_hook.py',
                        "timeout": 90,
                    }
                ],
            }
        ]
    }
}

PREDICTIONS: Final[str] = """# Predictions, registered before the sweep

- base: the dictation prompt's telegraph is copied into TREE/LOG in at least
  half of runs; the inheritance dialect persists in nearly all runs (agents
  mimic the file's established conventions).
- norms: new prose cleaner than base; inherited dialect still mostly persists
  (nothing forces touching old content).
- gate: new prose mostly clean; inherited dialect cleaned only in runs where
  the agent actually runs the validator. Expected validator-run rate 50-80%
  (both AGENTS.md versions already demand a session-end validator run).
- hook: cleanest overall and the only arm where inherited dialect is cleaned
  reliably, because failures enter context without agent discipline.
- Decision rule for the hooks hypothesis: hooks look necessary if the gate arm
  leaves shorthand or a red validator in a third or more of runs where the
  hook arm does not.
"""


# ---------------------------------------------------------------- workspace
def git_show(rev: str, rel: str) -> str:
    return subprocess.run(
        ["git", "show", f"{rev}:{rel}"],
        cwd=HARNESS,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    ).stdout


def render(text: str) -> str:
    """The install.py placeholder substitutions, with fixed eval values."""
    return (
        text.replace("<PROJECT NAME>", NAME)
        .replace("<one-line description>", DESCRIPTION)
        .replace("<the project's research question>", QUESTION)
        .replace("<What this project is, who is working on it, and its timebox if any.>", SUMMARY)
    )


def build_tree(docs_rev: str, nodes: str) -> str:
    template = render(git_show(docs_rev, "templates/TREE.md"))
    seed_line = f"- Q1: {QUESTION} [open]\n"
    if seed_line not in template:
        raise RuntimeError(f"template TREE.md at {docs_rev} lost its seed node anchor")
    return template.replace(seed_line, nodes)


def build_log(docs_rev: str, entries: str) -> str:
    template = render(git_show(docs_rev, "templates/RESEARCH_LOG.md"))
    head, sep, _ = template.partition("### SEED-DATE")
    if not sep:
        raise RuntimeError(f"template RESEARCH_LOG.md at {docs_rev} lost its SEED-DATE anchor")
    return head + entries


def build_workspace(task_id: str, arm: str, key: str) -> Path:
    """A fenced workspace outside any git repository, its own git repo, with
    the seed committed so the agent's changes are a clean diff."""
    workspace = Path(tempfile.gettempdir()) / "plain-language-workspaces" / key
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    spec, task = ARMS[arm], TASKS[task_id]
    files: dict[str, str] = {
        "AGENTS.md": render(git_show(spec["docs_rev"], "templates/AGENTS.md")),
        "CLAUDE.md": git_show(spec["docs_rev"], "templates/CLAUDE.md"),
        ".claude/skills/research-log/SKILL.md": git_show(
            spec["docs_rev"], ".claude/skills/research-log/SKILL.md"
        ),
        "scripts/validate_research.py": git_show(
            spec["validator_rev"], "scripts/validate_research.py"
        ),
        "TREE.md": build_tree(spec["docs_rev"], task["nodes"]),
        "RESEARCH_LOG.md": build_log(spec["docs_rev"], task["entries"]),
        **FIXTURES,
        **task.get("extra_files", {}),
    }
    if spec["hook"]:
        files[".claude/hooks/validate_hook.py"] = HOOK_SCRIPT
        files[".claude/settings.json"] = json.dumps(HOOK_SETTINGS, indent=2)
    if spec.get("cli"):
        for rel in CLI_MODULES:
            files[rel] = git_show(spec["validator_rev"], rel)
    for rel, content in files.items():
        target = workspace / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    (workspace / "scripts" / "validate_research.py").chmod(0o755)
    if spec.get("cli"):
        (workspace / "scripts" / "research_graph.py").chmod(0o755)
    identity = ["-c", "user.email=eval@local", "-c", "user.name=eval"]
    for args in (["init", "-q"], ["add", "-A"], [*identity, "commit", "-q", "-m", "seed"]):
        subprocess.run(["git", *args], cwd=workspace, capture_output=True, check=False, timeout=30)
    return workspace


# ------------------------------------------------------------- cli metrics
# A record-CLI invocation and its subcommand: the only global flag is --root,
# so the first non-flag token after the script name is the subcommand.
CLI_CALL_RE: Final[re.Pattern[str]] = re.compile(
    r"research_graph\.py(?:\s+--root\s+\S+)?\s+(--help|-h|[a-z][a-z-]*)"
)
CLI_WRITE_SUBCOMMANDS: Final[frozenset[str]] = frozenset(
    {"add", "add-evidence", "set-status", "log", "add-note"}
)


def cli_metrics(transcript_text: str) -> dict[str, Any]:
    """How the agent used (or avoided) the record CLI, from the transcript.

    Descriptive measurements for the usability read. They live in the runner,
    not the pinned graders: they record what happened, they never score it.
    """
    out: dict[str, Any] = {
        "cli_calls": 0,
        "cli_write_calls": 0,
        "cli_help_calls": 0,
        "cli_subcommands": [],
        "hand_edits": 0,
    }
    result_chunks: list[str] = []
    for line in transcript_text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        # System and error events carry a plain-string "message"; only the
        # assistant/user turn events have the dict shape scanned here.
        message = event.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if event.get("type") == "assistant" and block.get("type") == "tool_use":
                name = block.get("name")
                tool_input = block.get("input", {})
                if name == "Bash":
                    for sub in CLI_CALL_RE.findall(str(tool_input.get("command", ""))):
                        sub = "help" if sub in ("-h", "--help") else sub
                        out["cli_calls"] += 1
                        out["cli_subcommands"].append(sub)
                        out["cli_write_calls"] += sub in CLI_WRITE_SUBCOMMANDS
                        out["cli_help_calls"] += sub == "help"
                elif name in ("Write", "Edit", "MultiEdit") and str(
                    tool_input.get("file_path", "")
                ).endswith(("TREE.md", "RESEARCH_LOG.md")):
                    out["hand_edits"] += 1
            elif event.get("type") == "user" and block.get("type") == "tool_result":
                inner = block.get("content")
                if isinstance(inner, str):
                    result_chunks.append(inner)
                elif isinstance(inner, list):
                    result_chunks.extend(
                        str(item.get("text", "")) for item in inner if isinstance(item, dict)
                    )
    results = "\n".join(result_chunks)
    out["cli_rejections"] = results.count("the record would become invalid")
    out["cli_usage_errors"] = results.count("research_graph.py: error:")
    out["cli_unknown_id_errors"] = results.count("Error: no node with id")
    return out


# ---------------------------------------------------------------- running
def run_claude_scoped(
    prompt: str, cwd: Path, model: str, timeout: int, max_turns: int = 40
) -> dict[str, Any]:
    cmd = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        model,
        "--max-turns",
        str(max_turns),
        "--setting-sources",
        "project",
        "--allowedTools",
        ALLOWED_TOOLS,
    ]
    try:
        done = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False
        )
        stdout = done.stdout
    except subprocess.TimeoutExpired as exc:
        stdout = (
            exc.stdout
            if isinstance(exc.stdout, str)
            else (exc.stdout or b"").decode(errors="replace")
        )
        return {"stdout": stdout, "final": {}, "timed_out": True}
    final: dict[str, Any] = {}
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "result":
            final = event
    return {"stdout": stdout, "final": final, "timed_out": False}


def run_one(task_id: str, arm: str, run_idx: int, args: argparse.Namespace) -> dict[str, Any]:
    key = f"pl|{task_id}|{arm}|r{run_idx}"
    workspace = build_workspace(task_id, arm, key.replace("|", "_"))
    started = time.monotonic()
    outcome = run_claude_scoped(TASKS[task_id]["prompt"], workspace, args.model, args.timeout)
    transcript = outcome["stdout"]
    artefacts = args.out / "artifacts" / key.replace("|", "_")
    artefacts.mkdir(parents=True, exist_ok=True)
    (artefacts / "transcript.jsonl").write_text(transcript)
    for rel in ("TREE.md", "RESEARCH_LOG.md"):
        shutil.copy2(workspace / rel, artefacts / rel)
    final = outcome["final"]
    usage_limited = "hit your session limit" in transcript or "usage limit" in transcript.lower()
    row: dict[str, Any] = {
        "key": key,
        "task": task_id,
        "arm": arm,
        "run": run_idx,
        "model": args.model,
        "served_models": sorted((final.get("modelUsage") or {}).keys()),
        "num_turns": int(final.get("num_turns", 0)),
        "cost_usd": float(final.get("total_cost_usd") or 0.0),
        "duration_s": round(time.monotonic() - started, 1),
        "timed_out": outcome["timed_out"],
        "is_error": bool(final.get("is_error", False)) or outcome["timed_out"],
        "usage_limited": usage_limited,
        "workspace": str(workspace),
        "artifacts": str(artefacts),
        "ts": time.strftime("%FT%T"),
    }
    task = TASKS[task_id]
    row.update(grade(workspace, transcript, SEED_DATE, canaries=tuple(task.get("canaries", ()))))
    row.update(cli_metrics(transcript))
    everything = "\n".join(
        (workspace / rel).read_text()
        for rel in ("TREE.md", "RESEARCH_LOG.md")
        if (workspace / rel).is_file()
    )
    for note in sorted(workspace.glob("notes/*.md")):
        everything += "\n" + note.read_text()
    row["mentions_present"] = sum(1 for m in task.get("must_mention", ()) if m in everything)
    row["mentions_total"] = len(task.get("must_mention", ()))
    done_id = task.get("done_id", "Q1.H1.E1")
    tree_text = (workspace / "TREE.md").read_text()
    row["target_done"] = bool(re.search(rf"{re.escape(done_id)}:.*\[done\].*evidence:", tree_text))
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=lambda s: s.split(","), default=list(TASKS))
    parser.add_argument("--arms", type=lambda s: s.split(","), default=list(ARMS))
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--out", type=Path, default=Path("results/plain_language"))
    args = parser.parse_args()
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(args.out / "run.log")],
    )
    predictions = args.out / "predictions.md"
    if not predictions.exists():
        predictions.write_text(PREDICTIONS)
    out_file = args.out / "runs.jsonl"
    done_keys: set[str] = set()
    if out_file.is_file():
        done_keys = {
            json.loads(line)["key"] for line in out_file.read_text().splitlines() if line.strip()
        }
    jobs = [
        (task_id, arm, run_idx)
        for task_id in args.tasks
        for arm in args.arms
        for run_idx in range(args.runs)
        if f"pl|{task_id}|{arm}|r{run_idx}" not in done_keys
    ]
    log.info("%d runs to do (%d already recorded)", len(jobs), len(done_keys))
    lock = threading.Lock()
    stop = threading.Event()
    completed = 0
    total_cost = 0.0

    def submit(job: tuple[str, str, int]) -> dict[str, Any] | None:
        if stop.is_set():
            return None
        return run_one(*job, args)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(submit, job): job for job in jobs}
        for future in as_completed(futures):
            row = future.result()
            if row is None:
                continue
            if row["usage_limited"]:
                log.warning("usage limit at %s — stopping sweep; re-run to resume", row["key"])
                stop.set()
                continue
            with lock:
                with out_file.open("a") as sink:
                    sink.write(json.dumps(row) + "\n")
                completed += 1
                total_cost += row["cost_usd"]
            log.info(
                "%s done (%d/%d) — turns=%s validator_calls=%s pass=%s cost so far $%.2f",
                row["key"],
                completed,
                len(jobs),
                row["num_turns"],
                row["validator_calls"],
                row["arm_validator_pass"],
                total_cost,
            )
    log.info("sweep finished: %d rows appended, total cost $%.2f", completed, total_cost)
    return 0


if __name__ == "__main__":
    sys.exit(main())
