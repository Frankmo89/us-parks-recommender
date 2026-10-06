"""Find each park's peak-visitation months from NPS monthly visit counts.

Source: NPS Visitor Use Statistics (https://irma.nps.gov/Stats/), monthly
recreation visits, fetched from the IRMA REST endpoint

    https://irmaservices.nps.gov/v3/rest/stats/visitation
        ?unitCodes=ACAD,...&startMonth=1&startYear=YYYY&endMonth=12&endYear=YYYY

and saved verbatim as data/raw/nps_recreation_visits_by_month_YYYY.json.

Analysis only for now: this script prints peak months under candidate
cutoffs. It does not write data/parks.csv; the cutoff needs approval first.

Two cutoff rules:

    mean: a month is peak when visits >= k * the park's monthly mean
    max:  a month is peak when visits >= f * the park's busiest month

Usage:

    python scripts/build_peak_months.py                    # 2025, summary
    python scripts/build_peak_months.py --parks yose,dena  # per-park detail
    python scripts/build_peak_months.py --years 2023-2025  # average years
    python scripts/build_peak_months.py --download 2025    # refetch raw file
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PARKS_CSV = ROOT / "data" / "parks.csv"
API_URL = "https://irmaservices.nps.gov/v3/rest/stats/visitation"
MONTHS = tuple(range(1, 13))

# NPS Stats unit code -> catalog park_code, where they differ. The catalog's
# `seki` row is Sequoia National Park; NPS Stats reports Sequoia as SEQU and
# Kings Canyon (KICA) separately, so no split is needed.
UNIT_TO_PARK = {"SEQU": "seki"}
PARK_TO_UNIT = {park: unit for unit, park in UNIT_TO_PARK.items()}

CANDIDATES = (("mean", 1.0), ("mean", 1.25), ("mean", 1.5), ("max", 0.7), ("max", 0.75))


def raw_path(year: int) -> Path:
    return RAW_DIR / f"nps_recreation_visits_by_month_{year}.json"


def catalog_codes(path: Path = PARKS_CSV) -> list[str]:
    with path.open(newline="") as handle:
        return [row["park_code"] for row in csv.DictReader(handle)]


def unit_code(park_code: str) -> str:
    return PARK_TO_UNIT.get(park_code, park_code.upper())


def park_code(unit: str) -> str:
    return UNIT_TO_PARK.get(unit, unit.lower())


def download(year: int, codes: list[str]) -> Path:
    """Fetch one calendar year for the catalog parks and save it verbatim."""
    query = (
        f"?unitCodes={','.join(unit_code(c) for c in codes)}"
        f"&startMonth=1&startYear={year}&endMonth=12&endYear={year}"
    )
    request = urllib.request.Request(API_URL + query, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        body = response.read()
    json.loads(body)  # fail before writing if the body is not JSON
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = raw_path(year)
    path.write_bytes(body)
    return path


def load_year(year: int, codes: list[str]) -> dict[str, dict[int, int]]:
    """park_code -> {month: recreation visits}; every park needs 12 months."""
    records = json.loads(raw_path(year).read_text())
    visits: dict[str, dict[int, int]] = {}
    for rec in records:
        if int(rec["Year"]) != year:
            raise ValueError(f"{raw_path(year).name}: unexpected year {rec['Year']}")
        visits.setdefault(park_code(rec["UnitCode"]), {})[int(rec["Month"])] = int(
            rec["RecreationVisitors"]
        )
    missing = sorted(set(codes) - set(visits))
    if missing:
        raise ValueError(f"{year}: no visits for {missing}")
    short = sorted(code for code in codes if set(visits[code]) != set(MONTHS))
    if short:
        raise ValueError(f"{year}: not all 12 months for {short}")
    return {code: visits[code] for code in codes}


def load_monthly(years: list[int], codes: list[str]) -> dict[str, dict[int, float]]:
    """Average monthly visits across `years` (one year = that year's counts)."""
    per_year = [load_year(year, codes) for year in years]
    return {
        code: {m: sum(y[code][m] for y in per_year) / len(per_year) for m in MONTHS}
        for code in codes
    }


def peak_months(monthly: dict[int, float], rule: str, cutoff: float) -> list[int]:
    if rule == "mean":
        threshold = cutoff * sum(monthly.values()) / 12
    elif rule == "max":
        threshold = cutoff * max(monthly.values())
    else:
        raise ValueError(f"unknown rule {rule!r}")
    if threshold <= 0:
        return []
    return [m for m in MONTHS if monthly[m] >= threshold]


def annual_visits(monthly: dict[str, dict[int, float]]) -> dict[str, float]:
    return {code: sum(months.values()) for code, months in monthly.items()}


def _label(rule: str, cutoff: float) -> str:
    return f"{rule} {'k' if rule == 'mean' else 'f'}={cutoff:g}"


def summary(monthly: dict[str, dict[int, float]]) -> list[str]:
    lines = ["Peak-month count -> number of parks"]
    for rule, cutoff in CANDIDATES:
        counts: dict[int, int] = {}
        zero = []
        for code, months in monthly.items():
            n = len(peak_months(months, rule, cutoff))
            counts[n] = counts.get(n, 0) + 1
            if n == 0:
                zero.append(code)
        dist = ", ".join(f"{n}:{counts[n]}" for n in sorted(counts))
        lines.append(f"  {_label(rule, cutoff):12} {dist}" + (f"  (no peak: {', '.join(zero)})" if zero else ""))
    return lines


def detail(code: str, months: dict[int, float]) -> list[str]:
    mean = sum(months.values()) / 12
    lines = [
        f"{code}: annual {sum(months.values()):,.0f}, monthly mean {mean:,.0f}, "
        f"busiest {max(months.values()):,.0f} ({max(months.values()) / mean:.2f}x mean)",
        "  by month: " + " ".join(f"{m}:{months[m] / 1000:.0f}k" for m in MONTHS),
    ]
    for rule, cutoff in CANDIDATES:
        lines.append(f"  {_label(rule, cutoff):12} {peak_months(months, rule, cutoff)}")
    return lines


def parse_years(text: str) -> list[int]:
    if "-" in text:
        start, end = (int(part) for part in text.split("-"))
        return list(range(start, end + 1))
    return [int(part) for part in text.split(",")]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--years", default="2025", help="2025, 2023-2025 or 2023,2025")
    parser.add_argument("--parks", default="", help="comma-separated park codes to detail")
    parser.add_argument("--download", type=int, metavar="YEAR", help="refetch one raw year")
    args = parser.parse_args(argv)

    codes = catalog_codes()
    if args.download:
        print(f"Wrote {download(args.download, codes)}")
        return 0
    years = parse_years(args.years)
    monthly = load_monthly(years, codes)
    print(f"NPS recreation visits, {args.years} ({len(monthly)} parks)")
    print("\n".join(summary(monthly)))
    for code in [c for c in args.parks.split(",") if c]:
        print()
        print("\n".join(detail(code, monthly[code])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
