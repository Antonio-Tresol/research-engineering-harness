# research-harness

A portable harness for AI-assisted technical research, aimed at AI safety work in
particular, with the discipline needed to keep both the human and the AI agents
honest. It holds the skills, templates, mechanical checks, and the evidence base
behind their design. Install it into each new research project and maintain it
here.

Licensed MIT.

## Design principles

1. **Norms remove the reasons to deceive; mechanisms catch the ways you can be
   wrong anyway.** Completion pressure is a documented driver of fabrication in
   research agents: removing it cut undisclosed fabrication from roughly 21% to
   3% in SciIntegrity-Bench (see `references/harness.bib`). So the harness says
   everywhere that nulls, refutations, and "infeasible" are first-class outcomes,
   and separately enforces, mechanically, that claims trace to evidence files
   that exist.
2. **Log versus view.** History (the research log) is append-only and never lies
   about what was believed when. State (the research tree) says what is believed
   now and on what evidence. A script validates both, so the guarantee does not
   rest on vigilance.
3. **Claims graduate through gates.** A claim starts `unvalidated` and can only
   become `survived`, `weakened`, or `failed` through a falsification or
   validation protocol whose scorecard is linked as evidence.
4. **Speed is a first-class constraint.** Exploratory code is exempt from polish
   and linting by design. Quality gates apply at promotion, when code starts
   producing evidence a claim rests on.
5. **Generic and machine-free.** Nothing here references a specific machine,
   timebox, or person. Per-machine pointers live in each user's gitignored
   `CLAUDE.local.md`, and every source cited is public, identified by arXiv ID,
   DOI, or URL.

## Contents

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
2. Extend the generated `CLAUDE.local.md` with your machine-local pointers.
3. Check the requirements: `arxiv-mcp-server` and `uv` on PATH, and Python 3.10
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
on it. Adopt it when a project writes substantial analysis code, because the
failure it catches (long, high-complexity functions producing plausible but wrong
numbers) is a documented AI-scientist failure mode rather than a style
preference. Skip it for a project that is mostly prose and notebooks.

## Maintaining the harness

Improvements discovered inside a project, whether a new gap, a better rule, or a
pitfall from new literature, come back here as commits, with sources added to the
relevant `.bib` and, when a survey was involved, notes under `research/`. The same
evidence discipline applies to the harness itself: a design rule without a
traceable source is a preference, not a finding.
