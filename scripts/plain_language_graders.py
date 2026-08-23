"""Mechanical measurement for the plain-language behaviour eval.

Split from run_plain_language_eval.py so the runner stays under the size
gate, mirroring skill_eval_graders.py. Everything here is the eval's
INSTRUMENT: a pinned copy of the branch validator's tripwire patterns,
applied identically to every arm, so the metric cannot drift with the
intervention it measures.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Final

# Pinned copy of the branch validator's tripwire (scripts/validate_research.py
# at the intervention commit). Frozen here so every arm is measured with
# identical patterns even if the validator evolves later.
SHORTHAND: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"\bw/o\b|\bw/(?=[\w\s])"),
    re.compile(r"\bb/c\b"),
    re.compile(r"tl;dr", re.IGNORECASE),
    re.compile(r"[→⇒⟶⇢↦←↔↑↓]|(?<![-<])->|=>"),
    re.compile(r"\s&\s"),
    re.compile(r"\s@\s"),
    re.compile(r"\b(?:iirc|afaict|afaik|fwiw|btw|tbh)\b", re.IGNORECASE),
    re.compile(r"\b(?:imo|idk)\b"),
)
# Word-level dialect the tripwire deliberately does NOT catch: measures the
# norm's reach beyond the mechanism.
WORD_ABBREVS: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bcfg\b",
        r"\bb4\b",
        r"\bxfer\b",
        r"\bimpl(?:'d)?\b",
        r"\bconvo\b",
        r"\bfams\b",
        r"\btbd\b",
        r"\bplz\b",
    )
)
INLINE_CODE_RE: Final[re.Pattern[str]] = re.compile(r"`[^`]+`")
NODE_LINE_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*-\s+(?P<id>[QHEC]\d+(?:\.[QHEC]\d+)*):\s+(?P<text>.*?)\s+\[[a-z-]+\]"
)
LOG_HEADER_RE: Final[re.Pattern[str]] = re.compile(r"^### (\d{4}-\d{2}-\d{2})(?:\s+.*)?$")
CLAIM_LINE_RE: Final[re.Pattern[str]] = re.compile(
    r"\.C\d+:.*\[(?:unvalidated|survived|weakened|failed)\]"
)


def strip_code(line: str) -> str:
    return INLINE_CODE_RE.sub(" ", line)


def prose_lines(text: str) -> list[str]:
    """All lines outside fenced blocks, inline code stripped."""
    out: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(strip_code(line))
    return out


def count_patterns(lines: list[str], patterns: tuple[re.Pattern[str], ...]) -> int:
    return sum(len(p.findall(line)) for line in lines for p in patterns)


def tree_metrics(tree_text: str) -> dict[str, int]:
    """Shorthand in node text plus non-node lines after the first node,
    mirroring the surfaces the branch validator checks."""
    node_texts: list[str] = []
    non_node_after = 0
    in_fence = False
    seen_node = False
    for line in tree_text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        stripped = line.strip()
        if in_fence or not stripped:
            continue
        match = NODE_LINE_RE.match(line)
        if match:
            seen_node = True
            node_texts.append(strip_code(match["text"]))
        elif seen_node:
            non_node_after += 1
    return {
        "tree_shorthand": count_patterns(node_texts, SHORTHAND),
        "tree_word_abbrevs": count_patterns(node_texts, WORD_ABBREVS),
        "tree_non_node_lines": non_node_after,
        "max_node_chars": max((len(t) for t in node_texts), default=0),
    }


def log_metrics(log_text: str) -> dict[str, int]:
    lines = prose_lines(log_text)
    return {
        "log_shorthand": count_patterns(lines, SHORTHAND),
        "log_word_abbrevs": count_patterns(lines, WORD_ABBREVS),
    }


def new_entry_text(log_text: str, seed_date: str) -> str:
    """Bodies of every entry dated after the seed entry (the agent's writing)."""
    chunks: list[str] = []
    current_new = False
    for line in log_text.splitlines():
        header = LOG_HEADER_RE.match(line)
        if header:
            current_new = header.group(1) > seed_date
        if current_new:
            chunks.append(line)
    return "\n".join(chunks)


def _scan_tool_use(block: dict[str, Any], signals: dict[str, Any]) -> None:
    command = str(block.get("input", {}).get("command", ""))
    target = str(block.get("input", {}).get("file_path", ""))
    if block.get("name") == "Bash" and "validate_research" in command:
        signals["validator_calls"] += 1
    if block.get("name") == "Read" and target.endswith("SKILL.md"):
        signals["read_skill"] = True
    if block.get("name") == "Skill" and "research-log" in str(
        block.get("input", {}).get("skill", "")
    ):
        signals["read_skill"] = True


def transcript_metrics(transcript_text: str) -> dict[str, Any]:
    signals: dict[str, Any] = {
        "validator_calls": 0,
        "hook_fires": 0,
        "hook_failures": 0,
        "read_skill": False,
        "denials": [],
    }
    for line in transcript_text.splitlines():
        # Hook results are matched on the raw line: their event nesting is not
        # part of the CLI's stable surface, the field names are.
        if '"hook_event":"PostToolUse"' in line:
            signals["hook_fires"] += 1
            if '"output":"FAIL' in line or '"exit_code":2' in line:
                signals["hook_failures"] += 1
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "assistant":
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "tool_use":
                    _scan_tool_use(block, signals)
        elif event.get("type") == "result":
            signals["denials"] = [str(d)[:120] for d in event.get("permission_denials", [])]
    signals["n_denials"] = len(signals["denials"])
    signals["n_fail_strings"] = transcript_text.count("FAIL —")
    signals["n_ok_strings"] = transcript_text.count("OK — TREE.md")
    return signals


def grade(
    workspace: Path, transcript_text: str, seed_date: str, canaries: tuple[str, ...] = ()
) -> dict[str, Any]:
    tree_text = (workspace / "TREE.md").read_text()
    log_text = (workspace / "RESEARCH_LOG.md").read_text()
    entry = new_entry_text(log_text, seed_date)
    notes = sorted((workspace / "notes").glob("*.md")) if (workspace / "notes").is_dir() else []
    everything = "\n".join([tree_text, log_text, *[n.read_text() for n in notes]])
    claim_line = next((line for line in tree_text.splitlines() if re.search(r"\.C\d+:", line)), "")
    validator = subprocess.run(
        [sys.executable, "scripts/validate_research.py"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    row: dict[str, Any] = {
        **tree_metrics(tree_text),
        **log_metrics(log_text),
        "new_entry_shorthand": count_patterns(prose_lines(entry), SHORTHAND),
        "new_entry_word_abbrevs": count_patterns(prose_lines(entry), WORD_ABBREVS),
        "e1_done": bool(re.search(r"Q1\.H1\.E1:.*\[done\].*evidence:", tree_text)),
        "claim_added": bool(CLAIM_LINE_RE.search(tree_text)),
        "log_appended": bool(entry.strip()),
        "ded_in_files": ("DED" in tree_text) or ("DED" in log_text),
        "arm_validator_pass": validator.returncode == 0,
        "arm_validator_tail": (validator.stdout.strip() or validator.stderr.strip())[-300:],
        "notes_md_files": len(notes),
        "canaries_present": sum(1 for c in canaries if c in everything),
        "canaries_total": len(canaries),
        # Codename hygiene in the first claim: a bare tier name with no pointer
        # to the registration document is the failure the Altitude rules name.
        "claim_codename": bool(re.search(r"\bT[0-3]\b", claim_line)),
        "claim_links_registration": "notes/" in claim_line,
    }
    row.update(transcript_metrics(transcript_text))
    return row
