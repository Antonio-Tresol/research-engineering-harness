#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Mechanical validator for TREE.md and RESEARCH_LOG.md.

Exit 0 = both documents structurally valid; nonzero = violations (printed).
Run from the project root: uv run scripts/validate_research.py
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path
from typing import Final

ROOT: Final[Path] = Path(__file__).resolve().parent.parent
TREE: Final[Path] = ROOT / "TREE.md"
LOG: Final[Path] = ROOT / "RESEARCH_LOG.md"

STATUS_VOCAB: Final[dict[str, set[str]]] = {
    "Q": {"open", "answered", "abandoned"},
    "H": {"open", "supported", "refuted", "abandoned"},
    "E": {"planned", "running", "done", "abandoned"},
    "C": {"unvalidated", "survived", "weakened", "failed"},
}

NODE_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<indent>\s*)-\s+(?P<id>[QHEC0-9.]+):\s+(?P<text>.*?)"
    r"\s+\[(?P<status>[a-z-]+)\]"
    r"(?:\s*\|\s*evidence:\s*(?P<evidence>[^|]+?))?"
    r"(?:\s*\|\s*log:\s*(?P<log>\d{4}-\d{2}-\d{2}))?\s*$"
)

LOG_HEADER_RE: Final[re.Pattern[str]] = re.compile(r"^### (\d{4}-\d{2}-\d{2})\s*$")
LOG_BULLETS: Final[list[str]] = [
    "What I did:",
    "What I expected vs what happened:",
    "What this changes about my thinking:",
    "What I will do next:",
]


def node_type(node_id: str) -> str | None:
    """Last letter-prefixed segment determines type: Q1.H2.E1 -> E."""
    seg = node_id.split(".")[-1]
    m = re.match(r"([QHEC])\d+$", seg)
    return m.group(1) if m else None


def validate_tree(errors: list[str]) -> dict[str, str | None]:
    """Returns {node_id: log_date} for cross-checking against the log."""
    if not TREE.exists():
        errors.append("TREE.md missing")
        return {}
    seen: dict[str, str | None] = {}
    lines = TREE.read_text().splitlines()
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        # Heuristic: list items whose first token looks like a node ID
        first = stripped[2:].split(":", 1)[0]
        if not re.match(r"^[QHEC]\d+(\.[QHEC]\d+)*$", first):
            continue
        m = NODE_RE.match(line)
        if not m:
            errors.append(f"TREE.md:{lineno}: node line does not match grammar: {stripped[:80]}")
            continue
        nid, status = m["id"], m["status"]
        ntype = node_type(nid)
        if ntype is None:
            errors.append(f"TREE.md:{lineno}: bad node id {nid!r}")
            continue
        if nid in seen:
            errors.append(f"TREE.md:{lineno}: duplicate id {nid}")
        seen[nid] = m["log"]
        # Parent must exist and be a prefix
        if "." in nid:
            parent = nid.rsplit(".", 1)[0]
            if parent not in seen:
                errors.append(f"TREE.md:{lineno}: {nid} has no parent {parent} defined above it")
        elif ntype != "Q":
            errors.append(f"TREE.md:{lineno}: top-level node {nid} must be a question (Q)")
        # Status vocabulary
        if status not in STATUS_VOCAB[ntype]:
            errors.append(
                f"TREE.md:{lineno}: {nid} status {status!r} not in {sorted(STATUS_VOCAB[ntype])}"
            )
        # Evidence requirements
        needs_evidence = (ntype == "E" and status == "done") or (
            ntype == "C" and status != "unvalidated"
        )
        evidence = [e.strip() for e in (m["evidence"] or "").split(",") if e.strip()]
        if needs_evidence and not evidence:
            errors.append(f"TREE.md:{lineno}: {nid} [{status}] requires evidence: <path>")
        for ev in evidence:
            if not (ROOT / ev).exists():
                errors.append(f"TREE.md:{lineno}: {nid} evidence path does not exist: {ev}")
        # Claims graduate only via a falsify/validation scorecard artifact
        if ntype == "C" and status in {"survived", "weakened", "failed"}:
            if not any(
                re.search(r"falsif|scorecard|validat", Path(ev).name, re.IGNORECASE)
                for ev in evidence
            ):
                errors.append(
                    f"TREE.md:{lineno}: {nid} [{status}] needs a scorecard evidence file "
                    "(name containing 'falsify', 'scorecard', or 'validation')"
                )
    # Rule 4: supported/refuted hypotheses need a validated child claim.
    statuses: dict[str, str] = {}
    for line in lines:
        m = NODE_RE.match(line)
        if m and node_type(m["id"]):
            statuses[m["id"]] = m["status"]
    for nid, status in statuses.items():
        if node_type(nid) == "H" and status in {"supported", "refuted"}:
            kids = [
                k for k, s in statuses.items()
                if k.startswith(nid + ".") and node_type(k) == "C" and s in {"survived", "weakened"}
            ]
            if not kids:
                errors.append(
                    f"TREE.md: hypothesis {nid} is [{status}] but has no survived/weakened claim"
                )
    return seen


def validate_log(errors: list[str]) -> set[str]:
    """Returns the set of entry dates (ISO strings)."""
    if not LOG.exists():
        errors.append("RESEARCH_LOG.md missing")
        return set()
    text = LOG.read_text()
    if "## Project summary" not in text and "## **Project summary**" not in text:
        errors.append("RESEARCH_LOG.md: missing '## Project summary' section")
    dates: list[str] = []
    entries: dict[str, str] = {}
    current = None
    for line in text.splitlines():
        m = LOG_HEADER_RE.match(line)
        if m:
            current = m.group(1)
            dates.append(current)
            entries[current] = ""
        elif current:
            entries[current] += line + "\n"
    for d in dates:
        try:
            date.fromisoformat(d)
        except ValueError:
            errors.append(f"RESEARCH_LOG.md: bad date {d}")
    for a, b in zip(dates, dates[1:]):
        if a <= b:
            errors.append(f"RESEARCH_LOG.md: entries not newest-first ({a} then {b})")
    for d, body in entries.items():
        for bullet in LOG_BULLETS:
            pat = re.compile(re.escape(bullet) + r"\s*(\S.*)")
            if not pat.search(body):
                errors.append(f"RESEARCH_LOG.md {d}: missing or empty bullet '{bullet}'")
    return set(dates)


def main() -> int:
    errors: list[str] = []
    tree_nodes = validate_tree(errors)
    log_dates = validate_log(errors)
    for nid, log_ref in tree_nodes.items():
        if log_ref and log_ref not in log_dates:
            errors.append(f"TREE.md: {nid} references log {log_ref}, no such entry")
    if errors:
        print(f"FAIL — {len(errors)} violation(s):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"OK — TREE.md ({len(tree_nodes)} nodes) and RESEARCH_LOG.md ({len(log_dates)} entries) valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
