"""Seed content and task definitions for the plain-language behaviour eval.

Split from run_plain_language_eval.py so the runner stays under the size
gate, mirroring plain_language_graders.py. Everything here is what a
workspace STARTS with (project fixtures, tree and log seeds) plus the task
prompts; the runner assembles workspaces from it and the graders never read
it, so seed and instrument cannot contaminate each other.
"""

from __future__ import annotations

import json
from typing import Any, Final

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

# No-force-load variants: identical seeds, but the prompt never points at the
# skill file. The forced tasks measure compliance given the conventions are in
# context; these measure trigger times compliance — the realistic product,
# where nothing guarantees the conventions are read at all.
TASKS["dictation_nf"] = {
    **TASKS["dictation"],
    "prompt": (
        "quick update b4 i sign off — reran the sweep w/ the v2 cfg (coef 8.0 "
        "instead of 4.0), refusal went 0.62 → 0.71 on the 200 heldout, file's at "
        "results/steering_v2.json. v1 run (coef 4.0) was flat btw, 0.62 vs 0.62, "
        "that one's results/steering_v1.json. pls update TREE.md + RESEARCH_LOG.md: "
        "E1 done w/ evidence, add the claim (keep it unvalidated, no falsify pass "
        "yet), + today's log entry."
    ),
}
TASKS["accretion_nf"] = {
    **TASKS["accretion"],
    "prompt": (
        "The first tranche of the dose-response protocol scored; results are in "
        "results/tranche1.json — the gate read passes its registered bar, "
        "saturation is undecided, fluency is intact, which the registered ladder "
        "calls tier T2. Also record the design amendment we agreed: a "
        "paraphrased-prompt control arm is added (same prompts, "
        "meaning-preserving paraphrases), and any dose-response statistic must "
        "also survive it. Please do the session-end update of TREE.md and "
        "RESEARCH_LOG.md."
    ),
}
