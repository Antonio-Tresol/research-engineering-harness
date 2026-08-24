# The record: TREE.md and RESEARCH_LOG.md

Two markdown files carry the project's state and history. They are canonical
and hand-editable. Every derived view is computed from them on read, so there
is no second store to drift out of sync.

## The tree and the log

`TREE.md` is current belief: a tree of questions, hypotheses, experiments,
and claims. Edit it in place; a claim that fails falsification changes status
there. `RESEARCH_LOG.md` is append-only history: one dated entry per session,
newest first, answering the same four questions, never revised. Keeping both
means you can always ask what is believed now, and also what you believed
last Tuesday before the result came in.

Each tree node has a status, and anything concluded links the file that
supports it:

```markdown
- Q1: Does the Gemma refusal direction steer Llama refusals? [open]
  - Q1.H1: The refusal direction transfers across model families [open]
    - Q1.H1.E1: Steer Llama with the Gemma direction, measure refusal rate [done] | evidence: results/steering.json
    - Q1.H1.E1.C1: Steering raises Llama refusal rate above baseline [survived] | evidence: results/steering.json
```

## How a claim's status is decided

Every claim starts `unvalidated`. It can only become `survived`, `weakened`,
or `failed` once a falsification or validation run has produced a report
file, which the checker requires by name. When the status is decided, the
evidence is pinned: a commit hash and a per-file sha256 embedded in the
scorecard, so a later `verify` catches evidence files that changed after
certification. `failed` is a normal outcome. Retracting a claim before it
ships is the system working.

## Plain language

Both files are written for a reader who knows the field and has never opened
the repository: the standard vocabulary of machine learning, statistics, and
software engineering, complete sentences, no shorthand, and no names invented
in one session. Their whole job is to be read by someone without the
writer's context: a collaborator, a reviewer, the next agent session. The
validator catches the worst telegraph shorthand; the research-log skill
carries the rest of the contract, including the rule that a thing with no
standard name gets described in plain words wherever it appears.

Node text stays under 1,200 characters. A node is a headline; protocols,
registrations, and amendments live as dated documents under `notes/`, linked
from the node as evidence. This limit was calibrated on real project trees
whose nodes had grown past 12,000 characters.

## Two modes for code

Exploratory work in notebooks and scratch scripts is exempt from linting on
purpose. Most research is de-risking, and gating it just slows you down. The
checks apply to promoted code, meaning anything a claim now rests on.
