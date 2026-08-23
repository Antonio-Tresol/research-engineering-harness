#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Fresh-reader comprehension probe: can a cheap model answer factual
questions about the project from the research tree alone?

Legibility is the construct every other metric proxies; this measures it
directly. A reader model (haiku) receives one tree file inline — no tools,
no repository — and answers curated factual questions about the real
gemma4-emotion-vectors project. Questions come in two tiers: state
questions a headline-level tree should answer, and detail questions whose
answers the altitude rules deliberately relocate into notes/ documents.

Conditions: the original 94KB tree, each brownfield-migrated tree alone,
and each migrated tree plus the notes/ documents the migration created
(the detail tier's recovery path). Answers are graded by regex with
abstention detected separately, so honest "not in the tree" is
distinguished from a confidently wrong answer.

Run:  uv run scripts/run_comprehension_probe.py --brownfield results/brownfield
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Final

from run_brownfield_eval import SOURCE, SOURCE_REV

QUESTIONS: Final[tuple[dict[str, str], ...]] = (
    {
        "id": "s1",
        "tier": "state",
        "q": "Did the mean-centered PCA on the base model reproduce the paper's "
        "circumplex geometry, and what peak correlation was measured between the "
        "first principal component and lexicon valence?",
        "answer_re": r"0\.83",
    },
    {
        "id": "s2",
        "tier": "state",
        "q": "After instruction tuning, what happened to the valence principal component?",
        "answer_re": r"PC3|demot",
    },
    {
        "id": "s3",
        "tier": "state",
        "q": "Under which readout do the story-derived emotion vectors work as "
        "scenario-level emotion detectors, according to the claim that survived "
        "its falsification gate?",
        "answer_re": r"cent(er|re)",
    },
    {
        "id": "s4",
        "tier": "state",
        "q": "What was the final status of the claim that emotion vectors carry "
        "no detectable causal preference content, and why?",
        "answer_re": r"fail|artifact|wrong.{0,14}position",
    },
    {
        "id": "s5",
        "tier": "state",
        "q": "What is the status of research question Q2, about detecting the "
        "steered emotional direction, and why?",
        "answer_re": r"abandon|pivot",
    },
    {
        "id": "s6",
        "tier": "state",
        "q": "Which collaborator contributed the emotion-triples prompt substrate "
        "for the temporal-dynamics question, and in which commit?",
        "answer_re": r"Peyton|68b7d42",
    },
    {
        "id": "s7",
        "tier": "state",
        "q": "Was scaling the number of stories per emotion enough to improve the "
        "twelve-way battery diagonal?",
        "answer_re": r"saturat|(stayed |remained )?flat",
    },
    {
        "id": "s8",
        "tier": "state",
        "q": "Does the project conclude that instruction tuning erases the emotional geometry?",
        "answer_re": r"demot|does not erase",
    },
    {
        "id": "d1",
        "tier": "detail",
        "q": "What per-token noise standard deviation did the trajectory "
        "instrument calibration measure at layer 33?",
        "answer_re": r"0\.0021",
    },
    {
        "id": "d2",
        "tier": "detail",
        "q": "In the numerical-template confound diagnostic, how many of the "
        "tracked probe directions had the registered correct sign?",
        "answer_re": r"11\s*(of|/)\s*11",
    },
    {
        "id": "d3",
        "tier": "detail",
        "q": "After the extraction-fix probe rescore, what is the corrected "
        "probe-Elo correlation headline for the preferences claim?",
        "answer_re": r"0\.64",
    },
    {
        "id": "d4",
        "tier": "detail",
        "q": "How many stories were re-extracted in the post-fix GPU run of the "
        "extraction-offset audit?",
        "answer_re": r"6,?278",
    },
    {
        "id": "d5",
        "tier": "detail",
        "q": "For the self-generated n=256 lineage, what was the minimum contrast "
        "cosine after the padding fix, and did it clear the registered 0.995 bar?",
        "answer_re": r"0\.99499|below the (0\.995 )?bar",
    },
    {
        "id": "d6",
        "tier": "detail",
        "q": "Which arXiv paper is cited as the closest prior work steering "
        "sycophancy with persona vectors?",
        "answer_re": r"2605\.21006",
    },
)

ABSTAIN_RE: Final[re.Pattern[str]] = re.compile(
    r"not in the tree|not (found|stated|present|contained|available|recorded)"
    r"|does not (appear|contain|state|include|specify|mention)"
    r"|tree does not|cannot (be )?(determin|answer|find)"
    r"|no (information|mention)|unable to (find|determine)",
    re.IGNORECASE,
)

READER_TEMPLATE: Final[str] = """You are answering questions about a research \
project using ONLY the research record below. Answer in one or two sentences \
with the specific fact. If the record does not contain the answer, say \
exactly: "Not in the tree."

<record>
{record}
</record>

Question: {question}"""

PREDICTIONS: Final[str] = """# Predictions, registered before the probe runs

Conditions: original 94KB tree; each brownfield-migrated tree alone; each
migrated tree plus its new notes/ documents. Reader: haiku, no tools, 2
repeats per question. 8 state questions, 6 detail questions.

1. State tier: every migrated tree scores at least as high as the original
   tree; the original's state accuracy lands at 55-80% (the facts are
   present but buried in 4,000-12,000-character nodes).
2. Detail tier: the original beats migrated-tree-alone (those numbers are
   deliberately relocated out of the tree); migrated tree plus notes
   recovers to within one question of the original or better.
3. Honesty: on detail questions the migrated-tree-alone condition abstains
   more than it answers wrongly (the tree says where the detail lives);
   the original condition's failures skew toward wrong answers.
4. Reader cost per question: original at least twice the migrated-alone
   condition (24k-token input vs a headline-sized tree).
"""

log = logging.getLogger("comprehension-probe")


def ask_reader(record: str, question: str, model: str, timeout: int) -> dict[str, Any]:
    prompt = READER_TEMPLATE.format(record=record, question=question)
    proc = subprocess.run(
        ["claude", "-p", "--output-format", "json", "--model", model, "--max-turns", "1"],
        input=prompt,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    try:
        final = json.loads(proc.stdout)
    except json.JSONDecodeError:
        final = {}
    return {
        "answer": str(final.get("result", ""))[:400],
        "cost_usd": float(final.get("total_cost_usd") or 0.0),
        "is_error": bool(final.get("is_error", False)) or proc.returncode != 0,
    }


def classify(answer: str, answer_re: str) -> str:
    if re.search(answer_re, answer, re.IGNORECASE):
        return "correct"
    if ABSTAIN_RE.search(answer):
        return "abstain"
    return "wrong"


def load_conditions(brownfield_out: Path) -> dict[str, str]:
    """Condition name -> full record text handed to the reader."""
    original = subprocess.run(
        ["git", "show", f"{SOURCE_REV}:TREE.md"],
        cwd=SOURCE,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    ).stdout
    conditions = {"original": original}
    runs_file = brownfield_out / "runs.jsonl"
    if not runs_file.is_file():
        return conditions
    for line in runs_file.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        artefacts = Path(row["artifacts"])
        tree = artefacts / "TREE.md"
        if not tree.is_file():
            continue
        name = f"migrated_r{row['run']}"
        tree_text = tree.read_text()
        conditions[name] = tree_text
        notes_chunks = [
            (artefacts / "notes" / Path(rel).name).read_text(errors="replace")
            for rel in row.get("notes_md_new", ())
            if (artefacts / "notes" / Path(rel).name).is_file()
        ]
        if notes_chunks:
            record = tree_text + "\n\n# Notes documents\n\n" + "\n\n---\n\n".join(notes_chunks)
            conditions[f"{name}_notes"] = record[:200_000]
    return conditions


def run_probe(args: argparse.Namespace) -> None:
    conditions = load_conditions(args.brownfield)
    log.info("conditions: %s", ", ".join(f"{k} ({len(v)}B)" for k, v in conditions.items()))
    out_file = args.out / "runs.jsonl"
    done: set[str] = set()
    if out_file.is_file():
        done = {
            json.loads(line)["key"] for line in out_file.read_text().splitlines() if line.strip()
        }
    jobs = [
        (cond, q, rep)
        for cond in conditions
        for q in QUESTIONS
        for rep in range(args.reps)
        if f"cp|{cond}|{q['id']}|r{rep}" not in done
    ]
    log.info("%d probe calls to make (%d recorded)", len(jobs), len(done))
    lock = threading.Lock()

    def one(job: tuple[str, dict[str, str], int]) -> dict[str, Any]:
        cond, q, rep = job
        outcome = ask_reader(conditions[cond], q["q"], args.model, args.timeout)
        return {
            "key": f"cp|{cond}|{q['id']}|r{rep}",
            "condition": cond,
            "qid": q["id"],
            "tier": q["tier"],
            "rep": rep,
            "class": classify(outcome["answer"], q["answer_re"]),
            "answer": outcome["answer"],
            "cost_usd": outcome["cost_usd"],
            "is_error": outcome["is_error"],
            "record_bytes": len(conditions[cond]),
            "model": args.model,
            "ts": time.strftime("%FT%T"),
        }

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(one, job) for job in jobs]
        for future in as_completed(futures):
            row = future.result()
            with lock, out_file.open("a") as sink:
                sink.write(json.dumps(row) + "\n")
            log.info("%s -> %s ($%.4f)", row["key"], row["class"], row["cost_usd"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brownfield", type=Path, default=Path("results/brownfield"))
    parser.add_argument("--reps", type=int, default=2)
    parser.add_argument("--model", default="haiku")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--out", type=Path, default=Path("results/comprehension"))
    args = parser.parse_args()
    args.out = args.out.resolve()
    args.brownfield = args.brownfield.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(args.out / "run.log")],
    )
    predictions = args.out / "predictions.md"
    if not predictions.exists():
        predictions.write_text(PREDICTIONS)
    run_probe(args)
    log.info("probe finished")
    return 0


if __name__ == "__main__":
    sys.exit(main())
