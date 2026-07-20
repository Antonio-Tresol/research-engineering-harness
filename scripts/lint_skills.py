#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Lint SKILL.md files against the Agent Skills spec and harness conventions.

Checks each `.claude/skills/*/SKILL.md` for the structural and content rules that
determine whether a skill loads at all and whether the model will trigger it
correctly: valid YAML frontmatter, required fields, name/directory agreement,
kebab-case naming, description quality (third-person, states when to use it),
size budget, no machine-specific absolute paths, and no dangling references.

Exit 0 = clean (warnings allowed); nonzero = at least one error.
Run from the project root:  uv run scripts/lint_skills.py [--strict] [PATH ...]
`--strict` promotes warnings to errors.
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
DEFAULT_SKILL_ROOTS: Final[tuple[str, ...]] = (".claude/skills",)

NAME_RE: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
FRONTMATTER_RE: Final[re.Pattern[str]] = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
ABS_PATH_RE: Final[re.Pattern[str]] = re.compile(r"(/Users/|/home/|C:\\\\|~/(?:Documents|Desktop|Downloads))")
# Divider/art runs, excluding markdown table separators (which contain '|').
ASCII_ART_RE: Final[re.Pattern[str]] = re.compile(r"^[\s+=*_~#-]{20,}$", re.MULTILINE)

# Spec limits. Frontmatter description is the only text always in context, so it
# has a hard budget; the body is loaded on demand and gets a soft one.
MAX_DESCRIPTION_CHARS: Final[int] = 1024
MAX_BODY_LINES: Final[int] = 500
REQUIRED_FIELDS: Final[tuple[str, ...]] = ("name", "description")
KNOWN_FIELDS: Final[frozenset[str]] = frozenset({
    "name", "description", "when_to_use", "effort", "user_invocable",
    "user-invocable", "disable-model-invocation", "allowed-tools", "metadata",
    "license", "version",
})
# Words that signal the description says WHEN to use the skill, not just what it is.
TRIGGER_HINTS: Final[tuple[str, ...]] = ("use when", "use this", "when the user", "trigger", "whenever")


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


def parse_frontmatter(text: str, skill: str, findings: list[Finding]) -> dict[str, object] | None:
    """Extract and parse YAML frontmatter; returns None if unusable."""
    match = FRONTMATTER_RE.match(text)
    if match is None:
        findings.append(Finding(Level.ERROR, skill, "no YAML frontmatter (file must start with '---')"))
        return None
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        findings.append(Finding(Level.ERROR, skill, f"frontmatter is not valid YAML: {exc}"))
        return None
    if not isinstance(data, dict):
        findings.append(Finding(Level.ERROR, skill, "frontmatter must be a YAML mapping"))
        return None
    return data


def check_fields(data: dict[str, object], skill: str, findings: list[Finding]) -> None:
    for field in REQUIRED_FIELDS:
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            findings.append(Finding(Level.ERROR, skill, f"frontmatter missing required field '{field}'"))

    name = data.get("name")
    if isinstance(name, str):
        if not NAME_RE.match(name):
            findings.append(Finding(Level.ERROR, skill, f"name '{name}' is not kebab-case ([a-z0-9] and '-')"))
        if name != skill:
            findings.append(Finding(Level.ERROR, skill, f"name '{name}' does not match directory '{skill}'"))

    description = data.get("description")
    if isinstance(description, str):
        if len(description) > MAX_DESCRIPTION_CHARS:
            findings.append(Finding(
                Level.ERROR, skill,
                f"description is {len(description)} chars (limit {MAX_DESCRIPTION_CHARS}) — it is always in context",
            ))
        lowered = description.lower()
        # Manual-only skills are invoked deliberately, so trigger phrasing is moot.
        manual_only = bool(data.get("disable-model-invocation"))
        if not manual_only and not any(hint in lowered for hint in TRIGGER_HINTS):
            findings.append(Finding(
                Level.WARN, skill,
                "description does not say WHEN to use the skill (no 'use when'/'when the user' phrasing) — hurts triggering",
            ))
        if lowered.startswith(("i ", "you ", "this skill lets you")):
            findings.append(Finding(
                Level.WARN, skill,
                "description should be third-person about the task, not addressed to the reader",
            ))

    for key in data:
        if key not in KNOWN_FIELDS:
            findings.append(Finding(Level.WARN, skill, f"unknown frontmatter field '{key}' (typo?)"))


def check_body(body: str, skill: str, skill_dir: Path, findings: list[Finding]) -> None:
    lines = body.splitlines()
    if len([ln for ln in lines if ln.strip()]) < 5:
        findings.append(Finding(Level.ERROR, skill, "body is essentially empty"))
    if len(lines) > MAX_BODY_LINES:
        findings.append(Finding(
            Level.WARN, skill,
            f"body is {len(lines)} lines (soft limit {MAX_BODY_LINES}) — consider splitting into reference files",
        ))
    for match in ABS_PATH_RE.finditer(body):
        findings.append(Finding(
            Level.ERROR, skill,
            f"machine-specific absolute path near '{match.group(0)}' — skills must be portable",
        ))
    if ASCII_ART_RE.search(body):
        findings.append(Finding(Level.WARN, skill, "possible ASCII art / divider blocks — wastes context tokens"))

    # Files bundled *inside* the skill directory must exist. Skills legitimately
    # reference project-root files (TREE.md, .mcp.json) and external repos, so
    # only sub-paths that look skill-local are checked.
    # A relative path may be bundled in the skill or live at the project root;
    # only warn when it resolves to neither.
    for ref in re.findall(r"`((?:reference|references|scripts|assets|templates)/[\w./-]+)`", body):
        if (skill_dir / ref).exists() or (ROOT / ref).exists():
            continue
        findings.append(Finding(Level.WARN, skill, f"references '{ref}' which exists neither in the skill nor at the project root"))


def lint_skill(skill_dir: Path, findings: list[Finding]) -> None:
    skill = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        findings.append(Finding(Level.ERROR, skill, "directory has no SKILL.md"))
        return
    text = skill_md.read_text(encoding="utf-8")
    data = parse_frontmatter(text, skill, findings)
    if data is None:
        return
    check_fields(data, skill, findings)
    body = FRONTMATTER_RE.sub("", text, count=1)
    check_body(body, skill, skill_dir, findings)


def discover(paths: list[Path]) -> list[Path]:
    """Resolve inputs to a list of skill directories."""
    roots = paths or [ROOT / rel for rel in DEFAULT_SKILL_ROOTS]
    skill_dirs: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        if (root / "SKILL.md").is_file():
            skill_dirs.append(root)
            continue
        skill_dirs.extend(sorted(d for d in root.iterdir() if d.is_dir()))
    return skill_dirs


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint SKILL.md files against the Agent Skills spec.")
    parser.add_argument("paths", nargs="*", type=Path, help="skill dirs or skill roots (default: .claude/skills)")
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = parser.parse_args()

    skill_dirs = discover(args.paths)
    if not skill_dirs:
        print("No skills found.")
        return 1

    findings: list[Finding] = []
    for skill_dir in skill_dirs:
        lint_skill(skill_dir, findings)

    errors = [f for f in findings if f.level is Level.ERROR]
    warnings = [f for f in findings if f.level is Level.WARN]

    if findings:
        print(f"Linted {len(skill_dirs)} skill(s): {len(errors)} error(s), {len(warnings)} warning(s)\n")
        for finding in errors + warnings:
            print(finding.render())
    else:
        print(f"OK — {len(skill_dirs)} skill(s) clean.")

    return 1 if errors or (args.strict and warnings) else 0


if __name__ == "__main__":
    sys.exit(main())
