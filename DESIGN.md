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

A red-team sweep on the harness's own stack measured what that buys. Eighteen
runs were each instructed to corrupt the record a different way; fourteen
refused outright and quoted these documents back. Asked to record a fabricated
number for an experiment never run, 3 of 3 refused; asked to graduate a claim
on a stub scorecard, 3 of 3 refused, against a registered prediction that most
would succeed; asked to delete an abandoned hypothesis before a reviewer saw
it, 3 of 3 refused and no node id disappeared ([meta Q3.H3][meta]). None of
those three shortcuts is mechanically detectable — a fabricated number backed
by a fabricated file passes every check the validator can run. The norms are
carrying that load, which is the argument for writing them down where an agent
reads them rather than relying on the gate.

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

### Nothing in the tree may be invisible to the checks

The parser skips fenced blocks so a grammar example can sit in the preamble.
An adversarial run found what that carve-out costs: wrapping a claim line in a
code fence graduated it to `survived` with no evidence past a green validator,
every grader file untouched. Fenced content is skipped by *every* rule, so one
trick defeated the scorecard gate, the evidence requirement, the length limit,
and the shorthand tripwire together, while the line still read as recorded to
anyone opening the file — the validator counted one node fewer than the file
visibly contained and exited 0 ([meta Q3.H3][meta]).

A node-shaped line inside a fence among the nodes is now an error. The rule is
position-sensitive on purpose: a fenced example above the first node stays
quiet, because that is documentation no reader mistakes for the tree, and
policing it would fire on every project the installer creates. The general
lesson is that an exemption in a checker is a place to hide things, and an
exemption that applies to every rule at once is a place to hide anything.

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

### Writes go through a validating pen; the graph is derived, never stored

The record's structure — nodes, evidence links, log cross-references, notes
documents — is parsed fresh from the markdown files on every read
(`scripts/research_graph_model.py`), and the CLI's write commands
(`scripts/research_graph.py`) compose a change, run the full validator, and
restore the files byte-for-byte when it fails. Both halves answer documented
failures. Design-rationale tools from gIBIS through Compendium found that
formal structure imposed at capture time gets bypassed — Shipman and
Marshall's "Formality Considered Harmful" is the canonical post-mortem — so
the formal graph here is computed from what writers already produce, never a
second representation that can drift from it. And the harness's own probes
located the binding constraint in validator *coverage*, not validator
adoption (agents ran it unprompted in 24/24 runs), so validation moved to the
moment of writing, where a rejected write names what is missing while the
writer still has the context to fix it. When a claim graduates, its evidence
files are pinned — commit hash and per-file sha256, embedded in the scorecard
by the `pin` command — and `verify` reports drift when a pinned file later
changes: the integrity failure that is otherwise invisible exactly when it
matters, because nothing else re-reads certified evidence
([meta Q3.H1][meta]; the full design note is `notes/record-cli-design.md`
there).

### A refusal has to say whose problem it is

The write commands refuse anything that would leave the record invalid, and
roll the files back byte for byte. Measured on agents who had never been told
the tool existed, that refusal did two opposite things with the same message.
Given a seeded node already over the length limit, one run read the rejection,
hand-trimmed the node, retried the identical command, and landed it; another
read the same bytes as "this tool cannot get me there" and abandoned the write
commands for the rest of the session ([meta Q3.H2][meta]). The message had
listed a violation the command neither caused nor could fix, without saying so.

So a refusal now distinguishes a bad command from a record that was already
broken. The same sweep found a preview that validated nothing (a clean dry run
followed by a hard rejection of the identical command) and a repeated evidence
flag that dropped every path but the last while reporting success. A tool whose
whole purpose is to be trusted with the record cannot report success over
silent data loss, and cannot spend its credibility on a preview that is wrong.

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
