"""Enforce docs/engine-contract.md §4: a fixture change needs an engine_version bump.

Compares data/engine_fixtures.json between a base git revision (the PR's target
branch) and the working tree (or a second revision). The comparison ignores the
file's own version stamps (top-level ``engine_version`` and every
``profiles[*].output.engine_version``) and the free-text ``notes``. Everything
else counts: park order, scores, breakdown, facts, drive hours, tie_groups,
weights, tie_epsilon, k.

Rules:

* Fixtures differ  -> pyproject.toml ``[project].version`` must also differ.
  "Differ" is whole-bundle equality after normalization, so profiles added or
  removed (a change in the pinned set) count, not just changed output for
  profiles present on both sides.
* Fixtures identical -> no bump required.
* The fixture's own version stamps must equal pyproject's version, so a bump
  cannot leave the parity file stamped with the old number.

Usage:

    python scripts/check_engine_version_bump.py --base origin/main
    python scripts/check_engine_version_bump.py --base 3a82f07 --head f104f49

Exit code 0 = pass, 1 = contract violation, 2 = could not run.
"""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_PATH = "data/engine_fixtures.json"
PYPROJECT_PATH = "pyproject.toml"
CONTRACT_REF = "docs/engine-contract.md §4 (Versioning)"


@dataclass
class Verdict:
    ok: bool
    messages: list[str] = field(default_factory=list)


# --- Pure logic ---------------------------------------------------------------


def strip_version_stamps(bundle: dict) -> dict:
    """Return a copy without the file's own version stamps and prose notes."""
    out = copy.deepcopy(bundle)
    out.pop("engine_version", None)
    out.pop("notes", None)
    for profile in out.get("profiles", []):
        profile.pop("notes", None)
        if isinstance(profile.get("output"), dict):
            profile["output"].pop("engine_version", None)
    return out


def fixture_version_stamps(bundle: dict) -> set[str]:
    stamps = set()
    if "engine_version" in bundle:
        stamps.add(str(bundle["engine_version"]))
    for profile in bundle.get("profiles", []):
        output = profile.get("output")
        if isinstance(output, dict) and "engine_version" in output:
            stamps.add(str(output["engine_version"]))
    return stamps


def pyproject_version(text: str) -> str:
    return str(tomllib.loads(text)["project"]["version"])


def _order(output: dict) -> list[str]:
    return [park["facts"]["park_code"] for park in output.get("parks", [])]


def _scores(output: dict) -> list[tuple]:
    return [
        (park.get("score"), json.dumps(park.get("breakdown"), sort_keys=True))
        for park in output.get("parks", [])
    ]


def describe_fixture_changes(base: dict, head: dict) -> tuple[list[str], list[str]]:
    """What differs between two normalized bundles.

    Returns ``(behavior, surface)``: ``behavior`` lists changed constants and
    changed output for profiles present on both sides; ``surface`` lists
    profiles added or removed (the pinned set a consumer can rely on grew or
    shrank, even if every shared profile is unchanged).
    """
    lines: list[str] = []
    surface: list[str] = []
    for key in ("weights", "tie_epsilon", "k"):
        if base.get(key) != head.get(key):
            lines.append(f"{key}: {base.get(key)!r} -> {head.get(key)!r}")

    base_profiles = {p["id"]: p for p in base.get("profiles", [])}
    head_profiles = {p["id"]: p for p in head.get("profiles", [])}
    for pid in sorted(set(base_profiles) - set(head_profiles)):
        surface.append(f"{pid}: profile removed")
    for pid in sorted(set(head_profiles) - set(base_profiles)):
        surface.append(f"{pid}: profile added")
    if len(base.get("profiles", [])) != len(base_profiles) or len(
        head.get("profiles", [])
    ) != len(head_profiles):
        surface.append("duplicate profile ids present")

    for pid in sorted(set(base_profiles) & set(head_profiles)):
        b, h = base_profiles[pid], head_profiles[pid]
        if b == h:
            continue
        kinds = []
        if b.get("profile") != h.get("profile"):
            kinds.append("profile input")
        b_out, h_out = b.get("output", {}), h.get("output", {})
        if _order(b_out) != _order(h_out):
            kinds.append(f"park order {_order(b_out)} -> {_order(h_out)}")
        elif _scores(b_out) != _scores(h_out):
            kinds.append("scores/breakdown")
        if b_out.get("tie_groups") != h_out.get("tie_groups"):
            kinds.append(f"tie_groups {b_out.get('tie_groups')} -> {h_out.get('tie_groups')}")
        if not kinds:
            kinds.append("other output fields")
        lines.append(f"{pid}: " + "; ".join(kinds))
    return lines, surface


