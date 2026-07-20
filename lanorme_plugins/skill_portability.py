"""HSKILL-001/002/003: harness-specific SKILL.md checks.

Complements lanorme's built-in `skills` check (SKILL-001..006), which owns spec
compliance. These are the harness's own concerns and do not overlap:

    HSKILL-001  no machine-specific absolute path in a skill body. Skills are
                shared between machines and teammates; a `/Users/...` path
                breaks on clone.
    HSKILL-002  the description says WHEN to use the skill, not only what it
                is — descriptions are the only text always in context, and
                vague ones hurt triggering.  [warning]
    HSKILL-003  no unrecognized frontmatter key (typo catcher).  [warning]

Frontmatter is read with a minimal top-level key scanner rather than a YAML
parser, so the check stays dependency-free inside lanorme's environment. Any
frontmatter that will not parse at all is lanorme's SKILL-006, not ours.

Run:
    lanorme check . --check=skill_portability
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from lanorme import CheckResult, Status, Violation, register

from ._common import normalize, scan_tree

ABS_PATH_RE: Final[re.Pattern[str]] = re.compile(
    r"(/Users/|/home/|C:\\\\|~/(?:Documents|Desktop|Downloads))"
)
FRONTMATTER_RE: Final[re.Pattern[str]] = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
TOP_LEVEL_KEY_RE: Final[re.Pattern[str]] = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):")

KNOWN_FIELDS: Final[frozenset[str]] = frozenset({
    "name", "description", "when_to_use", "effort", "user_invocable",
    "user-invocable", "disable-model-invocation", "allowed-tools", "metadata",
    "compatibility", "license", "version",
})
TRIGGER_HINTS: Final[tuple[str, ...]] = (
    "use when", "use this", "when the user", "trigger", "whenever",
)
HSKILL_001: Final[str] = "HSKILL-001: skills contain no machine-specific absolute paths"
HSKILL_002: Final[str] = "HSKILL-002: description states when to use the skill (warning)"
HSKILL_003: Final[str] = "HSKILL-003: frontmatter keys are recognized (warning)"


@dataclass(frozen=True)
class Frontmatter:
    """Top-level keys and the raw text of a skill's frontmatter."""

    keys: tuple[str, ...]
    text: str

    @property
    def is_manual_only(self) -> bool:
        return "disable-model-invocation: true" in self.text.lower()

    def value_of(self, key: str) -> str:
        """Text following `key:` up to the next top-level key. '' when absent."""
        pattern = re.compile(rf"^{re.escape(key)}:(.*?)(?=^[A-Za-z][A-Za-z0-9_-]*:|\Z)", re.DOTALL | re.MULTILINE)
        match = pattern.search(self.text)
        return match.group(1).strip() if match else ""


def parse_frontmatter(text: str) -> Frontmatter | None:
    match = FRONTMATTER_RE.match(text)
    if match is None:
        return None
    body = match.group(1)
    keys = tuple(m.group(1) for m in (TOP_LEVEL_KEY_RE.match(line) for line in body.splitlines()) if m)
    return Frontmatter(keys=keys, text=body)


def check_portability(body: str, file: str) -> list[Violation]:
    found: list[Violation] = []
    for lineno, line in enumerate(body.splitlines(), 1):
        match = ABS_PATH_RE.search(line)
        if match is None:
            continue
        found.append(Violation(
            file=file, line=lineno, rule=HSKILL_001,
            message=f"Machine-specific absolute path near '{match.group(0)}'",
            fix="Move the path to a gitignored CLAUDE.local.md and reference it generically",
        ))
    return found


def check_triggering(frontmatter: Frontmatter, file: str) -> list[Violation]:
    if frontmatter.is_manual_only:
        return []  # manual-only skills are never model-triggered
    # normalize first: a folded block scalar can split "use when" across lines
    description = normalize(frontmatter.value_of("description")).lower()
    if not description or any(hint in description for hint in TRIGGER_HINTS):
        return []
    return [Violation(
        file=file, line=1, rule=HSKILL_002,
        message="Description does not say WHEN to use the skill",
        fix="Add trigger phrasing, e.g. 'Use when ...' or 'Use whenever the user ...'",
    )]


def check_field_names(frontmatter: Frontmatter, file: str) -> list[Violation]:
    return [
        Violation(
            file=file, line=1, rule=HSKILL_003,
            message=f"Unrecognized frontmatter key '{key}'",
            fix=f"Remove it or correct the spelling; known keys: {', '.join(sorted(KNOWN_FIELDS))}",
        )
        for key in frontmatter.keys
        if key not in KNOWN_FIELDS
    ]


@dataclass
class SkillPortabilityCheck:
    """Harness-specific SKILL.md checks that complement lanorme's spec rules."""

    name: str = "skill_portability"
    description: str = "Harness SKILL.md checks: portability, trigger phrasing, frontmatter typos"
    enabled: bool = True
    rules: list[str] = field(
        default_factory=lambda: [
            "HSKILL-001: skills contain no machine-specific absolute paths",
            "HSKILL-002: description states when to use the skill (warning)",
            "HSKILL-003: frontmatter keys are recognized (warning)",
        ]
    )

    def configure(self, *, settings: dict[str, object]) -> None:
        enabled = settings.get("enabled")
        if isinstance(enabled, bool):
            self.enabled = enabled

    def _scan_file(self, path: Path, file: str) -> tuple[list[Violation], list[Violation]]:
        text = path.read_text(encoding="utf-8")
        body = FRONTMATTER_RE.sub("", text, count=1)
        violations = check_portability(body, file)
        frontmatter = parse_frontmatter(text)
        if frontmatter is None:
            return violations, []  # unparseable frontmatter is lanorme's SKILL-006
        warnings = check_triggering(frontmatter, file) + check_field_names(frontmatter, file)
        return violations, warnings

    def run(self, *, src_root: str) -> CheckResult:
        if not self.enabled:
            return CheckResult(check=self.name, status=Status.PASS)
        return scan_tree(name=self.name, src_root=src_root, pattern="SKILL.md", scan=self._scan_file)


register(SkillPortabilityCheck())
