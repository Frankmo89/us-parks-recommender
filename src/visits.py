"""NPS monthly recreation visits: loading, peak months and annual visits.

Raw files: data/raw/nps_recreation_visits_by_month_YYYY.json, saved verbatim
from the NPS Visitor Use Statistics REST endpoint (see README.md).

Rules (approved for engine 0.6.0):

* Visits are averaged over VISIT_YEARS (2023-2025), month by month.
* The federal shutdown (Oct 1 - Nov 12, 2025) is treated as missing data, not
  low visits: October and November average 2023 and 2024 only, for every park.
* A month is a peak month when its averaged visits are at least
  PEAK_CUTOFF (0.7) x the park's busiest averaged month.
"""

from __future__ import annotations

import json
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
MONTHS = tuple(range(1, 13))
VISIT_YEARS = (2023, 2024, 2025)
PEAK_CUTOFF = 0.7
# (year, month) pairs treated as missing for every park.
MISSING_MONTHS = frozenset({(2025, 10), (2025, 11)})

# NPS Stats unit code -> catalog park_code, where they differ. The catalog's
# `seki` row is Sequoia National Park, reported by NPS Stats as SEQU; Kings
# Canyon (KICA) is reported separately.
UNIT_TO_PARK = {"SEQU": "seki"}
PARK_TO_UNIT = {park: unit for unit, park in UNIT_TO_PARK.items()}


def raw_path(year: int, raw_dir: Path = RAW_DIR) -> Path:
    return raw_dir / f"nps_recreation_visits_by_month_{year}.json"


def unit_code(park_code: str) -> str:
    return PARK_TO_UNIT.get(park_code, park_code.upper())


def park_code(unit: str) -> str:
    return UNIT_TO_PARK.get(unit, unit.lower())


def load_year(year: int, codes: list[str], raw_dir: Path = RAW_DIR) -> dict[str, dict[int, int]]:
    """park_code -> {month: recreation visits}; every park needs 12 months."""
    path = raw_path(year, raw_dir)
    visits: dict[str, dict[int, int]] = {}
    for rec in json.loads(path.read_text()):
        if int(rec["Year"]) != year:
            raise ValueError(f"{path.name}: unexpected year {rec['Year']}")
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


def load_monthly(
    codes: list[str],
    years: tuple[int, ...] | list[int] = VISIT_YEARS,
    missing: frozenset[tuple[int, int]] = MISSING_MONTHS,
    raw_dir: Path = RAW_DIR,
) -> dict[str, dict[int, float]]:
    """Average visits per month across `years`, skipping `missing` (year, month)."""
    per_year = {year: load_year(year, codes, raw_dir) for year in years}
    out: dict[str, dict[int, float]] = {}
    for code in codes:
        out[code] = {}
        for month in MONTHS:
            kept = [per_year[y][code][month] for y in years if (y, month) not in missing]
            if not kept:
                raise ValueError(f"month {month}: every year is marked missing")
            out[code][month] = sum(kept) / len(kept)
    return out


def peak_months(monthly: dict[int, float], cutoff: float = PEAK_CUTOFF) -> list[int]:
    """Months with visits >= cutoff x the busiest month (empty if no visits)."""
    busiest = max(monthly.values())
    if busiest <= 0:
        return []
    return [m for m in MONTHS if monthly[m] >= cutoff * busiest]


def annual_visits(monthly: dict[str, dict[int, float]]) -> dict[str, float]:
    """Average annual visits: the sum of the averaged months."""
    return {code: sum(months.values()) for code, months in monthly.items()}
