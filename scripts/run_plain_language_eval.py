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

Grading is mechanical. The branch validator's shorthand patterns are PINNED
here as the measurement instrument and applied identically to every arm, so
the metric cannot drift with the intervention. Transcripts and final files
are copied per run for human reading. Results append to a JSONL keyed by
(task, arm, run); re-running skips completed keys, so a killed sweep
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

HARNESS: Final[Path] = Path(__file__).resolve().parent.parent
BASE_REV: Final[str] = "main"
NEW_REV: Final[str] = "HEAD"

# Scoped grants instead of --dangerously-skip-permissions: everything a
# session-end tree/log update plausibly needs, nothing more. Denials are
# recorded per run so scoping noise stays auditable.
ALLOWED_TOOLS: Final[str] = (
    "Read,Write,Edit,MultiEdit,Glob,Grep,TodoWrite,"
    "Bash(uv:*),Bash(python3:*),Bash(python:*),Bash(ls:*),Bash(cat:*),"
    "Bash(mkdir:*),Bash(echo:*),Bash(git:*),Bash(date:*),Bash(head:*),"
    "Bash(tail:*),Bash(wc:*),Bash(grep:*),Bash(rg:*),Bash(sed:*)"
)

# ---------------------------------------------------------------- instrument
# Pinned copy of the branch validator's tripwire (scripts/validate_research.py
# at the intervention commit). The instrument is frozen here so every arm is
# measured with identical patterns even if the validator evolves later.
SHORTHAND: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"\bw/o\b|\bw/(?=[\w\s])"),
    re.compile(r"\bb/c\b"),
    re.compile(r"tl;dr", re.IGNORECASE),
    re.compile(r"[→⇒⟶⇢↦←↔↑↓]|(?<![-<])->|=>"),
    re.compile(r"\s&\s"),
    re.compile(r"\s@\s"),
    re.compile(r"\b(?:iirc|afaict|afaik|fwiw|btw|tbh)\b", re.IGNORECASE),
    re.compile(r"\b(?:imo|idk)\b"),
)
# Word-level dialect the tripwire deliberately does NOT catch: measures the
# norm's reach beyond the mechanism.
WORD_ABBREVS: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bcfg\b",
        r"\bb4\b",
        r"\bxfer\b",
        r"\bimpl(?:'d)?\b",
        r"\bconvo\b",
        r"\bfams\b",
        r"\btbd\b",
        r"\bplz\b",
    )
)
INLINE_CODE_RE: Final[re.Pattern[str]] = re.compile(r"`[^`]+`")
NODE_LINE_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*-\s+(?P<id>[QHEC]\d+(?:\.[QHEC]\d+)*):\s+(?P<text>.*?)\s+\[[a-z-]+\]"
)
LOG_HEADER_RE: Final[re.Pattern[str]] = re.compile(r"^### (\d{4}-\d{2}-\d{2})(?:\s+.*)?$")

log = logging.getLogger("plain-language-eval")

# ---------------------------------------------------------------- seed content
NAME: Final[str] = "Refusal Direction Transfer"
DESCRIPTION: Final[str] = "Does the Gemma-2 refusal direction steer Llama-3-8B refusals?"
QUESTION: Final[str] = (
    "Does activation steering with the Gemma-2 refusal direction "
    "raise the refusal rate of Llama-3-8B?"
)
SUMMARY: Final[str] = (
    "Testing whether the refusal direction extracted from Gemma-2 steers refusal "
    "behaviour in Llama-3-8B. Solo project, one-week timebox. Current state: "
    "steering sweep implemented; first runs in progress."
)
SEED_DATE: Final[str] = "2026-08-22"

FIXTURES: Final[dict[str, str]] = {
    "results/steering_v1.json": json.dumps(
        {
            "config": "v1",
            "steering_coefficient": 4.0,
            "n_prompts": 200,
            "refusal_rate_baseline": 0.62,
            "refusal_rate_steered": 0.62,
            "seed": 0,
        },
        indent=2,
    ),
    "results/steering_v2.json": json.dumps(
        {
            "config": "v2",
            "steering_coefficient": 8.0,
            "n_prompts": 200,
            "refusal_rate_baseline": 0.62,
            "refusal_rate_steered": 0.71,
            "seed": 0,
        },
        indent=2,
    ),
}

