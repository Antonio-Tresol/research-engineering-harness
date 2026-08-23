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

HARNESS: Final[Path] = Path(__file__).resolve().parent.parent
BASE_REV: Final[str] = "main"
NEW_REV: Final[str] = "HEAD"
# The intervention branch just before the altitude commit: plain-language
# rules and the hook, but no node-length gate. Pinned so the prealt/alt pair
# differs in exactly one thing.
PRE_ALTITUDE_REV: Final[str] = "da766f7"

# Scoped grants instead of --dangerously-skip-permissions: everything a
# session-end tree/log update plausibly needs, nothing more. Denials are
# recorded per run so scoping noise stays auditable.
ALLOWED_TOOLS: Final[str] = (
    "Read,Write,Edit,MultiEdit,Glob,Grep,TodoWrite,"
    "Bash(uv:*),Bash(python3:*),Bash(python:*),Bash(ls:*),Bash(cat:*),"
    "Bash(mkdir:*),Bash(echo:*),Bash(git:*),Bash(date:*),Bash(head:*),"
    "Bash(tail:*),Bash(wc:*),Bash(grep:*),Bash(rg:*),Bash(sed:*)"
)

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

# A registered-protocol node in the accreted state observed in a real tree
# (registration + reads + verdict ladder + one dated amendment, inlined into
# a single node line). One line by construction, ~1.5k characters: the
# pre-altitude validator accepts it, the altitude validator does not.
ACCRETED_NODE: Final[str] = (
    "    - Q1.H1.E2: Dose-response protocol for steering strength — REGISTERED "
    "2026-08-20 before any scoring: coefficients {2.0, 4.0, 8.0, 16.0} on the same "
    "200 held-out prompts, three seeds per cell, refusal judged by the fixed "
    "classifier; per-cell noise standard deviation measured at 0.0021 from 24 "
    "random-direction control runs, which form the null band for every read. READS "
    "registered: (D, gate) dose-response slope — refusal rate regressed on log "
    "coefficient, bar: slope positive with permutation p < 0.001 over 10,000 "
    "shuffles of the coefficient labels; (S) saturation — verdict saturating if the "
    "fitted curve's rise completes within one coefficient doubling, with a "
    "bootstrap interval excluding two doublings; (F) fluency guard — mean "
    "perplexity of steered completions within 1.5x baseline, else the refusal rise "
    "is discounted as degeneration. VERDICT LADDER registered so a middling result "
    "cannot be argued sideways: T3 monotonic dose-response with intact fluency > "
    "T2 rise at high coefficient only, fluency intact > T1 rise with fluency "
    "degradation > T0 null. AMENDED 2026-08-21: shuffled-prompt control added — "
    "the same scoring on prompts with shuffled word order; any dose-response "
    "statistic must not survive it. INSTRUMENT VALIDATION ran 2026-08-21 "
    "(simulation at matched noise, before any true scoring): the slope estimator "
    "recovers planted slopes within its bootstrap interval at all four "
    "coefficients, never reports a positive slope on null simulations (0 of 500), "
    "and the saturation read is decidable only when the rise amplitude exceeds "
    "four times the per-cell noise, so an undecided saturation verdict at small "
    "amplitude is insufficient signal, not evidence against saturation "
    "[running]\n"
)

REGISTRATION_DOC: Final[str] = """# Dose-response protocol — registration

Registered 2026-08-20, before any scoring. Coefficients {2.0, 4.0, 8.0, 16.0}
on the same 200 held-out prompts, three seeds per cell; per-cell noise
standard deviation 0.0021 from 24 random-direction control runs (the null
band for every read).

## Reads

- Gate (D): dose-response slope — refusal rate regressed on log coefficient;
  bar: slope positive with permutation p < 0.001 over 10,000 shuffles.
- Saturation (S): saturating if the fitted rise completes within one
  coefficient doubling (bootstrap interval excluding two doublings).
- Fluency guard (F): mean perplexity of steered completions within 1.5x
  baseline, else the refusal rise is discounted as degeneration.

## Verdict ladder

- T3: monotonic dose-response with intact fluency.
- T2: rise at high coefficient only, fluency intact.
- T1: rise with fluency degradation.
- T0: null.

Amended 2026-08-21: shuffled-prompt control added — the same scoring on
prompts with shuffled word order; no dose-response statistic may survive it.
"""

