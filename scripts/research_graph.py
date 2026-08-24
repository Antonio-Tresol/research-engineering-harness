#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Interfaces layer: the command-line entry point agents and humans use to
navigate, verify, and extend the research record as a typed graph.

Presentation only: every handler calls research_graph_model (domain model and
loader), research_graph_checks (read-only checks), or research_graph_write
(validated writes), then formats the result. Every command is declared once
in COMMAND_REGISTRY — name, one-sentence help, arguments, handler — and both
argparse's subparsers and the agent-facing `help` command are generated from
it, so the documented commands and the runnable commands can never drift
apart.

Run: uv run scripts/research_graph.py <command>. For an agent-oriented guide
assuming no prior context, run: uv run scripts/research_graph.py help"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final

import research_graph_checks as checks
import research_graph_model as model
import research_graph_write as write
from research_graph_model import INVALID as EXIT_INVALID
from research_graph_model import OK as EXIT_OK
from research_graph_model import USAGE as EXIT_USAGE

NODE_TYPES: Final[tuple[str, ...]] = ("question", "hypothesis", "experiment", "claim")
LINE_WIDTH: Final[int] = 80

# Curated recipes for the `help` command: exact command lines under task
# headings, kept separate from COMMAND_REGISTRY since a recipe is a workflow.
RECIPES: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    (
        "Start of session",
        (
            "uv run scripts/research_graph.py tree",
            "uv run scripts/research_graph.py show Q1",
        ),
    ),
    (
        "Record an experiment result",
        (
            "uv run scripts/research_graph.py set-status Q1.H1.E1 done "
            "--evidence results/run1.jsonl",
            'uv run scripts/research_graph.py add claim "<one falsifiable sentence>" '
            "--parent Q1.H1.E1",
            'uv run scripts/research_graph.py log --did "<did>" --expected "<expected>" '
            '--changes "<changes>" --next "<next>"',
        ),
    ),
    (
        "Graduate a claim",
        (
            "uv run scripts/research_graph.py pin Q1.H1.E1.C1",
            "uv run scripts/research_graph.py set-status Q1.H1.E1.C1 survived "
            "--evidence results/falsify_scorecard.json",
        ),
    ),
    (
        "After a compaction or with no context, run",
        (
            "uv run scripts/research_graph.py tree",
            "uv run scripts/research_graph.py verify",
        ),
    ),
)

Arg = tuple[tuple[str, ...], dict[str, object]]


def arg(*flags: str, **kwargs: object) -> Arg:
    """Build one argparse argument declaration for a COMMAND_REGISTRY entry."""
    return flags, kwargs


@dataclass(frozen=True)
class CommandSpec:
    """One CLI command: its name, one-sentence help, arguments, and handler."""

    name: str
    help: str
    args: tuple[Arg, ...]
    handler: Callable[[argparse.Namespace], int]


# Shared formatting and lookup helpers, used by more than one handler below.


def _default_root() -> Path:
    """The repository root two levels above this script, matching validate_research.py."""
    return Path(__file__).resolve().parent.parent


def _truncate(text: str, width: int = LINE_WIDTH) -> str:
    """Collapse whitespace and shorten text to width characters for a scannable line."""
    flat = " ".join(text.split())
    return flat if len(flat) <= width else flat[: width - 3] + "..."


