#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Do agents find and use the clarity-review workflow when a task calls for it?

One cell, run against the shipped record tooling: a project whose review file
holds two open findings from an outside reader — one pointing at an invented
name that genuinely needs a rewrite, one pointing at standard statistics
vocabulary that deserves a recorded waiver. The task prompt says only that an
outside collaborator found parts of the record hard to follow; it never names
the review command. Measured per run: whether the agent discovers the review
report, resolves the real finding by rewriting through the record tool,
resolves the defensible one by waiver or rewrite, hand-edits the review file
(the workflow's failure mode), and leaves the record valid.

Predictions are registered in results/review_usability/predictions.md before
the first run. Lab equipment: measures the harness, never ships.

    uv run scripts/run_review_usability_eval.py --out /path/to/meta/results/review_usability
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Final

HARNESS: Final[Path] = Path(__file__).resolve().parents[1]

CLI_MODULES: Final[tuple[str, ...]] = (
    "scripts/research_graph.py",
    "scripts/research_graph_model.py",
    "scripts/research_graph_write.py",
    "scripts/research_graph_checks.py",
    "scripts/research_graph_txn.py",
    "scripts/research_graph_views.py",
    "scripts/research_graph_verification.py",
    "scripts/research_graph_glossary.py",
    "scripts/research_graph_review.py",
    "scripts/review_clarity.py",
    "scripts/validate_research.py",
)

# Same scoped grants as the earlier usability sweeps, so a permission denial
# can never masquerade as low adoption.
ALLOWED_TOOLS: Final[str] = (
    "Read,Write,Edit,MultiEdit,Glob,Grep,TodoWrite,"
    "Bash(uv:*),Bash(python3:*),Bash(python:*),Bash(ls:*),Bash(cat:*),"
    "Bash(mkdir:*),Bash(echo:*),Bash(git:*),Bash(date:*),Bash(head:*),"
    "Bash(tail:*),Bash(wc:*),Bash(grep:*),Bash(rg:*),Bash(sed:*),"
    "Bash(awk:*),Bash(cut:*),Bash(sort:*),Bash(uniq:*),Bash(cp:*),"
    "Bash(mv:*),Bash(touch:*),Bash(for:*),Bash(while:*),"
    "Bash(scripts/*),Bash(./scripts/*)"
)

# The record under test. "The mirror pass" is the planted invented name; the
# claim's n=3 is the planted standard vocabulary a reader flagged anyway.
TREE: Final[str] = """# Research tree — probe embedding stability

Grammar and status vocabulary: see `.claude/skills/research-log/SKILL.md`.
Validate with `uv run scripts/validate_research.py`.

- Q1: Do the fine-tuned model's probe directions survive a change of embedding basis? [open] | log: 2026-08-20
  - Q1.H1: Probe directions are basis-stable up to rotation [open] | log: 2026-08-20
    - Q1.H1.E1: Recompute the probes after the mirror pass and compare cosine similarity per layer; sonnet judgments for tie-breaks [done] | evidence: results/basis_stability.jsonl | log: 2026-08-20
      - Q1.H1.E1.C1: Cosine similarity to the original directions stays above 0.93 in every layer after recomputation (n=3 seeds per layer) [unvalidated] | evidence: results/basis_stability.jsonl
"""

LOG: Final[str] = """# Research log — probe embedding stability

## Project summary

A two-week probe of whether learned probe directions in a fine-tuned language
model survive a change of embedding basis. One question, one hypothesis under
test. All experiments run from `scripts/` with fixed seeds; results land in
`results/` as JSON Lines files.

---

# Log

Newest entry first. Every entry answers the same four questions.

### 2026-08-20

* What I did: Ran the recomputation experiment for Q1.H1.E1 and recorded the per-layer cosine similarities to results/basis_stability.jsonl.
* What I expected vs what happened: Expected similarity to drop in late layers; it stayed above 0.93 everywhere.
* What this changes about my thinking: The rotation story looks plausible at this scale; the claim is recorded as unvalidated until a falsification pass runs.
* What I will do next: Design the falsification tests for Q1.H1.E1.C1.
"""

FINDING_REAL: Final[dict[str, str]] = {
    "excerpt": "Recompute the probes after the mirror pass and compare cosine similarity per layer",
    "problem": (
        '"The mirror pass" is never defined anywhere in the document, so I '
        "cannot tell what operation the probes are recomputed after."
    ),
}
FINDING_DEFENSIBLE: Final[dict[str, str]] = {
    "excerpt": "stays above 0.93 in every layer after recomputation (n=3 seeds per layer)",
    "problem": "I cannot tell what the n refers to in this claim.",
}

PROMPT: Final[str] = (
    "A collaborator from outside the project read our research record and said "
    "parts of it were hard to follow. Use the project's own tooling to find out "
    "exactly what an outside reader could not follow in TREE.md, and address "
    "every open item: fix what deserves fixing (for background: the operation "
    "the experiment ran after is re-expressing the embedding matrix in an "
    "orthonormalised basis), and where the text is right as it stands, record "
    "why it stays. When you are done, the record must pass its checks."
)


def build_workspace(base: Path, key: str) -> Path:
    """A fresh project with the shipped tooling and one current review on disk."""
    workspace = base / key
    if workspace.exists():
        shutil.rmtree(workspace)
    (workspace / "results").mkdir(parents=True)
    (workspace / "TREE.md").write_text(TREE, encoding="utf-8")
    (workspace / "RESEARCH_LOG.md").write_text(LOG, encoding="utf-8")
    (workspace / "results" / "basis_stability.jsonl").write_text(
        '{"layer": 0, "cosine": 0.97}\n', encoding="utf-8"
    )
    for rel in CLI_MODULES:
        dest = workspace / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(HARNESS / rel, dest)
    skill_dir = workspace / ".claude" / "skills" / "research-log"
    skill_dir.mkdir(parents=True)
    shutil.copy2(HARNESS / ".claude" / "skills" / "research-log" / "SKILL.md", skill_dir)
    tree_sha = hashlib.sha256(TREE.encode("utf-8")).hexdigest()
    (workspace / "reviews").mkdir()
    (workspace / "reviews" / "tree-md.json").write_text(
        json.dumps(
            {
                "artifact": "TREE.md",
                "sha256": tree_sha,
                "protocol": (
                    "Read this document as a researcher who knows machine learning, "
                    "statistics, and software engineering, but has never opened this "
                    "repository, and report every place the text does not communicate, "
                    "quoting it verbatim."
                ),
                "runs": [
                    {
                        "reader": "sonnet",
                        "at": "2026-08-21",
                        "verdict": "needs-work",
                        "findings": [FINDING_REAL, FINDING_DEFENSIBLE],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return workspace


def run_subject(workspace: Path, args: argparse.Namespace) -> str:
    """One agent session over the workspace; returns the stream-json transcript."""
    cmd = [
        "claude",
        "-p",
        PROMPT,
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        args.model,
        "--max-turns",
        str(args.max_turns),
        "--setting-sources",
        "project",
        "--allowedTools",
        ALLOWED_TOOLS,
    ]
    try:
        done = subprocess.run(
            cmd, cwd=workspace, capture_output=True, text=True, timeout=args.timeout, check=False
        )
        return done.stdout
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout
        return out if isinstance(out, str) else (out or b"").decode(errors="replace")


def _tool_calls(transcript: str) -> tuple[list[str], list[str]]:
    """Bash commands and file-edit paths actually executed, from tool_use blocks.

    Substring checks over the raw transcript are unusable here: an agent that
    reads the CLI source or its help pulls every command name and message
    string into the transcript without running anything. The first grading of
    this cell mis-scored two runs exactly that way.
    """
    commands: list[str] = []
    edits: list[str] = []
    for line in transcript.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        message = event.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list):
            continue
        for block in content:
            if not (isinstance(block, dict) and block.get("type") == "tool_use"):
                continue
            payload = block.get("input")
            if not isinstance(payload, dict):
                continue
            if block.get("name") == "Bash":
                commands.append(str(payload.get("command", "")))
            elif block.get("name") in ("Write", "Edit", "MultiEdit"):
                edits.append(str(payload.get("file_path", "")))
    return commands, edits


def grade(workspace: Path, transcript: str) -> dict[str, Any]:
    """Every measure is a fact about executed tool calls or the final workspace."""
    commands, edits = _tool_calls(transcript)
    row: dict[str, Any] = {"bash_calls": len(commands)}
    row["ran_review_report"] = any(
        "review" in c and "research_graph" in c and "--run" not in c and "--waive" not in c
        for c in commands
    )
    row["ran_reader"] = any("--run TREE.md" in c or "--run RESEARCH_LOG" in c for c in commands)
    row["used_set_text"] = any("set-text" in c for c in commands)
    row["executed_waive"] = any(
        "--waive TREE.md" in c or "--waive RESEARCH_LOG" in c for c in commands
    )
    row["edited_review_file_directly"] = any("reviews/" in e for e in edits)
    row["edited_tree_by_hand"] = any(e.endswith("TREE.md") for e in edits)
    tree_text = (workspace / "TREE.md").read_text(encoding="utf-8")
    row["real_finding_fixed"] = "the mirror pass" not in tree_text
    review_path = workspace / "reviews" / "tree-md.json"
    row["review_file_survives"] = review_path.is_file()
    waived = []
    if review_path.is_file():
        try:
            waived = json.loads(review_path.read_text(encoding="utf-8")).get("waivers", [])
        except json.JSONDecodeError:
            row["review_file_survives"] = False
    row["defensible_waived"] = any(
        "n=3" in str(w.get("excerpt", "")) or "seeds" in str(w.get("excerpt", "")) for w in waived
    )
    validator = subprocess.run(
        [sys.executable, "scripts/validate_research.py"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    row["record_valid_at_end"] = validator.returncode == 0
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--max-turns", type=int, default=40)
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--workdir", type=Path, default=Path("/tmp/review_usability_workspaces"))
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for index in range(args.runs):
        key = f"review_usability_r{index}"
        workspace = build_workspace(args.workdir, key)
        print(f"run {index + 1}/{args.runs} ...", file=sys.stderr)
        started = time.monotonic()
        transcript = run_subject(workspace, args)
        (args.out / f"{key}.transcript.jsonl").write_text(transcript, encoding="utf-8")
        row = {"key": key, "seconds": round(time.monotonic() - started, 1)}
        row.update(grade(workspace, transcript))
        rows.append(row)
        with (args.out / "runs.jsonl").open("w", encoding="utf-8") as sink:
            for done_row in rows:
                sink.write(json.dumps(done_row) + "\n")
        print(json.dumps(row), file=sys.stderr)
    print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
