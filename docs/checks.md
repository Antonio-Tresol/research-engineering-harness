# The checks

```bash
./check.sh
```

runs two layers:

| | Covers |
|---|---|
| `lanorme` + harness plugins | Python quality, Agent Skills spec, tensor shape discipline (`TENSOR-*`), skill portability (`HSKILL-*`), claim provenance (`PROV-*`), bookkeeping staleness (`STALE-*`) |
| `scripts/validate_research.py`, run via `scripts/research_graph.py verify` in projects | Tree and log structure, evidence files exist, no status change without a falsification report, tree-to-log cross-references, plain-language checks (no telegraph shorthand, nothing but nodes in the tree); `verify` adds evidence that changed since a claim was decided, verification quote anchors, and orphaned `notes/` documents |

The integrity gate is a zero-dependency script, so a project that never
installs [lanorme](https://github.com/lanorme/lanorme) still gets every
guarantee about evidence and about how a claim's status is decided.

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
YAML. Each one encodes a false positive that was genuinely shipped at some
point. A checker that cries wolf gets bypassed, and then its true positives
go unread too.

The rules are also measured against real repositories rather than only
against fixtures. One rule was deleted on that evidence: it produced 43
findings across four existing skill collections and not one of them was a
real problem.

## Staleness

Two checks answer a different question: not "is this consistent" but "has
the bookkeeping kept up". `STALE-001` compares, in git, how many commits
have touched `results/` or `scripts/` since the research tree last changed,
and warns past a threshold. `STALE-002` reads an `updated:` date from a
document's frontmatter and warns when git says the file changed after it.
Both are warnings, because only a person can say whether a run produced a
belief worth recording.

## Hooks

In Claude Code sessions the project settings wire two hooks. A `PostToolUse`
hook re-runs the validator after every edit to `TREE.md` or
`RESEARCH_LOG.md`, so failures land straight back in the agent's context. In
behaviour runs, agents reliably fixed what the validator showed them; the
hook removes the need to remember to run it. A `SessionStart` hook puts the
`verify` report in front of every fresh or just-compacted session, so the
record's health is the first thing a session sees.

The optional pre-commit hook (`./hooks/install.sh`) blocks a commit when
checks fail, then lists what the change implies without blocking: results
that arrived with no tree update, a skill edited without touching the docs,
code and results moving together so a decided claim may need re-checking, a
shared document that changed since an independent reader last saw it, an
`updated:` date that wants bumping. Each reminder names the files that
triggered it, because a vague reminder gets skimmed and a specific one gets
acted on.
