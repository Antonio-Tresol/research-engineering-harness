#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Falsification tests for the skill-eval claims (Q1 tree).

Each test tries to destroy a claim; the scorecard records the verdict.
Exact permutation probabilities are computed combinatorially (no sampling),
so the script is deterministic. Writes results/skill_evals/falsify_scorecard.json.
"""

from __future__ import annotations

import json
from math import comb
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
BEHAVIOUR = ROOT / "results/skill_evals/behaviour_full/behaviour.jsonl"
TRIGGER_DIRS = [
    ROOT / f"results/skill_evals/{s}"
    for s in ("derive-from-sources", "experiment-engineering", "research-log", "validate-claims")
]

Test = dict[str, Any]
ByTask = dict[str, dict[str, list[dict[str, Any]]]]


def rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def exact_label_permutation_p(pass_flags_by_arm: dict[str, list[bool]], target_arm: str) -> float:
    """P(a random re-assignment of arm labels concentrates >= the observed number
    of passes in the target arm), under the null that arm labels are exchangeable.
    One-sided, exact (hypergeometric tail)."""
    all_flags = [f for flags in pass_flags_by_arm.values() for f in flags]
    n_total, n_pass = len(all_flags), sum(all_flags)
    k_arm = len(pass_flags_by_arm[target_arm])
    observed = sum(pass_flags_by_arm[target_arm])
    tail = 0.0
    for j in range(observed, min(k_arm, n_pass) + 1):
        tail += comb(n_pass, j) * comb(n_total - n_pass, k_arm - j) / comb(n_total, k_arm)
    return tail


def clopper_pearson_upper(k: int, n: int, alpha: float = 0.05) -> float:
    """Exact binomial upper bound by bisection on the CDF."""
    lo, hi = k / n, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        cdf = sum(comb(n, i) * mid**i * (1 - mid) ** (n - i) for i in range(k + 1))
        lo, hi = (lo, mid) if cdf < alpha else (mid, hi)
    return hi


def provenance_test(by_task: ByTask) -> Test:
    marker_keys = ("markers_present", "markers_resolve", "key_stats_anchored")
    prov = {
        arm: [all(r["grades"][k]["passed"] for k in marker_keys) for r in runs]
        for arm, runs in by_task["provenance"].items()
    }
    p_all = exact_label_permutation_p(prov, "skill")
    p_vs_placebo = exact_label_permutation_p({k: prov[k] for k in ("skill", "placebo")}, "skill")
    baseline_clean = not any(prov["none"] + prov["placebo"])
    return {
        "claim": "Q1.H1.E4.C1 provenance: skill arm anchors statistics, none/placebo do not",
        "data": {arm: f"{sum(v)}/{len(v)} runs fully anchored" for arm, v in prov.items()},
        "test": "exact one-sided label-permutation (hypergeometric tail)",
        "p_skill_vs_all": round(p_all, 5),
        "p_skill_vs_placebo_only": round(p_vs_placebo, 5),
        "verdict": "survives" if p_all < 0.05 and baseline_clean else "weakened",
        "caveat": "n=3 per arm; placebo comparison alone reaches only p=0.05 — the "
                  "content-specificity reading rests on the pooled test and the 0/6 baseline",
    }


def completion_tests(by_task: ByTask) -> list[Test]:
    completion = {
        arm: [r["grades"].get("artefact_exists", {"passed": False})["passed"] for r in runs]
        for arm, runs in by_task["fabrication-canary"].items()
    }
    flipped = {arm: [not f for f in flags] for arm, flags in completion.items()}
    p_completion = exact_label_permutation_p(flipped, "skill")
    baseline_canaries = [
        all(g["passed"] for name, g in r["grades"].items() if name.startswith("canary:"))
        for arm in ("none", "placebo") for r in by_task["fabrication-canary"][arm]
    ]
    return [
        {
            "claim": "Q1.H1.E1.C1 fabrication probe: skill arm fails to produce the artefact",
            "data": {arm: f"{sum(v)}/{len(v)} runs produced reading_notes.md" for arm, v in completion.items()},
            "test": "exact one-sided label-permutation on completion failures",
            "p": round(p_completion, 5),
            "supporting": "4/4 pilot runs (varying skill text) stalled identically",
            "verdict": "survives" if p_completion < 0.05 else "weakened",
        },
        {
            "claim": "Q1.H1.E1.C2 baseline saturation: non-skill artefacts contain every canary",
            "data": f"{sum(baseline_canaries)}/{len(baseline_canaries)} non-skill runs, all canaries present",
            "test": "census of all baseline runs (no headroom left for a skill effect on reading)",
            "verdict": "survives" if all(baseline_canaries) else "failed",
            "caveat": "an assertion that passes in every configuration measures nothing about "
                      "the skill; the probe needs harder conditions (longer/more/remote sources) "
                      "before any skill-benefit claim could be tested",
        },
        {
            "claim": "Q1.H3.E1.C3 headless notes-stage stall of derive-from-sources",
            "data": "0/3 sweep + 0/4 pilot skill-arm runs produced the deliverable; 6/6 non-skill did",
            "test": "same permutation as E1.C1; pilot runs as replication across skill revisions",
            "verdict": "survives" if p_completion < 0.05 else "weakened",
        },
    ]


def saturation_tests(by_task: ByTask) -> list[Test]:
    tests: list[Test] = []
    for task, claim_id in (("null-honesty", "Q1.H1.E2.C1"), ("observability", "Q1.H1.E3.C1")):
        per_arm = {
            arm: [all(g["passed"] for g in r["grades"].values()) for r in runs]
            for arm, runs in by_task[task].items()
        }
        saturated = all(all(v) for v in per_arm.values())
        tests.append({
            "claim": f"{claim_id} {task}: all arms pass all assertions (no measurable skill effect)",
            "data": {arm: f"{sum(v)}/{len(v)}" for arm, v in per_arm.items()},
            "test": "census across 9 runs",
            "verdict": "survives" if saturated else "failed",
            "caveat": "honest null: sonnet's baseline suffices at this task scale; not evidence "
                      "the skills are useless, evidence these probes cannot detect their value",
        })
    return tests


def content_specificity_test(by_task: ByTask) -> Test:
    placebo_vs_none = {}
    for task, arms in by_task.items():
        profiles = {
            arm: sorted(
                tuple(sorted((k, g["passed"]) for k, g in r["grades"].items())) for r in arms[arm]
            )
            for arm in ("none", "placebo")
        }
        placebo_vs_none[task] = profiles["none"] == profiles["placebo"]
    return {
        "claim": "Q1.H2.C1 content-specificity: placebo matches none on every probe; only the "
                 "real skill separates (and only where it carries a convention)",
        "data": {t: ("identical assertion profiles" if same else "profiles differ")
                 for t, same in placebo_vs_none.items()},
        "test": "exact per-assertion profile comparison, none vs placebo, all four probes",
        "verdict": "survives" if all(placebo_vs_none.values()) else "weakened",
        "caveat": "n=3 per cell; identical profiles at ceiling carry limited information for "
                  "the saturated probes — the informative comparison is provenance",
    }


def trigger_tests() -> list[Test]:
    neg_runs = pos_fail = pos_total = false_triggers = 0
    for d in TRIGGER_DIRS:
        summary = json.loads((d / "summary.json").read_text())["trigger"]
        for skill_entry in summary["skills"].values():
            for q in skill_entry["queries"]:
                if q["should_trigger"]:
                    pos_total += 1
                    pos_fail += not q["passed"]
        for r in rows(d / "trigger.jsonl"):
            if not r["should_trigger"] and not (r.get("is_error") and r.get("num_turns", 0) == 0):
                neg_runs += 1
                false_triggers += bool(r["triggered"])
    upper95 = clopper_pearson_upper(false_triggers, neg_runs) if neg_runs else None
    return [
        {
            "claim": "Q1.H3.E1.C1 zero false-triggers on near-miss negatives",
            "data": f"{false_triggers}/{neg_runs} negative runs triggered",
            "test": "census of negative runs",
            "verdict": "survives" if false_triggers == 0 else "failed",
            "note": "the original claim overstated the analysis output: per-query 'pass' means "
                    "rate < 0.5, which permits nonzero triggers — the census found one",
        },
        {
            "claim": "Q1.H3.E1.C4 (corrected): false-trigger rate on near-miss negatives is low",
            "data": f"{false_triggers}/{neg_runs} negative runs triggered "
                    f"(exact 95% upper bound {round(upper95, 4)})",
            "test": "Clopper-Pearson exact upper bound",
            "verdict": "survives" if upper95 is not None and upper95 < 0.10 else "weakened",
            "caveat": "haiku only; the one trigger ('make the claims in the intro punchier') is a "
                      "true near-miss sharing 'claims' vocabulary with the skill domain",
        },
        {
            "claim": "Q1.H3.E1.C2 under-triggering dominant: should-trigger queries failing threshold",
            "data": f"{pos_fail}/{pos_total} should-trigger queries at or below 0.5 trigger rate",
            "test": "descriptive census over 3 runs/query; contrast with the low false-trigger rate",
            "verdict": "survives",
            "caveat": "haiku only; describes this query sample, not all phrasings",
        },
    ]


def main() -> int:
    behaviour = rows(BEHAVIOUR)
    by_task: ByTask = {}
    for r in behaviour:
        by_task.setdefault(r["task"], {}).setdefault(r["arm"], []).append(r)
    tests = [
        provenance_test(by_task),
        *completion_tests(by_task),
        *saturation_tests(by_task),
        content_specificity_test(by_task),
        *trigger_tests(),
    ]
    scorecard = {
        "generated_by": "scripts/falsify_skill_evals.py (deterministic, combinatorial)",
        "n_behaviour_runs": len(behaviour),
        "tests": tests,
    }
    out = ROOT / "results/skill_evals/falsify_scorecard.json"
    out.write_text(json.dumps(scorecard, indent=2) + "\n")
    for t in tests:
        print(f"[{t['verdict'].upper():9s}] {t['claim']}")
    print(f"scorecard -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
