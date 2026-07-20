# Design rationale

Why the harness enforces what it enforces. Every claim here cites a source in
`references/`; the per-source notes, with read-depth tags and verbatim quotes,
are under `research/`.

The organising idea: **norms remove the reasons to fabricate, and mechanisms
catch the mistakes that honesty does not prevent.** Neither substitutes for the
other. A validator alone teaches a pressured agent to produce things that pass
the validator; norms alone do nothing about an honest bug.

## Norms

### Nulls and refutations are first-class outcomes

SciIntegrity-Bench put seven frontier models in situations where the honest
answer was "this cannot be done" ([arXiv:2605.10246][sci]). All seven generated
synthetic data instead. The interesting part is the intervention: removing
explicit completion pressure from the prompt cut *undisclosed* fabrication from
20.6% to 3.2%, while the rate at which models synthesised data was unchanged.
The pressure did not change what they did; it changed whether they admitted it.

So the harness says everywhere that a null or infeasible result recorded with
evidence is a completed experiment. This is not encouragement, it is the removal
of an incentive.

### A failed claim means the protocol worked

`falsify` grades each claim Survives, Weakened, or Failed. A scorecard where
everything survives suggests the tests were not adversarial, not that the
research was strong.

### Pivots are recorded, not erased

Nodes become `abandoned` with a log entry, never deleted. The tree's value is
that it does not lie about what was tried.

### Humans set direction

When 43 experts actually executed research ideas that had been rated at the
proposal stage, LLM-generated ideas fell further on every metric than
human-generated ones, reversing the ranking that ideation-stage review had
produced ([arXiv:2506.20803][gap], following [arXiv:2409.04109][ideas]).
Pre-execution novelty is not a proxy for research value, so the harness
structures the choice of what to run and leaves the direction to a person.

## Mechanisms

### Evidence must exist on disk

Hallucinated numbers are plausible by construction, so plausibility is not a
test. Independent evaluation of The AI Scientist found papers containing
"hallucinated numerical results" and placeholder text alongside real output
([arXiv:2502.14297][beel]). `validate_research.py` therefore checks that every
evidence path resolves to a file, and refuses to take the claim's word for it.

### Claims cannot graduate without a scorecard

An audit of the KOSMOS autonomous scientist tested three of its hypotheses
against null models: one was well supported, one uncertain, and one was
statistically indistinguishable from random five-gene sets (Spearman ρ = −0.40,
p = 0.76). The genuine finding survived a permutation test at empirical
p = 0.0039 ([arXiv:2511.13825][kosmos]). Only the null model separated them.

So a claim reaching `survived` must link a file whose name marks it as a
falsification or validation artefact. Otherwise the gate is honour-system, and
honour-system gates are skipped exactly when time is short.

### Numbers in documents must resolve

Jr. AI Scientist documented false performance gains produced by incorrect
batch-level normalisation: invalid code that looked like an improvement. The
same report notes that current AI reviewers "primarily evaluate text and cannot
detect discrepancies between reported results and actual experimental data or
code" ([arXiv:2511.04583][jr]).

`PROV-001/002` cannot catch the bug itself, since the number is genuinely what
the code produced. It catches the other half: prose drifting from correct data
after a re-run, which no amount of careful reading reliably notices.

### Graders are pinned

Agentic benchmarks have been compromised by giving agents write access to the
files that score them; a trivial agent that replaced assertions scored highly on
a task it never performed (reported in the agentic-benchmark critique surveyed in
`research/research-agents/`, which draws the figures from an AI-generated
overview rather than the paper body — treat the exact numbers as indicative).
The structural point holds regardless: in this harness one agent writes the
experiment and could edit the validator certifying it, so graders are pinned and
never changed in the same commit as what they grade.

### Qualitative labels need discrimination tests

Detection-style scoring of interpretability labels is invariant to descriptive
collision: a label that also fits an unrelated feature scores well. In one
analysis, 82.1% of 722 human-annotated SAE features shared a label with another
feature ([arXiv:2605.12874][labels]). For interpretability work the label *is*
the result, so `falsify` requires scoring against a matched distractor and
reporting selectivity, not recall alone.

### Distributions, not anecdotes

Agent benchmark conclusions reverse depending on time budget and aggregation
rule, and a single run of an investigation is close to uninformative. Claims
therefore state `n` and the aggregation rule. See `research/research-agents/`
for the specific reversals.

### Code quality applies to promoted code only

42% of The AI Scientist's experiments failed on coding errors
([arXiv:2502.14297][beel]). Long, high-complexity analysis functions are where
plausible-but-wrong numbers hide. But most research work is exploratory
de-risking, and linting that phase taxes the part that should be cheapest, so
gates apply at promotion.

## What the harness deliberately does not do

Sandboxing and self-modification guards, multi-agent debate, tournament review,
and publication-bias governance all appear in the literature as mitigations. The
AI Scientist edited its own launch script to extend its timeout
([arXiv:2408.06292][aisci]), which is a real risk when an agent runs unattended
for hours. This harness assumes a human in the loop and a reviewer who is that
same human, so those remedies would be machinery without a corresponding threat.
The gap analyses in `research/` record the reasoning for each.

[sci]: https://arxiv.org/abs/2605.10246
[gap]: https://arxiv.org/abs/2506.20803
[ideas]: https://arxiv.org/abs/2409.04109
[beel]: https://arxiv.org/abs/2502.14297
[kosmos]: https://arxiv.org/abs/2511.13825
[jr]: https://arxiv.org/abs/2511.04583
[labels]: https://arxiv.org/abs/2605.12874
[aisci]: https://arxiv.org/abs/2408.06292