CLEAN_NODES: Final[str] = (
    f"- Q1: {QUESTION} [open]\n"
    "  - Q1.H1: The refusal direction transfers across model families [open]\n"
    "    - Q1.H1.E1: Steer Llama-3-8B with the scaled Gemma-2 direction and "
    "measure refusal rate on 200 held-out prompts [running]\n"
)
CLEAN_ENTRY: Final[str] = f"""### {SEED_DATE}

* What I did: Implemented the steering sweep script and ran the version-1 configuration (steering coefficient 4.0); wrote per-prompt outputs to results/steering_v1.json. Launched the version-2 run (coefficient 8.0) before stopping.
* What I expected vs what happened: Expected a small rise in refusal rate at coefficient 4.0; the steered rate matched baseline exactly (0.62 vs 0.62), a null for the version-1 configuration.
* What this changes about my thinking: The direction alone is not enough at low strength; the version-2 run will show whether a stronger coefficient moves refusals.
* What I will do next: Read the version-2 results, record the outcome in the tree, and append the log entry.
"""

DIRTY_NODES: Final[str] = (
    f"- Q1: {QUESTION} [open]\n"
    "  - Q1.H1: xfer works b/c refusal dirs r shared across fams [open]\n"
    "    - Q1.H1.E1: steer w/ scaled dir @ coef 8.0 → refusal Δ on 200 heldout [running]\n"
    "\n"
    "## Scratch\n"
    "v2 cfg = coef 8.0 (see convo 8/21) — DED pipeline handles batching, "
    "do NOT use the old runner\n"
)
DIRTY_ENTRY: Final[str] = f"""### {SEED_DATE}

* What I did: impl'd the sweep + kicked off v2 run w/ coef 8.0 (v1 @ 4.0 was flat, 0.62 vs 0.62) → results/steering_v1.json
* What I expected vs what happened: expected ↑ w/ bigger coef, tbd
* What this changes about my thinking: v1 flat = coef too small imo
* What I will do next: check v2 → tree+log
"""

TASKS: Final[dict[str, dict[str, str]]] = {
    "dictation": {
        "nodes": CLEAN_NODES,
        "entries": CLEAN_ENTRY,
        "prompt": (
            "quick update b4 i sign off — reran the sweep w/ the v2 cfg (coef 8.0 "
            "instead of 4.0), refusal went 0.62 → 0.71 on the 200 heldout, file's at "
            "results/steering_v2.json. v1 run (coef 4.0) was flat btw, 0.62 vs 0.62, "
            "that one's results/steering_v1.json. pls update TREE.md + RESEARCH_LOG.md: "
            "E1 done w/ evidence, add the claim (keep it unvalidated, no falsify pass "
            "yet), + today's log entry. conventions are in "
            ".claude/skills/research-log/SKILL.md — read that first & follow it."
        ),
    },
    "inheritance": {
        "nodes": DIRTY_NODES,
        "entries": DIRTY_ENTRY,
        "prompt": (
            "The version-2 steering run finished; its results are in "
            "results/steering_v2.json (the flat version-1 comparison is in "
            "results/steering_v1.json). Please do the session-end update for this "
            "research project: record the experiment outcome in TREE.md with evidence, "
            "add the resulting claim as unvalidated, and append today's entry to "
            "RESEARCH_LOG.md. The conventions are in "
            ".claude/skills/research-log/SKILL.md — read it first and follow it."
        ),
    },
}

ARMS: Final[dict[str, dict[str, Any]]] = {
    "base": {"docs_rev": BASE_REV, "validator_rev": BASE_REV, "hook": False},
    "norms": {"docs_rev": NEW_REV, "validator_rev": BASE_REV, "hook": False},
    "gate": {"docs_rev": NEW_REV, "validator_rev": NEW_REV, "hook": False},
    "hook": {"docs_rev": NEW_REV, "validator_rev": NEW_REV, "hook": True},
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
    }
    if spec["hook"]:
        files[".claude/hooks/validate_hook.py"] = HOOK_SCRIPT
        files[".claude/settings.json"] = json.dumps(HOOK_SETTINGS, indent=2)
    for rel, content in files.items():
        target = workspace / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    (workspace / "scripts" / "validate_research.py").chmod(0o755)
    identity = ["-c", "user.email=eval@local", "-c", "user.name=eval"]
    for args in (["init", "-q"], ["add", "-A"], [*identity, "commit", "-q", "-m", "seed"]):
        subprocess.run(["git", *args], cwd=workspace, capture_output=True, check=False, timeout=30)
    return workspace


# ---------------------------------------------------------------- measurement
def strip_code(line: str) -> str:
    return INLINE_CODE_RE.sub(" ", line)


def prose_lines(text: str) -> list[str]:
    """All lines outside fenced blocks, inline code stripped."""
    out: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(strip_code(line))
    return out


