#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Multi-session accumulation eval: does the altitude gate flatten the
growth curve that real project trees showed?

One workspace is carried through five chained agent sessions, each with a
fresh context window and a dated prompt: a protocol registration, a first
results tranche, an amendment plus instrument validation, the full tranche,
and a qualification plus a second registration. This is the schedule that
grew real nodes to 4,000-12,000 characters — every session hands the agent
more protocol text than fits a headline.

Arms: base (the pre-intervention harness, pinned) vs alt (the current
harness with the PostToolUse hook). Three chains per arm. Measured per
session: tree bytes, node count, max and total node text, new-entry length,
the arm's own validator verdict, hook activity, and cumulative survival of
ten regex canaries dictated across the sessions — the growth curve, its
flattening, and whether relocation loses what accumulation would have kept.

Run:  uv run scripts/run_chain_eval.py --chains 3 --out results/chains
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Final

from plain_language_graders import grade, new_entry_text
from run_plain_language_eval import SEED_DATE, build_workspace, run_claude_scoped

ANY_NODE_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*-\s+((?:[QHEC]\d\w*)(?:\.[QHEC]?\d\w*)*):\s+(.*)$"
)
CHAIN_ARMS: Final[tuple[str, ...]] = ("base", "alt")
SKILL_POINTER: Final[str] = (
    " Then append today's log entry, following the conventions in "
    ".claude/skills/research-log/SKILL.md — read it first and follow it."
)

SESSIONS: Final[tuple[dict[str, Any], ...]] = (
    {
        "date": "2026-08-23",
        "files": {},
        "canaries": (r"0\.0034", r"20,?000"),
        "prompt": (
            "Today is 2026-08-23. Before any scoring happens, register the "
            "dose-response protocol for steering strength as a new experiment "
            "under Q1.H1: coefficients {2.0, 4.0, 8.0, 16.0} on the same 200 "
            "held-out prompts, three seeds per cell. The per-cell noise standard "
            "deviation is 0.0034, measured from 32 random-direction control "
            "runs, and that is the null band for every read. Three reads, "
            "registered now: first, the dose-response gate — refusal rate "
            "regressed on log coefficient, and the bar is a positive slope with "
            "permutation p below 0.0005 over 20,000 shuffles of the coefficient "
            "labels; second, saturation — saturating if the fitted rise "
            "completes within one coefficient doubling, with a bootstrap "
            "interval excluding two doublings; third, a fluency guard — mean "
            "perplexity of steered completions must stay within 1.5 times "
            "baseline, otherwise a refusal rise is discounted as degeneration. "
            "And a verdict ladder, so a middling result cannot be argued "
            "sideways: tier 3 is a monotonic dose-response with intact fluency; "
            "tier 2, a rise at the high coefficient only with fluency intact; "
            "tier 1, a rise with degraded fluency; tier 0, a null. Please "
            "record this registration." + SKILL_POINTER
        ),
    },
    {
        "date": "2026-08-24",
        "files": {
            "results/tranche1.json": json.dumps(
                {
                    "read": "dose_gate",
                    "slope_per_log2_coefficient": 0.041,
                    "permutation_p": 0.0003,
                    "n_shuffles": 20000,
                    "fluency_ratio": 1.18,
                    "saturation": "undecided",
                    "tier": "T2",
                    "cells_scored": 8,
                    "cells_total": 12,
                    "seed": 0,
                },
                indent=2,
            )
        },
        "canaries": (r"0\.041", r"1\.18"),
        "prompt": (
            "Today is 2026-08-24. The first tranche of the dose-response "
            "protocol scored; results are in results/tranche1.json. The gate "
            "read passes its registered bar (slope 0.041 per doubling of the "
            "coefficient, permutation p 0.0003), saturation is undecided with "
            "eight of twelve cells scored, and fluency is intact at 1.18 times "
            "baseline — tier 2 on the registered ladder. Record the outcome in "
            "the tree." + SKILL_POINTER
        ),
    },
    {
        "date": "2026-08-25",
        "files": {
            "results/instrument_check.json": json.dumps(
                {
                    "planted_slope_recovery_bias": 0.0007,
                    "false_positives": "0/400",
                    "null_simulations": 400,
                    "decidable_amplitude_multiple": 4,
                },
                indent=2,
            )
        },
        "canaries": (r"0\.0007", r"shuffled"),
        "prompt": (
            "Today is 2026-08-25. Two records before the second tranche runs. "
            "First, a design amendment the team agreed on: a shuffled-prompt "
            "control is added — the same scoring on prompts with shuffled word "
            "order — and no dose-response statistic may survive it. Second, the "
            "instrument validation ran on simulations at matched noise "
            "(results/instrument_check.json): the slope estimator recovers "
            "planted slopes with bias 0.0007, reports zero false positives in "
            "400 null simulations, and the saturation read is only decidable "
            "when the rise amplitude exceeds four times the per-cell noise. "
            "Record both." + SKILL_POINTER
        ),
    },
    {
        "date": "2026-08-26",
        "files": {
            "results/tranche2.json": json.dumps(
                {
                    "read": "dose_gate",
                    "slope_per_log2_coefficient": 0.038,
                    "permutation_p": 0.0001,
                    "n_shuffles": 20000,
                    "fluency_ratio": 1.22,
                    "saturation": "saturating",
                    "saturation_doublings": 0.8,
                    "shuffled_control_max_slope": 0.002,
                    "tier": "T3",
                    "cells_scored": 12,
                    "cells_total": 12,
                    "seed": 0,
                },
                indent=2,
            )
        },
        "canaries": (r"0\.038", r"1\.22"),
        "prompt": (
            "Today is 2026-08-26. The full dose-response scored, all twelve "
            "cells (results/tranche2.json): slope 0.038 per coefficient "
            "doubling at permutation p 0.0001, the rise completes within 0.8 "
            "doublings so saturation is now decided as saturating, fluency "
            "holds at 1.22 times baseline, and the shuffled-prompt control "
            "shows a maximum null slope of 0.002 — tier 3 on the registered "
            "ladder. Update the experiment and record the resulting claim as "
            "unvalidated." + SKILL_POINTER
        ),
    },
    {
        "date": "2026-08-27",
        "files": {},
        "canaries": (r"1\.15", r"Mistral"),
        "prompt": (
            "Today is 2026-08-27. Two records from today's review meeting. "
            "First, a qualification: a reviewer pointed out the fluency guard's "
            "1.5-times threshold was never justified, so we agreed to also "
            "report a stricter 1.15-times read, under which the high-"
            "coefficient cells fail the guard and the ladder verdict drops to "
            "tier 2 — record the qualification without erasing the tier-3 "
            "read. Second, register the next protocol before any data exists: "
            "cross-model transfer — the same three reads and the same verdict "
            "ladder, applied to steering Mistral-7B with the Gemma-2 refusal "
            "direction, the same 200 prompts, three seeds, the same "
            "coefficient grid. Record both." + SKILL_POINTER
        ),
    },
)

