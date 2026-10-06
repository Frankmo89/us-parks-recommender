"""data/engine_fixtures.json must match what the live Python engine produces."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_engine_fixtures.py"


def _load():
    spec = importlib.util.spec_from_file_location("generate_engine_fixtures", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fixtures_file_matches_generator_byte_for_byte():
    gen = _load()
    current = gen.FIXTURES_PATH.read_text(encoding="utf-8")
    assert gen.render(gen.regenerate(json.loads(current))) == current, (
        "data/engine_fixtures.json is stale. Run: python scripts/generate_engine_fixtures.py "
        "(and bump engine_version, docs/engine-contract.md §4)"
    )


def test_generator_check_mode_passes_on_committed_file():
    assert _load().main(["--check"]) == 0
