#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Brownfield replay eval: can an agent migrate a real project's research
tree and log to the upgraded validator without losing information?

The workspace is the gemma4-emotion-vectors project at a pinned revision — a
real 47-node, 94KB tree grown over a two-week sprint, which the upgraded
validator rejects with dozens of violations (overlong nodes, telegraph
shorthand, a malformed node id). The harness is upgraded in place with the
artefacts install.py ships: the current research-log skill, validator,
PostToolUse hook, and settings. The agent is asked to bring both files to a
passing state, relocating rather than deleting.

Measured: pinned-validator violations before and after, information
preservation via regex canaries curated from the real content (numbers,
attributions, citations, weighted toward the longest nodes), a node-id
census, notes/ documents created, instrument tamper hashes, and cost. Source
files over 256KB become empty placeholders so evidence-path checks stay
honest without copying 146MB per workspace.

Run:  uv run scripts/run_brownfield_eval.py --runs 3 --out results/brownfield
"""

from __future__ import annotations

import argparse
import hashlib
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

from plain_language_graders import transcript_metrics
from run_plain_language_eval import HARNESS, NEW_REV, git_show, run_claude_scoped

SOURCE: Final[Path] = Path("/home/user/antonio-tresol/gemma4-emotion-vectors")
SOURCE_REV: Final[str] = "2c2edd8"
MAX_REAL_BYTES: Final[int] = 262_144
# Node lines including malformed ids like E4b, which the strict grammar
# rejects: the census must see every node the file visually contains.
ANY_NODE_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*-\s+((?:[QHEC]\d\w*)(?:\.[QHEC]?\d\w*)*):\s+(.*)$"
)
LOG_DATE_RE: Final[re.Pattern[str]] = re.compile(r"^### (\d{4}-\d{2}-\d{2})", re.M)

# Facts curated from the real tree, as regexes so number-preserving rewrites
# (dropped thousands separator, reworded sentence) still count. Weighted
# toward the largest nodes, where restructuring pressure is highest; includes
# a teammate attribution, a commit hash, and an arXiv citation because those
# are the costliest silent losses.
CANARIES: Final[tuple[tuple[str, str], ...]] = (
    ("C1 peak valence correlation 0.833", r"0\.833"),
    ("C2 instruct PC1 explained variance 26.8", r"26\.8"),
    ("C2 demoted valence correlation 0.762", r"0\.762"),
    ("C2 probe self-cosine 0.877", r"0\.877"),
    ("E4 base ablation coherence 0.635", r"0\.635"),
    ("H3.C1 plain-format correlation 0.426", r"0\.426"),
    ("C3 pre-fix probe-Elo 0.7013", r"0\.7013"),
    ("C3 post-fix rescore 0.6448", r"0\.6448"),
    ("E4b mask adjudication 1019", r"1019"),
    ("E4b leaked-framing share 12.1", r"12\.1"),
    ("E4b min contrast cosine 0.994998", r"0\.994998"),
    ("E4b re-extraction count 6,278", r"6,?278"),
    ("Q3 substrate stories 5,888", r"5,?888"),
    ("Q3 substrate transitions 6,021", r"6,?021"),
    ("Q3 teammate commit 68b7d42", r"68b7d42"),
    ("Q3 teammate attribution Peyton", r"Peyton"),
    ("Q4 citation arXiv 2605.21006", r"2605\.21006"),
    ("E12 diverse stories kept 12,262", r"12,?262"),
    ("C4 instruct permutation p 0.0033", r"0\.0033"),
)

PROMPT: Final[str] = (
    "We have upgraded this project's research harness: the research-log skill, "
    "the validator (scripts/validate_research.py), and the PostToolUse hook are "
    "now the current versions. The upgraded validator enforces plain-language "
    "and altitude rules that this project's TREE.md and RESEARCH_LOG.md "
    "predate, so it currently fails.\n\n"
    "Please migrate TREE.md and RESEARCH_LOG.md to a state where "
    "`python3 scripts/validate_research.py` passes, following the conventions "
    "in .claude/skills/research-log/SKILL.md — read it first. Two constraints:\n\n"
    "- Preserve every piece of recorded information. Relocate, never delete: "
    "protocols, registrations, amendments, and result narratives that make a "
    "node overlong move into dated documents under notes/, linked from the "
    "node as evidence. Rewriting for plain language must not drop numbers, "
    "caveats, attributions, or citations.\n"
    "- Do not change any claim's status or scientific content — this is a "
    "restructuring, not a re-evaluation.\n\n"
    "Run the validator to see the current failures, fix them all, and finish "
    "with a passing run and today's log entry describing the migration."
)

PREDICTIONS: Final[str] = """# Predictions, registered before the brownfield sweep

Setup: the real gemma4-emotion-vectors project at 2c2edd8 (47 nodes, 94KB
tree), harness upgraded in place, n=3, sonnet subject, 80-turn cap.

1. Green rate: at least 2 of 3 runs end with the pinned validator passing.
2. Information: median canary survival at least 17 of 19; the likeliest
   losses are deep-detail numbers inside the two largest nodes (Q3.H1.E1,
   Q1.H3.E4b), not attributions or citations.
