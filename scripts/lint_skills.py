#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Harness-specific SKILL.md checks that complement lanorme.

lanorme (`uvx lanorme check .`) already enforces Agent Skills spec compliance:
SKILL-001 name/directory agreement, SKILL-002 description length, SKILL-003
optional fields, SKILL-004 body size, SKILL-005 relative links, SKILL-006
frontmatter parses. Run it first — it is the spec authority.

This script covers only what the harness needs on top of the spec:

  PORTABILITY  no machine-specific absolute paths (skills are shared between
               machines and teammates; a `/Users/...` path breaks on clone)
  TRIGGERING   the description says WHEN to use the skill, not just what it is
  TYPOS        no unrecognized frontmatter fields

Exit 0 = clean (warnings allowed); nonzero = at least one error.
Run from the project root:  uv run scripts/lint_skills.py [--strict] [PATH ...]
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Final

import yaml

ROOT: Final[Path] = Path(__file__).resolve().parent.parent
DEFAULT_SKILL_ROOT: Final[str] = ".claude/skills"

FRONTMATTER_RE: Final[re.Pattern[str]] = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
ABS_PATH_RE: Final[re.Pattern[str]] = re.compile(
    r"(/Users/|/home/|C:\\\\|~/(?:Documents|Desktop|Downloads))"
)

KNOWN_FIELDS: Final[frozenset[str]] = frozenset({
    "name", "description", "when_to_use", "effort", "user_invocable",
    "user-invocable", "disable-model-invocation", "allowed-tools", "metadata",
    "compatibility", "license", "version",
})
# Phrases that signal the description states WHEN to use the skill.
TRIGGER_HINTS: Final[tuple[str, ...]] = (
    "use when", "use this", "when the user", "trigger", "whenever",
)


class Level(str, Enum):
    ERROR = "ERROR"
    WARN = "WARN"


@dataclass(frozen=True)
class Finding:
    level: Level
    skill: str
    message: str

    def render(self) -> str:
        return f"  [{self.level.value:5}] {self.skill}: {self.message}"


def load_frontmatter(text: str) -> dict[str, object] | None:
    """Parsed frontmatter mapping, or None when absent/unparseable.

    Spec violations here are lanorme's SKILL-006; this script stays quiet about
    them and simply skips the frontmatter-dependent checks.
    """
    match = FRONTMATTER_RE.match(text)
    if match is None:
        return None
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def check_portability(body: str, skill: str, findings: list[Finding]) -> None:
    for match in ABS_PATH_RE.finditer(body):
        findings.append(Finding(
            Level.ERROR, skill,
            f"machine-specific absolute path near '{match.group(0)}' — skills must be portable",
        ))


def check_triggering(data: dict[str, object], skill: str, findings: list[Finding]) -> None:
    description = data.get("description")
    if not isinstance(description, str):
        return  # lanorme SKILL-002 owns missing/invalid descriptions
    if data.get("disable-model-invocation"):
        return  # manual-only skills are never model-triggered
    if not any(hint in description.lower() for hint in TRIGGER_HINTS):
        findings.append(Finding(
            Level.WARN, skill,
            "description does not say WHEN to use the skill "
            "(no 'use when'/'when the user' phrasing) — hurts triggering",
        ))


def check_field_names(data: dict[str, object], skill: str, findings: list[Finding]) -> None:
    for key in data:
        if key not in KNOWN_FIELDS:
            findings.append(Finding(Level.WARN, skill, f"unknown frontmatter field '{key}' (typo?)"))


def lint_skill(skill_dir: Path, findings: list[Finding]) -> None:
    skill = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        findings.append(Finding(Level.ERROR, skill, "directory has no SKILL.md"))
        return
    text = skill_md.read_text(encoding="utf-8")
    check_portability(FRONTMATTER_RE.sub("", text, count=1), skill, findings)
    data = load_frontmatter(text)
    if data is None:
        findings.append(Finding(
            Level.WARN, skill,
            "frontmatter missing or unparseable — run `uvx lanorme check .` (SKILL-006) for detail",
        ))
        return
    check_triggering(data, skill, findings)
    check_field_names(data, skill, findings)


def discover(paths: list[Path]) -> list[Path]:
    """Resolve inputs to a list of skill directories."""
    roots = paths or [ROOT / DEFAULT_SKILL_ROOT]
    skill_dirs: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        if (root / "SKILL.md").is_file():
            skill_dirs.append(root)
        else:
            skill_dirs.extend(sorted(d for d in root.iterdir() if d.is_dir()))
    return skill_dirs


def report(findings: list[Finding], skill_count: int, strict: bool) -> int:
    errors = [f for f in findings if f.level is Level.ERROR]
    warnings = [f for f in findings if f.level is Level.WARN]
    if findings:
        print(f"Linted {skill_count} skill(s): {len(errors)} error(s), {len(warnings)} warning(s)\n")
        for finding in errors + warnings:
            print(finding.render())
    else:
        print(f"OK — {skill_count} skill(s) clean (harness checks; run lanorme for spec compliance).")
    return 1 if errors or (strict and warnings) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*", type=Path, help=f"skill dirs or roots (default: {DEFAULT_SKILL_ROOT})")
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = parser.parse_args()

    skill_dirs = discover(args.paths)
    if not skill_dirs:
        print("No skills found.")
        return 1
    findings: list[Finding] = []
    for skill_dir in skill_dirs:
        lint_skill(skill_dir, findings)
    return report(findings, len(skill_dirs), args.strict)


if __name__ == "__main__":
    sys.exit(main())
