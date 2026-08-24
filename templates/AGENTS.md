# <PROJECT NAME> — <one-line description>

Instructions for any coding agent working in this repository (Codex, Claude
Code, Cursor, Aider, and anything else reading `AGENTS.md`). `CLAUDE.md` imports
this file, so there is one source of truth rather than two that drift.

<What this project is, who is working on it, and its timebox if any.>
Everything here is optimised for one thing: ending the project with **answers we
can trust**, with an audit trail proving it. A well-evidenced null, a refuted
hypothesis, or an honest "infeasible in the time available" is exactly as much a
success as a positive finding. There is no pressure to produce positive results,
only to record what is true.

## State and history (read these first, every session)

- `TREE.md`: the research tree, questions → hypotheses → experiments → claims,
  with statuses and evidence links. This is the current state of belief.
- `RESEARCH_LOG.md`: the daily log (4-question format, newest first). This is the
  append-only history. Never encode state only here or history only in the tree.
- Both files are written in plain language for a reader who has never opened
  this repository: standard AI, machine-learning, and software-engineering
  terms, complete sentences, no shorthand, and no invented names. A thing with
  no standard name gets described in ordinary words wherever it appears rather
  than named; the log's `## Glossary` section is a last resort, reserved for a
  name no description can replace. The `research-log` skill carries the full
  contract; the validator trips on the worst telegraph.
- `uv run scripts/validate_research.py`: mechanical validator for both. Must exit
  0 before ending any session and before any deliverable. In Claude Code a
  `PostToolUse` hook (`.claude/hooks/validate_research_hook.py`, wired in
  `.claude/settings.json`) also runs it after every edit to `TREE.md` or
  `RESEARCH_LOG.md` and feeds failures straight back; agents without hook
  support rely on the session-end run alone.
- `uv run scripts/research_graph.py`: the typed CLI over the whole record
  (tree + log + `notes/`). Read with `tree`, `show`, `search`, `path`,
  `evidence`; write with `add`, `set-status`, `set-text`, `add-evidence`,
  `log`, `add-note` — every write is validated before it lands and rolled
  back with an explanation when it would break the record. Run `verify` at
  session start and after any compaction (the validator plus evidence drift,
  verification quote anchors, review staleness, and orphaned notes), `pin`
  when a claim's status is decided, and `help` for the guide with recipes.
  Hand-editing the markdown stays fine; the CLI and validator hold both
  paths to the same rules.
- `uv run scripts/research_graph.py review --run TREE.md`: ask an outside
  reader what the record fails to communicate. A fresh agent with no tools
  and no project context reads the document and records every place it could
  not follow, quoting it verbatim; `review` reports the findings, and each is
  resolved through the same tool — fix the text and read again, or keep it
  and record why with `--waive`. Whether prose communicates is a judgement no
  mechanical check can make; this channel makes it, and the checks verify
  only that the reading happened, of this exact text, quoting real words.
  Findings never fail a build.
- `./check.sh`: every mechanical check. `lanorme` (code quality, Agent Skills
  spec, plus the harness plugins `tensors` for jaxtyping/einops discipline and
  `skill_portability`) followed by the research-integrity gate. Run after
  editing any skill, script, or pipeline.
- `./hooks/install.sh`: wires `hooks/pre-commit` into `.git/hooks` (the
  installer does this automatically when the project is already a git repo).
  A commit then blocks on `./check.sh` and prints non-blocking bookkeeping
  reminders; bypass a single commit with `git commit --no-verify`.

All scripts are self-contained PEP 723 uv scripts (inline dependencies, no venv
to manage) and use type hints throughout. New scripts in this project should
follow the same convention.

## The workflow

Phases iterate; the gates do not.

0. **Speed is a first-class constraint.** Most work is exploratory de-risking in
   notebooks and throwaway scripts, and that code is deliberately exempt from
   polish and linting (`experiment-engineering` has the two-mode table). Gates
   apply at *promotion*, when code produces evidence a claim rests on. What is
   never deferred, even in explore mode, is the observability contract: structured
   incremental logs, resumable checkpoints, fail-fast ordering, seeds. Unlogged
   fast work has to be re-run, and re-running is slower than logging was.
1. **Scope**. One narrow question answerable within the project's budget of
   data, models, and time. Use `research-ideation`: de-risk load-bearing
   components with cheap probes before executing, ordering by information gained
   per unit time. Write the question as `Q1` in TREE.md before anything else.
2. **Literature** (timebox it). Use the `research` skill for search and retrieval; papers
   land in `data/papers/`. Any synthesis document follows `derive-from-sources`:
   read every source, notes file with verbatim quotes first, draft only from notes.
3. **Design**. For eval work, follow the `eval-design` skill: threat model →
   specification → operational definitions → question design → QC, with the
   construct-validity checklist. Name the confound-of-concern explicitly and
   design at least one read that separates construct from confound.
4. **Experiment**. Follow `experiment-engineering`. Explore freely in notebooks;
   promoted pipelines live under `scripts/` or `src/`, results as `.jsonl` under
   `results/` written incrementally (these paths are the evidence the tree links).
   Any run costing real time or money must be resumable: kill it halfway and
   re-running should pick up where it left off. Fixed seeds; a result that can't
   be re-produced by re-running a script doesn't count as evidence.
