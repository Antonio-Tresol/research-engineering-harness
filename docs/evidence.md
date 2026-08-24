# Why these rules

Each rule answers a documented failure mode of research agents, from
fabrication under time pressure to plausible numbers produced by buggy code.
The reasoning, with citations, is in [DESIGN.md](../DESIGN.md). The
underlying literature surveys, with per-source notes and read-depth tags,
are under `research/`, and the bibliographies are in `references/`.

The harness also evaluates itself: skill-trigger evals, behaviour probes
with placebo arms, red-team runs against the record mechanisms, usability
studies of the command-line tool, and the incidents that shaped the design.
That research lives in the companion repository `research-harness-meta`
(currently private), which keeps its own tree, log, and evidence;
`DESIGN.md` here summarises the findings it cites. The same standard applies
to the harness as to any project built on it: a design rule without a
traceable source is a preference rather than a finding.
