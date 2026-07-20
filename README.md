# research-engineering-harness

Eliciting good research work from agents takes deliberate work, and doing good
science takes the right mindset and practices. Neither comes free from a capable
model. This repository is what those practices look like once they are written
down, made portable, and enforced mechanically wherever enforcement is possible.

Every rule here exists because something specific goes wrong without it. The
parentheticals throughout say what.

Licensed MIT.

## The problem

Agents doing research fail in characteristic, documented ways. They fabricate
rather than admit a task is infeasible. They produce plausible numbers from buggy
code. They judge their own output optimistically. They present a single run as a
finding, and they cite work that does not exist.

None of this is hypothetical, and none of it is fixed by a better model alone.
The surveys under `research/` collect the incidents with per-source notes and
read-depth tags; `references/` holds the citations, each identified by arXiv ID,
DOI, or URL. Every claim below is checkable against them.

## Mindset

Norms remove the *reasons* to deceive. Nothing here is machine-enforceable, which
makes it the part that matters most.

- **Nulls, refutations, and "infeasible" are first-class successes.** There is no
  pressure to produce a positive result, only to record what is true.
  *(In SciIntegrity-Bench, all seven tested models generated synthetic data
  rather than acknowledge an impossible task. Removing explicit completion
  pressure cut undisclosed fabrication from roughly 21% to 3%, while the
  underlying synthesis rate stayed the same: what the pressure changed was
  whether the model owned up to it.)*
- **A failed claim means the protocol worked.** Retracting something before it
  ships is the entire point. *(A falsification scorecard where everything
  survives is evidence that nothing was genuinely tested.)*
- **Pivots are recorded, never erased.** Nodes become `abandoned`, with a log
  entry saying why. *(An abandoned branch with a reason tells the next person, or
  the next you, what not to retry.)*
- **Humans set the direction; the harness structures the choice.** *(Ideas that
  look novel before execution often do not survive it: when experts actually ran
  a set of LLM-generated and human-generated research ideas, the LLM ideas fell
  significantly further on every metric, reversing the ranking seen at the
  ideation stage.)*

## Practices

How the work gets done, one skill per practice.

- **Sequence by information gained per hour, and de-risk before executing**
  (`research-ideation`). *(The expensive failure is finishing the easy components
  of a project whose hard component was never going to work.)*
- **Read every source before writing a word from it** (`derive-from-sources`).
  *(Research agents cite irrelevant work and occasionally fabricate BibTeX
  entries outright. The notes file, written first and quoting verbatim, is what
  proves the reading actually happened.)*
- **Threat model before metric, and name the confound** (`eval-design`).
  *(Otherwise you can build a perfectly valid measurement of a property that no
  longer connects to the harm you cared about.)*
- **Explore fast, promote deliberately** (`experiment-engineering`). Exploratory
  code is exempt from polish and linting by design. *(Most research work is
  de-risking in notebooks, and gating that phase taxes exactly the part that
  should be cheapest. Gates belong at promotion, when a claim starts resting on
  the code.)*
- **Observability is never deferred, even in explore mode.** Structured
  incremental logs, resumable checkpoints, fail-fast ordering, fixed seeds.
  *(Unlogged fast work has to be re-run, and re-running is slower than logging
  was. The fastest iteration loop is the one you can kill and resume.)*
- **Try to destroy every claim before believing it** (`falsify`). *(An
  independent audit of an autonomous scientist found one headline hypothesis
  statistically indistinguishable from random gene sets, p = 0.76. A permutation
  null was the only thing that separated it from the finding that was real.)*
- **Trace every number back to a file before it ships** (`validate-claims`).
  *(One system's apparent improvement came from incorrect batch-level
  normalisation. It looked exactly like a real gain, and a text-only reviewer
  cannot tell the difference between reported results and what the code
  actually did.)*
- **Report the distribution, not the anecdote** (`communicate-results`). State
  *n* and the aggregation rule. *(Agent benchmark results reverse depending on
  time budget and on whether you report best-of-k, a mean over seeds, or a union
  over variants. A bare number without its *n* is an anecdote.)*

## Mechanisms

