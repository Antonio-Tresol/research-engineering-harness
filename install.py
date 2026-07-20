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
from datetime import date
from pathlib import Path

HARNESS = Path(__file__).resolve().parent

# Files/dirs copied verbatim (portable, no placeholders).
COPY_TREE = [".claude", "scripts"]
# Reference material worth having in every project (read-only evidence base).
COPY_REFERENCE = ["references", "research"]
# Templates rendered with placeholder substitution: (template_src, dest_in_project).
RENDER = [
    ("templates/CLAUDE.md", "CLAUDE.md"),
    ("templates/TREE.md", "TREE.md"),
    ("templates/RESEARCH_LOG.md", "RESEARCH_LOG.md"),
]
# Copied but renamed, no placeholder rendering.
COPY_AS = [("templates/mcp.json", ".mcp.json")]
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


def install(target: Path, values: dict[str, str], force: bool,
            with_reference: bool, today: str) -> list[str]:
    actions: list[str] = []
    target.mkdir(parents=True, exist_ok=True)

    def guard(dest: Path) -> bool:
        if dest.exists() and not force:
            actions.append(f"SKIP (exists, use --force): {dest.relative_to(target)}")
            return False
        return True

    for rel in COPY_TREE:
        src, dest = HARNESS / rel, target / rel
        if not guard(dest):
            continue
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__"))
        actions.append(f"copied {rel}/")

    if with_reference:
        for rel in COPY_REFERENCE:
            src, dest = HARNESS / rel, target / rel
            if not src.exists() or not guard(dest):
                continue
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
            actions.append(f"copied {rel}/ (reference)")

    for src_rel, dest_rel in COPY_AS:
        dest = target / dest_rel
        if not guard(dest):
            continue
        shutil.copyfile(HARNESS / src_rel, dest)
        actions.append(f"copied {src_rel} -> {dest_rel}")

    for src_rel, dest_rel in RENDER:
        dest = target / dest_rel
        if not guard(dest):
            continue
        text = (HARNESS / src_rel).read_text()
        text = render(text, values)
        if dest_rel == "RESEARCH_LOG.md":
            # Only the seed entry's header gets a real date; the format block
            # above it keeps its literal YYYY-MM-DD as documentation.
            text = text.replace("SEED-DATE", today)
        dest.write_text(text)
        actions.append(f"rendered {dest_rel}")

    for rel in MKDIRS:
        d = target / rel
        d.mkdir(parents=True, exist_ok=True)
        (d / ".gitkeep").touch()
        actions.append(f"mkdir {rel}/")

    gi = target / ".gitignore"
    if gi.exists() and not force:
        actions.append("SKIP (exists, use --force): .gitignore")
    else:
        gi.write_text(GITIGNORE)
        actions.append("wrote .gitignore")

    local = target / "CLAUDE.local.md"
    if local.exists() and not force:
        actions.append("SKIP (exists, use --force): CLAUDE.local.md")
    else:
        local.write_text(
            "# Machine-local pointers (gitignored — keep your own copy)\n\n"
            f"- `{HARNESS}` — canonical home of the research-harness. Improvements\n"
            "  flow harness-first, then re-install here.\n\n"
            "Add local copies of reference material and related repos on this machine below.\n"
        )
        actions.append("wrote CLAUDE.local.md")

    return actions


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
    }
    if args.context:
        values["summary_context"] = args.context
    elif args.name or args.timebox:
        who = args.name or "This project"
        tb = f" Timebox: {args.timebox}." if args.timebox else ""
        values["summary_context"] = f"{who}.{tb}".strip()
    else:
        values["summary_context"] = ""

    values = prompt_missing(values, allow_input=not args.no_input)

    today = args.today or date.today().isoformat()
    actions = install(args.target, values, force=args.force,
                      with_reference=not args.no_reference, today=today)

    print(f"\nInstalled research-harness into {args.target}")
    for a in actions:
        print(f"  {a}")
    unfilled = [ph for k, ph in PLACEHOLDERS.items() if not values.get(k)]
    if unfilled:
        print("\nUnfilled placeholders still in CLAUDE.md / TREE.md / RESEARCH_LOG.md:")
        for ph in unfilled:
            print(f"  {ph}")
    print("\nNext:")
    print(f"  cd {args.target} && git init && git add -A && git commit -m 'Scaffold from research-harness'")
    print("  Write your gitignored CLAUDE.local.md pointers, then start on Q1.")
    print("  Verify: python scripts/validate_research.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
