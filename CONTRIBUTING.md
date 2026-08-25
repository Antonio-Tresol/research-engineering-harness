# Contributing to the research-engineering-harness

The harness turns a repository into a research project whose record can be
trusted: two canonical markdown files, a validator, one command-line tool
over them, agent skills, and hooks, all checked by
[lanorme](https://github.com/lanorme/lanorme), the standard-library code
checker the harness builds on and extends. Everything it ships was adopted because
a measured run of agents behaving on it said so; the measurements live in
the companion `research-harness-meta` repository.

## Principles

- **The record is the database.** `TREE.md` and `RESEARCH_LOG.md` are
  canonical and hand-editable; every derived view is computed on read,
  never stored beside them. A change that makes the markdown depend on a
  second store will not be accepted.
- **Gate only on facts.** A mechanical check may fail a build only for
  something with no false-positive risk: a cited file that does not exist,
  a quoted excerpt that does not appear in the file it cites, a claim
  status that changed with no falsification report on disk.
  Judgement (is this clear, is this well designed) is advisory, or
  delegated to an independent reader whose verdicts are themselves
  checkable. A checker that cries wolf gets bypassed and takes its true
  positives with it; this is measured, not asserted.
- **Norms and mechanisms together.** The written rules remove the reasons
  to cut corners; the mechanisms catch the mistakes honesty does not
  prevent. Red-teaming found each catching what the other misses, so a
  change that trades one for the other needs new evidence, not taste.
- **Plain language, no invented names.** Shared artefacts, meaning the
  skills, the documentation, the templates, and every message a tool
  prints, use standard
  AI/ML/software vocabulary and describe anything that has no standard
  name. The reader channel (`research_graph.py review`) is the check;
  run it on prose you touch.
- **Lab equipment never ships.** Eval runners, graders, and red-team
  scenarios measure agent behaviour ON the harness, and `COPY_IGNORE` in
  `install.py` keeps them out of the projects the installer creates.
  Adversarial or generated work runs in throwaway workspaces outside any
  real repository, so it cannot touch a real record.
- **Evidence before shipping.** A mechanism earns its place through a
  registered-prediction eval: predictions written before the runs, every
  condition run more than once, transcripts read by hand, because the
  numbers mislead until the traces are read. `experiment-engineering` and
  `eval-design` in `.claude/skills/` carry the method.
- **Shipped scripts are self-contained.** PEP 723 uv scripts with inline
  dependencies; the validator stays dependency-free so a project that
  installs nothing still gets every integrity guarantee.

## Setup

You need [`uv`](https://docs.astral.sh/uv/). There is no environment to
build; every script declares its own dependencies.

    ./check.sh          # formatting, lanorme and the harness's own checks, tests, record validation
    ./hooks/install.sh  # wire the pre-commit gate into .git/hooks

## Making a change

- **A validator or graph check**: add it to the module that owns the layer
  (`validate_research.py` for the grammar, `research_graph_checks.py` and
  friends for the derived record). Every check needs tests on both sides:
  fires on the defect, stays quiet on clean input. The false-positive
  suite is as load-bearing as the true-positive one.
- **A CLI command**: writes go through the write transaction (snapshot,
  write, validate, keep or roll back byte-identical) and take `--dry-run`.
  Update the recipes in `research_graph.py help` and the research-log
  skill if the workflow changes.
- **A skill**: `.claude/skills/<name>/SKILL.md`; the `description` field
  is the trigger, so say when to use it in behavioural terms. lanorme
  checks the file format; the trigger evals in the meta repository are the
  measure of whether it fires.
- **Anything user-facing**: update `CHANGELOG.md` under `[Unreleased]` in
  the same commit; the pre-commit reminder will point it out if you
  forget. Narrate the why, not just the what, and include upgrade steps
  when an installed project must act.

Before pushing: `./check.sh` green, and reread what you wrote as the
research partner who was not in the room when you wrote it.

## Cutting a release

Releases are archived on Zenodo automatically, so the release body is a
permanent, citable record: write it as carefully as anything else here.

1. Move the `[Unreleased]` entries into a new `## [X.Y.Z] - YYYY-MM-DD`
   section. Raise the minor version for new capability or for a change
   that requires an installed project to act, the patch version for fixes.
2. Set the same version in `HARNESS_VERSION` in `install.py`, which stamps
   it into every scaffold. A test fails if the shipped version has no
   section in the changelog.
3. Merge to `main` and wait for CI to pass on that exact commit.
4. Publish the release, which creates the tag. The Release workflow
   (Actions, then Release, then Run workflow on `main` with the version
   number) verifies the version against `HARNESS_VERSION` and the
   changelog, then publishes with that changelog section as the release
   body. The manual equivalent is:

       gh release create vX.Y.Z --target <commit> --title "vX.Y.Z" \
           --notes-file <the new changelog section>

5. A webhook tells Zenodo, which archives the release and mints a version
   DOI under the project's permanent concept DOI. Record the new version
   DOI in the list at the bottom of `CITATION.cff`, and set
   `date-released` to the date Zenodo published, which is the release
   timestamp in UTC and may fall a day later than your own.