def _excerpt(text: str, term: str, width: int = LINE_WIDTH) -> str:
    """A short window of text centred on the first case-insensitive hit of term."""
    flat = " ".join(text.split())
    idx = flat.lower().find(term.lower())
    if idx == -1:
        return _truncate(flat, width)
    start = max(0, idx - width // 2)
    end = min(len(flat), start + width)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(flat) else ""
    return f"{prefix}{flat[start:end]}{suffix}"


def _node_line(node: model.GraphNode, indent: int = 0) -> str:
    """One line matching TREE.md's own grammar: '<id>: <text> [<status>]'."""
    return f"{'  ' * indent}{node.node_id}: {_truncate(node.text)} [{node.status}]"


def _sorted_nodes(graph: model.Graph) -> list[model.GraphNode]:
    """Nodes in the order they appear in TREE.md, the order agents expect to read them."""
    return sorted(graph.nodes.values(), key=lambda n: n.lineno)


def _require_node(graph: model.Graph, node_id: str) -> model.GraphNode | None:
    """Look up node_id, printing a plain-language error if it is not in the record."""
    node = graph.nodes.get(node_id)
    if node is None:
        print(
            f"Error: no node with id {node_id!r} in the record. "
            "Run 'tree' to see the ids that exist.",
            file=sys.stderr,
        )
    return node


def _pin_and_drift(root: Path, graph: model.Graph) -> tuple[set[str], set[str]]:
    """Evidence paths covered by a provenance pin, and which of those drifted.

    An unpinned path was never drift-checked, so callers report it as "not
    pinned", never as "no drift" — those are different claims."""
    pinned: set[str] = set()
    for provenance in checks.read_pins(root, graph).values():
        pinned.update(provenance.get("evidence_sha256", {}))
    findings = checks.drift_report(root, graph)
    drifted = {path for path in pinned if any(path in finding for finding in findings)}
    return pinned, drifted


def _evidence_rows(
    nodes: list[model.GraphNode], graph: model.Graph, pinned: set[str], drifted: set[str]
) -> list[tuple[str, ...]]:
    """(node id, path, kind, exists, pinned, drifted) for every evidence path on nodes."""
    rows: list[tuple[str, ...]] = []
    for node in nodes:
        for path in node.evidence:
            artifact = graph.artifacts[path]
            is_pinned = path in pinned
            drift = "n/a" if not is_pinned else ("yes" if path in drifted else "no")
            exists = "yes" if artifact.exists else "no"
            pin = "yes" if is_pinned else "no"
            rows.append((node.node_id, path, artifact.kind, exists, pin, drift))
    return rows


def _print_table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> None:
    """Print a header row then one '|'-separated row per data row."""
    print(" | ".join(headers))
    for row in rows:
        print(" | ".join(row))


# Navigation commands: implemented directly against the loaded graph.


def cmd_tree(args: argparse.Namespace) -> int:
    graph = model.load(args.root)
    nodes = _sorted_nodes(graph)
    if args.type:
        nodes = [n for n in nodes if n.node_type == args.type]
    if args.status:
        nodes = [n for n in nodes if n.status == args.status]
    if args.under:
        nodes = [
            n for n in nodes if n.node_id == args.under or n.node_id.startswith(args.under + ".")
        ]
    if not nodes:
        print("No nodes match those filters.")
        return EXIT_OK
    for node in nodes:
        print(_node_line(node, indent=node.node_id.count(".")))
    return EXIT_OK


def cmd_show(args: argparse.Namespace) -> int:
    graph = model.load(args.root)
    node = _require_node(graph, args.id)
    if node is None:
        return EXIT_USAGE
    print(f"{node.node_id} ({node.node_type})")
    print(f"  status: {node.status}")
    print(f"  text: {node.text}")
    print(f"  parent: {node.parent or '(none - top-level question)'}")
    print(f"  children: {', '.join(node.children) or '(none)'}")
    print(f"  log: {node.log_date or '(none)'}")
    pinned, drifted = _pin_and_drift(args.root, graph)
    rows = _evidence_rows([node], graph, pinned, drifted)
    print("Evidence:")
    if not rows:
        print("  none recorded.")
    for _, path, kind, exists, pin, drift in rows:
        print(f"  {path}  kind={kind} exists={exists} pinned={pin} drifted={drift}")
    log_hits = sorted(d for d, e in graph.entries.items() if node.node_id in e.mentions_ids)
    print(f"Mentioned in log entries: {', '.join(log_hits) or '(none)'}")
    doc_hits = sorted(
        p
        for p, d in graph.documents.items()
        if node.node_id in d.linked_from or node.node_id in d.mentions_ids
    )
    print(f"Mentioned in documents: {', '.join(doc_hits) or '(none)'}")
    return EXIT_OK


def cmd_path(args: argparse.Namespace) -> int:
    graph = model.load(args.root)
    node = _require_node(graph, args.id)
    if node is None:
        return EXIT_USAGE
    chain = [node]
    while chain[-1].parent is not None:
        parent = graph.nodes.get(chain[-1].parent)
        if parent is None:
            break
        chain.append(parent)
    for step in reversed(chain):
        print(_node_line(step))
    return EXIT_OK


def cmd_search(args: argparse.Namespace) -> int:
    graph = model.load(args.root)
    term = args.term
    hits = 0
    for node in _sorted_nodes(graph):
        if term.lower() in node.text.lower():
            print(f"node {node.node_id}: {_excerpt(node.text, term)}")
            hits += 1
    for date in sorted(graph.entries, reverse=True):
        entry = graph.entries[date]
        if term.lower() in entry.body.lower():
            print(f"log {date}: {_excerpt(entry.body, term)}")
            hits += 1
    for path in sorted(graph.documents):
        doc = graph.documents[path]
        if term.lower() in doc.title.lower() or term.lower() in path.lower():
            print(f"document {path}: {doc.title}")
            hits += 1
    if hits == 0:
        print(f"No hits for {term!r}.")
    return EXIT_OK


def cmd_evidence(args: argparse.Namespace) -> int:
    graph = model.load(args.root)
    if args.id:
        node = _require_node(graph, args.id)
        if node is None:
            return EXIT_USAGE
        nodes = [node]
    else:
        nodes = _sorted_nodes(graph)
    if args.graduated:
        nodes = [n for n in nodes if n.status in checks.GRADUATED]
    pinned, drifted = _pin_and_drift(args.root, graph)
    rows = _evidence_rows(nodes, graph, pinned, drifted)
    if not rows:
        print("No evidence found for that selection.")
        return EXIT_OK
    _print_table(("node", "path", "kind", "exists", "pinned", "drifted"), rows)
    return EXIT_OK


def cmd_orphans(args: argparse.Namespace) -> int:
    graph = model.load(args.root)
    findings = checks.orphan_report(graph)
    if not findings:
        print("No orphan documents found.")
        return EXIT_OK
    for finding in findings:
        print(finding)
    return EXIT_OK


def cmd_json(args: argparse.Namespace) -> int:
    graph = model.load(args.root)
    text = json.dumps(model.to_ir(graph), indent=2)
    if args.out:
        args.out.write_text(text + "\n")
        print(f"Wrote the JSON IR to {args.out}.")
    else:
        print(text)
    return EXIT_OK


def cmd_mermaid(args: argparse.Namespace) -> int:
    graph = model.load(args.root)
    text = model.to_mermaid(graph, with_evidence=args.evidence)
    if args.out:
        args.out.write_text(text + "\n")
        print(f"Wrote the Mermaid diagram to {args.out}.")
    else:
        print(text)
    return EXIT_OK


# Checks dispatch: thin wrappers over research_graph_checks.


def cmd_verify(args: argparse.Namespace) -> int:
    return checks.verify(args.root)


def cmd_pin(args: argparse.Namespace) -> int:
    result = checks.compute_pin(args.root, args.ids)
    print(json.dumps(result, indent=2))
    print(
        'Embed this dict under the "provenance" key of the scorecard evidence file '
        "you are about to write for these claims."
    )
    return EXIT_OK


# Write dispatch: thin wrappers over research_graph_write. Every write command
# follows the same transaction contract inside that module, so these handlers
# only translate parsed arguments into one call and return its exit code — no
# formatting or validation logic belongs here.


def cmd_add(args: argparse.Namespace) -> int:
    return write.add_node(
        args.root,
        args.parent,
        args.type,
        args.text,
        args.status,
        args.evidence or [],
        dry_run=args.dry_run,
    )


def cmd_add_evidence(args: argparse.Namespace) -> int:
    return write.add_evidence(args.root, args.id, args.paths, dry_run=args.dry_run)


def cmd_set_status(args: argparse.Namespace) -> int:
    return write.set_status(
        args.root, args.id, args.status, args.evidence or [], args.log_date, dry_run=args.dry_run
    )


def cmd_log(args: argparse.Namespace) -> int:
    return write.append_log_entry(
        args.root,
        args.date,
        args.did,
        args.expected,
        args.changes,
        args.next,
        dry_run=args.dry_run,
    )


def cmd_add_note(args: argparse.Namespace) -> int:
    return write.add_note(
        args.root, args.slug, args.title, args.body, args.link, dry_run=args.dry_run
    )


def cmd_help(args: argparse.Namespace) -> int:
    print("Commands:")
    for spec in COMMAND_REGISTRY:
        print(f"  {spec.name:<14} {spec.help}")
    print()
    print("Add --dry-run to any write command to preview its exact output before committing.")
    print()
    print("Recipes for common agent workflows, as exact command lines:")
    for heading, lines in RECIPES:
        print(f"\n{heading}:")
        for line in lines:
            print(f"  {line}")
    return EXIT_OK


# The command registry: the single source every subparser and the help text
# below are generated from. DRY_RUN is shared by every write command so the
# flag's wording never drifts between them.
DRY_RUN: Final[Arg] = arg(
    "--dry-run", action="store_true", help="Preview the exact change; write nothing."
)

COMMAND_REGISTRY: Final[tuple[CommandSpec, ...]] = (
    CommandSpec(
        "tree",
        "Print the tree as an indented outline: id, status, and text truncated to 80 characters.",
        (
            arg("--type", choices=NODE_TYPES, help="Only show nodes of this type."),
            arg("--status", help="Only show nodes with exactly this status."),
            arg("--under", help="Only show this node id and its descendants."),
        ),
        cmd_tree,
    ),
    CommandSpec(
        "show",
        "Print every field for one node, its evidence, and what mentions it in the log and notes.",
        (arg("id", help="The node id to show, for example Q1.H1.E2."),),
        cmd_show,
    ),
    CommandSpec(
        "path",
        "Print the chain from the root question down to one node, one line each.",
        (arg("id", help="The node id whose ancestor chain to print."),),
        cmd_path,
    ),
    CommandSpec(
        "search",
        "Search node text, log entries, and document titles and paths for a term, and show "
        "each hit.",
        (arg("term", help="The text to search for, case-insensitively."),),
        cmd_search,
    ),
    CommandSpec(
        "evidence",
        "Print an evidence table: path, kind, whether it exists, and whether it is pinned "
        "and drifted.",
        (
            arg("id", nargs="?", help="Only this node's evidence. Omit for every node's."),
            arg(
                "--graduated",
                action="store_true",
                help="Limit to graduated claims (survived, weakened, or failed).",
            ),
        ),
        cmd_evidence,
    ),
    CommandSpec(
        "orphans",
        "Print notes files that no node evidence links and no tree or log text mentions.",
        (),
        cmd_orphans,
    ),
    CommandSpec(
        "json",
        "Print the record as the versioned JSON graph, or write it to a file.",
        (arg("--out", type=Path, help="Write to this file instead of standard output."),),
        cmd_json,
    ),
    CommandSpec(
        "mermaid",
        "Print the record as a Mermaid flowchart, or write it to a file.",
        (
            arg("--evidence", action="store_true", help="Add edges to each node's evidence."),
            arg("--out", type=Path, help="Write to this file instead of standard output."),
        ),
        cmd_mermaid,
    ),
    CommandSpec(
        "verify",
        "Run every integrity check and report pass or fail: grammar, evidence, drift, orphans.",
        (),
        cmd_verify,
    ),
    CommandSpec(
        "pin",
        "Compute a provenance pin (commit, date, evidence hashes) to embed in a scorecard.",
        (arg("ids", nargs="+", help="One or more claim ids, for example Q1.H1.E1.C1."),),
        cmd_pin,
    ),
    CommandSpec(
        "add",
        "Add a question, hypothesis, experiment, or claim node under a parent, with the "
        "next free id.",
        (
            arg("type", choices=NODE_TYPES, help="The kind of node to add."),
            arg("text", help="The node's headline text, under 1,200 characters."),
            arg("--parent", help="The parent node's id. Required unless type is question."),
            arg("--status", help="Initial status. Omit to take the type's default."),
            arg("--evidence", nargs="+", help="Evidence paths to attach immediately."),
            DRY_RUN,
        ),
        cmd_add,
    ),
    CommandSpec(
        "add-evidence",
        "Attach one or more evidence paths to an existing node.",
        (
            arg("id", help="The node id to attach evidence to."),
            arg("paths", nargs="+", help="One or more repo-relative evidence paths."),
            DRY_RUN,
        ),
        cmd_add_evidence,
    ),
    CommandSpec(
        "set-status",
        "Change a node's status, optionally attaching evidence and a log date in the same edit.",
        (
            arg("id", help="The node id to change."),
            arg("status", help="The new status, from the vocabulary for that node's type."),
            arg("--evidence", nargs="+", help="Evidence paths to attach with the status change."),
            arg("--log-date", help="A RESEARCH_LOG.md date (YYYY-MM-DD) explaining this change."),
            DRY_RUN,
        ),
        cmd_set_status,
    ),
    CommandSpec(
        "log",
        "Append today's (or a given date's) log entry, merging into an existing entry for "
        "that date.",
        (
            arg("--date", help="YYYY-MM-DD. Defaults to today; must not predate the newest entry."),
            arg("--did", required=True, help="What I did."),
            arg("--expected", required=True, help="What I expected versus what happened."),
            arg("--changes", required=True, help="What this changes about my thinking."),
            arg("--next", required=True, help="What I will do next."),
            DRY_RUN,
        ),
        cmd_log,
    ),
    CommandSpec(
        "add-note",
        "Create a dated document under notes/, optionally linking it as evidence on a node.",
        (
            arg("slug", help="Filename stem: creates notes/<slug>.md."),
            arg("title", help="The document's title heading."),
            arg("body", help="The document's body text."),
            arg("--link", help="A node id to attach this note's path to as evidence."),
            DRY_RUN,
        ),
        cmd_add_note,
    ),
    CommandSpec(
        "help",
        "Print every command's one-line help plus curated recipes for common agent workflows.",
        (),
        cmd_help,
    ),
)


def build_parser() -> argparse.ArgumentParser:
    """Build the full CLI from COMMAND_REGISTRY, so every command is documented once."""
    parser = argparse.ArgumentParser(
        prog="research_graph.py",
        description="Navigate, verify, and extend the research record as a typed graph. "
        "Run 'research_graph.py help' for an agent-oriented guide with recipes.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=_default_root(),
        help="Path to the project root containing TREE.md and RESEARCH_LOG.md. Defaults to "
        "the repository root two levels above this script, the same convention "
        "validate_research.py uses.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True, metavar="command")
    for spec in COMMAND_REGISTRY:
        sub = subparsers.add_parser(spec.name, help=spec.help, description=spec.help)
        for flags, kwargs in spec.args:
            sub.add_argument(*flags, **kwargs)
        sub.set_defaults(handler=spec.handler)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch to the matched command's handler.

    A bad --root surfaces as FileNotFoundError from research_graph_model.load
    with an already-plain-language message; that is a usage mistake, not a
    record-validity failure, so it is caught once here at exit code 2."""
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except FileNotFoundError as error:
        print(f"Error: {error}", file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
