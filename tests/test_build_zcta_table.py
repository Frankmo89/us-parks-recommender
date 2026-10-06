"""data/zcta_centroids.csv format and agreement with scripts/build_zcta_table.py.

No network: the build step runs on a verbatim sample of the 2026 Census
Gazetteer ZCTA file (tests/fixtures/gaz_zcta_2026_sample.txt).
"""

from __future__ import annotations

import csv
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_zcta_table.py"
TABLE = ROOT / "data" / "zcta_centroids.csv"
SAMPLE = ROOT / "tests" / "fixtures" / "gaz_zcta_2026_sample.txt"


def _load():
    spec = importlib.util.spec_from_file_location("build_zcta_table", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def table_lines() -> list[str]:
    return TABLE.read_text(encoding="utf-8").splitlines()


def test_table_header_row_count_and_format(table_lines):
    assert table_lines[0] == "zip,lat,lon"
    rows = table_lines[1:]
    # 2026 national ZCTA Gazetteer: 33,791 ZCTAs.
    assert len(rows) == 33_791
    pattern = re.compile(r"^\d{5},-?\d{1,2}\.\d{1,6},-?\d{1,3}\.\d{1,6}$")
    bad = [line for line in rows if not pattern.match(line)]
    assert not bad, bad[:5]
    zips = [line[:5] for line in rows]
    assert zips == sorted(zips)
    assert len(set(zips)) == len(zips)


def test_table_keeps_leading_zeros_as_strings():
    with TABLE.open(newline="", encoding="utf-8") as handle:
        by_zip = {row["zip"]: row for row in csv.DictReader(handle)}
    assert by_zip["02108"] == {"zip": "02108", "lat": "42.355097", "lon": "-71.065737"}
    assert "00601" in by_zip


def test_build_script_output_matches_committed_rows_for_sample(table_lines):
    build = _load()
    rows = build.parse_gazetteer(SAMPLE.read_text(encoding="utf-8"))
    rendered = build.render_csv(rows).splitlines()
    assert rendered[0] == table_lines[0]
    committed = set(table_lines[1:])
    assert len(rendered) == 8
    for line in rendered[1:]:
        assert line in committed, line
    # Last ZCTA in the source is also the last row of the table.
    assert rendered[-1] == table_lines[-1]


def test_build_script_reads_zip_archive_and_tab_layout():
    build = _load()
    import io
    import zipfile

    tab_text = (
        "GEOID\tALAND\tAWATER\tALAND_SQMI\tAWATER_SQMI\tINTPTLAT\tINTPTLONG              \n"
        "02108\t709322\t14973\t0.274\t0.006\t42.355097\t-71.065737              \n"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("2024_Gaz_zcta_national.txt", tab_text)
    text = build.read_gazetteer_text(buf.getvalue())
    assert build.parse_gazetteer(text) == [("02108", "42.355097", "-71.065737")]


def test_build_script_rejects_bad_rows():
    build = _load()
    header = "GEOID|INTPTLAT|INTPTLONG\n"
    with pytest.raises(ValueError, match="bad ZCTA code"):
        build.parse_gazetteer(header + "2108|42.35|-71.06\n")
    with pytest.raises(ValueError, match="duplicate ZCTA"):
        build.parse_gazetteer(header + "02108|42.35|-71.06\n02108|42.35|-71.06\n")
    with pytest.raises(ValueError, match="unexpected Gazetteer header"):
        build.parse_gazetteer("ZIP|LAT|LON\n02108|42.35|-71.06\n")


def test_source_url_points_at_census_gazetteer():
    build = _load()
    assert build.source_url(2026) == (
        "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
        "2026_Gazetteer/2026_Gaz_zcta_national.zip"
    )


def test_build_script_drops_leading_plus_sign():
    build = _load()
    rows = build.parse_gazetteer("GEOID|INTPTLAT|INTPTLONG\n96910|13.450428|+144.751149\n")
    assert rows == [("96910", "13.450428", "144.751149")]
