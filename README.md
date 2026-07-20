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
| `templates/` | Seed files for a new project: `CLAUDE.md`, `TREE.md`, `RESEARCH_LOG.md`, `mcp.json` |
| `references/harness.bib` | BibTeX for every source underpinning the harness design, with unequivocal identifiers |
| `research/ai-scientist-pitfalls/` | The literature survey the harness design answers to: pitfall taxonomy, per-source notes with read-depth tags, gap analysis |

## Installing into a new project

```bash
PROJECT=/path/to/new-project
mkdir -p "$PROJECT"/{data/papers,results,notes}
cp -R .claude "$PROJECT"/
cp -R scripts "$PROJECT"/
cp templates/CLAUDE.md templates/TREE.md templates/RESEARCH_LOG.md "$PROJECT"/
cp templates/mcp.json "$PROJECT"/.mcp.json
cd "$PROJECT" && git init
printf 'data/papers/\n__pycache__/\n.venv/\n.DS_Store\nCLAUDE.local.md\n' > .gitignore
```

Then, in the project:
1. Fill in the `<PLACEHOLDERS>` in `CLAUDE.md` and `RESEARCH_LOG.md`.
2. Write your own gitignored `CLAUDE.local.md` with machine-local pointers
   (local copies of reference material, related repos on your machine).
3. Requirements: `arxiv-mcp-server` and `uv` on PATH (see `templates/mcp.json`);
   Python 3.10+ for the validator. After your first paper download, verify papers
   land in `data/papers/` — if not, make the storage path in `.mcp.json` absolute.
4. Write `Q1` in `TREE.md`, and start.

## Maintaining the harness

Improvements discovered inside a project (a new gap, a better rule, a pitfall
from new literature) come back here as commits, with sources added to
`references/harness.bib` and, when a survey was involved, notes under
`research/`. The same evidence discipline applies to the harness itself: a
design rule without a traceable source is a preference, not a finding.
