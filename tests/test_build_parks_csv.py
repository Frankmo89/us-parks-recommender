"""scripts/build_parks_csv.py must reproduce the committed data/parks.csv."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_parks_csv.py"


def _load():
    spec = importlib.util.spec_from_file_location("build_parks_csv", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_script_output_matches_committed_csv_byte_for_byte():
    build = _load()
    committed = (ROOT / "data" / "parks.csv").read_bytes().decode("utf-8")
    assert build.render_csv() == committed, (
        "scripts/build_parks_csv.py and data/parks.csv disagree; update the script "
        "table when the catalog changes"
    )


def test_build_script_access_values():
    build = _load()
    rows = {row[0]: row[-1] for row in build.build_rows()}
    assert build.FIELDS[-1] == "access"
    assert {code for code, value in rows.items() if value == "flight"} == {
        "hale", "havo", "npsa", "viis", "gaar", "glba", "katm", "kova", "lacl",
    }
    assert {code for code, value in rows.items() if value == "boat"} == {"chis", "drto", "isro"}
    assert sum(value == "road" for value in rows.values()) == 63 - 9 - 3
