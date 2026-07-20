#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Enforce tensor-shape discipline: jaxtyping annotations and einops operations.

Two rules, both aimed at the same failure — a shape bug that does not raise, and
so is found by debugging a wrong number rather than by reading a signature:

  TENSOR-001  a tensor parameter or return annotated with a bare type
              (`Tensor`, `torch.Tensor`, `np.ndarray`) instead of a jaxtyping
              annotation naming its axes. Vectors count: rank 1 is a shape.
  TENSOR-002  a raw shape operation (`.view`, `.reshape`, `.permute`,
              `.transpose`, `.squeeze`, `.unsqueeze`) where an einops call
              would state the intent and be checkable.

Exploratory code is exempt by design — pass only promoted paths, or rely on the
default excludes. Rules are warnings by default; `--strict` makes them errors.

Run from the project root:  uv run scripts/lint_tensors.py [--strict] [PATH ...]
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

ROOT: Final[Path] = Path(__file__).resolve().parent.parent

# Bare tensor types that should carry axis names instead.
BARE_TENSOR_TYPES: Final[frozenset[str]] = frozenset({
    "Tensor", "torch.Tensor", "ndarray", "np.ndarray", "numpy.ndarray",
    "FloatTensor", "LongTensor", "BoolTensor", "IntTensor",
})
# jaxtyping's array annotations, which is what we want to see instead.
JAXTYPING_NAMES: Final[frozenset[str]] = frozenset({
    "Float", "Int", "Bool", "Complex", "Float32", "Float16", "BFloat16",
    "Int32", "Int64", "UInt8", "Shaped", "Num", "Key", "PRNGKeyArray",
})
RAW_SHAPE_OPS: Final[frozenset[str]] = frozenset({
    "view", "reshape", "permute", "transpose", "squeeze", "unsqueeze", "flatten",
})
EINOPS_SUGGESTION: Final[dict[str, str]] = {
    "view": "rearrange", "reshape": "rearrange", "permute": "rearrange",
    "transpose": "rearrange", "squeeze": "rearrange", "unsqueeze": "rearrange",
    "flatten": "rearrange",
}
DEFAULT_EXCLUDE_PARTS: Final[frozenset[str]] = frozenset({
    "notebooks", "explore", "scratch", "experiments", "research",
    ".venv", "__pycache__", "data", "results", "notes",
})


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    rule: str
    message: str

    def render(self, root: Path) -> str:
        try:
            shown = self.path.relative_to(root)
        except ValueError:
            shown = self.path
        return f"  {shown}:{self.line} — [{self.rule}] {self.message}"


def annotation_text(node: ast.expr | None) -> str:
    """Source-ish text of an annotation node, or '' when absent."""
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except AttributeError:  # pragma: no cover — ast.unparse exists on 3.9+
        return ""


def is_bare_tensor(annotation: str) -> bool:
    """True when the annotation names a tensor type without axis names."""
    stripped = annotation.replace("Optional[", "").replace("]", "").strip()
    for part in stripped.replace("|", ",").split(","):
        if part.strip() in BARE_TENSOR_TYPES:
            return True
    return False


def is_jaxtyped(annotation: str) -> bool:
    return any(annotation.startswith(f"{name}[") for name in JAXTYPING_NAMES)


def check_annotation(annotation: str, path: Path, line: int, what: str) -> Finding | None:
    if not annotation or is_jaxtyped(annotation):
        return None
    if not is_bare_tensor(annotation):
        return None
    return Finding(
        path, line, "TENSOR-001",
        f"{what} annotated `{annotation}` — use a jaxtyping annotation naming its axes, "
        'e.g. Float[Tensor, "batch seq d_model"] (vectors too: Float[Tensor, "d_model"])',
    )


def check_function(node: ast.FunctionDef | ast.AsyncFunctionDef, path: Path) -> list[Finding]:
    findings: list[Finding] = []
    args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
    for arg in args:
        finding = check_annotation(annotation_text(arg.annotation), path, arg.lineno, f"parameter '{arg.arg}'")
        if finding is not None:
            findings.append(finding)
    returned = check_annotation(annotation_text(node.returns), path, node.lineno, f"return of '{node.name}'")
    if returned is not None:
        findings.append(returned)
    return findings


def check_shape_calls(tree: ast.AST, path: Path) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        method = node.func.attr
        if method not in RAW_SHAPE_OPS:
            continue
        findings.append(Finding(
            path, node.lineno, "TENSOR-002",
            f"`.{method}(...)` — prefer einops.{EINOPS_SUGGESTION[method]} with named axes, "
            'e.g. rearrange(x, "b s (h d) -> b h s d", h=n_heads)',
        ))
    return findings


def lint_file(path: Path) -> list[Finding]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            findings.extend(check_function(node, path))
    findings.extend(check_shape_calls(tree, path))
    return findings


def is_excluded(path: Path) -> bool:
    return any(part in DEFAULT_EXCLUDE_PARTS for part in path.parts)


def discover(paths: list[Path]) -> list[Path]:
    roots = paths or [ROOT]
    files: list[Path] = []
    for root in roots:
        if root.is_file() and root.suffix == ".py":
            files.append(root)
        elif root.is_dir():
            files.extend(p for p in sorted(root.rglob("*.py")) if not is_excluded(p))
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*", type=Path, help="files or directories (default: project root)")
    parser.add_argument("--strict", action="store_true", help="treat findings as errors")
    args = parser.parse_args()

    files = discover(args.paths)
    findings: list[Finding] = []
    for path in files:
        findings.extend(lint_file(path))

    if not findings:
        print(f"OK — {len(files)} file(s) clean (tensor annotations and einops usage).")
        return 0
    print(f"Checked {len(files)} file(s): {len(findings)} finding(s)\n")
    for finding in findings:
        print(finding.render(ROOT))
    print("\nExploratory code is exempt — these rules apply to promoted pipelines.")
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
