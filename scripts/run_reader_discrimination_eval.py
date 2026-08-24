#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Does the independent reader discriminate a record known to communicate poorly?

Instrument validation for the clarity-review channel, run against this
project's own history: the record before the plain-language rewrite (which a
survey showed carried eighteen phrases a reader would have to look up) and the
record after it. The same pinned reader protocol reads both versions blind;
if the channel measures what it was built for, the before-version must draw
strictly more findings, and those findings must hit the invented vocabulary
the rewrite targeted rather than random sentences.

Predictions are registered in results/reader_discrimination/predictions.md
BEFORE this script's first run. Lab equipment: measures the harness, never
ships to projects.

    uv run scripts/run_reader_discrimination_eval.py \\
        --meta-root /path/to/research-harness-meta --before b4ea266 --readers 3
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Final

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from review_clarity import build_prompt, run_reader  # noqa: E402

DOCUMENTS: Final[tuple[str, ...]] = ("TREE.md", "RESEARCH_LOG.md")

# The vocabulary the rewrite removed, for scoring prediction 2 (construct:
# before-version findings should hit these, not random sentences). Lowercase
# substrings matched against each finding's excerpt and problem text.
TARGET_PHRASES: Final[tuple[str, ...]] = (
    "tripwire",
    "altitude",
    "graduat",
    "provenance pin",
    "canar",
    "cell",
    "norms-only",
    "norm layer",
    "pre-intervention",
    "abandonment path",
    "falsify gate",
    "falsify pass",
    "scorecard gate",
    "dialect",
    "codename",
    "accretion",
    "arm",
)


def text_at(root: Path, revision: str, document: str) -> str | None:
    """One file's content at a git revision, or None when git cannot show it."""
    done = subprocess.run(
        ["git", "show", f"{revision}:{document}"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return done.stdout if done.returncode == 0 else None


def is_target_hit(finding: dict[str, Any]) -> bool:
    """Whether one finding touches the vocabulary the rewrite targeted."""
    blob = (str(finding.get("excerpt", "")) + " " + str(finding.get("problem", ""))).lower()
    return any(phrase in blob for phrase in TARGET_PHRASES)


def read_version(
    version: str, revision: str, document: str, text: str, args: argparse.Namespace
) -> list[dict[str, Any]]:
    """All reader rows for one document at one version."""
    prompt = build_prompt(document, text)
    rows: list[dict[str, Any]] = []
    for index in range(args.readers):
        print(f"{version}/{document} reader {index + 1}/{args.readers} ...", file=sys.stderr)
        started = time.monotonic()
        parsed = run_reader(prompt, args.model, args.timeout)
        row: dict[str, Any] = {
            "version": version,
            "revision": revision,
            "document": document,
            "reader_index": index,
            "seconds": round(time.monotonic() - started, 1),
        }
        if parsed is None:
            # A dead reader must read as a dead reader, never as a clean verdict.
            row["dead"] = True
        else:
            findings = [f for f in parsed.get("findings") or [] if isinstance(f, dict)]
            row.update(
                dead=False,
                verdict=str(parsed.get("verdict", "")),
                finding_count=len(findings),
                target_hits=sum(1 for f in findings if is_target_hit(f)),
                findings=findings,
            )
        rows.append(row)
    return rows


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Per version-document finding counts, plus the separation verdict."""
    live = [r for r in rows if not r.get("dead")]
    counts: dict[str, list[int]] = {}
    for row in live:
        counts.setdefault(f"{row['version']}/{row['document']}", []).append(row["finding_count"])
    separated = {
        document: bool(counts.get(f"before/{document}"))
        and bool(counts.get(f"after/{document}"))
        and min(counts[f"before/{document}"]) > max(counts[f"after/{document}"])
        for document in DOCUMENTS
    }
    before_findings = [f for r in live if r["version"] == "before" for f in r.get("findings", [])]
    hit_rate = (
        sum(1 for f in before_findings if is_target_hit(f)) / len(before_findings)
        if before_findings
        else None
    )
    return {
        "dead_rows": sum(1 for r in rows if r.get("dead")),
        "finding_counts": counts,
        "complete_separation": separated,
        "before_target_hit_rate": hit_rate,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--meta-root", type=Path, required=True)
    parser.add_argument("--before", required=True, help="Git revision of the pre-rewrite record.")
    parser.add_argument("--after", default="HEAD", help="Git revision of the current record.")
    parser.add_argument("--readers", type=int, default=3)
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--timeout", type=int, default=420)
    args = parser.parse_args()

    root = args.meta_root.resolve()
    out_dir = root / "results" / "reader_discrimination"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for version, revision in (("before", args.before), ("after", args.after)):
        for document in DOCUMENTS:
            text = text_at(root, revision, document)
            if text is None:
                print(f"cannot read {document} at {revision}", file=sys.stderr)
                return 1
            rows.extend(read_version(version, revision, document, text, args))
            # Written incrementally so a killed run keeps every completed row.
            with (out_dir / "runs.jsonl").open("w", encoding="utf-8") as sink:
                for row in rows:
                    sink.write(json.dumps(row) + "\n")
    summary = summarise(rows)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