PREDICTIONS: Final[str] = """# Predictions, registered before the chain sweep

Setup: five chained sessions on one workspace (registration, first tranche,
amendment plus instrument validation, full tranche, qualification plus a
second registration), fresh context per session, arms base (pre-intervention,
pinned 3cc8ff3) vs alt (current harness, hooked), 3 chains per arm, sonnet.

1. base: max node text grows with session index, crossing 2,000 characters
   by session 3 and 3,000 by session 5 in at least 2 of 3 chains — the
   real-project accretion curve reproduced in miniature.
2. alt: max node text stays at or under 1,200 in every session of every
   chain, and the protocol, amendment, and qualification content lands in
   notes/ (at least 3 new documents by session 5 in every chain).
3. Tree bytes at session 5: alt at most two-thirds of base (headlines with
   pointers vs inlined protocols). Log growth is similar across arms, since
   entry length is deliberately ungated.
4. Information: cumulative canary survival at session 5 is at least 9 of 10
   patterns in both arms — the arms differ in where content lives, not in
   whether it survives.
5. Compliance: the arm's own validator passes at session end in at least 14
   of 15 alt session records; the hook fires with failure feedback at least
   once in a third or more of alt sessions.
"""

log = logging.getLogger("chain-eval")


def census(tree_text: str) -> dict[str, int]:
    lengths = [
        len(m.group(2).split("| evidence:")[0].rstrip())
        for line in tree_text.splitlines()
        if (m := ANY_NODE_RE.match(line))
    ]
    return {"n_nodes": len(lengths), "sum_node_chars": sum(lengths)}


def cumulative_canaries(workspace: Path, upto: int) -> tuple[int, int]:
    patterns = [c for sess in SESSIONS[:upto] for c in sess["canaries"]]
    blob = "\n".join(
        p.read_text(errors="replace")
        for p in sorted(workspace.rglob("*.md"))
        if ".git" not in p.parts
    )
    return sum(1 for pat in patterns if re.search(pat, blob)), len(patterns)


