# Changelog

All notable changes to the surface an installed project receives. That
surface is: the record grammar the validator enforces over `TREE.md` and
`RESEARCH_LOG.md`, the `research_graph.py` commands and their flags, the
installed skill names, the hook contracts (`PostToolUse` validation,
`SessionStart` verify report, the pre-commit gate), the scorecard and review
file formats under `results/` and `reviews/`, and `check.sh`. A breaking
change is one after which an installed project must act to stay green. In
the record grammar, a claim is one node of `TREE.md`, and its status may
leave `unvalidated` only when a falsification run has produced the claim's
report file.

Versions are semantic in that spirit: breaking changes raise the minor
version while 0.x lasts, new capability raises it too and says so, fixes
raise the patch. This file follows the spirit of
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The installer
stamps `.harness-version` into every scaffold so a project knows which
surface it holds.

## [Unreleased]

## [0.2.0] - 2026-08-24

Derived from the 40 commits between the July 2026 Zenodo deposit (version
0.1.0) and today. The measurements each mechanism cites live in the
companion (currently private) `research-harness-meta` repository;
`DESIGN.md` summarises them with sources.

### Added

- `scripts/research_graph.py`: one command-line tool over the whole record.
  Reads: `tree`, `show`, `search`, `path`, `evidence`, `orphans`, `json`,
  `mermaid`. Writes: `add`, `set-status`, `set-text`, `add-evidence`,
  `log`, `add-note`. Every write is validated before it lands and rolled
  back byte-identical when it would break the record; every write takes
  `--dry-run`. `verify` re-derives the record's health from disk, and
  `pin` records the commit, date, and a hash of every evidence file behind
  a claim whose status has been decided as `survived`, `weakened`, or
  `failed`, so a later change to that evidence is detectable. `set-text` was added
  after a usability study found it was the one missing command that forced
  hand edits.
- The independent reader (`review --run`, `review`, `review --waive`): a
  reader agent with none of the writer's context receives a document and
  reports every place it could not follow, quoting it verbatim. The
  mechanical checks verify the reading (quotes resolve, the reviewed
  text's hash matches, waivers answer recorded complaints) and never judge
  prose. Findings resolve by rewriting and re-reading, or by a waiver with
  grounds; waivers survive re-reads. Nothing in the review workflow can
  fail a build. By default the reader runs through the Claude Code CLI;
  `RESEARCH_READER_CMD` substitutes any agent command that accepts the
  prompt file and prints the reader's JSON.
- Verification blocks, a named section of a claim's report file: a claim
  verified by reading rather than computation records its reader runs with
  dates and verbatim quotes, and the validator
  resolves every quote against its cited file.
- Hooks for both supported agents. Claude Code: a `PostToolUse` hook
  re-validates after every edit to the two record files, and a
  `SessionStart` hook puts the `verify` report in front of every session at
  its start, including the restart after context compaction, when the
  session's history has just been summarised to fit its window. Codex: `.codex/hooks.json` wires the same two,
  with an adapter that hashes the record files and validates only when
  they changed. The installer wires the pre-commit gate automatically when
  the target is already a git repository.
- Release discipline: this changelog, `CONTRIBUTING.md`, a CI workflow
  running `./check.sh` on pull requests and pushes to main, and
  `.harness-version` stamped into every scaffold.

### Changed

- The plain-language contract in the research-log skill (one of the nine
  skills 0.1.0 shipped): standard
  vocabulary, no invented names, prose that stands without the codebase,
  and clean-up that must move displaced information into the log or a
  linked document before the words carrying it are deleted. The first
  version of the vocabulary rule asked for a glossary of coined terms; it
  now says to prefer rewriting in standard terms, with a glossary reserved
  for names no description can replace.
- The validator grew, each check added on measured evidence: checks
  against telegraph shorthand; a 1,200-character limit on node text, calibrated on two real
  project trees; rejection of malformed node ids and log entry headers,
  which the old validator silently skipped; and rejection of node-shaped
  lines inside code fences, which a red-team run had used to hide a
  claim from every other check.
- The documentation: the README shrank to what a visitor needs, five
  documents under `docs/` carry the depth, and the deep material moved
  there rather than being deleted.

### Fixed

- Re-reading a document no longer deletes its recorded waivers.
- A reader that tried to open the files a record cites died and looked
  like an interface error; it now recovers from the denied attempt and
  answers from the text alone.
- Usability defects found by reading agent transcripts: silent evidence
  loss on a rejected write, dry runs that reported nothing, and the
  rejection that made agents abandon the tool and edit the markdown by
  hand.

## [0.1.0] - 2026-07-27

Initial release, archived on Zenodo (version DOI 10.5281/zenodo.21617975):
the nine agent skills, the two record templates, the mechanical validator
for both files, `install.py`, the pre-commit gate, and
[lanorme](https://github.com/lanorme/lanorme), the code checker the
harness builds on, with the harness's own checks as its plugins. Everything in 0.2.0 was built on and measured
against this state.
