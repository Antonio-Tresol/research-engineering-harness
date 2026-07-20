# research-engineering-harness

Doing good, honest, trustworthy science takes the right mindset and practices.
An AI-assisted project has to hold both itself and its agents to them.

The aim is research that stays auditable, reproducible, open, and grounded in the
literature, where mistakes are easy to catch and easy to resume from. Underneath
that sits falsification: science is not the business of proving a hypothesis, it
is the sustained effort to break your hypotheses until the ones left standing are
worth believing. Working that way makes two artefacts central. A **tree** records
what you have explored and what you currently believe. A **log** records how you
got there, so the state of the project has a history and not just a snapshot.
Around both sits ordinary good engineering, because an experiment you cannot
rerun is not evidence.

Every principle here is enforced mechanically where that is possible. What a
script cannot check is written where an agent will actually pick it up: the
skills, the MCP config, and `AGENTS.md`.

In practice you get nine agent skills, two structured project files, and a set of
checks that fail your build when the audit trail breaks: when a claim cites
evidence that does not exist, when a number in a write-up disagrees with the
results file it came from, or when a claim is marked "survived" without a
falsification scorecard behind it.

Built for AI safety research, useful for any empirical work where an agent is
writing the code and the write-up. Works with Codex, Claude Code, and anything
else reading [`AGENTS.md`](https://agents.md/).

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

**Skills** are `SKILL.md` files carrying the method: how to run a literature
search, how to design an eval, how to attack a claim. The agent follows a
documented procedure instead of improvising one per session. Claude Code and
Codex both load them automatically based on the `description` field, and
`AGENTS.md` lists which one applies to which situation for agents that do not.

**Two modes for code.** Exploratory work in notebooks and scratch scripts is
exempt from linting on purpose; most research is de-risking and gating it just
slows you down. The checks apply to *promoted* code, meaning anything a claim
now rests on.

## Agent compatibility

Instructions live in `AGENTS.md`, the cross-tool standard; `CLAUDE.md` imports it
in one line so the two cannot drift. Skills use the shared `SKILL.md` format and
live in `.claude/skills/`, with `.agents/skills` symlinked to the same directory,
so Claude Code and Codex both load them automatically and neither sees a stale
copy. The checks are plain scripts and care about none of this.

On Windows, git needs `core.symlinks=true` and Developer Mode. Without them it
checks the symlink out as a text file and Codex silently finds no skills.
`HSKILL-004` catches exactly that, and the installer falls back to copying where
symlinks are unavailable.

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

`./check.sh` also runs the checks' own test suite. Roughly half of those tests
assert that a rule stays **quiet**: on rounded values, on documentation examples
inside code fences, on ordinary Python with no tensors, on folded YAML. Each one
encodes a false positive that was genuinely shipped at some point. A checker that
cries wolf gets bypassed, and then its true positives go unread too.

The rules are also measured against real repositories rather than only against
fixtures. One rule was deleted on that evidence: it produced 43 findings across
four existing skill collections and not one of them was a real problem.

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