def session_row(
    workspace: Path, arm: str, chain_idx: int, k: int, prev_date: str, outcome: dict[str, Any]
) -> dict[str, Any]:
    transcript = outcome["stdout"]
    final = outcome["final"]
    tree_text = (workspace / "TREE.md").read_text()
    log_text = (workspace / "RESEARCH_LOG.md").read_text()
    present, total = cumulative_canaries(workspace, k)
    row: dict[str, Any] = {
        "key": f"ch|{arm}|c{chain_idx}|s{k}",
        "arm": arm,
        "chain": chain_idx,
        "session": k,
        "date": SESSIONS[k - 1]["date"],
        "tree_bytes": len(tree_text),
        "log_bytes": len(log_text),
        **census(tree_text),
        "entry_chars": len(new_entry_text(log_text, prev_date).strip()),
        "canaries_cum_present": present,
        "canaries_cum_total": total,
        "num_turns": int(final.get("num_turns", 0)),
        "cost_usd": float(final.get("total_cost_usd") or 0.0),
        "timed_out": outcome["timed_out"],
        "is_error": bool(final.get("is_error", False)) or outcome["timed_out"],
        "usage_limited": "hit your session limit" in transcript
        or "usage limit" in transcript.lower(),
        "ts": time.strftime("%FT%T"),
    }
    row.update(grade(workspace, transcript, prev_date))
    return row


def run_chain(arm: str, chain_idx: int, args: argparse.Namespace) -> list[dict[str, Any]]:
    ws_key = f"ch_{arm}_c{chain_idx}"
    workspace = build_workspace("dictation", arm, ws_key)
    artefacts = args.out / "artifacts" / ws_key
    artefacts.mkdir(parents=True, exist_ok=True)
    identity = ["-c", "user.email=eval@local", "-c", "user.name=eval"]
    rows: list[dict[str, Any]] = []
    prev_date = SEED_DATE
    for k, sess in enumerate(SESSIONS, start=1):
        for rel, content in sess["files"].items():
            target = workspace / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        outcome = run_claude_scoped(sess["prompt"], workspace, args.model, args.timeout)
        (artefacts / f"s{k}.transcript.jsonl").write_text(outcome["stdout"])
        shutil.copy2(workspace / "TREE.md", artefacts / f"s{k}.TREE.md")
        shutil.copy2(workspace / "RESEARCH_LOG.md", artefacts / f"s{k}.RESEARCH_LOG.md")
        row = session_row(workspace, arm, chain_idx, k, prev_date, outcome)
        rows.append(row)
        for git_args in (["add", "-A"], [*identity, "commit", "-q", "-m", f"session {k}"]):
            subprocess.run(
                ["git", *git_args], cwd=workspace, capture_output=True, check=False, timeout=60
            )
        if row["usage_limited"] or row["is_error"]:
            log.warning("%s aborted (usage_limited=%s)", row["key"], row["usage_limited"])
            break
        prev_date = sess["date"]
    return rows


def completed_chains(out_file: Path) -> tuple[set[tuple[str, int]], list[str]]:
    """Chains with all sessions recorded, plus the raw lines of only those."""
    rows_by_chain: dict[tuple[str, int], list[str]] = {}
    if out_file.is_file():
        for line in out_file.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            rows_by_chain.setdefault((row["arm"], row["chain"]), []).append(line)
    done = {ck for ck, lines in rows_by_chain.items() if len(lines) == len(SESSIONS)}
    keep = [line for ck in sorted(done) for line in rows_by_chain[ck]]
    return done, keep


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chains", type=int, default=3)
    parser.add_argument("--arms", type=lambda s: s.split(","), default=list(CHAIN_ARMS))
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--out", type=Path, default=Path("results/chains"))
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
    done, keep_lines = completed_chains(out_file)
    if out_file.is_file():
        out_file.write_text("".join(line + "\n" for line in keep_lines))
    jobs = [(arm, c) for arm in args.arms for c in range(args.chains) if (arm, c) not in done]
    log.info("%d chains to run (%d complete)", len(jobs), len(done))
    lock = threading.Lock()
    stop = threading.Event()

    def submit(job: tuple[str, int]) -> list[dict[str, Any]]:
        if stop.is_set():
            return []
        return run_chain(*job, args)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(submit, job): job for job in jobs}
        for future in as_completed(futures):
            rows = future.result()
            if not rows:
                continue
            if any(r["usage_limited"] for r in rows):
                log.warning("usage limit — stopping sweep; re-run to resume")
                stop.set()
                continue
            if len(rows) < len(SESSIONS):
                log.warning("chain %s incomplete — not recording", rows[0]["key"])
                continue
            with lock, out_file.open("a") as sink:
                for row in rows:
                    sink.write(json.dumps(row) + "\n")
            tail = rows[-1]
            log.info(
                "%s|c%d complete — s5 tree=%dB max_node=%d notes=%d canaries=%d/%d $%.2f",
                tail["arm"],
                tail["chain"],
                tail["tree_bytes"],
                tail["max_node_chars"],
                tail["notes_md_files"],
                tail["canaries_cum_present"],
                tail["canaries_cum_total"],
                sum(r["cost_usd"] for r in rows),
            )
    log.info("chain sweep finished")
    return 0


if __name__ == "__main__":
    sys.exit(main())
