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

### Added

- A feedback channel from the agents the harness scaffolds. Every
  scaffold's `AGENTS.md` now carries a "Feedback to the harness"
  section telling agents where their experience should go: defects to
  their own issues on this repository, friction and missing pieces to
  the standing feedback thread (issue #13), and — the signal the
  harness wants most — corrections a human had to make on ground the
  norms already claim to cover, quoted. It also states the rules of the
  road: name the `.harness-version`, post nothing project-confidential
  to the public tracker, and fall back to `notes/harness-feedback.md`
  when the environment has no GitHub access or the user prefers not to
  post. Until now this loop ran only through a project's own humans
  carrying reports by hand; issues #2 through #12 all arrived that way.

### Fixed

- Re-installing over an existing project no longer destroys it. `copy_dir`
  removed the destination tree before copying, so `--force`, the only
  documented way to take an update, deleted whatever the project kept
  under `tests/`, `.claude/`, `scripts/` and `lanorme_plugins/` — its own
  test files, its own skills, its own plugins. It now merges file by file
  and never deletes, so `--force` overwrites the harness's files and leaves
  the project's alone. Found while updating a project from a pre-`0.2.1`
  scaffold, where the only safe route was to install without `--force` and
  then sync directory contents by hand.
- `TREE.md` and `RESEARCH_LOG.md` are never replaced, even under `--force`.
  A re-install rendered the seed scaffold over them, so taking an update
  destroyed the record the harness exists to protect. They now follow the
  rule the pre-commit hook already followed. Upgrade note: a project that
  re-installed with `--force` before this release should check its record
  against git history.
- A plain re-install now carries a release's new files into a project that
  already has the directory. `copy_dir` skipped any directory that existed,
  so without `--force` nothing new arrived and with `--force` everything
  was deleted first; there was no setting that simply updated a project.
- `tests/test_codex_hooks.py` stays home. It reads `templates/`, which does
  not ship, so every project installed since it was added received a test
  that could not pass. `test_every_shipped_test_passes_in_a_fresh_project`
  is now the forcing function, running the shipped suite inside a fresh
  scaffold rather than naming files one at a time. Upgrade note: delete
  `tests/test_codex_hooks.py` from an installed project.

## [0.3.0] - 2026-08-25

Every entry here traces to one downstream project's first day of real
use (issues #4 to #12): a scaffolded repository whose gate was silently
passing, and whose collection script exhibited three failure classes the
experiment-engineering skill did not yet name. The minor version rises
because the Added entries are new capability, per the rule above.

### Fixed

- `check.sh` ran its two ruff steps as one `a && b` statement, and under
  `set -e` a failure to the left of `&&` aborts nothing: a formatting
  failure was swallowed and the lint step never ran, while the gate
  exited 0 (issue #4). In this repository the swallow was hiding four
  unformatted test files and an unsorted import block; in the downstream
  project that found it, 27 files. The steps are now separate
  statements, the gate has its own tests (it must fire on bad input and
  stay quiet on clean input, like every other check here), and the ruff
  version is pinned in both `check.sh` and `ruff.toml` so the verdict
  cannot drift with formatter releases.
- The shipped tests errored at collection under bare pytest, looking
  like broken code instead of a missing dependency (issue #8). The two
  modules that need lanorme now skip with the remedy in the message, and
  a shipped `pytest.ini` replaces every per-file `sys.path` edit in the
  tests with pytest's own import mechanism.
- Ten dead imports and one unsorted import block across the tooling and
  a skill reference, found by pyflakes on its first run.

### Added

- The gate's configuration ships (issue #5): `ruff.toml` (line length
  100, pyflakes and import sorting selected, jaxtyping reference files
  exempted from false positives) and `pytest.ini` now reach every
  scaffold, so a project extends the lint by editing configuration
  rather than the gate script, whose command line would override it.
- A credentials pattern (issue #11): scaffolds get a committed
  `.env.example` carrying names but never values, `.gitignore` learns to
  ignore every other `.env` file, and the experiment-engineering skill
  documents reading configuration once into one typed object with
  pydantic-settings and `SecretStr`, plus the rule that a key which
  reaches git history is rotated, not deleted.
- The experiment-engineering skill covers three failure classes found in
  a real scaffolded project: the vendor-SDK boundary (issue #9 — typed
  attribute access at one boundary module, so a renamed field crashes
  before budget is spent instead of silently corrupting results), the
  full identity of an API call (issue #10 — dated model snapshot, pinned
  provider, every sampling parameter sent and recorded, and
  reproducibility understood distributionally), and truncation as a
  measurement hazard (issue #12 — check `finish_reason` before parsing,
  size the cap by the cost asymmetry).
- `AGENTS.md` states the code norms in one place: promoted code lives in
  the project's package, modules are nouns and functions are verbs,
  types where they aid readability, no `getattr`/`hasattr`/`isinstance`
  papering or `sys.path` edits, canonical dependencies over
  hand-rolling, and no magic numbers in experiment configuration.

### Upgrading a project scaffolded before this version

Split the `&&` line in your `check.sh` (or re-copy it from the harness),
and copy `ruff.toml`, `pytest.ini`, and `.env.example` from a fresh
install. If your project already carries its own ruff configuration,
keep it and delete none of it: only make the two gate steps separate
statements.

## [0.2.1] - 2026-08-25

### Fixed

- On Windows, two checks (`PROV-003` claim provenance, `STALE-002` stale
  dates) built their glob match target with backslashes, matched no
  /-separated config glob, silently scanned zero files, and passed. Both
  now convert paths with `as_posix()`, a regression test encodes the
  failure on every platform, and a tripwire test keeps `str()` match
  targets out of the shipped checks. Reported as issue #2, with the fix
  verified on Windows by the reporter.
- A `.python-version` file pinning 3.13 now sits at the repository root
  and ships with every scaffold, so `check.sh` works when uv's default
  interpreter is older; without it, dependency resolution for the test
  step failed on an otherwise healthy repository. Reported as issue #3;
  `check.sh` had already gained an inline `--python 3.13` for its own
  test step, and the shipped pin covers every other entry point.

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
