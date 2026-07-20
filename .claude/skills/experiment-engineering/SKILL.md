---
name: experiment-engineering
description: >-
  The engineering contract for research code: two modes (explore fast, promote
  when it matters) and the non-negotiable observability requirements — structured
  logging, resumable checkpoints, fail-fast ordering, and error handling. Use
  whenever writing or reviewing an experiment script, pipeline, or any code that
  spends GPU time or API budget.
---

# Experiment engineering

Research code has two modes. Confusing them is what makes process feel like drag.

| | **Explore** | **Pipeline** |
|---|---|---|
| Looks like | notebook, `#%%` cells, throwaway script | `scripts/` or `src/`, CLI args, importable |
| Goal | time-to-insight | reproducibility and reuse |
| Polish (naming, structure, types) | **skip it** | apply it |
| Observability contract (below) | required as soon as a run costs real time or money | required always |
| Linting gates | not enforced | enforced |

Most work is explore mode — the workflow literature puts it around 75%. Code is
**promoted** to pipeline mode when it produces evidence a claim will rest on, when
someone else must run it, or when it will run more than a few times. Promotion is
the gate; there is no gate on exploring.

## The observability contract (non-negotiable for any run that costs time or money)

These are not polish. Polish can be deferred forever; these cannot, because
un-observable work has to be re-run, and re-running is slower than logging was.

1. **Structured results, written incrementally.** Append one JSON line per unit of
   work — metadata, inputs, outputs — to a `.jsonl` under `results/`. Analyze with
   pandas afterwards. Write as you go, not at the end: a crash at 90% must not cost
   90% of the run. These files are the evidence the research tree links to.
2. **Resumable by construction.** Before any expensive call, check whether its
   result already exists on disk; skip if so. Cache keyed by the inputs (one file
   per generation is enough; a few lines of code). The test: **kill the script
   halfway and re-run it — it should pick up where it left off, not start over.**
   Applies to API calls, generations, and long training loops (periodic checkpoints).
3. **Fail fast.** Order the script so the most likely crash happens as early as
   possible. Do not spend minutes tokenizing before the first backward pass can
   fail. Validate config, paths, credentials, and shapes up front; smoke-test on a
   tiny slice (a handful of items, the smallest model) before the full run.
4. **Error handling that preserves work.** A failure on one item must not kill the
   batch: catch per item, record the error into the results file as a row with an
   `error` field, and continue. Never swallow an exception silently, and never let
   a partial failure masquerade as a complete run — the results file must make the
   difference visible.
5. **Logging to a file, not just stdout.** Timestamped, with the run's config
   echoed at start. A terminal that scrolled away or an SSH session that dropped is
   not a record. Log the model identifier and date, the seed, and the git commit.
6. **Seeds and shuffling.** Fix and record seeds. Always shuffle datasets yourself —
   it is free, and do not rely on someone else having done it. Sample subsets
   randomly rather than taking the first *n*.

## Before you run it

Ask, in order: What is the motivation? Have I de-risked this (is there a cheaper
probe that would tell me it won't work)? What result do I expect? Am I changing too
many variables at once?

Then: **simple fast experiments on simple infra before big expensive experiments on
complex infra.** Get signal in minutes on a small model before committing GPU hours.

## After it runs, before you believe it

Look at the raw outputs, not only the metric. Plot the distribution; read actual
model responses; check the numbers are not crazy before investigating anything
programmatically. A metric computed over data you never looked at is where silent
bugs live — buggy code producing plausible-but-wrong gains is a documented failure
mode of AI-assisted research (see the harness's `research/` surveys).

## Conventions that keep runs findable

- Dated experiment folders with numbered scripts showing execution order:
  `experiments/<name>/YYMMDD_thing_v1/{1_generate.py, 2_score.py, 3_analyse.ipynb}`.
- Every script takes CLI arguments — makes it wrappable, testable, and
  parallelizable without editing code.
- Few dependencies, and none you don't understand.
- Use the fast inference path when generating at volume; naive `model.generate`
  loops are dramatically slower than dedicated inference libraries.

$ARGUMENTS
