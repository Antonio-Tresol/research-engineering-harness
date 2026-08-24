# The record command-line tool

`scripts/research_graph.py` reads and writes the record as one typed graph.
The markdown files stay canonical and hand-editable; the tool is a paved
road over them, never a second store.

## Reading and writing

Navigate with `tree`, `show`, `search`, `path`, `evidence`, and `orphans`.
Export with `json` and `mermaid`. Change the record with `add`,
`set-status`, `set-text`, `add-evidence`, `log`, and `add-note`.

Every write is validated before it lands. A write that would break the
record is rolled back byte-identical, with an explanation of what it would
have broken. Every write command takes `--dry-run` to rehearse the change
and report the validator's verdict without touching the files.

`verify` re-checks everything from disk: structure, evidence files exist,
evidence that changed after a claim was decided, verification quotes that
must resolve in their sources, and orphaned `notes/` documents. It is the
first command an agent runs in a fresh session. `pin` records the commit,
date, and evidence hashes behind a decided claim. `help` prints the guide
with recipes.

## The independent reader

Whether the record communicates is a judgement no checker can make. The
validator catches "w/" and over-long nodes, never an unreadable paragraph.
So the judgement is delegated to a reader with none of the writer's context:

```bash
uv run scripts/research_graph.py review --run TREE.md
```

spawns a fresh reader process that receives only the document. No tools, no
repository, no conversation. It reports every place it could not follow,
each complaint quoting the file verbatim. The reader stands in for the
person the record is actually for: a research partner who shares the work
but none of the writer's saved state.

The mechanical layer then does what it is good at. Each quote must resolve
against the file; the review carries a hash of the text that was read, so
staleness is visible; `verify` and the pre-commit hook report a shared
document that changed since a reader last saw it. Findings resolve through
the same command: fix the text and read again, or keep it and record why
with `--waive`. A waiver must answer a real complaint, and waivers survive
re-reads.

The reader is spawned through an agent command-line tool: the Claude Code
CLI by default. To use another agent, set `RESEARCH_READER_CMD` to a shell
command; it receives the reader prompt at `{prompt_file}` and must print
the reader's JSON object on standard output.

Nothing in this channel can fail a build. A semantic verdict that can block
gets bypassed once and then forever, so the reader's findings are advisory,
and leaving one open is an honest recorded state, like an unvalidated claim.
