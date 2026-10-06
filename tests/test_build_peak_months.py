"""scripts/build_peak_months.py: raw NPS visit files and the peak-month rules."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_peak_months as bpm  # noqa: E402

FLAT = {m: 100.0 for m in bpm.MONTHS}
SUMMER = {m: (300.0 if m in (6, 7, 8) else 50.0) for m in bpm.MONTHS}


@pytest.mark.parametrize("year", [2023, 2024, 2025])
def test_raw_file_covers_every_catalog_park_for_12_months(year):
    codes = bpm.catalog_codes()
    visits = bpm.load_year(year, codes)
    assert sorted(visits) == sorted(codes)
    assert all(sorted(months) == list(bpm.MONTHS) for months in visits.values())


def test_seki_maps_to_sequoia_unit_and_kica_stays_separate():
    assert bpm.unit_code("seki") == "SEQU"
    assert bpm.park_code("SEQU") == "seki"
    assert bpm.unit_code("kica") == "KICA"


def test_mean_rule():
    assert bpm.peak_months(SUMMER, "mean", 1.25) == [6, 7, 8]
    # A flat park has no month above 1.25x its mean.
    assert bpm.peak_months(FLAT, "mean", 1.25) == []
    assert bpm.peak_months(FLAT, "mean", 1.0) == list(bpm.MONTHS)


def test_max_rule_always_keeps_the_busiest_month():
    assert bpm.peak_months(SUMMER, "max", 0.7) == [6, 7, 8]
    assert bpm.peak_months(FLAT, "max", 0.7) == list(bpm.MONTHS)


def test_all_zero_park_has_no_peak_and_unknown_rule_raises():
    assert bpm.peak_months({m: 0.0 for m in bpm.MONTHS}, "max", 0.7) == []
    with pytest.raises(ValueError):
        bpm.peak_months(FLAT, "median", 1.0)


def test_yosemite_peaks_in_summer_not_january():
    monthly = bpm.load_monthly([2025], bpm.catalog_codes())["yose"]
    for rule, cutoff in bpm.CANDIDATES:
        peaks = bpm.peak_months(monthly, rule, cutoff)
        assert 7 in peaks and 1 not in peaks, (rule, cutoff)


def test_parse_years():
    assert bpm.parse_years("2025") == [2025]
    assert bpm.parse_years("2023-2025") == [2023, 2024, 2025]
    assert bpm.parse_years("2023,2025") == [2023, 2025]
