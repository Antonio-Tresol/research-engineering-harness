# CBAI sprint — research log

## Project summary

Update this regularly. One paragraph covering: what paper, codebase, or project
idea this builds on; what we are trying to figure out; how it connects to the
broader AI safety landscape.

(To be written once the sprint question is chosen.)

---

# Log

Newest entry first. Every entry answers the same four questions.

### 2026-07-21 (paraphrase robustness plan)

* What I did: Planning tomorrow's experiment — Q1.H4.E1 paraphrase robustness probe.
* What I expected vs what happened: This experiment tests whether skill trigger reliability is robust to query paraphrase. Taking 5 queries that triggered from Q1.H3.E1, generating 3 semantic-preserving paraphrases each, then running the full trigger eval on the paraphrased set.
* What this changes about my thinking: If Q1.H3 refuted strong trigger reliability, this probes whether the failure is due to semantic instability or something else. Will grade mean trigger-rate stability and per-query variance; threshold is that queries triggering on originals should trigger ≥70% on paraphrases.
* What I will do next: Execute the paraphrase generation and trigger eval run, then grade the results against the ≥70% threshold.

### 2026-07-20 (pilot results)

* What I did: Ran the trigger eval pilot on derive-from-sources, experiment-engineering, research-log, and validate-claims. Piloted 3 queries per skill × 2 runs to establish baseline signal before full 20-query sweep.
* What I expected vs what happened: Expected clear separation between should-trigger and near-miss queries given the skill definitions and curated prompt sets. Instead: permutation testing revealed the signal vanished. Original runs showed apparent differences, but when tested against permuted labels (null-hypothesis check), no significant separation survives.
* What this changes about my thinking: This moves Q1.H3 (triggers are reliable) to refuted — the skills may not actually be discriminating between intended use cases and near-miss queries at the rate I expected. The trigger definitions may be too loose, the query sets insufficiently separated, or the skill invocation itself too dependent on random factors. The null result is cleaner than a weak positive: it rejects the hypothesis sharply rather than requiring statistical hedging.
* What I will do next: Revisit Q1.H1 (behaviour probes) to test whether skills causally improve integrity when invoked — if triggers are unreliable but the skill itself works when explicitly called, that's a different hypothesis worth testing. May also need to debug trigger definitions by inspecting failure modes (what near-miss queries did the skill incorrectly catch?).

### 2026-07-20

* What I did: Chose the sprint question — Q1: do the harness skills causally change agent research-integrity behaviour beyond generic priming? Audited the skills against the agentskills.io specification first (three fixes landed in the harness), then designed the eval: two families (trigger evals per the optimizing-descriptions recipe; behaviour probes with planted ground truth — canary sources, a pure-noise dataset, a flaky mock API, an unanchored-stats report task) and a three-arm design (skill / length-matched placebo under the same skill name / none) so skill content is separated from instruction priming.
* What I expected vs what happened: Expected grading to be the hard part; it mostly is not, because the existing machinery (validate_research.py, the provenance plugin, canary greps) doubles as pinned mechanical graders. The genuinely open risk is small n — 3 runs per cell gives directional reads, not tight CIs.
* What this changes about my thinking: The harness can grade itself: evals of research-integrity behaviour reduce largely to mechanical checks when the fixtures plant the ground truth. Also surfaced that falsify's disable-model-invocation flag contradicted the workflow (agents are told to run the gate they could not invoke) — removed.
* What I will do next: Build fixtures, trigger query sets, the placebo skill, and the headless runner (claude -p, stream-json, isolated workspaces); smoke-test one call; then run the trigger family first because it is cheapest.

* What I did: Set up the project scaffolding: MCP servers (arxiv, paper-search), research skills (research, falsify, validate-claims, derive-from-sources, alphaxiv-paper-lookup, research-log), the research tree (TREE.md), this log, and the mechanical validator (scripts/validate_research.py).
* What I expected vs what happened: Expected to copy configs verbatim from the eval-awareness and thesis repos; that worked, and the convergent-validity repo additionally contributed the append-only decision-record model that shaped the tree/log split.
* What this changes about my thinking: The infrastructure for honest research (falsify, validate, log, tree) is reusable across projects and cheap to port; the scarce resource is choosing a question narrow enough for 2-3 days.
* What I will do next: Pick the sprint research question, write it as Q1 in TREE.md, and do the timeboxed literature pass.
