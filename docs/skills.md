# The skills

Skills are `SKILL.md` files carrying the method: how to run a literature
search, how to design an eval, how to attack a claim. The agent follows a
documented procedure instead of improvising one per session. Claude Code and
Codex both load them automatically from the `description` field, and
`AGENTS.md` lists which one applies to which situation for agents that do
not.

| Skill | What it covers |
|---|---|
| `research-ideation` | Test the parts a result depends on most with cheap probes first; order experiments by how much they can teach per unit of time |
| `research` | Literature search through the configured paper-search servers (Model Context Protocol), with plain web-search fallbacks when they are absent |
| `derive-from-sources` | Read every source, take verbatim-quote notes, draft only from the notes |
| `eval-design` | Threat model, specification, question design, QC, construct-validity checklist, LLM-judge audit |
| `experiment-engineering` | Observability contract, API concurrency and backoff, GPU batching, tensor discipline. Includes runnable reference code |
| `falsify` | Permutation nulls, bootstrap CIs, base-rate checks, and tests that a qualitative label can actually distinguish the cases it claims to |
| `validate-claims` | Trace every number to data, every method sentence to code, every citation to a real paper |
| `research-log` | Tree and log grammar, the [plain-language rules](the-record.md), and the session routine: `verify` at session start, the day's log entry and the validator at session end |
| `communicate-results` | Strongest message first, error bars, real model outputs shown |

## Agent compatibility

Instructions live in `AGENTS.md`, the cross-tool standard; `CLAUDE.md`
imports it in one line so the two cannot drift. Skills use the shared
`SKILL.md` format and live in `.claude/skills/`, with `.agents/skills`
symlinked to the same directory, so Claude Code and Codex both load them
automatically and neither sees a stale copy. The checks are plain scripts
and care about none of this.

On Windows, git needs `core.symlinks=true` and Developer Mode. Without them
it checks the symlink out as a text file and Codex silently finds no skills.
`HSKILL-004`, one of the harness's own [checks](checks.md), catches exactly
that, and the installer falls back to copying where symlinks are
unavailable.
