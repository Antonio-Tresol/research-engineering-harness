#!/usr/bin/env bash
# Every mechanical check, in one command.
#
#   lanorme  — code quality, Agent Skills spec compliance, and the harness's own
#              plugins (tensors, skill_portability). PYTHONPATH=. is what lets
#              lanorme import them from lanorme_plugins/.
#   validate_research.py — the research-integrity gate. Deliberately standalone
#              and dependency-free: a project that never installs lanorme must
#              still have every integrity guarantee. Skipped in the harness repo
#              itself, which is not a research project and has no TREE.md.
set -euo pipefail
cd "$(dirname "$0")"

PYTHONPATH=. uvx lanorme check "${1:-.}"

if [[ -f TREE.md ]]; then
    uv run scripts/validate_research.py
else
    echo "No TREE.md — skipping research-integrity gate (not a research project)."
fi