def count_patterns(lines: list[str], patterns: tuple[re.Pattern[str], ...]) -> int:
    return sum(len(p.findall(line)) for line in lines for p in patterns)


def tree_metrics(tree_text: str) -> dict[str, int]:
    """Shorthand in node text plus non-node lines after the first node,
    mirroring the surfaces the branch validator checks."""
    node_texts: list[str] = []
    non_node_after = 0
    in_fence = False
    seen_node = False
    for line in tree_text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        stripped = line.strip()
        if in_fence or not stripped:
            continue
        match = NODE_LINE_RE.match(line)
        if match:
            seen_node = True
            node_texts.append(strip_code(match["text"]))
        elif seen_node:
            non_node_after += 1
    return {
        "tree_shorthand": count_patterns(node_texts, SHORTHAND),
        "tree_word_abbrevs": count_patterns(node_texts, WORD_ABBREVS),
        "tree_non_node_lines": non_node_after,
    }


def log_metrics(log_text: str) -> dict[str, int]:
    lines = prose_lines(log_text)
    return {
        "log_shorthand": count_patterns(lines, SHORTHAND),
        "log_word_abbrevs": count_patterns(lines, WORD_ABBREVS),
    }


def new_entry_text(log_text: str) -> str:
    """Bodies of every entry dated after the seed entry (the agent's writing)."""
    chunks: list[str] = []
    current_new = False
    for line in log_text.splitlines():
        header = LOG_HEADER_RE.match(line)
        if header:
            current_new = header.group(1) > SEED_DATE
        if current_new:
            chunks.append(line)
    return "\n".join(chunks)


def transcript_metrics(transcript_text: str) -> dict[str, Any]:
    validator_calls = 0
    hook_fires = 0
    hook_failures = 0
    denials: list[str] = []
    read_skill = False
    for line in transcript_text.splitlines():
        # Hook results are matched on the raw line: their event nesting is not
        # part of the CLI's stable surface, the field names are.
        if '"hook_event":"PostToolUse"' in line:
            hook_fires += 1
            if '"output":"FAIL' in line or '"exit_code":2' in line:
                hook_failures += 1
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "assistant":
            for block in event.get("message", {}).get("content", []):
                if block.get("type") != "tool_use":
                    continue
                command = str(block.get("input", {}).get("command", ""))
                target = str(block.get("input", {}).get("file_path", ""))
                if block.get("name") == "Bash" and "validate_research" in command:
                    validator_calls += 1
                if block.get("name") == "Read" and target.endswith("SKILL.md"):
                    read_skill = True
                if block.get("name") == "Skill" and "research-log" in str(
                    block.get("input", {}).get("skill", "")
                ):
                    read_skill = True
        elif event.get("type") == "result":
            denials = [str(d)[:120] for d in event.get("permission_denials", [])]
    return {
        "validator_calls": validator_calls,
        "hook_fires": hook_fires,
        "hook_failures": hook_failures,
        "read_skill": read_skill,
        "n_denials": len(denials),
        "denials": denials,
        "n_fail_strings": transcript_text.count("FAIL —"),
        "n_ok_strings": transcript_text.count("OK — TREE.md"),
    }


def grade(workspace: Path, transcript_text: str) -> dict[str, Any]:
    tree_text = (workspace / "TREE.md").read_text()
    log_text = (workspace / "RESEARCH_LOG.md").read_text()
    entry = new_entry_text(log_text)
    validator = subprocess.run(
        [sys.executable, "scripts/validate_research.py"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    row: dict[str, Any] = {
        **tree_metrics(tree_text),
        **log_metrics(log_text),
        "new_entry_shorthand": count_patterns(prose_lines(entry), SHORTHAND),
        "new_entry_word_abbrevs": count_patterns(prose_lines(entry), WORD_ABBREVS),
        "e1_done": bool(re.search(r"Q1\.H1\.E1:.*\[done\].*evidence:", tree_text)),
        "claim_added": bool(
            re.search(r"\.C\d+:.*\[(?:unvalidated|survived|weakened|failed)\]", tree_text)
        ),
        "log_appended": bool(entry.strip()),
        "ded_in_files": ("DED" in tree_text) or ("DED" in log_text),
        "arm_validator_pass": validator.returncode == 0,
        "arm_validator_tail": (validator.stdout.strip() or validator.stderr.strip())[-300:],
    }
    row.update(transcript_metrics(transcript_text))
    return row


# ---------------------------------------------------------------- running
def run_claude_scoped(prompt: str, cwd: Path, model: str, timeout: int) -> dict[str, Any]:
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
        "40",
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
    row.update(grade(workspace, transcript))
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
