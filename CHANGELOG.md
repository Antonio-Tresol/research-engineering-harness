# Changelog

All notable changes to the surface an installed project receives. That
surface is: the record grammar the validator enforces over `TREE.md` and
`RESEARCH_LOG.md`, the `research_graph.py` commands and their flags, the
installed skill names, the hook contracts (`PostToolUse` validation,
`SessionStart` verify report, the pre-commit gate), the scorecard and review
file formats under `results/` and `reviews/`, and `check.sh`. A breaking
change is one after which an installed project must act to stay green.

Versions are semantic in that spirit: breaking changes raise the minor
version while 0.x lasts, new capability raises it too and says so, fixes
raise the patch. This file follows the spirit of
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The installer
stamps `.harness-version` into every scaffold so a project knows which
surface it holds.

## [Unreleased]

## [0.2.0] - 2026-08-24

Everything between the July deposit and today. The measurements every
mechanism cites live in the research record of the companion (currently
private) `research-harness-meta` repository; `DESIGN.md` summarises them
with sources.

### The record system

- Two canonical markdown files per project: `TREE.md` (questions →
  hypotheses → experiments → claims, each with a status and evidence links)
  and `RESEARCH_LOG.md` (dated entries, newest first, four fixed questions).
  The files are the database; everything else is derived from them on read.
- `scripts/validate_research.py`: the mechanical validator. It checks
  structure, statuses, that evidence files exist, claim statuses only change with a
  falsification report, node text under 1,200 characters, no telegraph
  shorthand, no node-shaped lines hidden in code fences, malformed node ids
  and log headers rejected by name.
- `scripts/research_graph.py`: one command-line tool over the whole record.
  Reads: `tree`, `show`, `search`, `path`, `evidence`, `orphans`, `json`,
  `mermaid`. Writes: `add`, `set-status`, `set-text`, `add-evidence`, `log`,
  `add-note`. Every write is validated before it lands, and rolled back
  byte-identical when it would break the record. `verify` re-derives the
  record's health from disk; `pin` records commit, date, and a hash of every
  evidence file behind a decided claim, so later drift is detectable.
- Verification blocks: claims verified by reading (traces, literature) carry
  a machine-checkable block: reader runs with dates, and verbatim quotes
  that must resolve in the cited files.

### The clarity review channel

- `review --run <file>`: an independent reader agent, with no shared
  context, no tools, and only the document, reports every place it cannot
  follow,
  quoting verbatim. The mechanical checks verify the judging (quotes
  resolve, the reviewed text's hash matches, waivers answer real
  complaints), never the prose. `review` reports; `review --waive` records
  a disagreement with grounds. Findings can stay open; nothing here fails
  a build.

### Skills, hooks, install

- Nine agent skills installed under `.claude/skills/`, with `.agents/skills`
  symlinked for other agents: research-ideation, research,
  derive-from-sources, eval-design, experiment-engineering, falsify,
  research-log, validate-claims, communicate-results. The research-log
  skill carries the plain-language contract: standard vocabulary, no
  invented names, complete sentences, prose that stands without the
  codebase; the reader is your research partner, and the record is the one
  place you actually meet.
- Hooks: a `PostToolUse` hook re-validates after any edit to the two record
  files; a `SessionStart` hook puts the verify report in front of every
  fresh or just-compacted session; `hooks/pre-commit` blocks on `check.sh`
  and prints non-blocking bookkeeping reminders.
- `install.py` scaffolds all of it into a project, renders the templates,
  wires the git hook when a repository exists, excludes the harness's lab
  equipment, and stamps `.harness-version`.

### Upgrading a project scaffolded before 0.2.0

Re-run `install.py` over the project (it reports what it would overwrite),
or copy `scripts/`, `.claude/`, and `hooks/` by hand. Then expect and work
through, in order: node-length findings on any tree written without the
1,200-character limit (move detail into `notes/` documents; the relocation
recipe is in the research-log skill); malformed node ids the old validator
silently skipped, now rejected by name; and the first `review --run` of each
record file, which will report real findings; fix or waive them through the
tool. The emotion-vectors migration in the meta record is the worked example
of exactly this upgrade.

## [0.1.0] - 2026-07-27

Initial release, archived on Zenodo (version DOI 10.5281/zenodo.21617975):
the nine agent skills, the two record templates, the mechanical validator
for both files, `install.py`, the pre-commit gate, and lanorme with the
harness's own plugins. Everything in 0.2.0 was built on and measured
against this state.