TRANCHE_RESULT: Final[str] = json.dumps(
    {
        "read": "D_gate",
        "slope_per_log2_coefficient": 0.031,
        "permutation_p": 0.0004,
        "n_shuffles": 10000,
        "fluency_ratio": 1.2,
        "saturation": "undecided",
        "tier": "T2",
        "cells_scored": 8,
        "cells_total": 12,
        "seed": 0,
    },
    indent=2,
)

TASKS: Final[dict[str, dict[str, Any]]] = {
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
    "accretion": {
        "nodes": (
            f"- Q1: {QUESTION} [open]\n"
            "  - Q1.H1: The refusal direction transfers across model families [open]\n"
            "    - Q1.H1.E1: Steer Llama-3-8B with the scaled Gemma-2 direction and "
            "measure refusal rate on 200 held-out prompts [done] | "
            "evidence: results/steering_v1.json, results/steering_v2.json\n" + ACCRETED_NODE
        ),
        "entries": CLEAN_ENTRY,
        "extra_files": {
            "notes/runpod-setup.md": (
                "# GPU box setup\n\nPod template and mount points for the steering "
                "sweeps; rebuild with the standard image before each batch.\n"
            ),
            "results/tranche1.json": TRANCHE_RESULT,
        },
        "canaries": ["0.0021", "10,000", "shuffled-prompt", "perplexity"],
        "must_mention": ["paraphras", "0.031"],
        "done_id": "Q1.H1.E1",
        "prompt": (
            "The first tranche of the dose-response protocol scored; results are in "
            "results/tranche1.json — the gate read passes its registered bar, "
            "saturation is undecided, fluency is intact, which the registered ladder "
            "calls tier T2. Also record the design amendment we agreed: a "
            "paraphrased-prompt control arm is added (same prompts, "
            "meaning-preserving paraphrases), and any dose-response statistic must "
            "also survive it. Please do the session-end update of TREE.md and "
            "RESEARCH_LOG.md following the conventions in "
            ".claude/skills/research-log/SKILL.md — read it first."
        ),
    },
    "codename": {
        "nodes": (
            f"- Q1: {QUESTION} [open]\n"
            "  - Q1.H1: The refusal direction transfers across model families [open]\n"
            "    - Q1.H1.E2: Run the registered dose-response protocol over four "
            "steering coefficients (registration: notes/dose-response-registration.md) "
            "[running]\n"
        ),
        "entries": CLEAN_ENTRY,
        "extra_files": {
            "notes/dose-response-registration.md": REGISTRATION_DOC,
            "results/tranche1.json": TRANCHE_RESULT,
        },
        "must_mention": ["0.031"],
        "done_id": "Q1.H1.E2",
        "prompt": (
            "The dose-response scoring finished; results are in results/tranche1.json "
            "— the gate read passes, saturation is undecided, fluency intact: tier T2 "
            "on the registered ladder. Mark the experiment done with evidence, add "
            "the resulting claim as unvalidated, and append today's entry, following "
            "the conventions in .claude/skills/research-log/SKILL.md — read it first."
        ),
    },
}

ARMS: Final[dict[str, dict[str, Any]]] = {
    "base": {"docs_rev": BASE_REV, "validator_rev": BASE_REV, "hook": False},
    "norms": {"docs_rev": NEW_REV, "validator_rev": BASE_REV, "hook": False},
    "gate": {"docs_rev": NEW_REV, "validator_rev": NEW_REV, "hook": False},
    "hook": {"docs_rev": NEW_REV, "validator_rev": NEW_REV, "hook": True},
    # Altitude A/B: identical hooked setups differing only in whether the
    # docs and validator carry the altitude rules (node-length gate, notes/
    # relocation contract, codename hygiene).
    "prealt": {"docs_rev": PRE_ALTITUDE_REV, "validator_rev": PRE_ALTITUDE_REV, "hook": True},
    "alt": {"docs_rev": NEW_REV, "validator_rev": NEW_REV, "hook": True},
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
    for rel, content in files.items():
        target = workspace / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    (workspace / "scripts" / "validate_research.py").chmod(0o755)
    identity = ["-c", "user.email=eval@local", "-c", "user.name=eval"]
    for args in (["init", "-q"], ["add", "-A"], [*identity, "commit", "-q", "-m", "seed"]):
        subprocess.run(["git", *args], cwd=workspace, capture_output=True, check=False, timeout=30)
    return workspace


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
    task = TASKS[task_id]
    row.update(grade(workspace, transcript, SEED_DATE, canaries=tuple(task.get("canaries", ()))))
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
