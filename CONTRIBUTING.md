# Contributing to the research-engineering-harness

The harness turns a repository into a research project whose record can be
trusted: two canonical markdown files, a validator, one command-line tool
over them, agent skills, and hooks. Everything it ships was adopted because
a measured run of agents behaving on it said so; the measurements live in
the companion `research-harness-meta` repository.

## Principles

- **The record is the database.** `TREE.md` and `RESEARCH_LOG.md` are
  canonical and hand-editable; every derived view is computed on read,
  never stored beside them. A change that makes the markdown depend on a
  second store will not be accepted.
- **Gate only on facts.** A mechanical check may fail a build only for
  something with no false-positive risk: a file that does not exist, a
  quote that does not resolve, a status that changed without its report.
  Judgement — is this clear, is this well designed — is advisory, or
  delegated to an independent reader whose verdicts are themselves
  checkable. A checker that cries wolf gets bypassed and takes its true
  positives with it; this is measured, not asserted.
- **Norms and mechanisms together.** The written rules remove the reasons
  to cut corners; the mechanisms catch the mistakes honesty does not
  prevent. Red-teaming found each catching what the other misses, so a
  change that trades one for the other needs new evidence, not taste.
- **Plain language, no invented names.** Shared artefacts — skills,
  documentation, templates, every message a tool prints — use standard
  AI/ML/software vocabulary and describe anything that has no standard
  name. The reader channel (`research_graph.py review`) is the check;
  run it on prose you touch.
- **Lab equipment never ships.** Eval runners, graders, and red-team
  scenarios measure agent behaviour ON the harness and stay out of
  scaffolds via `COPY_IGNORE` in `install.py`. Adversarial or generated
  work runs in fenced workspaces outside any real repository.
- **Evidence before shipping.** A mechanism earns its place through a
  registered-prediction eval: predictions written before the runs, every
  condition run more than once, transcripts read by hand — the numbers
  mislead until the traces are read. `experiment-engineering` and
  `eval-design` in `.claude/skills/` carry the method.
- **Shipped scripts are self-contained.** PEP 723 uv scripts with inline
  dependencies; the validator stays dependency-free so a project that
  installs nothing still gets every integrity guarantee.

## Setup

You need [`uv`](https://docs.astral.sh/uv/). There is no environment to
build; every script declares its own dependencies.

    ./check.sh          # formatting, lanorme + house plugins, tests, integrity gate
    ./hooks/install.sh  # wire the pre-commit gate into .git/hooks

## Making a change

- **A validator or graph check**: add it to the module that owns the layer
  (`validate_research.py` for the grammar, `research_graph_checks.py` and
  friends for the derived record). Every check needs tests on both sides:
  fires on the defect, stays quiet on clean input — the false-positive
  suite is as load-bearing as the true-positive one.
- **A CLI command**: writes go through the write transaction (snapshot,
  write, validate, keep or roll back byte-identical) and take `--dry-run`.
  Update the recipes in `research_graph.py help` and the research-log
  skill if the workflow changes.
- **A skill**: `.claude/skills/<name>/SKILL.md`; the `description` field
  is the trigger, so say when to use it in behavioural terms. `lanorme`
  checks the format; the trigger evals in the meta repository are the
  measure of whether it fires.
- **Anything user-facing**: update `CHANGELOG.md` under `[Unreleased]` in
  the same commit — the pre-commit reminder will point it out if you
  forget. Narrate the why, not just the what, and include upgrade steps
  when an installed project must act.

Before pushing: `./check.sh` green, and reread what you wrote as the
research partner who was not in the room when you wrote it.
