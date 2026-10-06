"""Build data/zcta_centroids.csv (zip, lat, lon) from the Census ZCTA Gazetteer.

Source: U.S. Census Bureau Gazetteer Files, ZIP Code Tabulation Areas,
national file (public domain):
https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html

Each row is a ZCTA's internal point (INTPTLAT / INTPTLONG), copied as the
Census prints it (up to 6 decimals, leading "+" dropped). ZIPs stay 5-character strings with leading
zeros. Run:

    python scripts/build_zcta_table.py                 # download DEFAULT_YEAR
    python scripts/build_zcta_table.py --year 2026
    python scripts/build_zcta_table.py --source path/to/2026_Gaz_zcta_national.zip

Needs network only when --source is not given. Tests never download.
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "data" / "zcta_centroids.csv"
DEFAULT_YEAR = 2026
URL_TEMPLATE = (
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    "{year}_Gazetteer/{year}_Gaz_zcta_national.zip"
)
ZIP_RE = re.compile(r"^\d{5}$")


def source_url(year: int) -> str:
    return URL_TEMPLATE.format(year=year)


def read_gazetteer_text(raw: bytes) -> str:
    """Return the Gazetteer text from a .zip archive or a plain .txt payload."""
    if raw[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names = [name for name in archive.namelist() if name.endswith(".txt")]
            if len(names) != 1:
                raise ValueError(f"expected one .txt in the archive, got {names}")
            raw = archive.read(names[0])
    return raw.decode("utf-8-sig")


def parse_gazetteer(text: str) -> list[tuple[str, str, str]]:
    """(zip, lat, lon) rows sorted by ZIP.

    Handles both layouts the Census has used: pipe-delimited (2026) and
    tab-delimited with padded last column (earlier years).
    """
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("empty Gazetteer file")
    delimiter = "|" if "|" in lines[0] else "\t"
    header = [cell.strip() for cell in lines[0].split(delimiter)]
    try:
        i_zip = header.index("GEOID")
        i_lat = header.index("INTPTLAT")
        i_lon = header.index("INTPTLONG")
    except ValueError as exc:
        raise ValueError(f"unexpected Gazetteer header: {header}") from exc

    rows: dict[str, tuple[str, str, str]] = {}
    for line in lines[1:]:
        cells = [cell.strip() for cell in line.split(delimiter)]
        # Census prints a leading "+" on some positive values (Guam, CNMI).
        code, lat, lon = cells[i_zip], cells[i_lat].lstrip("+"), cells[i_lon].lstrip("+")
        if not ZIP_RE.match(code):
            raise ValueError(f"bad ZCTA code {code!r}")
        lat_f, lon_f = float(lat), float(lon)
        if not (-90 <= lat_f <= 90 and -180 <= lon_f <= 180):
            raise ValueError(f"ZCTA {code}: coordinates out of range ({lat}, {lon})")
        if code in rows:
            raise ValueError(f"duplicate ZCTA {code}")
        rows[code] = (code, lat, lon)
    return [rows[code] for code in sorted(rows)]


def render_csv(rows: list[tuple[str, str, str]]) -> str:
    out = ["zip,lat,lon"]
    out.extend(f"{code},{lat},{lon}" for code, lat, lon in rows)
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
    parser.add_argument("--source", type=Path, help="local Gazetteer .zip or .txt (skips download)")
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args(argv)

    if args.source:
        raw = args.source.read_bytes()
        origin = str(args.source)
    else:
        origin = source_url(args.year)
        with urllib.request.urlopen(origin, timeout=60) as response:  # noqa: S310 (fixed census.gov URL)
            raw = response.read()

    rows = parse_gazetteer(read_gazetteer_text(raw))
    args.out.write_text(render_csv(rows), encoding="utf-8", newline="")
    print(f"Wrote {len(rows)} ZCTAs to {args.out} from {origin}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