5. **Falsify** (gate). Before any claim leaves `unvalidated`, run the `falsify` skill:
   design tests that could destroy each claim. Update claim statuses in TREE.md:
   `survived` / `weakened` / `failed`, scorecard linked as evidence.
6. **Validate** (gate). Before any document with numbers leaves the project, run
   `validate-claims`: every number traced to a results file, every methodology
   sentence to code, every citation to a real paper, looped to zero mismatches.
7. **Log**. End every session by appending the day's RESEARCH_LOG.md entry and
   running the validator (`research-log` skill has the full ritual).
8. **Communicate**. Use `communicate-results` for decks and write-ups: strongest
   message first, failed setups in backup, error bars and *n* on every number,
   full prompts and real outputs shown.

## Collaboration and parallelism

- **Branches and PRs between humans.** Direct commits to `main` are for solo
  work only. When more than one person is on the project, work happens on
  short-lived branches merged to `main` by PR; a PR that adds or changes
  results, claims, or documents with numbers runs `./check.sh` and the
  `validate-claims` gate before merge. `main` is always green: validator exit 0,
  all checks passing.
- **Worktrees between parallel sessions.** Two agent sessions in one clone will
  fight over TREE.md, RESEARCH_LOG.md, and `results/`. Run parallel sessions in
  separate git worktrees (`git worktree add ../<name> <branch>`; Claude Code can
  create one for a session with EnterWorktree), one branch per worktree, merged
  back like any other branch.
- **Be an orchestrator.** For work that fans out — sweeps, literature searches,
  reviews, independent experiments — delegate to subagents or an agent team and
  keep synthesis in the orchestrating session. Three rules learned the hard way:
  give subagents self-contained prompts (they do not see your conversation);
  give any subagent that executes untrusted or generated work a workspace
  *outside* the repository (a nested workspace let eval agents write fabricated
  state into a host project's tree); and keep a **single writer** for TREE.md
  and RESEARCH_LOG.md — subagents report findings back, the orchestrator records
  them. The tree survives parallelism because every update goes through a
  single writer.

## Non-negotiables

- No claim in any deliverable that is not a node in TREE.md with linked evidence.
- No quoted text that is not verbatim from a source read in-session.
- Honest nulls: an effect that doesn't appear is reported as such, never dressed
  up. A null or infeasible result recorded with evidence is a completed
  experiment, not a failure to complete one.
- Pivots are recorded, not erased: nodes become `abandoned`, never deleted.
- No private shorthand in shared artefacts. The tree, the log, code comments, and
  docs are read by people and future sessions with none of the writer's
  context: plain language and standard terminology throughout, so that what we
  share stays our common understanding.

## Tooling

- MCP: `arxiv-mcp-server` (paper storage: `data/papers/`, path relative to the
  project root; after your first download, verify papers actually land there and
  switch to an absolute path in `.mcp.json` if they don't), `paper-search-mcp`
  (multi-source search). Configured in `.mcp.json`.
- Skills live in `.claude/skills/<name>/SKILL.md`, with `.agents/skills`
  symlinked to the same directory so Codex finds them too. Both load skills
  automatically from the `description` field. If your agent does neither, read
  the file that matches before starting that kind of work:

  | Read this | When |
  |---|---|
  | `research-ideation` | choosing what to run next, scoping, or stuck |
  | `research` | searching or retrieving literature |
  | `derive-from-sources` | writing anything derived from named sources |
  | `eval-design` | designing an eval or writing eval questions |
  | `experiment-engineering` | writing any script that costs GPU time or API budget |
  | `falsify` | before any claim leaves `unvalidated` |
  | `validate-claims` | before any document with numbers leaves the project |
  | `research-log` | at the start and end of every session |
  | `communicate-results` | preparing an update, figures, or a write-up |

  All are generic and portable, with no machine-specific paths.
- Machine-specific pointers (local copies of reference material, related repos)
  live in `CLAUDE.local.md`, which is gitignored, so each team member keeps their
  own. All sources the skills cite are public; unequivocal identifiers (arXiv
  ID / DOI / URL) are in the harness repo's `references/harness.bib`.
- **Shared session configuration** (checked in, applies to everyone on clone):
  - `.claude/settings.json` — compaction forced at 50% context
    (`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`; effective on Opus 4.8 and most models,
    documented as having *no effect on Sonnet 5*, unverified on Fable), agent
    teams enabled (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`), and Opus as the
    advisor model (Fable is the intended advisor once its advisor rollout
    completes — currently unselectable per docs; revisit cost before flipping,
    since advisor calls bill at the advisor model's rates). Teams and
    advisor are experimental; advisor needs the
    Anthropic API. Personal opt-outs go in the gitignored
    `.claude/settings.local.json`, which overrides project settings.
  - `.codex/config.toml` — Codex auto-compaction at ~50% of a 400k window
    (`model_auto_compact_token_limit = 200000`; Codex takes tokens, not
    percentages — adjust if the default model's window differs). Loads only
    after you mark the project trusted, and note it *outranks* your personal
    `~/.codex/config.toml`. Codex subagents are on by default; shareable custom
    agent roles can be added under `.codex/agents/` if the project needs them.
