# Research tree

State of the project: questions → hypotheses → experiments → claims.
Grammar and status vocabulary: see `.claude/skills/research-log/SKILL.md`.
Validate with `python scripts/validate_research.py`. Never delete nodes — mark
them `abandoned` and point at the log entry explaining why.

- Q1: Do the harness skills causally change agent research-integrity behaviour (fabrication from priors, dressing up nulls, unanchored statistics, unobservable experiment code), beyond generic instruction priming? [open] | log: 2026-07-20
  - Q1.H1: With the relevant skill loaded, agents exhibit the target integrity behaviour more often than with no skill [open]
    - Q1.H1.E1: Canary-source fabrication probe — summarise two local "papers" seeded with counter-prior canary facts; grade canary presence in the artefact (derive-from-sources vs placebo vs none) [planned]
    - Q1.H1.E2: Null-dataset honesty probe — analyse a seeded pure-noise dataset framed as a promising effect; grade whether the report claims an effect and whether tree claims graduate without a scorecard (falsify + research-log vs placebo vs none) [planned]
    - Q1.H1.E3: Observability probe — write a batch pipeline over a flaky mock API; grade recorded seed, incremental JSONL, per-item error rows, and idempotent re-run (experiment-engineering vs placebo vs none) [planned]
    - Q1.H1.E4: Provenance probe — write a report from a results file; grade whether statistics carry claim markers that resolve against the data (validate-claims vs placebo vs none) [planned]
  - Q1.H2: The effect is content-specific — the real skill outperforms a length-matched placebo skill of generic research-virtue prose on the same probes [abandoned] | log: 2026-07-20
  - Q1.H3: Skills trigger when they should — trigger rate above 0.5 on should-trigger queries and below 0.5 on near-miss negatives [refuted] | log: 2026-07-20
    - Q1.H3.E1: Trigger evals — 20 labelled queries × 3 runs each for derive-from-sources, experiment-engineering, research-log, validate-claims [done] | evidence: results/skill_evals/trigger_results_2026-07-20.json | log: 2026-07-20
      - Q1.H3.E1.C1: Trigger rates > 0.5 on should-trigger queries [failed] | log: 2026-07-20
      - Q1.H3.E1.C2: Trigger rates < 0.5 on near-miss negatives [failed] | log: 2026-07-20
  - Q1.H4: Skill effectiveness is robust to paraphrase variations — agents maintain target integrity behaviour when the same query is reworded without semantic change [open]
    - Q1.H4.E1: Paraphrase robustness probe — take 5 queries from Q1.H3.E1 trigger evals, generate 3 semantic-preserving paraphrases each; run full trigger eval on paraphrases; grade mean trigger rate stability and per-query variance (queries triggering on original should trigger ≥70% on paraphrases) [planned] | log: 2026-07-21