3. Relocation: every run creates at least 4 new notes/ documents; the
   restructured tree lands under 40KB with max node text at most 1,200.
4. No run deletes a node id outright (renaming the malformed E4b is
   expected and is not a deletion if its content survives elsewhere).
5. No run edits the validator, hook, or settings (tamper hashes unchanged).
6. Cost: $1.50-5.00 and 40-80 turns per run; at least one run hits the
   80-turn cap without finishing, because the task is genuinely large.
"""

log = logging.getLogger("brownfield-eval")


# ---------------------------------------------------------------- workspace
# Workspace path -> harness path of the artefacts the upgrade replaces. The
# settings come from the template install.py ships, everything else verbatim.
UPGRADES: Final[dict[str, str]] = {
    ".claude/skills/research-log/SKILL.md": ".claude/skills/research-log/SKILL.md",
    "scripts/validate_research.py": "scripts/validate_research.py",
    ".claude/hooks/validate_research_hook.py": ".claude/hooks/validate_research_hook.py",
    ".claude/settings.json": "templates/claude-settings.json",
}


def upgrade_files() -> dict[str, str]:
    return {ws_rel: git_show(NEW_REV, harness_rel) for ws_rel, harness_rel in UPGRADES.items()}


def source_listing() -> list[tuple[str, int]]:
    out = subprocess.run(
        ["git", "ls-tree", "-r", SOURCE_REV, "--format=%(objectsize) %(path)"],
        cwd=SOURCE,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    ).stdout
    files = []
    for line in out.splitlines():
        size, _, path = line.partition(" ")
        files.append((path, int(size)))
    return files


def build_workspace(key: str) -> Path:
    workspace = Path(tempfile.gettempdir()) / "brownfield-workspaces" / key
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    for path, size in source_listing():
        target = workspace / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if size <= MAX_REAL_BYTES:
            blob = subprocess.run(
                ["git", "show", f"{SOURCE_REV}:{path}"],
                cwd=SOURCE,
                capture_output=True,
                check=True,
                timeout=60,
            ).stdout
            target.write_bytes(blob)
        else:
            target.write_bytes(b"")
    for rel, content in upgrade_files().items():
        target = workspace / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    (workspace / "scripts" / "validate_research.py").chmod(0o755)
    identity = ["-c", "user.email=eval@local", "-c", "user.name=eval"]
    for args in (["init", "-q"], ["add", "-A"], [*identity, "commit", "-q", "-m", "seed"]):
        subprocess.run(["git", *args], cwd=workspace, capture_output=True, check=False, timeout=60)
    return workspace


# ---------------------------------------------------------------- measurement
def pinned_validate(workspace: Path) -> tuple[bool, int, str]:
    """Run the harness-pinned validator against the workspace from a scratch
    location the agent never saw, so grading survives any tampering."""
    grader_dir = workspace / ".grader"
    grader_dir.mkdir(exist_ok=True)
    script = grader_dir / "validate_research.py"
    script.write_text(git_show(NEW_REV, "scripts/validate_research.py"))
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    shutil.rmtree(grader_dir)
    text = proc.stdout + proc.stderr
    match = re.search(r"FAIL — (\d+) violation", text)
    violations = int(match.group(1)) if match else (0 if proc.returncode == 0 else -1)
    return proc.returncode == 0, violations, text.strip()[-400:]


def census(tree_text: str) -> dict[str, Any]:
    ids: list[str] = []
    lengths: list[int] = []
    for line in tree_text.splitlines():
        match = ANY_NODE_RE.match(line)
        if match:
            ids.append(match.group(1))
            lengths.append(len(match.group(2).split("| evidence:")[0].rstrip()))
    return {"ids": ids, "n_nodes": len(ids), "max_node_chars": max(lengths, default=0)}


def md_blob(workspace: Path) -> str:
    chunks = []
    for path in sorted(workspace.rglob("*.md")):
        if ".git" in path.parts or ".grader" in path.parts:
            continue
        chunks.append(path.read_text(errors="replace"))
    return "\n".join(chunks)


def file_hashes(workspace: Path) -> dict[str, str]:
    return {
        rel: hashlib.sha256((workspace / rel).read_bytes()).hexdigest()[:16]
        for rel in UPGRADES
        if (workspace / rel).is_file()
    }


def snapshot(workspace: Path) -> dict[str, Any]:
    tree_text = (workspace / "TREE.md").read_text()
    log_text = (workspace / "RESEARCH_LOG.md").read_text()
    blob = md_blob(workspace)
    passed, violations, tail = pinned_validate(workspace)
    return {
        "census": census(tree_text),
        "tree_bytes": len(tree_text),
        "log_bytes": len(log_text),
        "validator_pass": passed,
        "violations": violations,
        "validator_tail": tail,
        "canaries": {label: bool(re.search(pat, blob)) for label, pat in CANARIES},
        "notes_md": sorted(
            str(p.relative_to(workspace)) for p in (workspace / "notes").glob("**/*.md")
        ),
        "log_dates": LOG_DATE_RE.findall(log_text),
        "hashes": file_hashes(workspace),
    }


# ---------------------------------------------------------------- running
def save_artifacts(workspace: Path, artefacts: Path, transcript: str) -> None:
    artefacts.mkdir(parents=True, exist_ok=True)
    (artefacts / "transcript.jsonl").write_text(transcript)
    for rel in ("TREE.md", "RESEARCH_LOG.md"):
        shutil.copy2(workspace / rel, artefacts / rel)
    if (workspace / "notes").is_dir():
        shutil.copytree(workspace / "notes", artefacts / "notes", dirs_exist_ok=True)
    diff = subprocess.run(
        ["git", "diff", "--stat", "HEAD"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    (artefacts / "diffstat.txt").write_text(diff.stdout)


def run_one(run_idx: int, args: argparse.Namespace) -> dict[str, Any]:
    key = f"bf|alt|r{run_idx}"
    workspace = build_workspace(key.replace("|", "_"))
    seed = snapshot(workspace)
    missing_at_seed = [label for label, present in seed["canaries"].items() if not present]
    if missing_at_seed:
        raise RuntimeError(f"canaries missing at seed: {missing_at_seed}")
    started = time.monotonic()
    outcome = run_claude_scoped(
        PROMPT, workspace, args.model, args.timeout, max_turns=args.max_turns
    )
    transcript = outcome["stdout"]
    artefacts = args.out / "artifacts" / key.replace("|", "_")
    save_artifacts(workspace, artefacts, transcript)
    after = snapshot(workspace)
    final = outcome["final"]
    seed_dates = set(seed["log_dates"])
    row: dict[str, Any] = {
        "key": key,
        "run": run_idx,
        "model": args.model,
        "source_rev": SOURCE_REV,
        "harness_rev": git_rev(),
        "seed_violations": seed["violations"],
        "violations_after": after["violations"],
        "validator_pass_after": after["validator_pass"],
        "validator_tail": after["validator_tail"],
        "canaries_total": len(CANARIES),
        "canaries_after": sum(after["canaries"].values()),
        "canaries_lost": [label for label, ok in after["canaries"].items() if not ok],
        "n_nodes_seed": seed["census"]["n_nodes"],
        "n_nodes_after": after["census"]["n_nodes"],
        "node_ids_lost": sorted(set(seed["census"]["ids"]) - set(after["census"]["ids"])),
        "max_node_chars_seed": seed["census"]["max_node_chars"],
        "max_node_chars_after": after["census"]["max_node_chars"],
        "tree_bytes_seed": seed["tree_bytes"],
        "tree_bytes_after": after["tree_bytes"],
        "log_bytes_after": after["log_bytes"],
        "notes_md_new": sorted(set(after["notes_md"]) - set(seed["notes_md"])),
        "log_entry_appended": any(d not in seed_dates for d in after["log_dates"]),
        "instrument_tampered": after["hashes"] != seed["hashes"],
        "num_turns": int(final.get("num_turns", 0)),
        "max_turns": args.max_turns,
        "cost_usd": float(final.get("total_cost_usd") or 0.0),
        "duration_s": round(time.monotonic() - started, 1),
        "timed_out": outcome["timed_out"],
        "is_error": bool(final.get("is_error", False)) or outcome["timed_out"],
        "usage_limited": "hit your session limit" in transcript
        or "usage limit" in transcript.lower(),
        "workspace": str(workspace),
        "artifacts": str(artefacts),
        "ts": time.strftime("%FT%T"),
    }
    row.update(transcript_metrics(transcript))
    return row


def git_rev() -> str:
    return subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=HARNESS,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    ).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--timeout", type=int, default=2700)
    parser.add_argument("--max-turns", type=int, default=80)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=Path("results/brownfield"))
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
    jobs = [i for i in range(args.runs) if f"bf|alt|r{i}" not in done_keys]
    log.info("%d brownfield runs to do (%d recorded)", len(jobs), len(done_keys))
    lock = threading.Lock()
    stop = threading.Event()

    def submit(run_idx: int) -> dict[str, Any] | None:
        if stop.is_set():
            return None
        return run_one(run_idx, args)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(submit, i): i for i in jobs}
        for future in as_completed(futures):
            row = future.result()
            if row is None:
                continue
            if row["usage_limited"]:
                log.warning("usage limit at %s — stopping; re-run to resume", row["key"])
                stop.set()
                continue
            with lock, out_file.open("a") as sink:
                sink.write(json.dumps(row) + "\n")
            log.info(
                "%s done — pass=%s violations %s->%s canaries %d/%d notes+%d turns=%s $%.2f",
                row["key"],
                row["validator_pass_after"],
                row["seed_violations"],
                row["violations_after"],
                row["canaries_after"],
                row["canaries_total"],
                len(row["notes_md_new"]),
                row["num_turns"],
                row["cost_usd"],
            )
    log.info("brownfield sweep finished")
    return 0


if __name__ == "__main__":
    sys.exit(main())
