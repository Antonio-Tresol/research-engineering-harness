#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest>=8.0", "lanorme"]
# ///
"""Tests for the harness's checks.

Two things are tested, and the second matters more:

  * that each rule FIRES on the thing it is meant to catch, and
  * that it STAYS QUIET on realistic input it should not touch.

The false-positive tests exist because every false positive found so far was
found by accident, in the middle of doing something else. A checker that cries
wolf gets bypassed, and then the true positives go unread too. Each `quiet_*`
test below encodes a specific false positive that was actually shipped.

Run:  uv run tests/test_checks.py        (or: uv run --with pytest pytest tests/)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lanorme_plugins._common import is_glob_match  # noqa: E402
from lanorme_plugins.provenance import ProvenanceCheck  # noqa: E402
from lanorme_plugins.skill_portability import SkillPortabilityCheck  # noqa: E402
from lanorme_plugins.tensors import TensorsCheck  # noqa: E402

SKILL_BODY = "\n".join(f"Body line {i} with real content." for i in range(8))


def write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def make_skill(root: Path, name: str, frontmatter: str, body: str = SKILL_BODY) -> None:
    write(root, f".claude/skills/{name}/SKILL.md", f"---\n{frontmatter}\n---\n\n{body}\n")


def codes(result: object) -> list[str]:
    """Rule codes reported, violations and warnings together."""
    return [v.code for v in [*result.violations, *result.warnings]]  # type: ignore[attr-defined]


# --------------------------------------------------------------------------
# Glob matching. The shipped default `reports/**/*.md` silently matched nothing
# for files directly inside reports/, because fnmatch requires a separator.
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("path", "pattern", "expected"),
    [
        ("reports/findings.md", "reports/**/*.md", True),   # regression: was False
        ("reports/a/b/deep.md", "reports/**/*.md", True),
        ("README.md", "**/*.md", True),                     # regression: was False
        ("notes/a/b.md", "**/*.md", True),
        ("src/main.py", "**/*.md", False),
        ("otherdir/findings.md", "reports/**/*.md", False),
        ("reports/findings.txt", "reports/**/*.md", False),
    ],
)
def test_glob_semantics(path: str, pattern: str, expected: bool) -> None:
    assert is_glob_match(path, [pattern]) is expected


# --------------------------------------------------------------------------
# Provenance
# --------------------------------------------------------------------------

def test_provenance_fires_on_wrong_value(tmp_path: Path) -> None:
    write(tmp_path, "results/r.json", json.dumps({"rate": 0.43}))
    write(tmp_path, "doc.md", "Rate was 50%.\n<!-- claim: 0.50 from results/r.json#rate -->\n")
    assert "PROV-002" in codes(ProvenanceCheck().run(src_root=str(tmp_path)))


def test_provenance_fires_on_missing_file_and_key(tmp_path: Path) -> None:
    write(tmp_path, "results/r.json", json.dumps({"rate": 0.43}))
    write(tmp_path, "a.md", "x\n<!-- claim: 0.1 from results/gone.json#rate -->\n")
    write(tmp_path, "b.md", "x\n<!-- claim: 0.1 from results/r.json#nope -->\n")
    assert codes(ProvenanceCheck().run(src_root=str(tmp_path))).count("PROV-001") == 2


def test_provenance_quiet_on_rounded_value(tmp_path: Path) -> None:
    """0.37 in prose against 0.3712 on disk agrees to the precision written."""
    write(tmp_path, "results/r.json", json.dumps({"rate": 0.3712}))
    write(tmp_path, "doc.md", "37%.\n<!-- claim: 0.37 from results/r.json#rate -->\n")
    assert codes(ProvenanceCheck().run(src_root=str(tmp_path))) == []


def test_provenance_quiet_on_explicit_tolerance(tmp_path: Path) -> None:
    write(tmp_path, "results/r.json", json.dumps({"rate": 0.44}))
    write(tmp_path, "doc.md", "44%.\n<!-- claim: 0.43 from results/r.json#rate tol=0.02 -->\n")
    assert codes(ProvenanceCheck().run(src_root=str(tmp_path))) == []


def test_provenance_quiet_inside_code_fence(tmp_path: Path) -> None:
    """Documentation showing the syntax is not a claim about this project."""
    write(tmp_path, "doc.md", "Example:\n\n```markdown\n<!-- claim: 0.9 from results/x.json#k -->\n```\n")
    assert codes(ProvenanceCheck().run(src_root=str(tmp_path))) == []


def test_provenance_resolves_list_indices(tmp_path: Path) -> None:
    write(tmp_path, "results/r.json", json.dumps({"runs": [{"acc": 0.8}, {"acc": 0.9}]}))
    write(tmp_path, "doc.md", "Second run 0.90.\n<!-- claim: 0.9 from results/r.json#runs.1.acc -->\n")
    assert codes(ProvenanceCheck().run(src_root=str(tmp_path))) == []


def test_prov003_quiet_when_marker_on_adjacent_line(tmp_path: Path) -> None:
    """The documented convention puts the marker on the line after the prose."""
    write(tmp_path, "results/r.json", json.dumps({"rate": 0.43}))
    write(tmp_path, "reports/f.md", "Rate was 43%.\n<!-- claim: 0.43 from results/r.json#rate -->\n")
    check = ProvenanceCheck()
    check.configure(settings={"claim_bearing": ["reports/**/*.md"]})
    assert codes(check.run(src_root=str(tmp_path))) == []


def test_prov003_fires_on_unmarked_statistic(tmp_path: Path) -> None:
    write(tmp_path, "reports/f.md", "An unmarked rate of 22.5% appears here.\n")
    check = ProvenanceCheck()
    check.configure(settings={"claim_bearing": ["reports/**/*.md"]})
    assert "PROV-003" in codes(check.run(src_root=str(tmp_path)))


def test_prov003_off_by_default(tmp_path: Path) -> None:
    """Opt-in: no claim_bearing configured means no PROV-003 anywhere."""
    write(tmp_path, "reports/f.md", "An unmarked rate of 22.5% appears here.\n")
    assert codes(ProvenanceCheck().run(src_root=str(tmp_path))) == []


def test_provenance_quiet_on_prose_without_numbers(tmp_path: Path) -> None:
    write(tmp_path, "reports/f.md", "This document discusses methodology and cites no figures.\n")
    check = ProvenanceCheck()
    check.configure(settings={"claim_bearing": ["reports/**/*.md"]})
    assert codes(check.run(src_root=str(tmp_path))) == []


# --------------------------------------------------------------------------
# Tensors
# --------------------------------------------------------------------------

def test_tensors_fires_on_bare_annotations_including_vectors(tmp_path: Path) -> None:
    write(tmp_path, "m.py", "from torch import Tensor\n\n"
                            "def f(x: Tensor, v: Tensor) -> Tensor:\n    return x\n")
    found = codes(TensorsCheck().run(src_root=str(tmp_path)))
    assert found.count("TENSOR-001") == 3  # two parameters and the return


def test_tensors_fires_on_raw_shape_ops(tmp_path: Path) -> None:
    write(tmp_path, "m.py", "def f(x):\n    return x.view(1, -1).permute(1, 0)\n")
    assert codes(TensorsCheck().run(src_root=str(tmp_path))).count("TENSOR-002") == 2


def test_tensors_quiet_on_jaxtyping_and_einops(tmp_path: Path) -> None:
    write(tmp_path, "m.py",
          'from jaxtyping import Float\nfrom torch import Tensor\nfrom einops import rearrange\n\n'
          'def f(x: Float[Tensor, "b s d"], v: Float[Tensor, "d"]) -> Float[Tensor, "b s"]:\n'
          '    return rearrange(x, "b s d -> b d s")\n')
    assert codes(TensorsCheck().run(src_root=str(tmp_path))) == []


def test_tensors_quiet_on_non_tensor_code(tmp_path: Path) -> None:
    """Ordinary Python must not attract tensor rules."""
    write(tmp_path, "m.py", "def add(a: int, b: int) -> int:\n    return a + b\n\n"
                            "def name(items: list[str]) -> str:\n    return items[0]\n")
    assert codes(TensorsCheck().run(src_root=str(tmp_path))) == []


def test_tensors_survives_unparseable_file(tmp_path: Path) -> None:
    write(tmp_path, "broken.py", "def f(:\n")
    assert codes(TensorsCheck().run(src_root=str(tmp_path))) == []


# --------------------------------------------------------------------------
# Skill portability
# --------------------------------------------------------------------------

def test_hskill001_fires_on_machine_path(tmp_path: Path) -> None:
    make_skill(tmp_path, "a", "name: a\ndescription: Use when testing.",
               SKILL_BODY + "\nSee /Users/someone/thing.md\n")
    assert "HSKILL-001" in codes(SkillPortabilityCheck().run(src_root=str(tmp_path)))


def test_task_style_descriptions_are_not_flagged(tmp_path: Path) -> None:
    """Regression: a rule requiring literal 'use when' phrasing produced 43
    findings and zero true positives across four real skill collections. An
    imperative task description says when to use a skill perfectly well."""
    for i, description in enumerate([
        "Convert a Jupyter notebook (.ipynb) to a marimo notebook (.py).",
        "Generate anywidget components for marimo notebooks.",
        "Check if a marimo notebook is compatible with WASM and report issues.",
    ]):
        make_skill(tmp_path, f"s{i}", f"name: s{i}\ndescription: {description}")
    (tmp_path / ".agents").mkdir()
    (tmp_path / ".agents/skills").symlink_to(Path("..") / ".claude" / "skills", target_is_directory=True)
    assert codes(SkillPortabilityCheck().run(src_root=str(tmp_path))) == []


def test_hskill002_fires_on_unknown_key(tmp_path: Path) -> None:
    make_skill(tmp_path, "a", "name: a\ndescription: Use when testing.\ndescriptn: typo")
    assert "HSKILL-002" in codes(SkillPortabilityCheck().run(src_root=str(tmp_path)))


def test_hskill003_fires_when_link_is_a_text_file(tmp_path: Path) -> None:
    """Git on Windows checks a symlink out as text; Codex then sees no skills."""
    make_skill(tmp_path, "a", "name: a\ndescription: Use when testing.")
    write(tmp_path, ".agents/skills", "../.claude/skills")
    assert "HSKILL-003" in codes(SkillPortabilityCheck().run(src_root=str(tmp_path)))


def test_hskill003_fires_when_copy_has_drifted(tmp_path: Path) -> None:
    make_skill(tmp_path, "a", "name: a\ndescription: Use when testing.")
    make_skill(tmp_path, "b", "name: b\ndescription: Use when testing.")
    (tmp_path / ".agents").mkdir()
    (tmp_path / ".agents/skills/a").mkdir(parents=True)
    assert "HSKILL-003" in codes(SkillPortabilityCheck().run(src_root=str(tmp_path)))


def test_codex_link_check_can_be_disabled(tmp_path: Path) -> None:
    make_skill(tmp_path, "a", "name: a\ndescription: Use when testing.")
    check = SkillPortabilityCheck()
    check.configure(settings={"require_codex_link": False})
    assert codes(check.run(src_root=str(tmp_path))) == []


def test_hskill003_quiet_when_symlinked(tmp_path: Path) -> None:
    make_skill(tmp_path, "a", "name: a\ndescription: Use when testing.")
    (tmp_path / ".agents").mkdir()
    (tmp_path / ".agents/skills").symlink_to(Path("..") / ".claude" / "skills", target_is_directory=True)
    assert "HSKILL-003" not in codes(SkillPortabilityCheck().run(src_root=str(tmp_path)))


def test_skill_checks_quiet_on_a_well_formed_skill(tmp_path: Path) -> None:
    """The whole point: a correct skill produces nothing at all."""
    make_skill(tmp_path, "good", "name: good\ndescription: Use when the user asks for a thing.")
    (tmp_path / ".agents").mkdir()
    (tmp_path / ".agents/skills").symlink_to(Path("..") / ".claude" / "skills", target_is_directory=True)
    assert codes(SkillPortabilityCheck().run(src_root=str(tmp_path))) == []


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
