"""Unit tests for scripts/check_engine_version_bump.py (contract §4 enforcement)."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_engine_version_bump.py"

spec = importlib.util.spec_from_file_location("check_engine_version_bump", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod  # dataclasses resolve annotations via sys.modules
spec.loader.exec_module(mod)


def _park(code: str, score: float) -> dict:
    return {
        "rank": 1,
        "score": score,
        "match_percent": 50,
        "tied_with_neighbors": False,
        "breakdown": {"content": score, "weighted": {"content": score}},
        "facts": {"park_code": code, "name": code.upper()},
    }


def _bundle(version: str = "0.1.0") -> dict:
    return {
        "notes": ["prose"],
        "engine_version": version,
        "weights": {"W_CONTENT": 0.55},
        "tie_epsilon": 0.001,
        "k": 5,
        "profiles": [
            {
                "id": "p1",
                "kind": "eval",
                "split": "train",
                "notes": "prose",
                "profile": {"biomes": [], "tags": ["hiking"]},
                "output": {
                    "engine_version": version,
                    "k": 5,
                    "n_returned": 2,
                    "empty": False,
                    "tie_epsilon": 0.001,
                    "tie_groups": [],
                    "parks": [_park("acad", 0.6), _park("arch", 0.5)],
                },
            }
        ],
    }


def test_strip_version_stamps_removes_only_stamps_and_notes():
    stripped = mod.strip_version_stamps(_bundle())
    assert "engine_version" not in stripped
    assert "notes" not in stripped
    assert "notes" not in stripped["profiles"][0]
    assert "engine_version" not in stripped["profiles"][0]["output"]
    assert stripped["weights"] == {"W_CONTENT": 0.55}
    assert stripped["profiles"][0]["output"]["parks"][0]["facts"]["park_code"] == "acad"
    assert mod.strip_version_stamps(_bundle("0.1.0")) == mod.strip_version_stamps(_bundle("0.2.0"))


def test_identical_fixtures_same_version_passes():
    verdict = mod.check(_bundle(), _bundle(), "0.1.0", "0.1.0")
    assert verdict.ok
    assert any("no engine_version bump required" in m for m in verdict.messages)


def test_version_bump_with_restamped_fixtures_and_no_scoring_change_passes():
    verdict = mod.check(_bundle("0.1.0"), _bundle("0.2.0"), "0.1.0", "0.2.0")
    assert verdict.ok
    assert any("no engine_version bump required" in m for m in verdict.messages)


def test_order_change_without_bump_fails_and_points_to_contract():
    head = _bundle()
    parks = head["profiles"][0]["output"]["parks"]
    parks.reverse()
    verdict = mod.check(_bundle(), head, "0.1.0", "0.1.0")
    assert not verdict.ok
    text = "\n".join(verdict.messages)
    assert "engine-contract.md §4" in text
    assert "p1: park order ['acad', 'arch'] -> ['arch', 'acad']" in text


def test_score_change_without_bump_fails():
    head = _bundle()
    head["profiles"][0]["output"]["parks"][0]["score"] = 0.61
    verdict = mod.check(_bundle(), head, "0.1.0", "0.1.0")
    assert not verdict.ok
    assert "p1: scores/breakdown" in "\n".join(verdict.messages)


def test_tie_groups_change_without_bump_fails():
    head = _bundle()
    head["profiles"][0]["output"]["tie_groups"] = [["acad", "arch"]]
    verdict = mod.check(_bundle(), head, "0.1.0", "0.1.0")
    assert not verdict.ok
    assert "tie_groups [] -> [['acad', 'arch']]" in "\n".join(verdict.messages)


def test_weights_change_without_bump_fails():
    head = _bundle()
    head["weights"]["W_CONTENT"] = 0.6
    verdict = mod.check(_bundle(), head, "0.1.0", "0.1.0")
    assert not verdict.ok
    assert "weights:" in "\n".join(verdict.messages)


def test_fixture_change_with_bump_passes():
    head = _bundle("0.2.0")
    head["profiles"][0]["output"]["parks"].reverse()
    verdict = mod.check(_bundle("0.1.0"), head, "0.1.0", "0.2.0")
    assert verdict.ok
    assert "bumped 0.1.0 -> 0.2.0" in "\n".join(verdict.messages)


def test_bump_without_restamping_fixtures_fails():
    verdict = mod.check(_bundle("0.1.0"), _bundle("0.1.0"), "0.1.0", "0.2.0")
    assert not verdict.ok
    assert "stamped engine_version ['0.1.0'] but pyproject.toml says 0.2.0" in "\n".join(
        verdict.messages
    )


def test_missing_base_passes():
    verdict = mod.check(None, _bundle(), None, "0.1.0")
    assert verdict.ok


def test_added_profile_without_bump_fails():
    head = _bundle()
    head["profiles"].append(copy.deepcopy(head["profiles"][0]) | {"id": "p2"})
    verdict = mod.check(_bundle(), head, "0.1.0", "0.1.0")
    assert not verdict.ok
    assert "p2: profile added" in "\n".join(verdict.messages)


def test_committed_fixtures_are_stamped_with_pyproject_version():
    fixtures = json.loads((ROOT / "data" / "engine_fixtures.json").read_text(encoding="utf-8"))
    version = mod.pyproject_version((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert mod.fixture_version_stamps(fixtures) == {version}


@pytest.mark.parametrize(
    ("base", "head", "expected"),
    [
        # PR #7 changed empty_content_defaults order via the park_code tie-break
        # without a bump. The check must flag it.
        ("3a82f07", "f104f49", 1),
        # PR #8 (TypeScript port) left fixtures untouched.
        ("f104f49", "799fd0d", 0),
    ],
)
def test_history_regressions(base: str, head: str, expected: int, capsys):
    try:
        mod.git_show(base, mod.PYPROJECT_PATH)
        mod.git_show(head, mod.PYPROJECT_PATH)
    except RuntimeError:
        pytest.skip("shallow clone: history not available")
    assert mod.main(["--base", base, "--head", head]) == expected
