# Research Engineering Harness

[![CI](https://github.com/Antonio-Tresol/research-engineering-harness/actions/workflows/ci.yml/badge.svg)](https://github.com/Antonio-Tresol/research-engineering-harness/actions/workflows/ci.yml)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21617974.svg)](https://doi.org/10.5281/zenodo.21617974)
[![Licence: MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)

The harness turns a repository into a research project whose record can be
trusted. It exists because science is not the process of proving a
hypothesis: it is the sustained effort to break your hypotheses until the
ones left standing are worth believing. An AI-assisted project has to hold
both itself and its agents to that.

It is set of agentware meant to make doing research engineering with agents more reliable. It is built with
AI safety research in mind but it might be useful for any empirical work where an agent writes the
code and the write-up. Works with Claude Code, Codex, and anything else
reading [`AGENTS.md`](https://agents.md/).

## Quick start

```bash
git clone https://github.com/Antonio-Tresol/research-engineering-harness
cd research-engineering-harness

uv run install.py ~/my-project \
    --name "Refusal Probe Transfer" \
    --question "Does the Gemma refusal direction steer Llama refusals?"

cd ~/my-project
git init && ./hooks/install.sh    # optional: check on every commit
./check.sh
```

## What it looks like in use

The beliefs live in `TREE.md` as a tree of questions, hypotheses,
experiments and claims. Each node has a status and anything you have
concluded links the file that supports it:

```markdown
- Q1: Does the Gemma refusal direction steer Llama refusals? [open]
  - Q1.H1: The refusal direction transfers across model families [open]
    - Q1.H1.E1: Steer Llama with the Gemma direction, measure refusal rate [done] | evidence: results/steering.json
    - Q1.H1.E1.C1: Steering raises Llama refusal rate above baseline [survived] | evidence: results/steering.json
```

That last line is a lie, and `./check.sh` says so:

```
FAIL — 1 violation(s):
  - TREE.md:11: Q1.H1.E1.C1 [survived] needs a scorecard evidence file
    (name containing 'falsify', 'scorecard', or 'validation')
```

A claim only reaches `survived` after something tried to kill it.

When something cannot be check mechanically, the cli utility can spawn an agent reviewer to take a look:

```bash
uv run scripts/research_graph.py review --run TREE.md
```

## Documentation

- [The record: TREE.md and RESEARCH_LOG.md](docs/the-record.md). The two
  files, claim statuses, and the writing rules that keep both readable by
  someone who was not in the session that wrote them.
- [The record command-line tool](docs/record-cli.md). Reading, validated
  writes, `verify`, and the independent reader.
- [The checks](docs/checks.md). The validator, the code-quality checks
  built on [lanorme](https://github.com/lanorme/lanorme) with the
  harness's own plugins, the provenance markers, the false-positive
  suite, and the hooks.
- [The skills](docs/skills.md). What each of the nine covers, and how they
  load in Claude Code and Codex.
- [Why these rules](docs/evidence.md). The evidence and the design
  rationale, with [DESIGN.md](DESIGN.md) carrying the full argument.

## Versioning

`CHANGELOG.md` narrates every change to what installing the harness puts
into a project: the record format the validator enforces, the command-line
tool, the skills, the hooks, and `check.sh`. It includes upgrade steps
whenever an already-installed project must act, and a breaking change is
exactly one that requires such action. `install.py` stamps
`.harness-version` into each scaffold so a project knows what it holds.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the principles a change is
reviewed against and how to add a check, a command, or a skill.

## Citation

Archived on Zenodo. The DOI below is the *concept* DOI: it always resolves to the
newest version, which is usually what you want in a bibliography.

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21617974.svg)](https://doi.org/10.5281/zenodo.21617974)

```bibtex
@misc{badillaolivas2026harness,
author = {Badilla-Olivas, Antonio},
doi = {10.5281/zenodo.21617974},
month = {8},
title = {research-engineering-harness},
url = {https://github.com/Antonio-Tresol/research-engineering-harness},
year = {2026}
}
```

Generated from `CITATION.cff` with `cffconvert`; edit that file rather than this
block, so the two cannot disagree.
