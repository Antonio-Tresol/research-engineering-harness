# The checks

Every mechanical check of the research-engineering-harness, which turns a
repository into a research project with a trustworthy record. A project
keeps that record in two files: `TREE.md`, the tree of questions,
hypotheses, experiments, and claims, written one node per line, and
`RESEARCH_LOG.md`, the dated log. [The record](the-record.md) describes
both. The checks below run in this repository and in every project the
installer creates.

```bash
./check.sh
```

runs two layers:

| | Covers |
|---|---|
| [lanorme](https://github.com/lanorme/lanorme), plus the checks this repository adds as plugins | Python quality, the `SKILL.md` skill format, tensor shape discipline (`TENSOR-*`), skill portability (`HSKILL-*`), claim provenance (`PROV-*`), bookkeeping staleness (`STALE-*`) |
| `scripts/validate_research.py`, run inside a project by `scripts/research_graph.py verify` | Tree and log structure, evidence files exist, no claim status change without its falsification report (the scorecard file described in [the record](the-record.md)), tree-to-log cross-references, plain-language checks (no telegraph shorthand, and nothing in the tree file except the one-line nodes the grammar defines, so stray prose cannot hide from the rules); `verify` adds evidence that changed since a claim's status was decided, verbatim quotes that must still appear in the files they cite, and orphaned `notes/` documents |

The second layer, the validator, is a zero-dependency script, so a project
that never installs lanorme still gets every guarantee about evidence and about how a claim's status is decided.

## Provenance markers in prose

A number in a report carries a marker naming where it came from, invisible
once the Markdown renders:

```markdown
Steering raised the refusal rate to 62%.
<!-- claim: 0.62 from results/steering.json#refusal_rate -->
```

Re-run the experiment, get 0.58, forget to update the sentence, and the next
`./check.sh` fails with the old number and the new one side by side. This is
the failure that careful reading does not catch, because the prose still
looks right.

## The false-positive suite

`./check.sh` also runs the checks' own test suite. Roughly half of those
tests assert that a rule stays quiet: on rounded values, on documentation
examples inside code fences, on ordinary Python with no tensors, on folded
YAML. Each one records a false positive an earlier version of the checks
actually produced. A checker that cries wolf gets bypassed, and then its true positives
go unread too.

The rules are also measured against real repositories rather than only
against fixtures. One rule was deleted on that evidence: it produced 43
findings across four existing skill collections and not one of them was a
real problem.

## Staleness

Two checks answer a different question: not "is this consistent" but "has
the bookkeeping kept up". `STALE-001` compares, in git, how many commits
have touched `results/` or `scripts/` since the research tree (`TREE.md`)
last changed,
and warns past a threshold. `STALE-002` reads an `updated:` date from a
document's frontmatter and warns when git says the file changed after it.
Both are warnings, because only a person can say whether a run produced a
belief worth recording.

## Hooks

Both supported agents get the same two hooks. In Claude Code the project
settings wire them; in Codex, `.codex/hooks.json` does, with a small
adapter (`.codex/hooks/validate_record_hook.py`) that hashes `TREE.md` and
`RESEARCH_LOG.md` and runs the validator only when they changed, because Codex
sends different event payloads per tool. The Codex wiring follows the hook interface Codex documents and has not
yet been exercised in a live Codex session; if it misbehaves, delete
`.codex/hooks.json` and fall back to running the checks by hand: `verify`
at session start, the validator before ending. The `PostToolUse`
hook re-runs the validator after every edit to `TREE.md` or
`RESEARCH_LOG.md`, so failures land straight back in the agent's context. In
the behaviour evaluations run on the harness (summarised in
[why these rules](evidence.md)), agents reliably fixed what the validator
showed them; the
hook removes the need to remember to run it. The `SessionStart` hook puts
the `verify` report in front of every fresh or just-compacted session, so
the record's health is the first thing a session sees.

The optional pre-commit hook (`./hooks/install.sh`) blocks a commit when
checks fail, then lists what the change implies without blocking: results
that arrived with no tree update, a skill edited without touching the docs,
code and results moving together so an already-decided claim may need
re-checking, a shared document that changed since the
[independent reader](record-cli.md), an agent process that reads a
document with none of the writer's context, last read it, an
`updated:` date that wants bumping. Each reminder names the files that
triggered it, because a vague reminder gets skimmed and a specific one gets
acted on.