def check(
    base_fixtures: dict | None,
    head_fixtures: dict,
    base_version: str | None,
    head_version: str,
) -> Verdict:
    messages: list[str] = []
    ok = True

    stamps = fixture_version_stamps(head_fixtures)
    if stamps != {head_version}:
        ok = False
        messages.append(
            f"FAIL: {FIXTURES_PATH} is stamped engine_version {sorted(stamps)} but "
            f"{PYPROJECT_PATH} says {head_version}. Restamp the fixtures so the "
            f"parity file and the package agree ({CONTRACT_REF})."
        )

    if base_fixtures is None or base_version is None:
        messages.append(
            f"PASS: no {FIXTURES_PATH} or {PYPROJECT_PATH} at the base revision; "
            "nothing to compare."
        )
        return Verdict(ok, messages)

    base_norm = strip_version_stamps(base_fixtures)
    head_norm = strip_version_stamps(head_fixtures)

    if base_norm == head_norm:
        messages.append(
            f"PASS: {FIXTURES_PATH} unchanged apart from version stamps/notes; "
            f"no engine_version bump required (version {base_version} -> {head_version})."
        )
        return Verdict(ok, messages)

    behavior, surface = describe_fixture_changes(base_norm, head_norm)
    changes = behavior + surface
    detail = "\n".join(f"  - {line}" for line in changes) or "  - (see git diff)"

    if base_version == head_version:
        ok = False
        reasons = []
        if behavior or not surface:
            reasons.append(
                f"Per {CONTRACT_REF}, any change to weights, filters, drive constants, "
                f"IDF, vocab, score formula, tie semantics, or catalog features that "
                f"changes scores/order for existing profiles is breaking and must bump "
                f"engine_version."
            )
        if surface:
            reasons.append(
                f"Profiles were added or removed ({len(surface)}). The pinned set of "
                f"behaviors a consumer can rely on changed, so per the spirit of "
                f"{CONTRACT_REF} it must be visible as a new engine_version."
            )
        messages.append(
            f"FAIL: {FIXTURES_PATH} changed but {PYPROJECT_PATH} version is still "
            f"{head_version}.\n" + "\n".join(reasons) + "\n"
            f"Bump the version (today: the minor component of 0.x, e.g. 0.1.0 -> 0.2.0), "
            f"restamp the fixtures, and record before/after metrics in CHANGELOG.md.\n"
            f"Fixture changes detected:\n{detail}"
        )
    else:
        messages.append(
            f"PASS: {FIXTURES_PATH} changed and engine_version bumped "
            f"{base_version} -> {head_version}.\nFixture changes detected:\n{detail}"
        )
    return Verdict(ok, messages)


# --- Git plumbing -------------------------------------------------------------


def git_show(rev: str, path: str) -> str | None:
    """File content at ``rev``, or None when the path does not exist there."""
    proc = subprocess.run(
        ["git", "show", f"{rev}:{path}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return proc.stdout
    stderr = proc.stderr.strip()
    if "does not exist" in stderr or "exists on disk, but not in" in stderr:
        return None
    raise RuntimeError(f"git show {rev}:{path} failed: {stderr}")


def load_side(rev: str | None) -> tuple[dict | None, str | None]:
    """(fixtures, version) at ``rev``; ``None`` rev reads the working tree."""
    if rev is None:
        fixtures_text = (ROOT / FIXTURES_PATH).read_text(encoding="utf-8")
        pyproject_text = (ROOT / PYPROJECT_PATH).read_text(encoding="utf-8")
    else:
        fixtures_text = git_show(rev, FIXTURES_PATH)
        pyproject_text = git_show(rev, PYPROJECT_PATH)
    fixtures = json.loads(fixtures_text) if fixtures_text is not None else None
    version = pyproject_version(pyproject_text) if pyproject_text is not None else None
    return fixtures, version


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--base",
        default="origin/main",
        help="git revision to compare against (default: origin/main)",
    )
    parser.add_argument(
        "--head",
        default=None,
        help="git revision to check (default: the working tree)",
    )
    args = parser.parse_args(argv)

    try:
        base_fixtures, base_version = load_side(args.base)
        head_fixtures, head_version = load_side(args.head)
    except (RuntimeError, OSError, json.JSONDecodeError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if head_fixtures is None or head_version is None:
        print(f"ERROR: {FIXTURES_PATH} or {PYPROJECT_PATH} missing on the head side", file=sys.stderr)
        return 2

    verdict = check(base_fixtures, head_fixtures, base_version, head_version)
    head_label = args.head or "working tree"
    print(f"engine_version check: base={args.base} head={head_label}")
    for message in verdict.messages:
        print(message)
    return 0 if verdict.ok else 1


if __name__ == "__main__":
    sys.exit(main())
