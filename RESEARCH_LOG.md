# Research harness — self-evaluation log

## Project summary

The harness's own research record: evals of whether its skills causally change
agent research-integrity behaviour (trigger evals + three-arm behaviour probes
with planted ground truth), and what the process itself revealed (workspace
containment, error-classification, usage-limit silent failures). Day one
answered Q1's core: skills change behaviour where they transmit a convention
(provenance markers, placebo-controlled p=0.012), not where they exhort
diligence; triggering under-fires but almost never over-fires; one skill's
staged workflow breaks headless completion. Research done WITH the harness
lives in each consuming project's own tree and log — this file is only about
the harness itself.

---

# Log

Newest entry first. Every entry answers the same four questions.

### 2026-07-20

* What I did: Audited all nine skills against the agentskills.io specification (three fixes). Built and ran the skill evals: trigger family (20 labelled queries × 3 runs × 4 skills, haiku, fenced workspaces) and behaviour family (4 probes × 3 arms × 3 runs, sonnet) with a length-matched placebo installed under the real skill's name so content is separated from priming. Ran ten deterministic falsification tests (scripts/falsify_skill_evals.py) and graduated every claim through the gate. Handled three validity incidents en route: the containment incident (eval agents escaped workspaces nested inside the host project and fabricated research state there — caught by the host's validate_research.py with 7 violations; workspaces now live in OS temp with git-init fencing), the error-classification bug (max-turn-capped runs were dropped as errors although they trigger MORE often, biasing rates down), and the usage-limit silent failure (the CLI reports a subscription limit kill as an ordinary success message; 44 such runs were recorded as data before transcripts exposed them — runner now aborts on usage_limit). Also: falsify made model-invocable (the workflow told agents to run a gate they could not invoke), transcripts persisted per run, and two headless-operation rules added to derive-from-sources.
* What I expected vs what happened: Expected clean sweeps in ~15 minutes per skill and grading to be the hard part. Instead, infrastructure failures repeatedly masqueraded as behavioural results, and the falsify gate caught my own overclaim — "zero false-triggers" was wrong (1 of 120 negative runs triggered; per-query "pass" only bounds the rate at 0.5), recorded as C1 [failed] and superseded by the corrected C4. Grading itself was indeed mostly mechanical because the fixtures plant ground truth.
* What this changes about my thinking: Skills earn their tokens where they carry information the model lacks (the claim-marker convention: 3/3 skill runs anchored vs 0/6 none+placebo), not where they exhort virtues the model already practices (null-honesty and observability saturated in every arm — honest nulls about the probes' headroom, not the skills' value). Conversational-era skills can actively harm autonomous use (7/7 headless stalls at derive-from-sources' notes-to-draft boundary, robust to two text fixes — needs workflow restructuring, not wording). Workspace isolation and error classification are validity requirements, not hygiene. Longer horizons are where the saturated probes should regain headroom (filed as issue #1 with the prediction registered).
* What I will do next: Long-horizon probe variants (issue #1), a controlled nested-vs-fenced experiment to close H5, description optimisation for the 16 under-triggering queries, and a workflow-level fix for the headless stall — then re-run the affected sweeps.
