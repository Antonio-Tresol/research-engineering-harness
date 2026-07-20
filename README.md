# research-engineering-harness

Scaffolding that keeps an AI-assisted research project honest. You get nine
agent skills, two structured project files, and a set of checks that fail your
build when the audit trail breaks: when a claim cites evidence that does not
exist, when a number in a write-up disagrees with the results file it came from,
or when a claim is marked "survived" without a falsification scorecard behind
it.

Built for AI safety research, useful for any empirical work where an agent is
writing the code and the write-up.

Works with any agent that reads [`AGENTS.md`](https://agents.md/) — Codex,
Cursor, Aider, and others — and with Claude Code, where `CLAUDE.md` is a
one-line import of the same file. Claude Code loads the skills automatically;
other agents are told in `AGENTS.md` which skill file to read for which task.
The checks are plain scripts and care about none of this.

**Requires** [`uv`](https://docs.astral.sh/uv/) and Python 3.10+. MIT licensed.

## Quick start

```bash
git clone https://github.com/Antonio-Tresol/research-engineering-harness
cd research-engineering-harness

uv run install.py ~/my-project \
    --name "Refusal Probe Transfer" \
    --question "Does the Gemma refusal direction steer Llama refusals?"

cd ~/my-project
git init && ./hooks/install.sh    # optional: check on every commit
./check.sh
```

The installer copies the skills, seeds `TREE.md` and `RESEARCH_LOG.md`, and
writes the `AGENTS.md` your agent reads at the start of every session. A fresh
project passes `./check.sh` immediately.

## What it looks like in use

Your beliefs live in `TREE.md` as a tree of questions, hypotheses, experiments,
and claims. Each node has a status, and anything you have concluded links to the
file that supports it:

```markdown
- Q1: Does the Gemma refusal direction steer Llama refusals? [open]
  - Q1.H1: The refusal direction transfers across model families [open]
    - Q1.H1.E1: Steer Llama with the Gemma direction, measure refusal rate [done] | evidence: results/steering.json
    - Q1.H1.E1.C1: Steering raises Llama refusal rate above baseline [survived] | evidence: results/steering.json
```

That last line is a lie, and `./check.sh` says so:

```
FAIL — 1 violation(s):
  - TREE.md:11: Q1.H1.E1.C1 [survived] needs a scorecard evidence file
    (name containing 'falsify', 'scorecard', or 'validation')
```

A claim only reaches `survived` after something tried to kill it. Pointing at
the same results file that produced the claim is not evidence that it holds up,
so the check refuses it until a falsification scorecard exists on disk.

The same idea applies to prose. A number in a report carries a marker naming
where it came from, invisible once the Markdown renders:

```markdown
Steering raised the refusal rate to 62%.
<!-- claim: 0.62 from results/steering.json#refusal_rate -->
```

Re-run the experiment, get 0.58, forget to update the sentence, and the next
`./check.sh` fails with the old number and the new one side by side. This is the
failure that careful reading does not catch, because the prose still looks
right.

## Concepts

**The tree and the log.** `TREE.md` is current belief: edit it in place, and a
claim that fails falsification changes status there. `RESEARCH_LOG.md` is
append-only history, one dated entry per session answering the same four
questions, never revised. Keeping both means you can always ask what is believed
now *and* what you believed last Tuesday before the result came in.

**Claim graduation.** Every claim starts `unvalidated`. It can only become
`survived`, `weakened`, or `failed` once a falsification or validation run has
produced a scorecard file, which the checker requires by name. `failed` is a
normal outcome: retracting a claim before it ships is the system working.

**Skills** are Markdown files under `.claude/skills/` carrying the method: how to
run a literature search, how to design an eval, how to attack a claim. The agent
follows a documented procedure instead of improvising one per session. Claude
Code loads them automatically; `AGENTS.md` carries a table telling other agents
which file to read for which situation.

**Two modes for code.** Exploratory work in notebooks and scratch scripts is
exempt from linting on purpose; most research is de-risking and gating it just
slows you down. The checks apply to *promoted* code, meaning anything a claim
now rests on.

## The checks

```bash
./check.sh
```

runs two things:

| | Covers |
|---|---|
| `lanorme` + harness plugins | Python quality, Agent Skills spec, tensor shape discipline (`TENSOR-*`), skill portability (`HSKILL-*`), claim provenance (`PROV-*`) |
| `scripts/validate_research.py` | Tree and log structure, evidence files exist, scorecard-gated graduation, tree-to-log cross-references |

The integrity gate is a zero-dependency script, so a project that never installs
[lanorme](https://github.com/lanorme/lanorme) still gets every guarantee about
evidence and claim graduation.

The optional pre-commit hook (`./hooks/install.sh`) blocks a commit when checks
fail, and reminds you when experiment code changed but the tree did not.

## The skills

| Skill | What it covers |
|---|---|
| `research-ideation` | De-risk load-bearing components first; order work by information gained per hour |
| `research` | Literature search across the paper MCPs, with no-MCP fallbacks |
| `derive-from-sources` | Read every source, take verbatim-quote notes, draft only from the notes |
| `eval-design` | Threat model, specification, question design, QC, construct-validity checklist, LLM-judge audit |
| `experiment-engineering` | Observability contract, API concurrency and backoff, GPU batching, tensor discipline. Includes runnable reference code |
| `falsify` | Permutation nulls, bootstrap CIs, base-rate checks, discrimination tests for qualitative labels |
| `validate-claims` | Trace every number to data, every method sentence to code, every citation to a real paper |
| `research-log` | Tree and log grammar, and the session ritual |
| `communicate-results` | Strongest message first, error bars, real model outputs shown |

## Why these rules

Each rule answers a documented failure mode of research agents, from fabrication
under time pressure to plausible numbers produced by buggy code. The reasoning,
with citations, is in **[DESIGN.md](DESIGN.md)**. The underlying literature
surveys, with per-source notes and read-depth tags, are under `research/`, and
the bibliographies are in `references/`.

## Contributing

Improvements found while using the harness come back here as commits. Add
sources to the relevant `.bib`, and notes under `research/` when a survey was
involved. The same standard applies to the harness itself: a design rule without
a traceable source is a preference rather than a finding.
