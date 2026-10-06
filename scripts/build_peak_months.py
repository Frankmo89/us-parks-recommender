"""Peak-visitation months per park from NPS monthly visit counts.

The rules live in src/visits.py (2023-2025 average, Oct/Nov 2025 treated as
missing because of the federal shutdown, peak = visits >= 0.7 x the busiest
month). This script prints the result, checks that the PEAK_MONTHS table in
scripts/build_parks_csv.py matches it, and can refetch a raw year.

Usage:

    python scripts/build_peak_months.py                  # summary + table
    python scripts/build_peak_months.py --parks yose,havo
    python scripts/build_peak_months.py --check          # build script in sync?
    python scripts/build_peak_months.py --download 2025  # refetch one raw year
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import visits  # noqa: E402

PARKS_CSV = ROOT / "data" / "parks.csv"
BUILD_SCRIPT = ROOT / "scripts" / "build_parks_csv.py"
API_URL = "https://irmaservices.nps.gov/v3/rest/stats/visitation"


def catalog_codes(path: Path = PARKS_CSV) -> list[str]:
    with path.open(newline="") as handle:
        return [row["park_code"] for row in csv.DictReader(handle)]


def computed_peak_months(codes: list[str]) -> dict[str, str]:
    """park_code -> peak months in best_months format ("6,7,8")."""
    monthly = visits.load_monthly(codes)
    return {code: ",".join(str(m) for m in visits.peak_months(monthly[code])) for code in codes}


def build_script_table() -> dict[str, str]:
    spec = importlib.util.spec_from_file_location("build_parks_csv", BUILD_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return dict(module.PEAK_MONTHS)


def download(year: int, codes: list[str]) -> Path:
    """Fetch one calendar year for the catalog parks and save it verbatim."""
    query = (
        f"?unitCodes={','.join(visits.unit_code(c) for c in codes)}"
        f"&startMonth=1&startYear={year}&endMonth=12&endYear={year}"
    )
    request = urllib.request.Request(API_URL + query, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        body = response.read()
    json.loads(body)  # fail before writing if the body is not JSON
    path = visits.raw_path(year)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return path


def detail(code: str, monthly: dict[int, float]) -> str:
    busiest = max(monthly.values())
    months = " ".join(f"{m}:{monthly[m] / 1000:.0f}k" for m in visits.MONTHS)
    return (
        f"{code}: busiest {busiest:,.0f}, cutoff {visits.PEAK_CUTOFF * busiest:,.0f}, "
        f"peak {visits.peak_months(monthly)}\n  {months}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--parks", default="", help="comma-separated park codes to detail")
    parser.add_argument("--check", action="store_true", help="compare with build_parks_csv.py")
    parser.add_argument("--download", type=int, metavar="YEAR", help="refetch one raw year")
    args = parser.parse_args(argv)

    codes = catalog_codes()
    if args.download:
        print(f"Wrote {download(args.download, codes)}")
        return 0
    table = computed_peak_months(codes)
    if args.check:
        stale = {c: (v, table[c]) for c, v in build_script_table().items() if table.get(c) != v}
        if stale or set(build_script_table()) != set(codes):
            print(f"PEAK_MONTHS in build_parks_csv.py is stale: {stale}")
            return 1
        print("PEAK_MONTHS in build_parks_csv.py matches the raw data")
        return 0

    counts = Counter(len(v.split(",")) if v else 0 for v in table.values())
    print(f"Peak months ({visits.PEAK_CUTOFF:g} x busiest month, {visits.VISIT_YEARS[0]}-"
          f"{visits.VISIT_YEARS[-1]} average, Oct/Nov 2025 missing)")
    print("count -> parks: " + ", ".join(f"{n}:{counts[n]}" for n in sorted(counts)))
    monthly = visits.load_monthly(codes)
    for code in [c for c in args.parks.split(",") if c]:
        print(detail(code, monthly[code]))
    print("PEAK_MONTHS = {")
    for code in codes:
        print(f'    "{code}": "{table[code]}",')
    print("}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
