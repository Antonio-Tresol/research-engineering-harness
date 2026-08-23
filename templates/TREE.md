# Research tree

State of the project: questions → hypotheses → experiments → claims.
Grammar and status vocabulary: see `.claude/skills/research-log/SKILL.md`.
Validate with `python scripts/validate_research.py`. Never delete nodes — mark
them `abandoned` and point at the log entry explaining why.

Node text is plain language for a reader who has never opened this repository:
standard AI/ML/software terms only, no shorthand, no coined names, no phrasing
that needs the codebase to parse. Any project-specific term is defined once in
the research log's Project summary before it appears here. Below this preamble
the file holds nodes only — narrative belongs in `RESEARCH_LOG.md`. A node is
a headline (under 1,200 characters): protocols, registrations, and amendments
live as dated documents in `notes/`, linked from the node, never inlined.

- Q1: <the project's research question> [open]
