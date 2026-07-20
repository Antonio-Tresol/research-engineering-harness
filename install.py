#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Install the research-harness into a project, filling in placeholders.

The harness lives in this repo (the directory containing this script). This
utility copies the portable parts (skills, validator, templates) into a target
project, renders the template placeholders from the values you pass, seeds the
project layout, and writes a starter gitignored CLAUDE.local.md.

Agent instructions land in AGENTS.md, the cross-tool standard read by Codex,
Cursor, Aider and others. CLAUDE.md is a one-line @import of it, so Claude Code
and every other agent follow the same file.

Idempotent-ish: it refuses to clobber existing project files unless --force is
given, and always prints exactly what it did.

Usage:
    python install.py TARGET_DIR --name "My Project" [options]

Examples:
    # Interactive: prompts for any value not passed on the CLI
    python install.py ~/Documents/ai-safety/new-project

    # Fully specified, non-interactive
    python install.py ~/Documents/ai-safety/new-project \\
        --name "Refusal probe transfer" \\
        --description "Do refusal directions transfer across model families?" \\
        --question "Does the Gemma refusal direction steer Llama refusals?" \\
        --timebox "one week, solo" \\
        --no-input
"""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Final

HARNESS = Path(__file__).resolve().parent

# Files/dirs copied verbatim (portable, no placeholders).
COPY_TREE = [".claude", "scripts", "lanorme_plugins", "hooks"]
# Reference material worth having in every project (read-only evidence base).
COPY_REFERENCE = ["references", "research"]
# Templates rendered with placeholder substitution: (template_src, dest_in_project).
RENDER = [
    ("templates/AGENTS.md", "AGENTS.md"),
    ("templates/TREE.md", "TREE.md"),
    ("templates/RESEARCH_LOG.md", "RESEARCH_LOG.md"),
]
# Copied but renamed, no placeholder rendering.
COPY_AS = [
    ("templates/CLAUDE.md", "CLAUDE.md"),   # one-line @import of AGENTS.md
    ("templates/mcp.json", ".mcp.json"),
    ("templates/lanorme.toml", "lanorme.toml"),
    ("check.sh", "check.sh"),
]
# Directories to create empty.
MKDIRS = ["data/papers", "results", "notes"]

GITIGNORE = "data/papers/\n__pycache__/\n.venv/\n.DS_Store\nCLAUDE.local.md\n"

PLACEHOLDERS = {
    "name": "<PROJECT NAME>",
    "description": "<one-line description>",
    "question": "<the project's research question>",
    "summary_context": (
        "<What this project is, who is working on it, and its timebox if any.>"
    ),
}


def render(text: str, values: dict[str, str]) -> str:
    """Replace the template placeholder strings with provided values.

    Only substitutes placeholders whose value is non-empty, so a partial install
    leaves the remaining <PLACEHOLDERS> visibly unfilled rather than blanking them.
    """
    out = text
    if values.get("name"):
        out = out.replace(PLACEHOLDERS["name"], values["name"])
    if values.get("description"):
        out = out.replace(PLACEHOLDERS["description"], values["description"])
    if values.get("question"):
        out = out.replace(PLACEHOLDERS["question"], values["question"])
    if values.get("summary_context"):
        out = out.replace(PLACEHOLDERS["summary_context"], values["summary_context"])
    return out


def build_context(context: str, name: str, timebox: str) -> str:
    """One-sentence project context: explicit --context wins, else name + timebox."""
    if context:
        return context
    if not (name or timebox):
        return ""
    who = name or "This project"
    suffix = f" Timebox: {timebox}." if timebox else ""
    return f"{who}.{suffix}".strip()


def prompt_missing(values: dict[str, str], allow_input: bool) -> dict[str, str]:
    fields = [
        ("name", "Project name"),
        ("description", "One-line description"),
        ("question", "Q1 research question"),
        ("summary_context", "Context (who/what/timebox; one sentence)"),
    ]
    for key, label in fields:
        if values.get(key):
            continue
        if not allow_input:
            continue
        try:
            answer = input(f"{label}: ").strip()
        except EOFError:
            answer = ""
        if answer:
            values[key] = answer
    return values


LOCAL_POINTERS_TEXT: Final[str] = (
    "# Machine-local pointers (gitignored — keep your own copy)\n\n"
    f"- `{HARNESS}` — canonical home of the research-harness. Improvements\n"
    "  flow harness-first, then re-install here.\n\n"
    "Add local copies of reference material and related repos on this machine below.\n"
)


@dataclass(frozen=True)
class InstallPlan:
    """Everything an install needs, so helpers take one parameter, not five."""

    target: Path
    values: dict[str, str]
    today: str
    force: bool = False
    with_reference: bool = True


class Installer:
    """Performs the install, recording one action line per step."""

    def __init__(self, plan: InstallPlan) -> None:
        self.plan = plan
        self.actions: list[str] = []

    def can_write(self, dest: Path) -> bool:
        """False (and records a SKIP) when dest exists and --force was not given."""
        if dest.exists() and not self.plan.force:
            self.actions.append(f"SKIP (exists, use --force): {dest.relative_to(self.plan.target)}")
            return False
        return True

    def copy_dir(self, rel: str, label: str = "") -> None:
        src, dest = HARNESS / rel, self.plan.target / rel
        if not src.exists() or not self.can_write(dest):
            return
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__"))
        self.actions.append(f"copied {rel}/{label}")

    def copy_file(self, src_rel: str, dest_rel: str) -> None:
        dest = self.plan.target / dest_rel
        if not self.can_write(dest):
            return
        # copy2, not copyfile: the executable bit on check.sh must survive.
        shutil.copy2(HARNESS / src_rel, dest)
        self.actions.append(f"copied {src_rel} -> {dest_rel}")

    def render_file(self, src_rel: str, dest_rel: str) -> None:
        dest = self.plan.target / dest_rel
        if not self.can_write(dest):
            return
        text = render((HARNESS / src_rel).read_text(), self.plan.values)
        if dest_rel == "RESEARCH_LOG.md":
            # Only the seed entry's header gets a real date; the format block
            # above it keeps its literal YYYY-MM-DD as documentation.
            text = text.replace("SEED-DATE", self.plan.today)
        dest.write_text(text)
        self.actions.append(f"rendered {dest_rel}")

    def write_text_file(self, dest_rel: str, content: str) -> None:
        dest = self.plan.target / dest_rel
        if not self.can_write(dest):
            return
        dest.write_text(content)
        self.actions.append(f"wrote {dest_rel}")

    def link_codex_skills(self) -> None:
        """Point .agents/skills at .claude/skills.

        Codex searches `.agents/skills`; Claude Code requires `.claude/skills`.
        A symlink means one set of files serves both, so a skill edited for one
        agent can never drift from the other.
        """
        agents_dir = self.plan.target / ".agents"
        link = agents_dir / "skills"
        if link.is_symlink() or link.exists():
            self.actions.append("SKIP (exists): .agents/skills")
            return
        agents_dir.mkdir(parents=True, exist_ok=True)
        try:
            link.symlink_to(Path("..") / ".claude" / "skills", target_is_directory=True)
        except OSError:
            # Windows without Developer Mode cannot create symlinks. Copy instead
            # and say so: the copy can drift, and HSKILL-004 is what catches it.
            shutil.copytree(self.plan.target / ".claude" / "skills", link)
            self.actions.append(
                "COPIED .agents/skills (symlinks unavailable) — re-copy after editing skills"
            )
            return
        self.actions.append("linked .agents/skills -> ../.claude/skills")

    def make_dirs(self) -> None:
        for rel in MKDIRS:
            directory = self.plan.target / rel
            directory.mkdir(parents=True, exist_ok=True)
            (directory / ".gitkeep").touch()
            self.actions.append(f"mkdir {rel}/")

    def run(self) -> list[str]:
        self.plan.target.mkdir(parents=True, exist_ok=True)
        for rel in COPY_TREE:
            self.copy_dir(rel)
        if self.plan.with_reference:
            for rel in COPY_REFERENCE:
                self.copy_dir(rel, label=" (reference)")
        for src_rel, dest_rel in COPY_AS:
            self.copy_file(src_rel, dest_rel)
        for src_rel, dest_rel in RENDER:
            self.render_file(src_rel, dest_rel)
        self.link_codex_skills()
        self.make_dirs()
        self.write_text_file(".gitignore", GITIGNORE)
        self.write_text_file("CLAUDE.local.md", LOCAL_POINTERS_TEXT)
        return self.actions


def install(plan: InstallPlan) -> list[str]:
    return Installer(plan).run()


def main() -> int:
    p = argparse.ArgumentParser(description="Install the research-harness into a project.")
    p.add_argument("target", type=Path, help="target project directory")
    p.add_argument("--name", default="")
    p.add_argument("--description", default="")
    p.add_argument("--question", default="", help="the Q1 research question")
    p.add_argument("--timebox", default="", help="e.g. 'one week, solo' — folded into project context")
    p.add_argument("--context", default="", help="explicit one-sentence project context (overrides --timebox)")
    p.add_argument("--force", action="store_true", help="overwrite existing project files")
    p.add_argument("--no-reference", action="store_true", help="do not copy references/ and research/")
    p.add_argument("--no-input", action="store_true", help="never prompt; leave unfilled placeholders in place")
    p.add_argument("--today", default="", help="ISO date for the seed log entry (default: system today)")
    args = p.parse_args()

    values = {
        "name": args.name,
        "description": args.description,
        "question": args.question,
        "summary_context": build_context(args.context, args.name, args.timebox),
    }
    values = prompt_missing(values, allow_input=not args.no_input)

    plan = InstallPlan(
        target=args.target,
        values=values,
        today=args.today or date.today().isoformat(),
        force=args.force,
        with_reference=not args.no_reference,
    )
    actions = install(plan)

    print(f"\nInstalled research-harness into {args.target}")
    for a in actions:
        print(f"  {a}")
    unfilled = [ph for k, ph in PLACEHOLDERS.items() if not values.get(k)]
    if unfilled:
        print("\nUnfilled placeholders still in AGENTS.md / TREE.md / RESEARCH_LOG.md:")
        for ph in unfilled:
            print(f"  {ph}")
    print("\nNext:")
    print(f"  cd {args.target} && git init && git add -A && git commit -m 'Scaffold from research-harness'")
    print("  Write your gitignored CLAUDE.local.md pointers, then start on Q1.")
    print("  Verify: uv run scripts/validate_research.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