Norms remove the reasons to deceive; mechanisms catch the ways you can be wrong
anyway. All of it runs from one command, `./check.sh`.

- **Evidence must exist on disk before a claim graduates.** *(Hallucinated
  numbers are plausible by construction, so the check has to be existence rather
  than plausibility.)*
- **Numbers in documents resolve against the results files they came from.**
  A claim marker names the value and its source, and the check re-resolves it on
  every run. *(False gains from a batch-normalisation bug looked exactly like a
  real improvement, and a text-only reviewer cannot tell the difference. Prose
  also drifts quietly from correct data after a re-run, which no amount of
  careful reading reliably catches.)*
- **Commits remind you what the change implies.** The pre-commit hook blocks on
  failing checks and reminds when experiment code moved but the tree did not.
  *(Bookkeeping is what slips under time pressure, which is exactly when the
  audit trail matters most.)*
- **Claims cannot leave `unvalidated` without a linked scorecard.** *(Otherwise
  the falsification gate is honour-system, and honour-system gates are the ones
  skipped under time pressure.)*
- **Graders are pinned, and never edited in the same commit as what they grade.**
  *(At least one agent benchmark was compromised because agents could write to
  the test files that scored them.)*
- **Tensors carry their shapes, and einops replaces raw reshaping.** *(A shape
  bug usually does not raise. It broadcasts silently and computes a wrong number,
  which you then debug for an afternoon.)*
- **Skills stay portable and correctly triggered.** *(A machine-specific path
  breaks the moment a teammate clones the repository, and malformed frontmatter
  fails silently rather than loudly.)*
