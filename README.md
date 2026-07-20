# research-harness

A portable harness for doing AI-assisted technical research — AI safety research
in particular — with the discipline needed to keep both the human and the AI
agents honest. It is the canonical home of a set of skills, templates, a
mechanical validator, and the evidence base behind their design. Copy it into
each new research project; maintain it here.

## Design principles

1. **Norms remove the reasons to deceive; mechanisms catch the ways you can be
   wrong anyway.** Completion pressure is a documented driver of fabrication in
   research agents (removing it cut undisclosed fabrication from ~21% to ~3% in
   SciIntegrity-Bench — see `references/harness.bib`). So the harness states
   everywhere that nulls, refutations, and "infeasible" are first-class outcomes
   — and separately enforces, mechanically, that claims trace to evidence files
   that exist.
2. **Log vs view.** History (the research log) is append-only and never lies
   about what was believed when; state (the research tree) says what is believed
   now and on what evidence. Both are validated by a script, not by vigilance.
3. **Claims graduate through gates.** A claim starts `unvalidated` and can only
   become `survived`/`weakened`/`failed` via a falsification or validation
   protocol whose scorecard is linked as evidence — enforced by the validator.
4. **Generic and machine-free.** Nothing in the harness references a specific
   machine, timebox, or person. Per-machine pointers live in each user's
   gitignored `CLAUDE.local.md`. Every source the harness cites is public and
   identified unequivocally (arXiv ID / DOI / URL) in `references/harness.bib`.

## Contents

| Path | What it is |
|------|------------|
| `.claude/skills/research/` | Literature search/retrieval routing (paper-search + arxiv MCPs, AlphaXiv HTTP, fallbacks) |
| `.claude/skills/derive-from-sources/` | Grounded synthesis: read every source, verbatim-quote notes first, draft only from notes |
| `.claude/skills/eval-design/` | Building LLM evals: threat model → spec → questions → QC → Inspect, with a construct-validity checklist and LLM-judge audit rule |
| `.claude/skills/falsify/` | Claim destruction protocol: permutation nulls, bootstrap CIs, base-rate checks; Survives/Weakened/Failed scorecard |
| `.claude/skills/validate-claims/` | Traceability protocol: every number → data file, every method sentence → code, every citation → real paper; loop to zero mismatches |
| `.claude/skills/research-log/` | The tree/log conventions and session ritual |
| `scripts/validate_research.py` | Mechanical validator for TREE.md + RESEARCH_LOG.md (structure, statuses, evidence existence, scorecard-gated claim graduation, tree↔log cross-refs) |
| `scripts/lint_skills.py` | Harness-specific `SKILL.md` checks that complement lanorme: portability (no machine-specific absolute paths), trigger phrasing, frontmatter typos |
| `lanorme.toml` | Config for [lanorme](https://github.com/lanorme/lanorme), the authority on Python quality and Agent Skills spec compliance (`SKILL-001..006`). `templates/lanorme.toml` ships to installed projects |
| `templates/` | Seed files for a new project: `CLAUDE.md`, `TREE.md`, `RESEARCH_LOG.md`, `mcp.json` |
| `references/harness.bib` | BibTeX for every source underpinning the harness design, with unequivocal identifiers |
| `research/ai-scientist-pitfalls/` | The literature survey the harness design answers to: pitfall taxonomy, per-source notes with read-depth tags, gap analysis |

## Installing into a new project

`install.py` copies the portable parts, renders the template placeholders, seeds
the project layout, and writes a starter gitignored `CLAUDE.local.md`.

```bash
# Interactive — prompts for anything not passed
python install.py ~/path/to/new-project

# Fully specified, non-interactive
python install.py ~/path/to/new-project \
    --name "Refusal Probe Transfer" \
    --description "do refusal directions transfer across model families" \
    --question "Does the Gemma refusal direction steer Llama refusals?" \
    --timebox "one week, solo" \
    --no-input
```

Options: `--context` (explicit project context, overrides `--timebox`),
`--no-reference` (skip copying `references/` and `research/`), `--force`
(overwrite existing files — without it, existing files are reported as SKIP and
left untouched), `--today ISO-DATE` (date for the seed log entry).

A fresh install passes `python scripts/validate_research.py` immediately: the
research log is seeded with a complete scaffolding entry and `TREE.md` with your
`Q1`. Anything you didn't supply stays visible as a `<PLACEHOLDER>` and is listed
in the installer's output rather than silently blanked.

Afterwards:
1. `git init && git add -A && git commit -m 'Scaffold from research-harness'`.
2. Extend the generated `CLAUDE.local.md` with your machine-local pointers.
3. Requirements: `arxiv-mcp-server` and `uv` on PATH (see `templates/mcp.json`);
   Python 3.10+ for the validator. After your first paper download, verify papers
   land in `data/papers/` — if not, make the storage path in `.mcp.json` absolute.

## Scripts

Every script is a self-contained [PEP 723](https://peps.python.org/pep-0723/) uv
script: dependencies are declared inline at the top, so there is no environment
to create and no requirements file to install.

```bash
uv run scripts/validate_research.py     # tree + log structural validation
uvx lanorme check .                     # Python quality + Agent Skills spec
uv run scripts/lint_skills.py           # harness-specific skill checks
uv run install.py TARGET --name "..."   # install into a project
```

The harness holds AI agents to mechanical checks, so it applies the same to
itself: `uvx lanorme check .` must pass on this repo. lanorme owns Python
quality (complexity, size, typing, security) and Agent Skills spec compliance;
`lint_skills.py` adds only what lanorme does not cover — portability, trigger
phrasing, and frontmatter typos. Run both; they do not overlap.

**Is lanorme required downstream?** No. Installed projects get a
`lanorme.toml`, but lanorme is an optional external tool: the harness's own
integrity gates (`validate_research.py`, `lint_skills.py`) are self-contained
uv scripts with no dependency on it, and a project that never runs lanorme
still has every research-integrity guarantee. Adopt it when a project writes
substantial analysis code — the failure it catches (long, high-complexity
functions producing plausible but wrong numbers) is a documented AI-scientist
failure mode, not a style preference. Skip it for a project that is mostly
prose and notebooks.

They are also executable directly (`./scripts/lint_skills.py`) via a
`#!/usr/bin/env -S uv run --script` shebang. Requires `uv` on PATH.

## Maintaining the harness

Improvements discovered inside a project (a new gap, a better rule, a pitfall
from new literature) come back here as commits, with sources added to
`references/harness.bib` and, when a survey was involved, notes under
`research/`. The same evidence discipline applies to the harness itself: a
design rule without a traceable source is a preference, not a finding.
