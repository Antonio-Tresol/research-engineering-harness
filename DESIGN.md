# Design rationale

Why the harness enforces what it enforces. Every claim here cites either a
source in `references/` — with per-source notes, read-depth tags, and verbatim
quotes under `research/` — or the harness's own measured record in the private
companion repo [research-harness-meta][meta] (tree nodes named inline).

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

### Shared artefacts are written for readers without the writer's context

Behaviour probes on the harness's own files found that legibility drift is
mimicry: the same model that wrote plain entries on a clean project — even
from a telegraph-heavy user message — reproduced seeded dialect in 3/3 runs on
a dialect-seeded one, extending it into its own new writing. The files, not
the agent's disposition, carry the style forward. Norms alone cleaned
inherited dialect unreliably (the tree in 3/3 runs, the log history in 1/3),
while the validator tripwire cleaned both in 6/6 — and agents ran the
validator in 24/24 runs, so what it catches, not whether it runs, was the
binding constraint ([meta Q2.H1][meta]). Hence the plain-language contract is
stated as a norm, enforced as a tripwire, and backed by a PostToolUse hook as
insurance for sessions that skip the ritual. Clean-up carries an explicit
relocation rule because, before it existed, agents deleted a seeded
operational warning in 8 of 9 clean-up runs instead of moving it. Two
robustness reads later strengthened the stack: with prompts that never
mention the skill, it auto-loaded from its description in 18/18 headless
runs and no telegraph leaked; with a smaller subject model the gate held
(12/12 green) but a previously registered control was silently dropped from
the record in 2 of 6 restructuring runs — length is checked mechanically,
completeness still rides on the docs and the model ([meta Q2.H1][meta]).

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

### A node is a headline

The artefact histories of two real consuming projects (103 artefact commits,
every one agent-co-authored) showed the dominant legibility failure is
accretion, not shorthand: registration protocols and dated amendments
appended into single tree nodes until one reached 12,051 characters, its
codename legend buried inside the same unreadable line. A deliberate hand
clean-up in the second project — every claim restructured to one falsifiable
sentence with labelled support and falsification clauses — landed at median
node text near 600 characters, which calibrates the validator's
1,200-character limit. In an A/B differing only in the altitude rules, agents
without them appended (nodes grew to 1,902–2,822 characters across n=6);
with them they restructured in 6/6 runs into linked `notes/` registration
documents with every seeded protocol detail preserved. Across five chained
sessions on one workspace the gate flattened the real growth curve — max
node text stayed at or under 1,200 in 15/15 sessions against unbounded
growth without it — and in a brownfield migration of a real 94KB, 68-
violation tree, every one of 19 tracked facts (numbers, a teammate
attribution, a citation) survived in all runs, with a fresh cheap reader
recovering detail answers from the relocation documents at 40% of the
original tree's reading cost ([meta Q2.H2–H3][meta]).

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
[meta]: https://github.com/Antonio-Tresol/research-harness-meta