- **Code quality applies to promoted code only.** *(Long, high-complexity
  analysis functions are where plausible-but-wrong numbers hide. One independent
  evaluation found 42% of an agent's experiments failed on coding errors alone.)*

## What is in the box

### Skills (`.claude/skills/`)

| Skill | What it covers |
|---|---|
| `research-ideation` | Choosing and sequencing work: de-risk load-bearing components first, order by information gained per hour |
| `research` | Literature search and retrieval across the paper MCPs, with no-MCP fallbacks |
| `derive-from-sources` | Grounded synthesis: read every source, take verbatim-quote notes, draft only from the notes |
| `eval-design` | Building LLM evals: threat model, specification, question design, QC, with a construct-validity checklist and an LLM-judge audit rule |
| `experiment-engineering` | The engineering contract: two modes, the observability contract, API concurrency, GPU batching, tensor discipline. Bundles runnable reference code |
| `falsify` | Claim destruction: permutation nulls, bootstrap CIs, base-rate checks, discrimination tests for qualitative labels |
| `validate-claims` | Traceability: every number to a data file, every method sentence to code, every citation to a real paper |
| `research-log` | Tree and log conventions, plus the session ritual |
| `communicate-results` | Presenting results honestly: strongest message first, error bars, real outputs shown |

### Checks and tooling

| Path | What it is |
|---|---|
| `check.sh` | Runs every mechanical check in one command |
| `scripts/validate_research.py` | The research-integrity gate: tree and log structure, evidence existence, scorecard-gated claim graduation, tree-to-log cross-references |
| `lanorme_plugins/tensors.py` | `TENSOR-001/002`: jaxtyping annotations on every tensor, vectors included, and einops instead of raw reshaping |
| `lanorme_plugins/provenance.py` | `PROV-001/002/003`: numbers in documents resolve against the results files they cite |
| `hooks/pre-commit` | Blocks on failing checks; reminds about tree, log, and docs updates. Install with `hooks/install.sh` |
| `lanorme_plugins/skill_portability.py` | `HSKILL-001/002/003`: no machine-specific paths in skills, trigger phrasing, frontmatter typos |
| `lanorme.toml` | Config for [lanorme](https://github.com/lanorme/lanorme), which owns Python quality and Agent Skills spec compliance |
| `install.py` | Installs the harness into a project and fills in the template placeholders |
| `templates/` | Seed files: `CLAUDE.md`, `TREE.md`, `RESEARCH_LOG.md`, `mcp.json`, `lanorme.toml` |

### Evidence base

| Path | What it is |
|---|---|
| `references/harness.bib` | Sources behind the harness design, mostly the AI-scientist pitfalls literature |
| `references/agents.bib` | Sources on AI R&D, interpretability, red-teaming, and evals agents |
| `references/practice.bib` | Sources on fast empirical research practice |
| `research/ai-scientist-pitfalls/` | Pitfall taxonomy, per-source notes with read-depth tags, and a gap analysis against this harness |
| `research/research-agents/` | The same treatment for domain-specific research agents |
| `research/fast-research-practice/` | Notes behind the speed, ideation, and communication guidance |

## Two documents, and why they are separate

`TREE.md` is the **state**: questions, hypotheses, experiments, and claims, each
with a status and links to the evidence. `RESEARCH_LOG.md` is the **history**: an
append-only daily log answering the same four questions each time. The tree says
what is believed now; the log never lies about what was believed when. Neither
state nor history should live only in the other, and a script validates both.

## Installing into a new project

`install.py` copies the portable parts, renders the template placeholders, seeds
the project layout, and writes a starter gitignored `CLAUDE.local.md`.

```bash
# Interactive, prompting for anything not passed
uv run install.py ~/path/to/new-project

# Fully specified
uv run install.py ~/path/to/new-project \
    --name "Refusal Probe Transfer" \
    --description "do refusal directions transfer across model families" \
    --question "Does the Gemma refusal direction steer Llama refusals?" \
    --timebox "one week, solo" \
    --no-input
```

Other options: `--context` (explicit project context, overriding `--timebox`),
`--no-reference` (skip copying `references/` and `research/`), `--force`
(overwrite existing files; without it they are reported as SKIP and left alone),
and `--today` (the date for the seed log entry).

A fresh install passes `./check.sh` immediately. The research log arrives seeded
with a complete scaffolding entry and `TREE.md` with your `Q1`. Anything you did
not supply stays visible as a `<PLACEHOLDER>` and is listed in the installer's
output rather than silently blanked.

Afterwards:

1. `git init && git add -A && git commit -m 'Scaffold from research-harness'`
2. `./hooks/install.sh` to enable the pre-commit hook.
3. Extend the generated `CLAUDE.local.md` with your machine-local pointers.
4. Check the requirements: `arxiv-mcp-server` and `uv` on PATH, and Python 3.10
   or newer. After your first paper download, confirm papers land in
   `data/papers/`; if they do not, make the storage path in `.mcp.json` absolute.

## Running the checks

Every script is a self-contained [PEP 723](https://peps.python.org/pep-0723/) uv
script, with dependencies declared inline, so there is no environment to create.

```bash
./check.sh
```

That runs two things, and the split is deliberate:

```bash
PYTHONPATH=. uvx lanorme check .        # code quality, skills spec, harness plugins
uv run scripts/validate_research.py     # research-integrity gate
```

The harness's own rules are lanorme **plugins** in `lanorme_plugins/`, registered
through `plugins = [...]` in `lanorme.toml`, so `TENSOR-001/002` and
`HSKILL-001/002/003` report through the same runner, config, and exit code as the
built-in rules. `PYTHONPATH=.` is what lets lanorme import them.

The harness holds AI agents to mechanical checks, so it applies the same standard
to itself: `./check.sh` must pass on this repository.

**Why `validate_research.py` is not a plugin.** It is the research-integrity
gate, covering evidence existence, scorecard-gated claim graduation, and
tree-to-log consistency. Folding it into lanorme would make those guarantees
depend on an optional external tool, so the check that most needs to be
unskippable would become the easiest to skip. It stays a zero-dependency script.

**Is lanorme required downstream?** No. Installed projects get a `lanorme.toml`,
but lanorme is an optional external tool and the integrity gate does not depend
on it. Adopt it when a project writes substantial analysis code. Skip it for a
project that is mostly prose and notebooks.

## Maintaining the harness

Improvements discovered inside a project, whether a new gap, a better rule, or a
pitfall from new literature, come back here as commits, with sources added to the
relevant `.bib` and, when a survey was involved, notes under `research/`. The same
evidence discipline applies to the harness itself: a design rule without a
traceable source is a preference, not a finding.
